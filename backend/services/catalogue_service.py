"""
Catalogue service: HITL data pipeline with sqlite-vec for semantic search.

Pipeline:
  1. ingest(rca, check_id, confidence) → shadow_catalogue OR pending_catalogue
  2. Deduplication check via KNN before adding to pending
  3. HITL: approve/reject/edit → primary_catalogue + catalogue_vec
  4. search(query_text, k) → KNN results for RAG context

sqlite-vec virtual table: catalogue_vec (rowid = primary_catalogue.id, embedding float32[768])
"""
import sqlite3
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional

import sqlite_vec
from services.sqlite_service import DB_PATH
from services.embedding_service import embed

CONFIDENCE_THRESHOLD = 0.70  # Below this → shadow catalogue
DEDUP_SIMILARITY_THRESHOLD = 0.92  # Above this cosine similarity → skip as duplicate


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_vec_table(conn: sqlite3.Connection):
    """Create the sqlite-vec virtual table and its UUID mapping table if they don't exist.
       Includes a self-repair block to fix int8 vs float32 type mismatches.
    """
    # ── Check for schema mismatch (Repair block) ───────────────────────────
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE name='catalogue_vec';")
    row = cursor.fetchone()
    if row and "int8" in row[0]:
        print("INFO: Found legacy int8 vector table. Dropping to recreate with float32...")
        conn.execute("DROP TABLE catalogue_vec;")
        conn.commit()

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS catalogue_vec
        USING vec0(embedding float32[768])
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS catalogue_vec_map (
            rowid INTEGER PRIMARY KEY AUTOINCREMENT, 
            catalogue_id TEXT UNIQUE
        )
    """)
    conn.commit()


# ── Stage 1: Ingest ───────────────────────────────────────────────────────────
async def ingest(rca: dict, check_id: Optional[str], confidence: float):
    """
    Route an RCA result through the confidence gate into the appropriate catalogue table.
    """
    category = rca.get("category", "Unknown")
    probable_cause = rca.get("probable_cause", "")
    rca_json = json.dumps(rca)

    if confidence < CONFIDENCE_THRESHOLD:
        _write_shadow(check_id, probable_cause, confidence, category, rca_json)
        return

    # Check for near-duplicate before adding to pending
    summary_text = _rca_to_summary(rca)
    embedding = await embed(summary_text)

    if embedding is not None:
        is_dup = await _is_duplicate(embedding)
        if is_dup:
            print(f"INFO: Catalogue ingest skipped (duplicate detected) for: {probable_cause[:60]}")
            return

    _write_pending(check_id, rca_json, confidence, category)
    print(f"INFO: Catalogue entry queued for HITL review (confidence={confidence:.2f}): {probable_cause[:60]}")


def _rca_to_summary(rca: dict) -> str:
    """Convert an RCA dict into a concise text for embedding."""
    parts = []
    if rca.get("category"):
        parts.append(f"Category: {rca['category']}")
    if rca.get("probable_cause"):
        parts.append(f"Cause: {rca['probable_cause']}")
    if rca.get("repair_action"):
        parts.append(f"Fix: {rca['repair_action']}")
    return " | ".join(parts)


def _write_shadow(check_id, probable_cause, confidence, category, raw_rca_json):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO shadow_catalogue (id, check_id, probable_cause, confidence, category, raw_rca_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), check_id, probable_cause, confidence, category, raw_rca_json),
    )
    conn.commit()
    conn.close()


def _write_pending(check_id, rca_json, confidence, category):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO pending_catalogue (id, check_id, rca_json, confidence, category)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), check_id, rca_json, confidence, category),
    )
    conn.commit()
    conn.close()


# ── Stage 2: Deduplication ────────────────────────────────────────────────────
async def _is_duplicate(embedding: bytes) -> bool:
    """Returns True if a very similar entry already exists in catalogue_vec."""
    try:
        conn = _get_conn()
        _ensure_vec_table(conn)
        rows = conn.execute(
            """SELECT vec_distance_cosine(embedding, ?) AS distance
               FROM catalogue_vec
               ORDER BY distance LIMIT 1""",
            [embedding],
        ).fetchall()
        conn.close()
        if rows:
            distance = rows[0]["distance"]
            # vec_distance_cosine returns 0.0 for identical, 2.0 for opposite.
            # Similarity = 1.0 - distance
            similarity = 1.0 - distance
            return similarity >= DEDUP_SIMILARITY_THRESHOLD
        return False
    except Exception as e:
        print(f"WARNING: Dedup check failed (non-blocking): {e}")
        return False


# ── Stage 3: HITL Actions ─────────────────────────────────────────────────────
async def approve(pending_id: str, reviewer_id: str, edited_rca: Optional[dict] = None) -> dict:
    """
    Move a pending entry to primary_catalogue and embed it into catalogue_vec.
    If edited_rca is provided, use that instead of the stored version.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM pending_catalogue WHERE id = ? AND status = 'pending'", (pending_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Pending entry {pending_id} not found or already reviewed")

    rca = edited_rca if edited_rca else json.loads(row["rca_json"])

    # Write to primary catalogue
    catalogue_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO primary_catalogue
           (id, category, probable_cause, repair_action, confidence, evidence_json, approved_by)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            catalogue_id,
            rca.get("category", row["category"] or "Unknown"),
            rca.get("probable_cause", ""),
            rca.get("repair_action", ""),
            row["confidence"],
            json.dumps(rca),
            reviewer_id,
        ),
    )

    # Mark pending as approved
    cur.execute(
        "UPDATE pending_catalogue SET status = 'approved', reviewer_id = ?, reviewed_at = ? WHERE id = ?",
        (reviewer_id, datetime.now().isoformat(), pending_id),
    )
    
    # Embed and insert into sqlite-vec virtual table
    summary = _rca_to_summary(rca)
    embedding = await embed(summary)
    if embedding:
        # Use existing connection to ensure atomic-like updates
        # Load sqlite-vec into the same connection we used for primary_catalogue
        cur.connection.enable_load_extension(True)
        sqlite_vec.load(cur.connection)
        cur.connection.enable_load_extension(False)
        _ensure_vec_table(cur.connection)

        # 1. Map UUID to INTEGER rowid
        cur.execute(
            "CREATE TABLE IF NOT EXISTS catalogue_vec_map (rowid INTEGER PRIMARY KEY AUTOINCREMENT, catalogue_id TEXT UNIQUE)"
        )
        cur.execute("INSERT OR IGNORE INTO catalogue_vec_map (catalogue_id) VALUES (?)", (catalogue_id,))
        cur.execute("SELECT rowid FROM catalogue_vec_map WHERE catalogue_id = ?", (catalogue_id,))
        int_rowid = cur.fetchone()[0]

        # 2. Insert into virtual table
        cur.execute(
            "INSERT INTO catalogue_vec (rowid, embedding) VALUES (?, ?)",
            [int_rowid, embedding],
        )

    conn.commit()
    conn.close()
    
    if embedding:
        print(f"INFO: Catalogue entry {catalogue_id} embedded and stored in vec table")

    return {"catalogue_id": catalogue_id, "embedded": embedding is not None}


async def reject(pending_id: str, reviewer_id: str, note: str = "") -> None:
    """Mark a pending entry as rejected."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """UPDATE pending_catalogue
           SET status = 'rejected', reviewer_id = ?, reviewer_note = ?, reviewed_at = ?
           WHERE id = ?""",
        (reviewer_id, note, datetime.now().isoformat(), pending_id),
    )
    conn.commit()
    conn.close()


# ── Semantic Search (RAG retrieval) ───────────────────────────────────────────
async def search(query_text: str, k: int = 3) -> list[dict]:
    """
    Consolidated KNN search in catalogue_vec using SQL JOINs.
    Returns top-k primary_catalogue entries with similarity scores.
    """
    embedding = await embed(query_text)
    if not embedding:
        return []

    try:
        conn = _get_conn()
        _ensure_vec_table(conn)
        
        # Taking "Full Advantage": Single SQL query for k-NN + metadata mapping + similarity scoring
        query = """
            SELECT 
                p.*,
                1.0 - v.distance AS similarity
            FROM catalogue_vec v
            JOIN catalogue_vec_map m ON v.rowid = m.rowid
            JOIN primary_catalogue p ON m.catalogue_id = p.id
            WHERE v.embedding MATCH ? AND v.k = ?
            ORDER BY v.distance 
        """
        rows = conn.execute(query, [embedding, k]).fetchall()
        
        results = [dict(r) for r in rows]
        
        # Update last_matched_at for retrieved entries (atomic update)
        if results:
            ids = [r["id"] for r in results]
            conn.executemany(
                "UPDATE primary_catalogue SET last_matched_at = ? WHERE id = ?",
                [(datetime.now().isoformat(), i) for i in ids]
            )
            conn.commit()
            
        conn.close()
        return results

    except Exception as e:
        print(f"ERROR: Consolidated catalogue search failed: {e}")
        return []


# ── Read helpers ──────────────────────────────────────────────────────────────
def get_pending(limit: int = 50) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM pending_catalogue WHERE status = 'pending' ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_approved(limit: int = 100) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, category, probable_cause, repair_action, confidence, evidence_json as rca_json, approved_by, created_at FROM primary_catalogue ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_shadow(limit: int = 100) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, check_id, probable_cause, confidence, category, raw_rca_json as rca_json, created_at FROM shadow_catalogue ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

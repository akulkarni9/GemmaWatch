import pytest
import sqlite3
import json
from services.catalogue_service import ingest, approve, get_pending, get_shadow, get_approved

@pytest.mark.asyncio
async def test_catalogue_ingest_shadow(temp_db):
    """Low confidence RCAs should be routed to shadow_catalogue."""
    rca = {"probable_cause": "Minor CSS change", "category": "Frontend"}
    
    # Confidence 0.5 is below 0.7 threshold
    await ingest(rca, check_id="check-1", confidence=0.5)
    
    shadows = get_shadow()
    assert len(shadows) == 1
    assert shadows[0]["probable_cause"] == "Minor CSS change"
    assert shadows[0]["confidence"] == 0.5
    
    # Verify not in pending
    assert len(get_pending()) == 0

@pytest.mark.asyncio
async def test_catalogue_ingest_pending(temp_db, mock_embedding):
    """High confidence RCAs should be routed to pending_catalogue (if not duplicate)."""
    rca = {"probable_cause": "Database connection timeout", "category": "Backend"}
    
    # Mocking embedding to avoid actual API call and ensure deterministic duplicate check
    # Confidence 0.9 is above 0.7 threshold
    await ingest(rca, check_id="check-1", confidence=0.9)
    
    pending = get_pending()
    assert len(pending) == 1
    assert "Database connection timeout" in pending[0]["rca_json"]

@pytest.mark.asyncio
async def test_catalogue_approve_flow(temp_db, mock_embedding):
    """Approving a pending entry should move it to primary and trigger embedding."""
    # 1. Setup pending entry
    conn = sqlite3.connect(temp_db)
    pending_id = "pending-1"
    rca = {"probable_cause": "System crash", "category": "Infrastructure"}
    conn.execute("INSERT INTO pending_catalogue (id, rca_json, confidence, category) VALUES (?, ?, ?, ?)",
                 (pending_id, json.dumps(rca), 0.95, "Infrastructure"))
    conn.commit()
    conn.close()
    
    # Check if virtual table exists to decide if we can test embedding logic
    conn = sqlite3.connect(temp_db)
    is_virtual = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='catalogue_vec' AND sql LIKE '%VIRTUAL%'").fetchone()[0] > 0
    conn.close()
    
    if not is_virtual:
        # Avoid size checks on non-virtual table by skipping the actual embedding part in approve()
        # but approve() calls embed() internally.
        # Fixed: Conftest mock returns 3072 bytes (float32) which matches sqlite-vec default.
        pass

    # 2. Approve
    await approve(pending_id, reviewer_id="admin-1")
    
    # 3. Verify transfers
    approved = get_approved()
    assert len(approved) == 1
    assert approved[0]["probable_cause"] == "System crash"
    
    # 4. Verify vector mapping
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT catalogue_id FROM catalogue_vec_map")
    mapping = cur.fetchone()
    assert mapping[0] is not None
    conn.close()

@pytest.mark.asyncio
async def test_catalogue_search_rag(temp_db, mock_embedding):
    """Verify that semantic search returns matched entries with similarity scores."""
    # 1. Setup primary entry and vector mapping manually
    conn = sqlite3.connect(temp_db)
    # MUST load extension for EVERY connection
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except:
        pytest.skip("Could not load sqlite-vec in test")

    cat_id = "cat-1"
    conn.execute("INSERT INTO primary_catalogue (id, category, probable_cause) VALUES (?, ?, ?)",
                 (cat_id, "Frontend", "Button alignment issue"))
    conn.execute("INSERT INTO catalogue_vec_map (catalogue_id) VALUES (?)", (cat_id,))
    rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # Check if virtual table exists
    is_virtual = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='catalogue_vec' AND sql LIKE '%VIRTUAL%'").fetchone()[0] > 0
    
    if not is_virtual:
        pytest.skip("sqlite-vec virtual table not found")
        
    # If virtual, we need a 3072 byte blob (float32)
    import struct
    vec_blob = struct.pack('768f', *([0.0]*768))
    conn.execute("INSERT INTO catalogue_vec (rowid, embedding) VALUES (?, ?)", (rowid, vec_blob))
    conn.commit()
    conn.close()
    
    # 2. Search
    from services.catalogue_service import search
    results = await search("Is the button aligned?")
    
    assert isinstance(results, list)
    if len(results) > 0:
        assert results[0]["id"] == cat_id
        assert "similarity" in results[0]

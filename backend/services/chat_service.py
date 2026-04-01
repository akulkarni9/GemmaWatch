"""
Chat service: natural language query interface scoped to GemmaWatch data.
Two-path routing:
  - Structured: Gemma generates SQL → execute → Gemma formats result
  - Semantic: embed query → KNN in catalogue_vec → Gemma synthesises answer
"""
import sqlite3
import uuid
import json
import re
import os
from datetime import datetime
from typing import Optional, List

from services.sqlite_service import DB_PATH


# ── Read-only schema accurately mapping to the SQLite DB ──────────────────────
READ_SCHEMA = """
Tables & Columns:
  sites(id, name, url, check_type, frequency, created_at, last_checked_at)
  checks(id, site_id, status, timestamp, status_code, console_log_count, network_error_count)
  metrics(id, site_id, response_time_ms, dom_elements, console_errors, timestamp)
  incidents(id, title, severity, status, affected_site_ids_json, probable_shared_cause, created_at, resolved_at)
  anomaly_events(id, site_id, severity, metric_type, observed_value, z_score, gemma_interpretation, created_at)
  primary_catalogue(id, category, probable_cause, repair_action, confidence, evidence_json, last_matched_at)
"""

ALLOWED_SQL_PATTERN = re.compile(
    r"^\s*SELECT\b.+\bFROM\b.+$", re.IGNORECASE | re.DOTALL
)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _get_latest_screenshot(site_name: str) -> Optional[str]:
    """Retrieves the absolute path to the latest screenshot for a site."""
    try:
        conn = _get_conn()
        site = conn.execute("SELECT id FROM sites WHERE name = ?", (site_name,)).fetchone()
        if not site:
            conn.close()
            return None
        
        check = conn.execute(
            "SELECT screenshot_url FROM checks WHERE site_id = ? AND screenshot_url != '' ORDER BY timestamp DESC LIMIT 1",
            (site["id"],)
        ).fetchone()
        conn.close()
        
        if check and check["screenshot_url"]:
            # URL is like /screenshots/currents/site_id_timestamp.png
            # The app root is one level up from backend/
            rel_path = check["screenshot_url"].lstrip("/")
            abs_path = os.path.abspath(os.path.join(os.getcwd(), "..", rel_path))
            if os.path.exists(abs_path):
                return abs_path
        return None
    except Exception:
        return None


def _detect_site_match(query: str) -> list[str]:
    """Deterministically check if query mentions a site name."""
    try:
        conn = _get_conn()
        sites = conn.execute("SELECT name FROM sites").fetchall()
        conn.close()
        
        matches = []
        for s in sites:
            name = s["name"]
            # Case-insensitive match on whole word or specific name
            if re.search(rf"\b{re.escape(name)}\b", query, re.IGNORECASE):
                matches.append(name)
        return matches
    except Exception:
        return []


async def _classify_query(query: str, history_context: str = "") -> str:
    """
    Ask Gemma to classify the query. Gemma 3 is smart enough to handle subtle intent.
    """
    from services.ai_service import ai_service
    prompt = f"""Classify this monitoring question for an autonomous observability platform.
{history_context}
Question: {query}

Categories:
- 'system': General help, identity, "what can you do", or basic platform info.
- 'structured': Questions about metrics, uptime, site status, logs, or specific historical data.
- 'semantic': Questions about patterns, "why did this happen", or cross-referencing past known issues.

Respond with ONLY one word: system, structured, or semantic."""
    try:
        result = (await ai_service._call_ollama(prompt) or "structured").strip().lower()
        if "system" in result: return "system"
        if "semantic" in result: return "semantic"
        return "structured"
    except Exception:
        return "structured"


async def _system_query(query: str) -> dict:
    """Handle general platform info with high technical precision (No conversational fluff)."""
    from services.ai_service import ai_service
    prompt = f"""You are GemmaWatch AI, a high-precision autonomous observability engine. 
Persona: Technical Analyst. Tone: Concise, Data-Driven, Professional.
MANDATORY: Do NOT use conversational filler (e.g., "Certainly," "It's a pleasure," "I understand").
MANDATORY: Provide direct information about system capabilities or status.

CORE FEATURES:
- Visual Regression: Snapshot-based UI change detection.
- Autonomous RCA: Gemma-interpreted failure analysis & code-level fixes.
- Anomaly Detection: Statistical deviation monitoring (Response Time/DOM).
- Intelligence Catalogue: Shared knowledge base of approved patterns.

Question: {query}
Answer concisely."""
    answer = await ai_service._call_ollama(prompt)
    return {"answer": answer, "query_type": "system", "sources": []}


async def _structured_query(query: str, site_hint: Optional[str] = None, images: List[str] = None) -> dict:
    """Gemma generates analytic SQL with join awareness and temporal reasoning."""
    from services.ai_service import ai_service
    now_iso = datetime.now().isoformat()

    hint_text = f"\nHINT: User is asking about site '{site_hint}'." if site_hint else ""

    sql_prompt = f"""You are a SQLite and Observability expert. Generate a SELECT query to answer this query.
DB SCHEMA: {READ_SCHEMA}
CURRENT TIME: '{now_iso}'{hint_text}

MANDATORY RULES:
- ONLY SELECT.
- Keep queries simple and flat. Do NOT use SQLite JSON functions like JSON_OBJECT or JSON_GROUP_ARRAY.
- ALWAYS explicitly alias your tables (e.g., `FROM sites AS s`). Do NOT use undeclared aliases like T1 or T2.
- Use 'LIKE %keyword%' for text comparisons to avoid case-sensitivity misses (e.g., `s.name LIKE '%neo4j%'`).
- Use JOINs where appropriate (e.g., checks + metrics) to correlate failures with performance spikes.
- Use 'timestamp' filters for recent data.
- Return ONLY the SQL query. No explanation.

Question: {query}"""

    try:
        raw_sql = (await ai_service._call_ollama(sql_prompt) or "").strip()
        # Extract SQL if wrapped in markdown
        if "```" in raw_sql:
            raw_sql = raw_sql.split("```")[1]
            if raw_sql.startswith("sql"): raw_sql = raw_sql[3:]
        raw_sql = raw_sql.strip()
        print(f"DEBUG: Generated SQL for query '{query}': {raw_sql}")

        # Safety validation
        if not raw_sql or not ALLOWED_SQL_PATTERN.match(raw_sql):
            return {"answer": "I couldn't construct a precise query for that. Can you specify which site or time range?",
                    "query_type": "structured", "sources": []}

        conn = _get_conn()
        try:
            rows = conn.execute(raw_sql).fetchmany(20)
            data = [dict(r) for r in rows]
        except sqlite3.Error as e:
            conn.close()
            return {"answer": f"Analysis error: {e}. Let's try rephrasing.",
                    "query_type": "structured", "sources": []}
        conn.close()

        if not data:
            return {"answer": "I couldn't find any data matching those criteria in the system.", 
                    "query_type": "structured", "sources": []}

        format_prompt = f"""Analyze the provided monitoring data and provide a deep reasoning response.
Question: {query}

### DATA CONTEXT (UP TO 15k CHARS):
{json.dumps(data, default=str)[:15000]}

### INSTRUCTIONS:
- Identify trends, correlations, or anomalies in the data.
- If screenshots are provided, prioritize visual evidence for layout or rendering queries.
- Be concise, technical, and professional. Use markdown tables for data if helpful."""

        # Synchronous call for non-streaming usage
        answer = await ai_service._call_ollama(format_prompt, images=images)
        return {"answer": answer or str(data), "query_type": "structured", "sources": [], "raw_data": data}

    except Exception as e:
        return {"answer": f"Intelligence engine error: {e}", "query_type": "structured", "sources": []}

async def _structured_query_stream(query: str, history_context: str = "", site_hint: Optional[str] = None, images: List[str] = None):
    """Generator version of _structured_query."""
    yield "[SYSTEM] Generating data filters for your request...\n\n"
    from services.ai_service import ai_service
    now_iso = datetime.now().isoformat()
    hint_text = f"\nHINT: User is asking about site '{site_hint}'." if site_hint else ""

    sql_prompt = f"""You are a SQLite and Observability expert. Generate a SELECT query to answer this query.
DB SCHEMA: {READ_SCHEMA}
CURRENT TIME: '{now_iso}'{hint_text}
{history_context}
MANDATORY RULES:
- Keep queries simple and flat. Do NOT use SQLite JSON functions like JSON_OBJECT or JSON_GROUP_ARRAY.
- ALWAYS explicitly alias your tables (e.g., `FROM sites AS s`). Do NOT use undeclared aliases like T1 or T2.
- Use 'LIKE %keyword%' for text comparisons to avoid case-sensitivity misses (e.g., `s.name LIKE '%neo4j%'`).
- Return ONLY a valid JSON object with a single key "sql" containing the SELECT query. Nothing else.

Question: {query}"""

    raw_sql_resp = (await ai_service._call_ollama(sql_prompt, is_json=True) or "").strip()
    
    raw_sql = ""
    try:
        sql_data = json.loads(raw_sql_resp)
        raw_sql = sql_data.get("sql", "")
    except Exception:
        raw_sql = raw_sql_resp
        if "```" in raw_sql:
            raw_sql = raw_sql.split("```")[1]
            if raw_sql.startswith("sql"): raw_sql = raw_sql[3:]
            
    raw_sql = raw_sql.strip()

    if not raw_sql or not ALLOWED_SQL_PATTERN.match(raw_sql):
        yield "I couldn't construct a precise query for that. Can you specify which site or time range?"
        return

    # Log the exact SQL generated to the UI for absolute transparency
    yield f"[SYSTEM] Executing query:\n```sql\n{raw_sql}\n```\n\n"

    conn = _get_conn()
    yield "[SYSTEM] Fetching metrics from GemmaWatch database...\n\n"
    try:
        rows = conn.execute(raw_sql).fetchmany(20)
        data = [dict(r) for r in rows]
    except sqlite3.Error as e:
        conn.close()
        yield f"Analysis error: {e}"
        return
    conn.close()

    if not data:
        yield "I couldn't find any data matching those criteria in the system."
        return

    yield f"[SYSTEM] Synthesis in progress (analyzing {len(data)} records)...\n\n"

    format_prompt = f"""Analyze the provided monitoring data and provide a deep reasoning response.
{history_context}
Question: {query}
### DATA CONTEXT:
{json.dumps(data, default=str)[:15000]}
### INSTRUCTIONS:
- Identify trends, correlations, or anomalies. Highlight anomalies.
- If screenshots were provided, use them to verify layout/rendering.
- Respond technical and concise."""

    try:
        async for chunk in ai_service.yield_ollama(format_prompt, images=images):
            yield chunk
    except Exception as e:
        yield f"Intelligence engine error: {e}"


async def _semantic_query(query: str) -> dict:
    """Embed query → KNN in catalogue_vec → Gemma synthesises an answer."""
    from services.ai_service import ai_service
    from services.catalogue_service import search as catalogue_search

    sources = await catalogue_search(query, k=3)

    if not sources:
        # Fallback to system query if no semantic context found
        return await _system_query(query)

    context = "\n\n".join([
        f"[{i+1}] Category: {s.get('category')} | Cause: {s.get('probable_cause')} | Fix: {s.get('repair_action')}"
        for i, s in enumerate(sources)
    ])

    answer_prompt = f"""You are GemmaWatch AI. Answer this question using ONLY the knowledge base entries provided.
Do not invent information. If the entries don't fully answer the question, say so.

Question: {query}

Knowledge base entries:
{context}

Answer concisely in 3-5 sentences."""

    answer = await ai_service._call_ollama(answer_prompt)
    return {
        "answer": answer or "I found similar patterns but could not synthesise an answer.",
        "query_type": "semantic",
        "sources": [{"category": s.get("category"), "probable_cause": s.get("probable_cause"),
                     "similarity": s.get("similarity")} for s in sources],
    }


# ── Public interface ──────────────────────────────────────────────────────────
async def chat(query: str, session_id: str, user_id: Optional[str] = None) -> dict:
    # (Existing sync code remains same, just uses the updated 15k limit via _structured_query)
    # ... (rest of function unchanged, just need to ensure it's here)
    if not query.strip():
        return {"answer": "Please ask a question.", "query_type": "structured", "sources": []}

    matched_sites = _detect_site_match(query)
    images = []
    if matched_sites:
        screenshot_path = _get_latest_screenshot(matched_sites[0])
        if screenshot_path:
            from services.ai_service import ai_service as ai
            encoded = ai._encode_image(screenshot_path)
            if encoded:
                images.append(encoded)

    if matched_sites:
        result = await _structured_query(query, site_hint=matched_sites[0], images=images)
    else:
        query_type = await _classify_query(query)
        if query_type == "system":
            result = await _system_query(query)
        elif query_type == "semantic":
            result = await _semantic_query(query)
        else:
            result = await _structured_query(query, images=images)

    _persist_messages(session_id, user_id, query, result)
    return result


async def chat_stream(query: str, session_id: str, user_id: Optional[str] = None):
    """Streaming entry point for chat."""
    if not query.strip():
        yield "Please ask a question."
        return

    matched_sites = _detect_site_match(query)
    images = []
    if matched_sites:
        screenshot_path = _get_latest_screenshot(matched_sites[0])
        if screenshot_path:
            from services.ai_service import ai_service as ai
            encoded = ai._encode_image(screenshot_path)
            if encoded:
                images.append(encoded)

    full_answer = ""
    query_type = "structured"
    
    # Extract Conversation History Context
    history = get_chat_history(session_id)
    history_context = ""
    if history:
        # Take last 4 messages to avoid token bloat
        recent_history = history[-4:]
        history_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in recent_history if msg["content"] and not msg["content"].startswith("[SYSTEM]")])
        history_context = f"### RECENT CONVERSATION HISTORY:\n{history_text}\n\nUse this context to understand references like 'it', 'that site', or 'previous issue'.\n"
    
    if matched_sites:
        async for chunk in _structured_query_stream(query, history_context=history_context, site_hint=matched_sites[0], images=images):
            full_answer += chunk
            yield chunk
    else:
        # Prevent "hanging" while classifying the intent
        status_msg = "[SYSTEM] Analyzing query intent...\n\n"
        full_answer += status_msg
        yield status_msg
        
        query_type = await _classify_query(query, history_context=history_context)
        if query_type == "system":
            # System query is short, we can just call it sync but yield it
            result = await _system_query(query)
            full_answer = result["answer"]
            yield full_answer
        elif query_type == "semantic":
            # Semantic query generator
            async for chunk in _semantic_query_stream(query, history_context=history_context):
                full_answer += chunk
                yield chunk
        else:
            async for chunk in _structured_query_stream(query, history_context=history_context, images=images):
                full_answer += chunk
                yield chunk

    # Persist the final result
    _persist_messages(session_id, user_id, query, {"answer": full_answer, "query_type": query_type, "sources": []})


async def _semantic_query_stream(query: str, history_context: str = ""):
    """Generator version of _semantic_query."""
    yield "[SYSTEM] Searching knowledge base for similar incidents...\n\n"
    from services.ai_service import ai_service
    from services.catalogue_service import search as catalogue_search

    sources = await catalogue_search(query, k=3)
    if not sources:
        result = await _system_query(query)
        yield result["answer"]
        return

    context = "\n\n".join([
        f"[{i+1}] Category: {s.get('category')} | Cause: {s.get('probable_cause')} | Fix: {s.get('repair_action')}"
        for i, s in enumerate(sources)
    ])

    yield "[SYSTEM] Found matches in approved catalogue. Summarizing solution...\n\n"

    answer_prompt = f"""You are GemmaWatch AI. Answer this question using ONLY the knowledge base entries.
{history_context}
Question: {query}
Entries:
{context}
Answer concisely."""

    async for chunk in ai_service.yield_ollama(answer_prompt):
        yield chunk


def _persist_messages(session_id: str, user_id: Optional[str], query: str, result: dict):
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO chat_messages (id, session_id, user_id, role, content, query_type, sources_json, created_at) VALUES (?, ?, ?, 'user', ?, ?, ?, ?)",
        (str(uuid.uuid4()), session_id, user_id, query, result.get("query_type"), "[]", now),
    )
    conn.execute(
        "INSERT INTO chat_messages (id, session_id, user_id, role, content, query_type, sources_json, created_at) VALUES (?, ?, ?, 'assistant', ?, ?, ?, ?)",
        (str(uuid.uuid4()), session_id, user_id, result.get("answer", ""), result.get("query_type"),
         json.dumps(result.get("sources", [])), now),
    )
    conn.commit()
    conn.close()


def get_chat_history(session_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content, query_type, sources_json, created_at FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

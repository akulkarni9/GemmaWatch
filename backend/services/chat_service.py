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
from datetime import datetime
from typing import Optional

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


async def _classify_query(query: str) -> str:
    """
    Ask Gemma to classify the query: 'system', 'structured', or 'semantic'.
    'system' = General help, product info, identity.
    'structured' = Data-heavy queries (counts, uptime, status).
    'semantic' = Pattern-based queries (RAG).
    """
    from services.ai_service import ai_service
    prompt = f"""Classify this monitoring question as 'system', 'structured', or 'semantic'.

- 'system': Questions like "Who are you?", "What can you do?", "Help me", or general platform info.
- 'structured': Questions about specific sites, entity names (e.g. Mark, Google), counts, uptime, or metrics.
- 'semantic': Questions about historical patterns, root cause knowledge, or "have we seen this before".

Question: {query}
Respond with ONLY one word: system, structured, or semantic"""
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


async def _structured_query(query: str, site_hint: Optional[str] = None) -> dict:
    """Gemma generates SQL with temporal awareness and optional entity hints."""
    from services.ai_service import ai_service
    now_iso = datetime.now().isoformat()

    hint_text = f"\nHINT: Users is asking about site '{site_hint}'." if site_hint else ""

    sql_prompt = f"""You are a SQLite expert. Generate a SELECT query to answer this query.
DB SCHEMA: {READ_SCHEMA}
CURRENT TIME: '{now_iso}'{hint_text}

MANDATORY RULES:
- ONLY SELECT. No mutations.
- Limit 20 rows.
- ALWAYS wrap strings and timestamps in SINGLE QUOTES (e.g. '{now_iso}').
- Use current time '{now_iso}' for relative filters.
- Use LIKE for case-insensitive site name searches.
- Return ONLY the SQL query. No explanation, no markdown fluff.

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

        format_prompt = f"""Answer this query based on the monitoring data. 
Question: {query}
Data: {json.dumps(data, default=str)[:3000]}
Be concise and professional."""
        answer = await ai_service._call_ollama(format_prompt)
        return {"answer": answer or str(data), "query_type": "structured", "sources": [], "raw_data": data}

    except Exception as e:
        return {"answer": f"Intelligence engine error: {e}", "query_type": "structured", "sources": []}


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
    """Main entry point: route, execute, persist, return."""
    if not query.strip():
        return {"answer": "Please ask a question.", "query_type": "structured", "sources": []}

    # Deterministic Entity Recognition Layer
    matched_sites = _detect_site_match(query)
    
    if matched_sites:
        # Force structured analysis if a site is matched
        result = await _structured_query(query, site_hint=matched_sites[0])
    else:
        query_type = await _classify_query(query)

        if query_type == "system":
            result = await _system_query(query)
        elif query_type == "semantic":
            result = await _semantic_query(query)
        else:
            result = await _structured_query(query)

    # Persist the exchange
    _persist_messages(session_id, user_id, query, result)
    return result


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

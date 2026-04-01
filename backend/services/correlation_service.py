"""
Cross-site correlation engine → Incident creation.
After every check, scans for 2+ sites that degraded within a 15-minute window.
Creates Incident records and triggers alerting.
"""
import sqlite3
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional

from services.sqlite_service import DB_PATH

CORRELATION_WINDOW_MINUTES = 15
MIN_SITES_FOR_INCIDENT = 2


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


async def check_and_create_incident(triggering_site_id: str, triggering_check_status: str) -> Optional[dict]:
    """
    Called after every monitoring check. If 2+ sites degraded within the window,
    creates an Incident (unless one already exists for this group).
    Returns the created incident dict, or None.
    """
    if triggering_check_status not in ("FAILED",):
        # Also trigger on anomaly events — see anomaly_service integration
        return None

    window_start = (datetime.now() - timedelta(minutes=CORRELATION_WINDOW_MINUTES)).isoformat()
    now = datetime.now().isoformat()

    conn = _get_conn()
    # Find all sites with failures or anomalies in the window
    failed_checks = conn.execute(
        """SELECT DISTINCT c.site_id, s.name
           FROM checks c
           JOIN sites s ON c.site_id = s.id
           WHERE c.status = 'FAILED'
             AND c.timestamp >= ?""",
        (window_start,),
    ).fetchall()

    anomalous_sites = conn.execute(
        """SELECT DISTINCT site_id FROM anomaly_events
           WHERE created_at >= ?""",
        (window_start,),
    ).fetchall()

    # Merge and deduplicate
    affected = {r["site_id"]: r["name"] for r in failed_checks}
    for row in anomalous_sites:
        if row["site_id"] not in affected:
            site = conn.execute("SELECT id, name FROM sites WHERE id = ?", (row["site_id"],)).fetchone()
            if site:
                affected[site["id"]] = site["name"]

    if len(affected) < MIN_SITES_FOR_INCIDENT:
        conn.close()
        return None

    # Check if an open incident already covers this set of sites
    affected_ids = sorted(affected.keys())
    open_incidents = conn.execute(
        "SELECT * FROM incidents WHERE status = 'open' AND created_at >= ?",
        (window_start,),
    ).fetchall()

    for inc in open_incidents:
        existing_ids = sorted(json.loads(inc["affected_site_ids_json"] or "[]"))
        # If there's significant overlap (>50%), don't create a duplicate
        overlap = len(set(affected_ids) & set(existing_ids))
        if overlap >= MIN_SITES_FOR_INCIDENT:
            conn.close()
            return None  # Incident already exists

    conn.close()

    # Create the incident
    site_names = list(affected.values())
    incident = await _create_incident(
        affected_ids=affected_ids,
        affected_names=site_names,
        window_start=window_start,
        window_end=now,
    )

    return incident


async def _create_incident(affected_ids: list, affected_names: list,
                            window_start: str, window_end: str) -> dict:
    from services.ai_service import ai_service

    # Derive severity from count
    severity = "low"
    if len(affected_ids) >= 5:
        severity = "critical"
    elif len(affected_ids) >= 3:
        severity = "high"
    elif len(affected_ids) >= 2:
        severity = "medium"

    names_str = ", ".join(affected_names[:5])
    title = f"Simultaneous degradation across {len(affected_ids)} sites: {names_str}"

    # Ask Gemma for a shared cause hypothesis
    probable_cause = await _gemma_shared_cause(affected_names)

    incident_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO incidents
           (id, title, severity, status, affected_site_ids_json,
            correlation_window_start, correlation_window_end, probable_shared_cause)
           VALUES (?, ?, ?, 'open', ?, ?, ?, ?)""",
        (
            incident_id, title, severity,
            json.dumps(affected_ids),
            window_start, window_end,
            probable_cause,
        ),
    )
    conn.commit()
    conn.close()

    incident = {
        "id": incident_id,
        "title": title,
        "severity": severity,
        "status": "open",
        "affected_site_ids": affected_ids,
        "affected_site_names": affected_names,
        "correlation_window_start": window_start,
        "correlation_window_end": window_end,
        "probable_shared_cause": probable_cause,
        "created_at": datetime.now().isoformat(),
    }

    print(f"INFO: Incident created — {title}")
    return incident


async def _gemma_shared_cause(site_names: list) -> str:
    try:
        from services.ai_service import ai_service
        prompt = f"""[OBSERVABILITY ANALYST MODE]
Multiple monitored sites have degraded simultaneously within a 15-minute window:
Sites affected: {', '.join(site_names)}

Provide a detailed, high-confidence correlation analysis (2-3 sentences). 
Identify the most likely shared infrastructure failure (e.g., specific CDN outage, regional DNS failure, shared hosting cluster latency). 
Include a brief suggested verification step for an analyst.
Respond with the analysis only, no preamble."""
        result = await ai_service._call_ollama(prompt)
        return (result or "Shared infrastructure failure suspected — investigate CDN, DNS, or hosting provider").strip()[:1000]
    except Exception:
        return "Shared infrastructure failure suspected — investigate CDN, DNS, or hosting provider"


# ── CRUD ──────────────────────────────────────────────────────────────────────
def get_incidents(status: Optional[str] = None, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM incidents WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["affected_site_ids"] = json.loads(d.get("affected_site_ids_json") or "[]")
        result.append(d)
    return result


def get_incident(incident_id: str) -> Optional[dict]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["affected_site_ids"] = json.loads(d.get("affected_site_ids_json") or "[]")
    return d


def resolve_incident(incident_id: str, resolver_id: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE incidents SET status = 'resolved', resolved_at = ?, resolved_by = ? WHERE id = ?",
        (datetime.now().isoformat(), resolver_id, incident_id),
    )
    conn.commit()
    conn.close()
    return True


def add_incident_note(incident_id: str, user_id: Optional[str], note: str) -> str:
    note_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + 'Z'
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO incident_notes (id, incident_id, user_id, note, created_at) VALUES (?, ?, ?, ?, ?)",
        (note_id, incident_id, user_id, note, now),
    )
    conn.commit()
    conn.close()
    return note_id


def get_incident_notes(incident_id: str) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        """SELECT n.*, u.name as user_name 
           FROM incident_notes n 
           LEFT JOIN users u ON n.user_id = u.id 
           WHERE n.incident_id = ? 
           ORDER BY n.created_at ASC""",
        (incident_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

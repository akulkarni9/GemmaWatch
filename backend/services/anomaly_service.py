"""
Anomaly detection service.
Stage 1: Statistical (z-score) — cheap, runs after every check.
Stage 2: Gemma interpretation — async, only when Stage 1 triggers.
"""
import sqlite3
import uuid
import json
import math
from datetime import datetime
from typing import Optional

from services.sqlite_service import DB_PATH

# Thresholds
Z_SCORE_THRESHOLD = 3.0
DOM_DROP_THRESHOLD = 0.20   # 20% drop in element count
ERROR_RATE_WINDOW = 5       # last N checks for error rate
ERROR_RATE_THRESHOLD = 0.40  # 40% error rate


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


async def run_stage1(site_id: str, check_id: str, response_time_ms: float,
                     dom_elements: int, status: str) -> Optional[dict]:
    """
    Statistical anomaly detection. Returns an anomaly dict if triggered, else None.
    """
    try:
        conn = _get_conn()

        # ── Response time z-score ────────────────────────────────────────────
        metrics = conn.execute(
            """SELECT response_time_ms FROM metrics
               WHERE site_id = ? AND response_time_ms > 0
               ORDER BY timestamp DESC LIMIT 200""",
            (site_id,),
        ).fetchall()
        times = [r["response_time_ms"] for r in metrics if r["response_time_ms"] > 0]

        if len(times) >= 10 and response_time_ms > 0:
            mean = sum(times) / len(times)
            variance = sum((t - mean) ** 2 for t in times) / len(times)
            std = math.sqrt(variance) if variance > 0 else 1.0
            z = (response_time_ms - mean) / std

            if z > Z_SCORE_THRESHOLD:
                conn.close()
                return {
                    "metric_type": "response_time",
                    "z_score": round(z, 2),
                    "baseline_mean": round(mean, 2),
                    "baseline_std": round(std, 2),
                    "observed_value": response_time_ms,
                    "severity": _severity_from_z(z),
                }

        # ── DOM element count drop ────────────────────────────────────────────
        dom_metrics = conn.execute(
            """SELECT dom_elements FROM metrics
               WHERE site_id = ? AND dom_elements > 0
               ORDER BY timestamp DESC LIMIT 50""",
            (site_id,),
        ).fetchall()
        dom_vals = [r["dom_elements"] for r in dom_metrics if r["dom_elements"] > 0]

        if len(dom_vals) >= 5 and dom_elements > 0:
            baseline_dom = sum(dom_vals) / len(dom_vals)
            drop_pct = (baseline_dom - dom_elements) / baseline_dom
            if drop_pct > DOM_DROP_THRESHOLD:
                conn.close()
                return {
                    "metric_type": "dom_elements",
                    "z_score": None,
                    "baseline_mean": round(baseline_dom, 1),
                    "baseline_std": None,
                    "observed_value": dom_elements,
                    "severity": "medium" if drop_pct < 0.5 else "high",
                }

        # ── Error rate over last N checks ─────────────────────────────────────
        recent_checks = conn.execute(
            """SELECT status FROM checks
               WHERE site_id = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (site_id, ERROR_RATE_WINDOW),
        ).fetchall()
        conn.close()

        if len(recent_checks) >= ERROR_RATE_WINDOW:
            fail_count = sum(1 for r in recent_checks if r["status"] == "FAILED")
            error_rate = fail_count / len(recent_checks)
            if error_rate >= ERROR_RATE_THRESHOLD:
                return {
                    "metric_type": "error_rate",
                    "z_score": None,
                    "baseline_mean": 0,
                    "baseline_std": None,
                    "observed_value": round(error_rate, 2),
                    "severity": "high" if error_rate >= 0.8 else "medium",
                }

        return None

    except Exception as e:
        print(f"ERROR: Anomaly Stage 1 failed for {site_id}: {e}")
        return None


async def run_stage2(site_id: str, check_id: str, anomaly: dict, site_name: str, screenshot_path: str = None) -> str:
    """
    Gemma interprets the statistical anomaly. Returns interpretation text.
    Also writes to anomaly_events and optionally queues for HITL.
    """
    from services.ai_service import ai_service
    from services.catalogue_service import ingest as catalogue_ingest

    metric_type = anomaly.get("metric_type", "unknown")
    severity = anomaly.get("severity", "low")

    # Build a concise prompt for Gemma
    visual_context = ""
    images = []
    if screenshot_path:
        encoded = ai_service._encode_image(screenshot_path)
        if encoded:
            images.append(encoded)
            visual_context = "I have uploaded a screenshot of the site during this anomaly for your visual context."

    prompt = f"""You are an infrastructure monitoring AI. A statistical anomaly was detected.
{visual_context}

Site: {site_name}
Metric: {metric_type}
Observed value: {anomaly.get('observed_value')}
Baseline average: {anomaly.get('baseline_mean')}
Z-score: {anomaly.get('z_score', 'N/A')}
Severity: {severity}

In 2-3 sentences, explain what this likely means and suggest one concrete action.
Respond as JSON: {{"interpretation": "...", "suggested_action": "...", "confidence": 0.0-1.0}}"""

    try:
        raw = await ai_service._call_ollama(prompt, images=images)
        parsed = _parse_gemma_json(raw)
        interpretation = parsed.get("interpretation", raw[:200] if raw else "Anomaly detected")
        confidence = float(parsed.get("confidence", 0.6))
        suggested_action = parsed.get("suggested_action", "")
    except Exception as e:
        print(f"WARNING: Gemma Stage 2 failed: {e}")
        interpretation = f"Statistical anomaly detected in {metric_type}"
        confidence = 0.5
        suggested_action = "Investigate recent changes to this service"

    # Persist anomaly event
    event_id = _write_anomaly_event(
        site_id, check_id, anomaly, interpretation, severity
    )

    # Route to HITL catalogue if confidence is high enough
    rca = {
        "category": f"Anomaly:{metric_type}",
        "probable_cause": interpretation,
        "repair_action": suggested_action,
        "confidence": confidence,
    }
    await catalogue_ingest(rca, check_id, confidence)

    return interpretation


def _write_anomaly_event(site_id, check_id, anomaly, interpretation, severity) -> str:
    event_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """INSERT INTO anomaly_events
           (id, site_id, check_id, z_score, metric_type, baseline_mean, baseline_std,
            observed_value, gemma_interpretation, severity)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event_id, site_id, check_id,
            anomaly.get("z_score"),
            anomaly.get("metric_type"),
            anomaly.get("baseline_mean"),
            anomaly.get("baseline_std"),
            anomaly.get("observed_value"),
            interpretation,
            severity,
        ),
    )
    conn.commit()
    conn.close()
    return event_id


def get_recent_anomalies(site_id: str = None, limit: int = 20) -> list[dict]:
    conn = _get_conn()
    if site_id:
        rows = conn.execute(
            "SELECT * FROM anomaly_events WHERE site_id = ? ORDER BY created_at DESC LIMIT ?",
            (site_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM anomaly_events ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _severity_from_z(z: float) -> str:
    if z > 6:
        return "critical"
    elif z > 4.5:
        return "high"
    elif z > 3:
        return "medium"
    return "low"


def _parse_gemma_json(raw: str) -> dict:
    if not raw:
        return {}
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(raw[start:end])
    except Exception:
        pass
    return {}

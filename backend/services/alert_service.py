"""
Alert service: email notifications via aiosmtplib.
Implements per-tier logic, per-site cooldown, and incident bypass.
"""
import sqlite3
import uuid
import os
from datetime import datetime, timedelta
from typing import Optional

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from services.sqlite_service import DB_PATH

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


def _get_alert_config() -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM alert_config WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else {}


def _is_on_cooldown(site_id: str, alert_type: str, cooldown_minutes: int) -> bool:
    """Check if a non-incident alert for this site was sent within the cooldown window."""
    if alert_type == "incident":
        return False  # Incidents always bypass cooldown
    cutoff = (datetime.now() - timedelta(minutes=cooldown_minutes)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        """SELECT id FROM alert_log
           WHERE site_id = ? AND alert_type = ? AND sent_at > ? AND status = 'sent'""",
        (site_id, alert_type, cutoff),
    ).fetchone()
    conn.close()
    return row is not None


def _log_alert(site_id: Optional[str], incident_id: Optional[str],
               alert_type: str, recipient: str, status: str = "sent"):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO alert_log (id, site_id, incident_id, alert_type, recipient_email, status) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), site_id, incident_id, alert_type, recipient, status),
    )
    conn.commit()
    conn.close()


async def _send_email(config: dict, subject: str, html_body: str, recipient: Optional[str] = None):
    """Low-level async email send via aiosmtplib."""
    to_email = recipient or config.get("recipient_email")
    if not to_email or not config.get("smtp_host"):
        print("WARNING: Email not configured (missing smtp_host or recipient_email)")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.get("smtp_user", "gemmawatch@localhost")
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=config["smtp_host"],
            port=int(config.get("smtp_port", 587)),
            username=config.get("smtp_user"),
            password=config.get("smtp_password"),
            start_tls=True,
        )
        return True
    except Exception as e:
        print(f"ERROR: Email send failed: {e}")
        return False


# ── Alert triggers ────────────────────────────────────────────────────────────
async def alert_failure(site_id: str, site_name: str, site_url: str,
                        consecutive_failures: int) -> bool:
    """Called when a site has N consecutive failures."""
    config = _get_alert_config()
    if not config.get("enabled") or not config.get("alert_on_failure"):
        return False
    threshold = int(config.get("consecutive_failures_threshold", 2))
    if consecutive_failures < threshold:
        return False
    if _is_on_cooldown(site_id, "failure", config.get("cooldown_minutes", 30)):
        print(f"INFO: Alert suppressed (cooldown) for {site_name}")
        return False

    subject = f"🚨 GemmaWatch: {site_name} is FAILING"
    body = _failure_email_body(site_name, site_url, consecutive_failures)
    ok = await _send_email(config, subject, body)
    _log_alert(site_id, None, "failure", config.get("recipient_email", ""), "sent" if ok else "failed")
    return ok


async def alert_anomaly(site_id: str, site_name: str, interpretation: str, severity: str) -> bool:
    """Called when Stage 2 anomaly detection triggers."""
    config = _get_alert_config()
    if not config.get("enabled") or not config.get("alert_on_anomaly"):
        return False

    severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    min_sev = config.get("min_severity", "medium")
    if severity_order.get(severity, 0) < severity_order.get(min_sev, 1):
        return False

    if _is_on_cooldown(site_id, "anomaly", config.get("cooldown_minutes", 30)):
        return False

    subject = f"⚠️ GemmaWatch: Anomaly detected on {site_name} [{severity.upper()}]"
    body = _anomaly_email_body(site_name, interpretation, severity)
    ok = await _send_email(config, subject, body)
    _log_alert(site_id, None, "anomaly", config.get("recipient_email", ""), "sent" if ok else "failed")
    return ok


async def alert_incident(incident: dict) -> bool:
    """Called when a new Incident is created. Bypasses cooldown."""
    config = _get_alert_config()
    if not config.get("enabled") or not config.get("alert_on_incident"):
        return False

    subject = f"🔴 GemmaWatch INCIDENT [{incident['severity'].upper()}]: {incident['title']}"
    body = _incident_email_body(incident)
    ok = await _send_email(config, subject, body)
    _log_alert(None, incident["id"], "incident", config.get("recipient_email", ""), "sent" if ok else "failed")
    return ok


async def send_test_email(recipient: str) -> bool:
    """Send a test email to verify SMTP config."""
    config = _get_alert_config()
    subject = "✅ GemmaWatch — Test Alert"
    body = _base_email("Test Alert", "<p>Your GemmaWatch alert configuration is working correctly.</p>")
    return await _send_email(config, subject, body, recipient)


# ── Config CRUD ───────────────────────────────────────────────────────────────
def get_config() -> dict:
    config = _get_alert_config()
    # Never expose SMTP password in API responses
    config.pop("smtp_password", None)
    return config


def update_config(updates: dict) -> bool:
    conn = sqlite3.connect(DB_PATH)
    fields = ["recipient_email", "smtp_host", "smtp_port", "smtp_user", "smtp_password",
              "enabled", "min_severity", "cooldown_minutes", "alert_on_failure",
              "consecutive_failures_threshold", "alert_on_anomaly", "alert_on_incident"]
    set_clauses = []
    values = []
    for f in fields:
        if f in updates:
            set_clauses.append(f"{f} = ?")
            values.append(updates[f])
    if not set_clauses:
        conn.close()
        return False
    set_clauses.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(1)  # WHERE id = 1
    conn.execute(f"UPDATE alert_config SET {', '.join(set_clauses)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return True


# ── Email templates ───────────────────────────────────────────────────────────
def _base_email(title: str, content: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #050510; color: #e2e8f0; margin: 0; padding: 20px; }}
  .card {{ background: #0a0a1a; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 24px; max-width: 560px; margin: 0 auto; }}
  h2 {{ color: #60a5fa; margin-top: 0; }}
  .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }}
  .critical {{ background: #7f1d1d; color: #fca5a5; }}
  .high {{ background: #78350f; color: #fcd34d; }}
  .medium {{ background: #1e3a5f; color: #93c5fd; }}
  .low {{ background: #14532d; color: #86efac; }}
  a.btn {{ display: inline-block; background: #2563eb; color: #fff; padding: 10px 20px; border-radius: 8px; text-decoration: none; margin-top: 16px; }}
  hr {{ border-color: rgba(255,255,255,0.1); }}
  .footer {{ font-size: 11px; color: #475569; margin-top: 16px; }}
</style></head>
<body><div class="card">
  <h2>GemmaWatch AI</h2>
  <h3>{title}</h3>
  {content}
  <hr>
  <div class="footer">GemmaWatch — AI-powered monitoring<br>
  <a href="{FRONTEND_BASE_URL}" style="color:#60a5fa">Open Dashboard →</a></div>
</div></body></html>"""


def _failure_email_body(site_name: str, url: str, consecutive: int) -> str:
    content = f"""
    <p>Site <strong>{site_name}</strong> has failed <strong>{consecutive} consecutive checks</strong>.</p>
    <p>URL: <a href="{url}" style="color:#60a5fa">{url}</a></p>
    <a href="{FRONTEND_BASE_URL}" class="btn">View Dashboard →</a>"""
    return _base_email(f"🚨 {site_name} is FAILING", content)


def _anomaly_email_body(site_name: str, interpretation: str, severity: str) -> str:
    content = f"""
    <p>An anomaly was detected on <strong>{site_name}</strong>.</p>
    <p>Severity: <span class="badge {severity}">{severity.upper()}</span></p>
    <p><em>{interpretation}</em></p>
    <a href="{FRONTEND_BASE_URL}" class="btn">Investigate →</a>"""
    return _base_email(f"⚠️ Anomaly: {site_name}", content)


def _incident_email_body(incident: dict) -> str:
    sites = ", ".join(incident.get("affected_site_names", incident.get("affected_site_ids", [])))
    sev = incident.get("severity", "medium")
    content = f"""
    <p><span class="badge {sev}">{sev.upper()}</span></p>
    <p><strong>{incident['title']}</strong></p>
    <p><strong>Affected sites:</strong> {sites}</p>
    <p><strong>Probable shared cause:</strong><br><em>{incident.get('probable_shared_cause', 'Under investigation')}</em></p>
    <a href="{FRONTEND_BASE_URL}/incidents" class="btn">View Incident →</a>"""
    return _base_email("🔴 Incident Detected", content)

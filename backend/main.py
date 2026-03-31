from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
import uvicorn
import json
import os
from dotenv import load_dotenv
import uuid
import asyncio
from datetime import datetime
from typing import Optional

# Load environment variables from .env file
load_dotenv()

from services.scraper import scraper_service
from services.ai_service import ai_service
from services.sqlite_service import SQLiteService
from services.check_types import CheckType, CheckConfig, CheckExecutor
from services.auth_service import (
    get_current_user, get_optional_user, require_admin,
    get_google_auth_url, exchange_google_code,
    get_github_auth_url, exchange_github_code,
    find_or_create_user, store_refresh_token,
    create_access_token, create_refresh_token,
    FRONTEND_BASE_URL, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
)
from services.scheduler_service import scheduler_service
import services.catalogue_service as catalogue_service
import services.anomaly_service as anomaly_service
import services.correlation_service as correlation_service
import services.alert_service as alert_service
import services.chat_service as chat_service

# Configuration
WS_TIMEOUT = 30.0
SCREENSHOT_DIRS = ("screenshots/baselines", "screenshots/currents")

app = FastAPI(
    title="GemmaWatch AI API",
    description="AI-powered website monitoring platform with visual analysis and root cause identification",
    version="2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS — allow credentials for cookie-based auth
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_BASE_URL, "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup screenshot directories
for dir_path in SCREENSHOT_DIRS:
    os.makedirs(dir_path, exist_ok=True)
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")

# Initialize services
db_service = SQLiteService()


@app.on_event("startup")
async def startup_event():
    print("INFO: GemmaWatch backend started with SQLite persistence")
    scheduler_service.set_monitor_fn(run_monitoring_task)
    scheduler_service.start()
    # Check embedding model availability
    from services.embedding_service import check_embed_model_available
    asyncio.create_task(check_embed_model_available())


@app.on_event("shutdown")
async def shutdown_event():
    scheduler_service.stop()


# ── WebSocket Manager ─────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()
baselines = {}


# ═══════════════════════════════════════════════════════════════════════════════
# ── Core monitoring task ──────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
async def run_monitoring_task(url: str, name: str, site_id: str, check_type: str = "http"):
    check_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    print(f"DEBUG: run_monitoring_task STARTED - name={name}, url={url}, site_id={site_id}, check_type={check_type}")

    await manager.broadcast({
        "type": "status",
        "msg": f"🔍 Starting {check_type.upper()} check for {name}",
        "check_id": check_id
    })

    response_time_ms = 0.0
    dom_elements = 0
    final_status = "SUCCESS"

    if check_type.lower() == "http":
        result = await scraper_service.run_check(url, site_id)
        if "error" in result:
            await manager.broadcast({"type": "error", "msg": result["error"], "check_id": check_id})
            return

        current_dom = result["dom"]
        status_code = result.get("status_code", 200)
        console_logs = result.get("console_logs", [])
        network_errors = result.get("network_errors", [])
        is_failed = status_code >= 400 or status_code == 0

        screenshot_path = result.get("screenshot", "")
        screenshot_url = f"/screenshots/{'/'.join(screenshot_path.split('/')[1:])}" if screenshot_path else ""

        dom_elements = len(json.loads(current_dom)) if current_dom else 0
        await manager.broadcast({
            "type": "status",
            "msg": f"📸 Captured screenshot (HTTP {status_code}), distilled DOM with {dom_elements} interactive elements.",
            "check_id": check_id
        })

        # Visual regression
        visual_analysis = None
        if not result["is_new_baseline"] and site_id in baselines:
            baseline_dom = baselines[site_id]
            if current_dom != baseline_dom:
                await manager.broadcast({"type": "status", "msg": "🔬 UI Change detected. Analyzing with Gemma...", "check_id": check_id})
                visual_analysis = await ai_service.analyze_visual_change(baseline_dom, current_dom)
                if isinstance(visual_analysis, str):
                    try:
                        visual_analysis = json.loads(visual_analysis)
                    except json.JSONDecodeError:
                        visual_analysis = None
        baselines[site_id] = current_dom

        # RCA
        rca = None
        if is_failed or len(network_errors) > 0:
            error_context = f"HTTP {status_code}"
            if network_errors:
                error_context += f" | {len(network_errors)} network failure(s)"
            await manager.broadcast({"type": "status", "msg": f"🧠 Analyzing failure with Gemma ({error_context})...", "check_id": check_id})
            rca = await ai_service.analyze_failure(current_dom, console_logs, network_errors, error_context)
            if isinstance(rca, str):
                try:
                    rca = json.loads(rca)
                except json.JSONDecodeError:
                    start_idx = rca.find('{')
                    end_idx = rca.rfind('}') + 1
                    if start_idx != -1 and end_idx > start_idx:
                        try:
                            rca = json.loads(rca[start_idx:end_idx])
                        except Exception:
                            rca = None
                    else:
                        rca = None
            if isinstance(rca, dict) and "error" in rca:
                rca = None
            if rca and isinstance(rca, dict):
                rca.setdefault("probable_cause", error_context)
                rca.setdefault("confidence", 0.6)
                rca.setdefault("repair_action", "Check logs for error details")
                rca.setdefault("category", "Unknown")
            else:
                rca = {"probable_cause": error_context, "confidence": 0.4,
                       "repair_action": "Review console logs and network errors", "category": "Unknown"}

        final_status = "FAILED" if is_failed or (visual_analysis and visual_analysis.get("is_regression")) else "SUCCESS"

        await db_service.create_check(site_id, check_id, final_status, timestamp, screenshot_url,
                                      status_code, console_logs, network_errors)
        await db_service.log_metric(site_id, check_id, response_time_ms=0,
                                    dom_elements=dom_elements, console_errors=len(console_logs),
                                    network_failures=len(network_errors))

        if rca and isinstance(rca, dict):
            confidence = float(rca.get("confidence", 0.5))
            await db_service.create_root_cause(check_id, rca.get("probable_cause", ""), confidence, rca.get("repair_action", ""))
            # HITL catalogue pipeline
            asyncio.create_task(catalogue_service.ingest(rca, check_id, confidence))

        await manager.broadcast({
            "type": "result", "site_id": site_id, "check_id": check_id,
            "name": name, "url": url, "status": final_status, "status_code": status_code,
            "rca": rca, "visual_analysis": visual_analysis, "timestamp": timestamp,
            "screenshot": screenshot_url, "is_visual_change": visual_analysis is not None,
            "console_logs": console_logs, "network_errors": network_errors,
            "console_log_count": len(console_logs), "network_error_count": len(network_errors)
        })

    else:
        # API / DNS / TCP checks
        try:
            import time
            t0 = time.monotonic()
            config = CheckConfig(CheckType(check_type), url)
            result = await CheckExecutor.execute(config)
            response_time_ms = (time.monotonic() - t0) * 1000

            is_success = result.get("is_success", False)
            final_status = "SUCCESS" if is_success else "FAILED"
            status_code = result.get("status_code", 0)

            await manager.broadcast({
                "type": "status",
                "msg": f"✅ {check_type.upper()} check completed with status: {final_status}",
                "check_id": check_id
            })
            await db_service.create_check(site_id, check_id, final_status, timestamp, "", status_code, [], [])
            await db_service.log_metric(site_id, check_id, response_time_ms=response_time_ms,
                                        dom_elements=0, console_errors=0, network_failures=0)
            await manager.broadcast({
                "type": "result", "site_id": site_id, "check_id": check_id,
                "name": name, "url": url, "check_type": check_type,
                "status": final_status, "status_code": status_code,
                "details": result, "timestamp": timestamp,
            })
        except Exception as e:
            final_status = "FAILED"
            await manager.broadcast({"type": "error", "msg": f"Error executing {check_type} check: {str(e)}", "check_id": check_id})

    # ── Post-check intelligence pipeline ──────────────────────────────────────
    asyncio.create_task(_post_check_pipeline(site_id, check_id, name, final_status, response_time_ms, dom_elements))


async def _post_check_pipeline(site_id: str, check_id: str, site_name: str,
                                final_status: str, response_time_ms: float, dom_elements: int):
    """Runs anomaly detection, correlation, and alerting after every check."""
    try:
        # Stage 1: Statistical anomaly detection
        anomaly = await anomaly_service.run_stage1(site_id, check_id, response_time_ms, dom_elements, final_status)
        if anomaly:
            # Stage 2: Gemma interpretation (async, non-blocking)
            interpretation = await anomaly_service.run_stage2(site_id, check_id, anomaly, site_name)
            # Alert on anomaly
            asyncio.create_task(alert_service.alert_anomaly(
                site_id, site_name, interpretation, anomaly.get("severity", "low")
            ))

        # Cross-site correlation → Incidents
        incident = await correlation_service.check_and_create_incident(site_id, final_status)
        if incident:
            asyncio.create_task(alert_service.alert_incident(incident))

        # Consecutive failure alerting
        if final_status == "FAILED":
            asyncio.create_task(_check_consecutive_failures(site_id, site_name))

    except Exception as e:
        print(f"ERROR: Post-check pipeline failed for {site_id}: {e}")


async def _check_consecutive_failures(site_id: str, site_name: str):
    import sqlite3
    conn = sqlite3.connect(db_service.DB_PATH if hasattr(db_service, 'DB_PATH') else "gemmawatch.db")
    from services.sqlite_service import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT status FROM checks WHERE site_id = ? ORDER BY timestamp DESC LIMIT 5", (site_id,)
    ).fetchall()
    conn.close()
    statuses = [r[0] for r in rows]
    consecutive = 0
    for s in statuses:
        if s == "FAILED":
            consecutive += 1
        else:
            break

    # Fetch site URL for the alert
    import sqlite3 as sq
    from services.sqlite_service import DB_PATH
    c2 = sq.connect(DB_PATH)
    site = c2.execute("SELECT url FROM sites WHERE id = ?", (site_id,)).fetchone()
    c2.close()
    site_url = site[0] if site else ""

    await alert_service.alert_failure(site_id, site_name, site_url, consecutive)


# ═══════════════════════════════════════════════════════════════════════════════
# ── Auth routes ───────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/auth/google/login", tags=["auth"])
async def google_login():
    return RedirectResponse(get_google_auth_url())


@app.get("/auth/google/callback", tags=["auth"])
async def google_callback(code: str, response: Response):
    user_info = await exchange_google_code(code)
    user = await find_or_create_user(
        db_service,
        provider="google",
        provider_id=str(user_info.get("sub", user_info.get("id", ""))),
        email=user_info.get("email", ""),
        name=user_info.get("name", ""),
        avatar_url=user_info.get("picture", ""),
    )
    return _complete_oauth(response, user)


@app.get("/auth/github/login", tags=["auth"])
async def github_login(response: Response):
    state = str(uuid.uuid4())
    # Store state in a secure cookie for CSRF validation (optional but recommended)
    response.set_cookie("oauth_state", state, max_age=600, secure=False, httponly=True, samesite="lax")
    return RedirectResponse(get_github_auth_url(state=state))


@app.get("/auth/github/callback", tags=["auth"])
async def github_callback(code: str, response: Response):
    user_info = await exchange_github_code(code)
    user = await find_or_create_user(
        db_service,
        provider="github",
        provider_id=str(user_info.get("id", "")),
        email=user_info.get("email", "") or "",
        name=user_info.get("name", user_info.get("login", "")),
        avatar_url=user_info.get("avatar_url", ""),
    )
    return _complete_oauth(response, user)


def _complete_oauth(response: Response, user: dict):
    access_token = create_access_token(user["id"], user["email"], user["role"])
    raw_refresh, refresh_hash = create_refresh_token(user["id"])
    import asyncio
    asyncio.create_task(store_refresh_token(db_service, user["id"], refresh_hash))

    redirect = RedirectResponse(url=f"{FRONTEND_BASE_URL}/dashboard")
    max_age = REFRESH_TOKEN_EXPIRE_DAYS * 86400
    redirect.set_cookie("access_token", access_token, httponly=True, samesite="lax",
                        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, secure=False)
    redirect.set_cookie("refresh_token", raw_refresh, httponly=True, samesite="lax",
                        max_age=max_age, secure=False)
    return redirect


@app.post("/auth/logout", tags=["auth"])
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@app.get("/auth/me", tags=["auth"])
async def me(request: Request):
    user = await get_optional_user(request)
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}


# ═══════════════════════════════════════════════════════════════════════════════
# ── Existing routes (unchanged) ───────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/", tags=["info"])
async def root():
    return {"status": "online", "engine": "GemmaWatch AI", "version": "2.0", "db": "SQLite"}


@app.get("/health", tags=["info"])
async def health_check():
    try:
        ollama_status = await ai_service.check_connection()
        return {"status": "healthy", "gemma_available": ollama_status}
    except Exception as e:
        return {"status": "degraded", "gemma_available": False, "message": str(e)}


@app.post("/monitor", tags=["monitoring"])
async def monitor_site(url: str, name: str, check_type: str = "http", background_tasks: BackgroundTasks = None):
    site_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
    await db_service.create_site(name, url, site_id, check_type)
    background_tasks.add_task(run_monitoring_task, url, name, site_id, check_type)
    # Reset scheduling timestamps after a manual trigger
    asyncio.create_task(scheduler_service.reset_schedule(site_id))
    return {"message": "Monitoring task started", "site_id": site_id, "check_type": check_type}


@app.get("/sites", tags=["sites"])
async def list_sites():
    sites = await db_service.get_all_sites()
    return {"sites": sites}


@app.get("/sites/{site_id}/history", tags=["check-history"])
async def get_site_history(site_id: str, limit: int = 10):
    history = await db_service.get_checks_by_site(site_id)
    return {"history": history[:limit]}


@app.delete("/sites/{site_id}", tags=["sites"])
async def delete_site(site_id: str, user: dict = Depends(get_current_user)):
    await db_service.delete_site(site_id)
    return {"message": "Site deleted"}


@app.patch("/sites/{site_id}/frequency", tags=["scheduler"])
async def update_frequency(site_id: str, frequency: int, user: dict = Depends(require_admin)):
    import sqlite3
    from services.sqlite_service import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE sites SET frequency = ? WHERE id = ?", (frequency, site_id))
    conn.commit()
    conn.close()
    return {"site_id": site_id, "frequency": frequency}


@app.get("/sites/{site_id}/metrics", tags=["analytics"])
async def get_site_metrics(site_id: str, limit: int = 50):
    metrics = await db_service.get_site_metrics(site_id, limit)
    return {"metrics": metrics}


@app.get("/sites/{site_id}/uptime", tags=["analytics"])
async def get_site_uptime(site_id: str, days: int = 7):
    uptime = await db_service.get_uptime_percentage(site_id, days)
    return {"site_id": site_id, "uptime_percentage": uptime, "days": days}


@app.get("/analytics/summary", tags=["analytics"])
async def get_analytics_summary():
    sites = await db_service.get_all_sites()
    summary = {"total_sites": len(sites), "sites_data": []}
    for site in sites:
        uptime = await db_service.get_uptime_percentage(site["id"], 7)
        metrics = await db_service.get_site_metrics(site["id"], 1)
        summary["sites_data"].append({
            "site_id": site["id"], "name": site["name"],
            "uptime_7d": uptime, "latest_status": metrics[0] if metrics else None
        })
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# ── Catalogue routes ──────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/catalogue/pending", tags=["catalogue"])
async def get_pending_catalogue(user: dict = Depends(require_admin)):
    return {"entries": catalogue_service.get_pending()}


@app.post("/catalogue/{entry_id}/approve", tags=["catalogue"])
async def approve_catalogue_entry(entry_id: str, body: dict = {}, user: dict = Depends(require_admin)):
    edited_rca = body.get("edited_rca")
    result = await catalogue_service.approve(entry_id, user["sub"], edited_rca)
    return {"success": True, **result}


@app.post("/catalogue/{entry_id}/reject", tags=["catalogue"])
async def reject_catalogue_entry(entry_id: str, body: dict = {}, user: dict = Depends(require_admin)):
    note = body.get("note", "")
    await catalogue_service.reject(entry_id, user["sub"], note)
    return {"success": True}


@app.get("/catalogue/approved", tags=["catalogue"])
async def get_approved_catalogue(user: dict = Depends(require_admin)):
    return {"entries": catalogue_service.get_approved()}


@app.get("/catalogue/shadow", tags=["catalogue"])
async def get_shadow_catalogue(user: dict = Depends(require_admin)):
    return {"entries": catalogue_service.get_shadow()}


# ═══════════════════════════════════════════════════════════════════════════════
# ── Incidents routes ──────────────────────────────════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/incidents", tags=["incidents"])
async def get_incidents(status: Optional[str] = None):
    """Public — read-only for unauthenticated users."""
    return {"incidents": correlation_service.get_incidents(status)}


@app.get("/incidents/{incident_id}", tags=["incidents"])
async def get_incident(incident_id: str):
    inc = correlation_service.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc["notes"] = correlation_service.get_incident_notes(incident_id)
    return inc


@app.post("/incidents/{incident_id}/resolve", tags=["incidents"])
async def resolve_incident(incident_id: str, user: dict = Depends(require_admin)):
    correlation_service.resolve_incident(incident_id, user["sub"])
    return {"success": True}


@app.post("/incidents/{incident_id}/notes", tags=["incidents"])
async def add_incident_note(incident_id: str, body: dict, user: dict = Depends(get_current_user)):
    note_id = correlation_service.add_incident_note(incident_id, user["sub"], body.get("note", ""))
    return {"note_id": note_id}


# ═══════════════════════════════════════════════════════════════════════════════
# ── Anomaly routes ────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/anomalies", tags=["anomalies"])
async def get_anomalies(site_id: Optional[str] = None, limit: int = 20):
    return {"anomalies": anomaly_service.get_recent_anomalies(site_id, limit)}


# ═══════════════════════════════════════════════════════════════════════════════
# ── Alert config routes ───────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/settings/alerts", tags=["settings"])
async def get_alert_settings(user: dict = Depends(require_admin)):
    return alert_service.get_config()


@app.put("/settings/alerts", tags=["settings"])
async def update_alert_settings(body: dict, user: dict = Depends(require_admin)):
    alert_service.update_config(body)
    return {"success": True}


@app.post("/settings/alerts/test", tags=["settings"])
async def test_alert(body: dict, user: dict = Depends(require_admin)):
    recipient = body.get("email", user.get("email", ""))
    ok = await alert_service.send_test_email(recipient)
    return {"success": ok}


# ═══════════════════════════════════════════════════════════════════════════════
# ── Chat routes ───────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/chat", tags=["chat"])
async def chat_query(body: dict, user: dict = Depends(get_current_user)):
    query = body.get("query", "").strip()
    session_id = body.get("session_id", str(uuid.uuid4()))
    result = await chat_service.chat(query, session_id, user.get("sub"))
    return {**result, "session_id": session_id}


@app.get("/chat/history/{session_id}", tags=["chat"])
async def get_chat_history(session_id: str, user: dict = Depends(get_current_user)):
    return {"messages": chat_service.get_chat_history(session_id)}


# ═══════════════════════════════════════════════════════════════════════════════
# ── Scheduler status route ────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/scheduler/status", tags=["scheduler"])
async def scheduler_status(user: dict = Depends(require_admin)):
    import sqlite3
    from services.sqlite_service import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, check_type, frequency, last_checked_at, next_check_at FROM sites"
    ).fetchall()
    conn.close()
    return {"sites": [dict(r) for r in rows]}


# ═══════════════════════════════════════════════════════════════════════════════
# ── WebSocket ─────────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
@app.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await manager.connect(websocket)
        await websocket.send_json({"type": "status", "msg": "Connected to GemmaWatch"})
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=WS_TIMEOUT)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        try:
            manager.disconnect(websocket)
        except Exception:
            pass

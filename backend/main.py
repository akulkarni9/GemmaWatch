from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import os
import uuid
import asyncio
from datetime import datetime
from services.scraper import scraper_service
from services.ai_service import ai_service
from services.sqlite_service import SQLiteService
from services.check_types import CheckType, CheckConfig, CheckExecutor

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

# CORS configuration for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup screenshot directories
for dir_path in SCREENSHOT_DIRS:
    os.makedirs(dir_path, exist_ok=True)
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")

# Initialize SQLite service
db_service = SQLiteService()

@app.on_event("startup")
async def startup_event():
    print("INFO: GemmaWatch backend started with SQLite persistence")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"DEBUG: WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSocket clients, cleaning up disconnected ones."""
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


@app.get("/", tags=["info"])
async def root():
    """Get API status and version information."""
    return {"status": "online", "engine": "GemmaWatch AI", "version": "2.0", "db": "SQLite"}


@app.get("/health", tags=["info"])
async def health_check():
    """Health check endpoint - verifies Ollama connection for Gemma."""
    try:
        ollama_status = await ai_service.check_connection()
        return {
            "status": "healthy",
            "gemma_available": ollama_status,
            "message": "Ollama is connected and Gemma is available" if ollama_status else "Ollama not responding - Gemma analysis unavailable"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "gemma_available": False,
            "message": f"Ollama connection error: {str(e)}. Make sure Ollama is running with: ollama run gemma"
        }


async def run_monitoring_task(url: str, name: str, site_id: str, check_type: str = "http"):
    check_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    print(f"DEBUG: run_monitoring_task STARTED - name={name}, url={url}, site_id={site_id}, check_type={check_type}")

    await manager.broadcast({
        "type": "status",
        "msg": f"🔍 Starting {check_type.upper()} check for {name}",
        "check_id": check_id
    })

    # Handle different check types
    if check_type.lower() == "http":
        # Original HTTP/Web monitoring flow
        # 1. Scraper & Visual Capture
        result = await scraper_service.run_check(url, site_id)
        if "error" in result:
            await manager.broadcast({
                "type": "error",
                "msg": result["error"],
                "check_id": check_id
            })
            return

        current_dom = result["dom"]
        status_code = result.get("status_code", 200)
        console_logs = result.get("console_logs", [])
        network_errors = result.get("network_errors", [])

        # Proper failure detection via HTTP status code
        is_failed = status_code >= 400 or status_code == 0

        # Convert screenshot path to a serveable URL
        screenshot_path = result.get("screenshot", "")
        screenshot_url = f"/screenshots/{'/'.join(screenshot_path.split('/')[1:])}" if screenshot_path else ""

        await manager.broadcast({
            "type": "status",
            "msg": f"📸 Captured screenshot (HTTP {status_code}), distilled DOM with {len(json.loads(current_dom))} interactive elements.",
            "check_id": check_id
        })

        # 2. Visual Regression Logic
        visual_analysis = None
        if not result["is_new_baseline"] and site_id in baselines:
            baseline_dom = baselines[site_id]
            if current_dom != baseline_dom:
                await manager.broadcast({
                    "type": "status",
                    "msg": "🔬 UI Change detected. Analyzing visual impact with Gemma...",
                    "check_id": check_id
                })
                visual_analysis = await ai_service.analyze_visual_change(baseline_dom, current_dom)
                if isinstance(visual_analysis, str):
                    try:
                        visual_analysis = json.loads(visual_analysis)
                    except json.JSONDecodeError:
                        visual_analysis = None

        baselines[site_id] = current_dom

        # 3. RCA if failed
        rca = None
        if is_failed or len(network_errors) > 0:
            error_context = f"HTTP {status_code}"
            if network_errors:
                error_context += f" | {len(network_errors)} network failure(s)"

            await manager.broadcast({
                "type": "status",
                "msg": f"🧠 Analyzing failure with Gemma ({error_context})...",
                "check_id": check_id
            })
            rca = await ai_service.analyze_failure(current_dom, console_logs, network_errors, error_context)
            print(f"DEBUG: RCA response type: {type(rca)}, value: {rca}")
            
            if isinstance(rca, str):
                try:
                    rca = json.loads(rca)
                except json.JSONDecodeError as e:
                    print(f"DEBUG: JSON parse error - {e}, trying to extract...")
                    # Try to extract JSON from the response if it's wrapped in text
                    try:
                        start_idx = rca.find('{')
                        end_idx = rca.rfind('}') + 1
                        if start_idx != -1 and end_idx > start_idx:
                            json_str = rca[start_idx:end_idx]
                            print(f"DEBUG: Extracted JSON: {json_str}")
                            rca = json.loads(json_str)
                        else:
                            print(f"DEBUG: No JSON braces found")
                            rca = None
                    except Exception as extract_error:
                        print(f"DEBUG: JSON extraction failed - {extract_error}")
                        rca = None
            elif isinstance(rca, dict) and "error" in rca:
                print(f"DEBUG: Gemma error: {rca['error']}")
                rca = None
            
            # Ensure rca has all required fields with smart fallbacks
            if rca and isinstance(rca, dict):
                rca.setdefault("probable_cause", error_context or "Unknown error detected")
                rca.setdefault("confidence", 0.6)
                rca.setdefault("repair_action", "Check logs for error details")
                rca.setdefault("category", "Unknown")
            else:
                rca = {
                    "probable_cause": error_context or "Unexpected failure",
                    "confidence": 0.4,
                    "repair_action": "Review console logs and network errors above for details",
                    "category": "Unknown"
                }

        # 4. Determine final status
        # Determine final status
        final_status = "FAILED" if is_failed or (visual_analysis and visual_analysis.get("is_regression")) else "SUCCESS"

        # Persist monitoring results to SQLite (site is already created in the /monitor endpoint)
        await db_service.create_check(
            site_id, check_id, final_status, timestamp, screenshot_url, 
            status_code, console_logs, network_errors
        )
        
        # Log performance metrics for analytics
        dom_count = len(json.loads(current_dom)) if current_dom else 0
        await db_service.log_metric(
            site_id, check_id, 
            response_time_ms=0,  # Could be calculated from result if supported by scraper
            dom_elements=dom_count,
            console_errors=len(console_logs),
            network_failures=len(network_errors)
        )

        if rca and isinstance(rca, dict):
            category = rca.get("category", "Unknown")
            await db_service.create_error(check_id, rca.get("probable_cause", ""), category)
            await db_service.create_root_cause(
                check_id,
                rca.get("probable_cause", ""),
                rca.get("confidence", 0),
                rca.get("repair_action", "")
            )

        # 6. Final Broadcast
        final_result = {
            "type": "result",
            "site_id": site_id,
            "check_id": check_id,
            "name": name,
            "url": url,
            "status": final_status,
            "status_code": status_code,
            "rca": rca,
            "visual_analysis": visual_analysis,
            "timestamp": timestamp,
            "screenshot": screenshot_url,
            "is_visual_change": visual_analysis is not None,
            "console_logs": console_logs,
            "network_errors": network_errors,
            "console_log_count": len(console_logs),
            "network_error_count": len(network_errors)
        }
        print(f"DEBUG: Broadcasting result for {name} with site_id={site_id}: {json.dumps(final_result, default=str)[:200]}...")
        await manager.broadcast(final_result)
        print(f"DEBUG: Result broadcast completed for site_id={site_id}")

    else:
        # Use custom check executor for API, DNS, TCP, etc.
        try:
            config = CheckConfig(CheckType(check_type), url)
            result = await CheckExecutor.execute(config)
            
            is_success = result.get("is_success", False)
            final_status = "SUCCESS" if is_success else "FAILED"
            status_code = result.get("status_code", 0)
            
            await manager.broadcast({
                "type": "status",
                "msg": f"✅ {check_type.upper()} check completed with status: {final_status}",
                "check_id": check_id
            })
            
            # Persist check results to SQLite (site is already created in the /monitor endpoint)
            await db_service.create_check(
                site_id, check_id, final_status, timestamp, "", 
                status_code, [], []
            )
            
            # Log metric
            await db_service.log_metric(
                site_id, check_id,
                response_time_ms=result.get("response_time_ms", 0),
                dom_elements=0,
                console_errors=0,
                network_failures=0
            )
            
            # Final Broadcast
            final_result = {
                "type": "result",
                "site_id": site_id,
                "check_id": check_id,
                "name": name,
                "url": url,
                "check_type": check_type,
                "status": final_status,
                "status_code": status_code,
                "details": result,
                "timestamp": timestamp,
            }
            await manager.broadcast(final_result)
            
        except Exception as e:
            await manager.broadcast({
                "type": "error",
                "msg": f"Error executing {check_type} check: {str(e)}",
                "check_id": check_id
            })


@app.post("/monitor", tags=["monitoring"])
async def monitor_site(url: str, name: str, check_type: str = "http", background_tasks: BackgroundTasks = None):
    """Start a monitoring check for a website.
    
    - **url**: Website/API URL to monitor
    - **name**: Human-readable site name
    - **check_type**: Type of check - 'http' (default), 'api', 'dns', or 'tcp'
    """
    site_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
    print(f"INFO: /monitor endpoint called - name={name}, url={url}, site_id={site_id}, check_type={check_type}")
    
    # Create site immediately so it appears in the list right away
    result = await db_service.create_site(name, url, site_id, check_type)
    print(f"INFO: Site creation result: {result}")
    
    # Start monitoring task in the background
    background_tasks.add_task(run_monitoring_task, url, name, site_id, check_type)
    return {"message": "Monitoring task started", "site_id": site_id, "check_type": check_type}


@app.get("/sites", tags=["sites"])
async def list_sites():
    """List all monitored websites."""
    sites = await db_service.get_all_sites()
    print(f"INFO: /sites endpoint called - returning {len(sites)} sites")
    for site in sites:
        print(f"  - {site['name']} ({site['url']})")
    return {"sites": sites}


@app.get("/sites/{site_id}/history", tags=["check-history"])
async def get_site_history(site_id: str, limit: int = 10):
    """Get check history for a specific site."""
    history = await db_service.get_checks_by_site(site_id)
    return {"history": history[:limit]}


@app.delete("/sites/{site_id}", tags=["sites"])
async def delete_site(site_id: str):
    """Delete a monitored site and all related data."""
    await db_service.delete_site(site_id)
    return {"message": "Site deleted"}


@app.get("/sites/{site_id}/metrics", tags=["analytics"])
async def get_site_metrics(site_id: str, limit: int = 50):
    """Get performance metrics for a specific site."""
    metrics = await db_service.get_site_metrics(site_id, limit)
    return {"metrics": metrics}


@app.get("/sites/{site_id}/uptime", tags=["analytics"])
async def get_site_uptime(site_id: str, days: int = 7):
    """Get uptime percentage for a site over the last N days."""
    uptime = await db_service.get_uptime_percentage(site_id, days)
    return {"site_id": site_id, "uptime_percentage": uptime, "days": days}


@app.get("/analytics/summary", tags=["analytics"])
async def get_analytics_summary():
    """Get overall system analytics across all sites."""
    sites = await db_service.get_all_sites()
    summary = {
        "total_sites": len(sites),
        "sites_data": []
    }
    
    for site in sites:
        uptime = await db_service.get_uptime_percentage(site["id"], 7)
        metrics = await db_service.get_site_metrics(site["id"], 1)
        summary["sites_data"].append({
            "site_id": site["id"],
            "name": site["name"],
            "uptime_7d": uptime,
            "latest_status": metrics[0] if metrics else None
        })
    
    return summary


@app.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring status updates."""
    try:
        await manager.connect(websocket)
        await websocket.send_json({"type": "status", "msg": "Connected to GemmaWatch"})
        # Keep connection alive with 30-second pings
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=WS_TIMEOUT)
            except asyncio.TimeoutError:
                # Timeout is expected, connection stays alive
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

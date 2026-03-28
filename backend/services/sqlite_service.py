import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "gemmawatch.db"

class SQLiteService:
    def __init__(self):
        self.available = False
        self.init_db()
    
    def init_db(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Sites Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sites (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    check_type TEXT DEFAULT 'http',
                    frequency INTEGER DEFAULT 300,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Schema migrations - add missing columns to existing tables
            cursor.execute("PRAGMA table_info(sites)")
            sites_columns = [col[1] for col in cursor.fetchall()]
            if 'check_type' not in sites_columns:
                cursor.execute("ALTER TABLE sites ADD COLUMN check_type TEXT DEFAULT 'http'")
                print("INFO: Added check_type column to sites table")
            
            # Add detailed logs columns to checks table
            cursor.execute("PRAGMA table_info(checks)")
            checks_columns = [col[1] for col in cursor.fetchall()]
            if 'console_logs_json' not in checks_columns:
                cursor.execute("ALTER TABLE checks ADD COLUMN console_logs_json TEXT")
                print("INFO: Added console_logs_json column to checks table")
            if 'network_errors_json' not in checks_columns:
                cursor.execute("ALTER TABLE checks ADD COLUMN network_errors_json TEXT")
                print("INFO: Added network_errors_json column to checks table")
            
            # Checks Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS checks (
                    id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    screenshot_url TEXT,
                    status_code INTEGER,
                    console_log_count INTEGER,
                    network_error_count INTEGER,
                    FOREIGN KEY(site_id) REFERENCES sites(id)
                )
            """)
            
            # RootCauses Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS root_causes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_id TEXT NOT NULL,
                    probable_cause TEXT,
                    confidence REAL,
                    repair_action TEXT,
                    FOREIGN KEY(check_id) REFERENCES checks(id)
                )
            """)
            
            # Metrics Table (for analytics)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id TEXT NOT NULL,
                    check_id TEXT NOT NULL,
                    response_time_ms REAL,
                    dom_elements INTEGER,
                    console_errors INTEGER,
                    network_failures INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(site_id) REFERENCES sites(id),
                    FOREIGN KEY(check_id) REFERENCES checks(id)
                )
            """)
            
            conn.commit()
            conn.close()
            self.available = True
            print("INFO: SQLite database initialized at", DB_PATH)
        except Exception as e:
            print(f"ERROR: SQLite init failed: {e}")
            self.available = False
    
    async def create_site(self, name, url, site_id, check_type="http"):
        if not self.available:
            print(f"WARNING: SQLite not available, cannot create site {site_id}")
            return False
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Check if site already exists
            cursor.execute("SELECT id, name FROM sites WHERE id = ?", (site_id,))
            existing = cursor.fetchone()
            
            if existing:
                existing_id, existing_name = existing
                if existing_name != name:
                    # Update the name if it's different
                    cursor.execute("UPDATE sites SET name = ? WHERE id = ?", (name, site_id))
                    print(f"INFO: Updated site name from '{existing_name}' to '{name}' for {site_id}")
                else:
                    print(f"INFO: Site {site_id} already exists with same name, skipping")
            else:
                cursor.execute(
                    "INSERT INTO sites (id, name, url, check_type) VALUES (?, ?, ?, ?)",
                    (site_id, name, url, check_type)
                )
                print(f"INFO: Inserted new site {site_id}: {name} ({url})")
            
            conn.commit()
            conn.close()
            
            # Verify the final state
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sites")
            count = cursor.fetchone()[0]
            print(f"INFO: Total sites in database: {count}")
            conn.close()
            
            return True
        except Exception as e:
            print(f"ERROR: Failed to create site {site_id}: {e}")
            return False
    
    async def create_check(self, site_id, check_id, status, timestamp, screenshot_url, status_code, console_logs=None, network_errors=None):
        if not self.available:
            return
        try:
            import json
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Handle both old format (counts) and new format (actual logs)
            if isinstance(console_logs, list):
                console_count = len(console_logs)
                console_logs_json = json.dumps(console_logs)
            else:
                console_count = console_logs if isinstance(console_logs, int) else 0
                console_logs_json = json.dumps([])
            
            if isinstance(network_errors, list):
                network_count = len(network_errors)
                network_errors_json = json.dumps(network_errors)
            else:
                network_count = network_errors if isinstance(network_errors, int) else 0
                network_errors_json = json.dumps([])
            
            cursor.execute(
                """INSERT INTO checks 
                   (id, site_id, status, timestamp, screenshot_url, status_code, console_log_count, network_error_count, console_logs_json, network_errors_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (check_id, site_id, status, timestamp, screenshot_url, status_code, console_count, network_count, console_logs_json, network_errors_json)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"ERROR: Failed to create check: {e}")
    
    async def create_root_cause(self, check_id, probable_cause, confidence, repair_action):
        if not self.available:
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO root_causes (check_id, probable_cause, confidence, repair_action)
                   VALUES (?, ?, ?, ?)""",
                (check_id, probable_cause, confidence, repair_action)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"ERROR: Failed to create root cause: {e}")
    
    async def get_all_sites(self):
        if not self.available:
            return []
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, url, check_type, created_at FROM sites")
            rows = cursor.fetchall()
            conn.close()
            return [{"id": r[0], "name": r[1], "url": r[2], "check_type": r[3], "created_at": r[4]} for r in rows]
        except Exception as e:
            print(f"ERROR: Failed to get sites: {e}")
            return []
    
    async def get_checks_by_site(self, site_id):
        if not self.available:
            return []
        try:
            import json
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """SELECT c.id, c.status, c.timestamp, c.screenshot_url, c.status_code, 
                          c.console_log_count, c.network_error_count,
                          c.console_logs_json, c.network_errors_json,
                          r.probable_cause, r.confidence, r.repair_action
                   FROM checks c
                   LEFT JOIN root_causes r ON c.id = r.check_id
                   WHERE c.site_id = ? 
                   ORDER BY c.timestamp DESC""",
                (site_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            results = []
            for r in rows:
                try:
                    console_logs = json.loads(r[7]) if r[7] else []
                    network_errors = json.loads(r[8]) if r[8] else []
                except:
                    console_logs = []
                    network_errors = []
                
                check_data = {
                    "id": r[0],
                    "status": r[1],
                    "timestamp": r[2],
                    "screenshot": r[3],
                    "status_code": r[4],
                    "console_log_count": r[5] or 0,
                    "network_error_count": r[6] or 0,
                    "console_logs": console_logs,
                    "network_errors": network_errors,
                }
                # Add RCA if available
                if r[9] is not None:  # probable_cause
                    check_data["rca"] = {
                        "probable_cause": r[9],
                        "confidence": r[10] or 0,
                        "repair_action": r[11] or "",
                        "category": "Unknown"  # Category not persisted, comes from Gemma in WebSocket
                    }
                results.append(check_data)
            return results
        except Exception as e:
            print(f"ERROR: Failed to get checks: {e}")
            return []
    
    async def create_error(self, check_id, error_msg, category):
        # Placeholder - not used in current flow
        pass
    
    async def delete_site(self, site_id):
        if not self.available:
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sites WHERE id = ?", (site_id,))
            cursor.execute("DELETE FROM checks WHERE site_id = ?", (site_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"ERROR: Failed to delete site: {e}")
    
    async def log_metric(self, site_id, check_id, response_time_ms, dom_elements, console_errors, network_failures):
        """Log performance metrics for analytics."""
        if not self.available:
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO metrics (site_id, check_id, response_time_ms, dom_elements, console_errors, network_failures)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (site_id, check_id, response_time_ms, dom_elements, console_errors, network_failures)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"ERROR: Failed to log metric: {e}")
    
    async def get_site_metrics(self, site_id, limit: int = 50):
        """Get historical metrics for a site."""
        if not self.available:
            return []
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """SELECT response_time_ms, dom_elements, console_errors, network_failures, timestamp
                   FROM metrics WHERE site_id = ? ORDER BY timestamp DESC LIMIT ?""",
                (site_id, limit)
            )
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    "response_time_ms": r[0],
                    "dom_elements": r[1],
                    "console_errors": r[2],
                    "network_failures": r[3],
                    "timestamp": r[4]
                } for r in rows
            ]
        except Exception as e:
            print(f"ERROR: Failed to get metrics: {e}")
            return []
    
    async def get_uptime_percentage(self, site_id, days: int = 7):
        """Calculate uptime percentage for the last N days."""
        if not self.available:
            return 0
        try:
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT COUNT(*) FROM checks WHERE site_id = ? AND timestamp > ? AND status = 'SUCCESS'",
                (site_id, cutoff_date)
            )
            success_count = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM checks WHERE site_id = ? AND timestamp > ?",
                (site_id, cutoff_date)
            )
            total_count = cursor.fetchone()[0]
            
            conn.close()
            
            if total_count == 0:
                return 100.0
            return (success_count / total_count) * 100
        except Exception as e:
            print(f"ERROR: Failed to calculate uptime: {e}")
            return 0

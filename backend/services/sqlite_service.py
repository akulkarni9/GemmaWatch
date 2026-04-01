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
            
            # ── Sites Table ──────────────────────────────────────────────────────
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
            
            # ── Schema migrations (non-destructive) ──────────────────────────────
            cursor.execute("PRAGMA table_info(sites)")
            sites_cols = [col[1] for col in cursor.fetchall()]
            for col, definition in [
                ("check_type",     "TEXT DEFAULT 'http'"),
                ("last_checked_at","TIMESTAMP"),
                ("next_check_at",  "TIMESTAMP"),
            ]:
                if col not in sites_cols:
                    cursor.execute(f"ALTER TABLE sites ADD COLUMN {col} {definition}")
                    print(f"INFO: Added {col} column to sites table")

            # ── Checks Table ─────────────────────────────────────────────────────
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
            cursor.execute("PRAGMA table_info(checks)")
            checks_cols = [col[1] for col in cursor.fetchall()]
            for col in ("console_logs_json", "network_errors_json"):
                if col not in checks_cols:
                    cursor.execute(f"ALTER TABLE checks ADD COLUMN {col} TEXT")
                    print(f"INFO: Added {col} column to checks table")

            # ── RootCauses Table ─────────────────────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS root_causes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    check_id TEXT NOT NULL,
                    probable_cause TEXT,
                    confidence REAL,
                    repair_action TEXT,
                    repair_steps_json TEXT, -- Added for structured repair pipeline
                    FOREIGN KEY(check_id) REFERENCES checks(id)
                )
            """)
            # Migration for existing root_causes
            cursor.execute("PRAGMA table_info(root_causes)")
            rc_cols = [col[1] for col in cursor.fetchall()]
            if "repair_steps_json" not in rc_cols:
                cursor.execute("ALTER TABLE root_causes ADD COLUMN repair_steps_json TEXT")
                print("INFO: Added repair_steps_json column to root_causes table")

            # ── Metrics Table ─────────────────────────────────────────────────────
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

            # ── Auth: Users ───────────────────────────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT,
                    avatar_url TEXT,
                    provider TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP,
                    UNIQUE(provider, provider_id)
                )
            """)

            # ── Auth: Refresh Tokens ──────────────────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    revoked INTEGER DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

            # ── Catalogue: Shadow (low-confidence, never reviewed) ────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shadow_catalogue (
                    id TEXT PRIMARY KEY,
                    check_id TEXT,
                    probable_cause TEXT,
                    confidence REAL,
                    category TEXT,
                    raw_rca_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ── Catalogue: Pending (HITL review queue) ───────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_catalogue (
                    id TEXT PRIMARY KEY,
                    check_id TEXT,
                    rca_json TEXT NOT NULL,
                    confidence REAL,
                    category TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    reviewer_id TEXT,
                    reviewer_note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    FOREIGN KEY(reviewer_id) REFERENCES users(id)
                )
            """)

            # ── Catalogue: Primary (approved, ground truth) ───────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS primary_catalogue (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    probable_cause TEXT NOT NULL,
                    repair_action TEXT,
                    confidence REAL,
                    evidence_json TEXT,
                    approved_by TEXT,
                    last_matched_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(approved_by) REFERENCES users(id)
                )
            """)

            # ── Anomaly Events ────────────────────────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anomaly_events (
                    id TEXT PRIMARY KEY,
                    site_id TEXT NOT NULL,
                    check_id TEXT,
                    z_score REAL,
                    metric_type TEXT,
                    baseline_mean REAL,
                    baseline_std REAL,
                    observed_value REAL,
                    gemma_interpretation TEXT,
                    severity TEXT DEFAULT 'low',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(site_id) REFERENCES sites(id)
                )
            """)

            # ── Incidents (cross-site correlation) ───────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'open',
                    affected_site_ids_json TEXT,
                    correlation_window_start TIMESTAMP,
                    correlation_window_end TIMESTAMP,
                    probable_shared_cause TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    resolved_by TEXT,
                    FOREIGN KEY(resolved_by) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incident_notes (
                    id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    user_id TEXT,
                    note TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(incident_id) REFERENCES incidents(id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

            # ── Alert Config ──────────────────────────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_config (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    recipient_email TEXT,
                    smtp_host TEXT,
                    smtp_port INTEGER DEFAULT 587,
                    smtp_user TEXT,
                    smtp_password TEXT,
                    enabled INTEGER DEFAULT 0,
                    min_severity TEXT DEFAULT 'medium',
                    cooldown_minutes INTEGER DEFAULT 30,
                    alert_on_failure INTEGER DEFAULT 1,
                    consecutive_failures_threshold INTEGER DEFAULT 2,
                    alert_on_anomaly INTEGER DEFAULT 1,
                    alert_on_incident INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Seed default alert config row if missing
            cursor.execute("SELECT COUNT(*) FROM alert_config")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO alert_config (id) VALUES (1)")

            # ── Alert Log ─────────────────────────────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_log (
                    id TEXT PRIMARY KEY,
                    site_id TEXT,
                    incident_id TEXT,
                    alert_type TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    recipient_email TEXT,
                    status TEXT DEFAULT 'sent'
                )
            """)

            # ── ErrorFingerprints Table ─────────────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_fingerprints (
                    id TEXT PRIMARY KEY, -- SHA-256 hash
                    type TEXT NOT NULL, -- 'console' | 'network'
                    pattern TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    severity TEXT DEFAULT 'Medium',
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_occurrences INTEGER DEFAULT 1
                )
            """)

            # ── CheckFingerprints Table (Join) ──────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS check_fingerprints (
                    check_id TEXT NOT NULL,
                    fingerprint_id TEXT NOT NULL,
                    PRIMARY KEY(check_id, fingerprint_id),
                    FOREIGN KEY(check_id) REFERENCES checks(id),
                    FOREIGN KEY(fingerprint_id) REFERENCES error_fingerprints(id)
                )
            """)

            # ── Chat Messages ─────────────────────────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    query_type TEXT,
                    sources_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    async def create_root_cause(self, check_id, probable_cause, confidence, repair_action, repair_steps=None):
        if not self.available:
            return
        try:
            import json
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            repair_steps_json = json.dumps(repair_steps) if repair_steps else None
            cursor.execute(
                """INSERT INTO root_causes (check_id, probable_cause, confidence, repair_action, repair_steps_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (check_id, probable_cause, confidence, repair_action, repair_steps_json)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"ERROR: Failed to create root cause: {e}")

    async def upsert_fingerprint(self, fid, ftype, pattern, title=None, description=None):
        if not self.available:
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO error_fingerprints (id, type, pattern, title, description)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET 
                   last_seen = CURRENT_TIMESTAMP,
                   total_occurrences = total_occurrences + 1""",
                (fid, ftype, pattern, title, description)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"ERROR: Failed to upsert fingerprint: {e}")

    async def link_check_to_fingerprint(self, check_id, fingerprint_id):
        if not self.available:
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO check_fingerprints (check_id, fingerprint_id) VALUES (?, ?)",
                (check_id, fingerprint_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"ERROR: Failed to link fingerprint: {e}")

    async def get_fingerprint(self, fid):
        if not self.available:
            return None
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM error_fingerprints WHERE id = ?", (fid,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            print(f"ERROR: Failed to get fingerprint {fid}: {e}")
            return None

    async def get_check_fingerprints(self, check_id):
        if not self.available:
            return []
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT f.* 
                   FROM error_fingerprints f
                   JOIN check_fingerprints cf ON f.id = cf.fingerprint_id
                   WHERE cf.check_id = ?""",
                (check_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"ERROR: Failed to get fingerprints for check {check_id}: {e}")
            return []
    
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
                          r.probable_cause, r.confidence, r.repair_action, r.repair_steps_json
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
                    repair_steps = None
                    if r[12]:  # repair_steps_json
                        try:
                            repair_steps = json.loads(r[12])
                        except:
                            repair_steps = None
                    check_data["rca"] = {
                        "probable_cause": r[9],
                        "confidence": r[10] or 0,
                        "repair_action": r[11] or "",
                        "category": "Unknown",
                        "repair_steps": repair_steps,
                    }

                # Attach fingerprints for this check
                try:
                    fp_conn = sqlite3.connect(DB_PATH)
                    fp_cursor = fp_conn.cursor()
                    fp_cursor.execute(
                        """SELECT f.id, f.type, f.title, f.description, f.severity
                           FROM error_fingerprints f
                           JOIN check_fingerprints cf ON f.id = cf.fingerprint_id
                           WHERE cf.check_id = ?""",
                        (r[0],)
                    )
                    fp_rows = fp_cursor.fetchall()
                    fp_conn.close()
                    check_data["fingerprints"] = [
                        {
                            "id": fp[0],
                            "fingerprint_hash": fp[0],
                            "error_type": fp[1],
                            "title": fp[2] or "Unnamed Pattern",
                            "description": fp[3] or "",
                            "severity": fp[4] or "low",
                        }
                        for fp in fp_rows
                    ]
                except Exception as fp_err:
                    print(f"WARN: Could not fetch fingerprints for check {r[0]}: {fp_err}")
                    check_data["fingerprints"] = []
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

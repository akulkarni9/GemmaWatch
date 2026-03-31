"""
Scheduler service: APScheduler AsyncIOScheduler.
Master job runs every 60 seconds and triggers checks for all sites that are due.
State is fully persisted in SQLite (next_check_at on the sites table) — crash-safe.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._monitor_fn = None  # Injected from main.py to avoid circular imports

    def set_monitor_fn(self, fn):
        """Inject the monitoring task function (avoids circular import)."""
        self._monitor_fn = fn

    def start(self):
        self.scheduler.add_job(
            self._tick,
            trigger="interval",
            seconds=60,
            id="master_scheduler",
            replace_existing=True,
            next_run_time=datetime.now(),  # Run immediately on startup
        )
        self.scheduler.start()
        print("INFO: Scheduler started — checking for due sites every 60s")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            print("INFO: Scheduler stopped")

    async def _tick(self):
        """Master tick: find all sites due for a check and fire them."""
        if self._monitor_fn is None:
            return
        try:
            import sqlite3
            from services.sqlite_service import DB_PATH
            now = datetime.now().isoformat()
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """SELECT id, name, url, check_type, frequency
                   FROM sites
                   WHERE next_check_at IS NULL OR next_check_at <= ?""",
                (now,),
            )
            due_sites = [dict(row) for row in cur.fetchall()]
            conn.close()

            if due_sites:
                print(f"INFO: Scheduler tick — {len(due_sites)} site(s) due for check")

            for site in due_sites:
                asyncio.create_task(self._run_and_update(site))

        except Exception as e:
            print(f"ERROR: Scheduler tick failed: {e}")

    async def _run_and_update(self, site: dict):
        """Run a monitoring check and update next_check_at on completion."""
        try:
            await self._monitor_fn(
                url=site["url"],
                name=site["name"],
                site_id=site["id"],
                check_type=site.get("check_type", "http"),
            )
        except Exception as e:
            print(f"ERROR: Scheduled check failed for {site['name']}: {e}")
        finally:
            # Always update scheduling timestamps, even if check errored
            await self._update_schedule(site["id"], site.get("frequency", 300))

    @staticmethod
    async def _update_schedule(site_id: str, frequency_seconds: int):
        import sqlite3
        from services.sqlite_service import DB_PATH
        now = datetime.now()
        next_check = (now + timedelta(seconds=frequency_seconds)).isoformat()
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE sites SET last_checked_at = ?, next_check_at = ? WHERE id = ?",
            (now.isoformat(), next_check, site_id),
        )
        conn.commit()
        conn.close()

    @staticmethod
    async def reset_schedule(site_id: str):
        """Call this after manual trigger to reset the next_check_at clock."""
        import sqlite3
        from services.sqlite_service import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT frequency FROM sites WHERE id = ?", (site_id,))
        row = cur.fetchone()
        if row:
            frequency = row[0] or 300
            next_check = (datetime.now() + timedelta(seconds=frequency)).isoformat()
            conn.execute(
                "UPDATE sites SET last_checked_at = ?, next_check_at = ? WHERE id = ?",
                (datetime.now().isoformat(), next_check, site_id),
            )
            conn.commit()
        conn.close()


scheduler_service = SchedulerService()

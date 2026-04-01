import hashlib
import re
import asyncio
from typing import List, Dict, Any, Optional

class FingerprintService:
    def __init__(self, db_service, ai_service):
        self.db = db_service
        self.ai = ai_service
        self.manager = None
        # Cache for known fingerprint titles to avoid redundant AI calls in a single run
        self._title_cache = {}

    def set_manager(self, manager):
        self.manager = manager

    def normalize_console_error(self, log: Dict[str, Any]) -> str:
        """
        Normalizes a console log message by removing dynamic data like IDs,
        timestamps, and specific line numbers.
        """
        msg = log.get("message", "")
        if not msg:
            return "empty_console_message"

        # 1. Remove standard ISO8601 timestamps and Unix epochs
        msg = re.sub(r'\d{4}-\d{2}-\d{1,2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?', '<time>', msg)
        msg = re.sub(r'\b\d{10,13}\b', '<num>', msg)

        # 2. Remove UUIDs / Hex IDs (at least 8 chars)
        msg = re.sub(r'\b[0-9a-fA-F]{8,}\b', '<id>', msg)

        # 3. Remove line/column numbers (e.g. "main.js:123:45" -> "main.js:*:*")
        msg = re.sub(r':\d+:\d+', ':*:*', msg)
        msg = re.sub(r':\d+', ':*', msg)

        # 4. Collapse multiple spaces and trim
        msg = re.sub(r'\s+', ' ', msg).strip()
        
        return f"console|{log.get('level', 'error')}|{msg}"

    def normalize_network_error(self, error: Dict[str, Any]) -> str:
        """
        Normalizes a network error by stripping query params and 
        replacing resource IDs in URLs.
        """
        url = error.get("url", "")
        method = error.get("method", "GET").upper()
        reason = error.get("message", "unknown_error")

        if not url:
            return f"network|{method}|{reason}"

        # 1. Remove query parameters
        url = url.split('?')[0]

        # 2. Replace resource IDs in path (digits or long hex segments)
        # e.g. /api/v1/posts/123 -> /api/v1/posts/*
        url_parts = url.split('/')
        normalized_parts = []
        for part in url_parts:
            # If part is pure digits or looks like a UUID/Hash
            if re.match(r'^\d+$', part) or re.match(r'^[0-9a-fA-F]{8,}$', part):
                normalized_parts.append('*')
            else:
                normalized_parts.append(part)
        
        url = '/'.join(normalized_parts)

        return f"network|{method}|{url}|{reason}"

    def get_hash(self, text: str) -> str:
        """Generates a stable SHA-256 hash for a normalized string."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    async def process_check_errors(self, check_id: str, console_logs: List[Dict], network_errors: List[Dict]):
        """
        Identifies all unique fingerprints in a check, upserts them to the DB,
        and links them to the check.
        """
        fingerprints_found = {} # hash -> {type, pattern}

        # Process console logs (only errors/warns)
        for log in console_logs:
            if log.get("level") in ["error", "warning"]:
                pattern = self.normalize_console_error(log)
                fid = self.get_hash(pattern)
                fingerprints_found[fid] = {"type": "console", "pattern": pattern}

        # Process network errors
        for err in network_errors:
            pattern = self.normalize_network_error(err)
            fid = self.get_hash(pattern)
            fingerprints_found[fid] = {"type": "network", "pattern": pattern}

        for fid, data in fingerprints_found.items():
            # Link to check first (this ensures we track frequency even if metadata gen fails)
            await self.db.link_check_to_fingerprint(check_id, fid)
            
            # Upsert into error_fingerprints table
            # We'll trigger AI metadata generation if it's new (handled in service or DB logic)
            # For simplicity, we check if it already has a title in our cache or DB
            await self.db.upsert_fingerprint(fid, data["type"], data["pattern"])
            
            # Optional: Trigger AI naming if this is the first time we see it
            # (In a production app, we'd check DB first, then trigger)
            asyncio.create_task(self._ensure_metadata(fid, data["type"], data["pattern"]))

    async def _ensure_metadata(self, fid: str, ftype: str, pattern: str):
        """Asks Gemma to provide a clean title/description for a new fingerprint."""
        if fid in self._title_cache:
            return

        # Double-check DB before AI call to avoid redundant processing
        # Use simple get_fingerprint check
        existing = await self.db.get_fingerprint(fid)
        if existing and existing.get("title"):
            self._title_cache[fid] = existing["title"]
            return

        try:
            metadata = await self.ai.generate_fingerprint_metadata(pattern)
            if metadata:
                await self.db.upsert_fingerprint(
                    fid, ftype, pattern, 
                    title=metadata.get("title"), 
                    description=metadata.get("description")
                )
                self._title_cache[fid] = metadata.get("title")
                print(f"DEBUG: Successfully generated AI metadata for fingerprint {fid}")
                
                # Broadcast the update to anyone listening (e.g., ErrorFingerprintPanel)
                if self.manager:
                    await self.manager.broadcast({
                        "type": "fingerprint_updated",
                        "fingerprint": {
                            "id": fid,
                            "title": metadata.get("title"),
                            "description": metadata.get("description"),
                            # Let the frontend overlay these new values on its existing object
                        }
                    })
            else:
                print(f"DEBUG: AI Fingerprint generation returned no result for {fid}")
        except Exception as e:
            print(f"ERROR: AI Fingerprint generation failed for {fid}: {e}")

fingerprint_service = None # To be initialized in main.py

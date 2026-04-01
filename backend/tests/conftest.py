"""Pytest configuration and shared fixtures for GemmaWatch 2.0."""
import pytest
import sqlite3
import tempfile
import json
import uuid
import os
from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture(scope="function")
def temp_db():
    """Create a temporary SQLite database with the full 2.0 schema for testing."""
    # Create a unique filename for every test to ensure 100% isolation
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(db_fd)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # ── Full 2.0 Schema ──────────────────────────────────────────────────
    cursor.execute("CREATE TABLE sites (id TEXT PRIMARY KEY, name TEXT, url TEXT, check_type TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE checks (id TEXT PRIMARY KEY, site_id TEXT, status TEXT, timestamp TIMESTAMP, screenshot_url TEXT, status_code INTEGER, console_log_count INTEGER, network_error_count INTEGER, console_logs_json TEXT, network_errors_json TEXT, FOREIGN KEY(site_id) REFERENCES sites(id))")
    cursor.execute("CREATE TABLE metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, site_id TEXT, check_id TEXT, response_time_ms REAL, dom_elements INTEGER, console_errors INTEGER, network_failures INTEGER, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(site_id) REFERENCES sites(id), FOREIGN KEY(check_id) REFERENCES checks(id))")
    cursor.execute("CREATE TABLE root_causes (id INTEGER PRIMARY KEY AUTOINCREMENT, check_id TEXT, probable_cause TEXT, confidence REAL, repair_action TEXT, FOREIGN KEY(check_id) REFERENCES checks(id))")
    cursor.execute("CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT UNIQUE, name TEXT, avatar_url TEXT, provider TEXT, provider_id TEXT, role TEXT DEFAULT 'viewer', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login_at TIMESTAMP)")
    cursor.execute("CREATE TABLE refresh_tokens (id TEXT PRIMARY KEY, user_id TEXT, token_hash TEXT UNIQUE, expires_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, revoked INTEGER DEFAULT 0, FOREIGN KEY(user_id) REFERENCES users(id))")
    cursor.execute("CREATE TABLE shadow_catalogue (id TEXT PRIMARY KEY, check_id TEXT, probable_cause TEXT, confidence REAL, category TEXT, raw_rca_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE pending_catalogue (id TEXT PRIMARY KEY, check_id TEXT, rca_json TEXT NOT NULL, confidence REAL, category TEXT, status TEXT DEFAULT 'pending', reviewer_id TEXT, reviewer_note TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reviewed_at TIMESTAMP, FOREIGN KEY(reviewer_id) REFERENCES users(id))")
    cursor.execute("CREATE TABLE primary_catalogue (id TEXT PRIMARY KEY, category TEXT NOT NULL, probable_cause TEXT NOT NULL, repair_action TEXT, confidence REAL, evidence_json TEXT, approved_by TEXT, last_matched_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(approved_by) REFERENCES users(id))")
    cursor.execute("CREATE TABLE catalogue_vec_map (rowid INTEGER PRIMARY KEY AUTOINCREMENT, catalogue_id TEXT UNIQUE)")
    
    # ── Vector Virtual Table (Conditional) ──
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        cursor.execute("CREATE VIRTUAL TABLE catalogue_vec USING vec0(embedding float32[768])")
    except:
        # Fallback to normal table for non-matching tests
        cursor.execute("CREATE TABLE catalogue_vec (rowid INTEGER PRIMARY KEY, embedding BLOB)")
    
    cursor.execute("CREATE TABLE chat_messages (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, user_id TEXT, role TEXT NOT NULL, content TEXT NOT NULL, query_type TEXT, sources_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    
    conn.commit()
    conn.close()
    
    # Point all services to this SPECIFIC temp DB
    with patch("services.sqlite_service.DB_PATH", db_path), \
         patch("services.catalogue_service.DB_PATH", db_path), \
         patch("services.chat_service.DB_PATH", db_path):
        yield db_path
    
    # Force cleanup
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except:
            pass

# ── Mock Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_ai_service():
    """Mock for Ollama/Gemma service."""
    with patch("services.ai_service.AiService._call_ollama", new_callable=AsyncMock) as mocked:
        yield mocked

@pytest.fixture
def mock_embedding():
    """Mock for embedding service returning a deterministic float32 vector (3072 bytes)."""
    with patch("services.embedding_service.embed", new_callable=AsyncMock) as mocked:
        import struct
        # Return 768 zeros as float32 bytes (3072 bytes)
        mocked.return_value = struct.pack('768f', *([0.0] * 768))
        yield mocked

@pytest.fixture
def mock_auth_user():
    """Returns a sample authenticated user dict."""
    return {
        "sub": "test-user-id",
        "email": "test@gemmawatch.com",
        "role": "admin",
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
    }

# ── Sample Data Fixtures (Existing) ────────────────────────────────────────

@pytest.fixture
def sample_site_data():
    return {'id': 'test-site-1', 'name': 'Test Site', 'url': 'https://example.com', 'check_type': 'http'}

@pytest.fixture
def sample_check_data():
    return {
        'check_id': 'check-1',
        'site_id': 'test-site-1',
        'status': 'SUCCESS',
        'timestamp': datetime.now().isoformat(),
        'screenshot_url': '/screenshots/test.png',
        'status_code': 200,
        'console_count': 0,
        'network_count': 0
    }

@pytest.fixture
def sample_metric_data():
    return {
        'site_id': 'test-site-1',
        'check_id': 'check-1',
        'response_time_ms': 125.5,
        'dom_elements': 50,
        'console_errors': 0,
        'network_failures': 0
    }

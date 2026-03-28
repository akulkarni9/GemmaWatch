"""Pytest configuration and shared fixtures."""
import pytest
import sqlite3
import tempfile
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Initialize the database schema
    conn = sqlite3.connect(db_path)
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
    
    # Metrics Table
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
    
    # Root Causes Table
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
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_site_data():
    """Sample site data for testing."""
    return {
        'id': 'test-site-1',
        'name': 'Test Site',
        'url': 'https://example.com',
        'check_type': 'http'
    }


@pytest.fixture
def sample_check_data():
    """Sample check data for testing."""
    return {
        'check_id': 'check-1',
        'site_id': 'test-site-1',
        'status': 'SUCCESS',
        'timestamp': '2026-03-27T10:00:00',
        'screenshot_url': '/screenshots/test.png',
        'status_code': 200,
        'console_count': 0,
        'network_count': 0
    }


@pytest.fixture
def sample_metric_data():
    """Sample metric data for testing."""
    return {
        'site_id': 'test-site-1',
        'check_id': 'check-1',
        'response_time_ms': 125.5,
        'dom_elements': 50,
        'console_errors': 0,
        'network_failures': 0
    }

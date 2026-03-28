"""Unit tests for SQLite service."""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.sqlite_service import SQLiteService


@pytest.fixture
def sqlite_db(temp_db, monkeypatch):
    """SQLite service with temporary database."""
    # Patch the DB_PATH before importing
    import services.sqlite_service as sqlite_module
    monkeypatch.setattr(sqlite_module, 'DB_PATH', temp_db)
    
    service = SQLiteService()
    return service, temp_db


class TestSQLiteServiceBasics:
    """Test basic SQLite service initialization and setup."""
    
    def test_init_creates_service(self, sqlite_db):
        """Test that service initializes correctly."""
        service, _ = sqlite_db
        assert service is not None
        assert service.available is True
    
    def test_init_db_creates_tables(self, sqlite_db):
        """Test that init_db creates all required tables."""
        service, db_path = sqlite_db
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert 'sites' in tables
        assert 'checks' in tables
        assert 'metrics' in tables
        assert 'root_causes' in tables
        conn.close()


class TestSiteOperations:
    """Test site CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_site(self, sqlite_db, sample_site_data):
        """Test creating a site."""
        service, _ = sqlite_db
        
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id'],
            sample_site_data['check_type']
        )
        
        sites = await service.get_all_sites()
        assert len(sites) == 1
        assert sites[0]['name'] == 'Test Site'
        assert sites[0]['url'] == 'https://example.com'
        assert sites[0]['check_type'] == 'http'
    
    @pytest.mark.asyncio
    async def test_get_all_sites(self, sqlite_db):
        """Test retrieving all sites."""
        service, _ = sqlite_db
        
        # Create multiple sites
        await service.create_site('Site 1', 'https://site1.com', 'site-1', 'http')
        await service.create_site('Site 2', 'https://site2.com', 'site-2', 'api')
        
        sites = await service.get_all_sites()
        assert len(sites) == 2
        assert any(s['name'] == 'Site 1' for s in sites)
        assert any(s['name'] == 'Site 2' for s in sites)
    
    @pytest.mark.asyncio
    async def test_delete_site(self, sqlite_db, sample_site_data):
        """Test deleting a site."""
        service, _ = sqlite_db
        
        # Create site
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id'],
            sample_site_data['check_type']
        )
        
        # Verify it exists
        sites = await service.get_all_sites()
        assert len(sites) == 1
        
        # Delete it
        await service.delete_site(sample_site_data['id'])
        
        # Verify it's gone
        sites = await service.get_all_sites()
        assert len(sites) == 0


class TestCheckOperations:
    """Test check recording operations."""
    
    @pytest.mark.asyncio
    async def test_create_check(self, sqlite_db, sample_site_data, sample_check_data):
        """Test recording a check."""
        service, _ = sqlite_db
        
        # Create site first
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id']
        )
        
        # Create check
        await service.create_check(
            sample_check_data['site_id'],
            sample_check_data['check_id'],
            sample_check_data['status'],
            sample_check_data['timestamp'],
            sample_check_data['screenshot_url'],
            sample_check_data['status_code'],
            sample_check_data['console_count'],
            sample_check_data['network_count']
        )
        
        checks = await service.get_checks_by_site(sample_check_data['site_id'])
        assert len(checks) == 1
        assert checks[0]['status'] == 'SUCCESS'
        assert checks[0]['status_code'] == 200
    
    @pytest.mark.asyncio
    async def test_get_checks_by_site(self, sqlite_db, sample_site_data, sample_check_data):
        """Test retrieving checks for a site."""
        service, _ = sqlite_db
        
        # Create site and checks
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id']
        )
        
        # Create multiple checks
        for i in range(3):
            await service.create_check(
                sample_site_data['id'],
                f'check-{i}',
                'SUCCESS' if i < 2 else 'FAILED',
                '2026-03-27T10:00:00',
                '/screenshots/test.png',
                200 if i < 2 else 500,
                0,
                0
            )
        
        checks = await service.get_checks_by_site(sample_site_data['id'])
        assert len(checks) == 3
        assert checks[0]['status'] in ['SUCCESS', 'FAILED']


class TestMetricsOperations:
    """Test metrics tracking operations."""
    
    @pytest.mark.asyncio
    async def test_log_metric(self, sqlite_db, sample_site_data, sample_metric_data):
        """Test logging a performance metric."""
        service, _ = sqlite_db
        
        # Create site
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id']
        )
        
        # Log metric
        await service.log_metric(
            sample_metric_data['site_id'],
            sample_metric_data['check_id'],
            sample_metric_data['response_time_ms'],
            sample_metric_data['dom_elements'],
            sample_metric_data['console_errors'],
            sample_metric_data['network_failures']
        )
        
        metrics = await service.get_site_metrics(sample_site_data['id'])
        assert len(metrics) == 1
        assert metrics[0]['response_time_ms'] == 125.5
        assert metrics[0]['dom_elements'] == 50
    
    @pytest.mark.asyncio
    async def test_get_site_metrics_limit(self, sqlite_db, sample_site_data):
        """Test metric retrieval with limit."""
        service, _ = sqlite_db
        
        # Create site
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id']
        )
        
        # Log multiple metrics
        for i in range(10):
            await service.log_metric(
                sample_site_data['id'],
                f'check-{i}',
                100 + i,
                50 + i,
                i,
                0
            )
        
        # Get with limit
        metrics = await service.get_site_metrics(sample_site_data['id'], limit=5)
        assert len(metrics) == 5
    
    @pytest.mark.asyncio
    async def test_get_uptime_percentage(self, sqlite_db, sample_site_data):
        """Test uptime calculation."""
        service, _ = sqlite_db
        
        # Create site
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id']
        )
        
        # Create checks: 7 SUCCESS, 3 FAILED
        for i in range(7):
            await service.create_check(
                sample_site_data['id'],
                f'check-{i}',
                'SUCCESS',
                datetime.now().isoformat(),
                '/screenshots/test.png',
                200,
                0,
                0
            )
        
        for i in range(7, 10):
            await service.create_check(
                sample_site_data['id'],
                f'check-{i}',
                'FAILED',
                datetime.now().isoformat(),
                '/screenshots/test.png',
                500,
                0,
                0
            )
        
        uptime = await service.get_uptime_percentage(sample_site_data['id'], days=7)
        
        # Should be 70% (7 out of 10)
        assert 69.9 <= uptime <= 70.1
    
    @pytest.mark.asyncio
    async def test_uptime_100_percent(self, sqlite_db, sample_site_data):
        """Test 100% uptime calculation."""
        service, _ = sqlite_db
        
        # Create site
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id']
        )
        
        # Create all-success checks
        for i in range(5):
            await service.create_check(
                sample_site_data['id'],
                f'check-{i}',
                'SUCCESS',
                datetime.now().isoformat(),
                '/screenshots/test.png',
                200,
                0,
                0
            )
        
        uptime = await service.get_uptime_percentage(sample_site_data['id'], days=7)
        assert uptime == 100.0
    
    @pytest.mark.asyncio
    async def test_uptime_no_data(self, sqlite_db, sample_site_data):
        """Test uptime when no checks exist."""
        service, _ = sqlite_db
        
        # Create site but no checks
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id']
        )
        
        uptime = await service.get_uptime_percentage(sample_site_data['id'], days=7)
        # Should return 100 when no data (assumed to be working)
        assert uptime == 100.0


class TestRootCauseOperations:
    """Test root cause analysis storage."""
    
    @pytest.mark.asyncio
    async def test_create_root_cause(self, sqlite_db):
        """Test storing a root cause analysis."""
        service, db_path = sqlite_db
        
        check_id = 'check-1'
        
        await service.create_root_cause(
            check_id,
            'Database connection timeout',
            0.95,
            'Restart database service'
        )
        
        # Verify it was stored via direct DB query using the fixture DB
        import sqlite3
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT probable_cause, confidence FROM root_causes WHERE check_id = ?",
            (check_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        # Should have found the root cause
        assert row is not None
        assert row[0] == 'Database connection timeout'
        assert row[1] == 0.95


class TestServiceResilience:
    """Test service resilience and error handling."""
    
    @pytest.mark.asyncio
    async def test_unavailable_service_handling(self):
        """Test service behavior when database is unavailable."""
        # Create a service with bad DB path
        with patch('services.sqlite_service.DB_PATH', '/nonexistent/path/db.db'):
            service = SQLiteService()
            
            # Service should still be created
            assert service is not None
            # But marked as unavailable
            assert service.available is False
    
    @pytest.mark.asyncio
    async def test_duplicate_site_creation(self, sqlite_db, sample_site_data):
        """Test creating duplicate sites (should handle gracefully)."""
        service, _ = sqlite_db
        
        # Create a site twice
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id']
        )
        
        # Second creation should use INSERT OR IGNORE
        await service.create_site(
            sample_site_data['name'],
            sample_site_data['url'],
            sample_site_data['id']
        )
        
        sites = await service.get_all_sites()
        assert len(sites) == 1  # Should still be only one

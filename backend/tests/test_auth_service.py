import pytest
import sqlite3
from unittest.mock import patch, AsyncMock
from services.auth_service import assign_role, create_access_token, decode_access_token, find_or_create_user
from services.sqlite_service import SQLiteService

@pytest.fixture
def mock_db():
    return SQLiteService()

def test_assign_role_admin():
    """Verify that admin emails get assigned the admin role."""
    # Patch the global sets in services.auth_service directly
    with patch("services.auth_service.ADMIN_EMAILS", {"admin@mark.com"}), \
         patch("services.auth_service.ALLOWED_EMAILS", set()):
        assert assign_role("admin@mark.com") == "admin"
        assert assign_role("other@mark.com") == "viewer"

def test_jwt_flow():
    """Verify that tokens can be encoded and decoded correctly."""
    user_id = "user-1"
    email = "test@mark.com"
    role = "admin"
    
    token = create_access_token(user_id, email, role)
    payload = decode_access_token(token)
    
    assert payload["sub"] == user_id
    assert payload["email"] == email
    assert payload["role"] == role
    assert payload["type"] == "access"

@pytest.mark.asyncio
async def test_find_or_create_user_new(temp_db, mock_db):
    """Verify that a brand new OAuth user is correctly persisted."""
    with patch("services.auth_service.assign_role") as mock_assign:
        mock_assign.return_value = "viewer"
        
        user = await find_or_create_user(
            db=mock_db,
            provider="google",
            provider_id="google-123",
            email="new@mark.com",
            name="New User",
            avatar_url="http://avatar.com/1"
        )
        
        assert user["email"] == "new@mark.com"
        assert user["role"] == "viewer"
        
        conn = sqlite3.connect(temp_db)
        cur = conn.cursor()
        cur.execute("SELECT email, role FROM users WHERE provider_id = ?", ("google-123",))
        row = cur.fetchone()
        assert row[0] == "new@mark.com"
        assert row[1] == "viewer"
        conn.close()

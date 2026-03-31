"""
Auth service: Google + GitHub OAuth flows, JWT session management,
role assignment via ADMIN_EMAILS / ALLOWED_EMAILS env vars.
"""
import os
from dotenv import load_dotenv
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

# Load environment variables from .env file
load_dotenv()

import httpx
from fastapi import Request, HTTPException, Cookie
from jose import JWTError, jwt

from services.sqlite_service import SQLiteService

# ── Config from environment ───────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-32-chars!!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

# Comma-separated email lists
ADMIN_EMAILS = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
ALLOWED_EMAILS = {e.strip().lower() for e in os.getenv("ALLOWED_EMAILS", "").split(",") if e.strip()}

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8002")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


# ── Role assignment ───────────────────────────────────────────────────────────
def assign_role(email: str) -> Optional[str]:
    """
    Returns 'admin', 'viewer', or None (access denied).
    - If ADMIN_EMAILS is set: only listed emails get admin. Others need ALLOWED_EMAILS or open signup.
    - If ALLOWED_EMAILS is empty: any authenticated user becomes a viewer.
    """
    el = email.lower()
    if el in ADMIN_EMAILS:
        return "admin"
    if not ALLOWED_EMAILS or el in ALLOWED_EMAILS:
        return "viewer"
    return None  # Deny


# ── JWT helpers ───────────────────────────────────────────────────────────────
def create_access_token(user_id: str, email: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Returns (raw_token, token_hash) — store hash in DB, send raw to client."""
    raw = str(uuid.uuid4())
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── User lookup / creation ────────────────────────────────────────────────────
async def find_or_create_user(
    db: SQLiteService,
    provider: str,
    provider_id: str,
    email: str,
    name: str,
    avatar_url: str,
) -> dict:
    """Looks up by (provider, provider_id), falls back to email merge, else creates."""
    import sqlite3
    from services.sqlite_service import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Exact provider match
    cur.execute(
        "SELECT * FROM users WHERE provider = ? AND provider_id = ?",
        (provider, provider_id),
    )
    row = cur.fetchone()
    if row:
        user = dict(row)
        cur.execute(
            "UPDATE users SET last_login_at = ?, name = ?, avatar_url = ? WHERE id = ?",
            (datetime.now().isoformat(), name, avatar_url, user["id"]),
        )
        conn.commit()
        conn.close()
        user["name"] = name
        user["avatar_url"] = avatar_url
        return user

    # 2. Email merge (same email, different provider)
    cur.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
    row = cur.fetchone()
    if row:
        user = dict(row)
        cur.execute(
            "UPDATE users SET last_login_at = ?, name = ?, avatar_url = ? WHERE id = ?",
            (datetime.now().isoformat(), name, avatar_url, user["id"]),
        )
        conn.commit()
        conn.close()
        return user

    # 3. New user — check role assignment
    role = assign_role(email)
    if role is None:
        conn.close()
        raise HTTPException(status_code=403, detail="Email not authorised to access GemmaWatch.")

    user_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO users (id, email, name, avatar_url, provider, provider_id, role, last_login_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, email.lower(), name, avatar_url, provider, provider_id, role, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {
        "id": user_id, "email": email.lower(), "name": name,
        "avatar_url": avatar_url, "provider": provider,
        "provider_id": provider_id, "role": role,
    }


async def store_refresh_token(db: SQLiteService, user_id: str, token_hash: str) -> str:
    import sqlite3
    from services.sqlite_service import DB_PATH
    token_id = str(uuid.uuid4())
    expires_at = (datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
        (token_id, user_id, token_hash, expires_at),
    )
    conn.commit()
    conn.close()
    return token_id


# ── Google OAuth ──────────────────────────────────────────────────────────────
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_google_auth_url(state: str = "") -> str:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{BACKEND_BASE_URL}/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    from urllib.parse import urlencode
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_google_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": f"{BACKEND_BASE_URL}/auth/google/callback",
            "grant_type": "authorization_code",
        })
        token_resp.raise_for_status()
        tokens = token_resp.json()
        user_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


# ── GitHub OAuth ──────────────────────────────────────────────────────────────
GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def get_github_auth_url(state: str = "") -> str:
    from urllib.parse import urlencode
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": f"{BACKEND_BASE_URL}/auth/github/callback",
        "scope": "read:user user:email",
        "state": state,
    }
    return f"{GITHUB_AUTH_URL}?{urlencode(params)}"


async def exchange_github_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{BACKEND_BASE_URL}/auth/github/callback",
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}

        user_resp = await client.get(GITHUB_USERINFO_URL, headers=headers)
        user_resp.raise_for_status()
        user_data = user_resp.json()

        # GitHub may not expose email publicly — fetch from emails endpoint
        if not user_data.get("email"):
            emails_resp = await client.get(GITHUB_EMAILS_URL, headers=headers)
            if emails_resp.status_code == 200:
                emails = emails_resp.json()
                primary = next((e["email"] for e in emails if e.get("primary") and e.get("verified")), None)
                user_data["email"] = primary

        return user_data


# ── FastAPI dependencies ──────────────────────────────────────────────────────
async def get_current_user(request: Request) -> dict:
    """Dependency: requires authenticated user. Raises 401 if not."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_access_token(token)


async def get_optional_user(request: Request) -> Optional[dict]:
    """Dependency: returns user if authenticated, else None (read-only access)."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        return decode_access_token(token)
    except HTTPException:
        return None


async def require_admin(request: Request) -> dict:
    """Dependency: requires admin role."""
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

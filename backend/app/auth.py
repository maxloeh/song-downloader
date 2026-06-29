"""Authentication: first-run setup, login, and signed session cookies.

The app no longer uses HTTP Basic Auth (which forces an ugly browser prompt and
requires credentials in .env). Instead:

- On first run, if no admin account exists, the UI shows a setup screen.
- Login issues a signed session cookie (HMAC, HttpOnly).
- Admin credentials are stored (password hashed) in the secrets store, so no
  file editing is needed. Existing APP_USERNAME/APP_PASSWORD env vars still work
  as a fallback admin for backward compatibility.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets as pysecrets
import time

from fastapi import HTTPException, Request, Response, status

from .config import get_settings
from .secrets_store import get_secret, set_secret

SESSION_COOKIE = "mdl_session"
SESSION_TTL = 30 * 24 * 3600  # 30 days
WS_TICKET_TTL = 60


# ── server secret (stable across restarts) ───────────────────────────────────
def _server_secret() -> bytes:
    s = get_secret("session_secret")
    if not s:
        s = pysecrets.token_hex(32)
        set_secret("session_secret", s)
    return s.encode()


# ── password hashing ─────────────────────────────────────────────────────────
def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or pysecrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${h}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(_hash_password(password, salt), stored)


# ── admin account ────────────────────────────────────────────────────────────
def _env_admin() -> tuple[str, str] | None:
    s = get_settings()
    if s.app_username and s.app_password and s.app_username != "changeme":
        return s.app_username, s.app_password
    return None


def admin_exists() -> bool:
    return bool(get_secret("admin_username")) or _env_admin() is not None


def setup_needed() -> bool:
    return not admin_exists()


def create_admin(username: str, password: str) -> None:
    set_secret("admin_username", username)
    set_secret("admin_password", _hash_password(password))


def verify_credentials(username: str, password: str) -> bool:
    stored_user = get_secret("admin_username")
    if stored_user:
        stored_pw = get_secret("admin_password") or ""
        return hmac.compare_digest(username, stored_user) and _verify_password(password, stored_pw)
    env = _env_admin()
    if env:
        return hmac.compare_digest(username, env[0]) and hmac.compare_digest(password, env[1])
    return False


# ── sessions ─────────────────────────────────────────────────────────────────
def issue_session(username: str) -> str:
    exp = str(int(time.time()) + SESSION_TTL)
    payload = base64.urlsafe_b64encode(f"{username}|{exp}".encode()).decode()
    sig = hmac.new(_server_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_session(token: str | None) -> str | None:
    if not token:
        return None
    try:
        payload, sig = token.split(".", 1)
        expected = hmac.new(_server_secret(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        username, exp = base64.urlsafe_b64decode(payload).decode().split("|", 1)
        if int(exp) < time.time():
            return None
        return username
    except Exception:
        return None


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_TTL,
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def require_auth(request: Request) -> str:
    """FastAPI dependency: require a valid session cookie."""
    user = verify_session(request.cookies.get(SESSION_COOKIE))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


# ── WebSocket tickets (browsers can't send cookies-as-headers on WS handshakes
#    reliably across setups, so we keep the short-lived ticket flow) ───────────
def issue_ws_ticket(ttl: int = WS_TICKET_TTL) -> str:
    exp = str(int(time.time()) + ttl)
    sig = hmac.new(_server_secret(), f"ws:{exp}".encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{exp}:{sig}".encode()).decode()


def verify_ws_ticket(ticket: str) -> bool:
    try:
        exp_str, sig = base64.urlsafe_b64decode(ticket.encode()).decode().split(":", 1)
        if int(exp_str) < time.time():
            return False
        expected = hmac.new(_server_secret(), f"ws:{exp_str}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False

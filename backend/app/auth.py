"""HTTP Basic Auth dependency + short-lived tickets for the WebSocket.

Browsers don't attach Basic Auth credentials to WebSocket handshakes and the
WebSocket JS API can't set headers, so the frontend first fetches a signed,
short-lived ticket over authenticated HTTP and passes it as a `?ticket=` query
param when opening the socket. Tickets are stateless HMAC tokens.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import get_settings

_security = HTTPBasic()

WS_TICKET_TTL = 60  # seconds


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    settings = get_settings()
    user_ok = secrets.compare_digest(credentials.username, settings.app_username)
    pass_ok = secrets.compare_digest(credentials.password, settings.app_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def _ticket_secret() -> bytes:
    s = get_settings()
    return hashlib.sha256(f"ws-ticket:{s.app_username}:{s.app_password}".encode()).digest()


def issue_ws_ticket(ttl: int = WS_TICKET_TTL) -> str:
    """Mint a signed ticket that authorises a WebSocket connection for `ttl`s."""
    exp = str(int(time.time()) + ttl)
    sig = hmac.new(_ticket_secret(), exp.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{exp}:{sig}".encode()).decode()


def verify_ws_ticket(ticket: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(ticket.encode()).decode()
        exp_str, sig = raw.split(":", 1)
        exp = int(exp_str)
    except Exception:
        return False
    if exp < time.time():
        return False
    expected = hmac.new(_ticket_secret(), exp_str.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)

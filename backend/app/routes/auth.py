"""First-run setup, login, logout, and auth state."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from ..auth import (
    SESSION_COOKIE,
    clear_session_cookie,
    create_admin,
    issue_session,
    set_session_cookie,
    setup_needed,
    verify_credentials,
    verify_session,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str
    password: str


@router.get("/state")
def auth_state(request: Request) -> dict:
    user = verify_session(request.cookies.get(SESSION_COOKIE))
    return {"needs_setup": setup_needed(), "authenticated": bool(user), "username": user}


@router.post("/setup")
def setup(creds: Credentials, response: Response) -> dict:
    if not setup_needed():
        raise HTTPException(status_code=409, detail="An account already exists.")
    username, password = creds.username.strip(), creds.password
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    create_admin(username, password)
    set_session_cookie(response, issue_session(username))
    return {"ok": True, "username": username}


@router.post("/login")
def login(creds: Credentials, response: Response) -> dict:
    username = creds.username.strip()
    if not verify_credentials(username, creds.password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    set_session_cookie(response, issue_session(username))
    return {"ok": True, "username": username}


@router.post("/logout")
def logout(response: Response) -> dict:
    clear_session_cookie(response)
    return {"ok": True}

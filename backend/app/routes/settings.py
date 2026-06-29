"""Runtime settings: connect/disconnect the SoundCloud account via the UI."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_auth
from ..config import get_settings
from ..secrets_store import delete_secret, get_secret, set_secret
from ..sources.soundcloud import verify_soundcloud_token

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SoundcloudTokenBody(BaseModel):
    token: str


def soundcloud_status() -> dict:
    """Where the active token comes from: 'app' (UI), 'env', or none."""
    stored = get_secret("soundcloud_auth_token")
    if stored:
        return {"connected": True, "username": get_secret("soundcloud_username"), "source": "app"}
    if get_settings().soundcloud_auth_token:
        return {"connected": True, "username": None, "source": "env"}
    return {"connected": False, "username": None, "source": None}


@router.get("/soundcloud")
def get_soundcloud(_: str = Depends(require_auth)) -> dict:
    return soundcloud_status()


@router.post("/soundcloud")
async def connect_soundcloud(
    body: SoundcloudTokenBody, _: str = Depends(require_auth)
) -> dict:
    token = body.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token is empty.")
    username = await asyncio.to_thread(verify_soundcloud_token, token)
    if not username:
        raise HTTPException(
            status_code=400,
            detail=(
                "SoundCloud rejected this token. Make sure you're logged in and copied the "
                "full value of the `oauth_token` cookie."
            ),
        )
    set_secret("soundcloud_auth_token", token)
    set_secret("soundcloud_username", username)
    return {"connected": True, "username": username, "source": "app"}


@router.delete("/soundcloud")
def disconnect_soundcloud(_: str = Depends(require_auth)) -> dict:
    delete_secret("soundcloud_auth_token", "soundcloud_username")
    return {"connected": False, "username": None, "source": None}

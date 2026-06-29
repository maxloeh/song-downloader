"""Runtime settings: connect/disconnect the SoundCloud account via the UI."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_auth
from ..config import get_settings
from ..secrets_store import delete_secret, get_secret, set_secret
from ..sources.soundcloud import verify_soundcloud_token
from ..sources.spotify import reset_spotdl_client, verify_spotify_credentials

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SoundcloudTokenBody(BaseModel):
    token: str


class SpotifyCredsBody(BaseModel):
    client_id: str
    client_secret: str


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


def spotify_status() -> dict:
    if get_secret("spotify_client_id") and get_secret("spotify_client_secret"):
        return {"configured": True, "source": "app"}
    s = get_settings()
    if s.spotify_client_id and s.spotify_client_secret:
        return {"configured": True, "source": "env"}
    return {"configured": False, "source": None}


@router.get("/spotify")
def get_spotify(_: str = Depends(require_auth)) -> dict:
    return spotify_status()


@router.post("/spotify")
async def connect_spotify(body: SpotifyCredsBody, _: str = Depends(require_auth)) -> dict:
    cid, secret = body.client_id.strip(), body.client_secret.strip()
    if not cid or not secret:
        raise HTTPException(status_code=400, detail="Client ID and secret are required.")
    ok = await asyncio.to_thread(verify_spotify_credentials, cid, secret)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail="Spotify rejected these credentials. Double-check the Client ID and Secret.",
        )
    set_secret("spotify_client_id", cid)
    set_secret("spotify_client_secret", secret)
    reset_spotdl_client()
    return {"configured": True, "source": "app"}


@router.delete("/spotify")
def disconnect_spotify(_: str = Depends(require_auth)) -> dict:
    delete_secret("spotify_client_id", "spotify_client_secret")
    reset_spotdl_client()
    return {"configured": False, "source": None}

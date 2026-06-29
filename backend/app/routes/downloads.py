"""Download submission, job listing, and live progress WebSocket."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from ..auth import issue_ws_ticket, require_auth, verify_ws_ticket
from ..config import get_settings
from ..models import (
    SUPPORTED_BITRATES,
    SUPPORTED_FORMATS,
    DownloadRequest,
    Job,
)

log = logging.getLogger("music-dl.routes")
router = APIRouter(prefix="/api", tags=["downloads"])


@router.get("/config")
def get_config(_: str = Depends(require_auth)) -> dict:
    """UI bootstrap: supported formats/bitrates and capability flags."""
    from ..sources.spotify import spotify_configured

    s = get_settings()
    return {
        "formats": SUPPORTED_FORMATS,
        "bitrates": SUPPORTED_BITRATES,
        "default_format": s.default_format,
        "default_bitrate": s.default_bitrate,
        "spotify_configured": spotify_configured(),
        "max_concurrent_downloads": s.max_concurrent_downloads,
    }


@router.post("/download")
async def create_download(
    req: DownloadRequest,
    request: Request,
    _: str = Depends(require_auth),
) -> dict:
    queue = request.app.state.queue
    jobs = await queue.submit_urls(req.urls, req.options)
    return {"jobs": [j.model_dump() for j in jobs]}


@router.get("/jobs", response_model=list[Job])
def list_jobs(request: Request, _: str = Depends(require_auth)) -> list[Job]:
    return request.app.state.queue.list_jobs()


@router.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str, request: Request, _: str = Depends(require_auth)) -> Job:
    job = request.app.state.queue.get_job(job_id)
    if job is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/jobs")
async def clear_failed_jobs(request: Request, _: str = Depends(require_auth)) -> dict:
    removed = await request.app.state.queue.clear_failed()
    return {"removed": removed}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, request: Request, _: str = Depends(require_auth)) -> dict:
    ok = await request.app.state.queue.remove_job(job_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Job not found")
    return {"removed": 1}


@router.get("/ws-ticket")
def ws_ticket(_: str = Depends(require_auth)) -> dict:
    """Issue a short-lived ticket the browser uses to open the progress WS."""
    return {"ticket": issue_ws_ticket()}


@router.websocket("/ws")
async def progress_ws(websocket: WebSocket) -> None:
    ticket = websocket.query_params.get("ticket", "")
    if not verify_ws_ticket(ticket):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    queue = websocket.app.state.queue
    sub = queue.broadcaster.subscribe()

    # Send a snapshot of current jobs on connect.
    try:
        await websocket.send_json(
            {"type": "snapshot", "jobs": [j.model_dump() for j in queue.list_jobs()]}
        )
        while True:
            event = await sub.get()
            if websocket.client_state != WebSocketState.CONNECTED:
                break
            await websocket.send_json(event)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("ws error: %s", exc)
    finally:
        queue.broadcaster.unsubscribe(sub)

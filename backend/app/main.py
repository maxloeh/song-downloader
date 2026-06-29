"""FastAPI application: wires config, DB, queue, routes, and static frontend."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import Database
from .queue import JobQueue
from .routes import auth as auth_routes
from .routes import downloads, files, settings as settings_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("music-dl")

# Path to the built React frontend (Dockerfile copies dist/ here).
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "static"


async def _idle_watcher(app: FastAPI, minutes: int) -> None:
    """Stop the process after `minutes` of no requests and no active downloads.

    With the launcher's `--restart no`, a clean exit stops the container; the
    user just hits Start again. Active/queued jobs always keep it alive.
    """
    timeout = minutes * 60
    while True:
        await asyncio.sleep(60)
        idle = time.monotonic() - app.state.last_activity
        if idle < timeout or app.state.queue.has_pending():
            continue
        log.info("Idle for %.0f min with no active downloads — shutting down.", idle / 60)
        os.kill(os.getpid(), signal.SIGTERM)  # graceful uvicorn shutdown
        return


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.download_dir.mkdir(parents=True, exist_ok=True)

    db = Database(settings.db_path)
    await db.init()

    queue = JobQueue(settings, db)
    await queue.start()

    app.state.settings = settings
    app.state.db = db
    app.state.queue = queue
    app.state.last_activity = time.monotonic()

    idle_task = None
    if settings.idle_shutdown_minutes > 0:
        idle_task = asyncio.create_task(_idle_watcher(app, settings.idle_shutdown_minutes))
        log.info("Idle auto-stop enabled: %d min.", settings.idle_shutdown_minutes)

    log.info("music-dl ready; downloads -> %s", settings.download_dir)
    try:
        yield
    finally:
        if idle_task:
            idle_task.cancel()
        await queue.stop()


app = FastAPI(title="Music Downloader", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def track_activity(request: Request, call_next):
    # Any real request counts as activity; ignore health checks so external
    # monitors don't keep an idle instance alive forever.
    if request.url.path != "/api/health":
        app.state.last_activity = time.monotonic()
    return await call_next(request)


app.include_router(auth_routes.router)
app.include_router(downloads.router)
app.include_router(files.router)
app.include_router(settings_routes.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ── Static frontend ──────────────────────────────────────────────────────────
# Mount built assets if present; otherwise serve a placeholder so the container
# still boots before the frontend is built.
if (FRONTEND_DIR / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIR / "assets"),
        name="assets",
    )


@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    """Serve the React SPA shell (the app gates itself via /api/auth/state;
    all data endpoints stay protected by the session cookie)."""
    # Never let the SPA catch-all shadow the API.
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        return JSONResponse(
            {
                "detail": "Frontend not built yet. Run the multi-stage Docker build, "
                "or `npm run build` in frontend/ and copy dist/ to backend/static/."
            },
            status_code=200,
        )

    # Serve a real static file if it exists (favicon, etc.), else the SPA shell.
    candidate = FRONTEND_DIR / full_path
    if full_path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(index)

"""FastAPI application: wires config, DB, queue, routes, and static frontend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth import require_auth
from .config import get_settings
from .db import Database
from .queue import JobQueue
from .routes import downloads, files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("music-dl")

# Path to the built React frontend (Dockerfile copies dist/ here).
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "static"


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
    log.info("music-dl ready; downloads -> %s", settings.download_dir)
    try:
        yield
    finally:
        await queue.stop()


app = FastAPI(title="Music Downloader", version="0.1.0", lifespan=lifespan)

app.include_router(downloads.router)
app.include_router(files.router)


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
def serve_spa(full_path: str, _: str = Depends(require_auth)):
    """Serve the React SPA (auth-gated), falling back to index.html for routes."""
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

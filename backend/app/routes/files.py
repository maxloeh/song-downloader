"""File listing, single-file serving, and zip-all download.

All paths are validated to stay inside DOWNLOAD_DIR to prevent path traversal.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from ..auth import require_auth
from ..config import get_settings

router = APIRouter(prefix="/api/files", tags=["files"])

_AUDIO_EXTS = {".mp3", ".m4a", ".opus", ".flac", ".ogg", ".wav"}


def _download_root() -> Path:
    return get_settings().download_dir.resolve()


def _safe_resolve(rel: str) -> Path:
    """Resolve `rel` under the download root, rejecting traversal."""
    root = _download_root()
    candidate = (root / rel).resolve()
    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid path")
    return candidate


@router.get("")
def list_files(_: str = Depends(require_auth)) -> list[dict]:
    """List downloaded audio files, newest first."""
    root = _download_root()
    if not root.exists():
        return []
    items: list[dict] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _AUDIO_EXTS:
            continue
        # Skip internal app data (e.g. the sqlite dir).
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        stat = path.stat()
        items.append(
            {
                "path": str(path.relative_to(root)),
                "name": path.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }
        )
    items.sort(key=lambda i: i["modified"], reverse=True)
    return items


@router.get("/download")
def download_file(
    path: str = Query(..., description="Path relative to the download dir"),
    _: str = Depends(require_auth),
) -> FileResponse:
    target = _safe_resolve(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        target, filename=target.name, media_type="application/octet-stream"
    )


@router.get("/zip")
def download_zip(
    path: str | None = Query(
        default=None, description="Optional subfolder to zip; defaults to everything"
    ),
    _: str = Depends(require_auth),
) -> StreamingResponse:
    root = _download_root()
    base = _safe_resolve(path) if path else root
    if not base.exists():
        raise HTTPException(status_code=404, detail="Nothing to zip")

    files = [
        p
        for p in (base.rglob("*") if base.is_dir() else [base])
        if p.is_file()
        and p.suffix.lower() in _AUDIO_EXTS
        and not any(part.startswith(".") for part in p.relative_to(root).parts)
    ]
    if not files:
        raise HTTPException(status_code=404, detail="No audio files to zip")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=str(f.relative_to(base.parent if base.is_dir() else root)))
    buffer.seek(0)

    name = (base.name or "downloads") if base.is_dir() else base.stem
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}.zip"'},
    )

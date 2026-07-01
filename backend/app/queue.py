"""Async job queue, worker pool, in-memory registry and progress broadcasting.

The queue owns the lifecycle of every Job: it enumerates URLs into tracks,
fans them out into per-track jobs, runs the blocking download in a thread, runs
metadata verification, persists state to SQLite, and pushes every change to
subscribed WebSocket clients.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .config import Settings
from .db import Database
from .metadata import verify_and_fix
from .models import (
    DownloadOptions,
    Job,
    JobStatus,
    SourceType,
    TrackRef,
)
from .sources import resolve_source
from .sources.base import UnsupportedURLError

log = logging.getLogger("music-dl.queue")


def _humanize_error(exc: object, fallback_enabled: bool) -> str:
    """Translate noisy engine errors into actionable, context-aware messages.

    Tailors the advice to whether a SoundCloud account is connected and whether
    the YouTube fallback was enabled for this job.
    """
    from .sources.soundcloud import get_soundcloud_token

    msg = str(exc)
    low = msg.lower()
    connected = bool(get_soundcloud_token())

    drm = any(s in low for s in ("drm protected", "no video formats", "no formats",
                                 "only images are available"))
    forbidden = "http error 403" in low or "forbidden" in low
    if not (drm or forbidden):
        return msg

    if drm:
        parts = [
            "SoundCloud serves this track only as protected/encrypted streams, so it can't be "
            "downloaded directly from SoundCloud."
        ]
    else:
        parts = [
            "SoundCloud denied access to this track's file (HTTP 403) — the uploader has "
            "disabled downloads."
        ]
    # Suggesting "connect your account" only makes sense if it isn't already.
    if forbidden and not connected:
        parts.append("If it's a private track you have access to, connect your SoundCloud "
                     "account (panel above).")
    # The real fix for protected/disabled tracks is the YouTube fallback.
    if fallback_enabled:
        parts.append("A matching YouTube source couldn't be downloaded either.")
    else:
        parts.append("Turn on “fall back to a YouTube match” above and retry to fetch "
                     "it from YouTube instead.")
    return " ".join(parts)


class Broadcaster:
    """Fan-out of job events to connected WebSocket clients."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, event: dict) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


class JobQueue:
    def __init__(self, settings: Settings, db: Database) -> None:
        self._settings = settings
        self._db = db
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._jobs: dict[str, Job] = {}
        self._workers: list[asyncio.Task] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self.broadcaster = Broadcaster()

    # ── lifecycle ────────────────────────────────────────────────────────────
    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        # Restore history into the registry (but don't requeue old work).
        for job in await self._db.load_recent():
            # Mark jobs that were mid-flight at shutdown as failed.
            if job.status in (JobStatus.QUEUED, JobStatus.DOWNLOADING, JobStatus.CONVERTING):
                job.status = JobStatus.FAILED
                job.error = "Interrupted by server restart"
            self._jobs[job.id] = job
        n = self._settings.max_concurrent_downloads
        self._workers = [asyncio.create_task(self._worker(i)) for i in range(n)]
        log.info("Job queue started with %d workers", n)

    async def stop(self) -> None:
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    # ── public API ───────────────────────────────────────────────────────────
    def list_jobs(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def has_pending(self) -> bool:
        """True if any job is queued / downloading / converting."""
        active = {JobStatus.QUEUED, JobStatus.DOWNLOADING, JobStatus.CONVERTING}
        return any(j.status in active for j in self._jobs.values())

    def submit_urls(self, urls: list[str], options: DownloadOptions) -> None:
        """Kick off enumeration in the background; returns immediately.

        Each URL gets a 'Resolving…' placeholder right away (streamed to the UI
        over the WebSocket); enumeration then replaces it with one job per track,
        or marks it failed. Enumeration can be slow (Spotify playlists), so it
        must never block the HTTP request.
        """
        for raw in urls:
            url = raw.strip()
            if url:
                asyncio.create_task(self._resolve_and_enqueue(url, options))

    async def _resolve_and_enqueue(self, url: str, options: DownloadOptions) -> None:
        try:
            source = resolve_source(url)
        except UnsupportedURLError as exc:
            await self._register(
                Job(source=SourceType.SOUNDCLOUD, url=url, options=options,
                    status=JobStatus.FAILED, error=str(exc))
            )
            return

        # Immediate placeholder so the user sees feedback while it resolves.
        placeholder = Job(
            source=source.source_type, url=url, options=options,
            title="Resolving tracks…", status=JobStatus.QUEUED,
        )
        await self._register(placeholder)

        try:
            tracks = await asyncio.to_thread(source.enumerate, url)
        except Exception as exc:
            log.exception("enumerate failed for %s", url)
            placeholder.status = JobStatus.FAILED
            placeholder.title = None
            placeholder.error = _humanize_error(exc, options.youtube_fallback)
            await self._persist_update(placeholder)
            return

        # Replace the placeholder with one real job per resolved track.
        await self.remove_job(placeholder.id)
        for track in tracks:
            job = Job(
                source=track.source,
                url=track.url,
                title=track.title,
                playlist=track.playlist,
                artwork_url=track.artwork_url,
                artist=track.artist,
                duration=track.duration,
                options=options,
            )
            await self._register(job)
            await self._queue.put(job)

    async def remove_job(self, job_id: str) -> bool:
        job = self._jobs.pop(job_id, None)
        if job is None:
            return False
        await self._db.delete(job_id)
        self.broadcaster.publish({"type": "remove", "id": job_id})
        return True

    async def clear_failed(self) -> int:
        ids = [j.id for j in self._jobs.values() if j.status == JobStatus.FAILED]
        for jid in ids:
            await self.remove_job(jid)
        return len(ids)

    # ── internals ────────────────────────────────────────────────────────────
    async def _register(self, job: Job) -> None:
        self._jobs[job.id] = job
        await self._db.upsert(job)
        self.broadcaster.publish({"type": "job", "job": job.model_dump()})

    def _publish_update(self, job: Job) -> None:
        job.touch()
        self.broadcaster.publish({"type": "job", "job": job.model_dump()})

    async def _persist_update(self, job: Job) -> None:
        self._publish_update(job)
        await self._db.upsert(job)

    async def _worker(self, idx: int) -> None:
        while True:
            job = await self._queue.get()
            try:
                await self._run_job(job)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                log.exception("worker %d crashed on job %s", idx, job.id)
                job.status = JobStatus.FAILED
                job.error = str(exc)
                await self._persist_update(job)
            finally:
                self._queue.task_done()

    async def _run_job(self, job: Job) -> None:
        source = resolve_source(job.url)
        track = TrackRef(
            url=job.url,
            source=job.source,
            title=job.title,
            artist=job.artist,
            artwork_url=job.artwork_url,
            duration=job.duration,
            playlist=job.playlist,
        )

        job.status = JobStatus.DOWNLOADING
        await self._persist_update(job)

        loop = asyncio.get_running_loop()

        # Progress callback runs inside the worker thread; marshal onto the loop.
        def on_progress(pct: float, label: str, audio_source: str | None) -> None:
            def apply() -> None:
                job.progress = round(pct, 1)
                if audio_source:
                    job.audio_source = audio_source
                if label == "converting" and job.status != JobStatus.CONVERTING:
                    job.status = JobStatus.CONVERTING
                elif label == "downloading" and job.status != JobStatus.DOWNLOADING:
                    job.status = JobStatus.DOWNLOADING
                self._publish_update(job)

            loop.call_soon_threadsafe(apply)

        try:
            path: Path = await asyncio.to_thread(
                source.download, track, job.options, on_progress
            )
        except Exception as exc:
            log.exception("download failed for %s", job.url)
            job.status = JobStatus.FAILED
            job.error = _humanize_error(exc, job.options.youtube_fallback)
            job.progress = 0.0
            await self._persist_update(job)
            return

        # Metadata verification / fixups (best-effort). Pass the artwork URL so a
        # cover can be embedded even for WAV (and any file the source didn't tag).
        try:
            await asyncio.to_thread(verify_and_fix, path, job.artwork_url)
        except Exception as exc:
            log.warning("metadata verify failed for %s: %s", path, exc)

        job.status = JobStatus.DONE
        job.progress = 100.0
        job.output_path = self._relative_path(path)
        if not job.title:
            job.title = path.stem
        await self._persist_update(job)

    def _relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self._settings.download_dir))
        except ValueError:
            return path.name

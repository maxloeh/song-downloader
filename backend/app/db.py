"""SQLite persistence for job history.

Kept deliberately small: a single `jobs` table holding the JSON-serialisable
Job fields. Writes happen off the event loop via `asyncio.to_thread`.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from .models import Job

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id           TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    url          TEXT NOT NULL,
    title        TEXT,
    playlist     TEXT,
    artwork_url  TEXT,
    options      TEXT NOT NULL,
    status       TEXT NOT NULL,
    progress     REAL NOT NULL,
    audio_source TEXT,
    output_path  TEXT,
    error        TEXT,
    created_at   REAL NOT NULL,
    updated_at   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_sync(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            # Migrate older DBs that predate the artwork_url column.
            cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
            if "artwork_url" not in cols:
                conn.execute("ALTER TABLE jobs ADD COLUMN artwork_url TEXT")

    async def init(self) -> None:
        await asyncio.to_thread(self._init_sync)

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        data = dict(row)
        data["options"] = json.loads(data["options"])
        return Job.model_validate(data)

    def _upsert_sync(self, job: Job) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, source, url, title, playlist, artwork_url, options,
                                  status, progress, audio_source, output_path, error,
                                  created_at, updated_at)
                VALUES (:id, :source, :url, :title, :playlist, :artwork_url, :options,
                        :status, :progress, :audio_source, :output_path, :error,
                        :created_at, :updated_at)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    playlist=excluded.playlist,
                    artwork_url=excluded.artwork_url,
                    status=excluded.status,
                    progress=excluded.progress,
                    audio_source=excluded.audio_source,
                    output_path=excluded.output_path,
                    error=excluded.error,
                    updated_at=excluded.updated_at
                """,
                {
                    "id": job.id,
                    "source": job.source.value,
                    "url": job.url,
                    "title": job.title,
                    "playlist": job.playlist,
                    "artwork_url": job.artwork_url,
                    "options": json.dumps(job.options.model_dump()),
                    "status": job.status.value,
                    "progress": job.progress,
                    "audio_source": job.audio_source,
                    "output_path": job.output_path,
                    "error": job.error,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                },
            )

    async def upsert(self, job: Job) -> None:
        async with self._lock:
            await asyncio.to_thread(self._upsert_sync, job)

    def _load_sync(self, limit: int) -> list[Job]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_job(r) for r in rows]

    async def load_recent(self, limit: int = 500) -> list[Job]:
        return await asyncio.to_thread(self._load_sync, limit)

    def _delete_sync(self, job_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))

    async def delete(self, job_id: str) -> None:
        async with self._lock:
            await asyncio.to_thread(self._delete_sync, job_id)

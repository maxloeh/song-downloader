"""Domain models: enums, track/option DTOs, and the Job registry entity."""

from __future__ import annotations

import time
import uuid
from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    SOUNDCLOUD = "soundcloud"
    SPOTIFY = "spotify"


class JobStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    CONVERTING = "converting"
    DONE = "done"
    FAILED = "failed"


# Formats / bitrates the UI exposes. Kept here so frontend and backend agree.
SUPPORTED_FORMATS = ["mp3", "m4a", "opus", "flac", "ogg", "wav"]
SUPPORTED_BITRATES = ["128k", "192k", "256k", "320k", "best"]


class DownloadOptions(BaseModel):
    """Per-request download options chosen in the UI."""

    format: str = "mp3"
    bitrate: str = "320k"
    # SoundCloud only: request the uploader's original file when available.
    soundcloud_original: bool = False
    # When SoundCloud can't serve a track (DRM/blocked), match it on YouTube.
    youtube_fallback: bool = True


class TrackRef(BaseModel):
    """A single resolvable track. A playlist enumerates to many of these."""

    url: str
    source: SourceType
    title: str | None = None
    artist: str | None = None
    artwork_url: str | None = None
    # The playlist/album this track belongs to, used for the output folder.
    playlist: str | None = None


class DownloadRequest(BaseModel):
    """Body of POST /api/download."""

    urls: list[str] = Field(min_length=1)
    options: DownloadOptions = DownloadOptions()


class Job(BaseModel):
    """A unit of work in the queue + its persisted history record."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source: SourceType
    url: str
    title: str | None = None
    playlist: str | None = None
    artwork_url: str | None = None
    options: DownloadOptions
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0  # 0..100
    # Audio provider actually used (e.g. "youtube-music") — surfaced in the UI.
    audio_source: str | None = None
    output_path: str | None = None  # relative to DOWNLOAD_DIR
    error: str | None = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def touch(self) -> None:
        self.updated_at = time.time()

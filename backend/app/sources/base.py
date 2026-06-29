"""Source interface + URL -> Source resolver.

Each concrete source knows how to (a) claim a URL, (b) enumerate that URL into
one or more concrete tracks, and (c) download a single track to disk while
reporting progress.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

from ..models import DownloadOptions, SourceType, TrackRef

# (progress 0..100, status_label, audio_source|None)
ProgressCallback = Callable[[float, str, str | None], None]


@runtime_checkable
class Source(Protocol):
    source_type: SourceType

    def matches(self, url: str) -> bool:
        """True if this source can handle the URL."""

    def enumerate(self, url: str) -> list[TrackRef]:
        """Expand a URL into individual tracks (1 for a track, N for a set)."""

    def download(
        self,
        track: TrackRef,
        opts: DownloadOptions,
        on_progress: ProgressCallback,
    ) -> Path:
        """Download a single track, returning the final file path.

        Runs in a worker thread (yt-dlp / spotdl are blocking), so it is a plain
        synchronous method.
        """


class UnsupportedURLError(ValueError):
    """Raised when no source claims a URL."""


def _build_sources() -> list[Source]:
    # Imported lazily to avoid importing yt-dlp/spotdl at module import time.
    from .soundcloud import SoundCloudSource
    from .spotify import SpotifySource

    return [SoundCloudSource(), SpotifySource()]


_SOURCES: list[Source] | None = None


def resolve_source(url: str) -> Source:
    """Return the Source able to handle `url`, or raise UnsupportedURLError."""
    global _SOURCES
    if _SOURCES is None:
        _SOURCES = _build_sources()
    for source in _SOURCES:
        if source.matches(url):
            return source
    raise UnsupportedURLError(
        f"Unsupported URL (not a recognised SoundCloud or Spotify link): {url}"
    )

"""Spotify source, backed by spotDL.

spotDL is a metadata-matching engine: it reads track metadata from the Spotify
API, finds the closest match on YouTube Music / YouTube, downloads *that* audio
with yt-dlp, and embeds the Spotify metadata + cover. The audio therefore comes
from YouTube and is bitrate-capped by that source — surfaced to the user.
"""

from __future__ import annotations

import re
import threading
from pathlib import Path

from ..config import get_settings
from ..models import DownloadOptions, SourceType, TrackRef
from .base import ProgressCallback

_HOST_RE = re.compile(r"https?://(?:open|play)\.spotify\.com/", re.IGNORECASE)
_URI_RE = re.compile(r"^spotify:(track|album|playlist):", re.IGNORECASE)

# spotDL is initialised once (it spins up a downloader + Spotify client).
_spotdl_lock = threading.Lock()
_spotdl_client = None
_spotdl_format: str | None = None
_spotdl_bitrate: str | None = None


def _spotdl_bitrate_value(bitrate: str) -> str:
    return "disable" if bitrate == "best" else bitrate


def _get_spotdl(opts: DownloadOptions):
    """Lazily build (and memoise) a configured Spotdl client for these options."""
    global _spotdl_client, _spotdl_format, _spotdl_bitrate
    from spotdl import Spotdl

    settings = get_settings()
    with _spotdl_lock:
        if (
            _spotdl_client is not None
            and _spotdl_format == opts.format
            and _spotdl_bitrate == opts.bitrate
        ):
            return _spotdl_client

        downloader_settings = {
            "output": str(settings.download_dir / "{list-name}" / "{artists} - {title}.{output-ext}"),
            "format": opts.format,
            "bitrate": _spotdl_bitrate_value(opts.bitrate),
            "audio_providers": settings.spotdl_audio_providers,
            "threads": 1,
            "print_errors": False,
            "simple_tui": True,
        }
        client = Spotdl(
            client_id=settings.spotify_client_id or "5f573c9620494bae87890c0f08a60293",
            client_secret=settings.spotify_client_secret or "212476d9b0f3472eaa762d90b19b0ba8",
            no_cache=not settings.spotify_configured,
            downloader_settings=downloader_settings,
        )
        _spotdl_client = client
        _spotdl_format = opts.format
        _spotdl_bitrate = opts.bitrate
        return client


class SpotifySource:
    source_type = SourceType.SPOTIFY

    def matches(self, url: str) -> bool:
        u = url.strip()
        return bool(_HOST_RE.search(u) or _URI_RE.match(u))

    def enumerate(self, url: str) -> list[TrackRef]:
        client = _get_spotdl(DownloadOptions())
        songs = client.search([url])
        # Use the album/playlist name as folder when more than one song.
        playlist = None
        if len(songs) > 1:
            first = songs[0]
            playlist = getattr(first, "list_name", None) or getattr(first, "album_name", None)
        refs: list[TrackRef] = []
        for song in songs:
            title = f"{song.artist} - {song.name}" if song.artist else song.name
            refs.append(
                TrackRef(
                    url=song.url,
                    source=SourceType.SPOTIFY,
                    title=title,
                    playlist=playlist or getattr(song, "list_name", None),
                )
            )
        return refs

    def download(
        self,
        track: TrackRef,
        opts: DownloadOptions,
        on_progress: ProgressCallback,
    ) -> Path:
        client = _get_spotdl(opts)

        on_progress(5.0, "downloading", "youtube-music")
        songs = client.search([track.url])
        if not songs:
            raise RuntimeError(f"spotDL could not resolve the Spotify URL: {track.url}")
        song = songs[0]

        on_progress(20.0, "downloading", "youtube-music")
        _song, path = client.download(song)
        if path is None:
            raise RuntimeError(
                f"spotDL found no downloadable YouTube match for: {track.title or track.url}"
            )

        on_progress(100.0, "done", getattr(song, "download_url", None) or "youtube-music")
        return Path(path)

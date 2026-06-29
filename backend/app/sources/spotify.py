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

# spotDL's SpotifyClient is a process-global singleton that can only be
# initialised ONCE. So we build the Spotdl client a single time and just adjust
# its per-download format/bitrate, rather than reconstructing it.
_spotdl_lock = threading.Lock()
_spotdl_client = None
# spotDL isn't safe for concurrent use from our worker threads (shared client +
# internal asyncio), so all spotDL search/download calls are serialized.
_spotdl_op_lock = threading.Lock()


def _spotdl_bitrate_value(bitrate: str) -> str:
    return "disable" if bitrate == "best" else bitrate


def _bind_spotdl_loop(client) -> None:
    """Make the current worker thread use spotDL's own event loop.

    spotDL runs `self.loop.run_until_complete(asyncio.gather(...))`, and gather
    binds futures to the *current* thread's loop. Since our download workers run
    in rotating threads, we must point each at spotDL's loop or the futures end
    up "on a different loop". Calls are serialized so the loop is never run
    concurrently.
    """
    import asyncio

    asyncio.set_event_loop(client.downloader.loop)


def get_spotify_credentials() -> tuple[str, str]:
    """(client_id, client_secret); UI-entered (persisted) takes precedence."""
    from ..secrets_store import get_secret

    settings = get_settings()
    cid = get_secret("spotify_client_id") or settings.spotify_client_id
    secret = get_secret("spotify_client_secret") or settings.spotify_client_secret
    return cid or "", secret or ""


def spotify_configured() -> bool:
    cid, secret = get_spotify_credentials()
    return bool(cid and secret)


def verify_spotify_credentials(client_id: str, client_secret: str) -> bool:
    """Validate creds via Spotify's client-credentials token endpoint."""
    import base64
    import json
    import urllib.parse
    import urllib.request

    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=body,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
        return bool(data.get("access_token"))
    except Exception:
        return False


def reset_spotdl_client() -> None:
    """Drop our client AND spotDL's singleton so it can re-init with new creds."""
    global _spotdl_client
    with _spotdl_lock:
        _spotdl_client = None
        try:
            from spotdl.utils.spotify import SpotifyClient

            SpotifyClient._instance = None
        except Exception:
            pass


def _build_spotdl():
    from spotdl import Spotdl

    settings = get_settings()
    cid, secret = get_spotify_credentials()
    downloader_settings = {
        "output": str(settings.download_dir / "{list-name}" / "{artists} - {title}.{output-ext}"),
        "format": settings.default_format,
        "bitrate": _spotdl_bitrate_value(settings.default_bitrate),
        "audio_providers": settings.spotdl_audio_provider_list,
        "threads": 1,
        "print_errors": False,
        "simple_tui": True,
    }
    return Spotdl(
        client_id=cid or "5f573c9620494bae87890c0f08a60293",
        client_secret=secret or "212476d9b0f3472eaa762d90b19b0ba8",
        no_cache=not spotify_configured(),
        downloader_settings=downloader_settings,
    )


def _get_spotdl(opts: DownloadOptions):
    """Return the singleton Spotdl client, updating its per-download settings.

    spotDL can only initialise its Spotify client once per process, so we build
    it a single time and mutate the downloader's format/bitrate per request.
    """
    global _spotdl_client
    with _spotdl_lock:
        if _spotdl_client is None:
            _spotdl_client = _build_spotdl()
        s = _spotdl_client.downloader.settings
        s["format"] = opts.format
        s["bitrate"] = _spotdl_bitrate_value(opts.bitrate)
        return _spotdl_client


class SpotifySource:
    source_type = SourceType.SPOTIFY

    def matches(self, url: str) -> bool:
        u = url.strip()
        return bool(_HOST_RE.search(u) or _URI_RE.match(u))

    def enumerate(self, url: str) -> list[TrackRef]:
        with _spotdl_op_lock:
            client = _get_spotdl(DownloadOptions())
            _bind_spotdl_loop(client)
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
                    artist=getattr(song, "artist", None),
                    artwork_url=getattr(song, "cover_url", None),
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
        on_progress(5.0, "downloading", "youtube-music")
        with _spotdl_op_lock:
            client = _get_spotdl(opts)
            _bind_spotdl_loop(client)
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

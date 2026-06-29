"""SoundCloud source, backed by yt-dlp's Python API.

Enumeration uses SoundCloud's resolve API (via yt-dlp's extractor client) so a
track's title/artist are available even when its streams are DRM-protected —
which lets us fall back to a YouTube match for tracks SoundCloud won't serve.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from pathlib import Path

from ..config import get_settings
from ..models import DownloadOptions, SourceType, TrackRef
from .base import ProgressCallback

log = logging.getLogger("music-dl.soundcloud")

_HOST_RE = re.compile(r"https?://[^/]*soundcloud\.com", re.IGNORECASE)

# Containers ffmpeg can embed cover art into. WAV notably cannot, so embedding
# must be skipped for it or the whole download fails at post-processing.
_EMBED_THUMBNAIL_FORMATS = {"mp3", "m4a", "opus", "ogg", "flac"}

_API_V2 = "https://api-v2.soundcloud.com"

# Substrings that mean "SoundCloud can't/won't serve this stream" → try YouTube.
_FALLBACK_SIGNALS = (
    "drm protected",
    "no video formats",
    "no formats",
    "requested format is not available",
    "http error 403",
    "http error 404",
    "geo",
    "not available",
    "no longer available",
    "private",
)


def get_soundcloud_token() -> str:
    """Active SoundCloud OAuth token: UI-entered (persisted) takes precedence."""
    from ..secrets_store import get_secret

    return get_secret("soundcloud_auth_token") or get_settings().soundcloud_auth_token


def _sc_api_client():
    """Return (ydl, ie, client_id, headers) for direct SoundCloud API calls."""
    import yt_dlp

    ydl = yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True})
    ie = ydl.get_info_extractor("Soundcloud")
    ie.initialize()
    token = get_soundcloud_token()
    headers = {"Authorization": f"OAuth {token}"} if token else {}
    return ydl, ie, getattr(ie, "_CLIENT_ID", None), headers


def verify_soundcloud_token(token: str) -> str | None:
    """Validate an OAuth token against SoundCloud; return the username or None."""
    import yt_dlp

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            ie = ydl.get_info_extractor("Soundcloud")
            ie.initialize()
            client_id = getattr(ie, "_CLIENT_ID", None)
            if not client_id:
                return None
            data = ie._download_json(
                f"{_API_V2}/me?client_id={client_id}",
                "me",
                note="Verifying SoundCloud token",
                headers={"Authorization": f"OAuth {token}"},
            )
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data.get("username") or data.get("permalink") or data.get("full_name")


def split_artist_title(raw_title: str) -> tuple[str | None, str]:
    """Parse a "Artist - Title" pattern, common in SoundCloud track titles."""
    if not raw_title:
        return None, raw_title
    # Use a hyphen surrounded by spaces to avoid splitting hyphenated words.
    parts = re.split(r"\s[-–—]\s", raw_title, maxsplit=1)
    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
        return parts[0].strip(), parts[1].strip()
    return None, raw_title.strip()


def _audio_postprocessors(opts: DownloadOptions) -> list[dict]:
    """yt-dlp postprocessors for the chosen format/quality + tags + cover."""
    quality = "0" if opts.bitrate == "best" else opts.bitrate.rstrip("k")
    pps: list[dict] = [
        {"key": "FFmpegExtractAudio", "preferredcodec": opts.format, "preferredquality": quality},
        {"key": "FFmpegMetadata", "add_metadata": True},
    ]
    if opts.format in _EMBED_THUMBNAIL_FORMATS:
        pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
    return pps


def _should_fallback(exc: Exception) -> bool:
    low = str(exc).lower()
    return any(sig in low for sig in _FALLBACK_SIGNALS)


def download_via_youtube(
    track: TrackRef, opts: DownloadOptions, on_progress: ProgressCallback
) -> Path:
    """Find the closest YouTube match for a track and download its audio.

    Used as a fallback when SoundCloud won't serve the stream. Not a DRM bypass:
    the audio comes from a different public host (same idea as the Spotify path).
    """
    import yt_dlp
    from yt_dlp.utils import sanitize_filename

    from ..metadata import set_basic_tags

    settings = get_settings()
    title = track.title or track.url
    # Build a search query; prepend the artist unless it's already in the title.
    if track.artist and track.artist.lower() not in (title or "").lower():
        query = f"{track.artist} {title}"
    else:
        query = title

    safe = sanitize_filename(title, restricted=False) or "track"
    if track.playlist:
        folder = settings.download_dir / sanitize_filename(track.playlist)
    else:
        folder = settings.download_dir
    outtmpl = str(folder / f"{safe}.%(ext)s")

    def hook(d: dict) -> None:
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes") or 0
            pct = (done / total * 100.0) if total else 0.0
            on_progress(min(10 + pct * 0.85, 95.0), "downloading", "youtube")
        elif d.get("status") == "finished":
            on_progress(96.0, "converting", "youtube")

    embed_cover = opts.format in _EMBED_THUMBNAIL_FORMATS
    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "outtmpl": outtmpl,
        "writethumbnail": embed_cover,
        "format": "bestaudio/best",
        "noplaylist": True,
        "default_search": "ytsearch",
        "progress_hooks": [hook],
        "postprocessors": _audio_postprocessors(opts),
    }

    on_progress(8.0, "downloading", "youtube")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=True)
        entries = info.get("entries") if isinstance(info, dict) else None
        if not entries:
            raise RuntimeError(f"No YouTube match found for: {title}")
        entry = entries[0]
        final = Path(ydl.prepare_filename(entry)).with_suffix(f".{opts.format}")

    # Force the clean SoundCloud title; only set artist when the title encodes
    # it ("Artist - Title"), to avoid clobbering YouTube's (often richer)
    # credits with a reposter's handle.
    artist, parsed_title = split_artist_title(title)
    set_basic_tags(final, parsed_title or title, artist)

    on_progress(100.0, "done", "youtube")
    return final


class SoundCloudSource:
    source_type = SourceType.SOUNDCLOUD

    def matches(self, url: str) -> bool:
        return bool(_HOST_RE.search(url.strip()))

    # ── enumerate ────────────────────────────────────────────────────────────
    def enumerate(self, url: str) -> list[TrackRef]:
        try:
            return self._enumerate_via_api(url)
        except Exception as exc:
            log.warning("resolve-API enumerate failed (%s); falling back to yt-dlp", exc)
            return self._enumerate_via_ytdlp(url)

    def _enumerate_via_api(self, url: str) -> list[TrackRef]:
        ydl, ie, cid, headers = _sc_api_client()
        with ydl:
            obj = self._resolve(ie, cid, headers, url)
            kind = obj.get("kind")
            if kind in ("playlist", "system-playlist"):
                playlist = obj.get("title")
                tracks = self._hydrate_tracks(ie, cid, headers, obj.get("tracks") or [])
                return [self._track_ref(t, playlist) for t in tracks if t.get("title")]
            if kind == "track":
                return [self._track_ref(obj, None)]
            raise ValueError(f"Unsupported SoundCloud URL kind: {kind}")

    def _resolve(self, ie, cid: str, headers: dict, url: str) -> dict:
        clean = url.split("?")[0]
        quoted = urllib.parse.quote(clean, safe="")
        return ie._download_json(
            f"{_API_V2}/resolve?url={quoted}&client_id={cid}",
            "resolve",
            note="Resolving SoundCloud URL",
            headers=headers,
        )

    def _hydrate_tracks(self, ie, cid: str, headers: dict, tracks: list[dict]) -> list[dict]:
        """Sets return some tracks as id-only stubs; batch-fetch the missing ones."""
        need = [t["id"] for t in tracks if not t.get("title") and t.get("id")]
        fetched: dict[int, dict] = {}
        for i in range(0, len(need), 50):
            ids = ",".join(str(x) for x in need[i : i + 50])
            try:
                data = ie._download_json(
                    f"{_API_V2}/tracks?ids={ids}&client_id={cid}",
                    "tracks",
                    note=False,
                    headers=headers,
                )
            except Exception:
                continue
            for d in data or []:
                fetched[d["id"]] = d
        out: list[dict] = []
        for t in tracks:
            if t.get("title"):
                out.append(t)
            elif t.get("id") in fetched:
                out.append(fetched[t["id"]])
        return out

    def _track_ref(self, t: dict, playlist: str | None) -> TrackRef:
        return TrackRef(
            url=t.get("permalink_url") or t.get("uri"),
            source=SourceType.SOUNDCLOUD,
            title=t.get("title"),
            artist=(t.get("user") or {}).get("username"),
            playlist=playlist,
        )

    def _enumerate_via_ytdlp(self, url: str) -> list[TrackRef]:
        import yt_dlp

        opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist"}
        self._apply_auth(opts)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if info is None:
            return []
        if info.get("_type") == "playlist" or "entries" in info:
            playlist = info.get("title")
            refs: list[TrackRef] = []
            for entry in info.get("entries") or []:
                if not entry:
                    continue
                refs.append(
                    TrackRef(
                        url=entry.get("url") or entry.get("webpage_url") or entry.get("id"),
                        source=SourceType.SOUNDCLOUD,
                        title=entry.get("title"),
                        artist=entry.get("uploader"),
                        playlist=playlist,
                    )
                )
            return refs
        return [
            TrackRef(
                url=info.get("webpage_url") or url,
                source=SourceType.SOUNDCLOUD,
                title=info.get("title"),
                artist=info.get("uploader"),
            )
        ]

    # ── download ─────────────────────────────────────────────────────────────
    def download(
        self,
        track: TrackRef,
        opts: DownloadOptions,
        on_progress: ProgressCallback,
    ) -> Path:
        try:
            return self._download_soundcloud(track, opts, on_progress)
        except Exception as exc:
            if opts.youtube_fallback and _should_fallback(exc):
                log.info("SoundCloud unavailable for %s; trying YouTube: %s", track.url, exc)
                return download_via_youtube(track, opts, on_progress)
            raise

    def _download_soundcloud(
        self, track: TrackRef, opts: DownloadOptions, on_progress: ProgressCallback
    ) -> Path:
        import yt_dlp

        settings = get_settings()

        def hook(d: dict) -> None:
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                done = d.get("downloaded_bytes") or 0
                pct = (done / total * 100.0) if total else 0.0
                on_progress(min(pct * 0.95, 95.0), "downloading", "soundcloud")
            elif status == "finished":
                on_progress(96.0, "converting", "soundcloud")

        def pp_hook(d: dict) -> None:
            if d.get("status") == "started":
                on_progress(97.0, "converting", "soundcloud")

        if track.playlist:
            outtmpl = str(
                settings.download_dir / "%(playlist_title|uploader)s" / "%(title)s.%(ext)s"
            )
        else:
            outtmpl = str(settings.download_dir / "%(title)s.%(ext)s")

        embed_cover = opts.format in _EMBED_THUMBNAIL_FORMATS
        ydl_opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": outtmpl,
            "writethumbnail": embed_cover,
            "format": "download/bestaudio/best" if opts.soundcloud_original else "bestaudio/best",
            "progress_hooks": [hook],
            "postprocessor_hooks": [pp_hook],
            "postprocessors": _audio_postprocessors(opts),
            "noplaylist": True,
        }
        self._apply_auth(ydl_opts)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(track.url, download=True)
            final = self._final_filepath(ydl, info, opts)

        on_progress(100.0, "done", "soundcloud")
        return Path(final)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _apply_auth(self, opts: dict) -> None:
        token = get_soundcloud_token()
        if token:
            # yt-dlp's SoundCloud extractor reads the OAuth token via the
            # special "oauth" username (it then sets its own Authorization
            # header for the API calls that resolve stream URLs).
            opts["username"] = "oauth"
            opts["password"] = token

    def _final_filepath(self, ydl, info: dict, opts: DownloadOptions) -> str:
        base = ydl.prepare_filename(info)
        candidate = Path(base).with_suffix(f".{opts.format}")
        if candidate.exists():
            return str(candidate)
        for d in info.get("requested_downloads") or []:
            fp = d.get("filepath")
            if fp and Path(fp).exists():
                return fp
        return str(candidate)

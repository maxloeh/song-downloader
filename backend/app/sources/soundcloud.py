"""SoundCloud source, backed by yt-dlp's Python API."""

from __future__ import annotations

import re
from pathlib import Path

from ..config import get_settings
from ..models import DownloadOptions, SourceType, TrackRef
from .base import ProgressCallback

_SOUNDCLOUD_RE = re.compile(r"^https?://(?:www\.|m\.|on\.)?soundcloud\.com/", re.IGNORECASE)
# "on.soundcloud.com" short links and api links are also accepted via the host check.
_HOST_RE = re.compile(r"https?://[^/]*soundcloud\.com", re.IGNORECASE)

# Containers ffmpeg can embed cover art into. WAV notably cannot, so embedding
# must be skipped for it or the whole download fails at post-processing.
_EMBED_THUMBNAIL_FORMATS = {"mp3", "m4a", "opus", "ogg", "flac"}


def get_soundcloud_token() -> str:
    """Active SoundCloud OAuth token: UI-entered (persisted) takes precedence."""
    from ..secrets_store import get_secret

    return get_secret("soundcloud_auth_token") or get_settings().soundcloud_auth_token


def verify_soundcloud_token(token: str) -> str | None:
    """Validate an OAuth token against SoundCloud; return the username or None.

    Uses yt-dlp to obtain a working client_id, then calls the api-v2 `/me`
    endpoint with the token. Runs network I/O, so call it off the event loop.
    """
    import yt_dlp

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            ie = ydl.get_info_extractor("Soundcloud")
            ie.initialize()
            client_id = getattr(ie, "_CLIENT_ID", None)
            if not client_id:
                return None
            data = ie._download_json(
                f"https://api-v2.soundcloud.com/me?client_id={client_id}",
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


class SoundCloudSource:
    source_type = SourceType.SOUNDCLOUD

    def matches(self, url: str) -> bool:
        return bool(_HOST_RE.search(url.strip()))

    # ── enumerate ────────────────────────────────────────────────────────────
    def enumerate(self, url: str) -> list[TrackRef]:
        import yt_dlp

        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
        }
        self._apply_auth(opts)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info is None:
            return []

        # A playlist/set has "entries"; a single track does not.
        if info.get("_type") == "playlist" or "entries" in info:
            playlist = info.get("title")
            tracks: list[TrackRef] = []
            for entry in info.get("entries") or []:
                if not entry:
                    continue
                track_url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
                tracks.append(
                    TrackRef(
                        url=track_url,
                        source=SourceType.SOUNDCLOUD,
                        title=entry.get("title"),
                        playlist=playlist,
                    )
                )
            return tracks

        return [
            TrackRef(
                url=info.get("webpage_url") or url,
                source=SourceType.SOUNDCLOUD,
                title=info.get("title"),
                playlist=None,
            )
        ]

    # ── download ─────────────────────────────────────────────────────────────
    def download(
        self,
        track: TrackRef,
        opts: DownloadOptions,
        on_progress: ProgressCallback,
    ) -> Path:
        import yt_dlp

        settings = get_settings()
        result_paths: list[str] = []

        def hook(d: dict) -> None:
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                done = d.get("downloaded_bytes") or 0
                pct = (done / total * 100.0) if total else 0.0
                # Cap download phase at 95% so conversion has visible headroom.
                on_progress(min(pct * 0.95, 95.0), "downloading", "soundcloud")
            elif status == "finished":
                on_progress(96.0, "converting", "soundcloud")

        def pp_hook(d: dict) -> None:
            if d.get("status") == "started":
                on_progress(97.0, "converting", "soundcloud")

        # Build a per-track output template. Playlist tracks go in a subfolder.
        if track.playlist:
            outtmpl = str(settings.download_dir / "%(playlist_title|uploader)s" / "%(title)s.%(ext)s")
        else:
            outtmpl = str(settings.download_dir / "%(title)s.%(ext)s")

        embed_cover = opts.format in _EMBED_THUMBNAIL_FORMATS
        ydl_opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": outtmpl,
            # Only fetch the thumbnail when the target container can embed it,
            # otherwise it leaves orphan image files and breaks WAV downloads.
            "writethumbnail": embed_cover,
            "format": "bestaudio/best",
            "progress_hooks": [hook],
            "postprocessor_hooks": [pp_hook],
            "postprocessors": self._postprocessors(opts),
            # Record the final path(s) after post-processing.
            "noplaylist": True,
        }
        self._apply_auth(ydl_opts)

        # SoundCloud "original" download: prefer the uploader-provided file.
        if opts.soundcloud_original:
            ydl_opts["format"] = "download/bestaudio/best"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(track.url, download=True)
            final = self._final_filepath(ydl, info, opts)
            result_paths.append(final)

        on_progress(100.0, "done", "soundcloud")
        return Path(result_paths[0])

    # ── helpers ──────────────────────────────────────────────────────────────
    def _postprocessors(self, opts: DownloadOptions) -> list[dict]:
        pps: list[dict] = []
        if opts.bitrate == "best":
            quality = "0"  # best VBR for codecs that support it
        else:
            quality = opts.bitrate.rstrip("k")
        pps.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": opts.format,
                "preferredquality": quality,
            }
        )
        # Write tags. Then embed cover art, but only for containers that support
        # it (WAV cannot hold a cover and would fail the whole post-process).
        pps.append({"key": "FFmpegMetadata", "add_metadata": True})
        if opts.format in _EMBED_THUMBNAIL_FORMATS:
            pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
        return pps

    def _apply_auth(self, opts: dict) -> None:
        token = get_soundcloud_token()
        if token:
            # yt-dlp's SoundCloud extractor reads the OAuth token via the
            # special "oauth" username (it then sets its own Authorization
            # header for the API calls that resolve stream URLs). Putting the
            # token in http_headers does NOT reach those calls.
            opts["username"] = "oauth"
            opts["password"] = token

    def _final_filepath(self, ydl, info: dict, opts: DownloadOptions) -> str:
        # After FFmpegExtractAudio the extension matches the chosen format.
        base = ydl.prepare_filename(info)
        candidate = Path(base).with_suffix(f".{opts.format}")
        if candidate.exists():
            return str(candidate)
        # Fall back to whatever requested_downloads reports.
        for d in info.get("requested_downloads") or []:
            fp = d.get("filepath")
            if fp and Path(fp).exists():
                return fp
        return str(candidate)

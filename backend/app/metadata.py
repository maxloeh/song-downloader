"""Post-download metadata + cover verification and best-effort fixups.

After a track is written we confirm that title/artist/album/cover are present.
If a cover is missing but a sidecar thumbnail was fetched, we embed it. This is
a safety net on top of the source post-processors; failures here are logged but
never fatal to a download.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .sources.soundcloud import split_artist_title

log = logging.getLogger("music-dl.metadata")

_THUMB_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _find_sidecar_thumbnail(audio_path: Path) -> Path | None:
    for ext in _THUMB_EXTS:
        cand = audio_path.with_suffix(ext)
        if cand.exists():
            return cand
    return None


def set_basic_tags(audio_path: Path, title: str | None, artist: str | None) -> None:
    """Force title/artist tags (used for YouTube-sourced fallback files)."""
    if not audio_path.exists() or not (title or artist):
        return
    try:
        # WAV has no easy interface; write ID3 frames directly.
        if audio_path.suffix.lower() == ".wav":
            from mutagen.id3 import TIT2, TPE1
            from mutagen.wave import WAVE

            audio = WAVE(audio_path)
            if audio.tags is None:
                audio.add_tags()
            if title:
                audio.tags.setall("TIT2", [TIT2(encoding=3, text=title)])
            if artist:
                audio.tags.setall("TPE1", [TPE1(encoding=3, text=artist)])
            audio.save()
            return

        from mutagen import File as MutagenFile

        audio = MutagenFile(audio_path, easy=True)
        if audio is None:
            return
        if title:
            audio["title"] = title
        if artist:
            audio["artist"] = artist
        audio.save()
    except Exception as exc:
        log.warning("could not set tags on %s: %s", audio_path, exc)


def _fetch_image(url: str) -> tuple[bytes | None, str | None]:
    """Download cover art bytes from a URL. Returns (data, mime) or (None, None)."""
    import urllib.request

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "music-dl"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except Exception as exc:
        log.warning("could not fetch cover art %s: %s", url, exc)
        return None, None
    if not data:
        return None, None
    low = (ctype + url).lower()
    mime = "image/png" if "png" in low else "image/jpeg"
    return data, mime


def verify_and_fix(audio_path: Path, artwork_url: str | None = None) -> dict[str, bool]:
    """Return a small report of which fields are present after fixups.

    If a cover is missing, try a sidecar thumbnail first, then fall back to
    downloading `artwork_url` (works for WAV via an ID3 chunk, and for any
    format whose source post-processor didn't embed one).
    """
    report = {"title": False, "artist": False, "album": False, "cover": False}
    try:
        from mutagen import File as MutagenFile
    except Exception as exc:  # pragma: no cover - mutagen always installed in prod
        log.warning("mutagen unavailable, skipping verification: %s", exc)
        return report

    if not audio_path.exists():
        log.warning("verify: file missing: %s", audio_path)
        return report

    # Tag read/fill is best-effort — mutagen's easy reader can return None for
    # some containers (e.g. a WAV with no ID3 yet). Cover embedding below must
    # still run in that case.
    try:
        audio = MutagenFile(audio_path, easy=True)
        if audio is not None:
            tags = audio.tags or {}
            title = (tags.get("title") or [None])[0]
            artist = (tags.get("artist") or [None])[0]
            album = (tags.get("album") or [None])[0]

            # Fill missing artist/title from a "Artist - Title" filename pattern.
            if (not artist or not title) and audio_path.stem:
                parsed_artist, parsed_title = split_artist_title(audio_path.stem)
                changed = False
                if not title and parsed_title:
                    audio["title"] = parsed_title
                    title = parsed_title
                    changed = True
                if not artist and parsed_artist:
                    audio["artist"] = parsed_artist
                    artist = parsed_artist
                    changed = True
                if changed:
                    audio.save()

            report["title"] = bool(title)
            report["artist"] = bool(artist)
            report["album"] = bool(album)
    except Exception as exc:
        # Never let a tag-read/fill issue (e.g. WAV) block cover embedding below.
        log.warning("tag fixup skipped for %s: %s", audio_path, exc)

    report["cover"] = _has_cover(audio_path)

    if not report["cover"]:
        data: bytes | None = None
        mime: str | None = None
        thumb = _find_sidecar_thumbnail(audio_path)
        if thumb:
            data = thumb.read_bytes()
            mime = "image/png" if thumb.suffix.lower() == ".png" else "image/jpeg"
        elif artwork_url:
            data, mime = _fetch_image(artwork_url)

        if data and _embed_cover_bytes(audio_path, data, mime or "image/jpeg"):
            report["cover"] = True
            if thumb:
                thumb.unlink(missing_ok=True)

    if not report["cover"]:
        log.warning("track ended without embedded cover art: %s", audio_path)
    return report


def _has_cover(audio_path: Path) -> bool:
    try:
        from mutagen import File as MutagenFile

        raw = MutagenFile(audio_path)
        if raw is None:
            return False
        # MP3 (ID3 APIC)
        if hasattr(raw, "tags") and raw.tags is not None:
            for key in raw.tags.keys():
                if str(key).startswith("APIC"):
                    return True
        # MP4 / m4a
        if hasattr(raw, "get") and raw.get("covr"):
            return True
        # FLAC / OGG pictures
        if getattr(raw, "pictures", None):
            return True
    except Exception:
        return False
    return False


def _embed_cover_bytes(audio_path: Path, data: bytes, mime: str) -> bool:
    """Embed cover-art bytes for common containers, including WAV (via ID3)."""
    try:
        ext = audio_path.suffix.lower()

        if ext == ".mp3":
            from mutagen.id3 import APIC, ID3

            try:
                tags = ID3(audio_path)
            except Exception:
                tags = ID3()
            tags.delall("APIC")
            tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=data))
            tags.save(audio_path)
            return True

        if ext == ".wav":
            # WAV has no native cover art, but it can carry an ID3 chunk that DJ
            # software (Rekordbox/Serato) and good players read.
            from mutagen.id3 import APIC
            from mutagen.wave import WAVE

            audio = WAVE(audio_path)
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall("APIC")
            audio.tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=data))
            audio.save()
            return True

        if ext in (".m4a", ".mp4"):
            from mutagen.mp4 import MP4, MP4Cover

            fmt = MP4Cover.FORMAT_PNG if mime == "image/png" else MP4Cover.FORMAT_JPEG
            mp4 = MP4(audio_path)
            mp4["covr"] = [MP4Cover(data, imageformat=fmt)]
            mp4.save()
            return True

        if ext == ".flac":
            from mutagen.flac import FLAC, Picture

            pic = Picture()
            pic.type = 3
            pic.mime = mime
            pic.data = data
            flac = FLAC(audio_path)
            flac.clear_pictures()
            flac.add_picture(pic)
            flac.save()
            return True
    except Exception as exc:
        log.warning("cover embed failed for %s: %s", audio_path, exc)
    return False

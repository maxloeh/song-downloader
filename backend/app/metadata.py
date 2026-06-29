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


def verify_and_fix(audio_path: Path) -> dict[str, bool]:
    """Return a small report of which fields are present after fixups."""
    report = {"title": False, "artist": False, "album": False, "cover": False}
    try:
        from mutagen import File as MutagenFile
    except Exception as exc:  # pragma: no cover - mutagen always installed in prod
        log.warning("mutagen unavailable, skipping verification: %s", exc)
        return report

    if not audio_path.exists():
        log.warning("verify: file missing: %s", audio_path)
        return report

    audio = MutagenFile(audio_path, easy=True)
    if audio is None:
        return report

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
            try:
                audio.save()
            except Exception as exc:
                log.warning("could not save tag fixups for %s: %s", audio_path, exc)

    report["title"] = bool(title)
    report["artist"] = bool(artist)
    report["album"] = bool(album)
    report["cover"] = _has_cover(audio_path)

    if not report["cover"]:
        thumb = _find_sidecar_thumbnail(audio_path)
        if thumb and _embed_cover(audio_path, thumb):
            report["cover"] = True

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


def _embed_cover(audio_path: Path, thumb: Path) -> bool:
    """Embed a sidecar image as cover art for common containers."""
    try:
        ext = audio_path.suffix.lower()
        data = thumb.read_bytes()
        mime = "image/png" if thumb.suffix.lower() == ".png" else "image/jpeg"

        if ext == ".mp3":
            from mutagen.id3 import APIC, ID3

            try:
                tags = ID3(audio_path)
            except Exception:
                tags = ID3()
            tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=data))
            tags.save(audio_path)
            return True

        if ext in (".m4a", ".mp4"):
            from mutagen.mp4 import MP4, MP4Cover

            fmt = MP4Cover.FORMAT_PNG if mime == "image/png" else MP4Cover.FORMAT_JPEG
            mp4 = MP4(audio_path)
            mp4["covr"] = [MP4Cover(data, imageformat=fmt)]
            mp4.save()
            return True

        if ext in (".flac",):
            from mutagen.flac import FLAC, Picture

            pic = Picture()
            pic.type = 3
            pic.mime = mime
            pic.data = data
            flac = FLAC(audio_path)
            flac.add_picture(pic)
            flac.save()
            return True
    except Exception as exc:
        log.warning("cover embed failed for %s: %s", audio_path, exc)
    return False

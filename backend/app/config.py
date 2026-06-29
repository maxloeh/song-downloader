"""Application configuration, loaded from environment variables / `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. See `.env.example` for documentation."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Auth
    app_username: str = "changeme"
    app_password: str = "changeme"

    # Spotify Developer credentials
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    # SoundCloud
    soundcloud_auth_token: str = ""

    # Behavior
    max_concurrent_downloads: int = Field(default=3, ge=1, le=16)
    default_format: str = "mp3"
    default_bitrate: str = "320k"
    download_dir: Path = Path("/downloads")
    output_template: str = "%(playlist_title)s/%(title)s.%(ext)s"

    # spotDL audio providers, comma-separated. Kept as a string because
    # pydantic-settings JSON-decodes list-typed env vars before validation,
    # which would reject a plain comma-separated value. Use the
    # `spotdl_audio_provider_list` property to get the parsed list.
    spotdl_audio_providers: str = "youtube-music,youtube"

    # Maintenance / server
    ytdlp_auto_update: bool = True
    host: str = "0.0.0.0"
    port: int = 8080

    # Auto-stop after this many minutes with no requests and no active downloads.
    # 0 disables it. Designed for the launcher (which runs with --restart no, so
    # the process exiting cleanly stops the container). Set 0 for always-on hosts.
    idle_shutdown_minutes: int = 30

    @property
    def spotdl_audio_provider_list(self) -> list[str]:
        return [p.strip() for p in self.spotdl_audio_providers.split(",") if p.strip()]

    @property
    def spotify_configured(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    @property
    def db_path(self) -> Path:
        return self.download_dir / ".music-dl" / "history.sqlite3"


@lru_cache
def get_settings() -> Settings:
    return Settings()

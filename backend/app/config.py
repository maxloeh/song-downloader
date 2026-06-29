"""Application configuration, loaded from environment variables / `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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

    # spotDL audio providers (comma-separated in env -> list here)
    spotdl_audio_providers: list[str] = ["youtube-music", "youtube"]

    # Maintenance / server
    ytdlp_auto_update: bool = True
    host: str = "0.0.0.0"
    port: int = 8080

    @field_validator("spotdl_audio_providers", mode="before")
    @classmethod
    def _split_providers(cls, v: object) -> object:
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @property
    def spotify_configured(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    @property
    def db_path(self) -> Path:
        return self.download_dir / ".music-dl" / "history.sqlite3"


@lru_cache
def get_settings() -> Settings:
    return Settings()

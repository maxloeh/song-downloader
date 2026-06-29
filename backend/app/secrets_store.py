"""Persistent secrets (e.g. the SoundCloud OAuth token) entered via the UI.

Stored as JSON under the download volume so it survives container restarts.
Kept separate from `config.py` (env settings) because these are written at
runtime. File is written atomically and chmod 600.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path


class SecretsStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._data: dict[str, str] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            if self._path.exists():
                self._data = json.loads(self._path.read_text())
        except Exception:
            self._data = {}
        self._loaded = True

    def get(self, key: str) -> str | None:
        with self._lock:
            self._ensure_loaded()
            return self._data.get(key) or None

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._ensure_loaded()
            self._data[key] = value
            self._flush()

    def delete(self, *keys: str) -> None:
        with self._lock:
            self._ensure_loaded()
            for k in keys:
                self._data.pop(k, None)
            self._flush()

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2))
        os.replace(tmp, self._path)
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            pass


_store: SecretsStore | None = None
_store_lock = threading.Lock()


def get_store() -> SecretsStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                from .config import get_settings

                _store = SecretsStore(get_settings().db_path.parent / "secrets.json")
    return _store


def get_secret(key: str) -> str | None:
    return get_store().get(key)


def set_secret(key: str, value: str) -> None:
    get_store().set(key, value)


def delete_secret(*keys: str) -> None:
    get_store().delete(*keys)

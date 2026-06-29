"""Tests for path-traversal safety in file serving."""

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.routes import files


def test_safe_resolve_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "_download_root", lambda: tmp_path.resolve())
    with pytest.raises(HTTPException):
        files._safe_resolve("../../etc/passwd")


def test_safe_resolve_allows_inside(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "_download_root", lambda: tmp_path.resolve())
    (tmp_path / "sub").mkdir()
    resolved = files._safe_resolve("sub/song.mp3")
    assert str(resolved).startswith(str(tmp_path.resolve()))


def test_settings_db_under_download_dir():
    s = get_settings()
    assert s.db_path.parent.name == ".music-dl"

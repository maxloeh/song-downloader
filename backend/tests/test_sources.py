"""Tests for URL source detection and title parsing."""

import pytest

from app.sources.base import UnsupportedURLError, resolve_source
from app.sources.soundcloud import SoundCloudSource, split_artist_title
from app.sources.spotify import SpotifySource


@pytest.mark.parametrize(
    "url",
    [
        "https://soundcloud.com/artist/track",
        "https://www.soundcloud.com/artist/sets/my-playlist",
        "https://m.soundcloud.com/artist/track",
        "https://on.soundcloud.com/abcd",
    ],
)
def test_soundcloud_matches(url):
    assert SoundCloudSource().matches(url)
    assert resolve_source(url).source_type.value == "soundcloud"


@pytest.mark.parametrize(
    "url",
    [
        "https://open.spotify.com/track/abc123",
        "https://open.spotify.com/playlist/xyz",
        "https://open.spotify.com/album/foo",
        "spotify:track:abc123",
    ],
)
def test_spotify_matches(url):
    assert SpotifySource().matches(url)
    assert resolve_source(url).source_type.value == "spotify"


def test_cross_source_no_false_positive():
    sc = SoundCloudSource()
    sp = SpotifySource()
    assert not sc.matches("https://open.spotify.com/track/abc")
    assert not sp.matches("https://soundcloud.com/artist/track")


def test_unsupported_url():
    with pytest.raises(UnsupportedURLError):
        resolve_source("https://example.com/whatever")


@pytest.mark.parametrize(
    "raw,artist,title",
    [
        ("Daft Punk - Around the World", "Daft Punk", "Around the World"),
        ("Some Artist – Em Dash Track", "Some Artist", "Em Dash Track"),
        ("NoSeparatorTitle", None, "NoSeparatorTitle"),
        ("Hyphenated-word only", None, "Hyphenated-word only"),
    ],
)
def test_split_artist_title(raw, artist, title):
    assert split_artist_title(raw) == (artist, title)

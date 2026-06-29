"""Tests for the YouTube fallback candidate scoring."""

from app.sources.soundcloud import _pick_best_match, _score_candidate, _title_similarity


def _c(title, duration, channel="Some Channel"):
    return {"id": "x", "title": title, "duration": duration, "channel": channel}


def test_title_similarity_orders_sensibly():
    q = "Daft Punk Around the World"
    assert _title_similarity(q, "Daft Punk - Around the World") > _title_similarity(
        q, "Some Unrelated Song"
    )


def test_prefers_duration_match():
    target = 200.0
    entries = [
        _c("Artist - Song (1 HOUR loop)", 3600),
        _c("Artist - Song", 203),  # closest to target
        _c("Artist - Song (sped up)", 150),
    ]
    best = _pick_best_match(entries, target, "Artist Song", "Artist")
    assert best["duration"] == 203


def test_topic_channel_bonus_breaks_ties():
    target = 200.0
    entries = [
        _c("Artist - Song", 200, channel="Random Uploads"),
        _c("Artist - Song", 200, channel="Artist - Topic"),
    ]
    best = _pick_best_match(entries, target, "Artist Song", "Artist")
    assert best["channel"] == "Artist - Topic"


def test_junk_penalized_even_if_duration_unknown():
    target = 200.0
    entries = [
        _c("Artist - Song (nightcore)", 198),
        _c("Artist - Song", 210),
    ]
    best = _pick_best_match(entries, target, "Artist Song", "Artist")
    assert "nightcore" not in best["title"].lower()


def test_far_duration_scores_negative():
    # A wildly-off duration should score below a clean in-tolerance match.
    target = 180.0
    near = _score_candidate(_c("Artist - Song", 182), target, "Artist Song", "Artist")
    far = _score_candidate(_c("Artist - Song", 4000), target, "Artist Song", "Artist")
    assert near > far

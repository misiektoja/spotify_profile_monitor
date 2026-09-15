"""Checks missing follow data without replacing known history."""

import json
from unittest.mock import Mock

import pytest

import spotify_profile_monitor as monitor
from test_monitoring_loop import error_alerts_for, profile_snapshot

PERSON = {"name": "Known person", "uri": "spotify:user:known"}


# Builds a snapshot with explicitly known or unavailable follow counts
def follow_profile(count):
    result = profile_snapshot()
    result.update(sp_user_followers_count=count, sp_user_followers_count_available=count is not None, sp_user_followings_count=count)
    return result


# Preserves the difference between absent profile fields and an explicit zero
def test_profile_missing_counts_are_unknown(monkeypatch):
    reply = Mock(status_code=200)
    reply.json.return_value = {"name": "Profile"}
    monkeypatch.setattr(monitor.SESSION, "get", Mock(return_value=reply))
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    result = monitor.spotify_get_user_info("token", "user", False, 0)
    assert result["sp_user_followers_count"] is None
    assert result["sp_user_followings_count"] is None
    reply.json.return_value = {"name": "Profile", "followers_count": 0, "following_count": 0}
    result = monitor.spotify_get_user_info("token", "user", False, 0)
    assert result["sp_user_followers_count"] == result["sp_user_followings_count"] == 0


@pytest.mark.parametrize("function,key", [(monitor.spotify_get_user_followers, "sp_user_followers"), (monitor.spotify_get_user_followings, "sp_user_followings")])
# Rejects malformed lists while retaining missing versus explicit empty responses
def test_follow_list_shapes(monkeypatch, function, key):
    reply = Mock(status_code=200)
    monkeypatch.setattr(monitor.SESSION, "get", Mock(return_value=reply))
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    reply.json.return_value = {}
    assert function("token", "user")[key] is None
    reply.json.return_value = {"profiles": []}
    assert function("token", "user")[key] == []
    reply.json.return_value = {"profiles": "invalid"}
    with pytest.raises(ValueError, match="profiles"):
        function("token", "user")


# Distinguishes an unavailable graph from a usable explicit empty collection
def test_follow_count_resolution():
    assert monitor.spotify_follow_snapshot(follow_profile(None), None, "followers") == (None, None)
    assert monitor.spotify_follow_snapshot(follow_profile(None), [], "followers") == (0, [])
    assert monitor.spotify_follow_snapshot(follow_profile(0), None, "followers") == (0, [])
    assert monitor.spotify_follow_snapshot(follow_profile(2), [], "followers") == (2, None)


# Does not claim an unsupported OAuth follower list is an empty list
def test_oauth_followers_are_unavailable(monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "oauth_user")
    assert monitor.spotify_get_user_followers("token", "user")["sp_user_followers"] is None


# Missing polls retain a saved nonzero baseline and never emit removal events
def test_missing_polls_preserve_history(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "known")
    monkeypatch.setattr(monitor, "JSON_DIR", "")
    events = []
    unknown = {"sp_user_followers": None}
    error_alerts_for(monkeypatch, tmp_path, [follow_profile(1)] + [follow_profile(None)] * 4, 5, follower_answers=[unknown] * 4, initial_followers=[PERSON], following_answers=[{"sp_user_followings": [PERSON]}] + [{"sp_user_followings": None}] * 4, collection_events=events)
    paths = monitor.build_json_history_paths("known", "")
    assert json.loads((tmp_path / paths[0]).read_text()) == [1, [PERSON]]
    assert json.loads((tmp_path / paths[1]).read_text()) == [1, [PERSON]]
    assert events == []
    assert "accepting 0 as the new baseline" not in capsys.readouterr().out


# Restarting with missing data retains the existing history and prints unavailable counts
def test_restart_with_unknown_counts_keeps_files(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "known")
    monkeypatch.setattr(monitor, "JSON_DIR", "")
    paths = monitor.build_json_history_paths("known", "")
    stored = json.dumps([1, [PERSON]])
    for path in paths[:2]:
        (tmp_path / path).write_text(stored)
    events = []
    error_alerts_for(monkeypatch, tmp_path, [follow_profile(None)] * 4, 4, follower_answers=[{"sp_user_followers": None}] * 3, initial_followers=None, following_answers=[{"sp_user_followings": None}] * 4, collection_events=events)
    assert all((tmp_path / path).read_text() == stored for path in paths[:2])
    assert events == []
    output = capsys.readouterr().out
    assert "n/a" in output


# A first known snapshot initializes history without announcing additions
def test_first_available_snapshot_creates_baseline(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "fresh")
    monkeypatch.setattr(monitor, "JSON_DIR", "")
    events = []
    error_alerts_for(monkeypatch, tmp_path, [follow_profile(None), follow_profile(1)], 2, follower_answers=[{"sp_user_followers": [PERSON]}], initial_followers=None, following_answers=[{"sp_user_followings": None}, {"sp_user_followings": [PERSON]}], collection_events=events)
    for path in monitor.build_json_history_paths("fresh", "")[:2]:
        assert json.loads((tmp_path / path).read_text()) == [1, [PERSON]]
    assert events == []


# Explicit zero responses still pass through the configured disappearance threshold
def test_confirmed_zero_is_still_accepted(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER", 3)
    monkeypatch.setattr(monitor, "JSON_DIR", "")
    events = []
    error_alerts_for(monkeypatch, tmp_path, [follow_profile(1)] + [follow_profile(0)] * 3, 4, initial_followers=[PERSON], following_answers=[{"sp_user_followings": [PERSON]}] + [{"sp_user_followings": []}] * 3, collection_events=events)
    assert len(events) == 2
    assert all(event[3:5] == (0, 1) for event in events)


# Unavailable polls interrupt a zero-count streak rather than confirming removal
def test_unknown_poll_resets_zero_confirmation(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER", 3)
    monkeypatch.setattr(monitor, "JSON_DIR", "")
    events = []
    counts = [1, 0, 0, None, 0, 0]
    follower_answers = [{"sp_user_followers": None if count is None else []} for count in counts[1:]]
    following_answers = [{"sp_user_followings": [PERSON]}] + [{"sp_user_followings": None if count is None else []} for count in counts[1:]]
    error_alerts_for(monkeypatch, tmp_path, [follow_profile(count) for count in counts], len(counts), initial_followers=[PERSON], follower_answers=follower_answers, following_answers=following_answers, collection_events=events)
    assert events == []

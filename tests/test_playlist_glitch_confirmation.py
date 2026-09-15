"""Checks that an empty playlist response is confirmed before it replaces a known baseline."""

import json
from unittest.mock import Mock

import pytest

import spotify_profile_monitor as monitor

PLAYLIST = {"uri": "spotify:playlist:aaaaaaaaaaaaaaaaaaaaaa", "owner_uri": "spotify:user:watched"}


# Builds a profile reply for the cookie and client sources
def profile_reply(playlists):
    body = {"name": "Watched", "followers_count": 1, "following_count": 1}
    if playlists is not None:
        body["public_playlists"] = playlists
    return body


# Drives spotify_get_user_info through a scripted sequence of replies
def scripted_profile(monkeypatch, bodies):
    replies = []
    for body in bodies:
        reply = Mock(status_code=200)
        reply.json.return_value = body
        replies.append(reply)
    getter = Mock(side_effect=replies)
    monkeypatch.setattr(monitor.SESSION, "get", getter)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "GET_ALL_PLAYLISTS", True)
    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRY_SLEEP", 0)
    return getter


# A missing field is a broken read, while an empty list may be a user who really has no public playlists
def test_absent_playlist_field_is_distinguished_from_an_empty_one(monkeypatch):
    scripted_profile(monkeypatch, [profile_reply(None), profile_reply([])])

    absent = monitor.spotify_get_user_info("token", "watched", True, 0)
    empty = monitor.spotify_get_user_info("token", "watched", True, 0)

    assert absent["sp_user_public_playlists_available"] is False
    assert empty["sp_user_public_playlists_available"] is True
    assert absent["sp_user_public_playlists_count"] == empty["sp_user_public_playlists_count"] == 0


# A glitch clears on a re-read, which is the only signal available to a one-shot command
def test_empty_playlists_are_confirmed_by_re_reading(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRIES", 2)
    getter = scripted_profile(monkeypatch, [profile_reply([]), profile_reply([PLAYLIST])])

    result = monitor.spotify_get_user_info_confirmed("token", "watched", True, 0)

    assert result["sp_user_public_playlists_count"] == 1
    assert getter.call_count == 2
    assert "was a glitch" in capsys.readouterr().out


# A profile that really has no playlists must not be re-read forever, and the last answer still stands
def test_persistently_empty_playlists_are_accepted(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRIES", 2)
    getter = scripted_profile(monkeypatch, [profile_reply([])] * 3)

    result = monitor.spotify_get_user_info_confirmed("token", "watched", True, 0)

    assert result["sp_user_public_playlists_count"] == 0
    assert getter.call_count == 3
    assert "treating the empty list as real" in capsys.readouterr().out


# Re-reading costs a request, so a response that already carries playlists must not trigger one
def test_a_populated_response_is_not_re_read(monkeypatch):
    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRIES", 2)
    getter = scripted_profile(monkeypatch, [profile_reply([PLAYLIST])])

    result = monitor.spotify_get_user_info_confirmed("token", "watched", True, 0)

    assert result["sp_user_public_playlists_count"] == 1
    assert getter.call_count == 1


# Callers that do not ask for playlists have nothing to confirm
def test_confirmation_is_skipped_when_playlists_were_not_requested(monkeypatch):
    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRIES", 2)
    getter = scripted_profile(monkeypatch, [profile_reply(None)])

    monitor.spotify_get_user_info_confirmed("token", "watched", False, 0)

    assert getter.call_count == 1


# Setting the retries to zero must disable the extra reads outright
def test_retries_can_be_disabled(monkeypatch):
    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRIES", 0)
    getter = scripted_profile(monkeypatch, [profile_reply([])])

    result = monitor.spotify_get_user_info_confirmed("token", "watched", True, 0)

    assert result["sp_user_public_playlists_count"] == 0
    assert getter.call_count == 1


# A failed re-read must not abort the command, since the first answer is still usable
def test_a_failing_re_read_falls_back_to_the_first_answer(monkeypatch):
    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRIES", 1)
    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRY_SLEEP", 0)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    reply = Mock(status_code=200)
    reply.json.return_value = profile_reply([])
    monkeypatch.setattr(monitor.SESSION, "get", Mock(side_effect=[reply, RuntimeError("503 Server Error")]))

    result = monitor.spotify_get_user_info_confirmed("token", "watched", True, 0, quiet=True)

    assert result["sp_user_public_playlists_count"] == 0


# Builds the playlist history file the monitoring startup reads
def seed_playlist_history(tmp_path, uris):
    monitor.FILE_SUFFIX = "watched-user"
    path = tmp_path / "spotify_profile_watched-user_playlists.json"
    path.write_text(json.dumps([len(uris), [{"uri": uri} for uri in uris]]), encoding="utf-8")
    return path


# Startup gets one read and no streak to fall back on, so an empty list must leave the saved history alone
def test_startup_keeps_the_saved_baseline_when_playlists_come_back_empty(monkeypatch, tmp_path):
    from test_monitoring_loop import error_alerts_for, profile_snapshot

    history = seed_playlist_history(tmp_path, [PLAYLIST["uri"]])
    before = history.read_text(encoding="utf-8")
    events = []
    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRIES", 0)
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "watched-user")

    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot()], 1, playlist_checks=True, collection_events=events)

    assert history.read_text(encoding="utf-8") == before
    assert not [event for event in events if event[5] == "Playlists"]


# A real removal still has to be reported, otherwise the guard would hide the change it exists to confirm
def test_startup_still_reports_a_real_playlist_change(monkeypatch, tmp_path):
    from test_monitoring_loop import error_alerts_for, profile_snapshot

    seed_playlist_history(tmp_path, [PLAYLIST["uri"], "spotify:playlist:bbbbbbbbbbbbbbbbbbbbbb"])
    events = []
    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRIES", 0)
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "watched-user")
    snapshot = profile_snapshot()
    snapshot.update(sp_user_public_playlists_count=1, sp_user_public_playlists_uris=[{"uri": PLAYLIST["uri"]}], sp_user_public_playlists_available=True)

    error_alerts_for(monkeypatch, tmp_path, [snapshot], 1, playlist_checks=True, collection_events=events)

    assert [event for event in events if event[5] == "Playlists"]


# Writing a first baseline from a broken read would record an emptied profile as the truth
def test_startup_writes_no_baseline_from_an_unusable_read(monkeypatch, tmp_path):
    from test_monitoring_loop import error_alerts_for, profile_snapshot

    monkeypatch.setattr(monitor, "PLAYLISTS_EMPTY_RETRIES", 0)
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "watched-user")
    snapshot = profile_snapshot()
    snapshot.update(sp_user_public_playlists_available=False)

    error_alerts_for(monkeypatch, tmp_path, [snapshot], 1, playlist_checks=True, collection_events=[])

    assert not (tmp_path / "spotify_profile_watched-user_playlists.json").exists()

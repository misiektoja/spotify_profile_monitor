import pytest

import spotify_profile_monitor as monitor
from test_monitoring_loop import error_alerts_for, profile_snapshot

A = "spotify:playlist:aaaaaaaaaaaaaaaaaaaaaa"
B = "spotify:playlist:bbbbbbbbbbbbbbbbbbbbbb"


# Builds a successful profile response with an independently reported playlist collection
def playlist_profile(*uris):
    result = profile_snapshot()
    result.update(sp_user_public_playlists_count=len(uris), sp_user_public_playlists_uris=[{"uri": uri} for uri in uris])
    return result


# Persistent metadata outages reach both channels once without changing playlist membership
def test_playlist_outage_alerts_without_poisoning_membership(monkeypatch, tmp_path, capsys):
    errors = error_alerts_for(monkeypatch, tmp_path, [playlist_profile(A)] * 12, 10, check_interval=300, playlist_checks=True, playlist_answers=[RuntimeError("503 Server Error")] * 20)
    assert len(errors) == 1
    assert errors[0]["email"] and errors[0]["webhook"]
    assert monitor.PLAYLISTS_BASELINE_CACHE["user:watched-user"]["uris"] == frozenset({A})
    output = capsys.readouterr().out
    assert output.count("* Error while processing playlists:") == 1
    assert "Monitoring healthy" not in output


# Failed playlist error deliveries retain their retry state across successful profile and follower polls
def test_playlist_delivery_failures_retry_with_backoff(monkeypatch, tmp_path):
    errors = error_alerts_for(monkeypatch, tmp_path, [playlist_profile(A)] * 12, 10, check_interval=300, playlist_checks=True, playlist_answers=[RuntimeError("503 Server Error")] * 20, delivery_results=[False] * 20)
    assert len(errors) == 4


# A successful nonempty response interrupts the disappearance streak even while its change awaits confirmation
def test_disappearance_counter_requires_consecutive_empty_responses(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "PLAYLISTS_DISAPPEARED_COUNTER", 3)
    monkeypatch.setattr(monitor, "PLAYLISTS_CHANGE_COUNTER", 3)
    events = []
    answers = [playlist_profile(A), playlist_profile(), playlist_profile(B), playlist_profile(), playlist_profile()]
    errors = error_alerts_for(monkeypatch, tmp_path, answers, len(answers), playlist_checks=True, collection_events=events)
    assert not errors
    assert not [event for event in events if event[5] == "Playlists" and event[3] == 0]
    assert monitor.PLAYLISTS_BASELINE_CACHE["user:watched-user"]["uris"] == frozenset({A})


# An empty response interrupts a pending nonempty membership change
def test_change_counter_does_not_span_an_empty_response(monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "PLAYLISTS_DISAPPEARED_COUNTER", 3)
    monkeypatch.setattr(monitor, "PLAYLISTS_CHANGE_COUNTER", 3)
    answers = [playlist_profile(A), playlist_profile(B), playlist_profile(), playlist_profile(B), playlist_profile(B)]
    error_alerts_for(monkeypatch, tmp_path, answers, len(answers), playlist_checks=True, collection_events=[])
    assert monitor.PLAYLISTS_BASELINE_CACHE["user:watched-user"]["uris"] == frozenset({A})
    assert monitor.PLAYLISTS_PENDING_CACHE["user:watched-user"]["streak"] == 2


@pytest.mark.parametrize("disappearance,change,observations,expected", [(3, 3, [(), (), ()], frozenset()), (5, 3, [(B,), (B,), (B,)], frozenset({B})), (5, 0, [(B,)], frozenset({B}))])
# Configured thresholds still accept real changes and zero disables only the nonempty-change protection
def test_playlist_confirmation_thresholds_remain_effective(monkeypatch, tmp_path, disappearance, change, observations, expected):
    monkeypatch.setattr(monitor, "PLAYLISTS_DISAPPEARED_COUNTER", disappearance)
    monkeypatch.setattr(monitor, "PLAYLISTS_CHANGE_COUNTER", change)
    answers = [playlist_profile(A), *[playlist_profile(*uris) for uris in observations]]
    errors = error_alerts_for(monkeypatch, tmp_path, answers, len(answers), playlist_checks=True, collection_events=[])
    assert not errors
    assert monitor.PLAYLISTS_BASELINE_CACHE["user:watched-user"]["uris"] == expected


# Changing the failed request does not restart the alert delay for one continuous outage
def test_follower_to_playlist_failure_keeps_the_original_outage_age(monkeypatch, tmp_path):
    healthy = {"sp_playlist_name": "Playlist", "sp_playlist_owner": "Owner", "sp_playlist_owner_uri": "spotify:user:owner", "sp_playlist_description": "", "sp_playlist_tracks": [], "sp_playlist_tracks_count": 0, "sp_playlist_tracks_count_before_filtering": 0, "sp_playlist_followers_count": 1}
    errors = error_alerts_for(monkeypatch, tmp_path, [playlist_profile(A)] * 4, 3, follower_answers=[RuntimeError("503 Server Error"), None], check_interval=300, playlist_checks=True, playlist_answers=[healthy, RuntimeError("503 Server Error")])
    assert len(errors) == 1
    assert errors[0]["email"] and errors[0]["webhook"]


# A complete successful playlist check allows a later outage to earn a new alert
def test_playlist_recovery_resets_alert_delivery(monkeypatch, tmp_path, capsys):
    healthy = {"sp_playlist_name": "Playlist", "sp_playlist_owner": "Owner", "sp_playlist_owner_uri": "spotify:user:owner", "sp_playlist_description": "", "sp_playlist_tracks": [], "sp_playlist_tracks_count": 0, "sp_playlist_tracks_count_before_filtering": 0, "sp_playlist_followers_count": 1}
    failure = RuntimeError("503 Server Error")
    errors = error_alerts_for(monkeypatch, tmp_path, [playlist_profile(A)] * 7, 6, check_interval=300, playlist_checks=True, playlist_answers=[healthy, failure, failure, healthy, failure, failure])
    assert len(errors) == 2
    assert "Monitoring recovered" in capsys.readouterr().out

"""Checks that one-shot playlist sweeps wait out a Spotify rate limit instead of skipping the playlist."""

import spotify_profile_monitor as monitor
from test_monitoring_loop import error_alerts_for, failure_alerts
from test_playlist_outage_integration import A, B, HEALTHY_PLAYLIST, playlist_profile

RATE_LIMITED = RuntimeError("429 Too Many Requests")
RETRY_NOTICE = f"* Spotify is rate limiting requests; retrying playlist {monitor.spotify_format_playlist_reference(A)} in 1 minute (retry 1/3)"


# Builds playlist details holding one track added by the given user
def playlist_added_by(user_id):
    track = {"added_at": "2026-07-14T17:30:18Z", "added_by": {"id": user_id}, "track": {"artists": [{"name": "Artist"}], "duration_ms": 120000, "name": "Track", "uri": "spotify:track:track-a"}}
    return {**HEALTHY_PLAYLIST, "sp_playlist_tracks": [track], "sp_playlist_tracks_count": 1, "sp_playlist_tracks_count_before_filtering": 1}


# Runs a sweep over playlists A and B with scripted Spotify reads and returns the sleeps, the profile lookups and the sweep result
def sweep(monkeypatch, playlist_answers, user_answers=(), errors=None, show_progress=False):
    sleeps = []
    lookups = []
    remaining_playlists = list(playlist_answers)
    remaining_users = list(user_answers)

    # Answers playlist reads in order and raises the scripted failures
    def playlist_info(*_arguments):
        answer = remaining_playlists.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    # Answers profile lookups in order and raises the scripted failures
    def user_info(_access_token, user_id, *_arguments):
        lookups.append(user_id)
        answer = remaining_users.pop(0) if remaining_users else {"sp_username": "Owner Name"}
        if isinstance(answer, BaseException):
            raise answer
        return answer

    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 1800)
    monkeypatch.setattr(monitor, "PLAYLIST_INFO_CACHE", {})
    monkeypatch.setattr(monitor, "spotify_get_playlist_info", playlist_info)
    monkeypatch.setattr(monitor, "spotify_get_user_info", user_info)
    monkeypatch.setattr(monitor.time, "sleep", sleeps.append)
    result = monitor.spotify_process_public_playlists("token", [{"uri": A}, {"uri": B}], True, show_progress=show_progress, errors=errors)
    return sleeps, lookups, result


# A rate limited read waits on the doubling backoff and is read again, so the playlist is not skipped
def test_a_rate_limited_playlist_read_waits_and_is_read_again(monkeypatch, capsys):
    sleeps, _, (playlists, failed) = sweep(monkeypatch, [RATE_LIMITED, RATE_LIMITED, HEALTHY_PLAYLIST, HEALTHY_PLAYLIST])

    assert sleeps == [60, 120]
    assert [playlist["uri"] for playlist in playlists] == [A, B]
    assert failed is False
    assert RETRY_NOTICE in capsys.readouterr().out


# The profile lookups that name collaborators hit the same limit and wait the same way
def test_a_rate_limited_collaborator_lookup_waits_too(monkeypatch):
    sleeps, lookups, (playlists, failed) = sweep(monkeypatch, [playlist_added_by("owner")] * 2, user_answers=[RATE_LIMITED])

    assert sleeps == [60]
    assert lookups == ["owner", "owner"]
    assert [playlist["collaborators_count"] for playlist in playlists] == [1, 1]
    assert failed is False


# One owner usually adds the tracks to most of their playlists, so a sweep looks each adder up only once
def test_each_adder_is_looked_up_once_per_sweep(monkeypatch):
    _, lookups, _ = sweep(monkeypatch, [playlist_added_by("owner")] * 2)

    assert lookups == ["owner"]


# A limit that outlasts every wait is reported, and the rest of the sweep does not wait on it again
def test_a_limit_that_outlasts_every_wait_is_not_waited_on_again(monkeypatch, capsys):
    sleeps, _, (playlists, failed) = sweep(monkeypatch, [RATE_LIMITED] * 5)

    assert sleeps == [60, 120, 240]
    assert playlists == []
    assert failed is True
    assert "could not be processed and will be retried" in capsys.readouterr().out


# The monitoring loop retries a rate limited check as a whole, so its sweep never waits inside
def test_the_monitoring_sweep_does_not_wait(monkeypatch):
    errors = []
    sleeps, _, (_, failed) = sweep(monkeypatch, [RATE_LIMITED, HEALTHY_PLAYLIST], errors=errors)

    assert sleeps == []
    assert errors == [RATE_LIMITED]
    assert failed is True


# Notices and errors used to continue the progress bar's line, so they now start on a line of their own
def test_messages_start_below_the_progress_bar(monkeypatch, capsys):
    # The bar draws on the saved terminal stream while a log file is active, so the test keeps it on captured output
    monkeypatch.setattr(monitor, "stdout_bck", None)
    sweep(monkeypatch, [HEALTHY_PLAYLIST, RATE_LIMITED, HEALTHY_PLAYLIST], show_progress=True)

    output = capsys.readouterr().out
    assert "(1/2) - Playlist\n* Spotify is rate limiting requests; retrying playlist" in output
    assert "Playlist*" not in output


# The startup snapshot waits out a rate limit before monitoring begins instead of starting without the playlist
def test_startup_waits_out_a_rate_limit(monkeypatch, tmp_path):
    sleeps = []
    alerts = error_alerts_for(monkeypatch, tmp_path, [playlist_profile(A)] * 4, 3, check_interval=10800, playlist_checks=True, playlist_answers=[RATE_LIMITED, RATE_LIMITED, HEALTHY_PLAYLIST, HEALTHY_PLAYLIST], sleep_log=sleeps)

    assert sleeps == [60, 120, 10800]
    assert failure_alerts(alerts) == []

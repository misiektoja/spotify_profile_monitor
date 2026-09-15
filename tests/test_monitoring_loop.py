"""Drives the profile monitoring loop with scripted Spotify answers, so error alert timing can be observed."""

import pytest

import spotify_profile_monitor as monitor

USER = "watched-user"


class LoopStopped(BaseException):
    """Leaves the endless monitoring loop once the scripted checks have run."""


# Builds the profile snapshot the monitored user answers with when a check succeeds
def profile_snapshot():
    return {"sp_username": "Watched Person", "sp_user_image_url": "", "sp_user_followers_count": 0, "sp_user_followers_count_available": True, "sp_user_followings_count": 0, "sp_user_public_playlists_count": 0, "sp_user_public_playlists_uris": []}


# Runs the loop until stop_after sleeps have passed and returns the error alerts it handed to the channels
def error_alerts_for(monkeypatch, tmp_path, answers, stop_after):
    calls = []
    sleeps = []
    now = [1_800_000_000.0]
    remaining = list(answers)

    def stopping_sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds
        if len(sleeps) >= stop_after:
            raise LoopStopped

    def scripted_user_info(*_arguments, **_keywords):
        if not remaining:
            return profile_snapshot()
        answer = remaining.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def record_delivery(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None, **_keywords):
        calls.append({"type": notification_type, "subject": subject, "body": body, "email": email_enabled, "webhook": webhook_enabled})
        return True, True

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor.time, "sleep", stopping_sleep)
    monkeypatch.setattr(monitor.time, "time", lambda: now[0])
    # The POSIX watchdog alarm is real wall-clock time and would fire into a test that runs on a fake clock
    monkeypatch.setattr(monitor, "_start_timeout_alarm", lambda timeout: None)
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "cookie-value")
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 1800)
    monkeypatch.setattr(monitor, "SPOTIFY_ERROR_INTERVAL", 300)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 100 * 1800)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "DETECT_CHANGES_IN_PLAYLISTS", False)
    monkeypatch.setattr(monitor, "DETECT_CHANGED_PROFILE_PIC", False)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "access-token")
    monkeypatch.setattr(monitor, "spotify_get_user_info", scripted_user_info)
    monkeypatch.setattr(monitor, "spotify_get_user_followers", lambda token, uri: {"sp_user_followers": []})
    monkeypatch.setattr(monitor, "spotify_get_user_followings", lambda token, uri: {"sp_user_followings": []})
    monkeypatch.setattr(monitor, "send_notification_channels", record_delivery)
    with pytest.raises(LoopStopped):
        monitor.spotify_profile_monitor_uri(USER, "", [])
    return [call for call in calls if call["type"] == "error"]


# A failure the loop can retry away is alerted only once the outage has lasted the alert delay, which the second
# failing check of a poller this slow already is, while the first failing check reaches nobody
@pytest.mark.parametrize("stop_after,expected", [(2, []), (3, [(True, True)])])
def test_a_retryable_failure_is_alerted_once_the_outage_has_lasted(monkeypatch, tmp_path, stop_after, expected):
    # The startup snapshot succeeds, then every check times out
    outage = [profile_snapshot(), RuntimeError("The read operation timed out"), RuntimeError("The read operation timed out")]
    errors = error_alerts_for(monkeypatch, tmp_path, outage, stop_after)

    assert [(call["email"], call["webhook"]) for call in errors] == expected


# A failure nothing here can retry away is alerted on the first check, since waiting would change nothing
def test_a_failure_that_cannot_clear_itself_is_alerted_at_once(monkeypatch, tmp_path):
    errors = error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), RuntimeError("401 Unauthorized")], 2)

    assert len(errors) == 1
    assert errors[0]["subject"].startswith("spotify_profile_monitor: ") and errors[0]["subject"].endswith(f" (uri: {USER})")
    assert "To fix:" in errors[0]["body"]

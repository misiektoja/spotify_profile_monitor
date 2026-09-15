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
        calls.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html, "email": email_enabled, "webhook": webhook_enabled})
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


# The guide link sits under the fix in the HTML body too, since HTML renders the newline the fix carries as a space
def test_the_guide_link_keeps_its_own_line_in_the_html_body(monkeypatch, tmp_path):
    errors = error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), RuntimeError("401 Unauthorized")], 2)

    parts = errors[0]["body_html"].split("<br>")
    fix_index = next(index for index, part in enumerate(parts) if part.startswith("To fix: "))
    assert parts[fix_index + 1].startswith("Guide: https://")
    assert "\n" not in parts[fix_index]


# Verifies an internet outage that classifies as a timeout on one check and as unreachable on the next is one
# outage, so it is reported once on screen and alerted once
def test_an_internet_outage_that_flaps_is_one_outage(monkeypatch, tmp_path, capsys):
    flapping = [RuntimeError("The read operation timed out"), monitor.req.exceptions.ConnectionError("connection refused")] * 6
    errors = error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), *flapping], 12)

    output = capsys.readouterr().out
    assert output.count("* Error:") == 1
    assert output.count("To fix: ") == 1
    assert "Monitoring failure changed" not in output
    assert len(errors) == 1


# Verifies a reported outage that starts failing differently is still one outage, so the change is one line
# rather than a second report
def test_a_second_failure_category_is_noted_in_one_line(monkeypatch, tmp_path, capsys):
    outage = [RuntimeError("503 Server Error")] * 3 + [RuntimeError("The read operation timed out")] * 2
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), *outage], 6)

    lines = capsys.readouterr().out.splitlines()
    reports = [line for line in lines if line.startswith("* Error:")]
    changes = [number for number, line in enumerate(lines) if line.startswith(f"* Monitoring failure changed for {USER}. ")]
    assert len(reports) == 1 and "temporarily unavailable" in reports[0]
    assert len(changes) == 1 and lines[changes[0]].endswith("The Spotify request timed out")
    assert lines[changes[0] + 1].startswith("Timestamp:")
    assert "\n".join(lines).count("To fix: ") == 1


# Verifies a lasting outage is reported once and then carried by the hourly reminder with a count of its checks
def test_a_lasting_outage_is_carried_by_the_hourly_reminder(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 900)
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), *[RuntimeError("The read operation timed out")] * 10], 11)

    output = capsys.readouterr().out
    assert output.count("* Error:") == 1
    assert output.count("To fix: ") == 1
    # Five minute error checks put every third one at the reminder interval
    assert output.count(f"* Monitoring degraded for {USER}. The Spotify request timed out since ") == 3
    assert ", 4 failed checks\n" in output and ", 10 failed checks\n" in output
    assert output.count("Liveness check, timestamp:") == 3

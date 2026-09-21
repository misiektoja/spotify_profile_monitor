"""Drives the profile monitoring loop with scripted Spotify answers, so error alert timing can be observed."""

import inspect

import pytest

import spotify_profile_monitor as monitor

USER = "watched-user"
# The alert label the loop builds, since a failure names the profile by display name and URI id
ALERT_TARGET = "Watched Person, watched-user"


class LoopStopped(BaseException):
    """Leaves the endless monitoring loop once the scripted checks have run."""


# Builds the profile snapshot the monitored user answers with when a check succeeds
def profile_snapshot():
    return {"sp_username": "Watched Person", "sp_user_image_url": "", "sp_user_followers_count": 0, "sp_user_followers_count_available": True, "sp_user_followings_count": 0, "sp_user_public_playlists_count": 0, "sp_user_public_playlists_uris": []}


# Runs the loop until stop_after sleeps have passed and returns the error alerts it handed to the channels
def error_alerts_for(monkeypatch, tmp_path, answers, stop_after, follower_answers=(), check_interval=1800, liveness_seconds=None, delivery_results=(), playlist_checks=False, playlist_answers=(), collection_events=None, initial_followers=(), following_answers=(), sleep_log=None, alert_log=None):
    calls = alert_log if alert_log is not None else []
    sleeps = sleep_log if sleep_log is not None else []
    now = [1_800_000_000.0]
    remaining = list(answers)
    remaining_followers = list(follower_answers)
    remaining_followings = list(following_answers)
    follower_calls = []
    deliveries = list(delivery_results)
    remaining_playlists = list(playlist_answers)

    # Returns real processor inputs while allowing individual metadata requests to fail
    def scripted_playlist_info(*_arguments, **_keywords):
        if remaining_playlists:
            answer = remaining_playlists.pop(0)
            if isinstance(answer, BaseException):
                raise answer
            return answer
        return {"sp_playlist_name": "Playlist", "sp_playlist_owner": "Owner", "sp_playlist_owner_uri": "spotify:user:owner", "sp_playlist_description": "", "sp_playlist_tracks": [], "sp_playlist_tracks_count": 0, "sp_playlist_tracks_count_before_filtering": 0, "sp_playlist_followers_count": 1}

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

    # The follower poll has its own outage reporter, so the harness can fail it while the profile poll succeeds.
    # The startup snapshot reads the same list and a failure there ends the run, so only loop checks fail
    def scripted_followers(*_arguments, **_keywords):
        follower_calls.append(1)
        if remaining_followers and len(follower_calls) > 1:
            answer = remaining_followers.pop(0)
            if isinstance(answer, BaseException):
                raise answer
            if isinstance(answer, dict):
                return answer
        return {"sp_user_followers": (list(initial_followers) if initial_followers is not None else None) if len(follower_calls) == 1 else []}

    # Returns scripted following snapshots including unavailable data
    def scripted_followings(*_arguments, **_keywords):
        return remaining_followings.pop(0) if remaining_followings else {"sp_user_followings": []}

    # Prints the same delivery lines the real dispatcher prints, so a report that leaves one outside itself is visible
    def record_delivery(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None, **keywords):
        calls.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html, "webhook_body": keywords.get("webhook_body", ""), "webhook_body_html": keywords.get("webhook_body_html", ""), "email": email_enabled, "webhook": webhook_enabled})
        if email_enabled:
            print(f"Sending email notification to {monitor.RECEIVER_EMAIL}")
        if webhook_enabled:
            print("Sending webhook notification via Discord")
        delivered = deliveries.pop(0) if deliveries else True
        return bool(email_enabled) and delivered, bool(webhook_enabled) and delivered

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor.time, "sleep", stopping_sleep)
    monkeypatch.setattr(monitor.time, "time", lambda: now[0])
    # The POSIX watchdog alarm is real wall-clock time and would fire into a test that runs on a fake clock
    monkeypatch.setattr(monitor, "_start_timeout_alarm", lambda timeout: None)
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "cookie-value")
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", check_interval)
    monkeypatch.setattr(monitor, "SPOTIFY_ERROR_INTERVAL", 300)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", liveness_seconds if liveness_seconds is not None else 100 * check_interval)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "watcher@example.invalid")
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "DETECT_CHANGES_IN_PLAYLISTS", playlist_checks)
    monkeypatch.setattr(monitor, "PLAYLIST_INFO_CACHE", {})
    monkeypatch.setattr(monitor, "PLAYLISTS_BASELINE_CACHE", {})
    monkeypatch.setattr(monitor, "PLAYLISTS_PENDING_CACHE", {})
    monkeypatch.setattr(monitor, "spotify_get_playlist_info", scripted_playlist_info)
    if collection_events is not None:
        monkeypatch.setattr(monitor, "spotify_print_changed_followers_followings_playlists", lambda *args, **kwargs: collection_events.append(args))
    monkeypatch.setattr(monitor, "DETECT_CHANGED_PROFILE_PIC", False)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "access-token")
    monkeypatch.setattr(monitor, "spotify_get_user_info", scripted_user_info)
    monkeypatch.setattr(monitor, "spotify_get_user_followers", scripted_followers)
    monkeypatch.setattr(monitor, "spotify_get_user_followings", scripted_followings)
    monkeypatch.setattr(monitor, "send_notification_channels", record_delivery)
    with pytest.raises(LoopStopped):
        monitor.spotify_profile_monitor_uri(USER, "", [])
    return [call for call in calls if call["type"] == "error"]


# Returns the alerts that report a failing check, which share the error event with the recovery alerts that close them
def failure_alerts(alerts):
    return [alert for alert in alerts if " error: " in alert["subject"]]


# Returns the alerts that report a failure cleared
def recovery_alerts(alerts):
    return [alert for alert in alerts if " recovered: " in alert["subject"]]


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
    assert not errors[0]["subject"].startswith("spotify_profile_monitor: ")
    assert errors[0]["subject"] == f"Spotify Profile Monitor error: Spotify rejected the sp_dc cookie (user: {ALERT_TARGET})"
    assert "To fix:" in errors[0]["body"]


# The guide link sits under the fix in the HTML body too, since HTML renders the newline the fix carries as a space
def test_the_guide_link_keeps_its_own_line_in_the_html_body(monkeypatch, tmp_path):
    errors = error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), RuntimeError("401 Unauthorized")], 2)

    parts = errors[0]["body_html"].split("<br>")
    fix_index = next(index for index, part in enumerate(parts) if part.startswith("To fix: "))
    assert parts[fix_index + 1].startswith('Guide: <a href="https://')
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
    changes = [number for number, line in enumerate(lines) if line.startswith(f"* Monitoring failure changed for {ALERT_TARGET}. ")]
    assert len(reports) == 1 and "temporarily unavailable" in reports[0]
    assert len(changes) == 1 and lines[changes[0]].endswith("Spotify did not answer in time")
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
    assert output.count(f"* Monitoring degraded for {ALERT_TARGET}. Spotify did not answer in time since ") == 3
    assert ", 4 failed checks\n" in output and ", 10 failed checks\n" in output
    assert output.count("Liveness check, timestamp:") == 3


# Verifies the follower poll carries its own outage, so a profile check that keeps succeeding is not reported failed
def test_a_follower_failure_is_reported_on_its_own_without_the_profile_poll(monkeypatch, tmp_path, capsys):
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot()], 3, follower_answers=[RuntimeError("The read operation timed out")] * 4)

    lines = capsys.readouterr().out.splitlines()
    reports = [line for line in lines if line.startswith("* Error while getting followers and followings: ")]
    assert len(reports) == 1 and reports[0].endswith("(retrying in 5 minutes)")
    assert not [line for line in lines if line.startswith("* Error:")]


# Verifies each poll announces its own recovery on screen, not only ends the outage it was tracking
@pytest.mark.parametrize("answers,follower_answers", [([profile_snapshot(), RuntimeError("503 Server Error")], ()), ([profile_snapshot()], [RuntimeError("503 Server Error")])])
def test_a_check_that_succeeds_after_a_failure_announces_the_recovery(monkeypatch, tmp_path, capsys, answers, follower_answers):
    error_alerts_for(monkeypatch, tmp_path, answers, 4, follower_answers=follower_answers)

    output = capsys.readouterr().out
    assert output.count(f"* Monitoring recovered for {ALERT_TARGET} after ") == 1


# Verifies a run that never fails announces no recovery, so the line marks a real return rather than every check
def test_a_run_that_never_fails_announces_no_recovery(monkeypatch, tmp_path, capsys):
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot()], 4)

    output = capsys.readouterr().out
    assert "* Monitoring recovered" not in output
    assert "* Error" not in output


# Verifies the healthy banner reaches a plain run and follows elapsed time rather than a count of checks, so the
# same four checks report it once at a five-minute interval and three times at a fifteen-minute one
@pytest.mark.parametrize("check_interval,expected", [(300, 1), (900, 3)])
def test_the_healthy_banner_reaches_a_plain_run_on_its_own_clock(monkeypatch, tmp_path, capsys, check_interval, expected):
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot()], 5, check_interval=check_interval, liveness_seconds=900)

    lines = capsys.readouterr().out.splitlines()
    banners = [number for number, line in enumerate(lines) if line == f"* Monitoring healthy for {ALERT_TARGET}. No profile or playlist change since the last check"]
    assert len(banners) == expected
    assert all(lines[number + 1].startswith("Liveness check, timestamp:") for number in banners)


# Verifies a channel that could not deliver keeps owing the alert, so the next failing check past its hold tries
# again instead of the loop recording a failed send as done
def test_a_channel_that_could_not_deliver_is_tried_again(monkeypatch, tmp_path, capsys):
    outage = [profile_snapshot(), *[RuntimeError("401 Unauthorized")] * 5]
    errors = error_alerts_for(monkeypatch, tmp_path, outage, 5, check_interval=1800, delivery_results=[False])

    assert len(errors) == 2
    assert "The email alert is on hold for 5 minutes after 1 attempt, then tried again" in capsys.readouterr().out


# Verifies a channel that delivered is not asked again while the same outage lasts
def test_a_delivered_alert_is_not_repeated_during_one_outage(monkeypatch, tmp_path):
    outage = [profile_snapshot(), *[RuntimeError("401 Unauthorized")] * 5]
    errors = error_alerts_for(monkeypatch, tmp_path, outage, 5)

    assert len(errors) == 1


# Verifies a halted request is a failing check like any other, so it joins the outage clock and earns the alert
# rather than retrying silently forever. It retries every ALARM_RETRY seconds, so the alert delay takes 31 of them
def test_a_watchdog_timeout_is_reported_and_alerted(monkeypatch, tmp_path, capsys):
    halted = [profile_snapshot(), *[monitor.TimeoutException("Spotify timeout") for _ in range(40)]]
    errors = error_alerts_for(monkeypatch, tmp_path, halted, 32)

    output = capsys.readouterr().out
    assert output.count("* Error:") == 1
    assert len(errors) == 1
    assert errors[0]["subject"] == f"Spotify Profile Monitor error: Spotify did not answer in time (user: {ALERT_TARGET})"


# Verifies a run that halts and then answers again reports the recovery, which needs the timeout to have opened an outage
def test_a_watchdog_timeout_that_clears_announces_the_recovery(monkeypatch, tmp_path, capsys):
    answers = [profile_snapshot(), monitor.TimeoutException("Spotify timeout"), monitor.TimeoutException("Spotify timeout"), profile_snapshot()]
    error_alerts_for(monkeypatch, tmp_path, answers, 5)

    assert capsys.readouterr().out.count(f"* Monitoring recovered for {ALERT_TARGET} after ") == 1


# Verifies a follower poll that keeps failing alerts too, since the profile poll answering does not make the check complete
def test_a_lasting_follower_failure_is_alerted(monkeypatch, tmp_path):
    errors = error_alerts_for(monkeypatch, tmp_path, [profile_snapshot()], 4, follower_answers=[RuntimeError("401 Unauthorized")] * 5)

    assert len(errors) == 1


# Verifies a check that reported a change does not then claim nothing changed, and that the clock restarts from
# what was printed rather than from the last banner
def test_a_check_that_reported_a_change_does_not_claim_it_was_quiet(monkeypatch, tmp_path, capsys):
    renamed = dict(profile_snapshot(), sp_username="Renamed Person")
    # The first check is quiet and the second renames, so the rename lands on exactly the check whose clock is due
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), profile_snapshot(), renamed], 3, check_interval=900, liveness_seconds=900)

    output = capsys.readouterr().out
    assert "has changed username to 'Renamed Person'" in output
    assert f"* Monitoring healthy for {ALERT_TARGET}." not in output


# Returns every delivery line that no timestamp closes before the next separator, which would leave it dangling
def unclosed_delivery_lines(output):
    lines = output.splitlines()
    dangling = []
    for number, line in enumerate(lines):
        if not line.startswith("Sending "):
            continue
        rest = lines[number + 1:]
        separator = next((index for index, later in enumerate(rest) if later.startswith("─")), len(rest))
        if not any(later.startswith(("Timestamp:", "Liveness check, timestamp:")) for later in rest[:separator]):
            dangling.append(line)
    return dangling


# Verifies the alert a failing check sends is part of that check's report rather than a line after the separator,
# so the console still says when the alert went out
def test_an_alert_stays_inside_the_report_of_the_check_that_sent_it(monkeypatch, tmp_path, capsys):
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), RuntimeError("401 Unauthorized")], 2)

    output = capsys.readouterr().out
    assert "Sending email notification to " in output
    assert unclosed_delivery_lines(output) == []


# Verifies the hourly reminder waits for the alert it carries before closing, since both land on the same check
# when the alert delay and the reminder interval come due together
def test_the_degraded_reminder_closes_after_the_alert_it_carries(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 900)
    monkeypatch.setattr(monitor, "ERROR_ALERT_AFTER_SECONDS", 900)
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), *[RuntimeError("503 Server Error")] * 6], 5)

    lines = capsys.readouterr().out.splitlines()
    reminder = next(number for number, line in enumerate(lines) if line.startswith(f"* Monitoring degraded for {ALERT_TARGET}."))
    assert lines[reminder + 1].startswith("Sending email notification to ")
    assert lines[reminder + 3].startswith("Liveness check, timestamp:")
    assert unclosed_delivery_lines("\n".join(lines)) == []


# Verifies a failure alert names the failure, the fix, the streak and the next retry, and that a recovery alert
# follows on the channels that received it once the failure clears
def test_a_recovery_alert_closes_the_failure_alert(monkeypatch, tmp_path, capsys):
    answers = [profile_snapshot(), *[RuntimeError("503 Server Error")] * 2, profile_snapshot()]
    alerts = error_alerts_for(monkeypatch, tmp_path, answers, 5, check_interval=300)
    failures, recoveries = failure_alerts(alerts), recovery_alerts(alerts)

    assert len(failures) == 1 and len(recoveries) == 1
    assert failures[0]["subject"] == f"Spotify Profile Monitor error: Spotify is temporarily unavailable (user: {ALERT_TARGET})"
    assert failures[0]["body"].startswith("Spotify is temporarily unavailable\n\nTo fix: Usually nothing to do, ")
    assert "\nFailed checks in a row: 2\nFailing since: " in failures[0]["body"]
    assert "\nNext retry in: 5 minutes\n" in failures[0]["body"]
    assert recoveries[0]["subject"] == f"Spotify Profile Monitor recovered: monitoring {ALERT_TARGET} resumed after 10 minutes"
    assert recoveries[0]["body"].startswith(f"Monitoring recovered for {ALERT_TARGET} after 10 minutes.\n\nThe failure was: Spotify is temporarily unavailable")
    assert (recoveries[0]["email"], recoveries[0]["webhook"]) == (True, True)
    assert unclosed_delivery_lines(capsys.readouterr().out) == []


# Verifies only the email body carries a timestamp, since a chat message already shows when it arrived
def test_the_webhook_body_leaves_the_timestamp_to_the_email(monkeypatch, tmp_path):
    answers = [profile_snapshot(), *[RuntimeError("503 Server Error")] * 2, profile_snapshot()]
    alerts = error_alerts_for(monkeypatch, tmp_path, answers, 5, check_interval=300)

    for alert in alerts:
        assert "\n\nTimestamp: " in alert["body"]
        assert "Timestamp: " not in alert["webhook_body"]
        assert alert["body"].startswith(alert["webhook_body"])


# Verifies a failure that cleared before any channel was alerted ends without a recovery alert, since nobody was told
def test_a_failure_nobody_was_alerted_about_ends_without_a_recovery_alert(monkeypatch, tmp_path, capsys):
    answers = [profile_snapshot(), RuntimeError("503 Server Error"), profile_snapshot()]
    alerts = error_alerts_for(monkeypatch, tmp_path, answers, 4, check_interval=300)

    assert alerts == []
    assert capsys.readouterr().out.count(f"* Monitoring recovered for {ALERT_TARGET} after ") == 1


# Verifies a rate limited profile poll comes back on its own short backoff rather than on the error interval,
# since the limit clears on a timer of Spotify's own
def test_a_rate_limited_profile_poll_retries_on_the_backoff(monkeypatch, tmp_path):
    sleeps = []
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), *[RuntimeError("429 Too Many Requests")] * 6], 5, check_interval=10800, sleep_log=sleeps)

    assert sleeps == [10800, 60, 120, 240, 480]


# Verifies any other failing profile poll keeps the configured error interval
def test_another_failing_profile_poll_keeps_the_error_interval(monkeypatch, tmp_path):
    sleeps = []
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), *[RuntimeError("503 Server Error")] * 6], 4, check_interval=10800, sleep_log=sleeps)

    assert sleeps == [10800, 300, 300, 300]


# Verifies a change names the window the run actually observed, since a failing check no longer costs a full poll
# interval and the configured one would overstate how long the tool had been watching
def test_a_change_names_the_window_the_run_observed(monkeypatch, tmp_path, capsys):
    renamed = dict(profile_snapshot(), sp_username="Renamed Person")
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot(), RuntimeError("503 Server Error"), renamed], 3, check_interval=10800)

    lines = capsys.readouterr().out.splitlines()
    window = next(line for line in lines if line.startswith("Check interval:") and " - " in line)
    assert window.split("\t")[-1].startswith("3 hours, 5 minutes ("), window


# Verifies the window helpers measure from the previous check rather than from the configured interval
def test_the_window_helpers_measure_from_the_previous_check(monkeypatch):
    monkeypatch.setattr(monitor.time, "time", lambda: 1_000_000.0)
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 10800)
    monkeypatch.setattr(monitor, "LAST_CHECK_TS", 1_000_000 - 60)

    assert monitor.observed_window() == (60, 1_000_000)
    assert monitor.check_window_text().startswith("1 minute (")
    assert monitor.check_window_html().startswith("<b>1 minute</b> (")


# Verifies the configured interval is all a run can report before it has a previous check to measure from
def test_the_window_falls_back_to_the_configured_interval(monkeypatch):
    monkeypatch.setattr(monitor.time, "time", lambda: 1_000_000.0)
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 10800)
    monkeypatch.setattr(monitor, "LAST_CHECK_TS", 0)

    assert monitor.observed_window() == (10800, 1_000_000)


# Verifies no report still builds its window from the configured interval, which a shortened retry makes wrong
def test_no_report_builds_its_window_from_the_configured_interval():
    source = inspect.getsource(monitor)

    assert "int(time.time()) - SPOTIFY_CHECK_INTERVAL" not in source
    assert source.count("check_window_text()") + source.count("check_window_html()") >= 50

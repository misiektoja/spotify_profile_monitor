"""Checks that a follower who changes their display name is reported as a rename, not as a departure and an arrival."""

import csv
import json

import spotify_profile_monitor as monitor
from test_monitoring_loop import USER, error_alerts_for, profile_snapshot

JOHNSON_OLD = {"name": "Miss Johnson", "uri": "spotify:user:johnson"}
JOHNSON_NEW = {"name": "Johnson", "uri": "spotify:user:johnson"}
ANIA = {"name": "sweet_ania", "uri": "spotify:user:ania"}
NEWCOMER = {"name": "newcomer", "uri": "spotify:user:newcomer"}
JOHNSON_URL = monitor.spotify_convert_uri_to_url(JOHNSON_NEW["uri"])
RENAME_ROW = f"- Miss Johnson -> Johnson [ {JOHNSON_URL} ]"


# Runs the real follower report and returns its console output, the delivered notification and the paths it wrote
def report_followers(monkeypatch, capsys, tmp_path, current, previous, count, old_count, csv_name=""):
    delivered = {}
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "FOLLOWERS_FOLLOWINGS_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "webhook_event_enabled", lambda notification_type: False)
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *arguments, **keywords: delivered.update(subject=arguments[1], body=arguments[2], body_html=arguments[3]))
    history = tmp_path / "followers.json"
    monitor.spotify_print_changed_followers_followings_playlists(USER, current, previous, count, old_count, "Followers", "for", "Added followers", "Added Follower", "Removed followers", "Removed Follower", str(history), csv_name, True, False)
    return capsys.readouterr().out, delivered, history


# Reads back the events a report wrote to its CSV file
def csv_events(path):
    with open(path, newline="", encoding="utf-8") as source:
        return [(row[1], row[2], row[3], row[4]) for row in csv.reader(source)]


# The user's own case: one follower left and another only changed their name, so only the departure is a removal
def test_a_renamed_follower_is_not_reported_as_a_departure_and_an_arrival(monkeypatch, capsys, tmp_path):
    output, delivered, _ = report_followers(monkeypatch, capsys, tmp_path, [JOHNSON_NEW], [JOHNSON_OLD, ANIA], 1, 2)

    assert "Added followers:" not in output
    assert "Removed followers:" in output and "- sweet_ania [" in output
    assert "Renamed followers:" in output
    assert RENAME_ROW in output
    assert "Added followers" not in delivered["body"]
    assert RENAME_ROW in delivered["body"]
    assert f"- Miss Johnson -&gt; <a href=\"{JOHNSON_URL}\">Johnson</a>" in delivered["body_html"]


# A name change on its own leaves the total untouched, so the report says so instead of claiming a change of zero
def test_a_name_only_change_keeps_the_total_in_the_headline(monkeypatch, capsys, tmp_path):
    output, delivered, _ = report_followers(monkeypatch, capsys, tmp_path, [JOHNSON_NEW, ANIA], [JOHNSON_OLD, ANIA], 2, 2)

    assert f"* Followers changed for user {USER} while the total remained 2" in output
    assert "number changed" not in output
    assert delivered["subject"] == f"Spotify user {USER} followers have changed! (total remains 2)"
    assert "while the total remained <b>2</b>" in delivered["body_html"]


# One follower leaving while another arrives keeps the total, and used to be reported nowhere
def test_a_swap_that_keeps_the_total_is_still_reported(monkeypatch, capsys, tmp_path):
    output, _, _ = report_followers(monkeypatch, capsys, tmp_path, [NEWCOMER], [ANIA], 1, 1)

    assert "while the total remained 1" in output
    assert "- newcomer [" in output and "- sweet_ania [" in output
    assert "Renamed followers:" not in output


# A rename is one CSV event carrying both names, rather than an unrelated removal and addition pair
def test_a_rename_is_recorded_as_one_csv_event(monkeypatch, capsys, tmp_path):
    csv_name = str(tmp_path / "events.csv")
    report_followers(monkeypatch, capsys, tmp_path, [JOHNSON_NEW, ANIA], [JOHNSON_OLD, ANIA], 2, 2, csv_name=csv_name)

    assert ("Renamed Follower", USER, "Miss Johnson", "Johnson") in csv_events(csv_name)
    assert not [event for event in csv_events(csv_name) if event[0] in {"Added Follower", "Removed Follower"}]


# The new name has to reach the history file, otherwise a restart replays the rename against a stale baseline
def test_a_rename_updates_the_saved_baseline(monkeypatch, capsys, tmp_path):
    _, _, history = report_followers(monkeypatch, capsys, tmp_path, [JOHNSON_NEW, ANIA], [JOHNSON_OLD, ANIA], 2, 2)

    assert json.loads(history.read_text(encoding="utf-8")) == [2, [JOHNSON_NEW, ANIA]]


# A followings report names its own section and CSV event
def test_a_renamed_following_uses_its_own_labels(monkeypatch, capsys, tmp_path):
    csv_name = str(tmp_path / "events.csv")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *arguments, **keywords: None)
    monitor.spotify_print_changed_followers_followings_playlists(USER, [JOHNSON_NEW], [JOHNSON_OLD], 1, 1, "Followings", "by", "Added followings", "Added Following", "Removed followings", "Removed Following", str(tmp_path / "followings.json"), csv_name, False, False)

    assert "Renamed followings:" in capsys.readouterr().out
    assert ("Renamed Following", USER, "Miss Johnson", "Johnson") in csv_events(csv_name)


# Pairing happens on the URI, and entries without one keep the whole-entry comparison they had before
def test_profile_changes_are_paired_on_the_uri():
    assert monitor.split_profile_changes([JOHNSON_NEW], [JOHNSON_OLD, ANIA]) == ([ANIA], [], [{**JOHNSON_NEW, "old_name": "Miss Johnson"}])
    assert monitor.split_profile_changes([JOHNSON_NEW], [JOHNSON_NEW]) == ([], [], [])

    nameless = {"uri": "spotify:user:johnson"}
    assert monitor.split_profile_changes([JOHNSON_NEW], [nameless]) == ([], [], [{**JOHNSON_NEW, "old_name": "Unknown"}])

    unkeyed_old = {"name": "No URI"}
    unkeyed_new = {"name": "Still no URI"}
    assert monitor.split_profile_changes([unkeyed_new], [unkeyed_old]) == ([unkeyed_old], [unkeyed_new], [])

    assert monitor.split_profile_changes([nameless], [JOHNSON_OLD]) == ([], [], [])


# An empty list beside a positive count means the list was unavailable, not that every follower left at once
def test_an_unavailable_list_is_not_a_membership_change():
    assert monitor.follow_membership_changed([], [JOHNSON_OLD], 1) is False
    assert monitor.follow_membership_changed([JOHNSON_OLD], [], 1) is False
    assert monitor.follow_membership_changed([], [], 0) is False
    assert monitor.follow_membership_changed([JOHNSON_NEW], [JOHNSON_OLD], 1) is True


# The arrow between the two names is not part of either name, so it keeps the plain colour of the row
def test_a_rename_row_colours_both_names_and_leaves_the_arrow_plain(monkeypatch):
    styles = {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", styles)
    line = RENAME_ROW

    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert f"{styles['username']}Miss Johnson{monitor.ANSI_RESET} -> {styles['username']}Johnson{monitor.ANSI_RESET}" in result


# The monitoring loop used to compare lists only after the count moved, so a rename waited for an unrelated change
def test_the_loop_reports_a_rename_while_the_count_holds(monkeypatch, tmp_path, capsys):
    error_alerts_for(monkeypatch, tmp_path, [profile_snapshot()], 2, follower_answers=[{"sp_user_followers": [JOHNSON_NEW, ANIA]}], initial_followers=[JOHNSON_OLD, ANIA])

    output = capsys.readouterr().out
    assert "while the total remained 2" in output
    assert RENAME_ROW in output

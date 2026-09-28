"""Checks that a follower who changes their display name is reported as a rename, not as a departure and an arrival."""

import csv
import json

import pytest

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


# Three people whose display names one Spotify response replaced with their user IDs
BURST_OLD = [{"name": f"Person {index}", "uri": f"spotify:user:person{index}"} for index in range(3)]
BURST_NEW = [{"name": f"person{index}", "uri": f"spotify:user:person{index}"} for index in range(3)]
BURST_HELD = "3 followers changed their display names at once with no profiles available to confirm them, streak {streak}/3; old names retained"
BURST_CONTRADICTED = "3 followers changed their display names at once but their profiles show other names; old names retained"
BURST_VERIFIED = "3 followers changed their display names at once and their profiles show the new names; reporting them"


# Makes three renames in one check a burst that needs three matching checks when the profiles cannot be read
def small_burst(monkeypatch, counter=3):
    monkeypatch.setattr(monitor, "FOLLOWERS_FOLLOWINGS_RENAME_BURST", 2)
    monkeypatch.setattr(monitor, "FOLLOWERS_FOLLOWINGS_RENAME_COUNTER", counter)


# Answers profile lookups from a URI to name mapping, failing for other URIs, and returns the URIs read
def profiles_showing(monkeypatch, names):
    looked_up = []

    # Stands in for the real profile request
    def lookup(_access_token, user_uri):
        looked_up.append(user_uri)
        if user_uri not in names:
            raise RuntimeError("profile unavailable")
        return names[user_uri]

    monkeypatch.setattr(monitor, "spotify_get_profile_name", lookup)
    return looked_up


# Maps each profile in a list to the name it carries
def names_of(profiles):
    return {profile["uri"]: profile["name"] for profile in profiles}


# Returns how many matching checks a held burst has seen, or None when nothing is held
def streak_of(pending):
    return pending["streak"] if pending else None


# Writes a saved follower history so startup compares against it
def saved_followers(monkeypatch, tmp_path, profiles):
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "burst")
    monkeypatch.setattr(monitor, "JSON_DIR", "")
    (tmp_path / monitor.build_json_history_paths("burst", "")[0]).write_text(json.dumps([len(profiles), profiles]), encoding="utf-8")


# Returns the new and old lists of every follower report the loop made
def reported(events):
    return [(event[1], event[2]) for event in events]


# Profiles that show the new names prove the burst real, so it is reported without waiting for more checks
def test_profiles_showing_the_new_names_report_a_burst_at_once(monkeypatch):
    small_burst(monkeypatch)
    profiles_showing(monkeypatch, names_of(BURST_NEW))

    assert monitor.hold_follow_rename_burst(BURST_NEW, BURST_OLD, None, "access-token") == (BURST_NEW, None, "verified", 3)


# The user's own case: the lists carried user IDs while the profiles still showed the real names, which outweighs any streak
def test_profiles_showing_other_names_keep_the_old_ones(monkeypatch):
    small_burst(monkeypatch)
    looked_up = profiles_showing(monkeypatch, names_of(BURST_OLD))

    assert monitor.hold_follow_rename_burst(BURST_NEW, BURST_OLD, {"names": names_of(BURST_NEW), "streak": 2}, "access-token") == (BURST_OLD, None, "contradicted", 3)
    assert looked_up == [BURST_NEW[0]["uri"]]


# A profile that cannot be read proves nothing, so the burst waits for repeated checks instead
def test_an_unreadable_profile_falls_back_to_repeated_checks(monkeypatch):
    small_burst(monkeypatch)
    profiles_showing(monkeypatch, names_of(BURST_NEW[:2]))

    held, pending, outcome, _ = monitor.hold_follow_rename_burst(BURST_NEW, BURST_OLD, None, "access-token")

    assert (held, outcome, streak_of(pending)) == (BURST_OLD, "held", 1)


# Only a few profiles are read, taken from across the burst so a glitch that hit part of the list is still seen
def test_the_profile_check_samples_across_the_burst(monkeypatch):
    small_burst(monkeypatch)
    old = [{"name": f"Person {index}", "uri": f"spotify:user:person{index}"} for index in range(10)]
    new = [{**profile, "name": f"person{index}"} for index, profile in enumerate(old)]
    looked_up = profiles_showing(monkeypatch, names_of(new))

    assert monitor.hold_follow_rename_burst(new, old, None, "access-token")[2] == "verified"
    assert looked_up == ["spotify:user:person0", "spotify:user:person4", "spotify:user:person9"]


# Follower URIs carry percent-encoded IDs, and artists in a followings list have no user profile to read
def test_the_profile_lookup_decodes_user_ids_and_skips_artists(monkeypatch):
    requests = []
    monkeypatch.setattr(monitor, "spotify_get_user_info", lambda *arguments: requests.append(arguments) or {"sp_username": "Music Fan"})

    assert monitor.spotify_get_profile_name("access-token", "spotify:user:%21%21fan%21%21") == "Music Fan"
    assert monitor.spotify_get_profile_name("access-token", "spotify:artist:0LcJLqbBmaGUft1e9Mm8HV") is None
    assert requests == [("access-token", "!!fan!!", False, 0)]


# Without readable profiles a burst keeps the old names while it repeats and is handed over once it has repeated enough times
def test_an_unchecked_burst_keeps_the_old_names_until_it_repeats(monkeypatch):
    small_burst(monkeypatch)

    held, pending, outcome, burst = monitor.hold_follow_rename_burst(BURST_NEW + [ANIA], BURST_OLD + [ANIA], None)
    assert (held, outcome, burst, streak_of(pending)) == (BURST_OLD + [ANIA], "held", 3, 1)

    held, pending, outcome, _ = monitor.hold_follow_rename_burst(BURST_NEW + [ANIA], held, pending)
    assert (held, outcome, streak_of(pending)) == (BURST_OLD + [ANIA], "held", 2)

    assert monitor.hold_follow_rename_burst(BURST_NEW + [ANIA], held, pending) == (BURST_NEW + [ANIA], None, "repeated", 3)


# Spotify can swap user IDs for Facebook names between checks, which is a different burst and starts counting again
def test_a_burst_with_different_names_restarts_the_streak(monkeypatch):
    small_burst(monkeypatch)
    facebook_names = [{**profile, "name": f"Full Name {index}"} for index, profile in enumerate(BURST_OLD)]

    _, pending, _, _ = monitor.hold_follow_rename_burst(BURST_NEW, BURST_OLD, None)
    _, pending, _, _ = monitor.hold_follow_rename_burst(facebook_names, BURST_OLD, pending)

    assert streak_of(pending) == 1


# Renames up to the burst size are reported at once and a counter of 0 or 1 turns the protection off
@pytest.mark.parametrize("counter,current", [(3, BURST_NEW[:2] + BURST_OLD[2:]), (0, BURST_NEW), (1, BURST_NEW)])
def test_small_rename_sets_and_a_disabled_hold_pass_through(monkeypatch, counter, current):
    small_burst(monkeypatch, counter=counter)
    looked_up = profiles_showing(monkeypatch, {})

    assert monitor.hold_follow_rename_burst(current, BURST_OLD, None, "access-token") == (current, None, "", 0)
    assert looked_up == []


# An entry that had no name before gets none back, so the held list still compares equal to the baseline
def test_a_held_entry_without_an_earlier_name_stays_nameless(monkeypatch):
    small_burst(monkeypatch)
    nameless = [{"uri": profile["uri"]} for profile in BURST_OLD]

    held, pending, _, _ = monitor.hold_follow_rename_burst(BURST_NEW, nameless, None)

    assert held == nameless
    assert streak_of(pending) == 1


# Tonight's case end to end: one bad response that the profiles contradict and a next check with the real names
def test_the_loop_stays_silent_about_a_rename_burst_that_clears(monkeypatch, tmp_path, capsys):
    small_burst(monkeypatch)
    profiles_showing(monkeypatch, names_of(BURST_OLD))
    events = []

    error_alerts_for(monkeypatch, tmp_path, [], 3, follower_answers=[{"sp_user_followers": BURST_NEW}, {"sp_user_followers": BURST_OLD}], initial_followers=BURST_OLD, collection_events=events)

    assert events == []
    assert BURST_CONTRADICTED in capsys.readouterr().out


# A glitch the profiles keep contradicting is never reported, however many checks it lasts
def test_the_loop_never_reports_a_burst_its_profiles_contradict(monkeypatch, tmp_path):
    small_burst(monkeypatch)
    profiles_showing(monkeypatch, names_of(BURST_OLD))
    events = []

    error_alerts_for(monkeypatch, tmp_path, [], 5, follower_answers=[{"sp_user_followers": BURST_NEW}] * 4, initial_followers=BURST_OLD, collection_events=events)

    assert events == []


# A burst the profiles confirm is reported on the check that found it
def test_the_loop_reports_a_burst_its_profiles_confirm(monkeypatch, tmp_path, capsys):
    small_burst(monkeypatch)
    profiles_showing(monkeypatch, names_of(BURST_NEW))
    events = []

    error_alerts_for(monkeypatch, tmp_path, [], 2, follower_answers=[{"sp_user_followers": BURST_NEW}], initial_followers=BURST_OLD, collection_events=events)

    assert reported(events) == [(BURST_NEW, BURST_OLD)]
    assert BURST_VERIFIED in capsys.readouterr().out


# Followings are checked on their own, since the same bad response can rename both lists
def test_the_loop_stays_silent_about_a_following_burst_that_clears(monkeypatch, tmp_path, capsys):
    small_burst(monkeypatch)
    profiles_showing(monkeypatch, names_of(BURST_OLD))
    events = []

    error_alerts_for(monkeypatch, tmp_path, [], 3, following_answers=[{"sp_user_followings": profiles} for profiles in (BURST_OLD, BURST_NEW, BURST_OLD)], collection_events=events)

    assert events == []
    assert "3 followings changed their display names at once but their profiles show other names; old names retained" in capsys.readouterr().out


# Without readable profiles a burst that survives the confirmation checks is reported once, against the names it replaced
def test_the_loop_reports_an_unchecked_burst_that_persists(monkeypatch, tmp_path, capsys):
    small_burst(monkeypatch)
    profiles_showing(monkeypatch, {})
    events = []

    error_alerts_for(monkeypatch, tmp_path, [], 4, follower_answers=[{"sp_user_followers": BURST_NEW}] * 3, initial_followers=BURST_OLD, collection_events=events)

    assert reported(events) == [(BURST_NEW, BURST_OLD)]
    output = capsys.readouterr().out
    assert BURST_HELD.format(streak=2) in output
    assert "The same 3 renames among followers were seen in 3 checks in a row; reporting them" in output


# Someone who arrives while a burst is held is still reported, next to the old names
def test_an_arrival_during_a_held_burst_is_reported(monkeypatch, tmp_path):
    small_burst(monkeypatch)
    profiles_showing(monkeypatch, names_of(BURST_OLD))
    events = []

    error_alerts_for(monkeypatch, tmp_path, [], 2, follower_answers=[{"sp_user_followers": BURST_NEW + [NEWCOMER]}], initial_followers=BURST_OLD, collection_events=events)

    assert reported(events) == [(BURST_OLD + [NEWCOMER], BURST_OLD)]


# History saved during a glitch holds the wrong names, and the profiles confirm the real ones as soon as the monitor starts
def test_startup_reports_a_correction_the_profiles_confirm(monkeypatch, tmp_path):
    small_burst(monkeypatch)
    saved_followers(monkeypatch, tmp_path, BURST_NEW)
    profiles_showing(monkeypatch, names_of(BURST_OLD))
    events = []

    # The run stops before its first loop check, so the report can only come from startup
    error_alerts_for(monkeypatch, tmp_path, [], 1, initial_followers=BURST_OLD, collection_events=events)

    assert reported(events) == [(BURST_OLD, BURST_NEW)]


# Startup compares against saved history once, so an unchecked burst found there is held and its streak carries into the loop
@pytest.mark.parametrize("answers,expected", [([BURST_OLD], []), ([BURST_NEW, BURST_NEW], [(BURST_NEW, BURST_OLD)])])
def test_an_unchecked_burst_against_saved_history_is_held_at_startup(monkeypatch, tmp_path, capsys, answers, expected):
    small_burst(monkeypatch)
    saved_followers(monkeypatch, tmp_path, BURST_OLD)
    profiles_showing(monkeypatch, {})
    events = []

    error_alerts_for(monkeypatch, tmp_path, [], len(answers) + 1, follower_answers=[{"sp_user_followers": answer} for answer in answers], initial_followers=BURST_NEW, collection_events=events)

    assert reported(events) == expected
    assert BURST_HELD.format(streak=1) in capsys.readouterr().out


# Negative values cannot describe a burst size or a number of checks
@pytest.mark.parametrize("name", ["FOLLOWERS_FOLLOWINGS_RENAME_BURST", "FOLLOWERS_FOLLOWINGS_RENAME_COUNTER"])
def test_negative_rename_burst_settings_are_rejected(monkeypatch, name):
    monkeypatch.setattr(monitor, name, -1)

    assert f"{name}=-1" in monitor.runtime_numeric_errors()

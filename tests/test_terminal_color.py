"""Terminal colour contract tests for the coloured output layer."""

import argparse
import re
from io import StringIO
from pathlib import Path

import pytest

import spotify_profile_monitor as monitor


CHANGE_REPORT_LINES = ("* Playlist 'bzy i kosy': number of tracks changed from 22 to 23 (+1)", "* Playlists number changed for user martus from 2 to 1 (-1)", "* User martus has changed profile picture !")


# Enables colour with a known style map so assertions do not depend on the shipped theme
@pytest.fixture
def colored(monkeypatch):
    styles = {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", styles)
    return styles


# Reads a block the template ships commented out, as the parser would see it once uncommented
def uncomment_block(first_line):
    lines = monitor.CONFIG_BLOCK.split("\n")
    start = next(index for index, line in enumerate(lines) if line.startswith(first_line))
    end = next(index for index in range(start, len(lines)) if lines[index].rstrip() == "# }")
    return "\n".join(line[2:] if line.startswith("# ") else line[1:] for line in lines[start:end + 1])


# Verifies the shipped config template and the built-in theme describe exactly the same keys
def test_config_template_theme_matches_the_built_in_theme():
    values = monitor.parse_config_content(monitor.CONFIG_BLOCK, "<built-in-config>")
    commented = monitor.parse_config_content(uncomment_block("# COLOR_THEME = {"), "<built-in-config>")

    assert values["COLORED_OUTPUT"] is True
    assert "COLOR_THEME" not in values
    assert commented["COLOR_THEME"] == monitor.DEFAULT_COLOR_THEME


# Verifies a configuration that sets the commented-out theme is still accepted, since older files all set it
def test_a_config_setting_the_theme_is_still_accepted(tmp_path):
    config = tmp_path / "monitor.conf"
    config.write_text('COLOR_THEME = { "username": "green" }\n', encoding="utf-8")

    assert monitor.parse_config_content(config.read_text(encoding="utf-8"), str(config)) == {"COLOR_THEME": {"username": "green"}}


# Verifies every style word used by the shipped theme resolves, allowing a deliberately uncoloured part
def test_default_theme_styles_all_resolve():
    for name, value in monitor.DEFAULT_COLOR_THEME.items():
        assert monitor._build_ansi_sequence(value) or value == "", name


# Verifies the Timestamp label is left uncoloured, matching the sibling monitors
def test_timestamp_label_is_uncolored(colored):
    assert monitor.DEFAULT_COLOR_THEME["timestamp_label"] == ""
    assert "timestamp_label" not in colored
    assert monitor._colorize_line("Timestamp:\t\t\tWed 26 Aug 2026, 20:23:03") == f"Timestamp:\t\t\t{colored['timestamp_value']}Wed 26 Aug 2026, 20:23:03{monitor.ANSI_RESET}"


# Verifies the liveness banner timestamp carries the timestamp colour instead of the generic date colour
def test_liveness_check_timestamp_uses_timestamp_style(colored):
    line = monitor._colorize_line("Liveness check, timestamp:\tWed 26 Aug 2026, 20:23:03")
    assert line == f"Liveness check, timestamp:\t{colored['timestamp_value']}Wed 26 Aug 2026, 20:23:03{monitor.ANSI_RESET}"


# Verifies a startup summary row is not block-coloured just because it names a mode
def test_startup_summary_rows_are_not_block_colored(colored):
    for line in ("* Mode:                         Spotify-to-Last.fm scrobble health", "* Target:                       misiektoja", "* Polling interval:             1 minute"):
        assert monitor.ANSI_ESCAPE_RE.sub("", monitor._colorize_line(line)) == line
        assert colored["info"] not in monitor._colorize_line(line)


# Verifies the timer row whose label names a problem word reports a setting, so it keeps the plain label and
# green duration of every other summary row instead of turning red
def test_startup_summary_timer_row_is_not_error_colored(colored):
    line = "* Error retry timer:            3 minutes"

    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert colored["error"] not in result
    assert f"{colored['duration']}3 minutes{monitor.ANSI_RESET}" in result


# Verifies a debug trace line and a fallback notice are not painted red, while a real problem still is. A debug
# line records an attempt the tool then handles, and a backend switch reports a recovery that worked
@pytest.mark.parametrize("line", [
    "[DEBUG 15:57:30] HTTP GET https://api.spotify.com/v1 [connectivity check], timeout=5, verify_ssl=True",
    "[DEBUG 15:57:30] HTTP HEAD https://open.spotify.com/ [server time] timeout=15",
    "[DEBUG 16:05:53] _spotify_get_playlist_info_api(): failed for uri=spotify:playlist:64038SKKJNi7GIAh16NlRr: 403 Client Error: Forbidden for url",
    "* Playlist metadata switched to the web-player backend after legacy API failures",
])
def test_diagnostic_details_and_fallback_notices_are_not_error_colored(colored, line):
    assert colored["error"] not in monitor._colorize_line(line)


# Verifies the same words still paint a line that really reports a problem
@pytest.mark.parametrize("line", ["Spotify follow verification failed: bad token", "* Error: request timeout after 15 seconds"])
def test_real_problem_lines_stay_error_colored(colored, line):
    assert monitor._colorize_line(line).startswith(colored["error"])


# Verifies a static count stays plain and only a reported change colours its numbers
def test_static_counts_stay_plain_and_changes_are_colored(colored):
    for line in ("Followers:\t\t\t98", "Followings:\t\t\t302", "Public playlists:\t\t41", "Number of friends:\t\t7"):
        assert monitor._colorize_line(line) == line

    changed = monitor._colorize_line("* Followers number changed for user john from 98 to 100 (+2)")
    assert colored["count_up"] in changed


# Verifies colouring only inserts escape sequences and never changes the text itself
@pytest.mark.parametrize("line", [
    "Username:\t\t\tJohn Doe",
    "Spotify user ID:\t\t31nnv6eqt4qswvjhcnknimtxqife",
    "Playlist 'Chill Vibes' owned by 'John Doe':",
    "Songs:\t\t\t150 (3 filtered out)",
    "URL:\t\t\thttps://open.spotify.com/playlist/abc",
    "* Followers number changed for user john from 10 to 12 (+2)",
    "* Signal SIGUSR1 received",
    "Timestamp:\t\t\tSun 21 Apr 2024, 15:08:45",
])
def test_colorize_line_never_rewrites_the_text(colored, line):
    assert monitor.ANSI_ESCAPE_RE.sub("", monitor._colorize_line(line)) == line


# Verifies the ASCII startup banner reaches the terminal in one colour. The art contains apostrophes, slashes
# and underscores, so a line rule reading part of it as a name would leave the logo patchy
def test_startup_banner_uses_only_its_own_colours(colored, capsys):
    monitor.print_startup_banner()
    printed = capsys.readouterr().out

    rendered = monitor.apply_color_to_text(printed)

    assert monitor.ANSI_ESCAPE_RE.sub("", rendered) == monitor.ANSI_ESCAPE_RE.sub("", printed)
    assert set(monitor.SGR_SEQUENCE_RE.findall(rendered)) <= {colored["header"], colored["info"], monitor.ANSI_RESET}
    for art_line in monitor.STARTUP_BANNER.splitlines():
        if art_line:
            assert f"{colored['header']}{art_line}{monitor.ANSI_RESET}" in rendered


# Verifies colouring the banner does not change the characters it draws
def test_startup_banner_art_is_unchanged(colored):
    colored_banner = monitor.apply_color_to_text(monitor.STARTUP_BANNER)

    assert monitor.ANSI_ESCAPE_RE.sub("", colored_banner) == monitor.STARTUP_BANNER


# Verifies labelled Spotify rows colour the value with the expected theme part
@pytest.mark.parametrize("line,part", [
    ("Username:\t\t\tJohn Doe", "username"),
    ("Spotify user ID:\t\tsq58", "id"),
    ("Duration:\t\t\t9 hours", "duration"),
])
def test_labelled_rows_use_the_expected_theme_part(colored, line, part):
    assert colored[part] in monitor._colorize_line(line)


# Verifies Doctor status markers are coloured while the rest of the line stays plain
@pytest.mark.parametrize("marker,part", [("PASS", "boolean_true"), ("WARN", "warning"), ("FAIL", "error"), ("SKIP", "info")])
def test_doctor_status_markers_are_colored(colored, marker, part):
    line = f"[{marker}] SP_DC_COOKIE is missing or still a placeholder"

    result = monitor._colorize_line(line)

    assert result == f"{colored[part]}[{marker}]{monitor.ANSI_RESET} SP_DC_COOKIE is missing or still a placeholder"


# Verifies quoted names take the colour of what the line is about
def test_quoted_names_follow_the_subject_of_the_line(colored):
    assert colored["playlist"] in monitor._colorize_line("Playlist 'Chill Vibes' owned by 'John Doe':")
    assert colored["username"] in monitor._colorize_line("* User 'oldname' has changed username to 'newname'")


# Verifies the word "user" inside a URI form is not read as the label that introduces a user name
def test_a_uri_form_named_in_prose_is_not_coloured_as_a_user_name(colored):
    line = "For <spotify_target>, use a complete Spotify profile URL, spotify:user URI or user ID."

    assert monitor._colorize_line(line) == line
    assert colored["id"] in monitor._colorize_line("for user martus")
    assert colored["id"] in monitor._colorize_line("Monitoring user martus")


# Verifies a quoted file name stays plain so log and state paths are not read as content
def test_quoted_file_names_stay_plain(colored):
    line = "* Playlists (12) loaded from file 'spotify_profile_monitor_john.json'"

    assert monitor._colorize_line(line) == line


# Verifies counter directions pick the rising and falling styles apart
def test_counter_direction_picks_the_matching_style(colored):
    assert colored["count_up"] in monitor._colorize_line("* Followers number changed for user john from 10 to 12 (+2)")
    assert colored["count_down"] in monitor._colorize_line("* Followings number changed for user john from 20 to 18 (-2)")


# Verifies time highlighting accepts valid clock values without matching numeric port mappings
@pytest.mark.parametrize("value", ["00:00", "23:59", "21:07:39", "~21:07:39", "09:15 PM"])
def test_time_color_regex_accepts_only_complete_clock_values(value):
    assert monitor._TIME_ONLY_RE.fullmatch(value)
    for invalid in ("24:00", "12:60", "8000:8000", "abc12:30", "1:12:30"):
        assert monitor._TIME_ONLY_RE.search(invalid) is None


# Verifies hostile terminal control sequences in Spotify text cannot drive the operator's terminal
@pytest.mark.parametrize("hostile,expected", [
    ("playlist\x1b[2Jcleared", "playlist[2Jcleared"),
    ("playlist\x1b]0;stolen title\x07", "playlist]0;stolen title"),
    ("visible\rhidden", "visiblehidden"),
    ("bell\x07 and null\x00", "bell and null"),
    ("delete\x7f and c1\x9b[3J", "delete and c1[3J"),
])
def test_sanitize_terminal_text_removes_control_sequences(hostile, expected):
    assert monitor.sanitize_terminal_text(hostile) == expected


# Verifies the tool's own colour codes and ordinary whitespace survive sanitization
def test_sanitize_terminal_text_keeps_colours_and_layout():
    coloured = "\033[36mInfo\033[0m\tvalue\nnext line"

    assert monitor.sanitize_terminal_text(coloured) == coloured


# Verifies Spotify text cannot smuggle an escape sequence between the tool's own colour codes
def test_sanitize_terminal_text_cleans_between_colour_codes():
    smuggled = "\033[36mlabel\033[0m \x1b[2J\033[31mvalue\033[0m"

    assert monitor.sanitize_terminal_text(smuggled) == "\033[36mlabel\033[0m [2J\033[31mvalue\033[0m"


# Builds a Logger writing into two in-memory buffers and returns it with both buffers
def make_logger():
    terminal = StringIO()
    logfile = StringIO()
    logger = monitor.Logger.__new__(monitor.Logger)
    logger.__dict__["terminal"] = terminal
    logger.__dict__["logfile"] = logfile
    return logger, terminal, logfile


# Verifies the log file stays plain text while the terminal receives the coloured version
def test_logger_colors_the_terminal_and_keeps_the_log_plain(colored, monkeypatch):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    logger, terminal, logfile = make_logger()

    logger.write("Username:\t\t\tJohn Doe\n")

    assert colored["username"] in terminal.getvalue()
    assert "\x1b" not in logfile.getvalue()
    assert logfile.getvalue().startswith("Username:")


# Verifies truncation measures plain text so escape sequences never consume the visible width
def test_truncation_runs_before_colour_is_applied(colored, monkeypatch):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 20)
    logger, terminal, _logfile = make_logger()

    logger.write("Username:\tJohn Doe The Very Long Display Name\n")

    plain = monitor.ANSI_ESCAPE_RE.sub("", terminal.getvalue()).rstrip("\n")
    assert len(plain.expandtabs(8)) == 20
    assert colored["username"] in terminal.getvalue()


# Verifies the terminal-only stream colours output while still neutralizing hostile text
def test_terminal_stream_colors_and_sanitizes(colored):
    terminal = StringIO()

    monitor.TerminalStream(terminal).write("Username:\tJohn\x1b[2JDoe\n")

    assert colored["username"] in terminal.getvalue()
    assert "\x1b[2J" not in terminal.getvalue()


# Verifies the playlist progress bar never carries a colour code into its overwritten line
def test_playlist_progress_bar_strips_every_escape(colored, monkeypatch):
    terminal = StringIO()
    monkeypatch.setattr(monitor, "stdout_bck", terminal)

    monitor._display_progress(1, 2, "Chill\x1b[31m\x1b[2JVibes")

    output = terminal.getvalue()
    assert output.startswith("\r\x1b[K")
    assert "\x1b" not in output[3:]


# Verifies the transient Doctor progress line stays uncoloured so its erase width remains correct
def test_doctor_progress_line_is_never_colored(colored, monkeypatch):
    written = []
    terminal = type("Stream", (), {"isatty": lambda self: True, "write": lambda self, text: written.append(text), "flush": lambda self: None})()
    monkeypatch.setattr(monitor, "_doctor_terminal_stream", lambda: terminal)
    monkeypatch.setattr(monitor._doctor_progress, "last_width", 0, raising=False)

    monitor._doctor_progress("Spotify authentication")
    progress_line = written[-1]
    monitor._doctor_progress_clear()

    assert "\x1b" not in "".join(written)
    assert written[-1] == "\r" + (" " * (len(progress_line) - 1)) + "\r"


# Verifies the doctor progress stream unwraps every output wrapper down to the real terminal
def test_doctor_terminal_stream_unwraps_output_wrappers(monkeypatch):
    real_terminal = StringIO()
    logger, _terminal, _logfile = make_logger()
    logger.__dict__["terminal"] = monitor.TerminalStream(real_terminal)
    monkeypatch.setattr(monitor.sys, "stdout", logger)

    assert monitor._doctor_terminal_stream() is real_terminal


# Verifies colour stays off unless the stream is an interactive terminal that allows it
def test_stream_support_detection_honours_environment(monkeypatch):
    monkeypatch.setattr(monitor.sys, "stdin", type("Stdin", (), {"isatty": lambda self: True})())
    interactive = type("Stream", (), {"isatty": lambda self: True})()
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)

    assert monitor._stream_supports_color(interactive) is True
    assert monitor._stream_supports_color(type("Stream", (), {"isatty": lambda self: False})()) is False

    monkeypatch.setenv("NO_COLOR", "1")
    assert monitor._stream_supports_color(interactive) is False
    monkeypatch.delenv("NO_COLOR")

    monkeypatch.setenv("TERM", "dumb")
    assert monitor._stream_supports_color(interactive) is False


# Verifies a piped stdin disables colour so redirected output never carries escape sequences
def test_piped_stdin_disables_color(monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(monitor.sys, "stdin", type("Stdin", (), {"isatty": lambda self: False})())

    assert monitor._stream_supports_color(type("Stream", (), {"isatty": lambda self: True})()) is False


# Verifies a configured theme overrides only the parts it names and leaves the rest built in
def test_config_theme_overrides_only_named_parts(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"username": "red bold"})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)

    monitor.init_color_output(StringIO())

    assert monitor.COLOR_ENABLED is True
    assert monitor._COLOR_STYLES["username"] == "\033[31;1m"
    assert monitor._COLOR_STYLES["playlist"] == monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["playlist"])


# Verifies a disabled setting clears the style map so colorize becomes a no-op
def test_disabled_color_output_clears_the_style_map(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", False)
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)

    monitor.init_color_output(StringIO())

    assert monitor.COLOR_ENABLED is False
    assert monitor._COLOR_STYLES == {}
    assert monitor.colorize("username", "John") == "John"
    assert monitor.apply_color_to_text("Username:\tJohn\n") == "Username:\tJohn\n"


# Verifies the early config peek applies terminal appearance before arguments are parsed
def test_early_output_config_reads_terminal_appearance(monkeypatch, tmp_path):
    config_file = tmp_path / "spotify_profile_monitor.conf"
    config_file.write_text("CLEAR_SCREEN = False\nCOLORED_OUTPUT = False\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor.py", "--config-file", str(config_file)])
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)

    monitor.apply_early_output_config()

    assert monitor.CLEAR_SCREEN is False
    assert monitor.COLORED_OUTPUT is False


# Verifies a broken config leaves the early defaults alone so the later load reports the error
def test_early_output_config_ignores_a_broken_config(monkeypatch, tmp_path):
    config_file = tmp_path / "spotify_profile_monitor.conf"
    config_file.write_text("import os\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor.py", "--config-file", str(config_file)])
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)

    monitor.apply_early_output_config()

    assert monitor.COLORED_OUTPUT is True


# Verifies disabled config discovery skips the early peek entirely
def test_early_output_config_skips_disabled_discovery(monkeypatch):
    calls = []
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor.py", "--config-file", "none"])
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: calls.append(path))

    monitor.apply_early_output_config()

    assert calls == []


# Verifies the raw argument scan finds the config path in both accepted spellings
@pytest.mark.parametrize("arguments,expected", [
    (["--config-file", "/tmp/one.conf"], "/tmp/one.conf"),
    (["--config-file=/tmp/two.conf"], "/tmp/two.conf"),
    (["--verbose"], None),
    (["--config-file"], None),
])
def test_early_config_file_argument_scan(arguments, expected):
    assert monitor.early_config_file_argument(arguments) == expected


# Verifies --no-color turns colour off even when the config file enables it
def test_no_color_flag_disables_colored_output(monkeypatch):
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor.py", "--no-color"])
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)

    if "--no-color" in monitor.sys.argv:
        monitor.COLORED_OUTPUT = False
    monitor.init_color_output(StringIO())

    assert monitor.COLOR_ENABLED is False


# Verifies the logger writes past the early sanitizing stream so no line is colourised twice
def test_logger_unwraps_the_early_terminal_stream(colored, monkeypatch, tmp_path):
    raw_terminal = StringIO()
    monkeypatch.setattr(monitor.sys, "stdout", monitor.TerminalStream(raw_terminal))
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    logger = monitor.Logger(str(tmp_path / "monitor.log"))
    try:
        logger.write("Timestamp:\t\t\tWed 26 Aug 2026, 20:23:03\n")
    finally:
        logger.logfile.close()

    assert logger.terminal is raw_terminal
    # A second colour pass would no longer see the label and would recolour the value as a date
    assert raw_terminal.getvalue() == f"Timestamp:\t\t\t{colored['timestamp_value']}Wed 26 Aug 2026, 20:23:03{monitor.ANSI_RESET}\n"


# Verifies the unwrapper reaches the real terminal through any depth of sanitizing wrappers
def test_unwrap_terminal_stream_reaches_the_real_terminal():
    raw_terminal = StringIO()

    assert monitor.unwrap_terminal_stream(raw_terminal) is raw_terminal
    assert monitor.unwrap_terminal_stream(monitor.TerminalStream(monitor.TerminalStream(raw_terminal))) is raw_terminal


# Verifies a rule cannot reclaim text an earlier rule already coloured, so each value gets one clean span
def test_inline_rules_do_not_reclaim_already_colored_text(colored):
    result = monitor._colorize_line("[ date: Sun 16 Feb 2025, 14:34:06 - 1 year ago ]")

    assert result.count(colored["date"]) == 1
    assert result == f"[ date: {colored['date']}Sun 16 Feb 2025, 14:34:06{monitor.ANSI_RESET} - {colored['duration']}1 year{monitor.ANSI_RESET} ago ]"


# Verifies a name is coloured whatever punctuation it contains, so listings do not colour only some rows
@pytest.mark.parametrize("name", ["3 AM Sessions", "BDSM (dark techno/electronica)", "Hypnotic Trance / Techno / House", "Tomorrowland (TML) Festival Music", "Nocturne Rewired"])
def test_names_with_slashes_and_brackets_are_still_colored(colored, name):
    assert colored["playlist"] in monitor._colorize_line(f"- '{name}'")


# Verifies a name's own apostrophe does not end it early, which left most of the name uncoloured
@pytest.mark.parametrize("name", ["Don't Stop Me Now", "Ain't No Mountain High Enough"])
def test_a_name_containing_an_apostrophe_is_coloured_whole(colored, name):
    assert f"{colored['playlist']}{name}{monitor.ANSI_RESET}" in monitor._colorize_line(f"- '{name}'")


# Verifies two quoted names on one line stay two names, since the closing quote rule could have joined them
def test_two_quoted_names_on_one_line_stay_separate(colored):
    result = monitor._colorize_line("- 'Deep Focus' and 'Peaceful Piano'")

    assert f"{colored['playlist']}Deep Focus{monitor.ANSI_RESET}" in result
    assert f"{colored['playlist']}Peaceful Piano{monitor.ANSI_RESET}" in result


# Verifies a quoted placeholder inside a printed command stays plain, since it is text to replace rather than a name
@pytest.mark.parametrize("line", ["Run: spotify_profile_monitor '<user_uri_id>'", "Replace '<topic>' with your own ntfy topic"])
def test_quoted_command_placeholders_stay_plain(colored, line):
    assert colored["playlist"] not in monitor._colorize_line(line)


# Verifies a quoted command-line option is left plain, since it is text to retype rather than a name
def test_quoted_command_options_stay_plain(colored):
    assert colored["playlist"] not in monitor._colorize_line("Replace '--env-file none' with a writable path")


# Verifies a quoted fragment of a URL stays plain, since it is a piece of an address rather than a name
@pytest.mark.parametrize("value", ["?code=", "&state="])
def test_quoted_url_fragments_stay_plain(colored, value):
    line = f"Copy everything after '{value}' from the address bar."

    assert monitor._colorize_line(line) == line


# Verifies quoted values shaped like a file name or a path stay plain
@pytest.mark.parametrize("value", ["monitor_state.json", "/data/spotify.log", "~/logs/output.txt", "C:\\Users\\me\\state.json"])
def test_quoted_file_and_path_values_stay_plain(colored, value):
    line = f"* State loaded from '{value}'"

    assert monitor._colorize_line(line) == line


# Verifies a standalone quoted description is left plain instead of being read as a name
def test_standalone_quoted_description_stays_plain(colored):
    line = "'Dark, dirty, underground, cyberpunk techno / electronica for consensual sessions.'"

    assert monitor._colorize_line(line) == line


# Verifies a bracketed listing row colours the owner while its static counts stay plain
def test_bracketed_listing_metadata_colors_only_the_owner(colored):
    counts = "[ songs: 72, likes: 7, collaborators: 1 ]"

    assert monitor._colorize_line(counts) == counts
    assert monitor._colorize_line("[ owner: misiektoja ]") == f"[ owner: {colored['username']}misiektoja{monitor.ANSI_RESET} ]"


# Verifies a date row colours the date and keeps the elapsed time beside it green, like the bracketed rows
def test_date_rows_keep_the_elapsed_time_green(colored):
    line = "  Creation date: Sun 06 Apr 2025, 21:21:46 (1 year, 4 months, 2 weeks ago)"

    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert f"{colored['date']}Sun 06 Apr 2025, 21:21:46{monitor.ANSI_RESET}" in result
    for elapsed in ("1 year", "4 months", "2 weeks"):
        assert f"{colored['duration']}{elapsed}{monitor.ANSI_RESET}" in result


# Verifies a listing row takes its colour from the reference in its brackets rather than from the row order
@pytest.mark.parametrize("line,part", [
    ("- bzy i kosy [ https://open.spotify.com/playlist/64038SKKJNi7GIAh16NlRr?si=1 ]", "playlist"),
    ("- Some Person [ https://open.spotify.com/user/31nnv6eqt4qswvjhcnknimtxqife?si=1 ]", "username"),
    ("- Mikromusic - Po co ja tu jestem [ Wed 26 Aug 2026, 23:02:25, martus ]", "track"),
])
def test_listing_rows_are_colored_from_their_reference(colored, line, part):
    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert colored[part] in result


# Verifies the collaborator who added a track is coloured as a person
def test_track_row_colors_the_collaborator(colored):
    result = monitor._colorize_line("- Mikromusic - Po co ja tu jestem [ Wed 26 Aug 2026, 23:02:25, martus ]")

    assert f"{colored['username']}martus{monitor.ANSI_RESET}" in result


# Verifies a row this tool does not recognize is left alone instead of being guessed at
@pytest.mark.parametrize("line", [
    "- Skipping playlist bzy i kosy [ https://open.spotify.com/playlist/64038 ] due to cached error or missing data",
    "- collab [songs: 12, 5.0%] [URL: https://open.spotify.com/user/abc ]",
])
def test_unrecognized_listing_rows_keep_their_name_plain(colored, line):
    result = monitor._colorize_line(line)

    assert colored["playlist"] not in result
    assert colored["track"] not in result


# Verifies the monitored target renders as an ID everywhere it is named, since this tool identifies a
# profile by URI ID rather than by display name
@pytest.mark.parametrize("line", [
    "Monitoring user 31nnv6eqt4qswvjhcnknimtxqife",
    "Spotify user ID:\t\t31nnv6eqt4qswvjhcnknimtxqife",
    "* Target:                       31nnv6eqt4qswvjhcnknimtxqife",
])
def test_target_id_uses_the_id_colour_everywhere(colored, line):
    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert f"{colored['id']}31nnv6eqt4qswvjhcnknimtxqife{monitor.ANSI_RESET}" in result


# Verifies a config written against the pre-rename 'user_uri_id' key still colours identifiers
def test_legacy_theme_key_still_applies(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"user_uri_id": "red"})
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)
    monitor.init_color_output(StringIO())
    assert monitor._COLOR_STYLES["id"] == monitor._build_ansi_sequence("red")


# Verifies the current key name wins when a config sets both the old and the new name
def test_current_theme_key_wins_over_the_legacy_name(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"user_uri_id": "red", "id": "green"})
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)
    monitor.init_color_output(StringIO())
    assert monitor._COLOR_STYLES["id"] == monitor._build_ansi_sequence("green")


# Verifies the word before a quoted value decides its colour, even when the line also mentions playlists
@pytest.mark.parametrize("line,part", [
    ("* Spotify API: suspected transient playlist change for user 'martus' (2 -> 1), streak 1/2", "username"),
    ("* Spotify API: suspected transient collaborator change for playlist 'bzy i kosy' (2 -> 1)", "playlist"),
    ("* Getting detailed info for Spotify user ID '31nnv6eqt4qswvjhcnknimtxqife' ...", "id"),
    ("* Searching for users with 'martus' string ...", "username"),
])
def test_quoted_value_takes_its_colour_from_the_preceding_word(colored, line, part):
    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert colored[part] in result


# Verifies a change header colours the complete display name, including spaces and emoji
@pytest.mark.parametrize("line", [
    "* Playlists number changed for user martus \U0001f496 from 2 to 1 (-1)",
    "* Followers changed for user martus \U0001f496 while the total remained 98",
    "* User martus \U0001f496 has changed profile picture !",
])
def test_change_header_colours_the_complete_display_name(colored, line):
    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert f"{colored['username']}martus \U0001f496{monitor.ANSI_RESET}" in result


# Verifies the label word in "Spotify user ID" is not mistaken for a display name
def test_user_id_label_is_not_colored_as_a_name(colored):
    result = monitor._colorize_line("* Getting detailed info for Spotify user ID 'abc' ...")

    assert f"{colored['username']}ID{monitor.ANSI_RESET}" not in result


# Verifies a change report is not painted end to end, so every value it names keeps its own colour
@pytest.mark.parametrize("line", CHANGE_REPORT_LINES)
def test_change_reports_are_not_painted_end_to_end(colored, line):
    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert not result.startswith("\x1b")


# Verifies a whole-line style is only ever applied to lines that report a problem, never to a change report
@pytest.mark.parametrize("line, part", [("* Error: could not reach Spotify", "error"), ("Sending email notification to someone@example.com", "email"), ("Sending webhook notification", "webhook"), ("* Info: the token was refreshed", "info")])
def test_only_problem_lines_are_painted_end_to_end(colored, line, part):
    assert monitor._colorize_line(line).startswith(colored[part])


# Warning and signal lines mark their own opening word instead of being painted end to end, so a value
# inside them keeps the colour that says what it is
def test_a_warning_marks_its_opening_word_and_leaves_the_rest(colored):
    assert monitor._colorize_line("* Warning: something odd") == f"* {colored['warning']}Warning:{monitor.ANSI_RESET} something odd"


def test_a_signal_line_marks_the_signal_it_reports(colored):
    assert monitor._colorize_line("* Signal SIGUSR1 received") == f"* Signal {colored['signal']}SIGUSR1{monitor.ANSI_RESET} received"


# The playlist colour is the yellow the warning line used to paint over, so the name it reports was
# indistinguishable from the line around it
def test_a_warning_row_still_shows_the_playlist_inside_it(colored):
    rendered = monitor._colorize_line("* Warning: playlist 'My Mix' could not be read")

    assert f"{colored['playlist']}My Mix{monitor.ANSI_RESET}" in rendered
    assert not rendered.startswith(colored["warning"])


# A value drawn in the colour of the block enclosing it disappears
def test_a_block_style_never_hides_a_name(colored):
    for block in monitor.BLOCK_STYLE_PARTS:
        for name in monitor.NAME_STYLE_PARTS:
            assert colored[name] != colored[block], f"{name} is invisible inside a {block} line"


# Verifies every part the shipped theme offers is actually looked up somewhere, so the theme documents only
# colours a user can really change
def test_every_theme_part_is_used():
    source = Path(monitor.__file__).read_text(encoding="utf-8")
    looked_up = set(re.findall(r"""colorize\(\s*["\']([a-z_]+)["\']""", source))
    looked_up |= set(re.findall(r"""_apply_style_nested\([^,]+,\s*["\']([a-z_]+)["\']""", source))
    looked_up |= set(re.findall(r"""_COLOR_STYLES\.get\(["\']([a-z_]+)["\']""", source))
    looked_up |= set(re.findall(r"""(?:style_name|quoted_style|key) = ["\']([a-z_]+)["\']""", source))
    looked_up |= set(re.findall(r""",\s*["\']([a-z_]+)["\']\),?\s*$""", source, re.M))
    doctor_marks = re.search(r"_DOCTOR_MARK_STYLES = \{(.*?)\}", source, re.S)
    assert doctor_marks is not None
    looked_up |= set(re.findall(r""":\s*["\']([a-z_]+)["\']""", doctor_marks.group(1)))

    assert not set(monitor.DEFAULT_COLOR_THEME) - looked_up


# Verifies the reported playlist name stands out from the activity header that reports the change
def test_playlist_name_stands_out_in_a_change_header(colored):
    line = "* Playlist 'bzy i kosy': number of tracks changed from 22 to 23 (+1)"

    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert f"{colored['playlist']}bzy i kosy{monitor.ANSI_RESET}" in result


# Verifies the guided setup surface is coloured, not only the monitoring output. The install method decides
# every command shown afterwards, and the commands themselves are what the user has to copy
def test_setup_surface_is_coloured(colored, capsys, monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")

    monitor._wizard_print_setup_destinations("pip", Path("monitor.conf"), Path(".env"))
    monitor._wizard_print_command("Check setup before monitoring:", "spotify_profile_monitor --doctor <target>")
    output = capsys.readouterr().out

    assert f"Detected install method: {colored['username']}pip{monitor.ANSI_RESET}" in output
    assert f"{colored['section']}spotify_profile_monitor --doctor <target>{monitor.ANSI_RESET}" in output


# Verifies a wizard prompt and its menu are coloured so the question and the number to type stand out
def test_wizard_prompt_and_menu_are_coloured(colored, capsys, monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_input", lambda prompt: "1")

    monitor._wizard_ask_choice("Pick one", [("First", ""), ("Second", "")], default_index=1)
    output = capsys.readouterr().out

    assert f"{colored['username']}1{monitor.ANSI_RESET}. First" in output
    assert f"{colored['info']} (default){monitor.ANSI_RESET}" in output


# Verifies the Doctor report headings and verdict are coloured, matching the sibling monitors
def test_doctor_report_headings_are_coloured(colored):
    built = monitor.build_doctor_report(None, None, "none")
    report = monitor.render_doctor_sections(built) + monitor.render_doctor_summary(built.checks)

    assert f"{colored['header']}Doctor{monitor.ANSI_RESET}" in report
    assert f"{colored['header']}Summary{monitor.ANSI_RESET}" in report
    assert f"{colored['section']}Environment{monitor.ANSI_RESET}" in report
    assert monitor.ANSI_ESCAPE_RE.sub("", report).splitlines()[0] == "Doctor"


# Verifies recovery guidance reads as advice rather than inheriting the colour of the failure it explains
def test_recovery_guidance_uses_the_info_colour(colored):
    line = "To fix: Verify the --config-file path then retry"

    assert monitor._colorize_line(line).startswith(colored["info"])


# Verifies truncation measures what is displayed, so colour codes do not eat into the visible width
def test_truncation_measures_display_width_not_escape_sequences():
    pytest.importorskip("wcwidth")

    truncated = monitor.truncate_string_per_line("\x1b[31m0123456789ABCDEF\x1b[0m", 10)

    assert re.sub(r"\x1b\[[0-9;]*m", "", truncated) == "0123456789"


# Verifies a double-width character costs two columns, so a CJK title does not wrap past the limit
def test_truncation_counts_double_width_characters():
    pytest.importorskip("wcwidth")

    assert monitor.truncate_string_per_line("原神原神原神", 4) == "原神"


# Verifies each line is measured on its own rather than the whole message being cut at one offset
def test_truncation_applies_to_every_line():
    pytest.importorskip("wcwidth")

    assert monitor.truncate_string_per_line("abcdef\nabcdef", 3) == "abc\nabc"


# Verifies the TLS row colours its state word, the one setting whose off state weakens a security property
def test_the_tls_row_colours_its_state(colored):
    on_row = monitor._colorize_line("* TLS verification:             On")
    off_row = monitor._colorize_line("* TLS verification:             Off, server certificates are not checked")

    assert on_row == f"* TLS verification:             {colored['boolean_true']}On{monitor.ANSI_RESET}"
    assert off_row == f"* TLS verification:             {colored['boolean_false']}Off{monitor.ANSI_RESET}, server certificates are not checked"


HELP_SAMPLE = """usage: monitor [-h] [--config-file PATH] [TARGET]

positional arguments:
  TARGET                The target to monitor

Configuration & dotenv files:
  --config-file PATH    Path to a config file
  -m, --check-interval SECONDS
                        Time between checks (default: 60)

Examples:

Getting started:
  # Guided setup, see https://example.invalid/guide/
  python3 monitor.py --setup <target>

Guide: https://example.invalid/guide/
"""

HELP_SAMPLE_EPILOG = HELP_SAMPLE[HELP_SAMPLE.index("Examples:"):]


# Enables colour with the shipped theme and returns the escape sequence of every part
@pytest.fixture
def help_palette(monkeypatch):
    styles = {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", styles)
    return styles


# Returns the sample help screen with the help palette applied
@pytest.fixture
def colored_help(help_palette):
    return monitor.colorize_help_text(HELP_SAMPLE, HELP_SAMPLE_EPILOG)


# Verifies colouring changes no character of the screen, since argparse laid out its columns on the plain text
def test_the_coloured_help_keeps_the_plain_layout(colored_help):
    assert monitor.ANSI_ESCAPE_RE.sub("", colored_help) == HELP_SAMPLE


# Verifies the argument groups and the example tasks share one heading colour, the anchors the reader scans for
def test_the_help_headings_carry_the_heading_colour(help_palette, colored_help):
    for heading in ("positional arguments:", "Configuration & dotenv files:", "Examples:", "Getting started:"):
        assert f"{help_palette['help_heading']}{heading}{monitor.ANSI_RESET}" in colored_help


# Verifies an option name and the value it takes are coloured apart, in the usage block and in the option rows
def test_the_help_option_names_and_their_values_are_coloured_apart(help_palette, colored_help):
    option = f"{help_palette['help_option']}--config-file{monitor.ANSI_RESET}"
    metavar = f"{help_palette['help_metavar']}PATH{monitor.ANSI_RESET}"

    assert f"{option} {metavar}" in colored_help
    assert f"[{option} {metavar}]" in colored_help
    assert f"{help_palette['help_usage']}usage:{monitor.ANSI_RESET}" in colored_help
    assert f"{help_palette['help_metavar']}TARGET{monitor.ANSI_RESET}                The target to monitor" in colored_help


# Verifies the examples separate the comment from the command and mark the value the reader has to replace
def test_the_help_examples_mark_comments_commands_and_placeholders(help_palette, colored_help):
    assert f"{help_palette['help_comment']}  # Guided setup" in colored_help
    assert f"{help_palette['help_command']}  python3 monitor.py --setup" in colored_help
    assert f"{help_palette['help_placeholder']}<target>{monitor.ANSI_RESET}" in colored_help


# Verifies a default note is dimmed and a documentation link keeps the shared link colour
def test_the_help_default_notes_and_links_stay_secondary(help_palette, colored_help):
    assert f"{help_palette['help_default']}(default: 60){monitor.ANSI_RESET}" in colored_help
    assert f"{help_palette['link']}https://example.invalid/guide/{monitor.ANSI_RESET}" in colored_help


# Verifies the help screen stays plain while colour is switched off, so --no-color and NO_COLOR clear all of it
def test_the_help_palette_switches_off_with_colour():
    assert monitor.colorize_help_text(HELP_SAMPLE, HELP_SAMPLE_EPILOG) == HELP_SAMPLE


# Verifies the finished help screen reaches the terminal untouched, past the colouriser that paints monitoring output
def test_the_help_screen_is_not_repainted_by_the_monitoring_rules(help_palette):
    buffer = StringIO()
    parser = monitor.ColoredHelpParser(prog="monitor", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--config-file", metavar="PATH", help="Path to a config file")
    parser.print_help(monitor.TerminalStream(buffer))

    written = buffer.getvalue()
    assert written == parser.format_help()
    assert help_palette["help_option"] in written

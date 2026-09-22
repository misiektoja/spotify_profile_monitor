import contextlib
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
def test_chromium_profile_discovery(tmp_path, real_browser_profiles):
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


# Verifies every configured Chromium root is relative to the home directory, derived from the table so a root added
# there is covered without editing this test
def test_chromium_roots_are_relative_and_named_per_platform(tmp_path):
    for system_name, browsers in monitor.CHROMIUM_USER_DATA_DIRS.items():
        for browser, relative_paths in browsers.items():
            assert isinstance(relative_paths, tuple), f"{system_name}/{browser}"
            for relative_path in relative_paths:
                assert not Path(relative_path).is_absolute(), f"{system_name}/{browser}"
            resolved = monitor.get_chromium_user_data_dir(browser, system_name=system_name, home=tmp_path)
            assert resolved == tmp_path / relative_paths[0], f"{system_name}/{browser}"


# Verifies the first root that exists is used, so a packaged install is found while the conventional one is named
# when nothing exists at all
def test_chromium_packaged_roots_are_searched_in_order(tmp_path):
    browser = "chromium"
    relative_paths = monitor.CHROMIUM_USER_DATA_DIRS["Linux"][browser]
    assert len(relative_paths) > 1, "this test needs a browser with more than one candidate root"

    assert monitor.get_chromium_user_data_dir(browser, system_name="Linux", home=tmp_path) == tmp_path / relative_paths[0]

    packaged = tmp_path / relative_paths[-1]
    packaged.mkdir(parents=True)
    assert monitor.get_chromium_user_data_dir(browser, system_name="Linux", home=tmp_path) == packaged


# Verifies the packaged Linux trees are reachable, which a single root per browser made impossible
@pytest.mark.parametrize("browser", ["brave", "chromium"])
def test_chromium_linux_reaches_snap_and_flatpak_trees(browser):
    roots = monitor.CHROMIUM_USER_DATA_DIRS["Linux"][browser]

    assert any(root.startswith("snap/") for root in roots), browser
    assert any(root.startswith(".var/app/") for root in roots), browser


# Verifies a system with no known location resolves to no root rather than a wrong one
def test_chromium_unknown_platform_has_no_root(tmp_path):
    assert monitor.get_chromium_user_data_dir("chrome", system_name="Plan9", home=tmp_path) is None


# Verifies each keyring failure is attributed to the cause the user must actually fix. The strings are taken verbatim
# from the installed keyring backends and from pycookiecheat, several of which name neither the keyring nor the service
@pytest.mark.parametrize("error_text,expected", [
    ("Failed to unlock the collection!", "Unlock the keyring"),
    ("Failed to unlock the item!", "Unlock the keyring"),
    ("Can't open a session to the secret service", "Unlock the keyring"),
    ("Failed to unlock the keyring!", "Unlock the keyring"),
    ("The Secret Service daemon is neither running nor activatable through D-Bus", "Unlock the keyring"),
    ("Can't get password from keychain: Keychain Access Denied", "Unlock the keyring"),
    ("Could not find a password for the pair (Chrome Safe Storage, Chrome)", "Unlock the keyring"),
    ("No recommended backend was available. Install a recommended 3rd party backend package.", "Install one such as"),
    ("Invalid padding, InvalidTag raised during decrypt", "Could not decrypt"),
])
def test_a_keyring_failure_names_the_cause_to_fix(error_text, expected):
    message = monitor._safe_chromium_cookie_error("chrome", RuntimeError(error_text))

    assert expected in message
    # The generic fallback sends the user to sign in again, which is the wrong fix for every case above
    assert "Confirm Spotify is signed in" not in message


# Verifies a missing keyring backend is not reported as a locked one, since one must be installed and the other unlocked
def test_a_missing_keyring_backend_is_not_reported_as_a_locked_one():
    message = monitor._safe_chromium_cookie_error("chrome", RuntimeError("No recommended backend was available."))

    assert "Install one such as" in message
    assert "Unlock the keyring" not in message


# Verifies an empty Chromium listing names which of its causes applies, since each needs a different fix
def test_chromium_empty_listing_separates_its_causes(tmp_path):
    absent = tmp_path / "not-installed"
    assert "Install Chrome" in monitor.chromium_no_profiles_message("chrome", user_data_dir=absent)

    bare_root = tmp_path / "installed"
    bare_root.mkdir()
    assert "Open Chrome once to create a profile" in monitor.chromium_no_profiles_message("chrome", user_data_dir=bare_root)

    with_profile = tmp_path / "with-profile"
    (with_profile / "Default").mkdir(parents=True)
    fresh = monitor.chromium_no_profiles_message("chrome", user_data_dir=with_profile)
    assert "none of its profiles (Default) holds a cookie database yet" in fresh
    # An installed browser must never be reported as one the user has to install
    assert "Install Chrome" not in fresh

    assert "no known Chrome profile location" in monitor.chromium_no_profiles_message("chrome", system_name="Plan9", home=tmp_path)


# Verifies an empty Firefox listing separates the same causes rather than repeating one message
def test_firefox_empty_listing_separates_its_causes(tmp_path):
    assert "no known Firefox profile location" in monitor.firefox_no_profiles_message(system_name="Plan9", home=tmp_path)

    assert "Install Firefox" in monitor.firefox_no_profiles_message(system_name="Linux", home=tmp_path / "absent")

    (tmp_path / ".mozilla/firefox").mkdir(parents=True)
    installed = monitor.firefox_no_profiles_message(system_name="Linux", home=tmp_path)
    assert "holds a cookie database yet" in installed
    assert "Install Firefox" not in installed


# Verifies the import surfaces the specific reason rather than the generic one when no profile can be offered
def test_the_import_reports_the_specific_empty_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "discover_chromium_profiles", lambda *arguments, **keywords: [])
    monkeypatch.setattr(monitor, "chromium_no_profiles_message", lambda *arguments, **keywords: "the specific reason")

    with pytest.raises(monitor.BrowserCookieImportError, match="the specific reason"):
        monitor.run_browser_cookie_import(browser="chrome", env_file=tmp_path / ".env", interactive=False)


# Builds three interchangeable profile records for the picker tests
def picker_profiles(count=3, cookie_root="/p"):
    return [{"dir": f"p{index}", "name": f"name{index}", "cookie_file": f"{cookie_root}/p{index}/cookies.sqlite", "install": ""} for index in range(1, count + 1)]


# Verifies an invalid answer re-asks instead of ending the import, so a typo does not mean starting over
@pytest.mark.parametrize("answers,expected", [(["tow", "2"], "p2"), (["", "1"], "p1"), (["9", "3"], "p3"), (["-1", "2"], "p2"), (["1.5", "1"], "p1"), (["  2  "], "p2")])
def test_the_picker_re_asks_on_invalid_input(answers, expected, monkeypatch):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: None)
    supplied = iter(answers)

    chosen = monitor.select_browser_profile(picker_profiles(), "firefox", interactive=True, input_func=lambda prompt: next(supplied))

    assert chosen["dir"] == expected


# Verifies a negative number is refused rather than indexing backwards from the end of the list
def test_the_picker_never_indexes_backwards(monkeypatch):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: None)
    supplied = iter(["-1", "-3", "1"])

    chosen = monitor.select_browser_profile(picker_profiles(), "firefox", interactive=True, input_func=lambda prompt: next(supplied))

    assert chosen["dir"] == "p1"


# Verifies the documented cancel answer and an interrupted prompt both end the import cleanly
@pytest.mark.parametrize("behaviour", ["zero", "eof", "interrupt"])
def test_the_picker_cancels_without_a_traceback(behaviour, monkeypatch):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: None)
    supplied = iter(["0"])

    def answer(prompt):
        if behaviour == "eof":
            raise EOFError
        if behaviour == "interrupt":
            raise KeyboardInterrupt
        return next(supplied)

    with pytest.raises(monitor.BrowserCookieImportError, match="cancelled"):
        monitor.select_browser_profile(picker_profiles(), "firefox", interactive=True, input_func=answer)


# Verifies the one profile holding a current login is marked and preselected, so Enter accepts it
def test_the_picker_marks_and_preselects_the_only_live_profile(monkeypatch, capsys):
    profiles = picker_profiles()
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda cookie_file, **keywords: cookie_file.endswith("p2/cookies.sqlite"))
    prompts = []
    supplied = iter([""])

    chosen = monitor.select_browser_profile(profiles, "firefox", interactive=True, input_func=lambda prompt: (prompts.append(prompt), next(supplied))[1])

    assert chosen["dir"] == "p2"
    listing = capsys.readouterr().out
    assert "* marks a profile holding a current Spotify login" in listing
    assert "* name2" in listing and "(default)" in listing
    # Only the profile worth choosing carries the mark
    assert listing.count("*") == 2
    assert "Enter for default" in prompts[0]


# Verifies nothing is marked or preselected when no profile holds a current login
def test_the_picker_marks_nothing_when_no_profile_is_live(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: False)
    prompts = []
    supplied = iter(["2"])

    chosen = monitor.select_browser_profile(picker_profiles(), "firefox", interactive=True, input_func=lambda prompt: (prompts.append(prompt), next(supplied))[1])

    assert chosen["dir"] == "p2"
    assert "marks a profile holding" not in capsys.readouterr().out
    assert "Enter for default" not in prompts[0]


# Verifies no default is offered when several profiles qualify, since there is no basis to choose between them
def test_the_picker_preselects_nothing_when_several_are_live(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: True)
    prompts = []
    supplied = iter(["3"])

    chosen = monitor.select_browser_profile(picker_profiles(), "firefox", interactive=True, input_func=lambda prompt: (prompts.append(prompt), next(supplied))[1])

    assert chosen["dir"] == "p3"
    assert "(default)" not in capsys.readouterr().out
    assert "Enter for default" not in prompts[0]


# Verifies a database that could not be read is left unmarked rather than reported as signed out
def test_an_unreadable_profile_is_left_unmarked(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: None)
    supplied = iter(["1"])

    monitor.select_browser_profile(picker_profiles(), "firefox", interactive=True, input_func=lambda prompt: next(supplied))

    listing = capsys.readouterr().out
    assert "marks a profile holding" not in listing
    assert "signed out" not in listing


# Verifies the only profile is warned about when it holds no current login, since there is no alternative to offer
def test_a_single_signed_out_profile_is_warned_about(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: False)

    chosen = monitor.select_browser_profile(picker_profiles(count=1), "firefox", interactive=True, input_func=lambda prompt: "")

    assert chosen["dir"] == "p1"
    assert "holds no current Spotify login" in capsys.readouterr().out


# Verifies an unreadable single profile is not called signed out, which the import cannot know
def test_a_single_unreadable_profile_is_not_warned_about(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: None)

    monitor.select_browser_profile(picker_profiles(count=1), "firefox", interactive=True, input_func=lambda prompt: "")

    assert "holds no current Spotify login" not in capsys.readouterr().out


# Verifies two installs sharing a profile directory name are told apart, and that the advice given can be followed.
# Naming the directory cannot resolve it, since the directory is what they share
def test_a_directory_name_shared_by_two_installs_names_the_cookie_file():
    duplicate = [{"dir": "Default", "name": "Person 1", "cookie_file": "/a/Default/Cookies", "install": ""}, {"dir": "Default", "name": "Person 1", "cookie_file": "/b/Default/Cookies", "install": "Snap"}]

    with pytest.raises(monitor.BrowserCookieImportError) as failure:
        monitor.select_browser_profile(duplicate, "chrome", requested_profile="Default", interactive=False)

    message = str(failure.value)
    assert "--cookie-file PATH" in message
    assert "Pass one profile directory" not in message
    # The two choices must be distinguishable in the listing, which is what the packaging tag is for
    assert "[Snap]" in message


# Verifies the packaging a profile came from is recognized, since Snap, Flatpak, Microsoft Store and
# distribution trees share names. A Windows path is classified from any host, so the check never reads os.sep
@pytest.mark.parametrize("path,expected", [("/home/u/.config/chromium/Default", ""), ("/home/u/snap/chromium/common/chromium/Default", "Snap"), ("/home/u/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Default", "Flatpak"), ("/home/u/.mozilla/firefox/abc.default", ""), (r"C:\Users\u\AppData\Roaming\Mozilla\Firefox\Profiles\abc.default", ""), (r"C:\Users\u\AppData\Local\Packages\Mozilla.Firefox_n80bbvh6b1yt2\LocalCache\Roaming\Mozilla\Firefox\Profiles\abc.default", "Microsoft Store")])
def test_the_packaging_of_a_profile_tree_is_recognized(path, expected):
    assert monitor.packaging_label(Path(path)) == expected


# Verifies a redirected application-data directory does not hide the home-relative root, and that the two
# collapse into one entry when they name the same directory
@pytest.mark.parametrize("appdata,expected_roots", [(None, ["AppData/Roaming/Mozilla/Firefox"]), ("AppData/Roaming", ["AppData/Roaming/Mozilla/Firefox"]), ("Redirected", ["Redirected/Mozilla/Firefox", "AppData/Roaming/Mozilla/Firefox"])])
def test_the_windows_roaming_root_covers_a_redirection(tmp_path, appdata, expected_roots):
    environ = {"APPDATA": str(tmp_path / appdata)} if appdata else {}

    roots = monitor._firefox_profile_roots(system_name="Windows", home=tmp_path, environ=environ)

    assert roots == [tmp_path / relative for relative in expected_roots]


# Verifies the Microsoft Store package is searched, since its profiles never appear under the roaming root
def test_the_windows_store_package_is_searched(tmp_path, real_browser_profiles):
    store_root = tmp_path / "AppData/Local/Packages/Mozilla.Firefox_n80bbvh6b1yt2/LocalCache/Roaming/Mozilla/Firefox"
    (store_root / "Profiles/store.default-release").mkdir(parents=True)
    create_firefox_database(store_root / "Profiles/store.default-release/cookies.sqlite", [("spotify.com", "sp_dc", "cookie", 4102444800, 10)])

    profiles = monitor.discover_firefox_profiles(system_name="Windows", home=tmp_path, environ={})

    assert [(profile["dir"], profile["install"]) for profile in profiles] == [("store.default-release", "Microsoft Store")]


# Verifies a Store profile is told apart from a regular one, since both installs create a default-release
def test_a_store_profile_is_told_apart_from_a_regular_one(tmp_path, real_browser_profiles):
    for root in ("AppData/Roaming/Mozilla/Firefox", "AppData/Local/Packages/Mozilla.Firefox_n80bbvh6b1yt2/LocalCache/Roaming/Mozilla/Firefox"):
        profile_dir = tmp_path / root / "Profiles/abcd1234.default-release"
        profile_dir.mkdir(parents=True)
        create_firefox_database(profile_dir / "cookies.sqlite", [])

    # The listing is ordered by name, directory then cookie file, so the package under AppData/Local sorts first
    profiles = monitor.discover_firefox_profiles(system_name="Windows", home=tmp_path, environ={})
    assert [profile["install"] for profile in profiles] == ["Microsoft Store", ""]

    with pytest.raises(monitor.BrowserCookieImportError) as failure:
        monitor.select_browser_profile(profiles, "firefox", requested_profile="abcd1234.default-release", interactive=False)
    assert "[Microsoft Store]" in str(failure.value)


# Verifies the live-login probe answers on both cookie schemas, neither of which needs a decryption key to read the
# cookie name, host and expiry
@pytest.mark.parametrize("firefox", [True, False])
def test_the_live_cookie_probe_reads_both_schemas(tmp_path, firefox):
    now = 1790000000.0
    cookie_file = tmp_path / ("cookies.sqlite" if firefox else "Cookies")
    with contextlib.closing(sqlite3.connect(cookie_file)) as connection:
        if firefox:
            connection.execute("CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT, expiry INTEGER, lastAccessed INTEGER)")
            connection.execute("INSERT INTO moz_cookies VALUES ('.spotify.com', 'sp_dc', 'v', ?, 1)", (int((now + 86400) * 1000),))
        else:
            connection.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, encrypted_value BLOB, expires_utc INTEGER)")
            connection.execute("INSERT INTO cookies VALUES ('.spotify.com', 'sp_dc', X'00', ?)", (int((now + 86400 + monitor.CHROMIUM_EPOCH_OFFSET_SECONDS) * 1_000_000),))
        connection.commit()

    assert monitor.profile_has_live_spotify_cookie(cookie_file, firefox=firefox, now=now) is True
    assert monitor.profile_has_live_spotify_cookie(cookie_file, firefox=firefox, now=now + 86400 * 2) is False


# Verifies a database the probe cannot read answers "unknown" rather than "signed out"
@pytest.mark.parametrize("content", [b"not a database", b""])
def test_the_live_cookie_probe_returns_unknown_for_an_unreadable_database(tmp_path, content):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.write_bytes(content)

    assert monitor.profile_has_live_spotify_cookie(cookie_file, firefox=True) is None


# Verifies a missing database answers "unknown" as well, since absence is not evidence of being signed out
def test_the_live_cookie_probe_returns_unknown_for_a_missing_database(tmp_path):
    assert monitor.profile_has_live_spotify_cookie(tmp_path / "absent.sqlite", firefox=True) is None


# Verifies the suite never enumerates the browser profiles of whoever runs it. Without the shared stub the listing
# differs per machine, costs a SQLite open per profile and makes a failure depend on which browsers are installed
def test_browser_profile_discovery_is_stubbed_by_default(tmp_path, monkeypatch):
    firefox_root = tmp_path / "firefox"
    (firefox_root / "abc.default").mkdir(parents=True)
    (firefox_root / "abc.default" / "cookies.sqlite").touch()
    chromium_root = tmp_path / "chromium"
    (chromium_root / "Default").mkdir(parents=True)
    (chromium_root / "Default" / "Cookies").touch()
    monkeypatch.setattr(monitor, "_firefox_profile_roots", lambda *arguments, **keywords: [firefox_root])
    monkeypatch.setattr(monitor, "get_chromium_user_data_dir", lambda *arguments, **keywords: chromium_root)

    assert monitor.discover_firefox_profiles() == []
    assert monitor.discover_chromium_profiles("chrome") == []


# Verifies the real enumerators are one fixture away, so stubbing them by default does not leave them untested
def test_the_real_enumerators_are_available_on_request(tmp_path, monkeypatch, real_browser_profiles):
    firefox_root = tmp_path / "firefox"
    (firefox_root / "abc.default").mkdir(parents=True)
    (firefox_root / "abc.default" / "cookies.sqlite").touch()
    chromium_root = tmp_path / "chromium"
    (chromium_root / "Default").mkdir(parents=True)
    (chromium_root / "Default" / "Cookies").touch()
    monkeypatch.setattr(monitor, "_firefox_profile_roots", lambda *arguments, **keywords: [firefox_root])
    monkeypatch.setattr(monitor, "get_chromium_user_data_dir", lambda *arguments, **keywords: chromium_root)

    assert [profile["dir"] for profile in monitor.discover_firefox_profiles()] == ["abc.default"]
    assert [profile["dir"] for profile in monitor.discover_chromium_profiles("chrome")] == ["Default"]

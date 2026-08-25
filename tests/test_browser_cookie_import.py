import json
import sqlite3
import sys
import types
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

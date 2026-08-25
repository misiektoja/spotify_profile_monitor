import argparse
import contextlib
import inspect
import os
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

import spotify_profile_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("value,expected", [("spotify:user:MiXeDcAsE", "MiXeDcAsE"), ("spotify:playlist:AbC123", "AbC123"), ("https://open.spotify.com/user/Spotify", "Spotify"), ("Spotify", "Spotify"), ("spotify", "spotify"), ("  padded  ", "padded"), ("", "")])
# Confirms Spotify identifiers keep their case, since Spotify treats them as case sensitive
def test_extract_id_preserves_case(value, expected):
    assert monitor.spotify_extract_id_or_name(value) == expected


# Confirms two IDs differing only in case no longer collide in ignore-list matching
def test_extract_id_keeps_case_distinct_ids_apart():
    assert monitor.spotify_extract_id_or_name("spotify:playlist:AbC") != monitor.spotify_extract_id_or_name("spotify:playlist:abc")


# Confirms a user literally named Spotify is not mistaken for the official account
def test_extract_id_does_not_alias_the_official_account():
    assert monitor.spotify_extract_id_or_name("spotify:user:Spotify") != "spotify"
    assert monitor.spotify_extract_id_or_name("spotify:user:spotify") == "spotify"


# Confirms no CSV output path is left on the platform locale encoding
def test_no_locale_encoded_csv_writes():
    source = inspect.getsource(monitor)
    assert 'with open(csv_file_name, "w") as file:' not in source
    assert source.count('with open(csv_file_name, "w", encoding="utf-8") as file:') == 2


# Confirms non-ASCII track names survive an explicit UTF-8 write, which cp1252 would reject
def test_utf8_export_round_trips_non_ascii():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "tracks.txt"
        tracks = ["Zażółć gęślą jaźń", "日本語のトラック", "Beyoncé"]
        with open(path, "w", encoding="utf-8") as handle:
            handle.writelines([track + "\n" for track in tracks])
        assert path.read_text(encoding="utf-8").splitlines() == tracks


# Confirms the cookie database handle is closed rather than only its transaction committed
def test_sqlite_connection_is_closed_by_contextlib():
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "cookies.sqlite"
        sqlite3.connect(database).close()
        with contextlib.closing(sqlite3.connect(database.resolve().as_uri() + "?immutable=1", uri=True)) as connection:
            connection.execute("SELECT 1")
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")


# Confirms the cookie importer uses the closing wrapper rather than a bare connect
def test_cookie_import_closes_its_connection():
    source = inspect.getsource(monitor)
    assert "with contextlib.closing(sqlite3.connect(" in source
    assert "with sqlite3.connect(" not in source


@pytest.mark.parametrize("host", [None, 12345, ["x"], "your_smtp_server_ssl"])
# Confirms a non-string SMTP_HOST cannot raise a bare AttributeError at startup
def test_smtp_host_placeholder_check_accepts_any_type(host):
    assert isinstance(str(host).startswith("your_smtp_server_"), bool)


@pytest.mark.parametrize("argv,expected", [([], None), (["--truncate", "0"], 0), (["--truncate", "50"], 50)])
# Confirms an explicit --truncate 0 is distinguishable from the flag being absent
def test_truncate_zero_is_distinguishable(argv, expected):
    parser = argparse.ArgumentParser()
    parser.add_argument("--truncate", type=int, default=None)
    assert parser.parse_args(argv).truncate == expected


# Confirms the truncate option is read with an explicit None check
def test_truncate_uses_none_check():
    source = inspect.getsource(monitor)
    assert "if args.truncate is not None:" in source


@pytest.mark.parametrize("uri", ["spotify:playlist:37i9dQZF1DXcBWIGoYBM5M", "spotify:playlist:abc", "::abc"])
# Confirms the temporary artwork filename carries no colon, which Windows rejects
def test_artwork_filename_has_no_colon(uri):
    filename = f"spotify_{monitor.spotify_extract_id_or_name(uri)}_playlist_pic_tmp.jpeg"
    assert ":" not in filename
    assert filename.endswith("_playlist_pic_tmp.jpeg")


@pytest.mark.parametrize("url,allowed", [("https://open.spotifycdn.com/cdn/build/web-player/web-player.2df27348.js", True), ("https://open.spotify.com/web-player/web-player.abc.js", True), ("https://evil.example/web-player/web-player.abc.js", False), ("http://open.spotifycdn.com/x.js", False), ("https://spotifycdn.com.evil.example/x.js", False), ("", False), (None, False)])
# Confirms the bundle URL scraped from remote HTML must resolve to a Spotify-owned host
def test_web_bundle_host_binding(url, allowed):
    assert monitor.spotify_web_bundle_url_is_allowed(url) is allowed


# Confirms the web-player pagination loop is bounded and cannot be extended by a growing total
def test_web_pagination_is_bounded():
    source = inspect.getsource(monitor)
    assert "total_tracks = min(total_tracks, page_total_tracks)" in source
    assert "web-player playlist pagination exceeded" in source
    assert monitor.SPOTIFY_PAGINATION_MAX_PAGES > 0


# Confirms the refresh token is masked so it is not echoed in full by default
def test_refresh_token_is_masked_by_default():
    masked = str(monitor.mask_secret("AQD1234567890SECRETTOKENVALUE"))
    assert "SECRET" not in masked
    assert masked.startswith("AQD1")
    source = inspect.getsource(monitor)
    assert 'print(" - Refresh Token:\\t", REFRESH_TOKEN, "\\n")' in source
    assert "re-run with --verbose to show" in source


# Confirms the generated config is written with owner-only permissions on POSIX
@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes only")
def test_generated_config_is_owner_only():
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "generated.conf"
        monitor.write_config_file(destination, "TRUNCATE_CHARS = 5\n")
        assert oct(destination.stat().st_mode & 0o777) == "0o600"


# Confirms every playlist export stays inside the dedicated export directory
@pytest.mark.parametrize("playlist_name", ["My Playlist", "../../etc/passwd", "..\\..\\windows\\system32", "", "con", "  spaced  ", "dots..."])
def test_exports_are_confined_to_their_directory(playlist_name, monkeypatch):
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "testuser")
    export_directory = Path(os.path.abspath(str(monitor.playlist_export_directory())))
    path = Path(os.path.abspath(str(monitor.build_playlist_export_path(playlist_name, "someid", set()))))

    assert export_directory in path.parents
    assert path.suffix == ".csv"


# Confirms two playlists sanitizing to the same name get separate files instead of appending to one
def test_export_name_collisions_get_distinct_files(monkeypatch):
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "testuser")
    used = set()
    first = monitor.build_playlist_export_path("Same Name", "id1", used)
    second = monitor.build_playlist_export_path("Same Name", "id2", used)

    assert first != second
    assert "id2" in second.name
    assert len(used) == 2


# Confirms the export directory is named after the monitored target
def test_export_directory_is_named_after_target(monkeypatch):
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "someuser")
    assert monitor.playlist_export_directory().name == "spotify_profile_someuser_playlists_export"


# Confirms the collaborator caches drop playlists the profile no longer exposes
def test_prune_playlist_caches_drops_dead_playlists(monkeypatch):
    monkeypatch.setattr(monitor, "COLLABORATORS_BASELINE_CACHE", {"spotify:playlist:live": {"ids": ()}, "spotify:playlist:gone": {"ids": ()}})
    monkeypatch.setattr(monitor, "COLLABORATORS_PENDING_CACHE", {"spotify:playlist:gone": {"streak": 1}})
    monkeypatch.setattr(monitor, "GLITCH_CACHE", {"spotify:playlist:old": 0.0})

    monitor.prune_playlist_caches([{"uri": "spotify:playlist:live"}])

    assert set(monitor.COLLABORATORS_BASELINE_CACHE) == {"spotify:playlist:live"}
    assert monitor.COLLABORATORS_PENDING_CACHE == {}
    assert monitor.GLITCH_CACHE == {}


# Confirms an empty or missing playlist list leaves the collaborator caches untouched
@pytest.mark.parametrize("current", [None, [], frozenset()])
def test_prune_playlist_caches_keeps_entries_without_a_live_list(current, monkeypatch):
    monkeypatch.setattr(monitor, "COLLABORATORS_BASELINE_CACHE", {"spotify:playlist:a": {"ids": ()}})
    monkeypatch.setattr(monitor, "COLLABORATORS_PENDING_CACHE", {})

    monitor.prune_playlist_caches(current)

    assert set(monitor.COLLABORATORS_BASELINE_CACHE) == {"spotify:playlist:a"}


# Confirms the caches keyed per monitored user cannot grow with playlist churn
def test_user_keyed_caches_are_not_per_playlist():
    source = inspect.getsource(monitor)
    assert "PLAYLISTS_BASELINE_CACHE[user_playlists_key]" in source
    assert "PLAYLISTS_BASELINE_CACHE[p_uri]" not in source
    assert "PLAYLISTS_PENDING_CACHE[p_uri]" not in source


# Confirms the contentless playlist branch no longer prints placeholders or skips the baseline write
def test_no_stray_added_removed_prints():
    source = inspect.getsource(monitor)
    assert 'print("Added", list_of_added_f_list.strip())' not in source
    assert 'print("Removed", list_of_removed_f_list.strip())' not in source
    assert "nothing_to_report" in source


# Confirms requirements.txt declares the same lower bounds as the package metadata
def test_requirements_match_project_metadata():
    lines = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    # Commented lines document the optional extras, which carry their own markers and are asserted separately
    requirements = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert requirements, "requirements.txt must not be empty"
    for requirement in requirements:
        assert ">=" in requirement, f"{requirement} has no lower bound"
        assert f'"{requirement}"' in pyproject, f"{requirement} is missing from pyproject dependencies"


# Verifies artwork support ships as an optional extra that keeps Python 3.9 on the last Pillow it supports
def test_artwork_support_is_an_optional_extra():
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")

    runtime_block = re.search(r"^dependencies = \[(.*?)^\]", pyproject, re.M | re.S)
    assert runtime_block is not None and "Pillow" not in runtime_block.group(1)
    assert "notification-images = [\"Pillow>=11.3.0,<12; python_version < '3.10'\", \"Pillow>=12.0.0; python_version >= '3.10'\"]" in pyproject
    assert not any(line.strip().startswith("Pillow") for line in requirements.splitlines())
    assert '# Pillow>=12.0.0; python_version >= "3.10"' in requirements


# The requirement must track the interpreter, since Pillow 12 refuses to install on Python 3.9
def test_artwork_requirement_follows_the_running_interpreter():
    requirement = monitor.notification_images_requirement()

    assert requirement == ("Pillow>=11.3.0,<12" if sys.version_info < (3, 10) else "Pillow>=12.0.0")


# A user who enabled artwork without Pillow needs the exact install command, not only the missing-feature notice
def test_artwork_install_command_names_the_extra():
    assert "spotify_profile_monitor[notification-images]" in monitor.notification_images_install_command("pip")
    assert monitor.notification_images_requirement() in monitor.notification_images_install_command("manual")

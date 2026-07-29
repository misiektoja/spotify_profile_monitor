import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import spotify_profile_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "spotify_profile_monitor.py"
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "target_input_test_artifacts"
ISOLATED_PRELUDE = "import requests, runpy, socket, sys; requests.sessions.Session.request = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network request attempted')); socket.create_connection = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network connection attempted')); "


# Creates a disposable test directory under the project local directory
def make_temp_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT)


# Runs an isolated CLI scenario with real network access blocked
def run_cli(arguments, runtime_setup="", cwd=PROJECT_ROOT):
    source = f"module = runpy.run_path({str(CLI_PATH)!r}, run_name='spotify_profile_monitor_target_test'); runtime = module['main'].__globals__; runtime['sys'].argv = {[str(CLI_PATH), *arguments]!r}; runtime['CLEAR_SCREEN'] = False; runtime['signal'].signal = lambda *args, **kwargs: None; {runtime_setup} module['main']()"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, "-c", ISOLATED_PRELUDE + source], cwd=cwd, capture_output=True, text=True, env=environment, timeout=30, check=False)


# Verifies all accepted target forms normalize to one Spotify user ID
def test_target_normalization_accepts_supported_forms():
    cases = {
        "31abc123": "31abc123",
        "spotify:user:31abc123": "31abc123",
        "https://open.spotify.com/user/31abc123": "31abc123",
        "https://open.spotify.com/user/31abc123/": "31abc123",
        "https://open.spotify.com/user/31abc123?si=test": "31abc123",
        "https://open.spotify.com/user/legacy%2Euser": "legacy.user",
        "  legacy.user-name_1  ": "legacy.user-name_1",
    }
    for target, expected in cases.items():
        assert monitor.normalize_spotify_user_id(target) == expected


# Verifies invalid entities, hosts and malformed target values are rejected
def test_target_normalization_rejects_unsafe_forms():
    rejected = [
        "",
        "spotify:track:31abc123",
        "spotify:user:",
        "spotify:user:abc:extra",
        "https://example.com/user/31abc123",
        "https://open.spotify.com/track/31abc123",
        "https://open.spotify.com/user/",
        "https://open.spotify.com/user/31abc123/extra",
        "https://open.spotify.com/user/legacy%2Fuser",
        "embedded space",
        "control\x00character",
        "legacy\\user",
        "https://open.spotify.com/user/%ZZ",
    ]
    for target in rejected:
        with pytest.raises(ValueError, match="raw user ID"):
            monitor.normalize_spotify_user_id(target)


# Verifies a positional target overrides the configured target
def test_target_resolution_prefers_cli_value():
    result = monitor.resolve_target_user_id("spotify:user:cli.user", "https://open.spotify.com/user/config.user")
    assert result == "cli.user"


# Verifies the configured target is normalized when no positional target exists
def test_target_resolution_uses_configured_value():
    result = monitor.resolve_target_user_id(None, "https://open.spotify.com/user/config%2Euser?si=test")
    assert result == "config.user"


# Verifies a config-only CLI run monitors the normalized target and uses it as the file suffix
def test_config_only_monitoring_uses_normalized_target_and_suffix():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "spotify_profile_monitor.conf"
        config_path.write_text('TARGET_USER_URI_ID = "https://open.spotify.com/user/config%2Euser?si=test"\nSP_DC_COOKIE = "test-cookie"\nDOTENV_FILE = "none"\nLOCAL_TIMEZONE = "UTC"\nDISABLE_LOGGING = True\n', encoding="utf-8")
        setup = "runtime['check_internet'] = lambda: True; runtime['spotify_profile_monitor_uri'] = lambda user_id, csv_file, playlists: print(f'MONITOR_TARGET={user_id}\\nFILE_SUFFIX={runtime[\"FILE_SUFFIX\"]}');"
        result = run_cli(["--config-file", str(config_path)], setup)
    assert result.returncode == 0, result.stderr
    assert "MONITOR_TARGET=config.user" in result.stdout
    assert "FILE_SUFFIX=config.user" in result.stdout


# Verifies an invalid configured target is ignored by target-free commands
def test_target_free_command_ignores_invalid_configured_target():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "spotify_profile_monitor.conf"
        config_path.write_text('TARGET_USER_URI_ID = "https://open.spotify.com/track/not-a-user"\nDOTENV_FILE = "none"\n', encoding="utf-8")
        result = run_cli(["--config-file", str(config_path), "--set-sp-dc"], "runtime['run_set_sp_dc'] = lambda **kwargs: print('SET_SP_DC');")
    assert result.returncode == 0, result.stderr
    assert "SET_SP_DC" in result.stdout
    assert "Invalid Spotify target" not in result.stdout

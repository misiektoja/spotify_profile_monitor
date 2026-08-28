import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import spotify_profile_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "spotify_profile_monitor.py"
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "config_effect_test_artifacts"
ISOLATED_PRELUDE = "import requests, runpy, socket, sys; requests.sessions.Session.request = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network request attempted')); socket.create_connection = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network connection attempted')); "

# Records what the startup connectivity check actually resolved, then reports the interval-derived
# values the monitor loop will use. Both are read after the config file and dotenv have been applied
PROBE_SETUP = (
    "runtime['req'].get = lambda url, **kwargs: print(f'CONNECTIVITY_URL={url}') or print(f'CONNECTIVITY_TIMEOUT={kwargs[\"timeout\"]}') or print(f'CONNECTIVITY_VERIFY={kwargs[\"verify\"]}') or type('Response', (), {'status_code': 200})(); "
    "runtime['urllib3'].disable_warnings = lambda *args, **kwargs: print('INSECURE_WARNINGS_DISABLED'); "
    "runtime['spotify_profile_monitor_uri'] = lambda user_id, csv_file, playlists: print(f'CHECK_INTERVAL={runtime[\"SPOTIFY_CHECK_INTERVAL\"]}') or print(f'LIVENESS_COUNTER={runtime[\"LIVENESS_CHECK_COUNTER\"]}') or print(f'CACHE_TTL={runtime[\"PLAYLIST_INFO_CACHE_TTL\"]}'); "
)
DIAGNOSTIC_PROBE_SETUP = PROBE_SETUP + "runtime['spotify_profile_monitor_uri'] = lambda user_id, csv_file, playlists: print(f'EFFECTIVE_DEBUG={runtime[\"DEBUG_MODE\"]}') or print(f'EFFECTIVE_VERBOSE={runtime[\"VERBOSE_MODE\"]}'); "


# Creates a disposable test directory under the project local directory
def make_temp_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT)


# Runs an isolated CLI scenario with real network access blocked
def run_cli(arguments, runtime_setup="", cwd=PROJECT_ROOT):
    source = f"module = runpy.run_path({str(CLI_PATH)!r}, run_name='spotify_profile_monitor_config_test'); runtime = module['main'].__globals__; runtime['sys'].argv = {[str(CLI_PATH), *arguments]!r}; runtime['CLEAR_SCREEN'] = False; runtime['signal'].signal = lambda *args, **kwargs: None; {runtime_setup} module['main']()"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, "-c", ISOLATED_PRELUDE + source], cwd=cwd, capture_output=True, text=True, env=environment, timeout=60, check=False)


# Writes one config file carrying the supplied settings plus the minimum needed to reach monitoring
def write_config(directory_name, settings):
    config_path = Path(directory_name) / "spotify_profile_monitor.conf"
    baseline = 'TARGET_USER_URI_ID = "config.user"\nSP_DC_COOKIE = "test-cookie"\nDOTENV_FILE = "none"\nLOCAL_TIMEZONE = "UTC"\nDISABLE_LOGGING = True\n'
    config_path.write_text(baseline + settings, encoding="utf-8")
    return config_path


# Reads one KEY=value line out of a captured CLI run
def probe_value(output, key):
    for line in output.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    raise AssertionError(f"{key} was never reported\n{output}")


# Confirms a config-file check interval rescales the liveness cadence and the playlist cache lifetime
def test_config_file_check_interval_rescales_derived_values():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_CHECK_INTERVAL = 300\nLIVENESS_CHECK_INTERVAL = 43200\n")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CHECK_INTERVAL") == "300"
    assert float(probe_value(result.stdout, "LIVENESS_COUNTER")) == 144.0, "the liveness cadence must follow the configured interval, not the built-in default"


# Confirms a slow config-file poll widens the playlist cache instead of expiring between every check
def test_config_file_slow_poll_widens_the_playlist_cache():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_CHECK_INTERVAL = 86400\n")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert float(probe_value(result.stdout, "CACHE_TTL")) == 172800.0, "a poll slower than the cache lifetime must widen the cache"


# Confirms a command-line interval still wins over the config file and rescales the same values
def test_command_line_interval_overrides_the_config_file():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_CHECK_INTERVAL = 300\nLIVENESS_CHECK_INTERVAL = 43200\n")
        result = run_cli(["--config-file", str(config_path), "--check-interval", "600"], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CHECK_INTERVAL") == "600"
    assert float(probe_value(result.stdout, "LIVENESS_COUNTER")) == 72.0


# Confirms the startup connectivity check honors a config-file URL and timeout rather than the built-in defaults
def test_config_file_connectivity_settings_reach_the_startup_check():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, 'CHECK_INTERNET_URL = "https://probe.example/ping"\nCHECK_INTERNET_TIMEOUT = 17\n')
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CONNECTIVITY_URL") == "https://probe.example/ping"
    assert probe_value(result.stdout, "CONNECTIVITY_TIMEOUT") == "17"


# Confirms VERIFY_SSL from a config file reaches the startup check and silences insecure-request warnings
def test_config_file_verify_ssl_reaches_the_startup_check():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "VERIFY_SSL = False\n")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CONNECTIVITY_VERIFY") == "False", "a TLS-inspecting proxy setup must not be blocked by the startup check"
    assert "INSECURE_WARNINGS_DISABLED" in result.stdout, "VERIFY_SSL = False must suppress the warnings it exists to avoid"


# Confirms the default configuration still verifies TLS and leaves the warnings in place
def test_default_configuration_keeps_tls_verification():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CONNECTIVITY_VERIFY") == "True"
    assert "INSECURE_WARNINGS_DISABLED" not in result.stdout


# Confirms a retired-setting upgrade note is printed once after the startup banner
def test_retired_setting_note_survives_normal_startup():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, 'SECRET_CIPHER_DICT = ""\n')
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    note = "* Note: SECRET_CIPHER_DICT was removed in a later version and is ignored."
    assert result.stdout.count(note) == 1
    assert result.stdout.index(f"v{monitor.VERSION}") < result.stdout.index(note)


# Confirms verbose CLI startup shows the effective configured JSON history destination
def test_verbose_startup_shows_json_history_directory():
    with make_temp_directory() as directory_name:
        json_dir = Path(directory_name) / "state" / "json"
        config_path = write_config(directory_name, f"JSON_DIR = {str(json_dir)!r}\n")
        result = run_cli(["--config-file", str(config_path), "--verbose"], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert "* JSON history directory:" in result.stdout
    assert str(json_dir) in result.stdout


@pytest.mark.parametrize(("flag", "setting"), (("--verbose", "VERBOSE_MODE"), ("--debug", "DEBUG_MODE")))
# Confirms explicit diagnostic flags win when a loaded config disables the same mode
def test_diagnostic_flag_overrides_disabled_config(flag, setting):
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, f"{setting} = False\n")
        result = run_cli(["--config-file", str(config_path), flag], DIAGNOSTIC_PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, f"EFFECTIVE_{setting.removesuffix('_MODE')}") == "True"


@pytest.mark.parametrize("url,timeout,verify", [("https://explicit.example", 3, False), ("https://other.example", 9, True)])
# Confirms an explicit argument still wins over the resolved global, so callers keep full control
def test_explicit_connectivity_arguments_win(monkeypatch, url, timeout, verify):
    recorded = {}
    monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://global.example")
    monkeypatch.setattr(monitor, "CHECK_INTERNET_TIMEOUT", 99)
    monkeypatch.setattr(monitor, "VERIFY_SSL", not verify)
    monkeypatch.setattr(monitor.req, "get", lambda target, **kwargs: recorded.update(url=target, **kwargs))

    assert monitor.check_internet(url, timeout, verify) is True
    assert (recorded["url"], recorded["timeout"], recorded["verify"]) == (url, timeout, verify)


# Confirms no connectivity setting is frozen into the function signature where a config file cannot reach it
def test_connectivity_defaults_are_not_bound_at_import():
    defaults = monitor.check_internet.__defaults__

    assert defaults == (None, None, None), "resolving these at import time would freeze them before any config file loads"


# Confirms JSON history files resolve under JSON_DIR while the empty default preserves bare filenames
def test_json_history_paths_follow_the_configured_directory(tmp_path):
    assert monitor.build_json_history_paths("alice") == ("spotify_profile_alice_followers.json", "spotify_profile_alice_followings.json", "spotify_profile_alice_playlists.json")

    json_dir = tmp_path / "state" / "json"
    prepared = monitor.prepare_json_directory(str(json_dir))

    assert Path(prepared) == json_dir
    assert json_dir.is_dir()
    assert monitor.build_json_history_paths("alice", prepared) == (str(json_dir / "spotify_profile_alice_followers.json"), str(json_dir / "spotify_profile_alice_followings.json"), str(json_dir / "spotify_profile_alice_playlists.json"))

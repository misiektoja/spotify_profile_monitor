import re
import inspect
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
    "runtime['spotify_profile_monitor_uri'] = lambda user_id, csv_file, playlists: print(f'CHECK_INTERVAL={runtime[\"SPOTIFY_CHECK_INTERVAL\"]}') or print(f'LIVENESS_SECONDS={runtime[\"LIVENESS_REMINDER_SECONDS\"]}') or print(f'CACHE_TTL={runtime[\"PLAYLIST_INFO_CACHE_TTL\"]}'); "
)
DIAGNOSTIC_PROBE_SETUP = PROBE_SETUP + "runtime['spotify_profile_monitor_uri'] = lambda user_id, csv_file, playlists: print(f'EFFECTIVE_DEBUG={runtime[\"DEBUG_MODE\"]}') or print(f'EFFECTIVE_VERBOSE={runtime[\"VERBOSE_MODE\"]}'); "
WEBHOOK_PROBE_SETUP = PROBE_SETUP + "runtime['spotify_profile_monitor_uri'] = lambda user_id, csv_file, playlists: print(f'WEBHOOK_ENABLED={runtime[\"WEBHOOK_ENABLED\"]}'); "


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


# Confirms a config-file check interval reaches the loop with the liveness reminder and the playlist cache lifetime
def test_config_file_check_interval_rescales_derived_values():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_CHECK_INTERVAL = 300\nLIVENESS_CHECK_INTERVAL = 43200\n")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CHECK_INTERVAL") == "300"
    assert float(probe_value(result.stdout, "LIVENESS_SECONDS")) == 43200.0, "the liveness cadence must follow the configured interval, not the built-in default"


# Confirms a slow config-file poll widens the playlist cache instead of expiring between every check
def test_config_file_slow_poll_widens_the_playlist_cache():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_CHECK_INTERVAL = 86400\n")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert float(probe_value(result.stdout, "CACHE_TTL")) == 172800.0, "a poll slower than the cache lifetime must widen the cache"


# Confirms a check interval longer than the liveness interval leaves the configured reminder alone
def test_a_long_check_interval_keeps_the_configured_liveness_interval():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_CHECK_INTERVAL = 86400\nLIVENESS_CHECK_INTERVAL = 43200\n")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert float(probe_value(result.stdout, "LIVENESS_SECONDS")) == 43200.0


# Confirms a command-line interval still wins over the config file and leaves the liveness reminder alone
def test_command_line_interval_overrides_the_config_file():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_CHECK_INTERVAL = 300\nLIVENESS_CHECK_INTERVAL = 43200\n")
        result = run_cli(["--config-file", str(config_path), "--check-interval", "600"], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CHECK_INTERVAL") == "600"
    assert float(probe_value(result.stdout, "LIVENESS_SECONDS")) == 43200.0


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
    assert str(json_dir.resolve()) in result.stdout


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
    parameters = inspect.signature(monitor.check_internet).parameters

    assert [parameters[name].default for name in ("url", "timeout", "verify")] == [None, None, None], "resolving these at import time would freeze them before any config file loads"


# Confirms JSON history files resolve under JSON_DIR while the empty default preserves bare filenames
def test_json_history_paths_follow_the_configured_directory(tmp_path):
    assert monitor.build_json_history_paths("alice") == ("spotify_profile_alice_followers.json", "spotify_profile_alice_followings.json", "spotify_profile_alice_playlists.json")

    json_dir = tmp_path / "state" / "json"
    prepared = monitor.prepare_json_directory(str(json_dir))

    assert Path(prepared) == json_dir
    assert json_dir.is_dir()
    assert monitor.build_json_history_paths("alice", prepared) == (str(json_dir / "spotify_profile_alice_followers.json"), str(json_dir / "spotify_profile_alice_followings.json"), str(json_dir / "spotify_profile_alice_playlists.json"))


# Confirms an unedited webhook destination switches the channel off while a real one keeps it on
@pytest.mark.parametrize(("webhook_url", "expected"), (("your_webhook_url", "False"), ("https://ntfy.sh/some-topic", "True")))
def test_a_placeholder_webhook_url_switches_the_channel_off(webhook_url, expected):
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, f'WEBHOOK_ENABLED = True\nWEBHOOK_PROVIDER = "ntfy"\nWEBHOOK_URL = "{webhook_url}"\n')
        result = run_cli(["--config-file", str(config_path)], WEBHOOK_PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "WEBHOOK_ENABLED") == expected


# The diagnostic line is documented as comma-separated key=value fields, so the length travels as its own field
@pytest.mark.parametrize("key, value, fields", [
    ("SP_USER_CLIENT_ID", "0123456789abcdef0123456789abcdef", {"value": "set", "chars": 32}),
    ("SMTP_PASSWORD", "a-password-the-user-picked", {"value": "set", "chars": None}),
    ("SP_APP_CLIENT_SECRET", "your_spotify_app_client_secret", {"value": "not set", "chars": None}),
    ("SP_DC_COOKIE", "", {"value": "not set", "chars": None}),
])
def test_no_secret_field_value_carries_a_comma(key, value, fields):
    assert monitor.secret_fields(value, key) == fields
    assert all("," not in str(part) for part in fields.values())


# A source outside the set is a typo rather than a new layer, so it is refused instead of reaching the summary
def test_an_unsupported_secret_source_is_refused(monkeypatch):
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {})

    with pytest.raises(ValueError, match="Unsupported secret source"):
        monitor.record_secret_source("SMTP_PASSWORD", "somewhere else", "a-password-the-user-picked")

    assert monitor.SECRET_SOURCES == {}


# A placeholder is not a value, so recording it clears the earlier answer rather than adding a row
def test_a_placeholder_clears_the_recorded_source(monkeypatch):
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"SMTP_PASSWORD": "dotenv file"})

    monitor.record_secret_source("SMTP_PASSWORD", "command line", "your_smtp_password")

    assert monitor.SECRET_SOURCES == {}


# Confirms every layer that can supply a secret is traced under the source that actually supplied it
@pytest.mark.parametrize("arguments, setup, expected", [
    ([], "", "name=SMTP_PASSWORD, source=configuration file or command line, value=set"),
    ([], "runtime['os'].environ['NTFY_ACCESS_TOKEN'] = 'tk_exported_token'; ", "name=NTFY_ACCESS_TOKEN, source=environment, value=set"),
    (["--webhook-url", "https://ntfy.sh/traced-topic"], "", "name=WEBHOOK_URL, source=command line, value=set"),
    (["--oauth-user-creds", "0123456789abcdef0123456789abcdef:fedcba9876543210fedcba9876543210"], "", "name=SP_USER_CLIENT_ID, source=command line, value=set, chars=32"),
])
def test_every_secret_layer_is_traced(arguments, setup, expected):
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, 'SMTP_PASSWORD = "a-password-the-user-picked"\n')
        result = run_cli(["--config-file", str(config_path), "--debug", "--doctor"] + arguments, setup)

    assert f"Secret resolution: {expected}" in result.stdout
    assert "a-password-the-user-picked" not in result.stdout


# The command line is the last layer to supply a secret, so a run with none says so only after it has had its say
def test_a_run_with_no_secret_anywhere_says_so():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "spotify_profile_monitor.conf"
        config_path.write_text('TARGET_USER_URI_ID = "config.user"\nDOTENV_FILE = "none"\nLOCAL_TIMEZONE = "UTC"\nDISABLE_LOGGING = True\n', encoding="utf-8")
        result = run_cli(["--config-file", str(config_path), "--env-file", "none", "--debug", "--doctor"])

    assert "Secret resolution:" not in result.stdout
    assert "No private settings were resolved from config, dotenv, environment or the command line" in result.stdout


# Verifies a real run with discovery switched off carries the sentinel into the recovery command it prints,
# since the command reads the config and pasting it without the flag would turn discovery back on
def test_discovery_switched_off_reaches_the_printed_recovery_command():
    setup = "runtime['SP_DC_COOKIE'] = 'your_sp_dc_cookie_value'; runtime['TOKEN_SOURCE'] = 'cookie'; runtime['_wizard_install_method'] = lambda: 'manual'; runtime['check_internet'] = lambda *args, **kwargs: False;"
    result = run_cli(["--doctor", "--config-file", "none", "--env-file", "none"], setup)

    assert "--import-browser-cookie --browser firefox --config-file none" in result.stdout


# Confirms an unedited placeholder is never reported as a loaded secret, whichever layer recorded it
def test_placeholder_secrets_are_not_reported_as_loaded(monkeypatch):
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"WEBHOOK_URL": "dotenv file", "SMTP_PASSWORD": "configuration file or command line"})
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "your_webhook_url")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "your_smtp_password")

    from_file, from_environment, from_settings, from_command_line = monitor.doctor_secret_sources(None)

    assert "WEBHOOK_URL" not in from_file + from_environment + from_settings + from_command_line
    assert "SMTP_PASSWORD" not in from_file + from_environment + from_settings + from_command_line


# Verifies the settings count is a debug trace rather than a verbose line, since it says nothing a user acts on
def test_the_config_settings_count_is_a_debug_only_trace(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spotify_profile_monitor.conf"
    config.write_text("CLEAR_SCREEN = False\nDISABLE_LOGGING = True\n", encoding="utf-8")
    namespace = {}

    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monitor.load_config_file(config, namespace=namespace)
    assert "settings from the configuration file" not in capsys.readouterr().out

    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monitor.load_config_file(config, namespace=namespace)
    assert "Configuration applied" in capsys.readouterr().out


# Confirms only debug keeps the screen, since a cleared terminal loses the run being compared against
@pytest.mark.parametrize(("debug", "verbose", "expected"), ((True, False, False), (False, True, True), (False, False, True)))
def test_only_debug_mode_keeps_the_screen(monkeypatch, debug, verbose, expected):
    cleared = []
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: cleared.append(bool(enabled)))
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)
    monkeypatch.setattr(monitor, "DEBUG_MODE", debug)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", verbose)
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: True, raising=False)

    monitor.prepare_startup_screen()

    assert cleared == [expected]


# Verifies the one-shot commands keep whatever is already on the screen, so their output stays scrollable
@pytest.mark.parametrize(("argv", "expected"), ((["spotify_profile_monitor", "--doctor"], True), (["spotify_profile_monitor", "--set-sp-dc"], True), (["spotify_profile_monitor", "--send-test-email"], True), (["spotify_profile_monitor", "--help"], True), (["spotify_profile_monitor", "test-user"], False)))
def test_one_shot_commands_keep_the_terminal_history(monkeypatch, argv, expected):
    monkeypatch.setattr(monitor.sys, "argv", argv)

    assert monitor.keep_terminal_history() is expected


# Verifies a redirected stdout is never cleared, so no escape sequence or TERM warning reaches the captured output
def test_a_redirected_stdout_is_never_cleared(monkeypatch):
    commands = []
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(monitor.os, "system", lambda command: commands.append(command))

    monitor.clear_screen(True)

    assert commands == []


@pytest.mark.parametrize("source, position", [("dotenv file", 0), ("environment", 1), ("configuration file or command line", 2), ("command line", 3)])
# Verifies each source that can supply a secret lands in its own bucket, so none of them is filed under another
def test_each_secret_source_lands_in_its_own_bucket(monkeypatch, source, position):
    for name in monitor.SECRET_KEYS:
        monkeypatch.setattr(monitor, name, "your_placeholder", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"SMTP_PASSWORD": source}, raising=False)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "a-real-secret-value", raising=False)

    buckets = monitor.doctor_secret_sources(None)

    assert buckets[position] == ["SMTP_PASSWORD"]
    assert [names for index, names in enumerate(buckets) if index != position] == [[], [], []]


# The part of the configuration template every sibling monitor shares, in the order they all use
SHARED_SETTING_ORDER = ("WEBHOOK_HEADERS", "NTFY_ACCESS_TOKEN", "WEBHOOK_TEMPLATE", "WEBHOOK_TRANSFORMS", "DISABLE_LOGGING", "ASCII_LOG_SEPARATORS", "TRUNCATE_CHARS", "CLEAR_SCREEN", "COLORED_OUTPUT", "COLOR_THEME", "VERBOSE_MODE", "DEBUG_MODE", "DELIVERY_CONFIRMATIONS")


# Returns every setting the built-in template declares, in template order, including the commented theme block
def template_setting_order(module):
    order = []
    for line in module.CONFIG_BLOCK.split("\n"):
        match = re.match(r"^([A-Z][A-Z0-9_]*)\s*[:=]", line) or re.match(r"^# ([A-Z][A-Z0-9_]*)\s*=", line)
        if match and match.group(1) not in order:
            order.append(match.group(1))
    return order


# Verifies the template keeps the order shared with the sibling monitors, so one tool's config reads like the next
def test_the_template_keeps_the_shared_setting_order():
    order = template_setting_order(monitor)

    assert set(SHARED_SETTING_ORDER) <= set(order), f"the template no longer declares {sorted(set(SHARED_SETTING_ORDER) - set(order))}"
    assert [name for name in order if name in SHARED_SETTING_ORDER] == list(SHARED_SETTING_ORDER)


# Verifies the linter defaults below the template repeat it in the same order, so a setting cannot drift or be filed twice
def test_the_linter_defaults_follow_the_template_order():
    source = Path(monitor.__file__).read_text(encoding="utf-8").split("\n")
    start = next(index for index, line in enumerate(source) if line.startswith("# Do not change values below")) + 1
    end = next(index for index, line in enumerate(source) if line.startswith("exec(CONFIG_BLOCK"))
    order = template_setting_order(monitor)
    mirrored = [match.group(1) for match in (re.match(r"^([A-Z][A-Z0-9_]*)\s*[:=]", line) for line in source[start:end]) if match and match.group(1) in set(order)]

    assert len(mirrored) == len(set(mirrored)), "a setting is repeated in the linter defaults"
    assert mirrored == [name for name in order if name in set(mirrored)]

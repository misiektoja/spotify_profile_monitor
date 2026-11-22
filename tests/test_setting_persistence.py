"""Checks saved-setting guidance and reusable Doctor monitoring commands."""

import argparse
import importlib
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

monitor = importlib.import_module("spotify_profile_monitor")


@pytest.fixture(autouse=True)
# Keeps command rendering independent of the active installation and files
def clean_command_context(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["spotify_profile_monitor.py"])
    for name, value in (("CLI_CONFIG_PATH", "none"), ("DOTENV_FILE", "none"), ("CONFIG_DISCOVERY_DISABLED", True), ("COLOR_ENABLED", False), ("WEB_DASHBOARD_ENABLED", False)):
        monkeypatch.setattr(monitor, name, value, raising=False)
    if hasattr(monitor, "INSTALL_METHOD_ENV_VAR"):
        monkeypatch.setenv(monitor.INSTALL_METHOD_ENV_VAR, "manual")


# Preserves explicit values and disabled switches without disclosing command-line credentials
def test_doctor_command_preserves_monitoring_settings(capsys):
    args = argparse.Namespace(check_interval=321, csv_file="output with spaces.csv", truncate=0, error_notification=False, webhook_enabled=False, do_not_detect_changed_profile_pic=False, do_not_monitor_playlists=False, spotify_dc_cookie="private-command-value", oauth_app_creds="private-command-value", oauth_user_creds="private-command-value", webhook_url="private-command-value")
    monitor._wizard_print_monitor_after_doctor("none", "none", "example-user", cli_args=args)
    output = capsys.readouterr().out
    command = next(line.strip() for line in output.splitlines() if line.startswith("    "))
    tokens = shlex.split(command)
    assert tokens[tokens.index("--check-interval") + 1] == "321"
    assert tokens[tokens.index("--csv-file") + 1] == "output with spaces.csv"
    assert tokens[tokens.index("--truncate") + 1] == "0"
    assert "--no-error-notify" in tokens
    assert "--no-webhook" in tokens
    assert "--no-profile-pic-detect" in tokens
    assert "--no-playlist-monitor" in tokens
    assert tokens[tokens.index("--spotify-dc-cookie") + 1] == "SP_DC_COOKIE"
    assert tokens[tokens.index("--oauth-app-creds") + 1] == "SP_APP_CLIENT_ID:SP_APP_CLIENT_SECRET"
    assert tokens[tokens.index("--oauth-user-creds") + 1] == "SP_USER_CLIENT_ID:SP_USER_CLIENT_SECRET"
    assert tokens[tokens.index("--webhook-url") + 1] == "WEBHOOK_URL"
    assert "private-command-value" not in output
    assert "Replace the uppercase credential placeholders" in output


# Prevents a monitoring command from repeating setup, delivery tests or listing actions
def test_monitoring_command_omits_other_actions():
    args = argparse.Namespace(doctor=True, setup=True, generate_config="new.conf", force=True, send_test_email=True, send_test_webhook=True, set_smtp_password=True, info_mode=True, list_recent=True, list_recent_matches=True, list_repos=True, import_browser_cookie=True, import_browser_session=True, export_all_playlists=True, achievements_count=5, games_count=10)
    assert monitor.doctor_monitoring_overrides(args) == ([], False)


# Keeps leading dashes inside values from becoming options when the command is reused
def test_leading_dash_value_is_attached_to_option():
    tokens, private = monitor.doctor_monitoring_overrides(argparse.Namespace(csv_file="-output.csv"))
    assert tokens == ["--csv-file=-output.csv"]
    assert private is False


# Leaves a command with no explicit monitoring overrides compact
def test_no_overrides_adds_no_options_or_credential_notice(capsys):
    args = argparse.Namespace()
    monitor._wizard_print_monitor_after_doctor("none", "none", "example-user", cli_args=args)
    output = capsys.readouterr().out
    assert "--check-interval" not in output
    assert "credential placeholders" not in output


# Exercises the real Doctor entry point while preventing network access
def test_cli_doctor_next_step_retains_selected_options():
    program = """import importlib, socket, sys
monitor = importlib.import_module("spotify_profile_monitor")
socket.socket.connect = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Unexpected network access"))
monitor.run_doctor = lambda *args, **kwargs: 0
sys.argv = ["spotify_profile_monitor.py", "--doctor", "--config-file", "none", "--env-file", "none", "--no-color", "--check-interval", "321"] + ["example-user"]
monitor.main()
"""
    result = subprocess.run([sys.executable, "-c", program], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, env=dict(os.environ, NO_COLOR="1"), timeout=30)
    assert result.returncode == 0, result.stderr + result.stdout
    output = result.stdout.split("Next steps", 1)[1]
    assert "--check-interval 321" in output
    assert "example-user" in output
    assert "--doctor" not in output


# Confirms the real help explains that setting flags need to be repeated
def test_help_explains_setting_lifetime():
    assert monitor.__file__ is not None
    result = subprocess.run([sys.executable, str(Path(monitor.__file__).resolve()), "--help"], capture_output=True, text=True, env=dict(os.environ, NO_COLOR="1"), timeout=30)
    assert result.returncode == 0
    assert "Setting options apply to the current run" in result.stdout
    assert "Include them on each run" in result.stdout

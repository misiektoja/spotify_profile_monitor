from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import Mock

import pytest

import spotify_profile_monitor as monitor


# Verifies runtime URL builders use centralized globals instead of repeated literals
def test_runtime_url_builders_use_global_bases(monkeypatch):
    monkeypatch.setattr(monitor, "NTFY_PUBLIC_BASE_URL", "https://notify.example")
    monkeypatch.setattr(monitor, "SPOTIFY_WEB_BASE_URL", "https://web.example")

    assert monitor.normalize_ntfy_topic_url("private-topic") == "https://notify.example/private-topic"
    assert monitor.spotify_convert_uri_to_url("spotify:user:target") == "https://web.example/user/target?si=1"


# Verifies project guide globals use the repository base and match explicit README anchors
def test_guide_urls_match_readme_anchors():
    guide_names = ("QUICK_START_GUIDE_URL", "INSTALLATION_GUIDE_URL", "CONFIG_GUIDE_URL", "COOKIE_GUIDE_URL", "MANUAL_COOKIE_GUIDE_URL", "CLIENT_GUIDE_URL", "TARGET_GUIDE_URL", "SMTP_GUIDE_URL", "WEBHOOK_GUIDE_URL", "SECRETS_GUIDE_URL", "INTERVALS_GUIDE_URL", "DOCTOR_GUIDE_URL", "OAUTH_GUIDE_URL", "OAUTH_USER_GUIDE_URL", "BROWSER_COOKIE_GUIDE_URL", "SETUP_GUIDE_URL")
    readme_anchors = set(re.findall(r'<a\s+id=["\x27]([^"\x27]+)', (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")))

    assert all(getattr(monitor, name).startswith(monitor.PROJECT_URL + "#") for name in guide_names)
    assert all(getattr(monitor, name).partition("#")[2] in readme_anchors for name in guide_names)


# Verifies failed config execution cannot mutate scalar or mutable existing values
def test_config_load_is_atomic_for_in_place_mutation(tmp_path):
    config_path = tmp_path / "broken.conf"
    config_path.write_text("VALUES.append('leak')\nSETTING = 'changed'\nraise RuntimeError('stop')\n", encoding="utf-8")
    namespace = {"VALUES": ["original"], "SETTING": "original"}

    assert monitor.load_config_file(config_path, namespace=namespace, report_errors=False) is False
    assert namespace == {"VALUES": ["original"], "SETTING": "original"}


# Verifies successful config execution commits assignments, mutations and deletions together
def test_config_load_commits_complete_namespace_transaction(tmp_path):
    config_path = tmp_path / "valid.conf"
    config_path.write_text("VALUES.append('saved')\nSETTING = 'changed'\ndel REMOVE_ME\n", encoding="utf-8")
    namespace = {"VALUES": ["original"], "SETTING": "original", "REMOVE_ME": True}

    assert monitor.load_config_file(config_path, namespace=namespace, report_errors=False) is True
    assert namespace == {"VALUES": ["original", "saved"], "SETTING": "changed"}


# Verifies loading a real config preserves builtins needed by later timestamp formatting
def test_config_load_preserves_runtime_builtins_for_timestamp_formatting(tmp_path):
    config_path = tmp_path / "valid.conf"
    config_path.write_text("LOCAL_TIMEZONE = 'UTC'\n", encoding="utf-8")
    source = f"import spotify_profile_monitor as monitor; from datetime import datetime; assert monitor.load_config_file({str(config_path)!r}); assert '__builtins__' in monitor.__dict__; print(monitor.get_short_date_from_ts(datetime(2025, 1, 2, 3, 4), always_show_year=True))"

    result = subprocess.run([sys.executable, "-c", source], cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "Thu 02 Jan 25, 03:04"


# Verifies recovery output keeps sanitized technical detail behind debug mode
def test_recovery_output_hides_detail_until_debug(monkeypatch):
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "COOKIE-SECRET-SENTINEL")
    error = RuntimeError("request failed with sp_dc=COOKIE-SECRET-SENTINEL")

    normal = monitor.render_recovery_error(error, "cookie_auth", debug=False)
    debug = monitor.render_recovery_error(error, "cookie_auth", debug=True)

    assert "Technical detail:" not in normal
    assert "Technical detail:" in debug
    assert "COOKIE-SECRET-SENTINEL" not in debug
    assert "<redacted>" in debug


# Verifies recurring recovery guidance is deduplicated until a successful reset
def test_recovery_hint_tracker_deduplicates_and_resets(capsys):
    tracker = monitor.RecoveryHintTracker()
    error = RuntimeError("401 Unauthorized sp_dc")

    monitor.print_monitor_recovery(error, "cookie_auth", tracker, "* Retry: ")
    first = capsys.readouterr().out
    monitor.print_monitor_recovery(error, "cookie_auth", tracker, "* Retry: ")
    second = capsys.readouterr().out
    tracker.reset()
    monitor.print_monitor_recovery(error, "cookie_auth", tracker, "* Retry: ")
    third = capsys.readouterr().out

    assert "To fix:" in first
    assert "To fix:" not in second
    assert "To fix:" in third


# Verifies existing generated configs require confirmation or explicit force
def test_config_replacement_requires_confirmation_or_force(tmp_path):
    destination = tmp_path / "existing.conf"
    destination.write_text("VALUE = 1\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        monitor.confirm_config_replacement(destination, interactive=False)
    assert monitor.confirm_config_replacement(destination, force=True, interactive=False) is True
    assert monitor.confirm_config_replacement(destination, interactive=True, input_func=lambda prompt: "no") is False
    assert monitor.confirm_config_replacement(destination, interactive=True, input_func=lambda prompt: "yes") is True


# Verifies setup duration input accepts portable human-friendly units
@pytest.mark.parametrize(("value", "expected"), (("90", 90), ("2m", 120), ("1.5h", 5400), ("1h 30m", 5400)))
def test_setup_duration_parser(value, expected):
    assert monitor._wizard_parse_duration(value) == expected


# Verifies the Chromium dependency installer uses the active interpreter
def test_chromium_dependency_install_uses_active_interpreter(monkeypatch):
    runner = Mock(return_value=Mock(returncode=0))
    available = iter((True,))
    monkeypatch.setattr(monitor.sys, "executable", "/active/venv/bin/python")
    monkeypatch.setattr(monitor.subprocess, "run", runner)
    monkeypatch.setattr(monitor, "_wizard_chromium_dependency_available", lambda: next(available))

    assert monitor._wizard_install_chromium_dependency("pip") is True
    runner.assert_called_once_with(["/active/venv/bin/python", "-m", "pip", "install", "spotify_profile_monitor[browser]"], check=False)


# Verifies saved ntfy tokens can be retained or explicitly disabled without display
def test_ntfy_token_setup_supports_keep_and_disable(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("NTFY_ACCESS_TOKEN=private-token\n", encoding="utf-8")
    updates = {}
    choices = iter((0, 2))
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: next(choices))

    monitor._wizard_collect_ntfy_access_token(updates, env_path)
    assert updates == {}
    monitor._wizard_collect_ntfy_access_token(updates, env_path)
    assert updates == {"NTFY_ACCESS_TOKEN": ""}


# Verifies Doctor reports each phase through the optional progress callback
def test_doctor_build_reports_progress(monkeypatch):
    monkeypatch.setattr(monitor, "doctor_check_environment", lambda *args: [])
    monkeypatch.setattr(monitor, "doctor_check_configuration", lambda *args: [])
    monkeypatch.setattr(monitor, "doctor_check_authentication", lambda *args: [])
    monkeypatch.setattr(monitor, "doctor_check_optional_oauth", lambda: [])
    monkeypatch.setattr(monitor, "doctor_check_connectivity", lambda *args: [])
    monkeypatch.setattr(monitor, "doctor_check_target", lambda *args: [])
    monkeypatch.setattr(monitor, "doctor_check_notifications", lambda: [])
    phases = []

    monitor.build_doctor_report(progress=phases.append)

    assert phases == ["environment", "configuration", "Spotify authentication", "metadata", "connectivity and target", "notifications"]


# Verifies Doctor preserves a startup failure for an explicitly missing dotenv file
def test_doctor_preserves_explicit_missing_dotenv_failure():
    advice = monitor.classify_recovery_error(context="config_missing", detail="Dotenv file not found: missing.env")
    startup = monitor.make_doctor_check("Configuration", "FAIL", "The requested dotenv file was not found", advice.detail, advice.fix, advice)

    checks = monitor.doctor_check_configuration(startup_checks=(startup,))

    assert startup in checks
    assert not any(check.label == "No dotenv file selected" for check in checks)


# Verifies Doctor keeps structured technical detail behind debug mode
def test_doctor_hides_recovery_detail_until_debug(monkeypatch):
    advice = monitor.make_recovery_advice("auth.cookie_invalid", "Spotify rejected authentication", "Import the cookie again", False, "HTTP 401 internal detail")
    report = monitor.DoctorReport(checks=[monitor.make_doctor_check("Authentication", "FAIL", advice.summary, advice.detail, advice=advice)])

    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    normal = monitor.render_doctor_report(report)
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    debug = monitor.render_doctor_report(report)

    assert "HTTP 401 internal detail" not in normal
    assert "HTTP 401 internal detail" in debug


# Verifies exclusive setup actions reject arguments they would otherwise ignore
@pytest.mark.parametrize("arguments", (("--setup", "--send-test-email"), ("--set-sp-dc", "target.user"), ("--set-webhook-url", "--doctor"), ("--import-browser-cookie", "--send-test-webhook"), ("--generate-config", "--doctor")))
def test_exclusive_actions_reject_ignored_arguments(arguments, monkeypatch):
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor", *arguments])

    with pytest.raises(SystemExit) as error:
        monitor.main()

    assert error.value.code == 2


# Verifies config generation accepts force before the action and backs up replacement
def test_generate_config_force_order_is_safe(tmp_path, monkeypatch):
    destination = tmp_path / "generated.conf"
    destination.write_text("SENTINEL = True\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor", "--force", "--generate-config", str(destination)])

    with pytest.raises(SystemExit) as error:
        monitor.main()

    backups = list(tmp_path.glob("generated.conf.*.bak"))
    assert error.value.code == 0
    assert "SENTINEL" not in destination.read_text(encoding="utf-8")
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "SENTINEL = True\n"

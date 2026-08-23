import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

import spotify_profile_monitor as monitor


# Verifies the startup banner uses the selected profile card and aligned product wordmark
def test_startup_banner_matches_selected_ascii_logo(capsys):
    monitor.print_startup_banner()

    output = capsys.readouterr().out
    banner_lines = monitor.STARTUP_BANNER.splitlines()

    assert output == f"{monitor.STARTUP_BANNER}\n{'':21}v{monitor.VERSION}\n\n"
    assert "| .-----.  ----  |   / ___| _ __   ___ | |_(_)/ _|_   _" in output
    assert "                     |  _ \\ _ __ ___  / _(_) | ___" in output
    assert "                     |  \\/  | ___  _ __ (_) |_ ___  _ __" in output
    assert all(line[18:21] == "   " for line in banner_lines[1:7])
    assert banner_lines[6][21:] == "      |_|                    |___/"
    assert "" not in banner_lines[1:]
    assert output.isascii()


# Verifies startup clearing requires the configured interactive terminal conditions
@pytest.mark.parametrize(("clear_enabled", "input_tty", "output_tty", "require_input", "expected"), ((True, True, True, True, True), (True, False, True, True, False), (True, True, False, True, False), (False, True, True, True, False), (True, False, True, False, True)))
def test_prepare_startup_screen_respects_terminal_conditions(clear_enabled, input_tty, output_tty, require_input, expected, monkeypatch):
    clear_mock = Mock()
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", clear_enabled)
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: input_tty)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: output_tty)
    monkeypatch.setattr(monitor, "clear_screen", clear_mock)

    monitor.prepare_startup_screen(require_input=require_input)

    clear_mock.assert_called_once_with(expected)


# Verifies direct setup clears the screen before launching the wizard
def test_setup_action_prepares_screen_before_wizard(monkeypatch):
    events = []
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor", "--setup"])
    monkeypatch.setattr(monitor, "prepare_startup_screen", lambda **kwargs: events.append(("screen", kwargs)))
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda *args: events.append(("setup", args)))

    with pytest.raises(SystemExit) as error:
        monitor.main()

    assert error.value.code == 0
    assert events == [("screen", {"require_input": True}), ("setup", (None, None, None))]


# Verifies no-argument onboarding clears the screen before printing its welcome
def test_no_argument_onboarding_prepares_screen_before_welcome(monkeypatch):
    events = []
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor"])
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(monitor, "TARGET_USER_URI_ID", "")
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "prepare_startup_screen", lambda **kwargs: events.append(("screen", kwargs)))
    monkeypatch.setattr(monitor, "_wizard_welcome", lambda: events.append(("welcome", {})))

    with pytest.raises(SystemExit) as error:
        monitor.main()

    assert error.value.code == 0
    assert events == [("screen", {"require_input": True}), ("welcome", {})]


# Verifies recovery actions preserve terminal history instead of clearing it
@pytest.mark.parametrize(("arguments", "runner_name", "exit_code"), ((["--import-browser-cookie", "--env-file", "none"], "run_browser_cookie_import", 0), (["--set-sp-dc", "--env-file", "none"], "run_set_sp_dc", 0), (["--set-webhook-url", "--env-file", "none"], "run_set_webhook_url", 0), (["--doctor", "--env-file", "none"], "run_doctor", 1)))
def test_recovery_actions_preserve_terminal_history(arguments, runner_name, exit_code, monkeypatch):
    prepare_mock = Mock()
    runner_result = exit_code if runner_name == "run_doctor" else None
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor", *arguments])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "TARGET_USER_URI_ID", "")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "USER_AGENT", "test-agent")
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "prepare_startup_screen", prepare_mock)
    monkeypatch.setattr(monitor, runner_name, lambda *args, **kwargs: runner_result)

    with pytest.raises(SystemExit) as error:
        monitor.main()

    assert error.value.code == exit_code
    prepare_mock.assert_not_called()


# Verifies the webhook delivery test uses the same clean-screen flow as the email test
def test_webhook_delivery_test_prepares_startup_screen(monkeypatch):
    prepare_mock = Mock()
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor", "--send-test-webhook", "--env-file", "none"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "USER_AGENT", "test-agent")
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "prepare_startup_screen", prepare_mock)
    monkeypatch.setattr(monitor, "send_webhook", lambda *args, **kwargs: 0)

    with pytest.raises(SystemExit) as error:
        monitor.main()

    assert error.value.code == 0
    prepare_mock.assert_called_once_with()


# Verifies generated configuration changes non-secrets but preserves secret placeholders
def test_generated_config_preserves_secrets_and_updates_regular_values():
    values = dict(vars(monitor))
    values.update({"SPOTIFY_CHECK_INTERVAL": 42, "SP_DC_COOKIE": "must-not-appear", "VERBOSE_MODE": True})

    content = monitor.generate_config_with_current_values(values)

    assert "SPOTIFY_CHECK_INTERVAL = 42" in content
    assert "VERBOSE_MODE = True" in content
    assert 'SP_DC_COOKIE = "your_sp_dc_cookie_value"' in content
    assert "must-not-appear" not in content


# Verifies safe config writes validate first and back up replacements
def test_write_config_validates_and_backs_up(tmp_path):
    destination = tmp_path / "profile.conf"
    destination.write_text("TRUNCATE_CHARS = 1\n", encoding="utf-8")

    status = monitor.write_config_file(destination, "TRUNCATE_CHARS = 2\n")

    assert destination.read_text(encoding="utf-8") == "TRUNCATE_CHARS = 2\n"
    assert Path(status["backup_path"]).read_text(encoding="utf-8") == "TRUNCATE_CHARS = 1\n"
    with pytest.raises(SyntaxError):
        monitor.write_config_file(destination, "TRUNCATE_CHARS =\n")
    # Content that parses but is not a plain setting assignment is refused before the file is touched
    with pytest.raises(ValueError):
        monitor.write_config_file(destination, "TRUNCATE_CHARS = __import__('os').getpid()\n")
    assert destination.read_text(encoding="utf-8") == "TRUNCATE_CHARS = 2\n"


# Verifies generated recovery commands preserve interpreter and custom paths
def test_action_command_uses_active_interpreter_and_custom_paths(tmp_path, monkeypatch):
    config_path = tmp_path / "custom config.conf"
    env_path = tmp_path / "private.env"
    monkeypatch.setattr(monitor.sys, "executable", "/custom/venv/bin/python")

    command = monitor._wizard_action_command("pip", "--doctor", config_path, env_path, "target.user")

    assert command.startswith("/custom/venv/bin/python -m spotify_profile_monitor --doctor target.user")
    assert str(config_path.resolve()) in command
    assert str(env_path.resolve()) in command


# Verifies concise startup output hides full rows until verbose mode
def test_startup_summary_has_concise_and_full_views(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "PROFILE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    rows = monitor.build_startup_summary("target.user", None, None, None)

    monitor.emit_startup_summary(rows, show_full=False)
    concise = capsys.readouterr().out
    monitor.emit_startup_summary(rows, show_full=True)
    complete = capsys.readouterr().out

    assert "* Target:" in concise
    assert "* More details:" in concise
    assert "* Error retry timer:" not in concise
    assert "* Error retry timer:" in complete
    assert "* More details:" not in complete


# Verifies setup review can edit one section without losing other answers
def test_setup_review_edits_polling_without_losing_state(tmp_path, monkeypatch):
    baseline = dict(vars(monitor))
    state = monitor.WizardSetupState(tmp_path / "config.conf", tmp_path / ".env", baseline, dict(baseline), {}, "target.user", True, {"complete": False, "validated": False, "browser": None, "source": "not configured"}, [], [])
    state.config_values["SPOTIFY_CHECK_INTERVAL"] = 1800
    choices = iter((1, 1, 0))
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: next(choices))
    monkeypatch.setattr(monitor, "_wizard_ask_duration", lambda *args, **kwargs: 90)

    saved = monitor._wizard_review_setup(state, "pip")

    assert saved is True
    assert state.config_values["SPOTIFY_CHECK_INTERVAL"] == 90
    assert state.target == "target.user"


# Verifies noninteractive setup refuses to mutate destination files
def test_setup_requires_interactive_terminal(tmp_path, monkeypatch):
    config_path = tmp_path / "config.conf"
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: False)

    with pytest.raises(SystemExit) as error:
        monitor.run_setup_wizard(config_file=config_path, env_file=tmp_path / ".env")

    assert error.value.code == 1
    assert not config_path.exists()


# Verifies initial setup collects polling before authentication
def test_setup_collects_polling_before_authentication(tmp_path, monkeypatch, capsys):
    events = []
    config_path = tmp_path / "config.conf"
    env_path = tmp_path / ".env"
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(monitor, "_wizard_destinations", lambda config, env: (config_path, env_path))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "_wizard_choose_config_destination", lambda path: path)
    monkeypatch.setattr(monitor, "_wizard_collect_target_section", lambda state, target=None: events.append("target"))
    monkeypatch.setattr(monitor, "_wizard_collect_polling_section", lambda state: (events.append("polling"), print("Spotify polling interval [1800s - 30m]:")))
    monkeypatch.setattr(monitor, "_wizard_collect_auth_section", lambda state, method: (events.append("authentication"), print("\nChoose an authentication mode")))
    monkeypatch.setattr(monitor, "_wizard_collect_email_section", lambda state: events.append("email"))
    monkeypatch.setattr(monitor, "_wizard_collect_webhook_section", lambda state: events.append("webhook"))
    monkeypatch.setattr(monitor, "_wizard_review_setup", lambda state, method: False)

    with pytest.raises(SystemExit) as error:
        monitor.run_setup_wizard()

    assert error.value.code == 1
    assert events == ["target", "polling", "authentication", "email", "webhook"]
    output = capsys.readouterr().out
    assert "Spotify polling interval [1800s - 30m]:\n\nChoose an authentication mode" in output
    assert "Spotify polling interval [1800s - 30m]:\n\n\nChoose an authentication mode" not in output


# Verifies the editable summary follows the same polling-before-authentication order
def test_setup_summary_and_editor_order_polling_before_authentication(tmp_path, monkeypatch, capsys):
    baseline = dict(vars(monitor))
    state = monitor.WizardSetupState(tmp_path / "config.conf", tmp_path / ".env", baseline, dict(baseline), {}, "target.user", True, {"complete": True, "validated": True, "browser": None, "source": "cookie"}, [], [])
    state.config_values["SPOTIFY_CHECK_INTERVAL"] = 90
    labels = []

    def choose(question, options, *args, **kwargs):
        labels.extend(label for label, description in options)
        return 6

    monkeypatch.setattr(monitor, "_wizard_ask_choice", choose)

    monitor._wizard_print_setup_summary(state, "pip")
    summary = capsys.readouterr().out
    monitor._wizard_edit_setup_section(state, "pip")

    assert summary.index("Polling interval:") < summary.index("Token source:")
    assert labels[:3] == ["Target and persistence", "Polling interval", "Authentication"]


# Verifies confirmed setup writes both files and prints portable next steps
def test_setup_saves_confirmed_incomplete_configuration(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "custom config.conf"
    env_path = tmp_path / "private.env"
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(monitor, "_wizard_choose_config_destination", lambda path: path)

    # Supplies deterministic answers without bypassing setup persistence
    def collect_target(state, initial_target=None):
        state.target = "target.user"
        state.persist_target = True
        state.config_values["TARGET_USER_URI_ID"] = state.target

    # Leaves authentication incomplete so the test never contacts Spotify
    def collect_auth(state, method):
        state.config_values["TOKEN_SOURCE"] = "cookie"
        state.auth = {"complete": False, "validated": False, "browser": None, "source": "not configured"}

    monkeypatch.setattr(monitor, "_wizard_collect_target_section", collect_target)
    monkeypatch.setattr(monitor, "_wizard_collect_auth_section", collect_auth)
    monkeypatch.setattr(monitor, "_wizard_collect_polling_section", lambda state: state.config_values.update({"SPOTIFY_CHECK_INTERVAL": 90}))
    monkeypatch.setattr(monitor, "_wizard_collect_email_section", lambda state: setattr(state, "enabled_notifications", []))
    monkeypatch.setattr(monitor, "_wizard_collect_webhook_section", lambda state: setattr(state, "enabled_webhooks", []))
    monkeypatch.setattr(monitor, "_wizard_review_setup", lambda state, method: True)

    with pytest.raises(SystemExit) as error:
        monitor.run_setup_wizard(config_file=config_path, env_file=env_path)

    output = capsys.readouterr().out
    assert error.value.code == 0
    assert config_path.is_file()
    assert env_path.is_file()
    assert 'TARGET_USER_URI_ID = "target.user"' in config_path.read_text(encoding="utf-8")
    assert "--config-file" in output
    assert str(config_path) in output
    assert "--env-file" in output
    assert str(env_path) in output

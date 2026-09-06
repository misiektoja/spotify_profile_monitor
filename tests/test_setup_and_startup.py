import builtins
from pathlib import Path
from unittest.mock import Mock

import signal
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


# Verifies an invalid discovered config remains visible and exits before no-argument onboarding
def test_invalid_config_exits_before_no_argument_onboarding(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "spotify_profile_monitor.conf"
    config_path.write_text("# unsupported helper\nCUSTOM_HELPER = 'test'\n", encoding="utf-8")
    prepare_mock = Mock()
    welcome_mock = Mock()
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "TARGET_USER_URI_ID", "")
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: config_path)
    monkeypatch.setattr(monitor, "prepare_startup_screen", prepare_mock)
    monkeypatch.setattr(monitor, "_wizard_welcome", welcome_mock)

    with pytest.raises(SystemExit) as error:
        monitor.main()

    output = capsys.readouterr().out
    assert error.value.code == 1
    assert "Line 2: unsupported configuration setting 'CUSTOM_HELPER'" in output
    prepare_mock.assert_not_called()
    welcome_mock.assert_not_called()


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


# Verifies direct Doctor startup prints the product banner before running checks
def test_doctor_action_prints_banner_before_checks(monkeypatch):
    events = []
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor", "--doctor", "--config-file", "none", "--env-file", "none"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "TARGET_USER_URI_ID", "")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "USER_AGENT", "test-agent")
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: events.append("banner"))
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: events.append("doctor") or 1)

    with pytest.raises(SystemExit) as error:
        monitor.main()

    assert error.value.code == 1
    assert events == ["banner", "doctor"]


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
    monkeypatch.setattr(monitor, "JSON_DIR", "state/json")
    rows = monitor.build_startup_summary("target.user", None, None, None)

    monitor.emit_startup_summary(rows, show_full=False)
    concise = capsys.readouterr().out
    monitor.emit_startup_summary(rows, show_full=True)
    complete = capsys.readouterr().out

    assert "* Target:" in concise
    assert "* More details:" in concise
    assert "* JSON history directory:" not in concise
    assert "* Error retry timer:" not in concise
    assert "* JSON history directory:" in complete
    assert str(Path("state/json").resolve()) in complete
    assert "* Error retry timer:" in complete
    assert "* More details:" not in complete


# Verifies the complete view alone reports the install method and names the origin of every loaded secret
def test_startup_summary_reports_install_method_and_secret_origins(tmp_path, monkeypatch, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text("SMTP_PASSWORD=from-file\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "from-file")
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "from-environment")
    monkeypatch.setenv("SP_DC_COOKIE", "from-environment")
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"SMTP_PASSWORD": "dotenv file", "SP_DC_COOKIE": "environment"}, raising=False)
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor.py"])
    rows = monitor.build_startup_summary("target.user", None, str(env_file), None)

    monitor.emit_startup_summary(rows, show_full=False)
    concise = capsys.readouterr().out
    monitor.emit_startup_summary(rows, show_full=True)
    complete = capsys.readouterr().out

    for label in ("* Install method:", "* Secrets from dotenv:", "* Secrets from environment:"):
        assert label not in concise
        assert label in complete
    assert "downloaded script" in complete
    assert "SMTP_PASSWORD" in complete and "SP_DC_COOKIE" in complete
    assert "from-file" not in complete and "from-environment" not in complete


# Verifies the default JSON history destination is shown as its effective directory path
def test_startup_summary_shows_current_json_directory_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "JSON_DIR", "")

    rows = monitor.build_startup_summary("target.user", None, None, None)
    json_row = next(row for row in rows if row.label == "JSON history directory")

    assert json_row.value == str(tmp_path)


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


# Verifies the polling prompt advertises every accepted duration form
def test_setup_polling_prompt_includes_duration_hint(tmp_path, monkeypatch):
    baseline = dict(vars(monitor))
    state = monitor.WizardSetupState(tmp_path / "config.conf", tmp_path / ".env", baseline, dict(baseline), {}, "target.user", True, {"complete": False, "validated": False, "browser": None, "source": "not configured"}, [], [])
    state.config_values["SPOTIFY_CHECK_INTERVAL"] = 1800
    prompts = []
    monkeypatch.setattr(monitor, "_wizard_ask_duration", lambda question, default: prompts.append((question, default)) or default)

    monitor._wizard_collect_polling_section(state)

    assert prompts == [("Spotify polling interval (seconds or use s/m/h/d)", 1800)]


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
    monkeypatch.setattr(monitor, "_wizard_collect_polling_section", lambda state: (events.append("polling"), print("Spotify polling interval (seconds or use s/m/h/d) [1800s - 30m]:")))
    monkeypatch.setattr(monitor, "_wizard_collect_auth_section", lambda state, method: (events.append("authentication"), print("\nChoose an authentication mode")))
    monkeypatch.setattr(monitor, "_wizard_collect_email_section", lambda state: events.append("email"))
    monkeypatch.setattr(monitor, "_wizard_collect_webhook_section", lambda state: events.append("webhook"))
    monkeypatch.setattr(monitor, "_wizard_collect_output_section", lambda state: events.append("output"))
    monkeypatch.setattr(monitor, "_wizard_review_setup", lambda state, method: False)

    with pytest.raises(SystemExit) as error:
        monitor.run_setup_wizard()

    assert error.value.code == 1
    assert events == ["target", "polling", "authentication", "email", "webhook", "output"]
    output = capsys.readouterr().out
    assert "Spotify polling interval (seconds or use s/m/h/d) [1800s - 30m]:\n\nChoose an authentication mode" in output
    assert "Spotify polling interval (seconds or use s/m/h/d) [1800s - 30m]:\n\n\nChoose an authentication mode" not in output


# Verifies the editable summary follows the same polling-before-authentication order
def test_setup_summary_and_editor_order_polling_before_authentication(tmp_path, monkeypatch, capsys):
    baseline = dict(vars(monitor))
    state = monitor.WizardSetupState(tmp_path / "config.conf", tmp_path / ".env", baseline, dict(baseline), {}, "target.user", True, {"complete": True, "validated": True, "browser": None, "source": "cookie"}, [], [])
    state.config_values["SPOTIFY_CHECK_INTERVAL"] = 90
    labels = []

    def choose(question, options, *args, **kwargs):
        labels.extend(label for label, description in options)
        return 7

    monkeypatch.setattr(monitor, "_wizard_ask_choice", choose)

    monitor._wizard_print_setup_summary(state, "pip")
    summary = capsys.readouterr().out
    monitor._wizard_edit_setup_section(state, "pip")

    assert summary.index("Polling interval:") < summary.index("Token source:")
    assert "Polling interval:      90s - 1m 30s" in summary
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
    monkeypatch.setattr(monitor, "_wizard_collect_output_section", lambda state: None)
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


# Verifies the output section records the log choice and the CSV destination it was given
def test_the_output_section_records_the_log_and_csv_choices(monkeypatch, tmp_path):
    baseline = dict(vars(monitor))
    state = monitor.WizardSetupState(tmp_path / "config.conf", tmp_path / ".env", baseline, dict(baseline), {}, "target.user", True, {"complete": False, "validated": False, "browser": None, "source": "not configured"}, [], [])
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: False)
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, default="", required=False: str(tmp_path / "profile.csv"))

    monitor._wizard_collect_output_section(state)

    assert state.config_values["DISABLE_LOGGING"] is True
    assert state.config_values["CSV_FILE"] == str(tmp_path / "profile.csv")


# Verifies a blank CSV answer disables CSV output rather than storing an empty path as a file name
def test_a_blank_csv_answer_disables_csv_output(monkeypatch, tmp_path):
    baseline = dict(vars(monitor))
    state = monitor.WizardSetupState(tmp_path / "config.conf", tmp_path / ".env", baseline, dict(baseline), {}, "target.user", True, {"complete": False, "validated": False, "browser": None, "source": "not configured"}, [], [])
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: True)
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, default="", required=False: "")

    monitor._wizard_collect_output_section(state)

    assert state.config_values["DISABLE_LOGGING"] is False
    assert state.config_values["CSV_FILE"] == ""


# Verifies the two escape wordings, so a blank answer and a rejected one are never asked the same way
@pytest.mark.parametrize(("consequence", "question", "answer", "expected"), (("", "Try entering the webhook URL again?", "y", True), ("", "Try entering the webhook URL again?", "n", False), ("Webhook alerts stay off until one is set", "Continue without the webhook URL? Webhook alerts stay off until one is set", "y", False), ("Webhook alerts stay off until one is set", "Continue without the webhook URL? Webhook alerts stay off until one is set", "n", True)))
def test_the_escape_wording_matches_the_kind_of_rejection(monkeypatch, consequence, question, answer, expected):
    questions = []
    monkeypatch.setattr(monitor, "_wizard_input", lambda prompt: questions.append(prompt) or answer)

    assert monitor._wizard_offer_retry("webhook URL", consequence) is expected
    assert question in questions[0]


# Verifies a required answer can be abandoned instead of trapping the wizard in its own loop
def test_a_required_text_answer_can_be_abandoned(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_input", lambda prompt: "")
    monkeypatch.setattr(monitor, "_wizard_offer_retry", lambda label, consequence="": False)

    assert monitor._wizard_ask_text("SMTP username", required=True) == ""


# Verifies a retried required answer is still collected
def test_a_retried_required_text_answer_is_accepted(monkeypatch):
    answers = iter(["", "smtp-user"])
    monkeypatch.setattr(monitor, "_wizard_input", lambda prompt: next(answers))
    monkeypatch.setattr(monitor, "_wizard_offer_retry", lambda label, consequence="": True)

    assert monitor._wizard_ask_text("SMTP username", required=True) == "smtp-user"


# Verifies the hidden prompt returns a blank secret instead of looping, leaving the decision to its caller
def test_a_blank_secret_returns_instead_of_looping(monkeypatch):
    monkeypatch.setattr(monitor.getpass, "getpass", lambda prompt: "")

    assert monitor._wizard_ask_secret("SMTP password") == ""


# Verifies a target the wizard cannot normalize can be abandoned rather than asked forever, and that an answer already abandoned is not queried twice
@pytest.mark.parametrize(("answer", "expected_offers"), (("", []), ("not a spotify profile", ["Spotify profile"])))
def test_an_unusable_target_can_be_abandoned(monkeypatch, answer, expected_offers):
    offers = []
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, default="", required=False: answer)
    monkeypatch.setattr(monitor, "_wizard_offer_retry", lambda label, consequence="": offers.append(label) or False)

    assert monitor._wizard_target() == ""
    assert offers == expected_offers


# Verifies abandoning any mail server answer switches every email alert off rather than saving half a server
@pytest.mark.parametrize("abandoned", ["SMTP host", "SMTP username", "Sender email", "Receiver email"])
def test_an_abandoned_mail_server_answer_switches_email_off(monkeypatch, tmp_path, abandoned):
    config_values = {"PROFILE_NOTIFICATION": True, "FOLLOWERS_FOLLOWINGS_NOTIFICATION": True, "ERROR_NOTIFICATION": True, "EMAIL_IMAGES": True}
    secret_updates = {}
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: True)
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, default="", required=False: "" if question == abandoned else "answer@example.test")
    monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda question, default: default)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda question: "private-password")

    assert monitor._wizard_collect_email(config_values, secret_updates, tmp_path / ".env") == []
    assert config_values == {"PROFILE_NOTIFICATION": False, "FOLLOWERS_FOLLOWINGS_NOTIFICATION": False, "ERROR_NOTIFICATION": False, "EMAIL_IMAGES": False}
    assert secret_updates == {}


# Verifies a mail server that refuses the sign-in can be abandoned, which switches every email alert off
def test_rejected_mail_server_settings_can_be_abandoned(monkeypatch, tmp_path):
    config_values = {"PROFILE_NOTIFICATION": True, "FOLLOWERS_FOLLOWINGS_NOTIFICATION": True, "ERROR_NOTIFICATION": True, "EMAIL_IMAGES": True}
    labels = []
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: True)
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, default="", required=False: "answer@example.test")
    monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda question, default: default)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda question: "private-password")
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: monitor.make_recovery_advice("smtp.invalid", "SMTP settings are invalid", "Correct SENDER_EMAIL", False, "SENDER_EMAIL is not a valid address"))
    monkeypatch.setattr(monitor, "_wizard_offer_retry", lambda label, consequence="": labels.append(label) or False)

    assert monitor._wizard_collect_email(config_values, {}, tmp_path / ".env") == []
    assert labels == ["mail server settings"]
    assert config_values["PROFILE_NOTIFICATION"] is False
    assert config_values["ERROR_NOTIFICATION"] is False


# Verifies a webhook URL nobody can supply switches the channel off instead of repeating the prompt
@pytest.mark.parametrize(("entry", "consequence_expected"), (("", True), ("not-a-url", False)))
def test_an_unusable_webhook_url_can_be_abandoned(monkeypatch, tmp_path, entry, consequence_expected):
    config_values = {"WEBHOOK_ENABLED": True, "WEBHOOK_PROFILE_NOTIFICATION": True, "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION": True, "WEBHOOK_ERROR_NOTIFICATION": True, "NTFY_IMAGES": True}
    secret_updates = {}
    labels = []
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: True)
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda question, options, default_index=0: 0)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda question: entry)
    monkeypatch.setattr(monitor, "_wizard_offer_retry", lambda label, consequence="": labels.append((label, consequence)) or False)

    assert monitor._wizard_collect_webhook(config_values, secret_updates, tmp_path / ".env") == []
    assert labels == [("webhook URL", "Webhook alerts stay off until one is set" if consequence_expected else "")]
    assert config_values == {"WEBHOOK_ENABLED": False, "WEBHOOK_PROFILE_NOTIFICATION": False, "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION": False, "WEBHOOK_ERROR_NOTIFICATION": False, "NTFY_IMAGES": False, "WEBHOOK_PROVIDER": "discord"}
    assert secret_updates == {}


# Verifies a retried webhook URL is still collected after one unusable entry
def test_a_retried_webhook_url_is_accepted(monkeypatch, tmp_path):
    config_values = {}
    secret_updates = {}
    entries = iter(["", "https://discord.com/api/webhooks/1/token"])
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: True)
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda question, options, default_index=0: 0)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda question: next(entries))
    monkeypatch.setattr(monitor, "_wizard_offer_retry", lambda label, consequence="": True)
    monkeypatch.setattr(monitor, "_wizard_collect_notification_images", lambda question: False)

    monitor._wizard_collect_webhook(config_values, secret_updates, tmp_path / ".env")

    assert secret_updates["WEBHOOK_URL"] == "https://discord.com/api/webhooks/1/token"
    assert config_values["WEBHOOK_ENABLED"] is True


# Verifies a blank ntfy access token means no token rather than an unanswerable prompt
def test_a_blank_ntfy_access_token_means_no_token(monkeypatch, tmp_path):
    secret_updates = {}
    monkeypatch.delenv("NTFY_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: True)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda question: "")

    monitor._wizard_collect_ntfy_access_token(secret_updates, tmp_path / ".env")

    assert secret_updates == {}


# Verifies a token pasted with its authorization scheme can be abandoned and is never saved
def test_an_ntfy_access_token_pasted_with_its_scheme_can_be_abandoned(monkeypatch, tmp_path):
    secret_updates = {}
    labels = []
    monkeypatch.delenv("NTFY_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: True)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda question: "Bearer tk_secret")
    monkeypatch.setattr(monitor, "_wizard_offer_retry", lambda label, consequence="": labels.append(label) or False)

    monitor._wizard_collect_ntfy_access_token(secret_updates, tmp_path / ".env")

    assert labels == ["ntfy access token"]
    assert secret_updates == {}


# Verifies a blank sp_dc entry is never sent to Spotify and can be abandoned without losing the other answers
def test_a_blank_sp_dc_entry_is_not_validated(monkeypatch, tmp_path):
    secret_updates = {}
    labels = []
    monkeypatch.delenv("SP_DC_COOKIE", raising=False)
    monkeypatch.setattr(monitor, "_wizard_import_browsers", lambda: [])
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda question, options, default_index=0: len(options) - 2)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda question: "")
    monkeypatch.setattr(monitor, "validate_sp_dc_cookie", lambda cookie: pytest.fail("a blank cookie was sent to Spotify"))
    monkeypatch.setattr(monitor, "_wizard_offer_retry", lambda label, consequence="": labels.append((label, consequence)) or False)

    auth = monitor._wizard_collect_cookie_auth("pip", tmp_path / ".env", secret_updates)

    assert labels == [("sp_dc cookie", "Monitoring cannot start until one is set")]
    assert auth == {"complete": False, "validated": False, "browser": None, "source": "not configured"}
    assert secret_updates == {}


# Verifies a login Protobuf missing values can be abandoned, leaving client mode without credentials rather than looping
def test_an_incomplete_login_protobuf_can_be_abandoned(monkeypatch, tmp_path):
    protobuf_path = tmp_path / "login.bin"
    protobuf_path.write_bytes(b"protobuf")
    config_values = {}
    offers = []
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: True)
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, default="", required=False: str(protobuf_path))
    monkeypatch.setattr(monitor, "parse_login_request_body_file", lambda path: ("device-id", "system-id", "", "refresh-token"))
    monkeypatch.setattr(monitor, "_wizard_offer_retry", lambda label, consequence="": offers.append(label) or False)

    result = monitor._wizard_collect_client_auth(config_values, tmp_path / ".env", {})

    assert offers == ["login request Protobuf file"]
    assert result == {"complete": False, "validated": False, "browser": None, "source": "advanced client mode without credentials"}
    assert config_values == {}


# The rows shared with the sibling monitors, in the order every one of them prints
SHARED_ROW_ORDER = ("Target", "Authentication", "Polling interval", "Notifications (email)", "Notifications (webhook)", "Output", "Output logging", "Config", "Dotenv", "Liveness output", "CSV output", "Terminal truncation", "Local timezone", "Install method", "Secrets from dotenv", "Secrets from environment", "Secrets from config file", "Secrets from command line", "TLS verification", "ASCII log separators", "Coloured output", "Verbose mode", "Debug mode", "More details")


# Verifies the shared rows keep the order and the label column width every sibling monitor prints
def test_the_shared_summary_rows_match_the_sibling_tools():
    rows = monitor.build_startup_summary("target.user", "spotify_profile_monitor.conf", ".env", "spotify_profile_monitor.log")

    assert [row.label for row in rows if row.label in SHARED_ROW_ORDER] == list(SHARED_ROW_ORDER)
    # The renderer pads "<label>:" into a 30-character column, so a longer label swallows the separating space
    assert max(len(row.label) for row in rows) <= 28


# Verifies the one-shot command signs in before the password reaches the dotenv file
def test_set_smtp_password_signs_in_before_saving(tmp_path, monkeypatch, capsys):
    destination = tmp_path / ".env"
    destination.write_text("UNRELATED=stay\n", encoding="utf-8")
    sign_in = Mock(return_value="monitor@example.test")
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "find_config_file", lambda: None)
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor@example.test")

    result = monitor.run_set_smtp_password(env_file=destination, interactive=True, getpass_func=lambda prompt: "app-password", sign_in=sign_in)

    assert result == str(destination.resolve())
    sign_in.assert_called_once_with("app-password", timeout=5)
    saved = destination.read_text(encoding="utf-8")
    assert "UNRELATED=stay" in saved
    assert 'SMTP_PASSWORD="app-password"' in saved
    output = capsys.readouterr().out
    assert "signing in to smtp.example.test as monitor@example.test" in output
    assert "The mail server accepted the password for monitor@example.test" in output
    assert "app-password" not in output


# Verifies a password the mail server refuses leaves the dotenv file untouched
def test_set_smtp_password_keeps_the_dotenv_file_on_a_refused_sign_in(tmp_path):
    destination = tmp_path / ".env"
    destination.write_text("UNRELATED=stay\n", encoding="utf-8")
    refuse = Mock(side_effect=monitor.smtplib.SMTPAuthenticationError(535, b"authentication failed"))

    with pytest.raises(monitor.RecoveryError) as error:
        monitor.run_set_smtp_password(env_file=destination, interactive=True, getpass_func=lambda prompt: "wrong", sign_in=refuse)

    assert error.value.advice.code == "smtp.authentication"
    assert destination.read_text(encoding="utf-8") == "UNRELATED=stay\n"


# Verifies the command refuses without a terminal or a writable dotenv destination
def test_set_smtp_password_requires_safe_persistence():
    with pytest.raises(monitor.RecoveryError) as no_terminal:
        monitor.run_set_smtp_password(interactive=False, getpass_func=Mock(side_effect=AssertionError("prompted")))
    assert "interactive terminal" in no_terminal.value.advice.detail

    with pytest.raises(monitor.RecoveryError) as no_destination:
        monitor.run_set_smtp_password(env_file="none", interactive=True, getpass_func=Mock(side_effect=AssertionError("prompted")))
    assert "dotenv destination" in no_destination.value.advice.detail


# Verifies the sign-in uses the configured mail server and restores the password it borrowed
def test_smtp_sign_in_uses_the_configured_mail_server(monkeypatch):
    session = Mock()
    connect = Mock(return_value=session)
    monkeypatch.setattr(monitor, "validate_smtp_configuration", lambda: None)
    monkeypatch.setattr(monitor, "smtp_connect_and_login", connect)
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor@example.test")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "saved")
    monkeypatch.setattr(monitor, "SMTP_SSL", True)

    assert monitor.smtp_sign_in("entered", timeout=5) == "monitor@example.test"

    connect.assert_called_once_with(True, smtp_timeout=5)
    session.quit.assert_called_once()
    assert monitor.SMTP_PASSWORD == "saved"


# Verifies incomplete mail server settings are reported instead of a bare connection failure
def test_smtp_sign_in_reports_incomplete_settings(monkeypatch):
    monkeypatch.setattr(monitor, "smtp_connect_and_login", Mock(side_effect=AssertionError("connected")))
    monkeypatch.setattr(monitor, "SMTP_HOST", "your_smtp_server_ssl")

    with pytest.raises(monitor.RecoveryError) as error:
        monitor.smtp_sign_in("entered")

    assert "SMTP_HOST" in error.value.advice.detail


# Verifies Ctrl+C at the welcome offer reports one line instead of a traceback
def test_interrupting_the_welcome_offer_reports_a_cancellation(monkeypatch, capsys):
    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(builtins, "input", interrupt)
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda *args, **kwargs: pytest.fail("the wizard ran after being interrupted"))

    with pytest.raises(SystemExit) as exit_error:
        monitor._wizard_welcome()

    assert exit_error.value.code == 1
    assert "Setup cancelled." in capsys.readouterr().out


# Puts the wizard on the shortest path to the save, so a test can interrupt one chosen prompt
def install_saving_wizard_flow(monkeypatch, config_path, env_path, answers):
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(monitor, "_wizard_destinations", lambda config, env: (config_path, env_path))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "_wizard_choose_config_destination", lambda path: path)
    monkeypatch.setattr(monitor, "_wizard_collect_target_section", lambda state, target=None: setattr(state, "target", "target.user"))
    monkeypatch.setattr(monitor, "_wizard_collect_polling_section", lambda state: None)
    monkeypatch.setattr(monitor, "_wizard_collect_auth_section", lambda state, method: state.auth.update({"complete": True, "source": "existing SP_DC_COOKIE"}))
    monkeypatch.setattr(monitor, "_wizard_collect_email_section", lambda state: None)
    monkeypatch.setattr(monitor, "_wizard_collect_webhook_section", lambda state: None)
    monkeypatch.setattr(monitor, "_wizard_collect_output_section", lambda state: None)
    monkeypatch.setattr(monitor, "_wizard_review_setup", lambda state, method: True)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", Mock(side_effect=list(answers)))


# Verifies an interrupt before the save says the destination files are untouched
def test_interrupting_the_questions_reports_untouched_files(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.conf"
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(monitor, "_wizard_destinations", lambda config, env: (config_path, tmp_path / ".env"))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(builtins, "input", Mock(side_effect=KeyboardInterrupt))

    with pytest.raises(SystemExit) as error:
        monitor.run_setup_wizard()

    assert error.value.code == 1
    assert "Setup cancelled. Destination files were not changed." in capsys.readouterr().out
    assert not config_path.exists()


# Verifies an interrupt at the doctor offer reports the saved setup instead of a cancellation
def test_interrupting_the_doctor_offer_keeps_the_saved_setup(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.conf"
    install_saving_wizard_flow(monkeypatch, config_path, tmp_path / ".env", [KeyboardInterrupt, False])

    with pytest.raises(SystemExit) as error:
        monitor.run_setup_wizard()

    output = capsys.readouterr().out
    assert error.value.code == 0
    assert "Setup is saved. Use the commands below when ready." in output
    assert "Setup cancelled" not in output
    assert "Next steps" in output
    assert config_path.is_file()


# Verifies an interrupt at the launch offer reports the saved setup and points at the printed command
def test_interrupting_the_launch_offer_keeps_the_saved_setup(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.conf"
    install_saving_wizard_flow(monkeypatch, config_path, tmp_path / ".env", [True, KeyboardInterrupt])
    monkeypatch.setattr(monitor, "_wizard_load_effective_setup", lambda config, env: True)
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: 0)
    execv_mock = Mock()
    monkeypatch.setattr(monitor.os, "execv", execv_mock)

    with pytest.raises(SystemExit) as error:
        monitor.run_setup_wizard()

    output = capsys.readouterr().out
    assert error.value.code == 0
    assert "Setup is saved. Start monitoring with the command above when ready." in output
    assert "Setup cancelled" not in output
    execv_mock.assert_not_called()


# Verifies a prompt runs with Python's default Ctrl+C behavior, so the signal handler cannot pre-empt it
def test_prompts_restore_the_default_interrupt_handler(monkeypatch):
    observed = {}

    def answer(_prompt=""):
        observed["during"] = signal.getsignal(signal.SIGINT)
        return "value"

    monkeypatch.setattr(builtins, "input", answer)
    previous_handler = signal.signal(signal.SIGINT, monitor.signal_handler)
    try:
        assert monitor._wizard_input("Prompt: ") == "value"
        assert observed["during"] is signal.default_int_handler
        assert signal.getsignal(signal.SIGINT) is monitor.signal_handler
    finally:
        signal.signal(signal.SIGINT, previous_handler)


# Verifies a repeated operational notice such as a token refresh closes its own block once monitoring runs,
# and stays a bare line on the startup screen, where the monitoring header closes the block instead
def test_a_token_refresh_notice_closes_its_own_block_only_while_monitoring(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "HORIZONTAL_LINE", 10)
    monkeypatch.setattr(monitor, "MONITORING_ACTIVE", False)

    monitor.verbose_notice("Authentication token refreshed (cookie mode)")

    assert capsys.readouterr().out == "* Authentication token refreshed (cookie mode)\n"

    monitor.mark_monitoring_started()
    monitor.verbose_notice("Authentication token refreshed (cookie mode)")

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines[0] == "* Authentication token refreshed (cookie mode)"
    assert lines[1].startswith("Timestamp:")
    assert set(lines[2]) == {"─"}


# Verifies hidden prompts are colorized like the visible ones, so one question does not look different
def test_hidden_prompts_are_colorized_like_the_visible_ones(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)})
    prompts = []
    monkeypatch.setattr(monitor.getpass, "getpass", lambda prompt: prompts.append(prompt) or "secret")
    monkeypatch.setattr(builtins, "input", lambda prompt: prompts.append(prompt) or "")

    assert monitor._wizard_ask_secret("SMTP password") == "secret"
    assert monitor._wizard_input("Receiver email: ") == ""

    hidden_prompt, visible_prompt = prompts
    assert hidden_prompt == monitor.colorize("info", "SMTP password: ")
    assert hidden_prompt.startswith(visible_prompt[:visible_prompt.index("R")])
    assert hidden_prompt.endswith(monitor.ANSI_RESET)


# Verifies debug output is off while a hidden value is read and restored afterwards
def test_a_hidden_value_is_read_with_debug_output_off(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    seen = []
    monkeypatch.setattr(monitor.getpass, "getpass", lambda prompt: seen.append(monitor.DEBUG_MODE) or "secret")

    assert monitor._wizard_ask_secret("SMTP password") == "secret"
    assert monitor.read_secret_privately(lambda prompt: seen.append(monitor.DEBUG_MODE) or "value", "Enter it: ") == "value"
    assert seen == [False, False]
    assert monitor.DEBUG_MODE is True


# Verifies an interrupted entry reports the cancel itself, with the command that resumes it
def test_an_interrupted_secret_entry_reports_the_cancel(tmp_path, monkeypatch):
    destination = tmp_path / ".env"
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor@example.test")

    def interrupt(prompt=""):
        raise KeyboardInterrupt

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_smtp_password(env_file=destination, interactive=True, getpass_func=interrupt, sign_in=Mock(side_effect=AssertionError("signed in")))

    advice = raised.value.advice
    assert advice.summary == "SMTP password setup was cancelled and the dotenv file was not changed"
    assert "Run --set-smtp-password again when you have the value ready" in advice.fix
    assert monitor.SMTP_GUIDE_URL in advice.fix
    assert not destination.exists()


# Verifies a declined replacement reports the kept value rather than a cancelled entry
def test_a_declined_secret_replacement_reports_the_kept_value(tmp_path, monkeypatch):
    destination = tmp_path / ".env"
    destination.write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor@example.test")

    with pytest.raises(monitor.RecoveryError) as raised:
        monitor.run_set_smtp_password(env_file=destination, interactive=True, input_func=lambda prompt: "n", getpass_func=Mock(side_effect=AssertionError("hidden prompt used")))

    advice = raised.value.advice
    assert advice.summary == "The saved SMTP password was left as it is and the dotenv file was not changed"
    assert "answer y to replace the saved value" in advice.fix
    assert destination.read_text(encoding="utf-8") == 'SMTP_PASSWORD="original"\n'

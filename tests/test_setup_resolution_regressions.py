import copy

import pytest

import spotify_profile_monitor as monitor


@pytest.fixture(autouse=True)
# Keeps entry-point tests from leaking loaded configuration into later tests
def isolated_runtime(monkeypatch, tmp_path):
    for name, value in list(vars(monitor).items()):
        if name.isupper():
            monkeypatch.setattr(monitor, name, copy.copy(value) if isinstance(value, (dict, list, set)) else value)
    if hasattr(monitor, "SECRET_SOURCES"):
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    for key in monitor.SECRET_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("content", ["'SMTP_PASSWORD'='synthetic-old'\n", "export 'SMTP_PASSWORD'='xxxxxxxx\nxxxxxxxx'\n"])
# Quoted keys participate in both replacement confirmation and complete assignment updates
def test_quoted_saved_secret_is_detected_and_removed(tmp_path, content):
    path = tmp_path / "private.env"
    path.write_text(content + "KEEP=untouched\n", encoding="utf-8")
    assert monitor._dotenv_contains_key(path, "SMTP_PASSWORD")
    monitor.update_dotenv_file(path, {"SMTP_PASSWORD": ""})
    assert not monitor._dotenv_contains_key(path, "SMTP_PASSWORD")
    assert path.read_text(encoding="utf-8") == "KEEP=untouched\n"


# Explicit empty dotenv values override nonempty configuration values
def test_empty_saved_secret_overrides_configuration(monkeypatch, tmp_path):
    path = tmp_path / "private.env"
    path.write_text('SMTP_PASSWORD=""\n', encoding="utf-8")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "synthetic-config")
    assert monitor.effective_secret_after_setup("SMTP_PASSWORD", path, {}) == ("", False)


# Nonempty exported credentials override the saved value and any pending replacement
def test_exported_secret_keeps_precedence(monkeypatch, tmp_path):
    path = tmp_path / "private.env"
    path.write_text('SMTP_PASSWORD="synthetic-file"\n', encoding="utf-8")
    monkeypatch.setenv("SMTP_PASSWORD", "synthetic-export")
    if hasattr(monitor, "SECRET_SOURCES"):
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    if hasattr(monitor, "EXPORTED_SECRET_KEYS"):
        monkeypatch.setattr(monitor, "EXPORTED_SECRET_KEYS", frozenset({"SMTP_PASSWORD"}))
    assert monitor.effective_secret_after_setup("SMTP_PASSWORD", path, {"SMTP_PASSWORD": "synthetic-new"}) == ("synthetic-export", True)


# Recovery commands stay readable independently of the installation directory
def test_recovery_prefix_uses_short_names(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert monitor._wizard_local_command_args("manual") == ["python3", "spotify_profile_monitor.py"]
    assert monitor._wizard_local_command_args("pip") == ["spotify_profile_monitor"]


@pytest.mark.parametrize("setting", ["SPOTIFY_CHECK_INTERVAL", "LIVENESS_CHECK_INTERVAL"])
# The real CLI reaches Doctor's validation before attempting numeric startup arithmetic
def test_doctor_entry_point_reports_quoted_numbers(monkeypatch, tmp_path, setting):
    import sys
    config = tmp_path / "settings.conf"
    config.write_text(f'{setting} = "3600"\n', encoding="utf-8")
    labels = []

    # Captures the report configuration rows reached through normal startup
    def doctor(*args, **kwargs):
        labels.extend(check.label for check in monitor.doctor_check_configuration())
        return 1
    monkeypatch.setattr(sys, "argv", [monitor.__file__, "--doctor", "--config-file", str(config), "--env-file", "none"])
    monkeypatch.setattr(monitor, "run_doctor", doctor)
    with pytest.raises(SystemExit) as stopped:
        monitor.main()
    assert stopped.value.code == 1
    assert "One or more numeric settings are invalid" in labels


# Post-save loading and normal startup agree on explicit empty credentials
def test_post_save_and_startup_resolve_empty_credentials_identically(monkeypatch, tmp_path):
    import sys
    config = tmp_path / "settings.conf"
    env = tmp_path / "private.env"
    config.write_text('SP_DC_COOKIE="synthetic-config"\nSMTP_PASSWORD="synthetic-config"\n', encoding="utf-8")
    env.write_text('SP_DC_COOKIE=""\nSMTP_PASSWORD=""\n', encoding="utf-8")
    for key in ("SP_DC_COOKIE", "SMTP_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    assert monitor._wizard_load_effective_setup(config, env)
    after_save = (monitor.SP_DC_COOKIE, monitor.SMTP_PASSWORD)
    resolved = []

    # Records values after the real startup resolver reaches Doctor
    def doctor(*args, **kwargs):
        resolved.append((monitor.SP_DC_COOKIE, monitor.SMTP_PASSWORD))
        return 0
    monkeypatch.setattr(sys, "argv", [monitor.__file__, "--doctor", "--config-file", str(config), "--env-file", str(env)])
    monkeypatch.setattr(monitor, "run_doctor", doctor)
    with pytest.raises(SystemExit):
        monitor.main()
    assert after_save == resolved[0] == ("", "")


# A quoted saved password must still allow the operator to decline its replacement
def test_quoted_password_replacement_can_be_declined(monkeypatch, tmp_path):
    path = tmp_path / "private.env"
    original = "'SMTP_PASSWORD'='synthetic-original'\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "synthetic-user")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "sender@example.test")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "receiver@example.test")
    prompted = []

    # Declines the actual replacement prompt before any new password is collected
    def decline(prompt):
        prompted.append(prompt)
        return "n"
    with pytest.raises(monitor.RecoveryError):
        monitor.run_set_smtp_password(env_file=path, interactive=True, input_func=decline, getpass_func=lambda prompt: pytest.fail("No password should be collected"), sign_in=lambda *args, **kwargs: pytest.fail("No sign-in should be attempted"))
    assert len(prompted) == 1
    assert path.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("override", [False, True])
# Setup resolves the selected file before offering saved answers or looking for credentials
def test_setup_keeps_saved_dotenv_destination(monkeypatch, tmp_path, override):
    import sys
    config = tmp_path / "settings.conf"
    saved = tmp_path / "saved.env"
    explicit = tmp_path / "explicit.env"
    saved.write_text('SMTP_PASSWORD="synthetic-saved"\n', encoding="utf-8")
    explicit.write_text('SMTP_PASSWORD="synthetic-explicit"\n', encoding="utf-8")
    config.write_text(f"DOTENV_FILE={str(saved)!r}\nDISABLE_LOGGING=True\n", encoding="utf-8")
    recorded = []

    class Captured(BaseException):
        pass

    # Stops at the first section after destination and baseline resolution
    def collect(state, *args, **kwargs):
        recorded.append((state.env_path, state.config_values["DISABLE_LOGGING"]))
        raise Captured
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(monitor, "_wizard_choose_config_destination", lambda *args, **kwargs: config)
    monkeypatch.setattr(monitor, "_wizard_collect_target_section", collect)
    with pytest.raises(Captured):
        monitor.run_setup_wizard(config_file=config, env_file=explicit if override else None)
    assert recorded == [(explicit if override else saved, True)]

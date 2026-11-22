"""Generated commands retain executable arguments while diagnostics keep secrets hidden."""

import pytest

import spotify_profile_monitor as monitor


COMMAND = 'spotify_profile_monitor --doctor account-name --config-file "C:\\Profiles\\account-name.conf" --env-file "C:\\Profiles\\account-name.env"'


@pytest.fixture
# Configures a credential that also occurs in otherwise valid command arguments
def command_collision(monkeypatch):
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "account-name")
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False, raising=False)
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0, raising=False)
    return monitor.make_recovery_advice("unknown", "Server rejected account-name", "Run: " + COMMAND, False, "SMTP_PASSWORD=account-name")


@pytest.mark.parametrize("surface", ["recovery", "doctor"])
# Keeps paths and targets intact without exposing the matching credential in diagnostic fields
def test_generated_command_survives_redaction(command_collision, surface, capsys):
    advice = command_collision
    if surface == "recovery":
        print(monitor.render_recovery_advice(advice, debug=True))
    else:
        report = monitor.DoctorReport()
        report.checks.append(monitor.make_doctor_check(monitor.DOCTOR_SECTIONS[0], "FAIL", advice.summary, advice.detail, advice))
        rendered = monitor.render_doctor_sections(report)
        if rendered is not None:
            print(rendered)
    output = capsys.readouterr().out
    assert COMMAND in output
    assert "Server rejected account-name" not in output
    assert "SMTP_PASSWORD=account-name" not in output


# Keeps serialized secret assignments hidden independently of any generated command
def test_raw_diagnostics_still_redact_credentials(monkeypatch):
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "account-name")
    output = monitor.sanitize_error_text("SMTP_PASSWORD=account-name")
    assert "account-name" not in output

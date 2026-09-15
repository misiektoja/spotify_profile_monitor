import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from dotenv import dotenv_values

import spotify_profile_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "private_sp_dc_test_artifacts"


# Creates one disposable private-cookie test directory under the project local directory
def make_test_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=str(ARTIFACT_ROOT))


# Verifies private cookie entry requires a TTY and a writable dotenv destination
def test_set_sp_dc_requires_safe_persistence():
    with pytest.raises(monitor.SpDcConfigurationError, match="interactive terminal"):
        monitor.run_set_sp_dc(interactive=False, getpass_func=Mock(side_effect=AssertionError("prompted")))
    with pytest.raises(monitor.SpDcConfigurationError, match="requires a dotenv destination"):
        monitor.run_set_sp_dc(env_file="none", interactive=True, getpass_func=Mock(side_effect=AssertionError("prompted")))


# Verifies private cookie setup validates before replacing only SP_DC_COOKIE
def test_set_sp_dc_validates_and_updates_only_cookie(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        destination.write_text("# keep\nUNRELATED=stay\nSP_DC_COOKIE=old-value\n", encoding="utf-8")
        secret = "new-private-sp-dc"
        validator = Mock(return_value=True)
        monkeypatch.setattr(monitor, "validate_sp_dc_cookie", validator)
        result = monitor.run_set_sp_dc(env_file=destination, interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: secret)
        output = capsys.readouterr().out
        assert result == str(destination.resolve())
        assert destination.read_text(encoding="utf-8").startswith("# keep\nUNRELATED=stay\n")
        assert dotenv_values(str(destination), interpolate=False) == {"UNRELATED": "stay", "SP_DC_COOKIE": secret}
        assert secret not in output
        validator.assert_called_once_with(secret)


# Verifies rejected cookie validation leaves the dotenv file unchanged without exposing the value
def test_set_sp_dc_rejects_invalid_cookie_without_write(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        destination.write_text("UNRELATED=stay\n", encoding="utf-8")
        original_content = destination.read_text(encoding="utf-8")
        secret = "rejected-private-sp-dc"
        monkeypatch.setattr(monitor, "validate_sp_dc_cookie", Mock(side_effect=monitor.SpDcConfigurationError("Spotify authentication rejected the entered sp_dc cookie. The private settings file was not changed.")))
        with pytest.raises(monitor.SpDcConfigurationError) as error:
            monitor.run_set_sp_dc(env_file=destination, interactive=True, getpass_func=lambda prompt: secret)
        assert destination.read_text(encoding="utf-8") == original_content
        assert secret not in capsys.readouterr().out
        assert secret not in str(error.value)


# Verifies cookie validation restores temporary runtime settings after success
def test_validate_sp_dc_cookie_restores_runtime_settings(monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "client")
    monkeypatch.setattr(monitor, "USER_AGENT", "")
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monkeypatch.setattr(monitor, "get_random_user_agent", Mock(return_value="validation-agent"))
    refresh = Mock(return_value={"access_token": "validated-token", "client_id": "validated-client"})
    validity = Mock(return_value=True)
    monkeypatch.setattr(monitor, "refresh_access_token_from_sp_dc", refresh)
    monkeypatch.setattr(monitor, "check_token_validity", validity)
    assert monitor.validate_sp_dc_cookie("private-sp-dc") is True
    refresh.assert_called_once_with("private-sp-dc")
    validity.assert_called_once_with("validated-token", "validated-client", "validation-agent")
    assert monitor.TOKEN_SOURCE == "client"
    assert monitor.USER_AGENT == ""
    assert monitor.DEBUG_MODE is True


# Verifies the replace question names the secret the way every sibling one-shot command names its own
def test_set_sp_dc_replace_question_uses_the_shared_wording(monkeypatch):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        destination.write_text("SP_DC_COOKIE=old-value\n", encoding="utf-8")
        prompts = []
        monkeypatch.setattr(monitor, "validate_sp_dc_cookie", Mock(return_value=True))

        monitor.run_set_sp_dc(env_file=destination, interactive=True, input_func=lambda prompt: prompts.append(prompt) or "y", getpass_func=lambda prompt: "new-private-sp-dc")

        assert prompts == [f"Replace the saved Spotify cookie in '{destination.resolve()}'? [y/N]: "]


# Verifies a secret cleared by its owner leaves the file rather than staying behind as an empty value
def test_a_cleared_secret_is_removed_rather_than_emptied():
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        destination.write_text('UNRELATED=stay\nNTFY_ACCESS_TOKEN="tk_old"\n', encoding="utf-8")

        monitor.update_dotenv_file(destination, {"NTFY_ACCESS_TOKEN": ""})

        assert "NTFY_ACCESS_TOKEN" not in destination.read_text(encoding="utf-8")
        assert dotenv_values(destination, interpolate=False) == {"UNRELATED": "stay"}


# Verifies clearing a secret the file never held does not add an empty line for it
def test_clearing_an_absent_secret_writes_nothing():
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        destination.write_text("UNRELATED=stay\n", encoding="utf-8")

        monitor.update_dotenv_file(destination, {"NTFY_ACCESS_TOKEN": ""})

        assert destination.read_text(encoding="utf-8") == "UNRELATED=stay\n"


# Verifies an assignment the owner exported keeps its export, since dropping it changes what a shell sourcing the file exports
def test_an_exported_assignment_keeps_its_export(tmp_path):
    destination = tmp_path / ".env"
    destination.write_text('export SMTP_PASSWORD="old"\nOTHER=keep\n', encoding="utf-8")

    monitor.update_dotenv_file(destination, {"SMTP_PASSWORD": "new"})

    assert destination.read_text(encoding="utf-8") == 'export SMTP_PASSWORD="new"\nOTHER=keep\n'


# Verifies a line break inside a value is escaped rather than written through, since a raw one would split the assignment
def test_a_line_break_in_a_value_cannot_split_the_assignment(tmp_path):
    destination = tmp_path / ".env"

    monitor.update_dotenv_file(destination, {"SMTP_PASSWORD": "one\ntwo"})

    assert destination.read_text(encoding="utf-8") == 'SMTP_PASSWORD="one\\ntwo"\n'


# Verifies the writer refuses a key this tool does not ship, so a typo cannot put an unknown name in the private file
def test_the_writer_refuses_a_key_this_tool_does_not_ship(tmp_path):
    with pytest.raises(ValueError):
        monitor.update_dotenv_file(tmp_path / ".env", {"NOT_A_SECRET": "value"})


# Verifies the writer refuses a value that is not text, so a mistyped caller fails before the file is touched
def test_the_writer_refuses_a_value_that_is_not_text(tmp_path):
    with pytest.raises(TypeError):
        monitor.update_dotenv_file(tmp_path / ".env", {"SMTP_PASSWORD": 1234})

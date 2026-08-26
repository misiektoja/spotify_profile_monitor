from io import StringIO
from unittest.mock import Mock

import requests
import spotify_profile_monitor as monitor


# Provides one in-memory stream that behaves like an interactive terminal
class TTYBuffer(StringIO):
    def isatty(self):
        return True


# Verifies Doctor classifies supported Python and missing dependencies
def test_doctor_environment_checks_python_and_dependencies():
    finder = lambda name: object() if name != "pyotp" else None

    checks = monitor.doctor_check_environment((3, 12, 1), finder)

    assert any(check.status == "PASS" and "Python 3.12.1" in check.label for check in checks)
    assert any(check.status == "FAIL" and "pyotp" in check.label for check in checks)


# Verifies Chromium dependency guidance explicitly preserves Firefox import support
def test_doctor_explains_browser_import_dependency_scope():
    checks = monitor.doctor_check_environment((3, 12, 1), lambda name: object())
    check = next(item for item in checks if "pycookiecheat" in item.label)

    assert check.status == "PASS"
    assert check.detail == "Used only for importing cookies from Chromium-based browsers. Firefox cookie import does not need it"


# Pillow moved to an optional extra, so a missing copy must never be reported as a broken installation
def test_doctor_treats_missing_artwork_support_as_optional():
    checks = monitor.doctor_check_environment((3, 12, 1), lambda name: None if name == "PIL" else object())

    assert not any(check.status == "FAIL" and "Pillow" in check.label for check in checks)
    check = next(item for item in checks if "Pillow" in item.label)
    assert check.status == "WARN"
    # The rendered command follows the entry point, so assert the part that holds either way
    assert "-m pip install" in check.detail and "Normal monitoring is unaffected" in check.detail


# A user who turned artwork on needs to be told the alerts are silently text-only until Pillow is installed
def test_doctor_artwork_detail_follows_the_image_settings(monkeypatch):
    monkeypatch.setattr(monitor, "EMAIL_IMAGES", False)
    monkeypatch.setattr(monitor, "NTFY_IMAGES", False)
    assert "currently disabled" in monitor.doctor_notification_images_detail()

    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    assert "text-only until Pillow is installed" in monitor.doctor_notification_images_detail()


# Verifies Doctor omits the internal separator resolution for valid settings
def test_doctor_omits_valid_ascii_separator_resolution(monkeypatch):
    monkeypatch.setattr(monitor, "ASCII_LOG_SEPARATORS", "Auto")

    checks = monitor.doctor_check_configuration()

    assert not any("ASCII_LOG_SEPARATORS" in check.label for check in checks)


# Verifies Doctor still reports an invalid separator setting
def test_doctor_reports_invalid_ascii_separator_setting(monkeypatch):
    monkeypatch.setattr(monitor, "ASCII_LOG_SEPARATORS", "invalid")

    checks = monitor.doctor_check_configuration()

    assert any(check.status == "FAIL" and check.label == "ASCII_LOG_SEPARATORS is invalid" for check in checks)


# Verifies Doctor keeps trusted redraw controls when stdout has the runtime sanitizer wrapper
def test_doctor_progress_redraws_through_terminal_stream(monkeypatch):
    terminal = TTYBuffer()
    monkeypatch.setattr(monitor.sys, "stdout", monitor.TerminalStream(terminal))

    monitor._doctor_progress("Spotify authentication")
    authentication = "* Checking Spotify authentication ..."
    assert terminal.getvalue() == "\r" + authentication

    monitor._doctor_progress("metadata")
    metadata = "* Checking metadata ..."
    assert terminal.getvalue() == "\r" + authentication + "\r" + (" " * len(authentication)) + "\r" + "\r" + metadata

    monitor._doctor_progress_clear()
    assert terminal.getvalue().endswith("\r" + metadata + "\r" + (" " * len(metadata)) + "\r")


# Verifies missing cookie authentication remains actionable and secret-safe
def test_doctor_reports_missing_cookie(monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "your_sp_dc_cookie_value")
    report = monitor.DoctorReport()

    checks = monitor.doctor_check_authentication(report)

    assert checks[0].status == "FAIL"
    assert "SP_DC_COOKIE" in checks[0].detail
    assert "--import-browser-cookie" in checks[0].fix


# Verifies successful authentication is reused for one live target check
def test_doctor_reuses_access_token_for_target(monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "doctor_acquire_access_token", Mock(return_value="access-token"))
    profile_request = Mock(return_value={"sp_username": "Target"})
    monkeypatch.setattr(monitor, "spotify_get_user_info", profile_request)
    report = monitor.DoctorReport()

    auth_checks = monitor.doctor_check_authentication(report)
    target_checks = monitor.doctor_check_target(report, "spotify:user:target.user")

    assert auth_checks[0].status == "PASS"
    assert target_checks[0].status == "PASS"
    profile_request.assert_called_once_with("access-token", "target.user", False, 0)


# Verifies cookie target checks do not evaluate OAuth-only timestamps with an unresolved automatic timezone
def test_cookie_target_check_does_not_require_resolved_timezone(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {"name": "sara", "followers_count": 1, "following_count": 2}
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Auto")
    monkeypatch.setattr(monitor, "now_local", Mock(side_effect=AssertionError("timezone should not be read")))
    monkeypatch.setattr(monitor.SESSION, "get", Mock(return_value=response))

    profile = monitor.spotify_get_user_info("access-token", "sq58", False, 0)

    assert profile["sp_username"] == "sara"
    response.raise_for_status.assert_called_once_with()


# Verifies Doctor does not describe an internal target-check failure as a missing Spotify profile
def test_doctor_target_preserves_non_target_failure(monkeypatch):
    monkeypatch.setattr(monitor, "spotify_get_user_info", Mock(side_effect=KeyError("Auto")))
    report = monitor.DoctorReport(access_token="access-token")

    check = monitor.doctor_check_target(report, "sq58")[0]

    assert check.status == "FAIL"
    assert check.label == "An unexpected error occurred"
    assert check.advice is not None and check.advice.code == "unknown"
    assert "confirm it still exists" not in check.fix


# Verifies Doctor still gives profile-specific recovery for a real Spotify HTTP 404
def test_doctor_target_classifies_http_404_as_not_found(monkeypatch):
    response = Mock(status_code=404)
    error = requests.HTTPError("404 Client Error", response=response)
    monkeypatch.setattr(monitor, "spotify_get_user_info", Mock(side_effect=error))
    report = monitor.DoctorReport(access_token="access-token")

    check = monitor.doctor_check_target(report, "missing.user")[0]

    assert check.status == "FAIL"
    assert check.label == "The Spotify target could not be loaded"
    assert check.advice is not None and check.advice.code == "target.not_found"
    assert "https://open.spotify.com/user/missing.user" in check.fix


# Verifies an authentication-mode restriction is not described as a missing Spotify profile
def test_doctor_target_classifies_authentication_mode_restriction(monkeypatch):
    error = ValueError("Cannot monitor user 'sq58' with 'oauth_app' token source")
    monkeypatch.setattr(monitor, "spotify_get_user_info", Mock(side_effect=error))
    report = monitor.DoctorReport(access_token="access-token")

    check = monitor.doctor_check_target(report, "sq58")[0]

    assert check.status == "FAIL"
    assert check.label == "The selected authentication mode cannot load this profile"
    assert check.advice is not None and check.advice.code == "auth.rejected"
    assert "cookie or client" in check.fix


# Verifies Doctor resolves the automatic timezone instead of accepting it without checking
def test_doctor_configuration_resolves_auto_timezone(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Auto")
    monkeypatch.setattr(monitor, "get_localzone", Mock(return_value="Europe/Warsaw"))

    checks = monitor.doctor_check_configuration()

    assert any(check.status == "PASS" and check.label == "LOCAL_TIMEZONE Auto resolves to Europe/Warsaw" for check in checks)


# Verifies Doctor checks the final target-specific log filename
def test_doctor_configuration_uses_final_target_log_path(monkeypatch):
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
    monkeypatch.setattr(monitor, "SP_LOGFILE", "spotify_profile_monitor")
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "")

    checks = monitor.doctor_check_configuration(target_value="https://open.spotify.com/user/sq58")
    check = next(item for item in checks if item.label == "Log destination appears writable")

    assert check.detail == "Path: spotify_profile_monitor_sq58.log"


# Verifies a custom suffix and explicit extension use the runtime naming rules
def test_build_log_path_preserves_custom_suffix_and_explicit_filename(monkeypatch):
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
    monkeypatch.setattr(monitor, "SP_LOGFILE", "logs/profile")
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "friends")

    checks = monitor.doctor_check_configuration(target_value="sq58")
    check = next(item for item in checks if item.label == "Log destination appears writable")

    assert check.detail == "Path: logs/profile_friends.log"
    assert monitor.build_log_path("logs/fixed.log", "sq58") == monitor.Path("logs/fixed.log")


# Verifies Doctor renders sections and recovery lines without secrets
def test_doctor_report_rendering_redacts_secrets(monkeypatch):
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "COOKIE-SECRET-SENTINEL")
    report = monitor.DoctorReport(checks=[monitor.make_doctor_check("Authentication", "FAIL", "Spotify authentication failed", "cookie=COOKIE-SECRET-SENTINEL", "Import again")])

    rendered = monitor.render_doctor_report(report)

    assert "Authentication" in rendered
    assert "[FAIL] Spotify authentication failed" in rendered
    assert "To fix: Import again" in rendered
    assert "COOKIE-SECRET-SENTINEL" not in rendered


# Verifies Doctor visually attaches explanatory details to their check rows
def test_doctor_report_indents_check_details():
    report = monitor.DoctorReport(checks=[monitor.make_doctor_check("Configuration", "PASS", "Log destination appears writable", "Path: spotify_profile_monitor")])

    rendered = monitor.render_doctor_report(report)

    assert "[PASS] Log destination appears writable\n  Path: spotify_profile_monitor" in rendered


# Verifies disabled notifications cause no network delivery attempts
def test_doctor_disabled_notifications_are_passive(monkeypatch):
    monkeypatch.setattr(monitor, "PROFILE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    smtp = Mock(side_effect=AssertionError("SMTP called"))
    webhook = Mock(side_effect=AssertionError("webhook called"))
    monkeypatch.setattr(monitor, "smtp_connect_and_login", smtp)
    monkeypatch.setattr(monitor, "send_webhook", webhook)

    checks = monitor.doctor_check_notifications()

    assert [check.status for check in checks] == ["PASS", "PASS"]
    smtp.assert_not_called()
    webhook.assert_not_called()


# Verifies malformed configuration reports its syntax line to Doctor
def test_load_config_reports_syntax_line(tmp_path):
    config_path = tmp_path / "broken.conf"
    config_path.write_text("TOKEN_SOURCE =\n", encoding="utf-8")
    errors = []

    loaded = monitor.load_config_file(config_path, namespace={}, error_out=errors, report_errors=False)

    assert loaded is False
    assert errors[0].status == "FAIL"
    assert "line 1" in errors[0].detail

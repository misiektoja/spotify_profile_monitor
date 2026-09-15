from io import StringIO
from unittest.mock import Mock

import inspect
import pytest

import requests
import spotify_profile_monitor as monitor


# Provides one in-memory stream that behaves like an interactive terminal


# Composes the two renderers the way run_doctor does, so a test can assert on the whole transcript
def render_doctor_report(report):
    return monitor.render_doctor_sections(report) + "\n" + monitor.render_doctor_summary(report.checks)


# Builds the minimal action a WARN or FAIL row is required to carry
def actionable_advice():
    return monitor.make_recovery_advice("config.invalid", "a label", "do the thing", False)
class TTYBuffer(StringIO):
    def isatty(self):
        return True


# Verifies Doctor classifies supported Python and missing dependencies
def test_doctor_environment_checks_python_and_dependencies():
    finder = lambda name: object() if name != "pyotp" else None

    checks = monitor.doctor_check_environment((3, 12, 1), finder)

    assert any(check.status == "PASS" and "Python 3.12.1" in check.label for check in checks)
    assert any(check.status == "FAIL" and "pyotp" in check.label for check in checks)
    assert not any(check.label.startswith("Install method") for check in checks)


# Verifies Chromium dependency guidance explicitly preserves Firefox import support
def test_doctor_explains_browser_import_dependency_scope():
    checks = monitor.doctor_check_environment((3, 12, 1), lambda name: object())
    check = next(item for item in checks if "pycookiecheat" in item.label)

    assert check.status == "PASS"
    assert check.detail == "Used only for importing cookies from Chromium-based browsers. Firefox cookie import does not need it"


# Verifies a warning about a library that cannot affect this machine is not shown at all
@pytest.mark.parametrize("system, reported", [("Windows", True), ("Linux", False), ("Darwin", False)])
def test_a_platform_specific_dependency_is_only_reported_where_it_applies(monkeypatch, system, reported):
    monkeypatch.setattr(monitor.platform, "system", lambda: system)

    checks = monitor.doctor_check_environment((3, 12, 1), lambda name: None)

    assert any("colorama" in check.label for check in checks) is reported


# Verifies the Windows colour library is reported there, so broken colours on that platform have a diagnostic
def test_missing_colorama_is_reported_on_windows(monkeypatch):
    monkeypatch.setattr(monitor.platform, "system", lambda: "Windows")

    checks = monitor.doctor_check_environment((3, 12, 1), lambda name: None if name == "colorama" else object())

    missing = next(check for check in checks if "colorama" in check.label)
    assert missing.status == "WARN"
    assert "Coloured output may not render in the classic Windows Command Prompt" in missing.detail
    assert "Windows Terminal, which needs nothing extra" in missing.advice.fix


# Pillow moved to an optional extra, so a missing copy must never be reported as a broken installation
def test_doctor_treats_missing_artwork_support_as_optional():
    checks = monitor.doctor_check_environment((3, 12, 1), lambda name: None if name == "PIL" else object())

    assert not any(check.status == "FAIL" and "Pillow" in check.label for check in checks)
    check = next(item for item in checks if "Pillow" in item.label)
    assert check.status == "WARN"
    # The rendered command follows the entry point, so assert the part that holds either way
    assert "-m pip install" in check.advice.fix and "Every other feature is unaffected" in check.detail


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
    assert "--import-browser-cookie" in checks[0].advice.fix


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
    profile_request.assert_called_once_with("access-token", "target.user", True, 0)


# Verifies the connectivity and target rows skipped for the same missing token name that cause without a fix line
def test_skipped_connectivity_and_target_rows_name_the_same_cause(monkeypatch):
    monkeypatch.setattr(monitor, "doctor_connectivity_endpoint_check", lambda: monitor.make_doctor_check("Connectivity", "PASS", "Endpoint answered"))
    report = monitor.DoctorReport()

    connectivity_skip = monitor.doctor_check_connectivity(report)[-1]
    target_skip = monitor.doctor_check_target(report, "spotify:user:target.user")[0]

    assert connectivity_skip.status == target_skip.status == "SKIP"
    assert connectivity_skip.label == "Spotify connectivity was not checked"
    assert target_skip.label == "The monitored profile was not checked"
    assert connectivity_skip.detail == "Authentication did not succeed, so no request was attempted"
    assert target_skip.detail == "Authentication did not succeed, so no lookup was attempted"
    assert connectivity_skip.advice is None and target_skip.advice is None


# Verifies Doctor tests legacy OAuth against the target playlist endpoint instead of token issuance alone
def test_doctor_checks_legacy_metadata_with_target_playlist(monkeypatch):
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "legacy-client")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "legacy-secret")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_oauth_app", Mock(return_value="legacy-token"))
    metadata_request = Mock(return_value={"sp_playlist_name": "Playlist"})
    monkeypatch.setattr(monitor, "_spotify_get_playlist_info_api", metadata_request)
    report = monitor.DoctorReport(target_profile={"sp_user_public_playlists_uris": [{"uri": "spotify:playlist:playlist123"}]})

    check = monitor.doctor_check_optional_oauth(report)[0]

    assert check.status == "PASS"
    assert check.label == "Legacy OAuth playlist metadata access succeeded"
    metadata_request.assert_called_once_with("legacy-token", "spotify:playlist:playlist123", False, oauth_app=True)


# Verifies Doctor explains when token issuance succeeds but Spotify rejects actual playlist metadata
def test_doctor_warns_when_legacy_token_cannot_read_playlist_metadata(monkeypatch):
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "legacy-client")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "legacy-secret")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_oauth_app", Mock(return_value="legacy-token"))
    response = Mock(status_code=403)
    monkeypatch.setattr(monitor, "_spotify_get_playlist_info_api", Mock(side_effect=requests.HTTPError("403 Client Error", response=response)))
    report = monitor.DoctorReport(target_profile={"sp_user_public_playlists_uris": [{"uri": "spotify:playlist:playlist123"}]})

    check = monitor.doctor_check_optional_oauth(report)[0]

    assert check.status == "WARN"
    assert check.label == "Legacy OAuth token issued, but playlist metadata access is unavailable"
    assert "Normal monitoring will use the web-player backend" in check.detail


# Verifies Doctor does not claim playlist compatibility when the target has nothing available to probe
def test_doctor_marks_unchecked_legacy_playlist_access(monkeypatch):
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "legacy-client")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "legacy-secret")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_oauth_app", Mock(return_value="legacy-token"))

    check = monitor.doctor_check_optional_oauth(monitor.DoctorReport(target_profile={"sp_user_public_playlists_uris": []}))[0]

    assert check.status == "WARN"
    assert check.label == "Legacy OAuth token issued, but playlist access was not checked"


# Verifies Doctor does not claim token issuance when the credential exchange itself fails
def test_doctor_preserves_legacy_token_failure_label(monkeypatch):
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "legacy-client")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "legacy-secret")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_oauth_app", Mock(side_effect=RuntimeError("invalid_client")))

    check = monitor.doctor_check_optional_oauth(monitor.DoctorReport())[0]

    assert check.status == "WARN"
    assert check.label == "Legacy OAuth metadata access is unavailable"


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
    assert "confirm it still exists" not in check.advice.fix


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
    assert "https://open.spotify.com/user/missing.user" in check.advice.fix


# Verifies an authentication-mode restriction is not described as a missing Spotify profile
def test_doctor_target_classifies_authentication_mode_restriction(monkeypatch):
    error = ValueError("Cannot monitor user 'sq58' with 'oauth_app' token source")
    monkeypatch.setattr(monitor, "spotify_get_user_info", Mock(side_effect=error))
    report = monitor.DoctorReport(access_token="access-token")

    check = monitor.doctor_check_target(report, "sq58")[0]

    assert check.status == "FAIL"
    assert check.label == "The selected authentication mode cannot load this profile"
    assert check.advice is not None and check.advice.code == "auth.rejected"
    assert "cookie or client" in check.advice.fix


# Verifies Doctor reports the automatic timezone the shared resolver settled on rather than the literal Auto value
def test_doctor_configuration_resolves_auto_timezone(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Auto")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE_STATE", "config")
    monkeypatch.setattr(monitor, "get_localzone", Mock(return_value="Europe/Warsaw"))

    checks = monitor.doctor_check_configuration(timezone_advice=monitor.resolve_local_timezone())

    assert any(check.status == "PASS" and check.label == "Local timezone can be detected" and check.detail == "Time zone: Europe/Warsaw" for check in checks)


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


# Verifies Doctor checks the configured JSON history directory without creating it
def test_doctor_checks_json_directory_without_writing(tmp_path, monkeypatch):
    json_dir = tmp_path / "missing" / "json"
    monkeypatch.setattr(monitor, "JSON_DIR", str(json_dir))

    checks = monitor.doctor_check_configuration(target_value="sq58")
    check = next(item for item in checks if item.label == "JSON directory appears writable")

    assert check.detail == f"Path: {json_dir}"
    assert not json_dir.exists()


# Verifies Doctor renders sections and recovery lines without secrets
def test_doctor_report_rendering_redacts_secrets(monkeypatch):
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "COOKIE-SECRET-SENTINEL")
    report = monitor.DoctorReport(checks=[monitor.make_doctor_check("Authentication", "FAIL", "Spotify authentication failed", "cookie=COOKIE-SECRET-SENTINEL", monitor.make_recovery_advice("auth.cookie_invalid", "Spotify authentication failed", "Import again", False))])

    rendered = render_doctor_report(report)

    assert "Authentication" in rendered
    assert "[FAIL] Spotify authentication failed" in rendered
    assert "To fix: Import again" in rendered
    assert "COOKIE-SECRET-SENTINEL" not in rendered


# Verifies the preflight notice reaches the user before any check runs rather than inside the report
def test_doctor_preflight_notice_precedes_the_report(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "build_doctor_report", lambda *args, **kwargs: monitor.DoctorReport(checks=[monitor.make_doctor_check("Environment", "PASS", "ok")]))
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: False))

    monitor.run_doctor()

    output = capsys.readouterr().out
    assert "Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval." in output
    assert output.index("Running preflight checks.") < output.index("Doctor\n")


# Verifies the install method is stated as context instead of a check that can never fail
def test_doctor_report_states_the_install_method_without_a_marker():
    report = monitor.DoctorReport(checks=[monitor.make_doctor_check("Environment", "PASS", "Python 3.12.1 is supported")])

    rendered = render_doctor_report(report)

    assert f"Doctor\nDetected install method: {monitor._wizard_install_method()}\n" in rendered
    assert "[PASS] Install method" not in rendered


# Verifies disabled output destinations are stated rather than left out of the report
def test_doctor_names_disabled_output_destinations(monkeypatch):
    monkeypatch.setattr(monitor, "CSV_FILE", "")
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", True)

    checks = monitor.doctor_check_configuration()

    rows = {(check.status, check.label, check.detail) for check in checks}
    # The labels say everything, so neither row carries a detail that only repeats them
    assert ("PASS", "CSV logging is disabled", "") in rows
    assert ("PASS", "Output logging is disabled", "") in rows


# Verifies Doctor visually attaches explanatory details to their check rows
def test_doctor_report_indents_check_details():
    report = monitor.DoctorReport(checks=[monitor.make_doctor_check("Configuration", "PASS", "Log destination appears writable", "Path: spotify_profile_monitor")])

    rendered = render_doctor_report(report)

    assert "[PASS] Log destination appears writable\n  Path: spotify_profile_monitor" in rendered


# Verifies the delivery-test gate still recognizes the readiness check once its label names the provider
def test_delivery_gate_matches_the_provider_named_label(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    label = f"{monitor.WEBHOOK_READY_CHECK_LABEL} for {monitor.webhook_provider_display_name()}"
    assert label.endswith("for Discord")
    report = monitor.DoctorReport(checks=[monitor.make_doctor_check("Notifications", "PASS", label)])
    consent = Mock(return_value=False)
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor.sys, "stdout", Mock(isatty=lambda: True, write=lambda *args: None, flush=lambda: None))
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", consent)

    monitor._doctor_offer_notification_tests(report)

    assert consent.call_count == 1
    assert "Send one test webhook through Discord now?" in consent.call_args[0][0]


# Verifies the delivery rows print the same label and detail the sibling tools print
def test_the_delivery_rows_print_the_shared_label_and_detail(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    email_label = monitor.SMTP_READY_CHECK_LABEL
    webhook_label = f"{monitor.WEBHOOK_READY_CHECK_LABEL} for {monitor.webhook_provider_display_name()}"
    report = monitor.DoctorReport(checks=[monitor.make_doctor_check("Notifications", "PASS", email_label), monitor.make_doctor_check("Notifications", "PASS", webhook_label)])
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", lambda question: "webhook" not in question)
    monkeypatch.setattr(monitor, "send_email", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "send_webhook", Mock(side_effect=AssertionError("webhook sent without approval")))

    monitor._doctor_offer_notification_tests(report)
    output = capsys.readouterr().out

    assert "Optional delivery tests" in output
    assert "[PASS] Doctor test email delivered" in output
    assert "  One real test email was sent after confirmation" in output
    assert "[SKIP] Test webhook through Discord was not sent" in output
    assert "  You declined the real delivery test. Run doctor again and approve the webhook test when ready" in output


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


# Exported secrets are a documented alternative to a dotenv file, so they must apply when no file is loaded
def test_environment_secrets_apply_without_a_dotenv_file(monkeypatch):
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor", "--doctor", "--env-file", "none"])
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "", raising=False)
    monkeypatch.setenv("NTFY_ACCESS_TOKEN", "tk_from_environment")

    with pytest.raises(SystemExit):
        monitor.main()

    assert monitor.NTFY_ACCESS_TOKEN == "tk_from_environment"


# Exported values win over duplicate dotenv keys and retain their effective source
def test_environment_secret_wins_over_duplicate_dotenv_key(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("NTFY_ACCESS_TOKEN=tk_from_file\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor", "--doctor", "--env-file", str(env_file)])
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {}, raising=False)
    monkeypatch.setenv("NTFY_ACCESS_TOKEN", "tk_from_environment")

    with pytest.raises(SystemExit):
        monitor.main()

    assert monitor.NTFY_ACCESS_TOKEN == "tk_from_environment"
    assert monitor.SECRET_SOURCES["NTFY_ACCESS_TOKEN"] == "environment"


# An empty export is a shell-profile leftover rather than a value, so it neither blocks nor blanks the dotenv value
def test_an_empty_export_does_not_shadow_the_dotenv_value(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("NTFY_ACCESS_TOKEN=tk_from_file\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor", "--doctor", "--env-file", str(env_file)])
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {}, raising=False)
    monkeypatch.setenv("NTFY_ACCESS_TOKEN", "")

    with pytest.raises(SystemExit):
        monitor.main()

    assert monitor.NTFY_ACCESS_TOKEN == "tk_from_file"
    assert monitor.SECRET_SOURCES["NTFY_ACCESS_TOKEN"] == "dotenv file"


# Each secret is attributed to the source it actually came from, so the report can name the dotenv path
def test_secret_sources_split_by_origin(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("SMTP_PASSWORD=from-file\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "from-file", raising=False)
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.sh/topic", raising=False)
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "your_sp_dc_cookie_value", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"SMTP_PASSWORD": "dotenv file", "WEBHOOK_URL": "environment"}, raising=False)

    from_file, from_environment, from_settings, from_command_line = monitor.doctor_secret_sources(str(env_file))

    assert "SMTP_PASSWORD" in from_file
    assert "WEBHOOK_URL" in from_environment
    assert "SP_DC_COOKIE" not in from_file + from_environment + from_settings + from_command_line


# Verifies a row whose advice repeats its own summary prints that text once rather than as two problems
def test_a_row_never_prints_its_summary_twice():
    repeated = "No valid sp_dc cookie was found"

    check = monitor.make_doctor_check("Configuration", "WARN", repeated, repeated, actionable_advice())

    assert check.label == repeated
    assert check.detail == ""


# Verifies a secret passed as an argument is reported under the command line rather than the configuration file
def test_a_command_line_secret_is_reported_as_such(monkeypatch):
    for name in monitor.SECRET_KEYS:
        monkeypatch.setattr(monitor, name, "your_placeholder", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"SMTP_PASSWORD": "command line"}, raising=False)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "a-real-secret-value", raising=False)

    labels = [check.label for check in monitor.doctor_secret_checks(None)]

    assert "Secrets loaded from the command line" in labels
    assert "Secrets loaded from the configuration file or command line" not in labels


# Verifies the Python row states the minimum it was judged against and that the fix names the same minimum
def test_the_python_row_names_the_minimum_supported_version():
    supported = monitor.doctor_check_environment((3, 12, 1), lambda name: object())[0]
    unsupported = monitor.doctor_check_environment((3, 8, 18), lambda name: object())[0]

    assert supported.status == "PASS"
    assert supported.detail == f"Minimum supported version: {monitor.MINIMUM_PYTHON_VERSION_TEXT}"
    assert unsupported.status == "FAIL"
    assert unsupported.detail == supported.detail
    assert monitor.MINIMUM_PYTHON_VERSION_TEXT in unsupported.advice.fix


# Verifies valid numeric settings take no row, since a value that is merely fine is not a finding
def test_valid_numeric_settings_take_no_row():
    checks = monitor.doctor_check_configuration()

    assert not any("numeric" in check.label.casefold() for check in checks)


# Verifies email alerts that cannot deliver are one WARN whose detail and action name the same settings
def test_unusable_email_settings_warn_and_name_the_same_settings(monkeypatch):
    monkeypatch.setattr(monitor, "PROFILE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_PORT", 587)
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "monitor@example.invalid")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "owner@example.invalid")
    monkeypatch.setattr(monitor, "SMTP_USER", "your_smtp_user")
    monkeypatch.setattr(monitor, "smtp_connect_and_login", Mock(side_effect=AssertionError("SMTP was contacted")))

    check = monitor.doctor_check_notifications()[0]

    assert check.status == "WARN"
    assert check.label == monitor.EMAIL_UNUSABLE_CHECK_LABEL
    assert check.detail == "SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder"
    assert "Set SMTP_USER and SMTP_PASSWORD or turn the email alerts off" in check.advice.fix
    assert monitor.SMTP_GUIDE_URL in check.advice.fix


# Verifies every doctor detail keeps to the agreed shapes: it never repeats its label, gives an instruction or joins values with a pipe
def test_doctor_details_keep_to_the_agreed_shapes():
    import ast
    import inspect

    # Renders one detail argument as text, standing in {} for the parts an f-string fills at runtime
    def detail_text(node):
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, str) else None
        if isinstance(node, ast.JoinedStr):
            return "".join(part.value if isinstance(part, ast.Constant) else "{}" for part in node.values)
        return None

    offenders = []
    for node in ast.walk(ast.parse(inspect.getsource(monitor))):
        if not isinstance(node, ast.Call) or ast.unparse(node.func) not in {"make_doctor_check", "report.add"} or len(node.args) < 4:
            continue
        label, text = node.args[2], detail_text(node.args[3])
        if text is None:
            continue
        if isinstance(label, ast.Constant) and text == label.value:
            offenders.append(f"{node.lineno}: the detail repeats its label")
        if text.startswith(("Use ", "Set ", "Run ")):
            offenders.append(f"{node.lineno}: the detail gives an instruction, which belongs in the fix line")
        if " | " in text:
            offenders.append(f"{node.lineno}: the detail joins two values with a pipe")
        if text.endswith("."):
            offenders.append(f"{node.lineno}: the detail ends with a full stop")

    assert not offenders, "doctor details outside the agreed shapes:\n" + "\n".join(offenders)


# Verifies the constructor drops a detail that only repeats its label, so no row says the same thing twice
def test_a_detail_that_repeats_its_label_is_dropped():
    check = monitor.make_doctor_check("Configuration", "PASS", "Output logging is disabled", "Output logging is disabled")

    assert check.detail == ""


# Verifies only the four shared markers can reach a report
def test_an_actionable_row_is_rejected_without_a_fix():
    for status in ("WARN", "FAIL"):
        with pytest.raises(ValueError):
            monitor.make_doctor_check("Configuration", status, "a label", "some detail")

    assert monitor.make_doctor_check("Configuration", "SKIP", "a label").status == "SKIP"


# Verifies only the four shared markers can reach a report
def test_only_the_four_shared_markers_are_accepted():
    assert monitor.DOCTOR_STATUSES == ("PASS", "WARN", "FAIL", "SKIP")
    assert [monitor.make_doctor_check("Configuration", status, "a label", "", actionable_advice()).status for status in monitor.DOCTOR_STATUSES] == list(monitor.DOCTOR_STATUSES)

    with pytest.raises(ValueError):
        monitor.make_doctor_check("Configuration", "INFO", "a label")


# Verifies one row reads as one block: the action lines sit under the marker at the detail indent while a pass row has none
def test_the_action_lines_sit_indented_under_their_marker(monkeypatch):
    monkeypatch.setattr(monitor, "colorize", lambda theme, text: text)
    advice = monitor.make_recovery_advice("config.invalid", "a warning row", monitor.recovery_fix_with_guide("do the thing", monitor.DOCTOR_GUIDE_URL), False)
    report = monitor.DoctorReport([
        monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping", advice),
        monitor.make_doctor_check("Configuration", "PASS", "a passing row", "", advice),
    ])

    lines = render_doctor_report(report).splitlines()
    rows = lines[lines.index("[WARN] a warning row"):]

    assert rows[:5] == ["[WARN] a warning row", "  a detail worth keeping", "  To fix: do the thing", f"  Guide: {monitor.DOCTOR_GUIDE_URL}", "[PASS] a passing row"]


# Verifies an approved delivery test that failed reaches the summary, so a failing run cannot report a clean one
def test_a_failed_delivery_test_reaches_the_summary(monkeypatch):
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", monitor.SMTP_READY_CHECK_LABEL)])
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor.sys, "stdout", TTYBuffer())
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", Mock(return_value=True))
    monkeypatch.setattr(monitor, "send_email", Mock(return_value=1))

    monitor._doctor_offer_notification_tests(report)

    assert [(check.section, check.status, check.label) for check in report.checks][-1] == (monitor.DOCTOR_DELIVERY_SECTION, "FAIL", "Doctor test email delivery failed")
    assert "1 check(s) failed, 0 warning(s)." in monitor.render_doctor_summary(report.checks)


# Verifies a failed delivery test fails the whole run, so the exit code and the last sentence agree
def test_a_failed_delivery_test_changes_the_exit_code(monkeypatch):
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", monitor.SMTP_READY_CHECK_LABEL)])
    stream = TTYBuffer()
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor.sys, "stdout", stream)
    monkeypatch.setattr(monitor, "build_doctor_report", lambda *args, **kwargs: report)
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", Mock(return_value=True))
    monkeypatch.setattr(monitor, "send_email", Mock(return_value=1))

    code = monitor.run_doctor()

    assert code == 1
    assert "[FAIL] Doctor test email delivery failed" in stream.getvalue()
    assert "1 check(s) failed" in stream.getvalue()
    assert "All checks passed" not in stream.getvalue()


# Verifies every doctor entry point renders its summary after the delivery tests, so the sentence and the exit code describe one run
def test_the_summary_is_rendered_after_the_delivery_tests():
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(monitor))
    checked = 0
    for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
        calls = [(call.lineno, ast.unparse(call.func)) for call in ast.walk(function) if isinstance(call, ast.Call)]
        offers = [lineno for lineno, name in calls if name.endswith("_doctor_offer_notification_tests")]
        summaries = [lineno for lineno, name in calls if name.endswith("render_doctor_summary")]
        if not offers or not summaries:
            continue
        checked += 1
        assert max(offers) < min(summaries), f"{function.name} renders the summary before the delivery tests"

    assert checked, "no doctor entry point runs the delivery tests and then the summary"


# Verifies the connectivity row carries the label and the endpoint detail shared with the sibling monitors
def test_the_connectivity_row_names_the_shared_endpoint(monkeypatch):
    monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://probe.example/ping")
    monkeypatch.setattr(monitor, "check_internet", lambda **kwargs: True)
    passing = monitor.doctor_connectivity_endpoint_check()
    monkeypatch.setattr(monitor, "check_internet", lambda **kwargs: False)
    failing = monitor.doctor_connectivity_endpoint_check()

    assert (passing.status, passing.label, passing.detail) == ("PASS", "The connectivity endpoint is reachable", "Endpoint: https://probe.example/ping")
    assert (failing.status, failing.label, failing.detail) == ("FAIL", "The connectivity endpoint could not be reached", "Endpoint: https://probe.example/ping")
    assert failing.advice.fix == "Check network, DNS, proxy and CHECK_INTERNET_URL settings"


# Verifies a report read on its own ends with the command that starts monitoring, carrying this run's files
def test_the_report_ends_with_the_command_that_starts_monitoring(capsys):
    monitor._wizard_print_monitor_after_doctor("/etc/spm.conf", "/etc/spm.env", "friend.user", doctor_exit=0)

    transcript = capsys.readouterr().out
    assert "Next steps" in transcript
    assert "Start monitoring:" in transcript
    # The paths are resolved before printing, so the flags and file names are what this pins
    assert "--config-file" in transcript and "spm.conf" in transcript
    assert "--env-file" in transcript and "spm.env" in transcript
    assert transcript.rstrip().endswith(monitor.QUICK_START_GUIDE_URL)


# Verifies a failing report names the order to work in, rather than inviting a run that cannot succeed yet
def test_a_failing_report_asks_for_the_failures_first(capsys):
    monitor._wizard_print_monitor_after_doctor("/etc/spm.conf", "/etc/spm.env", "friend.user", doctor_exit=1)

    assert "After Doctor passes, start monitoring:" in capsys.readouterr().out


# Verifies the dotenv sentinel is carried, since monitoring only reads the file the sentinel disables
def test_the_dotenv_sentinel_is_carried_into_the_command(capsys):
    monitor._wizard_print_monitor_after_doctor("none", "none", "friend.user", doctor_exit=0)

    assert "--env-file none" in capsys.readouterr().out


# Verifies the row names the state the shared resolver settled on, so it says what a restart would say
def test_the_timezone_row_follows_the_shared_resolver(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "Mars/Olympus_Mons")
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE_STATE", "config")

    advice = monitor.resolve_local_timezone()

    assert monitor.LOCAL_TIMEZONE_STATE == "invalid"
    row = next(item for item in monitor.doctor_check_configuration(timezone_advice=advice) if item.label in monitor.TIMEZONE_CHECK_LABELS.values())
    assert (row.status, row.label, row.detail) == ("FAIL", "Local timezone is invalid", "Time zone: Mars/Olympus_Mons")


# Verifies Ctrl+C at a delivery prompt ends the run instead of declining one test and asking the next
def test_a_delivery_prompt_interrupt_ends_the_run(monkeypatch):
    def interrupt(prompt=""):
        raise KeyboardInterrupt

    # The handler restores the saved stream, so it is pointed at the one this test captures
    monkeypatch.setattr(monitor, "stdout_bck", monitor.sys.stdout)
    monkeypatch.setattr("builtins.input", interrupt)

    with pytest.raises(SystemExit) as raised:
        monitor._doctor_ask_yes_no("Send one test")

    assert raised.value.code == 0


# Verifies a run with no target of its own prints no placeholder, so the command can be pasted as it is
def test_doctor_monitoring_command_carries_no_placeholder_target(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")

    monitor._wizard_print_monitor_after_doctor(tmp_path / "spotify_profile_monitor.conf", tmp_path / ".env")

    output = capsys.readouterr().out
    assert "SPOTIFY_TARGET" not in output
    assert f"--config-file {tmp_path / 'spotify_profile_monitor.conf'}" in output


# An interval below the safe floor gets the account rate limited, which looks like the tool being broken
def test_a_rate_limiting_interval_is_warned_about(monkeypatch):
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 5)

    rows = [item for item in monitor.doctor_check_configuration() if item.label == "Check intervals are short"]

    assert [item.status for item in rows] == ["WARN"]
    assert str(monitor.DOCTOR_MIN_SAFE_CHECK_INTERVAL) in rows[0].advice.fix


# The default interval is safe, so the row must stay away rather than warning about every run
def test_a_safe_interval_is_not_warned_about(monkeypatch):
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", monitor.DOCTOR_MIN_SAFE_CHECK_INTERVAL)

    assert not [item for item in monitor.doctor_check_configuration() if item.label == "Check intervals are short"]


# A run with no target warns with the sentence every monitor in this family uses, so the report reads the same
def test_a_missing_target_warns_with_the_shared_detail():
    checks = monitor.doctor_check_target(monitor.DoctorReport(), None)

    assert [check.status for check in checks] == ["WARN"]
    assert checks[0].detail == "Nothing will be monitored until one is given"


# Verifies configured mail settings with no alert types selected warn, since nothing would ever be emailed
def test_email_configured_but_nothing_selected_warns(monkeypatch):
    monkeypatch.setattr(monitor, "PROFILE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_PROFILE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "SMTP_PORT", 587)
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "private-password")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "monitor@example.test")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "alerts@example.test")
    monkeypatch.setattr(monitor, "smtp_connect_and_login", Mock(side_effect=AssertionError("SMTP was contacted")))

    check = monitor.doctor_check_notifications()[0]

    assert (check.status, check.label) == ("WARN", "Email is configured but no alert types are selected")
    assert check.advice.fix.startswith("Turn on at least one email alert in the configuration file")
    assert monitor.SMTP_GUIDE_URL in check.advice.fix


# Verifies webhook alert types selected while the channel is off warn, since nothing would ever be delivered
def test_webhook_alerts_selected_but_switched_off_warn(monkeypatch):
    monkeypatch.setattr(monitor, "PROFILE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_PROFILE_NOTIFICATION", True)

    check = monitor.doctor_check_notifications()[-1]

    assert (check.status, check.label) == ("WARN", "Webhook alert types are selected but webhooks are switched off")
    assert "WEBHOOK_ENABLED" in check.advice.fix


# One row shape and one advice shape across the family: the advice rides on the row and its fix carries the
# guide, so a row or an advice copied from a sibling means the same thing here
def test_the_doctor_row_and_its_advice_share_one_contract():
    row_parameters = list(inspect.signature(monitor.make_doctor_check).parameters.values())
    advice_parameters = list(inspect.signature(monitor.make_recovery_advice).parameters.values())

    assert [parameter.name for parameter in row_parameters] == ["section", "status", "label", "detail", "advice"]
    assert [parameter.default for parameter in row_parameters[3:]] == ["", None]
    assert [parameter.name for parameter in advice_parameters] == ["code", "summary", "fix", "retryable", "detail"]
    assert monitor.recovery_fix_with_guide("do the thing", "https://example.invalid/page") == "do the thing\nGuide: https://example.invalid/page"


# A non-pass row is refused without advice and keeps the advice it was given, which is where its fix and guide live
def test_a_row_carries_its_advice_and_refuses_to_go_without():
    advice = monitor.make_recovery_advice("config.invalid", "a warning row", monitor.recovery_fix_with_guide("do the thing", monitor.DOCTOR_GUIDE_URL), False)

    row = monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping", advice)

    assert row.advice is advice
    assert not hasattr(advice, "guide_url")
    with pytest.raises(ValueError):
        monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping")


# A retired setting used to stop the doctor at startup, so the warning row it becomes is pinned with the action it carries
def test_a_retired_setting_becomes_a_warning_row_with_an_action(monkeypatch, tmp_path):
    config_path = tmp_path / "spotify_profile_monitor.conf"
    config_path.write_text("TOTP_VER = 1\n", encoding="utf-8")
    received = {}
    # main() records the selected paths in module globals, so they are restored for the tests that run after this one
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", monitor.CLI_CONFIG_PATH, raising=False)
    monkeypatch.setattr(monitor, "DOTENV_FILE", monitor.DOTENV_FILE, raising=False)
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_profile_monitor", "--doctor", "--config-file", str(config_path), "--env-file", "none"])
    monkeypatch.setattr(monitor, "run_doctor", lambda target, config, env, startup_checks, **kwargs: received.update(checks=list(startup_checks)) or 0)

    with pytest.raises(SystemExit):
        monitor.main()

    row = next(check for check in received["checks"] if check.label == "Configuration file contains removed settings")
    assert row.status == "WARN"
    assert "TOTP_VER" in row.detail
    assert row.advice.fix == monitor.recovery_fix_with_guide("Delete the listed settings from the configuration file", monitor.CONFIG_GUIDE_URL)

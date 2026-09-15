import stat
from pathlib import Path
import ast
import inspect
import os
import re
import subprocess
import sys
import time
import unicodedata
from unittest.mock import Mock

import pytest

import spotify_profile_monitor as monitor



# Composes the two renderers the way run_doctor does, so a test can assert on the whole transcript
def render_doctor_report(report):
    return monitor.render_doctor_sections(report) + "\n" + monitor.render_doctor_summary(report.checks)


# Guide constants may point at Spotify's own developer documentation, which this repository cannot resolve to a page
EXTERNAL_GUIDE_PREFIXES = ("https://developer.spotify.com/",)


# Verifies runtime URL builders use centralized globals instead of repeated literals
def test_runtime_url_builders_use_global_bases(monkeypatch):
    monkeypatch.setattr(monitor, "NTFY_PUBLIC_BASE_URL", "https://notify.example")
    monkeypatch.setattr(monitor, "SPOTIFY_WEB_BASE_URL", "https://web.example")

    assert monitor.normalize_ntfy_topic_url("private-topic") == "https://notify.example/private-topic"
    assert monitor.spotify_convert_uri_to_url("spotify:user:target") == "https://web.example/user/target?si=1"


# Returns explicit and heading-generated Markdown anchor IDs for one document
def markdown_anchors(text: str) -> set:
    anchors = set(re.findall(r'<a\s+id=["\x27]([^"\x27]+)', text))
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        heading = None if in_fence else re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading is None:
            continue
        normalized = unicodedata.normalize("NFKD", heading.group(1)).encode("ascii", "ignore").decode("ascii").casefold()
        slug = re.sub(r"[-\s]+", "-", re.sub(r"[^\w\s-]", "", normalized)).strip("-")
        if slug:
            anchors.add(slug)
    return anchors


# Verifies every runtime guide global resolves to a published documentation page and anchor, enumerated so a new constant cannot escape the check
def test_guide_urls_match_documentation_anchors():
    guide_names = sorted(name for name in vars(monitor) if name.endswith("_GUIDE_URL"))
    assert guide_names, "no runtime guide constants were found"

    for name in guide_names:
        guide_url = getattr(monitor, name)
        if not guide_url.startswith(monitor.DOCUMENTATION_URL + "/"):
            assert guide_url.startswith(EXTERNAL_GUIDE_PREFIXES), f"{name} points outside both this site and the allowed external guides: {guide_url}"
            continue
        relative_path, _separator, fragment = guide_url.removeprefix(monitor.DOCUMENTATION_URL).lstrip("/").partition("#")
        document_path = "docs/index.md" if not relative_path else f"docs/{relative_path.rstrip('/')}.md"
        document = Path(__file__).parents[1] / document_path
        assert document.is_file(), f"{name} references missing page {document_path}"
        if fragment:
            assert fragment in markdown_anchors(document.read_text(encoding="utf-8")), f"{name} references missing anchor #{fragment} in {document_path}"


# Verifies the documentation site publishes every navigation page through a strict deployment
def test_documentation_site_contract():
    root = Path(__file__).parents[1]
    mkdocs = (root / "mkdocs.yml").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/docs.yml").read_text(encoding="utf-8")

    assert f"site_url: {monitor.DOCUMENTATION_URL}/" in mkdocs
    for page in ("index.md", "installation.md", "setup-and-first-run.md", "configuration.md", "usage.md", "troubleshooting.md", "debugging.md", "testing.md", "about.md"):
        assert f": {page}" in mkdocs, page
        assert (root / "docs" / page).is_file(), page
    assert "mkdocs gh-deploy --force --strict" in workflow


# Verifies every in-page and cross-page documentation fragment link resolves, which MkDocs does not check for same-page anchors
def test_documentation_fragment_links_resolve():
    pages = {path.name: path.read_text(encoding="utf-8") for path in sorted((Path(__file__).parents[1] / "docs").glob("*.md"))}
    anchors = {name: markdown_anchors(text) for name, text in pages.items()}
    broken = []

    for name, text in pages.items():
        for target, fragment in re.findall(r"\]\(([^)#\s]*)#([^)\s]+)\)", text):
            if target.startswith("http"):
                continue
            page = target or name
            if page not in anchors:
                broken.append(f"{name}: link to unknown page {page}")
            elif fragment not in anchors[page]:
                broken.append(f"{name}: dead anchor {page}#{fragment}")
        for target in re.findall(r"\]\(([A-Za-z0-9._-]+\.md)\)", text):
            if target not in pages:
                broken.append(f"{name}: link to unknown page {target}")

    assert broken == []


# Verifies debugging guidance tracks the current shared utilities instead of a stale branch or download command
def test_debugging_docs_track_the_current_utilities():
    debugging = (Path(__file__).parents[1] / "docs" / "debugging.md").read_text(encoding="utf-8")

    # These utilities live on the sibling project's default branch, so a dev-branch link rots as soon as dev moves
    assert "/dev/" not in debugging
    assert "refs/heads/dev" not in debugging
    assert "wget " not in debugging
    for command in ("curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/debug/spotify_monitor_totp_test.py", "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/debug/spotify_monitor_secret_grabber.py"):
        assert command in debugging
    # The container examples must keep checking for a newer extractor image before each run
    assert debugging.count("docker run --rm --pull=always") == 5
    assert 'SPOTIFY_SECRET_GRABBER_UID="$(id -u)" SPOTIFY_SECRET_GRABBER_GID="$(id -g)" docker compose run --rm spotify-secrets-grabber --all' in debugging


# Verifies the README keeps pointing readers at the published documentation instead of removed sections
def test_readme_points_at_the_documentation_site():
    readme = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")

    assert f"{monitor.DOCUMENTATION_URL}/" in readme
    assert "#table-of-contents" not in readme


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
    config_path.write_text("LOCAL_TIMEZONE = 'UTC'\nTRUNCATE_CHARS = 120\n", encoding="utf-8")
    namespace = {"LOCAL_TIMEZONE": "Auto", "TRUNCATE_CHARS": 0, "KEEP_ME": True}

    assert monitor.load_config_file(config_path, namespace=namespace, report_errors=False) is True
    assert namespace == {"LOCAL_TIMEZONE": "UTC", "TRUNCATE_CHARS": 120, "KEEP_ME": True}


@pytest.mark.parametrize("content", ["VALUES.append('saved')\n", "del LOCAL_TIMEZONE\n", "import os\n", "LOCAL_TIMEZONE = __import__('os').getcwd()\n", "LOCAL_TIMEZONE = open('/etc/passwd').read()\n", "if True:\n    LOCAL_TIMEZONE = 'UTC'\n", "LOCAL_TIMEZONE = 'UTC'; import sys\n"])
# Verifies a config file cannot execute code, import modules or delete settings
def test_config_load_refuses_executable_content(tmp_path, content):
    config_path = tmp_path / "hostile.conf"
    config_path.write_text(content, encoding="utf-8")
    namespace = {"LOCAL_TIMEZONE": "Auto", "VALUES": ["original"]}

    assert monitor.load_config_file(config_path, namespace=namespace, report_errors=False) is False
    assert namespace == {"LOCAL_TIMEZONE": "Auto", "VALUES": ["original"]}


# Verifies a setting the tool does not define is rejected instead of silently landing in the namespace
def test_config_load_rejects_unknown_setting(tmp_path):
    config_path = tmp_path / "unknown.conf"
    config_path.write_text("NOT_A_REAL_SETTING = 1\n", encoding="utf-8")
    namespace = {"LOCAL_TIMEZONE": "Auto"}

    assert monitor.load_config_file(config_path, namespace=namespace, report_errors=False) is False
    assert "NOT_A_REAL_SETTING" not in namespace


@pytest.mark.parametrize(("content", "expected"), (("# unsupported helper\nCUSTOM_HELPER = 'test'\n", "Line 2: unsupported configuration setting 'CUSTOM_HELPER'"), ("CSV_FILE = f'exports.csv'\n", "Line 1: CSV_FILE must be a plain value")))
# Verifies config failures expose their exact line and actionable reason without debug mode
def test_config_load_reports_exact_invalid_line(tmp_path, capsys, content, expected):
    config_path = tmp_path / "invalid.conf"
    config_path.write_text(content, encoding="utf-8")

    assert monitor.load_config_file(config_path) is False
    output = capsys.readouterr().out
    assert expected in output
    assert str(config_path) in output
    assert "Technical detail:" not in output


# Verifies a configuration written by an older version still loads when it carries retired settings
def test_config_load_ignores_retired_settings(tmp_path, capsys):
    config_path = tmp_path / "legacy.conf"
    config_path.write_text('TOTP_VER = 0\nSECRET_CIPHER_DICT = {"12": [1, 2]}\nSECRET_CIPHER_DICT_URL = "https://example.invalid/secrets.json"\nTRUNCATE_CHARS = 120\n', encoding="utf-8")
    namespace = {"TRUNCATE_CHARS": 0}

    assert monitor.load_config_file(config_path, namespace=namespace) is True
    assert namespace == {"TRUNCATE_CHARS": 120}
    output = capsys.readouterr().out
    assert "TOTP_VER" in output
    assert "are ignored" in output


# Verifies captured retired settings are deferred so the caller can report them after any screen clear
def test_config_load_reports_retired_settings_to_caller(tmp_path, capsys):
    config_path = tmp_path / "legacy.conf"
    config_path.write_text("TOTP_VER = 0\nTRUNCATE_CHARS = 120\n", encoding="utf-8")
    retired = []

    assert monitor.load_config_file(config_path, namespace={}, retired_out=retired) is True
    assert retired == ["TOTP_VER"]
    assert capsys.readouterr().out == ""


# Verifies ignoring retired names does not weaken rejection of any other unknown setting
def test_retired_allowance_does_not_accept_other_unknown_names():
    assert monitor.RETIRED_CONFIG_SETTINGS.isdisjoint(monitor._config_allowed_names())
    with pytest.raises(ValueError, match="unsupported configuration setting"):
        monitor.parse_config_content("TOTP_VERSION_TYPO = 1\n")


# Verifies the shipped config template still loads through the restricted parser
def test_config_template_parses_as_literals():
    parsed = monitor.parse_config_content(monitor.CONFIG_BLOCK, "<built-in-config>")

    assert parsed["LOCAL_TIMEZONE"] == "Auto"
    assert len(parsed) == len(monitor._config_allowed_names() - monitor.COMMENTED_CONFIG_SETTINGS)


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

    monitor.print_recovery_error(error, "cookie_auth", retry_note="retrying in 5 minutes", tracker=tracker)
    first = capsys.readouterr().out
    monitor.print_recovery_error(error, "cookie_auth", retry_note="retrying in 5 minutes", tracker=tracker)
    second = capsys.readouterr().out
    tracker.reset()
    monitor.print_recovery_error(error, "cookie_auth", retry_note="retrying in 5 minutes", tracker=tracker)
    third = capsys.readouterr().out

    assert first.splitlines()[0].startswith("* Error: ")
    assert first.splitlines()[0].endswith(" (retrying in 5 minutes)")
    assert "To fix:" in first
    assert second == first.splitlines()[0] + "\n"
    assert third == first


# Verifies a named sub-operation keeps the shared line shape rather than inventing its own
def test_a_labelled_failure_keeps_the_shared_shape(capsys):
    error = RuntimeError("401 Unauthorized sp_dc")

    monitor.print_recovery_error(error, "cookie_auth", retry_note="retrying in 5 minutes", label="Error while getting followers and followings", tracker=None)

    first_line = capsys.readouterr().out.splitlines()[0]
    assert first_line.startswith("* Error while getting followers and followings: ")
    assert first_line.endswith(" (retrying in 5 minutes)")


# Verifies a lasting failure is reported once and then only once the reminder interval has passed
def test_the_outage_reporter_reports_once_then_on_the_cadence(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 180)
    reporter = monitor.OutageReporter()
    advice = monitor.classify_recovery_error(RuntimeError("503 Server Error"), "cookie_auth")

    assert reporter.failed(advice) == "full"
    outcomes = []
    for _ in range(3):
        clock[0] += 60
        outcomes.append(reporter.failed(advice))

    assert outcomes == ["", "", "reminder"]
    assert reporter.recovered() is not None
    assert reporter.recovered() is None


# Verifies a category change mid-outage keeps the outage start, so the alert delay and the reminder still elapse
def test_an_outage_that_changes_category_keeps_its_start(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    first = monitor.classify_recovery_error(RuntimeError("503 Server Error"), "cookie_auth")
    second = monitor.classify_recovery_error(OSError(24, "Too many open files"))
    assert first.code != second.code

    assert reporter.failed(first) == "full"
    for index in range(60):
        clock[0] += 15
        reporter.failed(second if index % 2 else first)

    assert reporter.since == 1000000
    assert reporter.recovered() == 900


# Verifies the reminder follows the clock, so a run that retries faster than it polls does not remind more often
def test_the_outage_reminder_follows_the_clock_not_the_check_count(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    advice = monitor.classify_recovery_error(RuntimeError("503 Server Error"), "cookie_auth")

    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 900)
    assert reporter.failed(advice) == "full"
    outcomes = []
    for _ in range(60):
        clock[0] += 15
        outcomes.append(reporter.failed(advice))

    assert outcomes.count("reminder") == 1


# Verifies the reminder keeps its own clock when the liveness banner is switched off, so a lasting failure is
# neither silenced nor repeated every check
def test_the_outage_reporter_reminds_on_its_own_clock_without_a_liveness_banner(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 0)
    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 60)
    reporter = monitor.OutageReporter()
    advice = monitor.classify_recovery_error(RuntimeError("503 Server Error"), "cookie_auth")

    assert reporter.failed(advice) == "full"
    clock[0] += 59
    assert reporter.failed(advice) == ""
    clock[0] += 1
    assert reporter.failed(advice) == "reminder"
    assert reporter.failed(advice) == ""


# Verifies the reporter treats every network code as one outage and any other retryable change as a one-line note
def test_the_outage_reporter_merges_network_codes_and_notes_other_changes(monkeypatch, capsys):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    reporter = monitor.OutageReporter()
    timeout = monitor.classify_recovery_error(RuntimeError("The read operation timed out"), "cookie_auth")
    unreachable = monitor.classify_recovery_error(monitor.req.exceptions.ConnectionError("connection refused"), "cookie_auth")
    unavailable = monitor.classify_recovery_error(RuntimeError("503 Server Error"), "cookie_auth")
    assert (monitor.outage_family(timeout.code), monitor.outage_family(unreachable.code)) == ("network", "network")

    assert reporter.failed(timeout) == "full"
    assert reporter.failed(unreachable) == ""
    assert reporter.failed(timeout) == ""
    assert reporter.failed(unavailable) == "changed"
    assert reporter.failed(unavailable) == ""
    assert reporter.since == 1000000

    monitor.print_outage_change("watched-user", unavailable)
    monitor.print_outage_liveness("watched-user", unavailable, reporter.since, reporter.failures)

    output = capsys.readouterr().out
    assert f"* Monitoring failure changed for watched-user. {unavailable.summary}\n" in output
    assert f"* Monitoring degraded for watched-user. {unavailable.summary} since " in output
    assert ", 5 failed checks\n" in output


# Verifies a destination that already exists is refused as itself, since --force rather than permissions is the answer
def test_an_existing_destination_is_not_reported_as_unwritable(tmp_path):
    destination = tmp_path / "spotify_profile_monitor.conf"
    destination.write_text("SPOTIFY_CHECK_INTERVAL = 60\n", encoding="utf-8")

    with pytest.raises(FileExistsError) as refusal:
        monitor.confirm_config_replacement(str(destination), force=False, interactive=False)
    advice = monitor.classify_recovery_error(refusal.value, "file_exists", detail=str(refusal.value))

    assert advice.code == "file.exists"
    assert "already exists" in advice.summary
    assert "--force" in advice.fix
    assert f"Guide: {monitor.CONFIG_GUIDE_URL}" in advice.fix


# Verifies a local file descriptor limit is reported as itself rather than as a failure of the call that hit it
def test_a_file_descriptor_limit_is_not_reported_as_a_service_failure():
    try:
        try:
            raise OSError(24, "Too many open files")
        except OSError as inner:
            raise RuntimeError("the Spotify request failed") from inner
    except RuntimeError as error:
        advice = monitor.classify_recovery_error(error)

    assert advice.code == "resource.exhausted"
    assert advice.retryable is False
    assert "not a Spotify problem" in advice.summary
    assert "ulimit -n 4096" in advice.fix


# Verifies the descriptor limit is matched as a whole errno, so errno 240 or 241 in a message is not mistaken for it
def test_a_neighbouring_errno_is_not_a_file_descriptor_limit():
    assert monitor.is_too_many_open_files(RuntimeError("[Errno 24] Too many open files")) is True
    assert monitor.is_too_many_open_files(RuntimeError("[Errno 240] something else")) is False
    assert monitor.is_too_many_open_files(RuntimeError("[Errno 241] something else")) is False


# Verifies an operation failure names the step that failed in front of the classified cause and still carries a fix
def test_an_operation_failure_names_the_step_and_the_cause(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)

    monitor.print_operation_error("A CSV event could not be written", PermissionError(13, "Permission denied"))

    printed = capsys.readouterr().out
    assert "* Error: A CSV event could not be written: An output destination is not writable" in printed
    assert "To fix: Choose a writable path" in printed
    assert f"Guide: {monitor.DIAGNOSTICS_GUIDE_URL}" in printed


# Verifies a step that failed without an exception still picks its fix from the context it names
def test_an_operation_failure_without_an_exception_keeps_its_own_summary(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)

    monitor.print_operation_error("The login Protobuf file 'login.bin' does not exist", context="file_read")

    printed = capsys.readouterr().out
    assert "* Error: The login Protobuf file 'login.bin' does not exist" in printed
    assert "To fix: Verify the path, file format and read permissions then retry" in printed


# Verifies a command-line value the tool cannot use is refused with the action that corrects it
def test_a_refused_argument_names_the_action_that_corrects_it(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)

    monitor.print_argument_error("--export-all-playlists needs a profile to export from", "Add -i / --show-user-profile to the command")

    printed = capsys.readouterr().out
    assert "* Error: --export-all-playlists needs a profile to export from" in printed
    assert "To fix: Add -i / --show-user-profile to the command" in printed
    assert f"Guide: {monitor.USAGE_GUIDE_URL}" in printed


# Verifies an optional library that is missing names what the run loses and the command that installs it
def test_a_missing_optional_library_names_the_loss_and_the_install(monkeypatch):
    advice = monitor.missing_dependency_advice("Pillow", "Email and ntfy alerts are sent without artwork", "pip install Pillow")

    assert advice.code == "dependency.missing"
    assert advice.summary == "Email and ntfy alerts are sent without artwork because the optional 'Pillow' library is missing"
    assert "Install it with: pip install Pillow" in advice.fix
    assert f"Guide: {monitor.INSTALLATION_GUIDE_URL}" in advice.fix


# Verifies a mail setting that makes delivery impossible is reported through the recovery block rather than a bare line
@pytest.mark.parametrize("setting,value,named", [("SMTP_HOST", "not a host", "invalid IP address/FQDN in SMTP_HOST"), ("SMTP_PORT", 0, "invalid port number in SMTP_PORT"), ("SENDER_EMAIL", "not-an-address", "invalid email in SENDER_EMAIL or RECEIVER_EMAIL"), ("SMTP_USER", "your_smtp_user", "check SMTP_USER & SMTP_PASSWORD configuration options")])
def test_an_unusable_mail_setting_is_reported_through_the_recovery_block(monkeypatch, capsys, setting, value, named):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    for name, usable in (("SMTP_HOST", "smtp.example.com"), ("SMTP_PORT", 587), ("SMTP_USER", "user"), ("SMTP_PASSWORD", "secret"), ("SENDER_EMAIL", "sender@example.com"), ("RECEIVER_EMAIL", "receiver@example.com")):
        monkeypatch.setattr(monitor, name, usable)
    monkeypatch.setattr(monitor, setting, value)

    assert monitor.send_email("subject", "body", "", False) == 1

    printed = capsys.readouterr().out
    # The summary names the setting that failed, so the reader does not have to rerun with --debug to learn which one
    assert f"* Error: The SMTP settings are incorrect ({named})" in printed
    assert "To fix: Correct SMTP_HOST" in printed
    assert f"Guide: {monitor.SMTP_GUIDE_URL}" in printed


# Verifies a message the tool cannot compose is reported the same way as an unusable setting
@pytest.mark.parametrize("subject,body", [("", "body"), ("subject", "")])
def test_an_uncomposable_message_is_reported_through_the_recovery_block(monkeypatch, capsys, subject, body):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    for name, usable in (("SMTP_HOST", "smtp.example.com"), ("SMTP_PORT", 587), ("SMTP_USER", "user"), ("SMTP_PASSWORD", "secret"), ("SENDER_EMAIL", "sender@example.com"), ("RECEIVER_EMAIL", "receiver@example.com")):
        monkeypatch.setattr(monitor, name, usable)

    assert monitor.send_email(subject, body, "", False) == 1
    assert "* Error: The SMTP settings are incorrect (" in capsys.readouterr().out


# Verifies a caller that adds context does not hide the error text the classification rules read
def test_added_context_does_not_hide_the_error_from_the_rules(monkeypatch):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    rows = [
        ("target", RuntimeError("404 not found"), "target.not_found"),
        ("metadata", RuntimeError("rate limit exceeded"), "spotify.rate_limited"),
        ("browser_import", RuntimeError("cookies.sqlite could not be read"), "file.unreadable"),
    ]

    for context, error, expected in rows:
        with_context = monitor.classify_recovery_error(error, context=context, detail="The operation did not complete")
        assert with_context.code == expected, f"{context} fell back to {with_context.code}"


# Verifies a failure category that changes is reported in full again rather than hidden by the previous one
def test_a_changed_failure_category_is_reported_in_full(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    reporter = monitor.OutageReporter()
    unavailable = monitor.classify_recovery_error(RuntimeError("503 Server Error"), "cookie_auth")
    rejected = monitor.classify_recovery_error(RuntimeError("401 Unauthorized sp_dc"), "cookie_auth")

    assert reporter.failed(unavailable) == "full"
    assert reporter.failed(unavailable) == ""
    assert reporter.failed(rejected) == "full", "a failure nothing can retry away is a new report rather than a note"

    monitor.print_outage_liveness("watched-user", rejected, int(time.time()) - 60)
    monitor.print_outage_recovery("watched-user", 60)

    output = capsys.readouterr().out
    assert f"* Monitoring degraded for watched-user. {rejected.summary} since " in output
    assert "Liveness check, timestamp:" in output
    assert "* Monitoring recovered for watched-user after 1 minute" in output


# Verifies the liveness banner explains itself without --verbose, so a plain run never prints a bare timestamp
def test_the_liveness_banner_explains_itself_without_diagnostics(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "LOCAL_TIMEZONE", "UTC")
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)

    monitor.print_liveness_banner("Monitoring healthy for watched-user. No profile or playlist change since the last check")

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "* Monitoring healthy for watched-user. No profile or playlist change since the last check"
    assert lines[1].startswith("Liveness check, timestamp:")


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
    monkeypatch.setattr(monitor, "doctor_check_optional_oauth", lambda report: [])
    monkeypatch.setattr(monitor, "doctor_check_connectivity", lambda *args: [])
    monkeypatch.setattr(monitor, "doctor_check_target", lambda *args: [])
    monkeypatch.setattr(monitor, "doctor_check_notifications", lambda: [])
    phases = []

    monitor.build_doctor_report(progress=phases.append)

    assert phases == ["environment", "configuration", "connectivity", "authentication", "metadata", "the monitored profile", "notifications"]


# Verifies Doctor preserves a startup failure for an explicitly missing dotenv file
def test_doctor_preserves_explicit_missing_dotenv_failure():
    advice = monitor.classify_recovery_error(context="config_missing", detail="Dotenv file not found: missing.env")
    startup = monitor.make_doctor_check("Configuration", "FAIL", "The requested dotenv file was not found", advice.detail, advice)

    checks = monitor.doctor_check_configuration(startup_checks=(startup,))

    assert startup in checks
    assert not any(check.label == "No dotenv file selected" for check in checks)


# Verifies Doctor prints the detail of a failed row the way the sibling monitors do, with or without debug mode
def test_doctor_prints_recovery_detail_without_debug(monkeypatch):
    advice = monitor.make_recovery_advice("auth.cookie_invalid", "Spotify rejected authentication", "Import the cookie again", False, "HTTP 401 internal detail")
    report = monitor.DoctorReport(checks=[monitor.make_doctor_check("Authentication", "FAIL", advice.summary, advice.detail, advice=advice)])

    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    normal = render_doctor_report(report)
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    debug = render_doctor_report(report)

    assert "HTTP 401 internal detail" in normal
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


# Verifies a backup does not widen access to a configuration holding device identifiers
@pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX-only")
def test_config_backup_keeps_the_owner_only_mode_of_its_source(tmp_path):
    destination = tmp_path / "private.conf"
    destination.write_text("SENTINEL = True\n", encoding="utf-8")
    os.chmod(destination, 0o600)

    monitor.write_config_file(destination, 'LOCAL_TIMEZONE = "Auto"\n')

    backups = list(tmp_path.glob("private.conf.*.bak"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "SENTINEL = True\n"
    assert backups[0].stat().st_mode & 0o077 == 0
    assert destination.stat().st_mode & 0o077 == 0


# Verifies the completed check stays a debug trace, since one verbose line per cycle buried the events worth reading
def test_the_completed_check_is_a_debug_only_trace():
    source = (Path(__file__).resolve().parents[1] / "spotify_profile_monitor.py").read_text(encoding="utf-8")

    assert "Monitoring check #" not in source
    assert 'debug_print("Completed check"' in source


# Verifies the documented doctor sections are exactly the ones the report renders
def test_the_documented_doctor_sections_match_the_code():
    text = (Path(__file__).resolve().parents[1] / "docs" / "troubleshooting.md").read_text(encoding="utf-8")

    for section in monitor.DOCTOR_SECTIONS:
        assert f"**{section}**" in text, f"the {section} doctor section is not documented"


GUIDELESS_ADVICE = {
    "The connectivity endpoint did not answer in time": "no page covers this check and the doctor report already ends with the troubleshooting link",
    "The connectivity endpoint could not be reached": "no page covers this check and the doctor report already ends with the troubleshooting link",
}

# The guide sits in this positional slot for each builder, or inside the fix when the signature carries no slot
GUIDE_SLOT = {"advice": 4, "make_recovery_advice": 5}


# True when this builder attaches a documentation link in any of the three shapes the tool uses
def attaches_a_guide(node, source):
    slot = GUIDE_SLOT.get(getattr(node.func, "id", ""))
    if slot is not None and len(node.args) > slot:
        return True
    if any(keyword.arg in ("guide_url", "guide") for keyword in node.keywords):
        return True
    return "recovery_fix_with_guide" in (ast.get_source_segment(source, node.args[2]) or "")


# Returns every expression assigned to each plain name in the module, so a fix held in a variable can be read
def assigned_expressions(tree):
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
    return assignments


# Returns the text of the summary or fix, resolving one level of plain-name assignment
def resolved_text(node, source, assignments):
    if isinstance(node, ast.Name):
        return " ".join(ast.get_source_segment(source, value) or "" for value in assignments.get(node.id, []))
    return ast.get_source_segment(source, node) or ""


# Returns every advice builder that names no page, paired with the summary it reports
def guideless_advice(source):
    tree = ast.parse(source)
    assignments = assigned_expressions(tree)
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT) or len(node.args) < 3:
            continue
        # A builder that re-wraps an already-classified advice carries whatever guide that advice was given
        if isinstance(node.args[2], ast.Attribute) and node.args[2].attr == "fix":
            continue
        if attaches_a_guide(node, source) or "recovery_fix_with_guide" in resolved_text(node.args[2], source, assignments):
            continue
        found.append((node.lineno, resolved_text(node.args[1], source, assignments)))
    return found


# A failure with no page to read leaves the operator with a one-line fix and nowhere to go next
def test_every_failure_names_a_page():
    source = inspect.getsource(monitor)
    unexplained = [f"line {line}: {summary[:100]}" for line, summary in guideless_advice(source) if not any(marker in summary for marker in GUIDELESS_ADVICE)]

    assert unexplained == []


# An allowlist that stopped matching anything would quietly cover every failure in the file
def test_the_guide_guard_still_inspects_the_source():
    source = inspect.getsource(monitor)
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT]
    bare = guideless_advice(source)

    assert len(inspected) > 40
    assert all(any(marker in summary for _, summary in bare) for marker in GUIDELESS_ADVICE), "an allowlisted summary stopped matching a builder"


CLASSIFIER_EXEMPTIONS = {
    "or higher required": "runs at import on an interpreter too old to load the rest of the file",
    "Couldn't find the pytz library": "raised at import, before the classifier and the settings it reads exist",
    "Cannot clear the screen contents": "a cosmetic notice with nothing for the operator to recover from",
    "Masking additional errors": "a note printed under the classified failure above it, saying repeats are hidden",
    "Installation could not start": "a wizard result printed above the question that offers another option",
    "could not be installed": "a wizard result printed above the question that offers another option",
    "need the optional Pillow package": "a wizard hint above the question that offers to switch the feature off",
    "could not be parsed read-only": "a wizard result followed by the question that offers another file",
    "dotenv destination": "a wizard result that reports what was saved and what was not",
    "Setup needs a writable dotenv file": "an answer hint inside the question that re-asks, where the next prompt is the recovery",
    "could not write configuration file": "a wizard result that reports what was saved and what was not",
    "Setup was saved": "a wizard result followed by the step that finishes the setup",
    "Monitoring failure changed for": "a one-line note on a classified outage that already had its full report",
}


# Words that mark a printed line as a report of something going wrong
TROUBLE_WORDS = re.compile(r"error|cannot|can't|failed|failure|invalid|not valid|missing|not installed|no such|refused|unsupported|needs to be|could not|couldn't|unable to", re.IGNORECASE)


# Returns the literal text one print argument shows, leaving out the parts an f-string fills at runtime
def printed_text(node):
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else ""
    if isinstance(node, ast.JoinedStr):
        return "".join(printed_text(part) for part in node.values)
    if isinstance(node, ast.BinOp):
        return printed_text(node.left) + printed_text(node.right)
    return ""


# Returns every printed line that reads as a problem, paired with the line it sits on
def reported_problems(source):
    found = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}):
            continue
        text = " ".join(printed_text(argument) for argument in node.args)
        if TROUBLE_WORDS.search(text):
            found.append((node.lineno, " ".join(text.split())))
    return found


# A problem reported without a category leaves the reader with a message and no next step
def test_every_reported_problem_goes_through_the_classifier():
    unexplained = [f"line {line}: {text[:120]}" for line, text in reported_problems(inspect.getsource(monitor)) if not any(marker in text for marker in CLASSIFIER_EXEMPTIONS)]

    assert unexplained == []


# An exemption list that stopped matching anything would quietly cover the whole file
def test_the_classifier_guard_still_inspects_the_source():
    source = inspect.getsource(monitor)
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}]

    problems = reported_problems(source)

    assert len(inspected) > 100
    assert all(any(marker in text for _, text in problems) for marker in CLASSIFIER_EXEMPTIONS), "an exemption stopped matching a printed line"


# One concept carried three names across this family: a renderer taking a built advice, a renderer taking the
# failure itself, and a third pair named after the monitoring loop. Pinned here so a call copied from a sibling
# cannot quietly mean something else
def test_the_recovery_printers_share_one_contract():
    advice_first = ("advice", "debug", "retry_note", "with_fix", "label")
    error_first = ("error", "context", "debug", "detail", "retry_note", "with_fix", "label")

    assert tuple(inspect.signature(monitor.render_recovery_advice).parameters) == advice_first
    assert tuple(inspect.signature(monitor.render_recovery_error).parameters) == error_first + ("target_user_id",)
    # This tool's own parameters follow the shared ones, so a call written for a sibling still means the same thing
    assert tuple(inspect.signature(monitor.print_recovery_advice).parameters) == advice_first + ("tracker",)
    assert tuple(inspect.signature(monitor.print_recovery_error).parameters) == error_first + ("tracker", "target_user_id")


# The advice pair prints what the caller built, so a summary the classifier would never produce survives the trip
def test_the_advice_printer_does_not_reclassify(capsys):
    monitor.DEBUG_MODE = False
    advice = monitor.make_recovery_advice("network.timeout", "a summary no rule produces", "a fix of its own", True)

    returned = monitor.print_recovery_advice(advice)

    assert capsys.readouterr().out == "* Error: a summary no rule produces\nTo fix: a fix of its own\n"
    assert returned is advice


# The error pair classifies what the caller hands it, which is the difference between the two front doors
def test_the_error_printer_classifies_what_it_was_given(capsys):
    monitor.DEBUG_MODE = False

    returned = monitor.print_recovery_error(Exception("connection refused"), context="runtime")

    assert returned.code != "unknown"
    assert capsys.readouterr().out.startswith(f"* Error: {returned.summary}\n")


# Both front doors reach the same renderer, so the retry note, the label and a suppressed fix behave the same way
def test_both_front_doors_render_the_same_line():
    monitor.DEBUG_MODE = False
    error = Exception("connection refused")
    advice = monitor.classify_recovery_error(error, "runtime")

    through_advice = monitor.render_recovery_advice(advice, retry_note="retrying in 5 minutes", with_fix=False, label="Warning")
    through_error = monitor.render_recovery_error(error, "runtime", retry_note="retrying in 5 minutes", with_fix=False, label="Warning")

    assert through_advice == through_error
    assert through_advice == f"* Warning: {advice.summary} (retrying in 5 minutes)"


# The tracker decides only whether the fix repeats, and it does that after the caller has already allowed it
def test_the_tracker_suppresses_only_the_repeated_fix(capsys):
    monitor.DEBUG_MODE = False
    tracker = monitor.RecoveryHintTracker()

    monitor.print_recovery_error(Exception("connection refused"), "runtime", tracker=tracker)
    monitor.print_recovery_error(Exception("connection refused"), "runtime", tracker=tracker)

    printed = capsys.readouterr().out
    assert printed.count("* Error: ") == 2
    assert printed.count("To fix: ") == 1


# A detail that only repeats the summary spends a line saying nothing, so the block drops it and keeps a real one
def test_a_detail_repeating_the_summary_is_dropped():
    repeated = monitor.make_recovery_advice("unknown", "the same sentence twice", "a fix", False, "the same sentence twice")
    differing = monitor.make_recovery_advice("unknown", "the summary", "a fix", False, "the raw cause")

    assert "Technical detail:" not in monitor.render_recovery_advice(repeated, debug=True)
    assert "Technical detail: the raw cause" in monitor.render_recovery_advice(differing, debug=True)


# A run that already prints the technical cause cannot be told to re-run for it
def test_the_unrecognized_failure_fix_follows_the_diagnostic_mode(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    plain = monitor.classify_recovery_error(Exception("a wholly unfamiliar failure"), "runtime").fix
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    debugging = monitor.classify_recovery_error(Exception("a wholly unfamiliar failure"), "runtime").fix

    assert "--debug" in plain
    assert "--debug" not in debugging


# The only advice that names no page, and the reason no page covers it


# Verifies the backup name every tool in this family writes, so one documented shape covers them all
def test_the_backup_carries_the_family_name_and_mode(tmp_path):
    destination = tmp_path / "monitor.conf"
    destination.write_text("SETTING = 1\n", encoding="utf-8")

    backup_path = monitor.create_timestamped_backup(destination)

    assert re.fullmatch(r"monitor\.conf\.\d{14}\.bak", Path(backup_path).name)
    assert Path(backup_path).read_text(encoding="utf-8") == "SETTING = 1\n"
    assert stat.S_IMODE(Path(backup_path).stat().st_mode) == 0o600


# Verifies a second backup in the same second takes its own name rather than overwriting the first
def test_a_second_backup_in_the_same_second_keeps_the_first(tmp_path):
    destination = tmp_path / "monitor.conf"
    destination.write_text("first\n", encoding="utf-8")
    first = monitor.create_timestamped_backup(destination)
    destination.write_text("second\n", encoding="utf-8")

    second = monitor.create_timestamped_backup(destination)

    assert first != second
    assert Path(first).read_text(encoding="utf-8") == "first\n"
    assert Path(second).read_text(encoding="utf-8") == "second\n"


# Verifies a destination that is not there yet earns no backup, since there is nothing to copy
def test_a_missing_destination_earns_no_backup(tmp_path):
    assert monitor.create_timestamped_backup(tmp_path / "absent.conf") is None


# A status code is matched as a whole number, so an id or a path that happens to contain the digits is not that status
def test_a_status_code_inside_a_longer_number_is_not_matched():
    assert monitor.classify_recovery_error(RuntimeError("playlist 14290 unavailable"), "runtime").code != "spotify.rate_limited"
    assert monitor.classify_recovery_error(RuntimeError("delivery 14290 failed"), "webhook").code != "webhook.rate_limited"
    assert monitor.classify_recovery_error(RuntimeError("status 429 returned"), "runtime").code == "spotify.rate_limited"
    assert monitor.mentions_status_code("404", "user 14041 not visible") is False
    assert monitor.mentions_status_code("404", "http error 404 for playlist") is True
    assert monitor.mentions_status_code("429", "https://example.test/429/status") is False
    assert monitor.mentions_status_code("429", "HTTP 429 Too Many Requests") is True
    assert monitor.mentions_status_code("429", "request 14290 failed") is False

from pathlib import Path
import os
import re
import subprocess
import sys
import unicodedata
from unittest.mock import Mock

import pytest

import spotify_profile_monitor as monitor


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


# Verifies every runtime guide global resolves to a published documentation page and anchor
def test_guide_urls_match_documentation_anchors():
    guide_names = ("QUICK_START_GUIDE_URL", "INSTALLATION_GUIDE_URL", "CONFIG_GUIDE_URL", "COOKIE_GUIDE_URL", "MANUAL_COOKIE_GUIDE_URL", "CLIENT_GUIDE_URL", "TARGET_GUIDE_URL", "SMTP_GUIDE_URL", "WEBHOOK_GUIDE_URL", "SECRETS_GUIDE_URL", "INTERVALS_GUIDE_URL", "DOCTOR_GUIDE_URL", "OAUTH_GUIDE_URL", "OAUTH_USER_GUIDE_URL", "BROWSER_COOKIE_GUIDE_URL", "SETUP_GUIDE_URL")

    for name in guide_names:
        guide_url = getattr(monitor, name)
        assert guide_url.startswith(monitor.DOCUMENTATION_URL + "/"), name
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


# Verifies retired settings are reported to the caller so Doctor can surface them without printing
def test_config_load_reports_retired_settings_to_caller(tmp_path):
    config_path = tmp_path / "legacy.conf"
    config_path.write_text("TOTP_VER = 0\nTRUNCATE_CHARS = 120\n", encoding="utf-8")
    retired = []

    assert monitor.load_config_file(config_path, namespace={}, report_errors=False, retired_out=retired) is True
    assert retired == ["TOTP_VER"]


# Verifies ignoring retired names does not weaken rejection of any other unknown setting
def test_retired_allowance_does_not_accept_other_unknown_names():
    assert monitor.RETIRED_CONFIG_SETTINGS.isdisjoint(monitor._config_allowed_names())
    with pytest.raises(ValueError, match="unsupported configuration setting"):
        monitor.parse_config_content("TOTP_VERSION_TYPO = 1\n")


# Verifies the shipped config template still loads through the restricted parser
def test_config_template_parses_as_literals():
    parsed = monitor.parse_config_content(monitor.CONFIG_BLOCK, "<built-in-config>")

    assert parsed["LOCAL_TIMEZONE"] == "Auto"
    assert len(parsed) == len(monitor._config_allowed_names())


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

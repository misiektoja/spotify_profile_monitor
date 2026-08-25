"""Contract tests for governance documents, issue templates, workflows, repository metadata and declared versions."""

import configparser
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

import spotify_profile_monitor as monitor

yaml = pytest.importorskip("yaml")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIRECTORY = PROJECT_ROOT / ".github" / "workflows"


# Reads one repository file as text
def read_asset(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


# Reads one repository file as parsed YAML
def read_yaml_asset(relative_path: str):
    return yaml.safe_load(read_asset(relative_path))


class TestGovernanceDocuments:
    # Contributors are pointed to these documents from the README and templates, so a missing one is a broken promise
    def test_governance_documents_exist(self):
        for relative_path in ("SECURITY.md", "SUPPORT.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "THIRD_PARTY_NOTICES.md", "LICENSE", ".github/pull_request_template.md"):
            asset = PROJECT_ROOT / relative_path
            assert asset.is_file(), relative_path
            assert asset.stat().st_size > 200, relative_path

    # A CODEOWNERS entry is what actually requests review on every change
    def test_codeowners_covers_every_path(self):
        assert re.search(r"^\*\s+@\S+", read_asset(".github/CODEOWNERS"), re.M)

    # The policy must name the private reporting route, or reporters fall back to a public issue
    def test_security_policy_routes_reports_privately(self):
        policy = read_asset("SECURITY.md")
        assert "security/advisories/new" in policy
        assert "Do not open a public issue" in policy

    # Contributors need the setup, the checks and the branch to target
    def test_contributing_covers_setup_and_expectations(self):
        contributing = read_asset("CONTRIBUTING.md")
        for concept in ("pip install -e", "python -m pytest", "RELEASE_NOTES.md", "SECURITY.md", "GPL-3.0-or-later", "dev"):
            assert concept in contributing, concept

    # Every declared runtime dependency must carry a license attribution
    def test_third_party_notices_list_every_runtime_dependency(self):
        notices = read_asset("THIRD_PARTY_NOTICES.md")
        pyproject = read_asset("pyproject.toml")
        declared = re.search(r"^dependencies = \[(.*?)^\]", pyproject, re.S | re.M)
        assert declared is not None
        for requirement in re.findall(r'"([A-Za-z0-9_.-]+)', declared.group(1)):
            assert requirement.lower() in notices.lower(), requirement


class TestIssueTemplates:
    # Blank issues bypass the forms, and the contact links are what route vulnerabilities away from public issues
    def test_template_config_disables_blank_issues_and_links_reporting(self):
        config = read_yaml_asset(".github/ISSUE_TEMPLATE/config.yml")
        assert config["blank_issues_enabled"] is False
        urls = [link["url"] for link in config["contact_links"]]
        assert any("security/advisories/new" in url for url in urls)

    # A malformed form is silently ignored by GitHub, so every template must parse and declare its required parts
    def test_every_issue_template_is_well_formed(self):
        templates = sorted((PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml"))
        assert [path.name for path in templates] == ["bug_report.yml", "config.yml", "feature_request.yml"]
        for path in templates:
            if path.name == "config.yml":
                continue
            form = yaml.safe_load(path.read_text(encoding="utf-8"))
            assert form["name"] and form["description"]
            assert any(field.get("validations", {}).get("required") for field in form["body"]), path.name

    # The bug form is where a user is most likely to paste a secret, so it must warn first
    def test_bug_report_warns_before_collecting_output(self):
        bug_report = read_asset(".github/ISSUE_TEMPLATE/bug_report.yml")
        assert "SECURITY.md" in bug_report
        for secret in ("sp_dc", "refresh token", "webhook URL"):
            assert secret in bug_report, secret


class TestWorkflowSupplyChain:
    # Every third-party action is pinned to a commit, so a moved tag cannot change what runs with our secrets
    def test_actions_are_pinned_to_commit_shas(self):
        unpinned = []
        for workflow in sorted(WORKFLOW_DIRECTORY.glob("*.yml")):
            for match in re.finditer(r"uses:\s*(\S+)", workflow.read_text(encoding="utf-8")):
                reference = match.group(1)
                if reference.startswith("./"):
                    continue
                action, _, ref = reference.partition("@")
                if not re.fullmatch(r"[0-9a-f]{40}", ref):
                    unpinned.append(f"{workflow.name}: {reference}")
        assert unpinned == []

    # Each pin records the human-readable version so updates stay reviewable
    def test_pinned_actions_carry_a_version_comment(self):
        missing = []
        for workflow in sorted(WORKFLOW_DIRECTORY.glob("*.yml")):
            for line in workflow.read_text(encoding="utf-8").splitlines():
                if "uses:" in line and "@" in line and "./" not in line and not re.search(r"#\s*v?\d", line):
                    missing.append(f"{workflow.name}: {line.strip()}")
        assert missing == []

    # Event and input values never reach a shell directly, which would allow script injection
    def test_run_steps_do_not_interpolate_event_values(self):
        offenders = []
        for workflow in sorted(WORKFLOW_DIRECTORY.glob("*.yml")):
            for block in re.findall(r"run: \|(.*?)(?=\n      [-a-zA-Z]|\Z)", workflow.read_text(encoding="utf-8"), re.S):
                for line in block.splitlines():
                    if "${{" in line:
                        offenders.append(f"{workflow.name}: {line.strip()}")
        assert offenders == []

    # Publishing must run the suite first, or a broken build reaches PyPI under the project's name
    def test_pypi_publish_depends_on_the_test_suite(self):
        publish = read_yaml_asset(".github/workflows/publish.yml")
        assert publish["jobs"]["test"]["uses"] == "./.github/workflows/tests.yml"
        assert "test" in publish["jobs"]["build-n-publish"]["needs"]

    # The scanning workflows are the automated half of the security posture the policy describes
    def test_security_workflows_cover_code_and_supply_chain(self):
        for workflow_name in ("codeql.yml", "scorecard.yml", "supply-chain.yml", "tests.yml"):
            assert (WORKFLOW_DIRECTORY / workflow_name).is_file(), workflow_name

        codeql = read_yaml_asset(".github/workflows/codeql.yml")
        assert any("python" in str(job).lower() for job in codeql["jobs"].values())

        supply_chain = read_yaml_asset(".github/workflows/supply-chain.yml")
        assert {"gitleaks", "pip-audit", "sbom"} <= set(supply_chain["jobs"])

    # Dependabot must watch every ecosystem this repository actually declares
    def test_dependabot_watches_actions_and_python_dependencies(self):
        updates = read_yaml_asset(".github/dependabot.yml")["updates"]
        assert {"github-actions", "pip"} <= {entry["package-ecosystem"] for entry in updates}


class TestRepositoryMetadata:
    # Verifies the citation metadata GitHub renders stays parseable and describes this project
    def test_citation_describes_this_project(self):
        citation = read_yaml_asset("CITATION.cff")
        assert citation["cff-version"] == "1.2.0"
        assert citation["type"] == "software"
        assert citation["title"] == "spotify_profile_monitor"
        assert citation["message"]
        assert citation["license"] == "GPL-3.0-or-later"
        assert citation["repository-code"] == "https://github.com/misiektoja/spotify_profile_monitor"
        assert citation["date-released"].isoformat() == str(citation["date-released"])

        author = citation["authors"][0]
        assert author["given-names"] and author["family-names"] and author["alias"] == "misiektoja"

    # The sponsor button needs a target, since an empty file hides it without failing any check
    def test_funding_declares_a_sponsor_target(self):
        funding = read_yaml_asset(".github/FUNDING.yml")
        assert funding["github"] == "misiektoja"
        assert funding["buy_me_a_coffee"] == "misiektoja"

    # The shared editor settings must still declare the style the repository is written in
    def test_editor_configuration_declares_the_repository_style(self):
        settings = configparser.ConfigParser()
        settings.read_string("[editorconfig]\n" + read_asset(".editorconfig"))

        assert settings["editorconfig"]["root"] == "true"
        assert settings["*"]["charset"] == "utf-8"
        assert settings["*"]["end_of_line"] == "lf"
        assert settings["*"]["indent_style"] == "space"
        assert settings["*"]["indent_size"] == "4"
        assert settings["*"]["insert_final_newline"] == "true"
        assert settings["*"]["trim_trailing_whitespace"] == "true"
        assert settings["*.py"]["indent_size"] == "4"
        assert settings["*.{yml,yaml}"]["indent_size"] == "2"
        assert settings["*.toml"]["indent_size"] == "2"
        # Two trailing spaces are a Markdown line break, so they must stay exempt from trimming
        assert settings["*.md"]["trim_trailing_whitespace"] == "false"

    # An editor setting only warns on the machine that has it, so the tracked files are checked directly
    def test_tracked_text_files_obey_the_declared_whitespace_rules(self):
        listing = subprocess.run(["git", "ls-files"], cwd=PROJECT_ROOT, check=False, capture_output=True, text=True)
        if listing.returncode != 0:
            pytest.skip("not a git checkout")

        offenders = []
        for name in listing.stdout.split():
            asset = PROJECT_ROOT / name
            if not asset.is_file() or asset.suffix.casefold() in {".png", ".jpg", ".gif"}:
                continue
            content = asset.read_bytes()
            if b"\r\n" in content:
                offenders.append(f"{name}: CRLF line ending")
            if content and not content.endswith(b"\n"):
                offenders.append(f"{name}: missing final newline")
            # LICENSE is verbatim upstream text and Markdown keeps meaningful trailing spaces
            if name != "LICENSE" and asset.suffix.casefold() != ".md" and re.search(rb"[ \t]+\n", content):
                offenders.append(f"{name}: trailing whitespace")
        assert offenders == []

    # One CRLF commit from a Windows contributor would otherwise rewrite whole files
    def test_line_ending_policy_is_declared(self):
        attributes = read_asset(".gitattributes")
        assert "* text=auto eol=lf" in attributes
        for pattern in ("*.png binary", "*.jpg binary", "*.gif binary"):
            assert pattern in attributes

    # The support document must route each request to a channel that exists
    def test_support_document_routes_every_request_type(self):
        support = read_asset("SUPPORT.md")
        for destination in ("https://github.com/misiektoja/spotify_profile_monitor/discussions", "https://github.com/misiektoja/spotify_profile_monitor/security/advisories/new", "https://github.com/misiektoja/spotify_profile_monitor/issues/new?template=bug_report.yml", "https://github.com/misiektoja/spotify_profile_monitor/issues/new?template=feature_request.yml"):
            assert destination in support
        assert "spotify_profile_monitor --doctor" in support
        for concept in ("sp_dc", "SMTP passwords", "webhook URLs", "--debug"):
            assert concept in support

    # A locally clean commit must not still fail CI, so the hook and the pinned extra have to agree
    def test_local_hooks_match_the_pinned_linter(self):
        pinned = re.search(r'lint = \["ruff==([^"]+)"\]', read_asset("pyproject.toml"))
        assert pinned is not None

        hooks = read_yaml_asset(".pre-commit-config.yaml")["repos"]
        ruff_hook = next(entry for entry in hooks if "ruff-pre-commit" in entry["repo"])
        assert ruff_hook["rev"] == f"v{pinned.group(1)}"

        lint_steps = read_yaml_asset(".github/workflows/tests.yml")["jobs"]["lint"]["steps"]
        assert any("ruff check" in step.get("run", "") for step in lint_steps)

    # An unsigned download cannot be told apart from a tampered one, so releases carry checksums and provenance
    def test_release_archives_ship_checksums_and_provenance(self):
        job = read_yaml_asset(".github/workflows/release-assets.yml")["jobs"]["build-and-upload-assets"]
        assert job["permissions"]["attestations"] == "write"
        assert job["permissions"]["id-token"] == "write"

        assert any("sha256sum" in step.get("run", "") for step in job["steps"])
        assert any("attest-build-provenance" in step.get("uses", "") for step in job["steps"])

        upload = next(step for step in job["steps"] if "action-gh-release" in step.get("uses", ""))
        assert "_SHA256SUMS.txt" in upload["with"]["files"]


class TestVersionConsistency:
    # The module, its docstring and the package metadata must agree, since only one of them reaches a user
    def test_declared_versions_match(self):
        packaged = re.search(r'^version = "([^"]+)"', read_asset("pyproject.toml"), re.M)
        docstring = re.search(r"^v(\d+\.\d+(?:\.\d+)?)\s*$", monitor.__doc__ or "", re.M)

        assert packaged is not None and docstring is not None
        assert monitor.VERSION == packaged.group(1) == docstring.group(1)

    # The citation must name a version somebody can actually cite, so it tracks the newest dated release
    # notes section rather than the version under development
    def test_citation_tracks_the_newest_released_version(self):
        released = re.search(r"^# Changes in ([\d.]+) \((\d{1,2} \w{3} \d{4})\)", read_asset("RELEASE_NOTES.md"), re.M)
        citation = read_asset("CITATION.cff")
        cited_version = re.search(r'^version: "([^"]+)"', citation, re.M)
        cited_date = re.search(r"^date-released: (\d{4}-\d{2}-\d{2})", citation, re.M)

        assert released is not None and cited_version is not None and cited_date is not None
        assert cited_version.group(1) == released.group(1)
        assert cited_date.group(1) == datetime.strptime(released.group(2), "%d %b %Y").strftime("%Y-%m-%d")

    # Release notes must describe the version the code actually declares, or the notes ship ahead of the code
    def test_release_notes_lead_with_the_declared_version(self):
        newest = re.search(r"^# Changes in ([\d.]+)", read_asset("RELEASE_NOTES.md"), re.M)

        assert newest is not None
        assert newest.group(1) == monitor.VERSION

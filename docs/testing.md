# Testing

The [tests directory](https://github.com/misiektoja/spotify_profile_monitor/tree/main/tests/) contains an offline pytest suite for contributors. It checks target parsing, configuration effects, the setup wizard, browser cookie import, private `sp_dc` entry, Doctor, webhook delivery, notification escaping, playlist snapshot handling, download safety and repository contracts. Tests replace Spotify requests with local test doubles. Its [README](https://github.com/misiektoja/spotify_profile_monitor/blob/main/tests/README.md) maps every test file to the area it covers.

Install the test dependencies and run the suite from the repository root:

```sh
pip install -e '.[test]'
python -m pytest
```

The browser extra is needed only for the Chromium cookie import path. Without it, `test_browser_cookie_import.py` exercises the same absent-dependency behavior a user would see:

```sh
pip install -e '.[test,browser]'
```

The `notification-images` extra needs no separate install. The test extra already brings in Pillow, so the artwork tests covering email and ntfy attachments run from a plain `.[test]` install. If Pillow is missing anyway, those tests skip instead of failing.

A pinned [Ruff](https://docs.astral.sh/ruff/) lint pass runs alongside the suite. It selects defect rules only, pyflakes and bugbear, so it reports unused names, undefined names and common bug patterns without enforcing formatting or import order:

```sh
pip install -e '.[lint]'
python -m ruff check spotify_profile_monitor.py tests
```

GitHub Actions runs the linter, then the same suite on Python 3.9 through 3.14, plus a Windows job for the platform-sensitive behaviors: ANSI codepage text writes, reserved characters in artwork filenames, export path handling and the POSIX-only watchdog. See the [test workflow](https://github.com/misiektoja/spotify_profile_monitor/blob/main/.github/workflows/tests.yml).

The same suite gates every release. [Publishing to PyPI](https://github.com/misiektoja/spotify_profile_monitor/blob/main/.github/workflows/publish.yml) runs it first and stops if anything fails, so a release cannot ship ahead of a passing test run.

## Test Layers

The suite combines several test types:

- Unit and component tests exercise focused functions with deterministic inputs.
- Integration tests use temporary files, SQLite cookie databases and real loopback HTTP connections.
- Source-level sweeps prove properties that a single example cannot, such as every HTML email body escaping Spotify-supplied text.
- Contract tests validate governance documents, issue templates, action pinning, release gating, declared versions and repository metadata.

No test needs a real Spotify cookie, Protobuf login file, OAuth client secret, SMTP password or webhook URL. Loopback transport tests use fake credentials that are accepted only by temporary local servers.

Online tests that authenticate against Spotify are excluded, because automated logins could trigger account protection. A change to token handling, the monitoring loop or playlist retrieval is not verified by this suite alone. Exercise it against a real account and say so in the pull request.

## Supply Chain Checks

A separate [supply chain workflow](https://github.com/misiektoja/spotify_profile_monitor/blob/main/.github/workflows/supply-chain.yml) runs on every change and again weekly, so a vulnerability published after a merge is still caught. It scans the full commit history for leaked credentials with gitleaks, audits the resolved dependency tree with `pip-audit` and builds a CycloneDX software bill of materials that lists every package a user actually installs.

Two further workflows watch the code and the project setup. [CodeQL](https://github.com/misiektoja/spotify_profile_monitor/blob/main/.github/workflows/codeql.yml) runs GitHub's `security-extended` Python queries on every change and weekly, reporting findings as code scanning alerts. [OpenSSF Scorecard](https://github.com/misiektoja/spotify_profile_monitor/blob/main/.github/workflows/scorecard.yml) scores the repository's security practices, such as branch protection, action pinning and dependency update automation, and publishes the score shown as a badge on the project page.

Published archives stay verifiable: the [release assets workflow](https://github.com/misiektoja/spotify_profile_monitor/blob/main/.github/workflows/release-assets.yml) records SHA-256 checksums and signs a build provenance attestation, so an unsigned download can be told apart from a tampered one.

The pytest suite covers the workflows themselves. It fails when a third-party action is not pinned to a commit SHA, when a pin lacks its version comment or when a workflow passes an event value straight into a shell.

## Focused Test Commands

Run the documentation and repository contracts:

```sh
python -m pytest tests/test_repository_contracts.py
```

Run Doctor and setup coverage:

```sh
python -m pytest tests/test_doctor.py tests/test_setup_and_startup.py
```

Run notification and output safety tests:

```sh
python -m pytest tests/test_webhook_notifications.py tests/test_notification_escaping.py tests/test_untrusted_output.py
```

## Documentation Build

The documentation site is built with strict validation, so a broken link or a page missing from the navigation fails the build:

```sh
pip install -r docs/requirements.txt
mkdocs build --strict
```

## Conventions

- Keep everything offline. If a code path needs network access, stub it with `monkeypatch` rather than skipping the test.
- Restore module-level globals you change. Tests share one imported module, so a leaked global affects whatever runs next.
- Put disposable artifacts under `local/`, never in the repository root or the system temp directory.
- Never use a real cookie, Protobuf login file, OAuth client secret, SMTP password or webhook URL.

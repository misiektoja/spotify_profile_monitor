# Test suite

These tests cover logic in `spotify_profile_monitor.py` that can run without network access.
Functions that normally contact Spotify are replaced with test doubles, and several tests launch the
CLI in a subprocess with a prelude that makes any real network call raise. See
`test_config_effects.py` for an example.

## Running

From the repository root:

```bash
pip install -e '.[test]'
python -m pytest
```

`pyproject.toml` puts the repository root first on `sys.path`, so the tests use the working tree
instead of an installed copy of the module.

The browser extra is needed only for the Chromium cookie import path:

```bash
pip install -e '.[test,browser]'
```

Without it, `test_browser_cookie_import.py` exercises the same absent-dependency behavior a user
would see.

## Layout

| File | Area under test |
| --- | --- |
| `test_target_inputs.py` | Target normalization, rejection of unsafe forms, CLI and config precedence |
| `test_config_effects.py` | Config-file settings reaching their consumers, including polling cadence, playlist cache and connectivity |
| `test_recovery_and_parity.py` | Atomic config loading, refusal of executable config content, recovery advice and in-app guide links matching README anchors |
| `test_setup_and_startup.py` | Setup wizard flow, startup banner rendering and terminal screen preparation |
| `test_private_sp_dc.py` | `--set-sp-dc` validation, atomic dotenv updates and refusal to write on a bad cookie |
| `test_browser_cookie_import.py` | Firefox and Chromium profile discovery, cookie selection, deceptive-domain rejection and dotenv preservation |
| `test_web_playlist_backend.py` | TOTP generation and config, plus the generated config's token-source guidance |
| `test_playlist_snapshot_baseline.py` | Playlist baseline advancement on partial failure, removal confirmation and membership acceptance |
| `test_webhook_notifications.py` | Webhook URL validation, provider detection, startup rollups and `SIGHUP` reload |
| `test_notification_escaping.py` | Source-level sweep proving every HTML email body escapes Spotify-supplied text |
| `test_untrusted_output.py` | Terminal control-character stripping across the logger and output streams |
| `test_url_and_download_safety.py` | Spotify URI and URL conversion boundaries, host allowlists and bounded downloads |
| `test_runtime_deadlines.py` | Nested request alarms restoring the enclosing watchdog deadline, and the POSIX-only guard |
| `test_cleanup_and_compatibility.py` | Case-sensitive ID handling, UTF-8 CSV writes and export round-trips |
| `test_doctor.py` | `--doctor` environment, dependency, cookie and settings checks |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and declared versions plus repository metadata: citation, funding, line endings, the declared editor style, the pinned linter and release integrity |

## Conventions

* Keep everything offline. If a code path needs network access, stub it with `monkeypatch` rather
  than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a leaked global
  affects whatever runs next.
* Put disposable artifacts under `local/`, never in the repository root or the system temp
  directory.
* Never use a real cookie, Protobuf login file, OAuth client secret, SMTP password or webhook URL.

Online tests that authenticate against Spotify are excluded, because automated logins could trigger
account protection. A change to token handling, the monitoring loop or playlist retrieval is not
verified by this suite alone. Exercise it against a real account and say so in the pull request.

CI runs the same suite on Python 3.9 through 3.14, plus a Windows job for the platform-sensitive
behaviors: ANSI codepage text writes, reserved characters in artwork filenames, export path handling
and the POSIX-only watchdog. See [CONTRIBUTING.md](../CONTRIBUTING.md).

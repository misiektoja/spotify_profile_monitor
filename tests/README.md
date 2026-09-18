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
| `test_notification_receipts.py` | SMTP acceptance despite cleanup failures, receipt controls and unchanged notification content |
| `test_oauth_validation_boundaries.py` | Fresh OAuth validation and immediate resource failure with real HTTP clients |
| `test_configuration_notification_boundaries.py` | Invalid output settings, CLI precedence and strict webhook fields with legacy JSON support |
| `test_boundary_regressions.py` | Real notification transports, literal secret resolution and malformed startup paths |
| `test_resource_boundaries.py` | Optional network work stops after real transport resource exhaustion |
| `test_release_boundaries.py` | Real HTTP retries, Discord mention safety, unrenderable templates, SMTP password round trips, split terminal writes and the width cap without wcwidth |
| `test_compact_commands.py` | Literal short command prefixes, real help output and dependency hints |
| `test_release_safety.py` | Credential preservation, private error rendering, runtime timing validation and saved-state compatibility |
| `test_recovery_safety.py` | Real dotenv reloads, setup backups, oversized counts and provider-error privacy |
| `test_secret_policy.py` | Shared credential priority, reload ownership and setup destination conflicts |
| `test_startup_numeric_message.py` | Real offline startup names the invalid interval without debug mode |
| `test_smtp_error_privacy.py` | Short and escaped passwords in rejected SMTP sign-ins through commands, setup, Doctor and delivery |
| `conftest.py` | Shared fixture: exported secrets are cleared between tests, so a dotenv one test loads cannot change what a later one resolves |
| `test_setup_resolution_regressions.py` | Saved dotenv destinations, empty secrets, export precedence and recovery paths |
| `test_spotipy_request_policy.py` | TLS policy at the Spotipy request boundary for token exchanges and refreshes |
| `test_playlist_outage_integration.py` | Real monitoring flow for playlist outages, alert retries and confirmation counters |
| `test_playlist_glitch_confirmation.py` | Empty playlist responses confirmed by a re-read, and the startup baseline kept when one cannot be confirmed |
| `test_dotenv_quoted_keys.py` | Quoted dotenv keys, export prefixes, multiline values and duplicate removal |
| `test_startup_summary_channels.py` | Summary rows naming the webhook provider, the mail server, the masked recipient, the delivery confirmations and the runtime |
| `test_target_inputs.py` | Target normalization, rejection of unsafe forms, CLI and config precedence |
| `test_config_effects.py` | Config-file settings reaching their consumers, including polling cadence, playlist cache and connectivity |
| `test_recovery_and_parity.py` | Atomic config loading, refusal of executable config content, recovery advice, in-app guide links matching published documentation anchors and the documentation site contract |
| `test_setup_and_startup.py` | Setup wizard flow, startup banner rendering and terminal screen preparation |
| `test_private_sp_dc.py` | `--set-sp-dc` validation, atomic dotenv updates and refusal to write on a bad cookie |
| `test_browser_cookie_import.py` | Firefox and Chromium profile discovery, cookie selection, deceptive-domain rejection and dotenv preservation |
| `test_follow_snapshot.py` | Unavailable follow data, restart history, first available baselines and confirmed zero counts |
| `test_oauth_user_playlists.py` | Current playlist item shapes, pagination, older route compatibility and per-playlist OAuth restrictions |
| `test_web_playlist_backend.py` | TOTP generation and config, plus the generated config's token-source guidance |
| `test_playlist_snapshot_baseline.py` | Playlist baseline advancement on partial failure, removal confirmation and membership acceptance |
| `test_webhook_notifications.py` | Webhook URL validation, provider detection, startup rollups and `SIGHUP` reload |
| `test_monitoring_loop.py` | Error alert timing in the monitoring loop: a retryable outage alerts once it has lasted the alert delay and a failure that cannot clear itself alerts at once |
| `test_notification_escaping.py` | Source-level sweep proving every HTML email body escapes Spotify-supplied text |
| `test_untrusted_output.py` | Terminal control-character stripping across the logger, output streams and early-exit listing modes |
| `test_help_screen.py` | The `--help` screen: the shared argument group names, the task-grouped examples and the startup banner |
| `test_tls_verification.py` | Every connection honouring `VERIFY_SSL` and the single shared TLS context builder |
| `test_terminal_color.py` | Coloured terminal output: theme resolution, line rules, the colour-aware sanitizer, plain log files and the uncoloured progress lines |
| `test_url_and_download_safety.py` | Spotify URI and URL conversion boundaries, host allowlists and bounded downloads |
| `test_runtime_deadlines.py` | Nested request alarms restoring the enclosing watchdog deadline, and the POSIX-only guard |
| `test_cleanup_and_compatibility.py` | Case-sensitive ID handling, UTF-8 CSV writes and export round-trips |
| `test_doctor.py` | `--doctor` environment, dependency, cookie and settings checks |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and declared versions plus repository metadata: citation, funding, line endings, the declared editor style, the pinned linter and release integrity |
| `test_moved_private_settings.py` | Kept credentials across dotenv destination changes and startup error handling |

## Conventions

* Keep everything offline. If a code path needs network access, stub it with `monkeypatch` rather
  than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a leaked global
  affects whatever runs next.
* Exported secrets are cleared before every test by the autouse fixture in `conftest.py`, because
  loading a dotenv writes them into `os.environ` and nothing removes them again. Set the one a test
  needs with `monkeypatch.setenv` inside that test.
* Write disposable artifacts to pytest's `tmp_path` or to the gitignored `local/` directory the
  existing tests use. Do not leave them in the repository root.
* Never use a real cookie, Protobuf login file, OAuth client secret, SMTP password or webhook URL.

Online tests that authenticate against Spotify are excluded, because automated logins could trigger
account protection. A change to token handling, the monitoring loop or playlist retrieval is not
verified by this suite alone. Exercise it against a real account and say so in the pull request.

CI runs the same suite on Python 3.9 through 3.14, plus a Windows job for the platform-sensitive
behaviors: ANSI codepage text writes, reserved characters in artwork filenames, export path handling
and the POSIX-only watchdog. See [CONTRIBUTING.md](../CONTRIBUTING.md).

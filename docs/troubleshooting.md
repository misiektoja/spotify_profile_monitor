# Troubleshooting

Examples on this page use the PyPI command `spotify_profile_monitor`. If you installed the manual script, replace that command with the matching [command prefix](usage.md#command-format).

<a id="doctor-preflight"></a>
## Doctor Preflight

Run Doctor before unattended monitoring:

```sh
spotify_profile_monitor --doctor <spotify_target>
```

Each row is marked `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`, colour-coded by status when colour output is on. Every `[WARN]` and `[FAIL]` row carries an indented `To fix:` line under its marker, plus a `Guide:` link when a documentation page covers that row. A `[SKIP]` row names a check that could not run and says why.

Doctor checks **Environment**, **Configuration**, **Authentication**, **Metadata**, **Connectivity**, **Target** and **Notifications**. It reports active files, secret sources, output destinations, timezone and [TLS verification](configuration.md#tls-verification). Secret values are not displayed. Notification checks validate email sign-in and webhook settings without sending a message.

If legacy OAuth app credentials and a playlist are available, Doctor checks playlist access. If Spotify accepts the credentials but rejects the playlist request, it warns that monitoring will use the web-player backend.

In an interactive terminal, Doctor offers one real test message per ready notification channel. Each prompt defaults to No and requires separate approval. Ctrl+C ends the report. Warnings do not fail the command. A failed check or approved delivery test returns a nonzero exit status.

Follow the report's **Next steps** after correcting any failed checks. The printed start command uses the configuration and dotenv files you checked.

<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** reports changes, warnings and errors.
- **Verbose mode (`--verbose`)** adds the full startup summary, operational changes and alert delivery confirmations. Set `DELIVERY_CONFIRMATIONS = False` to hide those confirmations.
- **Debug mode (`--debug`)** adds request details, polling activity and technical diagnostics. It also keeps existing terminal output on screen.

Delivery confirmations name the email recipient or webhook provider without repeating the subject or message body. `DELIVERY_CONFIRMATIONS = False` hides those optional success receipts. Event output, send attempts and errors remain visible. Explicit notification tests report their result once. Generated email subjects and webhook titles use readable service names without a program-name prefix.

The expanded startup summary includes active files, secret sources, notification settings and runtime information. Secret values are hidden.

```sh
spotify_profile_monitor <spotify_target> --verbose
spotify_profile_monitor <spotify_target> --debug
```

During quiet monitoring, `* Monitoring healthy for <spotify_target>` confirms the tool is still running. `LIVENESS_CHECK_INTERVAL` defaults to 86400 seconds (24 hours). Set it to `0` to disable this reminder.

Failures show an error and a `To fix:` action. A continuing outage produces a `* Monitoring degraded` reminder once an hour, even when liveness reminders are disabled. `* Monitoring recovered` marks recovery. Follow any new instructions if the failure changes. Use `--debug` for technical error details.

Cookies, tokens, passwords, authorization headers and webhook URLs are redacted from verbose and debug output, so sanitized output is safe to attach to a GitHub issue.

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening an issue.

<a id="common-problems"></a>
## Common Problems

| Symptom | Likely cause | Where to look |
| --- | --- | --- |
| `sp_dc` cookie rejected or expired | The monitoring account signed out or Spotify rotated the session | [Spotify sp_dc Cookie](configuration.md#spotify-sp_dc-cookie) then rerun `--set-sp-dc` or [browser import](setup-and-first-run.md#browser-cookie-import) |
| Playlists show as `[ RESTRICTED ]` | Spotify returns 403 or 404 for that playlist through both backends | [Restricted Playlists](usage.md#restricted-playlists-spotify-api-404) |
| Followings or followers are missing | The active token source does not expose them | [Spotify access token source](configuration.md#spotify-access-token-source) |
| Username search (`-s`) returns nothing | `SP_SHA256` is not configured | [Spotify sha256](configuration.md#spotify-sha256-optional) |
| Refresh token expired in `client` mode | The intercepted login request body is stale | [Spotify Desktop Client](configuration.md#spotify-desktop-client) then re-export and send `SIGHUP` |
| Emails never arrive | Incomplete SMTP settings | [SMTP Settings](configuration.md#smtp-settings) then run `--send-test-email` |
| Webhook alerts never arrive | Provider mismatch or a redirecting destination | [Webhook Settings](configuration.md#webhook-settings) then run `--send-test-webhook` |
| "null bytes" error reading the config file | PowerShell redirection wrote UTF-16 | [Configuration File](configuration.md#configuration-file) |
| Artwork missing from alerts | The optional artwork extra is not installed | [Install from PyPI](installation.md#install-from-pypi) |
| Escape sequences such as `[36m` printed as text, or no colour at all | The terminal cannot display ANSI colour, or colour was switched off by `--no-color`, `COLORED_OUTPUT`, `NO_COLOR`, a redirect or an unset `TERM` | [Terminal Colours](configuration.md#terminal-colours) |

## Invalid saved settings and state

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

If a saved playlist, follower or following file has an invalid structure, monitoring stops before replacing it. Correct the named file or move it aside to start a fresh baseline. Keep a copy if you need the old history. Older valid records and extra trailing metadata remain accepted.

Malformed path settings and color-theme values are reported by Doctor with the setting name. Invalid color values are ignored while rendering help so you can still find the configuration commands.

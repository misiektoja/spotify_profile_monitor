# Troubleshooting

Examples on this page use the PyPI command `spotify_profile_monitor`. If you installed the manual script, replace that command with the matching [command prefix](usage.md#command-format).

<a id="doctor-preflight"></a>
## Doctor Preflight

Run Doctor before unattended monitoring:

```sh
spotify_profile_monitor --doctor <spotify_target>
```

Each row is marked `[PASS]`, `[WARN]`, `[FAIL]` or `[SKIP]`, colour-coded by status when colour output is on. Every `[WARN]` and `[FAIL]` row carries an indented `To fix:` line under its marker, plus a `Guide:` link when a documentation page covers that row. A `[SKIP]` row names a check that could not run and says why.

Doctor shows the current check phase, opens with the raw install method, then groups its rows into **Environment** for the Python version and the required dependencies, **Configuration** for the config and dotenv files, the numeric settings and the output destinations, **Authentication** for the Spotify sign-in, **Metadata** for the metadata backend, **Connectivity** for the endpoint it checks, **Target** for one optional target and **Notifications** for the alert channels. A section with nothing to report is left out. When optional legacy OAuth app credentials and a target playlist are available, Doctor makes a live playlist metadata request. This distinguishes successful token issuance from actual legacy playlist access. If Spotify issues a token but rejects the playlist endpoint, Doctor warns that normal monitoring will use the web-player backend. It names the dotenv file it loaded and lists which secrets are in effect and where each effective value came from. Secret names are listed, never their values. Output destination rows name each file monitoring would write and say so when CSV or log output is disabled. Doctor resolves `LOCAL_TIMEZONE`, reporting the detected zone when the setting is `Auto` and failing when the zone is invalid or cannot be detected. It also reports whether [TLS verification](configuration.md#tls-verification) is on, and warns while it is off. The Notifications section signs in to the configured SMTP server and checks webhook settings without sending a message, and each ready row lists the alert categories that channel would deliver.

When a terminal is interactive and passive checks pass, Doctor separately offers one real email test and one real webhook test. Each prompt defaults to No. Ctrl+C at either prompt ends the run rather than declining one test and asking the next. Warnings do not fail the command. A failed check or approved delivery test returns a nonzero exit status. The `Summary` line is printed after the tests finish and counts their results, so the sentence and the exit code always describe the same run.

The report ends with a **Next steps** block naming the command that starts monitoring, carrying the same `--config-file` and `--env-file` this run checked. It carries the target this run used, leaves it out when the configuration file already supplies one and otherwise shows `<spotify_target>` for you to replace. While a check is failing it asks for the failures first.


<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** keeps startup output compact and reports profile changes, warnings and errors
- **Verbose mode (`--verbose`)** adds the complete startup summary, infrequent operational transitions such as metadata backend changes and a line naming where each delivered alert went. It prints nothing per check, so an uneventful run stays quiet
- **Debug mode (`--debug`)** adds sanitized HTTP flow, scheduling details and internal diagnostics. Each line names the operation, then lists its details as comma-separated `key=value` fields, and every outbound call reports `outcome=OK` or `outcome=failed`. A `--debug` run leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen. `--verbose` clears it like an ordinary run.

Either mode also expands the startup summary with the detected install method and the names of the secrets that came from the dotenv file, the environment or the configuration file. Secret values never appear.

```sh
spotify_profile_monitor <spotify_target> --verbose
spotify_profile_monitor <spotify_target> --debug
```

Recoverable failures use a short `Error`, `To fix` and relevant guide format. A command in the fix text matches how you installed the tool and carries the `--config-file` or `--env-file` you started with, so it can be pasted as it is. The banner that says nothing changed prints in any mode: `* Monitoring healthy for <spotify_target>` with what was checked, followed by `Liveness check, timestamp:`. It is timed rather than counted in checks, so it appears once per `LIVENESS_CHECK_INTERVAL` of quiet, measured from the last thing the run printed. A monitoring failure is reported as `* Error: <what failed> (retrying in <time>)`, with the `To fix:` paragraph under it the first time that category appears. Every monitor in this family prints that same line. During a long outage the failure is reported in full once, then the liveness banner takes over with `* Monitoring degraded for <spotify_target>` and the summary of what is still failing, so a broken run keeps saying it is alive without repeating the same paragraph. The reminder follows the same clock, so an outage that retries faster than the normal polling interval does not report more often. When the failure clears, `* Monitoring recovered for <spotify_target>` reports how long it lasted. Setting `LIVENESS_CHECK_INTERVAL` to 0 removes the banner that carries the reminder, so the one-line summary goes back to printing on every check. Raw exception detail is shown only in debug mode.

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

# Troubleshooting

Examples on this page use the PyPI command `spotify_profile_monitor`. If you installed the manual script, replace that command with the matching [command prefix](usage.md#command-format-by-installation-method).

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

<a id="common-problems"></a>
## Common Problems

Every failure is reported in the same three-part shape: what went wrong, a `To fix:` action and a `Guide:` link to the page that covers it. The fix command matches how you installed the tool and carries the `--config-file` or `--env-file` you started with, so it can be pasted as it is. `--debug` appends a `Technical detail:` line for bug reports. Secrets are redacted from all three.

| Symptom | Likely cause | Where to look |
| --- | --- | --- |
| `sp_dc` cookie rejected or expired | The monitoring account signed out or Spotify rotated the session | [Spotify sp_dc Cookie](configuration.md#spotify-sp_dc-cookie) then rerun `--set-sp-dc` or [browser import](setup-and-first-run.md#import-a-spotify-login-from-a-browser) |
| Playlists show as `[ RESTRICTED ]` | Spotify returns 403 or 404 for that playlist through both backends | [Restricted Playlists](usage.md#restricted-playlists-spotify-api-403404) |
| Followings or followers are missing | The active token source does not expose them | [Spotify Access Token Source](configuration.md#spotify-access-token-source) |
| Username search (`-s`) returns nothing | `SP_SHA256` is not configured | [Spotify sha256](configuration.md#spotify-sha256-optional) |
| Refresh token expired in `client` mode | The intercepted login request body is stale | [Spotify Desktop Client](configuration.md#spotify-desktop-client) then re-export and send `SIGHUP` |
| Emails never arrive | Incomplete SMTP settings | [SMTP Settings](configuration.md#smtp-settings) then run `spotify_profile_monitor --send-test-email` |
| Webhook alerts never arrive | Provider mismatch or a redirecting destination | [Webhook Settings](configuration.md#webhook-settings) then run `spotify_profile_monitor --send-test-webhook` |
| "null bytes" error reading the config file | PowerShell redirection wrote UTF-16 | [Configuration File](configuration.md#configuration-file) |
| Artwork missing from alerts | The optional artwork extra is not installed | [Install from PyPI](installation.md#install-from-pypi) |
| Escape sequences such as `[36m` printed as text or no colour at all | The terminal cannot display ANSI colour or colour was switched off | [Terminal Colours Look Wrong](#terminal-colours-look-wrong) |

A continuing outage produces a `* Monitoring degraded` reminder once an hour, even when the [liveness reminder](usage.md#liveness-reminder) is switched off. `* Monitoring recovered` marks recovery. Use `--verbose` to see the first failed check.

<a id="terminal-colours-look-wrong"></a>
## Terminal Colours Look Wrong

If escape sequences such as `[36m` appear as literal text, the terminal does not understand ANSI colour. Start the tool with `--no-color` or set `COLORED_OUTPUT = False` in the configuration file. On Windows, `pip install colorama` fixes the classic Command Prompt.

If colour is missing where you expect it, check in this order: `--no-color` on the command line, `COLORED_OUTPUT` in the configuration file, a `NO_COLOR` environment variable and whether output is redirected or piped. Colour is switched off in all of those cases and also when `TERM` is unset or set to `dumb`.

Log files never contain colour by design. To colour a saved log while reading it, see [Coloring Log Output with GRC](usage.md#coloring-log-output-with-grc).

To change which colours are used, see [Terminal Colours](configuration.md#terminal-colours).

<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** reports activity changes and important errors
- **Verbose mode (`--verbose`)** adds occasional state changes, a line naming where each delivered alert went and a complete startup summary without private values. Set `DELIVERY_CONFIRMATIONS = False` to keep verbose mode without those delivery lines
- **Debug mode (`--debug`)** adds sanitized request flow, scheduling details and internal diagnostics

Delivery confirmations name the recipient or webhook provider. `DELIVERY_CONFIRMATIONS = False` hides these optional success messages. Monitoring events, send attempts and errors remain visible.

Both `--verbose` and `--debug` show the complete startup summary, including notification settings and credential sources. Use it to check which configuration is active without displaying private values.

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening a GitHub issue.

<a id="verbose-and-debug-output"></a>
## Verbose and Debug Output

`--verbose` adds the decisions a run made, in the same `*` lines as the rest of the output:

```sh
spotify_profile_monitor <spotify_target> --verbose
```

`--debug` traces what the tool is doing in timestamped `[DEBUG HH:MM:SS]` lines:

```sh
spotify_profile_monitor <spotify_target> --debug
```

Lines with details read `Operation: key=value, key=value`. Fields depend on the operation. Some results report `outcome=OK`, `failed`, `degraded` or `skipped`.

<a id="installation-and-command-problems"></a>
## Installation and Command Problems

If Python or `pip` is missing, use the [Python install walkthrough](installation.md#new-to-python-check-and-install).

If `spotify_profile_monitor` is not found after installation, close the terminal and open it again. On Windows with Python Install Manager, run `py install --refresh` to refresh command aliases. For a pipx installation, run `pipx ensurepath` then reopen the terminal. If you downloaded the script, use the [manual command](usage.md#command-format-by-installation-method) from its directory.

If `pip` reports an externally managed environment, follow the pipx steps in [Installation](installation.md#install-spotify-profile-monitor). Use `pipx upgrade spotify_profile_monitor` for later upgrades.

If the tool cannot import a dependency, install the dependencies with the same Python interpreter that runs the script. On macOS or Linux use `python3 -m pip install -r requirements.txt`. On Windows use `python -m pip install -r requirements.txt`. Match the requirements file to your downloaded script.

If a new terminal cannot find your saved settings, return to the directory used during setup or pass both `--config-file` and `--env-file` explicitly. Run `spotify_profile_monitor --doctor` to see which settings are loaded.

<a id="invalid-saved-settings-and-state"></a>
## Invalid saved settings and state

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

If a saved playlist, follower or following file has an invalid structure, monitoring stops before replacing it. Correct the named file or move it aside to start a fresh baseline. Keep a copy if you need the old history. Older valid records and extra trailing metadata remain accepted.

Malformed path settings and color-theme values are reported by Doctor with the setting name. Invalid color values are ignored while rendering help so you can still find the configuration commands.

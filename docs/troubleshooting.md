# Troubleshooting

Examples on this page use the PyPI command `spotify_profile_monitor`. If you installed the manual script, replace that command with the matching [command prefix](usage.md#command-format).

<a id="doctor-preflight"></a>
## Doctor Preflight

Run Doctor before unattended monitoring:

```sh
spotify_profile_monitor --doctor <spotify_target>
```

Doctor shows the current check phase then reports the Python environment and required dependencies, config and dotenv files, numeric settings, output destinations, Spotify authentication, metadata backend, connectivity, one optional target and notification settings.

When a terminal is interactive and passive checks pass, Doctor separately offers one real email test and one real webhook test. Each prompt defaults to No. Warnings do not fail the command. A failed check or approved delivery test returns a nonzero exit status.


<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** keeps startup output compact and reports profile changes, warnings and errors
- **Verbose mode (`--verbose`)** adds the complete startup summary plus infrequent operational transitions such as token refreshes or metadata backend changes
- **Debug mode (`--debug`)** adds sanitized HTTP flow, scheduling details and internal diagnostics

```sh
spotify_profile_monitor <spotify_target> --verbose
spotify_profile_monitor <spotify_target> --debug
```

Recoverable failures use a short `Error`, `To fix` and relevant guide format. Repeated monitoring failures keep the short error visible but suppress unchanged recovery instructions until the operation succeeds or the failure category changes. Raw exception detail is shown only in debug mode.

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

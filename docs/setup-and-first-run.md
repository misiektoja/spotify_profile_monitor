# Setup & First Run

This page covers the first run: the setup wizard, importing a Spotify login from your browser and starting monitoring. Examples use the PyPI command `spotify_profile_monitor`. Manual script users should replace that command with `python3 spotify_profile_monitor.py` on macOS or Linux, or `python spotify_profile_monitor.py` on Windows.

<a id="before-you-start"></a>

## Before you start

The easiest path is the interactive wizard:

```sh
spotify_profile_monitor --setup
```

The wizard asks for the target, authentication, polling interval, optional email or webhook alerts and output files. Review or change each section before saving. Settings go to `spotify_profile_monitor.conf` and private values go to `.env`.

For manual setup you need two values:

1. A Spotify target for the person you want to monitor. The easiest form is the complete profile URL copied from Spotify. A `spotify:user:` URI or user ID is also accepted. See [How to Find a Friend's Spotify Profile URL](configuration.md#how-to-find-a-friends-spotify-profile-url).
2. The `sp_dc` login cookie from the Spotify account used for monitoring. Follow the [manual cookie extraction steps](configuration.md#manual-cookie-extraction) and treat this value like a password.

In commands below, `<spotify_target>` means any accepted profile URL, `spotify:user:` URI or user ID.

Save the cookie through the hidden prompt:

```sh
spotify_profile_monitor --set-sp-dc
```

The command validates the cookie with Spotify before saving `SP_DC_COOKIE` to `.env`. The value is not displayed or placed in shell history. Do not share the generated `.env` file or commit it to a repository.

Start monitoring profile and playlist changes:

```sh
spotify_profile_monitor <spotify_target>
```

Or if you installed [manually](installation.md#manual-installation):

```sh
python3 spotify_profile_monitor.py <spotify_target>
```

To get the list of all supported command-line arguments / flags:

```sh
spotify_profile_monitor --help
```

<a id="setup-wizard"></a>
## Setup Wizard

Run `spotify_profile_monitor --setup` in an interactive terminal. Press Enter to accept each displayed default. The final setup summary contains no secret values and offers these actions:

* Save settings.
* Review or change target, authentication, polling, email, webhook or file destinations.
* Discard every answer without changing the destination files.

Setup asks before replacing an existing configuration and keeps a timestamped backup. A rerun uses saved settings as defaults. Declining a section disables it. After saving, setup can run Doctor and start monitoring. See [Storing Secrets](configuration.md#storing-secrets) for backup details.

Use `--config-file PATH` and `--env-file PATH` or the summary's **File destinations** section to choose other files. Both paths must be writable. `--config-file none` and `--env-file none` are not supported by setup.

Setup validates your `sp_dc` cookie and checks email sign-in without sending a message. Invalid answers can be retried. If the mail server is unreachable, check the saved settings later with `--doctor`.

When you enable email or ntfy alerts, setup offers artwork attachments. If the optional Pillow package is missing it says so and can install the `notification-images` extra for you, then enables the matching setting only when the install succeeds. Declining keeps the alerts text-only.

Polling intervals accept seconds or readable durations such as `90`, `2m`, `1.5h` or `1h 30m`.

Use the printed commands for the next steps. For manual installations, see [Command Format](usage.md#command-format).

<a id="browser-cookie-import"></a>
## Browser Cookie Import

First open [Spotify Web Player](https://open.spotify.com/) in the selected browser and sign in to the Spotify account used for monitoring. Then run:

```sh
spotify_profile_monitor --import-browser-cookie --browser firefox
```

Supported sources are Firefox, Chrome, Brave and Chromium. Firefox works on macOS, Linux and Windows without an extra package. Chromium import works on macOS and Linux with the `browser` extra. If that extra is missing, setup can install it through the active Python interpreter after approval. Current Chromium app-bound encryption prevents reliable import on Windows, so use Firefox there.

Select a browser profile if prompted. The importer validates its Spotify login and saves `SP_DC_COOKIE` to the selected dotenv file. Replacing a saved cookie needs confirmation or `--force` in a noninteractive script. Other dotenv settings are preserved.

Useful overrides are `--browser-profile PROFILE`, `--cookie-file PATH` and `--env-file PATH`.

<a id="next-step"></a>
## Next Step

Run [Doctor](troubleshooting.md#doctor-preflight) before an unattended run to confirm authentication, connectivity and notification settings.

For every configurable setting, see [Configuration](configuration.md). For monitoring options, listing commands, notifications and output files, see [Usage](usage.md).

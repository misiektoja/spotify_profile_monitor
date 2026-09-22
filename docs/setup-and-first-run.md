# Setup & First Run

<a id="run-the-setup-wizard"></a>
## Run the setup wizard

Already installed? Run the setup command below for your installation and follow the prompts. Otherwise, start with [Installation](installation.md).

Setup asks who to monitor, how to connect to Spotify, how often to check and which alerts and output files you want. You can review your answers before saving. Regular settings go in `spotify_profile_monitor.conf` and private values go in `.env`. Keep `.env` private.

Press Enter to accept a default or Ctrl+C to cancel. Cancelling before saving leaves your files untouched. Cancelling after saving keeps the saved settings. For changes to an existing setup, see [Configuration File](configuration.md#configuration-file).

After saving, follow the offered Doctor checks and monitoring steps.

=== "PyPI"

    ```sh
    spotify_profile_monitor --setup
    ```

=== "Manual Python script on macOS or Linux"

    ```sh
    python3 spotify_profile_monitor.py --setup
    ```

=== "Manual Python script on Windows"

    ```powershell
    python spotify_profile_monitor.py --setup
    ```

A **target** is the Spotify user whose profile and playlists you want to monitor. The **monitoring account** is the Spotify account represented by your saved login cookie or client credentials. They are normally different accounts.

The wizard recommends importing the monitoring account's saved Firefox login. On macOS and Linux it can also import from Chrome, Brave or Chromium. Those three browsers require the optional `pycookiecheat` package. If it is missing, the wizard can install it in a local Python installation.

The polling prompt accepts plain seconds or the `s`, `m`, `h` and `d` units. It shows both the seconds and a readable form of the default.

With a saved target, running Spotify Profile Monitor without a target starts monitoring that user. If no target is saved, an interactive no-argument run offers setup.

<a id="before-you-start"></a>
## Before you start

You need two things before the first monitoring run:

1. A Spotify target. The easiest form is the complete profile URL copied from Spotify. A `spotify:user:` URI or a bare user ID also works. See [How to Find a Friend's Spotify Profile URL](configuration.md#how-to-find-a-friends-spotify-profile-url).
2. Working authentication for a Spotify account. The default `cookie` token source uses the `sp_dc` login cookie of the monitoring account. See [Spotify Access Token Source](configuration.md#spotify-access-token-source) for the `client`, `oauth_app` and `oauth_user` alternatives.

Spotify might withhold some data for you, for example follower and following lists can be unavailable and playlists the Web API refuses are reported as `[ RESTRICTED ]` with reduced detail. See [Unavailable Followers and Followings](usage.md#unavailable-followers-and-followings) and [Restricted Playlists](usage.md#restricted-playlists-spotify-api-403404).

<a id="not-sure-which-command-you-need"></a>
## Not sure which command you need?

| I want to... | Run this |
| --- | --- |
| Set up Spotify Profile Monitor for the first time | Use the setup command for your installation above |
| Start monitoring with existing authentication | `spotify_profile_monitor <spotify_target>`, where the target is a complete profile URL, `spotify:user:` URI or user ID |
| Start the target saved in `TARGET_USER_URI_ID` | `spotify_profile_monitor --config-file spotify_profile_monitor.conf` |
| Check dependencies, authentication, connectivity and one target | `spotify_profile_monitor --doctor <spotify_target>` |
| Import a Spotify login from Firefox | Open [Spotify Web Player](https://open.spotify.com/) in Firefox, sign in then run `spotify_profile_monitor --import-browser-cookie --browser firefox` |
| Most securely enter or replace a manually extracted `SP_DC_COOKIE` | Run `spotify_profile_monitor --set-sp-dc` and enter `sp_dc` at the hidden prompt |
| Save an SMTP password for email alerts | Run `spotify_profile_monitor --set-smtp-password` |
| Send a test email | Run `spotify_profile_monitor --send-test-email` |
| Set up webhook alerts | Run the setup wizard and choose webhook alerts |
| Save a new webhook URL | Run `spotify_profile_monitor --set-webhook-url` |
| Send a test webhook | Run `spotify_profile_monitor --send-test-webhook` |
| Show profile details, followers, followings and playlist statistics | `spotify_profile_monitor -i <spotify_target>` |
| Display or export the tracks of one playlist | `spotify_profile_monitor -l PLAYLIST_URL -b tracks.csv` |
| Find a Spotify user ID by name | `spotify_profile_monitor -s "user name"` |
| List every supported command-line flag | `spotify_profile_monitor --help` |

<a id="run-individual-commands"></a>
## Run Individual Commands

The examples below use PyPI. For a manual script, replace `spotify_profile_monitor` with `python3 spotify_profile_monitor.py` on macOS or Linux. Use `python spotify_profile_monitor.py` on Windows and run it from the directory holding the script or give its full path. See [Command Format by Installation Method](usage.md#command-format-by-installation-method).

Throughout this page `<spotify_target>` means any accepted target form: a complete Spotify profile URL, a `spotify:user:` URI or a bare user ID.

<a id="import-a-spotify-login-from-a-browser"></a>
### Import a Spotify login from a browser

To configure authentication without the wizard, first open [Spotify Web Player](https://open.spotify.com/) in the chosen browser and sign in to the monitoring account. Then import that browser login:

```sh
spotify_profile_monitor --import-browser-cookie --browser firefox
```

Supported sources are Firefox, Chrome, Brave and Chromium. Firefox works on macOS, Linux and Windows without an extra package. Chromium import works on macOS and Linux with the `browser` extra. If that extra is missing, setup can install it through the active Python interpreter after approval. Current Chromium app-bound encryption prevents reliable import on Windows, so use Firefox there.

Select a browser profile if prompted. The importer validates its Spotify login and saves `SP_DC_COOKIE` to the selected dotenv file. Replacing a saved cookie needs confirmation or `--force` in a noninteractive script. Other dotenv settings are preserved.

In guided setup, each browser choice reports how many of its profiles hold a current Spotify login, so you can pick
one before opening the profile list. If an import does not complete, setup offers to retry, to import from a
different browser, to enter the cookie privately or to finish and authenticate later.

Useful overrides are `--browser-profile PROFILE`, `--cookie-file PATH` and `--env-file PATH`. For the browser table, profile selection and the browser extra, see [Which browsers are supported](configuration.md#which-browsers-are-supported).

If browser import is not available, use the [manual cookie extraction](configuration.md#manual-cookie-extraction) fallback.

### Save a manually extracted cookie

For a manually extracted cookie, `--set-sp-dc` is the recommended and most secure entry method. The command reads `sp_dc` through a hidden prompt, so the value does not appear on screen or in the command line. It validates the cookie with Spotify before updating only `SP_DC_COOKIE`. If validation fails, it does not change the `.env` file. Replacing an existing cookie requires confirmation. Directly adding `SP_DC_COOKIE` to `.env` remains supported.

```sh
spotify_profile_monitor --set-sp-dc
```

`--set-sp-dc` does not accept the cookie as a command-line value. Use `--env-file PATH` to select another `.env` file. Add `--config-file PATH` when its success output should preserve a nondefault configuration path. `--env-file none` is invalid because this command must save the validated cookie. The older `-u` and `--spotify-dc-cookie` options still work, but their values may appear in shell history or process listings.

### Save notification credentials

The SMTP password is entered through a hidden prompt, checked against the mail server and saved as `SMTP_PASSWORD` in `.env`:

```sh
spotify_profile_monitor --set-smtp-password
```

A webhook URL is the private address used to deliver notifications. Treat it like a password because anyone who has it may be able to post through it. Follow the [webhook setup steps](configuration.md#webhook-settings) then save the link:

```sh
spotify_profile_monitor --set-webhook-url
```

The link is entered through a hidden prompt and saved as `WEBHOOK_URL` in `.env`. This command only saves the link. It does not turn on webhook alerts or send a message. See [Webhook Settings](configuration.md#webhook-settings) to choose your alerts then run `spotify_profile_monitor --send-test-webhook` to test them.

### Start monitoring

Start monitoring with a complete Spotify profile URL, a `spotify:user:` URI or a user ID. The first two examples use a positional target. The third uses a saved `TARGET_USER_URI_ID`:

```sh
spotify_profile_monitor <spotify_target>
spotify_profile_monitor "https://open.spotify.com/user/USER_ID"
spotify_profile_monitor --config-file spotify_profile_monitor.conf
```

For a [manual script](installation.md#install-the-manual-script):

```sh
python3 spotify_profile_monitor.py <spotify_target>
```

To see all supported command-line arguments and flags:

```sh
spotify_profile_monitor --help
```

<a id="next-step"></a>
## Next Step

Run [Doctor](troubleshooting.md#doctor-preflight) before an unattended run to confirm dependencies, authentication, connectivity and notification settings.

With authentication saved and a first run working, continue to [Configuration](configuration.md) for targets, Spotify login, SMTP and secrets. See [Usage](usage.md) for command formats, monitoring, listing commands, notifications and output files.

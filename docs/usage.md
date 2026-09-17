# Usage

<a id="command-format-by-installation-method"></a>
## Command Format by Installation Method

Most examples on this page use the PyPI command `spotify_profile_monitor`. If you chose the manual script, replace only that command with the prefix in this table. Keep the targets and options that follow it.

| Installation | Command prefix |
| --- | --- |
| PyPI | `spotify_profile_monitor` |
| Manual script on macOS or Linux | `python3 spotify_profile_monitor.py` |
| Manual script on Windows | `python spotify_profile_monitor.py` |

For example, `spotify_profile_monitor --doctor <spotify_target>` becomes `python3 spotify_profile_monitor.py --doctor <spotify_target>` with the manual script.

Activate the tool's virtual environment before running these commands. For a downloaded script, run them from the directory containing `spotify_profile_monitor.py`.

Throughout this page `<spotify_target>` means any accepted target form: a complete Spotify profile URL, a `spotify:user:` URI or a bare user ID.

See [Installation](installation.md) for setup, optional dependencies and upgrade commands.

<a id="monitoring-mode"></a>
## Monitoring Mode

To monitor a specific user for all profile changes including playlists, pass a complete Spotify profile URL, a `spotify:user:` URI or a user ID:

```sh
spotify_profile_monitor "https://open.spotify.com/user/USER_ID?si=tracking_id"
spotify_profile_monitor "spotify:user:USER_ID"
spotify_profile_monitor USER_ID
```

You can also save any of these forms as `TARGET_USER_URI_ID` in `spotify_profile_monitor.conf`. A positional target takes precedence. With a saved target no positional value is needed:

```sh
spotify_profile_monitor --config-file spotify_profile_monitor.conf
```

If you use the default method to obtain a Spotify access token (`cookie`) and have not set `SP_DC_COOKIE` secret, you can use `-u` flag:

```sh
spotify_profile_monitor <spotify_target> -u "your_sp_dc_cookie_value"
```

OAuth app credentials are optional in `cookie` mode. Existing credentials can still be supplied with `-r` to retain the legacy Web API path when Spotify allows it:

```sh
spotify_profile_monitor <spotify_target> -u "your_sp_dc_cookie_value" -r "your_spotify_app_client_id:your_spotify_app_client_secret"
```

The tool falls back to the web-player playlist backend automatically when those credentials are absent or restricted.


 If you generated a configuration file as described in [Configuration](configuration.md#configuration-file), but saved it under a different name or in a different directory, you can specify its location using the `--config-file` flag:

```sh
spotify_profile_monitor <spotify_target> --config-file /path/spotify_profile_monitor_new.conf
```

`--config-file none` switches automatic config discovery off for one run. The startup summary reports `Discovery disabled` when it is in effect.

By default, only public playlists owned by the user are fetched. To change this behavior:
- set `GET_ALL_PLAYLISTS` to `True`
- or use the `-k` flag

```sh
spotify_profile_monitor <spotify_target> -k
```

It is helpful in the case of playlists created by another user added to another user profile.

Some users don't list all their public playlists on their profile, but if you know a playlist's URI, you can still monitor it.

To do so, add entries to the `ADD_PLAYLISTS_TO_MONITOR` configuration option. Example:

```python
ADD_PLAYLISTS_TO_MONITOR = [
    {'uri': 'spotify:playlist:{playlist_id1}', 'owner_name': '{user_id}', 'owner_uri': 'spotify:user:{user_id}'},
    {'uri': 'spotify:playlist:{playlist_id2}', 'owner_name': '{user_id}', 'owner_uri': 'spotify:user:{user_id}'}
]
```

Replace `{playlist_id1}` and `{playlist_id2}` with the playlist IDs you want to monitor. Replace `{user_id}` with the playlist owner's Spotify user ID.

If you want to completely disable detection of changes in user's public playlists (like added/removed tracks in playlists, playlists name and description changes, number of likes for playlists):
- set `DETECT_CHANGES_IN_PLAYLISTS` to `False`
- or use the `-q` flag

```sh
spotify_profile_monitor <spotify_target> -q
```

If you want to skip some user's playlists from processing, you can use `PLAYLISTS_TO_SKIP_FILE` or `-t` flag (more info [here](#playlist-blacklisting))

```sh
spotify_profile_monitor <spotify_target> -t ignored_playlists
```

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple Spotify users by running multiple copies of the script.

The tool normalizes every accepted target form to a Spotify user ID for output filenames. It saves its log as `spotify_profile_monitor_<user_id/file_suffix>.log`. The log file name can be changed via `SP_LOGFILE` and its suffix via `FILE_SUFFIX` / `-y`. Logging can be disabled with `DISABLE_LOGGING` / `-d`.

The terminal shows a concise startup summary by default. The complete non-secret summary is still written to the log. Use `--verbose` to show that complete summary in the terminal plus occasional events such as metadata backend changes. The complete view includes the effective JSON history directory path alongside the other output destinations, including the current working directory path when `JSON_DIR` is empty. It also names the detected install method and which secrets came from the dotenv file, the environment or the configuration file, by name only. Use `--debug` for sanitized request flow and internal state details.

Set `ASCII_LOG_SEPARATORS` to `"Auto"` (default) to use ASCII separator-only lines on Windows, `"On"` to use them on every operating system or `"Off"` to preserve Unicode separators in logs everywhere. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

The tool also saves the list of followings, followers and playlists to these files:

- `spotify_profile_<user_id/file_suffix>_followings.json`
- `spotify_profile_<user_id/file_suffix>_followers.json`
- `spotify_profile_<user_id/file_suffix>_playlists.json`

Thanks to this we can detect changes after the tool is restarted. By default these files use the current working directory. Set [`JSON_DIR`](configuration.md#json-history-directory) to read and write all three in another directory.

The tool also saves the user profile picture to `spotify_profile_<user_id/file_suffix>_pic*.jpeg` files.

<a id="terminal-output"></a>
## Terminal Output

Use `--help` for examples grouped by task and matched to your installation.

Monitoring mode prints the settings that are actually in effect before the first check.

Optional features appear once you switch them on.

Use `--verbose` or `--debug` for the full startup summary, including output paths, notification settings, secret sources and runtime information.

Use `--truncate N` or `TRUNCATE_CHARS` to limit screen line width. Set it to `999` to detect the terminal width automatically. Truncation does not change log files and is ignored when logging is disabled with `-d`.

The tool clears the terminal when monitoring starts. Set `CLEAR_SCREEN` to `False` to keep whatever is already on the screen.

The screen is never cleared when output is redirected to a file or a pipe, in debug mode, or for a command that prints a result and exits, such as `--doctor`, `--help` and the test senders.

Two settings add detail to what a run prints. `VERBOSE_MODE` adds the decisions the run made and `DEBUG_MODE` adds timestamped technical traces. Both are off by default, both are independent of each other and both have a flag that wins over the file, `--verbose` and `--debug`. `DELIVERY_CONFIRMATIONS` is on by default and controls whether verbose mode confirms each delivered email and webhook alert. See [Verbose and Debug Output](troubleshooting.md#verbose-and-debug-output).

<a id="coloured-terminal-output"></a>
### Coloured Terminal Output

Spotify Profile Monitor colours live terminal output and help by default. Saved log files stay plain text.

Turn colour off for one run with `--no-color` or permanently with `COLORED_OUTPUT = False`. Colour is also disabled for redirected output, `NO_COLOR` or an unsupported terminal. See [Terminal Colours](configuration.md#terminal-colours) for details and Windows support.

Override individual colours with `COLOR_THEME`. It is merged over the built-in theme, so you only name the parts you want to change:

```ini
COLOR_THEME = { "playlist": "bright_magenta bold", "username": "green" }
```

See [Terminal Colours](configuration.md#terminal-colours) for every theme key and the accepted colour and style names.

<a id="listing-mode"></a>
## Listing Mode

There is also another mode of the tool which displays various requested information.

If you want to display details for a specific Spotify playlist URL (i.e. its name, description, number of tracks, likes, overall duration, creation and last update date, list of tracks with information on when they were added), then use the `-l` flag:

```sh
spotify_profile_monitor -l "https://open.spotify.com/playlist/playlist_uri_id"
```

The `-l` flag accepts a playlist URL, a `spotify:playlist:playlist_uri_id` URI or the bare playlist ID. A value in none of these forms is reported as an invalid playlist instead of being sent to Spotify.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/spotify_profile_monitor_playlist.png" alt="spotify_profile_monitor_playlist" width="100%"/>
</p>

If you want to not only display, but also save the list of tracks for a specific Spotify playlist to a CSV file, use the `-l` flag with `-b` indicating the CSV file:

```sh
spotify_profile_monitor -l "https://open.spotify.com/playlist/playlist_uri_id" -b spotify_playlist_tracks.csv
```

If you want to display similar information for **Liked Songs** playlist for the user owning the Spotify access token, use the `-x` flag (can also be used with `-b`):

```sh
spotify_profile_monitor -x
```

If you want to export tracks from `-l` or `-x` for direct import into [spotify_monitor](https://github.com/misiektoja/spotify_monitor), use the `-o` flag to ensure appropriate formatting (optionally with `-b` to specify the text file where the tracks will be exported):

```sh
spotify_profile_monitor -o -x -b spotify_liked_tracks.txt
spotify_profile_monitor -o -l "https://open.spotify.com/playlist/playlist_uri_id" -b spotify_playlist_tracks.txt
```

To display profile details for any accepted Spotify target, including its normalized user ID, followers, followings, recently played artists and playlist statistics, use `-i`:

```sh
spotify_profile_monitor <spotify_target> -i
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/spotify_profile_monitor_user_details.png" alt="spotify_profile_monitor_user_details" width="80%"/>
</p>

By default, only public playlists owned by the user are fetched. You can change this behavior with `-k` flag. It is helpful in the case of playlists created by another user added to another user profile:

```sh
spotify_profile_monitor <spotify_target> -i -k
```

If you want to additionally export each of the user's playlists into a separate .CSV file (named after the playlist and sanitized), use the `--export-all-playlists` flag (requires `pathvalidate` library):

```sh
spotify_profile_monitor <spotify_target> -i --export-all-playlists
```

Each file is written into a dedicated `spotify_profile_<user_id/file_suffix>_playlists_export` directory created in the current working directory, using the sanitized playlist name. Exports can no longer land beside your other files, so your `-b` output and anything else in the working directory are untouched.

File names are sanitized for every platform, not only the one running the export, so the directory stays readable after you copy it to another OS or to a FAT or exFAT volume. Separators (`/`, `\`, `|` and `:`) become a dash and keep the spacing the playlist name had, so `Techno / House` becomes `Techno - House` and `techno/electronica` becomes `techno-electronica`. The remaining characters Windows rejects (`*`, `?`, `"`, `<` and `>`) are dropped, leftover double spaces are collapsed and emoji are kept.

The destination is printed before the profile scan starts, so you can see where files will go without waiting for the scan to finish. Exports are written afterwards, from the tracks the scan already downloaded, so `--export-all-playlists` costs no extra Spotify requests. A progress bar shows how far the export has got. It is drawn only in an interactive terminal, so redirected output and log files are unaffected.

`CSV_FILE_FORMAT_EXPORT` and `CLEAN_OUTPUT` apply to these files the same way they apply to `-l`.

An existing export file is never appended to. If the file is already present from an earlier run, that playlist is skipped with a message. Pass `--force` to replace existing exports:

```sh
spotify_profile_monitor <spotify_target> -i --export-all-playlists --force
```

When two playlists sanitize to the same filename, the second one gets the playlist ID appended so both are exported in full.

To skip public playlist processing while displaying details for a Spotify target, use `-q`:

```sh
spotify_profile_monitor <spotify_target> -i -q
```

If you only want to display the list of followings and followers for the user (`-f` flag):

```sh
spotify_profile_monitor <spotify_target> -f
```

If you want to display a list of recently played artists (this feature only works if the user has it enabled in their settings), use the `-a` flag:

```sh
spotify_profile_monitor <spotify_target> -a
```

To search the Spotify catalog for users with a specific name and obtain their Spotify user ID plus profile URL, use `-s`:

```sh
spotify_profile_monitor -s "user name"
```

<a id="email-notifications"></a>
## Email Notifications

To enable email notifications for all user profile changes (including playlists):
- set `PROFILE_NOTIFICATION` to `True`
- or use the `-p` flag

```sh
spotify_profile_monitor <spotify_target> -p
```

To disable sending an email about new followers/followings (these are sent by default when the `-p` flag is enabled):
- set `FOLLOWERS_FOLLOWINGS_NOTIFICATION` to `False`
- or use the `-g` flag

```sh
spotify_profile_monitor <spotify_target> -p -g
```

To disable sending an email on errors (enabled by default):
- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
spotify_profile_monitor <spotify_target> -e
```

Email and webhook error alerts are sent after **5 minutes** of a continuing failure. Problems that need your action, such as an expired `sp_dc` cookie, alert immediately. Each channel gets one alert until a full check succeeds, including the follower poll. Failed deliveries are retried after 5 minutes, with increasing waits up to an hour.

Make sure you defined your SMTP settings earlier (see [SMTP settings](configuration.md#smtp-settings)).

Playlist change emails include inline artwork when Spotify provides it. Track-change alerts prefer playlist artwork when both playlist and album images are available, then fall back to album artwork when the playlist has no image. Artwork is accepted only from Spotify HTTPS CDN hosts and is resized to fit within 320 x 320 pixels. Download or image preparation failures do not block the email. Dedicated profile-picture events continue to attach the saved profile picture.

Playlist and album artwork are disabled by default and need the optional artwork extra (`pip install "spotify_profile_monitor[notification-images]"`). To include them in email notifications:

```ini
EMAIL_IMAGES = True
```

This setting does not control dedicated profile-picture events. Profile-picture detection, downloads and email attachments remain enabled by default through `DETECT_CHANGED_PROFILE_PIC = True`. Set that option to `False` or use `-j` to disable the profile-picture feature.

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/spotify_profile_monitor_email_notifications.png" alt="spotify_profile_monitor_email_notifications" width="90%"/>
</p>

<a id="webhook-notifications"></a>
## Webhook Notifications

Webhook event settings mirror the email controls while remaining independent from SMTP:

| Event | Config setting | CLI override |
| --- | --- | --- |
| Profile or playlist change | `WEBHOOK_PROFILE_NOTIFICATION` | `--webhook-profile` |
| Followers or followings change | `WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION` | Disable with `--no-webhook-followers-followings-notify` |
| Monitoring error | `WEBHOOK_ERROR_NOTIFICATION` | Enable with `--webhook-errors` or disable with `--no-webhook-error-notify` |

Enable the master switch and the profile event setting in `spotify_profile_monitor.conf`:

```ini
WEBHOOK_ENABLED = True
WEBHOOK_PROVIDER = "discord"
WEBHOOK_PROFILE_NOTIFICATION = True
WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION = True
WEBHOOK_ERROR_NOTIFICATION = True
```

A `WEBHOOK_URL` left unset, or left at its `your_webhook_url` placeholder, switches webhook alerts off at startup instead of failing at the first alert. `--verbose` reports why.

You can also enable profile webhooks for one run:

```sh
spotify_profile_monitor <spotify_target> --webhook-profile
```

Use `--webhook` or `--no-webhook` to turn all configured webhook alerts on or off for one run. Standard Discord and public `ntfy.sh` URLs automatically correct a stale configured provider. Use `--webhook-provider {discord,ntfy}` as an explicit override for self-hosted ntfy or compatible endpoints.

The recommended way to save the private destination is `--set-webhook-url`. Use `--webhook-url URL` only when shell history or process visibility is acceptable. See [Webhook Settings](configuration.md#webhook-settings) for Discord setup, ntfy artwork and advanced payload customization.

<a id="csv-export"></a>
## CSV Export

If you want to save all profile changes (including playlists) to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
spotify_profile_monitor <spotify_target> -b spotify_profile_changes_spotify_user.csv
```

The file will be automatically created if it does not exist.

Spotify-supplied text (playlist names, track names, artist names, collaborator names and descriptions) that starts with `=`, `+`, `-`, `@`, a tab or a carriage return is written with a leading apostrophe, so opening the export in a spreadsheet cannot evaluate it as a formula. The same applies to the per-playlist files produced by `--export-all-playlists`. Timestamps and numeric values are unaffected.

<a id="unavailable-followers-and-followings"></a>
## Unavailable Followers and Followings

Missing follower or following data is shown as `n/a`. It does not replace saved history or trigger removal alerts, including after a restart. The first available snapshot establishes a baseline if no history exists.

An explicit zero count or a valid empty list still uses `FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER` to confirm a disappearance during monitoring. Missing responses interrupt that confirmation streak.

<a id="detection-of-changed-profile-pictures"></a>
## Detection of Changed Profile Pictures

The tool can detect when a monitored user changes their profile picture. Notifications appear in the console and (if the `-p` flag is enabled) via email.

This feature is enabled by default. To disable it, either:

- set the `DETECT_CHANGED_PROFILE_PIC` to `False`
- or use the `-j` flag

<a id="how-it-works"></a>
### How It Works

Since Spotify periodically changes the profile picture URL even when the image is the same, the tool performs a binary comparison of JPEG files to detect actual changes.

On the first run, it saves the current profile picture to `spotify_profile_<user_id/file_suffix>_pic.jpeg`

On each subsequent check a new image is fetched and it is compared byte-for-byte with the saved image.

Profile pictures are accepted only from the HTTPS CDN hosts Spotify serves them on (`scdn.co` and `spotifycdn.com`, plus `fbcdn.net` and `fbsbx.com` for accounts linked to Facebook), redirects are not followed and the download stops at 5 MB. The saved file is replaced only after a complete picture arrives, so a refused or interrupted download leaves the previous picture in place and reports `* Error saving profile picture !`.

If a change is detected, the old picture is moved to `spotify_profile_<user_id/file_suffix>_pic_old.jpeg` and the new one is saved to:
- `spotify_profile_<user_id/file_suffix>_pic.jpeg` (current)
- `spotify_profile_<user_id/file_suffix>_pic_YYmmdd_HHMM.jpeg` (for history)

<a id="displaying-images-in-your-terminal"></a>
## Displaying Images in Your Terminal

If you have `imgcat` installed, you can enable inline display of profile pictures and playlist artwork directly in your terminal.

To do this, set the path to your `imgcat` binary in the `IMGCAT_PATH` configuration option.

If you specify only the binary name, it will be auto-searched in your PATH.

Set it to empty to disable this feature.

<a id="playlist-blacklisting"></a>
## Playlist Blacklisting

By default, all Spotify-owned playlists are skipped from processing, i.e. the tool won't fetch or report changed tracks and the number of likes for them. This is because they are typically dynamically generated with a high volume of changes in terms of likes and sometimes tracks as well. You can change this behavior by setting `IGNORE_SPOTIFY_PLAYLISTS` to `False`.

On top of that, you can also use the `PLAYLISTS_TO_SKIP_FILE` / `-t` flag which allows you to indicate a file with additional playlists to be blacklisted.

The file may include lines referencing playlist URIs and URLs, as well as the playlist owner's name, URI and URL. Below is an example of an `ignored_playlists` file with acceptable entries:

```sh
PLAYLIST_ID
spotify:playlist:PLAYLIST_ID
https://open.spotify.com/playlist/PLAYLIST_ID
https://open.spotify.com/playlist/PLAYLIST_ID?si=1
Some User Name
USER_ID
spotify:user:USER_ID
https://open.spotify.com/user/USER_ID?si=1
```

You can comment out specific lines with # if needed.

Entries are matched case sensitively, because Spotify identifiers are case sensitive and two IDs differing only in case are different playlists. Copy each ID, name or URL exactly as Spotify shows it.

If certain playlists are blacklisted, there will be an appropriate message. For example:

```
- 'Afternoon Acoustic' [ IGNORED ]
[ https://open.spotify.com/playlist/37i9dQZF1DX4E3UdUs7fUx?si=1 ]
[ songs: 100, likes: 2164491, collaborators: 0 ]
[ owner: Spotify ]
[ date: Fri 23 Aug 2024, 17:05:15 - 7 months, 10 hours, 27 minutes ago ]
[ update: Fri 23 Aug 2024, 17:05:15 - 7 months, 10 hours, 27 minutes ago ]
'Unwind and let the afternoon unfold.'
```

<a id="restricted-playlists-spotify-api-403404"></a>
## Restricted Playlists (Spotify API 403/404)

Some playlists may appear on profile pages but return `403` or `404` from the public Web API. Version 3.5 automatically retries them through the Spotify web-player backend.

The tool marks a playlist as `[ RESTRICTED ]` and uses profile-view metadata only when both the Web API and web-player backend cannot retrieve it.

For restricted playlists, the tool can monitor:
- added/removed from profile
- playlist name changes
- likes/followers count changes (when available in profile-view)

For restricted playlists, the tool cannot monitor:
- track-level changes
- collaborators
- description changes
- creation/last update timestamps derived from track history

<a id="playlist-change-confirmation"></a>
## Playlist Change Confirmation

`PLAYLISTS_CHANGE_COUNTER` requires repeated matching nonempty playlist collections before reporting a change. Set it to `0` to accept a nonempty change immediately. `PLAYLISTS_DISAPPEARED_COUNTER` separately controls how many consecutive empty responses confirm that all playlists disappeared. A nonempty response resets the disappearance count and an empty response clears a pending nonempty change. Playlist metadata failures retain the last successful details and can trigger error alerts without bypassing either threshold.

Those two thresholds need several checks to decide, which only works while monitoring is already running. A one-shot `-i` read and the first check after startup get a single response, so they confirm an empty playlist list differently: the profile is read again up to `PLAYLISTS_EMPTY_RETRIES` times (default `2`), `PLAYLISTS_EMPTY_RETRY_SLEEP` seconds apart (default `3`). A Spotify glitch usually clears on the retry while a real removal does not. Set `PLAYLISTS_EMPTY_RETRIES` to `0` to disable the extra reads.

If startup still sees no playlists while the saved history file holds some, it keeps the saved history and says so, rather than recording an emptied profile. The count then follows the usual `PLAYLISTS_DISAPPEARED_COUNTER` confirmation once monitoring is running. For the same reason, a first baseline is never written from a response whose playlist field was missing altogether.

<a id="check-intervals"></a>
## Check Intervals

If you want to customize the polling interval, use the `-c` flag (or the `SPOTIFY_CHECK_INTERVAL` configuration option):

```sh
spotify_profile_monitor <spotify_target> -c 900
```

An interval below 30 seconds invites the Spotify rate limiter, which stops the tool seeing anything. `--doctor` warns when the configured interval is that short.

<a id="liveness-reminder"></a>
### Liveness Reminder

While nothing changes, the tool prints one reminder that it is still running:

```
* Monitoring healthy for <spotify_target>. No profile or playlist change since the last check
Liveness check, timestamp:	Mon 08 Sep 2026, 09:15:05
```

Set `LIVENESS_CHECK_INTERVAL` to change it (default: 86400, i.e. 24 hours), or to 0 to switch it off.

Anything the tool prints about the target restarts the countdown, so a busy run stays quiet.

<a id="signal-controls-macoslinuxunix"></a>
## Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications for user's profile changes (-p) |
| TRAP | Increase the profile check timer (by 5 minutes) |
| ABRT | Decrease the profile check timer (by 5 minutes) |
| HUP | Reload secrets from .env file and token source credentials from Protobuf files |

`SIGHUP` keeps command-line credentials and nonempty environment values exported before startup. Change those values and restart to replace them.

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "spotify_profile_monitor <spotify_target>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
## Coloring Log Output with GRC

Spotify Profile Monitor colours live terminal output through `COLORED_OUTPUT` and `COLOR_THEME`. To colour saved log files when you view them later, you can use [GRC](https://github.com/garabik/grc).

The bundled recipe follows the same colours as the live output. It also covers the other monitors in the family, so one copy in `~/.grc/` colours every tool's logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using `grc` tool.

Example:

```sh
grc tail -F -n 100 spotify_profile_monitor_<user_id/file_suffix>.log
```

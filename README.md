# spotify_profile_monitor

spotify_profile_monitor is an OSINT tool for real-time monitoring of Spotify users' activities and profile changes including playlists.

NOTE: If you want to track Spotify friends' music activity, check out another tool I developed: [spotify_monitor](https://github.com/misiektoja/spotify_monitor).

<a id="features"></a>
## Features

- Real-time tracking of Spotify user activities and profile changes:
   - addition/removal of followings and followers
   - addition/removal of playlists
   - addition/removal of tracks in playlists (including collaborator info for newly added tracks)
   - playlists name and description changes
   - number of likes for playlists
   - number of collaborators for playlists
   - profile picture changes
   - username changes
- Email notifications for various events (as listed above)
- Attaching changed profile pictures directly to email notifications
- Displaying the profile picture right in your terminal (if you have `imgcat` installed)
- Additional functionalities on top of the monitoring mode allowing to display detailed info about the user, list of followers & followings, recently played artists and possibility to search for users in Spotify catalog with specific names
- Ability to display and export the list of tracks for a specific playlist (including Liked Songs for the user who owns the Spotify access token)
- Saving all profile changes (including playlists) with timestamps to the CSV file
- Clickable Spotify, Apple Music, YouTube Music and Genius Lyrics search URLs printed in the console & included in email notifications
- Possibility to control the running copy of the script via signals

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/spotify_profile_monitor.png" alt="spotify_profile_monitor_screenshot" width="100%"/>
</p>

<a id="table-of-contents"></a>
## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
   * [Install from PyPI](#install-from-pypi)
   * [Manual Installation](#manual-installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
   * [Configuration File](#configuration-file)
   * [Spotify access token source](#spotify-access-token-source)
      * [Spotify sp_dc Cookie](#spotify-sp_dc-cookie)
      * [Spotify Desktop Client](#spotify-desktop-client)
   * [How to Get a Friend's User URI ID](#how-to-get-a-friends-user-uri-id)
   * [Spotify sha256 (optional)](#spotify-sha256-optional)
   * [Time Zone](#time-zone)
   * [SMTP Settings](#smtp-settings)
   * [Storing Secrets](#storing-secrets)
5. [Usage](#usage)
   * [Monitoring Mode](#monitoring-mode)
   * [Listing Mode](#listing-mode)
   * [Email Notifications](#email-notifications)
   * [CSV Export](#csv-export)
   * [Detection of Changed Profile Pictures](#detection-of-changed-profile-pictures)
   * [Displaying Images in Your Terminal](#displaying-images-in-your-terminal)
   * [Playlist Blacklisting](#playlist-blacklisting)
   * [Check Intervals](#check-intervals)
   * [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix)
   * [Coloring Log Output with GRC](#coloring-log-output-with-grc)
6. [Change Log](#change-log)
7. [License](#license)

<a id="requirements"></a>
## Requirements

* Python 3.6 or higher
* Libraries: `requests`, `python-dateutil`, `urllib3`, `pyotp`, `pytz`, `tzlocal`, `python-dotenv`

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm), Ubuntu 24, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="installation"></a>
## Installation

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install spotify_profile_monitor
```

<a id="manual-installation"></a>
### Manual Installation

Download the *[spotify_profile_monitor.py](https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/spotify_profile_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install requests python-dateutil urllib3 pyotp pytz tzlocal python-dotenv
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

<a id="quick-start"></a>
## Quick Start

- Grab your [Spotify sp_dc cookie](#spotify-sp_dc-cookie) and track the `spotify_user_uri_id` profile changes (including playlists):


```sh
spotify_profile_monitor <spotify_user_uri_id> -u "your_sp_dc_cookie_value"
```

Or if you installed [manually](#manual-installation):

```sh
python3 spotify_profile_monitor.py <spotify_user_uri_id> -u "your_sp_dc_cookie_value"
```

To get the list of all supported command-line arguments / flags:

```sh
spotify_profile_monitor --help
```

<a id="configuration"></a>
## Configuration

<a id="configuration-file"></a>
### Configuration File

Most settings can be configured via command-line arguments.

If you want to have it stored persistently, generate a default config template and save it to a file named `spotify_profile_monitor.conf`:

```sh
spotify_profile_monitor --generate-config > spotify_profile_monitor.conf

```

Edit the `spotify_profile_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

<a id="spotify-access-token-source"></a>
#### Spotify access token source

The tool supports two methods for obtaining a Spotify access token.

It can be configured via the `TOKEN_SOURCE` configuration option or the `--token-source` flag. 

The **recommended method** is `cookie` which uses the sp_dc cookie to retrieve a token from the Spotify web endpoint. This method supports all features except fetching the list of liked tracks for the account that owns the access token (Spotify has recently restricted the token's scope).

The **alternative method** is `client` which uses captured credentials from the Spotify desktop client and a Protobuf-based login flow. This approach is intended for advanced users who want an indefinitely valid token with the widest scope.

If no method is specified, the tool defaults to the `cookie` method.

<a id="spotify-sp_dc-cookie"></a>
#### Spotify sp_dc Cookie

It is default method used to obtain a Spotify access token.

Log in to [https://open.spotify.com/](https://open.spotify.com/) in your web browser.

Locate and copy the value of the `sp_dc` cookie.

Use your web browser's dev console or **Cookie-Editor** by cgagnier to extract it easily: [https://cookie-editor.com/](https://cookie-editor.com/)

Provide the `SP_DC_COOKIE` secret using one of the following methods:
 - Pass it at runtime with `-u` / `--spotify-dc-cookie`
 - Set it as an [environment variable](#storing-secrets) (e.g. `export SP_DC_COOKIE=...`)
 - Add it to [.env file](#storing-secrets) (`SP_DC_COOKIE=...`) for persistent use

Fallback:
 - Hard-code it in the code or config file

You will be informed by the tool once the `sp_dc` cookie expires (proper message on the console and in email).

If you store the `SP_DC_COOKIE` in a dotenv file you can update its value and send a `SIGHUP` signal to the process to reload the file with the new `sp_dc` cookie without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix).

**Important**: It is strongly recommended to use a separate Spotify account with this tool. It does not rely on the official Spotify Web API for many features (e.g. retrieving a list of followers/followings, followings count or recently played artists), as these are not supported by the public API.

<a id="spotify-desktop-client"></a>
#### Spotify Desktop Client

To use credentials captured from the Spotify desktop client to obtain an access token, set the `TOKEN_SOURCE` configuration option to `client` or use the `--token-source client` flag.

Run an intercepting proxy of your choice (like [Proxyman](https://proxyman.com)).

Launch the Spotify desktop client and look for POST requests to `https://login{n}.spotify.com/v3/login`

Note: The `login` part is suffixed with one or more digits (e.g. `login5`).

If you don't see this request, log out from the client and log back in.

Export the login request body (a binary Protobuf payload) to a file.

In Proxyman: ***right click the request → Export → Request Body → Save File***.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/proxyman_export_protobuf.png" alt="proxyman_export_protobuf" width="80%"/>
</p>

Then run the tool with `-w <path-to-login-request-body-file>`:

```sh
spotify_profile_monitor --token-source client -w <path-to-login-request-body-file> <spotify_user_uri_id>
```

If successful, the tool will automatically extract the necessary fields and begin monitoring.

You can also persist the Protobuf request file path using the `LOGIN_REQUEST_BODY_FILE` configuration option.

The tool will automatically refresh both the access token and client token using the intercepted refresh token.

Advanced options are available for further customization - refer to the configuration file comments. However, default settings should work for most cases.

You will be informed by the tool once the refresh token expires (proper message on the console and in email).

**Important**: It is strongly recommended to use a separate Spotify account with this tool. It does not rely on the official Spotify Web API for many features (e.g. retrieving a list of followers/followings, followings count or recently played artists), as these are not supported by the public API.

<a id="how-to-get-a-friends-user-uri-id"></a>
### How to Get a Friend's User URI ID

The easiest way is via the Spotify desktop or mobile client:
- go to your friend's profile
- click the **three dots** (•••) or press the **Share** button
- copy the link to the profile

You'll get a URL like: [https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id](https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id)

Extract the part between `/user/` and `?si=` - in this case: `spotify_user_uri_id`

Use that as the user URI ID (`spotify_user_uri_id`) in the tool.

Alternatively you can use the built-in functionality to search for usernames (`-s` flag) to get the user URI ID:

```sh
spotify_profile_monitor -s "user name"
```

It will list all users with such names with their user URI ID. 

Before using this feature make sure you followed the instructions [here](#spotify-sha256-optional).

<a id="spotify-sha256-optional"></a>
### Spotify sha256 (optional)

This step is optional and only required if you want to use the feature that searches Spotify's catalog for users with a specific name to obtain their Spotify user URI ID (`-s` flag).

To do this, you need to intercept your Spotify client's network traffic and obtain the sha256 value.

To simulate the required request, search for the user in the Spotify client. Then, in the intercepting proxy, look for requests with the `searchUsers` or `searchDesktop` operation name.

Display the details of one of these requests and copy the **sha256Hash** parameter value, then place it in the `SP_SHA256` secret.

Example request:
`https://api-partner.spotify.com/pathfinder/v1/query?operationName=searchUsers&variables={"searchTerm":"spotify_user_uri_id","offset":0,"limit":5,"numberOfTopResults":5,"includeAudiobooks":false}&extensions={"persistedQuery":{"version":1,"sha256Hash":"XXXXXXXXXX"}}`

You are interested in the string marked as `XXXXXXXXXX` here. 

Provide the `SP_SHA256` secret using one of the following methods:
   - Set it as an [environment variable](#storing-secrets) (e.g. `export SP_SHA256=...`)
   - Add it to [.env file](#storing-secrets) (`SP_SHA256=...`) for persistent use
 
 Fallback:
   - Hard-code it in the code or config file

<a id="time-zone"></a>
### Time Zone

By default, time zone is auto-detected using `tzlocal`. You can set it manually in `spotify_profile_monitor.conf`:

```ini
LOCAL_TIMEZONE='Europe/Warsaw'
```

You can get the list of all time zones supported by pytz like this:

```sh
python3 -c "import pytz; print('\n'.join(pytz.all_timezones))"
```

<a id="smtp-settings"></a>
### SMTP Settings

If you want to use email notifications functionality, configure SMTP settings in the `spotify_profile_monitor.conf` file. 

Verify your SMTP settings by using `--send-test-email` flag (the tool will try to send a test email notification):

```sh
spotify_profile_monitor --send-test-email
```

<a id="storing-secrets"></a>
### Storing Secrets

It is recommended to store secrets like `SP_DC_COOKIE`, `SP_SHA256` or `SMTP_PASSWORD` as either an environment variable or in a dotenv file.

Set environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

```sh
export SP_DC_COOKIE="your_sp_dc_cookie_value"
export SP_SHA256="your_spotify_client_sha256"
export SMTP_PASSWORD="your_smtp_password"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

Alternatively store them persistently in a dotenv file (recommended):

```ini
SP_DC_COOKIE="your_sp_dc_cookie_value"
SP_SHA256="your_spotify_client_sha256"
SMTP_PASSWORD="your_smtp_password"
```

By default the tool will auto-search for dotenv file named `.env` in current directory and then upward from it. 

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
spotify_profile_monitor <spotify_user_uri_id> --env-file /path/.env-spotify_profile_monitor
```

 You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
spotify_profile_monitor <spotify_user_uri_id> --env-file none
```

As a fallback, you can also store secrets in the configuration file or source code.

<a id="usage"></a>
## Usage

<a id="monitoring-mode"></a>
### Monitoring Mode

To monitor specific user for all profile changes (including playlists), just type [Spotify user URI ID](#how-to-get-a-friends-user-uri-id) as a command-line argument (`spotify_user_uri_id` in the example below):

```sh
spotify_profile_monitor <spotify_user_uri_id>
```

If you use the default method to obtain a Spotify access token (`cookie`) and have not set `SP_DC_COOKIE` secret, you can use `-u` flag:

```sh
spotify_profile_monitor <spotify_user_uri_id> -u "your_sp_dc_cookie_value"
```

By default, the tool looks for a configuration file named `spotify_profile_monitor.conf` in:
 - current directory 
 - home directory (`~`)
 - script directory 

 If you generated a configuration file as described in [Configuration](#configuration), but saved it under a different name or in a different directory, you can specify its location using the `--config-file` flag:


```sh
spotify_profile_monitor <spotify_user_uri_id> --config-file /path/spotify_profile_monitor_new.conf
```

By default, only public playlists owned by the user are fetched. To change this behavior:
- set `GET_ALL_PLAYLISTS` to `True`
- or use the `-k` flag

```sh
spotify_profile_monitor <spotify_user_uri_id> -k
```

It is helpful in the case of playlists created by another user added to another user profile.

If you want to completely disable detection of changes in user's public playlists (like added/removed tracks in playlists, playlists name and description changes, number of likes for playlists):
- set `DETECT_CHANGES_IN_PLAYLISTS` to `False`
- or use the `-q` flag

```sh
spotify_profile_monitor <spotify_user_uri_id> -q
```

If you want to skip some user's playlists from processing, you can use `PLAYLISTS_TO_SKIP_FILE` or `-t` flag (more info [here](#playlist-blacklisting))

```sh
spotify_profile_monitor <spotify_user_uri_id> -t ignored_playlists
```

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple Spotify users by running multiple copies of the script.

The tool automatically saves its output to `spotify_profile_monitor_<user_uri_id/file_suffix>.log` file. The log file name can be changed via `SP_LOGFILE` configuration option and its suffix via `FILE_SUFFIX` / `-y` flag. Logging can be disabled completely via `DISABLE_LOGGING` / `-d` flag.

The tool also saves the list of followings, followers and playlists to these files:
- `spotify_profile_<user_uri_id/file_suffix>_followings.json` 
- `spotify_profile_<user_uri_id/file_suffix>_followers.json`
- `spotify_profile_<user_uri_id/file_suffix>_playlists.json`

Thanks to this we can detect changes after the tool is restarted.

The tool also saves the user profile picture to `spotify_profile_{user_uri_id/file_suffix}_pic*.jpeg` files.

<a id="listing-mode"></a>
### Listing Mode

There is also another mode of the tool which displays various requested information.

If you want to display details for a specific Spotify playlist URL (i.e. its name, description, number of tracks, likes, overall duration, creation and last update date, list of tracks with information on when they were added), then use the `-l` flag:

```sh
spotify_profile_monitor -l "https://open.spotify.com/playlist/playlist_uri_id"
```

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

If you want to display details for a specific Spotify user profile URL (i.e. user URI ID, list and number of followers and followings, recently played artists, list and number of user's playlists with basic statistics like when created, last updated, description, number of tracks and likes) then use the `-i` flag:

```sh
spotify_profile_monitor <spotify_user_uri_id> -i
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/spotify_profile_monitor_user_details.png" alt="spotify_profile_monitor_user_details" width="80%"/>
</p>

By default, only public playlists owned by the user are fetched. You can change this behavior with `-k` flag. It is helpful in the case of playlists created by another user added to another user profile:

```sh
spotify_profile_monitor <spotify_user_uri_id> -i -k
```

If you want to completely disable the processing of a user's public playlists while displaying details for a specific Spotify user profile URL (to speed up the process), you can use the `-q` flag:

```sh
spotify_profile_monitor <spotify_user_uri_id> -i -q
```

If you only want to display the list of followings and followers for the user (`-f` flag):

```sh
spotify_profile_monitor <spotify_user_uri_id> -f
```

If you want to display a list of recently played artists (this feature only works if the user has it enabled in their settings), use the `-a` flag:

```sh
spotify_profile_monitor <spotify_user_uri_id> -a
```

To get basic information about the Spotify access token owner (`-v` flag):

```sh
spotify_profile_monitor -v
```

If you want to search the Spotify catalog for users with a specific name to obtain their Spotify user URI ID (`-s` flag):

```sh
spotify_profile_monitor -s "user name"
```

<a id="email-notifications"></a>
### Email Notifications

To enable email notifications for all user profile changes (including playlists):
- set `PROFILE_NOTIFICATION` to `True`
- or use the `-p` flag

```sh
spotify_profile_monitor <spotify_user_uri_id> -p
```

To disable sending an email about new followers/followings (these are sent by default when the `-p` flag is enabled):
- set `FOLLOWERS_FOLLOWINGS_NOTIFICATION` to `False`
- or use the `-g` flag

```sh
spotify_profile_monitor <spotify_user_uri_id> -p -g
```

To disable sending an email on errors (enabled by default):
- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
spotify_profile_monitor <spotify_user_uri_id> -e
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/spotify_profile_monitor_email_notifications.png" alt="spotify_profile_monitor_email_notifications" width="80%"/>
</p>

<a id="csv-export"></a>
### CSV Export

If you want to save all profile changes (including playlists) to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
spotify_profile_monitor <spotify_user_uri_id> -b spotify_profile_changes_spotify_user.csv
```

The file will be automatically created if it does not exist.

<a id="detection-of-changed-profile-pictures"></a>
### Detection of Changed Profile Pictures

The tool can detect when a monitored user changes their profile picture. Notifications appear in the console and (if the `-p` flag is enabled) via email.

This feature is enabled by default. To disable it, either:

- set the `DETECT_CHANGED_PROFILE_PIC` to `False`
- or use the `-j` flag

<a id="how-it-works"></a>
#### How It Works

Since Spotify periodically changes the profile picture URL even when the image is the same, the tool performs a binary comparison of JPEG files to detect actual changes.

On the first run, it saves the current profile picture to `spotify_profile_<user_uri_id/file_suffix>_pic.jpeg`

On each subsequent check a new image is fetched and it is compared byte-for-byte with the saved image.

If a change is detected, the old picture is moved to `spotify_profile_<user_uri_id/file_suffix>_pic_old.jpeg` and the new one is saved to:
- `spotify_profile_<user_uri_id/file_suffix>_pic.jpeg` (current)
- `spotify_profile_<user_uri_id/file_suffix>_pic_YYmmdd_HHMM.jpeg` (for history)

<a id="displaying-images-in-your-terminal"></a>
### Displaying Images in Your Terminal

If you have `imgcat` installed, you can enable inline display of profile pictures and playlist artwork directly in your terminal.

To do this, set the path to your `imgcat` binary in the `IMGCAT_PATH` configuration option. 

If you specify only the binary name, it will be auto-searched in your PATH.

Set it to empty to disable this feature.

<a id="playlist-blacklisting"></a>
### Playlist Blacklisting

By default, all Spotify-owned playlists are skipped from processing, i.e. the tool won't fetch or report changed tracks and the number of likes for them. This is because they are typically dynamically generated with a high volume of changes in terms of likes and sometimes tracks as well. You can change this behavior by setting `IGNORE_SPOTIFY_PLAYLISTS` to `False`.

On top of that, you can also use the `PLAYLISTS_TO_SKIP_FILE` / `-t` flag which allows you to indicate a file with additional playlists to be blacklisted.

The file may include lines referencing playlist URIs and URLs, as well as the playlist owner's name, URI and URL. Below is an example of an `ignored_playlists` file with acceptable entries:

```sh
playlist_uri_id
spotify:playlist:playlist_uri_id
https://open.spotify.com/playlist/playlist_uri_id
https://open.spotify.com/playlist/playlist_uri_id?si=1
Some User Name
user_uri_id
spotify:user:user_uri_id
https://open.spotify.com/user/user_uri_id?si=1
```

You can comment out specific lines with # if needed.

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

<a id="check-intervals"></a>
### Check Intervals

If you want to customize polling interval, use `-c` flag (or `SPOTIFY_CHECK_INTERVAL` configuration option):

```sh
spotify_profile_monitor <spotify_user_uri_id> -c 900
```

<a id="signal-controls-macoslinuxunix"></a>
### Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications for user's profile changes (-p) |
| TRAP | Increase the profile check timer (by 5 minutes) |
| ABRT | Decrease the profile check timer (by 5 minutes) |
| HUP | Reload secrets from .env file and token source credentials from Protobuf files |

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "spotify_profile_monitor <spotify_user_uri_id>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
### Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to color logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using `grc` tool.

Example:

```sh
grc tail -F -n 100 spotify_profile_monitor_<user_uri_id/file_suffix>.log
```

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/spotify_profile_monitor/blob/main/RELEASE_NOTES.md) for details.

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/spotify_profile_monitor/blob/main/LICENSE).

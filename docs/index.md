# spotify_profile_monitor

[![GitHub Release](https://img.shields.io/github/v/release/misiektoja/spotify_profile_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/spotify_profile_monitor/releases)
[![PyPI Version](https://img.shields.io/pypi/v/spotify_profile_monitor?style=flat-square&color=teal)](https://pypi.org/project/spotify-profile-monitor/)
[![GitHub Stars](https://img.shields.io/github/stars/misiektoja/spotify_profile_monitor?style=flat-square&color=magenta)](https://github.com/misiektoja/spotify_profile_monitor)
[![Python Versions](https://img.shields.io/badge/python-3.9+-blueviolet?style=flat-square)](https://pypi.org/project/spotify-profile-monitor/)
[![License](https://img.shields.io/github/license/misiektoja/spotify_profile_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/spotify_profile_monitor/blob/main/LICENSE)
[![OpenSSF Scorecard](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Fspotify_profile_monitor%3Fbadge_cache%3D20260826&query=%24.score&label=openssf%20scorecard&style=flat-square)](https://scorecard.dev/viewer/?uri=github.com/misiektoja/spotify_profile_monitor)
[![Last Commit](https://img.shields.io/github/last-commit/misiektoja/spotify_profile_monitor?style=flat-square&color=green)](https://github.com/misiektoja/spotify_profile_monitor/commits/main)
[![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square)](https://github.com/misiektoja/spotify_profile_monitor)

Powerful Spotify tool for real-time tracking of profile changes, playlist updates, follower growth, collaborators and more - delivered straight to your terminal, inbox or webhook.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/spotify_profile_monitor.png" alt="spotify_profile_monitor_screenshot" width="90%"/>
</p>

<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install spotify_profile_monitor
```

Run the setup wizard:

```sh
spotify_profile_monitor --setup
```

The wizard asks for the target, authentication, polling interval and optional email or webhook alerts, then offers to run Doctor and start monitoring.

For the manual single-file method, optional extras and upgrade commands, see [Installation](installation.md).

<a id="features"></a>
## Features

### 📜 Playlists
- Detect added or removed playlists and tracks.
- Track playlist names, descriptions, likes and collaborators.
- See who added each track to a collaborative playlist.

### 👤 Profile Changes
- Track username and profile-picture changes.
- See when followers or followed accounts are added or removed.
- View profile details and recently played artists.

### 🔔 Notifications and History
- Receive alerts in the terminal, by email, through Discord or through ntfy.
- Keep a timestamped CSV history of profile and playlist changes.
- Include profile pictures and optional playlist or album artwork in notifications.

### 🔎 Extra Tools
- List or export tracks from playlists and Liked Songs.
- Search for Spotify users by name.
- Open music and lyrics searches across Spotify, YouTube Music, Apple Music, Tidal and other services.
- Use the automatic web-player playlist backend without creating a Spotify developer app.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/spotify_profile_monitor_playlist.png" alt="spotify_profile_monitor_playlist" width="90%"/>
</p>

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install-run) above for first-time setup. The table uses PyPI commands. For the manual script equivalents, see [Command Format by Installation Method](usage.md#command-format).

| I want to... | Run this |
| --- | --- |
| Start monitoring with existing authentication | `spotify_profile_monitor TARGET`, where `TARGET` is a complete profile URL, `spotify:user:` URI or user ID |
| Check dependencies, authentication, connectivity and one target | `spotify_profile_monitor --doctor TARGET` |
| Import a Spotify login from a browser | Open [Spotify Web Player](https://open.spotify.com/) in the browser, sign in then run `spotify_profile_monitor --import-browser-cookie --browser firefox` |
| Enter or replace securely a manually extracted `SP_DC_COOKIE` | Run `spotify_profile_monitor --set-sp-dc` and enter `sp_dc` at the hidden prompt |
| Show profile details, followers, followings and playlist statistics | `spotify_profile_monitor TARGET -i` |
| Display or export the tracks of one playlist | `spotify_profile_monitor -l PLAYLIST_URL -b tracks.csv` |
| Find a Spotify user ID by name | `spotify_profile_monitor -s "user name"` |
| Configure and test webhook alerts | Use the setup wizard or follow [Webhook Settings](configuration.md#webhook-settings) |

For authentication, token sources, targets and notification setup, see the [full Setup & First Run guide](setup-and-first-run.md).

✨ If you want to track Spotify friends' music activity, check out another tool I developed: [spotify_monitor](https://github.com/misiektoja/spotify_monitor).

🛠️ For Spotify Web Player token and secret-key utilities, see [Debugging Tools](debugging.md).

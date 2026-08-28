# spotify_profile_monitor

[![GitHub Release](https://img.shields.io/github/v/release/misiektoja/spotify_profile_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/spotify_profile_monitor/releases)
[![PyPI Version](https://img.shields.io/pypi/v/spotify_profile_monitor?style=flat-square&color=teal)](https://pypi.org/project/spotify-profile-monitor/)
[![GitHub Stars](https://img.shields.io/github/stars/misiektoja/spotify_profile_monitor?style=flat-square&color=magenta)](https://github.com/misiektoja/spotify_profile_monitor)
[![Python Versions](https://img.shields.io/badge/python-3.9+-blueviolet?style=flat-square)](https://pypi.org/project/spotify-profile-monitor/)
[![License](https://img.shields.io/github/license/misiektoja/spotify_profile_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/spotify_profile_monitor/blob/main/LICENSE)
[![OpenSSF Scorecard](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Fspotify_profile_monitor&query=%24.score&label=openssf%20scorecard&style=flat-square)](https://scorecard.dev/viewer/?uri=github.com/misiektoja/spotify_profile_monitor)
[![Last Commit](https://img.shields.io/github/last-commit/misiektoja/spotify_profile_monitor?style=flat-square&color=green)](https://github.com/misiektoja/spotify_profile_monitor/commits/main)
[![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square)](https://github.com/misiektoja/spotify_profile_monitor)

Powerful Spotify tool for real-time tracking of profile changes, playlist updates, follower growth, collaborators and more - delivered straight to your terminal, inbox or webhook.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/spotify_profile_monitor.png" alt="spotify_profile_monitor_screenshot" width="90%"/>
</p>

<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/spotify_profile_monitor/installation/#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install spotify_profile_monitor
```

Run the setup wizard:

```sh
spotify_profile_monitor --setup
```

The wizard asks for the target, authentication, polling interval and optional email or webhook alerts, then offers to run Doctor and start monitoring.

For the manual single-file method, optional extras and upgrade commands, see [Installation](https://misiektoja.github.io/spotify_profile_monitor/installation/).

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
- Read coloured terminal output with a customizable theme, while log files stay plain text.
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

✨ If you want to track Spotify friends' music activity, check out another tool I developed: [spotify_monitor](https://github.com/misiektoja/spotify_monitor).

🛠️ For Spotify Web Player token and secret-key utilities, see [Debugging Tools](https://misiektoja.github.io/spotify_profile_monitor/debugging/).

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install-run) above for first-time setup. The table uses PyPI commands. For the manual script equivalents, see [Command Format by Installation Method](https://misiektoja.github.io/spotify_profile_monitor/usage/#command-format).

| I want to... | Run this |
| --- | --- |
| Start monitoring with existing authentication | `spotify_profile_monitor TARGET`, where `TARGET` is a complete profile URL, `spotify:user:` URI or user ID |
| Check dependencies, authentication, connectivity and one target | `spotify_profile_monitor --doctor TARGET` |
| Import a Spotify login from a browser | Open [Spotify Web Player](https://open.spotify.com/) in the browser, sign in then run `spotify_profile_monitor --import-browser-cookie --browser firefox` |
| Enter or replace securely a manually extracted `SP_DC_COOKIE` | Run `spotify_profile_monitor --set-sp-dc` and enter `sp_dc` at the hidden prompt |
| Show profile details, followers, followings and playlist statistics | `spotify_profile_monitor TARGET -i` |
| Display or export the tracks of one playlist | `spotify_profile_monitor -l PLAYLIST_URL -b tracks.csv` |
| Find a Spotify user ID by name | `spotify_profile_monitor -s "user name"` |
| Configure and test webhook alerts | Use the setup wizard or follow [Webhook Settings](https://misiektoja.github.io/spotify_profile_monitor/configuration/#webhook-settings) |
| List every supported command-line flag | `spotify_profile_monitor --help` |

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence, and run multiple copies to monitor several users.

<a id="documentation"></a>
## Documentation

Full documentation is available at **[misiektoja.github.io/spotify_profile_monitor](https://misiektoja.github.io/spotify_profile_monitor/)**:

- [Installation](https://misiektoja.github.io/spotify_profile_monitor/installation/) - requirements, PyPI, manual script and upgrades
- [Setup & First Run](https://misiektoja.github.io/spotify_profile_monitor/setup-and-first-run/) - setup wizard, browser cookie import and first run
- [Configuration](https://misiektoja.github.io/spotify_profile_monitor/configuration/) - config file, token sources, targets, time zone, SMTP, webhooks and secrets
- [Usage](https://misiektoja.github.io/spotify_profile_monitor/usage/) - monitoring, listing, notifications, CSV export, blacklisting, intervals and signals
- [Troubleshooting](https://misiektoja.github.io/spotify_profile_monitor/troubleshooting/) - the `--doctor` self-check, logging levels and common problems
- [Debugging Tools](https://misiektoja.github.io/spotify_profile_monitor/debugging/) - TOTP token testing and secret key extraction
- [Testing](https://misiektoja.github.io/spotify_profile_monitor/testing/) - the offline suite, CI jobs and supply chain checks

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/spotify_profile_monitor/blob/main/RELEASE_NOTES.md) for details.

<a id="contributing"></a>
## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/spotify_profile_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/spotify_profile_monitor/blob/main/CODE_OF_CONDUCT.md).

<a id="security"></a>
## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/spotify_profile_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/spotify_profile_monitor/blob/main/SECURITY.md) covers the reporting process, the supported versions and the security posture of stored secrets, configuration loading and untrusted Spotify text.

<a id="maintainers"></a>
## Maintainers

- **misiektoja** ([@misiektoja](https://github.com/misiektoja))
- **tomballgithub** ([@tomballgithub](https://github.com/tomballgithub))

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/spotify_profile_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/spotify_profile_monitor/blob/main/THIRD_PARTY_NOTICES.md).

<a id="support"></a>
## Support

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).

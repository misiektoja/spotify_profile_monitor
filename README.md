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

<a id="quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/spotify_profile_monitor/installation/#new-to-python-check-and-install) first.

Install from PyPI:

```sh
pip install spotify_profile_monitor
```

Run the setup wizard:

```sh
spotify_profile_monitor --setup
```

The wizard asks for the target, the Spotify login and optional notifications. Review the settings before saving them. See [Setup & First Run](https://misiektoja.github.io/spotify_profile_monitor/setup-and-first-run/) for the browser login import and the manual cookie steps.

For the manual single-file method, optional extras and upgrade commands, see [Installation](https://misiektoja.github.io/spotify_profile_monitor/installation/).

<a id="features"></a>
## Features

### 📜 Playlists
- Detect added or removed playlists and tracks.
- Track playlist names, descriptions, likes and collaborators.
- See who added each track to a collaborative playlist.

### 👤 Profile Changes
- Track username and profile-picture changes.
- See when followers or followed accounts are added, removed or renamed.
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

Use [Quick Install & Run](#-quick-install--run) above for first-time setup. The table uses PyPI commands. For the manual script equivalents, see [Run Individual Commands](https://misiektoja.github.io/spotify_profile_monitor/setup-and-first-run/#run-individual-commands).

Replace the target placeholders with a complete Spotify profile URL, a `spotify:user:` URI or a user ID.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `spotify_profile_monitor --setup` |
| Start monitoring with existing authentication | `spotify_profile_monitor <spotify_target>` |
| Check authentication, connectivity and one target | `spotify_profile_monitor --doctor <spotify_target>` |
| Import a Spotify login from a browser | Open [Spotify Web Player](https://open.spotify.com/) in the browser, sign in then run `spotify_profile_monitor --import-browser-cookie --browser firefox` |
| Enter or replace securely a manually extracted `SP_DC_COOKIE` | Run `spotify_profile_monitor --set-sp-dc` and enter `sp_dc` at the hidden prompt |
| Configure and test webhook alerts | Use the setup wizard or follow [Webhook Settings](https://misiektoja.github.io/spotify_profile_monitor/configuration/#webhook-settings) |
| Save an SMTP password for email alerts | `spotify_profile_monitor --set-smtp-password` |
| Send a test email | `spotify_profile_monitor --send-test-email` |
| Save a new webhook URL | `spotify_profile_monitor --set-webhook-url` |
| Send a test webhook | `spotify_profile_monitor --send-test-webhook` |
| Show profile details, followers, followings and playlist statistics | `spotify_profile_monitor <spotify_target> -i` |
| Display or export the tracks of one playlist | `spotify_profile_monitor -l <playlist_url> -b tracks.csv` |
| Find a Spotify user ID by name | `spotify_profile_monitor -s "user name"` |
| List every supported command-line flag | `spotify_profile_monitor --help` |

Running the tool with no arguments offers the wizard if you have not saved a target. If a target is already saved, it starts monitoring that target.

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence and run multiple copies to monitor several targets.

For authentication, token sources, saved targets and notification setup, see the [full Setup & First Run guide](https://misiektoja.github.io/spotify_profile_monitor/setup-and-first-run/).

For browser profiles, manual cookie extraction, email and webhook setup, see [Configuration](https://misiektoja.github.io/spotify_profile_monitor/configuration/). For notification choices, listing commands and output files, see [Usage](https://misiektoja.github.io/spotify_profile_monitor/usage/).

If a run fails, start with [Doctor Preflight](https://misiektoja.github.io/spotify_profile_monitor/troubleshooting/#doctor-preflight).

<a id="documentation"></a>
## Documentation

Full documentation is available at **[misiektoja.github.io/spotify_profile_monitor](https://misiektoja.github.io/spotify_profile_monitor/)**:

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/spotify_profile_monitor/installation/) | Python walkthrough, PyPI or manual installation, upgrades |
| [Setup & First Run](https://misiektoja.github.io/spotify_profile_monitor/setup-and-first-run/) | Setup wizard, browser cookie import, the first monitoring run |
| [Configuration](https://misiektoja.github.io/spotify_profile_monitor/configuration/) | Config file, token sources, targets, time zone, SMTP, webhooks, storing secrets, check intervals |
| [Usage](https://misiektoja.github.io/spotify_profile_monitor/usage/) | Monitoring mode, listing mode, notifications, CSV export, blacklisting, signals, terminal output |
| [Troubleshooting](https://misiektoja.github.io/spotify_profile_monitor/troubleshooting/) | `--doctor` preflight checks, what to do when something fails, `--verbose` and `--debug` output |
| [Debugging Tools](https://misiektoja.github.io/spotify_profile_monitor/debugging/) | TOTP token testing and secret key extraction |
| [Testing](https://misiektoja.github.io/spotify_profile_monitor/testing/) | Running the offline suite, the linter and the docs build |
| [About](https://misiektoja.github.io/spotify_profile_monitor/about/) | Change log, contributing, security, license, support |

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

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/spotify_profile_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).

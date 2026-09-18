# Installation

Choose one installation method.

PyPI is usually the easiest local option. If you are new to Python or unsure whether Python is ready, follow [New to Python: check and install](#new-to-python-check-and-install).

<a id="requirements"></a>
## Requirements

* Python 3.9 or higher
* Libraries: `requests`, `python-dateutil`, `urllib3`, `pyotp`, `pytz`, `tzlocal`, `python-dotenv`, [Spotipy](https://github.com/spotipy-dev/spotipy), `wcwidth`, `pathvalidate`
* Optional for Chrome, Brave or Chromium cookie import: [pycookiecheat](https://github.com/n8henrie/pycookiecheat)
* Optional for email and ntfy artwork attachments: [Pillow](https://github.com/python-pillow/Pillow)
* Optional for better coloured output in the classic Windows Command Prompt: [colorama](https://github.com/tartley/colorama). `--doctor` reports it as missing only on Windows, where it makes a difference

Tested on:

* **macOS**: Tahoe, Sequoia, Sonoma, Ventura
* **Linux**: Raspberry Pi OS (Trixie, Bookworm, Bullseye), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2026/2025/2024
* **Windows**: 11, 10

It should work on other versions of macOS, Linux, Unix and Windows as well.


<a id="new-to-python-check-and-install"></a>
## New to Python: check and install

Use this section if you are new to Python or do not know what is already installed. The platform sections only prepare Python and `pip`. Everyone then uses the same Spotify Profile Monitor installation and setup commands. Spotify Profile Monitor requires Python 3.9 or newer and is currently tested through Python 3.14.

### Check whether Spotify Profile Monitor is already installed

Open Windows PowerShell on Windows or Terminal on macOS and Linux then run:

    spotify_profile_monitor --version

If this prints a Spotify Profile Monitor version, skip to [Run the setup wizard](#run-the-setup-wizard). If the command is not recognized or not found, continue with the section for your operating system.

### Windows 10 or 11

Open Windows PowerShell. Select **Start**, type `PowerShell` then open **Windows PowerShell**.

Check Python and `pip`:

    python --version
    pip --version

If both commands work and Python reports version 3.9 or newer, skip to [Install Spotify Profile Monitor](#install-spotify-profile-monitor).

If either command fails:

1. Open the official [Python Install Manager in Microsoft Store](https://apps.microsoft.com/detail/9NQ7512CXL7T), select **View in Store** then select **Install**. If Microsoft Store is unavailable, download the manager from [python.org](https://www.python.org/downloads/).

2. Close PowerShell then open it again.

3. Run `python --version`. Python Install Manager downloads the current Python release if no runtime is installed.

4. Check both commands again:

        python --version
        pip --version

If `pip` is still not recognized, run `py install --refresh`, close PowerShell then open it again. `py install` belongs to Python Install Manager and is used only to repair its Python commands.

See the official [Python Install Manager troubleshooting table](https://docs.python.org/3/using/windows.html#troubleshooting) if either check is still unavailable.

### macOS

Open Terminal. Press **Command+Space**, type `Terminal` then press **Return**.

Check Python and `pip`:

    python3 --version
    pip --version

If both commands work and Python reports version 3.9 or newer, skip to [Install Spotify Profile Monitor](#install-spotify-profile-monitor).

If either command fails:

1. Open the official [Python downloads for macOS](https://www.python.org/downloads/macos/). Select the latest stable Python 3.14 release then download its **macOS 64-bit universal2 installer**. This single installer supports Apple Silicon and Intel Macs.

2. Open the downloaded `.pkg` file. Keep the standard options, select **Continue** through the installer then enter your macOS password when requested.

3. Open the new **Python 3.14** folder in Applications then double-click **Install Certificates.command**. Wait until its Terminal window reports `update complete` then close that window.

4. Close Terminal then open it again.

5. Check both commands again:

        python3 --version
        pip --version

The official [Using Python on macOS](https://docs.python.org/3/using/mac.html) guide shows every installer screen and explains the installed applications.

### Ubuntu, Debian, Raspberry Pi OS or Kali

Open Terminal then check Python and `pip`:

    python3 --version
    pip --version

If both commands work and Python reports version 3.9 or newer, skip to [Install Spotify Profile Monitor](#install-spotify-profile-monitor).

If either command fails, install the missing packages:

    sudo apt update
    sudo apt install python3 python3-pip

The package manager keeps an existing current package instead of reinstalling it. Terminal may ask for your password. Type the password you use to sign in then press **Enter**. Terminal does not show password characters while you type.

Check both commands again:

    python3 --version
    pip --version

If Python reports a version older than 3.9, follow your distribution's instructions to install a supported Python version before continuing. For another Linux distribution, install Python 3.9 or newer plus `pip` through its package manager.

<a id="install-spotify-profile-monitor"></a>
### Install Spotify Profile Monitor

Every operating system uses the same command:

    pip install spotify_profile_monitor

Verify the installation:

    spotify_profile_monitor --version

On Linux, `pip` may report that the system Python is externally managed. If that happens, install Spotify Profile Monitor with the isolated `pipx` tool instead:

    sudo apt install pipx
    pipx ensurepath
    pipx install spotify_profile_monitor

Close Terminal, open it again then run `spotify_profile_monitor --version`.

<a id="run-the-setup-wizard"></a>
### Run the setup wizard

Every operating system uses the same command:

    spotify_profile_monitor --setup

The setup wizard can import a signed-in browser session, save the target and configure notifications. Continue to [Setup & First Run](setup-and-first-run.md) for a walkthrough of its questions.

<a id="choose-an-installation-method"></a>
## Choose an Installation Method

| Method | Best for | Command used in later examples |
| --- | --- | --- |
| PyPI | Users who already have Python or followed the beginner steps above | `spotify_profile_monitor [OPTIONS]` |
| Manual script | Users who want to download and run one Python file | `python3 spotify_profile_monitor.py [OPTIONS]` on macOS/Linux or `python spotify_profile_monitor.py [OPTIONS]` on Windows |

Later pages use the short PyPI command. If you chose the manual script, keep the options after `spotify_profile_monitor` and replace the command itself with the one in the table. The setup wizard and `--help` also print commands for the detected installation.

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install spotify_profile_monitor
spotify_profile_monitor --version
```

Optional extras include the base package. Choose the extra you need instead of running the plain install first.

Firefox cookie import needs no extra dependency. To import from Chrome, Brave or Chromium on macOS or Linux install the browser extra:

```sh
pip install "spotify_profile_monitor[browser]"
```

This installs Spotify Profile Monitor and the optional `pycookiecheat` dependency.

Artwork in email and ntfy alerts is optional. Install the artwork extra to attach profile pictures and playlist or album covers to those notifications:

```sh
pip install "spotify_profile_monitor[notification-images]"
```

This installs Spotify Profile Monitor and the optional Pillow dependency. Python 3.10 and newer get the current Pillow, while Python 3.9 gets the last release that still supports it. Without it the tool runs normally and the affected alerts stay text-only. The [setup wizard](setup-and-first-run.md#run-the-setup-wizard) can also install this extra for you when you enable artwork.

Extras can be installed together:

```sh
pip install "spotify_profile_monitor[browser,notification-images]"
```

<a id="install-the-manual-script"></a>
### Install the Manual Script

Download the script and dependency list into the same directory:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/spotify_profile_monitor.py
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/requirements.txt
```

You can also download [spotify_profile_monitor.py](https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/spotify_profile_monitor.py) and [requirements.txt](https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/requirements.txt) in a browser or use the files from a cloned repository.

Install the core dependencies:

```sh
pip install -r requirements.txt
```

You can install the core dependencies directly if you downloaded only the script:

```sh
pip install requests python-dateutil urllib3 pyotp pytz tzlocal python-dotenv spotipy wcwidth pathvalidate
```

For optional Chrome, Brave or Chromium import on macOS or Linux install `pycookiecheat`:

```sh
pip install "pycookiecheat>=0.8"
```

For optional artwork in email and ntfy alerts install `Pillow`:

```sh
pip install "Pillow>=12.0.0"
```

On Python 3.9 install the last release that supports it instead:

```sh
pip install "Pillow>=11.3.0,<12"
```

On the classic Windows Command Prompt, install `colorama` for better coloured output:

```sh
pip install colorama
```

Verify the script:

```sh
python3 spotify_profile_monitor.py --version
```

Use `python spotify_profile_monitor.py --version` on Windows.


<a id="next-step"></a>
## Next Step

Continue to [Setup & First Run](setup-and-first-run.md). It walks through the setup wizard, browser cookie import and the first monitoring run.

<a id="upgrading"></a>
## Upgrading

Upgrading does not remove your configuration, `.env` secrets, logs, CSV files or saved history. Keep those files in the same working directory or another persistent location.

### Upgrade a PyPI Installation

```sh
pip install --upgrade spotify_profile_monitor
spotify_profile_monitor --version
```

Retain any optional extras you use during the upgrade:

```sh
pip install --upgrade "spotify_profile_monitor[browser,notification-images]"
```

### Upgrade a Manual Installation

Replace [spotify_profile_monitor.py](https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/spotify_profile_monitor.py) and [requirements.txt](https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/requirements.txt) with the newest copies. You can download them in a browser, use the files from an updated clone or run:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/spotify_profile_monitor.py
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/requirements.txt
pip install --upgrade -r requirements.txt
python3 spotify_profile_monitor.py --version
```

Refresh the dependencies even when `requirements.txt` appears unchanged because a new release may add or change a required library.

Use `python spotify_profile_monitor.py --version` on Windows. If you modified the script itself, save your changes before replacing it and reapply them to the new version.

### Check Upgrade

After any upgrade run the doctor command:

```sh
spotify_profile_monitor --doctor
```

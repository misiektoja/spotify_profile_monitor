#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v3.7.1

OSINT tool implementing real-time tracking of Spotify users activities and profile changes including playlists:
https://github.com/misiektoja/spotify_profile_monitor/

Python pip3 requirements:

requests
python-dateutil
urllib3
pyotp (needed for web-player token generation)
pytz
tzlocal (optional)
python-dotenv (optional)
spotipy
wcwidth (optional, needed by TRUNCATE_CHARS feature)
pathvalidate (optional, needed by --export-all-playlists)
Pillow (needed for email and ntfy artwork attachments)
"""

VERSION = "3.7.1"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
# Select the method used to obtain the Spotify access token
# Available options:
#   cookie     - uses the sp_dc cookie to retrieve a token via the Spotify web endpoint (recommended)
#   oauth_app  - uses the Client Credentials OAuth flow (app-level token for public data, has some limitations)
#   oauth_user - uses the Authorization Code OAuth flow (user-level token for public and private data, has some limitations)
#   client     - uses captured credentials from the Spotify desktop client and a Protobuf-based login flow (for advanced users)
TOKEN_SOURCE = "cookie"

# Spotify target to monitor as a complete profile URL, spotify:user URI or user ID
# A positional command-line target overrides this value
TARGET_USER_URI_ID = ""

# ---------------------------------------------------------------------

# The section below is used when the token source is set to 'cookie'
# (to configure the alternative 'oauth_app', 'oauth_user' or 'client' methods, see the section at the end of this config block)
#
# - Recommended: open Spotify Web Player in Firefox, sign in and run:
#     spotify_profile_monitor --import-browser-cookie --browser firefox
#   Firefox import needs no extra dependency. Chrome, Brave and Chromium are also supported on macOS and Linux
#   through the optional browser extra. Imported cookies are validated before the dotenv file changes.
# - Manual fallback: follow the cookie extraction guide:
#   https://github.com/misiektoja/spotify_profile_monitor#manual-cookie-extraction
# - Provide the SP_DC_COOKIE secret using one of the following methods:
#   - Recommended manual entry: run --set-sp-dc to use a hidden prompt, validate the cookie and save it to ".env"
#   - Add it directly to a ".env" file for persistent use
#   - Set it as an environment variable (for example export SP_DC_COOKIE=...)
#   - Pass it at runtime with -u / --spotify-dc-cookie (not recommended because command-line secrets may be exposed)
#   - Fallback: hard-code it in the code or config file (not recommended)
SP_DC_COOKIE = "your_sp_dc_cookie_value"

# ---------------------------------------------------------------------

# The optional section below enables the legacy Client Credentials OAuth path
# Do not create a new Spotify app only for this tool because new apps normally lack the required legacy endpoint access
# Configure these values only for an existing app that you have verified still supports the legacy endpoints
# Restricted or incomplete apps fall back automatically to the Spotify web-player backend for public playlists
#
# To use a working existing app:
#   - Log in to Spotify Developer dashboard: https://developer.spotify.com/dashboard
#   - Open the existing app with verified legacy endpoint access
#   - Copy the 'Client ID' and 'Client Secret'
#
# Provide the SP_APP_CLIENT_ID and SP_APP_CLIENT_SECRET secrets using one of the following methods:
#   - Pass it at runtime with -r / --oauth-app-creds (use SP_APP_CLIENT_ID:SP_APP_CLIENT_SECRET format - note the colon separator)
#   - Set it as an environment variable (e.g. export SP_APP_CLIENT_ID=...; export SP_APP_CLIENT_SECRET=...)
#   - Add it to ".env" file (SP_APP_CLIENT_ID=... and SP_APP_CLIENT_SECRET=...) for persistent use
#   - Fallback: hard-code it in the code or config file
#
# The tool automatically refreshes and caches the OAuth app access token when these credentials are configured
SP_APP_CLIENT_ID = "your_spotify_app_client_id"
SP_APP_CLIENT_SECRET = "your_spotify_app_client_secret"

# Path to cache file used to store OAuth app access tokens across tool restarts
# Set to empty to use in-memory cache only
SP_APP_TOKENS_FILE = ".spotify-profile-monitor-oauth-app.json"

# ---------------------------------------------------------------------

# SMTP settings for sending email notifications
# If left as-is, no notifications will be sent
#
# Provide the SMTP_PASSWORD secret using one of the following methods:
#   - Set it as an environment variable (e.g. export SMTP_PASSWORD=...)
#   - Add it to ".env" file (SMTP_PASSWORD=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# Whether to send an email when the user's profile changes
# Can also be enabled via the -p flag
PROFILE_NOTIFICATION = False

# Whether to attach playlist or album artwork to email notifications
# Image preparation failures fall back to text-only email
EMAIL_IMAGES = False

# Whether to send an email when followers or followings change
# Only applies if PROFILE_NOTIFICATION / -p is enabled
# Can also be disabled via the -g flag
FOLLOWERS_FOLLOWINGS_NOTIFICATION = True

# Whether to send an email on errors
# Can also be disabled via the -e flag
ERROR_NOTIFICATION = True

# ----------------------------
# Webhook Notifications
# ----------------------------

# Master switch for webhook notifications through Discord or ntfy
# Event settings below select which notifications are sent
# Can also be enabled via the --webhook flag
WEBHOOK_ENABLED = False

# Service used to deliver webhook notifications: "discord" or "ntfy"
# Known Discord and ntfy.sh URLs correct a mismatched configured value at runtime
# Can also be set via the --webhook-provider flag
WEBHOOK_PROVIDER = "discord"

# Private destination used to send webhook notifications
# Discord: Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL
# ntfy: complete topic URL such as https://ntfy.sh/your-private-topic
# Prefer --set-webhook-url, an environment variable or a dotenv file instead of storing this private URL here
# The --webhook-url flag is available for one-run overrides but may leave the private URL in shell history
WEBHOOK_URL = "your_webhook_url"

# Discord display name (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_USERNAME = "Spotify Profile Monitor"

# Discord avatar URL (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_AVATAR_URL = ""

# Whether to send a webhook notification when the user's profile changes
# Can also be enabled via the --webhook-profile flag
WEBHOOK_PROFILE_NOTIFICATION = False

# Whether to send webhook notifications when followers or followings change
# Only applies if WEBHOOK_PROFILE_NOTIFICATION / --webhook-profile is enabled
# Can also be disabled via the --no-webhook-followers-followings-notify flag
WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION = True

# Whether to send a webhook notification on monitoring errors
# Can also be enabled via --webhook-errors or disabled via --no-webhook-error-notify
WEBHOOK_ERROR_NOTIFICATION = True

# Optional request headers for advanced webhook integrations
# Values support the same placeholders as WEBHOOK_TEMPLATE
WEBHOOK_HEADERS = {}

# ----------------------------
# Advanced Webhook Settings
# ----------------------------

# Discord-format webhook request payload template
# Applies only when WEBHOOK_PROVIDER is "discord". The "ntfy" provider needs no template and ignores this
# value: it sends the alert body as a native ntfy message with the subject as its title. Use WEBHOOK_HEADERS
# to add ntfy options such as priority or tags
# Supported placeholders include title, description, version, image_url, fields, fields_str, color, timestamp,
# username and avatar_url
WEBHOOK_TEMPLATE = {
    "username": "{username}",
    "avatar_url": "{avatar_url}",
    "allowed_mentions": {
        "parse": [],
    },
    "embeds": [{
        "title": "{title}",
        "description": "{description}",
        "color": "{color}",
        "footer": {
            "text": "Spotify Profile Monitor v{version}",
        },
        "timestamp": "{timestamp}",
    }],
}

# Optional transformations applied to WEBHOOK_TEMPLATE and WEBHOOK_HEADERS values
# Tuple format: (field_to_target, method_name, *optional_arguments)
#
# Examples:
#   [
#       ("title", "upper"),
#       ("description", "replace", "**", ""),
#       ("description", "strip"),
#   ]
WEBHOOK_TRANSFORMS = []

# Optional ntfy access token for Bearer authentication
# Prefer an environment variable or dotenv file instead of storing this token here
NTFY_ACCESS_TOKEN = ""

# Whether to attach profile or playlist artwork to supported ntfy alerts
# Image preparation or delivery failures fall back to text
NTFY_IMAGES = True

# How often to check for user profile changes; in seconds
# Can also be set using the -c flag
SPOTIFY_CHECK_INTERVAL = 1800  # 30 mins

# Retry interval after errors; in seconds
# Can also be set using the -m flag
SPOTIFY_ERROR_INTERVAL = 300  # 5 mins

# Set your local time zone so that Spotify timestamps are converted accordingly (e.g. 'Europe/Warsaw')
# Use this command to list all time zones supported by pytz:
#   python3 -c "import pytz; print('\\n'.join(pytz.all_timezones))"
# If set to 'Auto', the tool will try to detect your local time zone automatically (requires tzlocal)
LOCAL_TIMEZONE = 'Auto'

# Notify when the user's profile picture changes? (via console and email if PROFILE_NOTIFICATION / -p is enabled)
# If enabled, the current profile picture is saved as:
#   - spotify_profile_<user_uri_id/file_suffix>_pic.jpeg (initial)
#   - spotify_profile_<user_uri_id/file_suffix>_pic_YYmmdd_HHMM.jpeg (on change)
# The binary JPEGs are compared to detect changes
# Can also be disabled via the -j flag
DETECT_CHANGED_PROFILE_PIC = True

# If you have 'imgcat' installed, you can set its path below to display profile pictures directly in your terminal
# If you specify only the binary name, it will be auto-searched in your PATH
# Leave empty to disable this feature
IMGCAT_PATH = "imgcat"

# SHA256 hash needed to search for Spotify users (used with -s)
#
# - Run an intercepting proxy of your choice (like Proxyman)
# - Launch the Spotify desktop client and search for some user
# - Look for requests with the 'searchUsers' or 'searchDesktop' operation name
# - Display the details of one of these requests and copy the 'sha256Hash' parameter value
#   (string marked as `XXXXXXXXXX` below)
#
# Example request:
# https://api-partner.spotify.com/pathfinder/v1/query?operationName=searchUsers&variables={"searchTerm":"user_uri_id","offset":0,"limit":5,"numberOfTopResults":5,"includeAudiobooks":false}&extensions={"persistedQuery":{"version":1,"sha256Hash":"XXXXXXXXXX"}}
#
# Provide the SP_SHA256 secret using one of the following methods:
#   - Set it as an environment variable (e.g. export SP_SHA256=...)
#   - Add it to ".env" file (SP_SHA256=...) for persistent use
#   - Fallback: hard-code it in the code or config file
SP_SHA256 = "your_spotify_client_sha256"

# Notify when user's public playlists change? (via console and email if PROFILE_NOTIFICATION / -p is enabled)
# Detects:
#   - added/removed tracks
#   - name or description changes
#   - number of likes
#   - collaborators
# This option also affects behavior when using -i (listing mode)
# It can also be disabled via the -q flag
DETECT_CHANGES_IN_PLAYLISTS = True

# By default, only public playlists owned by the user are fetched
# Set to True to include all public playlists on their profile (e.g. created by others, but added to the profile)
# Can also be enabled via the -k flag
GET_ALL_PLAYLISTS = False

# Some users don't list all their public playlists on their profile, but if you know a playlist's URI, you can still monitor it
#
# Example:
#
# ADD_PLAYLISTS_TO_MONITOR = [
#     {'uri': 'spotify:playlist:{playlist_id1}', 'owner_name': '{user_id}', 'owner_uri': 'spotify:user:{user_id}'},
#     {'uri': 'spotify:playlist:{playlist_id2}', 'owner_name': '{user_id}', 'owner_uri': 'spotify:user:{user_id}'}
# ]
# Replace {playlist_id1} and {playlist_id2} with the playlist IDs to monitor and {user_id} with the owner's Spotify user ID
ADD_PLAYLISTS_TO_MONITOR = []

# Ignore Spotify-owned playlists when monitoring?
# Set to True to avoid tracking Spotify-generated playlists that often change frequently (likes, tracks etc.)
IGNORE_SPOTIFY_PLAYLISTS = True

# Max number of public playlists to monitor
PLAYLISTS_LIMIT = 50

# Max number of recently played artists to show (when using -a)
RECENTLY_PLAYED_ARTISTS_LIMIT = 50

# Max number of recently played artists to show (when using -i)
RECENTLY_PLAYED_ARTISTS_LIMIT_INFO = 15

# Occasionally, the Spotify API glitches and returns an empty list of user playlists
# To avoid false alarms, we delay notifications until this happens PLAYLISTS_DISAPPEARED_COUNTER times in a row
PLAYLISTS_DISAPPEARED_COUNTER = 3

# Occasionally, the Spotify API glitches and returns incomplete/empty playlists list
# (e.g. network issues, API transient failures or playlists temporarily not visible)
# To avoid false alarms, we delay playlist change notifications until the same change is seen
# PLAYLISTS_CHANGE_COUNTER times in a row (set to 0 to disable this protection)
PLAYLISTS_CHANGE_COUNTER = 2

# Occasionally, the Spotify API glitches and returns an empty list of user followers / followings
# To avoid false alarms, we delay notifications until this happens FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER times in a row
FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER = 3

# Occasionally, the Spotify API glitches and returns inconsistent collaborator data for playlists
# (e.g. missing or transient `added_by` fields on tracks can cause collaborator sets to flicker)
# To avoid false alarms, we delay collaborator change notifications until the same change is seen
# COLLABORATORS_CHANGE_COUNTER times in a row
COLLABORATORS_CHANGE_COUNTER = 2

# To avoid multiple errors at same time during networking issues when communicating with Spotify,
# enabling this will eliminate showing multiple errors at a time, replacing
# that output with "(Masking additional errors)"
HIDE_DUPLICATE_NETWORK_ERRORS = False

# Optional: specify user agent manually
#
# When the token source is 'cookie' - set it to web browser user agent, some examples:
# Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0
# Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:139.0) Gecko/20100101 Firefox/139.0
#
# When the token source is 'client' - set it to Spotify desktop client user agent, some examples:
# Spotify/126200580 Win32_x86_64/0 (PC desktop)
# Spotify/126400408 OSX_ARM64/OS X 15.5.0 [arm 2]
#
# Leave empty to auto-generate it randomly for specific token source
USER_AGENT = ""

# How often to print a "liveness check" message to the output; in seconds
# Set to 0 to disable
LIVENESS_CHECK_INTERVAL = 43200  # 12 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://api.spotify.com/v1'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# Whether to enable / disable SSL certificate verification while sending https requests
VERIFY_SSL = True

# CSV file to write all profile changes
# Can also be set using the -b flag
CSV_FILE = ""

# Format used when exporting playlists (-l) or liked songs (-x) to CSV file:
# 1 - default format used for activity logging ['Date', 'Type', 'Name', 'Old', 'New']
# 2 - playlist dump format ['Date', 'Playlist Name', 'Artist', 'Track']
CSV_FILE_FORMAT_EXPORT = 2

# Set to true if you want the simplified output when exporting playlists (-l) or liked songs (-x) to allow
# direct import into spotify_monitor tool
CLEAN_OUTPUT = False

# Filename with Spotify playlists to ignore
# Can also be set using the -t flag
PLAYLISTS_TO_SKIP_FILE = ""

# Location of the optional dotenv file which can keep secrets
# If not specified it will try to auto-search for .env files
# To disable auto-search, set this to the literal string "none"
# Can also be set using the --env-file flag
# The setup wizard keeps private values here and preserves unrelated dotenv entries
DOTENV_FILE = ""

# Suffix to append to the output filenames instead of the normalized Spotify user ID
# Can also be set using the -y flag
FILE_SUFFIX = ""

# Base name for the log file. Output will be saved to spotify_profile_monitor_<user_uri_id/file_suffix>.log
# Can include a directory path to specify the location, e.g. ~/some_dir/spotify_profile_monitor
SP_LOGFILE = "spotify_profile_monitor"

# Whether to disable logging to spotify_profile_monitor_<user_uri_id/file_suffix>.log
# Can also be disabled via the -d flag
DISABLE_LOGGING = False

# Controls conversion of separator-only log lines to ASCII:
#   "Auto" - enable on Windows only (default)
#   "On"   - enable on every operating system
#   "Off"  - preserve Unicode separators in logs
ASCII_LOG_SEPARATORS = "Auto"

# Enable debug mode for technical logging (can also be enabled via --debug flag)
# Shows request flow, selected params and internal state changes (with sensitive values redacted)
DEBUG_MODE = False

# Enable verbose mode for occasional operational events and the complete startup summary
# Full request flow and internal state details remain exclusive to DEBUG_MODE
VERBOSE_MODE = False

# Width of horizontal line
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# Max characters per line when printing to screen to avoid line wrapping
# Does not affect log file output
# Set to 999 to auto-detect terminal width
# Applies only when DISABLE_LOGGING is False
# Can also be set via the --truncate flag
TRUNCATE_CHARS = 0

# Value used by signal handlers to increase or decrease profile check interval (SPOTIFY_CHECK_INTERVAL); in seconds
SPOTIFY_CHECK_SIGNAL_VALUE = 300  # 5 minutes

# Whether to show Apple Music URL in console and emails
ENABLE_APPLE_MUSIC_URL = True

# Whether to show YouTube Music URL in console and emails
ENABLE_YOUTUBE_MUSIC_URL = True

# Whether to show Amazon Music URL in console and emails
ENABLE_AMAZON_MUSIC_URL = False

# Whether to show Deezer URL in console and emails
ENABLE_DEEZER_URL = False

# Whether to show Tidal URL in console and emails
# Note: Tidal requires users to be logged in to their account in the web browser to use the search functionality
ENABLE_TIDAL_URL = False

# Whether to show Genius lyrics URL in console and emails
ENABLE_GENIUS_LYRICS_URL = True

# Whether to show AZLyrics URL in console and emails
ENABLE_AZLYRICS_URL = False

# Whether to show Tekstowo.pl lyrics URL in console and emails
ENABLE_TEKSTOWO_URL = False

# Whether to show Musixmatch lyrics URL in console and emails
# Note: Musixmatch requires users to be logged in to their account in the web browser to use the search functionality
ENABLE_MUSIXMATCH_URL = False

# Whether to show Lyrics.com lyrics URL in console and emails
ENABLE_LYRICS_COM_URL = False

# Token refresh settings used by cookie mode and the anonymous playlist backend

# Maximum number of attempts to get a valid access token in a single run of the spotify_get_access_token_from_sp_dc() function
TOKEN_MAX_RETRIES = 3

# Interval between access token retry attempts; in seconds
TOKEN_RETRY_TIMEOUT = 0.5  # 0.5 second

# ----------------------------------------------
# Advanced options for 'cookie' token source
# Modifying the values below is NOT recommended!
# ----------------------------------------------

# TOTP parameters used to sign Spotify web-player access token requests
#
# The web player derives a time-based one-time password from a versioned secret embedded in its JavaScript
# bundle and sends it with every token request. Version 3.5 ships the v61 secret that the web player has
# selected since January 2026, so no external secret dictionary is downloaded at runtime.
#
# You only need to change these if Spotify rotates the secret and cookie-based auth starts failing (for
# example 'Bad credentials' or repeated token refresh errors) even though your sp_dc cookie is still valid.
# To refresh them:
#   - Run the spotify_monitor_secret_grabber tool to extract the current version and cipher bytes from the
#     live web-player bundle (see the "Secret Key Extraction from Spotify Web Player Bundles" README section)
#   - Set TOTP_VERSION to the extracted version identifier (a positive integer)
#   - Set TOTP_SECRET_CIPHER_BYTES to the extracted cipher bytes (a non-empty sequence of integers)
TOTP_VERSION = 61
TOTP_SECRET_CIPHER_BYTES = (44, 55, 47, 42, 70, 40, 34, 114, 76, 74, 50, 111, 120, 97, 75, 76, 94, 102, 43, 69, 49, 120, 118, 80, 64, 78)

# ---------------------------------------------------------------------

# The section below is used when the token source is set to 'oauth_user'
# (Authorization Code OAuth Flow)
#
# To obtain the credentials:
#   - Log in to Spotify Developer dashboard: https://developer.spotify.com/dashboard
#   - Create a new app
#   - For 'Redirect URL', use: http://127.0.0.1:1234
#   - Select 'Web API' as the intended API
#   - Copy the 'Client ID' and 'Client Secret' (the secret is not required if you're using PKCE mode)
#
# Provide the SP_USER_CLIENT_ID and SP_USER_CLIENT_SECRET secrets using one of the following methods:
#   - Pass it at runtime with -n / --oauth-user-creds (use SP_USER_CLIENT_ID:SP_USER_CLIENT_SECRET format - note the colon separator)
#   - Set it as an environment variable (e.g. export SP_USER_CLIENT_ID=...; export SP_USER_CLIENT_SECRET=...)
#   - Add it to ".env" file (SP_USER_CLIENT_ID=... and SP_USER_CLIENT_SECRET=...) for persistent use
#   - Fallback: hard-code it in the code or config file
#
# To use PKCE mode, set SP_USER_CLIENT_SECRET to an empty string ("")
#
# The tool automatically refreshes the access token, so it remains valid indefinitely
SP_USER_CLIENT_ID = "your_spotify_user_client_id"
SP_USER_CLIENT_SECRET = "your_spotify_user_client_secret"  # set to empty string ("") to use PKCE

# Redirect URI used during OAuth user authorization flow, must match value set in the Spotify Developer Dashboard
SP_USER_REDIRECT_URI = "http://127.0.0.1:1234"

# OAuth scopes requested for accessing user data - determines which Spotify APIs can be used with the token
# Leave it as it is below
SP_USER_SCOPE = "user-read-private playlist-read-private playlist-read-collaborative user-library-read user-read-recently-played user-top-read user-follow-read"

# Path to cache file used to store OAuth user access and refresh tokens across tool restarts
# Set to empty to use in-memory cache only
SP_USER_TOKENS_FILE = ".spotify-profile-monitor-oauth-user.json"

# ---------------------------------------------------------------------

# The section below is used when the token source is set to 'client'
#
# - Run an intercepting proxy of your choice (like Proxyman)
# - Launch the Spotify desktop client and look for requests to: https://login{n}.spotify.com/v3/login
#   (the 'login' part is suffixed with one or more digits)
# - Export the login request body (a binary Protobuf payload) to a file
#   (e.g. in Proxyman: right click the request -> Export -> Request Body -> Save File -> <login-request-body-file>)
#
# To automatically extract DEVICE_ID, SYSTEM_ID, USER_URI_ID and REFRESH_TOKEN from the exported binary login
# request Protobuf file:
#
# - Run the tool with the -w flag to indicate an exported file or specify its file name below
LOGIN_REQUEST_BODY_FILE = ""

# Alternatively, you can manually set the DEVICE_ID, SYSTEM_ID, USER_URI_ID and REFRESH_TOKEN options
# (however, using the automated method described above is recommended)
#
# These values can be extracted using one of the following methods:
#
# - Run spotify_profile_monitor with the -w flag without a positional Spotify target - it will decode the file and
#   print the values to stdout, example:
#       spotify_profile_monitor --token-source client -w <path-to-login-request-body-file>
#
# - Use the protoc tool (part of protobuf pip package):
#       pip install protobuf
#       protoc --decode_raw < <path-to-login-request-body-file>
#
# - Use the built-in Protobuf decoder in your intercepting proxy (if supported)
#
# The Protobuf structure is as follows:
#
#    {
#      1: {
#           1: "DEVICE_ID",
#           2: "SYSTEM_ID"
#         },
#      100: {
#           1: "USER_URI_ID",
#           2: "REFRESH_TOKEN"
#         }
#    }
#
# Provide the extracted values below (DEVICE_ID, SYSTEM_ID, USER_URI_ID). The REFRESH_TOKEN secret can be
# supplied using one of the following methods:
#   - Set it as an environment variable (e.g. export REFRESH_TOKEN=...)
#   - Add it to ".env" file (REFRESH_TOKEN=...) for persistent use
#   - Fallback: hard-code it in the code or config file
DEVICE_ID = "your_spotify_app_device_id"
SYSTEM_ID = "your_spotify_app_system_id"
USER_URI_ID = "your_spotify_user_uri_id"
REFRESH_TOKEN = "your_spotify_app_refresh_token"

# ----------------------------------------------
# Advanced options for 'client' token source
# Modifying the values below is NOT recommended!
# ----------------------------------------------

# Spotify login URL
LOGIN_URL = "https://login5.spotify.com/v3/login"

# Spotify client token URL
CLIENTTOKEN_URL = "https://clienttoken.spotify.com/v1/clienttoken"

# Platform-specific values for token generation so the Spotify client token requests match your exact Spotify desktop
# client build (arch, OS build, app version etc.)
#
# - Run an intercepting proxy of your choice (like Proxyman)
# - Launch the Spotify desktop client and look for requests to: https://clienttoken.spotify.com/v1/clienttoken
#   (these requests are sent every time client token expires, usually every 2 weeks)
# - Export the client token request body (a binary Protobuf payload) to a file
#   (e.g. in Proxyman: right click the request -> Export -> Request Body -> Save File -> <clienttoken-request-body-file>)
#
# To automatically extract APP_VERSION, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR and CLIENT_MODEL from the
# exported binary client token request Protobuf file:
#
# - Run the tool with the hidden -z flag to indicate an exported file or specify its file name below
CLIENTTOKEN_REQUEST_BODY_FILE = ""

# Alternatively, you can manually set the APP_VERSION, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR and
# CLIENT_MODEL options
#
# These values can be extracted using one of the following methods:
#
# - run spotify_profile_monitor with the hidden -z flag without a positional Spotify target - it will decode the file
#   and print the values to stdout, example:
#       spotify_profile_monitor --token-source client -z <path-to-clienttoken-request-body-file>
#
# - use the protoc tool (part of protobuf pip package):
#       pip install protobuf
#       protoc --decode_raw < <path-to-clienttoken-request-body-file>
#
# - use the built-in Protobuf decoder in your intercepting proxy (if supported)
#
# The Protobuf structure is as follows:
#
# 1: 1
# 2 {
#   1: "APP_VERSION"
#   2: "DEVICE_ID"
#   3 {
#     1 {
#       4 {
#         1: "CPU_ARCH"
#         3: "OS_BUILD"
#         4: "PLATFORM"
#         5: "OS_MAJOR"
#         6: "OS_MINOR"
#         8: "CLIENT_MODEL"
#       }
#     }
#     2: "SYSTEM_ID"
#   }
# }
#
# Provide the extracted values below (except for DEVICE_ID and SYSTEM_ID as it was already provided via -w)
CPU_ARCH = 10
OS_BUILD = 19045
PLATFORM = 2
OS_MAJOR = 9
OS_MINOR = 9
CLIENT_MODEL = 34404

# App version (e.g. '1.2.62.580.g7e3d9a4f')
# Leave empty to auto-generate from USER_AGENT
APP_VERSION = ""

# ---------------------------------------------------------------------
"""

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Default dummy values so linters shut up
# Do not change values below - modify them in the configuration section or config file instead
TOKEN_SOURCE = ""
TARGET_USER_URI_ID = ""
SP_DC_COOKIE = ""
SP_APP_CLIENT_ID = ""
SP_APP_CLIENT_SECRET = ""
SP_APP_TOKENS_FILE = ""
SP_USER_CLIENT_ID = ""
SP_USER_CLIENT_SECRET = ""
SP_USER_REDIRECT_URI = ""
SP_USER_SCOPE = ""
SP_USER_TOKENS_FILE = ""
LOGIN_REQUEST_BODY_FILE = ""
CLIENTTOKEN_REQUEST_BODY_FILE = ""
LOGIN_URL = ""
USER_AGENT = ""
DEVICE_ID = ""
SYSTEM_ID = ""
USER_URI_ID = ""
REFRESH_TOKEN = ""
CLIENTTOKEN_URL = ""
APP_VERSION = ""
CPU_ARCH = 0
OS_BUILD = 0
PLATFORM = 0
OS_MAJOR = 0
OS_MINOR = 0
CLIENT_MODEL = 0
SMTP_HOST = ""
SMTP_PORT = 0
SMTP_USER = ""
SMTP_PASSWORD = ""
SMTP_SSL = False
SENDER_EMAIL = ""
RECEIVER_EMAIL = ""
PROFILE_NOTIFICATION = False
EMAIL_IMAGES = False
FOLLOWERS_FOLLOWINGS_NOTIFICATION = False
ERROR_NOTIFICATION = False
WEBHOOK_ENABLED = False
WEBHOOK_URL = ""
WEBHOOK_PROVIDER = ""
WEBHOOK_USERNAME = ""
WEBHOOK_AVATAR_URL = ""
WEBHOOK_HEADERS = {}
WEBHOOK_TEMPLATE = {}
WEBHOOK_TRANSFORMS = []
NTFY_ACCESS_TOKEN = ""
NTFY_IMAGES = False
WEBHOOK_PROFILE_NOTIFICATION = False
WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION = False
WEBHOOK_ERROR_NOTIFICATION = False
SPOTIFY_CHECK_INTERVAL = 0
SPOTIFY_ERROR_INTERVAL = 0
LOCAL_TIMEZONE = ""
DETECT_CHANGED_PROFILE_PIC = False
IMGCAT_PATH = ""
SP_SHA256 = ""
DETECT_CHANGES_IN_PLAYLISTS = False
GET_ALL_PLAYLISTS = False
ADD_PLAYLISTS_TO_MONITOR = []
IGNORE_SPOTIFY_PLAYLISTS = False
HIDE_DUPLICATE_NETWORK_ERRORS = False
PLAYLISTS_LIMIT = 0
RECENTLY_PLAYED_ARTISTS_LIMIT = 0
RECENTLY_PLAYED_ARTISTS_LIMIT_INFO = 0
PLAYLISTS_DISAPPEARED_COUNTER = 0
FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER = 0
COLLABORATORS_CHANGE_COUNTER = 0
PLAYLISTS_CHANGE_COUNTER = 0
USER_AGENT = ""
LIVENESS_CHECK_INTERVAL = 0
CHECK_INTERNET_URL = ""
CHECK_INTERNET_TIMEOUT = 0
VERIFY_SSL = False
CSV_FILE = ""
CSV_FILE_FORMAT_EXPORT = 0
CLEAN_OUTPUT = False
PLAYLISTS_TO_SKIP_FILE = ""
DOTENV_FILE = ""
FILE_SUFFIX = ""
SP_LOGFILE = ""
DISABLE_LOGGING = False
ASCII_LOG_SEPARATORS = "Auto"
DEBUG_MODE = False
VERBOSE_MODE = False
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
SPOTIFY_CHECK_SIGNAL_VALUE = 0
ENABLE_APPLE_MUSIC_URL = False
ENABLE_YOUTUBE_MUSIC_URL = False
ENABLE_AMAZON_MUSIC_URL = False
ENABLE_DEEZER_URL = False
ENABLE_TIDAL_URL = False
ENABLE_GENIUS_LYRICS_URL = False
ENABLE_AZLYRICS_URL = False
ENABLE_TEKSTOWO_URL = False
ENABLE_MUSIXMATCH_URL = False
ENABLE_LYRICS_COM_URL = False
TOKEN_MAX_RETRIES = 0
TOKEN_RETRY_TIMEOUT = 0.0
TOTP_VERSION = 0
TOTP_SECRET_CIPHER_BYTES: tuple[int, ...] = ()
TRUNCATE_CHARS = 0
EXPORT_ALL = False

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "spotify_profile_monitor.conf"
DEFAULT_DOTENV_FILENAME = ".env"

# List of secret keys to load from env/config
SECRET_KEYS = ("SP_DC_COOKIE", "SP_APP_CLIENT_ID", "SP_APP_CLIENT_SECRET", "SP_USER_CLIENT_ID", "SP_USER_CLIENT_SECRET", "REFRESH_TOKEN", "SP_SHA256", "SMTP_PASSWORD", "WEBHOOK_URL", "NTFY_ACCESS_TOKEN")

# Config values that retain safe template defaults in generated files
SENSITIVE_CONFIG_KEYS = frozenset((*SECRET_KEYS, "WEBHOOK_HEADERS"))

# Browsers supported by the private sp_dc importer
IMPORT_BROWSERS = ("firefox", "chrome", "brave", "chromium")
CHROMIUM_IMPORT_BROWSERS = ("chrome", "brave", "chromium")
CHROMIUM_USER_DATA_DIRS = {
    "Darwin": {
        "chrome": "Library/Application Support/Google/Chrome",
        "brave": "Library/Application Support/BraveSoftware/Brave-Browser",
        "chromium": "Library/Application Support/Chromium",
    },
    "Linux": {
        "chrome": ".config/google-chrome",
        "brave": ".config/BraveSoftware/Brave-Browser",
        "chromium": ".config/chromium",
    },
}

PROJECT_URL = "https://github.com/misiektoja/spotify_profile_monitor"
QUICK_START_GUIDE_URL = PROJECT_URL + "#quick-start"
INSTALLATION_GUIDE_URL = PROJECT_URL + "#installation"
CONFIG_GUIDE_URL = PROJECT_URL + "#configuration-file"
COOKIE_GUIDE_URL = PROJECT_URL + "#spotify-sp_dc-cookie"
MANUAL_COOKIE_GUIDE_URL = PROJECT_URL + "#manual-cookie-extraction"
CLIENT_GUIDE_URL = PROJECT_URL + "#spotify-desktop-client"
TARGET_GUIDE_URL = PROJECT_URL + "#how-to-find-a-friends-spotify-profile-url"
SMTP_GUIDE_URL = PROJECT_URL + "#smtp-settings"
WEBHOOK_GUIDE_URL = PROJECT_URL + "#webhook-settings"
SECRETS_GUIDE_URL = PROJECT_URL + "#storing-secrets"
INTERVALS_GUIDE_URL = PROJECT_URL + "#check-intervals"
DOCTOR_GUIDE_URL = PROJECT_URL + "#doctor-self-check"
OAUTH_GUIDE_URL = PROJECT_URL + "#spotify-oauth-app"
OAUTH_USER_GUIDE_URL = PROJECT_URL + "#spotify-oauth-user"
BROWSER_COOKIE_GUIDE_URL = PROJECT_URL + "#browser-cookie-import"
SETUP_GUIDE_URL = PROJECT_URL + "#setup-wizard"
SPOTIFY_WEB_BASE_URL = "https://open.spotify.com"
SPOTIFY_WEB_LOGIN_URL = SPOTIFY_WEB_BASE_URL + "/"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
SPOTIFY_PARTNER_BASE_URL = "https://api-partner.spotify.com"
SPOTIFY_SPCLIENT_BASE_URL = "https://spclient.wg.spotify.com"
SPOTIFY_PRESENCE_URL = "https://guc-spclient.spotify.com/presence-view/v1/buddylist"
SPOTIFY_PROFILE_API_BASE_URL = SPOTIFY_SPCLIENT_BASE_URL + "/user-profile-view/v3/profile"
SPOTIFY_OAUTH_VALIDATION_TRACK_URL = SPOTIFY_API_BASE_URL + "/tracks/7tFiyTwD0nx5a1eklYtX2J"
SPOTIFY_OAUTH_USER_URL = SPOTIFY_API_BASE_URL + "/me"
SPOTIFY_CLIENTTOKEN_ORIGIN = "https://clienttoken.spotify.com"
SPOTIFY_DEVELOPER_DASHBOARD_URL = "https://developer.spotify.com/dashboard"
SPOTIFY_APPS_GUIDE_URL = "https://developer.spotify.com/documentation/web-api/concepts/apps"
NTFY_PUBLIC_BASE_URL = "https://ntfy.sh"
APPLE_MUSIC_SEARCH_URL = "https://music.apple.com/pl/search"
GENIUS_SEARCH_URL = "https://genius.com/search"
AZLYRICS_SEARCH_URL = "https://www.azlyrics.com/search/"
TEKSTOWO_SEARCH_URL = "https://www.tekstowo.pl/szukaj"
MUSIXMATCH_SEARCH_URL = "https://www.musixmatch.com/search"
LYRICS_COM_SEARCH_URL = "https://www.lyrics.com/serp.php"
YOUTUBE_MUSIC_SEARCH_URL = "https://music.youtube.com/search"
AMAZON_MUSIC_SEARCH_URL = "https://music.amazon.com/search"
DEEZER_SEARCH_URL = "https://www.deezer.com/search"
TIDAL_SEARCH_URL = "https://tidal.com/search"
TARGET_INPUT_ERROR = f"Invalid Spotify target. Use {SPOTIFY_WEB_BASE_URL}/user/USER_ID, spotify:user:USER_ID or a Spotify user ID."
PLAYLIST_INPUT_ERROR = f"Invalid Spotify playlist. Use {SPOTIFY_WEB_BASE_URL}/playlist/PLAYLIST_ID, spotify:playlist:PLAYLIST_ID or a Spotify playlist ID."

# Object types that can appear as a whole path segment in a Spotify link or as the middle field of a Spotify URI
SPOTIFY_OBJECT_TYPES = frozenset({"user", "artist", "track", "album", "playlist"})

# Stable machine-readable categories used by recovery output and Doctor checks
RECOVERY_CODES = frozenset({"config.missing", "config.invalid", "dependency.missing", "secret.missing", "auth.cookie_invalid", "auth.client_invalid", "auth.oauth_invalid", "auth.rejected", "network.unavailable", "network.timeout", "spotify.rate_limited", "spotify.unavailable", "target.invalid", "target.not_found", "smtp.invalid", "smtp.authentication", "smtp.connection", "webhook.invalid", "webhook.rejected", "webhook.redirected", "webhook.rate_limited", "webhook.connection", "file.unreadable", "file.unwritable", "unknown"})

# Strings removed from track names for generating proper Genius search URLs
re_search_str = r'remaster|extended|original mix|remix|original soundtrack|radio( |-)edit|\(feat\.|( \(.*version\))|( - .*version)'
re_replace_str = r'( - (\d*)( )*remaster$)|( - (\d*)( )*remastered( version)*( \d*)*.*$)|( \((\d*)( )*remaster\)$)|( - (\d+) - remaster$)|( - extended$)|( - extended mix$)|( - (.*); extended mix$)|( - extended version$)|( - (.*) remix$)|( - remix$)|( - remixed by .*$)|( - original mix$)|( - .*original soundtrack$)|( - .*radio( |-)edit$)|( \(feat\. .*\)$)|( \(\d+.*Remaster.*\)$)|( \(.*Version\))|( - .*version)'

# Default value for network-related timeouts in functions; in seconds
FUNCTION_TIMEOUT = 15

# Enclosing main-loop watchdog timeout; in seconds
# This is a backstop for the rare case where a per-request timeout does not fire. It must stay larger than a
# single request's own alarm (FUNCTION_TIMEOUT + 2) so a nested request alarm never pre-empts legitimate work
ALARM_TIMEOUT = 2 * (FUNCTION_TIMEOUT + 2) + 5
ALARM_RETRY = 10

# Variables for caching functionality of the Spotify 'cookie' access token / 'client' refresh token to avoid unnecessary refreshing
SP_CACHED_ACCESS_TOKEN = None
SP_CACHED_REFRESH_TOKEN = None
SP_ACCESS_TOKEN_EXPIRES_AT = 0
SP_CACHED_CLIENT_ID = ""

# Separate cache for OAuth app access token (Client Credentials Flow) used in legacy fallback mode
SP_CACHED_OAUTH_APP_TOKEN = None

# Separate cache for the anonymous web-player token used by the public playlist backend
SP_CACHED_WEB_ACCESS_TOKEN = None
SP_WEB_ACCESS_TOKEN_EXPIRES_AT = 0
SP_CACHED_WEB_CLIENT_ID = ""

# Cache for the current playlist GraphQL persisted-query hash and normalized revisions
SP_CACHED_PLAYLIST_QUERY_HASH = ""
WEB_PLAYLIST_REVISION_CACHE = {}

# Switches remaining playlist requests to the web backend after a restricted Web API response
SP_WEB_PLAYLIST_BACKEND_PREFERRED = False

# Counts consecutive legacy Web API failures before latching the web backend
SP_WEB_PLAYLIST_API_FAILURES = 0

# Number of consecutive non-restricted legacy Web API failures tolerated before preferring the web backend
METADATA_API_FAILURE_LATCH_THRESHOLD = 3

# URL of the Spotify Web Player endpoint to get access token
TOKEN_URL = SPOTIFY_WEB_BASE_URL + "/api/token"

# URLs and page size used by the public web-player playlist backend
WEB_PLAYER_URL = SPOTIFY_WEB_LOGIN_URL
WEB_PLAYER_QUERY_URL = SPOTIFY_PARTNER_BASE_URL + "/pathfinder/v2/query"
WEB_PLAYLIST_PAGE_LIMIT = 100
WEB_PLAYER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

# URL of the endpoint to get server time needed to create TOTP object
SERVER_TIME_URL = SPOTIFY_WEB_LOGIN_URL

# Variables for caching functionality of the Spotify client token to avoid unnecessary refreshing
SP_CACHED_CLIENT_TOKEN = None
SP_CLIENT_TOKEN_EXPIRES_AT = 0

# Cache for playlist info to avoid redundant API calls
PLAYLIST_INFO_CACHE = {}

# Cache TTL for playlist info
PLAYLIST_INFO_CACHE_TTL = (SPOTIFY_CHECK_INTERVAL * 2 if SPOTIFY_CHECK_INTERVAL > 43200 else 43200)  # 12h

# Tracks temporarily glitched playlists to suppress false alerts
GLITCH_CACHE = {}

# Tracks transient collaborator glitches to suppress false alerts
COLLABORATORS_BASELINE_CACHE = {}
COLLABORATORS_PENDING_CACHE = {}

# Tracks transient playlists glitches to suppress false alerts
PLAYLISTS_BASELINE_CACHE = {}
PLAYLISTS_PENDING_CACHE = {}

LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / SPOTIFY_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Type', 'Name', 'Old', 'New']
csvfieldnames_export = ['Date', 'Playlist Name', 'Artist', 'Track']

imgcat_exe = ""

CLI_CONFIG_PATH = None

# To solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"

STARTUP_BANNER = r"""
 .---------------.    ____              _   _  __
| .-----.  ----  |   / ___| _ __   ___ | |_(_)/ _|_   _
| |  o o  | ---- |   \___ \| '_ \ / _ \| __| | |_| | | |
| |   -   | -))) |    ___) | |_) | (_) | |_| |  _| |_| |
|  '-----'   ))) |   |____/| .__/ \___/ \__|_|_|  \__, |
 '---------------'         |_|                    |___/
                      ____             __ _ _
                     |  _ \ _ __ ___  / _(_) | ___
                     | |_) | '__/ _ \| |_| | |/ _ \
                     |  __/| | | (_) |  _| | |  __/
                     |_|   |_|  \___/|_| |_|_|\___|
                      __  __             _ _
                     |  \/  | ___  _ __ (_) |_ ___  _ __
                     | |\/| |/ _ \| '_ \| | __/ _ \| '__|
                     | |  | | (_) | | | | | || (_) | |
                     |_|  |_|\___/|_| |_|_|\__\___/|_|"""

import sys

if sys.version_info < (3, 9):
    print("* Error: Python version 3.9 or higher required !")
    sys.exit(1)

import time
import string
import textwrap
import json
import os
from datetime import datetime, timezone, timedelta
from dateutil import relativedelta
from dateutil.parser import isoparse
import calendar
import requests as req
import shutil
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import argparse
import ast
import csv
import getpass
import subprocess
try:
    import pytz
except ModuleNotFoundError:
    pytz_install_command = subprocess.list2cmdline([sys.executable, "-m", "pip", "install", "pytz"])
    raise SystemExit(f"Error: Couldn't find the pytz library !\n\nTo install it through the active Python environment, run:\n    {pytz_install_command}\n\nOnce installed, re-run this tool")
try:
    from tzlocal import get_localzone
except ImportError:
    get_localzone = None
import platform
import html
from urllib.parse import quote_plus, quote, unquote, urljoin, urlparse, urlsplit
import re
import ipaddress
from itertools import zip_longest
from html import escape
import base64
import random
import shlex
import tempfile
import sqlite3
import configparser
import importlib
import importlib.util
from collections import Counter
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path, PureWindowsPath
import secrets
import socket
from typing import Any, Callable, Collection, Dict, FrozenSet, List, Optional, Sequence, Tuple, Type, cast
from email.utils import parsedate_to_datetime

import urllib3
if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SESSION = req.Session()
WEBHOOK_SESSION = req.Session()

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Cap server-provided Retry-After to avoid long blocking sleeps on 429 responses
MAX_RETRY_AFTER_SECONDS = 60

# Keep webhook delivery independent from Spotify API retries and long server timers
WEBHOOK_MAX_ATTEMPTS = 2
WEBHOOK_MAX_RETRY_AFTER_SECONDS = 5.0
WEBHOOK_FALLBACK_RETRY_SECONDS = 1.0
WEBHOOK_TIMEOUT_SECONDS = 10
WEBHOOK_EMBED_TITLE_LIMIT = 256
WEBHOOK_EMBED_DESCRIPTION_LIMIT = 4096
NTFY_MESSAGE_LIMIT_BYTES = 4095
NTFY_TRUNCATION_SUFFIX = "\n\n[Notification truncated to fit ntfy's 4 KB message limit]"
NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES = 5 * 1024 * 1024
NOTIFICATION_IMAGE_DOWNLOAD_CHUNK_BYTES = 64 * 1024
NOTIFICATION_IMAGE_PIXEL_LIMIT = 25_000_000
NTFY_IMAGE_FILENAME = "spotify-profile.jpg"
# Spotify serves images from its own CDN and, for accounts linked to Facebook, from Facebook's CDN.
# Measured against the live profile API: 51.6% of profile pictures are on scdn.co, 48.4% on fbcdn.net or fbsbx.com
SPOTIFY_IMAGE_ALLOWED_HOST_SUFFIXES = ("scdn.co", "spotifycdn.com", "fbcdn.net", "fbsbx.com")

# Every endpoint that receives the Spotify bearer token lives under this suffix (api, api-partner, spclient, open, login5)
SPOTIFY_CREDENTIALED_HOST_SUFFIXES = ("spotify.com",)

# A playlist tops out at 10000 tracks and a page holds 100, so this ceiling is far above any legitimate pagination run
SPOTIFY_PAGINATION_MAX_PAGES = 1000
EMAIL_ARTWORK_CONTENT_ID = "spotify_artwork"
EMAIL_ARTWORK_MAX_DIMENSIONS = (320, 320)

PILImage: Any = None
try:
    from PIL import Image as PILImageModule
    PILImage = PILImageModule
except ImportError:
    pass
NOTIFICATION_IMAGES_AVAILABLE = PILImage is not None


# Stores one stable recovery category with secret-safe user guidance
@dataclass(frozen=True)
class RecoveryAdvice:
    code: str
    summary: str
    fix: str
    retryable: bool
    detail: str = ""


# Carries structured recovery guidance through exception boundaries
class RecoveryError(Exception):
    # Initializes a recovery exception without exposing its technical cause
    def __init__(self, advice: RecoveryAdvice, cause: Optional[BaseException] = None):
        self.advice = advice
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause
        super().__init__(advice.summary)


# Suppresses repeated recovery hints until a successful operation resets the category
@dataclass
class RecoveryHintTracker:
    last_code: Optional[str] = None

    # Returns whether the current recovery category needs a new fix hint
    def should_render(self, advice: RecoveryAdvice) -> bool:
        if advice.code == self.last_code:
            return False
        self.last_code = advice.code
        return True

    # Clears recovery hint suppression after a successful operation
    def reset(self) -> None:
        self.last_code = None


class CappedRetry(Retry):
    def get_retry_after(self, response):
        retry_after = super().get_retry_after(response)
        if retry_after is None:
            return None
        return min(retry_after, MAX_RETRY_AFTER_SECONDS)


retry = CappedRetry(
    total=5,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD", "OPTIONS"],
    raise_on_status=False,
    respect_retry_after_header=True
)

adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
SESSION.mount("https://", adapter)
SESSION.mount("http://", adapter)

# The web-player GraphQL endpoint is queried through idempotent read-only POSTs, so it gets a dedicated
# adapter that also retries POST on transient failures (other POSTs use the bare requests module, not SESSION)
web_player_retry = CappedRetry(
    total=5,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD", "OPTIONS", "POST"],
    raise_on_status=False,
    respect_retry_after_header=True
)

web_player_adapter = HTTPAdapter(max_retries=web_player_retry, pool_connections=100, pool_maxsize=100)
SESSION.mount(SPOTIFY_PARTNER_BASE_URL, web_player_adapter)


# Truncates each line of a string to a specified number of characters including tab expansion and multi-line support
def truncate_string_per_line(message, truncate_width, tabsize=8):
    try:
        from wcwidth import wcwidth
    except ImportError:
        return message

    lines = message.split('\n')
    truncated_lines = []

    for line in lines:
        expanded_line = line.expandtabs(tabsize)
        current_width = 0
        truncated = ''

        for char in expanded_line:
            char_width = wcwidth(char)
            if char_width < 0:
                char_width = 0  # Non-printable or unknown width
            if current_width + char_width > truncate_width:
                break
            truncated += char
            current_width += char_width

        truncated_lines.append(truncated)

    return '\n'.join(truncated_lines)


# Reports whether separator-only log lines should use ASCII on this system
def ascii_log_separators_enabled():
    mode = str(ASCII_LOG_SEPARATORS).strip().lower()
    if mode not in {"auto", "on", "off"}:
        raise ValueError("ASCII_LOG_SEPARATORS must be 'Auto', 'On' or 'Off'")
    return mode == "on" or (mode == "auto" and platform.system() == "Windows")


# Converts Unicode-only horizontal separator lines to ASCII when configured
def normalize_log_separators(message):
    if not ascii_log_separators_enabled():
        return message
    return re.sub(r"(?m)^─+$", lambda match: match.group(0).replace("─", "-"), message)


# Every control character is dropped, keeping only tab and newline. A carriage return would let Spotify-supplied
# text overwrite an already printed line, and the inline progress bars that use one write to the terminal directly
TERMINAL_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


# Removes terminal control sequences that Spotify-supplied text could use to drive the terminal or the log file
def sanitize_terminal_text(message):
    if not isinstance(message, str) or not message:
        return message
    return TERMINAL_CONTROL_RE.sub("", message)


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        message = sanitize_terminal_text(message)
        # Expand tabs for file output (stdout remains untouched)
        self.logfile.write(normalize_log_separators(message.expandtabs(8)))
        if (TRUNCATE_CHARS):
            message = truncate_string_per_line(message, TRUNCATE_CHARS)
        self.terminal.write(message)
        self.terminal.flush()
        self.logfile.flush()

    # Writes one message to the terminal without duplicating it in the log
    def terminal_only(self, message):
        message = sanitize_terminal_text(message)
        if TRUNCATE_CHARS:
            message = truncate_string_per_line(message, TRUNCATE_CHARS)
        self.terminal.write(message)
        self.terminal.flush()

    # Writes one message to the complete log without showing it in the terminal
    def log_only(self, message):
        self.logfile.write(normalize_log_separators(sanitize_terminal_text(message).expandtabs(8)))
        self.logfile.flush()

    # Flushes both output destinations
    def flush(self):
        self.terminal.flush()
        self.logfile.flush()


# Sanitizing stdout wrapper used when file logging is disabled, mirroring the Logger interface
class TerminalStream(object):
    def __init__(self, stream):
        self.terminal = stream

    def write(self, message):
        self.terminal.write(sanitize_terminal_text(message))
        self.terminal.flush()

    # Writes one message to the terminal, matching the Logger interface
    def terminal_only(self, message):
        self.write(message)

    # Discards log-only output since no log file exists in this mode, matching the Logger interface
    def log_only(self, message):
        return

    # Flushes the wrapped terminal
    def flush(self):
        self.terminal.flush()

    # Forwards every remaining stream attribute (isatty, buffer, encoding, fileno) to the wrapped terminal
    def __getattr__(self, name):
        return getattr(self.terminal, name)


# Class used to generate timeout exceptions
class TimeoutException(Exception):
    pass


# Class used for custom PlaylistRestrictedError exception
class PlaylistRestrictedError(Exception):
    pass


# Signal handler for SIGALRM when the operation times out
def timeout_handler(sig, frame):
    raise TimeoutException


# Starts a POSIX alarm without discarding an earlier enclosing deadline
def _start_timeout_alarm(timeout: float):
    if platform.system() == "Windows" or not hasattr(signal, "setitimer"):
        return None
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_delay, previous_interval = signal.getitimer(signal.ITIMER_REAL)
    effective_timeout = min(float(timeout), previous_delay) if previous_delay > 0 else float(timeout)
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, effective_timeout)
    return previous_handler, previous_delay, previous_interval, time.monotonic()


# Restores the enclosing POSIX alarm with its elapsed time deducted
def _restore_timeout_alarm(alarm_state) -> None:
    if alarm_state is None:
        return
    previous_handler, previous_delay, previous_interval, started_at = alarm_state
    elapsed = max(0.0, time.monotonic() - started_at)
    signal.signal(signal.SIGALRM, previous_handler)
    if previous_delay > 0:
        signal.setitimer(signal.ITIMER_REAL, max(previous_delay - elapsed, 0.000001), previous_interval)
    else:
        signal.setitimer(signal.ITIMER_REAL, 0, previous_interval)


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)


# Checks internet connectivity
def check_internet(url=None, timeout=None, verify=None):
    # Resolve at call time so config file and dotenv overrides take effect (these globals change after import)
    url = CHECK_INTERNET_URL if url is None else url
    timeout = CHECK_INTERNET_TIMEOUT if timeout is None else timeout
    verify = VERIFY_SSL if verify is None else verify
    try:
        debug_print(f"HTTP GET {url} [connectivity check], timeout={timeout}, verify_ssl={verify}")
        _ = req.get(url, headers={'User-Agent': USER_AGENT}, timeout=timeout, verify=verify)
        debug_print(f"HTTP GET {url} -> OK")
        return True
    except req.RequestException as e:
        debug_print(f"HTTP GET {url} -> failed: {sanitize_error_text(e)}")
        print_recovery_error(e, "runtime")
        return False


# Clears the terminal screen
def clear_screen(enabled=True):
    if not enabled:
        return
    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        print("* Cannot clear the screen contents")


# Prepares a clean screen for interactive full-screen startup flows
def prepare_startup_screen(require_input=False):
    input_is_interactive = not require_input or sys.stdin.isatty()
    clear_screen(bool(CLEAR_SCREEN and input_is_interactive and sys.stdout.isatty()))


# Prints the ASCII startup banner with its separately aligned version
def print_startup_banner() -> None:
    print(STARTUP_BANNER)
    print(f"{'':21}v{VERSION}\n")


# Debug print helper - only prints when DEBUG_MODE is enabled
def debug_print(message):
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[DEBUG {timestamp}] {message}")


# Prints one sanitized operational event only when verbose mode is enabled
def verbose_print(message: Any) -> None:
    if VERBOSE_MODE:
        print(f"* {sanitize_error_text(message)}")


# Masks one secret while retaining small optional edge fragments
def mask_secret(value, prefix=4, suffix=2):
    if value is None:
        return None
    s = str(value)
    if not s:
        return ""
    if len(s) <= (prefix + suffix):
        return "*" * len(s)
    return f"{s[:prefix]}...{s[-suffix:]}"


# Redacts sensitive request parameters before debug output
def sanitize_debug_params(params):
    if not isinstance(params, dict):
        return params
    redacted_keys = {"totp", "totpServer", "refresh_token", "access_token"}
    out = {}
    for k, v in params.items():
        if k in redacted_keys:
            out[k] = mask_secret(v)
        else:
            out[k] = v
    return out


# Redacts sensitive request headers before debug output
def sanitize_debug_headers(headers):
    if not isinstance(headers, dict):
        return headers
    sensitive = {"authorization", "cookie", "client-token"}
    out = {}
    for k, v in headers.items():
        if str(k).lower() in sensitive:
            out[k] = mask_secret(v)
        else:
            out[k] = v
    return out


# Returns all complete secret values currently known to the process
def known_secret_values(extra_values: Sequence[Any] = ()) -> List[str]:
    values = []
    for key in SECRET_KEYS:
        value = globals().get(key)
        if isinstance(value, str) and value and not value.startswith("your_"):
            values.append(value)
    webhook_headers = globals().get("WEBHOOK_HEADERS")
    if isinstance(webhook_headers, dict):
        for key, value in webhook_headers.items():
            if isinstance(key, str) and key.casefold() == "authorization" and isinstance(value, str) and value:
                values.append(value)
    for key in ("SP_CACHED_ACCESS_TOKEN", "SP_CACHED_REFRESH_TOKEN", "SP_CACHED_CLIENT_TOKEN", "SP_CACHED_OAUTH_APP_TOKEN", "SP_CACHED_WEB_ACCESS_TOKEN"):
        value = globals().get(key)
        if isinstance(value, str) and value:
            values.append(value)
    for value in extra_values:
        if isinstance(value, str) and value:
            values.append(value)
    return sorted(set(values), key=len, reverse=True)


# Redacts credentials and serialized secret fields from arbitrary error text
def sanitize_error_text(value: Any, extra_secrets: Sequence[Any] = ()) -> str:
    text = str(value or "")
    for secret in known_secret_values(extra_secrets):
        text = text.replace(secret, "<redacted>")
    patterns = (
        (r"(?m)(\b(?:SP_DC_COOKIE|REFRESH_TOKEN|SP_APP_CLIENT_ID|SP_APP_CLIENT_SECRET|SP_USER_CLIENT_ID|SP_USER_CLIENT_SECRET|SP_SHA256|SMTP_PASSWORD|WEBHOOK_URL|NTFY_ACCESS_TOKEN)\b\s*=\s*).*$", r"\1<redacted>"),
        (r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?bearer\s+)[^\s,;'\"}]+", r"\1<redacted>"),
        (r"(?i)(cookie\s*[:=][^\r\n]*?sp_dc\s*=\s*)[^\s;,;'\"}]+", r"\1<redacted>"),
        (r"(?i)(\bsp_dc\s*=\s*)[^\s;,;'\"}]+", r"\1<redacted>"),
        (r"(?i)(['\"]?(?:access_token|refresh_token|client-token|client_token|smtp_password|webhook_url|ntfy_access_token)['\"]?\s*[:=]\s*['\"]?)[^\s,;'\"}]+", r"\1<redacted>"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


# Extracts an HTTP status code from a requests-style exception or response
def recovery_http_status(error: Any) -> Optional[int]:
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if status is None:
        status = getattr(error, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


# Creates one validated secret-safe recovery advice value
def make_recovery_advice(code: str, summary: str, fix: str, retryable: bool, detail: Any = "") -> RecoveryAdvice:
    if code not in RECOVERY_CODES:
        raise ValueError(f"Unsupported recovery code: {code}")
    return RecoveryAdvice(code, sanitize_error_text(summary), sanitize_error_text(fix), retryable, sanitize_error_text(detail))


# Adds one directly relevant documentation link to recovery instructions
def recovery_fix_with_guide(fix: str, guide_url: str) -> str:
    return f"{fix}\nGuide: {guide_url}"


# Returns an install-aware Firefox cookie recovery command
def cookie_auth_recovery_fix() -> str:
    command = _wizard_action_command(_wizard_install_method(), "--import-browser-cookie --browser firefox", CLI_CONFIG_PATH, DOTENV_FILE or None)
    return f"Open {SPOTIFY_WEB_LOGIN_URL} in Firefox. Sign in to the Spotify account used for monitoring then run: {command}"


# Builds a directly usable Spotify profile URL from a normalized user ID
def spotify_user_profile_url(user_id: str) -> str:
    return f"{SPOTIFY_WEB_BASE_URL}/user/{quote(user_id, safe='')}"


# Classifies a failure into stable user-facing recovery guidance
def classify_recovery_error(error: Any = None, context: str = "runtime", detail: Any = "", target_user_id: Optional[str] = None) -> RecoveryAdvice:
    if isinstance(error, RecoveryError):
        return error.advice
    safe_detail = sanitize_error_text(detail or error)
    message = str(detail or error or "").casefold()
    status = recovery_http_status(error)

    if context == "browser_import":
        if any(term in message for term in ("network", "connectivity", "timeout", "timed out", "name resolution", "dns", "proxy", "ssl")):
            return make_recovery_advice("network.unavailable", safe_detail or "Browser cookie validation could not reach Spotify", recovery_fix_with_guide("Check connectivity then retry browser import", BROWSER_COOKIE_GUIDE_URL), True, safe_detail)
        if any(term in message for term in ("invalid or expired", "authentication rejected", "no sp_dc", "nonempty sp_dc")):
            return make_recovery_advice("auth.cookie_invalid", safe_detail or "No valid sp_dc cookie was found", recovery_fix_with_guide(cookie_auth_recovery_fix(), BROWSER_COOKIE_GUIDE_URL), False, safe_detail)
        if any(term in message for term in ("database", "cookie file", "cookies.sqlite", "could not read")):
            return make_recovery_advice("file.unreadable", safe_detail or "The browser cookie database could not be read", recovery_fix_with_guide("Close the browser, verify the selected profile or cookie database path then retry", BROWSER_COOKIE_GUIDE_URL), False, safe_detail)
        if any(term in message for term in ("update dotenv", "dotenv destination", "file permissions")):
            return make_recovery_advice("file.unwritable", safe_detail or "The dotenv destination could not be updated", "Choose a writable --env-file path then retry", False, safe_detail)
        return make_recovery_advice("unknown", safe_detail or "Browser cookie import failed", recovery_fix_with_guide(cookie_auth_recovery_fix(), BROWSER_COOKIE_GUIDE_URL), False, safe_detail)

    if context == "set_sp_dc":
        if "interactive terminal" in message:
            return make_recovery_advice("secret.missing", "--set-sp-dc requires an interactive terminal", "Run --set-sp-dc from an interactive shell so the cookie remains hidden", False, safe_detail)
        if any(term in message for term in ("network", "connectivity", "timeout", "timed out", "name resolution")):
            return make_recovery_advice("network.unavailable", "Spotify cookie validation could not reach Spotify", recovery_fix_with_guide("Check connectivity then run the private entry command again", MANUAL_COOKIE_GUIDE_URL), True, safe_detail)
        if any(term in message for term in ("invalid or expired", "authentication rejected", "no nonempty", "rejected")):
            return make_recovery_advice("auth.cookie_invalid", "Spotify rejected the entered sp_dc cookie", recovery_fix_with_guide("Sign in to Spotify Web Player then run the private entry command again", MANUAL_COOKIE_GUIDE_URL), False, safe_detail)
        if any(term in message for term in ("dotenv", "file permissions", "writable path")):
            return make_recovery_advice("file.unwritable", "The dotenv destination could not be updated", "Choose a writable --env-file path then retry", False, safe_detail)
        return make_recovery_advice("unknown", "SP_DC_COOKIE was not changed", recovery_fix_with_guide("Run --set-sp-dc again or use Firefox import", MANUAL_COOKIE_GUIDE_URL), False, safe_detail)

    if context == "set_webhook_url":
        if "interactive terminal" in message:
            return make_recovery_advice("webhook.invalid", "--set-webhook-url requires an interactive terminal", "Run --set-webhook-url in a terminal so the destination remains hidden", False, safe_detail)
        if any(term in message for term in ("dotenv", "file permissions", "writable path")):
            return make_recovery_advice("file.unwritable", "The webhook URL could not be saved", "Check file permissions or choose another --env-file path", False, safe_detail)
        return make_recovery_advice("webhook.invalid", "The webhook URL was not changed", recovery_fix_with_guide("Copy a fresh Discord or ntfy destination then run --set-webhook-url again", WEBHOOK_GUIDE_URL), False, safe_detail)

    if context == "config_missing":
        return make_recovery_advice("config.missing", "The requested configuration file was not found", recovery_fix_with_guide("Verify the --config-file path or generate a new config at that path", CONFIG_GUIDE_URL), False, safe_detail)
    if context == "config_invalid":
        return make_recovery_advice("config.invalid", "The configuration file could not be loaded", recovery_fix_with_guide("Correct the reported line or generate a fresh config then retry", CONFIG_GUIDE_URL), False, safe_detail)
    if context == "dependency":
        dependency = getattr(error, "name", None) or safe_detail or "required package"
        return make_recovery_advice("dependency.missing", f"A required dependency is missing: {dependency}", recovery_fix_with_guide("Install the project requirements then retry", INSTALLATION_GUIDE_URL), False, safe_detail)
    if context == "secret":
        return make_recovery_advice("secret.missing", safe_detail or "A required secret is missing", recovery_fix_with_guide("Provide the secret through a dotenv file, environment variable or supported private setup command", SECRETS_GUIDE_URL), False, safe_detail)
    if context == "target_missing":
        return make_recovery_advice("target.invalid", "No Spotify target was provided", recovery_fix_with_guide("Provide a Spotify profile URL, spotify:user URI or user ID or set TARGET_USER_URI_ID", QUICK_START_GUIDE_URL), False)
    if context == "target_invalid":
        return make_recovery_advice("target.invalid", "Invalid Spotify target", recovery_fix_with_guide("Pass a Spotify profile URL, spotify:user:USER_ID URI or user ID", TARGET_GUIDE_URL), False, safe_detail)
    if context == "target" and (status == 403 or "cannot monitor user" in message):
        return make_recovery_advice("auth.rejected", "The selected authentication mode cannot load this profile", recovery_fix_with_guide("Use cookie or client authentication for another user's profile then run Doctor again", COOKIE_GUIDE_URL), False, safe_detail)
    if context == "target_not_found":
        fix = "Check the target ID or profile URL then retry"
        if target_user_id:
            fix = f"Open this profile and confirm it still exists and is public enough for the selected authentication mode:\nProfile: {spotify_user_profile_url(target_user_id)}"
        return make_recovery_advice("target.not_found", "The Spotify target could not be loaded", recovery_fix_with_guide(fix, TARGET_GUIDE_URL), False, safe_detail)
    if context == "file_read":
        return make_recovery_advice("file.unreadable", "A required file could not be read", "Verify the path, file format and read permissions then retry", False, safe_detail)
    if context == "file_write":
        return make_recovery_advice("file.unwritable", "An output destination is not writable", "Choose a writable path and verify its parent directory permissions then retry", False, safe_detail)
    if context == "smtp_config":
        return make_recovery_advice("smtp.invalid", "The SMTP configuration is incomplete or invalid", recovery_fix_with_guide("Correct SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL and RECEIVER_EMAIL then run --send-test-email", SMTP_GUIDE_URL), False, safe_detail)
    if context == "webhook_config":
        return make_recovery_advice("webhook.invalid", "The webhook configuration is invalid", recovery_fix_with_guide("Check the provider, URL, template, headers and ntfy access token then run --send-test-webhook", WEBHOOK_GUIDE_URL), False, safe_detail)

    if context.startswith("webhook"):
        if status == 429 or any(term in message for term in ("429", "too many requests", "rate limit")):
            return make_recovery_advice("webhook.rate_limited", "The webhook service is temporarily limiting messages", recovery_fix_with_guide("Wait briefly then run --send-test-webhook", WEBHOOK_GUIDE_URL), True, safe_detail)
        if status is not None and 300 <= status <= 399:
            return make_recovery_advice("webhook.redirected", "The webhook destination redirected the alert", recovery_fix_with_guide("Redirects are not followed, so custom headers and alert content cannot reach another host. Save the final destination with --set-webhook-url then run --send-test-webhook", WEBHOOK_GUIDE_URL), False, safe_detail)
        if status is not None and 400 <= status <= 499:
            return make_recovery_advice("webhook.rejected", "The webhook service did not accept the alert", recovery_fix_with_guide("Check that WEBHOOK_PROVIDER matches the saved destination then run --send-test-webhook", WEBHOOK_GUIDE_URL), False, safe_detail)
        return make_recovery_advice("webhook.connection", "The webhook alert could not be sent", recovery_fix_with_guide("Check connectivity then run --send-test-webhook. Retry with --debug if it still fails", WEBHOOK_GUIDE_URL), True, safe_detail)

    if isinstance(error, smtplib.SMTPAuthenticationError) or status == 535:
        return make_recovery_advice("smtp.authentication", "SMTP authentication was rejected", recovery_fix_with_guide("Verify SMTP_USER and SMTP_PASSWORD then run --send-test-email", SMTP_GUIDE_URL), False, safe_detail)
    if isinstance(error, (smtplib.SMTPException, ConnectionError)) and context.startswith("smtp"):
        return make_recovery_advice("smtp.connection", "The SMTP server connection failed", recovery_fix_with_guide("Verify SMTP_HOST, SMTP_PORT and SMTP_SSL then run --send-test-email", SMTP_GUIDE_URL), True, safe_detail)
    if isinstance(error, (req.Timeout, TimeoutException, socket.timeout)) or "timed out" in message or " timeout" in message:
        if context.startswith("smtp"):
            return make_recovery_advice("smtp.connection", "The SMTP connection timed out", recovery_fix_with_guide("Verify SMTP_HOST, SMTP_PORT and network access then run --send-test-email", SMTP_GUIDE_URL), True, safe_detail)
        return make_recovery_advice("network.timeout", "The Spotify request timed out", "Check connectivity and retry. Run --doctor --debug if timeouts continue", True, safe_detail)
    if isinstance(error, req.exceptions.SSLError) or any(term in message for term in ("certificate verify failed", "tls", "ssl error")):
        return make_recovery_advice("network.unavailable", "A secure connection could not be established", "Check the system clock, CA certificates, firewall and TLS-inspecting proxy settings then retry", True, safe_detail)
    if isinstance(error, (req.ConnectionError, socket.gaierror)) or any(term in message for term in ("name resolution", "failed to resolve", "network is unreachable", "connection refused", "connection aborted", "max retries exceeded")):
        return make_recovery_advice("network.unavailable", "Spotify could not be reached", "Check DNS, internet access, firewall and proxy settings then retry", True, safe_detail)
    if status == 429 or any(term in message for term in ("429", "too many requests", "rate limit")):
        return make_recovery_advice("spotify.rate_limited", "Spotify is rate limiting requests", recovery_fix_with_guide("Wait before retrying and increase --check-interval if this repeats", INTERVALS_GUIDE_URL), True, safe_detail)
    if (status is not None and 500 <= status <= 599) or any(term in message for term in ("500 server", "502 server", "503 server", "504 server")):
        return make_recovery_advice("spotify.unavailable", "Spotify is temporarily unavailable", "Wait and retry later. Run --doctor if the failure continues", True, safe_detail)
    if status == 404 or "not found" in message:
        return classify_recovery_error(error, "target_not_found", safe_detail, target_user_id)
    if status == 401 or "401 unauthorized" in message or "unauthorized" in message:
        if context.startswith("cookie"):
            return make_recovery_advice("auth.cookie_invalid", "Spotify rejected the sp_dc cookie", recovery_fix_with_guide(cookie_auth_recovery_fix(), COOKIE_GUIDE_URL), False, safe_detail)
        if context.startswith("client"):
            return make_recovery_advice("auth.client_invalid", "Spotify rejected the desktop client credentials", recovery_fix_with_guide("Re-export the Spotify Desktop Client login request", CLIENT_GUIDE_URL), False, safe_detail)
        if context.startswith("oauth"):
            guide = OAUTH_USER_GUIDE_URL if "user" in context else OAUTH_GUIDE_URL
            fix = f"Verify the app credentials and authorize again if required\nDashboard: {SPOTIFY_DEVELOPER_DASHBOARD_URL}\nSpotify app guide: {SPOTIFY_APPS_GUIDE_URL}"
            return make_recovery_advice("auth.oauth_invalid", "Spotify rejected the OAuth credentials", recovery_fix_with_guide(fix, guide), False, safe_detail)
        return make_recovery_advice("auth.rejected", "Spotify rejected authentication", "Refresh the configured credentials then run --doctor", False, safe_detail)
    if status == 403 and context == "metadata":
        return make_recovery_advice("spotify.unavailable", "The legacy Spotify metadata path is restricted", recovery_fix_with_guide("Remove the optional OAuth credentials to use the automatic web-player fallback or verify the existing app", OAUTH_GUIDE_URL), False, safe_detail)
    if context.startswith("cookie") and any(term in message for term in ("sp_dc", "unsuccessful token request", "valid spotify access token", "access token after")):
        return make_recovery_advice("auth.cookie_invalid", "The sp_dc cookie is invalid, expired or was rejected", recovery_fix_with_guide(cookie_auth_recovery_fix(), COOKIE_GUIDE_URL), False, safe_detail)
    if context.startswith("client") and any(term in message for term in ("refresh token", "client token", "invalid grant", "access token not found")):
        return make_recovery_advice("auth.client_invalid", "The Spotify desktop client credentials are invalid or expired", recovery_fix_with_guide("Re-export the relevant Spotify Desktop Client request", CLIENT_GUIDE_URL), False, safe_detail)
    if context.startswith("oauth") and any(term in message for term in ("invalid_client", "invalid_grant", "authorization_required", "refresh token")):
        guide = OAUTH_USER_GUIDE_URL if "user" in context else OAUTH_GUIDE_URL
        fix = f"Verify the app credentials and authorize again\nDashboard: {SPOTIFY_DEVELOPER_DASHBOARD_URL}\nSpotify app guide: {SPOTIFY_APPS_GUIDE_URL}"
        return make_recovery_advice("auth.oauth_invalid", "The Spotify OAuth credentials are invalid or require authorization", recovery_fix_with_guide(fix, guide), False, safe_detail)
    if isinstance(error, ModuleNotFoundError):
        return classify_recovery_error(error, "dependency", safe_detail)
    if isinstance(error, FileNotFoundError):
        return classify_recovery_error(error, "file_read", safe_detail)
    return make_recovery_advice("unknown", "An unexpected error occurred", recovery_fix_with_guide("Run --doctor. If the issue continues retry with --debug", DOCTOR_GUIDE_URL), True, safe_detail)


# Renders one structured recovery error with technical detail limited to debug mode
def render_recovery_error(error: Any = None, context: str = "runtime", debug: Optional[bool] = None, detail: Any = "") -> str:
    advice = classify_recovery_error(error, context, detail)
    lines = [f"* Error: {advice.summary}", f"To fix: {advice.fix}"]
    if (DEBUG_MODE if debug is None else debug) and advice.detail:
        lines.append(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return "\n".join(lines)


# Prints one structured recovery error and returns its stable advice
def print_recovery_error(error: Any = None, context: str = "runtime", debug: Optional[bool] = None, detail: Any = "", target_user_id: Optional[str] = None) -> RecoveryAdvice:
    advice = classify_recovery_error(error, context, detail, target_user_id)
    print(render_recovery_error(RecoveryError(advice), debug=debug))
    return advice


# Prints one recurring error while suppressing unchanged recovery instructions
def print_monitor_recovery(error: Any, context: str, tracker: RecoveryHintTracker, prefix: str) -> RecoveryAdvice:
    advice = classify_recovery_error(error, context)
    print(prefix + advice.summary)
    if tracker.should_render(advice):
        print(f"To fix: {advice.fix}")
        if DEBUG_MODE and advice.detail:
            print(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return advice


# Prints a concise operation failure with sanitized technical detail only in debug mode
def print_operation_error(summary: str, error: Any = None) -> None:
    print(f"* Error: {summary}")
    if DEBUG_MODE and error is not None:
        print(f"Technical detail: {sanitize_error_text(error)}")


# Converts absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952),  # approximation
        ('months', 2629746),  # approximation
        ('weeks', 604800),    # 60 * 60 * 24 * 7
        ('days', 86400),      # 60 * 60 * 24
        ('hours', 3600),      # 60 * 60
        ('minutes', 60),
        ('seconds', 1),
    )
    result = []

    if seconds > 0:
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append(f"{value} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Calculates time span between two timestamps, accepts timestamp integers, floats and datetime objects
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if isinstance(timestamp1, str):
        try:
            timestamp1 = isoparse(timestamp1)
        except Exception:
            return ""

    if isinstance(timestamp1, int):
        dt1 = datetime.fromtimestamp(int(ts1), tz=timezone.utc)
    elif isinstance(timestamp1, float):
        ts1 = int(round(ts1))
        dt1 = datetime.fromtimestamp(ts1, tz=timezone.utc)
    elif isinstance(timestamp1, datetime):
        dt1 = timestamp1
        if dt1.tzinfo is None:
            dt1 = pytz.utc.localize(dt1)
        else:
            dt1 = dt1.astimezone(pytz.utc)
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if isinstance(timestamp2, str):
        try:
            timestamp2 = isoparse(timestamp2)
        except Exception:
            return ""

    if isinstance(timestamp2, int):
        dt2 = datetime.fromtimestamp(int(ts2), tz=timezone.utc)
    elif isinstance(timestamp2, float):
        ts2 = int(round(ts2))
        dt2 = datetime.fromtimestamp(ts2, tz=timezone.utc)
    elif isinstance(timestamp2, datetime):
        dt2 = timestamp2
        if dt2.tzinfo is None:
            dt2 = pytz.utc.localize(dt2)
        else:
            dt2 = dt2.astimezone(pytz.utc)
        ts2 = int(round(dt2.timestamp()))
    else:
        return ""

    if ts1 >= ts2:
        ts_diff = ts1 - ts2
    else:
        ts_diff = ts2 - ts1
        dt1, dt2 = dt2, dt1

    if ts_diff > 0:
        date_diff = relativedelta.relativedelta(dt1, dt2)
        years = date_diff.years
        months = date_diff.months
        days_total = date_diff.days

        if show_weeks:
            weeks = days_total // 7
            days = days_total % 7
        else:
            weeks = 0
            days = days_total

        hours = date_diff.hours if show_hours or ts_diff <= 86400 else 0
        minutes = date_diff.minutes if show_minutes or ts_diff <= 3600 else 0
        seconds = date_diff.seconds if show_seconds or ts_diff <= 60 else 0

        date_list = [years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval > 0:
                name = intervals[index]
                if interval == 1:
                    name = name.rstrip('s')
                result.append(f"{interval} {name}")

        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Sends email notification
def send_email(subject, body, body_html, use_ssl, image_file="", image_name="image1", smtp_timeout=15, image_bytes=None):
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            print("Error sending email - SMTP settings are incorrect (invalid IP address/FQDN in SMTP_HOST)")
            return 1

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("Error sending email - SMTP settings are incorrect (invalid port number in SMTP_PORT)")
        return 1

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        print("Error sending email - SMTP settings are incorrect (invalid email in SENDER_EMAIL or RECEIVER_EMAIL)")
        return 1

    if not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password":
        print("Error sending email - SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD configuration options)")
        return 1

    if not subject or not isinstance(subject, str):
        print("Error sending email - SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    if not body and not body_html:
        print("Error sending email - SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
        return 1

    try:
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
        smtpObj.login(SMTP_USER, SMTP_PASSWORD)
        image_data = image_bytes
        if image_file:
            with open(image_file, 'rb') as fp:
                image_data = fp.read()
        email_msg = MIMEMultipart('related' if image_data else 'alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] = str(Header(subject, 'utf-8'))
        content_msg = MIMEMultipart('alternative') if image_data else email_msg
        if image_data:
            email_msg.attach(content_msg)

        if body:
            part1 = MIMEText(body, 'plain')
            part1 = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
            content_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            part2 = MIMEText(body_html.encode('utf-8'), 'html', _charset='utf-8')
            content_msg.attach(part2)

        if image_data:
            img_part = MIMEImage(image_data)
            img_part.add_header('Content-ID', f'<{image_name}>')
            email_msg.attach(img_part)

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtpObj.quit()
    except Exception as e:
        print_recovery_error(e, "smtp_connection")
        return 1
    return 0


# Returns whether a webhook URL is a complete private HTTPS link
def validate_webhook_url(url: Any = None) -> bool:
    selected_url = WEBHOOK_URL if url is None else url
    if not isinstance(selected_url, str) or not selected_url.strip():
        return False
    try:
        parsed = urlsplit(selected_url.strip())
    except ValueError:
        return False
    return parsed.scheme.casefold() == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and bool(parsed.path.strip("/"))


# Converts a complete ntfy URL or valid ntfy.sh topic into a complete HTTPS URL
def normalize_ntfy_topic_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if validate_webhook_url(normalized):
        return normalized
    if re.fullmatch(r"[-_A-Za-z0-9]{1,64}", normalized):
        return f"{NTFY_PUBLIC_BASE_URL}/{normalized}"
    return ""


# Returns the normalized configured webhook provider or an empty string when unsupported
def normalized_webhook_provider(provider: Any = None) -> str:
    selected_provider = WEBHOOK_PROVIDER if provider is None else provider
    if not isinstance(selected_provider, str):
        return ""
    normalized = selected_provider.strip().casefold()
    return normalized if normalized in ("discord", "ntfy") else ""


# Detects Discord and public ntfy webhook providers from distinctive URL shapes
def detect_webhook_provider(url: Any) -> str:
    if not validate_webhook_url(url):
        return ""
    try:
        parsed = urlsplit(str(url).strip())
    except ValueError:
        return ""
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    if hostname == "ntfy.sh":
        return "ntfy"
    discord_host = hostname in ("discord.com", "discordapp.com") or hostname.endswith(".discord.com") or hostname.endswith(".discordapp.com")
    discord_path = re.match(r"^/api(?:/v[0-9]+)?/webhooks/[0-9]+/[^/]+/?$", parsed.path) is not None
    return "discord" if discord_host and discord_path else ""


# Returns enabled email notification category names in display order
def _startup_email_notification_categories() -> List[str]:
    settings = (
        (PROFILE_NOTIFICATION, "profile"),
        (PROFILE_NOTIFICATION and FOLLOWERS_FOLLOWINGS_NOTIFICATION, "followers/followings"),
        (ERROR_NOTIFICATION, "errors"),
    )
    return [label for enabled, label in settings if enabled]


# Returns enabled webhook notification category names in display order
def _startup_webhook_notification_categories() -> List[str]:
    settings = (
        (WEBHOOK_PROFILE_NOTIFICATION, "profile"),
        (WEBHOOK_PROFILE_NOTIFICATION and WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION, "followers/followings"),
        (WEBHOOK_ERROR_NOTIFICATION, "errors"),
    )
    return [label for enabled, label in settings if WEBHOOK_ENABLED and enabled]


# Formats one notification row with unstarred continuation lines when needed
def _format_startup_notification_line(label: str, categories: List[str]) -> str:
    prefix = f"* {label:<30}"
    state = "On (" + ", ".join(categories) + ")" if categories else "Off"
    return textwrap.fill(state, width=100, initial_indent=prefix, subsequent_indent=" " * len(prefix), break_long_words=False, break_on_hyphens=False)


# Builds compact startup notification lines for both delivery channels
def _startup_notification_summary_lines() -> List[str]:
    enabled_email = _startup_email_notification_categories()
    enabled_webhook = _startup_webhook_notification_categories()
    return [_format_startup_notification_line("Notifications (email):", enabled_email), _format_startup_notification_line("Notifications (webhook):", enabled_webhook)]


# Returns whether one configured webhook alert is enabled independently of email settings
def webhook_event_enabled(notification_type: str) -> bool:
    settings = {
        "profile": WEBHOOK_PROFILE_NOTIFICATION,
        "followers_followings": WEBHOOK_PROFILE_NOTIFICATION and WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION,
        "error": WEBHOOK_ERROR_NOTIFICATION,
    }
    return bool(WEBHOOK_ENABLED and settings.get(notification_type, False))


# Returns whether either notification channel is enabled for one event
def notification_channels_enabled(notification_type: str, email_enabled: bool = False) -> bool:
    return bool(email_enabled or webhook_event_enabled(notification_type))


# Returns whether either enabled notification channel has not attempted one event
def notification_channels_pending(notification_type: str, email_enabled: bool, email_attempted: bool, webhook_attempted: bool) -> bool:
    return bool((email_enabled and not email_attempted) or (webhook_event_enabled(notification_type) and not webhook_attempted))


# Parses a webhook rate-limit delay and caps untrusted server values to a short wait
def webhook_retry_after_seconds(response: Any) -> float:
    candidates = []
    headers = getattr(response, "headers", {}) or {}
    if hasattr(headers, "get"):
        candidates.append(headers.get("Retry-After"))
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        candidates.append(payload.get("retry_after"))
    for candidate in candidates:
        if candidate is None or candidate == "":
            continue
        try:
            seconds = float(candidate)
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(candidate))
                seconds = (retry_at - datetime.now(retry_at.tzinfo)).total_seconds()
            except Exception:
                continue
        return max(0.0, min(seconds, WEBHOOK_MAX_RETRY_AFTER_SECONDS))
    return WEBHOOK_FALLBACK_RETRY_SECONDS


# Applies configured placeholders recursively to a webhook template
def format_payload(template: Any, payload: dict) -> Any:
    if isinstance(template, dict):
        return {key: format_payload(value, payload) for key, value in template.items()}
    if isinstance(template, list):
        return [format_payload(value, payload) for value in template]
    if isinstance(template, tuple):
        return tuple(format_payload(value, payload) for value in template)
    if isinstance(template, str):
        if template == "{fields}":
            return payload.get("fields", [])
        if template == "{color}":
            return payload.get("color", 0x1DB954)
        try:
            return template.format(**payload)
        except KeyError:
            return template
    return template


# Returns a configuration error for unsafe or unsupported webhook customization
def validate_webhook_customization(provider: Any = None) -> Optional[str]:
    selected_provider = normalized_webhook_provider(provider)
    if selected_provider == "discord":
        if not isinstance(WEBHOOK_USERNAME, str):
            return "WEBHOOK_USERNAME must be a string"
        if not isinstance(WEBHOOK_AVATAR_URL, str):
            return "WEBHOOK_AVATAR_URL must be a string"
        if WEBHOOK_AVATAR_URL.strip() and not validate_webhook_url(WEBHOOK_AVATAR_URL):
            return "WEBHOOK_AVATAR_URL must contain a complete HTTPS link without embedded credentials"
        if not isinstance(WEBHOOK_TEMPLATE, (dict, list, str)):
            return "WEBHOOK_TEMPLATE must be a dictionary, list or string"
    if not isinstance(WEBHOOK_TRANSFORMS, (list, tuple)):
        return "WEBHOOK_TRANSFORMS must be a list or tuple"
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        if not isinstance(transform, (list, tuple)) or len(transform) < 2 or not isinstance(transform[0], str) or not isinstance(transform[1], str):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} must contain a field name and string method name"
        if transform[1].startswith("_") or not callable(getattr("", transform[1], None)):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} uses an unsupported string method"
    return None


# Applies configured string transformations to one webhook value mapping
def apply_webhook_transforms(payload: dict) -> dict:
    transformed = dict(payload)
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        field = transform[0]
        method_name = transform[1]
        if field not in transformed or not isinstance(transformed[field], str):
            continue
        try:
            transformed[field] = getattr(transformed[field], method_name)(*transform[2:])
        except Exception as exc:
            raise ValueError(f"WEBHOOK_TRANSFORMS entry {index + 1} could not apply {field}.{method_name}") from exc
    return transformed


# Builds bounded placeholder values shared by webhook templates, headers and providers
def build_webhook_values(title: str, description: str, notification_type: str, image_url: str = "") -> dict:
    colors = {"profile": 0x1DB954, "followers_followings": 0x3498DB, "error": 0xE74C3C}
    safe_title = sanitize_error_text(title)[:WEBHOOK_EMBED_TITLE_LIMIT] or "Spotify Profile Monitor"
    safe_description = sanitize_error_text(description)[:WEBHOOK_EMBED_DESCRIPTION_LIMIT]
    username = WEBHOOK_USERNAME.strip()[:80] if isinstance(WEBHOOK_USERNAME, str) else ""
    avatar_url = WEBHOOK_AVATAR_URL.strip() if isinstance(WEBHOOK_AVATAR_URL, str) else ""
    payload = {"title": safe_title, "description": safe_description, "version": VERSION, "image_url": str(image_url or ""), "fields": [], "fields_str": "", "color": colors.get(notification_type, 0x1DB954), "timestamp": datetime.now().astimezone().isoformat(), "username": username, "avatar_url": avatar_url}
    return apply_webhook_transforms(payload)


# Builds one customized Discord-format payload while keeping mentions disabled
def build_webhook_payload(title: str, description: str, notification_type: str, image_url: str = "", payload_values: Optional[dict] = None) -> Any:
    values = build_webhook_values(title, description, notification_type, image_url) if payload_values is None else payload_values
    try:
        payload = format_payload(WEBHOOK_TEMPLATE, values)
    except Exception as exc:
        raise ValueError("WEBHOOK_TEMPLATE could not be formatted with the supported placeholders") from exc
    if isinstance(payload, dict):
        if payload.get("username") == "":
            payload.pop("username")
        if payload.get("avatar_url") == "":
            payload.pop("avatar_url")
        payload["allowed_mentions"] = {"parse": []}
    return payload


# Truncates text to a UTF-8 byte limit with an optional suffix and no partial character
def truncate_utf8_bytes(text: str, max_bytes: int, suffix: str = "") -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    encoded_suffix = suffix.encode("utf-8")
    if len(encoded_suffix) >= max_bytes:
        return encoded_suffix[:max_bytes].decode("utf-8", errors="ignore")
    return encoded[:max_bytes - len(encoded_suffix)].decode("utf-8", errors="ignore") + suffix


# Builds one bounded ntfy title and message pair
def build_ntfy_webhook_message(title: str, description: str) -> Tuple[str, str]:
    safe_title = sanitize_error_text(title)[:WEBHOOK_EMBED_TITLE_LIMIT] or "Spotify Profile Monitor"
    safe_message = truncate_utf8_bytes(sanitize_error_text(description), NTFY_MESSAGE_LIMIT_BYTES, NTFY_TRUNCATION_SUFFIX)
    return safe_title, safe_message


# Returns a safe validation error for one custom webhook header mapping
def _validate_webhook_header_mapping(headers: Any) -> Optional[str]:
    if not isinstance(headers, dict):
        return "WEBHOOK_HEADERS must be a dictionary of string header names and values"
    normalized_names = set()
    for name, value in headers.items():
        if not isinstance(name, str) or not re.fullmatch(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", name):
            return "WEBHOOK_HEADERS contains an invalid HTTP header name"
        normalized_name = name.casefold()
        if normalized_name in normalized_names:
            return "WEBHOOK_HEADERS contains duplicate case-insensitive header names"
        normalized_names.add(normalized_name)
        if not isinstance(value, str):
            return f"WEBHOOK_HEADERS value for {name} must be a string"
        if "\r" in value or "\n" in value:
            return f"WEBHOOK_HEADERS value for {name} must not contain line breaks"
    return None


# Returns a safe configuration error for custom webhook headers or ntfy access tokens
def validate_webhook_headers(provider: Any = None) -> Optional[str]:
    selected_provider = normalized_webhook_provider(provider)
    header_error = _validate_webhook_header_mapping(WEBHOOK_HEADERS)
    if header_error is not None:
        return header_error
    if selected_provider == "ntfy":
        if not isinstance(NTFY_ACCESS_TOKEN, str):
            return "NTFY_ACCESS_TOKEN must be a string"
        token = NTFY_ACCESS_TOKEN.strip()
        if "\r" in token or "\n" in token:
            return "NTFY_ACCESS_TOKEN must not contain line breaks"
        if token.casefold().startswith(("bearer ", "basic ")):
            return "NTFY_ACCESS_TOKEN must contain only the access token without an Authorization scheme"
    return None


# Builds provider-specific headers while formatting placeholders and applying private ntfy authentication
def build_webhook_headers(provider: str, payload: dict) -> dict:
    validation_error = validate_webhook_headers(provider)
    if validation_error is not None:
        raise ValueError(validation_error)
    try:
        formatted_headers = format_payload(WEBHOOK_HEADERS, payload)
    except Exception as exc:
        raise ValueError("WEBHOOK_HEADERS could not be formatted with the supported placeholders") from exc
    formatted_error = _validate_webhook_header_mapping(formatted_headers)
    if formatted_error is not None:
        raise ValueError(formatted_error)
    headers = dict(cast(dict, formatted_headers))
    if not any(name.casefold() == "user-agent" for name in headers):
        headers["User-Agent"] = f"SpotifyProfileMonitor/{VERSION}"
    if provider == "ntfy":
        headers = {name: value for name, value in headers.items() if name.casefold() != "content-type"}
        headers["Content-Type"] = "text/plain; charset=utf-8"
        token = NTFY_ACCESS_TOKEN.strip()
        if token:
            headers = {name: value for name, value in headers.items() if name.casefold() != "authorization"}
            headers["Authorization"] = f"Bearer {token}"
    return headers


# Returns True when a URL may receive a request carrying the Spotify bearer token
def spotify_api_url_is_allowed(api_url: Any) -> bool:
    if not isinstance(api_url, str) or not api_url:
        return False
    try:
        parsed_url = urlsplit(api_url)
    except ValueError:
        return False
    hostname = parsed_url.hostname.casefold() if parsed_url.hostname else ""
    return parsed_url.scheme.casefold() == "https" and any(hostname == suffix or hostname.endswith(f".{suffix}") for suffix in SPOTIFY_CREDENTIALED_HOST_SUFFIXES)


# Validates one server-supplied pagination URL before a request carrying the Spotify bearer token is sent to it
def spotify_next_page_url(next_url: Any, pages_fetched: int, context: str) -> str:
    if not next_url:
        return ""
    if pages_fetched >= SPOTIFY_PAGINATION_MAX_PAGES:
        raise RuntimeError(f"Spotify {context} pagination exceeded {SPOTIFY_PAGINATION_MAX_PAGES} pages")
    if not spotify_api_url_is_allowed(next_url):
        raise RuntimeError(f"Spotify {context} pagination returned a next URL outside the Spotify API: {next_url!r}")
    return str(next_url)


# Returns True when a Spotify image URL uses HTTPS on one of the CDN hosts Spotify serves images from
def spotify_image_url_is_allowed(image_url: str) -> bool:
    try:
        parsed_url = urlsplit(image_url)
    except ValueError:
        return False
    hostname = parsed_url.hostname.casefold() if parsed_url.hostname else ""
    return parsed_url.scheme.casefold() == "https" and any(hostname == suffix or hostname.endswith(f".{suffix}") for suffix in SPOTIFY_IMAGE_ALLOWED_HOST_SUFFIXES)


# Downloads one bounded image from a trusted Spotify CDN host
def download_spotify_notification_image(image_url: str = "") -> Optional[bytes]:
    if not image_url or not NOTIFICATION_IMAGES_AVAILABLE:
        return None
    try:
        if not spotify_image_url_is_allowed(image_url):
            raise ValueError("artwork image URL must use a Spotify HTTPS CDN host")
        debug_print(f"Downloading notification artwork from {image_url}")
        response = WEBHOOK_SESSION.get(image_url, headers={"User-Agent": f"SpotifyProfileMonitor/{VERSION}"}, timeout=WEBHOOK_TIMEOUT_SECONDS, verify=VERIFY_SSL, stream=True, allow_redirects=False)
        with response:
            response.raise_for_status()
            content_type = str((response.headers or {}).get("Content-Type", "")).split(";", 1)[0].strip().casefold()
            if content_type and not content_type.startswith("image/"):
                raise ValueError(f"artwork response has unsupported content type {content_type}")
            content_length = (response.headers or {}).get("Content-Length")
            if content_length is not None and int(content_length) > NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES:
                raise ValueError(f"artwork image exceeds {NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES} bytes")
            image_bytes = bytearray()
            for chunk in response.iter_content(chunk_size=NOTIFICATION_IMAGE_DOWNLOAD_CHUNK_BYTES):
                if not chunk:
                    continue
                image_bytes.extend(chunk)
                if len(image_bytes) > NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES:
                    raise ValueError(f"artwork image exceeds {NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES} bytes")
        if not image_bytes:
            raise ValueError("artwork response was empty")
        return bytes(image_bytes)
    except Exception as error:
        debug_print(f"Artwork download failed, sending without it: {sanitize_error_text(error)}")
        return None


# Builds one bounded JPEG for an inline email artwork attachment
def build_email_artwork(image_url: str = "") -> Optional[bytes]:
    image_bytes = download_spotify_notification_image(image_url)
    if image_bytes is None:
        return None
    try:
        image_module = cast(Any, PILImage)
        with image_module.open(BytesIO(image_bytes)) as original_img:
            if original_img.width * original_img.height > NOTIFICATION_IMAGE_PIXEL_LIMIT:
                raise ValueError(f"artwork image exceeds {NOTIFICATION_IMAGE_PIXEL_LIMIT} pixels")
            original_img.load()
            resized_img = original_img.convert("RGB")
        try:
            resized_img.thumbnail(EMAIL_ARTWORK_MAX_DIMENSIONS, image_module.Resampling.LANCZOS)
            output = BytesIO()
            resized_img.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()
        finally:
            resized_img.close()
    except Exception as error:
        debug_print(f"Email artwork preparation failed, sending text only: {sanitize_error_text(error)}")
        return None


# Escapes one value for safe interpolation into a quoted HTML attribute such as href or src
def escape_html_attr(value) -> str:
    return escape(str(value or ""), quote=True)


# Adds one inline artwork reference before the closing HTML body tag
def add_email_artwork_html(body_html: str, image_name: str = EMAIL_ARTWORK_CONTENT_ID) -> str:
    artwork_html = f'<br><br><img src="cid:{escape_html_attr(image_name)}" alt="Spotify artwork" style="max-width: {EMAIL_ARTWORK_MAX_DIMENSIONS[0]}px; height: auto;">'
    closing_body_index = body_html.casefold().rfind("</body>")
    if closing_body_index >= 0:
        return body_html[:closing_body_index] + artwork_html + body_html[closing_body_index:]
    return body_html + artwork_html


# Selects playlist artwork before album artwork and profile artwork
def select_notification_image_url(playlist_image_url: str = "", album_image_url: str = "", profile_image_url: str = "") -> str:
    return str(playlist_image_url or album_image_url or profile_image_url or "")


# Builds one bounded in-memory JPEG for an ntfy attachment
def build_ntfy_image(image_url: str = "") -> Optional[bytes]:
    if not NTFY_IMAGES or not image_url or not NOTIFICATION_IMAGES_AVAILABLE:
        return None
    image_bytes = download_spotify_notification_image(image_url)
    if image_bytes is None:
        return None
    try:
        image_module = cast(Any, PILImage)
        with image_module.open(BytesIO(image_bytes)) as original_img:
            if original_img.width * original_img.height > NOTIFICATION_IMAGE_PIXEL_LIMIT:
                raise ValueError(f"ntfy image exceeds {NOTIFICATION_IMAGE_PIXEL_LIMIT} pixels")
            original_img.load()
            debug_print(f"NTFY original image dimensions: {original_img.size}")
            resized_img = original_img.convert("RGB")
        try:
            resized_img.thumbnail((160, 160), image_module.Resampling.LANCZOS)
            debug_print(f"NTFY resized image dimensions: {resized_img.size}")
            canvas = image_module.new("RGB", (400, 160), (27, 32, 35))
            try:
                paste_x = (canvas.size[0] - resized_img.size[0]) // 2
                paste_y = (canvas.size[1] - resized_img.size[1]) // 2
                canvas.paste(resized_img, (paste_x, paste_y))
                output = BytesIO()
                canvas.save(output, format="JPEG", quality=85, optimize=True)
                return output.getvalue()
            finally:
                canvas.close()
        finally:
            resized_img.close()
    except Exception as error:
        debug_print(f"NTFY image generation failed, sending text only: {sanitize_error_text(error)}")
        return None


# Prints one structured secret-safe webhook error
def print_webhook_error(detail: Any, context: str = "webhook") -> None:
    print_recovery_error(detail, context)


# Sends one webhook through an isolated bounded retry path that never uses Spotify retries
def send_webhook(title: str, description: str, notification_type: str = "profile", force: bool = False, sleeper: Optional[Callable[[float], None]] = None, image_url: str = "") -> int:
    if not force and not webhook_event_enabled(notification_type):
        return 1
    if not validate_webhook_url():
        print_webhook_error("WEBHOOK_URL must contain a complete HTTPS link", "webhook_config")
        return 1
    provider = normalized_webhook_provider()
    if not provider:
        print_webhook_error("WEBHOOK_PROVIDER must be discord or ntfy", "webhook_config")
        return 1
    customization_error = validate_webhook_customization(provider)
    if customization_error is not None:
        print_webhook_error(customization_error, "webhook_config")
        return 1
    header_error = validate_webhook_headers(provider)
    if header_error is not None:
        print_webhook_error(header_error, "webhook_config")
        return 1
    try:
        webhook_values = build_webhook_values(title, description, notification_type, image_url)
        request_headers = build_webhook_headers(provider, webhook_values)
        discord_payload = build_webhook_payload(title, description, notification_type, image_url, webhook_values) if provider == "discord" else None
    except ValueError as exc:
        print_webhook_error(exc, "webhook_config")
        return 1
    sleep_func = time.sleep if sleeper is None else sleeper
    ntfy_title, ntfy_message = build_ntfy_webhook_message(str(webhook_values["title"]), str(webhook_values["description"])) if provider == "ntfy" else ("", "")
    ntfy_image = build_ntfy_image(image_url) if provider == "ntfy" and NTFY_IMAGES and image_url else None
    use_ntfy_image = ntfy_image is not None
    last_error = None
    for attempt in range(WEBHOOK_MAX_ATTEMPTS):
        try:
            if provider == "ntfy":
                if use_ntfy_image:
                    response = WEBHOOK_SESSION.post(str(WEBHOOK_URL).strip(), data=ntfy_image, params={"title": ntfy_title, "message": ntfy_message}, headers=dict(request_headers, **{"Content-Type": "image/jpeg", "X-Filename": NTFY_IMAGE_FILENAME}), timeout=WEBHOOK_TIMEOUT_SECONDS, allow_redirects=False)
                else:
                    response = WEBHOOK_SESSION.post(str(WEBHOOK_URL).strip(), data=ntfy_message.encode("utf-8"), params={"title": ntfy_title}, headers=request_headers, timeout=WEBHOOK_TIMEOUT_SECONDS, allow_redirects=False)
            elif isinstance(discord_payload, str):
                response = WEBHOOK_SESSION.post(str(WEBHOOK_URL).strip(), data=discord_payload, headers=request_headers, timeout=WEBHOOK_TIMEOUT_SECONDS, allow_redirects=False)
            else:
                response = WEBHOOK_SESSION.post(str(WEBHOOK_URL).strip(), json=discord_payload, headers=request_headers, timeout=WEBHOOK_TIMEOUT_SECONDS, allow_redirects=False)
            if 200 <= response.status_code <= 299:
                return 0
            last_error = response
            retryable = response.status_code == 429 or 500 <= response.status_code <= 599
            if use_ntfy_image and attempt < WEBHOOK_MAX_ATTEMPTS - 1:
                use_ntfy_image = False
                delay = webhook_retry_after_seconds(response) if response.status_code == 429 else WEBHOOK_FALLBACK_RETRY_SECONDS if response.status_code >= 500 else 0.0
                debug_print(f"NTFY attachment returned HTTP {response.status_code}. Falling back to a text-only alert")
                if delay:
                    sleep_func(delay)
                continue
            if not retryable or attempt == WEBHOOK_MAX_ATTEMPTS - 1:
                print_recovery_error(response, "webhook", detail=f"HTTP {response.status_code}: {getattr(response, 'text', '')[:200]}")
                return 1
            delay = webhook_retry_after_seconds(response) if response.status_code == 429 else WEBHOOK_FALLBACK_RETRY_SECONDS
            debug_print(f"Webhook delivery returned HTTP {response.status_code}. Retrying once in {delay:g} seconds")
            sleep_func(delay)
        except req.RequestException as exc:
            last_error = exc
            if use_ntfy_image and attempt < WEBHOOK_MAX_ATTEMPTS - 1:
                use_ntfy_image = False
                debug_print(f"NTFY attachment delivery failed. Falling back to a text-only alert: {sanitize_error_text(exc)}")
                sleep_func(WEBHOOK_FALLBACK_RETRY_SECONDS)
                continue
            if attempt == WEBHOOK_MAX_ATTEMPTS - 1:
                print_webhook_error(exc)
                return 1
            debug_print(f"Webhook delivery failed. Retrying once in {WEBHOOK_FALLBACK_RETRY_SECONDS:g} seconds: {sanitize_error_text(exc)}")
            sleep_func(WEBHOOK_FALLBACK_RETRY_SECONDS)
    print_webhook_error(last_error)
    return 1


# Sends one alert through the enabled email and webhook channels
def send_notification_channels(notification_type: str, subject: str, body: str, body_html: str = "", email_enabled: bool = False, webhook_enabled: Optional[bool] = None, image_url: str = "", email_image_file: str = "", email_image_name: str = "image1", email_image_url: str = "") -> Tuple[bool, bool]:
    email_attempted = bool(email_enabled)
    webhook_attempted = webhook_event_enabled(notification_type) if webhook_enabled is None else bool(webhook_enabled)
    if email_attempted:
        print(f"Sending email notification to {RECEIVER_EMAIL}")
        if email_image_file:
            send_email(subject, body, body_html, SMTP_SSL, email_image_file, email_image_name)
        elif EMAIL_IMAGES and email_image_url:
            email_artwork = build_email_artwork(email_image_url)
            if email_artwork:
                send_email(subject, body, add_email_artwork_html(body_html), SMTP_SSL, image_name=EMAIL_ARTWORK_CONTENT_ID, image_bytes=email_artwork)
            else:
                send_email(subject, body, body_html, SMTP_SSL)
        else:
            send_email(subject, body, body_html, SMTP_SSL)
    if webhook_attempted:
        print("Sending webhook notification")
        send_webhook(subject, body, notification_type, force=True, image_url=image_url)
    return email_attempted, webhook_attempted


# Sends one error only through notification channels that have not attempted it
def send_pending_error_notification(subject: str, body: str, body_html: str, email_attempted: bool, webhook_attempted: bool) -> Tuple[bool, bool]:
    email_sent_now, webhook_sent_now = send_notification_channels("error", subject, body, body_html, email_enabled=ERROR_NOTIFICATION and not email_attempted, webhook_enabled=webhook_event_enabled("error") and not webhook_attempted)
    return email_attempted or email_sent_now, webhook_attempted or webhook_sent_now


# Prefixes one CSV value so spreadsheet software cannot evaluate Spotify-supplied text as a formula
def escape_csv_formula(value):
    return f"'{value}" if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


# Initializes the CSV file
def init_csv_file(csv_file_name, format_type=1):
    try:
        csv_fields = csvfieldnames if format_type == 1 else csvfieldnames_export
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csv_fields, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
    except Exception as e:
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")


# Writes CSV entry
def write_csv_entry(csv_file_name, timestamp, object_type, object_name, old, new, format_type=1):
    try:
        if format_type == 1:
            csv_fields = csvfieldnames
            csv_row = {'Date': timestamp, 'Type': object_type, 'Name': object_name, 'Old': old, 'New': new}
        else:
            csv_fields = csvfieldnames_export
            csv_row = {'Date': timestamp, 'Playlist Name': object_name, 'Artist': old, 'Track': new}

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csv_fields, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({key: escape_csv_formula(value) for key, value in csv_row.items()})

    except Exception as e:
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")


# Converts a datetime to local timezone and removes timezone info (naive)
def convert_to_local_naive(dt: Optional[datetime] = None):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if dt is not None:
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)

        dt_local = dt.astimezone(tz)

        return dt_local.replace(tzinfo=None)
    else:
        return None


# Returns current local time without timezone info (naive)
def now_local_naive():
    return datetime.now(pytz.timezone(LOCAL_TIMEZONE)).replace(microsecond=0, tzinfo=None)


# Returns current local time with timezone info (aware)
def now_local():
    return datetime.now(pytz.timezone(LOCAL_TIMEZONE))


# Converts ISO datetime string to localized datetime (aware)
def convert_iso_str_to_datetime(dt_str):
    if not dt_str:
        return None

    try:
        utc_dt = isoparse(dt_str)
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        return utc_dt.astimezone(pytz.timezone(LOCAL_TIMEZONE))
    except Exception:
        return None


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(now_local_naive()).weekday()]} {now_local_naive().strftime("%d %b %Y, %H:%M:%S")}')


# Prints the current date/time in human readable format with separator; eg. Sun 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("─" * HORIZONTAL_LINE)


# Returns the timestamp/datetime object in human readable format (long version); eg. Sun 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)

    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)

    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)

    else:
        return ""

    return (f'{calendar.day_abbr[ts_new.weekday()]} {ts_new.strftime("%d %b %Y, %H:%M:%S")}')


# Returns the timestamp/datetime object in human readable format (short version); eg.
# Sun 21 Apr 15:08
# Sun 21 Apr 24, 15:08 (if show_year == True and current year is different)
# Sun 21 Apr 25, 15:08 (if always_show_year == True and current year can be the same)
# Sun 21 Apr (if show_hour == False)
# Sun 21 Apr 15:08:32 (if show_seconds == True)
# 21 Apr 15:08 (if show_weekday == False)
def get_short_date_from_ts(ts, show_year=False, show_hour=True, show_weekday=True, show_seconds=False, always_show_year=False):
    tz = pytz.timezone(LOCAL_TIMEZONE)
    if always_show_year:
        show_year = True

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)

    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)

    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)

    else:
        return ""

    if show_hour:
        hour_strftime = " %H:%M:%S" if show_seconds else " %H:%M"
    else:
        hour_strftime = ""

    weekday_str = f"{calendar.day_abbr[ts_new.weekday()]} " if show_weekday else ""

    if (show_year and ts_new.year != datetime.now(tz).year) or always_show_year:
        hour_prefix = "," if show_hour else ""
        return f'{weekday_str}{ts_new.strftime(f"%d %b %y{hour_prefix}{hour_strftime}")}'
    else:
        return f'{weekday_str}{ts_new.strftime(f"%d %b{hour_strftime}")}'


# Returns the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if isinstance(ts, str):
        try:
            ts = isoparse(ts)
        except Exception:
            return ""

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        ts_new = ts.astimezone(tz)

    elif isinstance(ts, int):
        ts_new = datetime.fromtimestamp(ts, tz)

    elif isinstance(ts, float):
        ts_rounded = int(round(ts))
        ts_new = datetime.fromtimestamp(ts_rounded, tz)

    else:
        return ""

    out_strf = "%H:%M:%S" if show_seconds else "%H:%M"
    return ts_new.strftime(out_strf)


# Returns the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False):
    tz = pytz.timezone(LOCAL_TIMEZONE)

    if isinstance(ts1, datetime):
        ts1_new = int(round(ts1.timestamp()))
    elif isinstance(ts1, int):
        ts1_new = ts1
    elif isinstance(ts1, float):
        ts1_new = int(round(ts1))
    else:
        return ""

    if isinstance(ts2, datetime):
        ts2_new = int(round(ts2.timestamp()))
    elif isinstance(ts2, int):
        ts2_new = ts2
    elif isinstance(ts2, float):
        ts2_new = int(round(ts2))
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new, tz).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new, tz).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new, show_seconds=True)}"
    else:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_short_date_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_date_from_ts(ts2_new)}"

    return str(out_str)


# Checks if the given timezone name is valid
def is_valid_timezone(tz_name):
    return tz_name in pytz.all_timezones


# Signal handler for SIGUSR1 allowing to switch email notifications about profile changes
def toggle_profile_changes_notifications_signal_handler(sig, frame):
    global PROFILE_NOTIFICATION
    PROFILE_NOTIFICATION = not PROFILE_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications:\t\t[profile changes = {PROFILE_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGTRAP allowing to increase profile check timer by SPOTIFY_CHECK_SIGNAL_VALUE seconds
def increase_check_signal_handler(sig, frame):
    global SPOTIFY_CHECK_INTERVAL
    SPOTIFY_CHECK_INTERVAL = SPOTIFY_CHECK_INTERVAL + SPOTIFY_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Spotify timers:\t\t[check interval: {display_time(SPOTIFY_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGABRT allowing to decrease profile check timer by SPOTIFY_CHECK_SIGNAL_VALUE seconds
def decrease_check_signal_handler(sig, frame):
    global SPOTIFY_CHECK_INTERVAL
    if SPOTIFY_CHECK_INTERVAL - SPOTIFY_CHECK_SIGNAL_VALUE > 0:
        SPOTIFY_CHECK_INTERVAL = SPOTIFY_CHECK_INTERVAL - SPOTIFY_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Spotify timers:\t\t[check interval: {display_time(SPOTIFY_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGHUP allowing to reload secrets from dotenv files and token source credentials
# from login & client token requests body files
def reload_secrets_signal_handler(sig, frame):
    global DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN, LOGIN_URL, USER_AGENT, APP_VERSION, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL
    global SP_CACHED_ACCESS_TOKEN, SP_CACHED_REFRESH_TOKEN, SP_ACCESS_TOKEN_EXPIRES_AT, SP_CACHED_CLIENT_ID, SP_CACHED_OAUTH_APP_TOKEN, SP_CACHED_CLIENT_TOKEN, SP_CLIENT_TOKEN_EXPIRES_AT, WEBHOOK_PROVIDER

    sig_name = signal.Signals(sig).name

    print(f"* Signal {sig_name} received\n")

    suffix = "\n" if TOKEN_SOURCE == 'client' else ""
    auth_values_before = (SP_DC_COOKIE, SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET, SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, REFRESH_TOKEN, DEVICE_ID, SYSTEM_ID, USER_URI_ID)
    webhook_url_changed = False

    # Disable autoscan if DOTENV_FILE set to none
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        # Reload .env if python-dotenv is installed
        try:
            from dotenv import load_dotenv, find_dotenv
            if DOTENV_FILE:
                env_path = DOTENV_FILE
            else:
                env_path = find_dotenv()
            if env_path:
                load_dotenv(env_path, override=True)
            else:
                print(f"* No .env file found, skipping env-var reload{suffix}")
        except ImportError:
            env_path = None
            print(f"* python-dotenv not installed, skipping env-var reload{suffix}")

    if env_path:
        for secret in SECRET_KEYS:
            old_val = globals().get(secret)
            val = os.getenv(secret)
            if val is not None and val != old_val:
                globals()[secret] = val
                if secret == "WEBHOOK_URL":
                    webhook_url_changed = True
                print(f"* Reloaded {secret} from {env_path}{suffix}")

    if TOKEN_SOURCE == 'client':

        # Process the login request body file
        if LOGIN_REQUEST_BODY_FILE:
            if os.path.isfile(LOGIN_REQUEST_BODY_FILE):
                try:
                    DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN = parse_login_request_body_file(LOGIN_REQUEST_BODY_FILE)
                except Exception as e:
                    print_operation_error(f"Protobuf file '{LOGIN_REQUEST_BODY_FILE}' could not be processed", e)
                else:
                    print(f"* Login data correctly read from Protobuf file ({LOGIN_REQUEST_BODY_FILE}):")
                    print(" - Device ID:\t\t", DEVICE_ID)
                    print(" - System ID:\t\t", SYSTEM_ID)
                    print(" - Spotify user ID:\t", USER_URI_ID)
                    print(" - Refresh Token:\t<<hidden>>\n")
            else:
                print(f"* Error: Protobuf file ({LOGIN_REQUEST_BODY_FILE}) does not exist")

        # Process the client token request body file
        if CLIENTTOKEN_REQUEST_BODY_FILE:
            if os.path.isfile(CLIENTTOKEN_REQUEST_BODY_FILE):
                try:
                    (APP_VERSION, _, _, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL) = parse_clienttoken_request_body_file(CLIENTTOKEN_REQUEST_BODY_FILE)
                except Exception as e:
                    print_operation_error(f"Protobuf file '{CLIENTTOKEN_REQUEST_BODY_FILE}' could not be processed", e)
                else:
                    print(f"* Client token data correctly read from Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}):")
                    print(" - App version:\t\t", APP_VERSION)
                    print(" - CPU arch:\t\t", CPU_ARCH)
                    print(" - OS build:\t\t", OS_BUILD)
                    print(" - Platform:\t\t", PLATFORM)
                    print(" - OS major:\t\t", OS_MAJOR)
                    print(" - OS minor:\t\t", OS_MINOR)
                    print(" - Client model:\t", CLIENT_MODEL, "\n")
            else:
                print(f"* Error: Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}) does not exist")

    auth_values_after = (SP_DC_COOKIE, SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET, SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, REFRESH_TOKEN, DEVICE_ID, SYSTEM_ID, USER_URI_ID)
    if auth_values_after != auth_values_before:
        SP_CACHED_ACCESS_TOKEN = None
        SP_CACHED_REFRESH_TOKEN = None
        SP_ACCESS_TOKEN_EXPIRES_AT = 0
        SP_CACHED_CLIENT_ID = ""
        SP_CACHED_OAUTH_APP_TOKEN = None
        SP_CACHED_CLIENT_TOKEN = None
        SP_CLIENT_TOKEN_EXPIRES_AT = 0
        print(f"* Cleared cached Spotify authentication after secret reload{suffix}")
    if webhook_url_changed:
        detected_provider = detect_webhook_provider(WEBHOOK_URL)
        if detected_provider and detected_provider != normalized_webhook_provider():
            WEBHOOK_PROVIDER = detected_provider
            print(f"* Updated webhook provider to {detected_provider}{suffix}")

    print_cur_ts("Timestamp:\t\t\t")


# Returns Apple & lyrics search URLs for specified track
def get_apple_genius_search_urls(artist, track):
    spotify_search_string = f"{artist} {track}"
    youtube_music_search_string = quote_plus(spotify_search_string)
    # Clean search string for lyrics services (remove remaster, extended, etc.)
    lyrics_search_string = spotify_search_string
    if re.search(re_search_str, lyrics_search_string, re.IGNORECASE):
        lyrics_search_string = re.sub(re_replace_str, '', lyrics_search_string, flags=re.IGNORECASE)
    apple_search_string = quote(spotify_search_string)
    apple_search_url = f"{APPLE_MUSIC_SEARCH_URL}?term={apple_search_string}"
    genius_search_url = f"{GENIUS_SEARCH_URL}?q={quote_plus(lyrics_search_string)}"
    azlyrics_search_url = f"{AZLYRICS_SEARCH_URL}?q={quote_plus(lyrics_search_string)}"
    tekstowo_search_url = f"{TEKSTOWO_SEARCH_URL},{quote_plus(lyrics_search_string)}.html"
    musixmatch_search_url = f"{MUSIXMATCH_SEARCH_URL}?query={quote_plus(lyrics_search_string)}"
    lyrics_com_search_url = f"{LYRICS_COM_SEARCH_URL}?st={quote_plus(lyrics_search_string)}&qtype=1"
    youtube_music_search_url = f"{YOUTUBE_MUSIC_SEARCH_URL}?q={youtube_music_search_string}"
    amazon_music_search_url = f"{AMAZON_MUSIC_SEARCH_URL}/{quote_plus(spotify_search_string)}"
    deezer_search_url = f"{DEEZER_SEARCH_URL}/{quote_plus(spotify_search_string)}"
    tidal_search_url = f"{TIDAL_SEARCH_URL}?q={quote_plus(spotify_search_string)}"
    return apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url


# Formats lyrics URLs for console output based on configuration
def format_lyrics_urls_console(genius_url, azlyrics_url, tekstowo_url, musixmatch_url, lyrics_com_url):
    lines = []
    if ENABLE_GENIUS_LYRICS_URL:
        lines.append(f"Genius lyrics URL: {genius_url}")
    if ENABLE_AZLYRICS_URL:
        lines.append(f"AZLyrics URL: {azlyrics_url}")
    if ENABLE_TEKSTOWO_URL:
        lines.append(f"Tekstowo.pl URL: {tekstowo_url}")
    if ENABLE_MUSIXMATCH_URL:
        lines.append(f"Musixmatch URL: {musixmatch_url}")
    if ENABLE_LYRICS_COM_URL:
        lines.append(f"Lyrics.com URL: {lyrics_com_url}")
    return "\n".join(lines) if lines else ""


# Formats lyrics URLs for plain text email body based on configuration
def format_lyrics_urls_email_text(genius_url, azlyrics_url, tekstowo_url, musixmatch_url, lyrics_com_url):
    lines = []
    if ENABLE_GENIUS_LYRICS_URL:
        lines.append(f"Genius lyrics URL: {genius_url}")
    if ENABLE_AZLYRICS_URL:
        lines.append(f"AZLyrics URL: {azlyrics_url}")
    if ENABLE_TEKSTOWO_URL:
        lines.append(f"Tekstowo.pl URL: {tekstowo_url}")
    if ENABLE_MUSIXMATCH_URL:
        lines.append(f"Musixmatch URL: {musixmatch_url}")
    if ENABLE_LYRICS_COM_URL:
        lines.append(f"Lyrics.com URL: {lyrics_com_url}")
    return "\n".join(lines) if lines else ""


# Formats lyrics URLs for HTML email body based on configuration
def format_lyrics_urls_email_html(genius_url, azlyrics_url, tekstowo_url, musixmatch_url, lyrics_com_url, artist, track):
    lines = []
    escaped_artist = escape(artist)
    escaped_track = escape(track)
    if ENABLE_GENIUS_LYRICS_URL:
        lines.append(f'Genius lyrics URL: <a href="{escape_html_attr(genius_url)}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_AZLYRICS_URL:
        lines.append(f'AZLyrics URL: <a href="{escape_html_attr(azlyrics_url)}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_TEKSTOWO_URL:
        lines.append(f'Tekstowo.pl URL: <a href="{escape_html_attr(tekstowo_url)}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_MUSIXMATCH_URL:
        lines.append(f'Musixmatch URL: <a href="{escape_html_attr(musixmatch_url)}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_LYRICS_COM_URL:
        lines.append(f'Lyrics.com URL: <a href="{escape_html_attr(lyrics_com_url)}">{escaped_artist} - {escaped_track}</a>')
    return "<br>".join(lines) if lines else ""


# Formats music service URLs for console output based on configuration
def format_music_urls_console(apple_music_url, youtube_music_url, amazon_music_url, deezer_url, tidal_url):
    lines = []
    if ENABLE_APPLE_MUSIC_URL:
        lines.append(f"Apple Music URL: {apple_music_url}")
    if ENABLE_YOUTUBE_MUSIC_URL:
        lines.append(f"YouTube Music URL: {youtube_music_url}")
    if ENABLE_AMAZON_MUSIC_URL:
        lines.append(f"Amazon Music URL: {amazon_music_url}")
    if ENABLE_DEEZER_URL:
        lines.append(f"Deezer URL: {deezer_url}")
    if ENABLE_TIDAL_URL:
        lines.append(f"Tidal URL: {tidal_url}")
    return "\n".join(lines) if lines else ""


# Formats music service URLs for plain text email body based on configuration
def format_music_urls_email_text(apple_music_url, youtube_music_url, amazon_music_url, deezer_url, tidal_url):
    lines = []
    if ENABLE_APPLE_MUSIC_URL:
        lines.append(f"Apple Music URL: {apple_music_url}")
    if ENABLE_YOUTUBE_MUSIC_URL:
        lines.append(f"YouTube Music URL: {youtube_music_url}")
    if ENABLE_AMAZON_MUSIC_URL:
        lines.append(f"Amazon Music URL: {amazon_music_url}")
    if ENABLE_DEEZER_URL:
        lines.append(f"Deezer URL: {deezer_url}")
    if ENABLE_TIDAL_URL:
        lines.append(f"Tidal URL: {tidal_url}")
    return "\n".join(lines) if lines else ""


# Formats music service URLs for HTML email body based on configuration
def format_music_urls_email_html(apple_music_url, youtube_music_url, amazon_music_url, deezer_url, tidal_url, artist, track):
    lines = []
    escaped_artist = escape(artist)
    escaped_track = escape(track)
    if ENABLE_APPLE_MUSIC_URL:
        lines.append(f'Apple Music URL: <a href="{escape_html_attr(apple_music_url)}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_YOUTUBE_MUSIC_URL:
        lines.append(f'YouTube Music URL: <a href="{escape_html_attr(youtube_music_url)}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_AMAZON_MUSIC_URL:
        lines.append(f'Amazon Music URL: <a href="{escape_html_attr(amazon_music_url)}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_DEEZER_URL:
        lines.append(f'Deezer URL: <a href="{escape_html_attr(deezer_url)}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_TIDAL_URL:
        lines.append(f'Tidal URL: <a href="{escape_html_attr(tidal_url)}">{escaped_artist} - {escaped_track}</a>')
    return "<br>".join(lines) if lines else ""


# Extracts Spotify ID from URI or URL and return cleaned name
def spotify_extract_id_or_name(s):
    if not isinstance(s, str) or not s.strip():
        return ""

    s = s.strip().lower()

    if s.startswith(f"{SPOTIFY_WEB_BASE_URL}/"):
        parsed = urlparse(s)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) == 2:
            return path_parts[1]
        return s

    if ":" in s:
        return s.split(":")[-1]

    return s


# Sends a lightweight request to check Spotify token validity
def check_token_validity(access_token: str, client_id: Optional[str] = None, user_agent: Optional[str] = None, oauth_app: bool = False) -> bool:
    url_cookie_client = SPOTIFY_PRESENCE_URL

    # Use a known stable track for validation (Bohemian Rhapsody - Queen)
    url_oauth_app = SPOTIFY_OAUTH_VALIDATION_TRACK_URL

    url_oauth_user = SPOTIFY_OAUTH_USER_URL

    if oauth_app or TOKEN_SOURCE == "oauth_app":
        url = url_oauth_app
        check_mode = "oauth_app"
    elif TOKEN_SOURCE in {"cookie", "client"}:
        url = url_cookie_client
        check_mode = f"{TOKEN_SOURCE}_token"
    else:
        url = url_oauth_user
        check_mode = "oauth_user_token"

    headers = {"Authorization": f"Bearer {access_token}"}

    if user_agent is not None:
        headers.update({
            "User-Agent": user_agent
        })

    if not oauth_app and TOKEN_SOURCE == "cookie" and client_id is not None:
        headers.update({
            "Client-Id": client_id
        })

    alarm_state = _start_timeout_alarm(FUNCTION_TIMEOUT + 2)
    try:
        debug_print(
            f"Token validity check mode={check_mode}, url={url}, "
            f"client_id_header={'yes' if 'Client-Id' in headers else 'no'}"
        )
        debug_print(f"HTTP GET {url} [token validity] headers={sanitize_debug_headers(headers)}")
        response = req.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        valid = response.status_code == 200
        debug_print(f"HTTP GET {url} -> {response.status_code} [token validity mode={check_mode}] (valid={valid})")
    except Exception:
        valid = False
        debug_print(f"HTTP GET {url} -> failed during token validity check [mode={check_mode}]")
    finally:
        _restore_timeout_alarm(alarm_state)
    return valid


# -------------------------------------------------------
# Supporting functions when token source is set to cookie
# -------------------------------------------------------

# Returns random user agent string
def get_random_user_agent() -> str:
    browser = random.choice(['chrome', 'firefox', 'edge', 'safari'])

    if browser == 'chrome':
        os_choice = random.choice(['mac', 'windows'])
        if os_choice == 'mac':
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(4, 9)}) "
                f"AppleWebKit/{random.randrange(530, 537)}.{random.randrange(30, 37)} (KHTML, like Gecko) "
                f"Chrome/{random.randrange(80, 105)}.0.{random.randrange(3000, 4500)}.{random.randrange(60, 125)} "
                f"Safari/{random.randrange(530, 537)}.{random.randrange(30, 36)}"
            )
        else:
            chrome_version = random.randint(80, 105)
            build = random.randint(3000, 4500)
            patch = random.randint(60, 125)
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{chrome_version}.0.{build}.{patch} Safari/537.36"
            )

    elif browser == 'firefox':
        os_choice = random.choice(['windows', 'mac', 'linux'])
        version = random.randint(90, 110)
        if os_choice == 'windows':
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )
        elif os_choice == 'mac':
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(0, 10)}; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )
        else:
            return (
                f"Mozilla/5.0 (X11; Linux x86_64; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )

    elif browser == 'edge':
        os_choice = random.choice(['windows', 'mac'])
        chrome_version = random.randint(80, 105)
        build = random.randint(3000, 4500)
        patch = random.randint(60, 125)
        version_str = f"{chrome_version}.0.{build}.{patch}"
        if os_choice == 'windows':
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{version_str} Safari/537.36 Edg/{version_str}"
            )
        else:
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(0, 10)}) "
                f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
                f"Version/{random.randint(13, 16)}.0 Safari/605.1.15 Edg/{version_str}"
            )

    elif browser == 'safari':
        os_choice = 'mac'
        if os_choice == 'mac':
            mac_major = random.randrange(11, 16)
            mac_minor = random.randrange(0, 10)
            webkit_major = random.randint(600, 610)
            webkit_minor = random.randint(1, 20)
            webkit_patch = random.randint(1, 20)
            safari_version = random.randint(13, 16)
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{mac_major}_{mac_minor}) "
                f"AppleWebKit/{webkit_major}.{webkit_minor}.{webkit_patch} (KHTML, like Gecko) "
                f"Version/{safari_version}.0 Safari/{webkit_major}.{webkit_minor}.{webkit_patch}"
            )
        else:
            return ""
    else:
        return ""


# Returns Spotify edge-server Unix time
def fetch_server_time(session: req.Session, ua: str) -> int:

    headers = {
        "User-Agent": ua,
        "Accept": "*/*",
    }

    alarm_state = _start_timeout_alarm(FUNCTION_TIMEOUT + 2)
    try:
        debug_print(f"HTTP HEAD {SERVER_TIME_URL} [server time] timeout={FUNCTION_TIMEOUT}")
        response = session.head(SERVER_TIME_URL, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        debug_print(f"HTTP HEAD {SERVER_TIME_URL} -> {response.status_code}")
    except TimeoutException as e:
        raise Exception(f"fetch_server_time() head network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        raise Exception(f"fetch_server_time() head network request error: {e}")
    finally:
        _restore_timeout_alarm(alarm_state)

    date_hdr = response.headers.get("Date")
    if not date_hdr:
        raise Exception("fetch_server_time() missing 'Date' header")

    return int(parsedate_to_datetime(date_hdr).timestamp())


# Builds a pyotp TOTP object from the configured web-player cipher bytes
def generate_totp():
    import pyotp

    cipher_bytes = TOTP_SECRET_CIPHER_BYTES
    if not cipher_bytes or not all(isinstance(value, int) and not isinstance(value, bool) for value in cipher_bytes):
        raise ValueError("TOTP_SECRET_CIPHER_BYTES must be a non-empty sequence of integers; refresh it with the spotify_monitor_secret_grabber tool if Spotify rotated the web-player secret")
    if not isinstance(TOTP_VERSION, int) or isinstance(TOTP_VERSION, bool) or TOTP_VERSION <= 0:
        raise ValueError("TOTP_VERSION must be a positive integer; refresh it with the spotify_monitor_secret_grabber tool if Spotify rotated the web-player secret")

    transformed = [value ^ ((index % 33) + 9) for index, value in enumerate(cipher_bytes)]
    joined = "".join(str(num) for num in transformed)
    hex_str = joined.encode().hex()
    secret = base64.b32encode(bytes.fromhex(hex_str)).decode().rstrip("=")

    return pyotp.TOTP(secret, digits=6, interval=30)


# Refreshes the Spotify access token using the sp_dc cookie, tries first with mode "transport" and if needed with "init"
def refresh_access_token_from_sp_dc(sp_dc: str) -> dict:
    transport = True
    init = True
    session = req.Session()
    data: dict = {}
    token = ""

    server_time = fetch_server_time(session, USER_AGENT)
    totp_obj = generate_totp()
    otp_value = totp_obj.at(server_time)

    params = {
        "reason": "transport",
        "productType": "web-player",
        "totp": otp_value,
        "totpServer": otp_value,
        "totpVer": TOTP_VERSION,
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Referer": SPOTIFY_WEB_LOGIN_URL,
        "App-Platform": "WebPlayer",
        "Cookie": f"sp_dc={sp_dc}",
    }

    last_err = ""

    alarm_state = _start_timeout_alarm(FUNCTION_TIMEOUT + 2)
    try:
        debug_print(f"HTTP GET {TOKEN_URL} [sp_dc transport] params={sanitize_debug_params(params)} headers={sanitize_debug_headers(headers)}")
        response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        data = response.json()
        token = data.get("accessToken", "")
        debug_print(f"HTTP GET {TOKEN_URL} [sp_dc transport] -> {response.status_code}, token_len={len(token)}")

    except (req.RequestException, TimeoutException, req.HTTPError, ValueError) as e:
        transport = False
        last_err = str(e)
        debug_print(f"HTTP GET {TOKEN_URL} [sp_dc transport] failed: {sanitize_error_text(e)}")
    finally:
        _restore_timeout_alarm(alarm_state)

    if not transport or (sp_dc and not check_token_validity(token, data.get("clientId", ""), USER_AGENT)):
        params["reason"] = "init"

        alarm_state = _start_timeout_alarm(FUNCTION_TIMEOUT + 2)
        try:
            debug_print(f"HTTP GET {TOKEN_URL} [sp_dc init] params={sanitize_debug_params(params)} headers={sanitize_debug_headers(headers)}")
            response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
            response.raise_for_status()
            data = response.json()
            token = data.get("accessToken", "")
            debug_print(f"HTTP GET {TOKEN_URL} [sp_dc init] -> {response.status_code}, token_len={len(token)}")

        except (req.RequestException, TimeoutException, req.HTTPError, ValueError) as e:
            init = False
            last_err = str(e)
            debug_print(f"HTTP GET {TOKEN_URL} [sp_dc init] failed: {sanitize_error_text(e)}")
        finally:
            _restore_timeout_alarm(alarm_state)

    if not init or not data or "accessToken" not in data:
        raise Exception(f"refresh_access_token_from_sp_dc(): Unsuccessful token request{': ' + last_err if last_err else ''}")

    expires_at_ms = data.get("accessTokenExpirationTimestampMs")
    if not isinstance(expires_at_ms, (int, float)) or isinstance(expires_at_ms, bool):
        raise Exception("refresh_access_token_from_sp_dc(): Unsuccessful token request: token response missing expiry")

    return {
        "access_token": token,
        "expires_at": int(expires_at_ms) // 1000,
        "client_id": data.get("clientId", ""),
        "length": len(token)
    }


# Fetches Spotify access token based on provided SP_DC value
def spotify_get_access_token_from_sp_dc(sp_dc: str):
    global SP_CACHED_ACCESS_TOKEN, SP_ACCESS_TOKEN_EXPIRES_AT, SP_CACHED_CLIENT_ID

    now = time.time()

    if SP_CACHED_ACCESS_TOKEN and now < SP_ACCESS_TOKEN_EXPIRES_AT and check_token_validity(SP_CACHED_ACCESS_TOKEN, SP_CACHED_CLIENT_ID, USER_AGENT):
        debug_print("Using cached Spotify access token (sp_dc source)")
        return SP_CACHED_ACCESS_TOKEN

    max_retries = TOKEN_MAX_RETRIES
    retry = 0

    last_error = ""

    while retry < max_retries:
        try:
            debug_print(f"Refreshing Spotify access token via sp_dc (attempt {retry + 1}/{max_retries})")
            token_data = refresh_access_token_from_sp_dc(sp_dc)
            token = token_data["access_token"]
            client_id = token_data.get("client_id", "")
            length = token_data["length"]

            SP_CACHED_ACCESS_TOKEN = token
            SP_ACCESS_TOKEN_EXPIRES_AT = token_data["expires_at"]
            SP_CACHED_CLIENT_ID = client_id

            if SP_CACHED_ACCESS_TOKEN is None or not check_token_validity(SP_CACHED_ACCESS_TOKEN, SP_CACHED_CLIENT_ID, USER_AGENT):
                debug_print("Received token is invalid, retrying")
                retry += 1
                time.sleep(TOKEN_RETRY_TIMEOUT)
            else:
                debug_print(f"Spotify access token obtained successfully, length={length}")
                verbose_print("Authentication token refreshed (cookie mode)")
                break
        except Exception as e:
            last_error = str(e)
            debug_print(f"Token refresh attempt failed: {sanitize_error_text(e)}")
            retry += 1
            if retry < max_retries:
                time.sleep(TOKEN_RETRY_TIMEOUT)

    if retry == max_retries:
        error_msg = f"Failed to obtain a valid Spotify access token after {max_retries} attempts"
        if last_error:
            error_msg += f": {last_error}"
        raise RuntimeError(error_msg)

    return SP_CACHED_ACCESS_TOKEN


# ----------------------------------------------------------
# Supporting functions when token source is set to oauth_app
# ----------------------------------------------------------


# Fetches Spotify access token based on provided sp_client_id & sp_client_secret values (Client Credentials OAuth Flow)
def spotify_get_access_token_from_oauth_app(sp_client_id, sp_client_secret):
    global SP_CACHED_OAUTH_APP_TOKEN

    if not sp_client_id or not sp_client_secret:
        return None

    try:
        from spotipy.oauth2 import SpotifyClientCredentials
        from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler
    except ImportError:
        install_command = _wizard_render_command([sys.executable or ("python" if platform.system() == "Windows" else "python3"), "-m", "pip", "install", "spotipy"])
        print(f"* Warning: the 'spotipy' package is required for 'oauth_app' token source")
        print(f"To fix: Install it through the active Python environment then retry: {install_command}")
        print(f"Guide: {INSTALLATION_GUIDE_URL}")
        return None

    if SP_CACHED_OAUTH_APP_TOKEN and check_token_validity(SP_CACHED_OAUTH_APP_TOKEN, oauth_app=True):
        debug_print("Using cached OAuth app access token")
        return SP_CACHED_OAUTH_APP_TOKEN

    if SP_APP_TOKENS_FILE:
        cache_handler = CacheFileHandler(cache_path=SP_APP_TOKENS_FILE)
    else:
        cache_handler = MemoryCacheHandler()

    session = req.Session()
    session.headers.update({'User-Agent': USER_AGENT})

    auth_manager = SpotifyClientCredentials(client_id=sp_client_id, client_secret=sp_client_secret, cache_handler=cache_handler, requests_session=session)  # type: ignore[arg-type]

    SP_CACHED_OAUTH_APP_TOKEN = auth_manager.get_access_token(as_dict=False)
    debug_print("OAuth app access token refreshed successfully")
    verbose_print("Legacy OAuth metadata token refreshed")

    return SP_CACHED_OAUTH_APP_TOKEN


# -----------------------------------------------------------
# Supporting functions when token source is set to oauth_user
# -----------------------------------------------------------


# Fetches Spotify access token based on provided sp_client_id, sp_client_secret, redirect_uri and scope values
# (Authorization Code OAuth Flow)
# Silently refreshes the token or optionally runs the interactive auth flow
def spotify_get_access_token_from_oauth_user(sp_client_id, sp_client_secret, redirect_uri, scope, init=False):
    global SP_CACHED_ACCESS_TOKEN

    try:
        from spotipy.oauth2 import SpotifyOAuth, SpotifyPKCE
        from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler
    except ImportError:
        install_command = _wizard_render_command([sys.executable or ("python" if platform.system() == "Windows" else "python3"), "-m", "pip", "install", "spotipy"])
        print(f"* Warning: the 'spotipy' package is required for 'oauth_user' token source")
        print(f"To fix: Install it through the active Python environment then retry: {install_command}")
        print(f"Guide: {INSTALLATION_GUIDE_URL}")
        return None

    if SP_CACHED_ACCESS_TOKEN and check_token_validity(SP_CACHED_ACCESS_TOKEN):
        return SP_CACHED_ACCESS_TOKEN

    if SP_USER_TOKENS_FILE:
        cache_handler = CacheFileHandler(cache_path=SP_USER_TOKENS_FILE)
    else:
        cache_handler = MemoryCacheHandler()

    session = req.Session()
    session.headers.update({'User-Agent': USER_AGENT})

    if sp_client_secret:
        # Use standard Authorization Code flow with client secret
        auth_manager = SpotifyOAuth(client_id=sp_client_id, client_secret=sp_client_secret, redirect_uri=redirect_uri, scope=scope, cache_handler=cache_handler, open_browser=False, show_dialog=init, requests_session=session)  # type: ignore[arg-type]
    else:
        # Use Authorization Code PKCE flow without a client secret
        auth_manager = SpotifyPKCE(client_id=sp_client_id, redirect_uri=redirect_uri, scope=scope, cache_handler=cache_handler, open_browser=False, requests_session=session)  # type: ignore[arg-type]

    token_info = auth_manager.get_cached_token()

    if not token_info:
        if init:
            print(f"Authorizing via OAuth{' (PKCE)' if not sp_client_secret else ''}...")
            auth_url = auth_manager.get_authorize_url()
            print(f"\nOpen this URL in your web browser to authorize:\n{auth_url}\n")
            response = input("Paste the full callback URL: ").strip()
            code = auth_manager.parse_response_code(response)
            if sp_client_secret:
                auth_manager.get_access_token(code, as_dict=False)  # type: ignore[arg-type]
            else:
                auth_manager.get_access_token(code)
            token_info = auth_manager.get_cached_token()
        else:
            raise RuntimeError("User OAuth token missing or expired - re-authorization required")

    if token_info is None:
        raise RuntimeError("Failed to obtain token info - authorization did not return tokens")

    expires_at = token_info.get("expires_at", 0)
    if time.time() >= expires_at:
        refresh_token = token_info.get("refresh_token")
        if init and refresh_token:
            token_info = auth_manager.refresh_access_token(refresh_token)
        else:
            raise RuntimeError("User token expired - reauthorization required")

    SP_CACHED_ACCESS_TOKEN = token_info.get("access_token")
    return token_info.get("access_token")


# -------------------------------------------------------
# Supporting functions when token source is set to client
# -------------------------------------------------------

# Returns random Spotify client user agent string
def get_random_spotify_user_agent() -> str:
    os_choice = random.choice(['windows', 'mac', 'linux'])

    if os_choice == 'windows':
        build = random.randint(120000000, 130000000)
        arch = random.choice(['Win32', 'Win32_x86_64'])
        device = random.choice(['desktop', 'laptop'])
        return f"Spotify/{build} {arch}/0 (PC {device})"

    elif os_choice == 'mac':
        build = random.randint(120000000, 130000000)
        arch = random.choice(['OSX_ARM64', 'OSX_X86_64'])
        major = random.randint(10, 15)
        minor = random.randint(0, 7)
        patch = random.randint(0, 5)
        os_version = f"OS X {major}.{minor}.{patch}"
        if arch == 'OSX_ARM64':
            bracket = f"[arm {random.randint(1, 3)}]"
        else:
            bracket = "[x86_64]"
        return f"Spotify/{build} {arch}/{os_version} {bracket}"

    else:  # linux
        build = random.randint(120000000, 130000000)
        arch = random.choice(['Linux; x86_64', 'Linux; x86'])
        return f"Spotify/{build} ({arch})"


# Encodes an integer using Protobuf varint format
def encode_varint(value):
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value //= 128
    result.append(value)
    return bytes(result)


# Encodes a string field with the given tag
def encode_string_field(tag, value):
    key = encode_varint((tag << 3) | 2)  # wire type 2 (length-delimited)
    value_bytes = value.encode('utf-8')
    length = encode_varint(len(value_bytes))
    return key + length + value_bytes


# Encodes a nested message field with the given tag
def encode_nested_field(tag, nested_bytes):
    key = encode_varint((tag << 3) | 2)
    length = encode_varint(len(nested_bytes))
    return key + length + nested_bytes


# Builds the Spotify Protobuf login request body
def build_spotify_auth_protobuf(device_id, system_id, user_uri_id, refresh_token):
    """
    {
      1: {
           1: "device_id",
           2: "system_id"
         },
      100: {
           1: "user_uri_id",
           2: "refresh_token"
         }
    }
    """
    device_info_msg = encode_string_field(1, device_id) + encode_string_field(2, system_id)
    field_device_info = encode_nested_field(1, device_info_msg)

    user_auth_msg = encode_string_field(1, user_uri_id) + encode_string_field(2, refresh_token)
    field_user_auth = encode_nested_field(100, user_auth_msg)

    return field_device_info + field_user_auth


# Reads a varint from data starting at index
def read_varint(data, index):
    shift = 0
    result = 0
    bytes_read = 0
    while True:
        b = data[index]
        result |= ((b & 0x7F) << shift)
        bytes_read += 1
        index += 1
        if not (b & 0x80):
            break
        shift += 7
    return result, bytes_read


# Parses Spotify Protobuf login response
def parse_protobuf_message(data):
    index = 0
    result = {}
    while index < len(data):
        try:
            key, key_len = read_varint(data, index)
        except IndexError:
            break
        index += key_len
        tag = key >> 3
        wire_type = key & 0x07
        if wire_type == 2:  # length-delimited
            length, len_len = read_varint(data, index)
            index += len_len
            raw_value = data[index:index + length]
            index += length
            # If the first byte is a control character (e.g. 0x0A) assume nested
            if raw_value and raw_value[0] < 0x20:
                value = parse_protobuf_message(raw_value)
            else:
                try:
                    value = raw_value.decode('utf-8')
                except UnicodeDecodeError:
                    value = raw_value
            result[tag] = value
        elif wire_type == 0:  # varint
            value, var_len = read_varint(data, index)
            index += var_len
            result[tag] = value
        else:
            break
    return result  # dictionary mapping tags to values


# Parses the Protobuf-encoded login request body file (as dumped for example by Proxyman) and returns a tuple:
# (device_id, system_id, user_uri_id, refresh_token)
def parse_login_request_body_file(file_path):
    """
    {
      1: {
           1: "device_id",
           2: "system_id"
         },
      100: {
           1: "user_uri_id",
           2: "refresh_token"
         }
    }
    """
    with open(file_path, "rb") as f:
        data = f.read()
    parsed = parse_protobuf_message(data)

    device_id = None
    system_id = None
    user_uri_id = None
    refresh_token = None

    if 1 in parsed:
        device_info = parsed[1]
        if isinstance(device_info, dict):
            device_id = device_info.get(1)
            system_id = device_info.get(2)
        else:
            pass

    if 100 in parsed:
        user_auth = parsed[100]
        if isinstance(user_auth, dict):
            user_uri_id = user_auth.get(1)
            refresh_token = user_auth.get(2)

    protobuf_fields = {
        "device_id": device_id,
        "system_id": system_id,
        "user_uri_id": user_uri_id,
        "refresh_token": refresh_token,
    }

    protobuf_missing_fields = [name for name, value in protobuf_fields.items() if value is None]

    if protobuf_missing_fields:
        missing_str = ", ".join(protobuf_missing_fields)
        raise Exception(f"Following fields could not be extracted: {missing_str}")

    return device_id, system_id, user_uri_id, refresh_token


# Recursively flattens nested dictionaries or lists into a single string
def deep_flatten(value):
    if isinstance(value, dict):
        return "".join(deep_flatten(v) for k, v in sorted(value.items()))
    elif isinstance(value, list):
        return "".join(deep_flatten(item) for item in value)
    else:
        return str(value)


# Returns the input if it's a dict, parses as Protobuf it if it's bytes or returns an empty dict otherwise
def ensure_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            return parse_protobuf_message(value)
        except Exception:
            return {}
    return {}


# Parses the Protobuf-encoded client token request body file (as dumped for example by Proxyman) and returns a tuple:
# (app_version, device_id, system_id, cpu_arch, os_build, platform, os_major, os_minor, client_model)
def parse_clienttoken_request_body_file(file_path):
    """
        1: 1 (const)
        2: {
          1: "app_version"
          2: "device_id"
          3: {
            1: {
              4: {
                1: "cpu_arch"
                3: "os_build"
                4: "platform"
                5: "os_major"
                6: "os_minor"
                8: "client_model"
              }
            }
            2: "system_id"
          }
        }
    """

    with open(file_path, "rb") as f:
        data = f.read()

    root = ensure_dict(parse_protobuf_message(data).get(2))

    app_version = root.get(1)
    device_id = root.get(2)

    nested_3 = ensure_dict(root.get(3))
    nested_1 = ensure_dict(nested_3.get(1))
    nested_4 = ensure_dict(nested_1.get(4))

    cpu_arch = nested_4.get(1)
    os_build = nested_4.get(3)
    platform = nested_4.get(4)
    os_major = nested_4.get(5)
    os_minor = nested_4.get(6)
    client_model = nested_4.get(8)

    system_id = nested_3.get(2)

    required = {
        "app_version": app_version,
        "device_id": device_id,
        "system_id": system_id,
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise Exception(f"Could not extract fields: {', '.join(missing)}")

    return (app_version, device_id, system_id, cpu_arch, os_build, platform, os_major, os_minor, client_model)


# Converts Spotify user agent string to Protobuf app_version string
# For example: 'Spotify/126200580 Win32_x86_64/0 (PC desktop)' to '1.2.62.580.g<random-hex>'
def ua_to_app_version(user_agent: str) -> str:

    m = re.search(r"Spotify/(\d{5,})", user_agent)
    if not m:
        raise ValueError(f"User-Agent missing build number: {user_agent!r}")

    digits = m.group(1)
    if len(digits) < 5:
        raise ValueError(f"Build number too short: {digits}")

    major = digits[0]
    minor = digits[1]
    patch = str(int(digits[2:4]))
    build = str(int(digits[4:]))
    suffix = secrets.token_hex(4)

    return f"{major}.{minor}.{patch}.{build}.g{suffix}"


# Builds the Protobuf client token request body
def build_clienttoken_request_protobuf(app_version, device_id, system_id, cpu_arch=10, os_build=19045, platform=2, os_major=9, os_minor=9, client_model=34404):
    """
        1: 1 (const)
        2: {
          1: "app_version"
          2: "device_id"
          3: {
            1: {
              4: {
                1: "cpu_arch"
                3: "os_build"
                4: "platform"
                5: "os_major"
                6: "os_minor"
                8: "client_model"
              }
            }
            2: "system_id"
          }
        }
    """

    leaf = (
        encode_varint((1 << 3) | 0) + encode_varint(cpu_arch) + encode_varint((3 << 3) | 0) + encode_varint(os_build) + encode_varint((4 << 3) | 0) + encode_varint(platform) + encode_varint((5 << 3) | 0) + encode_varint(os_major) + encode_varint((6 << 3) | 0) + encode_varint(os_minor) + encode_varint((8 << 3) | 0) + encode_varint(client_model))

    msg_4 = encode_nested_field(4, leaf)
    msg_1 = encode_nested_field(1, msg_4)
    msg_3 = msg_1 + encode_string_field(2, system_id)

    payload = (encode_string_field(1, app_version) + encode_string_field(2, device_id) + encode_nested_field(3, msg_3))

    root = (encode_varint((1 << 3) | 0) + encode_varint(1) + encode_nested_field(2, payload))

    return root


# Fetches Spotify access token based on provided device_id, system_id, user_uri_id, refresh_token and client_token value
def spotify_get_access_token_from_client(device_id, system_id, user_uri_id, refresh_token, client_token):
    global SP_CACHED_ACCESS_TOKEN, SP_CACHED_REFRESH_TOKEN, SP_ACCESS_TOKEN_EXPIRES_AT

    if SP_CACHED_ACCESS_TOKEN and time.time() < SP_ACCESS_TOKEN_EXPIRES_AT and check_token_validity(SP_CACHED_ACCESS_TOKEN, user_agent=USER_AGENT):
        debug_print("Using cached Spotify access token (client source)")
        return SP_CACHED_ACCESS_TOKEN

    if not client_token:
        raise Exception("Client token is missing")

    if SP_CACHED_REFRESH_TOKEN:
        debug_print("Using cached refresh token for client auth flow")
        refresh_token = SP_CACHED_REFRESH_TOKEN

    protobuf_body = build_spotify_auth_protobuf(device_id, system_id, user_uri_id, refresh_token)

    parsed_url = urlparse(LOGIN_URL)
    host = parsed_url.netloc
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

    headers = {
        "Host": host,
        "Connection": "keep-alive",
        "Content-Type": "application/x-protobuf",
        "User-Agent": USER_AGENT,
        "X-Retry-Count": "0",
        "Client-Token": client_token,
        "Origin": origin,
        "Accept-Language": "en-Latn-GB,en-GB;q=0.9,en;q=0.8",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Dest": "empty",
        "Accept-Encoding": "gzip, deflate, br, zstd"
    }

    alarm_state = _start_timeout_alarm(FUNCTION_TIMEOUT + 2)
    try:
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] headers={sanitize_debug_headers(headers)} payload_len={len(protobuf_body)}")
        response = req.post(LOGIN_URL, headers=headers, data=protobuf_body, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] -> {response.status_code}")
    except TimeoutException as e:
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] timeout: {sanitize_error_text(e)}")
        raise Exception(f"spotify_get_access_token_from_client() network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] failed: {sanitize_error_text(e)}")
        raise Exception(f"spotify_get_access_token_from_client() network request error: {e}")
    finally:
        _restore_timeout_alarm(alarm_state)

    if response.status_code != 200:
        if response.headers.get("client-token-error") == "INVALID_CLIENTTOKEN":
            raise Exception(f"Request failed with status {response.status_code}: invalid client token")
        elif response.headers.get("client-token-error") == "EXPIRED_CLIENTTOKEN":
            raise Exception(f"Request failed with status {response.status_code}: expired client token")

        try:
            error_json = response.json()
        except ValueError:
            error_json = {}

        if error_json.get("error") == "invalid_grant":
            desc = error_json.get("error_description", "")
            if "refresh token" in desc.lower() and "revoked" in desc.lower():
                raise Exception(f"Request failed with status {response.status_code}: refresh token has been revoked")
            elif "refresh token" in desc.lower() and "expired" in desc.lower():
                raise Exception(f"Request failed with status {response.status_code}: refresh token has expired")
            elif "invalid refresh token" in desc.lower():
                raise Exception(f"Request failed with status {response.status_code}: refresh token is invalid")
            else:
                raise Exception(f"Request failed with status {response.status_code}: invalid grant during refresh ({desc})")

        raise Exception(f"Request failed with status code {response.status_code}\nResponse Headers: {response.headers}\nResponse Content (raw): {response.content}\nResponse text: {response.text}")

    parsed = parse_protobuf_message(response.content)
    # {1: {1: user_uri_id, 2: access_token, 3: refresh_token, 4: expires_in}}
    access_token_raw = None
    expires_in = 3600  # default
    if 1 in parsed and isinstance(parsed[1], dict):
        nested = parsed[1]
        access_token_raw = nested.get(2)
        user_uri_id = parsed[1].get(1)

        if 4 in nested:
            raw_expires = nested.get(4)
            if isinstance(raw_expires, (int, str, bytes)):
                try:
                    expires_in = int(raw_expires)
                except ValueError:
                    expires_in = 3600

    access_token = deep_flatten(access_token_raw) if access_token_raw else None

    if not access_token:
        raise Exception("Access token not found in response")

    SP_CACHED_ACCESS_TOKEN = access_token
    SP_CACHED_REFRESH_TOKEN = parsed[1].get(3)
    SP_ACCESS_TOKEN_EXPIRES_AT = time.time() + expires_in
    verbose_print("Authentication token refreshed (advanced client mode)")
    return access_token


# Fetches fresh client token
def spotify_get_client_token(app_version, device_id, system_id, **device_overrides):
    global SP_CACHED_CLIENT_TOKEN, SP_CLIENT_TOKEN_EXPIRES_AT

    if SP_CACHED_CLIENT_TOKEN and time.time() < SP_CLIENT_TOKEN_EXPIRES_AT:
        debug_print("Using cached client token")
        return SP_CACHED_CLIENT_TOKEN

    body = build_clienttoken_request_protobuf(app_version, device_id, system_id, **device_overrides)

    headers = {
        "Host": "clienttoken.spotify.com",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache, no-store, max-age=0",
        "Accept": "application/x-protobuf",
        "Content-Type": "application/x-protobuf",
        "User-Agent": USER_AGENT,
        "Origin": SPOTIFY_CLIENTTOKEN_ORIGIN,
        "Accept-Language": "en-Latn-GB,en-GB;q=0.9,en;q=0.8",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Dest": "empty",
        "Accept-Encoding": "gzip, deflate, br, zstd",
    }

    alarm_state = _start_timeout_alarm(FUNCTION_TIMEOUT + 2)
    try:
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] app_version={app_version}, device_overrides={device_overrides}, payload_len={len(body)}")
        response = req.post(CLIENTTOKEN_URL, headers=headers, data=body, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] -> {response.status_code}")
    except TimeoutException as e:
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] timeout: {sanitize_error_text(e)}")
        raise Exception(f"spotify_get_client_token() network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] failed: {sanitize_error_text(e)}")
        raise Exception(f"spotify_get_client_token() network request error: {e}")
    finally:
        _restore_timeout_alarm(alarm_state)

    if response.status_code != 200:
        raise Exception(f"clienttoken request failed - status {response.status_code}\nHeaders: {response.headers}\nBody (raw): {response.content[:120]}...")

    parsed = parse_protobuf_message(response.content)
    inner = parsed.get(2, {})
    client_token = deep_flatten(inner.get(1)) if inner.get(1) else None
    ttl = int(inner.get(3, 0)) or 1209600

    if not client_token:
        raise Exception("clienttoken response did not contain a token")

    SP_CACHED_CLIENT_TOKEN = client_token
    SP_CLIENT_TOKEN_EXPIRES_AT = time.time() + ttl
    debug_print(f"Client token refreshed successfully, ttl={ttl}s")
    verbose_print("Spotify client token refreshed")

    return client_token


# Fetches Spotify access token with automatic client token refresh
def spotify_get_access_token_from_client_auto(device_id, system_id, user_uri_id, refresh_token):
    client_token = None

    if all([
        CLIENTTOKEN_URL,
        APP_VERSION,
        CPU_ARCH is not None and CPU_ARCH > 0,
        OS_BUILD is not None and OS_BUILD > 0,
        PLATFORM is not None and PLATFORM > 0,
        OS_MAJOR is not None and OS_MAJOR > 0,
        OS_MINOR is not None and OS_MINOR > 0,
        CLIENT_MODEL is not None and CLIENT_MODEL > 0
    ]):
        debug_print("Attempting to refresh/get client token before client auth")
        client_token = spotify_get_client_token(app_version=APP_VERSION, device_id=device_id, system_id=system_id, cpu_arch=CPU_ARCH, os_build=OS_BUILD, platform=PLATFORM, os_major=OS_MAJOR, os_minor=OS_MINOR, client_model=CLIENT_MODEL)

    try:
        return spotify_get_access_token_from_client(device_id, system_id, user_uri_id, refresh_token, client_token)
    except Exception as e:
        err = str(e).lower()
        debug_print(f"Client auth failed: {sanitize_error_text(e)}")
        if all([
            CLIENTTOKEN_URL,
            APP_VERSION,
            CPU_ARCH is not None and CPU_ARCH > 0,
            OS_BUILD is not None and OS_BUILD > 0,
            PLATFORM is not None and PLATFORM > 0,
            OS_MAJOR is not None and OS_MAJOR > 0,
            OS_MINOR is not None and OS_MINOR > 0,
            CLIENT_MODEL is not None and CLIENT_MODEL > 0
        ]) and ("invalid client token" in err or "expired client token" in err):
            global SP_CLIENT_TOKEN_EXPIRES_AT
            SP_CLIENT_TOKEN_EXPIRES_AT = 0
            debug_print("Client token invalid/expired, forcing refresh and retry")

            client_token = spotify_get_client_token(app_version=APP_VERSION, device_id=DEVICE_ID, system_id=SYSTEM_ID, cpu_arch=CPU_ARCH, os_build=OS_BUILD, platform=PLATFORM, os_major=OS_MAJOR, os_minor=OS_MINOR, client_model=CLIENT_MODEL)

            return spotify_get_access_token_from_client(device_id, system_id, user_uri_id, refresh_token, client_token)
        raise


# --------------------------------------------------------


# Removes the specified key from the list of dictionaries
def remove_key_from_list_of_dicts(list_of_dicts, del_key):
    if list_of_dicts:
        for items in list_of_dicts:
            if del_key in items:
                del items[del_key]


# Removes the specified key from the list of dictionaries, but preserves the original list
def remove_key_from_list_of_dicts_copy(list_of_dicts, del_key):
    if not list_of_dicts:
        return []
    return [{k: v for k, v in d.items() if k != del_key} for d in list_of_dicts]


# Displays one image inline through imgcat using an argument vector instead of a shell
def display_image_via_imgcat(imgcat_exe, path, blank_before=False, blank_after=False):
    # Route the spacing to the terminal only; the image itself bypasses the log, so its blank lines should too
    terminal_out = stdout_bck if stdout_bck is not None else sys.stdout
    if blank_before:
        terminal_out.write("\n")
        terminal_out.flush()
    subprocess.run([imgcat_exe, path], check=True)
    if blank_after:
        terminal_out.write("\n")
        terminal_out.flush()


# Displays the downloaded image for user's profile or playlist's artwork
def display_tmp_pic(image_url, pic_file_tmp, imgcat_exe=None, is_profile=True):

    if image_url:
        if save_profile_pic(image_url, pic_file_tmp):
            pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(pic_file_tmp)), pytz.timezone(LOCAL_TIMEZONE))
            if not is_profile:
                delta_seconds = abs((now_local() - pic_mdate_dt).total_seconds())
                if delta_seconds <= 60:
                    print("auto-generated")
                else:
                    print(f"user‐uploaded ({get_short_date_from_ts(pic_mdate_dt, always_show_year=True)} - {calculate_timespan(now_local(), pic_mdate_dt, show_seconds=False)} ago)")
            else:
                print(f"({get_short_date_from_ts(pic_mdate_dt, always_show_year=True)} - {calculate_timespan(now_local(), pic_mdate_dt, show_seconds=False)} ago)")
            if imgcat_exe:
                try:
                    display_image_via_imgcat(imgcat_exe, pic_file_tmp, blank_before=True)
                except Exception:
                    pass
            try:
                os.remove(pic_file_tmp)
            except Exception:
                pass
        else:
            print("")
    else:
        print("")


# Converts Spotify URI (e.g. spotify:user:username) to URL (e.g. https://open.spotify.com/user/username)
def spotify_convert_uri_to_url(uri):
    # Add si parameter so link opens in native Spotify app after clicking
    si = "?si=1"
    # si=""

    uri = uri or ''
    url = ""
    if not isinstance(uri, str):
        return url
    if "spotify:user:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"{SPOTIFY_WEB_BASE_URL}/user/{s_id}{si}"
    elif "spotify:artist:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"{SPOTIFY_WEB_BASE_URL}/artist/{s_id}{si}"
    elif "spotify:track:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"{SPOTIFY_WEB_BASE_URL}/track/{s_id}{si}"
    elif "spotify:album:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"{SPOTIFY_WEB_BASE_URL}/album/{s_id}{si}"
    elif "spotify:playlist:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"{SPOTIFY_WEB_BASE_URL}/playlist/{s_id}{si}"

    return url


# Converts Spotify URL (e.g. https://open.spotify.com/user/username) or URI to URI (e.g. spotify:user:username), returning an empty string when the reference cannot be parsed
def spotify_convert_url_to_uri(url):
    if not isinstance(url, str):
        return ""

    value = url.strip()
    if not value:
        return ""

    if value.casefold().startswith("spotify:"):
        parts = value.split(":")
        if len(parts) == 3 and parts[1].casefold() in SPOTIFY_OBJECT_TYPES and parts[2]:
            return f"spotify:{parts[1].casefold()}:{parts[2]}"
        return ""

    try:
        parsed = urlsplit(value)
    except ValueError:
        return ""

    # Whole path segments are matched so an object ID that merely contains "user", "track" or "album" cannot be
    # mistaken for the object type, and so a localized link such as /intl-pl/track/<id> still resolves correctly
    segments = [segment for segment in parsed.path.split("/") if segment]
    for index, segment in enumerate(segments[:-1]):
        object_type = segment.casefold()
        if object_type in SPOTIFY_OBJECT_TYPES:
            return f"spotify:{object_type}:{segments[index + 1]}"

    return ""


# Returns True when complete non-placeholder OAuth app credentials are configured
def spotify_has_oauth_app_credentials():
    return not any([not SP_APP_CLIENT_ID, SP_APP_CLIENT_ID == "your_spotify_app_client_id", not SP_APP_CLIENT_SECRET, SP_APP_CLIENT_SECRET == "your_spotify_app_client_secret"])


# Describes the configured playlist backend policy for startup output
def spotify_get_playlist_backend_description():
    api_available = TOKEN_SOURCE in {"oauth_app", "oauth_user"} or spotify_has_oauth_app_credentials()
    return "automatic (legacy Web API + web player)" if api_available else "web player"


# Returns a cached or freshly generated anonymous Spotify web-player token
def spotify_get_web_access_token_data():
    global SP_CACHED_WEB_ACCESS_TOKEN, SP_WEB_ACCESS_TOKEN_EXPIRES_AT, SP_CACHED_WEB_CLIENT_ID

    now = time.time()
    if SP_CACHED_WEB_ACCESS_TOKEN and now < SP_WEB_ACCESS_TOKEN_EXPIRES_AT - 60:
        return {"access_token": SP_CACHED_WEB_ACCESS_TOKEN, "expires_at": SP_WEB_ACCESS_TOKEN_EXPIRES_AT, "client_id": SP_CACHED_WEB_CLIENT_ID}

    token_data = refresh_access_token_from_sp_dc("")
    access_token = token_data.get("access_token", "")
    expires_at = token_data.get("expires_at", 0)
    client_id = token_data.get("client_id", "")
    if not access_token or not expires_at or not client_id:
        raise RuntimeError("Spotify returned incomplete anonymous web-player token data")

    SP_CACHED_WEB_ACCESS_TOKEN = access_token
    SP_WEB_ACCESS_TOKEN_EXPIRES_AT = expires_at
    SP_CACHED_WEB_CLIENT_ID = client_id
    debug_print(f"Anonymous Spotify web-player token obtained successfully, token_len={len(access_token)}")
    verbose_print("Web-player metadata token refreshed")
    return {"access_token": access_token, "expires_at": expires_at, "client_id": client_id}


# Discovers and caches the playlist persisted-query hash from the current web-player bundle
def spotify_discover_playlist_query_hash(force=False):
    global SP_CACHED_PLAYLIST_QUERY_HASH

    if SP_CACHED_PLAYLIST_QUERY_HASH and not force:
        return SP_CACHED_PLAYLIST_QUERY_HASH

    headers = {"Accept": "text/html,application/xhtml+xml", "User-Agent": WEB_PLAYER_USER_AGENT}
    debug_print(f"HTTP GET {WEB_PLAYER_URL} [playlist query discovery] headers={sanitize_debug_headers(headers)}")
    response = SESSION.get(WEB_PLAYER_URL, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    debug_print(f"HTTP GET {WEB_PLAYER_URL} [playlist query discovery] -> {response.status_code}")
    response.raise_for_status()

    script_urls = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', response.text, flags=re.IGNORECASE)
    bundle_url = ""
    for script_url in script_urls:
        if re.search(r'/web-player/web-player\.[^/?]+\.js(?:\?|$)', script_url):
            bundle_url = urljoin(WEB_PLAYER_URL, script_url)
            break
    if not bundle_url:
        raise RuntimeError("Cannot find the Spotify web-player JavaScript bundle")

    debug_print(f"HTTP GET {bundle_url} [playlist query bundle]")
    bundle_response = SESSION.get(bundle_url, headers={"User-Agent": WEB_PLAYER_USER_AGENT}, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    debug_print(f"HTTP GET {bundle_url} [playlist query bundle] -> {bundle_response.status_code}")
    bundle_response.raise_for_status()

    hash_match = re.search(r'["\']fetchPlaylistContents["\']\s*,\s*["\']query["\']\s*,\s*["\']([0-9a-f]{64})["\']', bundle_response.text)
    if not hash_match:
        raise RuntimeError("Cannot find the playlist persisted-query hash in the Spotify web-player bundle")

    SP_CACHED_PLAYLIST_QUERY_HASH = hash_match.group(1)
    debug_print(f"Discovered Spotify playlist persisted-query hash from {bundle_url}")
    return SP_CACHED_PLAYLIST_QUERY_HASH


# Executes a Spotify web-player playlist query with automatic token and hash refresh
def spotify_web_playlist_query(operation_name, variables):
    global SP_CACHED_WEB_ACCESS_TOKEN, SP_WEB_ACCESS_TOKEN_EXPIRES_AT, SP_CACHED_WEB_CLIENT_ID, SP_CACHED_PLAYLIST_QUERY_HASH

    last_error = ""
    for attempt in range(2):
        token_data = spotify_get_web_access_token_data()
        query_hash = spotify_discover_playlist_query_hash(force=attempt > 0 and not SP_CACHED_PLAYLIST_QUERY_HASH)
        headers = {"Accept": "application/json", "App-Platform": "WebPlayer", "Authorization": f"Bearer {token_data['access_token']}", "Client-Id": token_data["client_id"], "Content-Type": "application/json", "User-Agent": WEB_PLAYER_USER_AGENT}
        payload = {"extensions": {"persistedQuery": {"sha256Hash": query_hash, "version": 1}}, "operationName": operation_name, "variables": variables}

        debug_print(f"HTTP POST {WEB_PLAYER_QUERY_URL} [web playlist operation={operation_name}] headers={sanitize_debug_headers(headers)}")
        response = SESSION.post(WEB_PLAYER_QUERY_URL, headers=headers, json=payload, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP POST {WEB_PLAYER_QUERY_URL} [web playlist operation={operation_name}] -> {response.status_code}")

        try:
            json_response = response.json()
        except ValueError:
            response.raise_for_status()
            raise RuntimeError(f"Spotify web-player playlist operation '{operation_name}' returned invalid JSON")

        errors = json_response.get("errors") if isinstance(json_response, dict) else None
        error_message = " | ".join(str(error.get("message", error)) if isinstance(error, dict) else str(error) for error in (errors or []))
        last_error = error_message or f"HTTP {response.status_code}"

        if response.status_code == 401 and attempt == 0:
            SP_CACHED_WEB_ACCESS_TOKEN = None
            SP_WEB_ACCESS_TOKEN_EXPIRES_AT = 0
            SP_CACHED_WEB_CLIENT_ID = ""
            debug_print("Anonymous web-player token was rejected, refreshing it once")
            continue

        if errors and attempt == 0 and any(marker in error_message.lower() for marker in ("persistedquery", "persisted query", "sha256")):
            SP_CACHED_PLAYLIST_QUERY_HASH = ""
            debug_print("Playlist persisted query was rejected, rediscovering its hash once")
            continue

        if errors:
            raise RuntimeError(f"Spotify web-player playlist operation '{operation_name}' failed: {error_message}")

        response.raise_for_status()
        data = json_response.get("data") if isinstance(json_response, dict) else None
        if not isinstance(data, dict):
            raise RuntimeError(f"Spotify web-player playlist operation '{operation_name}' returned no data")
        return data

    raise RuntimeError(f"Spotify web-player playlist operation '{operation_name}' failed after refresh: {last_error}")


# Fetches public playlist metadata from the Spotify web-player service
def spotify_get_web_playlist_metadata(playlist_uri):
    data = spotify_web_playlist_query("fetchPlaylistMetadata", {"enableWatchFeedEntrypoint": False, "uri": playlist_uri})
    playlist = data.get("playlistV2")
    if not isinstance(playlist, dict):
        raise PlaylistRestrictedError(f"Playlist is unavailable from the Spotify web-player service: {playlist_uri}")
    return playlist


# Normalizes one Spotify web-player playlist item to the legacy Web API shape
def spotify_normalize_web_playlist_item(item):
    if not isinstance(item, dict):
        return {"added_at": None, "added_by": {}, "track": None}

    added_at_data = item.get("addedAt") or {}
    added_by_data = (item.get("addedBy") or {}).get("data") or {}
    added_by_uri = added_by_data.get("uri", "") if isinstance(added_by_data, dict) else ""
    added_by_id = added_by_data.get("username", "") if isinstance(added_by_data, dict) else ""
    if not added_by_id and added_by_uri:
        added_by_id = added_by_uri.rsplit(":", 1)[-1]

    track_data = (item.get("itemV2") or {}).get("data") or {}
    if not isinstance(track_data, dict):
        track_data = {}

    artist_items = (track_data.get("artists") or {}).get("items") or []
    artists = []
    for artist in artist_items:
        if isinstance(artist, dict):
            profile = artist.get("profile") or {}
            artists.append({"name": profile.get("name", "") if isinstance(profile, dict) else "", "uri": artist.get("uri", "")})

    duration_data = track_data.get("trackDuration") or {}
    album_data = track_data.get("albumOfTrack") or {}
    cover_art = album_data.get("coverArt") or {} if isinstance(album_data, dict) else {}
    album_image_sources = cover_art.get("sources") or [] if isinstance(cover_art, dict) else []
    album_image_url = album_image_sources[0].get("url", "") if album_image_sources and isinstance(album_image_sources[0], dict) else ""
    normalized_track = None
    if track_data:
        normalized_track = {"album": {"images": [{"url": album_image_url}]} if album_image_url else {"images": []}, "artists": artists, "duration_ms": duration_data.get("totalMilliseconds") if isinstance(duration_data, dict) else None, "name": track_data.get("name", ""), "uri": track_data.get("uri", "")}

    return {"added_at": added_at_data.get("isoString") if isinstance(added_at_data, dict) else None, "added_by": {"display_name": added_by_data.get("name", "") if isinstance(added_by_data, dict) else "", "id": added_by_id, "uri": added_by_uri}, "track": normalized_track}


# Returns detailed public playlist information through Spotify's web-player service
def spotify_get_playlist_info_web(playlist_uri, get_tracks):
    metadata = spotify_get_web_playlist_metadata(playlist_uri)
    content = metadata.get("content") or {}
    total_raw = content.get("totalCount") if isinstance(content, dict) else None
    if total_raw is None:
        raise ValueError(f"Playlist's total tracks number is missing or malformed for {playlist_uri}")
    try:
        total_tracks = int(total_raw)
    except (TypeError, ValueError):
        raise ValueError(f"Playlist's total tracks number is missing or malformed for {playlist_uri}")

    revision_id = metadata.get("revisionId", "")

    # Skip track pagination when the caller only needs playlist metadata (mirrors the legacy Web API path,
    # which reports the raw total and no track list when get_tracks is False)
    if get_tracks:
        cached_revision = WEB_PLAYLIST_REVISION_CACHE.get(playlist_uri, {})
        if revision_id and cached_revision.get("revision_id") == revision_id and cached_revision.get("total_tracks") == total_tracks:
            normalized_items = cached_revision.get("items", [])
            cached_revision["timestamp"] = time.time()
            debug_print(f"spotify_get_playlist_info_web(): using cached revision for uri={playlist_uri}, revision_id={revision_id}")
        else:
            raw_items = []
            offset = 0
            while offset < total_tracks:
                variables = {"includeEpisodeContentRatingsV2": False, "limit": WEB_PLAYLIST_PAGE_LIMIT, "offset": offset, "uri": playlist_uri}
                page_data = spotify_web_playlist_query("fetchPlaylistContents", variables)
                page_playlist = page_data.get("playlistV2")
                if not isinstance(page_playlist, dict):
                    raise PlaylistRestrictedError(f"Playlist contents are unavailable from the Spotify web-player service: {playlist_uri}")
                page_content = page_playlist.get("content") or {}
                page_items = page_content.get("items") if isinstance(page_content, dict) else None
                if not isinstance(page_items, list) or not page_items:
                    raise RuntimeError(f"Spotify web-player returned incomplete playlist contents for {playlist_uri} at offset {offset}")
                page_total = page_content.get("totalCount") if isinstance(page_content, dict) else None
                if page_total is not None:
                    try:
                        total_tracks = int(page_total)
                    except (TypeError, ValueError):
                        raise ValueError(f"Playlist's paginated total tracks number is malformed for {playlist_uri}")
                raw_items.extend(page_items)
                offset += len(page_items)

            if len(raw_items) < total_tracks:
                raise RuntimeError(f"Spotify web-player returned {len(raw_items)} of {total_tracks} playlist items for {playlist_uri}")

            normalized_items = [spotify_normalize_web_playlist_item(item) for item in raw_items]
            if revision_id:
                WEB_PLAYLIST_REVISION_CACHE[playlist_uri] = {"items": normalized_items, "revision_id": revision_id, "total_tracks": total_tracks, "timestamp": time.time()}

        filtered_tracks = []
        for item in normalized_items:
            track_info = item.get("track") if isinstance(item, dict) else None
            if not isinstance(track_info, dict):
                continue
            artists = track_info.get("artists") or []
            artist_name = artists[0].get("name", "") if artists and isinstance(artists[0], dict) else ""
            track_name = track_info.get("name", "")
            if not artist_name or not track_name:
                continue
            duration_ms_value = track_info.get("duration_ms")
            if duration_ms_value is None:
                raise ValueError(f"Track '{track_name}' (URI: {track_info.get('uri', 'Unknown URI')}) in playlist {playlist_uri} has a missing or null duration (duration_ms)")
            try:
                duration_ms_int = int(duration_ms_value)
            except (TypeError, ValueError):
                raise ValueError(f"Track '{track_name}' (URI: {track_info.get('uri', 'Unknown URI')}) in playlist {playlist_uri} has an invalid, non-numeric duration_ms: '{duration_ms_value}'")
            if duration_ms_int >= 1000:
                filtered_tracks.append(item)
    else:
        normalized_items = []
        filtered_tracks = []

    owner_data = (metadata.get("ownerV2") or {}).get("data") or {}
    if not isinstance(owner_data, dict):
        raise ValueError("Playlist's owner data is missing or malformed")
    owner_uri = owner_data.get("uri", "")
    if not owner_uri:
        raise ValueError("Playlist's owner URI is missing or empty")

    image_items = (metadata.get("images") or {}).get("items") or []
    image_sources = image_items[0].get("sources", []) if image_items and isinstance(image_items[0], dict) else []
    image_url = image_sources[0].get("url", "") if image_sources and isinstance(image_sources[0], dict) else ""
    sharing_info = metadata.get("sharingInfo") or {}
    followers_raw = metadata.get("followers")
    try:
        followers_count = int(followers_raw) if followers_raw is not None else None
    except (TypeError, ValueError):
        followers_count = None

    tracks_count = len(filtered_tracks) if filtered_tracks else total_tracks
    tracks_count_before_filtering = len(normalized_items) if normalized_items else total_tracks
    attributes = metadata.get("attributes") or []
    collaborative = any("collaborative" in str(attribute).lower() for attribute in attributes)
    playlist_url = sharing_info.get("shareUrl") if isinstance(sharing_info, dict) else ""
    if not playlist_url:
        playlist_url = spotify_convert_uri_to_url(playlist_uri)

    debug_print(f"spotify_get_playlist_info_web(): uri={playlist_uri}, get_tracks={get_tracks}, revision_id={revision_id}, tracks={tracks_count}, tracks_raw={tracks_count_before_filtering}, followers={followers_count}")
    return {"sp_playlist_collaborative": collaborative, "sp_playlist_description": metadata.get("description", ""), "sp_playlist_followers_count": followers_count, "sp_playlist_image_url": image_url, "sp_playlist_name": metadata.get("name", ""), "sp_playlist_owner": owner_data.get("name", "") or owner_data.get("username", ""), "sp_playlist_owner_uri": owner_uri, "sp_playlist_owner_url": spotify_convert_uri_to_url(owner_uri), "sp_playlist_tracks": filtered_tracks, "sp_playlist_tracks_count": tracks_count, "sp_playlist_tracks_count_before_filtering": tracks_count_before_filtering, "sp_playlist_url": playlist_url}


# Checks if a playlist has been completely removed and/or set as private
def is_playlist_private(access_token, playlist_uri, oauth_app: bool = False):
    if TOKEN_SOURCE in {"cookie", "client"} and not oauth_app:
        if spotify_has_oauth_app_credentials():
            debug_print("is_playlist_private(): requesting oauth_app token for cookie/client legacy fallback")
            access_token = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
            oauth_app = True
        else:
            try:
                spotify_get_web_playlist_metadata(playlist_uri)
                return False
            except PlaylistRestrictedError:
                return True
            except Exception as e:
                debug_print(f"is_playlist_private(): web-player check failed for playlist_uri={playlist_uri}: {sanitize_error_text(e)}")
                return False
        if not access_token:
            debug_print("is_playlist_private(): missing oauth_app token, trying web-player metadata")
            try:
                spotify_get_web_playlist_metadata(playlist_uri)
                return False
            except PlaylistRestrictedError:
                return True
            except Exception:
                return False

    playlist_id = playlist_uri.split(':', 2)[2]
    url = f"{SPOTIFY_API_BASE_URL}/playlists/{quote(playlist_id, safe='')}?fields=id"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie" and not oauth_app:
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    try:
        debug_print(f"HTTP GET {url} [playlist private check] headers={sanitize_debug_headers(headers)}")
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP GET {url} [playlist private check] -> {response.status_code}")
        if response.status_code in {403, 404}:
            try:
                spotify_get_web_playlist_metadata(playlist_uri)
                debug_print(f"is_playlist_private(): playlist_uri={playlist_uri} is public through web-player metadata")
                return False
            except PlaylistRestrictedError:
                debug_print(f"is_playlist_private(): playlist_uri={playlist_uri} resolved as private/restricted")
                return True
            except Exception as e:
                debug_print(f"is_playlist_private(): web-player fallback failed for playlist_uri={playlist_uri}: {sanitize_error_text(e)}")
                return response.status_code == 404
        debug_print(f"is_playlist_private(): playlist_uri={playlist_uri} not private/restricted")
        return False
    except Exception as e:
        debug_print(f"is_playlist_private(): request failed for playlist_uri={playlist_uri}: {sanitize_error_text(e)}")
        return False


# Checks if a Spotify user ID has been deleted
def is_user_removed(access_token, user_uri_id, oauth_app: bool = False):
    # For oauth_app / oauth_user: use web scraping fallback (Client Credentials token cannot access user profile endpoints)
    # open.spotify.com/user/{id} returns 404 for removed users, no auth needed
    if TOKEN_SOURCE in {"oauth_app", "oauth_user"} or oauth_app:
        url = f"{SPOTIFY_WEB_BASE_URL}/user/{quote(user_uri_id, safe='')}"
        try:
            debug_print(f"HTTP HEAD {url} [user removed check]")
            response = req.head(url, timeout=FUNCTION_TIMEOUT, allow_redirects=True, verify=VERIFY_SSL)
            debug_print(f"HTTP HEAD {url} [user removed check] -> {response.status_code}")
            if response.status_code == 404:
                return True
            if response.status_code == 429:
                return False  # Rate limited, can't determine
            return False
        except Exception:
            return False

    # For cookie/client: use internal API (works with these token types)
    url = f"{SPOTIFY_PROFILE_API_BASE_URL}/{quote(user_uri_id, safe='')}?playlist_limit=0&artist_limit=0&episode_limit=0&market=from_token"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    alarm_state = _start_timeout_alarm(FUNCTION_TIMEOUT + 2)

    try:
        temp_session = req.Session()
        temp_session.headers.update(headers)

        debug_print(f"HTTP GET {url} [user removed check] headers={sanitize_debug_headers(headers)}")
        response = temp_session.get(url, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP GET {url} [user removed check] -> {response.status_code}")

        if response.status_code == 429:
            return False

        if response.status_code == 404:
            return True
        return False
    except TimeoutException:
        return False
    except req.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            return False
        elif e.response is not None and e.response.status_code == 404:
            return True
        return False
    except Exception:
        return False
    finally:
        _restore_timeout_alarm(alarm_state)


# Returns True if the access token owner's user ID matches the provided user_uri_id, False otherwise
def is_token_owner(access_token, user_uri_id) -> bool:
    # /v1/me is only reliable/usable for oauth_user now
    if TOKEN_SOURCE != "oauth_user":
        debug_print(f"is_token_owner(): skipped because TOKEN_SOURCE={TOKEN_SOURCE}")
        return False

    url = SPOTIFY_OAUTH_USER_URL

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    try:
        debug_print(f"HTTP GET {url} [token owner check] headers={sanitize_debug_headers(headers)}")
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP GET {url} [token owner check] -> {response.status_code}")
        response.raise_for_status()
        owner_match = response.json().get("id") == user_uri_id
        debug_print(f"is_token_owner(): requested_user={user_uri_id}, owner_match={owner_match}")
        return owner_match
    except Exception as e:
        debug_print(f"is_token_owner(): failed for user_uri_id={user_uri_id}: {sanitize_error_text(e)}")
        return False


# Returns detailed playlist information through the legacy Spotify Web API path
def _spotify_get_playlist_info_api(access_token, playlist_uri, get_tracks, oauth_app: bool = False):
    debug_print(f"_spotify_get_playlist_info_api(): uri={playlist_uri}, get_tracks={get_tracks}, token_source={TOKEN_SOURCE}, oauth_app_override={oauth_app}")
    if TOKEN_SOURCE in {"cookie", "client"} and not oauth_app:
        access_token = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
        oauth_app = True
        if not access_token:
            raise Exception("_spotify_get_playlist_info_api(): oauth_app token is missing")

    parts = playlist_uri.split(':')
    if len(parts) == 3:
        playlist_id = parts[2]
    else:
        playlist_id = "invalid_playlist"
        print(f"Invalid playlist format")

    if get_tracks:
        url1 = f"{SPOTIFY_API_BASE_URL}/playlists/{quote(playlist_id, safe='')}?fields=name,description,owner,followers,external_urls,tracks.total,collaborative,images"
        url2 = f"{SPOTIFY_API_BASE_URL}/playlists/{quote(playlist_id, safe='')}/tracks?fields=next,total,items(added_at,track(name,uri,duration_ms,album(images)),added_by),items(track(artists(name,uri)))"
    else:
        url1 = f"{SPOTIFY_API_BASE_URL}/playlists/{quote(playlist_id, safe='')}?fields=name,description,owner,followers,external_urls,tracks.total,images"
        url2 = f"{SPOTIFY_API_BASE_URL}/playlists/{quote(playlist_id, safe='')}/tracks?fields=next,total,items(added_at)"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie" and not oauth_app:
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })
    # Add si parameter so link opens in native Spotify app after clicking
    si = "?si=1"

    try:
        debug_print(f"HTTP GET {url1} [playlist info] headers={sanitize_debug_headers(headers)}")
        response1 = SESSION.get(url1, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP GET {url1} [playlist info] -> {response1.status_code}")
        if response1.status_code == 404:
            raise PlaylistRestrictedError(f"404 Not Found for playlist endpoint: {url1}")
        response1.raise_for_status()
        json_response1 = response1.json()

        sp_playlist_tracks_concatenated_list = []
        next_url = url2
        page_idx = 0
        while next_url:
            page_idx += 1
            debug_print(f"HTTP GET {next_url} [playlist tracks page={page_idx}] headers={sanitize_debug_headers(headers)}")
            response2 = SESSION.get(next_url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
            debug_print(f"HTTP GET {next_url} [playlist tracks page={page_idx}] -> {response2.status_code}")
            response2.raise_for_status()
            json_response2 = response2.json()

            for track in json_response2.get("items"):
                sp_playlist_tracks_concatenated_list.append(track)

            next_url = spotify_next_page_url(json_response2.get("next"), page_idx, "playlist tracks")

        sp_playlist_name = json_response1.get("name", "")

        # We fetch collaborative field for the future, for now it is always set to false by Spotify as a countermeasure against finding collaborative playlists by scraping
        sp_playlist_collaborative = json_response1.get("collaborative", False)

        sp_playlist_description = json_response1.get("description", "")

        owner_data = json_response1.get("owner")
        if not isinstance(owner_data, dict):
            raise ValueError("Playlist's owner data is missing or malformed")

        sp_playlist_owner = owner_data.get("display_name", "")

        sp_playlist_owner_uri = owner_data.get("uri")

        if not sp_playlist_owner_uri:
            raise ValueError(f"Playlist's owner URI is missing or empty")

        sp_playlist_owner_url = (owner_data.get("external_urls") or {}).get("spotify")

        sp_playlist_image_url = (json_response1.get("images") or [{}])[0].get("url")

        sp_playlist_tracks = sp_playlist_tracks_concatenated_list

        # Support both old ('tracks') and new ('items') field names (Spotify Mar 2026 API change)
        tracks_metadata = json_response1.get("items") or json_response1.get("tracks")
        if not isinstance(tracks_metadata, dict):
            raise ValueError("Playlist's tracks metadata is missing or malformed")

        total_tracks_from_api = tracks_metadata.get("total")

        if total_tracks_from_api is None:
            raise ValueError("Playlist's total tracks number is missing or malformed")

        sp_playlist_tracks_count = sp_playlist_tracks_count_before_filtering = int(total_tracks_from_api)

        if sp_playlist_tracks:
            sp_playlist_tracks_count_before_filtering_tmp = len(sp_playlist_tracks)
            if sp_playlist_tracks_count_before_filtering_tmp > 0:
                sp_playlist_tracks_count_before_filtering = sp_playlist_tracks_count_before_filtering_tmp

        # Filtering of unavailable tracks for example due to copyright issues
        filtered_tracks_list = []

        for t_item in sp_playlist_tracks_concatenated_list:
            track_info = t_item.get("track")

            if not isinstance(track_info, dict):
                continue

            artist_name = (track_info.get("artists", [{}]) or [{}])[0].get("name", "")
            track_name = track_info.get("name", "")

            if not (artist_name and track_name):
                continue

            duration_ms_value = track_info.get("duration_ms")

            if duration_ms_value is None:
                raise ValueError(f"Track '{track_name if track_name else 'Unknown Track'}' (URI: {track_info.get('uri', 'Unknown URI')}) in playlist {playlist_id} has a missing or null duration (duration_ms)")

            try:
                duration_ms_int = int(duration_ms_value)
            except (ValueError, TypeError):
                raise ValueError(f"Track '{track_name if track_name else 'Unknown Track'}' (URI: {track_info.get('uri', 'Unknown URI')}) in playlist {playlist_id} has an invalid, non-numeric duration_ms: '{duration_ms_value}'")

            if duration_ms_int >= 1000:
                filtered_tracks_list.append(t_item)

        sp_playlist_tracks = filtered_tracks_list

        if sp_playlist_tracks:
            sp_playlist_tracks_count_tmp = len(sp_playlist_tracks)
            if sp_playlist_tracks_count_tmp > 0:
                sp_playlist_tracks_count = sp_playlist_tracks_count_tmp

        followers_data = json_response1.get("followers")
        total_followers_from_api = followers_data.get("total") if isinstance(followers_data, dict) else None

        sp_playlist_followers_count = None
        if total_followers_from_api is not None:
            try:
                sp_playlist_followers_count = int(total_followers_from_api)
            except (TypeError, ValueError):
                sp_playlist_followers_count = None

        if sp_playlist_followers_count is None:
            debug_print(f"_spotify_get_playlist_info_api(): followers count unavailable for uri={playlist_uri}, using n/a")

        sp_playlist_url = (json_response1.get("external_urls") or {}).get("spotify")
        if sp_playlist_url:
            sp_playlist_url += si

        debug_print(
            f"_spotify_get_playlist_info_api(): uri={playlist_uri}, name={sp_playlist_name!r}, "
            f"tracks={sp_playlist_tracks_count}, tracks_raw={sp_playlist_tracks_count_before_filtering}, "
            f"followers={sp_playlist_followers_count}"
        )

        return {"sp_playlist_name": sp_playlist_name, "sp_playlist_collaborative": sp_playlist_collaborative, "sp_playlist_description": sp_playlist_description, "sp_playlist_owner": sp_playlist_owner, "sp_playlist_owner_url": sp_playlist_owner_url, "sp_playlist_tracks_count": sp_playlist_tracks_count, "sp_playlist_tracks_count_before_filtering": sp_playlist_tracks_count_before_filtering, "sp_playlist_tracks": sp_playlist_tracks, "sp_playlist_followers_count": sp_playlist_followers_count, "sp_playlist_url": sp_playlist_url, "sp_playlist_owner_uri": sp_playlist_owner_uri, "sp_playlist_image_url": sp_playlist_image_url}

    except Exception as e:
        debug_print(f"_spotify_get_playlist_info_api(): failed for uri={playlist_uri}: {sanitize_error_text(e)}")
        raise


# Decides whether to latch the web-player backend after a legacy Web API failure
def spotify_should_latch_web_backend(error, consecutive_failures):
    status_code = error.response.status_code if isinstance(error, req.HTTPError) and error.response is not None else None
    # A 403 signals an app-level restriction (the whole legacy path is unavailable) so latch immediately; an
    # individual restricted playlist (404 / PlaylistRestrictedError) must not switch the backend for every
    # playlist, so it only contributes to the consecutive-failure threshold below
    if status_code == 403:
        return True
    return consecutive_failures >= METADATA_API_FAILURE_LATCH_THRESHOLD


# Records which backend produced a playlist snapshot so change detection can ignore backend switches
def spotify_tag_playlist_source(playlist_data, source):
    if isinstance(playlist_data, dict):
        playlist_data["sp_playlist_source"] = source
    return playlist_data


# Selects the legacy or web-player playlist backend and falls back automatically
def spotify_get_playlist_info(access_token, playlist_uri, get_tracks, oauth_app: bool = False):
    global SP_WEB_PLAYLIST_BACKEND_PREFERRED, SP_WEB_PLAYLIST_API_FAILURES

    api_available = TOKEN_SOURCE in {"oauth_app", "oauth_user"} or oauth_app or spotify_has_oauth_app_credentials()
    api_error = None
    web_error = None

    if api_available and not SP_WEB_PLAYLIST_BACKEND_PREFERRED:
        try:
            result = _spotify_get_playlist_info_api(access_token, playlist_uri, get_tracks, oauth_app)
            SP_WEB_PLAYLIST_API_FAILURES = 0
            return spotify_tag_playlist_source(result, "api")
        except Exception as e:
            api_error = e
            SP_WEB_PLAYLIST_API_FAILURES += 1
            if spotify_should_latch_web_backend(e, SP_WEB_PLAYLIST_API_FAILURES):
                SP_WEB_PLAYLIST_BACKEND_PREFERRED = True
                status_code = e.response.status_code if isinstance(e, req.HTTPError) and e.response is not None else None
                debug_print(f"spotify_get_playlist_info(): legacy Web API unavailable (failures={SP_WEB_PLAYLIST_API_FAILURES}, status={status_code}), preferring web-player backend for remaining playlists")
                verbose_print("Playlist metadata switched to the web-player backend after legacy API failures")
            else:
                debug_print(f"spotify_get_playlist_info(): legacy Web API backend failed for uri={playlist_uri} (failures={SP_WEB_PLAYLIST_API_FAILURES}): {sanitize_error_text(e)}")

    try:
        return spotify_tag_playlist_source(spotify_get_playlist_info_web(playlist_uri, get_tracks), "web")
    except Exception as e:
        web_error = e
        debug_print(f"spotify_get_playlist_info(): web-player backend failed for uri={playlist_uri}: {sanitize_error_text(e)}")

    if api_available and (SP_WEB_PLAYLIST_BACKEND_PREFERRED or api_error is None):
        try:
            return spotify_tag_playlist_source(_spotify_get_playlist_info_api(access_token, playlist_uri, get_tracks, oauth_app), "api")
        except Exception as e:
            api_error = e
            debug_print(f"spotify_get_playlist_info(): legacy Web API fallback failed for uri={playlist_uri}: {sanitize_error_text(e)}")

    if isinstance(web_error, PlaylistRestrictedError):
        raise web_error
    if api_error is not None and web_error is not None:
        raise RuntimeError(f"Both Spotify playlist backends failed for {playlist_uri}: Web API: {api_error}. Web player: {web_error}")
    if web_error is not None:
        raise web_error
    if api_error is not None:
        raise api_error
    raise RuntimeError(f"No Spotify playlist backend is available for {playlist_uri}")


# Returns detailed info about user with specified URI
def spotify_get_user_info(access_token, user_uri_id, get_playlists, recently_played_limit):
    # URL used for cookie and client token sources
    url1 = f"{SPOTIFY_PROFILE_API_BASE_URL}/{quote(user_uri_id, safe='')}?playlist_limit={PLAYLISTS_LIMIT if get_playlists else 0}&artist_limit={recently_played_limit}&episode_limit=10&market=from_token"

    # URLs used for oauth_app & oauth_user token sources
    url2 = f"{SPOTIFY_API_BASE_URL}/users/{quote(user_uri_id, safe='')}"
    url2_pl = f"{SPOTIFY_API_BASE_URL}/users/{quote(user_uri_id, safe='')}/playlists?limit={PLAYLISTS_LIMIT if get_playlists else 0}"

    def _rq(url: str, **kw) -> dict:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": USER_AGENT,
            **kw.pop("extra_headers", {})
        }
        if TOKEN_SOURCE == "cookie":
            headers["Client-Id"] = SP_CACHED_CLIENT_ID
        debug_print(f"HTTP GET {url} [user info] headers={sanitize_debug_headers(headers)}")
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL, **kw)
        debug_print(f"HTTP GET {url} [user info] -> {response.status_code}")
        response.raise_for_status()
        return response.json()

    def _trim(items: list[dict], keys=("is_following",)) -> list[dict]:
        if isinstance(items, list):
            for d in items:
                for k in keys:
                    d.pop(k, None)
        return items or []

    def _safe_int(raw, field: str) -> int:
        if raw is None:
            return 0
        try:
            return int(raw)
        except (ValueError, TypeError):
            raise ValueError(f"User {user_uri_id} {field} count ('{raw}') is not a valid integer")

    out = {
        "sp_username": "",
        "sp_user_followers_count": 0,
        "sp_user_followers_count_available": False,
        "sp_user_show_follows": None,
        "sp_user_followings_count": 0,
        "sp_user_public_playlists_count": 0,
        "sp_user_public_playlists_uris": [],
        "sp_user_recently_played_artists": [],
        "sp_user_image_url": ""
    }

    if TOKEN_SOURCE in {"cookie", "client"}:

        json_response = _rq(url1)

        out.update({
            "sp_username": json_response.get("name", ""),
            "sp_user_followers_count": _safe_int(json_response.get("followers_count"), "followers"),
            "sp_user_followers_count_available": json_response.get("followers_count") is not None,
            "sp_user_show_follows": json_response.get("show_follows"),
            "sp_user_followings_count": _safe_int(json_response.get("following_count"), "followings"),
            "sp_user_image_url": json_response.get("image_url", "")
        })

        if get_playlists:
            raw_playlist_data_from_api = json_response.get("public_playlists")
            current_list_to_process = raw_playlist_data_from_api if isinstance(raw_playlist_data_from_api, list) else []

            if not GET_ALL_PLAYLISTS:
                current_list_to_process = [d for d in current_list_to_process if isinstance(d, dict) and d.get("owner_uri") == f"spotify:user:{user_uri_id}"]

            actual_processed_playlists = [d for d in current_list_to_process if isinstance(d, dict)]

            trimmed_playlists = _trim(actual_processed_playlists)

            out["sp_user_public_playlists_uris"] = trimmed_playlists
            out["sp_user_public_playlists_count"] = len(trimmed_playlists)

        raw_artists = json_response.get("recently_played_artists")
        artists_data = raw_artists if isinstance(raw_artists, list) else []
        for d in artists_data:
            if isinstance(d, dict):
                d.pop("image_url", None)
                d.pop("followers_count", None)
        out["sp_user_recently_played_artists"] = artists_data

    else:  # oauth tokens
        is_self = TOKEN_SOURCE == "oauth_user" and is_token_owner(access_token, user_uri_id)

        if is_self:
            # oauth_user monitoring self: use /me endpoints (still available for authenticated users)
            url_me = SPOTIFY_OAUTH_USER_URL
            url_me_playlists = f"{SPOTIFY_API_BASE_URL}/me/playlists?limit={PLAYLISTS_LIMIT if get_playlists else 0}"

            json_response = _rq(url_me)

            followers_data = json_response.get("followers") or {}
            followers_total = followers_data.get("total")

            out.update({
                "sp_username": json_response.get("display_name", ""),
                # followers field removed in Mar 2026, handle gracefully
                "sp_user_followers_count": _safe_int(followers_total, "followers"),
                "sp_user_followers_count_available": followers_total is not None,
                "sp_user_image_url": (json_response.get("images") or [{}])[0].get("url", "")
            })

            if get_playlists:
                playlist_page_idx = 0
                while url_me_playlists:
                    playlist_page_idx += 1
                    json_response = _rq(url_me_playlists)
                    raw_playlist_data_from_api = json_response.get("items")
                    current_list_to_process = raw_playlist_data_from_api if isinstance(raw_playlist_data_from_api, list) else []
                    out["sp_user_public_playlists_uris"].extend({"image_url": (p.get("images") or [{}])[0].get("url", ""), "uri": p.get("uri"), "owner_uri": p.get("owner", {}).get("uri")} for p in current_list_to_process if isinstance(p, dict) and (GET_ALL_PLAYLISTS or p.get("owner", {}).get("uri") == f"spotify:user:{user_uri_id}"))
                    url_me_playlists = spotify_next_page_url(json_response.get("next"), playlist_page_idx, "own playlists")
                out["sp_user_public_playlists_count"] = len(out["sp_user_public_playlists_uris"])

        else:
            # oauth_app or oauth_user monitoring others: try existing endpoints
            # Note: GET /users/{id} and GET /users/{id}/playlists are not accessible with Client Credentials (oauth_app) token
            try:
                json_response = _rq(url2)

                followers_data = json_response.get("followers") or {}
                followers_total = followers_data.get("total")

                out.update({
                    "sp_username": json_response.get("display_name", ""),
                    "sp_user_followers_count": _safe_int(followers_total, "followers"),
                    "sp_user_followers_count_available": followers_total is not None,
                    "sp_user_image_url": (json_response.get("images") or [{}])[0].get("url", "")
                })

                if get_playlists:
                    playlist_page_idx = 0
                    while url2_pl:
                        playlist_page_idx += 1
                        json_response = _rq(url2_pl)
                        raw_playlist_data_from_api = json_response.get("items")
                        current_list_to_process = raw_playlist_data_from_api if isinstance(raw_playlist_data_from_api, list) else []
                        out["sp_user_public_playlists_uris"].extend({"image_url": (p.get("images") or [{}])[0].get("url", ""), "uri": p.get("uri"), "owner_uri": p.get("owner", {}).get("uri")} for p in current_list_to_process if isinstance(p, dict) and (GET_ALL_PLAYLISTS or p.get("owner", {}).get("uri") == f"spotify:user:{user_uri_id}"))
                        url2_pl = spotify_next_page_url(json_response.get("next"), playlist_page_idx, "user playlists")
                    out["sp_user_public_playlists_count"] = len(out["sp_user_public_playlists_uris"])

            except req.HTTPError as e:
                if e.response is not None and e.response.status_code in {403, 404}:
                    # oauth_app (Client Credentials) does not have permission to access user profile endpoints
                    print(f"\n* Warning: Cannot fetch profile for user '{user_uri_id}' with {TOKEN_SOURCE} token source")
                    print("* GET /users/{{id}} and GET /users/{{id}}/playlists are not accessible with Client Credentials (oauth_app) token")
                    print("* To monitor other users, use 'cookie' or 'client' token source (with oauth_app hybrid)")
                    print("* If you're using oauth_user to monitor your own account, ensure the Spotify user ID matches your account\n")
                    raise ValueError(f"Cannot monitor user '{user_uri_id}' with '{TOKEN_SOURCE}' token source. Use 'cookie' or 'client' token source for monitoring other users.")
                raise

        # Recently played artists (only for oauth_user monitoring self)
        artists_data = []
        if TOKEN_SOURCE == "oauth_user" and recently_played_limit > 0 and is_self:
            days_back = 7
            url3 = f"{SPOTIFY_API_BASE_URL}/me/player/recently-played?limit={recently_played_limit}&after={int((now_local() - timedelta(days=days_back)).timestamp() * 1000)}"
            json_response = _rq(url3)

            for item in json_response.get("items", []) or []:
                for artist in item.get("track", {}).get("artists", []) or []:
                    if isinstance(artist, dict):
                        artists_data.append({"name": artist.get("name"), "uri": artist.get("uri")})
            seen = set()
            unique = []
            for a in artists_data:
                if a["uri"] not in seen:
                    seen.add(a["uri"])
                    unique.append(a)
            artists_data = unique[:recently_played_limit]

        out["sp_user_recently_played_artists"] = artists_data

    return out


# Returns followings for user with specified URI
def spotify_get_user_followings(access_token, user_uri_id):
    if TOKEN_SOURCE == "oauth_app":
        return {"sp_user_followings": []}

    if TOKEN_SOURCE == "oauth_user":
        if is_token_owner(access_token, user_uri_id):
            headers = {"Authorization": f"Bearer {access_token}", "User-Agent": USER_AGENT}
            all_artists = []
            after = None
            while True:
                params = {"type": "artist", "limit": 50}
                if after:
                    params["after"] = after
                response = SESSION.get(f"{SPOTIFY_API_BASE_URL}/me/following", headers=headers, params=params, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
                debug_print(f"HTTP GET {SPOTIFY_API_BASE_URL}/me/following [followings] -> {response.status_code}")
                response.raise_for_status()
                data = response.json().get("artists", {})
                items = data.get("items", []) or []
                for a in items:
                    if isinstance(a, dict):
                        all_artists.append({"name": a.get("name"), "uri": a.get("uri")})
                after = data.get("cursors", {}).get("after")
                if not after:
                    break
            return {"sp_user_followings": all_artists}
        else:
            return {"sp_user_followings": []}

    url = f"{SPOTIFY_PROFILE_API_BASE_URL}/{quote(user_uri_id, safe='')}/following?market=from_token"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    try:
        debug_print(f"HTTP GET {url} [followings] headers={sanitize_debug_headers(headers)}")
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP GET {url} [followings] -> {response.status_code}")
        response.raise_for_status()
        json_response = response.json()

        sp_user_followings = json_response.get("profiles", None)

        if sp_user_followings:
            remove_key_from_list_of_dicts(sp_user_followings, 'image_url')
            remove_key_from_list_of_dicts(sp_user_followings, 'followers_count')
            remove_key_from_list_of_dicts(sp_user_followings, 'following_count')
            remove_key_from_list_of_dicts(sp_user_followings, 'color')
            remove_key_from_list_of_dicts(sp_user_followings, 'is_following')

        return {"sp_user_followings": sp_user_followings}
    except Exception:
        raise


# Returns followers for user with specified URI
def spotify_get_user_followers(access_token, user_uri_id):
    if TOKEN_SOURCE not in {"cookie", "client"}:
        return {"sp_user_followers": []}

    url = f"{SPOTIFY_PROFILE_API_BASE_URL}/{quote(user_uri_id, safe='')}/followers?market=from_token"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    try:
        debug_print(f"HTTP GET {url} [followers] headers={sanitize_debug_headers(headers)}")
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP GET {url} [followers] -> {response.status_code}")
        response.raise_for_status()
        json_response = response.json()

        sp_user_followers = json_response.get("profiles", None)
        if sp_user_followers:
            remove_key_from_list_of_dicts(sp_user_followers, 'image_url')
            remove_key_from_list_of_dicts(sp_user_followers, 'followers_count')
            remove_key_from_list_of_dicts(sp_user_followers, 'following_count')
            remove_key_from_list_of_dicts(sp_user_followers, 'color')
            remove_key_from_list_of_dicts(sp_user_followers, 'is_following')

        return {"sp_user_followers": sp_user_followers}
    except Exception:
        raise


# Lists tracks for playlist with specified URI (-l flag)
def spotify_list_tracks_for_playlist(sp_accessToken, playlist_url, csv_file_name, format_type=2):
    added_at_dt: Optional[datetime] = None

    try:
        if csv_file_name:
            init_csv_file(csv_file_name, format_type)
    except Exception as e:
        print_operation_error("The CSV output could not be initialized", e)

    if not CLEAN_OUTPUT and not EXPORT_ALL:
        list_operation = "* Listing & saving" if csv_file_name else "* Listing"
        print(f"{list_operation} tracks for playlist '{playlist_url}' ...\n")

    user_id_name_mapping = {}
    user_track_counts = Counter()
    unknown_added_by_tracks = 0

    pattern = re.compile(r'^[a-zA-Z0-9]{22}$')
    if (pattern.match(playlist_url)):
        playlist_uri = f"spotify:playlist:{playlist_url}"
    else:
        playlist_uri = spotify_convert_url_to_uri(playlist_url)

    if not playlist_uri:
        raise ValueError(PLAYLIST_INPUT_ERROR)

    sp_playlist_data = spotify_get_playlist_info(sp_accessToken, playlist_uri, True)

    p_name = sp_playlist_data.get("sp_playlist_name", "")
    p_descr = html.unescape(sp_playlist_data.get("sp_playlist_description", ""))
    p_owner = sp_playlist_data.get("sp_playlist_owner", "")
    p_owner_uri = sp_playlist_data.get("sp_playlist_owner_uri", "")
    p_owner_id = spotify_extract_id_or_name(p_owner_uri) if p_owner_uri else ""

    p_image_url = sp_playlist_data.get("sp_playlist_image_url", "")

    if not CLEAN_OUTPUT and not EXPORT_ALL:
        print(f"Playlist '{p_name}' owned by '{p_owner}':\n")

    p_likes = sp_playlist_data.get("sp_playlist_followers_count")
    p_tracks = sp_playlist_data.get("sp_playlist_tracks_count", 0)
    p_tracks_before_filtering = sp_playlist_data.get("sp_playlist_tracks_count_before_filtering", 0)
    p_tracks_list = sp_playlist_data.get("sp_playlist_tracks", None)
    added_at_ts_lowest = 0
    added_at_ts_highest = 0
    duration_sum = 0
    tracks_list = []

    if p_tracks_list is not None:
        for index, track in enumerate(p_tracks_list or []):
            track_info = track.get("track")
            p_artist = track_info["artists"][0]["name"]
            p_track = track_info["name"]
            duration_ms = track_info["duration_ms"]

            artist_track = f"{p_artist} - {p_track}"
            duration = int(str(duration_ms)[0:-3])
            duration_sum += duration

            added_at_dt = convert_iso_str_to_datetime(track.get("added_at"))

            added_by = track.get("added_by", {}) or {}
            added_by_id = (added_by.get("id") or "").strip()

            # Some tracks may have missing `added_by` due to Spotify API quirks
            # For Spotify-owned playlists, treating it as "Spotify" gives better UX, for non-Spotify-owned playlists,
            # treat as unknown and exclude from collaborator list/count to avoid false positives
            if not added_by_id:
                if p_owner_id.lower() == "spotify":
                    added_by_id = "spotify"
                else:
                    unknown_added_by_tracks += 1
                    added_by_id = "unknown"

            added_by_name = user_id_name_mapping.get(added_by_id)
            if not added_by_name:
                if added_by_id == "spotify":
                    added_by_name = "Spotify"
                elif added_by_id == "unknown":
                    added_by_name = "Unknown"
                else:
                    sp_user_data = spotify_get_user_info(sp_accessToken, added_by_id, False, 0)
                    added_by_name = sp_user_data.get("sp_username", added_by_id)

                # Exclude unknown from collaborator mapping to keep collaborator counts stable.
                if added_by_id != "unknown":
                    user_id_name_mapping[added_by_id] = added_by_name

            if not added_by_name:
                added_by_name = added_by_id

            user_track_counts[added_by_id] += 1

            if added_at_dt:
                added_at_dt_ts = int(added_at_dt.timestamp())
                if index == 0:
                    added_at_ts_lowest = added_at_dt_ts
                    added_at_ts_highest = added_at_dt_ts
                if added_at_dt_ts < added_at_ts_lowest:
                    added_at_ts_lowest = added_at_dt_ts
                if added_at_dt_ts > added_at_ts_highest:
                    added_at_ts_highest = added_at_dt_ts
                added_at_dt_str = get_short_date_from_ts(added_at_dt, show_weekday=False, show_seconds=True, always_show_year=True)
                added_at_dt_week_day = calendar.day_abbr[added_at_dt.weekday()]
                if not CLEAN_OUTPUT and not EXPORT_ALL:
                    artist_track = artist_track[:75]
                    line_new = '%75s    %20s    %3s     %10s' % (artist_track, added_at_dt_str, added_at_dt_week_day, added_by_name)
                else:
                    line_new = f"{artist_track}"
                    tracks_list.append(line_new)
                if not EXPORT_ALL:
                    print(line_new)

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, convert_to_local_naive(added_at_dt), *(("Added Track", p_name, added_by_name, artist_track) if format_type == 1 else ("", p_name, p_artist, p_track)), format_type)
                except Exception as e:
                    print_operation_error("A CSV event could not be written", e)

    if not CLEAN_OUTPUT and not EXPORT_ALL:
        print(f"\nName:\t\t\t'{p_name}'")
        if p_descr:
            print(f"Description:\t\t'{p_descr}'")

        songs_display = f"{p_tracks} ({p_tracks_before_filtering - p_tracks} filtered out)" if p_tracks_before_filtering > p_tracks else f"{p_tracks}"

        likes_display = p_likes if p_likes is not None else "n/a"
        print(f"URL:\t\t\t{playlist_url}\nSongs:\t\t\t{songs_display}\nLikes:\t\t\t{likes_display}")

        if added_at_ts_lowest > 0:
            p_creation_date = get_date_from_ts(int(added_at_ts_lowest))
            p_creation_date_since = calculate_timespan(int(time.time()), int(added_at_ts_lowest))
            print(f"Creation date:\t\t{p_creation_date} ({p_creation_date_since} ago)")

        if added_at_ts_highest > 0:
            p_last_track_date = get_date_from_ts(int(added_at_ts_highest))
            p_last_track_date_since = calculate_timespan(int(time.time()), int(added_at_ts_highest))
            print(f"Last update:\t\t{p_last_track_date} ({p_last_track_date_since} ago)")

        print(f"Duration:\t\t{display_time(duration_sum)}")
    else:
        try:
            if CLEAN_OUTPUT and csv_file_name:
                with open(csv_file_name, "w") as file:
                    file.writelines([track + '\n' for track in tracks_list])
        except Exception as e:
            print_operation_error(f"Output file '{csv_file_name}' could not be written", e)

    if p_image_url and not CLEAN_OUTPUT and not EXPORT_ALL:
        # print(f"Playlist artwork URL:\t{p_image_url}")
        print(f"Playlist artwork:\t", end="")

        display_tmp_pic(p_image_url, f"spotify_{playlist_uri}_playlist_pic_tmp.jpeg", imgcat_exe, False)

        total_tracks = sum(user_track_counts.values())

        if len(user_id_name_mapping) > 1:

            print(f"\nCollaborators ({len(user_id_name_mapping)}):\n")

            for collab_id, collab_name in user_id_name_mapping.items():
                count = user_track_counts.get(collab_id, 0)
                percent = (count / total_tracks * 100) if total_tracks else 0
                url = spotify_convert_uri_to_url(f"spotify:user:{collab_id}")
                print(f"- {collab_name} [songs: {count}, {percent:.1f}%] [URL: {url}]")

        # if unknown_added_by_tracks > 0:
        #     print(f"\nNote: {unknown_added_by_tracks} track(s) had missing added_by info from Spotify API - excluded from collaborator list/count")


# Returns detailed information about tracks liked by the user owning the access token
def spotify_get_user_liked_tracks(access_token):
    url = f"{SPOTIFY_API_BASE_URL}/me/tracks?fields=next,total,items(added_at,track(name,uri,duration_ms),added_by),items(track(artists(name,uri)))"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    try:
        sp_playlist_tracks_concatenated_list = []
        json_response: dict = {}
        next_url = url
        page_idx = 0

        while next_url:
            page_idx += 1
            debug_print(f"HTTP GET {next_url} [liked tracks] headers={sanitize_debug_headers(headers)}")
            response = SESSION.get(next_url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
            debug_print(f"HTTP GET {next_url} [liked tracks] -> {response.status_code}")
            response.raise_for_status()
            json_response = response.json()

            for track in json_response.get("items", []):
                sp_playlist_tracks_concatenated_list.append(track)

            next_url = spotify_next_page_url(json_response.get("next"), page_idx, "liked tracks")

        sp_playlist_tracks = sp_playlist_tracks_concatenated_list

        sp_playlist_tracks_count = sp_playlist_tracks_count_before_filtering = json_response.get("total", 0)
        if sp_playlist_tracks:
            sp_playlist_tracks_count_before_filtering_tmp = len(sp_playlist_tracks)
            if sp_playlist_tracks_count_before_filtering_tmp > 0:
                sp_playlist_tracks_count_before_filtering = sp_playlist_tracks_count_before_filtering_tmp

        # Filtering of unavailable tracks for example due to copyright issues
        sp_playlist_tracks = [t for t in (sp_playlist_tracks or []) if t.get("track") and t["track"].get("artists", [{}])[0].get("name", "") and t["track"].get("name", "") and int(t["track"].get("duration_ms", 0)) >= 1000]

        if sp_playlist_tracks:
            sp_playlist_tracks_count_tmp = len(sp_playlist_tracks)
            if sp_playlist_tracks_count_tmp > 0:
                sp_playlist_tracks_count = sp_playlist_tracks_count_tmp

        return {"sp_playlist_tracks_count": sp_playlist_tracks_count, "sp_playlist_tracks_count_before_filtering": sp_playlist_tracks_count_before_filtering, "sp_playlist_tracks": sp_playlist_tracks}

    except Exception:
        raise


# Lists liked tracks by the user owning the access token
def spotify_list_liked_tracks(sp_accessToken, csv_file_name, format_type=2):
    added_at_dt: Optional[datetime] = None
    username = ""

    try:
        if csv_file_name:
            init_csv_file(csv_file_name, format_type)
    except Exception as e:
        print_operation_error("The CSV output could not be initialized", e)

    if not CLEAN_OUTPUT:
        list_operation = "* Listing & saving" if csv_file_name else "* Listing"
        print(f"{list_operation} liked tracks for the user owning the token ...\n")

    sp_playlist_data = spotify_get_user_liked_tracks(sp_accessToken)

    p_tracks = sp_playlist_data.get("sp_playlist_tracks_count", 0)
    p_tracks_before_filtering = sp_playlist_data.get("sp_playlist_tracks_count_before_filtering", 0)
    p_tracks_list = sp_playlist_data.get("sp_playlist_tracks", None)
    added_at_ts_lowest = 0
    added_at_ts_highest = 0
    duration_sum = 0
    tracks_list = []

    if p_tracks_list is not None:
        for index, track in enumerate(reversed(p_tracks_list or [])):
            track_info = track.get("track")

            p_artist = track_info["artists"][0]["name"]
            p_track = track_info["name"]
            duration_ms = track_info["duration_ms"]

            artist_track = f"{p_artist} - {p_track}"
            duration = int(str(duration_ms)[0:-3])
            duration_sum = duration_sum + duration
            added_at_dt = convert_iso_str_to_datetime(track.get("added_at"))

            if added_at_dt:
                added_at_dt_ts = int(added_at_dt.timestamp())
                if index == 0:
                    added_at_ts_lowest = added_at_dt_ts
                    added_at_ts_highest = added_at_dt_ts
                if added_at_dt_ts < added_at_ts_lowest:
                    added_at_ts_lowest = added_at_dt_ts
                if added_at_dt_ts > added_at_ts_highest:
                    added_at_ts_highest = added_at_dt_ts
                added_at_dt_str = get_short_date_from_ts(added_at_dt, show_weekday=False, show_seconds=True, always_show_year=True)
                added_at_dt_week_day = calendar.day_abbr[added_at_dt.weekday()]
                if not CLEAN_OUTPUT:
                    artist_track = artist_track[:75]
                    line_new = '%80s    %20s    %3s' % (artist_track, added_at_dt_str, added_at_dt_week_day)
                else:
                    line_new = f"{artist_track}"
                    tracks_list.append(line_new)
                print(line_new)
                try:
                    if csv_file_name and not CLEAN_OUTPUT:
                        write_csv_entry(csv_file_name, convert_to_local_naive(added_at_dt), *(("Added Track", "Liked Songs", username, artist_track) if format_type == 1 else ("", "Liked Songs", p_artist, p_track)), format_type)
                except Exception as e:
                    print_operation_error("A CSV event could not be written", e)

    if not CLEAN_OUTPUT:
        songs_display = f"{p_tracks} ({p_tracks_before_filtering - p_tracks} filtered out)" if p_tracks_before_filtering > p_tracks else f"{p_tracks}"

        print(f"Songs:\t\t\t{songs_display}")

        if added_at_ts_lowest > 0:
            p_creation_date = get_date_from_ts(int(added_at_ts_lowest))
            p_creation_date_since = calculate_timespan(int(time.time()), int(added_at_ts_lowest))
            print(f"Creation date:\t\t{p_creation_date} ({p_creation_date_since} ago)")

        if added_at_ts_highest > 0:
            p_last_track_date = get_date_from_ts(int(added_at_ts_highest))
            p_last_track_date_since = calculate_timespan(int(time.time()), int(added_at_ts_highest))
            print(f"Last update:\t\t{p_last_track_date} ({p_last_track_date_since} ago)")

        print(f"Duration:\t\t{display_time(duration_sum)}")
    else:
        try:
            if CLEAN_OUTPUT and csv_file_name:
                with open(csv_file_name, "w") as file:
                    file.writelines([track + '\n' for track in tracks_list])
        except Exception as e:
            print_operation_error(f"Output file '{csv_file_name}' could not be written", e)


# Builds one hashable signature for a dictionary so list differences can use set lookups instead of linear scans
def dict_signature(item):
    if isinstance(item, dict):
        return tuple(sorted((str(key), repr(value)) for key, value in item.items()))
    return (repr(item),)


# Returns the entries of the first list that are absent from the second, preserving their order and duplicates
def compare_two_lists_of_dicts(list1: list, list2: list):
    if not list1:
        return []
    if not list2:
        return list(list1)

    signatures = {dict_signature(item) for item in list2}
    return [item for item in list1 if dict_signature(item) not in signatures]


# Searches for Spotify users (-s flag)
def spotify_search_users(access_token, username):
    url = f"{SPOTIFY_PARTNER_BASE_URL}/pathfinder/v1/query"

    # Built as structures and percent-encoded by requests so a search term containing #, &, = or a space
    # cannot truncate the URL or inject query parameters
    query_params = {
        "operationName": "searchUsers",
        "variables": json.dumps({"searchTerm": username, "offset": 0, "limit": 5, "numberOfTopResults": 5, "includeAudiobooks": False}, separators=(",", ":")),
        "extensions": json.dumps({"persistedQuery": {"version": 1, "sha256Hash": SP_SHA256}}, separators=(",", ":")),
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    print(f"* Searching for users with '{username}' string ...\n")

    try:
        debug_print(f"HTTP GET {url} [search users] headers={sanitize_debug_headers(headers)}")
        response = SESSION.get(url, params=query_params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP GET {url} [search users] -> {response.status_code}")
        response.raise_for_status()
    except Exception:
        raise

    json_response = response.json()
    if json_response["data"]["searchV2"]["users"].get("totalCount") > 0:
        for user in json_response["data"]["searchV2"]["users"]["items"]:
            print(f"Username:\t\t{user['data']['displayName']}")
            print(f"User URI:\t\t{user['data']['uri']}")
            print(f"Spotify user ID:\t{user['data']['id']}")
            print(f"User URL:\t\t{spotify_convert_uri_to_url(user['data']['uri'])}")
            print("─" * HORIZONTAL_LINE)
    else:
        print("No results")


# Returns playlist name and URL if available, otherwise just URL
def spotify_format_playlist_reference(uri):
    uri = uri or ''
    playlist_url = spotify_convert_uri_to_url(uri)
    cached = PLAYLIST_INFO_CACHE.get(uri)
    cached_name = cached.get("name") if cached and cached.get("name") else ""
    if cached_name:
        return f"{cached_name} [ {playlist_url} ]"
    else:
        return f"[ {playlist_url} ]"


# Displays a progress bar with percentage and current playlist name
def _display_progress(current, total, playlist_name: str = "", bar_length: int = 40, is_final: bool = False) -> None:
    if total == 0:
        return

    # Defensive fallback for environments without a real TTY
    try:
        term_width = shutil.get_terminal_size(fallback=(80, 20)).columns
    except Exception:
        term_width = 80

    term_width = max(40, term_width)

    percent = float(current) / total
    percent_str = f"{percent * 100:.1f}%"
    counter_str = f"({current}/{total})"

    # Sanitized here because this bar writes to the terminal and the log file directly, bypassing Logger.write
    display_name = sanitize_terminal_text(playlist_name or "")
    prefix = "Playlists"

    def compute_base_length(include_prefix: bool) -> int:
        base = ""
        if include_prefix:
            base += prefix + " "
        base += "[]"  # placeholder for bar brackets
        base += f" {percent_str} {counter_str}"
        return len(base) + 1  # +1 for margin

    show_prefix = True
    base_len = compute_base_length(True)
    available_for_bar_and_name = term_width - base_len

    if available_for_bar_and_name < 10:
        show_prefix = False
        base_len = compute_base_length(False)
        available_for_bar_and_name = term_width - base_len

    min_name_space = 23 if display_name else 0  # 20 for name + 3 for "- "
    min_bar_len = 3
    max_reasonable_bar = 20  # Don't make bar too long

    # Calculate bar length: reserve space for name first, then use remaining for bar
    if available_for_bar_and_name >= (min_bar_len + min_name_space):
        max_bar_space = available_for_bar_and_name - min_name_space
        bar_len = max(min_bar_len, min(max_reasonable_bar, min(bar_length, max_bar_space)))
    else:
        if available_for_bar_and_name >= 10:
            if display_name:
                bar_len = max(min_bar_len, min(max_reasonable_bar, (available_for_bar_and_name * 3) // 10))  # 30% to bar
            else:
                bar_len = max(min_bar_len, available_for_bar_and_name // 2)
        else:
            # Very tight - prioritize name, shrink bar to minimum
            bar_len = min_bar_len

    def build_bar(length: int) -> str:
        filled_length = int(length * percent)
        return "█" * filled_length + "░" * (length - filled_length)

    bar = build_bar(bar_len)

    parts = []
    if show_prefix:
        parts.append(prefix)
    parts.append(f"[{bar}]")
    parts.append(percent_str)
    parts.append(counter_str)

    base_str = " ".join(parts) + " "
    available_for_name = term_width - len(base_str) - 3  # -3 for "- " prefix

    if display_name and available_for_name > 0:
        raw_name = display_name
        trimmed_name = ""

        if len(raw_name) <= available_for_name:
            # Full name fits
            trimmed_name = raw_name
        elif available_for_name >= 7:
            # Can show truncated name with ellipsis (need at least 7 chars: "abc...")
            trimmed_name = raw_name[:available_for_name - 3] + "..."
        else:
            # Very tight - show as many chars as possible (no ellipsis)
            trimmed_name = raw_name[:max(1, available_for_name)]

        if trimmed_name:
            parts.append(f"- {trimmed_name}")

    progress_str = " ".join(parts)

    terminal_out = stdout_bck if stdout_bck is not None else sys.stdout

    if is_final:
        terminal_out.write("\r\033[K" + progress_str)
        terminal_out.flush()

        if stdout_bck is not None and isinstance(sys.stdout, Logger):
            sys.stdout.logfile.write(progress_str)
            sys.stdout.logfile.flush()
    else:
        terminal_out.write("\r\033[K" + progress_str)
        terminal_out.flush()


# Processes items from all the provided playlists and returns a list of dictionaries
def spotify_process_public_playlists(sp_accessToken, playlists, get_tracks, playlists_to_skip=None, show_progress=True):
    global PLAYLIST_INFO_CACHE
    list_of_playlists = []
    error_while_processing = False
    added_at_dt: Optional[datetime] = None

    if playlists_to_skip is None:
        playlists_to_skip = []

    if playlists:
        playlists = list(playlists)
        total_playlists = len(playlists)
        debug_print(f"spotify_process_public_playlists(): total={total_playlists}, get_tracks={get_tracks}, show_progress={show_progress}")

        if show_progress:
            print()

        # Track current playlist name to keep it visible
        current_playlist_name = ""

        failure_count = 0
        for idx, playlist in enumerate(playlists, 1):
            user_id_name_mapping = {}
            unknown_added_by_tracks = 0
            p_uri = ""
            if "uri" in playlist:
                list_of_tracks = []
                try:
                    p_owner = playlist.get("owner_name", "")
                    p_owner_uri = playlist.get("owner_uri", "")

                    p_uri = playlist.get("uri", "")
                    if not p_uri:
                        print(f"\n* Playlist with missing URI returned by API, skipping for now")
                        print_cur_ts("Timestamp:\t\t\t")
                        error_while_processing = True
                        if show_progress:
                            _display_progress(idx, total_playlists, current_playlist_name, is_final=(idx == total_playlists))
                        continue

                    p_uri_id = spotify_extract_id_or_name(p_uri)
                    if not p_uri_id:
                        print(f"\n* Playlist with invalid URI ({p_uri}) returned by API, skipping for now")
                        print_cur_ts("Timestamp:\t\t\t")
                        error_while_processing = True
                        if show_progress:
                            _display_progress(idx, total_playlists, current_playlist_name, is_final=(idx == total_playlists))
                        continue

                    p_owner_name = spotify_extract_id_or_name(p_owner)
                    p_owner_id = spotify_extract_id_or_name(p_owner_uri)

                    # We do not get a list of tracks for playlists that are ignored
                    if (playlists_to_skip and (p_uri_id in playlists_to_skip or p_owner_id in playlists_to_skip or p_owner_name in playlists_to_skip)) or (IGNORE_SPOTIFY_PLAYLISTS and p_owner_id == "spotify"):
                        effective_get_tracks = False
                    else:
                        effective_get_tracks = get_tracks
                    debug_print(
                        f"playlist loop: uri={p_uri}, owner={p_owner_id or p_owner_name}, "
                        f"effective_get_tracks={effective_get_tracks}"
                    )

                    restricted_playlist = False
                    cached_entry = PLAYLIST_INFO_CACHE.get(p_uri, {})

                    def _safe_profile_followers_count(raw_value):
                        if raw_value is None:
                            return None
                        try:
                            return int(raw_value)
                        except (TypeError, ValueError):
                            return None

                    def _build_restricted_playlist_data():
                        fallback_name = playlist.get("name", "") or cached_entry.get("name", "")
                        fallback_owner = playlist.get("owner_name", "") or cached_entry.get("owner", "")
                        fallback_owner_uri = playlist.get("owner_uri", "") or cached_entry.get("owner_uri", "")
                        fallback_likes = _safe_profile_followers_count(playlist.get("followers_count"))

                        return {
                            "sp_playlist_name": fallback_name,
                            "sp_playlist_description": "",
                            "sp_playlist_followers_count": fallback_likes,
                            "sp_playlist_tracks_count": 0,
                            "sp_playlist_tracks_count_before_filtering": 0,
                            "sp_playlist_tracks": [],
                            "sp_playlist_owner": fallback_owner,
                            "sp_playlist_owner_uri": fallback_owner_uri,
                            "sp_playlist_image_url": playlist.get("image_url", "") or cached_entry.get("image_url", ""),
                            "sp_playlist_restricted": True
                        }

                    if cached_entry.get("status") == "restricted":
                        debug_print(f"playlist loop: uri={p_uri} served from restricted cache")
                        sp_playlist_data = _build_restricted_playlist_data()
                        restricted_playlist = True
                        PLAYLIST_INFO_CACHE[p_uri].update({
                            "timestamp": time.time(),
                            "name": sp_playlist_data.get("sp_playlist_name", ""),
                            "owner": sp_playlist_data.get("sp_playlist_owner", ""),
                            "owner_uri": sp_playlist_data.get("sp_playlist_owner_uri", ""),
                            "followers_count": sp_playlist_data.get("sp_playlist_followers_count"),
                            "image_url": sp_playlist_data.get("sp_playlist_image_url", "")
                        })
                    else:
                        try:
                            sp_playlist_data = spotify_get_playlist_info(sp_accessToken, p_uri, effective_get_tracks)
                            PLAYLIST_INFO_CACHE[p_uri] = {
                                "status": "ok",
                                "timestamp": time.time(),
                                "name": sp_playlist_data.get("sp_playlist_name", ""),
                                "followers_count": sp_playlist_data.get("sp_playlist_followers_count"),
                                "image_url": sp_playlist_data.get("sp_playlist_image_url", "") or playlist.get("image_url", "")
                            }
                        except PlaylistRestrictedError:
                            debug_print(f"playlist loop: uri={p_uri} marked restricted (404)")
                            sp_playlist_data = _build_restricted_playlist_data()
                            restricted_playlist = True
                            PLAYLIST_INFO_CACHE[p_uri] = {
                                "status": "restricted",
                                "timestamp": time.time(),
                                "name": sp_playlist_data.get("sp_playlist_name", ""),
                                "owner": sp_playlist_data.get("sp_playlist_owner", ""),
                                "owner_uri": sp_playlist_data.get("sp_playlist_owner_uri", ""),
                                "followers_count": sp_playlist_data.get("sp_playlist_followers_count"),
                                "image_url": sp_playlist_data.get("sp_playlist_image_url", ""),
                                "error": "playlist endpoint returned 404 (restricted)"
                            }
                            # print(f"\n* Playlist {spotify_format_playlist_reference(p_uri)} is restricted, tracking metadata only")
                        except Exception as e:
                            debug_print(f"playlist loop: uri={p_uri} processing error: {sanitize_error_text(e)}")
                            existing = PLAYLIST_INFO_CACHE.get(p_uri, {})
                            existing.update({
                                "status": "error",
                                "timestamp": time.time(),
                                "error": str(e)
                            })
                            PLAYLIST_INFO_CACHE[p_uri] = existing

                            failure_count += 1
                            if failure_count == 1 or not HIDE_DUPLICATE_NETWORK_ERRORS:
                                print_operation_error(f"Playlist {spotify_format_playlist_reference(p_uri)} could not be processed and will be retried", e)
                                if not HIDE_DUPLICATE_NETWORK_ERRORS:
                                    print_cur_ts("Timestamp:\t\t\t")
                                error_while_processing = True
                            elif failure_count == 2 and HIDE_DUPLICATE_NETWORK_ERRORS:
                                print(f"\n- (Masking additional errors)")
                            if show_progress:
                                _display_progress(idx, total_playlists, current_playlist_name, is_final=(idx == total_playlists))
                            continue

                    p_name = sp_playlist_data.get("sp_playlist_name", "")
                    current_playlist_name = p_name  # Update tracked name
                    p_descr = html.unescape(sp_playlist_data.get("sp_playlist_description", ""))
                    p_likes = _safe_profile_followers_count(sp_playlist_data.get("sp_playlist_followers_count"))
                    if p_likes is None:
                        profile_likes = _safe_profile_followers_count(playlist.get("followers_count"))
                        cached_likes = _safe_profile_followers_count(cached_entry.get("followers_count"))
                        p_likes = profile_likes if profile_likes is not None else cached_likes
                        if p_likes is not None:
                            fallback_source = "profile metadata" if profile_likes is not None else "cached baseline"
                            debug_print(f"playlist loop: uri={p_uri} detailed followers count unavailable, using {fallback_source} value {p_likes}")
                    p_tracks = sp_playlist_data.get("sp_playlist_tracks_count", 0)
                    p_tracks_before_filtering = sp_playlist_data.get("sp_playlist_tracks_count_before_filtering", 0)
                    p_url = spotify_convert_uri_to_url(p_uri)
                    p_owner = sp_playlist_data.get("sp_playlist_owner", "")
                    p_owner_uri = sp_playlist_data.get("sp_playlist_owner_uri", "")
                    p_owner_id = spotify_extract_id_or_name(p_owner_uri) if p_owner_uri else ""
                    p_source = sp_playlist_data.get("sp_playlist_source", "")
                    p_image_url = sp_playlist_data.get("sp_playlist_image_url", "") or playlist.get("image_url", "") or cached_entry.get("image_url", "")

                    p_tracks_list = sp_playlist_data.get("sp_playlist_tracks", None)
                    added_at_ts_lowest = 0
                    added_at_ts_highest = 0
                    duration_sum = 0

                    if p_tracks_list is not None:
                        for index, track in enumerate(p_tracks_list or []):
                            added_at = track.get("added_at")
                            p_artist = p_track = added_by_name = added_by_id = track_uri = ""
                            album_image_url = ""
                            track_duration = 0

                            if effective_get_tracks:
                                track_info = track.get("track")

                                p_artist = track_info["artists"][0]["name"]
                                p_track = track_info["name"]
                                duration_ms = track_info["duration_ms"]
                                album_images = (track_info.get("album") or {}).get("images") or []
                                album_image_url = album_images[0].get("url", "") if album_images and isinstance(album_images[0], dict) else ""

                                track_duration = int(str(duration_ms)[0:-3])
                                duration_sum += int(duration_ms) // 1000  # Convert to seconds
                                track_uri = track_info.get("uri")

                                added_by = track.get("added_by", {}) or {}
                                added_by_id = (added_by.get("id") or "").strip()

                                # Some tracks may have missing `added_by` due to Spotify API quirks
                                # For Spotify-owned playlists, treating it as "Spotify" gives better UX, for non-Spotify-owned playlists,
                                # treat as unknown and exclude from collaborator list/count to avoid false positives
                                if not added_by_id:
                                    if p_owner_id.lower() == "spotify":
                                        added_by_id = "spotify"
                                    else:
                                        unknown_added_by_tracks += 1
                                        added_by_id = "unknown"

                                added_by_name = user_id_name_mapping.get(added_by_id)
                                if not added_by_name:
                                    if added_by_id == "spotify":
                                        added_by_name = "Spotify"
                                    elif added_by_id == "unknown":
                                        added_by_name = "Unknown"
                                    else:
                                        sp_user_data = spotify_get_user_info(sp_accessToken, added_by_id, False, 0)
                                        added_by_name = sp_user_data.get("sp_username", added_by_id)

                                    # Exclude unknown from collaborator mapping to keep collaborator counts stable
                                    if added_by_id != "unknown":
                                        user_id_name_mapping[added_by_id] = added_by_name

                                if not added_by_name:
                                    added_by_name = added_by_id

                            if added_at:
                                added_at_dt = convert_iso_str_to_datetime(added_at)
                                if added_at_dt:
                                    added_at_dt_ts = int(added_at_dt.timestamp())

                                    if index == 0:
                                        added_at_ts_lowest = added_at_dt_ts
                                        added_at_ts_highest = added_at_dt_ts
                                    if added_at_dt_ts < added_at_ts_lowest:
                                        added_at_ts_lowest = added_at_dt_ts
                                    if added_at_dt_ts > added_at_ts_highest:
                                        added_at_ts_highest = added_at_dt_ts

                            if effective_get_tracks and added_at and p_artist and p_track:
                                list_of_tracks.append({"artist": p_artist, "track": p_track, "duration": track_duration, "added_at": added_at_dt, "uri": track_uri, "added_by": added_by_name, "added_by_id": added_by_id, "album_image_url": album_image_url})

                except Exception as e:
                    debug_print(f"playlist loop: unexpected build error for uri={p_uri}: {sanitize_error_text(e)}")

                    failure_count += 1
                    if failure_count == 1 or not HIDE_DUPLICATE_NETWORK_ERRORS:
                        print_operation_error(f"Playlist data for {spotify_format_playlist_reference(p_uri)} could not be built", e)
                        if not HIDE_DUPLICATE_NETWORK_ERRORS:
                            print_cur_ts("Timestamp:\t\t\t")
                        error_while_processing = True
                    elif failure_count == 2 and HIDE_DUPLICATE_NETWORK_ERRORS:
                        print(f"\n- (Masking additional errors)")
                    if show_progress:
                        _display_progress(idx, total_playlists, current_playlist_name, is_final=(idx == total_playlists))
                    continue

                p_creation_date = datetime.fromtimestamp(int(added_at_ts_lowest), pytz.timezone(LOCAL_TIMEZONE)) if added_at_ts_lowest > 0 else None
                p_last_track_date = datetime.fromtimestamp(int(added_at_ts_highest), pytz.timezone(LOCAL_TIMEZONE)) if added_at_ts_highest > 0 else None

                p_collaborators_count = len(user_id_name_mapping)

                # Update cache with comprehensive playlist data
                if p_uri in PLAYLIST_INFO_CACHE:
                    PLAYLIST_INFO_CACHE[p_uri].update({
                        "followers_count": p_likes,
                        "tracks_count": p_tracks,
                        "duration_seconds": duration_sum,
                        "creation_date_ts": added_at_ts_lowest if added_at_ts_lowest > 0 else None,
                        "update_date_ts": added_at_ts_highest if added_at_ts_highest > 0 else None,
                        "creation_date": p_creation_date,
                        "update_date": p_last_track_date,
                        "image_url": p_image_url
                    })

                if list_of_tracks and effective_get_tracks:
                    list_of_playlists.append({"uri": p_uri, "name": p_name, "desc": p_descr, "likes": p_likes, "tracks_count": p_tracks, "tracks_count_before_filtering": p_tracks_before_filtering, "url": p_url, "date": p_creation_date, "update_date": p_last_track_date, "list_of_tracks": list_of_tracks, "collaborators_count": p_collaborators_count, "collaborators": user_id_name_mapping, "owner": p_owner, "owner_uri": p_owner_uri, "unknown_added_by_tracks": unknown_added_by_tracks, "restricted": restricted_playlist, "source": p_source, "image_url": p_image_url})
                else:
                    list_of_playlists.append({"uri": p_uri, "name": p_name, "desc": p_descr, "likes": p_likes, "tracks_count": p_tracks, "tracks_count_before_filtering": p_tracks_before_filtering, "url": p_url, "date": p_creation_date, "update_date": p_last_track_date, "collaborators_count": p_collaborators_count, "collaborators": {}, "owner": p_owner, "owner_uri": p_owner_uri, "unknown_added_by_tracks": unknown_added_by_tracks, "restricted": restricted_playlist, "source": p_source, "image_url": p_image_url})

                # Final refresh after successful processing
                if show_progress:
                    _display_progress(idx, total_playlists, p_name, is_final=(idx == total_playlists))
                    # If this is the last playlist, immediately add a newline after the progress bar
                    if idx == total_playlists:
                        # Write newline to terminal
                        terminal_out = stdout_bck if stdout_bck is not None else sys.stdout
                        terminal_out.write("\n")
                        terminal_out.flush()
                        # Also write to log file if logging is enabled
                        if stdout_bck is not None and isinstance(sys.stdout, Logger):
                            sys.stdout.logfile.write("\n")
                            sys.stdout.logfile.flush()

        if failure_count and HIDE_DUPLICATE_NETWORK_ERRORS:
            print_cur_ts("Timestamp:\t\t\t")

    return list_of_playlists, error_while_processing


# Builds the next playlist baseline from successful snapshots and accepted playlist membership
def merge_playlist_snapshots(previous_snapshots, successful_snapshots, accepted_playlists):
    previous_by_uri = {snapshot.get("uri"): snapshot for snapshot in (previous_snapshots or []) if isinstance(snapshot, dict) and snapshot.get("uri")}
    successful_by_uri = {snapshot.get("uri"): snapshot for snapshot in (successful_snapshots or []) if isinstance(snapshot, dict) and snapshot.get("uri")}
    merged_snapshots = []

    for playlist in accepted_playlists or []:
        if not isinstance(playlist, dict):
            continue

        playlist_uri = playlist.get("uri")
        if not playlist_uri:
            continue

        if playlist_uri in successful_by_uri:
            successful_snapshot = successful_by_uri[playlist_uri]
            previous_snapshot = previous_by_uri.get(playlist_uri)
            if successful_snapshot.get("likes") is None and previous_snapshot is not None and previous_snapshot.get("likes") is not None:
                successful_snapshot = {**successful_snapshot, "likes": previous_snapshot["likes"]}
            merged_snapshots.append(successful_snapshot)
        elif playlist_uri in previous_by_uri:
            merged_snapshots.append(previous_by_uri[playlist_uri])

    return merged_snapshots


# Reports whether two available playlist like counts differ
def playlist_likes_changed(previous_likes, current_likes):
    return previous_likes is not None and current_likes is not None and previous_likes != current_likes


# Extracts playlist URI values for order-independent membership comparisons
def extract_playlist_uris(playlist_list):
    if not playlist_list:
        return frozenset()

    return frozenset(p.get("uri") if isinstance(p, dict) else p for p in playlist_list if p)


# Reports whether a playlist count or URI membership changed
def playlist_collection_changed(current_playlists, previous_playlists, current_count, previous_count):
    return current_count != previous_count or extract_playlist_uris(current_playlists) != extract_playlist_uris(previous_playlists)


# Prints detailed info about user's playlists
def spotify_print_public_playlists(sp_accessToken, list_of_playlists, playlists_to_skip=None):
    p_update = datetime.min.replace(tzinfo=pytz.timezone(LOCAL_TIMEZONE))
    p_update_recent = datetime.min.replace(tzinfo=pytz.timezone(LOCAL_TIMEZONE))
    p_name = ""
    p_name_recent = ""
    p_url = ""
    p_url_recent = ""

    if playlists_to_skip is None:
        playlists_to_skip = []

    if list_of_playlists:
        print()
        for playlist in list_of_playlists:
            if "uri" in playlist:
                p_uri = playlist.get("uri", "")
                p_name = playlist.get("name", "")
                p_descr = html.unescape(playlist.get("desc", ""))
                p_likes = playlist.get("likes", 0)
                p_tracks = playlist.get("tracks_count", 0)
                p_url = playlist.get("url")
                p_date = playlist.get("date")
                p_update = playlist.get("update_date")
                p_collaborators_count = playlist.get("collaborators_count")
                p_collaborators = playlist.get("collaborators")
                p_owner = playlist.get("owner", "")
                p_owner_uri = playlist.get("owner_uri", "")
                p_restricted = bool(playlist.get("restricted", False))
                p_uri_id = spotify_extract_id_or_name(p_uri)
                p_owner_name = spotify_extract_id_or_name(p_owner)
                p_owner_id = spotify_extract_id_or_name(p_owner_uri)

                skipped_from_processing = ""
                if (playlists_to_skip and (p_uri_id in playlists_to_skip or p_owner_id in playlists_to_skip or p_owner_name in playlists_to_skip)) or (IGNORE_SPOTIFY_PLAYLISTS and p_owner_id == "spotify"):
                    skipped_from_processing = " [ IGNORED ]"

                restricted_label = " [ RESTRICTED ]" if p_restricted else ""
                likes_display = p_likes if p_likes is not None else "n/a"
                if p_restricted:
                    print(f"- '{p_name}'{skipped_from_processing}{restricted_label}\n[ {p_url} ]\n[ likes: {likes_display} ]\n[ owner: {p_owner} ]")
                    print("[ metadata source: profile-view only ]")
                else:
                    print(f"- '{p_name}'{skipped_from_processing}\n[ {p_url} ]\n[ songs: {p_tracks}, likes: {likes_display}, collaborators: {p_collaborators_count} ]\n[ owner: {p_owner} ]")
                if p_date:
                    print(f"[ date: {get_date_from_ts(p_date)} - {calculate_timespan(now_local(), p_date)} ago ]")
                if p_update:
                    print(f"[ update: {get_date_from_ts(p_update)} - {calculate_timespan(now_local(), p_update)} ago ]")
                if p_descr:
                    print(f"'{p_descr}'")
                if EXPORT_ALL and not skipped_from_processing and not p_restricted:
                    from pathvalidate import sanitize_filename
                    safe_filename = sanitize_filename(p_name)
                    safe_filename_path = os.path.expanduser(safe_filename + '.csv')
                    print(f"-- Exporting playlist to '{safe_filename_path}'")
                    spotify_list_tracks_for_playlist(sp_accessToken, p_url, safe_filename_path, CSV_FILE_FORMAT_EXPORT)
                    print(f"-- Export completed")
                print()

            if p_update is not None and p_update > p_update_recent:
                p_update_recent = p_update
                p_name_recent = p_name
                p_url_recent = p_url

        if p_update_recent is not None and p_update_recent > datetime.min.replace(tzinfo=pytz.timezone(LOCAL_TIMEZONE)) and p_name_recent and p_url_recent:
            print(f"Recently updated playlist:\n\n- '{p_name_recent}'\n[ {p_url_recent} ]\n[ update: {get_date_from_ts(p_update_recent)} - {calculate_timespan(now_local(), p_update_recent)} ago ]")


# Prints detailed info about the user with the specified Spotify user ID (-i flag)
def spotify_get_user_details(sp_accessToken, user_uri_id):
    playlists_count = 0
    playlists = None

    print(f"* Getting detailed info for Spotify user ID '{user_uri_id}' ...\n")

    sp_user_data = spotify_get_user_info(sp_accessToken, user_uri_id, DETECT_CHANGES_IN_PLAYLISTS, RECENTLY_PLAYED_ARTISTS_LIMIT_INFO)
    sp_user_followers_data = spotify_get_user_followers(sp_accessToken, user_uri_id)
    sp_user_followings_data = spotify_get_user_followings(sp_accessToken, user_uri_id)

    username = sp_user_data["sp_username"]
    image_url = sp_user_data["sp_user_image_url"]

    followers = sp_user_followers_data["sp_user_followers"]
    followings = sp_user_followings_data["sp_user_followings"]

    followers_count = sp_user_data["sp_user_followers_count"]
    if followers:
        followers_count_tmp = len(followers)
        if followers_count_tmp > 0:
            followers_count = followers_count_tmp

    followings_count = sp_user_data["sp_user_followings_count"]
    if followings:
        followings_count_tmp = len(followings)
        if followings_count_tmp > 0:
            followings_count = followings_count_tmp

    if DETECT_CHANGES_IN_PLAYLISTS:
        playlists_count = sp_user_data["sp_user_public_playlists_count"]
        playlists = sp_user_data["sp_user_public_playlists_uris"]

    recently_played_artists = sp_user_data["sp_user_recently_played_artists"]

    print(f"Username:\t\t{username}")
    print(f"Spotify user ID:\t{user_uri_id}")
    print(f"User URL:\t\t{spotify_convert_uri_to_url(f'spotify:user:{user_uri_id}')}")

    print(f"User profile picture:\t{image_url != ''}", end=" ")

    display_tmp_pic(image_url, f"spotify_{user_uri_id}_profile_pic_tmp_info.jpeg", imgcat_exe, True)

    print(f"\nFollowers:\t\t{followers_count}" + (f" (list not supported with {TOKEN_SOURCE})" if TOKEN_SOURCE in {"oauth_app", "oauth_user"} else ""))
    if followers:
        print()
        for f_dict in followers:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")

    is_user_owner = False
    if TOKEN_SOURCE == "oauth_user":
        is_user_owner = is_token_owner(sp_accessToken, user_uri_id)

    if TOKEN_SOURCE == "oauth_user" and is_user_owner:
        print(f"\nFollowings:\t\t{followings_count} (only artists, without users)")
    else:
        print(f"\nFollowings:\t\t{followings_count}" + (f" (list and count not supported with {TOKEN_SOURCE})" if TOKEN_SOURCE in {"oauth_app", "oauth_user"} else ""))
    if followings:
        print()
        for f_dict in followings:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")

    if recently_played_artists:
        print(f"\nPlayed artists:\t\t{len(recently_played_artists)} (limit {RECENTLY_PLAYED_ARTISTS_LIMIT_INFO})\n")
        for f_dict in recently_played_artists:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")

    if DETECT_CHANGES_IN_PLAYLISTS:
        if TOKEN_SOURCE == "oauth_user" and is_user_owner:
            print(f"\nPlaylists:\t\t{playlists_count}")
        else:
            print(f"\nPublic playlists:\t{playlists_count}")

        if playlists:
            list_of_playlists, error_while_processing = spotify_process_public_playlists(sp_accessToken, playlists, True)
            spotify_print_public_playlists(sp_accessToken, list_of_playlists)


# Returns recently played artists for a user with the specified URI (-a flag)
def spotify_get_recently_played_artists(sp_accessToken, user_uri_id):
    print(f"* Getting list of recently played artists for Spotify user ID '{user_uri_id}' ...\n")

    sp_user_data = spotify_get_user_info(sp_accessToken, user_uri_id, False, RECENTLY_PLAYED_ARTISTS_LIMIT)

    username = sp_user_data["sp_username"]
    image_url = sp_user_data["sp_user_image_url"]

    recently_played_artists = sp_user_data["sp_user_recently_played_artists"]

    print(f"Username:\t\t{username}")
    print(f"Spotify user ID:\t{user_uri_id}")
    print(f"User URL:\t\t{spotify_convert_uri_to_url(f'spotify:user:{user_uri_id}')}")

    print(f"User profile picture:\t{image_url != ''}")

    if recently_played_artists:
        print(f"\nPlayed artists:\t\t{len(recently_played_artists)} (limit {RECENTLY_PLAYED_ARTISTS_LIMIT})\n")
        for f_dict in recently_played_artists:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
    else:
        print("\nRecently played artists list is empty\n")


# Prints followers & followings for a user with specified URI (-f flag)
def spotify_get_followers_and_followings(sp_accessToken, user_uri_id):
    print(f"* Getting followers & followings for Spotify user ID '{user_uri_id}' ...\n")

    sp_user_data = spotify_get_user_info(sp_accessToken, user_uri_id, False, 0)
    image_url = sp_user_data["sp_user_image_url"]
    sp_user_followers_data = spotify_get_user_followers(sp_accessToken, user_uri_id)
    sp_user_followings_data = spotify_get_user_followings(sp_accessToken, user_uri_id)

    username = sp_user_data["sp_username"]

    followers = sp_user_followers_data["sp_user_followers"]
    followings = sp_user_followings_data["sp_user_followings"]

    followers_count = sp_user_data["sp_user_followers_count"]
    if followers:
        followers_count_tmp = len(followers)
        if followers_count_tmp > 0:
            followers_count = followers_count_tmp

    followings_count = sp_user_data["sp_user_followings_count"]
    if followings:
        followings_count_tmp = len(followings)
        if followings_count_tmp > 0:
            followings_count = followings_count_tmp

    print(f"Username:\t\t{username}")
    print(f"Spotify user ID:\t{user_uri_id}")
    print(f"User URL:\t\t{spotify_convert_uri_to_url(f'spotify:user:{user_uri_id}')}")

    print(f"User profile picture:\t{image_url != ''}")

    followers_label = ""
    if TOKEN_SOURCE in {"oauth_app", "oauth_user"}:
        if not sp_user_data["sp_user_followers_count_available"]:
            followers_label = f" (list and count not supported with {TOKEN_SOURCE})"
        else:
            followers_label = f" (list not supported with {TOKEN_SOURCE})"

    print(f"\nFollowers:\t\t{followers_count}{followers_label}")
    if followers:
        print()
        for f_dict in followers:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
    if TOKEN_SOURCE == "oauth_user" and is_token_owner(sp_accessToken, user_uri_id):
        print(f"Followings:\t\t{followings_count} (only artists, without users)")
    else:
        print(f"Followings:\t\t{followings_count}" + (f" (list and count not supported with {TOKEN_SOURCE})" if TOKEN_SOURCE in {"oauth_app", "oauth_user"} else ""))
    if followings:
        print()
        for f_dict in followings:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")


# Helper function to get playlist details (songs count, duration, creation date, update date)
def get_playlist_details_for_notification(sp_accessToken, playlist_uri):
    try:
        # Check cache first
        if playlist_uri in PLAYLIST_INFO_CACHE:
            cache_entry = PLAYLIST_INFO_CACHE[playlist_uri]
            if cache_entry.get("status") == "ok":
                tracks_count = cache_entry.get("tracks_count", 0)
                duration_seconds = cache_entry.get("duration_seconds", 0)
                creation_date_ts = cache_entry.get("creation_date_ts")
                update_date_ts = cache_entry.get("update_date_ts")

                # If we have cached data, use it
                if tracks_count is not None and duration_seconds is not None:
                    is_empty = tracks_count == 0

                    creation_date_str = ""
                    creation_date_since = ""
                    if creation_date_ts and creation_date_ts > 0:
                        creation_date_str = get_date_from_ts(creation_date_ts)
                        creation_date_since = calculate_timespan(int(time.time()), creation_date_ts)

                    update_date_str = ""
                    update_date_since = ""
                    if update_date_ts and update_date_ts > 0:
                        update_date_str = get_date_from_ts(update_date_ts)
                        update_date_since = calculate_timespan(int(time.time()), update_date_ts)

                    return {
                        "songs_count": tracks_count,
                        "duration_seconds": duration_seconds,
                        "creation_date": creation_date_str,
                        "creation_date_since": creation_date_since,
                        "update_date": update_date_str,
                        "update_date_since": update_date_since,
                        "is_empty": is_empty
                    }

        # Cache miss or incomplete data - fetch fresh
        sp_playlist_data = spotify_get_playlist_info(sp_accessToken, playlist_uri, True)
        p_tracks = sp_playlist_data.get("sp_playlist_tracks_count", 0)
        p_tracks_list = sp_playlist_data.get("sp_playlist_tracks", [])

        # Check if playlist is empty
        is_empty = p_tracks == 0

        # Calculate duration
        duration_sum = 0
        added_at_ts_lowest = 0
        added_at_ts_highest = 0

        if p_tracks_list:
            for index, track in enumerate(p_tracks_list):
                track_info = track.get("track")
                if track_info:
                    duration_ms = track_info.get("duration_ms", 0)
                    if duration_ms:
                        duration_sum += int(duration_ms) // 1000  # Convert to seconds

                    added_at_str = track.get("added_at")
                    if added_at_str:
                        added_at_dt = convert_iso_str_to_datetime(added_at_str)
                        if added_at_dt:
                            added_at_ts = int(added_at_dt.timestamp())
                            if index == 0:
                                added_at_ts_lowest = added_at_ts
                                added_at_ts_highest = added_at_ts
                            if added_at_ts < added_at_ts_lowest:
                                added_at_ts_lowest = added_at_ts
                            if added_at_ts > added_at_ts_highest:
                                added_at_ts_highest = added_at_ts

        creation_date_str = ""
        creation_date_since = ""
        if added_at_ts_lowest > 0:
            creation_date_str = get_date_from_ts(added_at_ts_lowest)
            creation_date_since = calculate_timespan(int(time.time()), added_at_ts_lowest)

        update_date_str = ""
        update_date_since = ""
        if added_at_ts_highest > 0:
            update_date_str = get_date_from_ts(added_at_ts_highest)
            update_date_since = calculate_timespan(int(time.time()), added_at_ts_highest)

        return {
            "songs_count": p_tracks,
            "duration_seconds": duration_sum,
            "creation_date": creation_date_str,
            "creation_date_since": creation_date_since,
            "update_date": update_date_str,
            "update_date_since": update_date_since,
            "is_empty": is_empty
        }
    except Exception as e:
        return {
            "songs_count": 0,
            "duration_seconds": 0,
            "creation_date": "",
            "creation_date_since": "",
            "update_date": "",
            "update_date_since": "",
            "is_empty": True,
            "error": str(e)
        }


# Prints and saves changed lists of followers, followings or playlists with enabled notifications
def spotify_print_changed_followers_followings_playlists(username, f_list, f_list_old, f_count, f_old_count, f_str, f_str_by_or_from, f_added_str, f_added_csv, f_removed_str, f_removed_csv, f_file, csv_file_name, profile_notification, is_playlist, sp_accessToken=None, notification_image_url="", webhook_notification_allowed=None):
    global GLITCH_CACHE
    global PLAYLIST_INFO_CACHE
    global WEB_PLAYLIST_REVISION_CACHE

    if is_playlist:
        now = time.time()
        GLITCH_CACHE = {uri: ts for uri, ts in GLITCH_CACHE.items() if now - ts < SPOTIFY_CHECK_INTERVAL}
        PLAYLIST_INFO_CACHE = {uri: entry for uri, entry in PLAYLIST_INFO_CACHE.items() if now - entry.get("timestamp", 0) < PLAYLIST_INFO_CACHE_TTL}
        WEB_PLAYLIST_REVISION_CACHE = {uri: entry for uri, entry in WEB_PLAYLIST_REVISION_CACHE.items() if now - entry.get("timestamp", 0) < PLAYLIST_INFO_CACHE_TTL}

    f_diff = f_count - f_old_count

    f_diff_str = "+" + str(f_diff) if f_diff > 0 else str(f_diff)

    if is_playlist:
        def _playlist_identity(items):
            if not items:
                return []
            return [{"uri": d.get("uri"), "owner_uri": d.get("owner_uri")} for d in items if isinstance(d, dict) and d.get("uri")]

        f_list_stripped = _playlist_identity(f_list)
        f_list_old_stripped = _playlist_identity(f_list_old)
    else:
        f_list_stripped = remove_key_from_list_of_dicts_copy(f_list, "owner_name")
        f_list_old_stripped = remove_key_from_list_of_dicts_copy(f_list_old, "owner_name")

    removed_f_list = compare_two_lists_of_dicts(f_list_old_stripped, f_list_stripped)
    added_f_list = compare_two_lists_of_dicts(f_list_stripped, f_list_old_stripped)
    playlist_membership_only_change = is_playlist and f_diff == 0 and bool(added_f_list or removed_f_list)

    list_of_added_f_list = ""
    list_of_removed_f_list = ""
    added_f_list_mbody = ""
    removed_f_list_mbody = ""
    list_of_added_f_list_html = ""
    list_of_removed_f_list_html = ""
    added_f_list_mbody_html = ""
    removed_f_list_mbody_html = ""
    playlist_notification_image_url = ""

    if playlist_membership_only_change:
        print(f"* {f_str} changed for user {username} while the total remained {f_count}\n")
    elif added_f_list or removed_f_list or ((f_str == "Followers" or f_str == "Followings") and TOKEN_SOURCE == "oauth_app"):
        print(f"* {f_str} number changed {f_str_by_or_from} user {username} from {f_old_count} to {f_count} ({f_diff_str})\n")

    if added_f_list:
        print(f"{f_added_str}:\n")
        added_f_list_mbody = f"\n{f_added_str}:\n\n"
        added_f_list_mbody_html = f"<br><b>{escape(f_added_str)}:</b><br><br>"
        for idx, f_dict in enumerate(added_f_list):
            if is_playlist:
                if "uri" in f_dict:

                    uri = f_dict["uri"]
                    current_meta = next((p for p in (f_list or []) if isinstance(p, dict) and p.get("uri") == uri), {})
                    if not playlist_notification_image_url:
                        playlist_notification_image_url = current_meta.get("image_url", "")
                    cached = PLAYLIST_INFO_CACHE.get(uri)
                    cached_status = cached.get("status") if cached else ""
                    is_restricted = cached_status == "restricted"

                    if not cached or cached_status not in {"ok", "restricted"}:
                        print(f"- Skipping playlist {spotify_format_playlist_reference(uri)} due to cached error or missing data")
                        list_of_added_f_list += f"- Skipping playlist {spotify_format_playlist_reference(uri)} due to error\n"
                        list_of_added_f_list_html += f"- Skipping playlist {escape(spotify_format_playlist_reference(uri))} due to error<br>"
                        continue
                    p_name = (current_meta.get("name") or f_dict.get("name") or cached.get("name") or "Unknown")
                    p_url = spotify_convert_uri_to_url(uri)
                    current_likes = current_meta.get("followers_count", f_dict.get("followers_count", cached.get("followers_count")))
                    current_likes_str = str(current_likes) if current_likes is not None else "n/a"

                    if is_restricted:
                        restricted_followers = current_meta.get("followers_count", f_dict.get("followers_count", cached.get("followers_count")))
                        followers_str = restricted_followers if restricted_followers is not None else "n/a"
                        console_output = f"- {p_name} [ {p_url} ] [ RESTRICTED ]\n  Likes: {followers_str}\n  Metadata source: profile-view only"
                        email_output = f"- {p_name} [ {p_url} ] [ RESTRICTED ]\n  Likes: {followers_str}\n  Metadata source: profile-view only"
                        html_output = f"- <a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a> [ <b>RESTRICTED</b> ]<br>&nbsp;&nbsp;Likes: <b>{escape(str(followers_str))}</b><br>&nbsp;&nbsp;Metadata source: profile-view only"
                    else:
                        # Get playlist details
                        playlist_details = None
                        if sp_accessToken:
                            try:
                                playlist_details = get_playlist_details_for_notification(sp_accessToken, uri)
                            except Exception:
                                playlist_details = None

                        # Format console output
                        console_output = f"- {p_name} [ {p_url} ]"
                        email_output = f"- {p_name} [ {p_url} ]"
                        html_output = f"- <a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a>"
                        console_output += f"\n  Likes: {current_likes_str}"
                        email_output += f"\n  Likes: {current_likes_str}"
                        html_output += f"<br>&nbsp;&nbsp;Likes: <b>{escape(current_likes_str)}</b>"

                        if playlist_details and not playlist_details.get("error"):
                            if playlist_details.get("is_empty"):
                                console_output += f"\n  (Playlist is empty)"
                                email_output += f"\n  (Playlist is empty)"
                                html_output += f"<br>&nbsp;&nbsp;(Playlist is empty)"
                            else:
                                # Songs count
                                console_output += f"\n  Songs: {playlist_details.get('songs_count', 0)}"
                                email_output += f"\n  Songs: {playlist_details.get('songs_count', 0)}"
                                html_output += f"<br>&nbsp;&nbsp;Songs: <b>{playlist_details.get('songs_count', 0)}</b>"

                                # Duration
                                duration_str = display_time(playlist_details.get('duration_seconds', 0))
                                console_output += f"\n  Duration: {duration_str}"
                                email_output += f"\n  Duration: {duration_str}"
                                html_output += f"<br>&nbsp;&nbsp;Duration: <b>{escape(duration_str)}</b>"

                                # Creation date
                                if playlist_details.get('creation_date'):
                                    creation_info = f"{playlist_details.get('creation_date')} ({playlist_details.get('creation_date_since', '')} ago)"
                                    console_output += f"\n  Creation date: {creation_info}"
                                    email_output += f"\n  Creation date: {creation_info}"
                                    html_output += f"<br>&nbsp;&nbsp;Creation date: <b>{escape(playlist_details.get('creation_date'))}</b> ({escape(playlist_details.get('creation_date_since', ''))} ago)"

                                # Last update date
                                if playlist_details.get('update_date'):
                                    update_info = f"{playlist_details.get('update_date')} ({playlist_details.get('update_date_since', '')} ago)"
                                    console_output += f"\n  Last update: {update_info}"
                                    email_output += f"\n  Last update: {update_info}"
                                    html_output += f"<br>&nbsp;&nbsp;Last update: <b>{escape(playlist_details.get('update_date'))}</b> ({escape(playlist_details.get('update_date_since', ''))} ago)"

                    print(console_output)
                    list_of_added_f_list += email_output
                    list_of_added_f_list_html += html_output

                    # Add empty line between playlists if not the last one and there are multiple playlists
                    if len(added_f_list) > 1 and idx < len(added_f_list) - 1:
                        print()
                        list_of_added_f_list += "\n\n"
                        list_of_added_f_list_html += "<br><br>"
                    else:
                        list_of_added_f_list += "\n"
                        list_of_added_f_list_html += "<br>"

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), f_added_csv, username, "", p_name)
                    except Exception as e:
                        print_operation_error("A CSV event could not be written", e)
            else:
                if "name" in f_dict and "uri" in f_dict:
                    print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                    list_of_added_f_list += f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]"
                    list_of_added_f_list_html += f"- <a href=\"{escape_html_attr(spotify_convert_uri_to_url(f_dict['uri']))}\">{escape(f_dict['name'])}</a>"

                    # Add empty line between items if not the last one and there are multiple items
                    if len(added_f_list) > 1 and idx < len(added_f_list) - 1:
                        print()
                        list_of_added_f_list += "\n\n"
                        list_of_added_f_list_html += "<br><br>"
                    else:
                        list_of_added_f_list += "\n"
                        list_of_added_f_list_html += "<br>"

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), f_added_csv, username, "", f_dict["name"])
                    except Exception as e:
                        print_operation_error("A CSV event could not be written", e)
        if added_f_list:
            print()
    if removed_f_list:
        print(f"{f_removed_str}:\n")
        removed_f_list_mbody = f"\n{f_removed_str}:\n\n"
        removed_f_list_mbody_html = f"<br><b>{escape(f_removed_str)}:</b><br><br>"
        for idx, f_dict in enumerate(removed_f_list):
            if is_playlist:
                if "uri" in f_dict:

                    uri = f_dict["uri"]
                    old_meta = next((p for p in (f_list_old or []) if isinstance(p, dict) and p.get("uri") == uri), {})
                    if not playlist_notification_image_url:
                        playlist_notification_image_url = old_meta.get("image_url", "")

                    if uri in GLITCH_CACHE:
                        print(f"- Skipping playlist {spotify_format_playlist_reference(uri)} due to recent glitch")
                        continue

                    cached = PLAYLIST_INFO_CACHE.get(uri)
                    cached_status = cached.get("status") if cached else ""
                    is_restricted = cached_status == "restricted"

                    if not cached or cached_status not in {"ok", "restricted"}:
                        error_str = cached.get("error", "") if cached else ""

                        if "not found" in error_str.lower():
                            print(f"- {spotify_format_playlist_reference(uri)}: playlist has been removed or set to private")
                            list_of_removed_f_list += f"- {spotify_format_playlist_reference(uri)}: playlist has been removed or set to private\n"
                            list_of_removed_f_list_html += f"- {escape(spotify_format_playlist_reference(uri))}: playlist has been removed or set to private<br>"

                        elif any(keyword in error_str.lower() for keyword in ["502", "server error", "bad gateway"]):
                            print(f"- Suspected temporary glitch for playlist {spotify_format_playlist_reference(uri)}")
                            if error_str:
                                debug_print(f"Playlist glitch detail: {sanitize_error_text(error_str)}")
                            GLITCH_CACHE[uri] = time.time()
                            print_cur_ts("Timestamp:\t\t\t")
                            continue

                        else:
                            print(f"- Error while getting info for playlist {spotify_format_playlist_reference(uri)}, skipping for now")
                            if error_str:
                                debug_print(f"Playlist retrieval detail: {sanitize_error_text(error_str)}")
                            list_of_removed_f_list += f"- Error while getting info for playlist {spotify_format_playlist_reference(uri)}\n"
                            list_of_removed_f_list_html += f"- Error while getting info for playlist {escape(spotify_format_playlist_reference(uri))}<br>"
                            print_cur_ts("Timestamp:\t\t\t")
                            continue

                    if cached:
                        p_name = old_meta.get("name", cached.get("name", "Unknown"))
                    else:
                        p_name = old_meta.get("name", "Unknown")

                    p_url = spotify_convert_uri_to_url(uri)
                    last_known_likes = old_meta.get("followers_count")
                    if last_known_likes is None:
                        last_known_likes = old_meta.get("likes")
                    if last_known_likes is None and cached:
                        last_known_likes = cached.get("followers_count")
                    last_known_likes_str = str(last_known_likes) if last_known_likes is not None else "n/a"

                    if is_restricted:
                        restricted_followers = old_meta.get("followers_count", f_dict.get("followers_count", cached.get("followers_count") if cached else None))
                        followers_str = restricted_followers if restricted_followers is not None else "n/a"
                        console_output = f"- {p_name} [ {p_url} ] [ RESTRICTED ]\n  Likes: {followers_str}\n  Metadata source: profile-view only"
                        email_output = f"- {p_name} [ {p_url} ] [ RESTRICTED ]\n  Likes: {followers_str}\n  Metadata source: profile-view only"
                        html_output = f"- <a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a> [ <b>RESTRICTED</b> ]<br>&nbsp;&nbsp;Likes: <b>{escape(str(followers_str))}</b><br>&nbsp;&nbsp;Metadata source: profile-view only"

                        print(console_output)
                        list_of_removed_f_list += email_output
                        list_of_removed_f_list_html += html_output

                        if len(removed_f_list) > 1 and idx < len(removed_f_list) - 1:
                            print()
                            list_of_removed_f_list += "\n\n"
                            list_of_removed_f_list_html += "<br><br>"
                        else:
                            list_of_removed_f_list += "\n"
                            list_of_removed_f_list_html += "<br>"
                        try:
                            if csv_file_name:
                                write_csv_entry(csv_file_name, now_local_naive(), f_removed_csv, username, p_name, "")
                        except Exception as e:
                            print_operation_error("A CSV event could not be written", e)
                        continue

                    # Check if playlist is private first
                    is_private = is_playlist_private(sp_accessToken, uri) if sp_accessToken else False

                    # Try to get playlist details if still accessible
                    playlist_details = None
                    if sp_accessToken and not is_private:
                        try:
                            playlist_details = get_playlist_details_for_notification(sp_accessToken, uri)
                        except Exception:
                            playlist_details = None

                    if is_private:
                        console_output = f"- {spotify_format_playlist_reference(uri)}: playlist has been removed or set to private"
                        email_output = f"- {spotify_format_playlist_reference(uri)}: playlist has been removed or set to private"
                        html_output = f"- <a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a>: playlist has been removed or set to private"
                        console_output += f"\n  Likes: {last_known_likes_str}"
                        email_output += f"\n  Likes: {last_known_likes_str}"
                        html_output += f"<br>&nbsp;&nbsp;Likes: <b>{escape(last_known_likes_str)}</b>"

                        # If we have cached details, show them
                        if playlist_details and not playlist_details.get("error"):
                            if playlist_details.get("is_empty"):
                                console_output += f"\n  (Playlist was empty)"
                                email_output += f"\n  (Playlist was empty)"
                                html_output += f"<br>&nbsp;&nbsp;(Playlist was empty)"
                            else:
                                # Songs count
                                console_output += f"\n  Songs: {playlist_details.get('songs_count', 0)}"
                                email_output += f"\n  Songs: {playlist_details.get('songs_count', 0)}"
                                html_output += f"<br>&nbsp;&nbsp;Songs: <b>{playlist_details.get('songs_count', 0)}</b>"

                                # Duration
                                duration_str = display_time(playlist_details.get('duration_seconds', 0))
                                console_output += f"\n  Duration: {duration_str}"
                                email_output += f"\n  Duration: {duration_str}"
                                html_output += f"<br>&nbsp;&nbsp;Duration: <b>{escape(duration_str)}</b>"

                                # Creation date
                                if playlist_details.get('creation_date'):
                                    creation_info = f"{playlist_details.get('creation_date')} ({playlist_details.get('creation_date_since', '')} ago)"
                                    console_output += f"\n  Creation date: {creation_info}"
                                    email_output += f"\n  Creation date: {creation_info}"
                                    html_output += f"<br>&nbsp;&nbsp;Creation date: <b>{escape(playlist_details.get('creation_date'))}</b> ({escape(playlist_details.get('creation_date_since', ''))} ago)"

                                # Last update date
                                if playlist_details.get('update_date'):
                                    update_info = f"{playlist_details.get('update_date')} ({playlist_details.get('update_date_since', '')} ago)"
                                    console_output += f"\n  Last update: {update_info}"
                                    email_output += f"\n  Last update: {update_info}"
                                    html_output += f"<br>&nbsp;&nbsp;Last update: <b>{escape(playlist_details.get('update_date'))}</b> ({escape(playlist_details.get('update_date_since', ''))} ago)"

                        print(console_output)
                        list_of_removed_f_list += email_output
                        list_of_removed_f_list_html += html_output

                        # Add empty line between playlists if not the last one and there are multiple playlists
                        if len(removed_f_list) > 1 and idx < len(removed_f_list) - 1:
                            print()
                            list_of_removed_f_list += "\n\n"
                            list_of_removed_f_list_html += "<br><br>"
                        else:
                            list_of_removed_f_list += "\n"
                            list_of_removed_f_list_html += "<br>"
                    else:
                        console_output = f"- {spotify_format_playlist_reference(uri)}"
                        email_output = f"- {spotify_format_playlist_reference(uri)}"
                        html_output = f"- <a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a>"
                        console_output += f"\n  Likes: {last_known_likes_str}"
                        email_output += f"\n  Likes: {last_known_likes_str}"
                        html_output += f"<br>&nbsp;&nbsp;Likes: <b>{escape(last_known_likes_str)}</b>"

                        # Get playlist details if available
                        if playlist_details and not playlist_details.get("error"):
                            if playlist_details.get("is_empty"):
                                console_output += f"\n  (Playlist is empty)"
                                email_output += f"\n  (Playlist is empty)"
                                html_output += f"<br>&nbsp;&nbsp;(Playlist is empty)"
                            else:
                                # Songs count
                                console_output += f"\n  Songs: {playlist_details.get('songs_count', 0)}"
                                email_output += f"\n  Songs: {playlist_details.get('songs_count', 0)}"
                                html_output += f"<br>&nbsp;&nbsp;Songs: <b>{playlist_details.get('songs_count', 0)}</b>"

                                # Duration
                                duration_str = display_time(playlist_details.get('duration_seconds', 0))
                                console_output += f"\n  Duration: {duration_str}"
                                email_output += f"\n  Duration: {duration_str}"
                                html_output += f"<br>&nbsp;&nbsp;Duration: <b>{escape(duration_str)}</b>"

                                # Creation date
                                if playlist_details.get('creation_date'):
                                    creation_info = f"{playlist_details.get('creation_date')} ({playlist_details.get('creation_date_since', '')} ago)"
                                    console_output += f"\n  Creation date: {creation_info}"
                                    email_output += f"\n  Creation date: {creation_info}"
                                    html_output += f"<br>&nbsp;&nbsp;Creation date: <b>{escape(playlist_details.get('creation_date'))}</b> ({escape(playlist_details.get('creation_date_since', ''))} ago)"

                                # Last update date
                                if playlist_details.get('update_date'):
                                    update_info = f"{playlist_details.get('update_date')} ({playlist_details.get('update_date_since', '')} ago)"
                                    console_output += f"\n  Last update: {update_info}"
                                    email_output += f"\n  Last update: {update_info}"
                                    html_output += f"<br>&nbsp;&nbsp;Last update: <b>{escape(playlist_details.get('update_date'))}</b> ({escape(playlist_details.get('update_date_since', ''))} ago)"

                        print(console_output)
                        list_of_removed_f_list += email_output
                        list_of_removed_f_list_html += html_output

                        # Add empty line between playlists if not the last one and there are multiple playlists
                        if len(removed_f_list) > 1 and idx < len(removed_f_list) - 1:
                            print()
                            list_of_removed_f_list += "\n\n"
                            list_of_removed_f_list_html += "<br><br>"
                        else:
                            list_of_removed_f_list += "\n"
                            list_of_removed_f_list_html += "<br>"
                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), f_removed_csv, username, p_name, "")
                    except Exception as e:
                        print_operation_error("A CSV event could not be written", e)
            else:
                if "name" in f_dict and "uri" in f_dict:
                    print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                    list_of_removed_f_list += f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]"
                    list_of_removed_f_list_html += f"- <a href=\"{escape_html_attr(spotify_convert_uri_to_url(f_dict['uri']))}\">{escape(f_dict['name'])}</a>"

                    # Add empty line between items if not the last one and there are multiple items
                    if len(removed_f_list) > 1 and idx < len(removed_f_list) - 1:
                        print()
                        list_of_removed_f_list += "\n\n"
                        list_of_removed_f_list_html += "<br><br>"
                    else:
                        list_of_removed_f_list += "\n"
                        list_of_removed_f_list_html += "<br>"

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), f_removed_csv, username, f_dict["name"], "")
                    except Exception as e:
                        print_operation_error("A CSV event could not be written", e)
        if removed_f_list:
            print()

    if is_playlist and f_diff != 0 and not list_of_added_f_list.strip() and not list_of_removed_f_list.strip():
        print("Added", list_of_added_f_list.strip())
        print("Removed", list_of_removed_f_list.strip())
        return True

    f_list_to_save = []
    f_list_to_save.append(f_count)
    f_list_to_save.append(f_list)
    try:
        with open(f_file, 'w', encoding="utf-8") as f:
            json.dump(f_list_to_save, f, indent=2)
    except Exception as e:
        print_operation_error(f"The {str(f_str).lower()} list could not be saved to '{f_file}'", e)

    try:
        if csv_file_name:
            write_csv_entry(csv_file_name, now_local_naive(), f_str, username, f_old_count, f_count)
    except Exception as e:
        print_operation_error("A CSV event could not be written", e)

    notification_type = "profile" if is_playlist else "followers_followings"
    is_follower_event = f_str == "Followers" or f_str == "Followings"
    email_enabled = bool(profile_notification and (not is_follower_event or FOLLOWERS_FOLLOWINGS_NOTIFICATION))
    webhook_allowed = bool(profile_notification) if webhook_notification_allowed is None else bool(webhook_notification_allowed)
    webhook_enabled = bool(webhook_allowed and webhook_event_enabled(notification_type))
    if not email_enabled and not webhook_enabled:
        return False

    if playlist_membership_only_change:
        m_subject = f"Spotify user {username} {str(f_str).lower()} have changed! (total remains {f_count})"
        m_body = f"{f_str} changed for user {username} while the total remained {f_count}\n{removed_f_list_mbody}{list_of_removed_f_list}{added_f_list_mbody}{list_of_added_f_list}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
        m_body_html = f"<html><head></head><body>{escape(f_str)} changed for user <b>{escape(username)}</b> while the total remained <b>{f_count}</b><br>{removed_f_list_mbody_html}{list_of_removed_f_list_html}{added_f_list_mbody_html}{list_of_added_f_list_html}<br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
    else:
        m_subject = f"Spotify user {username} {str(f_str).lower()} number has changed! ({f_diff_str}, {f_old_count} -> {f_count})"
        m_body = f"{f_str} number changed {f_str_by_or_from} user {username} from {f_old_count} to {f_count} ({f_diff_str})\n{removed_f_list_mbody}{list_of_removed_f_list}{added_f_list_mbody}{list_of_added_f_list}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
        m_body_html = f"<html><head></head><body>{escape(f_str)} number changed {escape(f_str_by_or_from)} user <b>{escape(username)}</b> from <b>{f_old_count}</b> to <b>{f_count}</b> (<b>{escape(f_diff_str)}</b>)<br>{removed_f_list_mbody_html}{list_of_removed_f_list_html}{added_f_list_mbody_html}{list_of_added_f_list_html}<br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"

    selected_notification_image_url = select_notification_image_url(playlist_notification_image_url, profile_image_url=notification_image_url)
    send_notification_channels(notification_type, m_subject, m_body, m_body_html, email_enabled=email_enabled, webhook_enabled=webhook_enabled, image_url=selected_notification_image_url, email_image_url=playlist_notification_image_url if is_playlist else "")

    return False


# Saves user's profile pic to selected file name from a trusted Spotify CDN host with a bounded read
def save_profile_pic(user_image_url, image_file_name):
    try:
        if not spotify_image_url_is_allowed(user_image_url):
            raise ValueError("profile picture URL must use a Spotify HTTPS CDN host")

        debug_print(f"HTTP GET {user_image_url} [profile image] stream=True")
        image_response = req.get(user_image_url, headers={'User-Agent': USER_AGENT}, timeout=FUNCTION_TIMEOUT, stream=True, verify=VERIFY_SSL, allow_redirects=False)
        with image_response:
            debug_print(f"HTTP GET {user_image_url} [profile image] -> {image_response.status_code}")
            image_response.raise_for_status()
            if image_response.status_code != 200:
                raise ValueError(f"profile picture request returned HTTP {image_response.status_code}")

            content_length = (image_response.headers or {}).get("Content-Length")
            if content_length is not None and int(content_length) > NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES:
                raise ValueError(f"profile picture exceeds {NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES} bytes")

            image_bytes = bytearray()
            for chunk in image_response.iter_content(chunk_size=NOTIFICATION_IMAGE_DOWNLOAD_CHUNK_BYTES):
                if not chunk:
                    continue
                image_bytes.extend(chunk)
                if len(image_bytes) > NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES:
                    raise ValueError(f"profile picture exceeds {NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES} bytes")

            url_time = image_response.headers.get('last-modified')

        if not image_bytes:
            raise ValueError("profile picture response was empty")

        url_time_in_tz_ts = 0
        if url_time:
            url_time_in_tz = parsedate_to_datetime(url_time).astimezone(pytz.timezone(LOCAL_TIMEZONE))
            url_time_in_tz_ts = int(url_time_in_tz.timestamp())

        # Written only once the complete bounded body arrived so a capped or failed download cannot truncate a saved picture
        with open(image_file_name, 'wb') as f:
            f.write(image_bytes)
        if url_time_in_tz_ts:
            os.utime(image_file_name, (url_time_in_tz_ts, url_time_in_tz_ts))
        debug_print(f"save_profile_pic(): saved image to {image_file_name}")
        return True
    except Exception as e:
        debug_print(f"save_profile_pic(): failed for url={user_image_url}: {sanitize_error_text(e)}")
        return False


# Compares two image files
def compare_images(path1, path2):
    try:
        with open(path1, 'rb') as f1, open(path2, 'rb') as f2:
            for line1, line2 in zip_longest(f1, f2, fillvalue=None):
                if line1 == line2:
                    continue
                else:
                    return False
            return True
    except Exception as e:
        print_operation_error("Profile pictures could not be compared", e)
        return False


# Return tracks in list_a that are not in list_b, ignoring added_by
def diff_tracks(list_a, list_b):
    def sig(d):
        return (d.get("uri"), d.get("artist"), d.get("track"), d.get("duration"), d.get("added_at"), d.get("added_by_id") or "")

    set_b = {sig(x) for x in list_b}
    return [x for x in list_a if sig(x) not in set_b]


# Splits an assignment value from an inline comment while ignoring hashes inside strings
def _split_inline_comment_preserving_strings(rhs: str) -> Tuple[str, str]:
    in_single = False
    in_double = False
    escaped = False
    for index, character in enumerate(rhs):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == "'" and not in_double:
            in_single = not in_single
            continue
        if character == '"' and not in_single:
            in_double = not in_double
            continue
        if character == "#" and not in_single and not in_double:
            return rhs[:index].rstrip(), rhs[index:].rstrip()
    return rhs.rstrip(), ""


# Formats one supported runtime value as a valid Python config literal
def _format_config_value(value, prefer_double_quotes: bool) -> str:
    if isinstance(value, str):
        if prefer_double_quotes:
            return json.dumps(value, ensure_ascii=True)
        escaped = value.encode("unicode_escape").decode("ascii").replace("'", "\\'")
        return f"'{escaped}'"
    if value is None or isinstance(value, (bool, int, float, list, tuple, dict)):
        return repr(value)
    raise TypeError(f"Unsupported config value type: {type(value).__name__}")


# Returns the setting names declared by the trusted built-in config template
def _config_allowed_names() -> FrozenSet[str]:
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    return frozenset(statement.targets[0].id for statement in template_tree.body if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name))


# Parses allowlisted literal config assignments without executing any file content
def parse_config_content(content: str, filename: str = "<config>") -> Dict[str, Any]:
    tree = ast.parse(content, filename, "exec")
    allowed_names = _config_allowed_names()
    parsed_values: Dict[str, Any] = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            raise ValueError(f"Line {getattr(statement, 'lineno', '?')}: only NAME = value assignments are allowed")
        name = statement.targets[0].id
        if name not in allowed_names:
            raise ValueError(f"Line {statement.lineno}: unsupported configuration setting {name!r}")
        try:
            parsed_values[name] = ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as exc:
            raise ValueError(f"Line {statement.lineno}: {name} must be a plain value such as a number, string, True, False, None, list, tuple or dict") from exc
    return parsed_values


# Validates config content through the same restricted parser used at startup
def validate_config_content(content: str, filename: str = "<generated-config>") -> None:
    parse_config_content(content, filename)


# Renders CONFIG_BLOCK with current non-secret values and original secret placeholders
def generate_config_with_current_values(values=None) -> str:
    current_values = globals() if values is None else values
    assignment_pattern = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=\s*(.*)$")
    output_lines = []
    for line in CONFIG_BLOCK.strip("\n").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            output_lines.append(line)
            continue
        match = assignment_pattern.match(line)
        if not match:
            output_lines.append(line)
            continue
        variable = match.group(1)
        expression, comment = _split_inline_comment_preserving_strings(match.group(2))
        expression_stripped = expression.strip()
        if expression_stripped.endswith(("{", "[", "(")) and not any(character in expression_stripped for character in ("}", "]", ")")):
            output_lines.append(line)
            continue
        try:
            compile(f"{variable} = {expression}\n", "<config-template-line>", "exec")
        except SyntaxError:
            output_lines.append(line)
            continue
        if variable in SENSITIVE_CONFIG_KEYS or variable not in current_values:
            output_lines.append(line)
            continue
        rendered_value = _format_config_value(current_values[variable], prefer_double_quotes=expression_stripped.startswith('"'))
        rendered_line = f"{variable} = {rendered_value}"
        if comment:
            rendered_line = f"{rendered_line}  {comment}"
        output_lines.append(rendered_line)
    rendered = "\n".join(output_lines) + "\n"
    validate_config_content(rendered)
    return rendered


# Confirms replacement of an existing generated config or requires explicit force
def confirm_config_replacement(destination, force: bool = False, interactive=None, input_func=None) -> bool:
    destination_path = Path(destination).expanduser()
    if not destination_path.exists() or force:
        return True
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise FileExistsError(f"Config file '{destination_path}' already exists. Re-run with --force to replace it after a timestamped backup.")
    prompt = input if input_func is None else input_func
    try:
        answer = prompt(f"Config file '{destination_path}' exists. Replace it and create a timestamped backup? [y/N]: ").strip().casefold()
    except (EOFError, KeyboardInterrupt):
        answer = ""
    return answer in ("y", "yes")


# Writes validated config content atomically and backs up an existing destination
def write_config_file(destination, content: str) -> dict:
    destination_path = Path(destination).expanduser()
    validate_config_content(content, str(destination_path))
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    backup_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if destination_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            for collision_index in range(1000):
                collision_suffix = "" if collision_index == 0 else f"-{collision_index:02d}"
                candidate = destination_path.with_name(f"{destination_path.name}.{timestamp}{collision_suffix}.bak")
                try:
                    with destination_path.open("rb") as source_file, candidate.open("xb") as backup_file:
                        shutil.copyfileobj(source_file, backup_file)
                        backup_file.flush()
                        os.fsync(backup_file.fileno())
                    backup_path = candidate
                    break
                except FileExistsError:
                    continue
                except Exception:
                    if candidate.exists():
                        candidate.unlink()
                    raise
            if backup_path is None:
                raise FileExistsError(f"Could not create a unique backup for '{destination_path}'")
        os.replace(str(temporary_path), str(destination_path))
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return {"path": str(destination_path), "backup_path": str(backup_path) if backup_path is not None else None}


class WebhookConfigurationError(Exception):
    pass


class SpDcConfigurationError(Exception):
    pass


class BrowserCookieImportError(Exception):
    pass


# Returns a writable dotenv destination for private webhook setup
def resolve_webhook_env_path(env_file=None, cwd=None) -> Path:
    if env_file is not None and str(env_file).casefold() == "none":
        raise WebhookConfigurationError("Webhook setup requires a dotenv destination. Replace '--env-file none' with a writable path.")
    base_directory = Path.cwd() if cwd is None else Path(cwd)
    destination = base_directory / ".env" if env_file is None else Path(env_file).expanduser()
    return destination.resolve()


# Returns a writable dotenv destination for private Spotify cookie setup
def resolve_sp_dc_env_path(env_file=None, cwd=None) -> Path:
    if env_file is not None and str(env_file).casefold() == "none":
        raise SpDcConfigurationError("Private Spotify cookie setup requires a dotenv destination. Replace '--env-file none' with a writable path.")
    base_directory = Path.cwd() if cwd is None else Path(cwd)
    destination = base_directory / ".env" if env_file is None else Path(env_file).expanduser()
    return destination.resolve()


# Checks whether a dotenv file already contains one named assignment
def _dotenv_contains_key(destination, key, error_type: Type[Exception] = WebhookConfigurationError) -> bool:
    destination_path = Path(destination)
    if not destination_path.exists():
        return False
    try:
        lines = destination_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise error_type(f"Could not read private settings file '{destination_path}'. Check that it is a readable UTF-8 file.") from None
    assignment_pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")
    return any(assignment_pattern.match(line) for line in lines)


# Quotes one secret value for lossless parsing by python-dotenv
def _format_dotenv_value(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Dotenv secret values must be strings")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    return f'"{escaped}"'


# Updates allowed secrets in a dotenv file through an atomic replacement
def update_dotenv_file(destination, updates) -> dict:
    if not hasattr(updates, "items"):
        raise TypeError("Dotenv updates must be a mapping")
    update_items = list(updates.items())
    for key, value in update_items:
        if not isinstance(key, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or key not in SECRET_KEYS:
            raise ValueError(f"Unsupported dotenv key: {key!r}")
        if not isinstance(value, str):
            raise TypeError(f"Dotenv value for {key} must be a string")

    destination_path = Path(destination).expanduser()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = destination_path.read_text(encoding="utf-8").splitlines() if destination_path.exists() else []
    update_keys = {key for key, _ in update_items}
    values_by_key = dict(update_items)
    seen_keys = set()
    output_lines = []
    assignment_pattern = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
    for line in existing_lines:
        match = assignment_pattern.match(line)
        key = match.group(1) if match else None
        if key not in update_keys:
            output_lines.append(line)
            continue
        if key in seen_keys:
            continue
        output_lines.append(f"{key}={_format_dotenv_value(values_by_key[key])}")
        seen_keys.add(key)
    for key, value in update_items:
        if key not in seen_keys:
            output_lines.append(f"{key}={_format_dotenv_value(value)}")
            seen_keys.add(key)
    content = "\n".join(output_lines)
    if output_lines:
        content += "\n"

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if os.name == "posix":
            os.chmod(str(temporary_path), 0o600)
        os.replace(str(temporary_path), str(destination_path))
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return {"path": str(destination_path), "updated_keys": tuple(key for key, _ in update_items)}


# Identifies network-shaped Spotify authentication failures without returning raw exception text
def _looks_like_network_failure(error) -> bool:
    if isinstance(error, req.RequestException):
        return True
    error_text = str(error).lower()
    return any(term in error_text for term in ("connection", "connectivity", "timeout", "timed out", "name resolution", "dns", "proxy", "ssl", "500", "502", "503", "504"))


# Validates one sp_dc cookie through token acquisition and an authenticated Spotify request
def validate_sp_dc_cookie(sp_dc) -> bool:
    global TOKEN_SOURCE, USER_AGENT, DEBUG_MODE
    if not isinstance(sp_dc, str) or not sp_dc:
        raise SpDcConfigurationError("No nonempty sp_dc cookie was entered.")

    previous_token_source = TOKEN_SOURCE
    previous_user_agent = USER_AGENT
    previous_debug_mode = DEBUG_MODE
    TOKEN_SOURCE = "cookie"
    DEBUG_MODE = False
    if not USER_AGENT:
        USER_AGENT = get_random_user_agent()
    try:
        try:
            token_data = refresh_access_token_from_sp_dc(sp_dc)
        except Exception as exc:
            if _looks_like_network_failure(exc):
                raise SpDcConfigurationError("A network or connectivity failure prevented Spotify cookie validation. The private settings file was not changed.") from None
            raise SpDcConfigurationError("The entered sp_dc cookie is invalid or expired. The private settings file was not changed.") from None

        access_token = token_data.get("access_token") if isinstance(token_data, dict) else None
        client_id = token_data.get("client_id", "") if isinstance(token_data, dict) else ""
        if not isinstance(access_token, str) or not access_token or not check_token_validity(access_token, client_id, USER_AGENT):
            raise SpDcConfigurationError("Spotify authentication rejected the entered sp_dc cookie. The private settings file was not changed.")
    finally:
        TOKEN_SOURCE = previous_token_source
        USER_AGENT = previous_user_agent
        DEBUG_MODE = previous_debug_mode
    return True


# Returns a user-facing label for one supported browser
def browser_label(browser):
    return "Firefox" if browser == "firefox" else browser.capitalize()


# Returns normal Firefox profile roots for the selected platform
def _firefox_profile_roots(system_name=None, home=None, environ=None):
    selected_system = platform.system() if system_name is None else system_name
    home_path = Path.home() if home is None else Path(home)
    environment = os.environ if environ is None else environ
    if selected_system == "Darwin":
        return [home_path / "Library/Application Support/Firefox"]
    if selected_system == "Windows":
        appdata = environment.get("APPDATA")
        return [Path(appdata) / "Mozilla/Firefox"] if appdata else [home_path / "AppData/Roaming/Mozilla/Firefox"]
    if selected_system == "Linux":
        return [home_path / ".mozilla/firefox", home_path / "snap/firefox/common/.mozilla/firefox", home_path / ".var/app/org.mozilla.firefox/.mozilla/firefox"]
    return []


# Builds one normalized browser profile record
def _browser_profile_record(profile_dir, friendly_name, cookie_file):
    return {"dir": profile_dir.name, "name": friendly_name or profile_dir.name, "path": str(profile_dir), "cookie_file": str(cookie_file)}


# Adds one usable profile record without duplicating its cookie database
def _add_browser_profile(profiles_by_cookie, profile_dir, friendly_name):
    cookie_file = profile_dir / "cookies.sqlite"
    if not cookie_file.is_file():
        return
    cookie_key = str(cookie_file.resolve())
    profiles_by_cookie.setdefault(cookie_key, _browser_profile_record(profile_dir, friendly_name, cookie_file))


# Discovers usable Firefox profiles from metadata plus directory scans
def discover_firefox_profiles(system_name=None, home=None, environ=None):
    profiles_by_cookie = {}
    for root in _firefox_profile_roots(system_name=system_name, home=home, environ=environ):
        profiles_ini = root / "profiles.ini"
        if profiles_ini.is_file():
            parser = configparser.RawConfigParser()
            try:
                with profiles_ini.open("r", encoding="utf-8") as profiles_file:
                    parser.read_file(profiles_file)
                for section in parser.sections():
                    if not section.lower().startswith("profile") or not parser.has_option(section, "Path"):
                        continue
                    configured_path = os.path.expandvars(os.path.expanduser(parser.get(section, "Path")))
                    profile_dir = Path(configured_path)
                    if parser.get(section, "IsRelative", fallback="1") != "0":
                        profile_dir = root / profile_dir
                    _add_browser_profile(profiles_by_cookie, profile_dir, parser.get(section, "Name", fallback=profile_dir.name))
            except (OSError, UnicodeError, configparser.Error):
                pass
        for profile_parent in (root, root / "Profiles"):
            if not profile_parent.is_dir():
                continue
            try:
                profile_dirs = sorted((entry for entry in profile_parent.iterdir() if entry.is_dir()), key=lambda entry: entry.name.lower())
            except OSError:
                continue
            for profile_dir in profile_dirs:
                friendly_name = profile_dir.name.split(".", 1)[1] if "." in profile_dir.name else profile_dir.name
                _add_browser_profile(profiles_by_cookie, profile_dir, friendly_name)
    return sorted(profiles_by_cookie.values(), key=lambda profile: (profile["name"].lower(), profile["dir"].lower(), profile["cookie_file"]))


# Formats profile choices without exposing cookie values
def _format_profile_choices(profiles):
    return ", ".join(f"{profile['dir']} ({profile['name']})" if profile["name"] != profile["dir"] else profile["dir"] for profile in profiles)


# Selects one browser profile explicitly or automatically or through a prompt
def select_browser_profile(profiles, browser, requested_profile=None, interactive=None, input_func=None):
    label = browser_label(browser)
    if not profiles:
        raise BrowserCookieImportError(f"No usable {label} profiles found. Sign in to Spotify in {label} or pass --cookie-file PATH.")
    if requested_profile:
        requested = requested_profile.casefold()
        directory_matches = [profile for profile in profiles if profile["dir"].casefold() == requested]
        friendly_matches = [profile for profile in profiles if profile["name"].casefold() == requested]
        matches = directory_matches or friendly_matches
        if len(matches) == 1:
            return matches[0]
        choices = _format_profile_choices(profiles)
        if len(matches) > 1:
            raise BrowserCookieImportError(f"{label} profile name '{requested_profile}' is ambiguous. Pass one profile directory with --browser-profile. Choices: {choices}")
        raise BrowserCookieImportError(f"Unknown {label} profile '{requested_profile}'. Choices: {choices}")
    if len(profiles) == 1:
        return profiles[0]
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    choices = _format_profile_choices(profiles)
    if not terminal_is_interactive:
        raise BrowserCookieImportError(f"Multiple {label} profiles found: {choices}. Pass --browser-profile PROFILE to select one in a noninteractive environment.")
    print(f"\nMultiple {label} profiles found:")
    for index, profile in enumerate(profiles, start=1):
        print(f"  {index}) {profile['name']} [{profile['dir']}] - {profile['cookie_file']}")
    prompt = input if input_func is None else input_func
    try:
        choice = int(prompt("Select profile number (0 to cancel): "))
    except (EOFError, ValueError):
        raise BrowserCookieImportError("Browser cookie import cancelled because the profile selection was invalid.") from None
    if choice == 0:
        raise BrowserCookieImportError("Browser cookie import cancelled.")
    if choice < 1 or choice > len(profiles):
        raise BrowserCookieImportError("Browser cookie import cancelled because the profile selection was invalid.")
    return profiles[choice - 1]


# Quotes a SQLite identifier obtained from database schema metadata
def _sqlite_identifier(identifier):
    return '"' + identifier.replace('"', '""') + '"'


# Converts an optional SQLite cookie field into a comparable number
def _numeric_cookie_field(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# Reads the best Spotify sp_dc cookie from a Firefox SQLite database
def read_firefox_sp_dc(cookie_file, now=None):
    cookie_path = Path(cookie_file).expanduser()
    if not cookie_path.is_file():
        raise BrowserCookieImportError(f"Firefox cookie database '{cookie_path}' was not found. Pass a valid cookies.sqlite path with --cookie-file.")
    try:
        with sqlite3.connect(cookie_path.resolve().as_uri() + "?immutable=1", uri=True) as connection:
            columns = connection.execute("PRAGMA table_info(moz_cookies)").fetchall()
            column_names = {str(row[1]).lower(): str(row[1]) for row in columns}
            if "name" not in column_names or "value" not in column_names:
                raise sqlite3.DatabaseError("missing required cookie columns")
            domain_key = "host" if "host" in column_names else "basedomain" if "basedomain" in column_names else None
            if domain_key is None:
                raise sqlite3.DatabaseError("missing cookie domain column")
            selected_keys = ["value", domain_key]
            last_access_key = "lastaccessed" if "lastaccessed" in column_names else "last_accessed" if "last_accessed" in column_names else None
            expiry_key = next((key for key in ("expiry", "expires", "expirationdate") if key in column_names), None)
            if last_access_key:
                selected_keys.append(last_access_key)
            if expiry_key:
                selected_keys.append(expiry_key)
            selected_columns = ", ".join(_sqlite_identifier(column_names[key]) for key in selected_keys)
            name_column = _sqlite_identifier(column_names["name"])
            value_column = _sqlite_identifier(column_names["value"])
            domain_column = _sqlite_identifier(column_names[domain_key])
            query = f"SELECT {selected_columns} FROM moz_cookies WHERE {name_column} = ? AND {value_column} IS NOT NULL AND {value_column} != '' AND (lower(ltrim({domain_column}, '.')) = ? OR lower(ltrim({domain_column}, '.')) LIKE ?)"
            rows = connection.execute(query, ("sp_dc", "spotify.com", "%.spotify.com")).fetchall()
    except (sqlite3.DatabaseError, sqlite3.OperationalError, OSError):
        raise BrowserCookieImportError("Could not read the Firefox cookie database. Close Firefox then retry or pass --cookie-file with a readable cookies.sqlite copy.") from None
    if not rows:
        raise BrowserCookieImportError("No sp_dc cookie for spotify.com was found in the selected Firefox profile. Sign in to Spotify in Firefox then retry.")
    now_value = time.time() if now is None else now
    last_access_index = selected_keys.index(last_access_key) if last_access_key else None
    expiry_index = selected_keys.index(expiry_key) if expiry_key else None

    # Ranks nonexpired cookies first then uses stable fields for deterministic selection
    def cookie_rank(row):
        last_accessed = _numeric_cookie_field(row[last_access_index]) if last_access_index is not None else 0.0
        expiry = _numeric_cookie_field(row[expiry_index]) if expiry_index is not None else 0.0
        nonexpired = 1 if expiry <= 0 or expiry > now_value else 0
        return nonexpired, last_accessed, expiry, str(row[1]).lower(), str(row[0])
    return str(max(rows, key=cookie_rank)[0])


# Returns the standard Chromium user-data directory for one browser and platform
def get_chromium_user_data_dir(browser, system_name=None, home=None):
    selected_system = platform.system() if system_name is None else system_name
    relative_path = CHROMIUM_USER_DATA_DIRS.get(selected_system, {}).get(browser)
    if relative_path is None:
        return None
    home_path = Path.home() if home is None else Path(home)
    return home_path / relative_path


# Resolves a Chromium profile cookie database with modern layout preference
def resolve_chromium_cookie_file(user_data_dir, profile_dir):
    profile_path = Path(user_data_dir) / profile_dir
    for relative_path in (Path("Network") / "Cookies", Path("Cookies")):
        candidate = profile_path / relative_path
        if candidate.is_file():
            return candidate
    return None


# Discovers usable Chrome or Brave or Chromium profiles and display names
def discover_chromium_profiles(browser, system_name=None, home=None, user_data_dir=None):
    base_path = Path(user_data_dir) if user_data_dir is not None else get_chromium_user_data_dir(browser, system_name=system_name, home=home)
    if base_path is None or not base_path.is_dir():
        return []
    friendly_names = {}
    try:
        with (base_path / "Local State").open("r", encoding="utf-8") as local_state_file:
            info_cache = json.load(local_state_file).get("profile", {}).get("info_cache", {})
        friendly_names = {directory: details.get("name") or directory for directory, details in info_cache.items() if isinstance(details, dict)}
    except (OSError, UnicodeError, ValueError, AttributeError):
        pass
    profiles = []
    try:
        entries = sorted(base_path.iterdir(), key=lambda entry: entry.name.lower())
    except OSError:
        return []
    for entry in entries:
        if not entry.is_dir() or (entry.name != "Default" and not entry.name.startswith("Profile ")):
            continue
        cookie_path = resolve_chromium_cookie_file(base_path, entry.name)
        if cookie_path is not None:
            profiles.append({"dir": entry.name, "name": friendly_names.get(entry.name, entry.name), "path": str(entry), "cookie_file": str(cookie_path)})
    return profiles


# Calls pycookiecheat for Spotify through a narrow dynamically imported adapter
def _pycookiecheat_spotify_cookies(browser, cookie_file):
    try:
        from pycookiecheat import BrowserType, get_cookies
    except (ImportError, ModuleNotFoundError):
        executable = sys.executable or ("python" if platform.system() == "Windows" else "python3")
        install_command = _wizard_render_command([executable, "-m", "pip", "install", "spotify_profile_monitor[browser]"])
        raise BrowserCookieImportError(f"Chromium browser import requires the optional pycookiecheat dependency. Firefox needs no extra dependency. Install it through the active Python environment with:\n\n    {install_command}") from None
    browser_type = {"chrome": BrowserType.CHROME, "brave": BrowserType.BRAVE, "chromium": BrowserType.CHROMIUM}[browser]
    return get_cookies(SPOTIFY_WEB_BASE_URL, browser=browser_type, cookie_file=str(cookie_file))


# Converts a Chromium cookie failure into a secret-safe actionable message
def _safe_chromium_cookie_error(browser, error):
    label = browser_label(browser)
    error_text = str(error).lower()
    if any(term in error_text for term in ("keyring", "secretservice", "secret service", "password")):
        return f"Could not access the OS keyring needed to decrypt {label} cookies. Unlock the keyring then retry or use Firefox."
    if any(term in error_text for term in ("decrypt", "invalidtag", "encryption")):
        return f"Could not decrypt {label} cookies. Close {label} then retry or import from Firefox."
    if any(term in error_text for term in ("permission", "denied", "locked", "readonly", "unable to open")):
        return f"Could not access the {label} cookie database. Close {label} then check file permissions and retry or use Firefox."
    return f"Could not read {label} cookies. Confirm Spotify is signed in then close {label} and retry or use Firefox."


# Reads only the Spotify sp_dc value from a Chromium cookie collection
def read_chromium_sp_dc(browser, cookie_file, cookie_adapter=None, system_name=None):
    selected_system = platform.system() if system_name is None else system_name
    label = browser_label(browser)
    if selected_system == "Windows":
        raise BrowserCookieImportError(f"Importing {label} cookies is unavailable on Windows because current Chromium app-bound cookie encryption prevents reliable external access. Use Firefox instead.")
    cookie_path = Path(cookie_file).expanduser()
    if not cookie_path.is_file():
        raise BrowserCookieImportError(f"{label} cookie database '{cookie_path}' was not found. Pass a valid path with --cookie-file.")
    adapter = _pycookiecheat_spotify_cookies if cookie_adapter is None else cookie_adapter
    try:
        cookies = adapter(browser, cookie_path)
    except BrowserCookieImportError:
        raise
    except Exception as exc:
        raise BrowserCookieImportError(_safe_chromium_cookie_error(browser, exc)) from None
    sp_dc = cookies.get("sp_dc") if isinstance(cookies, dict) else next((getattr(cookie, "value", None) for cookie in cookies if getattr(cookie, "name", None) == "sp_dc"), None)
    if not isinstance(sp_dc, str) or not sp_dc:
        raise BrowserCookieImportError(f"No sp_dc cookie for spotify.com was found in the selected {label} profile. Sign in to Spotify in {label} then retry.")
    return sp_dc


# Resolves the browser import dotenv destination without parent discovery
def resolve_import_env_path(env_file=None, cwd=None):
    if env_file is not None and str(env_file).casefold() == "none":
        raise BrowserCookieImportError("Browser cookie import requires a dotenv destination. Replace '--env-file none' with a writable path.")
    base_directory = Path.cwd() if cwd is None else Path(cwd)
    destination = base_directory / DEFAULT_DOTENV_FILENAME if env_file is None else Path(env_file).expanduser()
    return destination.resolve()


# Runs extraction and validation plus confirmed atomic dotenv persistence
def run_browser_cookie_import(browser="firefox", browser_profile=None, cookie_file=None, env_file=None, force=False, interactive=None, input_func=None, config_path=None, target=None):
    destination = resolve_import_env_path(env_file)
    print(f"* Browser prerequisite: open {SPOTIFY_WEB_LOGIN_URL} in {browser_label(browser)} and sign in to the Spotify account used for monitoring")
    print(f"* Dotenv destination: {destination}")
    selected_system = platform.system()
    if browser in CHROMIUM_IMPORT_BROWSERS and selected_system == "Windows":
        raise BrowserCookieImportError(f"Importing {browser_label(browser)} cookies is unavailable on Windows because current Chromium app-bound cookie encryption prevents reliable external access. Use Firefox instead.")
    selected_profile = None
    if cookie_file is not None:
        selected_cookie_file = Path(cookie_file).expanduser()
        if browser_profile:
            print("* Note: --cookie-file takes precedence over --browser-profile")
    elif browser == "firefox":
        selected_profile = select_browser_profile(discover_firefox_profiles(), browser, requested_profile=browser_profile, interactive=interactive, input_func=input_func)
        selected_cookie_file = Path(selected_profile["cookie_file"])
    else:
        selected_profile = select_browser_profile(discover_chromium_profiles(browser), browser, requested_profile=browser_profile, interactive=interactive, input_func=input_func)
        selected_cookie_file = Path(selected_profile["cookie_file"])
    if selected_profile is not None:
        print(f"* Browser profile: {selected_profile['name']} [{selected_profile['dir']}]")
    print(f"* Cookie database: {selected_cookie_file}")
    sp_dc = read_firefox_sp_dc(selected_cookie_file) if browser == "firefox" else read_chromium_sp_dc(browser, selected_cookie_file)
    print("* Cookie extracted. Validating it with Spotify ...")
    try:
        validate_sp_dc_cookie(sp_dc)
    except SpDcConfigurationError as exc:
        raise BrowserCookieImportError(sanitize_error_text(exc)) from None
    print("* Spotify cookie validation succeeded")
    if _dotenv_contains_key(destination, "SP_DC_COOKIE", BrowserCookieImportError) and not force:
        terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
        if not terminal_is_interactive:
            raise BrowserCookieImportError(f"Dotenv destination '{destination}' already contains SP_DC_COOKIE. Re-run with --force to replace it in a noninteractive environment.")
        prompt = input if input_func is None else input_func
        try:
            confirmed = prompt(f"Replace SP_DC_COOKIE in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except EOFError:
            confirmed = False
        if not confirmed:
            raise BrowserCookieImportError("Browser cookie import cancelled. The dotenv file was not changed.")
    print(f"* Writing SP_DC_COOKIE to: {destination}")
    try:
        update_dotenv_file(destination, {"SP_DC_COOKIE": sp_dc})
    except Exception:
        raise BrowserCookieImportError(f"Could not update dotenv destination '{destination}'. Check the path and file permissions.") from None
    print("* Browser cookie import completed successfully\n")
    method = _wizard_install_method()
    selected_config = config_path or find_config_file()
    _wizard_print_command("Check authentication and the target:", _wizard_action_command(method, "--doctor", selected_config, destination, target or "SPOTIFY_TARGET"))
    _wizard_print_command("After Doctor passes, start monitoring:", _wizard_action_command(method, "", selected_config, destination, target or "SPOTIFY_TARGET"))
    return str(destination)


# Validates and atomically stores one privately entered sp_dc cookie
def run_set_sp_dc(env_file=None, interactive=None, input_func=None, getpass_func=None, config_path=None) -> str:
    destination = resolve_sp_dc_env_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise SpDcConfigurationError("--set-sp-dc requires an interactive terminal. Run it in a terminal window so the cookie stays hidden while you paste it.")
    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "SP_DC_COOKIE", SpDcConfigurationError):
        try:
            confirmed = prompt(f"Replace SP_DC_COOKIE in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            confirmed = False
        if not confirmed:
            raise SpDcConfigurationError("Spotify cookie setup was cancelled. The private settings file was not changed.")
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        sp_dc = hidden_prompt("Enter sp_dc privately (input hidden): ").strip()
    except (EOFError, KeyboardInterrupt):
        raise SpDcConfigurationError("Spotify cookie setup was cancelled. The private settings file was not changed.") from None
    if not sp_dc:
        raise SpDcConfigurationError("No nonempty sp_dc cookie was entered. The private settings file was not changed.")
    print("* Validating the entered Spotify cookie before changing the private settings file ...")
    validate_sp_dc_cookie(sp_dc)
    try:
        update_dotenv_file(destination, {"SP_DC_COOKIE": sp_dc})
    except Exception:
        raise SpDcConfigurationError(f"Could not save SP_DC_COOKIE in '{destination}'. Check file permissions or choose another path with --env-file.") from None
    print("* SP_DC_COOKIE validation succeeded")
    print(f"* Updated private settings file: {destination}")
    method = _wizard_install_method()
    recovery_target = None if TARGET_USER_URI_ID else "SPOTIFY_TARGET"
    _wizard_print_command("Check authentication and the target:", _wizard_action_command(method, "--doctor", config_path or find_config_file(), destination, recovery_target))
    _wizard_print_command("After Doctor passes, start monitoring:", _wizard_action_command(method, "", config_path or find_config_file(), destination, recovery_target))
    return str(destination)


# Checks and safely stores one privately entered webhook URL
def run_set_webhook_url(env_file=None, interactive=None, input_func=None, getpass_func=None, config_path=None) -> str:
    destination = resolve_webhook_env_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise WebhookConfigurationError("--set-webhook-url requires an interactive terminal. Run it in a terminal window so the webhook URL stays hidden while you paste it.")
    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "WEBHOOK_URL"):
        try:
            confirmed = prompt(f"Replace the saved webhook URL in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            confirmed = False
        if not confirmed:
            raise WebhookConfigurationError("Webhook setup was cancelled. The private settings file was not changed.")
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        webhook_url = hidden_prompt("Paste the Discord or ntfy webhook URL (input hidden): ").strip()
    except (EOFError, KeyboardInterrupt):
        raise WebhookConfigurationError("Webhook setup was cancelled. The private settings file was not changed.") from None
    if not validate_webhook_url(webhook_url):
        raise WebhookConfigurationError("That does not look like a complete HTTPS webhook URL. The private settings file was not changed.")
    try:
        update_dotenv_file(destination, {"WEBHOOK_URL": webhook_url})
    except Exception:
        raise WebhookConfigurationError(f"Could not save the webhook URL in '{destination}'. Check file permissions or choose another path with --env-file.") from None
    test_command = _wizard_action_command(_wizard_install_method(), "--send-test-webhook", config_path, destination)
    print("* Webhook URL looks valid")
    print(f"* Updated private settings file: {destination}")
    print(f"* Send a test webhook:\n  {test_command}")
    return str(destination)


# Finds an optional config file
def find_config_file(cli_path=None):
    """
    Search for an optional config file in:
      1) CLI-provided path (must exist if given)
      2) ./{DEFAULT_CONFIG_FILENAME}
      3) ~/.{DEFAULT_CONFIG_FILENAME}
      4) script-directory/{DEFAULT_CONFIG_FILENAME}
    """

    if cli_path:
        p = Path(os.path.expanduser(cli_path))
        return str(p) if p.is_file() else None

    candidates = [
        Path.cwd() / DEFAULT_CONFIG_FILENAME,
        Path.home() / f".{DEFAULT_CONFIG_FILENAME}",
        Path(__file__).parent / DEFAULT_CONFIG_FILENAME,
    ]

    for p in candidates:
        if p.is_file():
            return str(p)
    return None


# Loads one UTF-8 config atomically and reports exact failures safely
def load_config_file(config_path, namespace=None, error_out=None, report_errors=True):
    selected_namespace = globals() if namespace is None else namespace
    try:
        content = Path(config_path).read_text(encoding="utf-8")
        # Parsed as data rather than executed, so a config file picked up from the working directory cannot run code
        parsed_values = parse_config_content(content, str(config_path))
        selected_namespace.update(parsed_values)
        return True
    except SyntaxError as exc:
        details = [f"Config file '{config_path}' has invalid Python syntax"]
        if exc.lineno is not None:
            details.append(f"line {exc.lineno}")
        if exc.text:
            details.append(f"Source: {exc.text.rstrip()}")
        details.append(f"Parser: {exc.msg}")
        detail = " | ".join(details)
        summary = details[0] + (f" at line {exc.lineno}" if exc.lineno is not None else "")
    # Checked before ValueError because UnicodeDecodeError derives from it
    except UnicodeDecodeError:
        detail = f"Config file '{config_path}' is not valid UTF-8"
        summary = detail
    except ValueError as exc:
        detail = f"Config file '{config_path}' contains unsupported content: {exc}"
        summary = "The configuration file contains unsupported content"
    except Exception as exc:
        detail = f"Config file '{config_path}' failed with {type(exc).__name__}: {sanitize_error_text(exc)}"
        summary = "The configuration file could not be loaded"
    advice = classify_recovery_error(context="config_invalid", detail=detail)
    advice = make_recovery_advice(advice.code, summary, advice.fix, advice.retryable, advice.detail)
    check = make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice.fix, advice)
    if error_out is not None:
        error_out.append(check)
    if report_errors:
        print(render_recovery_error(RecoveryError(advice)))
    return False


# Detects whether this run uses a script or installed command entry point
def _wizard_install_method() -> str:
    return "manual" if os.path.basename(sys.argv[0] or "").endswith(".py") else "pip"


# Returns command arguments using friendly names or exact runtime paths
def _wizard_local_command_args(method: str, exact: bool = False) -> List[str]:
    if exact:
        executable = sys.executable or ("python" if platform.system() == "Windows" else "python3")
        if method == "pip":
            return [executable, "-m", "spotify_profile_monitor"]
        return [executable, str(Path(__file__).resolve())]
    path_class = PureWindowsPath if platform.system() == "Windows" else Path
    executable_name = "python" if platform.system() == "Windows" else "python3"
    return [executable_name, path_class(__file__).name] if method == "manual" else ["spotify_profile_monitor"]


# Renders command arguments for the active host shell
def _wizard_render_command(arguments: Sequence[str]) -> str:
    values = [str(argument) for argument in arguments]
    return subprocess.list2cmdline(values) if platform.system() == "Windows" else shlex.join(values)


# Quotes one command argument for the active host shell
def _wizard_quote_argument(value: Any) -> str:
    return _wizard_render_command([str(value)])


# Returns the command prefix for the detected installation method
def _wizard_cmd_prefix(method: str, exact: bool = False) -> str:
    return _wizard_render_command(_wizard_local_command_args(method, exact=exact))


# Validates one local setup destination without creating or modifying it
def _wizard_validate_destination(path, label: str) -> Path:
    destination = Path(path).expanduser().resolve()
    if destination.exists() and destination.is_dir():
        raise ValueError(f"{label} must be a file path, not a directory")
    parent = nearest_existing_parent(destination)
    if not parent.is_dir():
        raise ValueError(f"{label} does not have a usable parent directory")
    if not os.access(str(parent), os.W_OK):
        raise ValueError(f"{label} is not writable through parent '{parent}'")
    return destination


# Prints one labelled setup or recovery command
def _wizard_print_command(label: str, command: str, suffix: str = "") -> None:
    print(label)
    print(f"    {command}{suffix}\n")


# Builds one action command with portable interpreter and explicit file paths
def _wizard_action_command(method: str, action: str, config_path, env_path, target: Optional[str] = None) -> str:
    parts = list(_wizard_local_command_args(method, exact=True))
    if action:
        parts.extend(shlex.split(action))
    if target:
        parts.append(str(target))
    if config_path is not None:
        selected_config = "none" if str(config_path).casefold() == "none" else str(Path(config_path).expanduser().resolve())
        parts.extend(("--config-file", selected_config))
    if env_path is not None:
        selected_env = "none" if str(env_path).casefold() == "none" else str(Path(env_path).expanduser().resolve())
        parts.extend(("--env-file", selected_env))
    return _wizard_render_command(parts)


# Returns an exact Firefox import command with optional setup context
def _wizard_firefox_import_cmd(method: str, env_path=None, exact: bool = False, config_path=None, target: Optional[str] = None) -> str:
    parts = list(_wizard_local_command_args(method, exact=exact))
    parts.extend(("--import-browser-cookie", "--browser", "firefox"))
    if target:
        parts.append(str(target))
    if config_path is not None:
        parts.extend(("--config-file", str(Path(config_path).expanduser().resolve())))
    if env_path is not None:
        parts.extend(("--env-file", str(Path(env_path).expanduser().resolve())))
    return _wizard_render_command(parts)


# Returns an exact hidden sp_dc entry command with optional setup context
def _wizard_set_sp_dc_cmd(method: str, env_path=None, exact: bool = False, config_path=None) -> str:
    parts = list(_wizard_local_command_args(method, exact=exact))
    parts.append("--set-sp-dc")
    if config_path is not None:
        parts.extend(("--config-file", str(Path(config_path).expanduser().resolve())))
    if env_path is not None:
        parts.extend(("--env-file", str(Path(env_path).expanduser().resolve())))
    return _wizard_render_command(parts)


# Returns an exact hidden webhook destination entry command
def _wizard_set_webhook_url_cmd(method: str, env_path=None, exact: bool = False, config_path=None) -> str:
    parts = list(_wizard_local_command_args(method, exact=exact))
    parts.append("--set-webhook-url")
    if config_path is not None:
        parts.extend(("--config-file", str(Path(config_path).expanduser().resolve())))
    if env_path is not None:
        parts.extend(("--env-file", str(Path(env_path).expanduser().resolve())))
    return _wizard_render_command(parts)


# Prints the exact monitoring command after a successful Doctor run
def _wizard_print_monitor_after_doctor(config_path, env_path, target: Optional[str] = None, target_is_saved: bool = False) -> None:
    command_target = None if target_is_saved else target or "SPOTIFY_TARGET"
    command = _wizard_action_command(_wizard_install_method(), "", config_path, env_path, command_target)
    print("\nNext steps\n")
    _wizard_print_command("After Doctor passes, start monitoring:", command)


# Builds install-aware examples for command help
def _build_help_epilog() -> str:
    method = _wizard_install_method()
    prefix = _wizard_cmd_prefix(method)
    return "\n".join((
        "Examples:",
        "  # Guided setup, recommended for the first run",
        f"  {prefix} --setup",
        "",
        f"  # Open {SPOTIFY_WEB_LOGIN_URL} in Firefox and sign in first",
        "  # Then import and validate Spotify login from Firefox",
        f"  {prefix} --import-browser-cookie --browser firefox",
        "",
        "  # Or enter the Spotify cookie through a hidden validated prompt",
        f"  {prefix} --set-sp-dc",
        "",
        "  # Save a Discord or ntfy destination through a hidden prompt",
        f"  {prefix} --set-webhook-url",
        "",
        "  # Check authentication, connectivity and one target",
        f"  {prefix} --doctor <spotify_target>",
        "",
        "  # Monitor one Spotify user",
        "  # Use a complete profile URL, spotify:user URI or user ID",
        f"  {prefix} <spotify_target>",
        "",
        "  # Advanced Spotify desktop client mode",
        f"  {prefix} <spotify_target> --token-source client --login-request-body-file <protobuf_file>",
        "",
        f"Guide: {QUICK_START_GUIDE_URL}",
    )) + "\n"


# Prints a short no-argument welcome and optionally launches setup
def _wizard_welcome() -> None:
    method = _wizard_install_method()
    prefix = _wizard_cmd_prefix(method)
    interactive = sys.stdin.isatty()
    print("For <spotify_target>, use a complete Spotify profile URL, spotify:user URI or user ID.\n")
    _wizard_print_command("Quickest start (already configured):", f"{prefix} <spotify_target>")
    setup_suffix = "   (or just answer Y below)" if interactive else ""
    _wizard_print_command("Easiest start (guided setup wizard):", f"{prefix} --setup", setup_suffix)
    _wizard_print_command("Check setup before monitoring:", f"{prefix} --doctor <spotify_target>")
    print(f"Full options: {prefix} --help")
    print(f"\nGuide:        {QUICK_START_GUIDE_URL}\n")
    if interactive and _wizard_ask_yes_no("Run the guided setup wizard now?", default=True):
        run_setup_wizard()


# Resolves an executable path by checking if it's a valid file or searching in $PATH
def resolve_executable(path):
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path

    found = shutil.which(path)
    if found:
        return found

    raise FileNotFoundError(f"Could not find executable '{path}'")


# Normalizes a Spotify profile URL, user URI or user ID into one user ID
def normalize_spotify_user_id(value):
    if not isinstance(value, str):
        raise ValueError(TARGET_INPUT_ERROR)

    target = value.strip()
    if not target or any(character.isspace() or ord(character) < 32 or 127 <= ord(character) <= 159 for character in target):
        raise ValueError(TARGET_INPUT_ERROR)

    encoded_user_id = target
    if target.lower().startswith("spotify:"):
        parts = target.split(":")
        if len(parts) != 3 or parts[0].lower() != "spotify" or parts[1].lower() != "user":
            raise ValueError(TARGET_INPUT_ERROR)
        encoded_user_id = parts[2]
    elif "://" in target or target.lower().startswith(("http:", "https:")):
        try:
            parsed = urlsplit(target)
            parsed_port = parsed.port
        except ValueError as exc:
            raise ValueError(TARGET_INPUT_ERROR) from exc
        if parsed.scheme.lower() not in ("http", "https") or parsed.hostname is None or parsed.hostname.lower() != "open.spotify.com":
            raise ValueError(TARGET_INPUT_ERROR)
        if parsed.username is not None or parsed.password is not None or parsed_port is not None or parsed.fragment:
            raise ValueError(TARGET_INPUT_ERROR)
        path_parts = parsed.path.split("/")
        if path_parts and path_parts[-1] == "":
            path_parts = path_parts[:-1]
        if len(path_parts) != 3 or path_parts[0] != "" or path_parts[1].lower() != "user":
            raise ValueError(TARGET_INPUT_ERROR)
        encoded_user_id = path_parts[2]
    elif any(character in target for character in (":", "?", "#")):
        raise ValueError(TARGET_INPUT_ERROR)

    if re.search(r"%(?![0-9A-Fa-f]{2})", encoded_user_id):
        raise ValueError(TARGET_INPUT_ERROR)
    try:
        user_id = unquote(encoded_user_id, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(TARGET_INPUT_ERROR) from exc

    if not user_id or user_id in (".", "..") or any(character in user_id for character in ("/", "\\", "?", "#")):
        raise ValueError(TARGET_INPUT_ERROR)
    if any(character.isspace() or ord(character) < 32 or 127 <= ord(character) <= 159 for character in user_id):
        raise ValueError(TARGET_INPUT_ERROR)
    return user_id


# Resolves CLI and configured targets with CLI precedence then normalizes the selected value
def resolve_target_user_id(cli_value, configured_value):
    if cli_value is not None:
        return normalize_spotify_user_id(cli_value)
    if configured_value is None or configured_value == "":
        return None
    return normalize_spotify_user_id(configured_value)


# Stores one startup setting and its output routing
@dataclass(frozen=True)
class StartupSummaryRow:
    label: str
    value: str
    concise: bool = False
    full: bool = True
    log: bool = True


# Stores one Doctor result before the report is rendered
@dataclass(frozen=True)
class DoctorCheck:
    section: str
    status: str
    label: str
    detail: str = ""
    fix: str = ""
    advice: Optional[RecoveryAdvice] = None


# Collects Doctor checks and reusable authenticated data
@dataclass
class DoctorReport:
    checks: List[DoctorCheck] = field(default_factory=list)
    access_token: Optional[str] = field(default=None, repr=False)
    authentication_error: str = ""
    authentication_advice: Optional[RecoveryAdvice] = None


# Builds the concise and complete non-secret startup summary rows
def build_startup_summary(target: str, config_path, env_path, output_path) -> List[StartupSummaryRow]:
    authentication_names = {"cookie": "Cookie mode", "client": "Client mode, advanced", "oauth_app": "OAuth app mode", "oauth_user": "OAuth user mode"}
    enabled_email = _startup_email_notification_categories()
    enabled_webhook = _startup_webhook_notification_categories()
    notification_state_email = "On (" + ", ".join(enabled_email) + ")" if enabled_email else "Off"
    notification_state_webhook = "On (" + ", ".join(enabled_webhook) + ")" if enabled_webhook else "Off"
    output_state = str(output_path) if output_path else "Terminal only (logging disabled)"
    rows = [
        StartupSummaryRow("Target", str(target), concise=True),
        StartupSummaryRow("Authentication", authentication_names.get(TOKEN_SOURCE, TOKEN_SOURCE), concise=True),
        StartupSummaryRow("Token source", TOKEN_SOURCE),
        StartupSummaryRow("Polling interval", display_time(SPOTIFY_CHECK_INTERVAL), concise=True),
        StartupSummaryRow("Error retry timer", display_time(SPOTIFY_ERROR_INTERVAL)),
        StartupSummaryRow("Notifications (email)", notification_state_email, concise=True),
        StartupSummaryRow("Notifications (webhook)", notification_state_webhook, concise=True),
        StartupSummaryRow("Output", output_state, concise=True, full=False, log=False),
        StartupSummaryRow("Output logging", str(output_path) if output_path else "Disabled"),
        StartupSummaryRow("ASCII log separators", f"{ascii_log_separators_enabled()} (mode: {ASCII_LOG_SEPARATORS})"),
        StartupSummaryRow("Config", str(config_path) if config_path else "None", concise=True),
        StartupSummaryRow("Dotenv", str(env_path) if env_path else "None", concise=True),
        StartupSummaryRow("Playlist backend", spotify_get_playlist_backend_description(), concise=True),
        StartupSummaryRow("Profile picture changes", str(DETECT_CHANGED_PROFILE_PIC)),
        StartupSummaryRow("Playlist changes", str(DETECT_CHANGES_IN_PLAYLISTS)),
        StartupSummaryRow("All public playlists", str(GET_ALL_PLAYLISTS)),
        StartupSummaryRow("Liveness output", display_time(LIVENESS_CHECK_INTERVAL) if LIVENESS_CHECK_INTERVAL else "Disabled", concise=bool(LIVENESS_CHECK_INTERVAL)),
        StartupSummaryRow("CSV output", CSV_FILE or "Disabled", concise=bool(CSV_FILE)),
        StartupSummaryRow("Ignored-playlist file", PLAYLISTS_TO_SKIP_FILE or "Disabled", concise=bool(PLAYLISTS_TO_SKIP_FILE)),
        StartupSummaryRow("Spotify playlists ignored", str(IGNORE_SPOTIFY_PLAYLISTS)),
        StartupSummaryRow("Profile picture display", imgcat_exe or "Disabled", concise=bool(imgcat_exe)),
        StartupSummaryRow("Terminal truncation", f"{TRUNCATE_CHARS} chars" if TRUNCATE_CHARS else "Disabled", concise=bool(TRUNCATE_CHARS)),
        StartupSummaryRow("Local timezone", str(LOCAL_TIMEZONE)),
        StartupSummaryRow("Verbose mode", str(VERBOSE_MODE), concise=bool(VERBOSE_MODE)),
        StartupSummaryRow("Debug mode", str(DEBUG_MODE), concise=bool(DEBUG_MODE)),
        StartupSummaryRow("More details", "use --verbose or --debug", concise=True, full=False, log=False),
    ]
    if TOKEN_SOURCE == "oauth_user":
        rows.append(StartupSummaryRow("Spotify token cache", SP_USER_TOKENS_FILE or "None (memory only)"))
    elif TOKEN_SOURCE == "oauth_app" or spotify_has_oauth_app_credentials():
        rows.append(StartupSummaryRow("Spotify OAuth cache", SP_APP_TOKENS_FILE or "None (memory only)"))
    return rows


# Formats one startup summary row with aligned ASCII columns
def _format_startup_summary_row(row: StartupSummaryRow) -> str:
    prefix = f"* {(row.label + ':'):<30}"
    if row.label in ("Notifications (email)", "Notifications (webhook)"):
        return textwrap.fill(row.value, width=100, initial_indent=prefix, subsequent_indent=" " * len(prefix), break_long_words=False, break_on_hyphens=False) + "\n"
    return f"{prefix}{row.value}\n"


# Routes concise or complete startup rows to the terminal and complete log
def emit_startup_summary(rows: Sequence[StartupSummaryRow], show_full: bool, stream=None) -> None:
    destination: Any = stream or sys.stdout
    routed = hasattr(destination, "terminal_only") and hasattr(destination, "log_only")
    for row in rows:
        line = _format_startup_summary_row(row)
        if routed and row.full and row.log:
            destination.log_only(line)
        show_in_terminal = row.full if show_full else row.concise
        if show_in_terminal:
            if routed:
                destination.terminal_only(line)
            else:
                destination.write(line)
    if routed:
        destination.log_only("\n")
        destination.terminal_only("\n")
    else:
        destination.write("\n")
        destination.flush()


# Creates one secret-safe Doctor result with optional structured recovery guidance
def make_doctor_check(section: str, status: str, label: str, detail: Any = "", fix: Any = "", advice: Optional[RecoveryAdvice] = None) -> DoctorCheck:
    if status not in ("PASS", "WARN", "FAIL"):
        raise ValueError(f"Unsupported Doctor status: {status}")
    selected_fix = advice.fix if advice is not None and not fix else fix
    return DoctorCheck(section, status, sanitize_error_text(label), sanitize_error_text(detail), sanitize_error_text(selected_fix), advice)


# Checks the active Python version plus required and optional dependencies
def doctor_check_environment(version_info=None, spec_finder: Optional[Callable[[str], Any]] = None) -> List[DoctorCheck]:
    checks = []
    selected_version = sys.version_info if version_info is None else version_info
    version_text = ".".join(str(part) for part in tuple(selected_version)[:3])
    if tuple(selected_version)[:2] >= (3, 9):
        checks.append(make_doctor_check("Environment", "PASS", f"Python {version_text} is supported"))
    else:
        checks.append(make_doctor_check("Environment", "FAIL", f"Python {version_text} is unsupported", fix="Install Python 3.9 or newer then retry"))
    find_spec = importlib.util.find_spec if spec_finder is None else spec_finder
    required = (("requests", "requests"), ("dateutil", "python-dateutil"), ("urllib3", "urllib3"), ("dotenv", "python-dotenv"), ("pyotp", "pyotp"), ("pytz", "pytz"), ("tzlocal", "tzlocal"), ("spotipy", "Spotipy"), ("wcwidth", "wcwidth"), ("pathvalidate", "pathvalidate"), ("PIL", "Pillow"))
    for module_name, package_name in required:
        try:
            present = find_spec(module_name) is not None
        except (ImportError, ValueError):
            present = False
        if present:
            checks.append(make_doctor_check("Environment", "PASS", f"Required dependency {package_name} is installed"))
            continue
        install_command = _wizard_render_command([sys.executable or ("python" if platform.system() == "Windows" else "python3"), "-m", "pip", "install", package_name])
        advice = classify_recovery_error(ModuleNotFoundError(package_name), "dependency", f"Missing Python package: {package_name}")
        fix = recovery_fix_with_guide(f"Install it through the active Python environment then retry: {install_command}", INSTALLATION_GUIDE_URL)
        checks.append(make_doctor_check("Environment", "FAIL", f"Required dependency {package_name} is missing", advice.detail, fix, advice))
    optional = (("pycookiecheat", "pycookiecheat"),)
    for module_name, package_name in optional:
        try:
            present = find_spec(module_name) is not None
        except (ImportError, ValueError):
            present = False
        purpose = "Used only for importing cookies from Chromium-based browsers. Firefox cookie import does not need it" if present else "Required only for importing cookies from Chromium-based browsers. Normal monitoring is unaffected. Firefox cookie import is also unaffected"
        checks.append(make_doctor_check("Environment", "PASS" if present else "WARN", f"Optional dependency {package_name} is {'installed' if present else 'not installed'}", purpose))
    return checks


# Returns the nearest existing parent without creating directories
def nearest_existing_parent(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.exists():
        return candidate if candidate.is_dir() else candidate.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


# Builds the exact log path used for one effective target or custom suffix
def build_log_path(base_path, suffix: str) -> Path:
    log_path = Path(os.path.expanduser(str(base_path)))
    if log_path.suffix == "" and suffix:
        log_path = log_path.parent / f"{log_path.name}_{suffix}.log"
    return log_path


# Validates effective settings and file destinations without writing them
def doctor_check_configuration(config_path=None, env_path=None, startup_checks: Sequence[DoctorCheck] = (), target_value=None) -> List[DoctorCheck]:
    checks = list(startup_checks)
    if not any(check.section == "Configuration" and "configuration file" in check.label.lower() for check in checks):
        checks.append(make_doctor_check("Configuration", "PASS", "Configuration file loaded", f"Path: {config_path}") if config_path else make_doctor_check("Configuration", "PASS", "No configuration file selected", "Using built-in defaults and command-line overrides"))
    if not any(check.section == "Configuration" and "dotenv" in check.label.lower() for check in checks):
        checks.append(make_doctor_check("Configuration", "PASS", "Dotenv file loaded", f"Path: {env_path}") if env_path else make_doctor_check("Configuration", "PASS", "No dotenv file selected", "Using environment variables and other configured sources"))
    if TOKEN_SOURCE not in ("cookie", "client", "oauth_app", "oauth_user"):
        advice = classify_recovery_error(context="config_invalid", detail=f"TOKEN_SOURCE must be cookie, client, oauth_app or oauth_user, not {TOKEN_SOURCE!r}")
        checks.append(make_doctor_check("Configuration", "FAIL", "TOKEN_SOURCE is invalid", advice.detail, advice.fix, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", f"TOKEN_SOURCE is {TOKEN_SOURCE}"))
    if TOKEN_SOURCE == "cookie":
        totp_bytes_valid = bool(TOTP_SECRET_CIPHER_BYTES) and all(isinstance(value, int) and not isinstance(value, bool) for value in TOTP_SECRET_CIPHER_BYTES)
        totp_version_valid = isinstance(TOTP_VERSION, int) and not isinstance(TOTP_VERSION, bool) and TOTP_VERSION > 0
        if totp_bytes_valid and totp_version_valid:
            checks.append(make_doctor_check("Configuration", "PASS", f"Web-player TOTP parameters are valid (v{TOTP_VERSION})"))
        else:
            advice = classify_recovery_error(context="config_invalid", detail="TOTP_VERSION must be a positive integer and TOTP_SECRET_CIPHER_BYTES must be a non-empty integer sequence")
            checks.append(make_doctor_check("Configuration", "FAIL", "Web-player TOTP parameters are invalid", advice.detail, advice.fix, advice))
    numeric_values = (("SPOTIFY_CHECK_INTERVAL", SPOTIFY_CHECK_INTERVAL, 1, None), ("SPOTIFY_ERROR_INTERVAL", SPOTIFY_ERROR_INTERVAL, 0, None), ("LIVENESS_CHECK_INTERVAL", LIVENESS_CHECK_INTERVAL, 0, None), ("PLAYLISTS_LIMIT", PLAYLISTS_LIMIT, 1, None), ("RECENTLY_PLAYED_ARTISTS_LIMIT", RECENTLY_PLAYED_ARTISTS_LIMIT, 0, None), ("RECENTLY_PLAYED_ARTISTS_LIMIT_INFO", RECENTLY_PLAYED_ARTISTS_LIMIT_INFO, 0, None), ("PLAYLISTS_DISAPPEARED_COUNTER", PLAYLISTS_DISAPPEARED_COUNTER, 1, None), ("FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER", FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER, 1, None), ("COLLABORATORS_CHANGE_COUNTER", COLLABORATORS_CHANGE_COUNTER, 0, None), ("PLAYLISTS_CHANGE_COUNTER", PLAYLISTS_CHANGE_COUNTER, 0, None), ("TRUNCATE_CHARS", TRUNCATE_CHARS, 0, None), ("SMTP_PORT", SMTP_PORT, 1, 65535))
    invalid_numeric = [f"{name}={value!r}" for name, value, minimum, maximum in numeric_values if not isinstance(value, (int, float)) or isinstance(value, bool) or value < minimum or maximum is not None and value > maximum]
    if invalid_numeric:
        advice = classify_recovery_error(context="config_invalid", detail="Invalid numeric settings: " + ", ".join(invalid_numeric))
        checks.append(make_doctor_check("Configuration", "FAIL", "One or more numeric settings are invalid", advice.detail, advice.fix, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "Numeric intervals, counters and ports are valid"))
    if LOCAL_TIMEZONE == "Auto":
        try:
            detected_timezone = str(get_localzone()) if get_localzone is not None else ""
        except Exception as exc:
            detected_timezone = ""
            timezone_error = exc
        else:
            timezone_error = None
        if detected_timezone and is_valid_timezone(detected_timezone):
            checks.append(make_doctor_check("Configuration", "PASS", f"LOCAL_TIMEZONE Auto resolves to {detected_timezone}"))
        else:
            detail = f"LOCAL_TIMEZONE Auto could not be resolved{f': {timezone_error}' if timezone_error else ''}"
            if get_localzone is None:
                advice = classify_recovery_error(ModuleNotFoundError("tzlocal"), "dependency", detail)
            else:
                advice = make_recovery_advice("config.invalid", "The local timezone could not be detected", recovery_fix_with_guide("Set LOCAL_TIMEZONE to a valid timezone such as Europe/Warsaw then retry", CONFIG_GUIDE_URL), False, detail)
            checks.append(make_doctor_check("Configuration", "FAIL", "LOCAL_TIMEZONE Auto could not be resolved", advice.detail, advice.fix, advice))
    elif is_valid_timezone(LOCAL_TIMEZONE):
        checks.append(make_doctor_check("Configuration", "PASS", f"LOCAL_TIMEZONE is {LOCAL_TIMEZONE}"))
    else:
        advice = classify_recovery_error(context="config_invalid", detail=f"LOCAL_TIMEZONE is invalid: {LOCAL_TIMEZONE!r}")
        checks.append(make_doctor_check("Configuration", "FAIL", "LOCAL_TIMEZONE is invalid", advice.detail, advice.fix, advice))
    try:
        ascii_log_separators_enabled()
    except ValueError as exc:
        advice = classify_recovery_error(exc, "config_invalid", str(exc))
        checks.append(make_doctor_check("Configuration", "FAIL", "ASCII_LOG_SEPARATORS is invalid", advice.detail, advice.fix, advice))
    if PLAYLISTS_TO_SKIP_FILE:
        skip_path = Path(PLAYLISTS_TO_SKIP_FILE).expanduser()
        readable = skip_path.is_file() and os.access(str(skip_path), os.R_OK)
        advice = None if readable else classify_recovery_error(context="file_read", detail=f"Ignored-playlist file is unreadable: {skip_path}")
        checks.append(make_doctor_check("Configuration", "PASS" if readable else "FAIL", "Ignored-playlist file is readable" if readable else "Ignored-playlist file is unreadable", f"Path: {skip_path}", advice.fix if advice else "", advice))
    destinations = []
    if CSV_FILE:
        destinations.append(("CSV destination", Path(CSV_FILE)))
    if not DISABLE_LOGGING and SP_LOGFILE:
        log_suffix = FILE_SUFFIX
        if not log_suffix and target_value:
            try:
                log_suffix = resolve_target_user_id(target_value, None) or ""
            except ValueError:
                log_suffix = ""
        if log_suffix:
            destinations.append(("Log destination", build_log_path(SP_LOGFILE, log_suffix)))
        else:
            checks.append(make_doctor_check("Configuration", "PASS", "Log destination will be finalized after a target is selected", f"Base path: {Path(os.path.expanduser(SP_LOGFILE))}"))
    for label, destination in destinations:
        expanded_destination = destination.expanduser()
        if expanded_destination.exists():
            writable = expanded_destination.is_file() and os.access(str(expanded_destination), os.W_OK)
        else:
            parent = nearest_existing_parent(expanded_destination)
            writable = parent.is_dir() and os.access(str(parent), os.W_OK)
        advice = None if writable else classify_recovery_error(context="file_write", detail=f"{label} is not writable: {destination.expanduser()}")
        checks.append(make_doctor_check("Configuration", "PASS" if writable else "FAIL", f"{label} {'appears writable' if writable else 'is not writable'}", f"Path: {destination.expanduser()}", advice.fix if advice else "", advice))
    return checks


# Acquires one Spotify token through the configured authentication mode
def doctor_acquire_access_token() -> str:
    if TOKEN_SOURCE == "cookie":
        if not SP_DC_COOKIE or SP_DC_COOKIE == "your_sp_dc_cookie_value":
            raise RuntimeError("SP_DC_COOKIE is missing or still a placeholder")
        token = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
        if not isinstance(token, str) or not token:
            raise RuntimeError("Spotify cookie authentication did not return an access token")
        return token
    if TOKEN_SOURCE == "client":
        values = {"DEVICE_ID": DEVICE_ID, "SYSTEM_ID": SYSTEM_ID, "USER_URI_ID": USER_URI_ID, "REFRESH_TOKEN": REFRESH_TOKEN}
        if LOGIN_REQUEST_BODY_FILE:
            values.update(dict(zip(("DEVICE_ID", "SYSTEM_ID", "USER_URI_ID", "REFRESH_TOKEN"), parse_login_request_body_file(Path(LOGIN_REQUEST_BODY_FILE).expanduser()))))
        placeholders = {"DEVICE_ID": "your_spotify_app_device_id", "SYSTEM_ID": "your_spotify_app_system_id", "USER_URI_ID": "your_spotify_user_uri_id", "REFRESH_TOKEN": "your_spotify_app_refresh_token"}
        missing = [name for name, value in values.items() if not value or value == placeholders[name]]
        if missing:
            raise RuntimeError("Client mode is missing required values: " + ", ".join(missing))
        return spotify_get_access_token_from_client_auto(values["DEVICE_ID"], values["SYSTEM_ID"], values["USER_URI_ID"], values["REFRESH_TOKEN"])
    if TOKEN_SOURCE == "oauth_app":
        if not spotify_has_oauth_app_credentials():
            raise RuntimeError("SP_APP_CLIENT_ID or SP_APP_CLIENT_SECRET is missing or still a placeholder")
        token = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
    else:
        if not SP_USER_CLIENT_ID or SP_USER_CLIENT_ID == "your_spotify_user_client_id":
            raise RuntimeError("SP_USER_CLIENT_ID is missing or still a placeholder")
        token = spotify_get_access_token_from_oauth_user(SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, SP_USER_REDIRECT_URI, SP_USER_SCOPE, init=False)
    if not token:
        raise RuntimeError("Spotify authentication did not return an access token")
    return token


# Validates configured Spotify credentials and stores a reusable access token
def doctor_check_authentication(report: DoctorReport) -> List[DoctorCheck]:
    global SP_APP_TOKENS_FILE
    saved_oauth_cache = SP_APP_TOKENS_FILE
    try:
        if TOKEN_SOURCE == "oauth_app":
            SP_APP_TOKENS_FILE = ""
        report.access_token = doctor_acquire_access_token()
        return [make_doctor_check("Authentication", "PASS", f"Spotify {TOKEN_SOURCE} authentication succeeded", "A live Spotify token request succeeded")]
    except Exception as exc:
        report.authentication_error = sanitize_error_text(exc)
        context = {"cookie": "cookie_auth", "client": "client_auth", "oauth_app": "oauth_app_auth", "oauth_user": "oauth_user_auth"}.get(TOKEN_SOURCE, "runtime")
        report.authentication_advice = classify_recovery_error(exc, context, report.authentication_error)
        return [make_doctor_check("Authentication", "FAIL", report.authentication_advice.summary, report.authentication_advice.detail, report.authentication_advice.fix, report.authentication_advice)]
    finally:
        SP_APP_TOKENS_FILE = saved_oauth_cache


# Reports connectivity using the authenticated request when available
def doctor_check_connectivity(report: DoctorReport) -> List[DoctorCheck]:
    if report.access_token:
        return [make_doctor_check("Connectivity", "PASS", "Spotify is reachable", "Confirmed through the authentication request")]
    if report.authentication_error and _looks_like_network_failure(report.authentication_error):
        advice = classify_recovery_error(req.ConnectionError(report.authentication_error), "runtime", report.authentication_error)
        return [make_doctor_check("Connectivity", "FAIL", advice.summary, advice.detail, advice.fix, advice)]
    return [make_doctor_check("Connectivity", "WARN", "Spotify connectivity check was skipped", "Authentication did not produce a reusable access token", "Fix authentication then run --doctor again")]


# Validates an optional target through one live profile request
def doctor_check_target(report: DoctorReport, target_value=None) -> List[DoctorCheck]:
    if target_value is None or target_value == "":
        return [make_doctor_check("Target", "WARN", "No Spotify target was provided", "Authentication-only preflight completed", "Pass a user ID, spotify:user URI or profile URL to check one target")]
    try:
        target_id = resolve_target_user_id(target_value, None)
    except ValueError as exc:
        advice = classify_recovery_error(exc, "target_invalid")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice.fix, advice)]
    if not report.access_token:
        return [make_doctor_check("Target", "WARN", f"Target '{target_id}' live check was skipped", "Authentication did not produce an access token", "Fix authentication then rerun Doctor")]
    try:
        spotify_get_user_info(report.access_token, target_id, False, 0)
        return [make_doctor_check("Target", "PASS", f"Target '{target_id}' can be monitored", "A live Spotify profile request succeeded")]
    except Exception as exc:
        advice = classify_recovery_error(exc, "target", target_user_id=target_id)
        return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice.fix, advice)]


# Checks optional legacy OAuth metadata credentials without writing a token cache
def doctor_check_optional_oauth() -> List[DoctorCheck]:
    client_present = bool(SP_APP_CLIENT_ID and SP_APP_CLIENT_ID != "your_spotify_app_client_id")
    secret_present = bool(SP_APP_CLIENT_SECRET and SP_APP_CLIENT_SECRET != "your_spotify_app_client_secret")
    if not client_present and not secret_present:
        return [make_doctor_check("Metadata", "PASS", "Legacy OAuth metadata credentials are not configured", "The web-player playlist backend remains available")]
    if client_present != secret_present:
        advice = classify_recovery_error(context="config_invalid", detail="SP_APP_CLIENT_ID and SP_APP_CLIENT_SECRET must both be set or both be removed")
        return [make_doctor_check("Metadata", "WARN", "Legacy OAuth metadata credentials are incomplete", "The web-player playlist backend remains available", recovery_fix_with_guide("Set both values or remove both", OAUTH_GUIDE_URL), advice)]
    global SP_APP_TOKENS_FILE
    saved_cache = SP_APP_TOKENS_FILE
    try:
        SP_APP_TOKENS_FILE = ""
        token = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
        if not token:
            raise RuntimeError("Spotify did not provide an OAuth app token")
        return [make_doctor_check("Metadata", "PASS", "Legacy OAuth metadata authentication succeeded", "A memory-only token was used and no OAuth cache was written")]
    except Exception as exc:
        advice = classify_recovery_error(exc, "metadata")
        return [make_doctor_check("Metadata", "WARN", "Legacy OAuth metadata access is unavailable", advice.detail, advice.fix, advice)]
    finally:
        SP_APP_TOKENS_FILE = saved_cache


# Returns one validation error for configured SMTP settings
def validate_smtp_configuration() -> Optional[str]:
    if not SMTP_HOST or str(SMTP_HOST).startswith("your_smtp_server_"):
        return "SMTP_HOST is missing or still a placeholder"
    try:
        port = int(SMTP_PORT)
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        return "SMTP_PORT must be between 1 and 65535"
    if not SMTP_USER or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or SMTP_PASSWORD == "your_smtp_password":
        return "SMTP_USER or SMTP_PASSWORD is missing or still a placeholder"
    if "@" not in str(SENDER_EMAIL) or "@" not in str(RECEIVER_EMAIL):
        return "SENDER_EMAIL or RECEIVER_EMAIL is invalid"
    return None


# Opens and authenticates one SMTP connection without sending a message
def smtp_connect_and_login(use_ssl, smtp_timeout=5):
    smtp_object = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
    if use_ssl:
        smtp_object.starttls(context=ssl.create_default_context())
    smtp_object.login(SMTP_USER, SMTP_PASSWORD)
    return smtp_object


# Validates notification settings without sending a message
def doctor_check_notifications() -> List[DoctorCheck]:
    checks = []
    email_enabled = bool(_startup_email_notification_categories()) and bool(SMTP_HOST) and not str(SMTP_HOST).startswith("your_smtp_server_")
    if not email_enabled:
        checks.append(make_doctor_check("Notifications", "PASS", "Email notifications are disabled", "No SMTP connection was attempted and no email was sent"))
    else:
        validation_error = validate_smtp_configuration()
        if validation_error:
            advice = classify_recovery_error(context="smtp_config", detail=validation_error)
            checks.append(make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice.fix, advice))
        else:
            smtp_object = None
            try:
                smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=5)
                checks.append(make_doctor_check("Notifications", "PASS", "SMTP connection and login succeeded", "No email was sent during this passive check"))
            except Exception as exc:
                advice = classify_recovery_error(exc, "smtp_connection")
                checks.append(make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice.fix, advice))
            finally:
                if smtp_object is not None:
                    try:
                        smtp_object.quit()
                    except Exception:
                        pass
    if not WEBHOOK_ENABLED:
        checks.append(make_doctor_check("Notifications", "PASS", "Webhook alerts are disabled", "No webhook was sent"))
    elif not normalized_webhook_provider():
        advice = classify_recovery_error(context="webhook_config", detail=f"WEBHOOK_PROVIDER must be discord or ntfy, not {WEBHOOK_PROVIDER!r}")
        checks.append(make_doctor_check("Notifications", "FAIL", "Webhook provider is invalid", advice.detail, advice.fix, advice))
    elif not validate_webhook_url():
        advice = classify_recovery_error(context="webhook_config", detail="WEBHOOK_URL must contain a complete HTTPS destination")
        checks.append(make_doctor_check("Notifications", "FAIL", "Webhook URL is invalid", "The private link was not displayed", advice.fix, advice))
    else:
        customization_error = validate_webhook_customization(normalized_webhook_provider()) or validate_webhook_headers(normalized_webhook_provider())
        if customization_error:
            advice = classify_recovery_error(context="webhook_config", detail=customization_error)
            checks.append(make_doctor_check("Notifications", "FAIL", "Webhook customization is invalid", advice.detail, advice.fix, advice))
        elif not _startup_webhook_notification_categories():
            checks.append(make_doctor_check("Notifications", "WARN", "Webhook alerts are on but no alert types are selected", "No webhook was sent", "Enable at least one webhook alert or turn WEBHOOK_ENABLED off"))
        else:
            checks.append(make_doctor_check("Notifications", "PASS", "Webhook URL and alert choices look valid", "The private link was not displayed. No webhook was sent"))
    return checks


# Prompts for explicit Doctor delivery consent and defaults to no
def _doctor_ask_yes_no(question: str) -> bool:
    while True:
        try:
            value = input(f"{question} [y/N]: ").strip().casefold()
        except (EOFError, KeyboardInterrupt):
            print("\nDelivery test skipped.")
            return False
        if not value or value in ("n", "no"):
            return False
        if value in ("y", "yes"):
            return True
        print("  Please answer 'y' or 'n'.")


# Offers separate delivery tests only after explicit interactive approval
def _doctor_offer_notification_tests(report: DoctorReport) -> List[DoctorCheck]:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return []
    email_ready = any(check.status == "PASS" and check.label == "SMTP connection and login succeeded" for check in report.checks)
    webhook_ready = any(check.status == "PASS" and check.label == "Webhook URL and alert choices look valid" for check in report.checks)
    if not email_ready and not webhook_ready:
        return []
    print("\nOptional delivery tests\n")
    print("Doctor will not write files. Each approved test sends one real message.\n")
    results = []
    if email_ready:
        if _doctor_ask_yes_no("Send one test email now? This will deliver a real message"):
            result = send_email("spotify_profile_monitor: doctor test email", "This test email was sent after approval in --doctor. Your SMTP delivery settings work.", "", SMTP_SSL, smtp_timeout=5)
            check = make_doctor_check("Notifications", "PASS" if result == 0 else "FAIL", "Doctor test email delivered" if result == 0 else "Doctor test email delivery failed")
            results.append(check)
            print(f"[{check.status}] {check.label}")
        else:
            print("[SKIP] Test email was not sent")
    if webhook_ready:
        provider = normalized_webhook_provider()
        if _doctor_ask_yes_no(f"Send one test webhook through {provider} now? This will publish a real notification"):
            result = send_webhook("Spotify Profile Monitor doctor test", "This test notification was sent after approval in --doctor. Your webhook delivery settings work.", "profile", force=True)
            check = make_doctor_check("Notifications", "PASS" if result == 0 else "FAIL", "Doctor test webhook delivered" if result == 0 else "Doctor test webhook delivery failed")
            results.append(check)
            print(f"[{check.status}] {check.label}")
        else:
            print("[SKIP] Test webhook was not sent")
    return results


# Prints one transient Doctor progress update in interactive terminals
def _doctor_progress(label: str) -> None:
    if sys.stdout.isatty():
        message = f"* Checking {label} ..."
        width = max(len(message), int(getattr(_doctor_progress, "last_width", 0)))
        setattr(_doctor_progress, "last_width", width)
        print("\r" + message.ljust(width), end="", flush=True)


# Clears the transient Doctor progress line before permanent output
def _doctor_progress_clear() -> None:
    if sys.stdout.isatty():
        width = int(getattr(_doctor_progress, "last_width", 0))
        if width:
            print("\r" + (" " * width) + "\r", end="", flush=True)
    setattr(_doctor_progress, "last_width", 0)


# Builds all independent and dependent Doctor checks with optional progress updates
def build_doctor_report(target_value=None, config_path=None, env_path=None, startup_checks: Sequence[DoctorCheck] = (), version_info=None, spec_finder: Optional[Callable[[str], Any]] = None, progress: Optional[Callable[[str], None]] = None) -> DoctorReport:
    report = DoctorReport()
    if progress is not None:
        progress("environment")
    report.checks.extend(doctor_check_environment(version_info, spec_finder))
    if progress is not None:
        progress("configuration")
    report.checks.extend(doctor_check_configuration(config_path, env_path, startup_checks, target_value))
    if progress is not None:
        progress("Spotify authentication")
    report.checks.extend(doctor_check_authentication(report))
    if progress is not None:
        progress("metadata")
    report.checks.extend(doctor_check_optional_oauth())
    if progress is not None:
        progress("connectivity and target")
    report.checks.extend(doctor_check_connectivity(report))
    report.checks.extend(doctor_check_target(report, target_value))
    if progress is not None:
        progress("notifications")
    report.checks.extend(doctor_check_notifications())
    return report


# Renders one sectioned ASCII Doctor report with recovery actions
def render_doctor_report(report: DoctorReport) -> str:
    lines = ["Doctor", "", "No files will be written. In an interactive terminal, real email and webhook tests are offered separately and run only after approval."]
    for section in ("Environment", "Configuration", "Authentication", "Metadata", "Connectivity", "Target", "Notifications"):
        section_checks = [item for item in report.checks if item.section == section]
        if not section_checks:
            continue
        lines.extend(("", section))
        for check in section_checks:
            lines.append(f"[{check.status}] {check.label}")
            if check.detail and (check.advice is None or DEBUG_MODE):
                lines.append(f"  {check.detail}")
            if check.fix and check.status in ("FAIL", "WARN"):
                lines.append(f"To fix: {check.fix}")
    failures = sum(check.status == "FAIL" for check in report.checks)
    warnings = sum(check.status == "WARN" for check in report.checks)
    lines.extend(("", "Summary", f"{failures} failure(s), {warnings} warning(s)", "", f"Guide: {DOCTOR_GUIDE_URL}"))
    return sanitize_error_text("\n".join(lines))


# Runs Doctor preflight plus approved delivery tests
def run_doctor(target_value=None, config_path=None, env_path=None, startup_checks: Sequence[DoctorCheck] = ()) -> int:
    try:
        report = build_doctor_report(target_value, config_path, env_path, startup_checks, progress=_doctor_progress)
    finally:
        _doctor_progress_clear()
    print(render_doctor_report(report))
    delivery_checks = _doctor_offer_notification_tests(report)
    return 1 if any(check.status == "FAIL" for check in (*report.checks, *delivery_checks)) else 0


# Reads one setup line and exits cleanly when input is cancelled
def _wizard_input(prompt_text: str) -> str:
    try:
        return input(prompt_text)
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        raise SystemExit(1) from None


# Prompts for text while applying an Enter default
def _wizard_ask_text(question: str, default: str = "", required: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = _wizard_input(f"{question}{suffix}: ").strip()
        if not value:
            value = default
        if value or not required:
            return value
        print("  This value is required.")


# Prompts until the user provides yes or no
def _wizard_ask_yes_no(question: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        value = _wizard_input(f"{question} {hint}: ").strip().casefold()
        if not value:
            return default
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Displays numbered choices and returns a zero-based index
def _wizard_ask_choice(question: str, options, default_index: int = 0) -> int:
    print(f"\n{question}")
    for index, option in enumerate(options, start=1):
        label, description = option
        marker = " (default)" if index - 1 == default_index else ""
        print(f"  {index}. {label}{marker}")
        if description:
            for line in description.splitlines():
                print(f"     {line}")
    while True:
        value = _wizard_input(f"Choose [1-{len(options)}]: ").strip()
        if not value:
            return default_index
        if value.isdigit() and 1 <= int(value) <= len(options):
            return int(value) - 1
        print(f"  Enter a number between 1 and {len(options)}.")


# Prompts until the user provides a positive integer
def _wizard_ask_positive_int(question: str, default: int) -> int:
    while True:
        value = _wizard_ask_text(question, default=str(default), required=True)
        try:
            parsed = int(value)
        except ValueError:
            parsed = 0
        if parsed > 0:
            return parsed
        print("  Enter a positive whole number.")


# Converts seconds into a compact setup duration label
def _wizard_format_duration(seconds: int) -> str:
    remaining = seconds
    parts = []
    for suffix, count in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        value, remaining = divmod(remaining, count)
        if value:
            parts.append(f"{value}{suffix}")
    raw = f"{seconds}s"
    readable = " ".join(parts) or raw
    return raw if readable == raw else f"{raw} - {readable}"


# Parses one positive setup duration from whole or compound time units
def _wizard_parse_duration(value: str) -> Optional[int]:
    normalized = value.strip().casefold()
    matches = list(re.finditer(r"(\d+(?:\.\d+)?)\s*([a-z]*)", normalized))
    if not matches:
        return None
    unit_seconds = {"": 1, "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1, "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60, "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600, "d": 86400, "day": 86400, "days": 86400}
    cursor = 0
    total = 0.0
    for match in matches:
        if normalized[cursor:match.start()].strip():
            return None
        multiplier = unit_seconds.get(match.group(2))
        if multiplier is None or len(matches) > 1 and not match.group(2):
            return None
        total += float(match.group(1)) * multiplier
        cursor = match.end()
    if normalized[cursor:].strip() or total < 1 or not total.is_integer():
        return None
    return int(total)


# Prompts until the user enters a valid positive duration
def _wizard_ask_duration(question: str, default: int) -> int:
    prompt_text = f"{question} [{_wizard_format_duration(default)}]: "
    while True:
        value = _wizard_input(prompt_text).strip()
        if not value:
            return default
        parsed = _wizard_parse_duration(value)
        if parsed is not None:
            return parsed
        print("  Enter a positive duration such as 120, 2m, 1.5h, 1h 30m or 1d.")


# Reads a required secret through getpass without echoing it
def _wizard_ask_secret(question: str) -> str:
    while True:
        try:
            value = getpass.getpass(f"{question}: ")
        except (EOFError, KeyboardInterrupt):
            print("\nSetup cancelled.")
            raise SystemExit(1) from None
        if value:
            return value
        print("  This secret is required and cannot be empty.")


# Lists browser choices supported by setup on the active platform
def _wizard_import_browsers() -> List[str]:
    return ["firefox"] if platform.system() == "Windows" else list(IMPORT_BROWSERS)


# Describes one browser import choice without exposing browser data
def _wizard_browser_description(browser: str) -> str:
    if browser == "firefox":
        return "Built-in reader for macOS, Linux and Windows with no extra package."
    return f"Import from the signed-in {browser_label(browser)} profile."


# Returns whether Chromium browser import support is installed
def _wizard_chromium_dependency_available() -> bool:
    try:
        return importlib.util.find_spec("pycookiecheat") is not None
    except (AttributeError, ImportError, ValueError):
        return False


# Installs optional Chromium browser import support after user approval
def _wizard_install_chromium_dependency(method: str) -> bool:
    requirement = "spotify_profile_monitor[browser]" if method == "pip" else "pycookiecheat>=0.8"
    executable = sys.executable or ("python" if platform.system() == "Windows" else "python3")
    command = [executable, "-m", "pip", "install", requirement]
    print(f"Installing Chromium browser support with:\n    {_wizard_render_command(command)}\n")
    try:
        result = subprocess.run(command, check=False)
    except OSError as exc:
        print(f"  Installation could not start: {sanitize_error_text(exc)}")
        return False
    importlib.invalidate_caches()
    if result.returncode == 0 and _wizard_chromium_dependency_available():
        print("\nChromium browser support was installed successfully.")
        return True
    print("\nChromium browser support could not be installed. Choose Firefox or another authentication method.")
    return False


# Explains the setup prompt defaults shared with Spotify Monitor
def _wizard_print_default_guidance() -> None:
    print("\nPress Enter to accept the shown default. Ctrl+C cancels.\n")


# Resolves setup destinations without parent directory discovery
def _wizard_destinations(config_file=None, env_file=None):
    if config_file is not None and str(config_file).casefold() == "none":
        raise ValueError("--setup requires a config destination. Replace '--config-file none' with a writable path.")
    if env_file is not None and str(env_file).casefold() == "none":
        raise ValueError("--setup requires a dotenv destination. Replace '--env-file none' with a writable path.")
    config_path = Path(config_file).expanduser() if config_file is not None else Path.cwd() / DEFAULT_CONFIG_FILENAME
    env_path = Path(env_file).expanduser() if env_file is not None else Path.cwd() / DEFAULT_DOTENV_FILENAME
    return _wizard_validate_destination(config_path, "Configuration destination"), _wizard_validate_destination(env_path, "Dotenv destination")


# Confirms replacement or selects another config destination before collecting secrets
def _wizard_choose_config_destination(config_path: Path) -> Path:
    selected = config_path
    while selected.exists() and not _wizard_ask_yes_no(f"Configuration file '{selected}' exists. Replace it with a fresh configuration built from defaults and create a timestamped backup?", default=False):
        alternative = _wizard_ask_text("Another config destination or leave empty to cancel")
        if not alternative:
            print("Setup cancelled. Destination files were not changed.")
            raise SystemExit(1)
        try:
            selected = _wizard_validate_destination(alternative, "Configuration destination")
        except ValueError as exc:
            print(f"  {exc}.")
    return selected


# Returns whether a non-placeholder secret exists in dotenv or the environment
def _wizard_existing_secret(key: str, env_path: Path, placeholders: Sequence[str] = ()) -> bool:
    value = None
    if env_path.is_file():
        try:
            from dotenv import dotenv_values
            value = dotenv_values(str(env_path), interpolate=False).get(key)
        except Exception:
            value = None
    if value is None:
        value = os.environ.get(key)
    return isinstance(value, str) and bool(value.strip()) and value not in placeholders


# Queues one secret after confirming replacement of an existing assignment
def _wizard_queue_secret(updates: dict, env_path: Path, key: str, value: str) -> bool:
    error_type = SpDcConfigurationError if key == "SP_DC_COOKIE" else WebhookConfigurationError
    try:
        existing_assignment = _dotenv_contains_key(env_path, key, error_type)
    except Exception as exc:
        print(f"  {sanitize_error_text(exc)}")
        raise SystemExit(1) from None
    if existing_assignment and not _wizard_ask_yes_no(f"The dotenv file already contains {key}. Replace that value?", default=False):
        print(f"  Existing {key} will be retained without being displayed or rewritten.")
        return False
    updates[key] = value
    return True


# Prompts for one valid Spotify target
def _wizard_target(initial_target: Optional[str] = None) -> str:
    default = initial_target or ""
    while True:
        raw_target = _wizard_ask_text("Spotify profile URL, spotify:user URI or user ID to monitor", default=default, required=True)
        try:
            return normalize_spotify_user_id(raw_target)
        except ValueError:
            print(f"  Use {SPOTIFY_WEB_BASE_URL}/user/USER_ID, spotify:user:USER_ID or a Spotify user ID.")
            default = ""


# Collects cookie authentication with browser dependency and validation guidance
def _wizard_collect_cookie_auth(method: str, env_path: Path, secret_updates: dict) -> dict:
    existing_cookie = _wizard_existing_secret("SP_DC_COOKIE", env_path, ("your_sp_dc_cookie_value",))
    options = [("Import from Firefox, recommended", "Uses Firefox directly with no additional package.")]
    actions = ["firefox"]
    chromium_browsers = [browser for browser in _wizard_import_browsers() if browser in CHROMIUM_IMPORT_BROWSERS]
    if chromium_browsers:
        chromium_description = "Import from a signed-in Chrome, Brave or Chromium profile." if _wizard_chromium_dependency_available() else "Setup can install the required pycookiecheat package now."
        options.append(("Import from Chrome, Brave or Chromium", chromium_description))
        actions.append("chromium")
    options.extend((("Use an existing SP_DC_COOKIE", "Retains a non-placeholder value without displaying or rewriting it."), ("Paste an existing sp_dc value privately", "Reads it through getpass and saves it in the selected dotenv file."), ("Finish without credentials", "Saves an incomplete setup and lets you authenticate later.")))
    actions.extend(("existing", "manual", "finish"))
    while True:
        action = actions[_wizard_ask_choice("How should cookie authentication be configured?", options)]
        if action in ("firefox", "chromium"):
            browser = "firefox"
            if action == "chromium":
                if not _wizard_chromium_dependency_available():
                    print()
                    if not _wizard_ask_yes_no("Chromium browser import requires pycookiecheat. Install it now?", default=True):
                        print("  Chromium import was not selected. Choose Firefox or another authentication method.")
                        continue
                    if not _wizard_install_chromium_dependency(method):
                        continue
                browser_index = _wizard_ask_choice("Which Chromium browser should be imported?", [(browser_label(item), _wizard_browser_description(item)) for item in chromium_browsers])
                browser = chromium_browsers[browser_index]
            print(f"\n  Before import, open {SPOTIFY_WEB_LOGIN_URL} in {browser_label(browser)} and sign in to the Spotify account used for monitoring.")
            return {"complete": False, "validated": False, "browser": browser, "source": f"browser import ({browser_label(browser)})"}
        if action == "existing":
            if not existing_cookie:
                print("  No non-placeholder SP_DC_COOKIE was found.")
                continue
            if _wizard_ask_yes_no("Retain the existing SP_DC_COOKIE without displaying or rewriting it?", default=True):
                return {"complete": True, "validated": False, "browser": None, "source": "existing SP_DC_COOKIE"}
            continue
        if action == "manual":
            print(f"\nFind the sp_dc cookie first: {MANUAL_COOKIE_GUIDE_URL}\n")
            cookie = _wizard_ask_secret("Existing sp_dc value")
            print("  Validating the entered Spotify cookie before saving it ...")
            try:
                validate_sp_dc_cookie(cookie)
            except Exception as exc:
                print(render_recovery_error(exc, "set_sp_dc"))
                if _wizard_ask_yes_no("Try another authentication method?", default=True):
                    continue
                return {"complete": False, "validated": False, "browser": None, "source": "not configured"}
            replaced = _wizard_queue_secret(secret_updates, env_path, "SP_DC_COOKIE", cookie)
            complete = replaced or _wizard_existing_secret("SP_DC_COOKIE", env_path, ("your_sp_dc_cookie_value",))
            return {"complete": complete, "validated": replaced, "browser": None, "source": "private manual entry" if replaced else "existing SP_DC_COOKIE"}
        return {"complete": False, "validated": False, "browser": None, "source": "not configured"}


# Collects advanced client-mode Protobuf values through read-only parsers
def _wizard_collect_client_auth(config_values: dict, env_path: Path, secret_updates: dict) -> dict:
    print("Client mode is advanced.\n")
    result = {"complete": False, "validated": False, "browser": None, "source": "advanced client mode without credentials"}
    if not _wizard_ask_yes_no("Use an exported login request Protobuf file?", default=True):
        return result
    while True:
        login_path_text = _wizard_ask_text("Login request Protobuf path or leave empty to finish incomplete")
        if not login_path_text:
            return result
        login_path = Path(login_path_text).expanduser().resolve()
        try:
            device_id, system_id, user_uri_id, refresh_token = parse_login_request_body_file(login_path)
        except Exception:
            print(f"  Login Protobuf file '{login_path}' could not be parsed read-only.")
            if not _wizard_ask_yes_no("Try another login Protobuf file?", default=True):
                return result
            continue
        if not all(isinstance(value, str) and value for value in (device_id, system_id, user_uri_id, refresh_token)):
            print("  The login Protobuf did not contain all required text values.")
            continue
        config_values.update({"LOGIN_REQUEST_BODY_FILE": str(login_path), "DEVICE_ID": device_id, "SYSTEM_ID": system_id, "USER_URI_ID": user_uri_id})
        _wizard_queue_secret(secret_updates, env_path, "REFRESH_TOKEN", cast(str, refresh_token))
        result.update({"complete": True, "source": "login request Protobuf"})
        return result


# Validates proposed SMTP values through the shared validator without connecting
def _wizard_validate_smtp(values: dict, password: str) -> Optional[str]:
    names = ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SMTP_PASSWORD", "SENDER_EMAIL", "RECEIVER_EMAIL")
    previous = {name: globals()[name] for name in names}
    try:
        globals().update(values)
        globals()["SMTP_PASSWORD"] = password
        return validate_smtp_configuration()
    finally:
        globals().update(previous)


# Collects SMTP settings and profile-monitor notification choices
def _wizard_collect_email(config_values: dict, secret_updates: dict, env_path: Path) -> List[str]:
    if not _wizard_ask_yes_no("Configure email notifications?", default=False):
        config_values.update({"PROFILE_NOTIFICATION": False, "FOLLOWERS_FOLLOWINGS_NOTIFICATION": False, "ERROR_NOTIFICATION": False})
        return []
    while True:
        smtp_values = {
            "SMTP_HOST": _wizard_ask_text("SMTP host", required=True),
            "SMTP_PORT": _wizard_ask_positive_int("SMTP port", 587),
            "SMTP_SSL": _wizard_ask_yes_no("Enable TLS/SSL for SMTP?", default=True),
            "SMTP_USER": _wizard_ask_text("SMTP username", required=True),
            "SENDER_EMAIL": _wizard_ask_text("Sender email", required=True),
            "RECEIVER_EMAIL": _wizard_ask_text("Receiver email", required=True),
        }
        smtp_password = _wizard_ask_secret("SMTP password")
        validation_error = _wizard_validate_smtp(smtp_values, smtp_password)
        if validation_error is None:
            break
        print(f"  SMTP settings are invalid: {validation_error}")
        print("  Re-enter the SMTP settings.")
    _wizard_queue_secret(secret_updates, env_path, "SMTP_PASSWORD", smtp_password)
    config_values.update(smtp_values)
    preset = _wizard_ask_choice("Which email notifications should be enabled?", [("Profile changes and errors, recommended", "Includes playlist and follower changes."), ("Custom", "Choose profile, follower and error notifications separately.")])
    if preset == 0:
        selected = {"PROFILE_NOTIFICATION": True, "FOLLOWERS_FOLLOWINGS_NOTIFICATION": True, "ERROR_NOTIFICATION": True}
    else:
        print()
        selected = {
            "PROFILE_NOTIFICATION": _wizard_ask_yes_no("Email when the user's profile changes?", default=True),
            "FOLLOWERS_FOLLOWINGS_NOTIFICATION": _wizard_ask_yes_no("Email when followers or followings change?", default=True),
            "ERROR_NOTIFICATION": _wizard_ask_yes_no("Email on monitoring errors?", default=True),
        }
    if not selected["PROFILE_NOTIFICATION"]:
        selected["FOLLOWERS_FOLLOWINGS_NOTIFICATION"] = False
    config_values.update(selected)
    labels = {"PROFILE_NOTIFICATION": "profile", "FOLLOWERS_FOLLOWINGS_NOTIFICATION": "followers/followings", "ERROR_NOTIFICATION": "errors"}
    return [labels[name] for name in labels if selected[name]]


# Collects optional ntfy authentication without displaying the saved token
def _wizard_collect_ntfy_access_token(secret_updates: dict, env_path: Path) -> None:
    existing_token = _wizard_existing_secret("NTFY_ACCESS_TOKEN", env_path)
    if existing_token:
        choice = _wizard_ask_choice("Which ntfy authentication should be used?", [("Keep the saved access token", "Keeps the private value without displaying or changing it."), ("Paste a new access token", "Uses a hidden prompt then saves the replacement in the dotenv file."), ("Do not use an access token", "Disables the saved token. Authentication in the topic URL still works.")])
        if choice == 0:
            return
        if choice == 2:
            secret_updates["NTFY_ACCESS_TOKEN"] = ""
            print("  The saved ntfy access token will be disabled without being displayed.")
            return
    elif not _wizard_ask_yes_no("Authenticate this ntfy topic with a separate access token?", default=False):
        print("  No separate access token selected. Authentication already present in the topic URL still works.")
        return
    while True:
        token = _wizard_ask_secret("Paste the ntfy access token only").strip()
        if token and "\r" not in token and "\n" not in token and not token.casefold().startswith(("bearer ", "basic ")):
            break
        print("  Paste only the access token without a Bearer or Basic prefix.")
    if existing_token:
        secret_updates["NTFY_ACCESS_TOKEN"] = token
    else:
        _wizard_queue_secret(secret_updates, env_path, "NTFY_ACCESS_TOKEN", token)


# Collects hidden webhook details and profile-monitor alert choices
def _wizard_collect_webhook(config_values: dict, secret_updates: dict, env_path: Path) -> List[str]:
    if not _wizard_ask_yes_no("Set up webhook alerts (Discord, ntfy etc.)?", default=False):
        config_values.update({"WEBHOOK_ENABLED": False, "WEBHOOK_PROFILE_NOTIFICATION": False, "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION": False, "WEBHOOK_ERROR_NOTIFICATION": False})
        return []
    provider_choice = _wizard_ask_choice("Which webhook service should receive alerts?", [("Discord", "Sends a Discord embed to one channel webhook."), ("ntfy", "Sends a native notification to one ntfy topic URL.")])
    provider = "discord" if provider_choice == 0 else "ntfy"
    config_values["WEBHOOK_PROVIDER"] = provider
    if provider == "discord":
        print("  In Discord: Edit Channel > Integrations > Webhooks > New Webhook > Copy Webhook URL.")
    else:
        print("  In ntfy: choose a hard-to-guess topic. Paste its name for ntfy.sh or use the complete HTTPS URL for a self-hosted server.")
    existing_webhook = _wizard_existing_secret("WEBHOOK_URL", env_path, ("your_webhook_url",))
    replace_webhook = not existing_webhook or _wizard_ask_choice("Which webhook URL should be used?", [("Keep the saved URL", "Keeps the private value without displaying it."), ("Paste a new URL", "Uses a hidden prompt and saves the replacement.")]) == 1
    if replace_webhook:
        while True:
            webhook_input = _wizard_ask_secret("Paste the Discord webhook URL" if provider == "discord" else "Paste the ntfy topic URL or ntfy.sh topic name")
            webhook_url = normalize_ntfy_topic_url(webhook_input) if provider == "ntfy" else webhook_input.strip()
            if validate_webhook_url(webhook_url):
                break
            print("  That does not look like a complete HTTPS webhook destination. Try again.")
        if existing_webhook:
            secret_updates["WEBHOOK_URL"] = webhook_url
        else:
            _wizard_queue_secret(secret_updates, env_path, "WEBHOOK_URL", webhook_url)
    if provider == "ntfy":
        _wizard_collect_ntfy_access_token(secret_updates, env_path)
    config_values["WEBHOOK_ENABLED"] = True
    preset = _wizard_ask_choice("Which webhook alerts should be sent?", [("Profile changes and errors, recommended", "Includes playlist and follower changes."), ("Custom", "Choose profile, follower and error alerts separately.")])
    if preset == 0:
        selected = {"WEBHOOK_PROFILE_NOTIFICATION": True, "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION": True, "WEBHOOK_ERROR_NOTIFICATION": True}
    else:
        print()
        selected = {
            "WEBHOOK_PROFILE_NOTIFICATION": _wizard_ask_yes_no("Send a webhook when the user's profile changes?", default=True),
            "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION": _wizard_ask_yes_no("Send a webhook when followers or followings change?", default=True),
            "WEBHOOK_ERROR_NOTIFICATION": _wizard_ask_yes_no("Send a webhook when monitoring has a problem?", default=True),
        }
    if not selected["WEBHOOK_PROFILE_NOTIFICATION"]:
        selected["WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION"] = False
    config_values.update(selected)
    labels = {"WEBHOOK_PROFILE_NOTIFICATION": "profile", "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION": "followers/followings", "WEBHOOK_ERROR_NOTIFICATION": "errors"}
    return [labels[name] for name in labels if selected[name]]


WIZARD_AUTH_CONFIG_KEYS = ("TOKEN_SOURCE", "LOGIN_REQUEST_BODY_FILE", "DEVICE_ID", "SYSTEM_ID", "USER_URI_ID")
WIZARD_EMAIL_CONFIG_KEYS = ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL", "PROFILE_NOTIFICATION", "FOLLOWERS_FOLLOWINGS_NOTIFICATION", "ERROR_NOTIFICATION")
WIZARD_WEBHOOK_CONFIG_KEYS = ("WEBHOOK_ENABLED", "WEBHOOK_PROVIDER", "WEBHOOK_PROFILE_NOTIFICATION", "WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION")


# Holds editable setup answers until the user saves them
@dataclass
class WizardSetupState:
    config_path: Path
    env_path: Path
    baseline_values: dict
    config_values: dict
    secret_updates: dict
    target: str
    persist_target: bool
    auth: dict
    enabled_notifications: List[str]
    enabled_webhooks: List[str]


# Restores one editable section to setup-start values
def _wizard_reset_section(state: WizardSetupState, config_keys: Sequence[str], secret_keys: Sequence[str]) -> None:
    for key in config_keys:
        if key in state.baseline_values:
            state.config_values[key] = state.baseline_values[key]
        else:
            state.config_values.pop(key, None)
    for key in secret_keys:
        state.secret_updates.pop(key, None)


# Collects the target and persistence choice
def _wizard_collect_target_section(state: WizardSetupState, initial_target: Optional[str] = None) -> None:
    state.target = _wizard_target(initial_target or state.target or None)
    state.persist_target = _wizard_ask_yes_no("Persist this target in the generated config?", default=state.persist_target)
    state.config_values["TARGET_USER_URI_ID"] = state.target if state.persist_target else ""


# Collects one authentication mode after clearing its pending answers
def _wizard_collect_auth_section(state: WizardSetupState, method: str) -> None:
    _wizard_reset_section(state, WIZARD_AUTH_CONFIG_KEYS, ("SP_DC_COOKIE", "REFRESH_TOKEN"))
    auth_mode = _wizard_ask_choice("Choose an authentication mode", [("Cookie mode using sp_dc, recommended", "Browser import is the recommended onboarding path and Firefox is the easiest source."), ("Client mode using Spotify desktop credentials, advanced", "Uses an exported Protobuf login request.")])
    if auth_mode == 0:
        state.config_values["TOKEN_SOURCE"] = "cookie"
        state.auth = _wizard_collect_cookie_auth(method, state.env_path, state.secret_updates)
    else:
        print()
        state.config_values["TOKEN_SOURCE"] = "client"
        state.auth = _wizard_collect_client_auth(state.config_values, state.env_path, state.secret_updates)


# Collects the polling interval using the current answer as its default
def _wizard_collect_polling_section(state: WizardSetupState) -> None:
    current_interval = int(state.config_values.get("SPOTIFY_CHECK_INTERVAL", SPOTIFY_CHECK_INTERVAL))
    state.config_values["SPOTIFY_CHECK_INTERVAL"] = _wizard_ask_duration("Spotify polling interval", current_interval)


# Collects email settings after clearing pending answers
def _wizard_collect_email_section(state: WizardSetupState) -> None:
    _wizard_reset_section(state, WIZARD_EMAIL_CONFIG_KEYS, ("SMTP_PASSWORD",))
    state.enabled_notifications = _wizard_collect_email(state.config_values, state.secret_updates, state.env_path)


# Collects webhook settings after clearing pending answers
def _wizard_collect_webhook_section(state: WizardSetupState) -> None:
    _wizard_reset_section(state, WIZARD_WEBHOOK_CONFIG_KEYS, ("WEBHOOK_URL", "NTFY_ACCESS_TOKEN"))
    state.enabled_webhooks = _wizard_collect_webhook(state.config_values, state.secret_updates, state.env_path)


# Lets the user change output files and recollects secret-bearing sections
def _wizard_collect_destination_section(state: WizardSetupState, method: str) -> None:
    while True:
        config_text = _wizard_ask_text("Configuration file destination", default=str(state.config_path), required=True)
        try:
            selected_config = _wizard_validate_destination(config_text, "Configuration destination")
            break
        except ValueError as exc:
            print(f"  {exc}.")
    if selected_config != state.config_path:
        state.config_path = _wizard_choose_config_destination(selected_config)
    while True:
        env_text = _wizard_ask_text("Dotenv file destination", default=str(state.env_path), required=True)
        if env_text.casefold() == "none":
            print("  Setup needs a writable dotenv file and cannot use 'none'.")
            continue
        try:
            selected_env = _wizard_validate_destination(env_text, "Dotenv destination")
            break
        except ValueError as exc:
            print(f"  {exc}.")
    state.config_values["DOTENV_FILE"] = str(selected_env)
    if selected_env == state.env_path:
        return
    state.env_path = selected_env
    print("  The dotenv destination changed. Re-enter authentication and notification settings that may contain secrets.")
    _wizard_collect_auth_section(state, method)
    print()
    _wizard_collect_email_section(state)
    print()
    _wizard_collect_webhook_section(state)


# Prints current editable answers without exposing secrets
def _wizard_print_setup_summary(state: WizardSetupState, method: str) -> None:
    print("\nSetup summary\n")
    print(f"  Target: {state.target}")
    print(f"  Persist target: {'yes' if state.persist_target else 'no'}")
    print(f"  Polling interval: {state.config_values['SPOTIFY_CHECK_INTERVAL']} seconds")
    print(f"  Token source: {state.auth['source']}")
    print(f"  Authentication status: {'complete' if state.auth['complete'] else 'incomplete'}")
    if state.auth.get("browser"):
        print(f"  Browser: {browser_label(state.auth['browser'])}")
    print(f"  Email: {'enabled' if state.enabled_notifications else 'disabled'}")
    print(f"  Email notifications: {', '.join(state.enabled_notifications) if state.enabled_notifications else 'none'}")
    print(f"  Webhook: {'enabled' if state.enabled_webhooks else 'disabled'}")
    print(f"  Webhook alerts: {', '.join(state.enabled_webhooks) if state.enabled_webhooks else 'none'}")
    print(f"  Config destination: {state.config_path}")
    print(f"  Dotenv destination: {state.env_path}")
    print(f"  Install method: {method}")


# Opens one selected setup section then returns to the summary
def _wizard_edit_setup_section(state: WizardSetupState, method: str) -> None:
    section = _wizard_ask_choice("Which setup section should be changed?", [("Target and persistence", "Change the Spotify profile and whether it is saved."), ("Polling interval", "Change how often Spotify is checked."), ("Authentication", "Choose cookie or advanced client authentication again."), ("Email notifications", "Change SMTP details and email events."), ("Webhook alerts", "Change Discord or ntfy details and events."), ("File destinations", "Change the configuration or dotenv output path."), ("Return to summary", "Keep every current answer.")])
    if section == 0:
        print()
        _wizard_collect_target_section(state, state.target)
    elif section == 1:
        print()
        _wizard_collect_polling_section(state)
    elif section == 2:
        _wizard_collect_auth_section(state, method)
    elif section == 3:
        print()
        _wizard_collect_email_section(state)
    elif section == 4:
        print()
        _wizard_collect_webhook_section(state)
    elif section == 5:
        print()
        _wizard_collect_destination_section(state, method)


# Reviews editable answers until the user saves or discards them
def _wizard_review_setup(state: WizardSetupState, method: str) -> bool:
    while True:
        _wizard_print_setup_summary(state, method)
        action = _wizard_ask_choice("What would you like to do?", [("Save settings", "Write the displayed settings to the selected files."), ("Review or change settings", "Edit one section without losing the other answers."), ("Discard answers and exit", "Leave the destination files unchanged.")])
        if action == 0:
            return True
        if action == 1:
            _wizard_edit_setup_section(state, method)
            continue
        print()
        if _wizard_ask_yes_no("Discard all entered answers and exit?", default=False):
            return False
        print("  Setup answers retained.")


# Loads generated config and allowlisted dotenv secrets for Doctor
def _wizard_load_effective_setup(config_path: Path, env_path: Path) -> bool:
    global USER_AGENT
    if not load_config_file(config_path):
        return False
    if env_path.is_file():
        try:
            from dotenv import dotenv_values
            parsed = dotenv_values(str(env_path), interpolate=False)
            for key in SECRET_KEYS:
                if parsed.get(key) is not None:
                    globals()[key] = parsed[key]
        except Exception:
            print(f"* Error: Dotenv file '{env_path}' could not be loaded")
            return False
    if not USER_AGENT:
        USER_AGENT = get_random_spotify_user_agent() if TOKEN_SOURCE == "client" else get_random_user_agent()
    return True


# Completes browser import with retry, private entry or incomplete recovery choices
def _wizard_finish_browser_import(auth: dict, env_path: Path, config_path: Path, target: str) -> dict:
    browser = auth.get("browser")
    if not browser:
        return auth
    while True:
        try:
            run_browser_cookie_import(browser=browser, env_file=str(env_path), interactive=True, input_func=_wizard_input, config_path=str(config_path), target=target)
            auth.update({"complete": True, "validated": True})
            return auth
        except BrowserCookieImportError as exc:
            print(render_recovery_error(exc, "browser_import"))
        recovery = _wizard_ask_choice("Browser import did not complete. What next?", [("Retry browser import", "Try discovery, extraction and validation again."), ("Enter sp_dc privately", "Validate and save a manually extracted value through getpass."), ("Finish without authentication", "Keep the generated config and authenticate later.")])
        if recovery == 0:
            continue
        if recovery == 1:
            cookie = _wizard_ask_secret("Existing sp_dc value")
            try:
                validate_sp_dc_cookie(cookie)
                update_dotenv_file(env_path, {"SP_DC_COOKIE": cookie})
                auth.update({"complete": True, "validated": True, "source": "private manual entry"})
            except Exception as exc:
                print(render_recovery_error(exc, "set_sp_dc"))
                auth.update({"complete": False, "validated": False})
            return auth
        auth.update({"complete": False, "validated": False})
        return auth


# Launches monitoring with a child process on Windows or process replacement elsewhere
def _wizard_launch_monitor(arguments: Sequence[str]) -> int:
    command = [str(argument) for argument in arguments]
    if platform.system() == "Windows":
        try:
            return subprocess.run(command, check=False).returncode
        except KeyboardInterrupt:
            return 0
    os.execv(command[0], command)
    return 0


# Runs the interactive setup wizard and persists only confirmed answers
def run_setup_wizard(initial_target: Optional[str] = None, config_file=None, env_file=None) -> None:
    if not sys.stdin.isatty():
        print("The setup wizard needs an interactive terminal (TTY).")
        print("Run --setup from an interactive shell or use --generate-config and edit the files manually.")
        print(f"Guide: {SETUP_GUIDE_URL}")
        raise SystemExit(1)
    try:
        config_path, env_path = _wizard_destinations(config_file, env_file)
    except ValueError as exc:
        print(f"Setup cannot start: {exc}")
        raise SystemExit(1) from None
    method = _wizard_install_method()
    print("\nSetup Wizard\n")
    print("This asks a few questions and writes a ready-to-run configuration.")
    _wizard_print_default_guidance()
    print("Secrets go to the dotenv file. Non-secret settings go to the config file.")
    print("Cookie mode is recommended. Client mode is advanced.\n")
    print(f"Detected install method: {method}")
    print(f"Configuration:          {config_path}")
    print(f"Dotenv:                 {env_path}\n")
    config_path = _wizard_choose_config_destination(config_path)
    baseline_values = dict(globals())
    config_values = dict(baseline_values)
    config_values["DOTENV_FILE"] = str(env_path)
    initial_auth = {"complete": False, "validated": False, "browser": None, "source": "not configured"}
    state = WizardSetupState(config_path, env_path, baseline_values, config_values, {}, "", True, initial_auth, [], [])
    _wizard_collect_target_section(state, initial_target)
    _wizard_collect_polling_section(state)
    _wizard_collect_auth_section(state, method)
    print()
    _wizard_collect_email_section(state)
    print()
    _wizard_collect_webhook_section(state)
    if not _wizard_review_setup(state, method):
        print("Setup cancelled. Destination files were not changed.")
        raise SystemExit(1)
    config_content = generate_config_with_current_values(state.config_values)
    try:
        write_status = write_config_file(state.config_path, config_content)
    except Exception as exc:
        print(f"Setup could not write configuration file '{state.config_path}': {sanitize_error_text(exc)}")
        print("No dotenv changes were attempted.")
        raise SystemExit(1) from None
    print("\nSaved files\n")
    print(f"  Configuration: {write_status['path']}")
    if write_status["backup_path"]:
        print(f"  Backup:        {write_status['backup_path']}")
    if state.secret_updates or not state.env_path.exists():
        try:
            update_status = update_dotenv_file(state.env_path, state.secret_updates)
            print(f"  {'Secrets:' if state.secret_updates else 'Dotenv:':<15}{update_status['path']}")
        except Exception:
            print(f"Configuration was saved but dotenv destination '{state.env_path}' could not be updated.")
            raise SystemExit(1) from None
    if state.auth.get("browser"):
        print()
        state.auth = _wizard_finish_browser_import(state.auth, state.env_path, state.config_path, state.target)
    doctor_failed = False
    doctor_ran = False
    if state.auth["complete"] and _wizard_ask_yes_no("Run doctor now? It writes no files and offers real delivery tests only with separate approval.", default=True):
        doctor_ran = True
        if _wizard_load_effective_setup(state.config_path, state.env_path):
            doctor_failed = run_doctor(state.target, str(state.config_path), str(state.env_path)) != 0
            state.auth["validated"] = not doctor_failed
        else:
            doctor_failed = True
    command_target = None if state.persist_target else state.target
    doctor_command = _wizard_action_command(method, "--doctor", state.config_path, state.env_path, command_target)
    monitor_command = _wizard_action_command(method, "", state.config_path, state.env_path, command_target)
    print("\nNext steps\n")
    if not state.auth["complete"]:
        print("Setup was saved. Authentication still needs to be completed.\n")
        if state.config_values["TOKEN_SOURCE"] == "cookie":
            import_command = _wizard_action_command(method, f"--import-browser-cookie --browser {state.auth.get('browser') or 'firefox'}", state.config_path, state.env_path, state.target)
            _wizard_print_command("Import Spotify login from a signed-in browser:", import_command)
            _wizard_print_command("Or enter sp_dc privately:", _wizard_action_command(method, "--set-sp-dc", state.config_path, state.env_path))
        else:
            print("Complete advanced client authentication before running Doctor.\n")
        _wizard_print_command("After authentication succeeds, verify authentication and the target:", doctor_command)
    else:
        _wizard_print_command("Check setup again:", doctor_command)
    _wizard_print_command("After Doctor passes, start monitoring:" if doctor_failed or not state.auth["validated"] else "Start monitoring:", monitor_command)
    print(f"Guide: {SETUP_GUIDE_URL}\n")
    if state.auth["complete"] and not doctor_failed and state.auth["validated"] and doctor_ran and _wizard_ask_yes_no("Start monitoring now? Monitoring will continue until Ctrl+C.", default=True):
        exec_args = _wizard_local_command_args(method, exact=True)
        if not state.persist_target:
            exec_args.append(state.target)
        exec_args.extend(("--config-file", str(state.config_path), "--env-file", str(state.env_path)))
        sys.stdout.flush()
        raise SystemExit(_wizard_launch_monitor(exec_args))
    raise SystemExit(0)


# Monitors profile changes of the specified Spotify user ID
def spotify_profile_monitor_uri(user_uri_id, csv_file_name, playlists_to_skip):
    global SP_CACHED_ACCESS_TOKEN, SP_CACHED_OAUTH_APP_TOKEN
    playlists_count = 0
    playlists_old_count = 0
    playlists = None
    playlists_old = None
    playlists_zeroed_counter = 0
    followers_zeroed_counter = 0
    followings_zeroed_counter = 0
    sp_accessToken = ""
    monitor_recovery_tracker = RecoveryHintTracker()
    follower_recovery_tracker = RecoveryHintTracker()

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print_recovery_error(e, "file_write")

    email_sent = False
    webhook_sent = False

    out = f"Monitoring user {user_uri_id}"
    print(out)
    # print("-" * len(out))
    print("─" * HORIZONTAL_LINE)

    try:
        if TOKEN_SOURCE == "client":
            sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
        elif TOKEN_SOURCE == "oauth_app":
            sp_accessToken = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
        elif TOKEN_SOURCE == "oauth_user":
            sp_accessToken = spotify_get_access_token_from_oauth_user(SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, SP_USER_REDIRECT_URI, SP_USER_SCOPE, init=True)
        else:
            sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
        sp_user_data = spotify_get_user_info(sp_accessToken, user_uri_id, DETECT_CHANGES_IN_PLAYLISTS, 0)
        sp_user_followers_data = spotify_get_user_followers(sp_accessToken, user_uri_id)
        sp_user_followings_data = spotify_get_user_followings(sp_accessToken, user_uri_id)
    except Exception as e:
        err = str(e).lower()

        if TOKEN_SOURCE == 'cookie' and '401' in err:
            SP_CACHED_ACCESS_TOKEN = None
            SP_CACHED_OAUTH_APP_TOKEN = None

        context = f"{TOKEN_SOURCE}_auth"
        if '404' in err and is_user_removed(sp_accessToken, user_uri_id):
            context = "target_not_found"
        print_recovery_error(e, context, detail=e)

        sys.exit(1)

    username = sp_user_data["sp_username"]
    image_url = sp_user_data["sp_user_image_url"]

    followers = sp_user_followers_data["sp_user_followers"]
    followings = sp_user_followings_data["sp_user_followings"]

    followers_count = sp_user_data["sp_user_followers_count"]
    if followers:
        followers_count_tmp = len(followers)
        if followers_count_tmp > 0:
            followers_count = followers_count_tmp

    followings_count = sp_user_data["sp_user_followings_count"]
    if followings:
        followings_count_tmp = len(followings)
        if followings_count_tmp > 0:
            followings_count = followings_count_tmp

    if DETECT_CHANGES_IN_PLAYLISTS:
        playlists_count = sp_user_data["sp_user_public_playlists_count"]
        playlists = sp_user_data["sp_user_public_playlists_uris"]

        if ADD_PLAYLISTS_TO_MONITOR:
            playlists.extend(ADD_PLAYLISTS_TO_MONITOR)
            playlists_count += len(ADD_PLAYLISTS_TO_MONITOR)

    recently_played_artists = sp_user_data["sp_user_recently_played_artists"]

    print(f"Username:\t\t\t{username}")
    print(f"Spotify user ID:\t\t{user_uri_id}")
    print(f"User URL:\t\t\t{spotify_convert_uri_to_url(f'spotify:user:{user_uri_id}')}")

    print(f"User profile picture:\t\t{image_url != ''}", end=" ")

    display_tmp_pic(image_url, f"spotify_profile_{FILE_SUFFIX}_pic_tmp_info.jpeg", imgcat_exe, True)

    followers_label = ""
    if TOKEN_SOURCE in {"oauth_app", "oauth_user"}:
        if not sp_user_data["sp_user_followers_count_available"]:
            followers_label = f" (list and count not supported with {TOKEN_SOURCE})"
        else:
            followers_label = f" (list not supported with {TOKEN_SOURCE})"

    print(f"\nFollowers:\t\t\t{followers_count}{followers_label}")

    is_user_owner = False
    if TOKEN_SOURCE == "oauth_user":
        is_user_owner = is_token_owner(sp_accessToken, user_uri_id)

    if TOKEN_SOURCE == "oauth_user" and is_user_owner:
        print(f"Followings:\t\t\t{followings_count} (only artists, without users)")
    else:
        print(f"Followings:\t\t\t{followings_count}" + (f" (list and count not supported with {TOKEN_SOURCE})" if TOKEN_SOURCE in {"oauth_app", "oauth_user"} else ""))

    list_of_playlists = []

    if DETECT_CHANGES_IN_PLAYLISTS:
        if TOKEN_SOURCE == "oauth_user" and is_user_owner:
            print(f"Playlists:\t\t\t{playlists_count}")
        else:
            print(f"Public playlists:\t\t{playlists_count}")

        if playlists:
            list_of_playlists, error_while_processing = spotify_process_public_playlists(sp_accessToken, playlists, True, playlists_to_skip)
            spotify_print_public_playlists(sp_accessToken, list_of_playlists, playlists_to_skip)

    print_cur_ts("\nTimestamp:\t\t\t")

    followers_file = f"spotify_profile_{FILE_SUFFIX}_followers.json"
    followings_file = f"spotify_profile_{FILE_SUFFIX}_followings.json"
    playlists_file = f"spotify_profile_{FILE_SUFFIX}_playlists.json"
    profile_pic_file = f"spotify_profile_{FILE_SUFFIX}_pic.jpeg"
    profile_pic_file_old = f"spotify_profile_{FILE_SUFFIX}_pic_old.jpeg"
    profile_pic_file_tmp = f"spotify_profile_{FILE_SUFFIX}_pic_tmp.jpeg"

    followers_old = followers
    followings_old = followings

    followers_old_count = followers_count
    followings_old_count = followings_count

    username_old = username

    if DETECT_CHANGES_IN_PLAYLISTS:
        playlists_old = playlists
        playlists_old_count = playlists_count

    list_of_playlists_old = list_of_playlists

    followers_read = []
    followings_read = []
    playlists_read = []

    # playlists
    if DETECT_CHANGES_IN_PLAYLISTS:
        if os.path.isfile(playlists_file):
            try:
                with open(playlists_file, 'r', encoding="utf-8") as f:
                    playlists_read = json.load(f)
            except Exception as e:
                print_operation_error(f"Playlist history could not be loaded from '{playlists_file}'", e)
            if playlists_read:
                playlists_old_count = playlists_read[0]
                playlists_old = playlists_read[1]
                playlists_mdate = datetime.fromtimestamp(int(os.path.getmtime(playlists_file)), pytz.timezone(LOCAL_TIMEZONE))
                print(f"* Playlists ({playlists_old_count}) loaded from file '{playlists_file}' ({get_short_date_from_ts(playlists_mdate, show_weekday=False, always_show_year=True)})")
        if not playlists_read:
            playlists_to_save = []
            playlists_to_save.append(playlists_count)
            playlists_to_save.append(playlists)
            try:
                with open(playlists_file, 'w', encoding="utf-8") as f:
                    json.dump(playlists_to_save, f, indent=2)
                print(f"* Playlists ({playlists_count}) saved to file '{playlists_file}'")
            except Exception as e:
                print_operation_error(f"Playlist history could not be saved to '{playlists_file}'", e)

        if playlist_collection_changed(playlists, playlists_old, playlists_count, playlists_old_count):
            spotify_print_changed_followers_followings_playlists(username, playlists, playlists_old, playlists_count, playlists_old_count, "Playlists", "for", "Added playlists to profile", "Added Playlist", "Removed playlists from profile", "Removed Playlist", playlists_file, csv_file_name, False, True, sp_accessToken)

        print_cur_ts("Timestamp:\t\t\t")

    # followers
    if os.path.isfile(followers_file):
        try:
            with open(followers_file, 'r', encoding="utf-8") as f:
                followers_read = json.load(f)
        except Exception as e:
            print_operation_error(f"Follower history could not be loaded from '{followers_file}'", e)
        if followers_read:
            followers_old_count = followers_read[0]
            followers_old = followers_read[1]
            followers_mdate = datetime.fromtimestamp(int(os.path.getmtime(followers_file)), pytz.timezone(LOCAL_TIMEZONE))
            print(f"* Followers ({followers_old_count}) loaded from file '{followers_file}' ({get_short_date_from_ts(followers_mdate, show_weekday=False, always_show_year=True)})")
    if not followers_read:
        followers_to_save = []
        followers_to_save.append(followers_count)
        followers_to_save.append(followers)
        try:
            with open(followers_file, 'w', encoding="utf-8") as f:
                json.dump(followers_to_save, f, indent=2)
            print(f"* Followers ({followers_count}) saved to file '{followers_file}'")
        except Exception as e:
            print_operation_error(f"Follower history could not be saved to '{followers_file}'", e)

    if followers_count != followers_old_count:
        spotify_print_changed_followers_followings_playlists(username, followers, followers_old, followers_count, followers_old_count, "Followers", "for", "Added followers", "Added Follower", "Removed followers", "Removed Follower", followers_file, csv_file_name, False, False)

    print_cur_ts("Timestamp:\t\t\t")

    # followings
    if os.path.isfile(followings_file):
        try:
            with open(followings_file, 'r', encoding="utf-8") as f:
                followings_read = json.load(f)
        except Exception as e:
            print_operation_error(f"Following history could not be loaded from '{followings_file}'", e)
        if followings_read:
            followings_old_count = followings_read[0]
            followings_old = followings_read[1]
            followings_mdate = datetime.fromtimestamp(int(os.path.getmtime(followings_file)), pytz.timezone(LOCAL_TIMEZONE))
            print(f"* Followings ({followings_old_count}) loaded from file '{followings_file}' ({get_short_date_from_ts(followings_mdate, show_weekday=False, always_show_year=True)})")
    if not followings_read:
        followings_to_save = []
        followings_to_save.append(followings_count)
        followings_to_save.append(followings)
        try:
            with open(followings_file, 'w', encoding="utf-8") as f:
                json.dump(followings_to_save, f, indent=2)
            print(f"* Followings ({followings_count}) saved to file '{followings_file}'")
        except Exception as e:
            print_operation_error(f"Following history could not be saved to '{followings_file}'", e)

    if followings_count != followings_old_count:
        spotify_print_changed_followers_followings_playlists(username, followings, followings_old, followings_count, followings_old_count, "Followings", "by", "Added followings", "Added Following", "Removed followings", "Removed Following", followings_file, csv_file_name, False, False)

    print_cur_ts("Timestamp:\t\t\t")

    # profile pic

    if DETECT_CHANGED_PROFILE_PIC:

        # User has no profile pic, but it exists in the filesystem
        if not image_url and os.path.isfile(profile_pic_file):
            profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)), pytz.timezone(LOCAL_TIMEZONE))
            print(f"* User {username} has removed profile picture added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ! (after {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)})")
            os.replace(profile_pic_file, profile_pic_file_old)

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, now_local_naive(), "Profile Picture Removed", username, convert_to_local_naive(profile_pic_mdate_dt), "")
            except Exception as e:
                print_operation_error("A CSV event could not be written", e)

            print_cur_ts("Timestamp:\t\t\t")

        # User has profile pic, but it does not exist in the filesystem
        elif image_url and not os.path.isfile(profile_pic_file):
            if save_profile_pic(image_url, profile_pic_file):
                profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)), pytz.timezone(LOCAL_TIMEZONE))
                print(f"* User {username} profile picture saved to '{profile_pic_file}'")
                print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)")

                try:
                    if imgcat_exe:
                        display_image_via_imgcat(imgcat_exe, profile_pic_file, blank_before=True, blank_after=True)
                    shutil.copy2(profile_pic_file, f'spotify_profile_{FILE_SUFFIX}_pic_{profile_pic_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                except Exception:
                    pass

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, now_local_naive(), "Profile Picture Created", username, "", convert_to_local_naive(profile_pic_mdate_dt))
                except Exception as e:
                    print_operation_error("A CSV event could not be written", e)

            else:
                print(f"* Error saving profile picture !")

            print_cur_ts("Timestamp:\t\t\t")

        # User has profile pic and it exists in the filesystem, but we check if it has not changed
        elif image_url and os.path.isfile(profile_pic_file):
            profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)), pytz.timezone(LOCAL_TIMEZONE))
            if save_profile_pic(image_url, profile_pic_file_tmp):
                profile_pic_tmp_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file_tmp)), pytz.timezone(LOCAL_TIMEZONE))

                if not compare_images(profile_pic_file, profile_pic_file_tmp) and profile_pic_mdate_dt != profile_pic_tmp_mdate_dt:
                    print(f"* User {username} has changed profile picture ! (previous one added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} - {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)")
                    print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_tmp_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)")

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), "Profile Picture Changed", username, convert_to_local_naive(profile_pic_mdate_dt), convert_to_local_naive(profile_pic_tmp_mdate_dt))
                    except Exception as e:
                        print_operation_error("A CSV event could not be written", e)

                    try:
                        if imgcat_exe:
                            display_image_via_imgcat(imgcat_exe, profile_pic_file_tmp, blank_before=True, blank_after=True)
                        shutil.copy2(profile_pic_file_tmp, f'spotify_profile_{FILE_SUFFIX}_pic_{profile_pic_tmp_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                        os.replace(profile_pic_file, profile_pic_file_old)
                        os.replace(profile_pic_file_tmp, profile_pic_file)
                    except Exception as e:
                        print_operation_error("Profile picture files could not be replaced or copied", e)

                else:
                    print(f"* Profile picture '{profile_pic_file}' already exists")
                    print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)")
                    try:
                        os.remove(profile_pic_file_tmp)
                    except Exception:
                        pass
            else:
                print(f"* Error while checking if the profile picture has changed !")
            print_cur_ts("Timestamp:\t\t\t")

    followers_old = followers
    followings_old = followings
    followers_old_count = followers_count
    followings_old_count = followings_count

    if DETECT_CHANGES_IN_PLAYLISTS:
        playlists_old = playlists
        playlists_old_count = playlists_count

    time.sleep(SPOTIFY_CHECK_INTERVAL)
    email_sent = False
    webhook_sent = False
    alive_counter = 0

    # Primary loop
    while True:
        debug_print(f"Loop tick: token_source={TOKEN_SOURCE}, check_interval={SPOTIFY_CHECK_INTERVAL}, error_interval={SPOTIFY_ERROR_INTERVAL}")
        # Sometimes Spotify network functions halt even though we specified the timeout
        # To overcome this we use alarm signal functionality to kill it inevitably, not available on Windows
        # The helper preserves any enclosing deadline so nested per-request alarms cannot disable this watchdog
        alarm_state = _start_timeout_alarm(ALARM_TIMEOUT)
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            elif TOKEN_SOURCE == "oauth_app":
                sp_accessToken = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
            elif TOKEN_SOURCE == "oauth_user":
                sp_accessToken = spotify_get_access_token_from_oauth_user(SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, SP_USER_REDIRECT_URI, SP_USER_SCOPE)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
            sp_user_data = spotify_get_user_info(sp_accessToken, user_uri_id, DETECT_CHANGES_IN_PLAYLISTS, 0)
            email_sent = False
            webhook_sent = False
            monitor_recovery_tracker.reset()
            _restore_timeout_alarm(alarm_state)
        except TimeoutException as e:
            _restore_timeout_alarm(alarm_state)
            print_monitor_recovery(e, "runtime", monitor_recovery_tracker, f"* Error, retrying in {display_time(ALARM_RETRY)}: ")
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(ALARM_RETRY)
            continue
        except Exception as e:
            _restore_timeout_alarm(alarm_state)

            debug_print(f"Main monitor loop error: {sanitize_error_text(e)}")

            err = str(e).lower()

            if TOKEN_SOURCE == 'cookie' and '401' in err:
                SP_CACHED_ACCESS_TOKEN = None

            context = f"{TOKEN_SOURCE}_auth"
            if 'not found' in err or '404' in err:
                context = "target_not_found"
            advice = print_monitor_recovery(e, context, monitor_recovery_tracker, f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: ")
            if notification_channels_pending("error", ERROR_NOTIFICATION, email_sent, webhook_sent):
                safe_detail = sanitize_error_text(e)
                m_subject = f"spotify_profile_monitor: {advice.summary} (uri: {user_uri_id})"
                m_body = f"{advice.summary}\n\nTo fix: {advice.fix}\n\nTechnical detail: {safe_detail}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                m_body_html = f"<html><head></head><body>{escape(advice.summary)}<br><br>To fix: {escape(advice.fix)}<br><br>Technical detail: {escape(safe_detail)}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                email_sent, webhook_sent = send_pending_error_notification(m_subject, m_body, m_body_html, email_sent, webhook_sent)

            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(SPOTIFY_ERROR_INTERVAL)
            continue

        username = sp_user_data["sp_username"]
        image_url = sp_user_data["sp_user_image_url"]

        # Spotify username has changed
        if username != username_old:
            print(f"* User '{username_old}' has changed username to '{username}'")

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, now_local_naive(), "Username", username, username_old, username)
            except Exception as e:
                print_operation_error("A CSV event could not be written", e)

            if notification_channels_enabled("profile", PROFILE_NOTIFICATION):
                m_subject = f"Spotify user {username_old} has changed username to {username}"
                m_body = f"Spotify user '{username_old}' has changed username to '{username}'\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                m_body_html = f"<html><head></head><body>Spotify user '<b>{escape(username_old)}</b>' has changed username to '<b>{escape(username)}</b>'<br><br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
                send_notification_channels("profile", m_subject, m_body, m_body_html, email_enabled=PROFILE_NOTIFICATION, image_url=image_url)

            username_old = username

            print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
            print_cur_ts("Timestamp:\t\t\t")

        try:
            sp_user_followings_data = spotify_get_user_followings(sp_accessToken, user_uri_id)
            sp_user_followers_data = spotify_get_user_followers(sp_accessToken, user_uri_id)
            follower_recovery_tracker.reset()
        except Exception as e:
            print_monitor_recovery(e, f"{TOKEN_SOURCE}_auth", follower_recovery_tracker, f"* Error while getting followers and followings, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: ")
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(SPOTIFY_ERROR_INTERVAL)
            continue

        followers = sp_user_followers_data["sp_user_followers"]
        followings = sp_user_followings_data["sp_user_followings"]

        followers_count = sp_user_data["sp_user_followers_count"]
        if followers:
            followers_count_tmp = len(followers)
            if followers_count_tmp > 0:
                followers_count = followers_count_tmp

        followings_count = sp_user_data["sp_user_followings_count"]
        if followings:
            followings_count_tmp = len(followings)
            if followings_count_tmp > 0:
                followings_count = followings_count_tmp

        if DETECT_CHANGES_IN_PLAYLISTS:
            playlists_count = sp_user_data["sp_user_public_playlists_count"]
            playlists = sp_user_data["sp_user_public_playlists_uris"]

            if ADD_PLAYLISTS_TO_MONITOR:
                playlists.extend(ADD_PLAYLISTS_TO_MONITOR)
                playlists_count += len(ADD_PLAYLISTS_TO_MONITOR)

        recently_played_artists = sp_user_data["sp_user_recently_played_artists"]

        if followers_count != followers_old_count:
            if followers_count == 0:
                followers_zeroed_counter += 1
                if followers_zeroed_counter == FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER:
                    print(f"* Spotify API: Followers count dropped from {followers_old_count} to 0 and has been 0 for {followers_zeroed_counter} checks; accepting 0 as the new baseline")
                    spotify_print_changed_followers_followings_playlists(username, followers, followers_old, followers_count, followers_old_count, "Followers", "for", "Added followers", "Added Follower", "Removed followers", "Removed Follower", followers_file, csv_file_name, PROFILE_NOTIFICATION, False, notification_image_url=image_url, webhook_notification_allowed=True)
                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t\t")
                    followers_old_count = followers_count
                    followers_old = followers
                    followers_zeroed_counter = 0
                elif followers_zeroed_counter < FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER:
                    print(f"* Spotify API: Followers count dropped from {followers_old_count} to 0, streak {followers_zeroed_counter}/{FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER}; old count and list retained")
                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t\t")
            else:
                if followers_old_count == 0 and followers_zeroed_counter >= FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER:
                    print(f"* Spotify API: Followers count recovered to {followers_count}; previously was 0 for {followers_zeroed_counter} checks (old baseline was {followers_old_count})")

                spotify_print_changed_followers_followings_playlists(username, followers, followers_old, followers_count, followers_old_count, "Followers", "for", "Added followers", "Added Follower", "Removed followers", "Removed Follower", followers_file, csv_file_name, PROFILE_NOTIFICATION, False, notification_image_url=image_url, webhook_notification_allowed=True)
                print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                print_cur_ts("Timestamp:\t\t\t")
                followers_old_count = followers_count
                followers_old = followers
                followers_zeroed_counter = 0

        elif followers_count == followers_old_count:
            if followers_count == 0:
                followers_zeroed_counter = 0
                followers_old = followers
            else:
                if followers_zeroed_counter > 0:
                    print(f"* Spotify API: Followers count recovered to {followers_count} (matching old baseline) after a streak of {followers_zeroed_counter} checks")
                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t\t")
                followers_zeroed_counter = 0
                followers_old = followers

        if followings_count != followings_old_count:
            if followings_count == 0:
                followings_zeroed_counter += 1
                if followings_zeroed_counter == FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER:
                    print(f"* Spotify API: Followings count dropped from {followings_old_count} to 0 and has been 0 for {followings_zeroed_counter} checks; accepting 0 as the new baseline")
                    spotify_print_changed_followers_followings_playlists(username, followings, followings_old, followings_count, followings_old_count, "Followings", "by", "Added followings", "Added Following", "Removed followings", "Removed Following", followings_file, csv_file_name, PROFILE_NOTIFICATION, False, notification_image_url=image_url, webhook_notification_allowed=True)
                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t\t")
                    followings_old_count = followings_count
                    followings_old = followings
                    followings_zeroed_counter = 0
                elif followings_zeroed_counter < FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER:
                    print(f"* Spotify API: Followings count dropped from {followings_old_count} to 0, streak {followings_zeroed_counter}/{FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER}; old count and list retained")
                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t\t")
            else:
                if followings_old_count == 0 and followings_zeroed_counter >= FOLLOWERS_FOLLOWINGS_DISAPPEARED_COUNTER:
                    print(f"* Spotify API: Followings count recovered to {followings_count}; previously was 0 for {followings_zeroed_counter} checks (old baseline was {followings_old_count})")

                spotify_print_changed_followers_followings_playlists(username, followings, followings_old, followings_count, followings_old_count, "Followings", "by", "Added followings", "Added Following", "Removed followings", "Removed Following", followings_file, csv_file_name, PROFILE_NOTIFICATION, False, notification_image_url=image_url, webhook_notification_allowed=True)
                print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                print_cur_ts("Timestamp:\t\t\t")
                followings_old_count = followings_count
                followings_old = followings
                followings_zeroed_counter = 0

        elif followings_count == followings_old_count:
            if followings_count == 0:
                followings_zeroed_counter = 0
                followings_old = followings
            else:
                if followings_zeroed_counter > 0:
                    print(f"* Spotify API: Followings count recovered to {followings_count} (matching old baseline) after a streak of {followings_zeroed_counter} checks")
                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t\t")
                followings_zeroed_counter = 0
                followings_old = followings

        # profile pic

        if DETECT_CHANGED_PROFILE_PIC:

            # User has no profile pic, but it exists in the filesystem
            if not image_url and os.path.isfile(profile_pic_file):
                profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)), pytz.timezone(LOCAL_TIMEZONE))
                print(f"* User {username} has removed profile picture added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ! (after {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)})\n")
                os.replace(profile_pic_file, profile_pic_file_old)

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, now_local_naive(), "Profile Picture Removed", username, convert_to_local_naive(profile_pic_mdate_dt), "")
                except Exception as e:
                    print_operation_error("A CSV event could not be written", e)

                if notification_channels_enabled("profile", PROFILE_NOTIFICATION):
                    m_subject = f"Spotify user {username} has removed profile picture ! (after {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)})"
                    m_body = f"Spotify user {username} has removed profile picture added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} (after {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)})\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>Spotify user <b>{escape(username)}</b> has removed profile picture added on <b>{escape(get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True))}</b> (after <b>{escape(calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2))}</b>)<br><br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
                    send_notification_channels("profile", m_subject, m_body, m_body_html, email_enabled=PROFILE_NOTIFICATION)

                print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                print_cur_ts("Timestamp:\t\t\t")

            # User has profile pic, but it does not exist in the filesystem
            elif image_url and not os.path.isfile(profile_pic_file):
                print(f"* User {username} has set profile picture !")
                m_body_html_pic_saved_text = ""
                if save_profile_pic(image_url, profile_pic_file):
                    profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)), pytz.timezone(LOCAL_TIMEZONE))
                    print(f"* User profile picture saved to '{profile_pic_file}'")
                    print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)\n")
                    m_body_html_pic_saved_text = f'<br><br><img src="cid:profile_pic">'

                    try:
                        if imgcat_exe:
                            display_image_via_imgcat(imgcat_exe, profile_pic_file, blank_after=True)
                        shutil.copy2(profile_pic_file, f'spotify_profile_{FILE_SUFFIX}_pic_{profile_pic_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                    except Exception:
                        pass

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), "Profile Picture Created", username, "", convert_to_local_naive(profile_pic_mdate_dt))
                    except Exception as e:
                        print_operation_error("A CSV event could not be written", e)

                    if notification_channels_enabled("profile", PROFILE_NOTIFICATION):
                        m_subject = f"Spotify user {username} has set profile picture ! ({get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)})"
                        m_body = f"Spotify user {username} has set profile picture !\n\nProfile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Spotify user <b>{escape(username)}</b> has set profile picture !{m_body_html_pic_saved_text}<br><br>Profile picture has been added on <b>{get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)}</b> ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)<br><br>Check interval: <b>{display_time(SPOTIFY_CHECK_INTERVAL)}</b> ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts('<br>Timestamp: ')}</body></html>"
                        send_notification_channels("profile", m_subject, m_body, m_body_html, email_enabled=PROFILE_NOTIFICATION, image_url=image_url, email_image_file=profile_pic_file, email_image_name="profile_pic")

                else:
                    print(f"* Error saving profile picture !\n")

                print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                print_cur_ts("Timestamp:\t\t\t")

            # User has profile pic and it exists in the filesystem, but we check if it has not changed
            elif image_url and os.path.isfile(profile_pic_file):
                profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)), pytz.timezone(LOCAL_TIMEZONE))
                if save_profile_pic(image_url, profile_pic_file_tmp):
                    profile_pic_tmp_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file_tmp)), pytz.timezone(LOCAL_TIMEZONE))

                    if not compare_images(profile_pic_file, profile_pic_file_tmp) and profile_pic_mdate_dt != profile_pic_tmp_mdate_dt:
                        print(f"* User {username} has changed profile picture ! (previous one added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} - {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)")
                        print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_tmp_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)\n")
                        m_body_html_pic_saved_text = ""

                        try:
                            if csv_file_name:
                                write_csv_entry(csv_file_name, now_local_naive(), "Profile Picture Changed", username, convert_to_local_naive(profile_pic_mdate_dt), convert_to_local_naive(profile_pic_tmp_mdate_dt))
                        except Exception as e:
                            print_operation_error("A CSV event could not be written", e)

                        try:
                            if imgcat_exe:
                                display_image_via_imgcat(imgcat_exe, profile_pic_file_tmp, blank_after=True)
                            shutil.copy2(profile_pic_file_tmp, f'spotify_profile_{FILE_SUFFIX}_pic_{profile_pic_tmp_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                            os.replace(profile_pic_file, profile_pic_file_old)
                            os.replace(profile_pic_file_tmp, profile_pic_file)
                        except Exception as e:
                            print_operation_error("Profile picture files could not be replaced or copied", e)

                        if notification_channels_enabled("profile", PROFILE_NOTIFICATION):
                            m_body_html_pic_saved_text = f'<br><br><img src="cid:profile_pic">'
                            m_subject = f"Spotify user {username} has changed profile picture ! (after {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)})"
                            m_body = f"Spotify user {username} has changed profile picture !\n\nPrevious one added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)\n\nProfile picture has been added on {get_short_date_from_ts(profile_pic_tmp_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                            m_body_html = f"<html><head></head><body>Spotify user <b>{escape(username)}</b> has changed profile picture !{m_body_html_pic_saved_text}<br><br>Previous one added on <b>{get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)}</b> ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)<br><br>Profile picture has been added on <b>{get_short_date_from_ts(profile_pic_tmp_mdate_dt, always_show_year=True)}</b> ({calculate_timespan(now_local(), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)<br><br>Check interval: <b>{display_time(SPOTIFY_CHECK_INTERVAL)}</b> ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts('<br>Timestamp: ')}</body></html>"
                            send_notification_channels("profile", m_subject, m_body, m_body_html, email_enabled=PROFILE_NOTIFICATION, image_url=image_url, email_image_file=profile_pic_file, email_image_name="profile_pic")

                        print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                        print_cur_ts("Timestamp:\t\t\t")
                    else:
                        try:
                            os.remove(profile_pic_file_tmp)
                        except Exception:
                            pass
                else:
                    print(f"* Error while checking if the profile pic has changed !\n")
                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t\t")

        list_of_playlists = []
        error_while_processing = False

        if DETECT_CHANGES_IN_PLAYLISTS:
            if playlists:
                list_of_playlists, error_while_processing = spotify_process_public_playlists(sp_accessToken, playlists, True, playlists_to_skip, show_progress=False)

            for playlist in list_of_playlists:
                if "uri" in playlist:
                    p_uri = playlist.get("uri", "")
                    p_owner = playlist.get("owner", "")
                    p_owner_uri = playlist.get("owner_uri", "")
                    p_uri_id = spotify_extract_id_or_name(p_uri)
                    p_owner_name = spotify_extract_id_or_name(p_owner)
                    p_owner_id = spotify_extract_id_or_name(p_owner_uri)

                    # We do not process playlists that are ignored
                    if (playlists_to_skip and (p_uri_id in playlists_to_skip or p_owner_id in playlists_to_skip or p_owner_name in playlists_to_skip)) or (IGNORE_SPOTIFY_PLAYLISTS and p_owner_id == "spotify"):
                        continue
                    p_name = playlist.get("name", "")
                    p_url = spotify_convert_uri_to_url(p_uri)
                    p_descr = html.unescape(playlist.get("desc", ""))
                    p_likes = playlist.get("likes", 0)
                    p_tracks = playlist.get("tracks_count", 0)
                    p_date = playlist.get("date")
                    p_update = playlist.get("update_date")
                    p_collaborators = playlist.get("collaborators_count")
                    p_collaborators_list = playlist.get("collaborators")
                    p_tracks_list = playlist.get("list_of_tracks")
                    p_restricted = bool(playlist.get("restricted", False))
                    p_source = playlist.get("source", "")
                    p_image_url = playlist.get("image_url", "")
                    for playlist_old in list_of_playlists_old:
                        if "uri" in playlist_old:
                            if playlist_old.get("uri") == p_uri:
                                p_name_old = playlist_old.get("name")
                                p_descr_old = playlist_old.get("desc")
                                p_likes_old = playlist_old.get("likes")
                                p_tracks_old = playlist_old.get("tracks_count")
                                p_update_old = playlist_old.get("update_date")
                                p_tracks_list_old = playlist_old.get("list_of_tracks")
                                p_collaborators_old = playlist_old.get("collaborators_count")
                                p_collaborators_list_old = playlist_old.get("collaborators")
                                p_restricted_old = bool(playlist_old.get("restricted", False))
                                p_source_old = playlist_old.get("source", "")
                                p_image_url = str(p_image_url or playlist_old.get("image_url", "") or "")
                                restricted_pair = p_restricted or p_restricted_old
                                # When the backend that produced this snapshot differs from the previous one, the two
                                # sources can legitimately disagree on the filtered track set (for example a different
                                # market), so treat this cycle as a silent re-baseline and skip track/collaborator
                                # change detection to avoid spurious notifications
                                source_changed = bool(p_source) and bool(p_source_old) and p_source != p_source_old
                                if source_changed:
                                    debug_print(f"playlist diff: uri={p_uri} backend source changed ({p_source_old} -> {p_source}); re-baselining tracks/collaborators without notification")

                                likes_display_old = p_likes_old if p_likes_old is not None else "n/a"
                                likes_display_new = p_likes if p_likes is not None else "n/a"

                                # Number of likes changed while both snapshots contain numeric values
                                if playlist_likes_changed(p_likes_old, p_likes) and p_likes_old is not None and p_likes is not None:
                                    try:
                                        p_likes_diff = p_likes - p_likes_old
                                        if p_likes_diff > 0:
                                            p_likes_diff_str = "+" + str(p_likes_diff)
                                        else:
                                            p_likes_diff_str = str(p_likes_diff)
                                        p_message = f"* Playlist '{p_name}': number of likes changed from {p_likes_old} to {p_likes} ({p_likes_diff_str})\n* Playlist URL: {p_url}\n"
                                        print(p_message)
                                    except Exception as e:
                                        print_operation_error(f"Likes for playlist {spotify_format_playlist_reference(p_uri)} could not be processed and will be retried", e)
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue

                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Playlist Likes", p_name, likes_display_old, likes_display_new)
                                    except Exception as e:
                                        print_operation_error("A CSV event could not be written", e)

                                    m_subject = f"Spotify user {username} number of likes for playlist '{p_name}' has changed! ({p_likes_diff_str}, {likes_display_old} -> {likes_display_new})"
                                    m_body = f"{p_message}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>Playlist '<b><a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a></b>': number of likes changed from <b>{escape(str(likes_display_old))}</b> to <b>{escape(str(likes_display_new))}</b> (<b>{escape(p_likes_diff_str)}</b>)<br><br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
                                    send_notification_channels("profile", m_subject, m_body, m_body_html, email_enabled=PROFILE_NOTIFICATION, image_url=select_notification_image_url(p_image_url, profile_image_url=image_url), email_image_url=p_image_url)
                                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t\t")

                                if restricted_pair:
                                    if p_name != p_name_old:
                                        p_message = f"* Playlist '{p_name_old}': name changed to new name '{p_name}' [RESTRICTED]\n* Playlist URL: {p_url}\n"
                                        print(p_message)
                                        try:
                                            if csv_file_name:
                                                write_csv_entry(csv_file_name, now_local_naive(), "Playlist Name", username, p_name_old, p_name)
                                        except Exception as e:
                                            print_operation_error("A CSV event could not be written", e)
                                        m_subject = f"Spotify user {username} playlist '{p_name_old}' name changed to '{p_name}'! [RESTRICTED]"
                                        m_body = f"{p_message}\nMetadata source: profile-view only\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                        m_body_html = f"<html><head></head><body>Playlist '<b>{escape(p_name_old)}</b>': name changed to new name '<b><a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a></b>' [<b>RESTRICTED</b>]<br><br>Metadata source: profile-view only<br><br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
                                        send_notification_channels("profile", m_subject, m_body, m_body_html, email_enabled=PROFILE_NOTIFICATION, image_url=select_notification_image_url(p_image_url, profile_image_url=image_url), email_image_url=p_image_url)
                                        print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                        print_cur_ts("Timestamp:\t\t\t")
                                    continue

                                # Number of collaborators changed

                                # Suppress transient collaborator glitches by confirming changes across multiple checks,
                                # and keep a stable baseline per playlist to avoid baseline poisoning
                                global COLLABORATORS_BASELINE_CACHE
                                global COLLABORATORS_PENDING_CACHE

                                stable_entry = COLLABORATORS_BASELINE_CACHE.get(p_uri)
                                if stable_entry is None:
                                    # Initialize baseline from previously persisted playlist snapshot (if available)
                                    stable_ids = set((p_collaborators_list_old or {}).keys()) if isinstance(p_collaborators_list_old, dict) else set()
                                    stable_map = (p_collaborators_list_old or {}) if isinstance(p_collaborators_list_old, dict) else {}
                                    COLLABORATORS_BASELINE_CACHE[p_uri] = {"ids": stable_ids, "map": stable_map}
                                    stable_entry = COLLABORATORS_BASELINE_CACHE[p_uri]

                                stable_ids = set(stable_entry.get("ids") or set())
                                stable_map = stable_entry.get("map") or {}
                                current_ids = set((p_collaborators_list or {}).keys()) if isinstance(p_collaborators_list, dict) else set()
                                suppress_collab_notification = False

                                if source_changed and current_ids != stable_ids:
                                    # Backend switched this cycle; adopt the new source's collaborators as the baseline
                                    # instead of reporting a switch-induced difference as a real collaborator change
                                    current_map = (p_collaborators_list or {}) if isinstance(p_collaborators_list, dict) else {}
                                    stable_ids = current_ids
                                    stable_map = current_map
                                    COLLABORATORS_BASELINE_CACHE[p_uri] = {"ids": current_ids, "map": current_map}
                                    COLLABORATORS_PENDING_CACHE.pop(p_uri, None)
                                    suppress_collab_notification = True

                                if current_ids != stable_ids:
                                    pending = COLLABORATORS_PENDING_CACHE.get(p_uri)
                                    if pending and pending.get("new_ids") == current_ids:
                                        pending["streak"] = int(pending.get("streak", 0)) + 1
                                    else:
                                        pending = {
                                            "new_ids": current_ids,
                                            "new_map": (p_collaborators_list or {}) if isinstance(p_collaborators_list, dict) else {},
                                            "streak": 1,
                                            "first_seen_ts": time.time()
                                        }
                                        COLLABORATORS_PENDING_CACHE[p_uri] = pending

                                    if int(pending.get("streak", 0)) < int(COLLABORATORS_CHANGE_COUNTER):
                                        print(f"* Spotify API: suspected transient collaborator change for playlist '{p_name}' ({len(stable_ids)} -> {len(current_ids)}), streak {pending.get('streak')}/{COLLABORATORS_CHANGE_COUNTER}; will confirm next check")
                                        print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                        print_cur_ts("Timestamp:\t\t\t")
                                        suppress_collab_notification = True
                                    else:
                                        p_collaborators_old = len(stable_ids)
                                        p_collaborators_list_old = stable_map
                                        p_collaborators = len(current_ids)
                                        p_collaborators_list = (p_collaborators_list or {}) if isinstance(p_collaborators_list, dict) else {}

                                        # Update stable baseline and clear pending
                                        COLLABORATORS_BASELINE_CACHE[p_uri] = {"ids": current_ids, "map": p_collaborators_list}
                                        try:
                                            del COLLABORATORS_PENDING_CACHE[p_uri]
                                        except Exception:
                                            pass
                                else:
                                    # No change vs stable baseline; clear any pending candidate
                                    if p_uri in COLLABORATORS_PENDING_CACHE:
                                        # If we had a pending change and we're back to stable baseline, this was a transient glitch that resolved - suppress notification
                                        suppress_collab_notification = True
                                        # Update the old values to match current stable baseline so the notification condition check fails
                                        p_collaborators_old = len(stable_ids)
                                        p_collaborators_list_old = stable_map
                                        p_collaborators = len(current_ids)
                                        p_collaborators_list = (p_collaborators_list or {}) if isinstance(p_collaborators_list, dict) else {}
                                        try:
                                            del COLLABORATORS_PENDING_CACHE[p_uri]
                                        except Exception:
                                            pass

                                if not suppress_collab_notification and p_collaborators != p_collaborators_old:
                                    try:

                                        p_collaborators_diff = p_collaborators - p_collaborators_old
                                        p_collaborators_diff_str = ""

                                        if p_collaborators_diff > 0:
                                            p_collaborators_diff_str = "+" + str(p_collaborators_diff)
                                        else:
                                            p_collaborators_diff_str = str(p_collaborators_diff)

                                        p_message = f"* Playlist '{p_name}': number of collaborators changed from {p_collaborators_old} to {p_collaborators} ({p_collaborators_diff_str})\n* Playlist URL: {p_url}\n"
                                        print(p_message)
                                    except Exception as e:
                                        print_operation_error(f"Collaborators for playlist {spotify_format_playlist_reference(p_uri)} could not be processed and will be retried", e)
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue

                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Collaborators Number", p_name, p_collaborators_old, p_collaborators)
                                    except Exception as e:
                                        print_operation_error("A CSV event could not be written", e)

                                    try:

                                        added_keys = p_collaborators_list.keys() - p_collaborators_list_old.keys()
                                        removed_keys = p_collaborators_list_old.keys() - p_collaborators_list.keys()

                                        added_collaborators = {key: p_collaborators_list[key] for key in added_keys}
                                        removed_collaborators = {key: p_collaborators_list_old[key] for key in removed_keys}

                                        p_message_added_collaborators = ""
                                        p_message_removed_collaborators = ""
                                        p_message_added_collaborators_html = ""
                                        p_message_removed_collaborators_html = ""

                                        if added_collaborators:
                                            p_message_added_collaborators = "Added collaborators:\n\n"
                                            p_message_added_collaborators_html = "<br><b>Added collaborators:</b><br><br>"

                                            for collab_id, collab_name in added_collaborators.items():
                                                added_collab = f'- {collab_name} [ {spotify_convert_uri_to_url(f"spotify:user:{collab_id}")} ]\n'
                                                p_message_added_collaborators += added_collab
                                                p_message_added_collaborators_html += f'- <a href="{escape_html_attr(spotify_convert_uri_to_url(f"spotify:user:{collab_id}"))}">{escape(collab_name)}</a><br>'
                                                try:
                                                    if csv_file_name:
                                                        write_csv_entry(csv_file_name, now_local_naive(), "Added Collaborator", p_name, "", collab_name)
                                                except Exception as e:
                                                    print_operation_error("A CSV event could not be written", e)

                                            p_message_added_collaborators += "\n"
                                            print(p_message_added_collaborators, end="")

                                        if removed_collaborators:
                                            p_message_removed_collaborators = "Removed collaborators:\n\n"
                                            p_message_removed_collaborators_html = "<br><b>Removed collaborators:</b><br><br>"

                                            for collab_id, collab_name in removed_collaborators.items():
                                                removed_collab = f'- {collab_name} [ {spotify_convert_uri_to_url(f"spotify:user:{collab_id}")} ]\n'
                                                p_message_removed_collaborators += removed_collab
                                                p_message_removed_collaborators_html += f'- <a href="{escape_html_attr(spotify_convert_uri_to_url(f"spotify:user:{collab_id}"))}">{escape(collab_name)}</a><br>'
                                                try:
                                                    if csv_file_name:
                                                        write_csv_entry(csv_file_name, now_local_naive(), "Removed Collaborator", p_name, collab_name, "")
                                                except Exception as e:
                                                    print_operation_error("A CSV event could not be written", e)

                                            p_message_removed_collaborators += "\n"
                                            print(p_message_removed_collaborators, end="")

                                    except Exception as e:
                                        print_operation_error(f"Collaborator changes for playlist {spotify_format_playlist_reference(p_uri)} could not be processed and will be retried", e)
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue

                                    m_subject = f"Spotify user {username} number of collaborators for playlist '{p_name}' has changed! ({p_collaborators_diff_str}, {p_collaborators_old} -> {p_collaborators})"
                                    m_body = f"{p_message}\n{p_message_added_collaborators}{p_message_removed_collaborators}Check interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>Playlist '<b><a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a></b>': number of collaborators changed from <b>{p_collaborators_old}</b> to <b>{p_collaborators}</b> (<b>{escape(p_collaborators_diff_str)}</b>)<br>{p_message_added_collaborators_html}{p_message_removed_collaborators_html}<br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
                                    send_notification_channels("profile", m_subject, m_body, m_body_html, email_enabled=PROFILE_NOTIFICATION, image_url=select_notification_image_url(p_image_url, profile_image_url=image_url), email_image_url=p_image_url)
                                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t\t")

                                # Number of tracks changed (skipped on a backend switch to avoid switch-induced diffs)
                                if not source_changed and (p_tracks != p_tracks_old or p_update != p_update_old):
                                    p_after_str = ""
                                    try:

                                        p_tracks_diff = p_tracks - p_tracks_old
                                        p_tracks_diff_str = ""

                                        if p_tracks_diff > 0:
                                            p_tracks_diff_str = "+" + str(p_tracks_diff)
                                        else:
                                            p_tracks_diff_str = str(p_tracks_diff)

                                        if p_tracks != p_tracks_old and not p_update and p_update_old:
                                            p_update = now_local()

                                        if p_update and p_update_old:
                                            if p_update < p_update_old or p_update == p_update_old:
                                                p_update = now_local()

                                        if p_tracks_diff != 0:
                                            if p_update and p_update_old:
                                                p_after_str = f" (after {calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2)}; previous update: {get_short_date_from_ts(p_update_old, True)})"
                                            p_message = f"* Playlist '{p_name}': number of tracks changed from {p_tracks_old} to {p_tracks} ({p_tracks_diff_str}){p_after_str}\n* Playlist URL: {p_url}\n"
                                        else:
                                            if p_update and p_update_old:
                                                p_after_str = f" (after {calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2)}; previous update: {get_short_date_from_ts(p_update_old, True)})"
                                            p_message = f"* Playlist '{p_name}': list of tracks ({p_tracks}) have changed{p_after_str}\n* Playlist URL: {p_url}\n"
                                        print(p_message)
                                    except Exception as e:
                                        print_operation_error(f"Track changes for playlist {spotify_format_playlist_reference(p_uri)} could not be processed and will be retried", e)
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue

                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Playlist Number of Tracks", p_name, p_tracks_old, p_tracks)
                                    except Exception as e:
                                        print_operation_error("A CSV event could not be written", e)

                                    try:

                                        removed_tracks = diff_tracks(p_tracks_list_old, p_tracks_list)
                                        added_tracks = diff_tracks(p_tracks_list, p_tracks_list_old)
                                        album_notification_image_url = next((track.get("album_image_url", "") for track in added_tracks + removed_tracks if track.get("album_image_url")), "")
                                        p_message_added_tracks = ""
                                        p_message_removed_tracks = ""
                                        p_message_added_tracks_html = ""
                                        p_message_removed_tracks_html = ""

                                        if added_tracks:
                                            print("Added tracks:\n")
                                            p_message_added_tracks = "Added tracks:\n\n"
                                            p_message_added_tracks_html = "<br><b>Added tracks:</b><br><br>"

                                            for f_dict in added_tracks:
                                                if "artist" in f_dict and "track" in f_dict:
                                                    apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url = get_apple_genius_search_urls(f_dict["artist"], f_dict["track"])
                                                    tempuri = f'spotify:user:{f_dict["added_by_id"]}'
                                                    music_urls_output = format_music_urls_console(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                                                    lyrics_urls_output = format_lyrics_urls_console(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                                                    music_urls_text = format_music_urls_email_text(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                                                    lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                                                    music_urls_html = format_music_urls_email_html(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, f_dict["artist"], f_dict["track"])
                                                    lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, f_dict["artist"], f_dict["track"])
                                                    added_track_console = f'- {f_dict["artist"]} - {f_dict["track"]} [ {get_date_from_ts(f_dict["added_at"])}, {f_dict["added_by"]} ]\n[ Spotify URL: {spotify_convert_uri_to_url(f_dict["uri"])} ]\n'
                                                    if music_urls_output:
                                                        for line in music_urls_output.split("\n"):
                                                            if line:
                                                                added_track_console += f"[ {line} ]\n"
                                                    if lyrics_urls_output:
                                                        for line in lyrics_urls_output.split("\n"):
                                                            if line:
                                                                added_track_console += f"[ {line} ]\n"
                                                    added_track_console += f'[ Collaborator URL: {spotify_convert_uri_to_url(tempuri)} ]\n\n'
                                                    added_track_email = f'- {f_dict["artist"]} - {f_dict["track"]} [ {get_date_from_ts(f_dict["added_at"])}, {f_dict["added_by"]} ]\n[ Spotify URL: {spotify_convert_uri_to_url(f_dict["uri"])} ]\n'
                                                    if music_urls_text:
                                                        for line in music_urls_text.split("\n"):
                                                            if line:
                                                                added_track_email += f"[ {line} ]\n"
                                                    if lyrics_urls_text:
                                                        for line in lyrics_urls_text.split("\n"):
                                                            if line:
                                                                added_track_email += f"[ {line} ]\n"
                                                    added_track_email += f'[ Collaborator URL: {spotify_convert_uri_to_url(tempuri)} ]\n\n'
                                                    added_track_html = f'- <b><a href="{escape_html_attr(spotify_convert_uri_to_url(f_dict["uri"]))}">{escape(f_dict["artist"])} - {escape(f_dict["track"])}</a></b> [ {escape(get_date_from_ts(f_dict["added_at"]))}, <a href="{escape_html_attr(spotify_convert_uri_to_url(tempuri))}">{escape(f_dict["added_by"])}</a> ]<br>'
                                                    if music_urls_html:
                                                        for line in music_urls_html.split("<br>"):
                                                            if line:
                                                                added_track_html += f"{line}<br>"
                                                    if lyrics_urls_html:
                                                        for line in lyrics_urls_html.split("<br>"):
                                                            if line:
                                                                added_track_html += f"{line}<br>"
                                                    added_track_html += '<br>'
                                                    p_message_added_tracks += added_track_email
                                                    p_message_added_tracks_html += added_track_html
                                                    added_at_dt = f_dict['added_at']
                                                    print(added_track_console, end="")
                                                    try:
                                                        if csv_file_name:
                                                            write_csv_entry(csv_file_name, convert_to_local_naive(added_at_dt), "Added Track", p_name, f_dict['added_by'], f_dict["artist"] + " - " + f_dict["track"])
                                                    except Exception as e:
                                                        print_operation_error("A CSV event could not be written", e)

                                        if removed_tracks:
                                            print("Removed tracks:\n")
                                            p_message_removed_tracks = "Removed tracks:\n\n"
                                            # Add leading <br> only if there were no added tracks
                                            if added_tracks:
                                                p_message_removed_tracks_html = "<b>Removed tracks:</b><br><br>"
                                            else:
                                                p_message_removed_tracks_html = "<br><b>Removed tracks:</b><br><br>"

                                            for f_dict in removed_tracks:
                                                if "artist" in f_dict and "track" in f_dict:
                                                    apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url = get_apple_genius_search_urls(f_dict["artist"], f_dict["track"])
                                                    tempuri = f'spotify:user:{f_dict["added_by_id"]}'
                                                    music_urls_output = format_music_urls_console(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                                                    lyrics_urls_output = format_lyrics_urls_console(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                                                    music_urls_text = format_music_urls_email_text(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                                                    lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                                                    music_urls_html = format_music_urls_email_html(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, f_dict["artist"], f_dict["track"])
                                                    lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, f_dict["artist"], f_dict["track"])
                                                    removed_track_console = f'- {f_dict["artist"]} - {f_dict["track"]} [ {get_date_from_ts(f_dict["added_at"])}, {f_dict["added_by"]} ]\n[ Spotify URL: {spotify_convert_uri_to_url(f_dict["uri"])} ]\n'
                                                    if music_urls_output:
                                                        for line in music_urls_output.split("\n"):
                                                            if line:
                                                                removed_track_console += f"[ {line} ]\n"
                                                    if lyrics_urls_output:
                                                        for line in lyrics_urls_output.split("\n"):
                                                            if line:
                                                                removed_track_console += f"[ {line} ]\n"
                                                    removed_track_console += f'[ Collaborator URL: {spotify_convert_uri_to_url(tempuri)} ]\n\n'
                                                    removed_track_email = f'- {f_dict["artist"]} - {f_dict["track"]} [ {get_date_from_ts(f_dict["added_at"])}, {f_dict["added_by"]} ]\n[ Spotify URL: {spotify_convert_uri_to_url(f_dict["uri"])} ]\n'
                                                    if music_urls_text:
                                                        for line in music_urls_text.split("\n"):
                                                            if line:
                                                                removed_track_email += f"[ {line} ]\n"
                                                    if lyrics_urls_text:
                                                        for line in lyrics_urls_text.split("\n"):
                                                            if line:
                                                                removed_track_email += f"[ {line} ]\n"
                                                    removed_track_email += f'[ Collaborator URL: {spotify_convert_uri_to_url(tempuri)} ]\n\n'
                                                    removed_track_html = f'- <b><a href="{escape_html_attr(spotify_convert_uri_to_url(f_dict["uri"]))}">{escape(f_dict["artist"])} - {escape(f_dict["track"])}</a></b> [ {escape(get_date_from_ts(f_dict["added_at"]))}, <a href="{escape_html_attr(spotify_convert_uri_to_url(tempuri))}">{escape(f_dict["added_by"])}</a> ]<br>'
                                                    if music_urls_html:
                                                        for line in music_urls_html.split("<br>"):
                                                            if line:
                                                                removed_track_html += f"{line}<br>"
                                                    if lyrics_urls_html:
                                                        for line in lyrics_urls_html.split("<br>"):
                                                            if line:
                                                                removed_track_html += f"{line}<br>"
                                                    removed_track_html += '<br>'
                                                    p_message_removed_tracks += removed_track_email
                                                    p_message_removed_tracks_html += removed_track_html
                                                    print(removed_track_console, end="")
                                                    try:
                                                        if csv_file_name:
                                                            write_csv_entry(csv_file_name, now_local_naive(), "Removed Track", p_name, f_dict["artist"] + " - " + f_dict["track"], "")
                                                    except Exception as e:
                                                        print_operation_error("A CSV event could not be written", e)

                                    except Exception as e:
                                        print_operation_error(f"Added or removed tracks for playlist {spotify_format_playlist_reference(p_uri)} could not be processed and will be retried", e)
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue

                                    p_subject_after_str = ""
                                    if p_tracks_diff != 0:
                                        if p_update and p_update_old:
                                            p_subject_after_str = f"; after {calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2)}"
                                        m_subject = f"Spotify user {username} number of tracks for playlist '{p_name}' has changed! ({p_tracks_diff_str}, {p_tracks_old} -> {p_tracks}{p_subject_after_str})"
                                        m_body_html_p_message = f"Playlist '<b><a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a></b>': number of tracks changed from <b>{p_tracks_old}</b> to <b>{p_tracks}</b> (<b>{escape(p_tracks_diff_str)}</b>)"
                                        if p_after_str:
                                            m_body_html_p_message += f" (after <b>{escape(calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2))}</b>; previous update: <b>{escape(get_short_date_from_ts(p_update_old, True))}</b>)"
                                        m_body_html_p_message += "<br>"
                                    else:
                                        if p_update and p_update_old:
                                            p_subject_after_str = f" (after {calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2)})"
                                        m_subject = f"Spotify user {username} list of tracks ({p_tracks}) for playlist '{p_name}' has changed!{p_subject_after_str}"
                                        m_body_html_p_message = f"Playlist '<b><a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a></b>': list of tracks (<b>{p_tracks}</b>) have changed"
                                        if p_after_str:
                                            m_body_html_p_message += f" (after <b>{escape(calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2))}</b>; previous update: <b>{escape(get_short_date_from_ts(p_update_old, True))}</b>)"
                                        m_body_html_p_message += "<br>"
                                    m_body = f"{p_message}\n{p_message_added_tracks}{p_message_removed_tracks}Check interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>{m_body_html_p_message}{p_message_added_tracks_html}{p_message_removed_tracks_html}Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
                                    selected_track_image_url = select_notification_image_url(p_image_url, album_notification_image_url, image_url)
                                    selected_track_email_image_url = select_notification_image_url(p_image_url, album_notification_image_url)
                                    send_notification_channels("profile", m_subject, m_body, m_body_html, email_enabled=PROFILE_NOTIFICATION, image_url=selected_track_image_url, email_image_url=selected_track_email_image_url)
                                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t\t")

                                # Playlist name changed
                                if p_name != p_name_old:
                                    p_message = f"* Playlist '{p_name_old}': name changed to new name '{p_name}'\n* Playlist URL: {p_url}\n"
                                    print(p_message)
                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Playlist Name", username, p_name_old, p_name)
                                    except Exception as e:
                                        print_operation_error("A CSV event could not be written", e)
                                    m_subject = f"Spotify user {username} playlist '{p_name_old}' name changed to '{p_name}'!"
                                    m_body = f"{p_message}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>Playlist '<b>{escape(p_name_old)}</b>': name changed to new name '<b><a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a></b>'<br><br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
                                    send_notification_channels("profile", m_subject, m_body, m_body_html, email_enabled=PROFILE_NOTIFICATION, image_url=select_notification_image_url(p_image_url, profile_image_url=image_url), email_image_url=p_image_url)
                                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t\t")

                                # Playlist description changed
                                if p_descr != p_descr_old:
                                    p_message = f"* Playlist '{p_name}' description changed from:\n\n'{p_descr_old}'\n\nto:\n\n'{p_descr}'\n\n* Playlist URL: {p_url}\n"
                                    print(p_message)
                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Playlist Description", p_name, p_descr_old, p_descr)
                                    except Exception as e:
                                        print_operation_error("A CSV event could not be written", e)
                                    m_subject = f"Spotify user {username} playlist '{p_name}' description has changed !"
                                    m_body = f"{p_message}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>Playlist '<b><a href=\"{escape_html_attr(p_url)}\">{escape(p_name)}</a></b>' description changed from:<br><br>'<i>{escape(p_descr_old)}</i>'<br><br>to:<br><br>'<i>{escape(p_descr)}</i>'<br><br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
                                    send_notification_channels("profile", m_subject, m_body, m_body_html, email_enabled=PROFILE_NOTIFICATION, image_url=select_notification_image_url(p_image_url, profile_image_url=image_url), email_image_url=p_image_url)
                                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t\t")

            # Suppress transient playlist glitches by confirming changes across multiple checks  and keep a stable
            # baseline to avoid baseline poisoning
            global PLAYLISTS_BASELINE_CACHE
            global PLAYLISTS_PENDING_CACHE

            user_playlists_key = f"user:{user_uri_id}"
            stable_entry = PLAYLISTS_BASELINE_CACHE.get(user_playlists_key)
            if stable_entry is None:
                # Initialize baseline from previously persisted playlist snapshot (if available)
                stable_uris = extract_playlist_uris(playlists_old)
                stable_count = playlists_old_count
                # Store both the URI set (for comparison) and the full list (for restoration)
                PLAYLISTS_BASELINE_CACHE[user_playlists_key] = {"uris": stable_uris, "count": stable_count, "playlist_list": list(playlists_old) if playlists_old else []}
                stable_entry = PLAYLISTS_BASELINE_CACHE[user_playlists_key]

            stable_uris = stable_entry.get("uris") or frozenset()
            stable_count = stable_entry.get("count", 0)
            stable_playlist_list = stable_entry.get("playlist_list") or []
            current_uris = extract_playlist_uris(playlists)
            suppress_playlists_notification = False

            if current_uris != stable_uris:
                # Playlists have changed vs stable baseline
                # Skip PLAYLISTS_CHANGE_COUNTER protection when dropping to 0 - let PLAYLISTS_DISAPPEARED_COUNTER handle that case
                dropping_to_zero = len(current_uris) == 0

                if not dropping_to_zero:
                    pending = PLAYLISTS_PENDING_CACHE.get(user_playlists_key)
                    if pending and pending.get("new_uris") == current_uris:
                        pending["streak"] = int(pending.get("streak", 0)) + 1
                    else:
                        pending = {"new_uris": current_uris, "new_count": len(current_uris), "streak": 1, "first_seen_ts": time.time(), "playlist_list": list(playlists) if playlists else []}
                        PLAYLISTS_PENDING_CACHE[user_playlists_key] = pending

                    if PLAYLISTS_CHANGE_COUNTER and int(pending.get("streak", 0)) < int(PLAYLISTS_CHANGE_COUNTER):
                        print(f"* Spotify API: suspected transient playlist change for user '{username}' ({stable_count} -> {len(current_uris)}), streak {pending.get('streak')}/{PLAYLISTS_CHANGE_COUNTER}; will confirm next check\n")
                        print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                        print_cur_ts("Timestamp:\t\t\t")
                        suppress_playlists_notification = True
                    else:
                        # Change confirmed - update variables for notification
                        # Restore playlists_old from the stored dict list, not from URI strings
                        playlists_old = stable_playlist_list
                        playlists_old_count = stable_count
                        playlists_count = len(current_uris)
                        # playlists already contains current dict list, no change needed

                        # Update stable baseline and clear pending
                        PLAYLISTS_BASELINE_CACHE[user_playlists_key] = {
                            "uris": current_uris,
                            "count": playlists_count,
                            "playlist_list": list(playlists) if playlists else []
                        }
                        try:
                            del PLAYLISTS_PENDING_CACHE[user_playlists_key]
                        except Exception:
                            pass
                # else: dropping to 0, let PLAYLISTS_DISAPPEARED_COUNTER handle it below
            else:
                # No change vs stable baseline; clear any pending candidate
                if user_playlists_key in PLAYLISTS_PENDING_CACHE:
                    # If we had a pending change and we're back to stable baseline, this was a transient glitch that resolved - suppress notification
                    suppress_playlists_notification = True
                    # Update the old values to match current stable baseline so the notification condition check fails
                    playlists_old_count = stable_count
                    playlists_old = stable_playlist_list
                    playlists_count = len(current_uris)
                    # playlists already contains current dict list, no change needed
                    print(f"* Spotify API: Playlists for user '{username}' reverted to baseline ({stable_count}) after transient glitch; suppressing notification\n")
                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t\t")
                    try:
                        del PLAYLISTS_PENDING_CACHE[user_playlists_key]
                    except Exception:
                        pass

            if not suppress_playlists_notification and playlist_collection_changed(playlists, playlists_old, playlists_count, playlists_old_count):
                if playlists_count == 0:
                    playlists_zeroed_counter += 1
                    if playlists_zeroed_counter == PLAYLISTS_DISAPPEARED_COUNTER:
                        print(f"* Spotify API: Playlists count dropped from {playlists_old_count} to 0 and has been 0 for {playlists_zeroed_counter} checks; accepting 0 as the new baseline\n")
                        spotify_print_changed_followers_followings_playlists(
                            username, playlists, playlists_old, playlists_count, playlists_old_count, "Playlists", "for", "Added playlists to profile", "Added Playlist", "Removed playlists from profile", "Removed Playlist", playlists_file, csv_file_name, PROFILE_NOTIFICATION, True, sp_accessToken, image_url, True)
                        print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                        print_cur_ts("Timestamp:\t\t\t")
                        playlists_old_count = playlists_count
                        playlists_old = playlists
                        playlists_zeroed_counter = 0
                        # Update baseline after accepting 0 as new baseline
                        PLAYLISTS_BASELINE_CACHE[user_playlists_key] = {"uris": frozenset(), "count": 0, "playlist_list": []}
                    elif playlists_zeroed_counter < PLAYLISTS_DISAPPEARED_COUNTER:
                        print(f"* Spotify API: Playlists count dropped from {playlists_old_count} to 0, streak {playlists_zeroed_counter}/{PLAYLISTS_DISAPPEARED_COUNTER}; old count and list retained\n")
                        print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                        print_cur_ts("Timestamp:\t\t\t")
                else:
                    if playlists_old_count == 0 and playlists_zeroed_counter >= PLAYLISTS_DISAPPEARED_COUNTER:
                        print(f"* Spotify API: Playlists count recovered to {playlists_count}; previously was 0 for {playlists_zeroed_counter} checks (old baseline was {playlists_old_count})\n")

                    spotify_print_changed_followers_followings_playlists(username, playlists, playlists_old, playlists_count, playlists_old_count, "Playlists", "for", "Added playlists to profile", "Added Playlist", "Removed playlists from profile", "Removed Playlist", playlists_file, csv_file_name, PROFILE_NOTIFICATION, True, sp_accessToken, image_url, True)
                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t\t")
                    playlists_old_count = playlists_count
                    playlists_old = playlists
                    playlists_zeroed_counter = 0
                    # Update baseline after confirmed change
                    PLAYLISTS_BASELINE_CACHE[user_playlists_key] = {
                        "uris": extract_playlist_uris(playlists),
                        "count": playlists_count,
                        "playlist_list": list(playlists) if playlists else []
                    }

            elif not suppress_playlists_notification and playlists_count == playlists_old_count:
                if playlists_count == 0:
                    playlists_zeroed_counter = 0
                    playlists_old = playlists
                else:
                    if playlists_zeroed_counter > 0:
                        print(f"* Spotify API: Playlists count recovered to {playlists_count} (matching old baseline) after a streak of {playlists_zeroed_counter} checks\n")
                        print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                        print_cur_ts("Timestamp:\t\t\t")
                    playlists_zeroed_counter = 0
                    playlists_old = playlists

            if error_while_processing:
                debug_print("Playlist processing was partial: advancing successful baselines while retaining failed baselines")
            list_of_playlists_old = merge_playlist_snapshots(list_of_playlists_old, list_of_playlists, playlists_old)

        alive_counter += 1

        if LIVENESS_CHECK_COUNTER and alive_counter >= LIVENESS_CHECK_COUNTER:
            print_cur_ts("Liveness check, timestamp:\t")
            alive_counter = 0

        time.sleep(SPOTIFY_CHECK_INTERVAL)


# Applies validated one-run webhook command-line overrides to runtime settings
def apply_webhook_cli_overrides(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    global WEBHOOK_ENABLED, WEBHOOK_URL, WEBHOOK_PROVIDER, WEBHOOK_PROFILE_NOTIFICATION, WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION, WEBHOOK_ERROR_NOTIFICATION
    if args.webhook_provider is not None:
        WEBHOOK_PROVIDER = str(args.webhook_provider)
    if args.webhook_url is not None:
        if not validate_webhook_url(args.webhook_url):
            parser.error("--webhook-url must contain a complete HTTPS link without embedded credentials")
        WEBHOOK_URL = str(args.webhook_url).strip()
        WEBHOOK_ENABLED = True
    if args.webhook_enabled is not None:
        WEBHOOK_ENABLED = args.webhook_enabled
    if args.webhook_profile is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_PROFILE_NOTIFICATION = True
    if args.webhook_followers_followings is False:
        WEBHOOK_FOLLOWERS_FOLLOWINGS_NOTIFICATION = False
    if args.webhook_errors is not None:
        WEBHOOK_ERROR_NOTIFICATION = args.webhook_errors
        if args.webhook_errors:
            WEBHOOK_ENABLED = True
    if args.webhook_provider is None:
        detected_provider = detect_webhook_provider(WEBHOOK_URL)
        configured_provider = normalized_webhook_provider()
        if detected_provider and detected_provider != configured_provider:
            WEBHOOK_PROVIDER = detected_provider
            print(f"* Warning: Configured webhook provider did not match the URL. Using {detected_provider}.")


CLI_EXPLICIT_FALSE_DESTINATIONS = frozenset({"disable_followers_followings_notification", "error_notification", "webhook_enabled", "webhook_followers_followings", "webhook_errors", "do_not_detect_changed_profile_pic", "do_not_monitor_playlists"})


# Lists command-line arguments that one exclusive action would otherwise ignore
def cli_action_conflicts(args, allowed: Collection[str]) -> List[str]:
    conflicts = []
    for name, value in vars(args).items():
        if name in allowed:
            continue
        explicitly_enabled = value is not None and value is not False
        if name in CLI_EXPLICIT_FALSE_DESTINATIONS and value is False:
            explicitly_enabled = True
        if explicitly_enabled:
            conflicts.append("SPOTIFY_TARGET" if name == "user_id" else "--" + name.replace("_", "-"))
    return conflicts


# Parses configuration and command-line options then runs the selected operation
def main():
    global CLI_CONFIG_PATH, DOTENV_FILE, LOCAL_TIMEZONE, LIVENESS_CHECK_COUNTER, SP_DC_COOKIE, SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET, SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, LOGIN_REQUEST_BODY_FILE, CLIENTTOKEN_REQUEST_BODY_FILE, REFRESH_TOKEN, LOGIN_URL, USER_AGENT, DEVICE_ID, SYSTEM_ID, USER_URI_ID, CSV_FILE, PLAYLISTS_TO_SKIP_FILE, FILE_SUFFIX, DISABLE_LOGGING, DEBUG_MODE, VERBOSE_MODE, SP_LOGFILE, PROFILE_NOTIFICATION, EMAIL_IMAGES, SPOTIFY_CHECK_INTERVAL, SPOTIFY_ERROR_INTERVAL, FOLLOWERS_FOLLOWINGS_NOTIFICATION, ERROR_NOTIFICATION, DETECT_CHANGED_PROFILE_PIC, DETECT_CHANGES_IN_PLAYLISTS, GET_ALL_PLAYLISTS, imgcat_exe, SMTP_PASSWORD, SP_SHA256, stdout_bck, APP_VERSION, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL, TOKEN_SOURCE, ALARM_TIMEOUT, CLEAN_OUTPUT, SP_APP_TOKENS_FILE, SP_USER_TOKENS_FILE, TARGET_USER_URI_ID, TRUNCATE_CHARS, NTFY_IMAGES
    global EXPORT_ALL, PLAYLIST_INFO_CACHE_TTL

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(
        prog="spotify_profile_monitor",
        description=(f"Monitor a Spotify user's profile changes including playlists and send customizable email or webhook alerts [ {PROJECT_URL}/ ]"), formatter_class=argparse.RawTextHelpFormatter,
        epilog=_build_help_epilog()
    )

    # Positional
    parser.add_argument(
        "user_id",
        nargs="?",
        metavar="SPOTIFY_TARGET",
        help="Complete Spotify profile URL, spotify:user URI or user ID",
        type=str
    )

    # Version, just to list in help, it is handled earlier
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s v{VERSION}"
    )

    # Configuration & dotenv files
    conf = parser.add_argument_group("Configuration & dotenv files")
    conf.add_argument(
        "--setup",
        action="store_true",
        help="Run the interactive first-run setup wizard",
    )
    conf.add_argument(
        "--config-file",
        dest="config_file",
        metavar="PATH",
        help="Location of the optional config file",
    )
    conf.add_argument(
        "--generate-config",
        dest="generate_config",
        nargs="?",
        const=True,
        metavar="FILENAME",
        help="Print default config template and exit (on Windows PowerShell, specify a filename to avoid redirect encoding issues)",
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--set-sp-dc",
        dest="set_sp_dc",
        action="store_true",
        help="Privately validate and save SP_DC_COOKIE through a hidden prompt",
    )
    conf.add_argument(
        "--set-webhook-url",
        dest="set_webhook_url",
        action="store_true",
        help="Save a Discord or ntfy webhook URL through a hidden prompt",
    )
    conf.add_argument(
        "--doctor",
        action="store_true",
        help="Run preflight checks with separately approved delivery tests then exit",
    )

    browser_import = parser.add_argument_group("Browser sp_dc import")
    browser_import.add_argument(
        "--import-browser-cookie",
        action="store_true",
        help="Import, validate and save Spotify sp_dc from a supported browser",
    )
    browser_import.add_argument(
        "--browser",
        choices=list(IMPORT_BROWSERS),
        default=None,
        help="Browser source: firefox (default), chrome, brave or chromium",
    )
    browser_import.add_argument(
        "--browser-profile",
        metavar="PROFILE",
        help="Firefox friendly profile name or Chromium profile directory",
    )
    browser_import.add_argument(
        "--cookie-file",
        metavar="PATH",
        help="Advanced explicit browser cookie database override",
    )
    browser_import.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing SP_DC_COOKIE or generated config without a prompt after safe validation and backup",
    )

    # Token source
    parser.add_argument(
        "--token-source",
        dest="token_source",
        choices=["cookie", "client", "oauth_app", "oauth_user"],
        help="Method to obtain Spotify access token: 'cookie', 'client', 'oauth_app' or 'oauth_user'"
    )

    # Auth details used when token source is set to cookie
    cookie_auth = parser.add_argument_group("Auth details for 'cookie' token source")
    cookie_auth.add_argument(
        "-u", "--spotify-dc-cookie",
        dest="spotify_dc_cookie",
        metavar="SP_DC_COOKIE",
        type=str,
        help="Spotify sp_dc cookie"
    )

    # Auth details used when token source is set to client
    client_auth = parser.add_argument_group("Auth details for 'client' token source")
    client_auth.add_argument(
        "-w", "--login-request-body-file",
        dest="login_request_body_file",
        metavar="PROTOBUF_FILENAME",
        help="Read device_id, system_id, user_uri_id and refresh_token from binary Protobuf login file"
    )

    client_auth.add_argument(
        "-z", "--clienttoken-request-body-file",
        dest="clienttoken_request_body_file",
        metavar="PROTOBUF_FILENAME",
        # help="Read app_version, cpu_arch, os_build, platform, os_major, os_minor and client_model from binary Protobuf client token file"
        help=argparse.SUPPRESS
    )

    # Auth details used when token source is set to oauth_app
    oauth_app_auth = parser.add_argument_group("Auth details for 'oauth_app' token source")
    oauth_app_auth.add_argument(
        "-r", "--oauth-app-creds",
        dest="oauth_app_creds",
        metavar='SPOTIFY_APP_CLIENT_ID:SPOTIFY_APP_CLIENT_SECRET',
        help="Spotify OAuth app client credentials - specify both values as SPOTIFY_APP_CLIENT_ID:SPOTIFY_APP_CLIENT_SECRET"
    )

    # Auth details used when token source is set to oauth_user
    oauth_user_auth = parser.add_argument_group("Auth details for 'oauth_user' token source")
    oauth_user_auth.add_argument(
        "-n", "--oauth-user-creds",
        dest="oauth_user_creds",
        metavar='SPOTIFY_USER_CLIENT_ID:SPOTIFY_USER_CLIENT_SECRET',
        help="Spotify OAuth user authorization credentials - specify both values as SPOTIFY_USER_CLIENT_ID:SPOTIFY_USER_CLIENT_SECRET"
    )

    # Notifications
    notify = parser.add_argument_group("Notifications")
    notify.add_argument(
        "-p", "--notify-profile",
        dest="profile_notification",
        action="store_true",
        default=None,
        help="Email when user's profile changes"
    )
    notify.add_argument(
        "-g", "--no-followers-followings-notify",
        dest="disable_followers_followings_notification",
        action="store_false",
        default=None,
        help="Disable notifications about new followers/followings"
    )
    notify.add_argument(
        "-e", "--no-error-notify",
        dest="error_notification",
        action="store_false",
        default=None,
        help="Disable emails on errors"
    )
    notify.add_argument(
        "--send-test-email",
        dest="send_test_email",
        action="store_true",
        help="Send test email to verify SMTP settings"
    )

    webhook_notify = parser.add_argument_group("Webhook notifications")
    webhook_toggle = webhook_notify.add_mutually_exclusive_group()
    webhook_toggle.add_argument(
        "--webhook",
        dest="webhook_enabled",
        action="store_true",
        default=None,
        help="Enable the configured webhook alerts"
    )
    webhook_toggle.add_argument(
        "--no-webhook",
        dest="webhook_enabled",
        action="store_false",
        default=None,
        help="Disable the configured webhook alerts"
    )
    webhook_notify.add_argument(
        "--webhook-url",
        dest="webhook_url",
        metavar="URL",
        type=str,
        help="Use one Discord webhook or ntfy topic URL for this run (may remain in shell history)"
    )
    webhook_notify.add_argument(
        "--webhook-provider",
        dest="webhook_provider",
        choices=("discord", "ntfy"),
        help="Webhook request format for this run (default: configured provider)"
    )
    webhook_notify.add_argument(
        "--webhook-profile",
        dest="webhook_profile",
        action="store_true",
        default=None,
        help="Send webhook alerts when the user's profile changes"
    )
    webhook_notify.add_argument(
        "--no-webhook-followers-followings-notify",
        dest="webhook_followers_followings",
        action="store_false",
        default=None,
        help="Disable webhook alerts about new followers or followings"
    )
    webhook_error_toggle = webhook_notify.add_mutually_exclusive_group()
    webhook_error_toggle.add_argument(
        "--webhook-errors",
        dest="webhook_errors",
        action="store_true",
        default=None,
        help="Send webhook alerts when monitoring has a problem"
    )
    webhook_error_toggle.add_argument(
        "--no-webhook-error-notify",
        dest="webhook_errors",
        action="store_false",
        default=None,
        help="Disable webhook alerts when monitoring has a problem"
    )
    webhook_notify.add_argument(
        "--send-test-webhook",
        dest="send_test_webhook",
        action="store_true",
        help="Send one test webhook without starting monitoring"
    )

    # Intervals & timers
    times = parser.add_argument_group("Intervals & timers")
    times.add_argument(
        "-c", "--check-interval",
        dest="check_interval",
        metavar="SECONDS",
        type=int,
        help="Time between monitoring checks, in seconds"
    )
    times.add_argument(
        "-m", "--error-interval",
        dest="error_interval",
        metavar="SECONDS",
        type=int,
        help="Time between error checks, in seconds"
    )

    # Listing
    listing = parser.add_argument_group("Listing")
    listing.add_argument(
        "-l", "--list-tracks-for-playlist",
        dest="list_tracks_for_playlist",
        metavar="URL",
        type=str,
        help="List all tracks for a Spotify playlist URL"
    )
    listing.add_argument(
        "--export-all-playlists",
        dest="export_all_playlists",
        action="store_true",
        help="Create files per playlist with all tracks for each Spotify playlist (use with -i)"
    )
    listing.add_argument(
        "-x", "--list-liked-tracks",
        dest="list_liked_tracks",
        action="store_true",
        help="List all liked tracks for the user owning the Spotify access token (works only with oauth_user)"
    )
    listing.add_argument(
        "-i", "--show-user-profile",
        dest="user_profile_details",
        action="store_true",
        help="Show profile details for a specific user"
    )
    listing.add_argument(
        "-a", "--list-recently-played-artists",
        dest="recently_played_artists",
        action="store_true",
        help="List recently played artists for a user"
    )
    listing.add_argument(
        "-f", "--list-followers-followings",
        dest="followers_and_followings",
        action="store_true",
        help="List followers & followings for a user"
    )
    listing.add_argument(
        "-s", "--search-username",
        dest="search_username",
        metavar="USERNAME",
        type=str,
        help="Search for Spotify users by name"
    )

    # Features & output
    opts = parser.add_argument_group("Features & output")
    opts.add_argument(
        "-b", "--csv-file",
        dest="csv_file",
        metavar="CSV_FILE",
        type=str,
        help="Write all profile changes to CSV file"
    )
    opts.add_argument(
        "-t", "--playlists-to-skip",
        dest="playlists_to_skip",
        metavar="PLAYLISTS_FILE",
        type=str,
        help="Filename with Spotify playlists to ignore"
    )
    opts.add_argument(
        "-o", "--export-for-spotify-monitor",
        dest="export_for_spotify_monitor",
        action="store_true",
        help="Simplified output for exporting playlists (-l) or liked songs (-x) into 'spotify_monitor'",
    )
    opts.add_argument(
        "-j", "--no-profile-pic-detect",
        dest="do_not_detect_changed_profile_pic",
        action="store_false",
        default=None,
        help="Disable detection of changed profile picture"
    )
    opts.add_argument(
        "-q", "--no-playlist-monitor",
        dest="do_not_monitor_playlists",
        action="store_false",
        default=None,
        help="Disable monitoring of playlist changes"
    )
    opts.add_argument(
        "-k", "--get-all-playlists",
        dest="get_all_playlists",
        action="store_true",
        default=None,
        help="Fetch all playlists instead of only owned ones"
    )
    opts.add_argument(
        "--user-agent",
        dest="user_agent",
        metavar="USER_AGENT",
        type=str,
        help="Specify a custom user agent for Spotify API requests; leave empty to auto-generate it"
    )
    opts.add_argument(
        "-y", "--file-suffix",
        dest="file_suffix",
        metavar="SUFFIX",
        type=str,
        help="File suffix to append to output filenames instead of the normalized Spotify user ID"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        default=None,
        help="Disable logging to spotify_profile_monitor_<user_id/file_suffix>.log"
    )
    opts.add_argument(
        "--debug",
        dest="debug_mode",
        action="store_true",
        default=None,
        help="Enable debug mode for technical logging"
    )
    opts.add_argument(
        "--verbose",
        dest="verbose_mode",
        action="store_true",
        default=None,
        help="Show rare operational events plus the complete startup summary"
    )
    opts.add_argument(
        "--truncate",
        dest="truncate",
        metavar="N",
        type=int,
        help="Max characters per screen line (not log), use 999 to auto-detect terminal width, ignored if -d is set"
    )

    args = parser.parse_args()

    if args.generate_config is not None:
        conflicts = cli_action_conflicts(args, {"generate_config", "force"})
        if conflicts:
            parser.error("--generate-config cannot be combined with " + ", ".join(conflicts))
        config_content = generate_config_with_current_values()
        if args.generate_config is True:
            output_buffer = getattr(sys.stdout, "buffer", None)
            if output_buffer is not None:
                output_buffer.write(config_content.encode("utf-8"))
                output_buffer.flush()
            else:
                sys.stdout.write(config_content)
                sys.stdout.flush()
            sys.exit(0)
        output_file = str(args.generate_config)
        try:
            if not confirm_config_replacement(output_file, force=args.force):
                print("Config replacement cancelled. The existing file was not changed.")
                sys.exit(1)
            write_status = write_config_file(output_file, config_content)
        except Exception as exc:
            print_recovery_error(exc, "file_write", detail=f"Could not write config file '{output_file}': {exc}")
            sys.exit(1)
        print(f"Config written to: {write_status['path']}")
        if write_status["backup_path"]:
            print(f"Backup written to: {write_status['backup_path']}")
        sys.exit(0)

    exclusive_actions = (
        (args.setup, "--setup", {"setup", "user_id", "config_file", "env_file"}),
        (args.import_browser_cookie, "--import-browser-cookie", {"import_browser_cookie", "user_id", "config_file", "env_file", "browser", "browser_profile", "cookie_file", "force"}),
        (args.set_sp_dc, "--set-sp-dc", {"set_sp_dc", "config_file", "env_file"}),
        (args.set_webhook_url, "--set-webhook-url", {"set_webhook_url", "config_file", "env_file"}),
    )
    for enabled, action_name, allowed in exclusive_actions:
        if not enabled:
            continue
        conflicts = cli_action_conflicts(args, allowed)
        if conflicts:
            parser.error(f"{action_name} cannot be combined with " + ", ".join(conflicts))

    if args.debug_mode is not None:
        DEBUG_MODE = args.debug_mode
    if args.verbose_mode is not None:
        VERBOSE_MODE = args.verbose_mode

    if args.setup:
        if args.config_file is not None and args.config_file.casefold() == "none":
            parser.error("--setup requires a config destination and cannot use --config-file none")
        if args.env_file is not None and args.env_file.casefold() == "none":
            parser.error("--setup requires a dotenv destination and cannot use --env-file none")
        prepare_startup_screen(require_input=True)
        print_startup_banner()
        run_setup_wizard(args.user_id, args.config_file, args.env_file)
        sys.exit(0)

    if args.doctor:
        conflicting_actions = []
        for enabled, option in ((args.import_browser_cookie, "--import-browser-cookie"), (args.set_sp_dc, "--set-sp-dc"), (args.set_webhook_url, "--set-webhook-url"), (args.send_test_email, "--send-test-email"), (args.send_test_webhook, "--send-test-webhook"), (args.list_tracks_for_playlist, "--list-tracks-for-playlist"), (args.list_liked_tracks, "--list-liked-tracks"), (args.user_profile_details, "--show-user-profile"), (args.recently_played_artists, "--list-recently-played-artists"), (args.followers_and_followings, "--list-followers-followings"), (args.search_username, "--search-username")):
            if enabled:
                conflicting_actions.append(option)
        if conflicting_actions:
            parser.error("--doctor cannot be combined with " + ", ".join(conflicting_actions))

    if not args.import_browser_cookie:
        import_only_flags = []
        if args.browser is not None:
            import_only_flags.append("--browser")
        if args.browser_profile is not None:
            import_only_flags.append("--browser-profile")
        if args.cookie_file is not None:
            import_only_flags.append("--cookie-file")
        if args.force and not args.generate_config:
            import_only_flags.append("--force")
        if import_only_flags:
            parser.error(f"{', '.join(import_only_flags)} require --import-browser-cookie")

    doctor_startup_checks = []
    config_discovery_disabled = args.config_file is not None and args.config_file.casefold() == "none"
    if config_discovery_disabled:
        CLI_CONFIG_PATH = None
    elif args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = None if config_discovery_disabled else find_config_file(CLI_CONFIG_PATH)

    if not cfg_path and CLI_CONFIG_PATH:
        advice = classify_recovery_error(context="config_missing", detail=f"Configuration file not found: {CLI_CONFIG_PATH}")
        if args.doctor:
            doctor_startup_checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice.fix, advice))
        else:
            print(render_recovery_error(RecoveryError(advice)))
            sys.exit(1)

    if cfg_path:
        config_errors = []
        if not load_config_file(cfg_path, error_out=config_errors, report_errors=not args.doctor):
            if args.doctor:
                doctor_startup_checks.extend(config_errors)
            else:
                sys.exit(1)

    if len(sys.argv) == 1 and not TARGET_USER_URI_ID:
        prepare_startup_screen(require_input=True)
        print_startup_banner()
        _wizard_welcome()
        sys.exit(0 if sys.stdin.isatty() else 1)

    debug_print(f"CLI override: DEBUG_MODE={DEBUG_MODE}")

    if args.import_browser_cookie:
        try:
            run_browser_cookie_import(browser=args.browser or "firefox", browser_profile=args.browser_profile, cookie_file=args.cookie_file, env_file=args.env_file or DOTENV_FILE or None, force=args.force, config_path=args.config_file, target=args.user_id or TARGET_USER_URI_ID)
        except BrowserCookieImportError as exc:
            print_recovery_error(exc, "browser_import")
            sys.exit(1)
        sys.exit(0)

    target_free_mode = any((args.set_sp_dc, args.set_webhook_url, args.doctor, args.send_test_email, args.send_test_webhook, args.list_tracks_for_playlist, args.list_liked_tracks, args.search_username, args.login_request_body_file, args.clienttoken_request_body_file))
    try:
        if args.user_id is not None or not target_free_mode:
            args.user_id = resolve_target_user_id(args.user_id, TARGET_USER_URI_ID)
    except ValueError as exc:
        print_recovery_error(exc, "target_invalid")
        sys.exit(1)

    if not args.user_id and not target_free_mode:
        print_recovery_error(context="target_missing")
        sys.exit(1)

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    env_path = None
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        try:
            from dotenv import load_dotenv, find_dotenv
            from dotenv.parser import parse_stream

            if DOTENV_FILE:
                env_path = DOTENV_FILE
                if not os.path.isfile(env_path):
                    advice = classify_recovery_error(context="config_missing", detail=f"Dotenv file not found: {env_path}")
                    if args.doctor:
                        doctor_startup_checks.append(make_doctor_check("Configuration", "FAIL", "The requested dotenv file was not found", advice.detail, advice.fix, advice))
                    else:
                        print(f"* Warning: dotenv file '{env_path}' does not exist")
                        print(f"Guide: {SECRETS_GUIDE_URL}\n")
                    env_path = None
                else:
                    with open(env_path, "r", encoding="utf-8") as dotenv_file:
                        bindings = list(parse_stream(dotenv_file))
                    malformed = [binding for binding in bindings if binding.error]
                    if malformed:
                        raise ValueError(f"Dotenv syntax error near line {malformed[0].original.line}")
                    load_dotenv(env_path, override=True, interpolate=False)
                    debug_print(f"Loaded dotenv file: {env_path}")
            else:
                env_path = find_dotenv() or None
                if env_path:
                    with open(env_path, "r", encoding="utf-8") as dotenv_file:
                        bindings = list(parse_stream(dotenv_file))
                    malformed = [binding for binding in bindings if binding.error]
                    if malformed:
                        raise ValueError(f"Dotenv syntax error near line {malformed[0].original.line}")
                    load_dotenv(env_path, override=True, interpolate=False)
                    debug_print(f"Auto-discovered and loaded dotenv file: {env_path}")
        except ImportError as exc:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            advice = classify_recovery_error(exc, "dependency", "python-dotenv is required to load dotenv files")
            if args.doctor:
                doctor_startup_checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice.fix, advice))
            elif env_path:
                print(render_recovery_error(RecoveryError(advice)))
        except (OSError, UnicodeError, ValueError) as exc:
            advice = classify_recovery_error(exc, "config_invalid", f"Dotenv file '{env_path}' could not be loaded: {exc}")
            if args.doctor:
                doctor_startup_checks.append(make_doctor_check("Configuration", "FAIL", "The dotenv file could not be loaded", advice.detail, advice.fix, advice))
            else:
                print(render_recovery_error(RecoveryError(advice)))
                sys.exit(1)

    if env_path:
        for secret in SECRET_KEYS:
            val = os.getenv(secret)
            if val is not None:
                globals()[secret] = val

    if args.set_sp_dc:
        try:
            run_set_sp_dc(env_file=DOTENV_FILE or None, config_path=cfg_path or CLI_CONFIG_PATH)
        except SpDcConfigurationError as exc:
            print_recovery_error(exc, "set_sp_dc")
            sys.exit(1)
        sys.exit(0)

    if args.set_webhook_url:
        try:
            run_set_webhook_url(env_file=DOTENV_FILE or None, config_path=cfg_path)
        except WebhookConfigurationError as exc:
            print_recovery_error(exc, "set_webhook_url")
            sys.exit(1)
        sys.exit(0)

    apply_webhook_cli_overrides(args, parser)

    if args.token_source:
        TOKEN_SOURCE = args.token_source
    if not TOKEN_SOURCE:
        TOKEN_SOURCE = "cookie"
    if args.spotify_dc_cookie:
        SP_DC_COOKIE = args.spotify_dc_cookie
    if args.oauth_app_creds:
        try:
            SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET = args.oauth_app_creds.split(":", 1)
        except ValueError as exc:
            print_recovery_error(exc, "config_invalid", detail="--oauth-app-creds must use SP_APP_CLIENT_ID:SP_APP_CLIENT_SECRET")
            sys.exit(1)
    if args.oauth_user_creds:
        try:
            SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET = args.oauth_user_creds.split(":", 1)
        except ValueError as exc:
            print_recovery_error(exc, "config_invalid", detail="--oauth-user-creds must use SPOTIFY_USER_CLIENT_ID:SPOTIFY_USER_CLIENT_SECRET")
            sys.exit(1)
    if args.login_request_body_file:
        LOGIN_REQUEST_BODY_FILE = os.path.expanduser(args.login_request_body_file)
    elif LOGIN_REQUEST_BODY_FILE:
        LOGIN_REQUEST_BODY_FILE = os.path.expanduser(LOGIN_REQUEST_BODY_FILE)
    if args.clienttoken_request_body_file:
        CLIENTTOKEN_REQUEST_BODY_FILE = os.path.expanduser(args.clienttoken_request_body_file)
    elif CLIENTTOKEN_REQUEST_BODY_FILE:
        CLIENTTOKEN_REQUEST_BODY_FILE = os.path.expanduser(CLIENTTOKEN_REQUEST_BODY_FILE)
    if args.check_interval is not None:
        SPOTIFY_CHECK_INTERVAL = args.check_interval
    if args.error_interval is not None:
        SPOTIFY_ERROR_INTERVAL = args.error_interval

    # Recompute interval-derived values after config file and CLI resolution so a config-file
    # SPOTIFY_CHECK_INTERVAL is honored, not only a --check-interval override
    if SPOTIFY_CHECK_INTERVAL > 0:
        LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / SPOTIFY_CHECK_INTERVAL
    PLAYLIST_INFO_CACHE_TTL = (SPOTIFY_CHECK_INTERVAL * 2 if SPOTIFY_CHECK_INTERVAL > 43200 else 43200)
    if args.profile_notification is True:
        PROFILE_NOTIFICATION = True
    if args.disable_followers_followings_notification is False:
        FOLLOWERS_FOLLOWINGS_NOTIFICATION = False
    if args.error_notification is False:
        ERROR_NOTIFICATION = False
    if args.user_agent:
        USER_AGENT = args.user_agent
        debug_print("Using USER_AGENT from CLI argument")
    if not USER_AGENT:
        USER_AGENT = get_random_spotify_user_agent() if TOKEN_SOURCE == "client" else get_random_user_agent()
        debug_print(f"Generated USER_AGENT for source={TOKEN_SOURCE}")
    debug_print(f"Effective TOKEN_SOURCE={TOKEN_SOURCE}")

    if args.file_suffix:
        FILE_SUFFIX = str(args.file_suffix)

    if args.doctor:
        doctor_target = args.user_id if args.user_id is not None else TARGET_USER_URI_ID
        doctor_exit = run_doctor(doctor_target, cfg_path or CLI_CONFIG_PATH, env_path, doctor_startup_checks)
        if doctor_exit == 0:
            command_config = "none" if config_discovery_disabled else cfg_path or CLI_CONFIG_PATH
            command_env = "none" if args.env_file and args.env_file.casefold() == "none" else env_path
            _wizard_print_monitor_after_doctor(command_config, command_env, args.user_id, target_is_saved=args.user_id is None and bool(TARGET_USER_URI_ID))
        sys.exit(doctor_exit)

    if (EMAIL_IMAGES or NTFY_IMAGES) and not NOTIFICATION_IMAGES_AVAILABLE:
        print("* Warning: Pillow is not installed, so email and ntfy artwork attachments are disabled for this run")
        EMAIL_IMAGES = False
        NTFY_IMAGES = False

    if args.send_test_webhook:
        prepare_startup_screen()
        print("* Sending a test webhook ...\n")
        if send_webhook("Spotify Profile Monitor test", "Your webhook alerts are set up correctly.", "profile", force=True) == 0:
            print("* Test webhook sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if args.export_for_spotify_monitor:
        if not args.list_tracks_for_playlist and not args.list_liked_tracks:
            print(f"* Error: The 'export for spotify monitor' feature is only supported with -l and -x command line options !")
            sys.exit(2)
        else:
            CLEAN_OUTPUT = True

    if not CLEAN_OUTPUT:
        stdout_bck = sys.stdout

        prepare_startup_screen()

        print_startup_banner()

    local_tz = None
    if LOCAL_TIMEZONE == "Auto":
        if get_localzone is not None:
            try:
                local_tz = get_localzone()
            except Exception:
                pass
        if local_tz:
            LOCAL_TIMEZONE = str(local_tz)
        else:
            install_command = _wizard_render_command([sys.executable or ("python" if platform.system() == "Windows" else "python3"), "-m", "pip", "install", "tzlocal"])
            advice = make_recovery_advice("dependency.missing", "The local timezone could not be detected", recovery_fix_with_guide(f"Install tzlocal through the active Python environment with '{install_command}' or set LOCAL_TIMEZONE manually", CONFIG_GUIDE_URL), False)
            print(render_recovery_error(RecoveryError(advice)))
            sys.exit(1)
    else:
        if not is_valid_timezone(LOCAL_TIMEZONE):
            print_recovery_error(ValueError(f"Invalid LOCAL_TIMEZONE: {LOCAL_TIMEZONE}"), "config_invalid")
            sys.exit(1)

    # Honor a config file or dotenv VERIFY_SSL by suppressing insecure-request warnings before any request
    # (the import-time guard only sees the built-in default)
    if not VERIFY_SSL:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if not check_internet():
        sys.exit(1)

    if args.send_test_email:
        print("* Sending test email notification ...\n")
        if send_email("spotify_profile_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if args.do_not_detect_changed_profile_pic is False:
        DETECT_CHANGED_PROFILE_PIC = False

    if args.do_not_monitor_playlists is False:
        DETECT_CHANGES_IN_PLAYLISTS = False

    if args.get_all_playlists is True:
        GET_ALL_PLAYLISTS = True

    if TOKEN_SOURCE == "client":
        login_request_body_file_param = False
        if args.login_request_body_file:
            LOGIN_REQUEST_BODY_FILE = os.path.expanduser(args.login_request_body_file)
            login_request_body_file_param = True
        else:
            if LOGIN_REQUEST_BODY_FILE:
                LOGIN_REQUEST_BODY_FILE = os.path.expanduser(LOGIN_REQUEST_BODY_FILE)

        if LOGIN_REQUEST_BODY_FILE:
            if os.path.isfile(LOGIN_REQUEST_BODY_FILE):
                try:
                    DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN = parse_login_request_body_file(LOGIN_REQUEST_BODY_FILE)
                except Exception as e:
                    print_operation_error(f"Protobuf file '{LOGIN_REQUEST_BODY_FILE}' could not be processed", e)
                    sys.exit(1)
                else:
                    if not args.user_id and not args.list_tracks_for_playlist and not args.search_username and not args.user_profile_details and not args.recently_played_artists and not args.followers_and_followings and not args.list_liked_tracks and login_request_body_file_param:
                        print(f"* Login data correctly read from Protobuf file ({LOGIN_REQUEST_BODY_FILE}):")
                        print(" - Device ID:\t\t", DEVICE_ID)
                        print(" - System ID:\t\t", SYSTEM_ID)
                        print(" - Spotify user ID:\t", USER_URI_ID)
                        print(" - Refresh Token:\t", REFRESH_TOKEN, "\n")
                        sys.exit(0)
            else:
                print(f"* Error: Protobuf file ({LOGIN_REQUEST_BODY_FILE}) does not exist")
                sys.exit(1)

        vals = {
            "LOGIN_URL": LOGIN_URL,
            "USER_AGENT": USER_AGENT,
            "DEVICE_ID": DEVICE_ID,
            "SYSTEM_ID": SYSTEM_ID,
            "USER_URI_ID": USER_URI_ID,
            "REFRESH_TOKEN": REFRESH_TOKEN,
        }
        placeholders = {
            "DEVICE_ID": "your_spotify_app_device_id",
            "SYSTEM_ID": "your_spotify_app_system_id",
            "USER_URI_ID": "your_spotify_user_uri_id",
            "REFRESH_TOKEN": "your_spotify_app_refresh_token",
        }

        bad = [
            f"{k} {'missing' if not v else 'is placeholder'}"
            for k, v in vals.items()
            if not v or placeholders.get(k) == v
        ]
        if bad:
            print("* Error:", "; ".join(bad))
            sys.exit(1)

        clienttoken_request_body_file_param = False
        if args.clienttoken_request_body_file:
            CLIENTTOKEN_REQUEST_BODY_FILE = os.path.expanduser(args.clienttoken_request_body_file)
            clienttoken_request_body_file_param = True
        else:
            if CLIENTTOKEN_REQUEST_BODY_FILE:
                CLIENTTOKEN_REQUEST_BODY_FILE = os.path.expanduser(CLIENTTOKEN_REQUEST_BODY_FILE)

        if CLIENTTOKEN_REQUEST_BODY_FILE:
            if os.path.isfile(CLIENTTOKEN_REQUEST_BODY_FILE):
                try:

                    (APP_VERSION, _, _, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL) = parse_clienttoken_request_body_file(CLIENTTOKEN_REQUEST_BODY_FILE)
                except Exception as e:
                    print_operation_error(f"Protobuf file '{CLIENTTOKEN_REQUEST_BODY_FILE}' could not be processed", e)
                    sys.exit(1)
                else:
                    if not args.user_id and not args.list_tracks_for_playlist and not args.search_username and not args.user_profile_details and not args.recently_played_artists and not args.followers_and_followings and not args.list_liked_tracks and clienttoken_request_body_file_param:
                        print(f"* Client token data correctly read from Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}):")
                        print(" - App version:\t\t", APP_VERSION)
                        print(" - CPU arch:\t\t", CPU_ARCH)
                        print(" - OS build:\t\t", OS_BUILD)
                        print(" - Platform:\t\t", PLATFORM)
                        print(" - OS major:\t\t", OS_MAJOR)
                        print(" - OS minor:\t\t", OS_MINOR)
                        print(" - Client model:\t", CLIENT_MODEL)
                        sys.exit(0)
            else:
                print(f"* Error: Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}) does not exist")
                sys.exit(1)

        app_version_default = "1.2.62.580.g7e3d9a4f"
        if USER_AGENT and not APP_VERSION:
            try:
                APP_VERSION = ua_to_app_version(USER_AGENT)
            except Exception as e:
                print("* Warning: USER_AGENT is invalid for APP_VERSION. Using the built-in default.")
                debug_print(f"USER_AGENT validation failed: {sanitize_error_text(e)}")
                APP_VERSION = app_version_default
        else:
            APP_VERSION = app_version_default

    elif TOKEN_SOURCE == "oauth_app":
        if any([
            not SP_APP_CLIENT_ID,
            SP_APP_CLIENT_ID == "your_spotify_app_client_id",
            not SP_APP_CLIENT_SECRET,
            SP_APP_CLIENT_SECRET == "your_spotify_app_client_secret",
        ]):
            print("* Error: SP_APP_CLIENT_ID or SP_APP_CLIENT_SECRET (-r / --oauth-app-creds) value is empty or incorrect")
            sys.exit(1)

    elif TOKEN_SOURCE == "oauth_user":
        if args.oauth_user_creds:
            try:
                SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET = args.oauth_user_creds.split(":")
            except ValueError:
                print("* Error: -n / --oauth-user-creds has invalid format - use SP_USER_CLIENT_ID:SP_USER_CLIENT_SECRET")
                sys.exit(1)

        if any([
            not SP_USER_CLIENT_ID,
            SP_USER_CLIENT_ID == "your_spotify_user_client_id",
            SP_USER_CLIENT_SECRET == "your_spotify_user_client_secret",
        ]):
            print("* Error: SP_USER_CLIENT_ID or SP_USER_CLIENT_SECRET (-n / --oauth-user-creds) value is empty or incorrect")
            sys.exit(1)
    else:
        if args.spotify_dc_cookie:
            SP_DC_COOKIE = args.spotify_dc_cookie

        if not SP_DC_COOKIE or SP_DC_COOKIE == "your_sp_dc_cookie_value":
            print("* Error: SP_DC_COOKIE (-u / --spotify_dc_cookie) value is empty or incorrect")
            sys.exit(1)

    if IMGCAT_PATH:
        try:
            imgcat_exe = resolve_executable(IMGCAT_PATH)
        except Exception:
            pass

    if SP_APP_TOKENS_FILE:
        SP_APP_TOKENS_FILE = os.path.expanduser(SP_APP_TOKENS_FILE)

    if SP_USER_TOKENS_FILE:
        SP_USER_TOKENS_FILE = os.path.expanduser(SP_USER_TOKENS_FILE)

    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    else:
        if CSV_FILE:
            CSV_FILE = os.path.expanduser(CSV_FILE)

    if CSV_FILE:
        try:
            with open(CSV_FILE, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            print_operation_error("The CSV file cannot be opened for writing", e)
            sys.exit(1)

    if args.export_all_playlists:
        if not args.user_profile_details:
            print("Error: --export-all-playlists requires -i / --show-user-profile flag !")
            sys.exit(1)
        try:
            import pathvalidate
        except ModuleNotFoundError:
            install_command = _wizard_render_command([sys.executable or ("python" if platform.system() == "Windows" else "python3"), "-m", "pip", "install", "pathvalidate"])
            raise SystemExit(f"Error: Couldn't find the pathvalidate library required for --export-all-playlists !\n\nTo install it through the active Python environment, run:\n    {install_command}\n\nOnce installed, re-run this tool")
        EXPORT_ALL = True

    if args.list_tracks_for_playlist:
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            elif TOKEN_SOURCE == "oauth_app":
                sp_accessToken = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
            elif TOKEN_SOURCE == "oauth_user":
                sp_accessToken = spotify_get_access_token_from_oauth_user(SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, SP_USER_REDIRECT_URI, SP_USER_SCOPE, init=True)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
            spotify_list_tracks_for_playlist(sp_accessToken, args.list_tracks_for_playlist, CSV_FILE, CSV_FILE_FORMAT_EXPORT)
        except Exception as e:
            if str(e) == PLAYLIST_INPUT_ERROR:
                print_operation_error(PLAYLIST_INPUT_ERROR, e)
            elif 'Not Found' in str(e) or '400 Client' in str(e):
                print_operation_error("The playlist does not exist or is private", e)
            else:
                print_recovery_error(e, "metadata")
            sys.exit(1)
        sys.exit(0)

    if args.list_liked_tracks:
        if TOKEN_SOURCE not in {"oauth_user"}:
            print(f"* Error: List of liked tracks is not supported with the '{TOKEN_SOURCE}' method ! Use the 'oauth_user' token source instead !")
            sys.exit(2)
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            elif TOKEN_SOURCE == "oauth_app":
                sp_accessToken = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
            elif TOKEN_SOURCE == "oauth_user":
                sp_accessToken = spotify_get_access_token_from_oauth_user(SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, SP_USER_REDIRECT_URI, SP_USER_SCOPE, init=True)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
            spotify_list_liked_tracks(sp_accessToken, CSV_FILE, CSV_FILE_FORMAT_EXPORT)
        except Exception as e:
            if 'Not Found' in str(e) or '400 Client' in str(e):
                print_operation_error("The playlist does not exist or is private", e)
            else:
                print_recovery_error(e, "metadata")
            sys.exit(1)
        sys.exit(0)

    if args.search_username:
        if TOKEN_SOURCE not in ("cookie", "client"):
            print(f"* Error: Search feature is not supported with the '{TOKEN_SOURCE}' method ! Use a different token source !")
            sys.exit(2)
        if not SP_SHA256 or SP_SHA256 == "your_spotify_client_sha256":
            print("* Error: Wrong SP_SHA256 value !")
            sys.exit(1)
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            elif TOKEN_SOURCE == "oauth_app":
                sp_accessToken = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
            elif TOKEN_SOURCE == "oauth_user":
                sp_accessToken = spotify_get_access_token_from_oauth_user(SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, SP_USER_REDIRECT_URI, SP_USER_SCOPE, init=True)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
            spotify_search_users(sp_accessToken, args.search_username)
        except Exception as e:
            print_recovery_error(e, f"{TOKEN_SOURCE}_auth")
            sys.exit(1)
        sys.exit(0)

    if not args.user_id:
        print_recovery_error(context="target_missing")
        sys.exit(1)

    if args.user_profile_details:
        sp_accessToken = ""
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            elif TOKEN_SOURCE == "oauth_app":
                sp_accessToken = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
            elif TOKEN_SOURCE == "oauth_user":
                sp_accessToken = spotify_get_access_token_from_oauth_user(SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, SP_USER_REDIRECT_URI, SP_USER_SCOPE, init=True)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
            spotify_get_user_details(sp_accessToken, args.user_id)
        except Exception as e:
            err = str(e).lower()
            if 'not found' in err or '404' in err:
                if is_user_removed(sp_accessToken, args.user_id):
                    print(f"* Error: User '{args.user_id}' does not exist!")
                else:
                    print_recovery_error(e, "target_not_found", target_user_id=args.user_id)
            else:
                print_recovery_error(e, f"{TOKEN_SOURCE}_auth")
            sys.exit(1)
        sys.exit(0)

    if args.recently_played_artists:
        if TOKEN_SOURCE not in ("cookie", "client", "oauth_user"):
            print(f"* Error: List of recently played artists is not supported with the '{TOKEN_SOURCE}' method ! Use a different token source !")
            sys.exit(2)
        sp_accessToken = ""
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            elif TOKEN_SOURCE == "oauth_app":
                sp_accessToken = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
            elif TOKEN_SOURCE == "oauth_user":
                sp_accessToken = spotify_get_access_token_from_oauth_user(SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, SP_USER_REDIRECT_URI, SP_USER_SCOPE, init=True)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
            if TOKEN_SOURCE != "oauth_user" or (TOKEN_SOURCE == "oauth_user" and is_token_owner(sp_accessToken, args.user_id)):
                spotify_get_recently_played_artists(sp_accessToken, args.user_id)
            else:
                print(f"* Error: List of recently played artists is only available for the token owner with the '{TOKEN_SOURCE}' method !")
                sys.exit(3)

        except Exception as e:
            err = str(e).lower()
            if 'not found' in err or '404' in err:
                if is_user_removed(sp_accessToken, args.user_id):
                    print(f"* Error: User '{args.user_id}' does not exist!")
                else:
                    print_recovery_error(e, "target_not_found", target_user_id=args.user_id)
            else:
                print_recovery_error(e, f"{TOKEN_SOURCE}_auth")
            sys.exit(1)
        sys.exit(0)

    if args.followers_and_followings:
        sp_accessToken = ""
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            elif TOKEN_SOURCE == "oauth_app":
                sp_accessToken = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
            elif TOKEN_SOURCE == "oauth_user":
                sp_accessToken = spotify_get_access_token_from_oauth_user(SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, SP_USER_REDIRECT_URI, SP_USER_SCOPE, init=True)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
            spotify_get_followers_and_followings(sp_accessToken, args.user_id)
        except Exception as e:
            err = str(e).lower()
            if 'not found' in err or '404' in err:
                if is_user_removed(sp_accessToken, args.user_id):
                    print(f"* Error: User '{args.user_id}' does not exist!")
                else:
                    print_recovery_error(e, "target_not_found", target_user_id=args.user_id)
            else:
                print_recovery_error(e, f"{TOKEN_SOURCE}_auth")
            sys.exit(1)
        sys.exit(0)

    if args.playlists_to_skip:
        PLAYLISTS_TO_SKIP_FILE = os.path.expanduser(args.playlists_to_skip)
    else:
        if PLAYLISTS_TO_SKIP_FILE:
            PLAYLISTS_TO_SKIP_FILE = os.path.expanduser(PLAYLISTS_TO_SKIP_FILE)

    if PLAYLISTS_TO_SKIP_FILE:
        try:
            with open(PLAYLISTS_TO_SKIP_FILE, encoding="utf-8") as file:
                playlists_to_skip = {
                    spotify_extract_id_or_name(line)
                    for line in file
                    if line.strip() and not line.strip().startswith("#")
                }
            file.close()
        except Exception as e:
            print_operation_error("The ignored-playlist file cannot be opened", e)
            sys.exit(1)
    else:
        playlists_to_skip = []

    if not FILE_SUFFIX:
        FILE_SUFFIX = str(args.user_id)

    if args.truncate:
        if args.truncate != 999:
            TRUNCATE_CHARS = args.truncate
        else:
            try:
                terminal_size = shutil.get_terminal_size()
                print(f"The detected terminal screen width is: {terminal_size.columns} characters\n")
                TRUNCATE_CHARS = terminal_size.columns
            except Exception as e:
                print_operation_error("Terminal width could not be detected", e)
                sys.exit(1)

    try:
        ascii_log_separators_enabled()
    except ValueError as e:
        print_recovery_error(e, "config_invalid")
        sys.exit(1)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    if not DISABLE_LOGGING:
        log_path = build_log_path(SP_LOGFILE, FILE_SUFFIX)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        FINAL_LOG_PATH = str(log_path)
        sys.stdout = Logger(FINAL_LOG_PATH)
    else:
        FINAL_LOG_PATH = None
        sys.stdout = TerminalStream(sys.stdout)

    if args.profile_notification is True:
        PROFILE_NOTIFICATION = True

    if args.disable_followers_followings_notification is False:
        FOLLOWERS_FOLLOWINGS_NOTIFICATION = False

    if args.error_notification is False:
        ERROR_NOTIFICATION = False

    if PROFILE_NOTIFICATION is False:
        FOLLOWERS_FOLLOWINGS_NOTIFICATION = False

    if SMTP_HOST.startswith("your_smtp_server_"):
        PROFILE_NOTIFICATION = False
        FOLLOWERS_FOLLOWINGS_NOTIFICATION = False
        ERROR_NOTIFICATION = False

    startup_rows = build_startup_summary(args.user_id, cfg_path, env_path, FINAL_LOG_PATH)
    emit_startup_summary(startup_rows, show_full=bool(VERBOSE_MODE or DEBUG_MODE))

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_profile_changes_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_check_signal_handler)
        signal.signal(signal.SIGHUP, reload_secrets_signal_handler)

    spotify_profile_monitor_uri(args.user_id, CSV_FILE, playlists_to_skip)

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()

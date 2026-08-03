#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v3.6.1

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

VERSION = "3.6.1"

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

# Spotify user to monitor by raw ID, Spotify user URI or Spotify profile URL
# A positional command-line target overrides this value
TARGET_USER_URI_ID = ""

# ---------------------------------------------------------------------

# The section below is used when the token source is set to 'cookie'
# (to configure the alternative 'oauth_app', 'oauth_user' or 'client' methods, see the section at the end of this config block)
#
# - Log in to Spotify Web Player and follow the manual cookie extraction guide:
#   https://github.com/misiektoja/spotify_profile_monitor#manual-cookie-extraction
# - Provide the SP_DC_COOKIE secret using one of the following methods:
#   - Recommended and most secure for manual entry: run --set-sp-dc to use a hidden prompt, validate the cookie and save it to ".env"
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
WEBHOOK_USERNAME = "Spotify Profile Monitor"

# Discord avatar URL (leave empty to use the webhook default)
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
# Replace {playlist_id1} and {playlist_id2} with the playlists URI IDs you want to monitor and {user_id} with the owner's URI ID
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
DOTENV_FILE = ""

# Suffix to append to the output filenames instead of default user URI ID
# Can also be set using the -y flag
FILE_SUFFIX = ""

# Base name for the log file. Output will be saved to spotify_profile_monitor_<user_uri_id/file_suffix>.log
# Can include a directory path to specify the location, e.g. ~/some_dir/spotify_profile_monitor
SP_LOGFILE = "spotify_profile_monitor"

# Whether to disable logging to spotify_profile_monitor_<user_uri_id/file_suffix>.log
# Can also be disabled via the -d flag
DISABLE_LOGGING = False

# Enable debug mode for technical logging (can also be enabled via --debug flag)
# Shows request flow, selected params and internal state changes (with sensitive values redacted)
DEBUG_MODE = False

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
# - Run spotify_profile_monitor with the -w flag without specifying SPOTIFY_USER_URI_ID - it will decode the file and
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
# - run spotify_profile_monitor with the hidden -z flag without specifying SPOTIFY_USER_URI_ID - it will decode the file
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
DEBUG_MODE = False
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

# Error text shared by all rejected Spotify target forms
TARGET_INPUT_ERROR = "Invalid Spotify target. Use a raw user ID, spotify:user:USER_ID or https://open.spotify.com/user/USER_ID."

# List of secret keys to load from env/config
SECRET_KEYS = ("SP_DC_COOKIE", "SP_APP_CLIENT_ID", "SP_APP_CLIENT_SECRET", "SP_USER_CLIENT_ID", "SP_USER_CLIENT_SECRET", "REFRESH_TOKEN", "SP_SHA256", "SMTP_PASSWORD", "WEBHOOK_URL", "NTFY_ACCESS_TOKEN")

# Strings removed from track names for generating proper Genius search URLs
re_search_str = r'remaster|extended|original mix|remix|original soundtrack|radio( |-)edit|\(feat\.|( \(.*version\))|( - .*version)'
re_replace_str = r'( - (\d*)( )*remaster$)|( - (\d*)( )*remastered( version)*( \d*)*.*$)|( \((\d*)( )*remaster\)$)|( - (\d+) - remaster$)|( - extended$)|( - extended mix$)|( - (.*); extended mix$)|( - extended version$)|( - (.*) remix$)|( - remix$)|( - remixed by .*$)|( - original mix$)|( - .*original soundtrack$)|( - .*radio( |-)edit$)|( \(feat\. .*\)$)|( \(\d+.*Remaster.*\)$)|( \(.*Version\))|( - .*version)'

# Default value for network-related timeouts in functions; in seconds
FUNCTION_TIMEOUT = 15

# Default value for alarm signal handler timeout; in seconds
ALARM_TIMEOUT = 15
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
TOKEN_URL = "https://open.spotify.com/api/token"

# URLs and page size used by the public web-player playlist backend
WEB_PLAYER_URL = "https://open.spotify.com/"
WEB_PLAYER_QUERY_URL = "https://api-partner.spotify.com/pathfinder/v2/query"
WEB_PLAYLIST_PAGE_LIMIT = 100
WEB_PLAYER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

# URL of the endpoint to get server time needed to create TOTP object
SERVER_TIME_URL = "https://open.spotify.com/"

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


import sys

if sys.version_info < (3, 6):
    print("* Error: Python version 3.6 or higher required !")
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
import csv
import getpass
try:
    import pytz
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the pytz library !\n\nTo install it, run:\n    pip install pytz\n\nOnce installed, re-run this tool")
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
import subprocess
import base64
import random
import shlex
import tempfile
from collections import Counter
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path
import secrets
from typing import Any, Callable, List, Optional, Sequence, Tuple, Type, cast
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
NOTIFICATION_IMAGE_ALLOWED_HOST_SUFFIXES = ("scdn.co", "spotifycdn.com")
EMAIL_ARTWORK_CONTENT_ID = "spotify_artwork"
EMAIL_ARTWORK_MAX_DIMENSIONS = (320, 320)

PILImage: Any = None
try:
    from PIL import Image as PILImageModule
    PILImage = PILImageModule
except ImportError:
    pass
NOTIFICATION_IMAGES_AVAILABLE = PILImage is not None


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
SESSION.mount("https://api-partner.spotify.com", web_player_adapter)


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


# Converts Unicode-only horizontal separator lines to ASCII for portable log display
def normalize_log_separators(message):
    return re.sub(r"(?m)^─+$", lambda match: match.group(0).replace("─", "-"), message)


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        # Expand tabs for file output (stdout remains untouched)
        self.logfile.write(normalize_log_separators(message.expandtabs(8)))
        if (TRUNCATE_CHARS):
            message = truncate_string_per_line(message, TRUNCATE_CHARS)
        self.terminal.write(message)
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
        pass


# Class used to generate timeout exceptions
class TimeoutException(Exception):
    pass


# Class used for custom PlaylistRestrictedError exception
class PlaylistRestrictedError(Exception):
    pass


# Signal handler for SIGALRM when the operation times out
def timeout_handler(sig, frame):
    raise TimeoutException


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)


# Checks internet connectivity
def check_internet(url=CHECK_INTERNET_URL, timeout=CHECK_INTERNET_TIMEOUT, verify=VERIFY_SSL):
    try:
        debug_print(f"HTTP GET {url} [connectivity check], timeout={timeout}, verify_ssl={verify}")
        _ = req.get(url, headers={'User-Agent': USER_AGENT}, timeout=timeout, verify=verify)
        debug_print(f"HTTP GET {url} -> OK")
        return True
    except req.RequestException as e:
        debug_print(f"HTTP GET {url} -> failed: {e}")
        print(f"* No connectivity, please check your network:\n\n{e}")
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


# Debug print helper - only prints when DEBUG_MODE is enabled
def debug_print(message):
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[DEBUG {timestamp}] {message}")


def mask_secret(value, prefix=4, suffix=2):
    if value is None:
        return None
    s = str(value)
    if not s:
        return ""
    if len(s) <= (prefix + suffix):
        return "*" * len(s)
    return f"{s[:prefix]}...{s[-suffix:]}"


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
        print(f"Error sending email: {e}")
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


# Returns whether one image URL is a complete HTTPS URL on a Spotify CDN host
def spotify_image_url_is_allowed(image_url: str) -> bool:
    try:
        parsed_url = urlsplit(image_url)
    except ValueError:
        return False
    hostname = parsed_url.hostname.casefold() if parsed_url.hostname else ""
    return parsed_url.scheme.casefold() == "https" and any(hostname == suffix or hostname.endswith(f".{suffix}") for suffix in NOTIFICATION_IMAGE_ALLOWED_HOST_SUFFIXES)


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


# Adds one inline artwork reference before the closing HTML body tag
def add_email_artwork_html(body_html: str, image_name: str = EMAIL_ARTWORK_CONTENT_ID) -> str:
    artwork_html = f'<br><br><img src="cid:{escape(image_name)}" alt="Spotify artwork" style="max-width: {EMAIL_ARTWORK_MAX_DIMENSIONS[0]}px; height: auto;">'
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


# Prints one secret-safe webhook delivery error
def print_webhook_error(detail: Any) -> None:
    safe_detail = sanitize_error_text(detail)
    print(f"Error sending webhook - {safe_detail or 'unknown delivery error'}")


# Sends one webhook through an isolated bounded retry path that never uses Spotify retries
def send_webhook(title: str, description: str, notification_type: str = "profile", force: bool = False, sleeper: Optional[Callable[[float], None]] = None, image_url: str = "") -> int:
    if not force and not webhook_event_enabled(notification_type):
        return 1
    if not validate_webhook_url():
        print_webhook_error("WEBHOOK_URL must contain a complete HTTPS link")
        return 1
    provider = normalized_webhook_provider()
    if not provider:
        print_webhook_error("WEBHOOK_PROVIDER must be discord or ntfy")
        return 1
    customization_error = validate_webhook_customization(provider)
    if customization_error is not None:
        print_webhook_error(customization_error)
        return 1
    header_error = validate_webhook_headers(provider)
    if header_error is not None:
        print_webhook_error(header_error)
        return 1
    try:
        webhook_values = build_webhook_values(title, description, notification_type, image_url)
        request_headers = build_webhook_headers(provider, webhook_values)
        discord_payload = build_webhook_payload(title, description, notification_type, image_url, webhook_values) if provider == "discord" else None
    except ValueError as exc:
        print_webhook_error(exc)
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
                    response = WEBHOOK_SESSION.post(str(WEBHOOK_URL).strip(), data=ntfy_image, params={"title": ntfy_title, "message": ntfy_message}, headers=dict(request_headers, **{"Content-Type": "image/jpeg", "X-Filename": NTFY_IMAGE_FILENAME}), timeout=WEBHOOK_TIMEOUT_SECONDS)
                else:
                    response = WEBHOOK_SESSION.post(str(WEBHOOK_URL).strip(), data=ntfy_message.encode("utf-8"), params={"title": ntfy_title}, headers=request_headers, timeout=WEBHOOK_TIMEOUT_SECONDS)
            elif isinstance(discord_payload, str):
                response = WEBHOOK_SESSION.post(str(WEBHOOK_URL).strip(), data=discord_payload, headers=request_headers, timeout=WEBHOOK_TIMEOUT_SECONDS)
            else:
                response = WEBHOOK_SESSION.post(str(WEBHOOK_URL).strip(), json=discord_payload, headers=request_headers, timeout=WEBHOOK_TIMEOUT_SECONDS)
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
                print_webhook_error(f"HTTP {response.status_code}: {getattr(response, 'text', '')[:200]}")
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
            csvwriter.writerow(csv_row)

    except Exception as e:
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")


# Converts a datetime to local timezone and removes timezone info (naive)
def convert_to_local_naive(dt: datetime | None = None):
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
                    print(f"* Error: Protobuf file ({LOGIN_REQUEST_BODY_FILE}) cannot be processed: {e}")
                else:
                    print(f"* Login data correctly read from Protobuf file ({LOGIN_REQUEST_BODY_FILE}):")
                    print(" - Device ID:\t\t", DEVICE_ID)
                    print(" - System ID:\t\t", SYSTEM_ID)
                    print(" - User URI ID:\t\t", USER_URI_ID)
                    print(" - Refresh Token:\t<<hidden>>\n")
            else:
                print(f"* Error: Protobuf file ({LOGIN_REQUEST_BODY_FILE}) does not exist")

        # Process the client token request body file
        if CLIENTTOKEN_REQUEST_BODY_FILE:
            if os.path.isfile(CLIENTTOKEN_REQUEST_BODY_FILE):
                try:
                    (APP_VERSION, _, _, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL) = parse_clienttoken_request_body_file(CLIENTTOKEN_REQUEST_BODY_FILE)
                except Exception as e:
                    print(f"* Error: Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}) cannot be processed: {e}")
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
    apple_search_url = f"https://music.apple.com/pl/search?term={apple_search_string}"
    genius_search_url = f"https://genius.com/search?q={quote_plus(lyrics_search_string)}"
    azlyrics_search_url = f"https://www.azlyrics.com/search/?q={quote_plus(lyrics_search_string)}"
    tekstowo_search_url = f"https://www.tekstowo.pl/szukaj,{quote_plus(lyrics_search_string)}.html"
    musixmatch_search_url = f"https://www.musixmatch.com/search?query={quote_plus(lyrics_search_string)}"
    lyrics_com_search_url = f"https://www.lyrics.com/serp.php?st={quote_plus(lyrics_search_string)}&qtype=1"
    youtube_music_search_url = f"https://music.youtube.com/search?q={youtube_music_search_string}"
    amazon_music_search_url = f"https://music.amazon.com/search/{quote_plus(spotify_search_string)}"
    deezer_search_url = f"https://www.deezer.com/search/{quote_plus(spotify_search_string)}"
    tidal_search_url = f"https://tidal.com/search?q={quote_plus(spotify_search_string)}"
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
        lines.append(f'Genius lyrics URL: <a href="{genius_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_AZLYRICS_URL:
        lines.append(f'AZLyrics URL: <a href="{azlyrics_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_TEKSTOWO_URL:
        lines.append(f'Tekstowo.pl URL: <a href="{tekstowo_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_MUSIXMATCH_URL:
        lines.append(f'Musixmatch URL: <a href="{musixmatch_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_LYRICS_COM_URL:
        lines.append(f'Lyrics.com URL: <a href="{lyrics_com_url}">{escaped_artist} - {escaped_track}</a>')
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
        lines.append(f'Apple Music URL: <a href="{apple_music_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_YOUTUBE_MUSIC_URL:
        lines.append(f'YouTube Music URL: <a href="{youtube_music_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_AMAZON_MUSIC_URL:
        lines.append(f'Amazon Music URL: <a href="{amazon_music_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_DEEZER_URL:
        lines.append(f'Deezer URL: <a href="{deezer_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_TIDAL_URL:
        lines.append(f'Tidal URL: <a href="{tidal_url}">{escaped_artist} - {escaped_track}</a>')
    return "<br>".join(lines) if lines else ""


# Extracts Spotify ID from URI or URL and return cleaned name
def spotify_extract_id_or_name(s):
    if not isinstance(s, str) or not s.strip():
        return ""

    s = s.strip().lower()

    if s.startswith("https://open.spotify.com/"):
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
    url_cookie_client = "https://guc-spclient.spotify.com/presence-view/v1/buddylist"

    # Use a known stable track for validation (Bohemian Rhapsody - Queen)
    url_oauth_app = "https://api.spotify.com/v1/tracks/7tFiyTwD0nx5a1eklYtX2J"

    url_oauth_user = "https://api.spotify.com/v1/me"

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

    if platform.system() != 'Windows':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT + 2)
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
        if platform.system() != 'Windows':
            signal.alarm(0)
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

    try:
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)
        debug_print(f"HTTP HEAD {SERVER_TIME_URL} [server time] timeout={FUNCTION_TIMEOUT}")
        response = session.head(SERVER_TIME_URL, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        debug_print(f"HTTP HEAD {SERVER_TIME_URL} -> {response.status_code}")
    except TimeoutException as e:
        raise Exception(f"fetch_server_time() head network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        raise Exception(f"fetch_server_time() head network request error: {e}")
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

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
        "Referer": "https://open.spotify.com/",
        "App-Platform": "WebPlayer",
        "Cookie": f"sp_dc={sp_dc}",
    }

    last_err = ""

    try:
        if platform.system() != "Windows":
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)

        debug_print(f"HTTP GET {TOKEN_URL} [sp_dc transport] params={sanitize_debug_params(params)} headers={sanitize_debug_headers(headers)}")
        response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        data = response.json()
        token = data.get("accessToken", "")
        debug_print(f"HTTP GET {TOKEN_URL} [sp_dc transport] -> {response.status_code}, token_len={len(token)}")

    except (req.RequestException, TimeoutException, req.HTTPError, ValueError) as e:
        transport = False
        last_err = str(e)
        debug_print(f"HTTP GET {TOKEN_URL} [sp_dc transport] failed: {e}")
    finally:
        if platform.system() != "Windows":
            signal.alarm(0)

    if not transport or (sp_dc and not check_token_validity(token, data.get("clientId", ""), USER_AGENT)):
        params["reason"] = "init"

        try:
            if platform.system() != "Windows":
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(FUNCTION_TIMEOUT + 2)

            debug_print(f"HTTP GET {TOKEN_URL} [sp_dc init] params={sanitize_debug_params(params)} headers={sanitize_debug_headers(headers)}")
            response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
            response.raise_for_status()
            data = response.json()
            token = data.get("accessToken", "")
            debug_print(f"HTTP GET {TOKEN_URL} [sp_dc init] -> {response.status_code}, token_len={len(token)}")

        except (req.RequestException, TimeoutException, req.HTTPError, ValueError) as e:
            init = False
            last_err = str(e)
            debug_print(f"HTTP GET {TOKEN_URL} [sp_dc init] failed: {e}")
        finally:
            if platform.system() != "Windows":
                signal.alarm(0)

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
                break
        except Exception as e:
            last_error = str(e)
            debug_print(f"Token refresh attempt failed: {e}")
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
        print("* Warning: the 'spotipy' package is required for 'oauth_app' token source, install it with `pip install spotipy`")
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
        print("* Warning: the 'spotipy' package is required for 'oauth_user' token source, install it with `pip install spotipy`")
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

    try:
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] headers={sanitize_debug_headers(headers)} payload_len={len(protobuf_body)}")
        response = req.post(LOGIN_URL, headers=headers, data=protobuf_body, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] -> {response.status_code}")
    except TimeoutException as e:
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] timeout: {e}")
        raise Exception(f"spotify_get_access_token_from_client() network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] failed: {e}")
        raise Exception(f"spotify_get_access_token_from_client() network request error: {e}")
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

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
        "Origin": "https://clienttoken.spotify.com",
        "Accept-Language": "en-Latn-GB,en-GB;q=0.9,en;q=0.8",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Dest": "empty",
        "Accept-Encoding": "gzip, deflate, br, zstd",
    }

    try:
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] app_version={app_version}, device_overrides={device_overrides}, payload_len={len(body)}")
        response = req.post(CLIENTTOKEN_URL, headers=headers, data=body, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] -> {response.status_code}")
    except TimeoutException as e:
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] timeout: {e}")
        raise Exception(f"spotify_get_client_token() network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] failed: {e}")
        raise Exception(f"spotify_get_client_token() network request error: {e}")
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

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
        debug_print(f"Client auth failed: {e}")
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
                    subprocess.run(f"{'echo.' if platform.system() == 'Windows' else 'echo'} {'&' if platform.system() == 'Windows' else ';'} {imgcat_exe} {pic_file_tmp}", shell=True, check=True)
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
        url = f"https://open.spotify.com/user/{s_id}{si}"
    elif "spotify:artist:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/artist/{s_id}{si}"
    elif "spotify:track:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/track/{s_id}{si}"
    elif "spotify:album:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/album/{s_id}{si}"
    elif "spotify:playlist:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/playlist/{s_id}{si}"

    return url


# Converts Spotify URL (e.g. https://open.spotify.com/user/username) to URI (e.g. spotify:user:username)
def spotify_convert_url_to_uri(url):

    url = url or ''
    uri = ""
    if not isinstance(url, str):
        return uri
    if "user" in url:
        uri = url.split('user/', 1)[1]
        if "?" in uri:
            uri = uri.split('?', 1)[0]
        uri = f"spotify:user:{uri}"
    elif "artist" in url:
        uri = url.split('artist/', 1)[1]
        if "?" in uri:
            uri = uri.split('?', 1)[0]
        uri = f"spotify:artist:{uri}"
    elif "track" in url:
        uri = url.split('track/', 1)[1]
        if "?" in uri:
            uri = uri.split('?', 1)[0]
        uri = f"spotify:track:{uri}"
    elif "album" in url:
        uri = url.split('album/', 1)[1]
        if "?" in uri:
            uri = uri.split('?', 1)[0]
        uri = f"spotify:album:{uri}"
    elif "playlist" in url:
        uri = url.split('playlist/', 1)[1]
        if "?" in uri:
            uri = uri.split('?', 1)[0]
        uri = f"spotify:playlist:{uri}"

    return uri


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
                debug_print(f"is_playlist_private(): web-player check failed for playlist_uri={playlist_uri}: {e}")
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
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}?fields=id"

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
                debug_print(f"is_playlist_private(): web-player fallback failed for playlist_uri={playlist_uri}: {e}")
                return response.status_code == 404
        debug_print(f"is_playlist_private(): playlist_uri={playlist_uri} not private/restricted")
        return False
    except Exception as e:
        debug_print(f"is_playlist_private(): request failed for playlist_uri={playlist_uri}: {e}")
        return False


# Checks if a Spotify user URI ID has been deleted
def is_user_removed(access_token, user_uri_id, oauth_app: bool = False):
    # For oauth_app / oauth_user: use web scraping fallback (Client Credentials token cannot access user profile endpoints)
    # open.spotify.com/user/{id} returns 404 for removed users, no auth needed
    if TOKEN_SOURCE in {"oauth_app", "oauth_user"} or oauth_app:
        url = f"https://open.spotify.com/user/{user_uri_id}"
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
    url = f"https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user_uri_id}?playlist_limit=0&artist_limit=0&episode_limit=0&market=from_token"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    if platform.system() != 'Windows':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT + 2)

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
        if platform.system() != 'Windows':
            signal.alarm(0)


# Returns True if the access token owner's user ID matches the provided user_uri_id, False otherwise
def is_token_owner(access_token, user_uri_id) -> bool:
    # /v1/me is only reliable/usable for oauth_user now
    if TOKEN_SOURCE != "oauth_user":
        debug_print(f"is_token_owner(): skipped because TOKEN_SOURCE={TOKEN_SOURCE}")
        return False

    url = "https://api.spotify.com/v1/me"

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
        debug_print(f"is_token_owner(): failed for user_uri_id={user_uri_id}: {e}")
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
        url1 = f"https://api.spotify.com/v1/playlists/{playlist_id}?fields=name,description,owner,followers,external_urls,tracks.total,collaborative,images"
        url2 = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?fields=next,total,items(added_at,track(name,uri,duration_ms,album(images)),added_by),items(track(artists(name,uri)))"
    else:
        url1 = f"https://api.spotify.com/v1/playlists/{playlist_id}?fields=name,description,owner,followers,external_urls,tracks.total,images"
        url2 = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?fields=next,total,items(added_at)"

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

            next_url = json_response2.get("next")

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
        debug_print(f"_spotify_get_playlist_info_api(): failed for uri={playlist_uri}: {e}")
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
            else:
                debug_print(f"spotify_get_playlist_info(): legacy Web API backend failed for uri={playlist_uri} (failures={SP_WEB_PLAYLIST_API_FAILURES}): {e}")

    try:
        return spotify_tag_playlist_source(spotify_get_playlist_info_web(playlist_uri, get_tracks), "web")
    except Exception as e:
        web_error = e
        debug_print(f"spotify_get_playlist_info(): web-player backend failed for uri={playlist_uri}: {e}")

    if api_available and (SP_WEB_PLAYLIST_BACKEND_PREFERRED or api_error is None):
        try:
            return spotify_tag_playlist_source(_spotify_get_playlist_info_api(access_token, playlist_uri, get_tracks, oauth_app), "api")
        except Exception as e:
            api_error = e
            debug_print(f"spotify_get_playlist_info(): legacy Web API fallback failed for uri={playlist_uri}: {e}")

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
    url1 = f"https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user_uri_id}?playlist_limit={PLAYLISTS_LIMIT if get_playlists else 0}&artist_limit={recently_played_limit}&episode_limit=10&market=from_token"

    # URLs used for oauth_app & oauth_user token sources
    url2 = f"https://api.spotify.com/v1/users/{user_uri_id}"
    url2_pl = f"https://api.spotify.com/v1/users/{user_uri_id}/playlists?limit={PLAYLISTS_LIMIT if get_playlists else 0}"

    # URL used for recently played artists for oauth_user
    days_back = 7
    url3 = f"https://api.spotify.com/v1/me/player/recently-played?limit={recently_played_limit}&after={int((now_local() - timedelta(days=days_back)).timestamp() * 1000)}"

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
            url_me = "https://api.spotify.com/v1/me"
            url_me_playlists = f"https://api.spotify.com/v1/me/playlists?limit={PLAYLISTS_LIMIT if get_playlists else 0}"

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
                while url_me_playlists:
                    json_response = _rq(url_me_playlists)
                    raw_playlist_data_from_api = json_response.get("items")
                    current_list_to_process = raw_playlist_data_from_api if isinstance(raw_playlist_data_from_api, list) else []
                    out["sp_user_public_playlists_uris"].extend({"image_url": (p.get("images") or [{}])[0].get("url", ""), "uri": p.get("uri"), "owner_uri": p.get("owner", {}).get("uri")} for p in current_list_to_process if isinstance(p, dict) and (GET_ALL_PLAYLISTS or p.get("owner", {}).get("uri") == f"spotify:user:{user_uri_id}"))
                    url_me_playlists = json_response.get("next")
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
                    while url2_pl:
                        json_response = _rq(url2_pl)
                        raw_playlist_data_from_api = json_response.get("items")
                        current_list_to_process = raw_playlist_data_from_api if isinstance(raw_playlist_data_from_api, list) else []
                        out["sp_user_public_playlists_uris"].extend({"image_url": (p.get("images") or [{}])[0].get("url", ""), "uri": p.get("uri"), "owner_uri": p.get("owner", {}).get("uri")} for p in current_list_to_process if isinstance(p, dict) and (GET_ALL_PLAYLISTS or p.get("owner", {}).get("uri") == f"spotify:user:{user_uri_id}"))
                        url2_pl = json_response.get("next")
                    out["sp_user_public_playlists_count"] = len(out["sp_user_public_playlists_uris"])

            except req.HTTPError as e:
                if e.response is not None and e.response.status_code in {403, 404}:
                    # oauth_app (Client Credentials) does not have permission to access user profile endpoints
                    print(f"\n* Warning: Cannot fetch profile for user '{user_uri_id}' with {TOKEN_SOURCE} token source")
                    print("* GET /users/{{id}} and GET /users/{{id}}/playlists are not accessible with Client Credentials (oauth_app) token")
                    print("* To monitor other users, use 'cookie' or 'client' token source (with oauth_app hybrid)")
                    print("* If you're using oauth_user to monitor your own account, ensure the user URI ID matches your account\n")
                    raise ValueError(f"Cannot monitor user '{user_uri_id}' with '{TOKEN_SOURCE}' token source. Use 'cookie' or 'client' token source for monitoring other users.")
                raise

        # Recently played artists (only for oauth_user monitoring self)
        artists_data = []
        if TOKEN_SOURCE == "oauth_user" and recently_played_limit > 0 and is_self:

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
                response = SESSION.get("https://api.spotify.com/v1/me/following", headers=headers, params=params, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
                debug_print(f"HTTP GET https://api.spotify.com/v1/me/following [followings] -> {response.status_code}")
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

    url = f"https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user_uri_id}/following?market=from_token"
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

    url = f"https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user_uri_id}/followers?market=from_token"
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
    added_at_dt: datetime | None = None

    try:
        if csv_file_name:
            init_csv_file(csv_file_name, format_type)
    except Exception as e:
        print(f"* Error: {e}")

    if not CLEAN_OUTPUT and not EXPORT_ALL:
        list_operation = "* Listing & saving" if csv_file_name else "* Listing"
        print(f"{list_operation} tracks for playlist '{playlist_url}' ...\n")

    user_id_name_mapping = {}
    user_track_counts = Counter()
    unknown_added_by_tracks = 0

    pattern = re.compile(r'^[a-zA-Z0-9]{22}$')
    if (pattern.match(playlist_url)):
        playlist_uri = f"::{playlist_url}"
    else:
        playlist_uri = spotify_convert_url_to_uri(playlist_url)

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
                    print(f"* Error: {e}")

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
            print(f"* Error writing to the output file {csv_file_name} - {e}")

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
    url = f"https://api.spotify.com/v1/me/tracks?fields=next,total,items(added_at,track(name,uri,duration_ms),added_by),items(track(artists(name,uri)))"

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

        while next_url:
            debug_print(f"HTTP GET {next_url} [liked tracks] headers={sanitize_debug_headers(headers)}")
            response = SESSION.get(next_url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
            debug_print(f"HTTP GET {next_url} [liked tracks] -> {response.status_code}")
            response.raise_for_status()
            json_response = response.json()

            for track in json_response.get("items", []):
                sp_playlist_tracks_concatenated_list.append(track)

            next_url = json_response.get("next")

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
    added_at_dt: datetime | None = None
    username = ""

    try:
        if csv_file_name:
            init_csv_file(csv_file_name, format_type)
    except Exception as e:
        print(f"* Error: {e}")

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
                    print(f"* Error: {e}")

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
            print(f"* Error writing to the output file {csv_file_name} - {e}")


# Compares two lists of dictionaries
def compare_two_lists_of_dicts(list1: list, list2: list):
    if not list1:
        list1 = []
    if not list2:
        list2 = []

    diff = [i for i in list1 + list2 if i not in list2]
    return diff


# Searches for Spotify users (-s flag)
def spotify_search_users(access_token, username):
    url = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=searchUsers&variables=%7B%22searchTerm%22%3A%22{username}%22%2C%22offset%22%3A0%2C%22limit%22%3A5%2C%22numberOfTopResults%22%3A5%2C%22includeAudiobooks%22%3Afalse%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{SP_SHA256}%22%7D%7D"

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
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP GET {url} [search users] -> {response.status_code}")
        response.raise_for_status()
    except Exception:
        raise

    json_response = response.json()
    if json_response["data"]["searchV2"]["users"].get("totalCount") > 0:
        for user in json_response["data"]["searchV2"]["users"]["items"]:
            print(f"Username:\t\t{user['data']['displayName']}")
            print(f"User URI:\t\t{user['data']['uri']}")
            print(f"User URI ID:\t\t{user['data']['id']}")
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

    display_name = playlist_name or ""
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
    added_at_dt: datetime | None = None

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
                            debug_print(f"playlist loop: uri={p_uri} processing error: {e}")
                            existing = PLAYLIST_INFO_CACHE.get(p_uri, {})
                            existing.update({
                                "status": "error",
                                "timestamp": time.time(),
                                "error": str(e)
                            })
                            PLAYLIST_INFO_CACHE[p_uri] = existing

                            failure_count += 1
                            if failure_count == 1 or not HIDE_DUPLICATE_NETWORK_ERRORS:
                                print(f"\n* Error while processing playlist {spotify_format_playlist_reference(p_uri)}, skipping for now" + (f": {e}" if e else ""))
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
                    debug_print(f"playlist loop: unexpected build error for uri={p_uri}: {e}")

                    failure_count += 1
                    if failure_count == 1 or not HIDE_DUPLICATE_NETWORK_ERRORS:
                        print(f"\n* Unexpected error while building playlist data for: {spotify_format_playlist_reference(p_uri)}: {e}")
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


# Prints detailed info about the user with the specified URI ID (-i flag)
def spotify_get_user_details(sp_accessToken, user_uri_id):
    playlists_count = 0
    playlists = None

    print(f"* Getting detailed info for user with URI ID '{user_uri_id}' ...\n")

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
    print(f"User URI ID:\t\t{user_uri_id}")
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
    print(f"* Getting list of recently played artists for user with URI ID '{user_uri_id}' ...\n")

    sp_user_data = spotify_get_user_info(sp_accessToken, user_uri_id, False, RECENTLY_PLAYED_ARTISTS_LIMIT)

    username = sp_user_data["sp_username"]
    image_url = sp_user_data["sp_user_image_url"]

    recently_played_artists = sp_user_data["sp_user_recently_played_artists"]

    print(f"Username:\t\t{username}")
    print(f"User URI ID:\t\t{user_uri_id}")
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
    print(f"* Getting followers & followings for user with URI ID '{user_uri_id}' ...\n")

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
    print(f"User URI ID:\t\t{user_uri_id}")
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
                        html_output = f"- <a href=\"{p_url}\">{escape(p_name)}</a> [ <b>RESTRICTED</b> ]<br>&nbsp;&nbsp;Likes: <b>{escape(str(followers_str))}</b><br>&nbsp;&nbsp;Metadata source: profile-view only"
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
                        html_output = f"- <a href=\"{p_url}\">{escape(p_name)}</a>"
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
                        print(f"* Error: {e}")
            else:
                if "name" in f_dict and "uri" in f_dict:
                    print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                    list_of_added_f_list += f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]"
                    list_of_added_f_list_html += f"- <a href=\"{spotify_convert_uri_to_url(f_dict['uri'])}\">{escape(f_dict['name'])}</a>"

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
                        print(f"* Error: {e}")
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
                            print(f"- Suspected temporary glitch for playlist {spotify_format_playlist_reference(uri)}" + (f": {error_str}" if error_str else ""))
                            GLITCH_CACHE[uri] = time.time()
                            print_cur_ts("Timestamp:\t\t\t")
                            continue

                        else:
                            print(f"- Error while getting info for playlist {spotify_format_playlist_reference(uri)}, skipping for now" + (f": {error_str}" if error_str else ""))
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
                        html_output = f"- <a href=\"{p_url}\">{escape(p_name)}</a> [ <b>RESTRICTED</b> ]<br>&nbsp;&nbsp;Likes: <b>{escape(str(followers_str))}</b><br>&nbsp;&nbsp;Metadata source: profile-view only"

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
                            print(f"* Error: {e}")
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
                        html_output = f"- <a href=\"{p_url}\">{escape(p_name)}</a>: playlist has been removed or set to private"
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
                        html_output = f"- <a href=\"{p_url}\">{escape(p_name)}</a>"
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
                        print(f"* Error: {e}")
            else:
                if "name" in f_dict and "uri" in f_dict:
                    print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                    list_of_removed_f_list += f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]"
                    list_of_removed_f_list_html += f"- <a href=\"{spotify_convert_uri_to_url(f_dict['uri'])}\">{escape(f_dict['name'])}</a>"

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
                        print(f"* Error: {e}")
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
        print(f"* Cannot save list of {str(f_str).lower()} to '{f_file}' file: {e}")

    try:
        if csv_file_name:
            write_csv_entry(csv_file_name, now_local_naive(), f_str, username, f_old_count, f_count)
    except Exception as e:
        print(f"* Error: {e}")

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


# Saves user's profile pic to selected file name
def save_profile_pic(user_image_url, image_file_name):
    try:
        debug_print(f"HTTP GET {user_image_url} [profile image] stream=True")
        image_response = req.get(user_image_url, headers={'User-Agent': USER_AGENT}, timeout=FUNCTION_TIMEOUT, stream=True, verify=VERIFY_SSL)
        debug_print(f"HTTP GET {user_image_url} [profile image] -> {image_response.status_code}")
        image_response.raise_for_status()
        url_time = image_response.headers.get('last-modified')

        url_time_in_tz_ts = 0
        if url_time:
            url_time_in_tz = parsedate_to_datetime(url_time).astimezone(pytz.timezone(LOCAL_TIMEZONE))
            url_time_in_tz_ts = int(url_time_in_tz.timestamp())

        if image_response.status_code == 200:
            with open(image_file_name, 'wb') as f:
                image_response.raw.decode_content = True
                shutil.copyfileobj(image_response.raw, f)
            if url_time_in_tz_ts:
                os.utime(image_file_name, (url_time_in_tz_ts, url_time_in_tz_ts))
            debug_print(f"save_profile_pic(): saved image to {image_file_name}")
        return True
    except Exception as e:
        debug_print(f"save_profile_pic(): failed for url={user_image_url}: {e}")
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
        print(f"* Error while comparing profile pictures: {e}")
        return False


# Return tracks in list_a that are not in list_b, ignoring added_by
def diff_tracks(list_a, list_b):
    def sig(d):
        return (d.get("uri"), d.get("artist"), d.get("track"), d.get("duration"), d.get("added_at"), d.get("added_by_id") or "")

    set_b = {sig(x) for x in list_b}
    return [x for x in list_a if sig(x) not in set_b]


class WebhookConfigurationError(Exception):
    pass


class SpDcConfigurationError(Exception):
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


# Validates and atomically stores one privately entered sp_dc cookie
def run_set_sp_dc(env_file=None, interactive=None, input_func=None, getpass_func=None) -> str:
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
    command_parts = ["spotify_profile_monitor", "--send-test-webhook"]
    if config_path:
        command_parts.extend(("--config-file", str(config_path)))
    command_parts.extend(("--env-file", str(destination)))
    test_command = " ".join(shlex.quote(part) for part in command_parts)
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


# Resolves an executable path by checking if it's a valid file or searching in $PATH
def resolve_executable(path):
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path

    found = shutil.which(path)
    if found:
        return found

    raise FileNotFoundError(f"Could not find executable '{path}'")


# Normalizes a raw Spotify user ID, user URI or profile URL into one user ID
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


# Monitors profile changes of the specified Spotify user URI ID
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

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print(f"* Error: {e}")

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

        client_errs = ['access token', 'invalid client token', 'expired client token', 'refresh token has been revoked', 'refresh token has expired', 'refresh token is invalid', 'invalid grant during refresh']
        cookie_errs = ['access token', 'unauthorized', 'unsuccessful token request']
        oauth_app_errs = ['invalid_client', 'invalid_client_id', 'could not authenticate you', '401']
        oauth_user_errs = ['invalid_client', 'invalid_grant', 'invalid_scope', 'authorization_required', 'refresh token has been revoked', 'refresh token has expired']

        if TOKEN_SOURCE == 'client' and any(k in err for k in client_errs):
            print(f"* Error: client or refresh token may be invalid or expired!\n{str(e)}")
        elif TOKEN_SOURCE == 'cookie' and any(k in err for k in cookie_errs):
            print(f"* Error: sp_dc may be invalid/expired or Spotify has broken sth again!\n{str(e)}")
        elif TOKEN_SOURCE == 'oauth_app' and any(k in err for k in oauth_app_errs):
            print(f"* Error: OAuth-app client_id/client_secret may be invalid or expired!\n{str(e)}")
        elif TOKEN_SOURCE == 'oauth_user' and any(k in err for k in oauth_user_errs):
            print(f"* Error: User OAuth token or credentials may be invalid, expired or require re-authorization!\n{str(e)}")
        elif '404' in err:
            if is_user_removed(sp_accessToken, user_uri_id):
                print(f"* Error: User '{user_uri_id}' does not exist!")
            else:
                print(f"* Error: {e}")
        else:
            print(f"* Error: {e}")

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
    print(f"User URI ID:\t\t\t{user_uri_id}")
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
                print(f"* Cannot load entries from '{playlists_file}' file: {e}")
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
                print(f"* Cannot save list of playlists to '{playlists_file}' file: {e}")

        if playlist_collection_changed(playlists, playlists_old, playlists_count, playlists_old_count):
            spotify_print_changed_followers_followings_playlists(username, playlists, playlists_old, playlists_count, playlists_old_count, "Playlists", "for", "Added playlists to profile", "Added Playlist", "Removed playlists from profile", "Removed Playlist", playlists_file, csv_file_name, False, True, sp_accessToken)

        print_cur_ts("Timestamp:\t\t\t")

    # followers
    if os.path.isfile(followers_file):
        try:
            with open(followers_file, 'r', encoding="utf-8") as f:
                followers_read = json.load(f)
        except Exception as e:
            print(f"* Cannot load entries from '{followers_file}' file: {e}")
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
            print(f"* Cannot save list of followers to '{followers_file}' file: {e}")

    if followers_count != followers_old_count:
        spotify_print_changed_followers_followings_playlists(username, followers, followers_old, followers_count, followers_old_count, "Followers", "for", "Added followers", "Added Follower", "Removed followers", "Removed Follower", followers_file, csv_file_name, False, False)

    print_cur_ts("Timestamp:\t\t\t")

    # followings
    if os.path.isfile(followings_file):
        try:
            with open(followings_file, 'r', encoding="utf-8") as f:
                followings_read = json.load(f)
        except Exception as e:
            print(f"* Cannot load entries from '{followings_file}' file: {e}")
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
            print(f"* Cannot save list of followings to '{followings_file}' file: {e}")

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
                print(f"* Error: {e}")

            print_cur_ts("Timestamp:\t\t\t")

        # User has profile pic, but it does not exist in the filesystem
        elif image_url and not os.path.isfile(profile_pic_file):
            if save_profile_pic(image_url, profile_pic_file):
                profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)), pytz.timezone(LOCAL_TIMEZONE))
                print(f"* User {username} profile picture saved to '{profile_pic_file}'")
                print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)")

                try:
                    if imgcat_exe:
                        subprocess.run(f"{'echo.' if platform.system() == 'Windows' else 'echo'} {'&' if platform.system() == 'Windows' else ';'} {imgcat_exe} {profile_pic_file} {'&' if platform.system() == 'Windows' else ';'} {'echo.' if platform.system() == 'Windows' else 'echo'}", shell=True, check=True)
                    shutil.copy2(profile_pic_file, f'spotify_profile_{FILE_SUFFIX}_pic_{profile_pic_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                except Exception:
                    pass

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, now_local_naive(), "Profile Picture Created", username, "", convert_to_local_naive(profile_pic_mdate_dt))
                except Exception as e:
                    print(f"* Error: {e}")

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
                        print(f"* Error: {e}")

                    try:
                        if imgcat_exe:
                            subprocess.run(f"{'echo.' if platform.system() == 'Windows' else 'echo'} {'&' if platform.system() == 'Windows' else ';'} {imgcat_exe} {profile_pic_file_tmp} {'&' if platform.system() == 'Windows' else ';'} {'echo.' if platform.system() == 'Windows' else 'echo'}", shell=True, check=True)
                        shutil.copy2(profile_pic_file_tmp, f'spotify_profile_{FILE_SUFFIX}_pic_{profile_pic_tmp_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                        os.replace(profile_pic_file, profile_pic_file_old)
                        os.replace(profile_pic_file_tmp, profile_pic_file)
                    except Exception as e:
                        print(f"* Error while replacing/copying files: {e}")

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
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(ALARM_TIMEOUT)
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
            if platform.system() != 'Windows':
                signal.alarm(0)
        except TimeoutException:
            if platform.system() != 'Windows':
                signal.alarm(0)
            print(f"spotify_*() function timeout after {display_time(ALARM_TIMEOUT)}, retrying in {display_time(ALARM_RETRY)}")
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(ALARM_RETRY)
            continue
        except Exception as e:
            if platform.system() != 'Windows':
                signal.alarm(0)

            debug_print(f"Main monitor loop error: {e}")
            print(f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: {e}")

            err = str(e).lower()

            if TOKEN_SOURCE == 'cookie' and '401' in err:
                SP_CACHED_ACCESS_TOKEN = None

            client_errs = ['access token', 'invalid client token', 'expired client token', 'refresh token has been revoked', 'refresh token has expired', 'refresh token is invalid', 'invalid grant during refresh']
            cookie_errs = ['access token', 'unauthorized', 'unsuccessful token request']
            oauth_app_errs = ['invalid_client', 'invalid_client_id', 'could not authenticate you', '401']
            oauth_user_errs = ['invalid_client', 'invalid_grant', 'invalid_scope', 'authorization_required', 'refresh token has been revoked', 'refresh token has expired']

            if TOKEN_SOURCE == 'client' and any(k in err for k in client_errs):
                print(f"* Error: client or refresh token may be invalid or expired!")
                if notification_channels_pending("error", ERROR_NOTIFICATION, email_sent, webhook_sent):
                    m_subject = f"spotify_profile_monitor: client or refresh token may be invalid or expired! (uri: {user_uri_id})"
                    m_body = f"Client or refresh token may be invalid or expired!\n{e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>Client or refresh token may be invalid or expired!<br>{escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    email_sent, webhook_sent = send_pending_error_notification(m_subject, m_body, m_body_html, email_sent, webhook_sent)

            elif TOKEN_SOURCE == 'cookie' and any(k in err for k in cookie_errs):
                print(f"* Error: sp_dc may be invalid/expired or Spotify has broken sth again!")
                if notification_channels_pending("error", ERROR_NOTIFICATION, email_sent, webhook_sent):
                    m_subject = f"spotify_profile_monitor: sp_dc may be invalid/expired or Spotify has broken sth again! (uri: {user_uri_id})"
                    m_body = f"sp_dc may be invalid/expired or Spotify has broken sth again!\n{e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>sp_dc may be invalid/expired or Spotify has broken sth again!<br>{escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    email_sent, webhook_sent = send_pending_error_notification(m_subject, m_body, m_body_html, email_sent, webhook_sent)

            elif TOKEN_SOURCE == 'oauth_app' and any(k in err for k in oauth_app_errs):
                print(f"* Error: OAuth-app client_id/client_secret may be invalid or expired!")

                if notification_channels_pending("error", ERROR_NOTIFICATION, email_sent, webhook_sent):
                    m_subject = f"spotify_profile_monitor: OAuth-app client_id/client_secret may be invalid or expired! (uri: {user_uri_id})"
                    m_body = f"OAuth-app client_id/client_secret may be invalid or expired!\n{e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>OAuth-app client_id/client_secret may be invalid or expired!<br>{escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    email_sent, webhook_sent = send_pending_error_notification(m_subject, m_body, m_body_html, email_sent, webhook_sent)

            elif TOKEN_SOURCE == 'oauth_user' and any(k in err for k in oauth_user_errs):
                print(f"* Error: User OAuth token or credentials may be invalid, expired or require re-authorization!")
                if notification_channels_pending("error", ERROR_NOTIFICATION, email_sent, webhook_sent):
                    m_subject = f"spotify_profile_monitor: user OAuth token or credentials may be invalid, expired or require re-authorization! (uri: {user_uri_id})"
                    m_body = f"User OAuth token or credentials may be invalid, expired or require re-authorization!\n{e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>User OAuth token or credentials may be invalid, expired or require re-authorization!<br>{escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    email_sent, webhook_sent = send_pending_error_notification(m_subject, m_body, m_body_html, email_sent, webhook_sent)

            elif 'cannot monitor user' in err:
                if notification_channels_pending("error", ERROR_NOTIFICATION, email_sent, webhook_sent):
                    m_subject = f"spotify_profile_monitor: token source '{TOKEN_SOURCE}' not supported for monitoring this user! (uri: {user_uri_id})"
                    m_body = f"Token source '{TOKEN_SOURCE}' is not supported for monitoring user '{user_uri_id}'!\n{e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>Token source '{TOKEN_SOURCE}' is not supported for monitoring user '{user_uri_id}'!<br>{escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    email_sent, webhook_sent = send_pending_error_notification(m_subject, m_body, m_body_html, email_sent, webhook_sent)

            elif 'not found' in err or '404' in err:
                if is_user_removed(sp_accessToken, user_uri_id):
                    print(f"* Error: User '{user_uri_id}' might have removed the account!")
                    if notification_channels_pending("error", ERROR_NOTIFICATION, email_sent, webhook_sent):
                        m_subject = f"spotify_profile_monitor: user might have removed the account! (uri: {user_uri_id})"
                        m_body = f"User might have removed the account: {e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>User might have removed the account: {escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
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
                print(f"* Error: {e}")

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
        except Exception as e:
            print(f"* Error while getting followers & followings, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: {e}")
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
                    print(f"* Error: {e}")

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
                            subprocess.run(f"{imgcat_exe} {profile_pic_file} {'&' if platform.system() == 'Windows' else ';'} {'echo.' if platform.system() == 'Windows' else 'echo'}", shell=True, check=True)
                        shutil.copy2(profile_pic_file, f'spotify_profile_{FILE_SUFFIX}_pic_{profile_pic_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                    except Exception:
                        pass

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), "Profile Picture Created", username, "", convert_to_local_naive(profile_pic_mdate_dt))
                    except Exception as e:
                        print(f"* Error: {e}")

                    if notification_channels_enabled("profile", PROFILE_NOTIFICATION):
                        m_subject = f"Spotify user {username} has set profile picture ! ({get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)})"
                        m_body = f"Spotify user {username} has set profile picture !\n\nProfile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Spotify user <b>{username}</b> has set profile picture !{m_body_html_pic_saved_text}<br><br>Profile picture has been added on <b>{get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)}</b> ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)<br><br>Check interval: <b>{display_time(SPOTIFY_CHECK_INTERVAL)}</b> ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts('<br>Timestamp: ')}</body></html>"
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
                            print(f"* Error: {e}")

                        try:
                            if imgcat_exe:
                                subprocess.run(f"{imgcat_exe} {profile_pic_file_tmp} {'&' if platform.system() == 'Windows' else ';'} {'echo.' if platform.system() == 'Windows' else 'echo'}", shell=True, check=True)
                            shutil.copy2(profile_pic_file_tmp, f'spotify_profile_{FILE_SUFFIX}_pic_{profile_pic_tmp_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                            os.replace(profile_pic_file, profile_pic_file_old)
                            os.replace(profile_pic_file_tmp, profile_pic_file)
                        except Exception as e:
                            print(f"* Error while replacing/copying files: {e}")

                        if notification_channels_enabled("profile", PROFILE_NOTIFICATION):
                            m_body_html_pic_saved_text = f'<br><br><img src="cid:profile_pic">'
                            m_subject = f"Spotify user {username} has changed profile picture ! (after {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)})"
                            m_body = f"Spotify user {username} has changed profile picture !\n\nPrevious one added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)\n\nProfile picture has been added on {get_short_date_from_ts(profile_pic_tmp_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                            m_body_html = f"<html><head></head><body>Spotify user <b>{username}</b> has changed profile picture !{m_body_html_pic_saved_text}<br><br>Previous one added on <b>{get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)}</b> ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)<br><br>Profile picture has been added on <b>{get_short_date_from_ts(profile_pic_tmp_mdate_dt, always_show_year=True)}</b> ({calculate_timespan(now_local(), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)<br><br>Check interval: <b>{display_time(SPOTIFY_CHECK_INTERVAL)}</b> ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts('<br>Timestamp: ')}</body></html>"
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
                                        print(f"* Error while processing likes for playlist {spotify_format_playlist_reference(p_uri)}, skipping for now" + (f": {e}" if e else ""))
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue

                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Playlist Likes", p_name, likes_display_old, likes_display_new)
                                    except Exception as e:
                                        print(f"* Error: {e}")

                                    m_subject = f"Spotify user {username} number of likes for playlist '{p_name}' has changed! ({p_likes_diff_str}, {likes_display_old} -> {likes_display_new})"
                                    m_body = f"{p_message}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>Playlist '<b><a href=\"{p_url}\">{escape(p_name)}</a></b>': number of likes changed from <b>{escape(str(likes_display_old))}</b> to <b>{escape(str(likes_display_new))}</b> (<b>{escape(p_likes_diff_str)}</b>)<br><br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
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
                                            print(f"* Error: {e}")
                                        m_subject = f"Spotify user {username} playlist '{p_name_old}' name changed to '{p_name}'! [RESTRICTED]"
                                        m_body = f"{p_message}\nMetadata source: profile-view only\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                        m_body_html = f"<html><head></head><body>Playlist '<b>{escape(p_name_old)}</b>': name changed to new name '<b><a href=\"{p_url}\">{escape(p_name)}</a></b>' [<b>RESTRICTED</b>]<br><br>Metadata source: profile-view only<br><br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
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
                                        print(f"* Error while processing collaborators for playlist {spotify_format_playlist_reference(p_uri)}, skipping for now" + (f": {e}" if e else ""))
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue

                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Collaborators Number", p_name, p_collaborators_old, p_collaborators)
                                    except Exception as e:
                                        print(f"* Error: {e}")

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
                                                p_message_added_collaborators_html += f'- <a href="{spotify_convert_uri_to_url(f"spotify:user:{collab_id}")}">{escape(collab_name)}</a><br>'
                                                try:
                                                    if csv_file_name:
                                                        write_csv_entry(csv_file_name, now_local_naive(), "Added Collaborator", p_name, "", collab_name)
                                                except Exception as e:
                                                    print(f"* Error: {e}")

                                            p_message_added_collaborators += "\n"
                                            print(p_message_added_collaborators, end="")

                                        if removed_collaborators:
                                            p_message_removed_collaborators = "Removed collaborators:\n\n"
                                            p_message_removed_collaborators_html = "<br><b>Removed collaborators:</b><br><br>"

                                            for collab_id, collab_name in removed_collaborators.items():
                                                removed_collab = f'- {collab_name} [ {spotify_convert_uri_to_url(f"spotify:user:{collab_id}")} ]\n'
                                                p_message_removed_collaborators += removed_collab
                                                p_message_removed_collaborators_html += f'- <a href="{spotify_convert_uri_to_url(f"spotify:user:{collab_id}")}">{escape(collab_name)}</a><br>'
                                                try:
                                                    if csv_file_name:
                                                        write_csv_entry(csv_file_name, now_local_naive(), "Removed Collaborator", p_name, collab_name, "")
                                                except Exception as e:
                                                    print(f"* Error: {e}")

                                            p_message_removed_collaborators += "\n"
                                            print(p_message_removed_collaborators, end="")

                                    except Exception as e:
                                        print(f"* Error while processing added/removed collaborators for playlist {spotify_format_playlist_reference(p_uri)}, skipping for now" + (f": {e}" if e else ""))
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue

                                    m_subject = f"Spotify user {username} number of collaborators for playlist '{p_name}' has changed! ({p_collaborators_diff_str}, {p_collaborators_old} -> {p_collaborators})"
                                    m_body = f"{p_message}\n{p_message_added_collaborators}{p_message_removed_collaborators}Check interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>Playlist '<b><a href=\"{p_url}\">{escape(p_name)}</a></b>': number of collaborators changed from <b>{p_collaborators_old}</b> to <b>{p_collaborators}</b> (<b>{escape(p_collaborators_diff_str)}</b>)<br>{p_message_added_collaborators_html}{p_message_removed_collaborators_html}<br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
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
                                        print(f"* Error while processing changed tracks for playlist {spotify_format_playlist_reference(p_uri)}, skipping for now" + (f": {e}" if e else ""))
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue

                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Playlist Number of Tracks", p_name, p_tracks_old, p_tracks)
                                    except Exception as e:
                                        print(f"* Error: {e}")

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
                                                    added_track_html = f'- <b><a href="{spotify_convert_uri_to_url(f_dict["uri"])}">{escape(f_dict["artist"])} - {escape(f_dict["track"])}</a></b> [ {escape(get_date_from_ts(f_dict["added_at"]))}, <a href="{spotify_convert_uri_to_url(tempuri)}">{escape(f_dict["added_by"])}</a> ]<br>'
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
                                                        print(f"* Error: {e}")

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
                                                    removed_track_html = f'- <b><a href="{spotify_convert_uri_to_url(f_dict["uri"])}">{escape(f_dict["artist"])} - {escape(f_dict["track"])}</a></b> [ {escape(get_date_from_ts(f_dict["added_at"]))}, <a href="{spotify_convert_uri_to_url(tempuri)}">{escape(f_dict["added_by"])}</a> ]<br>'
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
                                                        print(f"* Error: {e}")

                                    except Exception as e:
                                        print(f"* Error while processing added/removed tracks for playlist {spotify_format_playlist_reference(p_uri)}, skipping for now" + (f": {e}" if e else ""))
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue

                                    p_subject_after_str = ""
                                    if p_tracks_diff != 0:
                                        if p_update and p_update_old:
                                            p_subject_after_str = f"; after {calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2)}"
                                        m_subject = f"Spotify user {username} number of tracks for playlist '{p_name}' has changed! ({p_tracks_diff_str}, {p_tracks_old} -> {p_tracks}{p_subject_after_str})"
                                        m_body_html_p_message = f"Playlist '<b><a href=\"{p_url}\">{escape(p_name)}</a></b>': number of tracks changed from <b>{p_tracks_old}</b> to <b>{p_tracks}</b> (<b>{escape(p_tracks_diff_str)}</b>)"
                                        if p_after_str:
                                            m_body_html_p_message += f" (after <b>{escape(calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2))}</b>; previous update: <b>{escape(get_short_date_from_ts(p_update_old, True))}</b>)"
                                        m_body_html_p_message += "<br>"
                                    else:
                                        if p_update and p_update_old:
                                            p_subject_after_str = f" (after {calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2)})"
                                        m_subject = f"Spotify user {username} list of tracks ({p_tracks}) for playlist '{p_name}' has changed!{p_subject_after_str}"
                                        m_body_html_p_message = f"Playlist '<b><a href=\"{p_url}\">{escape(p_name)}</a></b>': list of tracks (<b>{p_tracks}</b>) have changed"
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
                                        print(f"* Error: {e}")
                                    m_subject = f"Spotify user {username} playlist '{p_name_old}' name changed to '{p_name}'!"
                                    m_body = f"{p_message}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>Playlist '<b>{escape(p_name_old)}</b>': name changed to new name '<b><a href=\"{p_url}\">{escape(p_name)}</a></b>'<br><br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
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
                                        print(f"* Error: {e}")
                                    m_subject = f"Spotify user {username} playlist '{p_name}' description has changed !"
                                    m_body = f"{p_message}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>Playlist '<b><a href=\"{p_url}\">{escape(p_name)}</a></b>' description changed from:<br><br>'<i>{escape(p_descr_old)}</i>'<br><br>to:<br><br>'<i>{escape(p_descr)}</i>'<br><br>Check interval: <b>{escape(display_time(SPOTIFY_CHECK_INTERVAL))}</b> ({escape(get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True))}){get_cur_ts('<br>Timestamp: ')}</body></html>"
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

# Parses configuration and command-line options then runs the selected operation
def main():
    global CLI_CONFIG_PATH, DOTENV_FILE, LOCAL_TIMEZONE, LIVENESS_CHECK_COUNTER, SP_DC_COOKIE, SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET, SP_USER_CLIENT_ID, SP_USER_CLIENT_SECRET, LOGIN_REQUEST_BODY_FILE, CLIENTTOKEN_REQUEST_BODY_FILE, REFRESH_TOKEN, LOGIN_URL, USER_AGENT, DEVICE_ID, SYSTEM_ID, USER_URI_ID, CSV_FILE, PLAYLISTS_TO_SKIP_FILE, FILE_SUFFIX, DISABLE_LOGGING, DEBUG_MODE, SP_LOGFILE, PROFILE_NOTIFICATION, EMAIL_IMAGES, SPOTIFY_CHECK_INTERVAL, SPOTIFY_ERROR_INTERVAL, FOLLOWERS_FOLLOWINGS_NOTIFICATION, ERROR_NOTIFICATION, DETECT_CHANGED_PROFILE_PIC, DETECT_CHANGES_IN_PLAYLISTS, GET_ALL_PLAYLISTS, imgcat_exe, SMTP_PASSWORD, SP_SHA256, stdout_bck, APP_VERSION, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL, TOKEN_SOURCE, ALARM_TIMEOUT, pyotp, CLEAN_OUTPUT, USER_AGENT, SP_APP_TOKENS_FILE, SP_USER_TOKENS_FILE, TARGET_USER_URI_ID, TRUNCATE_CHARS, NTFY_IMAGES
    global EXPORT_ALL

    if "--generate-config" in sys.argv:
        config_content = CONFIG_BLOCK.strip("\n") + "\n"
        # Check if a filename was provided after --generate-config
        try:
            idx = sys.argv.index("--generate-config")
            if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
                # Write directly to file (bypasses PowerShell UTF-16 encoding issue on Windows)
                output_file = sys.argv[idx + 1]
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(config_content)
                print(f"Config written to: {output_file}")
                sys.exit(0)
        except (ValueError, IndexError):
            pass
        # No filename provided - write to stdout using buffer to ensure UTF-8
        sys.stdout.buffer.write(config_content.encode("utf-8"))
        sys.stdout.buffer.flush()
        sys.exit(0)

    if "--version" in sys.argv:
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(
        prog="spotify_profile_monitor",
        description=("Monitor a Spotify user's profile changes including playlists and send customizable email or webhook alerts [ https://github.com/misiektoja/spotify_profile_monitor/ ]"), formatter_class=argparse.RawTextHelpFormatter
    )

    # Positional
    parser.add_argument(
        "user_id",
        nargs="?",
        metavar="SPOTIFY_USER_URI_ID",
        help="Spotify user ID, spotify:user URI or open.spotify.com profile URL",
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
        help="File suffix to append to output filenames instead of Spotify user URI ID"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        default=None,
        help="Disable logging to spotify_profile_monitor_<user_uri_id/file_suffix>.log"
    )
    opts.add_argument(
        "--debug",
        dest="debug_mode",
        action="store_true",
        default=None,
        help="Enable debug mode for technical logging"
    )
    opts.add_argument(
        "--truncate",
        dest="truncate",
        metavar="N",
        type=int,
        help="Max characters per screen line (not log), use 999 to auto-detect terminal width, ignored if -d is set"
    )

    args = parser.parse_args()

    if args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = find_config_file(CLI_CONFIG_PATH)

    if not cfg_path and CLI_CONFIG_PATH:
        print(f"* Error: Config file '{CLI_CONFIG_PATH}' does not exist")
        sys.exit(1)

    if cfg_path:
        try:
            with open(cfg_path, "r") as cf:
                exec(cf.read(), globals())
        except Exception as e:
            print(f"* Error loading config file '{cfg_path}': {e}")
            sys.exit(1)
        else:
            debug_print(f"Loaded configuration from: {cfg_path}")

    target_free_mode = any((args.set_sp_dc, args.set_webhook_url, args.send_test_email, args.send_test_webhook, args.list_tracks_for_playlist, args.list_liked_tracks, args.search_username, args.login_request_body_file, args.clienttoken_request_body_file))
    try:
        if args.user_id is not None or not target_free_mode:
            args.user_id = resolve_target_user_id(args.user_id, TARGET_USER_URI_ID)
    except ValueError as exc:
        print(f"* Error: {exc}")
        sys.exit(1)

    if not args.user_id and not target_free_mode:
        print("* Error: Spotify target is required. Provide a raw user ID, spotify:user URI or profile URL or set TARGET_USER_URI_ID.")
        sys.exit(1)

    if args.debug_mode is not None:
        DEBUG_MODE = args.debug_mode
        debug_print(f"CLI override: DEBUG_MODE={DEBUG_MODE}")

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        try:
            from dotenv import load_dotenv, find_dotenv

            if DOTENV_FILE:
                env_path = DOTENV_FILE
                if not os.path.isfile(env_path):
                    print(f"* Warning: dotenv file '{env_path}' does not exist\n")
                else:
                    load_dotenv(env_path, override=True)
                    debug_print(f"Loaded dotenv file: {env_path}")
            else:
                env_path = find_dotenv() or None
                if env_path:
                    load_dotenv(env_path, override=True)
                    debug_print(f"Auto-discovered and loaded dotenv file: {env_path}")
        except ImportError:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            if env_path:
                print(f"* Warning: Cannot load dotenv file '{env_path}' because 'python-dotenv' is not installed\n\nTo install it, run:\n    pip install python-dotenv\n\nOnce installed, re-run this tool\n")

    if env_path:
        for secret in SECRET_KEYS:
            val = os.getenv(secret)
            if val is not None:
                globals()[secret] = val

    if args.set_sp_dc:
        try:
            run_set_sp_dc(env_file=DOTENV_FILE or None)
        except SpDcConfigurationError as exc:
            print(f"* Error: {sanitize_error_text(exc)}")
            sys.exit(1)
        sys.exit(0)

    if args.set_webhook_url:
        try:
            run_set_webhook_url(env_file=DOTENV_FILE or None, config_path=cfg_path)
        except WebhookConfigurationError as exc:
            print(f"* Error: {sanitize_error_text(exc)}")
            sys.exit(1)
        sys.exit(0)

    apply_webhook_cli_overrides(args, parser)

    if (EMAIL_IMAGES or NTFY_IMAGES) and not NOTIFICATION_IMAGES_AVAILABLE:
        print("* Warning: Pillow is not installed, so email and ntfy artwork attachments are disabled for this run")
        EMAIL_IMAGES = False
        NTFY_IMAGES = False

    if args.send_test_webhook:
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

        clear_screen(CLEAR_SCREEN)

        print(f"Spotify Profile Monitoring Tool v{VERSION}\n")

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
            print("* Error: Cannot detect local timezone.")
            print("* Hint: This can happen if the optional 'tzlocal' library is missing. Install it with: pip install tzlocal")
            print("* Or set LOCAL_TIMEZONE to your local timezone manually.")
            sys.exit(1)
    else:
        if not is_valid_timezone(LOCAL_TIMEZONE):
            print(f"* Error: Configured LOCAL_TIMEZONE '{LOCAL_TIMEZONE}' is not valid. Please use a valid pytz timezone name.")
            sys.exit(1)

    if args.token_source:
        TOKEN_SOURCE = args.token_source

    if not TOKEN_SOURCE:
        TOKEN_SOURCE = "cookie"
    debug_print(f"Effective TOKEN_SOURCE={TOKEN_SOURCE}")

    if TOKEN_SOURCE == "cookie":
        ALARM_TIMEOUT = int((TOKEN_MAX_RETRIES * TOKEN_RETRY_TIMEOUT) + 5)

    try:
        import pyotp
    except ModuleNotFoundError:
        raise SystemExit("Error: Couldn't find the pyotp library !\n\nTo install it, run:\n    pip install pyotp\n\nOnce installed, re-run this tool")

    # spotipy is required when oauth_app is the selected token source
    if TOKEN_SOURCE == "oauth_app":
        try:
            from spotipy.oauth2 import SpotifyClientCredentials
        except ModuleNotFoundError:
            raise SystemExit("Error: Couldn't find the spotipy library !\n\nTo install it, run:\n    pip install spotipy\n\nOnce installed, re-run this tool")

    if TOKEN_SOURCE == "oauth_user":
        try:
            from spotipy.oauth2 import SpotifyOAuth
        except ModuleNotFoundError:
            raise SystemExit("Error: Couldn't find the spotipy library !\n\nTo install it, run:\n    pip install spotipy\n\nOnce installed, re-run this tool")

    if args.user_agent:
        USER_AGENT = args.user_agent
        debug_print("Using USER_AGENT from CLI argument")

    if not USER_AGENT:
        if TOKEN_SOURCE == "client":
            USER_AGENT = get_random_spotify_user_agent()
        else:
            USER_AGENT = get_random_user_agent()
        debug_print(f"Generated USER_AGENT for source={TOKEN_SOURCE}: {USER_AGENT}")
    else:
        debug_print("Using USER_AGENT from config/environment")

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

    if args.check_interval:
        SPOTIFY_CHECK_INTERVAL = args.check_interval
        LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / SPOTIFY_CHECK_INTERVAL

    if args.error_interval:
        SPOTIFY_ERROR_INTERVAL = args.error_interval

    # Allow providing optional oauth_app credentials for the selected source or legacy playlist fallback
    if args.oauth_app_creds:
        try:
            SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET = args.oauth_app_creds.split(":")
        except ValueError:
            print("* Error: -r / --oauth-app-creds has invalid format - use SP_APP_CLIENT_ID:SP_APP_CLIENT_SECRET")
            sys.exit(1)

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
                    print(f"* Error: Protobuf file ({LOGIN_REQUEST_BODY_FILE}) cannot be processed: {e}")
                    sys.exit(1)
                else:
                    if not args.user_id and not args.list_tracks_for_playlist and not args.search_username and not args.user_profile_details and not args.recently_played_artists and not args.followers_and_followings and not args.list_liked_tracks and login_request_body_file_param:
                        print(f"* Login data correctly read from Protobuf file ({LOGIN_REQUEST_BODY_FILE}):")
                        print(" - Device ID:\t\t", DEVICE_ID)
                        print(" - System ID:\t\t", SYSTEM_ID)
                        print(" - User URI ID:\t\t", USER_URI_ID)
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
                    print(f"* Error: Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}) cannot be processed: {e}")
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
                print(f"Warning: wrong USER_AGENT defined, reverting to the default one for APP_VERSION: {e}")
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
            print(f"* Error: CSV file cannot be opened for writing: {e}")
            sys.exit(1)

    if args.export_all_playlists:
        if not args.user_profile_details:
            print("Error: --export-all-playlists requires -i / --show-user-profile flag !")
            sys.exit(1)
        try:
            import pathvalidate
        except ModuleNotFoundError:
            raise SystemExit("Error: Couldn't find the pathvalidate library required for --export-all-playlists !\n\nTo install it, run:\n    pip install pathvalidate\n\nOnce installed, re-run this tool")
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
            if 'Not Found' in str(e) or '400 Client' in str(e):
                print(f"* Error: Playlist does not exist or is set to private: {e}")
            else:
                print(f"* Error: {e}")
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
                print(f"* Error: Playlist does not exist or is set to private: {e}")
            else:
                print(f"* Error: {e}")
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
            print(f"* Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if not args.user_id:
        print("* Error: SPOTIFY_USER_URI_ID argument is required !")
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
                    print(f"* Error: {e}")
            else:
                print(f"* Error: {e}")
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
                    print(f"* Error: {e}")
            else:
                print(f"* Error: {e}")
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
                    print(f"* Error: {e}")
            else:
                print(f"* Error: {e}")
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
            print(f"* Error: File with playlists to ignore cannot be opened: {e}")
            sys.exit(1)
    else:
        playlists_to_skip = []

    if args.file_suffix:
        FILE_SUFFIX = str(args.file_suffix)
    else:
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
                print(f"Error: Cannot determine terminal screen width: {e}")
                sys.exit(1)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    if not DISABLE_LOGGING:
        log_path = Path(os.path.expanduser(SP_LOGFILE))
        if log_path.parent != Path('.'):
            if log_path.suffix == "":
                log_path = log_path.parent / f"{log_path.name}_{FILE_SUFFIX}.log"
        else:
            if log_path.suffix == "":
                log_path = Path(f"{log_path.name}_{FILE_SUFFIX}.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        FINAL_LOG_PATH = str(log_path)
        sys.stdout = Logger(FINAL_LOG_PATH)
    else:
        FINAL_LOG_PATH = None

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

    print(f"* Spotify polling intervals:\t[check: {display_time(SPOTIFY_CHECK_INTERVAL)}] [error: {display_time(SPOTIFY_ERROR_INTERVAL)}]")
    for notification_summary_line in _startup_notification_summary_lines():
        print(notification_summary_line)
    print(f"* Token source:\t\t\t{TOKEN_SOURCE}")
    print(f"* Playlist backend:\t\t{spotify_get_playlist_backend_description()}")
    print(f"* Profile pic changes:\t\t{DETECT_CHANGED_PROFILE_PIC}")
    print(f"* Playlist changes:\t\t{DETECT_CHANGES_IN_PLAYLISTS}")
    print(f"* All public playlists:\t\t{GET_ALL_PLAYLISTS}")
    # print(f"* User agent:\t\t\t{USER_AGENT}")
    print(f"* Liveness check:\t\t{bool(LIVENESS_CHECK_INTERVAL)}" + (f" ({display_time(LIVENESS_CHECK_INTERVAL)})" if LIVENESS_CHECK_INTERVAL else ""))
    print(f"* CSV logging enabled:\t\t{bool(CSV_FILE)}" + (f" ({CSV_FILE})" if CSV_FILE else ""))
    print(f"* Ignore Spotify playlists:\t{IGNORE_SPOTIFY_PLAYLISTS}")
    print(f"* Ignore listed playlists:\t{bool(PLAYLISTS_TO_SKIP_FILE)}" + (f" ({PLAYLISTS_TO_SKIP_FILE})" if PLAYLISTS_TO_SKIP_FILE else ""))
    print(f"* Display profile pics:\t\t{bool(imgcat_exe)}" + (f" (via {imgcat_exe})" if imgcat_exe else ""))
    print(f"* Output logging enabled:\t{not DISABLE_LOGGING}" + (f" ({FINAL_LOG_PATH})" if not DISABLE_LOGGING else ""))
    print(f"* Debug mode:\t\t\t{DEBUG_MODE}")
    if not DISABLE_LOGGING and TRUNCATE_CHARS > 0:
        print(f"* Truncate terminal lines:\t{TRUNCATE_CHARS} chars")
    if TOKEN_SOURCE == 'oauth_user':
        print(f"* Spotify token cache file:\t{SP_USER_TOKENS_FILE if SP_USER_TOKENS_FILE else 'None (memory only)'}")
    elif TOKEN_SOURCE == 'oauth_app':
        print(f"* Spotify token cache file:\t{SP_APP_TOKENS_FILE if SP_APP_TOKENS_FILE else 'None (memory only)'}")
    elif TOKEN_SOURCE in {'cookie', 'client'} and spotify_has_oauth_app_credentials():
        print(f"* Spotify OAuth cache file:\t{SP_APP_TOKENS_FILE if SP_APP_TOKENS_FILE else 'None (memory only)'}")
    print(f"* Configuration file:\t\t{cfg_path}")
    print(f"* Dotenv file:\t\t\t{env_path or 'None'}")
    print(f"* Local timezone:\t\t{LOCAL_TIMEZONE}\n")

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

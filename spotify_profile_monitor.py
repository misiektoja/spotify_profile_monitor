#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v2.2

OSINT tool implementing real-time tracking of Spotify users' activities and profile changes:
https://github.com/misiektoja/spotify_profile_monitor/

Python pip3 requirements:

python-dateutil
pytz
tzlocal
requests
urllib3
pyotp
"""

VERSION = "2.2"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Log in to Spotify web client (https://open.spotify.com/) and put the value of sp_dc cookie below
# Alternatively, you can use the -u parameter to provide it at runtime
# The sp_dc cookie is typically valid for up to 1 year
# Tip: use the web browser dev console or "Cookie-Editor" by cgagnier (available for all major browsers) to extract it easily: https://cookie-editor.com/
SP_DC_COOKIE = "your_sp_dc_cookie_value"

# SMTP settings for sending email notifications
# If left as-is, no notifications will be sent
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# How often to check for user profile changes; in seconds
# Can also be set using the -c parameter
SPOTIFY_CHECK_INTERVAL = 1800  # 30 mins

# Retry interval after errors; in seconds
# Can also be set using the -m parameter
SPOTIFY_ERROR_INTERVAL = 300  # 5 mins

# Set your local time zone so that Spotify timestamps are converted accordingly (e.g. 'Europe/Warsaw').
# Use this command to list all time zones supported by pytz:
# python3 -c "import pytz; print('\n'.join(pytz.all_timezones))"
# If set to 'Auto', the tool will try to detect your local time zone automatically
LOCAL_TIMEZONE = 'Auto'

# Notify when the user's profile picture changes? (via console and email if -p is enabled).
# If enabled, the current profile picture is saved as:
#   - spotify_profile_{user_uri_id/file_suffix}_pic.jpeg (initial)
#   - spotify_profile_{user_uri_id/file_suffix}_pic_YYmmdd_HHMM.jpeg (on change)
# The binary JPEGs are compared to detect changes
# It is enabled by default, can be disabled by using -j parameter
DETECT_CHANGED_PROFILE_PIC = True

# If you have 'imgcat' installed, you can set its path below to display profile pictures directly in your terminal
# Leave empty to disable this feature
# IMGCAT_PATH = "/usr/local/bin/imgcat"
IMGCAT_PATH = ""

# SHA256 hash needed to search for Spotify users (used with -s)
# Intercept traffic when using search in the Spotify client, look for requests with searchUsers or searchDesktop operation name
# Extract the "sha256Hash" from the request
# Example request:
# https://api-partner.spotify.com/pathfinder/v1/query?operationName=searchUsers&variables={"searchTerm":"user_uri_id","offset":0,"limit":5,"numberOfTopResults":5,"includeAudiobooks":false}&extensions={"persistedQuery":{"version":1,"sha256Hash":"XXXXXXXXXX"}}
# You are interested in the string marked as "XXXXXXXXXX" here
SP_SHA256 = "your_spotify_client_sha256"

# Notify when user's public playlists change? (via console and email if -p is enabled)
# Detects:
#   - added/removed tracks
#   - name or description changes
#   - number of likes
#   - collaborators
# It is enabled by default, can be disabled by using -q parameter
# This option also affects behavior when using -i
DETECT_CHANGES_IN_PLAYLISTS = True

# Max number of public playlists (owned by the user) to monitor
PLAYLISTS_LIMIT = 50

# Max number of recently played artists to show (when using -a)
RECENTLY_PLAYED_ARTISTS_LIMIT = 50

# Max number of recently played artists to show (when using -i)
RECENTLY_PLAYED_ARTISTS_LIMIT_INFO = 15

# By default, only public playlists owned by the user are fetched
# Set to True to include all public playlists on their profile (e.g. created by others, but added to the profile)
# Can also be set with the -k parameter
GET_ALL_PLAYLISTS = False

# How often to print an "alive check" message to the output; in seconds
TOOL_ALIVE_INTERVAL = 21600  # 6 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://api.spotify.com/v1'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# Base name of the log file. The tool will save its output to spotify_profile_monitor_{user_uri_id/file_suffix}.log file
SP_LOGFILE = "spotify_profile_monitor"

# Value used by signal handlers to increase or decrease profile check interval (SPOTIFY_CHECK_INTERVAL); in seconds
SPOTIFY_CHECK_SIGNAL_VALUE = 300  # 5 minutes

# Maximum number of attempts to get a valid access token in a single run of the spotify_get_access_token() function
TOKEN_MAX_RETRIES = 10

# Interval between access token retry attempts; in seconds
TOKEN_RETRY_TIMEOUT = 0.5  # 0.5 second

# Whether to enable / disable SSL certificate verification while sending https requests
VERIFY_SSL = True

# Ignore Spotify-owned playlists when monitoring?
# Set to True to avoid tracking Spotify-generated playlists that often change frequently (likes, tracks etc.)
IGNORE_SPOTIFY_PLAYLISTS = True

# Format used when exporting playlists (-l) or liked songs (-x) to CSV file:
# 1 - default format used for activity logging ['Date', 'Type', 'Name', 'Old', 'New']
# 2 - playlist dump format ['Date', 'Playlist Name', 'Artist', 'Track']
CSV_FILE_FORMAT_EXPORT = 2

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Strings removed from track names for generating proper Genius search URLs
re_search_str = r'remaster|extended|original mix|remix|original soundtrack|radio( |-)edit|\(feat\.|( \(.*version\))|( - .*version)'
re_replace_str = r'( - (\d*)( )*remaster$)|( - (\d*)( )*remastered( version)*( \d*)*.*$)|( \((\d*)( )*remaster\)$)|( - (\d+) - remaster$)|( - extended$)|( - extended mix$)|( - (.*); extended mix$)|( - extended version$)|( - (.*) remix$)|( - remix$)|( - remixed by .*$)|( - original mix$)|( - .*original soundtrack$)|( - .*radio( |-)edit$)|( \(feat\. .*\)$)|( \(\d+.*Remaster.*\)$)|( \(.*Version\))|( - .*version)'

# Default value for network-related timeouts in functions; in seconds
FUNCTION_TIMEOUT = 15

# Default value for alarm signal handler timeout; in seconds
ALARM_TIMEOUT = int((TOKEN_MAX_RETRIES * TOKEN_RETRY_TIMEOUT) + 5)
ALARM_RETRY = 10

# Sometimes Spotify API has issues and returns info that all user's playlists disappeared
# We won't notify about such event right away, but only during PLAYLISTS_DISAPPEARED_COUNTER attempt (next check interval)
PLAYLISTS_DISAPPEARED_COUNTER = 2

# Variables for caching functionality of the Spotify access token to avoid unnecessary refreshing
SP_CACHED_ACCESS_TOKEN = None
SP_TOKEN_EXPIRES_AT = 0
SP_CACHED_CLIENT_ID = ""
SP_CACHED_USER_AGENT = ""

# URL of the Spotify Web Player endpoint to get access token
TOKEN_URL = "https://open.spotify.com/get_access_token"

# URL of the endpoint to get server time needed to create TOTP object
SERVER_TIME_URL = "https://open.spotify.com/server-time"

# Width of horizontal line (─)
HORIZONTAL_LINE = 113

# Cache for playlist info to avoid redundant API calls
PLAYLIST_INFO_CACHE = {}

# Cache TTL for playlist info
PLAYLIST_INFO_CACHE_TTL = (SPOTIFY_CHECK_INTERVAL * 2 if SPOTIFY_CHECK_INTERVAL > 43200 else 43200)  # 12h

# Tracks temporarily glitched playlists to suppress false alerts
GLITCH_CACHE = {}

TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / SPOTIFY_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Type', 'Name', 'Old', 'New']
csvfieldnames_export = ['Date', 'Playlist Name', 'Artist', 'Track']

profile_notification = False
followers_followings_notification = True
file_suffix = ""

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"


import sys
import time
from time import time_ns
import string
import json
import os
from datetime import datetime, timezone
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
import pytz
try:
    from tzlocal import get_localzone
except ImportError:
    get_localzone = None
import platform
import html
from urllib.parse import quote_plus, quote, urlparse
import re
import ipaddress
from itertools import zip_longest
from html import escape
import subprocess
import pyotp
import base64
import random
from collections import Counter
from email.utils import parsedate_to_datetime

import urllib3
if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SESSION = req.Session()

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry = Retry(
    total=5,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD", "OPTIONS"],
    raise_on_status=False
)

adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
SESSION.mount("https://", adapter)
SESSION.mount("http://", adapter)


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.logfile.write(message)
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
        pass


# Class used to generate timeout exceptions
class TimeoutException(Exception):
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
        _ = req.get(url, timeout=timeout, verify=verify)
        return True
    except req.RequestException as e:
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
def send_email(subject, body, body_html, use_ssl, image_file="", image_name="image1", smtp_timeout=15):
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
        print("Error sending email - SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD variables)")
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
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] = str(Header(subject, 'utf-8'))

        if body:
            part1 = MIMEText(body, 'plain')
            part1 = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
            email_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            part2 = MIMEText(body_html.encode('utf-8'), 'html', _charset='utf-8')
            email_msg.attach(part2)

        if image_file:
            with open(image_file, 'rb') as fp:
                img_part = MIMEImage(fp.read())
            img_part.add_header('Content-ID', f'<{image_name}>')
            email_msg.attach(img_part)

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtpObj.quit()
    except Exception as e:
        print(f"Error sending email: {e}")
        return 1
    return 0


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

    except Exception:
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
    return (f'{ts_str}{calendar.day_abbr[(now_local_naive()).weekday()]}, {now_local_naive().strftime("%d %b %Y, %H:%M:%S")}')


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
    global profile_notification
    profile_notification = not profile_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications:\t\t[profile changes = {profile_notification}]")
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


# Returns Apple & Genius search URLs for specified track
def get_apple_genius_search_urls(artist, track):
    genius_search_string = f"{artist} {track}"
    youtube_music_search_string = quote_plus(f"{artist} {track}")
    if re.search(re_search_str, genius_search_string, re.IGNORECASE):
        genius_search_string = re.sub(re_replace_str, '', genius_search_string, flags=re.IGNORECASE)
    apple_search_string = quote(f"{artist} {track}")
    apple_search_url = f"https://music.apple.com/pl/search?term={apple_search_string}"
    genius_search_url = f"https://genius.com/search?q={quote_plus(genius_search_string)}"
    youtube_music_search_url = f"https://music.youtube.com/search?q={youtube_music_search_string}"
    return apple_search_url, genius_search_url, youtube_music_search_url


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


# Removes spaces from a hex string and converts it into a corresponding bytes object
def hex_to_bytes(data: str) -> bytes:
    data = data.replace(" ", "")
    return bytes.fromhex(data)


# Creates a TOTP object using a secret derived from transformed cipher bytes
def generate_totp(ua: str):
    secret_cipher_bytes = [
        12, 56, 76, 33, 88, 44, 88, 33,
        78, 78, 11, 66, 22, 22, 55, 69, 54,
    ]

    transformed = [e ^ ((t % 33) + 9) for t, e in enumerate(secret_cipher_bytes)]
    joined = "".join(str(num) for num in transformed)
    utf8_bytes = joined.encode("utf-8")
    hex_str = "".join(format(b, 'x') for b in utf8_bytes)
    secret_bytes = hex_to_bytes(hex_str)
    secret = base64.b32encode(secret_bytes).decode().rstrip('=')

    headers = {
        "Host": "open.spotify.com",
        "User-Agent": ua,
        "Accept": "*/*",
    }

    try:
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)
        resp = req.get(SERVER_TIME_URL, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    except (req.RequestException, TimeoutException) as e:
        raise Exception(f"generate_totp() network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

    resp.raise_for_status()

    json_data = resp.json()
    server_time = json_data.get("serverTime")

    if server_time is None:
        raise Exception("Failed to get server time")

    totp_obj = pyotp.TOTP(secret, digits=6, interval=30)

    return totp_obj, server_time


# Sends a lightweight request to check Spotify token validity
def check_token_validity(token: str, client_id: str, user_agent: str) -> bool:
    url = "https://api.spotify.com/v1/me"
    headers = {
        "Authorization": f"Bearer {token}",
        "Client-Id": client_id,
        "User-Agent": user_agent,
    }

    if platform.system() != 'Windows':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT + 2)
    try:
        response = req.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        valid = response.status_code == 200
    except Exception:
        valid = False
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)
    return valid


# Retrieves a new Spotify access token using the sp_dc cookie, tries first with mode "transport" and if needed with "init"
def refresh_token(sp_dc: str) -> dict:
    transport = True
    init = True
    session = req.Session()
    session.cookies.set("sp_dc", sp_dc)
    data: dict = {}
    token = ""

    ua = get_random_user_agent()
    totp_obj, server_time = generate_totp(ua)
    client_time = int(time_ns() / 1000 / 1000)
    otp_value = totp_obj.at(server_time)

    params = {
        "reason": "transport",
        "productType": "web-player",
        "totp": otp_value,
        "totpServer": otp_value,
        "totpVer": 5,
        "sTime": server_time,
        "cTime": client_time,
    }

    headers = {
        "User-Agent": ua,
        "Accept": "application/json",
        "Cookie": f"sp_dc={sp_dc}",
    }

    try:
        if platform.system() != "Windows":
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)

        response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        data = response.json()
        token = data.get("accessToken", "")

    except (req.RequestException, TimeoutException, req.HTTPError, ValueError):
        transport = False
    finally:
        if platform.system() != "Windows":
            signal.alarm(0)

    if not transport or (transport and not check_token_validity(token, data.get("clientId", ""), ua)):
        params["reason"] = "init"

        try:
            if platform.system() != "Windows":
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(FUNCTION_TIMEOUT + 2)

            response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
            response.raise_for_status()
            data = response.json()
            token = data.get("accessToken", "")

        except (req.RequestException, TimeoutException, req.HTTPError, ValueError):
            init = False
        finally:
            if platform.system() != "Windows":
                signal.alarm(0)

    if not init or not data or "accessToken" not in data:
        raise Exception("refresh_token(): Unsuccessful token request")

    return {
        "access_token": token,
        "expires_at": data["accessTokenExpirationTimestampMs"] // 1000,
        "client_id": data.get("clientId", ""),
        "user_agent": ua,
        "length": len(token)
    }


# Fetches Spotify access token based on provided SP_DC value
def spotify_get_access_token(sp_dc: str):
    global SP_CACHED_ACCESS_TOKEN, SP_TOKEN_EXPIRES_AT, SP_CACHED_CLIENT_ID, SP_CACHED_USER_AGENT

    now = time.time()

    if SP_CACHED_ACCESS_TOKEN and now < SP_TOKEN_EXPIRES_AT and check_token_validity(SP_CACHED_ACCESS_TOKEN, SP_CACHED_CLIENT_ID, SP_CACHED_USER_AGENT):
        return SP_CACHED_ACCESS_TOKEN

    max_retries = TOKEN_MAX_RETRIES
    retry = 0

    while retry < max_retries:
        token_data = refresh_token(sp_dc)
        token = token_data["access_token"]
        client_id = token_data.get("client_id", "")
        user_agent = token_data.get("user_agent", get_random_user_agent())
        length = token_data["length"]

        SP_CACHED_ACCESS_TOKEN = token
        SP_TOKEN_EXPIRES_AT = token_data["expires_at"]
        SP_CACHED_CLIENT_ID = client_id
        SP_CACHED_USER_AGENT = user_agent

        if SP_CACHED_ACCESS_TOKEN is None or not check_token_validity(SP_CACHED_ACCESS_TOKEN, SP_CACHED_CLIENT_ID, SP_CACHED_USER_AGENT):
            retry += 1
            time.sleep(TOKEN_RETRY_TIMEOUT)
        else:
            # print("* Token is valid")
            break

    # print("Spotify Access Token:", SP_CACHED_ACCESS_TOKEN)
    # print("Token expires at:", time.ctime(SP_TOKEN_EXPIRES_AT))

    if retry == max_retries:
        if SP_CACHED_ACCESS_TOKEN is not None:
            print(f"* Token appears to be still invalid after {max_retries} attempts, returning token anyway")
            print_cur_ts("Timestamp:\t\t\t")
            return SP_CACHED_ACCESS_TOKEN
        else:
            raise RuntimeError(f"Failed to obtain a valid Spotify access token after {max_retries} attempts")

    return SP_CACHED_ACCESS_TOKEN


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


# Converts Spotify URI (e.g. spotify:user:username) to URL (e.g. https://open.spotify.com/user/username)
def spotify_convert_uri_to_url(uri):
    # add si parameter so link opens in native Spotify app after clicking
    si = "?si=1"
    # si=""

    url = ""
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

    uri = ""

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


# Gets basic information about access token owner
def spotify_get_current_user(access_token) -> dict | None:
    url = "https://api.spotify.com/v1/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": SP_CACHED_CLIENT_ID,
        "User-Agent": SP_CACHED_USER_AGENT,
    }

    if platform.system() != 'Windows':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT + 2)
    try:
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        data = response.json()

        user_info = {
            "display_name": data.get("display_name"),
            "uri": data.get("uri"),
            "is_premium": data.get("product") == "premium",
            "country": data.get("country"),
            "email": data.get("email"),
            "spotify_url": data.get("external_urls", {}).get("spotify") + "?si=1" if data.get("external_urls", {}).get("spotify") else None
        }

        return user_info
    except Exception as e:
        print(f"* Error: {e}")
        return None
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)


# Checks if a playlist has been completely removed and/or set as private
def is_playlist_private(access_token, playlist_uri):
    playlist_id = playlist_uri.split(':', 2)[2]
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}?fields=id"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": SP_CACHED_CLIENT_ID,
        "User-Agent": SP_CACHED_USER_AGENT,
    }

    try:
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        if response.status_code == 404:
            return True
        return False
    except Exception:
        return False


# Returns detailed info about playlist with specified URI (with possibility to get its tracks as well)
def spotify_get_playlist_info(access_token, playlist_uri, get_tracks):
    playlist_id = playlist_uri.split(':', 2)[2]

    if get_tracks:
        url1 = f"https://api.spotify.com/v1/playlists/{playlist_id}?fields=name,description,owner,followers,external_urls,tracks.total,collaborative"
        url2 = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?fields=next,total,items(added_at,track(name,uri,duration_ms),added_by),items(track(artists(name,uri)))"
    else:
        url1 = f"https://api.spotify.com/v1/playlists/{playlist_id}?fields=name,description,owner,followers,external_urls,tracks.total"
        url2 = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?fields=next,total,items(added_at)"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": SP_CACHED_CLIENT_ID,
        "User-Agent": SP_CACHED_USER_AGENT,
    }
    # add si parameter so link opens in native Spotify app after clicking
    si = "?si=1"

    try:
        response1 = SESSION.get(url1, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response1.raise_for_status()
        json_response1 = response1.json()

        sp_playlist_tracks_concatenated_list = []
        next_url = url2
        while next_url:
            response2 = SESSION.get(next_url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
            response2.raise_for_status()
            json_response2 = response2.json()
            # print(json.dumps(json_response2))

            for track in json_response2.get("items"):
                sp_playlist_tracks_concatenated_list.append(track)

            next_url = json_response2.get("next")

        sp_playlist_name = json_response1.get("name", "")

        # we fetch collaborative field for the future, for now it is always set to false by Spotify as a countermeasure against finding collaborative playlists by scraping
        sp_playlist_collaborative = json_response1.get("collaborative", "")

        sp_playlist_description = json_response1.get("description", "")
        sp_playlist_owner = json_response1["owner"].get("display_name", "")
        sp_playlist_owner_uri = json_response1["owner"].get("uri", "")
        sp_playlist_owner_url = json_response1["owner"]["external_urls"].get("spotify")

        sp_playlist_tracks = sp_playlist_tracks_concatenated_list

        sp_playlist_tracks_count = sp_playlist_tracks_count_before_filtering = json_response1["tracks"].get("total", 0)
        if sp_playlist_tracks:
            sp_playlist_tracks_count_before_filtering_tmp = len(sp_playlist_tracks)
            if sp_playlist_tracks_count_before_filtering_tmp > 0:
                sp_playlist_tracks_count_before_filtering = sp_playlist_tracks_count_before_filtering_tmp

        # filtering of unavailable tracks for example due to copyright issues
        sp_playlist_tracks = [t for t in (sp_playlist_tracks or []) if t.get("track") and t["track"].get("artists", [{}])[0].get("name", "") and t["track"].get("name", "") and int(t["track"].get("duration_ms", 0)) >= 1000]

        if sp_playlist_tracks:
            sp_playlist_tracks_count_tmp = len(sp_playlist_tracks)
            if sp_playlist_tracks_count_tmp > 0:
                sp_playlist_tracks_count = sp_playlist_tracks_count_tmp

        sp_playlist_followers_count = int(json_response1["followers"].get("total", 0))
        sp_playlist_url = json_response1["external_urls"].get("spotify") + si

        return {"sp_playlist_name": sp_playlist_name, "sp_playlist_collaborative": sp_playlist_collaborative, "sp_playlist_description": sp_playlist_description, "sp_playlist_owner": sp_playlist_owner, "sp_playlist_owner_url": sp_playlist_owner_url, "sp_playlist_tracks_count": sp_playlist_tracks_count, "sp_playlist_tracks_count_before_filtering": sp_playlist_tracks_count_before_filtering, "sp_playlist_tracks": sp_playlist_tracks, "sp_playlist_followers_count": sp_playlist_followers_count, "sp_playlist_url": sp_playlist_url, "sp_playlist_owner_uri": sp_playlist_owner_uri}

    except Exception:
        raise


# Returns detailed info about user with specified URI
def spotify_get_user_info(access_token, user_uri_id, get_playlists, recently_played_limit):
    if get_playlists:
        url = f"https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user_uri_id}?playlist_limit={PLAYLISTS_LIMIT}&artist_limit={recently_played_limit}&episode_limit=10&market=from_token"
    else:
        url = f"https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user_uri_id}?playlist_limit=0&artist_limit={recently_played_limit}&episode_limit=10&market=from_token"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": SP_CACHED_CLIENT_ID,
        "User-Agent": SP_CACHED_USER_AGENT,
    }

    try:
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        json_response = response.json()

        sp_username = json_response.get("name", "")
        sp_user_followers_count = json_response.get("followers_count", 0)
        sp_user_show_follows = json_response.get("show_follows")
        sp_user_followings_count = json_response.get("following_count", 0)
        sp_user_image_url = json_response.get("image_url", "")

        if get_playlists:
            sp_user_public_playlists_uris = json_response.get("public_playlists", None)
            sp_user_public_playlists_count = json_response.get("total_public_playlists_count", 0)
        else:
            sp_user_public_playlists_uris = None
            sp_user_public_playlists_count = 0

        if sp_user_public_playlists_uris:
            if not GET_ALL_PLAYLISTS:
                sp_user_public_playlists_uris[:] = [d for d in sp_user_public_playlists_uris if d.get('owner_uri', "") == 'spotify:user:' + str(user_uri_id)]
            sp_user_public_playlists_count_tmp = len(sp_user_public_playlists_uris)
            if sp_user_public_playlists_count_tmp > 0:
                sp_user_public_playlists_count = sp_user_public_playlists_count_tmp
            else:
                sp_user_public_playlists_count = 0

            remove_key_from_list_of_dicts(sp_user_public_playlists_uris, 'image_url')
            remove_key_from_list_of_dicts(sp_user_public_playlists_uris, 'is_following')
            remove_key_from_list_of_dicts(sp_user_public_playlists_uris, 'name')
            remove_key_from_list_of_dicts(sp_user_public_playlists_uris, 'followers_count')

        sp_user_recently_played_artists = json_response.get("recently_played_artists")
        remove_key_from_list_of_dicts(sp_user_recently_played_artists, 'image_url')
        remove_key_from_list_of_dicts(sp_user_recently_played_artists, 'followers_count')

        return {"sp_username": sp_username, "sp_user_followers_count": sp_user_followers_count, "sp_user_show_follows": sp_user_show_follows, "sp_user_followings_count": sp_user_followings_count, "sp_user_public_playlists_count": sp_user_public_playlists_count, "sp_user_public_playlists_uris": sp_user_public_playlists_uris, "sp_user_recently_played_artists": sp_user_recently_played_artists, "sp_user_image_url": sp_user_image_url}
    except Exception:
        raise


# Returns followings for user with specified URI
def spotify_get_user_followings(access_token, user_uri_id):
    url = f"https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user_uri_id}/following?market=from_token"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": SP_CACHED_CLIENT_ID,
        "User-Agent": SP_CACHED_USER_AGENT,
    }

    try:
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
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
    url = f"https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user_uri_id}/followers?market=from_token"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": SP_CACHED_CLIENT_ID,
        "User-Agent": SP_CACHED_USER_AGENT,
    }

    try:
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
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


# Lists tracks for playlist with specified URI (-l parameter)
def spotify_list_tracks_for_playlist(sp_accessToken, playlist_url, csv_file_name, format_type=2):
    added_at_dt: datetime | None = None

    try:
        if csv_file_name:
            init_csv_file(csv_file_name, format_type)
    except Exception as e:
        print(f"* Error: {e}")

    list_operation = "* Listing & saving" if csv_file_name else "* Listing"

    print(f"{list_operation} tracks for playlist '{playlist_url}' ...\n")

    user_info = spotify_get_current_user(sp_accessToken)
    if user_info:
        print(f"Token belongs to:\t{user_info.get('display_name', '')}\n\t\t\t[ {user_info.get('spotify_url')} ]\n")

    print("─" * HORIZONTAL_LINE)

    user_id_name_mapping = {}
    user_track_counts = Counter()

    playlist_uri = spotify_convert_url_to_uri(playlist_url)

    sp_playlist_data = spotify_get_playlist_info(sp_accessToken, playlist_uri, True)

    p_name = sp_playlist_data.get("sp_playlist_name", "")
    p_descr = html.unescape(sp_playlist_data.get("sp_playlist_description", ""))
    p_owner = sp_playlist_data.get("sp_playlist_owner", "")

    print(f"Playlist '{p_name}' owned by '{p_owner}':\n")

    p_likes = sp_playlist_data.get("sp_playlist_followers_count", 0)
    p_tracks = sp_playlist_data.get("sp_playlist_tracks_count", 0)
    p_tracks_before_filtering = sp_playlist_data.get("sp_playlist_tracks_count_before_filtering", 0)
    p_tracks_list = sp_playlist_data.get("sp_playlist_tracks", None)
    added_at_ts_lowest = 0
    added_at_ts_highest = 0
    duration_sum = 0
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
            added_by_id = added_by.get("id", "") or "Spotify"

            added_by_name = user_id_name_mapping.get(added_by_id)
            if not added_by_name:
                if added_by_id == "Spotify":
                    added_by_name = "Spotify"
                else:
                    sp_user_data = spotify_get_user_info(sp_accessToken, added_by_id, False, 0)
                    added_by_name = sp_user_data.get("sp_username", added_by_id)

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
                artist_track = artist_track[:75]
                line_new = '%75s    %20s    %3s     %10s' % (artist_track, added_at_dt_str, added_at_dt_week_day, added_by_name)
                print(line_new)

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, convert_to_local_naive(added_at_dt), *(("Added Track", p_name, added_by_name, artist_track) if format_type == 1 else ("", p_name, p_artist, p_track)), format_type)
                except Exception as e:
                    print(f"* Error: {e}")

    print(f"\nName:\t\t\t'{p_name}'")
    if p_descr:
        print(f"Description:\t\t'{p_descr}'")

    songs_display = f"{p_tracks} ({p_tracks_before_filtering - p_tracks} filtered out)" if p_tracks_before_filtering > p_tracks else f"{p_tracks}"

    print(f"URL:\t\t\t{playlist_url}\nSongs:\t\t\t{songs_display}\nLikes:\t\t\t{p_likes}")

    if added_at_ts_lowest > 0:
        p_creation_date = get_date_from_ts(int(added_at_ts_lowest))
        p_creation_date_since = calculate_timespan(int(time.time()), int(added_at_ts_lowest))
        print(f"Creation date:\t\t{p_creation_date} ({p_creation_date_since} ago)")

    if added_at_ts_highest > 0:
        p_last_track_date = get_date_from_ts(int(added_at_ts_highest))
        p_last_track_date_since = calculate_timespan(int(time.time()), int(added_at_ts_highest))
        print(f"Last update:\t\t{p_last_track_date} ({p_last_track_date_since} ago)")

    print(f"Duration:\t\t{display_time(duration_sum)}")

    total_tracks = sum(user_track_counts.values())

    if len(user_id_name_mapping) > 1:

        print(f"\nCollaborators ({len(user_id_name_mapping)}):\n")

        for collab_id, collab_name in user_id_name_mapping.items():
            count = user_track_counts.get(collab_id, 0)
            percent = (count / total_tracks * 100) if total_tracks else 0
            url = spotify_convert_uri_to_url(f"spotify:user:{collab_id}")
            print(f"- {collab_name} [songs: {count}, {percent:.1f}%] [URL: {url}]")


# Returns detailed information about tracks liked by the user owning the access token
def spotify_get_user_liked_tracks(access_token):
    url = f"https://api.spotify.com/v1/me/tracks?fields=next,total,items(added_at,track(name,uri,duration_ms),added_by),items(track(artists(name,uri)))"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": SP_CACHED_CLIENT_ID,
        "User-Agent": SP_CACHED_USER_AGENT,
    }

    try:
        sp_playlist_tracks_concatenated_list = []
        json_response: dict = {}
        next_url = url

        while next_url:
            response = SESSION.get(next_url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
            response.raise_for_status()
            json_response = response.json()
            # print(json.dumps(json_response, indent=2, sort_keys=True))

            for track in json_response.get("items", []):
                sp_playlist_tracks_concatenated_list.append(track)

            next_url = json_response.get("next")

        sp_playlist_tracks = sp_playlist_tracks_concatenated_list

        sp_playlist_tracks_count = sp_playlist_tracks_count_before_filtering = json_response.get("total", 0)
        if sp_playlist_tracks:
            sp_playlist_tracks_count_before_filtering_tmp = len(sp_playlist_tracks)
            if sp_playlist_tracks_count_before_filtering_tmp > 0:
                sp_playlist_tracks_count_before_filtering = sp_playlist_tracks_count_before_filtering_tmp

        # filtering of unavailable tracks for example due to copyright issues
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

    list_operation = "* Listing & saving" if csv_file_name else "* Listing"

    print(f"{list_operation} liked tracks by the user owning the token ...\n")

    user_info = spotify_get_current_user(sp_accessToken)
    if user_info:
        username = user_info.get("display_name", "")
        print(f"Token belongs to:\t{username}\n\t\t\t[ {user_info.get('spotify_url')} ]\n")

    print("─" * HORIZONTAL_LINE)

    sp_playlist_data = spotify_get_user_liked_tracks(sp_accessToken)

    p_tracks = sp_playlist_data.get("sp_playlist_tracks_count", 0)
    p_tracks_before_filtering = sp_playlist_data.get("sp_playlist_tracks_count_before_filtering", 0)
    p_tracks_list = sp_playlist_data.get("sp_playlist_tracks", None)
    added_at_ts_lowest = 0
    added_at_ts_highest = 0
    duration_sum = 0

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
                artist_track = artist_track[:75]
                line_new = '%80s    %20s    %3s' % (artist_track, added_at_dt_str, added_at_dt_week_day)
                print(line_new)
                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, convert_to_local_naive(added_at_dt), *(("Added Track", "Liked Songs", username, artist_track) if format_type == 1 else ("", "Liked Songs", p_artist, p_track)), format_type)
                except Exception as e:
                    print(f"* Error: {e}")

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


# Compares two lists of dictionaries
def compare_two_lists_of_dicts(list1: list, list2: list):
    if not list1:
        list1 = []
    if not list2:
        list2 = []

    diff = [i for i in list1 + list2 if i not in list2]
    return diff


# Searches for Spotify users (-s parameter)
def spotify_search_users(sp_accessToken, username):
    url = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=searchUsers&variables=%7B%22searchTerm%22%3A%22{username}%22%2C%22offset%22%3A0%2C%22limit%22%3A5%2C%22numberOfTopResults%22%3A5%2C%22includeAudiobooks%22%3Afalse%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{SP_SHA256}%22%7D%7D"
    headers = {
        "Authorization": f"Bearer {sp_accessToken}",
        "Client-Id": SP_CACHED_CLIENT_ID,
        "User-Agent": SP_CACHED_USER_AGENT,
    }

    print(f"* Searching for users with '{username}' string ...\n")

    user_info = spotify_get_current_user(sp_accessToken)
    if user_info:
        print(f"Token belongs to:\t{user_info.get('display_name', '')}\n\t\t\t[ {user_info.get('spotify_url')} ]\n")

    print("─" * HORIZONTAL_LINE)

    try:
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
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
    playlist_url = spotify_convert_uri_to_url(uri)
    cached = PLAYLIST_INFO_CACHE.get(uri)
    cached_name = cached.get("name") if cached and cached.get("name") else ""
    if cached_name:
        return f"{cached_name} [ {playlist_url} ]"
    else:
        return f"[ {playlist_url} ]"


# Processes items from all the provided playlists and returns a list of dictionaries
def spotify_process_public_playlists(sp_accessToken, playlists, get_tracks, playlists_to_skip=None):
    global PLAYLIST_INFO_CACHE
    list_of_playlists = []
    error_while_processing = False
    added_at_dt: datetime | None = None

    if playlists_to_skip is None:
        playlists_to_skip = []

    if playlists:
        for playlist in playlists:
            user_id_name_mapping = {}
            p_uri = ""
            if "uri" in playlist:
                list_of_tracks = []
                try:
                    p_owner = playlist.get("owner_name", "")
                    p_owner_uri = playlist.get("owner_uri", "")
                    p_uri = playlist.get("uri", "")
                    p_uri_id = spotify_extract_id_or_name(p_uri)
                    p_owner_name = spotify_extract_id_or_name(p_owner)
                    p_owner_id = spotify_extract_id_or_name(p_owner_uri)

                    # we do not get a list of tracks for playlists that are ignored
                    if (playlists_to_skip and (p_uri_id in playlists_to_skip or p_owner_id in playlists_to_skip or p_owner_name in playlists_to_skip)) or (IGNORE_SPOTIFY_PLAYLISTS and p_owner == "Spotify"):
                        effective_get_tracks = False
                    else:
                        effective_get_tracks = get_tracks

                    try:
                        sp_playlist_data = spotify_get_playlist_info(sp_accessToken, p_uri, effective_get_tracks)
                        PLAYLIST_INFO_CACHE[p_uri] = {
                            "status": "ok",
                            "timestamp": time.time(),
                            # "data": sp_playlist_data,
                            "name": sp_playlist_data.get("sp_playlist_name", "")
                        }
                    except Exception as e:
                        existing = PLAYLIST_INFO_CACHE.get(p_uri, {})
                        existing.update({
                            "status": "error",
                            "timestamp": time.time(),
                            "error": str(e)
                        })
                        PLAYLIST_INFO_CACHE[p_uri] = existing

                        print(f"* Error while processing playlist {spotify_format_playlist_reference(p_uri)}, skipping for now" + (f": {e}" if e else ""))
                        print_cur_ts("Timestamp:\t\t\t")
                        error_while_processing = True
                        continue

                    p_name = sp_playlist_data.get("sp_playlist_name", "")
                    p_descr = html.unescape(sp_playlist_data.get("sp_playlist_description", ""))
                    p_likes = sp_playlist_data.get("sp_playlist_followers_count", 0)
                    p_tracks = sp_playlist_data.get("sp_playlist_tracks_count", 0)
                    p_tracks_before_filtering = sp_playlist_data.get("sp_playlist_tracks_count_before_filtering", 0)
                    p_url = spotify_convert_uri_to_url(p_uri)
                    p_owner = sp_playlist_data.get("sp_playlist_owner", "")
                    p_owner_uri = sp_playlist_data.get("sp_playlist_owner_uri", "")

                    p_tracks_list = sp_playlist_data.get("sp_playlist_tracks", None)
                    added_at_ts_lowest = 0
                    added_at_ts_highest = 0

                    if p_tracks_list is not None:
                        for index, track in enumerate(p_tracks_list or []):
                            added_at = track.get("added_at")
                            p_artist = p_track = added_by_name = added_by_id = track_uri = ""
                            track_duration = 0

                            if effective_get_tracks:
                                track_info = track.get("track")

                                p_artist = track_info["artists"][0]["name"]
                                p_track = track_info["name"]
                                duration_ms = track_info["duration_ms"]

                                track_duration = int(str(duration_ms)[0:-3])
                                track_uri = track_info.get("uri")

                                added_by = track.get("added_by", {}) or {}
                                added_by_id = added_by.get("id", "") or "Spotify"

                                added_by_name = user_id_name_mapping.get(added_by_id)
                                if not added_by_name:
                                    if added_by_id == "Spotify":
                                        added_by_name = "Spotify"
                                    else:
                                        sp_user_data = spotify_get_user_info(sp_accessToken, added_by_id, False, 0)
                                        added_by_name = sp_user_data.get("sp_username", added_by_id)

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
                                list_of_tracks.append({"artist": p_artist, "track": p_track, "duration": track_duration, "added_at": added_at_dt, "uri": track_uri, "added_by": added_by_name, "added_by_id": added_by_id})

                except Exception as e:
                    print(f"* Unexpected error while building playlist data for: {spotify_format_playlist_reference(p_uri)}: {e}")
                    print_cur_ts("Timestamp:\t\t\t")
                    error_while_processing = True
                    continue

                p_creation_date = datetime.fromtimestamp(int(added_at_ts_lowest), pytz.timezone(LOCAL_TIMEZONE)) if added_at_ts_lowest > 0 else None
                p_last_track_date = datetime.fromtimestamp(int(added_at_ts_highest), pytz.timezone(LOCAL_TIMEZONE)) if added_at_ts_highest > 0 else None

                p_collaborators_count = len(user_id_name_mapping)

                if list_of_tracks and effective_get_tracks:
                    list_of_playlists.append({"uri": p_uri, "name": p_name, "desc": p_descr, "likes": p_likes, "tracks_count": p_tracks, "tracks_count_before_filtering": p_tracks_before_filtering, "url": p_url, "date": p_creation_date, "update_date": p_last_track_date, "list_of_tracks": list_of_tracks, "collaborators_count": p_collaborators_count, "collaborators": user_id_name_mapping, "owner": p_owner, "owner_uri": p_owner_uri})
                else:
                    list_of_playlists.append({"uri": p_uri, "name": p_name, "desc": p_descr, "likes": p_likes, "tracks_count": p_tracks, "tracks_count_before_filtering": p_tracks_before_filtering, "url": p_url, "date": p_creation_date, "update_date": p_last_track_date, "collaborators_count": p_collaborators_count, "collaborators": {}, "owner": p_owner, "owner_uri": p_owner_uri})

    return list_of_playlists, error_while_processing


# Prints detailed info about user's playlists
def spotify_print_public_playlists(list_of_playlists, playlists_to_skip=None):
    p_update = datetime.min.replace(tzinfo=pytz.timezone(LOCAL_TIMEZONE))
    p_update_recent = datetime.min.replace(tzinfo=pytz.timezone(LOCAL_TIMEZONE))
    p_name = ""
    p_name_recent = ""
    p_url = ""
    p_url_recent = ""

    if playlists_to_skip is None:
        playlists_to_skip = []

    if list_of_playlists:
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
                p_uri_id = spotify_extract_id_or_name(p_uri)
                p_owner_name = spotify_extract_id_or_name(p_owner)
                p_owner_id = spotify_extract_id_or_name(p_owner_uri)

                skipped_from_processing = ""
                if (playlists_to_skip and (p_uri_id in playlists_to_skip or p_owner_id in playlists_to_skip or p_owner_name in playlists_to_skip)) or (IGNORE_SPOTIFY_PLAYLISTS and p_owner == "Spotify"):
                    skipped_from_processing = " [ IGNORED ]"

                print(f"- '{p_name}'{skipped_from_processing}\n[ {p_url} ]\n[ songs: {p_tracks}, likes: {p_likes}, collaborators: {p_collaborators_count} ]\n[ owner: {p_owner} ]")
                if p_date:
                    print(f"[ date: {get_date_from_ts(p_date)} - {calculate_timespan(now_local(), p_date)} ago ]")
                if p_update:
                    print(f"[ update: {get_date_from_ts(p_update)} - {calculate_timespan(now_local(), p_update)} ago ]")
                if p_descr:
                    print(f"'{p_descr}'")
                print()

            if p_update is not None and p_update > p_update_recent:
                p_update_recent = p_update
                p_name_recent = p_name
                p_url_recent = p_url

        if p_update_recent is not None and p_update_recent > datetime.min.replace(tzinfo=pytz.timezone(LOCAL_TIMEZONE)) and p_name_recent and p_url_recent:
            print(f"Recently updated playlist:\n\n- '{p_name_recent}'\n[ {p_url_recent} ]\n[ update: {get_date_from_ts(p_update_recent)} - {calculate_timespan(now_local(), p_update_recent)} ago ]")


# Prints detailed info about the user with the specified URI ID (-i parameter)
def spotify_get_user_details(sp_accessToken, user_uri_id):
    playlists_count = 0
    playlists = None

    print(f"* Getting detailed info for user with URI ID '{user_uri_id}' ...\n")

    user_info = spotify_get_current_user(sp_accessToken)
    if user_info:
        print(f"Token belongs to:\t{user_info.get('display_name', '')}\n\t\t\t[ {user_info.get('spotify_url')} ]\n")

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

    profile_pic_file_tmp = f"spotify_{user_uri_id}_profile_pic_tmp_info.jpeg"
    if image_url:
        if save_profile_pic(image_url, profile_pic_file_tmp):
            profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file_tmp)), pytz.timezone(LOCAL_TIMEZONE))
            print(f"({get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} - {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)")
            if IMGCAT_PATH and os.path.isfile(IMGCAT_PATH):
                try:
                    subprocess.call((f'echo;{IMGCAT_PATH} {profile_pic_file_tmp}'), shell=True)
                except Exception:
                    pass
            try:
                os.remove(profile_pic_file_tmp)
            except Exception:
                pass
        else:
            print("")
    else:
        print("")

    print(f"\nFollowers:\t\t{followers_count}")
    if followers:
        print()
        for f_dict in followers:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
    print(f"\nFollowings:\t\t{followings_count}")
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
        print(f"\nPublic playlists:\t{playlists_count}")

        if playlists:
            print("\nGetting list of public playlists (be patient, it might take a while) ...\n")
            list_of_playlists, error_while_processing = spotify_process_public_playlists(sp_accessToken, playlists, True)
            spotify_print_public_playlists(list_of_playlists)


# Returns recently played artists for a user with the specified URI (-a parameter)
def spotify_get_recently_played_artists(sp_accessToken, user_uri_id):
    print(f"* Getting list of recently played artists for user with URI ID '{user_uri_id}' ...\n")

    user_info = spotify_get_current_user(sp_accessToken)
    if user_info:
        print(f"Token belongs to:\t{user_info.get('display_name', '')}\n\t\t\t[ {user_info.get('spotify_url')} ]\n")

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


# Prints followers & followings for a user with specified URI (-f parameter)
def spotify_get_followers_and_followings(sp_accessToken, user_uri_id):
    print(f"* Getting followers & followings for user with URI ID '{user_uri_id}' ...\n")

    user_info = spotify_get_current_user(sp_accessToken)
    if user_info:
        print(f"Token belongs to:\t{user_info.get('display_name', '')}\n\t\t\t[ {user_info.get('spotify_url')} ]\n")

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

    print(f"\nFollowers:\t\t{followers_count}")
    if followers:
        print()
        for f_dict in followers:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
    print(f"\nFollowings:\t\t{followings_count}")
    if followings:
        print()
        for f_dict in followings:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")


# Prints and saves changed list of followers/followings/playlists (with email notifications)
def spotify_print_changed_followers_followings_playlists(username, f_list, f_list_old, f_count, f_old_count, f_str, f_str_by_or_from, f_added_str, f_added_csv, f_removed_str, f_removed_csv, f_file, csv_file_name, profile_notification, is_playlist, sp_accessToken=None):
    global GLITCH_CACHE
    global PLAYLIST_INFO_CACHE

    if is_playlist:
        now = time.time()
        GLITCH_CACHE = {uri: ts for uri, ts in GLITCH_CACHE.items() if now - ts < SPOTIFY_CHECK_INTERVAL}
        PLAYLIST_INFO_CACHE = {uri: entry for uri, entry in PLAYLIST_INFO_CACHE.items() if now - entry.get("timestamp", 0) < PLAYLIST_INFO_CACHE_TTL}

    f_diff = f_count - f_old_count

    f_diff_str = "+" + str(f_diff) if f_diff > 0 else str(f_diff)

    f_list_stripped = remove_key_from_list_of_dicts_copy(f_list, "owner_name")
    f_list_old_stripped = remove_key_from_list_of_dicts_copy(f_list_old, "owner_name")

    removed_f_list = compare_two_lists_of_dicts(f_list_old_stripped, f_list_stripped)
    added_f_list = compare_two_lists_of_dicts(f_list_stripped, f_list_old_stripped)

    list_of_added_f_list = ""
    list_of_removed_f_list = ""
    added_f_list_mbody = ""
    removed_f_list_mbody = ""

    if added_f_list or removed_f_list:
        print(f"* {f_str} number changed {f_str_by_or_from} user {username} from {f_old_count} to {f_count} ({f_diff_str})\n")

    if added_f_list:
        print(f"{f_added_str}:\n")
        added_f_list_mbody = f"\n{f_added_str}:\n\n"
        for f_dict in added_f_list:
            if is_playlist:
                if "uri" in f_dict:

                    uri = f_dict["uri"]
                    cached = PLAYLIST_INFO_CACHE.get(uri)
                    if not cached or cached.get("status") != "ok":
                        print(f"- Skipping playlist {spotify_format_playlist_reference(uri)} due to cached error or missing data")
                        list_of_added_f_list += f"- Skipping playlist {spotify_format_playlist_reference(uri)} due to error\n"
                        continue
                    p_name = cached.get("name", "Unknown")
                    print(f"- {p_name} [ {spotify_convert_uri_to_url(uri)} ]")
                    list_of_added_f_list += f"- {p_name} [ {spotify_convert_uri_to_url(uri)} ]\n"

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), f_added_csv, username, "", p_name)
                    except Exception as e:
                        print(f"* Error: {e}")
            else:
                if "name" in f_dict and "uri" in f_dict:
                    print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                    list_of_added_f_list += f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]\n"
                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), f_added_csv, username, "", f_dict["name"])
                    except Exception as e:
                        print(f"* Error: {e}")
        print()
    if removed_f_list:
        print(f"{f_removed_str}:\n")
        removed_f_list_mbody = f"\n{f_removed_str}:\n\n"
        for f_dict in removed_f_list:
            if is_playlist:
                if "uri" in f_dict:

                    uri = f_dict["uri"]

                    if uri in GLITCH_CACHE:
                        print(f"- Skipping playlist {spotify_format_playlist_reference(uri)} due to recent glitch")
                        continue

                    cached = PLAYLIST_INFO_CACHE.get(uri)

                    if not cached or cached.get("status") != "ok":
                        error_str = cached.get("error", "") if cached else ""

                        if "not found" in error_str.lower():
                            print(f"- {spotify_format_playlist_reference(uri)}: playlist has been removed or set to private")
                            list_of_removed_f_list += f"- {spotify_format_playlist_reference(uri)}: playlist has been removed or set to private\n"

                        elif any(keyword in error_str.lower() for keyword in ["502", "server error", "bad gateway"]):
                            print(f"- Suspected temporary glitch for playlist {spotify_format_playlist_reference(uri)}" + (f": {error_str}" if error_str else ""))
                            GLITCH_CACHE[uri] = time.time()
                            print_cur_ts("Timestamp:\t\t\t")
                            continue

                        else:
                            print(f"- Error while getting info for playlist {spotify_format_playlist_reference(uri)}, skipping for now" + (f": {error_str}" if error_str else ""))
                            list_of_removed_f_list += f"- Error while getting info for playlist {spotify_format_playlist_reference(uri)}\n"
                            print_cur_ts("Timestamp:\t\t\t")
                            continue

                    if is_playlist_private(sp_accessToken, uri):
                        print(f"- {spotify_format_playlist_reference(uri)}: playlist has been removed or set to private")
                        list_of_removed_f_list += f"- {spotify_format_playlist_reference(uri)}: playlist has been removed or set to private\n"
                    else:
                        print(f"- {spotify_format_playlist_reference(uri)}")
                        list_of_removed_f_list += f"- {spotify_format_playlist_reference(uri)}\n"

                    if cached:
                        p_name = cached.get("name", "Unknown")
                    else:
                        p_name = "Unknown"
                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), f_removed_csv, username, p_name, "")
                    except Exception as e:
                        print(f"* Error: {e}")
            else:
                if "name" in f_dict and "uri" in f_dict:
                    print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                    list_of_removed_f_list += f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]\n"
                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), f_removed_csv, username, f_dict["name"], "")
                    except Exception as e:
                        print(f"* Error: {e}")
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

    if (f_str == "Followers" or f_str == "Followings") and not followers_followings_notification:
        return False

    if profile_notification:

        m_subject = f"Spotify user {username} {str(f_str).lower()} number has changed! ({f_diff_str}, {f_old_count} -> {f_count})"
        m_body = f"{f_str} number changed {f_str_by_or_from} user {username} from {f_old_count} to {f_count} ({f_diff_str})\n{removed_f_list_mbody}{list_of_removed_f_list}{added_f_list_mbody}{list_of_added_f_list}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"

        print(f"Sending email notification to {RECEIVER_EMAIL}")
        send_email(m_subject, m_body, "", SMTP_SSL)

    return False


# Saves user's profile pic to selected file name
def save_profile_pic(user_image_url, image_file_name):
    try:
        image_response = req.get(user_image_url, timeout=FUNCTION_TIMEOUT, stream=True, verify=VERIFY_SSL)
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
        return True
    except Exception:
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


# Main function that monitors profile changes of the specified Spotify user URI ID
def spotify_profile_monitor_uri(user_uri_id, error_notification, csv_file_name, playlists_to_skip):
    global SP_CACHED_ACCESS_TOKEN
    playlists_count = 0
    playlists_old_count = 0
    playlists = None
    playlists_old = None
    playlists_zeroed_counter = 0

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print(f"* Error: {e}")

    email_sent = False

    out = f"Monitoring user {user_uri_id}"
    print(out)
    print("-" * len(out))

    try:
        sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
        sp_user_data = spotify_get_user_info(sp_accessToken, user_uri_id, DETECT_CHANGES_IN_PLAYLISTS, 0)
        user_info = spotify_get_current_user(sp_accessToken)
        sp_user_followers_data = spotify_get_user_followers(sp_accessToken, user_uri_id)
        sp_user_followings_data = spotify_get_user_followings(sp_accessToken, user_uri_id)
    except Exception as e:
        if "401" in str(e):
            SP_CACHED_ACCESS_TOKEN = None
        if ('access token' in str(e)) or ('Unsuccessful token request' in str(e)):
            print(f"* Error: sp_dc might have expired!\n{str(e)}")
        elif '404' in str(e):
            print("* Error: user does not exist!")
        else:
            print(f"* Error: {e}")
        sys.exit(1)

    if user_info:
        print(f"Token belongs to:\t\t{user_info.get('display_name', '')}\n\t\t\t\t[ {user_info.get('spotify_url')} ]\n")

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

    print(f"Username:\t\t\t{username}")
    print(f"User URI ID:\t\t\t{user_uri_id}")
    print(f"User URL:\t\t\t{spotify_convert_uri_to_url(f'spotify:user:{user_uri_id}')}")

    print(f"User profile picture:\t\t{image_url != ''}")

    profile_pic_file_tmp = f"spotify_profile_{file_suffix}_pic_tmp_info.jpeg"
    if image_url and IMGCAT_PATH and os.path.isfile(IMGCAT_PATH):
        if save_profile_pic(image_url, profile_pic_file_tmp):
            try:
                subprocess.call((f'echo;{IMGCAT_PATH} {profile_pic_file_tmp}'), shell=True)
            except Exception:
                pass
            try:
                os.remove(profile_pic_file_tmp)
            except Exception:
                pass

    print(f"\nFollowers:\t\t\t{followers_count}")
    print(f"Followings:\t\t\t{followings_count}")

    list_of_playlists = []

    if DETECT_CHANGES_IN_PLAYLISTS:
        print(f"Public playlists:\t\t{playlists_count}")

        if playlists:
            print("\n* Getting list of public playlists (be patient, it might take a while) ...\n")
            list_of_playlists, error_while_processing = spotify_process_public_playlists(sp_accessToken, playlists, True, playlists_to_skip)
            spotify_print_public_playlists(list_of_playlists, playlists_to_skip)

    print_cur_ts("\nTimestamp:\t\t\t")

    followers_file = f"spotify_profile_{file_suffix}_followers.json"
    followings_file = f"spotify_profile_{file_suffix}_followings.json"
    playlists_file = f"spotify_profile_{file_suffix}_playlists.json"
    profile_pic_file = f"spotify_profile_{file_suffix}_pic.jpeg"
    profile_pic_file_old = f"spotify_profile_{file_suffix}_pic_old.jpeg"
    profile_pic_file_tmp = f"spotify_profile_{file_suffix}_pic_tmp.jpeg"

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

        if playlists_count != playlists_old_count:
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

        # user has no profile pic, but it exists in the filesystem
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

        # user has profile pic, but it does not exist in the filesystem
        elif image_url and not os.path.isfile(profile_pic_file):
            if save_profile_pic(image_url, profile_pic_file):
                profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)), pytz.timezone(LOCAL_TIMEZONE))
                print(f"* User {username} profile picture saved to '{profile_pic_file}'")
                print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)")

                try:
                    if IMGCAT_PATH and os.path.isfile(IMGCAT_PATH):
                        subprocess.call((f'echo;{IMGCAT_PATH} {profile_pic_file};echo'), shell=True)
                    shutil.copy2(profile_pic_file, f'spotify_profile_{file_suffix}_pic_{profile_pic_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
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

        # user has profile pic and it exists in the filesystem, but we check if it has not changed
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
                        if IMGCAT_PATH and os.path.isfile(IMGCAT_PATH):
                            subprocess.call((f'echo;{IMGCAT_PATH} {profile_pic_file_tmp};echo'), shell=True)
                        shutil.copy2(profile_pic_file_tmp, f'spotify_profile_{file_suffix}_pic_{profile_pic_tmp_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
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
    alive_counter = 0

    # Main loop
    while True:
        # Sometimes Spotify network functions halt even though we specified the timeout
        # To overcome this we use alarm signal functionality to kill it inevitably, not available on Windows
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(ALARM_TIMEOUT)
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            sp_user_data = spotify_get_user_info(sp_accessToken, user_uri_id, DETECT_CHANGES_IN_PLAYLISTS, 0)
            email_sent = False
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
            print(f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: {e}")
            if "401" in str(e):
                SP_CACHED_ACCESS_TOKEN = None
            if ('access token' in str(e)) or ('Unsuccessful token request' in str(e)):
                print(f"* Error: sp_dc might have expired!")
                if error_notification and not email_sent:
                    m_subject = f"spotify_profile_monitor: sp_dc might have expired! (uri: {user_uri_id})"
                    m_body = f"sp_dc might have expired!\n{e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>sp_dc might have expired!<br>{escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                    email_sent = True
            elif '404' in str(e):
                print("* Error: user might have removed the account !")
                if error_notification and not email_sent:
                    m_subject = f"spotify_profile_monitor: user might have removed the account! (uri: {user_uri_id})"
                    m_body = f"User might have removed the account: {e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>User might have removed the account: {escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                    email_sent = True
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

            if profile_notification:
                m_subject = f"Spotify user {username_old} has changed username to {username}"
                m_body = f"Spotify user '{username_old}' has changed username to '{username}'\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, "", SMTP_SSL)

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

        recently_played_artists = sp_user_data["sp_user_recently_played_artists"]

        if followers_count != followers_old_count:
            spotify_print_changed_followers_followings_playlists(username, followers, followers_old, followers_count, followers_old_count, "Followers", "for", "Added followers", "Added Follower", "Removed followers", "Removed Follower", followers_file, csv_file_name, profile_notification, False)

            followers_old_count = followers_count
            followers_old = followers

            print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
            print_cur_ts("Timestamp:\t\t\t")

        if followings_count != followings_old_count:
            spotify_print_changed_followers_followings_playlists(username, followings, followings_old, followings_count, followings_old_count, "Followings", "by", "Added followings", "Added Following", "Removed followings", "Removed Following", followings_file, csv_file_name, profile_notification, False)

            followings_old_count = followings_count
            followings_old = followings

            print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
            print_cur_ts("Timestamp:\t\t\t")

        # profile pic

        if DETECT_CHANGED_PROFILE_PIC:

            # user has no profile pic, but it exists in the filesystem
            if not image_url and os.path.isfile(profile_pic_file):
                profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)), pytz.timezone(LOCAL_TIMEZONE))
                print(f"* User {username} has removed profile picture added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ! (after {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)})\n")
                os.replace(profile_pic_file, profile_pic_file_old)

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, now_local_naive(), "Profile Picture Removed", username, convert_to_local_naive(profile_pic_mdate_dt), "")
                except Exception as e:
                    print(f"* Error: {e}")

                if profile_notification:
                    m_subject = f"Spotify user {username} has removed profile picture ! (after {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)})"
                    m_body = f"Spotify user {username} has removed profile picture added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} (after {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)})\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)

                print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                print_cur_ts("Timestamp:\t\t\t")

            # user has profile pic, but it does not exist in the filesystem
            elif image_url and not os.path.isfile(profile_pic_file):
                print(f"* User {username} has set profile picture !")
                m_body_html_pic_saved_text = ""
                if save_profile_pic(image_url, profile_pic_file):
                    profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)), pytz.timezone(LOCAL_TIMEZONE))
                    print(f"* User profile picture saved to '{profile_pic_file}'")
                    print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)\n")
                    m_body_html_pic_saved_text = f'<br><br><img src="cid:profile_pic">'

                    try:
                        if IMGCAT_PATH and os.path.isfile(IMGCAT_PATH):
                            subprocess.call((f'{IMGCAT_PATH} {profile_pic_file};echo'), shell=True)
                        shutil.copy2(profile_pic_file, f'spotify_profile_{file_suffix}_pic_{profile_pic_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                    except Exception:
                        pass

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, now_local_naive(), "Profile Picture Created", username, "", convert_to_local_naive(profile_pic_mdate_dt))
                    except Exception as e:
                        print(f"* Error: {e}")

                    if profile_notification:
                        m_subject = f"Spotify user {username} has set profile picture ! ({get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)})"
                        m_body = f"Spotify user {username} has set profile picture !\n\nProfile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"Spotify user <b>{username}</b> has set profile picture !{m_body_html_pic_saved_text}<br><br>Profile picture has been added on <b>{get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)}</b> ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False)} ago)<br><br>Check interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts('<br>Timestamp: ')}"
                        print(f"Sending email notification to {RECEIVER_EMAIL}")

                        send_email(m_subject, m_body, m_body_html, SMTP_SSL, profile_pic_file, "profile_pic")

                else:
                    print(f"* Error saving profile picture !\n")

                print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                print_cur_ts("Timestamp:\t\t\t")

            # user has profile pic and it exists in the filesystem, but we check if it has not changed
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
                            if IMGCAT_PATH and os.path.isfile(IMGCAT_PATH):
                                subprocess.call((f'{IMGCAT_PATH} {profile_pic_file_tmp};echo'), shell=True)
                            shutil.copy2(profile_pic_file_tmp, f'spotify_profile_{file_suffix}_pic_{profile_pic_tmp_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                            os.replace(profile_pic_file, profile_pic_file_old)
                            os.replace(profile_pic_file_tmp, profile_pic_file)
                        except Exception as e:
                            print(f"* Error while replacing/copying files: {e}")

                        if profile_notification:
                            m_body_html_pic_saved_text = f'<br><br><img src="cid:profile_pic">'
                            m_subject = f"Spotify user {username} has changed profile picture ! (after {calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)})"
                            m_body = f"Spotify user {username} has changed profile picture !\n\nPrevious one added on {get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)\n\nProfile picture has been added on {get_short_date_from_ts(profile_pic_tmp_mdate_dt, always_show_year=True)} ({calculate_timespan(now_local(), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                            m_body_html = f"Spotify user <b>{username}</b> has changed profile picture !{m_body_html_pic_saved_text}<br><br>Previous one added on <b>{get_short_date_from_ts(profile_pic_mdate_dt, always_show_year=True)}</b> ({calculate_timespan(now_local(), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)<br><br>Profile picture has been added on <b>{get_short_date_from_ts(profile_pic_tmp_mdate_dt, always_show_year=True)}</b> ({calculate_timespan(now_local(), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)<br><br>Check interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts('<br>Timestamp: ')}"
                            print(f"Sending email notification to {RECEIVER_EMAIL}")
                            send_email(m_subject, m_body, m_body_html, SMTP_SSL, profile_pic_file, "profile_pic")

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
                list_of_playlists, error_while_processing = spotify_process_public_playlists(sp_accessToken, playlists, True, playlists_to_skip)

            for playlist in list_of_playlists:
                if "uri" in playlist:
                    p_uri = playlist.get("uri", "")
                    p_owner = playlist.get("owner", "")
                    p_owner_uri = playlist.get("owner_uri", "")
                    p_uri_id = spotify_extract_id_or_name(p_uri)
                    p_owner_name = spotify_extract_id_or_name(p_owner)
                    p_owner_id = spotify_extract_id_or_name(p_owner_uri)

                    # we do not process playlists that are ignored
                    if (playlists_to_skip and (p_uri_id in playlists_to_skip or p_owner_id in playlists_to_skip or p_owner_name in playlists_to_skip)) or (IGNORE_SPOTIFY_PLAYLISTS and p_owner == "Spotify"):
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

                                # Number of likes changed
                                if p_likes != p_likes_old:
                                    p_likes_diff = p_likes - p_likes_old
                                    p_likes_diff_str = ""
                                    if p_likes_diff > 0:
                                        p_likes_diff_str = "+" + str(p_likes_diff)
                                    else:
                                        p_likes_diff_str = str(p_likes_diff)
                                    p_message = f"* Playlist '{p_name}': number of likes changed from {p_likes_old} to {p_likes} ({p_likes_diff_str})\n* Playlist URL: {p_url}\n"
                                    print(p_message)
                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Playlist Likes", p_name, p_likes_old, p_likes)
                                    except Exception as e:
                                        print(f"* Error: {e}")
                                    m_subject = f"Spotify user {username} number of likes for playlist '{p_name}' has changed! ({p_likes_diff_str}, {p_likes_old} -> {p_likes})"
                                    m_body = f"{p_message}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    if profile_notification:
                                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                                        send_email(m_subject, m_body, "", SMTP_SSL)
                                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t\t")

                                # Number of collaborators changed
                                if p_collaborators != p_collaborators_old:
                                    p_collaborators_diff = p_collaborators - p_collaborators_old
                                    p_collaborators_diff_str = ""

                                    if p_collaborators_diff > 0:
                                        p_collaborators_diff_str = "+" + str(p_collaborators_diff)
                                    else:
                                        p_collaborators_diff_str = str(p_collaborators_diff)

                                    p_message = f"* Playlist '{p_name}': number of collaborators changed from {p_collaborators_old} to {p_collaborators} ({p_collaborators_diff_str})\n* Playlist URL: {p_url}\n"
                                    print(p_message)

                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Collaborators Number", p_name, p_collaborators_old, p_collaborators)
                                    except Exception as e:
                                        print(f"* Error: {e}")

                                    added_keys = p_collaborators_list.keys() - p_collaborators_list_old.keys()
                                    removed_keys = p_collaborators_list_old.keys() - p_collaborators_list.keys()

                                    added_collaborators = {key: p_collaborators_list[key] for key in added_keys}
                                    removed_collaborators = {key: p_collaborators_list_old[key] for key in removed_keys}

                                    p_message_added_collaborators = ""
                                    p_message_removed_collaborators = ""

                                    if added_collaborators:
                                        p_message_added_collaborators = "Added collaborators:\n\n"

                                        for collab_id, collab_name in added_collaborators.items():
                                            added_collab = f'- {collab_name} [ {spotify_convert_uri_to_url(f"spotify:user:{collab_id}")} ]\n'
                                            p_message_added_collaborators += added_collab
                                            try:
                                                if csv_file_name:
                                                    write_csv_entry(csv_file_name, now_local_naive(), "Added Collaborator", p_name, "", collab_name)
                                            except Exception as e:
                                                print(f"* Error: {e}")

                                        p_message_added_collaborators += "\n"
                                        print(p_message_added_collaborators, end="")

                                    if removed_collaborators:
                                        p_message_removed_collaborators = "Removed collaborators:\n\n"

                                        for collab_id, collab_name in removed_collaborators.items():
                                            removed_collab = f'- {collab_name} [ {spotify_convert_uri_to_url(f"spotify:user:{collab_id}")} ]\n'
                                            p_message_removed_collaborators += removed_collab
                                            try:
                                                if csv_file_name:
                                                    write_csv_entry(csv_file_name, now_local_naive(), "Removed Collaborator", p_name, collab_name, "")
                                            except Exception as e:
                                                print(f"* Error: {e}")

                                        p_message_removed_collaborators += "\n"
                                        print(p_message_removed_collaborators, end="")

                                    m_subject = f"Spotify user {username} number of collaborators for playlist '{p_name}' has changed! ({p_collaborators_diff_str}, {p_collaborators_old} -> {p_collaborators})"
                                    m_body = f"{p_message}\n{p_message_added_collaborators}{p_message_removed_collaborators}Check interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    if profile_notification:
                                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                                        send_email(m_subject, m_body, "", SMTP_SSL)
                                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t\t")

                                # Number of tracks changed
                                if p_tracks != p_tracks_old or p_update != p_update_old:
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

                                        p_after_str = ""
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
                                        print(f"* Error while processing data for playlist {spotify_format_playlist_reference(p_uri)}, skipping for now" + (f": {e}" if e else ""))
                                        print_cur_ts("Timestamp:\t\t\t")
                                        continue
                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, now_local_naive(), "Playlist Number of Tracks", p_name, p_tracks_old, p_tracks)
                                    except Exception as e:
                                        print(f"* Error: {e}")

                                    removed_tracks = diff_tracks(p_tracks_list_old, p_tracks_list)
                                    added_tracks = diff_tracks(p_tracks_list, p_tracks_list_old)
                                    p_message_added_tracks = ""
                                    p_message_removed_tracks = ""

                                    if added_tracks:
                                        print("Added tracks:\n")
                                        p_message_added_tracks = "Added tracks:\n\n"

                                        for f_dict in added_tracks:
                                            if "artist" in f_dict and "track" in f_dict:
                                                apple_search_url, genius_search_url, youtube_music_search_url = get_apple_genius_search_urls(f_dict["artist"], f_dict["track"])
                                                tempuri = f'spotify:user:{f_dict["added_by_id"]}'
                                                added_track = f'- {f_dict["artist"]} - {f_dict["track"]} [ {get_date_from_ts(f_dict["added_at"])}, {f_dict["added_by"]} ]\n[ Spotify URL: {spotify_convert_uri_to_url(f_dict["uri"])} ]\n[ Apple Music URL: {apple_search_url} ]\n[ YouTube Music URL: {youtube_music_search_url} ]\n[ Genius URL: {genius_search_url} ]\n[ Collaborator URL: {spotify_convert_uri_to_url(tempuri)} ]\n\n'
                                                p_message_added_tracks += added_track
                                                added_at_dt = f_dict['added_at']
                                                print(added_track, end="")
                                                try:
                                                    if csv_file_name:
                                                        write_csv_entry(csv_file_name, convert_to_local_naive(added_at_dt), "Added Track", p_name, f_dict['added_by'], f_dict["artist"] + " - " + f_dict["track"])
                                                except Exception as e:
                                                    print(f"* Error: {e}")

                                    if removed_tracks:
                                        print("Removed tracks:\n")
                                        p_message_removed_tracks = "Removed tracks:\n\n"

                                        for f_dict in removed_tracks:
                                            if "artist" in f_dict and "track" in f_dict:
                                                apple_search_url, genius_search_url, youtube_music_search_url = get_apple_genius_search_urls(f_dict["artist"], f_dict["track"])
                                                tempuri = f'spotify:user:{f_dict["added_by_id"]}'
                                                removed_track = f'- {f_dict["artist"]} - {f_dict["track"]} [ {get_date_from_ts(f_dict["added_at"])}, {f_dict["added_by"]} ]\n[ Spotify URL: {spotify_convert_uri_to_url(f_dict["uri"])} ]\n[ Apple Music URL: {apple_search_url} ]\n[ YouTube Music URL: {youtube_music_search_url} ]\n[ Genius URL: {genius_search_url} ]\n[ Collaborator URL: {spotify_convert_uri_to_url(tempuri)} ]\n\n'
                                                p_message_removed_tracks += removed_track
                                                print(removed_track, end="")
                                                try:
                                                    if csv_file_name:
                                                        write_csv_entry(csv_file_name, now_local_naive(), "Removed Track", p_name, f_dict["artist"] + " - " + f_dict["track"], "")
                                                except Exception as e:
                                                    print(f"* Error: {e}")

                                    p_subject_after_str = ""
                                    if p_tracks_diff != 0:
                                        if p_update and p_update_old:
                                            p_subject_after_str = f"; after {calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2)}"
                                        m_subject = f"Spotify user {username} number of tracks for playlist '{p_name}' has changed! ({p_tracks_diff_str}, {p_tracks_old} -> {p_tracks}{p_subject_after_str})"
                                    else:
                                        if p_update and p_update_old:
                                            p_subject_after_str = f" (after {calculate_timespan(p_update, p_update_old, show_seconds=False, granularity=2)})"
                                        m_subject = f"Spotify user {username} list of tracks ({p_tracks}) for playlist '{p_name}' has changed!{p_subject_after_str}"
                                    m_body = f"{p_message}\n{p_message_added_tracks}{p_message_removed_tracks}Check interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    if profile_notification:
                                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                                        send_email(m_subject, m_body, "", SMTP_SSL)
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
                                    if profile_notification:
                                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                                        send_email(m_subject, m_body, "", SMTP_SSL)
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
                                    if profile_notification:
                                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                                        send_email(m_subject, m_body, "", SMTP_SSL)
                                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t\t")

            if not error_while_processing:
                list_of_playlists_old = list_of_playlists

            if playlists_count != playlists_old_count and (playlists or (not playlists and playlists_count == 0)):

                if playlists_count == 0:
                    playlists_zeroed_counter += 1
                else:
                    playlists_zeroed_counter = 0

                if playlists_zeroed_counter == PLAYLISTS_DISAPPEARED_COUNTER or playlists_count > 0:
                    glitch_detected = spotify_print_changed_followers_followings_playlists(username, playlists, playlists_old, playlists_count, playlists_old_count, "Playlists", "for", "Added playlists to profile", "Added Playlist", "Removed playlists from profile", "Removed Playlist", playlists_file, csv_file_name, profile_notification, True, sp_accessToken)

                    if not glitch_detected:
                        playlists_old_count = playlists_count
                        playlists_old = playlists
                        playlists_zeroed_counter = 0

                    else:
                        print("* Possible Spotify API glitch detected, not reporting the number of changed playlists temporarily!\n")
                    print(f"Check interval:\t\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t\t")

        alive_counter += 1

        if alive_counter >= TOOL_ALIVE_COUNTER:
            print_cur_ts("Alive check, timestamp:\t\t")
            alive_counter = 0

        time.sleep(SPOTIFY_CHECK_INTERVAL)


if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    clear_screen(CLEAR_SCREEN)

    print(f"Spotify Profile Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser(
        prog="spotify_profile_monitor",
        description="Monitor a Spotify user’s profile changes and send customizable email alerts [ https://github.com/misiektoja/spotify_profile_monitor/ ]"
    )

    # Positional
    parser.add_argument(
        "user_id",
        nargs="?",
        metavar="SPOTIFY_USER_URI_ID",
        help="Spotify user URI ID",
        type=str
    )

    # API credentials
    creds = parser.add_argument_group("API credentials")
    creds.add_argument(
        "-u", "--spotify-dc-cookie",
        dest="spotify_dc_cookie",
        metavar="SP_DC_COOKIE",
        type=str,
        help="Spotify sp_dc cookie"
    )

    # Notifications
    notify = parser.add_argument_group("Notifications")
    notify.add_argument(
        "-p", "--notify-profile",
        dest="profile_notification",
        action="store_true",
        help="Email when user’s profile changes"
    )
    notify.add_argument(
        "-g", "--no-followers-followings-notify",
        dest="disable_followers_followings_notification",
        action="store_false",
        help="Disable notifications about new followers/followings"
    )
    notify.add_argument(
        "-e", "--no-error-notify",
        dest="error_notification",
        action="store_false",
        help="Disable notifications on errors"
    )
    notify.add_argument(
        "-z", "--send-test-email",
        dest="send_test_email",
        action="store_true",
        help="Send test email to verify SMTP settings"
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
        "-x", "--list-liked-tracks",
        dest="list_liked_tracks",
        action="store_true",
        help="List all liked tracks for the user owning the Spotify access token"
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
        "-v", "--show-user-info",
        dest="show_user_info",
        action="store_true",
        help="Get basic information about the Spotify access token owner"
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
        "-j", "--no-profile-pic-detect",
        dest="do_not_detect_changed_profile_pic",
        action="store_false",
        help="Disable detection of changed profile picture"
    )
    opts.add_argument(
        "-q", "--no-playlist-monitor",
        dest="do_not_monitor_playlists",
        action="store_false",
        help="Disable monitoring of playlist changes"
    )
    opts.add_argument(
        "-k", "--get-all-playlists",
        dest="get_all_playlists",
        action="store_true",
        help="Fetch all playlists instead of only owned ones"
    )
    opts.add_argument(
        "-y", "--file-suffix",
        dest="file_suffix",
        metavar="SUFFIX",
        type=str,
        help="File suffix to append to output filenames"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        help="Disable logging to spotify_profile_monitor_<suffix>.log"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

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
            print("* Error: Cannot detect local timezone, consider setting LOCAL_TIMEZONE to your local timezone manually !")
            sys.exit(1)
    else:
        if not is_valid_timezone(LOCAL_TIMEZONE):
            print(f"* Error: Configured LOCAL_TIMEZONE '{LOCAL_TIMEZONE}' is not valid. Please use a valid pytz timezone name.")
            sys.exit(1)

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
        TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / SPOTIFY_CHECK_INTERVAL

    if args.error_interval:
        SPOTIFY_ERROR_INTERVAL = args.error_interval

    if args.spotify_dc_cookie:
        SP_DC_COOKIE = args.spotify_dc_cookie

    if not SP_DC_COOKIE or SP_DC_COOKIE == "your_sp_dc_cookie_value":
        print("* Error: SP_DC_COOKIE (-u / --spotify_dc_cookie) value is empty or incorrect")
        sys.exit(1)

    if args.show_user_info:
        print("* Getting basic information about access token owner ...\n")
        try:
            accessToken = spotify_get_access_token(SP_DC_COOKIE)
            user_info = spotify_get_current_user(accessToken)

            if user_info:
                print(f"Token belongs to:\n")

                print(f"Username:\t\t{user_info.get('display_name', '')}")
                print(f"User URI ID:\t\t{user_info.get('uri', '').split('spotify:user:', 1)[1]}")
                print(f"User URL:\t\t{user_info.get('spotify_url', '')}")
                print(f"User e-mail:\t\t{user_info.get('email', '')}")
                print(f"User country:\t\t{user_info.get('country', '')}")
                print(f"Is Premium?:\t\t{user_info.get('is_premium', '')}")
            else:
                print("Failed to retrieve user info.")

            print("─" * HORIZONTAL_LINE)
        except Exception as e:
            print(f"* Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.csv_file:
        try:
            with open(args.csv_file, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            print(f"* Error, CSV file cannot be opened for writing: {e}")
            sys.exit(1)

    if args.list_tracks_for_playlist:
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            spotify_list_tracks_for_playlist(sp_accessToken, args.list_tracks_for_playlist, args.csv_file, CSV_FILE_FORMAT_EXPORT)
        except Exception as e:
            if 'Not Found' in str(e) or '400 Client' in str(e):
                print("* Error: playlist does not exist or is set to private")
            else:
                print(f"* Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.list_liked_tracks:
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            spotify_list_liked_tracks(sp_accessToken, args.csv_file, CSV_FILE_FORMAT_EXPORT)
        except Exception as e:
            if 'Not Found' in str(e) or '400 Client' in str(e):
                print("* Error: playlist does not exist or is set to private")
            else:
                print(f"* Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.search_username:
        if not SP_SHA256 or SP_SHA256 == "your_spotify_client_sha256":
            print("* Error: wrong SP_SHA256 value !")
            sys.exit(1)
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            spotify_search_users(sp_accessToken, args.search_username)
        except Exception as e:
            print(f"* Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if not args.user_id:
        print("* Error: SPOTIFY_USER_URI_ID argument is required !")
        sys.exit(1)

    if args.user_profile_details:
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            spotify_get_user_details(sp_accessToken, args.user_id)
        except Exception as e:
            if 'Not Found' in str(e) or '404 Client' in str(e):
                print("* Error: user does not exist")
            else:
                print(f"* Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.recently_played_artists:
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            spotify_get_recently_played_artists(sp_accessToken, args.user_id)
        except Exception as e:
            if 'Not Found' in str(e) or '404 Client' in str(e):
                print("* Error: user does not exist")
            else:
                print(f"* Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.followers_and_followings:
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            spotify_get_followers_and_followings(sp_accessToken, args.user_id)
        except Exception as e:
            if 'Not Found' in str(e) or '404 Client' in str(e):
                print("* Error: user does not exist")
            else:
                print(f"* Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.playlists_to_skip:
        try:
            with open(args.playlists_to_skip, encoding="utf-8") as file:
                playlists_to_skip = {
                    spotify_extract_id_or_name(line)
                    for line in file
                    if line.strip() and not line.strip().startswith("#")
                }
            file.close()
        except Exception as e:
            print(f"* Error, file with playlists to ignore cannot be opened: {e}")
            sys.exit(1)
    else:
        playlists_to_skip = []

    if args.file_suffix:
        file_suffix = str(args.file_suffix)
    else:
        file_suffix = str(args.user_id)

    if not args.disable_logging:
        SP_LOGFILE = f"{SP_LOGFILE}_{file_suffix}.log"
        sys.stdout = Logger(SP_LOGFILE)

    profile_notification = args.profile_notification
    followers_followings_notification = args.disable_followers_followings_notification
    error_notification = args.error_notification

    if profile_notification is False:
        followers_followings_notification = False

    if SMTP_HOST == "your_smtp_server_ssl" or SMTP_HOST == "your_smtp_server_plaintext":
        profile_notification = False
        followers_followings_notification = False
        error_notification = False

    print(f"* Spotify timers:\t\t[check interval: {display_time(SPOTIFY_CHECK_INTERVAL)}] [error interval: {display_time(SPOTIFY_ERROR_INTERVAL)}]")
    print(f"* Email notifications:\t\t[profile changes = {profile_notification}] [followers/followings = {followers_followings_notification}]\n\t\t\t\t[errors = {error_notification}]")
    print(f"* Profile pic changes:\t\t{DETECT_CHANGED_PROFILE_PIC}")
    print(f"* Playlist changes:\t\t{DETECT_CHANGES_IN_PLAYLISTS}")
    print(f"* All public playlists:\t\t{GET_ALL_PLAYLISTS}")
    print(f"* Output logging enabled:\t{not args.disable_logging}" + (f" ({SP_LOGFILE})" if not args.disable_logging else ""))
    print(f"* CSV logging enabled:\t\t{bool(args.csv_file)}" + (f" ({args.csv_file})" if args.csv_file else ""))
    print(f"* Local timezone:\t\t{LOCAL_TIMEZONE}\n")

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_profile_changes_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_check_signal_handler)

    spotify_profile_monitor_uri(args.user_id, error_notification, args.csv_file, playlists_to_skip)

    sys.stdout = stdout_bck
    sys.exit(0)

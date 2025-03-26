#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v2.0.1

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

VERSION = "2.0.1"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Log in to Spotify web client (https://open.spotify.com/) and put the value of sp_dc cookie below (or use -u parameter)
# Newly generated Spotify's sp_dc cookie should be valid for 1 year
# You can use Cookie-Editor by cgagnier to get it easily (available for all major web browsers): https://cookie-editor.com/
SP_DC_COOKIE = "your_sp_dc_cookie_value"

# SMTP settings for sending email notifications, you can leave it as it is below and no notifications will be sent
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
# SMTP_HOST = "your_smtp_server_plaintext"
# SMTP_PORT = 25
# SMTP_USER = "your_smtp_user"
# SMTP_PASSWORD = "your_smtp_password"
# SMTP_SSL = False
# SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# How often do we perform checks for user's profile changes, you can also use -c parameter; in seconds
SPOTIFY_CHECK_INTERVAL = 1800  # 30 mins

# How often do we retry in case of errors, you can also use -m parameter; in seconds
SPOTIFY_ERROR_INTERVAL = 180  # 3 mins

# Specify your local time zone so we convert Spotify timestamps to your time (for example: 'Europe/Warsaw')
# If you leave it as 'Auto' we will try to automatically detect the local timezone
LOCAL_TIMEZONE = 'Auto'

# Do you want to be informed about changed user's profile pic ? (via console & email notifications when -p is enabled)
# If so, the tool will save the pic to the file named 'spotify_profile_{user_uri_id/file_suffix}_pic.jpeg' after tool is started
# And also to files named 'spotify_profile_{user_uri_id/file_suffix}_pic_YYmmdd_HHMM.jpeg' when changes are detected
# We need to save the binary form of the image as the pic URL can change, so we need to actually do bin comparison of jpeg files
# It is enabled by default, you can change it below or disable by using -j parameter
DETECT_CHANGED_PROFILE_PIC = True

# If you have 'imgcat' installed, you can configure its path below, so new profile pictures will be displayed right in your terminal
# Leave it empty to disable this feature
# IMGCAT_PATH = "/usr/local/bin/imgcat"
IMGCAT_PATH = ""

# SP_SHA256 is only needed for functionality searching Spotify users (-s), otherwise you can leave it empty
# You need to intercept your Spotify client's network traffic and get the sha256 value
# To simulate the needed request, search for some user in Spotify client
# Then in intercepting proxy look for requests with searchUsers or searchDesktop operation name
# Display details of one of such request and copy the sha256Hash parameter value and put it below
# Example request:
# https://api-partner.spotify.com/pathfinder/v1/query?operationName=searchUsers&variables={"searchTerm":"user_uri_id","offset":0,"limit":5,"numberOfTopResults":5,"includeAudiobooks":false}&extensions={"persistedQuery":{"version":1,"sha256Hash":"XXXXXXXXXX"}}
# You are interested in the string marked as "XXXXXXXXXX" here
# I used Proxyman proxy on MacOS to intercept Spotify's client traffic
SP_SHA256 = "your_spotify_client_sha256"

# Do you want to be informed about changes in user's profile public playlists ? (via console & email notifications when -p is enabled)
# It will cover added/removed tracks in playlists, playlists name and description changes, number of likes for playlists
# It is enabled by default, you can change it below or disable by using -q parameter
# It is also taken into consideration when using -i parameter
DETECT_CHANGES_IN_PLAYLISTS = True

# How many user owned public playlists the tool will monitor
PLAYLISTS_LIMIT = 50

# How many recently played artists the tool will display when using -a parameter
RECENTLY_PLAYED_ARTISTS_LIMIT = 50

# How many recently played artists the tool will display when using -i parameter
RECENTLY_PLAYED_ARTISTS_LIMIT_INFO = 15

# By default, only public playlists owned by the user are fetched, you can change this behavior below or by using -k parameter
# It is helpful in the case of playlists created by another user added to another user profile
GET_ALL_PLAYLISTS = False

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL = 21600  # 6 hours

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL = 'http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# The name of the .log file; the tool by default will output its messages to spotify_profile_monitor_{user_uri_id/file_suffix}.log file
SP_LOGFILE = "spotify_profile_monitor"

# Value used by signal handlers increasing/decreasing the profile check (SPOTIFY_CHECK_INTERVAL); in seconds
SPOTIFY_CHECK_SIGNAL_VALUE = 300  # 5 minutes

# How many times should we attempt to obtain a valid access token in a single run of the spotify_get_access_token() function
TOKEN_MAX_RETRIES = 10

# Time interval between consecutive attempts to obtain the access token
TOKEN_RETRY_TIMEOUT = 0.5  # 0.5 second

# Shall we enable or disable SSL certificate verification while sending https requests
VERIFY_SSL = True

# Shall we ignore Spotify-owned playlists from monitoring ? By default it is set to true, so the tool won't report changed tracks and
# number of likes for them (they are typically dynamically generated with high volume of changes in terms of likes and sometimes tracks as well)
IGNORE_SPOTIFY_PLAYLISTS = True

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

TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / SPOTIFY_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Type', 'Name', 'Old', 'New']

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
from datetime import datetime
from dateutil import relativedelta
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
    pass
import platform
import html
import urllib
from urllib.parse import quote_plus, quote, urlparse
import re
import ipaddress
from itertools import zip_longest
from html import escape
import subprocess
import pyotp
import base64
import random
from random import randrange

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


# Function to check internet connectivity
def check_internet():
    url = CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT, verify=VERIFY_SSL)
        print("OK")
        return True
    except Exception as e:
        print(f"No connectivity, please check your network - {e}")
        sys.exit(1)


# Function to convert absolute value of seconds to human readable format
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


# Function to calculate time span between two timestamps in seconds
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if type(timestamp1) is int:
        dt1 = datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is float:
        ts1 = int(round(ts1))
        dt1 = datetime.fromtimestamp(ts1)
    elif type(timestamp1) is datetime:
        dt1 = timestamp1
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2 = datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is float:
        ts2 = int(round(ts2))
        dt2 = datetime.fromtimestamp(ts2)
    elif type(timestamp2) is datetime:
        dt2 = timestamp2
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
        weeks = date_diff.weeks
        if not show_weeks:
            weeks = 0
        days = date_diff.days
        if weeks > 0:
            days = days - (weeks * 7)
        hours = date_diff.hours
        if (not show_hours and ts_diff > 86400):
            hours = 0
        minutes = date_diff.minutes
        if (not show_minutes and ts_diff > 3600):
            minutes = 0
        seconds = date_diff.seconds
        if (not show_seconds and ts_diff > 60):
            seconds = 0
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


# Function to send email notification
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

        if image_file:
            fp = open(image_file, 'rb')
            img_part = MIMEImage(fp.read())
            fp.close()

        if body:
            part1 = MIMEText(body, 'plain')
            part1 = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
            email_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            part2 = MIMEText(body_html.encode('utf-8'), 'html', _charset='utf-8')
            email_msg.attach(part2)

        if image_file:
            img_part.add_header('Content-ID', f'<{image_name}>')
            email_msg.attach(img_part)

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtpObj.quit()
    except Exception as e:
        print(f"Error sending email - {e}")
        return 1
    return 0


# Function to write CSV entry
def write_csv_entry(csv_file_name, timestamp, object_type, object_name, old, new):
    try:
        csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Date': timestamp, 'Type': object_type, 'Name': object_name, 'Old': old, 'New': new})
        csv_file.close()
    except Exception:
        raise


# Function to convert UTC string returned by Spotify to datetime object in specified timezone
def convert_utc_str_to_tz_datetime(utc_string, timezone, version=1):
    try:
        if version == 1:
            utc_string_sanitize = utc_string.split('Z', 1)[0]
            dt_utc = datetime.strptime(utc_string_sanitize, '%Y-%m-%dT%H:%M:%S')
        else:
            utc_string_sanitize = utc_string.split(' GMT', 1)[0]
            dt_utc = datetime.strptime(utc_string_sanitize, '%a, %d %b %Y %H:%M:%S')

        old_tz = pytz.timezone("UTC")
        new_tz = pytz.timezone(timezone)
        dt_new_tz = old_tz.localize(dt_utc).astimezone(new_tz)
        return dt_new_tz
    except Exception:
        return datetime.fromtimestamp(0)


# Function to return the timestamp in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]}, {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


# Function to print the current timestamp in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("-----------------------------------------------------------------------------------------------------------------")


# Function to return the timestamp/datetime object in human readable format (long version); eg. Sun 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime("%d %b %Y, %H:%M:%S")}')


# Function to return the timestamp/datetime object in human readable format (short version); eg.
# Sun 21 Apr 15:08
# Sun 21 Apr 24, 15:08 (if show_year == True and current year is different)
# Sun 21 Apr (if show_hour == False)
def get_short_date_from_ts(ts, show_year=False, show_hour=True):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_hour:
        hour_strftime = " %H:%M"
    else:
        hour_strftime = ""

    if show_year and int(datetime.fromtimestamp(ts_new).strftime("%Y")) != int(datetime.now().strftime("%Y")):
        if show_hour:
            hour_prefix = ","
        else:
            hour_prefix = ""
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b %y{hour_prefix}{hour_strftime}")}')
    else:
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b{hour_strftime}")}')


# Function to return the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_seconds:
        out_strf = "%H:%M:%S"
    else:
        out_strf = "%H:%M"
    return (str(datetime.fromtimestamp(ts_new).strftime(out_strf)))


# Function to return the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False):
    if type(ts1) is datetime:
        ts1_new = int(round(ts1.timestamp()))
    elif type(ts1) is int:
        ts1_new = ts1
    elif type(ts1) is float:
        ts1_new = int(round(ts1))
    else:
        return ""

    if type(ts2) is datetime:
        ts2_new = int(round(ts2.timestamp()))
    elif type(ts2) is int:
        ts2_new = ts2
    elif type(ts2) is float:
        ts2_new = int(round(ts2))
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new).strftime("%Y%m%d")

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
    return (str(out_str))


# Signal handler for SIGUSR1 allowing to switch email notifications about profile changes
def toggle_profile_changes_notifications_signal_handler(sig, frame):
    global profile_notification
    profile_notification = not profile_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [profile changes = {profile_notification}]")
    print_cur_ts("Timestamp:\t\t")


# Signal handler for SIGTRAP allowing to increase profile check timer by SPOTIFY_CHECK_SIGNAL_VALUE seconds
def increase_check_signal_handler(sig, frame):
    global SPOTIFY_CHECK_INTERVAL
    SPOTIFY_CHECK_INTERVAL = SPOTIFY_CHECK_INTERVAL + SPOTIFY_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Spotify timers: [check interval: {display_time(SPOTIFY_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t")


# Signal handler for SIGABRT allowing to decrease profile check timer by SPOTIFY_CHECK_SIGNAL_VALUE seconds
def decrease_check_signal_handler(sig, frame):
    global SPOTIFY_CHECK_INTERVAL
    if SPOTIFY_CHECK_INTERVAL - SPOTIFY_CHECK_SIGNAL_VALUE > 0:
        SPOTIFY_CHECK_INTERVAL = SPOTIFY_CHECK_INTERVAL - SPOTIFY_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Spotify timers: [check interval: {display_time(SPOTIFY_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t")


# Function preparing Apple & Genius search URLs for specified track
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


# Function extracting Spotify ID from URI or URL or returning cleaned name
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


# Function returning random user agent string
def get_random_user_agent():
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


# Function removing spaces from a hex string and converting it into a corresponding bytes object
def hex_to_bytes(data: str) -> bytes:
    data = data.replace(" ", "")
    return bytes.fromhex(data)


# Function creating a TOTP object using a secret derived from transformed cipher bytes
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


# Function sending a lightweight request to check token validity
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


# Function retrieving a new Spotify access token using the sp_dc cookie, tries first with mode "transport" and if needed with "init"
def refresh_token(sp_dc: str) -> dict:
    transport = True
    init = True
    session = req.Session()
    session.cookies.set("sp_dc", sp_dc)

    ua = get_random_user_agent()
    totp_obj, server_time = generate_totp(ua)
    client_time = int(time_ns() / 1000 / 1000)
    timestamp = int(time.time())
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
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)
        response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    except (req.RequestException, TimeoutException):
        transport = False
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

    try:
        response.raise_for_status()
    except req.HTTPError:
        transport = False

    try:
        data = response.json()
        token = data.get("accessToken", "")
    except Exception:
        transport = False

    if not transport or (transport and not check_token_validity(data.get("accessToken", ""), data.get("clientId", ""), ua)):
        params["reason"] = "init"
        try:
            if platform.system() != 'Windows':
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(FUNCTION_TIMEOUT + 2)
            response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        except (req.RequestException, TimeoutException):
            init = False
        finally:
            if platform.system() != 'Windows':
                signal.alarm(0)

        try:
            response.raise_for_status()
        except req.HTTPError:
            init = False

        try:
            data = response.json()
            token = data.get("accessToken", "")
        except Exception:
            init = False

    if not init or not data or "accessToken" not in data:
        raise Exception("refresh_token(): Unsuccessful token request")

    return {
        "access_token": token,
        "expires_at": data["accessTokenExpirationTimestampMs"] // 1000,
        "client_id": data.get("clientId", ""),
        "user_agent": ua,
        "length": len(token)
    }


# Function getting Spotify access token based on provided SP_DC value
def spotify_get_access_token(sp_dc: str):
    global SP_CACHED_ACCESS_TOKEN, SP_TOKEN_EXPIRES_AT, SP_CACHED_CLIENT_ID, SP_CACHED_USER_AGENT

    now = time.time()

    if SP_CACHED_ACCESS_TOKEN and now < SP_TOKEN_EXPIRES_AT and check_token_validity(SP_CACHED_ACCESS_TOKEN, SP_CACHED_CLIENT_ID, SP_CACHED_USER_AGENT):
        return SP_CACHED_ACCESS_TOKEN

    # print("-----------------------------------------------------------------------------------------------------------------")
    # print("* Fetching a new Spotify access token, it might take a while ...")

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
#    else:
#        print_cur_ts("Timestamp:\t\t\t")

    return SP_CACHED_ACCESS_TOKEN


# Function removing specified key from list of dictionaries
def remove_key_from_list_of_dicts(list_of_dicts, del_key):
    if list_of_dicts:
        for items in list_of_dicts:
            if del_key in items:
                del items[del_key]


# Function converting Spotify URI (e.g. spotify:user:username) to URL (e.g. https://open.spotify.com/user/username)
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


# Function converting Spotify URL (e.g. https://open.spotify.com/user/username) to URI (e.g. spotify:user:username)
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


# Function returning detailed info about playlist with specified URI (with possibility to get its tracks as well)
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
        sp_playlist_tracks_count = json_response1["tracks"].get("total", 0)
        sp_playlist_tracks = sp_playlist_tracks_concatenated_list
        if sp_playlist_tracks:
            sp_playlist_tracks_count_tmp = len(sp_playlist_tracks)
            if sp_playlist_tracks_count_tmp > 0:
                sp_playlist_tracks_count = sp_playlist_tracks_count_tmp
        sp_playlist_followers_count = int(json_response1["followers"].get("total", 0))
        sp_playlist_url = json_response1["external_urls"].get("spotify") + si

        return {"sp_playlist_name": sp_playlist_name, "sp_playlist_collaborative": sp_playlist_collaborative, "sp_playlist_description": sp_playlist_description, "sp_playlist_owner": sp_playlist_owner, "sp_playlist_owner_url": sp_playlist_owner_url, "sp_playlist_tracks_count": sp_playlist_tracks_count, "sp_playlist_tracks": sp_playlist_tracks, "sp_playlist_followers_count": sp_playlist_followers_count, "sp_playlist_url": sp_playlist_url, "sp_playlist_owner_uri": sp_playlist_owner_uri}

    except Exception:
        raise


# Function returning detailed info about user with specified URI
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


# Function returning followings for user with specified URI
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


# Function returning followers for user with specified URI
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


# Function listing tracks for playlist with specified URI (-l parameter)
def spotify_list_tracks_for_playlist(sp_accessToken, playlist_url):
    print(f"Listing tracks for playlist '{playlist_url}' ...\n")

    user_id_name_mapping = {}

    playlist_uri = spotify_convert_url_to_uri(playlist_url)

    sp_playlist_data = spotify_get_playlist_info(sp_accessToken, playlist_uri, True)

    p_name = sp_playlist_data.get("sp_playlist_name", "")
    p_descr = html.unescape(sp_playlist_data.get("sp_playlist_description", ""))
    p_owner = sp_playlist_data.get("sp_playlist_owner", "")

    print(f"Playlist '{p_name}' owned by '{p_owner}':\n")

    p_likes = sp_playlist_data.get("sp_playlist_followers_count", 0)
    p_tracks = sp_playlist_data.get("sp_playlist_tracks_count", 0)
    p_tracks_list = sp_playlist_data.get("sp_playlist_tracks", None)
    added_at_ts_lowest = 0
    added_at_ts_highest = 0
    duration_sum = 0
    if p_tracks_list is not None:
        for index, track in enumerate(p_tracks_list):
            p_artist = track["track"]["artists"][0].get("name", None)
            p_track = track["track"].get("name", None)
            duration_ms = track["track"].get("duration_ms")
            if p_artist and p_track and int(duration_ms) >= 1000:
                artist_track = f"{p_artist} - {p_track}"
                duration = int(str(duration_ms)[0:-3])
                duration_sum = duration_sum + duration
                added_at_dt = convert_utc_str_to_tz_datetime(track.get("added_at"), LOCAL_TIMEZONE)
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

                added_at_dt_ts = int(added_at_dt.timestamp())
                if index == 0:
                    added_at_ts_lowest = added_at_dt_ts
                    added_at_ts_highest = added_at_dt_ts
                if added_at_dt_ts < added_at_ts_lowest:
                    added_at_ts_lowest = added_at_dt_ts
                if added_at_dt_ts > added_at_ts_highest:
                    added_at_ts_highest = added_at_dt_ts
                added_at_dt_new = datetime.fromtimestamp(int(added_at_dt_ts)).strftime("%d %b %Y, %H:%M:%S")
                added_at_dt_new_week_day = calendar.day_abbr[datetime.fromtimestamp(int(added_at_dt_ts)).weekday()]
                artist_track = artist_track[:75]
                line_new = '%75s    %20s    %3s     %10s' % (artist_track, added_at_dt_new, added_at_dt_new_week_day, added_by_name)
                print(line_new)

    print(f"\nName:\t\t'{p_name}'")
    if p_descr:
        print(f"Description:\t'{p_descr}'")

    print(f"URL:\t\t{playlist_url}\nSongs:\t\t{p_tracks}\nLikes:\t\t{p_likes}")

    if added_at_ts_lowest > 0:
        p_creation_date = get_date_from_ts(int(added_at_ts_lowest))
        p_creation_date_since = calculate_timespan(int(time.time()), int(added_at_ts_lowest))
        print(f"Creation date:\t{p_creation_date} ({p_creation_date_since} ago)")

    if added_at_ts_highest > 0:
        p_last_track_date = get_date_from_ts(int(added_at_ts_highest))
        p_last_track_date_since = calculate_timespan(int(time.time()), int(added_at_ts_highest))
        print(f"Last update:\t{p_last_track_date} ({p_last_track_date_since} ago)")

    print(f"Duration:\t{display_time(duration_sum)}")

    if len(user_id_name_mapping) > 1:
        print(f"\nCollaborators ({len(user_id_name_mapping)}):\n")
        for collab_id, collab_name in user_id_name_mapping.items():
            print(f"- {collab_name} [id: {collab_id}]")


# Function comparing two lists of dictionaries
def compare_two_lists_of_dicts(list1: list, list2: list):
    if not list1:
        list1 = []
    if not list2:
        list2 = []

    diff = [i for i in list1 + list2 if i not in list2]
    return diff


# Function searching for Spotify users (-s parameter)
def spotify_search_users(access_token, username):
    url = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=searchUsers&variables=%7B%22searchTerm%22%3A%22{username}%22%2C%22offset%22%3A0%2C%22limit%22%3A5%2C%22numberOfTopResults%22%3A5%2C%22includeAudiobooks%22%3Afalse%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22{SP_SHA256}%22%7D%7D"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Client-Id": SP_CACHED_CLIENT_ID,
        "User-Agent": SP_CACHED_USER_AGENT,
    }

    print(f"Searching for users with '{username}' string ...\n")

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
            print("-----------------------------------------------")
    else:
        print("No results")


# Function processing items of all passed playlists and returning list of dictionaries
def spotify_process_public_playlists(sp_accessToken, playlists, get_tracks, playlists_to_skip=None):
    list_of_playlists = []
    error_while_processing = False

    if playlists_to_skip is None:
        playlists_to_skip = []

    if playlists:
        for playlist in playlists:
            user_id_name_mapping = {}
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
                    sp_playlist_data = spotify_get_playlist_info(sp_accessToken, p_uri, effective_get_tracks)
                    p_name = sp_playlist_data.get("sp_playlist_name", "")
                    p_descr = html.unescape(sp_playlist_data.get("sp_playlist_description", ""))
                    p_likes = sp_playlist_data.get("sp_playlist_followers_count", 0)
                    p_tracks = sp_playlist_data.get("sp_playlist_tracks_count", 0)
                    p_url = spotify_convert_uri_to_url(p_uri)
                    p_owner = sp_playlist_data.get("sp_playlist_owner", "")
                    p_owner_uri = sp_playlist_data.get("sp_playlist_owner_uri", "")

                    p_tracks_list = sp_playlist_data.get("sp_playlist_tracks", None)
                    added_at_ts_lowest = 0
                    added_at_ts_highest = 0

                    if p_tracks_list:
                        for index, track in enumerate(p_tracks_list):
                            added_at = track.get("added_at")

                            if effective_get_tracks:
                                p_artist = track["track"]["artists"][0].get("name", "")
                                p_track = track["track"].get("name", "")
                                duration_ms = track["track"].get("duration_ms")
                                if p_artist and p_track and int(duration_ms) >= 1000:
                                    track_duration = int(str(duration_ms)[0:-3])
                                    track_uri = track["track"].get("uri")

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
                                added_at_dt = convert_utc_str_to_tz_datetime(added_at, LOCAL_TIMEZONE)
                                added_at_dt_ts = int(added_at_dt.timestamp())
                                added_at_str = get_date_from_ts(added_at_dt_ts)

                                if index == 0:
                                    added_at_ts_lowest = added_at_dt_ts
                                    added_at_ts_highest = added_at_dt_ts
                                if added_at_dt_ts < added_at_ts_lowest:
                                    added_at_ts_lowest = added_at_dt_ts
                                if added_at_dt_ts > added_at_ts_highest:
                                    added_at_ts_highest = added_at_dt_ts
                                added_at_dt_new = datetime.fromtimestamp(int(added_at_dt_ts)).strftime("%d %b %Y, %H:%M:%S")

                            if effective_get_tracks and added_at:
                                list_of_tracks.append({"artist": p_artist, "track": p_track, "duration": track_duration, "added_at": added_at_str, "uri": track_uri, "added_by": added_by_name, "added_by_id": added_by_id})

                except Exception as e:
                    print(f"Error while processing playlist with URI {p_uri}, skipping for now - {e}")
                    print_cur_ts("Timestamp:\t\t")
                    error_while_processing = True
                    continue

                p_creation_date = None
                p_last_track_date = None

                if added_at_ts_lowest > 0:
                    p_creation_date = datetime.fromtimestamp(int(added_at_ts_lowest))

                if added_at_ts_highest > 0:
                    p_last_track_date = datetime.fromtimestamp(int(added_at_ts_highest))

                p_collaborators_count = len(user_id_name_mapping)

                if list_of_tracks and effective_get_tracks:
                    list_of_playlists.append({"uri": p_uri, "name": p_name, "desc": p_descr, "likes": p_likes, "tracks_count": p_tracks, "url": p_url, "date": p_creation_date, "update_date": p_last_track_date, "list_of_tracks": list_of_tracks, "collaborators_count": p_collaborators_count, "collaborators": user_id_name_mapping, "owner": p_owner, "owner_uri": p_owner_uri})
                else:
                    list_of_playlists.append({"uri": p_uri, "name": p_name, "desc": p_descr, "likes": p_likes, "tracks_count": p_tracks, "url": p_url, "date": p_creation_date, "update_date": p_last_track_date, "collaborators_count": p_collaborators_count, "collaborators": {}, "owner": p_owner, "owner_uri": p_owner_uri})

    return list_of_playlists, error_while_processing


# Function printing detailed info about user's playlists
def spotify_print_public_playlists(list_of_playlists, playlists_to_skip=None):
    p_update = datetime.min
    p_update_recent = datetime.min
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
                    p_date_str = p_date.strftime("%d %b %Y, %H:%M:%S")
                    p_date_week_day = calendar.day_abbr[p_date.weekday()]
                    p_date_since = calculate_timespan(int(time.time()), p_date)
                    print(f"[ date: {p_date_week_day} {p_date_str} - {p_date_since} ago ]")
                if p_update:
                    p_update_str = p_update.strftime("%d %b %Y, %H:%M:%S")
                    p_update_week_day = calendar.day_abbr[p_update.weekday()]
                    p_update_since = calculate_timespan(int(time.time()), p_update)
                    print(f"[ update: {p_update_week_day} {p_update_str} - {p_update_since} ago ]")
                if p_descr:
                    print(f"'{p_descr}'")
                print()

            if p_update is not None and p_update > p_update_recent:
                p_update_recent = p_update
                p_name_recent = p_name
                p_url_recent = p_url

        if p_update_recent is not None and p_update_recent > datetime.min and p_name_recent and p_url_recent:
            p_update_recent_str = p_update_recent.strftime("%d %b %Y, %H:%M:%S")
            p_update_recent_week_day = calendar.day_abbr[p_update_recent.weekday()]
            p_update_recent_since = calculate_timespan(int(time.time()), p_update_recent)
            print(f"Recently updated playlist:\n\n- '{p_name_recent}'\n[ {p_url_recent} ]\n[ update: {p_update_recent_week_day} {p_update_recent_str} - {p_update_recent_since} ago ]")


# Function printing detailed info about user with specified URI ID (-i parameter)
def spotify_get_user_details(sp_accessToken, user_uri_id):
    playlists_count = 0
    playlists = None

    print(f"Getting detailed info for user with URI ID '{user_uri_id}' ...\n")

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
            profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file_tmp)))
            print(f"({get_short_date_from_ts(profile_pic_mdate_dt, True)} - {calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False)} ago)")
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
        print(f"\nRecently played artists ({RECENTLY_PLAYED_ARTISTS_LIMIT_INFO}):\n")
        for f_dict in recently_played_artists:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")

    if DETECT_CHANGES_IN_PLAYLISTS:
        print(f"\nPublic playlists:\t{playlists_count}")

        if playlists:
            print("\nGetting list of public playlists (be patient, it might take a while) ...\n")
            list_of_playlists, error_while_processing = spotify_process_public_playlists(sp_accessToken, playlists, True)
            spotify_print_public_playlists(list_of_playlists)


# Function returning recently played artists for user with specified URI (-a parameter)
def spotify_get_recently_played_artists(sp_accessToken, user_uri_id):
    print(f"Getting list of recently played artists for user with URI ID '{user_uri_id}' ...\n")

    sp_user_data = spotify_get_user_info(sp_accessToken, user_uri_id, False, RECENTLY_PLAYED_ARTISTS_LIMIT)

    username = sp_user_data["sp_username"]
    image_url = sp_user_data["sp_user_image_url"]

    recently_played_artists = sp_user_data["sp_user_recently_played_artists"]

    print(f"Username:\t\t{username}")
    print(f"User URI ID:\t\t{user_uri_id}")
    print(f"User URL:\t\t{spotify_convert_uri_to_url(f'spotify:user:{user_uri_id}')}")

    print(f"User profile picture:\t{image_url != ''}")

    if recently_played_artists:
        print(f"\nRecently played artists ({RECENTLY_PLAYED_ARTISTS_LIMIT}):\n")
        for f_dict in recently_played_artists:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
    else:
        print("\nRecently played artists list is empty\n")


# Function printing followers & followings for user with specified URI (-f parameter)
def spotify_get_followers_and_followings(sp_accessToken, user_uri_id):
    print(f"Getting followers & followings for user with URI ID '{user_uri_id}' ...\n")

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

    print("\nFollowers:\t\t", followers_count)
    if followers:
        print()
        for f_dict in followers:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
    print("\nFollowings:\t\t", followings_count)
    if followings:
        print()
        for f_dict in followings:
            if "name" in f_dict and "uri" in f_dict:
                print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")


# Function printing and saving changed list of followers/followings/playlists (with email notifications)
def spotify_print_changed_followers_followings_playlists(username, f_list, f_list_old, f_count, f_old_count, f_str, f_str_by_or_from, f_added_str, f_added_csv, f_removed_str, f_removed_csv, f_file, csv_file_name, profile_notification, is_playlist, sp_accessToken=None):

    f_diff = f_count - f_old_count
    f_diff_str = ""
    if f_diff > 0:
        f_diff_str = "+" + str(f_diff)
    else:
        f_diff_str = str(f_diff)
    print(f"* {f_str} number changed {f_str_by_or_from} user {username} from {f_old_count} to {f_count} ({f_diff_str})\n")
    f_list_to_save = []
    f_list_to_save.append(f_count)
    f_list_to_save.append(f_list)
    try:
        with open(f_file, 'w', encoding="utf-8") as f:
            json.dump(f_list_to_save, f, indent=2)
    except Exception as e:
        print(f"* Cannot save list of {str(f_str).lower()} to '{f_file}' file - {e}")

    try:
        if csv_file_name:
            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), f_str, username, f_old_count, f_count)
    except Exception as e:
        print(f"* Cannot write CSV entry - {e}")

    removed_f_list = compare_two_lists_of_dicts(f_list_old, f_list)
    added_f_list = compare_two_lists_of_dicts(f_list, f_list_old)
    list_of_added_f_list = ""
    list_of_removed_f_list = ""
    added_f_list_mbody = ""
    removed_f_list_mbody = ""
    if added_f_list:
        print(f"{f_added_str}:\n")
        added_f_list_mbody = f"\n{f_added_str}:\n\n"
        for f_dict in added_f_list:
            if is_playlist:
                if "uri" in f_dict:
                    try:
                        sp_playlist_data = spotify_get_playlist_info(sp_accessToken, f_dict["uri"], False)
                    except Exception as e:
                        print(f"- Error while getting info for playlist with URI {f_dict['uri']}, skipping for now - {e}")
                        list_of_added_f_list += f"- Error while getting info for playlist with URI {f_dict['uri']}\n"
                        print_cur_ts("Timestamp:\t\t")
                        continue
                    p_name = sp_playlist_data.get("sp_playlist_name")
                    print(f"- {p_name} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                    list_of_added_f_list += f"- {p_name} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]\n"
                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), f_added_csv, username, "", p_name)
                    except Exception as e:
                        print(f"* Cannot write CSV entry - {e}")
            else:
                if "name" in f_dict and "uri" in f_dict:
                    print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                    list_of_added_f_list += f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]\n"
                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), f_added_csv, username, "", f_dict["name"])
                    except Exception as e:
                        print(f"* Cannot write CSV entry - {e}")
        print()
    if removed_f_list:
        print(f"{f_removed_str}:\n")
        removed_f_list_mbody = f"\n{f_removed_str}:\n\n"
        for f_dict in removed_f_list:
            if is_playlist:
                if "uri" in f_dict:
                    try:
                        sp_playlist_data = spotify_get_playlist_info(sp_accessToken, f_dict["uri"], False)
                    except Exception as e:
                        if 'Not Found' in str(e):
                            print(f"- Playlist has been removed or set to private [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                            list_of_removed_f_list += f"- Playlist has been removed or set to private [ {spotify_convert_uri_to_url(f_dict['uri'])} ]\n"
                        else:
                            print(f"- Error while getting info for playlist with URI {f_dict['uri']}, skipping for now - {e}")
                            list_of_removed_f_list += f"- Error while getting info for playlist with URI {f_dict['uri']}\n"
                            print_cur_ts("Timestamp:\t\t")
                        continue
                    p_name = sp_playlist_data.get("sp_playlist_name")
                    print(f"- {p_name} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                    list_of_removed_f_list += f"- {p_name} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]\n"
                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), f_removed_csv, username, p_name, "")
                    except Exception as e:
                        print(f"* Cannot write CSV entry - {e}")
            else:
                if "name" in f_dict and "uri" in f_dict:
                    print(f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]")
                    list_of_removed_f_list += f"- {f_dict['name']} [ {spotify_convert_uri_to_url(f_dict['uri'])} ]\n"
                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), f_removed_csv, username, f_dict["name"], "")
                    except Exception as e:
                        print(f"* Cannot write CSV entry - {e}")
        print()

    if (f_str == "Followers" or f_str == "Followings") and not followers_followings_notification:
        return

    if profile_notification:

        m_subject = f"Spotify user {username} {str(f_str).lower()} number has changed! ({f_diff_str}, {f_old_count} -> {f_count})"
        m_body = f"{f_str} number changed {f_str_by_or_from} user {username} from {f_old_count} to {f_count} ({f_diff_str})\n{removed_f_list_mbody}{list_of_removed_f_list}{added_f_list_mbody}{list_of_added_f_list}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"

        print(f"Sending email notification to {RECEIVER_EMAIL}")
        send_email(m_subject, m_body, "", SMTP_SSL)


# Function saving user's profile pic to selected file name
def save_profile_pic(user_image_url, image_file_name):
    try:
        image_response = req.get(user_image_url, timeout=FUNCTION_TIMEOUT, stream=True, verify=VERIFY_SSL)
        image_response.raise_for_status()
        url_time = image_response.headers.get('last-modified')
        url_time_in_tz_ts = 0
        if url_time:
            url_time_in_tz = convert_utc_str_to_tz_datetime(url_time, LOCAL_TIMEZONE, 2)
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


# Function comparing two image files
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
        print(f"Error while comparing profile pictures - {e}")
        return False


# Main function monitoring profile changes of the specified Spotify user URI ID
def spotify_profile_monitor_uri(user_uri_id, error_notification, csv_file_name, csv_exists, playlists_to_skip):
    global SP_CACHED_ACCESS_TOKEN
    playlists_count = 0
    playlists_old_count = 0
    playlists = None
    playlists_old = None
    playlists_zeroed_counter = 0

    try:
        if csv_file_name:
            csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print(f"* Error - {e}")

    email_sent = False

    out = f"Monitoring user {user_uri_id}"
    print(out)
    print("-" * len(out))

    try:
        sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
        sp_user_data = spotify_get_user_info(sp_accessToken, user_uri_id, DETECT_CHANGES_IN_PLAYLISTS, 0)
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
            print(f"Error: {e}")
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

    recently_played_artists = sp_user_data["sp_user_recently_played_artists"]

    print(f"Username:\t\t{username}")
    print(f"User URI ID:\t\t{user_uri_id}")
    print(f"User URL:\t\t{spotify_convert_uri_to_url(f'spotify:user:{user_uri_id}')}")

    print(f"User profile picture:\t{image_url != ''}")

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

    print(f"\nFollowers:\t\t{followers_count}")
    print(f"Followings:\t\t{followings_count}")

    list_of_playlists = []

    if DETECT_CHANGES_IN_PLAYLISTS:
        print(f"Public playlists:\t{playlists_count}")

        if playlists:
            print("\n* Getting list of public playlists (be patient, it might take a while) ...\n")
            list_of_playlists, error_while_processing = spotify_process_public_playlists(sp_accessToken, playlists, True, playlists_to_skip)
            spotify_print_public_playlists(list_of_playlists, playlists_to_skip)

    print_cur_ts("\nTimestamp:\t\t")

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
                print(f"* Cannot load entries from '{playlists_file}' file - {e}")
            if playlists_read:
                playlists_old_count = playlists_read[0]
                playlists_old = playlists_read[1]
                playlists_mdate = datetime.fromtimestamp(int(os.path.getmtime(playlists_file))).strftime("%d %b %Y, %H:%M:%S")
                print(f"* Playlists ({playlists_old_count}) loaded from file '{playlists_file}' ({playlists_mdate})")
        if not playlists_read:
            playlists_to_save = []
            playlists_to_save.append(playlists_count)
            playlists_to_save.append(playlists)
            try:
                with open(playlists_file, 'w', encoding="utf-8") as f:
                    json.dump(playlists_to_save, f, indent=2)
                print(f"* Playlists ({playlists_count}) saved to file '{playlists_file}'")
            except Exception as e:
                print(f"* Cannot save list of playlists to '{playlists_file}' file - {e}")

        if playlists_count != playlists_old_count:
            spotify_print_changed_followers_followings_playlists(username, playlists, playlists_old, playlists_count, playlists_old_count, "Playlists", "for", "Added playlists", "Added Playlist", "Removed playlists", "Removed Playlist", playlists_file, csv_file_name, False, True, sp_accessToken)

        print_cur_ts("Timestamp:\t\t")

    # followers
    if os.path.isfile(followers_file):
        try:
            with open(followers_file, 'r', encoding="utf-8") as f:
                followers_read = json.load(f)
        except Exception as e:
            print(f"* Cannot load entries from '{followers_file}' file - {e}")
        if followers_read:
            followers_old_count = followers_read[0]
            followers_old = followers_read[1]
            followers_mdate = datetime.fromtimestamp(int(os.path.getmtime(followers_file))).strftime("%d %b %Y, %H:%M:%S")
            print(f"* Followers ({followers_old_count}) loaded from file '{followers_file}' ({followers_mdate})")
    if not followers_read:
        followers_to_save = []
        followers_to_save.append(followers_count)
        followers_to_save.append(followers)
        try:
            with open(followers_file, 'w', encoding="utf-8") as f:
                json.dump(followers_to_save, f, indent=2)
            print(f"* Followers ({followers_count}) saved to file '{followers_file}'")
        except Exception as e:
            print(f"* Cannot save list of followers to '{followers_file}' file - {e}")

    if followers_count != followers_old_count:
        spotify_print_changed_followers_followings_playlists(username, followers, followers_old, followers_count, followers_old_count, "Followers", "for", "Added followers", "Added Follower", "Removed followers", "Removed Follower", followers_file, csv_file_name, False, False)

    print_cur_ts("Timestamp:\t\t")

    # followings
    if os.path.isfile(followings_file):
        try:
            with open(followings_file, 'r', encoding="utf-8") as f:
                followings_read = json.load(f)
        except Exception as e:
            print(f"* Cannot load entries from '{followings_file}' file - {e}")
        if followings_read:
            followings_old_count = followings_read[0]
            followings_old = followings_read[1]
            followings_mdate = datetime.fromtimestamp(int(os.path.getmtime(followings_file))).strftime("%d %b %Y, %H:%M:%S")
            print(f"* Followings ({followings_old_count}) loaded from file '{followings_file}' ({followings_mdate})")
    if not followings_read:
        followings_to_save = []
        followings_to_save.append(followings_count)
        followings_to_save.append(followings)
        try:
            with open(followings_file, 'w', encoding="utf-8") as f:
                json.dump(followings_to_save, f, indent=2)
            print(f"* Followings ({followings_count}) saved to file '{followings_file}'")
        except Exception as e:
            print(f"* Cannot save list of followings to '{followings_file}' file - {e}")

    if followings_count != followings_old_count:
        spotify_print_changed_followers_followings_playlists(username, followings, followings_old, followings_count, followings_old_count, "Followings", "by", "Added followings", "Added Following", "Removed followings", "Removed Following", followings_file, csv_file_name, False, False)

    print_cur_ts("Timestamp:\t\t")

    # profile pic

    if DETECT_CHANGED_PROFILE_PIC:

        # user has no profile pic, but it exists in the filesystem
        if not image_url and os.path.isfile(profile_pic_file):
            profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)))
            print(f"* User {username} has removed profile picture added on {get_short_date_from_ts(profile_pic_mdate_dt, True)} ! (after {calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False, granularity=2)})")
            os.replace(profile_pic_file, profile_pic_file_old)

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Profile Picture Removed", username, profile_pic_mdate_dt, "")
            except Exception as e:
                print(f"* Cannot write CSV entry - {e}")

            print_cur_ts("Timestamp:\t\t")

        # user has profile pic, but it does not exist in the filesystem
        elif image_url and not os.path.isfile(profile_pic_file):
            if save_profile_pic(image_url, profile_pic_file):
                profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)))
                print(f"* User {username} profile picture saved to '{profile_pic_file}'")
                print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, True)} ({calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False)} ago)")

                try:
                    if IMGCAT_PATH and os.path.isfile(IMGCAT_PATH):
                        subprocess.call((f'echo;{IMGCAT_PATH} {profile_pic_file};echo'), shell=True)
                    shutil.copy2(profile_pic_file, f'spotify_profile_{file_suffix}_pic_{profile_pic_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                except Exception:
                    pass

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Profile Picture Created", username, "", profile_pic_mdate_dt)
                except Exception as e:
                    print(f"* Cannot write CSV entry - {e}")

            else:
                print(f"Error saving profile picture !")

            print_cur_ts("Timestamp:\t\t")

        # user has profile pic and it exists in the filesystem, but we check if it has not changed
        elif image_url and os.path.isfile(profile_pic_file):
            profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)))
            if save_profile_pic(image_url, profile_pic_file_tmp):
                profile_pic_tmp_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file_tmp)))

                if not compare_images(profile_pic_file, profile_pic_file_tmp) and profile_pic_mdate_dt != profile_pic_tmp_mdate_dt:
                    print(f"* User {username} has changed profile picture ! (previous one added on {get_short_date_from_ts(profile_pic_mdate_dt, True)} - {calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)")
                    print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_tmp_mdate_dt, True)} ({calculate_timespan(int(time.time()), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)")

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Profile Picture Changed", username, profile_pic_mdate_dt, profile_pic_tmp_mdate_dt)
                    except Exception as e:
                        print(f"* Cannot write CSV entry - {e}")

                    try:
                        if IMGCAT_PATH and os.path.isfile(IMGCAT_PATH):
                            subprocess.call((f'echo;{IMGCAT_PATH} {profile_pic_file_tmp};echo'), shell=True)
                        shutil.copy2(profile_pic_file_tmp, f'spotify_profile_{file_suffix}_pic_{profile_pic_tmp_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                        os.replace(profile_pic_file, profile_pic_file_old)
                        os.replace(profile_pic_file_tmp, profile_pic_file)
                    except Exception as e:
                        print(f"Error while replacing/copying files - {e}")

                else:
                    print(f"* Profile picture '{profile_pic_file}' already exists")
                    print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, True)} ({calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False)} ago)")
                    try:
                        os.remove(profile_pic_file_tmp)
                    except Exception:
                        pass
            else:
                print(f"Error while checking if the profile picture has changed !")
            print_cur_ts("Timestamp:\t\t")

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
            print_cur_ts("Timestamp:\t\t")
            time.sleep(ALARM_RETRY)
            continue
        except Exception as e:
            if platform.system() != 'Windows':
                signal.alarm(0)
            print(f"Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)} - {e}")
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
            print_cur_ts("Timestamp:\t\t")
            time.sleep(SPOTIFY_ERROR_INTERVAL)
            continue

        username = sp_user_data["sp_username"]
        image_url = sp_user_data["sp_user_image_url"]

        # Spotify username has changed
        if username != username_old:
            print(f"* User '{username_old}' has changed username to '{username}'")

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Username", username, username_old, username)
            except Exception as e:
                print(f"* Cannot write CSV entry - {e}")

            if profile_notification:
                m_subject = f"Spotify user {username_old} has changed username to {username}"
                m_body = f"Spotify user '{username_old}' has changed username to '{username}'\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, "", SMTP_SSL)

            username_old = username

            print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
            print_cur_ts("Timestamp:\t\t")

        try:
            sp_user_followings_data = spotify_get_user_followings(sp_accessToken, user_uri_id)
            sp_user_followers_data = spotify_get_user_followers(sp_accessToken, user_uri_id)
        except Exception as e:
            print(f"Error while getting followers & followings, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)} - {e}")
            print_cur_ts("Timestamp:\t\t")
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

            print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
            print_cur_ts("Timestamp:\t\t")

        if followings_count != followings_old_count:
            spotify_print_changed_followers_followings_playlists(username, followings, followings_old, followings_count, followings_old_count, "Followings", "by", "Added followings", "Added Following", "Removed followings", "Removed Following", followings_file, csv_file_name, profile_notification, False)

            followings_old_count = followings_count
            followings_old = followings

            print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
            print_cur_ts("Timestamp:\t\t")

        # profile pic

        if DETECT_CHANGED_PROFILE_PIC:

            # user has no profile pic, but it exists in the filesystem
            if not image_url and os.path.isfile(profile_pic_file):
                profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)))
                print(f"* User {username} has removed profile picture added on {get_short_date_from_ts(profile_pic_mdate_dt, True)} ! (after {calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False, granularity=2)})\n")
                os.replace(profile_pic_file, profile_pic_file_old)

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Profile Picture Removed", username, profile_pic_mdate_dt, "")
                except Exception as e:
                    print(f"* Cannot write CSV entry - {e}")

                if profile_notification:
                    m_subject = f"Spotify user {username} has removed profile picture ! (after {calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False, granularity=2)})"
                    m_body = f"Spotify user {username} has removed profile picture added on {get_short_date_from_ts(profile_pic_mdate_dt, True)} (after {calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False, granularity=2)})\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)

                print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                print_cur_ts("Timestamp:\t\t")

            # user has profile pic, but it does not exist in the filesystem
            elif image_url and not os.path.isfile(profile_pic_file):
                print(f"* User {username} has set profile picture !")
                m_body_html_pic_saved_text = ""
                if save_profile_pic(image_url, profile_pic_file):
                    profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)))
                    print(f"* User profile picture saved to '{profile_pic_file}'")
                    print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, True)} ({calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False)} ago)\n")
                    m_body_html_pic_saved_text = f'<br><br><img src="cid:profile_pic">'

                    try:
                        if IMGCAT_PATH and os.path.isfile(IMGCAT_PATH):
                            subprocess.call((f'{IMGCAT_PATH} {profile_pic_file};echo'), shell=True)
                        shutil.copy2(profile_pic_file, f'spotify_profile_{file_suffix}_pic_{profile_pic_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                    except Exception:
                        pass

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Profile Picture Created", username, "", profile_pic_mdate_dt)
                    except Exception as e:
                        print(f"* Cannot write CSV entry - {e}")

                    if profile_notification:
                        m_subject = f"Spotify user {username} has set profile picture ! ({get_short_date_from_ts(profile_pic_mdate_dt, True)})"
                        m_body = f"Spotify user {username} has set profile picture !\n\nProfile picture has been added on {get_short_date_from_ts(profile_pic_mdate_dt, True)} ({calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False)} ago)\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"Spotify user <b>{username}</b> has set profile picture !{m_body_html_pic_saved_text}<br><br>Profile picture has been added on <b>{get_short_date_from_ts(profile_pic_mdate_dt, True)}</b> ({calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False)} ago)<br><br>Check interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts('<br>Timestamp: ')}"
                        print(f"Sending email notification to {RECEIVER_EMAIL}")

                        send_email(m_subject, m_body, m_body_html, SMTP_SSL, profile_pic_file, "profile_pic")

                else:
                    print(f"Error saving profile picture !\n")

                print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                print_cur_ts("Timestamp:\t\t")

            # user has profile pic and it exists in the filesystem, but we check if it has not changed
            elif image_url and os.path.isfile(profile_pic_file):
                profile_pic_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file)))
                if save_profile_pic(image_url, profile_pic_file_tmp):
                    profile_pic_tmp_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(profile_pic_file_tmp)))

                    if not compare_images(profile_pic_file, profile_pic_file_tmp) and profile_pic_mdate_dt != profile_pic_tmp_mdate_dt:
                        print(f"* User {username} has changed profile picture ! (previous one added on {get_short_date_from_ts(profile_pic_mdate_dt, True)} - {calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)")
                        print(f"* Profile picture has been added on {get_short_date_from_ts(profile_pic_tmp_mdate_dt, True)} ({calculate_timespan(int(time.time()), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)\n")
                        m_body_html_pic_saved_text = ""

                        try:
                            if csv_file_name:
                                write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Profile Picture Changed", username, profile_pic_mdate_dt, profile_pic_tmp_mdate_dt)
                        except Exception as e:
                            print(f"* Cannot write CSV entry - {e}")

                        try:
                            if IMGCAT_PATH and os.path.isfile(IMGCAT_PATH):
                                subprocess.call((f'{IMGCAT_PATH} {profile_pic_file_tmp};echo'), shell=True)
                            shutil.copy2(profile_pic_file_tmp, f'spotify_profile_{file_suffix}_pic_{profile_pic_tmp_mdate_dt.strftime("%Y%m%d_%H%M")}.jpeg')
                            os.replace(profile_pic_file, profile_pic_file_old)
                            os.replace(profile_pic_file_tmp, profile_pic_file)
                        except Exception as e:
                            print(f"Error while replacing/copying files - {e}")

                        if profile_notification:
                            m_body_html_pic_saved_text = f'<br><br><img src="cid:profile_pic">'
                            m_subject = f"Spotify user {username} has changed profile picture ! (after {calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False, granularity=2)})"
                            m_body = f"Spotify user {username} has changed profile picture !\n\nPrevious one added on {get_short_date_from_ts(profile_pic_mdate_dt, True)} ({calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)\n\nProfile picture has been added on {get_short_date_from_ts(profile_pic_tmp_mdate_dt, True)} ({calculate_timespan(int(time.time()), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)\n\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                            m_body_html = f"Spotify user <b>{username}</b> has changed profile picture !{m_body_html_pic_saved_text}<br><br>Previous one added on <b>{get_short_date_from_ts(profile_pic_mdate_dt, True)}</b> ({calculate_timespan(int(time.time()), profile_pic_mdate_dt, show_seconds=False, granularity=2)} ago)<br><br>Profile picture has been added on <b>{get_short_date_from_ts(profile_pic_tmp_mdate_dt, True)}</b> ({calculate_timespan(int(time.time()), profile_pic_tmp_mdate_dt, show_seconds=False)} ago)<br><br>Check interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts('<br>Timestamp: ')}"
                            print(f"Sending email notification to {RECEIVER_EMAIL}")
                            send_email(m_subject, m_body, m_body_html, SMTP_SSL, profile_pic_file, "profile_pic")

                        print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                        print_cur_ts("Timestamp:\t\t")
                    else:
                        try:
                            os.remove(profile_pic_file_tmp)
                        except Exception:
                            pass
                else:
                    print(f"Error while checking if the profile pic has changed !\n")
                    print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t")

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
                                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Playlist Likes", p_name, p_likes_old, p_likes)
                                    except Exception as e:
                                        print(f"* Cannot write CSV entry - {e}")
                                    m_subject = f"Spotify user {username} number of likes for playlist '{p_name}' has changed! ({p_likes_diff_str}, {p_likes_old} -> {p_likes})"
                                    m_body = f"{p_message}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    if profile_notification:
                                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                                        send_email(m_subject, m_body, "", SMTP_SSL)
                                    print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t")

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
                                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Collaborators Number", p_name, p_collaborators_old, p_collaborators)
                                    except Exception as e:
                                        print(f"* Cannot write CSV entry - {e}")

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
                                                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Added Collaborator", p_name, "", collab_name)
                                            except Exception as e:
                                                print(f"* Cannot write CSV entry - {e}")

                                        p_message_added_collaborators += "\n"
                                        print(p_message_added_collaborators, end="")

                                    if removed_collaborators:
                                        p_message_removed_collaborators = "Removed collaborators:\n\n"

                                        for collab_id, collab_name in removed_collaborators.items():
                                            removed_collab = f'- {collab_name} [ {spotify_convert_uri_to_url(f"spotify:user:{collab_id}")} ]\n'
                                            p_message_removed_collaborators += removed_collab
                                            try:
                                                if csv_file_name:
                                                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Removed Collaborator", p_name, collab_name, "")
                                            except Exception as e:
                                                print(f"* Cannot write CSV entry - {e}")

                                        p_message_removed_collaborators += "\n"
                                        print(p_message_removed_collaborators, end="")

                                    m_subject = f"Spotify user {username} number of collaborators for playlist '{p_name}' has changed! ({p_collaborators_diff_str}, {p_collaborators_old} -> {p_collaborators})"
                                    m_body = f"{p_message}\n{p_message_added_collaborators}{p_message_removed_collaborators}Check interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    if profile_notification:
                                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                                        send_email(m_subject, m_body, "", SMTP_SSL)
                                    print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t")

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
                                            p_update = datetime.fromtimestamp(int(time.time()))

                                        if p_update and p_update_old:
                                            if p_update < p_update_old or p_update == p_update_old:
                                                p_update = datetime.fromtimestamp(int(time.time()))

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
                                        print(f"Error while processing data for playlist with URI {p_uri}, skipping for now - {e}")
                                        print_cur_ts("Timestamp:\t\t")
                                        continue
                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Playlist Number of Tracks", p_name, p_tracks_old, p_tracks)
                                    except Exception as e:
                                        print(f"* Cannot write CSV entry - {e}")
                                    removed_tracks = compare_two_lists_of_dicts(p_tracks_list_old, p_tracks_list)
                                    added_tracks = compare_two_lists_of_dicts(p_tracks_list, p_tracks_list_old)
                                    p_message_added_tracks = ""
                                    p_message_removed_tracks = ""

                                    if added_tracks:
                                        print("Added tracks:\n")
                                        p_message_added_tracks = "Added tracks:\n\n"

                                        for f_dict in added_tracks:
                                            if "artist" in f_dict and "track" in f_dict:
                                                apple_search_url, genius_search_url, youtube_music_search_url = get_apple_genius_search_urls(f_dict["artist"], f_dict["track"])
                                                tempuri = f'spotify:user:{f_dict["added_by_id"]}'
                                                added_track = f'- {f_dict["artist"]} - {f_dict["track"]} [ {f_dict["added_at"]}, {f_dict["added_by"]} ]\n[ Spotify URL: {spotify_convert_uri_to_url(f_dict["uri"])} ]\n[ Apple Music URL: {apple_search_url} ]\n[ YouTube Music URL: {youtube_music_search_url} ]\n[ Genius URL: {genius_search_url} ]\n[ Collaborator URL: {spotify_convert_uri_to_url(tempuri)} ]\n\n'
                                                p_message_added_tracks += added_track
                                                added_at_dt = datetime.strptime(f_dict['added_at'], "%a %d %b %Y, %H:%M:%S")
                                                print(added_track, end="")
                                                try:
                                                    if csv_file_name:
                                                        write_csv_entry(csv_file_name, added_at_dt, "Added Track", p_name, f_dict['added_by'], f_dict["artist"] + " - " + f_dict["track"])
                                                except Exception as e:
                                                    print(f"* Cannot write CSV entry - {e}")

                                    if removed_tracks:
                                        print("Removed tracks:\n")
                                        p_message_removed_tracks = "Removed tracks:\n\n"

                                        for f_dict in removed_tracks:
                                            if "artist" in f_dict and "track" in f_dict:
                                                apple_search_url, genius_search_url, youtube_music_search_url = get_apple_genius_search_urls(f_dict["artist"], f_dict["track"])
                                                tempuri = f'spotify:user:{f_dict["added_by_id"]}'
                                                removed_track = f'- {f_dict["artist"]} - {f_dict["track"]} [ {f_dict["added_at"]}, {f_dict["added_by"]} ]\n[ Spotify URL: {spotify_convert_uri_to_url(f_dict["uri"])} ]\n[ Apple Music URL: {apple_search_url} ]\n[ YouTube Music URL: {youtube_music_search_url} ]\n[ Genius URL: {genius_search_url} ]\n[ Collaborator URL: {spotify_convert_uri_to_url(tempuri)} ]\n\n'
                                                p_message_removed_tracks += removed_track
                                                print(removed_track, end="")
                                                try:
                                                    if csv_file_name:
                                                        write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Removed Track", p_name, f_dict["artist"] + " - " + f_dict["track"], "")
                                                except Exception as e:
                                                    print(f"* Cannot write CSV entry - {e}")

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
                                    print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t")

                                # Playlist name changed
                                if p_name != p_name_old:
                                    p_message = f"* Playlist '{p_name_old}': name changed to new name '{p_name}'\n* Playlist URL: {p_url}\n"
                                    print(p_message)
                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Playlist Name", username, p_name_old, p_name)
                                    except Exception as e:
                                        print(f"* Cannot write CSV entry - {e}")
                                    m_subject = f"Spotify user {username} playlist '{p_name_old}' name changed to '{p_name}'!"
                                    m_body = f"{p_message}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    if profile_notification:
                                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                                        send_email(m_subject, m_body, "", SMTP_SSL)
                                    print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t")

                                # Playlist description changed
                                if p_descr != p_descr_old:
                                    p_message = f"* Playlist '{p_name}' description changed from:\n\n'{p_descr_old}'\n\nto:\n\n'{p_descr}'\n\n* Playlist URL: {p_url}\n"
                                    print(p_message)
                                    try:
                                        if csv_file_name:
                                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), "Playlist Description", p_name, p_descr_old, p_descr)
                                    except Exception as e:
                                        print(f"* Cannot write CSV entry - {e}")
                                    m_subject = f"Spotify user {username} playlist '{p_name}' description has changed !"
                                    m_body = f"{p_message}\nCheck interval: {display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)}){get_cur_ts(nl_ch + 'Timestamp: ')}"
                                    if profile_notification:
                                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                                        send_email(m_subject, m_body, "", SMTP_SSL)
                                    print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                                    print_cur_ts("Timestamp:\t\t")

            if not error_while_processing:
                list_of_playlists_old = list_of_playlists

            if playlists_count != playlists_old_count and (playlists or (not playlists and playlists_count == 0)):

                if playlists_count == 0:
                    playlists_zeroed_counter += 1
                else:
                    playlists_zeroed_counter = 0

                if playlists_zeroed_counter == PLAYLISTS_DISAPPEARED_COUNTER or playlists_count > 0:
                    spotify_print_changed_followers_followings_playlists(username, playlists, playlists_old, playlists_count, playlists_old_count, "Playlists", "for", "Added playlists", "Added Playlist", "Removed playlists", "Removed Playlist", playlists_file, csv_file_name, profile_notification, True, sp_accessToken)

                    playlists_old_count = playlists_count
                    playlists_old = playlists
                    playlists_zeroed_counter = 0

                    print(f"Check interval:\t\t{display_time(SPOTIFY_CHECK_INTERVAL)} ({get_range_of_dates_from_tss(int(time.time()) - SPOTIFY_CHECK_INTERVAL, int(time.time()), short=True)})")
                    print_cur_ts("Timestamp:\t\t")

        alive_counter += 1

        if alive_counter >= TOOL_ALIVE_COUNTER:
            print_cur_ts("Alive check, timestamp: ")
            alive_counter = 0

        time.sleep(SPOTIFY_CHECK_INTERVAL)


if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        print("* Cannot clear the screen contents")

    print(f"Spotify Profile Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser("spotify_profile_monitor")
    parser.add_argument("SPOTIFY_USER_URI_ID", nargs="?", help="Spotify user URI ID", type=str)
    parser.add_argument("-u", "--spotify_dc_cookie", help="Spotify sp_dc cookie to override the value defined within the script (SP_DC_COOKIE)", type=str)
    parser.add_argument("-p", "--profile_notification", help="Send email notification once user's profile changes (followers & followings, public playlists and its tracks, likes for playlists, profile picture)", action='store_true')
    parser.add_argument("-g", "--disable_followers_followings_notification", help="Disable sending email notifications about new followers/followings (it is sent by default when -p / --profile_notification is enabled)", action='store_false')
    parser.add_argument("-e", "--error_notification", help="Disable sending email notifications in case of errors like expired sp_dc", action='store_false')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks, in seconds", type=int)
    parser.add_argument("-m", "--error_interval", help="Time between error checks, in seconds", type=int)
    parser.add_argument("-b", "--csv_file", help="Write all profile changes to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-t", "--playlists_to_skip", help="Filename with Spotify playlists to ignore from monitoring (so it won't report changed tracks and number of likes for them); playlists can be blacklisted by its URI and URL, but also owner name, URI and URL", type=str, metavar="IGNORED_PLAYLISTS_FILENAME")
    parser.add_argument("-j", "--do_not_detect_changed_profile_pic", help="Disable detection of changed user's profile picture in monitoring mode", action='store_false')
    parser.add_argument("-q", "--do_not_monitor_playlists", help="Disable detection of changes in user's public playlists in monitoring mode (like added/removed tracks in playlists, playlists name and description changes, number of likes for playlists)", action='store_false')
    parser.add_argument("-k", "--get_all_playlists", help="By default, only public playlists owned by the user are fetched; you can change this behavior with this parameter; it is helpful in the case of playlists created by another user added to another user profile", action='store_true')
    parser.add_argument("-l", "--list_tracks_for_playlist", help="List all tracks for specific Spotify playlist URL", type=str, metavar="SPOTIFY_PLAYLIST_URL")
    parser.add_argument("-i", "--user_profile_details", help="Show profile details for user with specific Spotify URI ID (playlists, followers, followings, recently played artists etc.)", action='store_true')
    parser.add_argument("-a", "--recently_played_artists", help="List recently played artists for user with specific Spotify URI ID", action='store_true')
    parser.add_argument("-f", "--followers_and_followings", help="List followers & followings for user with specific Spotify URI ID", action='store_true')
    parser.add_argument("-s", "--search_username", help="Search for users with specific name to get their Spotify user URI ID", type=str, metavar="SPOTIFY_USERNAME")
    parser.add_argument("-d", "--disable_logging", help="Disable output logging to file 'spotify_profile_monitor_UserURIID.log' file", action='store_true')
    parser.add_argument("-y", "--file_suffix", help="File suffix to be used instead of Spotify user URI ID for different file names like output log file, json files, profile picture jpeg files", type=str, metavar="FILE_SUFFIX")
    parser.add_argument("-z", "--send_test_email_notification", help="Send test email notification to verify SMTP settings defined in the script", action='store_true')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    local_tz = None
    if LOCAL_TIMEZONE == "Auto":
        try:
            local_tz = get_localzone()
        except NameError:
            pass
        if local_tz:
            LOCAL_TIMEZONE = str(local_tz)
        else:
            print("* Error: Cannot detect local timezone, consider setting LOCAL_TIMEZONE manually !")
            sys.exit(1)

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.send_test_email_notification:
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

    if args.list_tracks_for_playlist:
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            spotify_list_tracks_for_playlist(sp_accessToken, args.list_tracks_for_playlist)
        except Exception as e:
            if 'Not Found' in str(e) or '400 Client' in str(e):
                print("* Error: playlist does not exist or is set to private")
            else:
                print(f"* Error - {e}")
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
            print(f"* Error - {e}")
            sys.exit(1)
        sys.exit(0)

    if not args.SPOTIFY_USER_URI_ID:
        print("* Error: SPOTIFY_USER_URI_ID argument is required !")
        sys.exit(1)

    if args.user_profile_details:
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            spotify_get_user_details(sp_accessToken, args.SPOTIFY_USER_URI_ID)
        except Exception as e:
            if 'Not Found' in str(e) or '404 Client' in str(e):
                print("* Error: user does not exist")
            else:
                print(f"* Error - {e}")
            sys.exit(1)
        sys.exit(0)

    if args.recently_played_artists:
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            spotify_get_recently_played_artists(sp_accessToken, args.SPOTIFY_USER_URI_ID)
        except Exception as e:
            if 'Not Found' in str(e) or '404 Client' in str(e):
                print("* Error: user does not exist")
            else:
                print(f"* Error - {e}")
            sys.exit(1)
        sys.exit(0)

    if args.followers_and_followings:
        try:
            sp_accessToken = spotify_get_access_token(SP_DC_COOKIE)
            spotify_get_followers_and_followings(sp_accessToken, args.SPOTIFY_USER_URI_ID)
        except Exception as e:
            if 'Not Found' in str(e) or '404 Client' in str(e):
                print("* Error: user does not exist")
            else:
                print(f"* Error - {e}")
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
            print(f"* Error: file with playlists to ignore cannot be opened - {e}")
            sys.exit(1)
    else:
        playlists_to_skip = []

    if args.csv_file:
        csv_enabled = True
        csv_exists = os.path.isfile(args.csv_file)
        try:
            csv_file = open(args.csv_file, 'a', newline='', buffering=1, encoding="utf-8")
        except Exception as e:
            print(f"* Error: CSV file cannot be opened for writing - {e}")
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled = False
        csv_file = None
        csv_exists = False

    if args.file_suffix:
        file_suffix = str(args.file_suffix)
    else:
        file_suffix = str(args.SPOTIFY_USER_URI_ID)

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
    print(f"* Detect changed profile pic:\t{DETECT_CHANGED_PROFILE_PIC}")
    print(f"* Detect changes in playlists:\t{DETECT_CHANGES_IN_PLAYLISTS}")
    print(f"* Get all public playlists:\t{GET_ALL_PLAYLISTS}")
    if not args.disable_logging:
        print(f"* Output logging enabled:\t{not args.disable_logging} ({SP_LOGFILE})")
    else:
        print(f"* Output logging enabled:\t{not args.disable_logging}")
    if csv_enabled:
        print(f"* CSV logging enabled:\t\t{csv_enabled} ({args.csv_file})")
    else:
        print(f"* CSV logging enabled:\t\t{csv_enabled}")
    print(f"* Local timezone:\t\t{LOCAL_TIMEZONE}\n")

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_profile_changes_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_check_signal_handler)

    spotify_profile_monitor_uri(args.SPOTIFY_USER_URI_ID, error_notification, args.csv_file, csv_exists, playlists_to_skip)

    sys.stdout = stdout_bck
    sys.exit(0)

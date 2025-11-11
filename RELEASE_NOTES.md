# spotify_profile_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 2.9 (11 Nov 2025)

**Features and Improvements**:

- **NEW:** Added support for **Amazon Music**, **Deezer** and **Tidal** URLs in console and email outputs
- **NEW:** Added support for **AZLyrics**, **Tekstowo.pl**, **Musixmatch** and **Lyrics.com** lyrics services
- **NEW:** Added configuration options to enable/disable music service URLs in console and email outputs (see `ENABLE_APPLE_MUSIC_URL`, `ENABLE_YOUTUBE_MUSIC_URL`, `ENABLE_AMAZON_MUSIC_URL`, `ENABLE_DEEZER_URL` and `ENABLE_TIDAL_URL` config options)
- **NEW:** Added configuration options to enable/disable lyrics service URLs in console and email outputs (see `ENABLE_GENIUS_LYRICS_URL`, `ENABLE_AZLYRICS_URL`, `ENABLE_TEKSTOWO_URL`, `ENABLE_MUSIXMATCH_URL` and `ENABLE_LYRICS_COM_URL` config options)

# Changes in 2.8 (12 Oct 2025)

**Features and Improvements**:

- **IMPROVE:** Added support for loading TOTP secrets from local files via file:// URLs
- **IMPROVE:** Updated remote URL in SECRET_CIPHER_DICT_URL
- **IMPROVE:** Updated  [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_secret_grabber.py) to dump secrets in different formats. Choose what you need with the `--secret`,` --secretbytes` and `--secretdict` CLI flags, or go all out with the `--all` mode to write all secret formats to files like `secrets.json`, `secretBytes.json` and `secretDict.json`
- **IMPROVE:** Added multi-arch Docker image build and compose support for  [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_secret_grabber.py) - more info at [🐳 Secret Key Extraction via Docker](https://github.com/misiektoja/spotify_monitor#-secret-key-extraction-via-docker-recommended-easiest-way)
- **IMPROVE:** Moved CLEAN_OUTPUT assignment after loading configuration files. Checks that it is used only with -l or -x
- **IMPROVE:** Added info to console output when TOTP secrets are fetched from a remote URL or local file

**Bug fixes**:

- **BUGFIX:** Fixed -l errors if playlist provided is just the ID (fixes [#25](https://github.com/misiektoja/spotify_profile_monitor/issues/25))

# Changes in 2.7 (14 Jul 2025)

**Features and Improvements**:

- **IMPROVE:** Added automatic fetching of secrets used by web-player access token endpoint (`cookie` mode) while generating TOTP; it avoids manual updates since Spotify started rotating them every two days

**Bug fixes**:

- **BUGFIX:** Fixed bugs in retry logic and error handling in spotify_get_access_token_from_sp_dc()

# Changes in 2.6.1 (10 Jul 2025)

**Features and Improvements**:

- **IMPROVE:** Updated secret cipher bytes used by web-player access token endpoint (`cookie` mode) to v11 & v12
- **IMPROVE:** Moved secret cipher bytes for web-player endpoint to configuration section
- **IMPROVE:** Implemented auto-selection of highest cipher version when `TOTP_VER` is set to 0

**Bug fixes**:

- **BUGFIX:** Fixed truncation code to handle emojis with an actual width greater than one character (thanks [@tomballgithub](https://github.com/tomballgithub))

# Changes in 2.6 (07 Jul 2025)

**Features and Improvements**:

- **NEW:** Added support for manually specifying additional playlists to monitor via the `ADD_PLAYLISTS_TO_MONITOR` configuration option (thanks [@tomballgithub](https://github.com/tomballgithub))
- **NEW:** Added new config option (`TRUNCATE_CHARS`) and flag (`--truncate`) to limit screen line length; set to 999 to auto-detect terminal width (thanks [@tomballgithub](https://github.com/tomballgithub))
- **IMPROVE:** Updated secret cipher bytes used by web-player access token endpoint (`cookie` mode) to v9 & v10 (thanks [@Thereallo1026](https://github.com/Thereallo1026) for reverse engineering the current secrets)

**Bug fixes**:

- **BUGFIX:** Fixed missing asterisk on startup screen (thanks [@tomballgithub](https://github.com/tomballgithub))

# Changes in 2.5.3 (02 Jul 2025)

**Bug fixes**:

- **BUGFIX:** Fixed web-player access token retrieval via sp_dc cookie by updating secret cipher bytes (thanks [@WurdahMekanik](https://github.com/WurdahMekanik))
- **BUGFIX:** Fixed missing email alerts for failed token requests when using sp_dc cookie method

# Changes in 2.5.2 (18 Jun 2025)

**Features and Improvements**:

- **NEW:** Added two new methods (`oauth_app`, `oauth_user`) to obtain Spotify access tokens using official Spotify API (Client Credentials and Authorization Code OAuth flows - requires Spotipy). Check the [Spotify OAuth App](https://github.com/misiektoja/spotify_profile_monitor#spotify-oauth-app) and [Spotify OAuth User](https://github.com/misiektoja/spotify_profile_monitor#spotify-oauth-user) for more info.
- **IMPROVE:** HTTPAdapter now honors the Retry-After header on 429 responses for better Spotify API rate limit handling
- **IMPROVE:** Suppressed -z / --clienttoken-request-body-file from help output to reduce confusion (flag remains functional, but hidden)
- **IMPROVE:** Clarifications in inline comments explaining how to configure Spotify Desktop client method
- **IMPROVE:** Applied custom user agent to Spotipy-generated requests

# Changes in 2.4 (13 Jun 2025)

**Features and Improvements**:

- **NEW:** Added new `-o` / `--export-for-spotify-monitor` flag for simplified output when exporting playlists (-l) or liked songs (-x) to allow direct import into `spotify_monitor` (thanks [@tomballgithub](https://github.com/tomballgithub))
- **NEW:** Added new config option (`USER_AGENT`) and flag (`--user-agent`) to set Spotify user agent string
- **NEW:** Ensured all Spotify requests now include the same user agent, if not specified - it is randomly generated per session for specific type of token source
- **IMPROVE:** Improved detection when a Spotify user has been removed
- **IMPROVE:** Added more descriptive error messages and covered additional corner cases

# Changes in 2.3.2 (10 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Fixed web-player access token retrieval via sp_dc cookie

# Changes in 2.3.1 (10 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Ensured all Spotify requests include the custom User-Agent header
- **BUGFIX:** Fixed config file generation to work reliably on Windows systems ([#13](https://github.com/misiektoja/spotify_profile_monitor/issues/13))

# Changes in 2.3 (09 Jun 2025)

**Features and Improvements**:

- **NEW:** Added support for a new method to obtain the Spotify access token ([#11](https://github.com/misiektoja/spotify_profile_monitor/issues/11)). This method uses captured credentials from the Spotify desktop client and a Protobuf-based login flow. It is intended for advanced users who want an indefinitely valid token with the widest scope. Check the [Spotify Desktop Client](https://github.com/misiektoja/spotify_profile_monitor#spotify-desktop-client) for more info.
- **NEW:** Added detection for whether a Spotify playlist's artwork is auto-generated or user-uploaded, along with the date and time the artwork was last changed
- **NEW:** Added support for displaying playlist images in the terminal using `imgcat` on supported terminals

**Bug fixes**:

- **BUGFIX:** Improved handling of API glitches and count changes for playlists, followers and followings ([#12](https://github.com/misiektoja/spotify_profile_monitor/issues/12))

# Changes in 2.2.1 (27 May 2025)

**Bug fixes**:

- **BUGFIX:** Add safeguards against API glitches while processing track diffs, collaborators and likes

# Changes in 2.2 (21 May 2025)

**Features and Improvements**:

- **NEW:** The tool can now be installed via pip: `pip install spotify_profile_monitor`
- **NEW:** Added support for external config files, environment-based secrets and dotenv integration with auto-discovery
- **NEW:** Added support for exporting playlists and liked songs to CSV files
- **NEW:** Display access token owner information for better transparency
- **IMPROVE:** Improved filtering of unavailable tracks (e.g. due to copyright restrictions)
- **IMPROVE:** Enhanced startup summary to show loaded config, dotenv and ignore-playlists file paths
- **IMPROVE:** Auto detect and display availability of `imgcat` binary for profile picture preview
- **IMPROVE:** Simplified and renamed command-line arguments for improved usability
- **NEW:** Implemented SIGHUP handler for dynamic reload of secrets from dotenv files
- **NEW:** Added configuration option to control clearing the terminal screen at startup
- **IMPROVE:** Changed connectivity check to use Spotify API endpoint for reliability
- **IMPROVE:** Added check for missing pip dependencies with install guidance
- **IMPROVE:** Allow disabling liveness check by setting interval to 0 (default changed to 12h)
- **IMPROVE:** Improved handling of log file creation
- **IMPROVE:** Refactored CSV file initialization and processing
- **NEW:** Added support for `~` path expansion across all file paths
- **IMPROVE:** Refactored code structure to support packaging for PyPI
- **IMPROVE:** Enforced configuration option precedence: code defaults < config file < env vars < CLI flags
- **IMPROVE:** Added warning about unsupported Python version
- **IMPROVE:** Removed short option for `--send-test-email` to avoid ambiguity

**Bug fixes**:

- **BUGFIX:** Fixed edge cases while processing playlist entries to avoid NoneType errors ([#10](https://github.com/misiektoja/spotify_profile_monitor/issues/10))
- **BUGFIX:** Improved playlist diff logic to ignore Spotify-owned playlists based on owner ID ([#9](https://github.com/misiektoja/spotify_profile_monitor/issues/9))
- **BUGFIX:** Fixed false positives in playlist diff by ignoring collaborator display names
- **BUGFIX:** Fixed imgcat command under Windows (use `echo. &` instead of `echo ;`)

# Changes in 2.1 (07 Apr 2025)

**Features and Improvements**:

- **IMPROVE:** Display URL of collaborator user instead of just ID (thanks [@filipw-ctrl](https://github.com/filipw-ctrl))
- **IMPROVE:** Added display of the number of tracks contributed by each collaborator with percentage breakdown to better visualize individual contributions
- **IMPROVE:** Implemented caching for playlist info to reduce redundant API calls
- **IMPROVE:** Improved detection and handling of completely removed or private playlists
- **IMPROVE:** Enhanced error messages for better debugging and clarity
- **IMPROVE:** Updated horizontal line for improved output aesthetics

**Bug fixes**:

- **BUGFIX:** Refactored playlist processing to handle erratic Spotify API behavior (e.g. sudden playlist removal/addition) (fixes [#7](https://github.com/misiektoja/spotify_profile_monitor/issues/7))
- **BUGFIX:** Fixed issue where Spotify username changes caused incorrect detection of playlist changes on the user profile
- **BUGFIX:** Fixed issue where manually defined LOCAL_TIMEZONE wasn't applied during timestamp conversion

# Changes in 2.0.1 (26 Mar 2025)

**Bug fixes**:

- **BUGFIX:** Added retry-enabled HTTPAdapter to global SESSION to address 'Remote end closed connection without response' errors

# Changes in 2.0 (25 Mar 2025)

**Features and Improvements**:

- **NEW:** Added playlist filtering (**-t** / **--playlists_to_skip**) and ignore Spotify-owned playlists by default (related to [#3](https://github.com/misiektoja/spotify_profile_monitor/issues/3)):
	- From now on, all Spotify-owned playlists are skipped from processing (unless `IGNORE_SPOTIFY_PLAYLISTS` is set to False)
	- On top of that, there is a new functionality which allows to indicate a file with additional playlists to be blacklisted
	- More details in [Playlist blacklisting](README.md#playlist-blacklisting)
- **IMPROVE:** Replaced repeated requests.get calls with a shared SESSION (pre-configured with Client-Id and User-Agent headers) to reuse HTTP connections and improve performance (by around 25% for huge playlists)
- **IMPROVE:** Improve mapping of user URI IDs to usernames to handle additional edge cases

**Bug fixes**:

- **BUGFIX:** Corrects spotify_extract_id_or_name() to handle NoneType objects (fixes [#4](https://github.com/misiektoja/spotify_profile_monitor/issues/4))
- **BUGFIX:** Fixes mapping of user URI IDs to usernames for Spotify-generated playlists (fixes [#2](https://github.com/misiektoja/spotify_profile_monitor/issues/2))
- **BUGFIX:** Fixes occasional None return from get_random_user_agent(), avoiding downstream NoneType error

# Changes in 1.9 (20 Mar 2025)

**Features and Improvements**:

- **NEW:** Added support for TOTP parameters in Spotify Web Player token endpoint, the tool now requires the pyotp pip module (fixes [#1](https://github.com/misiektoja/spotify_profile_monitor/issues/1))
- **NEW:** New feature displaying the recently updated playlist after the list of all user's playlists
- **NEW:** Caching mechanism to avoid unnecessary token refreshes
- **NEW:** Added the possibility to disable SSL certificate verification (VERIFY_SSL global variable)
- **IMPROVE:** Saving the added track timestamp instead of the time of checking to the CSV file
- **IMPROVE:** Email notification flags are now automatically disabled if the SMTP configuration is invalid
- **IMPROVE:** Different recently played artist limits are now used when using the -a & -i parameters (RECENTLY_PLAYED_ARTISTS_LIMIT and RECENTLY_PLAYED_ARTISTS_LIMIT_INFO global variables)
- **IMPROVE:** Possibility to disable displaying the list of playlists (-q) when using the -i parameter
- **IMPROVE:** Better exception handling in network-related functions
- **IMPROVE:** Better overall error handling
- **IMPROVE:** Code cleanup & linting fixes

**Bug fixes**:

- **BUGFIX:** Fixed f-string syntax errors introduced in v1.7 (thanks [@tomballgithub](https://github.com/tomballgithub) for reporting and code fixes!)

# Changes in 1.8 (03 Feb 2025)

**Features and Improvements**:

- **NEW:** Added new parameter (**-k** / **--get_all_playlists**) which retrieves all public playlists visible in the user's profile, even if they are not owned by them; it is helpful in the case of playlists created by one user added to another user's profile; by default, only public playlists owned by the user are processed
- **NEW:** Added info about the playlist owner to the output with the list of playlists

# Changes in 1.7 (28 Jan 2025)

**Features and Improvements**:

- **NEW:** The tool now provides information about **collaborators** on playlists (if applicable) and adds details about collaborators when new tracks are added. This applies to both monitoring mode (including email notifications) and listing mode (**-i**, **-l**).
Keep in mind: the tool displays the actual number of collaborators. That means it only counts users who have actually contributed to the playlist. If someone's name is visible in Spotify client, but they haven't added a single track, they don't make the cut (sorry, but the point is Spotify doesn't have an official API for that, so the tool gets its hands dirty by analyzing all the tracks in the playlist).

**Bug fixes**:

- **BUGFIX:** Hopefully fixed a rare bug where the tool would report a changed profile picture even though the timestamp remained the same

# Changes in 1.6 (03 Nov 2024)

**Features and Improvements**:

- **NEW:** Detection of Spotify username changes
- **NEW:** Support for YouTube Music search URLs
- **IMPROVE:** Displaying last update date of user's profile pic when using -i parameter
- **IMPROVE:** Added info to email notifications for playlists with errors

**Bug fixes**:

- **BUGFIX:** Fixed bug with wrong number of user owned public playlists if there are none

# Changes in 1.5 (11 Sep 2024)

**Features and Improvements**:

- **NEW:** Possibility to disable detection of changes in user's public playlists (new **-q** / **--do_not_monitor_playlists** parameter)
- **NEW:** Possibility to disable email notifications for changed followers/followings (new **-g** / **--disable_followers_followings_notification** parameter) 
- **IMPROVE:** Recently played artists limit increased from 15 to 50 + info about the limit in the output
- **IMPROVE:** Indentation + linting fixes

**Bug fixes**:

- **BUGFIX:** Fixed issue with missed playlists changes notifications in case of intermittent Spotify API issues
- **BUGFIX:** Fixed bug with wrong CSV file event entry name
- **BUGFIX:** Fixed issue with Spotify API sometimes returning wrong info that all user's playlists have been removed

# Changes in 1.4 (15 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new parameter (**-z** / **--send_test_email_notification**) which allows to send test email notification to verify SMTP settings defined in the script
- **IMPROVE:** Better handling of newly created / empty playlists
- **IMPROVE:** Better handling of situations when user removes all public playlists
- **IMPROVE:** Showing how much time passed since last playlist update in case all tracks are removed
- **IMPROVE:** Possibility to define email sending timeout (default set to 15 secs)

**Bug fixes**:

- **BUGFIX:** Fixed an issue of the tool crashing when user had no playlists and created a new one
- **BUGFIX:** Fixed "SyntaxError: f-string: unmatched (" issue in older Python versions
- **BUGFIX:** Fixed "SyntaxError: f-string expression part cannot include a backslash" issue in older Python versions

# Changes in 1.3 (03 Jun 2024)

**Features and Improvements**:

- **NEW:** Support for honoring last-modified timestamp for saved profile pics (it turned out it reflects timestamp when the picture has been actually added by the user); if you used previous version of the tool, remove the profile pic for the user and let the new version of the tool to re-download it with original modification time which will reflect the time when user actually changed the profile picture
- **IMPROVE:** File suffix (**-y**) honored for JSON and profile picture JPEG file names as well
- **IMPROVE:** get_short_date_from_ts() rewritten to display year if show_year == True and current year is different, also can omit displaying hour and minutes if show_hours == False; new version of function is used when number of tracks changes for the playlist (which might happen after a year, can't it ? 😉)
- **IMPROVE:** Support for float type of timestamps added in date/time related functions

**Bug fixes**:

- **BUGFIX:** Fix to handle situations when user removes track from playlist, but it is not the last track
- **BUGFIX:** Escaping of exception error string fixed

# Changes in 1.2 (24 May 2024)

**Features and Improvements**:

- **NEW:** Feature allowing for **detection of changed profile pictures**; since Spotify user's profile picture URL seems to change from time to time, the tool detects changed profile picture by doing binary comparison of saved jpeg files; initially it saves the profile pic to *spotify_{user_uri_id}_profile_pic.jpeg* file after the tool is started (in monitoring mode); then during every check the new picture is fetched and the tool does binary comparison if it has changed or not; in case of changes the old profile picture is moved to *spotify_{user_uri_id}_profile_pic_old.jpeg* file and the new one is saved to *spotify_{user_uri_id}_profile_pic.jpeg* and also to file named *spotify_{user_uri_id}_profile_pic_YYmmdd_HHMM.jpeg* (so we can have history of all profile pictures); in order to control the feature there is a new **DETECT_CHANGED_PROFILE_PIC** variable set to True by default; the feature can be disabled by setting it to *False* or by enabling **-j** / **--do_not_detect_changed_profile_pic** parameter
- **NEW:** Feature attaching changed profile pics directly in email notifications (when **-p** parameter is used)
- **NEW:** Feature allowing to display the profile picture right in your terminal (if you have *imgcat* installed); put path to your *imgcat* binary in **IMGCAT_PATH** variable (or leave it empty to disable this functionality)
- **IMPROVE:** Improved detection of tracks changed for the playlist; previously if the number of added and removed tracks was the same it went unnoticed by the tool; currently the tool also compares last update timestamp of the playlist to cover such use cases
- **IMPROVE:** The tool now shows the time which passed since the previous time new track has been added to the playlist (console + email notifications)
- **NEW:** Possibility to define output log file name suffix (**-y** / **--log_file_suffix**)
- **IMPROVE:** Information about log file name visible in the start screen
- **IMPROVE:** Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime
- **IMPROVE:** Detection of wrong Spotify user URI ID + unneeded while loop removed

**Bug fixes**:

- **BUGFIX:** Fixed stupid bug with the tool crashing when user had no public playlists at all
- **BUGFIX:** Fixed issues with sporadic broken links in HTML emails (vars with special characters are now escaped properly)

# Changes in 1.1 (19 May 2024)

**Features and Improvements**:

- **IMPROVE:** Improvements for running the code in Python under Windows
- **NEW:** Automatic detection of local timezone if you set LOCAL_TIMEZONE variable to 'Auto' (it is default now); requires tzlocal pip module
- **IMPROVE:** Information about time zone is displayed in the start screen now
- **IMPROVE:** Better checking for wrong command line arguments
- **IMPROVE:** pep8 style convention corrections

**Bug fixes**:

- **BUGFIX:** Improved exception handling while processing JSON files

# Changes in 1.0 (11 May 2024)

**Features and Improvements**:

- **NEW:** Feature to search for user names (**-s**) to get user URI ID
- **NEW:** Possibility to define SP_DC_COOKIE via command line argument (**-u** / **--spotify_dc_cookie**)
- **IMPROVE:** Fetching only public playlists owned by the user (ignoring playlists of other users added to user's profile)
- **IMPROVE:** Showing delta info (+N or -N) when informing about changed number of followers/followings/playlists/tracks
- **IMPROVE:** Information about user's profile URL put in different parts of the code
- **IMPROVE:** Possibility to configure limits for list of playlists (**PLAYLISTS_LIMIT**) and recently played artists (**RECENTLY_PLAYED_ARTISTS_LIMIT**) fetched from user's profile
- **IMPROVE:** Additional search/replace strings to sanitize tracks for Genius Lyrics URLs
- **IMPROVE:** Email sending function send_email() has been rewritten to detect invalid SMTP settings
- **IMPROVE:** Strings have been converted to f-strings for better code visibility
- **IMPROVE:** Info about CSV file name in the start screen
- **IMPROVE:** Small refactoring of functions processing playlists and its tracks to improve performance (it is still quite slow in case of huge number of playlists/tracks)
- **IMPROVE:** In case of getting an exception in main loop we will send the error email notification only once (until the issue is resolved)

**Bug fixes**:

- **BUGFIX:** Handling situations when user changes the playlist's visibility to private (previously the tool crashed)
- **BUGFIX:** Handling situations when JSON files storing info about followers, followings or playlists get corrupted (previously the tool crashed)

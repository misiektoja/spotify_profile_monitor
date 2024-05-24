# spotify_profile_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.2 (24 May 2024)

**Features and Improvements**:

- New feature allowing for **detection of changed profile pictures**; since Spotify user's profile picture URL seems to change from time to time, the tool detects changed profile picture by doing binary comparison of saved jpeg files; initially it saves the profile pic to *spotify_{user_uri_id}_profile_pic.jpeg* file after the tool is started (in monitoring mode); then during every check the new picture is fetched and the tool does binary comparison if it has changed or not; in case of changes the old profile picture is moved to *spotify_{user_uri_id}_profile_pic_old.jpeg* file and the new one is saved to *spotify_{user_uri_id}_profile_pic.jpeg* and also to file named *spotify_{user_uri_id}_profile_pic_YYmmdd_HHMM.jpeg* (so we can have history of all profile pictures); in order to control the feature there is a new **DETECT_CHANGED_PROFILE_PIC** variable set to True by default; the feature can be disabled by setting it to *False* or by enabling **-j** / **--do_not_detect_changed_profile_pic** parameter
- New feature attaching changed profile pics directly in email notifications (when **-p** parameter is used)
- New feature allowing to display the profile picture right in your terminal (if you have *imgcat* installed); put path to your *imgcat* binary in **IMGCAT_PATH** variable (or leave it empty to disable this functionality)
- Improved detection of tracks changed for the playlist; previously if the number of added and removed tracks was the same it went unnoticed by the tool; currently the tool also compares last update timestamp of the playlist to cover such use cases
- The tool now shows the time which passed since the previous time new track has been added to the playlist (console + email notifications)
- Possibility to define output log file name suffix (**-y** / **--log_file_suffix**)
- Information about log file name visible in the start screen
- Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime
- Detection of wrong Spotify user URI ID + uneeded while loop removed

**Bugfixes**:

- Fixed stupid bug with the tool crashing when user had no public playlists at all
- Fixed issues with sporadic broken links in HTML emails (vars with special characters are now escaped properly)

# Changes in 1.1 (19 May 2024)

**Features and Improvements**:

- Improvements for running the code in Python under Windows
- Automatic detection of local timezone if you set LOCAL_TIMEZONE variable to 'Auto' (it is default now); requires tzlocal pip module
- Information about time zone is displayed in the start screen now
- Better checking for wrong command line arguments
- pep8 style convention corrections

**Bugfixes**:

- Improved exception handling while processing JSON files

# Changes in 1.0 (11 May 2024)

**Features and Improvements**:

- Feature to search for user names (**-s**) to get user URI ID
- Possbility to define SP_DC_COOKIE via command line argument (**-u** / **--spotify_dc_cookie**)
- Fetching only public playlists owned by the user (igoring playlists of other users added to user's profile)
- Showing delta info (+N or -N) when informing about changed number of followers/followings/playlists/tracks
- Information about user's profile URL put in different parts of the code
- Possibility to configure limits for list of playlists (**PLAYLISTS_LIMIT**) and recently played artists (**RECENTLY_PLAYED_ARTISTS_LIMIT**) fetched from user's profile
- Additional search/replace strings to sanitize tracks for Genius Lyrics URLs
- Email sending function send_email() has been rewritten to detect invalid SMTP settings
- Strings have been converted to f-strings for better code visibility
- Info about CSV file name in the start screen
- Small refactoring of functions processing playlists and its tracks to improve performance (it is still quite slow in case of huge number of playlists/tracks)
- In case of getting an exception in main loop we will send the error email notification only once (until the issue is resolved)

**Bugfixes**:

- Handling situations when user changes the playlist's visibility to private (previously the tool crashed)
- Handling situations when JSON files storing info about followers, followings or playlists get corrupted (previously the tool crashed)

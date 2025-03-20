# spotify_profile_monitor release notes

This is a high-level summary of the most important changes. 

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

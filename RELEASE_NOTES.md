# spotify_profile_monitor release notes

This is a high-level summary of the most important changes. 

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

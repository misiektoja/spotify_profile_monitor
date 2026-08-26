# Configuration

Examples on this page use the PyPI command `spotify_profile_monitor`. Manual script users should keep the shown options and use the matching prefix under [Command Format by Installation Method](usage.md#command-format).

<a id="configuration-file"></a>
## Configuration File

Most settings can be configured via command-line arguments.

If you want to have it stored persistently, generate a default config template and save it to a file named `spotify_profile_monitor.conf`:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
spotify_profile_monitor --generate-config > spotify_profile_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
spotify_profile_monitor --generate-config spotify_profile_monitor.conf
```

> **IMPORTANT**: On **Windows PowerShell**, using redirection (`>`) can cause the file to be encoded in UTF-16, which will lead to "null bytes" errors when running the tool. It is highly recommended to provide the filename directly as an argument to `--generate-config` to ensure UTF-8 encoding.

Edit the `spotify_profile_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

The configuration file is read as data, not executed. It may contain only `NAME = value` assignments where the name is one of the settings in the generated template and the value is a plain literal: a number, a quoted string, `True`, `False`, `None`, or a list, tuple or dict of those. Expressions such as `30 * 60`, imports, function calls and references to other settings are rejected with the offending line number. Write the computed value directly instead, for example `SPOTIFY_CHECK_INTERVAL = 1800`. Because the tool also picks up a config file from the current directory, this ensures a `spotify_profile_monitor.conf` you did not write cannot run code when you start the tool.

When `--generate-config FILENAME` targets an existing file, an interactive run asks for confirmation. A noninteractive run refuses replacement unless `--force` is present. An approved replacement validates the generated content, writes it atomically and saves a timestamped backup beside the original. The setup wizard provides the same confirmation and backup protection.

Despite its legacy name, `TARGET_USER_URI_ID` accepts a complete Spotify profile URL, a `spotify:user:` URI or a user ID. Set it to run without a positional target. A positional target in any accepted form overrides the configured value.

<a id="spotify-access-token-source"></a>
## Spotify access token source

The tool supports four methods for obtaining a Spotify access token.

Public playlist details use an automatic backend. If working OAuth app credentials are configured, the tool first preserves the legacy Web API behavior. If Spotify returns a restricted response or if no app credentials are configured, the tool retrieves public playlist metadata and contents through the Spotify web-player service. The web backend discovers the current persisted-query hash automatically and does not require a Spotify app or Premium subscription.

> **OAuth app guidance:** Spotify restricted new Development Mode apps created on or after February 11, 2026. Some older apps have been observed to retain the legacy endpoint access used by this tool, but creation date alone does not guarantee compatibility. Configure `oauth_app` only if you already have an app which you have verified still works. If it returns HTTP 403 then remove the OAuth app credentials and let the automatic web backend handle public playlists. See Spotify's [official migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide).

The token source method can be configured via the `TOKEN_SOURCE` configuration option or the `--token-source` flag.

**Recommended: `cookie`**

Uses the `sp_dc` cookie to retrieve a token from the Spotify web endpoint. This method is easy to set up and supports all features except fetching the list of liked tracks for the account that owns the access token (due to recent Spotify token's scope restrictions).

Since version 3.1, due to Spotify restrictions introduced on December 22, 2025, it no longer shows other users' playlists added to a user's profile unless the user is a collaborator on a playlist owned by another user.

**Alternative: `client`**

Uses captured credentials from the Spotify desktop client and a Protobuf-based login flow. It's more complex to set up, but supports all features. This method is intended for advanced users who want a long-lasting token with the broadest possible access.

Since version 3.1, due to Spotify restrictions introduced on December 22, 2025, it no longer shows other users' playlists added to a user's profile unless the user is a collaborator on a playlist owned by another user.

**Optional legacy: `oauth_app`**

Relies on the official Spotify Web API Client Credentials flow. This mode is retained for existing apps which still have verified access to the legacy endpoints. It is not required for `cookie` or `client` mode and is not recommended for a new setup.

As a standalone token source it can monitor other users only when the existing app still retains the removed `GET /users/{id}` access. New Development Mode apps cannot use this workflow. The following features are also **not** supported:
- viewing the list of followers/followings
- accessing the followings count (only the followers count is tracked; **post-Feb 2026**: followers count also not available)
- getting the list of recently played artists
- showing other users' playlists added to user profile (unless the user is a collaborator on a playlist owned by other user)
- fetching the list of liked tracks for the account that owns the access token
- searching for Spotify users by name

Use `cookie` or `client` for normal monitoring. Add `oauth_app` credentials only as an optional legacy Web API path after verifying that the existing app still works.

**Personal: `oauth_user`**

Dedicated to tracking the authenticated user's own account via the official Spotify Web API (Authorization Code OAuth flow). I personally use this mode to monitor changes to my own account - such as new or lost followers/followings, likes on my playlists or when a collaborator adds a new song. You can also use this mode to track other users.

This method is easy to set up and safe to use, but has several limitations.

The following features are **not** supported when monitoring **your own account**:
- viewing the list of followers
- viewing the complete list of followings (only followed artists are available; followed users are not included)
- searching for Spotify users by name
- **viewing follower count (post-Feb 2026)**

**Note**: If you use `oauth_user` to monitor your own account, the tool will list all your playlists, including private ones.

The following features are **not** supported when monitoring **another user** in this mode:
- viewing the list of followers/followings
- accessing the followings count (only the followers count is tracked; **post-Feb 2026**: followers count also not available)
- getting the list of recently played artists
- showing other users' playlists added to user profile (unless the user is a collaborator on a playlist owned by other user)
- searching for Spotify users by name

> **Current limitation:** Spotify removed the `GET /users/{id}` endpoint on February 11, 2026. `oauth_user` can no longer monitor other users. Self-monitoring still works. For monitoring others, use the `cookie` or `client` method.

> **Premium required:** Since March 9, 2026, `oauth_user` requires the authorized user to have a Spotify Premium account.

If no method is specified, the tool defaults to the `cookie` method.

**Important**: It is strongly recommended to use a separate Spotify account with this tool if you obtain access tokens via the `cookie` or `client` methods. These methods interact with internal undocumented endpoints for features such as followers, followings and recently played artists. The automatic public playlist backend also uses an undocumented Spotify web-player interface. Spotify may change or restrict these interfaces in the future.

<a id="spotify-sp_dc-cookie"></a>
### Spotify sp_dc Cookie

This is the default method used to obtain a Spotify access token.

<a id="manual-cookie-extraction"></a>
#### Manual cookie extraction

Treat `sp_dc` like a password. Anyone who has it may be able to use your Spotify login session.

Follow these steps:

1. Open [Spotify Web Player](https://open.spotify.com/) and sign in to the Spotify account you want to use for monitoring.
2. Open your browser's developer tools. Press `F12` or `Ctrl+Shift+I` on Windows and Linux. Press `Command+Option+I` on macOS.
3. In Firefox, open **Storage** > **Cookies** > `https://open.spotify.com`.
4. In Chrome, Brave or Chromium, open **Application** > **Storage** > **Cookies** > `https://open.spotify.com`.
5. Find the cookie named `sp_dc` and copy only its **Value**. Do not copy the cookie name or the complete table row.
6. Run the private entry command then paste the copied value at its hidden prompt:

```sh
spotify_profile_monitor --set-sp-dc
```

The command validates the cookie before atomically saving it as `SP_DC_COOKIE` in `.env`. To use another dotenv path, add `--env-file PATH`.

As an alternative, [Cookie-Editor by cgagnier](https://cookie-editor.com/) can display the `sp_dc` value. Only use a browser extension that you trust because browser extensions can access sensitive login cookies.

You can provide `SP_DC_COOKIE` in these ways:

* Run `spotify_profile_monitor --set-sp-dc` to enter it privately, validate it with Spotify then save it to a [dotenv file](#storing-secrets). This is recommended.
* Add `SP_DC_COOKIE="your_sp_dc_cookie_value"` directly to a dotenv file for persistent use.
* Set it as an [environment variable](#storing-secrets), for example `export SP_DC_COOKIE="your_sp_dc_cookie_value"`.
* Pass it for one run with `-u` or `--spotify-dc-cookie`. This is not recommended because the value may appear in shell history or process listings.
* Store it in the configuration file or source code as a last resort. This is not recommended because it is easier to expose or commit accidentally.

If your `sp_dc` cookie expires, the tool reports the error in the console and sends it through each enabled notification channel: email, Discord or ntfy. In that case, you'll need to grab the new `sp_dc` cookie value.

If you store the `SP_DC_COOKIE` in a dotenv file you can update its value and send a `SIGHUP` signal to reload the file with the new `sp_dc` cookie without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

> **NOTE:** Spotify still requires TOTP parameters for web-player token requests. The web player continues to select v61 which was first published in January 2026. Version 3.5 embeds v61 directly and no longer downloads a third-party secret dictionary. The version and cipher bytes are exposed as the `TOTP_VERSION` and `TOTP_SECRET_CIPHER_BYTES` config options, so if Spotify resumes rotation you can patch them from the config file without a code release. Use [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/main/debug/spotify_monitor_secret_grabber.py) to extract the current bundle values then update those two options.

<a id="spotify-desktop-client"></a>
### Spotify Desktop Client

This is the alternative method used to obtain a Spotify access token which simulates a login from the real Spotify desktop app using credentials intercepted from a real session.

- Run an intercepting proxy of your choice (like [Proxyman](https://proxyman.com) - the trial version is sufficient)

- Enable SSL traffic decryption for `spotify.com` domain
   - in Proxyman: click **Tools → SSL Proxying List → + button → Add Domain → paste `*.spotify.com` → Add**

- Launch the Spotify desktop client, then switch to your intercepting proxy (like Proxyman) and look for POST requests to `https://login5.spotify.com/v3/login`

- If you don't see this request, try following steps (stop once it works):
   - restart the Spotify desktop client
   - log out from the Spotify desktop client and log back in
   - point Spotify at the intercepting proxy directly in its settings, i.e. in **Spotify → Settings → Proxy Settings**, set:
      - **proxy type**: `HTTP`
      - **host**: `127.0.0.1` (IP/FQDN of your proxy, for Proxyman use the IP you see at the top bar)
      - **port**: `9090` (port of your proxy, for Proxyman use the port you see at the top bar)
      - restart the app; since QUIC (HTTP/3) requires raw UDP and can't tunnel over HTTP CONNECT, Spotify will downgrade to TCP-only HTTP/2 or 1.1, which intercepting proxy can decrypt
   -  block Spotify's UDP port 443 at the OS level with a firewall of your choice - this prevents QUIC (HTTP/3), forcing TLS over TCP and letting intercepting proxy perform MITM
   - try an older version of the Spotify desktop client

- Export the login request body (a binary Protobuf payload) to a file (e.g. ***login-request-body-file***)
   - In Proxyman: **right click the request → Export → Request Body → Save File**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_profile_monitor/refs/heads/main/assets/proxyman_export_protobuf.png" alt="proxyman_export_protobuf" width="80%"/>
</p>

- Run the tool with `--token-source client -w <path-to-login-request-body-file>`:

```sh
spotify_profile_monitor --token-source client -w <path-to-login-request-body-file> <spotify_target>
```

If successful, the tool will automatically extract the necessary fields and begin monitoring.

When `-w` is used on its own to inspect a Protobuf file, the extracted refresh token is masked. Add `--verbose` to print the full value when you need to copy it into your configuration.

Instead of using the `-w` flag each time, you can persist the Protobuf login request file path by setting the `LOGIN_REQUEST_BODY_FILE` configuration option.

The same applies to `--token-source client` flag - you can persist it via `TOKEN_SOURCE` configuration option set to `client`.

The tool will automatically refresh both the access token and client token using the intercepted refresh token.

If your refresh token expires, the tool reports the error in the console and sends it through each enabled notification channel: email, Discord or ntfy. In that case, you'll need to re-export the login request body.

If you re-export the login request body to the same file name, you can send a `SIGHUP` signal to reload the file with the new refresh token without restarting the tool. More info in [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

Advanced options are available for further customization - refer to the configuration file comments. However, the default settings are suitable for most users and modifying other values is generally NOT recommended.

<a id="spotify-oauth-app"></a>
### Spotify OAuth App

OAuth app credentials are not required for public playlist retrieval. This section is retained only for users who already have a verified legacy-compatible app or want to test standalone Client Credentials behavior.

Do not create a new Spotify app solely for `spotify_profile_monitor`. Apps created under the current Development Mode restrictions cannot provide the removed public user endpoints needed for standalone monitoring of other users.

If you already have a working existing app:

- Log in to [Spotify Developer dashboard](https://developer.spotify.com/dashboard)

- Open the existing app which still has verified legacy endpoint access

- Copy the **Client ID** and **Client Secret**

- Provide the `SP_APP_CLIENT_ID` and `SP_APP_CLIENT_SECRET` secrets using one of the following methods:
   - Pass it at runtime with `-r` / `--oauth-app-creds` (use `SP_APP_CLIENT_ID:SP_APP_CLIENT_SECRET` format - note the colon separator)
   - Set it as an [environment variable](#storing-secrets) (e.g. `export SP_APP_CLIENT_ID=...; export SP_APP_CLIENT_SECRET=...`)
   - Add it to [.env file](#storing-secrets) (`SP_APP_CLIENT_ID=...` and `SP_APP_CLIENT_SECRET=...`) for persistent use
   - Fallback: hard-code it in the code or config file

Optional legacy example:

```sh
spotify_profile_monitor --token-source oauth_app -r "your_spotify_app_client_id:your_spotify_app_client_secret" <spotify_target>
```

The tool automatically refreshes the OAuth app access token, so it remains valid indefinitely. Tokens are cached in the file specified by `SP_APP_TOKENS_FILE` configuration option (default: `.spotify-profile-monitor-oauth-app.json`).

If you store the `SP_APP_CLIENT_ID` and `SP_APP_CLIENT_SECRET` in a dotenv file you can update their values and send a `SIGHUP` signal to reload the file with the new secret values without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

You can use this method as a standalone token source only when the existing app still retains all endpoints required for your selected operation. If it returns HTTP 403 use `cookie` or `client` without OAuth app credentials.

<a id="spotify-oauth-user"></a>
### Spotify OAuth User

This method uses an official Spotify Web API (Authorization Code OAuth flow).

- Log in to Spotify Developer dashboard: https://developer.spotify.com/dashboard

- Create a new app

- For **Redirect URL**, use: http://127.0.0.1:1234
   - The URL must match exactly as shown, including not having a / at the end
   - When copying the link via right-click, some browsers may add an extra / to the URL

- Select **Web API** as the intended API

- Copy the **Client ID** and **Client Secret** (the secret is not required if you're using `PKCE` mode)

- Provide the `SP_USER_CLIENT_ID` and `SP_USER_CLIENT_SECRET` secrets using one of the following methods:
   - Pass it at runtime with `-n` / `--oauth-user-creds`
      - Use `SP_USER_CLIENT_ID`:`SP_USER_CLIENT_SECRET` format - note the colon separator
   - Set it as an [environment variable](#storing-secrets) (e.g. `export SP_USER_CLIENT_ID=...; export SP_USER_CLIENT_SECRET=...`)
   - Add it to [.env file](#storing-secrets) (`SP_USER_CLIENT_ID=...` and `SP_USER_CLIENT_SECRET=...`) for persistent use
   - Fallback: hard-code it in the code or config file

To use `PKCE` mode, set SP_USER_CLIENT_SECRET to an empty string ("").

You can use the same client ID and secret values as those used for the [Spotify OAuth App](#spotify-oauth-app).

Example:

```sh
spotify_profile_monitor --token-source oauth_user -n "your_spotify_user_client_id:your_spotify_user_client_secret" <spotify_target>
```

The tool takes care of refreshing the access token so it should remain valid indefinitely.

If you store the `SP_USER_CLIENT_ID` and `SP_USER_CLIENT_SECRET` in a dotenv file you can update their values and send a `SIGHUP` signal to reload the file with the new secret values without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

<a id="how-to-find-a-friends-spotify-profile-url"></a>
## How to Find a Friend's Spotify Profile URL

The easiest way is via the Spotify desktop or mobile client:
- go to your friend's profile
- click the **three dots** (•••) or press the **Share** button
- copy the link to the profile

You'll get a URL like `https://open.spotify.com/user/USER_ID?si=tracking_id`.

Pass that profile URL directly to the tool. You do not need to extract the ID. Spotify user URIs such as `spotify:user:USER_ID` and standalone user IDs are also accepted.

Alternatively you can use the built-in username search (`-s`) to find a Spotify user ID:

```sh
spotify_profile_monitor -s "user name"
```

It lists matching users with their Spotify user IDs and profile URLs. Any listed profile URL or ID can then be used as the monitoring target.

Before using this feature make sure you followed the instructions [here](#spotify-sha256-optional).

<a id="spotify-sha256-optional"></a>
## Spotify sha256 (optional)

This step is optional and required only for the username search feature (`-s`). To use it, intercept your Spotify client's network traffic and extract the required `sha256Hash` value.

- Run an intercepting proxy of your choice (like [Proxyman](https://proxyman.com)).

- Launch the Spotify desktop client and search for some user

- Look for requests with the `searchUsers` or `searchDesktop` operation name

- Display the details of one of these requests and copy the **sha256Hash** parameter value (string marked as `XXXXXXXXXX` below)

Example request:
`https://api-partner.spotify.com/pathfinder/v1/query?operationName=searchUsers&variables={"searchTerm":"spotify_user_uri_id","offset":0,"limit":5,"numberOfTopResults":5,"includeAudiobooks":false}&extensions={"persistedQuery":{"version":1,"sha256Hash":"XXXXXXXXXX"}}`



 - Provide the `SP_SHA256` secret using one of the following methods:
   - Set it as an [environment variable](#storing-secrets) (e.g. `export SP_SHA256=...`)
   - Add it to [.env file](#storing-secrets) (`SP_SHA256=...`) for persistent use
   - Fallback: hard-code it in the code or config file

<a id="time-zone"></a>
## Time Zone

By default, time zone is auto-detected using `tzlocal`. You can set it manually in `spotify_profile_monitor.conf`:

```ini
LOCAL_TIMEZONE='Europe/Warsaw'
```

You can get the list of all time zones supported by pytz like this:

```sh
python3 -c "import pytz; print('\n'.join(pytz.all_timezones))"
```

<a id="smtp-settings"></a>
## SMTP Settings

If you want to use email notifications functionality, configure SMTP settings in the `spotify_profile_monitor.conf` file.

Verify your SMTP settings by using `--send-test-email` flag (the tool will try to send a test email notification):

```sh
spotify_profile_monitor --send-test-email
```

<a id="webhook-settings"></a>
## Webhook Settings

Spotify Profile Monitor can send profile, follower and error alerts through Discord or the native [ntfy publish API](https://docs.ntfy.sh/publish/). Webhook delivery works with or without email.

`WEBHOOK_PROVIDER` selects the request format. It defaults to `"discord"`. Standard Discord and public `ntfy.sh` URLs automatically select the matching format if this configured value is stale. Self-hosted ntfy and compatible endpoints still use the configured provider. Use `--webhook-provider discord` or `--webhook-provider ntfy` for an explicit one-run override.

### Discord

To create a private Discord webhook URL:

1. Open the Discord server and choose the channel that should receive alerts.
2. Click **Edit Channel** then open **Integrations** > **Webhooks**.
3. Click **New Webhook** then choose a name and click **Copy Webhook URL**.
4. Save the URL through the hidden prompt:

```sh
spotify_profile_monitor --set-webhook-url
```

The command saves only `WEBHOOK_URL` in `.env` without putting the private value in shell history. Treat this URL like a password because anyone who has it can post through it.

Keep the default request format in `spotify_profile_monitor.conf`:

```ini
WEBHOOK_PROVIDER = "discord"
```

### ntfy

Choose a hard-to-guess topic. Public `ntfy.sh` URLs are recognized automatically. Set the provider to `"ntfy"` for a self-hosted ntfy server:

```ini
WEBHOOK_PROVIDER = "ntfy"
```

Save its complete HTTPS topic URL through the same hidden prompt:

```sh
spotify_profile_monitor --set-webhook-url
```

For ntfy.sh the value looks like `https://ntfy.sh/spotify-profile-monitor-long-random-value`. Self-hosted ntfy servers also require a complete HTTPS topic URL.

Spotify Profile Monitor sends the alert body as a native UTF-8 ntfy message and the alert subject as its title. Query parameters already in the topic URL are preserved. Long ntfy messages are visibly truncated below ntfy's 4 KB boundary so they remain notifications instead of temporary attachments.

The ntfy provider needs no request template. `WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` shape the Discord embed only and are ignored when `WEBHOOK_PROVIDER` is `"ntfy"`. To customize ntfy delivery, add ntfy options such as priority or tags through `WEBHOOK_HEADERS` (for example `X-Priority` or `X-Tags`).

Profile and playlist artwork is disabled by default and needs the optional artwork extra (`pip install "spotify_profile_monitor[notification-images]"`). Enable it in `spotify_profile_monitor.conf` once the extra is installed:

```ini
NTFY_IMAGES = True
```

If the setting is on but the extra is missing, the monitor reports it at startup and sends the affected alerts as text.

The monitor accepts artwork only from Spotify HTTPS CDN hosts. It limits downloads to 5 MiB and rejects oversized decoded images before preparing each attachment in memory. If image preparation fails the alert is sent as text. If an attachment upload fails the monitor retries once as text. Self-hosted ntfy servers must allow attachments.

Protected ntfy topics can use a Bearer access token stored in `.env`:

```ini
NTFY_ACCESS_TOKEN="tk_your_ntfy_access_token"
```

`NTFY_ACCESS_TOKEN` takes precedence over an `Authorization` entry in `WEBHOOK_HEADERS`. Custom headers remain available for other authentication methods and compatible integrations:

```ini
WEBHOOK_HEADERS = {
    "X-Webhook-Title": "{title}",
}
```

Header values support the same placeholders as the Discord template (`{title}`, `{description}`, `{version}`, `{image_url}`, `{color}`, `{timestamp}` and so on) and work with both providers. Headers are validated before and after placeholder expansion so formatted values cannot add invalid names, non-string values or line breaks.

### Advanced Discord-format customization

The settings in this section apply only when `WEBHOOK_PROVIDER` is `"discord"`. The ntfy provider ignores them.

`WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` control the sender name and HTTPS avatar for Discord-format payloads:

```ini
WEBHOOK_USERNAME = "Spotify Profile Monitor"
WEBHOOK_AVATAR_URL = "https://example.com/path/avatar.png"
```

`WEBHOOK_TEMPLATE` controls the Discord-format request body. Supported placeholders are `title`, `description`, `version`, `image_url`, `fields`, `fields_str`, `color`, `timestamp`, `username` and `avatar_url`.

A dictionary or list is sent as JSON. A string template is sent as a raw request body for compatible integrations. Dictionary payloads always replace `allowed_mentions` with `{"parse": []}` so alert text cannot trigger Discord mentions.

`WEBHOOK_TRANSFORMS` applies string methods to shared placeholder values before the template and headers are rendered:

```ini
WEBHOOK_TRANSFORMS = [
    ("title", "upper"),
    ("description", "replace", "**", ""),
]
```

The tuple format is `(field_to_target, method_name, *optional_arguments)`. Invalid templates, avatar URLs, transforms or formatted headers fail before a webhook request is attempted.

For automation or one-time testing `--webhook-url URL` overrides the destination without changing `.env`. The URL may remain visible in shell history or process listings:

```sh
spotify_profile_monitor --webhook-provider ntfy --webhook-url "https://ntfy.sh/your-private-topic" --send-test-webhook
```

For normal setup use the hidden command then send a test:

```sh
spotify_profile_monitor --set-webhook-url
spotify_profile_monitor --send-test-webhook
```

Email and webhook delivery are independent. A failure in one channel does not stop the other channel.

Webhook requests do not follow redirects, so `WEBHOOK_HEADERS` credentials and alert content can never be handed to a host you did not configure. If your destination answers with a redirect, delivery fails with a message telling you to save the final URL. Save it with `--set-webhook-url` then confirm with `--send-test-webhook`.

<a id="terminal-colours"></a>
## Terminal Colours

`COLORED_OUTPUT` controls whether live terminal output is coloured. It defaults to `True` and is read before the startup banner is printed, so a configured value applies to the first line of output. `--no-color` disables colour for one run. Colour also switches itself off when output is redirected or piped, when `TERM` is unset or `dumb` and when the standard [`NO_COLOR`](https://no-color.org/) environment variable is set. Log files are always written with the escape sequences stripped.

`COLOR_THEME` overrides individual colours. It is merged over the built-in theme, so name only the parts you want to change:

```ini
COLOR_THEME = { "playlist": "bright_magenta bold", "username": "green" }
```

A value combines one colour with any number of style attributes, separated by spaces or `+`, for example `"bright_cyan bold"`, `"red underline"` or `"bright_magenta bold underline"`. An empty string leaves that part uncoloured.

| Colours | Styles |
| --- | --- |
| `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` and the matching `bright_` variants such as `bright_red` | `bold`, `dim`, `underline`, `blink` |

Parts with the same name mean the same thing in [spotify_monitor](https://github.com/misiektoja/spotify_monitor), so a `COLOR_THEME` block can be shared between the two tools. Each tool lists only the parts it actually colours, so a few names appear in one and not the other.

| Theme key | Colours |
| --- | --- |
| `header` | The startup banner plus the Setup Wizard and Doctor headings |
| `section` | Commands the wizard tells you to run, and the Doctor section names |
| `username` | Spotify display names and quoted user names |
| `user_uri_id` | Spotify user IDs and URIs |
| `status_active` | `ACTIVE` and `PRIVATE MODE` status words |
| `status_inactive` | `INACTIVE` status words |
| `status_offline` | `OFFLINE` status words |
| `status_other` | Any other reported status word |
| `track` | Track names in listings and other quoted names |
| `playlist` | Playlist names |
| `duration` | Playlist durations and elapsed times |
| `timestamp_label` | The `Timestamp:` label. Empty by default, so the label stays plain like in the sibling monitors |
| `timestamp_value` | The timestamp value |
| `info`, `warning`, `error`, `signal` | Informational, warning, error and received-signal lines |
| `email`, `webhook` | Notification delivery lines |
| `date`, `date_range` | Single dates and times, and date or hour ranges |
| `boolean_true`, `boolean_false` | `True` / `Enabled` and `False` / `Disabled` |
| `count_up`, `count_down` | Reported changes only, such as `from 10 to 12` and the `(+2)` / `(-2)` differences. A static count is left plain |
| `link` | URLs |

On Windows, install the optional `colorama` package for the best results in the classic Command Prompt. Windows Terminal needs nothing extra.

To colour saved log files when you view them later, see [Coloring Log Output with GRC](usage.md#coloring-log-output-with-grc).

<a id="storing-secrets"></a>
## Storing Secrets

It is recommended to store secrets like `SP_DC_COOKIE`, `SP_APP_CLIENT_ID`, `SP_APP_CLIENT_SECRET`, `SP_USER_CLIENT_ID`, `SP_USER_CLIENT_SECRET`, `REFRESH_TOKEN`, `SP_SHA256`, `SMTP_PASSWORD`, `WEBHOOK_URL` or `NTFY_ACCESS_TOKEN` as either an environment variable or in a dotenv file. For `SP_DC_COOKIE`, prefer `spotify_profile_monitor --set-sp-dc` so the value is entered through a hidden prompt and validated before it is saved.

Set the needed environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

```sh
export SP_DC_COOKIE="your_sp_dc_cookie_value"
export SP_APP_CLIENT_ID="your_spotify_app_client_id"
export SP_APP_CLIENT_SECRET="your_spotify_app_client_secret"
export SP_USER_CLIENT_ID="your_spotify_user_client_id"
export SP_USER_CLIENT_SECRET="your_spotify_user_client_secret"
export REFRESH_TOKEN="your_spotify_app_refresh_token"
export SP_SHA256="your_spotify_client_sha256"
export SMTP_PASSWORD="your_smtp_password"
export WEBHOOK_URL="https://discord.com/api/webhooks/your_id/your_token"
export NTFY_ACCESS_TOKEN="tk_your_ntfy_access_token"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

Alternatively store them persistently in a dotenv file (recommended). Create a plain text file named `.env` in the directory where you run Spotify Profile Monitor then add only the values you use:

```ini
SP_DC_COOKIE="your_sp_dc_cookie_value"
SP_APP_CLIENT_ID="your_spotify_app_client_id"
SP_APP_CLIENT_SECRET="your_spotify_app_client_secret"
SP_USER_CLIENT_ID="your_spotify_user_client_id"
SP_USER_CLIENT_SECRET="your_spotify_user_client_secret"
REFRESH_TOKEN="your_spotify_app_refresh_token"
SP_SHA256="your_spotify_client_sha256"
SMTP_PASSWORD="your_smtp_password"
WEBHOOK_URL="https://discord.com/api/webhooks/your_id/your_token"
NTFY_ACCESS_TOKEN="tk_your_ntfy_access_token"
```

By default the tool will auto-search for dotenv file named `.env` in current directory and then upward from it.

Commands that write a secret do not use that upward search when choosing a destination. Without `--env-file`, `--set-sp-dc`, `--set-webhook-url` and browser cookie import all write to `.env` in the current directory.

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
spotify_profile_monitor <spotify_target> --env-file /path/.env-spotify_profile_monitor
```

 You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
spotify_profile_monitor <spotify_target> --env-file none
```

As a fallback, you can also store secrets in the configuration file or source code.

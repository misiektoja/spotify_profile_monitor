# Debugging Tools

To help with troubleshooting and development, two debug utilities are available in the [debug](https://github.com/misiektoja/spotify_monitor/tree/dev/debug) directory of the related [spotify_monitor](https://github.com/misiektoja/spotify_monitor) project.

<a id="access-token-retrieval-via-sp_dc-cookie-and-totp"></a>
## Access Token Retrieval via sp_dc Cookie and TOTP

The [spotify_monitor_totp_test](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_totp_test.py) tool retrieves a Spotify access token using a Web Player `sp_dc` cookie and TOTP parameters.

Download from [here](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_totp_test.py) or:

```sh
wget https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/dev/debug/spotify_monitor_totp_test.py
```

Install requirements:

```sh
pip install requests python-dateutil pyotp
```

Run:

```sh
python3 spotify_monitor_totp_test.py --sp-dc "your_sp_dc_cookie_value"
```

You should get a valid Spotify access token, example output:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_totp_test.png" alt="spotify_monitor_totp_test" width="100%"/>
</p>

> **NOTE:** Spotify still requires TOTP but continues to select v61. If the embedded values stop working, `spotify_monitor_totp_test` offers two recovery methods. `--fetch-secrets` launches a headless browser and extracts current values from Spotify Web Player. It requires Playwright plus its browser files. `--download-secrets` reads `SECRET_CIPHER_DICT_URL`, which may point to a remote URL or a local `file:` URL. The default remote source is [xyloflake/spot-secrets-go](https://github.com/xyloflake/spot-secrets-go). These options affect only the test utility during that run. Spotify Profile Monitor v3.5 uses `TOTP_VERSION` and `TOTP_SECRET_CIPHER_BYTES` instead.

```sh
python3 spotify_monitor_totp_test.py --sp-dc "your_sp_dc_cookie_value" --fetch-secrets
python3 spotify_monitor_totp_test.py --sp-dc "your_sp_dc_cookie_value" --download-secrets
```

<a id="secret-key-extraction-from-spotify-web-player-bundles"></a>
## Secret Key Extraction from Spotify Web Player Bundles

The [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_secret_grabber.py) tool automatically extracts secret keys used for TOTP generation in Spotify Web Player JavaScript bundles. Version 1.3 scans the loaded bundle source for the inline object-literal format used by the current web player and retains the original runtime property hook as a fallback for older formats.

The restored extractor returns v59, v60 and v61 directly from Spotify's current web-player bundle even when the original runtime hook reports no captures.

> **Quick tip:** The easiest and recommended way to run this tool is via Docker. Jump directly to the [Docker usage section below](#-secret-key-extraction-via-docker-recommended-easiest-way).

Download from [here](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_secret_grabber.py) or:

```sh
wget https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/dev/debug/spotify_monitor_secret_grabber.py
```

Install requirements:

```sh
pip install playwright
playwright install
```

Run interactively using the default output mode:

```sh
python3 spotify_monitor_secret_grabber.py
```

You should get output similar to below:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_secret_grabber.png" alt="spotify_monitor_secret_grabber" width="100%"/>
</p>

Show help:

```sh
python3 spotify_monitor_secret_grabber.py -h
```

---

<a id="cli-output-modes"></a>
## CLI Output Modes

The script supports several output modes for different use cases:

| Flag | Description | Output |
|------|-------------|--------|
| `--secret` | Prints plain JSON array of extracted secrets | `[{"version": X, "secret": "..."}, ...]` |
| `--secretbytes` | Prints JSON array with ASCII byte values | `[{"version": X, "secret": [..]}, ...]` |
| `--secretdict` | Prints JSON object/dict mapping version -> byte list | `{"X": [..], "Y": [..]}` |
| `--all` | Extracts secrets and writes all three outputs to local files | `secrets.json`, `secretBytes.json`, `secretDict.json` |

Print extracted secrets in a specific format. For example you can create a Python-friendly secret byte mapping and save it to a file:

```sh
python3 spotify_monitor_secret_grabber.py --secretdict > secretDict.json
```

Generate and save all secret formats at once:

```sh
python3 spotify_monitor_secret_grabber.py --all
```

Default file paths and names can be configured directly in the `OUTPUT_FILES` dictionary at the top of the script.

---

<a id="-secret-key-extraction-via-docker-recommended-easiest-way"></a>
## Secret Key Extraction via Docker (Recommended Easiest Way)

A prebuilt multi-architecture image is available on Docker Hub: [`misiektoja/spotify-secrets-grabber`](https://hub.docker.com/r/misiektoja/spotify-secrets-grabber)

This image works on:

- macOS (Intel and Apple Silicon)
- Linux (x86_64 and ARM64)
- Windows (Docker Desktop or WSL2)
- Raspberry Pi 4/5 (64-bit OS)

Run interactively using the default output mode:

```sh
docker run --rm misiektoja/spotify-secrets-grabber
```

Show help:

```sh
docker run --rm misiektoja/spotify-secrets-grabber -h
```

Print a Python-friendly secret byte mapping and save it to a file:

```sh
docker run --rm misiektoja/spotify-secrets-grabber --secretdict > secretDict.json
```

Generate and save all secret formats at once:

```sh
docker run --rm -v .:/work -w /work misiektoja/spotify-secrets-grabber --all
```

For SELinux hosts such as Fedora or RHEL use `-v .:/work:Z`.

<a id="optional-use-docker-compose-one-command-for-all-oss"></a>
You can optionally use Docker Compose with the preconfigured [compose.yaml](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_secret_grabber_docker/compose.yaml) file included in the repository:

```sh
docker compose run --rm spotify-secrets-grabber --all
```

This saves all files into the current directory on macOS, Linux or Windows.

---

You can use the generated `secretDict.json` with `spotify_monitor_totp_test` and `spotify_monitor`. `spotify_profile_monitor` v3.5 embeds v61 directly and no longer depends on an external dictionary. If Spotify selects a new TOTP version later then update the `TOTP_VERSION` and `TOTP_SECRET_CIPHER_BYTES` config options with the values from the current web-player bundle. No code change is required.

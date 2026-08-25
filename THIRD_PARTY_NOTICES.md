# Third-party notices

spotify_profile_monitor original code is licensed under GPL-3.0-or-later. See [LICENSE](LICENSE).

The distributed package contains no vendored third-party source. It declares the dependencies below, which are installed from PyPI under their own licenses and remain the property of their authors.

## Runtime dependencies

| Component | Required version | License | Use |
| --- | --- | --- | --- |
| [requests](https://github.com/psf/requests) | >=2.0 | Apache-2.0 | HTTP for Spotify, notifications and artwork downloads |
| [python-dateutil](https://github.com/dateutil/dateutil) | >=2.8 | Apache-2.0 or BSD-3-Clause | Timestamp parsing and relative date arithmetic |
| [urllib3](https://github.com/urllib3/urllib3) | >=2.0.7 | MIT | HTTP connection pooling and retry handling |
| [pyotp](https://github.com/pyauth/pyotp) | >=2.9.0 | MIT | TOTP generation for Spotify web-player token refresh |
| [pytz](https://github.com/stub42/pytz) | >=2020.1 | MIT | Timezone conversion for displayed and logged times |
| [tzlocal](https://github.com/regebro/tzlocal) | >=4.0 | MIT | Local timezone detection |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | >=0.19 | BSD-3-Clause | Reading secrets from `.env` |
| [spotipy](https://github.com/spotipy-dev/spotipy) | >=2.24.0 | MIT | Spotify Web API access for the OAuth token sources |
| [wcwidth](https://github.com/jquast/wcwidth) | >=0.2.7 | MIT | Terminal column widths for aligned output and truncation |
| [pathvalidate](https://github.com/thombashi/pathvalidate) | >=3.2.0 | MIT | Sanitizing playlist names into safe export filenames |
| [Pillow](https://github.com/python-pillow/Pillow) | >=10.0 | MIT-CMU | Artwork handling for email and ntfy image notifications |
| [pycookiecheat](https://github.com/n8henrie/pycookiecheat) | >=0.8, `browser` extra | MIT | Importing Chrome, Brave and Chromium cookies on macOS and Linux |

## Build, test and documentation dependencies

These are not part of the distributed package.

| Component | License | Use |
| --- | --- | --- |
| [pytest](https://github.com/pytest-dev/pytest) | MIT | Test suite |
| [PyYAML](https://github.com/yaml/pyyaml) | MIT | Validating workflows and issue templates in the test suite |
| [pip-audit](https://github.com/pypa/pip-audit) | Apache-2.0 | Dependency vulnerability audit in the supply chain workflow |
| [CycloneDX](https://github.com/CycloneDX/cyclonedx-python) | Apache-2.0 | Software bill of materials in the supply chain workflow |
| [setuptools](https://github.com/pypa/setuptools), [wheel](https://github.com/pypa/wheel) | MIT | Package build |

## External services

The tool contacts Spotify only. Optional notification delivery contacts the SMTP server, Discord webhook or ntfy server you configure. Nothing is sent anywhere you have not configured.

## Reporting a licensing problem

If you believe a dependency is misattributed here, open an issue or email <misiektoja-github@rm-rf.ninja>.

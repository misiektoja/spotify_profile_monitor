# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability.

Report it privately through [GitHub security advisories](https://github.com/misiektoja/spotify_profile_monitor/security/advisories/new), which keeps the report visible only to the maintainer until an advisory is published. If you cannot use that, email <misiektoja-github@rm-rf.ninja>.

Do not include your `sp_dc` cookie, captured Protobuf login files, Spotify OAuth client credentials, refresh tokens, SMTP passwords, webhook URLs, ntfy tokens or the profiles you monitor in a report. Include the affected version, the impact, the preconditions to reproduce it and a sanitized proof when you have one.

The maintainer will acknowledge the report and coordinate disclosure once a fix is available.

## Supported versions

Security fixes are made on the default branch and shipped in the next release to [PyPI](https://pypi.org/project/spotify-profile-monitor/) and the [GitHub releases](https://github.com/misiektoja/spotify_profile_monitor/releases). Only the latest released version is supported. Earlier versions receive no backports.

## Security posture

This tool holds credentials for your own Spotify account and records what other profiles publish. Both matter when you deploy it.

- **Configuration files are parsed, not executed.** Only documented `SETTING = value` lines with plain literal values are accepted. Imports, function calls, expressions and control flow are rejected without being run, so a configuration file found in the working directory cannot execute code.
- **Secrets belong in `.env`, not in the configuration file.** `--set-sp-dc`, `--set-webhook-url` and the setup wizard read the value through a hidden prompt and write it to `.env`. Generated `.env` and configuration files are written atomically and set to owner-only permissions on POSIX systems, and a timestamped configuration backup is created owner-only and keeps the mode of the file it copies, so replacing a private configuration never leaves a readable copy behind. Tokens are masked in Doctor output and logs.
- **Spotify-supplied text is untrusted input.** Profile names, playlist titles and descriptions are stripped of terminal control sequences, escaped before entering HTML email and webhook bodies and prefixed before entering CSV exports, so a crafted playlist name cannot drive your terminal, inject markup into a message you trust or carry a formula into an exported spreadsheet.
- **Downloads and requests stay bounded.** Artwork and profile-picture downloads accept only Spotify HTTPS CDN hosts, follow no redirects, are rejected on a non-image content type and are cut off at a byte limit enforced during streaming rather than trusted from `Content-Length` alone. Paginated Spotify requests stay bound to Spotify hosts, and exported playlist filenames are sanitized before they reach the filesystem.
- **Monitoring an account is subject to the law where you are.** The tool is intended for accounts you own or are authorized to observe.

## Supply chain

Every GitHub Actions workflow pins third-party actions to a commit SHA with the version recorded alongside it. The test suite fails when a pin or its version comment is missing, or when a workflow passes an event value straight into a shell. Dependencies and actions are tracked by Dependabot. Each change runs secret scanning, a dependency vulnerability audit and an SBOM build. CodeQL analyzes the Python source with the `security-extended` query set, and OpenSSF Scorecard scores the repository's security practices. See [.github/workflows/supply-chain.yml](https://github.com/misiektoja/spotify_profile_monitor/blob/main/.github/workflows/supply-chain.yml) and [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/spotify_profile_monitor/blob/main/THIRD_PARTY_NOTICES.md).

Publishing to PyPI runs the full test suite first and stops if it fails, so no untested artifact is released under the project's name. The upload runs in a named GitHub environment and uses trusted publishing rather than a stored API token.

The default branch and the development branch are protected by rulesets that block deletion and force pushes and require changes to arrive through a pull request.

# Contributing

spotify_profile_monitor is a real-time OSINT tool for tracking Spotify profile, playlist and follower changes. Bug reports, documentation fixes and code contributions are welcome.

## Before contributing

Open an issue or a [discussion](https://github.com/misiektoja/spotify_profile_monitor/discussions) before starting substantial work, so an approach is agreed before you write it. [SUPPORT.md](SUPPORT.md) lists where usage questions and bug reports belong. Suspected vulnerabilities go through [SECURITY.md](SECURITY.md), never a public issue.

Contribute only code you have the right to license under GPL-3.0-or-later.

Never commit `sp_dc` cookies, captured Protobuf login files, Spotify OAuth client credentials, refresh tokens, SMTP passwords, webhook URLs, ntfy tokens, generated configuration files, log files or exported playlists. Keep scratch files and local test state out of commits. Secret scanning and gitleaks run on every change, but they are a backstop, not the first line of defense.

## Development setup

```sh
git clone https://github.com/misiektoja/spotify_profile_monitor.git
cd spotify_profile_monitor
pip install -e '.[test]'
```

The test extra already installs Pillow, so the artwork tests run without the `notification-images` extra.

Add the optional extra when you touch browser cookie import:

```sh
pip install -e '.[test,browser]'
```

## Development checks

```sh
python -m ruff check spotify_profile_monitor.py tests
python -m pytest
mkdocs build --strict
```

The linter comes from a pinned extra so a new ruff release cannot fail your build on a rule that did not exist yet:

```sh
pip install -e '.[lint]'
```

It selects defect rules only (pyflakes and bugbear). Formatting and import order are deliberately not enforced, so keep following the surrounding code.

The documentation build needs its own dependencies:

```sh
pip install -r docs/requirements.txt
```

The default suite is offline. It never contacts Spotify and network functions are replaced with local test doubles. See [tests/README.md](tests/README.md) for what each test file covers and [Testing](https://misiektoja.github.io/spotify_profile_monitor/testing/) for the CI jobs and supply chain checks.

CI additionally runs the suite on Python 3.9 through 3.14, a Windows smoke job for the platform-sensitive behaviors and a strict documentation build. The supported Python floor is 3.9, so avoid syntax and standard-library features added after it. The CI job also imports the module and runs `--version` on every supported interpreter, which is where a newer syntax or annotation feature would surface first.

A change to token handling, the monitoring loop or playlist retrieval is not verified by the offline suite alone. Exercise it against a real Spotify account and say so in the pull request, without profile URLs or credentials.

## What a change needs

- **Tests.** New behavior needs a test. A bug fix needs a test that fails without it. Match the existing files in `tests/`.
- **Documentation.** User-facing behavior belongs under `docs/`, which is published at [misiektoja.github.io/spotify_profile_monitor](https://misiektoja.github.io/spotify_profile_monitor/). Document a new configuration setting or command-line option on the page that covers its feature and keep the README a short landing page. The documentation build is strict and the suite asserts that every in-app guide link resolves to a real page and anchor, so a broken link or a missing anchor fails CI.
- **A release-notes entry.** Add it under the unreleased section of [RELEASE_NOTES.md](RELEASE_NOTES.md), following the existing category and `**BUGFIX:**`, `**IMPROVE:**`, `**NEW:**` or `**BREAKING:**` prefixes. Write it for a user, not as an implementation log.
- **A Conventional Commits message.** Use the scope the repository already uses for that area, for example `fix(runtime):`, `test(config):` or `docs(usage):`.

Pull requests target `dev`. The pull request template lists the checks to report.

## Code style

The codebase favors complete implementations over minimal patches, explicit validation of anything Spotify supplies and one concise summary comment directly above each shared function. Follow the surrounding code rather than introducing a new style.

Optional local hooks run the same linter, the whitespace rules and a private-key check before a commit is written:

```sh
pip install pre-commit
pre-commit install
```

[.editorconfig](.editorconfig) records the whitespace rules the repository already follows: UTF-8, LF line endings, a final newline, no trailing whitespace, four-space indentation for Python and two spaces for YAML and TOML. Most editors apply it automatically, a few need a plugin. The test suite checks tracked files against the same rules, so a change made in an editor that ignores them will fail CI.

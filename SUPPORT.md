# Getting help

Start with the [README](README.md). [Installation](README.md#installation), [Quick Start](README.md#quick-start) and [Configuration](README.md#configuration) cover most first-run problems, and [Debugging Tools](README.md#debugging-tools) covers the rest.

## Check your setup first

The tool diagnoses itself. Run it before asking anything, and include its output when you do:

```sh
spotify_profile_monitor --doctor
```

It checks the environment, configuration, credentials, notifications and connectivity, and names the reason for anything invalid.

An expired `sp_dc` cookie is the most common cause of sudden authentication failures, empty results or a tool that worked yesterday and stopped today. The [Configuration](README.md#configuration) section explains how to refresh it.

## Where to ask

| You want to | Go to |
| --- | --- |
| Ask a question or discuss an idea | [Discussions](https://github.com/misiektoja/spotify_profile_monitor/discussions) |
| Report something broken | [Bug report](https://github.com/misiektoja/spotify_profile_monitor/issues/new?template=bug_report.yml) |
| Request a capability | [Feature request](https://github.com/misiektoja/spotify_profile_monitor/issues/new?template=feature_request.yml) |
| Report a vulnerability | [Private security advisory](https://github.com/misiektoja/spotify_profile_monitor/security/advisories/new), never a public issue |
| Contribute a change | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Before you post

Include the version, how you installed it (PyPI or manual script), your operating system, which authentication method you use and the `--doctor` output. Run the failing command with `--debug` and attach the relevant part of the log.

Never post your `sp_dc` cookie, Spotify client ID or client secret, SMTP passwords, webhook URLs or a complete configuration file. Redact monitored usernames and playlist names if they matter to you. See [SECURITY.md](SECURITY.md).

## What to expect

This is a project maintained in spare time, so replies are best effort with no response time attached. Only the latest release receives fixes, as [SECURITY.md](SECURITY.md) describes, so reproduce the problem on the current version before reporting it.

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).

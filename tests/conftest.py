"""Shared pytest fixtures for the offline test suite."""

import pytest

import spotify_profile_monitor as monitor


@pytest.fixture(autouse=True)
# Clears exported secrets between tests so a dotenv loaded by one test cannot change what a later one resolves
def clean_secret_environment(monkeypatch):
    # load_dotenv writes into os.environ and nothing removes it again, so a test that loads a dotenv would
    # otherwise leak its secrets into every later test through the exported-environment lookup at startup
    for secret in monitor.SECRET_KEYS:
        monkeypatch.delenv(secret, raising=False)


# Enumerators that read whichever browsers are installed on the machine running the suite
_BROWSER_PROFILE_ENUMERATORS = ("discover_firefox_profiles", "discover_chromium_profiles")
_REAL_BROWSER_PROFILE_ENUMERATORS = {name: getattr(monitor, name) for name in _BROWSER_PROFILE_ENUMERATORS}


@pytest.fixture(autouse=True)
# Keeps the suite away from the real browser profiles of whoever runs it, which are slow to reach and differ per machine
def stub_browser_profile_discovery(monkeypatch):
    for name in _BROWSER_PROFILE_ENUMERATORS:
        monkeypatch.setattr(monitor, name, lambda *arguments, **keywords: [])


@pytest.fixture
# Restores the real enumerators for the tests that exercise them against their own synthetic browser roots
def real_browser_profiles(monkeypatch):
    for name, enumerator in _REAL_BROWSER_PROFILE_ENUMERATORS.items():
        monkeypatch.setattr(monitor, name, enumerator)


@pytest.fixture(autouse=True)
# Clears the wizard browser-login cache around every test, since a count left behind changes what a later menu reports
def reset_wizard_browser_counts():
    monitor._WIZARD_BROWSER_LOGIN_COUNTS.clear()
    yield
    monitor._WIZARD_BROWSER_LOGIN_COUNTS.clear()


# Returns a check's recovery advice, failing the test when the row carries none rather than reading through None
def advice_of(check):
    assert check.advice is not None, f"{check.label} carries no recovery advice"
    return check.advice

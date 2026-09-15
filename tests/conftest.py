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


# Returns a check's recovery advice, failing the test when the row carries none rather than reading through None
def advice_of(check):
    assert check.advice is not None, f"{check.label} carries no recovery advice"
    return check.advice

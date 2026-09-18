"""Checks current OAuth user playlist reads and resource-specific fallback."""

import copy
import json
from unittest.mock import Mock

import pytest
import requests

import spotify_profile_monitor as monitor

PLAYLIST = "spotify:playlist:owned"
TRACK = {"name": "Track", "uri": "spotify:track:one", "artists": [{"name": "Artist", "uri": "spotify:artist:one"}], "duration_ms": 123000, "album": {"images": []}}


# Supplies realistic REST responses to the playlist parser
def response(status=200, body=None):
    result = requests.Response()
    result.status_code = status
    result.url = monitor.SPOTIFY_API_BASE_URL + "/playlists/owned"
    result._content = json.dumps(body or {}).encode()
    return result


# Builds either generation of playlist metadata
def metadata(field="items", total=1):
    return {"name": "Owned", "owner": {"display_name": "Owner", "uri": "spotify:user:owner"}, "images": [], field: {"total": total}}


@pytest.fixture(autouse=True)
# Keeps user restrictions separate from legacy app preference in every test
def isolated_backend(monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "oauth_user")
    monkeypatch.setattr(monitor, "SP_USER_PLAYLIST_WEB_UNTIL", {})
    monkeypatch.setattr(monitor, "SP_WEB_PLAYLIST_BACKEND_PREFERRED", False)
    monkeypatch.setattr(monitor, "SP_WEB_PLAYLIST_API_FAILURES", 0)


@pytest.mark.parametrize("field", ["item", "track"])
# Normalizes both item generations and follows modern pagination with the user token
def test_items_pages_are_normalized(monkeypatch, field):
    first = {"items": [{field: TRACK, "added_at": "2026-01-01T00:00:00Z"}], "next": monitor.SPOTIFY_API_BASE_URL + "/playlists/owned/items?offset=1", "total": 2}
    second = {"items": [{field: TRACK}], "next": None, "total": 2}
    get = Mock(side_effect=[response(body=metadata(total=2)), response(body=first), response(body=second)])
    monkeypatch.setattr(monitor.SESSION, "get", get)
    web = Mock()
    monkeypatch.setattr(monitor, "spotify_get_playlist_info_web", web)
    result = monitor.spotify_get_playlist_info("user-token", PLAYLIST, True)
    assert result["sp_playlist_source"] == "api"
    assert result["sp_playlist_tracks_count"] == 2
    assert all(item["track"] == TRACK for item in result["sp_playlist_tracks"])
    assert "/items?limit=50" in get.call_args_list[1].args[0]
    assert "fields=" not in get.call_args_list[0].args[0]
    assert all(call.kwargs["headers"]["Authorization"] == "Bearer user-token" for call in get.call_args_list)
    web.assert_not_called()


# Retains an older app's tracks route when the modern route is unavailable
def test_legacy_route_compatibility(monkeypatch):
    get = Mock(side_effect=[response(body=metadata("tracks")), response(404), response(body={"items": [{"track": TRACK}], "next": None})])
    monkeypatch.setattr(monitor.SESSION, "get", get)
    result = monitor.spotify_get_playlist_info("user-token", PLAYLIST, True)
    assert result["sp_playlist_tracks"][0]["track"] == TRACK
    assert "/tracks?limit=50" in get.call_args_list[2].args[0]
    assert "fields=" not in get.call_args_list[2].args[0]


# Does not probe legacy routes after a modern permission rejection
def test_items_403_falls_back_without_legacy_retry(monkeypatch):
    get = Mock(side_effect=[response(body=metadata()), response(403)])
    monkeypatch.setattr(monitor.SESSION, "get", get)
    monkeypatch.setattr(monitor, "spotify_get_playlist_info_web", Mock(return_value={"sp_playlist_name": "Public"}))
    assert monitor.spotify_get_playlist_info("user-token", PLAYLIST, True)["sp_playlist_source"] == "web"
    assert get.call_count == 2
    assert monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED is False


# Public playlist restrictions do not prevent another owned playlist using OAuth
def test_restriction_is_per_playlist_and_token(monkeypatch):
    denied = requests.HTTPError(response=response(403))
    api = Mock(side_effect=[denied, {"sp_playlist_name": "Owned"}, {"sp_playlist_name": "Other token"}])
    monkeypatch.setattr(monitor, "_spotify_get_playlist_info_api", api)
    web = Mock(side_effect=lambda *_args: {"sp_playlist_name": "Public"})
    monkeypatch.setattr(monitor, "spotify_get_playlist_info_web", web)
    monitor.spotify_get_playlist_info("first", "spotify:playlist:public", True)
    monitor.spotify_get_playlist_info("first", "spotify:playlist:public", True)
    assert monitor.spotify_get_playlist_info("first", PLAYLIST, True)["sp_playlist_source"] == "api"
    assert monitor.spotify_get_playlist_info("second", "spotify:playlist:public", True)["sp_playlist_source"] == "api"
    assert api.call_count == 3
    assert web.call_count == 2


# A resource restriction is checked again after its bounded cache lifetime
def test_restriction_expires(monkeypatch):
    now = [10.0]
    monkeypatch.setattr(monitor.time, "monotonic", lambda: now[0])
    api = Mock(side_effect=[requests.HTTPError(response=response(403)), {"sp_playlist_name": "Available"}])
    monkeypatch.setattr(monitor, "_spotify_get_playlist_info_api", api)
    monkeypatch.setattr(monitor, "spotify_get_playlist_info_web", Mock(return_value={"sp_playlist_name": "Public"}))
    monitor.spotify_get_playlist_info("token", PLAYLIST, True)
    now[0] += monitor.SP_USER_PLAYLIST_RECHECK_SECONDS
    assert monitor.spotify_get_playlist_info("token", PLAYLIST, True)["sp_playlist_source"] == "api"


# Metadata without content access falls back without requesting a known missing collection
def test_metadata_only_response_skips_contents_request(monkeypatch):
    body = metadata()
    body.pop("items")
    get = Mock(return_value=response(body=body))
    monkeypatch.setattr(monitor.SESSION, "get", get)
    monkeypatch.setattr(monitor, "spotify_get_playlist_info_web", Mock(return_value={"sp_playlist_name": "Public"}))
    assert monitor.spotify_get_playlist_info("token", PLAYLIST, True)["sp_playlist_source"] == "web"
    assert get.call_count == 1


# A valid empty private playlist keeps its OAuth result
def test_empty_playlist_uses_api(monkeypatch):
    monkeypatch.setattr(monitor.SESSION, "get", Mock(side_effect=[response(body=metadata(total=0)), response(body={"items": [], "next": None})]))
    result = monitor.spotify_get_playlist_info("token", PLAYLIST, True)
    assert result["sp_playlist_tracks_count"] == 0
    assert result["sp_playlist_source"] == "api"


# Dates remain available in metadata-only mode under the modern response contract
def test_dates_only_with_modern_items(monkeypatch):
    item = {"item": copy.deepcopy(TRACK), "added_at": "2026-01-01T00:00:00Z"}
    monkeypatch.setattr(monitor.SESSION, "get", Mock(side_effect=[response(body=metadata()), response(body={"items": [item], "next": None})]))
    result = monitor.spotify_get_playlist_info("token", PLAYLIST, False)
    assert result["sp_playlist_tracks"][0]["added_at"] == item["added_at"]

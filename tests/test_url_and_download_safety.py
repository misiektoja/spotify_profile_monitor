import json
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

import pytest
from requests.models import PreparedRequest

import spotify_profile_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "download_safety_test_artifacts"


# Creates one disposable download test directory under the project local directory
def make_test_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=str(ARTIFACT_ROOT))


class FakeImageResponse:
    # Initializes one streamed image response from fixed chunks and headers
    def __init__(self, chunks, status_code=200, headers=None):
        self.chunks = chunks
        self.status_code = status_code
        self.headers = headers if headers is not None else {"Content-Type": "image/jpeg"}

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    # Mirrors requests by raising only for client and server errors
    def raise_for_status(self):
        if 400 <= self.status_code <= 599:
            raise RuntimeError(f"{self.status_code} Error")

    def iter_content(self, chunk_size=None):
        return iter(self.chunks)


@pytest.mark.parametrize("value,expected", [("https://open.spotify.com/playlist/3cEYpjA9oz9GiPac4AsH4n", "spotify:playlist:3cEYpjA9oz9GiPac4AsH4n"), ("https://open.spotify.com/user/someone", "spotify:user:someone"), ("https://open.spotify.com/track/abc?si=xyz", "spotify:track:abc"), ("https://open.spotify.com/intl-pl/track/abc?si=xyz", "spotify:track:abc"), ("https://open.spotify.com/playlist/abc/", "spotify:playlist:abc"), ("spotify:playlist:abc", "spotify:playlist:abc"), ("SPOTIFY:PLAYLIST:abc", "spotify:playlist:abc")])
# Confirms well-formed links and URIs still resolve to the expected Spotify URI
def test_convert_url_to_uri_accepts_valid_references(value, expected):
    assert monitor.spotify_convert_url_to_uri(value) == expected


@pytest.mark.parametrize("value,expected", [("https://open.spotify.com/playlist/user0000000000000000000", "spotify:playlist:user0000000000000000000"), ("https://open.spotify.com/album/track00000000000000000000", "spotify:album:track00000000000000000000"), ("https://open.spotify.com/user/albumuser0000000000000000", "spotify:user:albumuser0000000000000000")])
# Confirms an object ID that merely contains a type word is no longer mistaken for that type
def test_convert_url_to_uri_matches_whole_segments(value, expected):
    assert monitor.spotify_convert_url_to_uri(value) == expected


@pytest.mark.parametrize("value", ["myuserplaylist", "user", "track/", "a track b", "spotify:", "spotify:x:y", "spotify:playlist:", "https://open.spotify.com/playlist/", "https://example.com/", "", None, 12345, ["list"]])
# Confirms unparseable references return an empty string instead of raising IndexError
def test_convert_url_to_uri_never_raises(value):
    assert monitor.spotify_convert_url_to_uri(value) == ""


@pytest.mark.parametrize("uri", ["spotify:user:abc", "spotify:artist:r1", "spotify:track:xyz", "spotify:album:a1", "spotify:playlist:p1"])
# Confirms the URL and URI converters remain inverses of each other
def test_convert_url_to_uri_round_trips(uri):
    assert monitor.spotify_convert_url_to_uri(monitor.spotify_convert_uri_to_url(uri)) == uri


# Confirms an unparseable playlist reference fails with the dedicated message instead of an opaque API error
def test_list_tracks_rejects_unparseable_playlist():
    with pytest.raises(ValueError, match="Invalid Spotify playlist"):
        monitor.spotify_list_tracks_for_playlist("token", "not-a-playlist-reference", "")


# Confirms the search term is passed as a parameter so it cannot truncate the URL or inject query parameters
def test_search_users_encodes_the_search_term(monkeypatch, capsys):
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"searchV2": {"users": {"totalCount": 0}}}}

    def fake_get(url, params=None, headers=None, timeout=None, verify=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse()

    monkeypatch.setattr(monitor, "SESSION", types.SimpleNamespace(get=fake_get))
    monkeypatch.setattr(monitor, "SP_SHA256", "deadbeef")

    hostile_term = 'bob#frag&limit=999 smith"'
    monitor.spotify_search_users("token", hostile_term)
    capsys.readouterr()

    assert "?" not in captured["url"] and "#" not in captured["url"]
    assert json.loads(captured["params"]["variables"])["searchTerm"] == hostile_term
    assert json.loads(captured["params"]["extensions"])["persistedQuery"]["sha256Hash"] == "deadbeef"

    prepared = PreparedRequest()
    prepared.prepare_url(captured["url"], captured["params"])
    prepared_url = prepared.url or ""
    # The fragment and ampersand are encoded, so the extensions parameter still reaches Spotify
    assert "%23" in prepared_url and "%26" in prepared_url
    assert "extensions=" in prepared_url


@pytest.mark.parametrize("url,allowed", [("https://i.scdn.co/image/ab1", True), ("https://image-cdn-ak.spotifycdn.com/image/ab1", True), ("https://mosaic.scdn.co/640/ab1", True), ("https://evil.example/x.jpg", False), ("http://i.scdn.co/image/ab1", False), ("https://notscdn.co/x.jpg", False), ("https://i.scdn.co.evil.example/x.jpg", False)])
# Confirms profile pictures are only fetched from Spotify HTTPS CDN hosts
def test_save_profile_pic_host_allowlist(url, allowed):
    assert monitor.spotify_image_url_is_allowed(url) is allowed


# Confirms an off-allowlist URL is refused before any request is made and writes no file
def test_save_profile_pic_refuses_foreign_host():
    with make_test_directory() as directory:
        target = Path(directory) / "pic.jpeg"
        with patch.object(monitor.req, "get") as fake_get:
            assert monitor.save_profile_pic("https://evil.example/huge.jpg", str(target)) is False
        fake_get.assert_not_called()
        assert not target.exists()


# Confirms an oversized body is refused at the cap and leaves an already saved picture untouched
def test_save_profile_pic_enforces_byte_cap():
    with make_test_directory() as directory:
        target = Path(directory) / "pic.jpeg"
        target.write_bytes(b"ORIGINAL")
        oversized = [b"x" * (1024 * 1024)] * ((monitor.NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES // (1024 * 1024)) + 3)
        with patch.object(monitor.req, "get", return_value=FakeImageResponse(oversized)):
            assert monitor.save_profile_pic("https://i.scdn.co/image/ab1", str(target)) is False
        assert target.read_bytes() == b"ORIGINAL"


# Confirms a declared oversized Content-Length is refused without reading the body
def test_save_profile_pic_honors_content_length():
    with make_test_directory() as directory:
        target = Path(directory) / "pic.jpeg"
        headers = {"Content-Type": "image/jpeg", "Content-Length": str(monitor.NOTIFICATION_IMAGE_DOWNLOAD_LIMIT_BYTES + 1)}
        with patch.object(monitor.req, "get", return_value=FakeImageResponse([b"tiny"], headers=headers)):
            assert monitor.save_profile_pic("https://i.scdn.co/image/ab1", str(target)) is False
        assert not target.exists()


# Confirms a redirect is not followed and is treated as a failed download
def test_save_profile_pic_does_not_follow_redirects():
    captured = {}

    def capture_get(url, **kwargs):
        captured.update(kwargs)
        return FakeImageResponse([], status_code=302, headers={"Location": "https://evil.example/x.jpg"})

    with make_test_directory() as directory:
        target = Path(directory) / "pic.jpeg"
        with patch.object(monitor.req, "get", side_effect=capture_get):
            assert monitor.save_profile_pic("https://i.scdn.co/image/ab1", str(target)) is False
        assert captured.get("allow_redirects") is False
        assert not target.exists()


# Confirms an allowed, in-budget picture is still saved normally
def test_save_profile_pic_saves_allowed_image():
    with make_test_directory() as directory:
        target = Path(directory) / "pic.jpeg"
        with patch.object(monitor.req, "get", return_value=FakeImageResponse([b"JPEG", b"DATA"])):
            assert monitor.save_profile_pic("https://i.scdn.co/image/ab1", str(target)) is True
        assert target.read_bytes() == b"JPEGDATA"


# Confirms every webhook POST call site refuses redirects
def test_webhook_posts_disable_redirects():
    import inspect

    post_lines = [line for line in inspect.getsource(monitor).splitlines() if "WEBHOOK_SESSION.post" in line]
    assert post_lines
    assert all("allow_redirects=False" in line for line in post_lines)


# Confirms a redirected webhook is reported as its own actionable failure
def test_webhook_redirect_is_classified():
    advice = monitor.classify_recovery_error(types.SimpleNamespace(status_code=307), "webhook")
    assert advice.code == "webhook.redirected"
    assert advice.code in monitor.RECOVERY_CODES
    assert "--set-webhook-url" in advice.fix


@pytest.mark.parametrize("status,expected", [(429, "webhook.rate_limited"), (404, "webhook.rejected"), (500, "webhook.connection")])
# Confirms the redirect branch did not change the existing webhook classifications
def test_webhook_classifications_unchanged(status, expected):
    assert monitor.classify_recovery_error(types.SimpleNamespace(status_code=status), "webhook").code == expected


# Returns the previous quadratic result used as the reference implementation
def legacy_compare(list1, list2):
    list1 = list1 or []
    list2 = list2 or []
    return [item for item in list1 + list2 if item not in list2]


@pytest.mark.parametrize("list1,list2", [([{"uri": "u1"}, {"uri": "u2"}], [{"uri": "u2"}]), ([], [{"uri": "u1"}]), ([{"uri": "u1"}], []), ([{"uri": "u1"}], [{"uri": "u1"}]), (None, None), ([{"uri": "x"}, {"uri": "x"}], []), ([{"name": "a", "uri": "u1"}], [{"uri": "u1", "name": "a"}])])
# Confirms the set-based diff returns exactly what the previous linear scan returned
def test_compare_two_lists_of_dicts_matches_legacy(list1, list2):
    assert monitor.compare_two_lists_of_dicts(list1, list2) == legacy_compare(list1, list2)


# Confirms a large follower list is diffed without the previous quadratic scan
def test_compare_two_lists_of_dicts_scales():
    old = [{"uri": f"spotify:user:{index}", "name": f"n{index}"} for index in range(5000)]
    new = [{"uri": f"spotify:user:{index}", "name": f"n{index}"} for index in range(1, 5001)]
    assert monitor.compare_two_lists_of_dicts(old, new) == [{"uri": "spotify:user:0", "name": "n0"}]
    assert monitor.compare_two_lists_of_dicts(new, old) == [{"uri": "spotify:user:5000", "name": "n5000"}]


@pytest.mark.parametrize("item", [{"a": 1}, {}, "text", None, 7])
# Confirms signatures stay hashable for the value shapes Spotify returns
def test_dict_signature_is_hashable(item):
    assert isinstance(hash(monitor.dict_signature(item)), int)

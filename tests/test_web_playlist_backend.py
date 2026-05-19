import copy
import unittest
from unittest.mock import Mock, patch

import requests

import spotify_profile_monitor as monitor


# Verifies the automatic Spotify web-player playlist backend
class WebPlaylistBackendTests(unittest.TestCase):
    # Resets mutable backend state before each test
    def setUp(self):
        self.original_token_source = monitor.TOKEN_SOURCE
        self.original_client_id = monitor.SP_APP_CLIENT_ID
        self.original_client_secret = monitor.SP_APP_CLIENT_SECRET
        self.original_user_agent = monitor.USER_AGENT
        monitor.TOKEN_SOURCE = "cookie"
        monitor.SP_APP_CLIENT_ID = "your_spotify_app_client_id"
        monitor.SP_APP_CLIENT_SECRET = "your_spotify_app_client_secret"
        monitor.USER_AGENT = "Mozilla/5.0"
        monitor.SP_CACHED_PLAYLIST_QUERY_HASH = ""
        monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED = False
        monitor.SP_WEB_PLAYLIST_API_FAILURES = 0
        monitor.WEB_PLAYLIST_REVISION_CACHE.clear()

    # Restores mutable backend state after each test
    def tearDown(self):
        monitor.TOKEN_SOURCE = self.original_token_source
        monitor.SP_APP_CLIENT_ID = self.original_client_id
        monitor.SP_APP_CLIENT_SECRET = self.original_client_secret
        monitor.USER_AGENT = self.original_user_agent
        monitor.SP_CACHED_PLAYLIST_QUERY_HASH = ""
        monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED = False
        monitor.SP_WEB_PLAYLIST_API_FAILURES = 0
        monitor.WEB_PLAYLIST_REVISION_CACHE.clear()

    # Verifies the embedded v61 cipher generates the expected TOTP
    def test_generates_expected_v61_totp(self):
        self.assertEqual(monitor.TOTP_VERSION, 61)
        self.assertEqual(monitor.generate_totp().at(1700000000), "371599")

    # Verifies a configured TOTP override flows through to the generated token
    def test_totp_config_override_is_used(self):
        with patch.object(monitor, "TOTP_VERSION", 99), patch.object(monitor, "TOTP_SECRET_CIPHER_BYTES", (12, 34, 56, 78)):
            token = monitor.generate_totp()
        self.assertEqual(len(token.now()), 6)

    # Verifies invalid configured TOTP parameters raise an actionable error
    def test_generate_totp_rejects_invalid_config(self):
        with patch.object(monitor, "TOTP_SECRET_CIPHER_BYTES", ()):
            with self.assertRaises(ValueError):
                monitor.generate_totp()
        with patch.object(monitor, "TOTP_SECRET_CIPHER_BYTES", ("bad", 55)):
            with self.assertRaises(ValueError):
                monitor.generate_totp()
        with patch.object(monitor, "TOTP_VERSION", 0):
            with self.assertRaises(ValueError):
                monitor.generate_totp()

    # Verifies anonymous token retrieval skips the authenticated validity probe
    def test_anonymous_token_skips_authenticated_validity_probe(self):
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {"accessToken": "anonymous-token", "accessTokenExpirationTimestampMs": 1700003600000, "clientId": "web-client"}
        session = Mock()
        session.get.return_value = response

        with patch.object(monitor.req, "Session", return_value=session), patch.object(monitor, "fetch_server_time", return_value=1700000000), patch.object(monitor, "check_token_validity") as validity_check:
            token_data = monitor.refresh_access_token_from_sp_dc("")

        self.assertEqual(token_data["access_token"], "anonymous-token")
        self.assertEqual(session.get.call_count, 1)
        self.assertEqual(session.get.call_args.kwargs["params"]["totpVer"], 61)
        validity_check.assert_not_called()

    # Verifies startup output describes only playlist backends available from configuration
    def test_describes_configured_playlist_backend(self):
        self.assertEqual(monitor.spotify_get_playlist_backend_description(), "web player")
        monitor.SP_APP_CLIENT_ID = "legacy-client"
        monitor.SP_APP_CLIENT_SECRET = "legacy-secret"
        self.assertEqual(monitor.spotify_get_playlist_backend_description(), "automatic (legacy Web API + web player)")
        monitor.SP_APP_CLIENT_ID = "your_spotify_app_client_id"
        monitor.SP_APP_CLIENT_SECRET = "your_spotify_app_client_secret"
        monitor.TOKEN_SOURCE = "oauth_user"
        self.assertEqual(monitor.spotify_get_playlist_backend_description(), "automatic (legacy Web API + web player)")

    # Discovers the playlist persisted-query hash from the canonical web-player bundle
    def test_discovers_playlist_query_hash(self):
        expected_hash = "a" * 64
        html_response = Mock(status_code=200, text='<script src="https://open.spotifycdn.com/cdn/generated/manifest-web-player.js"></script><script src="https://open.spotifycdn.com/cdn/build/web-player/web-player.1234.js"></script>')
        html_response.raise_for_status.return_value = None
        bundle_response = Mock(status_code=200, text=f'new x("fetchPlaylistContents","query","{expected_hash}",null)')
        bundle_response.raise_for_status.return_value = None

        with patch.object(monitor.SESSION, "get", side_effect=[html_response, bundle_response]) as session_get:
            actual_hash = monitor.spotify_discover_playlist_query_hash()

        self.assertEqual(actual_hash, expected_hash)
        self.assertEqual(session_get.call_count, 2)
        self.assertIn("/web-player/web-player.1234.js", session_get.call_args_list[1].args[0])

    # Normalizes and paginates web-player playlist responses without losing collaborator data
    def test_normalizes_and_paginates_playlist(self):
        playlist_uri = "spotify:playlist:playlist123"
        metadata = {"playlistV2": {"attributes": [], "content": {"totalCount": 3}, "description": "Description", "followers": 12, "images": {"items": [{"sources": [{"url": "https://image.test/cover.jpg"}]}]}, "name": "Playlist", "ownerV2": {"data": {"name": "Owner", "uri": "spotify:user:owner123", "username": "owner123"}}, "revisionId": "revision-1", "sharingInfo": {"shareUrl": "https://open.spotify.com/playlist/playlist123"}}}
        first_item = {"addedAt": {"isoString": "2026-07-01T10:00:00Z"}, "addedBy": {"data": {"name": "Friend", "uri": "spotify:user:friend123", "username": "friend123"}}, "itemV2": {"data": {"artists": {"items": [{"profile": {"name": "Artist One"}, "uri": "spotify:artist:artist1"}]}, "name": "Track One", "trackDuration": {"totalMilliseconds": 180000}, "uri": "spotify:track:track1"}}}
        second_item = copy.deepcopy(first_item)
        second_item["addedAt"]["isoString"] = "2026-07-02T10:00:00Z"
        second_item["itemV2"]["data"].update({"name": "Track Two", "uri": "spotify:track:track2"})
        third_item = copy.deepcopy(first_item)
        third_item["addedAt"]["isoString"] = "2026-07-03T10:00:00Z"
        third_item["itemV2"]["data"].update({"name": "Track Three", "uri": "spotify:track:track3"})
        first_page = {"playlistV2": {"content": {"items": [first_item, second_item], "totalCount": 3}}}
        second_page = {"playlistV2": {"content": {"items": [third_item], "totalCount": 3}}}

        with patch.object(monitor, "spotify_web_playlist_query", side_effect=[metadata, first_page, second_page]) as query:
            result = monitor.spotify_get_playlist_info_web(playlist_uri, True)

        self.assertEqual(result["sp_playlist_name"], "Playlist")
        self.assertEqual(result["sp_playlist_followers_count"], 12)
        self.assertEqual(result["sp_playlist_owner_uri"], "spotify:user:owner123")
        self.assertEqual(result["sp_playlist_tracks_count"], 3)
        self.assertEqual(result["sp_playlist_tracks"][0]["added_by"]["id"], "friend123")
        self.assertEqual(result["sp_playlist_tracks"][2]["track"]["artists"][0]["name"], "Artist One")
        self.assertEqual(query.call_args_list[1].args[1]["offset"], 0)
        self.assertEqual(query.call_args_list[2].args[1]["offset"], 2)

    # Reuses normalized tracks when playlist metadata reports the same revision
    def test_reuses_cached_playlist_revision(self):
        playlist_uri = "spotify:playlist:cached123"
        metadata = {"playlistV2": {"attributes": [], "content": {"totalCount": 1}, "description": "", "followers": 1, "images": {"items": []}, "name": "Cached", "ownerV2": {"data": {"name": "Owner", "uri": "spotify:user:owner123"}}, "revisionId": "same-revision", "sharingInfo": {}}}
        item = {"addedAt": {"isoString": "2026-07-01T10:00:00Z"}, "addedBy": {"data": {"uri": "spotify:user:owner123", "username": "owner123"}}, "itemV2": {"data": {"artists": {"items": [{"profile": {"name": "Artist"}, "uri": "spotify:artist:artist1"}]}, "name": "Track", "trackDuration": {"totalMilliseconds": 120000}, "uri": "spotify:track:track1"}}}
        contents = {"playlistV2": {"content": {"items": [item], "totalCount": 1}}}

        with patch.object(monitor, "spotify_web_playlist_query", side_effect=[metadata, contents, metadata]) as query:
            first_result = monitor.spotify_get_playlist_info_web(playlist_uri, True)
            second_result = monitor.spotify_get_playlist_info_web(playlist_uri, True)

        self.assertEqual(first_result["sp_playlist_tracks"], second_result["sp_playlist_tracks"])
        self.assertEqual(query.call_count, 3)

    # Fetches metadata only and skips track pagination when get_tracks is False
    def test_metadata_only_when_get_tracks_false(self):
        playlist_uri = "spotify:playlist:meta123"
        metadata = {"playlistV2": {"attributes": [], "content": {"totalCount": 42}, "description": "Description", "followers": 7, "images": {"items": [{"sources": [{"url": "https://image.test/cover.jpg"}]}]}, "name": "Playlist", "ownerV2": {"data": {"name": "Owner", "uri": "spotify:user:owner123", "username": "owner123"}}, "revisionId": "revision-1", "sharingInfo": {}}}

        with patch.object(monitor, "spotify_web_playlist_query", side_effect=[metadata]) as query:
            result = monitor.spotify_get_playlist_info_web(playlist_uri, False)

        self.assertEqual(query.call_count, 1)
        self.assertEqual(query.call_args_list[0].args[0], "fetchPlaylistMetadata")
        self.assertEqual(result["sp_playlist_tracks_count"], 42)
        self.assertEqual(result["sp_playlist_tracks_count_before_filtering"], 42)
        self.assertEqual(result["sp_playlist_tracks"], [])
        self.assertEqual(result["sp_playlist_name"], "Playlist")

    # Preserves the legacy Web API path when configured credentials still work
    def test_preserves_working_legacy_api_backend(self):
        monitor.SP_APP_CLIENT_ID = "legacy-client"
        monitor.SP_APP_CLIENT_SECRET = "legacy-secret"
        expected = {"sp_playlist_name": "Legacy"}

        with patch.object(monitor, "_spotify_get_playlist_info_api", return_value=expected) as api_backend, patch.object(monitor, "spotify_get_playlist_info_web") as web_backend:
            result = monitor.spotify_get_playlist_info("legacy-token", "spotify:playlist:legacy123", True)

        self.assertEqual(result, expected)
        self.assertEqual(result.get("sp_playlist_source"), "api")
        api_backend.assert_called_once()
        web_backend.assert_not_called()

    # Switches automatically to the web backend after a restricted Web API response
    def test_switches_to_web_backend_after_403(self):
        monitor.SP_APP_CLIENT_ID = "restricted-client"
        monitor.SP_APP_CLIENT_SECRET = "restricted-secret"
        response = Mock(status_code=403)
        api_error = requests.HTTPError("403 Client Error", response=response)
        expected = {"sp_playlist_name": "Web"}

        with patch.object(monitor, "_spotify_get_playlist_info_api", side_effect=api_error) as api_backend, patch.object(monitor, "spotify_get_playlist_info_web", return_value=expected) as web_backend:
            result = monitor.spotify_get_playlist_info("restricted-token", "spotify:playlist:web123", True)

        self.assertEqual(result, expected)
        self.assertEqual(result.get("sp_playlist_source"), "web")
        self.assertTrue(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)
        api_backend.assert_called_once()
        web_backend.assert_called_once()

    # Switches to the web backend after a 404 Web API response, like the 403 path
    def test_restricted_404_falls_back_to_web_without_latching(self):
        monitor.SP_APP_CLIENT_ID = "legacy-client"
        monitor.SP_APP_CLIENT_SECRET = "legacy-secret"
        api_error = monitor.PlaylistRestrictedError("404 Not Found for playlist endpoint")
        expected = {"sp_playlist_name": "Web"}

        with patch.object(monitor, "_spotify_get_playlist_info_api", side_effect=api_error) as api_backend, patch.object(monitor, "spotify_get_playlist_info_web", return_value=expected) as web_backend:
            result = monitor.spotify_get_playlist_info("legacy-token", "spotify:playlist:web123", True)

        self.assertEqual(result, expected)
        self.assertEqual(result.get("sp_playlist_source"), "web")
        self.assertFalse(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)
        api_backend.assert_called_once()
        web_backend.assert_called_once()

    # Latches the web backend only after repeated restricted 404 responses, not on the first one
    def test_repeated_restricted_404_latches_after_threshold(self):
        monitor.SP_APP_CLIENT_ID = "legacy-client"
        monitor.SP_APP_CLIENT_SECRET = "legacy-secret"
        api_error = monitor.PlaylistRestrictedError("404 Not Found for playlist endpoint")
        expected = {"sp_playlist_name": "Web"}

        with patch.object(monitor, "_spotify_get_playlist_info_api", side_effect=api_error) as api_backend, patch.object(monitor, "spotify_get_playlist_info_web", return_value=expected) as web_backend:
            for _ in range(monitor.METADATA_API_FAILURE_LATCH_THRESHOLD - 1):
                monitor.spotify_get_playlist_info("legacy-token", "spotify:playlist:web123", True)
            self.assertFalse(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)
            monitor.spotify_get_playlist_info("legacy-token", "spotify:playlist:web123", True)
            self.assertTrue(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)

        self.assertEqual(api_backend.call_count, monitor.METADATA_API_FAILURE_LATCH_THRESHOLD)
        self.assertEqual(web_backend.call_count, monitor.METADATA_API_FAILURE_LATCH_THRESHOLD)

    # Latches the web backend only after repeated non-restricted legacy failures
    def test_non_restricted_failures_latch_after_threshold(self):
        monitor.SP_APP_CLIENT_ID = "legacy-client"
        monitor.SP_APP_CLIENT_SECRET = "legacy-secret"
        api_error = Exception("_spotify_get_playlist_info_api(): oauth_app token is missing")
        expected = {"sp_playlist_name": "Web"}

        with patch.object(monitor, "_spotify_get_playlist_info_api", side_effect=api_error) as api_backend, patch.object(monitor, "spotify_get_playlist_info_web", return_value=expected) as web_backend:
            for _ in range(monitor.METADATA_API_FAILURE_LATCH_THRESHOLD - 1):
                monitor.spotify_get_playlist_info("legacy-token", "spotify:playlist:web123", True)
            self.assertFalse(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)
            monitor.spotify_get_playlist_info("legacy-token", "spotify:playlist:web123", True)
            self.assertTrue(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)

        self.assertEqual(api_backend.call_count, monitor.METADATA_API_FAILURE_LATCH_THRESHOLD)
        self.assertEqual(web_backend.call_count, monitor.METADATA_API_FAILURE_LATCH_THRESHOLD)

    # Resets the consecutive-failure counter after a successful legacy request
    def test_success_resets_failure_counter(self):
        monitor.SP_APP_CLIENT_ID = "legacy-client"
        monitor.SP_APP_CLIENT_SECRET = "legacy-secret"
        expected = {"sp_playlist_name": "Legacy"}
        side_effects = [Exception("network glitch"), expected, Exception("network glitch")]

        with patch.object(monitor, "_spotify_get_playlist_info_api", side_effect=side_effects), patch.object(monitor, "spotify_get_playlist_info_web", return_value={"sp_playlist_name": "Web"}):
            monitor.spotify_get_playlist_info("legacy-token", "spotify:playlist:web123", True)
            monitor.spotify_get_playlist_info("legacy-token", "spotify:playlist:web123", True)
            self.assertEqual(monitor.SP_WEB_PLAYLIST_API_FAILURES, 0)
            monitor.spotify_get_playlist_info("legacy-token", "spotify:playlist:web123", True)

        self.assertFalse(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)
        self.assertEqual(monitor.SP_WEB_PLAYLIST_API_FAILURES, 1)

    # Reports an actionable error instead of KeyError when the token response omits its expiry
    def test_token_refresh_missing_expiry_is_actionable(self):
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {"accessToken": "anonymous-token", "clientId": "web-client"}
        session = Mock()
        session.get.return_value = response
        with patch.object(monitor.req, "Session", return_value=session), patch.object(monitor, "fetch_server_time", return_value=1700000000):
            with self.assertRaises(Exception) as caught:
                monitor.refresh_access_token_from_sp_dc("")
        self.assertNotIsInstance(caught.exception, KeyError)
        self.assertIn("missing expiry", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

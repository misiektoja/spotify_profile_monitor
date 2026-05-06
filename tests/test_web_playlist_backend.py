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
        monitor.WEB_PLAYLIST_REVISION_CACHE.clear()

    # Restores mutable backend state after each test
    def tearDown(self):
        monitor.TOKEN_SOURCE = self.original_token_source
        monitor.SP_APP_CLIENT_ID = self.original_client_id
        monitor.SP_APP_CLIENT_SECRET = self.original_client_secret
        monitor.USER_AGENT = self.original_user_agent
        monitor.SP_CACHED_PLAYLIST_QUERY_HASH = ""
        monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED = False
        monitor.WEB_PLAYLIST_REVISION_CACHE.clear()

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

    # Preserves the legacy Web API path when configured credentials still work
    def test_preserves_working_legacy_api_backend(self):
        monitor.SP_APP_CLIENT_ID = "legacy-client"
        monitor.SP_APP_CLIENT_SECRET = "legacy-secret"
        expected = {"sp_playlist_name": "Legacy"}

        with patch.object(monitor, "_spotify_get_playlist_info_api", return_value=expected) as api_backend, patch.object(monitor, "spotify_get_playlist_info_web") as web_backend:
            result = monitor.spotify_get_playlist_info("legacy-token", "spotify:playlist:legacy123", True)

        self.assertEqual(result, expected)
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
        self.assertTrue(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)
        api_backend.assert_called_once()
        web_backend.assert_called_once()


if __name__ == "__main__":
    unittest.main()

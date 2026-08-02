import unittest
from unittest.mock import mock_open, patch

import spotify_profile_monitor as monitor


# Verifies detailed playlist baselines remain independent across partial polling failures
class PlaylistSnapshotBaselineTests(unittest.TestCase):
    # Advances a successful playlist while retaining an unrelated failed playlist baseline
    def test_partial_failure_advances_successful_playlist_baseline(self):
        playlist_a_uri = "spotify:playlist:a"
        playlist_b_uri = "spotify:playlist:b"
        previous = [{"list_of_tracks": ["old-track"], "tracks_count": 81, "update_date": "2026-07-14T01:21:15", "uri": playlist_a_uri}, {"uri": playlist_b_uri, "tracks_count": 131}]
        successful = [{"list_of_tracks": ["old-track", "new-track-1", "new-track-2", "new-track-3"], "tracks_count": 84, "update_date": "2026-07-14T18:27:16", "uri": playlist_a_uri}]
        current = [{"uri": playlist_a_uri}, {"uri": playlist_b_uri}]

        merged = monitor.merge_playlist_snapshots(previous, successful, current)
        merged_by_uri = {snapshot["uri"]: snapshot for snapshot in merged}

        self.assertEqual(merged_by_uri[playlist_a_uri], successful[0])
        self.assertEqual(merged_by_uri[playlist_b_uri]["tracks_count"], 131)

    # Uses successful snapshots for every playlist when a polling cycle fully succeeds
    def test_full_success_replaces_every_playlist_baseline(self):
        playlist_a_uri = "spotify:playlist:a"
        playlist_b_uri = "spotify:playlist:b"
        previous = [{"uri": playlist_a_uri, "tracks_count": 81}, {"uri": playlist_b_uri, "tracks_count": 131}]
        successful = [{"uri": playlist_a_uri, "tracks_count": 84}, {"uri": playlist_b_uri, "tracks_count": 132}]
        current = [{"uri": playlist_b_uri}, {"uri": playlist_a_uri}]

        merged = monitor.merge_playlist_snapshots(previous, successful, current)

        self.assertEqual([snapshot["uri"] for snapshot in merged], [playlist_b_uri, playlist_a_uri])
        self.assertEqual([snapshot["tracks_count"] for snapshot in merged], [132, 84])

    # Drops a baseline after accepted playlist membership no longer contains its URI
    def test_removed_playlist_is_not_retained(self):
        playlist_a_uri = "spotify:playlist:a"
        playlist_b_uri = "spotify:playlist:b"
        previous = [{"uri": playlist_a_uri, "tracks_count": 81}, {"uri": playlist_b_uri, "tracks_count": 131}]
        successful = [{"uri": playlist_a_uri, "tracks_count": 84}]
        current = [{"uri": playlist_a_uri}]

        merged = monitor.merge_playlist_snapshots(previous, successful, current)

        self.assertEqual(merged, successful)

    # Retains an omitted playlist until the membership change protection accepts its removal
    def test_unconfirmed_playlist_removal_retains_detailed_baseline(self):
        playlist_a_uri = "spotify:playlist:a"
        playlist_b_uri = "spotify:playlist:b"
        previous = [{"uri": playlist_a_uri, "tracks_count": 81}, {"uri": playlist_b_uri, "tracks_count": 131}]
        successful = [{"uri": playlist_a_uri, "tracks_count": 84}]
        accepted_before_confirmation = [{"uri": playlist_a_uri}, {"uri": playlist_b_uri}]
        accepted_after_confirmation = [{"uri": playlist_a_uri}]

        pending_merged = monitor.merge_playlist_snapshots(previous, successful, accepted_before_confirmation)
        confirmed_merged = monitor.merge_playlist_snapshots(pending_merged, successful, accepted_after_confirmation)

        self.assertEqual([snapshot["uri"] for snapshot in pending_merged], [playlist_a_uri, playlist_b_uri])
        self.assertEqual(confirmed_merged, successful)

    # Delays a new detailed baseline until the membership change protection accepts the playlist
    def test_unconfirmed_new_playlist_waits_for_membership_acceptance(self):
        playlist_a_uri = "spotify:playlist:a"
        playlist_c_uri = "spotify:playlist:c"
        previous = [{"uri": playlist_a_uri, "tracks_count": 81}]
        successful = [{"uri": playlist_a_uri, "tracks_count": 84}, {"uri": playlist_c_uri, "tracks_count": 10}]
        accepted_before_confirmation = [{"uri": playlist_a_uri}]
        accepted_after_confirmation = [{"uri": playlist_a_uri}, {"uri": playlist_c_uri}]

        pending_merged = monitor.merge_playlist_snapshots(previous, successful, accepted_before_confirmation)
        confirmed_merged = monitor.merge_playlist_snapshots(pending_merged, successful, accepted_after_confirmation)

        self.assertEqual(pending_merged, [successful[0]])
        self.assertEqual(confirmed_merged, successful)

    # Omits a newly discovered playlist until its first detailed snapshot succeeds
    def test_new_failed_playlist_waits_for_first_successful_snapshot(self):
        playlist_a_uri = "spotify:playlist:a"
        playlist_c_uri = "spotify:playlist:c"
        previous = [{"uri": playlist_a_uri, "tracks_count": 81}]
        successful = [{"uri": playlist_a_uri, "tracks_count": 84}]
        current = [{"uri": playlist_a_uri}, {"uri": playlist_c_uri}]

        merged = monitor.merge_playlist_snapshots(previous, successful, current)

        self.assertEqual(merged, successful)

    # Retains every available old baseline when all current playlist detail requests fail
    def test_complete_detail_failure_retains_current_playlist_baselines(self):
        playlist_a_uri = "spotify:playlist:a"
        playlist_b_uri = "spotify:playlist:b"
        previous = [{"uri": playlist_a_uri, "tracks_count": 81}, {"uri": playlist_b_uri, "tracks_count": 131}]
        current = [{"uri": playlist_b_uri}, {"uri": playlist_a_uri}]

        merged = monitor.merge_playlist_snapshots(previous, [], current)

        self.assertEqual([snapshot["uri"] for snapshot in merged], [playlist_b_uri, playlist_a_uri])
        self.assertEqual([snapshot["tracks_count"] for snapshot in merged], [131, 81])

    # Retains the last numeric like count when a successful snapshot omits it
    def test_missing_likes_retains_previous_numeric_baseline(self):
        playlist_uri = "spotify:playlist:a"
        previous = [{"likes": 4, "tracks_count": 81, "uri": playlist_uri}]
        successful = [{"likes": None, "tracks_count": 81, "uri": playlist_uri}]
        current = [{"uri": playlist_uri}]

        merged = monitor.merge_playlist_snapshots(previous, successful, current)

        self.assertEqual(merged[0]["likes"], 4)
        self.assertIsNone(successful[0]["likes"])

    # Uses current profile metadata when detailed playlist metadata omits likes
    def test_missing_detailed_likes_uses_current_profile_count(self):
        playlist_uri = "spotify:playlist:a"
        current = [{"followers_count": 4, "name": "Playlist A", "owner_name": "Owner", "owner_uri": "spotify:user:owner", "uri": playlist_uri}]
        playlist_data = {"sp_playlist_description": "", "sp_playlist_followers_count": None, "sp_playlist_name": "Playlist A", "sp_playlist_owner": "Owner", "sp_playlist_owner_uri": "spotify:user:owner", "sp_playlist_tracks": [], "sp_playlist_tracks_count": 0, "sp_playlist_tracks_count_before_filtering": 0}
        cache = {playlist_uri: {"followers_count": 3, "status": "ok", "timestamp": monitor.time.time()}}

        with patch.object(monitor, "PLAYLIST_INFO_CACHE", cache), patch.object(monitor, "spotify_get_playlist_info", return_value=playlist_data), patch("builtins.print"):
            successful, error_while_processing = monitor.spotify_process_public_playlists("token", current, True, show_progress=False)

        self.assertFalse(error_while_processing)
        self.assertEqual(successful[0]["likes"], 4)
        self.assertEqual(cache[playlist_uri]["followers_count"], 4)

    # Uses the cached baseline when both detailed and profile metadata omit likes
    def test_missing_all_current_likes_uses_cached_count(self):
        playlist_uri = "spotify:playlist:a"
        current = [{"name": "Playlist A", "owner_name": "Owner", "owner_uri": "spotify:user:owner", "uri": playlist_uri}]
        playlist_data = {"sp_playlist_description": "", "sp_playlist_followers_count": None, "sp_playlist_name": "Playlist A", "sp_playlist_owner": "Owner", "sp_playlist_owner_uri": "spotify:user:owner", "sp_playlist_tracks": [], "sp_playlist_tracks_count": 0, "sp_playlist_tracks_count_before_filtering": 0}
        cache = {playlist_uri: {"followers_count": 4, "status": "ok", "timestamp": monitor.time.time()}}

        with patch.object(monitor, "PLAYLIST_INFO_CACHE", cache), patch.object(monitor, "spotify_get_playlist_info", return_value=playlist_data), patch("builtins.print"):
            successful, error_while_processing = monitor.spotify_process_public_playlists("token", current, True, show_progress=False)

        self.assertFalse(error_while_processing)
        self.assertEqual(successful[0]["likes"], 4)
        self.assertEqual(cache[playlist_uri]["followers_count"], 4)

    # Carries partial processor output into the merge without discarding a failed neighbor
    def test_processor_partial_failure_preserves_per_playlist_state(self):
        playlist_a_uri = "spotify:playlist:a"
        playlist_b_uri = "spotify:playlist:b"
        current = [{"uri": playlist_a_uri, "owner_name": "Owner", "owner_uri": "spotify:user:owner"}, {"uri": playlist_b_uri, "owner_name": "Owner", "owner_uri": "spotify:user:owner"}]
        previous = [{"uri": playlist_a_uri, "tracks_count": 81}, {"uri": playlist_b_uri, "tracks_count": 131}]
        playlist_a_data = {"sp_playlist_description": "", "sp_playlist_followers_count": 1, "sp_playlist_name": "Playlist A", "sp_playlist_owner": "Owner", "sp_playlist_owner_uri": "spotify:user:owner", "sp_playlist_tracks": [{"added_at": "2026-07-14T17:30:18Z", "added_by": {}, "track": {"artists": [{"name": "Artist"}], "duration_ms": 120000, "name": "Track", "uri": "spotify:track:track-a"}}], "sp_playlist_tracks_count": 84, "sp_playlist_tracks_count_before_filtering": 84}

        with patch.object(monitor, "LOCAL_TIMEZONE", "UTC"), patch.object(monitor, "spotify_get_playlist_info", side_effect=[playlist_a_data, RuntimeError("transient failure")]), patch.object(monitor, "spotify_get_user_info") as get_user_info, patch("builtins.print"):
            successful, error_while_processing = monitor.spotify_process_public_playlists("token", current, True, show_progress=False)

        merged = monitor.merge_playlist_snapshots(previous, successful, current)
        merged_by_uri = {snapshot["uri"]: snapshot for snapshot in merged}

        self.assertTrue(error_while_processing)
        self.assertEqual(merged_by_uri[playlist_a_uri]["tracks_count"], 84)
        self.assertEqual(merged_by_uri[playlist_b_uri]["tracks_count"], 131)
        get_user_info.assert_not_called()


# Verifies playlist membership changes are detected and described independently of count changes
class PlaylistMembershipChangeTests(unittest.TestCase):
    # Detects a removed and added playlist when the total count stays unchanged
    def test_same_count_uri_swap_is_a_change(self):
        previous = [{"uri": "spotify:playlist:a"}, {"uri": "spotify:playlist:b"}]
        current = [{"uri": "spotify:playlist:a"}, {"uri": "spotify:playlist:c"}]

        self.assertTrue(monitor.playlist_collection_changed(current, previous, 2, 2))

    # Ignores playlist reordering when URI membership and count stay unchanged
    def test_same_membership_in_different_order_is_not_a_change(self):
        previous = [{"uri": "spotify:playlist:a"}, {"uri": "spotify:playlist:b"}]
        current = [{"uri": "spotify:playlist:b"}, {"uri": "spotify:playlist:a"}]

        self.assertFalse(monitor.playlist_collection_changed(current, previous, 2, 2))

    # Preserves existing count-change detection even when URI sets happen to match
    def test_count_change_is_still_a_change(self):
        playlists = [{"uri": "spotify:playlist:a"}]

        self.assertTrue(monitor.playlist_collection_changed(playlists, playlists, 2, 1))

    # Uses membership wording for console and email output after a same-count swap
    def test_same_count_swap_uses_membership_change_wording(self):
        previous_uri = "spotify:playlist:previous"
        current_uri = "spotify:playlist:current"
        previous = [{"uri": previous_uri, "name": "Previous Playlist", "owner_uri": "spotify:user:owner", "followers_count": 2}]
        current = [{"uri": current_uri, "name": "Current Playlist", "owner_uri": "spotify:user:owner", "followers_count": 3}]
        cache = {previous_uri: {"status": "ok", "name": "Previous Playlist", "followers_count": 2, "timestamp": monitor.time.time()}, current_uri: {"status": "ok", "name": "Current Playlist", "followers_count": 3, "timestamp": monitor.time.time()}}
        state_file = mock_open()

        with patch.object(monitor, "LOCAL_TIMEZONE", "UTC"), patch.object(monitor, "GLITCH_CACHE", {}), patch.object(monitor, "PLAYLIST_INFO_CACHE", cache), patch("builtins.open", state_file), patch("builtins.print") as print_output, patch.object(monitor, "send_email") as send_email:
            result = monitor.spotify_print_changed_followers_followings_playlists("user", current, previous, 1, 1, "Playlists", "for", "Added playlists to profile", "Added Playlist", "Removed playlists from profile", "Removed Playlist", "state.json", None, True, True)

        subject, body, body_html, _ = send_email.call_args[0]
        self.assertFalse(result)
        state_file.assert_called_once_with("state.json", "w", encoding="utf-8")
        send_email.assert_called_once()
        self.assertTrue(any("Playlists changed for user user while the total remained 1" in str(call) for call in print_output.call_args_list))
        self.assertIn("playlists have changed! (total remains 1)", subject)
        self.assertIn("Playlists changed for user user while the total remained 1", body)
        self.assertIn("while the total remained <b>1</b>", body_html)
        self.assertNotIn("number changed", body)

    # Retains the existing number-change wording when the playlist total changes
    def test_count_change_keeps_number_change_wording(self):
        existing_uri = "spotify:playlist:existing"
        added_uri = "spotify:playlist:added"
        previous = [{"uri": existing_uri, "name": "Existing Playlist", "owner_uri": "spotify:user:owner", "followers_count": 2}]
        current = previous + [{"uri": added_uri, "name": "Added Playlist", "owner_uri": "spotify:user:owner", "followers_count": 3}]
        cache = {added_uri: {"status": "ok", "name": "Added Playlist", "followers_count": 3, "timestamp": monitor.time.time()}}

        with patch.object(monitor, "LOCAL_TIMEZONE", "UTC"), patch.object(monitor, "GLITCH_CACHE", {}), patch.object(monitor, "PLAYLIST_INFO_CACHE", cache), patch("builtins.open", mock_open()), patch("builtins.print"), patch.object(monitor, "send_email") as send_email:
            result = monitor.spotify_print_changed_followers_followings_playlists("user", current, previous, 2, 1, "Playlists", "for", "Added playlists to profile", "Added Playlist", "Removed playlists from profile", "Removed Playlist", "state.json", None, True, True)

        subject, body, _, _ = send_email.call_args[0]
        self.assertFalse(result)
        send_email.assert_called_once()
        self.assertIn("playlists number has changed! (+1, 1 -> 2)", subject)
        self.assertIn("Playlists number changed for user user from 1 to 2 (+1)", body)
        self.assertNotIn("total remained", body)


# Verifies unavailable playlist like counts do not produce false changes
class PlaylistLikesChangeTests(unittest.TestCase):
    # Detects a real numeric playlist like count change
    def test_numeric_likes_change_is_detected(self):
        self.assertTrue(monitor.playlist_likes_changed(4, 5))

    # Ignores a temporarily unavailable current playlist like count
    def test_likes_becoming_unavailable_is_ignored(self):
        self.assertFalse(monitor.playlist_likes_changed(4, None))

    # Ignores availability recovery without a numeric comparison baseline
    def test_likes_becoming_available_is_ignored(self):
        self.assertFalse(monitor.playlist_likes_changed(None, 4))


if __name__ == "__main__":
    unittest.main()

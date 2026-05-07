import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()

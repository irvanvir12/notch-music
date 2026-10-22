import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from notch_music import search_tracks, track_details, Notch


class QueueSearchTests(unittest.TestCase):
    def setUp(self):
        self.paths = [Path('/music/001.flac'), Path('/music/Ada Band - Manusia Bodoh.flac'),
                      Path('/music/Other - Song.flac')]
        self.metadata = {self.paths[0]: {'title': 'Hati Yang Kau Sakiti', 'artist': 'Rossa'}}

    def test_embedded_title_and_artist_without_matching_filename(self):
        self.assertEqual(search_tracks(self.paths, 'rossa hati', self.metadata), [(0, self.paths[0])])

    def test_tokens_match_regardless_of_order_case_and_punctuation(self):
        self.assertEqual(search_tracks(self.paths, 'BODOH ada-band', {}), [(1, self.paths[1])])

    def test_all_tracks_are_searched_beyond_visible_first_100(self):
        queue = [Path(f'/music/track-{i}.flac') for i in range(150)]
        self.assertEqual(search_tracks(queue, 'track 149', {}), [(149, queue[149])])

    def test_empty_restores_queue_and_no_match_returns_empty(self):
        self.assertEqual(search_tracks(self.paths, '  ', {}), list(enumerate(self.paths)))
        self.assertEqual(search_tracks(self.paths, 'not-found-anywhere', {}), [])

    def test_unicode_and_accents(self):
        self.assertEqual(search_tracks([Path('Beyoncé - Halo.flac')], 'beyonce', {})[0][0], 0)
        self.assertTrue(search_tracks([Path('伊織 - キミがいれば.flac')], 'キミがいれば', {}))

    def test_enter_plays_original_queue_index(self):
        state = SimpleNamespace(queue=self.paths, queue_metadata=self.metadata, load=Mock())
        entry = Mock()
        entry.get_text.return_value = 'manusia bodoh'
        Notch.activate_search_result(state, entry)
        state.load.assert_called_once_with(1)

    def test_track_labels_use_the_same_metadata_as_search(self):
        self.assertEqual(track_details(self.paths[0], self.metadata[self.paths[0]]),
                         ('Hati Yang Kau Sakiti', 'Rossa'))


if __name__ == '__main__':
    unittest.main()

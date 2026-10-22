import tempfile
import unittest
from pathlib import Path
from selection import resolve_selection
from notch_music import Notch


class SelectionTests(unittest.TestCase):
    def test_explicit_files_take_priority_over_folder_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            song = Path(folder) / 'one.flac'
            song.touch()
            self.assertEqual(resolve_selection([str(song)], folder), ([song], []))

    def test_no_selection_uses_open_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(resolve_selection([], folder), ([], [Path(folder)]))

    def test_selected_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(resolve_selection([folder], '/tmp'), ([], [Path(folder)]))

    def test_shuffle_visits_other_tracks_before_repeating(self):
        class Player:
            queue = ['a', 'b', 'c', 'd']
            index = 0
            shuffle = True
            shuffle_remaining = [3, 2, 1]
            history = []
            def load(self, index):
                self.index = index
        player = Player()
        visited = []
        for _ in range(3):
            Notch.step(player, 1)
            visited.append(player.index)
        self.assertEqual(set(visited), {1, 2, 3})
        Notch.step(player, -1)
        self.assertEqual(player.index, 2)


if __name__ == '__main__':
    unittest.main()

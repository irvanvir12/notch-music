import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from playlists import FORMAT, load_playlist, save_playlist
from notch_music import Notch


class PlaylistTests(unittest.TestCase):
    def test_round_trip_preserves_name_order_duplicates_and_missing_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            song = root / 'Musik ü.flac'
            song.write_bytes(b'file')
            missing = root / 'dipindahkan.wav'
            filename = root / 'Favorit.notchplaylist'
            save_playlist(filename, 'Favorit saya', [song, missing, song])
            name, tracks = load_playlist(filename)
            self.assertEqual(name, 'Favorit saya')
            self.assertEqual(tracks, [song, missing, song])
            self.assertFalse(missing.exists())
            self.assertEqual(json.loads(filename.read_text(encoding='utf-8'))['tracks'], list(map(str, tracks)))

    def test_empty_playlist_can_be_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / 'Empty.notchplaylist'
            save_playlist(filename, 'Kosong', [])
            self.assertEqual(load_playlist(filename), ('Kosong', []))

    def test_rejects_corrupt_documents_versions_and_relative_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / 'Bad.notchplaylist'
            for document in ('broken json', [], {'format': FORMAT, 'version': 2},
                             {'format': FORMAT, 'version': 1, 'name': 'Test', 'tracks': ['relative.flac']},
                             {'format': FORMAT, 'version': 1, 'name': 'Test', 'tracks': [None]}):
                filename.write_text(document if isinstance(document, str) else json.dumps(document))
                with self.subTest(document=document), self.assertRaises(ValueError):
                    load_playlist(filename)

    def test_windows_absolute_paths_survive_even_on_another_os(self):
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / 'Windows.notchplaylist'
            original = r'C:\Users\Someone\Music\Song.flac'
            save_playlist(filename, 'Windows', [original])
            self.assertEqual(str(load_playlist(filename)[1][0]), str(Path(original)))

    def test_failed_replace_preserves_existing_playlist_and_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            filename = root / 'Keep.notchplaylist'
            save_playlist(filename, 'Original', [])
            original = filename.read_bytes()
            with patch('playlists.os.replace', side_effect=PermissionError('Read only')):
                with self.assertRaises(PermissionError):
                    save_playlist(filename, 'Changed', [])
            self.assertEqual(filename.read_bytes(), original)
            self.assertEqual(len(list(root.iterdir())), 1)
            self.assertTrue(filename.is_file())

    def test_missing_audio_reports_original_path(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Missing.flac'
            state = SimpleNamespace(report_problem=Mock())
            self.assertFalse(Notch.check_track_file(state, path))
            text = state.report_problem.call_args.args[0]
            self.assertIn('File tidak ditemukan', text)
            self.assertIn(str(path), text)

    def test_missing_audio_does_not_interrupt_current_playback(self):
        state = SimpleNamespace(queue=[Path('/missing.flac')], check_track_file=Mock(return_value=False),
                                player=Mock(), index=3, playing=True)
        self.assertFalse(Notch.load(state, 0))
        state.player.set_state.assert_not_called()
        self.assertEqual(state.index, 3)
        self.assertTrue(state.playing)

    def test_rejects_blank_names(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                save_playlist(Path(folder) / 'Blank.notchplaylist', '  ', [])

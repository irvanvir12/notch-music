from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from gi.repository import GLib
from mpris import MprisService, PLAYER


def service():
    app = SimpleNamespace(queue=[Path.cwd() / 'one.wav', Path.cwd() / 'two.wav'], index=0,
                          playing=True, duration=120, shuffle=False, repeat_mode=0,
                          title=SimpleNamespace(get_text=lambda: 'One'),
                          artist=SimpleNamespace(get_text=lambda: 'Artist'),
                          volume=SimpleNamespace(get_value=lambda: .3, set_value=Mock()),
                          player=Mock(), load=Mock(), seek_changed=Mock(), stop_at_end=Mock(), open_files=Mock())
    app.player.query_position.return_value = (True, 5000000000)

    def toggle():
        app.playing = not app.playing

    def step(direction):
        app.index = (app.index + direction) % len(app.queue)
        app.playing = True

    def repeat():
        app.repeat_mode = (app.repeat_mode + 1) % 3

    app.toggle = Mock(side_effect=toggle)
    app.step = Mock(side_effect=step)
    app.toggle_repeat = Mock(side_effect=repeat)
    app.toggle_shuffle = Mock()
    result = MprisService.__new__(MprisService)
    result.app, result.connection = app, None
    result.stopped, result.previous = False, {}
    return result


class MprisTests(unittest.TestCase):
    def test_headset_play_pause_and_track_buttons(self):
        media = service()
        media.dispatch(PLAYER, 'PlayPause', ())
        self.assertFalse(media.app.playing)
        media.dispatch(PLAYER, 'Next', ())
        self.assertEqual(media.app.index, 1)
        self.assertFalse(media.app.playing)
        media.dispatch(PLAYER, 'Previous', ())
        self.assertEqual(media.app.index, 0)
        self.assertFalse(media.app.playing)
        media.dispatch(PLAYER, 'Play', ())
        self.assertTrue(media.app.playing)

    def test_pause_and_play_are_idempotent(self):
        media = service()
        media.dispatch(PLAYER, 'Pause', ())
        media.dispatch(PLAYER, 'Pause', ())
        self.assertFalse(media.app.playing)
        media.app.toggle.assert_called_once()
        media.dispatch(PLAYER, 'Play', ())
        media.dispatch(PLAYER, 'Play', ())
        self.assertTrue(media.app.playing)
        self.assertEqual(media.app.toggle.call_count, 2)

    def test_empty_queue_media_button_does_not_open_browse(self):
        media = service()
        media.app.queue = []
        media.app.index = -1
        media.app.playing = False
        for method in ('PlayPause', 'Next', 'Previous', 'Play'):
            media.dispatch(PLAYER, method, ())
        media.app.open_files.assert_not_called()
        media.app.toggle.assert_not_called()
        self.assertEqual(media.properties()['PlaybackStatus'].unpack(), 'Stopped')

    def test_metadata_and_position_use_mpris_units(self):
        media = service()
        metadata = media.metadata()
        self.assertEqual(metadata['xesam:title'].unpack(), 'One')
        self.assertEqual(metadata['mpris:length'].unpack(), 120000000)
        self.assertEqual(media.position(), 5000000)

    def test_seek_ignores_stale_track_ids(self):
        media = service()
        media.dispatch(PLAYER, 'SetPosition', ('/stale', 2000000))
        media.app.seek_changed.assert_not_called()
        media.dispatch(PLAYER, 'SetPosition', (media.metadata()['mpris:trackid'].unpack(), 2000000))
        media.app.seek_changed.assert_called_once_with(None, None, 2)

    def test_desktop_volume_and_repeat_controls(self):
        media = service()
        self.assertTrue(media.on_set(None, None, None, PLAYER, 'Volume', GLib.Variant('d', .6)))
        media.app.volume.set_value.assert_called_once_with(.6)
        self.assertTrue(media.on_set(None, None, None, PLAYER, 'LoopStatus', GLib.Variant('s', 'Playlist')))
        self.assertEqual(media.app.repeat_mode, 2)
        self.assertFalse(media.on_set(None, None, None, PLAYER, 'Rate', GLib.Variant('d', 2)))

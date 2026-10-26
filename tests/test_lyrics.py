import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from notch_music import Notch


class LyricsTests(unittest.TestCase):
    def state(self):
        return SimpleNamespace(theme='dark', lyrics_enabled=True, docked=False, dock_autohide=False,
                               lyrics=Mock(), peek_lyrics=Mock(), plain_lyrics=[],
                               lyric_lines=[(1.0, 'First & <line>'), (3.0, 'Second'), (5.0, 'Third')])

    def test_before_start_has_no_highlight(self):
        state = self.state()
        Notch.update_lyrics(state, .9)
        self.assertNotIn('#ff4c65', state.lyrics.set_markup.call_args.args[0])

    def test_timestamp_highlights_current_and_escapes_markup(self):
        state = self.state()
        Notch.update_lyrics(state, 1.0)
        markup = state.lyrics.set_markup.call_args.args[0]
        self.assertIn('weight="bold">First &amp; &lt;line&gt;', markup)
        self.assertNotIn('foreground=', markup)
        self.assertNotIn('Second', markup)
        self.assertNotIn('\n', markup)
        self.assertEqual(state.peek_lyrics.set_markup.call_args.args[0], markup)

    def test_hidden_notch_updates_lyrics_when_panel_is_off(self):
        state = self.state()
        state.lyrics_enabled = False
        state.docked = True
        state.dock_autohide = True
        Notch.update_lyrics(state, 3.2)
        self.assertIn('Second', state.peek_lyrics.set_markup.call_args.args[0])

    def test_seek_updates_highlight_in_both_directions(self):
        state = self.state()
        for seconds, current in [(3.0, 'Second'), (5.2, 'Third'), (1.5, 'First &amp; &lt;line&gt;')]:
            Notch.update_lyrics(state, seconds)
            self.assertIn(f'weight="bold">{current}</span>', state.lyrics.set_markup.call_args.args[0])

    def test_expanded_lyrics_drop_elapsed_lines_and_follow_seek(self):
        state = self.state()
        state.lyric_context = Mock()
        state.player_column = Mock()
        state.player_column.get_allocated_height.return_value = 300
        for seconds, current, absent in [(3.2, 'Second', 'First'), (1.2, 'First &amp; &lt;line&gt;', None)]:
            state.lyric_position = seconds
            Notch.update_lyric_context(state)
            markup = state.lyric_context.set_markup.call_args.args[0]
            self.assertIn(f'<b>{current}</b>', markup)
            self.assertIn('Third', markup)
            if absent:
                self.assertNotIn(absent, markup)

    def test_expanded_lyrics_without_timestamps_use_compact_text(self):
        state = self.state()
        state.lyric_lines = []
        state.lyric_context = Mock()
        state.lyrics.get_text.return_value = 'No timed lyrics'
        Notch.update_lyric_context(state)
        state.lyric_context.set_text.assert_called_once_with('No timed lyrics')


if __name__ == '__main__':
    unittest.main()

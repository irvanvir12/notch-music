import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from notch_music import Notch


class LyricsTests(unittest.TestCase):
    def state(self):
        return SimpleNamespace(theme='dark', lyrics_enabled=True, lyrics=Mock(), plain_lyrics=[],
                               lyric_lines=[(1.0, 'First & <line>'), (3.0, 'Second'), (5.0, 'Third')])

    def test_before_start_has_no_highlight(self):
        state = self.state()
        Notch.update_lyrics(state, .9)
        self.assertNotIn('#ff4c65', state.lyrics.set_markup.call_args.args[0])

    def test_timestamp_highlights_current_and_escapes_markup(self):
        state = self.state()
        Notch.update_lyrics(state, 1.0)
        markup = state.lyrics.set_markup.call_args.args[0]
        self.assertIn('foreground="#ff4c65" weight="bold">First &amp; &lt;line&gt;', markup)
        self.assertNotIn('Second', markup)
        self.assertNotIn('\n', markup)

    def test_seek_updates_highlight_in_both_directions(self):
        state = self.state()
        for seconds, current in [(3.0, 'Second'), (5.2, 'Third'), (1.5, 'First &amp; &lt;line&gt;')]:
            Notch.update_lyrics(state, seconds)
            self.assertIn(f'weight="bold">{current}</span>', state.lyrics.set_markup.call_args.args[0])


if __name__ == '__main__':
    unittest.main()

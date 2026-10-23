import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from gi.repository import Gtk
from notch_music import CSS, Notch
from themes import THEMES, theme_css


class ThemeTests(unittest.TestCase):
    def test_all_stylesheets_parse(self):
        for name in THEMES:
            provider = Gtk.CssProvider()
            errors = []
            provider.connect('parsing-error', lambda provider, section, error: errors.append(error))
            provider.load_from_data(theme_css(CSS, name))
            self.assertEqual(errors, [])

    def test_blur_has_transparency(self):
        self.assertLess(THEMES['blur']['surface'][3], 1)
        self.assertIn(b'background: rgba(16, 17, 22, 0.62)', theme_css(CSS, 'blur'))

    def test_light_changes_text_and_surface(self):
        css = theme_css(CSS, 'light')
        self.assertIn(b'background: #f5f6fa', css)
        self.assertIn(b'color: #242735', css)

    def test_theme_selection_is_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            state = SimpleNamespace(theme='dark', css_provider=Mock(), queue_draw=Mock(),
                                    player=Mock(), lyric_lines=[], plain_lyrics=[],
                                    update_theme_icon=Mock(), sync_menu_state=Mock(), settings_path=Path(folder) / 'config' / 'settings.json')
            state.player.query_position.return_value = (False, 0)
            Notch.set_theme(state, 'light')
            self.assertEqual(json.loads(state.settings_path.read_text()), {'theme': 'light'})
            self.assertEqual(state.theme, 'light')


if __name__ == '__main__':
    unittest.main()

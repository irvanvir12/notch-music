import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, GLib
from selection import prepare_file_selection


class FakeChooser:
    def __init__(self):
        self.handlers = {}
        self.files = ['automatic.flac']
        self.button = Mock()
    def connect(self, signal, callback):
        self.handlers[signal] = callback
    def unselect_all(self):
        self.files = []
        self.handlers['selection-changed'](self)
    def get_filenames(self):
        return self.files
    def get_visible(self):
        return True
    def get_widget_for_response(self, response):
        return self.button
    def get_focus(self):
        return None


class SelectionGuardTests(unittest.TestCase):
    def setUp(self):
        self.chooser = FakeChooser()
        self.selected = prepare_file_selection(self.chooser)

    def reset_folder(self, signal='current-folder-changed'):
        with patch.object(GLib, 'idle_add', side_effect=lambda callback: callback()):
            self.chooser.handlers[signal](self.chooser)

    def test_map_and_automatic_first_row_leave_no_selection(self):
        self.reset_folder('map')
        self.assertEqual(self.selected(), [])
        self.chooser.files = ['automatic.flac']
        self.chooser.handlers['selection-changed'](self.chooser)
        self.assertEqual(self.chooser.files, [])

    def test_explicit_ctrl_a_is_preserved(self):
        event = SimpleNamespace(keyval=Gdk.KEY_a, state=Gdk.ModifierType.CONTROL_MASK)
        self.chooser.handlers['key-press-event'](self.chooser, event)
        self.chooser.files = ['a.flac', 'b.flac']
        self.chooser.handlers['selection-changed'](self.chooser)
        self.assertEqual(self.selected(), ['a.flac', 'b.flac'])

    def test_folder_change_resets_previous_user_selection(self):
        self.test_explicit_ctrl_a_is_preserved()
        self.reset_folder()
        self.assertEqual(self.selected(), [])
        self.chooser.button.grab_focus.assert_called_once()


if __name__ == '__main__':
    unittest.main()

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from notch_music import Notch, Gdk


def dock():
    return SimpleNamespace(
        docked=True, dock_autohide=False, autohide_wait_exit=False,
        hover_left_at=None, pointer_inside=False, drag_origin=None,
        browse_open=False, layer_shell=True, get_mapped=Mock(return_value=True),
        body_revealer=Mock(), player_menu=Mock(), update_dock_handle=Mock())


class NotchVisibilityTests(unittest.TestCase):
    def test_autohide_waits_for_exit_then_follows_pointer(self):
        state = dock()
        state.player_menu.get_mapped.return_value = False
        state.pointer_inside = True
        Notch.toggle_dock_autohide(state)
        self.assertTrue(state.dock_autohide)
        state.body_revealer.set_reveal_child.assert_called_once_with(False)
        Notch.poll_notch_hover(state)
        state.body_revealer.set_reveal_child.assert_called_once_with(False)
        state.pointer_inside = False
        Notch.poll_notch_hover(state)
        self.assertFalse(state.autohide_wait_exit)
        state.pointer_inside = True
        Notch.poll_notch_hover(state)
        state.body_revealer.set_reveal_child.assert_called_with(True)
        for _ in range(3):
            state.pointer_inside = False
            Notch.poll_notch_hover(state)
            state.body_revealer.set_reveal_child.assert_called_with(False)
            self.assertTrue(state.dock_autohide)
            state.pointer_inside = True
            Notch.poll_notch_hover(state)
            state.body_revealer.set_reveal_child.assert_called_with(True)
            self.assertTrue(state.dock_autohide)

    def test_menu_and_file_dialog_hold_notch_open(self):
        for menu, browse in ((True, False), (False, True)):
            with self.subTest(menu=menu, browse=browse):
                state = dock()
                state.dock_autohide = True
                state.player_menu.get_mapped.return_value = menu
                state.browse_open = browse
                Notch.poll_notch_hover(state)
                state.body_revealer.set_reveal_child.assert_called_once_with(True)
                self.assertIsNone(state.hover_left_at)

    def test_xwayland_stale_coordinates_do_not_override_pointer_exit(self):
        state = dock()
        state.dock_autohide = True
        state.layer_shell = None
        state.pointer_inside = False
        state.player_menu.get_mapped.return_value = False
        window = Mock()
        window.get_device_position.return_value = (None, 20, 20, 0)
        window.get_visible_region.return_value.contains_point.return_value = True
        state.get_window = Mock(return_value=window)
        state.get_display = Mock()
        state.notch = Mock()
        state.notch.get_allocation.return_value = SimpleNamespace(x=0, width=350)
        Notch.poll_notch_hover(state)
        state.body_revealer.set_reveal_child.assert_called_once_with(False)

    def test_child_crossings_do_not_change_top_level_pointer_state(self):
        window = Mock()
        state = SimpleNamespace(pointer_inside=True, get_window=Mock(return_value=window))
        child_leave = SimpleNamespace(window=Mock(), detail=Gdk.NotifyType.NONLINEAR)
        Notch.notch_pointer_crossing(state, None, child_leave, False)
        self.assertTrue(state.pointer_inside)
        actual_leave = SimpleNamespace(window=window, detail=Gdk.NotifyType.NONLINEAR)
        Notch.notch_pointer_crossing(state, None, actual_leave, False)
        self.assertFalse(state.pointer_inside)

    def test_second_click_pins_notch_open(self):
        state = dock()
        state.dock_autohide = True
        Notch.toggle_dock_autohide(state)
        self.assertFalse(state.dock_autohide)
        state.body_revealer.set_reveal_child.assert_called_once_with(True)
        Notch.poll_notch_hover(state)
        state.body_revealer.set_reveal_child.assert_called_once_with(True)

    def test_minimize_is_restorable_and_does_not_stop_music(self):
        state = SimpleNamespace(docked=False, layer_shell=None, playing=True,
                                set_type_hint=Mock(), set_skip_taskbar_hint=Mock(),
                                set_skip_pager_hint=Mock(), iconify=Mock())
        Notch.minimize_player(state)
        state.set_type_hint.assert_called_once_with(Gdk.WindowTypeHint.NORMAL)
        state.set_skip_taskbar_hint.assert_called_once_with(False)
        state.iconify.assert_called_once()
        self.assertTrue(state.playing)
        state.docked = True
        Notch.minimize_player(state)
        state.iconify.assert_called_once()

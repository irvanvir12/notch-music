import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from notch_music import Notch, Gdk, LYRIC_STRIP_WIDTH, PLAYER_NORMAL_WIDTH


def dock():
    state = SimpleNamespace(
        docked=True, dock_autohide=False, autohide_wait_exit=False,
        hover_left_at=None, pointer_inside=False, drag_origin=None,
        browse_open=False, layer_shell=True, get_mapped=Mock(return_value=True),
        body_revealer=Mock(), peek_revealer=Mock(), dock_handle=Mock(), player=Mock(),
        player_menu=Mock(), update_dock_handle=Mock())
    state.player.query_position.return_value = (False, 0)
    state.update_lyrics = Mock()
    state.set_autohide_open = lambda opened: Notch.set_autohide_open(state, opened)
    return state


class NotchVisibilityTests(unittest.TestCase):
    def test_normal_notch_is_three_quarters_of_lyric_width(self):
        self.assertEqual(PLAYER_NORMAL_WIDTH, round(LYRIC_STRIP_WIDTH * .75))

    def test_windows_does_not_create_monitor_wide_bezel(self):
        state = SimpleNamespace(bezel_bar=None)
        with patch('notch_music.sys.platform', 'win32'), patch('notch_music.Gtk.Window') as create:
            Notch.show_bezel_bar(state, SimpleNamespace(width=1920, x=0, y=0))
        create.assert_not_called()
        self.assertIsNone(state.bezel_bar)

    def test_snap_finishes_with_or_without_bezel_window(self):
        for bar in (None, Mock()):
            with self.subTest(bezel=bar):
                state = SimpleNamespace(
                    floating_center=960, floating_y=24, docked=False,
                    bezel_bar=bar, place_floating=Mock(), show_bezel_bar=Mock(),
                    set_type_hint=Mock(), set_skip_taskbar_hint=Mock(),
                    update_dock_handle=Mock(), update_panel_layout=Mock(),
                    notch=Mock(), queue_draw=Mock(), add_tick_callback=Mock(return_value=1))
                with patch('notch_music.GLib.get_monotonic_time', return_value=1000000):
                    Notch.animate_snap(state, SimpleNamespace(x=0, y=0, width=1920))
                frame = state.add_tick_callback.call_args.args[0]
                self.assertFalse(frame(state, SimpleNamespace(get_frame_time=lambda: 1400000)))
                self.assertTrue(state.docked)
                self.assertEqual(state.floating_y, 0)
                self.assertEqual(state.connection_progress, 1)
                self.assertIsNone(state.snap_tick)
                if bar is not None:
                    bar.set_opacity.assert_called_once_with(1)

    def test_autohide_waits_for_exit_then_follows_pointer(self):
        state = dock()
        state.player_menu.get_mapped.return_value = False
        state.pointer_inside = True
        Notch.toggle_dock_autohide(state)
        self.assertTrue(state.dock_autohide)
        state.body_revealer.set_reveal_child.assert_called_once_with(False)
        state.peek_revealer.set_reveal_child.assert_called_once_with(True)
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
            state.peek_revealer.set_reveal_child.assert_called_with(True)
            self.assertTrue(state.dock_autohide)
            state.pointer_inside = True
            Notch.poll_notch_hover(state)
            state.body_revealer.set_reveal_child.assert_called_with(True)
            state.peek_revealer.set_reveal_child.assert_called_with(False)
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
                state.peek_revealer.set_reveal_child.assert_called_once_with(False)
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
        state.peek_revealer.set_reveal_child.assert_called_once_with(True)

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
        state.peek_revealer.set_reveal_child.assert_called_once_with(False)
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

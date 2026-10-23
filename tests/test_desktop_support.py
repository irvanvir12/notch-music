import unittest
from unittest.mock import Mock
from types import SimpleNamespace
from desktop_support import choose_backend, anchor_window, window_shape


class DesktopSupportTests(unittest.TestCase):
    def test_windows_uses_win32_instead_of_x11_or_wayland(self):
        self.assertEqual(choose_backend({}, False, 'win32'), 'win32')
        self.assertEqual(choose_backend({'WAYLAND_DISPLAY': 'wayland-0'}, True, 'win32'), 'win32')
        self.assertEqual(choose_backend({'NOTCH_GDK_BACKEND': 'broadway'}, False, 'win32'), 'broadway')

    def test_windows_shape_clips_floating_corners_but_keeps_docked_shoulders(self):
        floating = window_shape(24, 0, 350, 130, False)
        self.assertFalse(floating.contains_point(0, 10))
        self.assertFalse(floating.contains_point(24, 0))
        self.assertTrue(floating.contains_point(48, 0))
        self.assertTrue(floating.contains_point(24, 40))
        docked = window_shape(24, 0, 350, 130, True)
        self.assertTrue(docked.contains_point(0, 0))
        self.assertTrue(docked.contains_point(24, 0))
        self.assertTrue(docked.contains_point(23, 10))
        self.assertFalse(docked.contains_point(24, 129))

    def test_cachy_kde_prefers_native_wayland_when_layer_shell_available(self):
        env = {'XDG_CURRENT_DESKTOP': 'KDE', 'WAYLAND_DISPLAY': 'wayland-0'}
        self.assertEqual(choose_backend(env, True), 'wayland,x11')
        self.assertEqual(choose_backend(env, False), 'x11')

    def test_gnome_retains_xwayland(self):
        self.assertEqual(choose_backend({'XDG_CURRENT_DESKTOP': 'zorin:GNOME', 'WAYLAND_DISPLAY': 'wayland-0'}, True), 'x11')

    def test_x11_and_user_overrides(self):
        self.assertEqual(choose_backend({'XDG_SESSION_TYPE': 'x11'}, True), 'x11')
        self.assertEqual(choose_backend({'GDK_BACKEND': 'broadway'}, True), 'broadway')
        self.assertEqual(choose_backend({'NOTCH_GDK_BACKEND': 'wayland', 'GDK_BACKEND': 'x11'}, True), 'wayland')

    def test_wayland_window_anchors_and_does_not_reserve_desktop_space(self):
        layer = Mock()
        layer.Edge = SimpleNamespace(TOP=0, LEFT=1, RIGHT=2)
        window = Mock()
        anchor_window(window, layer)
        layer.init_for_window.assert_called_once_with(window)
        layer.set_exclusive_zone.assert_called_once_with(window, 0)
        self.assertEqual(layer.set_anchor.call_count, 3)
        layer.set_keyboard_mode.assert_called_once_with(window, layer.KeyboardMode.ON_DEMAND)


if __name__ == '__main__':
    unittest.main()

import ctypes
import sys
import unittest
from unittest.mock import Mock

from gi.repository import GLib
from mpris import WindowsMediaKeys


@unittest.skipUnless(sys.platform == 'win32', 'Native Win32 media message tests')
class WindowsMediaKeyTests(unittest.TestCase):
    def start(self):
        service = Mock()
        keys = WindowsMediaKeys(service)
        self.addCleanup(keys.close)
        self.assertTrue(keys.ready.wait(3), 'Media thread did not initialize')
        self.assertEqual(len(keys.registered), len(keys.KEYS), 'Media keys already owned by another app')
        return service, keys

    def test_native_messages_reach_gtk_thread_in_order(self):
        from ctypes import wintypes
        service, keys = self.start()
        post = ctypes.windll.user32.PostThreadMessageW
        post.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        post.restype = wintypes.BOOL
        for identifier in keys.registered:
            self.assertTrue(post(keys.thread_id, keys.WM_HOTKEY, identifier, 0))
        loop = GLib.MainLoop()
        GLib.timeout_add(250, lambda: (loop.quit(), False)[1])
        loop.run()
        self.assertEqual([call.args[1] for call in service.dispatch.call_args_list],
                         list(keys.KEYS.values()))

    def test_shutdown_releases_keys_for_next_instance(self):
        _, first = self.start()
        first.close()
        self.assertFalse(first.thread.is_alive())
        self.start()

    def test_pending_callback_does_nothing_after_shutdown(self):
        service, keys = self.start()
        keys.close()
        self.assertFalse(keys.deliver('PlayPause'))
        service.dispatch.assert_not_called()

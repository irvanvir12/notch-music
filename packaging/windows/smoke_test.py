"""Run on Windows CI against the relocated bundle; never outputs audio."""
from pathlib import Path
import math
import cairo
import ctypes
import struct
import tempfile
import wave

from notch_music import Notch, Gtk, GLib, Gst
from desktop_support import get_layer_shell
from metadata import read_audio_info, format_audio_info


def pump(milliseconds=250):
    loop = GLib.MainLoop()
    GLib.timeout_add(milliseconds, lambda: (loop.quit(), False)[1])
    loop.run()


assert Gtk.init_check()[0], 'No Win32 desktop available'
assert get_layer_shell() is None
with tempfile.TemporaryDirectory(prefix='notch-windows-') as folder:
    path = Path(folder) / 'Audio test ü.wav'
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, 44100, 0, 'NONE', 'not compressed'))
        audio.writeframes(b''.join(struct.pack('<h', int(8000 * math.sin(2 * math.pi * 440 * i / 44100)))
                                  for i in range(44100 * 3)))
    assert format_audio_info(read_audio_info(path)) == 'WAV · 16-bit · 44.1 kHz'
    window = Notch([])
    assert Gtk.Settings.get_default().get_property('gtk-xft-rgba') == 'none'
    assert window.get_screen().get_font_options().get_antialias() == cairo.ANTIALIAS_GRAY
    window.settings_path = Path(folder) / 'settings.json'
    sink = Gst.ElementFactory.make('fakesink')
    sink.set_property('sync', True)
    window.player.set_property('audio-sink', sink)
    assert window.volume.get_value() == .3
    window.show_all()
    window.toggle_lyrics()
    window.add_files([path])
    pump(700)
    assert window.spectrum is not None
    assert window.visualizer_updated > 0
    assert max(window.visualizer_target) > 0
    media = window.mpris.windows
    assert media.ready.wait(3), 'Windows media-key listener did not start'
    assert len(media.registered) == len(media.KEYS), 'Media keys could not be registered'
    play_pause = next(identifier for identifier, method in media.registered.items() if method == 'PlayPause')
    from ctypes import wintypes
    post = ctypes.windll.user32.PostThreadMessageW
    post.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    post.restype = wintypes.BOOL
    assert post(media.thread_id, media.WM_HOTKEY, play_pause, 0)
    pump()
    assert not window.playing, 'Native media message did not pause playback'
    assert post(media.thread_id, media.WM_HOTKEY, play_pause, 0)
    pump()
    assert window.playing, 'Native media message did not resume playback'
    window.show_queue()
    pump()
    assert window.queue_enabled and window.lyrics_enabled
    assert window.drawer.get_parent() is window.player_column
    for theme in ('light', 'blur', 'dark'):
        window.set_theme(theme)
        pump(50)
    window.toggle_mute()
    assert window.volume.get_value() == 0
    window.toggle_mute()
    assert window.volume.get_value() == .3
    original_queue = list(window.queue)
    window.create_playlist()
    assert not window.playlist_tracks and window.queue == original_queue
    window.add_files([path], playlist_target=window.playlist_tracks)
    playlist_file = Path(folder) / 'Favorit ü.notchplaylist'
    assert window.save_playlist_file(playlist_file)
    window.create_playlist()
    assert window.load_playlist_file(playlist_file)
    assert window.playlist_title_label.get_text() == 'Favorit ü'
    assert len(window.playlist_tracks) == 1 and window.playlist_tracks[0].samefile(path)
    assert window.queue == original_queue
    window.close_drawer()
    monitor = window.get_display().get_primary_monitor() or window.get_display().get_monitor(0)
    area = monitor.get_geometry()
    window.animate_snap(area)
    pump(700)
    assert window.docked and window.snap_tick is None
    assert window.bezel_bar is None, 'Windows must not create a monitor-wide bezel window'
    window.player.set_state(Gst.State.NULL)
    window.destroy()
    assert not media.thread.is_alive(), 'Media-key listener did not stop'
print('Relocated Windows bundle: GTK, playback, spectrum, themes, queue, lyrics, mute, docking and media keys OK')

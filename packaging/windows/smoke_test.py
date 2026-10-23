"""Run on Windows CI against the relocated bundle; never outputs audio."""
from pathlib import Path
import math
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
    window.close_drawer()
    window.player.set_state(Gst.State.NULL)
    window.destroy()
print('Relocated Windows bundle: GTK, playback, spectrum, themes, queue, lyrics and mute OK')

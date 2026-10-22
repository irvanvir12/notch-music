"""Headless smoke test of the libraries and audio stack inside the AppImage."""
import os
import sys
import tempfile
import wave
from pathlib import Path
import gi
import cairo
for namespace, version in [('Gtk', '3.0'), ('Gst', '1.0'), ('GdkPixbuf', '2.0')]:
    gi.require_version(namespace, version)
from gi.repository import Gtk, Gst, GdkPixbuf
from notch_music import CSS
from themes import THEMES, theme_css
Gst.init(None)
for name in THEMES:
    provider = Gtk.CssProvider()
    provider.load_from_data(theme_css(CSS, name))
for name in ('playbin', 'flacdec', 'vorbisdec', 'opusdec', 'avdec_mp3', 'autoaudiosink', 'pulsesink'):
    assert Gst.ElementFactory.find(name), f'Missing GStreamer plugin: {name}'
appdir = Path(os.environ['APPDIR'])
assert Path(gi.__file__).is_relative_to(appdir)
assert Path(cairo.__file__).is_relative_to(appdir)
with tempfile.TemporaryDirectory() as folder:
    audio = Path(folder) / 'test.wav'
    with wave.open(str(audio), 'wb') as stream:
        stream.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
        stream.writeframes(b'\0\0' * 800)
    player = Gst.ElementFactory.make('playbin')
    player.set_property('audio-sink', Gst.ElementFactory.make('fakesink'))
    player.set_property('uri', audio.as_uri())
    player.set_state(Gst.State.PLAYING)
    message = player.get_bus().timed_pop_filtered(10 * Gst.SECOND, Gst.MessageType.ERROR | Gst.MessageType.EOS)
    player.set_state(Gst.State.NULL)
    assert message and message.type == Gst.MessageType.EOS, message.parse_error() if message else 'Playback timeout'
if len(sys.argv) > 1:
    from metadata import read_metadata
    meta = read_metadata(sys.argv[1])
    assert meta['picture']
    loader = GdkPixbuf.PixbufLoader()
    loader.write(meta['picture'])
    loader.close()
    assert loader.get_pixbuf()
print('AppImage self-test OK: bundled Python, GTK, themes, audio codecs, playback and cover decoding.')

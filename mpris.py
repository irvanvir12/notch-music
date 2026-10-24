"""Expose Linux desktop/headset media controls on the session D-Bus."""
import hashlib
import os
from pathlib import Path
import sys

from gi.repository import Gio, GLib

PATH = '/org/mpris/MediaPlayer2'
ROOT = 'org.mpris.MediaPlayer2'
PLAYER = ROOT + '.Player'
NO_TRACK = PATH + '/TrackList/NoTrack'
XML = '''<node>
<interface name="org.mpris.MediaPlayer2">
  <method name="Raise"/><method name="Quit"/>
  <property name="CanQuit" type="b" access="read"/>
  <property name="CanRaise" type="b" access="read"/>
  <property name="HasTrackList" type="b" access="read"/>
  <property name="Identity" type="s" access="read"/>
  <property name="DesktopEntry" type="s" access="read"/>
  <property name="SupportedUriSchemes" type="as" access="read"/>
  <property name="SupportedMimeTypes" type="as" access="read"/>
</interface>
<interface name="org.mpris.MediaPlayer2.Player">
  <method name="Next"/><method name="Previous"/><method name="Pause"/>
  <method name="PlayPause"/><method name="Stop"/><method name="Play"/>
  <method name="Seek"><arg name="Offset" type="x" direction="in"/></method>
  <method name="SetPosition"><arg name="TrackId" type="o" direction="in"/><arg name="Position" type="x" direction="in"/></method>
  <method name="OpenUri"><arg name="Uri" type="s" direction="in"/></method>
  <signal name="Seeked"><arg name="Position" type="x"/></signal>
  <property name="PlaybackStatus" type="s" access="read"/>
  <property name="LoopStatus" type="s" access="readwrite"/>
  <property name="Rate" type="d" access="readwrite"/>
  <property name="Shuffle" type="b" access="readwrite"/>
  <property name="Metadata" type="a{sv}" access="read"/>
  <property name="Volume" type="d" access="readwrite"/>
  <property name="Position" type="x" access="read"/>
  <property name="MinimumRate" type="d" access="read"/>
  <property name="MaximumRate" type="d" access="read"/>
  <property name="CanGoNext" type="b" access="read"/>
  <property name="CanGoPrevious" type="b" access="read"/>
  <property name="CanPlay" type="b" access="read"/>
  <property name="CanPause" type="b" access="read"/>
  <property name="CanSeek" type="b" access="read"/>
  <property name="CanControl" type="b" access="read"/>
</interface></node>'''


class MprisService:
    def __init__(self, app):
        self.app = app
        self.connection = None
        self.registrations = []
        self.owner = self.source = None
        self.previous = {}
        self.stopped = False
        self.name = f'{ROOT}.notch_music.instance{os.getpid()}'
        self.windows = WindowsMediaKeys(self) if sys.platform == 'win32' else None
        if not sys.platform.startswith('linux'):
            return
        try:
            self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            for interface in Gio.DBusNodeInfo.new_for_xml(XML).interfaces:
                self.registrations.append(self.connection.register_object(
                    PATH, interface, self.on_method, self.on_get, self.on_set))
            self.owner = Gio.bus_own_name_on_connection(self.connection, self.name,
                                                       Gio.BusNameOwnerFlags.NONE, None, None)
            self.source = GLib.timeout_add(250, self.publish)
        except GLib.Error:
            self.close()

    def metadata(self):
        app = self.app
        if not 0 <= app.index < len(app.queue):
            return {'mpris:trackid': GLib.Variant('o', NO_TRACK)}
        uri = app.queue[app.index].as_uri()
        identifier = hashlib.sha256(uri.encode()).hexdigest()[:24]
        return {
            'mpris:trackid': GLib.Variant('o', f'{PATH}/track/t{identifier}_{app.index}'),
            'mpris:length': GLib.Variant('x', max(0, round(app.duration * 1000000))),
            'xesam:url': GLib.Variant('s', uri),
            'xesam:title': GLib.Variant('s', app.title.get_text()),
            'xesam:artist': GLib.Variant('as', [app.artist.get_text()]),
        }

    def properties(self):
        app = self.app
        loaded = 0 <= app.index < len(app.queue)
        if app.playing:
            self.stopped = False
        status = 'Playing' if app.playing else ('Paused' if loaded and not self.stopped else 'Stopped')
        return {
            'PlaybackStatus': GLib.Variant('s', status),
            'LoopStatus': GLib.Variant('s', ['None', 'Track', 'Playlist'][app.repeat_mode]),
            'Rate': GLib.Variant('d', 1.0),
            'Shuffle': GLib.Variant('b', app.shuffle),
            'Metadata': GLib.Variant('a{sv}', self.metadata()),
            'Volume': GLib.Variant('d', app.volume.get_value()),
            'MinimumRate': GLib.Variant('d', 1.0),
            'MaximumRate': GLib.Variant('d', 1.0),
            'CanGoNext': GLib.Variant('b', bool(app.queue)),
            'CanGoPrevious': GLib.Variant('b', bool(app.queue)),
            'CanPlay': GLib.Variant('b', bool(app.queue)),
            'CanPause': GLib.Variant('b', loaded),
            'CanSeek': GLib.Variant('b', loaded and app.duration > 0),
            'CanControl': GLib.Variant('b', True),
        }

    def position(self):
        from gi.repository import Gst
        ok, value = self.app.player.query_position(Gst.Format.TIME)
        return max(0, value // 1000) if ok else 0

    def on_get(self, connection, sender, path, interface, name):
        if interface == ROOT:
            return {
                'CanQuit': GLib.Variant('b', True), 'CanRaise': GLib.Variant('b', True),
                'HasTrackList': GLib.Variant('b', False), 'Identity': GLib.Variant('s', 'Notch Music'),
                'DesktopEntry': GLib.Variant('s', 'notch-music'),
                'SupportedUriSchemes': GLib.Variant('as', ['file']),
                'SupportedMimeTypes': GLib.Variant('as', ['audio/flac', 'audio/mpeg', 'audio/x-wav', 'audio/ogg', 'audio/mp4']),
            }.get(name)
        if name == 'Position':
            return GLib.Variant('x', self.position())
        return self.properties().get(name)

    def on_set(self, connection, sender, path, interface, name, value):
        app = self.app
        value = value.unpack()
        if interface != PLAYER:
            return False
        if name == 'Volume':
            app.volume.set_value(max(0.0, min(1.0, value)))
        elif name == 'Shuffle':
            if value != app.shuffle:
                app.toggle_shuffle()
        elif name == 'LoopStatus' and value in ('None', 'Track', 'Playlist'):
            target = ('None', 'Track', 'Playlist').index(value)
            while app.repeat_mode != target:
                app.toggle_repeat()
        elif name != 'Rate' or value != 1.0:
            return False
        self.publish()
        return True

    def dispatch(self, interface, method, args):
        app = self.app
        if interface == ROOT:
            if method == 'Quit':
                app.close()
            elif method == 'Raise':
                app.restore_player()
                if app.docked and app.dock_autohide:
                    app.toggle_dock_autohide()
            return
        if method == 'OpenUri':
            filename, host = GLib.filename_from_uri(args[0])
            if host and host != 'localhost':
                raise ValueError('Hanya file lokal yang didukung.')
            from selection import AUDIO
            track = Path(filename)
            if not track.is_file() or track.suffix.lower() not in AUDIO:
                raise ValueError('File musik tidak ditemukan atau format tidak didukung.')
            index = len(app.queue)
            app.add_files([track])
            if app.index != index:
                app.load(index)
            return
        if not app.queue:
            return
        if method in ('Next', 'Previous'):
            playing = app.playing
            app.step(1 if method == 'Next' else -1)
            if not playing and app.playing:
                app.toggle()
        elif method == 'PlayPause':
            self.stopped = False
            app.load(0) if app.index < 0 else app.toggle()
        elif method == 'Play':
            self.stopped = False
            if app.index < 0:
                app.load(0)
            elif not app.playing:
                app.toggle()
        elif method == 'Pause':
            if app.playing:
                app.toggle()
        elif method == 'Stop':
            app.stop_at_end()
            self.stopped = True
        elif method in ('Seek', 'SetPosition') and app.duration > 0:
            if method == 'Seek':
                target = max(0, self.position() + args[0])
                if target > app.duration * 1000000:
                    self.dispatch(PLAYER, 'Next', ())
                    return
            else:
                track_id, target = args
                if track_id != self.metadata()['mpris:trackid'].unpack() or not 0 <= target <= app.duration * 1000000:
                    return
            app.seek_changed(None, None, target / 1000000)
            if self.connection:
                self.connection.emit_signal(None, PATH, PLAYER, 'Seeked', GLib.Variant('(x)', (target,)))

    def on_method(self, connection, sender, path, interface, method, parameters, invocation):
        try:
            self.dispatch(interface, method, parameters.unpack())
            self.publish()
            invocation.return_value(GLib.Variant('()', ()))
        except (GLib.Error, ValueError) as error:
            invocation.return_dbus_error('org.mpris.MediaPlayer2.Error.Failed', str(error))

    def publish(self):
        if self.connection:
            current = self.properties()
            changed = {name: value for name, value in current.items()
                       if name not in self.previous or not value.equal(self.previous[name])}
            if changed:
                self.connection.emit_signal(None, PATH, 'org.freedesktop.DBus.Properties', 'PropertiesChanged',
                                            GLib.Variant('(sa{sv}as)', (PLAYER, changed, [])))
            self.previous = current
        return True

    def close(self):
        if getattr(self, 'windows', None) is not None:
            self.windows.close()
            self.windows = None
        if self.source is not None:
            GLib.source_remove(self.source)
            self.source = None
        if self.owner is not None:
            Gio.bus_unown_name(self.owner)
            self.owner = None
        if self.connection:
            for registration in self.registrations:
                self.connection.unregister_object(registration)
        self.registrations = []
        self.connection = None


class WindowsMediaKeys:
    """Receive Win32 media keys on a private thread; dispatch on GTK's thread.

    RegisterHotKey delivers WM_HOTKEY even when the player is not focused.
    Keep its message queue separate so GTK cannot consume those messages.
    Volume keys remain under Windows' system-volume control.
    """
    KEYS = {0xB3: 'PlayPause', 0xB0: 'Next', 0xB1: 'Previous', 0xB2: 'Stop'}
    WM_HOTKEY = 0x0312

    def __init__(self, service):
        import threading
        self.service = service
        self.stopping = threading.Event()
        self.ready = threading.Event()
        self.registered = {}
        self.thread_id = None
        self.thread = threading.Thread(target=self.listen, name='notch-media-keys', daemon=True)
        self.thread.start()

    def deliver(self, method):
        if not self.stopping.is_set():
            self.service.dispatch(PLAYER, method, ())
        return False

    def listen(self):
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        user32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
        user32.UnregisterHotKey.restype = wintypes.BOOL
        user32.PeekMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                       wintypes.UINT, wintypes.UINT, wintypes.UINT)
        user32.PeekMessageW.restype = wintypes.BOOL
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        self.thread_id = kernel32.GetCurrentThreadId()
        try:
            for offset, (key, method) in enumerate(self.KEYS.items()):
                identifier = 0x4E00 + offset
                if user32.RegisterHotKey(None, identifier, 0x4000, key):  # MOD_NOREPEAT
                    self.registered[identifier] = method
                else:
                    print(f'Notch Music: media key {method} unavailable (Win32 {ctypes.get_last_error()}).',
                          file=sys.stderr)
            self.ready.set()
            message = wintypes.MSG()
            while not self.stopping.is_set():
                while user32.PeekMessageW(ctypes.byref(message), None,
                                         self.WM_HOTKEY, self.WM_HOTKEY, 1):
                    method = self.registered.get(message.wParam)
                    if method is not None and not self.stopping.is_set():
                        GLib.idle_add(self.deliver, method)
                self.stopping.wait(.02)
        finally:
            for identifier in self.registered:
                user32.UnregisterHotKey(None, identifier)
            self.ready.set()

    def close(self):
        self.stopping.set()
        self.thread.join(timeout=2)

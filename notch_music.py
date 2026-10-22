#!/usr/bin/env python3
"""A compact GTK desktop music player. Run through ./run.sh."""
import os
import sys
import threading
import random
import math
import json
import cairo
from pathlib import Path
from metadata import read_metadata, parse_lyrics
from selection import resolve_selection
from themes import THEMES, theme_css
from desktop_support import configure_backend, get_layer_shell, anchor_window

import gi
configure_backend()
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gdk, GLib, Gst, Pango, GdkPixbuf

Gst.init(None)
AUDIO = {'.mp3', '.flac', '.ogg', '.opus', '.wav', '.m4a', '.aac', '.wma'}
CSS = b'''
#notch-window { background-color: transparent; color: #fafafa; }
#bar { background: #08090b; }
#notch { background: #101116; border: 1px solid #292b35; border-top: none; border-radius: 0 0 16px 16px; }
#player { padding: 6px 8px 7px; }
#drawer { padding: 9px; border-top: 1px solid #292b35; }
#drawer-title { font-size: 13px; font-weight: bold; }
#drawer-subtitle { color: #9297a6; font-size: 10px; }
#notch entry { background: #20222c; color: #f3f4f9; border: 1px solid #373a48; border-radius: 14px; padding: 7px 10px; box-shadow: none; }
#notch list, #notch viewport, #notch scrolledwindow { background: transparent; color: #f3f4f9; }
#notch row { padding: 7px; border-radius: 10px; margin: 2px 0; }
#notch row:hover { background: #252833; }
#notch row:selected { background: #303344; }
#notch .current-track { background: #242936; }
#notch .track-title { font-size: 12px; font-weight: bold; }
#notch .track-artist { color: #9297a6; font-size: 10px; }
#notch filechooser, #notch filechooser box, #notch treeview { background-color: #171921; color: #e9ebf0; }
#notch filechooser button { background: #272a36; }
#notch scrollbar slider { background: #4c5060; border-radius: 8px; min-width: 4px; }
#notch button.active { background: #34394b; }
#notch #mute { padding: 1px 2px; min-width: 14px; }
#notch button.enabled { color: #ff4c65; }
#notch button.enabled:hover { color: #ff7c8f; background: #30212a; }


#cover { background: linear-gradient(135deg, #323849, #a3b3ba); border-radius: 14px; color: white; }
#title { font-size: 11px; font-weight: bold; }
#artist, #time { color: #91949e; font-size: 9px; }
#hint { color: #b7bbc8; font-size: 11px; }
#brand { color: #757b88; font-size: 10px; letter-spacing: 2px; }
#notch button { background: transparent; border: none; box-shadow: none; color: #e9ebf0; border-radius: 7px; padding: 1px 3px; min-width: 12px; min-height: 16px; }
#notch button:hover { background: #252832; }
#notch #play { background: #f2f3f5; color: #0a0b0e; border-radius: 14px; min-width: 20px; }
#notch scale trough { background: #30323a; min-height: 3px; border: none; }
#notch scale highlight { background: #d8dde8; min-height: 3px; }
#notch scale slider { background: #ffffff; min-width: 8px; min-height: 8px; border: none; box-shadow: none; }
#notch scale { padding: 3px 0; }
'''


def clock(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 60}:{seconds % 60:02}'


class Notch(Gtk.Window):
    def __init__(self, files):
        super().__init__(title='Notch Music')
        self.layer_shell = get_layer_shell()
        if self.layer_shell:
            anchor_window(self, self.layer_shell)
        self.set_name('notch-window')
        icon = Path(__file__).resolve().parent / 'assets/notch-music-logo-v2.png'
        if icon.is_file():
            self.set_icon_from_file(str(icon))
        self.settings_path = Path(GLib.get_user_config_dir()) / 'notch-music' / 'settings.json'
        self.theme = 'dark'
        try:
            saved = json.loads(self.settings_path.read_text())
            if isinstance(saved, dict) and saved.get('theme') in THEMES:
                self.theme = saved['theme']
        except (OSError, ValueError, TypeError):
            pass
        self.lyric_lines = []
        self.plain_lyrics = []
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.queue = []
        self.index = -1
        self.playing = False
        self.muted = False
        self.volume_checkpoint = .3
        self.setting_volume = False
        self.duration = 0
        self.updating = False
        self.repeat_mode = 0  # off, one, all
        self.lyrics_enabled = True
        self.shuffle = False
        self.shuffle_remaining = []
        self.history = []
        self.player = Gst.ElementFactory.make('playbin', 'player')
        if not self.player:
            raise RuntimeError('GStreamer playbin belum tersedia.')
        self.player.set_property('volume', .3)
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.message)
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(theme_css(CSS, self.theme))
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), self.css_provider, 600)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)
        center = Gtk.Box()
        root.pack_start(center, False, False, 0)
        center.pack_start(Gtk.Box(), True, True, 0)
        shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.notch = shell
        self.connect_after('draw', self.draw_top_connection)
        shell.set_name('notch')
        notch = Gtk.Box(spacing=6)
        self.connect('size-allocate', self.update_input_region)
        notch.set_name('player')
        notch.set_size_request(390, 94)
        center.pack_start(shell, False, False, 0)
        shell.pack_start(notch, False, False, 0)
        center.pack_start(Gtk.Box(), True, True, 0)
        self.cover = Gtk.Image.new_from_icon_name('audio-x-generic', Gtk.IconSize.DIALOG)
        self.cover.set_name('cover')
        self.cover.set_size_request(54, 54)
        self.cover.set_valign(Gtk.Align.CENTER)
        self.cover.set_halign(Gtk.Align.CENTER)
        notch.pack_start(self.cover, False, False, 0)
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        info.set_size_request(150, -1)
        notch.pack_start(info, True, True, 0)
        self.title = self.label('Belum ada lagu', 'title', info)
        self.artist = self.label('Buka musik untuk mulai mendengarkan', 'artist', info)
        self.seek = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, .1)
        self.seek.set_draw_value(False)
        self.seek.connect('change-value', self.seek_changed)
        info.pack_start(self.seek, False, False, 0)
        self.time = Gtk.Label(label='0:00 / 0:00')
        self.time.set_name('time')
        controls = Gtk.Box(spacing=4)
        controls.set_halign(Gtk.Align.CENTER)
        controls.pack_start(self.time, False, False, 0)
        info.pack_start(controls, False, False, 0)
        self.icon_button(controls, 'media-skip-backward-symbolic', 'Lagu sebelumnya', lambda *_: self.step(-1))
        self.play_button = self.icon_button(controls, 'media-playback-start-symbolic', 'Play / pause (Space)', self.toggle)
        self.play_button.set_name('play')
        self.icon_button(controls, 'media-skip-forward-symbolic', 'Lagu berikutnya', lambda *_: self.step(1))
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        side.set_size_request(142, -1)
        notch.pack_start(side, False, False, 0)
        top = Gtk.Box(spacing=2)
        top.set_halign(Gtk.Align.END)
        side.pack_start(top, False, False, 0)
        self.add_button = self.icon_button(top, 'list-add-symbolic', 'Tambahkan musik', self.open_files)
        self.queue_button = self.icon_button(top, 'view-list-symbolic', 'Antrean lagu', self.show_queue)
        self.shuffle_button = self.icon_button(top, 'media-playlist-shuffle-symbolic', 'Shuffle: mati', self.toggle_shuffle)
        self.shuffle_button.set_name('shuffle')
        self.repeat_button = self.icon_button(top, 'media-playlist-repeat-symbolic', 'Repeat: mati', self.toggle_repeat)
        self.lyrics_button = self.icon_button(top, 'insert-text-symbolic', 'Lirik: aktif', self.toggle_lyrics)
        self.lyrics_button.get_style_context().add_class('enabled')
        self.theme_button = self.icon_button(top, 'preferences-desktop-theme-symbolic', 'Pilih tema', self.cycle_theme)
        self.update_theme_icon()
        self.icon_button(top, 'window-close-symbolic', 'Tutup aplikasi', lambda *_: self.close())
        self.lyrics = Gtk.Label(label='Lirik akan tampil di sini', xalign=0.5)
        self.lyrics.set_name('hint')
        self.lyrics.set_ellipsize(Pango.EllipsizeMode.NONE)
        self.lyrics.set_line_wrap(True)
        self.lyrics.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.lyrics.set_width_chars(21)
        self.lyrics.set_max_width_chars(21)
        self.lyrics.set_single_line_mode(False)
        lyric_area = Gtk.Box(spacing=5)
        self.lyric_area = lyric_area
        self.lyrics.set_justify(Gtk.Justification.CENTER)
        self.lyrics.set_yalign(0.5)
        lyric_area.pack_start(self.lyrics, True, True, 0)
        side.pack_start(lyric_area, True, True, 0)

        volume_row = Gtk.Box(spacing=4)
        volume_row.set_valign(Gtk.Align.END)
        self.mute_button = self.icon_button(volume_row, 'audio-volume-low-symbolic', 'Mute', self.toggle_mute)
        self.mute_button.set_name('mute')
        volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, .01)
        volume.set_value(.3)
        volume.set_draw_value(False)
        volume.set_tooltip_text('Volume')
        self.volume = volume
        volume.set_hexpand(True)
        volume.connect('value-changed', self.volume_changed)
        volume_row.pack_start(volume, True, True, 0)
        side.pack_start(volume_row, False, False, 0)
        self.drawer_mode = None
        self.queue_generation = 0
        self.drawer = Gtk.Revealer()
        self.drawer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.drawer.set_transition_duration(180)
        shell.pack_start(self.drawer, False, False, 0)
        self.drawer_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.drawer_body.set_name('drawer')
        self.drawer.add(self.drawer_body)
        heading = Gtk.Box(spacing=8)
        self.drawer_body.pack_start(heading, False, False, 0)
        self.drawer_title = Gtk.Label(xalign=0)
        self.drawer_title.set_name('drawer-title')
        heading.pack_start(self.drawer_title, True, True, 0)
        self.button(heading, '⌃', 'Tutup panel', lambda *_: self.close_drawer())
        self.drawer_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.drawer_body.pack_start(self.drawer_content, False, False, 0)
        self.status = Gtk.Label(xalign=0)
        self.status.set_name('drawer-subtitle')
        self.drawer_body.pack_start(self.status, False, False, 0)
        self.drawer.connect('notify::child-revealed', lambda *_: self.fit_window())
        self.connect('size-allocate', lambda *_: self.fit_window())
        self.connect('destroy', self.shutdown)
        self.connect('key-press-event', self.keypress)
        self.connect('realize', self.position)
        self.connect('map-event', self.position)
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect('drag-data-received', self.drop)
        GLib.timeout_add(100, self.tick)
        self.add_files(files)

    def label(self, text, name, parent):
        label = Gtk.Label(label=text, xalign=0)
        label.set_name(name)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(20)
        parent.pack_start(label, False, False, 0)
        return label

    def button(self, parent, text, tooltip, callback):
        button = Gtk.Button(label=text)
        button.set_tooltip_text(tooltip)
        button.connect('clicked', callback)
        parent.pack_start(button, False, False, 0)
        return button

    def icon_button(self, parent, icon, tooltip, callback, label=None):
        button = Gtk.Button()
        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
        image.set_pixel_size(12)
        button.set_image(image)
        if label:
            button.set_label(label)
            button.set_always_show_image(True)
        button.set_tooltip_text(tooltip)
        button.connect('clicked', callback)
        parent.pack_start(button, False, False, 0)
        return button

    def position(self, *_):
        display = self.get_display()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        area = monitor.get_geometry()
        self.set_size_request(area.width, -1)
        if self.layer_shell:
            self.layer_shell.set_monitor(self, monitor)
        else:
            self.move(area.x, area.y)

    def update_input_region(self, *_):
        window = self.get_window()
        if not window:
            return
        # Only the notch receives input; the full-width bar is decorative.
        coordinates = self.notch.translate_coordinates(self, 0, 0)
        if coordinates is None:
            return
        x, y = coordinates
        allocation = self.notch.get_allocation()
        region = cairo.Region(cairo.RectangleInt(x, y, allocation.width, allocation.height))
        window.input_shape_combine_region(region, 0, 0)

    def draw_top_connection(self, widget, context):
        coordinates = self.notch.translate_coordinates(self, 0, 0)
        if coordinates is None:
            return False
        x, y = coordinates
        right = x + self.notch.get_allocated_width()
        radius = 15
        context.save()
        context.set_source_rgba(*THEMES[self.theme]['surface'])
        # A thin visual bridge along the screen edge; input remains confined
        # to the player so the desktop panel outside it stays clickable.
        context.rectangle(0, 0, self.get_allocated_width(), 2)
        context.fill()
        # Inverse quarter circles blend the top bar into both notch sides.
        context.move_to(x - radius, y)
        context.line_to(x + 1, y)
        context.line_to(x + 1, y + radius)
        context.line_to(x, y + radius)
        context.arc_negative(x - radius, y + radius, radius, 0, -math.pi / 2)
        context.close_path()
        context.fill()
        context.move_to(right + radius, y)
        context.line_to(right - 1, y)
        context.line_to(right - 1, y + radius)
        context.line_to(right, y + radius)
        context.arc(right + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
        context.close_path()
        context.fill()
        context.restore()
        return False

    def fit_window(self):
        if self.get_realized():
            minimum, natural = self.get_preferred_height()
            if self.get_size().height != natural:
                self.resize(self.get_size().width, natural)

    def open_drawer(self, mode, title):
        self.drawer_mode = mode
        self.drawer_title.set_text(title)
        for child in self.drawer_content.get_children():
            child.destroy()
        for button, name in [(self.add_button, 'add'), (self.queue_button, 'queue')]:
            context = button.get_style_context()
            context.add_class('active') if mode == name else context.remove_class('active')
        self.drawer.set_reveal_child(True)

    def close_drawer(self):
        self.drawer_mode = None
        self.drawer.set_reveal_child(False)
        self.add_button.get_style_context().remove_class('active')
        self.queue_button.get_style_context().remove_class('active')
        self.theme_button.get_style_context().remove_class('active')

    def cycle_theme(self, *_):
        order = ['dark', 'light', 'blur']
        self.set_theme(order[(order.index(self.theme) + 1) % len(order)])

    def update_theme_icon(self):
        icons = {'dark': 'weather-clear-night-symbolic',
                 'light': 'weather-clear-symbolic',
                 'blur': 'weather-fog-symbolic'}
        image = Gtk.Image.new_from_icon_name(icons[self.theme], Gtk.IconSize.BUTTON)
        image.set_pixel_size(12)
        self.theme_button.set_image(image)
        following = {'dark': 'Light', 'light': 'Blur', 'blur': 'Dark'}
        self.theme_button.set_tooltip_text(f"Tema: {THEMES[self.theme]['name']} · Klik untuk {following[self.theme]}")

    def set_theme(self, theme):
        if theme not in THEMES:
            return
        self.theme = theme
        self.css_provider.load_from_data(theme_css(CSS, theme))
        self.queue_draw()
        ok, position = self.player.query_position(Gst.Format.TIME)
        if self.lyric_lines or self.plain_lyrics:
            self.update_lyrics(position / Gst.SECOND if ok else 0)
        self.update_theme_icon()
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.settings_path.with_suffix('.tmp')
            temporary.write_text(json.dumps({'theme': theme}) + '\n')
            temporary.replace(self.settings_path)
        except OSError:
            self.status.set_text('Tema diterapkan, tetapi pilihan tidak dapat disimpan.')

    def open_files(self, *_):
        self.close_drawer()
        dialog = Gtk.FileChooserDialog(title='Tambahkan musik', transient_for=self,
                                       action=Gtk.FileChooserAction.OPEN)
        # A custom response keeps Select enabled even with no file selected.
        dialog.add_buttons('Batal', Gtk.ResponseType.CANCEL, 'Select', 100)
        dialog.set_default_response(100)
        dialog.set_select_multiple(True)
        dialog.set_default_size(800, 520)
        music = Path.home() / 'Music'
        if music.is_dir():
            dialog.set_current_folder(str(music))
        audio_filter = Gtk.FileFilter()
        audio_filter.set_name('File musik')
        for ext in AUDIO:
            audio_filter.add_pattern('*' + ext)
            audio_filter.add_pattern('*' + ext.upper())
        dialog.add_filter(audio_filter)
        hint = Gtk.Label(label='Pilih lagu (Ctrl+klik / Ctrl+A), atau tanpa memilih file: Select untuk seluruh folder.')
        hint.set_margin_start(12)
        hint.set_margin_end(12)
        hint.set_margin_top(8)
        hint.set_margin_bottom(8)
        hint.show()
        dialog.set_extra_widget(hint)
        dialog.connect('file-activated', lambda chooser: chooser.response(100))
        if dialog.run() == 100:
            files, folders = resolve_selection(dialog.get_filenames(), dialog.get_current_folder())
            dialog.destroy()
            if files:
                self.add_files(files)
            if folders:
                self.scan_folders(folders)
        else:
            dialog.destroy()

    def scan_folders(self, folders):
        self.status.set_text('Memindai folder…')
        def scan():
            files = []
            for folder in folders:
                for directory, subdirs, names in os.walk(folder):
                    subdirs.sort(key=str.casefold)
                    files.extend(Path(directory) / name for name in sorted(names, key=str.casefold)
                                 if Path(name).suffix.lower() in AUDIO)
            GLib.idle_add(self.folder_scanned, files)
        threading.Thread(target=scan, daemon=True).start()

    def folder_scanned(self, files):
        self.add_files(files)
        if not files:
            self.status.set_text('Tidak ada file musik di folder')
        return False

    def add_files(self, files):
        for filename in files:
            path = Path(filename).expanduser().resolve()
            if path.is_file() and path.suffix.lower() in AUDIO:
                self.queue.append(path)
                if self.shuffle:
                    self.shuffle_remaining.insert(random.randrange(len(self.shuffle_remaining) + 1), len(self.queue) - 1)
        if self.index < 0 and self.queue:
            self.load(0)
        self.update_status()
        if self.drawer_mode == 'queue':
            self.refresh_queue()

    def update_status(self):
        self.status.set_text(f'{len(self.queue)} lagu dalam antrean' if self.queue else 'Musikmu, selalu dekat.')

    def load(self, index):
        self.player.set_state(Gst.State.NULL)
        self.index = index
        self.shuffle_remaining = [i for i in self.shuffle_remaining if i != index]
        self.duration = 0
        path = self.queue[index]
        self.title.set_text(path.stem)
        self.artist.set_text(path.parent.name)
        self.cover.set_from_icon_name('audio-x-generic', Gtk.IconSize.DIALOG)
        self.lyric_lines, self.plain_lyrics = [], []
        self.lyrics.set_text('Membaca lirik…')
        def read():
            metadata = read_metadata(path)
            GLib.idle_add(self.apply_metadata, path, metadata)
        threading.Thread(target=read, daemon=True).start()
        self.player.set_property('uri', path.as_uri())
        self.player.set_state(Gst.State.PLAYING)
        self.playing = True
        self.sync_play_icons()
        if self.drawer_mode == 'queue':
            self.mark_current_track()

    def apply_metadata(self, path, metadata):
        if self.index < 0 or self.queue[self.index] != path:
            return False
        for key, label in [('title', self.title), ('artist', self.artist)]:
            if metadata[key]:
                label.set_text(metadata[key])
        self.lyric_lines, self.plain_lyrics = parse_lyrics(metadata['lyrics'])
        self.lyrics.set_tooltip_text(metadata['lyrics'] or 'File ini tidak memiliki lirik embedded atau file .lrc pendamping.')
        ok, position = self.player.query_position(Gst.Format.TIME)
        self.update_lyrics(position / Gst.SECOND if ok else 0)
        if metadata['picture']:
            try:
                loader = GdkPixbuf.PixbufLoader()
                loader.set_size(54, 54)
                loader.write(metadata['picture'])
                loader.close()
                self.cover.set_from_pixbuf(loader.get_pixbuf())
            except GLib.Error:
                pass
        return False

    def update_lyrics(self, seconds):
        if not self.lyrics_enabled:
            return
        if self.lyric_lines:
            import bisect
            index = bisect.bisect_right([t for t, _ in self.lyric_lines], seconds) - 1
            # Replace the current sentence at its next timestamp; never show
            # a preview row or invent timing for lyrics without timestamps.
            text = self.lyric_lines[max(0, index)][1]
            escaped = GLib.markup_escape_text(text.replace('\n', ' '))
            if index >= 0:
                accent = '#cf2646' if self.theme == 'light' else '#ff4c65'
                self.lyrics.set_markup(f'<span foreground="{accent}" weight="bold">{escaped}</span>')
            else:
                dim = THEMES[self.theme]['lyric_dim']
                self.lyrics.set_markup(f'<span foreground="{dim}">{escaped}</span>')
        else:
            self.lyrics.set_text(next(iter(self.plain_lyrics), 'Lirik tidak tersedia'))

    def toggle(self, *_):
        if not self.queue:
            self.open_files()
            return
        self.playing = not self.playing
        self.player.set_state(Gst.State.PLAYING if self.playing else Gst.State.PAUSED)
        self.sync_play_icons()

    def step(self, direction):
        if not self.queue:
            return
        if direction < 0 and self.shuffle and self.history:
            self.load(self.history.pop())
            return
        if self.shuffle and direction > 0:
            self.shuffle_remaining = [i for i in self.shuffle_remaining if i < len(self.queue) and i != self.index]
            if not self.shuffle_remaining:
                self.shuffle_remaining = [i for i in range(len(self.queue)) if i != self.index]
                random.shuffle(self.shuffle_remaining)
            target = self.shuffle_remaining.pop() if self.shuffle_remaining else self.index
            self.history.append(self.index)
            self.load(target)
        else:
            self.load((self.index + direction) % len(self.queue))

    def toggle_shuffle(self, *_):
        self.shuffle = not self.shuffle
        self.shuffle_remaining = [i for i in range(len(self.queue)) if i != self.index]
        random.shuffle(self.shuffle_remaining)
        self.history.clear()
        context = self.shuffle_button.get_style_context()
        context.add_class('enabled') if self.shuffle else context.remove_class('enabled')
        self.shuffle_button.set_tooltip_text('Shuffle: ' + ('aktif' if self.shuffle else 'mati'))
        self.shuffle_button.set_state_flags(Gtk.StateFlags.CHECKED, False) if self.shuffle else self.shuffle_button.unset_state_flags(Gtk.StateFlags.CHECKED)

    def toggle_mute(self, *_):
        if not self.muted:
            self.volume_checkpoint = self.volume.get_value()
        self.muted = not self.muted
        level = 0 if self.muted else self.volume_checkpoint
        self.setting_volume = True
        try:
            self.volume.set_value(level)
        finally:
            self.setting_volume = False
        self.player.set_property('volume', level)
        self.player.set_property('mute', self.muted)
        self.update_volume_icon()

    def volume_changed(self, slider):
        if self.setting_volume:
            return
        level = slider.get_value()
        # Dragging away from zero also restores sound immediately.
        if self.muted and level > 0:
            self.muted = False
            self.player.set_property('mute', False)
        if level > 0:
            self.volume_checkpoint = level
        self.player.set_property('volume', level)
        self.update_volume_icon()

    def update_volume_icon(self):
        level = self.volume.get_value()
        silent = self.muted or level == 0
        icon = ('audio-volume-muted-symbolic' if silent else
                'audio-volume-low-symbolic' if level < .34 else
                'audio-volume-medium-symbolic' if level < .67 else
                'audio-volume-high-symbolic')
        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
        image.set_pixel_size(12)
        self.mute_button.set_image(image)
        self.mute_button.set_tooltip_text('Unmute' if self.muted else 'Mute')
        context = self.mute_button.get_style_context()
        context.add_class('enabled') if self.muted else context.remove_class('enabled')

    def toggle_repeat(self, *_):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        icon = 'media-playlist-repeat-song-symbolic' if self.repeat_mode == 1 else 'media-playlist-repeat-symbolic'
        self.repeat_button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))
        context = self.repeat_button.get_style_context()
        context.add_class('enabled') if self.repeat_mode else context.remove_class('enabled')
        self.repeat_button.set_tooltip_text('Repeat: ' + ['mati', 'satu lagu', 'semua lagu'][self.repeat_mode])

    def toggle_lyrics(self, *_):
        self.lyrics_enabled = not self.lyrics_enabled
        # Keep the compact layout stable while hiding the lyric text.
        self.lyric_area.set_opacity(1 if self.lyrics_enabled else 0)
        self.lyric_area.set_sensitive(self.lyrics_enabled)
        context = self.lyrics_button.get_style_context()
        context.add_class('enabled') if self.lyrics_enabled else context.remove_class('enabled')
        self.lyrics_button.set_tooltip_text('Lirik: ' + ('aktif' if self.lyrics_enabled else 'mati'))
        if self.lyrics_enabled:
            ok, position = self.player.query_position(Gst.Format.TIME)
            self.update_lyrics(position / Gst.SECOND if ok else 0)

    def reset_player(self):
        self.player.set_state(Gst.State.NULL)
        self.index = -1
        self.playing = False
        self.duration = 0
        self.lyric_lines, self.plain_lyrics = [], []
        self.title.set_text('Belum ada lagu')
        self.artist.set_text('Buka musik untuk mulai mendengarkan')
        self.cover.set_from_icon_name('audio-x-generic', Gtk.IconSize.DIALOG)
        self.lyrics.set_text('Lirik akan tampil di sini')
        self.lyrics.set_tooltip_text(None)
        self.seek.set_value(0)
        self.time.set_text('0:00 / 0:00')
        self.sync_play_icons()

    def clear_queue(self, *_):
        self.queue.clear()
        self.history.clear()
        self.shuffle_remaining.clear()
        self.reset_player()
        self.update_status()
        if self.drawer_mode == 'queue':
            self.refresh_queue()

    def remove_track(self, index):
        if index < 0 or index >= len(self.queue):
            return
        current = self.index
        was_playing = self.playing
        self.queue.pop(index)
        # Remap stored indices to preserve shuffle and previous-track history.
        self.shuffle_remaining = [i - (i > index) for i in self.shuffle_remaining if i != index]
        self.history = [i - (i > index) for i in self.history if i != index]
        if not self.queue:
            self.reset_player()
        elif index == current:
            self.load(min(index, len(self.queue) - 1))
            if not was_playing:
                self.playing = False
                self.player.set_state(Gst.State.PAUSED)
                self.sync_play_icons()
        elif index < current:
            self.index -= 1
        self.update_status()
        if self.drawer_mode == 'queue':
            self.refresh_queue()

    def end_of_track(self):
        if not self.queue:
            return
        if self.repeat_mode == 1:
            self.load(self.index)
        elif self.shuffle:
            remaining = [i for i in self.shuffle_remaining if i < len(self.queue) and i != self.index]
            if remaining or self.repeat_mode == 2:
                self.step(1)
            else:
                self.stop_at_end()
        elif self.index + 1 < len(self.queue) or self.repeat_mode == 2:
            self.step(1)
        else:
            self.stop_at_end()

    def stop_at_end(self):
        self.player.set_state(Gst.State.PAUSED)
        self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH, 0)
        self.playing = False
        self.sync_play_icons()

    def sync_play_icons(self):
        self.play_button.set_image(Gtk.Image.new_from_icon_name(
            'media-playback-pause-symbolic' if self.playing else 'media-playback-start-symbolic', Gtk.IconSize.MENU))

    def seek_changed(self, scale, scroll, value):
        if self.duration:
            self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, int(value * Gst.SECOND))
        return True

    def tick(self):
        ok, duration = self.player.query_duration(Gst.Format.TIME)
        pos_ok, position = self.player.query_position(Gst.Format.TIME)
        if ok and duration > 0:
            self.duration = duration / Gst.SECOND
            self.seek.set_range(0, self.duration)
            seconds = position / Gst.SECOND if pos_ok else 0
            self.seek.set_value(seconds)
            self.update_lyrics(seconds)
            self.time.set_text(f'{clock(seconds)} / {clock(self.duration)}')
        return True

    def message(self, bus, message):
        if message.type == Gst.MessageType.EOS:
            self.end_of_track()
        elif message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            self.playing = False
            self.sync_play_icons()
            self.lyrics.set_text('Gagal memutar lagu')
            self.lyrics.set_tooltip_text(str(error))
        elif message.type == Gst.MessageType.TAG:
            tags = message.parse_tag()
            for tag, label in [('title', self.title), ('artist', self.artist)]:
                found, value = tags.get_string(tag)
                if found:
                    label.set_text(value)

    def show_queue(self, *_, force=False):
        if self.drawer_mode == 'queue' and not force:
            self.close_drawer()
            return
        self.open_drawer('queue', 'Antrean musik')
        actions = Gtk.Box()
        self.button(actions, 'Clear', 'Kosongkan antrean (file musik tetap tersimpan)', self.clear_queue)
        self.drawer_content.pack_start(actions, False, False, 0)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text('Cari lagu atau artis…')
        self.search.connect('search-changed', lambda *_: self.refresh_queue())
        self.drawer_content.pack_start(self.search, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(190)
        scroll.set_max_content_height(190)
        self.listing = Gtk.ListBox()
        self.listing.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listing.set_activate_on_single_click(True)
        self.listing.connect('row-activated', lambda box, row: self.load(row.track_index) if hasattr(row, 'track_index') else None)
        scroll.add(self.listing)
        self.drawer_content.pack_start(scroll, False, False, 0)
        self.refresh_queue()
        self.drawer_content.show_all()

    def mark_current_track(self):
        for row in self.listing.get_children():
            if not isinstance(row, Gtk.ListBoxRow) or not hasattr(row, 'track_index'):
                continue
            context = row.get_style_context()
            if row.track_index == self.index:
                context.add_class('current-track')
                row.play_icon.set_text('♫')
            else:
                context.remove_class('current-track')
                row.play_icon.set_text('▶')

    def refresh_queue(self):
        self.queue_generation += 1
        generation = self.queue_generation
        for row in self.listing.get_children():
            row.destroy()
        query = self.search.get_text().casefold().strip()
        matches = [(i, p) for i, p in enumerate(self.queue) if query in p.stem.casefold()]
        rows = []
        for index, path in matches[:100]:
            row = Gtk.ListBoxRow()
            row.track_index = index
            box = Gtk.Box(spacing=10)
            row.add(box)
            image = Gtk.Image.new_from_icon_name('audio-x-generic', Gtk.IconSize.LARGE_TOOLBAR)
            image.set_size_request(34, 34)
            box.pack_start(image, False, False, 0)
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.pack_start(text, True, True, 0)
            artist, separator, title = path.stem.partition(' - ')
            name = Gtk.Label(label=title if separator else path.stem, xalign=0)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_max_width_chars(40)
            name.get_style_context().add_class('track-title')
            text.pack_start(name, False, False, 0)
            subtitle = Gtk.Label(label=artist if separator else path.parent.name, xalign=0)
            subtitle.set_ellipsize(Pango.EllipsizeMode.END)
            subtitle.set_max_width_chars(40)
            subtitle.get_style_context().add_class('track-artist')
            text.pack_start(subtitle, False, False, 0)
            row.play_icon = Gtk.Label(label='▶')
            self.icon_button(box, 'edit-delete-symbolic', 'Hapus dari antrean',
                             lambda button, track=index: self.remove_track(track))
            box.pack_end(row.play_icon, False, False, 8)
            self.listing.add(row)
            rows.append((path, image))
        if not matches:
            empty = Gtk.Label(label='Tidak ada lagu yang cocok.' if query else 'Antrean kosong. Tambahkan musik lewat ＋.')
            empty.set_margin_top(25)
            empty.set_margin_bottom(25)
            self.listing.add(empty)
        self.status.set_text(f'{len(matches)} lagu' + (' · menampilkan 100 pertama, gunakan pencarian' if len(matches) > 100 else ''))
        self.mark_current_track()
        self.listing.show_all()
        def artwork():
            for path, image in rows:
                if generation != self.queue_generation:
                    break
                data = read_metadata(path)['picture']
                if data:
                    GLib.idle_add(self.queue_artwork, generation, image, data)
        threading.Thread(target=artwork, daemon=True).start()

    def queue_artwork(self, generation, image, data):
        if generation != self.queue_generation or self.drawer_mode != 'queue':
            return False
        try:
            loader = GdkPixbuf.PixbufLoader()
            loader.set_size(34, 34)
            loader.write(data)
            loader.close()
            image.set_from_pixbuf(loader.get_pixbuf())
        except GLib.Error:
            pass
        return False

    def drop(self, widget, context, x, y, data, info, timestamp):
        paths = []
        for uri in data.get_uris() or []:
            try:
                path, host = GLib.filename_from_uri(uri)
                if not host:
                    paths.append(path)
            except GLib.Error:
                pass
        self.add_files(paths)
        Gtk.drag_finish(context, bool(paths), False, timestamp)

    def keypress(self, widget, event):
        if isinstance(self.get_focus(), (Gtk.Entry, Gtk.TextView)):
            return False
        if event.keyval == Gdk.KEY_space:
            self.toggle()
            return True
        if event.keyval == Gdk.KEY_Escape:
            if self.drawer_mode:
                self.close_drawer()
            else:
                self.close()
            return True
        return False

    def shutdown(self, *_):
        self.player.set_state(Gst.State.NULL)
        Gtk.main_quit()


if __name__ == '__main__':
    if not Gtk.init_check()[0]:
        sys.exit('Tidak dapat terhubung ke desktop. Jalankan dari sesi Linux Anda; untuk fallback X11/Wayland, pasang XWayland atau gtk-layer-shell.')
    display = Gdk.Display.get_default()
    if ('Wayland' in type(display).__name__ and not get_layer_shell()
            and os.environ.get('DISPLAY') and not os.environ.get('NOTCH_GDK_BACKEND')
            and os.environ.get('GDK_BACKEND') != 'x11'):
        os.environ['GDK_BACKEND'] = 'x11'
        os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])
    window = Notch(sys.argv[1:])
    window.show_all()
    Gtk.main()

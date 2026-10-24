#!/usr/bin/env python3
"""A compact GTK desktop music player. Run through ./run.sh."""
import os
import sys
import threading
import random
import math
import json
import re
import unicodedata
import cairo
from pathlib import Path
from metadata import read_metadata, parse_lyrics, read_audio_info, format_audio_info
from selection import resolve_selection, prepare_file_selection
from themes import THEMES, theme_css
from desktop_support import configure_backend, get_layer_shell, anchor_window, window_shape
from playlists import EXTENSION as PLAYLIST_EXTENSION, load_playlist, save_playlist
from mpris import MprisService

import gi
configure_backend()
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gdk, GLib, Gst, Pango, GdkPixbuf

Gst.init(None)
AUDIO = {'.mp3', '.flac', '.ogg', '.opus', '.wav', '.m4a', '.aac', '.wma'}
CSS = b'''
#notch-window { font-size: 12px; background-color: transparent; color: #fafafa; }
#bar { background: #08090b; }
#notch { background: #101116; border: 1px solid #292b35; border-radius: 0 0 16px 16px; transition: border-radius 180ms ease-out; }
#notch.floating { border-radius: 20px; border-top: 1px solid #292b35; }
#notch.docked { border-color: transparent; border-radius: 0 0 16px 16px; box-shadow: none; transition: none; }
#player { padding: 8px 8px 9px; }
#dock-handle { background: #101116; color: #b7bbc8; border: none; box-shadow: none; border-radius: 0 0 8px 8px; padding: 0 10px; min-width: 24px; min-height: 12px; font-size: 10px; }
#dock-handle:hover { color: #fafafa; }
#drawer { padding: 8px; }
#panel-divider { min-width: 1px; min-height: 0; border: none; background: linear-gradient(to bottom, rgba(145,151,166,0), rgba(145,151,166,0.65) 25%, rgba(145,151,166,0.65) 75%, rgba(145,151,166,0)); }
#panel-divider.horizontal { background: linear-gradient(to right, rgba(145,151,166,0), rgba(145,151,166,0.65) 25%, rgba(145,151,166,0.65) 75%, rgba(145,151,166,0)); }
#drawer entry { padding: 3px 7px; min-height: 16px; }
#drawer-title { font-size: 14px; font-weight: bold; }
#drawer-subtitle { color: #9297a6; font-size: 11px; }
#notch entry { background: #20222c; color: #f3f4f9; border: 1px solid #373a48; border-radius: 14px; padding: 7px 10px; box-shadow: none; }
#notch list, #notch viewport, #notch scrolledwindow { background: transparent; color: #f3f4f9; }
#notch row { padding: 3px; border-radius: 10px; margin: 2px 0; }
#notch row:hover { background: #252833; }
#notch row:selected { background: #303344; }
#notch .current-track { background: #242936; }
#notch row .track-title, #notch row:hover .track-title, #notch row:selected .track-title, #notch row:active .track-title { color: #f3f4f9; font-size: 13px; font-weight: bold; }
#notch row .track-artist, #notch row:hover .track-artist, #notch row:selected .track-artist, #notch row:active .track-artist { color: #9297a6; font-size: 11px; }
#notch filechooser, #notch filechooser box, #notch treeview { background-color: #171921; color: #e9ebf0; }
#notch filechooser button { background: #272a36; }
#notch scrollbar slider { background: #4c5060; border-radius: 8px; min-width: 4px; }
#notch button.active { background: #34394b; }
#notch #mute { padding: 1px 2px; min-width: 14px; }
#notch button.enabled { color: #ff4c65; }
#notch button.enabled:hover { color: #ff7c8f; background: #30212a; }


#cover { background: linear-gradient(135deg, #323849, #a3b3ba); border-radius: 14px; color: white; }
#title { font-size: 14px; font-weight: bold; }
#artist { color: #91949e; font-size: 12px; }
#audio-info { color: #91949e; font-size: 10px; }
#time { color: #91949e; font-size: 10px; }
#hint { color: #fafafa; font-size: 14px; }
#brand { color: #757b88; font-size: 11px; letter-spacing: 2px; }
#notch button { background: transparent; border: none; box-shadow: none; color: #e9ebf0; border-radius: 7px; padding: 1px 3px; min-width: 12px; min-height: 16px; }
#notch button:hover { background: #252832; }
#notch #overflow-menu { border-radius: 14px; min-width: 22px; min-height: 22px; font-size: 18px; background: #252832; }
#player-menu, #player-submenu { background: #101116; color: #fafafa; border: 1px solid #292b35; border-radius: 10px; padding: 3px; font-size: 12px; }
#player-menu menuitem, #player-submenu menuitem { color: #e9ebf0; padding: 2px 4px; min-width: 0; min-height: 19px; border-radius: 5px; }
#player-menu menuitem:hover, #player-submenu menuitem:hover { background: #252832; }
#player-submenu button { color: #e9ebf0; background: transparent; border: none; box-shadow: none; padding: 3px; }
#player-submenu button.enabled { color: #ff4c65; }
#player-submenu scale trough { background: #30323a; min-height: 3px; }
#player-submenu scale highlight { background: #d8dde8; }
#player-submenu scale slider { background: #ffffff; min-width: 9px; min-height: 9px; }
#notch #play { background: #f2f3f5; color: #0a0b0e; border-radius: 14px; min-width: 20px; }
#notch scale trough { background: #30323a; min-height: 3px; border: none; }
#notch scale highlight { background: #d8dde8; min-height: 3px; }
#notch scale slider { background: #ffffff; min-width: 8px; min-height: 8px; border: none; box-shadow: none; }
#notch scale { padding: 3px 0; }
'''


def clock(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 60}:{seconds % 60:02}'


def normalize_search(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    text = ''.join(char for char in text if not unicodedata.combining(char))
    return ' '.join(re.findall(r'[^\W_]+', text, re.UNICODE))


def track_details(path, metadata):
    artist, separator, title = path.stem.partition(' - ')
    return (metadata.get('title') or (title if separator else path.stem),
            metadata.get('artist') or (artist if separator else path.parent.name))


def search_tracks(queue, query, metadata):
    words = normalize_search(query).split()
    matches = []
    for index, path in enumerate(queue):
        title, artist = track_details(path, metadata.get(path, {}))
        haystack = normalize_search(f'{path.stem} {title} {artist}')
        if all(word in haystack for word in words):
            matches.append((index, path))
    return matches


class Notch(Gtk.Window):
    def __init__(self, files):
        super().__init__(title='Notch Music')
        self.docked = False
        self.drag_origin = None
        self.floating_center = None
        self.floating_y = 24
        self.positioned = False
        self.snap_tick = None
        self.connection_progress = 0.0
        self.bezel_bar = None
        self.dock_autohide = False
        self.autohide_wait_exit = False
        self.hover_left_at = None
        self.pointer_inside = False
        self.browse_open = False
        self.restore_window = None
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
        if sys.platform == 'win32':
            # Avoid colored subpixel fringes on small text over dark or
            # translucent surfaces. These settings affect only this process.
            settings = Gtk.Settings.get_default()
            settings.set_property('gtk-xft-antialias', 1)
            settings.set_property('gtk-xft-rgba', 'none')
            options = cairo.FontOptions()
            options.set_antialias(cairo.ANTIALIAS_GRAY)
            self.get_screen().set_font_options(options)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.queue = []
        self.playlist_tracks = []
        self.playlist_name = 'Playlist baru'
        self.playlist_file = None
        self.playlist_editing = False
        self.queue_metadata = {}
        self.metadata_pending = set()
        self.index = -1
        self.playing = False
        self.muted = False
        self.volume_checkpoint = .3
        self.setting_volume = False
        self.duration = 0
        self.updating = False
        self.repeat_mode = 0  # off, one, all
        self.lyrics_enabled = False
        self.shuffle = False
        self.shuffle_remaining = []
        self.history = []
        self.player = Gst.ElementFactory.make('playbin', 'player')
        if not self.player:
            raise RuntimeError('GStreamer playbin belum tersedia.')
        self.visualizer_target = [0.0] * 32
        self.visualizer_levels = [0.0] * 32
        self.visualizer_updated = 0
        self.visualizer_frame_time = 0
        self.spectrum = None
        try:
            audio_filter = Gst.parse_bin_from_description(
                'audioconvert ! spectrum name=lyric-spectrum bands=32 threshold=-72 '
                'interval=40000000 post-messages=false ! audioconvert', True)
            self.spectrum = audio_filter.get_by_name('lyric-spectrum')
            self.player.set_property('audio-filter', audio_filter)
        except GLib.Error:
            pass  # Playback remains available if the optional analyzer is missing.
        self.player.set_property('volume', .3)
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.message)
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(theme_css(CSS, self.theme))
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), self.css_provider, 600)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)
        self.body_revealer = Gtk.Revealer()
        self.body_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.body_revealer.set_transition_duration(220)
        self.body_revealer.set_reveal_child(True)
        root.pack_start(self.body_revealer, False, False, 0)
        center = Gtk.Box()
        self.body_revealer.add(center)
        self.dock_handle = Gtk.Button(label='▴')
        self.dock_handle.set_name('dock-handle')
        self.dock_handle.set_halign(Gtk.Align.CENTER)
        self.dock_handle.set_no_show_all(True)
        self.dock_handle.connect('clicked', self.toggle_dock_autohide)
        root.pack_start(self.dock_handle, False, False, 0)
        self.left_space = Gtk.Box()
        self.left_space.set_size_request(24, -1)
        center.pack_start(self.left_space, True, True, 0)
        shell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.notch = shell
        shell.set_name('notch')
        shell.get_style_context().add_class('floating')
        shell.set_hexpand(False)
        self.connect_after('draw', self.draw_top_connection)
        self.connect('size-allocate', self.update_input_region)
        center.pack_start(shell, False, False, 0)
        right_space = Gtk.Box()
        right_space.set_size_request(24, -1)
        center.pack_start(right_space, True, True, 0)

        player = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.player_widget = player
        player.set_name('player')
        player.set_size_request(350, 128)
        player.set_valign(Gtk.Align.CENTER)
        self.player_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        shell.pack_start(self.player_column, False, False, 0)
        self.player_column.pack_start(player, False, False, 0)
        top = Gtk.Box(spacing=2)
        top.set_halign(Gtk.Align.END)
        top.set_no_show_all(True)
        top.hide()
        player.pack_start(top, False, False, 0)
        self.add_button = self.icon_button(top, 'list-add-symbolic', 'Tambahkan musik', self.open_files)
        self.queue_button = self.icon_button(top, 'view-list-symbolic', 'Antrean lagu', self.show_queue)
        self.shuffle_button = self.icon_button(top, 'media-playlist-shuffle-symbolic', 'Shuffle: mati', self.toggle_shuffle)
        self.shuffle_button.set_name('shuffle')
        self.repeat_button = self.icon_button(top, 'media-playlist-repeat-symbolic', 'Repeat: mati', self.toggle_repeat)
        self.lyrics_button = self.icon_button(top, 'insert-text-symbolic', 'Lirik: mati', self.toggle_lyrics)
        self.theme_button = self.icon_button(top, 'preferences-desktop-theme-symbolic', 'Pilih tema', self.cycle_theme)
        self.update_theme_icon()
        self.icon_button(top, 'window-close-symbolic', 'Tutup aplikasi', lambda *_: self.close())

        song = Gtk.Box(spacing=9)
        player.pack_start(song, True, True, 0)
        self.cover = Gtk.Image.new_from_icon_name('audio-x-generic', Gtk.IconSize.DIALOG)
        self.cover.set_name('cover')
        self.cover.set_size_request(44, 44)
        self.cover.set_valign(Gtk.Align.CENTER)
        song.pack_start(self.cover, False, False, 0)
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        info.set_size_request(205, -1)
        info.set_valign(Gtk.Align.CENTER)
        song.pack_start(info, True, True, 0)
        title_row = Gtk.Box(spacing=5)
        info.pack_start(title_row, False, False, 0)
        self.title = self.label('Belum ada lagu', 'title', title_row)
        title_row.set_child_packing(self.title, True, True, 0, Gtk.PackType.START)
        self.menu_button = Gtk.MenuButton(label='⋯')
        self.menu_button.set_name('overflow-menu')
        self.menu_button.set_direction(Gtk.ArrowType.NONE)
        self.menu_button.set_tooltip_text('Menu player')
        title_row.pack_end(self.menu_button, False, False, 0)
        self.artist = self.label('Buka musik untuk mulai mendengarkan', 'artist', info)
        self.audio_info = self.label('Format audio', 'audio-info', info)
        self.audio_info.set_max_width_chars(32)
        progress = Gtk.Box(spacing=6)
        info.pack_start(progress, False, False, 0)
        self.seek = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, .1)
        self.seek.set_draw_value(False)
        self.seek.set_hexpand(True)
        self.seek.connect('change-value', self.seek_changed)
        progress.pack_start(self.seek, True, True, 0)
        self.time = Gtk.Label(label='0:00 / 0:00')
        self.time.set_name('time')
        progress.pack_end(self.time, False, False, 0)

        bottom = Gtk.Box(spacing=5)
        player.pack_start(bottom, False, False, 0)
        controls = Gtk.Box(spacing=15)
        self.transport_controls = controls
        controls.set_halign(Gtk.Align.CENTER)
        bottom.pack_start(controls, True, True, 0)
        top.remove(self.shuffle_button)
        controls.pack_start(self.shuffle_button, False, False, 0)
        self.icon_button(controls, 'media-skip-backward-symbolic', 'Lagu sebelumnya', lambda *_: self.step(-1))
        self.play_button = self.icon_button(controls, 'media-playback-start-symbolic', 'Play / pause (Space)', self.toggle)
        self.play_button.set_name('play')
        self.icon_button(controls, 'media-skip-forward-symbolic', 'Lagu berikutnya', lambda *_: self.step(1))
        top.remove(self.repeat_button)
        controls.pack_start(self.repeat_button, False, False, 0)
        for control in controls.get_children():
            control.get_image().set_pixel_size(16)
        volume_row = Gtk.Box(spacing=4)
        volume_row.set_size_request(100, -1)
        volume_row.set_no_show_all(True)
        volume_row.hide()
        bottom.pack_end(volume_row, False, False, 0)
        self.mute_button = self.icon_button(volume_row, 'audio-volume-low-symbolic', 'Mute', self.toggle_mute)
        self.mute_button.set_name('mute')
        self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, .01)
        self.volume.set_value(.3)
        self.volume.set_draw_value(False)
        self.volume.set_tooltip_text('Volume')
        self.volume.set_hexpand(True)
        self.volume.connect('value-changed', self.volume_changed)
        volume_row.pack_start(self.volume, True, True, 0)

        self.lyrics = Gtk.Label(label='Lirik akan tampil di sini', xalign=0.5)
        self.lyrics.set_name('hint')
        self.lyrics.set_line_wrap(True)
        self.lyrics.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.lyrics.set_width_chars(26)
        self.lyrics.set_max_width_chars(26)
        self.lyrics.set_justify(Gtk.Justification.CENTER)
        self.lyrics.set_yalign(0.5)
        self.lyric_area = Gtk.Box()
        self.lyric_area.pack_start(self.lyrics, True, True, 0)

        self.drawer_mode = None
        self.queue_enabled = False
        self.queue_ui_ready = False
        self.queue_generation = 0
        self.drawer = Gtk.Revealer()
        self.drawer.set_no_show_all(True)
        self.drawer.hide()
        self.drawer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
        self.drawer.set_transition_duration(180)
        shell.pack_start(self.drawer, False, False, 0)
        self.drawer_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.drawer_body.set_name('drawer')
        self.drawer_body.set_size_request(280, 128)
        panel_frame = Gtk.Box(spacing=0)
        self.panel_frame = panel_frame
        self.panel_divider = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.panel_divider.set_name('panel-divider')
        self.panel_divider.set_size_request(1, 64)
        self.panel_divider.set_valign(Gtk.Align.CENTER)
        panel_frame.pack_start(self.panel_divider, False, False, 0)
        panel_frame.pack_start(self.drawer_body, True, True, 0)
        self.drawer.add(panel_frame)
        self.drawer_heading = Gtk.Box(spacing=8)
        self.drawer_body.pack_start(self.drawer_heading, False, False, 0)
        self.drawer_title = Gtk.Label(xalign=0)
        self.drawer_title.set_name('drawer-title')
        self.drawer_heading.pack_start(self.drawer_title, True, True, 0)
        self.icon_button(self.drawer_heading, 'go-next-symbolic', 'Tutup panel', lambda *_: self.close_drawer())
        self.drawer_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.drawer_body.pack_start(self.drawer_content, True, True, 0)
        self.lyric_drawer = Gtk.Revealer()
        self.lyric_drawer.set_no_show_all(True)
        self.lyric_drawer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_RIGHT)
        self.lyric_drawer.set_transition_duration(180)
        shell.pack_start(self.lyric_drawer, False, False, 0)
        lyric_frame = Gtk.Box()
        self.lyric_divider = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.lyric_divider.set_name('panel-divider')
        self.lyric_divider.set_size_request(1, 64)
        self.lyric_divider.set_valign(Gtk.Align.CENTER)
        lyric_frame.pack_start(self.lyric_divider, False, False, 0)
        self.lyric_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.lyric_body.set_name('drawer')
        self.lyric_body.set_size_request(280, 128)
        lyric_frame.pack_start(self.lyric_body, True, True, 0)
        self.visualizer_top = Gtk.DrawingArea()
        self.visualizer_top.set_size_request(-1, 30)
        self.visualizer_top.connect('draw', self.draw_visualizer, True)
        self.lyric_body.pack_start(self.visualizer_top, False, False, 0)
        self.lyric_stack = Gtk.Stack()
        self.lyric_stack.set_hhomogeneous(False)
        self.lyric_stack.set_vhomogeneous(False)
        self.lyric_stack.add_named(self.lyric_area, 'compact')
        self.lyric_scroll = Gtk.ScrolledWindow()
        self.lyric_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        self.lyric_context = Gtk.Label(xalign=0.5, yalign=0.5)
        self.lyric_context.set_name('hint')
        self.lyric_context.set_line_wrap(True)
        self.lyric_context.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.lyric_context.set_width_chars(26)
        self.lyric_context.set_max_width_chars(26)
        self.lyric_context.set_justify(Gtk.Justification.CENTER)
        self.lyric_scroll.add(self.lyric_context)
        self.lyric_stack.add_named(self.lyric_scroll, 'expanded')
        self.lyric_body.pack_start(self.lyric_stack, True, True, 0)
        self.visualizer_bottom = Gtk.DrawingArea()
        self.visualizer_bottom.set_size_request(-1, 30)
        self.visualizer_bottom.connect('draw', self.draw_visualizer, False)
        self.lyric_body.pack_end(self.visualizer_bottom, False, False, 0)
        self.lyric_body.add_tick_callback(self.animate_visualizer)
        self.lyric_drawer.add(lyric_frame)
        self.lyric_position = 0
        self.lyrics.connect('notify::label', lambda *_: self.update_lyric_context())
        self.lyric_drawer.connect('notify::child-revealed', self.panel_transition_finished)
        self.status = Gtk.Label(xalign=0)
        self.status.set_name('drawer-subtitle')
        self.status.set_no_show_all(True)
        self.status.hide()
        self.drawer.connect('notify::child-revealed', self.panel_transition_finished)
        self.connect('size-allocate', lambda *_: self.fit_window())
        self.connect('destroy', self.shutdown)
        self.connect('key-press-event', self.keypress)
        self.connect('realize', self.position)
        self.connect('map-event', self.position)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect('button-press-event', self.start_move)
        self.connect('motion-notify-event', self.move_player)
        self.connect('button-release-event', self.finish_move)
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect('drag-data-received', self.drop)
        GLib.timeout_add(100, self.tick)
        self.hover_source = GLib.timeout_add(60, self.poll_notch_hover)
        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect('enter-notify-event', self.notch_pointer_crossing, True)
        self.connect('leave-notify-event', self.notch_pointer_crossing, False)
        self.build_player_menu(volume_row)
        self.add_files(files)
        self.mpris = MprisService(self)

    def build_player_menu(self, volume_row):
        self._syncing_menu = False
        self.player_menu = Gtk.Menu()
        self.player_menu.set_reserve_toggle_size(False)
        self.player_menu.set_name('player-menu')
        self.menu_button.set_popup(self.player_menu)
        self.menu_entries = {}

        def item(label, icon, callback=None):
            entry = Gtk.MenuItem()
            row = Gtk.Box(spacing=5)
            image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)
            row.pack_start(image, False, False, 0)
            text = Gtk.Label(label=label, xalign=0)
            row.pack_start(text, True, True, 0)
            entry.add(row)
            if callback:
                entry.connect('activate', callback)
            self.player_menu.append(entry)
            self.menu_entries[label] = entry
            return entry, text

        item('Browse', 'folder-open-symbolic', self.open_files)
        playlist_item, _ = item('Playlist', 'folder-music-symbolic')
        playlist_menu = Gtk.Menu()
        playlist_menu.set_name('player-submenu')
        playlist_menu.set_reserve_toggle_size(False)
        playlist_item.set_submenu(playlist_menu)
        for title, callback in (('Create Playlist', self.create_playlist), ('Load Playlist', self.load_playlist_dialog)):
            choice = Gtk.MenuItem(label=title)
            choice.connect('activate', callback)
            playlist_menu.append(choice)
        item('Queue', 'view-list-symbolic', self.show_queue)
        volume_item, self.menu_volume_label = item('Volume', 'audio-volume-high-symbolic')
        volume_menu = Gtk.Menu()
        volume_menu.set_reserve_toggle_size(False)
        volume_menu.set_name('player-submenu')
        volume_item.set_submenu(volume_menu)
        slider_item = Gtk.MenuItem()
        volume_row.get_parent().remove(volume_row)
        volume_row.set_no_show_all(False)
        volume_row.set_size_request(140, 26)
        self.volume.set_size_request(110, -1)
        volume_row.set_valign(Gtk.Align.CENTER)
        slider_item.add(volume_row)
        volume_menu.append(slider_item)
        # MenuShell owns the pointer grab, so route slider gestures explicitly
        # instead of letting a release activate and dismiss its MenuItem.
        self._menu_volume_dragging = False
        volume_menu.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        for signal in ('button-press-event', 'motion-notify-event', 'button-release-event'):
            volume_menu.connect(signal, self.menu_volume_pointer)
        volume_menu.connect('hide', lambda *_: setattr(self, '_menu_volume_dragging', False))

        _, self.menu_lyrics_label = item('Lirik', 'insert-text-symbolic', self.toggle_lyrics)

        theme_item, _ = item('Tema', 'preferences-desktop-theme-symbolic')
        theme_menu = Gtk.Menu()
        theme_menu.set_name('player-submenu')
        theme_item.set_submenu(theme_menu)
        for signal in ('button-press-event', 'button-release-event', 'key-press-event'):
            theme_menu.connect(signal, self.select_theme_without_closing)
        self.theme_menu_items = {}
        group = None
        for key, theme in THEMES.items():
            choice = Gtk.RadioMenuItem.new_with_label_from_widget(group, theme['name'])
            group = choice
            choice.connect('toggled', self.menu_theme_toggled, key)
            theme_menu.append(choice)
            self.theme_menu_items[key] = choice
        self.player_menu.append(Gtk.SeparatorMenuItem())
        minimize, _ = item('Minimize', 'window-minimize-symbolic', self.minimize_player)
        minimize.get_child().show_all()
        minimize.set_no_show_all(True)
        item('Close', 'window-close-symbolic', lambda *_: self.close())
        self.player_menu.connect('show', lambda *_: self.sync_menu_state())
        self.player_menu.show_all()
        self.player_menu.hide()
        self.sync_menu_state()

    def menu_volume_pointer(self, menu, event):
        top = self.volume.get_toplevel()
        origin = top.get_window().get_origin()[-2:]
        offset = self.volume.translate_coordinates(top, 0, 0)
        x = event.x_root - origin[0] - offset[0]
        y = event.y_root - origin[1] - offset[1]
        press = event.type == Gdk.EventType.BUTTON_PRESS
        release = event.type == Gdk.EventType.BUTTON_RELEASE
        if (press or release) and event.button != 1:
            return False
        if press and 0 <= y <= self.volume.get_allocated_height():
            if x < 0:
                self.toggle_mute()
                return True
            self._menu_volume_dragging = True
        if self._menu_volume_dragging:
            # Leave half a thumb at either end, matching the scale's track.
            width = self.volume.get_allocated_width()
            self.volume.set_value(max(0, min(1, (x - 5) / max(1, width - 10))))
            if release:
                self._menu_volume_dragging = False
            return True
        return release

    def select_theme_without_closing(self, menu, event):
        if event.type == Gdk.EventType.KEY_PRESS:
            if event.keyval not in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
                return False
            choice = menu.get_selected_item()
        else:
            if event.button != 1:
                return False
            top = menu.get_toplevel()
            origin = top.get_window().get_origin()[-2:]
            choice = None
            for candidate in menu.get_children():
                x, y = candidate.translate_coordinates(top, 0, 0)
                if (origin[0] + x <= event.x_root < origin[0] + x + candidate.get_allocated_width()
                        and origin[1] + y <= event.y_root < origin[1] + y + candidate.get_allocated_height()):
                    choice = candidate
                    break
        if choice not in self.theme_menu_items.values():
            return False
        menu.select_item(choice)
        if event.type != Gdk.EventType.BUTTON_PRESS:
            choice.set_active(True)
        return True

    def menu_theme_toggled(self, choice, theme):
        if not self._syncing_menu and choice.get_active():
            self.set_theme(theme)

    def sync_menu_state(self):
        if not hasattr(self, 'menu_lyrics_label'):
            return
        self._syncing_menu = True
        try:
            state = 'On' if self.lyrics_enabled else 'Off'
            self.menu_lyrics_label.set_markup(f'Lirik <span size="small">({state})</span>')
            self.theme_menu_items[self.theme].set_active(True)
            self.menu_volume_label.set_text(f'Volume · {round(self.volume.get_value() * 100)}%')
            self.menu_entries['Minimize'].set_visible(not self.docked)
        finally:
            self._syncing_menu = False

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
        if self.positioned:
            return
        display = self.get_display()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        area = monitor.get_geometry()
        if area.width <= 0:
            return
        self.positioned = True
        self.floating_center = area.x + area.width / 2
        self.floating_y = area.y + 24
        if self.layer_shell:
            self.layer_shell.set_monitor(self, monitor)
            self.layer_shell.set_anchor(self, self.layer_shell.Edge.RIGHT, False)
        self.place_floating()

    def place_floating(self):
        if self.floating_center is None:
            return
        # Keep the same transparent shoulder space in both modes. Resizing
        # from a compact window to monitor width during snap caused flashes.
        width = self.notch.get_preferred_width()[1] + 48
        self.set_size_request(-1, -1)
        height = self.get_preferred_height()[1]
        if self.get_size() != (width, height):
            self.resize(width, height)
        x = round(self.floating_center - width / 2)
        if self.layer_shell:
            layer = self.layer_shell
            monitor = layer.get_monitor(self) or self.get_display().get_monitor(0)
            area = monitor.get_geometry()
            layer.set_margin(self, layer.Edge.LEFT, max(0, x - area.x))
            layer.set_margin(self, layer.Edge.TOP, max(0, self.floating_y - area.y))
        else:
            self.move(x, self.floating_y)

    def minimize_player(self, *_):
        if self.docked:
            return
        if not self.layer_shell:
            # Dock windows are normally excluded from the taskbar. Give the WM
            # a normal, restorable taskbar window before requesting minimize.
            self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
            self.set_skip_taskbar_hint(False)
            self.set_skip_pager_hint(False)
            self.iconify()
            return
        # Layer-shell surfaces cannot be minimized by the Wayland WM. A normal
        # taskbar window supplies the restore action while the layer is hidden.
        if self.restore_window:
            return
        restore = Gtk.Window(title='Notch Music')
        self.restore_window = restore
        restore.set_default_size(260, 70)
        icon = self.get_icon()
        if icon:
            restore.set_icon(icon)
        button = Gtk.Button(label='Kembalikan player')
        button.connect('clicked', self.restore_player)
        restore.add(button)
        restore.connect('delete-event', lambda *_: (self.restore_player(), True)[1])
        restore.connect('window-state-event', self.restore_window_state)
        self.hide()
        restore.show_all()
        GLib.idle_add(lambda: (restore.iconify(), False)[1] if self.restore_window is restore else False)

    def restore_window_state(self, widget, event):
        if (event.changed_mask & Gdk.WindowState.ICONIFIED
                and not event.new_window_state & Gdk.WindowState.ICONIFIED):
            self.restore_player()
        return False

    def restore_player(self, *_):
        restore, self.restore_window = self.restore_window, None
        if restore:
            restore.destroy()
        self.show()
        self.present()

    def toggle_dock_autohide(self, *_):
        if not self.docked:
            return
        self.dock_autohide = not self.dock_autohide
        self.autohide_wait_exit = self.dock_autohide
        self.hover_left_at = None
        self.body_revealer.set_reveal_child(not self.dock_autohide)
        self.update_dock_handle()

    def update_dock_handle(self):
        self.dock_handle.set_visible(self.docked)
        self.dock_handle.set_label('▴' if self.dock_autohide else '▾')
        self.dock_handle.set_tooltip_text(
            'Klik untuk tetap terbuka' if self.dock_autohide else 'Sembunyikan otomatis; arahkan pointer ke atas untuk membuka')

    def notch_pointer_crossing(self, widget, event, inside):
        # Child controls have their own input windows. Only a crossing of the
        # actual top-level surface means the pointer entered/left the player.
        if event.window == self.get_window() and event.detail != Gdk.NotifyType.INFERIOR:
            self.pointer_inside = inside
        return False

    def poll_notch_hover(self):
        if not self.docked or not self.dock_autohide or self.drag_origin is not None:
            return True
        if not self.get_mapped():
            return True
        inside = self.pointer_inside
        if not self.layer_shell:
            pointer = self.get_display().get_default_seat().get_pointer()
            _, x, y, _ = self.get_window().get_device_position(pointer)
            # XWayland may retain the last local coordinates after the pointer
            # moves to a native Wayland surface. Never let those stale values
            # override a real LeaveNotify from our top-level window.
            inside = inside and self.get_window().get_visible_region().contains_point(x, y)
            # Transparent shoulder space should not hold the notch open.
            allocation = self.notch.get_allocation()
            inside = inside and allocation.x <= x < allocation.x + allocation.width
        if self.autohide_wait_exit:
            if not inside:
                self.autohide_wait_exit = False
            return True
        if self.browse_open or self.player_menu.get_mapped() or inside:
            self.hover_left_at = None
            self.body_revealer.set_reveal_child(True)
        else:
            self.body_revealer.set_reveal_child(False)
        return True

    def start_move(self, widget, event):
        if event.button != 1:
            return False
        # Buttons and sliders handle their own events before the window.
        target = Gtk.get_event_widget(event)
        while target and target != self:
            if isinstance(target, (Gtk.Button, Gtk.Range, Gtk.Entry)):
                return False
            target = target.get_parent()
        if self.snap_tick is not None:
            self.remove_tick_callback(self.snap_tick)
            self.snap_tick = None
        allocation = self.notch.get_allocation()
        position = self.get_position()
        window_x, window_y = position
        if self.layer_shell:
            layer = self.layer_shell
            monitor = layer.get_monitor(self) or self.get_display().get_monitor(0)
            area = monitor.get_geometry()
            window_x = area.x + layer.get_margin(self, layer.Edge.LEFT)
            window_y = area.y + layer.get_margin(self, layer.Edge.TOP)
        self.drag_origin = (event.x_root, event.y_root,
                            window_x + allocation.x + allocation.width / 2,
                            window_y)
        self.grab_add()
        self.get_display().get_default_seat().grab(
            self.get_window(), Gdk.SeatCapabilities.POINTER, False, None, event, None, None)
        return True

    def move_player(self, widget, event):
        if self.drag_origin is None:
            return False
        start_x, start_y, center, y = self.drag_origin
        if self.docked:
            self.docked = False
            self.dock_autohide = False
            self.body_revealer.set_reveal_child(True)
            self.update_dock_handle()
            self.connection_progress = 0.0
            if self.bezel_bar:
                self.bezel_bar.hide()
            self.notch.get_style_context().remove_class('docked')
            self.notch.get_style_context().add_class('floating')
            self.update_panel_layout()
            if self.layer_shell:
                self.layer_shell.set_anchor(self, self.layer_shell.Edge.RIGHT, False)
        self.floating_center = center + event.x_root - start_x
        self.floating_y = round(y + event.y_root - start_y)
        self.place_floating()
        self.queue_draw()
        return True

    def finish_move(self, widget, event):
        if self.drag_origin is None or event.button != 1:
            return False
        self.drag_origin = None
        self.get_display().get_default_seat().ungrab()
        self.grab_remove()
        monitor = self.get_display().get_monitor_at_point(int(event.x_root), int(event.y_root))
        area = monitor.get_geometry()
        if self.floating_y <= area.y + 12:
            if self.layer_shell:
                self.layer_shell.set_monitor(self, monitor)
            self.animate_snap(area)
        self.queue_draw()
        return True

    def animate_snap(self, area):
        start_center, start_y = self.floating_center, self.floating_y
        target_center = area.x + area.width / 2
        started = GLib.get_monotonic_time()

        def frame(widget, clock):
            elapsed = max(0, clock.get_frame_time() - started)
            progress = min(1.0, elapsed / 220000)
            eased = 1 - (1 - progress) ** 3
            self.floating_center = start_center + (target_center - start_center) * eased
            self.floating_y = round(start_y + (area.y - start_y) * eased)
            self.place_floating()
            if progress >= 1:
                if not self.docked:
                    self.show_bezel_bar(area)
                    self.docked = True
                    self.set_type_hint(Gdk.WindowTypeHint.DOCK)
                    self.set_skip_taskbar_hint(True)
                    self.update_dock_handle()
                    self.update_panel_layout()
                self.docked = True
                self.connection_progress = min(1.0, (elapsed - 220000) / 180000)
                if self.bezel_bar is not None:
                    self.bezel_bar.set_opacity(self.connection_progress)
                self.notch.get_style_context().remove_class('floating')
                self.notch.get_style_context().add_class('docked')
            finished = elapsed >= 400000
            if finished:
                self.snap_tick = None
            self.queue_draw()
            return not finished

        self.snap_tick = self.add_tick_callback(frame)

    def show_bezel_bar(self, area):
        # Win32 can enlarge/reposition this two-pixel top-level window. Draw
        # the connection inside the shaped player instead of creating a
        # monitor-wide window there. Linux retains its existing bezel bar.
        if sys.platform == 'win32':
            return
        if self.bezel_bar is None:
            bar = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            self.bezel_bar = bar
            bar.set_decorated(False)
            bar.set_resizable(False)
            bar.set_accept_focus(False)
            bar.set_skip_taskbar_hint(True)
            bar.set_skip_pager_hint(True)
            bar.set_keep_above(True)
            bar.set_type_hint(Gdk.WindowTypeHint.DOCK)
            bar.set_app_paintable(True)
            visual = self.get_screen().get_rgba_visual()
            if visual:
                bar.set_visual(visual)

            def paint(widget, context):
                context.set_operator(cairo.OPERATOR_SOURCE)
                context.set_source_rgba(*THEMES[self.theme]['surface'])
                context.paint()
                return True

            bar.connect('draw', paint)
            # Decorative only: clicks still reach the desktop's top panel.
            bar.connect('map', lambda widget: widget.get_window().input_shape_combine_region(cairo.Region(), 0, 0))
            if self.layer_shell:
                layer = self.layer_shell
                anchor_window(bar, layer)
                layer.set_keyboard_mode(bar, layer.KeyboardMode.NONE)
        bar = self.bezel_bar
        bar.set_size_request(area.width, 2)
        bar.resize(area.width, 2)
        bar.set_opacity(0)
        if self.layer_shell:
            monitor = self.get_display().get_monitor_at_point(area.x, area.y)
            self.layer_shell.set_monitor(bar, monitor)
        else:
            bar.move(area.x, area.y)
        bar.show()

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
        if self.docked:
            hx, hy = self.dock_handle.translate_coordinates(self, 0, 0)
            region.union(cairo.RectangleInt(hx, hy, self.dock_handle.get_allocated_width(), self.dock_handle.get_allocated_height()))
            region.union(cairo.RectangleInt(x, 0, allocation.width, 3))
        region.intersect(cairo.RectangleInt(0, 0, self.get_allocated_width(), self.get_allocated_height()))
        window.input_shape_combine_region(region, 0, 0)
        if sys.platform == 'win32':
            shape = (x, y, allocation.width, allocation.height, self.docked, self.get_allocated_height())
            if getattr(self, '_window_shape', None) != shape:
                outline = window_shape(*shape[:5])
                if self.docked:
                    outline.union(cairo.RectangleInt(hx, hy, self.dock_handle.get_allocated_width(), self.dock_handle.get_allocated_height()))
                    outline.union(cairo.RectangleInt(x, 0, allocation.width, 3))
                outline.intersect(cairo.RectangleInt(0, 0, self.get_allocated_width(), self.get_allocated_height()))
                window.shape_combine_region(outline, 0, 0)
                self._window_shape = shape

    def draw_top_connection(self, widget, context):
        if sys.platform == 'win32':
            self.update_input_region()
        if not self.docked:
            return False
        coordinates = self.notch.translate_coordinates(self, 0, 0)
        if coordinates is None:
            return False
        x, y = coordinates
        right = x + self.notch.get_allocated_width()
        radius = max(0.01, 24 * self.connection_progress)
        bar_height = 2
        shoulder_y = y + bar_height
        context.save()
        context.set_antialias(cairo.ANTIALIAS_BEST)
        # Replace rather than blend overlapping edges, keeping the translucent
        # theme uniform where the shoulders meet the bar and the shell border.
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(*THEMES[self.theme]['surface'])
        context.rectangle(0, 0, self.get_allocated_width(), bar_height)
        context.fill()
        # Each arc meets the underside of the bar horizontally and the notch
        # side vertically, avoiding the old step at the two-pixel bar edge.
        context.move_to(x - radius, shoulder_y)
        context.line_to(x + 1, shoulder_y)
        context.line_to(x + 1, shoulder_y + radius)
        context.line_to(x, shoulder_y + radius)
        context.arc_negative(x - radius, shoulder_y + radius, radius, 0, -math.pi / 2)
        context.close_path()
        context.fill()
        context.move_to(right + radius, shoulder_y)
        context.line_to(right - 1, shoulder_y)
        context.line_to(right - 1, shoulder_y + radius)
        context.line_to(right, shoulder_y + radius)
        context.arc(right + radius, shoulder_y + radius, radius, math.pi, 3 * math.pi / 2)
        context.close_path()
        context.fill()
        context.restore()
        return False

    def fit_window(self):
        if self.get_realized():
            self.place_floating()
            minimum, natural = self.get_preferred_height()
            if self.get_size().height != natural:
                self.resize(self.get_size().width, natural)

    def panel_transition_finished(self, revealer, *_):
        if not revealer.get_reveal_child():
            revealer.hide()
        self.fit_window()

    def open_drawer(self, mode, title):
        if mode == 'queue':
            self.queue_enabled = True
            if self.docked:
                self.lyrics_enabled = False
            for child in self.drawer_content.get_children():
                child.destroy()
        else:
            self.lyrics_enabled = True
            if self.docked:
                self.queue_enabled = False
        self.drawer_title.set_text(title)
        self.update_panel_layout()

    def close_drawer(self):
        self.queue_enabled = False
        self.lyrics_enabled = False
        self.update_panel_layout()

    def update_panel_layout(self):
        # In notch mode retain one side panel; floating mode allows both.
        if self.docked and self.queue_enabled and self.lyrics_enabled:
            if self.drawer_mode == 'lyrics':
                self.queue_enabled = False
            else:
                self.lyrics_enabled = False
        self.drawer_mode = 'queue' if self.queue_enabled else ('lyrics' if self.lyrics_enabled else None)
        below = not self.docked
        self.notch.set_orientation(Gtk.Orientation.HORIZONTAL)
        parent = self.player_column if below else self.notch
        if self.drawer.get_parent() is not parent:
            self.drawer.get_parent().remove(self.drawer)
            parent.pack_start(self.drawer, False, False, 0)
            if parent is self.notch:
                parent.reorder_child(self.drawer, 1)
        self.panel_frame.set_orientation(Gtk.Orientation.VERTICAL if below else Gtk.Orientation.HORIZONTAL)
        self.drawer.set_transition_type(
            Gtk.RevealerTransitionType.SLIDE_DOWN if below else Gtk.RevealerTransitionType.SLIDE_RIGHT)
        self.player_widget.set_size_request(300 if self.lyrics_enabled or (self.docked and self.queue_enabled) else 350, 128)
        self.drawer_body.set_size_request(-1 if below else 245, 112)
        self.panel_divider.set_orientation(Gtk.Orientation.HORIZONTAL if below else Gtk.Orientation.VERTICAL)
        self.panel_divider.set_size_request(260 if below else 1, 1 if below else 64)
        self.panel_divider.set_halign(Gtk.Align.CENTER if below else Gtk.Align.FILL)
        self.panel_divider.set_valign(Gtk.Align.FILL if below else Gtk.Align.CENTER)
        context = self.panel_divider.get_style_context()
        context.add_class('horizontal') if below else context.remove_class('horizontal')
        for revealer, enabled in ((self.drawer, self.queue_enabled), (self.lyric_drawer, self.lyrics_enabled)):
            if enabled:
                revealer.get_child().show_all()
                revealer.show()
            revealer.set_reveal_child(enabled)
            if not enabled and not revealer.get_child_revealed():
                revealer.hide()
        self.lyric_stack.set_visible_child_name('expanded' if below and self.queue_enabled and self.lyrics_enabled else 'compact')
        self.drawer_heading.hide()
        for button, enabled in ((self.queue_button, self.queue_enabled), (self.lyrics_button, self.lyrics_enabled)):
            context = button.get_style_context()
            context.add_class('enabled') if enabled else context.remove_class('enabled')
        self.lyrics_button.set_tooltip_text('Lirik: ' + ('aktif' if self.lyrics_enabled else 'mati'))
        if self.queue_ui_ready:
            self.update_queue_height()
        visualizer_height = 44 if below and self.queue_enabled and self.lyrics_enabled else 30
        self.visualizer_top.set_size_request(-1, visualizer_height)
        self.visualizer_bottom.set_size_request(-1, visualizer_height)
        if self.spectrum:
            self.spectrum.set_property('post-messages', self.lyrics_enabled)
        if self.lyrics_enabled:
            ok, position = self.player.query_position(Gst.Format.TIME)
            self.update_lyrics(position / Gst.SECOND if ok else 0)
        self.sync_menu_state()

    def animate_visualizer(self, widget, clock):
        now = clock.get_frame_time()
        if now - self.visualizer_frame_time < 30000:
            return True
        self.visualizer_frame_time = now
        audible = self.playing and not self.muted and self.volume.get_value() > 0
        fresh = GLib.get_monotonic_time() - self.visualizer_updated < 300000
        for index, current in enumerate(self.visualizer_levels):
            target = self.visualizer_target[index] if audible and fresh else 0
            smoothing = .55 if target > current else .18
            self.visualizer_levels[index] += (target - current) * smoothing
        self.visualizer_top.queue_draw()
        self.visualizer_bottom.queue_draw()
        return True

    def draw_visualizer(self, widget, context, top):
        width, height = widget.get_allocated_width(), widget.get_allocated_height()
        color = self.title.get_style_context().get_color(Gtk.StateFlags.NORMAL)
        step = width / len(self.visualizer_levels)
        bar_width = max(1, step * .72)
        baseline = height * .72
        segment, gap = 2, 1
        for index, level in enumerate(self.visualizer_levels):
            edge = .55 + .45 * math.sin(math.pi * (index + .5) / len(self.visualizer_levels))
            strength = max(0, min(1, level)) ** .65
            count = max(1, round(strength * edge * (baseline - 2) / (segment + gap)))
            x = index * step + (step - bar_width) / 2
            for cell in range(count):
                y = baseline - (cell + 1) * (segment + gap)
                opacity = .30 + .60 * strength
                context.set_source_rgba(color.red, color.green, color.blue, opacity)
                context.rectangle(x, y, bar_width, segment)
                context.fill()
                # A shorter, fading reflection below the spectrum's baseline.
                reflected_y = baseline + cell * (segment + gap) * .38
                fade = max(0, 1 - (reflected_y - baseline) / max(1, height - baseline))
                context.set_source_rgba(color.red, color.green, color.blue, opacity * .32 * fade)
                context.rectangle(x, reflected_y, bar_width, max(1, segment * .38))
                context.fill()
        return False

    def update_queue_height(self):
        if not self.docked:
            rows = self.listing.get_children()[:5]
            height = max(1, sum(row.get_preferred_height()[1] for row in rows))
        else:
            height = 60
        self.queue_scroll.set_min_content_height(0)
        self.queue_scroll.set_max_content_height(height)
        self.queue_scroll.set_min_content_height(height)

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
        if getattr(self, 'bezel_bar', None):
            self.bezel_bar.queue_draw()
        ok, position = self.player.query_position(Gst.Format.TIME)
        if self.lyric_lines or self.plain_lyrics:
            self.update_lyrics(position / Gst.SECOND if ok else 0)
        self.update_theme_icon()
        self.sync_menu_state()
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.settings_path.with_suffix('.tmp')
            temporary.write_text(json.dumps({'theme': theme}) + '\n')
            temporary.replace(self.settings_path)
        except OSError:
            self.status.set_text('Tema diterapkan, tetapi pilihan tidak dapat disimpan.')

    def open_files(self, *_, playlist_target=None):
        self.browse_open = True
        dialog = Gtk.FileChooserDialog(title='Tambahkan musik', transient_for=self,
                                       action=Gtk.FileChooserAction.OPEN)
        # A custom response keeps Select enabled even with no file selected.
        dialog.add_buttons('Batal', Gtk.ResponseType.CANCEL, 'Select', 100)
        dialog.set_default_response(100)
        dialog.set_select_multiple(True)
        selected_files = prepare_file_selection(dialog)
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
            files, folders = resolve_selection(selected_files(), dialog.get_current_folder())
            dialog.destroy()
            if files:
                self.add_files(files, playlist_target=playlist_target)
            if folders:
                self.scan_folders(folders, playlist_target=playlist_target)
        else:
            dialog.destroy()
        self.browse_open = False

    def report_problem(self, message):
        previous = self.browse_open
        self.browse_open = True
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.CLOSE, text='Notch Music')
        dialog.format_secondary_text(message)
        try:
            dialog.run()
        finally:
            dialog.destroy()
            self.browse_open = previous

    def check_track_file(self, path):
        try:
            with path.open('rb'):
                pass
        except FileNotFoundError:
            self.report_problem(f'File tidak ditemukan di direktori asal:\n{path}\n\nFile mungkin sudah dipindahkan atau dihapus.')
            return False
        except OSError as error:
            self.report_problem(f'Tidak dapat membaca file:\n{path}\n\n{error.strerror or error}')
            return False
        return True

    def create_playlist(self, *_):
        self.playlist_tracks = []
        self.playlist_name = 'Playlist baru'
        self.playlist_file = None
        self.show_queue(force=True, playlist=True)

    def playlist_filter(self):
        file_filter = Gtk.FileFilter()
        file_filter.set_name(f'Notch Music Playlist (*{PLAYLIST_EXTENSION})')
        file_filter.add_pattern('*' + PLAYLIST_EXTENSION)
        file_filter.add_pattern('*' + PLAYLIST_EXTENSION.upper())
        return file_filter

    def load_playlist_dialog(self, *_):
        self.browse_open = True
        dialog = Gtk.FileChooserDialog(title='Load Playlist', transient_for=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons('Batal', Gtk.ResponseType.CANCEL, 'Load Playlist', Gtk.ResponseType.ACCEPT)
        dialog.add_filter(self.playlist_filter())
        dialog.set_default_size(800, 520)
        filename = None
        try:
            if dialog.run() == Gtk.ResponseType.ACCEPT:
                filename = dialog.get_filename()
        finally:
            dialog.destroy()
            self.browse_open = False
        if filename:
            self.load_playlist_file(filename)

    def load_playlist_file(self, filename):
        try:
            name, tracks = load_playlist(filename)
        except (OSError, ValueError) as error:
            self.report_problem(f'Tidak dapat membuka playlist:\n{filename}\n\n{error}')
            return False
        self.playlist_name, self.playlist_tracks = Path(filename).stem, tracks
        self.playlist_file = Path(filename).resolve()
        self.show_queue(force=True, playlist=True)
        self.index_queue_metadata()
        missing = sum(not path.is_file() for path in tracks)
        if missing:
            self.playlist_message(f'{missing} file tidak ditemukan. Klik play untuk melihat lokasi asalnya.')
        return True

    def playlist_message(self, message):
        if self.playlist_editing and self.queue_enabled:
            self.playlist_notice.set_text(message)
            self.playlist_notice.set_tooltip_text(message)
            self.playlist_notice.show()

    def save_playlist_dialog(self, *_):
        if self.playlist_file:
            self.save_playlist_file(self.playlist_file)
            return
        self.browse_open = True
        dialog = Gtk.FileChooserDialog(title='Save Playlist', transient_for=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons('Batal', Gtk.ResponseType.CANCEL, 'Save Playlist', Gtk.ResponseType.ACCEPT)
        dialog.set_do_overwrite_confirmation(True)
        dialog.add_filter(self.playlist_filter())
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '-', self.playlist_name).strip(' .') or 'Playlist'
        dialog.set_current_name(name + PLAYLIST_EXTENSION)
        filename = None
        try:
            if dialog.run() == Gtk.ResponseType.ACCEPT:
                filename = dialog.get_filename()
        finally:
            dialog.destroy()
            self.browse_open = False
        if filename:
            if not filename.lower().endswith(PLAYLIST_EXTENSION):
                filename += PLAYLIST_EXTENSION
                # The chooser only confirmed the name before the suffix was
                # added. Do not silently overwrite a different existing file.
                if Path(filename).exists():
                    self.report_problem(f'File sudah ada:\n{filename}\n\nSimpan lagi dengan nama lengkap beserta {PLAYLIST_EXTENSION} untuk mengonfirmasi penggantian.')
                    return
            self.save_playlist_file(filename)

    def save_playlist_file(self, filename):
        try:
            name = Path(filename).stem.strip()
            save_playlist(filename, name, self.playlist_tracks)
        except (OSError, ValueError) as error:
            self.report_problem(f'Tidak dapat menyimpan playlist:\n{filename}\n\n{error}')
            return False
        self.playlist_name = name
        self.playlist_title_label.set_text(name)
        self.playlist_title_label.set_tooltip_text(name)
        self.playlist_file = Path(filename).resolve()
        self.playlist_message(f'Tersimpan: {self.playlist_file.name}')
        return True

    def play_visible_track(self, index):
        if not self.playlist_editing:
            return self.load(index)
        if not 0 <= index < len(self.playlist_tracks):
            return False
        if not self.check_track_file(self.playlist_tracks[index]):
            return False
        self.queue = list(self.playlist_tracks)
        self.history.clear()
        self.shuffle_remaining = list(range(len(self.queue)))
        return self.load(index)

    def remove_visible_track(self, index):
        if not self.playlist_editing:
            return self.remove_track(index)
        if 0 <= index < len(self.playlist_tracks):
            self.playlist_tracks.pop(index)
            self.refresh_queue()

    def scan_folders(self, folders, playlist_target=None):
        self.status.set_text('Memindai folder…')
        def scan():
            files = []
            for folder in folders:
                for directory, subdirs, names in os.walk(folder):
                    subdirs.sort(key=str.casefold)
                    files.extend(Path(directory) / name for name in sorted(names, key=str.casefold)
                                 if Path(name).suffix.lower() in AUDIO)
            GLib.idle_add(self.folder_scanned, files, playlist_target)
        threading.Thread(target=scan, daemon=True).start()

    def folder_scanned(self, files, playlist_target=None):
        self.add_files(files, playlist_target=playlist_target)
        if not files:
            self.status.set_text('Tidak ada file musik di folder')
        return False

    def add_files(self, files, playlist_target=None):
        if playlist_target is not None:
            for filename in files:
                path = Path(filename).expanduser().resolve()
                if path.is_file() and path.suffix.lower() in AUDIO:
                    playlist_target.append(path)
            self.index_queue_metadata()
            if self.drawer_mode == 'queue':
                self.refresh_queue()
            return
        for filename in files:
            path = Path(filename).expanduser().resolve()
            if path.is_file() and path.suffix.lower() in AUDIO:
                self.queue.append(path)
                if self.shuffle:
                    self.shuffle_remaining.insert(random.randrange(len(self.shuffle_remaining) + 1), len(self.queue) - 1)
        if self.index < 0 and self.queue:
            self.load(0)
        self.index_queue_metadata()
        self.update_status()
        if self.drawer_mode == 'queue':
            self.refresh_queue()

    def update_status(self):
        self.status.set_text(f'{len(self.queue)} lagu dalam antrean' if self.queue else 'Musikmu, selalu dekat.')

    def load(self, index):
        if not 0 <= index < len(self.queue):
            return False
        if not self.check_track_file(self.queue[index]):
            return False
        self.player.set_state(Gst.State.NULL)
        self.index = index
        self.shuffle_remaining = [i for i in self.shuffle_remaining if i != index]
        self.duration = 0
        path = self.queue[index]
        self.title.set_text(path.stem)
        self.artist.set_text(path.parent.name)
        self.audio_info.set_text(path.suffix.lstrip('.').upper())
        self.cover.set_from_icon_name('audio-x-generic', Gtk.IconSize.DIALOG)
        self.lyric_lines, self.plain_lyrics = [], []
        self.lyrics.set_text('Membaca lirik…')
        def read():
            metadata = read_metadata(path)
            metadata['audio_info'] = read_audio_info(path)
            GLib.idle_add(self.apply_metadata, path, metadata)
        threading.Thread(target=read, daemon=True).start()
        self.player.set_property('uri', path.as_uri())
        self.player.set_state(Gst.State.PLAYING)
        self.playing = True
        self.sync_play_icons()
        if self.drawer_mode == 'queue':
            self.mark_current_track()
        return True

    def apply_metadata(self, path, metadata):
        if not 0 <= self.index < len(self.queue) or self.queue[self.index] != path:
            return False
        if metadata.get('audio_info'):
            details = format_audio_info(metadata['audio_info'])
            self.audio_info.set_text(details)
            self.audio_info.set_tooltip_text(details)
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
                loader.set_size(44, 44)
                loader.write(metadata['picture'])
                loader.close()
                self.cover.set_from_pixbuf(loader.get_pixbuf())
            except GLib.Error:
                pass
        return False

    def update_lyrics(self, seconds):
        if not self.lyrics_enabled:
            return
        self.lyric_position = seconds
        if self.lyric_lines:
            import bisect
            index = bisect.bisect_right([t for t, _ in self.lyric_lines], seconds) - 1
            # Replace the current sentence at its next timestamp; never show
            # a preview row or invent timing for lyrics without timestamps.
            text = self.lyric_lines[max(0, index)][1]
            escaped = GLib.markup_escape_text(text.replace('\n', ' '))
            if index >= 0:
                self.lyrics.set_markup(f'<span weight="bold">{escaped}</span>')
            else:
                self.lyrics.set_markup(escaped)
        else:
            self.lyrics.set_text(next(iter(self.plain_lyrics), 'Lirik tidak tersedia'))

    def update_lyric_context(self):
        if not self.lyric_lines:
            self.lyric_context.set_text(self.lyrics.get_text())
            return
        import bisect
        index = bisect.bisect_right([t for t, _ in self.lyric_lines], self.lyric_position) - 1
        start = max(0, index)
        # Drop elapsed sentences and advance the upcoming lines at real LRC
        # timestamps; the compact view still shows just the active sentence.
        count = max(2, min(6, (self.player_column.get_allocated_height() - 100) // 48))
        lines = []
        for line_index in range(start, min(len(self.lyric_lines), start + count)):
            text = GLib.markup_escape_text(self.lyric_lines[line_index][1].replace('\n', ' '))
            lines.append(f'<b>{text}</b>' if line_index == index else text)
        self.lyric_context.set_markup('\n\n'.join(lines))

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
        self.sync_menu_state()

    def toggle_repeat(self, *_):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        icon = 'media-playlist-repeat-song-symbolic' if self.repeat_mode == 1 else 'media-playlist-repeat-symbolic'
        self.repeat_button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))
        context = self.repeat_button.get_style_context()
        context.add_class('enabled') if self.repeat_mode else context.remove_class('enabled')
        self.repeat_button.set_tooltip_text('Repeat: ' + ['mati', 'satu lagu', 'semua lagu'][self.repeat_mode])

    def toggle_lyrics(self, *_):
        if self.lyrics_enabled:
            self.lyrics_enabled = False
            self.update_panel_layout()
            return
        self.open_drawer('lyrics', 'Lirik')
        ok, position = self.player.query_position(Gst.Format.TIME)
        if self.lyric_lines or self.plain_lyrics:
            self.update_lyrics(position / Gst.SECOND if ok else 0)
        else:
            self.lyrics.set_text('Lirik tidak tersedia' if self.queue else 'Lirik akan tampil di sini')

    def reset_player(self):
        self.player.set_state(Gst.State.NULL)
        self.index = -1
        self.playing = False
        self.duration = 0
        self.lyric_lines, self.plain_lyrics = [], []
        self.title.set_text('Belum ada lagu')
        self.artist.set_text('Buka musik untuk mulai mendengarkan')
        self.audio_info.set_text('Format audio')
        self.audio_info.set_tooltip_text(None)
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
        if message.type == Gst.MessageType.ELEMENT:
            structure = message.get_structure()
            if structure and structure.get_name() == 'spectrum' and message.src == self.spectrum:
                # GstValueList lacks a Python converter on some distro builds.
                # The typed serialization is portable across GI installations.
                values = re.search(r'magnitude=\(float\)\{([^}]+)\}', structure.to_string())
                if values:
                    levels = [max(0, min(1, (float(value) + 72) / 72)) for value in values[1].split(',')]
                    if len(levels) == 32:
                        self.visualizer_target = levels
                        self.visualizer_updated = GLib.get_monotonic_time()
        elif message.type == Gst.MessageType.EOS:
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

    def index_queue_metadata(self):
        sources = self.queue + (self.playlist_tracks if self.playlist_editing else [])
        pending = [path for path in dict.fromkeys(sources)
                   if path not in self.queue_metadata and path not in self.metadata_pending]
        if not pending:
            return
        self.metadata_pending.update(pending)
        def read():
            results = {}
            for path in pending:
                metadata = read_metadata(path)
                results[path] = {key: metadata[key] for key in ('title', 'artist')}
            GLib.idle_add(self.queue_metadata_ready, results)
        threading.Thread(target=read, daemon=True).start()

    def queue_metadata_ready(self, results):
        self.queue_metadata.update(results)
        self.metadata_pending.difference_update(results)
        if self.drawer_mode == 'queue':
            self.refresh_queue()
        return False

    def focus_search(self, widget=None, event=None):
        if self.drawer_mode != 'queue':
            return False
        self.set_accept_focus(True)
        timestamp = event.time if event is not None else Gtk.get_current_event_time()
        if not self.layer_shell:
            # Dock-style windows can remain unfocused on X11/XWayland unless
            # explicitly activated following the user's click.
            self.present_with_time(timestamp)
            if self.get_window():
                self.get_window().focus(timestamp)
        if self.playlist_editing:
            self.listing.grab_focus()
        else:
            self.search.grab_focus()
        return False

    def on_search_changed(self, entry):
        if self.drawer_mode == 'queue' and self.queue_ui_ready and entry is self.search:
            self.refresh_queue()
            self.queue_scroll.get_vadjustment().set_value(0)

    def activate_search_result(self, entry):
        tracks = self.playlist_tracks if getattr(self, 'playlist_editing', False) else self.queue
        matches = search_tracks(tracks, entry.get_text(), self.queue_metadata)
        if matches:
            if getattr(self, 'playlist_editing', False):
                self.play_visible_track(matches[0][0])
            else:
                self.load(matches[0][0])

    def show_queue(self, *_, force=False, playlist=False):
        if self.queue_enabled and not force and self.playlist_editing == playlist:
            self.queue_enabled = False
            self.update_panel_layout()
            return
        self.queue_ui_ready = False
        self.playlist_editing = playlist
        self.open_drawer('queue', 'Playlist' if playlist else 'Antrean musik')
        actions = Gtk.Box(spacing=3)
        if playlist:
            self.playlist_title_label = Gtk.Label(label=self.playlist_name, xalign=0)
            self.playlist_title_label.set_ellipsize(Pango.EllipsizeMode.END)
            self.playlist_title_label.set_max_width_chars(20)
            self.playlist_title_label.set_tooltip_text(self.playlist_name)
            self.playlist_title_label.get_style_context().add_class('track-title')
            actions.pack_start(self.playlist_title_label, True, True, 0)
            self.playlist_add_button = self.icon_button(actions, 'list-add-symbolic', 'Tambah lagu ke playlist',
                lambda *_: self.open_files(playlist_target=self.playlist_tracks))
            self.playlist_save_button = self.icon_button(actions, 'media-floppy-symbolic', 'Save Playlist', self.save_playlist_dialog)
            self.playlist_add_button.get_image().set_pixel_size(16)
            self.playlist_save_button.get_image().set_pixel_size(16)
        else:
            self.button(actions, 'Clear', 'Kosongkan antrean (file musik tetap tersimpan)', self.clear_queue)
        self.drawer_content.pack_start(actions, False, False, 0)
        self.search = Gtk.SearchEntry()
        self.search.set_width_chars(14)
        self.search.set_max_width_chars(14)
        self.search.set_placeholder_text('Cari lagu atau artis…')
        self.search.connect('changed', self.on_search_changed)
        self.search.connect('activate', self.activate_search_result)
        self.search.connect('button-press-event', self.focus_search)
        if not playlist:
            actions.pack_start(self.search, True, True, 0)
            actions.reorder_child(self.search, 0)
        self.playlist_notice = Gtk.Label(xalign=0)
        self.playlist_notice.set_name('drawer-subtitle')
        self.playlist_notice.set_ellipsize(Pango.EllipsizeMode.END)
        self.playlist_notice.set_max_width_chars(26)
        self.playlist_notice.set_no_show_all(True)
        self.drawer_content.pack_start(self.playlist_notice, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        self.queue_scroll = scroll
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_overlay_scrolling(False)
        scroll.set_min_content_height(60)
        scroll.set_max_content_height(60)
        self.listing = Gtk.ListBox()
        self.listing.set_margin_end(4)
        self.listing.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listing.set_activate_on_single_click(True)
        self.listing.connect('row-activated', lambda box, row: self.play_visible_track(row.track_index) if hasattr(row, 'track_index') else None)
        scroll.add(self.listing)
        self.drawer_content.pack_start(scroll, False, False, 0)
        self.queue_ui_ready = True
        self.refresh_queue()
        self.drawer_content.show_all()
        self.update_panel_layout()
        GLib.idle_add(self.focus_search)

    def mark_current_track(self):
        for row in self.listing.get_children():
            if not isinstance(row, Gtk.ListBoxRow) or not hasattr(row, 'track_index'):
                continue
            context = row.get_style_context()
            current = (0 <= self.index < len(self.queue) and
                       (self.playlist_tracks[row.track_index] == self.queue[self.index]
                        if self.playlist_editing else row.track_index == self.index))
            if current:
                context.add_class('current-track')
                row.play_button.get_style_context().add_class('enabled')
            else:
                context.remove_class('current-track')
                row.play_button.get_style_context().remove_class('enabled')

    def refresh_queue(self):
        self.queue_generation += 1
        generation = self.queue_generation
        for row in self.listing.get_children():
            row.destroy()
        query = self.search.get_text().strip()
        tracks = self.playlist_tracks if self.playlist_editing else self.queue
        matches = search_tracks(tracks, query, self.queue_metadata)
        rows = []
        for index, path in matches[:100]:
            row = Gtk.ListBoxRow()
            row.track_index = index
            box = Gtk.Box(spacing=6)
            row.add(box)
            image = Gtk.Image.new_from_icon_name('audio-x-generic', Gtk.IconSize.LARGE_TOOLBAR)
            image.set_size_request(24, 24)
            box.pack_start(image, False, False, 0)
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            box.pack_start(text, True, True, 0)
            title, artist = track_details(path, self.queue_metadata.get(path, {}))
            name = Gtk.Label(label=title, xalign=0)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            name.set_max_width_chars(40)
            name.get_style_context().add_class('track-title')
            text.pack_start(name, False, False, 0)
            missing = self.playlist_editing and not path.is_file()
            row.set_tooltip_text(f'File tidak ditemukan di direktori asal:\n{path}' if missing else str(path))
            subtitle = Gtk.Label(label='File tidak ditemukan' if missing else artist, xalign=0)
            subtitle.set_ellipsize(Pango.EllipsizeMode.END)
            subtitle.set_max_width_chars(40)
            subtitle.get_style_context().add_class('track-artist')
            text.pack_start(subtitle, False, False, 0)
            self.icon_button(box, 'edit-delete-symbolic', 'Hapus dari playlist' if self.playlist_editing else 'Hapus dari antrean',
                             lambda button, track=index: self.remove_visible_track(track))
            row.play_button = self.icon_button(
                box, 'media-playback-start-symbolic', 'Putar lagu ini',
                lambda button, track=index: self.play_visible_track(track))
            self.listing.add(row)
            rows.append((path, image))
        if not matches:
            empty = Gtk.Label(label='Tidak ada lagu yang cocok.' if query else ('Playlist kosong. Tambahkan lewat ＋\natau seret lagu ke sini.' if self.playlist_editing else 'Antrean kosong. Tambahkan musik lewat ＋.'))
            empty.set_margin_top(25)
            empty.set_margin_bottom(25)
            self.listing.add(empty)
        self.status.set_text(f'{len(matches)} lagu' + (' · menampilkan 100 pertama, gunakan pencarian' if len(matches) > 100 else ''))
        self.mark_current_track()
        self.listing.show_all()
        self.update_queue_height()
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
            loader.set_size(24, 24)
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
        target = self.playlist_tracks if self.playlist_editing and self.queue_enabled else None
        files = [path for path in paths if Path(path).is_file()]
        folders = [Path(path) for path in paths if Path(path).is_dir()]
        self.add_files(files, playlist_target=target)
        if folders:
            self.scan_folders(folders, playlist_target=target)
        Gtk.drag_finish(context, bool(paths), False, timestamp)

    def keypress(self, widget, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            action = {Gdk.KEY_o: self.open_files, Gdk.KEY_O: self.open_files,
                      Gdk.KEY_l: self.toggle_lyrics, Gdk.KEY_L: self.toggle_lyrics,
                      Gdk.KEY_k: self.show_queue, Gdk.KEY_K: self.show_queue}.get(event.keyval)
            if action:
                action()
                return True
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
        self.mpris.close()
        GLib.source_remove(self.hover_source)
        if self.restore_window:
            self.restore_window.destroy()
        if self.bezel_bar:
            self.bezel_bar.destroy()
        self.player.set_state(Gst.State.NULL)
        if Gtk.main_level():
            Gtk.main_quit()


if __name__ == '__main__':
    if not Gtk.init_check()[0]:
        sys.exit('Tidak dapat membuka desktop. Jalankan dari sesi desktop Windows atau Linux yang aktif.')
    display = Gdk.Display.get_default()
    if ('Wayland' in type(display).__name__ and not get_layer_shell()
            and os.environ.get('DISPLAY') and not os.environ.get('NOTCH_GDK_BACKEND')
            and os.environ.get('GDK_BACKEND') != 'x11'):
        os.environ['GDK_BACKEND'] = 'x11'
        os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])
    window = Notch(sys.argv[1:])
    window.show_all()
    Gtk.main()

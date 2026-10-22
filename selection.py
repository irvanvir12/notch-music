"""Resolve the file chooser's Select action without requiring a selection."""
from pathlib import Path

AUDIO = {'.mp3', '.flac', '.ogg', '.opus', '.wav', '.m4a', '.aac', '.wma'}


def resolve_selection(filenames, current_folder):
    paths = [Path(name) for name in filenames]
    songs = [p for p in paths if p.is_file() and p.suffix.lower() in AUDIO]
    folders = [p for p in paths if p.is_dir()]
    if songs:
        return songs, folders
    return [], folders or ([Path(current_folder)] if current_folder else [])


def prepare_file_selection(dialog, select_response=100):
    """Keep GTK's automatic cursor selection separate from user selection.

    Returns a getter for files deliberately selected via pointer or keyboard.
    Folder changes reset intent so Select alone always imports that folder.
    """
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk, GLib
    state = {'explicit': False, 'clearing': False}

    def clear_automatic(*_):
        if not state['explicit'] and not state['clearing']:
            state['clearing'] = True
            try:
                dialog.unselect_all()
            finally:
                state['clearing'] = False
        return False

    def pointer_selection(tree, event):
        if event.window == tree.get_bin_window() and tree.get_path_at_pos(int(event.x), int(event.y)):
            state['explicit'] = True
        return False

    def keyboard_selection(tree, event):
        selection_keys = (Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Home, Gdk.KEY_End,
                          Gdk.KEY_Page_Up, Gdk.KEY_Page_Down, Gdk.KEY_space,
                          Gdk.KEY_KP_Up, Gdk.KEY_KP_Down, Gdk.KEY_KP_Home, Gdk.KEY_KP_End)
        if event.keyval in selection_keys or (event.state & Gdk.ModifierType.CONTROL_MASK
                                              and event.keyval in (Gdk.KEY_a, Gdk.KEY_A)):
            state['explicit'] = True
        return False

    def bind_file_lists(widget):
        if isinstance(widget, Gtk.TreeView) and not getattr(widget, '_notch_selection_guard', False):
            widget._notch_selection_guard = True
            widget.connect('button-press-event', pointer_selection)
            widget.connect('key-press-event', keyboard_selection)
        if isinstance(widget, Gtk.Container):
            for child in widget.get_children():
                bind_file_lists(child)

    def folder_ready():
        if dialog.get_visible():
            bind_file_lists(dialog)
            clear_automatic()
            button = dialog.get_widget_for_response(select_response)
            if button and not state['explicit']:
                button.grab_focus()
        return False

    def folder_changed(*_):
        state['explicit'] = False
        clear_automatic()
        GLib.idle_add(folder_ready)

    def dialog_keypress(widget, event):
        if (event.state & Gdk.ModifierType.CONTROL_MASK
                and event.keyval in (Gdk.KEY_a, Gdk.KEY_A)
                and not isinstance(dialog.get_focus(), (Gtk.Entry, Gtk.TextView))):
            state['explicit'] = True
        return False

    dialog.connect('key-press-event', dialog_keypress)
    dialog.connect('selection-changed', clear_automatic)
    dialog.connect('current-folder-changed', folder_changed)
    dialog.connect('map', folder_changed)
    bind_file_lists(dialog)
    return lambda: dialog.get_filenames() if state['explicit'] else []

"""Select a GTK backend and optionally anchor the player using Wayland layer-shell."""
import os


def choose_backend(environment, layer_shell_available):
    override = environment.get('NOTCH_GDK_BACKEND') or environment.get('GDK_BACKEND')
    if override:
        return override
    desktop = environment.get('XDG_CURRENT_DESKTOP', '').casefold()
    wayland = environment.get('WAYLAND_DISPLAY') or environment.get('XDG_SESSION_TYPE') == 'wayland'
    if wayland and layer_shell_available and not any(name in desktop for name in ('gnome', 'zorin')):
        return 'wayland,x11'
    return 'x11'


def configure_backend():
    import gi
    try:
        gi.require_version('GtkLayerShell', '0.1')
        available = True
    except ValueError:
        available = False
    os.environ['GDK_BACKEND'] = choose_backend(os.environ, available)


def get_layer_shell():
    import gi
    try:
        gi.require_version('GtkLayerShell', '0.1')
        from gi.repository import GtkLayerShell
        return GtkLayerShell if GtkLayerShell.is_supported() else None
    except (ImportError, ValueError):
        return None


def anchor_window(window, layer):
    layer.init_for_window(window)
    layer.set_namespace(window, 'notch-music')
    layer.set_layer(window, layer.Layer.TOP)
    for edge in (layer.Edge.TOP, layer.Edge.LEFT, layer.Edge.RIGHT):
        layer.set_anchor(window, edge, True)
        layer.set_margin(window, edge, 0)
    layer.set_exclusive_zone(window, 0)
    layer.set_keyboard_mode(window, layer.KeyboardMode.ON_DEMAND)

"""Select a GTK backend and optionally anchor the player using Wayland layer-shell."""
import os
import sys


def choose_backend(environment, layer_shell_available, platform='linux'):
    override = environment.get('NOTCH_GDK_BACKEND') or environment.get('GDK_BACKEND')
    if override:
        return override
    if platform == 'win32':
        return 'win32'
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
    os.environ['GDK_BACKEND'] = choose_backend(os.environ, available, sys.platform)


def get_layer_shell():
    if sys.platform == 'win32':
        return None
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


def window_shape(x, y, width, height, docked):
    """Clip the Win32 window where a compositor cannot supply an RGBA visual."""
    import math
    import cairo
    region = cairo.Region()
    top_radius = 0 if docked else 20
    bottom_radius = 16 if docked else 20
    for row in range(height):
        inset = 0
        if row < top_radius:
            inset = math.ceil(top_radius - math.sqrt(max(0, top_radius ** 2 - (top_radius - row - .5) ** 2)))
        elif row >= height - bottom_radius:
            inset = math.ceil(bottom_radius - math.sqrt(max(0, bottom_radius ** 2 - (row - (height - bottom_radius) + .5) ** 2)))
        region.union(cairo.RectangleInt(x + inset, y + row, max(1, width - 2 * inset), 1))
    if docked:
        region.union(cairo.RectangleInt(0, 0, x + width + 24, 2))
        for row in range(24):
            extension = 24 - math.ceil(math.sqrt(max(0, 24 ** 2 - (24 - row - .5) ** 2)))
            if extension:
                region.union(cairo.RectangleInt(x - extension, y + row + 2, extension, 1))
                region.union(cairo.RectangleInt(x + width, y + row + 2, extension, 1))
    return region

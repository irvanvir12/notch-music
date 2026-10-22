#!/usr/bin/env python3
"""Register an existing AppImage and its original logo for the current user."""
import argparse
import os
import subprocess
from pathlib import Path

import gi
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf, GLib


def install(appimage):
    appimage = Path(appimage).expanduser().resolve(strict=True)
    if not appimage.is_file():
        raise ValueError('AppImage must be a file')
    logo = Path(__file__).resolve().parents[1] / 'assets/notch-music-logo-v2.png'
    data = Path(GLib.get_user_data_dir())
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(logo))
    for size in (32, 48, 64, 128, 256, 512):
        target = data / f'icons/hicolor/{size}x{size}/apps/notch-music.png'
        target.parent.mkdir(parents=True, exist_ok=True)
        pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.HYPER).savev(str(target), 'png', [], [])
    icon = data / 'icons/hicolor/256x256/apps/notch-music.png'
    appimage.chmod(appimage.stat().st_mode | 0o111)
    # Quote the executable as one argument, including paths containing spaces.
    executable = str(appimage).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    launcher = data / 'applications/notch-music.desktop'
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text('[Desktop Entry]\nType=Application\nName=Notch Music\n'
                        'Comment=Compact desktop music player with synchronized lyrics\n'
                        f'Exec="{executable}" %F\nIcon={icon}\n'
                        'Terminal=false\nCategories=AudioVideo;Audio;Player;\n'
                        'MimeType=audio/flac;audio/mpeg;audio/ogg;audio/x-wav;\n')
    subprocess.run(['update-desktop-database', str(launcher.parent)], check=False)
    result = subprocess.run(['gio', 'set', str(appimage), 'metadata::custom-icon', icon.as_uri()],
                            capture_output=True, text=True)
    print(f'Launcher: {launcher}')
    print(f'Icon: {icon}')
    if result.returncode:
        print('File-manager custom icon unavailable: ' + result.stderr.strip())
    else:
        print('AppImage file icon set successfully.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('appimage', help='Path to the AppImage to register')
    args = parser.parse_args()
    install(args.appimage)

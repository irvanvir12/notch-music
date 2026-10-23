#!/usr/bin/env python3
"""Build an x86_64 AppImage using the native Ubuntu 24.04/Zorin 18 libraries."""
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'packaging'
OUT = ROOT / 'dist'
RUNTIME = PACK / 'tools/runtime-x86_64'
if platform.machine() != 'x86_64':
    sys.exit('This build targets x86_64 only.')
if not RUNTIME.is_file():
    sys.exit('Download the official type2 runtime to packaging/tools/runtime-x86_64 first.')
OUT.mkdir(exist_ok=True)
LIB = Path('/usr/lib/x86_64-linux-gnu')
VERSION = f'python{sys.version_info.major}.{sys.version_info.minor}'
BASE_LIBS = ['libgtk-3.so.0', 'libgdk-3.so.0', 'libgirepository-1.0.so.1',
             'libgstreamer-1.0.so.0', 'libgsttag-1.0.so.0', 'libgstpbutils-1.0.so.0',
             'libgstapp-1.0.so.0', 'libgdk_pixbuf-2.0.so.0', 'libpangoft2-1.0.so.0']
if (LIB / 'libgtk-layer-shell.so.0').is_file():
    BASE_LIBS.append('libgtk-layer-shell.so.0')
# The host supplies glibc, its loader and device-specific graphics drivers.
EXCLUDE = re.compile(r'^(ld-linux|lib(c|m|dl|pthread|rt|resolv|util|nss_[^.]+)\.so)')

with tempfile.TemporaryDirectory(prefix='notch-appimage-') as work:
    app = Path(work) / 'NotchMusic.AppDir'
    for folder in ('usr/bin', 'usr/lib', 'usr/share/notch-music', 'usr/share/applications', 'usr/share/icons/hicolor/scalable/apps'):
        (app / folder).mkdir(parents=True, exist_ok=True)
    def copy(source, target):
        source, target = Path(source), Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=True)
    def tree(source, target, ignore=None):
        shutil.copytree(source, target, dirs_exist_ok=True, symlinks=False, ignore=ignore)
    ignore = shutil.ignore_patterns('__pycache__', 'test', 'tests', '*.pyc', 'ensurepip', 'idlelib', 'tkinter')
    copy('/usr/bin/python3', app / 'usr/bin/python3')
    tree(Path('/usr/lib') / VERSION, app / 'usr/lib' / VERSION, ignore)
    for package in ('gi', 'cairo'):
        tree(Path('/usr/lib/python3/dist-packages') / package,
             app / 'usr/lib/python3/dist-packages' / package, ignore)
    tree(LIB / 'girepository-1.0', app / 'usr/lib/girepository-1.0')
    tree(LIB / 'gstreamer-1.0', app / 'usr/lib/gstreamer-1.0')
    tree(LIB / 'gdk-pixbuf-2.0/2.10.0/loaders', app / 'usr/lib/gdk-pixbuf/loaders')
    copy(LIB / 'gstreamer1.0/gstreamer-1.0/gst-plugin-scanner', app / 'usr/bin/gst-plugin-scanner')
    copy(LIB / 'gdk-pixbuf-2.0/gdk-pixbuf-query-loaders', app / 'usr/bin/gdk-pixbuf-query-loaders')
    for name in ('icons/Adwaita', 'icons/hicolor', 'glib-2.0/schemas', 'mime', 'themes/Default'):
        if (Path('/usr/share') / name).is_dir():
            tree(Path('/usr/share') / name, app / 'usr/share' / name)
    for name in ('notch_music.py', 'metadata.py', 'playlists.py', 'selection.py', 'themes.py', 'desktop_support.py'):
        copy(ROOT / name, app / 'usr/share/notch-music' / name)
    copy(PACK / 'packaged_check.py', app / 'usr/share/notch-music/packaged_check.py')
    copy(PACK / 'AppRun', app / 'AppRun')
    (app / 'AppRun').chmod(0o755)
    copy(PACK / 'notch-music.desktop', app / 'notch-music.desktop')
    copy(PACK / 'notch-music.desktop', app / 'usr/share/applications/notch-music.desktop')
    icon = ROOT / 'assets/notch-music-logo-v2.png'
    copy(icon, app / 'notch-music.png')
    copy(icon, app / '.DirIcon')
    copy(icon, app / 'usr/share/icons/hicolor/256x256/apps/notch-music.png')
    copy(icon, app / 'usr/share/notch-music/assets/notch-music-logo-v2.png')
    (app / 'usr/bin/notch-music').symlink_to('../../AppRun')
    seeds = [Path('/usr/bin/python3')] + [LIB / name for name in BASE_LIBS]
    seeds += list((LIB / 'gstreamer-1.0').glob('*.so'))
    seeds += list((LIB / 'gdk-pixbuf-2.0/2.10.0/loaders').glob('*.so'))
    seeds += list((app / 'usr/lib').rglob('*.so'))
    seeds += list((app / 'usr/bin').iterdir())[:-1]
    checked, bundled = set(), set()
    # ldd reports the complete dependency closure for each ELF; separately
    # seed libraries GTK/GStreamer load dynamically via introspection/plugins.
    unique_seeds = []
    for source in seeds:
        if source.is_file() and source.resolve() not in checked:
            checked.add(source.resolve())
            unique_seeds.append(source)
    def dependencies(source):
        result = subprocess.run(['ldd', str(source)], capture_output=True, text=True)
        libraries = []
        for line in result.stdout.splitlines():
            if 'not found' in line:
                raise RuntimeError(f'{source}: {line}')
            match = re.search(r'=> (/\S+)', line)
            if match:
                library = Path(match[1])
                if not EXCLUDE.match(library.name):
                    libraries.append(library)
        return libraries
    with ThreadPoolExecutor(max_workers=8) as executor:
        for libraries in executor.map(dependencies, unique_seeds):
            for library in libraries:
                if library not in bundled:
                    copy(library, app / 'usr/lib' / library.name)
                    bundled.add(library)
    for name in BASE_LIBS:
        copy(LIB / name, app / 'usr/lib' / name)
        bundled.add((LIB / name).resolve())
    # Keep Debian copyright/license notices for redistributed packages.
    copyright_dir = app / 'usr/share/doc/notch-music/bundled-copyright'
    package_names = set()
    result = subprocess.run(['dpkg-query', '-S', *map(str, bundled | {Path('/usr/bin/python3.12')})],
                            capture_output=True, text=True)
    for line in result.stdout.splitlines():
        package_names.add(line.split(': ')[0].split(':')[0])
    package_names.update({'python3.12', 'python3-gi', 'python3-cairo', 'adwaita-icon-theme',
                          'gstreamer1.0-plugins-base', 'gstreamer1.0-plugins-good', 'gstreamer1.0-libav'})
    for package in sorted(package_names):
        source = Path('/usr/share/doc') / package / 'copyright'
        if source.is_file():
            copy(source, copyright_dir / f'{package}.txt')
    print(f'Bundled {len(bundled)} shared libraries. Packing AppImage…', flush=True)
    payload = Path(work) / 'payload.squashfs'
    subprocess.run(['mksquashfs', str(app), str(payload), '-noappend', '-comp', 'zstd', '-processors', '2', '-quiet'], check=True)
    output = OUT / 'Notch-Music-x86_64.AppImage'
    with output.open('wb') as dest:
        for source in (RUNTIME, payload):
            with source.open('rb') as src:
                shutil.copyfileobj(src, dest)
    output.chmod(0o755)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    (OUT / (output.name + '.sha256')).write_text(f'{checksum}  {output.name}\n')
    (OUT / 'build-info.json').write_text(json.dumps({'architecture': 'x86_64', 'base': 'Ubuntu 24.04 / Zorin OS 18',
        'minimum_glibc': '2.39', 'runtime_sha256': hashlib.sha256(RUNTIME.read_bytes()).hexdigest(),
        'appimage_sha256': checksum, 'size_bytes': output.stat().st_size}, indent=2) + '\n')
    print(f'Created {output} ({output.stat().st_size / 1024 / 1024:.1f} MiB)')

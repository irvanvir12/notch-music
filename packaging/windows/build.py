"""Build a portable x64 ZIP using native MSYS2 UCRT64 Python on Windows."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def build():
    if sys.platform != 'win32' or os.environ.get('MSYSTEM') != 'UCRT64':
        raise SystemExit('Run with native /ucrt64/bin/python in the MSYS2 UCRT64 shell on Windows.')
    prefix = Path(sys.prefix)
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='notch-win-build-') as temporary:
        bundle = Path(temporary) / 'Notch-Music-Windows-x64'
        runtime = bundle / 'runtime'
        binaries = runtime / 'bin'
        binaries.mkdir(parents=True)
        for source in (prefix / 'bin').glob('*.dll'):
            shutil.copy2(source, binaries / source.name)
        for pattern in ('python*.exe', 'gspawn*helper*.exe', 'gdk-pixbuf-query-loaders.exe'):
            for source in (prefix / 'bin').glob(pattern):
                shutil.copy2(source, binaries / source.name)
        for name in ('lib/girepository-1.0', 'lib/gstreamer-1.0', 'lib/gdk-pixbuf-2.0',
                     'lib/gio', 'libexec/gstreamer-1.0', 'share/glib-2.0/schemas',
                     'share/icons/Adwaita', 'share/icons/AdwaitaLegacy', 'share/icons/hicolor',
                     'share/themes/Default', 'share/mime', 'share/licenses', 'etc/fonts'):
            source = prefix / name
            if source.exists():
                shutil.copytree(source, runtime / name, ignore=shutil.ignore_patterns('*.a', '*.la', '__pycache__'))
        for source in (prefix / 'lib').glob('python3*'):
            if source.is_dir():
                shutil.copytree(source, runtime / 'lib' / source.name,
                                ignore=shutil.ignore_patterns('__pycache__', 'test', 'tests', '*.a'))
        config = runtime / 'etc/gtk-3.0'
        config.mkdir(parents=True, exist_ok=True)
        (config / 'settings.ini').write_text('[Settings]\ngtk-theme-name=Adwaita\ngtk-font-name=Segoe UI 9\n', encoding='utf-8')
        app = bundle / 'app'
        app.mkdir()
        for name in ('notch_music.py', 'metadata.py', 'selection.py', 'themes.py', 'desktop_support.py'):
            shutil.copy2(ROOT / name, app / name)
        (app / 'assets').mkdir()
        shutil.copy2(ROOT / 'assets/notch-music-logo-v2.png', app / 'assets/notch-music-logo-v2.png')
        shutil.copy2(ROOT / 'packaging/windows/bootstrap.py', app / 'bootstrap.py')
        shutil.copy2(ROOT / 'packaging/windows/smoke_test.py', app / 'windows_smoke_test.py')
        shutil.copy2(ROOT / 'README.md', bundle / 'README.md')
        shutil.copy2(ROOT / 'VERSION', bundle / 'VERSION')
        from gi.repository import GdkPixbuf
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(app / 'assets/notch-music-logo-v2.png'), 256, 256, True)
        png = Path(temporary) / 'icon.png'
        pixbuf.savev(str(png), 'png', [], [])
        data = png.read_bytes()
        icon = Path(temporary) / 'icon.ico'
        icon.write_bytes(struct.pack('<HHHBBBBHHII', 0, 1, 1, 0, 0, 0, 0, 1, 32, len(data), 22) + data)
        resource = Path(temporary) / 'icon.rc'
        resource.write_text(f'1 ICON "{icon.as_posix()}"\n', encoding='utf-8')
        compiled_resource = Path(temporary) / 'icon.o'
        subprocess.run(['windres', str(resource), str(compiled_resource)], check=True)
        subprocess.run(['gcc', '-municode', '-mwindows', '-O2', '-s', '-static-libgcc',
                        str(ROOT / 'packaging/windows/launcher.c'), str(compiled_resource),
                        '-o', str(bundle / 'Notch-Music.exe')], check=True)
        # Launch outside MSYS2's DLL/data paths: catches missing bundled dependencies.
        environment = {key: value for key, value in os.environ.items() if key.upper() in {
            'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LOCALAPPDATA', 'APPDATA', 'USERPROFILE',
            'HOMEDRIVE', 'HOMEPATH', 'COMSPEC', 'NUMBER_OF_PROCESSORS'}}
        environment['PATH'] = str(Path(os.environ['SYSTEMROOT']) / 'System32')
        subprocess.run([str(binaries / 'python.exe'), str(app / 'bootstrap.py'), '--self-test'],
                       env=environment, cwd=bundle, check=True, timeout=90)
        packages = subprocess.check_output(['pacman', '-Q'], text=True)
        (bundle / 'build-info.json').write_text(json.dumps({
            'version': (ROOT / 'VERSION').read_text().strip(), 'platform': 'Windows x64 UCRT64',
            'packages': packages.splitlines(), 'runtime_smoke_test': 'passed',
        }, indent=2), encoding='utf-8')
        archive = Path(shutil.make_archive(str(out / bundle.name), 'zip', bundle.parent, bundle.name))
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
        print(f'Created {archive}')


if __name__ == '__main__':
    build()

"""Start the bundled native Win32 GTK runtime without requiring MSYS2."""
import os
from pathlib import Path
import runpy
import subprocess
import sys
import traceback


def main():
    root = Path(__file__).resolve().parent.parent
    runtime = root / 'runtime'
    app = root / 'app'
    cache = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Notch Music'
    cache.mkdir(parents=True, exist_ok=True)
    handles = []
    for folder in (runtime / 'bin', runtime / 'lib/gstreamer-1.0'):
        if hasattr(os, 'add_dll_directory'):
            handles.append(os.add_dll_directory(str(folder)))
    os.environ.update({
        'PATH': str(runtime / 'bin') + os.pathsep + os.environ.get('PATH', ''),
        'GDK_BACKEND': 'win32',
        'NOTCH_GDK_BACKEND': 'win32',
        'GI_TYPELIB_PATH': str(runtime / 'lib/girepository-1.0'),
        'XDG_DATA_DIRS': str(runtime / 'share'),
        'GTK_DATA_PREFIX': str(runtime),
        'GTK_EXE_PREFIX': str(runtime),
        'GSETTINGS_SCHEMA_DIR': str(runtime / 'share/glib-2.0/schemas'),
        'FONTCONFIG_PATH': str(runtime / 'etc/fonts'),
        'FONTCONFIG_FILE': str(runtime / 'etc/fonts/fonts.conf'),
        'GST_PLUGIN_PATH': '',
        'GST_PLUGIN_SYSTEM_PATH': str(runtime / 'lib/gstreamer-1.0'),
        'GST_REGISTRY': str(cache / 'gstreamer-registry.bin'),
    })
    scanner = runtime / 'libexec/gstreamer-1.0/gst-plugin-scanner.exe'
    if scanner.exists():
        os.environ['GST_PLUGIN_SCANNER'] = str(scanner)
    query = runtime / 'bin/gdk-pixbuf-query-loaders.exe'
    if query.exists():
        loaders = list((runtime / 'lib/gdk-pixbuf-2.0').glob('*/loaders/*.dll'))
        if loaders:
            result = subprocess.run([str(query), *map(str, loaders)], capture_output=True, check=True)
            loader_cache = cache / 'pixbuf-loaders.cache'
            loader_cache.write_bytes(result.stdout)
            os.environ['GDK_PIXBUF_MODULE_FILE'] = str(loader_cache)
    sys.path.insert(0, str(app))
    if '--self-test' in sys.argv[1:]:
        runpy.run_path(str(app / 'windows_smoke_test.py'), run_name='__main__')
    else:
        runpy.run_path(str(app / 'notch_music.py'), run_name='__main__')
    return handles  # Keep the DLL directory handles alive through the GTK loop.


if __name__ == '__main__':
    if '--self-test' in sys.argv[1:]:
        main()
    else:
        root = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Notch Music'
        root.mkdir(parents=True, exist_ok=True)
        with (root / 'notch-music.log').open('a', encoding='utf-8', buffering=1) as log:
            sys.stdout = sys.stderr = log
            try:
                main()
            except Exception:
                traceback.print_exc()
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, f'Gagal membuka player. Detail: {root / "notch-music.log"}',
                                               'Notch Music', 0x10)
                raise

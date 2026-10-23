"""Local playlist documents store references to audio files, never audio data."""
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import tempfile

EXTENSION = '.notchplaylist'
FORMAT = 'notch-music-playlist'


def load_playlist(filename):
    path = Path(filename)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError('File playlist terlalu besar (maksimal 5 MB).')
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('File playlist rusak atau bukan format Notch Music.') from error
    if (not isinstance(data, dict) or data.get('format') != FORMAT
            or type(data.get('version')) is not int or data['version'] != 1):
        raise ValueError('Format atau versi playlist tidak didukung.')
    name, tracks = data.get('name'), data.get('tracks')
    if not isinstance(name, str) or not name.strip() or len(name) > 128:
        raise ValueError('Nama playlist tidak valid.')
    if not isinstance(tracks, list) or len(tracks) > 10000:
        raise ValueError('Daftar lagu tidak valid (maksimal 10.000 lagu).')
    result = []
    for track in tracks:
        if not isinstance(track, str) or not track or '\0' in track:
            raise ValueError('Direktori lagu di dalam playlist tidak valid.')
        if not (PurePosixPath(track).is_absolute() or PureWindowsPath(track).is_absolute()):
            raise ValueError('Playlist harus menyimpan direktori asal lagu secara lengkap.')
        # Missing paths remain visible so the user can see and fix/remove them.
        result.append(Path(track))
    return name.strip(), result


def save_playlist(filename, name, tracks):
    name = name.strip()
    if not name or len(name) > 128:
        raise ValueError('Isi nama playlist terlebih dahulu (maksimal 128 karakter).')
    if len(tracks) > 10000:
        raise ValueError('Playlist maksimal berisi 10.000 lagu.')
    path = Path(filename)
    paths = []
    for track in tracks:
        value = str(track)
        if not (PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()):
            value = str(Path(track).expanduser().resolve())
        paths.append(value)
    document = {'format': FORMAT, 'version': 1, 'name': name, 'tracks': paths}
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name + '.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

"""Read native FLAC pictures, Vorbis lyrics, and adjacent LRC files offline."""
import re
import struct
from pathlib import Path


def read_metadata(filename):
    path = Path(filename)
    result = {'title': '', 'artist': '', 'lyrics': '', 'picture': None}
    try:
        with path.open('rb') as stream:
            if stream.read(4) == b'fLaC':
                while True:
                    header = stream.read(4)
                    if len(header) != 4:
                        break
                    size = int.from_bytes(header[1:], 'big')
                    block = stream.read(size)
                    if len(block) != size:
                        break
                    kind = header[0] & 127
                    if kind == 4:
                        offset = 0
                        def integer():
                            nonlocal offset
                            value = struct.unpack_from('<I', block, offset)[0]
                            offset += 4
                            return value
                        offset = 4 + integer()
                        count = integer()
                        for _ in range(count):
                            length = integer()
                            entry = block[offset:offset + length].decode('utf-8', 'replace')
                            offset += length
                            key, sep, value = entry.partition('=')
                            key = key.lower()
                            if sep and key in ('title', 'artist'):
                                result[key] = value
                            elif sep and key in ('lyrics', 'unsyncedlyrics', 'unsynced lyrics', 'syncedlyrics', 'synchronisedlyrics'):
                                result['lyrics'] = value
                    elif kind == 6:
                        offset = 0
                        def integer():
                            nonlocal offset
                            value = struct.unpack_from('>I', block, offset)[0]
                            offset += 4
                            return value
                        picture_type = integer()
                        length = integer()
                        mime = block[offset:offset + length]
                        offset += length
                        length = integer()
                        offset += length + 16  # description, width, height, depth, colors
                        length = integer()
                        picture = block[offset:offset + length]
                        if mime != b'-->' and picture and (result['picture'] is None or picture_type == 3):
                            result['picture'] = picture
                    if header[0] & 128:
                        break
    except (OSError, ValueError, struct.error):
        pass
    if not result['lyrics']:
        for extension in ('.lrc', '.LRC', '.txt'):
            try:
                result['lyrics'] = path.with_suffix(extension).read_text(encoding='utf-8-sig')
                break
            except (OSError, UnicodeError):
                pass
    return result


def parse_lyrics(text):
    timed, plain = [], []
    offset = re.search(r'\[offset:([+-]?\d+)\]', text, re.I)
    shift = int(offset[1]) / 1000 if offset else 0
    for line in text.splitlines():
        stamps = re.findall(r'\[(\d+):(\d+(?:\.\d+)?)\]', line)
        words = re.sub(r'\[[^\]]*\]', '', line).strip()
        if stamps:
            timed.extend((int(m) * 60 + float(s) + shift, words) for m, s in stamps)
        elif words:
            plain.append(words)
    return sorted(timed), plain

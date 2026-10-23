"""Read native FLAC pictures, Vorbis lyrics, and adjacent LRC files offline."""
import re
import struct
from pathlib import Path


def read_audio_info(filename):
    """Read source precision, never the decoder's output PCM precision."""
    path = Path(filename)
    info = {'format': path.suffix.lstrip('.').upper(), 'depth': 0, 'rate': 0, 'bitrate': 0}
    try:
        with path.open('rb') as stream:
            header = stream.read(12)
            if header[:4] == b'fLaC':
                stream.seek(4)
                block_header = stream.read(4)
                if len(block_header) == 4 and block_header[0] & 127 == 0:
                    block = stream.read(int.from_bytes(block_header[1:], 'big'))
                    if len(block) >= 18:
                        packed = int.from_bytes(block[10:18], 'big')
                        info.update(format='FLAC', rate=packed >> 44, depth=((packed >> 36) & 31) + 1)
            elif header[:4] in (b'RIFF', b'RF64') and header[8:] == b'WAVE':
                info['format'] = 'WAV'
                while True:
                    chunk = stream.read(8)
                    if len(chunk) != 8:
                        break
                    length = int.from_bytes(chunk[4:], 'little')
                    if chunk[:4] == b'fmt ':
                        block = stream.read(min(length, 40))
                        if len(block) >= 16:
                            info['rate'] = int.from_bytes(block[4:8], 'little')
                            info['depth'] = int.from_bytes(block[14:16], 'little')
                            if block[:2] == b'\xfe\xff' and len(block) >= 20:
                                info['depth'] = int.from_bytes(block[18:20], 'little') or info['depth']
                        break
                    stream.seek(length + length % 2, 1)
    except OSError:
        return info
    if info['rate']:
        return info
    try:
        import gi
        gi.require_version('Gst', '1.0')
        gi.require_version('GstPbutils', '1.0')
        from gi.repository import Gst, GstPbutils
        Gst.init(None)
        discovery = GstPbutils.Discoverer.new(3 * Gst.SECOND).discover_uri(path.resolve().as_uri())
        audio = discovery.get_audio_streams()
        if audio:
            info['rate'] = audio[0].get_sample_rate()
            info['bitrate'] = audio[0].get_bitrate()
            if info['format'] in ('FLAC', 'WAV', 'AIFF', 'AIF', 'ALAC'):
                info['depth'] = audio[0].get_depth()
    except (ImportError, ValueError, RuntimeError):
        pass
    except Exception:
        # Unsupported/corrupt streams must not stop playback or metadata loading.
        pass
    return info


def format_audio_info(info):
    parts = [info['format']]
    if info.get('depth'):
        parts.append(f"{info['depth']}-bit")
    elif info.get('bitrate'):
        parts.append(f"{round(info['bitrate'] / 1000)} kbps")
    if info.get('rate'):
        parts.append(f"{info['rate'] / 1000:g} kHz")
    return ' · '.join(parts)


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

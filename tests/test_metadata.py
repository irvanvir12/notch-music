import struct
import tempfile
import unittest
from pathlib import Path
from metadata import read_metadata, parse_lyrics, read_audio_info, format_audio_info


class MetadataTests(unittest.TestCase):
    def test_flac_source_precision(self):
        packed = (48000 << 44) | (1 << 41) | (23 << 36) | 48000
        block = bytes(10) + packed.to_bytes(8, 'big') + bytes(16)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audio.flac'
            path.write_bytes(b'fLaC\x80\x00\x00\x22' + block)
            self.assertEqual(format_audio_info(read_audio_info(path)), 'FLAC · 24-bit · 48 kHz')

    def test_wav_source_precision(self):
        fmt = struct.pack('<HHIIHH', 1, 2, 44100, 264600, 6, 24)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audio.wav'
            path.write_bytes(b'RIFF' + struct.pack('<I', 36) + b'WAVEfmt ' + struct.pack('<I', 16) + fmt)
            self.assertEqual(format_audio_info(read_audio_info(path)), 'WAV · 24-bit · 44.1 kHz')

    def test_lossy_format_shows_bitrate_without_inventing_bit_depth(self):
        self.assertEqual(format_audio_info({'format': 'MP3', 'bitrate': 320000, 'rate': 48000}),
                         'MP3 · 320 kbps · 48 kHz')
        self.assertEqual(format_audio_info({'format': 'MP3'}), 'MP3')

    def test_flac_comments_and_cover(self):
        comments = [b'TITLE=Example', b'ARTIST=Someone', b'LYRICS=[00:01.00]Hello\n[00:02.00]World']
        block = struct.pack('<I', 4) + b'test' + struct.pack('<I', len(comments))
        block += b''.join(struct.pack('<I', len(c)) + c for c in comments)
        picture = struct.pack('>II', 3, 9) + b'image/png' + struct.pack('>IIIII', 0, 72, 72, 24, 0)
        picture += struct.pack('>I', 5) + b'image'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sample.flac'
            path.write_bytes(b'fLaC' + bytes([4]) + len(block).to_bytes(3, 'big') + block
                             + bytes([128 | 6]) + len(picture).to_bytes(3, 'big') + picture)
            result = read_metadata(path)
        self.assertEqual(result['title'], 'Example')
        self.assertEqual(result['artist'], 'Someone')
        self.assertEqual(result['picture'], b'image')
        self.assertEqual(parse_lyrics(result['lyrics'])[0], [(1., 'Hello'), (2., 'World')])

    def test_lrc_fallback_and_offset(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sample.flac'
            path.write_bytes(b'fLaC\x84\x00\x00\x01x')
            path.with_suffix('.lrc').write_text('[offset:-500]\n[00:01.00][00:03.00]Hello')
            result = read_metadata(path)
        self.assertEqual(parse_lyrics(result['lyrics'])[0], [(.5, 'Hello'), (2.5, 'Hello')])

    def test_plain_lyrics(self):
        self.assertEqual(parse_lyrics('First line\nSecond line'), ([], ['First line', 'Second line']))


if __name__ == '__main__':
    unittest.main()

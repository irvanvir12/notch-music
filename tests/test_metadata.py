import struct
import tempfile
import unittest
from pathlib import Path
from metadata import read_metadata, parse_lyrics


class MetadataTests(unittest.TestCase):
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

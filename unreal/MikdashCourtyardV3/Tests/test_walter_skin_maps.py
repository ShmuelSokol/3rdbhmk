"""Verify extraction refuses corrupt, truncated and mismatched texture inputs."""
import io
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import extract_walter_skin_maps as E


def png(color):
    stream = io.BytesIO()
    Image.new('RGB', (1024, 1024), color).save(stream, format='PNG')
    return stream.getvalue()


class TextureTests(unittest.TestCase):
    def test_png_parser_preserves_bytes_and_refuses_damage(self):
        image = png((150, 90, 70))
        self.assertEqual(E.png_at(b'prefix' + image + b'suffix', 6), image)
        for broken in (image[:-12], image[:30] + bytes([image[30] ^ 1]) + image[31:]):
            with self.assertRaises(ValueError):
                E.png_at(broken, 0)

    def test_extract_matches_reference_and_never_overwrites(self):
        images = [png(c) for c in ((150, 90, 70), (128, 128, 255), (10, 20, 30))]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preset, reference, target = root / 'preset', root / 'albedo.png', root / 'textures'
            preset.write_bytes(b'package' + b'padding'.join(images))
            reference.write_bytes(images[0])
            report = E.extract(target, preset, reference)
            self.assertTrue(report['reviewedAlbedoPixelsMatch'])
            for row, expected in zip(report['textures'], images):
                self.assertEqual((target / row['file']).read_bytes(), expected)
            with self.assertRaises(FileExistsError):
                E.extract(target, preset, reference)
            reference.write_bytes(png((1, 2, 3)))
            with self.assertRaises(ValueError):
                E.extract(root / 'bad', preset, reference)
            self.assertFalse((root / 'bad').exists())

    def test_refuses_missing_maps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            preset = root / 'preset'
            preset.write_bytes(png((1, 2, 3)))
            with self.assertRaises(ValueError):
                E.extract(root / 'out', preset, root / 'unused')


if __name__ == '__main__':
    unittest.main()

"""Extract the approved preset's embedded skin PNGs without loading Unreal.

Validate every PNG chunk CRC and match the previously reviewed albedo before
assigning normal/cavity roles from the recorded FaceV5 preset order.
"""
import argparse
import hashlib
import io
import json
import struct
import zlib
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PRESET = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Plugins/MetaHuman/MetaHumanCharacter/Content/Optional/Presets/Walter.uasset')
ALBEDO_PIXELS_SHA = '6757ae8756a813bb553b146c8f61e1dc99f120dcc3a859ec3280b28d38833bc2'
SIGNATURE = b'\x89PNG\r\n\x1a\n'


def png_at(data, start):
    if data[start:start + 8] != SIGNATURE:
        raise ValueError('Missing PNG signature')
    offset, first = start + 8, True
    while offset + 12 <= len(data):
        size, kind = struct.unpack_from('>I4s', data, offset)
        end = offset + 12 + size
        if end > len(data):
            raise ValueError('Truncated PNG chunk')
        if first and (kind != b'IHDR' or size != 13):
            raise ValueError('Invalid initial PNG header')
        first = False
        actual = zlib.crc32(data[offset + 4:offset + 8 + size]) & 0xffffffff
        expected = struct.unpack_from('>I', data, offset + 8 + size)[0]
        if actual != expected:
            raise ValueError('PNG chunk CRC mismatch')
        if kind == b'IEND':
            if size != 0:
                raise ValueError('Invalid IEND size')
            return data[start:end]
        offset = end
    raise ValueError('Missing PNG end')


def extract(destination, preset=PRESET, albedo=None):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('Texture destination must be fresh')
    data = Path(preset).read_bytes()
    images, cursor = [], 0
    while True:
        start = data.find(SIGNATURE, cursor)
        if start < 0:
            break
        png = png_at(data, start)
        with Image.open(io.BytesIO(png)) as im:
            im.load()
            if im.size != (1024, 1024):
                raise ValueError('Unexpected preset map dimensions')
        images.append(png)
        cursor = start + len(png)
    if len(images) != 3:
        raise ValueError('Expected exactly three preset maps, got %d' % len(images))
    expected_pixels_sha = ALBEDO_PIXELS_SHA
    if albedo is not None:
        with Image.open(albedo) as reference:
            expected_pixels_sha = hashlib.sha256(reference.convert('RGB').tobytes()).hexdigest()
    with Image.open(io.BytesIO(images[0])) as found:
        actual_pixels_sha = hashlib.sha256(found.convert('RGB').tobytes()).hexdigest()
        if actual_pixels_sha != expected_pixels_sha:
            raise ValueError('Preset albedo differs from reviewed Walter selection')
    report = {'presetSha256': hashlib.sha256(data).hexdigest(),
              'reviewedAlbedoPixelsMatch': True,
              'reviewedAlbedoPixelsSha256': expected_pixels_sha,
              'roleSource': 'FaceV5/casting/casting-evidence.json: embedded order albedo, normal, cavity',
              'status': 'extracted-native-import-and-render-review-pending', 'textures': []}
    destination.mkdir(parents=True, exist_ok=False)
    for role, png in zip(('Albedo', 'Normal', 'Cavity'), images):
        name = 'T_KohenWalter_' + role + '_V2.png'
        (destination / name).write_bytes(png)
        report['textures'].append({'file': name, 'role': role, 'width': 1024, 'height': 1024,
                                   'sha256': hashlib.sha256(png).hexdigest(),
                                   'sRGB': role == 'Albedo'})
    (destination / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(extract(args.out), indent=2))

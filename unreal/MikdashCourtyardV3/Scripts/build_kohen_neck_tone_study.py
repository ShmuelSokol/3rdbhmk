"""Create a fresh, color-only Kohen neck correction study; never edit the source GLB.

The approved Walter face atlas contains a pale neck strip. Match that strip to the
measured jaw color in linear RGB, smoothly below the jaw, retaining local variation.
Native skin material integration and rendered review are still required.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from measure_pilgrim_walk import read_glb, read_accessor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'SourceAssets/characters-review/KohenGadolV1/meshes/SK_KohenGadol_V1.glb'
SOURCE_SHA = '173a0971089f20e9685a4c80b5c55c0ea214e2b55f4bf910b91e3a916685a09c'


def correct(heights, colors):
    heights, colors = np.asarray(heights), np.asarray(colors, dtype=np.float64)
    jaw = (heights >= 156.0) & (heights < 163.0)
    neck = heights < 150.0
    if not jaw.any() or not neck.any():
        raise ValueError('Approved jaw and lower-neck regions must both be present')
    jaw_mean, neck_mean = colors[jaw, :3].mean(axis=0), colors[neck, :3].mean(axis=0)
    if not np.isfinite(colors).all() or np.any(neck_mean <= 0):
        raise ValueError('Invalid linear skin colors')
    gain = jaw_mean / neck_mean
    if np.any(gain < .25) or np.any(gain > 2):
        raise ValueError('Unexpected neck/jaw mismatch; refuse automatic correction')
    blend = np.clip((156.0 - heights) / 6.0, 0, 1)
    blend = blend * blend * (3 - 2 * blend)
    result = colors.copy()
    result[:, :3] *= 1 + blend[:, None] * (gain - 1)
    if np.any(result < 0) or np.any(result > 1):
        raise ValueError('Correction leaves the valid linear-color range')
    return result, {'jawMeanLinearRGB': jaw_mean.tolist(),
                    'lowerNeckBeforeLinearRGB': neck_mean.tolist(),
                    'lowerNeckAfterLinearRGB': result[neck, :3].mean(axis=0).tolist(),
                    'gainRGB': gain.tolist(), 'fullCorrectionBelowCm': 150.0,
                    'unchangedAtAndAboveCm': 156.0,
                    'affectedVertices': int((blend > 0).sum())}


def build(destination, source=SOURCE):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError('Study destination must be fresh: ' + str(destination))
    original = source.read_bytes()
    if hashlib.sha256(original).hexdigest() != SOURCE_SHA:
        raise ValueError('Source is not the approved Walter GLB; remeasure before proceeding')
    doc, binary = read_glb(source)
    primitives = [p for m in doc['meshes'] for p in m['primitives']
                  if doc['materials'][p['material']]['name'] == 'KG_MHHead']
    if len(primitives) != 1:
        raise ValueError('Expected exactly one head primitive')
    attrs = primitives[0]['attributes']
    positions = np.asarray(read_accessor(doc, binary, attrs['POSITION']))
    colors = np.asarray(read_accessor(doc, binary, attrs['COLOR_0']))
    adjusted, report = correct(positions[:, 1] * 100, colors)
    accessor = doc['accessors'][attrs['COLOR_0']]
    view = doc['bufferViews'][accessor['bufferView']]
    if accessor['componentType'] != 5126 or accessor['type'] != 'VEC4' or 'sparse' in accessor:
        raise ValueError('Expected dense float32 RGBA head colors')
    offset, bin_start = 12, None
    while offset < len(original):
        size, kind = struct.unpack_from('<I4s', original, offset)
        if kind == b'BIN\x00':
            bin_start = offset + 8
            break
        offset += 8 + size
    if bin_start is None:
        raise ValueError('No embedded GLB binary chunk')
    base = bin_start + view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
    stride = view.get('byteStride', 16)
    output = bytearray(original)
    allowed = np.zeros(len(output), dtype=bool)
    for i, color in enumerate(adjusted):
        if positions[i, 1] * 100 >= 156.0:
            continue
        start = base + i * stride
        struct.pack_into('<3f', output, start, *color[:3])
        allowed[start:start + 12] = True
    changed = np.frombuffer(original, dtype=np.uint8) != np.frombuffer(output, dtype=np.uint8)
    if np.any(changed & ~allowed) or not changed.any():
        raise ValueError('Color-only byte preservation failed')
    report.update({'status': 'offline-study-native-review-pending',
                   'sourceSha256': SOURCE_SHA,
                   'outputSha256': hashlib.sha256(output).hexdigest(),
                   'bytesChanged': int(changed.sum()),
                   'onlyBelowJawHeadRGBBytesChanged': True,
                   'limits': 'No geometry, normals, UVs, skin weights, alpha or other material colors changed. Not imported, packaged or visually accepted.'})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    report = build(args.out)
    args.out.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))

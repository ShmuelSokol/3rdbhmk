"""Patch only matched outer-robe/hem vertices in a fresh approved-head GLB study."""
import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
import numpy as np
import create_kohen_gadol_v1 as K
from build_kohen_neck_tone_study import SOURCE, SOURCE_SHA
from measure_pilgrim_walk import read_glb, read_accessor


def f32(values):
    return tuple(float(v) for v in np.asarray(values, dtype=np.float32))


def normal_key(values):
    # Two hem-cap normals differ only by ~1e-17 roundoff in an analytically zero
    # component. Preserve exact float32 identity for every nonzero component.
    return tuple(0.0 if abs(v) < 1e-12 else v for v in f32(values))


def parts(ease, follow_ephod=False):
    saved = K.MEIL_LOWER_EASE_CM
    saved_surface = K.surface_point
    try:
        K.MEIL_LOWER_EASE_CM = ease
        result = K.Parts()
        vv = K.meil(result)
        K.bells_and_pomegranates(result, vv)
        if follow_ephod:
            def surface(t, z, offset, g=1.0, sh=1.02):
                extra = K.meil_offset(z) - K.OFF_MEIL if offset >= K.OFF_EPHOD else 0.0
                return saved_surface(t, z, offset + extra, g, sh)
            K.surface_point = surface
            K.ephod(result)
        return result.parts
    finally:
        K.MEIL_LOWER_EASE_CM = saved
        K.surface_point = saved_surface


def build(destination, ease, follow_ephod=False):
    destination = Path(destination)
    if destination.exists() or destination.with_suffix('.json').exists():
        raise FileExistsError('Fresh study destination required')
    if not np.isfinite(ease) or not 0 < ease <= 5:
        raise ValueError('Study ease must be within (0, 5] cm')
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Approved source hash differs')
    bones = K.C.skeleton()
    index = {b['name']: i for i, b in enumerate(bones)}
    replacements = {}
    expected = Counter()
    for old, new in zip(parts(0, follow_ephod), parts(ease, follow_ephod), strict=True):
        if old['name'] != new['name'] or old['faces'] != new['faces']:
            raise ValueError('Topology changed')
        old_normals, new_normals = K.C.normals(old), K.C.normals(new)
        for i, (a, b) in enumerate(zip(old['vertices'], new['vertices'], strict=True)):
            oi, ni = K.influence(old, a, index), K.influence(new, b, index)
            if oi != ni:
                raise ValueError('Skin weights changed: ' + old['name'])
            key = (old['material'], f32(K.C.gltf_vec(a)),
                   normal_key((old_normals[i][0], old_normals[i][2], -old_normals[i][1])),
                   tuple(j for j, w in oi), f32([w for j, w in oi]))
            value = (f32(K.C.gltf_vec(b)),
                     f32((new_normals[i][0], new_normals[i][2], -new_normals[i][1])))
            if key in replacements and replacements[key] != value:
                raise ValueError('Ambiguous vertex identity')
            replacements[key] = value
            expected[key] += 1
    doc, binary = read_glb(SOURCE)
    output = bytearray(binary)
    allowed = np.zeros(len(output), dtype=bool)
    found = Counter()
    changed_vertices = 0
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            mat = doc['materials'][primitive['material']]['name']
            attrs = primitive['attributes']
            names = ('POSITION', 'NORMAL', 'JOINTS_0', 'WEIGHTS_0')
            arrays = {name: read_accessor(doc, binary, attrs[name]) for name in names}
            positions = list(arrays['POSITION'])
            touched = False
            for i, pos in enumerate(positions):
                key = (mat, tuple(pos), normal_key(arrays['NORMAL'][i]),
                       tuple(arrays['JOINTS_0'][i]), tuple(arrays['WEIGHTS_0'][i]))
                if key not in replacements:
                    continue
                found[key] += 1
                values = replacements[key]
                if values[0] == tuple(pos) and normal_key(values[1]) == normal_key(arrays['NORMAL'][i]):
                    continue
                for name, value in zip(('POSITION', 'NORMAL'), values):
                    accessor = doc['accessors'][attrs[name]]
                    view = doc['bufferViews'][accessor['bufferView']]
                    if accessor['componentType'] != 5126 or accessor['type'] != 'VEC3' or 'sparse' in accessor:
                        raise ValueError('Expected dense float VEC3')
                    offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0) + i * view.get('byteStride', 12)
                    struct.pack_into('<3f', output, offset, *value)
                    allowed[offset:offset + 12] = True
                positions[i] = values[0]
                changed_vertices += 1
                touched = True
            if touched:
                accessor = doc['accessors'][attrs['POSITION']]
                accessor['min'] = np.asarray(positions).min(axis=0).tolist()
                accessor['max'] = np.asarray(positions).max(axis=0).tolist()
    if found != expected:
        raise ValueError('Source vertex correspondence failed: missing=%d extra=%d; examples=%r' %
                         (sum((expected - found).values()), sum((found - expected).values()),
                          list((expected - found).items())[:3]))
    changed = np.frombuffer(binary, dtype=np.uint8) != np.frombuffer(output, dtype=np.uint8)
    if not changed_vertices or np.any(changed & ~allowed):
        raise ValueError('Geometry-only byte preservation failed')
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    output += b'\0' * (-len(output) % 4)
    payload = (struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(output))
               + struct.pack('<I4s', len(encoded), b'JSON') + encoded
               + struct.pack('<I4s', len(output), b'BIN\0') + output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(payload)
    report = {'status': 'source-study-native-and-visual-review-pending', 'lowerEaseCm': ease,
              'ephodFollowsEase': follow_ephod,
              'sourceSha256': SOURCE_SHA, 'outputSha256': hashlib.sha256(payload).hexdigest(),
              'matchedVertices': sum(found.values()), 'changedVertices': changed_vertices,
              'normalIdentityZeroTolerance': 1e-12,
              'changedBinaryBytes': int(changed.sum()),
              'preserved': 'All binary bytes except matched robe/hem and optional ephod/edge position and normal bytes; rig, weights, face, colors, UVs and indices unchanged. Position accessor bounds updated.',
              'limits': 'Not imported, packaged or accepted; full clearance and rendered silhouette/decorations remain required.'}
    destination.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--ease', type=float, required=True)
    parser.add_argument('--follow-ephod', action='store_true', help='Carry the ephod and its edges outside the wider robe')
    args = parser.parse_args()
    print(json.dumps(build(args.out, args.ease, args.follow_ephod), indent=2))

"""Patch matched garment skin weights in a fresh approved-head GLB study."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
import create_kohen_gadol_v1 as K
from build_kohen_meil_study import f32, normal_key
from build_kohen_neck_tone_study import SOURCE, SOURCE_SHA
from measure_pilgrim_walk import read_glb, read_accessor
import verify_kohen_clearance_source as V


def garment_parts():
    # Include decorations: their anchors must follow the same garment skin field.
    p = K.Parts()
    K.ketonet(p)
    vv = K.meil(p)
    K.bells_and_pomegranates(p, vv)
    K.ephod(p)
    K.belt_and_knot(p)
    settings = K.straps_and_shoham(p)
    K.choshen(p, settings)
    K.sleeves(p)
    return p.parts


def build(destination, top, bottom):
    destination = Path(destination)
    if destination.exists() or destination.with_suffix('.json').exists():
        raise FileExistsError('Fresh study destination required')
    if not np.isfinite([top, bottom]).all() or not 5 <= bottom < top <= K.F_FULL:
        raise ValueError('Invalid knee blend range')
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Approved source hash differs')
    before = K.KNEE_TOP, K.KNEE_BOT
    bones = K.C.skeleton()
    index = {b['name']: i for i, b in enumerate(bones)}
    replacements, expected = {}, Counter()
    try:
        for part in garment_parts():
            normals = K.C.normals(part)
            for i, vertex in enumerate(part['vertices']):
                K.KNEE_TOP, K.KNEE_BOT = before
                old = K.influence(part, vertex, index)
                K.KNEE_TOP, K.KNEE_BOT = top, bottom
                new = K.influence(part, vertex, index)
                key = (part['material'], f32(K.C.gltf_vec(vertex)),
                       normal_key((normals[i][0], normals[i][2], -normals[i][1])),
                       tuple(j for j, w in old), f32([w for j, w in old]))
                value = tuple(j for j, w in new), f32([w for j, w in new])
                if key in replacements and replacements[key] != value:
                    raise ValueError('Ambiguous vertex identity')
                replacements[key] = value
                expected[key] += 1
    finally:
        K.KNEE_TOP, K.KNEE_BOT = before
    doc, binary = read_glb(SOURCE)
    if [doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']] != [b['name'] for b in bones]:
        raise ValueError('Joint identity/order differs')
    output = bytearray(binary)
    allowed = np.zeros(len(output), dtype=bool)
    found, changed_by_material = Counter(), Counter()
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            material = doc['materials'][primitive['material']]['name']
            attrs = primitive['attributes']
            arrays = {n: read_accessor(doc, binary, attrs[n])
                      for n in ('POSITION', 'NORMAL', 'JOINTS_0', 'WEIGHTS_0')}
            for i, position in enumerate(arrays['POSITION']):
                old = tuple(arrays['JOINTS_0'][i]), tuple(arrays['WEIGHTS_0'][i])
                key = (material, tuple(position), normal_key(arrays['NORMAL'][i]), *old)
                if key not in replacements:
                    continue
                found[key] += 1
                values = replacements[key]
                if values == old:
                    continue
                for name, value, component, fmt in (
                        ('JOINTS_0', values[0], 5123, '<4H'),
                        ('WEIGHTS_0', values[1], 5126, '<4f')):
                    accessor = doc['accessors'][attrs[name]]
                    view = doc['bufferViews'][accessor['bufferView']]
                    if accessor['componentType'] != component or accessor['type'] != 'VEC4' or 'sparse' in accessor:
                        raise ValueError('Expected dense joint/weight VEC4')
                    size = struct.calcsize(fmt)
                    offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0) + i * view.get('byteStride', size)
                    struct.pack_into(fmt, output, offset, *value)
                    allowed[offset:offset + size] = True
                changed_by_material[material] += 1
    if found != expected:
        raise ValueError('Vertex correspondence failed: missing=%d extra=%d' %
                         (sum((expected - found).values()), sum((found - expected).values())))
    changed = np.frombuffer(binary, dtype=np.uint8) != np.frombuffer(output, dtype=np.uint8)
    if not changed_by_material or np.any(changed & ~allowed):
        raise ValueError('Skinning-only preservation failed')
    # Preserve the entire original JSON chunk byte-for-byte, including accessor bounds.
    source = SOURCE.read_bytes()
    json_length = struct.unpack_from('<I', source, 12)[0]
    bin_start = 28 + json_length
    if source[bin_start:] != binary or len(source) != bin_start + len(output):
        raise ValueError('Unexpected GLB chunk layout')
    payload = source[:bin_start] + output
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(payload)
    try:
        K.KNEE_TOP, K.KNEE_BOT = top, bottom
        provenance = V.verify(destination)
    finally:
        K.KNEE_TOP, K.KNEE_BOT = before
    if not provenance['passed']:
        raise ValueError('Written study failed measured-triangle correspondence; retained for diagnosis')
    report = dict(status='source-study-native-and-visual-review-pending',
        kneeTopCm=top, kneeBottomCm=bottom, sourceSha256=SOURCE_SHA,
        outputSha256=hashlib.sha256(payload).hexdigest(),
        matchedVertices=sum(found.values()), changedVerticesByMaterial=dict(changed_by_material),
        changedBinaryBytes=int(changed.sum()), measuredGeometry=provenance,
        preserved='All original GLB bytes except matched garment joint/weight bytes. Face, geometry, normals, UVs, colors, indices, skeleton, JSON and source file unchanged.',
        limitations='Source study only. Full clip clearance, decoration alignment and native visual review required.',
        sourceHashes={Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                      for p in (K.__file__, V.__file__, __file__)})
    destination.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--top', type=float, required=True)
    parser.add_argument('--bottom', type=float, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.out, args.top, args.bottom), indent=2))

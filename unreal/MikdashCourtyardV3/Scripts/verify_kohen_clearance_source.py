"""Verify measured garment triangles/weights occur in the exported Kohen GLB.

This is source provenance, not native import, animation or visual acceptance.
No dependence on primitive order or contiguous part ranges.
"""
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path

import measure_kohen_garment_clearance as M
from measure_pilgrim_walk import read_glb, read_accessor


def verify(path=None):
    path = Path(path) if path else M.ROOT / 'SourceAssets/characters-review/KohenGadolV1/meshes/SK_KohenGadol_V1.glb'
    path = path.resolve()
    doc, binary = read_glb(path)
    bones, index, parts, influence, robe, _, outer, _ = M.body_parts('kohen')
    selected = [p for p in parts if p['name'] in (robe, outer)
                or p['name'].startswith(M.LEG_PREFIXES)]
    joints = doc['skins'][0]['joints']
    if [doc['nodes'][j]['name'] for j in joints] != [b['name'] for b in bones]:
        raise ValueError('Exported joint identity/order differs from measured rig')
    def f32(values):
        return struct.pack('<' + 'f' * len(values), *values)
    def key(position, joint, weight):
        return f32(position), tuple(joint), f32(weight)
    def triangle(keys):
        # Rotate, but do not reverse: winding is part of the comparison.
        return min(tuple(keys[i:] + keys[:i]) for i in range(3))
    required = Counter()
    for part in selected:
        keys = []
        for vertex in part['vertices']:
            inf = influence(part, vertex, index)
            keys.append(key(M.C.gltf_vec(vertex), [j for j, _ in inf], [w for _, w in inf]))
        required.update((part['material'], triangle([keys[i] for i in face])) for face in part['faces'])
    materials = {p['material'] for p in selected}
    actual = Counter()
    for primitive in doc['meshes'][0]['primitives']:
        material = doc['materials'][primitive['material']]['name']
        if material not in materials:
            continue
        attrs = primitive['attributes']
        positions, js, ws = [read_accessor(doc, binary, attrs[name])
                             for name in ('POSITION', 'JOINTS_0', 'WEIGHTS_0')]
        keys = [key(p, j, w) for p, j, w in zip(positions, js, ws)]
        indices = read_accessor(doc, binary, primitive['indices'])
        actual.update((material, triangle([keys[j] for j in indices[i:i + 3]]))
                      for i in range(0, len(indices), 3))
    missing = required - actual
    result = {'passed': not missing, 'glb': str(path.relative_to(M.ROOT)),
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'measuredParts': [p['name'] for p in selected],
              'measuredTriangles': sum(required.values()),
              'missingTriangles': sum(missing.values()),
              'comparison': 'Exact float32 positions/weights, joint identities, material and winding; triangle multiset containment.',
              'scope': 'Generator garments exist in exported source GLB. Native imported mesh and rendered clearance remain unverified.'}
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--glb', type=Path)
    parser.add_argument('--meil-ease', type=float, default=0.0)
    args = parser.parse_args()
    import create_kohen_gadol_v1 as K
    saved = K.MEIL_LOWER_EASE_CM
    try:
        K.MEIL_LOWER_EASE_CM = args.meil_ease
        result = verify(args.glb)
    finally:
        K.MEIL_LOWER_EASE_CM = saved
    result['candidateLowerEaseCm'] = args.meil_ease
    payload = json.dumps(result, indent=2) + '\n'
    if args.out:
        args.out.write_text(payload, encoding='utf-8')
    print(payload)
    raise SystemExit(0 if result['passed'] else 1)

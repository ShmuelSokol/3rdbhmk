"""Add temple/scalp hair and natural sidelocks to the approved Kohen GLB.

An authored appearance study, not a historical reconstruction claim or native adoption.
Original primitives and binary bytes are preserved; new head-weighted hair is appended.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np
from build_kohen_neck_tone_study import SOURCE, SOURCE_SHA
from measure_pilgrim_walk import read_glb, read_accessor, author


def build(destination):
    destination = Path(destination)
    if destination.exists() or destination.with_suffix('.json').exists():
        raise FileExistsError('Fresh study required')
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Approved Walter source changed')
    doc, binary = read_glb(SOURCE)
    original = copy.deepcopy(doc)
    primitives = doc['meshes'][0]['primitives']
    head = next(p for p in primitives if doc['materials'][p['material']]['name'] == 'KG_MHHead')
    hair_material = next(i for i, m in enumerate(doc['materials']) if m['name'] == 'KG_Hair')
    v = np.array([author(p) for p in read_accessor(doc, binary, head['attributes']['POSITION'])])
    n = np.array([(p[0], -p[2], p[1]) for p in read_accessor(doc, binary, head['attributes']['NORMAL'])])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    faces = np.array(read_accessor(doc, binary, head['indices']), dtype=int).reshape(-1, 3)
    # Hairline runs higher over the forehead and lower behind the ears. The
    # protruding ear itself stays bare. Boundary vertices sink into the skin.
    x, y, z = v.T
    hairline = 168.7 + 3.0 * np.clip(-y / 8, 0, 1) - 2.8 * np.clip(y / 8, 0, 1)
    mask = z - hairline
    mask[(abs(x) > 8.15) & (z < 170)] = -2
    retained = faces[mask[faces].mean(axis=1) > 0.15]
    used = np.unique(retained)
    remap = np.full(len(v), -1, dtype=int)
    remap[used] = np.arange(len(used))
    amount = np.clip(mask[used] / 1.1, 0, 1)
    amount = amount * amount * (3 - 2 * amount)
    texture = .025 * np.sin(v[used, 2] * 23 + v[used, 1] * 7)
    offset = -.05 + amount * (.20 + texture)
    positions = (v[used] + n[used] * offset[:, None]).tolist()
    normals = n[used].tolist()
    triangles = remap[retained].tolist()
    colors = []
    for p in positions:
        variation = .78 + .13 * math.sin(p[0] * 35 + p[1] * 20 + math.sin(p[2] * .6)) + .06 * math.sin(p[0] * 71)
        colors.append([.60 * variation, .585 * variation, .56 * variation, 1.0])
    scalp_vertices, scalp_triangles = len(positions), len(triangles)
    lock_centres = {}
    for side in (-1, 1):
        centres = []
        for i in range(33):
            t = i / 32
            height = 170.3 - 9.2 * t
            front = -3.6 + .32 * math.sin(t * math.pi * 1.8)
            eligible = np.flatnonzero((v[:, 0] * side > 4) & (n[:, 0] * side > .25))
            distance = (v[eligible, 1] - front) ** 2 + (v[eligible, 2] - height) ** 2
            near = eligible[np.argsort(distance)[:8]]
            surface_x = float(np.median(v[near, 0]))
            centres.append([surface_x + side * (.28 + .30 * math.sin(math.pi * t)), front, height])
        centres = np.asarray(centres)
        # Smooth source tessellation fluctuations, retaining the endpoints.
        for _ in range(3):
            centres[1:-1, 0] = (centres[:-2, 0] + 2 * centres[1:-1, 0] + centres[2:, 0]) / 4
        lock_centres[str(side)] = centres.tolist()
        start = len(positions)
        segments = 12
        for i, centre in enumerate(centres):
            t = i / (len(centres) - 1)
            radius = .76 * (.85 + .15 * math.sin(math.pi * t)) * (1 - .86 * t ** 8)
            for j in range(segments):
                angle = j * math.tau / segments
                # Flattened lock lies against the temple, with small strand ridges.
                ridge = 1 + .06 * math.cos(5 * angle + 8 * t)
                p = centre + np.array([side * .65 * radius * math.cos(angle), radius * math.sin(angle), 0]) * ridge
                normal = np.array([side * math.cos(angle) / .65, math.sin(angle), 0])
                normal /= np.linalg.norm(normal)
                positions.append(p.tolist()); normals.append(normal.tolist())
                shade = .82 + .14 * math.cos(5 * angle + t * 8)
                colors.append([.60 * shade, .585 * shade, .56 * shade, 1.0])
        for i in range(len(centres) - 1):
            for j in range(segments):
                a = start + i * segments + j
                b = start + i * segments + (j + 1) % segments
                c, d = a + segments, b + segments
                # Check geometric orientation below, independently of side.
                triangles.extend([[a, b, c], [b, d, c]])
        for ring, direction in ((0, 1), (len(centres) - 1, -1)):
            centre_id = len(positions)
            positions.append((centres[ring] + [0, 0, direction * .04]).tolist())
            normals.append([0, 0, direction])
            colors.append([.49, .48, .46, 1.0])
            for j in range(segments):
                triangles.append([centre_id, start + ring * segments + j,
                                  start + ring * segments + (j + 1) % segments])
        # Fine raised strands break the smooth cord silhouette and carry varied
        # grey tones. They use geometry, so no new shader or alpha mode is needed.
        for strand in range(24):
            strand_start = len(positions)
            sides = 5
            phase = strand * math.tau / 24
            tone = .37 + .19 * (.5 + .5 * math.sin(strand * 2.399))
            for i, centre in enumerate(centres):
                t = i / (len(centres) - 1)
                radius = .76 * (.85 + .15 * math.sin(math.pi * t)) * (1 - .86 * t ** 8)
                angle = phase + .035 * math.sin(t * 11 + phase)
                ridge = 1 + .06 * math.cos(5 * angle + 8 * t)
                strand_centre = centre + np.array([side * .65 * radius * math.cos(angle), radius * math.sin(angle), 0]) * ridge
                thickness = .055 * (1 - .78 * t ** 8)
                for j in range(sides):
                    a = j * math.tau / sides
                    normal = np.array([math.cos(a), math.sin(a), 0])
                    positions.append((strand_centre + normal * thickness).tolist())
                    normals.append(normal.tolist())
                    colors.append([tone, tone * .975, tone * .935, 1.0])
            for i in range(len(centres) - 1):
                for j in range(sides):
                    a = strand_start + i * sides + j
                    b = strand_start + i * sides + (j + 1) % sides
                    triangles.extend([[a, b, a + sides], [b, b + sides, a + sides]])
    positions = np.asarray(positions)
    normals = np.asarray(normals)
    triangles = np.asarray(triangles, dtype=int)
    cross = np.cross(positions[triangles[:, 1]] - positions[triangles[:, 0]],
                     positions[triangles[:, 2]] - positions[triangles[:, 0]])
    wrong = np.sum(cross * normals[triangles].mean(axis=1), axis=1) < 0
    triangles[wrong] = triangles[wrong][:, [0, 2, 1]]
    # Author centimetres -> glTF metres, matching the source coordinate system.
    positions = positions[:, [0, 2, 1]] * np.array([.01, .01, -.01])
    normals = normals[:, [0, 2, 1]] * np.array([1, 1, -1])
    head_joint = [doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']].index('head')
    joints = np.zeros((len(positions), 4), dtype=np.uint16); joints[:, 0] = head_joint
    weights = np.zeros((len(positions), 4), dtype=np.float32); weights[:, 0] = 1
    output = bytearray(binary)
    def append(values, kind, component, fmt):
        values = np.asarray(values)
        output.extend(b'\0' * (-len(output) % 4))
        offset = len(output)
        for row in values.reshape(len(values), -1):
            output.extend(struct.pack('<' + fmt * len(row), *row))
        doc['bufferViews'].append(dict(buffer=0, byteOffset=offset, byteLength=len(output) - offset))
        accessor = dict(bufferView=len(doc['bufferViews']) - 1, componentType=component, count=len(values), type=kind)
        if kind == 'VEC3':
            accessor.update(min=values.min(axis=0).tolist(), max=values.max(axis=0).tolist())
        doc['accessors'].append(accessor)
        return len(doc['accessors']) - 1
    attrs = dict(POSITION=append(positions, 'VEC3', 5126, 'f'), NORMAL=append(normals, 'VEC3', 5126, 'f'),
                 COLOR_0=append(colors, 'VEC4', 5126, 'f'), JOINTS_0=append(joints, 'VEC4', 5123, 'H'),
                 WEIGHTS_0=append(weights, 'VEC4', 5126, 'f'),
                 TEXCOORD_0=append(np.zeros((len(positions), 2)), 'VEC2', 5126, 'f'))
    primitives.append(dict(attributes=attrs, indices=append(triangles.reshape(-1), 'SCALAR', 5125, 'I'), material=hair_material, mode=4))
    output.extend(b'\0' * (-len(output) % 4))
    doc['buffers'][0]['byteLength'] = len(output)
    assert output[:len(binary)] == binary
    assert primitives[:-1] == original['meshes'][0]['primitives']
    encoded = json.dumps(doc, separators=(',', ':')).encode(); encoded += b' ' * (-len(encoded) % 4)
    payload = struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(output))
    payload += struct.pack('<I4s', len(encoded), b'JSON') + encoded
    payload += struct.pack('<I4s', len(output), b'BIN\0') + output
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream: stream.write(payload)
    report = dict(status='hair-study-visual-native-review-pending', sourceSha256=SOURCE_SHA,
        outputSha256=hashlib.sha256(payload).hexdigest(), generatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scalpVertices=scalp_vertices, scalpTriangles=scalp_triangles, addedVertices=len(positions), addedTriangles=len(triangles),
        headJointIndex=head_joint, sidelockCentresAuthorCm=lock_centres,
        preserved='All original binary bytes, primitives, materials, rig, approved face, beard, turban and garments.',
        scope='Authored natural temple hair and earlobe-length sidelocks. No historical hairstyle claim or native adoption.')
    destination.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.out)
    print(json.dumps({k: v for k, v in result.items() if k != 'sidelockCentresAuthorCm'}, indent=2))

"""Isolated source-GLB mantle repair; no live assets or maps are changed.

Fit the mantle outside the actual folded tunic and sash, instead of the smooth
ellipse used by the original generator. Preserve body/cloth weights and animations;
make edge trim follow its adjacent cloth vertex.
Measurements sample vertices and triangle centres, not continuous collision.
"""
import argparse
import copy
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
import create_pilgrim_v3 as C
import measure_kohen_garment_clearance as M
from measure_pilgrim_walk import Rig, read_accessor, read_glb

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'SourceAssets/characters-review/PilgrimRigV3/walk-v2/meshes/V3_Pilgrim_Man_Standard.glb'


def radial_envelope(points, triangles, clearance):
    """Move points radially past the outermost horizontal ray/triangle hit."""
    result = np.array(points, dtype=float).copy()
    v0 = triangles[:, 0]
    e1 = triangles[:, 1] - v0
    e2 = triangles[:, 2] - v0
    for i, p in enumerate(result):
        radius = np.linalg.norm(p[:2])
        if radius < 1e-6:
            raise ValueError('Cannot fit a vertex on the centre axis')
        direction = np.array([p[0] / radius, p[1] / radius, 0.0])
        origin = np.array([0.0, 0.0, p[2]])
        h = np.cross(direction, e2)
        determinant = np.einsum('ij,ij->i', e1, h)
        valid = np.abs(determinant) > 1e-10
        inverse = np.zeros_like(determinant)
        inverse[valid] = 1 / determinant[valid]
        delta = origin - v0
        u = inverse * np.einsum('ij,ij->i', delta, h)
        q = np.cross(delta, e1)
        v = inverse * (q @ direction)
        distance = inverse * np.einsum('ij,ij->i', e2, q)
        valid &= (u >= -1e-8) & (v >= -1e-8) & (u + v <= 1 + 1e-8) & (distance > 0)
        if valid.any():
            result[i] += direction * max(0.0, float(distance[valid].max()) + clearance - radius)
    return result


def source_parts():
    """Require exact ordered source position/weight/index correspondence first."""
    variant = next(v for v in C.VARIANTS if v['id'] == 'V3_Pilgrim_Man_Standard')
    parts = C.assembly(variant)
    bones = C.skeleton()
    index = {b['name']: i for i, b in enumerate(bones)}
    doc, binary = read_glb(SOURCE)
    assert [doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']] == list(index)
    for bone, node in zip(bones, doc['skins'][0]['joints']):
        assert np.array_equal(np.asarray(doc['nodes'][node]['translation'], dtype='<f4'),
                              np.asarray(C.gltf_vec(bone['local_translation_cm']), dtype='<f4'))
        assert doc['nodes'][node].get('rotation', [0, 0, 0, 1]) == [0, 0, 0, 1]
    inverse_bind = read_accessor(doc, binary, doc['skins'][0]['inverseBindMatrices'])
    for bone, matrix in zip(bones, inverse_bind):
        x, y, z = C.gltf_vec(bone['position_cm'])
        expected = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1]
        assert np.array_equal(np.asarray(matrix, dtype='<f4'), np.asarray(expected, dtype='<f4'))
    mapping = {}
    for primitive in doc['meshes'][0]['primitives']:
        material = doc['materials'][primitive['material']]['name']
        attrs = primitive['attributes']
        pos, joints, weights = [read_accessor(doc, binary, attrs[n])
                                for n in ('POSITION', 'JOINTS_0', 'WEIGHTS_0')]
        indices = read_accessor(doc, binary, primitive['indices'])
        offset, expected_indices = 0, []
        for part in [p for p in parts if p['material'] == material]:
            count = len(part['vertices'])
            expected_pos = np.asarray([C.gltf_vec(p) for p in part['vertices']], dtype='<f4')
            expected_inf = [C.influence(part, p, index) for p in part['vertices']]
            assert expected_pos.tobytes() == np.asarray(pos[offset:offset + count], dtype='<f4').tobytes(), part['name']
            assert np.array_equal(np.asarray(joints[offset:offset + count]), [[j for j, _ in inf] for inf in expected_inf]), part['name']
            assert np.asarray(weights[offset:offset + count], dtype='<f4').tobytes() == np.asarray([[w for _, w in inf] for inf in expected_inf], dtype='<f4').tobytes(), part['name']
            part['joints'] = np.asarray(joints[offset:offset + count], dtype=int)
            part['weights'] = np.asarray(weights[offset:offset + count], dtype=float)
            # Evaluate the float32 exported positions, not unrounded generator data.
            pp = np.asarray(pos[offset:offset + count], dtype=float)
            part['vertices'] = np.column_stack((pp[:, 0], -pp[:, 2], pp[:, 1])) * 100
            expected_indices.extend(offset + i for face in part['faces'] for i in face)
            mapping[part['name']] = (attrs, offset, count)
            offset += count
        assert offset == len(pos) and indices == expected_indices, material
    return variant, bones, parts, doc, binary, mapping


def write_candidate(path, parts, doc, binary, mapping, changed):
    doc = copy.deepcopy(doc)
    output = bytearray(binary)
    allowed = set()
    for part in parts:
        if part['name'] not in changed:
            continue
        attrs, offset, count = mapping[part['name']]
        values = {'POSITION': [C.gltf_vec(p) for p in part['vertices']],
                  'NORMAL': [(p[0], p[2], -p[1]) for p in C.normals(part)]}
        if part['name'] != 'Mantle':
            values.update(JOINTS_0=part['joints'], WEIGHTS_0=part['weights'])
        for name, rows in values.items():
            accessor = doc['accessors'][attrs[name]]
            view = doc['bufferViews'][accessor['bufferView']]
            fmt = '<4H' if name == 'JOINTS_0' else ('<4f' if name == 'WEIGHTS_0' else '<3f')
            assert accessor['componentType'] == (5123 if name == 'JOINTS_0' else 5126)
            assert accessor['type'] == ('VEC4' if name in ('JOINTS_0', 'WEIGHTS_0') else 'VEC3')
            size = struct.calcsize(fmt)
            stride = view.get('byteStride', size)
            base = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            for i, row in enumerate(rows):
                begin = base + (offset + i) * stride
                output[begin:begin + size] = struct.pack(fmt, *row)
                allowed.update(range(begin, begin + size))
            if name == 'POSITION':
                data = np.asarray(read_accessor(doc, output, attrs[name]))
                accessor['min'], accessor['max'] = data.min(axis=0).tolist(), data.max(axis=0).tolist()
    changed_bytes = {i for i, (a, b) in enumerate(zip(binary, output)) if a != b}
    assert changed_bytes <= allowed and len(binary) == len(output)
    payload = json.dumps(doc, separators=(',', ':')).encode()
    payload += b' ' * ((-len(payload)) % 4)
    output += b'\0' * ((-len(output)) % 4)
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 28 + len(payload) + len(output))
                     + struct.pack('<I4s', len(payload), b'JSON') + payload
                     + struct.pack('<I4s', len(output), b'BIN\0') + output)
    return len(changed_bytes)


def posed(parts, bones, rig, time):
    A, b = M.joint_affines(rig, rig.pose(time), bones)
    return [dict(p, vertices=M.skin(np.asarray(p['vertices']), p['joints'], p['weights'], A, b)) for p in parts]


def fit_mantle(parts, bones, clearance):
    """Fit coherent cloth pairs/trim rings across reference and sampled motion.

    Moving each cloth side independently collapses thickness onto the envelope.
    Instead give each paired front/back vertex the same translation. Edge trim
    receives the adjacent cloth translation and weights after the fit.
    """
    states = [(np.broadcast_to(np.eye(3), (len(bones), 3, 3)), np.zeros((len(bones), 3)))]
    for clip in ('Walk', 'Idle'):
        rig = Rig(SOURCE, 'A_Pilgrim_Original_' + clip)
        states += [M.joint_affines(rig, rig.pose(rig.duration * i / 8), bones) for i in range(8)]
    obstacles = []
    for A, b in states:
        obstacles.append(np.concatenate([M.skin(np.asarray(p['vertices']), p['joints'], p['weights'], A, b)[p['faces']]
                                         for p in parts if p['name'] in ('Tunic', 'Sash')]))
    selected = [p for p in parts if p['name'] in ('Mantle', 'MantleHem', 'MantleEdge-1', 'MantleEdge1')]
    originals = {p['name']: np.asarray(p['vertices']).copy() for p in selected}
    for iteration in range(3):
        for part in selected:
            if part['name'] != 'Mantle':
                continue
            vertices = np.asarray(part['vertices'])
            count = len(vertices)
            assert count == 22 * 34 * 2
            groups = np.column_stack((np.arange(count // 2), np.arange(count // 2, count)))
            centres = vertices[groups].mean(axis=1)
            direction = centres.copy()
            direction[:, 2] = 0
            direction /= np.linalg.norm(direction, axis=1)[:, None]
            distances = np.zeros(len(groups))
            # Account for the group's finite thickness in the envelope target.
            radius = np.linalg.norm(vertices[groups] - centres[:, None], axis=2).max(axis=1)
            for (A, b), triangles in zip(states, obstacles):
                world = M.skin(vertices, part['joints'], part['weights'], A, b)
                world_centres = world[groups].mean(axis=1)
                desired = radial_envelope(world_centres, triangles, clearance)
                delta = desired - world_centres
                need = np.linalg.norm(delta, axis=1)
                unit = np.divide(delta, need[:, None], out=np.zeros_like(delta), where=need[:, None] > 1e-8)
                weighted_A = (part['weights'][:, :, None, None] * A[part['joints']]).sum(axis=1)[groups].mean(axis=1)
                derivative = np.einsum('nij,nj->ni', weighted_A, direction)
                gain = (derivative * unit).sum(axis=1)
                required = np.where(need > 1e-8, (need + radius) / np.maximum(gain, 0.2), 0)
                distances = np.maximum(distances, required)
            vertices[groups] += distances[:, None, None] * direction[:, None]
            part['vertices'] = vertices
        print('Completed coherent motion-envelope pass %d' % (iteration + 1), flush=True)
    mantle = next(p for p in selected if p['name'] == 'Mantle')
    displacement = mantle['vertices'] - originals['Mantle']
    for part in selected:
        if part['name'] == 'Mantle':
            continue
        grid_indices = (np.arange(21 * 34, 22 * 34) if part['name'] == 'MantleHem'
                        else np.arange(22) * 34 + (0 if part['name'] == 'MantleEdge-1' else 33))
        assert len(part['vertices']) == len(grid_indices) * 6 + 2
        for ring, idx in enumerate(grid_indices):
            sl = slice(ring * 6, (ring + 1) * 6)
            part['vertices'][sl] += displacement[idx]
            part['joints'][sl] = mantle['joints'][idx]
            part['weights'][sl] = mantle['weights'][idx]
        for cap, idx in ((-2, grid_indices[0]), (-1, grid_indices[-1])):
            part['vertices'][cap] += displacement[idx]
            part['joints'][cap] = mantle['joints'][idx]
            part['weights'][cap] = mantle['weights'][idx]
    return {p['name']: float(np.linalg.norm(p['vertices'] - originals[p['name']], axis=1).max()) for p in selected}


def overlap(parts):
    by_name = {p['name']: p for p in parts}
    mantle = by_name['Mantle']
    vertices = np.asarray(mantle['vertices'])
    points = np.concatenate((vertices, vertices[np.asarray(mantle['faces'])].mean(axis=1)))
    result = {}
    for name in ('Tunic', 'Sash'):
        part = by_name[name]
        triangles = np.asarray(part['vertices'])[np.asarray(part['faces'])]
        selected = M.inside(points, triangles)
        result[name] = {'insideSamples': int(selected.sum()), 'samples': len(points),
                        'maxDepthCm': float(M.point_tri_distance(points[selected], triangles).max()) if selected.any() else 0.0}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--clearance', type=float, default=2.5)
    args = parser.parse_args()
    if not math.isfinite(args.clearance) or not 0.5 <= args.clearance <= 4:
        raise ValueError('Clearance must be 0.5..4 cm')
    args.out.mkdir(parents=True, exist_ok=False)
    original_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    variant, bones, baseline, doc, binary, mapping = source_parts()
    candidate = copy.deepcopy(baseline)
    changed = {'Mantle', 'MantleHem', 'MantleEdge-1', 'MantleEdge1'}
    shifts = fit_mantle(candidate, bones, args.clearance)
    target = args.out / 'V3_Pilgrim_Man_Standard_MantleStudy.glb'
    changed_bytes = write_candidate(target, candidate, doc, binary, mapping, changed)
    # Round candidate positions exactly as the saved GLB before measuring/rendering.
    for part in candidate:
        p = np.asarray([C.gltf_vec(v) for v in part['vertices']], dtype='<f4').astype(float)
        part['vertices'] = np.column_stack((p[:, 0], -p[:, 2], p[:, 1])) * 100
    records = []
    colours = C.variant_materials(variant)
    for clip in ('Reference', 'Walk', 'Idle'):
        rig = None if clip == 'Reference' else Rig(SOURCE, 'A_Pilgrim_Original_' + clip)
        times = [0.0] if rig is None else [rig.duration * i / 8 for i in range(8)]
        for i, time in enumerate(times):
            row = {'clip': clip, 'time': time}
            for label, parts in (('before', baseline), ('after', candidate)):
                evaluated = parts if rig is None else posed(parts, bones, rig, time)
                row[label] = overlap(evaluated)
                if i == 0:
                    C.render(evaluated, colours, args.out / f'{clip}-{label}.png', 0.25, width=480, height=800, ss=1, top=183, scale=4)
            records.append(row)
            print(json.dumps(row), flush=True)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == original_hash
    result = {'status': 'source-study-not-imported', 'source': str(SOURCE.relative_to(ROOT)),
              'sourceSha256': original_hash, 'candidateSha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'clearanceCm': args.clearance, 'maximumRadialShiftCm': shifts, 'changedBinaryBytes': changed_bytes,
              'preservation': 'Only mantle/trim POSITION and NORMAL, trim JOINTS_0/WEIGHTS_0 and accessor bounds change. Mantle/body weights, animation bytes, indices and other parts are preserved. Trim follows the adjacent mantle grid vertex instead of the old all-back hem weights.',
              'scope': 'Source reference and eight samples each of shipped walk/idle. Vertex and face-centre sampling is not exhaustive collision or native visual acceptance.',
              'samples': records}
    (args.out / 'review.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

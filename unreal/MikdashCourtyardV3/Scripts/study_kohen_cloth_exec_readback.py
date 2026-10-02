"""Validate isolated solver readback; optional ONE-walk existing clearance + renders.

No Unreal launch. Default checks all288 frames, source pose/kinematic correspondence.
--clearance runs existing conjunction checks on all288 frames, never idle/tend.
--renders emits matched shell-only offline views; no final silhouette acceptance.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import itertools
import json
import math
import uuid
from pathlib import Path
import numpy as np
import create_kohen_gadol_v1 as K
import measure_kohen_garment_clearance as M
from study_kohen_cloth_parts import body_parts

ROOT = Path(__file__).resolve().parents[1]


def atomic(path, data):
    if path.exists():
        raise FileExistsError(path)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    temp.rename(path)


def read_frame(path, topology):
    assert topology.get('frameSchemaVersion') == 2, 'Matched control requires frame schema2'
    ns, nr = topology['simulationVertices'], topology['renderVertices']
    assert 0 < ns <= 16384 and 0 < nr <= 20000
    assert path.stat().st_size == (ns + 3 * nr + 27) * 12, 'Truncated/oversized frame'
    data = np.fromfile(path, dtype='<f4').reshape(-1, 3)
    assert np.isfinite(data).all(), 'Nonfinite readback'
    return data[:ns], data[ns:ns + nr], data[ns + nr:ns + 2 * nr], data[ns + 2 * nr:ns + 3 * nr], data[-27:]


def matched_binding_control(topology, bone_index, a, b, original):
    rest = np.asarray(topology['simulationRestAuthorCm'])
    posed = np.zeros_like(rest)
    for i, influences in enumerate(topology['simulationBoneInfluences']):
        for native, weight in influences:
            j = bone_index[topology['boneNames'][int(native)]]
            posed[i] += weight * (a[j] @ rest[i] + b[j])
    normals = np.zeros_like(posed)
    # Faces have native winding; native normals use the reversed cross product.
    for pattern in topology['patterns']:
        f = np.asarray(pattern['faces']) + pattern['start']
        n = -topology['axisDeterminant'] * np.cross(posed[f[:, 1]] - posed[f[:, 0]], posed[f[:, 2]] - posed[f[:, 0]])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        for k in range(3):
            np.add.at(normals, f[:, k], n)
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    result = []
    for row, skin in zip(topology['renderPositionMappings'], original):
        ids = np.asarray(row[:3], dtype=int)
        bary, distance, blend = np.asarray(row[3:6]), row[6], row[7]
        result.append((bary @ (posed[ids] + distance * normals[ids])) * (1 - blend) + skin * blend)
    return np.asarray(result)


def validate_tethers(topology, model):
    rest = np.asarray(topology['simulationRestAuthorCm'])
    md = np.concatenate([p['maxDistanceCm'] for p in model['patterns']])
    outer = len(model['patterns'][0]['verticesCm'])
    rows = topology['tethers']
    assert len(rows) == len(rest) == len(md)
    total = 0
    for i, row in enumerate(rows):
        assert bool(row) == bool(i < outer and md[i] > 0), 'Missing/misplaced tethers'
        seen = set()
        for anchor, length in row:
            assert int(anchor) == anchor and 0 <= anchor < outer and md[int(anchor)] == 0 and anchor not in seen
            assert np.isfinite(length) and length > 0 and length + .01 >= np.linalg.norm(rest[i] - rest[int(anchor)])
            seen.add(anchor)
            total += 1
    assert total > 0
    return total


def correspondence(source, target):
    # Sparse neighbourhood buckets avoid an all-pairs memory allocation.
    buckets = {}
    for i, p in enumerate(target):
        buckets.setdefault(tuple(np.floor(p / .01).astype(int)), []).append(i)
    result = []
    for p in source:
        cell = np.floor(p / .01).astype(int)
        candidates = [j for delta in itertools.product((-1, 0, 1), repeat=3)
                      for j in buckets.get(tuple(cell + delta), []) if np.linalg.norm(target[j] - p) < .005]
        assert candidates, 'No source/render correspondence within0.005cm'
        result.append(candidates)
    return result


def draw(parts, path, yaw):
    from render_face_v5 import render
    ready = []
    for name, v, f in parts:
        v, f = np.asarray(v), np.asarray(f)
        normals = np.zeros_like(v)
        fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
        for k in range(3):
            np.add.at(normals, f[:, k], fn)
        normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
        color = (0.09, .2, .68, 1.) if name == 'Meil' else (.82, .8, .72, 1.)
        ready.append(dict(material='KG_Meil' if name == 'Meil' else 'KG_Linen', vertices=v.tolist(),
                          normals=normals.tolist(), colours=[color] * len(v), faces=f.tolist()))
    assert not path.exists()
    render(ready, path, dist_m=2.1, yaw=yaw, target=(0, 0, 80), width=420, height=630, ss=1)


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument('directory', type=Path)
    ap.add_argument('--clearance', action='store_true')
    ap.add_argument('--renders', action='store_true')
    args = ap.parse_args()
    out = args.directory.resolve()
    receipt = json.loads((out / 'run.json').read_text())
    topology = json.loads((out / 'topology.json').read_text())
    model = json.loads((ROOT / 'SourceAssets/characters-review/KohenClothExecutableV1/prepared-study-input-v2.json').read_text())
    assert validate_tethers(topology, model) == receipt['tetherCount']
    expected_influences = []
    names = [b['name'] for b in model['bones']]
    for p in model['patterns']:
        for row in p['boneInfluences']:
            expected_influences.append([(topology['boneNames'].index(names[int(j)]), w) for j, w in row])
    for expected, got in zip(expected_influences, topology['simulationBoneInfluences']):
        assert np.allclose(expected, got, atol=1e-6), 'Solver binding differs from prepared input'
    assert len(expected_influences) == len(topology['simulationBoneInfluences'])
    assert receipt['apiFeasibilityCompleted'] and receipt['completedWalkSamples'] == 288
    assert receipt['headRigUnboundSectionsPreserved'] and receipt['immutableSourcePreserved']
    assert json.loads((out / 'source-preservation.json').read_text())['passed']
    assert len(receipt['frames']) == 288
    K.KNEE_TOP, K.KNEE_BOT = 65, 20
    bones, index, parts, influence, *_ = body_parts()
    by = {p['name']: p for p in parts}
    rig = M.Rig(M.CLIPS[0][1], M.CLIPS[0][2])
    expected_names = ['Meil', 'Ketonet', 'ShinR', 'FootR', 'ShinL', 'FootL']
    assert [p['name'] for p in topology['patterns']] == expected_names
    assert topology['patterns'][0]['dynamic'] and not any(p['dynamic'] for p in topology['patterns'][1:])
    rows = {p['name']: p for p in topology['patterns']}
    render_rest = np.asarray(topology['renderRestAuthorCm'])
    matches = correspondence(np.asarray(by['Meil']['vertices']), render_rest)
    pick = np.array([m[0] for m in matches])
    bone_pick = [index[n] for n in topology['boneNames']]
    rfaces, rwall, rhem, nring = M.loft_triangles(by['Ketonet'], K.KETONET_SEGMENTS)
    rv = np.asarray(by['Ketonet']['vertices'])
    lower = rv[rfaces].mean(axis=1)[:, 2] < 70
    low_wall = rwall[rv[rwall].mean(axis=1)[:, 2] < 60]
    rsign = M.tube_signs(rv, low_wall)
    ofaces, owall, ohem, onring = M.loft_triangles(by['Meil'], K.MEIL_SEGMENTS)
    ov = np.asarray(by['Meil']['vertices'])
    osign = M.tube_signs(ov, owall)
    kmask = np.zeros(len(rv), dtype=bool)
    kmask[:nring] = (rv[:nring, 2] > ov[ohem, 2].max() + 1.5) & (rv[:nring, 2] < min(M.OUTER_TOP_CAP_CM, ov[:onring, 2].max() - 3))
    kmask[:nring] &= (np.arange(nring) % K.KETONET_SEGMENTS) % 2 == 0
    worst_bone = worst_kinematic = worst_control = worst_matched = physics_difference = 0.
    measurements = []
    for frame, entry in enumerate(receipt['frames']):
        assert entry['index'] == frame and abs(entry['timeSeconds'] - frame / 240) < 1e-6
        assert entry['file'] == f'frame-{frame:03d}.f32'
        sim, rendered, control, matched, native_bones = read_frame(out / entry['file'], topology)
        a, b = M.joint_affines(rig, rig.pose(frame / 240), bones)
        expected_bones = np.array([a[i] @ np.array(bones[i]['position_cm']) + b[i] for i in bone_pick])
        worst_bone = max(worst_bone, float(np.linalg.norm(expected_bones - native_bones, axis=1).max()))
        assert worst_bone <= .05, 'Native clip pose differs from pinned source'
        for name in expected_names[1:]:
            p = rows[name]
            v, j, w = M.skin_arrays(by[name], influence, index)
            expected = M.skin(v, j, w, a, b)
            got = sim[p['start']:p['start'] + p['count']]
            worst_kinematic = max(worst_kinematic, float(np.linalg.norm(expected - got, axis=1).max()))
        assert worst_kinematic <= .05, 'Exact collider readback differs from source skinning'
        v, j, w = M.skin_arrays(by['Meil'], influence, index)
        expected = M.skin(v, j, w, a, b)
        worst_control = max(worst_control, float(np.linalg.norm(control[pick] - expected, axis=1).max()))
        assert worst_control <= .05, 'Render/source correspondence or control weights differ'
        expected_matched = matched_binding_control(topology, index, a, b, control)
        worst_matched = max(worst_matched, float(np.linalg.norm(expected_matched - matched, axis=1).max()))
        assert worst_matched <= .05, 'Matched control differs from actual solver binding/deformer'
        physics_difference = max(physics_difference, float(np.linalg.norm(rendered - matched, axis=1).max()))
        for choices in matches:
            if len(choices) > 1:
                assert np.linalg.norm(rendered[choices] - rendered[choices[0]], axis=1).max() < .01, 'Ambiguous coincident render vertices diverge'
        def physical(name):
            p = rows[name]
            return sim[p['start']:p['start'] + p['count']]
        robe = physical('Ketonet')
        outer = rendered[pick]
        if args.clearance:
            legs = np.concatenate([physical(n) for n in expected_names[2:]])
            leg = M.conjunction(legs, robe, rfaces, rwall, rhem, lower, low_wall, rsign)
            layer = M.conjunction(robe[kmask], outer, ofaces, owall, ohem,
                                  np.ones(len(ofaces), dtype=bool), owall, osign, M.MEIL_HEM_MARGIN_CM)
            measurements.append(dict(frame=frame, time=frame / 240,
                                     legOutsideCm=float(leg.max()), innerOutsideCm=float(layer.max())))
        if args.renders and frame in (71, 280):
            for label, points in [('cloth', outer), ('original-rig-reference', control[pick]), ('matched-binding-control', matched[pick])]:
                for view, yaw in [('front', 0), ('side', math.pi / 2)]:
                    draw([('Ketonet', robe, by['Ketonet']['faces']), ('Meil', points, by['Meil']['faces'])],
                         out / f'offline-{frame:03d}-{label}-{view}.png', yaw)
    assert physics_difference >= .01, 'No measured physics departure from matched binding'
    atomic(out / 'offline-readback.json', dict(passed=True, frames=288,
        maxMatchedBindingControlErrorCm=worst_matched, maxPhysicsDifferenceCm=physics_difference,
        maxSourceBoneErrorCm=worst_bone, maxSourceKinematicErrorCm=worst_kinematic,
        maxSourceRenderControlErrorCm=worst_control, clearanceRun=args.clearance, clearance=measurements,
        sampledWalkClearancePassed=(all(r['legOutsideCm'] == r['innerOutsideCm'] == 0 for r in measurements) if args.clearance else None),
        drapeAccepted=False, full986='notrun',
        limitation='Rigid inner layer can force the shelf. Outer-only results establish API behaviour, not final drape. Existing sampled surface checks are not an exhaustive continuous triangle collision proof.'))


if __name__ == '__main__':
    run()

"""Export the V3 Man_Standard body carrying ONLY the lamp-tending clip, for an
animation-only import onto its EXISTING Skeleton. Offline; launches nothing.

  python Scripts/retend_pilgrim_v3.py --build

Writes SourceAssets/characters-review/PilgrimRigV3/tend-v1/:
  meshes/V3_Pilgrim_Man_Standard.glb   geometry + skin byte-identical to the shipped GLB
                                       (asserted with rewalk_pilgrim_v3.geometry_compare),
                                       one animation: A_Pilgrim_V3_TendLamp, 10 s at 30 fps,
                                       rotation channels + the pelvis translation track
  tend-measurements.json               the curve checks (pilgrim_tend_v1.measure) AND the same
                                       numbers re-read by FK off the written GLB
                                       (measure_pilgrim_walk.Rig: glTF LINEAR sampling)
  previews/*.png                       offline software renders of the posed body at key times
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import create_pilgrim_v3 as C             # noqa: E402
import pilgrim_tend_v1 as T               # noqa: E402
import rewalk_pilgrim_v3 as R             # noqa: E402
from measure_pilgrim_walk import Rig      # noqa: E402

OUT = ROOT / 'SourceAssets/characters-review/PilgrimRigV3'
NEW = OUT / 'tend-v1'
VARIANT = 'V3_Pilgrim_Man_Standard'


def export(path, variant, parts, bones, index, colours):
    asset = C.GLB('Original PilgrimRigV3 Python author, tend-v1 (' + variant['id'] + ')')
    doc = asset.doc
    for i, b in enumerate(bones):
        node = {'name': b['name'], 'translation': C.gltf_vec(b['local_translation_cm'])}
        children = [j for j, k in enumerate(bones) if k['parent_index'] == i]
        if children:
            node['children'] = children
        doc['nodes'].append(node)
    matrices = []
    for b in bones:
        x, y, z = C.gltf_vec(b['position_cm'])
        matrices.append([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1])
    doc['skins'] = [{'name': 'OriginalPilgrimHumanoid', 'joints': list(range(len(bones))), 'skeleton': 0,
                     'inverseBindMatrices': asset.accessor(matrices, 'MAT4')}]
    primitives = []
    used = [m for m in C.ROUGHNESS if any(p['material'] == m for p in parts)]
    for mat in used:
        rgb = colours[mat]
        mi = len(doc['materials'])
        doc['materials'].append({'name': mat, 'pbrMetallicRoughness': {
            'baseColorFactor': list(rgb) + [1.], 'metallicFactor': 0., 'roughnessFactor': C.ROUGHNESS[mat]}})
        positions, norms, joints, weights, vcolours, indices = [], [], [], [], [], []
        for p in parts:
            if p['material'] != mat:
                continue
            offset = len(positions)
            positions.extend(C.gltf_vec(a) for a in p['vertices'])
            norms.extend([n[0], n[2], -n[1]] for n in C.normals(p))
            for point in p['vertices']:
                inf = C.influence(p, point, index)
                joints.append([j for j, _ in inf])
                weights.append([w for _, w in inf])
                vcolours.append(list(rgb) + [1.0])
            indices.extend(offset + i for face in p['faces'] for i in face)
        attrs = {'POSITION': asset.accessor(positions, 'VEC3', target=34962, bounds_=True),
                 'NORMAL': asset.accessor(norms, 'VEC3', target=34962),
                 'COLOR_0': asset.accessor(vcolours, 'VEC4', target=34962),
                 'JOINTS_0': asset.accessor(joints, 'VEC4', 5123, target=34962),
                 'WEIGHTS_0': asset.accessor(weights, 'VEC4', target=34962)}
        primitives.append({'attributes': attrs, 'indices': asset.accessor(indices, 'SCALAR', 5125, 34963),
                           'material': mi, 'mode': 4})
    doc['meshes'] = [{'name': 'SK_' + variant['id'], 'primitives': primitives}]
    doc['nodes'].append({'name': variant['id'] + '_Mesh', 'mesh': 0, 'skin': 0})
    doc['scenes'] = [{'name': 'PilgrimRigV3', 'nodes': [0, len(bones)]}]
    count = round(T.DURATION * T.FPS) + 1
    times = [i * T.DURATION / (count - 1) for i in range(count)]
    poses = [T.tend_pose(bones, t) for t in times]
    time_accessor = asset.accessor(times, 'SCALAR', bounds_=True)
    anim = {'name': T.ANIM_NAME, 'samplers': [], 'channels': []}
    for j, b in enumerate(bones):
        values = [C.gltf_quat(p[0][b['name']]) for p in poses]
        if all(v == [0., 0., 0., 1.] for v in values):
            continue
        si = len(anim['samplers'])
        anim['samplers'].append({'input': time_accessor, 'output': asset.accessor(values, 'VEC4'),
                                 'interpolation': 'LINEAR'})
        anim['channels'].append({'sampler': si, 'target': {'node': j, 'path': 'rotation'}})
    values = [C.gltf_vec(p[1]['pelvis']) for p in poses]
    si = len(anim['samplers'])
    anim['samplers'].append({'input': time_accessor, 'output': asset.accessor(values, 'VEC3'),
                             'interpolation': 'LINEAR'})
    anim['channels'].append({'sampler': si, 'target': {'node': index['pelvis'], 'path': 'translation'}})
    doc['animations'] = [anim]
    doc['extras'] = {'variant': variant['id'], 'clip': T.ANIM_NAME,
                     'provenance': 'Original clip authored in this project (Scripts/pilgrim_tend_v1.py).',
                     'kindleAtSeconds': T.KINDLE_AT,
                     'coordinates': 'Author centimetres XYZ, front -Y, Z up; glTF metres X,Z,-Y.'}
    asset.save(path)
    return doc, count


def glb_checks(path, bones):
    rig = Rig(path, T.ANIM_NAME)
    idx = rig.index
    tip_local = C.scale(T._hand_rest_dir('r'), T.HAND_TIP_CM)
    at = rig.pose(T.KINDLE_AT)
    tip = rig.point(at, idx['hand_r'], tip_local)
    worst = 0.0
    a0 = None
    n = int(T.DURATION * 60)
    for i in range(n + 1):
        w = rig.pose(i / 60.0)
        ankles = [rig.point(w, idx['foot_r']), rig.point(w, idx['foot_l'])]
        a0 = a0 or ankles
        worst = max(worst, max(C.length(C.sub(a, b)) for a, b in zip(ankles, a0)))
    return {'durationSeconds': round(rig.duration, 4),
            'handTipAtKindleFromGlbCm': [round(v, 2) for v in tip],
            'handTipToWickAtKindleFromGlbCm': round(C.length(C.sub(tip, T.WICK)), 2),
            'plantedAnkleMaxDriftFromGlbCm': round(worst, 4)}


def previews(parts, colours, bones, index):
    (NEW / 'previews').mkdir(parents=True, exist_ok=True)
    shots = []
    for t in (0.0, 1.6, 3.0, 4.95, 6.6, T.KINDLE_AT, 9.0):
        q, trans = T.tend_pose(bones, t)
        g = T.fk(bones, q, trans)
        posed = []
        for part in parts:
            vs = []
            for p in part['vertices']:
                out = [0., 0., 0.]
                for j, w in C.influence(part, p, index):
                    if w:
                        gq, gt = g[j]
                        v = C.add(gt, C.qrotate(gq, C.sub(p, bones[j]['position_cm'])))
                        for k in range(3):
                            out[k] += v[k] * w
                vs.append(tuple(out))
            posed.append(dict(part, vertices=vs))
        for name, yaw in (('side', 1.5707963), ('three-quarter', 0.62)):
            p = NEW / 'previews' / ('tend-t%04.1f-%s.png' % (t, name))
            C.render(posed, colours, p, yaw)
            shots.append(str(p.relative_to(NEW)).replace('\\', '/'))
    return shots


def build(with_previews=True):
    (NEW / 'meshes').mkdir(parents=True, exist_ok=True)
    bones = C.skeleton()
    assert C.assert_rig_matches_v2(bones)
    index = {b['name']: i for i, b in enumerate(bones)}
    variant = [v for v in C.VARIANTS if v['id'] == VARIANT][0]
    parts = C.assembly(variant)
    colours = C.variant_materials(variant)
    # Interchange names a lone animation after the FILE, so the file carries the clip's name.
    path = NEW / 'meshes' / (VARIANT + '_TendLamp.glb')
    started = time.time()
    doc, keys = export(path, variant, parts, bones, index, colours)
    old = OUT / 'meshes' / (VARIANT + '.glb')
    cmp = R.geometry_compare(path, old)
    assert cmp['identical'], ('geometry drifted - only the clip may differ: %r' % cmp)
    report = {'status': 'offline_clip_authored_measured_native_import_pending',
              'generatedUtc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'variant': VARIANT, 'clip': T.ANIM_NAME, 'keys': keys,
              'file': str(path.relative_to(OUT)).replace('\\', '/'),
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'shippedGlbSha256': hashlib.sha256(old.read_bytes()).hexdigest(),
              'geometryComparison': cmp,
              'animations': [a['name'] for a in doc['animations']],
              'curveMeasurement': T.measure(bones),
              'glbMeasurement': glb_checks(path, bones),
              'geometrySource': 'SourceAssets/service-review/tend-geometry-probe-20260911T003954381275Z.json',
              'authoring': 'Scripts/pilgrim_tend_v1.py',
              'exportSeconds': round(time.time() - started, 1)}
    if with_previews:
        report['previews'] = previews(parts, colours, bones, index)
    (NEW / 'tend-measurements.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--no-previews', action='store_true')
    a = ap.parse_args()
    if a.build:
        print(json.dumps(build(not a.no_previews), indent=2))
    else:
        ap.print_help()

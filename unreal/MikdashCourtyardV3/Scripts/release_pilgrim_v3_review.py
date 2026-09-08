"""Guarded, resumable native import of the nine PilgrimRigV3 variants.

Offline (`run()`, no Unreal):
  * re-hashes every frozen input (generator, base importer, manifest, 27 mesh files);
  * runs the base importer's offline check (decode, distinctness, budget);
  * REST-POSE PROOF straight from the GLB bytes (`rest_pose_proof()`): each
    variant's skin joints must have the same names, parents and order as the
    PilgrimRigV2 GLB, identity rest rotations, the pelvis unmoved, a whole-arm
    A-pose direction drift no larger than the recorded 0.12 deg, and every clip
    must be rotation-only except one pelvis translation track in Walk. The
    imported A_Pilgrim_Original_Idle/_Walk must target exactly the joints the V2
    clips target. Numbers per variant go to rest-pose-proof.json;
  * writes the resident swap PLAN (resident-swap-plan.json) for the population
    owner. It is a plan: nothing here places, repoints or scales an actor.

Native (`run(import_assets=True, ...)`, root only, clean editor, main loaded):
  * fresh folder per variant under NAMESPACE/<variant>/ (Interchange puts the
    SkeletalMesh, Skeleton, PhysicsAsset and clips in SkeletalMeshes/ and one
    material instance per garment in Materials/; the OBJ crowd copy goes to
    StaticMeshes/SM_<variant>). V2 under /CharacterReview/PilgrimRigV2 is never
    written and never referenced;
  * the skeletal batch is saved only after native proof: a Skeleton created
    inside the variant folder (a foreign/V2 skeleton is refused - no V2 retarget),
    27 bone names in authored order, rest positions within 0.05 cm of the
    Interchange-frame expectation, and every clip rotation-only except pelvis,
    all read back through AnimPose / AnimationLibrary (see release_pilgrim_v3.py);
  * resume marker review-native-progress.json: `variants=None` imports the next
    `batch` variants that are not yet completed, so nine variants can go in as
    1 + 4 + 4 (or any split) and survive an editor restart between batches.
    A variant is completed only when its folder is on disk AND the marker lists
    its read-back identities. Partial failures are preserved, never overwritten;
  * refuses when more than one UnrealEditor process is alive (a zombie makes
    save_loaded_asset return False with no other symptom).

UE 5.8 pitfalls honoured: StaticMesh.get_num_uv_channels does not exist (base
reads StaticMeshDescription); material/property setters return False even on
success (nothing is trusted until read back off the reloaded asset); Nanite makes
get_num_triangles(0) report the fallback (recorded beside the Nanite flag); an
unregistered SkeletalMeshComponent returns identity bone transforms (AnimPose is
used instead); Interchange maps glTF (X,Y,Z) to UE (X,Z,Y), so an authored bone
(x, y, z) cm reads back at (x, -y, z).

Recommended visual scales (0.84 - 1.04) are skeletal-mesh COMPONENT scales for
the population owner. They never go on the Character actor, its 34/96 capsule or
the amah scale, and are never multiplied by 0.96.

These are stylised figures that read correctly at 5-30 m. They are not
film-quality humans, and nothing here is a halachic or historical ruling.
"""
import hashlib
import importlib.util
import json
import math
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'Scripts/release_pilgrim_v3_review.spec.json'
OUT = ROOT / 'SourceAssets/characters-review/PilgrimRigV3'
V2_GLB = ROOT / 'SourceAssets/characters-review/PilgrimRigV2/PilgrimRigV2.glb'
V2_RIG = ROOT / 'SourceAssets/characters-review/PilgrimRigV2/rig-definition.json'
PEOPLE = ROOT / 'Content/Distribution/People/people.json'
PROOF = OUT / 'rest-pose-proof.json'
SWAP = OUT / 'resident-swap-plan.json'
MARKER = OUT / 'review-native-progress.json'
BATCH_MARKER = OUT / 'review-native-batch-progress.json'
NAMESPACE = '/Game/MikdashV3/Characters/PilgrimRigV3'
DEFAULT_BATCH = 3


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def utc():
    return datetime.now(timezone.utc).isoformat()


def helper(name):
    s = importlib.util.spec_from_file_location('review_' + name, ROOT / 'Scripts' / (name + '.py'))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def spec():
    return json.loads(SPEC.read_text(encoding='utf-8-sig'))


def _rel(path):
    path = Path(path)
    try:
        return str(path.relative_to(ROOT)).replace('\\', '/')
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# GLB reader (struct only; no numpy/pygltflib on the bundled interpreter)
# ---------------------------------------------------------------------------


def decode_glb(path):
    data = Path(path).read_bytes()
    magic, version, total = struct.unpack_from('<4sII', data, 0)
    if not (magic == b'glTF' and version == 2 and total == len(data)):
        raise ValueError('Not a glTF 2 binary: ' + str(path))
    off, chunks = 12, {}
    while off < len(data):
        clen, ctype = struct.unpack_from('<I4s', data, off)
        chunks[ctype] = data[off + 8:off + 8 + clen]
        off += 8 + clen + (-clen) % 4
    doc = json.loads(chunks[b'JSON'].decode('utf8'))
    binary = chunks[b'BIN\0']

    def read(ai):
        acc = doc['accessors'][ai]
        view = doc['bufferViews'][acc['bufferView']]
        fmt = {5126: 'f', 5123: 'H', 5125: 'I', 5121: 'B'}[acc['componentType']]
        n = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[acc['type']]
        base = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
        vals = struct.unpack_from('<' + fmt * (acc['count'] * n), binary, base)
        return [vals[i * n:(i + 1) * n] for i in range(acc['count'])]
    return doc, read


def author_cm(v):
    """glTF metres back to the author's cm frame (inverse of the generator's gltf_vec)."""
    return (v[0] * 100.0, -v[2] * 100.0, v[1] * 100.0)


def glb_skeleton(doc):
    skin = doc['skins'][0]
    joints = skin['joints']
    parent = {}
    for i, n in enumerate(doc['nodes']):
        for c in n.get('children', []):
            parent[c] = i
    rows, gpos = [], {}
    for order, j in enumerate(joints):
        n = doc['nodes'][j]
        pj = parent.get(j)
        t = n.get('translation', [0, 0, 0])
        row = {'order': order, 'name': n['name'],
               'parent': doc['nodes'][pj]['name'] if pj is not None else None,
               'parentOrder': joints.index(pj) if pj is not None else None,
               'rotation': list(n.get('rotation', [0, 0, 0, 1])),
               'scale': list(n.get('scale', [1, 1, 1]))}
        if pj is None:
            g = tuple(t)
        else:
            p = gpos[doc['nodes'][pj]['name']]
            g = (p[0] + t[0], p[1] + t[1], p[2] + t[2])
        gpos[n['name']] = g
        row['restAuthorCm'] = [round(v, 4) for v in author_cm(g)]
        rows.append(row)
    return rows


def glb_clips(doc, read):
    names = [n['name'] for n in doc['nodes']]
    out = []
    for a in doc['animations']:
        paths, trans, maxq = {}, {}, 0.0
        times = [t[0] for t in read(a['samplers'][0]['input'])]
        for ch in a['channels']:
            path = ch['target']['path']
            target = names[ch['target']['node']]
            paths.setdefault(path, []).append(target)
            vals = read(a['samplers'][ch['sampler']]['output'])
            if path == 'rotation':
                for q in vals:
                    maxq = max(maxq, abs(math.sqrt(sum(c * c for c in q)) - 1))
            elif path == 'translation':
                cm = [author_cm(v) for v in vals]
                trans[target] = {'keys': len(vals),
                                 'minAuthorCm': [round(min(c[k] for c in cm), 3) for k in range(3)],
                                 'maxAuthorCm': [round(max(c[k] for c in cm), 3) for k in range(3)]}
        out.append({'name': a['name'], 'durationS': round(times[-1], 4), 'keys': len(times),
                    'channels': len(a['channels']),
                    'rotationTargets': sorted(paths.get('rotation', [])),
                    'translationTargets': sorted(paths.get('translation', [])),
                    'scaleTargets': sorted(paths.get('scale', [])),
                    'maxQuatNormError': maxq, 'translationRanges': trans})
    return out


def _angle(u, v):
    nu = math.sqrt(sum(x * x for x in u))
    nv = math.sqrt(sum(x * x for x in v))
    d = max(-1.0, min(1.0, sum(a * b for a, b in zip(u, v)) / (nu * nv)))
    return math.degrees(math.acos(d))


# ---------------------------------------------------------------------------
# rest-pose proof
# ---------------------------------------------------------------------------


def rest_pose_proof(write=True):
    """Prove from the GLB bytes that every V3 variant can play the V2 motion."""
    sp = spec()
    limits = sp['restPoseProof']
    d2, r2 = decode_glb(V2_GLB)
    s2 = glb_skeleton(d2)
    c2 = {c['name']: c for c in glb_clips(d2, r2)}
    rig = json.loads(V2_RIG.read_text(encoding='utf-8-sig'))['bones']
    v2_vs_rig = max(max(abs(a - b) for a, b in zip(r['restAuthorCm'], b_['position_cm']))
                    for r, b_ in zip(s2, rig))
    g2 = {r['name']: r['restAuthorCm'] for r in s2}
    report = {'utc': utc(), 'status': 'UNKNOWN',
              'reference': {'file': str(V2_GLB.relative_to(ROOT)).replace('\\', '/'), 'sha256': sha(V2_GLB),
                            'joints': len(s2), 'jointNames': [r['name'] for r in s2],
                            'v2GlbVsRigDefinitionMaxErrorCm': v2_vs_rig,
                            'nonIdentityRestRotations': [r['name'] for r in s2 if r['rotation'] != [0, 0, 0, 1]],
                            'clips': list(c2.values())},
              'limits': limits, 'variants': [], 'problems': []}
    if v2_vs_rig > 1e-6:
        report['problems'].append('V2 GLB disagrees with rig-definition.json by %.6f cm' % v2_vs_rig)
    for vid in sp['visualScales']:
        glb = OUT / 'meshes' / (vid + '.glb')
        d3, r3 = decode_glb(glb)
        s3 = glb_skeleton(d3)
        g3 = {r['name']: r['restAuthorCm'] for r in s3}
        row = {'id': vid, 'file': glb.name, 'sha256': sha(glb), 'joints': len(s3),
               'jointNamesIdentical': [r['name'] for r in s3] == [r['name'] for r in s2],
               'hierarchyIdentical': [(r['parent'], r['parentOrder']) for r in s3]
               == [(r['parent'], r['parentOrder']) for r in s2],
               'orderIdentical': [r['order'] for r in s3] == [r['order'] for r in s2],
               'nonIdentityRestRotations': [r['name'] for r in s3 if r['rotation'] != [0, 0, 0, 1]],
               'nonUnitRestScales': [r['name'] for r in s3 if r['scale'] != [1, 1, 1]],
               'materials': [m['name'] for m in d3.get('materials', [])],
               'meshName': d3['meshes'][0]['name']}
        problems = []
        if not (row['jointNamesIdentical'] and row['hierarchyIdentical'] and row['orderIdentical']):
            problems.append('joint names/hierarchy/order differ from V2')
            report['variants'].append(dict(row, problems=problems))
            continue
        if row['nonIdentityRestRotations'] or row['nonUnitRestScales']:
            problems.append('rest pose is not pure translation')
        moved = {}
        for name in g2:
            e = max(abs(a - b) for a, b in zip(g3[name], g2[name]))
            if e > 1e-6:
                moved[name] = {'v2Cm': g2[name], 'v3Cm': g3[name], 'deltaCm': round(e, 4)}
        row['movedJoints'] = moved
        row['movedJointCount'] = len(moved)
        row['pelvisMovedCm'] = round(max(abs(a - b) for a, b in zip(g3['pelvis'], g2['pelvis'])), 6)
        undeclared = sorted(set(moved) - set(limits['declaredMovedJoints']))
        if undeclared:
            problems.append('undeclared moved joints: ' + repr(undeclared))
        if row['pelvisMovedCm'] > 0:
            problems.append('pelvis (the only translated track) moved')
        drift = {}
        for side in 'rl':
            for a, b in (('upperarm_', 'hand_'), ('upperarm_', 'lowerarm_'), ('lowerarm_', 'hand_'),
                         ('foot_', 'ball_'), ('thigh_', 'calf_'), ('calf_', 'foot_')):
                u3 = tuple(g3[b + side][k] - g3[a + side][k] for k in range(3))
                u2 = tuple(g2[b + side][k] - g2[a + side][k] for k in range(3))
                drift[a + side + '->' + b + side] = round(_angle(u3, u2), 4)
        row['restDirectionDriftDeg'] = drift
        row['wholeArmAPoseDriftDeg'] = max(drift['upperarm_r->hand_r'], drift['upperarm_l->hand_l'])
        row['maxSegmentDriftDeg'] = max(drift.values())
        if row['wholeArmAPoseDriftDeg'] > limits['maxWholeArmDriftDeg']:
            problems.append('whole-arm A-pose drift %.4f deg exceeds %.4f'
                            % (row['wholeArmAPoseDriftDeg'], limits['maxWholeArmDriftDeg']))
        clips = glb_clips(d3, r3)
        row['clips'] = clips
        row['clipNames'] = [c['name'] for c in clips]
        if row['clipNames'] != limits['expectedClips']:
            problems.append('clip set differs from expectation: ' + repr(row['clipNames']))
        translated = set()
        for c in clips:
            translated |= set(c['translationTargets'])
            if c['scaleTargets']:
                problems.append('clip %s animates scale' % c['name'])
            if c['maxQuatNormError'] > 1e-5:
                problems.append('clip %s has non-unit quaternions' % c['name'])
            if c['durationS'] <= 0:
                problems.append('clip %s has no duration' % c['name'])
            ref = c2.get(c['name'])
            if ref:
                same = (ref['rotationTargets'] == c['rotationTargets']
                        and ref['translationTargets'] == c['translationTargets']
                        and ref['durationS'] == c['durationS'] and ref['keys'] == c['keys'])
                c['identicalTargetsAndTimingToV2'] = same
                if not same:
                    problems.append('clip %s targets/timing differ from the V2 clip' % c['name'])
        row['translatedBonesAcrossAllClips'] = sorted(translated)
        if not translated <= {'pelvis'}:
            problems.append('translation tracks on bones other than pelvis: ' + repr(sorted(translated)))
        row['problems'] = problems
        report['problems'].extend(vid + ': ' + p for p in problems)
        report['variants'].append(row)
    report['status'] = 'REST_POSE_PROVEN_FROM_GLB' if not report['problems'] else 'REST_POSE_PROOF_FAILED'
    report['scope'] = ('Byte-level proof on the delivered GLBs against the delivered V2 GLB. It proves the '
                       'V2 motion (rotation curves plus pelvis translation) is well-defined on every V3 '
                       'skeleton. It is not the native Skeleton identity: Interchange creates one Skeleton '
                       'per variant and the base readback re-proves names/rest pose/clips natively before save.')
    report['honestCeiling'] = ('Segment-level rest directions did move (elbow ~4.96 deg, wrist ~4.32 deg, '
                               'toe ~3.81 deg) because arm and foot were lengthened; the whole-arm A-pose '
                               'direction moved 0.12 deg. Rotation curves apply on top of these rest '
                               'offsets, so poses differ from V2 by exactly the proportion change and by '
                               'nothing else. Visible hand/foot contact still needs PIE eyes.')
    if write:
        PROOF.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


# ---------------------------------------------------------------------------
# resident swap plan (a plan for the population owner; nothing is applied)
# ---------------------------------------------------------------------------


def resident_swap_plan(write=True):
    sp = spec()
    plan = sp['residentSwap']
    people = json.loads(PEOPLE.read_text(encoding='utf-8-sig'))['people']
    stature = {v['id']: v['measuredCm']['stature']
               for v in json.loads((ROOT / 'Scripts/release_pilgrim_v3.spec.json').read_text(encoding='utf-8-sig'))['variants']}
    rows = []
    for person in people:
        cast = plan['casting'][person['id']]
        at = person['route'][0]['at']
        rows.append({'id': person['id'], 'name': person['name'], 'role': person['role'],
                     'garment': person['garment'], 'zone': person['zone'], 'start': at,
                     'variant': cast['variant'], 'visualComponentScale': cast['scale'],
                     'effectiveStatureCm': round(stature[cast['variant']] * cast['scale'], 1),
                     'garmentSlot': 'Linen' if cast['variant'] == 'V3_Pilgrim_Youth' else 'Mantle',
                     'why': cast['why']})
    problems = []
    radius = plan['neighbourRadiusCm']
    neighbours = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            d = math.hypot(a['start'][0] - b['start'][0], a['start'][1] - b['start'][1])
            if d <= radius:
                gap = round(abs(a['visualComponentScale'] - b['visualComponentScale']), 3)
                pair = {'a': a['id'], 'b': b['id'], 'distanceCm': round(d, 1),
                        'sameVariant': a['variant'] == b['variant'], 'scaleGap': gap}
                neighbours.append(pair)
                if gap == 0:
                    problems.append('neighbours share a scale: %s / %s' % (a['id'], b['id']))
                if pair['sameVariant'] and gap < plan['minScaleGapSameVariant']:
                    problems.append('neighbours share variant %s with scale gap %.2f: %s / %s'
                                    % (a['variant'], gap, a['id'], b['id']))
    by_variant = {}
    for r in rows:
        by_variant.setdefault(r['variant'], []).append(r['visualComponentScale'])
    for v, scales in by_variant.items():
        if len(scales) != len(set(scales)):
            problems.append('duplicate scale inside variant ' + v)
        if min(scales) < 0.84 or max(scales) > 1.04:
            problems.append('scale outside 0.84-1.04 in ' + v)
    unused = sorted(set(sp['visualScales']) - set(by_variant))
    report = {'utc': utc(), 'status': 'SWAP_PLAN_ONLY_NOTHING_APPLIED' if not problems else 'SWAP_PLAN_INCONSISTENT',
              'namespace': sp['namespace'], 'residents': rows, 'neighbourPairsChecked': neighbours,
              'variantUse': {v: len(s) for v, s in by_variant.items()}, 'variantsNotCastOnResidents': unused,
              'whyUnused': plan['whyUnused'], 'populationOwnerMustChange': plan['populationOwnerMustChange'],
              'verifyAfter': plan['verifyAfter'], 'problems': problems,
              'scalePolicy': sp['policy']}
    if write:
        SWAP.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


# ---------------------------------------------------------------------------
# offline gate
# ---------------------------------------------------------------------------


def offline_check(write=True):
    sp = spec()
    for path, value in sp['frozenFiles'].items():
        if sha(ROOT / path) != value:
            raise RuntimeError('Frozen input changed: ' + path)
    base = helper('release_pilgrim_v3')
    result = base.offline_check()
    if result['status'] != 'READY_FOR_NATIVE_IMPORT':
        raise RuntimeError('Base source checks refuse: ' + repr(result['problems']))
    proof = rest_pose_proof(write=write)
    if proof['status'] != 'REST_POSE_PROVEN_FROM_GLB':
        raise RuntimeError('Rest-pose proof failed: ' + repr(proof['problems']))
    swap = resident_swap_plan(write=write)
    if swap['problems']:
        raise RuntimeError('Resident swap plan inconsistent: ' + repr(swap['problems']))
    return sp, result, proof, swap


def _editor_processes():
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UnrealEditor.exe', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True, timeout=20).stdout
        pids = [line.split('","')[1] for line in out.splitlines() if line.startswith('"UnrealEditor.exe"')]
        return {'available': True, 'pids': pids}
    except Exception as error:                                       # noqa: BLE001
        return {'available': False, 'reason': str(error)[:120], 'pids': []}


def _load_marker(sp):
    if MARKER.is_file():
        m = json.loads(MARKER.read_text(encoding='utf-8-sig'))
        if m.get('namespace') != sp['namespace']:
            raise RuntimeError('Resume marker belongs to namespace %s, not %s' % (m.get('namespace'), sp['namespace']))
        return m
    return {'namespace': sp['namespace'], 'completed': {}, 'batches': []}


def next_batch(batch=DEFAULT_BATCH):
    """Which variants the next native call would import (offline helper for the coordinator)."""
    sp = spec()
    marker = _load_marker(sp)
    remaining = [v for v in sp['visualScales'] if v not in marker['completed']]
    return {'completed': sorted(marker['completed']), 'next': remaining[:max(1, int(batch))],
            'remainingAfterNext': remaining[max(1, int(batch)):]}


def _proof_summary(proof):
    return {v['id']: {'jointNamesHierarchyOrderIdentical': v['jointNamesIdentical'] and v['hierarchyIdentical']
                      and v['orderIdentical'],
                      'movedJoints': v.get('movedJointCount'), 'pelvisMovedCm': v.get('pelvisMovedCm'),
                      'wholeArmAPoseDriftDeg': v.get('wholeArmAPoseDriftDeg'),
                      'maxSegmentDriftDeg': v.get('maxSegmentDriftDeg'),
                      'translatedBonesAcrossAllClips': v.get('translatedBonesAcrossAllClips'),
                      'clips': [(c['name'], c['durationS'], c['keys'], len(c['rotationTargets']),
                                 c['translationTargets']) for c in v.get('clips', [])]}
            for v in proof['variants']}


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------


def run(*, import_assets=False, variants=None, batch=DEFAULT_BATCH):
    sp, offline, proof, swap = offline_check()
    plan = next_batch(batch)
    commands = {
        'firstBatch': "run(import_assets=True, variants=['V3_Pilgrim_Man_Standard'])",
        'followingBatches': 'run(import_assets=True, batch=4)  # repeat until next_batch()["next"] is empty',
        'explicitBatch': "run(import_assets=True, variants=['V3_Pilgrim_Man_Heavy', 'V3_Pilgrim_Man_Elder', "
                         "'V3_Pilgrim_Woman_Young', 'V3_Pilgrim_Woman_Elder'])"}
    if not import_assets:
        return dict(status='PREPARED_NOT_NATIVE', namespace=sp['namespace'], spec=sp, sourceCheck=offline,
                    restPoseProof={'status': proof['status'], 'file': _rel(PROOF),
                                   'perVariant': _proof_summary(proof)},
                    residentSwapPlan={'status': swap['status'], 'file': _rel(SWAP),
                                      'variantUse': swap['variantUse'], 'notCast': swap['variantsNotCastOnResidents']},
                    resume=plan, commands=commands)

    import unreal as u
    if Path(u.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed.get_game_world():
        raise RuntimeError('Live PIE world; never import against it')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; save or discard first')
    procs = _editor_processes()
    if procs['available'] and len(procs['pids']) > 1:
        raise RuntimeError('More than one UnrealEditor.exe alive (%s): a zombie makes saves fail silently. '
                           'Close it before importing.' % procs['pids'])

    marker = _load_marker(sp)
    for done, info in marker['completed'].items():
        if not u.EditorAssetLibrary.does_directory_exist(sp['namespace'] + '/' + done):
            raise RuntimeError('Marker says %s is complete but its folder is missing; inspect %s' % (done, info))
    if variants:
        chosen = list(variants)
        if len(chosen) != len(set(chosen)) or any(v not in sp['visualScales'] for v in chosen):
            raise RuntimeError('Unknown/duplicate variant')
        already = [v for v in chosen if v in marker['completed']]
        if already:
            raise RuntimeError('Already imported per marker: %s. Use a fresh variant list.' % already)
    else:
        chosen = plan['next']
    if not chosen:
        return dict(status='ALL_NINE_ALREADY_IMPORTED', marker=marker, namespace=sp['namespace'])
    for v in chosen:
        path = sp['namespace'] + '/' + v
        if u.EditorAssetLibrary.does_directory_exist(path) or (ROOT / 'Content' / path[6:]).exists():
            raise RuntimeError('Fresh variant folder required for %s; a partial import is preserved there, '
                               'inspect its receipt instead of rerunning over it' % v)

    base = helper('release_pilgrim_v3')
    base.DEST = sp['namespace']
    base.PROGRESS = BATCH_MARKER
    units = helper('release_amah48_candidate')
    protected = units.offline_plan()
    crowd = helper('release_resident_crowd')
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    snapshot = crowd._scene_snapshot(u, actors)
    v2_before = {p: sha(ROOT / 'Content' / p) for p in sp['protectedV2Assets']}
    bones = base.author().skeleton()
    base_spec = json.loads(base.SPEC.read_text(encoding='utf-8-sig'))
    original_import = base._import
    native_proofs = {}

    def checked_import(ue, tools, assets, filename, folder, name=None):
        objects = original_import(ue, tools, assets, filename, folder, name)
        skeletal = [x for x in objects if isinstance(x, ue.SkeletalMesh)]
        if skeletal:
            vid = folder.rsplit('/', 1)[1]
            if len(skeletal) != 1:
                raise RuntimeError('One skeletal mesh per variant required for ' + vid)
            skeleton = skeletal[0].get_editor_property('skeleton')
            path = base._path(skeleton)
            if not path or not path.startswith(folder + '/'):
                raise RuntimeError('Importer reused a foreign/V2 skeleton (%s); unsafe retarget refused' % path)
            clips = [x for x in objects if isinstance(x, ue.AnimSequence)]
            if len(clips) != 4:
                raise RuntimeError('Four GLB-native clips required for %s, got %d' % (vid, len(clips)))
            for clip in clips:
                if base._path(clip.get_editor_property('skeleton')) != path:
                    raise RuntimeError('Clip %s is not on the variant skeleton' % base._path(clip))
            entry = next(v for v in base_spec['variants'] if v['id'] == vid)
            row, problems = base._skeletal_readback(ue, skeletal[0], clips, entry, bones)
            row['materialSlots'] = [{'slot': str(m.get_editor_property('material_slot_name')),
                                     'material': base._path(m.get_editor_property('material_interface'))}
                                    for m in skeletal[0].get_editor_property('materials')]
            native_proofs[vid] = row
            if problems or row.get('boneNamesMatchAuthoredRig') is not True or row.get('frameMatched') != 'interchange':
                raise RuntimeError('Native rest-pose/clip proof failed for %s: %s' % (vid, problems))
        return objects
    base._import = checked_import

    receipt = {'utc': utc(), 'stamp': stamp(), 'status': 'started', 'namespace': sp['namespace'],
               'batch': chosen, 'editorProcesses': procs, 'restPoseProofOffline': _rel(PROOF),
               'nativeProofs': native_proofs, 'protectedV2Before': v2_before}
    receipt_path = OUT / ('review-native-' + receipt['stamp'] + '.json')

    def flush():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    flush()
    failure = None
    result = None
    try:
        result = base.run(apply=True, batch=len(chosen), variants=chosen, fresh=True)
        receipt['baseReceipt'] = result
        if result['status'] != 'IMPORTED_AND_READ_BACK_VISUAL_REVIEW_PENDING':
            raise RuntimeError('Import readback not clean: ' + result['status'] + ' ' + repr(result.get('problems')))
        for rb in result['readback']:
            vid = rb['id']
            marker['completed'][vid] = {'utc': utc(), 'receipt': _rel(receipt_path),
                                        'skeletalMesh': rb['skeletal']['asset'], 'skeleton': rb['skeletal']['skeleton'],
                                        'animations': rb['skeletal']['animations'], 'staticMesh': rb['static']['asset'],
                                        'materialSlots': native_proofs.get(vid, {}).get('materialSlots'),
                                        'facing': native_proofs.get(vid, {}).get('facing'),
                                        'visualComponentScale': sp['visualScales'][vid]}
        marker['batches'].append({'utc': utc(), 'variants': chosen, 'receipt': _rel(receipt_path)})
        MARKER.write_text(json.dumps(marker, indent=2) + '\n', encoding='utf-8')
        receipt['status'] = 'IMPORTED_NO_PLACEMENT_VISUAL_REVIEW_PENDING'
        receipt['marker'] = marker
        receipt['recommendedVisualComponentScales'] = {v: sp['visualScales'][v] for v in chosen}
        receipt['placement'] = 'Not applied; see resident-swap-plan.json; capsule and sole alignment need PIE review'
        receipt['next'] = next_batch(batch)
    except Exception as error:                                       # noqa: BLE001
        failure = error
        receipt['status'] = 'FAILED_PRESERVE_PARTIAL_INSPECT_RECEIPT'
        receipt['error'] = repr(error)
        raise
    finally:
        guard = []
        try:
            if units.offline_plan() != protected:
                guard.append('protected architecture plan changed')
            if crowd._scene_snapshot(u, actors) != snapshot:
                guard.append('scene snapshot changed')
            after = {p: sha(ROOT / 'Content' / p) for p in sp['protectedV2Assets']}
            if after != v2_before:
                guard.append('V2 assets changed: ' + repr([p for p in after if after[p] != v2_before[p]]))
            for path, value in sp['frozenFiles'].items():
                if sha(ROOT / path) != value:
                    guard.append('frozen input changed: ' + path)
        except Exception as error:                                   # noqa: BLE001
            guard.append('guard evaluation failed: ' + repr(error))
        receipt['postGuards'] = guard or ['clean']
        flush()
        if guard and failure is None:
            raise RuntimeError('Protected scene/map/assets changed during import: ' + '; '.join(guard))
    return receipt


def write_spec():
    """Refreeze the hashes of the inputs this wrapper guards. Review the diff before trusting it."""
    sp = spec()
    for path in list(sp['frozenFiles']):
        sp['frozenFiles'][path] = sha(ROOT / path)
    sp['frozen'] = utc()
    SPEC.write_text(json.dumps(sp, indent=2) + '\n', encoding='utf-8')
    return sp['frozenFiles']


if __name__ == '__main__':
    if '--write-spec' in sys.argv:
        print(json.dumps(write_spec(), indent=2))
    else:
        print(json.dumps(run(), indent=2, default=str))

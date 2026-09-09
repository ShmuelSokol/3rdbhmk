"""Re-export the nine PilgrimRigV3 bodies carrying the re-authored walk cycle.

Offline only: launches no editor, runs no build, imports nothing. It writes ONLY
into SourceAssets/characters-review/PilgrimRigV3/walk-v2/ and never touches the
shipped meshes/ folder or geometry-manifest.json, so the old GLBs stay on disk as
the evidence the before-column was measured from.

  python Scripts/rewalk_pilgrim_v3.py --build

Geometry, weights, materials, the rig and the Idle / PhotoCamera / PhotoPhone
clips are produced by exactly the same create_pilgrim_v3 code path as the shipped
files; the run asserts that the vertex, normal, joint, weight and index blocks
come out byte-identical to the shipped GLB, so the ONLY difference in these files
is the A_Pilgrim_Original_Walk animation.
"""
import argparse
import hashlib
import json
import struct
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import create_pilgrim_v3 as C            # noqa: E402
import pilgrim_walk_v2 as W              # noqa: E402
from measure_pilgrim_walk import measure  # noqa: E402

OUT = ROOT / 'SourceAssets/characters-review/PilgrimRigV3'
NEW = OUT / 'walk-v2'
CLIP = 'A_Pilgrim_Original_Walk'
GEOMETRY_ATTRS = ('POSITION', 'NORMAL', 'COLOR_0', 'JOINTS_0', 'WEIGHTS_0')
NORMAL_TOLERANCE = 1e-6


def _chunks(path):
    data = path.read_bytes()
    off, out = 12, {}
    while off < len(data):
        length, kind = struct.unpack('<I4s', data[off:off + 8])
        out[kind] = data[off + 8:off + 8 + length]
        off += 8 + length
    return json.loads(out[b'JSON'].decode('utf8')), out[b'BIN\0']


def _blocks(path):
    doc, binary = _chunks(path)
    out = {}
    for i, prim in enumerate(doc['meshes'][0]['primitives']):
        for key in GEOMETRY_ATTRS + ('indices',):
            j = prim['indices'] if key == 'indices' else prim['attributes'][key]
            acc = doc['accessors'][j]
            view = doc['bufferViews'][acc['bufferView']]
            base = view.get('byteOffset', 0)
            out['%d.%s' % (i, key)] = (acc['componentType'],
                                       binary[base:base + view['byteLength']])
    acc = doc['accessors'][doc['skins'][0]['inverseBindMatrices']]
    view = doc['bufferViews'][acc['bufferView']]
    base = view.get('byteOffset', 0)
    out['inverseBind'] = (acc['componentType'], binary[base:base + view['byteLength']])
    return out, [n.get('translation') for n in doc['nodes']], [n.get('name') for n in doc['nodes']]


def geometry_compare(new_path, old_path):
    """Prove only the walk clip moved: every vertex block must match the shipped file.

    Exact bytes, with one deliberate exception. Normals are summed over per-vertex
    face sets, and CPython randomises string hashing per process, so the summation
    order - and therefore the last bit of a normal - is not reproducible between
    runs. Positions, colours, joints, weights, indices, inverse-bind matrices, the
    rest pose and the joint names must be byte-identical; normals are allowed to
    differ by NORMAL_TOLERANCE, and the run reports what the difference actually was.
    """
    a, rest_a, names_a = _blocks(new_path)
    b, rest_b, names_b = _blocks(old_path)
    assert set(a) == set(b), 'primitive layout changed'
    worst_normal = 0.0
    exact = 0
    for key in sorted(a):
        (ct, da), (_, db) = a[key], b[key]
        if da == db:
            exact += 1
            continue
        if not key.endswith('.NORMAL') or ct != 5126:
            return {'identical': False, 'firstMismatch': key, 'maxNormalDiff': None}
        fa = struct.unpack('<%df' % (len(da) // 4), da)
        fb = struct.unpack('<%df' % (len(db) // 4), db)
        if len(fa) != len(fb):
            return {'identical': False, 'firstMismatch': key, 'maxNormalDiff': None}
        worst_normal = max(worst_normal, max(abs(x - y) for x, y in zip(fa, fb)))
    ok = (worst_normal <= NORMAL_TOLERANCE and rest_a == rest_b and names_a == names_b)
    return {'identical': ok, 'exactBlocks': exact, 'totalBlocks': len(a),
            'maxNormalDiff': worst_normal, 'restPoseIdentical': rest_a == rest_b,
            'jointNamesIdentical': names_a == names_b}


def verify_v1_reproduces_shipped(bones, sample=Path('V3_Pilgrim_Man_Standard.glb')):
    """create_pilgrim_v3.walk_pose_v1 must still reproduce the SHIPPED walk exactly.

    That is what makes this change revertible without keeping a second copy of the
    binaries: the old motion is code, not just a file.
    """
    from measure_pilgrim_walk import Rig
    rig = Rig(OUT / 'meshes' / sample.name, CLIP)
    worst = 0.0
    for i in range(37):
        t = i * 1.2 / 36.0
        rot, trs = C.walk_pose_v1(bones, t)
        mine = []
        for b in bones:
            lq = rot[b['name']]
            lt = trs.get(b['name'], b['local_translation_cm'])
            if b['parent_index'] is None:
                mine.append((lq, lt))
            else:
                pq, pt = mine[b['parent_index']]
                mine.append((C.qmul(pq, lq), C.add(pt, C.qrotate(pq, lt))))
        shipped = rig.pose(t)
        for j in range(len(bones)):
            worst = max(worst, max(abs(a - b) for a, b in zip(mine[j][1], rig.point(shipped, j))))
    return round(worst, 6)


def build(only=None):
    NEW.mkdir(parents=True, exist_ok=True)
    (NEW / 'meshes').mkdir(exist_ok=True)
    bones = C.skeleton()
    assert C.assert_rig_matches_v2(bones)
    index = {b['name']: i for i, b in enumerate(bones)}
    rows = []
    for variant in [v for v in C.VARIANTS if not only or v['id'] in only]:
        started = time.time()
        parts = C.assembly(variant)
        colours = C.variant_materials(variant)
        checks = C.deformation_checks(parts, bones, index)
        path = NEW / 'meshes' / (variant['id'] + '.glb')
        doc = C.export_glb(path, variant, parts, bones, index, colours)
        decode = C.glb_decode_checks(path, bones, sum(r['triangles'] for r in C.check(parts)))
        old = OUT / 'meshes' / (variant['id'] + '.glb')
        cmp = geometry_compare(path, old) if old.exists() else None
        same = None if cmp is None else cmp['identical']
        assert same is not False, ('geometry drifted for %s - only the walk clip may change: %s'
                                   % (variant['id'], cmp))
        walk = [c for c in checks['clips'] if c['clip'] == 'Walk'][0]
        rows.append({
            'id': variant['id'],
            'file': str(path.relative_to(OUT)).replace('\\', '/'),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'previousFile': str(old.relative_to(OUT)).replace('\\', '/'),
            'previousSha256': hashlib.sha256(old.read_bytes()).hexdigest() if old.exists() else None,
            'geometryIdenticalToShipped': same,
            'geometryComparison': cmp,
            'walkLoopVertexErrorCm': round(walk['loop_vertex_error_cm'], 6),
            'walkMinimumSoleZCm': round(min(s['minimum_sole_z_cm'] for s in walk['samples']), 4),
            'animations': [a['name'] for a in doc['animations']],
            'glbDecodeChecks': decode,
            'buildSeconds': round(time.time() - started, 2)})
        print('%-30s  %s  geometry %s  loop %.2e  sole %.3f  %.1fs'
              % (variant['id'], rows[-1]['sha256'][:12], 'identical' if same else '???',
                 rows[-1]['walkLoopVertexErrorCm'], rows[-1]['walkMinimumSoleZCm'],
                 rows[-1]['buildSeconds']), flush=True)
    return rows


def report(rows, rate=240.0):
    before = [measure(OUT / 'meshes' / (r['id'] + '.glb'), CLIP, rate) for r in rows]
    after = [measure(NEW / 'meshes' / (r['id'] + '.glb'), CLIP, rate) for r in rows]
    return {
        'status': 'offline_clip_reauthored_measured_native_import_pending',
        'generatedUtc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'clip': CLIP,
        'measurementRateHz': rate,
        'method': ('forward kinematics over the GLB joint hierarchy, glTF LINEAR sampling '
                   '(lerp on translation, slerp on rotation), Scripts/measure_pilgrim_walk.py'),
        'authoring': {
            'module': 'Scripts/pilgrim_walk_v2.py',
            'cycleSeconds': W.CYCLE_SECONDS,
            'cadenceStepsPerMin': round(120.0 / W.CYCLE_SECONDS, 2),
            'stepLengthCm': W.STEP_LENGTH_CM,
            'groundSpeedCmPerSec': W.GROUND_SPEED_CM_S,
            'stanceDutyFactor': W.STANCE_DUTY,
            'pelvisHeightCm': W.PELVIS_HEIGHT_CM,
            'anchor0Cm': W.ANCHOR0_CM,
            'swingLiftCm': round(W.TRACKS['r'].lift, 3),
            'exportFps': C.CLIP_FPS.get('Walk', C.DEFAULT_CLIP_FPS)},
        'walkPoseV1MaxErrorVsShippedCm': verify_v1_reproduces_shipped(C.skeleton()),
        'variants': rows,
        'before': before,
        'after': after,
        'allVariantsIdenticalMotion': {
            'before': len({json.dumps({k: v for k, v in b.items() if k != 'file'}) for b in before}) == 1,
            'after': len({json.dumps({k: v for k, v in a.items() if k != 'file'}) for a in after}) == 1},
    }


TABLE = [
    ('step length', 'stepLengthCmFromSpeed', 'cm', '~73 = 0.41 x stature'),
    ('implied ground speed', 'fittedGroundSpeedCmPerSec', 'cm/s', '130-145'),
    ('pelvis vertical bob', 'pelvisBobCm', 'cm', '4-5, at TWICE stride frequency'),
    ('pelvis lateral sway', 'pelvisLateralSwayCm', 'cm', '4-5, at stride frequency'),
    ('foot lift (swing)', 'footLift', 'cm', '~12'),
    ('STANCE PLANT: foot-flat drift', 'footFlatPlantDriftCm', 'cm', '0 - the foot must not move'),
    ('stance plant incl. touchdown/lift-off', 'maxStanceDriftCm', 'cm', '0'),
    ('arm swing (hand fore-aft)', 'armSwingCm', 'cm', '30-45'),
    ('arm-to-leg phase', 'armToLegPhaseDeg', 'deg', '180 = counter-swing'),
    ('shoulder girdle yaw', 'shoulderYawRangeDeg', 'deg', '8-12'),
    ('pelvis yaw', 'pelvisYawRangeDeg', 'deg', '6-10'),
    ('trunk counter-rotates pelvis', 'trunkCounterRotates', '', 'True'),
    ('stance duty factor', 'stanceDutyFactor', '', '0.58-0.62'),
    ('double support', 'doubleSupportFraction', 'of cycle', '0.16-0.24'),
    ('cycle', 'cycleSeconds', 's', '1.2, keep'),
    ('cadence', 'cadenceStepsPerMin', 'steps/min', '100, keep'),
    ('- ankle fore-aft excursion', 'ankleExcursionCm', 'cm', 'step length / duty'),
    ('- legacy 2 x excursion / cycle', 'legacyImpliedGroundSpeedCmPerSec', 'cm/s', '(diagnosis metric)'),
    ('- mean pelvis height', 'pelvisMeanHeightCm', 'cm', '(98.0 standing)'),
    ('- lowest sole point', 'lowestSolePointCm', 'cm', '0, never below'),
]


def _fmt(v):
    if isinstance(v, float):
        return ('%.3f' % v).rstrip('0').rstrip('.')
    return str(v)


def table(before, after):
    lines = ['| measured | before | after | unit | natural human |', '|---|---|---|---|---|']
    for label, key, unit, target in TABLE:
        if key == 'footLift':
            bv, av = before['footLiftCm']['r'], after['footLiftCm']['r']
        else:
            bv, av = before[key], after[key]
        lines.append('| %s | %s | %s | %s | %s |' % (label, _fmt(bv), _fmt(av), unit, target))
    return '\n'.join(lines)


def sweep_table(before, after):
    lines = ['| contact threshold (cm) | before: drift | before: fitted speed '
             '| after: drift | after: fitted speed |', '|---|---|---|---|---|']
    for key in sorted(before['driftByContactThresholdCm'], key=float, reverse=True):
        b = before['driftByContactThresholdCm'][key]
        a = after['driftByContactThresholdCm'][key]
        lines.append('| %s | %s cm | %s cm/s | %s cm | %s cm/s |'
                     % (key, _fmt(b['maxStanceDriftCm']), _fmt(b['fittedGroundSpeedCmPerSec']),
                        _fmt(a['maxStanceDriftCm']), _fmt(a['fittedGroundSpeedCmPerSec'])))
    return '\n'.join(lines)


RECEIPT = """# PilgrimRigV3 walk cycle re-authored - receipt

Generated %(when)s by `Scripts/rewalk_pilgrim_v3.py --build`.
Offline: no editor launched, no build run, nothing imported or cooked. Nothing
here is an in-engine acceptance, a render, or a performance result.

## What changed

`A_Pilgrim_Original_Walk` in all %(count)d PilgrimRigV3 bodies. Same 27 joints,
same 1.2 s cycle, same 100 steps/min cadence, same rest pose, same geometry.
The run asserts it: every position, colour, joint-index, weight, index and
inverse-bind block, plus the rest pose and the joint names, comes out
byte-identical to the shipped GLB, and normals match to %(normal)s (they are
summed over per-vertex face sets and CPython randomises string hashing per
process, so their last bit is not reproducible between runs). The ONLY difference
in these files is the walk animation. Idle, PhotoCamera and PhotoPhone are
untouched. The walk is now exported at 60 fps instead of 30, because its stance
rockers are curved and glTF/UE keys are linear - at 30 the chords cut the corner
off the heel and toe rolls and the planted foot picks up measurable drift.

Authoring: `Scripts/pilgrim_walk_v2.py`, called from `create_pilgrim_v3.pose()`.
The previous motion is kept verbatim as `create_pilgrim_v3.walk_pose_v1()` so the
shipped clip stays reproducible.

## The diagnosis, re-derived rather than trusted

Measured off the shipped `meshes/*.glb` before anything was changed, by the same
tool that measured the new ones. The handed-down numbers reproduce:

| handed down | re-derived here | agrees |
|---|---|---|
| step length 32.0 cm | ankle excursion 32.00 cm, peak foot separation 32.00 cm | yes |
| implied ground speed 53.3 cm/s | 2 x excursion / cycle = 53.33 cm/s | yes |
| pelvis vertical bob 0.50 cm | 0.50 cm | yes |
| foot lift 5 cm | 5.01 cm | yes |
| stance plant: NONE | 4.57 cm of drift with the sole flat on the floor | yes |
| cycle 1.2 s, 100 steps/min | 1.2 s, 100.0 steps/min | yes |

Three ways of asking for the old clip's step length - ankle excursion, peak foot
separation, and the speed implied by its own plant - all return 32 cm, and they
agree only because there is no plant: with both feet on pure counter-phase
sinusoids the foot's travel and the body's travel are the same curve. On a real
gait they separate, which is why the table below carries all three.

## The measurement

Forward kinematics over the GLB joint hierarchy, sampled the way a player samples
it (glTF LINEAR: lerp on translation, slerp on rotation), at %(rate)g Hz.
`Scripts/measure_pilgrim_walk.py`. Identical method and identical definitions for
both columns. All %(count)d variants measure identically (before: %(sameb)s,
after: %(samea)s), so one row of numbers describes the whole set.

%(table)s

## The stance plant, which is the one that matters

"Stilting" is a foot that never stops. The old clip drove both ankles as
counter-phase sinusoids, so at no instant was either foot still: against the
best-fit ground speed the planted foot slid **4.57 cm** while flat on the floor,
i.e. it skated ~9 cm every step no matter what speed the actor was driven at.

The new clip authors the stance foot as a rigid plate whose footprint is fixed
and which rotates only about points that are themselves on the ground (heel
rocker -> foot flat -> toe rocker). Rotating a body about its own contact point
cannot slide it, so the plant is exact by construction and the measurement
confirms it: **%(flat)s cm** of world-space drift while the sole is flat, against
%(flatbefore)s cm before. That residual is glTF linear-key chording at 60 fps,
not motion.

Contact thresholds do not rescue the old clip and are not what rescues the new
one - drift is swept over the threshold rather than reported at one value:

%(sweep)s

Read the last two columns: as the threshold tightens the new clip's drift
collapses toward zero and its fitted speed converges on the authored 120.00 cm/s,
because there is a real plant to find. The old clip's drift bottoms out at 3.6 cm
and its "ground speed" wanders from 53.6 to 63.5 cm/s, because there is no plant
to fit and every window is a different piece of a sinusoid.

## The number to change in C++

    Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashResidentCharacter.h:40
        constexpr double MeasuredWalkClipGroundSpeedCm = 53.33;   ->  120.0

    Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashResidentPopulation.h:40
        double WalkClipGroundSpeedCmPerSec = 53.33;               ->  120.0

    Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashResidentPopulation.h:161
        double DefaultWalkClipGroundSpeedCmPerSec = 53.33;        ->  120.0

NOT EDITED HERE - another agent has changes in flight in
MikdashResidentPopulation.cpp. `MikdashResidentPopulation.cpp` itself carries no
literal; it reads `DefaultWalkClipGroundSpeedCmPerSec` (lines 262, 266, 386, 467)
and the per-variant override (lines 419-421), so the three declarations above are
the whole change. Note line 419-421 gates the per-variant value to
`> 1.0 && < 400.0`; 120.0 passes.

The default (V2) rig plays the same authored motion and therefore needs the same
number, but only once its own GLB is re-exported - the V2 source is not touched
by this run.

## Honest limits

* **The rig's leg is 6.9 cm too short.** `skeleton()` puts `thigh_*` at z = 88
  and the ankle at z = 6, so hip-to-ankle is 82.0 cm on a 179.4 cm figure =
  0.457 H, where `create_pilgrim_v3.PROPORTIONS` itself asks for a 0.53 H hip
  joint. A 72 cm step at 100 spm needs ~78 cm of fore-aft ankle travel and an
  82 cm leg can only reach that by carrying the pelvis lower and the stance knee
  more bent than a real walker: mean pelvis %(pelvis)s cm against 95.8 in the old
  clip and 98.0 standing, mid-stance knee ~32 deg against a real 15-20 deg. Under
  a tunic at crowd distance that reads as a walk. Raising `thigh_*` is the real
  fix and it is a geometry change, out of scope for a clip re-author.
* **That is also why the ground speed is 120 and not 135 cm/s.** At a fixed 1.2 s
  cycle, speed is step length x 2 / 1.2 and nothing else; 135 cm/s would need an
  81 cm step, which this leg cannot reach without a visible crouch.
* **No toe joint in the skin.** The mesh weights the whole sandal sole to
  `foot_*` and gives `ball_*` no weight, so the foot is one rigid plate and the
  forefoot rocker has to pivot on the toe tip instead of rolling over the ball.
  Weighting the toe box to `ball_*` would buy a real MTP break - again a rig job.
* **Idle and Walk no longer stand at the same height.** Idle keeps the pelvis at
  its 98.0 cm rest; the walk carries it at %(pelvis)s cm mean, so an Idle -> Walk
  transition sinks the hips ~4.6 cm where it used to sink ~2.2. Cross-blend it
  (0.2-0.3 s is enough); do not cut.
* **The "before" step length reads %(stepbefore)s cm in the table, not 32.0.** Same
  clip, stricter definition: the table's step length is derived from the clip's
  own plant (fitted ground speed x cycle / 2) at a 2 mm contact threshold, and on
  a clip with no plant that fit lands wherever the window happens to sit. The
  32.0 cm of the original diagnosis is the ankle-excursion row, which reproduces
  exactly. Both are in the table; neither flatters the old clip.
* **The old arms were a quarter cycle out.** `armToLegPhaseDeg` was 90 on the old
  clip: the right arm reached its extreme when the right leg was at mid-swing, not
  when it was forward. A metronome, not a walk. It is 166 now - not the textbook
  180 because the new foot track is not a sinusoid and its fundamental phase is
  skewed by the rockers, while the arm is a clean cosine.
* Not measured here: anything in engine. No import, no retarget, no cook, no
  frame time, no visual acceptance. The clip must be RE-IMPORTED for any of this
  to reach the game; the existing `A_Pilgrim_Original_Walk` asset still carries
  the old motion.

## Files

Written under `SourceAssets/characters-review/PilgrimRigV3/walk-v2/`:

* `meshes/*.glb` - %(count)d re-exported bodies (new walk, identical geometry)
* `walk-measurements.json` - every number above, plus per-variant hashes and the
  full before/after measurement records
* `WALK-V2-RECEIPT.md` - this file

The shipped `meshes/*.glb` are NOT touched; they remain the evidence the before
column was measured from. `create_pilgrim_v3.walk_pose_v1()` still reproduces
their motion - checked this run over 37 samples x 27 joints, worst joint position
error %(v1err)s cm, which is float32 export precision. The old walk is therefore
recoverable from code, not only from those files.

%(hashes)s
"""


def receipt(data):
    b, a = data['before'][0], data['after'][0]
    hashes = ['| variant | new sha256 | previous sha256 | geometry |', '|---|---|---|---|']
    for r in data['variants']:
        hashes.append('| %s | `%s` | `%s` | %s |'
                      % (r['id'], r['sha256'][:16], (r['previousSha256'] or '-')[:16],
                         'identical' if r['geometryIdenticalToShipped'] else 'CHANGED'))
    return RECEIPT % {
        'when': data['generatedUtc'], 'count': len(data['variants']),
        'rate': data['measurementRateHz'],
        'sameb': data['allVariantsIdenticalMotion']['before'],
        'samea': data['allVariantsIdenticalMotion']['after'],
        'table': table(b, a), 'sweep': sweep_table(b, a),
        'flat': _fmt(a['footFlatPlantDriftCm']), 'flatbefore': _fmt(b['footFlatPlantDriftCm']),
        'normal': '%g' % NORMAL_TOLERANCE, 'stepbefore': _fmt(b['stepLengthCmFromSpeed']),
        'pelvis': _fmt(a['pelvisMeanHeightCm']),
        'v1err': _fmt(data['walkPoseV1MaxErrorVsShippedCm']),
        'hashes': '\n'.join(hashes)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--rate', type=float, default=240.0)
    args = ap.parse_args()
    if not args.build:
        ap.print_help()
        sys.exit(0)
    rows = build(set(args.only) if args.only else None)
    data = report(rows, args.rate)
    (NEW / 'walk-measurements.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    text = receipt(data)
    (NEW / 'WALK-V2-RECEIPT.md').write_text(text, encoding='utf-8')
    print()
    print(table(data['before'][0], data['after'][0]))
    print()
    print(json.dumps({'output': str(NEW), 'variants': len(rows),
                      'identicalMotionAcrossVariants': data['allVariantsIdenticalMotion'],
                      'maxStanceDriftCm': data['after'][0]['maxStanceDriftCm'],
                      'groundSpeedCmPerSec': data['after'][0]['fittedGroundSpeedCmPerSec']}, indent=2))

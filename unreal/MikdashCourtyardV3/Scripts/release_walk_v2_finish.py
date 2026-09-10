"""Finish walk-v2: the Kohen Gadol, the stale neutral phase, and the pilot population.

WHAT THIS IS. `Scripts/release_walk_v2.py` imported the re-authored walk and repointed the
six cast resident variants on both maps. Its own receipt lists three things it deliberately
left behind. This script closes those three and nothing else.

  1. THE KOHEN GADOL. `AMikdashServiceActor` is a different system from
     `AMikdashResidentPopulation`: it has NO play-rate matching at all. `UpdateBodyAnimation`
     calls `BodyMesh->SetAnimation(Desired); Play(true)` and never touches the play rate, so
     the clip always runs at 1.0 and carries whatever ground speed it was authored with. The
     single number that decides whether his stride matches his translation is therefore
     `WalkSpeedCmPerSec` (python `walk_speed_cm_per_sec`), the actor's own EditAnywhere
     float, which is what `Movement->MaxWalkSpeed` is set from on both the grounded and the
     kinematic path. It is NOT hardcoded: the header default is 90.0f and the map serialises
     an instance value. There is no `WalkClipGroundSpeedCmPerSec` and no `WalkClipNeutralPhase`
     on this class.

     One thing near it IS hardcoded and matters: when the body resolves as
     `EMikdashServiceBodySource::PilgrimRigV3` (which is what Main50 does, through
     `MeshFallbacks[0]`), `SpawnBody` runs a `ResolveClip` lambda that loads
     `.../V3_Pilgrim_Man_Standard/V3_Pilgrim_Man_Standard/SkeletalMeshes/
     V3_Pilgrim_Man_StandardA_Pilgrim_Original_Walk` by literal path whenever `WalkAnimation`
     is null or belongs to another skeleton. That is why Main50's kohen, with no walk clip
     set, would still play the OLD clip. The lambda's FIRST branch keeps a clip that is
     already valid and on the body's skeleton -- `retained compatible <path>` -- so SETTING
     the property to the WalkV2 clip overrides the hardcoded fallback with no rebuild. No
     UnrealBuildTool is run here and none is needed.

     HIS STILT IS ALREADY MEASURED IN A FRAME, and this is the one number in the whole
     walk-v2 effort that is not a static readback. `SourceAssets/service-review/
     candidate-runtime-20260909T070801049654Z.json` is a PIE run of the full 290 s candidate
     route (`Scripts/probe_service_candidate48.py`, which calls `start_service()` because
     `start_on_begin_play` is False on both maps). Its `samples` array carries 569 timestamped
     feet positions; differencing them gives 196 moving intervals whose median, p90 and max
     2D speed are all 90.00 cm/s exactly -- he translates at precisely `WalkSpeedCmPerSec`.
     The clip he is playing, the OLD V3_Pilgrim_Man_Standard walk, was fitted in engine at
     60.48 cm/s. 90.00 / 60.48 = 1.49: his feet slide forward under him by half again their
     stride, every step, for the whole route. That is the stilt, observed.

     It also settles that BOTH numbers have to move together. Repointing him at the new clip
     and leaving the speed at 90 would give 90 / 119.95 = 0.75 -- feet dragging backward
     instead of skating forward, no better. Setting the speed without the clip would give
     119.95 / 60.48 = 1.98, worse than today. This script always writes the pair.

     The cost of the fix, stated plainly: he walks at 120 cm/s instead of 90, so his authored
     loop shortens from 290.5 s to 266.9 s. That is still inside the spec's own 180..360 s
     window (`Scripts/release_kohen_service.spec.json`, `expectedDerivedPlan`), but the spec's
     `actorProperties.walk_speed_cm_per_sec: 90.0` no longer describes the actor. The spec
     file is deliberately NOT edited here: `configure_service_body_v3.py` hashes it into its
     verification receipts. The divergence is recorded instead.

  2. `WalkClipNeutralPhase` is 0.25 on every variant on both maps, taken from the OLD clip's
     sinusoid crossing. It is the phase the walk clip is entered at from Idle:
     `Phase = Frac(WalkClipNeutralPhase + Body->GetGaitPhase01())`. The new clip's feet cross
     somewhere else. This script MEASURES the crossing IN ENGINE off the imported
     AnimSequence, by the same `AnimPoseExtensions.get_anim_pose_at_time` component-space
     sampling at 240 Hz that `release_walk_v2.py` used for the gait numbers, and writes the
     measured value. The offline claim (0.285 / 0.785) is recorded next to it and is NOT what
     gets written; if the engine disagrees, the engine wins and the receipt says so.

  3. THE PILOT POPULATION. `RELEASE_ResidentPopulation` still points its population-level
     `WalkAnimation` at `PilgrimRigV2A_Pilgrim_Original_Walk`. The V2 GLB was not
     re-exported, so there is nothing to repoint it at -- the fix is the other half of the
     choice: set the per-actor `DefaultWalkClipGroundSpeedCmPerSec` to the speed that clip
     ACTUALLY carries, measured in engine by the same method, instead of the header's new
     120.0. `RELEASE_PeopleV3Population` carries the same two default fields against the same
     V2 clip, so it is corrected the same way; nothing is expected to take that path (see the
     evidence block in the receipt) but the landmine is removed either way.

     WHO ACTUALLY READS THOSE DEFAULTS, settled from the source before any map was opened.
     `ResolveBody` hands back the default body -- and with it the population-level
     `WalkAnimation` and `DefaultWalkClipGroundSpeedCmPerSec` -- only when a person's
     `body.variant` is empty, unregistered, or registered but unusable. Both staged
     directories (`Content/Distribution/People/people.json` and `people-candidate48.json`,
     24 people each) give every single person a variant, and the six they name are exactly
     the six registered on `RELEASE_PeopleV3Population`: Man_Standard 5, Woman_Young 5,
     Man_Heavy 4, Woman_Elder 4, Man_Elder 4, Youth 2. Zero of the 24 can reach the default.
     The only bodies that CAN are the pilot's five placed ones, because
     `BindConfiguredBodies` never consults `BodyVariants` at all -- it assigns
     `Plan.WalkClipGroundSpeedCmPerSec = DefaultWalkClipGroundSpeedCmPerSec` unconditionally.
     And those five were retired on 2026-09-09: `Scripts/release_retire_resident_pilot.py`
     read back `activate_reviewed_pilot_on_begin_play = false` and all five bodies hidden
     with collision off, on both maps (`SourceAssets/runtime-review/people/retire-pilot-*`).
     So the 2.25x over-drive is real in the data but currently unreachable in play. It is
     corrected anyway, because "unreachable" here means one boolean away.

WHAT IT DOES NOT DO. It never imports, never re-exports, never touches a GLB, an old clip, a
skeleton, a skeletal mesh or any `.uasset` at all: every asset this run reads is opened
read-only and hashed before and after. It changes exactly three actors per map and refuses if
a fourth moves.

THREE NATIVE MODES, each guarded, each with a receipt.

  -FinishMeasure  Map-agnostic. Opens the six cast variants' WalkV2 clips, the old
                  V3_Pilgrim_Man_Standard clip and the V2 pilot clip, and measures each:
                  foot-crossing phases (the neutral phase) and the plant-fitted ground speed.
                  Writes walkv2-finish-measure-<stamp>.json. No map is loaded, nothing is
                  saved, and the protected hash set is compared before and after.

  -FinishApply -FinishTarget=Main50|Candidate48
                  Checkpoints the .umap, loads it, snapshots the scene, reads the three
                  actors, writes the planned values, saves, REOPENS the map from disk and
                  reads every number back off the reopened actors. Refuses if any actor
                  other than those three changed, or if the other map's bytes moved.

  -FinishRevert -FinishTarget=...
                  Restores the exact `before` block recorded in that target's newest apply
                  receipt, through the same save/reopen/readback path.

  -FinishApplyAll             Candidate48 then Main50 in one process, each a full guarded pass.
  -FinishRevertAndReapply -FinishTarget=...
                              Runs the revert for real and then puts the target back.
                  Both exist only because this box runs ONE engine and two other agents plus
                  a packaging cook queue behind it; neither weakens a guard.

Traps already paid for on this project and honoured here:
  * Interchange maps glTF (X, Y, Z) to UE (X, Z, Y); the rig's toes sit at component +Y.
    Forward is component +Y, which is why the population uses MeshRelativeYaw = -90.
  * Import markers store PACKAGE paths, native readback returns OBJECT paths; every compare
    normalises through _object_path first.
  * 5.8 setters return False even when they worked: nothing is trusted until it is read back
    off the REOPENED map.
  * A zombie UnrealEditor makes save_loaded_asset / save_current_level return False with no
    other symptom, so more than one live editor is refused up front.

Nothing here is a visual, PIE, cook or performance acceptance. Nobody has looked at the walk
in a frame.

Proven launch (one engine at a time; this box runs one):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough
      -ExecutePythonScript="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_walk_v2_finish.py"
      -FinishMeasure -unattended -nullrhi -NoSplash -abslog=<unique>
"""
import hashlib, importlib.util, json, re, shutil, sys, traceback
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/characters-review/PilgrimRigV3'
WALK2 = OUT / 'walk-v2'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')

SAMPLE_RATE_HZ = 240.0          # the rate release_walk_v2.py measured at; kept so numbers compare
CONFIRM_RATE_HZ = 960.0         # convergence check on one clip only
FORWARD_AXIS = 1                # component +Y, see the module docstring
OFFLINE_NEUTRAL_CLAIM = [0.285, 0.785]

V2_WALK = ('/Game/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes/'
           'PilgrimRigV2A_Pilgrim_Original_Walk')
KOHEN_FALLBACK_MESH = ('/Game/MikdashV3/Characters/PilgrimRigV3/V3_Pilgrim_Man_Standard/'
                       'V3_Pilgrim_Man_Standard/SkeletalMeshes/V3_Pilgrim_Man_Standard')
V3_POPULATION_LABEL = 'RELEASE_PeopleV3Population'
PILOT_LABEL = 'RELEASE_ResidentPopulation'
KOHEN_LABEL = {'Candidate48': 'RELEASE_KohenGadolService_Selected48_V1',
               'Main50': 'RELEASE_KohenGadolService'}
SERVICE_CLASS = '/Script/MikdashRuntime.MikdashServiceActor'

KOHEN_FIELDS = ('walk_animation', 'idle_animation', 'configured_mesh', 'walk_speed_cm_per_sec',
                'use_grounded_movement', 'start_on_begin_play', 'authored_body',
                'configured_body_visual_scale', 'configured_body_yaw_degrees',
                'min_loop_seconds', 'max_loop_seconds', 'repeat_interval_seconds')
KOHEN_WRITE = ('walk_animation', 'walk_speed_cm_per_sec')
POP_FIELDS = ('walk_animation', 'idle_animation', 'resident_mesh', 'people_directory_file',
              'default_walk_clip_ground_speed_cm_per_sec', 'default_walk_clip_neutral_phase',
              'default_mesh_relative_yaw', 'match_walk_clip_to_ground_speed',
              'vary_gait_per_resident', 'activate_reviewed_pilot_on_begin_play',
              'spawn_authored_people_on_begin_play')
POP_WRITE = ('default_walk_clip_ground_speed_cm_per_sec', 'default_walk_clip_neutral_phase')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stamp_now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def utc():
    return datetime.now(timezone.utc).isoformat()


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WALKV2 = _load('release_walk_v2_base', 'Scripts/release_walk_v2.py')
_object_path = WALKV2._object_path
_pose_at = WALKV2._pose_at
measure_clip = WALKV2.measure_clip
_read_variants = WALKV2._read_variants
_build_variants = WALKV2._build_variants
_guards = WALKV2._guards
_targets = WALKV2._targets
disk_umap = WALKV2.disk_umap
disk_uasset = WALKV2.disk_uasset


def receipt_path(kind, stamp):
    WALK2.mkdir(parents=True, exist_ok=True)
    return WALK2 / ('walkv2-finish-' + kind + '-' + stamp + '.json')


def imported_marker():
    return json.loads((WALK2 / 'walkv2-import-progress.json').read_text(encoding='utf-8-sig'))['completed']


def cast_variants():
    return sorted({r['variant'] for r in json.loads(
        (OUT / 'resident-swap-plan.json').read_text(encoding='utf-8-sig'))['residents']})


def clips_of_interest():
    """Every clip this run measures, as {key: object path}. Read-only, all of them."""
    marker = imported_marker()
    rows = {}
    for vid in cast_variants():
        rows['new:' + vid] = _object_path(marker[vid]['newWalk'])
    rows['old:V3_Pilgrim_Man_Standard'] = _object_path(marker['V3_Pilgrim_Man_Standard']['oldWalk'])
    rows['v2:PilgrimRigV2'] = _object_path(V2_WALK)
    return rows


def protected_hashes():
    """Every asset and map this run must not change."""
    out = {}
    marker = imported_marker()
    for vid, entry in marker.items():
        for path in list(entry['clips']) + [entry['oldWalk'], entry['skeleton']]:
            f = disk_uasset(_object_path(path))
            if f.is_file():
                out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    for path in (V2_WALK, KOHEN_FALLBACK_MESH):
        f = disk_uasset(_object_path(path))
        if f.is_file():
            out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    for key, target in _targets().items():
        f = disk_umap(target['map'])
        out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    return out


# ---------------------------------------------------------------------------------------
# Offline evidence: which bodies can possibly fall back to the population default.
# ---------------------------------------------------------------------------------------
def directory_census(relative):
    """Read the staged people directory a population actually loads and count body variants.

    `AMikdashResidentPopulation::ResolveBody` takes the DEFAULT body -- and therefore the
    population-level WalkAnimation and DefaultWalkClipGroundSpeedCmPerSec -- exactly when a
    person's `body.variant` is empty, or names a variant that is not registered on the actor,
    or names one whose mesh/clip assets are missing or off-skeleton. The first two are
    decidable offline off the directory plus the actor's variant ids; the third is decided in
    engine during the apply, off the reopened actor.
    """
    path = ROOT / 'Content' / relative
    doc = json.loads(path.read_text(encoding='utf-8-sig'))
    people = doc.get('people', [])
    counts, empty = {}, []
    for person in people:
        variant = ((person.get('body') or {}).get('variant') or '').strip()
        if not variant:
            empty.append(person.get('id'))
        else:
            counts[variant] = counts.get(variant, 0) + 1
    return dict(file=str(path.relative_to(ROOT)).replace('\\', '/'), sha256=sha(path),
                version=doc.get('version'), people=len(people),
                variantCounts=counts, peopleWithNoVariant=empty,
                peopleWithNoVariantCount=len(empty))


# ---------------------------------------------------------------------------------------
# In-engine measurement. Everything here reads the IMPORTED AnimSequence, never a GLB.
# ---------------------------------------------------------------------------------------
def measure_neutral_phase(ue, clip, rate=SAMPLE_RATE_HZ):
    """Where in the cycle do the two feet cross fore-aft? That is the neutral (passing) pose.

    Method, stated so it can be argued with. `WalkClipNeutralPhase` is the phase the walk
    clip is entered at when a body's own GaitPhase01 is 0, and the pose it should enter at is
    the one that reads as neutral from a standing idle: the moment the swinging foot passes
    the planted one and the two are level fore-aft. Sample the clip through
    `AnimPoseExtensions.get_anim_pose_at_time` in component space at `rate` -- the same call
    and the same rate release_walk_v2.py fitted the gait numbers with, so the phases below are
    comparable to those -- form d(t) = ball_r.y - ball_l.y along component +Y, and take every
    sign change of d over the CYCLIC sample ring, linearly interpolated between the bracketing
    samples. A symmetric gait gives exactly two, half a cycle apart. The one with the lower
    phase is written, which is the convention the stale 0.25 came from (the old clip crossed
    at 0.30 s of 1.2 s).
    """
    length = float(ue.AnimationLibrary.get_sequence_length(clip))
    options = ue.AnimPoseEvaluationOptions()
    n = max(8, int(round(length * rate)))
    fore, height = {'r': [], 'l': []}, {'r': [], 'l': []}
    for i in range(n):
        pose = _pose_at(ue, clip, length * i / n, options)
        for side in ('r', 'l'):
            v = ue.AnimPoseExtensions.get_bone_pose(pose, 'ball_' + side,
                                                    ue.AnimPoseSpaces.WORLD).translation
            fore[side].append(float((v.x, v.y, v.z)[FORWARD_AXIS]))
            height[side].append(float(v.z))
    delta = [fore['r'][i] - fore['l'][i] for i in range(n)]
    crossings = []
    for i in range(n):
        a, b = delta[i], delta[(i + 1) % n]
        if a == 0.0 and b != 0.0:
            frac = 0.0
        elif a * b < 0.0:
            frac = a / (a - b)
        else:
            continue
        phase = ((i + frac) / float(n)) % 1.0
        crossings.append(dict(
            phase=round(phase, 6),
            timeSec=round(phase * length, 6),
            direction='right_passes_left' if b > a else 'left_passes_right',
            separationAtSampleCm=round(abs(a), 4),
            ballHeightRCm=round(height['r'][i], 4),
            ballHeightLCm=round(height['l'][i], 4)))
    crossings.sort(key=lambda c: c['phase'])
    row = dict(asset=clip.get_path_name(), sequenceLengthSec=length, sampleRateHz=rate,
               samples=n, forwardAxis='component +Y',
               foreAftSeparationRangeCm=round(max(delta) - min(delta), 4),
               crossings=crossings, crossingCount=len(crossings))
    if len(crossings) == 2:
        row['crossingSeparationOfCycle'] = round(crossings[1]['phase'] - crossings[0]['phase'], 6)
    row['neutralPhase'] = crossings[0]['phase'] if crossings else None
    return row


def run_measure():
    import unreal as ue
    stamp = stamp_now()
    out = receipt_path('measure', stamp)
    receipt = dict(status='starting', mode='measure', utc=utc(), stamp=stamp,
                   sampleRateHz=SAMPLE_RATE_HZ, confirmRateHz=CONFIRM_RATE_HZ,
                   offlineNeutralPhaseClaim=OFFLINE_NEUTRAL_CLAIM,
                   method=measure_neutral_phase.__doc__, clips={}, errors=[])

    def write():
        out.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    try:
        receipt['editorProcesses'] = _guards(ue)
        before = protected_hashes()
        receipt['protectedBefore'] = before
        write()
        for key, path in sorted(clips_of_interest().items()):
            clip = ue.load_asset(path)
            if clip is None or not isinstance(clip, ue.AnimSequence):
                raise RuntimeError('%s: not an AnimSequence at %s' % (key, path))
            row = dict(path=path)
            row['neutral'] = measure_neutral_phase(ue, clip)
            gait = measure_clip(ue, clip)
            row['gait'] = {k: gait.get(k) for k in
                           ('sequenceLengthSec', 'numFrames', 'numKeys', 'rateScale',
                            'fittedGroundSpeedCmPerSec', 'stepLengthCm', 'maxPlantDriftCm')}
            receipt['clips'][key] = row
            write()
        # Convergence: the same crossing read four times as densely on one clip. If 240 Hz
        # were too coarse to place the crossing this is where it would show.
        confirm = ue.load_asset(clips_of_interest()['new:V3_Pilgrim_Man_Standard'])
        receipt['confirm'] = measure_neutral_phase(ue, confirm, CONFIRM_RATE_HZ)
        coarse = receipt['clips']['new:V3_Pilgrim_Man_Standard']['neutral']['neutralPhase']
        fine = receipt['confirm']['neutralPhase']
        receipt['confirmDelta'] = round(abs(fine - coarse), 6)
        # Every cast variant must agree: they are the same authored motion on nine rigs.
        news = {k: v['neutral']['neutralPhase'] for k, v in receipt['clips'].items()
                if k.startswith('new:')}
        receipt['newClipNeutralPhases'] = news
        spread = max(news.values()) - min(news.values())
        receipt['newClipNeutralPhaseSpread'] = round(spread, 6)
        if spread > 0.01:
            raise RuntimeError('The six cast variants disagree on the neutral phase by %.4f of a '
                               'cycle: %r. They carry the same authored motion; refuse to pick one.'
                               % (spread, news))
        receipt['measuredNeutralPhase'] = round(sum(news.values()) / len(news), 4)
        receipt['measuredV2GroundSpeedCmPerSec'] = round(
            receipt['clips']['v2:PilgrimRigV2']['gait']['fittedGroundSpeedCmPerSec'], 2)
        receipt['measuredV2NeutralPhase'] = round(
            receipt['clips']['v2:PilgrimRigV2']['neutral']['neutralPhase'], 4)
        receipt['measuredNewGroundSpeedCmPerSec'] = round(
            receipt['clips']['new:V3_Pilgrim_Man_Standard']['gait']['fittedGroundSpeedCmPerSec'], 2)
        receipt['measuredOldNeutralPhase'] = round(
            receipt['clips']['old:V3_Pilgrim_Man_Standard']['neutral']['neutralPhase'], 4)
        receipt['offlineClaimAgrees'] = abs(
            receipt['measuredNeutralPhase'] - OFFLINE_NEUTRAL_CLAIM[0]) <= 0.01
        after = protected_hashes()
        receipt['protectedAfter'] = after
        moved = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        receipt['protectedChanged'] = moved
        if moved:
            raise RuntimeError('A protected asset or map changed bytes during a read-only '
                               'measurement: %r' % moved)
        receipt['status'] = 'measured'
        write()
    except Exception:
        receipt['status'] = 'failed'
        receipt['errors'].append(traceback.format_exc())
        write()
        raise
    return receipt


def newest_measure():
    found = sorted(WALK2.glob('walkv2-finish-measure-*.json'))
    for path in reversed(found):
        doc = json.loads(path.read_text(encoding='utf-8-sig'))
        if doc.get('status') == 'measured':
            return path, doc
    raise RuntimeError('No completed -FinishMeasure receipt; run it first')


# ---------------------------------------------------------------------------------------
# Native: apply / revert on one map
# ---------------------------------------------------------------------------------------
def _read_props(ue, actor, fields):
    row = {}
    for field in fields:
        try:
            value = actor.get_editor_property(field)
        except Exception:                                            # noqa: BLE001
            continue
        if hasattr(value, 'get_path_name'):
            row[field] = value.get_path_name()
        elif isinstance(value, bool):
            row[field] = bool(value)
        elif isinstance(value, (int, float)):
            row[field] = float(value)
        elif value is None:
            row[field] = None
        else:
            row[field] = str(value)
    return row


def _write_props(ue, actor, wanted, writable):
    actor.modify(True)
    for field in writable:
        if field not in wanted:
            continue
        value = wanted[field]
        if field in ('walk_animation', 'idle_animation', 'configured_mesh', 'resident_mesh'):
            asset = ue.load_asset(value) if value else None
            if value and asset is None:
                raise RuntimeError('Could not load %s for %s' % (value, field))
            actor.set_editor_property(field, asset)
        else:
            actor.set_editor_property(field, value)


def _same(a, b, tol=1e-3):
    """Structural equality that tolerates float32 storage.

    `AMikdashServiceActor::WalkSpeedCmPerSec` is a float, not a double: writing 119.95 and
    reading it back returns 119.94999694824219. Comparing that exactly would refuse a write
    that in fact worked -- and silently comparing everything loosely would let a real miss
    through -- so numbers compare within `tol` and everything else compares exactly. The
    receipt always records the raw readback, never the rounded plan.
    """
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= tol
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same(a[k], b[k], tol) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y, tol) for x, y in zip(a, b))
    return a == b


def _find(actors, label, expect=1):
    found = [a for a in actors.get_all_level_actors() if a.get_actor_label() == label]
    if len(found) != expect:
        raise RuntimeError('Expected exactly %d actor(s) labelled %s, found %d'
                           % (expect, label, len(found)))
    return found[0]


def _snapshot_actors(ue, actors, target_key):
    """The three actors this run may touch, read exactly the way they will be read back."""
    kohen = _find(actors, KOHEN_LABEL[target_key])
    if kohen.get_class().get_path_name() != SERVICE_CLASS:
        raise RuntimeError('%s is not a MikdashServiceActor (%s)'
                           % (KOHEN_LABEL[target_key], kohen.get_class().get_path_name()))
    people = _find(actors, V3_POPULATION_LABEL)
    pilot = _find(actors, PILOT_LABEL)
    for actor, label in ((people, V3_POPULATION_LABEL), (pilot, PILOT_LABEL)):
        if not isinstance(actor, ue.MikdashResidentPopulation):
            raise RuntimeError('%s is not a MikdashResidentPopulation' % label)
    return kohen, people, pilot, dict(
        kohen=_read_props(ue, kohen, KOHEN_FIELDS),
        peopleV3=dict(_read_props(ue, people, POP_FIELDS),
                      body_variants=_read_variants(ue, people)),
        pilot=dict(_read_props(ue, pilot, POP_FIELDS),
                   body_variants=_read_variants(ue, pilot),
                   bodies=[a.get_actor_label() if a else None
                           for a in pilot.get_editor_property('bodies')]))


def _plan_wanted(ue, target_key, before, measured):
    """What the three actors should hold, and why, decided from the MEASURED numbers."""
    notes = {}
    marker = imported_marker()

    # --- 1. the Kohen Gadol ------------------------------------------------------------
    kohen_before = before['kohen']
    if kohen_before.get('authored_body'):
        # With AuthoredBody set the actor uses a body already placed and dressed in the map,
        # bBodyWasSpawned stays false and UpdateBodyAnimation returns before it ever looks at
        # WalkAnimation. Writing the clip would be a no-op that reads like a fix.
        raise RuntimeError('The kohen has AuthoredBody set (%r); UpdateBodyAnimation never runs '
                           'on an authored body, so setting WalkAnimation would change nothing. '
                           'Refusing rather than writing a cosmetic value.'
                           % kohen_before['authored_body'])
    configured = kohen_before.get('configured_mesh')
    mesh_path = configured or _object_path(KOHEN_FALLBACK_MESH)
    mesh = ue.load_asset(mesh_path)
    if mesh is None:
        raise RuntimeError('Kohen body mesh not loadable at %s' % mesh_path)
    skeleton = mesh.get_editor_property('skeleton')
    if skeleton is None:
        raise RuntimeError('Kohen body mesh %s has no skeleton' % mesh_path)
    matches = [vid for vid in sorted(marker)
               if _object_path(marker[vid]['skeleton']) == skeleton.get_path_name()]
    if len(matches) != 1:
        raise RuntimeError('The kohen body skeleton %s matches %r imported variants; refuse to guess'
                           % (skeleton.get_path_name(), matches))
    variant = matches[0]
    target_clip = _object_path(marker[variant]['newWalk'])
    clip = ue.load_asset(target_clip)
    if clip is None or clip.get_editor_property('skeleton').get_path_name() != skeleton.get_path_name():
        raise RuntimeError('%s is not on the kohen body skeleton' % target_clip)
    old = _object_path(marker[variant]['oldWalk'])
    current = _object_path(kohen_before.get('walk_animation'))
    if current not in (None, old, target_clip):
        raise RuntimeError('The kohen walk clip %r is neither null, the shipped clip nor the new '
                           'one; refusing to guess' % current)
    speed = measured['measuredNewGroundSpeedCmPerSec']
    notes['kohen'] = dict(
        bodyMeshResolvedFrom='configured_mesh' if configured else 'C++ MeshFallbacks[0] '
                             '(PilgrimRigV3); WalkAnimation null would make SpawnBody load the '
                             'hardcoded old V3_Pilgrim_Man_Standard walk clip by literal path',
        bodyMesh=mesh_path, bodySkeleton=skeleton.get_path_name(), matchedVariant=variant,
        walkAnimationBefore=current, walkAnimationAfter=target_clip,
        walkSpeedBefore=kohen_before.get('walk_speed_cm_per_sec'),
        walkSpeedAfter=speed,
        whyThisSpeed='AMikdashServiceActor never sets a play rate: UpdateBodyAnimation calls '
                     'SetAnimation + Play(true) and the clip runs at 1.0. Its stride therefore '
                     'matches its translation only when WalkSpeedCmPerSec equals the speed the '
                     'clip carries, which is the in-engine fitted %.2f cm/s.' % speed)
    kohen_wanted = dict(kohen_before)
    kohen_wanted['walk_animation'] = target_clip
    kohen_wanted['walk_speed_cm_per_sec'] = speed

    # --- 2. the stale neutral phase ----------------------------------------------------
    neutral = measured['measuredNeutralPhase']
    people_wanted = dict(before['peopleV3'])
    rows, repointed = [], []
    for row in before['peopleV3']['body_variants']:
        new = dict(row)
        entry = marker.get(row['id'])
        if entry and _object_path(row.get('walk_animation')) == _object_path(entry['newWalk']):
            if 'walk_clip_neutral_phase' in new and new['walk_clip_neutral_phase'] != neutral:
                repointed.append(dict(id=row['id'], before=new['walk_clip_neutral_phase'],
                                      after=neutral))
                new['walk_clip_neutral_phase'] = neutral
        else:
            raise RuntimeError('%s is not on its WalkV2 clip (%r); run release_walk_v2.py '
                               '-WalkV2Apply first' % (row['id'], row.get('walk_animation')))
        rows.append(new)
    people_wanted['body_variants'] = rows
    notes['neutralPhase'] = dict(measuredInEngine=neutral,
                                 offlineClaim=OFFLINE_NEUTRAL_CLAIM,
                                 measuredOldClip=measured['measuredOldNeutralPhase'],
                                 perVariant=repointed, variantsChanged=len(repointed))

    # --- 3. the pilot population and the default-body landmine -------------------------
    v2_speed = measured['measuredV2GroundSpeedCmPerSec']
    v2_neutral = measured['measuredV2NeutralPhase']
    pilot_wanted = dict(before['pilot'])
    default_notes = {}
    for key, wanted_row, source in (('peopleV3', people_wanted, before['peopleV3']),
                                    ('pilot', pilot_wanted, before['pilot'])):
        clip_path = _object_path(source.get('walk_animation'))
        if clip_path != _object_path(V2_WALK):
            raise RuntimeError('%s: population-level walk_animation is %r, not the V2 clip; the '
                               'default speed below was measured off the V2 clip. Refuse.'
                               % (key, clip_path))
        wanted_row['default_walk_clip_ground_speed_cm_per_sec'] = v2_speed
        wanted_row['default_walk_clip_neutral_phase'] = v2_neutral
        default_notes[key] = dict(
            populationWalkAnimation=clip_path,
            groundSpeedBefore=source.get('default_walk_clip_ground_speed_cm_per_sec'),
            groundSpeedAfter=v2_speed,
            neutralPhaseBefore=source.get('default_walk_clip_neutral_phase'),
            neutralPhaseAfter=v2_neutral)
    notes['defaultBody'] = default_notes

    # Who can actually reach the default body? ResolveBody takes it when a person's variant is
    # empty, unregistered, or registered but unusable. The first two are decided off the
    # directory; the third is decided here, against the reopened actor's own assets, by
    # replaying ResolveBody's refusal conditions one for one.
    census = directory_census(_targets()[target_key]['relativeToContent'])
    usable, unusable = {}, {}
    for row in before['peopleV3']['body_variants']:
        reasons = []
        mesh_asset = ue.load_asset(row['skeletal_mesh']) if row.get('skeletal_mesh') else None
        idle_asset = ue.load_asset(row['idle_animation']) if row.get('idle_animation') else None
        walk_asset = ue.load_asset(row['walk_animation']) if row.get('walk_animation') else None
        if not (mesh_asset and idle_asset and walk_asset):
            reasons.append('missing skeletal mesh or clip asset')
        else:
            skel = mesh_asset.get_editor_property('skeleton')
            if skel is None or idle_asset.get_editor_property('skeleton') != skel \
                    or walk_asset.get_editor_property('skeleton') != skel:
                reasons.append('clips do not belong to its own skeleton')
        if not row.get('garment_material_slots'):
            reasons.append('names no garment slot')
        yaw = row.get('mesh_relative_yaw')
        if yaw is None or yaw != yaw or abs(yaw) == float('inf'):
            reasons.append('non-finite mesh yaw')
        (unusable if reasons else usable)[row['id']] = reasons or 'usable'
    reaching_default = sorted(set(census['variantCounts']) - set(usable))
    fallback_people = census['peopleWithNoVariantCount'] + sum(
        census['variantCounts'].get(v, 0) for v in reaching_default)
    notes['defaultBodyEvidence'] = dict(
        directory=census,
        registeredVariantIds=[r['id'] for r in before['peopleV3']['body_variants']],
        variantsUsableByResolveBody=sorted(usable),
        variantsRefusedByResolveBody=unusable,
        directoryVariantsWithNoUsableRegistration=reaching_default,
        peopleThatWouldTakeTheDefaultBody=fallback_people,
        peopleThatWouldTakeAVariantBody=census['people'] - fallback_people,
        pilotStartupEnabled=before['pilot'].get('activate_reviewed_pilot_on_begin_play'),
        pilotPlacedBodies=before['pilot'].get('bodies'),
        pilotPlacedBodyCount=len(before['pilot'].get('bodies') or []),
        peopleV3StartupEnabled=before['peopleV3'].get('spawn_authored_people_on_begin_play'),
        note='The pilot drives its five PLACED bodies through BindConfiguredBodies, which '
             'always uses the population-level WalkAnimation and DefaultWalkClipGroundSpeed'
             'CmPerSec -- it never consults BodyVariants. Those five are the only bodies in '
             'either map that read the default gait numbers, and only if pilot startup is on.')
    return dict(kohen=kohen_wanted, peopleV3=people_wanted, pilot=pilot_wanted), notes


def _apply(target_key, stamp, wanted_fn, kind):
    """Checkpoint -> load -> snapshot -> set -> save -> REOPEN -> read back. Nothing trusted."""
    targets = _targets()
    target = targets[target_key]
    MAP = target['map']
    map_file = disk_umap(MAP)
    others = {k: disk_umap(t['map']) for k, t in targets.items() if k != target_key}
    out = receipt_path(kind + '-' + target_key, stamp)
    receipt = dict(status='starting', mode=kind, target=target_key, map=MAP, utc=utc(), stamp=stamp,
                   mapBeforeSha256=sha(map_file),
                   otherMapsBefore={k: sha(v) for k, v in others.items()}, errors=[])

    def write():
        out.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    import unreal as ue
    receipt['editorProcesses'] = _guards(ue)
    if not hasattr(ue, 'MikdashResidentBodyVariant'):
        raise RuntimeError('Compiled plugin does not expose MikdashResidentBodyVariant')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    try:
        protected_before = protected_hashes()
        receipt['protectedBefore'] = protected_before
        checkpoint = CHECKPOINT_ROOT / ('WalkV2Finish-' + target_key + '-' + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'BeforeWalkV2Finish.umap')
        if sha(checkpoint / 'BeforeWalkV2Finish.umap') != receipt['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy mismatch')
        receipt['checkpoint'] = str(checkpoint)
        write()
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            if not levels.load_level(MAP):
                raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Unexpected editor world')
        crowd = _load('walkv2_finish_snapshot', 'Scripts/release_resident_crowd.py')
        baseline = crowd._scene_snapshot(ue, actors)
        kohen, people, pilot, before = _snapshot_actors(ue, actors, target_key)
        receipt['before'] = before
        write()
        wanted, notes = wanted_fn(ue, target_key, before)
        receipt['notes'] = notes
        receipt['wanted'] = wanted
        write()
        changed = not _same(wanted, before)
        owners = {'kohen': kohen, 'peopleV3': people, 'pilot': pilot}
        if changed:
            for key, actor in owners.items():
                if _same(wanted[key], before[key]):
                    continue
                writable = KOHEN_WRITE if key == 'kohen' else POP_WRITE
                _write_props(ue, actor, wanted[key], writable)
                if key != 'kohen' and not _same(wanted[key]['body_variants'], before[key]['body_variants']):
                    actor.set_editor_property('body_variants',
                                              _build_variants(ue, wanted[key]['body_variants']))
        _, _, _, after_set = _snapshot_actors(ue, actors, target_key)
        if not _same(after_set, wanted):
            raise RuntimeError('Properties did not read back as planned before the save: %r'
                               % after_set)
        after_scene = crowd._scene_snapshot(ue, actors)
        moved = {k for k in set(baseline) | set(after_scene) if baseline.get(k) != after_scene.get(k)}
        allowed = {a.get_name() for a in owners.values()} if changed else set()
        if moved - allowed:
            raise RuntimeError('Unexpected scene changes: %r' % sorted(moved - allowed)[:20])
        receipt['sceneChanges'] = sorted(moved)
        if changed:
            if not levels.save_current_level():
                raise RuntimeError('Level save failed')
            receipt.update(mapSaved=True, mapAfterSha256=sha(map_file),
                           status='saved_reopen_pending')
            write()
            if not levels.load_level(MAP) or editor.get_editor_world().get_outermost().get_name() != MAP:
                raise RuntimeError('Reopen failed')
        else:
            receipt.update(mapSaved=False, mapAfterSha256=sha(map_file),
                           status='no_change_needed')
            write()
        kohen, people, pilot, readback = _snapshot_actors(ue, actors, target_key)
        receipt['readbackAfterReopen'] = readback
        if not _same(readback, wanted):
            raise RuntimeError('Readback after reopen differs from the plan: %r' % readback)
        # The kohen's clip must sit on the skeleton of the body he will actually wear, or
        # UpdateBodyAnimation silently refuses it and he plays the idle while translating.
        mesh_path = readback['kohen'].get('configured_mesh') or _object_path(KOHEN_FALLBACK_MESH)
        mesh = ue.load_asset(mesh_path)
        clip = ue.load_asset(readback['kohen']['walk_animation'])
        idle = ue.load_asset(readback['kohen']['idle_animation']) if readback['kohen'].get('idle_animation') else None
        receipt['kohenClipCheck'] = dict(
            bodyMesh=mesh_path,
            bodySkeleton=mesh.get_editor_property('skeleton').get_path_name(),
            walkClipSkeleton=clip.get_editor_property('skeleton').get_path_name(),
            walkOnBodySkeleton=clip.get_editor_property('skeleton') == mesh.get_editor_property('skeleton'),
            idleClipSkeleton=idle.get_editor_property('skeleton').get_path_name() if idle else None,
            idleOnBodySkeleton=bool(idle) and idle.get_editor_property('skeleton') == mesh.get_editor_property('skeleton'),
            walkLengthSec=round(float(ue.AnimationLibrary.get_sequence_length(clip)), 6),
            walkNumKeys=int(ue.AnimationLibrary.get_num_keys(clip)),
            walkSpeedCmPerSec=readback['kohen']['walk_speed_cm_per_sec'])
        if not receipt['kohenClipCheck']['walkOnBodySkeleton']:
            raise RuntimeError('The kohen walk clip is not on his body skeleton')
        receipt['otherMapsAfter'] = {k: sha(v) for k, v in others.items()}
        receipt['otherMapsUnchanged'] = receipt['otherMapsAfter'] == receipt['otherMapsBefore']
        if not receipt['otherMapsUnchanged']:
            raise RuntimeError('Another map changed bytes during the run')
        protected_after = protected_hashes()
        this_map = str(map_file.relative_to(ROOT)).replace('\\', '/')
        receipt['protectedAfter'] = protected_after
        moved_assets = sorted(k for k in set(protected_before) | set(protected_after)
                              if protected_before.get(k) != protected_after.get(k)
                              and k != this_map)
        receipt['protectedChangedExcludingThisMap'] = moved_assets
        if moved_assets:
            raise RuntimeError('Assets outside this map changed bytes: %r' % moved_assets)
        receipt['status'] = ('%s_saved_reopened_readback_pie_review_pending' % kind) if changed \
            else ('%s_no_change_needed' % kind)
        write()
    except Exception:
        receipt['status'] = 'failed'
        receipt['errors'].append(traceback.format_exc())
        try:
            receipt['mapAfterSha256'] = sha(map_file)
        except Exception:                                            # noqa: BLE001
            pass
        write()
        raise
    return receipt


def run_apply(target_key):
    measure_file, measured = newest_measure()

    def wanted_fn(ue, key, before):
        plan, notes = _plan_wanted(ue, key, before, measured)
        notes['measureReceipt'] = dict(file=measure_file.name, sha256=sha(measure_file),
                                       stamp=measured['stamp'])
        return plan, notes
    return _apply(target_key, stamp_now(), wanted_fn, 'apply')


def run_revert(target_key):
    previous = sorted(WALK2.glob('walkv2-finish-apply-%s-*.json' % target_key))
    if not previous:
        raise RuntimeError('No finish-apply receipt for %s to revert to' % target_key)
    source = json.loads(previous[-1].read_text(encoding='utf-8-sig'))
    if 'before' not in source:
        raise RuntimeError('%s carries no before block' % previous[-1].name)

    def wanted_fn(ue, key, before):
        rows = source['before']
        if [r['id'] for r in rows['peopleV3']['body_variants']] != \
                [r['id'] for r in before['peopleV3']['body_variants']]:
            raise RuntimeError('Variant ids differ from the apply receipt; refuse')
        if rows['kohen'].get('configured_mesh') != before['kohen'].get('configured_mesh'):
            raise RuntimeError('The kohen body mesh differs from the apply receipt; refuse')
        return rows, dict(revertSource=previous[-1].name,
                          revertSourceSha256=sha(previous[-1]))
    return _apply(target_key, stamp_now(), wanted_fn, 'revert')


# ---------------------------------------------------------------------------------------
def _target(command_line):
    m = re.search(r'-FinishTarget=(Main50|Candidate48)', command_line)
    if not m:
        raise RuntimeError('Pass -FinishTarget=Main50 or -FinishTarget=Candidate48')
    return m.group(1)


def _main():
    try:
        import unreal                                                # noqa: F401
    except ImportError:
        print(json.dumps(dict(clips=clips_of_interest(), castVariants=cast_variants(),
                              kohenLabels=KOHEN_LABEL,
                              directories={k: directory_census(t['relativeToContent'])
                                           for k, t in _targets().items()}),
                         indent=2, default=str))
        return
    import unreal
    command_line = unreal.SystemLibrary.get_command_line()
    try:
        if '-FinishMeasure' in command_line:
            run_measure()
        elif '-FinishApplyAll' in command_line:
            # Candidate first, then Main50, in one process: this box runs ONE engine and two
            # other agents plus a cook are queueing behind it. Each target still checkpoints,
            # saves, reopens and reads back on its own, and the second refuses if the first
            # left anything dirty.
            for key in ('Candidate48', 'Main50'):
                run_apply(key)
        elif '-FinishRevertAndReapply' in command_line:
            # The revert is RUN, not asserted, and the target is then put back in the intended
            # state. Both halves are full guarded save/reopen/readback passes.
            key = _target(command_line)
            run_revert(key)
            run_apply(key)
        elif '-FinishApply' in command_line:
            run_apply(_target(command_line))
        elif '-FinishRevert' in command_line:
            run_revert(_target(command_line))
        else:
            raise RuntimeError('release_walk_v2_finish: nothing done. Pass -FinishMeasure, or '
                               '-FinishApply / -FinishRevert with -FinishTarget=Main50|Candidate48')
    except Exception:
        failure = receipt_path('failure', stamp_now())
        failure.write_text(json.dumps(dict(status='failed_before_or_during_run',
                                           commandLine=command_line,
                                           error=traceback.format_exc()), indent=2),
                           encoding='utf-8')
        raise


if __name__ == '__main__':
    _main()

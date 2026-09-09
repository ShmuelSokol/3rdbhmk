"""Import the re-authored PilgrimRigV3 walk (walk-v2) and repoint the residents at it.

WHAT THIS IS. `Scripts/rewalk_pilgrim_v3.py` re-authored `A_Pilgrim_Original_Walk`
offline and re-exported nine GLBs to SourceAssets/characters-review/PilgrimRigV3/walk-v2/meshes/.
Their geometry, rest pose, joint names, weights and inverse-bind matrices are asserted
byte-identical to the shipped bodies; only the walk animation differs. The C++ already
carries 120.0 cm/s as the clip's ground speed, so until this import lands the code and the
shipped clip disagree and the residents are driven at 120 on a clip that carries 53.33.

WHAT IT DOES NOT DO. It never re-imports geometry, never creates a Skeleton, never touches
the nine shipped GLBs or the nine imported SkeletalMeshes/Skeletons, and never deletes the
old clips. The new clips land in a fresh `WalkV2/` folder beside the originals and the
population's variant array is repointed. `-Revert` points it back.

THREE NATIVE MODES, each guarded, each with a receipt.

  -WalkV2Import   Animation-only Interchange import of the nine walk-v2 GLBs onto each
                  variant's EXISTING Skeleton (InterchangeGenericAssetsPipeline with
                  common.skeleton = the existing asset and import_only_animations = True).
                  Refuses if the importer creates a Skeleton or a SkeletalMesh, if a clip
                  binds to any other skeleton, or if a pre-existing .uasset changes bytes.
                  Saves only the new assets, reloads them from disk, then MEASURES them:
                  duration, key count, frame rate, and a plant-fitted ground speed and step
                  length computed by sampling the imported clip through AnimPose in
                  component space. The same measurement is run on the OLD imported clip in
                  the same session, so the before/after pair is one method, in engine.

  -WalkV2Apply -WalkV2Target=Main50|Candidate48
                  Checkpoints the .umap, loads it, snapshots the scene, replaces
                  WalkAnimation on every FMikdashResidentBodyVariant with that variant's
                  new clip (and pins WalkClipGroundSpeedCmPerSec to the measured 120.0),
                  saves, reopens the map, reads the array back off the reopened actor.
                  Refuses if any other actor changed or the other map's bytes moved.

  -WalkV2Revert -WalkV2Target=...
                  Restores the exact array recorded in that target's newest apply receipt.

Traps already paid for on this project and honoured here:
  * Interchange maps glTF (X, Y, Z) to UE (X, Z, Y); the rig's toes therefore sit at
    component +Y (ball_r y = +11.5) and the population uses MeshRelativeYaw = -90. The
    in-engine gait measurement reads forward along component +Y for that reason.
  * UE stores the reference skeleton depth-first, so bone identity is compared as a SET,
    never by authored order.
  * Import markers store PACKAGE paths and native readback returns OBJECT paths; every
    comparison here normalises with _object_path first (this is the exact compare that
    refused the bodies apply on 2026-09-08).
  * 5.8 setters return False even when they worked: nothing is trusted until it is read
    back off the reloaded asset.
  * A zombie UnrealEditor makes save_loaded_asset return False with no other symptom, so
    more than one live editor is refused up front.

Nothing here is a visual, PIE, cook or performance acceptance. Nobody has looked at the new
walk in a frame.

Proven launch (one at a time; this box runs one engine):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough
      -ExecutePythonScript="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_walk_v2.py"
      -WalkV2Import -unattended -nullrhi -NoSplash -abslog=<unique>
"""
import hashlib, importlib.util, json, re, shutil, subprocess, sys, traceback
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/characters-review/PilgrimRigV3'
WALK2 = OUT / 'walk-v2'
MESHES = WALK2 / 'meshes'
MEASURE = WALK2 / 'walk-measurements.json'
MARKER = OUT / 'review-native-progress.json'
IMPORT_MARKER = WALK2 / 'walkv2-import-progress.json'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
NAMESPACE = '/Game/MikdashV3/Characters/PilgrimRigV3'
SUBFOLDER = 'WalkV2'
WALK_SUFFIX = 'A_Pilgrim_Original_Walk'
IDLE_SUFFIX = 'A_Pilgrim_Original_Idle'
AUTHORED_GROUND_SPEED = 120.0
CYCLE_SECONDS = 1.2
SOURCE_KEYS = 73
SOURCE_FPS = 60
SOURCE_FRAMES = SOURCE_KEYS - 1
FORWARD_AXIS = 1          # component +Y: ball_r sits at y = +11.5 in the reference pose
CONTACT_THRESHOLDS_CM = (0.20, 0.50)
SAMPLE_RATE_HZ = 240.0

BODIES_SPEC = json.loads((ROOT / 'Scripts/release_resident_bodies_v3.spec.json').read_text(encoding='utf-8-sig'))


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


def _object_path(path):
    """Import markers store package paths; native readback returns object paths."""
    if path is None or '.' in path.rsplit('/', 1)[-1]:
        return path
    return path + '.' + path.rsplit('/', 1)[-1]


def disk_umap(package):
    return ROOT / 'Content' / (package[6:] + '.umap')


def disk_uasset(path):
    return ROOT / 'Content' / (path.split('.')[0][6:] + '.uasset')


def marker():
    m = json.loads(MARKER.read_text(encoding='utf-8-sig'))
    if m.get('namespace') != NAMESPACE:
        raise RuntimeError('Import marker namespace differs from the expected namespace')
    return m['completed']


def receipt_path(kind, stamp):
    WALK2.mkdir(parents=True, exist_ok=True)
    return WALK2 / ('walkv2-' + kind + '-' + stamp + '.json')


# ---------------------------------------------------------------------------------------
# Offline plan
# ---------------------------------------------------------------------------------------
def plan():
    """Pure Python. Re-hashes the nine walk-v2 GLBs and resolves every asset path."""
    failures = []
    measured = json.loads(MEASURE.read_text(encoding='utf-8-sig'))
    completed = marker()
    variants = {}
    for entry in measured['variants']:
        vid = entry['id']
        src = MESHES / (vid + '.glb')
        if not src.is_file():
            failures.append('%s: walk-v2 GLB missing at %s' % (vid, src))
            continue
        got = sha(src)
        if got != entry['sha256']:
            failures.append('%s: walk-v2 GLB sha256 %s does not match walk-measurements.json %s'
                            % (vid, got[:16], entry['sha256'][:16]))
        if not entry.get('geometryIdenticalToShipped'):
            failures.append('%s: walk-measurements.json does not assert identical geometry' % vid)
        shipped = OUT / 'meshes' / (vid + '.glb')
        if shipped.is_file() and sha(shipped) != entry['previousSha256']:
            failures.append('%s: the SHIPPED GLB has changed since the re-author run' % vid)
        done = completed.get(vid)
        if not done:
            failures.append('%s: not listed as natively imported in review-native-progress.json' % vid)
            continue
        walks = [a for a in done['animations'] if a.endswith(WALK_SUFFIX)]
        if len(walks) != 1:
            failures.append('%s: expected one existing walk clip, found %r' % (vid, walks))
            continue
        folder = NAMESPACE + '/' + vid + '/' + SUBFOLDER
        variants[vid] = dict(
            id=vid, source=str(src), sourceSha256=got,
            skeletalMesh=_object_path(done['skeletalMesh']),
            skeleton=_object_path(done['skeleton']),
            oldWalk=_object_path(walks[0]),
            oldIdle=_object_path([a for a in done['animations'] if a.endswith(IDLE_SUFFIX)][0]),
            destinationFolder=folder,
            existingAssets=sorted(_object_path(a) for a in
                                  [done['skeletalMesh'], done['skeleton']] + list(done['animations'])))
    return dict(utc=utc(), offlineOk=not failures, failures=failures,
                namespace=NAMESPACE, subfolder=SUBFOLDER, variants=variants,
                authoredGroundSpeedCmPerSec=AUTHORED_GROUND_SPEED,
                sourceKeys=SOURCE_KEYS, sourceFps=SOURCE_FPS, cycleSeconds=CYCLE_SECONDS,
                offlineBeforeStepLengthCm=measured['before'][0]['stepLengthCmFromSpeed'],
                offlineAfterStepLengthCm=measured['after'][0]['stepLengthCmFromSpeed'],
                castVariants=sorted({r['variant'] for r in json.loads(
                    (OUT / 'resident-swap-plan.json').read_text(encoding='utf-8-sig'))['residents']}))


def protected_hashes(plan_doc):
    """Every pre-existing asset this run must not change, plus both target maps."""
    out = {}
    for vid, v in plan_doc['variants'].items():
        for path in v['existingAssets']:
            f = disk_uasset(path)
            if f.is_file():
                out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    for key, target in _targets().items():
        f = disk_umap(target['map'])
        out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    return out


def _targets():
    routes = _load('release_resident_routes_v2', 'Scripts/release_resident_routes_v2.py')
    return routes.SPEC['targets']


# ---------------------------------------------------------------------------------------
# In-engine measurement: everything below reads the IMPORTED asset, never the GLB.
# ---------------------------------------------------------------------------------------
def _pose_at(ue, clip, time, options):
    fn = ue.AnimPoseExtensions.get_anim_pose_at_time
    try:
        return fn(clip, time, options, ue.AnimPose())
    except Exception:                                                # noqa: BLE001
        return fn(clip, time, options)


def _fit(times, values):
    """Least-squares slope/intercept and the worst residual, in the units given."""
    n = len(times)
    mt = sum(times) / n
    mv = sum(values) / n
    den = sum((t - mt) ** 2 for t in times)
    if den <= 0:
        return 0.0, mv, 0.0
    slope = sum((t - mt) * (v - mv) for t, v in zip(times, values)) / den
    intercept = mv - slope * mt
    worst = max(abs(v - (slope * t + intercept)) for t, v in zip(times, values))
    return slope, intercept, worst


def _longest_run(flags):
    """Longest cyclic run of True; returns the list of indices in order."""
    n = len(flags)
    if not any(flags):
        return []
    best, run = [], []
    for i in range(2 * n):
        if flags[i % n]:
            run.append(i % n)
            if len(run) > len(best):
                best = list(run)
        else:
            run = []
        if len(best) >= n:
            break
    return best[:n]


def measure_clip(ue, clip, rate=SAMPLE_RATE_HZ):
    """Sample the imported AnimSequence in component space and fit the stance plant.

    Method, stated so it can be argued with: the clip is authored in place, so during
    stance the planted foot travels BACKWARD through component space at exactly the
    ground speed the clip implies. Sample ball_r, take the longest cyclic run of samples
    whose height is within `threshold` of that foot's lowest point, least-squares fit its
    forward (component +Y) position against time over that run: |slope| is the ground
    speed and the worst residual is how far the planted foot slides against its own best
    straight line. Step length is speed x cycle / 2.
    """
    row = {'asset': clip.get_path_name()}
    for key, fn in (('sequenceLengthSec', lambda: float(ue.AnimationLibrary.get_sequence_length(clip))),
                    ('numFrames', lambda: int(ue.AnimationLibrary.get_num_frames(clip))),
                    ('numKeys', lambda: int(ue.AnimationLibrary.get_num_keys(clip))),
                    ('playLength', lambda: float(clip.get_play_length())),
                    ('rateScale', lambda: float(clip.get_editor_property('rate_scale')))):
        try:
            row[key] = fn()
        except Exception as error:                                   # noqa: BLE001
            row[key] = 'unavailable: ' + str(error)[:100]
    for prop in ('target_frame_rate', 'platform_target_frame_rate', 'import_file_framerate',
                 'import_resample_framerate', 'number_of_sampled_keys', 'number_of_frames'):
        try:
            value = clip.get_editor_property(prop)
            try:
                row[prop] = {'numerator': int(value.numerator), 'denominator': int(value.denominator),
                             'fps': float(value.numerator) / float(value.denominator)}
            except Exception:                                        # noqa: BLE001
                row[prop] = float(value) if isinstance(value, (int, float)) else str(value)
        except Exception:                                            # noqa: BLE001
            pass
    length = row['sequenceLengthSec'] if isinstance(row['sequenceLengthSec'], float) else CYCLE_SECONDS
    options = ue.AnimPoseEvaluationOptions()
    n = max(8, int(round(length * rate)))
    bones = ['pelvis', 'ball_r', 'ball_l', 'foot_r', 'foot_l', 'hand_r', 'head']
    times, track = [], {b: [] for b in bones}
    pose_bone_names = None
    for i in range(n):
        t = length * i / n
        pose = _pose_at(ue, clip, t, options)
        if pose_bone_names is None:
            pose_bone_names = sorted(str(x) for x in ue.AnimPoseExtensions.get_bone_names(pose))
        times.append(t)
        for b in bones:
            v = ue.AnimPoseExtensions.get_bone_pose(pose, b, ue.AnimPoseSpaces.WORLD).translation
            track[b].append((float(v.x), float(v.y), float(v.z)))
    row['sampleRateHz'] = rate
    row['samples'] = n
    row['poseBoneNames'] = pose_bone_names
    row['poseBoneCount'] = len(pose_bone_names or [])
    row['forwardAxis'] = 'component +Y'

    def span(name, axis):
        vals = [p[axis] for p in track[name]]
        return round(max(vals) - min(vals), 3)
    row['pelvisBobCm'] = span('pelvis', 2)
    row['pelvisLateralSwayCm'] = span('pelvis', 0)
    row['footLiftCm'] = {'r': span('ball_r', 2), 'l': span('ball_l', 2)}
    row['armSwingCm'] = span('hand_r', FORWARD_AXIS)
    row['ankleExcursionCm'] = span('foot_r', FORWARD_AXIS)
    row['pelvisMeanHeightCm'] = round(sum(p[2] for p in track['pelvis']) / n, 3)
    row['lowestBallZCm'] = round(min(min(p[2] for p in track['ball_r']),
                                     min(p[2] for p in track['ball_l'])), 4)

    row['plant'] = {}
    for threshold in CONTACT_THRESHOLDS_CM:
        speeds, drifts, duties = [], [], []
        for foot in ('ball_r', 'ball_l'):
            zs = [p[2] for p in track[foot]]
            floor = min(zs)
            flags = [z <= floor + threshold for z in zs]
            run = _longest_run(flags)
            if len(run) < 4:
                continue
            # The run is consecutive by construction (it may wrap past the loop point),
            # so its own time line is k * dt regardless of where in the cycle it starts.
            dt = length / n
            rt = [k * dt for k in range(len(run))]
            rv = [track[foot][idx][FORWARD_AXIS] for idx in run]
            slope, _, worst = _fit(rt, rv)
            speeds.append(abs(slope))
            drifts.append(worst)
            duties.append(len(run) / float(n))
        if speeds:
            speed = sum(speeds) / len(speeds)
            row['plant']['%.2f' % threshold] = {
                'fittedGroundSpeedCmPerSec': round(speed, 3),
                'stepLengthCm': round(speed * length / 2.0, 3),
                'strideLengthCm': round(speed * length, 3),
                'maxPlantDriftCm': round(max(drifts), 4),
                'stanceDutyFactor': round(sum(duties) / len(duties), 4),
                'feetFitted': len(speeds)}
    key = '%.2f' % CONTACT_THRESHOLDS_CM[0]
    if key in row['plant']:
        row['fittedGroundSpeedCmPerSec'] = row['plant'][key]['fittedGroundSpeedCmPerSec']
        row['stepLengthCm'] = row['plant'][key]['stepLengthCm']
        row['maxPlantDriftCm'] = row['plant'][key]['maxPlantDriftCm']
    else:
        row['fittedGroundSpeedCmPerSec'] = None
        row['stepLengthCm'] = None
        row['measurementNote'] = 'No contact window of four or more samples was found at any threshold.'
    return row


# ---------------------------------------------------------------------------------------
# Native: import
# ---------------------------------------------------------------------------------------
def _editor_pids():
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UnrealEditor*.exe', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True, timeout=30).stdout
        return {'available': True, 'pids': re.findall(r'","(\d+)","', out)}
    except Exception as error:                                       # noqa: BLE001
        return {'available': False, 'reason': str(error)[:120]}


def _guards(ue, allow_dirty_map=False):
    if Path(ue.Paths.project_dir()).resolve() != ROOT.resolve():
        raise RuntimeError('Wrong project directory: refuse native mutation')
    if ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Live PIE world; refuse')
    dirty = list(ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + \
        list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty and not allow_dirty_map:
        raise RuntimeError('Dirty packages present: %r' % [p.get_name() for p in dirty][:10])
    pids = _editor_pids()
    if pids.get('available') and len(pids['pids']) > 1:
        raise RuntimeError('More than one UnrealEditor process alive (%s): a zombie makes '
                           'save_loaded_asset return False with no other symptom.' % pids['pids'])
    return pids


def _anim_only_pipeline(ue, skeleton):
    """Interchange stack override: animations only, bound to an EXISTING Skeleton.

    Every value is read back, because 5.8 setters return False even when they worked. A
    property that will not take the value is a refusal, not a warning: importing without
    `skeleton` set would create a tenth Skeleton and silently orphan the clip.
    """
    pipeline = ue.InterchangeGenericAssetsPipeline()
    readback, missing = {}, []

    def apply(owner, key, value, required):
        try:
            owner.set_editor_property(key, value)
            got = owner.get_editor_property(key)
            readback[key] = got.get_path_name() if hasattr(got, 'get_path_name') else str(got)
        except Exception as error:                                   # noqa: BLE001
            readback[key] = 'unavailable: ' + str(error)[:120]
            if required:
                missing.append(key)

    common = pipeline.get_editor_property('common_skeletal_meshes_and_animations_properties')
    apply(common, 'skeleton', skeleton, True)
    apply(common, 'import_only_animations', True, True)
    apply(common, 'add_curve_metadata_to_skeleton', False, False)
    apply(common, 'use_t0_as_ref_pose', False, False)
    mesh = pipeline.get_editor_property('mesh_pipeline')
    apply(mesh, 'import_static_meshes', False, True)
    apply(mesh, 'import_skeletal_meshes', False, True)
    animation = pipeline.get_editor_property('animation_pipeline')
    apply(animation, 'import_animations', True, True)
    apply(animation, 'import_bone_tracks', True, False)
    # THE 30 Hz TRAP. Interchange inherits the FBX-era default
    # bUse30HzToBakeBoneAnimation = true and re-bakes every bone track at 30 Hz. The
    # first import of these files came back with 37 keys instead of the source's 73,
    # which is exactly the linear-chording the 60 fps export exists to avoid. Both of
    # these must take, and the key count is asserted off the saved asset afterwards.
    apply(animation, 'use30_hz_to_bake_bone_animation', False, True)
    apply(animation, 'custom_bone_animation_sample_rate', SOURCE_FPS, True)
    apply(animation, 'snap_to_closest_frame_boundary', False, False)
    readback['_animationPipelineProperties'] = [q for q in dir(animation) if not q.startswith('_')]
    material = pipeline.get_editor_property('material_pipeline')
    apply(material, 'import_materials', False, False)
    try:
        apply(material.get_editor_property('texture_pipeline'), 'import_textures', False, False)
    except Exception:                                                # noqa: BLE001
        pass
    if missing:
        raise RuntimeError('Interchange pipeline would not accept %r; readback %r. Available on '
                           'common: %r' % (missing, readback,
                                           [p for p in dir(common) if not p.startswith('_')][:60]))
    if skeleton.get_name() not in str(readback.get('skeleton', '')):
        raise RuntimeError('Interchange common.skeleton did not read back as %s (%r)'
                           % (skeleton.get_name(), readback.get('skeleton')))
    override = ue.InterchangePipelineStackOverride()
    override.add_pipeline(pipeline)
    return override, readback


def run_import(reimport=False):
    import unreal as ue
    stamp = stamp_now()
    out = receipt_path('import', stamp)
    planned = plan()
    receipt = dict(status='starting', mode='import', utc=utc(), stamp=stamp,
                   namespace=NAMESPACE, plan={k: v for k, v in planned.items() if k != 'variants'},
                   variants={}, cleaned={}, reimport=bool(reimport), errors=[])
    cleaned = receipt['cleaned']

    def write():
        out.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    if not planned['offlineOk']:
        receipt.update(status='failed_offline_plan', failures=planned['failures'])
        write()
        raise RuntimeError('Offline plan failed: %r' % planned['failures'])
    receipt['editorProcesses'] = _guards(ue)
    before = protected_hashes(planned)
    receipt['protectedBefore'] = before
    checkpoint = CHECKPOINT_ROOT / ('WalkV2-Import-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    for key, target in _targets().items():
        f = disk_umap(target['map'])
        shutil.copy2(f, checkpoint / (key + '.umap'))
        if sha(checkpoint / (key + '.umap')) != sha(f):
            raise RuntimeError('Checkpoint copy mismatch for ' + key)
    receipt['checkpoint'] = str(checkpoint)
    write()

    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    progress = json.loads(IMPORT_MARKER.read_text(encoding='utf-8-sig')) if IMPORT_MARKER.is_file() \
        else {'namespace': NAMESPACE, 'subfolder': SUBFOLDER, 'completed': {}}
    try:
        for vid in sorted(planned['variants']):
            v = planned['variants'][vid]
            if (vid in progress['completed'] and not reimport
                    and assets.does_directory_exist(v['destinationFolder'])):
                receipt['variants'][vid] = dict(progress['completed'][vid], skipped='already imported')
                write()
                continue
            if assets.does_directory_exist(v['destinationFolder']):
                if not reimport or vid not in progress['completed']:
                    raise RuntimeError('%s: %s already exists; pass -WalkV2Reimport to delete ONLY the '
                                       'WalkV2 folders this script itself created and import again'
                                       % (vid, v['destinationFolder']))
                # Only ever a folder this script made: it must be named WalkV2, sit under the
                # variant, and hold nothing but AnimSequences this marker lists.
                listed = sorted(str(x) for x in assets.list_assets(
                    v['destinationFolder'], recursive=True, include_folder=False))
                mine = {q.split('.')[0] for q in progress['completed'][vid]['clips']}
                stray = [q for q in listed if q.split('.')[0].rstrip('/') not in mine]
                if not v['destinationFolder'].endswith('/' + SUBFOLDER) or stray:
                    raise RuntimeError('%s: refusing to clean %s; unexpected contents %r'
                                       % (vid, v['destinationFolder'], stray[:8]))
                if not assets.delete_directory(v['destinationFolder']):
                    raise RuntimeError('%s: delete_directory failed for %s' % (vid, v['destinationFolder']))
                on_disk = ROOT / 'Content' / v['destinationFolder'][6:]
                leftover = [str(f) for f in on_disk.rglob('*') if f.is_file()] if on_disk.exists() else []
                if leftover:
                    raise RuntimeError('%s: files remain after delete_directory: %r' % (vid, leftover[:8]))
                cleaned[vid] = listed
                progress['completed'].pop(vid, None)
            skeleton = ue.load_asset(v['skeleton'])
            if not isinstance(skeleton, ue.Skeleton):
                raise RuntimeError('%s: existing Skeleton not loadable at %s' % (vid, v['skeleton']))
            bones_before = sorted(str(b) for b in ue.AnimPoseExtensions.get_bone_names(
                ue.AnimPoseExtensions.get_reference_pose(skeleton)))
            override, pipeline_readback = _anim_only_pipeline(ue, skeleton)
            task = ue.AssetImportTask()
            for key, value in dict(filename=str(v['source']), destination_path=v['destinationFolder'],
                                   automated=True, replace_existing=False, save=False,
                                   options=override).items():
                task.set_editor_property(key, value)
            tools.import_asset_tasks([task])
            objects = [o for o in list(task.get_objects()) if o]
            if not objects:
                objects = [o for o in (ue.load_asset(p) for p in assets.list_assets(
                    v['destinationFolder'], recursive=True, include_folder=False)) if o]
            kinds = {}
            for o in objects:
                kinds.setdefault(o.get_class().get_name(), []).append(o.get_path_name())
            clips = [o for o in objects if isinstance(o, ue.AnimSequence)]
            skeletons = [o for o in objects if isinstance(o, ue.Skeleton)]
            meshes = [o for o in objects if isinstance(o, (ue.SkeletalMesh, ue.StaticMesh))]
            if skeletons:
                raise RuntimeError('%s: the importer created a Skeleton (%r); refusing before save. '
                                   'The clip must bind to the existing one.' % (vid, kinds))
            if meshes:
                raise RuntimeError('%s: the importer created geometry (%r); animation-only was '
                                   'requested. Refusing before save.' % (vid, kinds))
            if not clips:
                raise RuntimeError('%s: no AnimSequence imported (%r)' % (vid, kinds))
            for clip in clips:
                bound = clip.get_editor_property('skeleton')
                if bound is None or bound.get_path_name() != skeleton.get_path_name():
                    raise RuntimeError('%s: clip %s bound to %r, not the existing skeleton %r'
                                       % (vid, clip.get_path_name(),
                                          bound.get_path_name() if bound else None,
                                          skeleton.get_path_name()))
            walk = [c for c in clips if c.get_name().endswith(WALK_SUFFIX)]
            if len(walk) != 1:
                raise RuntimeError('%s: expected exactly one clip ending %s, got %r'
                                   % (vid, WALK_SUFFIX, [c.get_name() for c in clips]))
            for asset in clips:
                if not assets.save_loaded_asset(asset, only_if_is_dirty=False):
                    raise RuntimeError('save_loaded_asset returned False for %s. FIRST thing to check: '
                                       'a zombie UnrealEditor process holding the package.'
                                       % asset.get_path_name())
            bones_after = sorted(str(b) for b in ue.AnimPoseExtensions.get_bone_names(
                ue.AnimPoseExtensions.get_reference_pose(skeleton)))
            row = dict(id=vid, sourceSha256=v['sourceSha256'], destinationFolder=v['destinationFolder'],
                       pipelineReadback=pipeline_readback, importedClasses=kinds,
                       newWalk=walk[0].get_path_name(), skeleton=skeleton.get_path_name(),
                       clips=sorted(c.get_path_name() for c in clips),
                       skeletonBoneSetUnchanged=bones_before == bones_after,
                       skeletonBoneCount=len(bones_after),
                       skeletonBoneSet=bones_after,
                       oldWalk=v['oldWalk'])
            if not row['skeletonBoneSetUnchanged']:
                raise RuntimeError('%s: the skeleton bone SET changed across the import' % vid)
            progress['completed'][vid] = {k: row[k] for k in
                                          ('id', 'newWalk', 'oldWalk', 'skeleton', 'clips',
                                           'destinationFolder', 'sourceSha256')}
            receipt['variants'][vid] = row
            write()
        IMPORT_MARKER.write_text(json.dumps(progress, indent=2) + '\n', encoding='utf-8')
        receipt['status'] = 'imported_reload_pending'
        write()

        # Reopen: drop every loaded copy and read the measurement off what is on disk.
        for vid, row in receipt['variants'].items():
            for path in row.get('clips', []):
                try:
                    ue.EditorAssetLibrary.load_asset(path)
                except Exception:                                    # noqa: BLE001
                    pass
        ue.EditorAssetLibrary.save_directory(NAMESPACE, only_if_is_dirty=True, recursive=True)
        receipt['status'] = 'measuring'
        write()
        for vid in sorted(receipt['variants']):
            row = receipt['variants'][vid]
            reloaded = ue.load_asset(row['newWalk'])
            old = ue.load_asset(_object_path(row['oldWalk']))
            row['measuredNew'] = measure_clip(ue, reloaded)
            row['measuredOld'] = measure_clip(ue, old)
            write()
        bad = {}
        for vid, row in receipt['variants'].items():
            m = row.get('measuredNew') or {}
            if m.get('numKeys') != SOURCE_KEYS or m.get('numFrames') != SOURCE_FRAMES:
                bad[vid] = {'numKeys': m.get('numKeys'), 'numFrames': m.get('numFrames')}
        receipt['keyCountMatchesSource'] = not bad
        receipt['keyCountExpected'] = {'numKeys': SOURCE_KEYS, 'numFrames': SOURCE_FRAMES,
                                       'fps': SOURCE_FPS, 'lengthSec': CYCLE_SECONDS}
        if bad:
            raise RuntimeError('Imported clips do not carry the source key count (expected %d keys / '
                               '%d frames at %d fps): %r. Interchange re-baked the bone tracks.'
                               % (SOURCE_KEYS, SOURCE_FRAMES, SOURCE_FPS, bad))
        after = protected_hashes(planned)
        receipt['protectedAfter'] = after
        moved = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        receipt['protectedChanged'] = moved
        if moved:
            raise RuntimeError('Pre-existing assets or maps changed bytes during the import: %r' % moved)
        receipt['status'] = 'imported_saved_measured_visual_review_pending'
        write()
    except Exception:
        receipt['status'] = 'failed'
        receipt['errors'].append(traceback.format_exc())
        try:
            receipt['protectedAfter'] = protected_hashes(planned)
        except Exception:                                            # noqa: BLE001
            pass
        write()
        raise
    return receipt


# ---------------------------------------------------------------------------------------
# Native: apply / revert on one map
# ---------------------------------------------------------------------------------------
VARIANT_FIELDS = ('id', 'skeletal_mesh', 'idle_animation', 'walk_animation',
                  'garment_material_slots', 'mesh_relative_yaw',
                  'walk_clip_ground_speed_cm_per_sec', 'walk_clip_neutral_phase')


def _read_variants(ue, actor):
    rows = []
    for s in actor.get_editor_property('body_variants'):
        row = {}
        for field in VARIANT_FIELDS:
            try:
                value = s.get_editor_property(field)
            except Exception:                                        # noqa: BLE001
                continue
            if field == 'garment_material_slots':
                row[field] = [str(n) for n in value]
            elif hasattr(value, 'get_path_name'):
                row[field] = value.get_path_name()
            elif isinstance(value, (int, float)):
                row[field] = float(value)
            else:
                row[field] = str(value)
        rows.append(row)
    return rows


def _build_variants(ue, rows):
    structs = []
    for row in rows:
        s = ue.MikdashResidentBodyVariant()
        for field, value in row.items():
            if field == 'garment_material_slots':
                s.set_editor_property(field, [ue.Name(n) for n in value])
            elif field in ('skeletal_mesh', 'idle_animation', 'walk_animation'):
                asset = ue.load_asset(value) if value else None
                if value and asset is None:
                    raise RuntimeError('Could not load %s for field %s' % (value, field))
                s.set_editor_property(field, asset)
            else:
                s.set_editor_property(field, value)
        structs.append(s)
    return structs


def _apply_rows(target_key, stamp, rows_wanted_fn, kind):
    """Shared guarded map mutation: checkpoint -> load -> snapshot -> set -> save -> reopen -> read."""
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
        raise RuntimeError('Compiled plugin does not expose MikdashResidentBodyVariant; rebuild first')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    try:
        checkpoint = CHECKPOINT_ROOT / ('WalkV2-' + target_key + '-' + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'BeforeWalkV2.umap')
        if sha(checkpoint / 'BeforeWalkV2.umap') != receipt['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy mismatch')
        receipt['checkpoint'] = str(checkpoint)
        write()
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            if not levels.load_level(MAP):
                raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Unexpected editor world')
        crowd = _load('walkv2_scene_snapshot', 'Scripts/release_resident_crowd.py')
        baseline = crowd._scene_snapshot(ue, actors)
        found = [a for a in actors.get_all_level_actors()
                 if a.get_actor_label() == target['populationActorLabel']]
        if len(found) != 1:
            raise RuntimeError('Expected exactly one actor labelled %s, found %d'
                               % (target['populationActorLabel'], len(found)))
        owner = found[0]
        rows_before = _read_variants(ue, owner)
        receipt['bodyVariantsBefore'] = rows_before
        receipt['variantsPresent'] = len(rows_before)
        rows_wanted, notes = rows_wanted_fn(ue, rows_before)
        receipt.update(notes)
        receipt['bodyVariantsWanted'] = rows_wanted
        write()
        changed_needed = rows_wanted != rows_before
        if changed_needed:
            owner.modify(True)
            owner.set_editor_property('body_variants', _build_variants(ue, rows_wanted))
        rows_after = _read_variants(ue, owner)
        if rows_after != rows_wanted:
            raise RuntimeError('body_variants did not read back as planned: %r' % rows_after)
        after_scene = crowd._scene_snapshot(ue, actors)
        moved = {k for k in set(baseline) | set(after_scene) if baseline.get(k) != after_scene.get(k)}
        allowed = {owner.get_name()} if changed_needed else set()
        if moved - allowed:
            raise RuntimeError('Unexpected scene changes: %r' % sorted(moved - allowed)[:20])
        receipt['sceneChanges'] = sorted(moved)
        if changed_needed:
            if not levels.save_current_level():
                raise RuntimeError('Level save failed')
            receipt.update(mapSaved=True, mapAfterSha256=sha(map_file), status='saved_reopen_pending')
            write()
            if not levels.load_level(MAP) or editor.get_editor_world().get_outermost().get_name() != MAP:
                raise RuntimeError('Reopen failed')
            found = [a for a in actors.get_all_level_actors()
                     if a.get_actor_label() == target['populationActorLabel']]
            owner = found[0]
        else:
            receipt.update(mapSaved=False, mapAfterSha256=sha(map_file), status='no_change_needed')
            write()
        readback = _read_variants(ue, owner)
        receipt['readbackAfterReopen'] = readback
        if readback != rows_wanted:
            raise RuntimeError('Readback after reopen differs from the plan')
        # Bone-set identity, read off the reopened assets: this is an animation swap only.
        skeletons = {}
        for row in readback:
            mesh = ue.load_asset(row['skeletal_mesh'])
            clip = ue.load_asset(row['walk_animation'])
            skel = mesh.get_editor_property('skeleton')
            clip_skel = clip.get_editor_property('skeleton')
            names = sorted(str(b) for b in ue.AnimPoseExtensions.get_bone_names(
                ue.AnimPoseExtensions.get_reference_pose(skel)))
            skeletons[row['id']] = dict(
                skeleton=skel.get_path_name(),
                clipSkeleton=clip_skel.get_path_name() if clip_skel else None,
                clipOnMeshSkeleton=bool(clip_skel and clip_skel.get_path_name() == skel.get_path_name()),
                boneCount=len(names), boneSetSha256=hashlib.sha256(
                    '\n'.join(names).encode('utf-8')).hexdigest()[:16], boneSet=names,
                walkLengthSec=round(float(ue.AnimationLibrary.get_sequence_length(clip)), 6))
            if not skeletons[row['id']]['clipOnMeshSkeleton']:
                raise RuntimeError('%s: walk clip is not on the mesh skeleton' % row['id'])
        receipt['skeletonReadback'] = skeletons
        # Read-only census of every OTHER actor in this map that owns a walk clip. The
        # kohen service body (MikdashServiceActor) is one of them; it belongs to another
        # system and is NOT repointed here, so the receipt has to say so out loud.
        others_with_walk = []
        for actor in actors.get_all_level_actors():
            if actor.get_name() == owner.get_name():
                continue
            try:
                clip = actor.get_editor_property('walk_animation')
            except Exception:                                        # noqa: BLE001
                continue
            others_with_walk.append(dict(label=actor.get_actor_label(), name=actor.get_name(),
                                         actorClass=actor.get_class().get_path_name(),
                                         walkAnimation=clip.get_path_name() if clip else None))
        receipt['otherActorsCarryingAWalkClipNotRepointed'] = others_with_walk
        distinct = {v['boneSetSha256'] for v in skeletons.values()}
        receipt['boneSetDigestsDistinct'] = sorted(distinct)
        receipt['otherMapsAfter'] = {k: sha(v) for k, v in others.items()}
        receipt['otherMapsUnchanged'] = receipt['otherMapsAfter'] == receipt['otherMapsBefore']
        if not receipt['otherMapsUnchanged']:
            raise RuntimeError('Another map changed bytes during the run')
        receipt['status'] = ('%s_saved_reopened_readback_pie_review_pending' % kind) if changed_needed \
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
    imported = json.loads(IMPORT_MARKER.read_text(encoding='utf-8-sig'))['completed']

    def wanted(ue, rows_before):
        notes = dict(repointed=[], alreadyPointed=[], notImported=[])
        rows = []
        for row in rows_before:
            new = dict(row)
            entry = imported.get(row['id'])
            if not entry:
                notes['notImported'].append(row['id'])
                rows.append(new)
                continue
            target_clip = _object_path(entry['newWalk'])
            if _object_path(row.get('walk_animation')) != _object_path(entry['oldWalk']) and \
                    _object_path(row.get('walk_animation')) != target_clip:
                raise RuntimeError('%s: current walk %r is neither the shipped clip nor the new one; '
                                   'refusing to guess' % (row['id'], row.get('walk_animation')))
            if _object_path(row.get('walk_animation')) == target_clip:
                notes['alreadyPointed'].append(row['id'])
            else:
                notes['repointed'].append(row['id'])
            new['walk_animation'] = target_clip
            if 'walk_clip_ground_speed_cm_per_sec' in new:
                new['walk_clip_ground_speed_cm_per_sec'] = AUTHORED_GROUND_SPEED
            rows.append(new)
        notes['variantsRepointed'] = len(notes['repointed'])
        notes['variantsPresent'] = len(rows_before)
        return rows, notes
    return _apply_rows(target_key, stamp_now(), wanted, 'apply')


def run_revert(target_key):
    previous = sorted(WALK2.glob('walkv2-apply-%s-*.json' % target_key))
    if not previous:
        raise RuntimeError('No apply receipt for %s to revert to' % target_key)
    source = json.loads(previous[-1].read_text(encoding='utf-8-sig'))
    if 'bodyVariantsBefore' not in source:
        raise RuntimeError('Apply receipt %s carries no bodyVariantsBefore' % previous[-1].name)

    def wanted(ue, rows_before):
        rows = source['bodyVariantsBefore']
        if [r['id'] for r in rows] != [r['id'] for r in rows_before]:
            raise RuntimeError('Variant ids on the actor differ from the apply receipt; refuse')
        return rows, dict(revertSource=previous[-1].name,
                          variantsReverted=sum(1 for a, b in zip(rows, rows_before)
                                               if a.get('walk_animation') != b.get('walk_animation')))
    return _apply_rows(target_key, stamp_now(), wanted, 'revert')


# ---------------------------------------------------------------------------------------
def _main():
    try:
        import unreal                                                # noqa: F401
        native = True
    except ImportError:
        native = False
    if not native:
        planned = plan()
        print(json.dumps(planned, indent=2, default=str))
        if not planned['offlineOk']:
            raise SystemExit('Offline plan has failures: %r' % planned['failures'])
        return
    import unreal
    command_line = unreal.SystemLibrary.get_command_line()
    try:
        if '-WalkV2Import' in command_line:
            run_import(reimport='-WalkV2Reimport' in command_line)
        elif '-WalkV2Apply' in command_line:
            run_apply(_target(command_line))
        elif '-WalkV2Revert' in command_line:
            run_revert(_target(command_line))
        else:
            raise RuntimeError('release_walk_v2: nothing done. Pass -WalkV2Import, or '
                               '-WalkV2Apply / -WalkV2Revert with -WalkV2Target=Main50|Candidate48 '
                               '(add -WalkV2Reimport to -WalkV2Import to redo a WalkV2 folder)')
    except Exception:
        failure = receipt_path('failure', stamp_now())
        failure.write_text(json.dumps(dict(status='failed_before_or_during_run',
                                           commandLine=command_line,
                                           error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise


def _target(command_line):
    m = re.search(r'-WalkV2Target=(Main50|Candidate48)', command_line)
    if not m:
        raise RuntimeError('Pass -WalkV2Target=Main50 or -WalkV2Target=Candidate48')
    return m.group(1)


if __name__ == '__main__':
    _main()

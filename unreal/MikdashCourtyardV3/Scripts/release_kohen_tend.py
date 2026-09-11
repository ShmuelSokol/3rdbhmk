"""Give the Kohen Gadol his lamp-tending clip: import it, then set TendAnimation on both maps.

WHY. The user's first request was "the kohen gadol lighting the menorah". Through cp12 he
walked to the stone and stood in the idle pose at every lamp while all seven flames already
burned. The C++ now (a) plays AMikdashServiceActor::TendAnimation once per Lamp station and
(b) keeps each lamp dark until his own kindling moment (ServiceScheduleMath LampBurning,
read by AMikdashFXDirector). This script supplies the asset and points both actors at it.

MODES (hidden editor, one engine at a time; each writes a receipt):
  -KohenTendImport     Animation-only Interchange import of
                       SourceAssets/characters-review/PilgrimRigV3/tend-v1/meshes/V3_Pilgrim_Man_Standard.glb
                       onto the EXISTING V3_Pilgrim_Man_Standard skeleton, into .../TendV1/.
                       Same pipeline as release_walk_v2 (import_only_animations, common.skeleton =
                       the existing asset) with the 30 Hz trap closed explicitly:
                       use30_hz_to_bake_bone_animation = False, custom sample rate = the source's
                       30 fps. Refuses if a Skeleton or mesh is created, if the clip binds elsewhere,
                       if the key count is not the source's 301, if the skeleton bone SET changes
                       (compared as a set: UE stores it depth-first), or if any protected asset or
                       map changes bytes. Then samples the IMPORTED clip through AnimPose and
                       compares hand_r at the kindle moment with the offline FK.
  -KohenTendApply  -KohenTarget=Candidate48|Main50
                       Checkpoint the .umap into ReviewCheckpoints/KohenTend-*, protected hashes
                       before/after, whole-scene snapshot (only the kohen actor may change), write
                       tend_animation, save, REOPEN, numeric readback, receipt.
  -KohenTendRevert -KohenTarget=...   restore tend_animation from the newest saved apply receipt.
  -KohenTendApplyAll   Candidate48 then Main50.
  -KohenTendRevertAndReapply -KohenTarget=...   prove the revert, then apply again.

Receipts: SourceAssets/service-review/kohen-tend-<mode>-<target>-<stamp>.json
"""
import importlib.util, json, re, shutil, sys, traceback
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/service-review'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
TEND_DIR = ROOT / 'SourceAssets/characters-review/PilgrimRigV3/tend-v1'
GLB = TEND_DIR / 'meshes/V3_Pilgrim_Man_Standard_TendLamp.glb'
MEASURE = TEND_DIR / 'tend-measurements.json'
MARKER = TEND_DIR / 'tend-import-progress.json'
V3 = '/Game/MikdashV3/Characters/PilgrimRigV3/V3_Pilgrim_Man_Standard/'
FOLDER = V3 + 'TendV1'
BODY_MESH = V3 + 'V3_Pilgrim_Man_Standard/SkeletalMeshes/V3_Pilgrim_Man_Standard.V3_Pilgrim_Man_Standard'
SKELETON = V3 + 'V3_Pilgrim_Man_Standard/SkeletalMeshes/V3_Pilgrim_Man_Standard_Skeleton.V3_Pilgrim_Man_Standard_Skeleton'
CLIP_SUFFIX = 'TendLamp'   # Interchange names a lone clip after the source file
SOURCE_FPS = 30
SOURCE_KEYS = 301
DURATION = 10.0
KINDLE_AT = 7.6
CLIP_START = 1.2


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIN = _load('release_walk_v2_finish_for_tend', 'Scripts/release_walk_v2_finish.py')
WALK = _load('release_walk_v2_for_tend', 'Scripts/release_walk_v2.py')
sha, stamp_now, utc = FIN.sha, FIN.stamp_now, FIN.utc
_same, _find, _read_props = FIN._same, FIN._find, FIN._read_props
_object_path, disk_umap, disk_uasset, _targets, _guards = (FIN._object_path, FIN.disk_umap, WALK.disk_uasset,
                                                          FIN._targets, FIN._guards)
KOHEN_LABEL, SERVICE_CLASS = FIN.KOHEN_LABEL, FIN.SERVICE_CLASS
FIELDS = FIN.KOHEN_FIELDS + ('sequence_enabled', 'tend_animation', 'tend_clip_start_seconds',
                             'kindle_at_clip_seconds', 'lamps_dark_until_kindled', 'per_lamp_seconds')
WRITE = ('tend_animation',)


def receipt_path(kind, key, stamp):
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT / ('kohen-tend-%s-%s-%s.json' % (kind, key, stamp))


def protected():
    out = FIN.protected_hashes()
    for p in (BODY_MESH, SKELETON):
        f = disk_uasset(p)
        if f.is_file():
            out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    return out


def tend_clip_path():
    m = json.loads(MARKER.read_text(encoding='utf-8-sig'))
    return m['clip']


# ---------------------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------------------
def run_import():
    import unreal as ue
    stamp = stamp_now()
    out = receipt_path('import', 'V3_Pilgrim_Man_Standard', stamp)
    measured = json.loads(MEASURE.read_text(encoding='utf-8-sig'))
    r = dict(status='starting', mode='import', utc=utc(), stamp=stamp, source=str(GLB),
             sourceSha256=sha(GLB), destination=FOLDER, errors=[])

    def write():
        out.write_text(json.dumps(r, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    try:
        if r['sourceSha256'] != measured['sha256']:
            raise RuntimeError('tend-v1 GLB does not match tend-measurements.json')
        if not measured['geometryComparison']['identical']:
            raise RuntimeError('tend-measurements.json does not assert identical geometry')
        r['editorProcesses'] = _guards(ue)
        assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        if assets.does_directory_exist(FOLDER):
            raise RuntimeError('%s already exists; refusing to import over it' % FOLDER)
        before = protected()
        r['protectedBefore'] = before
        cp = CHECKPOINT_ROOT / ('KohenTend-Import-' + stamp)
        cp.mkdir(parents=True, exist_ok=False)
        for key, target in _targets().items():
            f = disk_umap(target['map'])
            shutil.copy2(f, cp / (key + '.umap'))
            if sha(cp / (key + '.umap')) != sha(f):
                raise RuntimeError('Checkpoint copy mismatch for ' + key)
        r['checkpoint'] = str(cp)
        write()
        skeleton = ue.load_asset(SKELETON)
        mesh = ue.load_asset(BODY_MESH)
        if not isinstance(skeleton, ue.Skeleton) or mesh.get_editor_property('skeleton') != skeleton:
            raise RuntimeError('Body skeleton is not %s' % SKELETON)
        bones_before = sorted(str(b) for b in ue.AnimPoseExtensions.get_bone_names(
            ue.AnimPoseExtensions.get_reference_pose(skeleton)))
        WALK.SOURCE_FPS = SOURCE_FPS          # _anim_only_pipeline reads it for the custom rate
        override, readback = WALK._anim_only_pipeline(ue, skeleton)
        r['pipelineReadback'] = {k: v for k, v in readback.items() if not k.startswith('_')}
        if str(r['pipelineReadback'].get('use30_hz_to_bake_bone_animation')) != 'False':
            raise RuntimeError('use30_hz_to_bake_bone_animation did not read back False')
        task = ue.AssetImportTask()
        for key, value in dict(filename=str(GLB), destination_path=FOLDER, automated=True,
                               replace_existing=False, save=False, options=override).items():
            task.set_editor_property(key, value)
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objects = [o for o in list(task.get_objects()) if o]
        if not objects:
            objects = [o for o in (ue.load_asset(p) for p in assets.list_assets(
                FOLDER, recursive=True, include_folder=False)) if o]
        kinds = {}
        for o in objects:
            kinds.setdefault(o.get_class().get_name(), []).append(o.get_path_name())
        r['importedClasses'] = kinds
        clips = [o for o in objects if isinstance(o, ue.AnimSequence)]
        if [o for o in objects if isinstance(o, ue.Skeleton)]:
            raise RuntimeError('importer created a Skeleton: %r' % kinds)
        if [o for o in objects if isinstance(o, (ue.SkeletalMesh, ue.StaticMesh))]:
            raise RuntimeError('importer created geometry: %r' % kinds)
        if len(clips) != 1 or not clips[0].get_name().endswith(CLIP_SUFFIX):
            raise RuntimeError('expected exactly one clip ending %s: %r' % (CLIP_SUFFIX, kinds))
        clip = clips[0]
        if clip.get_editor_property('skeleton').get_path_name() != skeleton.get_path_name():
            raise RuntimeError('clip bound to %s' % clip.get_editor_property('skeleton').get_path_name())
        if not assets.save_loaded_asset(clip, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset returned False (zombie editor?)')
        bones_after = sorted(str(b) for b in ue.AnimPoseExtensions.get_bone_names(
            ue.AnimPoseExtensions.get_reference_pose(skeleton)))
        r['skeletonBoneSetUnchanged'] = set(bones_before) == set(bones_after)
        r['skeletonBoneCount'] = len(bones_after)
        if not r['skeletonBoneSetUnchanged']:
            raise RuntimeError('skeleton bone SET changed across the import')
        path = clip.get_path_name()
        MARKER.write_text(json.dumps({'clip': path, 'folder': FOLDER, 'sourceSha256': r['sourceSha256'],
                                      'stamp': stamp}, indent=2) + '\n', encoding='utf-8')
        r['clip'] = path
        write()
        reloaded = ue.load_asset(path)
        m = {}
        for key, fn in (('lengthSec', lambda: float(ue.AnimationLibrary.get_sequence_length(reloaded))),
                        ('numFrames', lambda: int(ue.AnimationLibrary.get_num_frames(reloaded))),
                        ('numKeys', lambda: int(ue.AnimationLibrary.get_num_keys(reloaded)))):
            try:
                m[key] = fn()
            except Exception as error:                                   # noqa: BLE001
                m[key] = 'unavailable: ' + str(error)[:100]
        r['imported'] = m
        if m.get('numKeys') != SOURCE_KEYS or abs(float(m.get('lengthSec', 0)) - DURATION) > 1e-3:
            raise RuntimeError('imported clip keys/length %r, expected %d keys over %.1f s: Interchange '
                               're-baked the tracks' % (m, SOURCE_KEYS, DURATION))
        # In-engine pose check against the offline FK (author (x,y,z) -> UE component (x,-y,z)).
        opts = ue.AnimPoseEvaluationOptions()
        sys.path.insert(0, str(ROOT / 'Scripts'))
        import create_pilgrim_v3 as C          # noqa: E402
        import pilgrim_tend_v1 as T            # noqa: E402
        bones = C.skeleton()
        idx = {b['name']: i for i, b in enumerate(bones)}
        rows = []
        worst = 0.0
        for t in (0.0, 2.5, 5.0, KINDLE_AT, 9.0, DURATION):
            pose = WALK._pose_at(ue, reloaded, t, opts)
            q, trans = T.tend_pose(bones, t)
            g = T.fk(bones, q, trans)
            row = {'t': t}
            for b in ('hand_r', 'hand_l', 'head', 'foot_r', 'pelvis'):
                v = ue.AnimPoseExtensions.get_bone_pose(pose, b, ue.AnimPoseSpaces.WORLD).translation
                ue_pos = (float(v.x), float(v.y), float(v.z))
                au = g[idx[b]][1]
                expect = (au[0], -au[1], au[2])
                d = sum((a - e) ** 2 for a, e in zip(ue_pos, expect)) ** 0.5
                worst = max(worst, d)
                row[b] = {'engine': [round(x, 2) for x in ue_pos], 'offline': [round(x, 2) for x in expect],
                          'diffCm': round(d, 3)}
            rows.append(row)
        r['engineVsOfflinePose'] = rows
        r['engineVsOfflineMaxDiffCm'] = round(worst, 3)
        if worst > 0.6:
            raise RuntimeError('imported pose differs from the offline FK by %.2f cm' % worst)
        after = protected()
        r['protectedAfter'] = after
        r['protectedChanged'] = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        if r['protectedChanged']:
            raise RuntimeError('protected assets changed: %r' % r['protectedChanged'])
        r['status'] = 'imported_saved_measured_apply_pending'
        write()
    except Exception:
        r['status'] = 'failed'
        r['errors'].append(traceback.format_exc())
        write()
        raise
    return r


# ---------------------------------------------------------------------------------------
# Apply / revert on one map (guard pattern of release_kohen_startup.py)
# ---------------------------------------------------------------------------------------
def _find_kohen(actors, key):
    kohen = _find(actors, KOHEN_LABEL[key])
    if kohen.get_class().get_path_name() != SERVICE_CLASS:
        raise RuntimeError('%s is not a MikdashServiceActor' % KOHEN_LABEL[key])
    return kohen


def _read(ue, actors, key):
    kohen = _find_kohen(actors, key)
    row = _read_props(ue, kohen, FIELDS)
    row['service_scenario'] = kohen.get_editor_property('service_scenario').name
    return kohen, row


def _fx_readback(ue, actors):
    rows = []
    for a in actors.get_all_level_actors():
        if a.get_class().get_name() == 'MikdashFXDirector':
            rows.append({'label': a.get_actor_label(),
                         'lamps_follow_service': bool(a.get_editor_property('lamps_follow_service')),
                         'lamp_kindle_ramp_seconds': float(a.get_editor_property('lamp_kindle_ramp_seconds'))})
    return rows


def _plan_apply(ue, key, before):
    if before.get('authored_body'):
        raise RuntimeError('AuthoredBody is set; UpdateBodyAnimation never runs on an authored body')
    if before['service_scenario'] != 'ORDINARY_DAY':
        raise RuntimeError('Scenario %s is not ORDINARY_DAY' % before['service_scenario'])
    if before.get('configured_mesh') != BODY_MESH:
        raise RuntimeError('configured_mesh is %r, not the V3 Man_Standard body the clip is on'
                           % before.get('configured_mesh'))
    clip_path = _object_path(tend_clip_path())
    if before.get('tend_animation') not in (None, clip_path):
        raise RuntimeError('tend_animation is already %r; refuse to override' % before.get('tend_animation'))
    clip = ue.load_asset(clip_path)
    body = ue.load_asset(BODY_MESH)
    if clip is None or clip.get_editor_property('skeleton') != body.get_editor_property('skeleton'):
        raise RuntimeError('%s is not on the body skeleton' % clip_path)
    for f, v in (('tend_clip_start_seconds', CLIP_START), ('kindle_at_clip_seconds', KINDLE_AT),
                 ('lamps_dark_until_kindled', True)):
        if not _same(before.get(f), v):
            raise RuntimeError('%s is %r, expected the C++ default %r that the clip is timed to'
                               % (f, before.get(f), v))
    wanted = dict(before)
    wanted['tend_animation'] = clip_path
    return wanted, dict(clip=clip_path, clipLengthSec=float(clip.get_play_length()),
                        kindleSecondsInStation=CLIP_START + KINDLE_AT,
                        perLampSeconds=before.get('per_lamp_seconds'))


def _write(ue, actor, wanted, before):
    actor.modify(True)
    for field in WRITE:
        if _same(wanted.get(field), before.get(field)):
            continue
        value = wanted[field]
        asset = ue.load_asset(value) if value else None
        if value and asset is None:
            raise RuntimeError('Could not load %s' % value)
        actor.set_editor_property(field, asset)


def _apply(key, kind, plan_fn):
    stamp = stamp_now()
    targets = _targets()
    MAP = targets[key]['map']
    map_file = disk_umap(MAP)
    others = {k: disk_umap(t['map']) for k, t in targets.items() if k != key}
    out = receipt_path(kind, key, stamp)
    r = dict(status='starting', mode=kind, target=key, map=MAP, utc=utc(), stamp=stamp,
             mapBeforeSha256=sha(map_file), otherMapsBefore={k: sha(v) for k, v in others.items()},
             errors=[])

    def write():
        out.write_text(json.dumps(r, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    import unreal as ue
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    try:
        r['editorProcesses'] = _guards(ue)
        protected_before = protected()
        clip_file = disk_uasset(_object_path(tend_clip_path()))
        protected_before[str(clip_file.relative_to(ROOT)).replace('\\', '/')] = sha(clip_file)
        r['protectedBefore'] = protected_before
        cp = CHECKPOINT_ROOT / ('KohenTend-%s-%s' % (key, stamp))
        cp.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, cp / 'BeforeKohenTend.umap')
        if sha(cp / 'BeforeKohenTend.umap') != r['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy mismatch')
        r['checkpoint'] = str(cp)
        write()
        if editor.get_editor_world().get_outermost().get_name() != MAP and not levels.load_level(MAP):
            raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Unexpected editor world')
        crowd = _load('kohen_tend_snapshot', 'Scripts/release_resident_crowd.py')
        baseline = crowd._scene_snapshot(ue, actors)
        kohen, before = _read(ue, actors, key)
        r['before'] = before
        r['fxBefore'] = _fx_readback(ue, actors)
        wanted, notes = plan_fn(ue, key, before)
        r['wanted'], r['notes'] = wanted, notes
        write()
        changed = not _same(wanted, before)
        if changed:
            _write(ue, kohen, wanted, before)
        _, after_set = _read(ue, actors, key)
        if not _same(after_set, wanted):
            raise RuntimeError('Did not read back as planned before save: %r' % after_set)
        after_scene = crowd._scene_snapshot(ue, actors)
        moved = {k for k in set(baseline) | set(after_scene) if baseline.get(k) != after_scene.get(k)}
        if moved - ({kohen.get_name()} if changed else set()):
            raise RuntimeError('Unexpected scene changes: %r' % sorted(moved)[:20])
        r['sceneChanges'] = sorted(moved)
        if changed:
            if not levels.save_current_level():
                raise RuntimeError('Level save failed')
            r.update(mapSaved=True, mapAfterSha256=sha(map_file), status='saved_reopen_pending')
            write()
            if not levels.load_level(MAP) or editor.get_editor_world().get_outermost().get_name() != MAP:
                raise RuntimeError('Reopen failed')
        else:
            r.update(mapSaved=False, mapAfterSha256=sha(map_file))
        _, readback = _read(ue, actors, key)
        r['readbackAfterReopen'] = readback
        r['fxAfterReopen'] = _fx_readback(ue, actors)
        if not _same(readback, wanted):
            raise RuntimeError('Readback after reopen differs: %r' % readback)
        r['otherMapsAfter'] = {k: sha(v) for k, v in others.items()}
        r['otherMapsUnchanged'] = r['otherMapsAfter'] == r['otherMapsBefore']
        if not r['otherMapsUnchanged']:
            raise RuntimeError('Another map changed bytes during the run')
        protected_after = protected()
        protected_after[str(clip_file.relative_to(ROOT)).replace('\\', '/')] = sha(clip_file)
        this_map = str(map_file.relative_to(ROOT)).replace('\\', '/')
        r['protectedAfter'] = protected_after
        r['protectedChangedExcludingThisMap'] = sorted(
            k for k in set(protected_before) | set(protected_after)
            if protected_before.get(k) != protected_after.get(k) and k != this_map)
        if r['protectedChangedExcludingThisMap']:
            raise RuntimeError('Protected assets changed: %r' % r['protectedChangedExcludingThisMap'])
        r['status'] = ('%s_saved_reopened_readback_frame_pending' % kind) if changed \
            else ('%s_no_change_needed' % kind)
        write()
    except Exception:
        r['status'] = 'failed'
        r['errors'].append(traceback.format_exc())
        try:
            r['mapAfterSha256'] = sha(map_file)
        except Exception:                                             # noqa: BLE001
            pass
        write()
        raise
    return r


def run_apply(key):
    return _apply(key, 'apply', _plan_apply)


def run_revert(key):
    previous = sorted(p for p in OUT.glob('kohen-tend-apply-%s-*.json' % key)
                      if json.loads(p.read_text(encoding='utf-8-sig')).get('mapSaved'))
    if not previous:
        raise RuntimeError('No saved apply receipt for %s to revert' % key)
    src = json.loads(previous[-1].read_text(encoding='utf-8-sig'))

    def plan(ue, k, before):
        restore = dict(before)
        for f in WRITE:
            restore[f] = src['before'][f]
        for f in ('configured_mesh', 'authored_body', 'service_scenario', 'walk_animation', 'idle_animation'):
            if not _same(before.get(f), src['before'].get(f)):
                raise RuntimeError('%s moved since the apply (%r -> %r); refuse to revert blind'
                                   % (f, src['before'].get(f), before.get(f)))
        return restore, dict(revertSource=previous[-1].name, revertSourceSha256=sha(previous[-1]))
    return _apply(key, 'revert', plan)


def _key(cmd):
    m = re.search(r'-KohenTarget=(Main50|Candidate48)', cmd)
    if not m:
        raise RuntimeError('Pass -KohenTarget=Main50|Candidate48')
    return m.group(1)


def _main():
    import unreal
    cmd = unreal.SystemLibrary.get_command_line()
    try:
        if '-KohenTendImport' in cmd:
            run_import()
        elif '-KohenTendRevertAndReapply' in cmd:
            key = _key(cmd)
            run_revert(key)
            run_apply(key)
        elif '-KohenTendApplyAll' in cmd:
            for key in ('Candidate48', 'Main50'):
                run_apply(key)
        elif '-KohenTendApply' in cmd:
            run_apply(_key(cmd))
        elif '-KohenTendRevert' in cmd:
            run_revert(_key(cmd))
        else:
            raise RuntimeError('release_kohen_tend: pass a -KohenTend* mode')
    except Exception:
        receipt_path('failure', 'any', stamp_now()).write_text(
            json.dumps(dict(commandLine=cmd, error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise
    finally:
        if '-executepythonscript' in cmd.lower() and '-run=pythonscript' not in cmd.lower():
            unreal.SystemLibrary.quit_editor()


if __name__ == '__main__':
    _main()

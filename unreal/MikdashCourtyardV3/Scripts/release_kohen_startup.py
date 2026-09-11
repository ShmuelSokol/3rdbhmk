"""Turn the Kohen Gadol ON in the shipped build: start_on_begin_play on both maps.

WHY THIS EXISTS. SourceAssets/visual-review/PEOPLE-IN-FRAME-20260910.md proved from the cp11
packaged build that the Kohen Gadol is not in the game at all: AMikdashServiceActor::ResolveBody
is reachable only from StartService(), BeginPlay calls StartService() only when
bStartOnBeginPlay && bSequenceEnabled, and bStartOnBeginPlay was False on both maps. It is an
EditAnywhere per-instance property, not config, so it can only be changed on the placed actor.

WHY IT WAS FALSE (read before flipping, not guessed). Every service receipt says the same:
"Placement and configuration only. The figure is not started: start_on_begin_play stays False so
nothing animates before a visual review" (release_kohen_service.spec.json). The later reviews
kept it off for VISUAL findings, none of them a crash, a refusal or a route through geometry:
  * grounded-full-review-20260909.json: all 18 stations arrived, 0 native blocked legs, 0 endpoint
    Pawn capsule hits, 0 arrival failures -- but 7 stair centre-foot floor mismatches;
  * grounded-service-visual-review-20260909.json: stand-in garments (not the eight golden
    garments), hands in the idle pose with no wick/oil/lamp interaction animation;
  * the 1.49x foot skate, since fixed by release_walk_v2_finish.py (clip + 119.95 cm/s).
Those findings are re-exposed deliberately, and reported in the receipt, not silently.

WHAT IT WRITES, per map, on the kohen actor only:
  start_on_begin_play = True, sequence_enabled = True, and on Main50 only:
  configured_mesh = the V3 Man_Standard mesh + configured_body_yaw_degrees = -90 +
  idle_animation = the V3 idle -- exactly what Candidate48 already carries. Main50 had no mesh
  and no idle set, so SpawnBody resolved them at run time: first by scanning /Game/MetaHumans
  (which, since 10 Sep 23:55Z, contains MH_Elder_Kohen from another agent's MetaHuman build --
  the body would be whatever that scan loads first) and otherwise by the hardcoded
  MeshFallbacks[0] + ResolveClip literal paths. Pinning makes both maps resolve identically
  and explicitly. ConfiguredMesh at yaw -90 / scale 1.0 is what the PilgrimRigV3 fallback did.

REFUSES if AuthoredBody is set (UpdateBodyAnimation returns early on an authored body, so the
clip work would be a no-op), if the scenario is not ORDINARY_DAY, if the walk clip is not the
WalkV2 clip on the body's skeleton at 119.95 cm/s, if someone already chose a different body or
idle, or if the idle is off-skeleton.

MODES (hidden editor, one engine at a time):
  -KohenStartupApplyAll                 Candidate48 then Main50, each a full guarded pass
  -KohenStartupApply  -KohenTarget=Candidate48|Main50
  -KohenStartupRevert -KohenTarget=...  restore the newest saved apply receipt's before block
  -KohenStartupRevertAndReapply -KohenTarget=...

Guards: checkpoint the .umap (hash-verified) into ReviewCheckpoints\\KohenStartup-*, protected
hash set before/after, whole-scene snapshot (only the kohen actor may change), other map bytes
unchanged, save, REOPEN, numeric readback, receipt in SourceAssets/service-review/.

Launch:
  UnrealEditor.exe "<uproject>" -ExecutePythonScript=C:/.../Scripts/release_kohen_startup.py
      -KohenStartupApplyAll -unattended -nullrhi -NoSplash -abslog=<unique>
"""
import importlib.util, json, re, shutil, sys, traceback
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/service-review'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIN = _load('release_walk_v2_finish_for_startup', 'Scripts/release_walk_v2_finish.py')
sha, stamp_now, utc = FIN.sha, FIN.stamp_now, FIN.utc
_same, _find, _read_props = FIN._same, FIN._find, FIN._read_props
_object_path, disk_umap, _targets, _guards = FIN._object_path, FIN.disk_umap, FIN._targets, FIN._guards

KOHEN_LABEL = FIN.KOHEN_LABEL
SERVICE_CLASS = FIN.SERVICE_CLASS
V3 = '/Game/MikdashV3/Characters/PilgrimRigV3/V3_Pilgrim_Man_Standard/'
BODY_MESH = V3 + 'V3_Pilgrim_Man_Standard/SkeletalMeshes/V3_Pilgrim_Man_Standard.V3_Pilgrim_Man_Standard'
IDLE = (V3 + 'V3_Pilgrim_Man_Standard/SkeletalMeshes/V3_Pilgrim_Man_StandardA_Pilgrim_Original_Idle.'
        'V3_Pilgrim_Man_StandardA_Pilgrim_Original_Idle')
WALK = V3 + 'WalkV2/V3_Pilgrim_Man_StandardA_Pilgrim_Original_Walk.V3_Pilgrim_Man_StandardA_Pilgrim_Original_Walk'
WALK_SPEED = 119.95
FIELDS = FIN.KOHEN_FIELDS + ('sequence_enabled',)
WRITE = ('start_on_begin_play', 'sequence_enabled', 'configured_mesh', 'configured_body_yaw_degrees',
         'idle_animation')
ASSET_FIELDS = ('idle_animation', 'configured_mesh')

WHY_IT_WAS_OFF = dict(
    stated='Placement and configuration only. The figure is not started: start_on_begin_play stays '
           'False so nothing animates before a visual review. (release_kohen_service.spec.json)',
    findingsThatKeptItOff=[
        'grounded-full-review-20260909.json: 7 stair centre-foot floor mismatches (all raw-walking '
        'with walkable support); 0 blocked legs, 0 endpoint Pawn capsule hits, 0 arrival failures',
        'grounded-service-visual-review-20260909.json: stand-in garments; hands in idle pose, no '
        'wick/oil/lamp interaction animation; washed-out pale clothing in the doorway view',
        '1.49x forward foot skate (clip 60.48 vs 90 cm/s) -- fixed 2026-09-10 by release_walk_v2_finish.py'],
    crashOrGeometryDefect=False,
    reexposedDeliberately=True,
    probesThatAssertServiceOff=[
        'Scripts/probe_transit_bridge_runtime.py', 'Scripts/probe_candidate_kotel_access.py',
        'Scripts/probe_candidate_metric_birds.py', 'Scripts/probe_candidate_transit.py',
        'Scripts/probe_enclosure_collision_restore.py', 'Scripts/probe_service_candidate48.py',
        'Scripts/configure_candidate_grounded_service.py', 'Scripts/configure_service_body_v3.py'])


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


def _plan_apply(ue, key, before):
    if before.get('authored_body'):
        raise RuntimeError('The kohen has AuthoredBody set (%r); UpdateBodyAnimation never runs on an '
                           'authored body. Refusing.' % before['authored_body'])
    if before['service_scenario'] != 'ORDINARY_DAY':
        raise RuntimeError('Scenario is %s, not ORDINARY_DAY; refuse to start it' % before['service_scenario'])
    if _object_path(before.get('walk_animation')) != WALK:
        raise RuntimeError('Walk clip is %r, not the WalkV2 clip; run release_walk_v2_finish.py first'
                           % before.get('walk_animation'))
    if not _same(before.get('walk_speed_cm_per_sec'), WALK_SPEED):
        raise RuntimeError('Walk speed %r is not the clip speed %.2f; the skate would return'
                           % (before.get('walk_speed_cm_per_sec'), WALK_SPEED))
    mesh = before.get('configured_mesh')
    if mesh not in (None, BODY_MESH):
        raise RuntimeError('configured_mesh is %r -- someone chose a body; refuse to override it' % mesh)
    if before.get('idle_animation') not in (None, IDLE):
        raise RuntimeError('idle_animation is %r; refuse to override it' % before.get('idle_animation'))
    if mesh is None and not _same(before.get('configured_body_yaw_degrees'), 0.0):
        raise RuntimeError('configured_body_yaw_degrees set without a mesh; refuse to guess')
    if mesh is not None and not _same(before.get('configured_body_yaw_degrees'), -90.0):
        raise RuntimeError('configured mesh with yaw %r, not -90; refuse' % before.get('configured_body_yaw_degrees'))
    body = ue.load_asset(BODY_MESH)
    skel = body.get_editor_property('skeleton')
    for path in (WALK, IDLE):
        clip = ue.load_asset(path)
        if clip is None or clip.get_editor_property('skeleton') != skel:
            raise RuntimeError('%s is not on the body skeleton' % path)
    wanted = dict(before)
    wanted.update(start_on_begin_play=True, sequence_enabled=True, configured_mesh=BODY_MESH,
                  configured_body_yaw_degrees=-90.0, idle_animation=IDLE)
    mh = ROOT / 'Content/MetaHumans'
    notes = dict(
        whyItWasOff=WHY_IT_WAS_OFF,
        bodyBefore='configured_mesh' if mesh else 'runtime discovery: /Game/MetaHumans scan, then '
                   'hardcoded MeshFallbacks[0]; idle via hardcoded ResolveClip literal path',
        metaHumansOnDisk=sorted(str(p.relative_to(ROOT)) for p in mh.rglob('*.uasset')) if mh.is_dir() else [],
        bodyAfter=BODY_MESH, idleAfter=IDLE, walk=WALK, walkSpeed=before.get('walk_speed_cm_per_sec'))
    return wanted, notes


def _write(ue, actor, wanted, before):
    actor.modify(True)
    for field in WRITE:
        if _same(wanted.get(field), before.get(field)):
            continue
        value = wanted[field]
        if field in ASSET_FIELDS:
            asset = ue.load_asset(value) if value else None
            if value and asset is None:
                raise RuntimeError('Could not load %s' % value)
            actor.set_editor_property(field, asset)
        else:
            actor.set_editor_property(field, value)


def receipt_path(kind, key, stamp):
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT / ('kohen-startup-%s-%s-%s.json' % (kind, key, stamp))


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
        protected_before = FIN.protected_hashes()
        r['protectedBefore'] = protected_before
        cp = CHECKPOINT_ROOT / ('KohenStartup-%s-%s' % (key, stamp))
        cp.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, cp / 'BeforeKohenStartup.umap')
        if sha(cp / 'BeforeKohenStartup.umap') != r['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy mismatch')
        r['checkpoint'] = str(cp)
        write()
        if editor.get_editor_world().get_outermost().get_name() != MAP and not levels.load_level(MAP):
            raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Unexpected editor world')
        crowd = _load('kohen_startup_snapshot', 'Scripts/release_resident_crowd.py')
        baseline = crowd._scene_snapshot(ue, actors)
        kohen, before = _read(ue, actors, key)
        r['before'] = before
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
        if not _same(readback, wanted):
            raise RuntimeError('Readback after reopen differs: %r' % readback)
        r['otherMapsAfter'] = {k: sha(v) for k, v in others.items()}
        r['otherMapsUnchanged'] = r['otherMapsAfter'] == r['otherMapsBefore']
        if not r['otherMapsUnchanged']:
            raise RuntimeError('Another map changed bytes during the run')
        protected_after = FIN.protected_hashes()
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
    previous = sorted(p for p in OUT.glob('kohen-startup-apply-%s-*.json' % key)
                      if json.loads(p.read_text(encoding='utf-8-sig')).get('mapSaved'))
    if not previous:
        raise RuntimeError('No saved apply receipt for %s to revert' % key)
    src = json.loads(previous[-1].read_text(encoding='utf-8-sig'))

    def plan(ue, k, before):
        restore = dict(before)
        for f in WRITE:
            restore[f] = src['before'][f]
        for f in ('walk_animation', 'walk_speed_cm_per_sec', 'authored_body', 'service_scenario'):
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
        if '-KohenStartupApplyAll' in cmd:
            for key in ('Candidate48', 'Main50'):
                run_apply(key)
        elif '-KohenStartupRevertAndReapply' in cmd:
            key = _key(cmd)
            run_revert(key)
            run_apply(key)
        elif '-KohenStartupApply' in cmd:
            run_apply(_key(cmd))
        elif '-KohenStartupRevert' in cmd:
            run_revert(_key(cmd))
        else:
            raise RuntimeError('release_kohen_startup: pass a -KohenStartup* mode')
    except Exception:
        receipt_path('failure', 'any', stamp_now()).write_text(
            json.dumps(dict(commandLine=cmd, error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise
    finally:
        if '-executepythonscript' in cmd.lower() and '-run=pythonscript' not in cmd.lower():
            unreal.SystemLibrary.quit_editor()


if __name__ == '__main__':
    _main()

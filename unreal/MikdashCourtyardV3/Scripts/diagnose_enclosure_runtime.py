"""PIE probe for AMikdashEnclosure: what the precinct actor actually is after BeginPlay.

Real RHI, isolated save slots, no map writes. Finds every AMikdashEnclosure in the game world
once BeginPlay has run and dumps its state, its own numeric API, its five mesh properties, each
HISM component (mesh path, instance count, material, visibility, cull distances, sample instance
transforms and world bounds), a sample of the hide list's actors, and two line traces from the
lighting agent's v7/v8 camera positions toward the east gate. Writes a receipt to
SourceAssets/enclosure-review/native-enclosure-runtime-<stamp>.json and quits the editor.

Launch (one process; never while another native job runs; the map is the first argument):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough
      -ExecCmds="py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/diagnose_enclosure_runtime.py"
      -TestSavePrefix=FableProbe_Enclosure_01
      -ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FableProbe_Enclosure_01,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FableProbe_Enclosure_01_Settings
      -unattended -NoSplash -abslog=C:\\Mikdash\\Working-5.8\\Fable-Enclosure-Runtime-01.log

  Add -Candidate48 (and pass the candidate map as the first argument) for the isolated map.

Nothing here fixes anything. The enclosure's HISM components have NoCollision by design, so a
trace can never hit the wall itself; the traces report what stands between the camera and the
gate (terrain, buildings) and the ground Z under each camera.
"""
import hashlib
import json
import os
import re
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
CMD = u.SystemLibrary.get_command_line()
CANDIDATE = '-candidate48' in CMD.lower()
MAP = ('/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough' if CANDIDATE
       else '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough')
OUT_DIR = ROOT / 'SourceAssets/enclosure-review'
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = OUT_DIR / ('native-enclosure-runtime-%s-%s.json' % ('Candidate48' if CANDIDATE else 'Main50', STAMP))
MESH_FOLDER = '/Game/MikdashV3/FutureMountV1/EnclosureV2/Meshes'
MESH_NAMES = ('SM_EnclosureV2_WallSegment', 'SM_EnclosureV2_Gate', 'SM_EnclosureV2_Corner',
              'SM_EnclosureV2_OverlaySlab', 'SM_EnclosureV2_Foundation')
MESH_PROPS = ('WallModuleMesh', 'GateModuleMesh', 'CornerModuleMesh', 'FoundationModuleMesh', 'OverlayQuadMesh')
HISM_NAMES = ('WallInstances', 'GateInstances', 'CornerInstances', 'FoundationInstances', 'OverlayInstances')
# The lighting agent's v7/v8 camera XY (lighting-v3-capture-20260908T220658Z.json) and the east
# gate on the Temple axis; Z is traced live.
GATE_XY = (112224.0, 0.0) if CANDIDATE else (116900.0, 0.0)
V7_XY = (GATE_XY[0] - 4000.0, 0.0)
V8_XY = (GATE_XY[0] + 6000.0, 0.0)
EYE_CM = 168.0

ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def xyz(v):
    return [float(v.x), float(v.y), float(v.z)]


def asset_path(obj):
    return None if obj is None else str(obj.get_path_name())


report = dict(status='starting', stamp=STAMP, map=MAP, errors=[], scope=(
    'Diagnostic only. Real-RHI PIE; nothing written to the map or to user save slots. '
    'Enclosure HISMs have NoCollision, so traces report obstructions and ground, never the wall.'))
map_file = ROOT / 'Content' / (MAP[6:] + '.umap')
report['mapShaBefore'] = sha(map_file)
main_file = ROOT / 'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap'
main_before = sha(main_file)


def write():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')


# ---------------------------------------------------------------------------
# Preflight: editor world, no PIE, clean packages, save isolation, mesh packages on disk
# ---------------------------------------------------------------------------
assert ed.get_game_world() is None, 'a game world is already active'
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'dirty map packages'
assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'dirty content packages'
assert ed.get_editor_world().get_outermost().get_name() == MAP, 'loaded world is not ' + MAP
prefix_match = re.search(r'-TestSavePrefix=(FableProbe_[A-Za-z0-9_]+)', CMD)
assert prefix_match, 'Require a unique -TestSavePrefix=FableProbe_<stamp> and Game ini overrides'
test_prefix = prefix_match.group(1)
for section, key, value in [('MikdashSaveSystem', 'SlotNamePrefix', test_prefix),
                            ('MikdashSettingsSubsystem', 'SaveSlot', test_prefix + '_Settings')]:
    assert ('[/Script/MikdashRuntime.' + section + ']:' + key + '=' + value) in CMD, 'Missing save-isolation ini override'
save_roots = [ROOT / 'Saved/SaveGames', Path(os.environ['LOCALAPPDATA']) / 'MikdashCourtyardV3/Saved/SaveGames']


def user_save_hashes():
    return {str(p): sha(p) for folder in save_roots if folder.exists()
            for p in folder.glob('*.sav') if not p.name.startswith(('FableProbe_', 'AstraProbe_'))}


original_saves = user_save_hashes()
report['saveIsolation'] = dict(testPrefix=test_prefix, originalSaveFileCount=len(original_saves))

report['meshPackages'] = {}
for name in MESH_NAMES:
    path = MESH_FOLDER + '/' + name
    on_disk = disk_path(path)
    report['meshPackages'][name] = dict(assetRegistryExists=bool(u.EditorAssetLibrary.does_asset_exist(path)),
                                        fileOnDisk=on_disk.exists(),
                                        fileSha256=sha(on_disk) if on_disk.exists() else None)

# The saved actor in the EDITOR world, before play: what does it reference right now?
editor_actors = [a for a in u.EditorActorSubsystem().get_all_level_actors()
                 if a is not None and a.get_class().get_name() == 'MikdashEnclosure']
report['editorWorldActors'] = []
for actor in editor_actors:
    report['editorWorldActors'].append(dict(
        label=str(actor.get_actor_label()), name=str(actor.get_name()),
        meshProperties={p: asset_path(actor.get_editor_property(p)) for p in MESH_PROPS},
        wallMaterial=asset_path(actor.get_editor_property('WallMaterial')),
        overlayMaterial=asset_path(actor.get_editor_property('OverlayMaterial')),
        initialState=str(actor.get_editor_property('InitialState')),
        worldCmPerAmah=float(actor.get_editor_property('WorldCmPerAmah')),
        courtPlatformHalfExtentCm=float(actor.get_editor_property('CourtPlatformHalfExtentCm')),
        groundProfileStepsPerSide=int(actor.get_editor_property('GroundProfileStepsPerSide')),
        groundProfileHighCount=len(actor.get_editor_property('GroundProfileHighZCm')),
        groundProfileLowCount=len(actor.get_editor_property('GroundProfileLowZCm')),
        explicitHideLabels=len(actor.get_editor_property('ExplicitHideLabels')),
        explicitHideMeshNames=len(actor.get_editor_property('ExplicitHideMeshNames')),
        hidden=bool(actor.get_editor_property('hidden')),
        level=str(actor.get_outer().get_outer().get_name()) if actor.get_outer() else None))
write()

settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse = settings.get_editor_property('GameGetsMouseControl')
old_throttle = u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
state = dict(start=time.monotonic(), phase='world', at=time.monotonic(), stopping=False, done=False)


def trace(world, start, end, label):
    result = u.SystemLibrary.line_trace_single(world, start, end, u.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                              False, [], u.DrawDebugTrace.NONE, True)
    if isinstance(result, tuple): result = result[-1]
    d = {str(k).lower().replace('_', ''): v for k, v in result.to_dict().items()} if result is not None else {}
    hit = bool(d.get('blockinghit', result is not None))
    row = dict(label=label, start=xyz(start), end=xyz(end), blockingHit=hit)
    if hit:
        component = d.get('hitcomponent')
        actor = component.get_owner() if component else None
        point = d.get('impactpoint')
        row.update(distanceCm=float(d.get('distance') or 0), location=xyz(point) if point else None,
                   hitActor=str(actor.get_actor_label()) if actor else None,
                   hitActorClass=str(actor.get_class().get_name()) if actor else None,
                   hitComponent=str(component.get_name()) if component else None,
                   hitMesh=asset_path(component.static_mesh) if component and hasattr(component, 'static_mesh') else None)
    return row


def ground_z(world, x, y):
    row = trace(world, u.Vector(x, y, 30000.0), u.Vector(x, y, -30000.0), 'ground')
    return (row['location'][2] if row['blockingHit'] else None), row


def dump_hism(component, mesh_bounds_cache):
    mesh = component.static_mesh
    count = int(component.get_instance_count())
    bounds_origin, bounds_extent, _ = u.SystemLibrary.get_component_bounds(component)
    row = dict(name=str(component.get_name()), staticMesh=asset_path(mesh), instanceCount=count,
               material0=asset_path(component.get_material(0)) if mesh else None,
               visible=bool(component.is_visible()),
               hiddenInGame=bool(component.get_editor_property('hidden_in_game')),
               castShadow=bool(component.get_editor_property('cast_shadow')),
               collision=str(component.get_collision_enabled()),
               instanceStartCullDistance=int(component.get_editor_property('instance_start_cull_distance')),
               instanceEndCullDistance=int(component.get_editor_property('instance_end_cull_distance')),
               componentBoundsOrigin=xyz(bounds_origin) if count else None,
               componentBoundsExtent=xyz(bounds_extent) if count else None,
               sampleInstances=[])
    if mesh is not None and count:
        if asset_path(mesh) not in mesh_bounds_cache:
            b = mesh.get_bounds()
            mesh_bounds_cache[asset_path(mesh)] = (xyz(b.origin), xyz(b.box_extent))
        origin, extent = mesh_bounds_cache[asset_path(mesh)]
        for index in sorted({0, count // 2, count - 1}):
            transform = component.get_instance_transform(index, True)
            if isinstance(transform, tuple):
                transform = transform[1] if transform[0] else None
            if transform is None:
                row['sampleInstances'].append(dict(index=index, error='get_instance_transform returned False'))
                continue
            loc, scale = transform.translation, transform.scale3d
            row['sampleInstances'].append(dict(
                index=index, location=xyz(loc), yaw=float(transform.rotation.rotator().yaw), scale=xyz(scale),
                approxWorldBoundsMin=[loc.x + (origin[0] - extent[0]) * scale.x, loc.y + (origin[1] - extent[1]) * scale.y,
                                      loc.z + (origin[2] - extent[2]) * scale.z],
                approxWorldBoundsMax=[loc.x + (origin[0] + extent[0]) * scale.x, loc.y + (origin[1] + extent[1]) * scale.y,
                                      loc.z + (origin[2] + extent[2]) * scale.z]))
    return row


def dump_world(world):
    actors = list(u.GameplayStatics.get_all_actors_of_class(world, u.MikdashEnclosure))
    report['pieActorCount'] = len(actors)
    report['pieActors'] = []
    mesh_bounds_cache = {}
    for actor in actors:
        counts = actor.get_instance_counts()
        faces = actor.get_outer_faces_cm()
        found, missing, duplicated = actor.get_hide_list_resolution()
        row = dict(
            label=str(actor.get_actor_label()), name=str(actor.get_name()),
            precinctState=str(actor.get_precinct_state()),
            isTransitioning=bool(actor.is_transitioning()),
            actorHidden=bool(actor.get_editor_property('hidden')),
            rootVisible=bool(actor.get_editor_property('root_component').is_visible()) if actor.get_editor_property('root_component') else None,
            instanceCounts=dict(wall=int(counts.x), gate=int(counts.y), corner=int(counts.z),
                                foundation=int(counts.w), overlay=int(actor.get_overlay_instance_count())),
            outerFacesCm=dict(west=float(faces.x), north=float(faces.y), east=float(faces.z), south=float(faces.w)),
            wallBaseZRangeCm={side: [float(actor.get_wall_base_z_range_cm(i).x), float(actor.get_wall_base_z_range_cm(i).y)]
                              for i, side in enumerate(('north', 'east', 'south', 'west'))},
            deepestFoundationCm={side: float(actor.get_deepest_foundation_cm(i))
                                 for i, side in enumerate(('north', 'east', 'south', 'west'))},
            groundProfileStatus=str(actor.get_ground_profile_status()),
            hideListResolution=dict(found=int(found), missing=int(missing), duplicated=int(duplicated)),
            hideSetFingerprint=str(actor.get_hide_set_fingerprint()),
            modernBuildingsSelected=int(actor.count_modern_buildings_inside()),
            meshProperties={p: asset_path(actor.get_editor_property(p)) for p in MESH_PROPS},
            wallMaterial=asset_path(actor.get_editor_property('WallMaterial')),
            wallMaterialInstancingUsage=bool(u.MaterialEditingLibrary.has_material_usage(actor.get_editor_property('WallMaterial'), u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)) if actor.get_editor_property('WallMaterial') else False,
            worldCmPerAmah=float(actor.get_editor_property('WorldCmPerAmah')),
            initialState=str(actor.get_editor_property('InitialState')),
            hisms=[])
        for component in actor.get_components_by_class(u.HierarchicalInstancedStaticMeshComponent):
            row['hisms'].append(dump_hism(component, mesh_bounds_cache))
        # A sample of the hide list: are those actors hidden in the game world right now?
        labels = list(actor.get_editor_property('ExplicitHideLabels'))
        sample = labels[:3] + labels[len(labels) // 2: len(labels) // 2 + 3] + labels[-3:]
        by_label = {}
        for a in u.GameplayStatics.get_all_actors_of_class(world, u.StaticMeshActor):
            l = str(a.get_actor_label())
            if l in sample:
                by_label[l] = bool(a.get_editor_property('hidden'))
        row['hideListSample'] = dict(labels=sample, hiddenInGame=by_label)
        report['pieActors'].append(row)

    # The v7 / v8 cameras and the gate.
    traces = []
    gz7, g7 = ground_z(world, *V7_XY)
    gz8, g8 = ground_z(world, *V8_XY)
    gzg, gg = ground_z(world, *GATE_XY)
    traces += [g7, g8, gg]
    gate_mid = u.Vector(GATE_XY[0], GATE_XY[1], (gzg if gzg is not None else 0.0) + 1500.0)
    if gz7 is not None:
        traces.append(trace(world, u.Vector(V7_XY[0], V7_XY[1], gz7 + EYE_CM), gate_mid, 'v7_camera_to_gate_opening'))
        traces.append(trace(world, u.Vector(V7_XY[0], V7_XY[1], gz7 + EYE_CM),
                            u.Vector(GATE_XY[0] + 20000.0, 0.0, gz7 + EYE_CM), 'v7_camera_level_east_20000cm'))
    if gz8 is not None:
        traces.append(trace(world, u.Vector(V8_XY[0], V8_XY[1], gz8 + EYE_CM), gate_mid, 'v8_camera_to_gate_opening'))
    report['traces'] = dict(groundZ=dict(v7=gz7, v8=gz8, gate=gzg), rows=traces,
                            note='Enclosure HISMs are NoCollision: a hit on the wall is impossible by design; '
                                 'these show what else is in the line of sight and the ground under each camera.')


def finish(status):
    if state['stopping']:
        return
    report['status'] = status
    state['stopping'] = True
    state['at'] = time.monotonic()
    levels.editor_request_end_play()
    write()


def tick(dt):
    try:
        now = time.monotonic()
        world = ed.get_game_world()
        if state['stopping']:
            if world and now - state['at'] < 15:
                return
            if world:
                report['errors'].append('PIE teardown timeout')
            report['pieEnded'] = world is None
            report['mapBytesUnchanged'] = sha(map_file) == report['mapShaBefore']
            report['mainBytesUnchanged'] = sha(main_file) == main_before
            report['saveIsolation']['originalSavesUnchanged'] = user_save_hashes() == original_saves
            for restore in (lambda: settings.set_editor_property('GameGetsMouseControl', old_mouse),
                            lambda: u.SystemLibrary.execute_console_command(ed.get_editor_world(), 'Slate.bAllowThrottling ' + str(old_throttle))):
                try:
                    restore()
                except Exception as exc:  # noqa: BLE001
                    report['errors'].append('Cleanup: ' + repr(exc))
            if report['errors'] or not report['mapBytesUnchanged'] or not report['mainBytesUnchanged'] or not report['saveIsolation']['originalSavesUnchanged']:
                report['status'] = 'failed_cleanup_or_verification'
            try:
                write()
            finally:
                u.unregister_slate_post_tick_callback(handle)
                u.SystemLibrary.quit_editor()
            return
        if now - state['start'] > 240:
            finish('failed_watchdog')
            return
        if not world:
            return
        if state['phase'] == 'world':
            controller = u.GameplayStatics.get_player_controller(world, 0)
            if controller is None: return
            if not state.get('resumed'):
                controller.resume_walkthrough()
                state['resumed'] = True
                return
            cinematic = u.MikdashCinematics.get(world)
            if cinematic and cinematic.is_playing(): cinematic.skip_intro()
            assert not u.GameplayStatics.is_game_paused(world), 'Walkthrough still paused'
            state['phase'] = 'warm'
            state['at'] = now
            state['gameAt'] = u.GameplayStatics.get_time_seconds(world)
            return
        # Give BeginPlay, the intro and streaming a few seconds of real game time.
        if u.GameplayStatics.get_time_seconds(world) - state['gameAt'] < 6.0:
            return
        if not state['done']:
            state['done'] = True
            dump_world(world)
            write()
            finish('measured_pie_diagnostic')
    except Exception:  # noqa: BLE001
        report['errors'].append(traceback.format_exc())
        if state['stopping']:
            report['status'] = 'failed_cleanup_exception'
            try:
                write()
            finally:
                u.unregister_slate_post_tick_callback(handle)
                u.SystemLibrary.quit_editor()
        else:
            finish('failed_exception')


handle = None
try:
    settings.set_editor_property('GameGetsMouseControl', False)
    u.SystemLibrary.execute_console_command(ed.get_editor_world(), 'Slate.bAllowThrottling 0')
    write()
    handle = u.register_slate_post_tick_callback(tick)
    levels.editor_request_begin_play()
except Exception as exc:  # noqa: BLE001
    report['status'] = 'failed_setup'
    report['errors'].append(repr(exc))
    if handle is not None:
        try:
            u.unregister_slate_post_tick_callback(handle)
        except Exception as cleanup:  # noqa: BLE001
            report['errors'].append('Callback cleanup: ' + repr(cleanup))
    for restore in (lambda: levels.editor_request_end_play(),
                    lambda: settings.set_editor_property('GameGetsMouseControl', old_mouse),
                    lambda: u.SystemLibrary.execute_console_command(ed.get_editor_world(), 'Slate.bAllowThrottling ' + str(old_throttle))):
        try:
            restore()
        except Exception as cleanup:  # noqa: BLE001
            report['errors'].append('Setup cleanup: ' + repr(cleanup))
    report['mapBytesUnchanged'] = sha(map_file) == report['mapShaBefore']
    try:
        write()
    finally:
        u.SystemLibrary.quit_editor()
    raise

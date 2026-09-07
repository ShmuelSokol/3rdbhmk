"""Read-only map review: prepare(), view(name), allow frames, capture(name), restore()."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue

ROOT = Path(ue.Paths.project_dir())
SPEC = ROOT / 'SourceAssets/visual-review/jerusalem-context-capture-spec.json'
_state = None


def _xyz(v):
    return [v.x, v.y, v.z]


def _rotation(camera, target):
    d = [target[i] - camera[i] for i in range(3)]
    return ue.Rotator(pitch=math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))),
                      yaw=math.degrees(math.atan2(d[1], d[0])), roll=0)


def prepare():
    global _state
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    if world.get_outermost().get_name() != '/Game/MikdashV3/Maps/Courtyard':
        raise RuntimeError('Load Courtyard first; this script does not load or save maps')
    manifest = json.loads((ROOT / 'SourceAssets/architecture-manifest.json').read_text())
    bounds = manifest['expectedBoundsUnrealCm']
    lo, hi = bounds['min'], bounds['max']
    center = [(a + b) / 2 for a, b in zip(lo, hi)]
    span = max(hi[0] - lo[0], hi[1] - lo[1])
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
    candidates = []
    for actor in actors:
        comp = actor.get_component_by_class(ue.StaticMeshComponent)
        mesh = comp.get_editor_property('static_mesh') if comp else None
        if not mesh or '/JerusalemContext/Streets/' not in mesh.get_path_name() or 'StonePaths' not in mesh.get_name():
            continue
        origin, extent = actor.get_actor_bounds(False)
        # Eastern context, outside measured architecture footprint; rank nearby
        # source paths, then validate actual triangle contact, not AABB top.
        if origin.x - extent.x > hi[0]:
            candidates.append(((origin.x-hi[0])**2 + origin.y**2, actor, origin, extent))
    candidates.sort(key=lambda item: item[0])
    chosen = None
    for _, actor, origin, extent in candidates[:30]:
        hit = ue.SystemLibrary.line_trace_single_by_profile(
            world_context_object=world,
            start=ue.Vector(origin.x, origin.y, origin.z+extent.z+1000),
            end=ue.Vector(origin.x, origin.y, origin.z-extent.z-1000),
            profile_name='Pawn', trace_complex=True,
            actors_to_ignore=[a for a in actors if a != actor],
            draw_debug_type=ue.DrawDebugTrace.NONE, ignore_self=False)
        if hit:
            floor = hit.get_editor_property('impact_point')
            chosen = (actor, floor, extent)
            break
    views = {'overall': dict(camera=[hi[0]+span*1.5, hi[1]+span, hi[2]+span*1.5], target=center)}
    if chosen is not None:
        actor, floor, extent = chosen
        eye = [floor.x, floor.y, floor.z+170.0]
        street_target = [eye[0], eye[1]+1000.0, eye[2]] if extent.y >= extent.x else [eye[0]+1000.0, eye[1], eye[2]]
        views['arrival'] = dict(camera=eye, target=[center[0], center[1], floor.z+170.0])
        views['street'] = dict(camera=eye, target=street_target)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    report = json.loads(SPEC.read_text())
    report['execution'] = dict(started_utc=stamp, architecture_bounds_cm=bounds,
        selected_path=actor.get_actor_label() if chosen else None, measured_path_contact_cm=_xyz(floor) if chosen else None, ground_views_status='available' if chosen else 'no_verified_path_contact',
        views=views, capture_requests=[], visual_acceptance=False)
    map_file = ROOT / 'Content/MikdashV3/Maps/Courtyard.umap'
    _state = dict(editor=editor, world=world, camera=editor.get_level_viewport_camera_info(),
                  report=report, views=views, stamp=stamp, map_file=map_file,
                  map_sha=hashlib.sha256(map_file.read_bytes()).hexdigest())
    SPEC.write_text(json.dumps(report, indent=2)+'\n')
    return views


def view(name):
    if not _state:
        raise RuntimeError('Call prepare first')
    v = _state['views'][name]
    _state['editor'].set_level_viewport_camera_info(ue.Vector(*v['camera']), _rotation(v['camera'], v['target']))
    _state['current_view'] = name
    return v


def capture(name):
    if not _state or _state.get('current_view') != name:
        raise RuntimeError('Call view(name), then allow editor frames before capture')
    destination = ROOT / 'Saved/Screenshots/ContextReview' / (_state['stamp']+'-'+name+'.png')
    destination.parent.mkdir(parents=True, exist_ok=True)
    ue.SystemLibrary.execute_console_command(_state['world'], 'HighResShot 1280x720 filename="'+str(destination)+'"')
    _state['report']['execution']['capture_requests'].append(dict(view=name, file=str(destination), status='requested_not_verified'))
    SPEC.write_text(json.dumps(_state['report'], indent=2)+'\n')
    return str(destination)


def restore():
    if _state:
        _state['editor'].set_level_viewport_camera_info(*_state['camera'])
        unchanged = hashlib.sha256(_state['map_file'].read_bytes()).hexdigest() == _state['map_sha']
        _state['report']['execution']['map_file_unchanged'] = unchanged
        SPEC.write_text(json.dumps(_state['report'], indent=2)+'\n')
        if not unchanged:
            raise RuntimeError('Map file changed during review')

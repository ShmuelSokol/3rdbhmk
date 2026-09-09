"""Read-only A/B capture of CityDetailV1: the same frame with the roofscape hidden and shown.

Real RHI, editor viewport (no PIE, no pawn, no save slots), NO map writes. For each camera the
script shoots the frame twice - once with every RELEASE_CityDetail_* actor temporarily hidden
in the editor, once with them shown - so the pair differs by exactly this job's work and by
nothing else: same sun, same clouds, same exposure, same second.

Launch (one process; never while another native job runs; the map is the first argument):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      /Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough
      -ExecCmds="py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/capture_city_detail.py"
      -unattended -NoSplash
      -abslog=C:\\Mikdash\\Working-5.8\\CityDetail-Capture-01.log

Writes PNGs and a receipt under SourceAssets/context-review/CityDetailV1/capture/ and quits.

WHY THE EDITOR VIEWPORT AND NOT PIE
-----------------------------------
perf_probe.py records that under -unattended the HighResShot console command captures the
EDITOR viewport rather than the PIE pawn camera, which is what made its before/after frames
useless. This script wants the editor viewport, aims it explicitly with
UnrealEditorSubsystem.set_level_viewport_camera_info, and holds a fixed number of frames
before every shot so Lumen, TSR and streaming have settled.

WHAT IT DOES NOT ESTABLISH
--------------------------
Nothing here is a frame-time measurement, a walkable check or a cook. Hidden-in-editor is not
the same code path as the precinct's run-time SetActorHiddenInGame, so the "before" frame is a
faithful picture of the geometry that was there before this job, not a proof about the
precinct system.
"""
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT_DIR = ROOT / 'SourceAssets/context-review/CityDetailV1/capture'
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
RECEIPT = OUT_DIR / ('capture-city-detail-%s.json' % STAMP)
PREFIX = OUT_DIR / ('city-detail-%s' % STAMP)
LABEL_PREFIX = 'RELEASE_CityDetail'
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'
SETTLE_FRAMES = 45
SHOT_TIMEOUT_S = 90.0
RUN_TIMEOUT_S = 1500.0

# x, y, height above the traced ground, yaw, pitch, fov, note.
# The Ottoman wall ring spans UE x -97,215..15,073 and y -63,733..57,733, centre
# (-41,071, -3,000); the Mikdash is at the origin. Aim points were computed from that ring
# and from the CityDetailV1 plan (the densest dome cluster, and the souq arch with the most
# neighbouring fittings).
CAMERAS = [
    ('oldcity_air', 5000.0, 20000.0, 22000.0, 206.5, -24.0, 75.0,
     'high oblique from the east-south-east over the whole walled city'),
    ('oldcity_low', -14000.0, -3000.0, 7000.0, 180.0, -11.0, 70.0,
     'low over the roofs on the ring centre line, looking west'),
    ('quarters', -30000.0, -2000.0, 5000.0, 209.0, -9.0, 70.0,
     'toward the densest dome cluster in the plan, about (-45000, -10000)'),
    ('mount_west', -3000.0, 0.0, 3500.0, 180.0, -5.0, 80.0,
     'the visitor view: from the Mount looking west across the Old City'),
    ('souq', -47126.0, 35147.0, 170.0, 92.2, -2.0, 80.0,
     'street level 15 m short of the plan arch at (-47184, 36646), looking along the alley'),
]

report = {
    'status': 'started',
    'stamp': STAMP,
    'map': None,
    'mapShaBefore': None,
    'cameras': [],
    'shots': [],
    'detailActors': [],
    'errors': [],
    'limitations': [
        'Editor viewport frames, not PIE. No frame time, no walkable check, no cook.',
        'The before frame hides the CityDetailV1 actors with set_is_temporarily_hidden_in_editor; '
        'that is an editor flag, not the precinct system\'s run-time SetActorHiddenInGame.',
        'No map, asset or setting is written. The map SHA-256 is recorded before and after.',
    ],
}
state = {'phase': 'warm', 'index': 0, 'variant': 0, 'frames': 0, 'shot': None,
         'start': time.monotonic(), 'stopping': False, 'busy': False}

editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
actor_system = u.get_editor_subsystem(u.EditorActorSubsystem)


def sha(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def disk_map(asset):
    return ROOT / 'Content' / (asset[len('/Game/'):] + '.umap')


def ground_z(world, x, y):
    """Ground under an XY, or None.

    HitResult does not expose 'impact_point' through get_editor_property in UE 5.8 (that is
    how the first run of this script failed); to_dict() is the accessor that works, and it is
    the one diagnose_enclosure_runtime.py uses.
    """
    result = u.SystemLibrary.line_trace_single(
        world, u.Vector(x, y, 60000.0), u.Vector(x, y, -30000.0),
        u.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], u.DrawDebugTrace.NONE, True)
    if isinstance(result, tuple):
        result = result[-1]
    if result is None:
        return None
    fields = {str(key).lower().replace('_', ''): value for key, value in result.to_dict().items()}
    if not fields.get('blockinghit', True):
        return None
    point = fields.get('impactpoint') or fields.get('location')
    return float(point.z) if point is not None else None


def detail_actors():
    return [actor for actor in actor_system.get_all_level_actors()
            if actor.get_actor_label().startswith(LABEL_PREFIX)]


def set_detail_hidden(actors, hidden):
    changed = 0
    for actor in actors:
        try:
            actor.set_is_temporarily_hidden_in_editor(hidden)
            changed += 1
        except Exception as error:                                    # noqa: BLE001
            report['errors'].append('hide %s: %r' % (actor.get_actor_label(), error))
    return changed


def arm(world, camera):
    name, x, y, height, yaw, pitch, fov, note = camera
    z = ground_z(world, x, y)
    location = u.Vector(x, y, (z if z is not None else 0.0) + height)
    editor.set_level_viewport_camera_info(location, u.Rotator(pitch=pitch, yaw=yaw, roll=0.0))
    u.SystemLibrary.execute_console_command(world, 'FOV %.1f' % fov)
    entry = {'name': name, 'xy': [x, y], 'groundZcm': z, 'heightAboveGroundCm': height,
             'locationCm': [location.x, location.y, location.z],
             'yawDeg': yaw, 'pitchDeg': pitch, 'fov': fov, 'note': note}
    if not any(row['name'] == name for row in report['cameras']):
        report['cameras'].append(entry)
    return entry


def request_shot(world, path):
    if path.exists():
        path.unlink()
    u.SystemLibrary.execute_console_command(
        world, 'HighResShot 1920x1080 filename="%s"' % str(path))
    state['shot'] = {'path': path, 'at': time.monotonic()}


def shot_complete(path):
    try:
        data = Path(path).read_bytes()
    except OSError:
        return False
    return len(data) > 1024 and data[:8] == PNG_MAGIC and data[-8:-4] == b'IEND'


def finish(status):
    if state['stopping']:
        return
    report['status'] = status
    state['stopping'] = True
    try:
        set_detail_hidden(state.get('actors') or [], False)
        report['mapShaAfter'] = sha(disk_map(report['map']))
        report['mapBytesUnchanged'] = report['mapShaAfter'] == report['mapShaBefore']
        if not report['mapBytesUnchanged']:
            report['status'] = 'failed_map_changed'
    except Exception as error:                                        # noqa: BLE001
        report['errors'].append('cleanup: %r' % (error,))
    write()
    u.unregister_slate_post_tick_callback(handle)
    u.SystemLibrary.quit_editor()


def tick(delta):
    if state['busy'] or state['stopping']:
        return
    state['busy'] = True
    try:
        if time.monotonic() - state['start'] > RUN_TIMEOUT_S:
            report['errors'].append('watchdog')
            finish('failed_watchdog')
            return
        world = editor.get_editor_world()
        if world is None:
            return
        if state['phase'] == 'warm':
            report['map'] = world.get_outermost().get_name()
            report['mapShaBefore'] = sha(disk_map(report['map']))
            actors = detail_actors()
            state['actors'] = actors
            report['detailActors'] = sorted(actor.get_actor_label() for actor in actors)
            report['detailActorCount'] = len(actors)
            counts = {}
            for actor in actors:
                for component in actor.get_components_by_class(
                        u.HierarchicalInstancedStaticMeshComponent):
                    counts[actor.get_actor_label()] = int(component.get_instance_count())
            report['detailInstanceCounts'] = counts
            report['detailInstanceTotal'] = sum(counts.values())
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            write()
            state['phase'] = 'aim'
            return
        if state['phase'] == 'aim':
            if state['index'] >= len(CAMERAS):
                finish('captured_before_after_pairs')
                return
            camera = CAMERAS[state['index']]
            variant = 'before' if state['variant'] == 0 else 'after'
            set_detail_hidden(state['actors'], state['variant'] == 0)
            state['camera'] = arm(world, camera)
            state['frames'] = 0
            state['variant_name'] = variant
            state['phase'] = 'settle'
            return
        if state['phase'] == 'settle':
            state['frames'] += 1
            if state['frames'] < SETTLE_FRAMES:
                return
            name = '%s__%s__%s.png' % (str(PREFIX), CAMERAS[state['index']][0], state['variant_name'])
            request_shot(world, Path(name))
            state['phase'] = 'shoot'
            return
        if state['phase'] == 'shoot':
            info = state['shot']
            if shot_complete(info['path']):
                report['shots'].append({
                    'camera': CAMERAS[state['index']][0],
                    'variant': state['variant_name'],
                    'file': str(info['path']),
                    'bytes': info['path'].stat().st_size,
                    'sha256': sha(info['path']),
                    'secondsToWrite': round(time.monotonic() - info['at'], 2),
                    'detailHidden': state['variant'] == 0,
                })
                write()
                state['variant'] += 1
                if state['variant'] > 1:
                    state['variant'] = 0
                    state['index'] += 1
                state['phase'] = 'aim'
                return
            if time.monotonic() - info['at'] > SHOT_TIMEOUT_S:
                report['errors'].append('HighResShot timed out for ' + str(info['path']))
                state['variant'] += 1
                if state['variant'] > 1:
                    state['variant'] = 0
                    state['index'] += 1
                state['phase'] = 'aim'
            return
    except Exception as error:                                        # noqa: BLE001
        import traceback
        report['errors'].append(traceback.format_exc()[-1500:])
        finish('failed_exception')
    finally:
        state['busy'] = False


handle = u.register_slate_post_tick_callback(tick)

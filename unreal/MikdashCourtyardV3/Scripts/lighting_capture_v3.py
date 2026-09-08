"""Walking-height PIE A/B captures of the main Walkthrough map for the lighting V3 review.

Nothing is persisted: variants are applied INSIDE the PIE world only (dynamic material
instances on the limestone components, the PIE copy of the post-process volume, the PIE sun).
The saved map, the material instances and the user's save files are hashed before and after.

Launch (dedicated real-RHI GUI editor, strictly serial, unique -abslog):
  UnrealEditor.exe <uproject> /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough
      -ExecCmds="py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/lighting_capture_v3.py"
      -unattended -NoSplash -abslog=C:/Mikdash/Working-5.8/Fable-LightingV3-Capture-NN.log
      -LightingV3Tag=<label> [-LightingV3Variants=baseline,A_relief_local_exposure] [-LightingV3Views=v1_...,v3_...]
      -ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=AstraProbe_<STAMP>,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=AstraProbe_<STAMP>_Settings

The save-slot override is REQUIRED (the runtime autosaves on quit; normal visitor slots must
never be written by a probe). Output: SourceAssets/visual-review/lighting-v3-<stamp>-<tag>__<variant>__<view>.png
and SourceAssets/lighting-review/lighting-v3-capture-<stamp>.json (rewritten after every event).
Pattern: release_frontend_flight_probe.py (PIE lifecycle, HighResShot) + release_capture_views.py
(loading barrier, warmup, PNG sampling). The script quits the editor itself.
"""
import hashlib
import json
import math
import os
import re
import struct
import sys
import time
import traceback
import zlib
from datetime import datetime, timezone
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'Scripts/release_lighting_v3.spec.json').read_text(encoding='utf-8-sig'))
MAP = SPEC['targetMap']
MAP_FILE = ROOT / SPEC['targetMapFile']
CAP = SPEC['capture']
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
CMD = u.SystemLibrary.get_command_line()


def switch(name, default=None):
    m = re.search(r'-' + name + r'=([^\s"]+)', CMD)
    return m.group(1) if m else default


TAG = re.sub(r'[^A-Za-z0-9_-]', '', switch('LightingV3Tag', 'review'))
VARIANTS = [v for v in switch('LightingV3Variants', ','.join(SPEC['variants'])).split(',') if v]
VIEW_FILTER = switch('LightingV3Views')
VIEWS = [v for v in CAP['views'] if not VIEW_FILTER or v['id'] in VIEW_FILTER.split(',')]
OUT_DIR = ROOT / SPEC['captureFolder']
RECEIPT = ROOT / SPEC['receiptFolder'] / ('lighting-v3-capture-' + STAMP + '.json')
INSTANCE_FOLDER = SPEC['instanceFolder']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def xyz(v):
    return [v.x, v.y, v.z]


def look_at(position, target):
    dx, dy, dz = [target[i] - position[i] for i in range(3)]
    return (math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx)))


# ----------------------------------------------------------------------------- PNG sampling
def png_metrics(data, grid=(96, 54), max_seconds=25.0):
    """Decode an 8-bit RGB/RGBA PNG (pure Python) and sample a luma grid; returns review metrics."""
    started = time.monotonic()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return {'skipped': 'not_png'}
    pos, width, height, depth, color, interlace, idat = 8, None, None, None, None, None, []
    while pos + 8 <= len(data):
        length, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b'IHDR':
            width, height, depth, color, _, _, interlace = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
        pos += 12 + length
    if depth != 8 or color not in (2, 6) or interlace != 0:
        return {'skipped': 'unsupported_png_layout', 'width': width, 'height': height}
    channels = 3 if color == 2 else 4
    stride = width * channels
    raw = zlib.decompress(b''.join(idat))
    prev = bytearray(stride)
    wanted_rows = sorted(set(int((j + 0.5) * height / grid[1]) for j in range(grid[1])))
    wanted_cols = [int((i + 0.5) * width / grid[0]) for i in range(grid[0])]
    samples = []
    offset = 0
    for y in range(height):
        if time.monotonic() - started > max_seconds:
            return {'skipped': 'decode_time_budget_exceeded', 'rowsDecoded': y}
        filter_type = raw[offset]
        line = bytearray(raw[offset + 1:offset + 1 + stride])
        offset += 1 + stride
        if filter_type == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif filter_type == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif filter_type == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 255
        elif filter_type != 0:
            return {'skipped': 'unknown_png_filter', 'filter': filter_type}
        if y in wanted_rows:
            row = []
            for x in wanted_cols:
                i = x * channels
                row.append(0.299 * line[i] + 0.587 * line[i + 1] + 0.114 * line[i + 2])
            samples.append(row)
        prev = line
    flat = [s for row in samples for s in row]
    n = len(flat)
    mean = sum(flat) / n
    stdev = math.sqrt(sum((s - mean) ** 2 for s in flat) / n)
    # local contrast: mean absolute difference between horizontal/vertical grid neighbours
    diffs = []
    for j, row in enumerate(samples):
        for i, s in enumerate(row):
            if i + 1 < len(row):
                diffs.append(abs(s - row[i + 1]))
            if j + 1 < len(samples):
                diffs.append(abs(s - samples[j + 1][i]))
    third = len(samples) // 3
    bands = [sum(sum(r) for r in samples[k * third:(k + 1) * third]) / max(1, third * len(samples[0])) for k in range(3)]
    return {'width': width, 'height': height, 'gridSamples': n, 'lumaMean': round(mean, 2), 'lumaStdev': round(stdev, 2),
            'lumaMin': round(min(flat), 1), 'lumaMax': round(max(flat), 1),
            'clippedFraction250': round(sum(1 for s in flat if s >= 250) / n, 4),
            'brightFraction235': round(sum(1 for s in flat if s >= 235) / n, 4),
            'darkFraction20': round(sum(1 for s in flat if s <= 20) / n, 4),
            'localContrastMeanAbsDiff': round(sum(diffs) / len(diffs), 3),
            'bandMeansTopMidBottom': [round(b, 1) for b in bands],
            'decodeSeconds': round(time.monotonic() - started, 2)}


# ----------------------------------------------------------------------------- receipt
report = {'status': 'starting', 'stamp': STAMP, 'tag': TAG, 'map': MAP, 'mapShaBefore': sha(MAP_FILE),
          'specSha256': sha(ROOT / 'Scripts/release_lighting_v3.spec.json'),
          'variantsRequested': VARIANTS, 'viewsRequested': [v['id'] for v in VIEWS],
          'instanceShaBefore': {n: sha(ROOT / 'Content' / (INSTANCE_FOLDER[6:] + n + '.uasset')) for n in SPEC['editableInstances']},
          'errors': [], 'failures': [], 'events': [], 'captures': [], 'liveLighting': {},
          'scope': 'Actual PIE walking-height stills; variants applied in the PIE world only; nothing saved. Visual acceptance is a separate human decision.'}
state = dict(start=time.monotonic(), phase='world', at=time.monotonic(), stopping=False, variant_index=0, view_index=-1,
             ticks=0, camera=None, current=None, shot_path=None, shot_started=None, barrier_done_for_variant=None)
ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse = settings.get_editor_property('GameGetsMouseControl')
old_throttle = u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
save_roots = [ROOT / 'Saved/SaveGames', Path(os.environ.get('LOCALAPPDATA', 'C:/nonexistent')) / 'MikdashCourtyardV3/Saved/SaveGames']


def user_save_hashes():
    return {str(p): sha(p) for folder in save_roots if folder.exists() for p in folder.glob('*.sav') if not p.name.startswith('AstraProbe_')}


original_saves = user_save_hashes()
handle = None


def write():
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')


def event(label, **extra):
    row = {'event': label, 'elapsedSeconds': round(time.monotonic() - state['start'], 2)}
    row.update(extra)
    report['events'].append(row)
    write()


def failure(where, message):
    report['failures'].append({'where': where, 'error': str(message), 'elapsedSeconds': round(time.monotonic() - state['start'], 2)})
    u.log_warning('LIGHTING_V3_CAPTURE_FAILURE %s: %s' % (where, message))
    write()


def phase(name):
    state.update(phase=name, at=time.monotonic(), ticks=0)


def enc(v):
    if isinstance(v, (bool, int, float, str)) or v is None:
        return v
    if isinstance(v, u.Rotator):
        return [v.pitch, v.yaw, v.roll]
    if isinstance(v, u.Vector):
        return xyz(v)
    if isinstance(v, u.LinearColor):
        return [v.r, v.g, v.b, v.a]
    return str(v)


# ----------------------------------------------------------------------------- live lighting readback
def lighting_snapshot(world):
    snap = {}
    suns = list(u.GameplayStatics.get_all_actors_of_class(world, u.DirectionalLight))
    skies = list(u.GameplayStatics.get_all_actors_of_class(world, u.SkyLight))
    volumes = list(u.GameplayStatics.get_all_actors_of_class(world, u.PostProcessVolume))
    fogs = list(u.GameplayStatics.get_all_actors_of_class(world, u.ExponentialHeightFog))
    snap['counts'] = {'DirectionalLight': len(suns), 'SkyLight': len(skies), 'PostProcessVolume': len(volumes), 'ExponentialHeightFog': len(fogs)}
    if suns:
        c = suns[0].get_component_by_class(u.DirectionalLightComponent)
        snap['sun'] = {'rotation': enc(suns[0].get_actor_rotation()), 'forward': enc(suns[0].get_actor_forward_vector()),
                       'intensity': c.get_editor_property('intensity'), 'temperature': c.get_editor_property('temperature'),
                       'useTemperature': c.get_editor_property('use_temperature')}
    if skies:
        c = skies[0].get_component_by_class(u.SkyLightComponent)
        snap['sky'] = {'intensity': c.get_editor_property('intensity'), 'lowerHemisphereIsBlack': c.get_editor_property('lower_hemisphere_is_black')}
    if fogs:
        c = fogs[0].get_component_by_class(u.ExponentialHeightFogComponent)
        snap['fog'] = {k: c.get_editor_property(k) for k in ('fog_density', 'fog_height_falloff', 'start_distance', 'enable_volumetric_fog')}
    if volumes:
        s = volumes[0].get_editor_property('settings')
        keys = ['auto_exposure_method', 'auto_exposure_min_brightness', 'auto_exposure_max_brightness', 'auto_exposure_bias',
                'auto_exposure_low_percent', 'auto_exposure_high_percent', 'film_slope', 'film_toe', 'film_shoulder', 'film_white_clip',
                'local_exposure_method', 'local_exposure_highlight_contrast_scale', 'local_exposure_shadow_contrast_scale',
                'local_exposure_detail_strength', 'override_local_exposure_highlight_contrast_scale', 'override_local_exposure_shadow_contrast_scale']
        snap['postProcess'] = {k: enc(s.get_editor_property(k)) for k in keys}
        snap['postProcess']['priority'] = volumes[0].get_editor_property('priority')
        snap['postProcess']['unbound'] = volumes[0].get_editor_property('unbound')
    tod = u.load_class(None, '/Script/MikdashRuntime.MikdashTimeOfDay')
    snap['timeOfDayActors'] = len(list(u.GameplayStatics.get_all_actors_of_class(world, tod))) if tod else 'class_unavailable'
    return snap


# ----------------------------------------------------------------------------- traces
def trace_ground(world, x, y, z_top, z_bottom, ignore=()):
    hit = u.SystemLibrary.line_trace_single_by_profile(
        world_context_object=world, start=u.Vector(x, y, z_top), end=u.Vector(x, y, z_bottom), profile_name='Pawn',
        trace_complex=True, actors_to_ignore=list(ignore), draw_debug_type=u.DrawDebugTrace.NONE, ignore_self=False)
    if not hit:
        return None
    data = {str(k).lower(): v for k, v in hit.to_dict().items()}
    point = data.get('impact_point') or data.get('impactpoint') or data.get('location')
    actor = data.get('hit_actor') or data.get('actor') or data.get('hitactor')
    label = None
    try:
        label = actor.get_actor_label() if actor else None
    except Exception:
        label = str(actor)
    return {'point': xyz(point), 'actor': label}


def sightline_blocker(world, start, end, ignore=()):
    hit = u.SystemLibrary.line_trace_single_by_profile(
        world_context_object=world, start=u.Vector(*start), end=u.Vector(*end), profile_name='Pawn',
        trace_complex=True, actors_to_ignore=list(ignore), draw_debug_type=u.DrawDebugTrace.NONE, ignore_self=False)
    if not hit:
        return None
    data = {str(k).lower(): v for k, v in hit.to_dict().items()}
    point = data.get('impact_point') or data.get('impactpoint') or data.get('location')
    actor = data.get('hit_actor') or data.get('actor') or data.get('hitactor')
    try:
        label = actor.get_actor_label() if actor else None
    except Exception:
        label = str(actor)
    return {'point': xyz(point), 'actor': label, 'distanceCm': round(math.dist(start, xyz(point)), 1)}


def plan_views(world):
    eye = CAP['eyeHeightCm']
    planned = []
    overlay_tag = CAP['kotel']['overlayTag']
    ignore = [a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor) if overlay_tag in [str(t) for t in a.tags]]
    for v in VIEWS:
        row = {'id': v['id'], 'basis': v.get('basis'), 'fov': v.get('fov', CAP['fovDegrees'])}
        try:
            if 'fixedZ' in v:
                row.update(position=[v['xy'][0], v['xy'][1], v['fixedZ']], pitch=v['pitch'], yaw=v['yaw'], groundTrace='fixed camera (anchor)')
            elif v.get('kotelFace'):
                k = CAP['kotel']
                mid = [(k['faceA'][0] + k['faceB'][0]) / 2.0, (k['faceA'][1] + k['faceB'][1]) / 2.0]
                n = k['faceNormal']
                xy = [mid[0] + n[0] * v['distanceCm'], mid[1] + n[1] * v['distanceCm']]
                ground = trace_ground(world, xy[0], xy[1], v['traceTopZ'], v['traceBottomZ'], ignore)
                floor_z = ground['point'][2] if ground else v['fallbackFloorZ']
                position = [xy[0], xy[1], floor_z + eye]
                target = [mid[0] + n[0] * 5.0, mid[1] + n[1] * 5.0, position[2] + v['targetRiseCm']]
                pitch, yaw = look_at(position, target)
                row.update(position=position, pitch=pitch, yaw=yaw, target=target, groundTrace=ground)
                if ground is None:
                    failure(v['id'], 'no plaza ground hit; fallback Z used')
            elif 'candidates' in v:
                chosen = None
                probes = []
                for cand in v['candidates']:
                    ground = trace_ground(world, cand['xy'][0], cand['xy'][1], v['traceTopZ'], v['traceBottomZ'])
                    floor_z = ground['point'][2] if ground else v['fallbackFloorZ']
                    position = [cand['xy'][0], cand['xy'][1], floor_z + eye]
                    blocker = sightline_blocker(world, position, cand['sightTo'])
                    probes.append({'xy': cand['xy'], 'groundTrace': ground, 'blocker': blocker})
                    if chosen is None and ground is not None and (blocker is None or blocker['distanceCm'] > 4000.0):
                        chosen = (cand, position)
                if chosen is None:
                    cand = v['candidates'][0]
                    ground = probes[0]['groundTrace']
                    floor_z = ground['point'][2] if ground else v['fallbackFloorZ']
                    chosen = (cand, [cand['xy'][0], cand['xy'][1], floor_z + eye])
                    failure(v['id'], 'no candidate with a clear city sightline; first candidate captured anyway')
                cand, position = chosen
                row.update(position=position, pitch=v['pitch'], yaw=cand['yaw'], candidateProbes=probes, chosenXY=cand['xy'])
            else:
                ground = trace_ground(world, v['xy'][0], v['xy'][1], v['traceTopZ'], v['traceBottomZ'])
                floor_z = ground['point'][2] if ground else v['fallbackFloorZ']
                row.update(position=[v['xy'][0], v['xy'][1], floor_z + eye], pitch=v['pitch'], yaw=v['yaw'], groundTrace=ground)
                if ground is None:
                    failure(v['id'], 'no Pawn-profile floor hit; manifest floor used')
        except Exception as exc:
            failure(v['id'], 'plan: ' + repr(exc))
            row['skipped'] = True
        planned.append(row)
    return planned


# ----------------------------------------------------------------------------- variants (PIE world only)
def resolve_variant(name):
    v = dict(SPEC['variants'][name])
    if 'inherits' in v:
        base = resolve_variant(v['inherits'])
        merged = dict(base)
        merged.update({k: val for k, val in v.items() if k != 'inherits'})
        return merged
    return v


def spec_value(raw):
    if isinstance(raw, dict) and '$enum' in raw:
        enum_name, member = raw['$enum'].split('.')
        return getattr(getattr(u, enum_name), member)
    return raw


def apply_variant(world, name):
    v = resolve_variant(name)
    applied = {'variant': name}
    if 'instances' in v:
        counts = {}
        for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
            for comp in actor.get_components_by_class(u.StaticMeshComponent):
                for i in range(comp.get_num_materials()):
                    m = comp.get_material(i)
                    if m is None:
                        continue
                    base = m.get_path_name().split('.')[0]
                    short = base.rsplit('/', 1)[-1]
                    if base.startswith(INSTANCE_FOLDER) and short in v['instances']:
                        mid = comp.create_dynamic_material_instance(i, m)
                        for pname, pval in v['instances'][short].get('scalars', {}).items():
                            mid.set_scalar_parameter_value(pname, float(pval))
                        if 'tint' in v['instances'][short]:
                            mid.set_vector_parameter_value('Tint', u.LinearColor(*v['instances'][short]['tint']))
                        counts[short] = counts.get(short, 0) + 1
        applied['dynamicInstancesCreated'] = counts
        applied['instanceParameters'] = v['instances']
    if 'postProcess' in v:
        volumes = list(u.GameplayStatics.get_all_actors_of_class(world, u.PostProcessVolume))
        assert len(volumes) == 1, 'Need exactly one PIE post-process volume'
        s = volumes[0].get_editor_property('settings')
        for k, raw in v['postProcess'].items():
            s.set_editor_property(k, spec_value(raw))
            s.set_editor_property('override_' + k, True)
        volumes[0].set_editor_property('settings', s)
        s2 = volumes[0].get_editor_property('settings')
        applied['postProcessReadback'] = {k: enc(s2.get_editor_property(k)) for k in v['postProcess']}
    if 'sun' in v:
        suns = list(u.GameplayStatics.get_all_actors_of_class(world, u.DirectionalLight))
        assert len(suns) == 1, 'Need exactly one PIE sun'
        p, y, r = v['sun']['rotatorPitchYawRoll']
        suns[0].set_actor_rotation(u.Rotator(pitch=p, yaw=y, roll=r), True)
        applied['sunRotationReadback'] = enc(suns[0].get_actor_rotation())
    return applied


# ----------------------------------------------------------------------------- lifecycle
def finish(status):
    if state['stopping']:
        return
    report['status'] = status
    state['stopping'] = True
    phase('stopping')
    try:
        levels.editor_request_end_play()
    except Exception as exc:
        report['errors'].append('end_play: ' + repr(exc))
    write()


def shutdown():
    for restore in (lambda: settings.set_editor_property('GameGetsMouseControl', old_mouse),
                    lambda: u.SystemLibrary.execute_console_command(ed.get_editor_world(), 'Slate.bAllowThrottling ' + str(old_throttle))):
        try:
            restore()
        except Exception as exc:
            report['errors'].append('Cleanup: ' + repr(exc))
    report['throttleRestored'] = u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling') == old_throttle
    report['mapBytesUnchanged'] = sha(MAP_FILE) == report['mapShaBefore']
    report['instanceBytesUnchanged'] = all(sha(ROOT / 'Content' / (INSTANCE_FOLDER[6:] + n + '.uasset')) == h for n, h in report['instanceShaBefore'].items())
    report['originalSavesUnchanged'] = user_save_hashes() == original_saves
    if not report['mapBytesUnchanged'] or not report['instanceBytesUnchanged'] or not report['originalSavesUnchanged']:
        report['errors'].append('Persistence check failed: map/instances/user saves changed during capture')
    if report['errors']:
        report['status'] = 'failed_' + report['status'] if not report['status'].startswith('failed') else report['status']
    write()
    u.log('LIGHTING_V3_CAPTURE_FINISHED %s status=%s' % (RECEIPT, report['status']))
    try:
        if handle is not None:
            u.unregister_slate_post_tick_callback(handle)
    finally:
        u.SystemLibrary.quit_editor()


def next_view(world):
    state['view_index'] += 1
    if state['view_index'] >= len(state['views']):
        state['variant_index'] += 1
        state['view_index'] = -1
        if state['variant_index'] >= len(VARIANTS):
            finish('captured_pie_ab_requires_visual_review')
            return
        name = VARIANTS[state['variant_index']]
        try:
            report.setdefault('variantsApplied', []).append(apply_variant(world, name))
            report['liveLighting'][name] = lighting_snapshot(world)
            event('variant_applied_' + name)
        except Exception as exc:
            failure('apply_variant ' + name, repr(exc))
            report.setdefault('variantsApplied', []).append({'variant': name, 'error': repr(exc)})
        state['barrier_done_for_variant'] = None
        next_view(world)
        return
    view = state['views'][state['view_index']]
    if view.get('skipped'):
        next_view(world)
        return
    state['current'] = view
    arm_view(world, view)


def arm_view(world, view):
    c = u.GameplayStatics.get_player_controller(world, 0)
    camera = state['camera']
    comp = camera.get_component_by_class(u.CameraComponent)
    comp.set_field_of_view(float(view['fov']))
    camera.set_actor_location(u.Vector(*view['position']), False, True)
    camera.set_actor_rotation(u.Rotator(pitch=view['pitch'], yaw=view['yaw'], roll=0.0), True)
    c.set_view_target_with_blend(camera, 0.0)
    variant = VARIANTS[state['variant_index']]
    if state['barrier_done_for_variant'] != variant:
        started = time.monotonic()
        u.AutomationLibrary.finish_loading_before_screenshot()
        state['barrier_done_for_variant'] = variant
        event('loading_barrier', variant=variant, view=view['id'], seconds=round(time.monotonic() - started, 2))
    phase('warming')


def request_shot(world, view):
    c = u.GameplayStatics.get_player_controller(world, 0)
    manager = u.GameplayStatics.get_player_camera_manager(world, 0)
    cam_loc = manager.get_camera_location()
    drift = (cam_loc - u.Vector(*view['position'])).length()
    if drift > 1.0:
        failure(view['id'], 'PIE camera is %.1f cm from the planned position (view target changed?)' % drift)
    variant = VARIANTS[state['variant_index']]
    path = OUT_DIR / ('%s%s-%s__%s__%s.png' % (SPEC['capturePrefix'], STAMP, TAG, variant, view['id']))
    assert not path.exists(), 'Output exists: ' + str(path)
    state['shot_path'] = path
    state['shot_started'] = time.monotonic()
    state['shot_record'] = {'variant': variant, 'view': view['id'], 'file': str(path), 'camera': {'position': view['position'], 'pitch': view['pitch'], 'yaw': view['yaw'], 'fov': view['fov']},
                            'liveCameraCm': xyz(cam_loc), 'warmupSeconds': round(time.monotonic() - state['at'], 2), 'warmupTicks': state['ticks'],
                            'gameSeconds': u.GameplayStatics.get_time_seconds(world)}
    res = CAP['resolution']
    u.SystemLibrary.execute_console_command(world, 'HighResShot %dx%d filename="%s"' % (res[0], res[1], str(path)), c)
    phase('shot_wait')


def tick(dt):
    global handle
    if state.get('busy'):        # traces / loading barrier / screenshots pump Slate: block re-entry
        return
    state['busy'] = True
    try:
        now = time.monotonic()
        world = ed.get_game_world()
        if state['stopping']:
            if world and now - state['at'] < 15:
                return
            if world:
                report['errors'].append('PIE teardown timeout')
            report['pieEnded'] = world is None
            shutdown()
            return
        if now - state['start'] > CAP['watchdogSeconds']:
            finish('failed_watchdog')
            return
        if not world:
            return
        c = u.GameplayStatics.get_player_controller(world, 0)
        if not c:
            return
        state['ticks'] += 1
        elapsed = now - state['at']
        if state['phase'] == 'world':
            front = u.MikdashFrontEnd.get(world)
            if front is None or not front.is_front_end_visible():
                if elapsed > 60.0 and not u.GameplayStatics.is_game_paused(world):
                    report['frontEndNeverVisible'] = True
                    phase('setup')
                return
            state['front'] = front
            c.resume_walkthrough()
            phase('intro')
            return
        if state['phase'] == 'intro':
            cinematic = u.MikdashCinematics.get(world)
            if cinematic and cinematic.is_playing():
                if elapsed < 2.0:
                    return
                cinematic.skip_intro()
                report['introSkipped'] = True
            elif elapsed < 3.0:
                return
            if c.is_walkthrough_menu_open():
                c.resume_walkthrough()
                return
            if u.GameplayStatics.is_game_paused(world):
                return
            phase('setup')
            return
        if state['phase'] == 'setup':
            if elapsed < 1.0:
                return
            report['liveLighting']['pie_start'] = lighting_snapshot(world)
            cameras = list(u.GameplayStatics.get_all_actors_of_class(world, u.CameraActor))
            assert cameras, 'No CameraActor in the PIE world to reuse'
            camera = cameras[0]
            comp = camera.get_component_by_class(u.CameraComponent)
            comp.set_editor_property('post_process_blend_weight', 0.0)   # walking exposure, not the legacy fixed EV
            assert comp.get_editor_property('post_process_blend_weight') == 0.0
            comp.set_constraint_aspect_ratio(False)
            state['camera'] = camera
            report['cameraActor'] = {'name': camera.get_name(), 'label': camera.get_actor_label(), 'postProcessBlendWeight': 0.0}
            pawn = u.GameplayStatics.get_player_pawn(world, 0)
            if pawn:
                pawn.set_actor_hidden_in_game(True)
                report['pawnHidden'] = True
                report['pawnLocation'] = xyz(pawn.get_actor_location())
            state['views'] = plan_views(world)
            report['views'] = state['views']
            state['variant_index'] = 0
            first = VARIANTS[0]
            if first != 'baseline':
                report.setdefault('variantsApplied', []).append(apply_variant(world, first))
            report['liveLighting'][first] = lighting_snapshot(world)
            event('setup_complete', variant=first)
            next_view(world)
            return
        if state['phase'] == 'warming':
            if elapsed >= CAP['warmupSeconds'] and state['ticks'] >= CAP['minimumSlateTicks']:
                request_shot(world, state['current'])
            return
        if state['phase'] == 'shot_wait':
            path = state['shot_path']
            if not path.exists():
                if now - state['shot_started'] > CAP['screenshotTimeoutSeconds']:
                    failure(state['current']['id'], 'screenshot did not arrive within %.0f s' % CAP['screenshotTimeoutSeconds'])
                    next_view(world)
                return
            # HighResShot writes asynchronously; wait until the file is a complete PNG (IEND present)
            data = path.read_bytes()
            if len(data) < 16 or data[:8] != b'\x89PNG\r\n\x1a\n' or b'IEND' not in data[-64:]:
                if now - state['shot_started'] > CAP['screenshotTimeoutSeconds']:
                    failure(state['current']['id'], 'screenshot incomplete after timeout')
                    next_view(world)
                return
            record = dict(state['shot_record'])
            record.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            try:
                record['metrics'] = png_metrics(data)
            except Exception as exc:
                record['metrics'] = {'skipped': 'decode_error ' + repr(exc)}
            report['captures'].append(record)
            event('captured', variant=record['variant'], view=record['view'])
            next_view(world)
            return
    except Exception as exc:
        report['errors'].append(repr(exc) + ' | ' + traceback.format_exc()[-800:])
        if state['stopping']:
            report['status'] = 'failed_cleanup_exception'
            shutdown()
        else:
            finish('failed_exception')
    finally:
        state['busy'] = False


try:
    assert Path(u.Paths.project_dir()).resolve() == ROOT, 'Wrong project'
    assert ed.get_game_world() is None, 'PIE already running'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Dirty map packages'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Dirty content packages'
    assert ed.get_editor_world().get_outermost().get_name() == MAP, 'Main map must be the loaded world'
    assert 'SlotNamePrefix=AstraProbe_' in CMD and 'SaveSlot=AstraProbe_' in CMD, 'Require the isolated save-slot ini overrides'
    for name in VARIANTS:
        assert name in SPEC['variants'], 'Unknown variant ' + name
        resolve_variant(name)
    settings.set_editor_property('GameGetsMouseControl', False)
    u.SystemLibrary.execute_console_command(ed.get_editor_world(), 'Slate.bAllowThrottling 0')
    report['status'] = 'pie_starting'
    write()
    handle = u.register_slate_post_tick_callback(tick)
    levels.editor_request_begin_play()
except Exception as exc:
    report['status'] = 'failed_setup'
    report['errors'].append(repr(exc))
    try:
        write()
    finally:
        for restore in (lambda: settings.set_editor_property('GameGetsMouseControl', old_mouse),
                        lambda: u.SystemLibrary.execute_console_command(ed.get_editor_world(), 'Slate.bAllowThrottling ' + str(old_throttle))):
            try:
                restore()
            except Exception:
                pass
        u.SystemLibrary.quit_editor()
    raise

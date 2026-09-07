"""Bounded PIE ground trace + guarded placement of the TransitV2 bus (13 meshes).

Why this exists: the release placement commandlet (release_place_assets.py) could
not trace the ground (all traces return nothing in -run=pythonscript and in
NullRHI editor worlds), and the handoff candidate at [-23101.76, 36185.43] has
about 28 degrees of road crossfall by offline interpolation. This script uses the
persistent-editor PIE pattern of release_walk_probe.py: a dedicated editor started
ON the combined map with -ExecCmds="py <this file>", a Slate post-tick callback,
editor_request_begin_play, traces in the PIE game world, editor_request_end_play,
and only then (in the EDITOR world) checkpoint -> spawn -> save -> reopen -> read back.

Every number comes from Scripts/release_place_bus.spec.json (offline candidate
search along Batei Mahase, OSM way 496167693; top 3 candidates with numbers).

Invocation (dedicated editor, never the user's GUI editor; serial with other native jobs):

  set MIKDASH_BUS_QUIT_EDITOR=1
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough
      -ExecCmds="py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_place_bus.py"
      -unattended -NoSplash -nullrhi -abslog="C:/Mikdash/Working-5.8/Release-Bus-01.log"

Modes (MIKDASH_BUS_MODE):
  trace_and_place   (default) PIE traces, end play, checkpoint, place, save, reopen, read back.
  trace_only        PIE traces only; writes the pose to the receipt; the map is never dirtied.
  place_from_receipt  No PIE. Reads the pose from an earlier receipt
                    (MIKDASH_BUS_POSE_RECEIPT=<path>, poseStatus must be pose_ok and the map
                    SHA-256 must still match) and places it. Runs synchronously, so it also works
                    as a commandlet: UnrealEditor-Cmd.exe <uproject> -run=pythonscript
                    -script=<this file> -unattended -nullrhi. This is the safe two-step path if
                    saving right after end-play in one process is not trusted.

Other environment switches:
  MIKDASH_BUS_QUIT_EDITOR=1     quit the editor when finished (dedicated editor only; default 0)
  MIKDASH_BUS_CANDIDATE=<n>     only try spec candidate n (1..3); default: try 1, then 2, then 3
  MIKDASH_BUS_POSE=plane|flat   plane (default) = pitch/roll from the wheel plane; flat = level at max wheel Z
  MIKDASH_BUS_LIMIT_SECONDS     hard wall-clock limit, 30..120 (default 120)
  MIKDASH_BUS_ALLOW_LOAD_MAP=1  load the combined map if another clean map is open (default 1)

Guards: exact project directory, exact map, no game world at start, no dirty
packages, no existing RELEASE_Bus_* actors / Release/Bus folder / actors already
using the bus meshes, TransitV2 native-import receipt status, mesh triangle counts
and bounds, protected maps' SHA-256 unchanged after the run. Slate.bAllowThrottling
and GameGetsMouseControl are restored like the walk probe. Receipt:
SourceAssets/arrival-review/TransitV2/native-placement-<UTC stamp>.json, written at
start and after every state change so partial evidence survives failures.

Not a claim of visual acceptance, pawn blocking, boarding, or a source-proven route.
"""
import hashlib
import json
import math
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_place_bus.spec.json'
TARGET_MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
MAP_FILE = ROOT / 'Content' / 'MikdashV3' / 'IntegratedReviewV2' / 'Maps' / 'Walkthrough.umap'
MODES = ('trace_and_place', 'trace_only', 'place_from_receipt')


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so offline_check() runs anywhere.
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec['targetMap'] != TARGET_MAP:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    if (ROOT / spec['targetMapFile']).resolve() != MAP_FILE.resolve():
        raise RuntimeError('Spec target map file differs from script map file')
    return spec


def env_float(name, default, low, high):
    try:
        value = float(os.environ.get(name, default))
    except ValueError:
        value = float(default)
    return min(high, max(low, value))


def local_to_world_xy(xy, yaw_degrees, lx, ly):
    yaw = math.radians(yaw_degrees)
    return [xy[0] + lx * math.cos(yaw) - ly * math.sin(yaw), xy[1] + lx * math.sin(yaw) + ly * math.cos(yaw)]


def rotation_axes(pitch, yaw, roll):
    """UE FRotationMatrix axes (X forward, Y right, Z up) for a rotator in degrees."""
    p, y, r = math.radians(pitch), math.radians(yaw), math.radians(roll)
    cp, sp, cy, sy, cr, sr = math.cos(p), math.sin(p), math.cos(y), math.sin(y), math.cos(r), math.sin(r)
    x_axis = (cp * cy, cp * sy, sp)
    y_axis = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    z_axis = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    return x_axis, y_axis, z_axis


def transform_point(location, rotation, local):
    xa, ya, za = rotation_axes(*rotation)
    return [location[i] + local[0] * xa[i] + local[1] * ya[i] + local[2] * za[i] for i in range(3)]


def rotated_box(local, location, rotation):
    """World AABB of a local AABB under a full pitch/yaw/roll rotation (eight corners)."""
    corners = []
    for x in (local['min'][0], local['max'][0]):
        for y in (local['min'][1], local['max'][1]):
            for z in (local['min'][2], local['max'][2]):
                corners.append(transform_point(location, rotation, (x, y, z)))
    return {'min': [min(c[i] for c in corners) for i in range(3)], 'max': [max(c[i] for c in corners) for i in range(3)]}


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def support_check(wheel_z, probes_spec):
    """Spread / gradient / crossfall from four wheel contact Z values."""
    z = wheel_z
    front = (z['wheel_front_left'] + z['wheel_front_right']) / 2.0
    rear = (z['wheel_rear_left'] + z['wheel_rear_right']) / 2.0
    left = (z['wheel_front_left'] + z['wheel_rear_left']) / 2.0
    right = (z['wheel_front_right'] + z['wheel_rear_right']) / 2.0
    values = [z[k] for k in ('wheel_front_left', 'wheel_front_right', 'wheel_rear_left', 'wheel_rear_right')]
    spread = max(values) - min(values)
    gradient = math.degrees(math.atan(abs(front - rear) / probes_spec['wheelbaseCm']))
    crossfall = math.degrees(math.atan(max(abs(z['wheel_front_left'] - z['wheel_front_right']),
                                           abs(z['wheel_rear_left'] - z['wheel_rear_right'])) / probes_spec['trackCm']))
    a = (front - rear) / probes_spec['wheelbaseCm']
    b = (left - right) / probes_spec['trackCm']
    c = sum(values) / 4.0
    pitch = math.degrees(math.atan(a))
    roll = -math.degrees(math.atan(b * math.cos(math.atan(a))))
    residuals = {k: z[k] - (c + a * lx + b * ly) for k, (lx, ly) in probes_spec['localPointsCm'].items() if k != 'center'}
    failures = []
    if spread > probes_spec['maxWheelSpreadCm']:
        failures.append('spread %.2f > %.1f cm' % (spread, probes_spec['maxWheelSpreadCm']))
    if gradient > probes_spec['maxGradientDegrees']:
        failures.append('gradient %.2f > %.1f deg' % (gradient, probes_spec['maxGradientDegrees']))
    if crossfall > probes_spec['maxCrossfallDegrees']:
        failures.append('crossfall %.2f > %.1f deg' % (crossfall, probes_spec['maxCrossfallDegrees']))
    if abs(pitch) > probes_spec['maxGradientDegrees']:
        failures.append('pitch %.2f exceeds gradient limit' % pitch)
    if abs(roll) > probes_spec['maxCrossfallDegrees']:
        failures.append('roll %.2f exceeds crossfall limit' % roll)
    return {'wheelZ': z, 'spreadCm': spread, 'gradientDegrees': gradient, 'crossfallDegrees': crossfall,
            'planeA': a, 'planeB': b, 'planeC': c, 'pitchDegrees': pitch, 'rollDegrees': roll,
            'planeResidualsCm': residuals, 'maxPlaneResidualCm': max(abs(v) for v in residuals.values()),
            'maxWheelZ': max(values), 'failures': failures, 'passed': not failures}


def build_pose(candidate, check, spec, style):
    """Actor transform shared by the 13 meshes. style 'plane' or 'flat'."""
    tire = float(spec['tireContactLocalZ'])
    if style == 'flat':
        location = [candidate['xy'][0], candidate['xy'][1], check['maxWheelZ'] - tire]
        rotation = [0.0, float(candidate['yaw']), 0.0]
    else:
        location = [candidate['xy'][0], candidate['xy'][1], check['planeC'] - tire]
        rotation = [check['pitchDegrees'], float(candidate['yaw']), check['rollDegrees']]
    wheels = {}
    for name, (lx, ly) in spec['groundProbes']['localPointsCm'].items():
        if name == 'center':
            continue
        world = transform_point(location, rotation, (lx, ly, tire))
        wheels[name] = {'worldContactPointCm': world, 'tracedGroundZ': check['wheelZ'][name],
                        'floatCm': world[2] - check['wheelZ'][name]}
    return {'style': style, 'location': location, 'rotation': rotation, 'scale': list(spec['scale']),
            'rotationOrder': 'unreal.Rotator(pitch, yaw, roll)', 'wheels': wheels,
            'maxWheelFloatCm': max(abs(w['floatCm']) for w in wheels.values())}


def offline_check(spec=None):
    """Engine-free consistency checks; raises on the first failure."""
    spec = spec or load_spec()
    report = {'assetFilesChecked': 0, 'missingFiles': []}
    files = [spec['targetMapFile'], spec['nativeImportReceipt']]
    files += [disk_path(spec['meshFolder'] + m['name']).relative_to(ROOT).as_posix() for m in spec['meshes']]
    for relative in files:
        report['assetFilesChecked'] += 1
        if not (ROOT / relative).exists():
            report['missingFiles'].append(relative)
    if report['missingFiles']:
        raise RuntimeError('Missing files on disk: ' + ', '.join(report['missingFiles']))
    union = {'min': [min(m['localBoundsCm']['min'][i] for m in spec['meshes']) for i in range(3)],
             'max': [max(m['localBoundsCm']['max'][i] for m in spec['meshes']) for i in range(3)]}
    if box_error(union, spec['assemblyLocalBoundsCm']) > 1e-6:
        raise RuntimeError('Bus mesh union differs from assembly bounds')
    if abs(union['min'][2] - spec['tireContactLocalZ']) > 1e-6:
        raise RuntimeError('Tire contact is not at local Z 0')
    if len(spec['meshes']) != 13 or len(spec['stationMeshesOmitted']) != 12:
        raise RuntimeError('Expected 13 bus and 12 station meshes')
    probes = spec['groundProbes']
    if len(spec['candidates']) < 1:
        raise RuntimeError('Spec has no candidates')
    report['candidates'] = []
    for candidate in spec['candidates']:
        # Re-derive the offline numbers from the recorded surface Z so the spec is self-consistent.
        check = support_check(candidate['offlineSurfaceZCm'], probes)
        derived = candidate['offlineDerived']
        for key, want in (('crossfallDegrees', check['crossfallDegrees']), ('gradientDegrees', check['gradientDegrees']),
                          ('spreadCm', check['spreadCm']), ('pitchDegrees', check['pitchDegrees']), ('rollDegrees', check['rollDegrees'])):
            if abs(derived[key] - want) > 0.01:
                raise RuntimeError('Candidate %d %s %.4f disagrees with recorded %.4f' % (candidate['rank'], key, want, derived[key]))
        if not check['passed']:
            raise RuntimeError('Candidate %d fails its own offline support check: %s' % (candidate['rank'], check['failures']))
        for name, (lx, ly) in probes['localPointsCm'].items():
            xy = local_to_world_xy(candidate['xy'], candidate['yaw'], lx, ly)
            if math.dist(xy, candidate['probeXY'][name]) > 0.01:
                raise RuntimeError('Candidate %d probe %s XY differs from recorded' % (candidate['rank'], name))
        for asset in candidate['expectedSupportAssets']:
            if not any(asset.startswith(prefix) for prefix in probes['supportMeshPrefixes']):
                raise RuntimeError('Candidate %d expected support %s is not a support prefix' % (candidate['rank'], asset))
            if not disk_path(asset).exists():
                raise RuntimeError('Candidate %d support asset missing on disk: %s' % (candidate['rank'], asset))
        clear = candidate['clearances']
        if clear['mountBoundaryCm'] <= spec['offlineSearch']['guardBufferCm'] or clear['platformDeckRingCm'] <= spec['offlineSearch']['guardBufferCm']:
            raise RuntimeError('Candidate %d inside the Mount guard' % candidate['rank'])
        if any(v <= spec['offlineSearch']['guardBufferCm'] for v in clear['protectedCm'].values()):
            raise RuntimeError('Candidate %d inside a protected-polygon guard' % candidate['rank'])
        if clear['nearestBuildingCm'] is not None and clear['nearestBuildingCm'] <= 0.0:
            raise RuntimeError('Candidate %d overlaps a building footprint' % candidate['rank'])
        pose = build_pose(candidate, check, spec, 'plane')
        report['candidates'].append({'rank': candidate['rank'], 'xy': candidate['xy'], 'yaw': candidate['yaw'],
                                     'offline': {k: check[k] for k in ('spreadCm', 'gradientDegrees', 'crossfallDegrees', 'pitchDegrees', 'rollDegrees')},
                                     'planePoseLocation': pose['location'], 'planePoseRotation': pose['rotation'],
                                     'planePoseMaxWheelFloatCm': pose['maxWheelFloatCm'],
                                     'plannedWorldBoundsCm': rotated_box(spec['assemblyLocalBoundsCm'], pose['location'], pose['rotation'])})
    handoff = spec['offlineSearch']['handoffCandidate']
    handoff_check = support_check(handoff['surfaceZCm'], probes)
    report['handoffCandidateStillFails'] = not handoff_check['passed']
    if handoff_check['passed']:
        raise RuntimeError('Handoff candidate unexpectedly passes; spec numbers are suspect')
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side
# --------------------------------------------------------------------------

def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


class BusJob:
    """State machine driven by a Slate post-tick callback (PIE modes) or run synchronously."""

    def __init__(self, ue, spec, mode):
        self.ue = ue
        self.spec = spec
        self.mode = mode
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.started = time.monotonic()
        self.limit = env_float('MIKDASH_BUS_LIMIT_SECONDS', spec['pie']['hardLimitSeconds'], 30, 120)
        self.quit_editor = os.environ.get('MIKDASH_BUS_QUIT_EDITOR', '0') == '1'
        self.pose_style = 'flat' if os.environ.get('MIKDASH_BUS_POSE', 'plane').lower() == 'flat' else 'plane'
        self.handle = None
        self.state = 'init'
        self.state_since = self.started
        self.finished = False
        self.saved = False
        self.world_seen_at = None
        self.end_requested_at = None
        self.trace_method = None
        self.old_throttle = None
        self.old_mouse = None
        self.settings = None
        self.map_sha_before = None
        self.protected_before = {}
        self.snapshot_baseline = None
        self.chosen = None
        self.placed_records = []
        self.receipt = None
        self.receipt_path = None
        self.stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    # -- receipt / logging ---------------------------------------------------

    def write_receipt(self):
        self.receipt['elapsedSeconds'] = round(time.monotonic() - self.started, 3)
        self.receipt['state'] = self.state
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    def event(self, kind, **data):
        data.update(kind=kind, seconds=round(time.monotonic() - self.started, 3))
        self.receipt['events'].append(data)

    def set_state(self, state):
        self.state = state
        self.state_since = time.monotonic()
        self.event('state', state=state)
        self.write_receipt()

    # -- preconditions -------------------------------------------------------

    def preflight(self):
        ue = self.ue
        spec = self.spec
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project: ' + ue.Paths.project_dir())
        if self.editor.get_game_world():
            raise RuntimeError('PIE already running; stop it first (user PIE preserved)')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present; save or revert first (nothing is auto-saved)')
        loaded_by_job = False
        if self.current_map() != TARGET_MAP:
            if os.environ.get('MIKDASH_BUS_ALLOW_LOAD_MAP', '1') != '1':
                raise RuntimeError('Wrong map %s; expected %s' % (self.current_map(), TARGET_MAP))
            if not self.levels.load_level(TARGET_MAP):
                raise RuntimeError('load_level failed for ' + TARGET_MAP)
            loaded_by_job = True
        if self.current_map() != TARGET_MAP:
            raise RuntimeError('Map assertion failed after load: ' + self.current_map())
        native = json.loads((ROOT / spec['nativeImportReceipt']).read_text(encoding='utf-8-sig'))
        if native['status'] != spec['nativeImportStatusRequired']:
            raise RuntimeError('TransitV2 native receipt status ' + native['status'])
        created = {c.split('.')[0] for c in native['created']}
        for record in spec['meshes']:
            if spec['meshFolder'] + record['name'] not in created:
                raise RuntimeError('Bus mesh not in native receipt: ' + record['name'])
        self.map_sha_before = sha256_of(MAP_FILE)
        self.protected_before = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}

        receipt_folder = ROOT / spec['receiptFolder']
        receipt_folder.mkdir(parents=True, exist_ok=True)
        self.receipt_path = receipt_folder / (spec['receiptPrefix'] + self.stamp + '.json')
        if self.receipt_path.exists():
            raise RuntimeError('Receipt already exists: ' + str(self.receipt_path))
        self.receipt = {
            'status': 'running', 'mode': self.mode, 'stamp': self.stamp, 'map': TARGET_MAP, 'mapFile': str(MAP_FILE),
            'mapSha256Before': self.map_sha_before, 'mapLoadedByJob': loaded_by_job,
            'protectedMapSha256Before': self.protected_before,
            'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'offlineCheck': offline_check(spec),
            'engineVersion': ue.SystemLibrary.get_engine_version(), 'commandLine': ue.SystemLibrary.get_command_line(),
            'config': {'hardLimitSeconds': self.limit, 'quitEditor': self.quit_editor, 'poseStyle': self.pose_style,
                       'candidateFilter': os.environ.get('MIKDASH_BUS_CANDIDATE'), 'poseReceipt': os.environ.get('MIKDASH_BUS_POSE_RECEIPT')},
            'scope': 'Line traces in a bounded PIE world (not a NullRHI editor world); pose from the traced wheel plane; '
                     'placement in the editor world after end-play with checkpoint, save, reopen and numeric readback. '
                     'Not visual, collision-route, boarding or packaged acceptance.',
            'events': [], 'errors': [], 'traceErrors': [], 'candidates': [], 'pose': None, 'poseStatus': None,
            'placed': [], 'mapSaved': False,
            'stationMeshesOmitted': spec['stationMeshesOmitted'], 'stationOmissionReason': spec['stationOmissionReason'],
        }
        self.write_receipt()
        self.check_release_actors()

    def current_map(self):
        return self.editor.get_editor_world().get_path_name().split('.')[0]

    def take_snapshot(self):
        ue = self.ue
        rows = []
        for actor in self.actors.get_all_level_actors():
            meshes = []
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                mesh = component.get_editor_property('static_mesh')
                meshes.append(mesh.get_path_name().split('.')[0] if mesh else None)
            location = actor.get_actor_location()
            rotation = actor.get_actor_rotation()
            scale = actor.get_actor_scale3d()
            rows.append({'actor': actor, 'name': actor.get_name(), 'label': actor.get_actor_label(),
                         'folder': str(actor.get_folder_path()), 'meshes': meshes,
                         'pose': (location.x, location.y, location.z, rotation.pitch, rotation.yaw, rotation.roll, scale.x, scale.y, scale.z)})
        return rows

    def check_release_actors(self):
        spec = self.spec
        rows = self.take_snapshot()
        bus_meshes = {spec['meshFolder'] + m['name'] for m in spec['meshes']}
        clashes = [row['label'] for row in rows
                   if row['label'].startswith(spec['labelPrefix']) or row['folder'] == spec['folder'] or row['folder'].startswith(spec['folder'] + '/')
                   or any(m in bus_meshes for m in row['meshes'])]
        if clashes:
            raise RuntimeError('Existing bus release actors preserved; refusing duplicate placement: %s' % clashes[:13])
        self.snapshot_baseline = {row['name']: (row['label'], tuple(row['meshes']), row['pose']) for row in rows}
        self.receipt['actorCountBefore'] = len(rows)
        self.receipt['preExistingReleaseActors'] = sorted(row['label'] for row in rows if row['label'].startswith('RELEASE_'))
        self.write_receipt()

    # -- tracing -----------------------------------------------------------------

    def trace_down(self, world, start, end):
        ue = self.ue
        common = dict(world_context_object=world, start=ue.Vector(*start), end=ue.Vector(*end), trace_complex=True,
                      actors_to_ignore=[], draw_debug_type=ue.DrawDebugTrace.NONE, ignore_self=False)
        attempts = [
            ('profile_Pawn', lambda: ue.SystemLibrary.line_trace_single_by_profile(profile_name='Pawn', **common)),
            ('profile_BlockAll', lambda: ue.SystemLibrary.line_trace_single_by_profile(profile_name='BlockAll', **common)),
            ('channel_Visibility', lambda: ue.SystemLibrary.line_trace_single(
                trace_channel=getattr(ue.TraceTypeQuery, 'TRACE_TYPE_QUERY1', None), **common)),
            ('objects_WorldStatic', lambda: ue.SystemLibrary.line_trace_single_for_objects(
                object_types=[getattr(ue.ObjectTypeQuery, 'OBJECT_TYPE_QUERY1', None)], **common)),
        ]
        if self.trace_method:
            attempts.sort(key=lambda item: item[0] != self.trace_method)
        for method, call in attempts:
            try:
                hit = call()
            except Exception as error:
                self.receipt['traceErrors'].append({'method': method, 'error': str(error)})
                continue
            if hit is None:
                continue
            parsed = self.parse_hit(hit)
            if parsed is None:
                continue
            self.trace_method = method
            parsed['method'] = method
            return parsed
        return None

    def parse_hit(self, hit):
        """Branch on what the launch mode exposes: break_hit_result, else HitResult.to_dict()."""
        ue = self.ue
        point = normal = actor = component = None
        parsed_by = None
        if hasattr(ue.GameplayStatics, 'break_hit_result'):
            try:
                split = ue.GameplayStatics.break_hit_result(hit)
                if len(split) >= 11:
                    if not bool(split[0]):
                        return None
                    point, normal, actor, component = split[5], split[7], split[9], split[10]
                    parsed_by = 'break_hit_result'
            except Exception as error:
                self.receipt['traceErrors'].append({'method': 'break_hit_result', 'error': str(error)})
        if point is None:
            try:
                data = hit.to_dict()
            except Exception as error:
                self.receipt['traceErrors'].append({'method': 'to_dict', 'error': str(error)})
                return None
            lowered = {str(k).lower(): v for k, v in data.items()}
            blocking = lowered.get('blocking_hit', lowered.get('blockinghit', True))
            if blocking is False:
                return None
            point = lowered.get('impact_point') or lowered.get('impactpoint') or lowered.get('location')
            normal = lowered.get('impact_normal') or lowered.get('impactnormal') or lowered.get('normal')
            actor = lowered.get('hit_actor') or lowered.get('actor') or lowered.get('hitactor')
            component = lowered.get('hit_component') or lowered.get('component') or lowered.get('hitcomponent')
            parsed_by = 'to_dict'
            if point is None:
                self.receipt['traceErrors'].append({'method': 'to_dict', 'error': 'keys: ' + ','.join(sorted(lowered))})
                return None
        try:
            point_list = [float(point.x), float(point.y), float(point.z)]
        except Exception:
            point_list = [float(v) for v in list(point)[:3]]
        normal_list = None
        if normal is not None:
            try:
                normal_list = [float(normal.x), float(normal.y), float(normal.z)]
            except Exception:
                normal_list = None
        mesh = None
        label = None
        try:
            if component is not None and isinstance(component, ue.StaticMeshComponent):
                static_mesh = component.get_editor_property('static_mesh')
                mesh = static_mesh.get_path_name().split('.')[0] if static_mesh else None
        except Exception as error:
            self.receipt['traceErrors'].append({'method': 'component_mesh', 'error': str(error)})
        try:
            if actor is not None:
                label = actor.get_actor_label()
                if mesh is None:
                    components = actor.get_components_by_class(ue.StaticMeshComponent)
                    if len(components) == 1:
                        static_mesh = components[0].get_editor_property('static_mesh')
                        mesh = static_mesh.get_path_name().split('.')[0] if static_mesh else None
        except Exception as error:
            self.receipt['traceErrors'].append({'method': 'actor_label', 'error': str(error)})
        return {'pointCm': point_list, 'normal': normal_list, 'actorLabel': label, 'mesh': mesh, 'parsedBy': parsed_by}

    def is_support(self, hit):
        probes = self.spec['groundProbes']
        if hit['mesh'] and any(hit['mesh'].startswith(p) for p in probes['supportMeshPrefixes']):
            return 'mesh_prefix'
        if hit['mesh'] is None and hit['actorLabel'] and any(hit['actorLabel'].startswith(p) for p in probes['supportLabelPrefixes']):
            return 'label_prefix_fallback'
        return None

    def evaluate_candidate(self, world, candidate):
        probes = self.spec['groundProbes']
        result = {'rank': candidate['rank'], 'xy': candidate['xy'], 'yaw': candidate['yaw'], 'probes': {}, 'bodyCorners': {}}
        top = candidate['offlineMeanWheelZCm'] + probes['traceAboveOfflineMeanWheelZCm']
        bottom = candidate['offlineMeanWheelZCm'] - probes['traceBelowOfflineMeanWheelZCm']
        rejects = []
        wheel_z = {}
        for name, (lx, ly) in probes['localPointsCm'].items():
            xy = local_to_world_xy(candidate['xy'], candidate['yaw'], lx, ly)
            hit = self.trace_down(world, [xy[0], xy[1], top], [xy[0], xy[1], bottom])
            row = {'xy': xy, 'traceStartZ': top, 'traceEndZ': bottom, 'hit': hit, 'offlineZ': candidate['offlineSurfaceZCm'][name]}
            if hit is None:
                rejects.append('no hit at ' + name)
            else:
                row['support'] = self.is_support(hit)
                row['offlineDeltaCm'] = hit['pointCm'][2] - candidate['offlineSurfaceZCm'][name]
                row['offlineAgreement'] = abs(row['offlineDeltaCm']) <= probes['offlineAgreementToleranceCm']
                if row['support'] is None:
                    rejects.append('non-support hit at %s: mesh %s label %s' % (name, hit['mesh'], hit['actorLabel']))
                if name != 'center':
                    wheel_z[name] = hit['pointCm'][2]
            result['probes'][name] = row
        for name, (lx, ly) in probes['bodyCornerPointsCm'].items():
            xy = local_to_world_xy(candidate['xy'], candidate['yaw'], lx, ly)
            hit = self.trace_down(world, [xy[0], xy[1], top], [xy[0], xy[1], bottom])
            result['bodyCorners'][name] = {'xy': xy, 'hit': hit, 'support': self.is_support(hit) if hit else None}
        if len(wheel_z) == 4:
            check = support_check(wheel_z, probes)
            result['supportCheck'] = check
            rejects += check['failures']
        result['rejectReasons'] = rejects
        result['accepted'] = not rejects
        return result

    def run_traces(self, world):
        spec = self.spec
        wanted = os.environ.get('MIKDASH_BUS_CANDIDATE')
        candidates = [c for c in spec['candidates'] if not wanted or str(c['rank']) == wanted]
        if not candidates:
            raise RuntimeError('MIKDASH_BUS_CANDIDATE=%s matches no spec candidate' % wanted)
        for candidate in candidates:
            result = self.evaluate_candidate(world, candidate)
            self.receipt['candidates'].append(result)
            self.write_receipt()
            if result['accepted']:
                pose = build_pose(candidate, result['supportCheck'], spec, self.pose_style)
                pose['candidateRank'] = candidate['rank']
                pose['groundSource'] = 'pie_line_trace_' + str(self.trace_method)
                pose['supportMeshes'] = sorted({p['hit']['mesh'] or ('label:' + str(p['hit']['actorLabel'])) for p in result['probes'].values()})
                pose['offlineAgreementAllProbes'] = all(p.get('offlineAgreement') for p in result['probes'].values())
                self.chosen = {'candidate': candidate, 'result': result, 'pose': pose}
                self.receipt['pose'] = pose
                self.receipt['poseStatus'] = 'pose_ok'
                self.receipt['pose']['mapSha256Before'] = self.map_sha_before
                self.event('candidate_accepted', rank=candidate['rank'], location=pose['location'], rotation=pose['rotation'])
                return True
            self.event('candidate_rejected', rank=candidate['rank'], reasons=result['rejectReasons'])
        self.receipt['poseStatus'] = 'no_candidate_accepted'
        return False

    # -- placement (editor world) ------------------------------------------------

    def checkpoint(self):
        spec = self.spec
        folder = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + self.stamp)
        folder.mkdir(parents=True, exist_ok=False)
        shutil.copy2(MAP_FILE, folder / MAP_FILE.name)
        if sha256_of(folder / MAP_FILE.name) != sha256_of(MAP_FILE):
            raise RuntimeError('Checkpoint copy hash differs')
        copied = []
        for name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / name / TARGET_MAP[6:]
            if external.exists():
                shutil.copytree(external, folder / name / TARGET_MAP[6:])
                copied.append(str(external))
        self.receipt['checkpoint'] = str(folder)
        self.receipt['oneFilePerActorFoldersCopied'] = copied
        self.write_receipt()

    def spawn_bus(self, pose):
        ue = self.ue
        spec = self.spec
        tolerance = spec['verification']['staticBoundsToleranceCm']
        meshes = []
        for record in spec['meshes']:
            asset_path = spec['meshFolder'] + record['name']
            mesh = ue.load_asset(asset_path)
            if not isinstance(mesh, ue.StaticMesh):
                raise RuntimeError('Not a StaticMesh: ' + asset_path)
            if mesh.get_num_triangles(0) != record['triangles']:
                raise RuntimeError('%s triangles %d differ from spec %d' % (asset_path, mesh.get_num_triangles(0), record['triangles']))
            box = mesh.get_bounding_box()
            local = {'min': [box.min.x, box.min.y, box.min.z], 'max': [box.max.x, box.max.y, box.max.z]}
            if box_error(local, record['localBoundsCm']) > tolerance:
                raise RuntimeError('%s bounds differ from spec by %.4f cm' % (asset_path, box_error(local, record['localBoundsCm'])))
            body = mesh.get_editor_property('body_setup')
            flag = str(body.get_editor_property('collision_trace_flag')) if body else None
            meshes.append({'path': asset_path, 'mesh': mesh, 'local': local, 'collisionTraceFlag': flag})
        location = pose['location']
        rotation = pose['rotation']
        placed = []
        records = []
        try:
            for index, entry in enumerate(meshes, start=1):
                label = spec['labelPrefix'] + str(index)
                actor = self.actors.spawn_actor_from_class(
                    ue.StaticMeshActor, ue.Vector(*location), ue.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]), transient=False)
                if actor is None:
                    raise RuntimeError('StaticMeshActor spawn returned None for ' + label)
                placed.append(actor)
                actor.set_actor_label(label)
                actor.set_folder_path(spec['folder'])
                actor.set_editor_property('tags', [ue.Name(spec['actorTag']), ue.Name(spec['groupTag']), ue.Name(entry['path'].rsplit('/', 1)[1])])
                component = actor.get_component_by_class(ue.StaticMeshComponent)
                if component is None:
                    raise RuntimeError('Spawned actor has no StaticMeshComponent: ' + label)
                if not component.set_static_mesh(entry['mesh']):
                    raise RuntimeError('set_static_mesh returned False for ' + label)
                readback = component.get_editor_property('static_mesh')
                if readback is None or readback.get_path_name().split('.')[0] != entry['path']:
                    raise RuntimeError('Static mesh readback differs for ' + label)
                component.set_collision_profile_name(spec['collisionProfile'])
                planned = rotated_box(entry['local'], location, rotation)
                origin, extent = actor.get_actor_bounds(False)
                actual = {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
                          'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}
                error = box_error(actual, planned)
                if error > max(tolerance, 0.5):
                    raise RuntimeError('Bus part %s bounds differ from plan by %.4f cm' % (label, error))
                records.append({'label': label, 'mesh': entry['path'], 'location': list(location), 'rotation': list(rotation),
                                'scale': [1.0, 1.0, 1.0], 'collisionProfile': spec['collisionProfile'],
                                'meshCollisionTraceFlag': entry['collisionTraceFlag'], 'plannedWorldBoundsCm': planned,
                                'placedWorldBoundsCm': actual, 'boundsErrorCm': error})
            # Wheel contact readback through the engine transform of the first actor.
            transform = placed[0].get_actor_transform()
            wheels = {}
            for name, (lx, ly) in spec['groundProbes']['localPointsCm'].items():
                if name == 'center':
                    continue
                local = ue.Vector(lx, ly, float(spec['tireContactLocalZ']))
                if hasattr(transform, 'transform_location'):
                    world = transform.transform_location(local)
                else:
                    world = ue.MathLibrary.transform_location(transform, local)
                wheels[name] = {'engineWorldContactCm': [world.x, world.y, world.z],
                                'tracedGroundZ': pose['wheels'][name]['tracedGroundZ'],
                                'floatCm': world.z - pose['wheels'][name]['tracedGroundZ']}
            worst = max(abs(w['floatCm']) for w in wheels.values())
            self.receipt['engineWheelContacts'] = wheels
            self.receipt['engineMaxWheelFloatCm'] = worst
            if self.pose_style == 'plane' and worst > spec['verification']['wheelContactToleranceCm']:
                raise RuntimeError('Engine wheel contact float %.3f cm exceeds tolerance' % worst)
        except Exception:
            for actor in placed:
                try:
                    self.actors.destroy_actor(actor)
                except Exception as error:
                    self.receipt['errors'].append('cleanup: ' + str(error))
            raise
        self.placed_records = records
        self.receipt['placed'] = records
        self.write_receipt()

    def verify_baseline_unchanged(self, rows, stage):
        current = {row['name']: (row['label'], tuple(row['meshes']), row['pose']) for row in rows}
        changed = [name for name, row in self.snapshot_baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed %s: %s' % (stage, changed[:10]))

    def place_and_save(self):
        ue = self.ue
        if self.editor.get_game_world() is not None:
            raise RuntimeError('Game world still present; refusing to mutate')
        if self.current_map() != TARGET_MAP:
            raise RuntimeError('Editor map changed to ' + self.current_map())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present before placement; refusing to save foreign edits')
        if sha256_of(MAP_FILE) != self.map_sha_before:
            raise RuntimeError('Map file changed on disk during the run')
        self.check_release_actors()
        self.checkpoint()
        self.spawn_bus(self.receipt['pose'])
        rows = self.take_snapshot()
        self.verify_baseline_unchanged([r for r in rows if not r['label'].startswith(self.spec['labelPrefix'])], 'before save')
        if not self.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        self.saved = True
        self.receipt['mapSaved'] = True
        self.receipt['mapSha256AfterSave'] = sha256_of(MAP_FILE)
        self.write_receipt()

    def reopen(self):
        if not self.levels.load_level(TARGET_MAP):
            raise RuntimeError('Reopen failed')
        if self.current_map() != TARGET_MAP:
            raise RuntimeError('Reopened world is ' + self.current_map())

    def readback(self):
        ue = self.ue
        spec = self.spec
        verify = spec['verification']
        rows = self.take_snapshot()
        self.verify_baseline_unchanged([r for r in rows if not r['label'].startswith(spec['labelPrefix'])], 'after reopen')
        readback = []
        for record in self.placed_records:
            matching = [row for row in rows if row['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
            row = matching[0]
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            pose = row['pose']
            location_error = max(abs(pose[i] - record['location'][i]) for i in range(3))
            rotation_error = max(abs(((pose[3 + i] - record['rotation'][i]) + 180.0) % 360.0 - 180.0) for i in range(3))
            scale_error = max(abs(pose[6 + i] - 1.0) for i in range(3))
            if location_error > verify['transformToleranceCm'] or rotation_error > verify['rotationToleranceDegrees'] or scale_error > 1e-6:
                raise RuntimeError('Reopened transform differs for %s: loc %.5f rot %.5f' % (record['label'], location_error, rotation_error))
            actor = row['actor']
            origin, extent = actor.get_actor_bounds(False)
            bounds = {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
                      'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}
            error = box_error(bounds, record['plannedWorldBoundsCm'])
            if error > max(verify['staticBoundsToleranceCm'], 0.5):
                raise RuntimeError('Reopened bounds differ for %s by %.4f' % (record['label'], error))
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            readback.append({'label': record['label'], 'folder': row['folder'], 'mesh': row['meshes'][0],
                             'location': list(pose[0:3]), 'rotation': list(pose[3:6]), 'scale': list(pose[6:9]),
                             'locationErrorCm': location_error, 'rotationErrorDegrees': rotation_error,
                             'worldBoundsCm': bounds, 'boundsErrorCm': error,
                             'collisionProfile': str(component.get_collision_profile_name()),
                             'tags': [str(t) for t in actor.get_editor_property('tags')]})
        self.receipt['reopenedReadback'] = readback
        self.receipt['actorCountAfter'] = len(rows)
        self.receipt['actorCountDelta'] = len(rows) - self.receipt['actorCountBefore']
        if self.receipt['actorCountDelta'] != len(self.placed_records):
            raise RuntimeError('Actor count delta %d differs from placed %d' % (self.receipt['actorCountDelta'], len(self.placed_records)))

    def finalize_hashes(self):
        self.receipt['mapSha256After'] = sha256_of(MAP_FILE)
        self.receipt['mapBytesChanged'] = self.receipt['mapSha256After'] != self.map_sha_before
        self.receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(m, 'umap')) == v for m, v in self.protected_before.items())
        if not self.receipt['protectedMapsUnchanged']:
            self.receipt['errors'].append('PROTECTED MAP HASH CHANGED')

    # -- PIE control -----------------------------------------------------------

    def begin_pie(self):
        ue = self.ue
        self.settings = ue.get_default_object(ue.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
        self.old_mouse = self.settings.get_editor_property('GameGetsMouseControl')
        self.old_throttle = ue.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
        self.receipt['config']['oldThrottle'] = self.old_throttle
        self.receipt['config']['oldGameGetsMouseControl'] = self.old_mouse
        ue.SystemLibrary.execute_console_command(self.editor.get_editor_world(), 'Slate.bAllowThrottling 0')
        self.settings.set_editor_property('GameGetsMouseControl', False)
        self.write_receipt()
        self.levels.editor_request_begin_play()
        self.set_state('wait_game_world')

    def restore_settings(self):
        ue = self.ue
        if self.settings is None:
            return
        for name, action in [
                ('restoreMouseSetting', lambda: self.settings.set_editor_property('GameGetsMouseControl', self.old_mouse)),
                ('restoreThrottle', lambda: ue.SystemLibrary.execute_console_command(
                    self.editor.get_editor_world(), 'Slate.bAllowThrottling ' + str(self.old_throttle)))]:
            try:
                action()
                self.receipt[name] = 'completed'
            except Exception as error:
                self.receipt['errors'].append(name + ': ' + str(error))
        self.settings = None

    def request_end_play(self):
        try:
            if self.editor.get_game_world() is not None:
                self.levels.editor_request_end_play()
                self.receipt['stopPie'] = 'requested'
        except Exception as error:
            self.receipt['errors'].append('stopPie: ' + str(error))
        self.end_requested_at = time.monotonic()

    def finish(self, status):
        if self.finished:
            return
        self.finished = True
        self.receipt['status'] = status
        self.request_end_play()
        self.restore_settings()
        try:
            self.finalize_hashes()
        except Exception as error:
            self.receipt['errors'].append('finalize: ' + str(error))
        self.set_state('finished')
        self.ue.log('release_place_bus: ' + status + ' -> ' + str(self.receipt_path))
        if not self.quit_editor and self.handle is not None:
            try:
                self.ue.unregister_slate_post_tick_callback(self.handle)
                self.handle = None
            except Exception as error:
                self.receipt['errors'].append('unregister: ' + str(error))
                self.write_receipt()

    def fail(self, error, stage):
        self.receipt['errors'].append({'stage': stage, 'error': repr(error)})
        if self.saved:
            self.finish('failed_after_save_checkpoint_available')
        else:
            self.finish('failed_' + stage + '_map_unchanged')

    def quit_tick(self):
        if self.end_requested_at is not None and time.monotonic() - self.end_requested_at < 2.0:
            return
        if self.editor.get_game_world() is not None and self.end_requested_at is not None and time.monotonic() - self.end_requested_at < 10.0:
            return
        if self.handle is not None:
            self.ue.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        self.ue.SystemLibrary.quit_editor()

    # -- tick state machine -----------------------------------------------------

    def tick(self, delta):
        if self.finished:
            if self.quit_editor:
                self.quit_tick()
            return
        now = time.monotonic()
        elapsed = now - self.started
        try:
            if elapsed > self.limit and not self.saved:
                self.finish('failed_timeout_map_unchanged')
                return
            if elapsed > self.limit and self.saved:
                self.receipt['limitExceededAfterSave'] = True
            if self.state == 'wait_game_world':
                world = self.editor.get_game_world()
                if world is None:
                    if elapsed > self.spec['pie']['pieWorldTimeoutSeconds']:
                        self.finish('failed_no_game_world')
                    return
                if self.world_seen_at is None:
                    self.world_seen_at = now
                    self.event('game_world_seen', world=world.get_path_name())
                    return
                if now - self.world_seen_at < self.spec['pie']['settleSecondsAfterWorld']:
                    return
                self.set_state('tracing')
                accepted = self.run_traces(world)
                self.event('traces_done', accepted=accepted, method=self.trace_method)
                self.request_end_play()
                self.set_state('ending_pie' if accepted else 'ending_pie_no_pose')
                return
            if self.state in ('ending_pie', 'ending_pie_no_pose'):
                if self.editor.get_game_world() is not None:
                    if now - self.end_requested_at > 20.0:
                        self.finish('failed_pie_did_not_end')
                    return
                if now - self.end_requested_at < self.spec['pie']['endPlaySettleSeconds']:
                    return
                self.restore_settings()
                if self.state == 'ending_pie_no_pose':
                    self.finish('no_candidate_accepted_map_unchanged')
                    return
                if self.mode == 'trace_only':
                    self.finish('pose_traced_not_placed')
                    return
                self.set_state('placing')
                return
            if self.state == 'placing':
                self.place_and_save()
                self.set_state('reopening')
                return
            if self.state == 'reopening':
                if now - self.state_since < self.spec['pie']['reopenSettleSeconds']:
                    return
                self.reopen()
                self.set_state('readback')
                return
            if self.state == 'readback':
                if now - self.state_since < self.spec['pie']['reopenSettleSeconds']:
                    return
                self.readback()
                self.finish('bus_saved_reopened_visual_runtime_acceptance_pending')
                return
        except Exception as error:
            self.fail(error, self.state)

    # -- synchronous mode -----------------------------------------------------------

    def place_from_receipt_sync(self):
        path = os.environ.get('MIKDASH_BUS_POSE_RECEIPT', '')
        if not path or not Path(path).exists():
            raise RuntimeError('MIKDASH_BUS_POSE_RECEIPT must point at an existing trace receipt')
        source = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        if source.get('poseStatus') != 'pose_ok' or not source.get('pose'):
            raise RuntimeError('Pose receipt has no accepted pose (poseStatus %s)' % source.get('poseStatus'))
        if source.get('map') != TARGET_MAP:
            raise RuntimeError('Pose receipt is for another map: ' + str(source.get('map')))
        if source['pose'].get('mapSha256Before') != self.map_sha_before and os.environ.get('MIKDASH_BUS_ALLOW_MAP_CHANGE') != '1':
            raise RuntimeError('Map SHA-256 differs from the traced map; retrace or set MIKDASH_BUS_ALLOW_MAP_CHANGE=1')
        if source.get('mapSaved'):
            raise RuntimeError('Pose receipt already recorded a save; refusing a second placement')
        pose = source['pose']
        for key in ('location', 'rotation'):
            if len(pose[key]) != 3 or not all(math.isfinite(float(v)) for v in pose[key]):
                raise RuntimeError('Pose %s is not a finite 3-vector' % key)
        self.pose_style = pose.get('style', self.pose_style)
        self.receipt['pose'] = pose
        self.receipt['poseStatus'] = 'pose_from_receipt'
        self.receipt['poseReceipt'] = {'path': path, 'sha256': sha256_of(path), 'stamp': source.get('stamp')}
        self.set_state('placing')
        self.place_and_save()
        self.set_state('reopening')
        self.reopen()
        self.set_state('readback')
        self.readback()
        self.finish('bus_saved_reopened_visual_runtime_acceptance_pending')


def _main():
    import unreal as ue
    mode = os.environ.get('MIKDASH_BUS_MODE', 'trace_and_place').lower()
    if mode not in MODES:
        raise RuntimeError('MIKDASH_BUS_MODE must be one of %s' % (MODES,))
    command_line = ue.SystemLibrary.get_command_line().lower()
    commandlet = '-run=pythonscript' in command_line
    if mode != 'place_from_receipt' and commandlet:
        raise RuntimeError('PIE modes cannot run under -run=pythonscript; use the -ExecCmds editor launch (see module docstring)')
    spec = load_spec()
    job = BusJob(ue, spec, mode)
    job.preflight()
    if mode == 'place_from_receipt':
        try:
            job.place_from_receipt_sync()
        except Exception as error:
            job.fail(error, job.state)
            raise
        finally:
            job.write_receipt()
            if job.quit_editor and not commandlet:
                ue.SystemLibrary.quit_editor()
        return job.receipt
    job.handle = ue.register_slate_post_tick_callback(job.tick)
    try:
        job.begin_pie()
    except Exception as error:
        job.fail(error, 'begin_play')
        raise
    ue.log('release_place_bus started (%s); receipt %s' % (mode, job.receipt_path))
    return job.receipt


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _unreal_available():
    import unreal as _ue
    _cmd = _ue.SystemLibrary.get_command_line().lower()
    if 'release_place_bus.py' in _cmd and ('-run=pythonscript' in _cmd or '-executepythonscript' in _cmd):
        _main()

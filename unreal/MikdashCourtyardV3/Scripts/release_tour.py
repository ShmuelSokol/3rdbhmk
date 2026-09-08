"""Guarded placement of the guided tour into the combined IntegratedReviewV2 map.

Places three things and nothing else:

  * ONE AMikdashTourGuide  (RELEASE_TOUR_Guide)  - loads tour-stops.json at run time,
    registers itself with UMikdashFrontEnd so the "Guided tour" menu entry lights up.
  * ONE AMikdashCodex      (RELEASE_TOUR_Codex)  - loads codex-entries.json.
  * ONE thin marker disc per tour stop, at the stop's own coordinates, tagged with the
    stop key so the guide can show only the one the visitor is heading for.

Every coordinate comes from SourceAssets/tour-review/tour-stops.json, which is the same
file the run-time actor reads and whose geometry Plugins/MikdashRuntime/Tests/
TourMathTest.cpp mirrors. Nothing about a stop's position is written twice by hand.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_tour.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Tour-01.log"

Optional switches (read from the engine command line):
  -TourGroups=markers          comma-separated subset of actors,markers.
  -TourDryRun                  run every guard and the trace self-test, place nothing,
                               write the receipt, leave the map byte-identical.

Run order. The module must be COMPILED first: this script spawns AMikdashTourGuide and
AMikdashCodex by name, and if the classes are not in the running editor it refuses
before touching anything rather than placing half a tour.

Safety model, the same one Scripts/release_place_assets.py uses and for the same reasons:
  * Refuses on the wrong project directory, a live game world, dirty packages, or a
    loaded world that is not the combined map.
  * Checkpoints Walkthrough.umap (and any One-File-Per-Actor folders) before any
    mutation and verifies the copy by hash.
  * Refuses if RELEASE_TOUR_ actors of a requested group already exist, rather than
    quietly doubling them.
  * Saves only if something was placed, reopens the map, and reads every placed actor
    back numerically - class, label, tags, mesh, transform, world bounds.
  * Writes the receipt at start and again in finally, so a failure preserves its evidence.

Offline, with no engine at all:  python Scripts/release_tour.py
That runs offline_check(), which re-implements MikdashTour::Route::Validate over the
JSON and audits the codex, and prints the result as JSON. It is the check worth running
after every content edit; it needs no editor and takes no lock.
"""
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_tour.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'

GROUP_ORDER = ('actors', 'markers')


# --------------------------------------------------------------------------
# Pure helpers. No unreal import, so offline_check() runs anywhere.
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets live on this project disk: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def load_tour(spec):
    return json.loads((ROOT / spec['tourContent']).read_text(encoding='utf-8-sig'))


def load_codex(spec):
    return json.loads((ROOT / spec['codexContent']).read_text(encoding='utf-8-sig'))


def normalise_groups(groups):
    if isinstance(groups, str):
        groups = groups.split(',')
    wanted = [g.strip().lower() for g in groups if g.strip()]
    unknown = [g for g in wanted if g not in GROUP_ORDER]
    if unknown:
        raise RuntimeError('Unknown tour groups %s; valid: %s' % (unknown, list(GROUP_ORDER)))
    if not wanted:
        raise RuntimeError('No tour groups requested')
    return tuple(g for g in GROUP_ORDER if g in wanted)


def finite3(value):
    return (isinstance(value, (list, tuple)) and len(value) == 3
            and all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in value))


def distance_2d(a, b):
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def marker_label(spec, order, key):
    return '%sMarker_%02d_%s' % (spec['labelPrefix'], order, key)


# --------------------------------------------------------------------------
# Offline validation. This is MikdashTour::Route::Validate, in Python, over the JSON.
# --------------------------------------------------------------------------

def validate_route(tour, rules):
    """Return a list of refusal strings. Empty means the route is legal.

    Deliberately a second implementation rather than a call into the C++: the point is
    that the JSON is checked by something that did not compile the header, so a change
    to one that breaks the other is visible instead of silently agreed to.
    """
    problems = []
    stops = tour.get('stops')
    if not isinstance(stops, list) or not stops:
        return ['no "stops" array, or it is empty']
    if len(stops) > rules['maxStops']:
        problems.append('%d stops; MaxStops is %d' % (len(stops), rules['maxStops']))
    if not (rules['minStopCount'] <= len(stops) <= rules['maxStopCount']):
        problems.append('%d stops; the brief asks for %d to %d'
                        % (len(stops), rules['minStopCount'], rules['maxStopCount']))

    seen = {}
    for index, stop in enumerate(stops):
        key = stop.get('key')
        where = 'stop %d (%s)' % (index, key or '?')
        if not key:
            problems.append('stop %d has no key' % index)
            continue
        if key in seen:
            problems.append('%s duplicates the key of stop %d' % (where, seen[key]))
        seen[key] = index

        for field in ('stand', 'look'):
            if not finite3(stop.get(field)):
                problems.append('%s has a missing or non-finite %s' % (where, field))

        waypoints = stop.get('approach') or []
        if len(waypoints) > rules['maxWaypoints']:
            problems.append('%s has %d approach waypoints; the limit is %d'
                            % (where, len(waypoints), rules['maxWaypoints']))
        for slot, point in enumerate(waypoints):
            if not finite3(point):
                problems.append('%s approach waypoint %d is malformed' % (where, slot))

        arrive = stop.get('arriveRadiusCm')
        leave = stop.get('leaveRadiusCm')
        if not isinstance(arrive, (int, float)) or not isinstance(leave, (int, float)):
            problems.append('%s is missing an arrival or leave radius' % where)
            continue
        if arrive < rules['minArriveRadiusCm']:
            problems.append('%s arrival radius %.1f is below the minimum %.1f'
                            % (where, arrive, rules['minArriveRadiusCm']))
        if leave - arrive < rules['minRadiusGapCm']:
            # Without a gap the arrival prompt strobes while the visitor stands still.
            problems.append('%s radii %.1f/%.1f are closer than the %.1f cm hysteresis gap'
                            % (where, arrive, leave, rules['minRadiusGapCm']))

        if index > 0:
            previous = stops[index - 1]
            if finite3(stop.get('stand')) and finite3(previous.get('stand')):
                gap = distance_2d(previous['stand'], stop['stand'])
                widest = max(float(arrive), float(previous.get('arriveRadiusCm') or 0.0))
                if gap <= widest:
                    problems.append('%s is %.1f cm from the stop before it, inside the %.1f cm '
                                    'arrival radius: the visitor would arrive at two places at once'
                                    % (where, gap, widest))

        order = stop.get('order')
        if order != index + 1:
            problems.append('%s carries order %r but is at position %d' % (where, order, index + 1))
    return problems


def validate_codex(tour, codex, rules):
    problems = []
    entries = codex.get('entries')
    if not isinstance(entries, list) or not entries:
        return ['no "entries" array, or it is empty'], {}

    counts = {label: 0 for label in rules['validConfidence']}
    ids = {}
    for index, entry in enumerate(entries):
        entry_id = entry.get('id')
        where = 'entry %d (%s)' % (index, entry_id or '?')
        if not entry_id:
            problems.append('entry %d has no id' % index)
            continue
        if entry_id in ids:
            problems.append('%s duplicates an earlier id' % where)
        ids[entry_id] = index

        label = entry.get('confidence')
        if label not in rules['validConfidence']:
            # The whole point of the codex. A typo must never read as "certain".
            problems.append('%s has an unrecognised confidence label %r' % (where, label))
            continue
        counts[label] += 1

        if rules['requireDisputedNamesPositions'] and label == 'disputed':
            positions = ((entry.get('dispute') or {}).get('positions')) or []
            if len(positions) < 2:
                problems.append('%s is labelled disputed but names %d position(s); '
                                'name who holds what' % (where, len(positions)))
        if rules['requireSourcesUnlessAuthored'] and label != 'authored':
            if not entry.get('sources'):
                problems.append('%s claims %s but cites nothing' % (where, label))

    stop_keys = {stop.get('key') for stop in (tour.get('stops') or [])}
    for entry in entries:
        for stop_key in entry.get('unlockedBy') or []:
            if stop_key not in stop_keys:
                problems.append('entry %s is unlocked by "%s", which is not a stop'
                                % (entry.get('id'), stop_key))
        for related in entry.get('related') or []:
            if related not in ids:
                problems.append('entry %s relates to "%s", which does not exist'
                                % (entry.get('id'), related))

    for stop in tour.get('stops') or []:
        for entry_id in stop.get('codexEntries') or []:
            if entry_id not in ids:
                problems.append('stop %s points at codex entry "%s", which does not exist'
                                % (stop.get('key'), entry_id))
    return problems, counts


def offline_check(spec=None):
    """Everything that can be proved without an editor. Safe to run at any time."""
    spec = spec or load_spec()
    tour = load_tour(spec)
    codex = load_codex(spec)

    route_problems = validate_route(tour, spec['routeRules'])
    codex_problems, counts = validate_codex(tour, codex, spec['codexRules'])

    stops = tour.get('stops') or []
    total_cm = 0.0
    for index in range(1, len(stops)):
        points = [stops[index - 1]['stand']] + list(stops[index].get('approach') or []) + [stops[index]['stand']]
        for step in range(1, len(points)):
            total_cm += distance_2d(points[step - 1], points[step])

    # Content honesty audit: what is empty on purpose, and what is not filled in yet.
    hebrew_names = sum(1 for s in stops if (s.get('name') or {}).get('he'))
    narration_filled = sum(1 for s in stops if ((s.get('narrationAudio') or {}).get('asset')))
    unreachable = [e['id'] for e in codex.get('entries') or [] if not e.get('unlockedBy')]

    return {
        'spec': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'tourContent': str(ROOT / spec['tourContent']),
        'tourContentSha256': sha256_of(ROOT / spec['tourContent']),
        'codexContent': str(ROOT / spec['codexContent']),
        'codexContentSha256': sha256_of(ROOT / spec['codexContent']),
        'stopCount': len(stops),
        'stopKeys': [s.get('key') for s in stops],
        'routeWalkingLengthCm': round(total_cm, 3),
        'routeWalkingLengthAmot': round(total_cm / 50.0, 2),
        'routeProblems': route_problems,
        'codexEntryCount': len(codex.get('entries') or []),
        'codexCountsByConfidence': counts,
        'codexProblems': codex_problems,
        'codexEntriesNoStopUnlocks': unreachable,
        'stopsWithHebrewName': hebrew_names,
        'stopsWithNarrationAudio': narration_filled,
        'ok': not route_problems and not codex_problems,
    }


# --------------------------------------------------------------------------
# Engine side.
# --------------------------------------------------------------------------

def _vector_list(v):
    return [float(v.x), float(v.y), float(v.z)]


def _rotator_list(r):
    return [float(r.pitch), float(r.yaw), float(r.roll)]


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _actor_bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
            'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}


def _actor_pose(actor):
    return {'location': _vector_list(actor.get_actor_location()),
            'rotation': _rotator_list(actor.get_actor_rotation()),
            'scale': _vector_list(actor.get_actor_scale3d())}


def _pose_error(pose, location, rotation, scale):
    errors = [abs(pose['location'][i] - location[i]) for i in range(3)]
    errors += [abs(pose['rotation'][i] - rotation[i]) for i in range(3)]
    errors += [abs(pose['scale'][i] - scale[i]) for i in range(3)]
    return max(errors)


class OmissionError(Exception):
    """A group that could not be placed but must not stop the rest."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


class TourPlacement:
    def __init__(self, ue, spec, tour, dry_run=False):
        self.ue = ue
        self.spec = spec
        self.tour = tour
        self.dry_run = dry_run
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.world = None
        self.snapshot = None
        self.receipt = None
        self.receipt_path = None
        self.trace_method = None

    # -- receipt -----------------------------------------------------------

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    # -- scene snapshot ----------------------------------------------------

    def take_snapshot(self):
        ue = self.ue
        rows = []
        for actor in self.actors.get_all_level_actors():
            meshes = []
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                meshes.append(_asset_path(component.get_editor_property('static_mesh')))
            rows.append({'actor': actor, 'name': actor.get_name(), 'label': actor.get_actor_label(),
                         'class': actor.get_class().get_name(), 'folder': str(actor.get_folder_path()),
                         'tags': [str(t) for t in actor.get_editor_property('tags')],
                         'meshes': meshes, 'pose': _actor_pose(actor), 'bounds': _actor_bounds(actor)})
        self.snapshot = rows
        return rows

    def numeric_baseline(self, rows):
        return {row['name']: (row['label'], tuple(row['meshes']),
                              tuple(row['pose']['location'] + row['pose']['rotation'] + row['pose']['scale']))
                for row in rows}

    # -- tracing -----------------------------------------------------------

    def trace_down(self, xy, fallback_z):
        """(z, method). method is 'trace' or 'json-fallback'."""
        ue = self.ue
        cfg = self.spec['trace']
        start = (float(xy[0]), float(xy[1]), float(fallback_z) + cfg['startAboveCm'])
        end = (float(xy[0]), float(xy[1]), float(fallback_z) - cfg['endBelowCm'])
        common = dict(world_context_object=self.world, start=ue.Vector(*start), end=ue.Vector(*end),
                      trace_complex=True, actors_to_ignore=[],
                      draw_debug_type=ue.DrawDebugTrace.NONE, ignore_self=False)
        attempts = [
            ('profile_Pawn', lambda: ue.SystemLibrary.line_trace_single_by_profile(profile_name='Pawn', **common)),
            ('channel_Visibility', lambda: ue.SystemLibrary.line_trace_single(
                trace_channel=getattr(ue.TraceTypeQuery, 'ECC_VISIBILITY',
                                      getattr(ue.TraceTypeQuery, 'TRACE_TYPE_QUERY1', None)), **common)),
            ('objects_WorldStatic', lambda: ue.SystemLibrary.line_trace_single_for_objects(
                object_types=[getattr(ue.ObjectTypeQuery, 'ECC_WORLD_STATIC',
                                      getattr(ue.ObjectTypeQuery, 'OBJECT_TYPE_QUERY1', None))], **common)),
        ]
        if self.trace_method:
            attempts.sort(key=lambda item: item[0] != self.trace_method)
        for method, call in attempts:
            try:
                hit = call()
            except Exception as error:                       # noqa: BLE001
                self.receipt.setdefault('traceErrors', []).append({'method': method, 'error': str(error)})
                continue
            if hit is None:
                continue
            try:
                split = ue.GameplayStatics.break_hit_result(hit)
            except Exception as error:                       # noqa: BLE001
                self.receipt.setdefault('traceErrors', []).append({'method': 'break_hit_result', 'error': str(error)})
                continue
            if len(split) < 16 or not bool(split[0]):
                continue
            z = float(split[5].z)
            if abs(z - float(fallback_z)) > self.spec['trace']['acceptWithinCm']:
                # A hit a long way from the recorded floor is a hit on something else -
                # a roof, a wall top, a vessel. Do not silently move the marker onto it.
                self.receipt.setdefault('traceRejected', []).append(
                    {'xy': [float(xy[0]), float(xy[1])], 'hitZ': z, 'expectedZ': float(fallback_z), 'method': method})
                continue
            self.trace_method = method
            return z, method
        return float(fallback_z), 'json-fallback'

    def trace_self_test(self):
        cfg = self.spec['trace']['selfTest']
        rows = []
        for probe in cfg['probes']:
            z, method = self.trace_down(probe['xy'], probe['expectedZ'])
            rows.append({'name': probe['name'], 'xy': probe['xy'], 'expectedZ': probe['expectedZ'],
                         'z': z, 'method': method,
                         'result': 'PASS' if method == 'trace' and abs(z - probe['expectedZ']) <= cfg['toleranceCm']
                                   else ('FALLBACK' if method == 'json-fallback' else 'HIT_BUT_UNEXPECTED')})
        result = {'probes': rows, 'anyTraceHit': any(r['method'] == 'trace' for r in rows)}
        self.receipt['traceSelfTest'] = result
        return result

    # -- guards ------------------------------------------------------------

    def require_classes(self):
        """Refuse before touching anything if the module was not compiled with the new
        classes in it. Half a tour is worse than no tour."""
        ue = self.ue
        missing = []
        found = {}
        for key in ('guideClass', 'codexClass'):
            name = self.spec[key]
            cls = getattr(ue, name, None)
            if cls is None:
                missing.append(name)
            else:
                found[name] = str(cls)
        if missing:
            raise RuntimeError('Classes not present in the running editor: %s. '
                               'Compile MikdashRuntime first (verify.py --build), then rerun.' % missing)
        return found

    # -- placing -----------------------------------------------------------

    def place_actors(self):
        """The tour guide and the codex. Content-free actors with no mesh."""
        ue = self.ue
        placed = []
        plan = [(self.spec['guideLabel'], self.spec['guideClass']),
                (self.spec['codexLabel'], self.spec['codexClass'])]
        if self.dry_run:
            return {'actors': [], 'dryRunPlan': [{'label': l, 'class': c} for l, c in plan]}
        for label, class_name in plan:
            cls = getattr(ue, class_name)
            actor = self.actors.spawn_actor_from_class(cls, ue.Vector(0.0, 0.0, 0.0), ue.Rotator(0.0, 0.0, 0.0),
                                                       transient=False)
            if actor is None:
                raise RuntimeError('spawn returned None for ' + label)
            actor.set_actor_label(label)
            actor.set_folder_path(self.spec['folder'])
            actor.set_editor_property('tags', [ue.Name(self.spec['actorTag'])])
            placed.append({'label': label, 'class': class_name, 'kind': 'Actor',
                           'location': [0.0, 0.0, 0.0], 'rotation': [0.0, 0.0, 0.0], 'scale': [1.0, 1.0, 1.0],
                           'actor': actor})
        return {'actors': placed}

    def place_markers(self):
        ue = self.ue
        cfg = self.spec['marker']
        mesh = None
        mesh_path = None
        tried = []
        for candidate in cfg['meshCandidates']:
            try:
                loaded = ue.load_asset(candidate)
            except Exception as error:                       # noqa: BLE001
                tried.append({'asset': candidate, 'error': str(error)})
                continue
            if isinstance(loaded, ue.StaticMesh):
                mesh, mesh_path = loaded, candidate
                break
            tried.append({'asset': candidate, 'error': 'not a StaticMesh'})
        if mesh is None:
            # Not fatal. The tour's on-screen bearing needs no asset at all.
            raise OmissionError('no marker mesh candidate loaded', {'candidates': tried})

        box = mesh.get_bounding_box()
        local = {'min': [box.min.x, box.min.y, box.min.z], 'max': [box.max.x, box.max.y, box.max.z]}
        half = max(abs(v) for v in local['min'] + local['max'])
        scaled_half = half * max(cfg['scale'])
        if scaled_half > cfg['maxHalfExtentCm']:
            raise OmissionError('marker mesh %s is too large at the planned scale (%0.1f cm half-extent)'
                                % (mesh_path, scaled_half), {'localBounds': local, 'scale': cfg['scale']})

        stops = self.tour['stops']
        rows = []
        placed = []
        for stop in stops:
            label = marker_label(self.spec, stop['order'], stop['key'])
            z, method = self.trace_down(stop['stand'][:2], stop['stand'][2])
            location = [float(stop['stand'][0]), float(stop['stand'][1]), z + cfg['zOffsetCm']]
            rows.append({'label': label, 'key': stop['key'], 'order': stop['order'],
                         'jsonZ': float(stop['stand'][2]), 'placedZ': location[2], 'zSource': method})
            if self.dry_run:
                continue
            actor = self.actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(*location),
                                                       ue.Rotator(0.0, 0.0, 0.0), transient=False)
            if actor is None:
                raise RuntimeError('StaticMeshActor spawn returned None for ' + label)
            actor.set_actor_label(label)
            actor.set_folder_path(self.spec['folder'] + '/Markers')
            actor.set_editor_property('tags', [ue.Name(self.spec['actorTag']),
                                               ue.Name(self.spec['markerTag']),
                                               ue.Name(stop['key'])])
            actor.set_actor_scale3d(ue.Vector(*cfg['scale']))
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            if component is None:
                raise RuntimeError('Spawned marker has no StaticMeshComponent: ' + label)
            if not component.set_static_mesh(mesh):
                raise RuntimeError('set_static_mesh returned False for ' + label)
            if _asset_path(component.get_editor_property('static_mesh')) != _asset_path(mesh):
                raise RuntimeError('Static mesh readback differs for ' + label)
            component.set_collision_profile_name(cfg['collisionProfile'])
            component.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
            if cfg['hiddenInGameOnPlace']:
                # The guide unhides only the stop the visitor is heading for.
                actor.set_actor_hidden_in_game(True)
            placed.append({'label': label, 'class': 'StaticMeshActor', 'kind': 'StaticMeshActor',
                           'mesh': mesh_path, 'key': stop['key'],
                           'location': location, 'rotation': [0.0, 0.0, 0.0], 'scale': list(cfg['scale']),
                           'actor': actor})
        return {'actors': placed, 'mesh': mesh_path, 'meshLocalBounds': local, 'markerRows': rows}


def _strip_actor_handles(record):
    return {k: v for k, v in record.items() if k != 'actor'}


def place(load_target=True, groups=GROUP_ORDER, dry_run=False):
    """Run the guarded placement. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    groups = normalise_groups(groups)
    spec = load_spec()
    tour = load_tour(spec)
    offline = offline_check(spec)
    if not offline['ok']:
        raise RuntimeError('Tour content did not pass the offline check; refusing to place. %s'
                           % (offline['routeProblems'] + offline['codexProblems'])[:6])

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    run = TourPlacement(ue, spec, tour, dry_run=dry_run)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    class_report = run.require_classes()
    if load_target:
        if not run.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed placement')

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    external_copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / TARGET[6:]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / TARGET[6:])
            external_copied.append(str(external))

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    run.receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))
    run.receipt = {
        'status': 'tour_placement_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'offlineCheck': offline,
        'runtimeClasses': class_report,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'groupsRequested': list(groups),
        'dryRun': bool(dry_run),
        'preExistingTourActors': [],
        'placed': {},
        'omissions': {},
        'errors': [],
        'mapSaved': False,
        'limitations': spec['limitations'],
    }
    run.write_receipt()

    saved = False
    try:
        run.take_snapshot()
        baseline = run.numeric_baseline(run.snapshot)
        pre_existing = [row for row in run.snapshot
                        if row['label'].startswith(spec['labelPrefix'])
                        or row['folder'].startswith(spec['folder'])
                        or spec['actorTag'] in row['tags']]
        run.receipt['preExistingTourActors'] = [
            {'label': r['label'], 'name': r['name'], 'class': r['class'], 'folder': r['folder'],
             'tags': r['tags'], 'pose': r['pose']} for r in pre_existing]
        if pre_existing and not dry_run:
            raise RuntimeError('Tour actors are already in the map; refusing to double them: %s'
                               % [r['label'] for r in pre_existing][:10])

        run.trace_self_test()
        run.write_receipt()

        results = {}
        runners = {'actors': run.place_actors, 'markers': run.place_markers}
        for group in groups:
            try:
                results[group] = runners[group]()
                run.receipt['placed'][group] = dict(
                    results[group], actors=[_strip_actor_handles(r) for r in results[group]['actors']])
            except OmissionError as omission:
                run.receipt['omissions'][group] = {'reason': str(omission), 'evidence': omission.evidence}
            except Exception as error:                       # noqa: BLE001
                run.receipt['omissions'][group] = {'reason': 'validation_or_api_failure: ' + str(error)}
                run.receipt['errors'].append({'group': group, 'error': repr(error)})
            run.write_receipt()

        placed_records = [record for result in results.values() for record in result['actors']]
        if dry_run:
            run.receipt['status'] = 'dry_run_complete_map_unchanged'
            return run.receipt
        if not placed_records:
            run.receipt['status'] = 'nothing_placed_map_unchanged'
            return run.receipt

        current = run.numeric_baseline(run.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])

        if not run.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()

        if not run.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run.world = run.editor.get_editor_world()
        reopened = run.take_snapshot()
        reopened_numeric = run.numeric_baseline(reopened)
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])

        verify = spec['verification']
        readback = []
        for record in placed_records:
            matching = [row for row in reopened if row['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
            row = matching[0]
            entry = {'label': record['label'], 'class': row['class'], 'folder': row['folder'],
                     'tags': row['tags'], 'meshPath': row['meshes'], 'pose': row['pose'],
                     'worldBoundsCm': row['bounds']}
            error = _pose_error(row['pose'], record['location'], record['rotation'], record['scale'])
            entry['poseErrorCm'] = error
            if error > verify['transformToleranceCm']:
                raise RuntimeError('Reopened transform differs for %s by %.4f' % (record['label'], error))
            if record['kind'] == 'StaticMeshActor':
                if row['meshes'] != [record['mesh']]:
                    raise RuntimeError('Reopened mesh differs for ' + record['label'])
                if spec['markerTag'] not in row['tags'] or record['key'] not in row['tags']:
                    raise RuntimeError('Reopened marker lost its tags: ' + record['label'])
            else:
                if row['class'] != record['class']:
                    raise RuntimeError('Reopened class differs for %s: %s' % (record['label'], row['class']))
            readback.append(entry)
        run.receipt['reopenedReadback'] = readback

        if verify['requireEveryStopHasAMarker'] and 'markers' in results:
            keys_placed = {r['key'] for r in results['markers']['actors']}
            missing = [s['key'] for s in tour['stops'] if s['key'] not in keys_placed]
            if missing:
                raise RuntimeError('Stops without a marker after reopen: %s' % missing[:10])

        run.receipt['status'] = 'tour_placed_saved_reopened_readback_matched'
        return run.receipt
    except Exception as error:                               # noqa: BLE001
        run.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        run.receipt['status'] = ('refused_after_save_checkpoint_available' if saved
                                 else 'refused_before_save_map_unchanged')
        raise
    finally:
        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapBytesChanged'] = run.receipt['mapSha256After'] != map_sha_before
        run.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
        run.receipt['placedActorCount'] = sum(len(g['actors']) for g in run.receipt['placed'].values())
        run.write_receipt()


def _unreal_available():
    try:
        import unreal                                        # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    """True only when the engine itself is executing this file as a script."""
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_tour.py' in command_line and ('-run=pythonscript' in command_line
                                                  or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    groups = GROUP_ORDER
    dry_run = '-tourdryrun' in command_line
    for token in command_line.split():
        if token.startswith('-tourgroups='):
            groups = normalise_groups(token.split('=', 1)[1].strip('"'))
    try:
        receipt = place(load_target=True, groups=groups, dry_run=dry_run)
        ue.log('release_tour: %s groups %s placed %s' % (receipt['status'], list(groups),
                                                         receipt.get('placedActorCount')))
    except Exception as error:                               # noqa: BLE001
        ue.log_error('release_tour failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

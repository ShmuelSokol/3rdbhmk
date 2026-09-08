"""Guarded release placement of the Kohen Gadol lamp-service actor.

Spawns ONE RELEASE_KohenGadolService actor (AMikdashServiceActor, compiled into
MikdashRuntime) into the combined walkthrough map, configured with the station
anchors in Scripts/release_kohen_service.spec.json, then proves numerically that
every station the actor will derive lies inside the measured Heikhal / doorway /
Ulam envelope and that no station reaches the paroches line at X -5600 in the
ordinary-day scenario.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_kohen_service.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-KohenService-01.log"

Run WITHOUT the engine to get the offline check only (no map is touched):

  python Scripts/release_kohen_service.py

Safety model, the same as Scripts/release_place_assets.py:
  * Refuses on the wrong project directory, an active game world, dirty
    packages, or a loaded world that is not the target map.
  * Refuses unless a freshly compiled MikdashRuntime exposing
    AMikdashServiceActor is loaded, and unless that class's own defaults still
    have the sequence switched off.
  * Copies Walkthrough.umap and any One-File-Per-Actor folders to
    ReviewCheckpoints/KohenService-<stamp>/ before any mutation, and verifies
    the copy by hash.
  * Runs the whole station/boundary check offline FIRST. A geometry failure
    raises before anything is spawned.
  * Refuses if a RELEASE_KohenGadolService actor already exists.
  * Saves only if the actor was spawned, reloads the map, and reads every
    written property back numerically.
  * Writes the receipt at start and again in finally, so a failure preserves
    partial state.

UE 5.8 pitfalls this script is built around:
  * A property setter can report failure on an assignment that actually took.
    No setter return value is trusted anywhere below; every write is verified
    by read-back, before the save and again after the reopen.
  * A static-mobility actor does not dirty its package on a transform change.
    This actor's root is Movable by construction and the script never relies on
    a transform edit to mark the map dirty; it checks get_dirty_map_packages()
    explicitly.
  * A "failed" save is often a leftover UnrealEditor / UnrealEditor-Cmd process
    holding the package. The receipt records the process list it observed at
    the moment of the save so that can be told apart from a real failure.

What this does NOT establish: any visual, animation, collision-route, lighting,
packaged or halachic acceptance. The figure is placed but not started
(start_on_begin_play stays False). The source register and the honest
depicted-versus-asserted statement are in
SourceAssets/runtime-review/kohen-service/sources.md.
"""
import hashlib
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_kohen_service.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
LAMP_COUNT = 7


# --------------------------------------------------------------------------
# Pure helpers. Everything below runs with no unreal import so offline_check()
# can be read and re-run by a human anywhere.
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def finite(*values):
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def zone_of(point, env):
    """Mirror of MikdashService::ZoneOf. XY only; height is checked separately.

    Kept as an independent Python implementation on purpose: if it ever
    disagrees with the C++ header, that disagreement is the finding.
    """
    x, y = float(point[0]), float(point[1])
    if not finite(x, y):
        return 'outside'
    abs_y = abs(y)
    inset = env['edgeInsetCm']
    ulam, heikhal, kodesh = env['ulamFloor'], env['heikhalFloor'], env['kodeshFloor']
    if ulam['minX'] + inset <= x <= ulam['maxX'] - inset and abs_y <= ulam['halfY'] - inset:
        return 'ulam'
    if heikhal['maxX'] <= x <= ulam['minX'] + inset and abs_y <= env['doorwayHalfY'] - inset:
        return 'doorway'
    if x > env['kodeshLineX'] + inset and x <= heikhal['maxX'] and abs_y <= heikhal['halfY'] - inset:
        return 'heikhal'
    if kodesh['maxX'] <= x <= env['kodeshLineX'] + inset and abs_y <= env['parochesGapHalfY'] - inset:
        return 'paroches_gap'
    if kodesh['minX'] + inset <= x <= kodesh['maxX'] and abs_y <= kodesh['halfY'] - inset:
        return 'kodesh'
    return 'outside'


def zone_permitted(zone, scenario):
    if zone in ('ulam', 'doorway', 'heikhal'):
        return True
    if zone in ('paroches_gap', 'kodesh'):
        return scenario == 'YOM_KIPPUR'
    return False


def height_permitted(z, env):
    if not finite(z):
        return False
    tol = env['heightToleranceCm']
    return (abs(z - env['heikhalFloor']['topZ']) <= tol
            or abs(z - env['stoneTopZ']) <= tol)


def segment_permitted(a, b, env, scenario, samples=128):
    """Mirror of MikdashService::SegmentPermitted. Returns (ok, reason)."""
    if not finite(*a[:3]) or not finite(*b[:3]):
        return False, 'bad_geometry'
    if scenario == 'ORDINARY_DAY' and min(a[0], b[0]) <= env['kodeshLineX']:
        return False, 'crosses_kodesh_line'
    for step in range(samples + 1):
        t = step / samples
        point = [a[i] + (b[i] - a[i]) * t for i in range(3)]
        zone = zone_of(point, env)
        if zone == 'outside':
            return False, 'outside_reviewed_envelope'
        if not zone_permitted(zone, scenario):
            return False, ('crosses_kodesh_line' if zone in ('paroches_gap', 'kodesh')
                           else 'scenario_forbids_station')
    return True, 'ok'


def derive_stations(props, env, scenario):
    """Mirror of MikdashService::BuildMenorahSequence, from the SAME anchors the
    actor is given. If this and the C++ ever disagree, the reopen read-back of
    station_count and planned_loop_seconds will catch it."""
    approach = list(props['ulam_approach_point'])
    doorway = list(props['doorway_point'])
    stone = list(props['tending_stone_point'])
    altar = list(props['golden_altar_point'])
    menorah = list(props['menorah_point'])
    inner = list(props['inner_stand_point'])

    branch_half_span = 46.95           # SM_MenorahV4_BranchesL/R local X half span
    stone_min_y, stone_max_y = 270.2, 360.2   # SM_MenorahV4_StepStone footprint
    lamp_z = menorah[2] + 150.0        # 18 tefachim at 50 cm/amah

    def lamp_at(k):
        t = k / (LAMP_COUNT - 1)
        return [menorah[0], menorah[1] - branch_half_span + 2.0 * branch_half_span * t, lamp_z]

    def stand_for_lamp(k):
        y = min(max(lamp_at(k)[1], stone_min_y), stone_max_y)
        return [stone[0], y, env['stoneTopZ']]

    first_group = 5   # Rambam, Temidin uMusafin 3:17
    lamp_s = props['per_lamp_seconds']
    out = []

    def add(kind, stand, dwell, lamp_index=-1):
        out.append({'index': len(out), 'kind': kind, 'lampIndex': lamp_index,
                    'stand': [round(float(v), 4) for v in stand], 'dwellSeconds': float(dwell)})

    add('UlamApproach', approach, props['approach_seconds'])
    add('Doorway', doorway, props['doorway_seconds'])
    add('TendingStone', stone, props['stone_seconds'])
    for k in range(first_group):
        add('Lamp', stand_for_lamp(k), lamp_s, k)
    add('KuzOnSecondStep', stone, props['kuz_seconds'])
    add('Doorway', doorway, props['doorway_seconds'])
    add('WithdrawOutside', approach, props['withdraw_seconds'])
    add('Doorway', doorway, props['doorway_seconds'])
    for k in range(first_group, LAMP_COUNT):
        add('Lamp', stand_for_lamp(k), lamp_s, k)
    add('KuzOnSecondStep', stone, props['kuz_seconds'])
    add('GoldenAltar', altar, props['altar_seconds'])
    if scenario == 'YOM_KIPPUR':
        add('InnerEntry', inner, props['inner_seconds'])
        add('InnerExit', [env['kodeshLineX'] + 200.0, 0.0, env['heikhalFloor']['topZ']],
            props['doorway_seconds'])
    add('Doorway', doorway, props['doorway_seconds'])
    add('UlamApproach', approach, props['approach_seconds'])
    return out, [lamp_at(k) for k in range(LAMP_COUNT)]


def distance_2d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def offline_check(spec=None):
    """The whole geometry argument, with no engine. Raises on any failure."""
    spec = spec or load_spec()
    env = spec['envelope']
    props = spec['actorProperties']
    scenario = props['service_scenario']
    if scenario != 'ORDINARY_DAY':
        raise RuntimeError(
            'This script only places the ordinary-day scenario. The Yom Kippur scenario is a '
            'separate, deliberately chosen flag and is not enabled here.')

    stations, lamps = derive_stations(props, env, scenario)
    findings = []

    # 1. Every station is inside the reviewed envelope, at a real standing height.
    for station in stations:
        stand = station['stand']
        zone = zone_of(stand, env)
        if zone == 'outside':
            raise RuntimeError('Station %d (%s) at %r is outside the measured Ulam/doorway/Heikhal floor'
                               % (station['index'], station['kind'], stand))
        if not zone_permitted(zone, scenario):
            raise RuntimeError('Station %d (%s) is in zone %s, which the %s scenario does not permit'
                               % (station['index'], station['kind'], zone, scenario))
        if not height_permitted(stand[2], env):
            raise RuntimeError('Station %d (%s) at Z %.3f is neither on the reviewed floor (%.1f) '
                               'nor on the three-step stone (%.1f)'
                               % (station['index'], station['kind'], stand[2],
                                  env['heikhalFloor']['topZ'], env['stoneTopZ']))
        station['zone'] = zone

    # 2. The hard boundary. No station reaches X -5600 on an ordinary day.
    line = env['kodeshLineX']
    for station in stations:
        if station['stand'][0] <= line:
            raise RuntimeError(
                'Station %d (%s) at X %.3f reaches the paroches line at %.1f. The Kodesh HaKodashim '
                'is entered only on Yom Kippur (Vayikra 16:2; Rambam, Biat HaMikdash 2:1).'
                % (station['index'], station['kind'], station['stand'][0], line))
    closest = min(s['stand'][0] for s in stations)
    findings.append('Closest approach to the paroches line: X %.3f, which is %.3f cm east of %.1f.'
                    % (closest, closest - line, line))

    # 3. Every straight leg between consecutive stations is permitted too, so a
    #    leg cannot cut a corner through a wall between two legal stations.
    for i in range(1, len(stations)):
        ok, reason = segment_permitted(stations[i - 1]['stand'], stations[i]['stand'], env, scenario)
        if not ok:
            raise RuntimeError('The straight leg from station %d to station %d is refused: %s'
                               % (i - 1, i, reason))

    # 4. The sequence is a closed loop, so the interval restart cannot teleport.
    if distance_2d(stations[0]['stand'], stations[-1]['stand']) > 1.0:
        raise RuntimeError('The sequence does not end where it began; restarting it would teleport the figure.')

    # 5. All seven lamps are tended, five then two.
    tended = sorted({s['lampIndex'] for s in stations if s['kind'] == 'Lamp'})
    if tended != list(range(LAMP_COUNT)):
        raise RuntimeError('The sequence tends lamps %r, not all seven' % tended)
    withdraw_at = [s['index'] for s in stations if s['kind'] == 'WithdrawOutside']
    if len(withdraw_at) != 1:
        raise RuntimeError('Expected exactly one withdrawal between the two groups of lamps')
    before = [s for s in stations if s['kind'] == 'Lamp' and s['index'] < withdraw_at[0]]
    after = [s for s in stations if s['kind'] == 'Lamp' and s['index'] > withdraw_at[0]]
    if len(before) != 5 or len(after) != 2:
        raise RuntimeError('Expected five lamps, a withdrawal, then two (Rambam, Temidin uMusafin 3:17); '
                           'got %d then %d' % (len(before), len(after)))
    last_lamp = max(s['index'] for s in stations if s['kind'] == 'Lamp')
    altar_at = [s['index'] for s in stations if s['kind'] == 'GoldenAltar']
    if len(altar_at) != 1 or altar_at[0] < last_lamp:
        raise RuntimeError('The incense station must follow the last lamp')

    # 6. The stone really is east of the menorah, and the lamps are on its axis.
    if props['tending_stone_point'][0] <= props['menorah_point'][0]:
        raise RuntimeError('The three-step stone must stand east of the menorah (Rambam, Beit HaBechirah 3:11)')
    if any(abs(p[0] - props['menorah_point'][0]) > 1e-6 for p in lamps):
        raise RuntimeError('The seven lamps must sit on the menorah axis in X')

    # 7. Duration.
    speed = props['walk_speed_cm_per_sec']
    if not finite(speed) or speed <= 0:
        raise RuntimeError('walk_speed_cm_per_sec must be a positive number')
    walk = sum(distance_2d(stations[i - 1]['stand'], stations[i]['stand']) for i in range(1, len(stations))) / speed
    dwell = sum(s['dwellSeconds'] for s in stations)
    loop = walk + dwell
    low, high = props['min_loop_seconds'], props['max_loop_seconds']
    if not low <= loop <= high:
        raise RuntimeError('The loop lasts %.2f s, outside the configured window %.0f..%.0f s' % (loop, low, high))
    findings.append('Loop: %.2f s walking + %.2f s standing = %.2f s (%.2f minutes), inside %.0f..%.0f s.'
                    % (walk, dwell, loop, loop / 60.0, low, high))

    # 8. The offline derivation must reproduce the numbers written in the spec,
    #    so the reviewable plan in the spec is not allowed to drift.
    expected = spec['expectedDerivedPlan']
    if len(stations) != expected['stationCount']:
        raise RuntimeError('Derived %d stations, spec says %d' % (len(stations), expected['stationCount']))
    if abs(loop - expected['loopSeconds']) > 0.01:
        raise RuntimeError('Derived loop %.4f s, spec says %.4f s' % (loop, expected['loopSeconds']))
    for got, want in zip(stations, expected['stations']):
        if got['kind'] != want['kind'] or got['lampIndex'] != want['lampIndex']:
            raise RuntimeError('Station %d differs from the spec' % got['index'])
        if max(abs(a - b) for a, b in zip(got['stand'], want['stand'])) > 0.001:
            raise RuntimeError('Station %d position %r differs from the spec %r'
                               % (got['index'], got['stand'], want['stand']))

    return {
        'status': 'offline_geometry_verified',
        'scenario': scenario,
        'stationCount': len(stations),
        'stations': stations,
        'lampWorldPoints': [[round(v, 4) for v in p] for p in lamps],
        'walkSeconds': round(walk, 4),
        'dwellSeconds': round(dwell, 4),
        'loopSeconds': round(loop, 4),
        'closestApproachToKodeshLineX': round(closest, 4),
        'kodeshLineX': line,
        'findings': findings,
        'specSha256': sha256_of(SPEC_PATH),
        'notEstablished': spec['limitations'],
    }


def running_editor_processes():
    """Zombie check. A 'failed' save is often a leftover editor holding the file."""
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UnrealEditor*.exe', '/NH'],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception as error:                                   # noqa: BLE001
        return ['tasklist_failed: ' + repr(error)]
    rows = [line.strip() for line in out.splitlines() if line.strip()
            and 'UnrealEditor' in line]
    return rows


# --------------------------------------------------------------------------
# Native (inside the editor)
# --------------------------------------------------------------------------

def _vector_list(v):
    return [float(v.x), float(v.y), float(v.z)]


def _scene_snapshot(ue, actors):
    snapshot = {}
    for actor in actors.get_all_level_actors():
        if not actor:
            continue
        origin, extent = actor.get_actor_bounds(False)
        snapshot[actor.get_name()] = {
            'label': actor.get_actor_label(),
            'folder': str(actor.get_folder_path()),
            'location': [round(v, 3) for v in _vector_list(actor.get_actor_location())],
            'rotation': [round(v, 3) for v in (actor.get_actor_rotation().pitch,
                                               actor.get_actor_rotation().yaw,
                                               actor.get_actor_rotation().roll)],
            'boundsOrigin': [round(v, 3) for v in _vector_list(origin)],
            'boundsExtent': [round(v, 3) for v in _vector_list(extent)],
        }
    return snapshot


def _require_fresh_binary(ue, spec):
    required = spec['compiledClassesRequired']
    service_class = ue.load_class(None, required['serviceActor'])
    if not service_class:
        raise RuntimeError(
            'AMikdashServiceActor is not loaded. Compile MikdashRuntime (the coordinator must build '
            'MikdashServiceActor.h/.cpp and ServiceScheduleMath.h into the module) and restart the '
            'editor process before running this script.')
    cdo = ue.get_default_object(service_class)
    try:
        cdo.get_editor_property(required['propertyProvingFreshBinary'])
    except Exception as error:                                   # noqa: BLE001
        raise RuntimeError('AMikdashServiceActor lacks %s: stale binary (%r)'
                           % (required['propertyProvingFreshBinary'], error))
    for name, must_be in required['defaultsThatMustRemainOff'].items():
        actual = cdo.get_editor_property(name)
        if bool(actual) is not bool(must_be):
            raise RuntimeError('Class default %s is %r; it must stay %r so placement alone never animates anything'
                               % (name, actual, must_be))
    return service_class


def _write_properties(ue, actor, props):
    """Write every property, then read every one back. No setter return value is
    trusted: UE 5.8 setters can report failure on an assignment that took."""
    vector_keys = {'ulam_approach_point', 'doorway_point', 'tending_stone_point',
                   'golden_altar_point', 'menorah_point', 'inner_stand_point'}
    for name, value in props.items():
        if name == 'service_scenario':
            actor.set_editor_property(name, getattr(ue.MikdashServiceScenario, value))
        elif name in vector_keys:
            actor.set_editor_property(name, ue.Vector(*[float(v) for v in value]))
        else:
            actor.set_editor_property(name, value)
    return _read_properties(ue, actor, props)


def _read_properties(ue, actor, props):
    vector_keys = {'ulam_approach_point', 'doorway_point', 'tending_stone_point',
                   'golden_altar_point', 'menorah_point', 'inner_stand_point'}
    out = {}
    for name in props:
        value = actor.get_editor_property(name)
        if name in vector_keys:
            out[name] = [round(v, 4) for v in _vector_list(value)]
        elif name == 'service_scenario':
            out[name] = str(value).rsplit('.', 1)[-1].replace('MikdashServiceScenario', '').strip('. ')
        elif isinstance(value, bool):
            out[name] = bool(value)
        else:
            out[name] = float(value)
    return out


def _compare_properties(read_back, props, spec, where):
    tol_v = spec['verification']['vectorToleranceCm']
    tol_s = spec['verification']['scalarTolerance']
    problems = []
    for name, want in props.items():
        got = read_back.get(name)
        if name == 'service_scenario':
            if str(got).upper().replace('_', '') != str(want).upper().replace('_', ''):
                problems.append('%s = %r, wanted %r' % (name, got, want))
        elif isinstance(want, bool):
            if bool(got) is not bool(want):
                problems.append('%s = %r, wanted %r' % (name, got, want))
        elif isinstance(want, list):
            if got is None or max(abs(a - b) for a, b in zip(got, want)) > tol_v:
                problems.append('%s = %r, wanted %r' % (name, got, want))
        else:
            if got is None or abs(float(got) - float(want)) > tol_s:
                problems.append('%s = %r, wanted %r' % (name, got, want))
    if problems:
        raise RuntimeError('Property read-back %s disagrees with the spec: %s' % (where, problems))


def place(load_target=True):
    """Run the guarded placement. Returns the receipt dict; raises on any guard."""
    import unreal as ue

    spec = load_spec()
    offline = offline_check(spec)

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())

    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)

    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target and not levels.load_level(TARGET):
        raise RuntimeError('load_level failed for ' + TARGET)
    world = editor.get_editor_world()
    loaded = world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed placement')

    service_class = _require_fresh_binary(ue, spec)

    conf = spec['actor']
    if conf['refuseIfLabelExists']:
        existing = [a.get_actor_label() for a in actors.get_all_level_actors()
                    if a and a.get_actor_label() == conf['label']]
        if existing:
            raise RuntimeError('%s already exists; refusing duplicate placement' % conf['label'])

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps']
                 if disk_path(m, 'umap').exists()}
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
    receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(receipt_path))

    receipt = {
        'status': 'checkpointed_placement_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'offlineGeometryCheck': offline,
        'sourceRegister': 'SourceAssets/runtime-review/kohen-service/sources.md',
        'standaloneTests': 'SourceAssets/runtime-review/kohen-service/tests.json',
        'sourceDecisions': {
            'kohenGadolMayPerformThisService':
                'Mishnah Yoma 1:2 printed on Yoma 14a names hatavat ha-nerot among the services the '
                'Kohen Gadol performs, and says that on other days he offers whatever he wishes; '
                'Rambam, Klei HaMikdash 5:12 adds that he does not enter the lottery. (The brief '
                'cited 5:11; 5:11 is his entry to the Heikhal to prostrate. Both are cited in code.)',
            'ordinarilyAnOrdinaryKohen':
                'Rambam, Biat HaMikdash 2:1: an ordinary priest enters the Heikhal for service every day.',
            'mayWalkTheHeikhalForService':
                'Rambam, Klei HaMikdash 5:11 has him entering the Heikhal in the ephod; Biat '
                'HaMikdash 2:2 warns against entering when not in the midst of service, so the '
                'actor has no idle wander state.',
            'kodeshHaKodashimBoundary':
                'Vayikra 16:2 and Rambam, Biat HaMikdash 2:1: only on Yom Kippur. Enforced here at '
                'X -5600 offline, in ServiceScheduleMath before the sequence starts, and again on '
                'every single move at run time.',
            'threeStepStone': 'Rambam, Beit HaBechirah 3:11.',
            'fiveThenTwoWithTheKuz': 'Rambam, Temidin uMusafin 3:17.',
            'whatHatavahMeans': 'Rambam, Temidin uMusafin 3:11-3:12 (half a log of oil; kindling is hatavah). '
                                'Other authorities read hatavah as cleaning only: recorded as disputed.',
            'lampsFaceTheCentre': 'Rambam, Beit HaBechirah 3:8 (the brief cited 3:12, which is the Shulchan).',
            'lampTendingOrder': 'AUTHORED PLACEHOLDER. No source consulted names which five and which two. '
                                'Must not be taught as the order of the service.',
        },
        'limitations': spec['limitations'],
        'placed': None,
        'errors': [],
        'mapSaved': False,
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')

    write()
    saved = False
    spawned = None
    try:
        before = _scene_snapshot(ue, actors)

        spawned = actors.spawn_actor_from_class(
            service_class, ue.Vector(*[float(v) for v in conf['spawnLocation']]),
            ue.Rotator(), transient=False)
        if not spawned:
            raise RuntimeError('Service actor spawn failed')
        spawned.set_actor_label(conf['label'])
        spawned.set_folder_path(conf['folder'])
        spawned.tags = [ue.Name(conf['tag'])]
        spawned_name = spawned.get_name()

        props = spec['actorProperties']
        read_back = _write_properties(ue, spawned, props)
        _compare_properties(read_back, props, spec, 'before the save')
        receipt['placed'] = {
            'label': conf['label'],
            'name': spawned_name,
            'folder': conf['folder'],
            'class': spec['compiledClassesRequired']['serviceActor'],
            'spawnLocation': [float(v) for v in conf['spawnLocation']],
            'propertiesReadBackBeforeSave': read_back,
        }
        spawned.modify()
        write()

        after = _scene_snapshot(ue, actors)
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        if changed - {spawned_name}:
            raise RuntimeError('Unexpected scene changes beyond the new actor: %r'
                               % sorted(changed - {spawned_name})[:10])
        receipt['sceneChanges'] = sorted(changed)

        # UE 5.8: the spawn itself dirties the map. Prove it rather than assume,
        # because a static-mobility actor would not have dirtied it on a
        # transform edit alone and this check is what would catch that.
        if not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('The map is not dirty after the spawn; nothing would be saved')

        receipt['editorProcessesAtSave'] = running_editor_processes()
        if not levels.save_current_level():
            raise RuntimeError(
                'save_current_level returned False. Before treating this as a real failure, check '
                'the process list recorded in editorProcessesAtSave for a leftover UnrealEditor '
                'holding the package: %r' % receipt['editorProcessesAtSave'])
        saved = True
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha256_of(map_file)
        write()

        if not levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Reopened world is not the target map')

        matching = [a for a in actors.get_all_level_actors()
                    if a and a.get_actor_label() == conf['label']]
        if len(matching) != 1:
            raise RuntimeError('Reopened actor count for %s is %d' % (conf['label'], len(matching)))
        reopened = matching[0]
        if not reopened.get_class().get_name().startswith('MikdashServiceActor'):
            raise RuntimeError('Reopened actor class is %s' % reopened.get_class().get_name())

        reopened_props = _read_properties(ue, reopened, props)
        _compare_properties(reopened_props, props, spec, 'after the reopen')

        tol = spec['verification']['transformToleranceCm']
        location = _vector_list(reopened.get_actor_location())
        if max(abs(a - b) for a, b in zip(location, conf['spawnLocation'])) > tol:
            raise RuntimeError('Reopened location %r differs from %r' % (location, conf['spawnLocation']))

        receipt['reopenedReadback'] = {
            'label': reopened.get_actor_label(),
            'name': reopened.get_name(),
            'class': reopened.get_class().get_name(),
            'folder': str(reopened.get_folder_path()),
            'tags': [str(t) for t in reopened.tags],
            'location': [round(v, 4) for v in location],
            'properties': reopened_props,
        }
        # The compiled actor's own read-only view of the plan it will run, which
        # is the numeric cross-check against this script's offline derivation.
        try:
            receipt['reopenedReadback']['scenarioDescription'] = str(reopened.get_scenario_description())
            receipt['reopenedReadback']['serviceStatus'] = str(reopened.get_service_status())
            receipt['reopenedReadback']['currentActionText'] = str(reopened.get_current_action_text())
        except Exception as error:                               # noqa: BLE001
            receipt['errors'].append({'stage': 'blueprint_pure_readback', 'error': repr(error)})

        receipt['status'] = 'kohen_service_actor_saved_reopened_visual_runtime_acceptance_pending'
        return receipt
    except Exception as error:                                   # noqa: BLE001
        receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                             else 'failed_before_save_map_unchanged')
        if not saved and spawned:
            try:
                actors.destroy_actor(spawned)
                receipt['partialActorDestroyed'] = True
            except Exception as cleanup:                         # noqa: BLE001
                receipt['errors'].append({'stage': 'cleanup', 'error': repr(cleanup)})
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
        receipt['editorProcessesAtEnd'] = running_editor_processes()
        write()


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    """True only when the engine itself is executing this file as a script."""
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return ('release_kohen_service.py' in command_line
            and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line))


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    try:
        receipt = place(load_target=True)
        ue.log('release_kohen_service: %s (%d stations, loop %.1f s)'
               % (receipt['status'], receipt['offlineGeometryCheck']['stationCount'],
                  receipt['offlineGeometryCheck']['loopSeconds']))
    except Exception as error:                                   # noqa: BLE001
        ue.log_error('release_kohen_service failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2, ensure_ascii=False))
elif _invoked_as_native_script():
    _main()

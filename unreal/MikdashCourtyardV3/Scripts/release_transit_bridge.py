"""Place ONE AMikdashTransitBoardingBridge in the combined Walkthrough map and wire it to the
single placed AMikdashTransit and AMikdashCrowdField.

COMMANDLET-SAFE. Nothing here traces, plays or renders: it loads the map, checks guards,
checkpoints the umap, spawns the actor, sets and reads back every property, saves, reopens
the map in the same process and reads everything back again, then writes a receipt. It is
the same guarded shape as Scripts/release_place_assets.py and release_transit_v3.py.

    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Scripts\\release_transit_bridge.py
        -unattended -nullrhi -abslog=<unique log>

    python Scripts\\release_transit_bridge.py           (no engine: offline consistency check only)

Environment:
    MIKDASH_BRIDGE_DRY_RUN=1        run every guard and the checkpoint, spawn nothing, save nothing
    MIKDASH_BRIDGE_ALLOW_LOAD_MAP=0 refuse instead of loading the target map when another is open

Guards, all fatal before any mutation: exact project directory; exact target map; no game
world; no dirty packages; the bridge class is compiled and loadable; exactly one placed
transit actor and exactly one placed crowd field; no existing bridge actor (class or label);
no AMikdashTransitCrowdCoordinator with activate_on_begin_play (see the spec); protected
maps' SHA-256 unchanged after the run.

Not a claim of visual acceptance or of any figure boarding anything: that needs a real-RHI
PIE run with the transit actor active, read back through the bridge's GetBridgeSummary().
"""
import hashlib
import json
import math
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_transit_bridge.spec.json'
TARGET_MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
MAP_FILE = ROOT / 'Content' / 'MikdashV3' / 'IntegratedReviewV2' / 'Maps' / 'Walkthrough.umap'
sys.path.insert(0, str(ROOT / 'Scripts'))
from release_place_assets import snapshot_row, diff_baselines, baseline_exclusions


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


def dwell_window(seconds_available, close_margin):
    """Mirror of MikdashBoardingBridge::DwellWindow, for the offline report only."""
    if seconds_available < 4.0:
        return None
    alight_end = seconds_available * 0.45
    deadline = seconds_available - close_margin
    if deadline <= alight_end + 0.5:
        return None
    return {'alightEnd': alight_end, 'boardStart': alight_end, 'deadline': deadline}


def door_throughput(phase_seconds, doors, seconds_per_person):
    if phase_seconds <= 0 or doors <= 0 or seconds_per_person <= 0:
        return 0
    return int(math.floor(phase_seconds / seconds_per_person)) * doors


def offline_check(spec=None):
    """Engine-free consistency checks; raises on the first failure."""
    spec = spec or load_spec()
    bridge = spec['bridgeActor']
    report = {'spec': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'invariants': {}}

    def require(name, condition, detail):
        report['invariants'][name] = {'ok': bool(condition), 'detail': detail}
        if not condition:
            raise RuntimeError('Spec invariant failed: %s (%s)' % (name, detail))

    cap, pool, per_group = bridge['max_concurrent_groups'], bridge['max_figures'], bridge['max_people_per_group']
    require('poolCoversCap', pool >= cap * per_group, '%d >= %d * %d' % (pool, cap, per_group))
    require('capRange', 1 <= cap <= 32, str(cap))
    require('poolRange', 8 <= pool <= 1024, str(pool))
    require('perGroupRange', 1 <= per_group <= 200, str(per_group))
    require('minGroupRange', 1 <= bridge['min_people_per_group'] <= 10, str(bridge['min_people_per_group']))
    require('budgetRange', 1 <= bridge['update_budget'] <= 1024, str(bridge['update_budget']))
    require('doorsRange', 1 <= bridge['doors_per_vehicle'] <= 6, str(bridge['doors_per_vehicle']))
    require('gatherClearance', bridge['gather_near_cm'] - 25.0 >= bridge['door_clearance_cm'],
            '%.1f - 25 >= %.1f' % (bridge['gather_near_cm'], bridge['door_clearance_cm']))
    require('gatherOrder', bridge['gather_far_cm'] >= bridge['gather_near_cm'], 'far >= near')
    require('fanClearance', 0.34 * bridge['dispersal_min_cm'] >= bridge['door_clearance_cm'],
            '0.34 * %.1f >= %.1f' % (bridge['dispersal_min_cm'], bridge['door_clearance_cm']))
    require('photoClearance', 0.34 * bridge['photo_spot_min_cm'] >= bridge['door_clearance_cm'],
            '0.34 * %.1f >= %.1f' % (bridge['photo_spot_min_cm'], bridge['door_clearance_cm']))
    require('dispersalOrder', bridge['dispersal_max_cm'] >= bridge['dispersal_min_cm'], 'max >= min')
    require('photoOrder', bridge['photo_spot_max_cm'] >= bridge['photo_spot_min_cm'], 'max >= min')
    require('walkSpeeds', 0 < bridge['walk_speed_min_cm_per_second'] <= bridge['walk_speed_max_cm_per_second'], 'min <= max, positive')
    require('holds', 1.0 <= bridge['photographer_hold_min_seconds'] <= bridge['photographer_hold_max_seconds'], 'min <= max')
    require('closeMargin', 0.0 <= bridge['close_margin_seconds'] <= 5.0, str(bridge['close_margin_seconds']))
    require('secondsPerPerson', 0.2 <= bridge['seconds_per_person_per_door'] <= 5.0, str(bridge['seconds_per_person_per_door']))
    require('scales', 0.5 <= bridge['figure_scale_min'] <= bridge['figure_scale_max'] <= 1.5, 'min <= max')
    focus = spec['mountFocusCm']
    require('mountFocusFinite', len(focus) == 3 and all(math.isfinite(v) for v in focus), str(focus))
    for key in ('activate_on_begin_play', 'auto_find_actors', 'refuse_if_coordinator_active',
                'trace_ground', 'sweep_static_obstacles', 'cast_shadows'):
        require('bool:' + key, isinstance(bridge[key], bool), repr(bridge[key]))

    # Per-stop report: what the transit layer can ask for versus what the bridge animates
    # at each stop's minimum authored dwell. Report only; the pool and cap are the bounds.
    routes_path = ROOT / spec['routesFile']
    stops = []
    if routes_path.exists():
        routes = json.loads(routes_path.read_text(encoding='utf-8-sig'))
        for route in routes['routes']:
            for stop in route['stops']:
                dwell = stop.get('dwellMinSeconds', 20.0)
                window = dwell_window(dwell, bridge['close_margin_seconds'])
                boarding_phase = (window['deadline'] - window['boardStart']) if window else 0.0
                alight_phase = window['alightEnd'] if window else 0.0
                board = min(stop['boardingMaxPeople'], per_group,
                            door_throughput(boarding_phase, bridge['doors_per_vehicle'], bridge['seconds_per_person_per_door']))
                alight = min(stop['boardingMaxPeople'], per_group,
                             door_throughput(alight_phase, bridge['doors_per_vehicle'], bridge['seconds_per_person_per_door']))
                stops.append({'route': route['id'], 'stop': stop['name'], 'dwellMinSeconds': dwell,
                              'requestedMax': stop['boardingMaxPeople'], 'boardersAnimatedAtMinDwell': board,
                              'alightersAnimatedAtMinDwell': alight, 'windowUsable': window is not None})
        report['routesSha256'] = sha256_of(routes_path)
    report['stops'] = stops
    report['stopCount'] = len(stops)
    return report


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


# --------------------------------------------------------------------------
# The engine job
# --------------------------------------------------------------------------

class BridgeJob(object):
    def __init__(self, ue, spec):
        self.ue = ue
        self.spec = spec
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.dry_run = os.environ.get('MIKDASH_BRIDGE_DRY_RUN', '0') == '1'
        self.stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.receipt = None
        self.receipt_path = None
        self.map_sha_before = None
        self.protected_before = {}
        self.references = {}
        self.reference_names = {}
        self.placed = None
        self.actor_count_before = None
        self.before_rows = []

    # -- receipt -------------------------------------------------------------

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    def event(self, kind, **data):
        data.update(kind=kind, at=datetime.now(timezone.utc).isoformat())
        self.receipt['events'].append(data)
        self.write_receipt()

    def current_map(self):
        world = self.editor.get_editor_world()
        return world.get_path_name().split('.')[0] if world is not None else ''

    def load_class(self, python_name, path):
        cls = getattr(self.ue, python_name, None)
        if cls is None:
            cls = self.ue.load_class(None, path)
        return cls

    # -- guards --------------------------------------------------------------

    def all_protected_maps(self):
        # Protect every other map, including maps added after the authored spec.
        maps = set(self.spec['protectedMaps'])
        maps.update('/Game/' + p.relative_to(ROOT / 'Content').with_suffix('').as_posix()
                    for p in (ROOT / 'Content').rglob('*.umap'))
        maps.discard(TARGET_MAP)
        return sorted(maps)

    def begin_receipt(self):
        ue = self.ue
        spec = self.spec
        self.map_sha_before = sha256_of(MAP_FILE)
        self.protected_before = {m: sha256_of(disk_path(m, 'umap'))
                                 for m in self.all_protected_maps()}
        folder = ROOT / spec['receiptFolder']
        folder.mkdir(parents=True, exist_ok=True)
        self.receipt_path = folder / (spec['receiptPrefix'] + self.stamp + '.json')
        if self.receipt_path.exists():
            raise RuntimeError('Receipt already exists: ' + str(self.receipt_path))
        self.receipt = {
            'status': 'running', 'stamp': self.stamp, 'map': TARGET_MAP, 'mapFile': str(MAP_FILE),
            'mapSha256Before': self.map_sha_before, 'mapLoadedByJob': False,
            'protectedMapSha256Before': self.protected_before,
            'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
            'offlineCheck': None,
            'engineVersion': ue.SystemLibrary.get_engine_version(),
            'commandLine': ue.SystemLibrary.get_command_line(),
            'dryRun': self.dry_run,
            'scope': spec['scope'],
            'events': [], 'errors': [], 'guards': {}, 'placed': None, 'mapSaved': False,
        }
        self.write_receipt()

    def preflight(self):
        ue = self.ue
        spec = self.spec
        self.receipt['offlineCheck'] = offline_check(spec)
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project: ' + ue.Paths.project_dir())
        if self.editor.get_game_world():
            raise RuntimeError('PIE already running; stop it first (user PIE preserved)')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present; save or revert first (nothing is auto-saved)')
        loaded_by_job = False
        if self.current_map() != TARGET_MAP:
            if os.environ.get('MIKDASH_BRIDGE_ALLOW_LOAD_MAP', '1') != '1':
                raise RuntimeError('Wrong map %s; expected %s' % (self.current_map(), TARGET_MAP))
            if not self.levels.load_level(TARGET_MAP):
                raise RuntimeError('load_level failed for ' + TARGET_MAP)
            loaded_by_job = True
        if self.current_map() != TARGET_MAP:
            raise RuntimeError('Map assertion failed after load: ' + self.current_map())

        self.receipt['mapLoadedByJob'] = loaded_by_job
        self.check_level()

    def check_level(self):
        """The class must be compiled, the two partners placed once each, no bridge yet, no
        active coordinator. Records the names so the readback can compare them."""
        ue = self.ue
        spec = self.spec
        bridge_class = self.load_class(spec['actorPythonName'], spec['actorClass'])
        if bridge_class is None:
            raise RuntimeError('Bridge class not loaded; compile MikdashRuntime first: ' + spec['actorClass'])
        actors = list(self.actors.get_all_level_actors())
        self.actor_count_before = len(actors)
        guards = self.receipt['guards']
        guards['actorCountBefore'] = len(actors)

        existing = [a for a in actors if ue.MathLibrary.class_is_child_of(a.get_class(), bridge_class) or a.get_actor_label() == spec['actorLabel']]
        guards['existingBridgeActors'] = [a.get_actor_label() for a in existing]
        if existing:
            raise RuntimeError('A bridge actor is already placed; do not duplicate: ' + ', '.join(guards['existingBridgeActors']))

        for key, required in spec['requiredActors'].items():
            cls = self.load_class(required['pythonName'], required['class'])
            if cls is None:
                raise RuntimeError('Class not loaded: ' + required['class'])
            matches = [a for a in actors if ue.MathLibrary.class_is_child_of(a.get_class(), cls)]
            guards[key] = [a.get_actor_label() for a in matches]
            if required.get('exactlyOne') and len(matches) != 1:
                raise RuntimeError('Exactly one placed %s is required, found %d' % (required['pythonName'], len(matches)))
            self.references[required['property']] = matches[0]
            self.reference_names[required['property']] = matches[0].get_name()

        guard = spec['coordinatorGuard']
        coordinator_class = self.load_class(guard['pythonName'], guard['class'])
        if coordinator_class is None:
            raise RuntimeError('Coordinator guard class missing: ' + guard['class'])
        coordinators = [a for a in actors if ue.MathLibrary.class_is_child_of(a.get_class(), coordinator_class)]
        active = []
        for actor in coordinators:
            try:
                if bool(actor.get_editor_property('activate_on_begin_play')):
                    active.append(actor.get_actor_label())
            except Exception as error:  # noqa: BLE001
                raise RuntimeError('Coordinator activation readback failed for ' + actor.get_actor_label()) from error
        guards['coordinators'] = [a.get_actor_label() for a in coordinators]
        guards['coordinatorsActivateOnBeginPlay'] = active
        if active and guard.get('refuseIfActivateOnBeginPlay', True):
            raise RuntimeError('An active AMikdashTransitCrowdCoordinator is placed (%s); both would animate every exchange twice'
                               % ', '.join(active))
        self.before_rows = [snapshot_row(ue, a, TARGET_MAP) for a in actors]
        guards['snapshotExclusions'] = baseline_exclusions(self.before_rows)
        self.write_receipt()

    # -- mutation ------------------------------------------------------------

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
        self.event('checkpoint', folder=str(folder))

    def _apply_and_readback(self, actor):
        """Set every spec property and read it straight back: set_editor_property does not
        raise on a clamped or refused value, it just keeps the old one."""
        ue = self.ue
        spec = self.spec
        settings = spec['bridgeActor']
        tolerance = spec['verification']['floatTolerance']
        readback = {}
        for key, value in settings.items():
            actor.set_editor_property(key, value)
            got = actor.get_editor_property(key)
            readback[key] = got
            if isinstance(value, bool):
                if bool(got) != value:
                    raise RuntimeError('%s read back as %s, set %s' % (key, got, value))
            elif isinstance(value, int):
                if int(got) != value:
                    raise RuntimeError('%s read back as %s, set %s' % (key, got, value))
            elif abs(float(got) - value) > tolerance:
                raise RuntimeError('%s read back as %s, set %s' % (key, got, value))
        focus = spec['mountFocusCm']
        actor.set_editor_property('mount_focus_cm', ue.Vector(*focus))
        got = actor.get_editor_property('mount_focus_cm')
        if max(abs(got.x - focus[0]), abs(got.y - focus[1]), abs(got.z - focus[2])) > tolerance:
            raise RuntimeError('mount_focus_cm read back as %s' % (got,))
        readback['mount_focus_cm'] = [got.x, got.y, got.z]
        for prop, reference in self.references.items():
            actor.set_editor_property(prop, reference)
            back = actor.get_editor_property(prop)
            if back is None or back.get_name() != self.reference_names[prop]:
                raise RuntimeError('Reference %s read back as %s' % (prop, back))
        return readback

    def spawn(self):
        ue = self.ue
        spec = self.spec
        bridge_class = self.load_class(spec['actorPythonName'], spec['actorClass'])
        location = ue.Vector(*spec['actorLocationCm'])
        actor = self.actors.spawn_actor_from_class(bridge_class, location, ue.Rotator(0, 0, 0), transient=False)
        if actor is None:
            raise RuntimeError('spawn_actor_from_class returned None for ' + spec['actorClass'])
        try:
            actor.set_actor_label(spec['actorLabel'])
            actor.set_folder_path(spec['folder'])
            actor.set_editor_property('tags', [ue.Name(spec['actorTag']), ue.Name(spec['groupTag'])])
            readback = self._apply_and_readback(actor)
            self.placed = {
                'label': spec['actorLabel'], 'class': spec['actorClass'], 'folder': spec['folder'],
                'location': list(spec['actorLocationCm']), 'rotation': [0.0, 0.0, 0.0],
                'properties': {k: (float(v) if isinstance(v, float) else v) for k, v in readback.items()},
                'references': dict(self.reference_names),
            }
            self.receipt['placed'] = self.placed
            self.event('spawned', label=spec['actorLabel'])
        except Exception:
            try:
                self.actors.destroy_actor(actor)
            except Exception as error:  # noqa: BLE001
                self.receipt['errors'].append('cleanup: ' + str(error))
            raise
        return actor

    def place_and_save(self):
        ue = self.ue
        if self.editor.get_game_world() is not None:
            raise RuntimeError('Game world present; refusing to mutate')
        if self.current_map() != TARGET_MAP:
            raise RuntimeError('Editor map changed to ' + self.current_map())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present before placement; refusing to save foreign edits')
        if sha256_of(MAP_FILE) != self.map_sha_before:
            raise RuntimeError('Map file changed on disk during the run')
        self.checkpoint()
        if self.dry_run:
            self.event('dry_run', note='guards and checkpoint passed; nothing spawned, nothing saved')
            return
        self.spawn()
        if not self.levels.save_current_level():
            raise RuntimeError('save_current_level returned False; inspect process ownership before retry')
        self.receipt['mapSaved'] = True
        self.receipt['mapSha256AfterSave'] = sha256_of(MAP_FILE)
        self.event('saved', sha256=self.receipt['mapSha256AfterSave'])

    # -- readback ------------------------------------------------------------

    def reopen_and_readback(self):
        ue = self.ue
        spec = self.spec
        if not self.levels.load_level(TARGET_MAP):
            raise RuntimeError('Reopen failed')
        if self.current_map() != TARGET_MAP:
            raise RuntimeError('Reopened world is ' + self.current_map())
        bridge_class = self.load_class(spec['actorPythonName'], spec['actorClass'])
        actors = list(self.actors.get_all_level_actors())
        matches = [a for a in actors if a.get_actor_label() == spec['actorLabel']]
        if bridge_class is None or len(matches) != 1 or not ue.MathLibrary.class_is_child_of(matches[0].get_class(), bridge_class):
            raise RuntimeError('Reopened actor mismatch: %d matches' % len(matches))
        actor = matches[0]
        if str(actor.get_folder_path()) != spec['folder']:
            raise RuntimeError('Reopened bridge folder differs')
        if set(str(t) for t in actor.get_editor_property('tags')) != {spec['actorTag'], spec['groupTag']}:
            raise RuntimeError('Reopened bridge tags differ')
        verify = spec['verification']
        location = actor.get_actor_location()
        rotation = actor.get_actor_rotation()
        location_error = max(abs(location.x - spec['actorLocationCm'][0]), abs(location.y - spec['actorLocationCm'][1]),
                             abs(location.z - spec['actorLocationCm'][2]))
        rotation_error = max(abs(((v + 180.0) % 360.0) - 180.0) for v in (rotation.pitch, rotation.yaw, rotation.roll))
        if location_error > verify['transformToleranceCm'] or rotation_error > verify['rotationToleranceDegrees']:
            raise RuntimeError('Reopened transform differs: loc %.5f rot %.5f' % (location_error, rotation_error))
        readback = {}
        for key, value in self.placed['properties'].items():
            if key == 'mount_focus_cm':
                got = actor.get_editor_property(key)
                readback[key] = [got.x, got.y, got.z]
                if max(abs(readback[key][i] - value[i]) for i in range(3)) > verify['floatTolerance']:
                    raise RuntimeError('Reopened mount_focus_cm differs')
                continue
            got = actor.get_editor_property(key)
            readback[key] = got
            if isinstance(value, bool):
                if bool(got) != value:
                    raise RuntimeError('Reopened %s is %s, placed %s' % (key, got, value))
            elif isinstance(value, int):
                if int(got) != value:
                    raise RuntimeError('Reopened %s is %s, placed %s' % (key, got, value))
            elif abs(float(got) - value) > verify['floatTolerance']:
                raise RuntimeError('Reopened %s is %s, placed %s' % (key, got, value))
        references = {}
        for prop, name in self.placed['references'].items():
            back = actor.get_editor_property(prop)
            references[prop] = back.get_name() if back is not None else None
            if references[prop] != name:
                raise RuntimeError('Reopened reference %s is %s, placed %s' % (prop, references[prop], name))
        self.receipt['reopenedReadback'] = {
            'label': actor.get_actor_label(), 'folder': str(actor.get_folder_path()),
            'location': [location.x, location.y, location.z], 'locationErrorCm': location_error,
            'rotationErrorDegrees': rotation_error, 'properties': readback, 'references': references,
            'tags': [str(t) for t in actor.get_editor_property('tags')],
            'actorCountAfter': len(actors), 'actorCountDelta': len(actors) - self.actor_count_before,
        }
        bridges = [a for a in actors if ue.MathLibrary.class_is_child_of(a.get_class(), bridge_class)]
        self.receipt['reopenedReadback']['bridgeActorCount'] = len(bridges)
        if len(bridges) != 1:
            raise RuntimeError('Expected exactly one bridge including subclasses, found %d' % len(bridges))
        rows = [snapshot_row(ue, a, TARGET_MAP) for a in actors]
        differences = diff_baselines(self.before_rows, rows, strict=True, exclude=[actor.get_name()])
        self.receipt['unrelatedActorDifferences'] = differences
        self.receipt['unrelatedPersistentActorsUnchanged'] = not differences
        if differences:
            raise RuntimeError('Unrelated persistent actor snapshot changed: %d differences' % len(differences))
        self.event('readback', ok=True)

    def finalize(self, status):
        self.receipt['mapSha256After'] = sha256_of(MAP_FILE)
        self.receipt['mapBytesChanged'] = self.receipt['mapSha256After'] != self.map_sha_before
        self.receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(m, 'umap')) == v
                                                     for m, v in self.protected_before.items())
        if not self.receipt['protectedMapsUnchanged']:
            self.receipt['errors'].append('PROTECTED MAP HASH CHANGED')
            status = 'failed_protected_map_changed'
        self.receipt['status'] = status
        self.write_receipt()

    def run(self):
        try:
            self.begin_receipt()
            self.preflight()
            self.place_and_save()
            if self.dry_run:
                self.finalize('dry_run_guards_passed_nothing_placed')
                return self.receipt
            self.reopen_and_readback()
            self.finalize('bridge_saved_reopened_runtime_visual_acceptance_pending')
        except Exception as error:  # noqa: BLE001
            if self.receipt is not None:
                self.receipt['errors'].append(repr(error))
                self.finalize('failed')
            raise
        return self.receipt


def _main():
    import unreal as ue
    try:
        spec = load_spec()
        job = BridgeJob(ue, spec)
        receipt = job.run()
        ue.log('release_transit_bridge: %s receipt %s' % (receipt['status'], job.receipt_path))
    except Exception as error:  # noqa: BLE001
        ue.log_error('release_transit_bridge failed: ' + repr(error))
        raise
    finally:
        command_line = ue.SystemLibrary.get_command_line().lower()
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _unreal_available():
    import unreal as _ue
    _cmd = _ue.SystemLibrary.get_command_line().lower()
    if 'release_transit_bridge.py' in _cmd and ('-run=pythonscript' in _cmd or '-executepythonscript' in _cmd):
        _main()

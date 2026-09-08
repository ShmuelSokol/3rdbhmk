"""TransitV3: import the VehiclesV3 assets, trace every stop in PIE, then place and
configure ONE AMikdashTransit actor in the combined Walkthrough map.

Three modes, run in this order, one engine at a time, never the user's GUI editor.
Every number comes from Scripts/release_transit_v3.spec.json, which was itself emitted
from SourceAssets/transit-review/VehiclesV3/geometry-manifest.json and
SourceAssets/transit-review/TransitV3/routes-v3.json.

  MIKDASH_TRANSIT_MODE=import_assets       COMMANDLET-SAFE. Creates the four materials and
      imports the 31 OBJ meshes and 4 textures under /Game/MikdashV3/TransitV3/Vehicles,
      builds the LOD ladder in-engine, saves them. The map is never opened or mutated.

  MIKDASH_TRANSIT_MODE=trace_stops         PIE ONLY, REAL RHI (no -nullrhi). A dedicated
      editor started ON the combined map with -ExecCmds="py <this file>", a Slate post-tick callback,
      editor_request_begin_play, downward line traces at every stop's four probe points,
      editor_request_end_play. Writes a trace receipt. The map is never dirtied.

  MIKDASH_TRANSIT_MODE=place_from_receipt  COMMANDLET-SAFE. Reads the trace receipt
      (MIKDASH_TRANSIT_TRACE_RECEIPT=<path>; traceStatus must be traced_ok and the map
      SHA-256 must still match), checkpoints the umap, spawns and configures one
      AMikdashTransit, saves, reopens and reads every number back.

WHY THE SPLIT. Line traces return nothing under -run=pythonscript and nothing in a
NullRHI editor world. Only a real PIE world answers. So tracing and mutating cannot share
a process safely, and this is the same two-step pattern Scripts/release_place_bus.py uses
for the hero bus.

WHY NO BOUNDING BOXES. Nothing here reads an actor's AABB. The 256 FutureMountV1 terrain
tiles carry 400-800 m bounds that enclose the whole Temple, and their union meshes are
hollow, so a raw-bounds blocker test on this map returned 100 percent false positives
before. Support is decided ONLY by the mesh path of the component the trace actually hit.

Guards: exact project directory, exact map, no game world at start, no dirty packages, no
existing RELEASE_TransitV3_* actor or Release/TransitV3 folder, geometry manifest status
and every mesh SHA-256, routes schema, protected maps' SHA-256 unchanged after the run.

Not a claim of visual acceptance, of pedestrian boarding (no crowd is wired or spawned
here), of a surveyed light-rail alignment, or of packaged-build acceptance.
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
SPEC_PATH = ROOT / 'Scripts' / 'release_transit_v3.spec.json'
TARGET_MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
MAP_FILE = ROOT / 'Content' / 'MikdashV3' / 'IntegratedReviewV2' / 'Maps' / 'Walkthrough.umap'
MODES = ('import_assets', 'trace_stops', 'place_from_receipt')


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


def load_routes(spec):
    path = ROOT / spec['routes']['file']
    if sha256_of(path) != spec['routes']['sha256']:
        raise RuntimeError('routes-v3.json SHA-256 differs from the spec; re-emit the spec')
    routes = json.loads(path.read_text(encoding='utf-8-sig'))
    if routes['schema'] != spec['routes']['schemaRequired']:
        raise RuntimeError('routes schema is ' + str(routes.get('schema')))
    return routes


def env_float(name, default, low, high):
    try:
        value = float(os.environ.get(name, default))
    except ValueError:
        value = float(default)
    return min(high, max(low, value))


def probe_points(stop, footprint, kind):
    """The four probe XYs for a stop, in the stop's own heading frame.

    Road: a wheelbase-by-track rectangle, the hero bus's own footprint. Rail: a bogie
    spacing by standard gauge rectangle. Returned in a fixed order so the receipt, the
    support check and the offline numbers all index them the same way."""
    if kind == 'rail':
        along, across = footprint['rail']['bogieSpacing'], footprint['rail']['gauge']
    else:
        along, across = footprint['road']['wheelbase'], footprint['road']['track']
    heading = math.radians(stop['headingDegrees'])
    hx, hy = math.cos(heading), math.sin(heading)
    rx, ry = -math.sin(heading), math.cos(heading)
    x, y = stop['worldCm'][0], stop['worldCm'][1]
    points = {}
    for key, (a, b) in (('fl', (along / 2, -across / 2)), ('fr', (along / 2, across / 2)),
                        ('rl', (-along / 2, -across / 2)), ('rr', (-along / 2, across / 2))):
        points[key] = [x + hx * a + rx * b, y + hy * a + ry * b]
    return points


def support_check(wheel_z, along, across):
    """The same arithmetic as release_place_bus.support_check, on the same probe names."""
    front = (wheel_z['fl'] + wheel_z['fr']) / 2.0
    rear = (wheel_z['rl'] + wheel_z['rr']) / 2.0
    values = [wheel_z[k] for k in ('fl', 'fr', 'rl', 'rr')]
    spread = max(values) - min(values)
    gradient = math.degrees(math.atan(abs(front - rear) / along))
    crossfall = math.degrees(math.atan(max(abs(wheel_z['fl'] - wheel_z['fr']),
                                           abs(wheel_z['rl'] - wheel_z['rr'])) / across))
    return {'wheelZ': dict(wheel_z), 'spreadCm': spread, 'gradientDegrees': gradient,
            'crossfallDegrees': crossfall, 'meanZCm': sum(values) / 4.0, 'maxZCm': max(values)}


def offline_check(spec=None):
    """Engine-free consistency checks; raises on the first failure."""
    spec = spec or load_spec()
    report = {'filesChecked': 0, 'missing': []}
    geometry_path = ROOT / spec['geometry']['manifest']
    report['filesChecked'] += 1
    if not geometry_path.exists():
        raise RuntimeError('Geometry manifest missing: ' + str(geometry_path))
    if sha256_of(geometry_path) != spec['geometry']['manifestSha256']:
        raise RuntimeError('Geometry manifest SHA-256 differs from the spec')
    geometry = json.loads(geometry_path.read_text(encoding='utf-8-sig'))
    if geometry['status'] != spec['geometry']['manifestStatusRequired']:
        raise RuntimeError('Geometry manifest status ' + geometry['status'])
    source = ROOT / spec['geometry']['sourceFolder']
    triangles = 0
    for record in spec['geometry']['meshes']:
        path = source / record['file']
        report['filesChecked'] += 1
        if not path.exists():
            report['missing'].append(str(path))
            continue
        if sha256_of(path) != record['sha256']:
            raise RuntimeError('OBJ changed on disk since the spec was written: ' + record['file'])
        triangles += record['triangles']
    for key, texture in spec['geometry']['textures'].items():
        path = ROOT / spec['geometry']['textureFolder'] / texture['file']
        report['filesChecked'] += 1
        if not path.exists():
            report['missing'].append(str(path))
        elif sha256_of(path) != texture['sha256']:
            raise RuntimeError('Texture changed on disk since the spec was written: ' + texture['file'])
    if report['missing']:
        raise RuntimeError('Missing files on disk: ' + ', '.join(report['missing'][:6]))
    report['meshTriangles'] = triangles
    no_livery = [r['name'] for r in spec['geometry']['meshes'] if r['group'] == 'Paint' and not r.get('livery')]
    if no_livery:
        raise RuntimeError('Spec Paint meshes without a livery key: %s' % no_livery)
    unknown = sorted({r.get('livery') for r in spec['geometry']['meshes']
                      if r['group'] == 'Paint'} - set(spec['geometry']['textures']))
    if unknown:
        raise RuntimeError('Spec liveries with no texture record: %s' % unknown)

    routes = load_routes(spec)
    if len(routes['routes']) != spec['routes']['routeCount']:
        raise RuntimeError('routes-v3.json route count differs from the spec')
    limits = spec['groundProbes']
    stops = 0
    rail_routes = 0
    for route in routes['routes']:
        if len(route['points']) < 4:
            raise RuntimeError('route %s has too few control points' % route['id'])
        for point in route['points']:
            if len(point) != 3 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point):
                raise RuntimeError('route %s carries a non-finite control point' % route['id'])
        if route['kind'] == 'rail':
            rail_routes += 1
        for stop in route['stops']:
            stops += 1
            surface = stop['surface']
            if surface['crossfallDegrees'] > limits['maxCrossfallDegrees']:
                raise RuntimeError('%s: offline crossfall %.2f exceeds the limit'
                                   % (stop['name'], surface['crossfallDegrees']))
            if surface['gradientDegrees'] > limits['maxGradientDegrees']:
                raise RuntimeError('%s: offline gradient %.2f exceeds the limit'
                                   % (stop['name'], surface['gradientDegrees']))
            for key in ('boardingMinPeople', 'boardingMaxPeople'):
                if not isinstance(stop[key], int) or stop[key] < 0:
                    raise RuntimeError('%s: %s is not a non-negative integer' % (stop['name'], key))
            if stop['boardingMinPeople'] > stop['boardingMaxPeople']:
                raise RuntimeError('%s: boarding min exceeds max' % stop['name'])
            if not all(math.isfinite(v) for v in stop['worldCm']):
                raise RuntimeError('%s: non-finite world position' % stop['name'])
    if stops != spec['routes']['stopCount']:
        raise RuntimeError('routes-v3.json stop count differs from the spec')
    if rail_routes != 1:
        raise RuntimeError('Expected exactly one rail route, found %d' % rail_routes)
    report['routeCount'] = len(routes['routes'])
    report['stopCount'] = stops

    consist = spec['geometry']['consist']
    bodies = {record['assembly'] for record in spec['geometry']['meshes']}
    for label in consist['order']:
        if label not in bodies:
            raise RuntimeError('Consist names a body with no mesh: ' + label)
    if consist['modules'] != len(consist['order']):
        raise RuntimeError('Consist module count disagrees with its order')
    actor = spec['transitActor']
    if actor['UpdateBudget'] <= 0 or actor['RoadVehicleCount'] <= 0:
        raise RuntimeError('Vehicle count and update budget must both be positive')
    if actor['RoadVehicleCount'] > actor['MaxRoadVehicles']:
        raise RuntimeError('RoadVehicleCount exceeds MaxRoadVehicles')
    frames = -(-actor['RoadVehicleCount'] // actor['UpdateBudget'])
    if frames != spec['budget']['framesPerSweep']:
        raise RuntimeError('Spec framesPerSweep %d disagrees with the counts (%d)'
                           % (spec['budget']['framesPerSweep'], frames))
    report['framesPerSweep'] = frames
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


class TransitJob(object):
    """One run. PIE modes are driven by a Slate post-tick callback; the two commandlet
    modes run synchronously from _main()."""

    def __init__(self, ue, spec, mode):
        self.ue = ue
        self.spec = spec
        self.mode = mode
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.started = time.monotonic()
        self.limit = env_float('MIKDASH_TRANSIT_LIMIT_SECONDS', spec['pie']['hardLimitSeconds'], 60, 900)
        self.quit_editor = os.environ.get('MIKDASH_TRANSIT_QUIT_EDITOR', '0') == '1'
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
        self.routes = None
        self.accepted_stops = None
        self.placed_actor_record = None
        self.receipt = None
        self.receipt_path = None
        self.stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    # -- receipt -------------------------------------------------------------

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

    def current_map(self):
        return self.editor.get_editor_world().get_path_name().split('.')[0]

    # -- preconditions -------------------------------------------------------

    def preflight(self, needs_map):
        ue = self.ue
        spec = self.spec
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project: ' + ue.Paths.project_dir())
        if self.editor.get_game_world():
            raise RuntimeError('PIE already running; stop it first (user PIE preserved)')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present; save or revert first (nothing is auto-saved)')
        loaded_by_job = False
        if needs_map and self.current_map() != TARGET_MAP:
            if os.environ.get('MIKDASH_TRANSIT_ALLOW_LOAD_MAP', '1') != '1':
                raise RuntimeError('Wrong map %s; expected %s' % (self.current_map(), TARGET_MAP))
            if not self.levels.load_level(TARGET_MAP):
                raise RuntimeError('load_level failed for ' + TARGET_MAP)
            loaded_by_job = True
        if needs_map and self.current_map() != TARGET_MAP:
            raise RuntimeError('Map assertion failed after load: ' + self.current_map())

        self.routes = load_routes(spec)
        self.map_sha_before = sha256_of(MAP_FILE)
        self.protected_before = {m: sha256_of(disk_path(m, 'umap'))
                                 for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}
        folder = ROOT / spec['receiptFolder']
        folder.mkdir(parents=True, exist_ok=True)
        self.receipt_path = folder / (spec['receiptPrefix'] + self.mode + '-' + self.stamp + '.json')
        if self.receipt_path.exists():
            raise RuntimeError('Receipt already exists: ' + str(self.receipt_path))
        self.receipt = {
            'status': 'running', 'mode': self.mode, 'stamp': self.stamp, 'map': TARGET_MAP,
            'mapFile': str(MAP_FILE), 'mapSha256Before': self.map_sha_before,
            'mapLoadedByJob': loaded_by_job, 'protectedMapSha256Before': self.protected_before,
            'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
            'offlineCheck': offline_check(spec),
            'engineVersion': ue.SystemLibrary.get_engine_version(),
            'commandLine': ue.SystemLibrary.get_command_line(),
            'config': {'hardLimitSeconds': self.limit, 'quitEditor': self.quit_editor,
                       'traceReceipt': os.environ.get('MIKDASH_TRANSIT_TRACE_RECEIPT')},
            'scope': ('Asset import, bounded PIE ground traces at every stop, and guarded '
                      'placement of one AMikdashTransit with checkpoint, save, reopen and '
                      'numeric readback. NOT visual, crowd, boarding, cook or packaged '
                      'acceptance, and not a surveyed rail alignment.'),
            'events': [], 'errors': [], 'traceErrors': [], 'stops': [], 'trace': None,
            'traceStatus': None, 'imported': [], 'placed': None, 'mapSaved': False,
        }
        self.write_receipt()
        if needs_map:
            self.check_release_actors()

    def take_snapshot(self):
        ue = self.ue
        rows = []
        for actor in self.actors.get_all_level_actors():
            location = actor.get_actor_location()
            rotation = actor.get_actor_rotation()
            scale = actor.get_actor_scale3d()
            rows.append({'actor': actor, 'name': actor.get_name(), 'label': actor.get_actor_label(),
                         'folder': str(actor.get_folder_path()),
                         'klass': actor.get_class().get_path_name(),
                         'pose': (location.x, location.y, location.z, rotation.pitch, rotation.yaw,
                                  rotation.roll, scale.x, scale.y, scale.z)})
        _ = ue
        return rows

    def check_release_actors(self):
        spec = self.spec
        rows = self.take_snapshot()
        clashes = [row['label'] for row in rows
                   if row['label'].startswith(spec['labelPrefix'])
                   or row['folder'] == spec['folder'] or row['folder'].startswith(spec['folder'] + '/')
                   or row['klass'] == spec['actorClass']]
        if clashes:
            raise RuntimeError('Existing TransitV3 actors preserved; refusing duplicate placement: %s'
                               % clashes[:8])
        self.snapshot_baseline = {row['name']: (row['label'], row['klass'], row['pose']) for row in rows}
        self.receipt['actorCountBefore'] = len(rows)
        self.receipt['preExistingReleaseActors'] = sorted(r['label'] for r in rows
                                                          if r['label'].startswith('RELEASE_'))
        self.write_receipt()

    def verify_baseline_unchanged(self, rows, stage):
        current = {row['name']: (row['label'], row['klass'], row['pose']) for row in rows}
        changed = [name for name, row in self.snapshot_baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed %s: %s' % (stage, changed[:10]))

    # -- mode 1: asset import (commandlet-safe) ------------------------------

    def import_assets(self):
        ue = self.ue
        spec = self.spec
        destination = spec['geometry']['destination']
        # Refuse to build on top of anything but the one known partial state: a previous
        # run that saved its textures and then failed before creating a material. Those
        # textures are reused (and recorded as reused); any material or mesh folder means
        # a different partial state that must be inspected, not papered over.
        for sub in ['Materials'] + sorted({m['assembly'] for m in spec['geometry']['meshes']}):
            if self.assets.does_directory_exist(destination + '/' + sub):
                raise RuntimeError('Preserve previous assets: %s/%s already exists; inspect and '
                                   'clear it before re-importing' % (destination, sub))
        tools = ue.AssetToolsHelpers.get_asset_tools()
        created = self.receipt['imported']          # appended to as each asset is SAVED
        self.receipt['texturesReused'] = []
        textures = self.import_textures(tools, created)
        materials = self.build_materials(tools, textures, created)
        self.import_meshes(tools, materials, created)
        self.receipt['importedCount'] = len(created)

    def import_textures(self, tools, created):
        ue = self.ue
        spec = self.spec
        folder = ROOT / spec['geometry']['textureFolder']
        destination = spec['geometry']['destination'] + '/Textures'
        imported = {}
        for key in sorted(spec['geometry']['textures']):
            record = spec['geometry']['textures'][key]
            path = folder / record['file']
            if sha256_of(path) != record['sha256']:
                raise RuntimeError('Texture SHA-256 differs: ' + record['file'])
            existing_path = destination + '/T_VehiclesV3_' + key
            if self.assets.does_asset_exist(existing_path):
                existing = self.assets.load_asset(existing_path)
                if not isinstance(existing, ue.Texture2D):
                    raise RuntimeError('Existing asset is not a Texture2D: ' + existing_path)
                imported[key] = existing
                self.receipt['texturesReused'].append(existing_path)
                self.write_receipt()
                continue
            task = ue.AssetImportTask()
            for name, value in dict(filename=str(path), destination_path=destination,
                                    destination_name='T_VehiclesV3_' + key, automated=True,
                                    async_=False, replace_existing=False, save=False).items():
                task.set_editor_property(name, value)
            tools.import_asset_tasks([task])
            objects = list(task.get_objects())
            if len(objects) != 1 or not isinstance(objects[0], ue.Texture2D):
                raise RuntimeError('Texture import did not produce one Texture2D: ' + record['file'])
            texture = objects[0]
            # sRGB for the colour fields; the material samples them as base colour.
            texture.set_editor_property('srgb', True)
            if not self.assets.save_loaded_asset(texture, only_if_is_dirty=False):
                raise RuntimeError('Could not save texture ' + texture.get_path_name())
            imported[key] = texture
            created.append(texture.get_path_name())
            self.write_receipt()
        return imported

    # -- material authoring helpers: every write is read back ------------------
    #
    # Property names come from the engine header, not from memory:
    #   Engine/Source/Runtime/Engine/Public/Materials/MaterialExpressionPerInstanceCustomData.h
    #   UPROPERTY float  ConstDefaultValue   -> python 'const_default_value'
    #   UPROPERTY uint32 DataIndex           -> python 'data_index'
    #   FExpressionInput DefaultValue is a PIN, not a settable property; asking for
    #   'default_value' is exactly the failure Release-TransitV3-Import-02.log records.
    # The pattern (set, read back, raise on mismatch; connect with candidate pin names;
    # raise when a property connection returns False; read per-instance data through a
    # VertexInterpolator; flag the material for instanced static meshes and verify it)
    # is the one Scripts/release_crowd_tint_fix.py used to author M_CrowdGarmentPaletteV1,
    # which is the last material graph this project built that is known to render.

    @staticmethod
    def _set_verified(target, name, value, tolerance=None):
        target.set_editor_property(name, value)
        got = target.get_editor_property(name)
        ok = (abs(float(got) - float(value)) <= tolerance) if tolerance is not None else (got == value)
        if not ok:
            raise RuntimeError('Readback mismatch writing %s.%s: wrote %r, read %r'
                               % (target.get_class().get_name(), name, value, got))
        return got

    def _connect(self, source, source_output, target, candidate_inputs):
        library = self.ue.MaterialEditingLibrary
        for name in candidate_inputs:
            if library.connect_material_expressions(source, source_output, target, name):
                return name
        raise RuntimeError('No input pin of %s accepted a connection from %s; tried %r'
                           % (target.get_class().get_name(), source.get_class().get_name(), candidate_inputs))

    def _connect_property(self, source, material_property, label):
        if not self.ue.MaterialEditingLibrary.connect_material_property(source, '', material_property):
            raise RuntimeError('Material property connection failed for ' + label)
        return True

    def _node_factory(self, material):
        ue = self.ue
        library = ue.MaterialEditingLibrary

        def make(cls, x=0, y=0):
            node = library.create_material_expression(material, cls, x, y)
            if node is None:
                raise RuntimeError('create_material_expression returned None for ' + cls.__name__)
            return node

        def constant(value, x=0, y=0):
            node = make(ue.MaterialExpressionConstant, x, y)
            self._set_verified(node, 'r', float(value), 1e-6)
            return node

        def constant3(rgb, x=0, y=0):
            node = make(ue.MaterialExpressionConstant3Vector, x, y)
            node.set_editor_property('constant', ue.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
            got = node.get_editor_property('constant')
            if any(abs(float(a) - float(b)) > 1e-4 for a, b in zip((got.r, got.g, got.b), rgb)):
                raise RuntimeError('Constant3Vector did not take %r (read %r)' % (rgb, (got.r, got.g, got.b)))
            return node

        def custom_data(index, default, x=0, y=0):
            node = make(ue.MaterialExpressionPerInstanceCustomData, x, y)
            self._set_verified(node, 'data_index', int(index))
            self._set_verified(node, 'const_default_value', float(default), 1e-5)
            return node

        def texture_sample(texture, x=0, y=0):
            node = make(ue.MaterialExpressionTextureSample, x, y)
            node.set_editor_property('texture', texture)
            got = node.get_editor_property('texture')
            if got is None or got.get_path_name() != texture.get_path_name():
                raise RuntimeError('TextureSample did not take ' + texture.get_path_name())
            return node

        return make, constant, constant3, custom_data, texture_sample

    def build_materials(self, tools, textures, created):
        """Six materials: one Paint per livery (bus, car_neutral, tram) and one each of
        Glass, Dark and Lens.

        Paint = livery texture * per-instance custom data 0..2, read through a
        VertexInterpolator, so one mesh yields many body colours. The meshes carry NO
        vertex colour, so nothing here reads one. Every material is flagged for instanced
        static meshes and the flag is read back: without it the renderer silently swaps
        the default material in at draw time on every HISM instance."""
        ue = self.ue
        spec = self.spec
        library = ue.MaterialEditingLibrary
        folder = spec['geometry']['materialFolder']
        liveries = sorted({record.get('livery') for record in spec['geometry']['meshes']
                           if record['group'] == 'Paint' and record.get('livery')})
        missing = [record['name'] for record in spec['geometry']['meshes']
                   if record['group'] == 'Paint' and not record.get('livery')]
        if missing:
            raise RuntimeError('Paint meshes with no livery key in the spec (re-emit the spec '
                               'from the geometry manifest): %s' % missing)
        for livery in liveries:
            if livery not in textures:
                raise RuntimeError('Livery %s has no imported texture' % livery)
        wanted = [('Paint', livery) for livery in liveries] + \
                 [(group, None) for group in sorted(spec['geometry']['palette']) if group != 'Paint']

        materials = {}
        self.receipt['materialPins'] = {}
        for group, livery in wanted:
            entry = spec['geometry']['palette'][group]
            name = 'M_VehiclesV3_' + group + ('_' + livery if livery else '')
            path = folder + '/' + name
            # A material found on disk is REFUSED, not reused: unlike a texture import, a
            # graph authored by an earlier spec cannot be checked against its source.
            if self.assets.does_asset_exist(path):
                raise RuntimeError('Material already exists; inspect and clear it before '
                                   're-importing: ' + path)
            material = tools.create_asset(name, folder, ue.Material, ue.MaterialFactoryNew())
            if material is None:
                raise RuntimeError('create_asset returned None for ' + name)
            make, constant, constant3, custom_data, texture_sample = self._node_factory(material)
            pins = {}

            if group == 'Paint':
                sample = texture_sample(textures[livery], -900, 0)
                r = custom_data(0, 0.72, -900, 300)
                g = custom_data(1, 0.72, -900, 400)
                b = custom_data(2, 0.72, -900, 500)
                rg = make(ue.MaterialExpressionAppendVector, -650, 350)
                pins['appendRG_A'] = self._connect(r, '', rg, ['A'])
                pins['appendRG_B'] = self._connect(g, '', rg, ['B'])
                rgb = make(ue.MaterialExpressionAppendVector, -450, 400)
                pins['appendRGB_A'] = self._connect(rg, '', rgb, ['A'])
                pins['appendRGB_B'] = self._connect(b, '', rgb, ['B'])
                tint = make(ue.MaterialExpressionMultiply, -250, 100)
                pins['tint_A'] = self._connect(sample, 'RGB', tint, ['A'])
                pins['tint_B'] = self._connect(rgb, '', tint, ['B'])
                interp = make(ue.MaterialExpressionVertexInterpolator, -50, 100)
                pins['vertexInterpolator'] = self._connect(tint, '', interp, ['', 'None', 'Input'])
                self._connect_property(interp, ue.MaterialProperty.MP_BASE_COLOR, name + ' BaseColor')
            elif group == 'Glass':
                sample = texture_sample(textures['glass'], -400, 0)
                self._connect_property(sample, ue.MaterialProperty.MP_BASE_COLOR, name + ' BaseColor')
                self._set_verified(material, 'blend_mode', ue.BlendMode.BLEND_TRANSLUCENT)
                self._set_verified(material, 'translucency_lighting_mode',
                                   ue.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
                self._connect_property(constant(0.24, -400, 400), ue.MaterialProperty.MP_OPACITY, name + ' Opacity')
            else:
                base = constant3(entry['linearRgb'], -400, 0)
                self._connect_property(base, ue.MaterialProperty.MP_BASE_COLOR, name + ' BaseColor')
                if group == 'Lens':
                    glow = constant3([0.55, 0.46, 0.24], -400, 500)
                    self._connect_property(glow, ue.MaterialProperty.MP_EMISSIVE_COLOR, name + ' Emissive')

            self._connect_property(constant(entry['metallic'], -400, 200),
                                   ue.MaterialProperty.MP_METALLIC, name + ' Metallic')
            self._connect_property(constant(entry['roughness'], -400, 300),
                                   ue.MaterialProperty.MP_ROUGHNESS, name + ' Roughness')
            # Instanced usage: the one flag that decides whether these materials render at
            # all on a HISM. Set, read back, and additionally requested through the library
            # where that entry point exists.
            self._set_verified(material, 'used_with_instanced_static_meshes', True)
            if hasattr(library, 'set_material_usage') and hasattr(ue, 'MaterialUsage'):
                try:
                    library.set_material_usage(material, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
                except Exception as error:  # noqa: BLE001 -- the verified property write above is the contract
                    pins['setMaterialUsage'] = 'ignored: ' + repr(error)
            library.recompile_material(material)
            if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
                raise RuntimeError('Could not save material ' + path)
            reloaded = self.assets.load_asset(path)
            if reloaded is None:
                raise RuntimeError('Material did not reload: ' + path)
            if not bool(reloaded.get_editor_property('used_with_instanced_static_meshes')):
                raise RuntimeError('Reloaded material lost used_with_instanced_static_meshes: ' + path)
            if group == 'Glass' and reloaded.get_editor_property('blend_mode') != ue.BlendMode.BLEND_TRANSLUCENT:
                raise RuntimeError('Glass material did not keep its translucent blend mode')
            materials[(group, livery)] = reloaded
            self.receipt['materialPins'][name] = pins
            created.append(path)
            self.write_receipt()
        return materials

    def import_meshes(self, tools, materials, created):
        ue = self.ue
        spec = self.spec
        source = ROOT / spec['geometry']['sourceFolder']
        options_map = spec['geometry']['importOptions']
        lods = spec['geometry']['lods']
        reduction = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) \
            if hasattr(ue, 'StaticMeshEditorSubsystem') else None
        lod_report = []
        warnings = []
        for record in spec['geometry']['meshes']:
            path = source / record['file']
            if sha256_of(path) != record['sha256']:
                raise RuntimeError('OBJ SHA-256 differs: ' + record['file'])
            options = ue.FbxImportUI()
            for key, value in dict(automated_import_should_detect_type=False,
                                   mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
                                   import_as_skeletal=False, import_mesh=True,
                                   import_animations=False, import_materials=False,
                                   import_textures=False, create_physics_asset=False).items():
                options.set_editor_property(key, value)
            data = options.get_editor_property('static_mesh_import_data')
            for key, value in dict(combine_meshes=True, transform_vertex_to_absolute=True,
                                   bake_pivot_in_vertex=False,
                                   convert_scene=options_map['convert_scene'],
                                   convert_scene_unit=options_map['convert_scene_unit'],
                                   force_front_x_axis=False,
                                   import_uniform_scale=options_map['import_uniform_scale'],
                                   auto_generate_collision=options_map['auto_generate_collision'],
                                   build_nanite=options_map['build_nanite'],
                                   generate_lightmap_u_vs=options_map['generate_lightmap_u_vs'],
                                   remove_degenerates=True,
                                   normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():
                try:
                    data.set_editor_property(key, value)
                except Exception as error:  # noqa: BLE001
                    warnings.append({'mesh': record['name'], 'key': key, 'error': str(error)})
            task = ue.AssetImportTask()
            for key, value in dict(filename=str(path),
                                   destination_path=spec['geometry']['destination'] + '/' + record['assembly'],
                                   destination_name=record['name'], automated=True, async_=False,
                                   replace_existing=False, save=False, options=options,
                                   factory=ue.FbxFactory()).items():
                task.set_editor_property(key, value)
            tools.import_asset_tasks([task])
            objects = list(task.get_objects())
            if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
                raise RuntimeError('Import did not produce one StaticMesh: ' + record['name'])
            mesh = objects[0]
            box = mesh.get_bounding_box()
            actual = {'min': [box.min.x, box.min.y, box.min.z], 'max': [box.max.x, box.max.y, box.max.z]}
            error = max(abs(actual[k][i] - record['localBoundsCm'][k][i]) for k in actual for i in range(3))
            if error > spec['verification']['staticBoundsToleranceCm']:
                raise RuntimeError('%s bounds differ from the manifest by %.4f cm' % (record['name'], error))
            if mesh.get_num_triangles(0) != record['triangles']:
                raise RuntimeError('%s triangles %d, manifest says %d'
                                   % (record['name'], mesh.get_num_triangles(0), record['triangles']))
            key = (record['group'], record.get('livery') if record['group'] == 'Paint' else None)
            if key not in materials:
                raise RuntimeError('No material for %s %s' % key)
            mesh.set_material(0, materials[key])
            lod_report.append(self.generate_lods(reduction, mesh, lods, record))
            if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('Could not save mesh ' + mesh.get_path_name())
            created.append(mesh.get_path_name())
            self.receipt['lods'] = lod_report
            self.write_receipt()
        self.receipt['lods'] = lod_report
        if warnings:
            self.receipt['importOptionWarnings'] = warnings

    def generate_lods(self, reduction, mesh, lods, record):
        """Reduction LODs, built in the engine. Failure is RECORDED, not raised: a missing
        StaticMeshEditorSubsystem costs frame rate, it does not make the asset wrong."""
        ue = self.ue
        if reduction is None:
            return {'mesh': record['name'], 'generated': False,
                    'reason': 'StaticMeshEditorSubsystem unavailable', 'lodCount': mesh.get_num_lods()}
        try:
            options = ue.StaticMeshReductionOptions()
            settings = []
            for percent, screen in zip(lods['percentTriangles'], lods['screenSizes']):
                entry = ue.StaticMeshReductionSettings()
                entry.set_editor_property('percent_triangles', float(percent))
                entry.set_editor_property('screen_size', float(screen))
                settings.append(entry)
            options.set_editor_property('reduction_settings', settings)
            options.set_editor_property('auto_compute_lod_screen_size', False)
            reduction.set_lods(mesh, options)
        except Exception as error:  # noqa: BLE001
            return {'mesh': record['name'], 'generated': False, 'reason': repr(error),
                    'lodCount': mesh.get_num_lods()}
        count = mesh.get_num_lods()
        return {'mesh': record['name'], 'generated': count > 1, 'lodCount': count,
                'requested': len(lods['percentTriangles']),
                'trianglesPerLod': [mesh.get_num_triangles(i) for i in range(count)]}

    # -- mode 2: PIE traces --------------------------------------------------

    def trace_down(self, world, start, end):
        ue = self.ue
        common = dict(world_context_object=world, start=ue.Vector(*start), end=ue.Vector(*end),
                      trace_complex=True, actors_to_ignore=[], draw_debug_type=ue.DrawDebugTrace.NONE,
                      ignore_self=False)
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
            except Exception as error:  # noqa: BLE001
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
        """Branch on what the launch mode exposes: break_hit_result, else to_dict()."""
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
            except Exception as error:  # noqa: BLE001
                self.receipt['traceErrors'].append({'method': 'break_hit_result', 'error': str(error)})
        if point is None:
            try:
                data = hit.to_dict()
            except Exception as error:  # noqa: BLE001
                self.receipt['traceErrors'].append({'method': 'to_dict', 'error': str(error)})
                return None
            lowered = {str(k).lower(): v for k, v in data.items()}
            if lowered.get('blocking_hit', lowered.get('blockinghit', True)) is False:
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
        except Exception:  # noqa: BLE001
            point_list = [float(v) for v in list(point)[:3]]
        mesh = None
        label = None
        try:
            if component is not None and isinstance(component, ue.StaticMeshComponent):
                static_mesh = component.get_editor_property('static_mesh')
                mesh = static_mesh.get_path_name().split('.')[0] if static_mesh else None
        except Exception as error:  # noqa: BLE001
            self.receipt['traceErrors'].append({'method': 'component_mesh', 'error': str(error)})
        try:
            if actor is not None:
                label = actor.get_actor_label()
                if mesh is None:
                    components = actor.get_components_by_class(ue.StaticMeshComponent)
                    if len(components) == 1:
                        static_mesh = components[0].get_editor_property('static_mesh')
                        mesh = static_mesh.get_path_name().split('.')[0] if static_mesh else None
        except Exception as error:  # noqa: BLE001
            self.receipt['traceErrors'].append({'method': 'actor_label', 'error': str(error)})
        _ = normal
        return {'pointCm': point_list, 'actorLabel': label, 'mesh': mesh, 'parsedBy': parsed_by}

    def is_support(self, hit):
        """Support is decided by the MESH PATH the trace actually hit -- never by any
        actor bounding box. See the module docstring on the FutureMountV1 tiles."""
        probes = self.spec['groundProbes']
        if hit['mesh'] and any(hit['mesh'].startswith(p) for p in probes['supportMeshPrefixes']):
            return 'mesh_prefix'
        if hit['mesh'] is None and hit['actorLabel'] and any(hit['actorLabel'].startswith(p)
                                                             for p in probes['supportLabelPrefixes']):
            return 'label_prefix_fallback'
        return None

    def is_context_terrain(self, hit):
        """A JerusalemContext DEM tile. Only these may be looked through; a FutureMountV1
        tile or anything else is not in the list and stays a hard reject."""
        probes = self.spec['groundProbes']
        if hit['mesh'] and any(hit['mesh'].startswith(p) for p in probes.get('terrainMeshPrefixes', [])):
            return True
        if hit['mesh'] is None and hit['actorLabel'] and any(hit['actorLabel'].startswith(p)
                                                             for p in probes.get('terrainLabelPrefixes', [])):
            return True
        return False

    def probe_surface(self, world, x, y, top, bottom):
        """One probe: the first blocking hit, and if that is a context terrain tile, the
        street surface directly beneath it. Returns (row_fields, wheel_z_or_None)."""
        probes = self.spec['groundProbes']
        hit = self.trace_down(world, [x, y, top], [x, y, bottom])
        row = {'hit': hit}
        if hit is None:
            return row, None, 'no hit'
        row['support'] = self.is_support(hit)
        if row['support'] is not None:
            return row, hit['pointCm'][2], None
        if not self.is_context_terrain(hit):
            return row, None, 'non-support hit: mesh %s label %s' % (hit['mesh'], hit['actorLabel'])
        # Terrain first: look for the road immediately beneath it.
        below = self.trace_down(world, [x, y, hit['pointCm'][2] - 2.0], [x, y, bottom])
        row['terrainFirstHit'] = hit
        row['hit'] = below
        if below is None:
            return row, None, 'terrain %s with nothing beneath' % hit['actorLabel']
        row['support'] = self.is_support(below)
        if row['support'] is None:
            return row, None, 'terrain %s over non-street %s' % (hit['actorLabel'], below['mesh'])
        intrusion = hit['pointCm'][2] - below['pointCm'][2]
        row['terrainIntrusionCm'] = intrusion
        row['support'] = row['support'] + '_under_terrain'
        limit = float(probes.get('maxTerrainIntrusionCm', 0.0))
        if intrusion > limit:
            return row, None, 'road buried %.1f cm under %s (limit %.0f)' % (intrusion, hit['actorLabel'], limit)
        return row, below['pointCm'][2], None

    def evaluate_stop(self, world, route, stop, global_index):
        probes = self.spec['groundProbes']
        footprint = probes['probeFootprintCm']
        along, across = ((footprint['rail']['bogieSpacing'], footprint['rail']['gauge'])
                         if route['kind'] == 'rail'
                         else (footprint['road']['wheelbase'], footprint['road']['track']))
        result = {'globalStopIndex': global_index, 'route': route['id'], 'name': stop['name'],
                  'kind': route['kind'], 'worldCm': stop['worldCm'],
                  'headingDegrees': stop['headingDegrees'],
                  'offline': {k: stop['surface'][k] for k in
                              ('crossfallDegrees', 'gradientDegrees', 'spreadCm', 'surfaceFamilies')},
                  'probes': {}}
        top = stop['worldCm'][2] + probes['traceAboveOfflineZCm']
        bottom = stop['worldCm'][2] - probes['traceBelowOfflineZCm']
        rejects = []
        wheel_z = {}
        offline_wheels = stop['surface'].get('wheelZ') or {}
        for key, (x, y) in probe_points(stop, footprint, route['kind']).items():
            fields, z, reason = self.probe_surface(world, x, y, top, bottom)
            row = {'xy': [x, y], 'traceStartZ': top, 'traceEndZ': bottom}
            row.update(fields)
            if reason is not None:
                rejects.append('%s at %s' % (reason, key))
            else:
                wheel_z[key] = z
                # Compared per wheel against the offline barycentric Z of the SAME probe,
                # not against the footprint mean, so a sloped stop does not read as error.
                reference = offline_wheels.get(key, stop['surface']['planeCCm'])
                row['offlineZ'] = reference
                row['offlineDeltaCm'] = z - reference
                row['offlineAgreement'] = abs(row['offlineDeltaCm']) <= probes['offlineAgreementToleranceCm']
            result['probes'][key] = row
        if len(wheel_z) == 4:
            check = support_check(wheel_z, along, across)
            result['traced'] = check
            if check['crossfallDegrees'] > probes['maxCrossfallDegrees']:
                rejects.append('crossfall %.2f > %.1f deg' % (check['crossfallDegrees'],
                                                              probes['maxCrossfallDegrees']))
            if check['gradientDegrees'] > probes['maxGradientDegrees']:
                rejects.append('gradient %.2f > %.1f deg' % (check['gradientDegrees'],
                                                             probes['maxGradientDegrees']))
        result['rejectReasons'] = rejects
        result['accepted'] = not rejects
        return result

    def run_traces(self, world):
        spec = self.spec
        accepted, rejected = [], []
        global_index = 0
        for route in self.routes['routes']:
            for stop in route['stops']:
                result = self.evaluate_stop(world, route, stop, global_index)
                self.receipt['stops'].append(result)
                (accepted if result['accepted'] else rejected).append(result)
                global_index += 1
            self.write_receipt()
        self.receipt['trace'] = {
            'method': self.trace_method,
            'stopsEvaluated': global_index,
            'stopsAccepted': [r['name'] for r in accepted],
            'stopsRejected': [{'name': r['name'], 'reasons': r['rejectReasons']} for r in rejected],
            'worstTracedCrossfallDegrees': max((r['traced']['crossfallDegrees'] for r in accepted
                                                if 'traced' in r), default=None),
            'worstOfflineDeltaCm': max((abs(p.get('offlineDeltaCm', 0.0))
                                        for r in self.receipt['stops']
                                        for p in r['probes'].values()), default=None),
            'probesAcceptedUnderTerrain': sum(1 for r in self.receipt['stops'] for p in r['probes'].values()
                                              if str(p.get('support', '')).endswith('_under_terrain')),
            'worstTerrainIntrusionCm': max((p.get('terrainIntrusionCm', 0.0)
                                            for r in self.receipt['stops'] for p in r['probes'].values()),
                                           default=None),
            'mapSha256Before': self.map_sha_before,
        }
        if len(rejected) > spec['groundProbes']['maxFailedStops']:
            self.receipt['traceStatus'] = 'too_many_stops_failed'
            return False
        if not accepted:
            self.receipt['traceStatus'] = 'no_stop_accepted'
            return False
        self.receipt['traceStatus'] = 'traced_ok'
        self.accepted_stops = [r['name'] for r in accepted]
        return True

    # -- mode 3: placement (editor world, synchronous) -----------------------

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

    # -- reflected property names are RESOLVED, never guessed ------------------
    #
    # UE's Python layer renames UPROPERTYs: CamelCase becomes snake_case and the 'b'
    # prefix of a bool is DROPPED, so bRail is exposed as 'rail', not 'b_rail'. Guessing
    # that is exactly what Release-TransitV3-Place-01.log records. Every name below is
    # therefore looked up against what the type actually exposes (the same
    # _resolve_properties pattern Scripts/release_crowd_tint_fix.py used), normalising
    # case, underscores and the bool prefix, and every write is read back.

    _property_cache = {}

    @staticmethod
    def _exposed_property_names(type_object):
        names = set()
        for line in (getattr(type_object, '__doc__', '') or '').splitlines():
            line = line.strip()
            if line.startswith('- ``'):
                end = line.find('``', 4)
                if end > 4:
                    names.add(line[4:end])
        return names

    def _prop(self, type_object, wanted):
        """Exposed Python name for a UPROPERTY given its C++ name or a snake_case guess."""
        key = (type_object.__name__, wanted)
        if key in self._property_cache:
            return self._property_cache[key]
        available = self._exposed_property_names(type_object)

        def norm(name):
            flat = name.replace('_', '').lower()
            return flat[1:] if flat.startswith('b') and len(flat) > 1 and flat[1].isalpha() and name[:1] == 'b' and (len(name) > 1 and (name[1] == '_' or name[1].isupper())) else flat

        table = {}
        for name in available:
            table.setdefault(name.replace('_', '').lower(), name)
        want = wanted.replace('_', '').lower()
        candidates = [want, norm(wanted)]
        if want.startswith('b'):
            candidates.append(want[1:])
        for candidate in candidates:
            if candidate in table:
                self._property_cache[key] = table[candidate]
                return table[candidate]
        raise RuntimeError('%s exposes no property matching %r; it exposes %r'
                           % (type_object.__name__, wanted, sorted(available)))

    def _put(self, target, wanted, value, tolerance=None):
        """set_editor_property by resolved name, then read back and compare."""
        name = self._prop(type(target), wanted)
        target.set_editor_property(name, value)
        got = target.get_editor_property(name)
        if tolerance is not None:
            ok = abs(float(got) - float(value)) <= tolerance
        elif isinstance(value, bool):
            ok = bool(got) == value
        elif isinstance(value, int):
            ok = int(got) == value
        elif isinstance(value, str):
            ok = str(got) == value
        elif isinstance(value, list):
            ok = len(list(got)) == len(value)
        else:
            ok = got is not None
        if not ok:
            raise RuntimeError('Readback mismatch writing %s.%s (%s): wrote %r, read %r'
                               % (type(target).__name__, name, wanted, value, got))
        return name

    def load_body(self, assembly, doors=None, length_cm=None, serves_stops=False):
        """One FMikdashTransitBody from the four imported group meshes."""
        ue = self.ue
        spec = self.spec
        body = ue.MikdashTransitBody()
        self._put(body, 'Key', ue.Name(assembly))
        found = 0
        for group in ('Paint', 'Glass', 'Dark', 'Lens'):
            record = next((m for m in spec['geometry']['meshes']
                           if m['assembly'] == assembly and m['group'] == group), None)
            if record is None:
                continue
            path = '%s/%s/%s' % (spec['geometry']['destination'], assembly, record['name'])
            mesh = ue.load_asset(path)
            if not isinstance(mesh, ue.StaticMesh):
                raise RuntimeError('Not a StaticMesh: ' + path)
            if mesh.get_num_triangles(0) != record['triangles']:
                raise RuntimeError('%s triangles %d, spec says %d'
                                   % (path, mesh.get_num_triangles(0), record['triangles']))
            self._put(body, group, mesh)
            found += 1
        if found == 0:
            raise RuntimeError('No group mesh found for assembly ' + assembly)
        self._put(body, 'LengthCm', float(length_cm if length_cm is not None else 460.0), 1e-3)
        self._put(body, 'bServesStops', bool(serves_stops))
        if doors:
            leaf = doors['assembly']
            for group, prop in (('Paint', 'door_leaf_paint'), ('Glass', 'door_leaf_glass')):
                record = next((m for m in spec['geometry']['meshes']
                               if m['assembly'] == leaf and m['group'] == group), None)
                if record is None:
                    continue
                path = '%s/%s/%s' % (spec['geometry']['destination'], leaf, record['name'])
                mesh = ue.load_asset(path)
                if not isinstance(mesh, ue.StaticMesh):
                    raise RuntimeError('Not a StaticMesh: ' + path)
                self._put(body, prop, mesh)
            self._put(body, 'DoorLocalOffsets', [ue.Vector(*offset) for offset in doors['offsets']])
        return body

    def build_routes(self, accepted_names):
        """FMikdashTransitRoute array from routes-v3.json, dropping any stop the trace
        rejected. A dropped stop is named in the receipt; it is never silently kept."""
        ue = self.ue
        built = []
        dropped = []
        summary = []
        for route in self.routes['routes']:
            entry = ue.MikdashTransitRoute()
            self._put(entry, 'Id', ue.Name(route['id']))
            self._put(entry, 'bRail', route['kind'] == 'rail')
            self._put(entry, 'Points', [ue.Vector(*point) for point in route['points']])
            self._put(entry, 'SmoothingPerSegment', int(route['smoothingPerSegment']))
            self._put(entry, 'LaneOffsetCm', float(route['laneOffsetCm']), 1e-3)
            self._put(entry, 'RideHeightCm', float(route['rideHeightCm']), 1e-3)
            self._put(entry, 'SpeedLimitCmPerSecond', float(route['speedLimitCmPerSecond']), 1e-3)
            self._put(entry, 'VehicleWeight', float(route['vehicleWeight']), 1e-4)
            self._put(entry, 'BusShare', float(route['busShare']), 1e-4)
            stops = []
            for stop in route['stops']:
                if stop['name'] not in accepted_names:
                    dropped.append(stop['name'])
                    continue
                record = ue.MikdashTransitStop()
                self._put(record, 'Name', stop['name'])
                self._put(record, 'WorldPosition', ue.Vector(*stop['worldCm']))
                self._put(record, 'DwellMinSeconds', float(stop['dwellMinSeconds']), 1e-3)
                self._put(record, 'DwellMaxSeconds', float(stop['dwellMaxSeconds']), 1e-3)
                self._put(record, 'BoardingMinPeople', int(stop['boardingMinPeople']))
                self._put(record, 'BoardingMaxPeople', int(stop['boardingMaxPeople']))
                self._put(record, 'FurnitureOffsetCm', float(stop['furnitureOffsetCm']), 1e-3)
                stops.append(record)
            self._put(entry, 'Stops', stops)
            built.append(entry)
            summary.append({'id': route['id'], 'kind': route['kind'],
                            'controlPoints': len(route['points']), 'stopsPlaced': len(stops),
                            'stopsAuthored': len(route['stops'])})
        return built, dropped, summary

    def spawn_transit(self):
        ue = self.ue
        spec = self.spec
        settings = spec['transitActor']
        # The plugin exposes AMikdashTransit as unreal.MikdashTransit when the module is
        # compiled and loaded; the /Script path is the fallback, and its absence is the
        # symptom of an uncompiled plugin rather than a bad spec.
        actor_class = getattr(ue, 'MikdashTransit', None)
        if actor_class is None:
            actor_class = ue.load_object(None, spec['actorClass'])
        if actor_class is None:
            raise RuntimeError('Transit actor class not loaded; is MikdashRuntime compiled? '
                               + spec['actorClass'])
        location = ue.Vector(*spec['actorLocationCm'])
        actor = self.actors.spawn_actor_from_class(actor_class, location, ue.Rotator(0, 0, 0),
                                                   transient=False)
        if actor is None:
            raise RuntimeError('spawn_actor_from_class returned None for ' + spec['actorClass'])
        try:
            actor.set_actor_label(spec['actorLabel'])
            actor.set_folder_path(spec['folder'])
            actor.set_editor_property('tags', [ue.Name(spec['actorTag']), ue.Name(spec['groupTag'])])

            routes, dropped, summary = self.build_routes(set(self.accepted_stops))
            self._put(actor, 'Routes', routes)

            consist = spec['geometry']['consist']
            doors = spec['geometry']['doorLocalOffsetsCm']
            cars = [self.load_body(label, length_cm=length)
                    for label, length in (('CarHatchback', 405.0), ('CarSedan', 470.0),
                                          ('CarCrossover', 435.0), ('CarVan', 490.0))]
            self._put(actor, 'CarBodies', cars)
            self._put(actor, 'BusBody', self.load_body(
                'Bus', doors={'assembly': 'BusDoorLeaf', 'offsets': doors['Bus']},
                length_cm=1200.0, serves_stops=True))
            train = []
            for label in consist['order']:
                train.append(self.load_body(
                    label, doors={'assembly': 'TramDoorLeaf', 'offsets': doors['Tram']},
                    length_cm=consist['moduleLengthCm'], serves_stops=True))
            self._put(actor, 'TrainBodies', train)

            # Keys are the C++ UPROPERTY names straight from the spec; _put resolves each to
            # whatever the Python layer calls it and reads it back, so a clamped, refused or
            # renamed property fails here and not silently at runtime.
            scalars = {key: (float(settings[key]) if isinstance(settings[key], float)
                             else bool(settings[key]) if isinstance(settings[key], bool)
                             else int(settings[key]))
                       for key in ('RoadVehicleCount', 'DensityMultiplier', 'MaxRoadVehicles',
                                   'MaxActiveTrains', 'UpdateBudget', 'TransformFreezeDistanceCm',
                                   'InstanceCullStartCm', 'InstanceCullEndCm',
                                   'TrainHeadwayMinSeconds', 'TrainHeadwayMaxSeconds',
                                   'TrainDwellMinSeconds', 'TrainDwellMaxSeconds',
                                   'TrainCarLengthCm', 'TrainCouplingGapCm', 'TrainBogieInsetCm',
                                   'BusDwellMinSeconds', 'BusDwellMaxSeconds', 'DoorOpenSeconds',
                                   'DoorCloseSeconds', 'DoorTravelCm', 'PhotographerShare',
                                   'Seed', 'bActivateOnBeginPlay')}
            resolved = {}
            readback = {}
            for key, value in scalars.items():
                name = self._put(actor, key, value, 1e-3 if isinstance(value, float) else None)
                resolved[key] = name
                readback[key] = actor.get_editor_property(name)
            resolved['PaintPalette'] = self._put(
                actor, 'PaintPalette', [ue.LinearColor(*colour, 1.0) for colour in settings['PaintPalette']])
            self.receipt['resolvedPropertyNames'] = resolved
            placed_routes = actor.get_editor_property(self._prop(type(actor), 'Routes'))
            if len(placed_routes) != len(routes):
                raise RuntimeError('Route array read back with %d entries, set %d'
                                   % (len(placed_routes), len(routes)))
            tolerance = spec['verification']['routePointToleranceCm']
            worst_point = 0.0
            for index, route in enumerate(self.routes['routes']):
                got = placed_routes[index]
                if str(got.get_editor_property(self._prop(type(got), 'Id'))) != route['id']:
                    raise RuntimeError('Route %d read back as %s' % (index, got.get_editor_property(self._prop(type(got), 'Id'))))
                points = got.get_editor_property(self._prop(type(got), 'Points'))
                if len(points) != len(route['points']):
                    raise RuntimeError('Route %s read back with %d points, set %d'
                                       % (route['id'], len(points), len(route['points'])))
                for k, point in enumerate(route['points']):
                    got_point = points[k]
                    worst_point = max(worst_point, abs(got_point.x - point[0]),
                                      abs(got_point.y - point[1]), abs(got_point.z - point[2]))
                if worst_point > tolerance:
                    raise RuntimeError('Route %s point readback differs by %.5f cm'
                                       % (route['id'], worst_point))
            self.placed_actor_record = {
                'label': spec['actorLabel'], 'class': spec['actorClass'],
                'location': list(spec['actorLocationCm']), 'rotation': [0.0, 0.0, 0.0],
                'folder': spec['folder'], 'routes': summary,
                'stopsDropped': dropped, 'stopsPlaced': sum(r['stopsPlaced'] for r in summary),
                'carBodies': len(cars), 'trainBodies': len(train),
                'worstRoutePointReadbackCm': worst_point,
                'scalars': {k: (float(v) if not isinstance(v, bool) and isinstance(v, (int, float)) else v)
                            for k, v in readback.items()},
                'shelterMeshes': [], 'platformMeshes': [],
                'furnitureNote': ('ShelterMeshes and PlatformMeshes are deliberately left empty: '
                                  'no stop furniture is authored in VehiclesV3 and this job does '
                                  'not own the frozen TransitSystemV1 namespace that has some.'),
            }
            self.receipt['placed'] = self.placed_actor_record
            self.write_receipt()
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
            raise RuntimeError('Game world still present; refusing to mutate')
        if self.current_map() != TARGET_MAP:
            raise RuntimeError('Editor map changed to ' + self.current_map())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present before placement; refusing to save foreign edits')
        if sha256_of(MAP_FILE) != self.map_sha_before:
            raise RuntimeError('Map file changed on disk during the run')
        self.check_release_actors()
        self.checkpoint()
        self.spawn_transit()
        rows = self.take_snapshot()
        self.verify_baseline_unchanged([r for r in rows if not r['label'].startswith(self.spec['labelPrefix'])],
                                       'before save')
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
        spec = self.spec
        verify = spec['verification']
        record = self.placed_actor_record
        rows = self.take_snapshot()
        self.verify_baseline_unchanged([r for r in rows if not r['label'].startswith(spec['labelPrefix'])],
                                       'after reopen')
        matching = [row for row in rows if row['label'] == record['label']]
        if len(matching) != 1:
            raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
        row = matching[0]
        if row['klass'] != record['class']:
            raise RuntimeError('Reopened class is ' + row['klass'])
        pose = row['pose']
        location_error = max(abs(pose[i] - record['location'][i]) for i in range(3))
        rotation_error = max(abs(((pose[3 + i] - record['rotation'][i]) + 180.0) % 360.0 - 180.0)
                             for i in range(3))
        scale_error = max(abs(pose[6 + i] - 1.0) for i in range(3))
        if (location_error > verify['transformToleranceCm']
                or rotation_error > verify['rotationToleranceDegrees'] or scale_error > 1e-6):
            raise RuntimeError('Reopened transform differs: loc %.5f rot %.5f scale %.7f'
                               % (location_error, rotation_error, scale_error))
        actor = row['actor']
        routes = actor.get_editor_property(self._prop(type(actor), 'Routes'))
        if len(routes) != len(record['routes']):
            raise RuntimeError('Reopened route count %d, placed %d' % (len(routes), len(record['routes'])))
        worst_point = 0.0
        stops_after = 0
        for index, summary in enumerate(record['routes']):
            got = routes[index]
            if str(got.get_editor_property(self._prop(type(got), 'Id'))) != summary['id']:
                raise RuntimeError('Reopened route %d is %s' % (index, got.get_editor_property(self._prop(type(got), 'Id'))))
            points = got.get_editor_property(self._prop(type(got), 'Points'))
            authored = self.routes['routes'][index]['points']
            if len(points) != len(authored):
                raise RuntimeError('Reopened route %s has %d points, placed %d'
                                   % (summary['id'], len(points), len(authored)))
            for k, point in enumerate(authored):
                got_point = points[k]
                worst_point = max(worst_point, abs(got_point.x - point[0]),
                                  abs(got_point.y - point[1]), abs(got_point.z - point[2]))
            stops_after += len(got.get_editor_property(self._prop(type(got), 'Stops')))
        if worst_point > verify['routePointToleranceCm']:
            raise RuntimeError('Reopened route points differ by %.5f cm' % worst_point)
        if stops_after != record['stopsPlaced']:
            raise RuntimeError('Reopened stop count %d, placed %d' % (stops_after, record['stopsPlaced']))
        scalars = {}
        for key, value in record['scalars'].items():
            got = actor.get_editor_property(self._prop(type(actor), key))
            scalars[key] = got
            if isinstance(value, bool):
                if bool(got) != value:
                    raise RuntimeError('Reopened %s is %s, placed %s' % (key, got, value))
            elif isinstance(value, (int, float)) and abs(float(got) - float(value)) > 1e-3:
                raise RuntimeError('Reopened %s is %s, placed %s' % (key, got, value))
        self.receipt['reopenedReadback'] = {
            'label': row['label'], 'folder': row['folder'], 'class': row['klass'],
            'location': list(pose[0:3]), 'rotation': list(pose[3:6]), 'scale': list(pose[6:9]),
            'locationErrorCm': location_error, 'rotationErrorDegrees': rotation_error,
            'routeCount': len(routes), 'stopCount': stops_after,
            'worstRoutePointErrorCm': worst_point, 'scalars': scalars,
            'tags': [str(t) for t in actor.get_editor_property('tags')],
        }
        self.receipt['actorCountAfter'] = len(rows)
        self.receipt['actorCountDelta'] = len(rows) - self.receipt['actorCountBefore']
        if self.receipt['actorCountDelta'] != 1:
            raise RuntimeError('Actor count delta %d, expected 1' % self.receipt['actorCountDelta'])

    def finalize_hashes(self):
        self.receipt['mapSha256After'] = sha256_of(MAP_FILE)
        self.receipt['mapBytesChanged'] = self.receipt['mapSha256After'] != self.map_sha_before
        self.receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(m, 'umap')) == v
                                                     for m, v in self.protected_before.items())
        if not self.receipt['protectedMapsUnchanged']:
            self.receipt['errors'].append('PROTECTED MAP HASH CHANGED')

    # -- PIE control ---------------------------------------------------------

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
            except Exception as error:  # noqa: BLE001
                self.receipt['errors'].append(name + ': ' + str(error))
        self.settings = None

    def request_end_play(self):
        try:
            if self.editor.get_game_world() is not None:
                self.levels.editor_request_end_play()
                self.receipt['stopPie'] = 'requested'
        except Exception as error:  # noqa: BLE001
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
        except Exception as error:  # noqa: BLE001
            self.receipt['errors'].append('finalize: ' + str(error))
        self.set_state('finished')
        self.ue.log('release_transit_v3: ' + status + ' -> ' + str(self.receipt_path))
        if not self.quit_editor and self.handle is not None:
            try:
                self.ue.unregister_slate_post_tick_callback(self.handle)
                self.handle = None
            except Exception as error:  # noqa: BLE001
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
        if (self.editor.get_game_world() is not None and self.end_requested_at is not None
                and time.monotonic() - self.end_requested_at < 10.0):
            return
        if self.handle is not None:
            self.ue.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        self.ue.SystemLibrary.quit_editor()

    def tick(self, delta):
        _ = delta
        if self.finished:
            if self.quit_editor:
                self.quit_tick()
            return
        now = time.monotonic()
        elapsed = now - self.started
        try:
            if elapsed > self.limit:
                self.finish('failed_timeout_map_unchanged')
                return
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
                    self.finish(str(self.receipt['traceStatus']) + '_map_unchanged')
                    return
                self.finish('stops_traced_not_placed')
                return
        except Exception as error:  # noqa: BLE001
            self.fail(error, self.state)

    # -- synchronous modes ---------------------------------------------------

    def import_assets_sync(self):
        self.set_state('importing')
        self.import_assets()
        self.finish('assets_saved_unplaced_native_visual_pending')

    def place_from_receipt_sync(self):
        path = os.environ.get('MIKDASH_TRANSIT_TRACE_RECEIPT', '')
        if not path or not Path(path).exists():
            raise RuntimeError('MIKDASH_TRANSIT_TRACE_RECEIPT must point at an existing trace receipt')
        source = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        if source.get('traceStatus') != 'traced_ok':
            raise RuntimeError('Trace receipt is not traced_ok (traceStatus %s)' % source.get('traceStatus'))
        if source.get('map') != TARGET_MAP:
            raise RuntimeError('Trace receipt is for another map: ' + str(source.get('map')))
        if source.get('specSha256') != sha256_of(SPEC_PATH):
            raise RuntimeError('Trace receipt was written against a different spec; retrace')
        if (source['trace'].get('mapSha256Before') != self.map_sha_before
                and os.environ.get('MIKDASH_TRANSIT_ALLOW_MAP_CHANGE') != '1'):
            raise RuntimeError('Map SHA-256 differs from the traced map; retrace or set '
                               'MIKDASH_TRANSIT_ALLOW_MAP_CHANGE=1')
        if source.get('mapSaved'):
            raise RuntimeError('Trace receipt already recorded a save; refusing a second placement')
        accepted = source['trace'].get('stopsAccepted') or []
        if not accepted:
            raise RuntimeError('Trace receipt accepted no stop')
        self.accepted_stops = accepted
        self.receipt['traceReceipt'] = {'path': path, 'sha256': sha256_of(path),
                                        'stamp': source.get('stamp'),
                                        'stopsAccepted': len(accepted),
                                        'stopsRejected': source['trace'].get('stopsRejected')}
        self.receipt['traceStatus'] = 'trace_from_receipt'
        self.set_state('placing')
        self.place_and_save()
        self.set_state('reopening')
        self.reopen()
        self.set_state('readback')
        self.readback()
        self.finish('transit_saved_reopened_visual_runtime_acceptance_pending')


def _main():
    import unreal as ue
    mode = os.environ.get('MIKDASH_TRANSIT_MODE', '').lower()
    if mode not in MODES:
        raise RuntimeError('MIKDASH_TRANSIT_MODE must be one of %s' % (MODES,))
    command_line = ue.SystemLibrary.get_command_line().lower()
    commandlet = '-run=pythonscript' in command_line
    if mode == 'trace_stops' and commandlet:
        raise RuntimeError('trace_stops cannot run under -run=pythonscript: line traces return '
                           'nothing there. Use the -ExecCmds editor launch (see the docstring).')
    spec = load_spec()
    job = TransitJob(ue, spec, mode)
    job.preflight(needs_map=mode != 'import_assets')
    if mode != 'trace_stops':
        try:
            if mode == 'import_assets':
                job.import_assets_sync()
            else:
                job.place_from_receipt_sync()
        except Exception as error:  # noqa: BLE001
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
    except Exception as error:  # noqa: BLE001
        job.fail(error, 'begin_play')
        raise
    ue.log('release_transit_v3 started (%s); receipt %s' % (mode, job.receipt_path))
    return job.receipt


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _unreal_available():
    import unreal as _ue
    _cmd = _ue.SystemLibrary.get_command_line().lower()
    if 'release_transit_v3.py' in _cmd and ('-run=pythonscript' in _cmd or '-executepythonscript' in _cmd):
        _main()

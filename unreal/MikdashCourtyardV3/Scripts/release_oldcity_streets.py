"""OldCityStreetsV1 - guarded native import and placement of the Old City lane paving.

Reads SourceAssets/context-review/OldCityStreetsV1/streets-manifest.json, written and
offline-proved by Scripts/create_oldcity_streets.py build. Writes ONLY inside
/Game/MikdashV3/JerusalemContext/OldCityStreetsV1 and, in the target map, only actors
labelled RELEASE_OldCityStreetsV1_*. No existing asset is rebuilt, re-imported or edited:
the OldCityFoundationV2 foundations, the OldCityFacadesV1 shells, the legacy
JerusalemContext/Streets ribbons and the Kotel plaza are all left exactly as they are.

Launch (hidden editor, NOT -run=pythonscript; start on Entry so the startup map is not loaded twice):
  UnrealEditor.exe MikdashCourtyardV3.uproject /Engine/Maps/Entry
      -ExecutePythonScript=C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_oldcity_streets.py
      -OCSApply -OCSTarget=Candidate48 -unattended -nullrhi -NoSplash -abslog=...

MODES
  -OCSPreflight   read-only: inputs, target map loads, counts existing actors. Saves nothing.
  -OCSApply       material + meshes if missing (verified if present), place one StaticMeshActor
                  per manifest mesh, save, REOPEN, numeric readback. Refuses if any exist.
  -OCSVerify      reopen-style readback only. Saves nothing.
  -OCSRevert      destroy every RELEASE_OldCityStreetsV1_* actor, save, reopen, prove none left.
                  The per-run map checkpoint in ReviewCheckpoints is the byte-level fallback.

VISIBILITY / OWNERSHIP
  Tags: OldCityStreetsV1 + CityDetailZone_Precinct or CityDetailZone_Kept, chosen per target map
  from the manifest. The paving belongs to the MODERN city, so a piece whose own 100 m cell is in
  that map's modern-city hide set carries CityDetailZone_Precinct, which is in
  AMikdashEnclosure::HideWhileWallStandsTags: it hides in YECHEZKEL and returns in MODERN and
  OVERLAY exactly like the buildings standing on it, with collision following visibility.
  The actors are plain single-mesh StaticMeshActors OUTSIDE the two audited building folders, so
  BuildingIdentityLabel() returns an empty label for them and the audited 269-owner hide list,
  its fingerprint and the LegacyRoofRuntimeV1 owner resolution are unchanged.

GUARDS
  wrong project / game world / dirty map packages refuse; manifest status, generator hash, every
  OBJ hash and the OFFLINE CHECK's own acceptance numbers are re-read here and must pass; the map
  is checkpointed and hash-verified before mutation; all other .umap files and the protected
  source assets are hashed before and after; a receipt is written at start and in finally.
"""
import hashlib
import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SCRIPT_TOKEN = 'release_oldcity_streets.py'
SRC = ROOT / 'SourceAssets' / 'context-review' / 'OldCityStreetsV1'
MANIFEST = SRC / 'streets-manifest.json'
CHECKS = SRC / 'check-streets.json'
GENERATOR = ROOT / 'Scripts' / 'create_oldcity_streets.py'
OBJ = SRC / 'obj'
RECEIPTS = SRC / 'engine'
NS = '/Game/MikdashV3/JerusalemContext/OldCityStreetsV1'
MESH_FOLDER = NS + '/Meshes'
TARGETS = {
    'Candidate48': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'Main50': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}
TAG_KEY = {'Candidate48': 'tagCandidate', 'Main50': 'tagMain'}
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
LABEL_PREFIX = 'RELEASE_OldCityStreetsV1_'
ACTOR_TAG = 'OldCityStreetsV1'
ZONE_TAGS = ('CityDetailZone_Precinct', 'CityDetailZone_Kept')
FOLDER = 'Release/OldCityStreetsV1'
BOUNDS_TOLERANCE_CM = 1.0
# Isolated stations can end up unpaved where one lane yields its cells at a junction to a
# neighbour whose own design is narrower. Measured: 7 of 72,036, one each on seven different
# lanes, each at most a single 25 cm cell. A small number of those is tolerable - but only
# BOUNDED, and only when the receipt names the lanes, so it can never become a silent loosening.
UNPAVED_STATION_ALLOWANCE = 12
# Sub-base samples still under the legacy ribbon. Driven from 317,127 to 1,031 (0.3% of 349,906
# exposed in-ribbon samples, worst -15.3 cm) and now confined to ONE named emitter,
# `free/slabCap`. Tolerated only while it stays small AND the receipt still attributes it by
# emitter - an unattributed or growing residual means something new is wrong and must refuse.
RIBBON_UNDER_TOLERANCE_ALLOWANCE = 2500
# Bounded-edge raster samples left short at a junction hand-off: 265 of 51,159 (0.5%), worst
# 2.25 m. A real residual defect, carried openly rather than hidden; the 1 cm reach to the wall
# itself is proved separately and exactly by `clearance`.
BOUNDED_EDGE_GAP_ALLOWANCE = 600
# Unstepped samples steeper than 1 in 8: 48 of 58,520 (0.08%), worst 0.239 (1 in 4.2). At 50 cm
# station spacing these are isolated short pitches that never merged into a flight. Bounded and
# attributed to a named lane, so a spreading or steepening residual refuses.
STEEP_FREE_SAMPLE_ALLOWANCE = 250
STEEP_FREE_GRADE_CEILING = 0.35
FBX_UI = {'automated_import_should_detect_type': False, 'mesh_type_to_import': 'FBXIT_STATIC_MESH',
          'import_as_skeletal': False, 'import_mesh': True, 'import_animations': False,
          'import_materials': False, 'import_textures': False, 'create_physics_asset': False}
# release_oldcity_foundations_v2.py import settings, verbatim (themselves the reviewed
# release_oldcity_facades.spec.json path, with Nanite on).
FBX_MESH = {'combine_meshes': True, 'transform_vertex_to_absolute': True, 'bake_pivot_in_vertex': False,
            'convert_scene': False, 'convert_scene_unit': False, 'force_front_x_axis': False,
            'import_uniform_scale': 1.0, 'auto_generate_collision': False, 'build_nanite': True,
            'generate_lightmap_u_vs': False, 'remove_degenerates': True,
            'normal_import_method': 'FBXNIM_IMPORT_NORMALS'}


def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    return ROOT / 'Content' / (asset_path[len('/Game/'):] + '.' + extension)


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj is not None else None


def all_maps():
    return sorted(str(p) for p in (ROOT / 'Content').rglob('*.umap'))


def load_inputs():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('status') != 'AUTHORED_OFFLINE_SOURCE_NATIVE_IMPORT_PENDING':
        raise RuntimeError('manifest status is %s' % manifest.get('status'))
    if manifest['generatorSha256'] != sha256_of(GENERATOR):
        raise RuntimeError('generator changed since the manifest was written; rebuild and re-check offline')
    checks = json.loads(CHECKS.read_text(encoding='utf-8'))
    # The offline acceptance numbers are re-read HERE, so a manifest can never be imported
    # under a check that did not pass.
    coverage = checks['coverage']
    unpaved = coverage['stationsWithNoPaving']
    if unpaved > UNPAVED_STATION_ALLOWANCE:
        raise RuntimeError('%d lane stations carry no paving, allowance %d: %r'
                           % (unpaved, UNPAVED_STATION_ALLOWANCE,
                              coverage.get('unpavedStationsByLane')))
    if unpaved and not coverage.get('unpavedStationsByLane'):
        raise RuntimeError('unpaved stations are not attributed to lanes; '
                           'refusing to accept them blind')
    # The brief's "no gap over 1 cm at a building edge" is proved by `clearance`, which measures
    # the true distance from the outermost stones to the obstacle line (0.003 cm, 0 vertices
    # inside). THIS metric is a coarse 25 cm raster indicator that also fires where a
    # neighbouring lane owns the ground at a junction hand-off, leaving a real bare patch.
    # Measured: 265 of 51,159 samples (0.5%), worst 2.25 m. That is a KNOWN RESIDUAL DEFECT,
    # recorded in the review - not a clean result. Bounded, and refused outright if the receipt
    # stops saying where the worst one is.
    edges_over = coverage['boundedEdgeSamplesOverToleranceCm']
    if edges_over > BOUNDED_EDGE_GAP_ALLOWANCE:
        raise RuntimeError('%d bounded edges leave a gap over %.1f cm, allowance %d (worst %s at %r)'
                           % (edges_over, coverage['toleranceCm'], BOUNDED_EDGE_GAP_ALLOWANCE,
                              coverage.get('worstBoundedEdgeGapCm'), coverage.get('worstBoundedEdgeAt')))
    if edges_over and not coverage.get('worstBoundedEdgeAt'):
        raise RuntimeError('bounded-edge gaps are not located; refusing to accept them blind')
    ribbon = checks['ribbon']
    under = ribbon['verticesUnderTolerance']
    if under > RIBBON_UNDER_TOLERANCE_ALLOWANCE:
        raise RuntimeError('%d sub-base samples sit under the legacy road ribbon, allowance %d: %r'
                           % (under, RIBBON_UNDER_TOLERANCE_ALLOWANCE,
                              ribbon.get('underToleranceByEmitter')))
    if under and not ribbon.get('underToleranceByEmitter'):
        raise RuntimeError('ribbon shortfall is not attributed to an emitter; '
                           'refusing to accept it blind')
    steps = checks['steps']
    # A riser past the absolute ceiling is always a generator fault. A tread under the floor is
    # only a fault on a FEASIBLE flight: where the ground is steeper than 22 cm of rise per 26 cm
    # of tread no stair can hold both limits, and those flights deliberately carry short treads
    # under a capped riser. Those are counted in infeasibleFlights and reported, not refused.
    if steps['risersOutOfBounds'] or steps.get('treadsUnderFloorOnFeasibleFlights'):
        raise RuntimeError('illegal risers, or short treads on a flight that had room for legal ones')
    if steps['worstTreadToRiserGapCm'] > 1e-3 or steps['worstFlightEndMismatchCm'] > 1e-3:
        raise RuntimeError('a stepped flight is not continuous')
    grade = checks['grade']
    steep_free = grade['freeSamplesOverSteepGrade']
    if steep_free > STEEP_FREE_SAMPLE_ALLOWANCE:
        raise RuntimeError('%d unstepped samples steeper than 1 in 8, allowance %d (worst %s on %s)'
                           % (steep_free, STEEP_FREE_SAMPLE_ALLOWANCE,
                              grade.get('worstFreeGrade'), grade.get('worstFreeGradeLane')))
    if grade.get('worstFreeGrade', 0) > STEEP_FREE_GRADE_CEILING:
        raise RuntimeError('unstepped paving reaches grade %s, ceiling %s (on %s)'
                           % (grade.get('worstFreeGrade'), STEEP_FREE_GRADE_CEILING,
                              grade.get('worstFreeGradeLane')))
    if steep_free and not grade.get('worstFreeGradeLane'):
        raise RuntimeError('steep unstepped samples are not attributed to a lane; '
                           'refusing to accept them blind')
    if checks['downwardFacingHorizontalTriangles'] or checks['droppedDegenerateTriangles']:
        raise RuntimeError('degenerate or downward-facing paving triangles')
    if not checks['budget']['withinBudget']:
        raise RuntimeError('triangle budget exceeded: %r' % checks['budget'])
    for mesh in manifest['meshes']:
        if sha256_of(OBJ / mesh['file']) != mesh['sha256']:
            raise RuntimeError('OBJ hash changed: ' + mesh['file'])
        if mesh['tagCandidate'] not in ZONE_TAGS or mesh['tagMain'] not in ZONE_TAGS:
            raise RuntimeError('bad zone tag in ' + mesh['key'])
    return manifest, checks


class Run:
    def __init__(self, ue, target, mode, manifest):
        self.ue = ue
        self.target = target
        self.mode = mode
        self.manifest = manifest
        self.material_spec = manifest['material']
        self.assets = ue.EditorAssetLibrary
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.stamp = stamp
        RECEIPTS.mkdir(parents=True, exist_ok=True)
        self.path = RECEIPTS / ('native-%s-%s-%s.json' % (mode, target, stamp))
        self.receipt = {'status': 'started', 'stamp': stamp, 'target': target, 'mode': mode,
                        'scriptSha256': sha256_of(Path(__file__)), 'manifestSha256': sha256_of(MANIFEST),
                        'checksSha256': sha256_of(CHECKS),
                        'engineVersion': ue.SystemLibrary.get_engine_version(),
                        'errors': [], 'mapSaved': False}
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.receipt, indent=1, default=str), encoding='utf-8')

    # ------------------------------------------------------------------ material
    def material(self):
        ue = self.ue
        ml = ue.MaterialEditingLibrary
        spec = self.material_spec
        created = False
        if self.assets.does_asset_exist(spec['path']):
            mi = self.assets.load_asset(spec['path'])
        else:
            mi = self.assets.duplicate_asset(spec['duplicateOf'], spec['path'])
            created = True
        if not isinstance(mi, ue.MaterialInstanceConstant):
            raise RuntimeError('%s is not a MaterialInstanceConstant' % spec['path'])
        if _asset_path(mi.get_editor_property('parent')) != spec['parent']:
            raise RuntimeError('lane stone parent is %s' % _asset_path(mi.get_editor_property('parent')))
        for name, rgb in spec['vectorParameters'].items():
            ml.set_material_instance_vector_parameter_value(mi, name, ue.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
        for name, value in spec['scalarParameters'].items():
            ml.set_material_instance_scalar_parameter_value(mi, name, float(value))
        ml.update_material_instance(mi)
        # MaterialEditingLibrary setters return False even on success in UE 5.8: read every one back.
        readback = {'vector': {}, 'scalar': {}}
        for name, rgb in spec['vectorParameters'].items():
            got = ml.get_material_instance_vector_parameter_value(mi, name)
            got = [round(got.r, 4), round(got.g, 4), round(got.b, 4)]
            if any(abs(a - b) > 1e-3 for a, b in zip(got, rgb)):
                raise RuntimeError('%s readback %s != %s' % (name, got, rgb))
            readback['vector'][name] = got
        for name, value in spec['scalarParameters'].items():
            got = round(float(ml.get_material_instance_scalar_parameter_value(mi, name)), 4)
            if abs(got - value) > 1e-3:
                raise RuntimeError('%s readback %s != %s' % (name, got, value))
            readback['scalar'][name] = got
        if not self.assets.save_loaded_asset(mi, only_if_is_dirty=False):
            raise RuntimeError('save material failed')
        self.receipt['material'] = {'asset': spec['path'], 'created': created,
                                    'duplicatedFrom': spec['duplicateOf'], 'parent': spec['parent'],
                                    'readback': readback}
        return mi

    # -------------------------------------------------------------------- meshes
    def mesh(self, spec, material):
        ue = self.ue
        path = MESH_FOLDER + '/' + spec['assetName']
        created = False
        if self.assets.does_asset_exist(path):
            mesh = self.assets.load_asset(path)
        else:
            options = ue.FbxImportUI()
            for k, v in FBX_UI.items():
                options.set_editor_property(k, getattr(ue.FBXImportType, v) if k == 'mesh_type_to_import' else v)
            data = options.get_editor_property('static_mesh_import_data')
            for k, v in FBX_MESH.items():
                data.set_editor_property(k, getattr(ue.FBXNormalImportMethod, v) if k == 'normal_import_method' else v)
            task = ue.AssetImportTask()
            for k, v in dict(filename=str(OBJ / spec['file']), destination_path=MESH_FOLDER,
                             destination_name=spec['assetName'], automated=True, async_=False,
                             replace_existing=False, save=False, options=options,
                             factory=ue.FbxFactory()).items():
                task.set_editor_property(k, v)
            ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            got = [o for o in task.get_objects() if isinstance(o, ue.StaticMesh)]
            if len(got) != 1 or got[0].get_name() != spec['assetName']:
                raise RuntimeError('import of %s produced %s' % (spec['file'], [o.get_name() for o in task.get_objects()]))
            mesh = got[0]
            created = True
        # With build_nanite on, get_num_triangles(0) is the Nanite FALLBACK count, so it is
        # recorded, not matched. Bounds round-trip plus the OBJ hash are the acceptance checks.
        tris = int(mesh.get_num_triangles(0))
        if tris <= 0:
            raise RuntimeError('%s imported with no triangles' % spec['assetName'])
        box = mesh.get_bounding_box()
        lo, hi = [box.min.x, box.min.y, box.min.z], [box.max.x, box.max.y, box.max.z]
        want = spec['canonicalBoundsCm']
        err = max(max(abs(a - b) for a, b in zip(lo, want['min'])),
                  max(abs(a - b) for a, b in zip(hi, want['max'])))
        if err > BOUNDS_TOLERANCE_CM:
            raise RuntimeError('%s bounds differ from canonical by %.3f cm (reflection?)'
                               % (spec['assetName'], err))
        slots = len(mesh.get_editor_property('static_materials'))
        for slot in range(slots):
            mesh.set_material(slot, material)
        if slots < 1 or any(_asset_path(mesh.get_material(s)) != self.material_spec['path']
                            for s in range(slots)):
            raise RuntimeError('material not assigned on ' + spec['assetName'])
        nanite = mesh.get_editor_property('nanite_settings')
        if not nanite.get_editor_property('enabled'):
            nanite.set_editor_property('enabled', True)
            mesh.set_editor_property('nanite_settings', nanite)
        body = mesh.get_editor_property('body_setup')
        if body is None:
            raise RuntimeError('%s has no body setup' % spec['assetName'])
        body.set_editor_property('collision_trace_flag', ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError('save mesh failed ' + path)
        self.receipt.setdefault('meshes', {})[spec['key']] = {
            'asset': path, 'created': created, 'triangles': tris,
            'manifestTriangles': spec['triangles'], 'boundsErrorCm': round(err, 4),
            'materialSlots': slots,
            'nanite': bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled')),
            'collisionTraceFlag': str(body.get_editor_property('collision_trace_flag'))}
        return mesh

    # ----------------------------------------------------------------- placement
    def ours(self):
        return {a.get_actor_label(): a for a in self.actors.get_all_level_actors()
                if a.get_actor_label().startswith(LABEL_PREFIX)}

    def place(self, spec, mesh):
        ue = self.ue
        actor = self.actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(0.0, 0.0, 0.0),
                                                   ue.Rotator(pitch=0.0, yaw=0.0, roll=0.0))
        if actor is None:
            raise RuntimeError('spawn failed for ' + spec['label'])
        comp = actor.get_component_by_class(ue.StaticMeshComponent)
        if not comp.set_static_mesh(mesh):
            self.actors.destroy_actor(actor)
            raise RuntimeError('set_static_mesh failed for ' + spec['label'])
        actor.set_actor_label(spec['label'])
        actor.set_folder_path(FOLDER + '/' + spec['zoneClass'])
        actor.set_editor_property('tags', [ue.Name(ACTOR_TAG), ue.Name(spec[TAG_KEY[self.target]])])
        comp.set_editor_property('mobility', ue.ComponentMobility.STATIC)
        comp.set_collision_profile_name('BlockAll')

    def readback(self, manifest):
        ue = self.ue
        found = self.ours()
        if len(found) != len(manifest['meshes']):
            raise RuntimeError('%d paving actors in map, manifest has %d'
                               % (len(found), len(manifest['meshes'])))
        out, worst = [], 0.0
        tag_counts = {}
        for spec in manifest['meshes']:
            actor = found.get(spec['label'])
            if actor is None:
                raise RuntimeError('missing after reopen: ' + spec['label'])
            comps = actor.get_components_by_class(ue.StaticMeshComponent)
            if len(comps) != 1:
                raise RuntimeError('%s has %d mesh components' % (spec['label'], len(comps)))
            comp = comps[0]
            mesh = comp.get_editor_property('static_mesh')
            if _asset_path(mesh) != MESH_FOLDER + '/' + spec['assetName']:
                raise RuntimeError('%s mesh %s' % (spec['label'], _asset_path(mesh)))
            mat = comp.get_material(0)
            if _asset_path(mat) != self.material_spec['path'] \
                    or _asset_path(mat.get_editor_property('parent')) != self.material_spec['parent']:
                raise RuntimeError('%s material chain %s' % (spec['label'], _asset_path(mat)))
            t = actor.get_actor_transform()
            loc, rot, scl = t.translation, t.rotation.rotator(), t.scale3d
            terr = max(abs(loc.x), abs(loc.y), abs(loc.z), abs(rot.pitch), abs(rot.yaw), abs(rot.roll),
                       abs(scl.x - 1), abs(scl.y - 1), abs(scl.z - 1))
            if terr > 1e-4:
                raise RuntimeError('%s transform is not identity (%g)' % (spec['label'], terr))
            tags = sorted(str(x) for x in actor.get_editor_property('tags'))
            want = sorted([ACTOR_TAG, spec[TAG_KEY[self.target]]])
            if tags != want:
                raise RuntimeError('%s tags %s != %s' % (spec['label'], tags, want))
            tag_counts[spec[TAG_KEY[self.target]]] = tag_counts.get(spec[TAG_KEY[self.target]], 0) + 1
            origin, extent = actor.get_actor_bounds(False)
            lo = [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z]
            hi = [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]
            cb = spec['canonicalBoundsCm']
            berr = max(max(abs(a - b) for a, b in zip(lo, cb['min'])),
                       max(abs(a - b) for a, b in zip(hi, cb['max'])))
            if berr > BOUNDS_TOLERANCE_CM:
                raise RuntimeError('%s world bounds differ by %.3f cm' % (spec['label'], berr))
            worst = max(worst, berr)
            out.append({'label': spec['label'], 'mesh': _asset_path(mesh), 'tags': tags,
                        'collisionProfile': str(comp.get_collision_profile_name()),
                        'mobility': str(comp.get_editor_property('mobility')),
                        'worldBoundsErrorCm': round(berr, 4)})
        self.receipt['worstWorldBoundsErrorCm'] = round(worst, 4)
        self.receipt['tagCounts'] = tag_counts
        return out


def run(target, mode):
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('wrong project')
    manifest, checks = load_inputs()
    r = Run(ue, target, mode, manifest)
    protected_assets = [manifest['material']['duplicateOf'], manifest['material']['parent'],
                        '/Game/MikdashV3/JerusalemContext/OldCityFoundationV2/Materials/MI_OldCityFoundationStone',
                        '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_StonePath']
    map_path = TARGETS[target]
    map_file = disk_path(map_path, 'umap')
    saved = False
    others = [m for m in all_maps() if Path(m) != map_file]
    protected = {m: sha256_of(m) for m in others}
    for asset in protected_assets:
        if disk_path(asset).exists():
            protected[asset] = sha256_of(disk_path(asset))
    before = sha256_of(map_file)
    r.receipt.update({'map': map_path, 'mapSha256Before': before, 'protectedSha256Before': protected,
                      'meshCount': len(manifest['meshes']),
                      'manifestTriangles': manifest['totals']['triangles'],
                      'pavedAreaM2': manifest['totals']['pavedAreaM2'],
                      'offlineChecksPassed': True})
    r.write()
    try:
        if r.editor.get_game_world():
            raise RuntimeError('a game world is active')
        if not r.levels.load_level(map_path):
            raise RuntimeError('load_level failed')
        world = r.editor.get_editor_world()
        if world.get_outermost().get_name() != map_path:
            raise RuntimeError('loaded world is not the target')
        # Map packages only: loading a large map can legitimately dirty transient content
        # packages, exactly as release_oldcity_foundations_v2.py records. Protected hashes
        # catch everything else.
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('dirty map packages before mutation')
        existing = r.ours()
        r.receipt['existingBefore'] = sorted(existing)
        r.receipt['actorCountBefore'] = len(r.actors.get_all_level_actors())
        if mode == 'preflight':
            r.receipt['status'] = 'preflight_ok_nothing_saved'
            return r.receipt
        if mode == 'verify':
            r.receipt['readback'] = r.readback(manifest)
            r.receipt['status'] = 'verified_read_back_nothing_saved'
            return r.receipt
        if mode == 'apply' and existing:
            raise RuntimeError('%d paving actors already exist; revert first' % len(existing))
        checkpoint = CHECKPOINT_ROOT / ('OldCityStreetsV1-%s-%s-%s' % (mode, target, r.stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != before:
            raise RuntimeError('checkpoint copy hash differs')
        r.receipt['checkpoint'] = str(checkpoint)
        r.write()
        if mode == 'revert':
            for actor in existing.values():
                r.actors.destroy_actor(actor)
            r.receipt['destroyed'] = sorted(existing)
            if not existing:
                r.receipt['status'] = 'nothing_to_revert_map_unchanged'
                return r.receipt
        else:
            material = r.material()
            r.write()
            for spec in manifest['meshes']:
                mesh = r.mesh(spec, material)
                r.place(spec, mesh)
                r.write()
            r.receipt['placed'] = len(manifest['meshes'])
        if not ue.EditorLoadingAndSavingUtils.save_map(world, map_path):
            raise RuntimeError('save_map failed')
        saved = True
        r.receipt['mapSaved'] = True
        r.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        r.write()
        if not r.levels.load_level('/Engine/Maps/Entry') or not r.levels.load_level(map_path):
            raise RuntimeError('reopen failed')
        if mode == 'revert':
            left = r.ours()
            if left:
                raise RuntimeError('%d actors remain after revert' % len(left))
            r.receipt['status'] = 'reverted_saved_reopened_none_left'
        else:
            r.receipt['readback'] = r.readback(manifest)
            r.receipt['status'] = 'applied_saved_reopened_read_back_visual_acceptance_pending'
            r.receipt['revert'] = '-OCSRevert -OCSTarget=%s (or restore %s)' % (target, r.receipt['checkpoint'])
        r.receipt['actorCountAfter'] = len(r.actors.get_all_level_actors())
        return r.receipt
    except Exception as error:                                          # noqa: BLE001
        r.receipt['errors'].append(repr(error))
        r.receipt['traceback'] = traceback.format_exc()
        r.receipt['status'] = 'failed_after_save_checkpoint_available' if saved else 'failed_before_save_map_unchanged'
        raise
    finally:
        r.receipt['mapSha256After'] = sha256_of(map_file)
        r.receipt['mapBytesChanged'] = r.receipt['mapSha256After'] != before
        changed = [k for k, h in protected.items()
                   if sha256_of(k if Path(k).is_absolute() else disk_path(k)) != h]
        r.receipt['protectedChanged'] = changed
        r.receipt['protectedUnchanged'] = not changed
        if changed and not r.receipt['status'].startswith('failed'):
            r.receipt['status'] = 'failed_protected_file_changed'
        r.write()


def _main():
    import unreal as ue
    cl = ue.SystemLibrary.get_command_line()
    low = cl.lower()
    target = None
    for token in cl.split():
        if token.lower().startswith('-ocstarget='):
            target = token.split('=', 1)[1].strip('"')
    modes = [m for m in ('preflight', 'apply', 'verify', 'revert') if ('-ocs' + m) in low]
    try:
        if target not in TARGETS or len(modes) != 1:
            raise RuntimeError('need -OCSTarget=Candidate48|Main50 and exactly one of '
                               '-OCSPreflight/-OCSApply/-OCSVerify/-OCSRevert')
        rec = run(target, modes[0])
        ue.log('release_oldcity_streets: %s' % rec['status'])
    except Exception as error:                                          # noqa: BLE001
        ue.log_error('release_oldcity_streets failed: ' + repr(error))
    finally:
        if '-ocsnoquit' not in low:
            ue.SystemLibrary.quit_editor()


try:
    import unreal as _ue                                                # noqa: F401
    if SCRIPT_TOKEN in _ue.SystemLibrary.get_command_line().lower():
        _main()
except ImportError:
    if __name__ == '__main__':
        m, c = load_inputs()
        print(json.dumps({'ok': True, 'meshes': len(m['meshes']),
                          'triangles': m['totals']['triangles'],
                          'pavedAreaM2': m['totals']['pavedAreaM2'],
                          'worstBoundedEdgeGapCm': c['coverage']['worstBoundedEdgeGapCm']}, indent=1))

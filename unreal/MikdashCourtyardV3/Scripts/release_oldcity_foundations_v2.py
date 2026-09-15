"""OldCityFoundationV2 - guarded native import and placement of the city stone foundations.

Reads SourceAssets/context-review/OldCityFoundationV2/foundations-manifest.json, written and
offline-proved by Scripts/oldcity_foundations_v2.py build (zero exposed-wall gaps over 1 cm in
check-after.json). Writes ONLY inside /Game/MikdashV3/JerusalemContext/OldCityFoundationV2 and,
in the target map, only actors labelled RELEASE_OldCityFoundationV2_*. No existing asset is
rebuilt, re-imported or edited; the V1 infill / OSM building actors are never touched.

Launch (hidden editor, NOT -run=pythonscript; start on Entry so the startup map is not loaded twice):
  UnrealEditor.exe MikdashCourtyardV3.uproject /Engine/Maps/Entry
      -ExecutePythonScript=C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_oldcity_foundations_v2.py
      -OCF2Apply -OCF2Target=Candidate48 -unattended -nullrhi -NoSplash -abslog=...
Scripts/run_oldcity_foundation_v2_engine.ps1 wraps this with the slot/memory wait.

MODES
  -OCF2Preflight   read-only: inputs, target map loads, counts existing actors. Saves nothing.
  -OCF2Apply       material + meshes if missing (verified if present), place one StaticMeshActor
                   per manifest mesh, save, REOPEN, numeric readback. Refuses if any exist.
  -OCF2Verify      reopen-style readback only. Saves nothing.
  -OCF2Revert      destroy every RELEASE_OldCityFoundationV2_* actor, save, reopen, prove none left.
                   The per-run map checkpoint in ReviewCheckpoints is the byte-level fallback.

VISIBILITY / OWNERSHIP
  Tags: OldCityFoundationV2 + CityDetailZone_Precinct or CityDetailZone_Kept, chosen per target map
  from the manifest (a mesh groups only footprints whose owner buildings share that map's precinct
  class). CityDetailZone_Precinct is in AMikdashEnclosure::HideWhileWallStandsTags, so these hide in
  YECHEZKEL and show in MODERN/OVERLAY exactly like the buildings they support; collision follows.
  The actors are plain single-mesh StaticMeshActors OUTSIDE the two audited building folders, so
  BuildingIdentityLabel() returns an empty label for them: the audited 269-owner hide list, its
  fingerprint and the LegacyRoofRuntimeV1 owner resolution are unchanged.

GUARDS
  wrong project / game world / dirty packages refuse; manifest status, generator hash and every OBJ
  hash checked; map checkpoint copied and hash-verified before mutation; all other .umap files and
  the protected source assets hashed before and after; receipt at start and in finally.
"""
import hashlib
import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SCRIPT_TOKEN = 'release_oldcity_foundations_v2.py'
SRC = ROOT / 'SourceAssets' / 'context-review' / 'OldCityFoundationV2'
MANIFEST = SRC / 'foundations-manifest.json'
GENERATOR = ROOT / 'Scripts' / 'oldcity_foundations_v2.py'
OBJ = SRC / 'obj'
RECEIPTS = SRC / 'engine'
NS = '/Game/MikdashV3/JerusalemContext/OldCityFoundationV2'
MESH_FOLDER = NS + '/Meshes'
MAT_FOLDER = NS + '/Materials'
MAT_NAME = 'MI_OldCityFoundationStone'
MAT_PATH = MAT_FOLDER + '/' + MAT_NAME
# Duplicated (never edited): the plaster instance already renders on the Nanite infill meshes, so its
# copy inherits a working parent chain and any usage overrides. Only the tints/scale change.
MAT_SOURCE = '/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Materials/MI_OldCityPlaster'
MAT_PARENT = '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building'
MAT_VECTOR = {'Tint0': [0.86, 0.81, 0.72], 'Tint1': [0.79, 0.75, 0.67], 'Tint2': [0.91, 0.86, 0.76],
              'Tint3': [0.74, 0.71, 0.65], 'RoofTint': [0.70, 0.67, 0.61]}
MAT_SCALAR = {'TileCm': 240.0, 'RoughVar': 0.16, 'VCInfluence': 0.0, 'HashVertexColorWeight': 0.0}
TARGETS = {
    'Candidate48': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'Main50': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}
TAG_KEY = {'Candidate48': 'tagCandidate', 'Main50': 'tagMain'}
PROTECTED_ASSETS = [MAT_SOURCE, MAT_PARENT,
                    '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall']
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
LABEL_PREFIX = 'RELEASE_OldCityFoundationV2_'
ACTOR_TAG = 'OldCityFoundationV2'
ZONE_TAGS = ('CityDetailZone_Precinct', 'CityDetailZone_Kept')
FOLDER = 'Release/OldCityFoundationV2'
BOUNDS_TOLERANCE_CM = 1.0
FBX_UI = {'automated_import_should_detect_type': False, 'mesh_type_to_import': 'FBXIT_STATIC_MESH',
          'import_as_skeletal': False, 'import_mesh': True, 'import_animations': False,
          'import_materials': False, 'import_textures': False, 'create_physics_asset': False}
# release_oldcity_facades.spec.json importSettings (the reviewed V1 infill import), verbatim.
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
    after = json.loads((SRC / 'check-after.json').read_text(encoding='utf-8'))
    if after['over1cmNotExcluded'] != 0 or after['downwardFacingTriangles'] != 0:
        raise RuntimeError('offline check-after does not pass; refusing to import')
    for mesh in manifest['meshes']:
        if sha256_of(OBJ / mesh['file']) != mesh['sha256']:
            raise RuntimeError('OBJ hash changed: ' + mesh['file'])
        if mesh['tagCandidate'] not in ZONE_TAGS or mesh['tagMain'] not in ZONE_TAGS:
            raise RuntimeError('bad zone tag in ' + mesh['key'])
    return manifest


class Run:
    def __init__(self, ue, target, mode):
        self.ue = ue
        self.target = target
        self.mode = mode
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
                        'engineVersion': ue.SystemLibrary.get_engine_version(), 'errors': [], 'mapSaved': False}
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.receipt, indent=1, default=str), encoding='utf-8')

    # ------------------------------------------------------------------ material
    def material(self):
        ue = self.ue
        ml = ue.MaterialEditingLibrary
        created = False
        if self.assets.does_asset_exist(MAT_PATH):
            mi = self.assets.load_asset(MAT_PATH)
        else:
            mi = self.assets.duplicate_asset(MAT_SOURCE, MAT_PATH)
            created = True
        if not isinstance(mi, ue.MaterialInstanceConstant):
            raise RuntimeError('%s is not a MaterialInstanceConstant' % MAT_PATH)
        if _asset_path(mi.get_editor_property('parent')) != MAT_PARENT:
            raise RuntimeError('foundation material parent is %s' % _asset_path(mi.get_editor_property('parent')))
        for name, rgb in MAT_VECTOR.items():
            ml.set_material_instance_vector_parameter_value(mi, name, ue.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
        for name, value in MAT_SCALAR.items():
            ml.set_material_instance_scalar_parameter_value(mi, name, float(value))
        ml.update_material_instance(mi)
        readback = {'vector': {}, 'scalar': {}}
        for name, rgb in MAT_VECTOR.items():       # setters return False even on success: read back
            got = ml.get_material_instance_vector_parameter_value(mi, name)
            got = [round(got.r, 4), round(got.g, 4), round(got.b, 4)]
            if any(abs(a - b) > 1e-3 for a, b in zip(got, rgb)):
                raise RuntimeError('%s readback %s != %s' % (name, got, rgb))
            readback['vector'][name] = got
        for name, value in MAT_SCALAR.items():
            got = round(float(ml.get_material_instance_scalar_parameter_value(mi, name)), 4)
            if abs(got - value) > 1e-3:
                raise RuntimeError('%s readback %s != %s' % (name, got, value))
            readback['scalar'][name] = got
        if not self.assets.save_loaded_asset(mi, only_if_is_dirty=False):
            raise RuntimeError('save material failed')
        self.receipt['material'] = {'asset': MAT_PATH, 'created': created, 'duplicatedFrom': MAT_SOURCE,
                                    'parent': MAT_PARENT, 'readback': readback}
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
                             replace_existing=False, save=False, options=options, factory=ue.FbxFactory()).items():
                task.set_editor_property(k, v)
            ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            got = [o for o in task.get_objects() if isinstance(o, ue.StaticMesh)]
            if len(got) != 1 or got[0].get_name() != spec['assetName']:
                raise RuntimeError('import of %s produced %s' % (spec['file'], [o.get_name() for o in task.get_objects()]))
            mesh = got[0]
            created = True
        # With build_nanite on, get_num_triangles(0) is the Nanite FALLBACK count (~11 % for V1,
        # release_oldcity_facades.spec.json requireTriangleMatch note), so it is recorded, not matched.
        # Bounds round-trip plus the OBJ hash are the acceptance checks, as for V1.
        tris = int(mesh.get_num_triangles(0))
        if tris <= 0:
            raise RuntimeError('%s imported with no triangles' % spec['assetName'])
        box = mesh.get_bounding_box()
        lo, hi = [box.min.x, box.min.y, box.min.z], [box.max.x, box.max.y, box.max.z]
        want = spec['canonicalBoundsCm']
        err = max(max(abs(a - b) for a, b in zip(lo, want['min'])), max(abs(a - b) for a, b in zip(hi, want['max'])))
        if err > BOUNDS_TOLERANCE_CM:
            raise RuntimeError('%s bounds differ from canonical by %.3f cm (reflection?)' % (spec['assetName'], err))
        slots = len(mesh.get_editor_property('static_materials'))
        for slot in range(slots):
            mesh.set_material(slot, material)
        if slots < 1 or any(_asset_path(mesh.get_material(s)) != MAT_PATH for s in range(slots)):
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
        info = {'asset': path, 'created': created, 'triangles': tris, 'manifestTriangles': spec['triangles'],
                'boundsErrorCm': round(err, 4), 'materialSlots': slots,
                'nanite': bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled')),
                'collisionTraceFlag': str(body.get_editor_property('collision_trace_flag'))}
        self.receipt.setdefault('meshes', {})[spec['key']] = info
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
            raise RuntimeError('%d foundation actors in map, manifest has %d' % (len(found), len(manifest['meshes'])))
        labels = {a.get_actor_label() for a in self.actors.get_all_level_actors()}
        out, worst = [], 0.0
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
            if _asset_path(mat) != MAT_PATH or _asset_path(mat.get_editor_property('parent')) != MAT_PARENT:
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
            origin, extent = actor.get_actor_bounds(False)
            lo = [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z]
            hi = [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]
            cb = spec['canonicalBoundsCm']
            berr = max(max(abs(a - b) for a, b in zip(lo, cb['min'])), max(abs(a - b) for a, b in zip(hi, cb['max'])))
            if berr > BOUNDS_TOLERANCE_CM:
                raise RuntimeError('%s world bounds differ by %.3f cm' % (spec['label'], berr))
            missing_owners = [o for o in spec['owners'] if o not in labels]
            worst = max(worst, berr)
            out.append({'label': spec['label'], 'mesh': _asset_path(mesh), 'tags': tags,
                        'collisionProfile': str(comp.get_collision_profile_name()),
                        'mobility': str(comp.get_editor_property('mobility')), 'worldBoundsErrorCm': round(berr, 4),
                        'owners': len(spec['owners']), 'ownersMissingInMap': missing_owners})
        self.receipt['worstWorldBoundsErrorCm'] = round(worst, 4)
        self.receipt['ownersMissingInMap'] = sorted({o for row in out for o in row['ownersMissingInMap']})
        return out


def run(target, mode):
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('wrong project')
    r = Run(ue, target, mode)
    map_path = TARGETS[target]
    map_file = disk_path(map_path, 'umap')
    saved = False
    others = [m for m in all_maps() if Path(m) != map_file]
    protected = {m: sha256_of(m) for m in others}
    protected.update({a: sha256_of(disk_path(a)) for a in PROTECTED_ASSETS})
    before = sha256_of(map_file)
    r.receipt.update({'map': map_path, 'mapSha256Before': before, 'protectedSha256Before': protected})
    r.write()
    try:
        manifest = load_inputs()
        r.receipt['meshCount'] = len(manifest['meshes'])
        r.receipt['manifestTriangles'] = manifest['totals']['triangles']
        if r.editor.get_game_world():
            raise RuntimeError('a game world is active')
        if not r.levels.load_level(map_path):
            raise RuntimeError('load_level failed')
        world = r.editor.get_editor_world()
        if world.get_outermost().get_name() != map_path:
            raise RuntimeError('loaded world is not the target')
        # Map packages only: loading a large map can legitimately dirty transient content packages
        # (the release_shell_openings.py guard makes the same choice). Protected hashes catch the rest.
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
            raise RuntimeError('%d foundation actors already exist; revert first' % len(existing))
        checkpoint = CHECKPOINT_ROOT / ('OldCityFoundationV2-%s-%s-%s' % (mode, target, r.stamp))
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
            r.receipt['revert'] = '-OCF2Revert -OCF2Target=%s (or restore %s)' % (target, r.receipt['checkpoint'])
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
        changed = [k for k, h in protected.items() if sha256_of(k if Path(k).is_absolute() else disk_path(k)) != h]
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
    for tok in cl.split():
        if tok.lower().startswith('-ocf2target='):
            target = tok.split('=', 1)[1].strip('"')
    modes = [m for m in ('preflight', 'apply', 'verify', 'revert') if ('-ocf2' + m) in low]
    try:
        if target not in TARGETS or len(modes) != 1:
            raise RuntimeError('need -OCF2Target=Candidate48|Main50 and exactly one of -OCF2Preflight/-OCF2Apply/-OCF2Verify/-OCF2Revert')
        rec = run(target, modes[0])
        ue.log('release_oldcity_foundations_v2: %s' % rec['status'])
    except Exception as error:                                          # noqa: BLE001
        ue.log_error('release_oldcity_foundations_v2 failed: ' + repr(error))
    finally:
        if '-ocf2noquit' not in low:
            ue.SystemLibrary.quit_editor()


try:
    import unreal as _ue                                                # noqa: F401
    if SCRIPT_TOKEN in _ue.SystemLibrary.get_command_line().lower():
        _main()
except ImportError:
    if __name__ == '__main__':
        m = load_inputs()
        print(json.dumps({'ok': True, 'meshes': len(m['meshes']), 'triangles': m['totals']['triangles']}, indent=1))

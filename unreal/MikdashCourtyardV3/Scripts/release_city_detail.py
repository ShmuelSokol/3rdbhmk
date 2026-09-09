"""Guarded, resumable native import and instancing of CityDetailV1.

Imports the twelve unit OBJs written by Scripts/create_city_detail.py into
/Game/MikdashV3/JerusalemContext/CityDetailV1/Meshes with Nanite OFF, creates the five
MaterialInstanceConstants the manifest describes (parent M_Context_Building, verified by
readback), then spawns ONE actor per (zone, mesh) pair carrying ONE
HierarchicalInstancedStaticMeshComponent and fills it from the plan. It saves, reopens and
reads back every component's instance count and a numeric sample of its instance transforms.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_city_detail.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/CityDetail-01.log"
      -CityDetailTarget=candidate -CityDetailMaxGroups=6

Switches (read from the engine command line):
  -CityDetailTarget=candidate|main   which map. `candidate` is the default and is the
                                     Amah48 candidate the project ships as its default map;
                                     `main` is the legacy Main50 combined map. Both carry the
                                     same city at the same coordinates (the 0.48 m amah
                                     conversion moved the Temple about the origin only -
                                     precinct-Candidate48.json: "city and terrain metric and
                                     unmoved"), so one plan serves both.
  -CityDetailGroups=parapet,dome     only these mesh keys.
  -CityDetailMaxGroups=N             stop after N (zone, mesh) groups this run. Memory valve.
  -CityDetailResume                  rebuild any group whose instance count does not match the
                                     plan; without it a partially filled group is a refusal.
  -CityDetailImportOnly              import and material work only; place nothing.
  -CityDetailRebuild                 re-import every unit mesh over itself (replace_existing)
                                     and destroy and rebuild every selected group. This is the
                                     switch to use after the generator is re-run: an existing
                                     asset is otherwise kept as it is, and a group whose
                                     instance COUNT happens to be unchanged would keep stale
                                     transforms under a newly pinned plan hash.
  -CityDetailRetint                  ALSO apply MI_CityDetail_CityStone as a per-COMPONENT
                                     material override on the SM_JerusalemBuildings_* actors.
                                     Off by default. See RETINT below.

WHY IT IS SHAPED THIS WAY
-------------------------
PERFORMANCE-BUDGET.md measured the frame after the Nanite pass as game-thread bound: game
thread 28.7 ms against a GPU of 17.0 ms, with 7,767 actors. The addition here is 87 k
instances of twelve props, and the only acceptable shape for that is instanced components:
it costs 24 actors and 24 base-pass draw calls, not 11,437 anything. Nanite is deliberately
NOT enabled - these are 24 to 84 triangle props and classic HISM honours the per-instance
cull distances the plan depends on, which is what keeps the small roof plant out of the far
city view and out of ShadowDepths.

ZONES, AND THE PRECINCT PLAZA
-----------------------------
A second job in this wave builds a flat plaza over the Yechezkel precinct, which at run time
hides whole building actors (policy hide_if_any_inside, 270 actors). Every instance is
therefore assigned in the plan to the zone of the actor it decorates, and the two zones go
into SEPARATE actors:

    RELEASE_CityDetail_Kept_<Mesh>        decorates buildings that stay
    RELEASE_CityDetail_Precinct_<Mesh>    decorates buildings the precinct hides

so hiding the precinct's buildings can hide their roofscape with them by the same actor-label
rule and nothing is left floating over the plaza. Both sets carry the tag CityDetailV1 and
the zone tag CityDetailZone_Kept / CityDetailZone_Precinct.

RETINT (off by default, and why it is separate)
-----------------------------------------------
Jerusalem has required stone facing on every building since the 1918 town-planning ordinance
issued under the military governor Ronald Storrs, carried into the Mandate planning schemes
and still enforced by the municipality; the city is one pale limestone family with the
Herodian ashlar, not brown. -CityDetailRetint applies that as a per-COMPONENT material
override on the building actors, using a MaterialInstanceConstant whose PARENT is the
existing M_Context_Building. It therefore:
  * never edits M_Context_Building, never edits the 1,499 building mesh assets, and never
    touches M_PBR_Tiled, the nine Nanite-repaired MI_PBR_* instances or any AntiRepeatV1
    asset - the concurrent material job owns those;
  * inherits any improvement that job makes to the context graph instead of fighting it;
  * is reversible: -CityDetailRetintClear removes the overrides and restores the asset
    material.

SAFETY MODEL (release_oldcity_facades.py / release_place_assets.py pattern)
--------------------------------------------------------------------------
  * Refuses on the wrong project directory, an active game world, dirty packages, or a loaded
    world that is not the requested target.
  * Verifies the spec hash, the manifest hash and status, the plan hash, and the SHA-256 of
    every OBJ, before touching anything.
  * Copies the target .umap (and any One-File-Per-Actor folders) to ReviewCheckpoints/ and
    verifies the copy before any mutation.
  * Writes only inside /Game/MikdashV3/JerusalemContext/CityDetailV1.
  * Saves only if at least one group completed, reloads the map, and reads back every
    component's instance count plus a numeric transform sample against the plan.
  * The receipt JSON is written at start and again in finally, so a failure preserves state.

UE 5.8 PYTHON PITFALLS HANDLED HERE (AGENTS.md)
------------------------------------------------
  * MaterialEditingLibrary setters return False even on success: every parameter is verified
    by readback.
  * MaterialEditingLibrary has no set_material_default_*; every material here is a
    MaterialInstanceConstant, never an edited Material.
  * spawn_actor_from_object returns None in commandlets: actors are spawned from a class.
  * AActor.add_component_by_class is NOT exposed to Python in UE 5.8 - it raises
    AttributeError, which is how the first run of this script failed (receipt
    native-city-detail-candidate-20260909T222341385928Z.json). The editor subobject path
    (SubobjectDataSubsystem.add_new_subobject) is used instead, the same one
    Scripts/import_instances_ue58.py used for the DecorativeInstancesV1 prototypes, and
    component ownership is verified three ways before any instance is added.
  * unreal.Rotator needs explicit pitch/yaw/roll keywords.
  * unreal.Transform's positional order is (rotation, translation, scale), which is NOT the
    order a reader expects; this script builds transforms by keyword, records which
    construction path worked, and then verifies instance transforms numerically. A silently
    swapped location and rotation is exactly the bug that survives an instance-count check.
  * StaticMeshEditorSubsystem is None under -run=pythonscript, so nothing here depends on it.
  * Mobility lives on the component, not the actor.
  * Numeric transform fields are compared, never str(Transform).
"""

import gc
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_city_detail.spec.json'
SCRIPT_TOKEN = 'release_city_detail.py'


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so offline_check() runs anywhere.
# --------------------------------------------------------------------------
def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def target_map(spec, key):
    if key not in spec['targetMaps']:
        raise ValueError('Unknown target %r; have %s' % (key, sorted(spec['targetMaps'])))
    return spec['targetMaps'][key]['map']


def load_manifest(spec):
    path = ROOT / spec['source']['manifest']
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    actual = sha256_of(path)
    if actual != spec['source']['manifestSha256']:
        raise RuntimeError('city-detail-manifest.json SHA256 %s is not the reviewed revision %s'
                           % (actual, spec['source']['manifestSha256']))
    if manifest['status'] != spec['source']['manifestStatusRequired']:
        raise RuntimeError('Manifest status %s is not %s'
                           % (manifest['status'], spec['source']['manifestStatusRequired']))
    return manifest, actual


def load_plan(spec):
    path = ROOT / spec['source']['plan']
    actual = sha256_of(path)
    if actual != spec['source']['planSha256']:
        raise RuntimeError('city-detail-plan.json SHA256 %s is not the reviewed revision %s'
                           % (actual, spec['source']['planSha256']))
    return json.loads(path.read_text(encoding='utf-8-sig')), actual


def group_jobs(spec, manifest, plan):
    """One job per (zone, mesh key): that is exactly one actor and one HISM component."""
    mesh_by_key = {record['key']: record for record in manifest['meshes']}
    grouped = {}
    for batch in plan['batches']:
        key = (batch['zone'], batch['meshKey'])
        grouped.setdefault(key, []).append(batch)
    jobs = []
    for (zone, mesh_key), batches in sorted(grouped.items()):
        mesh = mesh_by_key[mesh_key]
        batches.sort(key=lambda item: item['batchId'])
        label = '%s%s_%s_%s' % (spec['labelPrefix'], spec['group'],
                                zone.capitalize(), mesh['assetName'].split('_')[-1])
        jobs.append({
            'zone': zone,
            'meshKey': mesh_key,
            'assetName': mesh['assetName'],
            'assetPath': spec['meshFolder'] + '/' + mesh['assetName'],
            'objFile': mesh['file'],
            'sha256': mesh['sha256'],
            'triangles': mesh['triangles'],
            'canonicalBoundsCm': mesh['canonicalBoundsCm'],
            'materialKey': mesh['materialKey'],
            'castShadow': bool(mesh['castShadow']),
            'cullDistanceCm': float(mesh['cullDistanceCm']),
            'label': label,
            'batchIds': [batch['batchId'] for batch in batches],
            'instances': sum(batch['count'] for batch in batches),
            'rows': [row for batch in batches for row in batch['rows']],
        })
    jobs.sort(key=lambda job: (-job['instances'], job['label']))
    return jobs


def mesh_jobs(spec, manifest):
    """One import job per unit mesh, independent of how many zones use it."""
    return [{
        'assetName': mesh['assetName'],
        'assetPath': spec['meshFolder'] + '/' + mesh['assetName'],
        'objFile': mesh['file'],
        'sha256': mesh['sha256'],
        'triangles': mesh['triangles'],
        'vertices': mesh['vertices'],
        'canonicalBoundsCm': mesh['canonicalBoundsCm'],
        'materialKey': mesh['materialKey'],
        'yAsymmetric': bool(mesh['yAsymmetric']),
    } for mesh in manifest['meshes']]


def parse_keys(text, available):
    wanted = set()
    for token in str(text).replace('"', '').split(','):
        token = token.strip()
        if token:
            wanted.add(token)
    unknown = sorted(wanted - available)
    if unknown:
        raise ValueError('Unknown mesh keys: %s (have %s)' % (unknown, sorted(available)))
    return wanted


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def offline_check(spec=None, target='candidate'):
    """Everything verifiable without the engine. Runs before any mutation."""
    spec = spec or load_spec()
    manifest, manifest_sha = load_manifest(spec)
    plan, plan_sha = load_plan(spec)
    script_sha = sha256_of(ROOT / spec['source']['authoringScript'])
    obj_dir = ROOT / spec['source']['objFolder']
    missing, mismatched, bytes_total = [], [], 0
    for mesh in mesh_jobs(spec, manifest):
        path = obj_dir / mesh['objFile']
        if not path.exists():
            missing.append(mesh['objFile'])
            continue
        if sha256_of(path) != mesh['sha256']:
            mismatched.append(mesh['objFile'])
        bytes_total += path.stat().st_size
    if missing:
        raise RuntimeError('Missing generated OBJs: %s' % missing)
    if mismatched:
        raise RuntimeError('OBJ contents changed since the manifest was written: %s' % mismatched)
    jobs = group_jobs(spec, manifest, plan)
    instances = sum(job['instances'] for job in jobs)
    if instances != manifest['totals']['instances']:
        raise RuntimeError('Plan carries %d instances, manifest says %d'
                           % (instances, manifest['totals']['instances']))
    if len(jobs) != manifest['totals']['hismComponents']:
        raise RuntimeError('Plan yields %d components, manifest says %d'
                           % (len(jobs), manifest['totals']['hismComponents']))
    if manifest['reconstructionVerification']['matchRatio'] < spec['verification']['minimumMatchRatio']:
        raise RuntimeError('Footprint reconstruction match ratio %.4f is below the spec minimum'
                           % manifest['reconstructionVerification']['matchRatio'])
    if manifest['totals']['yAsymmetricMeshes'] < spec['verification']['minimumYAsymmetricMeshes']:
        raise RuntimeError('Only %d unit meshes are asymmetric in Y; the bounds round-trip could '
                           'not prove the OBJ reflection'
                           % manifest['totals']['yAsymmetricMeshes'])
    map_asset = target_map(spec, target)
    map_file = disk_path(map_asset, 'umap')
    return {
        'status': 'offline_spec_and_source_consistent',
        'target': target,
        'targetMap': map_asset,
        'specSha256': sha256_of(SPEC_PATH),
        'manifestSha256': manifest_sha,
        'planSha256': plan_sha,
        'authoringScriptSha256': script_sha,
        'authoringScriptMatchesSpec': script_sha == spec['source']['authoringScriptSha256'],
        'unitMeshes': len(manifest['meshes']),
        'objBytes': bytes_total,
        'groups': [{'label': job['label'], 'zone': job['zone'], 'mesh': job['assetName'],
                    'instances': job['instances']} for job in jobs],
        'groupCount': len(jobs),
        'instances': instances,
        'lod0Triangles': manifest['totals']['lod0Triangles'],
        'byZone': {zone: entry['instances'] for zone, entry in manifest['totals']['byZone'].items()},
        'footprintMatchRatio': manifest['reconstructionVerification']['matchRatio'],
        'targetMapSha256': sha256_of(map_file) if map_file.exists() else None,
        'namespaceOnDisk': (ROOT / 'Content' / spec['namespace'][len('/Game/'):]).exists(),
    }


# --------------------------------------------------------------------------
# Native side
# --------------------------------------------------------------------------
def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _xyz(vector):
    return [float(vector.x), float(vector.y), float(vector.z)]


def _static_mesh_box(mesh):
    box = mesh.get_bounding_box()
    return {'min': _xyz(box.min), 'max': _xyz(box.max)}


class Run:
    def __init__(self, ue, spec, manifest, plan, target_key):
        self.ue = ue
        self.spec = spec
        self.manifest = manifest
        self.plan = plan
        self.target_key = target_key
        self.target = target_map(spec, target_key)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.receipt = {}
        self.receipt_path = None
        self.world = None
        self.materials = {}
        self.transform_path = None

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2) + '\n', encoding='utf-8')

    # ---------------------------------------------------------------- state
    def existing_assets(self):
        folder = self.spec['meshFolder']
        if not self.assets.does_directory_exist(folder):
            return set()
        return {str(path).split('/')[-1].split('.')[0]
                for path in self.assets.list_assets(folder, recursive=True, include_folder=False)}

    def our_actors(self):
        prefix = self.spec['labelPrefix'] + self.spec['group']
        found = {}
        for actor in self.actors.get_all_level_actors():
            label = actor.get_actor_label()
            if label.startswith(prefix):
                found[label] = actor
        return found

    # ------------------------------------------------------------ materials
    def material(self, key):
        """MaterialInstanceConstant under CityDetailV1, parented on the context building base."""
        if key in self.materials:
            return self.materials[key]
        ue = self.ue
        cfg = self.manifest['materials'][key]
        parent_path = self.spec['materials']['parent']
        path = self.spec['materialFolder'] + '/' + cfg['name']
        parent = ue.load_asset(parent_path)
        if not isinstance(parent, ue.MaterialInterface):
            raise RuntimeError('Parent material did not load: ' + parent_path)
        created = False
        if self.assets.does_asset_exist(path):
            instance = ue.load_asset(path)
            if not isinstance(instance, ue.MaterialInstanceConstant):
                raise RuntimeError('%s exists but is not a MaterialInstanceConstant' % path)
        else:
            folder, name = path.rsplit('/', 1)
            instance = ue.AssetToolsHelpers.get_asset_tools().create_asset(
                name, folder, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew())
            if instance is None:
                raise RuntimeError('Could not create ' + path)
            created = True
        if _asset_path(instance.get_editor_property('parent')) != parent_path:
            instance.set_editor_property('parent', parent)
        if _asset_path(instance.get_editor_property('parent')) != parent_path:
            raise RuntimeError('%s parent is not %s' % (path, parent_path))
        edit = ue.MaterialEditingLibrary
        # UE 5.8: these setters return False even on success. Readback is the only check.
        for name, rgb in cfg['vector'].items():
            edit.set_material_instance_vector_parameter_value(
                instance, name, ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
        for name, value in cfg['scalar'].items():
            edit.set_material_instance_scalar_parameter_value(instance, name, float(value))
        edit.update_material_instance(instance)
        readback = {'vector': {}, 'scalar': {}}
        wrong = []
        for name, rgb in cfg['vector'].items():
            value = edit.get_material_instance_vector_parameter_value(instance, name)
            got = [round(float(value.r), 4), round(float(value.g), 4), round(float(value.b), 4)]
            readback['vector'][name] = got
            if max(abs(got[i] - float(rgb[i])) for i in range(3)) > 1e-3:
                wrong.append(name)
        for name, value in cfg['scalar'].items():
            got = round(float(edit.get_material_instance_scalar_parameter_value(instance, name)), 5)
            readback['scalar'][name] = got
            if abs(got - float(value)) > 1e-4:
                wrong.append(name)
        if wrong:
            raise RuntimeError('%s parameters did not take: %s' % (path, sorted(set(wrong))))
        if not self.assets.save_loaded_asset(instance, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        self.receipt['materials'][key] = {
            'asset': path, 'created': created, 'parent': parent_path, 'why': cfg['why'],
            'readback': readback,
            'note': 'Setters are not trusted; every value above was read back from the instance.'}
        self.materials[key] = instance
        return instance

    # --------------------------------------------------------------- import
    def import_mesh(self, job, replace=False):
        ue = self.ue
        settings = self.spec['importSettings']
        path = ROOT / self.spec['source']['objFolder'] / job['objFile']
        if sha256_of(path) != job['sha256']:
            raise RuntimeError('OBJ hash changed since offline check: ' + job['objFile'])
        options = ue.FbxImportUI()
        for key, value in settings['fbxImportUI'].items():
            if key == 'mesh_type_to_import':
                value = getattr(ue.FBXImportType, value)
            options.set_editor_property(key, value)
        data = options.get_editor_property('static_mesh_import_data')
        for key, value in settings['staticMeshImportData'].items():
            if key == 'normal_import_method':
                value = getattr(ue.FBXNormalImportMethod, value)
            data.set_editor_property(key, value)
        task = ue.AssetImportTask()
        for key, value in dict(filename=str(path), destination_path=self.spec['meshFolder'],
                               destination_name=job['assetName'], automated=True, async_=False,
                               replace_existing=bool(replace), save=False, options=options,
                               factory=ue.FbxFactory()).items():
            task.set_editor_property(key, value)
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objects = [obj for obj in task.get_objects() if isinstance(obj, ue.StaticMesh)]
        if len(objects) != 1:
            raise RuntimeError('Import of %s produced %s'
                               % (job['objFile'], [type(obj).__name__ for obj in task.get_objects()]))
        mesh = objects[0]
        if mesh.get_name() != job['assetName']:
            raise RuntimeError('Imported name %s differs from %s' % (mesh.get_name(), job['assetName']))
        return mesh

    def verify_and_assign(self, mesh, job):
        spec = self.spec
        box = _static_mesh_box(mesh)
        error = box_error(box, job['canonicalBoundsCm'])
        if error > spec['source']['boundsToleranceCm']:
            raise RuntimeError('%s bounds differ from canonical by %.4f cm (Y reflection did not '
                               'round-trip?): %r' % (job['assetName'], error, box))
        triangles = int(mesh.get_num_triangles(0))
        if spec['verification']['requireTriangleMatch'] and triangles != job['triangles']:
            raise RuntimeError('%s has %d triangles, manifest says %d'
                               % (job['assetName'], triangles, job['triangles']))
        slots = len(mesh.get_editor_property('static_materials'))
        if slots != 1:
            raise RuntimeError('%s has %d material slots, expected exactly 1 (one o, no g groups)'
                               % (job['assetName'], slots))
        material = self.material(job['materialKey'])
        mesh.set_material(0, material)
        expected = _asset_path(material)
        if _asset_path(mesh.get_material(0)) != expected:
            raise RuntimeError('Material slot not assigned on ' + job['assetName'])
        nanite = None
        try:
            nanite = bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
        except Exception as error:                                    # noqa: BLE001
            nanite = 'unreadable: %r' % (error,)
        if nanite is True:
            raise RuntimeError('%s imported with Nanite on; this set is deliberately classic HISM'
                               % job['assetName'])
        return {'asset': _asset_path(mesh), 'triangles': triangles,
                'renderVertices': int(mesh.get_num_vertices(0)), 'materialSlots': slots,
                'material': expected, 'materialKey': job['materialKey'],
                'boundsErrorCm': error, 'localBoundsCm': box,
                'yAsymmetric': job['yAsymmetric'], 'naniteEnabled': nanite}

    # ------------------------------------------------------------ transforms
    def make_transform(self, row):
        """Build one instance transform, by keyword, never positionally.

        unreal.Transform's positional order is (rotation, translation, scale). Passing a
        location first silently produces a rotation and an instance at the origin, and an
        instance-count check would never see it, so the keyword form is used and the first
        transform of every run is read back numerically below.
        """
        ue = self.ue
        location = ue.Vector(float(row[0]), float(row[1]), float(row[2]))
        rotation = ue.Rotator(pitch=float(row[4]), yaw=float(row[3]), roll=float(row[5]))
        scale = ue.Vector(float(row[6]), float(row[7]), float(row[8]))
        if self.transform_path is None:
            self.transform_path = self._probe_transform_path(location, rotation, scale)
        if self.transform_path == 'keyword_rotation_translation_scale':
            return ue.Transform(rotation=rotation, translation=location, scale=scale)
        transform = ue.Transform()
        transform.set_editor_property('translation', location)
        transform.set_editor_property('rotation', rotation.quaternion())
        transform.set_editor_property('scale3d', scale)
        return transform

    def _probe_transform_path(self, location, rotation, scale):
        ue = self.ue
        try:
            probe = ue.Transform(rotation=rotation, translation=location, scale=scale)
            got = probe.get_editor_property('translation')
            if (abs(got.x - location.x) < 1e-3 and abs(got.y - location.y) < 1e-3
                    and abs(got.z - location.z) < 1e-3):
                self.receipt['transformConstruction'] = 'keyword_rotation_translation_scale'
                return 'keyword_rotation_translation_scale'
        except Exception as error:                                    # noqa: BLE001
            self.receipt.setdefault('limitations', []).append(
                'unreal.Transform keyword construction unavailable (%r); fell back to '
                'set_editor_property' % (error,))
        self.receipt['transformConstruction'] = 'set_editor_property'
        return 'set_editor_property'

    # ------------------------------------------------------------- placement
    def new_hism(self, actor):
        """Instance-owned HISM on a plain editor actor.

        UE 5.8 does not expose AActor::AddComponentByClass to Python (the vegetation script's
        call raises AttributeError here), and merely constructing
        unreal.HierarchicalInstancedStaticMeshComponent(outer=actor) produces a component the
        level never owns. The editor's own subobject path is used instead, exactly as
        Scripts/import_instances_ue58.py does for the DecorativeInstancesV1 prototypes, and
        ownership is verified three ways before anything is added to it.
        """
        ue = self.ue
        subsystem = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
        library = ue.SubobjectDataBlueprintFunctionLibrary
        handles = subsystem.k2_gather_subobject_data_for_instance(actor)
        parent = next((handle for handle in handles
                       if library.get_associated_object(library.get_data(handle)) == actor), None)
        if parent is None:
            raise RuntimeError('Editor actor subobject handle missing')
        params = ue.AddNewSubobjectParams(
            parent_handle=parent,
            new_class=ue.HierarchicalInstancedStaticMeshComponent,
            blueprint_context=None, conform_transform_to_parent=True)
        handle, reason = subsystem.add_new_subobject(params)
        if not library.is_handle_valid(handle):
            raise RuntimeError('Persistent HISM creation failed: ' + str(reason))
        data = library.get_data(handle)
        component = library.get_associated_object(data)
        if not isinstance(component, ue.HierarchicalInstancedStaticMeshComponent):
            raise RuntimeError('Subobject is a %s, not a HISM' % type(component).__name__)
        if component.get_owner() != actor or not library.is_instanced_component(data):
            raise RuntimeError('HISM ownership/instance creation not verified')
        if component not in actor.get_components_by_class(
                ue.HierarchicalInstancedStaticMeshComponent):
            raise RuntimeError('HISM absent from the actor component readback')
        return component

    def add_instances(self, component, transforms):
        """add_instances(transforms, should_return_indices, world_space, update_navigation).

        The actor is spawned at the origin with an identity transform so local and world agree,
        but world_space is passed explicitly where the signature allows it and the result is
        verified against the plan either way.
        """
        try:
            component.add_instances(transforms, False, True, False)
            self.receipt.setdefault('instanceApi', 'add_instances(world_space=True)')
            return
        except TypeError:
            component.add_instances(transforms, False)
            self.receipt.setdefault('instanceApi', 'add_instances(local, actor at identity)')

    def build_group(self, job, mesh):
        ue = self.ue
        spec = self.spec
        actor = self.actors.spawn_actor_from_class(ue.Actor, ue.Vector(0.0, 0.0, 0.0),
                                                   ue.Rotator(pitch=0.0, yaw=0.0, roll=0.0))
        if actor is None:
            raise RuntimeError('spawn_actor_from_class returned None for ' + job['label'])
        actor.set_actor_label(job['label'])
        actor.set_folder_path(spec['folder'] + '/' + job['zone'].capitalize())
        actor.set_editor_property('tags', [ue.Name(spec['actorTag']),
                                           ue.Name(spec['zoneTagPrefix'] + job['zone'].capitalize())])
        try:
            component = self.new_hism(actor)
        except Exception:
            self.actors.destroy_actor(actor)
            raise
        component.set_editor_property('static_mesh', mesh)
        component.set_mobility(ue.ComponentMobility.STATIC)
        component.set_collision_profile_name(spec['collision']['profile'])
        component.set_editor_property('cast_shadow', job['castShadow'])
        cull = job['cullDistanceCm']
        component.set_cull_distances(int(cull * spec['lod']['cullStartFraction']), int(cull))
        transforms = [self.make_transform(row) for row in job['rows']]
        self.add_instances(component, transforms)
        count = int(component.get_instance_count())
        if count != job['instances']:
            self.actors.destroy_actor(actor)
            raise RuntimeError('%s: added %d instances, component reports %d'
                               % (job['label'], job['instances'], count))
        sample = self.transform_sample(component, job)
        del transforms
        return actor, component, sample

    def transform_sample(self, component, job):
        """Numeric readback of a spread of instances against the plan rows."""
        ue = self.ue
        rows = job['rows']
        count = len(rows)
        picks = sorted({0, count // 3, count // 2, (2 * count) // 3, count - 1})
        tolerance = float(self.spec['verification']['instanceToleranceCm'])
        worst = 0.0
        sample = []
        for index in picks:
            transform = component.get_instance_transform(index, True)
            location = transform.get_editor_property('translation')
            scale = transform.get_editor_property('scale3d')
            rotator = transform.get_editor_property('rotation').rotator()
            row = rows[index]
            error = max(abs(location.x - row[0]), abs(location.y - row[1]), abs(location.z - row[2]))
            scale_error = max(abs(scale.x - row[6]), abs(scale.y - row[7]), abs(scale.z - row[8]))
            yaw_error = abs(((float(rotator.yaw) - row[3]) + 180.0) % 360.0 - 180.0)
            worst = max(worst, error)
            if error > tolerance or scale_error > 1e-3 or yaw_error > 0.05:
                raise RuntimeError('%s instance %d read back at %.3f,%.3f,%.3f scale %.4f yaw %.3f, '
                                   'plan says %.3f,%.3f,%.3f scale %.4f yaw %.3f'
                                   % (job['label'], index, location.x, location.y, location.z,
                                      scale.x, rotator.yaw, row[0], row[1], row[2], row[6], row[3]))
            sample.append({'index': index,
                           'locationCm': [round(location.x, 3), round(location.y, 3),
                                          round(location.z, 3)],
                           'yawDeg': round(float(rotator.yaw), 3),
                           'scale': [round(scale.x, 4), round(scale.y, 4), round(scale.z, 4)]})
        return {'checked': len(picks), 'worstLocationErrorCm': round(worst, 5), 'rows': sample}

    # ---------------------------------------------------------------- retint
    def retint(self, clear=False):
        """Per-COMPONENT material override on the building actors. Reversible; off by default."""
        ue = self.ue
        cfg = self.manifest['retint']
        prefix = cfg['appliesToActorPrefix']
        instance = None
        if not clear:
            path = self.spec['materialFolder'] + '/' + cfg['name']
            saved = self.manifest['materials']
            self.manifest['materials'] = dict(saved)
            self.manifest['materials']['__retint__'] = {
                'name': cfg['name'], 'why': cfg['why'],
                'vector': cfg['vector'], 'scalar': cfg['scalar']}
            instance = self.material('__retint__')
            self.manifest['materials'] = saved
            expected = path
        touched, already, cleared = 0, 0, 0
        for actor in self.actors.get_all_level_actors():
            if not actor.get_actor_label().startswith(prefix):
                continue
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                if clear:
                    if component.get_editor_property('override_materials'):
                        component.set_editor_property('override_materials', [])
                        cleared += 1
                    continue
                current = component.get_editor_property('override_materials')
                if current and _asset_path(current[0]) == expected:
                    already += 1
                    continue
                component.set_material(0, instance)
                got = component.get_material(0)
                if _asset_path(got) != expected:
                    raise RuntimeError('Retint override did not take on ' + actor.get_actor_label())
                touched += 1
        self.receipt['retint'] = {
            'mode': 'clear' if clear else 'apply',
            'actorPrefix': prefix,
            'material': None if clear else expected,
            'componentsOverridden': touched,
            'componentsAlreadyCorrect': already,
            'componentsCleared': cleared,
            'why': cfg['why'],
            'note': ('Per-component override only. M_Context_Building, the 1,499 building mesh '
                     'assets, M_PBR_Tiled, the nine Nanite-repaired MI_PBR_* instances and every '
                     'AntiRepeatV1 asset are untouched. -CityDetailRetintClear reverses it.'),
        }
        return self.receipt['retint']


def release(target='candidate', load_target=True, keys=None, resume=False,
            import_only=False, max_groups=None, do_retint=False, clear_retint=False,
            rebuild=False):
    """Guarded import/instancing slice. Returns the receipt dict; raises on guard failure."""
    import unreal as ue

    spec = load_spec()
    manifest, manifest_sha = load_manifest(spec)
    plan, plan_sha = load_plan(spec)
    offline = offline_check(spec, target)
    jobs = group_jobs(spec, manifest, plan)
    if keys:
        jobs = [job for job in jobs if job['meshKey'] in keys]

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    run = Run(ue, spec, manifest, plan, target)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target:
        if not run.levels.load_level(run.target):
            raise RuntimeError('load_level failed for ' + run.target)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name()
    if loaded != run.target:
        raise RuntimeError('Loaded world %s is not the target %s' % (loaded, run.target))
    if (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Dirty packages present; resolve before a checkpointed import')

    map_file = disk_path(run.target, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {name: sha256_of(disk_path(name, 'umap'))
                 for name in spec['protectedMaps']
                 if name != run.target and disk_path(name, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + target + '-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    external_copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / run.target[len('/Game/'):]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / run.target[len('/Game/'):])
            external_copied.append(str(external))

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    run.receipt_path = receipt_folder / (spec['receiptPrefix'] + target + '-' + stamp + '.json')
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))

    existing_assets = run.existing_assets()
    placed = run.our_actors()
    pending, already, clashes = [], [], []
    for job in jobs:
        actor = placed.get(job['label'])
        if actor is None:
            pending.append(job)
            continue
        components = actor.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent)
        count = int(components[0].get_instance_count()) if len(components) == 1 else -1
        if rebuild:
            pending.append(job)
        elif count == job['instances']:
            already.append(job['label'])
        elif resume:
            pending.append(job)
        else:
            clashes.append({'label': job['label'], 'have': count, 'want': job['instances']})
    if max_groups is not None:
        pending = pending[:max_groups]

    run.receipt = {
        'status': 'checkpointed_city_detail_started',
        'stamp': stamp,
        'target': target,
        'map': run.target,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'scriptSha256': sha256_of(Path(__file__)),
        'manifestSha256': manifest_sha,
        'planSha256': plan_sha,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'offlineCheck': offline,
        'mode': {'keys': sorted(keys) if keys else None, 'resume': bool(resume),
                 'importOnly': bool(import_only), 'maxGroups': max_groups,
                 'rebuild': bool(rebuild),
                 'retint': bool(do_retint), 'clearRetint': bool(clear_retint)},
        'groupsSelected': len(jobs),
        'alreadyCompleteBefore': already,
        'plannedThisRun': [job['label'] for job in pending],
        'plannedInstancesThisRun': sum(job['instances'] for job in pending),
        'materials': {},
        'meshes': [],
        'groups': [],
        'errors': [],
        'mapSaved': False,
        'limitations': list(spec['limitations']),
    }
    run.write_receipt()

    if clashes:
        run.receipt['status'] = 'refused_existing_group_instance_count_mismatch'
        run.receipt['errors'].append({
            'stage': 'guard',
            'error': 'Actors exist with an instance count that is not the planned count and no '
                     '-CityDetailResume was given.',
            'clashes': clashes})
        run.write_receipt()
        raise RuntimeError('Existing CityDetailV1 groups disagree with the plan: %s' % clashes[:4])

    saved = False
    run.receipt['actorCountBefore'] = len(run.actors.get_all_level_actors())
    spawned = []
    try:
        # ---- meshes: imported once, shared by both zones
        needed = sorted({job['assetName'] for job in pending} if pending
                        else {mesh['assetName'] for mesh in mesh_jobs(spec, manifest)})
        loaded_meshes = {}
        for mesh_job in mesh_jobs(spec, manifest):
            if mesh_job['assetName'] not in needed:
                continue
            record = {'asset': mesh_job['assetPath']}
            try:
                if mesh_job['assetName'] in existing_assets and not rebuild:
                    mesh = ue.load_asset(mesh_job['assetPath'])
                    if not isinstance(mesh, ue.StaticMesh):
                        raise RuntimeError('Existing asset is not a StaticMesh: ' + mesh_job['assetPath'])
                    record['imported'] = False
                else:
                    replace = rebuild and mesh_job['assetName'] in existing_assets
                    mesh = run.import_mesh(mesh_job, replace=replace)
                    record['imported'] = True
                    record['replacedExisting'] = bool(replace)
                record.update(run.verify_and_assign(mesh, mesh_job))
                if record['imported']:
                    if not run.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                        raise RuntimeError('save_loaded_asset failed for ' + mesh_job['assetName'])
                    record['uassetSha256'] = sha256_of(disk_path(mesh_job['assetPath']))
                loaded_meshes[mesh_job['assetName']] = mesh
                record['status'] = 'ok'
            except Exception as error:                                # noqa: BLE001
                record['status'] = 'failed'
                record['error'] = repr(error)
                run.receipt['errors'].append({'stage': 'mesh', 'asset': mesh_job['assetName'],
                                              'error': repr(error)})
            run.receipt['meshes'].append(record)
        run.write_receipt()

        if import_only:
            run.receipt['status'] = ('city_detail_meshes_imported_no_placement'
                                     if not run.receipt['errors'] else 'city_detail_import_failed')
            if run.receipt['errors']:
                raise RuntimeError('Mesh import reported errors; see receipt')
            return run.receipt

        # ---- groups: one actor + one HISM each
        for index, job in enumerate(pending):
            record = {'label': job['label'], 'zone': job['zone'], 'meshKey': job['meshKey'],
                      'mesh': job['assetPath'], 'plannedInstances': job['instances'],
                      'cullDistanceCm': job['cullDistanceCm'], 'castShadow': job['castShadow'],
                      'batchIds': job['batchIds']}
            try:
                mesh = loaded_meshes.get(job['assetName']) or ue.load_asset(job['assetPath'])
                if not isinstance(mesh, ue.StaticMesh):
                    raise RuntimeError('Mesh not available: ' + job['assetPath'])
                stale = placed.get(job['label'])
                if stale is not None:
                    run.actors.destroy_actor(stale)
                    record['rebuiltFromPartial'] = True
                actor, component, sample = run.build_group(job, mesh)
                spawned.append((job, actor))
                record['instances'] = int(component.get_instance_count())
                record['transformSample'] = sample
                record['status'] = 'ok'
            except Exception as error:                                # noqa: BLE001
                record['status'] = 'failed'
                record['error'] = repr(error)
                run.receipt['errors'].append({'stage': 'group', 'label': job['label'],
                                              'error': repr(error)})
            run.receipt['groups'].append(record)
            run.write_receipt()
            gc.collect()
            ue.SystemLibrary.collect_garbage()

        run.receipt['groupsOk'] = sum(1 for r in run.receipt['groups'] if r['status'] == 'ok')
        run.receipt['groupsFailed'] = sum(1 for r in run.receipt['groups'] if r['status'] != 'ok')

        if do_retint or clear_retint:
            run.retint(clear=clear_retint)
        run.write_receipt()

        if run.receipt['groupsOk'] == 0 and not (do_retint or clear_retint):
            run.receipt['status'] = 'nothing_to_do_map_unchanged'
            return run.receipt

        if not ue.EditorLoadingAndSavingUtils.save_map(run.world, run.target):
            raise RuntimeError('save_map failed')
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()

        # ---- reopen and read back. Actor handles do not survive the reload.
        expected = [{'label': job['label'], 'mesh': job['assetPath'],
                     'instances': job['instances'], 'zone': job['zone'],
                     'rows': job['rows']} for job, _ in spawned]
        if not run.levels.load_level(run.target):
            raise RuntimeError('Reopening the map failed')
        run.world = run.editor.get_editor_world()
        reopened = run.our_actors()
        readback = []
        for item in expected:
            actor = reopened.get(item['label'])
            if actor is None:
                raise RuntimeError('Placed actor missing after reopen: ' + item['label'])
            components = actor.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent)
            if len(components) != 1:
                raise RuntimeError('%s has %d instanced components after reopen, expected 1'
                                   % (item['label'], len(components)))
            component = components[0]
            count = int(component.get_instance_count())
            if count != item['instances']:
                raise RuntimeError('%s: %d instances written, %d read back after reopen'
                                   % (item['label'], item['instances'], count))
            mesh_path = _asset_path(component.get_editor_property('static_mesh'))
            if mesh_path != item['mesh']:
                raise RuntimeError('Reopened mesh %s is not %s for %s'
                                   % (mesh_path, item['mesh'], item['label']))
            probe = component.get_instance_transform(count - 1, True)
            location = probe.get_editor_property('translation')
            row = item['rows'][-1]
            error = max(abs(location.x - row[0]), abs(location.y - row[1]), abs(location.z - row[2]))
            if error > float(spec['verification']['instanceToleranceCm']):
                raise RuntimeError('%s: last instance moved by %.4f cm across the reopen'
                                   % (item['label'], error))
            origin, extent = actor.get_actor_bounds(False)
            readback.append({'label': item['label'], 'zone': item['zone'], 'mesh': mesh_path,
                             'instances': count,
                             'lastInstanceErrorCm': round(error, 5),
                             'worldBoundsCentreCm': _xyz(origin),
                             'worldBoundsExtentCm': _xyz(extent),
                             'castShadow': bool(component.get_editor_property('cast_shadow'))})
        run.receipt['reopenedReadback'] = readback
        run.receipt['reopenedInstanceTotal'] = sum(row['instances'] for row in readback)
        run.receipt['actorCountAfter'] = len(run.actors.get_all_level_actors())

        after = run.our_actors()
        done = set()
        for label, actor in after.items():
            components = actor.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent)
            if len(components) == 1:
                done.add((label, int(components[0].get_instance_count())))
        remaining = [job['label'] for job in group_jobs(spec, manifest, plan)
                     if (job['label'], job['instances']) not in done]
        run.receipt['remainingGroups'] = remaining
        run.receipt['remainingGroupCount'] = len(remaining)
        run.receipt['resumeCommand'] = (
            'Re-run with -CityDetailResume until remainingGroupCount is 0' if remaining else None)
        run.receipt['status'] = ('city_detail_instanced_saved_reopened_visual_acceptance_pending'
                                 if not remaining else
                                 'city_detail_partial_slice_saved_reopened_resume_pending')
        return run.receipt
    except Exception as error:                                        # noqa: BLE001
        run.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        run.receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                                 else 'failed_before_save_map_unchanged')
        raise
    finally:
        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapBytesChanged'] = run.receipt['mapSha256After'] != map_sha_before
        run.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(name, 'umap')) == value for name, value in protected.items())
        run.write_receipt()


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return SCRIPT_TOKEN in command_line and ('-run=pythonscript' in command_line
                                             or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    lowered = command_line.lower()
    spec = load_spec()
    manifest, _ = load_manifest(spec)
    available = {mesh['key'] for mesh in manifest['meshes']}
    target = 'candidate'
    keys = None
    max_groups = None
    resume = '-citydetailresume' in lowered
    rebuild = '-citydetailrebuild' in lowered
    import_only = '-citydetailimportonly' in lowered
    do_retint = '-citydetailretint' in lowered and '-citydetailretintclear' not in lowered
    clear_retint = '-citydetailretintclear' in lowered
    for token in command_line.split():
        low = token.lower()
        if low.startswith('-citydetailtarget='):
            target = token.split('=', 1)[1].strip('"').lower()
        elif low.startswith('-citydetailgroups='):
            keys = parse_keys(token.split('=', 1)[1], available)
        elif low.startswith('-citydetailmaxgroups='):
            max_groups = int(token.split('=', 1)[1].strip('"'))
    try:
        receipt = release(target=target, load_target=True, keys=keys, resume=resume,
                          import_only=import_only, max_groups=max_groups,
                          do_retint=do_retint, clear_retint=clear_retint, rebuild=rebuild)
        ue.log('release_city_detail: %s groups ok %s failed %s remaining %s instances %s'
               % (receipt['status'], receipt.get('groupsOk'), receipt.get('groupsFailed'),
                  receipt.get('remainingGroupCount'), receipt.get('reopenedInstanceTotal')))
    except Exception as error:                                        # noqa: BLE001
        ue.log_error('release_city_detail failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in lowered and '-run=pythonscript' not in lowered:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

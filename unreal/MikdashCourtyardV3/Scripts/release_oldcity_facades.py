"""Guarded, resumable native import and placement of OldCityFacadesV1.

Imports the 100 m batched OBJs written by Scripts/create_oldcity_facades.py into
/Game/MikdashV3/JerusalemContext/OldCityFacadesV1 with Nanite ON, assigns the existing
context building material to the detail shells and a lighter plaster MaterialInstanceConstant
to the AUTHORED_INFILL massing, places one StaticMeshActor per batch at identity, then saves,
reopens and reads back every actor numerically.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_oldcity_facades.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/OldCityFacades-01.log"
      -FacadesGroups=0,1

Switches (read from the engine command line):
  -FacadesGroups=0,1,2   only these manifest groups. Groups are balanced by triangle count.
  -FacadesResume         every group, skipping cells that are already imported AND placed.
                         Safe to repeat until the receipt reports remainingCells 0.
  -FacadesPlaceOnly      do not import; only place actors for meshes that already exist.
                         This is the path for a namespace that is already populated, because
                         re-running a creator into an existing native namespace is prohibited.
  -FacadesMaxCells=N     stop after N cells this run (a memory valve on a 16 GB machine).

WHY IT IS RESUMABLE
-------------------
About 3.4 M triangles across 190 meshes is more than one editor lifetime wants to import,
build Nanite for and save on a 16 GB machine. Each run checkpoints the map, does its slice,
saves, reopens, reads back and writes its own receipt. State is derived from the world and
the content browser (which meshes exist, which actors are placed), never from a side file,
so an interrupted run resumes correctly.

SAFETY MODEL (release_place_assets.py pattern)
----------------------------------------------
  * Refuses on the wrong project directory, an active game world, dirty packages, or a loaded
    world that is not the combined map.
  * Verifies the generator manifest hash, its status, and the SHA-256 of every OBJ it is
    about to import, before touching anything.
  * Copies Walkthrough.umap (and any One-File-Per-Actor folders) to
    ReviewCheckpoints/OldCityFacades-<stamp>/ and verifies the copy before any mutation.
  * Writes only inside /Game/MikdashV3/JerusalemContext/OldCityFacadesV1. An existing asset
    for a requested cell is a refusal unless -FacadesResume or -FacadesPlaceOnly.
  * Saves only if at least one cell completed, reloads the map, and reads back every placed
    actor's mesh path, transform, world bounds and collision profile.
  * The receipt JSON is written at start and again in finally, so a failure preserves state.

UE 5.8 PYTHON PITFALLS HANDLED HERE (AGENTS.md)
------------------------------------------------
  * MaterialEditingLibrary setters return False even on success: every material-instance
    parameter is verified by readback.
  * MaterialEditingLibrary has no set_material_default_*; the plaster variant is a
    MaterialInstanceConstant, not an edited Material.
  * StaticMesh.get_num_uv_channels does not exist and is not called.
  * StaticMeshEditorSubsystem is None under -run=pythonscript, so nothing here depends on it.
  * spawn_actor_from_object returns None in commandlets: actors are spawned from the
    StaticMeshActor class and the mesh is set with a checked set_static_mesh.
  * unreal.Rotator needs explicit pitch/yaw/roll keywords.
  * Numeric transform fields are compared, never str(Transform).
"""

import gc
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_oldcity_facades.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
SCRIPT_TOKEN = 'release_oldcity_facades.py'


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
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def load_manifest(spec):
    path = ROOT / spec['source']['manifest']
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    actual = sha256_of(path)
    if actual != spec['source']['manifestSha256']:
        raise RuntimeError('facades-manifest.json SHA256 %s is not the reviewed revision %s'
                           % (actual, spec['source']['manifestSha256']))
    if manifest['status'] != spec['source']['manifestStatusRequired']:
        raise RuntimeError('Manifest status %s is not %s'
                           % (manifest['status'], spec['source']['manifestStatusRequired']))
    return manifest, actual


def cell_jobs(spec, manifest):
    """Flat, ordered list of the import/placement units: one per OBJ."""
    group_of = {}
    for group in manifest['groups']:
        for name in group['cells']:
            group_of[name] = group['group']
    jobs = []
    for batch in manifest['batches']:
        for role in ('facades', 'infill'):
            entry = batch.get(role)
            if not entry:
                continue
            asset = ('SM_OldCityFacades_' if role == 'facades' else 'SM_OldCityInfill_') + batch['name']
            jobs.append({
                'cell': batch['name'],
                'role': role,
                'group': group_of.get(batch['name']),
                'assetName': asset,
                'assetPath': spec['meshFolder'] + '/' + asset,
                'objFile': entry['file'],
                'sha256': entry['sha256'],
                'triangles': entry['triangles'],
                'vertices': entry['vertices'],
                'canonicalBoundsCm': entry['canonicalBoundsCm'],
                'buildings': entry.get('buildings', 0),
                'label': spec['labelPrefix'] + ('OldCityFacades_' if role == 'facades'
                                                else 'OldCityInfill_') + batch['name'],
            })
    if any(job['group'] is None for job in jobs):
        raise RuntimeError('Manifest groups do not cover every batch')
    jobs.sort(key=lambda job: (job['group'], job['cell'], job['role']))
    return jobs


def parse_groups(text, available):
    wanted = set()
    for token in str(text).replace('"', '').split(','):
        token = token.strip()
        if not token:
            continue
        if not token.lstrip('-').isdigit():
            raise ValueError('Group ids must be integers: ' + token)
        wanted.add(int(token))
    unknown = sorted(wanted - available)
    if unknown:
        raise ValueError('Unknown manifest group ids: %s (have %s)' % (unknown, sorted(available)))
    return sorted(wanted)


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def offline_check(spec=None):
    """Everything verifiable without the engine. Runs before any mutation."""
    spec = spec or load_spec()
    manifest, manifest_sha = load_manifest(spec)
    script_sha = sha256_of(ROOT / spec['source']['authoringScript'])
    obj_dir = ROOT / spec['source']['objFolder']
    missing, mismatched, bytes_total, triangles = [], [], 0, 0
    jobs = cell_jobs(spec, manifest)
    for job in jobs:
        path = obj_dir / job['objFile']
        if not path.exists():
            missing.append(job['objFile'])
            continue
        if sha256_of(path) != job['sha256']:
            mismatched.append(job['objFile'])
        bytes_total += path.stat().st_size
        triangles += job['triangles']
    if missing:
        raise RuntimeError('Missing generated OBJs: %s' % missing[:8])
    if mismatched:
        raise RuntimeError('OBJ contents changed since the manifest was written: %s' % mismatched[:8])
    if triangles != manifest['totals']['triangles']:
        raise RuntimeError('OBJ triangle sum %d differs from the manifest total %d'
                           % (triangles, manifest['totals']['triangles']))
    if len(jobs) != manifest['totals']['objFiles']:
        raise RuntimeError('Job count %d differs from the manifest objFiles %d'
                           % (len(jobs), manifest['totals']['objFiles']))
    return {
        'status': 'offline_spec_and_source_consistent',
        'specSha256': sha256_of(SPEC_PATH),
        'manifestSha256': manifest_sha,
        'authoringScriptSha256': script_sha,
        'authoringScriptMatchesSpec': script_sha == spec['source']['authoringScriptSha256'],
        'jobs': len(jobs),
        'facadeJobs': sum(1 for job in jobs if job['role'] == 'facades'),
        'infillJobs': sum(1 for job in jobs if job['role'] == 'infill'),
        'triangles': triangles,
        'objBytes': bytes_total,
        'groups': {str(group['group']): {'cells': len(group['cells']), 'triangles': group['triangles']}
                   for group in manifest['groups']},
        'targetMapSha256': sha256_of(disk_path(TARGET, 'umap')) if disk_path(TARGET, 'umap').exists() else None,
        'targetMapMatchesLastKnown': (disk_path(TARGET, 'umap').exists()
                                      and sha256_of(disk_path(TARGET, 'umap')) == spec['lastKnownMapSha256']),
        'namespaceOnDisk': (ROOT / 'Content' / spec['namespace'][len('/Game/'):]).exists(),
        'coverageBefore': manifest['infill']['coverageBefore'],
        'coverageAfter': manifest['infill']['coverageAfter'],
        'infillBuildings': manifest['infill']['buildings'],
        'buildingsInScope': manifest['oldCity']['buildingsInScope'],
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


def _actor_bounds(actor):
    origin, extent = actor.get_actor_bounds(only_colliding_components=False)
    return {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
            'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}


class Run:
    def __init__(self, ue, spec, manifest):
        self.ue = ue
        self.spec = spec
        self.manifest = manifest
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.receipt = {}
        self.receipt_path = None
        self.world = None

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2) + '\n', encoding='utf-8')

    # ---------------------------------------------------------------- state
    def existing_assets(self):
        folder = self.spec['meshFolder']
        if not self.assets.does_directory_exist(folder):
            return set()
        return {str(path).split('/')[-1].split('.')[0]
                for path in self.assets.list_assets(folder, recursive=True, include_folder=False)}

    def placed_actors(self):
        """label -> actor, for our own release actors only. Cached once (7000+ actors)."""
        prefix = self.spec['labelPrefix'] + 'OldCity'
        found = {}
        for actor in self.actors.get_all_level_actors():
            label = actor.get_actor_label()
            if label.startswith(prefix):
                found[label] = actor
        return found

    # ------------------------------------------------------------ materials
    def facade_material(self):
        tried = []
        for position, candidate in enumerate(self.spec['materials']['facades']['candidates']):
            exists = self.assets.does_asset_exist(candidate['path'])
            material = self.ue.load_asset(candidate['path']) if exists else None
            ok = isinstance(material, self.ue.MaterialInterface)
            tried.append({'path': candidate['path'], 'kind': candidate['kind'],
                          'exists': bool(exists), 'loaded': ok})
            if ok:
                if position > 0:
                    self.receipt['limitations'].append(
                        'Facade material fell back to %s; the preferred context building material '
                        'did not load' % candidate['path'])
                self.receipt['materials']['facades'] = {'assigned': candidate['path'], 'tried': tried}
                return material
        raise RuntimeError('No facade material candidate loads: %s' % tried)

    def infill_material(self, parent):
        """Lighter plaster variant as a MaterialInstanceConstant; created only if missing."""
        ue = self.ue
        cfg = self.spec['materials']['infill']['createIfMissing']
        path = cfg['path']
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
        parent_path = _asset_path(instance.get_editor_property('parent'))
        if parent_path != cfg['parent']:
            instance.set_editor_property('parent', ue.load_asset(cfg['parent']))
            parent_path = _asset_path(instance.get_editor_property('parent'))
        if parent_path != cfg['parent']:
            raise RuntimeError('Plaster instance parent is %s, expected %s' % (parent_path, cfg['parent']))
        edit = ue.MaterialEditingLibrary
        readback = {'vector': {}, 'scalar': {}}
        # UE 5.8: these setters return False even on success, so verify by readback only.
        for name, rgb in cfg['vectorParameters'].items():
            edit.set_material_instance_vector_parameter_value(
                instance, name, ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
        for name, value in cfg['scalarParameters'].items():
            edit.set_material_instance_scalar_parameter_value(instance, name, float(value))
        edit.update_material_instance(instance)
        wrong = []
        for name, rgb in cfg['vectorParameters'].items():
            value = edit.get_material_instance_vector_parameter_value(instance, name)
            got = [round(float(value.r), 4), round(float(value.g), 4), round(float(value.b), 4)]
            readback['vector'][name] = got
            if max(abs(got[i] - float(rgb[i])) for i in range(3)) > 1e-3:
                wrong.append(name)
        for name, value in cfg['scalarParameters'].items():
            got = round(float(edit.get_material_instance_scalar_parameter_value(instance, name)), 5)
            readback['scalar'][name] = got
            if abs(got - float(value)) > 1e-4:
                wrong.append(name)
        if wrong:
            raise RuntimeError('Plaster instance parameters did not take: %s' % sorted(set(wrong)))
        if not self.assets.save_loaded_asset(instance, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        self.receipt['materials']['infill'] = {
            'assigned': path, 'created': created, 'parent': parent_path, 'readback': readback,
            'note': 'Setters are not trusted; every value above was read back from the instance.'}
        return instance

    # --------------------------------------------------------------- import
    def import_mesh(self, job):
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
                               replace_existing=False, save=False, options=options,
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

    def enable_nanite(self, mesh):
        ue = self.ue
        state = {'requestedAtImport': True}
        try:
            settings = mesh.get_editor_property('nanite_settings')
            state['enabledAfterImport'] = bool(settings.get_editor_property('enabled'))
            if not state['enabledAfterImport']:
                settings.set_editor_property('enabled', True)
                mesh.set_editor_property('nanite_settings', settings)
                mesh.post_edit_change()
                state['enabledAfterSet'] = bool(
                    mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
            else:
                state['enabledAfterSet'] = True
        except Exception as error:
            state['error'] = repr(error)
            state['enabledAfterSet'] = None
        return state

    def verify_and_assign(self, mesh, job, material):
        spec = self.spec
        box = _static_mesh_box(mesh)
        error = box_error(box, job['canonicalBoundsCm'])
        triangles = int(mesh.get_num_triangles(0))
        if error > spec['source']['boundsToleranceCm']:
            raise RuntimeError('%s bounds differ from canonical by %.4f cm (Y reflection did not '
                               'round-trip?): %r' % (job['assetName'], error, box))
        if spec['verification']['requireTriangleMatch'] and triangles != job['triangles']:
            raise RuntimeError('%s has %d triangles, manifest says %d'
                               % (job['assetName'], triangles, job['triangles']))
        slots = len(mesh.get_editor_property('static_materials'))
        if slots < 1:
            raise RuntimeError('%s has no material slots' % job['assetName'])
        for slot in range(slots):
            mesh.set_material(slot, material)
        expected = _asset_path(material)
        wrong = [slot for slot in range(slots) if _asset_path(mesh.get_material(slot)) != expected]
        if wrong:
            raise RuntimeError('Material slots not assigned on %s: %s' % (job['assetName'], wrong[:10]))
        info = {'asset': _asset_path(mesh), 'triangles': triangles,
                'renderVertices': int(mesh.get_num_vertices(0)), 'materialSlots': slots,
                'material': expected, 'boundsErrorCm': error, 'localBoundsCm': box}
        if job['role'] == 'infill':
            info['collisionTraceFlag'] = self.set_complex_as_simple(mesh)
        return info

    def set_complex_as_simple(self, mesh):
        ue = self.ue
        try:
            body = mesh.get_editor_property('body_setup')
            if body is None:
                return 'body_setup is None; collision left at the mesh default'
            body.set_editor_property('collision_trace_flag',
                                     ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            return str(body.get_editor_property('collision_trace_flag'))
        except Exception as error:
            return 'unset: %r' % (error,)

    # -------------------------------------------------------------- placement
    def spawn(self, job, mesh):
        ue = self.ue
        placement = self.spec['placement']
        location = ue.Vector(*[float(v) for v in placement['location']])
        rotation = ue.Rotator(pitch=float(placement['rotation'][0]),
                              yaw=float(placement['rotation'][1]),
                              roll=float(placement['rotation'][2]))
        actor = self.actors.spawn_actor_from_class(ue.StaticMeshActor, location, rotation)
        if actor is None:
            raise RuntimeError('spawn_actor_from_class returned None for ' + job['label'])
        component = actor.get_component_by_class(ue.StaticMeshComponent)
        if not component.set_static_mesh(mesh):
            self.actors.destroy_actor(actor)
            raise RuntimeError('set_static_mesh failed for ' + job['label'])
        actor.set_actor_label(job['label'])
        actor.set_folder_path(self.spec['folder'])
        actor.set_actor_scale3d(ue.Vector(*[float(v) for v in placement['scale']]))
        profile = self.spec['collision']['facades' if job['role'] == 'facades' else 'infill']['profile']
        component.set_collision_profile_name(profile)
        tags = [self.spec['actorTag']]
        if job['role'] == 'infill':
            tags.append(self.spec['infillActorTag'])
        actor.set_editor_property('tags', [ue.Name(tag) for tag in tags])
        # Mobility lives on the component, not the actor (the recover_instances_mobility lesson).
        try:
            component.set_editor_property('mobility', ue.ComponentMobility.STATIC)
        except Exception as error:
            self.receipt['limitations'].append(
                'Could not set STATIC mobility on %s: %r' % (job['label'], error))
        return actor, {'label': job['label'], 'name': actor.get_name(),
                       'mesh': _asset_path(mesh), 'collisionProfile': str(component.get_collision_profile_name()),
                       'tags': tags, 'plannedWorldBoundsCm': job['canonicalBoundsCm']}


def release(load_target=True, groups=None, resume=False, place_only=False, max_cells=None):
    """Guarded import/placement slice. Returns the receipt dict; raises on guard failure."""
    import unreal as ue

    spec = load_spec()
    manifest, manifest_sha = load_manifest(spec)
    offline = offline_check(spec)
    jobs = cell_jobs(spec, manifest)
    available = {group['group'] for group in manifest['groups']}
    selected = sorted(available) if groups is None else groups
    jobs = [job for job in jobs if job['group'] in selected]

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    run = Run(ue, spec, manifest)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target:
        if not run.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before a checkpointed import')

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {name: sha256_of(disk_path(name, 'umap'))
                 for name in spec['protectedMaps'] if disk_path(name, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    external_copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / TARGET[len('/Game/'):]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / TARGET[len('/Game/'):])
            external_copied.append(str(external))

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    run.receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))

    existing_assets = run.existing_assets()
    placed = run.placed_actors()
    pending = []
    already = []
    clashes = []
    for job in jobs:
        has_asset = job['assetName'] in existing_assets
        has_actor = job['label'] in placed
        if has_asset and has_actor:
            already.append(job['assetName'])
            continue
        if has_asset and not (resume or place_only):
            clashes.append(job['assetName'])
            continue
        if place_only and not has_asset:
            continue
        pending.append(job)
    if max_cells is not None:
        pending = pending[:max_cells]

    run.receipt = {
        'status': 'checkpointed_import_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == spec['lastKnownMapSha256'],
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'scriptSha256': sha256_of(Path(__file__)),
        'manifestSha256': manifest_sha,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'offlineCheck': offline,
        'mode': {'groupsRequested': selected, 'resume': bool(resume),
                 'placeOnly': bool(place_only), 'maxCells': max_cells},
        'jobsInSelectedGroups': len(jobs),
        'alreadyCompleteBefore': already,
        'alreadyCompleteCountBefore': len(already),
        'plannedThisRun': [job['assetName'] for job in pending],
        'plannedCountThisRun': len(pending),
        'materials': {},
        'cells': [],
        'errors': [],
        'mapSaved': False,
        'limitations': list(spec['limitations']),
    }
    run.write_receipt()

    if clashes and not (resume or place_only):
        run.receipt['status'] = 'refused_existing_namespace_no_overwrite'
        run.receipt['errors'].append({
            'stage': 'guard',
            'error': 'Assets already exist for requested cells and no -FacadesResume / '
                     '-FacadesPlaceOnly was given; re-running a creator into an existing native '
                     'namespace is prohibited.',
            'assets': clashes[:20], 'assetCount': len(clashes)})
        run.write_receipt()
        raise RuntimeError('Existing OldCityFacadesV1 assets for requested cells: %s' % clashes[:8])

    saved = False
    actor_count_before = len(run.actors.get_all_level_actors())
    run.receipt['actorCountBefore'] = actor_count_before
    spawned = []
    try:
        facade_material = run.facade_material()
        infill_material = run.infill_material(facade_material)
        run.write_receipt()

        for index, job in enumerate(pending):
            record = {'cell': job['cell'], 'role': job['role'], 'group': job['group'],
                      'asset': job['assetPath'], 'label': job['label'],
                      'buildings': job['buildings']}
            try:
                if job['assetName'] in existing_assets or place_only:
                    mesh = ue.load_asset(job['assetPath'])
                    if not isinstance(mesh, ue.StaticMesh):
                        raise RuntimeError('Existing asset is not a StaticMesh: ' + job['assetPath'])
                    record['imported'] = False
                else:
                    mesh = run.import_mesh(job)
                    record['imported'] = True
                    record['nanite'] = run.enable_nanite(mesh)
                material = facade_material if job['role'] == 'facades' else infill_material
                record.update(run.verify_and_assign(mesh, job, material))
                if record.get('imported'):
                    if not run.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                        raise RuntimeError('save_loaded_asset failed for ' + job['assetName'])
                    record['uassetSha256'] = sha256_of(disk_path(job['assetPath']))
                if job['label'] in placed:
                    record['placed'] = False
                    record['placementNote'] = 'Actor already present from an earlier run'
                else:
                    actor, placement = run.spawn(job, mesh)
                    spawned.append((job, actor))
                    record['placed'] = True
                    record.update(placement)
                record['status'] = 'ok'
            except Exception as error:
                record['status'] = 'failed'
                record['error'] = repr(error)
                run.receipt['errors'].append({'stage': 'cell', 'cell': job['cell'],
                                              'role': job['role'], 'error': repr(error)})
            run.receipt['cells'].append(record)
            if (index + 1) % 10 == 0:
                run.write_receipt()
                gc.collect()
                ue.SystemLibrary.collect_garbage()

        run.receipt['cellsOk'] = sum(1 for record in run.receipt['cells'] if record['status'] == 'ok')
        run.receipt['cellsFailed'] = sum(1 for record in run.receipt['cells'] if record['status'] != 'ok')
        run.write_receipt()

        if run.receipt['cellsOk'] == 0:
            run.receipt['status'] = 'nothing_to_do_map_unchanged'
            return run.receipt

        if not ue.EditorLoadingAndSavingUtils.save_map(run.world, TARGET):
            raise RuntimeError('save_map failed')
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()

        # Reopen and read back. Cache labels first: actor handles do not survive the reload.
        expected = [{'label': job['label'], 'mesh': job['assetPath'],
                     'role': job['role'], 'bounds': job['canonicalBoundsCm'],
                     'profile': spec['collision']['facades' if job['role'] == 'facades' else 'infill']['profile']}
                    for job, _ in spawned]
        if not run.levels.load_level(TARGET):
            raise RuntimeError('Reopening the map failed')
        run.world = run.editor.get_editor_world()
        reopened = run.placed_actors()
        readback = []
        verify = spec['verification']
        for item in expected:
            actor = reopened.get(item['label'])
            if actor is None:
                raise RuntimeError('Placed actor missing after reopen: ' + item['label'])
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            mesh_path = _asset_path(component.get_editor_property('static_mesh'))
            if mesh_path != item['mesh']:
                raise RuntimeError('Reopened mesh differs for ' + item['label'])
            location = actor.get_actor_location()
            rotation = actor.get_actor_rotation()
            scale = actor.get_actor_scale3d()
            pose_error = max([abs(location.x), abs(location.y), abs(location.z),
                              abs(rotation.pitch), abs(rotation.yaw), abs(rotation.roll),
                              abs(scale.x - 1.0), abs(scale.y - 1.0), abs(scale.z - 1.0)])
            if pose_error > verify['transformToleranceCm']:
                raise RuntimeError('Reopened transform is not identity for %s (%.6f)'
                                   % (item['label'], pose_error))
            bounds_error = box_error(_actor_bounds(actor), item['bounds'])
            if bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened bounds differ for %s by %.4f cm'
                                   % (item['label'], bounds_error))
            profile = str(component.get_collision_profile_name())
            if profile != item['profile']:
                raise RuntimeError('Reopened collision profile %s is not %s for %s'
                                   % (profile, item['profile'], item['label']))
            readback.append({'label': item['label'], 'mesh': mesh_path, 'role': item['role'],
                             'poseErrorCm': pose_error, 'boundsErrorCm': bounds_error,
                             'collisionProfile': profile,
                             'triangles': int(ue.load_asset(mesh_path).get_num_triangles(0))})
        run.receipt['reopenedReadback'] = readback
        run.receipt['reopenedReadbackCount'] = len(readback)

        placed_after = run.placed_actors()
        run.receipt['totalOldCityActorsAfter'] = len(placed_after)
        run.receipt['actorCountAfter'] = len(run.actors.get_all_level_actors())
        done = {name for name in run.existing_assets()}
        remaining = [job['assetName'] for job in cell_jobs(spec, manifest)
                     if job['assetName'] not in done or job['label'] not in placed_after]
        run.receipt['remainingCells'] = remaining
        run.receipt['remainingCellCount'] = len(remaining)
        run.receipt['resumeCommand'] = (
            'Re-run with -FacadesResume until remainingCellCount is 0' if remaining else None)
        run.receipt['status'] = ('oldcity_facades_imported_saved_reopened_visual_acceptance_pending'
                                 if not remaining else
                                 'oldcity_facades_partial_slice_saved_reopened_resume_pending')
        return run.receipt
    except Exception as error:
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
    available = {group['group'] for group in manifest['groups']}
    groups = None
    resume = '-facadesresume' in lowered
    place_only = '-facadesplaceonly' in lowered
    max_cells = None
    for token in command_line.split():
        low = token.lower()
        if low.startswith('-facadesgroups='):
            groups = parse_groups(token.split('=', 1)[1], available)
        elif low.startswith('-facadesmaxcells='):
            max_cells = int(token.split('=', 1)[1].strip('"'))
    try:
        receipt = release(load_target=True, groups=groups, resume=resume,
                          place_only=place_only, max_cells=max_cells)
        ue.log('release_oldcity_facades: %s cells ok %s failed %s remaining %s'
               % (receipt['status'], receipt.get('cellsOk'), receipt.get('cellsFailed'),
                  receipt.get('remainingCellCount')))
    except Exception as error:
        ue.log_error('release_oldcity_facades failed: ' + repr(error))
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

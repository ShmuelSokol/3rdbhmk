"""The Kohen Gadol V1 body into the engine. Hidden editor, ONE engine at a time.

  UnrealEditor.exe <uproject> -ExecutePythonScript=<this> <MODE> -unattended -nullrhi -NoSplash -abslog=<log>

  -KohenGadolImport        Interchange import of SourceAssets/characters-review/KohenGadolV1/meshes/
                           SK_KohenGadol_V1.glb onto the EXISTING V3_Pilgrim_Man_Standard Skeleton (so the
                           shipped Idle / WalkV2 / TendLamp clips play on it unchanged), a new master
                           material (bUsedWithSkeletalMesh, vertex colour decoded) and one instance per slot,
                           the slots assigned by name AFTER the import (a re-import resets slots), every value
                           read back. Refuses if the folder exists, if a Skeleton or an animation is created,
                           if the bone SET changes, or if any protected asset (every resident body, clip and
                           skeleton under PilgrimRigV3, both maps) changes bytes.
  -KohenGadolImportRevert  Delete the imported folder; refuses while either map's kohen points at it.
  -KohenGadolApply  -KohenTarget=Candidate48|Main50
                           Guard pattern: checkpoint the .umap into ReviewCheckpoints/KohenGadol-*, protected
                           hashes before/after, set ONLY configured_mesh on the kohen actor, save, reopen,
                           numeric readback, scene snapshot (only the kohen actor may differ), receipt.
  -KohenGadolRevert -KohenTarget=...   restore configured_mesh from the newest saved apply receipt.
  -KohenGadolRevertAndReapply -KohenTarget=...   prove the revert, then apply again.
  -KohenGadolApplyAll      Candidate48 then Main50.
"""
import hashlib, importlib.util, json, re, shutil, sys, traceback
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/service-review'
KG_DIR = ROOT / 'SourceAssets/characters-review/KohenGadolV1'
GLB = KG_DIR / 'meshes/SK_KohenGadol_V1.glb'
MANIFEST = KG_DIR / 'kohen-gadol-v1-manifest.json'
MARKER = KG_DIR / 'kohen-gadol-import-marker.json'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
FOLDER = '/Game/MikdashV3/Characters/KohenGadolV1'
MESH_FOLDER = FOLDER + '/Mesh'
MAT_FOLDER = FOLDER + '/Materials'
MASTER = 'M_KohenGadol_Garment_V1'
VC_DECODE = 2.2      # the skeletal build stores COLOR_0 as sRGB bytes; the shader reads them raw
PROTECT_TREE = ROOT / 'Content/MikdashV3/Characters/PilgrimRigV3'


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TEND = _load('release_kohen_tend_for_kg', 'Scripts/release_kohen_tend.py')
sha, stamp_now, utc, _same = TEND.sha, TEND.stamp_now, TEND.utc, TEND._same
_object_path, disk_umap, disk_uasset, _targets, _guards = (TEND._object_path, TEND.disk_umap, TEND.disk_uasset,
                                                          TEND._targets, TEND._guards)
BODY_MESH, SKELETON = TEND.BODY_MESH, TEND.SKELETON
FIELDS = TEND.FIELDS
WRITE = ('configured_mesh',)


def receipt_path(kind, key, stamp):
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT / ('kohen-gadol-%s-%s-%s.json' % (kind, key, stamp))


def protected():
    """Every resident body, clip and skeleton under PilgrimRigV3, the two maps and the kohen clips."""
    out = TEND.protected()
    for f in sorted(PROTECT_TREE.rglob('*.uasset')):
        out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    try:
        clip = disk_uasset(_object_path(TEND.tend_clip_path()))
        out[str(clip.relative_to(ROOT)).replace('\\', '/')] = sha(clip)
    except Exception:                                                  # noqa: BLE001
        pass
    return out


def marker():
    return json.loads(MARKER.read_text(encoding='utf-8-sig'))


# ---------------------------------------------------------------------------------------- import
def _mesh_pipeline(ue, skeleton):
    pipeline = ue.InterchangeGenericAssetsPipeline()
    readback, missing = {}, []

    def apply(owner, key, value, required):
        try:
            owner.set_editor_property(key, value)
            got = owner.get_editor_property(key)
            readback[key] = got.get_path_name() if hasattr(got, 'get_path_name') else str(got)
        except Exception as error:                                   # noqa: BLE001
            readback[key] = 'unavailable: ' + str(error)[:120]
            if required:
                missing.append(key)

    common = pipeline.get_editor_property('common_skeletal_meshes_and_animations_properties')
    apply(common, 'skeleton', skeleton, True)
    apply(common, 'import_only_animations', False, True)
    apply(common, 'use_t0_as_ref_pose', False, False)
    apply(common, 'add_curve_metadata_to_skeleton', False, False)
    try:
        cm = pipeline.get_editor_property('common_meshes_properties')
        apply(cm, 'vertex_color_import_option', ue.InterchangeVertexColorImportOption.IVCIO_REPLACE, False)
    except Exception as error:                                       # noqa: BLE001
        readback['vertex_color_import_option'] = 'unavailable: ' + str(error)[:120]
    mesh = pipeline.get_editor_property('mesh_pipeline')
    apply(mesh, 'import_static_meshes', False, True)
    apply(mesh, 'import_skeletal_meshes', True, True)
    apply(mesh, 'create_physics_asset', False, False)
    apply(mesh, 'import_morph_targets', False, False)
    animation = pipeline.get_editor_property('animation_pipeline')
    apply(animation, 'import_animations', False, True)
    material = pipeline.get_editor_property('material_pipeline')
    apply(material, 'import_materials', True, False)
    if missing:
        raise RuntimeError('Interchange pipeline would not accept %r; readback %r' % (missing, readback))
    if skeleton.get_name() not in str(readback.get('skeleton', '')):
        raise RuntimeError('common.skeleton did not read back as %s (%r)' % (skeleton.get_name(),
                                                                             readback.get('skeleton')))
    override = ue.InterchangePipelineStackOverride()
    override.add_pipeline(pipeline)
    return override, readback


def _build_master(ue, tools, name):
    mel = ue.MaterialEditingLibrary
    mat = tools.create_asset(name, MAT_FOLDER, ue.Material, ue.MaterialFactoryNew())
    if mat is None:
        raise RuntimeError('could not create %s' % name)
    mat.set_editor_property('used_with_skeletal_mesh', True)

    def node(cls, x, y):
        return mel.create_material_expression(mat, cls, x, y)
    vc = node(ue.MaterialExpressionVertexColor, -1100, 0)
    mask = node(ue.MaterialExpressionComponentMask, -900, 0)
    for k, v in (('r', True), ('g', True), ('b', True), ('a', False)):
        mask.set_editor_property(k, v)
    mel.connect_material_expressions(vc, '', mask, '')
    dec = node(ue.MaterialExpressionScalarParameter, -900, 180)
    dec.set_editor_property('parameter_name', 'VCDecodeExponent')
    dec.set_editor_property('default_value', VC_DECODE)
    pw = node(ue.MaterialExpressionPower, -700, 0)
    mel.connect_material_expressions(mask, '', pw, 'Base')
    mel.connect_material_expressions(dec, '', pw, 'Exponent')
    tint = node(ue.MaterialExpressionVectorParameter, -900, 320)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', ue.LinearColor(1, 1, 1, 1))
    tmask = node(ue.MaterialExpressionComponentMask, -700, 320)
    for k, v in (('r', True), ('g', True), ('b', True), ('a', False)):
        tmask.set_editor_property(k, v)
    mel.connect_material_expressions(tint, '', tmask, '')
    mul = node(ue.MaterialExpressionMultiply, -450, 100)
    mel.connect_material_expressions(pw, '', mul, 'A')
    mel.connect_material_expressions(tmask, '', mul, 'B')
    mel.connect_material_property(mul, '', ue.MaterialProperty.MP_BASE_COLOR)
    for i, (pname, prop, default) in enumerate((('Metallic', ue.MaterialProperty.MP_METALLIC, 0.0),
                                                ('Roughness', ue.MaterialProperty.MP_ROUGHNESS, .85),
                                                ('Specular', ue.MaterialProperty.MP_SPECULAR, .5))):
        p = node(ue.MaterialExpressionScalarParameter, -450, 300 + 140 * i)
        p.set_editor_property('parameter_name', pname)
        p.set_editor_property('default_value', default)
        mel.connect_material_property(p, '', prop)
    mel.recompile_material(mat)
    return mat


def run_import():
    import unreal as ue
    stamp = stamp_now()
    out = receipt_path('import', 'SK_KohenGadol_V1', stamp)
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    r = dict(status='starting', mode='import', utc=utc(), stamp=stamp, source=str(GLB), sourceSha256=sha(GLB),
             destination=FOLDER, errors=[])

    def write():
        out.write_text(json.dumps(r, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    try:
        if r['sourceSha256'] != manifest['sha256']:
            raise RuntimeError('GLB does not match kohen-gadol-v1-manifest.json')
        r['editorProcesses'] = _guards(ue)
        assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        tools = ue.AssetToolsHelpers.get_asset_tools()
        if assets.does_directory_exist(FOLDER) and assets.list_assets(FOLDER, recursive=True, include_folder=False):
            raise RuntimeError('%s already holds assets; refusing to import over it (build to new names)' % FOLDER)
        before = protected()
        r['protectedBefore'] = {'count': len(before), 'sha256OfList': hashlib.sha256(
            json.dumps(before, sort_keys=True).encode()).hexdigest()}
        cp = CHECKPOINT_ROOT / ('KohenGadol-Import-' + stamp)
        cp.mkdir(parents=True, exist_ok=False)
        for key, target in _targets().items():
            f = disk_umap(target['map'])
            shutil.copy2(f, cp / (key + '.umap'))
            if sha(cp / (key + '.umap')) != sha(f):
                raise RuntimeError('Checkpoint copy mismatch for ' + key)
        r['checkpoint'] = str(cp)
        write()
        skeleton = ue.load_asset(SKELETON)
        if not isinstance(skeleton, ue.Skeleton):
            raise RuntimeError('missing skeleton %s' % SKELETON)
        bones_before = sorted(str(b) for b in ue.AnimPoseExtensions.get_bone_names(
            ue.AnimPoseExtensions.get_reference_pose(skeleton)))
        want = sorted(manifest['jointNames'])
        r['skeletonBoneSetMatchesGenerator'] = set(bones_before) == set(want)
        if not r['skeletonBoneSetMatchesGenerator']:
            raise RuntimeError('existing skeleton bones %r != generator %r' % (bones_before, want))
        override, readback = _mesh_pipeline(ue, skeleton)
        r['pipelineReadback'] = readback
        task = ue.AssetImportTask()
        for key, value in dict(filename=str(GLB), destination_path=MESH_FOLDER, automated=True,
                               replace_existing=False, save=False, options=override).items():
            task.set_editor_property(key, value)
        tools.import_asset_tasks([task])
        objects = [o for o in list(task.get_objects()) if o]
        if not objects:
            objects = [o for o in (ue.load_asset(p) for p in assets.list_assets(
                MESH_FOLDER, recursive=True, include_folder=False)) if o]
        kinds = {}
        for o in objects:
            kinds.setdefault(o.get_class().get_name(), []).append(o.get_path_name())
        r['importedClasses'] = kinds
        if [o for o in objects if isinstance(o, ue.Skeleton)]:
            raise RuntimeError('importer created a Skeleton: %r' % kinds)
        if [o for o in objects if isinstance(o, ue.AnimSequence)]:
            raise RuntimeError('importer created an animation: %r' % kinds)
        meshes = [o for o in objects if isinstance(o, ue.SkeletalMesh)]
        if len(meshes) != 1:
            raise RuntimeError('expected exactly one SkeletalMesh: %r' % kinds)
        mesh = meshes[0]
        if mesh.get_editor_property('skeleton').get_path_name() != skeleton.get_path_name():
            raise RuntimeError('mesh bound to %s' % mesh.get_editor_property('skeleton').get_path_name())
        bones_after = sorted(str(b) for b in ue.AnimPoseExtensions.get_bone_names(
            ue.AnimPoseExtensions.get_reference_pose(skeleton)))
        r['skeletonBoneSetUnchanged'] = set(bones_before) == set(bones_after)
        if not r['skeletonBoneSetUnchanged']:
            raise RuntimeError('skeleton bone SET changed across the import')
        # materials, built to NEW names (delete_all_material_expressions does not empty a graph)
        master = _build_master(ue, tools, MASTER)
        mel = ue.MaterialEditingLibrary
        slots = manifest['slots']
        mis = {}
        for slot, prm in slots.items():
            mi = tools.create_asset('MI_%s_V1' % slot, MAT_FOLDER, ue.MaterialInstanceConstant,
                                    ue.MaterialInstanceConstantFactoryNew())
            mel.set_material_instance_parent(mi, master)
            for pname, value in (('Roughness', prm['roughness']), ('Metallic', prm['metallic']),
                                 ('Specular', prm['specular']), ('VCDecodeExponent', VC_DECODE)):
                mel.set_material_instance_scalar_parameter_value(mi, pname, value)
            mel.set_material_instance_vector_parameter_value(mi, 'Tint', ue.LinearColor(1, 1, 1, 1))
            mel.update_material_instance(mi)
            mis[slot] = mi
        # assign by slot NAME, after the import
        mats = list(mesh.get_editor_property('materials'))
        names = [str(m.get_editor_property('material_slot_name')) for m in mats]
        r['slotNamesImported'] = names
        if set(names) != set(slots):
            raise RuntimeError('imported slot names %r != generator slots %r' % (names, sorted(slots)))
        for m in mats:
            m.set_editor_property('material_interface', mis[str(m.get_editor_property('material_slot_name'))])
        mesh.set_editor_property('materials', mats)
        for obj in [master] + list(mis.values()) + [mesh]:
            if not assets.save_loaded_asset(obj, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset(%s) returned False (zombie editor?)' % obj.get_name())
        # readback
        rb = {'mesh': mesh.get_path_name(), 'skeleton': mesh.get_editor_property('skeleton').get_path_name(),
              'masterUsedWithSkeletalMesh': bool(master.get_editor_property('used_with_skeletal_mesh')),
              'masterExpressionCount': int(mel.get_num_material_expressions(master)), 'slots': {}}
        for m in mesh.get_editor_property('materials'):
            mi = m.get_editor_property('material_interface')
            slot = str(m.get_editor_property('material_slot_name'))
            rb['slots'][slot] = {
                'material': mi.get_path_name() if mi else None,
                'parent': mi.get_editor_property('parent').get_path_name() if mi else None,
                'roughness': float(mel.get_material_instance_scalar_parameter_value(mi, 'Roughness')),
                'metallic': float(mel.get_material_instance_scalar_parameter_value(mi, 'Metallic')),
                'vcDecode': float(mel.get_material_instance_scalar_parameter_value(mi, 'VCDecodeExponent'))}
        for prop in ('has_vertex_colors', 'enable_per_poly_collision'):
            try:
                rb[prop] = str(mesh.get_editor_property(prop))
            except Exception as error:                                   # noqa: BLE001
                rb[prop] = 'unavailable: ' + str(error)[:80]
        for lib, fn in (('SkeletalMeshEditorSubsystem', 'get_num_verts'), ('EditorSkeletalMeshLibrary', 'get_num_verts')):
            try:
                owner = ue.get_editor_subsystem(getattr(ue, lib)) if lib.endswith('Subsystem') else getattr(ue, lib)
                rb['numVertsLod0'] = int(getattr(owner, fn)(mesh, 0))
                break
            except Exception as error:                                   # noqa: BLE001
                rb['numVertsLod0'] = 'unavailable: ' + str(error)[:80]
        r['readback'] = rb
        bad = [s for s, v in rb['slots'].items() if not v['material'] or MASTER not in str(v['parent'])]
        if bad or not rb['masterUsedWithSkeletalMesh']:
            raise RuntimeError('slot readback failed %r / usage %r' % (bad, rb['masterUsedWithSkeletalMesh']))
        dirty = [p.get_name() for p in list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())]
        r['dirtyPackagesLeftUnsaved'] = dirty
        MARKER.write_text(json.dumps({'mesh': mesh.get_path_name(), 'master': master.get_path_name(),
                                      'instances': {k: v.get_path_name() for k, v in mis.items()},
                                      'sourceSha256': r['sourceSha256'], 'stamp': stamp}, indent=2) + '\n',
                          encoding='utf-8')
        after = protected()
        r['protectedChanged'] = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        r['protectedCount'] = len(after)
        if r['protectedChanged']:
            raise RuntimeError('protected assets changed: %r' % r['protectedChanged'])
        r['status'] = 'imported_saved_readback_apply_pending'
        write()
    except Exception:
        r['status'] = 'failed'
        r['errors'].append(traceback.format_exc())
        write()
        raise
    return r


def run_reimport():
    """Replace SK_KohenGadol_V1 IN PLACE (same object path, so the maps' configured_mesh stays valid),
    then re-assign the EXISTING V1 instances by slot name: a re-import resets material slots."""
    import unreal as ue
    stamp = stamp_now()
    out = receipt_path('reimport', 'SK_KohenGadol_V1', stamp)
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    m = marker()
    r = dict(status='starting', mode='reimport', utc=utc(), stamp=stamp, source=str(GLB), sourceSha256=sha(GLB),
             previousSourceSha256=m.get('sourceSha256'), target=m['mesh'], errors=[])

    def write():
        out.write_text(json.dumps(r, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    try:
        if r['sourceSha256'] != manifest['sha256']:
            raise RuntimeError('GLB does not match kohen-gadol-v1-manifest.json')
        r['editorProcesses'] = _guards(ue)
        assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        tools = ue.AssetToolsHelpers.get_asset_tools()
        mesh_file = disk_uasset(_object_path(m['mesh']))
        r['meshFileSha256Before'] = sha(mesh_file)
        before = protected()
        cp = CHECKPOINT_ROOT / ('KohenGadol-Reimport-' + stamp)
        cp.mkdir(parents=True, exist_ok=False)
        shutil.copy2(mesh_file, cp / mesh_file.name)
        for key, target in _targets().items():
            shutil.copy2(disk_umap(target['map']), cp / (key + '.umap'))
        r['checkpoint'] = str(cp)
        write()
        skeleton = ue.load_asset(SKELETON)
        bones_before = sorted(str(b) for b in ue.AnimPoseExtensions.get_bone_names(
            ue.AnimPoseExtensions.get_reference_pose(skeleton)))
        override, readback = _mesh_pipeline(ue, skeleton)
        r['pipelineReadback'] = readback
        task = ue.AssetImportTask()
        for key, value in dict(filename=str(GLB), destination_path=MESH_FOLDER, destination_name='SK_KohenGadol_V1',
                               automated=True, replace_existing=True, save=False, options=override).items():
            task.set_editor_property(key, value)
        tools.import_asset_tasks([task])
        mesh = ue.load_asset(m['mesh'])
        if not isinstance(mesh, ue.SkeletalMesh):
            raise RuntimeError('%s did not reload as a SkeletalMesh' % m['mesh'])
        if mesh.get_editor_property('skeleton').get_path_name() != skeleton.get_path_name():
            raise RuntimeError('re-imported mesh bound to %s' % mesh.get_editor_property('skeleton').get_path_name())
        bones_after = sorted(str(b) for b in ue.AnimPoseExtensions.get_bone_names(
            ue.AnimPoseExtensions.get_reference_pose(skeleton)))
        r['skeletonBoneSetUnchanged'] = set(bones_before) == set(bones_after)
        if not r['skeletonBoneSetUnchanged']:
            raise RuntimeError('skeleton bone SET changed across the re-import')
        mis = {k: ue.load_asset(v) for k, v in m['instances'].items()}
        mats = list(mesh.get_editor_property('materials'))
        r['slotsAfterReimportBeforeAssign'] = {str(x.get_editor_property('material_slot_name')):
                                               (x.get_editor_property('material_interface').get_path_name()
                                                if x.get_editor_property('material_interface') else None) for x in mats}
        for x in mats:
            x.set_editor_property('material_interface', mis[str(x.get_editor_property('material_slot_name'))])
        mesh.set_editor_property('materials', mats)
        if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset(mesh) returned False (zombie editor?)')
        _, slots = _verify_body(ue, m['mesh'])
        r['slotsReadback'] = slots
        r['meshFileSha256After'] = sha(mesh_file)
        after = protected()
        r['protectedChanged'] = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        if r['protectedChanged']:
            raise RuntimeError('protected assets changed: %r' % r['protectedChanged'])
        m['sourceSha256'] = r['sourceSha256']
        m['reimportStamp'] = stamp
        MARKER.write_text(json.dumps(m, indent=2) + '\n', encoding='utf-8')
        r['status'] = 'reimported_saved_slots_reassigned_readback'
        write()
    except Exception:
        r['status'] = 'failed'
        r['errors'].append(traceback.format_exc())
        write()
        raise
    return r


def run_import_revert():
    import unreal as ue
    stamp = stamp_now()
    out = receipt_path('import-revert', 'SK_KohenGadol_V1', stamp)
    r = dict(status='starting', mode='import-revert', utc=utc(), stamp=stamp, folder=FOLDER, errors=[])
    try:
        r['editorProcesses'] = _guards(ue)
        for key, target in _targets().items():
            text = disk_umap(target['map']).read_bytes()
            if b'KohenGadolV1' in text:
                raise RuntimeError('%s still references KohenGadolV1; revert the map first' % key)
        assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        before = protected()
        r['deleted'] = list(assets.list_assets(FOLDER, recursive=True, include_folder=False))
        if not assets.delete_directory(FOLDER):
            raise RuntimeError('delete_directory returned False')
        r['folderGone'] = not assets.does_directory_exist(FOLDER) or not assets.list_assets(FOLDER, recursive=True)
        after = protected()
        r['protectedChanged'] = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        if r['protectedChanged']:
            raise RuntimeError('protected assets changed: %r' % r['protectedChanged'])
        if MARKER.is_file():
            MARKER.rename(MARKER.with_name('kohen-gadol-import-marker.reverted-%s.json' % stamp))
        r['status'] = 'import_reverted'
    except Exception:
        r['status'] = 'failed'
        r['errors'].append(traceback.format_exc())
        raise
    finally:
        out.write_text(json.dumps(r, indent=2, default=str) + '\n', encoding='utf-8')
    return r


# ---------------------------------------------------------------------------------------- maps
def _verify_body(ue, mesh_path):
    mesh = ue.load_asset(mesh_path)
    m = marker()
    if mesh is None or mesh.get_path_name() != _object_path(m['mesh']):
        raise RuntimeError('marker mesh %s does not load' % m['mesh'])
    slots = {}
    for s in mesh.get_editor_property('materials'):
        mi = s.get_editor_property('material_interface')
        slots[str(s.get_editor_property('material_slot_name'))] = mi.get_path_name() if mi else None
    want = {k: _object_path(v) for k, v in m['instances'].items()}
    if slots != want:
        raise RuntimeError('KG mesh slots %r are not the V1 instances %r (re-import resets slots)' % (slots, want))
    master = ue.load_asset(m['master'])
    if not master.get_editor_property('used_with_skeletal_mesh'):
        raise RuntimeError('master lost bUsedWithSkeletalMesh')
    return mesh, slots


def _plan_apply(ue, key, before):
    if before.get('authored_body'):
        raise RuntimeError('AuthoredBody is set; the configured mesh would never be used')
    if before['service_scenario'] != 'ORDINARY_DAY':
        raise RuntimeError('Scenario %s is not ORDINARY_DAY (the golden garments are the ordinary-day set)'
                           % before['service_scenario'])
    kg = _object_path(marker()['mesh'])
    if before.get('configured_mesh') not in (BODY_MESH, kg):
        raise RuntimeError('configured_mesh is %r, not the V3 Man_Standard stand-in' % before.get('configured_mesh'))
    mesh, slots = _verify_body(ue, kg)
    skel = mesh.get_editor_property('skeleton')
    for f in ('walk_animation', 'idle_animation', 'tend_animation'):
        if before.get(f):
            clip = ue.load_asset(before[f])
            if clip is None or clip.get_editor_property('skeleton') != skel:
                raise RuntimeError('%s %s is not on the KG mesh skeleton' % (f, before[f]))
    wanted = dict(before)
    wanted['configured_mesh'] = kg
    return wanted, dict(mesh=kg, slots=slots, skeleton=skel.get_path_name(),
                        note='Only configured_mesh changes. GarmentMaterialSlots (Garment/Robe/Cloth/Body) name '
                             'no slot on this mesh, so ApplyGarment paints nothing over the KG_* materials.')


def _write(ue, actor, wanted, before):
    actor.modify(True)
    for field in WRITE:
        if _same(wanted.get(field), before.get(field)):
            continue
        value = wanted[field]
        asset = ue.load_asset(value) if value else None
        if value and asset is None:
            raise RuntimeError('Could not load %s' % value)
        actor.set_editor_property(field, asset)


def _apply(key, kind, plan_fn):
    stamp = stamp_now()
    targets = _targets()
    MAP = targets[key]['map']
    map_file = disk_umap(MAP)
    others = {k: disk_umap(t['map']) for k, t in targets.items() if k != key}
    out = receipt_path(kind, key, stamp)
    r = dict(status='starting', mode=kind, target=key, map=MAP, utc=utc(), stamp=stamp,
             mapBeforeSha256=sha(map_file), otherMapsBefore={k: sha(v) for k, v in others.items()}, errors=[])

    def write():
        out.write_text(json.dumps(r, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    import unreal as ue
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    this_map = str(map_file.relative_to(ROOT)).replace('\\', '/')
    try:
        r['editorProcesses'] = _guards(ue)
        protected_before = protected()
        r['protectedBeforeCount'] = len(protected_before)
        cp = CHECKPOINT_ROOT / ('KohenGadol-%s-%s' % (key, stamp))
        cp.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, cp / 'BeforeKohenGadol.umap')
        if sha(cp / 'BeforeKohenGadol.umap') != r['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy mismatch')
        r['checkpoint'] = str(cp)
        write()
        if editor.get_editor_world().get_outermost().get_name() != MAP and not levels.load_level(MAP):
            raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Unexpected editor world')
        crowd = _load('kohen_gadol_snapshot', 'Scripts/release_resident_crowd.py')
        baseline = crowd._scene_snapshot(ue, actors)
        kohen, before = TEND._read(ue, actors, key)
        r['before'] = before
        wanted, notes = plan_fn(ue, key, before)
        r['wanted'], r['notes'] = wanted, notes
        write()
        changed = not _same(wanted, before)
        if changed:
            _write(ue, kohen, wanted, before)
        _, after_set = TEND._read(ue, actors, key)
        if not _same(after_set, wanted):
            raise RuntimeError('Did not read back as planned before save: %r' % after_set)
        after_scene = crowd._scene_snapshot(ue, actors)
        moved = {k for k in set(baseline) | set(after_scene) if baseline.get(k) != after_scene.get(k)}
        if moved - ({kohen.get_name()} if changed else set()):
            raise RuntimeError('Unexpected scene changes: %r' % sorted(moved)[:20])
        r['sceneChanges'] = sorted(moved)
        if changed:
            if not levels.save_current_level():
                raise RuntimeError('Level save failed')
            r.update(mapSaved=True, mapAfterSha256=sha(map_file), status='saved_reopen_pending')
            write()
            if not levels.load_level(MAP) or editor.get_editor_world().get_outermost().get_name() != MAP:
                raise RuntimeError('Reopen failed')
        else:
            r.update(mapSaved=False, mapAfterSha256=sha(map_file))
        _, readback = TEND._read(ue, actors, key)
        r['readbackAfterReopen'] = readback
        if not _same(readback, wanted):
            raise RuntimeError('Readback after reopen differs: %r' % readback)
        r['otherMapsAfter'] = {k: sha(v) for k, v in others.items()}
        r['otherMapsUnchanged'] = r['otherMapsAfter'] == r['otherMapsBefore']
        if not r['otherMapsUnchanged']:
            raise RuntimeError('Another map changed bytes during the run')
        protected_after = protected()
        r['protectedChangedExcludingThisMap'] = sorted(
            k for k in set(protected_before) | set(protected_after)
            if protected_before.get(k) != protected_after.get(k) and k != this_map)
        if r['protectedChangedExcludingThisMap']:
            raise RuntimeError('Protected assets changed: %r' % r['protectedChangedExcludingThisMap'])
        r['status'] = ('%s_saved_reopened_readback_frame_pending' % kind) if changed else ('%s_no_change_needed' % kind)
        write()
    except Exception:
        r['status'] = 'failed'
        r['errors'].append(traceback.format_exc())
        try:
            r['mapAfterSha256'] = sha(map_file)
        except Exception:                                             # noqa: BLE001
            pass
        write()
        raise
    return r


def run_apply(key):
    return _apply(key, 'apply', _plan_apply)


def run_revert(key):
    previous = sorted(p for p in OUT.glob('kohen-gadol-apply-%s-*.json' % key)
                      if json.loads(p.read_text(encoding='utf-8-sig')).get('mapSaved'))
    if not previous:
        raise RuntimeError('No saved apply receipt for %s to revert' % key)
    src = json.loads(previous[-1].read_text(encoding='utf-8-sig'))

    def plan(ue, k, before):
        restore = dict(before)
        restore['configured_mesh'] = src['before']['configured_mesh']
        for f in ('authored_body', 'service_scenario', 'walk_animation', 'idle_animation', 'tend_animation'):
            if not _same(before.get(f), src['before'].get(f)):
                raise RuntimeError('%s moved since the apply (%r -> %r); refuse to revert blind'
                                   % (f, src['before'].get(f), before.get(f)))
        return restore, dict(revertSource=previous[-1].name, revertSourceSha256=sha(previous[-1]))
    return _apply(key, 'revert', plan)


def _key(cmd):
    m = re.search(r'-KohenTarget=(Main50|Candidate48)', cmd)
    if not m:
        raise RuntimeError('Pass -KohenTarget=Main50|Candidate48')
    return m.group(1)


def _main():
    import unreal
    cmd = unreal.SystemLibrary.get_command_line()
    try:
        if '-KohenGadolImportRevert' in cmd:
            run_import_revert()
        elif '-KohenGadolReimport' in cmd:
            run_reimport()
        elif '-KohenGadolImport' in cmd:
            run_import()
        elif '-KohenGadolRevertAndReapply' in cmd:
            key = _key(cmd)
            run_revert(key)
            run_apply(key)
        elif '-KohenGadolApplyAll' in cmd:
            for key in ('Candidate48', 'Main50'):
                run_apply(key)
        elif '-KohenGadolApply' in cmd:
            run_apply(_key(cmd))
        elif '-KohenGadolRevert' in cmd:
            run_revert(_key(cmd))
        else:
            raise RuntimeError('release_kohen_gadol_v1: pass a -KohenGadol* mode')
    except Exception:
        receipt_path('failure', 'any', stamp_now()).write_text(
            json.dumps(dict(commandLine=cmd, error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise
    finally:
        if '-executepythonscript' in cmd.lower() and '-run=pythonscript' not in cmd.lower():
            unreal.SystemLibrary.quit_editor()


if __name__ == '__main__':
    _main()

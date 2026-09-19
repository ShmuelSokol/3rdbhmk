"""ResidentV4 bodies into the engine. Hidden editor, ONE engine at a time.

  UnrealEditor.exe <uproject> -ExecutePythonScript=<this> <MODE> -unattended -nullrhi -NoSplash -abslog=<log>

  -RV4Import        textures (4), masters M_RV4_Cloth / M_RV4_Skin (bUsedWithSkeletalMesh AND
                    bUsedWithMorphTargets, or the cook substitutes the default material), shared slot
                    instances, one garment instance per population garment key, and the six GLBs from
                    SourceAssets/characters-review/ResidentV4/meshes, EACH onto its variant's EXISTING
                    V3 Skeleton (so the shipped WalkV2 / Idle clips play unchanged). Morph targets Face0..3
                    required. Slots assigned by name AFTER the import. Refuses if a Skeleton or animation is
                    created, if a bone SET changes, or if any protected asset (all of PilgrimRigV3, the
                    Kohen Gadol, both maps) changes bytes.
  -RV4ImportRevert  delete /Game/MikdashV3/Characters/ResidentV4; refuses while a map references it.
  -RV4Apply -RV4Target=Candidate48|Main50
                    Guard pattern: checkpoint the .umap into ReviewCheckpoints/ResidentV4-*, protected hashes
                    before/after, on RELEASE_PeopleV3Population set ONLY body_variants[*].skeletal_mesh and
                    .garment_material_slots for the six cast variants and garment_materials (same keys, V4
                    instances); save, reopen, numeric readback, scene snapshot (only the population differs).
  -RV4Revert -RV4Target=...       restore those three fields from the newest saved apply receipt.
  -RV4RevertAndReapply -RV4Target=...
  -RV4ApplyAll                    Candidate48 then Main50.
"""
import hashlib, importlib.util, json, re, shutil, sys, traceback
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SRC = ROOT / 'SourceAssets/characters-review/ResidentV4'
MANIFEST = SRC / 'resident-v4-manifest.json'
TEXTURES = SRC / 'textures'
MARKER = SRC / 'resident-v4-import-marker.json'
OUT = SRC / 'engine'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
FOLDER = '/Game/MikdashV3/Characters/ResidentV4'
MAT_FOLDER = FOLDER + '/Materials'
TEX_FOLDER = FOLDER + '/Textures'
POP_LABEL = 'RELEASE_PeopleV3Population'
VC_DECODE = 1.0  # Source COLOR_0 is linear; native import calibration preserves it.
WALK_MARKER = ROOT / 'SourceAssets/characters-review/PilgrimRigV3/walk-v2/walkv2-import-progress.json'
PEOPLE_SPEC = ROOT / 'Scripts/release_people_v3.spec.json'
MORPHS = ('Face0', 'Face1', 'Face2', 'Face3')
GARMENT_SLOT = 'RV4_Garment'


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WALK = _load('release_walk_v2_for_rv4', 'Scripts/release_walk_v2.py')
FIN = _load('release_walk_v2_finish_for_rv4', 'Scripts/release_walk_v2_finish.py')
sha, stamp_now, utc, _same = FIN.sha, FIN.stamp_now, FIN.utc, FIN._same
_object_path, disk_umap, disk_uasset, _targets, _guards = (WALK._object_path, WALK.disk_umap, WALK.disk_uasset,
                                                          WALK._targets, WALK._guards)
# slot -> (master, roughness, specular, texture param set)
SLOT_MI = {
    'RV4_Skin': ('skin', .52, .45, dict(Pores='T_RV4_PoresN', Mottle='T_RV4_SlubMottle', PoreTiling=25.0, PoreStrength=.15,
                                         MottleTiling=.7, MottleStrength=.10)),
    'RV4_Eye': ('cloth', .06, .80, dict(WeaveNormal='T_RV4_PoresN', Mottle='T_RV4_SlubMottle', WeaveTiling=1.0,
                                         WeaveStrength=0.0, MottleTiling=1.0, MottleStrength=0.0)),
    'RV4_Hair': ('cloth', .55, .38, dict(WeaveNormal='T_RV4_StrandN', Mottle='T_RV4_SlubMottle', WeaveTiling=18.0,
                                          WeaveStrength=.70, MottleTiling=2.0, MottleStrength=.25)),
    'RV4_Cloth': ('cloth', .88, .40, dict(WeaveNormal='T_RV4_WeaveN', Mottle='T_RV4_SlubMottle', WeaveTiling=12.0,
                                           WeaveStrength=.75, MottleTiling=.55, MottleStrength=.32)),
    'RV4_Garment': ('cloth', .90, .38, dict(WeaveNormal='T_RV4_WeaveN', Mottle='T_RV4_SlubMottle', WeaveTiling=7.0,
                                             WeaveStrength=.85, MottleTiling=.45, MottleStrength=.38)),
    'RV4_Leather': ('cloth', .66, .42, dict(WeaveNormal='T_RV4_PoresN', Mottle='T_RV4_SlubMottle', WeaveTiling=6.0,
                                             WeaveStrength=.45, MottleTiling=1.5, MottleStrength=.30)),
}
DEFAULT_GARMENT_TINT = (.72, .66, .52)


def receipt_path(kind, key, stamp):
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT / ('resident-v4-%s-%s-%s.json' % (kind, key, stamp))


def protected():
    out = {}
    for tree in ('Content/MikdashV3/Characters/PilgrimRigV3', 'Content/MikdashV3/Characters/KohenGadolV1'):
        for f in sorted((ROOT / tree).rglob('*.uasset')):
            out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    for key, target in _targets().items():
        f = disk_umap(target['map'])
        out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    return out


def walk_marker():
    return json.loads(WALK_MARKER.read_text(encoding='utf-8-sig'))['completed']


def garment_keys():
    g = json.loads(PEOPLE_SPEC.read_text(encoding='utf-8-sig'))['garments']['variants']
    return {k: dict(asset='MI_RV4_' + v['asset'][3:], color=v['baseColor'], roughness=v['roughness']) for k, v in g.items()}


# ---------------------------------------------------------------------------------------- materials
def _mel(ue):
    return ue.MaterialEditingLibrary


def _build_master(ue, tools, name, skin):
    mel = _mel(ue)
    mat = tools.create_asset(name, MAT_FOLDER, ue.Material, ue.MaterialFactoryNew())
    if mat is None:
        raise RuntimeError('could not create %s' % name)
    mat.set_editor_property('used_with_skeletal_mesh', True)
    mat.set_editor_property('used_with_morph_targets', True)
    if skin:
        mat.set_editor_property('shading_model', ue.MaterialShadingModel.MSM_SUBSURFACE)

    def node(cls, x, y):
        return mel.create_material_expression(mat, cls, x, y)

    def scalar(pname, default, x, y):
        p = node(ue.MaterialExpressionScalarParameter, x, y)
        p.set_editor_property('parameter_name', pname)
        p.set_editor_property('default_value', default)
        return p

    def texparam(pname, tex, normal, x, y):
        t = node(ue.MaterialExpressionTextureSampleParameter2D, x, y)
        t.set_editor_property('parameter_name', pname)
        t.set_editor_property('texture', tex)
        t.set_editor_property('sampler_type', ue.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal
                              else ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        return t

    def mul(a, b, x, y, ao='', bo=''):
        m = node(ue.MaterialExpressionMultiply, x, y)
        mel.connect_material_expressions(a, ao, m, 'A')
        mel.connect_material_expressions(b, bo, m, 'B')
        return m
    texs = {n: ue.load_asset(TEX_FOLDER + '/' + n) for n in ('T_RV4_WeaveN', 'T_RV4_SlubMottle', 'T_RV4_PoresN')}
    uv = node(ue.MaterialExpressionTextureCoordinate, -1700, 400)
    # base colour: pow(VC, 1.0) * Tint * (1 + (mottle - .5) * 2 * MottleStrength)
    vc = node(ue.MaterialExpressionVertexColor, -1500, -200)
    mask = node(ue.MaterialExpressionComponentMask, -1300, -200)
    for k, v in (('r', True), ('g', True), ('b', True), ('a', False)):
        mask.set_editor_property(k, v)
    mel.connect_material_expressions(vc, '', mask, '')
    pw = node(ue.MaterialExpressionPower, -1100, -200)
    mel.connect_material_expressions(mask, '', pw, 'Base')
    decode = scalar('VCDecodeExponent', VC_DECODE, -1300, -60)
    if not mel.connect_material_expressions(decode, '', pw, 'Exp'):
        raise RuntimeError('Vertex-colour exponent connection failed')
    if list(mel.get_inputs_for_material_expression(mat, pw))[1] != decode:
        raise RuntimeError('Vertex-colour exponent connection readback failed')
    tint = node(ue.MaterialExpressionVectorParameter, -1300, 40)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', ue.LinearColor(1, 1, 1, 1))
    tmask = node(ue.MaterialExpressionComponentMask, -1100, 40)
    for k, v in (('r', True), ('g', True), ('b', True), ('a', False)):
        tmask.set_editor_property(k, v)
    mel.connect_material_expressions(tint, '', tmask, '')
    base = mul(pw, tmask, -900, -100)
    muv = mul(uv, scalar('MottleTiling', .5, -1700, 520), -1500, 480)
    mot = texparam('Mottle', texs['T_RV4_SlubMottle'], False, -1300, 480)
    mel.connect_material_expressions(muv, '', mot, 'UVs')
    half = node(ue.MaterialExpressionConstant, -1100, 640)
    half.set_editor_property('r', .5)
    centred = node(ue.MaterialExpressionSubtract, -1000, 520)
    mel.connect_material_expressions(mot, 'R', centred, 'A')
    mel.connect_material_expressions(half, '', centred, 'B')
    ms = mul(centred, scalar('MottleStrength', .3, -1100, 720), -850, 560)
    two = node(ue.MaterialExpressionConstant, -850, 760)
    two.set_editor_property('r', 2.0)
    ms2 = mul(ms, two, -700, 640)
    one = node(ue.MaterialExpressionConstant, -700, 760)
    one.set_editor_property('r', 1.0)
    fac = node(ue.MaterialExpressionAdd, -550, 640)
    mel.connect_material_expressions(one, '', fac, 'A')
    mel.connect_material_expressions(ms2, '', fac, 'B')
    final = mul(base, fac, -400, -40)
    mel.connect_material_property(final, '', ue.MaterialProperty.MP_BASE_COLOR)
    # roughness: Roughness + (mottle - .5) * .15
    k15 = node(ue.MaterialExpressionConstant, -700, 980)
    k15.set_editor_property('r', .15)
    rq = mul(centred, k15, -550, 960)
    radd = node(ue.MaterialExpressionAdd, -400, 900)
    mel.connect_material_expressions(scalar('Roughness', .85, -550, 1060), '', radd, 'A')
    mel.connect_material_expressions(rq, '', radd, 'B')
    mel.connect_material_property(radd, '', ue.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(scalar('Specular', .5, -400, 1160), '', ue.MaterialProperty.MP_SPECULAR)
    # normal: lerp((0,0,1), tex, Strength) at UV * Tiling
    nname, tname, sname, tex = (('Pores', 'PoreTiling', 'PoreStrength', texs['T_RV4_PoresN']) if skin else
                                ('WeaveNormal', 'WeaveTiling', 'WeaveStrength', texs['T_RV4_WeaveN']))
    nuv = mul(uv, scalar(tname, 10.0, -1700, 1300), -1500, 1300)
    ntex = texparam(nname, tex, True, -1300, 1300)
    mel.connect_material_expressions(nuv, '', ntex, 'UVs')
    flat = node(ue.MaterialExpressionConstant3Vector, -1100, 1200)
    flat.set_editor_property('constant', ue.LinearColor(0, 0, 1, 1))
    lp = node(ue.MaterialExpressionLinearInterpolate, -900, 1300)
    mel.connect_material_expressions(flat, '', lp, 'A')
    mel.connect_material_expressions(ntex, 'RGB', lp, 'B')
    mel.connect_material_expressions(scalar(sname, .6, -1100, 1450), '', lp, 'Alpha')
    mel.connect_material_property(lp, '', ue.MaterialProperty.MP_NORMAL)
    if skin:
        ssc = node(ue.MaterialExpressionVectorParameter, -600, 1500)
        ssc.set_editor_property('parameter_name', 'SubsurfaceColor')
        ssc.set_editor_property('default_value', ue.LinearColor(.62, .20, .11, 1))
        mel.connect_material_property(ssc, '', ue.MaterialProperty.MP_SUBSURFACE_COLOR)
        mel.connect_material_property(scalar('SubsurfaceAmount', .38, -600, 1650), '', ue.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    return mat


def _import_textures(ue, tools, assets, r):
    out = {}
    man = json.loads((TEXTURES / 'textures-manifest.json').read_text(encoding='utf-8-sig'))
    for fname, info in man.items():
        f = TEXTURES / fname
        if sha(f) != info['sha256']:
            raise RuntimeError('texture %s does not match its manifest' % fname)
        name = f.stem
        task = ue.AssetImportTask()
        for k, v in dict(filename=str(f), destination_path=TEX_FOLDER, destination_name=name, automated=True,
                         replace_existing=False, save=False).items():
            task.set_editor_property(k, v)
        tools.import_asset_tasks([task])
        tex = ue.load_asset(TEX_FOLDER + '/' + name)
        if not isinstance(tex, ue.Texture2D):
            raise RuntimeError('texture %s did not import' % name)
        normal = info['kind'] == 'normal'
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('compression_settings', ue.TextureCompressionSettings.TC_NORMALMAP if normal
                                else ue.TextureCompressionSettings.TC_DEFAULT)
        if normal:
            tex.set_editor_property('flip_green_channel', True)     # authored Y-up; UE normal maps are Y-down
        if not assets.save_loaded_asset(tex, only_if_is_dirty=False):
            raise RuntimeError('save texture %s failed' % name)
        out[name] = dict(path=tex.get_path_name(), srgb=bool(tex.get_editor_property('srgb')),
                         compression=str(tex.get_editor_property('compression_settings')))
    r['textures'] = out
    return out


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
        apply(cm, 'use_full_precision_u_vs', True, False)
    except Exception as error:                                       # noqa: BLE001
        readback['common_meshes_properties'] = 'unavailable: ' + str(error)[:120]
    mesh = pipeline.get_editor_property('mesh_pipeline')
    apply(mesh, 'import_static_meshes', False, True)
    apply(mesh, 'import_skeletal_meshes', True, True)
    apply(mesh, 'create_physics_asset', False, False)
    apply(mesh, 'import_morph_targets', True, True)
    apply(pipeline.get_editor_property('animation_pipeline'), 'import_animations', False, True)
    apply(pipeline.get_editor_property('material_pipeline'), 'import_materials', True, False)
    if missing:
        raise RuntimeError('Interchange pipeline would not accept %r; readback %r' % (missing, readback))
    if skeleton.get_name() not in str(readback.get('skeleton', '')):
        raise RuntimeError('common.skeleton did not read back as %s' % skeleton.get_name())
    override = ue.InterchangePipelineStackOverride()
    override.add_pipeline(pipeline)
    return override, readback


def _bones(ue, skeleton):
    return sorted(str(b) for b in ue.AnimPoseExtensions.get_bone_names(ue.AnimPoseExtensions.get_reference_pose(skeleton)))


def run_import():
    import unreal as ue
    stamp = stamp_now()
    out = receipt_path('import', 'all', stamp)
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    r = dict(status='starting', mode='import', utc=utc(), stamp=stamp, destination=FOLDER,
             manifestSha256=sha(MANIFEST), variants={}, errors=[])

    def write():
        out.write_text(json.dumps(r, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    try:
        r['editorProcesses'] = _guards(ue)
        assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        tools = ue.AssetToolsHelpers.get_asset_tools()
        mel = _mel(ue)
        if assets.does_directory_exist(FOLDER) and assets.list_assets(FOLDER, recursive=True, include_folder=False):
            raise RuntimeError('%s already holds assets; revert the import first' % FOLDER)
        before = protected()
        r['protectedBeforeCount'] = len(before)
        cp = CHECKPOINT_ROOT / ('ResidentV4-Import-' + stamp)
        cp.mkdir(parents=True, exist_ok=False)
        for key, target in _targets().items():
            f = disk_umap(target['map'])
            shutil.copy2(f, cp / (key + '.umap'))
            if sha(cp / (key + '.umap')) != sha(f):
                raise RuntimeError('Checkpoint copy mismatch for ' + key)
        r['checkpoint'] = str(cp)
        write()
        texs = _import_textures(ue, tools, assets, r)
        masters = {'cloth': _build_master(ue, tools, 'M_RV4_Cloth', False), 'skin': _build_master(ue, tools, 'M_RV4_Skin', True)}
        for m in masters.values():
            if not (m.get_editor_property('used_with_skeletal_mesh') and m.get_editor_property('used_with_morph_targets')):
                raise RuntimeError('%s lost its usage flags' % m.get_name())
            if not assets.save_loaded_asset(m, only_if_is_dirty=False):
                raise RuntimeError('save %s failed' % m.get_name())

        def make_mi(name, slot, tint=None, rough=None):
            master, rgh, spec, params = SLOT_MI[slot]
            mi = tools.create_asset(name, MAT_FOLDER, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew())
            mel.set_material_instance_parent(mi, masters[master])
            for pname, value in params.items():
                if isinstance(value, str):
                    mel.set_material_instance_texture_parameter_value(mi, pname, ue.load_asset(texs[value]['path']))
                else:
                    mel.set_material_instance_scalar_parameter_value(mi, pname, value)
            mel.set_material_instance_scalar_parameter_value(mi, 'Roughness', rough if rough is not None else rgh)
            mel.set_material_instance_scalar_parameter_value(mi, 'Specular', spec)
            mel.set_material_instance_scalar_parameter_value(mi, 'VCDecodeExponent', VC_DECODE)
            t = tint or (1, 1, 1)
            mel.set_material_instance_vector_parameter_value(mi, 'Tint', ue.LinearColor(t[0], t[1], t[2], 1))
            mel.update_material_instance(mi)
            if not assets.save_loaded_asset(mi, only_if_is_dirty=False):
                raise RuntimeError('save %s failed' % name)
            got = mel.get_material_instance_vector_parameter_value(mi, 'Tint')
            if abs(got.r - t[0]) > .002 or abs(got.b - t[2]) > .002:
                raise RuntimeError('%s Tint did not read back' % name)
            return mi
        slot_mis = {s: make_mi('MI_%s' % s, s, DEFAULT_GARMENT_TINT if s == GARMENT_SLOT else None) for s in SLOT_MI}
        garments = {}
        for key, g in garment_keys().items():
            garments[key] = make_mi(g['asset'], GARMENT_SLOT, tuple(g['color']), g['roughness']).get_path_name()
        r['slotInstances'] = {k: v.get_path_name() for k, v in slot_mis.items()}
        r['garmentInstances'] = garments
        write()
        wm = walk_marker()
        meshes = {}
        for row in manifest['variants']:
            vid = row['id']
            glb = SRC / row['file']
            if sha(glb) != row['sha256']:
                raise RuntimeError('%s does not match the manifest' % glb.name)
            skeleton = ue.load_asset(wm[vid]['skeleton'])
            if not isinstance(skeleton, ue.Skeleton):
                raise RuntimeError('missing skeleton for %s' % vid)
            b0 = _bones(ue, skeleton)
            if set(b0) != set(manifest['jointNames']):
                raise RuntimeError('%s skeleton bones differ from the generator' % vid)
            override, readback = _mesh_pipeline(ue, skeleton)
            dest = FOLDER + '/' + row['mesh'][7:]
            task = ue.AssetImportTask()
            for k, v in dict(filename=str(glb), destination_path=dest, automated=True, replace_existing=False,
                             save=False, options=override).items():
                task.set_editor_property(k, v)
            tools.import_asset_tasks([task])
            objs = [o for o in list(task.get_objects()) if o] or \
                   [o for o in (ue.load_asset(p) for p in assets.list_assets(dest, recursive=True, include_folder=False)) if o]
            kinds = {}
            for o in objs:
                kinds.setdefault(o.get_class().get_name(), []).append(o.get_path_name())
            if [o for o in objs if isinstance(o, (ue.Skeleton, ue.AnimSequence))]:
                raise RuntimeError('%s: importer created a Skeleton or an animation: %r' % (vid, kinds))
            ms = [o for o in objs if isinstance(o, ue.SkeletalMesh)]
            if len(ms) != 1:
                raise RuntimeError('%s: expected one SkeletalMesh: %r' % (vid, kinds))
            mesh = ms[0]
            if mesh.get_editor_property('skeleton').get_path_name() != skeleton.get_path_name():
                raise RuntimeError('%s bound to the wrong skeleton' % vid)
            if set(_bones(ue, skeleton)) != set(b0):
                raise RuntimeError('%s: skeleton bone SET changed' % vid)
            morphs = None
            for how in ('names', 'property'):
                try:
                    if how == 'names':
                        morphs = sorted(str(n) for n in mesh.get_all_morph_target_names())
                    else:
                        morphs = sorted(m.get_name() for m in mesh.get_editor_property('morph_targets'))
                    break
                except Exception as error:                               # noqa: BLE001
                    r.setdefault('morphReadbackErrors', []).append('%s: %s' % (how, str(error)[:120]))
            if morphs != sorted(MORPHS):
                raise RuntimeError('%s morph targets %r, need %r' % (vid, morphs, MORPHS))
            mats = list(mesh.get_editor_property('materials'))
            names = [str(m.get_editor_property('material_slot_name')) for m in mats]
            for m in mats:
                m.set_editor_property('material_interface', slot_mis[str(m.get_editor_property('material_slot_name'))])
            mesh.set_editor_property('materials', mats)
            if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('save %s failed (zombie editor?)' % mesh.get_name())
            slots = {str(m.get_editor_property('material_slot_name')): m.get_editor_property('material_interface').get_path_name()
                     for m in mesh.get_editor_property('materials')}
            meshes[vid] = mesh.get_path_name()
            r['variants'][vid] = dict(mesh=mesh.get_path_name(), skeleton=skeleton.get_path_name(), glbSha256=row['sha256'],
                                      imported=kinds, slotNames=names, slots=slots, morphTargets=morphs,
                                      boneSetUnchanged=True, pipelineReadback=readback)
            write()
        # delete Interchange's own per-slot materials (unreferenced now), then prove nothing protected moved
        dirty = [p.get_name() for p in list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())]
        r['dirtyPackagesLeftUnsaved'] = dirty
        MARKER.write_text(json.dumps({'meshes': meshes, 'masters': {k: v.get_path_name() for k, v in masters.items()},
                                      'slotInstances': r['slotInstances'], 'garmentInstances': garments,
                                      'textures': {k: v['path'] for k, v in texs.items()},
                                      'manifestSha256': r['manifestSha256'], 'stamp': stamp}, indent=2) + '\n', encoding='utf-8')
        after = protected()
        r['protectedChanged'] = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        r['protectedCount'] = len(after)
        if r['protectedChanged']:
            raise RuntimeError('protected assets changed: %r' % r['protectedChanged'][:20])
        r['status'] = 'imported_saved_readback_apply_pending'
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
    out = receipt_path('import-revert', 'all', stamp)
    r = dict(status='starting', mode='import-revert', utc=utc(), stamp=stamp, folder=FOLDER, errors=[])
    try:
        r['editorProcesses'] = _guards(ue)
        for key, target in _targets().items():
            if b'ResidentV4' in disk_umap(target['map']).read_bytes():
                raise RuntimeError('%s still references ResidentV4; revert the map first' % key)
        assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        before = protected()
        r['deleted'] = list(assets.list_assets(FOLDER, recursive=True, include_folder=False))
        if not assets.delete_directory(FOLDER):
            raise RuntimeError('delete_directory returned False')
        after = protected()
        r['protectedChanged'] = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        if r['protectedChanged']:
            raise RuntimeError('protected assets changed: %r' % r['protectedChanged'])
        if MARKER.is_file():
            MARKER.rename(MARKER.with_name('resident-v4-import-marker.reverted-%s.json' % stamp))
        r['status'] = 'import_reverted'
    except Exception:
        r['status'] = 'failed'
        r['errors'].append(traceback.format_exc())
        raise
    finally:
        out.write_text(json.dumps(r, indent=2, default=str) + '\n', encoding='utf-8')
    return r


# ---------------------------------------------------------------------------------------- maps
def _p(o):
    return o.get_path_name() if o is not None else None


def _find_pop(actors):
    found = [a for a in actors.get_all_level_actors() if a.get_actor_label() == POP_LABEL]
    if len(found) != 1:
        raise RuntimeError('Expected exactly one %s, found %d' % (POP_LABEL, len(found)))
    return found[0]


def _read(actors):
    pop = _find_pop(actors)
    rows = []
    for s in pop.get_editor_property('body_variants'):
        rows.append(dict(id=str(s.get_editor_property('id')), skeletalMesh=_p(s.get_editor_property('skeletal_mesh')),
                         idle=_p(s.get_editor_property('idle_animation')), walk=_p(s.get_editor_property('walk_animation')),
                         garmentSlots=[str(n) for n in s.get_editor_property('garment_material_slots')],
                         meshRelativeYaw=float(s.get_editor_property('mesh_relative_yaw')),
                         walkClipGroundSpeedCmPerSec=float(s.get_editor_property('walk_clip_ground_speed_cm_per_sec')),
                         walkClipNeutralPhase=float(s.get_editor_property('walk_clip_neutral_phase'))))
    return pop, dict(bodyVariants=rows, garmentKeys=[str(k) for k in pop.get_editor_property('garment_variant_keys')],
                     garmentMaterials=[_p(m) for m in pop.get_editor_property('garment_materials')])


def _plan_apply(ue, state):
    m = json.loads(MARKER.read_text(encoding='utf-8-sig'))
    wanted = json.loads(json.dumps(state))
    hit = 0
    for row in wanted['bodyVariants']:
        if row['id'] not in m['meshes']:
            continue
        mesh = ue.load_asset(m['meshes'][row['id']])
        skel = mesh.get_editor_property('skeleton')
        for f in ('idle', 'walk'):
            clip = ue.load_asset(row[f])
            if clip is None or clip.get_editor_property('skeleton') != skel:
                raise RuntimeError('%s %s is not on the V4 mesh skeleton' % (row['id'], f))
        slots = [str(x.get_editor_property('material_slot_name')) for x in mesh.get_editor_property('materials')]
        if GARMENT_SLOT not in slots:
            raise RuntimeError('%s has no %s slot' % (row['id'], GARMENT_SLOT))
        row['skeletalMesh'] = mesh.get_path_name()
        row['garmentSlots'] = [GARMENT_SLOT]
        hit += 1
    if hit != len(m['meshes']):
        raise RuntimeError('only %d of %d V4 variants are registered on the population' % (hit, len(m['meshes'])))
    missing = [k for k in state['garmentKeys'] if k not in m['garmentInstances']]
    if missing:
        raise RuntimeError('no V4 garment instance for keys %r' % missing)
    wanted['garmentMaterials'] = [m['garmentInstances'][k] for k in state['garmentKeys']]
    return wanted


def _write(ue, pop, wanted):
    pop.modify(True)
    structs = []
    for row in wanted['bodyVariants']:
        s = ue.MikdashResidentBodyVariant()
        s.set_editor_property('id', row['id'])
        s.set_editor_property('skeletal_mesh', ue.load_asset(row['skeletalMesh']))
        s.set_editor_property('idle_animation', ue.load_asset(row['idle']))
        s.set_editor_property('walk_animation', ue.load_asset(row['walk']))
        s.set_editor_property('garment_material_slots', [ue.Name(n) for n in row['garmentSlots']])
        s.set_editor_property('mesh_relative_yaw', row['meshRelativeYaw'])
        s.set_editor_property('walk_clip_ground_speed_cm_per_sec', row['walkClipGroundSpeedCmPerSec'])
        s.set_editor_property('walk_clip_neutral_phase', row['walkClipNeutralPhase'])
        structs.append(s)
    pop.set_editor_property('body_variants', structs)
    pop.set_editor_property('garment_materials', [ue.load_asset(p) for p in wanted['garmentMaterials']])


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
        pb = protected()
        for f in sorted((ROOT / 'Content/MikdashV3/Characters/ResidentV4').rglob('*.uasset')):
            pb[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
        cp = CHECKPOINT_ROOT / ('ResidentV4-%s-%s' % (key, stamp))
        cp.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, cp / 'BeforeResidentV4.umap')
        if sha(cp / 'BeforeResidentV4.umap') != r['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy mismatch')
        r['checkpoint'] = str(cp)
        write()
        if editor.get_editor_world().get_outermost().get_name() != MAP and not levels.load_level(MAP):
            raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Unexpected editor world')
        crowd = _load('rv4_snapshot', 'Scripts/release_resident_crowd.py')
        baseline = crowd._scene_snapshot(ue, actors)
        pop, before = _read(actors)
        r['before'] = before
        wanted = plan_fn(ue, before)
        r['wanted'] = wanted
        write()
        changed = not _same(wanted, before)
        if changed:
            _write(ue, pop, wanted)
        _, got = _read(actors)
        if not _same(got, wanted):
            raise RuntimeError('Did not read back as planned before save: %r' % got)
        after_scene = crowd._scene_snapshot(ue, actors)
        moved = {k for k in set(baseline) | set(after_scene) if baseline.get(k) != after_scene.get(k)}
        if moved - ({pop.get_name()} if changed else set()):
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
        _, rb = _read(actors)
        r['readbackAfterReopen'] = rb
        if not _same(rb, wanted):
            raise RuntimeError('Readback after reopen differs: %r' % rb)
        r['otherMapsAfter'] = {k: sha(v) for k, v in others.items()}
        if r['otherMapsAfter'] != r['otherMapsBefore']:
            raise RuntimeError('Another map changed bytes during the run')
        pa = protected()
        for f in sorted((ROOT / 'Content/MikdashV3/Characters/ResidentV4').rglob('*.uasset')):
            pa[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
        r['protectedChangedExcludingThisMap'] = sorted(k for k in set(pb) | set(pa)
                                                       if pb.get(k) != pa.get(k) and k != this_map)
        if r['protectedChangedExcludingThisMap']:
            raise RuntimeError('Protected assets changed: %r' % r['protectedChangedExcludingThisMap'][:20])
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
    previous = sorted(p for p in OUT.glob('resident-v4-apply-%s-*.json' % key)
                      if json.loads(p.read_text(encoding='utf-8-sig')).get('mapSaved'))
    if not previous:
        raise RuntimeError('No saved apply receipt for %s to revert' % key)
    src = json.loads(previous[-1].read_text(encoding='utf-8-sig'))

    def plan(ue, before):
        old = src['before']
        if before['garmentKeys'] != old['garmentKeys'] or [r['id'] for r in before['bodyVariants']] != [r['id'] for r in old['bodyVariants']]:
            raise RuntimeError('population keys moved since the apply; refuse to revert blind')
        restore = json.loads(json.dumps(before))
        for row, o in zip(restore['bodyVariants'], old['bodyVariants']):
            for f in ('idle', 'walk', 'meshRelativeYaw'):
                if not _same(row[f], o[f]):
                    raise RuntimeError('%s %s moved since the apply' % (row['id'], f))
            row['skeletalMesh'], row['garmentSlots'] = o['skeletalMesh'], o['garmentSlots']
        restore['garmentMaterials'] = old['garmentMaterials']
        return restore
    return _apply(key, 'revert', plan)


def _key(cmd):
    m = re.search(r'-RV4Target=(Main50|Candidate48)', cmd)
    if not m:
        raise RuntimeError('Pass -RV4Target=Main50|Candidate48')
    return m.group(1)


def _main():
    import unreal
    cmd = unreal.SystemLibrary.get_command_line()
    try:
        if '-RV4ImportRevert' in cmd:
            run_import_revert()
        elif '-RV4Import' in cmd:
            run_import()
        elif '-RV4RevertAndReapply' in cmd:
            key = _key(cmd)
            run_revert(key)
            run_apply(key)
        elif '-RV4ApplyAll' in cmd:
            for key in ('Candidate48', 'Main50'):
                run_apply(key)
        elif '-RV4Apply' in cmd:
            run_apply(_key(cmd))
        elif '-RV4Revert' in cmd:
            run_revert(_key(cmd))
        else:
            raise RuntimeError('release_resident_v4: pass a -RV4* mode')
    except Exception:
        receipt_path('failure', 'any', stamp_now()).write_text(
            json.dumps(dict(commandLine=cmd, error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise
    finally:
        if '-executepythonscript' in cmd.lower() and '-run=pythonscript' not in cmd.lower():
            unreal.SystemLibrary.quit_editor()


if __name__ == '__main__':
    _main()

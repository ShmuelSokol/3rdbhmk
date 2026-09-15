"""ShellOpeningsV1 - guarded native import and instancing of the panels behind every shell opening.

Reads SourceAssets/context-review/ShellOpeningsV1/shell-openings-manifest.json and -plan.json
(written by Scripts/create_shell_openings.py, which PROVES its opening list reproduces the shipped
OldCityFacadesV1 shells before writing anything). Writes only inside
/Game/MikdashV3/JerusalemContext/ShellOpeningsV1 and, in the target map, only actors labelled
RELEASE_ShellOpenings_*.

ASSETS
  M_ShellOpeningV1       stock nodes only: PerInstanceRandom -> (R - ShutterShare) * 1000 -> Saturate
                         picks glass or paint; Frac(R * 7.31) and a second Frac pick one of three
                         paints. No Custom node anywhere (EnclosureMath.h 6b: PerInstanceRandom and
                         stock nodes are the safe path). Two-sided (the panels are flat).
                         used_with_instanced_static_meshes set AND read back from disk after reload.
  MI_ShellOpening_Window glass or painted shutter (45 % shutters)
  MI_ShellOpening_Door   painted wooden doors, three colours
  SM_ShellOpening_*      four flat panels (2 or 4 triangles), classic HISM, Nanite OFF, like CityDetail

PLACEMENT
  One HISM actor per (mesh, zone): RELEASE_ShellOpenings_<Kept|Precinct>_<Mesh>. Tags
  ReleaseShellOpeningsV1 plus CityDetailZone_Kept / CityDetailZone_Precinct - the second is already in
  AMikdashEnclosure::HideWhileWallStandsTags, so panels behind the shells the precinct hides are
  hidden with them. No shadows, no collision, cull 525-700 m.

GUARDS (same pattern as release_city_facade.py)
  wrong project / game world / wrong loaded world / dirty packages refuse; manifest, plan and every
  OBJ hash-checked; map checkpoint in ReviewCheckpoints; protected-map hashes before and after;
  save; REOPEN; readback of every actor's mesh, material chain (resolved from disk), instance count,
  last-instance transform and shadow flag; receipt at start and in finally.

MODES
  -ShellOpeningsTarget=candidate|main
  -ShellOpeningsApply        import assets if missing, place the eight actors (refuses if any exist)
  -ShellOpeningsRevert       destroy every RELEASE_ShellOpenings_* actor in the target map
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SCRIPT_TOKEN = 'release_shell_openings.py'
SRC = ROOT / 'SourceAssets' / 'context-review' / 'ShellOpeningsV1'
MANIFEST = SRC / 'shell-openings-manifest.json'
PLAN = SRC / 'shell-openings-plan.json'
OBJ = SRC / 'obj'
NS = '/Game/MikdashV3/JerusalemContext/ShellOpeningsV1'
MESH_FOLDER = NS + '/Meshes'
MAT_FOLDER = NS + '/Materials'
MASTER = MAT_FOLDER + '/M_ShellOpeningV1'
INSTANCES = {
    'window': {'name': 'MI_ShellOpening_Window',
               'vector': {'GlassColor': [0.018, 0.021, 0.026], 'PaintA': [0.08, 0.18, 0.15],
                          'PaintB': [0.10, 0.16, 0.24], 'PaintC': [0.20, 0.12, 0.06]},
               'scalar': {'ShutterShare': 0.55, 'GlassRough': 0.12, 'PaintRough': 0.70}},
    'door': {'name': 'MI_ShellOpening_Door',
             'vector': {'GlassColor': [0.10, 0.06, 0.03], 'PaintA': [0.07, 0.15, 0.10],
                        'PaintB': [0.09, 0.15, 0.25], 'PaintC': [0.18, 0.10, 0.05]},
             'scalar': {'ShutterShare': 0.0, 'GlassRough': 0.60, 'PaintRough': 0.65}},
}
TARGETS = {
    'candidate': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'main': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}
PROTECTED = [
    '/Game/MikdashV3/Maps/Courtyard',
    '/Game/MikdashV3/FutureMountV1/L_FutureMount',
    '/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold',
    '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
    '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
]
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
LABEL_PREFIX = 'RELEASE_ShellOpenings_'
ACTOR_TAG = 'ReleaseShellOpeningsV1'
FOLDER = 'Release/ShellOpenings'
CULL_START_FRACTION = 0.75
TOLERANCE_CM = 0.01
# CityDetail's reviewed OBJ adapter import (release_city_detail.spec.json importSettings), verbatim.
FBX_UI = {'automated_import_should_detect_type': False, 'mesh_type_to_import': 'FBXIT_STATIC_MESH',
          'import_as_skeletal': False, 'import_mesh': True, 'import_animations': False,
          'import_materials': False, 'import_textures': False, 'create_physics_asset': False}
FBX_MESH = {'combine_meshes': True, 'transform_vertex_to_absolute': True, 'bake_pivot_in_vertex': False,
            'convert_scene': False, 'convert_scene_unit': False, 'force_front_x_axis': False,
            'import_uniform_scale': 1.0, 'auto_generate_collision': False, 'build_nanite': False,
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


def load_inputs():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('status') != 'AUTHORED_OFFLINE_SOURCE_NATIVE_IMPORT_PENDING':
        raise RuntimeError('manifest status is %s' % manifest.get('status'))
    if sha256_of(PLAN) != manifest['planSha256']:
        raise RuntimeError('plan hash differs from the manifest')
    for mesh in manifest['meshes']:
        if sha256_of(OBJ / mesh['file']) != mesh['sha256']:
            raise RuntimeError('OBJ hash changed: ' + mesh['file'])
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    total = sum(len(g['rows']) for g in plan['groups'])
    if total != manifest['totals']['instances']:
        raise RuntimeError('plan rows %d != manifest instances %d' % (total, manifest['totals']['instances']))
    return manifest, plan


class Run:
    def __init__(self, ue):
        self.ue = ue
        self.ml = ue.MaterialEditingLibrary
        self.assets = ue.EditorAssetLibrary
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.receipt = None
        self.receipt_path = None
        self.transform_path = None

    def write(self):
        SRC.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(self.receipt, indent=1, default=str), encoding='utf-8')

    # ------------------------------------------------------------ material
    def master(self):
        ue, ml = self.ue, self.ml
        if self.assets.does_asset_exist(MASTER):
            m = self.assets.load_asset(MASTER)
            self.receipt['master'] = {'asset': MASTER, 'created': False}
            return m
        m = ue.AssetToolsHelpers.get_asset_tools().create_asset('M_ShellOpeningV1', MAT_FOLDER, ue.Material, ue.MaterialFactoryNew())
        if not isinstance(m, ue.Material):
            raise RuntimeError('Material factory failed')
        nodes = []

        def node(cls, x, y, **props):
            e = ml.create_material_expression(m, cls, x, y)
            if e is None:
                raise RuntimeError('create_material_expression failed: ' + cls.__name__)
            for k, v in props.items():
                e.set_editor_property(k, v)
            nodes.append(cls.__name__)
            return e

        def wire(src, dst, name=''):
            if not ml.connect_material_expressions(src, '', dst, name):
                raise RuntimeError('connect %s -> %s.%s failed' % (src.get_class().get_name(), dst.get_class().get_name(), name))

        def vec(name, rgb, x, y):
            return node(ue.MaterialExpressionVectorParameter, x, y, parameter_name=name,
                        default_value=ue.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))

        def sca(name, v, x, y):
            return node(ue.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=float(v))

        d = INSTANCES['window']
        r = node(ue.MaterialExpressionPerInstanceRandom, -1400, 0)
        share = sca('ShutterShare', d['scalar']['ShutterShare'], -1400, 120)
        sub = node(ue.MaterialExpressionSubtract, -1200, 60)
        wire(r, sub, 'A')
        wire(share, sub, 'B')
        mul = node(ue.MaterialExpressionMultiply, -1050, 60, const_b=1000.0)
        wire(sub, mul, 'A')
        mask = node(ue.MaterialExpressionSaturate, -900, 60)
        wire(mul, mask)
        m1 = node(ue.MaterialExpressionMultiply, -1200, 240, const_b=7.31)
        wire(r, m1, 'A')
        f1 = node(ue.MaterialExpressionFrac, -1050, 240)
        wire(m1, f1)
        m2 = node(ue.MaterialExpressionMultiply, -1200, 360, const_b=3.7)
        wire(r, m2, 'A')
        f2a = node(ue.MaterialExpressionFrac, -1050, 360)
        wire(m2, f2a)
        s2 = node(ue.MaterialExpressionSubtract, -900, 360, const_b=0.66)
        wire(f2a, s2, 'A')
        m3 = node(ue.MaterialExpressionMultiply, -750, 360, const_b=1000.0)
        wire(s2, m3, 'A')
        f2 = node(ue.MaterialExpressionSaturate, -600, 360)
        wire(m3, f2)
        glass = vec('GlassColor', d['vector']['GlassColor'], -900, -300)
        pa = vec('PaintA', d['vector']['PaintA'], -900, -180)
        pb = vec('PaintB', d['vector']['PaintB'], -900, -60)
        pc = vec('PaintC', d['vector']['PaintC'], -600, -60)
        lab = node(ue.MaterialExpressionLinearInterpolate, -600, -180)
        wire(pa, lab, 'A')
        wire(pb, lab, 'B')
        wire(f1, lab, 'Alpha')
        paint = node(ue.MaterialExpressionLinearInterpolate, -400, -120)
        wire(lab, paint, 'A')
        wire(pc, paint, 'B')
        wire(f2, paint, 'Alpha')
        base = node(ue.MaterialExpressionLinearInterpolate, -200, -200)
        wire(glass, base, 'A')
        wire(paint, base, 'B')
        wire(mask, base, 'Alpha')
        gr = sca('GlassRough', d['scalar']['GlassRough'], -600, 200)
        pr = sca('PaintRough', d['scalar']['PaintRough'], -600, 280)
        rough = node(ue.MaterialExpressionLinearInterpolate, -200, 200)
        wire(gr, rough, 'A')
        wire(pr, rough, 'B')
        wire(mask, rough, 'Alpha')
        metal = node(ue.MaterialExpressionConstant, -200, 360, r=0.0)
        for src, prop in ((base, 'MP_BASE_COLOR'), (rough, 'MP_ROUGHNESS'), (metal, 'MP_METALLIC')):
            if not ml.connect_material_property(src, '', getattr(ue.MaterialProperty, prop)):
                raise RuntimeError('connect_material_property failed: ' + prop)
        m.set_editor_property('two_sided', True)
        try:
            m.set_editor_property('used_with_instanced_static_meshes', True)
        except Exception:                                              # noqa: BLE001
            ml.set_material_usage(m, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        if not m.get_editor_property('used_with_instanced_static_meshes'):
            raise RuntimeError('ISM usage flag did not take')
        ml.recompile_material(m)
        if not self.assets.save_loaded_asset(m, only_if_is_dirty=False):
            raise RuntimeError('save master failed')
        self.receipt['master'] = {'asset': MASTER, 'created': True, 'nodes': nodes,
                                  'customNodes': 0, 'twoSided': True}
        return m

    def instance(self, key, master):
        ue, ml = self.ue, self.ml
        cfg = INSTANCES[key]
        path = MAT_FOLDER + '/' + cfg['name']
        created = False
        if self.assets.does_asset_exist(path):
            mi = self.assets.load_asset(path)
        else:
            mi = ue.AssetToolsHelpers.get_asset_tools().create_asset(cfg['name'], MAT_FOLDER, ue.MaterialInstanceConstant,
                                                                     ue.MaterialInstanceConstantFactoryNew())
            created = True
        ml.set_material_instance_parent(mi, master)
        for name, rgb in cfg['vector'].items():
            ml.set_material_instance_vector_parameter_value(mi, name, ue.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
        for name, v in cfg['scalar'].items():
            ml.set_material_instance_scalar_parameter_value(mi, name, float(v))
        ml.update_material_instance(mi)
        if not self.assets.save_loaded_asset(mi, only_if_is_dirty=False):
            raise RuntimeError('save %s failed' % path)
        self.receipt.setdefault('instances', {})[key] = {'asset': path, 'created': created}
        return mi

    # ------------------------------------------------------------ meshes
    def mesh(self, spec, material):
        ue = self.ue
        path = MESH_FOLDER + '/' + spec['assetName']
        if self.assets.does_asset_exist(path):
            mesh = self.assets.load_asset(path)
            created = False
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
            if len(got) != 1:
                raise RuntimeError('import of %s produced %s' % (spec['file'], [type(o).__name__ for o in task.get_objects()]))
            mesh = got[0]
            created = True
        tris = int(mesh.get_num_triangles(0))
        if tris != spec['triangles']:
            raise RuntimeError('%s has %d triangles, manifest says %d' % (spec['assetName'], tris, spec['triangles']))
        slots = len(mesh.get_editor_property('static_materials'))
        if slots != 1:
            raise RuntimeError('%s has %d material slots' % (spec['assetName'], slots))
        box = mesh.get_bounding_box()
        lo = [box.min.x, box.min.y, box.min.z]
        hi = [box.max.x, box.max.y, box.max.z]
        want = spec['canonicalBoundsCm']
        err = max(max(abs(a - b) for a, b in zip(lo, want['min'])), max(abs(a - b) for a, b in zip(hi, want['max'])))
        if err > 0.05:
            raise RuntimeError('%s bounds %s %s differ from canonical %s by %.3f cm' % (spec['assetName'], lo, hi, want, err))
        mesh.set_material(0, material)
        if _asset_path(mesh.get_material(0)) != _asset_path(material):
            raise RuntimeError('material slot not assigned on ' + spec['assetName'])
        if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError('save mesh failed ' + path)
        self.receipt.setdefault('meshes', {})[spec['key']] = {'asset': path, 'created': created, 'triangles': tris,
                                                              'boundsErrorCm': round(err, 4), 'material': _asset_path(material)}
        return mesh

    # ------------------------------------------------------------ placement
    def new_hism(self, actor):
        ue = self.ue
        subsystem = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
        lib = ue.SubobjectDataBlueprintFunctionLibrary
        handles = subsystem.k2_gather_subobject_data_for_instance(actor)
        parent = next((h for h in handles if lib.get_associated_object(lib.get_data(h)) == actor), None)
        if parent is None:
            raise RuntimeError('actor subobject handle missing')
        params = ue.AddNewSubobjectParams(parent_handle=parent, new_class=ue.HierarchicalInstancedStaticMeshComponent,
                                          blueprint_context=None, conform_transform_to_parent=True)
        handle, reason = subsystem.add_new_subobject(params)
        if not lib.is_handle_valid(handle):
            raise RuntimeError('HISM creation failed: ' + str(reason))
        data = lib.get_data(handle)
        comp = lib.get_associated_object(data)
        if not isinstance(comp, ue.HierarchicalInstancedStaticMeshComponent) or comp.get_owner() != actor \
                or not lib.is_instanced_component(data):
            raise RuntimeError('HISM ownership not verified')
        return comp

    def transform(self, row):
        ue = self.ue
        loc = ue.Vector(row[0], row[1], row[2])
        rot = ue.Rotator(pitch=row[4], yaw=row[3], roll=row[5])
        scale = ue.Vector(row[6], row[7], row[8])
        if self.transform_path is None:
            # UE 5.8 here raises TypeError("'translation' is an invalid keyword argument") for the
            # keyword constructor (first apply, 11 Sep, failed before save). release_city_detail.py
            # already probes inside a try and falls back to set_editor_property; so does this now.
            ok = False
            try:
                probe = ue.Transform(rotation=rot, translation=loc, scale=scale)
                got = probe.get_editor_property('translation')
                ok = abs(got.x - loc.x) < 1e-3 and abs(got.y - loc.y) < 1e-3 and abs(got.z - loc.z) < 1e-3
            except TypeError as error:
                self.receipt['transformKeywordError'] = repr(error)
            self.transform_path = 'keyword' if ok else 'property'
            self.receipt['transformConstruction'] = self.transform_path
        if self.transform_path == 'keyword':
            return ue.Transform(rotation=rot, translation=loc, scale=scale)
        t = ue.Transform()
        t.set_editor_property('translation', loc)
        t.set_editor_property('rotation', rot.quaternion())
        t.set_editor_property('scale3d', scale)
        return t

    def place(self, group, mesh):
        ue = self.ue
        actor = self.actors.spawn_actor_from_class(ue.Actor, ue.Vector(0.0, 0.0, 0.0), ue.Rotator(pitch=0.0, yaw=0.0, roll=0.0))
        if actor is None:
            raise RuntimeError('spawn failed for ' + group['label'])
        actor.set_actor_label(group['label'])
        actor.set_folder_path(FOLDER + '/' + group['zone'].capitalize())
        actor.set_editor_property('tags', [ue.Name(ACTOR_TAG), ue.Name(group['zoneTag'])])
        comp = self.new_hism(actor)
        comp.set_editor_property('static_mesh', mesh)
        comp.set_mobility(ue.ComponentMobility.STATIC)
        comp.set_collision_profile_name('NoCollision')
        comp.set_editor_property('cast_shadow', False)
        cull = float(group['cullDistanceCm'])
        comp.set_cull_distances(int(cull * CULL_START_FRACTION), int(cull))
        transforms = [self.transform(r) for r in group['rows']]
        try:
            comp.add_instances(transforms, False, True, False)
        except TypeError:
            comp.add_instances(transforms, False)
        n = int(comp.get_instance_count())
        if n != group['instances']:
            raise RuntimeError('%s: %d instances placed, plan %d' % (group['label'], n, group['instances']))
        return n

    def ours(self):
        return {a.get_actor_label(): a for a in self.actors.get_all_level_actors()
                if a.get_actor_label().startswith(LABEL_PREFIX)}

    def readback(self, plan):
        """After REOPEN: every pointer resolved from disk, every count and a transform sample."""
        ue = self.ue
        found = self.ours()
        out = []
        for g in plan['groups']:
            a = found.get(g['label'])
            if a is None:
                raise RuntimeError('missing after reopen: ' + g['label'])
            comps = a.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent)
            if len(comps) != 1:
                raise RuntimeError('%s has %d HISMs' % (g['label'], len(comps)))
            c = comps[0]
            mesh = c.get_editor_property('static_mesh')
            if mesh is None:
                raise RuntimeError('%s mesh is null after reopen' % g['label'])
            mat = mesh.get_material(0)
            parent = mat.get_editor_property('parent') if mat is not None and hasattr(mat, 'get_editor_property') else None
            master = self.assets.load_asset(MASTER)
            if mat is None or _asset_path(parent) != MASTER or not master.get_editor_property('used_with_instanced_static_meshes'):
                raise RuntimeError('%s material chain unresolved: %s / %s' % (g['label'], _asset_path(mat), _asset_path(parent)))
            n = int(c.get_instance_count())
            if n != g['instances']:
                raise RuntimeError('%s: %d instances after reopen, plan %d' % (g['label'], n, g['instances']))
            t = c.get_instance_transform(n - 1, True).get_editor_property('translation')
            row = g['rows'][-1]
            err = max(abs(t.x - row[0]), abs(t.y - row[1]), abs(t.z - row[2]))
            if err > TOLERANCE_CM:
                raise RuntimeError('%s last instance moved %.4f cm' % (g['label'], err))
            tags = sorted(str(x) for x in a.get_editor_property('tags'))
            if g['zoneTag'] not in tags or ACTOR_TAG not in tags:
                raise RuntimeError('%s tags %s' % (g['label'], tags))
            out.append({'label': g['label'], 'mesh': _asset_path(mesh), 'material': _asset_path(mat),
                        'instances': n, 'lastInstanceErrorCm': round(err, 5), 'tags': tags,
                        'castShadow': bool(c.get_editor_property('cast_shadow'))})
        return out


def run(target, apply, revert):
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('wrong project')
    manifest, plan = load_inputs()
    r = Run(ue)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    mode = 'revert' if revert else 'apply'
    r.receipt_path = SRC / ('native-shell-openings-%s-%s-%s.json' % (mode, target, stamp))
    r.receipt = {'status': 'started', 'stamp': stamp, 'target': target, 'mode': mode,
                 'scriptSha256': sha256_of(Path(__file__)), 'manifestSha256': sha256_of(MANIFEST),
                 'planSha256': manifest['planSha256'], 'engineVersion': ue.SystemLibrary.get_engine_version(),
                 'errors': [], 'mapSaved': False}
    r.write()
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('a game world is active')
    map_path = TARGETS[target]
    map_file = disk_path(map_path, 'umap')
    protected = {p: sha256_of(disk_path(p, 'umap')) for p in PROTECTED if p != map_path and disk_path(p, 'umap').exists()}
    before = sha256_of(map_file)
    r.receipt.update({'mapSha256Before': before, 'protectedMapSha256Before': protected})
    saved = False
    try:
        if not levels.load_level(map_path):
            raise RuntimeError('load_level failed')
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != map_path:
            raise RuntimeError('loaded world is not the target')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('dirty map packages before mutation')
        existing = r.ours()
        if apply and existing:
            raise RuntimeError('%d RELEASE_ShellOpenings_ actors already exist; revert first' % len(existing))
        checkpoint = CHECKPOINT_ROOT / ('ShellOpenings-%s-%s-%s' % (mode, target, stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != before:
            raise RuntimeError('checkpoint copy hash differs')
        r.receipt['checkpoint'] = str(checkpoint)
        r.receipt['actorCountBefore'] = len(r.actors.get_all_level_actors())
        if revert:
            for label, actor in existing.items():
                r.actors.destroy_actor(actor)
            r.receipt['destroyed'] = sorted(existing)
            if not existing:
                r.receipt['status'] = 'nothing_to_revert_map_unchanged'
                return r.receipt
        else:
            master = r.master()
            mats = {k: r.instance(k, master) for k in INSTANCES}
            meshes = {m['key']: r.mesh(m, mats[m['materialKey']]) for m in manifest['meshes']}
            placed = {}
            for g in plan['groups']:
                placed[g['label']] = r.place(g, meshes[g['mesh']])
                r.write()
            r.receipt['placed'] = placed
            r.receipt['placedTotal'] = sum(placed.values())
        r.write()
        if not ue.EditorLoadingAndSavingUtils.save_map(world, map_path):
            raise RuntimeError('save_map failed')
        saved = True
        r.receipt['mapSaved'] = True
        r.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        r.write()
        if not levels.load_level(map_path):
            raise RuntimeError('reopen failed')
        if revert:
            left = r.ours()
            if left:
                raise RuntimeError('%d actors remain after revert' % len(left))
            r.receipt['status'] = 'shell_openings_reverted_saved_reopened'
        else:
            r.receipt['reopenedReadback'] = r.readback(plan)
            r.receipt['reopenedInstanceTotal'] = sum(x['instances'] for x in r.receipt['reopenedReadback'])
            if r.receipt['reopenedInstanceTotal'] != manifest['totals']['instances']:
                raise RuntimeError('reopened total differs from manifest')
            r.receipt['status'] = 'shell_openings_placed_saved_reopened_read_back_visual_acceptance_pending'
            r.receipt['revertCommand'] = '-ShellOpeningsRevert -ShellOpeningsTarget=%s' % target
        r.receipt['actorCountAfter'] = len(r.actors.get_all_level_actors())
        return r.receipt
    except Exception as error:                                          # noqa: BLE001
        r.receipt['errors'].append(repr(error))
        r.receipt['status'] = 'failed_after_save_checkpoint_available' if saved else 'failed_before_save_map_unchanged'
        raise
    finally:
        r.receipt['mapSha256After'] = sha256_of(map_file)
        r.receipt['mapBytesChanged'] = r.receipt['mapSha256After'] != before
        r.receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(p, 'umap')) == h for p, h in protected.items())
        r.write()


def _main():
    import unreal as ue
    cl = ue.SystemLibrary.get_command_line()
    low = cl.lower()
    target = 'candidate'
    for tok in cl.split():
        if tok.lower().startswith('-shellopeningstarget='):
            target = tok.split('=', 1)[1].strip('"').lower()
    if target not in TARGETS:
        raise RuntimeError('unknown target ' + target)
    revert = '-shellopeningsrevert' in low
    apply = '-shellopeningsapply' in low and not revert
    if not (apply or revert):
        raise RuntimeError('pass -ShellOpeningsApply or -ShellOpeningsRevert')
    try:
        rec = run(target, apply, revert)
        ue.log('release_shell_openings: %s total %s' % (rec['status'], rec.get('reopenedInstanceTotal')))
    except Exception as error:                                          # noqa: BLE001
        ue.log_error('release_shell_openings failed: ' + repr(error))
        raise


try:
    import unreal as _ue                                                # noqa: F401
    if SCRIPT_TOKEN in _ue.SystemLibrary.get_command_line().lower():
        _main()
except ImportError:
    if __name__ == '__main__':
        m, p = load_inputs()
        print(json.dumps({'ok': True, 'groups': len(p['groups']), 'instances': m['totals']['instances']}, indent=1))

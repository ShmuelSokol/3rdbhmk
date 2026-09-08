"""Guarded native import and placement of the Kotel ashlar V2 geometry into the combined map.

Imports the four SourceAssets/kotel-detail/KotelStoneV2/SM_KotelAshlarV2_E*.obj meshes into
/Game/MikdashV3/MaterialReview/KotelStoneV2, builds one limestone PBR material that reuses the
already imported LimestoneAshlar texture set with world-aligned UVs, a per-stone tint decoded
from UV0 (see create_kotel_stone_v2.py) and a per-stone roughness variation, places the meshes
at identity with NoCollision (the base wall keeps its collision), hides the four REVIEW_KotelPhoto_*
panels and verifies the six RELEASE_Kotel_1..6 overlays stay hidden. Every number comes from
Scripts/release_kotel_stone_v2.spec.json.

Commandlet invocation (serial, never while another native job runs; do not use the GUI editor):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_kotel_stone_v2.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-KotelStoneV2-01.log"

Switches: -KotelV2DryRun  audits the map, files and namespace and writes a receipt without mutation.

Safety model (after release_place_assets.py):
  * Refuses the wrong project directory, a game world, dirty packages, a loaded world other than
    the combined map, an existing native namespace, missing/mismatched source files or textures,
    a base wall that is not exactly one component at identity, overlays that are not six and
    hidden, or photo panels that are not four visible planes.
  * Copies Walkthrough.umap (and any OFPA folders) plus every protected asset to
    ReviewCheckpoints/KotelStoneV2-<stamp>/ before any mutation and verifies the copies.
  * Caches the whole-scene actor snapshot once per phase (never per actor); unrelated actors must be
    numerically unchanged before save and after reopen; the previous visibility of every actor this
    script hides is recorded under hiddenForRestore.
  * Saves only after every readback passes, reopens the map and reads everything back again.
  * The receipt SourceAssets/kotel-detail/KotelStoneV2/native-import-<stamp>.json is written at start,
    after save and in finally, preserving partial state on failure.
"""
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_kotel_stone_v2.spec.json'
MAIN = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != MAIN or Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec target/project differs from script constants')
    return spec


def load_manifest(spec):
    path = ROOT / spec['manifest']
    if sha256_of(path) != spec['manifestSha256']:
        raise RuntimeError('Manifest SHA-256 differs from the reviewed spec: ' + str(path))
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if manifest['namespace'] != spec['namespace'] or manifest['status'] != spec['manifestStatusRequired']:
        raise RuntimeError('Manifest namespace/status differ from spec')
    return manifest


def offline_check():
    """Pure file checks (no engine): spec, manifest, OBJ hashes, texture uassets on disk."""
    spec = load_spec()
    manifest = load_manifest(spec)
    folder = ROOT / spec['sourceFolder']
    rows = []
    total = 0
    for mesh in manifest['meshes']:
        path = folder / mesh['file']
        if sha256_of(path) != mesh['sha256']:
            raise RuntimeError('OBJ SHA-256 differs: ' + str(path))
        spec_row = next(m for m in spec['meshes'] if m['name'] == mesh['name'])
        if spec_row['triangles'] != mesh['triangles'] or spec_row['edge'] != mesh['edge'] or box_error(spec_row['boundsCm'], mesh['boundsCm']) > 1e-6:
            raise RuntimeError('Spec mesh row differs from manifest for ' + mesh['name'])
        rows.append({'name': mesh['name'], 'triangles': mesh['triangles'], 'megabytes': round(path.stat().st_size / 1e6, 1)})
        total += mesh['triangles']
    if total != manifest['totalTriangles'] or total >= spec['triangleBudget']:
        raise RuntimeError('Triangle total %d fails budget/manifest check' % total)
    textures = {}
    for kind, row in spec['textures'].items():
        file = disk_path(row['asset'])
        if not file.is_file():
            raise RuntimeError('Texture uasset missing on disk: ' + str(file))
        textures[kind] = {'asset': row['asset'], 'sha256': sha256_of(file)}
    if any(folder.glob('native-import-*.json')) and not spec.get('allowRepeatedReceipts', False):
        existing = sorted(p.name for p in folder.glob('native-import-*.json'))
        rows.append({'existingReceipts': existing})
    tints = manifest['tintsLinear'] + [manifest['mortarTintLinear']]
    if len(tints) != 9 or any(len(t) != 3 for t in tints):
        raise RuntimeError('Expected 8 stone tints plus a mortar tint')
    return {'spec': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'manifestSha256': spec['manifestSha256'],
            'meshes': rows, 'totalTriangles': total, 'textures': textures, 'tints': tints}


# --------------------------------------------------------------------------------------------
# Engine helpers
# --------------------------------------------------------------------------------------------

def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def _pose(actor):
    r = actor.get_actor_rotation()
    return _vec(actor.get_actor_location()) + [float(r.pitch), float(r.yaw), float(r.roll)] + _vec(actor.get_actor_scale3d())


def _bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
            'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}


def _mesh_box(mesh):
    box = mesh.get_bounding_box()
    return {'min': [box.min.x, box.min.y, box.min.z], 'max': [box.max.x, box.max.y, box.max.z]}


def _identity(pose, tolerance):
    return max(abs(v) for v in pose[:6]) <= tolerance and max(abs(v - 1.0) for v in pose[6:]) <= tolerance


def _without_visibility(rows):
    result = json.loads(json.dumps(rows))
    for row in result.values():
        for component in row['components']:
            component.pop('visible', None)
            component.pop('hidden', None)
    return result


class Job:
    def __init__(self, ue, spec, manifest, apply):
        self.ue = ue
        self.spec = spec
        self.manifest = manifest
        self.apply = apply
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.lib = ue.EditorAssetLibrary
        self.stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        folder = ROOT / spec['sourceFolder']
        folder.mkdir(parents=True, exist_ok=True)
        self.receipt_path = folder / ('native-import-%s.json' % self.stamp)
        self.receipt = {'status': 'started', 'apply': apply, 'stamp': self.stamp, 'map': MAIN, 'namespace': spec['namespace'],
                        'specSha256': sha256_of(SPEC_PATH), 'scriptSha256': sha256_of(__file__),
                        'manifestSha256': spec['manifestSha256'], 'engineVersion': ue.SystemLibrary.get_engine_version(),
                        'mapSaved': False, 'errors': [], 'hiddenForRestore': [], 'created': []}

    def write(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    # -- snapshot (whole scene, once per phase) --------------------------------------------------

    def snapshot(self):
        ue = self.ue
        rows = {}
        handles = {}
        for actor in self.actors.get_all_level_actors():
            components = []
            for c in actor.get_components_by_class(ue.StaticMeshComponent):
                components.append({'name': c.get_name(), 'mesh': _asset_path(c.get_editor_property('static_mesh')),
                                   'materials': [_asset_path(c.get_material(i)) for i in range(c.get_num_materials())],
                                   'collision': str(c.get_collision_profile_name()),
                                   'visible': bool(c.get_editor_property('visible')), 'hidden': bool(c.get_editor_property('hidden_in_game'))})
            rows[actor.get_name()] = {'label': actor.get_actor_label(), 'actorClass': actor.get_class().get_path_name(),
                                      'folder': str(actor.get_folder_path()), 'pose': _pose(actor), 'components': components}
            handles[actor.get_name()] = actor
        return rows, handles

    def classify(self, rows):
        """Base wall, six hidden overlays, four visible photo panels; refuse existing V2 actors."""
        spec = self.spec
        base, overlays, panels, v2 = [], [], [], []
        for name, row in rows.items():
            meshes = [c['mesh'] or '' for c in row['components']]
            if spec['baseWall']['mesh'] in meshes:
                base.append(name)
            if any(m.startswith(spec['hide']['overlayMeshPrefix']) for m in meshes):
                overlays.append(name)
            if row['label'].startswith(spec['hide']['photoPanelLabelPrefix']):
                panels.append(name)
            if any(m.startswith(spec['namespace'] + '/') for m in meshes) or row['label'].startswith(spec['actors']['labelPrefix']):
                v2.append(name)
        tol = spec['verification']['transformToleranceCm']
        if len(base) != 1:
            raise RuntimeError('Expected exactly one Kotel base wall actor, found %d' % len(base))
        if not _identity(rows[base[0]]['pose'], tol):
            raise RuntimeError('Kotel base wall is not at identity')
        if len(overlays) != spec['hide']['expectedOverlays']:
            raise RuntimeError('Expected %d procedural overlays, found %d' % (spec['hide']['expectedOverlays'], len(overlays)))
        for name in overlays:
            row = rows[name]
            if not row['label'].startswith('RELEASE_Kotel'):
                raise RuntimeError('Overlay label unexpected: ' + row['label'])
            for c in row['components']:
                if c['visible'] or not c['hidden'] or c['collision'] != 'NoCollision':
                    raise RuntimeError('Overlay %s is not hidden/NoCollision as recorded in the photo adoption' % row['label'])
        if len(panels) != spec['hide']['expectedPanels']:
            raise RuntimeError('Expected %d photo panels, found %d' % (spec['hide']['expectedPanels'], len(panels)))
        if {rows[n]['label'] for n in panels} != set(spec['hide']['photoPanelLabels']):
            raise RuntimeError('Photo panel labels differ from spec: %s' % sorted(rows[n]['label'] for n in panels))
        for name in panels:
            for c in rows[name]['components']:
                if c['mesh'] != spec['hide']['photoPanelMesh'] or c['collision'] != 'NoCollision':
                    raise RuntimeError('Photo panel %s mesh/collision unexpected' % rows[name]['label'])
        if v2:
            raise RuntimeError('KotelStoneV2 actors already present: %s' % [rows[n]['label'] for n in v2])
        return {'base': base[0], 'overlays': sorted(overlays), 'panels': sorted(panels)}

    # -- material ---------------------------------------------------------------------------------

    def build_material(self):
        ue = self.ue
        ml = ue.MaterialEditingLibrary
        spec = self.spec
        cfg = spec['material']
        tools = ue.AssetToolsHelpers.get_asset_tools()
        material = tools.create_asset(cfg['name'], spec['namespace'], ue.Material, ue.MaterialFactoryNew())
        if not isinstance(material, ue.Material):
            raise RuntimeError('Material factory failed')
        material.set_editor_property('tangent_space_normal', False)
        record = {'asset': _asset_path(material), 'nodes': 0, 'connections': [], 'textures': {}}

        def node(cls, x, y, **props):
            e = ml.create_material_expression(material, cls, x, y)
            if e is None:
                raise RuntimeError('create_material_expression failed for ' + cls.__name__)
            for k, v in props.items():
                e.set_editor_property(k, v)
            record['nodes'] += 1
            return e

        def pin(target, wanted):
            names = [str(n) for n in ml.get_material_expression_input_names(target)]
            for n in names:
                if n.lower() == wanted.lower():
                    return n
            if len(names) == 1:
                return names[0]
            raise RuntimeError('%s has no input %r (inputs %s)' % (target.get_class().get_name(), wanted, names))

        def wire(src, out, dst, wanted):
            p = pin(dst, wanted)
            if not ml.connect_material_expressions(src, out, dst, p):
                raise RuntimeError('connect %s.%s -> %s.%s failed' % (src.get_class().get_name(), out, dst.get_class().get_name(), p))
            record['connections'].append('%s.%s -> %s.%s' % (src.get_class().get_name(), out or 'out', dst.get_class().get_name(), p))
            return dst

        def to_property(src, out, prop):
            if not ml.connect_material_property(src, out, getattr(ue.MaterialProperty, prop)):
                raise RuntimeError('connect_material_property -> %s failed' % prop)
            record['connections'].append('%s.%s -> %s' % (src.get_class().get_name(), out or 'out', prop))

        def mask(src, out, x, y, **ch):
            m = node(ue.MaterialExpressionComponentMask, x, y, r=ch.get('r', False), g=ch.get('g', False), b=ch.get('b', False), a=ch.get('a', False))
            return wire(src, out, m, 'Input')

        def binary(cls, a, ao, b, bo, x, y):
            n = node(cls, x, y)
            wire(a, ao, n, 'A')
            wire(b, bo, n, 'B')
            return n

        def scalar(name, x, y):
            return node(ue.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=float(cfg['scalarParameters'][name]))

        def custom(x, y, code, inputs, output_type):
            e = node(ue.MaterialExpressionCustom, x, y)
            rows = []
            for name in inputs:
                ci = ue.CustomInput()
                ci.set_editor_property('input_name', name)
                rows.append(ci)
            e.set_editor_property('inputs', rows)
            e.set_editor_property('output_type', getattr(ue.CustomMaterialOutputType, output_type))
            e.set_editor_property('code', code)
            return e

        def sample(kind, uv, x, y):
            row = spec['textures'][kind]
            tex = ue.load_asset(row['asset'])
            if not isinstance(tex, ue.Texture2D):
                raise RuntimeError('Texture missing: ' + row['asset'])
            srgb = bool(tex.get_editor_property('srgb'))
            compression = str(tex.get_editor_property('compression_settings'))
            record['textures'][kind] = {'asset': row['asset'], 'srgb': srgb, 'compression': compression}
            if kind == 'albedo' and not srgb:
                raise RuntimeError('Albedo texture is not sRGB; sampler type would mismatch')
            if kind != 'albedo' and srgb:
                raise RuntimeError('%s texture is sRGB; sampler type would mismatch' % kind)
            s = node(ue.MaterialExpressionTextureSample, x, y, texture=tex, sampler_type=getattr(ue.MaterialSamplerType, row['samplerType']))
            return wire(uv, '', s, 'UVs')

        t0 = self.manifest_face_tangent()
        stride = float(self.manifest['uvEncoding']['stride'])
        tints = self.manifest['tintsLinear'] + [self.manifest['mortarTintLinear']]
        decode = ('float k = floor(UV.x / %.1f + 0.001); float q = (UV.y < 0.5) ? (1.0 - UV.y) : UV.y; float j = floor(q / %.1f + 0.001); '
                  'k = clamp(k, 0.0, 8.0); j = clamp(j, 0.0, 15.0); ' % (stride, stride))
        # -- world-aligned UV with a per-stone offset so the tile does not continue across joints
        world = node(ue.MaterialExpressionWorldPosition, -2200, -300)
        texcoord = node(ue.MaterialExpressionTextureCoordinate, -2200, 100, coordinate_index=0)
        tiling = scalar('TilingCm', -2200, -100)
        uv = custom(-1900, -200, decode + 'float along = P.x * %.9f + P.y * %.9f; float2 off = float2(k * 0.371 + j * 0.113, j * 0.293 + k * 0.137); '
                    'return float2(along, P.z) / Tiling + off;' % (t0[0], t0[1]), ['UV', 'P', 'Tiling'], 'CMOT_FLOAT2')
        wire(texcoord, '', uv, 'UV')
        wire(world, '', uv, 'P')
        wire(tiling, '', uv, 'Tiling')
        # -- per-stone tint (rgb) and roughness multiplier (a)
        table = ', '.join('float3(%.4f, %.4f, %.4f)' % tuple(t) for t in tints)
        tint = custom(-1900, 300, decode + 'float3 t[9] = {%s}; float jj = j / 15.0; float bright = lerp(%.3f, %.3f, frac(jj * 7.31 + 0.17)); '
                      'float rough = lerp(%.3f, %.3f, jj); return float4(t[(int)k] * bright, rough);'
                      % (table, cfg['brightnessRange'][0], cfg['brightnessRange'][1], cfg['roughnessRange'][0], cfg['roughnessRange'][1]),
                      ['UV'], 'CMOT_FLOAT4')
        wire(texcoord, '', tint, 'UV')
        tint_rgb = mask(tint, '', -1600, 300, r=True, g=True, b=True)
        tint_rough = mask(tint, '', -1600, 420, a=True)
        # -- base colour: tint x luminance detail of the limestone albedo (colour comes from the tints)
        albedo = sample('albedo', uv, -1600, -600)
        desat = node(ue.MaterialExpressionDesaturation, -1400, -600)
        wire(albedo, '', desat, 'None')
        mean = scalar('AlbedoMeanLuminance', -1400, -450)
        detail = binary(ue.MaterialExpressionDivide, desat, '', mean, '', -1200, -600)
        one = node(ue.MaterialExpressionConstant, -1200, -480, r=1.0)
        strength = scalar('DetailStrength', -1200, -400)
        lerp = node(ue.MaterialExpressionLinearInterpolate, -1000, -550)
        wire(one, '', lerp, 'A')
        wire(detail, '', lerp, 'B')
        wire(strength, '', lerp, 'Alpha')
        base_color = binary(ue.MaterialExpressionMultiply, lerp, '', tint_rgb, '', -800, -500)
        to_property(base_color, '', 'MP_BASE_COLOR')
        # -- ARM: R occlusion, G roughness
        arm = sample('arm', uv, -1600, -100)
        rough = mask(arm, '', -1400, -100, g=True)
        rough_scaled = binary(ue.MaterialExpressionMultiply, rough, '', tint_rough, '', -1200, -100)
        rough_out = binary(ue.MaterialExpressionMultiply, rough_scaled, '', scalar('RoughnessScale', -1200, 0), '', -1000, -100)
        to_property(rough_out, '', 'MP_ROUGHNESS')
        if hasattr(ue.MaterialProperty, 'MP_AMBIENT_OCCLUSION'):
            to_property(mask(arm, '', -1400, 20, r=True), '', 'MP_AMBIENT_OCCLUSION')
            record['ambientOcclusionWired'] = True
        # -- normal: tangent-space sample swizzled into world space (u along the face tangent, v up)
        normal = sample('normal', uv, -1600, 600)
        nx = mask(normal, '', -1400, 560, r=True)
        ny = mask(normal, '', -1400, 660, g=True)
        tangent = node(ue.MaterialExpressionConstant2Vector, -1400, 760, r=float(t0[0]), g=float(t0[1]))
        horizontal = binary(ue.MaterialExpressionMultiply, nx, '', tangent, '', -1200, 580)
        deviation = binary(ue.MaterialExpressionAppendVector, horizontal, '', ny, '', -1000, 600)
        scaled = binary(ue.MaterialExpressionMultiply, deviation, '', scalar('NormalStrength', -1000, 720), '', -800, 600)
        vertex_normal = node(ue.MaterialExpressionVertexNormalWS, -800, 480)
        bent = binary(ue.MaterialExpressionAdd, vertex_normal, '', scaled, '', -600, 560)
        normalized = node(ue.MaterialExpressionNormalize, -450, 560)
        wire(bent, '', normalized, 'VectorInput')
        to_property(normalized, '', 'MP_NORMAL')
        messages = [str(m) for m in (ml.recompile_material(material) or [])]
        record['recompileMessages'] = messages
        if any('error' in m.lower() for m in messages):
            raise RuntimeError('Material compile errors: %s' % messages)
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for the material')
        self.receipt['material'] = record
        return material

    def manifest_face_tangent(self):
        face = next(f for f in self.manifest['faces'] if f['edge'] == self.spec['material']['projectionEdge'])
        t = face['tangent']
        if abs(math.hypot(*t) - 1) > 1e-6:
            raise RuntimeError('Projection tangent is not unit length')
        return t

    # -- meshes -----------------------------------------------------------------------------------

    def import_meshes(self, material):
        ue = self.ue
        spec = self.spec
        folder = ROOT / spec['sourceFolder']
        tools = ue.AssetToolsHelpers.get_asset_tools()
        tolerance = spec['verification']['staticBoundsToleranceCm']
        imported = []
        for record in self.manifest['meshes']:
            path = folder / record['file']
            if sha256_of(path) != record['sha256']:
                raise RuntimeError('OBJ SHA-256 differs: ' + record['file'])
            ui = ue.FbxImportUI()
            for k, v in dict(automated_import_should_detect_type=False, mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH, import_as_skeletal=False,
                             import_mesh=True, import_animations=False, import_materials=False, import_textures=False, create_physics_asset=False).items():
                ui.set_editor_property(k, v)
            data = ui.get_editor_property('static_mesh_import_data')
            for k, v in dict(combine_meshes=True, transform_vertex_to_absolute=True, bake_pivot_in_vertex=False, convert_scene=False, convert_scene_unit=False,
                             force_front_x_axis=False, import_uniform_scale=1.0, auto_generate_collision=False, build_nanite=False, generate_lightmap_u_vs=False,
                             remove_degenerates=True, normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():
                data.set_editor_property(k, v)
            task = ue.AssetImportTask()
            for k, v in dict(filename=str(path), destination_path=spec['namespace'] + '/Meshes', destination_name=record['name'], automated=True,
                             replace_existing=False, save=False, options=ui, factory=ue.FbxFactory()).items():
                task.set_editor_property(k, v)
            tools.import_asset_tasks([task])
            objects = list(task.get_objects())
            if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
                raise RuntimeError('Import did not yield one StaticMesh for ' + record['name'])
            mesh = objects[0]
            triangles = mesh.get_num_triangles(0)
            box = _mesh_box(mesh)
            error = box_error(box, record['boundsCm'])
            if triangles != record['triangles']:
                raise RuntimeError('%s imported %d triangles, manifest %d' % (record['name'], triangles, record['triangles']))
            if error > tolerance:
                raise RuntimeError('%s bounds differ from manifest by %.4f cm' % (record['name'], error))
            mesh.set_material(0, material)
            if mesh.get_num_sections(0) != 1:
                raise RuntimeError('%s has %d sections, expected 1' % (record['name'], mesh.get_num_sections(0)))
            if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + record['name'])
            imported.append({'name': record['name'], 'edge': record['edge'], 'asset': _asset_path(mesh), 'mesh': mesh, 'triangles': triangles,
                             'boundsCm': box, 'boundsErrorCm': error, 'uvChannels': (mesh.get_num_uv_channels(0) if hasattr(mesh, 'get_num_uv_channels') else 'unverified_in_5_8_python')})
        self.receipt['imported'] = [{k: v for k, v in row.items() if k != 'mesh'} for row in imported]
        return imported

    # -- placement -----------------------------------------------------------------------------------

    def place(self, imported):
        ue = self.ue
        cfg = self.spec['actors']
        tolerance = self.spec['verification']['staticBoundsToleranceCm']
        created = []
        for row in imported:
            label = cfg['labelPrefix'] + 'E%d' % row['edge']
            actor = self.actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(0, 0, 0), ue.Rotator(pitch=0.0, yaw=0.0, roll=0.0), transient=False)
            if actor is None:
                raise RuntimeError('spawn_actor_from_class returned None for ' + label)
            created.append(actor)
            actor.set_actor_label(label)
            actor.set_folder_path(cfg['folder'])
            actor.set_editor_property('tags', [ue.Name(cfg['tag']), ue.Name(row['name'])])
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            if not component.set_static_mesh(row['mesh']):
                raise RuntimeError('set_static_mesh failed for ' + label)
            component.set_collision_profile_name(cfg['collisionProfile'])
            component.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
            if not actor.get_actor_label() == label or _asset_path(component.get_editor_property('static_mesh')) != row['asset']:
                raise RuntimeError('Readback differs for ' + label)
            bounds = _bounds(actor)
            error = box_error(bounds, row['boundsCm'])
            if error > tolerance:
                raise RuntimeError('%s world bounds differ from mesh bounds at identity by %.4f' % (label, error))
            if str(component.get_collision_profile_name()) != cfg['collisionProfile']:
                raise RuntimeError('Collision profile readback differs for ' + label)
            self.receipt['created'].append({'label': label, 'name': actor.get_name(), 'mesh': row['asset'], 'pose': _pose(actor),
                                            'worldBoundsCm': bounds, 'boundsErrorCm': error, 'collisionProfile': cfg['collisionProfile'],
                                            'material': _asset_path(component.get_material(0))})
        return created

    def hide_panels(self, rows, handles, scoped):
        ue = self.ue
        for name in scoped['panels']:
            actor = handles[name]
            before = rows[name]
            entry = {'name': name, 'label': before['label'], 'components': []}
            for c in actor.get_components_by_class(ue.StaticMeshComponent):
                entry['components'].append({'name': c.get_name(), 'visibleBefore': bool(c.get_editor_property('visible')),
                                            'hiddenInGameBefore': bool(c.get_editor_property('hidden_in_game'))})
                c.set_visibility(False, True)
                c.set_hidden_in_game(True, True)
                if c.get_editor_property('visible') or not c.get_editor_property('hidden_in_game'):
                    raise RuntimeError('Hide readback failed for ' + before['label'])
            self.receipt['hiddenForRestore'].append(entry)
        self.receipt['overlaysKeptHidden'] = [{'name': n, 'label': rows[n]['label']} for n in scoped['overlays']]

    # -- verification ----------------------------------------------------------------------------------

    def verify(self, baseline, scoped, phase):
        rows, handles = self.snapshot()
        created = {c['label']: c for c in self.receipt['created']}
        new_names = {c['name'] for c in self.receipt['created']}
        if set(rows) - set(baseline) != new_names:
            raise RuntimeError('%s: actor set differs from baseline plus the created actors' % phase)
        for name, row in baseline.items():
            if name in scoped['panels']:
                if _without_visibility({name: rows[name]}) != _without_visibility({name: row}):
                    raise RuntimeError('%s: photo panel %s changed beyond visibility' % (phase, row['label']))
                if any(c['visible'] or not c['hidden'] for c in rows[name]['components']):
                    raise RuntimeError('%s: photo panel %s is not hidden' % (phase, row['label']))
            elif rows[name] != row:
                raise RuntimeError('%s: unrelated actor %s changed' % (phase, row['label']))
        for name in scoped['overlays']:
            if any(c['visible'] or not c['hidden'] for c in rows[name]['components']):
                raise RuntimeError('%s: overlay %s became visible' % (phase, rows[name]['label']))
        if rows[scoped['base']] != baseline[scoped['base']]:
            raise RuntimeError('%s: base wall state changed' % phase)
        tol = self.spec['verification']
        readback = []
        for label, planned in created.items():
            matching = [n for n, r in rows.items() if r['label'] == label]
            if len(matching) != 1:
                raise RuntimeError('%s: %d actors labelled %s' % (phase, len(matching), label))
            row = rows[matching[0]]
            if not _identity(row['pose'], tol['transformToleranceCm']):
                raise RuntimeError('%s: %s is not at identity' % (phase, label))
            if [c['mesh'] for c in row['components']] != [planned['mesh']]:
                raise RuntimeError('%s: %s mesh differs' % (phase, label))
            c = row['components'][0]
            if c['materials'] != [planned['material']] or c['collision'] != planned['collisionProfile'] or not c['visible'] or c['hidden']:
                raise RuntimeError('%s: %s material/collision/visibility differ' % (phase, label))
            bounds = _bounds(handles[matching[0]])
            error = box_error(bounds, planned['worldBoundsCm'])
            if error > tol['staticBoundsToleranceCm']:
                raise RuntimeError('%s: %s bounds differ by %.4f' % (phase, label, error))
            readback.append({'label': label, 'name': matching[0], 'folder': row['folder'], 'mesh': c['mesh'], 'material': c['materials'][0],
                             'collision': c['collision'], 'worldBoundsCm': bounds, 'boundsErrorCm': error})
        self.receipt[phase] = {'readback': readback, 'actorCount': len(rows)}


def run(apply=True, load_target=True):
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory')
    spec = load_spec()
    manifest = load_manifest(spec)
    offline = offline_check()
    job = Job(ue, spec, manifest, apply)
    job.receipt['offlineCheck'] = offline
    if load_target:
        if not job.levels.load_level(MAIN):
            raise RuntimeError('load_level failed for ' + MAIN)
    if job.editor.get_game_world():
        raise RuntimeError('A game world is active')
    if job.editor.get_editor_world().get_outermost().get_name() != MAIN:
        raise RuntimeError('Loaded world is not the combined map')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present')
    if job.lib.does_directory_exist(spec['namespace']):
        raise RuntimeError('Native namespace already exists; never rerun a creator into an existing folder: ' + spec['namespace'])
    for kind, row in spec['textures'].items():
        if not job.lib.does_asset_exist(row['asset']):
            raise RuntimeError('Texture asset missing: ' + row['asset'])
    baseline, handles = job.snapshot()
    scoped = job.classify(baseline)
    job.receipt['scoped'] = {'base': {'name': scoped['base'], 'label': baseline[scoped['base']]['label']},
                             'overlays': [baseline[n]['label'] for n in scoped['overlays']],
                             'panels': [baseline[n]['label'] for n in scoped['panels']], 'actorCount': len(baseline)}
    map_file = disk_path(MAIN, 'umap')
    protected = [map_file, disk_path(spec['baseWall']['mesh'])]
    protected += [disk_path(p, 'umap') for p in spec['protectedMaps']]
    for folder in spec['protectedAssetFolders']:
        protected += sorted((ROOT / 'Content' / folder[6:]).rglob('*.uasset'))
    protected += [ROOT / spec['manifest']] + [ROOT / spec['sourceFolder'] / m['file'] for m in manifest['meshes']]
    protected += [disk_path(row['asset']) for row in spec['textures'].values()]
    before = {str(p): sha256_of(p) for p in protected}
    job.receipt['mapSha256Before'] = before[str(map_file)]
    job.receipt['protectedSha256Before'] = before
    job.write()
    if not apply:
        job.receipt['status'] = 'dry_run_no_mutation'
        job.write()
        return job.receipt
    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + job.stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    for p in protected:
        target = checkpoint / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        if sha256_of(target) != before[str(p)]:
            raise RuntimeError('Checkpoint copy differs: ' + str(p))
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / MAIN[6:]
        if external.exists():
            shutil.copytree(external, checkpoint / 'Content' / folder_name / MAIN[6:])
    job.receipt['checkpoint'] = str(checkpoint)
    job.receipt['status'] = 'checkpointed_import_started'
    job.write()
    created = []
    try:
        material = job.build_material()
        imported = job.import_meshes(material)
        created = job.place(imported)
        job.hide_panels(baseline, handles, scoped)
        job.verify(baseline, scoped, 'verifiedBeforeSave')
        if not job.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        job.receipt['mapSaved'] = True
        job.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        job.receipt['status'] = 'saved_reopen_pending'
        job.write()
        if not job.levels.load_level(MAIN) or job.editor.get_editor_world().get_outermost().get_name() != MAIN:
            raise RuntimeError('Reopen failed')
        job.verify(baseline, scoped, 'verifiedAfterReopen')
        job.receipt['status'] = 'kotel_stone_v2_saved_reopened_visual_acceptance_pending'
        job.receipt['restore'] = {'howTo': 'Copy the checkpoint Walkthrough.umap back, or delete the RELEASE_KotelStoneV2_* actors and set '
                                            'visible=True / hidden_in_game=False on every hiddenForRestore component; the native namespace may then be deleted.',
                                  'checkpointMap': str(checkpoint / map_file.relative_to(ROOT))}
        return job.receipt
    except Exception as error:
        job.receipt['errors'].append(repr(error))
        if not job.receipt['mapSaved']:
            for actor in created:
                try:
                    job.actors.destroy_actor(actor)
                except Exception as cleanup:
                    job.receipt.setdefault('cleanupErrors', []).append(repr(cleanup))
            job.receipt['status'] = 'failed_before_save_map_unchanged_native_assets_preserved'
        else:
            job.receipt['status'] = 'failed_after_save_checkpoint_available'
        raise
    finally:
        after = {str(p): sha256_of(p) for p in protected}
        job.receipt['mapSha256After'] = after[str(map_file)]
        job.receipt['mapBytesChanged'] = after[str(map_file)] != before[str(map_file)]
        unchanged = {k: v for k, v in before.items() if k != str(map_file)}
        job.receipt['protectedUnchanged'] = all(after[k] == v for k, v in unchanged.items())
        if not job.receipt['protectedUnchanged']:
            job.receipt['status'] = 'failed_protected_hash_guard'
            job.receipt['protectedChanged'] = [k for k, v in unchanged.items() if after[k] != v]
        job.write()
        if not job.receipt['protectedUnchanged']:
            raise RuntimeError('Protected file hash changed: %s' % job.receipt['protectedChanged'])


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
    return 'release_kotel_stone_v2.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    apply = '-kotelv2dryrun' not in command_line
    try:
        receipt = run(apply=apply, load_target=True)
        ue.log('release_kotel_stone_v2: %s created %d hidden %d' % (receipt['status'], len(receipt['created']), len(receipt['hiddenForRestore'])))
    except Exception as error:
        ue.log_error('release_kotel_stone_v2 failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

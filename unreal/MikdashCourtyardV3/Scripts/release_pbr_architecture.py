"""Textured PBR materials for the measured Temple architecture (commandlet-safe).

Stages (all guarded, checkpointed, receipted):
  1. Import the CC0 Poly Haven texture sets from SourceAssets/materials-pbr/<slug>/ into
     /Game/MikdashV3/Materials/PBR/<Folder>/ (albedo sRGB, normal TC_Normalmap, ARM TC_Masks, height TC_Grayscale).
  2. Build the master material M_PBR_Tiled (explicit world-position triplanar projection, world-space normal
     output because the imported FBX has no UVs) and one MaterialInstanceConstant per stone kind.
  3. In the combined Walkthrough map, replace the flat M_Canonical_* materials on the 'Measured architecture/*'
     components with the instances at the COMPONENT OVERRIDE level (see spec applyLevelJustification), save,
     reopen, read back, and write SourceAssets/materials-pbr/native-apply-<stamp>.json.

Switches (parsed from the engine command line):
  -PbrImportOnly    stages 1-2 only, map untouched (existing namespace assets reused, missing ones created).
  -PbrApply         stage 3, reusing the saved textures/master/instances (missing ones are created, nothing overwritten).
  -PbrIncludeGold   also remap gold / goldPaving (default keeps the canonical gold colours).
  -PbrDryRun        plan the reassignment, write the receipt, change nothing.
  (no switch)       stages 1-3 in one run.

Run without the engine to get the offline consistency check (spec, provenance hashes, mapping table):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\ThirdParty\\Python3\\Win64\\python.exe" Scripts\\release_pbr_architecture.py

Commandlet:
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe" C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject
      -run=pythonscript -script=C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_pbr_architecture.py
      -unattended -nullrhi -abslog=C:/Mikdash/Working-5.8/Release-PBR-01.log -PbrImportOnly
"""
import hashlib
import importlib.util
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_pbr_architecture.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
IMPORT_KINDS = ('albedo', 'normal', 'arm', 'height')


# --------------------------------------------------------------------------
# Offline helpers (no engine)
# --------------------------------------------------------------------------

def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec projectDir differs from ROOT')
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec targetMap differs from TARGET')
    return spec


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError(asset_path)
    return ROOT / 'Content' / (asset_path[len('/Game/'):] + '.' + extension)


def _load_module(relative, name, required):
    path = ROOT / relative
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    for attr in required:
        if not hasattr(module, attr):
            raise RuntimeError('%s lacks helper %s' % (relative, attr))
    return module


def load_placement_helper(spec):
    return _load_module(spec['placementHelper'], 'release_place_assets', ('Placement', '_asset_path', 'sha256_of'))


def image_header(path):
    data = open(path, 'rb').read(64)
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if data[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if data[:4] == b'\x76\x2f\x31\x01':
        return 'exr'
    raise RuntimeError('Unrecognised image header in %s' % path)


def load_provenance(spec, slug):
    folder = ROOT / spec['sourceRoot'] / slug
    prov = json.loads((folder / 'provenance.json').read_text(encoding='utf-8'))
    if prov['license'] != 'CC0 1.0' or prov['assetId'] != spec['sets'][slug]['assetId']:
        raise RuntimeError('Provenance mismatch for ' + slug)
    files = {}
    for kind in IMPORT_KINDS:
        entry = prov['maps'][kind]
        path = folder / entry['file']
        if not path.exists():
            raise RuntimeError('Missing texture file ' + str(path))
        if sha256_of(path) != entry['sha256']:
            raise RuntimeError('SHA-256 mismatch for ' + str(path))
        if image_header(path) != entry['format']:
            raise RuntimeError('Header/format mismatch for ' + str(path))
        files[kind] = {'path': path, 'sha256': entry['sha256'], 'width': entry['width'], 'height': entry['height'], 'format': entry['format']}
    return prov, files


def load_canonical_index(spec):
    """assetName -> {profileKey, sourceName, canonicalMaterial}; plus the canonical material name -> key map."""
    review = json.loads((ROOT / spec['canonicalReview']).read_text(encoding='utf-8-sig'))
    index = {}
    for change in review['componentChanges']:
        index[change['assetName']] = {'profileKey': change['targetProfileKey'], 'sourceName': change['sourceName'],
                                      'canonicalMaterial': change['newMaterial'].split('.')[0]}
    for held in review.get('heldSlots', []):
        index[held['assetName']] = {'profileKey': held['targetProfileKey'], 'sourceName': held['sourceName'], 'canonicalMaterial': None}
    canonical_names = {}
    for key, entry in review['nativeMaterials'].items():
        canonical_names[entry['path'].split('.')[0].split('/')[-1]] = key
    return index, canonical_names, review


def load_manifest_index(spec):
    manifest = json.loads((ROOT / spec['architectureManifest']).read_text(encoding='utf-8-sig'))
    index = {}
    uv_layers = 0
    for mesh in manifest['meshes']:
        index[mesh['assetName']] = {'sourcePart': mesh['sourcePart'], 'sourceName': mesh['sourceName'], 'semantic': mesh['semantic'],
                                    'slotKeys': [slot['sourceMaterialKey'] for slot in mesh['materialSlots']]}
        uv_layers += 1 if mesh.get('uvLayers') else 0
    return index, {'meshCount': manifest['meshCount'], 'meshesWithUvLayers': uv_layers, 'sourceModelSha256': manifest['sourceModelSha256']}


def resolve_instance(spec, profile_key, source_name, include_gold):
    """Return (instance name or None, reason)."""
    lowered = (source_name or '').lower()
    for rule in spec['sourceNameOverrides']:
        if 'contains' in rule and rule['contains'].lower() in lowered:
            return rule['instance'], 'name override: ' + rule['reason']
        if 'equals' in rule and source_name in rule['equals']:
            return rule['instance'], 'name override: ' + rule['reason']
    if profile_key in spec['profileMapping']:
        return spec['profileMapping'][profile_key], 'profile ' + profile_key
    if profile_key in spec['goldProfileMapping']:
        if include_gold:
            return spec['goldProfileMapping'][profile_key], 'gold profile ' + profile_key + ' (-PbrIncludeGold)'
        return None, 'gold kept canonical (no -PbrIncludeGold)'
    if profile_key in spec['untouchedProfiles']:
        return None, 'untouched profile ' + profile_key
    return None, 'unknown profile ' + str(profile_key)


def plan_table(spec, include_gold):
    """Offline mapping table from the canonical receipt: instance -> component count, and untouched counts."""
    canonical, _, _ = load_canonical_index(spec)
    counts = Counter()
    reasons = defaultdict(Counter)
    for asset_name, entry in canonical.items():
        instance, reason = resolve_instance(spec, entry['profileKey'], entry['sourceName'], include_gold)
        counts[instance or 'UNCHANGED'] += 1
        reasons[instance or 'UNCHANGED'][reason] += 1
    return {'counts': dict(counts), 'reasons': {k: dict(v) for k, v in reasons.items()}}


def offline_check(spec=None):
    spec = spec or load_spec()
    report = {'spec': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'sets': {}, 'instances': {}, 'errors': []}
    total = 0
    for slug, cfg in spec['sets'].items():
        try:
            prov, files = load_provenance(spec, slug)
            size = sum((ROOT / spec['sourceRoot'] / slug / m['file']).stat().st_size for m in prov['maps'].values() if 'file' in m)
            total += size
            report['sets'][slug] = {'assetId': prov['assetId'], 'resolution': prov['resolution'], 'physicalSizeMm': prov['physicalSizeMm'],
                                    'tilingCm': cfg['tilingCm'], 'megabytes': round(size / 1e6, 1), 'license': prov['license'],
                                    'imported': {k: f['path'].name for k, f in files.items()}}
        except Exception as error:
            report['errors'].append({'set': slug, 'error': repr(error)})
    report['totalMegabytes'] = round(total / 1e6, 1)
    for name, inst in spec['instances'].items():
        if inst['set'] not in spec['sets']:
            report['errors'].append({'instance': name, 'error': 'unknown set ' + inst['set']})
        unknown = set(inst['scalars']) - set(spec['masterMaterial']['scalarParameters'])
        if unknown:
            report['errors'].append({'instance': name, 'error': 'unknown scalar parameters %s' % sorted(unknown)})
        report['instances'][name] = inst['set']
    for mapping in ('profileMapping', 'goldProfileMapping'):
        for key, instance in spec[mapping].items():
            if instance not in spec['instances']:
                report['errors'].append({'mapping': key, 'error': 'unknown instance ' + instance})
    for rule in spec['sourceNameOverrides']:
        if rule['instance'] not in spec['instances']:
            report['errors'].append({'override': rule, 'error': 'unknown instance'})
    canonical, canonical_names, review = load_canonical_index(spec)
    known = set(spec['profileMapping']) | set(spec['goldProfileMapping']) | set(spec['untouchedProfiles'])
    profile_keys = {entry['profileKey'] for entry in canonical.values()}
    if profile_keys - known:
        report['errors'].append({'profiles': sorted(profile_keys - known), 'error': 'profile keys without a mapping decision'})
    report['canonicalReview'] = {'componentChanges': len(review['componentChanges']), 'appliedSlotCount': review['appliedSlotCount'],
                                 'sha256': sha256_of(ROOT / spec['canonicalReview']), 'profileKeys': sorted(profile_keys)}
    _, manifest_info = load_manifest_index(spec)
    report['architectureManifest'] = manifest_info
    if manifest_info['meshesWithUvLayers'] != 0:
        report['errors'].append({'manifest': 'meshesWithUvLayers', 'error': 'some meshes carry UVs; world projection still applies but recheck the note'})
    report['planDefault'] = plan_table(spec, include_gold=False)
    report['planWithGold'] = plan_table(spec, include_gold=True)
    report['passed'] = not report['errors']
    return report


# --------------------------------------------------------------------------
# Engine side: textures, master material, instances
# --------------------------------------------------------------------------

def _enum(ue, enum_name, *candidates):
    enum = getattr(ue, enum_name)
    for name in candidates:
        if name and hasattr(enum, name):
            return getattr(enum, name), name
    raise RuntimeError('%s has none of %s' % (enum_name, candidates))


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def texture_asset_name(spec, slug, kind):
    return 'T_' + spec['sets'][slug]['folderName'] + spec['textures'][kind]['suffix']


def texture_folder(spec, slug):
    return spec['nativeRoot'] + '/' + spec['sets'][slug]['folderName']


def import_texture(ue, spec, slug, kind, file_info, receipt):
    tex_spec = spec['textures'][kind]
    folder = texture_folder(spec, slug)
    name = texture_asset_name(spec, slug, kind)
    task = ue.AssetImportTask()
    for key, value in dict(filename=str(file_info['path']), destination_path=folder, destination_name=name, automated=True,
                           replace_existing=False, save=False).items():
        task.set_editor_property(key, value)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.Texture2D):
        raise RuntimeError('Texture import of %s produced %s' % (file_info['path'], [type(o).__name__ for o in objects]))
    tex = objects[0]
    compression, compression_name = _enum(ue, 'TextureCompressionSettings', tex_spec['compression'], tex_spec.get('compressionFallback'))
    tex.set_editor_property('compression_settings', compression)
    tex.set_editor_property('srgb', bool(tex_spec['srgb']))
    if kind == 'normal':
        tex.set_editor_property('flip_green_channel', bool(tex_spec['flipGreenChannel']))
    virtual_texture = None
    try:
        tex.set_editor_property('virtual_texture_streaming', False)  # keep 4K maps on the regular sampler path (SAMPLERTYPE_*)
        virtual_texture = bool(tex.get_editor_property('virtual_texture_streaming'))
    except Exception as error:
        virtual_texture = 'property unavailable: %r' % (error,)
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(tex, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + name)
    size = None
    for getter in ('blueprint_get_size_x', 'get_size_x'):
        if hasattr(tex, getter):
            try:
                size = [int(getattr(tex, getter)()), int(getattr(tex, getter.replace('_x', '_y'))())]
            except Exception:
                size = None
            break
    info = {'asset': _asset_path(tex), 'source': str(file_info['path']), 'sourceSha256': file_info['sha256'], 'sourceSize': [file_info['width'], file_info['height']],
            'compression': compression_name, 'srgb': bool(tex.get_editor_property('srgb')), 'importedSize': size, 'virtualTextureStreaming': virtual_texture,
            'uassetSha256': sha256_of(disk_path(_asset_path(tex)))}
    if kind == 'normal':
        info['flipGreenChannel'] = bool(tex.get_editor_property('flip_green_channel'))
    receipt['textures'].setdefault(slug, {})[kind] = info
    return tex


def build_master_material(ue, spec, sample_textures, receipt):
    """Explicit triplanar master. sample_textures: {kind: Texture2D} used as parameter defaults."""
    cfg = spec['masterMaterial']
    ml = ue.MaterialEditingLibrary
    folder = spec['nativeRoot']
    path = folder + '/' + cfg['name']
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    record = {'asset': path, 'nodes': [], 'connections': [], 'status': 'started'}
    receipt['masterMaterial'] = record
    material = tools.create_asset(cfg['name'], folder, ue.Material, ue.MaterialFactoryNew())
    if not isinstance(material, ue.Material):
        raise RuntimeError('Material factory failed for ' + path)
    material.set_editor_property('tangent_space_normal', bool(cfg['tangentSpaceNormal']))

    def node(cls, x, y, **props):
        expression = ml.create_material_expression(material, cls, x, y)
        if expression is None:
            raise RuntimeError('create_material_expression failed for %s' % cls.__name__)
        for key, value in props.items():
            expression.set_editor_property(key, value)
        record['nodes'].append({'class': cls.__name__, 'position': [x, y],
                                'properties': {k: (v if isinstance(v, (int, float, bool, str)) else str(v)) for k, v in props.items()}})
        return expression

    def input_name(expression, wanted):
        names = [str(n) for n in ml.get_material_expression_input_names(expression)]
        for candidate in names:
            if candidate.lower() == wanted.lower():
                return candidate
        if len(names) == 1:
            return names[0]
        raise RuntimeError('%s has no input %r (inputs %s)' % (expression.get_class().get_name(), wanted, names))

    def wire(source, output, target, wanted):
        pin = input_name(target, wanted)
        if not ml.connect_material_expressions(source, output, target, pin):
            raise RuntimeError('Connection %s[%r] -> %s[%r] failed; outputs=%s' % (
                source.get_class().get_name(), output, target.get_class().get_name(), pin, [str(n) for n in ml.get_material_expression_output_names(source)]))
        record['connections'].append('%s.%s -> %s.%s' % (source.get_class().get_name(), output or 'out', target.get_class().get_name(), pin))
        return target

    def to_property(source, output, prop_name):
        prop = getattr(ue.MaterialProperty, prop_name)
        if not ml.connect_material_property(source, output, prop):
            raise RuntimeError('connect_material_property %s -> %s failed' % (source.get_class().get_name(), prop_name))
        record['connections'].append('%s.%s -> %s' % (source.get_class().get_name(), output or 'out', prop_name))

    def scalar(name, x, y):
        return node(ue.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=float(cfg['scalarParameters'][name]))

    def mask(source, output, x, y, r=False, g=False, b=False, a=False):
        m = node(ue.MaterialExpressionComponentMask, x, y, r=r, g=g, b=b, a=a)
        return wire(source, output, m, 'Input')

    def binary(cls, a, a_out, b, b_out, x, y, **props):
        n = node(cls, x, y, **props)
        wire(a, a_out, n, 'A')
        wire(b, b_out, n, 'B')
        return n

    # -- world UVs -------------------------------------------------------------------------
    world_position = node(ue.MaterialExpressionWorldPosition, -2600, -400)
    tiling = scalar('TilingCm', -2600, -250)
    world_uv = binary(ue.MaterialExpressionDivide, world_position, '', tiling, '', -2400, -350)
    uv_z = mask(world_uv, '', -2200, -500, r=True, g=True)   # xy plane, projection along Z (floors, ceilings)
    uv_y = mask(world_uv, '', -2200, -350, r=True, b=True)   # xz plane, projection along Y
    uv_x = mask(world_uv, '', -2200, -200, g=True, b=True)   # yz plane, projection along X

    # -- blend weights: normalize(pow(abs(N), k)) --------------------------------------
    vertex_normal = node(ue.MaterialExpressionVertexNormalWS, -2600, 200)
    absolute = wire(vertex_normal, '', node(ue.MaterialExpressionAbs, -2450, 200), 'Input')
    powered = wire(absolute, '', node(ue.MaterialExpressionPower, -2300, 200, const_exponent=float(cfg['blendExponent'])), 'Base')
    ones = node(ue.MaterialExpressionConstant3Vector, -2300, 330, constant=ue.LinearColor(1.0, 1.0, 1.0, 1.0))
    weight_sum = binary(ue.MaterialExpressionDotProduct, powered, '', ones, '', -2150, 250)
    weights = binary(ue.MaterialExpressionDivide, powered, '', weight_sum, '', -2000, 200)
    w_x = mask(weights, '', -1850, 120, r=True)
    w_y = mask(weights, '', -1850, 200, g=True)
    w_z = mask(weights, '', -1850, 280, b=True)

    def sampler(kind, uv, x, y):
        sampler_type, _ = _enum(ue, 'MaterialSamplerType', spec['textures'][kind]['samplerType'])
        s = node(ue.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=cfg['textureParameters'][kind],
                 texture=sample_textures[kind], sampler_type=sampler_type)
        return wire(uv, '', s, 'UVs')

    def blend3(parts, x, y):
        """parts: [(expression, output)] for the X, Y, Z planes -> weighted sum."""
        (px, ox), (py, oy), (pz, oz) = parts
        mx = binary(ue.MaterialExpressionMultiply, px, ox, w_x, '', x, y - 80)
        my = binary(ue.MaterialExpressionMultiply, py, oy, w_y, '', x, y)
        mz = binary(ue.MaterialExpressionMultiply, pz, oz, w_z, '', x, y + 80)
        first = binary(ue.MaterialExpressionAdd, mx, '', my, '', x + 150, y - 40)
        return binary(ue.MaterialExpressionAdd, first, '', mz, '', x + 300, y)

    # -- albedo --------------------------------------------------------------------------------
    albedo_samples = [sampler('albedo', uv, -1600, y) for uv, y in ((uv_x, -1000), (uv_y, -800), (uv_z, -600))]
    albedo = blend3([(s, '') for s in albedo_samples], -1300, -800)
    flatness = scalar('AlbedoFlatness', -1000, -650)
    flat = node(ue.MaterialExpressionLinearInterpolate, -850, -800, const_b=1.0)
    wire(albedo, '', flat, 'A')
    wire(flatness, '', flat, 'Alpha')
    tint = node(ue.MaterialExpressionVectorParameter, -850, -600, parameter_name='Tint', default_value=ue.LinearColor(*cfg['vectorParameters']['Tint']))
    base_color = binary(ue.MaterialExpressionMultiply, flat, '', tint, '', -650, -750)
    to_property(base_color, '', 'MP_BASE_COLOR')

    # -- ARM: R ambient occlusion, G roughness, B metallic (metallic comes from a parameter) ------
    arm_samples = [sampler('arm', uv, -1600, y) for uv, y in ((uv_x, -300), (uv_y, -100), (uv_z, 100))]
    arm = blend3([(s, '') for s in arm_samples], -1300, -100)
    ao = mask(arm, '', -850, -180, r=True)
    rough_raw = mask(arm, '', -850, -60, g=True)
    rough_scale = scalar('RoughnessScale', -850, 40)
    roughness = binary(ue.MaterialExpressionMultiply, rough_raw, '', rough_scale, '', -650, -60)
    to_property(roughness, '', 'MP_ROUGHNESS')
    metallic = scalar('Metallic', -650, 120)
    to_property(metallic, '', 'MP_METALLIC')
    record['ambientOcclusionWired'] = False
    if hasattr(ue.MaterialProperty, 'MP_AMBIENT_OCCLUSION'):
        to_property(ao, '', 'MP_AMBIENT_OCCLUSION')
        record['ambientOcclusionWired'] = True

    # -- normal: per-plane tangent deviations swizzled into world axes, blended, added to N ------
    normal_samples = [sampler('normal', uv, -1600, y) for uv, y in ((uv_x, 400), (uv_y, 600), (uv_z, 800))]
    zero = node(ue.MaterialExpressionConstant, -1450, 900, r=0.0)
    n_x, n_y, n_z = normal_samples
    # X plane (uv = world yz): tangent Y, bitangent Z -> (0, nx, ny)
    dev_x = binary(ue.MaterialExpressionAppendVector, zero, '', mask(n_x, '', -1450, 380, r=True, g=True), '', -1300, 400)
    # Y plane (uv = world xz): tangent X, bitangent Z -> (nx, 0, ny)
    y_r = mask(n_y, '', -1450, 560, r=True)
    y_g = mask(n_y, '', -1450, 640, g=True)
    dev_y = binary(ue.MaterialExpressionAppendVector, binary(ue.MaterialExpressionAppendVector, y_r, '', zero, '', -1350, 600), '', y_g, '', -1250, 600)
    # Z plane (uv = world xy): tangent X, bitangent Y -> (nx, ny, 0)
    dev_z = binary(ue.MaterialExpressionAppendVector, mask(n_z, '', -1450, 780, r=True, g=True), '', zero, '', -1300, 800)
    deviation = blend3([(dev_x, ''), (dev_y, ''), (dev_z, '')], -1000, 600)
    strength = scalar('NormalStrength', -700, 750)
    scaled = binary(ue.MaterialExpressionMultiply, deviation, '', strength, '', -550, 600)
    bent = binary(ue.MaterialExpressionAdd, vertex_normal, '', scaled, '', -400, 550)
    normal_out = wire(bent, '', node(ue.MaterialExpressionNormalize, -250, 550), 'VectorInput')
    to_property(normal_out, '', 'MP_NORMAL')

    errors = list(ml.recompile_material(material))
    record['recompileMessages'] = [str(e) for e in errors]
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + path)
    record['nodeCount'] = len(record['nodes'])
    record['inputsWired'] = {}
    for prop_name in ('MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_AMBIENT_OCCLUSION'):
        if hasattr(ue.MaterialProperty, prop_name):
            wired = ml.get_material_property_input_node(material, getattr(ue.MaterialProperty, prop_name))
            record['inputsWired'][prop_name] = wired.get_class().get_name() if wired else None
    record['tangentSpaceNormal'] = bool(material.get_editor_property('tangent_space_normal'))
    # Out-params are returned in Python (build_atmosphere_pilot.py uses the same one-argument form).
    record['scalarParameters'] = sorted(str(n) for n in ml.get_scalar_parameter_names(material))
    record['textureParameters'] = sorted(str(n) for n in ml.get_texture_parameter_names(material))
    missing = set(cfg['scalarParameters']) - set(record['scalarParameters'])
    if missing:
        raise RuntimeError('Master material lacks scalar parameters %s' % sorted(missing))
    missing = set(cfg['textureParameters'].values()) - set(record['textureParameters'])
    if missing:
        raise RuntimeError('Master material lacks texture parameters %s' % sorted(missing))
    record['uassetSha256'] = sha256_of(disk_path(path))
    record['status'] = 'saved'
    return material


def _set_instance_parameter(ue, ml, instance, kind, parameter, value, record):
    """Set one MIC parameter and VERIFY BY READBACK.

    In 5.8 MaterialEditingLibrary.set_material_instance_{scalar,vector,texture}_parameter_value apply the value but
    always return False (bResult is never set in MaterialEditingLibrary.cpp), so the bool is ignored. If the readback
    still differs, fall back to the *_parameter_values struct arrays and record which path worked.
    """
    getters = {'texture': ml.get_material_instance_texture_parameter_value, 'scalar': ml.get_material_instance_scalar_parameter_value,
               'vector': ml.get_material_instance_vector_parameter_value}
    setters = {'texture': ml.set_material_instance_texture_parameter_value, 'scalar': ml.set_material_instance_scalar_parameter_value,
               'vector': ml.set_material_instance_vector_parameter_value}

    def matches():
        got = getters[kind](instance, parameter)
        if kind == 'texture':
            return _asset_path(got) == _asset_path(value), _asset_path(got)
        if kind == 'scalar':
            return abs(float(got) - float(value)) <= 1e-4, float(got)
        got_list = [float(got.r), float(got.g), float(got.b), float(got.a)]
        want = [float(value.r), float(value.g), float(value.b), float(value.a)]
        return all(abs(a - b) <= 1e-4 for a, b in zip(got_list, want)), got_list

    returned = setters[kind](instance, parameter, value)
    ok, got = matches()
    path = 'MaterialEditingLibrary.set_material_instance_%s_parameter_value (return %s ignored)' % (kind, returned)
    if not ok:
        prop = {'texture': 'texture_parameter_values', 'scalar': 'scalar_parameter_values', 'vector': 'vector_parameter_values'}[kind]
        struct_cls = {'texture': ue.TextureParameterValue, 'scalar': ue.ScalarParameterValue, 'vector': ue.VectorParameterValue}[kind]
        values = [v for v in instance.get_editor_property(prop) if str(v.get_editor_property('parameter_info').get_editor_property('name')) != parameter]
        entry = struct_cls()
        info = ue.MaterialParameterInfo()
        info.set_editor_property('name', parameter)
        entry.set_editor_property('parameter_info', info)
        entry.set_editor_property('parameter_value', value)
        values.append(entry)
        instance.set_editor_property(prop, values)
        ml.update_material_instance(instance)
        ok, got = matches()
        path = 'set_editor_property(%s) struct fallback' % prop
    record.setdefault('parameterPaths', {})[parameter] = path
    if not ok:
        raise RuntimeError('Parameter %s on %s read back %s after %s' % (parameter, instance.get_name(), got, path))


def build_instances(ue, spec, master, textures_by_slug, receipt):
    """textures_by_slug: {slug: {kind: Texture2D}}. Reuses saved instances that verify, creates the missing ones.
    Returns {instance name: MaterialInstanceConstant}."""
    ml = ue.MaterialEditingLibrary
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    folder = spec['instanceFolder']
    texture_parameters = spec['masterMaterial']['textureParameters']
    out = {}
    for name, cfg in spec['instances'].items():
        path = folder + '/' + name
        textures = textures_by_slug[cfg['set']]
        expected_textures = {p: _asset_path(textures[k]) for k, p in texture_parameters.items()}
        record = receipt['instances'].get(name) or {}
        record.update({'asset': path, 'set': cfg['set'], 'status': 'started'})
        receipt['instances'][name] = record
        if assets.does_asset_exist(path):
            instance = ue.load_asset(path)
            if not isinstance(instance, ue.MaterialInstanceConstant):
                raise RuntimeError('Existing asset at %s is not a MaterialInstanceConstant' % path)
            record['created'] = False
        else:
            instance = tools.create_asset(name, folder, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew())
            if not isinstance(instance, ue.MaterialInstanceConstant):
                raise RuntimeError('MaterialInstanceConstant factory failed for ' + path)
            record['created'] = True
        # Parent first: parameters only resolve against a compiled parent (the master is recompiled + saved before this).
        if _asset_path(instance.get_editor_property('parent')) != _asset_path(master):
            ml.set_material_instance_parent(instance, master)
            record['parentPath'] = 'MaterialEditingLibrary.set_material_instance_parent'
            if _asset_path(instance.get_editor_property('parent')) != _asset_path(master):
                instance.set_editor_property('parent', master)
                ml.update_material_instance(instance)
                record['parentPath'] = 'set_editor_property(parent) fallback'
        parent_now = _asset_path(instance.get_editor_property('parent'))
        if parent_now != _asset_path(master):
            raise RuntimeError('Instance %s parent is %s, not the master' % (name, parent_now))
        for kind, parameter in texture_parameters.items():
            _set_instance_parameter(ue, ml, instance, 'texture', parameter, textures[kind], record)
        for parameter, value in cfg['scalars'].items():
            _set_instance_parameter(ue, ml, instance, 'scalar', parameter, float(value), record)
        _set_instance_parameter(ue, ml, instance, 'vector', 'Tint', ue.LinearColor(*cfg['tint']), record)
        ml.update_material_instance(instance)
        if not assets.save_loaded_asset(instance, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        readback = {'parent': _asset_path(instance.get_editor_property('parent')),
                    'textures': {p: _asset_path(ml.get_material_instance_texture_parameter_value(instance, p)) for p in texture_parameters.values()},
                    'scalars': {p: float(ml.get_material_instance_scalar_parameter_value(instance, p)) for p in cfg['scalars']}}
        if readback['parent'] != _asset_path(master) or readback['textures'] != expected_textures:
            raise RuntimeError('Instance readback differs for %s: %s' % (name, readback))
        record.update(readback=readback, uassetSha256=sha256_of(disk_path(path)), status='saved' if record['created'] else 'reused_verified')
        out[name] = instance
    return out


def ensure_textures(ue, spec, receipt):
    """Reuse every texture that already exists in the namespace (verified by class and path), import the missing ones."""
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    textures_by_slug = {}
    for slug in spec['sets']:
        prov, files = load_provenance(spec, slug)
        slug_record = receipt['textures'].setdefault(slug, {})
        slug_record['provenance'] = {k: prov[k] for k in ('assetId', 'assetName', 'license', 'resolution', 'physicalSizeMm', 'downloadedUtc')}
        handles = {}
        for kind in IMPORT_KINDS:
            path = texture_folder(spec, slug) + '/' + texture_asset_name(spec, slug, kind)
            if assets.does_asset_exist(path):
                tex = ue.load_asset(path)
                if not isinstance(tex, ue.Texture2D):
                    raise RuntimeError('Existing asset at %s is not a Texture2D' % path)
                slug_record[kind] = {'asset': path, 'status': 'reused', 'sourceSha256': files[kind]['sha256'],
                                     'compression': str(tex.get_editor_property('compression_settings')), 'srgb': bool(tex.get_editor_property('srgb')),
                                     'uassetSha256': sha256_of(disk_path(path))}
                handles[kind] = tex
            else:
                handles[kind] = import_texture(ue, spec, slug, kind, files[kind], receipt)
                receipt['textures'][slug][kind]['status'] = 'imported'
        textures_by_slug[slug] = handles
        if hasattr(ue.SystemLibrary, 'collect_garbage'):
            ue.SystemLibrary.collect_garbage()
    return textures_by_slug


def ensure_master(ue, spec, textures_by_slug, receipt):
    """Reuse the saved master when it exists and exposes the expected parameters; build it otherwise."""
    ml = ue.MaterialEditingLibrary
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    cfg = spec['masterMaterial']
    path = spec['nativeRoot'] + '/' + cfg['name']
    if assets.does_asset_exist(path):
        master = ue.load_asset(path)
        if not isinstance(master, ue.Material):
            raise RuntimeError('Existing asset at %s is not a Material' % path)
        scalars = sorted(str(n) for n in ml.get_scalar_parameter_names(master))
        textures = sorted(str(n) for n in ml.get_texture_parameter_names(master))
        missing = (set(cfg['scalarParameters']) - set(scalars)) | (set(cfg['textureParameters'].values()) - set(textures))
        if missing:
            raise RuntimeError('Saved master lacks parameters %s; delete it to rebuild' % sorted(missing))
        receipt['masterMaterial'] = {'asset': path, 'status': 'reused_verified', 'scalarParameters': scalars, 'textureParameters': textures,
                                     'tangentSpaceNormal': bool(master.get_editor_property('tangent_space_normal')), 'uassetSha256': sha256_of(disk_path(path))}
        return master
    first = spec['profileMapping']['stone']
    defaults = textures_by_slug[spec['instances'][first]['set']]
    return build_master_material(ue, spec, defaults, receipt)


def ensure_assets(ue, spec, receipt):
    """Textures -> master (recompiled + saved) -> instances, each step reusing what already exists and creating only what is missing.
    Nothing existing is ever overwritten."""
    textures_by_slug = ensure_textures(ue, spec, receipt)
    master = ensure_master(ue, spec, textures_by_slug, receipt)
    instances = build_instances(ue, spec, master, textures_by_slug, receipt)
    return master, instances


# --------------------------------------------------------------------------
# Engine side: reassignment at the component-override level
# --------------------------------------------------------------------------

class Reassignment:
    def __init__(self, ue, spec, helper, instances, canonical, canonical_names, manifest, include_gold):
        self.ue = ue
        self.spec = spec
        self.helper = helper
        self.instances = instances
        self.canonical = canonical
        self.canonical_names = canonical_names
        self.manifest = manifest
        self.include_gold = include_gold
        self.instance_paths = {name: _asset_path(inst) for name, inst in instances.items()}
        self.plan = []
        self.skipped = Counter()
        self.skipped_examples = defaultdict(list)

    def classify_slot(self, effective_path):
        """Return ('canonical', key) | ('original', None) | ('foreign', None) for an effective material path."""
        if not effective_path:
            return 'foreign', None
        name = effective_path.split('/')[-1]
        if name.startswith(self.spec['canonicalMaterialPrefix']):
            return 'canonical', self.canonical_names.get(name)
        if effective_path.startswith(self.spec['originalImportedMaterialFolder']) and effective_path.count('/') == self.spec['originalImportedMaterialFolder'].count('/'):
            return 'original', None
        return 'foreign', None

    def build_plan(self, rows):
        ue = self.ue
        prefix = self.spec['architectureFolderPrefix']
        excluded = set(self.spec['excludedFolders'])
        mesh_prefix = self.spec['architectureMeshPrefix']
        for row in rows:
            folder = row['folder']
            if not folder.startswith(prefix):
                continue
            if folder in excluded:
                self.skipped['excluded folder ' + folder] += 1
                continue
            actor = row['actor']
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                mesh_path = _asset_path(component.get_editor_property('static_mesh'))
                if not mesh_path or not mesh_path.startswith(mesh_prefix):
                    self.skipped['non-architecture mesh'] += 1
                    self.skipped_examples['non-architecture mesh'].append(mesh_path)
                    continue
                asset_name = mesh_path[len(mesh_prefix):]
                entry = self.canonical.get(asset_name)
                manifest = self.manifest.get(asset_name, {})
                source_name = (entry or {}).get('sourceName') or manifest.get('sourceName')
                overrides = [_asset_path(m) for m in component.get_editor_property('override_materials')]
                for slot in range(component.get_num_materials()):
                    effective = _asset_path(component.get_material(slot))
                    kind, key_from_material = self.classify_slot(effective)
                    if kind == 'foreign':
                        self.skipped['foreign material preserved'] += 1
                        if len(self.skipped_examples['foreign material preserved']) < 20:
                            self.skipped_examples['foreign material preserved'].append({'component': component.get_path_name(), 'slot': slot, 'material': effective})
                        continue
                    profile_key = key_from_material if kind == 'canonical' else (entry or {}).get('profileKey')
                    if kind == 'canonical' and entry and entry['profileKey'] != profile_key:
                        self.skipped['receipt/material profile mismatch (material wins)'] += 1
                    if profile_key is None:
                        self.skipped['no profile key'] += 1
                        continue
                    instance, reason = resolve_instance(self.spec, profile_key, source_name, self.include_gold)
                    if instance is None:
                        self.skipped[reason] += 1
                        continue
                    self.plan.append({'actor': actor.get_path_name(), 'label': row['label'], 'folder': folder, 'component': component.get_path_name(),
                                      'componentHandle': component, 'mesh': mesh_path, 'assetName': asset_name, 'sourceName': source_name, 'slot': slot,
                                      'profileKey': profile_key, 'effectiveBefore': effective, 'overrideBefore': overrides[slot] if slot < len(overrides) else None,
                                      'overrideArrayBefore': list(overrides), 'instance': instance, 'newMaterial': self.instance_paths[instance], 'reason': reason})
        return self.plan

    def apply(self):
        ue = self.ue
        by_component = defaultdict(list)
        for item in self.plan:
            by_component[item['component']].append(item)
        applied = 0
        for component_path, items in by_component.items():
            component = items[0]['componentHandle']
            overrides = list(component.get_editor_property('override_materials'))
            count = component.get_num_materials()
            while len(overrides) < count:
                overrides.append(None)
            for item in items:
                overrides[item['slot']] = self.instances[item['instance']]
            component.set_editor_property('override_materials', overrides)
            for item in items:
                after = _asset_path(component.get_material(item['slot']))
                if after != item['newMaterial']:
                    raise RuntimeError('Override did not take on %s slot %d: %s' % (component_path, item['slot'], after))
                item['effectiveAfter'] = after
                applied += 1
        return applied

    def strip(self):
        return [{k: v for k, v in item.items() if k != 'componentHandle'} for item in self.plan]


def fresh_receipt_path(spec):
    folder = ROOT / spec['receiptFolder']
    folder.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path = folder / (spec['receiptPrefix'] + stamp + '.json')
        if not path.exists():
            return stamp, path
    raise RuntimeError('Could not allocate a fresh receipt stamp')


def run(import_only=False, apply_only=False, include_gold=False, dry_run=False):
    import unreal as ue
    if import_only and apply_only:
        raise RuntimeError('-PbrImportOnly and -PbrApply are mutually exclusive')
    spec = load_spec()
    helper = load_placement_helper(spec)
    offline = offline_check(spec)
    if not offline['passed']:
        raise RuntimeError('Offline check failed: %s' % offline['errors'][:5])
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before the run')
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    namespace = spec['nativeRoot']
    namespace_exists = assets.does_directory_exist(namespace)
    # An existing namespace is reused asset by asset (verified by path/class/parameters); missing assets are created.
    # Existing assets are never overwritten (AGENTS.md hard rule 4).

    stamp, receipt_path = fresh_receipt_path(spec)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}
    canonical, canonical_names, review = load_canonical_index(spec)
    manifest, manifest_info = load_manifest_index(spec)
    receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'protectedMapSha256Before': protected, 'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'offlineCheck': {k: v for k, v in offline.items() if k not in ('planDefault', 'planWithGold')},
        'plannedTable': offline['planWithGold' if include_gold else 'planDefault'],
        'switches': {'importOnly': import_only, 'applyOnly': apply_only, 'includeGold': include_gold, 'dryRun': dry_run},
        'applyLevel': spec['applyLevel'], 'applyLevelJustification': spec['applyLevelJustification'],
        'canonicalReviewSha256': sha256_of(ROOT / spec['canonicalReview']), 'architectureManifest': manifest_info,
        'textures': {}, 'masterMaterial': {}, 'instances': {}, 'reassignment': {}, 'errors': [], 'mapSaved': False,
        'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        # -- 1/2. textures, master, instances (reuse what exists, create what is missing) ---------
        receipt['namespaceExistedBefore'] = namespace_exists
        master, instances = ensure_assets(ue, spec, receipt)
        write()
        receipt['assetSummary'] = {
            'texturesImported': sum(1 for s in receipt['textures'].values() for k, v in s.items() if k != 'provenance' and v.get('status') == 'imported'),
            'texturesReused': sum(1 for s in receipt['textures'].values() for k, v in s.items() if k != 'provenance' and v.get('status') == 'reused'),
            'masterStatus': receipt['masterMaterial'].get('status'),
            'instancesCreated': sorted(n for n, r in receipt['instances'].items() if r.get('created')),
            'instancesReused': sorted(n for n, r in receipt['instances'].items() if r.get('created') is False),
        }
        receipt['status'] = 'assets_saved'
        if import_only:
            receipt['status'] = 'assets_saved_no_map_change'
            return receipt

        # -- 3. map guards + checkpoint --------------------------------------------------------
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map' % world.get_outermost().get_name())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present after loading the map; resolve before a checkpointed edit')
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[len('/Game/'):]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[len('/Game/'):])
        receipt['checkpoint'] = str(checkpoint)

        state = helper.Placement(ue, spec)
        state.world = world
        state.receipt = receipt
        state.receipt_path = receipt_path
        rows = state.take_snapshot()
        baseline = state.numeric_baseline(rows)
        receipt['actorCountBefore'] = len(rows)

        work = Reassignment(ue, spec, helper, instances, canonical, canonical_names, manifest, include_gold)
        plan = work.build_plan(rows)
        per_instance = Counter(item['instance'] for item in plan)
        per_profile = Counter((item['profileKey'], item['instance']) for item in plan)
        receipt['reassignment'] = {
            'plannedSlots': len(plan), 'plannedComponents': len({item['component'] for item in plan}),
            'perInstance': dict(per_instance), 'perProfile': {'%s -> %s' % k: v for k, v in per_profile.items()},
            'skipped': dict(work.skipped), 'skippedExamples': {k: v[:20] for k, v in work.skipped_examples.items()},
            'effectiveBeforeKinds': dict(Counter(work.classify_slot(item['effectiveBefore'])[0] for item in plan)),
        }
        write()
        if not plan:
            receipt['status'] = 'nothing_to_reassign_map_unchanged'
            return receipt
        if dry_run:
            receipt['reassignment']['plan'] = work.strip()
            receipt['status'] = 'dry_run_planned_map_unchanged'
            return receipt

        # -- 4. apply, verify invariants, save, reopen, read back -----------------------------------
        applied = work.apply()
        receipt['reassignment']['appliedSlots'] = applied
        receipt['reassignment']['restore'] = [{k: item[k] for k in ('component', 'slot', 'overrideBefore', 'overrideArrayBefore', 'effectiveBefore', 'newMaterial')} for item in work.plan]
        receipt['reassignment']['changes'] = [{k: item[k] for k in ('component', 'assetName', 'sourceName', 'slot', 'profileKey', 'instance', 'reason', 'effectiveBefore', 'effectiveAfter')} for item in work.plan]
        write()
        current = state.numeric_baseline(state.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed or len(current) != len(baseline):
            raise RuntimeError('Actor set or transforms changed before save: %s' % changed[:10])
        if not levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha256_of(map_file)
        write()

        if not levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        state.world = editor.get_editor_world()
        reopened = state.take_snapshot()
        reopened_numeric = state.numeric_baseline(reopened)
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if changed or len(reopened_numeric) != len(baseline):
            raise RuntimeError('Actors differ after reopen: %s' % changed[:10])
        receipt['actorCountAfter'] = len(reopened)
        expected = {(item['component'], item['slot']): item['newMaterial'] for item in work.plan}
        found = Counter()
        mismatches = []
        instance_paths = set(work.instance_paths.values())
        for row in reopened:
            for component in row['actor'].get_components_by_class(ue.StaticMeshComponent):
                path = component.get_path_name()
                for slot in range(component.get_num_materials()):
                    material = _asset_path(component.get_material(slot))
                    if material in instance_paths:
                        found[material.split('/')[-1]] += 1
                    want = expected.get((path, slot))
                    if want is not None and material != want:
                        mismatches.append({'component': path, 'slot': slot, 'expected': want, 'actual': material})
        sample = defaultdict(list)
        limit = spec['verification']['readbackSamplePerInstance']
        for item in work.plan:
            if len(sample[item['instance']]) < limit:
                sample[item['instance']].append({'component': item['component'], 'slot': item['slot'], 'material': expected[(item['component'], item['slot'])]})
        receipt['reopenedReadback'] = {'instanceSlotCounts': dict(found), 'expectedPerInstance': dict(per_instance), 'mismatches': mismatches[:50],
                                       'mismatchCount': len(mismatches), 'sample': dict(sample)}
        if mismatches:
            raise RuntimeError('%d reopened slots differ from the plan' % len(mismatches))
        if any(found.get(name, 0) != count for name, count in per_instance.items()):
            raise RuntimeError('Reopened instance counts differ: %s vs %s' % (dict(found), dict(per_instance)))
        receipt['status'] = 'pbr_materials_applied_saved_reopened_visual_acceptance_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif apply_only:
            receipt['status'] = 'failed_apply_map_unchanged_saved_assets_untouched'
        elif receipt['textures'] or receipt['masterMaterial'] or receipt['instances']:
            receipt['status'] = 'failed_partial_assets_preserved_map_unchanged'
        else:
            receipt['status'] = 'failed_before_assets_nothing_changed'
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(m, 'umap')) == v for m, v in protected.items())
        write()


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
    return 'release_pbr_architecture.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    lowered = [t.lower() for t in command_line.split()]
    try:
        receipt = run(import_only='-pbrimportonly' in lowered, apply_only='-pbrapply' in lowered,
                      include_gold='-pbrincludegold' in lowered, dry_run='-pbrdryrun' in lowered)
        ue.log('release_pbr_architecture: %s planned %s applied %s' % (
            receipt['status'], receipt.get('reassignment', {}).get('plannedSlots'), receipt.get('reassignment', {}).get('appliedSlots')))
    except Exception as error:
        ue.log_error('release_pbr_architecture failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line.lower() and '-run=pythonscript' not in command_line.lower():
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

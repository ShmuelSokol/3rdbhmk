"""Guarded paroches pattern: the frieze relief image woven into the paroches cloth material.

Every number comes from Scripts/release_paroches_pattern.spec.json. In order:

  1. Offline image stage: luma of the frozen relief image stretched by percentiles, and the V2
     frieze normal map, both fitted ONCE to the live cloth (scaled to the 306 cm height, centred,
     27 cm plain bands each side) into 2048 x 1741 PNGs in SourceAssets/relief-images/derived/.
  2. Engine: import both as textures (clamp addressing), read the canonical red, build
     M_ParochesPattern: BaseColor = red * lerp(0.7, 1.0, luma), Normal = drape normal perturbed
     by the relief normal at 0.3 in the projection frame, UVs from world Y/Z (cloth at X -5585
     facing east). Saved in /Game/MikdashV3/MaterialReview/ParochesPatternV1.
  3. Map: checkpoint; find the cloth actor (RELEASE_Doors_* with 'ParochesCloth' in its mesh),
     check its bounds against the doors receipt, override every slot of its StaticMeshComponent;
     hem / rod / rings untouched; save, reopen, readback, receipt in
     SourceAssets/sanctuary-detail/ParochesPatternV1/.

Commandlet invocation (serial; never while another native job is running; run AFTER the V2
frieze image stage has written gold-palm-cherub-relief_v2_normal.png):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_paroches_pattern.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-ParochesPattern-01.log"

Optional switches: -ParochesImagesOnly (offline PNGs only), -ParochesAssetsOnly (textures +
material, no map change), -ParochesAssignOnly (material already saved: assign only).

Offline: python Scripts/release_paroches_pattern.py [--derive]
"""
import argparse
import importlib.util
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_paroches_pattern.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET or Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec target or project differs from the script')
    return spec


def _load_module(relative, name):
    path = ROOT / relative
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def load_modules(spec):
    v2 = _load_module(spec['friezeV2Script'], 'release_frieze_v2')
    v1 = v2.load_v1(v2.load_spec())
    helper = _load_module(spec['placementHelper'], 'release_place_assets')
    return v1, v2, helper


def sha256_of(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _mesh_name(asset_path):
    """Asset NAME only: 'Paroches' must match SM_Paroches*, not the DoorsParochesV1 folder of every door mesh."""
    return (asset_path or '').rsplit('/', 1)[-1]


def latest_doors_receipt(spec):
    folder = ROOT / spec['doors']['receiptFolder']
    rows = []
    for path in sorted(folder.glob('native-import-*.json')):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if str(data.get('status', '')).startswith(spec['doors']['receiptStatusPrefix']):
            rows.append((path, data))
    if not rows:
        raise RuntimeError('No DoorsParochesV1 receipt with the saved status in ' + str(folder))
    return rows[-1]


# --------------------------------------------------------------------------
# Image stage
# --------------------------------------------------------------------------

def cloth_layout(spec):
    cfg = spec['image']
    width_px = int(cfg['outputs']['textureWidthPx'])
    cloth_w, cloth_h = float(cfg['cloth']['widthCm']), float(cfg['cloth']['heightCm'])
    height_px = int(round(width_px * cloth_h / cloth_w))
    image_px = height_px                                # square image fitted to the cloth height
    x0 = (width_px - image_px) // 2
    return {'textureSize': [width_px, height_px], 'imagePx': image_px, 'imageColumnStart': x0, 'imageColumnEnd': x0 + image_px,
            'imageWorldWidthCm': cloth_h, 'marginCmEachSide': (cloth_w - cloth_h) / 2.0}


def _embed(rows_img, layout, fill, width_px):
    x0 = layout['imageColumnStart']
    n = len(rows_img[0])
    out = []
    for row in rows_img:
        full = [fill] * width_px
        full[x0:x0 + n] = row
        out.append(full)
    return out


def image_stage(spec, v1, derived_dir=None):
    cfg = spec['image']
    source = ROOT / cfg['source']
    if sha256_of(source) != cfg['sourceSha256']:
        raise RuntimeError('Frozen relief image hash differs: ' + str(source))
    normal_src = ROOT / cfg['normalSource']
    if not normal_src.exists():
        raise RuntimeError('V2 frieze normal map missing; run Scripts/release_frieze_v2.py --derive first: ' + str(normal_src))
    derived = Path(derived_dir) if derived_dir else ROOT / cfg['derivedFolder']
    derived.mkdir(parents=True, exist_ok=True)
    layout = cloth_layout(spec)
    width_px, height_px = layout['textureSize']
    n = layout['imagePx']
    stem = source.stem

    decoded = v1.decode_png(source)
    luma = v1.luma_rows(decoded, cfg['lumaWeights'])
    src_size = [decoded['width'], decoded['height']]
    del decoded
    values = v1.flat_sorted(luma)
    lo, hi = v1.percentile_sorted(values, float(cfg['lumaLowPercentile'])), v1.percentile_sorted(values, float(cfg['lumaHighPercentile']))
    if hi <= lo:
        raise RuntimeError('Luma percentiles collapsed')
    del values
    scale = 1.0 / (hi - lo)
    stretched = [[min(1.0, max(0.0, (v - lo) * scale)) for v in row] for row in luma]
    del luma
    mean = sum(sum(r) for r in stretched) / float(len(stretched) * len(stretched[0]))
    fitted = v1.resample_bilinear(stretched, n, n)
    del stretched
    luma_rows = _embed(fitted, layout, mean, width_px)
    del fitted
    luma_path = derived / (stem + cfg['outputs']['lumaSuffix'])
    luma_sha = v1.encode_png(luma_path, width_px, height_px, [bytes(int(round(v * 255)) for v in row) for row in luma_rows], 0, bit_depth=8)
    del luma_rows

    normal = v1.decode_png(normal_src)
    if normal['channels'] != 3:
        raise RuntimeError('V2 normal PNG is not RGB')
    channels = []
    for c in range(3):
        plane = [[b / 255.0 for b in row[c::3]] for row in normal['rows']]
        channels.append(v1.resample_bilinear(plane, n, n))
    normal_size = [normal['width'], normal['height']]
    normal_sha_src = normal['sha256']
    del normal
    fills = (128 / 255.0, 128 / 255.0, 1.0)
    embedded = [_embed(channels[c], layout, fills[c], width_px) for c in range(3)]
    del channels
    rows_rgb = []
    for y in range(height_px):
        row = bytearray()
        for r, g, b in zip(embedded[0][y], embedded[1][y], embedded[2][y]):
            row += bytes((int(round(r * 255)), int(round(g * 255)), int(round(b * 255))))
        rows_rgb.append(bytes(row))
    del embedded
    normal_path = derived / (stem + cfg['outputs']['normalSuffix'])
    normal_sha = v1.encode_png(normal_path, width_px, height_px, rows_rgb, 2)
    return {'source': str(source), 'sourceSha256': cfg['sourceSha256'], 'sourceSize': src_size, 'stem': stem,
            'normalSource': str(normal_src), 'normalSourceSha256': normal_sha_src, 'normalSourceSize': normal_size,
            'luma': {'lowPercentileValue': lo, 'highPercentileValue': hi, 'stretchedMeanFill': mean},
            'layout': layout, 'fit': cfg['fit'],
            'outputs': {'luma': {'path': str(luma_path), 'sha256': luma_sha, 'size': [width_px, height_px], 'bitDepth': 8},
                        'normal': {'path': str(normal_path), 'sha256': normal_sha, 'size': [width_px, height_px], 'bitDepth': 8}}}


# --------------------------------------------------------------------------
# Offline check
# --------------------------------------------------------------------------

def offline_check(spec=None, namespace_expected=None):
    spec = spec or load_spec()
    report = {}
    source = ROOT / spec['image']['source']
    report['source'] = {'path': str(source), 'frozenHashMatches': source.exists() and sha256_of(source) == spec['image']['sourceSha256']}
    if not report['source']['frozenHashMatches']:
        raise RuntimeError('Frozen relief image missing or changed')
    report['normalSourceOnDisk'] = (ROOT / spec['image']['normalSource']).exists()
    path, receipt = latest_doors_receipt(spec)
    cloth = [r for r in receipt['reopenedReadback'] if spec['doors']['clothMeshNameContains'] in _mesh_name(r['meshPath'][0])]
    if len(cloth) != 1:
        raise RuntimeError('Doors receipt has %d cloth actors' % len(cloth))
    cloth = cloth[0]
    helper = _load_module(spec['placementHelper'], 'release_place_assets')
    error = helper.box_error(cloth['worldBoundsCm'], spec['doors']['expectedClothWorldBoundsCm'])
    if error > spec['doors']['clothBoundsToleranceCm']:
        raise RuntimeError('Cloth bounds in the doors receipt differ from the spec by %.3f cm' % error)
    if cloth['meshPath'] != [spec['doors']['expectedClothMesh']] or cloth['materials'] != [spec['doors']['expectedClothMaterial']]:
        raise RuntimeError('Cloth mesh/material in the doors receipt differ from the spec: %s %s' % (cloth['meshPath'], cloth['materials']))
    report['doorsReceipt'] = {'path': str(path), 'status': receipt['status'], 'clothLabel': cloth['label'], 'clothBoundsErrorCm': error,
                              'parochesActors': [r['label'] for r in receipt['reopenedReadback'] if spec['doors']['parochesMeshNameContains'] in _mesh_name(r['meshPath'][0])]}
    b = spec['doors']['expectedClothWorldBoundsCm']
    if abs((b['max'][1] - b['min'][1]) - spec['image']['cloth']['widthCm']) > 0.01 or abs((b['max'][2] - b['min'][2]) - spec['image']['cloth']['heightCm']) > 0.01:
        raise RuntimeError('image.cloth size differs from the cloth bounds')
    report['layout'] = cloth_layout(spec)
    report['redSourceOnDisk'] = helper.disk_path(spec['material']['redSource']).exists()
    namespace_dir = ROOT / 'Content' / spec['material']['namespace'][len('/Game/'):]
    report['namespaceFolderExistsOnDisk'] = namespace_dir.exists()
    if namespace_expected is False and namespace_dir.exists():
        raise RuntimeError('Target namespace already exists on disk: ' + str(namespace_dir))
    if namespace_expected is True and not namespace_dir.exists():
        raise RuntimeError('Assign-only needs the saved namespace: ' + str(namespace_dir))
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side
# --------------------------------------------------------------------------

def read_red(ue, spec, receipt):
    cfg = spec['material']
    ml = ue.MaterialEditingLibrary
    result = {'source': cfg['redSource'], 'read': False, 'linear': list(cfg['redFallbackLinear']), 'roughness': float(cfg['roughnessFallback']), 'note': cfg['redFallbackNote']}
    try:
        red = ue.load_asset(cfg['redSource'])
        if isinstance(red, ue.Material):
            node = ml.get_material_property_input_node(red, ue.MaterialProperty.MP_BASE_COLOR)
            if isinstance(node, ue.MaterialExpressionConstant3Vector):
                colour = node.get_editor_property('constant')
                result.update(read=True, linear=[float(colour.r), float(colour.g), float(colour.b)], nodeClass=node.get_class().get_name(), note='read from the canonical red')
            elif isinstance(node, ue.MaterialExpressionVectorParameter):
                colour = node.get_editor_property('default_value')
                result.update(read=True, linear=[float(colour.r), float(colour.g), float(colour.b)], nodeClass=node.get_class().get_name(), note='read from the canonical red (VectorParameter default)')
            else:
                result['note'] = 'BaseColor input is %s; fallback used' % (node.get_class().get_name() if node else None)
            rough = ml.get_material_property_input_node(red, ue.MaterialProperty.MP_ROUGHNESS)
            if isinstance(rough, ue.MaterialExpressionConstant):
                result['roughness'] = float(rough.get_editor_property('r'))
                result['roughnessRead'] = True
            try:
                result['twoSided'] = bool(red.get_editor_property('two_sided'))
            except Exception:
                pass
        else:
            result['note'] = 'red source did not load as a Material; fallback used'
    except Exception as error:
        result['note'] = 'red source unreadable (%r); fallback used' % (error,)
    receipt['red'] = result
    return result


def build_material(ue, spec, red, luma_tex, normal_tex, cloth_bounds, receipt):
    cfg = spec['material']
    ml = ue.MaterialEditingLibrary
    path = cfg['folder'] + '/' + cfg['name']
    record = {'asset': path, 'nodes': [], 'connections': [], 'status': 'started'}
    receipt['material'] = record
    material = ue.AssetToolsHelpers.get_asset_tools().create_asset(cfg['name'], cfg['folder'], ue.Material, ue.MaterialFactoryNew())
    if not isinstance(material, ue.Material):
        raise RuntimeError('Material factory failed for ' + path)

    def node(cls, x, y, **props):
        expression = ml.create_material_expression(material, cls, x, y)
        if expression is None:
            raise RuntimeError('create_material_expression failed for %s' % cls.__name__)
        for key, value in props.items():
            expression.set_editor_property(key, value)
        record['nodes'].append({'class': cls.__name__, 'position': [x, y], 'properties': {k: (v if isinstance(v, (int, float, bool, str)) else str(v)) for k, v in props.items()}})
        return expression

    def input_name(expression, wanted):
        names = [str(n) for n in ml.get_material_expression_input_names(expression)]
        for candidate in names:
            if candidate.lower() == wanted.lower():
                return candidate
        raise RuntimeError('%s has no input %r (inputs %s)' % (expression.get_class().get_name(), wanted, names))

    def wire(source, output, target, wanted):
        pin = input_name(target, wanted)
        if not ml.connect_material_expressions(source, output, target, pin):
            raise RuntimeError('Connection %s[%r] -> %s[%r] failed' % (source.get_class().get_name(), output, target.get_class().get_name(), pin))
        record['connections'].append('%s.%s -> %s.%s' % (source.get_class().get_name(), output or 'RGB', target.get_class().get_name(), pin))

    def to_property(source, output, prop_name):
        if not ml.connect_material_property(source, output, getattr(ue.MaterialProperty, prop_name)):
            raise RuntimeError('connect_material_property %s -> %s failed' % (source.get_class().get_name(), prop_name))
        record['connections'].append('%s.%s -> %s' % (source.get_class().get_name(), output or 'RGB', prop_name))

    def custom(code, inputs, output_type, x, y, description):
        slots = []
        for name in inputs:
            slot = ue.CustomInput()
            slot.set_editor_property('input_name', name)
            slots.append(slot)
        expression = node(ue.MaterialExpressionCustom, x, y, inputs=slots, code=code, output_type=output_type, description=description)
        for name, (source, output) in inputs.items():
            wire(source, output, expression, name)
        return expression

    y_max, z_top = cloth_bounds['max'][1], cloth_bounds['max'][2]
    width, height = cloth_bounds['max'][1] - cloth_bounds['min'][1], cloth_bounds['max'][2] - cloth_bounds['min'][2]
    uv_code = 'return float2((%.4f - P.y) / %.4f, (%.4f - P.z) / %.4f);' % (y_max, width, z_top, height)
    record['uvProjection'] = {'code': uv_code, 'yMax': y_max, 'zTop': z_top, 'widthCm': width, 'heightCm': height,
                              'rule': 'U grows toward world -Y (the east-facing viewer\'s right), V grows downward from the cloth top'}
    position = node(ue.MaterialExpressionWorldPosition, -1400, 0)
    uv = custom(uv_code, {'P': (position, '')}, ue.CustomMaterialOutputType.CMOT_FLOAT2, -1100, 0, 'Paroches cloth projection (world Y/Z -> UV)')

    gray, gray_name = None, None
    for candidate in (spec['textures']['luma']['samplerType'], spec['textures']['luma']['samplerTypeFallback']):
        if hasattr(ue.MaterialSamplerType, candidate):
            gray, gray_name = getattr(ue.MaterialSamplerType, candidate), candidate
            break
    luma_sample = node(ue.MaterialExpressionTextureSample, -800, -250, texture=luma_tex, sampler_type=gray)
    wire(uv, '', luma_sample, 'UVs')
    lerp = node(ue.MaterialExpressionLinearInterpolate, -500, -250, const_a=float(cfg['lumaLerp']['atLuma0']), const_b=float(cfg['lumaLerp']['atLuma1']))
    wire(luma_sample, 'R', lerp, 'Alpha')
    colour = node(ue.MaterialExpressionConstant3Vector, -500, -450, constant=ue.LinearColor(red['linear'][0], red['linear'][1], red['linear'][2], 1.0))
    multiply = node(ue.MaterialExpressionMultiply, -250, -350)
    wire(colour, '', multiply, 'A')
    wire(lerp, '', multiply, 'B')
    to_property(multiply, '', 'MP_BASE_COLOR')

    normal_sample = node(ue.MaterialExpressionTextureSample, -800, 150, texture=normal_tex, sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    wire(uv, '', normal_sample, 'UVs')
    strength = float(cfg['normalStrength'])
    world_space = True
    try:
        material.set_editor_property('tangent_space_normal', False)
    except Exception as error:
        world_space = False
        record['tangentSpaceNormalError'] = repr(error)
    if world_space:
        vertex_normal = node(ue.MaterialExpressionVertexNormalWS, -800, 400)
        normal_code = 'return normalize(N + %.4f * (T.x * float3(0.0, -1.0, 0.0) + T.y * float3(0.0, 0.0, -1.0)));' % strength
        composed = custom(normal_code, {'N': (vertex_normal, ''), 'T': (normal_sample, '')}, ue.CustomMaterialOutputType.CMOT_FLOAT3, -400, 250,
                          'Relief normal (+U = world -Y, +V = world -Z) added to the drape normal')
        to_property(composed, '', 'MP_NORMAL')
        record['normal'] = {'mode': 'world_space_projection_frame', 'code': normal_code, 'strength': strength}
    else:
        flat = node(ue.MaterialExpressionConstant3Vector, -500, 450, constant=ue.LinearColor(0.0, 0.0, 1.0, 1.0))
        blend = node(ue.MaterialExpressionLinearInterpolate, -250, 300, const_alpha=strength)
        wire(flat, '', blend, 'A')
        wire(normal_sample, '', blend, 'B')
        to_property(blend, '', 'MP_NORMAL')
        record['normal'] = {'mode': 'tangent_space_fallback_mesh_tangents_are_unreliable', 'strength': strength}
    rough = node(ue.MaterialExpressionConstant, -250, 550, r=float(red['roughness']))
    to_property(rough, '', 'MP_ROUGHNESS')
    metallic = node(ue.MaterialExpressionConstant, -250, 650, r=float(cfg['metallic']))
    to_property(metallic, '', 'MP_METALLIC')
    if red.get('twoSided'):
        material.set_editor_property('two_sided', True)
        record['twoSided'] = True
    if ml.get_material_property_input_node(material, ue.MaterialProperty.MP_WORLD_POSITION_OFFSET) is not None:
        raise RuntimeError('WorldPositionOffset unexpectedly connected')
    ml.recompile_material(material)
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + path)
    record['lumaSamplerType'] = gray_name
    record['inputsWired'] = {}
    for prop_name in ('MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_WORLD_POSITION_OFFSET'):
        wired = ml.get_material_property_input_node(material, getattr(ue.MaterialProperty, prop_name))
        record['inputsWired'][prop_name] = wired.get_class().get_name() if wired else None
    record['uassetSha256'] = sha256_of(ROOT / 'Content' / (path[len('/Game/'):] + '.uasset'))
    record['status'] = 'saved'
    return material


def set_clamp(ue, tex, spec, receipt, kind):
    mode = spec['textures']['addressMode']
    try:
        value = getattr(ue.TextureAddress, mode)
        tex.set_editor_property('address_x', value)
        tex.set_editor_property('address_y', value)
        ue.get_editor_subsystem(ue.EditorAssetSubsystem).save_loaded_asset(tex, only_if_is_dirty=False)
        receipt['textures'][kind]['addressMode'] = mode
    except Exception as error:
        receipt['textures'][kind]['addressMode'] = 'unset: %r' % (error,)


def fresh_receipt_path(spec):
    folder = ROOT / spec['receiptFolder']
    folder.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path = folder / (spec['receiptPrefix'] + stamp + '.json')
        if not path.exists():
            return stamp, path
    raise RuntimeError('Could not allocate a fresh receipt stamp')


def find_paroches_actors(spec, snapshot):
    doors = spec['doors']
    rows = [r for r in snapshot if r['label'].startswith(doors['labelPrefix']) and any(doors['parochesMeshNameContains'] in _mesh_name(m) for m in r['meshes'])]
    cloth = [r for r in rows if any(doors['clothMeshNameContains'] in _mesh_name(m) for m in r['meshes'])]
    if len(cloth) != 1:
        raise RuntimeError('Expected one paroches cloth actor, found %d' % len(cloth))
    return cloth[0], [r for r in rows if r is not cloth[0]]


def run(images_only=False, assets_only=False, assign_only=False):
    import unreal as ue
    if sum(bool(x) for x in (images_only, assets_only, assign_only)) > 1:
        raise RuntimeError('Switches are mutually exclusive')
    spec = load_spec()
    v1, v2, helper = load_modules(spec)
    offline = offline_check(spec, namespace_expected=(True if assign_only else (None if images_only else False)))
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before the run')
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    namespace = spec['material']['namespace']
    if assign_only and not assets.does_directory_exist(namespace):
        raise RuntimeError('Assign-only requested but namespace is missing: ' + namespace)
    if not assign_only and not images_only and assets.does_directory_exist(namespace):
        raise RuntimeError('Existing native namespace preserved (use -ParochesAssignOnly): ' + namespace)

    stamp, receipt_path = fresh_receipt_path(spec)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    doors_path, doors_receipt = latest_doors_receipt(spec)
    receipt = {'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
               'protectedMapSha256Before': protected, 'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
               'engineVersion': ue.SystemLibrary.get_engine_version(), 'offlineCheck': offline, 'doorsReceipt': str(doors_path),
               'switches': {'imagesOnly': images_only, 'assetsOnly': assets_only, 'assignOnly': assign_only},
               'sourceReference': spec['sourceReference'], 'image': {}, 'textures': {}, 'red': {}, 'material': {}, 'errors': [], 'mapSaved': False,
               'limitations': list(spec['limitations'])}

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    saved = False
    try:
        # Cloth bounds for the projection come from the doors receipt (checked live before assignment).
        cloth_receipt = [r for r in doors_receipt['reopenedReadback'] if spec['doors']['clothMeshNameContains'] in _mesh_name(r['meshPath'][0])][0]
        cloth_bounds = cloth_receipt['worldBoundsCm']
        if not assign_only:
            receipt['image'] = image_stage(spec, v1)
            write()
            if images_only:
                receipt['status'] = 'derived_images_written_no_engine_assets_no_map_change'
                return receipt
            luma_tex = v1.import_texture(ue, spec, 'luma', receipt['image']['outputs']['luma']['path'], receipt['image']['stem'], receipt)
            set_clamp(ue, luma_tex, spec, receipt, 'luma')
            normal_tex = v1.import_texture(ue, spec, 'normal', receipt['image']['outputs']['normal']['path'], receipt['image']['stem'], receipt)
            set_clamp(ue, normal_tex, spec, receipt, 'normal')
            write()
            red = read_red(ue, spec, receipt)
            material = build_material(ue, spec, red, luma_tex, normal_tex, cloth_bounds, receipt)
            write()
            if assets_only:
                receipt['status'] = 'assets_saved_no_map_change'
                return receipt
        else:
            material = ue.load_asset(spec['material']['folder'] + '/' + spec['material']['name'])
            if not isinstance(material, ue.Material):
                raise RuntimeError('Saved material missing')
            receipt['material'] = {'asset': v1._asset_path(material), 'status': 'reused'}

        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.load_level(TARGET):
            raise RuntimeError('load_level failed')
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world is not the combined map')
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[len('/Game/'):]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[len('/Game/'):])
        receipt['checkpoint'] = str(checkpoint)

        run_state = helper.Placement(ue, spec)
        run_state.world, run_state.receipt, run_state.receipt_path = world, receipt, receipt_path
        run_state.take_snapshot()
        baseline = run_state.numeric_baseline(run_state.snapshot)
        cloth, others = find_paroches_actors(spec, run_state.snapshot)
        error = helper.box_error(cloth['bounds'], cloth_bounds)
        if error > spec['doors']['clothBoundsToleranceCm']:
            raise RuntimeError('Live cloth bounds differ from the doors receipt by %.3f cm' % error)
        component = cloth['actor'].get_component_by_class(ue.StaticMeshComponent)
        before = [v1._asset_path(component.get_material(i)) for i in range(component.get_num_materials())]
        if set(before) != {spec['doors']['expectedClothMaterial']}:
            raise RuntimeError('Cloth currently carries %s, not the canonical red' % before)
        others_before = {r['label']: [v1._asset_path(r['actor'].get_component_by_class(ue.StaticMeshComponent).get_material(i))
                                      for i in range(r['actor'].get_component_by_class(ue.StaticMeshComponent).get_num_materials())] for r in others}
        for i in range(component.get_num_materials()):
            component.set_material(i, material)
        after = [v1._asset_path(component.get_material(i)) for i in range(component.get_num_materials())]
        if set(after) != {v1._asset_path(material)}:
            raise RuntimeError('Material override readback failed: %s' % after)
        tags = list(cloth['actor'].get_editor_property('tags'))
        cloth['actor'].set_editor_property('tags', tags + [ue.Name(spec['actorTag'])])
        receipt['assignment'] = {'clothLabel': cloth['label'], 'clothName': cloth['name'], 'mesh': cloth['meshes'], 'worldBoundsCm': cloth['bounds'],
                                 'boundsErrorVsDoorsReceiptCm': error, 'materialsBefore': before, 'materialsAfter': after,
                                 'untouched': others_before, 'restoreRule': 'set_material(slot, %s) on every slot of the cloth component' % spec['doors']['expectedClothMaterial']}
        write()
        current = run_state.numeric_baseline(run_state.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Actors moved before save: %s' % changed[:10])
        if not levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha256_of(map_file)
        write()
        if not levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run_state.world = editor.get_editor_world()
        reopened = run_state.take_snapshot()
        reopened_numeric = run_state.numeric_baseline(reopened)
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Actors differ after reopen: %s' % changed[:10])
        cloth2, others2 = find_paroches_actors(spec, reopened)
        comp2 = cloth2['actor'].get_component_by_class(ue.StaticMeshComponent)
        materials2 = [v1._asset_path(comp2.get_material(i)) for i in range(comp2.get_num_materials())]
        if set(materials2) != {v1._asset_path(material)}:
            raise RuntimeError('Cloth material after reopen: %s' % materials2)
        others_after = {r['label']: [v1._asset_path(r['actor'].get_component_by_class(ue.StaticMeshComponent).get_material(i))
                                     for i in range(r['actor'].get_component_by_class(ue.StaticMeshComponent).get_num_materials())] for r in others2}
        if others_after != others_before:
            raise RuntimeError('Hem/fixings materials changed: %s' % others_after)
        receipt['reopenedReadback'] = {'cloth': {'label': cloth2['label'], 'materials': materials2, 'worldBoundsCm': cloth2['bounds'], 'pose': cloth2['pose']},
                                       'untouched': others_after}
        receipt['status'] = 'paroches_pattern_saved_reopened_visual_acceptance_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif receipt['material'] or receipt['textures']:
            receipt['status'] = 'failed_partial_assets_preserved_map_unchanged'
        else:
            receipt['status'] = 'failed_before_assets_nothing_changed'
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(sha256_of(helper.disk_path(m, 'umap')) == v for m, v in protected.items())
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
    return 'release_paroches_pattern.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    lowered = ue.SystemLibrary.get_command_line().lower()
    try:
        receipt = run(images_only='-parochesimagesonly' in lowered, assets_only='-parochesassetsonly' in lowered, assign_only='-parochesassignonly' in lowered)
        ue.log('release_paroches_pattern: ' + receipt['status'])
    except Exception as error:
        ue.log_error('release_paroches_pattern failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in lowered and '-run=pythonscript' not in lowered:
            ue.SystemLibrary.quit_editor()


def _offline_main():
    parser = argparse.ArgumentParser(description='Offline image stage / consistency check for the paroches pattern')
    parser.add_argument('--derive', action='store_true', help='write the paroches luma/normal PNGs')
    parser.add_argument('--derived-dir', help='output folder (default spec derivedFolder)')
    args = parser.parse_args()
    spec = load_spec()
    if args.derive:
        v1, _, _ = load_modules(spec)
        print(json.dumps(image_stage(spec, v1, derived_dir=args.derived_dir), indent=2))
    else:
        print(json.dumps(offline_check(spec), indent=2))


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        _offline_main()
elif _invoked_as_native_script():
    _main()

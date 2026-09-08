"""Guarded native import and placement of the APPROVED V15 paroches (fresh ParochesV15 namespace).

Every number is read from Scripts/release_paroches_v15.spec.json and the frozen offline source set
SourceAssets/sanctuary-detail/ParochesV15/geometry-manifest.json (written by Scripts/create_paroches_v15.py).
The approved artwork hash f48ccf05...2df89 is verified against the frozen copy AND, when present, the
original approved file before anything else happens. One target per run:

  -Main50        current 50 cm main map   /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough      350 x 300 cm
  -Candidate48   isolated 48 cm candidate /Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough  336 x 288 cm

In order:
  1. Guards: approved hash, frozen manifest hash and OBJ/PNG hashes, right project, no game world,
     no dirty packages, target chosen, per-target mesh assets absent (unless -ParochesV15PlaceOnly).
  2. Shared assets: import T_ParochesV15_BaseColor (sRGB, clamp, stretch-to-POT unless -ParochesV15KeepNPOT)
     and the authored T_ParochesV15_FabricNormal; build M_ParochesV15_Fabric with MaterialEditingLibrary
     (two-sided, roughness .85, metallic 0, mesh UVs + FlipV parameter, Nanite usage); save; read back.
     If they already exist (second target) they are verified by readback and reused.
  3. Meshes: import SM_ParochesV15_Cloth_<suffix> / SM_ParochesV15_Fixings_<suffix> through the reviewed
     legacy OBJ adapter, verify triangles + canonical bounds against the manifest, assign the fabric /
     gold materials to every slot, save, GeometryScript winding check (needs -EnablePlugins=GeometryScripting).
  4. Map: load, verify, no dirty packages, checkpoint the .umap (+ external actor folders) into
     C:/Mikdash/Working-5.8/ReviewCheckpoints/ParochesV15-<stamp>/, snapshot, refuse existing
     RELEASE_ParochesV15_* actors, derive the Kodesh opening from the live partition actors and refuse if it
     differs from the spec, clearance check, HIDE the three old curtain actors (visibility only, reversible),
     spawn RELEASE_ParochesV15_Cloth and RELEASE_ParochesV15_Fixings at the exact spec position,
     verify pre-existing actors did not move, save, reopen, numeric readback (pose, bounds, mesh, materials,
     hidden flags), JSON receipt SourceAssets/sanctuary-detail/ParochesV15/native-import-<stamp>.json.

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_paroches_v15.py"
      -Main50 -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-ParochesV15-Main50-01.log"

  then, in a SECOND serial job (textures/material reused, 48 cm meshes imported, candidate map changed):
      ... -Candidate48 -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-ParochesV15-Candidate48-01.log"

Optional switches (engine command line):
  -ParochesV15ImportOnly            assets only (textures, material, the target's two meshes); no map change.
  -ParochesV15PlaceOnly             assets must already exist and match; place + hide only.
  -ParochesV15AllowUnverifiedWinding place even if the GeometryScript check is unavailable/failed (recorded).
  -ParochesV15KeepNPOT              leave the 1355 x 1161 textures non-power-of-two (no mip maps).

Offline (no engine):  python Scripts/release_paroches_v15.py [-Main50 | -Candidate48] [--json]
  runs every guard that does not need the engine and prints the plan (positions, bounds, hashes).
"""
import hashlib
import importlib.util
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_paroches_v15.spec.json'
TARGET_FLAGS = {'-main50': 'Main50', '-candidate48': 'Candidate48'}


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from the script root')
    return spec


def _load_module(relative, name):
    path = ROOT / relative
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def load_manifest(spec):
    path = ROOT / spec['source']['manifest']
    if not path.exists():
        raise RuntimeError('Offline source set missing; run python Scripts/create_paroches_v15.py --export first: ' + str(path))
    if sha256_of(path) != spec['source']['frozenManifestSha256']:
        raise RuntimeError('geometry-manifest.json hash differs from the frozen spec value; review before importing')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def target_from_args(tokens):
    chosen = [TARGET_FLAGS[t] for t in tokens if t in TARGET_FLAGS]
    if len(chosen) > 1:
        raise RuntimeError('Choose exactly one of -Main50 / -Candidate48')
    return chosen[0] if chosen else None


# --------------------------------------------------------------------------
# Pure plan
# --------------------------------------------------------------------------

def mesh_records(manifest, target_cfg):
    key = target_cfg['meshSuffix']
    by_name = {m['name']: m for m in manifest['meshes']}
    cloth = by_name['SM_ParochesV15_Cloth_' + key]
    fixings = by_name['SM_ParochesV15_Fixings_' + key]
    return cloth, fixings


def plan_target(spec, manifest, name):
    helper = _load_module(spec['placementHelper'], 'release_place_assets')
    cfg = spec['targets'][name]
    opening = cfg['expectedOpening']
    amah = float(cfg['amahCm'])
    W, H = float(cfg['widthCm']), float(cfg['heightCm'])
    if abs(W - spec['size']['amot'][0] * amah) > 1e-9 or abs(H - spec['size']['amot'][1] * amah) > 1e-9:
        raise RuntimeError('%s cloth size %.1f x %.1f is not %d x %d amot of %.1f cm' % (name, W, H, spec['size']['amot'][0], spec['size']['amot'][1], amah))
    tmanifest = manifest['targets'][cfg['meshSuffix']]
    if abs(tmanifest['widthCm'] - W) > 1e-9 or abs(tmanifest['heightCm'] - H) > 1e-9 or abs(tmanifest['amahCm'] - amah) > 1e-9:
        raise RuntimeError('%s: manifest target size differs from the spec' % name)
    expected_location = [opening['xMax'] + float(spec['standoffCm']), 0.0, opening['floorZ'] + float(spec['hemClearanceCm'])]
    if any(abs(expected_location[i] - cfg['location'][i]) > 1e-9 for i in range(3)):
        raise RuntimeError('%s location %s is not wall face + standoff / floor + hem clearance %s' % (name, cfg['location'], expected_location))
    if abs((opening['yMax'] - opening['yMin']) - W) > 1e-6 or abs((opening['lintelZ'] - opening['floorZ']) - H) > 1e-6:
        raise RuntimeError('%s: opening %s is not the cloth size %.0f x %.0f' % (name, opening, W, H))
    cloth, fixings = mesh_records(manifest, cfg)
    yaw = cfg['rotation'][1]
    cloth_world = helper.rotate_box_yaw(cloth['bounds_cm'], cfg['location'], yaw)
    fixings_world = helper.rotate_box_yaw(fixings['bounds_cm'], cfg['location'], yaw)
    covers = (abs(cloth_world['min'][1] - opening['yMin']) < 1e-6 and abs(cloth_world['max'][1] - opening['yMax']) < 1e-6
              and cloth_world['min'][2] >= opening['floorZ'] and cloth_world['max'][2] >= opening['lintelZ']
              and cloth_world['min'][0] > opening['xMax'])
    if not covers:
        raise RuntimeError('%s: planned cloth %s does not cover the opening %s on the Heichal side' % (name, cloth_world, opening))
    return {
        'target': name, 'map': cfg['map'], 'mapFile': str(ROOT / cfg['mapFile']), 'amahCm': amah, 'clothCm': [W, H],
        'arithmetic': tmanifest['arithmetic'], 'expectedOpening': opening, 'location': cfg['location'], 'rotation': cfg['rotation'],
        'derivation': cfg['derivation'],
        'cloth': {'mesh': cloth['name'], 'file': cloth['file'], 'sha256': cloth['sha256'], 'triangles': cloth['triangles'],
                  'localBoundsCm': cloth['bounds_cm'], 'plannedWorldBoundsCm': cloth_world, 'partVolumeSumCm3': cloth['part_volume_sum_cm3']},
        'fixings': {'mesh': fixings['name'], 'file': fixings['file'], 'sha256': fixings['sha256'], 'triangles': fixings['triangles'],
                    'localBoundsCm': fixings['bounds_cm'], 'plannedWorldBoundsCm': fixings_world, 'partVolumeSumCm3': fixings['part_volume_sum_cm3']},
        'clearanceToWallFaceCm': cloth_world['min'][0] - opening['xMax'],
        'hideActors': spec['hideActors']['labels'],
    }


def offline_opening_evidence(spec, name):
    """Cross-check expectedOpening against the receipts already on disk (no engine)."""
    cfg = spec['targets'][name]
    evidence = cfg['offlineOpeningEvidence']
    path = ROOT / evidence['path']
    expected = cfg['expectedOpening']
    tol = float(spec['openingActors']['openingToleranceCm'])
    if not path.exists():
        return {'path': str(path), 'status': 'missing'}
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if evidence['type'] == 'doorsReceipt':
        live = data['openingGeometry']['openings']['Kodesh']
        errors = {k: abs(float(live[k]) - expected[k]) for k in ('xMin', 'xMax', 'yMin', 'yMax', 'floorZ', 'lintelZ')}
    else:
        # candidate receipt rows carry boundsAfter as [origin, extent] (get_actor_bounds), not [min, max]
        rows = {c['name']: c for c in data['changes']}
        names = evidence['actorNames']

        def min_max(row):
            origin, extent = row['boundsAfter']
            return [origin[i] - extent[i] for i in range(3)], [origin[i] + extent[i] for i in range(3)]

        n_min, n_max = min_max(rows[names['shoulderNorth']])
        s_min, s_max = min_max(rows[names['shoulderSouth']])
        l_min, l_max = min_max(rows[names['lintel']])
        live = {'xMin': n_min[0], 'xMax': n_max[0], 'yMin': n_max[1], 'yMax': s_min[1], 'floorZ': min(n_min[2], s_min[2]), 'lintelZ': l_min[2]}
        errors = {k: abs(float(live[k]) - expected[k]) for k in live}
    worst = max(errors.values())
    return {'path': str(path), 'type': evidence['type'], 'live': live, 'errorsCm': errors, 'worstErrorCm': worst,
            'status': 'agrees' if worst <= tol else 'DISAGREES'}


def offline_check(spec=None, target=None):
    spec = spec or load_spec()
    report = {'status': 'started'}
    approval = spec['approval']
    frozen = ROOT / approval['frozenCopy']
    report['approvedHash'] = {'expected': approval['approvedPngSha256'], 'frozenCopy': str(frozen)}
    if not frozen.exists():
        raise RuntimeError('Frozen approved artwork copy missing: ' + str(frozen))
    frozen_sha = sha256_of(frozen)
    report['approvedHash']['frozenCopySha256'] = frozen_sha
    if frozen_sha != approval['approvedPngSha256']:
        raise RuntimeError('STOP: frozen artwork copy is not the approved V15 (hash %s)' % frozen_sha)
    original = Path(approval['approvedSource'])
    if original.exists():
        original_sha = sha256_of(original)
        report['approvedHash']['approvedSourceSha256'] = original_sha
        if original_sha != approval['approvedPngSha256']:
            raise RuntimeError('STOP: the approved source file changed on disk (hash %s)' % original_sha)
    else:
        report['approvedHash']['approvedSourceSha256'] = 'source file absent; frozen copy verified'
    manifest = load_manifest(spec)
    if manifest['approval']['approvedPngSha256'] != approval['approvedPngSha256'] or manifest['image']['sha256'] != approval['approvedPngSha256']:
        raise RuntimeError('Manifest was not built from the approved artwork')
    folder = ROOT / spec['source']['folder']
    files = {}
    for m in manifest['meshes']:
        actual = sha256_of(folder / m['file'])
        files[m['file']] = {'sha256': actual, 'frozen': actual == m['sha256']}
        if actual != m['sha256']:
            raise RuntimeError('Frozen OBJ hash changed: ' + m['file'])
    normal_path = ROOT / spec['source']['normalPng']
    actual = sha256_of(normal_path)
    files[normal_path.name] = {'sha256': actual, 'frozen': actual == manifest['normal']['sha256']}
    if actual != manifest['normal']['sha256']:
        raise RuntimeError('Authored normal PNG hash changed')
    report['sourceFiles'] = files
    report['image'] = {'sizePx': manifest['image']['sizePx'], 'powerOfTwo': manifest['image']['powerOfTwo'], 'aspectErrorPercent': manifest['image']['aspectErrorPercent'],
                       'importNote': manifest['image']['importNote']}
    report['namespaceFolderExistsOnDisk'] = (ROOT / 'Content' / spec['namespace'][len('/Game/'):]).exists()
    report['assetsOnDisk'] = {
        'baseColor': (ROOT / 'Content' / (spec['folders']['textures'][len('/Game/'):] + '/' + spec['textures']['baseColor']['name'] + '.uasset')).exists(),
        'normal': (ROOT / 'Content' / (spec['folders']['textures'][len('/Game/'):] + '/' + spec['textures']['normal']['name'] + '.uasset')).exists(),
        'material': (ROOT / 'Content' / (spec['folders']['materials'][len('/Game/'):] + '/' + spec['material']['name'] + '.uasset')).exists(),
    }
    report['goldMaterialsOnDisk'] = [{'path': c['path'], 'exists': (ROOT / 'Content' / (c['path'][len('/Game/'):] + '.uasset')).exists()} for c in spec['goldMaterialCandidates']]
    names = [target] if target else list(spec['targets'])
    report['targets'] = {}
    for name in names:
        cfg = spec['targets'][name]
        plan = plan_target(spec, manifest, name)
        map_file = ROOT / cfg['mapFile']
        plan['mapFileExists'] = map_file.exists()
        plan['mapSha256'] = sha256_of(map_file) if map_file.exists() else None
        plan['mapMatchesLastKnownSha256'] = plan['mapSha256'] == cfg['lastKnownMapSha256']
        plan['meshAssetsOnDisk'] = {m: (ROOT / 'Content' / (spec['folders']['meshes'][len('/Game/'):] + '/' + m + '.uasset')).exists()
                                    for m in (plan['cloth']['mesh'], plan['fixings']['mesh'])}
        plan['offlineOpeningEvidence'] = offline_opening_evidence(spec, name)
        if plan['offlineOpeningEvidence'].get('status') == 'DISAGREES':
            raise RuntimeError('%s: expectedOpening disagrees with the receipt on disk: %s' % (name, plan['offlineOpeningEvidence']))
        report['targets'][name] = plan
    report['heldWorkUntouched'] = ['Scripts/release_paroches_fabric.py', 'SourceAssets/sanctuary-detail/ParochesFabricV1/', 'ParochesFabricV7/V8/V9', 'ParochesPatternV1']
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side
# --------------------------------------------------------------------------

def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _enum(ue, enum_name, *candidates):
    enum = getattr(ue, enum_name)
    for name in candidates:
        if hasattr(enum, name):
            return getattr(enum, name), name
    raise RuntimeError('%s has none of %s' % (enum_name, candidates))


def _content_uasset(asset_path):
    return ROOT / 'Content' / (asset_path[len('/Game/'):] + '.uasset')


def _xyz(v):
    return [float(v.x), float(v.y), float(v.z)]


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def import_texture(ue, spec, kind, png_path, receipt, keep_npot):
    cfg = spec['textures']
    tex_spec = cfg[kind]
    name = tex_spec['name']
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    task = ue.AssetImportTask()
    for key, value in dict(filename=str(png_path), destination_path=spec['folders']['textures'], destination_name=name,
                           automated=True, replace_existing=False, save=False).items():
        task.set_editor_property(key, value)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.Texture2D):
        raise RuntimeError('Texture import of %s produced %s' % (png_path, [type(o).__name__ for o in objects]))
    tex = objects[0]
    info = {'asset': _asset_path(tex), 'sourcePng': str(png_path), 'sourceSha256': sha256_of(png_path), 'sourceSizePx': None, 'set': {}}
    compression, compression_name = _enum(ue, 'TextureCompressionSettings', tex_spec['compression'])
    tex.set_editor_property('compression_settings', compression)
    tex.set_editor_property('srgb', bool(tex_spec['srgb']))
    address, address_name = _enum(ue, 'TextureAddress', cfg['addressMode'])
    tex.set_editor_property('address_x', address)
    tex.set_editor_property('address_y', address)
    if kind == 'normal':
        tex.set_editor_property('flip_green_channel', bool(tex_spec['flipGreenChannel']))
    pot_mode = 'None (kept non-power-of-two: no mip maps)'
    if not keep_npot:
        try:
            value, pot_name = _enum(ue, 'TexturePowerOfTwoSetting', cfg['powerOfTwoMode'])
            tex.set_editor_property('power_of_two_mode', value)
            pot_mode = pot_name
        except Exception as error:
            pot_mode = 'unset: %r' % (error,)
    try:
        mip, mip_name = _enum(ue, 'TextureMipGenSettings', cfg['mipGenSettings'])
        tex.set_editor_property('mip_gen_settings', mip)
        info['set']['mipGenSettings'] = mip_name
    except Exception as error:
        info['set']['mipGenSettings'] = 'unset: %r' % (error,)
    try:
        tex.update_resource()
    except Exception:
        pass
    if not assets.save_loaded_asset(tex, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + name)
    # readback (setters are not trusted)
    info['readback'] = {
        'srgb': bool(tex.get_editor_property('srgb')),
        'compression': str(tex.get_editor_property('compression_settings')),
        'addressX': str(tex.get_editor_property('address_x')), 'addressY': str(tex.get_editor_property('address_y')),
        'powerOfTwoMode': str(tex.get_editor_property('power_of_two_mode')) if hasattr(tex, 'get_editor_property') else None,
    }
    if kind == 'normal':
        info['readback']['flipGreenChannel'] = bool(tex.get_editor_property('flip_green_channel'))
    size = None
    for getter in ('blueprint_get_size_x', 'get_size_x'):
        if hasattr(tex, getter):
            try:
                size = [int(getattr(tex, getter)()), int(getattr(tex, getter.replace('_x', '_y'))())]
            except Exception:
                size = None
            break
    info['builtSizePx'] = size
    info['powerOfTwoModeRequested'] = pot_mode
    info['compressionRequested'] = compression_name
    info['addressModeRequested'] = address_name
    if info['readback']['srgb'] != bool(tex_spec['srgb']):
        raise RuntimeError('%s sRGB readback %s != %s' % (name, info['readback']['srgb'], tex_spec['srgb']))
    if compression_name.split('_', 1)[1] not in info['readback']['compression'].upper().replace('TEXTURECOMPRESSIONSETTINGS.', ''):
        receipt.setdefault('warnings', []).append('%s compression readback %s (requested %s)' % (name, info['readback']['compression'], compression_name))
    info['uassetSha256'] = sha256_of(_content_uasset(_asset_path(tex)))
    receipt['textures'][kind] = info
    return tex


def verify_texture(ue, spec, kind, tex, receipt):
    tex_spec = spec['textures'][kind]
    info = {'asset': _asset_path(tex), 'reused': True, 'srgb': bool(tex.get_editor_property('srgb')),
            'addressX': str(tex.get_editor_property('address_x')), 'addressY': str(tex.get_editor_property('address_y')),
            'uassetSha256': sha256_of(_content_uasset(_asset_path(tex)))}
    if info['srgb'] != bool(tex_spec['srgb']):
        raise RuntimeError('Existing %s has sRGB %s; expected %s' % (info['asset'], info['srgb'], tex_spec['srgb']))
    receipt['textures'][kind] = info
    return tex


def build_material(ue, spec, base_tex, normal_tex, receipt):
    cfg = spec['material']
    ml = ue.MaterialEditingLibrary
    folder = spec['folders']['materials']
    path = folder + '/' + cfg['name']
    record = {'asset': path, 'nodes': [], 'connections': [], 'status': 'started'}
    receipt['material'] = record
    material = ue.AssetToolsHelpers.get_asset_tools().create_asset(cfg['name'], folder, ue.Material, ue.MaterialFactoryNew())
    if not isinstance(material, ue.Material):
        raise RuntimeError('Material factory failed for ' + path)

    def node(cls, x, y, **props):
        expression = ml.create_material_expression(material, cls, x, y)
        if expression is None:
            raise RuntimeError('create_material_expression failed for %s' % cls.__name__)
        for key, value in props.items():
            expression.set_editor_property(key, value)
        readback = {}
        for key in props:
            try:
                value = expression.get_editor_property(key)
                readback[key] = value if isinstance(value, (int, float, bool, str)) else str(value)
            except Exception as error:
                readback[key] = 'unreadable: %r' % (error,)
        record['nodes'].append({'class': cls.__name__, 'position': [x, y], 'readback': readback})
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

    # UVs: mesh chart (TexCoord 0) with an optional V flip parameter (fallback if the first visual review is upside down)
    texcoord = node(ue.MaterialExpressionTextureCoordinate, -1500, 0, coordinate_index=0)
    flip = node(ue.MaterialExpressionScalarParameter, -1500, 200, parameter_name='FlipV', default_value=float(cfg['flipVDefault']))
    slots = []
    for input_label in ('UV', 'Flip'):
        slot = ue.CustomInput()
        slot.set_editor_property('input_name', input_label)
        slots.append(slot)
    uv_code = 'return float2(UV.x, lerp(UV.y, 1.0 - UV.y, saturate(Flip)));'
    uv = node(ue.MaterialExpressionCustom, -1200, 50, inputs=slots, code=uv_code, output_type=ue.CustomMaterialOutputType.CMOT_FLOAT2,
              description='ParochesV15 whole-panel UV (mesh chart) with FlipV fallback')
    wire(texcoord, '', uv, 'UV')
    wire(flip, '', uv, 'Flip')
    record['uvCode'] = uv_code

    colour_sampler, colour_sampler_name = _enum(ue, 'MaterialSamplerType', spec['textures']['baseColor']['samplerType'])
    base = node(ue.MaterialExpressionTextureSampleParameter2D, -800, -250, parameter_name='BaseColor', texture=base_tex, sampler_type=colour_sampler)
    wire(uv, '', base, 'UVs')
    to_property(base, '', 'MP_BASE_COLOR')

    normal_sampler, normal_sampler_name = _enum(ue, 'MaterialSamplerType', spec['textures']['normal']['samplerType'])
    normal = node(ue.MaterialExpressionTextureSampleParameter2D, -800, 200, parameter_name='FabricNormal', texture=normal_tex, sampler_type=normal_sampler)
    wire(uv, '', normal, 'UVs')
    flat = node(ue.MaterialExpressionConstant3Vector, -500, 100, constant=ue.LinearColor(0.0, 0.0, 1.0, 1.0))
    strength = node(ue.MaterialExpressionScalarParameter, -500, 400, parameter_name='NormalStrength', default_value=float(cfg['normalStrengthDefault']))
    blend = node(ue.MaterialExpressionLinearInterpolate, -250, 250)
    wire(flat, '', blend, 'A')
    wire(normal, '', blend, 'B')
    wire(strength, '', blend, 'Alpha')
    to_property(blend, '', 'MP_NORMAL')

    rough = node(ue.MaterialExpressionConstant, -250, 550, r=float(cfg['roughness']))
    to_property(rough, '', 'MP_ROUGHNESS')
    metallic = node(ue.MaterialExpressionConstant, -250, 650, r=float(cfg['metallic']))
    to_property(metallic, '', 'MP_METALLIC')

    material.set_editor_property('two_sided', bool(cfg['twoSided']))
    nanite_usage = None
    if cfg.get('naniteUsage'):
        try:
            ml.set_base_material_usage(material, ue.MaterialUsage.MATUSAGE_NANITE, True)
            nanite_usage = bool(ml.has_material_usage(material, ue.MaterialUsage.MATUSAGE_NANITE))
        except Exception as error:
            nanite_usage = 'unset: %r' % (error,)
    if ml.get_material_property_input_node(material, ue.MaterialProperty.MP_WORLD_POSITION_OFFSET) is not None:
        raise RuntimeError('WorldPositionOffset unexpectedly connected')
    ml.recompile_material(material)
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + path)
    record['samplerTypes'] = {'baseColor': colour_sampler_name, 'normal': normal_sampler_name}
    record['naniteUsage'] = nanite_usage
    record['readback'] = material_readback(ue, spec, material, base_tex, normal_tex)
    record['uassetSha256'] = sha256_of(_content_uasset(path))
    record['status'] = 'saved'
    return material


def material_readback(ue, spec, material, base_tex=None, normal_tex=None):
    """Readback of the saved material; raises when it does not match the spec."""
    cfg = spec['material']
    ml = ue.MaterialEditingLibrary
    result = {'twoSided': bool(material.get_editor_property('two_sided')), 'inputs': {}}
    if result['twoSided'] != bool(cfg['twoSided']):
        raise RuntimeError('two_sided readback %s != %s' % (result['twoSided'], cfg['twoSided']))
    for prop_name in ('MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_WORLD_POSITION_OFFSET'):
        wired = ml.get_material_property_input_node(material, getattr(ue.MaterialProperty, prop_name))
        result['inputs'][prop_name] = wired.get_class().get_name() if wired else None
    if result['inputs']['MP_BASE_COLOR'] != 'MaterialExpressionTextureSampleParameter2D':
        raise RuntimeError('BaseColor is not a TextureSampleParameter2D: %s' % result['inputs']['MP_BASE_COLOR'])
    if result['inputs']['MP_NORMAL'] != 'MaterialExpressionLinearInterpolate' or result['inputs']['MP_WORLD_POSITION_OFFSET'] is not None:
        raise RuntimeError('Normal/WPO wiring differs: %s' % result['inputs'])
    base_node = ml.get_material_property_input_node(material, ue.MaterialProperty.MP_BASE_COLOR)
    base_texture = base_node.get_editor_property('texture')
    result['baseColorTexture'] = _asset_path(base_texture)
    result['baseColorTextureSrgb'] = bool(base_texture.get_editor_property('srgb')) if base_texture else None
    expected_base = spec['folders']['textures'] + '/' + spec['textures']['baseColor']['name']
    if result['baseColorTexture'] != expected_base or result['baseColorTextureSrgb'] is not True:
        raise RuntimeError('BaseColor texture readback %s sRGB %s' % (result['baseColorTexture'], result['baseColorTextureSrgb']))
    rough_node = ml.get_material_property_input_node(material, ue.MaterialProperty.MP_ROUGHNESS)
    metal_node = ml.get_material_property_input_node(material, ue.MaterialProperty.MP_METALLIC)
    result['roughness'] = float(rough_node.get_editor_property('r')) if isinstance(rough_node, ue.MaterialExpressionConstant) else None
    result['metallic'] = float(metal_node.get_editor_property('r')) if isinstance(metal_node, ue.MaterialExpressionConstant) else None
    if result['roughness'] is None or abs(result['roughness'] - float(cfg['roughness'])) > 1e-6 or result['metallic'] != float(cfg['metallic']):
        raise RuntimeError('Roughness/metallic readback %s / %s' % (result['roughness'], result['metallic']))
    texture_paths = []
    for expression in ml.get_material_expressions(material):
        if isinstance(expression, ue.MaterialExpressionTextureSample):
            texture_paths.append(_asset_path(expression.get_editor_property('texture')))
    result['textures'] = sorted(p for p in texture_paths if p)
    expected_normal = spec['folders']['textures'] + '/' + spec['textures']['normal']['name']
    if set(result['textures']) != {expected_base, expected_normal}:
        raise RuntimeError('Material samples %s, expected the two ParochesV15 textures' % result['textures'])
    try:
        result['naniteUsage'] = bool(ml.has_material_usage(material, ue.MaterialUsage.MATUSAGE_NANITE))
    except Exception as error:
        result['naniteUsage'] = 'unreadable: %r' % (error,)
    return result


def pick_gold(ue, spec, receipt):
    tried = []
    for candidate in spec['goldMaterialCandidates']:
        exists = _content_uasset(candidate['path']).exists()
        material = ue.load_asset(candidate['path']) if exists else None
        ok = isinstance(material, ue.MaterialInterface)
        tried.append({'path': candidate['path'], 'kind': candidate['kind'], 'exists': exists, 'loaded': ok})
        if ok:
            receipt['goldMaterial'] = {'assigned': candidate['path'], 'kind': candidate['kind'], 'tried': tried}
            return material
    raise RuntimeError('No gold material candidate loads: %s' % tried)


def import_mesh(ue, spec, folder, record, material, receipt, key):
    settings = spec['importSettings']
    path = folder / record['file']
    if sha256_of(path) != record['sha256']:
        raise RuntimeError('Frozen OBJ hash changed: ' + record['file'])
    ui = ue.FbxImportUI()
    for k, value in settings['fbxImportUI'].items():
        if k == 'mesh_type_to_import':
            value = getattr(ue.FBXImportType, value)
        ui.set_editor_property(k, value)
    data = ui.get_editor_property('static_mesh_import_data')
    for k, value in settings['staticMeshImportData'].items():
        if k == 'normal_import_method':
            value = getattr(ue.FBXNormalImportMethod, value)
        data.set_editor_property(k, value)
    task = ue.AssetImportTask()
    for k, value in dict(filename=str(path), destination_path=spec['folders']['meshes'], destination_name=record['name'],
                         automated=True, async_=False, replace_existing=False, save=False, options=ui, factory=ue.FbxFactory()).items():
        task.set_editor_property(k, value)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
        raise RuntimeError('Import of %s produced %s' % (record['file'], [type(o).__name__ for o in objects]))
    mesh = objects[0]
    if mesh.get_name() != record['name']:
        raise RuntimeError('Imported name %s differs from %s' % (mesh.get_name(), record['name']))
    info = verify_mesh(ue, spec, mesh, record)
    slots = len(mesh.get_editor_property('static_materials'))     # one slot per OBJ 'g' group (SM_KeruvimStudyV1 lesson)
    if slots < 1:
        raise RuntimeError('%s has no material slots' % record['name'])
    for i in range(slots):
        mesh.set_material(i, material)
    info['materialSlots'] = slots
    info['slotMaterials'] = sorted({_asset_path(mesh.get_material(i)) for i in range(slots)})
    if info['slotMaterials'] != [_asset_path(material)]:
        raise RuntimeError('Material assignment readback for %s: %s' % (record['name'], info['slotMaterials']))
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + record['name'])
    info['uassetSha256'] = sha256_of(_content_uasset(_asset_path(mesh)))
    receipt['meshes'][key] = info
    return mesh


def verify_mesh(ue, spec, mesh, record):
    helper_box = mesh.get_bounding_box()
    actual = {'min': [float(helper_box.min.x), float(helper_box.min.y), float(helper_box.min.z)],
              'max': [float(helper_box.max.x), float(helper_box.max.y), float(helper_box.max.z)]}
    error = max(abs(actual[k][i] - record['bounds_cm'][k][i]) for k in ('min', 'max') for i in range(3))
    triangles = mesh.get_num_triangles(0)
    if triangles != record['triangles']:
        raise RuntimeError('%s triangles %d != manifest %d' % (record['name'], triangles, record['triangles']))
    if error > float(spec['verification']['meshBoundsToleranceCm']):
        raise RuntimeError('%s bounds differ from the manifest by %.4f cm (importer adapter convention?)' % (record['name'], error))
    info = {'asset': _asset_path(mesh), 'file': record['file'], 'triangles': triangles, 'localBoundsCm': actual, 'boundsErrorCm': error}
    # StaticMesh.get_num_uv_channels does not exist in UE 5.8 Python (release_exterior_fixes note); never assumed.
    info['uvChannels'] = int(mesh.get_num_uv_channels(0)) if hasattr(mesh, 'get_num_uv_channels') else 'unverified_in_5_8_python'
    return info


def winding_report(ue, mesh, record, spec):
    check = spec['windingCheck']
    needed = ('GeometryScript_AssetUtils', 'GeometryScript_MeshQueries')
    if not all(hasattr(ue, n) for n in needed):
        return {'status': 'unavailable', 'passed': False, 'reason': 'GeometryScripting not loaded; launch with -EnablePlugins=GeometryScripting'}
    dynamic = ue.DynamicMesh()
    options = ue.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property('apply_build_settings', False)
    options.set_editor_property('request_tangents', False)
    options.set_editor_property('use_build_scale', False)
    lod = ue.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
    if ue.GeometryScriptOutcomePins.SUCCESS not in result:
        return {'status': 'copy_failed', 'passed': False, 'reason': str(result)}
    query = ue.GeometryScript_MeshQueries
    flux, disagreements = 0.0, 0
    count = dynamic.get_triangle_count()
    for tid in range(count):
        positions = [_xyz(v) for v in query.get_triangle_positions(dynamic, tid) if isinstance(v, ue.Vector)]
        if len(positions) != 3:
            return {'status': 'read_failed', 'passed': False, 'reason': 'triangle %d has %d corners' % (tid, len(positions))}
        face = query.get_triangle_face_normal(dynamic, tid)
        normals = [_xyz(v) for v in face if isinstance(v, ue.Vector)] if isinstance(face, tuple) else [_xyz(face)]
        if len(normals) != 1:
            return {'status': 'read_failed', 'passed': False, 'reason': 'no face normal for triangle %d' % tid}
        a, b, c = positions
        ue_cross = _cross(_sub(c, a), _sub(b, a))
        if _dot(ue_cross, normals[0]) < 0:
            disagreements += 1
        area = 0.5 * math.sqrt(_dot(ue_cross, ue_cross))
        centroid = [(a[i] + b[i] + c[i]) / 3.0 for i in range(3)]
        flux += _dot(normals[0], centroid) * area
    signed_volume = flux / 3.0
    expected = record['part_volume_sum_cm3']
    relative = abs(signed_volume - expected) / expected if expected else None
    passed = signed_volume > 0 and disagreements == 0 and relative is not None and relative <= check['maxRelativeVolumeError']
    return {'status': 'checked', 'passed': passed, 'triangles': count, 'signedVolumeUEcm3': signed_volume, 'manifestPartVolumeSumCm3': expected,
            'relativeVolumeError': relative, 'faceNormalVsCrossDisagreements': disagreements,
            'convention': 'UE left-handed face normal cross(C-A, B-A); positive volume means front faces point outward'}


def derive_live_opening(spec, snapshot):
    names = spec['openingActors']
    found = {}
    for role in ('shoulderNorth', 'shoulderSouth', 'lintel'):
        rows = [r for r in snapshot if any(m and m.rsplit('/', 1)[-1] == names[role] for m in r['meshes'])]
        if len(rows) != 1:
            raise RuntimeError('Expected one actor with mesh %s, found %d' % (names[role], len(rows)))
        found[role] = {'label': rows[0]['label'], 'name': rows[0]['name'], 'worldBoundsCm': rows[0]['bounds'], 'pose': rows[0]['pose']}
    north, south, lintel = found['shoulderNorth']['worldBoundsCm'], found['shoulderSouth']['worldBoundsCm'], found['lintel']['worldBoundsCm']
    opening = {'xMin': north['min'][0], 'xMax': north['max'][0], 'yMin': north['max'][1], 'yMax': south['min'][1],
               'floorZ': min(north['min'][2], south['min'][2]), 'lintelZ': lintel['min'][2]}
    return opening, found


def hidden_state(ue, actor):
    """Serialized visibility flags only (same readback as release_kotel_stone_v2 / release_adopt_kotel_photo)."""
    components = actor.get_components_by_class(ue.StaticMeshComponent)
    return {'hidden': bool(actor.get_editor_property('hidden')),
            'componentsVisible': [bool(c.get_editor_property('visible')) for c in components],
            'componentsHiddenInGame': [bool(c.get_editor_property('hidden_in_game')) for c in components]}


def is_hidden(state):
    return state['hidden'] and not any(state['componentsVisible']) and all(state['componentsHiddenInGame'])


def run(target, import_only=False, place_only=False, allow_unverified_winding=False, keep_npot=False):
    import unreal as ue
    if target not in ('Main50', 'Candidate48'):
        raise RuntimeError('Choose the target with -Main50 or -Candidate48')
    if import_only and place_only:
        raise RuntimeError('-ParochesV15ImportOnly and -ParochesV15PlaceOnly exclude each other')
    spec = load_spec()
    offline = offline_check(spec, target)
    manifest = load_manifest(spec)
    helper = _load_module(spec['placementHelper'], 'release_place_assets')
    cfg = spec['targets'][target]
    plan = offline['targets'][target]
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before the run')
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    mesh_paths = {k: spec['folders']['meshes'] + '/' + plan[k]['mesh'] for k in ('cloth', 'fixings')}
    meshes_exist = {k: assets.does_asset_exist(p) for k, p in mesh_paths.items()}
    if place_only and not all(meshes_exist.values()):
        raise RuntimeError('-ParochesV15PlaceOnly needs the imported meshes %s' % mesh_paths)
    if not place_only and any(meshes_exist.values()):
        raise RuntimeError('Existing ParochesV15 mesh assets preserved (use -ParochesV15PlaceOnly): %s' % meshes_exist)
    texture_paths = {k: spec['folders']['textures'] + '/' + spec['textures'][k]['name'] for k in ('baseColor', 'normal')}
    material_path = spec['folders']['materials'] + '/' + spec['material']['name']
    shared_exist = {**{k: assets.does_asset_exist(p) for k, p in texture_paths.items()}, 'material': assets.does_asset_exist(material_path)}
    if any(shared_exist.values()) and not all(shared_exist.values()):
        raise RuntimeError('Partial shared ParochesV15 assets on disk; inspect before rerunning: %s' % shared_exist)

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_folder = ROOT / spec['receiptFolder']
    receipt_path = receipt_folder / (spec['receiptPrefix'] + target + '-' + stamp + '.json')
    if receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(receipt_path))
    map_file = ROOT / cfg['mapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    receipt = {
        'status': 'started', 'stamp': stamp, 'target': target, 'map': cfg['map'], 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == cfg['lastKnownMapSha256'], 'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'manifestSha256': spec['source']['frozenManifestSha256'],
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'approvedPngSha256': spec['approval']['approvedPngSha256'],
        'offlineCheck': offline, 'plan': plan,
        'switches': {'importOnly': import_only, 'placeOnly': place_only, 'allowUnverifiedWinding': allow_unverified_winding, 'keepNPOT': keep_npot},
        'sourceReference': spec['sourceReference'], 'textures': {}, 'material': {}, 'goldMaterial': {}, 'meshes': {}, 'windingCheck': {},
        'openingGeometry': {}, 'clearance': {}, 'hiddenOldCurtain': {}, 'placed': [], 'errors': [], 'mapSaved': False,
        'limitations': list(spec['limitations']),
    }

    def write():
        receipt_folder.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    saved = False
    try:
        # -- 1. shared assets --------------------------------------------------------------
        if shared_exist['material']:
            base_tex = ue.load_asset(texture_paths['baseColor'])
            normal_tex = ue.load_asset(texture_paths['normal'])
            material = ue.load_asset(material_path)
            if not isinstance(material, ue.Material) or not isinstance(base_tex, ue.Texture2D) or not isinstance(normal_tex, ue.Texture2D):
                raise RuntimeError('Existing shared assets did not load as Material / Texture2D')
            verify_texture(ue, spec, 'baseColor', base_tex, receipt)
            verify_texture(ue, spec, 'normal', normal_tex, receipt)
            receipt['material'] = {'asset': material_path, 'reused': True, 'readback': material_readback(ue, spec, material),
                                   'uassetSha256': sha256_of(_content_uasset(material_path))}
        elif place_only:
            raise RuntimeError('-ParochesV15PlaceOnly needs the saved textures and material')
        else:
            base_tex = import_texture(ue, spec, 'baseColor', ROOT / spec['approval']['frozenCopy'], receipt, keep_npot)
            normal_tex = import_texture(ue, spec, 'normal', ROOT / spec['source']['normalPng'], receipt, keep_npot)
            write()
            material = build_material(ue, spec, base_tex, normal_tex, receipt)
        write()

        # -- 2. meshes -----------------------------------------------------------------
        gold = pick_gold(ue, spec, receipt)
        folder = ROOT / spec['source']['folder']
        cloth_rec, fixings_rec = mesh_records(manifest, cfg)
        if place_only:
            mesh_objects = {}
            for key, rec in (('cloth', cloth_rec), ('fixings', fixings_rec)):
                mesh = ue.load_asset(mesh_paths[key])
                if not isinstance(mesh, ue.StaticMesh):
                    raise RuntimeError('Saved mesh missing: ' + mesh_paths[key])
                info = verify_mesh(ue, spec, mesh, rec)
                slots = len(mesh.get_editor_property('static_materials'))
                info['slotMaterials'] = sorted({_asset_path(mesh.get_material(i)) for i in range(slots)})
                expected = [_asset_path(material)] if key == 'cloth' else [_asset_path(gold)]
                if info['slotMaterials'] != expected:
                    raise RuntimeError('%s carries %s, expected %s' % (rec['name'], info['slotMaterials'], expected))
                info['reused'] = True
                receipt['meshes'][key] = info
                mesh_objects[key] = mesh
        else:
            mesh_objects = {'cloth': import_mesh(ue, spec, folder, cloth_rec, material, receipt, 'cloth'),
                            'fixings': import_mesh(ue, spec, folder, fixings_rec, gold, receipt, 'fixings')}
        write()
        winding_ok = True
        for key, rec in (('cloth', cloth_rec), ('fixings', fixings_rec)):
            report = winding_report(ue, mesh_objects[key], rec, spec)
            receipt['windingCheck'][key] = report
            winding_ok = winding_ok and report['passed']
        receipt['windingVerified'] = winding_ok
        write()
        if not winding_ok and not allow_unverified_winding:
            raise RuntimeError('Winding check did not pass; meshes stay saved, nothing placed: %s' % receipt['windingCheck'])
        if import_only:
            receipt['status'] = 'assets_saved_no_map_change'
            return receipt

        # -- 3. map guards + checkpoint ------------------------------------------------------
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.load_level(cfg['map']):
            raise RuntimeError('load_level failed for ' + cfg['map'])
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != cfg['map']:
            raise RuntimeError('Loaded world %s is not the target map' % world.get_outermost().get_name())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present after loading the map; resolve before checkpointed placement')
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + target + '-' + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        external_copied = []
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / cfg['map'][len('/Game/'):]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / cfg['map'][len('/Game/'):])
                external_copied.append(str(external))
        receipt['checkpoint'] = str(checkpoint)
        receipt['oneFilePerActorFoldersCopied'] = external_copied

        placement = helper.Placement(ue, spec)
        placement.world, placement.receipt, placement.receipt_path = world, receipt, receipt_path
        placement.take_snapshot()
        baseline = placement.numeric_baseline(placement.snapshot)
        clashes = [r['label'] for r in placement.snapshot if r['label'].startswith(spec['labelPrefix']) or r['folder'] == spec['folder'] or r['folder'].startswith(spec['folder'] + '/')]
        if clashes:
            raise RuntimeError('Existing ParochesV15 actors preserved; refusing duplicate placement: %s' % clashes[:10])
        for key in ('cloth', 'fixings'):
            rows = placement.actors_with_mesh(mesh_paths[key])
            if rows:
                raise RuntimeError('Mesh %s already present in the map: %s' % (mesh_paths[key], [r['label'] for r in rows]))
        receipt['actorCountBefore'] = len(placement.snapshot)

        # -- 4. live opening must agree with the spec (no invented coordinates) -----------------
        opening, found = derive_live_opening(spec, placement.snapshot)
        tol = float(spec['openingActors']['openingToleranceCm'])
        errors = {k: abs(opening[k] - cfg['expectedOpening'][k]) for k in opening}
        receipt['openingGeometry'] = {'live': opening, 'expected': cfg['expectedOpening'], 'errorsCm': errors, 'actors': found}
        if max(errors.values()) > tol:
            raise RuntimeError('Live Kodesh opening %s differs from the spec %s by more than %.2f cm' % (opening, cfg['expectedOpening'], tol))
        write()

        # -- 5. clearance --------------------------------------------------------------------
        opening_names = set(found[r]['name'] for r in found)
        hide_labels = set(spec['hideActors']['labels'])
        overlaps = []
        for key in ('cloth', 'fixings'):
            planned = plan[key]['plannedWorldBoundsCm']
            for row in placement.snapshot:
                if not row['meshes'] or row['name'] in opening_names or row['label'] in hide_labels:
                    continue
                if helper.boxes_overlap_volume(planned, row['bounds']):
                    overlaps.append({'with': key, 'label': row['label'], 'folder': row['folder'], 'bounds': row['bounds']})
        union_limit = float(spec['clearance']['unionAabbVolumeCm3'])
        for o in overlaps:
            b = o['bounds']
            o['aabbVolumeCm3'] = (b['max'][0] - b['min'][0]) * (b['max'][1] - b['min'][1]) * (b['max'][2] - b['min'][2])
            o['measuredArchitecture'] = any(o['folder'].startswith(p) for p in spec['clearance']['refuseFolderPrefixes'])
            o['unionAabbNotEvaluated'] = o['aabbVolumeCm3'] > union_limit
        refused = [o for o in overlaps if o['measuredArchitecture'] and not o['unionAabbNotEvaluated']]
        receipt['clearance'] = {'overlaps': overlaps, 'refused': refused, 'excludedByName': sorted(opening_names), 'excludedLabels': sorted(hide_labels),
                                'rule': spec['clearance']['rule']}
        if refused:
            raise RuntimeError('Planned paroches overlaps measured architecture: %s' % refused[:5])

        # -- 6. hide the old curtain (visibility only) ----------------------------------------
        hidden = {}
        for label in spec['hideActors']['labels']:
            rows = [r for r in placement.snapshot if r['label'] == label]
            if len(rows) != 1:
                raise RuntimeError('Expected one actor labelled %s, found %d' % (label, len(rows)))
            row = rows[0]
            if not any(spec['hideActors']['meshNameMustContain'] in (m or '').rsplit('/', 1)[-1] for m in row['meshes']):
                raise RuntimeError('%s does not carry a Paroches mesh: %s' % (label, row['meshes']))
            actor = row['actor']
            before = hidden_state(ue, actor)
            actor.modify(True)
            actor.set_editor_property('hidden', True)
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                component.modify(True)
                component.set_visibility(False, True)
                component.set_hidden_in_game(True, True)
            tags = list(actor.get_editor_property('tags'))
            actor.set_editor_property('tags', tags + [ue.Name('ParochesV15HiddenOldCurtain')])
            after = hidden_state(ue, actor)
            if not is_hidden(after):
                raise RuntimeError('Hiding %s did not read back: %s' % (label, after))
            hidden[label] = {'name': row['name'], 'meshes': row['meshes'], 'pose': row['pose'], 'worldBoundsCm': row['bounds'], 'before': before, 'after': after}
        receipt['hiddenOldCurtain'] = {'actors': hidden, 'method': spec['hideActors']['method'], 'restoreRule': spec['hideActors']['restoreRule']}
        write()

        # -- 7. spawn ------------------------------------------------------------------------
        spawned = []
        for key in ('cloth', 'fixings'):
            label = spec['labelPrefix'] + key.capitalize()
            actor, component = placement.spawn_static(mesh_objects[key], cfg['location'], cfg['rotation'], label, spec['folder'],
                                                      spec['collisionProfile'], ['ParochesV15_' + key, 'ParochesV15_' + target])
            spawned.append(actor)
            bounds = helper._actor_bounds(actor)
            error = helper.box_error(bounds, plan[key]['plannedWorldBoundsCm'])
            entry = {'label': label, 'mesh': mesh_paths[key], 'location': cfg['location'], 'rotation': cfg['rotation'], 'scale': [1.0, 1.0, 1.0],
                     'plannedWorldBoundsCm': plan[key]['plannedWorldBoundsCm'], 'placedWorldBoundsCm': bounds, 'boundsErrorCm': error,
                     'collisionProfile': str(component.get_collision_profile_name()),
                     'materials': sorted({_asset_path(component.get_material(i)) for i in range(component.get_num_materials())})}
            receipt['placed'].append(entry)
            if error > float(spec['verification']['staticBoundsToleranceCm']):
                placement.destroy_all(spawned)
                raise RuntimeError('%s placed bounds differ from the plan by %.4f cm' % (label, error))
        write()
        current = placement.numeric_baseline(placement.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])

        # -- 8. save, reopen, read back ---------------------------------------------------------
        if not levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha256_of(map_file)
        write()
        if not levels.load_level(cfg['map']):
            raise RuntimeError('Reopen failed')
        placement.world = editor.get_editor_world()
        reopened = placement.take_snapshot()
        reopened_numeric = placement.numeric_baseline(reopened)
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])
        verify = spec['verification']
        readback = []
        for entry in receipt['placed']:
            matching = [r for r in reopened if r['label'] == entry['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (entry['label'], len(matching)))
            row = matching[0]
            close, pose_error = helper._pose_close(row['pose'], entry['location'], entry['rotation'], entry['scale'], verify['transformToleranceCm'])
            bounds_error = helper.box_error(row['bounds'], entry['plannedWorldBoundsCm'])
            component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
            materials = sorted({_asset_path(component.get_material(i)) for i in range(component.get_num_materials())})
            readback.append({'label': entry['label'], 'folder': row['folder'], 'meshPath': row['meshes'], 'pose': row['pose'], 'worldBoundsCm': row['bounds'],
                             'poseErrorCm': pose_error, 'boundsErrorCm': bounds_error, 'collisionProfile': str(component.get_collision_profile_name()),
                             'materials': materials, 'hiddenState': hidden_state(ue, row['actor'])})
            if row['meshes'] != [entry['mesh']] or materials != entry['materials']:
                raise RuntimeError('Reopened mesh/material differ for ' + entry['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)' % (entry['label'], pose_error, bounds_error))
        hidden_after = {}
        for label in spec['hideActors']['labels']:
            rows = [r for r in reopened if r['label'] == label]
            if len(rows) != 1:
                raise RuntimeError('Hidden actor %s missing after reopen' % label)
            state = hidden_state(ue, rows[0]['actor'])
            hidden_after[label] = state
            if not is_hidden(state):
                raise RuntimeError('%s is not hidden after reopen: %s' % (label, state))
        receipt['reopenedReadback'] = {'placed': readback, 'hiddenOldCurtain': hidden_after}
        receipt['actorCountAfter'] = len(reopened)
        receipt['status'] = 'paroches_v15_saved_reopened_visual_acceptance_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif receipt['meshes'] or receipt['textures'] or receipt['material']:
            receipt['status'] = 'failed_partial_assets_preserved_map_unchanged' if not place_only else 'failed_before_save_map_unchanged'
        else:
            receipt['status'] = 'failed_before_import_nothing_changed'
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(sha256_of(helper.disk_path(m, 'umap')) == v for m, v in protected.items())
        receipt['placedActorCount'] = len(receipt['placed'])
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
    return 'release_paroches_v15.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    tokens = command_line.split()
    try:
        target = target_from_args(tokens)
        receipt = run(target, import_only='-parochesv15importonly' in tokens, place_only='-parochesv15placeonly' in tokens,
                      allow_unverified_winding='-parochesv15allowunverifiedwinding' in tokens, keep_npot='-parochesv15keepnpot' in tokens)
        ue.log('release_paroches_v15 %s: %s placed %s winding_ok %s' % (target, receipt['status'], receipt.get('placedActorCount'), receipt.get('windingVerified')))
    except Exception as error:
        ue.log_error('release_paroches_v15 failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


def _offline_main():
    tokens = [t.lower() for t in sys.argv[1:]]
    target = target_from_args(tokens)
    report = offline_check(target=target)
    if '--json' in tokens:
        print(json.dumps(report, indent=2))
        return
    print('release_paroches_v15 offline check: ' + report['status'])
    print('approved V15 hash: frozen copy %s | source %s' % (report['approvedHash']['frozenCopySha256'][:16], str(report['approvedHash']['approvedSourceSha256'])[:16]))
    print('image %s px, powerOfTwo=%s, aspect error %.3f%%' % (report['image']['sizePx'], report['image']['powerOfTwo'], report['image']['aspectErrorPercent']))
    print('namespace on disk: %s; shared assets: %s' % (report['namespaceFolderExistsOnDisk'], report['assetsOnDisk']))
    for name, plan in report['targets'].items():
        print('-- %s  %s' % (name, plan['arithmetic']))
        print('   map %s' % plan['map'])
        print('   map sha %s matchesLastKnown=%s' % (str(plan['mapSha256'])[:16], plan['mapMatchesLastKnownSha256']))
        print('   opening %s' % json.dumps(plan['expectedOpening']))
        print('   evidence %s -> %s (worst %.4f cm)' % (plan['offlineOpeningEvidence'].get('type'), plan['offlineOpeningEvidence'].get('status'), plan['offlineOpeningEvidence'].get('worstErrorCm', -1)))
        print('   spawn %s at %s yaw %s' % (plan['cloth']['mesh'], plan['location'], plan['rotation'][1]))
        print('   cloth world bounds %s' % json.dumps(plan['cloth']['plannedWorldBoundsCm']))
        print('   fixings world bounds %s' % json.dumps(plan['fixings']['plannedWorldBoundsCm']))
        print('   clearance to wall face %.2f cm; hide %s' % (plan['clearanceToWallFaceCm'], plan['hideActors']))
        print('   mesh assets on disk %s' % plan['meshAssetsOnDisk'])
    print('run order: -Main50 first (creates shared textures/material), then -Candidate48 (reuses them); both -EnablePlugins=GeometryScripting -unattended -nullrhi, serial.')


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        _offline_main()
elif _invoked_as_native_script():
    _main()

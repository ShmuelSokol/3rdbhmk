"""Import-only paving review. run() is offline; root explicitly opts into import."""
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'SourceAssets/visual-review/JerusalemPavingV1'
DEST = '/Game/MikdashV3/MaterialReview/JerusalemPavingV2'
MATERIAL = DEST + '/M_JerusalemPaving_500cm'
TEXTURE = DEST + '/T_JerusalemPaving_BaseColor'
PLATFORM = '/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface'
FROZEN = 'd3c9f895f72105e812654550e2fc05c29b0e769ebce6026ecf31fa32a71921f6'
UV_CODE = 'return float2(P.x, P.y) / 500.0;'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def helper(name):
    spec = importlib.util.spec_from_file_location('paving_' + name, ROOT / 'Scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preflight():
    png = FOLDER / 'jerusalem-paving-albedo.png'
    receipt = FOLDER / 'source-receipt.json'
    source = json.loads(receipt.read_text(encoding='utf-8-sig'))
    if png.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n' or sha(png) != FROZEN or source['sha256'] != FROZEN:
        raise RuntimeError('Frozen paving PNG mismatch')
    if png.stat().st_size != source['bytes'] or source['intendedTileCm'] != 500:
        raise RuntimeError('Source size/tile declaration changed')
    return dict(status='OFFLINE_READY_IMPORT_NOT_RUN', sourceSha256=FROZEN,
                sourceReceiptSha256=sha(receipt), material=MATERIAL, texture=TEXTURE,
                tileCm=500, addressing='MIRROR_XY', allowedReviewMesh=PLATFORM,
                mapMutation=False, normal='None; no invented measured height', roughness=.8,
                interpretation=source['interpretation'], visualAcceptance='PENDING_ROOT_PIE_AB')


def graph_snapshot(u, material):
    ml = u.MaterialEditingLibrary
    expressions = list(ml.get_material_expressions(material))
    rows = {}
    kinds = {}
    for n in expressions:
        kind = n.get_class().get_name()
        kinds.setdefault(kind, []).append(n)
        row = dict(kind=kind, inputs=[x.get_name() if x else None for x in ml.get_inputs_for_material_expression(material, n)])
        if isinstance(n, u.MaterialExpressionCustom):
            row['code'] = n.get_editor_property('Code')
            row['outputType'] = str(n.get_editor_property('OutputType'))
            row['inputNames'] = [str(x.get_editor_property('InputName')) for x in n.get_editor_property('Inputs')]
        if isinstance(n, u.MaterialExpressionConstant):
            row['value'] = n.get_editor_property('R')
        if isinstance(n, u.MaterialExpressionTextureSample):
            t = n.get_editor_property('Texture')
            row['texture'] = t.get_path_name().split('.')[0]
            row['srgb'] = t.get_editor_property('srgb')
            row['address'] = [str(t.get_editor_property(k)) for k in ('address_x', 'address_y')]
            row['powerOfTwoMode'] = str(t.get_editor_property('power_of_two_mode'))
        rows[n.get_name()] = row
    expected = {'MaterialExpressionWorldPosition':1, 'MaterialExpressionCustom':1,
                'MaterialExpressionTextureSample':1, 'MaterialExpressionConstant':2}
    if {k:len(v) for k,v in kinds.items()} != expected:
        raise RuntimeError('Unexpected material graph nodes')
    world = kinds['MaterialExpressionWorldPosition'][0].get_name()
    uv = kinds['MaterialExpressionCustom'][0].get_name()
    sample = kinds['MaterialExpressionTextureSample'][0].get_name()
    if rows[uv]['code'] != UV_CODE or rows[uv]['inputNames'] != ['P'] or rows[uv]['inputs'] != [world]:
        raise RuntimeError('World XY mapping link mismatch')
    if rows[uv]['outputType'] != str(u.CustomMaterialOutputType.CMOT_FLOAT2):
        raise RuntimeError('UV output type mismatch')
    t = rows[sample]
    if t['texture'] != TEXTURE or not t['srgb'] or t['address'] != [str(u.TextureAddress.TA_MIRROR)] * 2 or uv not in t['inputs']:
        raise RuntimeError('Texture/sRGB/address/UV mismatch')
    if t['powerOfTwoMode'] != str(u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO):
        raise RuntimeError('Native mip-build resampling policy changed')
    outputs = {}
    for key in ('MP_BASE_COLOR', 'MP_ROUGHNESS', 'MP_METALLIC'):
        n = ml.get_material_property_input_node(material, getattr(u.MaterialProperty, key))
        if not n:
            raise RuntimeError('Missing material output ' + key)
        outputs[key] = n.get_name()
    if outputs['MP_BASE_COLOR'] != sample or abs(rows[outputs['MP_ROUGHNESS']].get('value', -1)-.8) > 1e-6 or rows[outputs['MP_METALLIC']].get('value') != 0:
        raise RuntimeError('Base/roughness/metal output mismatch')
    if ml.get_material_property_input_node(material, u.MaterialProperty.MP_NORMAL):
        raise RuntimeError('Unexpected normal override')
    if not ml.has_material_usage(material, u.MaterialUsage.MATUSAGE_NANITE):
        raise RuntimeError('Nanite usage not persisted')
    return dict(nodes=rows, outputs=outputs, nanite=True,
                blendMode=str(material.get_editor_property('blend_mode')))


def run(import_assets=False):
    report = preflight()
    if not import_assets:
        return report
    import unreal as u
    if Path(u.SystemLibrary.get_project_directory()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Live or dirty editor; import refused')
    if u.EditorAssetLibrary.does_directory_exist(DEST) or (ROOT / 'Content' / DEST[6:]).exists():
        raise RuntimeError('Fresh namespace required; never overwrite a partial import')
    units = helper('release_amah48_candidate')
    protected = units.offline_plan()
    # Protect main and the currently loaded editor map without loading/changing either.
    files = {str(units.disk(protected['source'])): protected['sourceSha256']}
    world = editor.get_editor_world()
    if world:
        loaded = world.get_path_name().split('.')[0]
        if loaded.startswith('/Game/') and units.disk(loaded).exists():
            files[str(units.disk(loaded))] = sha(units.disk(loaded))
    h = helper('release_resident_crowd')
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    baseline = h._scene_snapshot(u, actors)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('JerusalemPaving-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    # No existing asset or map is edited, so the checkpoint records hashes only.
    (checkpoint / 'protected.json').write_text(json.dumps(protected, indent=2), encoding='utf8')
    receipt = FOLDER / ('native-import-' + stamp + '.json')
    report.update(status='STARTED', checkpoint=str(checkpoint), mainSha256Before=protected['sourceSha256'])
    def write():
        receipt.write_text(json.dumps(report, indent=2), encoding='utf8')
    write()
    try:
        if preflight()['sourceReceiptSha256'] != report['sourceReceiptSha256'] or units.offline_plan() != protected:
            raise RuntimeError('Protected inputs changed before import')
        task = u.AssetImportTask()
        task.filename = str(FOLDER / 'jerusalem-paving-albedo.png')
        task.destination_path = DEST
        task.destination_name = TEXTURE.rsplit('/',1)[1]
        task.automated = True
        task.replace_existing = False
        task.save = False
        tools = u.AssetToolsHelpers.get_asset_tools()
        tools.import_asset_tasks([task])
        imported = list(task.get_objects())
        if len(imported) != 1 or not isinstance(imported[0], u.Texture2D):
            raise RuntimeError('Expected exactly one Texture2D')
        texture = imported[0]
        texture.set_editor_property('srgb', True)
        # Generated source is1254px; native build resampling enables mipmaps.
        # Preserve the original PNG unchanged, never pad borders into the tile.
        texture.set_editor_property('power_of_two_mode', u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO)
        for key in ('address_x', 'address_y'):
            texture.set_editor_property(key, u.TextureAddress.TA_MIRROR)
        material = tools.create_asset(MATERIAL.rsplit('/',1)[1], DEST, u.Material, u.MaterialFactoryNew())
        if not material:
            raise RuntimeError('Material creation failed')
        material.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
        ml = u.MaterialEditingLibrary
        world_node = ml.create_material_expression(material, u.MaterialExpressionWorldPosition)
        uv = ml.create_material_expression(material, u.MaterialExpressionCustom)
        uv.set_editor_property('Code', UV_CODE)
        uv.set_editor_property('OutputType', u.CustomMaterialOutputType.CMOT_FLOAT2)
        pin = u.CustomInput()
        pin.set_editor_property('InputName', 'P')
        uv.set_editor_property('Inputs', [pin])
        sample = ml.create_material_expression(material, u.MaterialExpressionTextureSample)
        sample.set_editor_property('Texture', texture)
        if not ml.connect_material_expressions(world_node, '', uv, 'P') or not ml.connect_material_expressions(uv, '', sample, 'UVs'):
            raise RuntimeError('UV wiring failed')
        rough = ml.create_material_expression(material, u.MaterialExpressionConstant)
        rough.set_editor_property('R', .8)
        metal = ml.create_material_expression(material, u.MaterialExpressionConstant)
        metal.set_editor_property('R', 0.0)
        for n, prop in ((sample,u.MaterialProperty.MP_BASE_COLOR), (rough,u.MaterialProperty.MP_ROUGHNESS), (metal,u.MaterialProperty.MP_METALLIC)):
            if not ml.connect_material_property(n, '', prop):
                raise RuntimeError('Material output wiring failed')
        ml.set_base_material_usage(material, u.MaterialUsage.MATUSAGE_NANITE, True)
        compile_errors = list(ml.recompile_material(material))
        report['materialCompileErrors'] = compile_errors
        if compile_errors:
            raise RuntimeError('Material compiler: ' + repr(compile_errors))
        before = graph_snapshot(u, material)
        for asset in (texture, material):
            if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
                raise RuntimeError('New asset save failed')
        after = graph_snapshot(u, u.EditorAssetLibrary.load_asset(MATERIAL))
        if after != before:
            raise RuntimeError('Saved graph readback mismatch')
        report.update(status='IMPORTED_ONLY_VISUAL_PENDING', savedGraph=after,
                      reloadLimit='load_asset readback; fresh-process disk reload and PIE A/B pending',
                      assets={p:sha(ROOT/'Content'/(p[6:]+'.uasset')) for p in (TEXTURE,MATERIAL)})
    except Exception as error:
        report.update(status='FAILED_PRESERVE_PARTIAL_NAMESPACE', error=repr(error))
        raise
    finally:
        try:
            report['protectedUnchanged'] = (units.offline_plan() == protected and
                all(sha(Path(p)) == value for p,value in files.items()) and
                preflight()['sourceReceiptSha256'] == report['sourceReceiptSha256'] and
                h._scene_snapshot(u, actors) == baseline)
        except Exception as error:
            report['protectedUnchanged'] = False
            report['protectionError'] = repr(error)
        if not report['protectedUnchanged']:
            report['status'] = 'FAILED_PROTECTED_HASH_OR_SCENE_MISMATCH'
        write()
        if not report['protectedUnchanged']:
            raise RuntimeError('Protected map/source/scene changed; see receipt')
    return report

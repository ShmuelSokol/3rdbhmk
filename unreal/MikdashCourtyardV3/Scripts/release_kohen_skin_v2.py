"""Create fresh skin-study assets, or verify them in a separate Unreal process.

Asset-only: never loads a map or changes the approved head/material binding.
Use -KohenSkinVerify for readback. Render approval and mesh adoption are separate.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'SourceAssets/characters-review/KohenSkinV2'
FOLDER = '/Game/Characters/KohenSkinV2Study03'
MASTER = FOLDER + '/M_KohenWalter_Skin_V2'
MEL = ue.MaterialEditingLibrary
ASSETS = ue.EditorAssetLibrary


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sources():
    manifest = json.loads((REVIEW / 'textures/manifest.json').read_text())
    for row in manifest['textures']:
        path = REVIEW / 'textures' / row['file']
        require(hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256'],
                'Source hash mismatch: ' + row['file'])
    return manifest['textures']


def create(rows):
    require(not ASSETS.does_directory_exist(FOLDER), 'Fresh namespace required: ' + FOLDER)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    textures = {}
    for row in rows:
        name = Path(row['file']).stem
        task = ue.AssetImportTask()
        for key, value in dict(filename=str(REVIEW / 'textures' / row['file']),
                               destination_path=FOLDER, destination_name=name,
                               automated=True, replace_existing=False, save=False).items():
            task.set_editor_property(key, value)
        tools.import_asset_tasks([task])
        texture = ue.load_asset(FOLDER + '/' + name)
        require(isinstance(texture, ue.Texture2D), 'Texture import failed: ' + name)
        texture.set_editor_property('srgb', row['sRGB'])
        texture.set_editor_property('compression_settings',
            ue.TextureCompressionSettings.TC_NORMALMAP if row['role'] == 'Normal'
            else ue.TextureCompressionSettings.TC_DEFAULT)
        # These are original Unreal preset pixels, not the Y-up authored resident maps.
        texture.set_editor_property('flip_green_channel', False)
        require(ASSETS.save_loaded_asset(texture, only_if_is_dirty=False), 'Texture save failed')
        textures[row['role']] = texture

    mat = tools.create_asset('M_KohenWalter_Skin_V2', FOLDER, ue.Material, ue.MaterialFactoryNew())
    require(mat is not None, 'Material creation failed')
    mat.set_editor_property('used_with_skeletal_mesh', True)
    mat.set_editor_property('used_with_morph_targets', True)
    mat.set_editor_property('shading_model', ue.MaterialShadingModel.MSM_SUBSURFACE)

    def node(cls, x=0, y=0):
        return MEL.create_material_expression(mat, cls, x, y)

    def connect(a, output, b, pin):
        require(MEL.connect_material_expressions(a, output, b, pin),
                'Connection failed: ' + pin + '; available=' +
                str(MEL.get_material_expression_input_names(b)))

    def prop(a, output, name):
        require(MEL.connect_material_property(a, output, name), 'Material property connection failed')

    def scalar(name, value, y):
        n = node(ue.MaterialExpressionScalarParameter, -650, y)
        n.set_editor_property('parameter_name', name)
        n.set_editor_property('default_value', value)
        return n

    def sample(role, y):
        n = node(ue.MaterialExpressionTextureSampleParameter2D, -1200, y)
        n.set_editor_property('parameter_name', role)
        n.set_editor_property('texture', textures[role])
        n.set_editor_property('sampler_type', ue.MaterialSamplerType.SAMPLERTYPE_NORMAL
                              if role == 'Normal' else ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        return n

    # Keep the approved face vertex colors and any later reviewed neck color correction.
    vc = node(ue.MaterialExpressionVertexColor, -1200, -500)
    rgb = node(ue.MaterialExpressionComponentMask, -1000, -500)
    for channel in ('r', 'g', 'b'):
        rgb.set_editor_property(channel, True)
    rgb.set_editor_property('a', False)
    connect(vc, '', rgb, '')
    decode = node(ue.MaterialExpressionPower, -800, -500)
    connect(rgb, '', decode, 'Base')
    # MaterialGraphNode::GetShortenPinName maps Exponent to Exp in UE 5.8.
    connect(scalar('VCDecodeExponent', 1.0, -350), '', decode, 'Exp')
    prop(decode, '', ue.MaterialProperty.MP_BASE_COLOR)
    normal = sample('Normal', 0)
    prop(normal, 'RGB', ue.MaterialProperty.MP_NORMAL)
    cavity = sample('Cavity', 400)

    # Epic's inspected packed paths: R concavity, G convexity, B micro detail.
    # Preserve separate adjustable multipliers, never reinterpret packed RGB as AO.
    def adjust(base, channel, name, amount, y):
        mul = node(ue.MaterialExpressionMultiply, -400, y)
        connect(base, '', mul, 'A')
        connect(scalar(name, amount, y + 100), '', mul, 'B')
        mix = node(ue.MaterialExpressionLinearInterpolate, -200, y)
        connect(base, '', mix, 'A')
        connect(mul, '', mix, 'B')
        connect(cavity, channel, mix, 'Alpha')
        return mix

    rough = scalar('Roughness', .55, 650)
    rough = adjust(rough, 'R', 'ConcavityRoughnessMultiply', 1.10, 800)
    rough = adjust(rough, 'G', 'ConvexityRoughnessMultiply', .95, 1050)
    rough = adjust(rough, 'B', 'MicroRoughnessMultiply', 1.08, 1300)
    clamp = node(ue.MaterialExpressionSaturate, 0, 1300)
    connect(rough, '', clamp, '')
    prop(clamp, '', ue.MaterialProperty.MP_ROUGHNESS)
    spec = scalar('Specular', .35, 1600)
    spec = adjust(spec, 'R', 'ConcavitySpecularMultiply', .8, 1750)
    prop(spec, '', ue.MaterialProperty.MP_SPECULAR)
    sss = node(ue.MaterialExpressionVectorParameter, -400, 2050)
    sss.set_editor_property('parameter_name', 'SubsurfaceColor')
    sss.set_editor_property('default_value', ue.LinearColor(.62, .20, .11, 1))
    prop(sss, '', ue.MaterialProperty.MP_SUBSURFACE_COLOR)
    prop(scalar('SubsurfaceOpacity', .85, 2250), '', ue.MaterialProperty.MP_OPACITY)
    MEL.recompile_material(mat)
    require(ASSETS.save_loaded_asset(mat, only_if_is_dirty=False), 'Material save failed')


def verify(rows):
    result = {'textures': [], 'material': MASTER}
    for row in rows:
        path = FOLDER + '/' + Path(row['file']).stem
        tex = ue.load_asset(path)
        require(isinstance(tex, ue.Texture2D), 'Missing texture: ' + path)
        expected = (ue.TextureCompressionSettings.TC_NORMALMAP if row['role'] == 'Normal'
                    else ue.TextureCompressionSettings.TC_DEFAULT)
        require(tex.get_editor_property('srgb') == row['sRGB'], 'Wrong sRGB: ' + path)
        require(tex.get_editor_property('compression_settings') == expected, 'Wrong compression')
        require(not tex.get_editor_property('flip_green_channel'), 'Unexpected normal flip')
        result['textures'].append({'path': path, 'sourceSha256': row['sha256'],
                                  'sRGB': row['sRGB'], 'compression': str(expected)})
    mat = ue.load_asset(MASTER)
    require(isinstance(mat, ue.Material), 'Missing skin material')
    require(mat.get_editor_property('used_with_skeletal_mesh'), 'Skeletal usage missing')
    require(mat.get_editor_property('shading_model') == ue.MaterialShadingModel.MSM_SUBSURFACE,
            'Wrong shading model')
    result['propertyInputs'] = {}
    for name in ('BASE_COLOR', 'NORMAL', 'ROUGHNESS', 'SPECULAR', 'SUBSURFACE_COLOR', 'OPACITY'):
        pin = getattr(ue.MaterialProperty, 'MP_' + name)
        value = MEL.get_material_property_input_node(mat, pin)
        require(value is not None, 'Unconnected ' + name)
        result['propertyInputs'][name] = value.get_class().get_name()
    require(MEL.get_material_property_input_node(mat, ue.MaterialProperty.MP_AMBIENT_OCCLUSION)
            is None, 'Packed cavity must not be wired to AO')
    expressions = list(MEL.get_material_expressions(mat))
    parameters = {}
    cavity_mix_channels = []
    samplers = {}
    for node in expressions:
        if isinstance(node, ue.MaterialExpressionTextureSampleParameter2D):
            name = str(node.get_editor_property('parameter_name'))
            require(name in ('Normal', 'Cavity'), 'Unexpected texture sampler')
            texture = node.get_editor_property('texture')
            expected_path = FOLDER + '/T_KohenWalter_' + name + '_V2'
            require(texture and texture.get_path_name().split('.')[0] == expected_path,
                    'Wrong sampled texture: ' + name)
            expected_sampler = (ue.MaterialSamplerType.SAMPLERTYPE_NORMAL if name == 'Normal'
                                else ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            require(node.get_editor_property('sampler_type') == expected_sampler, 'Wrong sampler type')
            samplers[name] = texture.get_path_name()
        if isinstance(node, ue.MaterialExpressionScalarParameter):
            parameters[str(node.get_editor_property('parameter_name'))] = float(
                node.get_editor_property('default_value'))
        if isinstance(node, ue.MaterialExpressionLinearInterpolate):
            inputs = list(MEL.get_inputs_for_material_expression(mat, node))
            require(len(inputs) == 3 and inputs[2] is not None, 'Unconnected cavity blend')
            source = inputs[2]
            require(isinstance(source, ue.MaterialExpressionTextureSampleParameter2D)
                    and str(source.get_editor_property('parameter_name')) == 'Cavity',
                    'Wrong cavity blend alpha source')
            cavity_mix_channels.append(MEL.get_input_node_output_name_for_material_expression(node, source))
    require(sorted(cavity_mix_channels) == ['B', 'G', 'R', 'R'], 'Wrong packed cavity channels')
    require(set(samplers) == {'Normal', 'Cavity'}, 'Missing skin texture samplers')
    base = MEL.get_material_property_input_node(mat, ue.MaterialProperty.MP_BASE_COLOR)
    require(isinstance(base, ue.MaterialExpressionPower), 'Missing vertex-color decode')
    decode_inputs = list(MEL.get_inputs_for_material_expression(mat, base))
    require(len(decode_inputs) == 2 and isinstance(decode_inputs[1], ue.MaterialExpressionScalarParameter)
            and str(decode_inputs[1].get_editor_property('parameter_name')) == 'VCDecodeExponent',
            'Decode exponent parameter is disconnected')
    require(abs(parameters.get('VCDecodeExponent', 0) - 1.0) < .0001, 'Wrong decode exponent')
    result.update(parameters=parameters, cavityBlendChannels=cavity_mix_channels, samplers=samplers)
    return result


def run():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    readback = '-KohenSkinVerify' in ue.SystemLibrary.get_command_line()
    report = {'status': 'started', 'mode': 'verify' if readback else 'create',
              'scope': 'Asset-only skin study; no mesh binding, map edit or rendered acceptance.'}
    try:
        rows = sources()
        if not readback:
            create(rows)
        report.update(verify(rows))
        report['status'] = 'native-readback-passed' if readback else 'created-readback-pending'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        (REVIEW / ('material-' + report['mode'] + '-' + stamp + '.json')).write_text(
            json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    run()

"""Precinct retaining faces: a distance-blended MACRO layer, plus hiding the Heikhal ceiling soot decal.

WHY THE RETAINING FACES WERE FEATURELESS (measured 11 Sep 2026, see PrecinctMacroV1/inspect-*.json)
Not a fallback, not a wrong instance, not the runtime build. MI_PrecinctPlaza_Ashlar resolves to the live
V5b Herodian set exactly (T_HerodianV5b_Ashlar_*, TilingCm 300, usage Nanite + ISM true) and the enclosure's
PlazaAshlarMaterial is that instance. The close-up tile is 300 cm and holds nothing larger than 3 m. The
aerial camera sees the face at ~0.5-1.5 m per pixel, which selects mip 9-11 of the 2048 tile (4, 2, 1
texels per tile); mip 11 is one colour by construction. The frame measured row-profile std 0.017-0.035
over whole faces: no course signal survives. Close-up detail had no far-field equivalent.

WHAT THIS DOES
  -PMApply              ASSET-ONLY. Imports T_PrecinctMacro_Tone / _Weather (Scripts/create_precinct_macro.py)
                        to fresh names, builds M_PrecinctMacroV1_Triplanar = M_PBR_Tiled's graph node for node
                        (61 nodes, same parameter names and defaults) + a macro tail, and REPARENTS
                        MI_PrecinctPlaza_Ashlar onto it with explicit overrides equal to the values it resolved
                        before (V5b textures, scalars, Tint) - so at close range it is the same shader output.
                        The macro multiplies base colour only, only on vertical faces (1 - w_z), faded in by
                        PixelDepth from MacroFadeStartCm to +MacroFadeLengthCm. No map is opened or saved; both
                        maps pick it up through the instance they already reference.
                        M_PBR_Tiled, MI_HerodianV4_* and every other asset are byte-identical (whole Content tree
                        hashed before and after; allow-list = the instance + the new MacroV1 folder).
  -PMVerify=<receipt>   fresh-process readback of the apply (and, with -PMVerifyMaps, both maps' decal flags).
  -PMRetone=<variant> -PMFarStrength=<v> [-PMCloseFadeFar=<v>]
                        import T_PrecinctMacro_Tone<variant> to a fresh name (never_stream, like V2/V3), point
                        MacroTone at it, set MacroFarStrength (and CloseFadeFarStrength when given). Works on any
                        macro master (V1/V2/V3). Every other parameter is read back unchanged or the run fails.
                        -PMVerify=<retone receipt> is the fresh-process reopen for it (cp20).
  -PMRevert=<receipt>   restore MI_PrecinctPlaza_Ashlar's checkpointed bytes (parent back to MI_HerodianV4_Ashlar).
                        The MacroV1 assets stay on disk, unreferenced.
  -PMDecalHide=<Candidate48|Main50>     set bHidden on SURFACEWEAR_Wear_Soot_GoldenAltar_Ceiling, save, re-read.
  -PMDecalRestore=<Candidate48|Main50>  set it back to visible, same guard.

Commandlet (one engine process at a time; check UnrealEditor, UnrealEditor-Cmd, AutomationTool, MikdashCourtyardV3):
  UnrealEditor-Cmd.exe <uproject> -run=pythonscript -unattended -nullrhi -abslog=<log>
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_precinct_macro.py" -PMApply
"""
import hashlib
import json
import re
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('C:/Mikdash/Working-5.8/MikdashCourtyardV3')
CONTENT = ROOT / 'Content'
SRC = ROOT / 'SourceAssets/enclosure-review/PrecinctMacroV1'
RECEIPTS = SRC
CHECKPOINT_ROOT = Path('C:/Mikdash/Working-5.8/ReviewCheckpoints')

INSTANCE = '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Materials/MI_PrecinctPlaza_Ashlar'
ORIGINAL_PARENT = '/Game/MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_Ashlar'
FOLDER = '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/MacroV1'
TEX_FOLDER = FOLDER + '/Textures'
MASTER_NAME = 'M_PrecinctMacroV1_Triplanar'
# V2 (cp19, 11 Sep): V1's graph + a distance fade of the CLOSE albedo toward its own mean, vertical faces only,
# so the 3 m tile's own dark/light blocks stop recurring as wallpaper at 60 m and the macro carries the far field.
# The far target is a VECTOR PARAMETER, not a forced-mip sample: no mip-bias, streaming or cooked-mip-tail
# dependency at all. Value = linear mean of T_HerodianV5_Ashlar_Albedo.png (2048^2, sha256 211bb370177029e8...,
# the source of T_HerodianV5b_Ashlar_Albedo), sRGB-decoded then averaged - what the GPU's mip chain converges to.
# DEPENDENCY: if the Herodian close albedo on MI_PrecinctPlaza_Ashlar changes, recompute this mean.
MASTER_V2_NAME = 'M_PrecinctMacroV2_Triplanar'
CLOSE_FADE_SCALARS = {'CloseFadeStartCm': 2000.0, 'CloseFadeLengthCm': 4000.0, 'CloseFadeFarStrength': 0.85}
CLOSE_ALBEDO_MEAN = (0.5302, 0.47318, 0.40348)
# V3 (cp19b): band-pass - release the close fade again in the far field so the aerial keeps the close tile's
# bed-joint row darkening (the only coursing signal at 1 km). See patch note in do_apply_v2.
MASTER_V3_NAME = 'M_PrecinctMacroV3_Triplanar'
CLOSE_FADE_OUT_SCALARS = {'CloseFadeOutStartCm': 40000.0, 'CloseFadeOutLengthCm': 50000.0}
CLOSE_ALBEDO_SOURCE_SHA256_PREFIX = '211bb370177029e8'
TEXTURES = {'MacroTone': ('T_PrecinctMacro_Tone', 'T_PrecinctMacro_Tone.png', [4096, 2048]),
            'MacroWeather': ('T_PrecinctMacro_Weather', 'T_PrecinctMacro_Weather.png', [1024, 1024])}

CORE_SCALARS = {'TilingCm': 300.0, 'NormalStrength': 1.0, 'RoughnessScale': 1.0, 'Metallic': 0.0, 'AlbedoFlatness': 0.0}
MACRO_SCALARS = {'MacroTileUCm': 9600.0, 'MacroTileVCm': 4800.0, 'WeatherTileCm': 12800.0,
                 'MacroFadeStartCm': 1500.0, 'MacroFadeLengthCm': 4500.0,
                 'MacroNearStrength': 0.0, 'MacroFarStrength': 1.0, 'WeatherStrength': 1.0}
BLEND_EXPONENT = 4.0
CORE_NODE_COUNT = 61   # M_PBR_Tiled, measured by inspect_precinct_macro.py

MAPS = {'Candidate48': 'MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
        'Main50': 'MikdashV3/IntegratedReviewV2/Maps/Walkthrough'}
DECAL_LABEL = 'SURFACEWEAR_Wear_Soot_GoldenAltar_Ceiling'

NAMED_PROTECTED = [
    '/Game/MikdashV3/Materials/PBR/M_PBR_Tiled',
    '/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_LimestoneAshlar',
    '/Game/MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_Ashlar',
    '/Game/MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_Trim',
    '/Game/MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_AshlarWeathered',
    '/Game/MikdashV3/MaterialReview/HerodianAshlarV4/Textures/T_HerodianV5b_Ashlar_Albedo',
    '/Game/MikdashV3/MaterialReview/KeruvFriezeV2/Materials/M_KeruvFriezeV2_Displaced',
    '/Game/MikdashV3/FX/Materials/MI_FX_Smoke_Ceiling',
    '/Game/MikdashV3/SurfaceDetailV2/Materials/MI_Wear_Soot',
]


def now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + 'Z'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def disk(asset, ext='uasset'):
    return CONTENT / (asset[6:] + '.' + ext)


def tree_hashes():
    out = {}
    for p in CONTENT.rglob('*'):
        if p.is_file():
            out[str(p.relative_to(CONTENT)).replace('\\', '/')] = sha(p)
    return out


def P(o):
    return o.get_path_name().split('.')[0] if o else None


class Run:
    def __init__(self, u, mode, target=None):
        self.u = u
        self.ml = u.MaterialEditingLibrary
        self.assets = u.get_editor_subsystem(u.EditorAssetSubsystem)
        self.mode = mode
        self.stamp = now()
        tag = mode + ('-' + target if target else '')
        self.path = RECEIPTS / ('precinct-macro-%s-%s.json' % (tag, self.stamp))
        self.r = {'status': 'started', 'mode': mode, 'target': target, 'startedUtc': datetime.now(timezone.utc).isoformat(),
                  'script': 'Scripts/release_precinct_macro.py', 'mapsSaved': []}
        self.save()

    def save(self):
        RECEIPTS.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.r, indent=1, default=str) + '\n', encoding='utf-8')

    # ------------------------------------------------------------------ readback helpers
    def instance_values(self, inst):
        u, ml = self.u, self.ml
        out = {'path': P(inst), 'parent': P(inst.get_editor_property('parent')), 'base': P(inst.get_base_material()),
               'textures': {}, 'scalars': {}}
        for n in ('Albedo', 'Normal', 'ARM', 'MacroTone', 'MacroWeather'):
            try:
                out['textures'][n] = P(ml.get_material_instance_texture_parameter_value(inst, n))
            except Exception:
                out['textures'][n] = None
        for n in list(CORE_SCALARS) + list(MACRO_SCALARS) + list(CLOSE_FADE_SCALARS) + list(CLOSE_FADE_OUT_SCALARS):
            try:
                out['scalars'][n] = round(float(ml.get_material_instance_scalar_parameter_value(inst, n)), 6)
            except Exception:
                out['scalars'][n] = None
        t = ml.get_material_instance_vector_parameter_value(inst, 'Tint')
        out['tint'] = [round(t.r, 6), round(t.g, 6), round(t.b, 6), round(t.a, 6)]
        try:
            m = ml.get_material_instance_vector_parameter_value(inst, 'CloseAlbedoMean')
            out['closeAlbedoMean'] = [round(m.r, 6), round(m.g, 6), round(m.b, 6)]
        except Exception:
            out['closeAlbedoMean'] = None
        for n in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            us = getattr(u.MaterialUsage, n)
            out[n] = {'has': bool(ml.has_material_usage(inst, us)), 'override': bool(ml.has_material_usage_override(inst, us))}
        return out

    def parity_view(self, v):
        return {'textures': {k: v['textures'][k] for k in ('Albedo', 'Normal', 'ARM')},
                'scalars': {k: v['scalars'][k] for k in CORE_SCALARS}, 'tint': v['tint']}

    def master_values(self, m):
        ml = self.ml
        d = {'path': P(m), 'numExpressions': ml.get_num_material_expressions(m)}
        for k in ('blend_mode', 'shading_model', 'two_sided', 'tangent_space_normal', 'used_with_nanite',
                  'used_with_instanced_static_meshes'):
            d[k] = str(m.get_editor_property(k))
        return d

    def texture_values(self, t):
        row = {'path': P(t), 'srgb': bool(t.get_editor_property('srgb')),
               'compression': str(t.get_editor_property('compression_settings')),
               'lodGroup': str(t.get_editor_property('lod_group')),
               'addressX': str(t.get_editor_property('address_x')), 'addressY': str(t.get_editor_property('address_y'))}
        for g in ('blueprint_get_size_x', 'get_size_x'):
            if hasattr(t, g):
                row['size'] = [int(getattr(t, g)()), int(getattr(t, g.replace('_x', '_y'))())]
                break
        return row

    # ------------------------------------------------------------------ the master graph
    def build_master(self, textures, core_textures, name=MASTER_NAME, close_fade=False, close_fade_out=False):
        u, ml = self.u, self.ml
        path = FOLDER + '/' + name
        if self.assets.does_asset_exist(path):
            raise RuntimeError('%s already exists; this pass builds new asset names (delete_all_material_expressions '
                               'does not empty a graph). Revert and delete it deliberately first.' % path)
        tools = u.AssetToolsHelpers.get_asset_tools()
        material = tools.create_asset(name, FOLDER, u.Material, u.MaterialFactoryNew())
        if not isinstance(material, u.Material):
            raise RuntimeError('Material factory failed')
        material.set_editor_property('tangent_space_normal', False)
        rec = {'asset': path, 'nodes': 0, 'coreNodes': None, 'connections': 0}
        self.r['master'] = rec

        def node(cls, x, y, **props):
            e = ml.create_material_expression(material, cls, x, y)
            if e is None:
                raise RuntimeError('create_material_expression failed for ' + cls.__name__)
            for k, v in props.items():
                e.set_editor_property(k, v)
            rec['nodes'] += 1
            return e

        def pin(expr, wanted):
            names = [str(n) for n in ml.get_material_expression_input_names(expr)]
            for c in names:
                if c.lower() == wanted.lower():
                    return c
            if len(names) == 1:
                return names[0]
            raise RuntimeError('%s has no input %r (%s)' % (expr.get_class().get_name(), wanted, names))

        def wire(src, out, dst, wanted):
            p = pin(dst, wanted)
            if not ml.connect_material_expressions(src, out, dst, p):
                raise RuntimeError('connect %s[%r] -> %s[%r] failed' % (src.get_class().get_name(), out, dst.get_class().get_name(), p))
            rec['connections'] += 1
            return dst

        def to_prop(src, out, prop):
            if not ml.connect_material_property(src, out, getattr(u.MaterialProperty, prop)):
                raise RuntimeError('connect_material_property -> %s failed' % prop)

        def scalar(name, default, x, y):
            return node(u.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=float(default))

        def mask(src, out, x, y, r=False, g=False, b=False, a=False):
            # 5.8 trap: a new ComponentMask starts with R, G and B ticked. Set all four explicitly, every time.
            m = node(u.MaterialExpressionComponentMask, x, y, r=r, g=g, b=b, a=a)
            got = [bool(m.get_editor_property(k)) for k in ('r', 'g', 'b', 'a')]
            if got != [r, g, b, a]:
                raise RuntimeError('ComponentMask read back %s, want %s' % (got, [r, g, b, a]))
            return wire(src, out, m, 'Input')

        def binary(cls, a, ao, b, bo, x, y, **props):
            n = node(cls, x, y, **props)
            wire(a, ao, n, 'A')
            wire(b, bo, n, 'B')
            return n

        def sampler(param, tex, stype, uv, x, y):
            s = node(u.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=param, texture=tex,
                     sampler_type=getattr(u.MaterialSamplerType, stype))
            return wire(uv, '', s, 'UVs')

        # ---------------- CORE: M_PBR_Tiled, node for node (release_pbr_architecture.py build_master_material)
        wp = node(u.MaterialExpressionWorldPosition, -2600, -400)
        tiling = scalar('TilingCm', CORE_SCALARS['TilingCm'], -2600, -250)
        world_uv = binary(u.MaterialExpressionDivide, wp, '', tiling, '', -2400, -350)
        uv_z = mask(world_uv, '', -2200, -500, r=True, g=True)
        uv_y = mask(world_uv, '', -2200, -350, r=True, b=True)
        uv_x = mask(world_uv, '', -2200, -200, g=True, b=True)
        vn = node(u.MaterialExpressionVertexNormalWS, -2600, 200)
        ab = wire(vn, '', node(u.MaterialExpressionAbs, -2450, 200), 'Input')
        pw = wire(ab, '', node(u.MaterialExpressionPower, -2300, 200, const_exponent=BLEND_EXPONENT), 'Base')
        ones = node(u.MaterialExpressionConstant3Vector, -2300, 330, constant=u.LinearColor(1.0, 1.0, 1.0, 1.0))
        wsum = binary(u.MaterialExpressionDotProduct, pw, '', ones, '', -2150, 250)
        weights = binary(u.MaterialExpressionDivide, pw, '', wsum, '', -2000, 200)
        w_x = mask(weights, '', -1850, 120, r=True)
        w_y = mask(weights, '', -1850, 200, g=True)
        w_z = mask(weights, '', -1850, 280, b=True)

        def blend3(parts, x, y):
            (px, ox), (py, oy), (pz, oz) = parts
            mx = binary(u.MaterialExpressionMultiply, px, ox, w_x, '', x, y - 80)
            my = binary(u.MaterialExpressionMultiply, py, oy, w_y, '', x, y)
            mz = binary(u.MaterialExpressionMultiply, pz, oz, w_z, '', x, y + 80)
            first = binary(u.MaterialExpressionAdd, mx, '', my, '', x + 150, y - 40)
            return binary(u.MaterialExpressionAdd, first, '', mz, '', x + 300, y)

        alb = [sampler('Albedo', core_textures['Albedo'], 'SAMPLERTYPE_COLOR', uv, -1600, y)
               for uv, y in ((uv_x, -1000), (uv_y, -800), (uv_z, -600))]
        albedo = blend3([(s, '') for s in alb], -1300, -800)
        flatness = scalar('AlbedoFlatness', CORE_SCALARS['AlbedoFlatness'], -1000, -650)
        flat = node(u.MaterialExpressionLinearInterpolate, -850, -800, const_b=1.0)
        wire(albedo, '', flat, 'A')
        wire(flatness, '', flat, 'Alpha')
        tint = node(u.MaterialExpressionVectorParameter, -850, -600, parameter_name='Tint',
                    default_value=u.LinearColor(1.0, 1.0, 1.0, 1.0))
        base_color = binary(u.MaterialExpressionMultiply, flat, '', tint, '', -650, -750)
        arm_s = [sampler('ARM', core_textures['ARM'], 'SAMPLERTYPE_MASKS', uv, -1600, y)
                 for uv, y in ((uv_x, -300), (uv_y, -100), (uv_z, 100))]
        arm = blend3([(s, '') for s in arm_s], -1300, -100)
        ao = mask(arm, '', -850, -180, r=True)
        rough_raw = mask(arm, '', -850, -60, g=True)
        rough_scale = scalar('RoughnessScale', CORE_SCALARS['RoughnessScale'], -850, 40)
        roughness = binary(u.MaterialExpressionMultiply, rough_raw, '', rough_scale, '', -650, -60)
        to_prop(roughness, '', 'MP_ROUGHNESS')
        metallic = scalar('Metallic', CORE_SCALARS['Metallic'], -650, 120)
        to_prop(metallic, '', 'MP_METALLIC')
        to_prop(ao, '', 'MP_AMBIENT_OCCLUSION')
        nrm = [sampler('Normal', core_textures['Normal'], 'SAMPLERTYPE_NORMAL', uv, -1600, y)
               for uv, y in ((uv_x, 400), (uv_y, 600), (uv_z, 800))]
        zero = node(u.MaterialExpressionConstant, -1450, 900, r=0.0)
        n_x, n_y, n_z = nrm
        dev_x = binary(u.MaterialExpressionAppendVector, zero, '', mask(n_x, '', -1450, 380, r=True, g=True), '', -1300, 400)
        y_r = mask(n_y, '', -1450, 560, r=True)
        y_g = mask(n_y, '', -1450, 640, g=True)
        dev_y = binary(u.MaterialExpressionAppendVector,
                       binary(u.MaterialExpressionAppendVector, y_r, '', zero, '', -1350, 600), '', y_g, '', -1250, 600)
        dev_z = binary(u.MaterialExpressionAppendVector, mask(n_z, '', -1450, 780, r=True, g=True), '', zero, '', -1300, 800)
        deviation = blend3([(dev_x, ''), (dev_y, ''), (dev_z, '')], -1000, 600)
        strength = scalar('NormalStrength', CORE_SCALARS['NormalStrength'], -700, 750)
        scaled = binary(u.MaterialExpressionMultiply, deviation, '', strength, '', -550, 600)
        bent = binary(u.MaterialExpressionAdd, vn, '', scaled, '', -400, 550)
        normal_out = wire(bent, '', node(u.MaterialExpressionNormalize, -250, 550), 'VectorInput')
        to_prop(normal_out, '', 'MP_NORMAL')
        rec['coreNodes'] = rec['nodes']
        if rec['coreNodes'] != CORE_NODE_COUNT:
            raise RuntimeError('Core graph has %d nodes, M_PBR_Tiled has %d' % (rec['coreNodes'], CORE_NODE_COUNT))

        # ---------------- MACRO tail: base colour only
        su = scalar('MacroTileUCm', MACRO_SCALARS['MacroTileUCm'], -2600, -1500)
        sv = scalar('MacroTileVCm', MACRO_SCALARS['MacroTileVCm'], -2600, -1400)
        uu = binary(u.MaterialExpressionAppendVector, su, '', su, '', -2450, -1500)
        uuv = binary(u.MaterialExpressionAppendVector, uu, '', sv, '', -2300, -1450)
        muv = binary(u.MaterialExpressionDivide, wp, '', uuv, '', -2150, -1450)
        muv_y = mask(muv, '', -2000, -1500, r=True, b=True)   # faces along Y: u = world X
        muv_x = mask(muv, '', -2000, -1400, g=True, b=True)   # faces along X: u = world Y
        tone_x = sampler('MacroTone', textures['MacroTone'], 'SAMPLERTYPE_LINEAR_COLOR', muv_x, -1800, -1560)
        tone_y = sampler('MacroTone', textures['MacroTone'], 'SAMPLERTYPE_LINEAR_COLOR', muv_y, -1800, -1400)
        swt = scalar('WeatherTileCm', MACRO_SCALARS['WeatherTileCm'], -2600, -1250)
        wuv = binary(u.MaterialExpressionDivide, wp, '', swt, '', -2300, -1250)
        wuv_y = mask(wuv, '', -2000, -1280, r=True, b=True)
        wuv_x = mask(wuv, '', -2000, -1200, g=True, b=True)
        wea_x = sampler('MacroWeather', textures['MacroWeather'], 'SAMPLERTYPE_LINEAR_COLOR', wuv_x, -1800, -1260)
        wea_y = sampler('MacroWeather', textures['MacroWeather'], 'SAMPLERTYPE_LINEAR_COLOR', wuv_y, -1800, -1120)
        neutral3 = node(u.MaterialExpressionConstant3Vector, -1600, -1000, constant=u.LinearColor(0.5, 0.5, 0.5, 1.0))
        neutral1 = node(u.MaterialExpressionConstant, -1600, -950, r=0.5)
        tone_b = blend3([(tone_x, ''), (tone_y, ''), (neutral3, '')], -1500, -1450)
        wea_b = blend3([(wea_x, 'R'), (wea_y, 'R'), (neutral1, '')], -1500, -1200)
        tone2 = wire(tone_b, '', node(u.MaterialExpressionMultiply, -1100, -1450, const_b=2.0), 'A')
        wea2 = wire(wea_b, '', node(u.MaterialExpressionMultiply, -1100, -1200, const_b=2.0), 'A')
        wstr = scalar('WeatherStrength', MACRO_SCALARS['WeatherStrength'], -1100, -1100)
        wmix = node(u.MaterialExpressionLinearInterpolate, -950, -1200, const_a=1.0)
        wire(wea2, '', wmix, 'B')
        wire(wstr, '', wmix, 'Alpha')
        mult = binary(u.MaterialExpressionMultiply, tone2, '', wmix, '', -800, -1350)
        depth = node(u.MaterialExpressionPixelDepth, -1300, -1700)
        fstart = scalar('MacroFadeStartCm', MACRO_SCALARS['MacroFadeStartCm'], -1300, -1620)
        flen = scalar('MacroFadeLengthCm', MACRO_SCALARS['MacroFadeLengthCm'], -1300, -1560)
        dsub = binary(u.MaterialExpressionSubtract, depth, '', fstart, '', -1150, -1680)
        ddiv = binary(u.MaterialExpressionDivide, dsub, '', flen, '', -1000, -1650)
        dsat = wire(ddiv, '', node(u.MaterialExpressionSaturate, -850, -1650), 'Input')
        snear = scalar('MacroNearStrength', MACRO_SCALARS['MacroNearStrength'], -850, -1580)
        sfar = scalar('MacroFarStrength', MACRO_SCALARS['MacroFarStrength'], -850, -1520)
        weight = node(u.MaterialExpressionLinearInterpolate, -700, -1620)
        wire(snear, '', weight, 'A')
        wire(sfar, '', weight, 'B')
        wire(dsat, '', weight, 'Alpha')
        factor = node(u.MaterialExpressionLinearInterpolate, -600, -1400, const_a=1.0)
        wire(mult, '', factor, 'B')
        wire(weight, '', factor, 'Alpha')
        if close_fade:
            # ---------------- V2 CLOSE FADE: albedo -> lerp(albedo, CloseAlbedoMean, w), re-routed into flat.A
            # w = saturate((PixelDepth - CloseFadeStartCm) / CloseFadeLengthCm) * CloseFadeFarStrength * (1 - w_z)
            n0 = rec['nodes']
            cmean = node(u.MaterialExpressionVectorParameter, -1150, -950, parameter_name='CloseAlbedoMean',
                         default_value=u.LinearColor(CLOSE_ALBEDO_MEAN[0], CLOSE_ALBEDO_MEAN[1], CLOSE_ALBEDO_MEAN[2], 1.0))
            cstart = scalar('CloseFadeStartCm', CLOSE_FADE_SCALARS['CloseFadeStartCm'], -1450, -1900)
            clen = scalar('CloseFadeLengthCm', CLOSE_FADE_SCALARS['CloseFadeLengthCm'], -1450, -1840)
            cstr = scalar('CloseFadeFarStrength', CLOSE_FADE_SCALARS['CloseFadeFarStrength'], -1450, -1780)
            csub = binary(u.MaterialExpressionSubtract, depth, '', cstart, '', -1300, -1900)
            cdiv = binary(u.MaterialExpressionDivide, csub, '', clen, '', -1150, -1900)
            csat = wire(cdiv, '', node(u.MaterialExpressionSaturate, -1000, -1900), 'Input')
            cw = binary(u.MaterialExpressionMultiply, csat, '', cstr, '', -850, -1900)
            vert = wire(w_z, '', node(u.MaterialExpressionOneMinus, -1000, -1820), 'Input')
            cw2 = binary(u.MaterialExpressionMultiply, cw, '', vert, '', -700, -1880)
            if close_fade_out:
                ostart = scalar('CloseFadeOutStartCm', CLOSE_FADE_OUT_SCALARS['CloseFadeOutStartCm'], -1450, -2000)
                olen = scalar('CloseFadeOutLengthCm', CLOSE_FADE_OUT_SCALARS['CloseFadeOutLengthCm'], -1450, -2060)
                osub = binary(u.MaterialExpressionSubtract, depth, '', ostart, '', -1300, -2030)
                odiv = binary(u.MaterialExpressionDivide, osub, '', olen, '', -1150, -2030)
                osat = wire(odiv, '', node(u.MaterialExpressionSaturate, -1000, -2030), 'Input')
                okeep = wire(osat, '', node(u.MaterialExpressionOneMinus, -850, -2030), 'Input')
                cw2 = binary(u.MaterialExpressionMultiply, cw2, '', okeep, '', -600, -1950)
            faded = node(u.MaterialExpressionLinearInterpolate, -1000, -900)
            wire(albedo, '', faded, 'A')
            wire(cmean, '', faded, 'B')
            wire(cw2, '', faded, 'Alpha')
            wire(faded, '', flat, 'A')          # replaces the core's albedo -> flat.A link
            rec['closeFadeNodes'] = rec['nodes'] - n0
        final = binary(u.MaterialExpressionMultiply, base_color, '', factor, '', -450, -800)
        to_prop(final, '', 'MP_BASE_COLOR')

        # usage flags on the BASE material: a HISM with a missing flag draws the default material in a cook
        for k in ('used_with_nanite', 'used_with_instanced_static_meshes'):
            material.set_editor_property(k, True)
        res = ml.recompile_material(material)
        rec['recompileReturned'] = str(res)
        try:
            st = ml.get_statistics(material)
            rec['statistics'] = {k: str(getattr(st, k)) for k in dir(st) if k.startswith('num_')}
        except Exception as err:
            rec['statistics'] = 'unavailable: %r' % (err,)
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save failed for ' + path)
        rec['readback'] = self.master_values(material)
        if rec['readback']['numExpressions'] != rec['nodes']:
            raise RuntimeError('Master has %s expressions, built %s' % (rec['readback']['numExpressions'], rec['nodes']))
        return material

    # ------------------------------------------------------------------ apply
    def do_apply(self):
        u, ml, r = self.u, self.ml, self.r
        man = json.loads((SRC / 'manifest.json').read_text(encoding='utf-8'))
        r['manifest'] = {'seed': man['seed'], 'tone': {k: man['tone'][k] for k in ('sha256', 'size', 'tileCm')},
                         'weather': {k: man['weather'][k] for k in ('sha256', 'size', 'tileCm')}}
        for key in ('tone', 'weather'):
            f = SRC / man[key]['file']
            if sha(f) != man[key]['sha256']:
                raise RuntimeError('%s does not match its manifest' % f)
        for k, v in MACRO_SCALARS.items():
            if k in ('MacroTileUCm', 'MacroTileVCm') and v != man['tone']['tileCm'][0 if k.endswith('UCm') else 1]:
                raise RuntimeError('%s %s disagrees with the tone manifest' % (k, v))
        if MACRO_SCALARS['WeatherTileCm'] != man['weather']['tileCm'][0]:
            raise RuntimeError('WeatherTileCm disagrees with the manifest')

        r['stage'] = 'hash_before'
        self.save()
        before = tree_hashes()
        r['contentFilesHashed'] = len(before)
        r['namedProtectedBefore'] = {a: sha(disk(a)) for a in NAMED_PROTECTED if disk(a).exists()}
        r['mapsBefore'] = {k: sha(CONTENT / (v + '.umap')) for k, v in MAPS.items()}

        inst = u.load_asset(INSTANCE)
        if not isinstance(inst, u.MaterialInstanceConstant):
            raise RuntimeError('%s is not a MaterialInstanceConstant' % INSTANCE)
        pre = self.instance_values(inst)
        r['instanceBefore'] = pre
        if pre['parent'] != ORIGINAL_PARENT:
            raise RuntimeError('%s parent is %s, expected %s (already applied? revert first)' % (INSTANCE, pre['parent'], ORIGINAL_PARENT))

        cp = CHECKPOINT_ROOT / ('PrecinctMacro-%s' % self.stamp)
        cp.mkdir(parents=True, exist_ok=False)
        dst = cp / 'MI_PrecinctPlaza_Ashlar.uasset'
        shutil.copy2(disk(INSTANCE), dst)
        r['checkpoint'] = str(cp)
        r['checkpointed'] = {INSTANCE: {'file': str(dst), 'sha256': sha(dst)}}
        self.save()

        r['stage'] = 'import'
        self.save()
        textures = {}
        r['textures'] = {}
        for param, (name, fname, size) in TEXTURES.items():
            path = TEX_FOLDER + '/' + name
            if self.assets.does_asset_exist(path):
                raise RuntimeError('%s already exists; import to fresh names only' % path)
            task = u.AssetImportTask()
            for k, v in dict(filename=str(SRC / fname), destination_path=TEX_FOLDER, destination_name=name,
                             automated=True, replace_existing=False, save=False).items():
                task.set_editor_property(k, v)
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            objs = list(task.get_objects())
            if len(objs) != 1 or not isinstance(objs[0], u.Texture2D):
                raise RuntimeError('Import of %s produced %s' % (fname, objs))
            t = objs[0]
            t.set_editor_property('srgb', False)
            t.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_DEFAULT)
            t.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WORLD)
            t.set_editor_property('address_x', u.TextureAddress.TA_WRAP)
            t.set_editor_property('address_y', u.TextureAddress.TA_WRAP)
            try:
                t.set_editor_property('virtual_texture_streaming', False)
            except Exception:
                pass
            if not self.assets.save_loaded_asset(t, only_if_is_dirty=False):
                raise RuntimeError('save failed for ' + path)
            rb = self.texture_values(t)
            if rb.get('size') != size or rb['srgb'] is not False or 'TC_DEFAULT' not in rb['compression']:
                raise RuntimeError('%s read back %s' % (path, rb))
            r['textures'][path] = {'source': fname, 'readback': rb, 'uassetSha256': sha(disk(path))}
            textures[param] = t
        self.save()

        r['stage'] = 'master'
        self.save()
        core = {k: u.load_asset(pre['textures'][k]) for k in ('Albedo', 'Normal', 'ARM')}
        master = self.build_master(textures, core)
        self.save()

        r['stage'] = 'reparent'
        self.save()
        ml.set_material_instance_parent(inst, master)
        if P(inst.get_editor_property('parent')) != P(master):
            inst.set_editor_property('parent', master)
        if P(inst.get_editor_property('parent')) != P(master):
            raise RuntimeError('Parent did not take')
        for k in ('Albedo', 'Normal', 'ARM'):
            ml.set_material_instance_texture_parameter_value(inst, k, core[k])
        for k, v in pre['scalars'].items():
            if k in CORE_SCALARS:
                ml.set_material_instance_scalar_parameter_value(inst, k, float(v))
        ml.set_material_instance_vector_parameter_value(inst, 'Tint', u.LinearColor(*pre['tint']))
        for k, v in MACRO_SCALARS.items():
            ml.set_material_instance_scalar_parameter_value(inst, k, float(v))
        for k in ('MacroTone', 'MacroWeather'):
            ml.set_material_instance_texture_parameter_value(inst, k, textures[k])
        for n in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            ml.set_material_usage_override(inst, getattr(u.MaterialUsage, n), True, True)
        ml.update_material_instance(inst)
        if not self.assets.save_loaded_asset(inst, only_if_is_dirty=False):
            raise RuntimeError('save failed for ' + INSTANCE)

        r['stage'] = 'readback'
        self.save()
        try:
            self.assets.load_asset(INSTANCE)
        except Exception:
            pass
        post = self.instance_values(u.load_asset(INSTANCE))
        r['instanceAfter'] = post
        r['parity'] = {'before': self.parity_view(pre), 'after': self.parity_view(post)}
        r['parity']['equal'] = r['parity']['before'] == r['parity']['after']
        if not r['parity']['equal']:
            raise RuntimeError('Close-range parameters changed: %s' % r['parity'])
        if post['parent'] != FOLDER + '/' + MASTER_NAME or post['base'] != FOLDER + '/' + MASTER_NAME:
            raise RuntimeError('Parent/base read back %s / %s' % (post['parent'], post['base']))
        for k, v in MACRO_SCALARS.items():
            if post['scalars'][k] is None or abs(post['scalars'][k] - v) > 1e-4:
                raise RuntimeError('%s read back %s want %s' % (k, post['scalars'][k], v))
        for n in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            if not post[n]['has']:
                raise RuntimeError('lost usage ' + n)
        r['instanceUassetSha256'] = sha(disk(INSTANCE))

        r['stage'] = 'hash_after'
        self.save()
        after = tree_hashes()
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
        allowed = (INSTANCE[6:] + '.uasset', FOLDER[6:] + '/')
        r['contentDiff'] = {'added': added, 'removed': removed, 'changed': changed}
        illegal = [k for k in added + removed + changed if not any(k == a or k.startswith(a) for a in allowed)]
        r['illegalChanges'] = illegal
        r['namedProtectedAfter'] = {a: sha(disk(a)) for a in NAMED_PROTECTED if disk(a).exists()}
        r['mapsAfter'] = {k: sha(CONTENT / (v + '.umap')) for k, v in MAPS.items()}
        if r['namedProtectedAfter'] != r['namedProtectedBefore']:
            raise RuntimeError('A named protected asset changed')
        if r['mapsAfter'] != r['mapsBefore']:
            raise RuntimeError('A map changed; this pass must not mutate a map')
        if illegal:
            raise RuntimeError('Files outside the allow-list changed: %s' % illegal[:20])
        r['status'] = 'applied_visual_acceptance_pending'
        r['limits'] = 'Offline readback only; acceptance is packaged-build frames (cp05b-04 camera, a 40-80 m face view, the 4 m jamb).'


    # ------------------------------------------------------------------ V2: close-albedo distance fade (cp19)
    def do_apply_v2(self, v3=False):
        """ASSET-ONLY. Builds M_PrecinctMacroV2_Triplanar (V1 graph node for node + the close fade) and reparents
        MI_PrecinctPlaza_Ashlar from the V1 master onto it with EVERY value it resolves today set explicitly (V5b
        textures, core scalars, Tint, the live macro scalars incl. MacroFarStrength, the live MacroTone/Weather), plus
        the three CloseFade* scalars and CloseAlbedoMean. Also sets never_stream on the two macro textures in use
        (world-position UVs give the streamer no UV density to size them by; 6 MB total). -PMRevert=<this receipt>
        restores the instance and both textures from their checkpointed bytes."""
        u, ml, r = self.u, self.ml, self.r
        v1_path = FOLDER + '/' + (MASTER_V2_NAME if v3 else MASTER_NAME)
        v2_path = FOLDER + '/' + (MASTER_V3_NAME if v3 else MASTER_V2_NAME)
        r['stage'] = 'hash_before'
        self.save()
        before = tree_hashes()
        r['contentFilesHashed'] = len(before)
        r['namedProtectedBefore'] = {a: sha(disk(a)) for a in NAMED_PROTECTED if disk(a).exists()}
        r['mapsBefore'] = {k: sha(CONTENT / (v + '.umap')) for k, v in MAPS.items()}
        inst = u.load_asset(INSTANCE)
        pre = self.instance_values(inst)
        r['instanceBefore'] = pre
        if pre['parent'] != v1_path:
            raise RuntimeError('%s parent is %s, expected %s' % (INSTANCE, pre['parent'], v1_path))
        if self.assets.does_asset_exist(v2_path):
            raise RuntimeError('%s already exists; build to new names only' % v2_path)
        tex_paths = [pre['textures']['MacroTone'], pre['textures']['MacroWeather']]
        for tp in tex_paths:
            if not tp or not tp.startswith(TEX_FOLDER + '/'):
                raise RuntimeError('macro texture %s is not in %s' % (tp, TEX_FOLDER))

        cp = CHECKPOINT_ROOT / (('PrecinctMacroV3-%s' if v3 else 'PrecinctMacroV2-%s') % self.stamp)
        cp.mkdir(parents=True, exist_ok=False)
        r['checkpoint'] = str(cp)
        r['checkpointed'] = {}
        for asset in [INSTANCE] + tex_paths:
            dst = cp / (asset.split('/')[-1] + '.uasset')
            shutil.copy2(disk(asset), dst)
            r['checkpointed'][asset] = {'file': str(dst), 'sha256': sha(dst)}
        self.save()

        # the far target's provenance: which file the live close albedo was imported from
        alb = u.load_asset(pre['textures']['Albedo'])
        srcinfo = {'asset': pre['textures']['Albedo']}
        try:
            srcinfo['importedFrom'] = str(alb.get_editor_property('asset_import_data').get_first_filename())
            fp = Path(srcinfo['importedFrom'])
            srcinfo['importedFromExists'] = fp.exists()
            if fp.exists():
                srcinfo['importedFromSha256'] = sha(fp)
                srcinfo['matchesMeanSource'] = srcinfo['importedFromSha256'].startswith(CLOSE_ALBEDO_SOURCE_SHA256_PREFIX)
        except Exception as err:
            srcinfo['importDataError'] = repr(err)
        srcinfo['closeAlbedoMeanLinear'] = list(CLOSE_ALBEDO_MEAN)
        r['closeAlbedoSource'] = srcinfo

        r['stage'] = 'never_stream'
        self.save()
        textures = {}
        r['textureStreaming'] = {}
        for param, tp in (('MacroTone', tex_paths[0]), ('MacroWeather', tex_paths[1])):
            t = u.load_asset(tp)
            was = bool(t.get_editor_property('never_stream'))
            t.set_editor_property('never_stream', True)
            if not self.assets.save_loaded_asset(t, only_if_is_dirty=False):
                raise RuntimeError('save failed for ' + tp)
            r['textureStreaming'][tp] = {'neverStreamBefore': was, 'neverStreamAfter': bool(t.get_editor_property('never_stream')),
                                         'lodBias': int(t.get_editor_property('lod_bias')), 'readback': self.texture_values(t)}
            textures[param] = t
        self.save()

        r['stage'] = 'master'
        self.save()
        core = {k: u.load_asset(pre['textures'][k]) for k in ('Albedo', 'Normal', 'ARM')}
        master = self.build_master(textures, core, name=(MASTER_V3_NAME if v3 else MASTER_V2_NAME), close_fade=True,
                                   close_fade_out=v3)
        if not r['master'].get('closeFadeNodes'):
            raise RuntimeError('close fade nodes were not built')
        self.save()

        r['stage'] = 'reparent'
        self.save()
        ml.set_material_instance_parent(inst, master)
        if P(inst.get_editor_property('parent')) != P(master):
            inst.set_editor_property('parent', master)
        if P(inst.get_editor_property('parent')) != P(master):
            raise RuntimeError('Parent did not take')
        for k in ('Albedo', 'Normal', 'ARM'):
            ml.set_material_instance_texture_parameter_value(inst, k, core[k])
        for k in ('MacroTone', 'MacroWeather'):
            ml.set_material_instance_texture_parameter_value(inst, k, textures[k])
        for k in list(CORE_SCALARS) + list(MACRO_SCALARS):
            ml.set_material_instance_scalar_parameter_value(inst, k, float(pre['scalars'][k]))
        for k, v in CLOSE_FADE_SCALARS.items():
            ml.set_material_instance_scalar_parameter_value(inst, k, float(v))
        if v3:
            for k, v in CLOSE_FADE_OUT_SCALARS.items():
                ml.set_material_instance_scalar_parameter_value(inst, k, float(v))
        ml.set_material_instance_vector_parameter_value(inst, 'Tint', u.LinearColor(*pre['tint']))
        ml.set_material_instance_vector_parameter_value(inst, 'CloseAlbedoMean', u.LinearColor(*(list(CLOSE_ALBEDO_MEAN) + [1.0])))
        for n in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            ml.set_material_usage_override(inst, getattr(u.MaterialUsage, n), True, True)
        ml.update_material_instance(inst)
        if not self.assets.save_loaded_asset(inst, only_if_is_dirty=False):
            raise RuntimeError('save failed for ' + INSTANCE)

        r['stage'] = 'readback'
        self.save()
        post = self.instance_values(u.load_asset(INSTANCE))
        r['instanceAfter'] = post
        r['parity'] = {'before': self.parity_view(pre), 'after': self.parity_view(post)}
        r['parity']['equal'] = r['parity']['before'] == r['parity']['after']
        if not r['parity']['equal']:
            raise RuntimeError('Close-range parameters changed: %s' % r['parity'])
        if post['parent'] != v2_path or post['base'] != v2_path:
            raise RuntimeError('Parent/base read back %s / %s' % (post['parent'], post['base']))
        for k in MACRO_SCALARS:
            if post['scalars'][k] is None or abs(post['scalars'][k] - pre['scalars'][k]) > 1e-4:
                raise RuntimeError('macro scalar %s read back %s, was %s' % (k, post['scalars'][k], pre['scalars'][k]))
        for k, v in list(CLOSE_FADE_SCALARS.items()) + (list(CLOSE_FADE_OUT_SCALARS.items()) if v3 else []):
            if post['scalars'][k] is None or abs(post['scalars'][k] - v) > 1e-4:
                raise RuntimeError('%s read back %s want %s' % (k, post['scalars'][k], v))
        if post['textures'] != pre['textures']:
            raise RuntimeError('texture overrides changed: %s -> %s' % (pre['textures'], post['textures']))
        if not post['closeAlbedoMean'] or max(abs(a - b) for a, b in zip(post['closeAlbedoMean'], CLOSE_ALBEDO_MEAN)) > 1e-4:
            raise RuntimeError('CloseAlbedoMean read back %s' % post['closeAlbedoMean'])
        for n in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            if not post[n]['has']:
                raise RuntimeError('lost usage ' + n)
        r['instanceUassetSha256'] = sha(disk(INSTANCE))

        r['stage'] = 'hash_after'
        self.save()
        after = tree_hashes()
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
        allowed = (INSTANCE[6:] + '.uasset', FOLDER[6:] + '/')
        r['contentDiff'] = {'added': added, 'removed': removed, 'changed': changed}
        illegal = [k for k in added + removed + changed if not any(k == a or k.startswith(a) for a in allowed)]
        r['illegalChanges'] = illegal
        r['namedProtectedAfter'] = {a: sha(disk(a)) for a in NAMED_PROTECTED if disk(a).exists()}
        r['mapsAfter'] = {k: sha(CONTENT / (v + '.umap')) for k, v in MAPS.items()}
        if r['namedProtectedAfter'] != r['namedProtectedBefore']:
            raise RuntimeError('A named protected asset changed')
        if r['mapsAfter'] != r['mapsBefore']:
            raise RuntimeError('A map changed; this pass must not mutate a map')
        if illegal:
            raise RuntimeError('Files outside the allow-list changed: %s' % illegal[:20])
        r['status'] = 'applied_v3_visual_acceptance_pending' if v3 else 'applied_v2_visual_acceptance_pending'
        r['limits'] = ('Offline readback only (-nullrhi draws nothing). Acceptance is packaged-build frames: P1 aerial, '
                       'P2/P3 60-70 m faces, 02 jamb and 07 plaza stone at walking range (fade 0 below 20 m).')

    # ------------------------------------------------------------------ verify / revert
    def do_verify(self, receipt, with_maps):
        u, r = self.u, self.r
        prior = json.loads(Path(receipt).read_text(encoding='utf-8-sig'))
        r['verifying'] = str(receipt)
        inst = u.load_asset(INSTANCE)
        v = self.instance_values(inst)
        r['instance'] = v
        r['uassetSha256'] = sha(disk(INSTANCE))
        if prior.get('mode') == 'retone':
            # cp20: fresh-process reopen of a retone - every parameter must equal what the retone read back
            want = prior['instanceAfter']

            def same2(a, b):
                if a is None or b is None:
                    return a is None and b is None
                return abs(a - b) <= 1e-5
            r['uassetMatchesApply'] = r['uassetSha256'] == prior.get('instanceUassetSha256')
            r['parentUnchanged'] = v['parent'] == want['parent']
            r['texturesEqual'] = v['textures'] == want['textures']
            r['scalarsMismatch'] = [k for k in want['scalars'] if not same2(want['scalars'][k], v['scalars'].get(k))]
            t = u.load_asset(prior['texture']['asset'])
            r['toneTexture'] = self.texture_values(t)
            r['toneNeverStream'] = bool(t.get_editor_property('never_stream'))
            r['usage'] = {n: v[n] for n in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES') if n in v}
            ok = (r['uassetMatchesApply'] and r['parentUnchanged'] and r['texturesEqual'] and not r['scalarsMismatch']
                  and r['toneNeverStream'] and all(x.get('has') for x in r['usage'].values()) and len(r['usage']) == 2)
            r['status'] = 'verified' if ok else 'verify_mismatch'
            return
        r['uassetMatchesApply'] = r['uassetSha256'] == prior.get('instanceUassetSha256')
        r['parityEqualToBefore'] = self.parity_view(v) == prior['parity']['before']
        master = u.load_asset(FOLDER + '/' + MASTER_NAME)
        r['master'] = self.master_values(master) if master else None
        r['textures'] = {t: self.texture_values(u.load_asset(t)) for t in prior.get('textures', {})}
        ok = r['uassetMatchesApply'] and r['parityEqualToBefore'] and v['parent'] == FOLDER + '/' + MASTER_NAME \
            and master is not None and 'True' in r['master']['used_with_instanced_static_meshes'] \
            and 'True' in r['master']['used_with_nanite']
        if with_maps:
            r['decals'] = {}
            les = u.get_editor_subsystem(u.LevelEditorSubsystem)
            for key, mp in MAPS.items():
                if not les.load_level('/Game/' + mp):
                    raise RuntimeError('load_level failed for ' + mp)
                a = self.find_decal()
                r['decals'][key] = self.decal_values(a)
                r['decals'][key]['mapSha256'] = sha(CONTENT / (mp + '.umap'))
        r['status'] = 'verified' if ok else 'verify_mismatch'

    def do_revert(self, receipt):
        u, r = self.u, self.r
        prior = json.loads(Path(receipt).read_text(encoding='utf-8-sig'))
        r['reverting'] = str(receipt)
        maps_before = {k: sha(CONTENT / (v + '.umap')) for k, v in MAPS.items()}
        r['restored'] = {}
        for asset, info in prior['checkpointed'].items():
            src = Path(info['file'])
            if sha(src) != info['sha256']:
                raise RuntimeError('Checkpoint changed since the apply: ' + asset)
        for asset, info in prior['checkpointed'].items():
            shutil.copy2(Path(info['file']), disk(asset))
            got = sha(disk(asset))
            r['restored'][asset] = got
            if got != info['sha256']:
                raise RuntimeError('Restored bytes do not match the checkpoint: ' + asset)
        r['restoredSha256'] = r['restored'].get(INSTANCE)
        r['mapsUnchanged'] = maps_before == {k: sha(CONTENT / (v + '.umap')) for k, v in MAPS.items()}
        r['confirmWith'] = 'Fresh-process inspect: MI_PrecinctPlaza_Ashlar parent must read MI_HerodianV4_Ashlar.'
        r['note'] = 'MacroV1 assets are left on disk, unreferenced; they cannot affect rendering.'
        r['status'] = 'reverted'

    # ------------------------------------------------------------------ retone: swap the tone map, tune far strength
    def do_retone(self, variant, far_strength, close_far=None):
        """ASSET-ONLY. Imports T_PrecinctMacro_Tone<variant> to a fresh name, points MI_PrecinctPlaza_Ashlar's
        MacroTone at it and sets MacroFarStrength. Same guard as -PMApply; -PMRevert=<this receipt> restores the
        instance bytes from before THIS step (i.e. back to the previous tone map, still on the macro master)."""
        u, ml, r = self.u, self.ml, self.r
        # cp20: the instance now sits on the V3 band-pass master; any macro master carries MacroTone/MacroFarStrength
        macro_masters = [FOLDER + '/' + n for n in (MASTER_NAME, MASTER_V2_NAME, MASTER_V3_NAME)]
        man = json.loads((SRC / ('manifest-%s.json' % variant)).read_text(encoding='utf-8'))
        tone_file = SRC / man['tone']['file']
        if sha(tone_file) != man['tone']['sha256']:
            raise RuntimeError('%s does not match its manifest' % tone_file)
        if man['tone']['tileCm'] != [MACRO_SCALARS['MacroTileUCm'], MACRO_SCALARS['MacroTileVCm']]:
            raise RuntimeError('tone tile size changed; the master expects %s' % [MACRO_SCALARS['MacroTileUCm'], MACRO_SCALARS['MacroTileVCm']])
        r['variant'] = variant
        r['farStrength'] = far_strength
        r['manifest'] = {'seed': man['seed'], 'params': man['params'], 'tone': {k: man['tone'][k] for k in ('sha256', 'size', 'tileCm', 'at100cmPerPx')}}
        r['stage'] = 'hash_before'
        self.save()
        before = tree_hashes()
        r['namedProtectedBefore'] = {a: sha(disk(a)) for a in NAMED_PROTECTED if disk(a).exists()}
        r['mapsBefore'] = {k: sha(CONTENT / (v + '.umap')) for k, v in MAPS.items()}
        inst = u.load_asset(INSTANCE)
        pre = self.instance_values(inst)
        r['instanceBefore'] = pre
        if pre['parent'] not in macro_masters:
            raise RuntimeError('%s parent is %s; run -PMApply first' % (INSTANCE, pre['parent']))
        cp = CHECKPOINT_ROOT / ('PrecinctMacro-retone%s-%s' % (variant, self.stamp))
        cp.mkdir(parents=True, exist_ok=False)
        dst = cp / 'MI_PrecinctPlaza_Ashlar.uasset'
        shutil.copy2(disk(INSTANCE), dst)
        r['checkpoint'] = str(cp)
        r['checkpointed'] = {INSTANCE: {'file': str(dst), 'sha256': sha(dst)}}
        self.save()
        name = 'T_PrecinctMacro_Tone%s' % variant
        path = TEX_FOLDER + '/' + name
        if self.assets.does_asset_exist(path):
            raise RuntimeError('%s already exists; import to fresh names only' % path)
        task = u.AssetImportTask()
        for k, v in dict(filename=str(tone_file), destination_path=TEX_FOLDER, destination_name=name,
                         automated=True, replace_existing=False, save=False).items():
            task.set_editor_property(k, v)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objs = list(task.get_objects())
        if len(objs) != 1 or not isinstance(objs[0], u.Texture2D):
            raise RuntimeError('Import produced %s' % objs)
        t = objs[0]
        t.set_editor_property('srgb', False)
        t.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_DEFAULT)
        t.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WORLD)
        t.set_editor_property('address_x', u.TextureAddress.TA_WRAP)
        t.set_editor_property('address_y', u.TextureAddress.TA_WRAP)
        if not self.assets.save_loaded_asset(t, only_if_is_dirty=False):
            raise RuntimeError('save failed for ' + path)
        # same streaming policy as the V2/V3 apply: world-position UVs give the streamer no UV density
        t.set_editor_property('never_stream', True)
        if not self.assets.save_loaded_asset(t, only_if_is_dirty=False):
            raise RuntimeError('save failed for ' + path + ' (never_stream)')
        r['textureNeverStream'] = bool(t.get_editor_property('never_stream'))
        if not r['textureNeverStream']:
            raise RuntimeError('never_stream did not read back on ' + path)
        rb = self.texture_values(t)
        if rb.get('size') != man['tone']['size'] or rb['srgb'] is not False:
            raise RuntimeError('%s read back %s' % (path, rb))
        r['texture'] = {'asset': path, 'readback': rb, 'uassetSha256': sha(disk(path))}
        ml.set_material_instance_texture_parameter_value(inst, 'MacroTone', t)
        ml.set_material_instance_scalar_parameter_value(inst, 'MacroFarStrength', float(far_strength))
        r['closeFadeFarStrength'] = close_far
        if close_far is not None:
            if 'CloseFadeFarStrength' not in pre['scalars'] or pre['scalars']['CloseFadeFarStrength'] is None:
                raise RuntimeError('-PMCloseFadeFar given but the parent has no CloseFadeFarStrength (needs the V2/V3 master)')
            ml.set_material_instance_scalar_parameter_value(inst, 'CloseFadeFarStrength', float(close_far))
        for n in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            ml.set_material_usage_override(inst, getattr(u.MaterialUsage, n), True, True)
        ml.update_material_instance(inst)
        if not self.assets.save_loaded_asset(inst, only_if_is_dirty=False):
            raise RuntimeError('save failed for ' + INSTANCE)
        post = self.instance_values(u.load_asset(INSTANCE))
        r['instanceAfter'] = post
        r['parity'] = {'equal': self.parity_view(pre) == self.parity_view(post)}
        if not r['parity']['equal']:
            raise RuntimeError('close-range parameters changed')
        if post['parent'] != pre['parent']:
            raise RuntimeError('parent changed %s -> %s' % (pre['parent'], post['parent']))
        def same(a, b):
            if a is None or b is None:
                return a is None and b is None
            return abs(a - b) <= 1e-5
        skip = {'MacroFarStrength'} | ({'CloseFadeFarStrength'} if close_far is not None else set())
        if close_far is not None and not same(post['scalars'].get('CloseFadeFarStrength'), close_far):
            raise RuntimeError('CloseFadeFarStrength read back %s, want %s' % (post['scalars'].get('CloseFadeFarStrength'), close_far))
        others = {'scalars': [k for k in pre['scalars']
                              if k not in skip and not same(pre['scalars'][k], post['scalars'].get(k))],
                  'textures': [k for k in pre['textures']
                               if k != 'MacroTone' and pre['textures'][k] != post['textures'].get(k)]}
        r['otherParamsChanged'] = others
        if others['scalars'] or others['textures']:
            raise RuntimeError('retone changed other parameters: %s' % others)
        if post['textures']['MacroTone'] != path or abs(post['scalars']['MacroFarStrength'] - far_strength) > 1e-4:
            raise RuntimeError('retone readback %s / %s' % (post['textures']['MacroTone'], post['scalars']['MacroFarStrength']))
        for n in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            if not post[n]['has']:
                raise RuntimeError('lost usage ' + n)
        r['instanceUassetSha256'] = sha(disk(INSTANCE))
        r['stage'] = 'hash_after'
        self.save()
        after = tree_hashes()
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        allowed = (INSTANCE[6:] + '.uasset', FOLDER[6:] + '/')
        r['contentDiff'] = changed
        r['illegalChanges'] = [k for k in changed if not any(k == a or k.startswith(a) for a in allowed)]
        r['namedProtectedAfter'] = {a: sha(disk(a)) for a in NAMED_PROTECTED if disk(a).exists()}
        r['mapsAfter'] = {k: sha(CONTENT / (v + '.umap')) for k, v in MAPS.items()}
        if r['illegalChanges'] or r['mapsAfter'] != r['mapsBefore'] or r['namedProtectedAfter'] != r['namedProtectedBefore']:
            raise RuntimeError('guard: illegal=%s maps/protected changed=%s' % (r['illegalChanges'][:10], r['mapsAfter'] != r['mapsBefore']))
        r['status'] = 'retoned_visual_acceptance_pending'

    # ------------------------------------------------------------------ the ceiling soot decal
    def find_decal(self):
        u = self.u
        hits = [a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
                if a.get_actor_label() == DECAL_LABEL]
        if len(hits) != 1:
            raise RuntimeError('Expected exactly one %s, found %d' % (DECAL_LABEL, len(hits)))
        return hits[0]

    def decal_values(self, a):
        u = self.u
        d = {'label': a.get_actor_label(), 'name': a.get_name(), 'class': a.get_class().get_name(),
             'hiddenInGame': bool(a.get_editor_property('hidden'))}
        loc = a.get_actor_location()
        rot = a.get_actor_rotation()
        d['locationCm'] = [round(loc.x, 2), round(loc.y, 2), round(loc.z, 2)]
        d['rotation'] = [round(rot.pitch, 2), round(rot.yaw, 2), round(rot.roll, 2)]
        o, e = a.get_actor_bounds(False)
        d['boundsOrigin'] = [round(o.x, 1), round(o.y, 1), round(o.z, 1)]
        d['boundsExtent'] = [round(e.x, 1), round(e.y, 1), round(e.z, 1)]
        try:
            comp = a.get_editor_property('decal')
            s = comp.get_editor_property('decal_size')
            d['decalSizeCm'] = [round(s.x, 2), round(s.y, 2), round(s.z, 2)]
            d['decalMaterial'] = P(comp.get_editor_property('decal_material'))
        except Exception as err:
            d['decalComponent'] = 'unavailable: %r' % (err,)
        return d

    def do_decal(self, target, hide):
        u, r = self.u, self.r
        if target not in MAPS:
            raise RuntimeError('Unknown map key ' + target)
        mp = MAPS[target]
        umap = CONTENT / (mp + '.umap')
        r['stage'] = 'hash_before'
        self.save()
        before = tree_hashes()
        r['mapSha256Before'] = sha(umap)
        r['otherMapsBefore'] = {k: sha(CONTENT / (v + '.umap')) for k, v in MAPS.items() if k != target}
        cp = CHECKPOINT_ROOT / ('PrecinctDecal-%s-%s' % (target, self.stamp))
        cp.mkdir(parents=True, exist_ok=False)
        shutil.copy2(umap, cp / 'Walkthrough.umap')
        r['checkpoint'] = {'file': str(cp / 'Walkthrough.umap'), 'sha256': sha(cp / 'Walkthrough.umap')}
        les = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if not les.load_level('/Game/' + mp):
            raise RuntimeError('load_level failed')
        a = self.find_decal()
        r['decalBefore'] = self.decal_values(a)
        want = bool(hide)
        if r['decalBefore']['hiddenInGame'] == want:
            r['status'] = 'already_in_target_state'
            r['note'] = 'Nothing to change; map not saved.'
            return
        a.modify()
        a.set_actor_hidden_in_game(want)
        if bool(a.get_editor_property('hidden')) != want:
            raise RuntimeError('bHidden did not take')
        r['stage'] = 'save'
        self.save()
        if not les.save_current_level():
            raise RuntimeError('save_current_level returned False (zombie editor holding the map?)')
        r['mapsSaved'].append(mp)
        r['mapSha256After'] = sha(umap)
        if r['mapSha256After'] == r['mapSha256Before']:
            raise RuntimeError('Map bytes did not change after save')
        r['decalAfterInProcess'] = self.decal_values(self.find_decal())
        r['stage'] = 'hash_after'
        self.save()
        after = tree_hashes()
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        r['contentDiff'] = changed
        illegal = [k for k in changed if k != mp + '.umap']
        r['illegalChanges'] = illegal
        r['otherMapsAfter'] = {k: sha(CONTENT / (v + '.umap')) for k, v in MAPS.items() if k != target}
        if illegal or r['otherMapsAfter'] != r['otherMapsBefore']:
            raise RuntimeError('Something other than the target map changed: %s' % illegal[:20])
        r['restore'] = ('-PMDecalRestore=%s sets bHidden back to False under the same guard; or copy %s over %s with no '
                        'editor running (that also discards any later edits to this map).' % (target, r['checkpoint']['file'], umap))
        r['status'] = 'decal_hidden' if hide else 'decal_restored'


def main():
    import unreal as u
    cmd = u.SystemLibrary.get_command_line()
    apply_m = re.search(r'-PMApply(?=\s|$)', cmd)
    v2_m = re.search(r'-PMApplyV2(?=\s|$)', cmd)
    v3_m = re.search(r'-PMApplyV3(?=\s|$)', cmd)
    verify_m = re.search(r'-PMVerify=(?:"([^"]+)"|([^\s]+))', cmd)
    revert_m = re.search(r'-PMRevert=(?:"([^"]+)"|([^\s]+))', cmd)
    hide_m = re.search(r'-PMDecalHide=([A-Za-z0-9]+)', cmd)
    restore_m = re.search(r'-PMDecalRestore=([A-Za-z0-9]+)', cmd)
    retone_m = re.search(r'-PMRetone=([A-Za-z0-9]+)', cmd)
    far_m = re.search(r'-PMFarStrength=([0-9]+(?:\.[0-9]+)?)', cmd)
    close_m = re.search(r'-PMCloseFadeFar=([0-9]+(?:\.[0-9]+)?)', cmd)   # cp20: optional, retone only
    modes = [n for n, h in (('apply', apply_m), ('applyv2', v2_m), ('applyv3', v3_m), ('verify', verify_m), ('revert', revert_m),
                            ('decalhide', hide_m), ('decalrestore', restore_m), ('retone', retone_m)) if h]
    if len(modes) != 1:
        raise RuntimeError('Pass exactly one mode. Command line: %s' % cmd)
    mode = modes[0]
    target = (hide_m or restore_m).group(1) if mode in ('decalhide', 'decalrestore') else None
    if mode == 'retone':
        target = retone_m.group(1)
        if not far_m:
            raise RuntimeError('-PMRetone needs -PMFarStrength=<value>')
        far_strength = float(far_m.group(1))
        if not 0.5 <= far_strength <= 1.6:
            raise RuntimeError('MacroFarStrength %s outside the sane 0.5-1.6 range (a lerp past ~1.6 drives '
                               'joint pixels toward black)' % far_strength)
    run = Run(u, mode, target)
    run.r['commandLine'] = cmd
    try:
        if mode == 'apply':
            run.do_apply()
        elif mode == 'applyv2':
            run.do_apply_v2()
        elif mode == 'applyv3':
            run.do_apply_v2(v3=True)
        elif mode == 'verify':
            m = verify_m
            run.do_verify(Path(m.group(1) or m.group(2)), '-PMVerifyMaps' in cmd)
        elif mode == 'revert':
            m = revert_m
            run.do_revert(Path(m.group(1) or m.group(2)))
        elif mode == 'retone':
            close_far = float(close_m.group(1)) if close_m else None
            if close_far is not None and not 0.0 <= close_far <= 1.0:
                raise RuntimeError('CloseFadeFarStrength %s outside 0-1' % close_far)
            run.do_retone(target, far_strength, close_far)
        else:
            run.do_decal(target, mode == 'decalhide')
    except Exception as err:
        run.r['status'] = 'failed'
        run.r['error'] = repr(err)
        run.r['traceback'] = traceback.format_exc()
        run.save()
        u.log_error('PRECINCT_MACRO_%s FAILED %s: %r' % (mode.upper(), run.path, err))
        raise
    finally:
        run.save()
    u.log('PRECINCT_MACRO_%s %s status=%s' % (mode.upper(), run.path, run.r['status']))


main()

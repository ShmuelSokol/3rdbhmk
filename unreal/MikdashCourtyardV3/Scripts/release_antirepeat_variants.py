"""Anti-repeat attempt 3: layout-identical V5 tile variants, picked per STONE by a stock-node hash.

Shmuel, verbatim: "I don't wanna see, like, repeating patterns all over."

WHY THIS AND NOT A UV WARP. Attempt 1 (2026-09-09) warped the UV with explicit gradients and the wall
went flat on Nanite (x0.20). Attempt 2 (2026-09-11 00:40Z) warped it implicitly with per-cell mirror and
course-band offset: detail held (x0.88-0.90) but the one-tile autocorrelation fell only x0.84 and the
mirror cut stones (false ridges, 14 cm slivers, dashed bed joints), because the STONES straddle the 300 cm
cell edge. This pass changes the source instead: Scripts/create_herodian_ashlar_v5.py --surface-seed makes
extra tiles with the same layout RNG (same stones, same joints - proved pixel for pixel in
SourceAssets/material-review/HerodianAshlarV5Variants/joint-proof.json) and new surface seeds (tone,
family, blotches, weathering, pitting, chips, drafted-margin widths, boss projection, mottle).

WHY PER STONE, NOT PER CELL. A per-cell pick puts the variant boundary on the cell edge, which runs through
every stone that straddles it - and per-stone tone is exactly what the variants change, so that would be a
vertical tone step through the middle of those stones: attempt 2's mid-block seam in a new form. A
nearest-sampled, unmipped StoneKey texture (layout only, identical for every variant) gives the shader each
pixel's offset to its stone's anchor, so floor(u - d) is the stone's home cell on every pixel of that stone,
including across the tile edge. The hash of (home cell, course cell, stone index) picks the variant, so the
switch only ever happens at a joint.

WHAT THE MASTER IS. M_AntiRepeat_TriplanarVariants: M_PBR_Tiled's triplanar graph node for node (same
projection, blend exponent, UDN-style world normal, AlbedoFlatness/Tint tail), with each plane's Albedo,
ARM and Normal a 0/1-weighted sum over the variant slots. Stock nodes only, no Custom node, no ddx/ddy:
every TextureSample takes implicit derivatives of a UV that is continuous everywhere, so mip selection is
M_PBR_Tiled's own. VariantEnable = 0 selects slot A (the live T_HerodianV5b_* set) everywhere, which is
M_PBR_Tiled's output.

  -ARVariantsBuild                  checkpoint the namespace, prove the sources, import the new textures to
                                    FRESH names, build the master and the Ashlar/Trim instances, save, read
                                    back -> antirepeat-variantsbuild-<stamp>.json (status
                                    BUILT_SAVED_READBACK_APPLY_PENDING, samplingMode 'variants'). Maps untouched.
  -ARVariantsVerify=<build receipt> fresh-process reopen and readback of every built asset. No writes.
  -ARVariantsRevert=<build receipt> delete the built assets (refuses while anything else references them)
                                    and prove the namespace is byte-identical to the build checkpoint.

Apply / verify / revert on a MAP are release_antirepeat.py's, unchanged: -AntiRepeatApply=<this receipt>
resolves samplingAssets.variants from the receipt, and its evidence gate needs a PASS frame for 'variants'.
Commandlets run detached, one engine process at a time.
"""
import json
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_antirepeat as ra  # noqa: E402

ROOT = ra.ROOT
MODE = 'variants'


def enum_name(value):
    """UE 5.8 prints enums as '<TextureAddress.TA_WRAP: 0>'. Return the member name, never the text."""
    m = re.search(r'\.([A-Za-z0-9_]+)(?::|>|$)', str(value))
    return m.group(1) if m else str(value)


COPY_TEXTURE_PROPS = ('compression_settings', 'srgb', 'lod_group', 'address_x', 'address_y', 'filter',
                      'mip_gen_settings', 'virtual_texture_streaming', 'lod_bias', 'max_texture_size',
                      'flip_green_channel', 'never_stream', 'compression_no_alpha')


class VariantsNative(ra.Native):
    def __init__(self, ue, spec, mode, stamp):
        super().__init__(ue, spec, mode, stamp, None, False, 1, False, MODE, False, None)
        # No map is a target here, so EVERY target map (both shipping maps and the frame-trial copy) joins
        # the protected set: the build must prove it saved none of them.
        self.other_map_file = [t['mapFile'] for t in spec['targets'].values()]
        self.report['variantsScript'] = 'Scripts/release_antirepeat_variants.py'
        self.report['variantsScriptSha256'] = ra.sha(Path(__file__))
        self.write()

    # ---------------------------------------------------------------------------- textures
    def texture_row(self, tex):
        row = {'path': ra.asset_path(tex), 'class': tex.get_class().get_name()}
        for prop in COPY_TEXTURE_PROPS:
            try:
                v = tex.get_editor_property(prop)
            except Exception:  # noqa: BLE001
                continue
            row[prop] = v if isinstance(v, (bool, int, float)) else enum_name(v)
        for getter in ('blueprint_get_size_x', 'get_size_x'):
            if hasattr(tex, getter):
                row['size'] = [int(getattr(tex, getter)()), int(getattr(tex, getter.replace('_x', '_y'))())]
                break
        return row

    def import_one(self, asset, cfg):
        u = self.u
        png = ROOT / cfg['png']
        folder, name = asset.rsplit('/', 1)
        rec = {'asset': asset, 'png': cfg['png'], 'pngSha256': ra.sha(png), 'kind': cfg['kind']}
        if self.assets.does_asset_exist(asset):
            # The V4/V5 importer trap: an existing path is reused without re-reading the file.
            raise RuntimeError('%s already exists; this pass imports to fresh names only' % asset)
        task = u.AssetImportTask()
        for k, v in dict(filename=str(png), destination_path=folder, destination_name=name, automated=True,
                         replace_existing=False, save=False).items():
            task.set_editor_property(k, v)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objs = list(task.get_objects())
        if len(objs) != 1 or not isinstance(objs[0], u.Texture2D):
            raise RuntimeError('Import of %s produced %s' % (png.name, [type(o).__name__ for o in objs]))
        tex = objs[0]
        if cfg['kind'] == 'StoneKey':
            st = cfg['settings']
            tex.set_editor_property('compression_settings', getattr(u.TextureCompressionSettings, st['compression']))
            tex.set_editor_property('srgb', bool(st['srgb']))
            tex.set_editor_property('lod_group', getattr(u.TextureGroup, st['lodGroup']))
            tex.set_editor_property('filter', getattr(u.TextureFilter, st['filter']))
            tex.set_editor_property('mip_gen_settings', getattr(u.TextureMipGenSettings, st['mipGen']))
            tex.set_editor_property('address_x', getattr(u.TextureAddress, st['address']))
            tex.set_editor_property('address_y', getattr(u.TextureAddress, st['address']))
            try:
                tex.set_editor_property('virtual_texture_streaming', False)
            except Exception:  # noqa: BLE001
                pass
            want = {'compression_settings': st['compression'], 'srgb': bool(st['srgb']), 'lod_group': st['lodGroup'],
                    'filter': st['filter'], 'mip_gen_settings': st['mipGen'], 'address_x': st['address'],
                    'address_y': st['address']}
        else:
            # Every setting copied from the LIVE V5b texture of the same kind, so slot B/C samples exactly
            # the way slot A does (same compression, sRGB, group, address, filter, mips, streaming).
            src = u.load_asset(cfg['settingsFrom'])
            if src is None:
                raise RuntimeError('settings source missing: ' + cfg['settingsFrom'])
            want, skipped = {}, {}
            for prop in COPY_TEXTURE_PROPS:
                try:
                    v = src.get_editor_property(prop)
                except Exception:  # noqa: BLE001
                    continue
                try:
                    tex.set_editor_property(prop, v)
                except Exception as err:  # noqa: BLE001
                    skipped[prop] = repr(err)
                    continue
                want[prop] = v if isinstance(v, (bool, int, float)) else enum_name(v)
            rec['settingsNotCopied'] = skipped
            for must in ('compression_settings', 'srgb', 'lod_group', 'address_x', 'address_y'):
                if must in skipped:
                    raise RuntimeError('%s: could not copy %s from %s: %s' % (asset, must, cfg['settingsFrom'], skipped[must]))
            rec['settingsFrom'] = cfg['settingsFrom']
        if not self.assets.save_loaded_asset(tex, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + asset)
        row = self.texture_row(tex)
        bad = {k: (row.get(k), v) for k, v in want.items() if row.get(k) != v}
        if bad or row.get('size') != [2048, 2048]:
            raise RuntimeError('%s read back %s (size %s)' % (asset, bad, row.get('size')))
        rec['readback'] = row
        rec['uassetSha256'] = ra.sha(ra.disk(asset))
        return tex, rec

    # ---------------------------------------------------------------------------- master
    def build_variants_master(self, textures):
        u, ml = self.u, self.ml
        mcfg = self.spec['masters']['TriplanarVariants']
        path = mcfg['asset']
        folder, name = path.rsplit('/', 1)
        if self.assets.does_asset_exist(path):
            raise RuntimeError('%s exists; masters are never rebuilt in place (delete_all_material_expressions '
                               'does not empty a graph)' % path)
        material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Material, u.MaterialFactoryNew())
        if not isinstance(material, u.Material):
            raise RuntimeError('Material factory failed for ' + path)
        material.set_editor_property('tangent_space_normal', bool(mcfg['tangentSpaceNormal']))
        rec = {'asset': path, 'nodeCount': 0, 'samplesPerPlane': {}}
        any_variant = next(iter(self.spec['variants'].values()))

        def node(cls, x, y, **props):
            e = ml.create_material_expression(material, cls, x, y)
            if e is None:
                raise RuntimeError('create_material_expression failed for %s' % cls.__name__)
            for k, v in props.items():
                e.set_editor_property(k, v)
            rec['nodeCount'] += 1
            return e

        def wire(src, tgt, pin):
            self._wire(material, src, tgt, pin)
            return tgt

        def bin_(cls, a, b, x, y, **props):
            n = node(cls, x, y, **props)
            wire(a, n, 'A')
            wire(b, n, 'B')
            return n

        def cmul(a, c, x, y):
            return wire(a, node(u.MaterialExpressionMultiply, x, y, const_b=float(c)), 'A')

        def cadd(a, c, x, y):
            return wire(a, node(u.MaterialExpressionAdd, x, y, const_b=float(c)), 'A')

        def csub(a, c, x, y):
            return wire(a, node(u.MaterialExpressionSubtract, x, y, const_b=float(c)), 'A')

        def un(cls, a, x, y, pin='Input', **props):
            return wire(a, node(cls, x, y, **props), pin)

        def mask(a, x, y, **ch):
            # ALL FOUR channels set explicitly, every time. A new ComponentMask in 5.8 does not start empty:
            # setting only the wanted channels left R/G/B ticked, so mask(uv, g, b) came out float3 and the
            # cook failed with "Cannot cast from larger type LWCVector3 to smaller type LWCVector2" (arv3,
            # 2026-09-11) - which a -nullrhi editor compile never reports. M_PBR_Tiled's builder sets all four.
            props = {c: bool(ch.get(c, False)) for c in ('r', 'g', 'b', 'a')}
            return wire(a, node(u.MaterialExpressionComponentMask, x, y, **props), 'Input')

        scalars = {}

        def scalar(pname):
            if pname not in scalars:
                default = any_variant['scalars'].get(pname, 0.0)
                scalars[pname] = node(u.MaterialExpressionScalarParameter, -4200, 120 * len(scalars),
                                      parameter_name=pname, default_value=float(default))
            return scalars[pname]

        def sample(pname, uv, x, y):
            s = node(u.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=pname,
                     texture=textures[pname], sampler_type=ra._sampler_type(u, mcfg['textureParameters'][pname]))
            return wire(uv, s, 'UVs')

        # -- world UVs and blend weights: M_PBR_Tiled (release_pbr_architecture.py build_master_material) -----
        wp = node(u.MaterialExpressionWorldPosition, -4000, -400)
        wuv = bin_(u.MaterialExpressionDivide, wp, scalar('TilingCm'), -3800, -350)
        uvs = {'X': mask(wuv, -3600, -200, g=True, b=True),     # yz plane, projection along X
               'Y': mask(wuv, -3600, -350, r=True, b=True),     # xz plane, projection along Y
               'Z': mask(wuv, -3600, -500, r=True, g=True)}     # xy plane, projection along Z
        # The HASH path works on a float copy of the tile coordinate. WorldPosition / TilingCm is a Large World
        # Coordinate value; the texture UVs keep M_PBR_Tiled's own LWC path untouched, and only floor / fmod /
        # sine see the truncated copy (|uv| <= ~480 tiles in this 1.44 km scene, far inside fp32).
        if hasattr(u, 'MaterialExpressionTruncateLWC'):
            wuv_f = un(u.MaterialExpressionTruncateLWC, wuv, -3800, -250)
            rec['hashPathLWC'] = 'MaterialExpressionTruncateLWC'
        else:
            wuv_f = wuv
            rec['hashPathLWC'] = 'TruncateLWC not exposed in this build: LWC operands fed to the hash nodes directly'
        uvf = {'X': mask(wuv_f, -3600, -150, g=True, b=True), 'Y': mask(wuv_f, -3600, -300, r=True, b=True),
               'Z': mask(wuv_f, -3600, -450, r=True, g=True)}
        vn = node(u.MaterialExpressionVertexNormalWS, -4000, 200)
        powered = un(u.MaterialExpressionPower, un(u.MaterialExpressionAbs, vn, -3850, 200), -3700, 200, pin='Base',
                     const_exponent=float(mcfg['blendExponent']))
        ones = node(u.MaterialExpressionConstant3Vector, -3700, 330, constant=u.LinearColor(1.0, 1.0, 1.0, 1.0))
        weights = bin_(u.MaterialExpressionDivide, powered,
                       bin_(u.MaterialExpressionDotProduct, powered, ones, -3550, 250), -3400, 200)
        wplane = {'X': mask(weights, -3250, 120, r=True), 'Y': mask(weights, -3250, 200, g=True),
                  'Z': mask(weights, -3250, 280, b=True)}

        # -- per plane: which variant does this pixel's STONE use? ------------------------------------------
        hash_k = node(u.MaterialExpressionConstant3Vector, -3000, -900, constant=u.LinearColor(12.9898, 78.233, 37.719, 0.0))
        two_pi = node(u.MaterialExpressionConstant, -3000, -820, r=6.2831853)
        slots = mcfg['variantSlots']
        count = scalar('VariantCount')
        enable = scalar('VariantEnable')
        blended = {k: {} for k in ('Albedo', 'ARM', 'Normal')}
        for pi, plane in enumerate(('X', 'Y', 'Z')):
            y0 = -2400 + pi * 1600
            uv = uvs[plane]
            key = sample('StoneKey', uv, -3000, y0)
            d = csub(cmul(mask(key, -2850, y0, r=True), 2.0, -2700, y0), 1.0, -2550, y0)           # R -> d in [-1, 1]
            home = un(u.MaterialExpressionFloor,
                      bin_(u.MaterialExpressionSubtract, mask(uvf[plane], -2850, y0 + 80, r=True), d, -2400, y0), -2250, y0)
            vcell = un(u.MaterialExpressionFloor, mask(uvf[plane], -2850, y0 + 160, g=True), -2250, y0 + 80)
            stone = un(u.MaterialExpressionFloor,
                       cadd(cmul(mask(key, -2850, y0 + 240, g=True), 15.0, -2700, y0 + 240), 0.5, -2550, y0 + 240),
                       -2400, y0 + 240)                                                            # G = index * 17 / 255
            v3 = bin_(u.MaterialExpressionAppendVector,
                      bin_(u.MaterialExpressionAppendVector, home, vcell, -2100, y0 + 40), stone, -1950, y0 + 80)
            arg = bin_(u.MaterialExpressionFmod, bin_(u.MaterialExpressionDotProduct, v3, hash_k, -1800, y0 + 80),
                       two_pi, -1650, y0 + 80)
            sine = un(u.MaterialExpressionSine, arg, -1500, y0 + 80, period=6.2831853)          # sin(x), not sin(2 pi x)
            h = un(u.MaterialExpressionFrac, cmul(sine, 43758.5453, -1350, y0 + 80), -1200, y0 + 80)
            idx = bin_(u.MaterialExpressionMultiply,
                       un(u.MaterialExpressionFloor, bin_(u.MaterialExpressionMultiply, h, count, -1050, y0 + 80), -900, y0 + 80),
                       enable, -750, y0 + 80)
            # w_k = saturate(1 - |idx - k|): exactly 1 on the chosen slot, 0 elsewhere
            wk = []
            for k in range(len(slots)):
                diff = csub(idx, float(k), -600, y0 + 40 * k) if k else idx
                wk.append(un(u.MaterialExpressionSaturate,
                             un(u.MaterialExpressionOneMinus, un(u.MaterialExpressionAbs, diff, -450, y0 + 40 * k), -300, y0 + 40 * k),
                             -150, y0 + 40 * k))
            rec['samplesPerPlane'][plane] = 1
            for ki, kind in enumerate(('Albedo', 'ARM', 'Normal')):
                acc = None
                for k, suffix in enumerate(slots):
                    s = sample(kind + suffix, uv, 0, y0 + 400 + ki * 300 + k * 90)
                    rec['samplesPerPlane'][plane] += 1
                    term = bin_(u.MaterialExpressionMultiply, s, wk[k], 200, y0 + 400 + ki * 300 + k * 90)
                    acc = term if acc is None else bin_(u.MaterialExpressionAdd, acc, term, 350, y0 + 400 + ki * 300 + k * 90)
                blended[kind][plane] = acc

        def blend3(parts, x, y):
            mx = bin_(u.MaterialExpressionMultiply, parts['X'], wplane['X'], x, y - 80)
            my = bin_(u.MaterialExpressionMultiply, parts['Y'], wplane['Y'], x, y)
            mz = bin_(u.MaterialExpressionMultiply, parts['Z'], wplane['Z'], x, y + 80)
            return bin_(u.MaterialExpressionAdd, bin_(u.MaterialExpressionAdd, mx, my, x + 150, y - 40), mz, x + 300, y)

        # -- albedo, ARM, normal tails: M_PBR_Tiled's, unchanged -----------------------------------------------
        albedo = blend3(blended['Albedo'], 700, -800)
        flat = node(u.MaterialExpressionLinearInterpolate, 1100, -800, const_b=1.0)
        wire(albedo, flat, 'A')
        wire(scalar('AlbedoFlatness'), flat, 'Alpha')
        tint = node(u.MaterialExpressionVectorParameter, 1100, -600, parameter_name='Tint',
                    default_value=u.LinearColor(1.0, 1.0, 1.0, 1.0))
        base = bin_(u.MaterialExpressionMultiply, flat, tint, 1300, -750)
        arm = blend3(blended['ARM'], 700, -100)
        ao = mask(arm, 1100, -180, r=True)
        rough = bin_(u.MaterialExpressionMultiply, mask(arm, 1100, -60, g=True), scalar('RoughnessScale'), 1300, -60)
        zero = node(u.MaterialExpressionConstant, 700, 900, r=0.0)
        nx, ny, nz = blended['Normal']['X'], blended['Normal']['Y'], blended['Normal']['Z']
        dev = {'X': bin_(u.MaterialExpressionAppendVector, zero, mask(nx, 700, 380, r=True, g=True), 850, 400),
               'Y': bin_(u.MaterialExpressionAppendVector,
                         bin_(u.MaterialExpressionAppendVector, mask(ny, 700, 560, r=True), zero, 800, 600),
                         mask(ny, 700, 640, g=True), 900, 600),
               'Z': bin_(u.MaterialExpressionAppendVector, mask(nz, 700, 780, r=True, g=True), zero, 850, 800)}
        deviation = blend3(dev, 1000, 600)
        scaled = bin_(u.MaterialExpressionMultiply, deviation, scalar('NormalStrength'), 1400, 600)
        normal = un(u.MaterialExpressionNormalize, bin_(u.MaterialExpressionAdd, vn, scaled, 1550, 550), 1700, 550,
                    pin='VectorInput')
        for src, prop in ((base, 'MP_BASE_COLOR'), (rough, 'MP_ROUGHNESS'), (scalar('Metallic'), 'MP_METALLIC'),
                          (normal, 'MP_NORMAL'), (ao, 'MP_AMBIENT_OCCLUSION')):
            if not ml.connect_material_property(src, '', getattr(u.MaterialProperty, prop)):
                raise RuntimeError('connect_material_property %s failed' % prop)
        # bUsedWithInstancedStaticMeshes lives on the PARENT UMaterial; without it the cook silently
        # substitutes the default material. Nanite likewise.
        for flag in ra.USAGE_FLAGS:
            ml.set_base_material_usage(material, getattr(u.MaterialUsage, flag), True)
        errors = [str(e) for e in (ml.recompile_material(material) or [])]
        rec['compileErrors'] = errors
        if errors:
            raise RuntimeError('%s failed to compile: %s' % (path, errors))
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        rec['customNodes'] = sum(1 for e in ml.get_material_expressions(material)
                                 if e.get_class().get_name() == 'MaterialExpressionCustom')
        if rec['customNodes']:
            raise RuntimeError('the variants master must be stock nodes only; found %d Custom nodes' % rec['customNodes'])
        rec['expressionCount'] = len(list(ml.get_material_expressions(material)))
        rec['texturesampleNodes'] = sum(1 for e in ml.get_material_expressions(material)
                                        if 'TextureSample' in e.get_class().get_name())
        rec.update(self.master_readback(material))
        rec['textureFetchesPerPixel'] = sum(rec['samplesPerPlane'].values())
        rec['statistics'] = self.material_statistics(material)
        rec['uassetSha256'] = ra.sha(ra.disk(path))
        return material, rec

    def master_readback(self, material):
        u, ml = self.u, self.ml
        mcfg = self.spec['masters']['TriplanarVariants']
        row = {'scalarParameters': sorted(str(n) for n in ml.get_scalar_parameter_names(material)),
               'textureParameters': sorted(str(n) for n in ml.get_texture_parameter_names(material)),
               'vectorParameters': sorted(str(n) for n in ml.get_vector_parameter_names(material)),
               'usage': {f: bool(ml.has_material_usage(material, getattr(u.MaterialUsage, f))) for f in ra.USAGE_FLAGS},
               'tangentSpaceNormal': bool(material.get_editor_property('tangent_space_normal')),
               'inputsWired': {}}
        for prop in ('MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_AMBIENT_OCCLUSION'):
            n = ml.get_material_property_input_node(material, getattr(u.MaterialProperty, prop))
            row['inputsWired'][prop] = n.get_class().get_name() if n else None
        missing = (set(mcfg['scalarParameters']) - set(row['scalarParameters'])) | \
                  (set(mcfg['textureParameters']) - set(row['textureParameters'])) | \
                  (set(mcfg['vectorParameters']) - set(row['vectorParameters']))
        if missing:
            raise RuntimeError('%s lacks parameters %s' % (mcfg['asset'], sorted(missing)))
        if not all(row['usage'].values()):
            raise RuntimeError('%s usage flags %s' % (mcfg['asset'], row['usage']))
        if not all(row['inputsWired'].values()):
            raise RuntimeError('%s has an unwired output: %s' % (mcfg['asset'], row['inputsWired']))
        return row

    def build_variants_instance(self, name, cfg, master):
        u, ml = self.u, self.ml
        path = cfg['newInstance']
        folder, asset_name = path.rsplit('/', 1)
        if self.assets.does_asset_exist(path):
            raise RuntimeError('%s exists; instances are built to fresh names' % path)
        inst = u.AssetToolsHelpers.get_asset_tools().create_asset(asset_name, folder, u.MaterialInstanceConstant,
                                                                  u.MaterialInstanceConstantFactoryNew())
        if not isinstance(inst, u.MaterialInstanceConstant):
            raise RuntimeError('MaterialInstanceConstant factory failed for ' + path)
        ml.set_material_instance_parent(inst, master)
        if ra.asset_path(inst.get_editor_property('parent')) != ra.asset_path(master):
            inst.set_editor_property('parent', master)
            ml.update_material_instance(inst)
        if ra.asset_path(inst.get_editor_property('parent')) != ra.asset_path(master):
            raise RuntimeError('Parent did not take on ' + path)
        for pname, tpath in cfg['textures'].items():
            self.set_param(inst, 'texture', pname, u.load_asset(tpath))
        for pname, value in cfg['scalars'].items():
            self.set_param(inst, 'scalar', pname, value)
        self.set_param(inst, 'vector', 'Tint', cfg['tint'])
        for flag in ra.USAGE_FLAGS:
            ml.set_material_usage_override(inst, getattr(u.MaterialUsage, flag), True, True)
        ml.update_material_instance(inst)
        if not self.assets.save_loaded_asset(inst, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        row = self.instance_values(inst, cfg)
        self.check_instance(row, name, cfg)
        return inst, {'asset': path, 'master': ra.asset_path(master), 'replaces': cfg['replaces'], 'readback': row,
                      'statistics': self.material_statistics(inst), 'uassetSha256': ra.sha(ra.disk(path))}

    # ---------------------------------------------------------------------------- modes
    def source_proof(self):
        src = self.spec['samplingAssets'][MODE]['source']
        proof = json.loads((ROOT / src['jointProof']).read_text(encoding='utf-8-sig'))
        if proof.get('status') != 'JOINTS_IDENTICAL':
            raise RuntimeError('joint proof status %r, need JOINTS_IDENTICAL' % proof.get('status'))
        files = proof.get('files', {})
        bad = []
        for asset, cfg in src['imports'].items():
            want = files.get(cfg['png'])
            got = ra.sha(ROOT / cfg['png'])
            if want != got:
                bad.append((cfg['png'], want, got))
        if bad:
            raise RuntimeError('source PNGs differ from the proved files: %s' % bad)
        return {'path': src['jointProof'], 'sha256': ra.sha(ROOT / src['jointProof']), 'status': proof['status'],
                'summary': proof.get('summary')}

    def new_asset_paths(self):
        src = self.spec['samplingAssets'][MODE]['source']
        paths = list(src['imports'])
        paths.append(self.spec['masters']['TriplanarVariants']['asset'])
        paths += [c['newInstance'] for c in self.spec['variants'].values()]
        return paths

    def do_variants_build(self):
        u = self.u
        spec = self.scope_to_priority()
        r = self.report
        self.guard_project()
        existing = [p for p in self.new_asset_paths() if self.assets.does_asset_exist(p)]
        if existing:
            raise RuntimeError('refusing: built asset paths already exist: %s' % existing)
        r['sourceProof'] = self.source_proof()
        r['buildCheckpoint'] = self.checkpoint_namespace('VariantsBuild')
        r['protectedBefore'] = self.protected()
        r['parityBefore'] = {n: self.parity_row(c['replaces']) for n, c in spec['variants'].items()}
        r['parityChecks'] = {n: self.check_parity(r['parityBefore'][n], n, c) for n, c in spec['variants'].items()}
        self.stage('checked', variants=sorted(spec['variants']))
        textures, r['textures'] = {}, {}
        for asset, cfg in spec['samplingAssets'][MODE]['source']['imports'].items():
            _, r['textures'][asset] = self.import_one(asset, cfg)
            self.stage('imported', asset=asset)
        # the master's parameter defaults are the Ashlar set (any variant would do; instances set all)
        first = spec['variants']['Ashlar']
        for pname, tpath in first['textures'].items():
            textures[pname] = u.load_asset(tpath)
            if textures[pname] is None:
                raise RuntimeError('texture missing: ' + tpath)
        r['textureAddressModes'] = self.texture_address_modes()
        if r['textureAddressModes']['nonWrap']:
            raise RuntimeError('every sampled texture must be TA_WRAP: %s' % r['textureAddressModes']['nonWrap'])
        master, r['master'] = self.build_variants_master(textures)
        self.stage('master_saved')
        r['instances'] = {}
        for name, cfg in spec['variants'].items():
            _, r['instances'][name] = self.build_variants_instance(name, cfg, master)
            self.stage('instance_saved_' + name)
        dirty = self.dirty_content_names()
        if dirty:
            raise RuntimeError('Packages still dirty after saves: %s' % dirty)
        r['parityAfter'] = {n: self.parity_row(c['replaces']) for n, c in spec['variants'].items()}
        if r['parityAfter'] != r['parityBefore']:
            raise RuntimeError('A replaced material changed during the build')
        r['diskResolved'] = {}
        for name, cfg in spec['variants'].items():
            row = self.instance_values(u.load_asset(cfg['newInstance']), cfg)
            self.check_instance(row, name, cfg)
            pointers = {'self': cfg['newInstance'], 'parent': row['parent']}
            pointers.update({'texture:' + k: v for k, v in row['textures'].items()})
            r['diskResolved'][name] = self.resolve_on_disk(cfg['newInstance'], pointers)
        ns = ROOT / 'Content' / spec['namespace'][6:]
        moved = sorted(rel for rel, digest in r['buildCheckpoint']['files'].items() if ra.sha(ns / rel) != digest)
        r['preexistingNamespaceAssetsChanged'] = moved
        if moved:
            raise RuntimeError('The build rewrote pre-existing assets: %s' % moved)
        r['newAssetHashes'] = {p: ra.sha(ra.disk(p)) for p in self.new_asset_paths()}
        r['shaderCost'] = {'textureFetchesPerPixel': {'M_PBR_Tiled': 9, 'variants': r['master']['textureFetchesPerPixel']},
                           'note': 'counted from the graph; -nullrhi builds no shader map, so instruction counts are not measurable here'}
        r['revertCommand'] = '-ARVariantsRevert="%s"' % self.receipt_path
        r['status'] = 'BUILT_SAVED_READBACK_APPLY_PENDING'
        return r

    def do_variants_verify(self, receipt_path):
        u = self.u
        spec = self.scope_to_priority()
        r = self.report
        prior = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
        r['buildReceipt'] = {'path': str(receipt_path), 'sha256': ra.sha(receipt_path), 'status': prior.get('status')}
        r['hashes'] = {p: {'receipt': d, 'now': ra.sha(ra.disk(p)) if ra.disk(p).exists() else None}
                       for p, d in prior['newAssetHashes'].items()}
        changed = [p for p, v in r['hashes'].items() if v['receipt'] != v['now']]
        r['texturesReadback'] = {}
        for asset, cfg in spec['samplingAssets'][MODE]['source']['imports'].items():
            row = self.texture_row(u.load_asset(asset))
            r['texturesReadback'][asset] = row
            if cfg['kind'] == 'StoneKey':
                st = cfg['settings']
                want = {'compression_settings': st['compression'], 'srgb': False, 'filter': st['filter'],
                        'mip_gen_settings': st['mipGen'], 'address_x': st['address'], 'address_y': st['address']}
            else:
                src = self.texture_row(u.load_asset(cfg['settingsFrom']))
                want = {k: src[k] for k in src if k not in ('path', 'size')}
            bad = {k: (row.get(k), v) for k, v in want.items() if row.get(k) != v}
            if bad:
                changed.append('%s settings %s' % (asset, bad))
        r['master'] = self.master_readback(u.load_asset(spec['masters']['TriplanarVariants']['asset']))
        for name, cfg in spec['variants'].items():
            row = self.instance_values(u.load_asset(cfg['newInstance']), cfg)
            self.check_instance(row, name, cfg)
            r.setdefault('instances', {})[name] = row
        r['problems'] = changed
        r['status'] = 'FRESH_PROCESS_VERIFIED' if not changed else 'FRESH_PROCESS_MISMATCH'
        return r

    def do_variants_revert(self, receipt_path):
        u = self.u
        spec = self.scope_to_priority()
        r = self.report
        prior = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
        r['buildReceipt'] = {'path': str(receipt_path), 'sha256': ra.sha(receipt_path), 'status': prior.get('status')}
        self.guard_project()
        ours = set(prior.get('newAssetHashes', {}))
        referenced = {}
        for p in ours:
            if not self.assets.does_asset_exist(p):
                continue
            refs = [str(x).split('.')[0] for x in (self.assets.find_package_referencers_for_asset(p, False) or [])]
            outside = sorted(x for x in refs if x not in ours)
            if outside:
                referenced[p] = outside
        if referenced:
            raise RuntimeError('refusing: built assets are still referenced (revert the map applies first): %s' % referenced)
        deleted = []
        # instances first, then the master, then the textures
        order = sorted(ours, key=lambda p: (0 if '/MI_' in p else 1 if '/M_' in p else 2))
        for p in order:
            if self.assets.does_asset_exist(p):
                if not self.assets.delete_asset(p):
                    raise RuntimeError('delete_asset failed for ' + p)
                deleted.append(p)
        r['deleted'] = deleted
        left = [p for p in ours if ra.disk(p).exists()]
        if left:
            raise RuntimeError('still on disk after delete: %s' % left)
        cp = prior.get('buildCheckpoint', {})
        ns = ROOT / 'Content' / spec['namespace'][6:]
        r['namespaceMatchesCheckpoint'] = all(ra.sha(ns / rel) == d for rel, d in cp.get('files', {}).items())
        if not r['namespaceMatchesCheckpoint']:
            raise RuntimeError('namespace differs from the build checkpoint %s' % cp.get('path'))
        r['status'] = 'REVERTED_ASSETS_DELETED'
        return r


def _native_main():
    import unreal as ue
    cmd = ue.SystemLibrary.get_command_line()
    build_m = re.search(r'-ARVariantsBuild(?=\s|$)', cmd)
    verify_m = re.search(r'-ARVariantsVerify=(?:"([^"]+)"|([^\s]+))', cmd)
    revert_m = re.search(r'-ARVariantsRevert=(?:"([^"]+)"|([^\s]+))', cmd)
    hits = [m for m in (build_m, verify_m, revert_m) if m]
    if len(hits) != 1:
        # A commandlet's flags are not in sys.argv; a script that finds no mode must fail loudly, not exit 0.
        raise RuntimeError('Pass exactly one of -ARVariantsBuild, -ARVariantsVerify=<receipt>, -ARVariantsRevert=<receipt>; '
                           'command line was: %s' % cmd)
    spec = ra.resolve_spec(ra.load_spec(), MODE)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    mode = 'variantsbuild' if build_m else ('variantsverify' if verify_m else 'variantsrevert')
    native = VariantsNative(ue, spec, mode, stamp)
    protected_before = native.protected()
    try:
        if build_m:
            native.do_variants_build()
        else:
            m = verify_m or revert_m
            arg = Path(m.group(1) or m.group(2))
            if not arg.exists():
                raise RuntimeError('Receipt not found: %s' % arg)
            (native.do_variants_verify if verify_m else native.do_variants_revert)(arg)
    except Exception as exc:  # noqa: BLE001
        native.report['status'] = 'FAILED_' + mode.upper()
        native.report['errors'].append(repr(exc))
        native.report['traceback'] = traceback.format_exc()
        raise
    finally:
        native.report['protectedAfter'] = native.protected()
        native.report['protectedUnchanged'] = native.report['protectedAfter'] == protected_before
        if not native.report['protectedUnchanged']:
            native.report['protectedChangedFiles'] = sorted(
                k for k in set(protected_before) | set(native.report['protectedAfter'])
                if protected_before.get(k) != native.report['protectedAfter'].get(k))
            native.report['status'] = 'FAILED_PROTECTED_HASH_MISMATCH'
        native.write()
        ue.log('ARVARIANTS_%s %s status=%s' % (mode.upper(), native.receipt_path, native.report['status']))


if __name__ == '__main__':
    try:
        import unreal  # noqa: F401
    except ImportError:
        spec = ra.resolve_spec(ra.load_spec(), MODE)
        print(json.dumps({'masters': list(spec['masters']), 'variants': {n: {'newInstance': c['newInstance'],
                          'textures': c['textures'], 'scalars': c['scalars']} for n, c in spec['variants'].items()
                          if 'TriplanarVariants' == c.get('master')},
                          'schemeProblems': ra.scheme_problems(spec)}, indent=1))
    else:
        _native_main()

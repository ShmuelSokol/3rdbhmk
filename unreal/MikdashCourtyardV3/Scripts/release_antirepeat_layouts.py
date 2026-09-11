"""Anti-repeat attempt 4: the Herodian Ashlar stone LAYOUT itself stops repeating. Build / verify / revert.

Shmuel, verbatim: "I don't wanna see, like, repeating patterns all over."

Attempt 3 (release_antirepeat_variants.py) picked one of three SURFACES per stone on ONE layout: tone alternation gone,
detail x0.98, but the rising joints recurred every 300 cm (joint repeat x0.93 of the control under acceptance v2).
This mode changes the LAYOUT: 15 slices from Scripts/create_herodian_ashlar_layouts.py (1-D Wang edges per course,
V5 bed joints, 3 boundary-stone types per 300 cm boundary), stacked into three Texture2DArrays (Albedo, Normal, ARM),
and a stock-node master that picks the slice per pixel from the analytic joint lines:

  per plane: u, v = world / TilingCm; k = floor(u), fu = frac(u); cy = floor(v), fv = frac(v)
    course c from CourseBounds (V5's two inner bed joints, tile units)
    a = type of boundary k, b = type of boundary k+1: floor(3 * hash(k|k+1, cy, 0))  (shared by a cell row's courses)
    q = LayoutQ<c>[a], p = LayoutP<c>[b] (tile units); left boundary stone if fu < q, right if fu > 1 - p
    slice: left -> diag(a, vL), right -> diag(b, vR), interior -> a == b ? diag(a, vI) : 3a + b
           diag(x, 0) = 4x, diag(x, v > 0) = 9 + 2x + (v - 1); vL/vR = floor(3 hash(boundary, cy, c + 10)),
           vI = floor(3 hash(k, cy, c + 20)) - so a boundary stone gets ONE slice on both sides of the tile edge
    TextureSampleParameter2DArray(float3(uv, slice)): implicit derivatives of the continuous world UV, 9 fetches per
    pixel (M_PBR_Tiled's count). No Custom node, no ddx/ddy.

The Trim is NOT rebuilt: it keeps attempt 3's per-stone variants instance, which the spec's samplingAssets.layouts
reuses (its hashes are checked, never rewritten). Apply / verify / revert on a map are release_antirepeat.py's.

  -ARLayoutsBuild                   checkpoint, prove the slices, import 45 PNGs to FRESH names (settings copied from
                                    the live T_HerodianV5b_Ashlar_*), build 3 Texture2DArrays, the master and the Ashlar
                                    instance, save, read back -> antirepeat-layoutsbuild-<stamp>.json
  -ARLayoutsVerify=<build receipt>  fresh-process readback. No writes.
  -ARLayoutsRevert=<build receipt>  delete the built assets (refuses while referenced), namespace byte-equal to checkpoint.
"""
import json
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_antirepeat as ra  # noqa: E402
import release_antirepeat_variants as rv  # noqa: E402

ROOT = ra.ROOT
MODE = 'layouts'
GAIN = 100000.0          # hard step: saturate((x - edge) * GAIN), transition 1e-5 tile = 0.003 cm


class LayoutsNative(rv.VariantsNative):
    def __init__(self, ue, spec, mode, stamp):
        ra.Native.__init__(self, ue, spec, mode, stamp, None, False, 1, False, MODE, False, None)
        self.other_map_file = [t['mapFile'] for t in spec['targets'].values()]
        self.report['layoutsScript'] = 'Scripts/release_antirepeat_layouts.py'
        self.report['layoutsScriptSha256'] = ra.sha(Path(__file__))
        self.write()

    # ------------------------------------------------------------------------------------------ source
    def src(self):
        return self.spec['samplingAssets'][MODE]['source']

    def source_proof(self):
        src = self.src()
        proof = json.loads((ROOT / src['layoutProof']).read_text(encoding='utf-8-sig'))
        if proof.get('status') != 'LAYOUT_SLICES_PROVED':
            raise RuntimeError('layout proof status %r, need LAYOUT_SLICES_PROVED' % proof.get('status'))
        bad = []
        for asset, cfg in src['imports'].items():
            want = proof['files'][str(cfg['slice'])][cfg['kind']]['sha256']
            got = ra.sha(ROOT / cfg['png'])
            if want != got:
                bad.append((cfg['png'], want, got))
        if bad:
            raise RuntimeError('slice PNGs differ from the proved files: %s' % bad[:5])
        lay = json.loads((ROOT / src['layoutJson']).read_text(encoding='utf-8'))
        vec = self.spec['samplingAssets'][MODE]['variantOverrides']['Ashlar']['vectors']
        for c in range(3):
            for a in range(3):
                for key, idx in (('LayoutQ%d' % c, 1), ('LayoutP%d' % c, 0)):
                    if abs(vec[key][a] * 300.0 - lay['courses'][c][a][idx]) > 1e-6:
                        raise RuntimeError('spec %s[%d] does not match layout.json' % (key, a))
        return {'path': src['layoutProof'], 'sha256': ra.sha(ROOT / src['layoutProof']), 'status': proof['status'],
                'checks': proof.get('checks', {}).get('stoneLengthsCm')}

    def reused(self):
        out = {}
        for name, cfg in self.spec['samplingAssets'][MODE]['reusedFromVariants'].items():
            prior = json.loads((ROOT / cfg['buildReceipt']).read_text(encoding='utf-8-sig'))
            rows = {}
            for p, digest in prior['newAssetHashes'].items():
                if '_Trim' in p or p == cfg['master'] or '/M_' in p:
                    now = ra.sha(ra.disk(p)) if ra.disk(p).exists() else None
                    rows[p] = {'variantsBuild': digest, 'now': now}
                    if now != digest:
                        raise RuntimeError('reused %s changed since its variants build' % p)
            out[name] = rows
        return out

    def new_asset_paths(self):
        src = self.src()
        paths = list(src['imports'])
        paths += [a['asset'] for a in src['arrays'].values()]
        paths.append(self.spec['samplingAssets'][MODE]['newMasters']['TriplanarLayouts']['asset'])
        paths.append(self.spec['samplingAssets'][MODE]['instances']['Ashlar'])
        return paths

    # ------------------------------------------------------------------------------------------ arrays
    def build_array(self, kind, cfg, textures):
        u = self.u
        path = cfg['asset']
        folder, name = path.rsplit('/', 1)
        if self.assets.does_asset_exist(path):
            raise RuntimeError('%s exists; arrays are built to fresh names' % path)
        # Texture2DArray creation is behind a console variable in 5.8 (Texture2DArrayFactory.cpp:40).
        u.SystemLibrary.execute_console_command(None, 'r.AllowTexture2DArrayCreation 1')
        arr = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Texture2DArray, u.Texture2DArrayFactory())
        if not isinstance(arr, u.Texture2DArray):
            raise RuntimeError('Texture2DArray factory returned %r for %s' % (arr, path))
        slices = [textures[p] for p in cfg['slices']]
        # PostEditChangeProperty(SourceTextures): 1 entry -> UpdateSourceFromSourceTextures(true) (creates the source,
        # copies compression and LOD group from slice 0, forces NoMipmaps + NeverStream); more -> (false), which re-stacks
        # all slices. So seed with one, then set all fifteen.
        arr.set_editor_property('source_textures', [slices[0]])
        arr.set_editor_property('source_textures', slices)
        src = u.load_asset(cfg['settingsFrom'])
        for prop in ('compression_settings', 'srgb', 'lod_group'):
            arr.set_editor_property(prop, src.get_editor_property(prop))
        # Mips back ON (the create path turned them off): the V5 boss bevel survives only with a real mip chain.
        arr.set_editor_property('mip_gen_settings', src.get_editor_property('mip_gen_settings'))
        for prop in ('address_x', 'address_y'):
            arr.set_editor_property(prop, u.TextureAddress.TA_WRAP)
        try:
            arr.set_editor_property('address_z', u.TextureAddress.TA_CLAMP)
        except Exception:  # noqa: BLE001
            pass
        if not self.assets.save_loaded_asset(arr, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        row = self.array_row(arr)
        want = {'compression_settings': rv.enum_name(src.get_editor_property('compression_settings')),
                'srgb': bool(src.get_editor_property('srgb')),
                'mip_gen_settings': rv.enum_name(src.get_editor_property('mip_gen_settings')),
                'address_x': 'TA_WRAP', 'address_y': 'TA_WRAP', 'sourceTextures': cfg['slices']}
        bad = {k: (row.get(k), v) for k, v in want.items() if row.get(k) != v}
        if bad:
            raise RuntimeError('%s read back %s' % (path, bad))
        if row['mip_gen_settings'] == 'TMGS_NO_MIPMAPS':
            raise RuntimeError('%s has no mips' % path)
        return arr, {'asset': path, 'readback': row, 'uassetSha256': ra.sha(ra.disk(path)),
                     'uassetBytes': ra.disk(path).stat().st_size}

    def array_row(self, arr):
        row = {'path': ra.asset_path(arr), 'class': arr.get_class().get_name()}
        for prop in ('compression_settings', 'srgb', 'lod_group', 'mip_gen_settings', 'address_x', 'address_y',
                     'address_z', 'never_stream'):
            try:
                v = arr.get_editor_property(prop)
            except Exception:  # noqa: BLE001
                continue
            row[prop] = v if isinstance(v, (bool, int, float)) else rv.enum_name(v)
        row['sourceTextures'] = [ra.asset_path(t) for t in arr.get_editor_property('source_textures')]
        return row

    # ------------------------------------------------------------------------------------------ master
    def build_layouts_master(self, arrays):
        u, ml = self.u, self.ml
        mcfg = self.spec['masters']['TriplanarLayouts']
        path = mcfg['asset']
        folder, name = path.rsplit('/', 1)
        if self.assets.does_asset_exist(path):
            raise RuntimeError('%s exists; masters are never rebuilt in place' % path)
        material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Material, u.MaterialFactoryNew())
        material.set_editor_property('tangent_space_normal', bool(mcfg['tangentSpaceNormal']))
        rec = {'asset': path, 'nodeCount': 0, 'samplesPerPlane': {}}
        vcfg = self.spec['samplingAssets'][MODE]['variantOverrides']['Ashlar']

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

        def un(cls, a, x, y, pin='Input', **props):
            return wire(a, node(cls, x, y, **props), pin)

        def mask(a, x, y, **ch):
            # ALL FOUR channels set explicitly (5.8 starts a new ComponentMask with R, G, B ticked).
            props = {c: bool(ch.get(c, False)) for c in ('r', 'g', 'b', 'a')}
            return wire(a, node(u.MaterialExpressionComponentMask, x, y, **props), 'Input')

        def const(v, x, y):
            return node(u.MaterialExpressionConstant, x, y, r=float(v))

        def cmul(a, c, x, y):
            return wire(a, node(u.MaterialExpressionMultiply, x, y, const_b=float(c)), 'A')

        def cadd(a, c, x, y):
            return wire(a, node(u.MaterialExpressionAdd, x, y, const_b=float(c)), 'A')

        def csub(a, c, x, y):
            return wire(a, node(u.MaterialExpressionSubtract, x, y, const_b=float(c)), 'A')

        def add(a, b, x, y):
            return bin_(u.MaterialExpressionAdd, a, b, x, y)

        def sub(a, b, x, y):
            return bin_(u.MaterialExpressionSubtract, a, b, x, y)

        def mul(a, b, x, y):
            return bin_(u.MaterialExpressionMultiply, a, b, x, y)

        def sat(a, x, y):
            return un(u.MaterialExpressionSaturate, a, x, y)

        def step_gt(a, b, x, y):
            """1 where a > b (hard, stock nodes only)."""
            return sat(cmul(sub(a, b, x, y), GAIN, x + 60, y), x + 120, y)

        def append(a, b, x, y):
            return bin_(u.MaterialExpressionAppendVector, a, b, x, y)

        scalars, vectors = {}, {}

        def scalar(pname):
            if pname not in scalars:
                scalars[pname] = node(u.MaterialExpressionScalarParameter, -6200, 120 * len(scalars), parameter_name=pname,
                                      default_value=float(vcfg['scalars'].get(pname, 0.0)))
            return scalars[pname]

        def vector(pname):
            if pname not in vectors:
                v = vcfg['vectors'][pname]
                vectors[pname] = node(u.MaterialExpressionVectorParameter, -6200, 1400 + 140 * len(vectors), parameter_name=pname,
                                      default_value=u.LinearColor(*[float(x) for x in v]))
            return vectors[pname]

        def vec3(pname, x, y):
            return mask(vector(pname), x, y, r=True, g=True, b=True)

        hash_k = node(u.MaterialExpressionConstant3Vector, -5000, -1200, constant=u.LinearColor(12.9898, 78.233, 37.719, 0.0))
        two_pi = const(6.2831853, -5000, -1120)
        idx3 = node(u.MaterialExpressionConstant3Vector, -5000, -1040, constant=u.LinearColor(0.0, 1.0, 2.0, 0.0))

        def hash3(v3, x, y):
            arg = bin_(u.MaterialExpressionFmod, bin_(u.MaterialExpressionDotProduct, v3, hash_k, x, y), two_pi, x + 150, y)
            s = un(u.MaterialExpressionSine, arg, x + 300, y, period=6.2831853)
            return un(u.MaterialExpressionFrac, cmul(s, 43758.5453, x + 450, y), x + 600, y)

        def pick3(h, x, y):
            return un(u.MaterialExpressionFloor, cmul(h, 3.0, x, y), x + 150, y)

        def onehot(t, x, y):
            """float3: 1 in the slot t (0, 1 or 2)."""
            d = un(u.MaterialExpressionAbs, sub(t, idx3, x, y), x + 150, y)
            return sat(un(u.MaterialExpressionOneMinus, d, x + 300, y), x + 450, y)

        def diag(xt, v, x, y):
            """4x for surface 0, 9 + 2x + (v - 1) = 8 + 2x + v otherwise."""
            base = cmul(xt, 4.0, x, y)
            on = step_gt(v, const(0.5, x, y + 40), x + 150, y)
            extra = add(csub(cmul(xt, -2.0, x + 300, y + 40), -8.0, x + 450, y + 40), v, x + 600, y + 40)  # 8 - 2x + v
            return add(base, mul(on, extra, x + 750, y), x + 900, y)

        # world UVs and blend weights: M_PBR_Tiled's
        wp = node(u.MaterialExpressionWorldPosition, -6000, -400)
        wuv = bin_(u.MaterialExpressionDivide, wp, scalar('TilingCm'), -5800, -350)
        uvs = {'X': mask(wuv, -5600, -200, g=True, b=True), 'Y': mask(wuv, -5600, -350, r=True, b=True),
               'Z': mask(wuv, -5600, -500, r=True, g=True)}
        if hasattr(u, 'MaterialExpressionTruncateLWC'):
            wuv_f = un(u.MaterialExpressionTruncateLWC, wuv, -5800, -250)
            rec['hashPathLWC'] = 'MaterialExpressionTruncateLWC'
        else:
            wuv_f = wuv
            rec['hashPathLWC'] = 'TruncateLWC not exposed: LWC operands fed to the layout nodes directly'
        uvf = {'X': mask(wuv_f, -5600, -150, g=True, b=True), 'Y': mask(wuv_f, -5600, -300, r=True, b=True),
               'Z': mask(wuv_f, -5600, -450, r=True, g=True)}
        vn = node(u.MaterialExpressionVertexNormalWS, -6000, 200)
        powered = un(u.MaterialExpressionPower, un(u.MaterialExpressionAbs, vn, -5850, 200), -5700, 200, pin='Base',
                     const_exponent=float(mcfg['blendExponent']))
        ones = node(u.MaterialExpressionConstant3Vector, -5700, 330, constant=u.LinearColor(1.0, 1.0, 1.0, 1.0))
        weights = bin_(u.MaterialExpressionDivide, powered, bin_(u.MaterialExpressionDotProduct, powered, ones, -5550, 250), -5400, 200)
        wplane = {'X': mask(weights, -5250, 120, r=True), 'Y': mask(weights, -5250, 200, g=True),
                  'Z': mask(weights, -5250, 280, b=True)}
        bounds = vector('CourseBounds')
        b1 = mask(bounds, -5000, -900, r=True)
        b2 = mask(bounds, -5000, -820, g=True)
        zero = const(0.0, -5000, -740)
        one = const(1.0, -5000, -660)
        enable = scalar('LayoutEnable')
        samples = {'Albedo': 'AlbedoArray', 'ARM': 'ARMArray', 'Normal': 'NormalArray'}
        blended = {k: {} for k in samples}
        for pi, plane in enumerate(('X', 'Y', 'Z')):
            Y = -3000 + pi * 2600
            X = -4600
            uu = mask(uvf[plane], X, Y, r=True)
            vv = mask(uvf[plane], X, Y + 80, g=True)
            k = un(u.MaterialExpressionFloor, uu, X + 150, Y)
            fu = un(u.MaterialExpressionFrac, uu, X + 150, Y + 40)
            cy = un(u.MaterialExpressionFloor, vv, X + 150, Y + 80)
            fv = un(u.MaterialExpressionFrac, vv, X + 150, Y + 120)
            s1 = step_gt(fv, b1, X + 300, Y + 160)
            s2 = step_gt(fv, b2, X + 300, Y + 240)
            cm = append(append(un(u.MaterialExpressionOneMinus, s1, X + 500, Y + 160), sub(s1, s2, X + 500, Y + 240), X + 650, Y + 200),
                        s2, X + 800, Y + 200)                                        # float3 course one-hot
            cidx = add(s1, s2, X + 650, Y + 280)
            k1 = cadd(k, 1.0, X + 300, Y)
            kc = append(k, cy, X + 450, Y)
            k1c = append(k1, cy, X + 450, Y + 40)
            a = pick3(hash3(append(kc, zero, X + 600, Y), X + 750, Y), X + 1400, Y)
            b = pick3(hash3(append(k1c, zero, X + 600, Y + 40), X + 750, Y + 40), X + 1400, Y + 40)
            A = onehot(a, X + 1700, Y)
            B = onehot(b, X + 1700, Y + 40)
            qc = append(append(bin_(u.MaterialExpressionDotProduct, vec3('LayoutQ0', X + 1900, Y), A, X + 2050, Y),
                               bin_(u.MaterialExpressionDotProduct, vec3('LayoutQ1', X + 1900, Y + 40), A, X + 2050, Y + 40), X + 2200, Y),
                        bin_(u.MaterialExpressionDotProduct, vec3('LayoutQ2', X + 1900, Y + 80), A, X + 2050, Y + 80), X + 2350, Y)
            pc = append(append(bin_(u.MaterialExpressionDotProduct, vec3('LayoutP0', X + 1900, Y + 120), B, X + 2050, Y + 120),
                               bin_(u.MaterialExpressionDotProduct, vec3('LayoutP1', X + 1900, Y + 160), B, X + 2050, Y + 160), X + 2200, Y + 120),
                        bin_(u.MaterialExpressionDotProduct, vec3('LayoutP2', X + 1900, Y + 200), B, X + 2050, Y + 200), X + 2350, Y + 120)
            q = bin_(u.MaterialExpressionDotProduct, cm, qc, X + 2500, Y)
            p = bin_(u.MaterialExpressionDotProduct, cm, pc, X + 2500, Y + 120)
            is_l = step_gt(q, fu, X + 2650, Y)                                          # fu < q
            is_r = step_gt(fu, un(u.MaterialExpressionOneMinus, p, X + 2650, Y + 160), X + 2800, Y + 120)   # fu > 1 - p
            is_i = sat(sub(sub(one, is_l, X + 3000, Y + 60), is_r, X + 3150, Y + 60), X + 3300, Y + 60)
            c10 = cadd(cidx, 10.0, X + 800, Y + 320)
            c20 = cadd(cidx, 20.0, X + 800, Y + 360)
            v_l = pick3(hash3(append(kc, c10, X + 950, Y + 320), X + 1100, Y + 320), X + 1750, Y + 320)
            v_r = pick3(hash3(append(k1c, c10, X + 950, Y + 360), X + 1100, Y + 360), X + 1750, Y + 360)
            v_i = pick3(hash3(append(kc, c20, X + 950, Y + 400), X + 1100, Y + 400), X + 1750, Y + 400)
            s_l = diag(a, v_l, X + 2000, Y + 320)
            s_r = diag(b, v_r, X + 2000, Y + 440)
            eq = sat(un(u.MaterialExpressionOneMinus, un(u.MaterialExpressionAbs, sub(a, b, X + 2000, Y + 560), X + 2150, Y + 560),
                        X + 2300, Y + 560), X + 2450, Y + 560)
            pair = add(cmul(a, 3.0, X + 2000, Y + 640), b, X + 2150, Y + 640)
            s_diag_i = diag(a, v_i, X + 2000, Y + 720)
            s_i = add(mul(eq, s_diag_i, X + 3000, Y + 600), mul(un(u.MaterialExpressionOneMinus, eq, X + 2850, Y + 680), pair, X + 3000, Y + 680),
                      X + 3150, Y + 640)
            slc = add(add(mul(is_l, s_l, X + 3400, Y + 320), mul(is_r, s_r, X + 3400, Y + 440), X + 3550, Y + 380),
                      mul(is_i, s_i, X + 3400, Y + 560), X + 3700, Y + 450)
            slc = mul(slc, enable, X + 3850, Y + 450)
            uvw = append(uvs[plane], slc, X + 4000, Y + 450)
            rec['samplesPerPlane'][plane] = 0
            for ki, (kind, pname) in enumerate(samples.items()):
                s = node(u.MaterialExpressionTextureSampleParameter2DArray, X + 4200, Y + 300 * ki, parameter_name=pname,
                         texture=arrays[kind], sampler_type=ra._sampler_type(u, mcfg['textureParameters'][pname]))
                wire(uvw, s, 'UVs')
                rec['samplesPerPlane'][plane] += 1
                blended[kind][plane] = s

        def blend3(parts, x, y):
            mx = bin_(u.MaterialExpressionMultiply, parts['X'], wplane['X'], x, y - 80)
            my = bin_(u.MaterialExpressionMultiply, parts['Y'], wplane['Y'], x, y)
            mz = bin_(u.MaterialExpressionMultiply, parts['Z'], wplane['Z'], x, y + 80)
            return bin_(u.MaterialExpressionAdd, bin_(u.MaterialExpressionAdd, mx, my, x + 150, y - 40), mz, x + 300, y)

        # tails: M_PBR_Tiled's (as release_antirepeat_variants.py), RGB masks explicit on the array samples
        rgb = {kind: {pl: mask(blended[kind][pl], 300, -1200 + 90 * i + 300 * j, r=True, g=True, b=True)
                      for i, pl in enumerate(('X', 'Y', 'Z'))} for j, kind in enumerate(('Albedo', 'ARM'))}
        albedo = blend3(rgb['Albedo'], 700, -800)
        flat = node(u.MaterialExpressionLinearInterpolate, 1100, -800, const_b=1.0)
        wire(albedo, flat, 'A')
        wire(scalar('AlbedoFlatness'), flat, 'Alpha')
        tint = vec3('Tint', 1100, -600)
        base = bin_(u.MaterialExpressionMultiply, flat, tint, 1300, -750)
        arm = blend3(rgb['ARM'], 700, -100)
        ao = mask(arm, 1100, -180, r=True)
        rough = bin_(u.MaterialExpressionMultiply, mask(arm, 1100, -60, g=True), scalar('RoughnessScale'), 1300, -60)
        nx, ny, nz = blended['Normal']['X'], blended['Normal']['Y'], blended['Normal']['Z']
        dev = {'X': append(zero, mask(nx, 700, 380, r=True, g=True), 850, 400),
               'Y': append(append(mask(ny, 700, 560, r=True), zero, 800, 600), mask(ny, 700, 640, g=True), 900, 600),
               'Z': append(mask(nz, 700, 780, r=True, g=True), zero, 850, 800)}
        deviation = blend3(dev, 1000, 600)
        scaled = bin_(u.MaterialExpressionMultiply, deviation, scalar('NormalStrength'), 1400, 600)
        normal = un(u.MaterialExpressionNormalize, bin_(u.MaterialExpressionAdd, vn, scaled, 1550, 550), 1700, 550, pin='VectorInput')
        for src, prop in ((base, 'MP_BASE_COLOR'), (rough, 'MP_ROUGHNESS'), (scalar('Metallic'), 'MP_METALLIC'),
                          (normal, 'MP_NORMAL'), (ao, 'MP_AMBIENT_OCCLUSION')):
            if not ml.connect_material_property(src, '', getattr(u.MaterialProperty, prop)):
                raise RuntimeError('connect_material_property %s failed' % prop)
        for flag in ra.USAGE_FLAGS:
            ml.set_base_material_usage(material, getattr(u.MaterialUsage, flag), True)
        errors = [str(e) for e in (ml.recompile_material(material) or [])]
        rec['compileErrors'] = errors
        if errors:
            raise RuntimeError('%s failed to compile: %s' % (path, errors))
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        exprs = list(ml.get_material_expressions(material))
        rec['customNodes'] = sum(1 for e in exprs if e.get_class().get_name() == 'MaterialExpressionCustom')
        if rec['customNodes']:
            raise RuntimeError('stock nodes only; found %d Custom nodes' % rec['customNodes'])
        masks = [e for e in exprs if e.get_class().get_name() == 'MaterialExpressionComponentMask']
        rec['componentMasks'] = len(masks)
        rec['expressionCount'] = len(exprs)
        rec['textureFetchesPerPixel'] = sum(rec['samplesPerPlane'].values())
        rec.update(self.layouts_master_readback(material))
        rec['statistics'] = self.material_statistics(material)
        rec['uassetSha256'] = ra.sha(ra.disk(path))
        return material, rec

    def layouts_master_readback(self, material):
        u, ml = self.u, self.ml
        mcfg = self.spec['masters']['TriplanarLayouts']
        row = {'scalarParameters': sorted(str(n) for n in ml.get_scalar_parameter_names(material)),
               'textureParameters': sorted(str(n) for n in ml.get_texture_parameter_names(material)),
               'vectorParameters': sorted(str(n) for n in ml.get_vector_parameter_names(material)),
               'usage': {f: bool(ml.has_material_usage(material, getattr(u.MaterialUsage, f))) for f in ra.USAGE_FLAGS},
               'tangentSpaceNormal': bool(material.get_editor_property('tangent_space_normal')), 'inputsWired': {}}
        for prop in ('MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_AMBIENT_OCCLUSION'):
            n = ml.get_material_property_input_node(material, getattr(u.MaterialProperty, prop))
            row['inputsWired'][prop] = n.get_class().get_name() if n else None
        missing = (set(mcfg['scalarParameters']) - set(row['scalarParameters'])) | \
                  (set(mcfg['textureParameters']) - set(row['textureParameters'])) | \
                  (set(mcfg['vectorParameters']) - set(row['vectorParameters']))
        if missing:
            raise RuntimeError('%s lacks parameters %s' % (mcfg['asset'], sorted(missing)))
        if not all(row['usage'].values()) or not all(row['inputsWired'].values()):
            raise RuntimeError('%s usage %s / inputs %s' % (mcfg['asset'], row['usage'], row['inputsWired']))
        return row

    def build_layouts_instance(self, master):
        u, ml = self.u, self.ml
        cfg = self.spec['variants']['Ashlar']
        path = cfg['newInstance']
        folder, asset_name = path.rsplit('/', 1)
        if self.assets.does_asset_exist(path):
            raise RuntimeError('%s exists; instances are built to fresh names' % path)
        inst = u.AssetToolsHelpers.get_asset_tools().create_asset(asset_name, folder, u.MaterialInstanceConstant,
                                                                  u.MaterialInstanceConstantFactoryNew())
        ml.set_material_instance_parent(inst, master)
        if ra.asset_path(inst.get_editor_property('parent')) != ra.asset_path(master):
            inst.set_editor_property('parent', master)
            ml.update_material_instance(inst)
        for pname, tpath in cfg['textures'].items():
            self.set_param(inst, 'texture', pname, u.load_asset(tpath))
        for pname, value in cfg['scalars'].items():
            self.set_param(inst, 'scalar', pname, value)
        for pname, value in cfg['vectors'].items():
            self.set_param(inst, 'vector', pname, value)
        for flag in ra.USAGE_FLAGS:
            ml.set_material_usage_override(inst, getattr(u.MaterialUsage, flag), True, True)
        ml.update_material_instance(inst)
        if not self.assets.save_loaded_asset(inst, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        row = self.instance_values(inst, cfg)
        self.check_instance(row, 'Ashlar', cfg)
        row['vectors'] = self.instance_vectors(inst, cfg)
        return inst, {'asset': path, 'master': ra.asset_path(master), 'replaces': cfg['replaces'], 'readback': row,
                      'statistics': self.material_statistics(inst), 'uassetSha256': ra.sha(ra.disk(path))}

    def instance_vectors(self, inst, cfg):
        ml = self.ml
        out = {}
        for pname, want in cfg['vectors'].items():
            v = ml.get_material_instance_vector_parameter_value(inst, pname)
            got = [float(v.r), float(v.g), float(v.b), float(v.a)]
            if not ra.close(got, [float(x) for x in want]):
                raise RuntimeError('%s vector %s read back %s, want %s' % (ra.asset_path(inst), pname, got, want))
            out[pname] = got
        return out

    # ------------------------------------------------------------------------------------------ modes
    def do_layouts_build(self):
        u = self.u
        spec = self.scope_to_priority()
        r = self.report
        self.guard_project()
        existing = [p for p in self.new_asset_paths() if self.assets.does_asset_exist(p)]
        if existing:
            raise RuntimeError('refusing: built asset paths already exist: %s' % existing[:5])
        r['sourceProof'] = self.source_proof()
        r['reusedAssets'] = self.reused()
        r['buildCheckpoint'] = self.checkpoint_namespace('LayoutsBuild')
        r['protectedBefore'] = self.protected()
        ash = spec['variants']['Ashlar']
        r['parityBefore'] = {'Ashlar': self.parity_row(ash['replaces'])}
        self.stage('checked')
        textures, r['textures'] = {}, {}
        for asset, cfg in self.src()['imports'].items():
            textures[asset], r['textures'][asset] = self.import_one(asset, cfg)
        self.stage('imported', count=len(textures))
        arrays, r['arrays'] = {}, {}
        for kind, cfg in self.src()['arrays'].items():
            arrays[kind], r['arrays'][kind] = self.build_array(kind, cfg, textures)
            self.stage('array_saved_' + kind)
        master, r['master'] = self.build_layouts_master(arrays)
        self.stage('master_saved')
        _, r['instance'] = self.build_layouts_instance(master)
        self.stage('instance_saved')
        dirty = self.dirty_content_names()
        if dirty:
            raise RuntimeError('Packages still dirty after saves: %s' % dirty)
        r['parityAfter'] = {'Ashlar': self.parity_row(ash['replaces'])}
        if r['parityAfter'] != r['parityBefore']:
            raise RuntimeError('The replaced material changed during the build')
        inst = u.load_asset(ash['newInstance'])
        row = self.instance_values(inst, ash)
        self.check_instance(row, 'Ashlar', ash)
        pointers = {'self': ash['newInstance'], 'parent': row['parent']}
        pointers.update({'texture:' + k: v for k, v in row['textures'].items()})
        r['diskResolved'] = {'Ashlar': self.resolve_on_disk(ash['newInstance'], pointers)}
        ns = ROOT / 'Content' / spec['namespace'][6:]
        moved = sorted(rel for rel, digest in r['buildCheckpoint']['files'].items() if ra.sha(ns / rel) != digest)
        r['preexistingNamespaceAssetsChanged'] = moved
        if moved:
            raise RuntimeError('The build rewrote pre-existing assets: %s' % moved[:5])
        r['newAssetHashes'] = {p: ra.sha(ra.disk(p)) for p in self.new_asset_paths()}
        r['reusedAssets'] = self.reused()
        r['shaderCost'] = {'textureFetchesPerPixel': {'M_PBR_Tiled': 9, 'layouts': r['master']['textureFetchesPerPixel']},
                           'arraySlices': 15, 'note': 'Texture2DArrays are fully resident (NeverStream after creation)'}
        r['revertCommand'] = '-ARLayoutsRevert="%s"' % self.receipt_path
        r['status'] = 'BUILT_SAVED_READBACK_APPLY_PENDING'
        return r

    def do_layouts_verify(self, receipt_path):
        u = self.u
        spec = self.scope_to_priority()
        r = self.report
        prior = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
        r['buildReceipt'] = {'path': str(receipt_path), 'sha256': ra.sha(receipt_path), 'status': prior.get('status')}
        r['hashes'] = {p: {'receipt': d, 'now': ra.sha(ra.disk(p)) if ra.disk(p).exists() else None}
                       for p, d in prior['newAssetHashes'].items()}
        problems = [p for p, v in r['hashes'].items() if v['receipt'] != v['now']]
        r['arrays'] = {}
        for kind, cfg in self.src()['arrays'].items():
            row = self.array_row(u.load_asset(cfg['asset']))
            r['arrays'][kind] = row
            if row['sourceTextures'] != cfg['slices'] or row.get('mip_gen_settings') == 'TMGS_NO_MIPMAPS' \
                    or row.get('address_x') != 'TA_WRAP' or row.get('address_y') != 'TA_WRAP':
                problems.append('%s array readback %s' % (kind, row))
        r['master'] = self.layouts_master_readback(u.load_asset(spec['masters']['TriplanarLayouts']['asset']))
        ash = spec['variants']['Ashlar']
        inst = u.load_asset(ash['newInstance'])
        row = self.instance_values(inst, ash)
        self.check_instance(row, 'Ashlar', ash)
        row['vectors'] = self.instance_vectors(inst, ash)
        r['instance'] = row
        trim = spec['variants']['Trim']
        trow = self.instance_values(u.load_asset(trim['newInstance']), trim)
        self.check_instance(trow, 'Trim', trim)
        r['trimReused'] = trow
        r['reusedAssets'] = self.reused()
        r['problems'] = problems
        r['status'] = 'FRESH_PROCESS_VERIFIED' if not problems else 'FRESH_PROCESS_MISMATCH'
        return r


def _revert_order(p):
    """Referencers first: instance, master, arrays, then the slice textures the arrays were stacked from."""
    return 0 if '/MI_' in p else 1 if '/M_' in p else 2 if '/T2DA_' in p else 3


def _do_layouts_revert(self, receipt_path):
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
    for p in sorted(ours, key=lambda x: (_revert_order(x), x)):
        if self.assets.does_asset_exist(p):
            if not self.assets.delete_asset(p):
                raise RuntimeError('delete_asset failed for ' + p)
            deleted.append(p)
    r['deleted'] = deleted
    left = [p for p in ours if ra.disk(p).exists()]
    if left:
        raise RuntimeError('still on disk after delete: %s' % left[:5])
    cp = prior.get('buildCheckpoint', {})
    ns = ROOT / 'Content' / spec['namespace'][6:]
    r['namespaceMatchesCheckpoint'] = all(ra.sha(ns / rel) == d for rel, d in cp.get('files', {}).items())
    if not r['namespaceMatchesCheckpoint']:
        raise RuntimeError('namespace differs from the build checkpoint %s' % cp.get('path'))
    r['reusedAssets'] = self.reused()              # the Trim's variants assets must be untouched by a revert
    r['status'] = 'REVERTED_ASSETS_DELETED'
    return r


LayoutsNative.do_layouts_revert = _do_layouts_revert


def _native_main():
    import unreal as ue
    cmd = ue.SystemLibrary.get_command_line()
    build_m = re.search(r'-ARLayoutsBuild(?=\s|$)', cmd)
    verify_m = re.search(r'-ARLayoutsVerify=(?:"([^"]+)"|([^\s]+))', cmd)
    revert_m = re.search(r'-ARLayoutsRevert=(?:"([^"]+)"|([^\s]+))', cmd)
    hits = [m for m in (build_m, verify_m, revert_m) if m]
    if len(hits) != 1:
        # A commandlet's flags are not in sys.argv; no mode must fail loudly, not exit 0.
        raise RuntimeError('Pass exactly one of -ARLayoutsBuild, -ARLayoutsVerify=<receipt>, -ARLayoutsRevert=<receipt>; '
                           'command line was: %s' % cmd)
    spec = ra.resolve_spec(ra.load_spec(), MODE)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    mode = 'layoutsbuild' if build_m else ('layoutsverify' if verify_m else 'layoutsrevert')
    native = LayoutsNative(ue, spec, mode, stamp)
    protected_before = native.protected()
    try:
        if build_m:
            native.do_layouts_build()
        else:
            m = verify_m or revert_m
            arg = Path(m.group(1) or m.group(2))
            if not arg.exists():
                raise RuntimeError('Receipt not found: %s' % arg)
            if verify_m:
                native.do_layouts_verify(arg)
            else:
                native.do_layouts_revert(arg)           # deletes exactly the receipt's newAssetHashes
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
        ue.log('ARLAYOUTS_%s %s status=%s' % (mode.upper(), native.receipt_path, native.report['status']))


if __name__ == '__main__':
    try:
        import unreal  # noqa: F401
    except ImportError:
        spec = ra.resolve_spec(ra.load_spec(), MODE)
        print(json.dumps({'masters': sorted(spec['masters']),
                          'variants': {n: {'master': c['master'], 'newInstance': c['newInstance']} for n, c in spec['variants'].items()},
                          'imports': len(spec['samplingAssets'][MODE]['source']['imports'])}, indent=1))
    else:
        _native_main()

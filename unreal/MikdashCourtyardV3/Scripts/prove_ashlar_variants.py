"""Prove the anti-repeat V5 tile variants before anything is imported. Offline, no engine.

1. GENERATOR REGRESSION. Scripts/create_herodian_ashlar_v5.py, refactored to take --surface-seed, must
   still produce V5 byte for byte when no seed is given: the six maps of a default regeneration are hashed
   against the V5 manifest (and so against the sourceSha256 the live T_HerodianV5b_* imports recorded).
2. JOINTS IDENTICAL. Every variant's JointMask (joint + arris pixels) and StoneKey must equal V5's pixel
   for pixel. Regions (margin / bevel / boss) are reported: they are allowed to differ, because the
   variant is picked per STONE and a stone never shows two variants.
3. V5's HARD-WON FIXES KEPT. Every generator parameter (the 1.9 cm boss bevel, the grain, the palette)
   equals V5's; the only differences are the surface seed and the tag. Measured B/R, bevel share and
   boss-edge normal are reported against V5.
Writes SourceAssets/material-review/HerodianAshlarV5Variants/joint-proof.json with status
JOINTS_IDENTICAL only if 1 and 2 hold for every variant; release_antirepeat_variants.py refuses otherwise.

  python Scripts/prove_ashlar_variants.py --regression <dir of the default regeneration> --tags vB,vC
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / 'SourceAssets' / 'material-review' / 'HerodianAshlarV5'
VAR = ROOT / 'SourceAssets' / 'material-review' / 'HerodianAshlarV5Variants'
LAYOUTS = ('Ashlar', 'Trim')
MAPS = ('Albedo', 'Normal', 'ARM', 'Roughness', 'AO', 'Height')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT)).replace('\\', '/')


def img(p):
    return np.asarray(Image.open(p).convert('RGB'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--regression', required=True, type=Path)
    ap.add_argument('--tags', required=True)
    a = ap.parse_args()
    tags = a.tags.split(',')
    v5m = json.loads((V5 / 'manifest.json').read_text(encoding='utf-8-sig'))
    regm = json.loads((a.regression / 'manifest.json').read_text(encoding='utf-8-sig'))
    varm = {t: json.loads((VAR / t / 'manifest.json').read_text(encoding='utf-8-sig')) for t in tags}
    out = {'utc': datetime.now(timezone.utc).isoformat(), 'script': 'Scripts/prove_ashlar_variants.py',
           'scriptSha256': sha(__file__), 'generatorSha256': sha(ROOT / 'Scripts' / 'create_herodian_ashlar_v5.py'),
           'regression': {}, 'layouts': {}, 'files': {}, 'problems': []}
    for name in LAYOUTS:
        # 1. regression
        reg = {}
        for kind in MAPS:
            want = v5m['variants'][name]['files'][kind]['sha256']
            got = sha(a.regression / ('T_HerodianV5_%s_%s.png' % (name, kind)))
            reg[kind] = {'v5': want, 'regenerated': got, 'equal': want == got}
            if want != got:
                out['problems'].append('regression: %s %s differs from V5' % (name, kind))
        out['regression'][name] = reg
        # 2. joints
        jb = img(a.regression / ('T_HerodianV5_%s_JointMask.png' % name))[..., 0]
        kb = img(a.regression / ('T_HerodianV5_%s_StoneKey.png' % name))
        rb = img(a.regression / ('T_HerodianV5_%s_Regions.png' % name))[..., 0]
        lay = {'jointPixels': int((jb == 255).sum()), 'arrisPixels': int((jb == 128).sum()),
               'stoneKeyValuesR': [int(kb[..., 0].min()), int(kb[..., 0].max())],
               'stones': len(np.unique(kb[..., 1])), 'variants': {}}
        base_p = v5m['variants'][name]['parameters']
        base_s = v5m['variants'][name]['statistics']
        for tag in tags:
            rec = varm[tag]['variants'][name + tag]
            j = img(VAR / tag / ('T_HerodianV5%s_%s_JointMask.png' % (tag, name)))[..., 0]
            k = img(VAR / tag / ('T_HerodianV5%s_%s_StoneKey.png' % (tag, name)))
            r = img(VAR / tag / ('T_HerodianV5%s_%s_Regions.png' % (tag, name)))[..., 0]
            row = {'surfaceSeed': rec['surfaceSeed'],
                   'jointMaskDiffPixels': int((j != jb).sum()),
                   'stoneKeyDiffPixels': int((k != kb).any(axis=2).sum()),
                   'regionsDiffPixels': int((r != rb).sum()),
                   'regionsDiffOutsideJointAndArris': int(((r != rb) & (jb == 0)).sum()),
                   'regionsDiffOnJointOrArris': int(((r != rb) & (jb != 0)).sum())}
            if row['jointMaskDiffPixels'] or row['stoneKeyDiffPixels'] or row['regionsDiffOnJointOrArris']:
                out['problems'].append('joints: %s %s differs from V5 %s' % (name, tag, row))
            # 3. fixes kept: parameters identical, measured numbers alongside V5's
            pdiff = {kk: (base_p.get(kk), rec['parameters'].get(kk)) for kk in set(base_p) | set(rec['parameters'])
                     if base_p.get(kk) != rec['parameters'].get(kk)}
            row['parameterDiffVsV5'] = pdiff
            if pdiff:
                out['problems'].append('parameters: %s %s differ from V5: %s' % (name, tag, sorted(pdiff)))
            s = rec['statistics']
            row['measuredVsV5'] = {
                'BoverR': [base_s['albedoChroma']['BoverR_mean'], s['albedoChroma']['BoverR_mean']],
                'GoverR': [base_s['albedoChroma']['GoverR_mean'], s['albedoChroma']['GoverR_mean']],
                'albedoMeanSRGB': [[base_s['albedoSRGB'][c]['mean'] for c in 'RGB'], [s['albedoSRGB'][c]['mean'] for c in 'RGB']],
                'albedoStdPerChannelMean': [base_s['albedoStdPerChannelMean'], s['albedoStdPerChannelMean']],
                'bossEdgeNormalP50': [base_s['normalBossEdgeOnly']['xyDeviation']['p50'], s['normalBossEdgeOnly']['xyDeviation']['p50']],
                'bossEdgeBevelCm': [v5m['variants'][name]['schedule']['bossEdgeBevelCm'], rec['schedule']['bossEdgeBevelCm']],
                'bevelPixelFraction': [v5m['variants'][name]['schedule']['pixelFraction']['bossBevel'],
                                       rec['schedule']['pixelFraction']['bossBevel']],
                'roughnessP50': [base_s['roughness']['p50'], s['roughness']['p50']]}
            row['stoneFamilies'] = [st['family'] for st in rec.get('stones', [])]
            lay['variants'][tag] = row
            for kind in ('Albedo', 'Normal', 'ARM', 'StoneKey'):
                p = VAR / tag / ('T_HerodianV5%s_%s_%s.png' % (tag, name, kind))
                out['files'][rel(p)] = sha(p)
        lay['v5StoneFamilies'] = [st['family'] for st in regm['variants'][name].get('stones', [])]
        out['layouts'][name] = lay
    out['status'] = 'JOINTS_IDENTICAL' if not out['problems'] else 'FAILED'
    out['summary'] = {n: {t: {'jointMaskDiffPixels': out['layouts'][n]['variants'][t]['jointMaskDiffPixels'],
                              'stoneKeyDiffPixels': out['layouts'][n]['variants'][t]['stoneKeyDiffPixels']}
                          for t in tags} for n in LAYOUTS}
    (VAR / 'joint-proof.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'status': out['status'], 'problems': out['problems'], 'summary': out['summary']}, indent=1))


if __name__ == '__main__':
    main()

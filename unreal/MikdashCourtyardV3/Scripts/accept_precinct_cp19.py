"""cp19 acceptance numbers from packaged-build frames (run after capture_frame_precinct_macro.ps1 -Label cp19).

  1. measure_precinct_face_profile.py on cp16before / cp17b / cp19 (rectified vertical profile per whole face)
  2. the cp17 screen-box metrics (ab3 definitions, kept for continuity) and the 60-70 m tile-period
     autocorrelation on P2/P3
  3. no-regression: mean |diff| of the 4 m jamb (02) and plaza stone at walking range (07) against cp17, with
     the cp17 -> cp17b 07 pair (no change to anything visible there) as the frame-to-frame noise floor
  4. side-by-side crops for the eye
  python Scripts/accept_precinct_cp19.py
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path('C:/Mikdash/Working-5.8/MikdashCourtyardV3')
V = ROOT / 'SourceAssets/visual-review'
OUT = ROOT / 'SourceAssets/enclosure-review/PrecinctMacroV1'
RUNS = (('before', 'cp16before-'), ('V2tone', 'cp17b-'), ('cp19', 'cp19-'), ('cp19b', 'cp19b-'))


def L(p):
    a = np.asarray(Image.open(p).convert('RGB'), dtype=np.float32) / 255
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def acorr(l, box, maxlag=400):
    x0, y0, x1, y1 = box
    p = l[y0:y1, x0:x1]
    p = p - p.mean(axis=1, keepdims=True)
    den = float((p * p).sum())
    return np.array([float((p[:, :-k] * p[:, k:]).sum()) / den for k in range(1, maxlag)])


def main():
    res = {'script': 'Scripts/accept_precinct_cp19.py'}
    prof = subprocess.run([sys.executable, str(ROOT / 'Scripts/measure_precinct_face_profile.py'),
                           'cp16before', 'cp17b', 'cp19', 'cp19b', '--overlay'], capture_output=True, text=True)
    res['faceProfileExit'] = prof.returncode
    pj = OUT / 'face-profile-cp16before-cp17b-cp19-cp19b.json'
    if pj.exists():
        d = json.loads(pj.read_text(encoding='utf-8'))
        res['faceProfile'] = {run: {view: {face: {k: vals.get(k) for k in ('metresPerPx', 'rawStd', 'hpStd', 'bandPowerShare', 'error')}
                                           for face, vals in faces.items()}
                                    for view, faces in views.items() if not view.endswith('_overlay')}
                              for run, views in d['runs'].items()}
    regions = {'southFace': (1760, 1420, 2100, 1500), 'southFace2': (2000, 1330, 2200, 1460),
               'southFaceWide': (1800, 1300, 2300, 1520)}
    res['screenBoxes_cp17definition'] = {}
    for tag, pre in RUNS:
        f = V / (pre + 'P1-precinct-plaza-aerial-SW-corner.png')
        if not f.exists():
            continue
        l = L(f)
        for name, (x0, y0, x1, y1) in regions.items():
            p = l[y0:y1, x0:x1]
            res['screenBoxes_cp17definition'].setdefault(name, {})[tag] = {
                'std': round(float(p.std()), 4), 'rowProfileStd': round(float(p.mean(axis=1).std()), 4),
                'meanAbsDy': round(float(np.abs(np.diff(p, axis=0)).mean()), 4)}
    for view, fn, box in (('P3', 'P3-retaining-east-face-60m', (200, 100, 3700, 1800)),
                          ('P2', 'P2-retaining-south-face-70m', (1500, 900, 3800, 1500))):
        for tag, pre in RUNS:
            f = V / (pre + fn + '.png')
            if not f.exists():
                continue
            l = L(f)
            ac = acorr(l, box)
            k = int(np.argmax(ac[40:])) + 41
            res.setdefault('tilePeriodAutocorr', {}).setdefault(view, {})[tag] = {
                'peakLagPx': k, 'peakCorr': round(float(ac[k - 1]), 4),
                'corrAtLag101': round(float(ac[100]), 4), 'std': round(float(l[box[1]:box[3], box[0]:box[2]].std()), 4)}
    # no-regression
    def mad(a, b):
        A, B = L(V / a), L(V / b)
        return round(float(np.abs(A - B).mean()), 5)
    nr = {}
    if (V / 'cp19-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png').exists():
        nr['02_jamb_cp17_vs_cp19'] = mad('cp17-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png',
                                         'cp19-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png')
    if (V / 'cp19-07-north-gate-approach-plaza-stone-near.png').exists():
        nr['07_plaza_cp17b_vs_cp19'] = mad('cp17b-07-north-gate-approach-plaza-stone-near.png',
                                           'cp19-07-north-gate-approach-plaza-stone-near.png')
    for lab in ('cp19b',):
        j = V / (lab + '-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png')
        s = V / (lab + '-07-north-gate-approach-plaza-stone-near.png')
        if j.exists():
            nr['02_jamb_cp17_vs_' + lab] = mad('cp17-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png', j.name)
        if s.exists():
            nr['07_plaza_cp17b_vs_' + lab] = mad('cp17b-07-north-gate-approach-plaza-stone-near.png', s.name)
    nr['07_noiseFloor_cp17_vs_cp17b'] = mad('cp17-07-north-gate-approach-plaza-stone-near.png',
                                            'cp17b-07-north-gate-approach-plaza-stone-near.png')
    res['noRegression'] = nr
    # crops
    crops = {'P1': ((1700, 1000, 3100, 1560), 'P1-precinct-plaza-aerial-SW-corner'),
             'P2': ((0, 0, 3840, 2160), 'P2-retaining-south-face-70m'),
             'P3': ((0, 0, 3840, 2160), 'P3-retaining-east-face-60m')}
    for view, (box, fn) in crops.items():
        ims = [Image.open(V / (pre + fn + '.png')).crop(box) for _t, pre in RUNS if (V / (pre + fn + '.png')).exists()]
        if not ims:
            continue
        if view != 'P1':
            ims = [im.resize((im.width // 2, im.height // 2)) for im in ims]
        w, h = ims[0].size
        sheet = Image.new('RGB', (w, h * len(ims) + 12 * (len(ims) - 1)), (255, 255, 255))
        for i, im in enumerate(ims):
            sheet.paste(im, (0, i * (h + 12)))
        dst = OUT / ('cp19-compare-%s.png' % view)
        sheet.save(dst)
        res.setdefault('compareSheets', {})[view] = str(dst)
    txt = json.dumps(res, indent=1)
    (OUT / 'accept-cp19.json').write_text(txt, encoding='utf-8')
    print(txt)


if __name__ == '__main__':
    main()

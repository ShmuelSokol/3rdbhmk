"""Rectified vertical brightness profile of the precinct retaining faces in a packaged-build frame.

WHY (11 Sep 2026, cp19 pass). The cp17 metric (frame-ab-metrics-*.json) averaged screen-space
boxes. That under-reads coursing for two reasons: on the aerial camera the south face recedes
obliquely, so world-horizontal course lines are SLANTED in the image and a screen-row average smears
them; and its 'eastFace' box (2980,1150)-(3100,1250) turns out to sit on the terrain and houses to
the right of the precinct's SE corner, not on any face - which is why it never changed in any build.

This projects world points ON THE FACE PLANE through the BugItGo camera (UE: X fwd, Y right, Z up,
horizontal FOV 90 = MikdashSaveGame FieldOfViewDegrees default, 16:9) and samples the frame there,
so each profile row is one world-Z level averaged along the face. Reported per face:
  rawStd        std of the profile (what cp17 called rowProfileStd, done right)
  hpStd         std after removing a 15 m moving average - the part that is courses/bands/ledges,
                not sky/fog/lighting gradients
  bandPower     spectral power at the periods that geometry and texture put there: 1.0 m (course),
                2.4 m (5-amah band), 3.0 m (close tile), 12.0 m (batter ledge every 5 bands)
  pxPerMetre    vertical screen pixels per metre of face at the face centre

  python Scripts/measure_precinct_face_profile.py cp16before cp17b [cp19 ...] [--overlay]
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path('C:/Mikdash/Working-5.8/MikdashCourtyardV3')
VR = ROOT / 'SourceAssets/visual-review'
OUT = ROOT / 'SourceAssets/enclosure-review/PrecinctMacroV1'
PREC = json.loads((ROOT / 'SourceAssets/enclosure-review/precinct-Candidate48.json').read_text(encoding='utf-8'))
F = PREC['square']['outerFacesCm']
XW, XE, YN, YS = F['xWest'], F['xEast'], F['yNorth'], F['ySouth']
HFOV = 90.0

VIEWS = {
    'P1': ('P1-precinct-plaza-aerial-SW-corner', (-95000, 175000, 30000, -9, -45, 0)),
    'P2': ('P2-retaining-south-face-70m', (10000, 118900, -1500, -18, -90, 0)),
    'P3': ('P3-retaining-east-face-60m', (117900, 60000, -1500, -15, 180, 0)),
}
# Face strips: (name, plane, fixed coordinate, along-range cm, z-range cm, outward normal)
# South face strips avoid the S1/S2 approach footprints (release_precinct_approaches receipt
# buildingsUnderApproach boxes: S1 X -29280..18624, S2 X 44352..66624). Z ranges stay inside the
# measured fill (deck 0 down to 15 m above the lowest ground of the strip) so nothing in front
# (terrain, roofs) is sampled.
FACES = {
    'P1': [
        ('west_face_full', 'x', XW, (YS - 60000, YS - 1500), None, (-1, 0)),
        ('south_S1toS2', 'y', YS, (19800, 43200), None, (0, 1)),
        ('south_eastOfS2', 'y', YS, (67800, 100000), None, (0, 1)),
    ],
    'P2': [('south_P2_view', 'y', YS, (4600, 15400), None, (0, 1))],
    'P3': [('east_P3_view', 'x', XE, (55000, 65000), None, (1, 0))],
}
BANDS_M = {'course1m': 1.0, 'band2p4m': 2.4, 'tile3m': 3.0, 'batter12m': 12.0}


def ground_low_along(plane, fixed, a0, a1):
    """Lowest ground under the strip, from the frozen 601-station profile the plaza was built on."""
    gp = PREC['groundProfile']
    lows = gp.get('lowZcm')
    if lows is None:
        return None
    side = {('y', YN): 0, ('x', XE): 1, ('y', YS): 2, ('x', XW): 3}.get((plane, fixed))
    if side is None or not isinstance(lows[0], list):
        return None
    return min(lows[side])


def cam_basis(p, y):
    p, y = math.radians(p), math.radians(y)
    f = np.array([math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)])
    r = np.array([-math.sin(y), math.cos(y), 0.0])
    u = np.array([-math.sin(p) * math.cos(y), -math.sin(p) * math.sin(y), math.cos(p)])
    return f, r, u


def project(pts, cam, W, H):
    x, y, z, pitch, yaw, _roll = cam
    f, r, u = cam_basis(pitch, yaw)
    d = pts - np.array([x, y, z], dtype=np.float64)
    df = d @ f
    t = math.tan(math.radians(HFOV) / 2.0)
    px = W / 2.0 * (1.0 + (d @ r) / df / t)
    py = H / 2.0 - W / 2.0 * (d @ u) / df / t
    return px, py, df


def bilinear(img, px, py):
    H, W = img.shape
    x0 = np.clip(np.floor(px).astype(int), 0, W - 2)
    y0 = np.clip(np.floor(py).astype(int), 0, H - 2)
    fx = np.clip(px - x0, 0, 1)
    fy = np.clip(py - y0, 0, 1)
    a = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    b = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy


def lum(path):
    a = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def strip_points(plane, fixed, along, zs):
    A, Z = np.meshgrid(along, zs)
    if plane == 'y':
        P = np.stack([A, np.full_like(A, fixed), Z], axis=-1)
    else:
        P = np.stack([np.full_like(A, fixed), A, Z], axis=-1)
    return P.reshape(-1, 3), A.shape


def measure(view, label, L, W, H, zrange_override=None):
    cam = VIEWS[view][1]
    out = {}
    for name, plane, fixed, (a0, a1), zr, normal in FACES[view]:
        # visible z-range: deck edge down; bottom from the frame itself (stop where the
        # projected strip leaves the image) and from a conservative fill floor
        z_top = -150.0
        z_bot = -9000.0 if view != 'P1' else -8500.0
        if zr:
            z_top, z_bot = zr
        dz = 12.5 if view == 'P1' else 5.0
        zs = np.arange(z_top, z_bot, -dz)
        along = np.linspace(a0, a1, 400 if view == 'P1' else 800)
        pts, shape = strip_points(plane, fixed, along, zs)
        px, py, df = project(pts, cam, W, H)
        inside = (df > 0) & (px >= 1) & (px < W - 2) & (py >= 1) & (py < H - 2)
        vals = np.where(inside, bilinear(L, np.clip(px, 0, W - 2), np.clip(py, 0, H - 2)), np.nan).reshape(shape)
        cov = np.isfinite(vals).mean(axis=1)
        keep = cov > 0.8
        prof = np.nanmean(vals[keep], axis=1)
        z_kept = zs[keep]
        if len(prof) < 40:
            out[name] = {'error': 'strip not in frame', 'rows': int(len(prof))}
            continue
        # vertical px per metre at strip centre
        mid = np.array([[(a0 + a1) / 2 if plane == 'y' else fixed, fixed if plane == 'y' else (a0 + a1) / 2, z]
                        for z in (z_kept[len(z_kept) // 2], z_kept[len(z_kept) // 2] - 100.0)])
        _, pyy, _ = project(mid, cam, W, H)
        ppm = float(abs(pyy[1] - pyy[0]))
        win = max(3, int(round(1500.0 / dz)))
        k = np.ones(win) / win
        pad = np.pad(prof, (win // 2, win - 1 - win // 2), mode='edge')
        trend = np.convolve(pad, k, mode='valid')
        hp = prof - trend
        spec = np.abs(np.fft.rfft(hp * np.hanning(len(hp)))) ** 2
        freqs = np.fft.rfftfreq(len(hp), d=dz / 100.0)      # cycles per metre
        total = float(spec[1:].sum()) + 1e-12
        bp = {}
        for bn, per in BANDS_M.items():
            f0 = 1.0 / per
            sel = (freqs > f0 * 0.9) & (freqs < f0 * 1.1)
            bp[bn] = round(float(spec[sel].sum()) / total, 4) if sel.any() else None
        out[name] = {'rows': int(len(prof)), 'zTopCm': float(z_kept[0]), 'zBottomCm': float(z_kept[-1]),
                     'pxPerMetre': round(ppm, 2), 'metresPerPx': round(1.0 / ppm, 3) if ppm > 0 else None,
                     'mean': round(float(prof.mean()), 4), 'rawStd': round(float(prof.std()), 4),
                     'hpStd': round(float(hp.std()), 4), 'bandPowerShare': bp}
    return out


def overlay(view, label, W, H):
    path = VR / ('%s-%s.png' % (label, VIEWS[view][0]))
    im = Image.open(path).convert('RGB')
    dr = ImageDraw.Draw(im)
    cam = VIEWS[view][1]
    for name, plane, fixed, (a0, a1), zr, normal in FACES[view]:
        for z in (-150.0, -1200.0, -2400.0, -3600.0, -4800.0, -6000.0):
            along = np.linspace(a0, a1, 50)
            pts, _ = strip_points(plane, fixed, along, np.array([z]))
            px, py, df = project(pts, cam, W, H)
            ok = df > 0
            dr.line(list(zip(px[ok].tolist(), py[ok].tolist())), fill=(255, 0, 0) if z == -150.0 else (0, 255, 255), width=3)
    dst = Path(sys.argv[0]).resolve().parent.parent / 'SourceAssets/enclosure-review/PrecinctMacroV1' / ('overlay-%s-%s.png' % (label, view))
    im.save(dst)
    return str(dst)


def main():
    labels = [a for a in sys.argv[1:] if not a.startswith('--')]
    do_overlay = '--overlay' in sys.argv
    res = {'script': 'Scripts/measure_precinct_face_profile.py', 'hfovDeg': HFOV, 'faces': FACES, 'runs': {}}
    for label in labels:
        res['runs'][label] = {}
        for view in VIEWS:
            path = VR / ('%s-%s.png' % (label, VIEWS[view][0]))
            if not path.exists():
                continue
            L = lum(path)
            H, W = L.shape
            res['runs'][label][view] = measure(view, label, L, W, H)
            if do_overlay:
                res['runs'][label][view + '_overlay'] = overlay(view, label, W, H)
            del L
    txt = json.dumps(res, indent=1, default=str)
    print(txt)
    tag = '-'.join(labels)
    (OUT / ('face-profile-%s.json' % tag)).write_text(txt, encoding='utf-8')


if __name__ == '__main__':
    main()

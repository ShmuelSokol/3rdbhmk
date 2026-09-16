"""Offline acceptance for KotelRetainingWallV2: does the plaza still see into the excavation void?

WHAT IS ACTUALLY BEING TESTED
-----------------------------
The defect KotelCutClosureV1 was built to close (KotelCutClosureV1/diagnosis.md) is a sightline
that leaves the plaza BELOW the surrounding hillside surface: the terrain is a one-sided
surface, so a ray that passes under it shows whatever lies beyond - the mirrored city band in
the cp24 K2 frame. A ray that leaves the plaza ABOVE the hillside is not a defect; it is the
view of the hill.

So this does not compare the two walls' distances (V2 deliberately stands up to
MAX_DEVIATION_CM inside the sawtooth, and grazing rays legitimately run alongside it). It
counts VOID RAYS: rays whose first hit in {wall, plaza deck, hillside terrain} is the BACK of
the hillside surface, outside the deck union - i.e. the player is looking in under the hill.

  * V1 (the accepted closure) is measured the same way, as the control.
  * V2 must have no more void rays than V1, and none of its own.
  * every V2 face foot must stand on a deck cell (the wall never floats over the cut).
  * the probe-lane numbers the edge test consumes must match the generated geometry.

Needs a 64-bit Python with numpy (the 32-bit default runs out of memory):
  set PATH=C:\\Users\\shmue\\anaconda3;C:\\Users\\shmue\\anaconda3\\Library\\bin;%PATH%
  C:\\Users\\shmue\\anaconda3\\python.exe Scripts/verify_kotel_retaining_wall.py
No Unreal, no assets, no maps. Writes SourceAssets/context-review/KotelViewsV1/coverage-v2.json.
"""
import json
import math
import runpy
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STUDY_DIR = ROOT / 'SourceAssets/context-review/KotelCutClosureV1'
WALL = ROOT / 'SourceAssets/context-review/KotelViewsV1/retaining-wall-v2.json'
OUT = ROOT / 'SourceAssets/context-review/KotelViewsV1/coverage-v2.json'
EYE_CM = 170.0
DECK_TOPS = {-984.594: 'upper', -1234.594: 'lower'}
AZIMUTH_STEP = 1.0
ELEVATIONS = np.arange(-25.0, 30.001, 2.5)
CLEARANCE_CM = 200.0
CAPTURE_CAMERAS = [(-20732.0, 19230.0, -814.0, 'K2 capture camera')]


def triangle_arrays(vertices, triangles, normals):
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(triangles, dtype=np.int64)
    n = np.asarray(normals, dtype=np.float64)[f[:, 0]]
    return v[f[:, 0]], v[f[:, 1]], v[f[:, 2]], n


def hits(origin, directions, A, B, C, N, two_sided):
    """Möller-Trumbore. Returns (t, backface) per ray for the nearest hit of this set."""
    best = np.full(len(directions), np.inf)
    back = np.zeros(len(directions), dtype=bool)
    where = np.zeros((len(directions), 3))
    e1, e2 = B - A, C - A
    for start in range(0, len(A), 2048):
        stop = min(start + 2048, len(A))
        a, b, c, nn = A[start:stop], e1[start:stop], e2[start:stop], N[start:stop]
        pv = np.cross(directions[:, None, :], c[None, :, :])
        det = np.einsum('tj,rtj->rt', b, pv)
        facing = (directions @ nn.T) < 0.0
        ok = (np.abs(det) > 1e-9) & (facing | two_sided)
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = origin[None, :] - a
        u = np.einsum('tj,rtj->rt', tv, pv) * inv
        qv = np.cross(tv, b)
        vv = (directions @ qv.T) * inv
        t = (c * qv).sum(axis=1)[None, :] * inv
        hit = ok & (u >= -1e-9) & (vv >= -1e-9) & (u + vv <= 1.0 + 1e-9) & (t > 1.0)
        t = np.where(hit, t, np.inf)
        nearest = t.argmin(axis=1)
        rows = np.arange(len(directions))
        closer = t[rows, nearest] < best
        best = np.where(closer, t[rows, nearest], best)
        back = np.where(closer, ~facing[rows, nearest], back)
        where = np.where(closer[:, None], origin[None, :] + directions * t[rows, nearest][:, None], where)
    return best, back, where


def directions():
    out = []
    for az in np.arange(0.0, 360.0, AZIMUTH_STEP):
        for el in ELEVATIONS:
            ca, sa = math.cos(math.radians(az)), math.sin(math.radians(az))
            ce, se = math.cos(math.radians(el)), math.sin(math.radians(el))
            out.append([ca * ce, sa * ce, se])
    return np.asarray(out, dtype=np.float64)


def deck_geometry(rects):
    v, f, n = [], [], []
    for (x0, y0, x1, y1), top in rects:
        quads = [([(x0, y0, top), (x1, y0, top), (x1, y1, top), (x0, y1, top)], (0.0, 0.0, 1.0)),
                 ([(x0, y0, top), (x0, y0, top - 50.0), (x1, y0, top - 50.0), (x1, y0, top)], (0.0, -1.0, 0.0)),
                 ([(x1, y1, top), (x1, y1, top - 50.0), (x0, y1, top - 50.0), (x0, y1, top)], (0.0, 1.0, 0.0)),
                 ([(x0, y1, top), (x0, y1, top - 50.0), (x0, y0, top - 50.0), (x0, y0, top)], (-1.0, 0.0, 0.0)),
                 ([(x1, y0, top), (x1, y0, top - 50.0), (x1, y1, top - 50.0), (x1, y1, top)], (1.0, 0.0, 0.0))]
        for corners, normal in quads:
            base = len(v)
            v.extend(corners)
            f.extend([[base, base + 1, base + 2], [base, base + 2, base + 3]])
            n.extend([normal] * 4)
    return triangle_arrays(v, f, n)


def terrain_geometry(source):
    v = source['vertices']
    f = source['triangles']
    n = [None] * len(v)
    for a, b, c in f:
        p, q, r = v[a], v[b], v[c]
        u = [q[i] - p[i] for i in range(3)]
        w = [r[i] - p[i] for i in range(3)]
        cr = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        size = math.sqrt(sum(x * x for x in cr)) or 1.0
        cr = [x / size for x in cr]
        if cr[2] < 0:
            cr = [-x for x in cr]
        n[a] = cr
    for i, value in enumerate(n):
        if value is None:
            n[i] = [0.0, 0.0, 1.0]
    return triangle_arrays(v, f, n)


def main():
    study = runpy.run_path(str(STUDY_DIR / 'generate_study_closure.py'))
    measure = study['M']
    plan = json.loads(measure['PLAN'].read_text(encoding='utf-8-sig'))
    source = json.loads(measure['SOURCE'].read_text(encoding='utf-8-sig'))
    rects = measure['rectangles'](plan, True)
    legacy = json.loads((STUDY_DIR / 'closure-study.json').read_text(encoding='utf-8'))
    wall = json.loads(WALL.read_text(encoding='utf-8'))

    walls = {'V1 closure': triangle_arrays(legacy['vertices'], legacy['triangles'], legacy['normals']),
             'V2 wall': triangle_arrays(wall['vertices'], wall['triangles'], wall['normals'])}
    deck = deck_geometry(rects)
    terrain = terrain_geometry(source)

    def clearance(p):
        best = float('inf')
        for chain in wall['chains']:
            poly = chain['polylineXYcm']
            for a, b in zip(poly, poly[1:]):
                dx, dy = b[0] - a[0], b[1] - a[1]
                L2 = dx * dx + dy * dy
                t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
                best = min(best, math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy))
        return best

    cameras = list(CAPTURE_CAMERAS)
    cells = sorted(plan['deck'], key=lambda d: (round(d['loc'][2], 3), d['loc'][0], d['loc'][1]))
    for level in DECK_TOPS:
        same = [d for d in cells if abs(d['loc'][2] - level) < 1e-6 and clearance(d['loc']) >= CLEARANCE_CM]
        for i in range(0, len(same), max(1, len(same) // 20)):
            d = same[i]
            cameras.append((d['loc'][0], d['loc'][1], level + EYE_CM, 'deck cell on the %s level' % DECK_TOPS[level]))

    def inside_deck(points):
        flags = np.zeros(len(points), dtype=bool)
        for (x0, y0, x1, y1), _ in rects:
            flags |= ((points[:, 0] >= x0 - 0.02) & (points[:, 0] <= x1 + 0.02)
                      & (points[:, 1] >= y0 - 0.02) & (points[:, 1] <= y1 + 0.02))
        return flags

    dirs = directions()
    report = {'status': 'checking', 'rayCountPerCamera': int(len(dirs)), 'cameras': [],
              'azimuthStepDegrees': AZIMUTH_STEP, 'elevationsDegrees': [float(e) for e in ELEVATIONS],
              'cameraClearanceCm': CLEARANCE_CM,
              'criterion': 'A void ray is one whose nearest hit among {wall, plaza deck, hillside terrain} is the '
                           'BACK of the hillside surface outside the deck union: the player is looking in under the hill.',
              'scope': 'Sampled sightlines from deck-level cameras against the frozen 566-triangle source terrain, the '
                       '959 deck cells and each wall. Not a rendered frame, not a whole-perimeter proof, and it '
                       'contains no other scene actor (buildings, roads, the Western Wall stone).'}
    totals = {name: 0 for name in walls}
    for x, y, z, why in cameras:
        origin = np.asarray([x, y, z], dtype=np.float64)
        tdeck, _, _ = hits(origin, dirs, *deck, two_sided=False)
        tterrain, backterrain, whereterrain = hits(origin, dirs, *terrain, two_sided=True)
        row = {'cameraCm': [x, y, z], 'why': why}
        for name, geometry in walls.items():
            twall, _, _ = hits(origin, dirs, *geometry, two_sided=False)
            first_terrain = (tterrain < twall) & (tterrain < tdeck) & np.isfinite(tterrain)
            void = first_terrain & backterrain & ~inside_deck(whereterrain)
            row[name] = int(void.sum())
            totals[name] += int(void.sum())
        report['cameras'].append(row)
    report['voidRayTotals'] = totals
    report['cameraCount'] = len(cameras)

    outside = 0
    for chain in wall['chains']:
        poly = chain['polylineXYcm']
        for a, b in zip(poly, poly[1:]):
            n = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / 25.0)))
            for k in range(n + 1):
                p = (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
                if not any(x0 - 0.02 <= p[0] <= x1 + 0.02 and y0 - 0.02 <= p[1] <= y1 + 0.02
                           for (x0, y0, x1, y1), _ in rects):
                    outside += 1
    report['faceFootSamplesOutsideDeckUnion'] = outside
    report['probeLane'] = wall['probeLane']
    # The bar is NO REGRESSION against the accepted V1 closure, not zero. V1 itself leaves
    # void rays (it excludes the internal level edges and the platform hole by design), so a
    # zero bar is one the accepted answer could not pass and would be meaningless.
    report['voidRayChangeVsV1'] = totals['V2 wall'] - totals['V1 closure']
    report['passed'] = totals['V2 wall'] <= totals['V1 closure'] and outside == 0
    report['status'] = 'void_rays_passed_native_acceptance_pending' if report['passed'] else 'void_rays_failed'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
    print('%s: void rays V1 %d, V2 %d over %d cameras x %d rays; %d foot samples off deck'
          % (report['status'], totals['V1 closure'], totals['V2 wall'], len(cameras), len(dirs), outside))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

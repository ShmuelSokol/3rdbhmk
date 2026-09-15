"""CityFacadeV1 step 1 - WHICH buildings does a visitor actually see up close?  (offline, read-only)

AUTHORED_OFFLINE_SOURCE: never imports `unreal`, never touches Content/ or a map. Writes one receipt,
SourceAssets/context-review/CityFacadeV1/visibility-<stamp>.json, plus visibility-latest.json.

Method (2.5D viewshed on a surface model):
  * Footprints, bases and roof heights are the exact buildings already in the level: the verified
    CitySource re-implementation of buildJerusalem() in Scripts/create_oldcity_facades.py.
  * Terrain is the same 257 x 257 DEM with the same two-triangle interpolation, vectorised.
  * DSM raster 4 m. Roofs are rasterised over the terrain.
  * Two world states, because the three viewpoint families see different cities:
      YECHEZKEL - the precinct deck (Z 0) and its 6-amah wall (top = max(ground, 0) + 288 cm),
                  buildings in every 100 m cell that holds an inside centroid HIDDEN
                  (policy hide_if_any_inside, as the precinct receipt records).
                  Viewpoints: the deck walk 10 m inside every wall, the five gates, the four
                  built approach flights sampled every 20 m.
      MODERN    - the whole city standing, no deck, no wall. Viewpoints: the Kotel plaza deck cells.
  * Each viewpoint casts 2,880 rays (0.125 deg) out to 1,500 m at 3 m steps with an eye 170 cm above
    its floor. A building is SEEN if any ray sample on it clears the running horizon.
The dove sees roofs from above everywhere, so the dove set is simply everything within 1.5 km of
the precinct; its need is a far read, not a facade.

Honest limits: the 2.5D model has no trees, no Temple, no Kotel wall mesh, no precinct gate
towers and no OldCityFacade parapets; a 4 m raster rounds footprints. Counts are measurements of
this model, not of the rendered frame.
"""
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
sys.path.insert(0, str(ROOT / 'Scripts'))
import create_oldcity_facades as F  # noqa: E402

OUT = ROOT / 'SourceAssets' / 'context-review' / 'CityFacadeV1'
PRECINCT = ROOT / 'SourceAssets' / 'enclosure-review' / 'precinct-Candidate48.json'
KOTEL_PLAN = ROOT / 'SourceAssets' / 'context-review' / 'KotelPlazaV1' / 'kotel-plaza-plan.json'
APPROACH_GLOB = 'native-approach-apply-Candidate48-*.json'

RES = 400.0            # cm per DSM cell
EYE = 170.0
RAYS = 2880
STEP = 300.0
RANGE = 150000.0
NEAR = 30000.0         # "up close": 300 m
MID = 80000.0
WALL_TOP = 288.0       # 6 amot at 48 cm


def terrain_z(xcm, ycm, src):
    """Vectorised CitySource.height_at (two-triangle), returned in UE cm."""
    xa = xcm / F.AMAH_CM - F.TX
    za = ycm / F.AMAH_CM - F.TZ
    size, step, origin = src.size, src.step, src.origin
    h = np.asarray(src.heights, dtype=np.float64).reshape(size, size)
    u = np.clip((xa - origin) / step, 0.0, size - 1.001)
    v = np.clip((za - origin) / step, 0.0, size - 1.001)
    i = u.astype(np.int64)
    j = v.astype(np.int64)
    a = u - i
    b = v - j
    h00 = h[j, i]
    h10 = h[j, i + 1]
    h01 = h[j + 1, i]
    h11 = h[j + 1, i + 1]
    lower = h00 + (h10 - h00) * a + (h01 - h00) * b
    upper = h11 + (h01 - h11) * (1.0 - a) + (h10 - h11) * (1.0 - b)
    return np.where(a + b <= 1.0, lower, upper) * F.AMAH_CM


def main():
    t0 = time.time()
    data = json.loads(Path(F.JERUSALEM_JSON if hasattr(F, 'JERUSALEM_JSON') else
                           r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\mikdash-walkthrough\public\context\jerusalem.json'
                           ).read_text(encoding='utf-8'))
    src = F.CitySource(data)
    kept, skipped = src.buildings()
    precinct = json.loads(PRECINCT.read_text(encoding='utf-8'))
    sq = precinct['square']['outerFacesCm']
    xw, xe, yn, ys = sq['xWest'], sq['xEast'], sq['yNorth'], sq['ySouth']

    # ---- the facade-shell scope, same rule as create_oldcity_facades.py
    ring, _, _ = F.old_city_ring(src)

    recs = []
    for b in kept:
        loop = [F.ue_xy(p[0], p[1]) for p in b['points']]
        cx, cy = F.ue_xy(b['centre'][0], b['centre'][1])
        in_ring = F.point_in_polygon(cx, cy, ring)
        in_scope = in_ring or F.near_polyline(ring, cx, cy, F.OLD_CITY_MARGIN_CM)
        recs.append({'id': b['id'], 'loop': loop, 'cx': cx, 'cy': cy,
                     'base': F.ue_z(b['base']), 'roof': F.ue_z(b['base'] + b['height']),
                     'inRing': in_ring, 'facadeShell': in_scope,
                     'cell': F.cell_key_of(cx, cy)})
    n = len(recs)

    # ---- the YECHEZKEL hide set: hide_if_any_inside by 100 m cell
    def inside(x, y):
        return xw < x < xe and yn < y < ys
    hidden_cells = {r['cell'] for r in recs if inside(r['cx'], r['cy'])}
    hidden = np.array([r['cell'] in hidden_cells for r in recs])

    # ---- raster frame
    x0, x1 = xw - RANGE - 5000, xe + RANGE + 5000
    y0, y1 = yn - RANGE - 5000, ys + RANGE + 5000
    W = int(math.ceil((x1 - x0) / RES))
    H = int(math.ceil((y1 - y0) / RES))
    xs = x0 + (np.arange(W) + 0.5) * RES
    ys_ = y0 + (np.arange(H) + 0.5) * RES
    gx, gy = np.meshgrid(xs, ys_)
    ground = terrain_z(gx, gy, src).astype(np.float32)

    order = sorted(range(n), key=lambda k: recs[k]['roof'])
    img = Image.new('I', (W, H), 0)
    draw = ImageDraw.Draw(img)
    for k in order:
        pts = [((p[0] - x0) / RES, (p[1] - y0) / RES) for p in recs[k]['loop']]
        if len(pts) >= 3:
            draw.polygon(pts, fill=k + 1)
    bid = np.array(img, dtype=np.int32)
    roof = np.array([r['roof'] for r in recs] + [0.0], dtype=np.float32)
    has = bid > 0
    roof_r = np.where(has, roof[np.maximum(bid - 1, 0)], -1e9)

    dsm_modern = np.maximum(ground, roof_r)
    # YECHEZKEL: drop hidden buildings, flatten the deck, raise the wall ring
    vis_mask = has & ~hidden[np.maximum(bid - 1, 0)]
    dsm_yech = np.maximum(ground, np.where(vis_mask, roof_r, -1e9))
    in_sq = (gx > xw) & (gx < xe) & (gy > yn) & (gy < ys)
    dsm_yech = np.where(in_sq, 0.0, dsm_yech)
    band = RES * 1.01
    on_wall = in_sq & ((gx - xw < band) | (xe - gx < band) | (gy - yn < band) | (ys - gy < band))
    dsm_yech = np.where(on_wall, np.maximum(ground, 0.0) + WALL_TOP, dsm_yech).astype(np.float32)
    bid_yech = np.where(vis_mask, bid, 0)

    # ---- viewpoints
    def gz(x, y):
        return float(terrain_z(np.array([x]), np.array([y]), src)[0])

    vps = {'deck': [], 'approach': [], 'kotel': []}
    for t in np.arange(0.0, 1.0001, 6000.0 / (xe - xw)):
        x = xw + t * (xe - xw)
        y = yn + t * (ys - yn)
        vps['deck'] += [(x, yn + 1000, EYE), (x, ys - 1000, EYE), (xw + 1000, y, EYE), (xe - 1000, y, EYE)]
    for g in precinct['gates']:
        gx0, gy0 = g['positionCm']
        vps['approach'].append((gx0, gy0, EYE))
    appr = sorted((ROOT / 'SourceAssets' / 'enclosure-review').glob(APPROACH_GLOB))[-1]
    ap = json.loads(appr.read_text(encoding='utf-8'))
    for a in ap['plan']['approaches']:
        if not a.get('built'):
            # the at-grade West entry: walk 60 m out into the city
            gx0, gy0 = a['gateCm']
            for d in range(0, 6001, 2000):
                vps['approach'].append((gx0 - d, gy0, gz(gx0 - d, gy0) + EYE))
            continue
        c = [c for c in a['candidates'] if c['name'] == a['chosen']][0]
        sx, sy = c['startCm']
        dx, dy = c['direction']
        run = c['runCm']
        for s in np.arange(0.0, run + 1, 2000.0):
            z = a['thresholdZcm'] + (a['footZcm'] - a['thresholdZcm']) * (s / run)
            vps['approach'].append((sx + dx * s, sy + dy * s, z + EYE))
    kp = json.loads(KOTEL_PLAN.read_text(encoding='utf-8'))
    for i, c in enumerate(kp['deck']):
        if i % 6 == 0:
            vps['kotel'].append((c['loc'][0], c['loc'][1], c['loc'][2] + EYE))

    # ---- viewshed
    az = np.linspace(0.0, 2 * math.pi, RAYS, endpoint=False)
    dist = np.arange(STEP, RANGE + 1, STEP, dtype=np.float32)
    cosA = np.cos(az)[:, None].astype(np.float32)
    sinA = np.sin(az)[:, None].astype(np.float32)
    seen = {k: np.full(n, np.inf) for k in vps}          # nearest distance at which the building is SEEN
    near = {k: np.full(n, np.inf) for k in vps}          # plain nearest distance (no LOS)
    cx = np.array([r['cx'] for r in recs])
    cy = np.array([r['cy'] for r in recs])
    for fam, pts in vps.items():
        dsm = dsm_modern if fam == 'kotel' else dsm_yech
        ids = bid if fam == 'kotel' else bid_yech
        present = np.ones(n, bool) if fam == 'kotel' else ~hidden
        for (px, py, pz) in pts:
            d2 = np.hypot(cx - px, cy - py)
            near[fam] = np.where(present, np.minimum(near[fam], d2), near[fam])
            sx = px + cosA * dist
            sy = py + sinA * dist
            ix = ((sx - x0) / RES).astype(np.int32)
            iy = ((sy - y0) / RES).astype(np.int32)
            np.clip(ix, 0, W - 1, out=ix)
            np.clip(iy, 0, H - 1, out=iy)
            h = dsm[iy, ix]
            ang = (h - pz) / dist
            run_max = np.maximum.accumulate(ang, axis=1)
            prev = np.concatenate([np.full((RAYS, 1), -1e9, np.float32), run_max[:, :-1]], axis=1)
            vis = ang >= prev - 1e-6
            b = ids[iy, ix]
            sel = vis & (b > 0)
            bb = b[sel] - 1
            dd = np.broadcast_to(dist, sel.shape)[sel]
            if bb.size:
                cur = np.full(n, np.inf)
                np.minimum.at(cur, bb, dd)
                seen[fam] = np.minimum(seen[fam], cur)

    def count(mask):
        return int(np.count_nonzero(mask))

    shell = np.array([r['facadeShell'] for r in recs])
    in_ring = np.array([r['inRing'] for r in recs])
    fams = {}
    any_seen = np.full(n, np.inf)
    any_near = np.full(n, np.inf)
    for fam in vps:
        s = seen[fam]
        any_seen = np.minimum(any_seen, s)
        any_near = np.minimum(any_near, near[fam])
        fams[fam] = {
            'viewpoints': len(vps[fam]),
            'within300m': count(near[fam] <= NEAR),
            'seenWithin300m': count(s <= NEAR),
            'seenWithin300mWithFacadeShell': count((s <= NEAR) & shell),
            'seenWithin300mPlainBox': count((s <= NEAR) & ~shell),
            'seen300to800m': count((s > NEAR) & (s <= MID)),
            'seenBeyond800m': count((s > MID) & np.isfinite(s)),
            'seenAnyDistance': count(np.isfinite(s)),
        }
    close = any_seen <= NEAR
    mid = (any_seen > NEAR) & (any_seen <= MID)
    precinct_centre = precinct['square']['centreCm']
    d_pc = np.maximum(np.maximum(xw - cx, cx - xe), np.maximum(yn - cy, cy - ys))
    dove = d_pc <= RANGE
    near_ids = [recs[k]['id'] for k in np.nonzero(close)[0]]
    near_plain = [recs[k]['id'] for k in np.nonzero(close & ~shell)[0]]
    near_cells = sorted({F.cell_name(recs[k]['cell']) for k in np.nonzero(close)[0]})
    near_plain_cells = sorted({F.cell_name(recs[k]['cell']) for k in np.nonzero(close & ~shell)[0]})

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt = {
        'status': 'measured_offline_2p5d_model',
        'stamp': stamp,
        'method': __doc__.strip().split('\n\n')[1],
        'parameters': {'dsmResolutionCm': RES, 'eyeCm': EYE, 'rays': RAYS, 'stepCm': STEP,
                       'rangeCm': RANGE, 'nearCm': NEAR, 'midCm': MID, 'precinctWallTopCm': WALL_TOP},
        'buildingsTotal': n, 'sourceSkipped': skipped,
        'hiddenInYechezkel': count(hidden),
        'withFacadeShell': count(shell), 'insideWallRing': count(in_ring),
        'families': fams,
        'union': {
            'within300mOfAnyVisitorPlace': count(any_near <= NEAR),
            'seenWithin300m': count(close),
            'seenWithin300mWithFacadeShell': count(close & shell),
            'seenWithin300mPlainBox': count(close & ~shell),
            'seen300to800m': count(mid),
            'seenBeyond800m': count((any_seen > MID) & np.isfinite(any_seen)),
            'neverSeenFromGround': count(~np.isfinite(any_seen)),
            'doveFarReadWithin1500mOfPrecinct': count(dove),
            'remainderBeyondDove': count(~dove),
        },
        'nearCells100m': near_cells,
        'nearPlainCells100m': near_plain_cells,
        'nearBuildingOsmIds': near_ids,
        'nearPlainBoxOsmIds': near_plain,
        'honestLimits': __doc__.strip().split('\n\n')[-1],
        'seconds': round(time.time() - t0, 1),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, indent=1)
    (OUT / ('visibility-%s.json' % stamp)).write_text(text, encoding='utf-8')
    (OUT / 'visibility-latest.json').write_text(text, encoding='utf-8')
    summary = {k: v for k, v in receipt.items() if k not in ('nearBuildingOsmIds', 'nearPlainBoxOsmIds', 'nearCells100m', 'nearPlainCells100m', 'method', 'honestLimits')}
    summary['nearCellCount'] = len(near_cells)
    summary['nearPlainCellCount'] = len(near_plain_cells)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()

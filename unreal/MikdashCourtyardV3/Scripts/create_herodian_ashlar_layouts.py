"""Anti-repeat attempt 4: Herodian Ashlar LAYOUT slices (Wang edges) for a Texture2DArray. Offline, stdlib only.

Shmuel, verbatim: "I don't wanna see, like, repeating patterns all over."

Attempt 3 varied the stone SURFACE per stone and fixed tone, but every tile kept one stone layout, so the joints
repeated every 300 cm (rising-joint repeat x0.93 of the control). This breaks the LAYOUT itself.

THE SCHEME (1-D Wang tiles along each course, bed joints shared):
  * Every 300 cm boundary k (texture u = 0, the same line for all three courses) carries a TYPE a in {0,1,2},
    hashed per (k, cell row cy) and shared by the three courses of that cell row.
  * In course c, the stone straddling boundary k runs from -p[c][a] to +q[c][a] cm: type a moves both joints of
    that stone. The segment between boundaries k and k+1 is that stone's right part, ONE interior stone, and the
    next boundary stone's left part.
  * Slice S(a,b) = the tile whose course rows run: type-a boundary stone's right part | interior | type-b boundary
    stone's left part. 9 slices (3 x 3) + 2 extra SURFACES of each diagonal S(a,a) = 15 slices.
  * The shader renders an INTERIOR pixel from S(a,b), and a BOUNDARY-stone pixel from a DIAGONAL slice S(x,x)^v of
    that stone's type x, the surface v hashed per (boundary, cell row, course). In S(x,x) the straddling stone is ONE
    stone that wraps inside ONE texture, so no stone is ever cut at a tile edge, and the texture's own wrap keeps it
    continuous across u = 0 at every mip. S(a,b)'s boundary region (a != b) is never rendered.
  * The switch between slices happens only at a rising joint (u = q[c][a] or 300 - p[c][b], analytic) or a bed joint
    (V5's course heights, identical in every slice), never inside a stone.
  * Per-stone surface variety (attempt 3's win) survives: boundary stones pick 1 of 3 surfaces of their type (9
    distinct), interior stones come from 9 pair slices (a == b interiors pick 1 of 3 surfaces).

Layout numbers: solved by an exact search (SourceAssets/material-review/HerodianAshlarV5Layouts/layout.json):
every stone in [1.25 H, 3.2 H] (V5's own rule, so no sliver), stagger >= 30 cm between courses of one cell row for
every type sequence, >= 35 cm across the cell-row bed joint for every independent pair, jitter 30 cm (types 15 cm
apart). Everything else - course heights, drafted margins, the 1.9 cm boss bevel, grain, palette - is
create_herodian_ashlar_v5.py's, called with its new explicit-layout mode.

  python Scripts/create_herodian_ashlar_layouts.py --screen 0,1,2      # seed candidates (128 px), parallel workers
  python Scripts/create_herodian_ashlar_layouts.py --screen-pick       # choose seeds keeping V5b colour
  python Scripts/create_herodian_ashlar_layouts.py --slice 3 [--size 2048]
  python Scripts/create_herodian_ashlar_layouts.py --prove              # structural proof over all written slices
"""
import argparse
import hashlib
import json
import random
import sys
import time
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import create_herodian_ashlar_v5 as g  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / 'SourceAssets' / 'material-review' / 'HerodianAshlarV5Layouts'
LAYOUT_JSON = OUT / 'layout.json'
T = g.TILE_CM
TAG = 'L'
V5B_COLOUR = {'R': 0.752, 'BoverR': 0.886, 'source': 'attempt-3 pool target (AGENTS.md: Ashlar R 0.752, B/R 0.886)'}


def slices():
    """Slice index -> (a, b, surface variant). 0..8 = S(a,b) at 3a+b (variant 0); 9..14 = S(x,x) variants 1, 2."""
    out = [(a, b, 0) for a in range(3) for b in range(3)]
    out += [(x, x, v) for x in range(3) for v in (1, 2)]
    return out


def diag_index(x, v):
    return 4 * x if v == 0 else 9 + 2 * x + (v - 1)


def load_layout():
    return json.loads(LAYOUT_JSON.read_text(encoding='utf-8'))


def course_stones(lay, a, b):
    """Per course: [(x0, L)] partitioning [0, 300) cyclically for slice S(a,b)."""
    out = []
    for c, pq in enumerate(lay['courses']):
        pa, qa = pq[a]
        pb, qb = pq[b]
        boundary = (-pb, pb + qa)                    # wraps u = 0: type-b left part .. type-a right part
        interior = (qa, T - qa - pb)
        out.append([boundary, interior])
    return out


def geometry_edge_seed(c, x0, L):
    """A stone's joint wobble from its GEOMETRY, so the same stone has the same joint half in every slice."""
    return zlib.crc32(('%d|%.4f|%.4f' % (c, x0 % T, L)).encode()) & 0x3fffffff


def generate_slice(idx, size, seeds, log):
    lay = load_layout()
    a, b, v = slices()[idx]
    cfg = g.VARIANTS['Ashlar']
    layout = course_stones(lay, a, b)
    seed = seeds[idx]
    orig = g.draw_block_surface

    def draw(cfg_, rng, L, H, x, y0):
        blk = orig(cfg_, rng, L, H, x, y0)
        c = min(range(len(lay['heightsExact'])), key=lambda i: abs(sum(lay['heightsExact'][:i]) - y0))
        blk['edge_seed'] = geometry_edge_seed(c, x, L)
        return blk
    g.draw_block_surface = draw
    try:
        maps, masks, schedule, seconds, extras = g.generate('Ashlar', cfg, size, log, surface_seed=seed, layout=layout)
    finally:
        g.draw_block_surface = orig
    return (a, b, v), layout, maps, masks, schedule, seconds, extras


def name_for(idx, kind, size):
    suffix = '' if size == g.DEFAULT_SIZE else '_%d' % size
    return 'T_HerodianV5%s_Ashlar_S%02d_%s%s.png' % (TAG, idx, kind, suffix)


def write_slice(idx, size, seeds, out=OUT, log=print):
    (a, b, v), layout, maps, masks, schedule, seconds, extras = generate_slice(idx, size, seeds, log)
    out.mkdir(parents=True, exist_ok=True)
    rec = {'slice': idx, 'a': a, 'b': b, 'surfaceVariant': v, 'surfaceSeed': seeds[idx], 'size': size,
           'layoutCm': layout, 'schedule': schedule, 'seconds': round(seconds, 1), 'files': {}}
    for kind in ('Albedo', 'Normal', 'ARM'):
        p = out / name_for(idx, kind, size)
        rec['files'][kind] = {'path': str(p.relative_to(ROOT)).replace('\\', '/'),
                              'sha256': g.write_png_rgb(p, size, size, maps[kind])}
    for kind in ('JointMask', 'Regions'):
        p = out / name_for(idx, kind, size)
        rec['files'][kind] = {'path': str(p.relative_to(ROOT)).replace('\\', '/'),
                              'sha256': g.write_png_rgb(p, size, size, extras[kind]), 'imported': False}
    rec['statistics'] = g.measure(maps, masks)
    s = rec['statistics']
    rec['colour'] = {'R': s['albedoSRGB']['R']['mean'], 'BoverR': s['albedoChroma']['BoverR_mean']}
    (out / ('slice-%02d%s.json' % (idx, '' if size == g.DEFAULT_SIZE else '_%d' % size))).write_text(
        json.dumps(rec, indent=1) + '\n', encoding='utf-8')
    log('slice %02d S(%d,%d)^%d seed %d: R %.4f B/R %.4f  %.0fs' % (idx, a, b, v, seeds[idx], rec['colour']['R'],
                                                                  rec['colour']['BoverR'], seconds))
    return rec


def screen_slices(idxs, size=128, per=8):
    """Surface-seed candidates for some slices at a small size (per-stone tint dominates the mean colour);
    one JSON per slice, so workers can run in parallel. --screen-pick chooses."""
    for idx in idxs:
        rows = []
        for k in range(per):
            seed = 7000 + 100 * idx + k
            (_, _, _), _, maps, masks, _, _, _ = generate_slice(idx, size, {idx: seed}, lambda m: None)
            s = g.measure(maps, masks)
            rows.append([seed, s['albedoSRGB']['R']['mean'], s['albedoChroma']['BoverR_mean']])
        (OUT / ('screen-%02d.json' % idx)).write_text(json.dumps({'slice': idx, 'size': size, 'candidates': rows}) + '\n',
                                                     encoding='utf-8')
        print('slice %d %s' % (idx, [(c[0], round(c[1], 3), round(c[2], 3)) for c in rows]), flush=True)


def screen_pick():
    """Choose one seed per slice so the 15-slice pool mean keeps V5b's R and B/R, preferring tonal spread."""
    lay = load_layout()
    cands = {i: [tuple(c) for c in json.loads((OUT / ('screen-%02d.json' % i)).read_text(encoding='utf-8'))['candidates']]
             for i in range(15)}
    pick = {i: min(cands[i], key=lambda c: abs(c[1] - V5B_COLOUR['R']) + abs(c[2] - V5B_COLOUR['BoverR'])) for i in cands}
    for _ in range(8):
        for i in cands:
            def cost(choice):
                trial = dict(pick)
                trial[i] = choice
                r = sum(c[1] for c in trial.values()) / 15.0
                br = sum(c[2] for c in trial.values()) / 15.0
                spread = max(c[1] for c in trial.values()) - min(c[1] for c in trial.values())
                return abs(r - V5B_COLOUR['R']) + abs(br - V5B_COLOUR['BoverR']) - 0.02 * spread
            pick[i] = min(cands[i], key=cost)
    lay['surfaceSeeds'] = {str(i): pick[i][0] for i in pick}
    lay['surfaceSeedScreen'] = {'size': json.loads((OUT / 'screen-00.json').read_text(encoding='utf-8'))['size'],
                                'poolMeanR': round(sum(c[1] for c in pick.values()) / 15, 4),
                                'poolMeanBoverR': round(sum(c[2] for c in pick.values()) / 15, 4), 'target': V5B_COLOUR,
                                'perSlice': {str(i): [round(pick[i][1], 4), round(pick[i][2], 4)] for i in pick}}
    LAYOUT_JSON.write_text(json.dumps(lay, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(lay['surfaceSeedScreen'], indent=1))


def prove(size=g.DEFAULT_SIZE):
    """Structural proof from the written slices: no stone cut at a tile edge, no sliver, bed joints shared,
    rising joints exactly where the shader switches, diagonal surfaces of one type share their layout."""
    lay = load_layout()
    H = lay['heightsExact']
    lo = [1.25 * h for h in H]
    hi = [3.2 * h for h in H]
    recs = {}
    for idx in range(15):
        p = OUT / ('slice-%02d%s.json' % (idx, '' if size == g.DEFAULT_SIZE else '_%d' % size))
        recs[idx] = json.loads(p.read_text(encoding='utf-8'))
    problems, checks = [], {}
    # 1. lengths (only the stones that are ever RENDERED: interiors of every slice, boundary stones of diagonals)
    rendered = []
    for idx, r in recs.items():
        for c, (bnd, inter) in enumerate(r['layoutCm']):
            rendered.append((c, inter[1], 'interior S%02d' % idx))
            if r['a'] == r['b']:
                rendered.append((c, bnd[1], 'boundary type %d S%02d' % (r['a'], idx)))
    short = [x for x in rendered if not (lo[x[0]] - 1e-6 <= x[1] <= hi[x[0]] + 1e-6)]
    checks['stoneLengthsCm'] = {'min': round(min(x[1] for x in rendered), 2), 'max': round(max(x[1] for x in rendered), 2),
                                'rule': '1.25 H .. 3.2 H per course (V5)', 'violations': short}
    problems += ['length %s' % (x,) for x in short]
    # 2. no stone cut at a tile edge: the only stone crossing u = 0 in any slice is the boundary block, and it is
    #    rendered only from a diagonal slice, where it is ONE stone of ONE type
    for idx, r in recs.items():
        for c, (bnd, inter) in enumerate(r['layoutCm']):
            if not (0 < inter[0] and inter[0] + inter[1] < T):
                problems.append('S%02d course %d: the interior stone crosses the tile edge' % (idx, c))
    checks['tileEdge'] = 'every interior stone lies inside (0, 300); boundary stones are rendered only from diagonals'
    # 3. bed joints: identical course heights in every slice
    hs = {tuple(round(h, 6) for h in r['schedule']['courseHeightsCm']) for r in recs.values()}
    checks['courseHeightsCmAllSlices'] = [list(x) for x in hs]
    if len(hs) != 1:
        problems.append('course heights differ between slices: %s' % hs)
    # 4. rising joints at the analytic switch lines, read from the written JointMask pixels
    px = T / size
    jm_ok = 0
    for idx, r in recs.items():
        w, h_, rows = g.decode_png_rgb8(ROOT / r['files']['JointMask']['path'])
        y0 = 0.0
        for c, (bnd, inter) in enumerate(r['layoutCm']):
            yc = int((y0 + H[c] / 2.0) / px)
            for xcm in (inter[0], inter[0] + inter[1]):
                xi = int(xcm / px)
                row = rows[yc]
                hit = any(row[3 * ((xi + d) % size)] == 255 for d in range(-3, 4))
                jm_ok += hit
                if not hit:
                    problems.append('S%02d course %d: no joint pixel at the switch line %.2f cm' % (idx, c, xcm))
            y0 += H[c]
    checks['jointAtSwitchLines'] = '%d of %d' % (jm_ok, 15 * 3 * 2)
    # 5. diagonal surfaces of one type share their JointMask pixel for pixel (same stones, same geometry-seeded wobble)
    diag = {}
    for idx, r in recs.items():
        if r['a'] == r['b']:
            diag.setdefault(r['a'], []).append(r['files']['JointMask']['sha256'])
    checks['diagonalJointMaskSha'] = {str(k): v for k, v in diag.items()}
    for k, v in diag.items():
        if len(set(v)) != 1:
            problems.append('type %d diagonal surfaces do not share their joints' % k)
    # 6. colour of the pool
    rr = [r['colour']['R'] for r in recs.values()]
    br = [r['colour']['BoverR'] for r in recs.values()]
    checks['colour'] = {'poolMeanR': round(sum(rr) / 15, 4), 'poolMeanBoverR': round(sum(br) / 15, 4), 'target': V5B_COLOUR,
                        'perSliceRMinMax': [round(min(rr), 4), round(max(rr), 4)]}
    if abs(checks['colour']['poolMeanR'] - V5B_COLOUR['R']) > 0.015 or abs(checks['colour']['poolMeanBoverR'] - V5B_COLOUR['BoverR']) > 0.015:
        problems.append('pool colour off V5b: %s' % checks['colour'])
    # 7. the V5 dressing parameters are untouched
    cfg = g.VARIANTS['Ashlar']
    checks['v5Parameters'] = {'boss_edge_cm': cfg['boss_edge_cm'], 'grain_cm': cfg['grain_cm'], 'base_srgb': cfg['base_srgb'],
                              'generatorSha256': hashlib.sha256((HERE / 'create_herodian_ashlar_v5.py').read_bytes()).hexdigest()}
    if cfg['boss_edge_cm'] != 1.9:
        problems.append('boss bevel is not 1.9 cm')
    out = {'status': 'LAYOUT_SLICES_PROVED' if not problems else 'LAYOUT_SLICES_PROBLEMS', 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'script': 'Scripts/create_herodian_ashlar_layouts.py', 'scriptSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'size': size, 'checks': checks, 'problems': problems,
           'files': {str(i): r['files'] for i, r in recs.items()}}
    (OUT / ('layout-proof%s.json' % ('' if size == g.DEFAULT_SIZE else '_%d' % size))).write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('status', 'problems')}, indent=1))
    print(json.dumps(checks, indent=1)[:3000])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--screen', type=str, help='comma-separated slice indices to screen')
    ap.add_argument('--screen-pick', action='store_true')
    ap.add_argument('--slice', type=int, action='append')
    ap.add_argument('--size', type=int, default=g.DEFAULT_SIZE)
    ap.add_argument('--prove', action='store_true')
    a = ap.parse_args()
    if a.screen:
        screen_slices([int(x) for x in a.screen.split(',')])
    if a.screen_pick:
        screen_pick()
    if a.slice:
        seeds = {int(k): v for k, v in load_layout()['surfaceSeeds'].items()}
        for idx in a.slice:
            write_slice(idx, a.size, seeds)
    if a.prove:
        prove(a.size)


if __name__ == '__main__':
    main()

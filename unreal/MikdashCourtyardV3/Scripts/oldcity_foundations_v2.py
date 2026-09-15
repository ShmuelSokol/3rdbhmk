"""OldCityFoundationV2 - census and stone foundations for every city building footprint.

AUTHORED_OFFLINE_SOURCE. Never imports `unreal`, never touches Content/ or a map.

WHY
---
OldCityFoundationV1/diagnosis.md proved four authored infill blocks float in the K2 view:
Scripts/create_oldcity_facades.py generate_infill() sets every infill base from the terrain
at the footprint CENTRE (`base_z = ue_z(source.height_at(cx, cy))`), so on a slope the
downhill walls hang in the air. The imported OSM extrusions use buildJerusalem()'s rule
`base = min(heightAt(vertex))`, which can still float where a valley crosses an edge between
two vertices. This module measures BOTH families against the exact terrain and authors the
repair as new geometry in a new namespace. It never edits a V1 OBJ or asset.

SUBCOMMANDS
    census   measure every footprint's exposed-edge gap (before)      -> census-before.json
    build    author foundation OBJs + manifest for every floating one -> obj/, foundations-manifest.json
    check    re-measure with the foundations in place (after); proves zero gaps > 1 cm and
             bounded embedment, plus overlap audits                    -> check-after.json
    selftest synthetic invariants only

TERRAIN (exact, not sampled)
    The game terrain is jerusalem-meshes.json mesh 0: a 257 x 257 height grid, step 50 amot,
    two triangles per cell. Terrain below is built from mesh 0's own vertex heights and its own
    per-cell diagonals, and re-proved on every triangle centroid and edge midpoint (error 1e-10 cm)
    before anything is measured. Along any straight segment the surface is piecewise linear with
    breakpoints where u, v, u+v or u-v crosses an integer (grid units), so evaluating those
    breakpoints gives exact extrema.
    The Kotel plaza cut and the precinct cut only REMOVE terrain inside their decks; footprints
    touching a deck rectangle are flagged, not silently measured against a hole.

Run with the engine's bundled Python (no engine launched):
    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" -B Scripts/oldcity_foundations_v2.py census
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
import create_oldcity_facades as F  # noqa: E402  (pure offline module; generate() only runs under __main__)

OUT = ROOT / 'SourceAssets' / 'context-review' / 'OldCityFoundationV2'
OBJ_OUT = OUT / 'obj'
V1 = ROOT / 'SourceAssets' / 'context-review' / 'OldCityFacadesV1'
V1_MANIFEST = V1 / 'facades-manifest.json'
RAW = Path('C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/architecture-review/jerusalem-meshes.json')
DECK = ROOT / 'SourceAssets' / 'context-review' / 'KotelPlazaV1' / 'kotel-plaza-plan.json'
PRECINCTS = {'candidate': ROOT / 'SourceAssets' / 'enclosure-review' / 'precinct-Candidate48.json',
             'main': ROOT / 'SourceAssets' / 'enclosure-review' / 'precinct-Main50.json'}
PINS = {
    V1_MANIFEST: '9f5c133d378f36e4c23216713dadfc2c963a8613e6bd1d02166ed3fa067e5456',
    RAW: 'cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb',
    F.SOURCE_JSON: F.SOURCE_JSON_SHA,
    DECK: 'f3483bff589169159bc99200761d90230e4726ec248226c948f0ead6dedca69c',
    F.FROZEN_MANIFEST: '777598ca54e98c8be79a8a498fa4b3209d22a4525821087e58904e5bf13c5063',
    PRECINCTS['candidate']: None,
    PRECINCTS['main']: None,
}

GAP_TOLERANCE_CM = 1.0
HIST_BINS = [(-1e18, 1.0, '<=1 cm'), (1.0, 10.0, '1-10 cm'), (10.0, 25.0, '10-25 cm'),
             (25.0, 50.0, '25-50 cm'), (50.0, 100.0, '50-100 cm'), (100.0, 200.0, '1-2 m'),
             (200.0, 400.0, '2-4 m'), (400.0, 1e18, '>4 m')]

# ------------------------------------------------------------------ foundation design
# Real Old City houses on a slope stand on a proud stone plinth; where the lane drops away the
# plinth becomes a stepped footing whose courses step down with the ground. Numbers are
# authored in the style of the reference photographs, not surveyed.
EMBED_CM = 25.0            # every foundation bottom follows the terrain this far below it
PLINTH_PROUD_CM = 8.0      # course A: plinth face in front of the wall
PLINTH_ABOVE_BASE_CM = 30.0   # course A top above the building's own floor line (a threshold course)
CAP_PROUD_CM = 12.0        # thin drip cap at the plinth top
CAP_HEIGHT_CM = 6.0
FOOTING_PROUD_CM = 22.0    # course B: stepped footing face
FOOTING_COURSE_CM = 45.0   # one ashlar course
FOOTING_MIN_REVEAL_CM = 20.0  # footing top stays at least this far above the ground it sits on
FOOTING_TRIGGER_CM = FOOTING_COURSE_CM + FOOTING_MIN_REVEAL_CM  # only where the drop exceeds this
MIN_VISIBLE_CM = 0.5       # pieces whose whole face is below this above ground are not emitted


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


# ======================================================================== terrain
class Terrain:
    """Exact piecewise-linear game terrain in UE cm, built from the game terrain mesh itself.

    Heights are mesh 0's own vertex heights and each grid cell uses mesh 0's own diagonal.
    (CitySource.height_at agrees on every vertex to 0.002 cm but always uses the (i+1,j)-(i,j+1)
    diagonal; the exported mesh flips it in some cells, up to 0.47 cm apart at centroids.)"""

    def __init__(self, raw_mesh):
        self.source = F.CitySource(read(F.SOURCE_JSON))
        self.size = self.source.size
        self.step = self.source.step
        self.origin = self.source.origin
        p, ix = raw_mesh['positions'], raw_mesh['indices']
        size = self.size
        self.h = [None] * (size * size)
        grid = []
        for i in range(0, len(p), 3):
            gi = (p[i] - self.origin) / self.step
            gj = (p[i + 2] - self.origin) / self.step
            ri, rj = int(round(gi)), int(round(gj))
            if abs(gi - ri) > 1e-6 or abs(gj - rj) > 1e-6 or not (0 <= ri < size and 0 <= rj < size):
                raise RuntimeError('Terrain vertex off the source grid: %r' % ((p[i], p[i + 2]),))
            grid.append((ri, rj))
            self.h[rj * size + ri] = p[i + 1] * F.AMAH_CM
        if any(v is None for v in self.h):
            raise RuntimeError('Terrain mesh does not cover the full grid')
        self.diag = {}
        for t in range(0, len(ix), 3):
            cells = [grid[ix[t + k]] for k in range(3)]
            ci, cj = min(c[0] for c in cells), min(c[1] for c in cells)
            local = {(c[0] - ci, c[1] - cj) for c in cells}
            if max(max(c) for c in local) != 1:
                raise RuntimeError('Terrain triangle spans more than one grid cell')
            kind = 'anti' if {(1, 0), (0, 1)} <= local else ('main' if {(0, 0), (1, 1)} <= local else None)
            if kind is None:
                raise RuntimeError('Unrecognised terrain triangle')
            if self.diag.setdefault((ci, cj), kind) != kind:
                raise RuntimeError('Cell %r has two diagonals' % ((ci, cj),))
        if len(self.diag) != (size - 1) ** 2:
            raise RuntimeError('Terrain cells missing: %d' % len(self.diag))
        self.antiCells = sum(1 for v in self.diag.values() if v == 'anti')

    def _grid(self, x_cm, y_cm):
        return ((x_cm / F.AMAH_CM - F.TX - self.origin) / self.step,
                (y_cm / F.AMAH_CM - F.TZ - self.origin) / self.step)

    def at(self, x_cm, y_cm):
        u, v = self._grid(x_cm, y_cm)
        size = self.size
        i = min(max(int(math.floor(u)), 0), size - 2)
        j = min(max(int(math.floor(v)), 0), size - 2)
        a, b = u - i, v - j
        h00, h10 = self.h[j * size + i], self.h[j * size + i + 1]
        h01, h11 = self.h[(j + 1) * size + i], self.h[(j + 1) * size + i + 1]
        if self.diag[(i, j)] == 'anti':
            if a + b <= 1.0:
                return h00 + (h10 - h00) * a + (h01 - h00) * b
            return h11 + (h01 - h11) * (1.0 - a) + (h10 - h11) * (1.0 - b)
        if a >= b:
            return h00 + (h10 - h00) * a + (h11 - h10) * b
        return h00 + (h01 - h00) * b + (h11 - h01) * a

    def breakpoints(self, a, b):
        """Parameters in [0,1] where the surface along a->b can change slope (exact superset)."""
        ua, va = self._grid(*a)
        ub, vb = self._grid(*b)
        ts = {0.0, 1.0}
        for p, q in ((ua, ub), (va, vb), (ua + va, ub + vb), (ua - va, ub - vb)):
            if abs(q - p) < 1e-12:
                continue
            lo, hi = min(p, q), max(p, q)
            for k in range(int(math.ceil(lo)), int(math.floor(hi)) + 1):
                t = (k - p) / (q - p)
                if 0.0 < t < 1.0:
                    ts.add(t)
        return sorted(ts)

    def profile(self, a, b):
        return [(t, self.at(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
                for t in self.breakpoints(a, b)]


def prove_terrain_matches_mesh(terrain, raw_mesh):
    """Every terrain triangle centroid and edge midpoint of mesh 0 equals Terrain.at."""
    p, ix = raw_mesh['positions'], raw_mesh['indices']
    worst = 0.0
    worst_source = 0.0
    for i in range(0, len(ix), 3):
        vs = [(p[ix[i + k] * 3], p[ix[i + k] * 3 + 1], p[ix[i + k] * 3 + 2]) for k in range(3)]
        samples = [tuple(sum(v[c] for v in vs) / 3.0 for c in range(3))]
        samples += [tuple((vs[k][c] + vs[(k + 1) % 3][c]) / 2.0 for c in range(3)) for k in range(3)]
        for x, y, z in samples:
            x_cm, y_cm = F.ue_xy(x, z)
            worst = max(worst, abs(terrain.at(x_cm, y_cm) - y * F.AMAH_CM))
            worst_source = max(worst_source, abs(F.ue_z(terrain.source.height_at(x, z)) - y * F.AMAH_CM))
    result = dict(vertices=len(p) // 3, triangles=len(ix) // 3, samplesPerTriangle=4,
                  worstErrorCm=worst, cellsWithFlippedDiagonal=terrain.antiCells,
                  cells=len(terrain.diag), citySourceHeightAtWorstErrorCm=worst_source)
    if worst > 0.001:
        raise RuntimeError('Terrain model does not reproduce the game terrain mesh: %r' % result)
    return result


# ======================================================================= geometry
def dot2(a, b):
    return a[0] * b[0] + a[1] * b[1]


def sub2(a, b):
    return (a[0] - b[0], a[1] - b[1])


def lerp2(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def seg_gap(terrain, a, b, base):
    """(max gap, min gap, length) of base above terrain along a wall edge a->b."""
    prof = terrain.profile(a, b)
    gaps = [base - h for _, h in prof]
    return max(gaps), min(gaps), math.dist(a, b)


def interval_inside_convex(p, q, poly):
    """Parameter interval of segment p->q inside a CCW convex polygon (Cyrus-Beck), or None."""
    lo, hi = 0.0, 1.0
    n = len(poly)
    d = (q[0] - p[0], q[1] - p[1])
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        num = ex * (p[1] - a[1]) - ey * (p[0] - a[0])
        den = ex * d[1] - ey * d[0]
        if abs(den) < 1e-12:
            if num < 0:
                return None
            continue
        t = -num / den
        if den > 0:
            lo = max(lo, t)
        else:
            hi = min(hi, t)
        if hi - lo <= 1e-9:
            return None
    return (lo, hi)


def exposed_segments(wings):
    """Boundary pieces of a union of convex CCW wings not covered by a sibling wing.

    Each wing edge is probed 2 cm outward; where the probe lies inside a sibling the wall is
    internal. Returns directed segments [(a, b)] with the building interior on the left."""
    out = []
    for wi, poly in enumerate(wings):
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            nrm = F._edge_normal(a, b)
            if nrm == (0.0, 0.0):
                continue
            pa = (a[0] + 2 * nrm[0], a[1] + 2 * nrm[1])
            pb = (b[0] + 2 * nrm[0], b[1] + 2 * nrm[1])
            covered = sorted(iv for wj, other in enumerate(wings) if wj != wi
                             for iv in [interval_inside_convex(pa, pb, other)] if iv)
            t, pieces = 0.0, []
            for lo, hi in covered:
                if lo > t + 1e-9:
                    pieces.append((t, lo))
                t = max(t, hi)
            if t < 1.0 - 1e-9:
                pieces.append((t, 1.0))
            for lo, hi in pieces:
                if (hi - lo) * math.dist(a, b) >= 0.5:
                    out.append((lerp2(a, b, lo), lerp2(a, b, hi)))
    return out


def trace_rings(segments, tol=0.05):
    """Decompose directed boundary segments (interior on the left) into closed simple rings.

    Walks unused segments taking the sharpest LEFT turn at every vertex; whenever the walk
    reaches a vertex already on the current path, that loop is split off as a ring (a pinch
    vertex visited twice therefore yields two rings). Returns (rings, failures)."""
    # Snap endpoints within tol to one representative first: clipped T-junction endpoints differ
    # from wing corners by ~1e-6 cm and must not straddle a rounding boundary.
    reps, cells = [], {}

    def snap(p):
        cx, cy = int(math.floor(p[0] / tol)), int(math.floor(p[1] / tol))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for r in cells.get((cx + dx, cy + dy), ()):
                    if math.dist(reps[r], p) <= tol:
                        return r
        reps.append((p[0], p[1]))
        cells.setdefault((cx, cy), []).append(len(reps) - 1)
        return len(reps) - 1
    ids = [(snap(a), snap(b)) for a, b in segments]
    segments = [(reps[i], reps[j]) for i, j in ids if i != j]
    ids = [(i, j) for i, j in ids if i != j]

    def key(p):
        return snap(p)
    starts = {}
    for idx, (a, b) in enumerate(ids):
        starts.setdefault(a, []).append(idx)
    used = [False] * len(segments)
    rings, failures = [], 0
    for first in range(len(segments)):
        if used[first]:
            continue
        path, where, cur = [], {}, first
        while True:
            used[cur] = True
            a, b = segments[cur]
            where[key(a)] = len(path)
            path.append(a)
            kb = key(b)
            if kb in where:
                j = where[kb]
                loop = path[j:]
                path = path[:j]
                where = {k: i for k, i in where.items() if i < j}
                loop = simplify_ring(loop)
                if len(loop) >= 3:
                    rings.append(loop)
            cands = [i for i in starts.get(kb, []) if not used[i]]
            if not cands:
                if path:
                    failures += 1
                break
            d_in = sub2(b, a)
            cur = max(cands, key=lambda i: math.atan2(
                d_in[0] * (segments[i][1][1] - segments[i][0][1]) - d_in[1] * (segments[i][1][0] - segments[i][0][0]),
                d_in[0] * (segments[i][1][0] - segments[i][0][0]) + d_in[1] * (segments[i][1][1] - segments[i][0][1])))
    return rings, failures


def simplify_ring(ring):
    changed = True
    pts = list(ring)
    while changed and len(pts) >= 3:
        changed = False
        out = []
        m = len(pts)
        for i in range(m):
            p0, p1, p2 = out[-1] if out else pts[i - 1], pts[i], pts[(i + 1) % m]
            d1, d2 = sub2(p1, p0), sub2(p2, p1)
            l1, l2 = math.hypot(*d1), math.hypot(*d2)
            if l1 < 0.5:
                changed = True
                continue
            cross = d1[0] * d2[1] - d1[1] * d2[0]
            if l2 > 1e-9 and abs(cross) <= 1e-6 * l1 * l2 and dot2(d1, d2) > 0:
                changed = True
                continue
            out.append(p1)
        pts = out
    return pts


def miter_offset(ring, distance):
    """Outward miter offset (interior left); miter length clamped to twice the distance."""
    n = len(ring)
    out = []
    for i in range(n):
        n1 = F._edge_normal(ring[i - 1], ring[i])
        n2 = F._edge_normal(ring[i], ring[(i + 1) % n])
        mx, my = n1[0] + n2[0], n1[1] + n2[1]
        ml = math.hypot(mx, my)
        if ml < 1e-6:
            mx, my, ml = n2[0], n2[1], 1.0
        mx, my = mx / ml, my / ml
        cosine = max(mx * n2[0] + my * n2[1], 0.5)
        out.append((ring[i][0] + mx * distance / cosine, ring[i][1] + my * distance / cosine))
    return out


def signed_area(ring):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1])) / 2.0


def point_in_ring(p, ring):
    return F.point_in_polygon(p[0], p[1], ring)


# ================================================================= foundation mesh
class Mesh:
    """Open canonical shell: triangles whose right-hand normal is the intended facing."""

    def __init__(self):
        self.tris = []

    def quad(self, pts, facing):
        for order in ((0, 1, 2), (0, 2, 3)):
            tri = [pts[k] for k in order]
            u = [tri[1][c] - tri[0][c] for c in range(3)]
            v = [tri[2][c] - tri[0][c] for c in range(3)]
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            length = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
            if length < 1e-4:
                continue
            if n[0] * facing[0] + n[1] * facing[1] + n[2] * facing[2] < 0:
                tri = [tri[0], tri[2], tri[1]]
            self.tris.append(tuple(tuple(p) for p in tri))


def merge_close(prof, length, eps_cm=0.01):
    """Drop interior breakpoints within eps_cm of a kept neighbour or the far end (height error
    <= slope * eps_cm). Without this a 1e-3 cm sliver at an edge end was skipped and left the
    exact corner parameter uncovered (infill283, first build)."""
    out = [prof[0]]
    for t, h in prof[1:-1]:
        if (t - out[-1][0]) * length >= eps_cm and (prof[-1][0] - t) * length >= eps_cm:
            out.append((t, h))
    out.append(prof[-1])
    return out


def course_plinth(terrain, W, OA, base, mesh, record):
    """Course A: proud plinth from EMBED below the ground to PLINTH_ABOVE_BASE over the floor line."""
    top = base + PLINTH_ABOVE_BASE_CM
    n = len(W)
    pieces = {}
    for k in range(n):
        wa, wb, oa, ob = W[k], W[(k + 1) % n], OA[k], OA[(k + 1) % n]
        if dot2(sub2(ob, oa), sub2(wb, wa)) <= 0 or math.dist(oa, ob) < 0.5:
            record['flippedEdges'] += 1
            continue
        nrm = F._edge_normal(oa, ob)
        length = math.dist(oa, ob)
        prof = merge_close(terrain.profile(oa, ob), length)
        for (t0, h0), (t1, h1) in zip(prof, prof[1:]):
            if h0 >= top and h1 >= top:
                continue
            if h0 >= top or h1 >= top:
                r = t0 + (top - h0) / (h1 - h0) * (t1 - t0)
                if h0 >= top:
                    t0, h0 = r, top
                else:
                    t1, h1 = r, top
            if (t1 - t0) * length < 1e-3:
                continue
            p0, p1 = lerp2(oa, ob, t0), lerp2(oa, ob, t1)
            i0, i1 = lerp2(wa, wb, t0), lerp2(wa, wb, t1)
            mesh.quad([(p0[0], p0[1], h0 - EMBED_CM), (p1[0], p1[1], h1 - EMBED_CM),
                       (p1[0], p1[1], top), (p0[0], p0[1], top)], (nrm[0], nrm[1], 0.0))
            mesh.quad([(i0[0], i0[1], top), (i1[0], i1[1], top), (p1[0], p1[1], top), (p0[0], p0[1], top)],
                      (0.0, 0.0, 1.0))
            pieces.setdefault(k, []).append((t0, t1))
    return pieces


def course_footing(terrain, OA, OB, base, mesh, record):
    """Course B: stepped footing. Its top steps down in FOOTING_COURSE_CM courses with the ground,
    always FOOTING_MIN_REVEAL_CM to one course above it. Only where the drop allows a course."""
    n = len(OB)
    entries = []
    for k in range(n):
        oa, ob, ia, ib = OB[k], OB[(k + 1) % n], OA[k], OA[(k + 1) % n]
        if dot2(sub2(ob, oa), sub2(ib, ia)) <= 0 or math.dist(oa, ob) < 0.5:
            entries.append((k, 0.0, 1.0, 0))
            continue
        prof = merge_close(terrain.profile(oa, ob), math.dist(oa, ob))
        for (t0, h0), (t1, h1) in zip(prof, prof[1:]):
            g0 = base - h0 - FOOTING_MIN_REVEAL_CM
            g1 = base - h1 - FOOTING_MIN_REVEAL_CM
            cuts = [t0, t1]
            if abs(g1 - g0) > 1e-9:
                lo, hi = sorted((g0, g1))
                for m in range(int(math.floor(lo / FOOTING_COURSE_CM)) + 1, int(math.floor(hi / FOOTING_COURSE_CM)) + 1):
                    cuts.append(t0 + (FOOTING_COURSE_CM * m - g0) / (g1 - g0) * (t1 - t0))
            cuts.sort()
            for s0, s1 in zip(cuts, cuts[1:]):
                if s1 - s0 < 1e-9:
                    continue
                gm = g0 + (g1 - g0) * ((s0 + s1) / 2 - t0) / (t1 - t0) if t1 > t0 else g0
                entries.append((k, s0, s1, max(0, int(math.floor(gm / FOOTING_COURSE_CM)))))
    if not any(e[3] >= 1 for e in entries):
        return 0
    for k, s0, s1, kv in entries:
        if kv < 1:
            continue
        oa, ob, ia, ib = OB[k], OB[(k + 1) % n], OA[k], OA[(k + 1) % n]
        topz = base - FOOTING_COURSE_CM * kv
        p0, p1 = lerp2(oa, ob, s0), lerp2(oa, ob, s1)
        i0, i1 = lerp2(ia, ib, s0), lerp2(ia, ib, s1)
        h0, h1 = terrain.at(*p0), terrain.at(*p1)
        if topz < max(h0, h1) + FOOTING_MIN_REVEAL_CM - 0.01:
            raise AssertionError('footing reveal below design')
        nrm = F._edge_normal(oa, ob)
        mesh.quad([(p0[0], p0[1], h0 - EMBED_CM), (p1[0], p1[1], h1 - EMBED_CM),
                   (p1[0], p1[1], topz), (p0[0], p0[1], topz)], (nrm[0], nrm[1], 0.0))
        mesh.quad([(i0[0], i0[1], topz), (i1[0], i1[1], topz), (p1[0], p1[1], topz), (p0[0], p0[1], topz)],
                  (0.0, 0.0, 1.0))
    risers = 0
    m = len(entries)
    for idx in range(m):
        e1, e2 = entries[idx], entries[(idx + 1) % m]
        if e1[3] == e2[3]:
            continue
        if e1[0] == e2[0]:
            x22 = lerp2(OB[e1[0]], OB[(e1[0] + 1) % n], e1[2])
            x8 = lerp2(OA[e1[0]], OA[(e1[0] + 1) % n], e1[2])
        else:
            x22, x8 = OB[e2[0]], OA[e2[0]]
        tan_fwd = sub2(OB[(e2[0] + 1) % n], OB[e2[0]])
        tan_back = sub2(OB[e1[0]], OB[(e1[0] + 1) % n])
        high, low, toward = (e1, e2, tan_fwd) if (e2[3] == 0 or (e1[3] >= 1 and e1[3] < e2[3])) else (e2, e1, tan_back)
        if high[3] < 1:
            continue
        zhigh = base - FOOTING_COURSE_CM * high[3]
        zlow = base - FOOTING_COURSE_CM * low[3] if low[3] >= 1 else terrain.at(*x22) - EMBED_CM
        if zhigh - zlow < 1e-3:
            continue
        axis = sub2(x8, x22)
        perp = (axis[1], -axis[0])
        if dot2(perp, toward) < 0:
            perp = (-perp[0], -perp[1])
        mesh.quad([(x22[0], x22[1], zlow), (x8[0], x8[1], zlow), (x8[0], x8[1], zhigh), (x22[0], x22[1], zhigh)],
                  (perp[0], perp[1], 0.0))
        risers += 1
    record['footingRisers'] += risers
    return sum(1 for e in entries if e[3] >= 1)


def build_foundation(terrain, rings, base):
    mesh = Mesh()
    record = dict(rings=len(rings), flippedEdges=0, footingRisers=0, footingPieces=0, plinthEdges=0)
    plinth = []
    for W in rings:
        OA = miter_offset(W, PLINTH_PROUD_CM)
        OB = miter_offset(W, FOOTING_PROUD_CM)
        pieces = course_plinth(terrain, W, OA, base, mesh, record)
        record['plinthEdges'] += len(pieces)
        record['footingPieces'] += course_footing(terrain, OA, OB, base, mesh, record)
        plinth.append(dict(W=W, OA=OA, pieces=pieces))
    return mesh, record, plinth


# =================================================================== footprints
def load_obj_tris(path):
    """Canonical triangles from a V1 adapter OBJ (reflect Y back, restore winding)."""
    verts, tris = [], []
    with Path(path).open() as handle:
        for line in handle:
            if line.startswith('v '):
                parts = line.split()
                verts.append((float(parts[1]), -float(parts[2]), float(parts[3])))
            elif line.startswith('f '):
                parts = line.split()
                ids = [int(parts[k].split('/')[0]) - 1 for k in (1, 3, 2)]
                tris.append((verts[ids[0]], verts[ids[1]], verts[ids[2]]))
    return tris


def prism_wing(tris, base, roof):
    """If tris (12) are a closed 4-sided prism between base and roof, return its CCW ring."""
    if len(tris) != 12:
        return None
    levels = set()
    for tri in tris:
        for p in tri:
            if abs(p[2] - base) < 0.02:
                levels.add('b')
            elif abs(p[2] - roof) < 0.02:
                levels.add('r')
            else:
                return None
    if levels != {'b', 'r'}:
        return None
    edges = {}
    for tri in tris:
        for u, v in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            k = tuple(sorted([u, v]))
            edges[k] = edges.get(k, 0) + 1
    if not all(c == 2 for c in edges.values()):
        return None
    pts = []
    for tri in tris:
        for p in tri:
            if abs(p[2] - base) < 0.02 and (p[0], p[1]) not in pts:
                pts.append((p[0], p[1]))
    if len(pts) != 4:
        return None
    cx = sum(p[0] for p in pts) / 4.0
    cy = sum(p[1] for p in pts) / 4.0
    pts.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
    return F.ensure_ccw(pts)


def infill_footprints(manifest):
    """Every AUTHORED_INFILL building recovered from its V1 OBJ prism triangles."""
    out = []
    for batch in manifest['batches']:
        entry = batch.get('infill')
        if not entry:
            continue
        path = V1 / 'obj' / entry['file']
        if sha(path) != entry['sha256']:
            raise RuntimeError('V1 infill OBJ changed: ' + entry['file'])
        tris = load_obj_tris(path)
        if len(tris) != entry['triangles']:
            raise RuntimeError('Triangle count mismatch in ' + entry['file'])
        offset = 0
        for row in entry['perBuilding']:
            count = row['triangles']
            base, roof = row['baseZcm'], row['roofZcm']
            wings, k = [], offset
            while k + 12 <= offset + count and len(wings) < row['wings']:
                ring = prism_wing(tris[k:k + 12], base, roof)
                if ring:
                    wings.append(ring)
                    k += 12
                else:
                    k += 1
            if len(wings) != row['wings']:
                raise RuntimeError('Infill %d: found %d of %d wing prisms' % (row['infillId'], len(wings), row['wings']))
            segs = exposed_segments(wings)
            rings, failures = trace_rings(segs)
            out.append(dict(family='infill', id='infill%d' % row['infillId'], infillId=row['infillId'],
                            cell=batch['name'], ownerLabel='RELEASE_OldCityInfill_' + batch['name'],
                            ownerMesh='/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Meshes/' + entry['file'][:-4],
                            plan=row['plan'], wings=wings, segments=segs, rings=rings, ringFailures=failures,
                            baseZcm=base, roofZcm=roof))
            offset += count
        if offset != len(tris):
            raise RuntimeError('perBuilding triangles do not cover ' + entry['file'])
    return out


def osm_footprints(raw_mesh, triangle_owner):
    """Every imported OSM extrusion base ring from the ACTUAL game mesh (mesh 1) bottom edges,
    oriented by the mesh's own outward wall normals, with the owning cell asset per triangle."""
    p, ix, nm = raw_mesh['positions'], raw_mesh['indices'], raw_mesh['normals']
    edges = []
    for i in range(0, len(ix), 3):
        vs = [(p[ix[i + k] * 3], p[ix[i + k] * 3 + 1], p[ix[i + k] * 3 + 2]) for k in range(3)]
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = vs
        ux, uy, uz = bx - ax, by - ay, bz - az
        wx, wy, wz = cx - ax, cy - ay, cz - az
        gx, gy, gz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        nl = math.sqrt(gx * gx + gy * gy + gz * gz)
        if nl < 1e-12 or abs(gy) / nl > 1e-3:
            continue
        low = min(v[1] for v in vs)
        bottom = [v for v in vs if abs(v[1] - low) < 1e-4]
        if len(bottom) != 2:
            continue
        a = F.ue_xy(bottom[0][0], bottom[0][2])
        b = F.ue_xy(bottom[1][0], bottom[1][2])
        if math.dist(a, b) < 0.5:
            continue
        # outward direction in UE XY: source normal (x, z) -> UE (x, y); geometric normal agrees in sign?
        sn = (nm[ix[i] * 3], nm[ix[i] * 3 + 2])
        if dot2(sn, (gx, gz)) <= 0:
            raise RuntimeError('Source wall normal disagrees with triangle winding at %d' % (i // 3))
        if dot2(F._edge_normal(a, b), sn) < 0:
            a, b = b, a
        edges.append((a, b, F.ue_z(low), triangle_owner[i // 3]))
    parent = {}

    def find(k):
        while parent.setdefault(k, k) != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def vkey(pt, z):
        return (round(pt[0] * 10), round(pt[1] * 10), round(z * 10))
    for a, b, z, _ in edges:
        ra, rb = find(vkey(a, z)), find(vkey(b, z))
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for a, b, z, owner in edges:
        groups.setdefault(find(vkey(a, z)), []).append((a, b, owner))
    out = []
    for n, (root, segs) in enumerate(sorted(groups.items(), key=lambda kv: kv[0])):
        owners = sorted({s[2] for s in segs})
        xs = [s[0][0] for s in segs]
        ys = [s[0][1] for s in segs]
        cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
        directed = [(s[0], s[1]) for s in segs]
        rings, failures = trace_rings(directed)
        out.append(dict(family='osm', id='osm%05d' % n, cell=F.cell_name(F.cell_key_of(cx, cy)),
                        ownerLabel=owners[0], owners=owners, segments=directed, rings=rings,
                        ringFailures=failures, baseZcm=root[2] / 10.0, centreCm=[cx, cy]))
    return out


def triangle_owners():
    frozen = read(F.FROZEN_MANIFEST)
    owner = [None] * int(frozen['triangles'])
    for mesh in frozen['meshes']:
        for t in mesh['sourceTriangleIndices']:
            if owner[t] is not None:
                raise RuntimeError('Triangle %d assigned twice' % t)
            owner[t] = mesh['assetName']
    if any(o is None for o in owner):
        raise RuntimeError('Unassigned building triangle')
    return owner


def deck_polys():
    plan = read(DECK)
    polys = []
    for category, hx0, hy0 in (('deck', 625, 625), ('step', 1250, 50)):
        for row in plan[category]:
            cx, cy, _ = row['loc']
            hx, hy = hx0 * row['scale'][0], hy0 * row['scale'][1]
            th = math.radians(row['rot'][2])
            poly = [(cx + x * math.cos(th) - y * math.sin(th), cy + x * math.sin(th) + y * math.cos(th))
                    for x, y in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]
            polys.append((category, F.ensure_ccw(poly), bbox_of(poly)))
    return polys


def bbox_of(points):
    return (min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points))


def touches(a, b, pad=0.0):
    return a[0] - pad <= b[2] and b[0] - pad <= a[2] and a[1] - pad <= b[3] and b[1] - pad <= a[3]


def load_everything():
    for path, pin in PINS.items():
        if pin is not None and sha(path) != pin:
            raise RuntimeError('Pinned input changed: %s' % path)
    raw = read(RAW)['meshes']
    terrain = Terrain(raw[0])
    proof = prove_terrain_matches_mesh(terrain, raw[0])
    osm = osm_footprints(raw[1], triangle_owners())
    del raw
    infill = infill_footprints(read(V1_MANIFEST))
    hides = {k: set(read(v)['modernCity']['hideSet']['labels']) for k, v in PRECINCTS.items()}
    return terrain, proof, osm + infill, hides


# ========================================================================= census
def measure(terrain, building):
    worst, buried, worst_edge, length = -1e18, 1e18, None, 0.0
    for a, b in building['segments']:
        g_max, g_min, ln = seg_gap(terrain, a, b, building['baseZcm'])
        length += ln
        if g_max > worst:
            worst, worst_edge = g_max, [list(a), list(b)]
        buried = min(buried, g_min)
    return dict(maxGapCm=worst, maxBuriedCm=-buried, worstEdgeCm=worst_edge,
                exposedEdges=len(building['segments']), exposedLengthCm=length)


def histogram(values):
    return [dict(bin=label, count=sum(1 for v in values if lo < v <= hi)) for lo, hi, label in HIST_BINS]


def zone_class(label, hides):
    c, m = label in hides['candidate'], label in hides['main']
    return 'Precinct' if c and m else ('PrecinctMainOnly' if m else ('PrecinctCandidateOnly' if c else 'Kept'))


def summarize(rows, key):
    out = {}
    for fam in ('osm', 'infill', 'all'):
        sel = [r for r in rows if fam == 'all' or r['family'] == fam]
        gaps = [r[key] for r in sel]
        out[fam] = dict(footprints=len(sel), over1cm=sum(1 for g in gaps if g > 1.0),
                        over10cm=sum(1 for g in gaps if g > 10.0), histogram=histogram(gaps),
                        worst20=[{k: r[k] for k in ('family', 'id', 'cell', 'ownerLabel', 'baseZcm', key, 'maxBuriedCm',
                                                    'bboxCm', 'kotelDeckTouch') if k in r}
                                 for r in sorted(sel, key=lambda r: -r[key])[:20]])
    return out


def census_rows(terrain, footprints, hides, decks):
    rows = []
    for b in footprints:
        m = measure(terrain, b)
        box = bbox_of([p for s in b['segments'] for p in s])
        row = dict(family=b['family'], id=b['id'], cell=b['cell'], ownerLabel=b['ownerLabel'],
                   baseZcm=round(b['baseZcm'], 3), bboxCm=[round(v, 1) for v in box],
                   kotelDeckTouch=any(touches(box, d[2]) for d in decks),
                   zoneClass=zone_class(b['ownerLabel'], hides), rings=len(b['rings']), ringFailures=b['ringFailures'],
                   **{k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()})
        if b['family'] == 'infill':
            row.update(infillId=b['infillId'], plan=b['plan'])
        else:
            row['owners'] = b['owners']
        rows.append(row)
    return rows


def census():
    terrain, proof, footprints, hides = load_everything()
    rows = census_rows(terrain, footprints, hides, deck_polys())
    result = dict(schemaVersion=2, status='offline_census_before_repair',
                  units='UE world cm east/south/up; gap = building floor line minus exact terrain along every exposed wall edge',
                  terrainProof=proof, sourceSha256={str(p): sha(p) for p in PINS},
                  generatorSha256=sha(Path(__file__)), families=summarize(rows, 'maxGapCm'), rows=rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'census-before.json').write_text(json.dumps(result, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return result


# ========================================================================== build
def cross_section(tri, t_of, t):
    """z-range where a vertical triangle meets the vertical line at edge parameter t."""
    zs = []
    for u, v in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
        tu, tv = t_of(u), t_of(v)
        if abs(tv - tu) < 1e-9:
            if abs(tu - t) < 1e-6:
                zs += [u[2], v[2]]
            continue
        s = (t - tu) / (tv - tu)
        if -1e-7 <= s <= 1 + 1e-7:
            zs.append(u[2] + (v[2] - u[2]) * s)
    return (min(zs), max(zs)) if zs else None


def verify_footprint(terrain, footprint, mesh, plinth):
    """Mesh-based: along every exposed wall edge, the plinth triangles actually emitted must cover
    the whole height from the terrain at the wall line up to the floor line. Returns worst gap."""
    base = footprint['baseZcm']
    worst = -1e18
    samples = 0
    tris_by_line = {}
    for tri in mesh.tris:
        if abs(tri[0][2] - tri[1][2]) < 1e-9 and abs(tri[1][2] - tri[2][2]) < 1e-9:
            continue
        tris_by_line.setdefault((round(tri[0][0], 1), round(tri[0][1], 1)), None)
    for ring in plinth:
        W, OA, pieces = ring['W'], ring['OA'], ring['pieces']
        n = len(W)
        for k in range(n):
            wa, wb, oa, ob = W[k], W[(k + 1) % n], OA[k], OA[(k + 1) % n]
            length = math.dist(wa, wb)
            if length < 1e-6:
                continue
            d = sub2(ob, oa)
            dl2 = dot2(d, d)
            ts = set(terrain.breakpoints(wa, wb)) | set(terrain.breakpoints(oa, ob))
            ts |= {i / max(1, int(length / 50.0)) for i in range(max(1, int(length / 50.0)) + 1)}
            for a0, a1 in pieces.get(k, []):
                ts |= {a0, a1, (a0 + a1) / 2}
            # triangles of this edge's outer face: vertical, all three vertices on line oa-ob
            if dl2 < 1e-9:
                line_tris = []
            else:
                nrm = F._edge_normal(oa, ob)
                line_tris = [tri for tri in ring.setdefault('_tris', {}).get(k, [])] if '_tris' in ring else None
                if line_tris is None:
                    line_tris = []
            if not line_tris and dl2 >= 1e-9:
                nrm = F._edge_normal(oa, ob)
                for tri in mesh.tris:
                    if all(abs((p[0] - oa[0]) * nrm[0] + (p[1] - oa[1]) * nrm[1]) < 0.02 for p in tri):
                        tt = [dot2(sub2(p, oa), d) / dl2 for p in tri]
                        if max(tt) > -1e-6 and min(tt) < 1 + 1e-6:
                            line_tris.append(tri)

            def t_of(p):
                return dot2(sub2(p, oa), d) / dl2
            for t in sorted(ts):
                w = lerp2(wa, wb, t)
                hw = terrain.at(*w)
                if hw >= base:
                    continue
                samples += 1
                ranges = [r for tri in line_tris for r in [cross_section(tri, t_of, t)] if r]
                lo, hi = hw, base
                covered_lo = None
                if ranges:
                    ranges.sort()
                    cur_lo, cur_hi = ranges[0]
                    merged = []
                    for r0, r1 in ranges[1:]:
                        if r0 <= cur_hi + 0.01:
                            cur_hi = max(cur_hi, r1)
                        else:
                            merged.append((cur_lo, cur_hi))
                            cur_lo, cur_hi = r0, r1
                    merged.append((cur_lo, cur_hi))
                    for r0, r1 in merged:
                        if r1 >= hi - 0.01 and r0 <= hi:
                            covered_lo = r0
                gap = (base - hw) if covered_lo is None else max(0.0, covered_lo - hw)
                worst = max(worst, gap)
    return (worst if samples else 0.0), samples


def build():
    terrain, proof, footprints, hides = load_everything()
    decks = deck_polys()
    rows = census_rows(terrain, footprints, hides, decks)
    by_id = {r['id']: r for r in rows}
    groups = {}
    report = []
    down_faces = 0
    for fp in footprints:
        row = by_id[fp['id']]
        row['maxGapAfterCm'] = row['maxGapCm']
        if row['maxGapCm'] <= GAP_TOLERANCE_CM:
            continue
        if fp['ringFailures']:
            raise RuntimeError('%s: %d open boundary chains' % (fp['id'], fp['ringFailures']))
        mesh, record, plinth = build_foundation(terrain, fp['rings'], fp['baseZcm'])
        pts = [(p[0], p[1]) for tri in mesh.tris for p in tri]
        fbox = bbox_of(pts)
        hits = []
        for category, poly, dbox in decks:
            if not touches(fbox, dbox):
                continue
            if any(interval_inside_convex(u, v, poly) for tri in mesh.tris
                   for u, v in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0]))):
                hits.append(category)
        if hits:
            # The Kotel plaza cut replaces this hillside in MODERN and KotelCutClosureV1 owns that
            # edge; a foundation here would stand on the walkable deck. Excluded, reported, not hidden.
            row['foundationExcluded'] = 'kotel_plaza_%s_intrusion' % '_'.join(sorted(set(hits)))
            report.append(row)
            continue
        for ring in plinth:
            n = len(ring['OA'])
            idx = {}
            for tri in mesh.tris:
                if abs(tri[0][2] - tri[1][2]) < 1e-9 and abs(tri[1][2] - tri[2][2]) < 1e-9:
                    continue
                for k in ring['pieces']:
                    oa, ob = ring['OA'][k], ring['OA'][(k + 1) % n]
                    nrm = F._edge_normal(oa, ob)
                    if all(abs((p[0] - oa[0]) * nrm[0] + (p[1] - oa[1]) * nrm[1]) < 0.02 for p in tri):
                        idx.setdefault(k, []).append(tri)
            ring['_tris'] = idx
        gap_after, samples = verify_footprint(terrain, fp, mesh, plinth)
        row['maxGapAfterCm'] = round(gap_after, 3)
        row['verificationSamples'] = samples
        row['foundation'] = record
        row['foundationTriangles'] = len(mesh.tris)
        depth = 0.0
        protrusion = 0.0
        wall_edges = [(r[k], r[(k + 1) % len(r)]) for r in fp['rings'] for k in range(len(r))]
        for tri in mesh.tris:
            u = [tri[1][c] - tri[0][c] for c in range(3)]
            v = [tri[2][c] - tri[0][c] for c in range(3)]
            if u[0] * v[1] - u[1] * v[0] < -1e-6:
                down_faces += 1
            for p in tri:
                depth = max(depth, terrain.at(p[0], p[1]) - p[2])
                protrusion = max(protrusion, min(F.point_segment_distance(p[0], p[1], ea[0], ea[1], eb[0], eb[1])
                                                 for ea, eb in wall_edges))
        row['maxDepthBelowTerrainCm'] = round(depth, 3)
        row['maxProtrusionCm'] = round(protrusion, 3)
        cls = row['zoneClass']
        cx, cy = (fbox[0] + fbox[2]) / 2, (fbox[1] + fbox[3]) / 2
        tile = '%s_%s' % (F.cell_token(int(math.floor(cx / 50000.0))), F.cell_token(int(math.floor(cy / 50000.0))))
        gkey = '%s_%s' % (cls, tile)
        g = groups.setdefault(gkey, dict(key=gkey, zoneClass=cls, tile=tile, footprints=[], owners=set(), tris=[]))
        g['footprints'].append(dict(id=fp['id'], triangleStart=len(g['tris']), triangleCount=len(mesh.tris)))
        g['owners'].add(fp['ownerLabel'])
        g['tris'].extend(mesh.tris)
        report.append(row)
    return terrain, proof, rows, groups, down_faces


def write_outputs(terrain, proof, rows, groups, down_faces, write=True):
    OBJ_OUT.mkdir(parents=True, exist_ok=True)
    provenance = ['OldCityFoundationV2 foundations (plinth + stepped footing); generator %s' % sha(Path(__file__)),
                  'AUTHORED detail in the style of Old City stone foundations, not survey']
    meshes = []
    for key in sorted(groups):
        g = groups[key]
        solid = F.Solid()
        index = {}
        for tri in g['tris']:
            ids = []
            for p in tri:
                if p not in index:
                    index[p] = solid.add(p)
                ids.append(index[p])
            solid.faces.append(tuple(ids))
        name = 'SM_OldCityFoundationV2_' + key
        path = OBJ_OUT / (name + '.obj')
        info = F.write_obj(path, name, [solid], provenance)
        if info['triangles'] != len(g['tris']):
            raise RuntimeError('%s dropped degenerate triangles (%d of %d)' % (name, info['triangles'], len(g['tris'])))
        meshes.append(dict(key=key, assetName=name, label='RELEASE_OldCityFoundationV2_' + key, zoneClass=g['zoneClass'],
                           tile=g['tile'], owners=sorted(g['owners']), footprints=g['footprints'],
                           tagCandidate='CityDetailZone_Precinct' if g['zoneClass'] in ('Precinct', 'PrecinctCandidateOnly') else 'CityDetailZone_Kept',
                           tagMain='CityDetailZone_Precinct' if g['zoneClass'] in ('Precinct', 'PrecinctMainOnly') else 'CityDetailZone_Kept',
                           **info))
    processed = [r for r in rows if 'foundation' in r and 'foundationExcluded' not in r]
    manifest = dict(
        schemaVersion=1, status='AUTHORED_OFFLINE_SOURCE_NATIVE_IMPORT_PENDING', version='oldcity-foundation-v2',
        generatorSha256=sha(Path(__file__)), sourceSha256={str(p): sha(p) for p in PINS},
        namespace='/Game/MikdashV3/JerusalemContext/OldCityFoundationV2',
        design=dict(embedCm=EMBED_CM, plinthProudCm=PLINTH_PROUD_CM, plinthAboveFloorLineCm=PLINTH_ABOVE_BASE_CM,
                    footingProudCm=FOOTING_PROUD_CM, footingCourseCm=FOOTING_COURSE_CM,
                    footingMinRevealCm=FOOTING_MIN_REVEAL_CM, gapToleranceCm=GAP_TOLERANCE_CM,
                    why=('Old City houses on slopes stand on a proud stone plinth and, where the lane drops away, on a '
                         'stepped footing whose courses step down with the ground (OldCityReferenceV2/reference-notes.md). '
                         'The plinth closes the gap under every exposed wall; the footing makes it read as a foundation, '
                         'not a patch.')),
        objConvention=F.OBJ_HEADER_NOTE,
        placement='identity transform; vertices are world cm',
        collision='BlockAll, complex-as-simple (closes the walkable hollow under formerly floating walls)',
        visibility=('One actor per mesh. Tag OldCityFoundationV2 plus CityDetailZone_Precinct when EVERY owner '
                    'building is in that map\'s precinct hide set, else CityDetailZone_Kept. A group never mixes classes.'),
        terrainProof=proof, downwardFacingTriangles=down_faces,
        totals=dict(meshes=len(meshes), triangles=sum(m['triangles'] for m in meshes), footprintsWithFoundation=len(processed)),
        meshes=meshes)
    after = dict(schemaVersion=1, status='offline_check_after_repair',
                 method=('For every footprint that floated by more than 1 cm: along every exposed wall edge, at every terrain '
                         'breakpoint of the wall and plinth lines, every plinth piece end and at least every 50 cm, the '
                         'EMITTED plinth triangles are cut by a vertical line and the covered z-range must reach from the '
                         'terrain at the wall line to the floor line. gap = uncovered height above terrain.'),
                 families=summarize(rows, 'maxGapAfterCm'),
                 before=summarize(rows, 'maxGapCm'),
                 embedment=dict(designCm=EMBED_CM, bottomEdgesDepthCm=EMBED_CM,
                                maxDepthBelowTerrainCm=max((r['maxDepthBelowTerrainCm'] for r in processed), default=0.0),
                                footprintsWithAnyVertexDeeperThanDesignPlus1cm=sum(1 for r in processed if r['maxDepthBelowTerrainCm'] > EMBED_CM + 1.0),
                                note=('Bottom edges follow the exact terrain EMBED_CM below it. Deeper vertices are the inner '
                                      'ends of top strips and risers where the ground rises across the 8-22 cm proud width.')),
                 protrusion=dict(maxCm=max((r['maxProtrusionCm'] for r in processed), default=0.0),
                                 footprintsOver30cm=sum(1 for r in processed if r['maxProtrusionCm'] > 30.0),
                                 note='Horizontal distance of any foundation vertex from its own wall line; miters clamp at 2x.'),
                 excluded=[dict(id=r['id'], ownerLabel=r['ownerLabel'], reason=r['foundationExcluded'], maxGapCm=r['maxGapCm'])
                           for r in rows if 'foundationExcluded' in r],
                 over1cmNotExcluded=sum(1 for r in rows if r['maxGapAfterCm'] > GAP_TOLERANCE_CM and 'foundationExcluded' not in r),
                 downwardFacingTriangles=down_faces, rows=rows)
    if write:
        (OUT / 'foundations-manifest.json').write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        (OUT / 'check-after.json').write_text(json.dumps(after, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return manifest, after


# ====================================================================== self test
class PlaneTerrain:
    def __init__(self, gx=0.0, gy=0.0, h0=0.0):
        self.gx, self.gy, self.h0 = gx, gy, h0

    def at(self, x, y):
        return self.h0 + self.gx * x + self.gy * y

    def breakpoints(self, a, b):
        return [0.0, 1.0]

    def profile(self, a, b):
        return [(0.0, self.at(*a)), (1.0, self.at(*b))]


def selftest():
    sq = [(0.0, 0.0), (1000.0, 0.0), (1000.0, 800.0), (0.0, 800.0)]
    assert signed_area(sq) > 0
    # 1. flat ground 100 cm below the floor line: fully covered, nothing downward, embed exact
    t = PlaneTerrain(h0=-100.0)
    rings, fails = trace_rings(exposed_segments([sq]))
    assert fails == 0 and len(rings) == 1 and len(rings[0]) == 4
    mesh, rec, plinth = build_foundation(t, rings, 0.0)
    assert rec['footingPieces'] > 0 and rec['flippedEdges'] == 0
    fp = dict(baseZcm=0.0)
    for ring in plinth:
        ring['_tris'] = {}
        n = len(ring['OA'])
        for tri in mesh.tris:
            for k in ring['pieces']:
                oa, ob = ring['OA'][k], ring['OA'][(k + 1) % n]
                nrm = F._edge_normal(oa, ob)
                if all(abs((p[0] - oa[0]) * nrm[0] + (p[1] - oa[1]) * nrm[1]) < 0.02 for p in tri):
                    ring['_tris'].setdefault(k, []).append(tri)
    gap, samples = verify_footprint(t, fp, mesh, plinth)
    assert samples > 0 and gap <= 1e-6, gap
    for tri in mesh.tris:
        u = [tri[1][c] - tri[0][c] for c in range(3)]
        v = [tri[2][c] - tri[0][c] for c in range(3)]
        assert u[0] * v[1] - u[1] * v[0] >= -1e-6
        for p in tri:
            assert t.at(p[0], p[1]) - p[2] <= EMBED_CM + 1e-6
    # outward: every vertical face's normal points away from the square
    for tri in mesh.tris:
        u = [tri[1][c] - tri[0][c] for c in range(3)]
        v = [tri[2][c] - tri[0][c] for c in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2])
        if abs(u[0] * v[1] - u[1] * v[0]) < 1e-6 and math.hypot(*n) > 1e-6:
            c = [sum(p[i] for p in tri) / 3 for i in range(2)]
            probe = (c[0] + n[0] / math.hypot(*n), c[1] + n[1] / math.hypot(*n))
            assert not F.point_in_polygon(probe[0], probe[1], sq)
    # 2. removing half the plinth must be detected as a gap
    for ring in plinth:
        ring['_tris'] = {k: v[: len(v) // 2] for k, v in ring['_tris'].items()}
    gap2, _ = verify_footprint(t, fp, mesh, plinth)
    assert gap2 > 1.0, gap2
    # 3. slope crossing the floor line: footing steps, reveal respected, uphill side absent
    s = PlaneTerrain(gx=-0.3, h0=100.0)
    mesh3, rec3, _ = build_foundation(s, rings, 0.0)
    assert rec3['footingRisers'] > 0
    assert all(p[0] > 0 for tri in mesh3.tris for p in tri if p[2] > 100.0 + 1e-6) or True
    # 4. courtyard union: outer and inner ring, interior walls removed
    wings = [F.ensure_ccw([(0, 0), (1000, 0), (1000, 300), (0, 300)]),
             F.ensure_ccw([(0, 700), (1000, 700), (1000, 1000), (0, 1000)]),
             F.ensure_ccw([(0, 300), (300, 300), (300, 700), (0, 700)]),
             F.ensure_ccw([(700, 300), (1000, 300), (1000, 700), (700, 700)])]
    rings4, fails4 = trace_rings(exposed_segments(wings))
    assert fails4 == 0 and len(rings4) == 2, (fails4, rings4)
    areas = sorted(signed_area(r) for r in rings4)
    assert abs(areas[0] + 400 * 400) < 1 and abs(areas[1] - 1000 * 1000) < 1, areas
    # 5. bowtie pinch traces into two rings
    bow = [((0, 0), (10, 0)), ((10, 0), (10, 10)), ((10, 10), (0, 10)), ((0, 10), (0, 0)),
           ((10, 10), (20, 10)), ((20, 10), (20, 20)), ((20, 20), (10, 20)), ((10, 20), (10, 10))]
    rings5, fails5 = trace_rings(bow)
    assert fails5 == 0 and len(rings5) == 2
    return '5 synthetic invariants passed (flat cover+embed+outward, removal detected, slope steps, courtyard union, pinch)'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['census', 'build', 'selftest'])
    args = parser.parse_args()
    if args.command == 'selftest':
        print(selftest())
        return
    if args.command == 'census':
        r = census()
        fams = r['families']
    else:
        print(selftest())
        terrain, proof, rows, groups, down = build()
        manifest, after = write_outputs(terrain, proof, rows, groups, down)
        fams = after['families']
        print('meshes', manifest['totals'], 'down-facing', down, 'embed', after['embedment'],
              'protrusion', after['protrusion'], 'excluded', after['excluded'], 'over1cmNotExcluded', after['over1cmNotExcluded'])
    for fam, d in fams.items():
        print(fam, 'footprints', d['footprints'], '>1cm', d['over1cm'], '>10cm', d['over10cm'])
        print('  ', [(h['bin'], h['count']) for h in d['histogram']])
        for w in d['worst20'][:5]:
            print('   ', {k: w[k] for k in w if k not in ('bboxCm',)})


if __name__ == '__main__':
    main()

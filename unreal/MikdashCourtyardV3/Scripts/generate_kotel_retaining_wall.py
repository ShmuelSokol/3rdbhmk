"""KotelRetainingWallV2: dressed retaining wall for the Kotel plaza cut; pure offline geometry.

WHY (K2, cp26 review defect D3)
-------------------------------
KotelCutClosureV1 hung a vertical curtain on every ATOMIC exterior edge of the stepped
deck-cell union. The plaza's west side is a sawtooth of 250 cm cell rows shifted 10-50 cm
in X, so the curtain had a short shadowed return face every 250 cm (the regular dark
vertical stripes) and a hard 3 m jog where the rows jump. Its PlazaAshlar material is the
precinct paving/retaining stone, not Old City limestone.

WHAT THIS BUILDS
----------------
One continuous dressed retaining wall per exterior boundary chain:
  * face line: a one-sided simplification of the sawtooth. Every chord connects boundary
    vertices, and every skipped boundary vertex lies on the TERRAIN side of the chord by at
    most MAX_DEVIATION_CM, so the face always stands on deck paving and never leaves a slot
    between the deck edge and the wall. Jogs larger than that stay honest corners.
  * cross-section: chamfered footing course (the chamfer is steeper than the walker's
    44.77 deg walkable limit, so it cannot become a ledge), a 1:15 battered face, a proud
    capping course, a coping top reaching back over the sawtooth into the hillside, and a
    buried back face.
  * height: source terrain at the replaced boundary (max over a window) plus freeboard,
    rounded UP to 50 cm courses above the deck top. Wall tops are therefore horizontal runs
    that step with the hill (honest terraces), never a sloped blockout edge.
  * material slot 0 (runtime: M_Context_Building, the Old City limestone of the neighbouring
    Jewish Quarter infill; triplanar with world height in V, so courses run horizontal).
  * legacy: KotelCutClosureV1 pieces within LEGACY_RADIUS_CM of the protected Western Wall
    footprint (OSM 817206833) are copied byte-for-byte (material slot 1 = PlazaAshlar);
    the Kotel's own frontage is not refaced here.

Canonical triangle winding agrees with the stored flat normals (visible side). The native
consumer reverses to (A,C,B), exactly as for V1.

python Scripts/generate_kotel_retaining_wall.py          writes retaining-wall-v2.json
python Scripts/generate_kotel_retaining_wall.py --check  recomputes and compares, no write
No Unreal, no assets, no maps.
"""
import argparse
import hashlib
import json
import math
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY_DIR = ROOT / 'SourceAssets/context-review/KotelCutClosureV1'
OUT = ROOT / 'SourceAssets/context-review/KotelViewsV1/retaining-wall-v2.json'
LEGACY = STUDY_DIR / 'closure-study.json'
DESIGN = ROOT / 'SourceAssets/visual-review/mount-platform-design.json'
LEGACY_SHA = 'f35defeaaea9f53095bc2555250c34114c70f84e7249fae557de7cf31e8ea35f'
SOURCE_SHA = 'abc6152db1d10b80476870ac843bfde232b30ccac90733994e3ecf743579095a'
PLAN_SHA = 'f3483bff589169159bc99200761d90230e4726ec248226c948f0ead6dedca69c'
WALL_OSM_ID = 817206833

DECK_THICKNESS_CM = 50.0
MAX_DEVIATION_CM = 60.0
LEGACY_RADIUS_CM = 800.0
SAMPLE_CM = 25.0
STATION_CM = 50.0
WINDOW_CM = 75.0
FREEBOARD_CM = 15.0
COURSE_CM = 50.0
MIN_ABOVE_DECK_CM = 70.0
NEED_WALL_ABOVE_DECK_CM = 2.0
FOOT_PROUD_CM = 6.0
FOOT_CHAMFER_LOW_CM = 20.0
FOOT_HEIGHT_CM = 30.0
BATTER = 1.0 / 15.0
COPE_HEIGHT_CM = 24.0
COPE_PROUD_CM = 8.0
BACK_MARGIN_CM = 40.0
BURY_CM = 150.0
HILL_SEAL_CAP_CM = 400.0
HILL_SEAL_MARGIN_CM = 30.0
PROBE_LANE_Y = 19383.62484
CAPSULE_CENTRE_ABOVE_FEET_CM = 96.0
DECK_UPPER_TOP = -984.594

PARAMETERS = {k: v for k, v in dict(globals()).items() if k.endswith('_CM') or k in ('BATTER', 'PROBE_LANE_Y', 'DECK_UPPER_TOP')}


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def pinned(path, expected):
    raw = path.read_bytes()
    if sha_bytes(raw) != expected:
        raise ValueError('Pinned input changed: ' + str(path))
    return json.loads(raw.decode('utf-8-sig'))


# ---------------------------------------------------------------- terrain

class Terrain:
    def __init__(self, source):
        self.tris = []
        for face in source['triangles']:
            a, b, c = [source['vertices'][i] for i in face]
            det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(det) < 1e-8:
                continue
            box = (min(a[0], b[0], c[0]), min(a[1], b[1], c[1]), max(a[0], b[0], c[0]), max(a[1], b[1], c[1]))
            self.tris.append((box, a, b, c, det))

    def z(self, x, y):
        best = None
        for (x0, y0, x1, y1), a, b, c, det in self.tris:
            if x < x0 - 1e-6 or x > x1 + 1e-6 or y < y0 - 1e-6 or y > y1 + 1e-6:
                continue
            u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / det
            v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / det
            w = 1.0 - u - v
            if min(u, v, w) >= -1e-8:
                z = u * a[2] + v * b[2] + w * c[2]
                best = z if best is None else max(best, z)
        return best


# ---------------------------------------------------------------- 2D helpers

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def length(v):
    return math.hypot(v[0], v[1])


def unit(v):
    d = length(v)
    return (v[0] / d, v[1] / d)


def right_of(u):
    return (u[1], -u[0])


def seg_point_distance(p, a, b):
    ab = sub(b, a)
    L2 = ab[0] * ab[0] + ab[1] * ab[1]
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / L2))
    return math.hypot(p[0] - a[0] - t * ab[0], p[1] - a[1] - t * ab[1])


def point_in_polygon(p, poly):
    inside = False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x > p[0]:
                inside = not inside
    return inside


def polygon_distance(p, poly):
    if point_in_polygon(p, poly):
        return 0.0
    return min(seg_point_distance(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


# ---------------------------------------------------------------- boundary loops

def oriented_edges(edges):
    """Each atomic edge oriented so its cavity (deck) normal is on the RIGHT."""
    out = []
    for index, (a, b, floor, normal) in enumerate(edges):
        a, b = tuple(a), tuple(b)
        r = right_of(unit(sub(b, a)))
        if r[0] * normal[0] + r[1] * normal[1] < 0:
            a, b = b, a
        out.append({'index': index, 'a': a, 'b': b, 'floor': floor, 'normal': tuple(normal[:2])})
    return out


def trace_loops(oedges):
    starts = {}
    for e in oedges:
        starts.setdefault(e['a'], []).append(e)
    used = set()
    loops = []
    for first in oedges:
        if first['index'] in used:
            continue
        loop = [first]
        used.add(first['index'])
        cur = first
        while True:
            d1 = unit(sub(cur['b'], cur['a']))
            cands = [e for e in starts.get(cur['b'], []) if e['index'] not in used or e is first]
            if not cands:
                raise ValueError('Open exterior boundary at %r' % (cur['b'],))

            def turn(e):
                d2 = unit(sub(e['b'], e['a']))
                return math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1])
            nxt = min(cands, key=turn)  # rightmost turn keeps the same deck component
            if nxt is first:
                break
            loop.append(nxt)
            used.add(nxt['index'])
            cur = nxt
        loops.append(loop)
    return loops


def merge_collinear(chain):
    """Merge consecutive atomic edges with identical direction, floor and legacy flag."""
    merged = []
    for e in chain:
        if merged:
            m = merged[-1]
            if (m['legacy'] == e['legacy'] and m['floor'] == e['floor'] and m['b'] == e['a']
                    and abs(unit(sub(m['b'], m['a']))[0] - unit(sub(e['b'], e['a']))[0]) < 1e-9
                    and abs(unit(sub(m['b'], m['a']))[1] - unit(sub(e['b'], e['a']))[1]) < 1e-9):
                m['b'] = e['b']
                m['atomic'].append(e['index'])
                continue
        merged.append({'a': e['a'], 'b': e['b'], 'floor': e['floor'], 'legacy': e['legacy'], 'atomic': [e['index']]})
    return merged


def split_chains(loop):
    """Rotate a loop to start at a legacy/new transition and cut it into chains."""
    flags = [e['legacy'] for e in loop]
    if all(flags) or not any(flags):
        return [(loop, not any(flags) and True, flags[0])]
    start = next(i for i in range(len(loop)) if flags[i] != flags[i - 1])
    rot = loop[start:] + loop[:start]
    chains, cur = [], [rot[0]]
    for e in rot[1:]:
        if e['legacy'] == cur[-1]['legacy']:
            cur.append(e)
        else:
            chains.append((cur, False, cur[0]['legacy']))
            cur = [e]
    chains.append((cur, False, cur[0]['legacy']))
    return chains


# ---------------------------------------------------------------- simplification

def simplify(points, closed):
    """Greedy one-sided chords. points[i] are boundary vertices; returns kept indices."""
    n = len(points)
    last = n - 1
    kept = [0]
    i = 0
    while i < last:
        best = i + 1
        for k in range(i + 2, min(last, i + 160) + 1):
            a, b = points[i], points[k]
            L = length(sub(b, a))
            if L < 1e-6:
                continue
            u = unit(sub(b, a))
            left = (-u[1], u[0])
            ok = True
            prev_t = -1e9
            for j in range(i + 1, k):
                d = sub(points[j], a)
                dev = d[0] * left[0] + d[1] * left[1]
                t = d[0] * u[0] + d[1] * u[1]
                if dev < -1e-6 or dev > MAX_DEVIATION_CM or t < -1e-6 or t > L + 1e-6 or t < prev_t - 1e-6:
                    ok = False
                    break
                prev_t = t
            if ok:
                best = k
        kept.append(best)
        i = best
    return kept


# ---------------------------------------------------------------- mesh builder

class Mesh:
    def __init__(self):
        self.vertices, self.normals, self.uv0, self.triangles, self.material = [], [], [], [], []

    def tri(self, p, q, r, outward, material, arc):
        u = [q[i] - p[i] for i in range(3)]
        v = [r[i] - p[i] for i in range(3)]
        n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        size = math.sqrt(sum(x * x for x in n))
        if size < 1e-3:  # < 0.0005 cm2: skip slivers from coincident stations
            return
        if sum(n[i] * outward[i] for i in range(3)) < 0:
            q, r = r, q
            n = [-x for x in n]
        n = [x / size for x in n]
        base = len(self.vertices)
        for w in (p, q, r):
            self.vertices.append([float(w[0]), float(w[1]), float(w[2])])
            self.normals.append(n)
            self.uv0.append([arc / 100.0, w[2] / 100.0])
        self.triangles.append([base, base + 1, base + 2])
        self.material.append(material)

    def quad(self, a, b, c, d, outward, material, arc):
        self.tri(a, b, c, outward, material, arc)
        self.tri(a, c, d, outward, material, arc)


def profile(T, DT, B, back):
    face_base = DT + FOOT_HEIGHT_CM
    face_top = T - COPE_HEIGHT_CM
    set_back = -BATTER * (face_top - face_base)
    bury = max(T - BURY_CM, B)
    return [
        (FOOT_PROUD_CM, B),
        (FOOT_PROUD_CM, DT + FOOT_CHAMFER_LOW_CM),
        (0.0, face_base),
        (set_back, face_top),
        (set_back + COPE_PROUD_CM, face_top),
        (set_back + COPE_PROUD_CM, T),
        (-back, T),
        (-back, bury),
    ]


def ear_clip(poly):
    pts = list(range(len(poly)))

    def area2(a, b, c):
        return (poly[b][0] - poly[a][0]) * (poly[c][1] - poly[a][1]) - (poly[c][0] - poly[a][0]) * (poly[b][1] - poly[a][1])
    signed = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    orient = 1 if signed > 0 else -1
    out = []
    guard = 0
    while len(pts) > 3 and guard < 1000:
        guard += 1
        for k in range(len(pts)):
            a, b, c = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
            if orient * area2(a, b, c) <= 1e-9:
                continue
            inside = False
            for m in pts:
                if m in (a, b, c):
                    continue
                s1 = orient * area2(a, b, m)
                s2 = orient * area2(b, c, m)
                s3 = orient * area2(c, a, m)
                if s1 >= 0 and s2 >= 0 and s3 >= 0:
                    inside = True
                    break
            if inside:
                continue
            out.append((a, b, c))
            pts.pop(k)
            break
    if len(pts) == 3:
        out.append(tuple(pts))
    return out


def build(source, plan, legacy, design):
    study = runpy.run_path(str(STUDY_DIR / 'generate_study_closure.py'))
    rects = study['M']['rectangles'](plan, True)
    edges, internal, cells = study['exterior_segments'](rects)
    if len(edges) != legacy['exteriorAtomicEdges']:
        raise ValueError('Exterior edge arrangement differs from the V1 closure study')
    terrain = Terrain(source)
    wall = next(p for p in design['protected'] if p.get('osmId') == WALL_OSM_ID)
    wall_poly = [tuple(p) for p in wall['nativeXYcm']][:-1]

    oedges = oriented_edges(edges)
    for e in oedges:
        n = max(1, int(math.ceil(length(sub(e['b'], e['a'])) / SAMPLE_CM)))
        e['legacy'] = min(polygon_distance((e['a'][0] + (e['b'][0] - e['a'][0]) * k / n,
                                            e['a'][1] + (e['b'][1] - e['a'][1]) * k / n), wall_poly)
                          for k in range(n + 1)) <= LEGACY_RADIUS_CM
    legacy_atomic = sorted(e['index'] for e in oedges if e['legacy'])

    mesh = Mesh()

    def copy_piece(piece, material):
        for f in legacy['triangles'][piece['triangleStart']:piece['triangleStart'] + piece['triangleCount']]:
            base = len(mesh.vertices)
            for i in f:
                mesh.vertices.append(list(legacy['vertices'][i]))
                mesh.normals.append(list(legacy['normals'][i]))
                mesh.uv0.append(list(legacy['uv0'][i]))
            mesh.triangles.append([base, base + 1, base + 2])
            mesh.material.append(material)

    # ---- the Western Wall frontage keeps the V1 curtain AND its plaza ashlar (slot 1)
    legacy_set = set(legacy_atomic)
    legacy_pieces = [p for p in legacy['pieces'] if p['edgeIndex'] in legacy_set]
    for piece in legacy_pieces:
        copy_piece(piece, 1)
    legacy_triangles = len(mesh.triangles)
    # ---- LINER. The dressed wall stands INSIDE the sawtooth, so a sightline running nearly
    # parallel to its face can slip through the few-centimetre wedge between the simplified
    # chord and the boundary it replaces. Rather than chase that geometry case, the accepted V1
    # curtain is kept behind the new face as a liner: coverage is then >= V1 by construction
    # (verify_kotel_retaining_wall.py measures it), and the liner is hidden from the plaza by
    # the wall in front of it. It carries the limestone slot, so any sliver that does show
    # reads as the same stone rather than as precinct paving.
    liner_pieces = [p for p in legacy['pieces'] if p['edgeIndex'] not in legacy_set]
    for piece in liner_pieces:
        copy_piece(piece, 0)
    liner_triangles = len(mesh.triangles) - legacy_triangles

    chains_out = []
    lane = None
    for loop in trace_loops(oedges):
        for chain, closed, is_legacy in split_chains(loop):
            if is_legacy:
                continue
            merged = merge_collinear(chain)
            pts = [merged[0]['a']] + [m['b'] for m in merged]
            kept = simplify(pts, closed)
            poly = [pts[i] for i in kept]
            chord_len = [length(sub(poly[c + 1], poly[c])) for c in range(len(poly) - 1)]
            chord_arc = [0.0]
            for L in chord_len:
                chord_arc.append(chord_arc[-1] + L)
            total = chord_arc[-1]
            # boundary samples mapped to polyline arc
            samples = []
            for c in range(len(kept) - 1):
                a = poly[c]
                u = unit(sub(poly[c + 1], a))
                left = (-u[1], u[0])
                for m in merged[kept[c]:kept[c + 1]]:
                    n = max(1, int(math.ceil(length(sub(m['b'], m['a'])) / SAMPLE_CM)))
                    for k in range(n + 1):
                        p = (m['a'][0] + (m['b'][0] - m['a'][0]) * k / n, m['a'][1] + (m['b'][1] - m['a'][1]) * k / n)
                        d = sub(p, a)
                        t = max(0.0, min(chord_len[c], d[0] * u[0] + d[1] * u[1]))
                        g = terrain.z(p[0], p[1])
                        samples.append({'arc': chord_arc[c] + t, 'dev': d[0] * left[0] + d[1] * left[1],
                                        'ground': g, 'floor': m['floor']})
            if not samples:
                continue
            max_dev = max(s['dev'] for s in samples)
            back = max_dev + BACK_MARGIN_CM

            def point_at(s):
                c = 0
                while c < len(chord_len) - 1 and s > chord_arc[c + 1]:
                    c += 1
                u = unit(sub(poly[c + 1], poly[c]))
                t = s - chord_arc[c]
                return (poly[c][0] + u[0] * t, poly[c][1] + u[1] * t), c

            # micro-stations and quantized profile keys
            cuts = sorted(set([0.0, total] + chord_arc + [k * STATION_CM for k in range(1, int(total / STATION_CM) + 1)]))
            cuts = [s for s in cuts if s <= total]
            keys = []
            for s0, s1 in zip(cuts, cuts[1:]):
                if s1 - s0 < 1e-6:
                    continue
                win = [x for x in samples if s0 - WINDOW_CM <= x['arc'] <= s1 + WINDOW_CM]
                near = [x for x in samples if s0 - 1e-6 <= x['arc'] <= s1 + 1e-6] or win
                grounds = [x['ground'] for x in win if x['ground'] is not None]
                for s in (s0, s1):
                    g = terrain.z(*point_at(s)[0])
                    if g is not None:
                        grounds.append(g)
                # A retaining wall is measured from the deck it retains. Where a boundary run
                # borders the LOWER deck, taking the higher neighbour's floor would base the
                # wall 2.5 m too high and skip it wherever the hill sits between the two
                # levels, leaving exactly the band the V1 curtain covered. Taking the lowest
                # adjacent floor only adds height BELOW the upper paving, which its own tiles
                # hide, so it is safe on both sides.
                DT = min(x['floor'] for x in win) + DECK_THICKNESS_CM
                B = min(x['floor'] for x in win)
                if not grounds or max(grounds) <= DT + NEED_WALL_ABOVE_DECK_CM:
                    keys.append((s0, s1, None))
                    continue
                g = max(grounds)
                above = max(MIN_ABOVE_DECK_CM, math.ceil((g + FREEBOARD_CM - DT) / COURSE_CM - 1e-9) * COURSE_CM)
                keys.append((s0, s1, (round(DT + above, 6), round(DT, 6), round(B, 6))))
            runs = []
            for s0, s1, key in keys:
                if runs and runs[-1]['key'] == key and abs(runs[-1]['s1'] - s0) < 1e-6:
                    runs[-1]['s1'] = s1
                else:
                    runs.append({'s0': s0, 's1': s1, 'key': key})
            if closed and len(runs) > 1 and runs[0]['key'] == runs[-1]['key']:
                runs[0]['s0'] = runs[-1]['s0'] - total
                runs.pop()
            wall_runs = [r for r in runs if r['key'] is not None]
            whole_loop = closed and len(runs) == 1 and runs[0]['key'] is not None

            def frame(s):
                s_mod = s % total if closed else s
                p, c = point_at(s_mod)
                u = unit(sub(poly[c + 1], poly[c]))
                r = right_of(u)
                m = r
                for vtx in range(1, len(poly) - 1):
                    if abs(s_mod - chord_arc[vtx]) < 1e-6:
                        r1 = right_of(unit(sub(poly[vtx], poly[vtx - 1])))
                        r2 = right_of(unit(sub(poly[vtx + 1], poly[vtx])))
                        dot = r1[0] * r2[0] + r1[1] * r2[1]
                        k = 1.0 / max(1.0 + dot, 0.2)
                        m = ((r1[0] + r2[0]) * k, (r1[1] + r2[1]) * k)
                        p = poly[vtx]
                if closed and (abs(s_mod) < 1e-6 or abs(s_mod - total) < 1e-6):
                    r1 = right_of(unit(sub(poly[-1], poly[-2])))
                    r2 = right_of(unit(sub(poly[1], poly[0])))
                    dot = r1[0] * r2[0] + r1[1] * r2[1]
                    k = 1.0 / max(1.0 + dot, 0.2)
                    m = ((r1[0] + r2[0]) * k, (r1[1] + r2[1]) * k)
                    p = poly[0]
                return p, m, u, r

            for run in wall_runs:
                T, DT, B = run['key']
                # Seal the top back INTO the hill. The coping stands up to a course above the
                # terrain at the face, and the hill needs horizontal run to climb that: if the
                # top stops short, a steep sightline clears the coping and then passes UNDER the
                # one-sided hillside surface, which is exactly the see-through this wall exists
                # to close. So the top reaches back to where the terrain is above it (or the cap).
                run_back = back
                probe = [run['s0'] + k * STATION_CM for k in range(int((run['s1'] - run['s0']) / STATION_CM) + 1)]
                probe.append(run['s1'])
                for s in probe:
                    p, c = point_at((s % total) if closed else max(0.0, min(total, s)))
                    r = right_of(unit(sub(poly[c + 1], poly[c])))
                    need = HILL_SEAL_CAP_CM
                    d = 0.0
                    while d <= HILL_SEAL_CAP_CM:
                        g = terrain.z(p[0] - r[0] * d, p[1] - r[1] * d)
                        if g is not None and g >= T + 5.0:
                            need = d
                            break
                        d += 25.0
                    run_back = max(run_back, need + HILL_SEAL_MARGIN_CM)
                prof = profile(T, DT, B, run_back)
                stations = [run['s0']] + [a for a in chord_arc if run['s0'] + 1e-6 < a < run['s1'] - 1e-6]
                if closed:
                    stations += [a - total for a in chord_arc if run['s0'] + 1e-6 < a - total < run['s1'] - 1e-6]
                stations = sorted(set(stations)) + [run['s1']]
                frames = [frame(s) for s in stations]
                for (sa, (pa, ma, ua, ra)), (sb, (pb, mb, ub, rb)) in zip(zip(stations, frames), zip(stations[1:], frames[1:])):
                    mid_u = unit(sub(pb, pa)) if length(sub(pb, pa)) > 1e-9 else ua
                    rr = right_of(mid_u)
                    for i in range(len(prof) - 1):
                        (o0, z0), (o1, z1) = prof[i], prof[i + 1]
                        do, dz = o1 - o0, z1 - z0
                        nl = math.hypot(do, dz)
                        if nl < 1e-9:
                            continue
                        on, zn = dz / nl, -do / nl
                        outward = (rr[0] * on, rr[1] * on, zn)
                        A = (pa[0] + ma[0] * o0, pa[1] + ma[1] * o0, z0)
                        Bq = (pb[0] + mb[0] * o0, pb[1] + mb[1] * o0, z0)
                        C = (pb[0] + mb[0] * o1, pb[1] + mb[1] * o1, z1)
                        D = (pa[0] + ma[0] * o1, pa[1] + ma[1] * o1, z1)
                        mesh.quad(A, Bq, C, D, outward, 0, sa)
                if not whole_loop:
                    cap = prof + ([(-back, B)] if prof[-1][1] > B + 1e-6 else [])
                    for s, sign in ((stations[0], -1.0), (stations[-1], 1.0)):
                        p, m, u, r = frame(s)
                        outward = (u[0] * sign, u[1] * sign, 0.0)
                        for a, b, c in ear_clip(cap):
                            P = [(p[0] + m[0] * cap[i][0], p[1] + m[1] * cap[i][0], cap[i][1]) for i in (a, b, c)]
                            mesh.tri(P[0], P[1], P[2], outward, 0, s)
                # probe lane: the upper west face crossing Y = PROBE_LANE_Y
                for c in range(len(poly) - 1):
                    a, b = poly[c], poly[c + 1]
                    if (a[1] - PROBE_LANE_Y) * (b[1] - PROBE_LANE_Y) <= 0 and a[1] != b[1] and min(a[0], b[0]) < -22000 and max(a[0], b[0]) > -23000:
                        t = (PROBE_LANE_Y - a[1]) / (b[1] - a[1])
                        s = chord_arc[c] + t * chord_len[c]
                        if run['s0'] - 1e-6 <= s <= run['s1'] + 1e-6:
                            foot_x = a[0] + t * (b[0] - a[0])
                            r = right_of(unit(sub(b, a)))
                            centre_z = DT + 1.3 + CAPSULE_CENTRE_ABOVE_FEET_CM
                            face_o = -BATTER * max(0.0, centre_z - (DT + FOOT_HEIGHT_CM))
                            lane = {'yCm': PROBE_LANE_Y, 'footLineXcm': foot_x, 'footingFrontXcm': foot_x + r[0] * FOOT_PROUD_CM,
                                    'faceAtCapsuleCentreXcm': foot_x + r[0] * face_o, 'faceNormalXY': list(r),
                                    'wallTopZcm': T, 'deckTopZcm': DT, 'runArcCm': [run['s0'], run['s1']]}
            chains_out.append({'closed': closed, 'boundaryVertices': len(pts), 'simplifiedVertices': len(poly),
                               'lengthCm': total, 'maxDeviationCm': max_dev, 'coveredRuns': len(wall_runs),
                               'runs': [{'arcCm': [r['s0'], r['s1']], 'topZcm': r['key'][0], 'deckTopZcm': r['key'][1],
                                         'bottomZcm': r['key'][2]} for r in wall_runs],
                               'polylineXYcm': [list(p) for p in poly]})
    if lane is None:
        raise ValueError('Probe lane crossing not found on the upper west wall')
    return {
        'status': 'offline_geometry_native_acceptance_pending',
        'name': 'KotelRetainingWallV2',
        'units': 'world centimeters',
        'vertices': mesh.vertices, 'normals': mesh.normals, 'uv0': mesh.uv0,
        'triangles': mesh.triangles, 'materialIds': mesh.material,
        'materialSlots': ['Old City limestone (runtime M_Context_Building)', 'legacy V1 pieces (runtime PlazaAshlar)'],
        'legacyPieces': len(legacy_pieces), 'legacyTriangles': legacy_triangles,
        'linerPieces': len(liner_pieces), 'linerTriangles': liner_triangles,
        'linerNote': 'V1 curtain retained behind the dressed face so occlusion is at least V1; limestone slot.',
        'legacyAtomicEdges': len(legacy_atomic), 'exteriorAtomicEdges': len(edges),
        'internalLevelEdgesExcluded': internal, 'arrangementCells': cells,
        'chains': chains_out, 'probeLane': lane, 'parameters': PARAMETERS,
        'sourceHashesSha256': {
            'SourceAssets/FutureMountV1/terrain-generated/SM_JerusalemTerrain_07_08_FutureMountCut.mesh.json': SOURCE_SHA,
            'SourceAssets/context-review/KotelPlazaV1/kotel-plaza-plan.json': PLAN_SHA,
            'SourceAssets/context-review/KotelCutClosureV1/closure-study.json': LEGACY_SHA,
            'SourceAssets/visual-review/mount-platform-design.json': sha_bytes(DESIGN.read_bytes()),
        },
        'generatorSha256': sha_bytes(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
        'normalsAndWinding': 'Flat per-triangle normals equal normalized canonical cross products (visible side). Native import must use (A,C,B).',
    }


def generate():
    study_m = runpy.run_path(str(STUDY_DIR / 'measure_boundary.py'))
    source = pinned(study_m['SOURCE'], SOURCE_SHA)
    plan = pinned(study_m['PLAN'], PLAN_SHA)
    legacy = pinned(LEGACY, LEGACY_SHA)
    design = json.loads(DESIGN.read_text(encoding='utf-8-sig'))
    return build(source, plan, legacy, design)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = generate()
    text = json.dumps(result, separators=(',', ':')) + '\n'
    if args.check:
        if OUT.read_bytes() != text.encode('utf-8'):
            raise SystemExit('retaining-wall-v2.json differs from a fresh generation')
        print('PASS: retaining-wall-v2.json reproduced')
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_bytes(text.encode('utf-8'))
    print('%d triangles (%d legacy), %d vertices, %d chains; lane foot X %.3f footing front X %.3f' % (
        len(result['triangles']), result['legacyTriangles'], len(result['vertices']), len(result['chains']),
        result['probeLane']['footLineXcm'], result['probeLane']['footingFrontXcm']))

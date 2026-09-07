"""ShulchanV2: original detailed shulchan lechem hapanim (table, four snifim, 28 kanim,
twelve loaves in two stacks, two bazichin, four rings). Offline only: --export writes
SourceAssets/vessels-review/ShulchanV2/ (OBJ parts, geometry-manifest.json, preview PNGs).
No engine launch, no Content/ change, no map action. Native import and placement live in
Scripts/release_import_shulchan.py.

Sources (SourceAssets/vessels-review/book-keilim-review-20260907.md; page images under
"mikdash book/reference-pages", PDF page index = printed folio + 105):
  p. 241 (printed 136)  Yechezkel 41:22: table 2 x 1 amot, 3 amot high; diagram 22:6 loaf as an
                        open box with the karnot gap marked "7 etzbaot"; north side of the Heikhal,
                        2.5 amot from the north wall, 5 amot from the west wall, length along the House.
  p. 242 (printed 137)  render 22:6a "shulchan lechem hapanim 3 amot": frame below the top, tapered
                        legs, poles along the long sides, two tall plates at the long side.
  p. 243 (printed 138)  22:2 / 22:3: Mishkan table 1.5 amot vs Third-Temple table 3 amot with the
                        plates rising well above; 5 amot west-wall distance (Baraisa d'Meleches HaMishkan).
  p. 250 (printed 145)  22:14 bazichin ON the table BETWEEN the loaves, "2 tefachim" gap; 22:15 "28 kanim
                        in the manikiyot"; 22:16 manikiyot with the loaves; 22:17 table in the Heikhal with
                        the two plates face-on, each "5 tefachim" wide, "5 amot" tall; 22:20 "golden tray
                        6 tefachim"; text: first loaf on the table, 3 kanim on it, 3 on the second, third
                        and fourth, 2 on the fifth, none on the last (= 14 per stack); four rectangular gold
                        plates 5 tefachim wide, two per stack, each with fourteen half-reed holes; plates
                        5 amot high from the floor; table 2.5 amot from the north wall, 5 from the west,
                        its length along the House.
Talmudic figures used where the page images carry them: Menachos 96a (R' Meir: table 12 x 6 tefachim,
loaf 10 x 5 folded 2 tefachim up on each side, 2 tefachim between the stacks for the bazichin);
Shemos 25:23-29 (gold overlay, zer, one-tefach misgeret, four rings at the legs for the poles).
Temple Institute photographs (SourceAssets/reference-ti/shulchan, permission granted for reference):
column supports stand in PAIRS AT THE TWO LONG SIDES, tapered pilaster legs, crown band on the top rim,
footed lidded censers. Their ornament (vine band, acanthus brackets) is NOT copied.

Conventions: centimeters, 50 cm amah (tefach 8.333, etzba 2.083). Canonical axes: X = table length
(east-west after yaw 0), +Y = outward/room side (south in the scene, the table stands at the north),
Z up, common bottom-centre pivot at the floor under the table centre for EVERY part so one actor
location places the whole assembly. The OBJ files are written for the legacy Unreal OBJ importer
adapter proven by Codex: Y reflected and triangle winding reversed; the importer reflects Y back.
"""
import hashlib
import importlib.util
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/vessels-review/ShulchanV2'
DEST = '/Game/MikdashV3/MaterialReview/ShulchanV2'

AMAH = 50.0
TEFACH = AMAH / 6.0
ETZBA = TEFACH / 4.0

# ---------------------------------------------------------------- dimensions
D = dict(
    table_length=2 * AMAH, table_width=1 * AMAH, table_height=3 * AMAH,
    top_thickness=5.0, misgeret_height=TEFACH, misgeret_thickness=2.5,
    zer_top_height=5.5, zer_top_thickness=2.0, crenel=2.0, crenel_pitch=5.0,
    leg_top=9.0, leg_bottom=6.0,
    ring_major=3.5, ring_minor=0.8,
    plate_width=5 * TEFACH, plate_height=5 * AMAH, plate_thickness=3.0,
    plate_gap_from_table=10.0,          # inner face of the plate from the table/loaf edge (|y| 25 -> 35)
    rod_outer=1.5, rod_inner=1.0,
    loaf_length_unfolded=10 * TEFACH, loaf_width=5 * TEFACH, loaf_base=6 * TEFACH,
    loaf_wall_height=2 * TEFACH, loaf_dough=0.5 * TEFACH,
    karnot_gap=7 * ETZBA, karnot_depth=1 * ETZBA,
    stack_gap=2 * TEFACH,
    censer_radius=6.5, censer_height=22.5,
)


def dimension_table():
    """Every dimension with its source and whether it is measured (book/Talmud) or artistic."""
    rows = [
        ('table length', D['table_length'], '2 amot', 'measured', 'p. 241 (Yechezkel 41:22); Shemos 25:23'),
        ('table width', D['table_width'], '1 amah', 'measured', 'p. 241; Shemos 25:23'),
        ('table height (floor to top surface)', D['table_height'], '3 amot', 'measured', 'p. 241 main line (Targum, Rashi, Radak); alternative reading p. 246 that 3 amot include the bread is NOT modelled'),
        ('misgeret (frame) height', D['misgeret_height'], '1 tefach', 'measured', 'Shemos 25:25; TI dossier; drawn BELOW the top between the legs as on p. 242 render (position disputed)'),
        ('misgeret thickness', D['misgeret_thickness'], None, 'artistic', 'profile'),
        ('zer (crown) on top rim: height / thickness / crenel size and pitch', [D['zer_top_height'], D['zer_top_thickness'], D['crenel'], D['crenel_pitch']], None, 'artistic', 'Shemos 25:24 gives a zer without size; TI shows a crenellated band; second zer moulding on the misgeret per TI dossier'),
        ('top slab thickness', D['top_thickness'], None, 'artistic', 'profile; the 3-amot height is measured to the top surface'),
        ('legs: tapered pilasters, top / bottom section', [D['leg_top'], D['leg_bottom']], None, 'artistic', 'p. 242 render and TI show tapered pilasters; outer faces flush with the top edges'),
        ('rings: 4, at the legs against the misgeret, hole axis east-west (poles along the length)', [D['ring_major'], D['ring_minor']], None, 'artistic size, measured count/position', 'Shemos 25:26-27 (four rings at the four legs, against the misgeret, housings for the poles); p. 242 render shows the pole along the long side'),
        ('snifim plates: count', 4, '2 per stack', 'measured', 'p. 250 text: four rectangular gold plates, two per stack'),
        ('snifim plate width', D['plate_width'], '5 tefachim', 'measured', 'p. 250 text and diagram 22:17 label'),
        ('snifim plate height from the floor', D['plate_height'], '5 amot', 'measured', 'p. 250 text "5 amot from the ground"; diagram 22:17 label'),
        ('snifim plate thickness', D['plate_thickness'], None, 'artistic', 'profile'),
        ('snifim position: standing on the floor at the two LONG sides (north and south), one pair per stack', D['plate_gap_from_table'], None, 'interpretation', 'p. 250 diagram 22:17 shows the two 5-tefach plates side by side face-on with the 2-tefach gap between them and the rod ends as dots (rods perpendicular to the plates, i.e. north-south); TI columns stand in pairs at the long sides. The 10 cm stand-off from the table edge is artistic (clears the rings).'),
        ('kanim (rods): count and distribution per stack', [28, [3, 3, 3, 3, 2, 0]], '14 per stack', 'measured', 'p. 250 text: 3 on loaves 1-4, 2 on loaf 5, none on the top loaf (Menachos 97a). NOTE the brief said "3 for the lower five, 2 for the top" (=17); the book page gives 3+3+3+3+2 = 14.'),
        ('kanim shape: half tube (split reed), convex side up', [D['rod_outer'], D['rod_inner']], None, 'artistic radius, measured shape', 'p. 250 "half-reed shaped holes"; Rashi Shemos 25:29; Menachos 96a'),
        ('kanim length (plate outer face to plate outer face)', 2 * (D['table_width'] / 2 + D['plate_gap_from_table'] + D['plate_thickness']), None, 'derived', 'spans the two plates'),
        ('loaves: count and arrangement', [12, 'two stacks of six along the length'], '12', 'measured', 'p. 241 text; Vayikra 24:5-6; Menachos 96a'),
        ('loaf unfolded length x width', [D['loaf_length_unfolded'], D['loaf_width']], '10 x 5 tefachim', 'measured', 'Menachos 96a; p. 250 diagram 22:17 marks 5 tefachim'),
        ('loaf folded base (across the table width) and wall height', [D['loaf_base'], D['loaf_wall_height']], '6 and 2 tefachim', 'measured', 'Menachos 96a per R\' Meir (table 12 x 6): 10 = 2 + 6 + 2; p. 250 diagram 22:20 "golden tray 6 tefachim". The brief\'s "walls 7 tefachim" was checked against p. 241 diagram 22:6: the 7 is "7 etzbaot" (fingers) for the karnot gap, not a wall height; 2-tefach walls are used.'),
        ('karnot (horn tabs) gap / depth', [D['karnot_gap'], D['karnot_depth']], '7 etzbaot gap', 'measured gap, artistic depth', 'p. 241 diagram 22:6 shows the two wall-top tabs with a 7-etzbaot gap; the 1-etzba notch depth is artistic'),
        ('loaf dough thickness', D['loaf_dough'], None, 'artistic', 'half a tefach so the six-loaf stack (6 x 2 tefachim + rods) ends near the 5-amot plate top as in diagrams 22:3 and 22:17'),
        ('gap between the two stacks (bazichin stand here)', D['stack_gap'], '2 tefachim', 'measured', 'p. 250 diagram 22:14 label "2 tefachim"; Menachos 96a'),
        ('bazichin (censers): count, position', [2, 'on the table between the stacks'], None, 'measured position, artistic shape', 'p. 250 diagram 22:14 caption "the bazichin on the table between the loaves"; footed lidded goblet profile after TI'),
        ('bazichin radius / height', [D['censer_radius'], D['censer_height']], None, 'artistic', 'fits the 2-tefach gap'),
        ('placement: table centre 2.5 amot from the north wall, 5 amot from the west wall, length east-west', [-5300, -350, 925], '2.5 / 5 amot', 'measured', 'p. 241, p. 250 (32)(33)(34); scene mapping per book-keilim-review reading A'),
    ]
    return [dict(item=i, value_cm=v, halachic=h, kind=k, source=s) for i, v, h, k, s in rows]


# ---------------------------------------------------------------- geometry helpers
def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'Scripts' / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


KEILIM = module('_shulchan_bevel', 'create_heikhal_keilim.py')
bevel_box = KEILIM.bevel_box


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def volume(vertices, faces):
    total = 0.0
    for a, b, c in faces:
        p, q, r = vertices[a], vertices[b], vertices[c]
        n = cross([q[i] - p[i] for i in range(3)], [r[i] - p[i] for i in range(3)])
        total += sum(p[i] * n[i] for i in range(3))
    return total / 6.0


def box(center, size):
    """Plain closed box, 12 triangles, outward winding."""
    hx, hy, hz = [s / 2 for s in size]
    cx, cy, cz = center
    v = [(cx + sx * hx, cy + sy * hy, cz + sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    # index = (sx>0)*4 + (sy>0)*2 + (sz>0)
    f = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5),   # -x, +x
         (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6),   # -y, +y
         (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]   # -z, +z
    return orient(v, f)


def frustum(center_xy, z0, z1, size0, size1):
    """Tapered square pilaster: size0 at z0, size1 at z1; closed, 12 triangles."""
    cx, cy = center_xy
    v = []
    for z, s in ((z0, size0), (z1, size1)):
        h = s / 2
        v += [(cx - h, cy - h, z), (cx + h, cy - h, z), (cx + h, cy + h, z), (cx - h, cy + h, z)]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7)]
    for i in range(4):
        j = (i + 1) % 4
        f += [(i, j, 4 + j), (i, 4 + j, 4 + i)]
    return orient(v, f)


def torus(center, major, minor, axis, seg_major=24, seg_minor=12):
    """Closed torus; hole axis 'x', 'y' or 'z'."""
    v = []
    for i in range(seg_major):
        a = i * math.tau / seg_major
        for j in range(seg_minor):
            b = j * math.tau / seg_minor
            r = major + minor * math.cos(b)
            ring_u, ring_v, h = r * math.cos(a), r * math.sin(a), minor * math.sin(b)
            if axis == 'z':
                p = (ring_u, ring_v, h)
            elif axis == 'y':
                p = (ring_u, h, ring_v)
            else:
                p = (h, ring_u, ring_v)
            v.append((center[0] + p[0], center[1] + p[1], center[2] + p[2]))
    f = []
    for i in range(seg_major):
        for j in range(seg_minor):
            a = i * seg_minor + j
            b = ((i + 1) % seg_major) * seg_minor + j
            c = ((i + 1) % seg_major) * seg_minor + (j + 1) % seg_minor
            d = i * seg_minor + (j + 1) % seg_minor
            f += [(a, c, b), (a, d, c)]
    return orient(v, f)


def revolve(profile, center, segments=32):
    """Closed surface of revolution about the local Z axis. profile = [(r, z), ...] starting and
    ending at r == 0 (poles), every intermediate r > 0."""
    assert profile[0][0] == 0 and profile[-1][0] == 0 and all(r > 0 for r, _ in profile[1:-1])
    cx, cy, cz = center
    v = [(cx, cy, cz + profile[0][1])]
    rings = []
    for r, z in profile[1:-1]:
        start = len(v)
        for i in range(segments):
            a = i * math.tau / segments
            v.append((cx + r * math.cos(a), cy + r * math.sin(a), cz + z))
        rings.append(start)
    top = len(v)
    v.append((cx, cy, cz + profile[-1][1]))
    f = []
    for i in range(segments):
        j = (i + 1) % segments
        f.append((0, rings[0] + j, rings[0] + i))
        f.append((top, rings[-1] + i, rings[-1] + j))
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            f += [(r0 + i, r0 + j, r1 + j), (r0 + i, r1 + j, r1 + i)]
    return orient(v, f)


def half_tube(center, length, r_out, r_in, segments=12):
    """Half of a hollow tube (a split reed) running along Y, convex side up, closed shell."""
    cx, cy, cz = center
    outer = [(r_out * math.cos(t * math.pi / segments), r_out * math.sin(t * math.pi / segments)) for t in range(segments + 1)]
    inner = [(r_in * math.cos(t * math.pi / segments), r_in * math.sin(t * math.pi / segments)) for t in range(segments, -1, -1)]
    poly = outer + inner          # simple closed polygon in the XZ plane
    n = len(poly)
    v = []
    for y in (cy - length / 2, cy + length / 2):
        v += [(cx + x, y, cz + z) for x, z in poly]
    f = []
    for i in range(n):            # sides
        j = (i + 1) % n
        f += [(i, j, n + j), (i, n + j, n + i)]
    m = segments + 1
    for t in range(segments):     # caps: quads between outer[t], outer[t+1] and the matching inner points
        o0, o1 = t, t + 1
        i1, i0 = m + (segments - t - 1), m + (segments - t)
        f += [(o0, o1, i1), (o0, i1, i0)]
        f += [(n + o0, n + i1, n + o1), (n + o0, n + i0, n + i1)]
    return orient(v, f)


def orient(v, f):
    if volume(v, f) < 0:
        f = [(a, c, b) for a, b, c in f]
    return v, f


def closed(vertices, faces):
    keys = [tuple(round(x, 6) for x in p) for p in vertices]
    edges = {}
    for a, b, c in faces:
        for i, j in ((a, b), (b, c), (c, a)):
            key = tuple(sorted((keys[i], keys[j])))
            edges[key] = edges.get(key, 0) + 1
    return all(n == 2 for n in edges.values())


# ---------------------------------------------------------------- the assembly
def table_parts():
    L, W, H = D['table_length'], D['table_width'], D['table_height']
    t = D['top_thickness']
    parts = [('TopSlab', bevel_box((0, 0, H - t / 2), (L, W, t), 0.6))]
    # Zer on the top rim: a band around the slab rising above the top surface, crenellated.
    zh, zt = D['zer_top_height'], D['zer_top_thickness']
    zc = H - t + zh / 2
    for sy in (-1, 1):
        parts.append(('ZerTopLong_%d' % sy, bevel_box((0, sy * (W / 2 + zt / 2), zc), (L + 2 * zt, zt, zh), 0.4)))
    for sx in (-1, 1):
        parts.append(('ZerTopEnd_%d' % sx, bevel_box((sx * (L / 2 + zt / 2), 0, zc), (zt, W + 2 * zt, zh), 0.4)))
    c, pitch = D['crenel'], D['crenel_pitch']
    ztop = H - t + zh
    n = 0
    for sy in (-1, 1):
        x = -L / 2
        while x <= L / 2 + 1e-6:
            parts.append(('Crenel_%03d' % n, box((x, sy * (W / 2 + zt / 2), ztop + c / 2 - 0.3), (c, zt, c + 0.3)))); n += 1
            x += pitch
    for sx in (-1, 1):
        y = -W / 2 + pitch
        while y <= W / 2 - pitch + 1e-6:
            parts.append(('Crenel_%03d' % n, box((sx * (L / 2 + zt / 2), y, ztop + c / 2 - 0.3), (zt, c, c + 0.3)))); n += 1
            y += pitch
    # Legs: tapered pilasters, outer faces flush with the slab edges at the top.
    lt, lb = D['leg_top'], D['leg_bottom']
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(('Leg_%d_%d' % (sx, sy), frustum((sx * (L / 2 - lt / 2), sy * (W / 2 - lt / 2)), 0.0, H - t + 0.5, lb, lt)))
    # Misgeret: one-tefach band below the top between the legs, with its own zer moulding.
    mh, mt = D['misgeret_height'], D['misgeret_thickness']
    mz = H - t - mh / 2
    for sy in (-1, 1):
        parts.append(('Misgeret_Long_%d' % sy, bevel_box((0, sy * (W / 2 - mt / 2), mz), (L - 2, mt, mh), 0.5)))
        parts.append(('ZerMisgeret_Long_%d' % sy, bevel_box((0, sy * (W / 2 + 0.5), H - t - mh + 0.9), (L + 1, 3.5, 1.8), 0.4)))
    for sx in (-1, 1):
        parts.append(('Misgeret_End_%d' % sx, bevel_box((sx * (L / 2 - mt / 2), 0, mz), (mt, W - 2, mh), 0.5)))
        parts.append(('ZerMisgeret_End_%d' % sx, bevel_box((sx * (L / 2 + 0.5), 0, H - t - mh + 0.9), (3.5, W + 1, 1.8), 0.4)))
    # Bosses along the misgeret faces (artistic hint of repousse, not a traced pattern).
    n = 0
    for sy in (-1, 1):
        x = -L / 2 + 12
        while x <= L / 2 - 12 + 1e-6:
            parts.append(('Boss_%03d' % n, box((x, sy * (W / 2 + 0.4), mz + 0.8), (1.6, 1.0, 1.6)))); n += 1
            x += 6
    for sx in (-1, 1):
        y = -W / 2 + 12
        while y <= W / 2 - 12 + 1e-6:
            parts.append(('Boss_%03d' % n, box((sx * (L / 2 + 0.4), y, mz + 0.8), (1.0, 1.6, 1.6)))); n += 1
            y += 6
    return parts


def ring_parts():
    L, W, H = D['table_length'], D['table_width'], D['table_height']
    z = H - D['top_thickness'] - D['misgeret_height'] / 2
    reach = D['ring_major'] + D['ring_minor']
    parts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(('Ring_%d_%d' % (sx, sy), torus((sx * (L / 2 - D['leg_top'] / 2), sy * (W / 2 + reach - 0.5), z), D['ring_major'], D['ring_minor'], 'x', 32, 12)))
    return parts


def stack_centers():
    return [-(D['loaf_width'] / 2 + D['stack_gap'] / 2), D['loaf_width'] / 2 + D['stack_gap'] / 2]


def plate_center_y():
    return D['table_width'] / 2 + D['plate_gap_from_table'] + D['plate_thickness'] / 2


def loaf_levels():
    pitch = D['loaf_wall_height'] + D['rod_outer']
    bottoms = [D['table_height'] + k * pitch for k in range(6)]
    tops = [b + D['loaf_wall_height'] for b in bottoms]
    return bottoms, tops


def rod_positions():
    """(x, z) for the 14 rods of one stack centred at x=0."""
    _, tops = loaf_levels()
    rows = []
    for k, count in enumerate([3, 3, 3, 3, 2, 0]):
        if count == 3:
            xs = [-12.5, 0.0, 12.5]
        elif count == 2:
            xs = [-8.3, 8.3]
        else:
            xs = []
        rows += [(x, tops[k]) for x in xs]
    return rows


def snifim_parts():
    parts = []
    yc = plate_center_y()
    for sx, cx in zip((-1, 1), stack_centers()):
        for sy in (-1, 1):
            parts.append(('Plate_%d_%d' % (sx, sy), bevel_box((cx, sy * yc, D['plate_height'] / 2), (D['plate_width'], D['plate_thickness'], D['plate_height']), 0.6)))
            for n, (x, z) in enumerate(rod_positions()):
                parts.append(('Collar_%d_%d_%02d' % (sx, sy, n), torus((cx + x, sy * (yc + D['plate_thickness'] / 2 + 0.3), z), 2.2, 0.6, 'y', 16, 8)))
    return parts


def kanim_parts():
    parts = []
    length = 2 * (plate_center_y() + D['plate_thickness'] / 2)
    for sx, cx in zip((-1, 1), stack_centers()):
        for n, (x, z) in enumerate(rod_positions()):
            parts.append(('Kaneh_%d_%02d' % (sx, n), half_tube((cx + x, 0.0, z), length, D['rod_outer'], D['rod_inner'], 12)))
    return parts


def loaf(cx, z0, tag):
    """Open-box loaf: base slab across the table width, two 2-tefach walls at the north and south
    ends with karnot tabs (7-etzbaot notch between them)."""
    w, base, d = D['loaf_width'], D['loaf_base'], D['loaf_dough']
    wall_h = D['loaf_wall_height'] - d
    tab = (w - D['karnot_gap']) / 2
    parts = [('%s_Base' % tag, bevel_box((cx, 0, z0 + d / 2), (w, base, d), 0.8))]
    for sy in (-1, 1):
        y = sy * (base / 2 - d / 2)
        zc = z0 + d + (wall_h + 0.5) / 2 - 0.5
        for sx in (-1, 1):
            parts.append(('%s_Karn_%d_%d' % (tag, sy, sx), bevel_box((cx + sx * (w / 2 - tab / 2), y, zc), (tab, d, wall_h + 0.5), 0.8)))
        mid_h = wall_h - D['karnot_depth'] + 0.5
        parts.append(('%s_WallMid_%d' % (tag, sy), bevel_box((cx, y, z0 + d + mid_h / 2 - 0.5), (D['karnot_gap'] + 1.0, d, mid_h), 0.8)))
    return parts


def loaves_parts(stack_index):
    cx = stack_centers()[stack_index]
    bottoms, _ = loaf_levels()
    parts = []
    for k, z0 in enumerate(bottoms):
        parts += loaf(cx, z0, 'Loaf%d' % (k + 1))
    return parts


def censer_profile():
    r, h = D['censer_radius'], D['censer_height']
    return [(0, 0), (4.8, 0), (5.0, 0.8), (3.8, 1.3), (1.6, 1.8), (1.6, 5.0), (2.4, 6.0), (4.8, 8.0), (r, 11.0),
            (r, 13.6), (r - 0.3, 14.0), (r - 0.1, 14.6), (5.6, 16.4), (4.2, 18.4), (2.4, 19.6), (1.1, 20.2), (1.1, 21.6), (0.9, 22.0), (0, h)]


def bazichin_parts():
    return [('Bazich_%d' % sy, revolve(censer_profile(), (0.0, sy * 12.5, D['table_height']), 32)) for sy in (-1, 1)]


def geometry():
    return {
        'SM_ShulchanV2_Table': table_parts(),
        'SM_ShulchanV2_Rings': ring_parts(),
        'SM_ShulchanV2_Snifim': snifim_parts(),
        'SM_ShulchanV2_Kanim': kanim_parts(),
        'SM_ShulchanV2_LoavesWest': loaves_parts(0),
        'SM_ShulchanV2_LoavesEast': loaves_parts(1),
        'SM_ShulchanV2_Bazichin': bazichin_parts(),
    }


MATERIAL_ROLE = {'SM_ShulchanV2_LoavesWest': 'bread', 'SM_ShulchanV2_LoavesEast': 'bread'}


# ---------------------------------------------------------------- export
def write_obj(name, parts, path):
    lines = ['# Original ShulchanV2 %s; Unreal legacy OBJ adapter (Y reflected, winding reversed)' % name, 'o ' + name]
    index = 1
    allv = []
    checks = []
    for part, (vertices, faces) in parts:
        vol = volume(vertices, faces)
        assert vol > 0, 'inverted part ' + part
        assert closed(vertices, faces), 'open part ' + part
        allv.extend(vertices)
        lines.append('g ' + part)
        for a, b, c in faces:
            p, q, r = [(vertices[i][0], -vertices[i][1], vertices[i][2]) for i in (a, c, b)]
            ab = [q[i] - p[i] for i in range(3)]
            ac = [r[i] - p[i] for i in range(3)]
            n = cross(ab, ac)
            length = math.sqrt(sum(x * x for x in ab))
            nl = math.sqrt(sum(x * x for x in n))
            assert nl > 1e-8 and length > 1e-8, 'degenerate triangle in ' + part
            for v in (p, q, r):
                lines.append('v %.9f %.9f %.9f' % v)
            for uv in ((0, 0), (length / 10, 0), (sum(ac[i] * ab[i] / length for i in range(3)) / 10, nl / length / 10)):
                lines.append('vt %.9f %.9f' % uv)
            for _ in range(3):
                lines.append('vn %.9f %.9f %.9f' % tuple(x / nl for x in n))
            lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
            index += 3
        checks.append(dict(name=part, triangles=len(faces), closed=True, volume_cm3=vol))
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn(p[i] for p in allv) for i in range(3)] for k, fn in [('min', min), ('max', max)]}
    return dict(name=name, file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), triangles=(index - 1) // 3,
                parts=len(parts), material_role=MATERIAL_ROLE.get(name, 'gold'), bounds_cm=bounds,
                minimum_part_signed_volume_cm3=min(c['volume_cm3'] for c in checks), part_checks=checks)


def readback(path, record):
    """Independent OBJ parse: counts, normals, UVs, adapter round trip to canonical bounds."""
    verts, uvs, normals, faces = [], [], [], []
    for line in path.read_text().splitlines():
        cols = line.split()
        if not cols:
            continue
        if cols[0] == 'v':
            verts.append(tuple(map(float, cols[1:])))
        elif cols[0] == 'vt':
            uvs.append(tuple(map(float, cols[1:])))
        elif cols[0] == 'vn':
            normals.append(tuple(map(float, cols[1:])))
        elif cols[0] == 'f':
            faces.append([tuple(int(v) - 1 for v in c.split('/')) for c in cols[1:]])
    assert len(faces) == record['triangles']
    for face in faces:
        assert len(face) == 3
        a, b, c = [verts[f[0]] for f in face]
        ab = [b[i] - a[i] for i in range(3)]
        ac = [c[i] - a[i] for i in range(3)]
        cr = cross(ab, ac)
        area = math.sqrt(sum(x * x for x in cr))
        assert area > 1e-8
        assert sum(cr[i] * normals[face[0][2]][i] for i in range(3)) / area > .999999
    canonical = [(x, -y, z) for x, y, z in verts]
    bounds = {k: [fn(v[i] for v in canonical) for i in range(3)] for k, fn in [('min', min), ('max', max)]}
    error = max(abs(bounds[k][i] - record['bounds_cm'][k][i]) for k in bounds for i in range(3))
    assert error < 1e-6
    # Right-handed signed volume of the FILE (adapter space) stays POSITIVE: the Y reflection and the
    # winding reversal each flip the sign once. Same sign the release scripts expect for "no flip needed"
    # (release_import_thirdparty_vessels.spec.json expectedOfflineRightHandedVolumeSign).
    file_volume = volume(verts, [tuple(f[0] for f in face) for face in faces])
    assert file_volume > 0, 'adapter sign unexpected for ' + path.name
    return dict(mesh=record['name'], triangles=len(faces), bounds_error_cm=error, file_space_signed_volume_cm3=file_volume, normals_and_uvs='PASS')


# ---------------------------------------------------------------- preview (stdlib PNG)
def render_views(geometry_by_mesh, path, views, size=(1600, 900)):
    """Software orthographic z-buffer render; illustrative colours only (gold / bread)."""
    W, H = size
    rgb = bytearray([24, 28, 33] * (W * H))
    zbuf = [-1e18] * (W * H)
    cols = len(views)
    panel_w = W // cols
    for k, view in enumerate(views):
        yaw, pitch, scale, label = view
        # Viewer stands in direction u (yaw 0 = +Y, the room side; yaw 90 = +X, east) at elevation pitch,
        # looking at the origin. right = cross(z, d), up = cross(d, right); nearest = smallest p.d.
        u = (math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
        cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
        cam = (-u[0] * cp, -u[1] * cp, -sp)
        right = cross((0.0, 0.0, 1.0), cam)
        rl = math.sqrt(sum(x * x for x in right)) or 1.0
        right = [x / rl for x in right]
        up = cross(cam, right)

        def project(p):
            sx = sum(p[i] * right[i] for i in range(3))
            sz = sum(p[i] * up[i] for i in range(3))
            depth = sum(p[i] * cam[i] for i in range(3))
            return sx, sz, -depth
        x0 = k * panel_w + panel_w / 2
        base_y = H / 2 if pitch > 60 else H - 60
        light = (-0.35, -0.6, 0.72)
        for mesh, parts in geometry_by_mesh.items():
            colour = (150, 96, 52) if MATERIAL_ROLE.get(mesh) == 'bread' else (214, 168, 78)
            for _, (v, faces) in parts:
                for a, b, c in faces:
                    pa, pb, pc = v[a], v[b], v[c]
                    n = cross([pb[i] - pa[i] for i in range(3)], [pc[i] - pa[i] for i in range(3)])
                    ln = math.sqrt(sum(x * x for x in n)) or 1.0
                    shade = 0.42 + 0.58 * max(0.0, sum(n[i] * light[i] for i in range(3)) / ln)
                    col = bytes(min(255, int(x * shade)) for x in colour)
                    pts = []
                    for p in (pa, pb, pc):
                        sx, sz, d = project(p)
                        pts.append((x0 + sx * scale, base_y - sz * scale, d))
                    (ax, ay, ad), (bx, by, bd), (cx_, cy_, cd) = pts
                    det = (by - cy_) * (ax - cx_) + (cx_ - bx) * (ay - cy_)
                    if abs(det) < 1e-9:
                        continue
                    ymin, ymax = max(0, int(min(ay, by, cy_))), min(H - 1, int(max(ay, by, cy_)) + 1)
                    xmin, xmax = max(k * panel_w, int(min(ax, bx, cx_))), min((k + 1) * panel_w - 1, int(max(ax, bx, cx_)) + 1)
                    for py in range(ymin, ymax + 1):
                        for px in range(xmin, xmax + 1):
                            w0 = ((by - cy_) * (px + .5 - cx_) + (cx_ - bx) * (py + .5 - cy_)) / det
                            w1 = ((cy_ - ay) * (px + .5 - cx_) + (ax - cx_) * (py + .5 - cy_)) / det
                            w2 = 1 - w0 - w1
                            if w0 < 0 or w1 < 0 or w2 < 0:
                                continue
                            depth = w0 * ad + w1 * bd + w2 * cd
                            idx = py * W + px
                            if depth > zbuf[idx]:
                                zbuf[idx] = depth
                                rgb[idx * 3:idx * 3 + 3] = col
        # panel separator
        for py in range(H):
            idx = py * W + k * panel_w
            rgb[idx * 3:idx * 3 + 3] = bytes((60, 64, 70))
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    scan = b''.join(b'\x00' + rgb[y * W * 3:(y + 1) * W * 3] for y in range(H))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', W, H, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(scan, 9)) + chunk(b'IEND', b''))
    return [v[3] for v in views]


def export(force=False):
    if (OUT / 'geometry-manifest.json').exists() and not force:
        raise SystemExit('Frozen generation preserved: %s exists (use --force to regenerate)' % (OUT / 'geometry-manifest.json'))
    OUT.mkdir(parents=True, exist_ok=True)
    geo = geometry()
    meshes = []
    checks = []
    for name, parts in geo.items():
        record = write_obj(name, parts, OUT / (name + '.obj'))
        checks.append(readback(OUT / record['file'], record))
        meshes.append(record)
    total = sum(m['triangles'] for m in meshes)
    assert total < 120000, total
    bottoms, tops = loaf_levels()
    yc = plate_center_y()
    previews = {}
    # South elevation (viewer in the room looking north: +X to the right), east elevation, top, oblique.
    previews['shulchan-v2-preview.png'] = render_views(geo, OUT / 'shulchan-v2-preview.png', [
        (0, 0, 2.6, 'south elevation (looking north, east right)'),
        (90, 0, 2.6, 'east elevation (looking west, north right)'),
        (35, 28, 2.2, 'oblique from the south-east above'),
    ], (1650, 800))
    previews['shulchan-v2-preview-top.png'] = render_views(geo, OUT / 'shulchan-v2-preview-top.png', [
        (0, 89.9, 5.0, 'plan (north up)'),
    ], (900, 700))
    manifest = dict(
        status='OFFLINE_VALIDATED_NATIVE_AND_VISUAL_PENDING', namespace=DEST, amah_cm=AMAH, tefach_cm=TEFACH, etzba_cm=ETZBA,
        script='Scripts/create_shulchan_v2.py', script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        bevel_helper='Scripts/create_heikhal_keilim.py', bevel_helper_sha256=hashlib.sha256((ROOT / 'Scripts/create_heikhal_keilim.py').read_bytes()).hexdigest(),
        convention='Canonical XYZ Unreal cm: X = table length (east-west at yaw 0), +Y = room side (south; the table stands at the north wall), Z up, '
                   'common bottom-centre pivot on the floor under the table centre for every part. OBJ files carry Y reflected and winding reversed '
                   'for the legacy OBJ importer (create_heikhal_keilim / create_sanctuary_doors adapter); the importer reflects Y back, so imported '
                   'bounds must equal bounds_cm and UE signed volumes must be positive. Per-triangle normals and non-degenerate UV charts; no images.',
        assembly=dict(
            table_top_z_cm=D['table_height'], loaf_bottoms_z_cm=bottoms, loaf_tops_z_cm=tops, top_of_stack_z_cm=tops[-1],
            plate_top_z_cm=D['plate_height'], plate_center_abs_y_cm=yc, plate_outer_abs_y_cm=yc + D['plate_thickness'] / 2,
            stack_centers_x_cm=stack_centers(), rod_rows_per_stack=[3, 3, 3, 3, 2, 0],
            supports_side='north and south LONG sides, one plate per stack per side (p. 250 diagram 22:17; TI column pairs at the long sides); rods run north-south',
            assembly_min_y_cm=min(m['bounds_cm']['min'][1] for m in meshes),
            north_wall_clearance_note='Placed at Y -350 the assembly (snifim collars) reaches Y %.1f, %.1f cm from the north wall face Y -500 (>= 100 cm guard in release_import_shulchan.py)' % (
                -350 + min(m['bounds_cm']['min'][1] for m in meshes), 150 + min(m['bounds_cm']['min'][1] for m in meshes)),
        ),
        dimensions=dimension_table(),
        brief_discrepancies=[
            'Brief: loaf walls 7 tefachim. Page 241 diagram 22:6 labels the karnot gap "7 etzbaot"; Menachos 96a gives 2-tefach folded walls. Modelled: 2-tefach walls, 7-etzba karnot gap.',
            'Brief: rods 3 for each of the lower five loaves + 2 for the top (17). Page 250 text: 3,3,3,3,2,0 = 14 per stack, 28 total. Modelled per the book.',
            'Brief asked whether the supports stand at the short ends. Book diagram 22:17 and the TI table both put them at the LONG sides; modelled at the long sides.',
        ],
        artistic_summary='Profiles (bevels, crenellated zer, misgeret moulding and bosses, leg taper), plate thickness and stand-off, rod radii, dough thickness, censer shape are artistic. Counts, halachic sizes and positions are from the cited pages.',
        total_triangles=total, meshes=meshes, readback=checks, previews=previews,
        preview_limit='Software orthographic source preview with illustrative gold/bread colours; not a native render or material acceptance.',
    )
    (OUT / 'geometry-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    if '--export' not in sys.argv:
        raise SystemExit('Explicit --export [--force] offline; native work is in Scripts/release_import_shulchan.py')
    report = export(force='--force' in sys.argv)
    print(json.dumps({m['name']: m['triangles'] for m in report['meshes']}, indent=2))
    print('total triangles', report['total_triangles'])
    print('previews', list(report['previews']))

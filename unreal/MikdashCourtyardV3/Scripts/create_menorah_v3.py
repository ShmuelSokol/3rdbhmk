"""Original parametric Temple-Institute-style menorah (MenorahV3) with its three-step tending stone.

Offline, stdlib only: writes per-part OBJ files, a geometry manifest with every counted ornament and a
software preview PNG into SourceAssets/vessels-review/MenorahV3/. No engine launch, no Content/ change.
Native import and placement live in Scripts/release_import_menorah_v3.py (+ .spec.json).

Sources (the manifest carries them per dimension):
  Shemos 25:31-40 (ornament counts), Menachos 28b (the 18-tefach vertical breakdown of the shaft),
  Rambam Beit HaBechirah 3:8 (wick directions), 3:10 (18 tefachim), 3:11 (three-step stone in front),
  3:12 (lamps north-south); book "Lishchno Tidreshu" pp. 252-254 (diagram 22:23b is the Rambam
  north-south depiction with the stone in front); SourceAssets/vessels-review/menorah-model-spec.json
  (Codex's audit of the TI photograph: nested rounded U branches, stepped polygonal plinth, seven
  similar upper stacks, lamp offsets about 0.11-0.12 H apart). The TI photographs were viewed for
  proportion only; nothing is traced, scanned or textured from them.

Canonical frame (Unreal cm): local X = the lamp row (fan axis), local +Y = FRONT (the side the tending
stone is on = east after the placement yaw of -90), Z up, origin at the centre of the base contact
plane on the floor. OBJ files carry Y reflected and reversed winding for the legacy OBJ importer
(same adapter as ShulchanV2 / DoorsParochesV1); the importer reflects Y back, so imported bounds must
equal bounds_cm and UE signed volumes must be positive.

Usage:  python Scripts/create_menorah_v3.py --export [--force]
"""
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets' / 'vessels-review' / 'MenorahV3'
DEST = '/Game/MikdashV3/MaterialReview/MenorahV3'
AMAH = 50.0
TEFACH = AMAH / 6.0
TAU = math.tau

# ---------------------------------------------------------------- parameters (cm)
P = dict(
    total_height=18 * TEFACH,          # 150.0: floor to the highest lamp detail (Rambam 3:10; book p. 252)
    lamp_pitch=18.0,                   # artistic / TI photo fit (offsets 0.12 H); 7 lamps -> tips +-54
    junction_z=[8.5 * TEFACH, 10.5 * TEFACH, 12.5 * TEFACH],   # Menachos 28b: knops with branches at tefachim 8-9, 10-11, 12-13
    lower_group_z=5 * TEFACH,          # Menachos 28b: goblet, knop, flower at tefach 5-6 (stretched, see manifest)
    base_tiers=[(30.0, 0.0, 7.0), (24.0, 7.0, 13.0), (18.0, 13.0, 18.5)],   # hex circumradius, z0, z1
    collar=[(0, 18.5), (9.0, 18.5), (9.0, 19.5), (6.5, 20.5), (5.5, 22.5), (0, 22.5)],
    base_flower_z=22.0,
    shaft_r=(3.4, 2.9),                # bottom -> top taper
    branch_r=(3.0, 2.2),               # root -> tip taper (brief)
    goblet_h=5.2, knop_h=5.0, knop_r=5.4, junction_knop=(6.6, 3.6), flower_h=4.0, flower_r=5.2,
    lamp_h=3.6, lamp_r=5.6, nozzle_r=0.7,
    stone=dict(gap=10.0, width=90.0, tread=30.0, rise=2 * TEFACH, steps=3, corner=12.0),
)
SEG = dict(round=40, flower=48, tube=24, hex=6)


# ---------------------------------------------------------------- vector helpers
def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def norm(a):
    length = math.sqrt(sum(x * x for x in a)) or 1.0
    return [x / length for x in a]


def volume(vertices, faces):
    total = 0.0
    for a, b, c in faces:
        va, vb, vc = vertices[a], vertices[b], vertices[c]
        total += va[0] * (vb[1] * vc[2] - vb[2] * vc[1]) + va[1] * (vb[2] * vc[0] - vb[0] * vc[2]) + va[2] * (vb[0] * vc[1] - vb[1] * vc[0])
    return total / 6.0


def orient(vertices, faces):
    if volume(vertices, faces) < 0:
        faces = [(a, c, b) for a, b, c in faces]
    return vertices, faces


def closed(vertices, faces):
    """Every welded position-edge is shared by exactly two triangles (closed 2-manifold)."""
    keys = [tuple(round(x, 5) for x in v) for v in vertices]
    edges = {}
    for a, b, c in faces:
        for i, j in ((a, b), (b, c), (c, a)):
            if keys[i] == keys[j]:
                return False
            edge = (keys[i], keys[j]) if keys[i] < keys[j] else (keys[j], keys[i])
            edges[edge] = edges.get(edge, 0) + 1
    return all(n == 2 for n in edges.values())


# ---------------------------------------------------------------- primitives
def lathe(profile, center=(0.0, 0.0, 0.0), segments=40, lobes=0, amp=0.0, phase=0.0):
    """Revolve an (r, z) profile that starts and ends on the axis; optional petal/relief lobes."""
    assert profile[0][0] == 0 and profile[-1][0] == 0, 'profile must start and end on the axis'
    vertices, rings, faces = [], [], []
    for radius, z in profile:
        ring = []
        for i in range(1 if radius == 0 else segments):
            angle = i * TAU / segments
            r = radius * (1 + amp * math.cos(lobes * angle + phase)) if lobes else radius
            ring.append(len(vertices))
            vertices.append((center[0] + r * math.cos(angle), center[1] + r * math.sin(angle), center[2] + z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if len(a) == 1 and len(b) > 1:
                faces.append((a[0], b[j], b[i]))
            elif len(b) == 1 and len(a) > 1:
                faces.append((a[i], a[j], b[0]))
            elif len(a) > 1 and len(b) > 1:
                faces.extend([(a[i], a[j], b[j]), (a[i], b[j], b[i])])
    return orient(vertices, faces)


def sweep(points, radii, segments=24):
    """Closed tube with circular sections along a polyline (planar curves get a twist-free frame)."""
    vertices, rings, faces = [], [], []
    n = len(points)
    for k, p in enumerate(points):
        if k == 0:
            t = sub(points[1], points[0])
        elif k == n - 1:
            t = sub(points[-1], points[-2])
        else:
            t = sub(points[k + 1], points[k - 1])
        t = norm(t)
        ref = (0.0, 1.0, 0.0) if abs(t[1]) < 0.9 else (1.0, 0.0, 0.0)
        u = norm(cross(ref, t))
        w = cross(t, u)
        ring = []
        for j in range(segments):
            a = j * TAU / segments
            ring.append(len(vertices))
            vertices.append(tuple(p[i] + radii[k] * (math.cos(a) * u[i] + math.sin(a) * w[i]) for i in range(3)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            faces.extend([(a[i], a[j], b[j]), (a[i], b[j], b[i])])
    for ring, point, reverse in ((rings[0], points[0], True), (rings[-1], points[-1], False)):
        c = len(vertices)
        vertices.append(tuple(point))
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((ring[j], ring[i], c) if reverse else (ring[i], ring[j], c))
    return orient(vertices, faces)


def prism(polygon, z0, z1):
    """Extruded convex polygon (list of (x, y)), caps as centroid fans."""
    n = len(polygon)
    cx = sum(p[0] for p in polygon) / n
    cy = sum(p[1] for p in polygon) / n
    vertices = [(x, y, z0) for x, y in polygon] + [(x, y, z1) for x, y in polygon] + [(cx, cy, z0), (cx, cy, z1)]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.extend([(i, j, n + j), (i, n + j, n + i)])
        faces.append((j, i, 2 * n))
        faces.append((n + i, n + j, 2 * n + 1))
    return orient(vertices, faces)


# ---------------------------------------------------------------- ornament profiles (r, z from the ornament base)
def goblet_profile():
    h = P['goblet_h']
    s = h / 5.2
    return [(0, 0), (3.0, 0), (3.0, .5 * s), (1.9, 1.0 * s), (1.7, 1.8 * s), (2.2, 2.8 * s), (3.2, 3.9 * s), (3.7, 4.7 * s), (3.6, h),
            (3.0, h), (2.8, 4.5 * s), (0, 4.4 * s)]


def knop_profile(rx, rz, steps=9):
    profile = [(0, 0)]
    for k in range(1, steps):
        theta = math.pi * k / steps
        profile.append((rx * math.sin(theta), rz * (1 - math.cos(theta))))
    profile.append((0, 2 * rz))
    return profile


def flower_profile(scale=1.0):
    h = P['flower_h'] * scale
    r = P['flower_r'] * scale
    return [(0, 0), (2.6 * scale, 0), (2.4 * scale, .25 * h), (3.2 * scale, .55 * h), (r * .92, .9 * h), (r, h), (r * .8, .97 * h),
            (2.0 * scale, .62 * h), (0, .58 * h)]


def lamp_profile():
    h = P['lamp_h']
    r = P['lamp_r']
    return [(0, 0), (2.6, 0), (3.0, .3), (r * .93, .66 * h), (r, .9 * h), (r, h), (r * .9, h), (r * .84, .9 * h), (3.0, .38 * h), (0, .33 * h)]


# ---------------------------------------------------------------- assembly
def layout():
    """Heights of every stack element, derived downward from the 150 cm lamp top (see manifest notes)."""
    top = P['total_height']
    nozzle_top = P['lamp_h'] + 1.0 + P['nozzle_r']          # nozzle rises 1.0 above the rim
    lamp_z0 = top - nozzle_top
    flower_z0 = lamp_z0 + 1.2 - P['flower_h']                # lamp bowl nests 1.2 cm into the flower
    knop_z0 = flower_z0 + .3 - P['knop_h']
    goblet_z0 = [knop_z0 + .4 - P['goblet_h'] * (3 - k) for k in range(3)]   # rims tuck 0.4 into the next element
    branch_top = goblet_z0[0] + .8                            # tube ends inside the first goblet foot
    lower = P['lower_group_z']
    lower_knop = lower + P['goblet_h'] - .4
    lower_flower = lower_knop + P['knop_h'] - .3
    return dict(lamp_z0=lamp_z0, flower_z0=flower_z0, knop_z0=knop_z0, goblet_z0=goblet_z0, branch_top=branch_top,
                lower_goblet=lower, lower_knop=lower_knop, lower_flower=lower_flower,
                lamp_rim=lamp_z0 + P['lamp_h'], upper_group_span=[goblet_z0[0], flower_z0 + P['flower_h']],
                lower_group_span=[lower, lower_flower + P['flower_h']])


def branch_curve(x_tip, z_root, z_top, steps):
    """Quarter ellipse: leaves the shaft horizontally at the junction knop, rises vertically into the stack."""
    points, radii = [], []
    for k in range(steps + 1):
        t = (math.pi / 2) * k / steps
        points.append((x_tip * math.sin(t), 0.0, z_root + (z_top - z_root) * (1 - math.cos(t))))
        radii.append(P['branch_r'][0] + (P['branch_r'][1] - P['branch_r'][0]) * k / steps)
    return points, radii


def geometry():
    """Returns {meshName: [(partId, kind, (vertices, faces), meta), ...]} and the ornament register."""
    L = layout()
    meshes = {name: [] for name in ('SM_MenorahV3_Base', 'SM_MenorahV3_Shaft', 'SM_MenorahV3_BranchesL', 'SM_MenorahV3_BranchesR',
                                    'SM_MenorahV3_Ornaments', 'SM_MenorahV3_Lamps', 'SM_MenorahV3_StepStone')}
    register = []

    def add(mesh, part_id, kind, geo, **meta):
        v, f = geo
        assert closed(v, f), 'open part ' + part_id
        assert volume(v, f) > 0, 'inverted part ' + part_id
        meshes[mesh].append((part_id, kind, (v, f)))
        register.append(dict(id=part_id, kind=kind, mesh=mesh, triangles=len(f), **meta))

    # Base: three hexagonal tiers (flats facing front/back), round collar. Rambam/Menachos: yerech + flower = 3 tefachim.
    for k, (R, z0, z1) in enumerate(P['base_tiers'], 1):
        b = 1.0
        add('SM_MenorahV3_Base', 'BaseTier_%02d' % k, 'base', lathe([(0, z0), (R, z0), (R, z1 - b), (R - b, z1), (0, z1)], segments=SEG['hex']),
            circumradius_cm=R, z_cm=[z0, z1])
    add('SM_MenorahV3_Base', 'BaseCollar', 'base', lathe(P['collar'], segments=SEG['round']), z_cm=[P['collar'][0][1], P['collar'][-1][1]])

    # Shaft tube (through the base flower up into the first upper goblet).
    z_shaft0 = 20.0
    add('SM_MenorahV3_Shaft', 'Shaft', 'shaft', sweep([(0, 0, z_shaft0), (0, 0, L['branch_top'])], list(P['shaft_r']), SEG['tube']),
        radius_cm=list(P['shaft_r']), z_cm=[z_shaft0, L['branch_top']])

    # Ornaments on the shaft (x = 0).
    orn = 'SM_MenorahV3_Ornaments'
    add(orn, 'Flower_Shaft_Base', 'flower', lathe(flower_profile(1.5), (0, 0, P['base_flower_z']), SEG['flower'], lobes=6, amp=.10),
        x_cm=0.0, z_cm=P['base_flower_z'], note='Menachos 28b: flower within the lowest 3 tefachim (yerech u-ferach)')
    add(orn, 'Goblet_Shaft_01', 'goblet', lathe(goblet_profile(), (0, 0, L['lower_goblet']), SEG['round'], lobes=16, amp=.03), x_cm=0.0, z_cm=L['lower_goblet'])
    add(orn, 'Knop_Shaft_Lower', 'knop', lathe(knop_profile(P['knop_r'], P['knop_h'] / 2), (0, 0, L['lower_knop']), SEG['round'], lobes=12, amp=.04), x_cm=0.0, z_cm=L['lower_knop'])
    add(orn, 'Flower_Shaft_Lower', 'flower', lathe(flower_profile(), (0, 0, L['lower_flower']), SEG['flower'], lobes=6, amp=.12), x_cm=0.0, z_cm=L['lower_flower'])
    for k, zj in enumerate(P['junction_z'], 1):
        rx, rz = P['junction_knop']
        add(orn, 'Knop_Junction_%02d' % k, 'knop', lathe(knop_profile(rx, rz), (0, 0, zj - rz), SEG['round'], lobes=12, amp=.05), x_cm=0.0, z_cm=zj,
            note='Menachos 28b: knop from which two branches emerge')

    # Seven upper stacks: 3 goblets, knop, flower, lamp each (Shemos 25:33-34; TI: seven similar stacks at one lamp level).
    stacks = [('L3', -3), ('L2', -2), ('L1', -1), ('C', 0), ('R1', 1), ('R2', 2), ('R3', 3)]
    for tag, k in stacks:
        x = k * P['lamp_pitch']
        for j in range(3):
            add(orn, 'Goblet_%s_%02d' % (tag, j + 1), 'goblet', lathe(goblet_profile(), (x, 0, L['goblet_z0'][j]), SEG['round'], lobes=16, amp=.03), x_cm=x, z_cm=L['goblet_z0'][j])
        add(orn, 'Knop_%s' % tag, 'knop', lathe(knop_profile(P['knop_r'], P['knop_h'] / 2), (x, 0, L['knop_z0']), SEG['round'], lobes=12, amp=.04), x_cm=x, z_cm=L['knop_z0'])
        add(orn, 'Flower_%s' % tag, 'flower', lathe(flower_profile(), (x, 0, L['flower_z0']), SEG['flower'], lobes=6, amp=.12), x_cm=x, z_cm=L['flower_z0'])
        # Lamp cup plus wick nozzle: side lamps face the centre lamp, the centre lamp faces west (Rambam 3:8) = local -Y.
        direction = (0.0, -1.0, 0.0) if k == 0 else (-1.0 if k > 0 else 1.0, 0.0, 0.0)
        cup = lathe(lamp_profile(), (x, 0, L['lamp_z0']), SEG['round'])
        h = P['lamp_h']
        a = (x + direction[0] * 3.4, direction[1] * 3.4, L['lamp_z0'] + .55 * h)
        b = [x + direction[0] * (P['lamp_r'] + 1.4), direction[1] * (P['lamp_r'] + 1.4), L['lamp_z0'] + h + 1.0]
        for _ in range(4):   # end-cap ring top = b.z + r * sqrt(1 - t_z^2) must equal the 18-tefach height exactly
            t = norm(sub(b, a))
            b[2] = P['total_height'] - P['nozzle_r'] * math.sqrt(max(0.0, 1 - t[2] ** 2))
        b = tuple(b)
        nozzle = sweep([a, b], [P['nozzle_r'], P['nozzle_r']], 12)
        add('SM_MenorahV3_Lamps', 'Lamp_%s' % tag, 'lamp', cup, x_cm=x, z_cm=L['lamp_z0'], rim_z_cm=L['lamp_z0'] + h,
            wick_direction_local=list(direction), wick_source='Rambam Beit HaBechirah 3:8 (six toward the middle lamp, the middle lamp toward the west)')
        add('SM_MenorahV3_Lamps', 'WickNozzle_%s' % tag, 'wick_nozzle', nozzle, x_cm=x, top_z_cm=b[2] + P['nozzle_r'])

    # Six branches: nested quarter-ellipse arcs (L = local -X, R = local +X); root at the shaft axis inside the junction knop.
    for k, zj in enumerate(P['junction_z'], 1):
        x_tip = (4 - k) * P['lamp_pitch']            # junction 1 (lowest) feeds the outermost pair
        length = (math.pi / 2) * math.sqrt((x_tip ** 2 + (L['branch_top'] - zj) ** 2) / 2)
        steps = max(16, int(length / 1.6))
        for side, sign in (('L', -1), ('R', 1)):
            points, radii = branch_curve(sign * x_tip, zj, L['branch_top'], steps)
            add('SM_MenorahV3_Branches' + side, 'Branch_%s%d' % (side, 4 - k), 'branch', sweep(points, radii, SEG['tube']),
                root_z_cm=zj, tip_x_cm=sign * x_tip, top_z_cm=L['branch_top'], horizontal_semi_axis_cm=x_tip, vertical_semi_axis_cm=L['branch_top'] - zj,
                section_radius_cm=list(P['branch_r']), curve='quarter ellipse, horizontal tangent at the shaft, vertical tangent at the stack')

    # Three-step stone in front (local +Y = east): Rambam 3:11; book p. 252 (2) and diagram 22:23b. Sizes artistic.
    S = P['stone']
    apothem = P['base_tiers'][0][0] * math.cos(math.pi / 6)
    y0 = apothem + S['gap']
    for k in range(S['steps']):
        depth = S['tread'] * (S['steps'] - k)
        z0, z1 = k * S['rise'], (k + 1) * S['rise']
        hw = S['width'] / 2
        poly = [(-hw, y0), (hw, y0)]
        rc = S['corner']
        for cx, sgn in ((hw - rc, 1), (-hw + rc, -1)):
            for m in range(0, 7):
                ang = (math.pi / 2) * m / 6
                if sgn > 0:
                    poly.append((cx + rc * math.cos(ang), y0 + depth - rc + rc * math.sin(ang)))
                else:
                    poly.append((cx - rc * math.sin(ang), y0 + depth - rc + rc * math.cos(ang)))
        add('SM_MenorahV3_StepStone', 'Step_%02d' % (k + 1), 'stone_step', prism(poly, z0, z1), z_cm=[z0, z1], y_cm=[y0, y0 + depth], width_cm=S['width'])
    return meshes, register, L


# ---------------------------------------------------------------- export: OBJ adapter, readback, preview
def write_obj(name, parts, path):
    lines = ['# Original MenorahV3 %s; Unreal legacy OBJ adapter (Y reflected, winding reversed)' % name, 'o ' + name]
    index = 1
    allv = []
    checks = []
    for part_id, kind, (vertices, faces) in parts:
        vol = volume(vertices, faces)
        assert vol > 0 and closed(vertices, faces), part_id
        allv.extend(vertices)
        lines.append('g ' + part_id)
        for a, b, c in faces:
            p, q, r = [(vertices[i][0], -vertices[i][1], vertices[i][2]) for i in (a, c, b)]
            ab = [q[i] - p[i] for i in range(3)]
            ac = [r[i] - p[i] for i in range(3)]
            n = cross(ab, ac)
            length = math.sqrt(sum(x * x for x in ab))
            nl = math.sqrt(sum(x * x for x in n))
            assert nl > 1e-9 and length > 1e-9, 'degenerate triangle in ' + part_id
            for v in (p, q, r):
                lines.append('v %.7f %.7f %.7f' % v)
            for uv in ((0, 0), (length / 10, 0), (sum(ac[i] * ab[i] / length for i in range(3)) / 10, nl / length / 10)):
                lines.append('vt %.7f %.7f' % uv)
            for _ in range(3):
                lines.append('vn %.7f %.7f %.7f' % tuple(x / nl for x in n))
            lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
            index += 3
        checks.append(dict(name=part_id, kind=kind, triangles=len(faces), closed=True, volume_cm3=vol))
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn(p[i] for p in allv) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    return dict(name=name, file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), triangles=(index - 1) // 3,
                parts=len(parts), bounds_cm=bounds, minimum_part_signed_volume_cm3=min(c['volume_cm3'] for c in checks), part_checks=checks)


def readback(path, record):
    """Independent OBJ parse: counts, normals, UVs, Y-reflection round trip, file-space signed volume."""
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
        cr = cross([b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)])
        area = math.sqrt(sum(x * x for x in cr))
        assert area > 1e-9
        assert sum(cr[i] * normals[face[0][2]][i] for i in range(3)) / area > .99999
        ua, ub, uc = [uvs[f[1]] for f in face]
        assert abs((ub[0] - ua[0]) * (uc[1] - ua[1]) - (ub[1] - ua[1]) * (uc[0] - ua[0])) > 1e-12
    canonical = [(x, -y, z) for x, y, z in verts]
    bounds = {k: [fn(v[i] for v in canonical) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    error = max(abs(bounds[k][i] - record['bounds_cm'][k][i]) for k in bounds for i in range(3))
    assert error < 1e-4, error
    file_volume = volume(verts, [tuple(f[0] for f in face) for face in faces])
    assert file_volume > 0
    return dict(mesh=record['name'], triangles=len(faces), bounds_error_cm=error, file_space_signed_volume_cm3=file_volume, normals_and_uvs='PASS')


def render_views(meshes, path, views, size=(1800, 900), skip=None):
    """Software orthographic z-buffer render (verify_and_preview.py method); illustrative colours only."""
    W, H = size
    rgb = bytearray([24, 28, 33] * (W * H))
    zbuf = [-1e18] * (W * H)
    panel_w = W // len(views)
    light = norm((-0.35, 0.65, 0.68))
    for k, (yaw, pitch, scale, _label) in enumerate(views):
        hidden = (skip or {}).get(k, ())
        # Viewer stands in direction u (yaw 0 = local +Y = front/east; yaw 90 = local +X) at elevation pitch, looking at the model centre.
        u = (math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
        cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
        cam = (-u[0] * cp, -u[1] * cp, -sp)
        right = norm(cross((0.0, 0.0, 1.0), cam))
        up = cross(cam, right)
        x0 = k * panel_w + panel_w / 2
        base_y = H - 70 if pitch < 60 else H / 2
        for mesh, parts in meshes.items():
            if mesh in hidden:
                continue
            colour = (168, 160, 146) if 'Stone' in mesh else (214, 168, 78)
            for _pid, _kind, (v, faces) in parts:
                for a, b, c in faces:
                    pa, pb, pc = v[a], v[b], v[c]
                    n = cross(sub(pb, pa), sub(pc, pa))
                    ln = math.sqrt(sum(x * x for x in n)) or 1.0
                    if sum(n[i] * cam[i] for i in range(3)) > 0:
                        continue   # back face
                    shade = 0.38 + 0.62 * max(0.0, sum(n[i] * light[i] for i in range(3)) / ln)
                    col = bytes(min(255, int(x * shade)) for x in colour)
                    pts = []
                    for p in (pa, pb, pc):
                        sx = sum(p[i] * right[i] for i in range(3))
                        sz = sum(p[i] * up[i] for i in range(3))
                        d = -sum(p[i] * cam[i] for i in range(3))
                        pts.append((x0 + sx * scale, base_y - (sz - (55 if pitch >= 60 else 0)) * scale, d))
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
        for py in range(H):
            idx = py * W + k * panel_w
            rgb[idx * 3:idx * 3 + 3] = bytes((60, 64, 70))
        # 1 amah scale bar (50 cm) bottom-left of every panel
        for px in range(int(k * panel_w + 20), int(k * panel_w + 20 + AMAH * scale)):
            for py in (H - 24, H - 23, H - 22):
                rgb[(py * W + px) * 3:(py * W + px) * 3 + 3] = bytes((230, 230, 230))

    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    scan = b''.join(b'\x00' + rgb[y * W * 3:(y + 1) * W * 3] for y in range(H))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', W, H, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(scan, 9)) + chunk(b'IEND', b''))
    return [v[3] for v in views]


def dimension_table(L, meshes_records):
    S = P['stone']
    union = {k: [fn(m['bounds_cm'][k][i] for m in meshes_records if 'Stone' not in m['name']) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    rows = [
        ('overall height, floor to highest lamp detail (wick nozzle top)', union['max'][2], '18 tefachim', 'measured', 'Rambam Beit HaBechirah 3:10; Menachos 28b; book p. 252 (1) "the height of the Menorah is eighteen tefachim"; 8.333 cm tefach (50 cm amah)'),
        ('lamp rim height', L['lamp_rim'], None, 'derived', 'lamp cups nest 1.2 cm into the upper flowers; 18 tefachim measured to the nozzle tops (the Talmudic breakdown ends at the flowers; lamps ride on them)'),
        ('lamp count and row', 7, '7 in one line', 'measured', 'Shemos 25:37; Rambam 3:12 (line north-south; book diagram 22:23b)'),
        ('lamp pitch (centre to centre) / row span', [P['lamp_pitch'], 6 * P['lamp_pitch']], None, 'artistic (TI photo fit)', 'menorah-model-spec normalized lamp offsets 0.11-0.12 H apart -> 18 cm at H 150; the brief\'s 25 cm alternative gives a 150 cm span, wider than the TI silhouette (0.73-0.83 H)'),
        ('overall width of the fan (lamp rims)', union['max'][0] - union['min'][0], None, 'derived', '6 x pitch + lamp diameter; TI width/H range 0.73-0.83'),
        ('branch junction heights (knop centres)', P['junction_z'], 'tefachim 8-9, 10-11, 12-13', 'measured', 'Menachos 28b breakdown of the 18 tefachim (3 legs+flower, 2 plain, 1 goblet-knop-flower, 2 plain, 1 knop+2 branches, 1, 1 knop+2 branches, 1, 1 knop+2 branches, 2 plain, 3 goblets-knop-flower)'),
        ('branch curve: quarter ellipses, horizontal / vertical semi-axes (outer, middle, inner)', [[3 * P['lamp_pitch'], L['branch_top'] - P['junction_z'][0]], [2 * P['lamp_pitch'], L['branch_top'] - P['junction_z'][1]], [P['lamp_pitch'], L['branch_top'] - P['junction_z'][2]]], None, 'artistic', 'nested rounded U forms per the TI photograph (menorah-model-spec finished_photo_observations.branches); near-circular because the Menachos heights and the 18 cm pitch nearly coincide'),
        ('branch section radius, root -> tip', list(P['branch_r']), None, 'artistic', 'brief: swept circular sections tapering 3.0 -> 2.2 cm; the TI branches read as broad bands, not measured'),
        ('shaft radius, bottom -> top', list(P['shaft_r']), None, 'artistic', 'brief; "visibly substantial" per the photo audit'),
        ('goblets (gevi\'im): count', 22, '22 = 6 x 3 + 4', 'measured', 'Shemos 25:33-34; menorah-model-spec count_contract'),
        ('goblet height / bowl radius', [P['goblet_h'], 3.7], None, 'artistic', 'Rashi Shemos 25:31 (Alexandrian cups, narrow below, wide above); revolved almond/cup profile with 16 shallow flutes'),
        ('knops (kaftorim): count (3 junction + lower shaft + upper shaft + 6 branch)', 11, '11', 'measured', 'Shemos 25:33-35; Menachos 28b; count_contract'),
        ('knop size: flattened sphere radius / height; junction knops', [P['knop_r'], P['knop_h'], list(P['junction_knop'])], None, 'artistic', 'Rashi Shemos 25:31 (like Cretan apples); 12 shallow lobes'),
        ('flowers (perachim): count (base + lower shaft + upper shaft + 6 branch)', 9, '9', 'measured', 'Shemos 25:31-34; Menachos 28b (flower in the lowest 3 tefachim); count_contract'),
        ('flower height / rim radius (base flower x1.5)', [P['flower_h'], P['flower_r']], None, 'artistic', 'flared six-petal rim; the upper flower carries the lamp'),
        ('upper stack span (first goblet foot to flower rim)', L['upper_group_span'], 'upper 3 tefachim', 'measured (approx.)', 'Menachos 28b: three goblets, knop and flower in the top 3 tefachim; modelled span %.1f cm' % (L['upper_group_span'][1] - L['upper_group_span'][0])),
        ('lower shaft group span (goblet, knop, flower)', L['lower_group_span'], 'tefach 5-6', 'measured position, stretched height', 'Menachos 28b puts all three in one tefach; modelled over %.1f cm so the profiles stay readable (recorded deviation)' % (L['lower_group_span'][1] - L['lower_group_span'][0])),
        ('base: hexagonal stepped plinth, 3 tiers, circumradius / z (bottom -> top) + round collar', [list(t) for t in P['base_tiers']] + [P['collar'][-1][1]], 'yerech within 3 tefachim', 'artistic form, measured height band', 'TI photo: broad stepped polygonal plinth under a round collar (menorah-model-spec base observation); hexagon count and relief panels not established; Menachos 28b: legs and flower occupy the lowest 3 tefachim'),
        ('lamps: open oil cups with a wick nozzle; radius / height', [P['lamp_r'], P['lamp_h']], None, 'artistic', 'Shemos 25:37; TI display shows covered forms (unverified); no flames, no shamash'),
        ('wick directions', 'six toward the centre lamp, centre lamp toward the west (local -Y)', None, 'measured', 'Rambam Beit HaBechirah 3:8; book-keilim-review item 2'),
        ('tending stone: three steps in front (east) of the menorah', [S['steps'], S['rise'], S['tread'], S['width']], '3 steps; 2-tefach rise', 'measured count/position, artistic sizes', 'Rambam 3:11; book p. 252 (2) "before the Menorah there is a stone with three steps on which the Kohen stands"; diagram 22:23b shows it east of the menorah; rise 16.7 cm, tread 30 cm, width 90 cm, 10 cm gap to the plinth are artistic'),
        ('orientation: lamp row north-south, stone east', 'yaw -90 in placement (local +X -> north, local +Y -> east)', None, 'measured', 'Rambam 3:12 (book diagram 22:23b); Rashi east-west alternative (22:23a) NOT modelled'),
        ('placement: centre X -5330, nearest lamp tip 125 cm (2.5 amot) from the south wall face Y +500', None, '2.5 amot', 'interpretation', 'book p. 252 (5) "in the south of the Heikhal, 2.5 amot from the southern wall"; measured to the tips as in the vessels release; X kept from the current RELEASE_Menorah'),
    ]
    return [dict(item=i, value_cm=v, halachic=h, kind=k, source=s) for i, v, h, k, s in rows]


def export(force=False):
    if (OUT / 'geometry-manifest.json').exists() and not force:
        raise SystemExit('Frozen generation preserved: %s exists (use --force to regenerate)' % (OUT / 'geometry-manifest.json'))
    OUT.mkdir(parents=True, exist_ok=True)
    meshes, register, L = geometry()
    counts = {}
    for entry in register:
        counts[entry['kind']] = counts.get(entry['kind'], 0) + 1
    expected = dict(goblet=22, knop=11, flower=9, lamp=7, wick_nozzle=7, branch=6, stone_step=3)
    for kind, n in expected.items():
        assert counts.get(kind) == n, (kind, counts.get(kind), n)
    records, checks = [], []
    for name, parts in meshes.items():
        record = write_obj(name, parts, OUT / (name + '.obj'))
        record['material_role'] = 'stone' if 'Stone' in name else 'gold'
        record['collision'] = 'BlockAll' if name in ('SM_MenorahV3_Base', 'SM_MenorahV3_StepStone') else 'NoCollision'
        checks.append(readback(OUT / record['file'], record))
        records.append(record)
    total = sum(m['triangles'] for m in records)
    assert total < 250000, total
    menorah_records = [m for m in records if 'Stone' not in m['name']]
    union = {k: [fn(m['bounds_cm'][k][i] for m in menorah_records) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    preview = render_views(meshes, OUT / 'menorah-v3-preview.png', [
        (0, 0, 4.6, 'front elevation: looking west from the east (north on the right); tending stone hidden so the plinth is visible'),
        (-90, 0, 4.6, 'side elevation: looking north from the south (east and the tending stone on the right)'),
        (-40, 30, 3.6, 'oblique from the south-east above'),
    ], (2100, 860), skip={0: ('SM_MenorahV3_StepStone',)})
    manifest = dict(
        status='OFFLINE_VALIDATED_NATIVE_AND_VISUAL_PENDING', namespace=DEST, amah_cm=AMAH, tefach_cm=TEFACH,
        script='Scripts/create_menorah_v3.py', script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        reference_spec='SourceAssets/vessels-review/menorah-model-spec.json',
        reference_spec_sha256=hashlib.sha256((ROOT / 'SourceAssets/vessels-review/menorah-model-spec.json').read_bytes()).hexdigest(),
        convention='Canonical XYZ Unreal cm: local X = lamp row (fan axis; +X = north after the placement yaw -90), local +Y = front (east; '
                   'the tending stone side), Z up, origin at the centre of the base contact plane on the floor; every part shares this pivot. '
                   'OBJ files carry Y reflected and winding reversed for the legacy OBJ importer (ShulchanV2 / DoorsParochesV1 adapter); the '
                   'importer reflects Y back, so imported bounds must equal bounds_cm and UE signed volumes must be positive. Per-triangle '
                   'normals and non-degenerate planar UV charts; no images, no scanned or traced geometry.',
        claims='Original approximate study guided by the Torah/Talmud counts and positions and by the Temple Institute photograph\'s silhouette; '
               'not a measured TI replica, not a rabbinically certified vessel (menorah-model-spec claims_allowed / claims_not_allowed).',
        parameters=P, layout=L,
        menorah_bounds_cm=union, half_span_x_cm=max(-union['min'][0], union['max'][0]),
        counts=counts, count_contract=dict(lamps=7, side_branches=6, goblets_total=22, goblets_each_side_branch=3, goblets_central_shaft=4,
                                           knops_total=11, knops_upper_groups=7, knops_branch_junctions=3, knops_lower_central=1,
                                           flowers_total=9, flowers_upper_groups=7, flowers_lower_central=2, source='Shemos 25:31-40; menorah-model-spec count_contract'),
        ornaments=register,
        dimensions=dimension_table(L, records),
        artistic_summary='Lamp pitch, branch section, shaft radius, ornament profiles (flutes, lobes, petals), hexagon/tier sizes, collar, lamp cup and '
                         'nozzle shape, stone sizes and the stretched lower group are artistic. Counts, the 18-tefach height, the junction heights, '
                         'the lamp row orientation, the wick directions and the stone\'s existence/position follow the cited sources.',
        not_modelled=['Base relief panels and ornament motifs (menorah-model-spec: unreadable at the available resolution)',
                      'TI broad-band branch section (circular sections used per the brief)', 'Flames, oil, wicks, service tools, shamash',
                      'Rashi east-west orientation (book 22:23a)'],
        total_triangles=total, meshes=records, readback=checks,
        previews={'menorah-v3-preview.png': preview},
        preview_limit='Software orthographic source preview with illustrative gold/stone colours; not a native render or material acceptance.',
    )
    (OUT / 'geometry-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    if '--export' in sys.argv:
        result = export(force='--force' in sys.argv)
        print(json.dumps(dict(status=result['status'], total_triangles=result['total_triangles'], counts=result['counts'],
                              menorah_bounds_cm=result['menorah_bounds_cm'], layout=result['layout'],
                              meshes=[(m['name'], m['triangles'], m['bounds_cm']) for m in result['meshes']]), indent=2))
    else:
        raise SystemExit('Use --export (offline OBJ + manifest + preview); native import is Scripts/release_import_menorah_v3.py')

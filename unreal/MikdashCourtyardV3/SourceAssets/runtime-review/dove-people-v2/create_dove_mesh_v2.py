"""Original stylized white dove, version 2: three OBJ meshes in the project's keilim OBJ
adapter convention (per-triangle vertices, Y reflected and winding reversed in the file so
the FbxFactory OBJ path lands on the canonical bounds; vt/vn per vertex; `g` groups).

  SM_DoveBodyV2.obj       body ellipsoid, breast, neck, head, eyes, beak, fanned tail
  SM_DoveWingLeftV2.obj   left wing, origin at the shoulder pivot, spanning -Y
  SM_DoveWingRightV2.obj  right wing, mirror of the left, spanning +Y

Colour: two material groups per file, `DoveWhite` and `DoveGrey` (grey wing tips, eyes and
beak). The importer keeps these as two material slots; Scripts/release_dove_people_v2.py
assigns the two flat materials by slot name. The OBJ `v x y z r g b` vertex-colour extension
is deliberately NOT written because FBX-SDK OBJ reader tolerance for it is unverified here;
per-part colours are recorded in editable-assembly.json instead.

Bird-local axes: +X forward (beak), +Y right, +Z up; centimetres; about twice life size so
the following camera at 230 cm reads the silhouette. Nothing here is measured wildlife
anatomy or a rigged skeletal asset: wings flap as rigid pieces around their pivots.

Offline only:  python create_dove_mesh_v2.py --export   (refuses to overwrite DoveV2/)
"""
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOLDER = HERE / 'DoveV2'
WHITE, GREY = 'DoveWhite', 'DoveGrey'
COLOURS = {WHITE: [0.92, 0.92, 0.90], GREY: [0.38, 0.39, 0.42]}


def orient(mesh):
    v, f = mesh
    volume = sum((v[a][0] * (v[b][1] * v[c][2] - v[b][2] * v[c][1]) + v[a][1] * (v[b][2] * v[c][0] - v[b][0] * v[c][2])
                  + v[a][2] * (v[b][0] * v[c][1] - v[b][1] * v[c][0])) / 6 for a, b, c in f)
    if volume < 0:
        f = [(a, c, b) for a, b, c in f]
    return v, f


def lathe(profile, center=(0, 0, 0), segments=32):
    """Closed profile (radius, z) from lower pole to upper pole; distinct pole vertices."""
    vertices = []; rings = []; faces = []
    for radius, z in profile:
        ring = []
        for i in range(1 if radius == 0 else segments):
            angle = i * math.tau / segments
            ring.append(len(vertices))
            vertices.append((center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle), center[2] + z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if len(a) == 1 and len(b) > 1: faces.append((a[0], b[j], b[i]))
            elif len(b) == 1 and len(a) > 1: faces.append((a[i], a[j], b[0]))
            elif len(a) > 1 and len(b) > 1: faces.extend([(a[i], a[j], b[j]), (a[i], b[j], b[i])])
    return vertices, faces


def ellipsoid(center, radii, pitch=0, yaw=0, segments=32, rings=16):
    profile = [(math.sin(math.pi * i / rings), -math.cos(math.pi * i / rings)) for i in range(rings + 1)]
    profile[0] = (0, -1); profile[-1] = (0, 1)
    v, f = lathe(profile, segments=segments)
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    out = []
    for x, y, z in v:
        x *= radii[0]; y *= radii[1]; z *= radii[2]
        x, z = cp * x + sp * z, -sp * x + cp * z          # pitch about Y (nose down positive)
        x, y = cy * x - sy * y, sy * x + cy * y          # yaw about Z
        out.append((center[0] + x, center[1] + y, center[2] + z))
    return orient((out, f))


def cone(base, tip, radius, segments=24):
    """Closed cone from a circular base (perpendicular to base->tip) to a tip."""
    ax = [tip[i] - base[i] for i in range(3)]; length = math.sqrt(sum(a * a for a in ax))
    ax = [a / length for a in ax]
    ref = (0, 0, 1) if abs(ax[2]) < 0.9 else (0, 1, 0)
    u = [ax[1] * ref[2] - ax[2] * ref[1], ax[2] * ref[0] - ax[0] * ref[2], ax[0] * ref[1] - ax[1] * ref[0]]
    ul = math.sqrt(sum(q * q for q in u)); u = [q / ul for q in u]
    w = [ax[1] * u[2] - ax[2] * u[1], ax[2] * u[0] - ax[0] * u[2], ax[0] * u[1] - ax[1] * u[0]]
    vertices = [tuple(base), tuple(tip)]; faces = []
    ring = []
    for i in range(segments):
        a = i * math.tau / segments
        ring.append(len(vertices))
        vertices.append(tuple(base[k] + radius * (math.cos(a) * u[k] + math.sin(a) * w[k]) for k in range(3)))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((0, ring[j], ring[i])); faces.append((1, ring[i], ring[j]))
    return orient((vertices, faces))


def feather(start, end, width, thickness, camber=1.5, rings=14, sides=10):
    """Closed lenticular feather with distinct poles; a slight upward camber along its length."""
    dx, dy, dz = (end[i] - start[i] for i in range(3)); length = math.hypot(dx, dy)
    nx, ny = (-dy / length, dx / length) if length > 1e-9 else (0.0, 1.0)
    vertices = []; ring_ids = []; faces = []
    for i in range(rings + 1):
        t = i / rings; ring = []
        r = math.sin(math.pi * t) ** 0.6 if i not in (0, rings) else 0
        for j in range(1 if r == 0 else sides):
            a = j * math.tau / sides
            ring.append(len(vertices))
            vertices.append((start[0] + dx * t + nx * width * r * math.cos(a),
                             start[1] + dy * t + ny * width * r * math.cos(a),
                             start[2] + dz * t + camber * math.sin(math.pi * t) + thickness * r * math.sin(a)))
        ring_ids.append(ring)
    for a, b in zip(ring_ids, ring_ids[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            if len(a) == 1: faces.append((a[0], b[j], b[i]))
            elif len(b) == 1: faces.append((a[i], a[j], b[0]))
            else: faces.extend([(a[i], a[j], b[j]), (a[i], b[j], b[i])])
    return orient((vertices, faces))


def lerp3(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def body_parts():
    parts = []
    add = lambda name, material, mesh: parts.append(dict(name=name, material=material, mesh=mesh))
    add('Body', WHITE, ellipsoid((0, 0, 0), (24, 10, 11), pitch=4))
    add('Breast', WHITE, ellipsoid((14, 0, -1), (13, 9.5, 10.5)))
    add('Neck', WHITE, ellipsoid((22, 0, 7), (9, 6.5, 8), pitch=-25))
    add('Head', WHITE, ellipsoid((31, 0, 13), (7.5, 6.5, 7)))
    add('Beak', GREY, cone((37.5, 0, 12.5), (46, 0, 11.2), 1.9))
    for side in (-1, 1):
        add('Eye%+d' % side, GREY, ellipsoid((34, side * 6.2, 14.5), (1.3, 0.7, 1.3), segments=16, rings=8))
    # Fanned tail: seven feathers from the rump, the outer ones splayed and slightly lower.
    for i in range(7):
        s = (i - 3) / 3.0
        yaw = s * 24.0
        root = (-18, s * 2.5, 1.5)
        tip = (-18 - 32 * math.cos(math.radians(yaw)), s * 2.5 - 32 * math.sin(math.radians(yaw)) * -1, -1.5 - abs(s) * 1.5)
        add('Tail%d' % i, WHITE if abs(s) < 0.9 else GREY, feather(root, tip, 4.2, 0.7, camber=0.8))
    return parts


def wing_parts(side):
    """Wing in pivot-local space: origin at the shoulder; `side` -1 spans -Y (left), +1 spans +Y."""
    parts = []
    add = lambda name, material, mesh: parts.append(dict(name=name, material=material, mesh=mesh))
    s = side
    # Arm and covert slab: an inclined ellipsoid from the shoulder out to the wrist.
    add('Coverts', WHITE, ellipsoid((-3, s * 22, 0.5), (14, 24, 2.2), yaw=s * -6))
    add('Wrist', WHITE, ellipsoid((-6, s * 44, 0.8), (9, 8, 1.8)))
    # Secondaries fan backward from the arm; primaries sweep out from the wrist.
    for i in range(6):
        t = i / 5.0
        root = (-4 - 6 * t, s * (12 + 28 * t), 0.2)
        tip = (-26 - 8 * t, s * (16 + 30 * t), -0.6)
        add('Secondary%d' % i, WHITE, feather(root, tip, 3.6, 0.55, camber=0.6))
    for i in range(8):
        t = i / 7.0
        root = (-8 + 2 * t, s * (44 + 3 * t), 0.6)
        angle = math.radians(12 + 46 * t)                      # sweep back progressively
        span = 46 - 12 * t
        tip = (root[0] - span * math.sin(angle), root[1] + s * span * math.cos(angle), 0.4 + 2.0 * t)
        mid = lerp3(root, tip, 0.58)
        add('Primary%dBase' % i, WHITE, feather(root, mid, 3.3 - 0.6 * t, 0.5, camber=0.4))
        add('Primary%dTip' % i, GREY if i >= 2 else WHITE, feather(mid, tip, 3.1 - 0.6 * t, 0.45, camber=0.5))
    return parts


def write_obj(path, name, parts):
    lines = ['# Original stylized white dove V2; bird-local cm; keilim OBJ adapter convention', 'o ' + name]
    index = 1; report_parts = []; all_vertices = []; total = 0
    for part in parts:
        vertices, faces = part['mesh']; all_vertices.extend(vertices)
        keys = [tuple(round(x, 6) for x in v) for v in vertices]; edges = {}; volume = 0
        lines.append('g ' + part['name']); lines.append('usemtl ' + part['material'])
        for a, b, c in faces:
            va, vb, vc = vertices[a], vertices[b], vertices[c]
            volume += sum(va[i] * [vb[1] * vc[2] - vb[2] * vc[1], vb[2] * vc[0] - vb[0] * vc[2], vb[0] * vc[1] - vb[1] * vc[0]][i] for i in range(3)) / 6
            for i, j in [(a, b), (b, c), (c, a)]:
                edge = tuple(sorted([keys[i], keys[j]])); edges[edge] = edges.get(edge, 0) + 1
            adapted = [(v[0], -v[1], v[2]) for v in (va, vc, vb)]
            aa, bb, cc = adapted; ab = [bb[i] - aa[i] for i in range(3)]; ac = [cc[i] - aa[i] for i in range(3)]
            n = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]]
            length = math.sqrt(sum(q * q for q in ab)); area = math.sqrt(sum(q * q for q in n))
            if area <= 1e-9:
                continue  # degenerate pole sliver: skipped, counted below
            normal = [q / area for q in n]
            uv = [(0, 0), (length / 10, 0), (sum(ac[i] * ab[i] / length for i in range(3)) / 10, area / length / 10)]
            for v in adapted: lines.append('v %.6f %.6f %.6f' % v)
            for v in uv: lines.append('vt %.6f %.6f' % v)
            for _ in range(3): lines.append('vn %.6f %.6f %.6f' % tuple(normal))
            lines.append('f ' + ' '.join('%d/%d/%d' % (i, i, i) for i in range(index, index + 3))); index += 3
        assert volume > 0 and all(count == 2 for count in edges.values()), part['name']
        written = (index - 1) // 3 - total
        report_parts.append(dict(name=part['name'], material=part['material'], colour=COLOURS[part['material']],
                                 triangles=written, signed_volume_cm3=volume, closed_welded_edges=True))
        total += written
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn(v[i] for v in all_vertices) for i in range(3)] for k, fn in [('min', min), ('max', max)]}
    return dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), triangles=total,
                bounds_cm=bounds, materials=sorted({p['material'] for p in parts}), parts=report_parts)


def export():
    if FOLDER.exists():
        raise RuntimeError('Existing DoveV2 preserved; author a new version folder for revisions')
    FOLDER.mkdir(parents=True)
    body = body_parts(); left = wing_parts(-1); right = wing_parts(+1)
    manifest = dict(status='offline_geometry_validated_native_import_pending',
                    convention='keilim OBJ adapter: per-triangle vertices, file Y = -canonical Y, winding reversed; importer reflects back; bounds must match canonical within 0.05 cm',
                    axes='bird-local: +X forward (beak), +Y right, +Z up; cm; wings in shoulder-pivot space',
                    shoulder_pivots_cm=dict(left=[2, -7, 6], right=[2, 7, 6]),
                    wing_animation='rigid wing pieces rotate about the pivot X axis: left roll -angle, right roll +angle; 35 deg sine, 4 Hz cruise, 6 Hz climb, level glide when diving (DoveFlightMath.h)',
                    colour_slots=COLOURS, vertex_colours='not written; see module docstring',
                    meshes={}, source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    limitations=['Stylized original, roughly twice life size; not measured anatomy',
                                 'Rigid feather pieces overlap at joins; not a skinned or watertight single shell',
                                 'Grey tips are a second material slot, not a texture',
                                 'No native import, render, cook or packaged acceptance from offline checks'])
    for name, parts in (('SM_DoveBodyV2', body), ('SM_DoveWingLeftV2', left), ('SM_DoveWingRightV2', right)):
        manifest['meshes'][name] = write_obj(FOLDER / (name + '.obj'), name, parts)
    # Symmetry: the right wing must mirror the left in Y exactly.
    lb, rb = manifest['meshes']['SM_DoveWingLeftV2']['bounds_cm'], manifest['meshes']['SM_DoveWingRightV2']['bounds_cm']
    assert abs(lb['min'][1] + rb['max'][1]) < 1e-6 and abs(lb['max'][1] + rb['min'][1]) < 1e-6
    assert lb['min'][0] == rb['min'][0] and lb['max'][2] == rb['max'][2]
    span = rb['max'][1] + manifest['shoulder_pivots_cm']['right'][1] - (lb['min'][1] + manifest['shoulder_pivots_cm']['left'][1])
    manifest['wingspan_cm'] = span; manifest['body_length_cm'] = manifest['meshes']['SM_DoveBodyV2']['bounds_cm']['max'][0] - manifest['meshes']['SM_DoveBodyV2']['bounds_cm']['min'][0]
    manifest['total_triangles'] = sum(m['triangles'] for m in manifest['meshes'].values())
    assert manifest['total_triangles'] < 60000
    editable = {name: [dict(name=p['name'], material=p['material'], colour=COLOURS[p['material']], mesh=p['mesh']) for p in parts]
                for name, parts in (('SM_DoveBodyV2', body), ('SM_DoveWingLeftV2', left), ('SM_DoveWingRightV2', right))}
    (FOLDER / 'editable-assembly.json').write_text(json.dumps(editable, separators=(',', ':')) + '\n')
    (FOLDER / 'geometry-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    if '--export' not in sys.argv:
        raise SystemExit(__doc__)
    result = export()
    print(json.dumps({k: result[k] for k in ('total_triangles', 'wingspan_cm', 'body_length_cm')}))
    for name, mesh in result['meshes'].items():
        print(name, mesh['triangles'], mesh['bounds_cm'])

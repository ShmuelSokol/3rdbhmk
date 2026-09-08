"""VehiclesV3: offline low-poly road and rail bodies for the instanced transit layer.

AUTHORED_OFFLINE_SOURCE. This module never imports 'unreal', never touches Content/,
never opens a map and never places an actor. It writes OBJ files, an editable mesh JSON
per assembly, livery//glass texture PNGs and a manifest under

    SourceAssets/transit-review/VehiclesV3/

The native half -- import, material creation, LOD reduction, actor configuration -- is
Scripts/release_transit_v3.py, driven by Scripts/release_transit_v3.spec.json.

CONVENTIONS
-----------
Centimetres throughout; no scaling at any stage. Vehicle local frame is +X forward,
+Y the DRIVER'S RIGHT, +Z up, with Z 0 at tyre contact (road vehicles) or railhead
(tram). +Y is right, not left: AMikdashTransit poses every vehicle yaw-only and offsets
it with TransitMath::RightFromYaw, which is FRotator(0, yaw, 0).GetRightVector() and
therefore local +Y. Israel drives on the right, so the kerb, the bus doors, the shelter
and the boarding point the actor broadcasts are all on +Y. Getting this backwards puts
the doors in the middle of the road, and nothing else would report it.

Every SM_*.obj is written through the legacy Unreal OBJ importer adapter proven on this
project: Y reflected and triangle winding reversed, so the importer reflects Y back and
the mesh arrives in canonical Unreal XYZ. The convention is recorded in
SourceAssets/sanctuary-detail/DoorsParochesV1/geometry-manifest.json. Never apply a
second reflection or unit conversion. A <label>-canonical.obj twin is written WITHOUT the
adapter so a human can diff real coordinates.

Geometry is split by material group into separate OBJ files, one material slot each,
because AMikdashTransit drives exactly four groups per body -- Paint, Glass, Dark, Lens --
and every extra group is another HISM component and another transform write per vehicle
per update.

WHAT IS FROM REAL REFERENCE AND WHAT IS GENERIC
-----------------------------------------------
From real reference (dimensions only):
  * The tram is proportioned as the articulated low-floor vehicle that works the
    Jerusalem Light Rail red line: five modules, 32.5 m over couplers, 2.40 m wide,
    3.35 m to the roof, 1435 mm standard gauge, doors on both sides.
  * The bus is a standard 12.0 m rigid low-floor single-decker, 2.55 m wide, 3.20 m
    high -- the Egged city-bus envelope.
  * The four car silhouettes use ordinary European segment dimensions: B-segment
    hatchback 4.05 m, D-segment saloon 4.70 m, compact crossover 4.35 m, small panel
    van 4.90 m.
GENERIC, invented here, and not a reproduction of anything:
  * Every body shape is a simplified prism silhouette. No manufacturer's bodywork,
    grille, lamp signature, badge, wheel design or trim is reproduced.
  * Liveries are flat colour fields plus a stripe. The tram's light grey and the bus's
    white-and-green are used AS COLOUR only; no operator logo, wordmark, route number,
    destination text or livery artwork of any kind is drawn. Destination blinds are
    blank black panels.
  * Interiors, driver, seats, pantograph detail, mirrors and number plates are omitted.
    These are seen at 50 m and beyond.

LIMITS (also written into the manifest)
---------------------------------------
  * Placeholder planar UVs only; no lightmap UVs and no unwrap. The livery PNGs are
    authored to the same planar parameterisation and previewed through it, but they are
    tiling colour fields, not a fitted skin.
  * LOD0 only is authored here. The reduction ladder is declared in the manifest and
    built in the engine by release_transit_v3.py; nothing is decimated in Python.
  * No collision is authored. These are HISM instances; AMikdashTransit sets
    NoCollision on every component.
  * Triangle counts are deliberately small. Do not treat these as hero assets.

Usage (offline only):
  "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" \
      Scripts/create_vehicles.py --export [--force] [--no-preview]
"""
import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets' / 'transit-review' / 'VehiclesV3'
TEXTURES = OUT / 'textures'
DEST = '/Game/MikdashV3/TransitV3/Vehicles'
MANIFEST_PATH = OUT / 'geometry-manifest.json'
TRIANGLE_BUDGET = 6000

# The four material groups AMikdashTransit drives, and nothing else.
GROUPS = ('Paint', 'Glass', 'Dark', 'Lens')

# base linear RGB, metallic, roughness
PALETTE = {
    'Paint': ([0.72, 0.73, 0.74], 0.10, 0.34),
    'Glass': ([0.10, 0.13, 0.15], 0.00, 0.07),
    'Dark': ([0.055, 0.058, 0.062], 0.00, 0.72),
    'Lens': ([0.85, 0.80, 0.62], 0.00, 0.18),
}

# =====================================================================================
# 1. Geometry primitives (all closed, outward-wound)
# =====================================================================================


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def signed_volume(vertices, triangles):
    """(1/6) sum a . (b x c). Positive for an outward-wound closed solid."""
    return sum(dot(vertices[a], cross(vertices[b], vertices[c])) for a, b, c in triangles) / 6.0


def orient(vertices, triangles):
    """Flip the winding when the signed volume came out negative. No epsilon: the sign
    is the whole question, and a solid with zero volume is caught by check_parts."""
    if signed_volume(vertices, triangles) > 0.0:
        return vertices, triangles
    return vertices, [(a, c, b) for a, b, c in triangles]


def prism(polygon, depth, axis, offset=(0.0, 0.0, 0.0)):
    """Extrude a 2D polygon by +/- depth/2 along `axis` (0=X, 1=Y, 2=Z).

    The polygon is given in the two remaining axes, in order; winding is fixed by
    orient() afterwards so the caller never has to think about it."""
    other = [i for i in range(3) if i != axis]
    vertices = []
    for side in (-1, 1):
        for point in polygon:
            vertex = [0.0, 0.0, 0.0]
            vertex[axis] = side * depth / 2.0
            vertex[other[0]] = point[0]
            vertex[other[1]] = point[1]
            vertices.append(tuple(vertex[i] + offset[i] for i in range(3)))
    n = len(polygon)
    triangles = []
    # Cap winding must AGREE with the side quads below, or the solid is not consistently
    # oriented and orient() cannot repair it -- it can only flip a whole solid, never one
    # face. The self-test on a 100 cm cube is what catches getting this backwards.
    for i in range(1, n - 1):
        triangles.append((0, i + 1, i))
        triangles.append((n, n + i, n + i + 1))
    for i in range(n):
        j = (i + 1) % n
        triangles.append((i, j, n + j))
        triangles.append((i, n + j, n + i))
    return orient(vertices, triangles)


def box(centre, size, bevel=0.0):
    """Axis-aligned box; a non-zero bevel chamfers the four long edges in XY, which is
    what keeps a flat-shaded body from reading as a shoebox at grazing angles."""
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    b = min(bevel, hx * 0.9, hy * 0.9)
    if b <= 0.0:
        polygon = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    else:
        polygon = [(-hx + b, -hy), (hx - b, -hy), (hx, -hy + b), (hx, hy - b),
                   (hx - b, hy), (-hx + b, hy), (-hx, hy - b), (-hx, -hy + b)]
    return prism(polygon, size[2], 2, (centre[0], centre[1], centre[2] - hz + hz))


def taper(profile_front, profile_rear, x_front, x_rear):
    """Loft between two XZ profiles at two X stations: the one shape that makes a car
    silhouette out of eight numbers. Both profiles must have the same point count."""
    assert len(profile_front) == len(profile_rear)
    n = len(profile_front)
    vertices = [(x_rear, p[0], p[1]) for p in profile_rear] + [(x_front, p[0], p[1]) for p in profile_front]
    triangles = []
    # Cap winding must AGREE with the side quads below, or the solid is not consistently
    # oriented and orient() cannot repair it -- it can only flip a whole solid, never one
    # face. The self-test on a 100 cm cube is what catches getting this backwards.
    for i in range(1, n - 1):
        triangles.append((0, i + 1, i))
        triangles.append((n, n + i, n + i + 1))
    for i in range(n):
        j = (i + 1) % n
        triangles.append((i, j, n + j))
        triangles.append((i, n + j, n + i))
    return orient(vertices, triangles)


def wheel(centre, radius, width, segments=10):
    """Low-poly tyre about Y. Ten segments is the point where the silhouette stops
    reading as a polygon at the distances these are seen from."""
    vertices = []
    for side in (-1, 1):
        for j in range(segments):
            angle = j * math.tau / segments
            vertices.append((centre[0] + radius * math.cos(angle), centre[1] + side * width / 2.0,
                             centre[2] + radius * math.sin(angle)))
    triangles = []
    for j in range(1, segments - 1):
        triangles.append((0, j + 1, j))
        triangles.append((segments, segments + j, segments + j + 1))
    for j in range(segments):
        k = (j + 1) % segments
        triangles.append((j, k, segments + k))
        triangles.append((j, segments + k, segments + j))
    return orient(vertices, triangles)


# =====================================================================================
# 2. Part accumulation and validation
# =====================================================================================


def builders(parts):
    def add(name, group, mesh):
        assert group in GROUPS, group
        parts.append(dict(name=name, group=group, vertices=mesh[0], triangles=mesh[1]))

    def b(name, group, centre, size, bevel=0.0):
        add(name, group, box(centre, size, bevel))

    def w(name, centre, radius, width, segments=10):
        add(name, 'Dark', wheel(centre, radius, width, segments))

    return add, b, w


def check_parts(label, parts):
    """Every part unique, edge-manifold, non-degenerate and positively wound.

    Edges are counted by vertex index, not by coordinate: these parts are built one
    solid at a time and never welded, so an index-level count is exact here."""
    names = set()
    min_area = 1e30
    min_volume = 1e30
    for part in parts:
        assert part['name'] not in names, '%s duplicate part %s' % (label, part['name'])
        names.add(part['name'])
        v = part['vertices']
        edges = {}
        for a, b, c in part['triangles']:
            ab = [v[b][i] - v[a][i] for i in range(3)]
            ac = [v[c][i] - v[a][i] for i in range(3)]
            n = cross(ab, ac)
            area = math.sqrt(dot(n, n)) / 2.0
            assert area > 1e-8, '%s degenerate triangle in %s' % (label, part['name'])
            min_area = min(min_area, area)
            for i, j in ((a, b), (b, c), (c, a)):
                key = tuple(sorted((i, j)))
                edges[key] = edges.get(key, 0) + 1
        assert all(count == 2 for count in edges.values()), '%s not edge-manifold: %s' % (label, part['name'])
        volume = signed_volume(v, part['triangles'])
        assert volume > 0.0, '%s inverted part %s (volume %.3f)' % (label, part['name'], volume)
        assert all(math.isfinite(c) for point in v for c in point), '%s non-finite vertex in %s' % (label, part['name'])
        min_volume = min(min_volume, volume)
    points = [p for part in parts for p in part['vertices']]
    return dict(parts=len(parts), triangles=sum(len(p['triangles']) for p in parts),
                closed_parts=True, min_triangle_area_cm2=round(min_area, 6),
                min_signed_volume_cm3=round(min_volume, 3),
                bounds_cm=dict(min=[round(min(p[i] for p in points), 3) for i in range(3)],
                               max=[round(max(p[i] for p in points), 3) for i in range(3)]),
                groups={g: sum(len(p['triangles']) for p in parts if p['group'] == g) for g in GROUPS})


# =====================================================================================
# 3. OBJ writing -- the legacy importer adapter lives here and nowhere else
# =====================================================================================

OBJ_ADAPTER_NOTE = ('Unreal legacy OBJ adapter: canonical vertices are UE cm; this file is '
                    'written with Y reflected and triangle winding reversed, and the importer '
                    'reflects Y back. Reflection and winding reversal each negate the signed '
                    'volume, so the two cancel and the file-space signed volume stays POSITIVE; '
                    'the self-test asserts that on a unit cube rather than asserting a sign from '
                    'memory. Never apply a second reflection or unit conversion.')


def write_obj(path, name, parts, native, uv_scale=100.0):
    """One OBJ. native=True applies the adapter; native=False writes canonical UE XYZ.

    Three unshared vertices, three UVs and three identical normals per triangle: these
    bodies are flat-shaded panels and sharing would smooth the creases away. The UV is a
    per-triangle local basis at uv_scale cm to the UV unit -- a tiling parameterisation,
    not an unwrap."""
    lines = ['# VehiclesV3 %s; centimetres; %s'
             % (name, OBJ_ADAPTER_NOTE if native else 'canonical Unreal XYZ, no adapter'),
             'o ' + name]
    index = 1
    for part in parts:
        lines.append('g ' + part['name'])
        lines.append('s off')
        for face in part['triangles']:
            source = [part['vertices'][i] for i in (face[0], face[2], face[1])] if native \
                else [part['vertices'][i] for i in face]
            p, q, r = [(v[0], -v[1], v[2]) for v in source] if native else source
            ab = [q[i] - p[i] for i in range(3)]
            ac = [r[i] - p[i] for i in range(3)]
            n = cross(ab, ac)
            nl = math.sqrt(dot(n, n))
            length = math.sqrt(dot(ab, ab))
            assert nl > 1e-8 and length > 1e-8, 'degenerate triangle in ' + part['name']
            for vertex in (p, q, r):
                lines.append('v %.6f %.6f %.6f' % vertex)
            for uv in ((0.0, 0.0), (length / uv_scale, 0.0),
                       (dot(ac, ab) / length / uv_scale, nl / length / uv_scale)):
                lines.append('vt %.6f %.6f' % uv)
            for _ in range(3):
                lines.append('vn %.6f %.6f %.6f' % tuple(x / nl for x in n))
            lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
            index += 3
    with path.open('w', encoding='ascii', newline='\n') as handle:
        handle.write('\n'.join(lines) + '\n')
    return (index - 1) // 3


def readback(path, expected_triangles, expected_bounds):
    """Re-parse the file just written and re-derive everything from it.

    Returns the FILE-SPACE signed volume rather than asserting a remembered sign, and
    checks the canonical bounds recovered by undoing the adapter."""
    vertices, normals, faces = [], [], []
    for line in path.read_text(encoding='ascii').splitlines():
        if line.startswith('v '):
            vertices.append(tuple(float(x) for x in line.split()[1:4]))
        elif line.startswith('vn '):
            normals.append(tuple(float(x) for x in line.split()[1:4]))
        elif line.startswith('f '):
            faces.append([int(part.split('/')[0]) - 1 for part in line.split()[1:4]])
    assert len(faces) == expected_triangles, '%s: %d faces, expected %d' % (path.name, len(faces), expected_triangles)
    worst_normal = 0.0
    for face in faces:
        p, q, r = (vertices[i] for i in face)
        n = cross([q[i] - p[i] for i in range(3)], [r[i] - p[i] for i in range(3)])
        length = math.sqrt(dot(n, n))
        assert length > 1e-9, path.name
        worst_normal = max(worst_normal, abs(1.0 - dot([x / length for x in n], normals[face[0]])))
    assert worst_normal < 1e-4, '%s normal disagreement %.2e' % (path.name, worst_normal)
    canonical = [(x, -y, z) for x, y, z in vertices]
    bounds = dict(min=[min(p[i] for p in canonical) for i in range(3)],
                  max=[max(p[i] for p in canonical) for i in range(3)])
    error = max(abs(bounds[k][i] - expected_bounds[k][i]) for k in bounds for i in range(3))
    assert error < 1e-3, '%s canonical bounds differ by %.5f cm' % (path.name, error)
    return dict(file=path.name, triangles=len(faces), boundsErrorCm=round(error, 6),
                worstNormalErrorRadians=round(worst_normal, 9),
                fileSpaceSignedVolumeCm3=round(signed_volume(vertices, [tuple(f) for f in faces]), 3),
                normalsAndUvs='PASS')


# =====================================================================================
# 4. Bodies
# =====================================================================================


def road_wheels(w, half_track, radius, width, stations):
    for index, x in enumerate(stations):
        for side in (-1, 1):
            w('Wheel_%d_%s' % (index, 'L' if side > 0 else 'R'),
              (x, side * half_track, radius), radius, width)


def car(spec):
    """One generic car silhouette from eight numbers.

    The body is two lofts -- a lower box section and an upper cabin -- plus glass, lamps
    and four wheels. Nothing here is a model of any particular car; `spec` only carries
    segment dimensions."""
    parts = []
    add, b, w = builders(parts)
    length, width, roof, sill = spec['length'], spec['width'], spec['roof'], spec['sill']
    ground = spec['groundCm']
    half = width / 2.0
    nose, tail = length / 2.0, -length / 2.0
    # Lower body: a tapered section so the nose and tail are narrower than the doors.
    lower = [(-half, ground), (half, ground), (half, sill), (-half, sill)]
    lower_end = [(-half * spec['endWidth'], ground + 4.0), (half * spec['endWidth'], ground + 4.0),
                 (half * spec['endWidth'], sill - 6.0), (-half * spec['endWidth'], sill - 6.0)]
    add('BodyFront', 'Paint', taper(lower_end, lower, nose, nose - spec['frontRun']))
    add('BodyCentre', 'Paint', taper(lower, lower, nose - spec['frontRun'], tail + spec['rearRun']))
    add('BodyRear', 'Paint', taper(lower, lower_end, tail + spec['rearRun'], tail))
    # Cabin: a second loft standing on the sill, inset and shorter at both ends.
    cabin_half = half * spec['cabinWidth']
    cabin = [(-cabin_half, sill), (cabin_half, sill), (cabin_half, roof), (-cabin_half, roof)]
    cabin_end = [(-cabin_half * 0.86, sill), (cabin_half * 0.86, sill),
                 (cabin_half * 0.72, roof - spec['roofDrop']), (-cabin_half * 0.72, roof - spec['roofDrop'])]
    add('CabinFront', 'Glass', taper(cabin_end, cabin, spec['cabinFront'], spec['cabinFront'] - spec['screenRun']))
    add('CabinCentre', 'Glass', taper(cabin, cabin, spec['cabinFront'] - spec['screenRun'], spec['cabinRear'] + spec['screenRun']))
    add('CabinRear', 'Glass', taper(cabin, cabin_end, spec['cabinRear'] + spec['screenRun'], spec['cabinRear']))
    b('Roof', 'Paint', (( spec['cabinFront'] + spec['cabinRear']) / 2.0, 0.0, roof + 2.0),
      (spec['cabinFront'] - spec['cabinRear'] + 6.0, cabin_half * 2.0 + 4.0, 5.0), 6.0)
    b('SillKerb', 'Dark', ((nose + tail) / 2.0, half - 2.0, ground + 6.0), (length * 0.72, 5.0, 10.0))
    b('SillRoad', 'Dark', ((nose + tail) / 2.0, -half + 2.0, ground + 6.0), (length * 0.72, 5.0, 10.0))
    b('LampFront', 'Lens', (nose - 2.0, 0.0, sill - 16.0), (5.0, width * 0.74, 12.0), 2.0)
    b('LampRear', 'Lens', (tail + 2.0, 0.0, sill - 14.0), (5.0, width * 0.70, 11.0), 2.0)
    road_wheels(w, half - spec['wheelInset'], spec['wheelRadius'], spec['wheelWidth'],
                (nose - spec['frontOverhang'], tail + spec['rearOverhang']))
    return parts


CARS = {
    # Ordinary European segment dimensions; no model is reproduced.
    'CarHatchback': dict(segment='B-segment hatchback', length=405.0, width=175.0, roof=148.0,
                         sill=96.0, groundCm=22.0, endWidth=0.86, cabinWidth=0.90,
                         frontRun=62.0, rearRun=52.0, cabinFront=68.0, cabinRear=-118.0,
                         screenRun=30.0, roofDrop=16.0, wheelRadius=30.0, wheelWidth=20.0,
                         wheelInset=6.0, frontOverhang=118.0, rearOverhang=96.0),
    'CarSedan': dict(segment='D-segment saloon', length=470.0, width=182.0, roof=147.0,
                     sill=92.0, groundCm=20.0, endWidth=0.84, cabinWidth=0.88,
                     frontRun=86.0, rearRun=80.0, cabinFront=42.0, cabinRear=-132.0,
                     screenRun=36.0, roofDrop=14.0, wheelRadius=32.0, wheelWidth=21.0,
                     wheelInset=6.0, frontOverhang=142.0, rearOverhang=132.0),
    'CarCrossover': dict(segment='compact crossover', length=435.0, width=182.0, roof=168.0,
                         sill=110.0, groundCm=28.0, endWidth=0.88, cabinWidth=0.90,
                         frontRun=70.0, rearRun=58.0, cabinFront=58.0, cabinRear=-136.0,
                         screenRun=30.0, roofDrop=12.0, wheelRadius=35.0, wheelWidth=23.0,
                         wheelInset=5.0, frontOverhang=124.0, rearOverhang=110.0),
    'CarVan': dict(segment='small panel van', length=490.0, width=190.0, roof=196.0,
                   sill=104.0, groundCm=24.0, endWidth=0.90, cabinWidth=0.94,
                   frontRun=54.0, rearRun=30.0, cabinFront=100.0, cabinRear=-210.0,
                   screenRun=26.0, roofDrop=8.0, wheelRadius=33.0, wheelWidth=22.0,
                   wheelInset=5.0, frontOverhang=136.0, rearOverhang=120.0),
}


BUS = dict(length=1200.0, width=255.0, roof=320.0, floor=34.0, sill=132.0,
           wheelRadius=48.0, wheelWidth=30.0, doorWidthCm=124.0)


def bus():
    """A 12.0 m rigid low-floor single-decker: the Egged city-bus envelope.

    Doors are on local +Y, the kerb side, because the actor's lane offset and the boarding
    point it broadcasts are both on +Y. Their leaves are a SEPARATE assembly so the actor
    can slide them; DoorLocalOffsets in the manifest gives one entry per doorway."""
    parts = []
    add, b, w = builders(parts)
    length, width, roof = BUS['length'], BUS['width'], BUS['roof']
    half, nose, tail = width / 2.0, length / 2.0, -length / 2.0
    sill, floor = BUS['sill'], BUS['floor']
    b('BodyLower', 'Paint', (0.0, 0.0, (floor + sill) / 2.0), (length, width, sill - floor), 14.0)
    b('BodyUpper', 'Paint', (0.0, 0.0, (sill + roof) / 2.0), (length - 10.0, width - 6.0, roof - sill), 16.0)
    b('Roof', 'Paint', (0.0, 0.0, roof + 4.0), (length - 40.0, width - 22.0, 9.0), 20.0)
    b('Skirt', 'Dark', (0.0, 0.0, floor / 2.0 + 2.0), (length - 30.0, width - 10.0, floor), 12.0)
    # Glazing: one band per side plus the screens. One box each, not one per bay.
    for side, tag in ((1, 'Kerb'), (-1, 'Road')):
        b('Glass%s' % tag, 'Glass', (-40.0, side * (half - 3.0), (sill + roof) / 2.0 + 6.0),
          (length - 150.0, 6.0, roof - sill - 58.0))
    b('Windscreen', 'Glass', (nose - 6.0, 0.0, (sill + roof) / 2.0 + 14.0), (8.0, width - 40.0, roof - sill - 70.0))
    b('RearScreen', 'Glass', (tail + 6.0, 0.0, (sill + roof) / 2.0 + 8.0), (8.0, width - 54.0, roof - sill - 96.0))
    b('DestinationBlind', 'Dark', (nose - 2.0, 0.0, roof - 20.0), (5.0, width - 96.0, 26.0))
    b('LampFront', 'Lens', (nose - 3.0, 0.0, sill - 42.0), (6.0, width - 44.0, 18.0), 3.0)
    b('LampRear', 'Lens', (tail + 3.0, 0.0, sill - 34.0), (6.0, width - 52.0, 16.0), 3.0)
    # Door apertures on the kerb side (+Y): recessed dark reveals the leaves close over.
    for index, x in enumerate(door_stations()):
        b('DoorReveal_%d' % index, 'Dark', (x, half - 3.0, (floor + roof) / 2.0 - 12.0),
          (BUS['doorWidthCm'], 8.0, roof - floor - 96.0))
    road_wheels(w, half - 18.0, BUS['wheelRadius'], BUS['wheelWidth'], (nose - 210.0, tail + 260.0))
    return parts


def door_stations():
    """X of each doorway centre on the bus, front to back."""
    return (410.0, 30.0, -350.0)


def door_leaf(width_cm, height_cm, thickness=7.0):
    """One sliding leaf: a painted frame with a glass panel. Its local origin is the
    leaf's own centre; the actor places it at DoorLocalOffsets and slides it along -X."""
    parts = []
    add, b, _ = builders(parts)
    b('LeafFrame', 'Paint', (0.0, 0.0, 0.0), (width_cm, thickness, height_cm), 3.0)
    b('LeafGlass', 'Glass', (0.0, 0.0, height_cm * 0.10), (width_cm - 16.0, thickness + 2.0, height_cm - 44.0))
    return parts


TRAM = dict(modules=5, moduleLengthCm=640.0, couplingGapCm=10.0, widthCm=240.0,
            roofCm=335.0, floorCm=35.0, sillCm=118.0, gaugeCm=143.5,
            doorWidthCm=130.0)


def tram_module(is_cab):
    """One module of the articulated tram.

    Five identical-length modules is a simplification: the real vehicle alternates motor
    and suspended modules of different lengths. TransitMath::CarCentreOffsetCm assumes a
    uniform module length, so the consist is authored uniform and the departure is stated
    in the manifest rather than hidden."""
    parts = []
    add, b, _ = builders(parts)
    length, width = TRAM['moduleLengthCm'], TRAM['widthCm']
    roof, sill, floor = TRAM['roofCm'], TRAM['sillCm'], TRAM['floorCm']
    half, nose, tail = width / 2.0, length / 2.0, -length / 2.0
    b('BodyLower', 'Paint', (0.0, 0.0, (floor + sill) / 2.0), (length, width, sill - floor), 10.0)
    b('BodyUpper', 'Paint', (0.0, 0.0, (sill + roof) / 2.0), (length - 4.0, width - 4.0, roof - sill), 12.0)
    b('Roof', 'Paint', (0.0, 0.0, roof + 3.0), (length - 24.0, width - 18.0, 7.0), 16.0)
    b('Skirt', 'Dark', (0.0, 0.0, floor / 2.0 + 1.0), (length - 12.0, width - 8.0, floor), 8.0)
    for side, tag in ((1, 'Kerb'), (-1, 'Road')):
        b('Glass%s' % tag, 'Glass', (0.0, side * (half - 3.0), (sill + roof) / 2.0 + 4.0),
          (length - 96.0, 6.0, roof - sill - 62.0))
        # Doors on BOTH sides: the corridor is a two-track street and platforms alternate.
        b('DoorReveal%s' % tag, 'Dark', (0.0, side * (half - 2.0), (floor + roof) / 2.0 - 14.0),
          (TRAM['doorWidthCm'], 7.0, roof - floor - 104.0))
    if is_cab:
        b('CabNose', 'Paint', (nose + 12.0, 0.0, (floor + roof) / 2.0), (26.0, width - 22.0, roof - floor - 20.0), 10.0)
        b('Windscreen', 'Glass', (nose + 22.0, 0.0, (sill + roof) / 2.0 + 12.0), (8.0, width - 54.0, roof - sill - 66.0))
        b('DestinationBlind', 'Dark', (nose + 24.0, 0.0, roof - 18.0), (5.0, width - 110.0, 24.0))
        b('LampFront', 'Lens', (nose + 24.0, 0.0, sill - 30.0), (5.0, width - 60.0, 14.0), 2.0)
    else:
        b('Pantograph', 'Dark', (0.0, 0.0, roof + 24.0), (140.0, 96.0, 34.0), 8.0)
    # Bogie: two low boxes at standard gauge. Wheels are not modelled -- they are never
    # visible below a low-floor tram skirt at these distances.
    for x in (nose - 150.0, tail + 150.0):
        for side in (-1, 1):
            b('BogieBox_%d_%d' % (int(x), side), 'Dark',
              (x, side * TRAM['gaugeCm'] / 2.0, 26.0), (150.0, 26.0, 44.0), 6.0)
    return parts


# =====================================================================================
# 5. Liveries -- flat colour fields written as PNG with the stdlib only
# =====================================================================================


class Canvas(object):
    """Minimal RGB raster. No PIL, no external dependency, the same encoder the other
    generators in this project use."""

    def __init__(self, w, h, background=(255, 255, 255)):
        self.w, self.h = int(w), int(h)
        self.px = bytearray(bytes(background) * (self.w * self.h))

    def rect(self, x0, y0, x1, y1, colour):
        x0, x1 = max(0, int(min(x0, x1))), min(self.w, int(max(x0, x1)))
        y0, y1 = max(0, int(min(y0, y1))), min(self.h, int(max(y0, y1)))
        row = bytes(colour) * max(0, x1 - x0)
        for y in range(y0, y1):
            start = (y * self.w + x0) * 3
            self.px[start:start + len(row)] = row

    def noise(self, amount, seed):
        """A deterministic per-pixel jitter so a flat field does not band on a gradient
        sky. Not a texture: it is +/- `amount` on each channel."""
        state = seed & 0xffffffff
        for i in range(len(self.px)):
            state = (1664525 * state + 1013904223) & 0xffffffff
            delta = ((state >> 16) % (2 * amount + 1)) - amount
            self.px[i] = max(0, min(255, self.px[i] + delta))

    def png(self, path):
        def chunk(kind, data):
            return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
        scan = b''.join(b'\x00' + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3]) for y in range(self.h))
        Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'
                               + chunk(b'IHDR', struct.pack('!2I5B', self.w, self.h, 8, 2, 0, 0, 0))
                               + chunk(b'IDAT', zlib.compress(scan, 9)) + chunk(b'IEND', b''))
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()


LIVERIES = {
    # colour only; no logo, wordmark, route number or destination text is drawn.
    'tram': dict(size=(512, 256), body=(226, 228, 231), band=(64, 72, 84), accent=(176, 32, 42),
                 claim='Light grey body with a dark waistband and a red accent stripe. The red '
                       'line is named for the line colour on the network map; the stripe is '
                       'authored decoration, not a reproduction of any operator livery.'),
    'bus': dict(size=(512, 256), body=(240, 241, 240), band=(20, 118, 66), accent=(20, 118, 66),
                claim='White body with green banding: the Egged city-bus colours used AS COLOUR. '
                      'No operator logo, wordmark or route branding is drawn.'),
    'car_neutral': dict(size=(256, 256), body=(206, 208, 210), band=(196, 198, 200), accent=(186, 188, 190),
                        claim='A flat neutral field. Per-instance body colour comes from the HISM '
                              'custom-data floats, not from this texture.'),
}


def livery(key):
    cfg = LIVERIES[key]
    w, h = cfg['size']
    canvas = Canvas(w, h, cfg['body'])
    canvas.rect(0, int(h * 0.62), w, int(h * 0.78), cfg['band'])
    canvas.rect(0, int(h * 0.78), w, int(h * 0.82), cfg['accent'])
    canvas.rect(0, int(h * 0.94), w, h, (44, 46, 48))
    canvas.noise(2, 0x5eed0000 ^ (hash(key) & 0xffff))
    return canvas


def glass_texture():
    """A single dark, slightly reflective field for every glazed group. The material
    supplies the reflectivity; this only breaks up the flat value."""
    canvas = Canvas(128, 128, (26, 33, 38))
    canvas.rect(0, 0, 128, 12, (38, 47, 54))
    canvas.noise(3, 0x9133)
    return canvas


# =====================================================================================
# 6. Self-test
# =====================================================================================


def self_test():
    """Cheap invariants for the primitives and the adapter, run before any authoring."""
    cube = box((0.0, 0.0, 50.0), (100.0, 100.0, 100.0))
    volume = signed_volume(*cube)
    if abs(volume - 1e6) > 1.0:
        raise RuntimeError('box volume %.3f is not the 100 cm cube' % volume)
    if len(cube[1]) != 12:
        raise RuntimeError('un-bevelled box should be 12 triangles, got %d' % len(cube[1]))
    edges = {}
    for a, b, c in cube[1]:
        for i, j in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((i, j)))] = edges.get(tuple(sorted((i, j))), 0) + 1
    if any(count != 2 for count in edges.values()):
        raise RuntimeError('cube is not edge-manifold')
    # The adapter's sign, derived rather than remembered: reflecting Y negates the signed
    # volume and reversing the winding negates it again, so the file-space volume of a
    # correctly written OBJ equals the canonical one.
    reflected = [(x, -y, z) for x, y, z in cube[0]]
    reversed_faces = [(a, c, b) for a, b, c in cube[1]]
    adapted = signed_volume(reflected, reversed_faces)
    if abs(adapted - volume) > 1.0:
        raise RuntimeError('adapter changed the signed volume: %.3f vs %.3f' % (adapted, volume))
    bevelled = box((0.0, 0.0, 25.0), (200.0, 100.0, 50.0), 12.0)
    if signed_volume(*bevelled) <= 0.0:
        raise RuntimeError('bevelled box failed to orient')
    tyre = wheel((0.0, 0.0, 30.0), 30.0, 20.0)
    disc = math.pi * 30.0 * 30.0 * 20.0
    polygon = 10 * 0.5 * 30.0 * 30.0 * math.sin(math.tau / 10) * 20.0
    if abs(signed_volume(*tyre) - polygon) > 1.0:
        raise RuntimeError('wheel volume %.1f is not the 10-gon prism %.1f' % (signed_volume(*tyre), polygon))
    return dict(cubeVolumeCm3=volume, adapterSignedVolumeCm3=adapted,
                adapterPreservesSign=True, wheelVolumeCm3=round(signed_volume(*tyre), 3),
                wheelIdealPrismCm3=round(polygon, 3), inscribedDiscCm3=round(disc, 3),
                edgeManifold=True)


# =====================================================================================
# 7. Export
# =====================================================================================


def assemblies():
    """label -> (parts, role metadata). Order is the order the manifest records."""
    built = {}
    for label, spec in CARS.items():
        built[label] = (car(spec), dict(role='car', servesStops=False, segment=spec['segment'],
                                        lengthCm=spec['length'], livery='car_neutral'))
    built['Bus'] = (bus(), dict(role='bus', servesStops=True, segment='12.0 m rigid low-floor single-decker',
                                lengthCm=BUS['length'], livery='bus'))
    built['BusDoorLeaf'] = (door_leaf(BUS['doorWidthCm'] / 2.0 - 4.0, BUS['roof'] - BUS['floor'] - 96.0),
                            dict(role='door_leaf', servesStops=False, segment='sliding leaf, bus',
                                 lengthCm=BUS['doorWidthCm'] / 2.0, livery='bus'))
    built['TramCab'] = (tram_module(True), dict(role='tram_cab', servesStops=True,
                                                segment='articulated low-floor tram, cab module',
                                                lengthCm=TRAM['moduleLengthCm'], livery='tram'))
    built['TramMid'] = (tram_module(False), dict(role='tram_mid', servesStops=True,
                                                 segment='articulated low-floor tram, intermediate module',
                                                 lengthCm=TRAM['moduleLengthCm'], livery='tram'))
    built['TramDoorLeaf'] = (door_leaf(TRAM['doorWidthCm'] / 2.0 - 4.0, TRAM['roofCm'] - TRAM['floorCm'] - 104.0),
                             dict(role='door_leaf', servesStops=False, segment='sliding leaf, tram',
                                  lengthCm=TRAM['doorWidthCm'] / 2.0, livery='tram'))
    return built


def export(force=False, preview=True):
    if MANIFEST_PATH.exists() and not force:
        raise SystemExit('Frozen generation preserved: %s already exists (pass --force to re-author)'
                         % MANIFEST_PATH)
    OUT.mkdir(parents=True, exist_ok=True)
    TEXTURES.mkdir(parents=True, exist_ok=True)
    checks = self_test()

    # Liveries first: a texture failure must stop the run before any OBJ is written.
    textures = {}
    for key in sorted(LIVERIES):
        path = TEXTURES / ('T_VehiclesV3_Livery_%s.png' % key)
        cfg = LIVERIES[key]
        textures[key] = dict(file=path.name, sha256=livery(key).png(path), pixels=list(cfg['size']),
                             materialRole='Paint', claim=cfg['claim'])
    glass_path = TEXTURES / 'T_VehiclesV3_Glass.png'
    textures['glass'] = dict(file=glass_path.name, sha256=glass_texture().png(glass_path),
                             pixels=[128, 128], materialRole='Glass',
                             claim='A dark tinted field for every glazed group; the material '
                                   'supplies the reflectivity.')

    manifest = dict(
        status='offline_checked_native_and_visual_pending',
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
        namespace=DEST, script=Path(__file__).name,
        scriptSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        units='centimetres',
        axes="+X forward, +Y driver's right (kerb side), +Z up; "
             'Z 0 at tyre contact (road) or railhead (tram)',
        objConvention=OBJ_ADAPTER_NOTE,
        materialGroups=list(GROUPS),
        materialGroupNote='Four and only four groups. AMikdashTransit creates one HISM '
                          'component per (body, group), so a fifth group is a fifth component '
                          'and a fifth transform write per vehicle per update.',
        palette={k: dict(linearRgb=v[0], metallic=v[1], roughness=v[2]) for k, v in PALETTE.items()},
        selfTest=checks, textures=textures,
        realReference=[
            'Right-hand traffic: Israel drives on the right, so doors, kerbs and boarding '
            'points are on the vehicle local +Y.',
            'Tram proportions: articulated low-floor vehicle of the Jerusalem Light Rail red '
            'line -- 32.5 m over five modules, 2.40 m wide, 3.35 m high, 1435 mm standard gauge, '
            'doors on both sides. Dimensions only.',
            'Bus proportions: standard 12.0 m rigid low-floor single-decker, 2.55 m wide, '
            '3.20 m high -- the Egged city-bus envelope. Dimensions only.',
            'Car dimensions: ordinary European segment sizes (B-segment hatchback 4.05 m, '
            'D-segment saloon 4.70 m, compact crossover 4.35 m, small panel van 4.90 m).',
        ],
        generic=[
            'Every body is a simplified prism silhouette. No manufacturer bodywork, grille, '
            'lamp signature, badge, wheel design or trim is reproduced.',
            'Liveries are flat colour fields plus a stripe. Tram grey and bus white-and-green '
            'are used AS COLOUR only. No operator logo, wordmark, route number, destination '
            'text or livery artwork is drawn; destination blinds are blank black panels.',
            'The five tram modules are authored to a uniform length because '
            'TransitMath::CarCentreOffsetCm assumes one. The real vehicle alternates motor and '
            'suspended modules of differing lengths.',
            'Interiors, driver, seats, mirrors, pantograph detail and number plates are omitted.',
        ],
        limitations=[
            'Placeholder planar UVs only; no lightmap UVs and no unwrap.',
            'LOD0 only is authored offline. The reduction ladder below is built in the engine '
            'by release_transit_v3.py; nothing is decimated in Python.',
            'No collision is authored; AMikdashTransit sets NoCollision on every component.',
            'The preview PNG is a stdlib depth-buffer inspection image, not an Unreal render.',
        ],
        lods=dict(percentTriangles=[1.0, 0.42, 0.16, 0.06],
                  screenSizes=[1.0, 0.30, 0.13, 0.05],
                  note='Four levels. These bodies are seen from 50 m and beyond; LOD0 exists '
                       'for the one tram standing at a platform in front of the camera.'),
        assemblies={}, imports=[], readback=[], triangleBudget=TRIANGLE_BUDGET)

    built = assemblies()
    total = 0
    for label, (parts, meta) in built.items():
        summary = check_parts(label, parts)
        summary.update(meta)
        manifest['assemblies'][label] = summary
        total += summary['triangles']
        # Editable source of truth, and a canonical twin a human can diff.
        (OUT / ('%s-editable.mesh.json' % label.lower())).write_text(
            json.dumps(dict(units='cm', axes=manifest['axes'], label=label, parts=parts),
                       separators=(',', ':')) + '\n', encoding='utf-8')
        write_obj(OUT / ('%s-canonical.obj' % label.lower()), label, parts, native=False)
        for group in GROUPS:
            selected = [p for p in parts if p['group'] == group]
            if not selected:
                continue
            name = 'SM_VehiclesV3_%s_%s' % (label, group)
            path = OUT / (name + '.obj')
            triangles = write_obj(path, name, selected, native=True)
            points = [p for part in selected for p in part['vertices']]
            bounds = dict(min=[round(min(p[i] for p in points), 3) for i in range(3)],
                          max=[round(max(p[i] for p in points), 3) for i in range(3)])
            manifest['imports'].append(dict(
                assembly=label, name=name, group=group, file=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                triangles=triangles, bounds_cm=bounds,
                livery=meta['livery'] if group == 'Paint' else None))
            manifest['readback'].append(readback(path, triangles, bounds))
        print('%-14s %5d tris  %s' % (label, summary['triangles'],
                                      ' '.join('%s=%d' % (g, summary['groups'][g]) for g in GROUPS
                                               if summary['groups'][g])))

    if total >= TRIANGLE_BUDGET:
        raise RuntimeError('Generated %d triangles, over the %d budget' % (total, TRIANGLE_BUDGET))
    manifest['totalTriangles'] = total
    manifest['consist'] = dict(
        modules=TRAM['modules'], moduleLengthCm=TRAM['moduleLengthCm'],
        couplingGapCm=TRAM['couplingGapCm'],
        overallLengthCm=TRAM['modules'] * (TRAM['moduleLengthCm'] + TRAM['couplingGapCm']) - TRAM['couplingGapCm'],
        order=['TramCab'] + ['TramMid'] * (TRAM['modules'] - 2) + ['TramCab'],
        note='The last module is posed with a 180 degree yaw by AMikdashTransit so its cab '
             'faces the direction of travel at the far end.')
    manifest['doorLocalOffsetsCm'] = dict(
        Bus=[[x, (BUS['width'] / 2.0) - 4.0, (BUS['floor'] + BUS['roof']) / 2.0 - 12.0]
             for x in door_stations()],
        Tram=[[0.0, side * (TRAM['widthCm'] / 2.0 - 3.0),
               (TRAM['floorCm'] + TRAM['roofCm']) / 2.0 - 14.0] for side in (-1, 1)],
        note='One entry per doorway, in the body local frame. The actor slides each leaf '
             'along the body -X by the smoothstepped door offset.')
    if preview:
        manifest['preview'] = render_preview(built)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return manifest


def render_preview(built):
    """Orthographic side elevations on one sheet, so the silhouettes can be compared at a
    glance. A stdlib inspection image, not an Unreal render."""
    cell_w, cell_h, columns = 340, 150, 2
    rows = (len(built) + columns - 1) // columns
    canvas = Canvas(cell_w * columns, cell_h * rows, (245, 245, 243))
    for index, (label, (parts, _meta)) in enumerate(built.items()):
        ox, oy = (index % columns) * cell_w, (index // columns) * cell_h
        points = [p for part in parts for p in part['vertices']]
        lo_x, hi_x = min(p[0] for p in points), max(p[0] for p in points)
        lo_z, hi_z = min(p[2] for p in points), max(p[2] for p in points)
        scale = min((cell_w - 24) / max(1.0, hi_x - lo_x), (cell_h - 24) / max(1.0, hi_z - lo_z))
        shade = {'Paint': (150, 152, 156), 'Glass': (70, 86, 96), 'Dark': (60, 62, 66), 'Lens': (198, 186, 140)}
        for part in parts:
            v = part['vertices']
            px0 = min(p[0] for p in v)
            px1 = max(p[0] for p in v)
            pz0 = min(p[2] for p in v)
            pz1 = max(p[2] for p in v)
            canvas.rect(ox + 12 + (px0 - lo_x) * scale, oy + cell_h - 12 - (pz1 - lo_z) * scale,
                        ox + 12 + (px1 - lo_x) * scale, oy + cell_h - 12 - (pz0 - lo_z) * scale,
                        shade[part['group']])
    path = OUT / 'geometry-preview.png'
    return dict(file=path.name, sha256=canvas.png(path), pixels=[cell_w * columns, cell_h * rows],
                what='Orthographic side-elevation bounding boxes per part, one cell per '
                     'assembly. An inspection sheet, not a render.')


def _main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--export', action='store_true', help='write the VehiclesV3 geometry')
    parser.add_argument('--force', action='store_true', help='overwrite a frozen generation')
    parser.add_argument('--no-preview', action='store_true', help='skip the inspection sheet')
    arguments = parser.parse_args()
    if not arguments.export:
        parser.error('Explicit --export [--force] [--no-preview]; offline only. The native '
                     'half is Scripts/release_transit_v3.py.')
    manifest = export(force=arguments.force, preview=not arguments.no_preview)
    print('total triangles %d of %d' % (manifest['totalTriangles'], manifest['triangleBudget']))
    print('meshes %d, textures %d' % (len(manifest['imports']), len(manifest['textures'])))
    print('manifest %s' % MANIFEST_PATH)
    return 0


if __name__ == '__main__':
    sys.exit(_main())

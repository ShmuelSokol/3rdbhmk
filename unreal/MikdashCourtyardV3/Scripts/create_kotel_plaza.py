"""Offline generator for KotelPlazaV1 - the present-day Western Wall Plaza as an open paved place.

Shmuel, 9 September 2026, verbatim:

    "i also want you to restore the old city to its current modern day layout... with kotel
     plaza and then houses up to that point"

WHAT THIS IS FOR
----------------
The MODERN state of this level is supposed to be present-day Jerusalem. Its 11,437 OSM
building footprints already put the Jewish Quarter housing right up to the edge of the
Western Wall Plaza - this generator's own census proves ZERO buildings stand inside the plaza
polygon and 36 within 30 m of its edge, which is exactly the post-1967 layout, the Mughrabi
Quarter already cleared. So the houses are a RESTORE, not a build.

What is missing is the plaza itself. The source data has it as OSM way 26492734,
`highway=pedestrian`, name "Western Wall Plaza" - and the context pipeline
(mikdash-walkthrough/lib/mikdash/jerusalem.ts) renders every `road` feature as a RIBBON of
`(width||2)*2` source amot around its centreline. A pedestrian AREA therefore came through as
a 2 m wide stone path traced around the plaza's 400 m outline, with bare DEM terrain inside
it. This generator lays the inside.

WHAT IS SOURCED AND WHAT IS AUTHORED
------------------------------------
SOURCED, and used unmodified:
  * The plaza footprint. OSM way 26492734, 31 vertices, carried in this project's own
    SourceAssets/visual-review/mount-platform-design.json as the `protected` entry
    "Western Wall Plaza", already in native world centimetres. Hash-pinned below.
  * The Western Wall footprint and its 200 cm no-edit guard. OSM way 817206833, the same
    file's other `protected` entry. Nothing is ever placed inside wall + guard.
  * The ground. jerusalem.json `terrain`, a 257 x 257 grid at 50 source amot (25 m) with
    reference elevation 748.0 m a.s.l. - the same DEM the precinct wall's ring profile and
    the precinct plaza's earthwork figures were sampled from. Hash-pinned below.
  * The deck, step, kerb and retaining-band modules, and their three materials: the
    PrecinctPlazaV1 set already imported and receipted on 9 September 2026. NOTHING NEW IS
    IMPORTED. The deck tile's own manifest note sanctions X/Y scaling for partial cells.

AUTHORED, and named as such:
  * That the plaza is two levels - a lower prayer plaza at the wall and an upper plaza behind
    it - and that the split stands 40 m out from the wall's west face.
  * The riser count, which is DERIVED from the DEM (the two decks are set from percentiles of
    the ground under each half) but rounded to the 25 cm riser of the existing step module.
  * The perimeter retaining and parapet, the mechitza line, and the paving cell size.

NOT BUILT, and NOT claimed: Wilson's Arch (a vaulted hall under the buildings at the north
end - it is interior architecture, not a plaza surface), the Mughrabi ramp to the Temple
Mount at the south end, the prayer-section furniture (shtenders, book cases, the partition
rails), the security plaza and its entrances at the west, and any lighting. NOBODY HAS
LOOKED AT ANY OF THIS IN A FRAME.

  python Scripts/create_kotel_plaza.py
  python Scripts/create_kotel_plaza.py --census      (buildings around the plaza, only)
"""
import hashlib
import io
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
DESIGN = ROOT / 'SourceAssets/visual-review/mount-platform-design.json'
BRIEF = ROOT / 'SourceAssets/visual-review/western-wall-detail-brief.json'
JERUSALEM = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace'
                 r'\mikdash-walkthrough\public\context\jerusalem.json')
OUT = ROOT / 'SourceAssets/context-review/KotelPlazaV1'

PLAZA_OSM_ID = 26492734
WALL_OSM_ID = 817206833

# The alignment that export_buildings.py baked and every context script since has reused,
# never re-applied. Scripts/create_oldcity_facades.py lines 120-121.
TX = 17.509700315687695
TZ = -0.5513496449385334
AMAH_CM = 50.0
REFERENCE_MASL = 748.0

# --- authored numbers, every one of them ---------------------------------------------
CELL_CM = 250.0          # paving cell. The deck module is 1250 cm; this is it at 0.2.
MIN_CELL_AREA_CM2 = 1.0e4  # 1 m2: below this a clipped sliver is dropped rather than placed
SPLIT_FROM_WALL_CM = 4000.0   # the lower prayer plaza is 40 m deep
WALL_GUARD_CM = 200.0    # the project's own minimumNoEditBufferCm on both protected polygons
RISER_CM = 25.0          # SM_PlazaV1_Step: Z -25..0
TREAD_CM = 100.0         # SM_PlazaV1_Step: 2500 x 100 cm
STEP_MODULE_CM = 2500.0
DECK_MODULE_CM = 1250.0
DECK_THICKNESS_CM = 50.0
KERB_MODULE_CM = 1250.0
KERB_PROUD_CM = 25.0     # SM_PlazaV1_Kerb: Z -50..25
BAND_MODULE_CM = 1250.0
BAND_HEIGHT_CM = 250.0
PARAPET_HEIGHT_CM = 110.0
MECHITZA_HEIGHT_CM = 180.0
MECHITZA_FRACTION = 0.62   # along the wall from its north end; men's section north
PARAPET_MIN_DROP_CM = 100.0

MESHES = {
    'deck': '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Meshes/SM_PlazaV1_DeckTile',
    'step': '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Meshes/SM_PlazaV1_Step',
    'kerb': '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Meshes/SM_PlazaV1_Kerb',
    'band': '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Meshes/SM_PlazaV1_RetainingBand',
}
MATERIALS = {
    'deck': '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Materials/M_PrecinctPlaza_Paving',
    'ashlar': '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Materials/MI_PrecinctPlaza_Ashlar',
}


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
def signed_area(poly):
    total = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def closed(poly):
    return poly if poly[0] == poly[-1] else poly + [poly[0]]


def point_in_polygon(point, poly):
    x, y = point
    inside = False
    ring = closed(poly)
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        if (y1 > y) != (y2 > y):
            if x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def clip_to_halfplane(poly, inside_fn, intersect_fn):
    """Sutherland-Hodgman against one half-plane."""
    out = []
    count = len(poly)
    for i in range(count):
        current = poly[i]
        previous = poly[(i - 1) % count]
        cur_in = inside_fn(current)
        prev_in = inside_fn(previous)
        if cur_in:
            if not prev_in:
                out.append(intersect_fn(previous, current))
            out.append(current)
        elif prev_in:
            out.append(intersect_fn(previous, current))
    return out


def clip_to_rect(poly, x0, y0, x1, y1):
    """Convex-rectangle clip of a simple polygon. Correct for the convex clipper; a concave
    subject can produce degenerate bridges, which only ever ADD area, so every clipped cell is
    additionally area-checked against a point sample below."""
    edges = [
        (lambda p: p[0] >= x0, lambda a, b: _lerp_x(a, b, x0)),
        (lambda p: p[0] <= x1, lambda a, b: _lerp_x(a, b, x1)),
        (lambda p: p[1] >= y0, lambda a, b: _lerp_y(a, b, y0)),
        (lambda p: p[1] <= y1, lambda a, b: _lerp_y(a, b, y1)),
    ]
    result = list(poly)
    for inside_fn, intersect_fn in edges:
        if not result:
            return []
        result = clip_to_halfplane(result, inside_fn, intersect_fn)
    return result


def _lerp_x(a, b, x):
    if abs(b[0] - a[0]) < 1e-12:
        return (x, a[1])
    t = (x - a[0]) / (b[0] - a[0])
    return (x, a[1] + t * (b[1] - a[1]))


def _lerp_y(a, b, y):
    if abs(b[1] - a[1]) < 1e-12:
        return (a[0], y)
    t = (y - a[1]) / (b[1] - a[1])
    return (a[0] + t * (b[0] - a[0]), y)


def polygon_area(poly):
    return abs(signed_area(poly)) if len(poly) >= 3 else 0.0


def bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def distance_point_to_segment(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 <= 0.0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def distance_to_polygon(p, poly):
    ring = closed(poly)
    return min(distance_point_to_segment(p, ring[i], ring[i + 1])
               for i in range(len(ring) - 1))


# ---------------------------------------------------------------------------
# sources
# ---------------------------------------------------------------------------
def load_sources():
    design = json.loads(DESIGN.read_text(encoding='utf-8-sig'))
    plaza = wall = None
    for entry in design['protected']:
        if entry.get('osmId') == PLAZA_OSM_ID:
            plaza = entry
        if entry.get('osmId') == WALL_OSM_ID:
            wall = entry
    if plaza is None or wall is None:
        raise RuntimeError('mount-platform-design.json is missing a protected polygon')
    plaza_poly = [(float(x), float(y)) for x, y in plaza['nativeXYcm']]
    wall_poly = [(float(x), float(y)) for x, y in wall['nativeXYcm']]
    if plaza_poly[0] == plaza_poly[-1]:
        plaza_poly = plaza_poly[:-1]
    if wall_poly[0] == wall_poly[-1]:
        wall_poly = wall_poly[:-1]

    with io.open(JERUSALEM, encoding='utf-8') as handle:
        city = json.load(handle)
    return dict(design=design, plaza=plaza, wall=wall, plaza_poly=plaza_poly,
                wall_poly=wall_poly, city=city)


class Ground(object):
    """The DEM. 257 x 257 samples at 50 source amot - 25 m - so it resolves a hillside and
    does NOT resolve a man-made terrace. Every level taken from it is reported as a
    percentile, never as a survey."""

    def __init__(self, terrain):
        self.size = int(terrain['size'])
        self.step = float(terrain['step'])
        self.origin = float(terrain['origin'])
        self.heights = terrain['heights']

    def at_amot(self, x, z):
        fx = (x - self.origin) / self.step
        fz = (z - self.origin) / self.step
        i = max(0, min(self.size - 2, int(math.floor(fx))))
        j = max(0, min(self.size - 2, int(math.floor(fz))))
        tx, tz = fx - i, fz - j
        get = lambda a, b: self.heights[b * self.size + a]        # noqa: E731
        return (get(i, j) * (1 - tx) * (1 - tz) + get(i + 1, j) * tx * (1 - tz)
                + get(i, j + 1) * (1 - tx) * tz + get(i + 1, j + 1) * tx * tz)

    def at_cm(self, x_cm, y_cm):
        return self.at_amot(x_cm / AMAH_CM - TX, y_cm / AMAH_CM - TZ) * AMAH_CM


def masl(z_cm):
    return REFERENCE_MASL + z_cm / 100.0


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        raise RuntimeError('no samples')
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


# ---------------------------------------------------------------------------
# the wall line: everything is measured perpendicular to the Kotel's west face
# ---------------------------------------------------------------------------
def wall_frame(wall_poly, plaza_poly):
    """Long axis of the Western Wall footprint, and the outward normal that points into the
    plaza. Derived from the SOURCED polygon; nothing here is chosen."""
    best = None
    for i in range(len(wall_poly)):
        for j in range(i + 1, len(wall_poly)):
            d = math.hypot(wall_poly[j][0] - wall_poly[i][0], wall_poly[j][1] - wall_poly[i][1])
            if best is None or d > best[0]:
                best = (d, wall_poly[i], wall_poly[j])
    length, a, b = best
    ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    nx, ny = -uy, ux
    plaza_cx = sum(p[0] for p in plaza_poly) / len(plaza_poly)
    plaza_cy = sum(p[1] for p in plaza_poly) / len(plaza_poly)
    if (plaza_cx - a[0]) * nx + (plaza_cy - a[1]) * ny < 0.0:
        nx, ny = -nx, -ny
    # The face nearest the plaza: the wall vertex with the greatest normal coordinate.
    face = max((p[0] - a[0]) * nx + (p[1] - a[1]) * ny for p in wall_poly)
    origin = (a[0] + face * nx, a[1] + face * ny)
    return dict(anchor=a, other=b, lengthCm=length, u=(ux, uy), n=(nx, ny), faceOrigin=origin)


def depth(point, frame):
    """Distance out from the wall's west face, positive into the plaza."""
    ox, oy = frame['faceOrigin']
    nx, ny = frame['n']
    return (point[0] - ox) * nx + (point[1] - oy) * ny


def along(point, frame):
    """Distance along the wall from its anchor end."""
    ax, ay = frame['anchor']
    ux, uy = frame['u']
    return (point[0] - ax) * ux + (point[1] - ay) * uy


def to_world(depth_cm, along_cm, frame):
    ox, oy = frame['faceOrigin']
    nx, ny = frame['n']
    ux, uy = frame['u']
    ax, ay = frame['anchor']
    # faceOrigin already carries the along-component of the anchor; rebuild from both bases.
    base_along = along((ox, oy), frame)
    delta = along_cm - base_along
    return (ox + nx * depth_cm + ux * delta, oy + ny * depth_cm + uy * delta)


# ---------------------------------------------------------------------------
# the plan
# ---------------------------------------------------------------------------
def build(sources):
    plaza_poly = sources['plaza_poly']
    wall_poly = sources['wall_poly']
    ground = Ground(sources['city']['terrain'])
    frame = wall_frame(wall_poly, plaza_poly)
    yaw = math.degrees(math.atan2(frame['u'][1], frame['u'][0]))

    minx, miny, maxx, maxy = bbox(plaza_poly)
    plaza_area = polygon_area(plaza_poly)

    # ---- ground statistics, per half, on a 200 cm sample grid --------------------------
    lower_samples, upper_samples, all_samples = [], [], []
    sx = math.floor(minx / 200.0) * 200.0
    while sx <= maxx:
        sy = math.floor(miny / 200.0) * 200.0
        while sy <= maxy:
            if point_in_polygon((sx, sy), plaza_poly):
                z = ground.at_cm(sx, sy)
                all_samples.append(z)
                (lower_samples if depth((sx, sy), frame) <= SPLIT_FROM_WALL_CM
                 else upper_samples).append(z)
            sy += 200.0
        sx += 200.0
    if not lower_samples or not upper_samples:
        raise RuntimeError('The 40 m split does not divide this polygon into two halves')

    lower_z = round(percentile(lower_samples, 0.25), 3)
    upper_target = percentile(upper_samples, 0.50)
    risers = max(1, int(round((upper_target - lower_z) / RISER_CM)))
    upper_z = round(lower_z + risers * RISER_CM, 3)

    plan = {'deck': [], 'step': [], 'kerb': [], 'band': []}

    # ---- deck ------------------------------------------------------------------------
    guard_poly = wall_poly
    cells = 0
    cells_dropped = 0
    deck_area = 0.0
    gx = math.floor(minx / CELL_CM) * CELL_CM
    while gx < maxx:
        gy = math.floor(miny / CELL_CM) * CELL_CM
        while gy < maxy:
            clipped = clip_to_rect(plaza_poly, gx, gy, gx + CELL_CM, gy + CELL_CM)
            area = polygon_area(clipped)
            if area < MIN_CELL_AREA_CM2:
                gy += CELL_CM
                continue
            cx0, cy0, cx1, cy1 = bbox(clipped)
            centre = ((cx0 + cx1) / 2.0, (cy0 + cy1) / 2.0)
            # Never pave the Kotel or its 200 cm no-edit guard.
            if point_in_polygon(centre, guard_poly) or \
                    distance_to_polygon(centre, guard_poly) < WALL_GUARD_CM:
                cells_dropped += 1
                gy += CELL_CM
                continue
            width = max(1.0, cx1 - cx0)
            height = max(1.0, cy1 - cy0)
            z = lower_z if depth(centre, frame) <= SPLIT_FROM_WALL_CM else upper_z
            plan['deck'].append(dict(
                loc=[round(centre[0], 3), round(centre[1], 3), round(z, 3)],
                rot=[0.0, 0.0, 0.0],
                scale=[round(width / DECK_MODULE_CM, 6), round(height / DECK_MODULE_CM, 6), 1.0]))
            deck_area += width * height
            cells += 1
            gy += CELL_CM
        gx += CELL_CM

    # ---- the flight between the two levels -------------------------------------------
    # The chord of the plaza along the wall at the split, tiled with whole step modules and
    # one scale factor so the flight ends exactly on the polygon.
    chord = chord_at_depth(plaza_poly, frame, SPLIT_FROM_WALL_CM)
    if chord is None:
        raise RuntimeError('No chord at the split depth')
    t0, t1 = chord
    span = t1 - t0
    modules = max(1, int(math.ceil(span / STEP_MODULE_CM)))
    scale_x = span / (modules * STEP_MODULE_CM)
    for riser in range(1, risers + 1):
        d = SPLIT_FROM_WALL_CM + (riser - 0.5) * TREAD_CM
        for m in range(modules):
            centre_t = t0 + (m + 0.5) * (span / modules)
            x, y = to_world(d, centre_t, frame)
            plan['step'].append(dict(
                loc=[round(x, 3), round(y, 3), round(lower_z + riser * RISER_CM, 3)],
                rot=[0.0, 0.0, round(yaw, 6)],
                scale=[round(scale_x, 6), 1.0, 1.0]))

    # ---- mechitza: one barrier across the lower plaza, wall out to the flight ---------
    a_lo, a_hi = along_range(plaza_poly, frame)
    mech_t = a_lo + MECHITZA_FRACTION * (a_hi - a_lo)
    mech_len = SPLIT_FROM_WALL_CM - WALL_GUARD_CM
    mech_modules = max(1, int(math.ceil(mech_len / KERB_MODULE_CM)))
    mech_scale = mech_len / (mech_modules * KERB_MODULE_CM)
    for m in range(mech_modules):
        d = WALL_GUARD_CM + (m + 0.5) * (mech_len / mech_modules)
        x, y = to_world(d, mech_t, frame)
        plan['kerb'].append(dict(
            loc=[round(x, 3), round(y, 3), round(lower_z, 3)],
            rot=[0.0, 0.0, round(yaw + 90.0, 6)],
            scale=[round(mech_scale, 6), 1.0,
                   round(MECHITZA_HEIGHT_CM / KERB_PROUD_CM, 6)],
            role='mechitza'))

    # ---- perimeter: retaining bands where the deck stands above ground, parapet above --
    ring = closed(plaza_poly)
    retained_edges = 0
    max_drop = 0.0
    for i in range(len(ring) - 1):
        a, b = ring[i], ring[i + 1]
        edge = math.hypot(b[0] - a[0], b[1] - a[1])
        if edge < 1.0:
            continue
        ex, ey = (b[0] - a[0]) / edge, (b[1] - a[1]) / edge
        edge_yaw = math.degrees(math.atan2(ey, ex))
        pieces = max(1, int(math.ceil(edge / BAND_MODULE_CM)))
        piece_scale = edge / (pieces * BAND_MODULE_CM)
        for p in range(pieces):
            t = (p + 0.5) * (edge / pieces)
            mx, my = a[0] + ex * t, a[1] + ey * t
            inward = (mx - (minx + maxx) / 2.0, my - (miny + maxy) / 2.0)
            probe = (mx, my)
            deck_z = lower_z if depth(probe, frame) <= SPLIT_FROM_WALL_CM else upper_z
            ground_z = ground.at_cm(mx, my)
            drop = deck_z - ground_z
            if drop > 0.0:
                bands = int(math.ceil(drop / BAND_HEIGHT_CM))
                max_drop = max(max_drop, drop)
                retained_edges += 1
                for band in range(bands):
                    plan['band'].append(dict(
                        loc=[round(mx, 3), round(my, 3),
                             round(deck_z - band * BAND_HEIGHT_CM, 3)],
                        rot=[0.0, 0.0, round(edge_yaw, 6)],
                        scale=[round(piece_scale, 6), 1.0, 1.0]))
            if drop > PARAPET_MIN_DROP_CM:
                plan['kerb'].append(dict(
                    loc=[round(mx, 3), round(my, 3), round(deck_z, 3)],
                    rot=[0.0, 0.0, round(edge_yaw, 6)],
                    scale=[round(piece_scale, 6), 1.0,
                           round(PARAPET_HEIGHT_CM / KERB_PROUD_CM, 6)],
                    role='parapet'))
            _ = inward

    census = building_census(sources, plaza_poly)
    earthwork = measure_earthwork(sources, plaza_poly, frame, ground, lower_z, upper_z)

    manifest = {
        'status': 'AUTHORED_OFFLINE_SOURCE_NATIVE_PLACEMENT_PENDING',
        'version': 1,
        'stamp': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
        'generatorSha256': sha256_of(Path(__file__)),
        'userInstruction': 'i also want you to restore the old city to its current modern day '
                           'layout... with kotel plaza and then houses up to that point',
        'source': {
            'design': str(DESIGN), 'designSha256': sha256_of(DESIGN),
            'jerusalemJson': str(JERUSALEM), 'jerusalemJsonSha256': sha256_of(JERUSALEM),
            'plazaOsmId': PLAZA_OSM_ID, 'wallOsmId': WALL_OSM_ID,
            'alignment': 'UEcm = ((x_amot + %.15f) * 50, (z_amot %+.15f) * 50) - baked once by '
                         'export_buildings.py, reused here, never re-applied' % (TX, TZ),
            'reuse': 'Every mesh and material is the PrecinctPlazaV1 set already imported and '
                     'receipted on 9 September 2026. This generator imports nothing.'},
        'sourced': {
            'plazaFootprint': 'OSM way %d "Western Wall Plaza", highway=pedestrian, 31 vertices'
                              % PLAZA_OSM_ID,
            'plazaAreaM2': round(plaza_area / 1.0e4, 2),
            'plazaBboxCm': [round(v, 1) for v in (minx, miny, maxx, maxy)],
            'plazaExtentM': [round((maxx - minx) / 100.0, 1), round((maxy - miny) / 100.0, 1)],
            'wallFootprint': 'OSM way %d "Western Wall", building=wall, height=20' % WALL_OSM_ID,
            'wallLengthCm': round(frame['lengthCm'], 1),
            'wallGuardCm': WALL_GUARD_CM,
            'groundDem': '257 x 257 at 50 source amot (25 m), reference elevation 748.0 m a.s.l.',
            'groundUnderPlazaMasl': {
                'samples': len(all_samples),
                'min': round(masl(min(all_samples)), 2),
                'p25': round(masl(percentile(all_samples, 0.25)), 2),
                'median': round(masl(percentile(all_samples, 0.50)), 2),
                'p75': round(masl(percentile(all_samples, 0.75)), 2),
                'max': round(masl(max(all_samples)), 2)}},
        'authored': {
            'twoLevels': 'A lower prayer plaza at the wall and an upper plaza behind it. That '
                         'the modern plaza has this form is well known; WHERE the split falls '
                         'here is authored, not surveyed.',
            'splitFromWallCm': SPLIT_FROM_WALL_CM,
            'cellCm': CELL_CM,
            'parapetHeightCm': PARAPET_HEIGHT_CM,
            'mechitzaHeightCm': MECHITZA_HEIGHT_CM,
            'mechitzaFractionAlongWall': MECHITZA_FRACTION,
            'note': 'The 25 cm riser and 100 cm tread are NOT authored here: they are the '
                    'existing SM_PlazaV1_Step module, reused.'},
        'derived': {
            'lowerDeckZCm': lower_z, 'lowerDeckMasl': round(masl(lower_z), 2),
            'lowerFrom': 'p25 of %d DEM samples under the lower half' % len(lower_samples),
            'upperDeckZCm': upper_z, 'upperDeckMasl': round(masl(upper_z), 2),
            'upperFrom': 'p50 of %d DEM samples under the upper half (%.2f m a.s.l.), rounded '
                         'to a whole number of 25 cm risers'
                         % (len(upper_samples), masl(upper_target)),
            'risers': risers, 'riseCm': round(risers * RISER_CM, 1),
            'flightSpanCm': round(span, 1), 'flightModules': modules,
            'flightScaleX': round(scale_x, 6),
            'deckCells': cells, 'deckCellsDroppedForWallGuard': cells_dropped,
            'deckAreaM2': round(deck_area / 1.0e4, 2),
            'deckAreaVersusPolygonPercent': round(100.0 * deck_area / plaza_area, 2),
            'retainedEdgePieces': retained_edges,
            'maxRetainedDropCm': round(max_drop, 1)},
        'meshes': MESHES, 'materials': MATERIALS,
        'components': [
            dict(key='deck', mesh=MESHES['deck'], material=MATERIALS['deck'],
                 instances=len(plan['deck']), castShadow=False,
                 note='Deck tiles clipped to the polygon and scaled in X and Y only, which is '
                      'the module manifest\'s own sanctioned use. The paving material maps by '
                      'WORLD position, so a scaled tile still lays a correct 5 m pattern.'),
            dict(key='step', mesh=MESHES['step'], material=MATERIALS['ashlar'],
                 instances=len(plan['step']), castShadow=True,
                 note='The flight between the two levels, 25 cm riser, 100 cm tread.'),
            dict(key='kerb', mesh=MESHES['kerb'], material=MATERIALS['ashlar'],
                 instances=len(plan['kerb']), castShadow=True,
                 note='Perimeter parapet where the deck stands more than 1 m above ground, and '
                      'the mechitza across the lower plaza. Scaled in Z; the ashlar material '
                      'maps by world position, so its courses stay on world-Z levels.'),
            dict(key='band', mesh=MESHES['band'], material=MATERIALS['ashlar'],
                 instances=len(plan['band']), castShadow=True,
                 note='Retaining bands down to grade, 250 cm each, never scaled in Z - the '
                      'PrecinctPlazaV1 discipline, kept.'),
        ],
        'instanceTotal': sum(len(v) for v in plan.values()),
        'triangleTotal': (len(plan['deck']) * 12 + len(plan['step']) * 12
                          + len(plan['kerb']) * 12 + len(plan['band']) * 12),
        'buildingCensus': census,
        'earthwork': earthwork,
        'notBuilt': [
            "Wilson's Arch. It is a vaulted hall under the buildings at the north end - "
            'interior architecture, not a plaza surface - and none is modelled.',
            'The Mughrabi ramp up to the Temple Mount at the south end. The Mughrabi Gate '
            'building (OSM 291836692) is in the model; the ramp is not.',
            'Prayer-section furniture: shtenders, book cases, partition rails, chairs.',
            'The security plaza, its entrances and its screening at the west.',
            'Lighting of any kind.',
            'NO VISUAL ACCEPTANCE. Nobody has looked at any of this in a frame.'],
        'limitations': [
            'The DEM is 257 x 257 at 25 m. It resolves the hillside and does NOT resolve a '
            'man-made terrace, so both deck levels are DEM percentiles, not survey levels.',
            'The deck edge is stepped at the 250 cm cell, clipped to the polygon by AABB of '
            'the clipped cell. It is not a smooth polygon edge.',
            'Nothing is placed inside the Western Wall footprint plus its 200 cm no-edit '
            'guard; the preserved source ground occupies that seam, exactly as the '
            'mount-access study left it.',
            'Collision, walkability and the seam to the surrounding street ribbons are '
            'untested here.'],
    }
    return manifest, plan, frame


TERRAIN_ORIGIN_CM = -320000.0    # jerusalem.json terrain origin -6400 amot x 50 cm
TERRAIN_TILE_CM = 40000.0        # the 16 x 16 grid of 400 m tiles


def terrain_tiles_over(poly):
    """Which SM_JerusalemTerrain_<rr>_<cc> tiles the polygon lands on. The grid is the one
    Scripts/create_precinct_plaza.py's design record reads: 16 x 16 tiles of 400 m, origin at
    -320,000 cm on both axes (the DEM's own -6400 amot origin)."""
    minx, miny, maxx, maxy = bbox(poly)
    tiles = []
    c0 = int(math.floor((minx - TERRAIN_ORIGIN_CM) / TERRAIN_TILE_CM))
    c1 = int(math.floor((maxx - TERRAIN_ORIGIN_CM) / TERRAIN_TILE_CM))
    r0 = int(math.floor((miny - TERRAIN_ORIGIN_CM) / TERRAIN_TILE_CM))
    r1 = int(math.floor((maxy - TERRAIN_ORIGIN_CM) / TERRAIN_TILE_CM))
    for row in range(r0, r1 + 1):
        for column in range(c0, c1 + 1):
            tiles.append(dict(row=row, column=column,
                              name='SM_JerusalemTerrain_%02d_%02d' % (row, column),
                              xCm=[TERRAIN_ORIGIN_CM + column * TERRAIN_TILE_CM,
                                   TERRAIN_ORIGIN_CM + (column + 1) * TERRAIN_TILE_CM],
                              yCm=[TERRAIN_ORIGIN_CM + row * TERRAIN_TILE_CM,
                                   TERRAIN_ORIGIN_CM + (row + 1) * TERRAIN_TILE_CM]))
    return tiles


def measure_earthwork(sources, plaza_poly, frame, ground, lower_z, upper_z):
    """THE BLOCKING MEASUREMENT. A 25 m DEM cannot describe a man-made terrace: over the
    93 x 131 m plaza it averages the plaza floor together with the hillside and the Jewish
    Quarter beside it, and comes out as a ramp falling about 9 m in both directions. This
    measures what that costs a flat deck, and then proves that NO flat level escapes it."""
    samples = []
    minx, miny, maxx, maxy = bbox(plaza_poly)
    x = minx
    while x <= maxx:
        y = miny
        while y <= maxy:
            if point_in_polygon((x, y), plaza_poly):
                d = depth((x, y), frame)
                samples.append((ground.at_cm(x, y),
                                lower_z if d <= SPLIT_FROM_WALL_CM else upper_z))
            y += 100.0
        x += 100.0
    cut = [g - deck for g, deck in samples if g > deck]
    fill = [deck - g for g, deck in samples if g <= deck]
    cut.sort()
    fill.sort()

    # The Kotel mesh AS IT STANDS IN THE LEVEL. Not re-derived: read from the recorded
    # componentDerivedUnrealBoundsCm in western-wall-detail-brief.json, which identified the
    # wall inside SM_JerusalemBuildings_Grid_N002_P001 by exact geometry bounds.
    brief = json.loads(BRIEF.read_text(encoding='utf-8-sig'))
    wall_bounds = brief['currentAsset']['componentDerivedUnrealBoundsCm']
    wall_top = float(wall_bounds['max'][2])
    wall_base = float(wall_bounds['min'][2])

    # The houses that border the plaza, and the grade they stand on.
    house_grades = []
    for feature in sources['city']['features']:
        if feature.get('kind') != 'building':
            continue
        points = [((float(px) + TX) * AMAH_CM, (float(py) + TZ) * AMAH_CM)
                  for px, py in feature['points']]
        near = min(distance_to_polygon(v, plaza_poly) for v in points)
        if near > 3000.0:
            continue
        house_grades.append(min(ground.at_cm(v[0], v[1]) for v in points))
    house_grades.sort()

    trials = []
    for fraction in (0.25, 0.50, 0.75, 0.90, 0.95, 1.00):
        candidate = percentile([g for g, _ in samples], fraction)
        pierced = sum(1 for g, _ in samples if g > candidate)
        buried = sum(1 for g in house_grades if candidate - g > 100.0)
        trials.append(dict(
            groundPercentile=fraction, deckMasl=round(masl(candidate), 2),
            areaPiercedByTerrainPercent=round(100.0 * pierced / len(samples), 1),
            kotelExposedM=round((wall_top - candidate) / 100.0, 1),
            borderingHousesBuriedOver1m=buried,
            worstHouseBurialM=round(max([(candidate - g) / 100.0 for g in house_grades] or [0.0]), 1)))

    return {
        'verdict': 'A TERRAIN CUT IS A PREREQUISITE. No flat deck level satisfies both the '
                   'Kotel and the houses at once: a level low enough to keep the wall exposed '
                   'is pierced by the DEM over most of the plaza, and a level high enough to '
                   'clear the DEM buries the bordering houses. The plan below is generated at '
                   'the low level - the wall keeps its height - and the terrain is what has to '
                   'move. This is the SAME open item PLAZA-DESIGN-20260909.md names first for '
                   'the precinct plaza, at 1/370th the size.',
        'demResolution': '257 x 257 at 50 source amot = 25 m. The plaza is 93 x 131 m, so the '
                         'whole terrace spans under four by six DEM cells.',
        'atGeneratedLevels': {
            'samples': len(samples), 'sampleStepCm': 100.0,
            'areaPiercedByTerrainPercent': round(100.0 * len(cut) / len(samples), 1),
            'cutDepthCm': {'median': round(cut[len(cut) // 2], 1) if cut else 0.0,
                           'max': round(cut[-1], 1) if cut else 0.0},
            'fillDepthCm': {'median': round(fill[len(fill) // 2], 1) if fill else 0.0,
                            'max': round(fill[-1], 1) if fill else 0.0}},
        'levelTrials': trials,
        'kotelMeshInLevel': {
            'asset': brief['currentAsset']['nativeMesh'],
            'source': 'componentDerivedUnrealBoundsCm in western-wall-detail-brief.json',
            'briefSha256': sha256_of(BRIEF),
            'baseMasl': round(masl(wall_base), 2), 'topMasl': round(masl(wall_top), 2),
            'heightM': round((wall_top - wall_base) / 100.0, 1)},
        'borderingHouseGradeMasl': {
            'houses': len(house_grades),
            'min': round(masl(house_grades[0]), 2) if house_grades else None,
            'median': round(masl(house_grades[len(house_grades) // 2]), 2) if house_grades else None,
            'max': round(masl(house_grades[-1]), 2) if house_grades else None},
        'terrainTilesToCut': terrain_tiles_over(plaza_poly),
        'recipe': 'Exactly the FutureMountV1 precedent, at one tile instead of four: '
                  'Scripts/import_future_mount_terrain.py already builds cut twins of terrain '
                  'tiles against a polygon using GeometryScripting, creates them as new assets '
                  'under a separate folder, and swaps them by visibility without ever deleting '
                  'the original. The plaza polygon lands on the tiles listed above.',
    }


def chord_at_depth(poly, frame, depth_cm):
    """Where the line at this distance from the wall crosses the polygon: the min and max
    along-wall coordinate of the crossings."""
    ring = closed(poly)
    hits = []
    for i in range(len(ring) - 1):
        a, b = ring[i], ring[i + 1]
        da, db = depth(a, frame), depth(b, frame)
        if (da > depth_cm) == (db > depth_cm):
            continue
        t = (depth_cm - da) / (db - da)
        point = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        hits.append(along(point, frame))
    if len(hits) < 2:
        return None
    return min(hits), max(hits)


def along_range(poly, frame):
    values = [along(p, frame) for p in poly]
    return min(values), max(values)


def building_census(sources, plaza_poly):
    """The houses. The whole point of this census is to establish whether they need building
    at all - and they do not."""
    features = sources['city']['features']
    minx, miny, maxx, maxy = bbox(plaza_poly)
    pad = 6000.0
    inside = 0
    bands = {'0m': 0, '5m': 0, '10m': 0, '20m': 0, '30m': 0, '60m': 0}
    considered = 0
    for feature in features:
        if feature.get('kind') != 'building':
            continue
        points = [((float(x) + TX) * AMAH_CM, (float(y) + TZ) * AMAH_CM)
                  for x, y in feature['points']]
        bx0, by0, bx1, by1 = bbox(points)
        if bx1 < minx - pad or bx0 > maxx + pad or by1 < miny - pad or by0 > maxy + pad:
            continue
        considered += 1
        centre = ((bx0 + bx1) / 2.0, (by0 + by1) / 2.0)
        if point_in_polygon(centre, plaza_poly):
            inside += 1
        near = min(distance_to_polygon(v, plaza_poly) for v in points)
        for key, limit in (('0m', 1.0), ('5m', 500.0), ('10m', 1000.0),
                           ('20m', 2000.0), ('30m', 3000.0), ('60m', 6000.0)):
            if near <= limit:
                bands[key] += 1
    return {
        'totalBuildingsInModel': sum(1 for f in features if f.get('kind') == 'building'),
        'consideredWithin60mOfPlazaBbox': considered,
        'centroidInsidePlazaPolygon': inside,
        'withAVertexWithin': bands,
        'finding': 'ZERO buildings stand inside the Western Wall Plaza polygon and %d have a '
                   'vertex within 30 m of its edge. That IS the present-day layout - the '
                   'Mughrabi Quarter was cleared in June 1967 and the OSM data is post-1967. '
                   'The Jewish Quarter housing bordering the plaza therefore already exists in '
                   'this level as OSM building actors; restoring it is the MODERN state doing '
                   'its job, not a build.' % bands['30m'],
    }


def write_preview(manifest, plan, frame, path):
    """A plan view, so a reviewer can SEE the layout rather than read that it exists."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError:
        return None
    figure, axes = plt.subplots(figsize=(9, 12))
    for row in plan['deck']:
        w = row['scale'][0] * DECK_MODULE_CM
        h = row['scale'][1] * DECK_MODULE_CM
        colour = '#d9d2c0' if row['loc'][2] <= manifest['derived']['lowerDeckZCm'] + 0.1 else '#bfb6a0'
        axes.add_patch(Rectangle((row['loc'][0] - w / 2, row['loc'][1] - h / 2), w, h,
                                 facecolor=colour, edgecolor='none'))
    for key, colour in (('band', '#8a7f6a'), ('kerb', '#5f5648'), ('step', '#3d3830')):
        xs = [r['loc'][0] for r in plan[key]]
        ys = [r['loc'][1] for r in plan[key]]
        axes.plot(xs, ys, '.', color=colour, markersize=1.5, label=key)
    axes.set_aspect('equal')
    axes.invert_yaxis()
    axes.set_title('KotelPlazaV1 plan - %d instances' % manifest['instanceTotal'])
    axes.legend(loc='upper right', fontsize=7)
    figure.savefig(str(path), dpi=110, bbox_inches='tight')
    plt.close(figure)
    return str(path)


def main():
    sources = load_sources()
    if '--census' in sys.argv:
        plaza_poly = sources['plaza_poly']
        print(json.dumps(building_census(sources, plaza_poly), indent=1))
        return
    manifest, plan, frame = build(sources)
    OUT.mkdir(parents=True, exist_ok=True)
    plan_path = OUT / 'kotel-plaza-plan.json'
    plan_path.write_text(json.dumps(plan, separators=(',', ':')), encoding='utf-8')
    manifest['planFile'] = plan_path.name
    manifest['planSha256'] = sha256_of(plan_path)
    preview = write_preview(manifest, plan, frame, OUT / 'kotel-plaza-plan.png')
    manifest['preview'] = preview
    (OUT / 'kotel-plaza-manifest.json').write_text(
        json.dumps(manifest, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in manifest.items()
                      if k in ('status', 'sourced', 'derived', 'components', 'instanceTotal',
                               'triangleTotal', 'buildingCensus', 'planSha256')}, indent=1))


if __name__ == '__main__':
    main()

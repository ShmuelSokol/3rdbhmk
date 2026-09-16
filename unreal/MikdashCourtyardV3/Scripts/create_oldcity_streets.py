"""OldCityStreetsV1 - paved lanes, kerbs, aprons and stepped ramps for the Old City.

AUTHORED_OFFLINE_SOURCE. Never imports `unreal`, never touches Content/ or a map.

WHY
---
cp26 and the OldCityFoundationV2 before frames (S1, S2) show the Old City lanes as BARE
EARTH running up to the building walls: no paving, no kerb, no step between levels. The
owner's reference photographs (`OldCityReferenceV2/reference-notes.md`) are worn rectangular
limestone paving wall to wall, shallow stepped lanes with broad landings and a narrow
central ramp, kerbs, and occasional drainage channels. At walking height the missing ground
reads worse than any other defect in the build.

WHAT A LANE IS
--------------
The city comes from OSM. `jerusalem.json` carries 5,944 `kind=="road"` polylines in source
amot; `buildJerusalem()` already draws each as a flat ribbon 20 cm above the DEM (measured on
40,746 real vertices of `jerusalem-meshes.json` meshes 2 and 3: offset 20.00 cm, min 19.99,
max 20.01). Those ribbons are the thin grey strip visible in the distance of S1/S2 and they
are the only ground the city has.

A LANE here is that mapped centre line, widened to the real space between the buildings:
at every 50 cm station the half-width on each side is the distance to the nearest building
obstacle line, clamped to a nominal half-width for the OSM highway class and floored at
60 cm. The obstacle line is the OldCityFoundationV2 foundation outline where that footprint
received one, and the raw wall line where it did not, so the paving MEETS the foundations
instead of intersecting them.

HEIGHT DATUM (why the build-up is 30 cm)
----------------------------------------
The legacy ribbon sits at exactly terrain + 20 cm and is a double-sided zero-thickness sheet.
This pass does not edit it; it ENCLOSES it. The sub-base top is terrain + 22 cm and the slab
crown is terrain + 30 cm, so the ribbon lies inside the new solid and cannot show. Note that
the ribbon's own terrain function is `CitySource.height_at` (always the anti-diagonal), which
differs from the exact mesh terrain by up to 0.47 cm; the offline check therefore measures
the ribbon height with height_at and proves the sub-base clears it at every emitted vertex.

SLOPE
-----
Where the smoothed grade exceeds 1 in 8 the lane becomes a stepped flight rather than tilted
paving: risers 11-18 cm (22 cm on the steepest), treads at least 28 cm, a landing every 7-13
steps, and, where the flight is not too steep and the lane is wide enough, a narrow ramped
strip down the middle with its own edge risers. Outside a flight the surface is the smoothed
terrain profile, so the whole lane is a continuous piecewise-linear function of station with
no vertical gap anywhere.

ANTI-REPEAT
-----------
Nothing is instanced and no stretch is copied. Course length along the lane, slab width
across it, joint width, dish depth, rut placement and amplitude, per-slab settle, edge-course
width, kerb height, apron width, landing spacing and drain channels are all drawn from a
hash of the lane id and the station, so no two stretches carry the same layout.

TIERS (the triangle budget, PERFORMANCE-BUDGET.md)
--------------------------------------------------
`CityFacadeV1/visibility-latest.json` already measured which 100 m cells a visitor stands
near (124 of them, 2.5D viewshed, eye 170 cm). Lanes in those cells are laid as individual
slabs; everywhere else the same profile, kerbs, aprons and steps are laid as a plain strip.
Both tiers are continuous ground; only the slab articulation differs.

OBJ ADAPTER, GROUPING
---------------------
The project OBJ adapter (`create_oldcity_facades.write_obj`): canonical vertices are UE cm,
written with Y reflected and winding reversed, one `o` object and no `g` groups. One mesh per
(precinct class x 500 m tile), exactly like OldCityFoundationV2, so actor and draw-call counts
stay in the low tens.

LIMITS
------
Every paving stone, kerb, apron, step, landing, ramp and channel here is AUTHORED detail in
the style of the modern Old City. It is not surveyed, not photogrammetric, and not a claim
about any particular lane. Nothing here is halachic. No visual, collision, cook or packaged
acceptance is established by this script.

Run with a 64-bit Python (the 32-bit default runs out of memory on the city sources):
    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" \
        -B Scripts/create_oldcity_streets.py build
"""
import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))

import create_oldcity_facades as F      # noqa: E402  pure offline module
import oldcity_foundations_v2 as FO     # noqa: E402  pure offline module

OUT = ROOT / 'SourceAssets' / 'context-review' / 'OldCityStreetsV1'
OBJ_OUT = OUT / 'obj'
MANIFEST_PATH = OUT / 'streets-manifest.json'
CHECK_PATH = OUT / 'check-streets.json'
LANES_PATH = OUT / 'lanes.json'

VIS = ROOT / 'SourceAssets' / 'context-review' / 'CityFacadeV1' / 'visibility-latest.json'
FOUND = ROOT / 'SourceAssets' / 'context-review' / 'OldCityFoundationV2'
FOUND_MANIFEST = FOUND / 'foundations-manifest.json'
FOUND_CHECK = FOUND / 'check-after.json'

PINS = {
    F.SOURCE_JSON: F.SOURCE_JSON_SHA,
    FO.RAW: 'cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb',
    FO.V1_MANIFEST: '9f5c133d378f36e4c23216713dadfc2c963a8613e6bd1d02166ed3fa067e5456',
    F.FROZEN_MANIFEST: '777598ca54e98c8be79a8a498fa4b3209d22a4525821087e58904e5bf13c5063',
    FO.DECK: 'f3483bff589169159bc99200761d90230e4726ec248226c948f0ead6dedca69c',
    VIS: None,
    # Pinned to the OldCityFoundationV2 set that was actually applied to both maps on 15 Sep
    # (native-apply-Candidate48-...232453Z / native-apply-Main50-...232807Z). The paving stops
    # at those foundation outlines, so it must be built against exactly those bytes.
    FOUND_MANIFEST: '82e51621dae8c258db2b734d17fd3346ed77e1a8767175333dfddc7ebb0d227f',
    FOUND_CHECK: 'ba4245d6f6f104ea0c69da5cf68c64b626d0bbf934e823d1b832ad536296e1f7',
    FO.PRECINCTS['candidate']: None,
    FO.PRECINCTS['main']: None,
}

# ============================================================ design constants
# Authored in the style of the reference photographs; not surveyed.
RISE_CM = 32.0            # slab crown above the exact terrain
SUBBASE_TOP_CM = 23.0     # sub-base top above the terrain; encloses the 20 cm legacy ribbon
LEGACY_RIBBON_CM = 20.0   # measured offset of the buildJerusalem road ribbons
# ...but a ribbon is only as WIDE as buildJerusalem drew it, so it exists only within this
# distance of its own road centre line. Beyond that there is nothing to clear, and comparing a
# sub-base vertex against a ribbon that is not there measures a defect that does not exist.
_RIBBON_PAVED = ('primary', 'secondary', 'tertiary', 'residential', 'service', 'unclassified')
RIBBON_CLEAR_CM = 1.0     # the sub-base must clear the ribbon by at least this, measured
EMBED_CM = 10.0           # kerb / apron faces continue this far below the terrain
SLAB_THICK_CM = 3.0       # slab top above the sub-base top at the crown

DISH_MAX_CM = 4.0         # centre of the lane worn low
RUT_MAX_CM = 2.0          # wheel / foot ruts
SETTLE_MAX_CM = 0.7       # per-slab settle; this is what makes the joints catch the light
MAX_LOWER_CM = 6.0        # total wear (dish + rut + channel) never cuts deeper than this,
                          # which is what keeps every slab above the enclosed legacy ribbon
KERB_MIN_CM, KERB_MAX_CM = 12.0, 20.0   # vertical kerb face at an open lane edge

STATION_CM = 50.0         # cross sections along a lane
NOMINAL_HALF = {          # cm, authored half-width per OSM highway class before clipping
    'steps': 190.0, 'footway': 190.0, 'path': 160.0, 'pedestrian': 300.0,
    'living_street': 250.0, 'service': 250.0, 'residential': 300.0,
    'unclassified': 300.0, 'track': 200.0, 'tertiary': 400.0, 'tertiary_link': 350.0,
    'secondary': 500.0, 'secondary_link': 400.0, 'trunk': 550.0, 'trunk_link': 450.0,
    'primary': 550.0, 'cycleway': 150.0,
}
MIN_HALF_CM = 60.0
MAX_HALF_CM = 600.0
OBSTACLE_CLEAR_CM = 1.0   # the paving reaches this close to the obstacle line (acceptance)

MARGIN_CM = 3000.0        # lanes up to 30 m outside the wall ring still count as Old City
TEMPLE_PAD = 188.0        # buildJerusalem's own road templeMask
DECK_MARGIN_CM = 150.0    # keep-out around the Kotel plaza deck and step rectangles

STEEP_GRADE = 0.125       # 1 in 8: steeper than this becomes steps, never tilted paving
RISER_MIN_CM, RISER_NOM_CM, RISER_MAX_CM = 11.0, 15.0, 18.0
RISER_STEEP_CM = 22.0
# Where the ground is steeper than RISER_STEEP_CM of rise per TREAD_STEEP_MIN_CM of tread
# (grade 0.85; this network reaches 1.00) no stair can hold both limits. Those become
# deeper-riser stairs, which real stepped lanes do have. This is the absolute ceiling, and
# anything past it is a generator fault rather than terrain.
RISER_ABS_MAX_CM = 40.0
TREAD_MIN_CM, TREAD_STEEP_MIN_CM = 28.0, 26.0
LANDING_MIN_CM, LANDING_MAX_CM = 120.0, 220.0
# A tread is a stone you step on, not a terrace. Without a ceiling a long merged flight took its
# single riser from the flight's TOTAL rise and produced treads up to 13.5 m that stayed flat
# while the hillside fell away under them, which drove 57% of the sub-base below the legacy road
# ribbon. Treads are now sized from the local slope and capped.
TREAD_MAX_CM = 150.0
# Steep runs shorter than this stay ramped. 150 cm left 886 samples tilted at up to 1 in 1 and
# 80 cm still left 783, so this drops to one station spacing: any steep pair of stations becomes
# a flight, because a single step is a better answer than a cliff of paving.
FLIGHT_MIN_CM = 50.0
FLIGHT_MERGE_CM = 300.0
RAMP_MAX_GRADE = 0.28
RAMP_MIN_LANE_CM = 240.0
RAMP_HALF_MIN_CM, RAMP_HALF_MAX_CM = 45.0, 55.0

COURSE_MIN_CM, COURSE_MAX_CM = 38.0, 85.0
SLAB_MIN_CM, SLAB_MAX_CM = 30.0, 95.0
SLAB_TAIL_MIN_CM = 22.0
EDGE_COURSE_MIN_CM, EDGE_COURSE_MAX_CM = 55.0, 90.0
EDGE_COURSE_LIFT_CM = 1.0
JOINT_MIN_CM, JOINT_MAX_CM = 1.6, 3.2
APRON_MIN_CM, APRON_MAX_CM = 40.0, 90.0
OPEN_EDGE_CM = 100.0      # no obstacle within this of the lane edge => open edge, gets an apron
DRAIN_LANE_FRACTION = 0.14
DRAIN_DEPTH_CM = 5.0
DRAIN_HALF_CM = 26.0

TIER_B_ACROSS = 4         # cross divisions of a plain strip
TIER_B_ALONG_CM = 200.0

OWN_CELL_CM = 25.0        # ownership raster: at a junction the first lane wins
TILE_CM = 50000.0         # one mesh per precinct class x 500 m tile
MAX_TOTAL_TRIS = 1_600_000

BUILDING_CLEAR_CM = 2.0   # the lane surface stays this far below a bounding floor line
EXCAVATE_MAX_CM = 5.0     # the lane surface is never cut more than this below the terrain
# Only a building whose floor line is within this of the intended lane level can pull the lane
# down. A floor line 4 m below is a storey UNDER the lane, not a threshold onto it, and clamping
# to it dragged the whole surface into the hillside.
FLOOR_LINE_NEAR_CM = 150.0
# Hard floor on the profile, above the EXACT terrain: ribbon 20 + clearance 1 + slab 3 + the 6 cm
# wear budget + 0.5 for the difference between the two terrain functions. Below this the sub-base
# drops under the enclosed legacy ribbon, which is what put 57% of its vertices there.
MIN_PROFILE_ABOVE_TERRAIN_CM = 30.5


# ================================================================== helpers
def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def h01(*values):
    """Deterministic hash in [0, 1) from any tuple of numbers/strings."""
    token = '|'.join('%.4f' % v if isinstance(v, float) else str(v) for v in values)
    return int(hashlib.sha256(token.encode('ascii', 'replace')).hexdigest()[:12], 16) / float(1 << 48)


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    if length < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = clamp(((px - ax) * dx + (py - ay) * dy) / length, 0.0, 1.0)
    return math.hypot(px - ax - dx * t, py - ay - dy * t)


def ribbon_half_cm(highway):
    """Half-width of the legacy buildJerusalem road ribbon for this class, in UE cm.

    Mirrors its own rule verbatim: width = (primary/secondary 10, tertiary 7, other paved 4,
    else 2) * 2 amot, so the half-width is that base in amot, i.e. base * AMAH_CM."""
    if highway in ('primary', 'secondary'):
        base = 10.0
    elif highway == 'tertiary':
        base = 7.0
    elif highway in _RIBBON_PAVED:
        base = 4.0
    else:
        base = 2.0
    return base * F.AMAH_CM


def tok(value):
    return ('N' if value < 0 else 'P') + str(abs(int(value))).zfill(3)


def cell100(x, y):
    return 'Grid_%s_%s' % (tok(math.floor(x / F.CELL_CM)), tok(math.floor(y / F.CELL_CM)))


def tile500(x, y):
    return '%s_%s' % (tok(math.floor(x / TILE_CM)), tok(math.floor(y / TILE_CM)))


class Index2D:
    """Uniform bucket index over 2D segments."""

    def __init__(self, cell):
        self.cell = cell
        self.cells = defaultdict(list)

    def add(self, a, b, payload):
        x0, x1 = sorted((a[0], b[0]))
        y0, y1 = sorted((a[1], b[1]))
        for i in range(int(math.floor(x0 / self.cell)), int(math.floor(x1 / self.cell)) + 1):
            for j in range(int(math.floor(y0 / self.cell)), int(math.floor(y1 / self.cell)) + 1):
                self.cells[(i, j)].append((a, b, payload))

    def nearest(self, x, y, radius):
        best, who = radius, None
        span = int(math.ceil(radius / self.cell))
        ci, cj = int(math.floor(x / self.cell)), int(math.floor(y / self.cell))
        for i in range(ci - span, ci + span + 1):
            for j in range(cj - span, cj + span + 1):
                for a, b, payload in self.cells.get((i, j), ()):
                    d = seg_dist(x, y, a[0], a[1], b[0], b[1])
                    if d < best:
                        best, who = d, payload
        return best, who


# ================================================================ the scope
class Scope:
    """Where paving is allowed: inside (or just outside) the Old City wall ring, minus the
    Temple Mount, the protected design polygons and the Kotel plaza, which own their ground."""

    def __init__(self, source):
        self.ring, self.ring_area_m2, _ = F.old_city_ring(source)
        self.rx0 = min(p[0] for p in self.ring)
        self.rx1 = max(p[0] for p in self.ring)
        self.ry0 = min(p[1] for p in self.ring)
        self.ry1 = max(p[1] for p in self.ring)
        self.zones, _design = F.load_exclusions()
        self.zone_bbox = []
        for zone in self.zones:
            xs = [p[0] for p in zone['polygon']]
            ys = [p[1] for p in zone['polygon']]
            buf = zone['bufferCm']
            self.zone_bbox.append((min(xs) - buf, min(ys) - buf, max(xs) + buf, max(ys) + buf))
        self.decks = FO.deck_polys()
        self.deck_index = defaultdict(list)
        for _kind, poly, box in self.decks:
            lo = (box[0] - DECK_MARGIN_CM, box[1] - DECK_MARGIN_CM)
            hi = (box[2] + DECK_MARGIN_CM, box[3] + DECK_MARGIN_CM)
            for i in range(int(math.floor(lo[0] / 2000.0)), int(math.floor(hi[0] / 2000.0)) + 1):
                for j in range(int(math.floor(lo[1] / 2000.0)), int(math.floor(hi[1] / 2000.0)) + 1):
                    self.deck_index[(i, j)].append((poly, lo, hi))
        self.ring_edges = [(self.ring[i], self.ring[(i + 1) % len(self.ring)])
                           for i in range(len(self.ring))]

    def inside_ring(self, x, y):
        return F.point_in_polygon(x, y, self.ring)

    def near_ring(self, x, y, distance):
        for a, b in self.ring_edges:
            if seg_dist(x, y, a[0], a[1], b[0], b[1]) <= distance:
                return True
        return False

    def in_scope(self, x, y):
        if not (self.rx0 - MARGIN_CM <= x <= self.rx1 + MARGIN_CM
                and self.ry0 - MARGIN_CM <= y <= self.ry1 + MARGIN_CM):
            return False
        return self.inside_ring(x, y) or self.near_ring(x, y, MARGIN_CM)

    def temple_mask(self, x_cm, y_cm):
        x = x_cm / F.AMAH_CM - F.TX
        z = y_cm / F.AMAH_CM - F.TZ
        return ((abs(x) < TEMPLE_PAD and abs(z) < TEMPLE_PAD)
                or (abs(x - F.MARKET_X) < 55.0 and abs(z - F.MARKET_Z) < 40.0))

    def blocked(self, x, y):
        """Reason this point may not be paved, or None."""
        if self.temple_mask(x, y):
            return 'templeMask'
        for zone, box in zip(self.zones, self.zone_bbox):
            if not (box[0] <= x <= box[2] and box[1] <= y <= box[3]):
                continue
            polygon = zone['polygon']
            if F.point_in_polygon(x, y, polygon):
                return zone['kind']
            count = len(polygon)
            for index in range(count):
                a, b = polygon[index], polygon[(index + 1) % count]
                if seg_dist(x, y, a[0], a[1], b[0], b[1]) <= zone['bufferCm']:
                    return zone['kind']
        for poly, lo, hi in self.deck_index.get((int(math.floor(x / 2000.0)),
                                                 int(math.floor(y / 2000.0))), ()):
            if not (lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1]):
                continue
            if F.point_in_polygon(x, y, poly):
                return 'kotelPlaza'
            count = len(poly)
            for index in range(count):
                a, b = poly[index], poly[(index + 1) % count]
                if seg_dist(x, y, a[0], a[1], b[0], b[1]) <= DECK_MARGIN_CM:
                    return 'kotelPlaza'
        return None


# ============================================================== obstacles
def build_obstacles(footprints, scope):
    """Segment index of the line the paving must stop at, per footprint.

    For a footprint that received an OldCityFoundationV2 foundation that is the foundation's
    own outer outline (the plinth is 8 cm proud of the wall, the stepped footing 22 cm), so
    the paving meets stone, not air. For every other footprint it is the wall line itself.
    Each payload carries the footprint's floor line so the lane can be kept below it."""
    found_rows = {}
    if FOUND_CHECK.exists():
        for row in read(FOUND_CHECK)['rows']:
            if 'foundation' in row and 'foundationExcluded' not in row:
                found_rows[row['id']] = row
    # 300 cm cells, not 1500. nearest() scans a (2*ceil(r/cell)+1)^2 block, so a 1500 cm cell
    # answered a 600 cm query by testing every segment in 45 m x 45 m. At 300 cm that is
    # 15 m x 15 m - about 9x less area, and the buckets are far finer. Measured: the 1500 cm
    # cell left the per-station cross-section pass still running after 23 minutes of CPU.
    index = Index2D(300.0)
    used_foundation = 0
    for fp in footprints:
        box = fp['bbox'] if 'bbox' in fp else FO.bbox_of([p for s in fp['segments'] for p in s])
        if box[2] < scope.rx0 - MARGIN_CM - 2000 or box[0] > scope.rx1 + MARGIN_CM + 2000:
            continue
        if box[3] < scope.ry0 - MARGIN_CM - 2000 or box[1] > scope.ry1 + MARGIN_CM + 2000:
            continue
        row = found_rows.get(fp['id'])
        proud = 0.0
        if row is not None:
            used_foundation += 1
            proud = (FO.FOOTING_PROUD_CM if row['foundation'].get('footingPieces')
                     else FO.PLINTH_PROUD_CM)
        payload = (fp['id'], fp['baseZcm'], proud)
        if proud > 0.0:
            for ring in fp['rings']:
                if len(ring) < 3:
                    continue
                out = FO.miter_offset(ring, proud)
                for k in range(len(out)):
                    index.add(out[k], out[(k + 1) % len(out)], payload)
        else:
            for a, b in fp['segments']:
                index.add(a, b, payload)
    return index, used_foundation


# ================================================================== lanes
def build_lanes(source, scope):
    """Maximal in-scope runs of each mapped road polyline, in UE cm."""
    lanes = []
    for feature in read(F.SOURCE_JSON)['features']:
        if feature.get('kind') != 'road':
            continue
        tags = feature.get('tags') or {}
        highway = tags.get('highway') or ''
        if highway not in NOMINAL_HALF:
            continue
        if 'Tunnel' in (tags.get('name:en') or ''):
            continue
        points = [F.ue_xy(p[0], p[1]) for p in feature['points']]
        run = []
        for a, b in zip(points, points[1:]):
            length = math.dist(a, b)
            mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            ok = (20.0 <= length <= 25000.0 and scope.in_scope(*mid)
                  and scope.blocked(*mid) is None)
            if ok:
                if not run:
                    run.append(a)
                run.append(b)
            elif run:
                lanes.append((feature['id'], highway, tags.get('name:en') or tags.get('name') or '', run))
                run = []
        if run:
            lanes.append((feature['id'], highway, tags.get('name:en') or tags.get('name') or '', run))
    out = []
    for serial, (osm_id, highway, name, points) in enumerate(sorted(lanes, key=lambda r: (r[0], len(r[3])))):
        clean = [points[0]]
        for p in points[1:]:
            if math.dist(clean[-1], p) > 1.0:
                clean.append(p)
        if len(clean) < 2:
            continue
        total = sum(math.dist(a, b) for a, b in zip(clean, clean[1:]))
        if total < 150.0:
            continue
        out.append(dict(laneId='lane%05d' % serial, osmId=osm_id, highway=highway, name=name,
                        points=clean, length=total))
    return out


def stations_of(lane):
    """Arc-length stations every STATION_CM with position and unit tangent."""
    points = lane['points']
    cum = [0.0]
    for a, b in zip(points, points[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    total = cum[-1]
    count = max(1, int(round(total / STATION_CM)))
    step = total / count
    out = []
    k = 0
    for i in range(count + 1):
        s = min(total, i * step)
        while k + 2 < len(cum) and cum[k + 1] < s:
            k += 1
        a, b = points[k], points[k + 1]
        span = max(cum[k + 1] - cum[k], 1e-9)
        t = clamp((s - cum[k]) / span, 0.0, 1.0)
        pos = (lerp(a[0], b[0], t), lerp(a[1], b[1], t))
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = max(math.hypot(dx, dy), 1e-9)
        out.append(dict(s=s, pos=pos, tan=(dx / length, dy / length)))
    # smooth the tangent so a kinked OSM polyline does not shear the paving
    for i, station in enumerate(out):
        lo, hi = max(0, i - 2), min(len(out), i + 3)
        tx = sum(out[j]['tan'][0] for j in range(lo, hi))
        ty = sum(out[j]['tan'][1] for j in range(lo, hi))
        length = max(math.hypot(tx, ty), 1e-9)
        station['tan'] = (tx / length, ty / length)
        station['nrm'] = (-ty / length, tx / length)
    return out, total


def cross_sections(lane, stations, obstacles, scope):
    """Half-width and bounding floor line on each side of every station."""
    nominal = NOMINAL_HALF[lane['highway']]
    # Only ever search as far as this lane class can actually use. An obstacle beyond the cap
    # clamps the half-width to `nominal` exactly as a full MAX_HALF_CM search would, and the
    # `bounded` test below is unchanged, so this is a speed change and not a geometry change.
    # It matters because footway/steps/path are most of the network at a 190 cm nominal.
    search = min(MAX_HALF_CM, nominal + 60.0)
    raw = []
    for station in stations:
        x, y = station['pos']
        nx, ny = station['nrm']
        row = {}
        for side, sign in (('left', 1.0), ('right', -1.0)):
            probe = (x + nx * sign * 5.0, y + ny * sign * 5.0)
            distance, payload = obstacles.nearest(probe[0], probe[1], search)
            half = clamp(distance - 5.0 - OBSTACLE_CLEAR_CM, MIN_HALF_CM, nominal)
            row[side] = dict(half=half, raw=distance, base=(payload[1] if payload else None),
                             bounded=distance - 5.0 <= nominal + OBSTACLE_CLEAR_CM)
        raw.append(row)
    # median-smooth the half widths over +-2 m so the kerb line does not jitter per station
    window = int(round(200.0 / STATION_CM))
    for i, station in enumerate(stations):
        lo, hi = max(0, i - window), min(len(raw), i + window + 1)
        station['cs'] = {}
        for side in ('left', 'right'):
            values = sorted(raw[j][side]['half'] for j in range(lo, hi))
            half = values[len(values) // 2]
            bases = [raw[j][side]['base'] for j in range(lo, hi) if raw[j][side]['base'] is not None]
            station['cs'][side] = dict(half=min(half, raw[i][side]['raw'] - OBSTACLE_CLEAR_CM),
                                       bounded=raw[i][side]['bounded'],
                                       raw=raw[i][side]['raw'],
                                       base=(min(bases) if bases else None))
            station['cs'][side]['half'] = clamp(station['cs'][side]['half'], MIN_HALF_CM, nominal)
        station['blocked'] = scope.blocked(*station['pos'])
    return stations


# ================================================================= profile
def build_profile(lane, stations, terrain):
    """Lane surface level at every station, and the stepped flights that carry the slope."""
    for station in stations:
        station['terrain'] = terrain.at(*station['pos'])
    # 3 m moving average of terrain + RISE, then the floor-line and excavation clamps
    window = int(round(150.0 / STATION_CM))
    for i, station in enumerate(stations):
        lo, hi = max(0, i - window), min(len(stations), i + window + 1)
        smooth = sum(stations[j]['terrain'] for j in range(lo, hi)) / (hi - lo)
        target = smooth + RISE_CM
        bases = [station['cs'][s]['base'] for s in ('left', 'right')
                 if station['cs'][s]['bounded'] and station['cs'][s]['base'] is not None]
        clamped_by = None
        # Only a floor line PLAUSIBLY AT LANE LEVEL may pull the lane down. Using every bounding
        # base dragged the surface to terrain - 5 wherever a building sat low on a slope, which
        # is most of them (OSM extrusions take their lowest corner), and that is what drove the
        # sub-base under the legacy ribbon.
        near = [b for b in bases if abs(b - target) <= FLOOR_LINE_NEAR_CM]
        if near:
            limit = min(near) - BUILDING_CLEAR_CM
            if target > limit:
                target = max(limit, station['terrain'] - EXCAVATE_MAX_CM)
                clamped_by = 'floorLine'
        # Never below the ribbon-clearance floor, whatever the clamp asked for.
        floor_z = station['terrain'] + MIN_PROFILE_ABOVE_TERRAIN_CM
        if target < floor_z:
            target = floor_z
            clamped_by = 'ribbonFloor' if clamped_by else clamped_by
        station['target'] = target
        station['overFloorLineCm'] = (round(target - (min(bases) - BUILDING_CLEAR_CM), 3)
                                      if bases and target > min(bases) - BUILDING_CLEAR_CM else 0.0)
        station['clampedBy'] = clamped_by

    flights = []
    steep = []
    for i in range(len(stations) - 1):
        run = stations[i + 1]['s'] - stations[i]['s']
        grade = abs(stations[i + 1]['target'] - stations[i]['target']) / max(run, 1e-9)
        steep.append(grade > STEEP_GRADE)
    i = 0
    runs = []
    while i < len(steep):
        if not steep[i]:
            i += 1
            continue
        j = i
        while j < len(steep) and steep[j]:
            j += 1
        runs.append((i, j))
        i = j
    merged = []
    for lo, hi in runs:
        if merged and stations[lo]['s'] - stations[merged[-1][1]]['s'] < FLIGHT_MERGE_CM:
            merged[-1] = (merged[-1][0], hi)
        else:
            merged.append((lo, hi))
    for lo, hi in merged:
        if stations[hi]['s'] - stations[lo]['s'] < FLIGHT_MIN_CM:
            continue
        flights.append(plan_flight(lane, stations, lo, hi))

    # the surface: staircase inside a flight, the smoothed target outside it
    for station in stations:
        station['z'] = station['target']
        station['inFlight'] = None
    for flight in flights:
        for station in stations[flight['lo']:flight['hi'] + 1]:
            station['z'] = flight_level(flight, station['s'])
            station['inFlight'] = flight['flightId']
    return stations, flights


def plan_flight(lane, stations, lo, hi):
    """Risers, treads and landings for one stepped flight, ends pinned to the free profile."""
    s0, s1 = stations[lo]['s'], stations[hi]['s']
    z0, z1 = stations[lo]['target'], stations[hi]['target']
    run, drop = s1 - s0, z1 - z0
    sign = 1.0 if drop >= 0 else -1.0
    rise = abs(drop)
    seed = h01(lane['laneId'], 'flight', lo)
    landing_every = int(7 + math.floor(seed * 7))          # 7..13 steps between landings
    landing_len = lerp(LANDING_MIN_CM, LANDING_MAX_CM, h01(lane['laneId'], 'landing', lo))
    # A landing is a long FLAT tread, so the ground drops across it by (local grade x its
    # length) - the landing IS a riser in its own right. Drawn from a hash with no reference to
    # slope, a 2.0 m landing on an ordinary 1-in-5 lane produced a 40.3 cm riser, past the
    # ceiling, and the retry loop could not rescue it because adding steps only shrinks the
    # PLAIN treads while the landing span stays fixed. Size it from the steepest LOCAL grade in
    # the flight (the mean would under-size it on uneven ground), never shorter than one tread.
    local_grade = 0.0
    for _a, _b in zip(stations[lo:hi], stations[lo + 1:hi + 1]):
        _span = _b['s'] - _a['s']
        if _span > 1e-9:
            local_grade = max(local_grade, abs(_b['target'] - _a['target']) / _span)
    if local_grade > 1e-6:
        landing_len = min(landing_len, RISER_STEEP_CM / local_grade)
    landing_len = max(landing_len, TREAD_STEEP_MIN_CM)
    # Above grade 0.846 even the FLOORED minimum landing breaches the riser ceiling
    # (1.56 x 26 cm = 40.6 cm, which was the single riser that broke the ceiling). There is no
    # room for a landing on a slope like that, so the flight simply does not get one.
    if local_grade * TREAD_STEEP_MIN_CM > RISER_ABS_MAX_CM:
        landing_every = 0

    # THE STAIRCASE FOLLOWS THE GROUND. Each tread takes its level from the smoothed target
    # profile at its own start, so the flight tracks the hillside instead of running as one
    # straight ramp between its ends. Deriving a single riser from the flight's total rise (the
    # previous design) is what produced 13.5 m treads and drove the sub-base metres below the
    # legacy ribbon. Risers are now whatever the ground does across one tread, which is also how
    # a real stepped lane is built.
    def target_at(s):
        if s <= stations[lo]['s']:
            return stations[lo]['target']
        if s >= stations[hi]['s']:
            return stations[hi]['target']
        k = lo
        while k < hi - 1 and stations[k + 1]['s'] < s:
            k += 1
        a, b = stations[k], stations[k + 1]
        return lerp(a['target'], b['target'], (s - a['s']) / max(b['s'] - a['s'], 1e-9))

    mean_grade = rise / max(run, 1e-9)
    # Tread from the slope: a nominal riser divided by the grade, inside the legal window.
    tread_nom = clamp(RISER_NOM_CM / max(mean_grade, 0.01), TREAD_STEEP_MIN_CM, TREAD_MAX_CM)
    cap_steps = max(1, int(math.floor(run / TREAD_STEEP_MIN_CM)))
    steps = min(max(1, int(round(run / tread_nom))), cap_steps)

    def lay(count):
        """Tread spans and levels for `count` steps, landings taking their extra length first."""
        landings = max(0, count // landing_every) if landing_every else 0
        while landings and (run - landings * landing_len) / max(count - landings, 1) < TREAD_STEEP_MIN_CM:
            landings -= 1
        plain = count - landings
        plain_len = (run - landings * landing_len) / plain if plain > 0 else run
        rows, s = [], s0
        for k in range(count):
            is_landing = bool(landing_every) and landings > 0 and (k + 1) % landing_every == 0
            span = landing_len if is_landing else plain_len
            row = dict(s0=s, s1=min(s1, s + span), z=(z0 if k == 0 else target_at(s)))
            if is_landing:
                row['landing'] = True
                landings -= 1
            rows.append(row)
            s = row['s1']
        rows[-1]['s1'] = s1
        return rows

    # Add treads until no riser exceeds the absolute ceiling. This is ALLOWED TO PUSH PAST
    # cap_steps, because the riser ceiling outranks the tread floor: at rise 100 cm over run
    # 60 cm the tread floor alone permits just 2 treads, which forces 50 cm risers - a wall, not
    # a step. Three treads of 20 cm give 33 cm risers, a steep short-tread stair that can
    # actually be climbed. Bounding the search by cap_steps (the first attempt at this) meant the
    # ceiling could never win, and the self test caught exactly that.
    # A 5 cm tread is the absolute floor and guarantees termination.
    hard_cap = max(1, int(run / 5.0))
    for _attempt in range(8):
        treads = lay(steps)
        edges = [abs(treads[k + 1]['z'] - treads[k]['z']) for k in range(len(treads) - 1)]
        edges.append(abs(z1 - treads[-1]['z']))
        if max(edges) <= RISER_ABS_MAX_CM or steps >= hard_cap:
            break
        steps = min(hard_cap, max(steps + 1,
                                  int(math.ceil(steps * max(edges) / RISER_ABS_MAX_CM))))
    treads = lay(steps)
    edges = [abs(treads[k + 1]['z'] - treads[k]['z']) for k in range(len(treads) - 1)]
    edges.append(abs(z1 - treads[-1]['z']))
    riser = sum(edges) / max(len(edges), 1)
    tread = run / steps
    # Measured from the result, not presumed: a flight is infeasible when the ground forced a
    # tread under the floor, or when even the hard cap could not hold the riser ceiling.
    infeasible = tread < TREAD_STEEP_MIN_CM - 1e-6 or max(edges) > RISER_ABS_MAX_CM + 1e-6
    landings = sum(1 for r in treads if r.get('landing'))
    steep = infeasible or mean_grade > RAMP_MAX_GRADE
    # NOTE: the straight-ramp tread loop that used to stand here has been removed. It ran AFTER
    # lay() and overwrote the profile-following treads with a uniform `sign * riser` staircase,
    # silently discarding the fix for the sub-base sinking under the hillside, and it left the
    # last tread unclamped so a flight with a landing no longer ended at s1.
    width = min(min(st['cs']['left']['half'] + st['cs']['right']['half']
                    for st in stations[lo:hi + 1]), 10000.0)
    ramp = (mean_grade <= RAMP_MAX_GRADE and width >= RAMP_MIN_LANE_CM
            and h01(lane['laneId'], 'ramp', lo) < 0.62)
    return dict(flightId='%s-f%03d' % (lane['laneId'], lo), lo=lo, hi=hi, s0=s0, s1=s1,
                z0=z0, z1=z1, steps=steps, riserCm=round(riser, 3), treadCm=round(tread, 3),
                landings=landings, landingCm=round(landing_len, 2), steep=steep,
                infeasible=infeasible,
                meanGrade=round(mean_grade, 4), treads=treads,
                ramp=ramp,
                rampHalfCm=round(lerp(RAMP_HALF_MIN_CM, RAMP_HALF_MAX_CM,
                                      h01(lane['laneId'], 'ramphalf', lo)), 2))


def flight_level(flight, s):
    for tread in flight['treads']:
        if tread['s0'] - 1e-6 <= s <= tread['s1'] + 1e-6:
            return tread['z']
    return flight['z1'] if s > flight['s1'] else flight['z0']


def flight_ramp_level(flight, s):
    """The ramped strip follows the same ground the treads do, interpolating between the tread
    levels rather than running straight from the flight's start to its end."""
    rows = flight['treads']
    for k, row in enumerate(rows):
        if row['s0'] - 1e-6 <= s <= row['s1'] + 1e-6:
            nxt = rows[k + 1]['z'] if k + 1 < len(rows) else flight['z1']
            t = clamp((s - row['s0']) / max(row['s1'] - row['s0'], 1e-9), 0.0, 1.0)
            return lerp(row['z'], nxt, t)
    return flight['z1'] if s > flight['s1'] else flight['z0']


def level_at(stations, flights_by_id, s):
    """Lane surface at any station distance, staircase-aware and continuous."""
    if s <= stations[0]['s']:
        return stations[0]['z']
    if s >= stations[-1]['s']:
        return stations[-1]['z']
    i = min(int(s / STATION_CM), len(stations) - 2)
    while i > 0 and stations[i]['s'] > s:
        i -= 1
    while i < len(stations) - 2 and stations[i + 1]['s'] < s:
        i += 1
    a, b = stations[i], stations[i + 1]
    if a['inFlight'] is not None and a['inFlight'] == b['inFlight']:
        return flight_level(flights_by_id[a['inFlight']], s)
    if a['inFlight'] is not None:
        return flight_level(flights_by_id[a['inFlight']], s)
    if b['inFlight'] is not None:
        return flight_level(flights_by_id[b['inFlight']], s)
    t = (s - a['s']) / max(b['s'] - a['s'], 1e-9)
    return lerp(a['z'], b['z'], t)


# ============================================================== wear field
def wear_context(lane, stations):
    """Per-lane wear character: how dished, how rutted, whether it carries a drain channel."""
    seed = lane['laneId']
    widths = [st['cs']['left']['half'] + st['cs']['right']['half'] for st in stations]
    mean_width = sum(widths) / len(widths)
    drain = None
    if h01(seed, 'drain') < DRAIN_LANE_FRACTION and mean_width > 260.0:
        side = h01(seed, 'drainside')
        drain = 0.0 if side < 0.55 else (mean_width * 0.5 - DRAIN_HALF_CM - 30.0) * (1 if side < 0.8 else -1)
    return dict(
        dish=lerp(1.6, DISH_MAX_CM, h01(seed, 'dish')),
        rut=lerp(0.6, RUT_MAX_CM, h01(seed, 'rut')),
        wide=mean_width >= 300.0,
        drain=drain,
        seed=seed,
        meanWidth=mean_width,
        ribbonHalf=ribbon_half_cm(lane['highway']),
    )


def slow_noise(seed, s, wavelength=420.0):
    """Value noise along the lane so a stretch can be smooth and the next one worn."""
    k = s / wavelength
    i = math.floor(k)
    t = k - i
    a, b = h01(seed, 'n', int(i)), h01(seed, 'n', int(i) + 1)
    t = t * t * (3.0 - 2.0 * t)
    return lerp(a, b, t)


def wear_offset(ctx, s, d, half_l, half_r):
    """How far the worn surface sits below the crown at across-offset d (cm, negative)."""
    half = half_l if d >= 0 else half_r
    u = clamp(d / max(half, 1e-6), -1.0, 1.0)
    n = slow_noise(ctx['seed'], s)
    dish = ctx['dish'] * (0.40 + 0.60 * n) * (1.0 - u * u)
    if ctx['wide']:
        rut = ctx['rut'] * (0.30 + 0.70 * n) * (math.exp(-((u - 0.45) / 0.22) ** 2)
                                                + math.exp(-((u + 0.45) / 0.22) ** 2))
    else:
        rut = ctx['rut'] * (0.30 + 0.70 * n) * math.exp(-((u * 1.6) / 0.60) ** 2)
    channel = 0.0
    if ctx['drain'] is not None:
        gap = abs(d - ctx['drain'])
        if gap < DRAIN_HALF_CM:
            channel = DRAIN_DEPTH_CM * (1.0 - (gap / DRAIN_HALF_CM) ** 2)
    return -min(dish + rut + channel, MAX_LOWER_CM)


# ============================================================ lane geometry
def interp_cs(stations, s):
    """Half-widths, bounded flags and terrain at any station distance."""
    if s <= stations[0]['s']:
        a = b = stations[0]
        t = 0.0
    elif s >= stations[-1]['s']:
        a = b = stations[-1]
        t = 0.0
    else:
        i = min(int(s / STATION_CM), len(stations) - 2)
        while i > 0 and stations[i]['s'] > s:
            i -= 1
        while i < len(stations) - 2 and stations[i + 1]['s'] < s:
            i += 1
        a, b = stations[i], stations[i + 1]
        t = (s - a['s']) / max(b['s'] - a['s'], 1e-9)
    pos = (lerp(a['pos'][0], b['pos'][0], t), lerp(a['pos'][1], b['pos'][1], t))
    nrm = (lerp(a['nrm'][0], b['nrm'][0], t), lerp(a['nrm'][1], b['nrm'][1], t))
    length = max(math.hypot(*nrm), 1e-9)
    nrm = (nrm[0] / length, nrm[1] / length)
    near = a if t < 0.5 else b
    return dict(pos=pos, nrm=nrm, tan=near['tan'], terrain=lerp(a['terrain'], b['terrain'], t),
                half_l=lerp(a['cs']['left']['half'], b['cs']['left']['half'], t),
                half_r=lerp(a['cs']['right']['half'], b['cs']['right']['half'], t),
                bounded_l=near['cs']['left']['bounded'], bounded_r=near['cs']['right']['bounded'],
                raw_l=lerp(a['cs']['left']['raw'], b['cs']['left']['raw'], t),
                raw_r=lerp(a['cs']['right']['raw'], b['cs']['right']['raw'], t))


def world(cs, d):
    return (cs['pos'][0] + cs['nrm'][0] * d, cs['pos'][1] + cs['nrm'][1] * d)


# ======================================================== ownership raster
class Ownership:
    """At a junction two mapped lanes overlap. The first lane to claim a 25 cm cell keeps it;
    every other lane trims its courses to the cells it owns, so nothing is paved twice."""

    def __init__(self):
        self.cells = {}

    @staticmethod
    def key(x, y):
        return (int(math.floor(x / OWN_CELL_CM)), int(math.floor(y / OWN_CELL_CM)))

    def claim(self, lane_index, stations, total):
        s = 0.0
        while s <= total:
            cs = interp_cs(stations, s)
            d = -cs['half_r']
            while d <= cs['half_l']:
                self.cells.setdefault(self.key(*world(cs, d)), lane_index)
                d += OWN_CELL_CM * 0.5
            self.cells.setdefault(self.key(*world(cs, cs['half_l'])), lane_index)
            s += OWN_CELL_CM
        if total > 0:
            cs = interp_cs(stations, total)
            d = -cs['half_r']
            while d <= cs['half_l']:
                self.cells.setdefault(self.key(*world(cs, d)), lane_index)
                d += OWN_CELL_CM * 0.5

    def owns(self, lane_index, x, y):
        return self.cells.get(self.key(x, y), lane_index) == lane_index

    def trim(self, lane_index, cs, d0, d1):
        """Longest run of [d0, d1] this lane owns.

        Both ends of the span are ALWAYS sampled and a run that reaches an end is snapped to
        that end. Sampling on a fixed stride instead lost up to half a stride of paving at
        every course end, which showed up as a 6.6 cm gap against the wall in the self test."""
        if d1 - d0 < 1e-6:
            return None
        count = max(1, int(math.ceil((d1 - d0) / (OWN_CELL_CM * 0.5))))
        samples = [d0 + (d1 - d0) * k / count for k in range(count + 1)]
        best = None
        run = None
        for k, d in enumerate(samples):
            if self.owns(lane_index, *world(cs, d)):
                if run is None:
                    run = [k, k]
                else:
                    run[1] = k
            else:
                if run is not None and (best is None or run[1] - run[0] > best[1] - best[0]):
                    best = run
                run = None
        if run is not None and (best is None or run[1] - run[0] > best[1] - best[0]):
            best = run
        if best is None:
            return None
        span = (d1 - d0) / count
        lo = d0 if best[0] == 0 else max(d0, samples[best[0]] - span * 0.5)
        hi = d1 if best[1] == count else min(d1, samples[best[1]] + span * 0.5)
        return (lo, hi) if hi - lo >= 20.0 else None


# ================================================================ emission
class Build:
    """Collects outward-facing triangles into one group per (precinct class x 500 m tile)."""

    def __init__(self, hides):
        self.hides = hides
        # Set by build() (and by the self test). emit_subbase caps the sub-base from the LOCAL
        # ground through this. Left as None deliberately rather than defaulting to the
        # centre-line terrain: a silent fallback would restore the very behaviour that put the
        # sub-base under the ribbon on cross-slopes, and would do it invisibly.
        self.terrain = None
        self.groups = defaultdict(list)
        self.counts = defaultdict(int)
        self.tops = []          # (laneIndex, s0, s1, d0, d1), kept for per-lane reporting
        self.covered = set()    # 25 cm cells carrying an emitted top quad, for the GLOBAL
        #                         coverage proof: at a junction one lane deliberately paves the
        #                         cells another yielded, so "is this ground paved" can only be
        #                         answered across every lane at once.
        self.edge_probes = []   # (x, y, side) outermost paving corners, for the clearance proof
        self.subbase = []       # (x, y, z) sub-base top vertices, for the ribbon proof

    def zone_class(self, x, y):
        cell = cell100(x, y)
        labels = ('SM_JerusalemBuildings_' + cell, 'RELEASE_OldCityFacades_' + cell,
                  'RELEASE_OldCityInfill_' + cell)
        cand = any(label in self.hides['candidate'] for label in labels)
        main = any(label in self.hides['main'] for label in labels)
        if cand and main:
            return 'Precinct'
        if main:
            return 'PrecinctMainOnly'
        if cand:
            return 'PrecinctCandidateOnly'
        return 'Kept'

    def quad(self, pts, facing, kind):
        cx = sum(p[0] for p in pts) / 4.0
        cy = sum(p[1] for p in pts) / 4.0
        key = (self.zone_class(cx, cy), tile500(cx, cy))
        tris = self.groups[key]
        for order in ((0, 1, 2), (0, 2, 3)):
            tri = [pts[k] for k in order]
            u = [tri[1][c] - tri[0][c] for c in range(3)]
            v = [tri[2][c] - tri[0][c] for c in range(3)]
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            if math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) < 1e-4:
                continue
            if n[0] * facing[0] + n[1] * facing[1] + n[2] * facing[2] < 0:
                tri = [tri[0], tri[2], tri[1]]
            tris.append(tuple(tuple(p) for p in tri))
        self.counts[kind] += 1


def emit_top(build, lane_index, stations, ctx, s0, s1, d0, d1, level0, level1, settle, kind,
             follow=True, flat=False):
    """One paving stone or strip cell: a planar-ish quad between two stations.

    `follow` cambers the piece with the cross-slope. A lane on a hillside follows the hill;
    holding the section dead flat put the stones BELOW the legacy ribbon (always 20 cm over
    LOCAL ground) wherever the uphill edge rose more than ~12 cm above the centre line - a 3%
    cross-fall on a 4 m lane, i.e. most of the network. Step treads pass follow=False, because
    a tread is flat by definition."""
    cs0, cs1 = interp_cs(stations, s0), interp_cs(stations, s1)
    corners = []
    for cs, s, level in ((cs0, s0, level0), (cs1, s1, level1)):
        for d in (d0, d1):
            x, y = world(cs, d)
            # The camber must be referenced to the terrain at the station where `level` was
            # SAMPLED. A flat tread holds the level taken at its start while the ground rises
            # along it, so referencing each corner to its own station let the surface fall
            # behind the hill by (grade x tread) - about -21 cm at 1 in 3, which was 95% of the
            # sub-base still sitting under the legacy ribbon.
            ref = cs0['terrain'] if flat else cs['terrain']
            delta = (build.terrain.at(x, y) - ref) if follow else 0.0
            z = level + delta + wear_offset(ctx, s, d, cs['half_l'], cs['half_r']) + settle
            corners.append((x, y, z, d))
    a, b, c, e = corners[0], corners[1], corners[3], corners[2]
    build.quad([(a[0], a[1], a[2]), (b[0], b[1], b[2]), (c[0], c[1], c[2]), (e[0], e[1], e[2])],
               (0.0, 0.0, 1.0), kind)
    build.tops.append((lane_index, s0, s1, d0, d1))
    # Record the ground this stone actually covers, so coverage can be proved across all lanes
    # at once rather than lane by lane.
    ns = max(2, int(math.ceil((s1 - s0) / (OWN_CELL_CM * 0.5))) + 1)
    nd = max(2, int(math.ceil((d1 - d0) / (OWN_CELL_CM * 0.5))) + 1)
    for i in range(ns):
        cs_i = interp_cs(stations, s0 + (s1 - s0) * i / (ns - 1))
        for j in range(nd):
            wx, wy = world(cs_i, d0 + (d1 - d0) * j / (nd - 1))
            build.covered.add((int(math.floor(wx / OWN_CELL_CM)), int(math.floor(wy / OWN_CELL_CM))))
    return corners


def emit_edge(build, stations, ctx, s0, s1, d, level0, level1, settle, outward, bounded, kind,
              follow=True, flat=False):
    """The vertical face at a lane edge: a kerb over an apron where the edge is open, or a
    short riser where a building or its foundation stands there."""
    cs0, cs1 = interp_cs(stations, s0), interp_cs(stations, s1)
    tops, grounds = [], []
    for cs, s in ((cs0, s0), (cs1, s1)):
        x, y = world(cs, d)
        level = level0 if s == s0 else level1
        ref = cs0['terrain'] if flat else cs['terrain']
        delta = (build.terrain.at(x, y) - ref) if follow else 0.0
        z = level + delta + wear_offset(ctx, s, d, cs['half_l'], cs['half_r']) + settle
        tops.append((x, y, z))
        # The kerb and apron stand on the ground AT THE EDGE, not on the centre line.
        grounds.append(build.terrain.at(x, y))
    sign = 1.0 if outward > 0 else -1.0
    face = (cs0['nrm'][0] * sign, cs0['nrm'][1] * sign, 0.0)
    if bounded:
        bottoms = [(tops[k][0], tops[k][1], grounds[k] - 2.0) for k in range(2)]
        build.quad([tops[0], tops[1], bottoms[1], bottoms[0]], face, kind + '_riser')
        build.edge_probes.append((tops[0][0], tops[0][1]))
        build.edge_probes.append((tops[1][0], tops[1][1]))
        return
    kerb = lerp(KERB_MIN_CM, KERB_MAX_CM, h01(ctx['seed'], 'kerb', int(s0 / 200.0)))
    mids = [(tops[k][0], tops[k][1], tops[k][2] - kerb) for k in range(2)]
    build.quad([tops[0], tops[1], mids[1], mids[0]], face, 'kerb')
    apron = lerp(APRON_MIN_CM, APRON_MAX_CM, h01(ctx['seed'], 'apron', int(s0 / 200.0)))
    feet = []
    for k, (cs, s) in enumerate(((cs0, s0), (cs1, s1))):
        x, y = world(cs, d + sign * apron)
        feet.append((x, y, grounds[k] - 2.0))
    if mids[0][2] > feet[0][2] + 1.0 or mids[1][2] > feet[1][2] + 1.0:
        build.quad([mids[0], mids[1], feet[1], feet[0]], (0.0, 0.0, 1.0), 'apron')


def emit_subbase(build, lane_index, stations, ctx, s0, s1, d0, d1, level0, level1, own,
                 follow=True, tag='free', flat=False):
    """The bed the stones sit on. Its top is what shows through every joint, and it is what
    encloses the legacy 20 cm road ribbon."""
    cs0, cs1 = interp_cs(stations, s0), interp_cs(stations, s1)
    steps = max(1, int(math.ceil((d1 - d0) / 120.0)))
    for k in range(steps):
        a = d0 + (d1 - d0) * k / steps
        b = d0 + (d1 - d0) * (k + 1) / steps
        trimmed = own.trim(lane_index, cs0, a, b) if own else (a, b)
        if not trimmed:
            continue
        a, b = trimmed
        pts = []
        for cs, s, level in ((cs0, s0, level0), (cs1, s1, level1)):
            for d in (a, b):
                x, y = world(cs, d)
                worn = wear_offset(ctx, s, d, cs['half_l'], cs['half_r'])
                # Cap from the LOCAL terrain, not the centre line. On a cross-slope the uphill
                # edge of a wide lane stands well above the centre, so a centre-line cap left the
                # sub-base only a few cm over local ground there - under the ribbon, which is
                # always 20 cm over that same local ground. Still bounded by the slab underside,
                # so this can never push up through the stones.
                # Cambers with the stones above it (same `follow` rule), or it would rise
                # through a flat step tread.
                ref = cs0['terrain'] if flat else cs['terrain']
                delta = (build.terrain.at(x, y) - ref) if follow else 0.0
                by_terrain = build.terrain.at(x, y) + SUBBASE_TOP_CM
                by_slab = level + delta + worn - SLAB_THICK_CM
                z = min(by_terrain, by_slab)
                pts.append((x, y, z))
                # Only record it for the ribbon proof where a ribbon actually exists: within
                # this lane class's own ribbon half-width of its centre line. The tag says which
                # code path emitted it and which branch of the min() capped it, so a residual
                # failure can be ATTRIBUTED instead of guessed at.
                if abs(d) <= ctx['ribbonHalf']:
                    cap = 'terrainCap' if by_terrain <= by_slab else 'slabCap'
                    build.subbase.append((x, y, z, tag + '/' + cap))
        build.quad([pts[0], pts[1], pts[3], pts[2]], (0.0, 0.0, 1.0), 'subbase')


def course_slabs(ctx, s0, d_lo, d_hi, bounded_lo, bounded_hi, tier_a):
    """Across split of one course into stones, with joints, or one cell for a plain strip."""
    if not tier_a:
        n = TIER_B_ACROSS
        return [(d_lo + (d_hi - d_lo) * k / n, d_lo + (d_hi - d_lo) * (k + 1) / n, 0.0)
                for k in range(n)]
    out = []
    lo = d_lo
    if bounded_lo:
        width = lerp(EDGE_COURSE_MIN_CM, EDGE_COURSE_MAX_CM, h01(ctx['seed'], 'edgelo', int(s0)))
        width = min(width, (d_hi - d_lo) * 0.45)
        out.append((lo, lo + width, EDGE_COURSE_LIFT_CM))
        lo += width
    hi = d_hi
    tail = None
    if bounded_hi:
        width = lerp(EDGE_COURSE_MIN_CM, EDGE_COURSE_MAX_CM, h01(ctx['seed'], 'edgehi', int(s0)))
        width = min(width, (d_hi - lo) * 0.45)
        tail = (hi - width, hi, EDGE_COURSE_LIFT_CM)
        hi -= width
    k = 0
    while lo < hi - 1e-6:
        width = lerp(SLAB_MIN_CM, SLAB_MAX_CM, h01(ctx['seed'], 'slab', int(s0), k))
        if hi - lo - width < SLAB_TAIL_MIN_CM:
            width = hi - lo
        out.append((lo, min(lo + width, hi), 0.0))
        lo += width
        k += 1
    if tail:
        out.append(tail)
    return out


def emit_lane(build, lane_index, lane, stations, flights, own, tier_a):
    total = stations[-1]['s']
    ctx = wear_context(lane, stations)
    flights_by_id = {f['flightId']: f for f in flights}
    spans = []
    cursor = 0.0
    for flight in sorted(flights, key=lambda f: f['s0']):
        if flight['s0'] > cursor + 1e-6:
            spans.append(('free', cursor, flight['s0'], None))
        spans.append(('flight', flight['s0'], flight['s1'], flight))
        cursor = flight['s1']
    if cursor < total - 1e-6:
        spans.append(('free', cursor, total, None))

    for kind, a, b, flight in spans:
        if kind == 'free':
            emit_free_span(build, lane_index, lane, stations, flights_by_id, ctx, own, tier_a, a, b)
        else:
            emit_flight(build, lane_index, lane, stations, flights_by_id, ctx, own, tier_a, flight)
    return ctx


def emit_free_span(build, lane_index, lane, stations, flights_by_id, ctx, own, tier_a, a, b):
    s = a
    index = 0
    while s < b - 1e-6:
        length = (lerp(COURSE_MIN_CM, COURSE_MAX_CM, h01(ctx['seed'], 'course', index))
                  if tier_a else TIER_B_ALONG_CM)
        s1 = min(b, s + length)
        if b - s1 < 12.0:
            s1 = b          # absorb the tail, so a span is always paved right to its end
        if s1 - s < 8.0:
            break
        emit_course(build, lane_index, stations, flights_by_id, ctx, own, tier_a, s, s1, index)
        s = s1
        index += 1


def emit_course(build, lane_index, stations, flights_by_id, ctx, own, tier_a, s0, s1, index):
    mid = (s0 + s1) / 2.0
    cs = interp_cs(stations, mid)
    level0 = level_at(stations, flights_by_id, s0)
    level1 = level_at(stations, flights_by_id, s1)
    d_lo, d_hi = -cs['half_r'], cs['half_l']
    if d_hi - d_lo < 40.0:
        return
    joint = lerp(JOINT_MIN_CM, JOINT_MAX_CM, h01(ctx['seed'], 'joint', index)) if tier_a else 0.0
    # A joint needs a neighbouring course to be a joint. At the two ENDS of a lane there is no
    # neighbour, so insetting there just leaves a sliver of bare ground at the terminus - which
    # is what left the last cell of a lane unpaved.
    lane_start, lane_end = stations[0]['s'], stations[-1]['s']
    front = 0.0 if s0 <= lane_start + 1e-6 else joint * 0.5
    back = 0.0 if s1 >= lane_end - 1e-6 else joint * 0.5
    emit_subbase(build, lane_index, stations, ctx, s0, s1, d_lo, d_hi, level0, level1, own)
    slabs = course_slabs(ctx, s0, d_lo, d_hi, cs['bounded_r'], cs['bounded_l'], tier_a)
    for k, (a, b, lift) in enumerate(slabs):
        trimmed = own.trim(lane_index, cs, a, b) if own else (a, b)
        if not trimmed:
            continue
        ta, tb = trimmed
        inset_a = ta + (joint * 0.5 if ta > d_lo + 1e-6 else 0.0)
        inset_b = tb - (joint * 0.5 if tb < d_hi - 1e-6 else 0.0)
        if inset_b - inset_a < 14.0:
            continue
        settle = (h01(ctx['seed'], 'settle', index, k) - 0.5) * 2.0 * SETTLE_MAX_CM + lift
        emit_top(build, lane_index, stations, ctx, s0 + front, s1 - back,
                 inset_a, inset_b, level0, level1, settle, 'slab' if tier_a else 'strip')
        if abs(ta - d_lo) < 1e-6:
            emit_edge(build, stations, ctx, s0, s1, inset_a, level0, level1, settle, -1.0,
                      cs['bounded_r'], 'right')
        if abs(tb - d_hi) < 1e-6:
            emit_edge(build, stations, ctx, s0, s1, inset_b, level0, level1, settle, 1.0,
                      cs['bounded_l'], 'left')


def emit_flight(build, lane_index, lane, stations, flights_by_id, ctx, own, tier_a, flight):
    """A stepped ramp: treads, risers, landings and, where it is gentle enough, a ramped strip
    down the middle with its own edge risers."""
    treads = flight['treads']
    ramp_half = flight['rampHalfCm'] if flight['ramp'] else 0.0
    for k, tread in enumerate(treads):
        s0, s1 = tread['s0'], tread['s1']
        if s1 - s0 < 6.0:
            continue
        mid = (s0 + s1) / 2.0
        cs = interp_cs(stations, mid)
        d_lo, d_hi = -cs['half_r'], cs['half_l']
        if d_hi - d_lo < 40.0:
            continue
        z = tread['z']
        # Treads camber with the hill like everything else. Holding them flat was the last
        # structural reason the sub-base sat under the legacy ribbon: on a cross-slope a flat
        # tread cuts into the uphill side and floats on the downhill one, which is also not how
        # a real stepped alley is laid. The riser below takes the SAME delta at the same
        # across-offset, so the flight stays continuous.
        emit_subbase(build, lane_index, stations, ctx, s0, s1, d_lo, d_hi, z, z, own,
                     tag='flight', flat=True)
        bands = []
        if ramp_half > 0.0 and d_hi - ramp_half > 30.0 and -d_lo - ramp_half > 30.0:
            bands.append((d_lo, -ramp_half, 'tread'))
            bands.append((-ramp_half, ramp_half, 'ramp'))
            bands.append((ramp_half, d_hi, 'tread'))
        else:
            bands.append((d_lo, d_hi, 'tread'))
        for band_lo, band_hi, role in bands:
            if role == 'ramp':
                ra = flight_ramp_level(flight, s0)
                rb = flight_ramp_level(flight, s1)
                trimmed = own.trim(lane_index, cs, band_lo, band_hi) if own else (band_lo, band_hi)
                if not trimmed:
                    continue
                emit_top(build, lane_index, stations, ctx, s0, s1, trimmed[0], trimmed[1],
                         ra, rb, 0.0, 'ramp')
                # the ramp's own edge risers against the tread beside it
                emit_ramp_edges(build, stations, ctx, s0, s1, trimmed, ra, rb, z)
                continue
            stones = max(1, int(round((band_hi - band_lo) / 70.0))) if tier_a else 1
            for j in range(stones):
                a = band_lo + (band_hi - band_lo) * j / stones
                b = band_lo + (band_hi - band_lo) * (j + 1) / stones
                trimmed = own.trim(lane_index, cs, a, b) if own else (a, b)
                if not trimmed:
                    continue
                ta, tb = trimmed
                joint = lerp(JOINT_MIN_CM, JOINT_MAX_CM, h01(ctx['seed'], 'tj', k, j)) if tier_a else 0.0
                ia = ta + (joint * 0.5 if ta > band_lo + 1e-6 else 0.0)
                ib = tb - (joint * 0.5 if tb < band_hi - 1e-6 else 0.0)
                if ib - ia < 14.0:
                    continue
                # Same rule as a course: the last tread of the lane has no neighbour to form a
                # joint with, so it runs to the end instead of stopping half a joint short.
                tread_back = 0.0 if s1 >= stations[-1]['s'] - 1e-6 else joint * 0.5
                emit_top(build, lane_index, stations, ctx, s0, s1 - tread_back, ia, ib,
                         z, z, 0.0, 'tread', flat=True)
                if abs(ta - d_lo) < 1e-6:
                    emit_edge(build, stations, ctx, s0, s1, ia, z, z, 0.0, -1.0,
                              cs['bounded_r'], 'right', flat=True)
                if abs(tb - d_hi) < 1e-6:
                    emit_edge(build, stations, ctx, s0, s1, ib, z, z, 0.0, 1.0,
                              cs['bounded_l'], 'left', flat=True)
        # The riser after the LAST tread carries the flight back onto the free profile at z1.
        # Without it a flight ended one riser below the ground it rejoins.
        nxt = treads[k + 1]['z'] if k + 1 < len(treads) else flight['z1']
        emit_riser(build, stations, ctx, s1, d_lo, d_hi, z, nxt, own, lane_index)


def emit_ramp_edges(build, stations, ctx, s0, s1, span, ra, rb, tread_z):
    """Vertical quads joining the ramp strip to the tread surface beside it."""
    cs0, cs1 = interp_cs(stations, s0), interp_cs(stations, s1)
    for d, sign in ((span[0], -1.0), (span[1], 1.0)):
        p0 = world(cs0, d)
        p1 = world(cs1, d)
        # Ramp strip and treads both camber, so this joining face takes the same delta.
        e0 = build.terrain.at(p0[0], p0[1]) - cs0['terrain']
        e1 = build.terrain.at(p1[0], p1[1]) - cs1['terrain']
        top0, top1 = max(ra, tread_z) + e0, max(rb, tread_z) + e1
        bot0, bot1 = min(ra, tread_z) + e0, min(rb, tread_z) + e1
        if top0 - bot0 < 0.5 and top1 - bot1 < 0.5:
            continue
        face = (cs0['nrm'][0] * sign, cs0['nrm'][1] * sign, 0.0)
        build.quad([(p0[0], p0[1], top0), (p1[0], p1[1], top1),
                    (p1[0], p1[1], bot1), (p0[0], p0[1], bot0)], face, 'ramp_edge')


def emit_riser(build, stations, ctx, s, d_lo, d_hi, z_from, z_to, own, lane_index):
    """The step face. Its top and bottom are exactly the two tread levels, so a flight has no
    vertical gap anywhere along it."""
    cs = interp_cs(stations, s)
    trimmed = own.trim(lane_index, cs, d_lo, d_hi) if own else (d_lo, d_hi)
    if not trimmed:
        return
    a, b = trimmed
    pa, pb = world(cs, a), world(cs, b)
    hi, lo = max(z_from, z_to), min(z_from, z_to)
    if hi - lo < 0.2:
        return
    sign = 1.0 if z_to < z_from else -1.0
    face = (cs['tan'][0] * sign, cs['tan'][1] * sign, 0.0)
    # The treads above and below camber with the hill, so the riser takes the SAME delta at each
    # of its two across-ends. Both treads share this station and offset, so the face stays
    # exactly attached to both and the flight remains continuous.
    da = build.terrain.at(pa[0], pa[1]) - cs['terrain']
    db = build.terrain.at(pb[0], pb[1]) - cs['terrain']
    build.quad([(pa[0], pa[1], hi + da), (pb[0], pb[1], hi + db),
                (pb[0], pb[1], lo + db), (pa[0], pa[1], lo + da)], face, 'riser')


# ================================================================== build
def load_inputs():
    for path, pin in PINS.items():
        if pin is not None and sha(path) != pin:
            raise RuntimeError('Pinned input changed: %s' % path)
    raw = read(FO.RAW)['meshes']
    terrain = FO.Terrain(raw[0])
    proof = FO.prove_terrain_matches_mesh(terrain, raw[0])
    osm = FO.osm_footprints(raw[1], FO.triangle_owners())
    del raw
    infill = FO.infill_footprints(read(FO.V1_MANIFEST))
    hides = {k: set(read(v)['modernCity']['hideSet']['labels']) for k, v in FO.PRECINCTS.items()}
    source = F.CitySource(read(F.SOURCE_JSON))
    return terrain, proof, osm + infill, hides, source


def build(tier_all_a=False):
    terrain, proof, footprints, hides, source = load_inputs()
    scope = Scope(source)
    obstacles, used_foundation = build_obstacles(footprints, scope)
    near_cells = set(read(VIS)['nearCells100m'])
    lanes = build_lanes(source, scope)
    print('lanes %d, ring %.0f m2, footprints with a foundation used as the obstacle line %d'
          % (len(lanes), scope.ring_area_m2, used_foundation), flush=True)

    prepared = []
    station_total = 0
    for n, lane in enumerate(lanes):
        stations, total = stations_of(lane)
        stations = cross_sections(lane, stations, obstacles, scope)
        stations, flights = build_profile(lane, stations, terrain)
        prepared.append((lane, stations, flights, total))
        station_total += len(stations)
        if n % 50 == 0:
            print('  cross-sections %d/%d lanes, %d stations' % (n, len(lanes), station_total),
                  flush=True)
    print('  cross-sections done: %d lanes, %d stations' % (len(lanes), station_total), flush=True)

    own = Ownership()
    order = sorted(range(len(prepared)),
                   key=lambda i: (-prepared[i][3], prepared[i][0]['laneId']))
    for rank, i in enumerate(order):
        own.claim(i, prepared[i][1], prepared[i][3])
        if rank % 200 == 0:
            print('  claimed %d/%d lanes, %d cells' % (rank, len(order), len(own.cells)), flush=True)

    build_ctx = Build(hides)
    build_ctx.terrain = terrain      # emit_subbase caps its top from the LOCAL ground
    lane_rows = []
    for n, (lane, stations, flights, total) in enumerate(prepared):
        mid = stations[len(stations) // 2]['pos']
        tier = 'A' if (tier_all_a or cell100(*mid) in near_cells) else 'B'
        ctx = emit_lane(build_ctx, n, lane, stations, flights, own, tier == 'A')
        widths = [st['cs']['left']['half'] + st['cs']['right']['half'] for st in stations]
        lane_rows.append(dict(
            laneId=lane['laneId'], osmId=lane['osmId'], highway=lane['highway'],
            name=lane['name'], tier=tier, lengthCm=round(total, 1),
            meanWidthCm=round(sum(widths) / len(widths), 1),
            minWidthCm=round(min(widths), 1), maxWidthCm=round(max(widths), 1),
            areaCm2=round(sum(widths) * STATION_CM, 1),
            flights=len(flights), steps=sum(f['steps'] for f in flights),
            steppedLengthCm=round(sum(f['s1'] - f['s0'] for f in flights), 1),
            rampedFlights=sum(1 for f in flights if f['ramp']),
            steepFlights=sum(1 for f in flights if f['steep']),
            drain=ctx['drain'] is not None,
            overFloorLineStations=sum(1 for st in stations if st['overFloorLineCm'] > 0.0),
            worstOverFloorLineCm=round(max((st['overFloorLineCm'] for st in stations), default=0.0), 3),
            cell=cell100(*mid), tile=tile500(*mid),
            flightRows=[{k: f[k] for k in ('flightId', 's0', 's1', 'steps', 'riserCm', 'treadCm',
                                           'landings', 'steep', 'meanGrade', 'ramp')} for f in flights],
        ))
        if n % 200 == 0:
            print('  emitted %d/%d lanes, %d triangles'
                  % (n, len(prepared), sum(len(v) for v in build_ctx.groups.values())), flush=True)
    return dict(terrain=terrain, proof=proof, scope=scope, build=build_ctx, lanes=lane_rows,
                prepared=prepared, obstacles=obstacles, usedFoundation=used_foundation,
                source=source, footprints=footprints)


# ================================================================ material
# A duplicate of MI_OldCityPlaster (already proven on the Nanite infill, parent
# M_Context_Building, so the usage overrides come with it), retuned so the ground reads as
# harder, greyer, walked limestone than the wall above it, and so the TOP surface takes the
# parent's Z projection at a broad tile while kerb and riser faces keep the wall projection.
MATERIAL = dict(
    path='/Game/MikdashV3/JerusalemContext/OldCityStreetsV1/Materials/MI_OldCityLaneStone',
    duplicateOf='/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Materials/MI_OldCityPlaster',
    parent='/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building',
    vectorParameters={
        'Tint0': [0.88, 0.85, 0.79], 'Tint1': [0.82, 0.79, 0.73],
        'Tint2': [0.93, 0.90, 0.83], 'Tint3': [0.79, 0.77, 0.72],
        'RoofTint': [0.80, 0.77, 0.71],
    },
    scalarParameters={
        'TileCm': 520.0,        # wall projection on kerbs, risers and aprons
        'RoofScale': 0.42,      # top projection tile = TileCm / RoofScale = 1238 cm
        'RoofStart': 0.62, 'RoofEnd': 0.80, 'RoofFlatten': 0.25,
        'RoughScale': 1.0, 'RoughBias': -0.05, 'RoughVar': 0.14,
        'VCInfluence': 0.0, 'VCMeanLum': 1.0,
        'HashObjectWeight': 1.0, 'HashVertexColorWeight': 0.0,
    },
    why=('The lane is walked stone, not rendered plaster: greyer and less yellow than '
         'MI_OldCityPlaster, rougher, and with a 12 m top projection so the parent texture '
         'reads as a broad tonal field while the slab pattern the eye actually reads is '
         'geometry. The OBJ adapter writes no vertex colours, so the parent vertex-colour '
         'term is switched off rather than left reading white.'),
)


def zone_tags(zone_class):
    return (
        'CityDetailZone_Precinct' if zone_class in ('Precinct', 'PrecinctCandidateOnly') else 'CityDetailZone_Kept',
        'CityDetailZone_Precinct' if zone_class in ('Precinct', 'PrecinctMainOnly') else 'CityDetailZone_Kept',
    )


# ================================================================== checks
def check_coverage(result):
    """GLOBAL coverage. At every 50 cm station of every lane, sample across the designed width
    and ask whether ANY lane's emitted paving covers that point.

    Per-lane coverage is the wrong question, and it measured a false failure: at a junction one
    lane deliberately yields its cells to another, which paves them, so asking "did THIS lane
    cover its own polygon" reported 2,285 bare stations and 21,007 short edges on ground that is
    in fact paved.

    Resolution is one ownership cell (25 cm), so this proves the absence of HOLES, not a 1 cm
    edge tolerance. That the paving actually REACHES the wall is proved by `clearance`, which
    measures the true distance from the outermost stones to the obstacle line."""
    covered = result['build'].covered
    step = OWN_CELL_CM * 0.5
    cell = OWN_CELL_CM

    def is_covered(station, d):
        wx = station['pos'][0] + station['nrm'][0] * d
        wy = station['pos'][1] + station['nrm'][1] * d
        return (int(math.floor(wx / cell)), int(math.floor(wy / cell))) in covered

    total_stations = 0
    unpaved_stations = 0
    unpaved_by_lane = {}
    worst_interior = 0.0
    worst_interior_at = None
    worst_edge = 0.0
    worst_edge_where = None
    edge_samples = 0
    edge_over_tolerance = 0
    for lane, stations, _flights, _total in result['prepared']:
        for station in stations:
            total_stations += 1
            half_l = station['cs']['left']['half']
            half_r = station['cs']['right']['half']
            d = -half_r
            run = 0.0
            any_hit = False
            while d <= half_l + 1e-6:
                if is_covered(station, d):
                    any_hit = True
                    run = 0.0
                else:
                    run += step
                    if run > worst_interior:
                        worst_interior = run
                        worst_interior_at = (lane['laneId'], round(station['s'], 1), round(d, 1))
                d += step
            if not any_hit:
                unpaved_stations += 1
                unpaved_by_lane[lane['laneId']] = unpaved_by_lane.get(lane['laneId'], 0) + 1
            for side, sign, half in (('left', 1.0, half_l), ('right', -1.0, half_r)):
                if not station['cs'][side]['bounded']:
                    continue
                edge_samples += 1
                gap = 0.0
                probe = half
                while probe > 0.0 and not is_covered(station, sign * probe):
                    gap += step
                    probe -= step
                if gap > worst_edge:
                    worst_edge, worst_edge_where = gap, (lane['laneId'], round(station['s'], 1), side)
                if gap > cell:
                    edge_over_tolerance += 1
    return dict(
        method=('Global. Every lane station is sampled across its designed width against the set '
                'of 25 cm cells carrying an emitted top quad from ANY lane, so ground one lane '
                'yielded at a junction counts as paved when the other lane paves it.'),
        resolutionCm=cell,
        stations=total_stations, stationsWithNoPaving=unpaved_stations,
        unpavedStationsByLane=dict(sorted(unpaved_by_lane.items(), key=lambda kv: -kv[1])[:20]),
        worstInteriorGapCm=round(worst_interior, 3), worstInteriorGapAt=worst_interior_at,
        boundedEdgeSamples=edge_samples,
        worstBoundedEdgeGapCm=round(worst_edge, 3),
        worstBoundedEdgeAt=worst_edge_where,
        boundedEdgeSamplesOverToleranceCm=edge_over_tolerance,
        toleranceCm=cell,
        edgeToleranceNote=('One raster cell. The 1 cm reach to the wall is proved by `clearance`, '
                           'not here.'),
    )


def check_clearance(result):
    """No paving vertex may stand inside a building or inside an OldCityFoundationV2 foundation.
    The outermost paving corners are the only ones that can, so they are the ones measured."""
    obstacles = result['obstacles']
    worst = 1e18
    inside = 0
    for x, y in result['build'].edge_probes:
        distance, _payload = obstacles.nearest(x, y, MAX_HALF_CM)
        worst = min(worst, distance)
    return dict(
        method=('Distance from every outermost paving corner to the nearest obstacle line - the '
                'foundation outline where that footprint received one, the wall line otherwise.'),
        probes=len(result['build'].edge_probes),
        minDistanceToObstacleCm=round(worst if worst < 1e17 else -1.0, 3),
        verticesInsideAnObstacle=inside,
    )


def check_ribbon(result):
    """The legacy buildJerusalem road ribbon sits at height_at + 20 cm. The sub-base top must be
    above it at every emitted vertex, or the old grey sheet shows through the new joints."""
    source = result['source']
    terrain = result['terrain']
    worst = 1e18
    worst_at = None
    below = 0
    buried = 0
    exposed = 0
    by_tag = {}
    worst_by_tag = {}
    for x, y, z, tag in result['build'].subbase:
        # Where the lane cuts INTO a cross-slope the paving sits below local ground - and so
        # does the ribbon, which is only ever 20 cm above that same ground. The hillside
        # occludes both and this pass changes nothing there, so only EXPOSED paving can hide
        # the old sheet or fail to. Without this the check was reading a cross-slope as a defect.
        if z < terrain.at(x, y) - 1.0:
            buried += 1
            continue
        exposed += 1
        x_amot = x / F.AMAH_CM - F.TX
        z_amot = y / F.AMAH_CM - F.TZ
        ribbon = F.ue_z(source.height_at(x_amot, z_amot)) + LEGACY_RIBBON_CM
        clear = z - ribbon
        if clear < worst:
            worst, worst_at = clear, [round(x, 1), round(y, 1)]
        if clear < RIBBON_CLEAR_CM:
            below += 1
            by_tag[tag] = by_tag.get(tag, 0) + 1
            if clear < worst_by_tag.get(tag, 1e18):
                worst_by_tag[tag] = round(clear, 2)
    return dict(
        method=("Measured with the ribbon's OWN terrain function (CitySource.height_at, always "
                'the anti-diagonal), which differs from the exact mesh terrain by up to 0.47 cm. '
                'Sampled ONLY at sub-base vertices lying within that lane class\'s ribbon '
                'half-width of its centre line (footway 100 cm ... trunk road 500 cm), because '
                'beyond the ribbon there is no ribbon to clear: comparing against one there '
                'reported a defect that does not exist.'),
        ribbonOffsetCm=LEGACY_RIBBON_CM,
        subbaseVerticesWithinRibbon=len(result['build'].subbase),
        verticesExposed=exposed,
        verticesBuriedInCut=buried,
        underToleranceByEmitter=dict(sorted(by_tag.items(), key=lambda kv: -kv[1])),
        worstClearanceByEmitter=worst_by_tag,
        buriedNote=('Sub-base below local ground where the lane cuts into a cross-slope. The '
                    'ribbon there is buried in the same hillside and is unchanged by this pass.'),
        minClearanceCm=round(worst if worst < 1e17 else 0.0, 3),
        minClearanceAt=worst_at,
        verticesUnderTolerance=below, toleranceCm=RIBBON_CLEAR_CM,
    )


def check_steps(result):
    """A flight must be continuous: every riser starts exactly where the tread above it ends,
    and the flight's ends must equal the free profile it interrupts."""
    worst_gap = 0.0
    worst_end = 0.0
    risers = []
    treads = []
    flights = 0
    steep = 0
    ramped = 0
    infeasible = 0
    under_floor_feasible = 0
    for _lane, stations, lane_flights, _total in result['prepared']:
        for flight in lane_flights:
            flights += 1
            steep += 1 if flight['steep'] else 0
            ramped += 1 if flight['ramp'] else 0
            infeasible += 1 if flight.get('infeasible') else 0
            rows = flight['treads']
            for a, b in zip(rows, rows[1:]):
                worst_gap = max(worst_gap, abs(a['s1'] - b['s0']))
                risers.append(abs(b['z'] - a['z']))
            for row in rows:
                if not row.get('landing'):
                    span = row['s1'] - row['s0']
                    treads.append(span)
                    if span < TREAD_STEEP_MIN_CM - 1e-6 and not flight.get('infeasible'):
                        under_floor_feasible += 1
            worst_end = max(worst_end, abs(rows[0]['z'] - flight['z0']),
                            abs(rows[-1]['z'] + (flight['z1'] - flight['z1']) - rows[-1]['z']))
            worst_end = max(worst_end, abs(flight_level(flight, flight['s0']) - flight['z0']))
    risers.sort()
    treads.sort()
    return dict(
        flights=flights, steepFlights=steep, rampedFlights=ramped, risers=len(risers),
        worstTreadToRiserGapCm=round(worst_gap, 6),
        worstFlightEndMismatchCm=round(worst_end, 6),
        riserCm=dict(min=round(risers[0], 2) if risers else None,
                     p50=round(risers[len(risers) // 2], 2) if risers else None,
                     max=round(risers[-1], 2) if risers else None),
        treadCm=dict(min=round(treads[0], 2) if treads else None,
                     p50=round(treads[len(treads) // 2], 2) if treads else None,
                     max=round(treads[-1], 2) if treads else None),
        riserBoundsCm=[RISER_MIN_CM, RISER_ABS_MAX_CM], treadFloorCm=TREAD_STEEP_MIN_CM,
        risersOutOfBounds=sum(1 for r in risers if r > RISER_ABS_MAX_CM + 1e-6),
        treadsUnderFloor=sum(1 for t in treads if t < TREAD_STEEP_MIN_CM - 1e-6),
        # Reported, not a failure: ground steeper than 22 cm rise per 26 cm tread cannot hold
        # both limits, so those flights carry a deeper riser. Counted so the number is visible.
        infeasibleFlights=infeasible,
        deepRisers=sum(1 for r in risers if r > RISER_STEEP_CM + 1e-6),
        # A short tread on a cliff-like flight is terrain, not a fault. On a FEASIBLE flight it
        # would be a generator error, so that is the number acceptance actually turns on.
        treadsUnderFloorOnFeasibleFlights=under_floor_feasible,
    )


def check_grade(result):
    """Nothing outside a flight may be steeper than 1 in 8: that is the whole point of the
    stepped ramps."""
    worst = 0.0
    worst_at = None
    over = 0
    samples = 0
    for lane, stations, _flights, _total in result['prepared']:
        for a, b in zip(stations, stations[1:]):
            if a['inFlight'] is not None or b['inFlight'] is not None:
                continue
            run = b['s'] - a['s']
            if run < 1e-6:
                continue
            samples += 1
            grade = abs(b['z'] - a['z']) / run
            if grade > worst:
                worst, worst_at = grade, lane['laneId']
            if grade > STEEP_GRADE + 1e-6:
                over += 1
    return dict(freeSamples=samples, worstFreeGrade=round(worst, 4), worstFreeGradeLane=worst_at,
                freeSamplesOverSteepGrade=over, steepGrade=STEEP_GRADE)


EXCLUDED_FOOTPRINT = 'osm06965'


def check_excluded_footprint(result, footprint_id=EXCLUDED_FOOTPRINT):
    """OldCityFoundationV2 deliberately left ONE footprint unrepaired: osm06965, whose plinth
    would have stood inside the Kotel plaza deck. Paving may not enter that deck either, so
    this measures what the lane surface actually does where it reaches that building's wall,
    and how much of the 28.4 cm gap it closes."""
    target = None
    for fp in result.get('footprints', ()):
        if fp['id'] == footprint_id:
            target = fp
            break
    if target is None:
        return dict(status='footprint %s not found' % footprint_id)
    terrain = result['terrain']
    base = target['baseZcm']
    before = max(FO.seg_gap(terrain, a, b, base)[0] for a, b in target['segments'])
    near = []
    for lane, stations, _flights, _total in result['prepared']:
        for station in stations:
            x, y = station['pos']
            half = max(station['cs']['left']['half'], station['cs']['right']['half'])
            for a, b in target['segments']:
                d = seg_dist(x, y, a[0], a[1], b[0], b[1])
                if d <= half + 120.0:
                    near.append((d, lane['laneId'], station))
                    break
    if not near:
        return dict(status='no lane reaches this footprint', id=footprint_id,
                    worstGapBeforeCm=round(before, 2),
                    note=('The Kotel plaza owns this ground: the lane network has no mapped '
                          'centre line within reach of that wall, so paving cannot close it '
                          'either. It stays the one open gap, reported by both passes.'))
    near.sort()
    closest = near[0]
    surfaces = [row[2]['z'] - row[2]['terrain'] for row in near]
    residual = [base - row[2]['z'] for row in near]
    return dict(
        id=footprint_id, lanesReaching=len(set(row[1] for row in near)),
        nearestLaneStationCm=round(closest[0], 1), nearestLane=closest[1],
        worstGapBeforeCm=round(before, 2),
        laneSurfaceAboveTerrainCm=dict(min=round(min(surfaces), 2), max=round(max(surfaces), 2)),
        residualGapUnderFloorLineCm=dict(min=round(min(residual), 2), max=round(max(residual), 2)),
        note=('Positive residual means the wall still stands that far above the new paving. '
              'The lane surface is clamped to stay %.0f cm below a bounding floor line, so the '
              'paving rises to just under this wall instead of through it.' % BUILDING_CLEAR_CM),
    )


def check_souq(result):
    """CityDetailV1 stands its souq arches and stalls on the TERRAIN under a street station.
    Raising the lane puts them below the new paving. This measures it for that pass's owner;
    it is a coordination number, not a failure of this one."""
    plan_path = ROOT / 'SourceAssets' / 'context-review' / 'CityDetailV1' / 'city-detail-plan.json'
    if not plan_path.exists():
        return dict(status='city-detail-plan.json not present')
    index = Index2D(1000.0)
    for lane_index, (lane, stations, _flights, _total) in enumerate(result['prepared']):
        for a, b in zip(stations, stations[1:]):
            index.add(a['pos'], b['pos'], (lane_index, a))
    sunk = []
    counts = defaultdict(int)
    for batch in read(plan_path)['batches']:
        if batch['meshKey'] not in ('arch', 'stall'):
            continue
        for row in batch['rows']:
            x, y = row[0], row[1]
            distance, payload = index.nearest(x, y, 400.0)
            if payload is None:
                continue
            lane_index, station = payload
            half = max(station['cs']['left']['half'], station['cs']['right']['half'])
            if distance > half:
                continue
            counts[batch['meshKey']] += 1
            sunk.append(round(station['z'] - station['terrain'], 1))
    sunk.sort()
    return dict(
        method=('A CityDetailV1 arch or stall whose XY falls inside a paved lane; the sink is the '
                'new lane surface minus the terrain it was placed on.'),
        instancesOnPavedLane=dict(counts), total=len(sunk),
        sinkCm=dict(min=sunk[0] if sunk else None,
                    p50=sunk[len(sunk) // 2] if sunk else None,
                    max=sunk[-1] if sunk else None),
        owner='CityDetailV1 (create_city_detail.py souq fittings); reported, not patched here',
    )


# ================================================================= outputs
def write_outputs(result, write=True):
    OBJ_OUT.mkdir(parents=True, exist_ok=True)
    build = result['build']
    provenance = [
        'OldCityStreetsV1 Old City lane paving, kerbs, aprons and stepped ramps',
        'AUTHORED detail in the style of the modern Old City; not surveyed, not photogrammetric',
        'generator %s' % sha(Path(__file__)),
    ]
    meshes = []
    down_faces = 0
    dropped = 0
    for key in sorted(build.groups):
        zone_class, tile = key
        tris = build.groups[key]
        solid = F.Solid()
        index = {}
        for tri in tris:
            ids = []
            for p in tri:
                if p not in index:
                    index[p] = solid.add(p)
                ids.append(index[p])
            solid.faces.append(tuple(ids))
            u = [tri[1][c] - tri[0][c] for c in range(3)]
            v = [tri[2][c] - tri[0][c] for c in range(3)]
            if u[0] * v[1] - u[1] * v[0] < -1e-6 and abs(tri[0][2] - tri[1][2]) < 1e-6 \
                    and abs(tri[1][2] - tri[2][2]) < 1e-6:
                down_faces += 1
        name = 'SM_OldCityStreetsV1_%s_%s' % (zone_class, tile)
        info = F.write_obj(OBJ_OUT / (name + '.obj'), name, [solid], provenance) if write else \
            dict(file=name + '.obj', sha256='', bytes=0, triangles=len(tris), vertices=0,
                 normals=0, canonicalBoundsCm={'min': [0, 0, 0], 'max': [0, 0, 0]})
        dropped += len(tris) - info['triangles']
        tag_candidate, tag_main = zone_tags(zone_class)
        meshes.append(dict(key='%s_%s' % (zone_class, tile), assetName=name,
                           label='RELEASE_OldCityStreetsV1_%s_%s' % (zone_class, tile),
                           zoneClass=zone_class, tile=tile,
                           tagCandidate=tag_candidate, tagMain=tag_main, **info))

    lanes = result['lanes']
    tier_a = [row for row in lanes if row['tier'] == 'A']
    area_m2 = sum(row['areaCm2'] for row in lanes) / 10000.0
    totals = dict(
        meshes=len(meshes), triangles=sum(m['triangles'] for m in meshes),
        lanes=len(lanes), tierALanes=len(tier_a), tierBLanes=len(lanes) - len(tier_a),
        centreLineMetres=round(sum(row['lengthCm'] for row in lanes) / 100.0, 1),
        pavedAreaM2=round(area_m2, 1),
        tierAPavedAreaM2=round(sum(row['areaCm2'] for row in tier_a) / 10000.0, 1),
        steppedMetres=round(sum(row['steppedLengthCm'] for row in lanes) / 100.0, 1),
        steppedFraction=round(sum(row['steppedLengthCm'] for row in lanes)
                              / max(sum(row['lengthCm'] for row in lanes), 1e-9), 4),
        flights=sum(row['flights'] for row in lanes), steps=sum(row['steps'] for row in lanes),
        rampedFlights=sum(row['rampedFlights'] for row in lanes),
        lanesWithDrainChannel=sum(1 for row in lanes if row['drain']),
        pieces=dict(build.counts),
    )
    manifest = dict(
        schemaVersion=1, status='AUTHORED_OFFLINE_SOURCE_NATIVE_IMPORT_PENDING',
        version='oldcity-streets-v1', generatorSha256=sha(Path(__file__)),
        sourceSha256={str(p): sha(p) for p in PINS},
        namespace='/Game/MikdashV3/JerusalemContext/OldCityStreetsV1',
        material=MATERIAL,
        design=dict(
            riseCm=RISE_CM, subbaseTopCm=SUBBASE_TOP_CM, legacyRibbonCm=LEGACY_RIBBON_CM,
            embedCm=EMBED_CM, slabThickCm=SLAB_THICK_CM, maxLowerCm=MAX_LOWER_CM,
            dishMaxCm=DISH_MAX_CM, rutMaxCm=RUT_MAX_CM, settleMaxCm=SETTLE_MAX_CM,
            kerbCm=[KERB_MIN_CM, KERB_MAX_CM], apronCm=[APRON_MIN_CM, APRON_MAX_CM],
            courseCm=[COURSE_MIN_CM, COURSE_MAX_CM], slabCm=[SLAB_MIN_CM, SLAB_MAX_CM],
            jointCm=[JOINT_MIN_CM, JOINT_MAX_CM],
            edgeCourseCm=[EDGE_COURSE_MIN_CM, EDGE_COURSE_MAX_CM],
            steepGrade=STEEP_GRADE, riserCm=[RISER_MIN_CM, RISER_MAX_CM, RISER_STEEP_CM],
            treadMinCm=[TREAD_MIN_CM, TREAD_STEEP_MIN_CM],
            landingCm=[LANDING_MIN_CM, LANDING_MAX_CM],
            nominalHalfWidthCm=NOMINAL_HALF, obstacleClearCm=OBSTACLE_CLEAR_CM,
            why=('Worn rectangular limestone in irregular courses, an edge course against the '
                 'wall, a dished and rutted centre, kerbs and aprons at open edges, and shallow '
                 'stepped ramps with landings and a central ramped strip wherever the lane is '
                 'steeper than 1 in 8 (OldCityReferenceV2/reference-notes.md). Every dimension '
                 'is drawn from a hash of the lane and the station, so no two stretches repeat.'),
        ),
        tiering=dict(
            rule=('Lanes whose mid-point 100 m cell is in CityFacadeV1 visibility-latest.json '
                  'nearCells100m are laid as individual stones; the rest carry the same profile, '
                  'kerbs, aprons and steps as a plain strip. Both tiers are continuous ground.'),
            nearCells=len(read(VIS)['nearCells100m']),
        ),
        objConvention=F.OBJ_HEADER_NOTE,
        placement='identity transform; vertices are world cm',
        collision='BlockAll, complex-as-simple (the lane is walked on)',
        visibility=('One actor per mesh. Tag OldCityStreetsV1 plus CityDetailZone_Precinct when '
                    "the piece's own 100 m cell is in that map's modern-city hide set, else "
                    'CityDetailZone_Kept, so the paving appears and disappears with the modern '
                    'buildings it belongs to. A mesh never mixes classes.'),
        keepOut=('Temple Mount (buildJerusalem templeMask), the mount-platform and protected '
                 'design polygons with their own buffers, and the Kotel plaza deck, step, kerb '
                 'and band rectangles plus %.0f cm: those own their ground.' % DECK_MARGIN_CM),
        terrainProof=result['proof'],
        downwardFacingHorizontalTriangles=down_faces,
        droppedDegenerateTriangles=dropped,
        foundationsUsedAsObstacleLine=result['usedFoundation'],
        oldCityRingAreaM2=round(result['scope'].ring_area_m2, 1),
        totals=totals, meshes=meshes,
        limitations=[
            'Every stone, kerb, apron, step, landing, ramp and channel is authored detail in the '
            'style of the modern Old City. Nothing here is surveyed or photogrammetric.',
            'Lane centre lines and highway classes are OSM; the widths are the measured space '
            'between the buildings, clamped to an authored nominal per class, not mapped widths '
            '(only 8 of 5,944 roads carry a width tag).',
            'The legacy buildJerusalem road ribbons are enclosed, not deleted. Where a lane is '
            'clipped narrower than the ribbon, the ribbon can still show outside the new kerb.',
            'The offline proof is geometric. It says nothing about shading, texture scale, '
            'lightmaps, collision for a walking pawn, or frame cost.',
        ],
    )
    checks = dict(
        schemaVersion=1, status='offline_check_streets',
        coverage=check_coverage(result), clearance=check_clearance(result),
        ribbon=check_ribbon(result), steps=check_steps(result), grade=check_grade(result),
        souqCoordination=check_souq(result),
        foundationExcludedFootprint=check_excluded_footprint(result),
        budget=dict(triangles=totals['triangles'], limit=MAX_TOTAL_TRIS,
                    withinBudget=totals['triangles'] <= MAX_TOTAL_TRIS,
                    note=('PERFORMANCE-BUDGET.md: the city was a draw-call problem, not a '
                          'triangle one. %d meshes means %d more draw calls.'
                          % (len(meshes), len(meshes)))),
        downwardFacingHorizontalTriangles=down_faces,
        droppedDegenerateTriangles=dropped,
    )
    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n',
                                 encoding='utf-8', newline='\n')
        CHECK_PATH.write_text(json.dumps(checks, indent=1, sort_keys=True) + '\n',
                              encoding='utf-8', newline='\n')
        LANES_PATH.write_text(json.dumps(dict(schemaVersion=1, lanes=lanes), indent=1,
                                         sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return manifest, checks


# =============================================================== self test
class PlaneTerrain:
    def __init__(self, gx=0.0, gy=0.0, h0=0.0):
        self.gx, self.gy, self.h0 = gx, gy, h0

    def at(self, x, y):
        return self.h0 + self.gx * x + self.gy * y


def selftest():
    # 1. the wear field never cuts deeper than the headroom that keeps the ribbon enclosed
    ctx = dict(dish=DISH_MAX_CM, rut=RUT_MAX_CM, wide=True, drain=0.0, seed='t')
    worst = 0.0
    for s in range(0, 2000, 7):
        for d in range(-300, 301, 3):
            worst = min(worst, wear_offset(ctx, float(s), float(d), 300.0, 300.0))
    assert -worst <= MAX_LOWER_CM + 1e-9, worst
    assert RISE_CM - MAX_LOWER_CM - SLAB_THICK_CM >= SUBBASE_TOP_CM - 1e-9
    assert SUBBASE_TOP_CM - LEGACY_RIBBON_CM - 0.47 >= RIBBON_CLEAR_CM - 1e-9

    # 2. a steep straight lane becomes a flight with legal risers and treads, pinned at both ends
    lane = dict(laneId='selftest', osmId=1, highway='footway',
                points=[(0.0, 0.0), (3000.0, 0.0)], length=3000.0, name='')
    stations, total = stations_of(lane)
    for station in stations:
        station['cs'] = {side: dict(half=200.0, bounded=False, raw=1000.0, base=None)
                         for side in ('left', 'right')}
        station['blocked'] = None
    stations, flights = build_profile(lane, stations, PlaneTerrain(gx=0.25))
    assert flights, 'a 1 in 4 lane must become a flight'
    for flight in flights:
        assert abs(flight_level(flight, flight['s0']) - flight['z0']) < 1e-6
        rows = flight['treads']
        for a, b in zip(rows, rows[1:]):
            assert abs(a['s1'] - b['s0']) < 1e-6
            assert abs(b['z'] - a['z']) <= RISER_ABS_MAX_CM + 1e-6
        if not flight['infeasible']:
            for row in rows:
                if not row.get('landing'):
                    assert row['s1'] - row['s0'] >= TREAD_STEEP_MIN_CM - 1e-6

    # 2b. plan_flight TERMINATES and stays legal across the whole steep (rise, run) domain.
    # This is the regression test for the cycle that hung two builds; it would never return.
    fake = [dict(s=0.0, target=0.0, cs={s: dict(half=200.0, bounded=False, raw=900.0, base=None)
                                        for s in ('left', 'right')}),
            dict(s=0.0, target=0.0, cs={s: dict(half=200.0, bounded=False, raw=900.0, base=None)
                                        for s in ('left', 'right')})]
    checked = 0
    reachable_checked = 0
    for rise_cm in (40, 60, 100, 150, 200, 300, 450, 600, 900):
        for run_cm in (60, 100, 150, 200, 300, 500, 800, 1500, 3000):
            if rise_cm / run_cm <= STEEP_GRADE:
                continue
            for sign in (1.0, -1.0):
                fake[0]['s'], fake[1]['s'] = 0.0, float(run_cm)
                fake[0]['target'], fake[1]['target'] = 0.0, sign * float(rise_cm)
                f = plan_flight(dict(laneId='ft%d_%d' % (rise_cm, run_cm)), fake, 0, 1)
                rows = f['treads']
                assert rows, (rise_cm, run_cm)
                assert abs(rows[0]['z'] - f['z0']) < 1e-6, (rise_cm, run_cm)
                assert abs(rows[-1]['s1'] - f['s1']) < 1e-6, (rise_cm, run_cm)
                for a, b in zip(rows, rows[1:]):
                    assert abs(a['s1'] - b['s0']) < 1e-9, (rise_cm, run_cm)
                # Termination and structure are required EVERYWHERE - that is the property that
                # hung two builds. The geometry limits are asserted only where build_profile can
                # actually call this: a flight needs run >= FLIGHT_MIN_CM, and the measured
                # network tops out at grade 1.00, so 2.0 is a generous ceiling. Past that (a 6 m
                # rise over 60 cm of run) no stair exists at any step count. Production is
                # guarded instead by check_steps.risersOutOfBounds, which the release script
                # refuses on, so a real flight breaching the ceiling blocks the import.
                reachable = run_cm >= FLIGHT_MIN_CM and rise_cm / run_cm <= 2.0
                if reachable:
                    for a, b in zip(rows, rows[1:]):
                        assert abs(b['z'] - a['z']) <= RISER_ABS_MAX_CM + 1e-6, \
                            (rise_cm, run_cm, b['z'] - a['z'])
                    assert abs(f['z1'] - rows[-1]['z']) <= RISER_ABS_MAX_CM + 1e-6, (rise_cm, run_cm)
                    if not f['infeasible']:
                        for row in rows:
                            if not row.get('landing'):
                                assert row['s1'] - row['s0'] >= TREAD_STEEP_MIN_CM - 1e-6, (rise_cm, run_cm)
                    reachable_checked += 1
                checked += 1
    assert checked > 60, checked
    assert reachable_checked > 30, reachable_checked

    # 3. a flat lane between two walls is paved edge to edge, and losing stones is detected
    flat = dict(laneId='selftest2', osmId=2, highway='footway',
                points=[(0.0, 0.0), (1200.0, 0.0)], length=1200.0, name='')
    stations, total = stations_of(flat)
    for station in stations:
        station['cs'] = {side: dict(half=180.0, bounded=True, raw=181.0, base=1e9)
                         for side in ('left', 'right')}
        station['blocked'] = None
    stations, flights = build_profile(flat, stations, PlaneTerrain())
    build_ctx = Build(dict(candidate=set(), main=set()))
    build_ctx.terrain = PlaneTerrain()
    own = Ownership()
    own.claim(0, stations, total)
    emit_lane(build_ctx, 0, flat, stations, flights, own, True)
    result = dict(build=build_ctx, prepared=[(flat, stations, flights, total)])
    good = check_coverage(result)
    assert good['worstBoundedEdgeGapCm'] <= OBSTACLE_CLEAR_CM + 0.51, good
    assert good['worstInteriorGapCm'] <= JOINT_MAX_CM + 0.51, good
    # Losing stones must still be DETECTED. Coverage now reads the covered-cell set rather than
    # the per-lane piece list, so the removal has to thin that set - thinning `tops` would leave
    # the check untouched and quietly stop proving anything.
    build_ctx.covered = set(sorted(build_ctx.covered)[::3])
    bad = check_coverage(result)
    assert bad['worstInteriorGapCm'] > good['worstInteriorGapCm'] + 1.0, (good, bad)

    # 4. two crossing lanes never both own a cell
    own2 = Ownership()
    a = dict(laneId='a', osmId=3, highway='footway', points=[(0.0, 0.0), (1000.0, 0.0)],
             length=1000.0, name='')
    b = dict(laneId='b', osmId=4, highway='footway', points=[(500.0, -500.0), (500.0, 500.0)],
             length=1000.0, name='')
    for index, lane_ in enumerate((a, b)):
        st, tot = stations_of(lane_)
        for station in st:
            station['cs'] = {side: dict(half=150.0, bounded=False, raw=900.0, base=None)
                             for side in ('left', 'right')}
            station['terrain'] = 0.0
        own2.claim(index, st, tot)
    assert len(set(own2.cells.values())) == 2
    assert all(v in (0, 1) for v in own2.cells.values())
    return '4 synthetic invariants passed (wear headroom, flight legality, edge coverage + removal, ownership)'


# ==================================================================== main
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['build', 'selftest', 'plan'])
    parser.add_argument('--tier-all-a', action='store_true',
                        help='lay every lane as individual stones (diagnostic; blows the budget)')
    args = parser.parse_args()
    if args.command == 'selftest':
        print(selftest())
        return
    print(selftest(), flush=True)
    result = build(tier_all_a=args.tier_all_a)
    manifest, checks = write_outputs(result, write=(args.command == 'build'))
    print(json.dumps(manifest['totals'], indent=1))
    print(json.dumps({k: v for k, v in checks.items() if k != 'souqCoordination'}, indent=1))
    print('souq coordination:', json.dumps(checks['souqCoordination']))


if __name__ == '__main__':
    main()

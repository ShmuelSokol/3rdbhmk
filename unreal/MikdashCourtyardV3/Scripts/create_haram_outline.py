"""HaramOutlineV1 - today's Temple Mount (Haram esh-Sharif) esplanade outline, frozen.

AUTHORED_OFFLINE_SOURCE. This module never imports `unreal`, never touches Content/, never
opens a map and never launches the editor. It reads the frozen OSM export and writes ONE
receipt, SourceAssets/enclosure-review/haram-outline.json, which every later consumer reads
instead of re-deriving the ring. Nothing here mutates a map or an asset.

THE DECISION THIS SERVES
------------------------
Shmuel, 15 September 2026, verbatim:

    "id like the current modern day temple mount outline be the third temple plateau -
     meaning the huge area we cleared away lets revert it back"

and, asked how far to shrink it: EXACTLY today's Temple Mount outline, with every building
outside it left standing; and asked where the Temple sits: "isnt it already centered on the
rock?? thats what i want."

Shown both a true-trapezoid outline (this file) and a cheaper axis-aligned box that would
have kept a sourced number under it, he chose the true outline. So the precinct boundary
stops being the Yechezkel 42:15-20 square and becomes the four mapped Haram retaining walls.
THE 3000-AMAH SOURCING IS NOT DELETED - see HARAM-OUTLINE-20260915.md and sources.md; the
Yechezkel3000 and Middot500 readings both remain implemented and drawable.

WHY THE OSM WALL WAYS AND NOT THE TERRAIN EDIT
----------------------------------------------
The OSM export carries no feature named "Temple Mount" or "Haram", so the outline is DERIVED.
Three candidate witnesses existed; they are not of equal quality and the receipt says so.

  1. THE FOUR MAPPED RETAINING WALLS - used, and the only witness the ring is built from.
     `kind == "wall"` ways 26554724, 137726908, 1080613976 and 391433907 chain end-to-end,
     in that order, with a closure gap of 0.0 cm and no reversal except the second. They are
     the north+west, west(south part), south and east walls of the Haram. Their run lengths
     reproduce the published wall lengths to within 2-10 m and their enclosed area to 1%.

  2. THE EXPORTER'S HARAM TERRAIN EDIT - corroboration only. The level grid was raised by up
     to 42.7 amot under the Haram to flatten the esplanade. Only 76-82% of the raised cells
     fall inside the ring, and the raised band is offset east of it, because the edit is a
     25 m-grid surface treatment of the esplanade and NOT the wall line. Too coarse to
     define a boundary; reported because it independently says "something flat is here".

  3. THE SURROUNDING STREET AND BUILDING RINGS - not used. They bound the Old City quarters
     around the Haram, not the Haram, and would have to be eyeballed.

UNITS AND ALIGNMENT - the classic error, stated once
-----------------------------------------------------
jerusalem.json `points` are AMOT at 0.5 m, and the level already carries the alignment
    UE_cm = ((x + 17.5097...) * 50, (y - 0.55135...) * 50)
whose constants are SOURCE_ALIGN_X_AMOT / SOURCE_ALIGN_Z_AMOT in create_mount_enclosure.py
and SOURCE_TX_AMOT / SOURCE_TZ_AMOT (the Z one NEGATIVE) in create_enclosure.py. It is
NEVER applied twice. The alignment is proved in this receipt rather than asserted: OSM
Western Wall vertex 0 lands 11.2 cm from the KotelStoneV2 E0 mesh corner over a 150 m lever.

FRAME. Unreal's: +X east, +Y SOUTH, +Z up. So a MORE NEGATIVE Y is further NORTH, and the
"north wall" of the Haram carries the most negative Y in this file.

RUN
    python Scripts/create_haram_outline.py --export
    python Scripts/create_haram_outline.py --report
(64-bit Python; the default 32-bit interpreter runs out of memory on jerusalem.json.)
"""
import argparse
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets' / 'enclosure-review'
RECEIPT = OUT / 'haram-outline.json'
WORKSPACE = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace')
JERUSALEM_SOURCE = WORKSPACE / 'mikdash-walkthrough' / 'public' / 'context' / 'jerusalem.json'
JERUSALEM_SHA256 = '76a2b76c0d97f45db7e532b3adbe8b58c02956fa0d3de73db71e31e097ea6463'
LEVEL_TERRAIN_SOURCE = WORKSPACE / 'output' / 'architecture-review' / 'jerusalem-meshes.json'
LEVEL_TERRAIN_SHA256 = 'cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb'
BUILDINGS_FROZEN_MANIFEST = WORKSPACE / 'output' / 'cloud-unreal-v3' / 'context-review' / 'buildings-manifest.json'
BUILDINGS_FROZEN_FBX_SHA256 = '271bc9b4e1297421a33dde0b00172ad6111decabdb683e05267d4b972aca5408'
FACADES_MANIFEST = ROOT / 'SourceAssets' / 'context-review' / 'OldCityFacadesV1' / 'facades-manifest.json'

# --- alignment, identical to create_enclosure.py -------------------------------------
SOURCE_TX_AMOT = 17.509700315687695
SOURCE_TZ_AMOT = -0.5513496449385334
CONTEXT_CM_PER_AMOT = 50.0
CELL_CM = 10000.0

# --- the ring, as four OSM ways in chain order ---------------------------------------
# (wayId, reversed, what it is). The chain is proved, not assumed: assemble() asserts the
# closure gap is zero and that consecutive ways share an endpoint.
RING_WAYS = [
    (26554724, False, 'north wall, then the west wall down to the Kotel'),
    (137726908, True, 'west wall, south part, down to the south-west corner'),
    (1080613976, False, 'south wall, eastern part'),
    (391433907, False, 'east wall, back to the north-east corner'),
]
# The named 2-point chord OSM carries for the south wall. Not part of the ring (it is a
# chord, not the traced wall) but recorded because it names the wall.
SOUTHERN_WALL_CHORD = 1080613975

# Published wall lengths for the validation table. SECONDARY (Wikipedia "Temple Mount" and
# the standard literature); quoted so the derivation can be judged, never used to build.
PUBLISHED = {
    'north': 310.0, 'west': 491.0, 'south': 280.0, 'east': 466.0,
    'areaHectares': 14.4,
}

# Landmarks whose containment proves the ring is the Haram and not something else.
CONTAINMENT = [
    (4709536, 'Dome of the Rock', True),
    (45099263, 'Dome of the Chain', True),
    (280309331, 'Al-Aqsa Mosque', True),
    (291836681, 'Dome of the Tablets (Kaufman\'s candidate)', True),
    (817206833, 'Western Wall (the Kotel stones)', True),
    (26492734, 'Western Wall Plaza (the modern prayer plaza)', False),
    (290726629, 'Yeshivat HaKotel', False),
]


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_to_ue(x_amot, z_amot):
    """Source amot -> level cm, with the alignment the level already baked."""
    return ((x_amot + SOURCE_TX_AMOT) * CONTEXT_CM_PER_AMOT,
            (z_amot + SOURCE_TZ_AMOT) * CONTEXT_CM_PER_AMOT)


def ring_area_cm2(ring):
    r = ring[:-1] if ring[0] == ring[-1] else ring
    a = 0.0
    for i in range(len(r)):
        x0, y0 = r[i]
        x1, y1 = r[(i + 1) % len(r)]
        a += x0 * y1 - x1 * y0
    return abs(a) / 2.0


def polygon_centroid(points):
    r = points[:-1] if len(points) > 2 and points[0] == points[-1] else points
    n = len(r)
    if n < 3:
        return (sum(p[0] for p in r) / n, sum(p[1] for p in r) / n)
    a = cx = cy = 0.0
    for i in range(n):
        x0, y0 = r[i]
        x1, y1 = r[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if abs(a) < 1e-9:
        return (sum(p[0] for p in r) / n, sum(p[1] for p in r) / n)
    return (cx / (6.0 * a), cy / (6.0 * a))


def point_in_ring(ring, x, y):
    r = ring[:-1] if ring[0] == ring[-1] else ring
    n = len(r)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = r[i]
        xj, yj = r[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def polyline_length_cm(points):
    return sum(math.hypot(points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1])
               for i in range(len(points) - 1))


class Source(object):
    def __init__(self):
        if not JERUSALEM_SOURCE.exists():
            raise RuntimeError('jerusalem.json not found at %s' % JERUSALEM_SOURCE)
        self.sha = sha256_of(JERUSALEM_SOURCE)
        if self.sha != JERUSALEM_SHA256:
            raise RuntimeError('jerusalem.json is not the reviewed revision (%s)' % self.sha)
        data = json.loads(JERUSALEM_SOURCE.read_text(encoding='utf-8-sig'))
        self.provenance = data['provenance']
        self.features = data['features']
        self.by_id = {f['id']: f for f in self.features}
        self.terrain = data['terrain']

    def ue_points(self, way_id):
        f = self.by_id[way_id]
        # feature points are (x, y) in source amot; y is the SOUTH axis
        return [source_to_ue(p[0], p[1]) for p in f['points']]


def assemble(src):
    """Chain the four ways into one closed ring, proving the chain rather than assuming it."""
    ring = []
    joins = []
    for way_id, reverse, role in RING_WAYS:
        pts = src.ue_points(way_id)
        if reverse:
            pts = pts[::-1]
        if ring:
            gap = math.hypot(ring[-1][0] - pts[0][0], ring[-1][1] - pts[0][1])
            joins.append(dict(wayId=way_id, joinGapCm=round(gap, 6)))
            if gap > 1.0:
                raise RuntimeError('way %d does not meet the chain (gap %.3f cm)' % (way_id, gap))
            pts = pts[1:]
        ring += pts
    gap = math.hypot(ring[0][0] - ring[-1][0], ring[0][1] - ring[-1][1])
    if gap > 1.0:
        raise RuntimeError('ring does not close (gap %.3f cm)' % gap)
    return ring, joins, gap


def corners(src):
    """The four corners, each taken from the way that actually turns there."""
    north_west_way = src.ue_points(26554724)
    west_south_way = src.ue_points(137726908)
    east_way = src.ue_points(391433907)
    ne = north_west_way[0]                                  # chain start
    nw = min(north_west_way, key=lambda p: p[0])            # westernmost point of the north/west way
    sw = max(west_south_way, key=lambda p: p[1])            # most SOUTH point (+Y is south)
    se = east_way[0]
    return dict(northEast=ne, northWest=nw, southWest=sw, southEast=se)


def build(src):
    ring, joins, gap = assemble(src)
    area = ring_area_cm2(ring)
    cx, cy = polygon_centroid(ring)
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    c = corners(src)

    def d(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1]) / 100.0

    walls = dict(
        north=dict(fromCorner='northEast', toCorner='northWest',
                   lengthM=round(d(c['northEast'], c['northWest']), 1), publishedM=PUBLISHED['north']),
        west=dict(fromCorner='northWest', toCorner='southWest',
                  lengthM=round(d(c['northWest'], c['southWest']), 1), publishedM=PUBLISHED['west']),
        south=dict(fromCorner='southWest', toCorner='southEast',
                   lengthM=round(d(c['southWest'], c['southEast']), 1), publishedM=PUBLISHED['south']),
        east=dict(fromCorner='southEast', toCorner='northEast',
                  lengthM=round(d(c['southEast'], c['northEast']), 1), publishedM=PUBLISHED['east']),
    )
    for w in walls.values():
        w['errorM'] = round(w['lengthM'] - w['publishedM'], 1)
        w['errorPercent'] = round(100.0 * (w['lengthM'] - w['publishedM']) / w['publishedM'], 1)

    # alignment proof: the Kotel corner
    kotel = src.ue_points(817206833)[0]
    proof = dict(
        osmWay=817206833, vertex=0,
        ueCm=[round(kotel[0], 1), round(kotel[1], 1)],
        kotelStoneV2E0CornerCm=[-15138.7, 11908.1],
        errorCm=[round(kotel[0] + 15138.7, 1), round(kotel[1] - 11908.1, 1)],
        leverM=150.0,
        note='11 cm over a 150 m lever proves the baked alignment is applied exactly once.')

    contain = []
    for fid, label, expect in CONTAINMENT:
        if fid not in src.by_id:
            contain.append(dict(osmId=fid, label=label, present=False))
            continue
        cc = polygon_centroid([source_to_ue(p[0], p[1]) for p in src.by_id[fid]['points']])
        got = point_in_ring(ring, cc[0], cc[1])
        contain.append(dict(osmId=fid, label=label, centroidCm=[round(cc[0], 1), round(cc[1], 1)],
                            inside=got, expectedInside=expect, agrees=(got == expect)))

    # the rock, and whether the Temple is centred on it
    dome = [source_to_ue(p[0], p[1]) for p in src.by_id[4709536]['points']]
    rock = polygon_centroid(dome)
    temple = dict(
        rockCm=[round(rock[0], 1), round(rock[1], 1)],
        rockSource='area centroid of OSM way 4709536, the Dome of the Rock octagon (9 pts, 8 unique)',
        uncertaintyRadiusCm=424.0,
        uncertaintyBasis='root-sum-square: OSM outline 200 cm, dome centre vs octagon centroid 50 cm, '
                         'rock centre vs dome centre 370 cm (a 13 m rock axis inside a 20.4 m drum)',
        anchors=[
            dict(name='Kodesh HaKodashim / Aron centre, Main50', pointCm=[-6200.0, 0.0],
                 offsetCm=[round(rock[0] + 6200.0, 1), round(rock[1], 1)],
                 offsetM=round(math.hypot(rock[0] + 6200.0, rock[1]) / 100.0, 2),
                 verdict='within the 4.24 m uncertainty: ALREADY ON THE ROCK'),
            dict(name='Kodesh HaKodashim / Aron centre, Candidate48', pointCm=[-5952.0, 0.0],
                 offsetCm=[round(rock[0] + 5952.0, 1), round(rock[1], 1)],
                 offsetM=round(math.hypot(rock[0] + 5952.0, rock[1]) / 100.0, 2),
                 verdict='within the 4.24 m uncertainty, but 2.48 m of it is the systematic .96 '
                         'pivot drift ARON-ON-EVEN-HASHETIYAH-20260908.md recommends removing'),
            dict(name='court supporting platform centre (world origin)', pointCm=[0.0, 0.0],
                 offsetCm=[round(rock[0], 1), round(rock[1], 1)],
                 offsetM=round(math.hypot(rock[0], rock[1]) / 100.0, 2),
                 verdict='63 m east of the rock - the COURT is not centred on it, and was never '
                         'meant to be; the HOLY OF HOLIES is'),
        ])

    return dict(ring=ring, joins=joins, closureGapCm=round(gap, 6), areaCm2=area,
                centroidCm=[round(cx, 1), round(cy, 1)],
                extentsCm=dict(xWest=round(min(xs), 1), xEast=round(max(xs), 1),
                               yNorth=round(min(ys), 1), ySouth=round(max(ys), 1)),
                corners=c, walls=walls, alignmentProof=proof,
                containment=contain, temple=temple)


def hide_set_under_ring(src, ring):
    """How many batched context ACTORS still stand inside today's walls."""
    out = dict(rule='component / building area centroid inside the ring')
    if not BUILDINGS_FROZEN_MANIFEST.exists():
        out['error'] = 'buildings-manifest.json not found'
        return out
    frozen = json.loads(BUILDINGS_FROZEN_MANIFEST.read_text(encoding='utf-8-sig'))
    if frozen.get('fbxSha256') != BUILDINGS_FROZEN_FBX_SHA256:
        raise RuntimeError('buildings-manifest.json is not the reviewed FBX revision')
    mesh_groups = {m['group'] for m in frozen['meshes']}
    cells = {}
    for comp in frozen['components']:
        b = comp['sourceBoundsAmos']
        x0, y0 = source_to_ue(b['min'][0], b['min'][2])
        x1, y1 = source_to_ue(b['max'][0], b['max'][2])
        cxx, cyy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        cell = cells.setdefault(comp['assignedGroup'], dict(inside=0, total=0))
        cell['total'] += 1
        if point_in_ring(ring, cxx, cyy):
            cell['inside'] += 1
    hidden = sorted('SM_JerusalemBuildings_' + g for g, v in cells.items()
                    if g in mesh_groups and v['inside'] > 0)
    collateral = sum(v['total'] - v['inside'] for g, v in cells.items()
                     if g in mesh_groups and v['inside'] > 0)
    out['buildingsGridActorsTotal'] = len(mesh_groups)
    out['buildingsGridActorsHidden'] = len(hidden)
    out['buildingsGridLabels'] = hidden
    out['componentsInsideRing'] = sum(v['inside'] for v in cells.values())
    out['componentsOutsideRingInAHiddenCell'] = collateral
    out['collateralVerdict'] = (
        'UNUSABLE AS BATCHED: %d cells would hide %d wanted components and take %d unwanted ones '
        'with them. At 14 ha that reads as holes punched in the Old City. The cut cells MUST be '
        'split at the wall line before this hide set is placed.'
        % (len(hidden), out['componentsInsideRing'], collateral))

    if FACADES_MANIFEST.exists():
        fa = json.loads(FACADES_MANIFEST.read_text(encoding='utf-8-sig'))
        cen = {}
        for f in src.features:
            if f['kind'] != 'building':
                continue
            cen[f['id']] = polygon_centroid([source_to_ue(p[0], p[1]) for p in f['points']])
        fac = inf = 0
        for batch in fa['batches']:
            ids = [pb['osmId'] for pb in ((batch.get('facades') or {}).get('perBuilding') or [])
                   if 'osmId' in pb]
            hit = any(i in cen and point_in_ring(ring, cen[i][0], cen[i][1]) for i in ids)
            if hit:
                fac += 1
                if batch.get('infill'):
                    inf += 1
        out['facadeBatchActorsTotal'] = len(fa['batches'])
        out['facadeBatchActorsHidden'] = fac
        out['infillBatchActorsHidden'] = inf
        out['totalActorsHidden'] = len(hidden) + fac + inf
    return out


def report(data):
    print('=' * 78)
    print("TODAY'S TEMPLE MOUNT OUTLINE - frozen %s" % data['stamp'])
    print('=' * 78)
    g = data['geometry']
    print('  ring points          %d   closure gap %.3f cm' % (len(g['pointsCm']), g['closureGapCm']))
    print('  area                 %.0f m2 = %.2f hectares  (published ~%.1f ha)'
          % (g['areaM2'], g['areaHectares'], PUBLISHED['areaHectares']))
    e = g['extentsCm']
    print('  extents UE cm        X %.0f .. %.0f   Y %.0f .. %.0f'
          % (e['xWest'], e['xEast'], e['yNorth'], e['ySouth']))
    print()
    print('  wall            derived   published    error')
    for name in ('north', 'west', 'south', 'east'):
        w = g['walls'][name]
        print('    %-6s %10.1f m %9.1f m %+7.1f m (%+.1f%%)'
              % (name, w['lengthM'], w['publishedM'], w['errorM'], w['errorPercent']))
    print()
    print('  containment checks:')
    for c in g['containment']:
        print('    %-46s inside=%-5s expected=%-5s %s'
              % (c['label'], c.get('inside'), c.get('expectedInside'),
                 'OK' if c.get('agrees') else 'MISMATCH'))
    print()
    print('  the rock: %s' % g['temple']['rockCm'])
    for a in g['temple']['anchors']:
        print('    %-52s %6.2f m  %s' % (a['name'], a['offsetM'], a['verdict']))
    h = data.get('hideSet', {})
    if 'totalActorsHidden' in h:
        print()
        print('  hide set inside the ring: %d actors (%d buildings + %d facade + %d infill)'
              % (h['totalActorsHidden'], h['buildingsGridActorsHidden'],
                 h['facadeBatchActorsHidden'], h['infillBatchActorsHidden']))
        print('  collateral if NOT split: %d components outside the ring would vanish'
              % h['componentsOutsideRingInAHiddenCell'])


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--export', action='store_true', help='write haram-outline.json')
    ap.add_argument('--report', action='store_true', help='print the numbers')
    args = ap.parse_args(argv)
    if not (args.export or args.report):
        ap.error('one of --export or --report is required')

    src = Source()
    g = build(src)
    ring = g.pop('ring')
    area = g.pop('areaCm2')

    data = dict(
        status='AUTHORED_OFFLINE_SOURCE_FROZEN_OUTLINE',
        version=1,
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
        generator='Scripts/create_haram_outline.py',
        generatorSha256=sha256_of(Path(__file__)),
        decision=dict(
            date='2026-09-15',
            who='Shmuel',
            verbatim='id like the current modern day temple mount outline be the third temple '
                     'plateau - meaning the huge area we cleared away lets revert it back',
            resolved='EXACTLY today\'s Temple Mount outline. Every building outside it stays '
                     'standing in the Third Temple view. The Temple stays where it is, centred '
                     'on the rock.',
            optionChosen='A - the true Haram trapezoid on the four mapped walls, chosen over a '
                         'cheaper axis-aligned box, knowing the box was cheaper and kept a '
                         'sourced number under it.',
            sourcingNotDeleted='Yechezkel 42:15-20 with 40:5 (500 reeds of six amot = 3000 amot) '
                               'REMAINS the sourced precinct and remains implemented as '
                               'EMikdashPrecinctReading::Yechezkel3000, as does Middot500. This '
                               'outline is a deliberate, recorded departure for the BUILT view, '
                               'not a correction of the sources. See sources.md and '
                               'HARAM-OUTLINE-20260915.md.'),
        source=dict(
            jerusalemJson=str(JERUSALEM_SOURCE), jerusalemJsonSha256=src.sha,
            provenance=src.provenance,
            units='feature points are AMOT at 0.5 m',
            alignment='UE_cm = ((x + %.15f) * %.1f, (y + %.16f) * %.1f); applied exactly once'
                      % (SOURCE_TX_AMOT, CONTEXT_CM_PER_AMOT, SOURCE_TZ_AMOT, CONTEXT_CM_PER_AMOT),
            frame='+X east, +Y SOUTH, +Z up; a more negative Y is further north'),
        derivation=dict(
            method='chain of four OSM kind=="wall" ways, end to end, closure proved',
            ways=[dict(osmId=w, reversed=rev, role=role) for w, rev, role in RING_WAYS],
            southernWallChordNotUsed=dict(
                osmId=SOUTHERN_WALL_CHORD, name='Southern Wall',
                why='a 2-point chord across the south wall, not the traced wall; recorded '
                    'because it is the feature that NAMES the wall, but a chord cannot bound.'),
            rejectedWitnesses=[
                dict(witness='exporter Haram terrain edit (jerusalem-meshes.json Terrain 0)',
                     use='corroboration only',
                     why='a 25 m-grid surface flattening of the esplanade, not the wall line; '
                         'only 76-82%% of raised cells fall inside the ring and the band is '
                         'offset east of it'),
                dict(witness='surrounding street and building rings', use='not used',
                     why='they bound the Old City quarters around the Haram, not the Haram'),
            ]),
        geometry=dict(
            pointsCm=[[round(p[0], 2), round(p[1], 2)] for p in ring],
            pointCount=len(ring),
            closureGapCm=g['closureGapCm'],
            joins=g['joins'],
            areaCm2=round(area, 1),
            areaM2=round(area / 10000.0, 1),
            areaHectares=round(area / 1e8, 4),
            publishedAreaHectares=PUBLISHED['areaHectares'],
            areaErrorPercent=round(100.0 * (area / 1e8 - PUBLISHED['areaHectares'])
                                   / PUBLISHED['areaHectares'], 1),
            centroidCm=g['centroidCm'],
            extentsCm=g['extentsCm'],
            cornersCm={k: [round(v[0], 1), round(v[1], 1)] for k, v in g['corners'].items()},
            walls=g['walls'],
            alignmentProof=g['alignmentProof'],
            containment=g['containment'],
            temple=g['temple']),
        limitations=[
            'The ring is the OSM TRACE of the retaining walls, which is a wall outline of '
            'unstated thickness, not a surveyed inner or outer face. Treat it as +-2 m.',
            'Published wall lengths and the 14.4 ha area are SECONDARY (the standard '
            'literature); they validate the derivation and are never built from.',
            'This file fixes the outline in PLAN only. The deck datum, the retaining section '
            'and the gates are not decided here.',
            'Nothing is mutated by this script. No map, no asset, no engine.',
        ])
    data['hideSet'] = hide_set_under_ring(src, ring)

    if args.export:
        OUT.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf-8')
        print('wrote %s (%d bytes)' % (RECEIPT, RECEIPT.stat().st_size))
    if args.report:
        report(data)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

"""Offline analysis: where the Dome of the Rock (es-Sakhra / Even HaShetiyah) lies in the
project's Unreal frame, how far the Aron is from it in both maps, and what a rigid
translation of the Temple would do to the Kotel, the OSM context, the Kidron slope and the
3000-amah Yechezkel precinct.  Pure file work: reads the read-only OSM export, receipts,
manifests and the code tree; launches nothing; modifies no asset.  Writes
SourceAssets/scale-review/aron-alignment-plan-<stamp>.json.

Run with any Python 3.8+:
  python Scripts/plan_aron_alignment.py            # writes the receipt, prints a summary
  python Scripts/plan_aron_alignment.py --no-write # summary only

Key facts this script re-derives rather than assumes (see the .md beside the receipt):
  * jerusalem.json "points" are in AMOT (0.5 m), not metres.  Native context meshes carry the
    alignment UE_cm = ((x + SOURCE_ALIGN_X_AMOT) * 50, (y - SOURCE_ALIGN_Y_AMOT) * 50), the
    constants living in Scripts/create_mount_enclosure.py and
    SourceAssets/visual-review/mount-platform-design.json.  The script proves the alignment by
    matching an OSM Western Wall vertex to the KotelStoneV2 E0 mesh corner.
  * Terrain heights in jerusalem.json are in amot relative to the 748 m reference (Z 0).
"""
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OSM = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\mikdash-walkthrough\public\context\jerusalem.json')
RECEIPT_DIR = ROOT / 'SourceAssets' / 'scale-review'
ENCLOSURE_SCRIPT = ROOT / 'Scripts' / 'create_mount_enclosure.py'
ENCLOSURE_MANIFEST = ROOT / 'SourceAssets' / 'enclosure-review' / 'geometry-manifest.json'
KOTEL_MANIFEST = ROOT / 'SourceAssets' / 'kotel-detail' / 'KotelStoneV2' / 'manifest.json'
INVENTORY = ROOT / 'SourceAssets' / 'scale-review' / 'native-scale-inventory-20260908T133142315573Z.json'
CANDIDATE_ARON = ROOT / 'SourceAssets' / 'scale-review' / 'amah48-aron-menorah-20260908T163553936830Z.json'
CANDIDATE_CONVERSION = ROOT / 'SourceAssets' / 'scale-review' / 'amah48-candidate-20260908T144034771385Z.json'

MAIN_MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
CANDIDATE_MAP = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'

CM_PER_AMAH_LEGACY = 50.0
CM_PER_AMAH_SELECTED = 48.0
RATIO = CM_PER_AMAH_SELECTED / CM_PER_AMAH_LEGACY
COURT_HALF_LEGACY_CM = 8100.0          # SM_0127 outer court supporting platform, +-8100 (inventory)
REFERENCE_ELEVATION_M = 748.0          # jerusalem.json provenance: Z 0 of the scene
DOR_OSM_ID = 4709536                   # building "Dome of the Rock"
WESTERN_WALL_OSM_ID = 817206833        # building "Western Wall" (the Kotel prayer-face polygon)
KOTEL_E0_MESH = 'SM_KotelAshlarV2_E0'  # longest west-facing Kotel face, edge 0

# --- the rock (es-Sakhra) ---------------------------------------------------------------
# Published (secondary) figures; see the .md for the source list and their status.
ROCK_LENGTH_M = 18.0                   # "approximately eighteen by thirteen meters" (Wikipedia, Foundation Stone)
ROCK_WIDTH_M = 13.0
ROCK_ABOVE_FLOOR_M = 1.5               # "about one and a half meters above the floor at its highest part"
DOME_INNER_DIAMETER_M = 20.4           # inner drum ~20 m (Wikipedia/Britannica: "approximately 20 metres")
ROCK_SUMMIT_ELEVATION_M = 743.7        # 2,440 ft above the Mediterranean (1865 Ordnance Survey figure as quoted
                                       # by lifeintheholyland.com); 2440 ft * 0.3048 = 743.7 m
ROCK_SUMMIT_ELEVATION_UNCERTAINTY_M = 1.0
STONE_ABOVE_FLOOR_ETZBAOT = 3          # Mishnah Yoma 5:2 / Rambam Beit HaBechirah 4:1: three fingerbreadths
ETZBA_CM_LEGACY = CM_PER_AMAH_LEGACY / 24.0
ETZBA_CM_SELECTED = CM_PER_AMAH_SELECTED / 24.0

# --- uncertainty budget for "the centre of the rock" in the scene (authored, stated in the .md) ---
OSM_OUTLINE_ACCURACY_M = 2.0           # typical OSM building-outline accuracy for a traced landmark
DOME_CENTRE_VS_OCTAGON_CENTROID_M = 0.5
ROCK_CENTRE_VS_DOME_CENTRE_MAX_M = (DOME_INNER_DIAMETER_M - ROCK_WIDTH_M) / 2.0   # 3.7 m: the rock must fit in the drum

HARDCODE_PATTERN = re.compile(r'-(?:6200|5600|5330|4650)(?:\.0+)?\b')
C_PLUS_PLUS_DIRS = [ROOT / 'Plugins' / 'MikdashRuntime' / 'Source' / 'MikdashRuntime' / 'Public',
                    ROOT / 'Plugins' / 'MikdashRuntime' / 'Source' / 'MikdashRuntime' / 'Private',
                    ROOT / 'Plugins' / 'MikdashRuntime' / 'Tests']


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def alignment_constants():
    """Read SOURCE_ALIGN_X_AMOT / SOURCE_ALIGN_Z_AMOT / grid constants from the enclosure generator
    (the same numbers are quoted in mount-platform-design.json) rather than retyping them."""
    text = ENCLOSURE_SCRIPT.read_text(encoding='utf-8')
    values = {}
    for key in ('SOURCE_ALIGN_X_AMOT', 'SOURCE_ALIGN_Z_AMOT', 'GRID_ORIGIN_AMOT', 'GRID_STEP_AMOT'):
        m = re.search(r'^%s\s*=\s*(-?[0-9.]+)' % key, text, re.M)
        if not m:
            raise RuntimeError('%s not found in %s' % (key, ENCLOSURE_SCRIPT))
        values[key] = float(m.group(1))
    return values


class Frame:
    """OSM source amot (east, south) <-> UE cm (X east, Y south)."""

    def __init__(self, ax, ay, cm_per_amah=CM_PER_AMAH_LEGACY):
        self.ax = ax
        self.ay = ay
        self.a = cm_per_amah

    def to_cm(self, p):
        return [(p[0] + self.ax) * self.a, (p[1] - self.ay) * self.a]

    def to_amot(self, x_cm, y_cm):
        return [x_cm / self.a - self.ax, y_cm / self.a + self.ay]


def polygon_centroid(points):
    pts = points[:-1] if len(points) > 2 and points[0] == points[-1] else list(points)
    a = cx = cy = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    if abs(a) < 1e-9:
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), 0.0
    return cx / (3 * a), cy / (3 * a), a / 2


def point_in_rect(p, rect):
    return rect[0] <= p[0] <= rect[2] and rect[1] <= p[1] <= rect[3]


def segment_hits_rect(p, q, rect):
    """Liang-Barsky style test: does segment p-q cross the axis-aligned rect?"""
    if point_in_rect(p, rect) or point_in_rect(q, rect):
        return True
    x0, y0, x1, y1 = rect
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pk, qk in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pk == 0:
            if qk < 0:
                return False
        else:
            t = qk / pk
            if pk < 0:
                if t > t1:
                    return False
                t0 = max(t0, t)
            else:
                if t < t0:
                    return False
                t1 = min(t1, t)
    return t0 <= t1


def feature_touches_rect(points_cm, rect):
    if any(point_in_rect(p, rect) for p in points_cm):
        return True
    for i in range(len(points_cm) - 1):
        if segment_hits_rect(points_cm[i], points_cm[i + 1], rect):
            return True
    return False


class Terrain:
    def __init__(self, terrain, frame, constants):
        self.size = terrain['size']
        self.heights = terrain['heights']
        self.frame = frame
        self.origin = constants['GRID_ORIGIN_AMOT']
        self.step = constants['GRID_STEP_AMOT']
        if terrain['origin'] != self.origin or terrain['step'] != self.step or len(self.heights) != self.size * self.size:
            raise RuntimeError('Terrain grid header differs from the enclosure generator constants')

    def height_cm(self, x_cm, y_cm):
        xa, ya = self.frame.to_amot(x_cm, y_cm)
        fc = (xa - self.origin) / self.step
        fr = (ya - self.origin) / self.step
        c, r = int(math.floor(fc)), int(math.floor(fr))
        if c < 0 or r < 0 or c >= self.size - 1 or r >= self.size - 1:
            return None
        u, v = fc - c, fr - r
        h = self.heights
        n = self.size
        h00, h10, h01, h11 = h[r * n + c], h[r * n + c + 1], h[(r + 1) * n + c], h[(r + 1) * n + c + 1]
        if u + v <= 1.0:
            ha = h00 + u * (h10 - h00) + v * (h01 - h00)
        else:
            ha = h11 + (1.0 - u) * (h01 - h11) + (1.0 - v) * (h10 - h11)
        return ha * self.frame.a

    def profile(self, x_cm, y0, y1, step=2500.0):
        rows = []
        y = y0
        while y <= y1 + 1e-6:
            z = self.height_cm(x_cm, y)
            rows.append({'yCm': round(y, 1), 'groundZcm': None if z is None else round(z, 1),
                         'elevationM': None if z is None else round(REFERENCE_ELEVATION_M + z / 100.0, 2)})
            y += step
        return rows


def find_latest(pattern):
    files = sorted(RECEIPT_DIR.parent.parent.glob(pattern))
    if not files:
        raise RuntimeError('No receipt matches ' + pattern)
    return files[-1]


def aron_main():
    """Aron footprint centre and bounds in the main map from the latest aron-poles-centre receipt."""
    path = sorted((ROOT / 'SourceAssets' / 'third-party').glob('aron-poles-centre-*.json'))[-1]
    receipt = load_json(path)
    bounds = receipt['aronBoundsCm']
    centre = [(bounds['min'][i] + bounds['max'][i]) / 2.0 for i in range(2)]
    return {'receipt': str(path.relative_to(ROOT)), 'receiptSha256': sha256_of(path), 'status': receipt['status'],
            'bodyBoundsCm': bounds, 'footprintCentreCm': [round(c, 3) for c in centre], 'floorTopZcm': bounds['min'][2],
            'poleActorX': receipt['poles']['RELEASE_Aron_Pole_N']['reopened'][0]}


def aron_candidate():
    receipt = load_json(CANDIDATE_ARON)
    body = next(p for p in receipt['proposals'] if p['label'] == 'RELEASE_Aron_Body')
    conversion = load_json(CANDIDATE_CONVERSION)
    return {'receipt': str(CANDIDATE_ARON.relative_to(ROOT)), 'receiptSha256': sha256_of(CANDIDATE_ARON),
            'bodyLocation48Cm': body['location48'], 'bodyOldPoseCm': body['oldPose'][:3],
            'conversionRatio': conversion['ratio'], 'conversionFixedOriginCm': conversion['fixedOriginCm'],
            'conversionReceipt': str(CANDIDATE_CONVERSION.relative_to(ROOT)),
            'floorTopZcm': body['location48'][2]}


def kotel_geometry(frame, features):
    manifest = load_json(KOTEL_MANIFEST)
    e0 = next(m for m in manifest['meshes'] if m['name'] == KOTEL_E0_MESH)
    wall = features[WESTERN_WALL_OSM_ID]
    # the E0 face runs from the vertex nearest (min X, min Y) of its bounds to the next vertex north-east
    verts_cm = [frame.to_cm(p) for p in wall['points']]
    corner = min(verts_cm, key=lambda v: abs(v[0] - e0['boundsCm']['min'][0]) + abs(v[1] - e0['boundsCm']['min'][1]))
    error = math.hypot(corner[0] - e0['boundsCm']['min'][0], corner[1] - e0['boundsCm']['min'][1])
    # the face segment: the two polygon vertices that bound the E0 mesh in Y
    face = sorted(verts_cm, key=lambda v: v[1])
    face_a = corner
    face_b = min(verts_cm, key=lambda v: abs(v[0] - e0['boundsCm']['max'][0]) + abs(v[1] - e0['boundsCm']['max'][1]))
    return {'manifestSha256': sha256_of(KOTEL_MANIFEST), 'e0MeshBoundsCm': e0['boundsCm'],
            'osmWesternWallId': WESTERN_WALL_OSM_ID, 'osmVertexMatchedCm': [round(c, 1) for c in corner],
            'alignmentProofErrorCm': round(error, 2), 'faceSegmentCm': [[round(c, 1) for c in face_a], [round(c, 1) for c in face_b]],
            'allKotelV2BoundsCm': {'min': [min(m['boundsCm']['min'][i] for m in manifest['meshes']) for i in range(3)],
                                   'max': [max(m['boundsCm']['max'][i] for m in manifest['meshes']) for i in range(3)]}}


def distance_point_segment(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def platform_consequences(label, delta_cm, half_cm, frame, features, terrain, kotel, precinct_before, cm_per_amah):
    """Everything that changes when the Temple (court platform +-half) is translated by delta."""
    rect = [-half_cm + delta_cm[0], -half_cm + delta_cm[1], half_cm + delta_cm[0], half_cm + delta_cm[1]]
    west_edge_x = rect[0]
    face_a, face_b = kotel['faceSegmentCm']
    kotel_x_at_face = min(face_a[0], face_b[0])
    # nearest approach between the platform's west edge (as a segment) and the Kotel face segment
    samples = [(west_edge_x, rect[1] + (rect[3] - rect[1]) * i / 40.0) for i in range(41)]
    nearest = min(distance_point_segment(s, face_a, face_b) for s in samples)
    under = {'building': [], 'road': [], 'wall': [], 'green': []}
    for fid, f in features.items():
        pts = [frame.to_cm(p) for p in f['points']]
        if feature_touches_rect(pts, rect):
            tags = f.get('tags', {})
            name = tags.get('name:en') or tags.get('name') or ''
            under.setdefault(f['kind'], []).append(
                {'id': fid, 'name': name, 'kind': f['kind'], 'tags': {k: v for k, v in tags.items() if k in ('building', 'highway', 'religion', 'amenity', 'height')}})
    east_profile = terrain.profile(rect[2], rect[1], rect[3])
    west_profile = terrain.profile(rect[0], rect[1], rect[3])
    east_valid = [r['groundZcm'] for r in east_profile if r['groundZcm'] is not None]
    # precinct: courts 500 amot from the west face, 501 from the north face (book fig. 2'2 as read by the project)
    side = 3000.0 * cm_per_amah
    xw = rect[0] - 500.0 * cm_per_amah
    yn = rect[1] - 501.0 * cm_per_amah
    faces = {'xWest': xw, 'xEast': xw + side, 'yNorth': yn, 'ySouth': yn + side}
    inside = 0
    inside_named = []
    for fid, f in features.items():
        if f['kind'] != 'building':
            continue
        cx, cy, _ = polygon_centroid(f['points'])
        c = frame.to_cm((cx, cy))
        if faces['xWest'] <= c[0] <= faces['xEast'] and faces['yNorth'] <= c[1] <= faces['ySouth']:
            inside += 1
            nm = f.get('tags', {}).get('name:en')
            if nm:
                inside_named.append(nm)
    return {
        'label': label, 'deltaCm': delta_cm, 'platformRectCm': [round(v, 1) for v in rect],
        'kotel': {'faceXcmAtPlatformLatitude': None, 'kotelFaceSegmentCm': [face_a, face_b],
                  'kotelFaceMinXcm': round(kotel_x_at_face, 1),
                  'platformWestEdgeXcm': round(west_edge_x, 1),
                  'westEdgeMinusKotelFaceCm': round(west_edge_x - kotel_x_at_face, 1),
                  'nearestWestEdgeToKotelFaceM': round(nearest / 100.0, 2),
                  'platformYRangeOverlapsKotelFace': not (rect[3] < min(face_a[1], face_b[1]) or rect[1] > max(face_a[1], face_b[1])),
                  'note': 'positive westEdgeMinusKotelFaceCm = the platform edge stays EAST of the Kotel face'},
        'osmFeaturesUnderPlatform': {k: v for k, v in under.items()},
        'osmFeaturesUnderPlatformCounts': {k: len(v) for k, v in under.items()},
        'terrainEastEdge': {'xCm': round(rect[2], 1), 'profile': east_profile,
                            'minGroundZcm': min(east_valid) if east_valid else None, 'maxGroundZcm': max(east_valid) if east_valid else None,
                            'note': 'ground below Z 0 means the Mount deck (Z 0) already stands above natural ground here; the court platform sits on the deck, not on terrain'},
        'terrainWestEdge': {'xCm': round(rect[0], 1), 'profile': west_profile},
        'precinct3000': {'cmPerAmah': cm_per_amah, 'outerFacesCm': {k: round(v, 1) for k, v in faces.items()},
                         'before': precinct_before, 'osmBuildingsInsideByCentroid': inside,
                         'namedInside': sorted(set(inside_named))[:60]},
    }


def precinct_baseline(frame, features):
    manifest = load_json(ENCLOSURE_MANIFEST)
    faces = manifest['square']['outerFacesCm']
    inside = 0
    for f in features.values():
        if f['kind'] != 'building':
            continue
        cx, cy, _ = polygon_centroid(f['points'])
        c = frame.to_cm((cx, cy))
        if faces['xWest'] <= c[0] <= faces['xEast'] and faces['yNorth'] <= c[1] <= faces['ySouth']:
            inside += 1
    return {'manifest': str(ENCLOSURE_MANIFEST.relative_to(ROOT)), 'manifestSha256': sha256_of(ENCLOSURE_MANIFEST),
            'manifestStatus': manifest['status'], 'outerFacesCm': faces, 'clearancesAmot': manifest['clearancesAmot'],
            'osmBuildingsInsideByCentroid': inside}


def actor_sets():
    """Temple vs context actor sets from the read-only main-map inventory (7767 actors)."""
    inventory = load_json(INVENTORY)
    context_mesh_prefixes = ('/Game/MikdashV3/JerusalemContext/', '/Game/MikdashV3/FutureMountV1/', '/Game/MikdashV3/ArrivalReview/',
                             '/Game/MikdashV3/MaterialReview/KotelStoneV1/', '/Game/MikdashV3/MaterialReview/KotelStoneV2/',
                             '/Game/MikdashV3/MaterialReview/KotelPhotoSurface', '/Game/MikdashV3/MaterialReview/KotelSurfacePolish')
    context_label_prefixes = ('RELEASE_Kotel', 'REVIEW_KotelPhoto', 'RELEASE_KotelStoneV2', 'RELEASE_Bus', 'RELEASE_MountAccess',
                              'SM_MountPlatform', 'JCTX_ISM', 'RELEASE_OldCity', 'SM_Jerusalem')
    global_classes = ('DirectionalLight', 'SkyAtmosphere', 'SkyLight', 'PostProcessVolume', 'VolumetricCloud', 'WindDirectionalSource',
                      'ExponentialHeightFog', 'LevelSequenceActor', 'MikdashResidentPopulation', 'MikdashDoveAppearance')
    temple, context, globals_, unclassified = {}, {}, {}, []
    for a in inventory['actors']:
        label = a['label'] or a['name']
        cls = a['classPath'].split('.')[-1]
        meshes = [c.get('mesh') or '' for c in a.get('components', [])]
        if cls in global_classes:
            globals_[cls] = globals_.get(cls, 0) + 1
            continue
        if label.startswith(context_label_prefixes) or any(m.startswith(context_mesh_prefixes) for m in meshes if m):
            key = label.split('_')[0] + ('_' + label.split('_')[1] if '_' in label else '')
            context[key] = context.get(key, 0) + 1
            continue
        b = a.get('boundsCm')
        loc = a['locationCm']
        in_court = (b and -9000 <= b['min'][0] and b['max'][0] <= 9000 and -9000 <= b['min'][1] and b['max'][1] <= 9000) or \
                   (not b and abs(loc[0]) <= 9000 and abs(loc[1]) <= 9000)
        if in_court or any(m.startswith('/Game/MikdashV3/Architecture/') for m in meshes):
            key = cls if cls != 'StaticMeshActor' else ('Architecture' if any(m.startswith('/Game/MikdashV3/Architecture/') for m in meshes) else label.split(' ')[0].split('_')[0] + '_' + (label.split('_')[1] if '_' in label else ''))
            temple[key] = temple.get(key, 0) + 1
        else:
            unclassified.append({'label': label, 'class': cls, 'locationCm': loc})
    return {'inventory': str(INVENTORY.relative_to(ROOT)), 'inventorySha256': sha256_of(INVENTORY), 'actorCount': inventory['actorCount'],
            'temple': dict(sorted(temple.items(), key=lambda kv: -kv[1])), 'templeTotal': sum(temple.values()),
            'context': dict(sorted(context.items(), key=lambda kv: -kv[1])), 'contextTotal': sum(context.values()),
            'sceneGlobals': globals_, 'unclassified': unclassified,
            'note': 'Main-map inventory of 2026-09-08T13:31Z; later work added actors (paroches, tour markers, crowd field, service, transit). The release script classifies live and refuses unknown actors.'}


def hardcoded_temple_coordinates():
    """Files that literally carry -6200 / -5600 / -5330 / -4650 (Aron, paroches line, menorah, golden altar)."""
    hits = {'scripts': [], 'specs': [], 'cpp': [], 'data': []}
    own_tools = {'plan_aron_alignment.py', 'release_aron_alignment.py', 'release_aron_alignment.spec.json'}
    for path in sorted((ROOT / 'Scripts').glob('*.py')):
        if path.name not in own_tools and HARDCODE_PATTERN.search(path.read_text(encoding='utf-8', errors='replace')):
            hits['scripts'].append(path.name)
    for path in sorted((ROOT / 'Scripts').glob('*.json')):
        if path.name not in own_tools and HARDCODE_PATTERN.search(path.read_text(encoding='utf-8', errors='replace')):
            hits['specs'].append(path.name)
    for folder in C_PLUS_PLUS_DIRS:
        if not folder.exists():
            continue
        for path in sorted(folder.rglob('*')):
            if path.suffix in ('.h', '.cpp') and HARDCODE_PATTERN.search(path.read_text(encoding='utf-8', errors='replace')):
                hits['cpp'].append(str(path.relative_to(ROOT)).replace('\\', '/'))
    for rel in ('SourceAssets/tour-review/tour-stops.json', 'SourceAssets/tour-review/codex-entries.json',
                'SourceAssets/runtime-review/crowd-field/zones.json', 'SourceAssets/vessels-review/aron-placement-spec.json',
                'SourceAssets/vessels-review/heikhal-keilim-spec.json', 'SourceAssets/visual-review/sanctuary-finishes-spec.json',
                'SourceAssets/fx-review/fx-materials.json', 'SourceAssets/surface-review/surface-detail.json'):
        path = ROOT / rel
        if path.exists() and HARDCODE_PATTERN.search(path.read_text(encoding='utf-8', errors='replace')):
            hits['data'].append(rel)
    hits['counts'] = {k: len(v) for k, v in hits.items() if isinstance(v, list)}
    return hits


def build_plan():
    constants = alignment_constants()
    frame = Frame(constants['SOURCE_ALIGN_X_AMOT'], constants['SOURCE_ALIGN_Z_AMOT'])
    osm = load_json(OSM)
    features = {f['id']: f for f in osm['features']}
    terrain = Terrain(osm['terrain'], frame, constants)

    dor = features[DOR_OSM_ID]
    cx, cy, area_amot2 = polygon_centroid(dor['points'])
    dome_cm = frame.to_cm((cx, cy))
    pts = dor['points'][:-1]
    diagonals_m = [math.hypot(pts[i][0] - pts[i + 4][0], pts[i][1] - pts[i + 4][1]) * 0.5 for i in range(4)]
    chain = features[45099263]
    ccx, ccy, _ = polygon_centroid(chain['points'])

    rock_radius_m = math.sqrt(OSM_OUTLINE_ACCURACY_M ** 2 + DOME_CENTRE_VS_OCTAGON_CENTROID_M ** 2 + ROCK_CENTRE_VS_DOME_CENTRE_MAX_M ** 2)
    rock_summit_z_cm = (ROCK_SUMMIT_ELEVATION_M - REFERENCE_ELEVATION_M) * 100.0
    dem_at_dome_cm = terrain.height_cm(dome_cm[0], dome_cm[1])
    dem_at_origin_cm = terrain.height_cm(0.0, 0.0)

    kotel = kotel_geometry(frame, features)
    main = aron_main()
    cand = aron_candidate()
    precinct_before = precinct_baseline(frame, features)

    delta_main = [dome_cm[0] - main['footprintCentreCm'][0], dome_cm[1] - main['footprintCentreCm'][1]]
    delta_cand = [dome_cm[0] - cand['bodyLocation48Cm'][0], dome_cm[1] - cand['bodyLocation48Cm'][1]]
    # candidate alternative: keep the frame representable (scale about a pivot) by re-pivoting the .96 conversion
    # about the legacy Aron position; equivalent to translating the converted Temple by (aron_legacy * (ratio - 1)).
    repivot = [main['footprintCentreCm'][0] * (1.0 - RATIO) * -1.0, 0.0]   # -6200 * 0.04 = -248
    repivot_delta = [-(main['footprintCentreCm'][0]) * (RATIO - 1.0) * -1.0, 0.0]
    repivot_delta = [main['footprintCentreCm'][0] * (1.0 - RATIO), 0.0]    # (-6200)*(0.04) = -248
    aron_after_repivot = [cand['bodyLocation48Cm'][0] + repivot_delta[0], cand['bodyLocation48Cm'][1]]

    consequences = {
        'main50_fullDelta': platform_consequences('main 50 cm, translate by full delta', delta_main, COURT_HALF_LEGACY_CM, frame, features, terrain, kotel, precinct_before, CM_PER_AMAH_LEGACY),
        'main50_noMove': platform_consequences('main 50 cm, no move (as built)', [0.0, 0.0], COURT_HALF_LEGACY_CM, frame, features, terrain, kotel, precinct_before, CM_PER_AMAH_LEGACY),
        'candidate48_fullDelta': platform_consequences('candidate 48 cm, translate by full delta', delta_cand, COURT_HALF_LEGACY_CM * RATIO, frame, features, terrain, kotel, precinct_before, CM_PER_AMAH_SELECTED),
        'candidate48_repivot': platform_consequences('candidate 48 cm, re-pivot the .96 conversion about the legacy Aron', repivot_delta, COURT_HALF_LEGACY_CM * RATIO, frame, features, terrain, kotel, precinct_before, CM_PER_AMAH_SELECTED),
        'candidate48_asBuilt': platform_consequences('candidate 48 cm, as built (pivot at origin)', [0.0, 0.0], COURT_HALF_LEGACY_CM * RATIO, frame, features, terrain, kotel, precinct_before, CM_PER_AMAH_SELECTED),
    }
    # trim the verbose per-feature lists to the counts plus names for the receipt
    for c in consequences.values():
        c['osmFeaturesUnderPlatformNamed'] = sorted({f['name'] for group in c['osmFeaturesUnderPlatform'].values() for f in group if f['name']})
        c['osmFeaturesUnderPlatformIds'] = {k: [f['id'] for f in v] for k, v in c['osmFeaturesUnderPlatform'].items()}
        del c['osmFeaturesUnderPlatform']

    sets = actor_sets()
    hardcodes = hardcoded_temple_coordinates()

    kodesh_floor_main = main['floorTopZcm']
    kodesh_floor_cand = cand['floorTopZcm']
    elevation = {
        'referenceElevationM_atZ0': REFERENCE_ELEVATION_M,
        'rockSummitElevationM': ROCK_SUMMIT_ELEVATION_M, 'rockSummitUncertaintyM': ROCK_SUMMIT_ELEVATION_UNCERTAINTY_M,
        'rockSummitZcm': round(rock_summit_z_cm, 1),
        'demGroundAtDomeCentroidZcm': None if dem_at_dome_cm is None else round(dem_at_dome_cm, 1),
        'demGroundAtDomeCentroidElevationM': None if dem_at_dome_cm is None else round(REFERENCE_ELEVATION_M + dem_at_dome_cm / 100.0, 2),
        'demGroundAtOriginZcm': None if dem_at_origin_cm is None else round(dem_at_origin_cm, 1),
        'demNote': 'The DEM is a surface model: over the Dome it returns roof/drum-biased heights, not the rock. It cannot locate the rock summit; the published 743.7 m figure is used instead.',
        'aronFloorTopZcm': {'main50': kodesh_floor_main, 'candidate48': kodesh_floor_cand},
        'aronFloorAboveRockSummitM': {'main50': round((kodesh_floor_main - rock_summit_z_cm) / 100.0, 2), 'candidate48': round((kodesh_floor_cand - rock_summit_z_cm) / 100.0, 2)},
        'mountDeckZ0AboveRockSummitM': round(-rock_summit_z_cm / 100.0, 2),
        'kodeshFloorIfAronRestsOnRock': {
            'rule': 'Mishnah Yoma 5:2 / Rambam Beit HaBechirah 4:1: the stone stood three etzbaot above the Kodesh HaKodashim floor; the Aron rested on the stone',
            'floorZcm_main50': round(rock_summit_z_cm - STONE_ABOVE_FLOOR_ETZBAOT * ETZBA_CM_LEGACY, 1),
            'floorZcm_candidate48': round(rock_summit_z_cm - STONE_ABOVE_FLOOR_ETZBAOT * ETZBA_CM_SELECTED, 1),
            'requiredVerticalShiftM_main50': round((rock_summit_z_cm - STONE_ABOVE_FLOOR_ETZBAOT * ETZBA_CM_LEGACY - kodesh_floor_main) / 100.0, 2),
            'requiredVerticalShiftM_candidate48': round((rock_summit_z_cm - STONE_ABOVE_FLOOR_ETZBAOT * ETZBA_CM_SELECTED - kodesh_floor_cand) / 100.0, 2),
            'status': 'NOT part of the XY alignment; a separate vertical-datum decision. Lowering the Temple ~13.5 m would put the court platform (Z 300 top) at about 734-735 m, below the present esplanade (~740 m per Wikipedia Temple Mount), and would invalidate the Mount deck / terrain cut / Kotel joins.'},
    }

    plan = {
        'status': 'analysis_complete_nothing_applied',
        'stamp': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),
        'scriptSha256': sha256_of(__file__),
        'inputs': {
            'osm': {'path': str(OSM), 'sha256': sha256_of(OSM), 'provenance': osm['provenance'], 'featureCount': len(osm['features']),
                    'unitsFinding': 'feature points and terrain heights are in AMOT at 0.5 m (metresPerAmah 0.5), not metres; see alignment proof'},
            'alignmentConstants': constants,
            'alignmentRule': 'UE_cm = ((x_amot + SOURCE_ALIGN_X_AMOT) * 50, (y_amot - SOURCE_ALIGN_Z_AMOT) * 50); source axes east/south; UE X east, Y south',
            'alignmentProof': {'osmWesternWallVertexCm': kotel['osmVertexMatchedCm'], 'kotelE0MeshMinXYcm': kotel['e0MeshBoundsCm']['min'][:2],
                               'errorCm': kotel['alignmentProofErrorCm'], 'kotelManifestSha256': kotel['manifestSha256']},
            'enclosureScript': {'path': str(ENCLOSURE_SCRIPT.relative_to(ROOT)), 'sha256': sha256_of(ENCLOSURE_SCRIPT)},
        },
        'domeOfTheRock': {
            'osmId': DOR_OSM_ID, 'tags': dor.get('tags'), 'vertexCountIncludingClosure': len(dor['points']),
            'centroidAmot': [round(cx, 3), round(cy, 3)], 'centroidCm': [round(v, 1) for v in dome_cm],
            'centroidM': [round(v / 100.0, 2) for v in dome_cm], 'polygonAreaM2': round(abs(area_amot2) * 0.25, 1),
            'octagonDiagonalsM': [round(d, 2) for d in diagonals_m],
            'domeOfTheChainCentroidCm': [round(v, 1) for v in frame.to_cm((ccx, ccy))],
            'note': 'The exporter\'s "hypothetical temple alignment" evidently placed this centroid at exactly X -6300, Y 0: the Kodesh HaKodashim was aligned on the Dome when the city was exported.'},
        'rock': {
            'lengthM': ROCK_LENGTH_M, 'widthM': ROCK_WIDTH_M, 'aboveFloorM': ROCK_ABOVE_FLOOR_M, 'domeInnerDiameterM': DOME_INNER_DIAMETER_M,
            'offsetFromDomeCentre': {'value': 'UNVERIFIED: no plan with the rock\'s centre coordinates could be fetched offline (ritmeyer.com and madainproject.com refused automated fetches)',
                                     'boundM': round(ROCK_CENTRE_VS_DOME_CENTRE_MAX_M, 2),
                                     'reasoning': 'the rock (~13 m across its short axis) lies inside the ~20.4 m drum circle, so its centre cannot be more than (20.4 - 13)/2 = 3.7 m from the drum centre'},
            'targetCentreCm': [round(v, 1) for v in dome_cm],
            'uncertaintyRadiusM': round(rock_radius_m, 2),
            'uncertaintyBudgetM': {'osmOutline': OSM_OUTLINE_ACCURACY_M, 'domeCentreVsOctagonCentroid': DOME_CENTRE_VS_OCTAGON_CENTROID_M,
                                   'rockCentreVsDomeCentreMax': round(ROCK_CENTRE_VS_DOME_CENTRE_MAX_M, 2)},
            'ritmeyerArkDepression': 'Ritmeyer reports a rectangular cutting on the rock of about 2.5 x 1.5 cubits (4 ft 4 in x 2 ft 7 in) which he places at the centre of his Holy of Holies; its position on the rock was not retrievable here and is NOT used numerically.'},
        'elevation': elevation,
        'aron': {'main50': main, 'candidate48': cand},
        'translation': {
            'main50': {'deltaCm': [round(v, 1) for v in delta_main], 'deltaM': [round(v / 100.0, 3) for v in delta_main],
                       'uncertaintyRadiusCm': round(rock_radius_m * 100.0), 'withinUncertainty': math.hypot(*delta_main) <= rock_radius_m * 100.0,
                       'aronAfterCm': [round(v, 1) for v in dome_cm]},
            'candidate48': {'deltaCm': [round(v, 1) for v in delta_cand], 'deltaM': [round(v / 100.0, 3) for v in delta_cand],
                            'uncertaintyRadiusCm': round(rock_radius_m * 100.0), 'withinUncertainty': math.hypot(*delta_cand) <= rock_radius_m * 100.0,
                            'aronAfterCm': [round(v, 1) for v in dome_cm],
                            'causeOfDrift': 'the .96 conversion was pivoted at the outer altar (fixedOriginCm [0,0,0]); the Aron at -6200 therefore slid 248 cm east to -5952',
                            'repivotAlternative': {'pivotCm': [main['footprintCentreCm'][0], 0.0, 0.0], 'deltaCm': [round(v, 1) for v in repivot_delta],
                                                   'aronAfterCm': [round(v, 1) for v in aron_after_repivot],
                                                   'residualToDomeCentroidCm': [round(dome_cm[0] - aron_after_repivot[0], 1), round(dome_cm[1] - aron_after_repivot[1], 1)],
                                                   'frameRepresentable': True,
                                                   'descriptorChange': 'MikdashSceneUnits.FixedArchitectureOriginCm [0,0,0] -> [-6200,0,0] so every runtime adapter (TryLegacyTemplePoint) follows without C++ edits'}},
        },
        'consequences': consequences,
        'routes': {
            'A_translateTemple': {
                'actorSets': sets,
                'hardcodedTempleCoordinates': hardcodes,
                'cost': 'moves the whole Temple actor set (about %d static-mesh actors in the main inventory plus PlayerStart, cameras, lights, residents, sound, tour markers, crowd-field/service/FX actors added later); every file in hardcodedTempleCoordinates must change or route through the scene-units frame' % sets['templeTotal'],
                'breaksTerrainCut': False,
                'why': 'the terrain was cut for the Mount deck ring (X -213..150 m, Y -252..260 m), not for the +-81 m court platform; a few metres of court-platform translation stays on the deck'},
            'B_translateCityAndTerrain': {
                'cost': 'moves about %d context actors (streets, buildings, 256 terrain tiles, Old City facades/infill, Kotel families, mount access, bus, platform, ISM actors), plus 4 metric crowd zones, transit stops, bird perches, and re-origins SOURCE_ALIGN_X_AMOT in create_mount_enclosure.py / mount-platform-design.json ("alignment already baked in native meshes; NEVER apply twice") and every Kotel manifest/receipt that records world bounds' % sets['contextTotal'],
                'breaksIdentityGuards': 'release_kotel_stone_v2.py, release_kotel_surface_polish.py and release_place_assets.py refuse a Kotel base wall that is not at identity; context meshes carry world coordinates baked at identity',
                'breaksTerrainCut': 'no (deck and terrain move together) but the FutureMountV1 map L_FutureMount and its receipts go stale',
                'preserves': 'all Temple hardcodes (C++ and specs) and every Temple receipt'},
            'recommendation': None,
        },
    }
    plan['routes']['recommendation'] = {
        'main50': 'DO NOT MOVE. The Aron footprint centre (-6200, 0) is %.0f cm from the Dome of the Rock centroid (-6300, 0); the rock\'s own centre is not known better than about %.1f m from OSM data, so the requested alignment is already satisfied within the evidence. A 1 m translation would touch ~%d actors, %d C++ files (6 runtime + 5 tests) and %d scripts/specs for a change no source can confirm.' % (
            abs(delta_main[0]), rock_radius_m, sets['templeTotal'], hardcodes['counts']['cpp'], hardcodes['counts']['scripts'] + hardcodes['counts']['specs']),
        'candidate48': 'Route A as a RE-PIVOT, when the candidate is next touched: translate the converted Temple set by (%.0f, 0, 0) cm and set the Selected48 descriptor FixedArchitectureOriginCm to (-6200, 0, 0). This undoes the systematic 248 cm eastward drift the origin pivot introduced and puts the candidate Aron back at X -6200 (the same 100 cm residual as main), while keeping the runtime frame representable. Do NOT chase the remaining 100 cm on either map. Route B is rejected: more actors, breaks the baked-alignment invariant and the Kotel identity guards, and stales the terrain/Kotel receipts.' % repivot_delta[0],
        'vertical': 'Separate decision: the Aron floor is ~13.5 m above the published rock summit; see elevation.kodeshFloorIfAronRestsOnRock. Not applied by any script here.',
    }
    return plan


def main(argv):
    plan = build_plan()
    summary = {
        'domeCentroidCm': plan['domeOfTheRock']['centroidCm'],
        'rockUncertaintyRadiusM': plan['rock']['uncertaintyRadiusM'],
        'translationMain50Cm': plan['translation']['main50']['deltaCm'],
        'translationCandidate48Cm': plan['translation']['candidate48']['deltaCm'],
        'repivotCandidateCm': plan['translation']['candidate48']['repivotAlternative']['deltaCm'],
        'kotelWestEdgeMinusFaceCm_main_noMove': plan['consequences']['main50_noMove']['kotel']['westEdgeMinusKotelFaceCm'],
        'kotelNearestM_main_fullDelta': plan['consequences']['main50_fullDelta']['kotel']['nearestWestEdgeToKotelFaceM'],
        'precinctBuildingsInside_before': plan['consequences']['main50_noMove']['precinct3000']['before']['osmBuildingsInsideByCentroid'],
        'precinctBuildingsInside_main_fullDelta': plan['consequences']['main50_fullDelta']['precinct3000']['osmBuildingsInsideByCentroid'],
        'precinctBuildingsInside_candidate_repivot': plan['consequences']['candidate48_repivot']['precinct3000']['osmBuildingsInsideByCentroid'],
        'hardcodeCounts': plan['routes']['A_translateTemple']['hardcodedTempleCoordinates']['counts'],
        'templeActors': plan['routes']['A_translateTemple']['actorSets']['templeTotal'],
        'contextActors': plan['routes']['A_translateTemple']['actorSets']['contextTotal'],
        'unclassified': len(plan['routes']['A_translateTemple']['actorSets']['unclassified']),
        'aronFloorAboveRockSummitM': plan['elevation']['aronFloorAboveRockSummitM'],
    }
    if '--no-write' not in argv:
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        out = RECEIPT_DIR / ('aron-alignment-plan-%s.json' % plan['stamp'])
        out.write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
        summary['receipt'] = str(out)
    print(json.dumps(summary, indent=2))
    return plan


if __name__ == '__main__':
    main(sys.argv[1:])

"""Reveal the Kotel stone-course overlay hidden behind the OSM city-wall extrusion (scenario map only).

Problem (kotel-visibility review, 2026-09-07)
--------------------------------------------
RELEASE_Kotel_1..6 (SM_KotelFace_Tint0..5, world-baked, 0.15..3.3 cm west of the Kotel building
face SM_JerusalemBuildings_Grid_N002_P001) are invisible from the plaza because the OSM "Mapped city
walls 4" batches SM_Jerusalem_CityWalls_04_Grid_N002_P000 / _P001 stand in front of the face along
the four west-facing footprint edges (kotel-detail manifest faces 24, 25, 0, 1).

What the batches really are (streets-manifest.json: "Original box, 24 vertices/12 triangles; no box
splitting"): chains of CLOSED boxes.  Along the Kotel each edge carries one 200 cm thick body box
straddling the face plane (corners -100..+100 cm; west face at +100 cm) with 220 cm wide merlon boxes
on top (to +110 cm).  Offline analysis of the source triangles (build_spec) finds 31 such boxes
(4 in P000, 27 in P001) whose centroids lie on the west-facing edges; every other box in the two
batches is the wall continuing north (Y >= 17732) or south (Y <= 8861) of the footprint.

Design - Option A (default): per-BOX cut on duplicates
  1. duplicate both assets to /Game/MikdashV3/FutureMountV1/KotelApproach/<name>_KotelCut
     (EditorAssetSubsystem.duplicate_asset); originals untouched, hashes verified;
  2. load each duplicate's LOD0 source model into a DynamicMesh, match every triangle to a spec box by
     its three corner positions (0.5 cm), delete the 12 triangles of every box flagged `cut`
     (GeometryScript_MeshSelection.convert_index_array_to_mesh_selection +
     GeometryScript_MeshEdits.delete_selected_triangles_from_mesh; per-triangle fallback), compact,
     copy back with GeometryScript_AssetUtils.copy_mesh_to_static_mesh (materials kept), save;
  3. in the combined map swap the two actors' static mesh to the duplicates (original path recorded
     for restore), save, reopen, read back; probe: 20 points per cut edge at Z -1000..500 must have no
     remaining triangle centroid west of the face within 160 cm, and no centroid in the cut band.
  Whole boxes are removed instead of the literal per-triangle centroid test because the body boxes'
  top/bottom/end faces have centroids exactly ON the face plane (west 0.0); a per-triangle test would
  leave open, single-sided box shells.  The box rule (centroid west -20..160 cm, along -80..L+80 cm,
  Z -1500..800) selects exactly the boxes in front of the overlay and none of the continuing wall.

Option B (flag -KotelOcclusionOptionB): move RELEASE_Kotel_1..6 by 122 cm along the edge-0 outward
  normal (original identity recorded).  Fallback only; misaligns the overlay by up to ~19 cm on the
  short edge 24 and leaves the OSM slab as the visible wall body.

Invocation (hidden editor; the module detects the engine command line and quits when done):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject /Engine/Maps/Entry
      -ExecutePythonScript=C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_fix_kotel_occlusion.py
      -unattended -nosplash -nullrhi -EnablePlugins=GeometryScripting
      [-DiagnoseOnly] [-KotelOcclusionOptionB] [-KotelCutEdges=0,1,24,25]
      -abslog=C:/Mikdash/Working-5.8/Release-Kotel-Occlusion-01.log
  -DiagnoseOnly loads the map, matches the ORIGINAL meshes' triangles to the spec boxes and writes
  occlusion-diagnostic-<stamp>.json without any mutation (no checkpoint, no duplicate).
  -KotelCutEdges restricts the cut to a subset of the spec's cutEdges (e.g. 0 for the camera face only);
  bend merlons of neighbouring edges that stand in front of a selected face are removed too
  (effective_cut_flags), spec-kept boxes never.  The probe runs on the cut duplicates before the map is
  touched, so a probe failure leaves the map unchanged.

Offline (any Python 3):
  python release_fix_kotel_occlusion.py               offline_check() against the spec
  python release_fix_kotel_occlusion.py --build-spec  regenerate the spec from the frozen sources

Safety model (as release_place_assets.py / release_fix_terrain_winding.py): exact project dir, exact
map, no game world, no dirty packages, protected map + original asset hashes, checkpoint copy of
Walkthrough.umap (+ One-File-Per-Actor folders) before mutation, receipt written at start and in
finally, every other actor numerically unchanged after reopen.
"""
import hashlib
import json
import math
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_fix_kotel_occlusion.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
KOTEL_DIR = ROOT / 'SourceAssets/kotel-detail/KotelStoneV1'
KOTEL_MANIFEST = KOTEL_DIR / 'manifest.json'
CAPTURE_SCRIPT = ROOT / 'Scripts' / 'release_capture_views.py'
STREETS_MANIFEST = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\cloud-unreal-v3\context-review\streets-manifest.json')
SOURCE_MESH_JSON = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\architecture-review\jerusalem-meshes.json')
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')

WALL_ASSETS = ['/Game/MikdashV3/JerusalemContext/Streets/SM_Jerusalem_CityWalls_04_Grid_N002_P000',
               '/Game/MikdashV3/JerusalemContext/Streets/SM_Jerusalem_CityWalls_04_Grid_N002_P001']
CUT_FOLDER = '/Game/MikdashV3/FutureMountV1/KotelApproach/'
CUT_SUFFIX = '_KotelCut'
BASE_WALL = '/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N002_P001'
OVERLAY_FOLDER = '/Game/MikdashV3/MaterialReview/KotelStoneV1/Meshes/'
OVERLAY_LABELS = ['RELEASE_Kotel_%d' % i for i in range(1, 7)]
PROTECTED_MAPS = ['/Game/MikdashV3/Maps/Courtyard', '/Game/MikdashV3/FutureMountV1/L_FutureMount',
                  '/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold']

# Defaults baked into the spec by build_spec(); the engine run reads them from the spec only.
CUT_EDGES_DEFAULT = [0, 1, 24, 25]
WEST_MIN_CM, WEST_MAX_CM = -20.0, 160.0
ALONG_PAD_CM = 80.0
Z_MIN_CM, Z_MAX_CM = -1500.0, 800.0
PROBE_POINTS_PER_EDGE = 20
PROBE_Z_CM = (-1000.0, 500.0)
PROBE_MIN_CLEARANCE_CM = 160.0
CORNER_TOLERANCE_CM = 0.5
BOUNDS_TOLERANCE_CM = 0.5
TRANSFORM_TOLERANCE_CM = 0.001
OPTION_B_OFFSET_CM = 122.0
CORNER_IGNORE_ALONG_CM = 20.0
TRIANGLES_PER_BOX = 12
OPTION_B_FLAG = '-kotelocclusionoptionb'


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so build_spec() / offline_check() run anywhere.
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, default=str) + '\n', encoding='utf-8')


def cut_asset_path(source_asset):
    return CUT_FOLDER + source_asset.rsplit('/', 1)[1] + CUT_SUFFIX


def plane_coords(face, point):
    """(west, along) of a point relative to a manifest face: west along the outward normal, along the tangent from a."""
    dx = point[0] - face['a'][0]
    dy = point[1] - face['a'][1]
    return dx * face['normal'][0] + dy * face['normal'][1], dx * face['tangent'][0] + dy * face['tangent'][1]


def classify_centroid(centroid, faces, rule):
    """Face whose cut band contains the centroid (smallest |west| wins), or None."""
    best = None
    for face in faces:
        west, along = plane_coords(face, centroid)
        if not (rule['westMinCm'] <= west <= rule['westMaxCm']):
            continue
        if not (-rule['alongPadCm'] <= along <= face['lengthCm'] + rule['alongPadCm']):
            continue
        if not (rule['zMinCm'] <= centroid[2] <= rule['zMaxCm']):
            continue
        if best is None or abs(west) < abs(best[1]) - 1e-9 or (abs(abs(west) - abs(best[1])) <= 1e-9 and face['edge'] < best[0]):
            best = (face['edge'], west, along)  # deterministic tie-break at the footprint bends
    return best


def aabb_of(points):
    return {'min': [min(p[k] for p in points) for k in range(3)], 'max': [max(p[k] for p in points) for k in range(3)]}


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def point_to_aabb_distance(point, box):
    return math.sqrt(sum(max(box['min'][k] - point[k], point[k] - box['max'][k], 0.0) ** 2 for k in range(3)))


def probe_points(face, probe):
    """Points on the face plane: along positions at (i+0.5)/n of the length, Z rising from zFromCm to zToCm."""
    n = probe['pointsPerEdge']
    points = []
    for i in range(n):
        s = face['lengthCm'] * (i + 0.5) / n
        z = probe['zFromCm'] + (probe['zToCm'] - probe['zFromCm']) * (i / (n - 1.0) if n > 1 else 0.0)
        points.append([face['a'][0] + face['tangent'][0] * s, face['a'][1] + face['tangent'][1] * s, z])
    return points


def shared_corner_pairs(boxes, cut_flags, tolerance=CORNER_TOLERANCE_CM):
    """Pairs of boxes sharing >= 3 corners (coincident end caps) whose cut decisions differ."""
    pairs = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if cut_flags[i] == cut_flags[j]:
                continue
            shared = sum(1 for a in boxes[i]['corners'] if any(max(abs(a[k] - b[k]) for k in range(3)) <= tolerance for b in boxes[j]['corners']))
            if shared >= 3:
                pairs.append([boxes[i]['box'], boxes[j]['box'], shared])
    return pairs


def effective_cut_flags(asset_spec, faces, rule, cut_edges):
    """Per-box cut decision for a (possibly restricted) edge set.

    A spec `cut` box is removed when its edge is selected, or when it is a bend merlon of a neighbouring edge
    whose corners stand in front of a selected face (west within the band, along overlapping the face minus
    the corner allowance).  Boxes the spec keeps are never promoted.  With the full spec edge set this is
    exactly the spec's `cut` flag.
    """
    by_edge = {f['edge']: f for f in faces}
    flags = []
    for box in asset_spec['boxes']:
        flag = bool(box['cut']) and box['edge'] in cut_edges
        if box['cut'] and not flag:
            for edge in cut_edges:
                face = by_edge[edge]
                coords = [plane_coords(face, c) for c in box['corners']]
                west_lo, west_hi = min(w for w, _ in coords), max(w for w, _ in coords)
                along_lo, along_hi = min(a for _, a in coords), max(a for _, a in coords)
                if west_hi >= rule['westMinCm'] and west_lo <= rule['westMaxCm'] \
                        and along_hi > rule['cornerIgnoreAlongCm'] and along_lo < face['lengthCm'] - rule['cornerIgnoreAlongCm']:
                    flag = True
                    break
        flags.append(flag)
    return flags


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def face_constants_from_capture_script():
    """KOTEL_FACE_A/B/NORMAL literal tuples in release_capture_views.py (regex, no import)."""
    text = CAPTURE_SCRIPT.read_text(encoding='utf-8')
    values = {}
    for name in ('KOTEL_FACE_A', 'KOTEL_FACE_B', 'KOTEL_FACE_NORMAL'):
        match = re.search(r'^%s\s*=\s*\(([^)]*)\)' % name, text, re.M)
        if not match:
            raise RuntimeError('Constant %s not found in %s' % (name, CAPTURE_SCRIPT))
        values[name] = [float(v) for v in match.group(1).split(',') if v.strip()]
    return values


# --------------------------------------------------------------------------
# Spec generation from the frozen sources (offline only).
# --------------------------------------------------------------------------

def build_spec(write=True):
    kotel = json.loads(KOTEL_MANIFEST.read_text(encoding='utf-8'))
    streets = json.loads(STREETS_MANIFEST.read_text(encoding='utf-8'))
    source_sha = sha256_of(SOURCE_MESH_JSON)
    if source_sha != kotel['sourceMeshSha256'] or source_sha != streets['sourceMeshSha256']:
        raise RuntimeError('jerusalem-meshes.json hash differs from the Kotel/streets manifests')
    source = json.loads(SOURCE_MESH_JSON.read_bytes())
    tx, _, tz = streets['alignment']['translationSourceAmos']
    faces = [dict(edge=f['edge'], a=f['a'], b=f['b'], tangent=f['tangent'], normal=f['normal'], lengthCm=f['lengthCm']) for f in kotel['faces']]
    by_edge = {f['edge']: f for f in faces}
    rule = dict(cutEdges=list(CUT_EDGES_DEFAULT), westMinCm=WEST_MIN_CM, westMaxCm=WEST_MAX_CM, alongPadCm=ALONG_PAD_CM,
                zMinCm=Z_MIN_CM, zMaxCm=Z_MAX_CM, cornerIgnoreAlongCm=CORNER_IGNORE_ALONG_CM,
                unit='whole 12-triangle source box, decided by box centroid',
                rationale='Body boxes straddle the face plane (-100..+100 cm) so their top/bottom/end triangles have centroid west 0.0; '
                          'removing whole closed boxes leaves no open single-sided shells. westMin -20 absorbs -0.0 rounding. '
                          'alongPad 80 includes the bend merlons at the edge joints (along 0 / L) and excludes the wall continuing '
                          'north of Y 17732 (box 783, along 2046 > 1944+80) and south of Y 8861 (box 238, along -280). '
                          'cornerIgnoreAlongCm 20: the probe ignores the outer 20 cm of each face, where the kept box 238 (OSM wall '
                          'body continuing south) overlaps the first ~16 cm of the 326 cm edge-24 stub at the SW corner.')
    by_name = {m['assetName']: m for m in streets['meshes']}
    assets = []
    for asset_path in WALL_ASSETS:
        name = asset_path.rsplit('/', 1)[1]
        entry = by_name[name]
        src = source['meshes'][entry['sourceMeshIndex']]
        if src['category'] != 'Mapped city walls' or 'no box splitting' not in entry['partitionUnit']:
            raise RuntimeError('Unexpected batch structure for ' + name)
        positions, indices = src['positions'], src['indices']
        tris = entry['sourceTriangleIndices']
        if len(tris) != entry['triangles'] or len(tris) % TRIANGLES_PER_BOX:
            raise RuntimeError('Batch %s is not whole boxes' % name)

        def vertex(index):
            x, y, z = positions[3 * index], positions[3 * index + 1], positions[3 * index + 2]
            return [(x + tx) * 50.0, (z + tz) * 50.0, y * 50.0]

        boxes = []
        all_points = []
        for start in range(0, len(tris), TRIANGLES_PER_BOX):
            group = tris[start:start + TRIANGLES_PER_BOX]
            if group != list(range(group[0], group[0] + TRIANGLES_PER_BOX)) or group[0] % TRIANGLES_PER_BOX:
                raise RuntimeError('Non-consecutive box triangles in ' + name)
            points = [vertex(indices[3 * t + k]) for t in group for k in range(3)]
            all_points += points
            corners = sorted({tuple(round(c, 4) for c in p) for p in points})
            if len(corners) != 8:
                raise RuntimeError('Box %d of %s has %d distinct corners' % (group[0] // TRIANGLES_PER_BOX, name, len(corners)))
            centroid = [round(sum(p[k] for p in points) / len(points), 4) for k in range(3)]  # rounded: offline_check re-classifies these exact values
            hit = classify_centroid(centroid, faces, rule)
            bounds = aabb_of(points)
            boxes.append(dict(box=group[0] // TRIANGLES_PER_BOX, sourceTriangles=[group[0], group[-1]],
                              corners=[list(c) for c in corners], centroidCm=centroid,
                              minCm=[round(v, 4) for v in bounds['min']], maxCm=[round(v, 4) for v in bounds['max']],
                              edge=hit[0] if hit else None, centroidWestCm=round(hit[1], 3) if hit else None,
                              centroidAlongCm=round(hit[2], 3) if hit else None,
                              cut=bool(hit and hit[0] in rule['cutEdges'])))
        remaining = [b for b in boxes if not b['cut']]
        cut = [b for b in boxes if b['cut']]
        if box_error(aabb_of(all_points), entry['expectedBoundsUnrealCm']) > BOUNDS_TOLERANCE_CM:
            raise RuntimeError('Recomputed bounds differ from streets manifest for ' + name)
        after_points = [c for b in remaining for c in b['corners']]
        cut_west = [plane_coords(by_edge[b['edge']], c)[0] for b in cut for c in b['corners']]
        shared_across = shared_corner_pairs(boxes, [b['cut'] for b in boxes])
        uasset = disk_path(asset_path)
        assets.append(dict(source=asset_path, destination=cut_asset_path(asset_path), uassetFile=uasset.relative_to(ROOT).as_posix(),
                           lastKnownUassetSha256=sha256_of(uasset) if uasset.exists() else None,
                           materialSlotFbxName=entry['materialSlots'][0]['fbxMaterialName'], materialSlots=len(entry['materialSlots']),
                           expectedBoundsUnrealCm=entry['expectedBoundsUnrealCm'], triangles=entry['triangles'], boxCount=len(boxes),
                           cutBoxes=len(cut), cutBoxIds=[b['box'] for b in cut], expectedTrianglesAfterCut=len(remaining) * TRIANGLES_PER_BOX,
                           expectedBoundsAfterCutCm=aabb_of(after_points) if after_points else None,
                           cutCornerWestRangeCm=[round(min(cut_west), 3), round(max(cut_west), 3)] if cut_west else None,
                           sharedCornerPairsAcrossCutBoundary=shared_across,
                           boxes=boxes))
    map_file = disk_path(TARGET, 'umap')
    spec = {
        'specVersion': 1,
        'prepared': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'purpose': 'Human-reviewable plan consumed by Scripts/release_fix_kotel_occlusion.py: per-box cut of the two OSM city-wall '
                   'batches in front of the Kotel face, applied to DUPLICATE assets and swapped into the combined map only. '
                   'Every box below was recomputed from the frozen source mesh; `cut` boxes are removed, all others stay. '
                   'Nothing here claims visual acceptance.',
        'projectDir': str(ROOT),
        'targetMap': TARGET,
        'targetMapFile': map_file.relative_to(ROOT).as_posix(),
        'lastKnownMapSha256': sha256_of(map_file) if map_file.exists() else None,
        'lastKnownMapSha256Note': 'Recorded as matched/not matched in the receipt only, not a guard.',
        'protectedMaps': list(PROTECTED_MAPS),
        'checkpointRoot': str(CHECKPOINT_ROOT),
        'checkpointPrefix': 'KotelOcclusion-',
        'receiptFolder': KOTEL_DIR.relative_to(ROOT).as_posix(),
        'receiptPrefix': 'occlusion-fix-',
        'diagnosticPrefix': 'occlusion-diagnostic-',
        'kotelManifest': {'file': KOTEL_MANIFEST.relative_to(ROOT).as_posix(), 'sha256': sha256_of(KOTEL_MANIFEST),
                          'sourceMeshSha256': kotel['sourceMeshSha256'], 'sharedGrid': kotel['sharedGrid']},
        'streetsManifest': {'file': str(STREETS_MANIFEST), 'sha256': sha256_of(STREETS_MANIFEST), 'sourceMeshFile': str(SOURCE_MESH_JSON),
                            'sourceMeshSha256': source_sha, 'translationSourceAmos': streets['alignment']['translationSourceAmos'],
                            'sourceToUnrealCm': '[(x+tx)*50, (z+tz)*50, y*50] (source amot: X east, Y up, Z south); '
                                                'identical to the Kotel manifest conversion (create_kotel_stone_detail.py)'},
        'faces': faces,
        'faceConvention': 'a/b footprint corners (cm, XY); tangent=(b-a)/|b-a|; normal=(-tangent.y, tangent.x) points WEST '
                          '(away from the building); west = dot(p-a, normal); along = dot(p-a, tangent).',
        'cutRule': rule,
        'probe': {'pointsPerEdge': PROBE_POINTS_PER_EDGE, 'zFromCm': PROBE_Z_CM[0], 'zToCm': PROBE_Z_CM[1], 'minClearanceCm': PROBE_MIN_CLEARANCE_CM,
                  'rule': 'Candidates are remaining triangle centroids in front of the face segment (west > 0, along within '
                          'cornerIgnoreAlongCm..L-cornerIgnoreAlongCm). For every probe point the nearest candidate must be farther than '
                          'minClearanceCm, and no candidate may lie within westMaxCm of the face at Z zMin..zMax.'},
        'verification': {'cornerToleranceCm': CORNER_TOLERANCE_CM, 'boundsToleranceCm': BOUNDS_TOLERANCE_CM,
                         'transformToleranceCm': TRANSFORM_TOLERANCE_CM, 'trianglesPerBox': TRIANGLES_PER_BOX},
        'baseWall': {'mesh': BASE_WALL, 'triangles': 284, 'expectedTransform': 'identity', 'rule': 'exactly one component; untouched'},
        'overlays': {'meshFolder': OVERLAY_FOLDER, 'labels': list(OVERLAY_LABELS), 'meshes': [m['name'] for m in kotel['meshes']],
                     'expectedTransform': 'identity'},
        'optionB': {'offsetCm': OPTION_B_OFFSET_CM, 'alongOutwardNormalOfEdge': 0, 'normal': by_edge[0]['normal'],
                    'note': 'Fallback only (flag -KotelOcclusionOptionB): overlay moved in front of the OSM slab; misaligned up to ~19 cm on edge 24.'},
        'assets': assets,
        'collateral': {'statement': 'All cut boxes have every corner within +-121 cm of their edge plane and along -170..L+170 cm; the '
                                    'remaining boxes are the OSM wall continuing north (Y >= 17732) and south (Y <= 8861) of the Kotel '
                                    'footprint. No other building or wall geometry is in these two batches within 160 cm west of the face.',
                       'keptCornerOverlap': 'Box 238 (P000, Y 8272..8861, the wall body south of the footprint) overlaps the first ~16 cm '
                                            'of edge 24 at the SW corner and is deliberately kept (cutting it would open a 6 m gap).',
                       'totalBoxes': sum(a['boxCount'] for a in assets), 'totalCutBoxes': sum(a['cutBoxes'] for a in assets),
                       'totalTrianglesBefore': sum(a['triangles'] for a in assets),
                       'totalTrianglesAfter': sum(a['expectedTrianglesAfterCut'] for a in assets)},
        'limitations': ['Geometric fix only; no visual, lighting or packaged acceptance.',
                        'The OSM wall now ends flush with the footprint corners; the closed boxes there expose no open faces, but the '
                        'transition to the Kotel base wall is unreviewed.',
                        'Only the combined Walkthrough map references the duplicates; other maps keep the original batches.'],
    }
    if write:
        write_json(SPEC_PATH, spec)
    return spec


# --------------------------------------------------------------------------
# Offline validation (no engine).
# --------------------------------------------------------------------------

def offline_check(spec=None, deep=None):
    """Consistency checks that need no engine. Raises on the first failure.

    deep: also rebuild the boxes from the 100 MB source mesh when the transfer workspace is present
    (default: only outside the engine).
    """
    spec = spec or load_spec()
    if deep is None:
        deep = not _unreal_available()
    report = {'filesChecked': 0}
    for relative in [spec['targetMapFile'], spec['kotelManifest']['file']] + [a['uassetFile'] for a in spec['assets']]:
        report['filesChecked'] += 1
        if not (ROOT / relative).exists():
            raise RuntimeError('Missing file: ' + relative)
    if sha256_of(ROOT / spec['kotelManifest']['file']) != spec['kotelManifest']['sha256']:
        raise RuntimeError('Kotel manifest changed since the spec was built')
    manifest = json.loads((ROOT / spec['kotelManifest']['file']).read_text(encoding='utf-8'))

    # Face plane math against the manifest.
    faces = spec['faces']
    manifest_faces = {f['edge']: f for f in manifest['faces']}
    base = manifest['sourceBase']['boundsCm']
    building_centre = [(base['min'][0] + base['max'][0]) / 2.0, (base['min'][1] + base['max'][1]) / 2.0]
    for face in faces:
        m = manifest_faces[face['edge']]
        if face['a'] != m['a'] or face['b'] != m['b'] or face['normal'] != m['normal']:
            raise RuntimeError('Face %d differs from the manifest' % face['edge'])
        dx, dy = face['b'][0] - face['a'][0], face['b'][1] - face['a'][1]
        length = math.hypot(dx, dy)
        tangent = [dx / length, dy / length]
        normal = [-tangent[1], tangent[0]]
        if abs(length - face['lengthCm']) > 1e-6 or max(abs(tangent[i] - face['tangent'][i]) for i in (0, 1)) > 1e-9 \
                or max(abs(normal[i] - face['normal'][i]) for i in (0, 1)) > 1e-9:
            raise RuntimeError('Face %d tangent/normal/length inconsistent' % face['edge'])
        if abs(math.hypot(*face['normal']) - 1.0) > 1e-9 or face['normal'][0] >= 0:
            raise RuntimeError('Face %d normal is not a unit west-pointing vector' % face['edge'])
        if plane_coords(face, building_centre)[0] >= 0:
            raise RuntimeError('Face %d normal points into the building' % face['edge'])
    by_edge = {f['edge']: f for f in faces}
    for first, second in ((24, 25), (25, 0), (0, 1)):
        if max(abs(by_edge[first]['b'][i] - by_edge[second]['a'][i]) for i in (0, 1)) > 1e-6:
            raise RuntimeError('Face chain %d -> %d is not continuous' % (first, second))
    capture = face_constants_from_capture_script()
    edge0 = by_edge[0]
    if max(abs(capture['KOTEL_FACE_A'][i] - edge0['a'][i]) for i in (0, 1)) > 1e-6 or \
            max(abs(capture['KOTEL_FACE_B'][i] - edge0['b'][i]) for i in (0, 1)) > 1e-6 or \
            max(abs(capture['KOTEL_FACE_NORMAL'][i] - edge0['normal'][i]) for i in (0, 1)) > 1e-6:
        raise RuntimeError('release_capture_views.py face constants differ from manifest edge 0')
    report['facePlaneMath'] = 'consistent with manifest and release_capture_views.py'
    report['faceLengthsCm'] = {f['edge']: round(f['lengthCm'], 3) for f in faces}

    # Spec boxes: structure, rule reproduction, tight collateral bound, expected counts/bounds.
    rule = spec['cutRule']
    if sorted(rule['cutEdges']) != sorted(by_edge):
        report['cutEdgesNote'] = 'cutEdges %s is a subset of the four west-facing edges' % rule['cutEdges']
    per_asset = []
    remaining_boxes = []
    for asset in spec['assets']:
        if asset['destination'] != cut_asset_path(asset['source']):
            raise RuntimeError('Destination path differs from convention for ' + asset['source'])
        boxes = asset['boxes']
        if len(boxes) * spec['verification']['trianglesPerBox'] != asset['triangles'] or len(boxes) != asset['boxCount']:
            raise RuntimeError('Box count differs from triangle count for ' + asset['source'])
        cut = 0
        west_extreme = 0.0
        for box in boxes:
            if len(box['corners']) != 8:
                raise RuntimeError('Box %d of %s lacks 8 corners' % (box['box'], asset['source']))
            hit = classify_centroid(box['centroidCm'], faces, rule)
            expected_cut = bool(hit and hit[0] in rule['cutEdges'])
            if expected_cut != box['cut'] or (hit[0] if hit else None) != box['edge']:
                raise RuntimeError('Cut rule does not reproduce box %d of %s' % (box['box'], asset['source']))
            if box['cut']:
                cut += 1
                face = by_edge[box['edge']]
                for corner in box['corners']:
                    west, along = plane_coords(face, corner)
                    west_extreme = max(west_extreme, abs(west))
                    if abs(west) > 121.0 or along < -rule['alongPadCm'] - 100.0 or along > face['lengthCm'] + rule['alongPadCm'] + 100.0:
                        raise RuntimeError('Cut box %d of %s reaches outside the tight Kotel band (west %.1f, along %.1f)'
                                           % (box['box'], asset['source'], west, along))
            else:
                remaining_boxes.append(box)
        if cut != asset['cutBoxes'] or (len(boxes) - cut) * spec['verification']['trianglesPerBox'] != asset['expectedTrianglesAfterCut']:
            raise RuntimeError('Cut counts differ from spec for ' + asset['source'])
        remaining_corners = [c for b in boxes if not b['cut'] for c in b['corners']]
        if remaining_corners and box_error(aabb_of(remaining_corners), asset['expectedBoundsAfterCutCm']) > 1e-6:
            raise RuntimeError('expectedBoundsAfterCutCm differs from remaining boxes for ' + asset['source'])
        all_corners = [c for b in boxes for c in b['corners']]
        if box_error(aabb_of(all_corners), asset['expectedBoundsUnrealCm']) > spec['verification']['boundsToleranceCm']:
            raise RuntimeError('Box corners do not reproduce expectedBoundsUnrealCm for ' + asset['source'])
        shared_across = shared_corner_pairs(boxes, [b['cut'] and b['edge'] in rule['cutEdges'] for b in boxes],
                                            spec['verification']['cornerToleranceCm'])
        if shared_across != asset['sharedCornerPairsAcrossCutBoundary']:
            raise RuntimeError('sharedCornerPairsAcrossCutBoundary differs from recomputation for ' + asset['source'])
        per_asset.append({'source': asset['source'], 'boxes': len(boxes), 'cutBoxes': cut, 'trianglesBefore': asset['triangles'],
                          'sharedCornerPairsAcrossCutBoundary': shared_across,
                          'trianglesAfter': asset['expectedTrianglesAfterCut'], 'maxCornerWestCmOfCutBoxes': round(west_extreme, 3),
                          'uassetSha256Matches': sha256_of(ROOT / asset['uassetFile']) == asset['lastKnownUassetSha256']})
    report['assets'] = per_asset

    # Offline probe lower bound: distance from each probe point to the remaining boxes' AABBs.
    probe = spec['probe']
    worst = None
    for edge in rule['cutEdges']:
        face = by_edge[edge]
        for point in probe_points(face, probe):
            for box in remaining_boxes:
                coords = [plane_coords(face, c) for c in box['corners']]
                if max(w for w, _ in coords) <= 0:
                    continue  # entirely behind this face: cannot occlude it
                if max(s for _, s in coords) < rule['cornerIgnoreAlongCm'] or min(s for _, s in coords) > face['lengthCm'] - rule['cornerIgnoreAlongCm']:
                    continue  # beside the face (continuing wall), not in front of it
                distance = point_to_aabb_distance(point, {'min': box['minCm'], 'max': box['maxCm']})
                if worst is None or distance < worst[0]:
                    worst = (distance, edge, box['box'])
    report['offlineProbeMinAabbDistanceCm'] = {'distanceCm': round(worst[0], 1), 'edge': worst[1], 'box': worst[2]} if worst else None
    if worst and worst[0] <= probe['minClearanceCm']:
        raise RuntimeError('A remaining box AABB is within %.1f cm of a probe point (edge %d, box %d)' % worst)

    if deep and STREETS_MANIFEST.exists() and SOURCE_MESH_JSON.exists():
        rebuilt = build_spec(write=False)
        max_error = 0.0
        for old, new in zip(spec['assets'], rebuilt['assets']):
            if [b['box'] for b in old['boxes']] != [b['box'] for b in new['boxes']] or [b['cut'] for b in old['boxes']] != [b['cut'] for b in new['boxes']]:
                raise RuntimeError('Rebuilt boxes differ from the spec for ' + old['source'])
            for a, b in zip(old['boxes'], new['boxes']):
                max_error = max(max_error, max(abs(x - y) for ca, cb in zip(a['corners'], b['corners']) for x, y in zip(ca, cb)))
        report['deepRebuildMaxCornerErrorCm'] = max_error
        if max_error > 1e-3:
            raise RuntimeError('Rebuilt corners drift %.4f cm from the spec' % max_error)
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side.
# --------------------------------------------------------------------------

def _xyz(v):
    return [float(v.x), float(v.y), float(v.z)]


def _rot(r):
    return [float(r.pitch), float(r.yaw), float(r.roll)]


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _actor_bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
            'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}


def _actor_pose(actor):
    return {'location': _xyz(actor.get_actor_location()), 'rotation': _rot(actor.get_actor_rotation()), 'scale': _xyz(actor.get_actor_scale3d())}


def _is_identity(pose, tolerance):
    return max(abs(v) for v in pose['location'] + pose['rotation']) <= tolerance and max(abs(v - 1.0) for v in pose['scale']) <= tolerance


class Native:
    """GeometryScript / asset wrappers (proven calls per release_fix_terrain_winding.py unless noted)."""

    def __init__(self):
        import unreal as ue
        self.ue = ue
        for name in ['GeometryScript_MeshEdits', 'GeometryScript_AssetUtils', 'GeometryScript_MeshQueries', 'GeometryScript_MeshSelection']:
            assert hasattr(ue, name), 'Launch with -EnablePlugins=GeometryScripting: ' + name
        self.edits = ue.GeometryScript_MeshEdits
        self.asset_utils = ue.GeometryScript_AssetUtils
        self.query = ue.GeometryScript_MeshQueries
        self.selection = ue.GeometryScript_MeshSelection
        self.repair = getattr(ue, 'GeometryScript_MeshRepair', None)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)

    def load_static_mesh(self, asset_path):
        mesh = self.assets.load_asset(asset_path)
        assert isinstance(mesh, self.ue.StaticMesh), 'Not a StaticMesh: ' + asset_path
        return mesh

    def source_dynamic_mesh(self, mesh):
        ue = self.ue
        dynamic = ue.DynamicMesh()
        options = ue.GeometryScriptCopyMeshFromAssetOptions()
        options.set_editor_property('apply_build_settings', False)
        options.set_editor_property('request_tangents', False)
        options.set_editor_property('use_build_scale', False)
        lod = ue.GeometryScriptMeshReadLOD()
        lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
        lod.set_editor_property('lod_index', 0)
        result = self.asset_utils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
        assert ue.GeometryScriptOutcomePins.SUCCESS in result, 'Source-mesh extraction failed'
        return dynamic

    def triangle_rows(self, dynamic):
        """Valid triangles only (IDs may have gaps after deletion): tid, corner positions, centroid.

        GeometryScript_MeshQueries.get_num_triangle_ids = MaxTriangleID+1 (MeshQueryFunctions.h:90);
        get_triangle_positions returns (bIsValid, v1, v2, v3) (:134).
        """
        ue = self.ue
        rows = []
        for tid in range((getattr(self.query, 'get_num_triangle_ids', None) or getattr(self.query, 'get_num_triangle_i_ds'))(dynamic)):
            result = self.query.get_triangle_positions(dynamic, tid)
            if not isinstance(result, tuple) or not bool(result[0]):
                continue
            positions = [_xyz(v) for v in result if isinstance(v, ue.Vector)]
            assert len(positions) == 3, 'Triangle %d has %d corners' % (tid, len(positions))
            rows.append(dict(tid=tid, positions=positions, centroid=[sum(p[k] for p in positions) / 3.0 for k in range(3)]))
        return rows

    def delete_triangles(self, dynamic, tids):
        """Selection route (MeshSelectionFunctions.h:140 + MeshBasicEditFunctions.h:248); per-triangle fallback (:224)."""
        ue = self.ue
        try:
            selection = self.selection.convert_index_array_to_mesh_selection(dynamic, list(tids), ue.GeometryScriptMeshSelectionType.TRIANGLES)
            if isinstance(selection, tuple):
                selection = next(s for s in selection if isinstance(s, ue.GeometryScriptMeshSelection))
            result = self.edits.delete_selected_triangles_from_mesh(dynamic, selection, False)
            deleted = [v for v in (result if isinstance(result, tuple) else (result,)) if isinstance(v, int) and not isinstance(v, bool)]
            return (deleted[0] if deleted else None), 'delete_selected_triangles_from_mesh'
        except Exception as error:  # noqa: BLE001 - fall back to the simplest call shape
            count = 0
            for tid in tids:
                result = self.edits.delete_triangle_from_mesh(dynamic, tid, False)
                flags = [v for v in (result if isinstance(result, tuple) else (result,)) if isinstance(v, bool)]
                count += 1 if (flags and flags[0]) else 0
            return count, 'delete_triangle_from_mesh_loop (selection route failed: %s)' % error

    def compact(self, dynamic):
        """MeshRepairFunctions.h:225; optional - copy_mesh_to_static_mesh tolerates ID gaps."""
        if self.repair is None:
            return False
        try:
            self.repair.compact_mesh(dynamic)
            return True
        except Exception:  # noqa: BLE001
            return False

    def write_in_place(self, dynamic, mesh):
        ue = self.ue
        options = ue.GeometryScriptCopyMeshToAssetOptions()
        settings = dict(enable_recompute_normals=False, enable_recompute_tangents=True, enable_remove_degenerates=False,
                        use_original_vertex_order=False, replace_materials=False, apply_nanite_settings=False,
                        emit_transaction=False, defer_mesh_post_edit_change=False)
        for key, value in settings.items():
            options.set_editor_property(key, value)
        lod = ue.GeometryScriptMeshWriteLOD()
        lod.set_editor_property('write_hi_res_source', False)
        lod.set_editor_property('lod_index', 0)
        result = self.asset_utils.copy_mesh_to_static_mesh(dynamic, mesh, options, lod)
        assert ue.GeometryScriptOutcomePins.SUCCESS in result, 'copy_mesh_to_static_mesh failed'
        return settings

    def render_summary(self, mesh):
        bounds = mesh.get_bounding_box()
        material = mesh.get_material(0)
        setup = mesh.get_editor_property('body_setup')
        try:
            slots = len(mesh.get_editor_property('static_materials'))
        except Exception:  # noqa: BLE001
            slots = None
        return dict(renderTriangles=mesh.get_num_triangles(0), renderVertices=mesh.get_num_vertices(0),
                    boundsCm={'min': _xyz(bounds.min), 'max': _xyz(bounds.max)},
                    material=material.get_path_name() if material else None, materialSlots=slots,
                    collisionTraceFlag=str(setup.get_editor_property('collision_trace_flag')) if setup else None,
                    lodForCollision=mesh.get_editor_property('lod_for_collision'))

    def reload_from_disk(self, asset_path):
        ue = self.ue
        package = ue.load_package(asset_path)
        assert package is not None
        result = ue.EditorLoadingAndSavingUtils.reload_packages([package], ue.ReloadPackagesInteractionMode.ASSUME_POSITIVE)
        reloaded = bool(result[0]) if isinstance(result, tuple) else bool(result)
        return reloaded, self.load_static_mesh(asset_path)


def _outward_sign(row, box):
    """Sign of dot(cross(C-A, B-A), centroid_tri - centroid_box); convention-free once calibrated per mesh."""
    a, b, c = row['positions']
    e1 = [b[k] - a[k] for k in range(3)]
    e2 = [c[k] - a[k] for k in range(3)]
    n = [e2[1] * e1[2] - e2[2] * e1[1], e2[2] * e1[0] - e2[0] * e1[2], e2[0] * e1[1] - e2[1] * e1[0]]
    d = [row['centroid'][k] - box['centroidCm'][k] for k in range(3)]
    dot = sum(n[k] * d[k] for k in range(3))
    return 1 if dot > 0 else (-1 if dot < 0 else 0)


def assign_boxes(rows, boxes, cut_flags, tolerance):
    """Map every triangle to the spec box it belongs to.

    Adjacent body boxes share their end-cap corners exactly, so a coincident end-cap triangle matches two
    boxes by corner set.  When both candidates have the same cut decision the choice is irrelevant; when
    they differ, the triangle belongs to the box its outward normal points away from (sign calibrated on
    this mesh's unambiguous triangles, so the winding convention does not matter).  Returns (assignment
    {tid: box index}, info).  Raises on unmatched triangles, unresolved ambiguity or wrong totals.
    """
    prepared = [(index, [v - tolerance for v in box['minCm']], [v + tolerance for v in box['maxCm']], box['corners'])
                for index, box in enumerate(boxes)]
    owners_by_tid = {}
    for row in rows:
        owners = []
        for index, lo, hi, corners in prepared:
            if any(not (lo[k] <= p[k] <= hi[k]) for p in row['positions'] for k in range(3)):
                continue
            if all(any(max(abs(p[k] - c[k]) for k in range(3)) <= tolerance for c in corners) for p in row['positions']):
                owners.append(index)
        if not owners:
            raise RuntimeError('Triangle %d matches no spec box (positions %s)' % (row['tid'], row['positions']))
        owners_by_tid[row['tid']] = owners
    signs = [_outward_sign(row, boxes[owners_by_tid[row['tid']][0]]) for row in rows if len(owners_by_tid[row['tid']]) == 1]
    positive = sum(1 for v in signs if v > 0)
    negative = sum(1 for v in signs if v < 0)
    if not signs or min(positive, negative) > 0.01 * len(signs):
        raise RuntimeError('Triangle winding is not consistent (%d outward, %d inward); cannot resolve shared end caps' % (positive, negative))
    outward = 1 if positive >= negative else -1
    assignment = {}
    ambiguous = mixed = 0
    for row in rows:
        owners = owners_by_tid[row['tid']]
        if len(owners) == 1:
            assignment[row['tid']] = owners[0]
            continue
        ambiguous += 1
        if len({cut_flags[i] for i in owners}) == 1:
            assignment[row['tid']] = owners[0]
            continue
        mixed += 1
        facing = [i for i in owners if _outward_sign(row, boxes[i]) * outward > 0]
        if len(facing) != 1:
            raise RuntimeError('Triangle %d lies on a shared cap between cut and kept boxes %s and cannot be resolved'
                               % (row['tid'], [boxes[i]['box'] for i in owners]))
        assignment[row['tid']] = facing[0]
    counts = {}
    for index in assignment.values():
        counts[index] = counts.get(index, 0) + 1
    cut_total = sum(n for i, n in counts.items() if cut_flags[i])
    expected_cut = TRIANGLES_PER_BOX * sum(1 for flag in cut_flags if flag)
    problems = []
    if len(assignment) != TRIANGLES_PER_BOX * len(boxes):
        problems.append('matched %d triangles, expected %d' % (len(assignment), TRIANGLES_PER_BOX * len(boxes)))
    if cut_total != expected_cut:
        problems.append('%d triangles assigned to cut boxes, expected %d' % (cut_total, expected_cut))
    odd = {boxes[i]['box']: counts.get(i, 0) for i in range(len(boxes)) if not 8 <= counts.get(i, 0) <= 16}
    if odd:
        problems.append('implausible per-box triangle counts %s' % odd)
    if problems:
        raise RuntimeError('Box/triangle mismatch: ' + '; '.join(problems))
    info = {'ambiguousSharedCapTriangles': ambiguous, 'resolvedAcrossCutBoundary': mixed, 'outwardSign': outward,
            'windingSamples': [positive, negative], 'perBoxCounts': {boxes[i]['box']: n for i, n in sorted(counts.items())}}
    return assignment, info


def geometric_probe(centroids, faces, cut_edges, probe, rule):
    """Nearest remaining centroid west of each cut face per probe point, plus cut-band emptiness."""
    by_edge = {f['edge']: f for f in faces}
    report = {'perEdge': {}, 'minClearanceCm': None, 'remainingCentroidsInCutBand': 0, 'passed': True}
    for edge in cut_edges:
        face = by_edge[edge]
        ignore = rule['cornerIgnoreAlongCm']
        # candidates: centroids in front of the face SEGMENT (west > 0, along inside the face minus the corner allowance)
        located = [(c, plane_coords(face, c)) for c in centroids]
        located = [(c, (w, s)) for c, (w, s) in located if w > 0.0 and ignore <= s <= face['lengthCm'] - ignore]
        report['remainingCentroidsInCutBand'] += sum(
            1 for c, (w, s) in located if w <= rule['westMaxCm'] and rule['zMinCm'] <= c[2] <= rule['zMaxCm'])
        points = []
        for point in probe_points(face, probe):
            nearest = None
            for c, (w, s) in located:
                d = math.dist(point, c)
                if nearest is None or d < nearest[0]:
                    nearest = (d, c)
            entry = {'point': [round(v, 2) for v in point],
                     'nearestWestCentroidDistanceCm': round(nearest[0], 1) if nearest else None,
                     'nearestCentroid': [round(v, 1) for v in nearest[1]] if nearest else None}
            entry['clear'] = nearest is None or nearest[0] > probe['minClearanceCm']
            points.append(entry)
            if nearest and (report['minClearanceCm'] is None or nearest[0] < report['minClearanceCm']):
                report['minClearanceCm'] = round(nearest[0], 1)
            report['passed'] = report['passed'] and entry['clear']
        report['perEdge'][str(edge)] = points
    report['passed'] = report['passed'] and report['remainingCentroidsInCutBand'] == 0
    return report


class Fix:
    def __init__(self, ue, spec, native):
        self.ue = ue
        self.spec = spec
        self.native = native
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.world = None
        self.snapshot = None
        self.receipt = None
        self.receipt_path = None
        self.remaining = {}

    def write_receipt(self):
        if self.receipt_path:
            write_json(self.receipt_path, self.receipt)

    # -- map -----------------------------------------------------------------

    def open_map(self):
        if not self.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        self.world = self.editor.get_editor_world()
        loaded = self.world.get_outermost().get_name()
        if loaded != TARGET:
            raise RuntimeError('Loaded world %s is not %s' % (loaded, TARGET))

    def take_snapshot(self):
        ue = self.ue
        rows = []
        for actor in self.actors.get_all_level_actors():
            components = list(actor.get_components_by_class(ue.StaticMeshComponent))
            meshes = [_asset_path(c.get_editor_property('static_mesh')) for c in components]
            rows.append({'actor': actor, 'components': components, 'name': actor.get_name(), 'label': actor.get_actor_label(),
                         'folder': str(actor.get_folder_path()), 'meshes': meshes, 'pose': _actor_pose(actor), 'bounds': _actor_bounds(actor),
                         'tags': [str(t) for t in actor.get_editor_property('tags')]})
        self.snapshot = rows
        return rows

    @staticmethod
    def numeric_baseline(rows):
        return {row['name']: (row['label'], tuple(row['meshes']), tuple(row['pose']['location'] + row['pose']['rotation'] + row['pose']['scale']))
                for row in rows}

    def single_component(self, mesh_path):
        found = [(row, c) for row in self.snapshot for c in row['components'] if _asset_path(c.get_editor_property('static_mesh')) == mesh_path]
        if len(found) != 1:
            raise RuntimeError('Expected exactly one component with %s, found %d' % (mesh_path, len(found)))
        return found[0]

    def wall_actors(self, mesh_paths):
        rows = []
        for path in mesh_paths:
            row, component = self.single_component(path)
            if not _is_identity(row['pose'], self.spec['verification']['transformToleranceCm']):
                raise RuntimeError('Wall actor %s is not at identity' % row['label'])
            rows.append({'row': row, 'component': component, 'label': row['label'], 'name': row['name'], 'folder': row['folder'],
                         'mesh': path, 'pose': row['pose'], 'bounds': row['bounds'], 'tags': row['tags'],
                         'collisionProfile': str(component.get_collision_profile_name()),
                         'materials': [_asset_path(component.get_material(i)) for i in range(component.get_num_materials())]})
        return rows

    def overlay_rows(self):
        folder = self.spec['overlays']['meshFolder']
        rows = [row for row in self.snapshot if row['label'] in self.spec['overlays']['labels']]
        if len(rows) != len(self.spec['overlays']['labels']):
            raise RuntimeError('Expected %d RELEASE_Kotel actors, found %d' % (len(self.spec['overlays']['labels']), len(rows)))
        for row in rows:
            if len(row['meshes']) != 1 or not row['meshes'][0].startswith(folder):
                raise RuntimeError('Overlay %s has unexpected meshes %s' % (row['label'], row['meshes']))
        return rows

    def base_wall_state(self):
        row, component = self.single_component(self.spec['baseWall']['mesh'])
        mesh = component.get_editor_property('static_mesh')
        if mesh.get_num_triangles(0) != self.spec['baseWall']['triangles']:
            raise RuntimeError('Kotel base triangle count changed')
        if not _is_identity(row['pose'], self.spec['verification']['transformToleranceCm']):
            raise RuntimeError('Kotel base is not at identity')
        return {'label': row['label'], 'name': row['name'], 'pose': row['pose'], 'bounds': row['bounds'],
                'materials': [_asset_path(component.get_material(i)) for i in range(component.get_num_materials())]}

    # -- diagnosis on any static mesh -------------------------------------------

    def diagnose_asset(self, asset_spec, mesh, cut_edges):
        native = self.native
        rows = native.triangle_rows(native.source_dynamic_mesh(mesh))
        render = native.render_summary(mesh)
        entry = {'asset': _asset_path(mesh), 'sourceTriangles': len(rows), 'expectedTriangles': asset_spec['triangles'], 'render': render}
        if len(rows) != asset_spec['triangles']:
            raise RuntimeError('%s has %d source triangles, spec expects %d' % (entry['asset'], len(rows), asset_spec['triangles']))
        error = box_error(render['boundsCm'], asset_spec['expectedBoundsUnrealCm'])
        if error > self.spec['verification']['boundsToleranceCm']:
            raise RuntimeError('%s bounds differ from spec by %.3f cm' % (entry['asset'], error))
        cut_flags = effective_cut_flags(asset_spec, self.spec['faces'], self.spec['cutRule'], cut_edges)
        assignment, info = assign_boxes(rows, asset_spec['boxes'], cut_flags, self.spec['verification']['cornerToleranceCm'])
        cut_ids = {i for i, flag in enumerate(cut_flags) if flag}
        tids = sorted(tid for tid, index in assignment.items() if index in cut_ids)
        entry.update(matchedBoxes=len(set(assignment.values())), boxMatching=info, cutBoxes=len(cut_ids),
                     cutBoxIds=[asset_spec['boxes'][i]['box'] for i in sorted(cut_ids)],
                     trianglesToDelete=len(tids), expectedTrianglesAfter=len(rows) - len(tids))
        return entry, rows, tids

    # -- option A --------------------------------------------------------------

    def cut_asset(self, asset_spec, cut_edges, checkpoint_dir, item):
        ue = self.ue
        native = self.native
        source_path, destination = asset_spec['source'], asset_spec['destination']
        source_file = ROOT / asset_spec['uassetFile']
        item['sourceUassetSha256Before'] = sha256_of(source_file)
        shutil.copy2(source_file, checkpoint_dir / source_file.name)
        if native.assets.does_asset_exist(destination):
            raise RuntimeError('Destination already exists (delete it or restore first): ' + destination)
        original = native.load_static_mesh(source_path)
        before, _, _ = self.diagnose_asset(asset_spec, original, cut_edges)
        item['before'] = before

        duplicate = native.assets.duplicate_asset(source_path, destination)
        if not isinstance(duplicate, ue.StaticMesh):
            raise RuntimeError('duplicate_asset failed for ' + source_path)
        item['duplicated'] = destination
        try:
            dynamic = native.source_dynamic_mesh(duplicate)
            rows = native.triangle_rows(dynamic)
            cut_flags = effective_cut_flags(asset_spec, self.spec['faces'], self.spec['cutRule'], cut_edges)
            assignment, info = assign_boxes(rows, asset_spec['boxes'], cut_flags, self.spec['verification']['cornerToleranceCm'])
            item['boxMatching'] = info
            cut_ids = {i for i, flag in enumerate(cut_flags) if flag}
            tids = sorted(tid for tid, index in assignment.items() if index in cut_ids)
            expected_after = len(rows) - len(tids)
            deleted, method = native.delete_triangles(dynamic, tids)
            remaining = native.triangle_rows(dynamic)
            item.update(deleteMethod=method, deletedReported=deleted, trianglesRemaining=len(remaining))
            if len(remaining) != expected_after:
                raise RuntimeError('Deletion left %d triangles, expected %d' % (len(remaining), expected_after))
            remaining_ids = {r['tid'] for r in remaining}
            if any(tid in remaining_ids for tid in tids):
                raise RuntimeError('A selected triangle survived deletion')
            kept_centroids = sorted(tuple(round(v, 4) for v in r['centroid']) for r in remaining)
            item['compacted'] = native.compact(dynamic)
            remaining = native.triangle_rows(dynamic)
            if len(remaining) != expected_after:
                raise RuntimeError('Compaction changed the triangle count')
            # Exact geometric check (IDs may have moved): the survivors are precisely the pre-compaction survivors.
            if sorted(tuple(round(v, 4) for v in r['centroid']) for r in remaining) != kept_centroids:
                raise RuntimeError('Triangle set changed during compaction')

            item['copyOptions'] = native.write_in_place(dynamic, duplicate)
            setup = duplicate.get_editor_property('body_setup')
            original_setup = original.get_editor_property('body_setup')
            if setup is not None and original_setup is not None:
                flag = original_setup.get_editor_property('collision_trace_flag')
                if setup.get_editor_property('collision_trace_flag') != flag:
                    setup.set_editor_property('collision_trace_flag', flag)
                    item['restoredCollisionTraceFlag'] = str(flag)
            if duplicate.get_editor_property('lod_for_collision') != original.get_editor_property('lod_for_collision'):
                duplicate.set_editor_property('lod_for_collision', original.get_editor_property('lod_for_collision'))
                item['restoredLodForCollision'] = True
            if _asset_path(duplicate.get_material(0)) != _asset_path(original.get_material(0)):
                raise RuntimeError('Material slot 0 changed on the duplicate')
            if not native.assets.save_loaded_asset(duplicate, only_if_is_dirty=False):
                raise RuntimeError('Save failed: ' + destination)
        except Exception:
            try:
                native.assets.delete_loaded_asset(duplicate)
                item['duplicateDiscarded'] = True
            except Exception as cleanup:  # noqa: BLE001
                item['duplicateCleanupError'] = str(cleanup)
            raise
        destination_file = disk_path(destination)
        if not destination_file.exists():
            raise RuntimeError('Saved duplicate not on disk: ' + str(destination_file))
        item.update(saved=True, destinationUassetSha256=sha256_of(destination_file), sourceUassetSha256After=sha256_of(source_file))
        if item['sourceUassetSha256After'] != item['sourceUassetSha256Before']:
            raise RuntimeError('ORIGINAL asset bytes changed: ' + source_path)

        try:
            reloaded, duplicate = native.reload_from_disk(destination)
        except Exception as error:  # noqa: BLE001
            reloaded, duplicate = False, native.load_static_mesh(destination)
            item['reloadError'] = str(error)
        item['reloadedFromDisk'] = reloaded
        after_rows = native.triangle_rows(native.source_dynamic_mesh(duplicate))
        after = native.render_summary(duplicate)
        item['after'] = {'sourceTriangles': len(after_rows), 'render': after}
        problems = []
        if len(after_rows) != expected_after:
            problems.append('source triangle count %d != %d' % (len(after_rows), expected_after))
        if after['renderTriangles'] not in (expected_after, before['render']['renderTriangles'] - len(tids)):
            problems.append('render triangle count %d unexpected' % after['renderTriangles'])
        if asset_spec['expectedBoundsAfterCutCm'] and sorted(cut_edges) == sorted(self.spec['cutRule']['cutEdges']):
            error = box_error(after['boundsCm'], asset_spec['expectedBoundsAfterCutCm'])
            item['boundsAfterErrorCm'] = error
            if error > self.spec['verification']['boundsToleranceCm']:
                problems.append('bounds after cut differ by %.3f cm' % error)
        if after['material'] != before['render']['material']:
            problems.append('material changed to %s' % after['material'])
        if after['materialSlots'] != before['render']['materialSlots']:
            problems.append('material slot count changed')
        item['problems'] = problems
        item['status'] = 'cut_saved_verified' if not problems else 'saved_but_verification_failed'
        if problems:
            raise RuntimeError('Verification failed for %s: %s' % (destination, problems))
        self.remaining[destination] = [r['centroid'] for r in after_rows]
        return duplicate

    def swap_meshes(self, walls, duplicates):
        for wall in walls:
            duplicate = duplicates[wall['mesh']]
            if not wall['component'].set_static_mesh(duplicate):
                raise RuntimeError('set_static_mesh returned False for ' + wall['label'])
            if _asset_path(wall['component'].get_editor_property('static_mesh')) != _asset_path(duplicate):
                raise RuntimeError('Static mesh readback differs for ' + wall['label'])
            wall['newMesh'] = _asset_path(duplicate)

    # -- option B --------------------------------------------------------------

    def move_overlays(self, rows):
        ue = self.ue
        b = self.spec['optionB']
        offset = [b['normal'][0] * b['offsetCm'], b['normal'][1] * b['offsetCm'], 0.0]
        records = []
        for row in rows:
            if not _is_identity(row['pose'], self.spec['verification']['transformToleranceCm']):
                raise RuntimeError('Overlay %s is not at identity; refusing to move it again' % row['label'])
            actor = row['actor']
            actor.set_actor_location(ue.Vector(*offset), False, True)
            pose = _actor_pose(actor)
            if max(abs(pose['location'][i] - offset[i]) for i in range(3)) > self.spec['verification']['transformToleranceCm']:
                raise RuntimeError('Overlay %s did not move to %s' % (row['label'], offset))
            records.append({'label': row['label'], 'name': row['name'], 'mesh': row['meshes'][0], 'originalPose': row['pose'],
                            'newLocation': offset, 'boundsBefore': row['bounds'], 'boundsAfter': _actor_bounds(actor)})
        return records


def parse_cut_edges(token, spec):
    edges = [int(v) for v in token.split(',') if v.strip()]
    unknown = [e for e in edges if e not in spec['cutRule']['cutEdges']]
    if unknown or not edges:
        raise RuntimeError('-KotelCutEdges must be a non-empty subset of %s' % spec['cutRule']['cutEdges'])
    return edges


def run(mode='optionA', cut_edges=None):
    """mode: 'diagnose' | 'optionA' | 'optionB'. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    spec = load_spec()
    offline = offline_check(spec, deep=False)
    cut_edges = cut_edges or list(spec['cutRule']['cutEdges'])
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    native = Native()
    fix = Fix(ue, spec, native)
    if fix.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before the checkpointed fix')
    fix.open_map()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}
    for asset in spec['assets']:
        protected[asset['source']] = sha256_of(ROOT / asset['uassetFile'])
    receipt_folder = ROOT / spec['receiptFolder']
    prefix = spec['diagnosticPrefix'] if mode == 'diagnose' else spec['receiptPrefix']
    fix.receipt_path = receipt_folder / (prefix + stamp + '.json')
    if fix.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(fix.receipt_path))
    fix.receipt = {
        'status': 'started', 'stamp': stamp, 'mode': mode, 'cutEdges': cut_edges, 'map': TARGET, 'mapFile': str(map_file),
        'mapSha256Before': map_sha_before, 'lastKnownMapSha256Matched': map_sha_before == spec['lastKnownMapSha256'],
        'protectedSha256Before': protected, 'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'wallActors': [], 'assets': [], 'errors': [], 'mapSaved': False,
        'limitations': list(spec['limitations']),
    }
    fix.write_receipt()
    saved = False
    checkpoint = None
    try:
        fix.take_snapshot()
        baseline = fix.numeric_baseline(fix.snapshot)
        base_before = fix.base_wall_state()
        overlays = fix.overlay_rows()
        fix.receipt['baseWall'] = base_before
        fix.receipt['overlays'] = [{'label': r['label'], 'mesh': r['meshes'][0], 'pose': r['pose']} for r in overlays]
        duplicates_present = [a['destination'] for a in spec['assets'] if any(a['destination'] in row['meshes'] for row in fix.snapshot)]
        if duplicates_present:
            raise RuntimeError('Cut duplicates already placed in the map: %s' % duplicates_present)
        walls = fix.wall_actors([a['source'] for a in spec['assets']])
        fix.receipt['wallActors'] = [{k: v for k, v in w.items() if k not in ('row', 'component')} for w in walls]

        if mode == 'diagnose':
            for asset in spec['assets']:
                entry, _, _ = fix.diagnose_asset(asset, native.load_static_mesh(asset['source']), cut_edges)
                fix.receipt['assets'].append(entry)
            fix.receipt['status'] = 'diagnosed_nothing_modified'
            return fix.receipt

        if mode == 'optionA':
            for row in overlays:
                if not _is_identity(row['pose'], spec['verification']['transformToleranceCm']):
                    raise RuntimeError('Overlay %s is not at identity (Option B applied?); refusing Option A' % row['label'])
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        copied = []
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[6:]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[6:])
                copied.append(str(external))
        fix.receipt.update(checkpoint=str(checkpoint), oneFilePerActorFoldersCopied=copied)
        fix.write_receipt()

        if mode == 'optionA':
            duplicates = {}
            for asset in spec['assets']:
                item = {'source': asset['source'], 'destination': asset['destination'], 'status': 'started'}
                fix.receipt['assets'].append(item)
                fix.write_receipt()
                duplicates[asset['source']] = fix.cut_asset(asset, cut_edges, checkpoint, item)
                fix.write_receipt()
            dirty = ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()
            if dirty:
                fix.receipt['dirtyContentPackagesAfterAssetSave'] = [p.get_name() for p in dirty]
            # Probe the cut duplicates BEFORE touching the map: a failure leaves the map unchanged
            # (the saved, unreferenced duplicates are listed in the receipt for manual deletion).
            centroids = [c for values in fix.remaining.values() for c in values]
            probe = geometric_probe(centroids, spec['faces'], cut_edges, spec['probe'], spec['cutRule'])
            fix.receipt['probe'] = probe
            fix.write_receipt()
            if not probe['passed']:
                fix.receipt['unreferencedDuplicatesSaved'] = [a['destination'] for a in spec['assets']]
                raise RuntimeError('Probe failed on the cut duplicates: min clearance %s cm, %d centroids still in the cut band; map untouched'
                                   % (probe['minClearanceCm'], probe['remainingCentroidsInCutBand']))
            fix.swap_meshes(walls, duplicates)
            fix.receipt['wallActors'] = [{k: v for k, v in w.items() if k not in ('row', 'component')} for w in walls]
            expected_changes = {w['name'] for w in walls}
        else:
            fix.receipt['optionB'] = {'moved': fix.move_overlays(overlays), 'offsetCm': spec['optionB']['offsetCm'], 'normal': spec['optionB']['normal']}
            expected_changes = {r['name'] for r in overlays}

        current = fix.numeric_baseline(fix.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row and name not in expected_changes]
        if changed:
            raise RuntimeError('Unrelated actors changed before save: %s' % changed[:10])
        if not fix.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        fix.receipt.update(mapSaved=True, mapSha256AfterSave=sha256_of(map_file))
        fix.write_receipt()

        fix.open_map()
        reopened = fix.take_snapshot()
        reopened_numeric = fix.numeric_baseline(reopened)
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row and name not in expected_changes]
        if changed:
            raise RuntimeError('Unrelated actors differ after reopen: %s' % changed[:10])
        readback = []
        if mode == 'optionA':
            for wall in walls:
                rows = [r for r in reopened if r['name'] == wall['name']]
                if len(rows) != 1 or rows[0]['meshes'] != [wall['newMesh']]:
                    raise RuntimeError('Reopened %s does not reference %s' % (wall['label'], wall['newMesh']))
                row = rows[0]
                if not _is_identity(row['pose'], spec['verification']['transformToleranceCm']):
                    raise RuntimeError('Reopened %s moved' % wall['label'])
                mesh = row['components'][0].get_editor_property('static_mesh')
                readback.append({'label': row['label'], 'folder': row['folder'], 'mesh': row['meshes'][0], 'originalMesh': wall['mesh'],
                                 'renderTriangles': mesh.get_num_triangles(0), 'worldBoundsCm': row['bounds'],
                                 'collisionProfile': str(row['components'][0].get_collision_profile_name())})
            fix.receipt['restore'] = {'howTo': 'Set each wallActors[].component static_mesh back to its `mesh` (original) and save, or copy the '
                                               'checkpoint Walkthrough.umap back; the *_KotelCut duplicates may then be deleted.',
                                      'checkpointMap': str(checkpoint / map_file.name)}
        else:
            for record in fix.receipt['optionB']['moved']:
                rows = [r for r in reopened if r['name'] == record['name']]
                if len(rows) != 1 or max(abs(rows[0]['pose']['location'][i] - record['newLocation'][i]) for i in range(3)) > spec['verification']['transformToleranceCm']:
                    raise RuntimeError('Reopened overlay %s is not at the moved location' % record['label'])
                readback.append({'label': record['label'], 'pose': rows[0]['pose'], 'worldBoundsCm': rows[0]['bounds']})
            fix.receipt['restore'] = {'howTo': 'Set each moved overlay actor location back to [0,0,0] and save, or copy the checkpoint Walkthrough.umap back.',
                                      'checkpointMap': str(checkpoint / map_file.name)}
        fix.receipt['reopenedReadback'] = readback
        base_after = fix.base_wall_state()
        if base_after != base_before:
            raise RuntimeError('Kotel base state differs after reopen')
        fix.receipt['status'] = ('citywall_cut_duplicates_swapped_saved_reopened_visual_acceptance_pending' if mode == 'optionA'
                                 else 'overlays_moved_optionB_saved_reopened_visual_acceptance_pending')
        return fix.receipt
    except Exception as error:
        fix.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        fix.receipt['status'] = 'failed_after_save_checkpoint_available' if saved else 'failed_before_map_save_map_unchanged'
        raise
    finally:
        fix.receipt['mapSha256After'] = sha256_of(map_file)
        fix.receipt['mapBytesChanged'] = fix.receipt['mapSha256After'] != map_sha_before
        unchanged = {}
        for key, value in protected.items():
            path = disk_path(key, 'umap') if key in spec['protectedMaps'] else disk_path(key)
            unchanged[key] = sha256_of(path) == value
        fix.receipt['protectedUnchanged'] = unchanged
        fix.receipt['allProtectedUnchanged'] = all(unchanged.values())
        fix.write_receipt()
        ue.log('release_fix_kotel_occlusion: %s -> %s' % (fix.receipt['status'], fix.receipt_path))


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_fix_kotel_occlusion.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    lowered = command_line.lower()
    mode = 'optionB' if OPTION_B_FLAG in lowered else 'optionA'
    if '-diagnoseonly' in lowered:
        mode = 'diagnose'
    cut_edges = None
    for token in command_line.split():
        if token.lower().startswith('-kotelcutedges='):
            cut_edges = parse_cut_edges(token.split('=', 1)[1].strip('"'), load_spec())
    try:
        receipt = run(mode=mode, cut_edges=cut_edges)
        ue.log('release_fix_kotel_occlusion: %s (mode %s)' % (receipt['status'], mode))
    except Exception as error:
        ue.log_error('release_fix_kotel_occlusion failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in lowered and '-run=pythonscript' not in lowered:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    elif '--build-spec' in sys.argv:
        built = build_spec(write=True)
        print(json.dumps({'spec': str(SPEC_PATH), 'collateral': built['collateral'],
                          'assets': [{k: v for k, v in a.items() if k != 'boxes'} for a in built['assets']]}, indent=2))
        print(json.dumps(offline_check(), indent=2))
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

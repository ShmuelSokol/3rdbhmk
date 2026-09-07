"""Guarded east-west poles for the CC BY-SA davidgra11 Aron: strip the model's north-south poles,
build a gold east-west pole and place two of them reaching the paroches (Yoma 54a / Menachot 98a-b,
Rashi Shemot 25:12), swapping RELEASE_Aron_Body to the pole-less duplicate.

What it does, in order (every number comes from Scripts/release_aron_poles.spec.json):

  1. Guards: right project, no game world, no dirty packages, frozen OBJ hash intact, the imported
     body mesh present with the receipt's triangle count and bounds, gold material present, the
     NoPoles duplicate and the pole mesh ABSENT (or present for -AronPolesPlaceOnly), the map present.
  2. Duplicates SM_ThirdParty_AronBody_davidgra11 to SM_ThirdParty_AronBody_davidgra11_NoPoles in the
     same folder, reads its LOD0 source model into a DynamicMesh (GeometryScript, needs
     -EnablePlugins=GeometryScripting), re-derives the two pole axes from the pole-tip corners,
     classifies every triangle by the spec's pole rule (distance from the axis, outward-normal test for
     the ring-bore band), deletes the pole triangles (index-list API, per-triangle fallback), checks
     the count against the offline parse, writes the mesh back, verifies triangles/bounds/materials,
     saves. Records before/after counts and the remaining bounds (body plus rings; Y +-42.5 mm).
  3. Builds one capsule pole (radius 4 cm, length from the geometry rule: west stub behind the Aron to
     3.4 cm inside the paroches cloth, ~680 cm), gold material, saved as SM_AronPolesEW
     (GeometryScript_NewAssetUtils, fallback: duplicate /Engine/BasicShapes/Cylinder + copy_mesh_to_static_mesh).
  4. Loads the combined map, refuses if RELEASE_Aron_Body is not exactly as the rotate receipt left it
     or if any RELEASE_Aron_Pole_* exists, checkpoints the .umap, checks clearance (vessels rules;
     paroches cloth/hem are the intended intersection), swaps the body's static mesh to the NoPoles
     duplicate, spawns RELEASE_Aron_Pole_N / RELEASE_Aron_Pole_S (NoCollision), verifies no other actor
     changed, saves, reopens, reads back and writes SourceAssets/third-party/aron-poles-<stamp>.json
     (written at start and in finally).

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_aron_poles.py"
      -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-AronPoles-01.log"

Optional switches (read from the engine command line):
  -AronPolesMeshOnly          steps 2-3 only, no map change.
  -AronPolesPlaceOnly         skip 2-3; both meshes must already exist (re-verified).
  -AronPolesDeleteRings       also delete the four model rings (see spec ringRule; not default).
  -AronPolesEastEndX=<x>      pole east end (default spec poles.eastEndX = -5590; must be inside the cloth).
  -AronPolesWestStubCm=<cm>   pole overhang west of the Aron (default 30).

Offline (no engine):  python Scripts/release_aron_poles.py  -> prints offline_check(): hash, OBJ parse,
pole axes, pole/ring-bore/body triangle counts, kept bounds, the pole plan (world numbers) and disk state.

Risks: 715k-triangle readback through per-triangle GeometryScript calls (minutes; the vessels winding
check took this path in 5.8 because the bulk list API did not round-trip). GeometryScript_List /
GeometryScript_NewAssetUtils availability is probed at run time with recorded fallbacks. The pole-less
mesh is a CC BY-SA derivative (attribution unchanged).

Reuses the pure helpers and Placement utilities of Scripts/release_place_assets.py and the DynamicMesh
readback and clearance code of Scripts/release_import_thirdparty_vessels.py.
"""
import hashlib
import importlib.util
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_aron_poles.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


# --------------------------------------------------------------------------
# Spec, shared helpers, pure geometry (no unreal import)
# --------------------------------------------------------------------------

def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def _load_module(relative_path, name):
    path = ROOT / relative_path
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def load_helpers(spec):
    """release_place_assets (pure box maths + Placement) and the vessels script (OBJ parse, DynamicMesh readback, clearance)."""
    helper = _load_module(spec['placementHelper'], 'release_place_assets')
    vessels = _load_module(spec['vesselsScript'], 'release_import_thirdparty_vessels')
    for name in ('sha256_of', 'disk_path', 'box_error', 'boxes_overlap_volume', 'verify_union_decomposition', 'Placement',
                 '_pose_close', '_actor_bounds', '_actor_pose', '_asset_path', '_static_mesh_box'):
        if not hasattr(helper, name):
            raise RuntimeError('release_place_assets.py lacks helper ' + name)
    for name in ('parse_obj', 'bounds_of', '_source_dynamic_mesh', '_xyz', 'VesselPlacement'):
        if not hasattr(vessels, name):
            raise RuntimeError('release_import_thirdparty_vessels.py lacks helper ' + name)
    return helper, vessels


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def face_normal(corners, handedness):
    """'right' = cross(B-A, C-A) (raw OBJ); 'ue' = cross(C-A, B-A) (imported asset, see spec windingConvention)."""
    a, b, c = corners
    return _cross(_sub(b, a), _sub(c, a)) if handedness == 'right' else _cross(_sub(c, a), _sub(b, a))


class PoleClassifier:
    """Spec pole rule shared by the offline OBJ parse and the engine DynamicMesh readback."""

    def __init__(self, spec, axes, handedness, delete_rings=False):
        self.rule = spec['poleRule']
        self.ring = spec['ringRule']
        self.axes = axes            # {'plus': [xc, zc, r], 'minus': [xc, zc, r]}
        self.handedness = handedness
        self.delete_rings = delete_rings

    def axis_for(self, cx):
        return self.axes['plus' if cx > 0 else 'minus']

    def classify(self, corners):
        """Returns (kind, distance, radial_dot_or_None). kinds: pole, ringBore, ring, other."""
        cx = sum(v[0] for v in corners) / 3.0
        cy = sum(v[1] for v in corners) / 3.0
        cz = sum(v[2] for v in corners) / 3.0
        xc, zc, _ = self.axis_for(cx)
        dx = cx - xc
        dz = cz - zc
        d = math.hypot(dx, dz)
        radial = None
        kind = 'other'
        if d < self.rule['poleInnerRadius']:
            kind = 'pole'
        elif d < self.rule['poleOuterRadius']:
            n = face_normal(corners, self.handedness)
            length = math.sqrt(sum(c * c for c in n)) or 1.0
            radial = (n[0] * dx + n[2] * dz) / (length * d)
            kind = 'pole' if radial > self.rule['outwardDotMin'] else 'ringBore'
        if kind != 'pole' and self.delete_rings:
            z0, z1 = self.ring['zBand']
            if abs(cx) > self.ring['minAbsX'] and z0 < cz < z1 and abs(cy) < self.ring['maxAbsY']:
                kind = 'ring'
        return kind, d, radial


def tip_extents_from_corners(corner_iter, tip_min_abs_y):
    ext = {}
    for v in corner_iter:
        if abs(v[1]) <= tip_min_abs_y:
            continue
        side = 'plus' if v[0] > 0 else 'minus'
        e = ext.get(side)
        if e is None:
            ext[side] = {'xmin': v[0], 'xmax': v[0], 'zmin': v[2], 'zmax': v[2], 'count': 1}
        else:
            e['xmin'] = min(e['xmin'], v[0]); e['xmax'] = max(e['xmax'], v[0])
            e['zmin'] = min(e['zmin'], v[2]); e['zmax'] = max(e['zmax'], v[2]); e['count'] += 1
    return ext


def finish_axes(ext, corner_iter, tip_min_abs_y):
    """Axis centre from the tip extents plus the max radial distance of the tip corners."""
    axes = {side: [(e['xmin'] + e['xmax']) / 2.0, (e['zmin'] + e['zmax']) / 2.0, 0.0] for side, e in ext.items()}
    for v in corner_iter:
        if abs(v[1]) <= tip_min_abs_y:
            continue
        axis = axes['plus' if v[0] > 0 else 'minus']
        axis[2] = max(axis[2], math.hypot(v[0] - axis[0], v[2] - axis[1]))
    return axes


def check_axes(spec, axes):
    tolerance = spec['poleRule']['axisToleranceFileUnits']
    for side in ('plus', 'minus'):
        if side not in axes:
            raise RuntimeError('No pole tip corners found on side ' + side)
        expected = spec['poleRule']['axes'][side]
        error = max(abs(axes[side][i] - expected[i]) for i in range(3))
        if error > tolerance:
            raise RuntimeError('Pole axis %s %r differs from spec %r by %.4f' % (side, axes[side], expected, error))


def classify_all(spec, triangles_corners, axes, handedness, delete_rings):
    """triangles_corners: iterable of (tid, corners). Returns (kinds_by_tid list of (tid, kind), summary)."""
    classifier = PoleClassifier(spec, axes, handedness, delete_rings)
    rule = spec['poleRule']
    counts = {'pole': 0, 'ringBore': 0, 'ring': 0, 'other': 0}
    deleted = []
    kept_min = [math.inf] * 3
    kept_max = [-math.inf] * 3
    tube_total = 0
    tube_outward = 0
    for tid, corners in triangles_corners:
        kind, d, radial = classifier.classify(corners)
        counts[kind] += 1
        if kind == 'pole' and d < 1.8 and abs(sum(v[1] for v in corners) / 3.0) < 60.0:
            # self-check of the normal convention on sure tube triangles
            n = face_normal(corners, handedness)
            cx = sum(v[0] for v in corners) / 3.0
            cz = sum(v[2] for v in corners) / 3.0
            xc, zc, _ = classifier.axis_for(cx)
            tube_total += 1
            if n[0] * (cx - xc) + n[2] * (cz - zc) > 0:
                tube_outward += 1
        if kind in ('pole', 'ring'):
            deleted.append(tid)
        else:
            for v in corners:
                for i in range(3):
                    if v[i] < kept_min[i]:
                        kept_min[i] = v[i]
                    if v[i] > kept_max[i]:
                        kept_max[i] = v[i]
    fraction = tube_outward / tube_total if tube_total else 0.0
    if fraction < rule['tubeSelfCheckMinOutwardFraction']:
        raise RuntimeError('Normal convention %s does not point outward on the pole tube (%.3f outward)' % (handedness, fraction))
    expected = rule['expectedPoleTriangles']
    if abs(counts['pole'] - expected) > rule['poleCountToleranceFraction'] * expected:
        raise RuntimeError('Pole triangle count %d differs from the offline expectation %d' % (counts['pole'], expected))
    summary = {'counts': counts, 'deletedTriangles': len(deleted), 'keptBounds': {'min': kept_min, 'max': kept_max},
               'tubeSelfCheck': {'triangles': tube_total, 'outwardFraction': fraction, 'handedness': handedness}}
    return deleted, summary


def expected_kept_bounds(spec, delete_rings):
    return spec['ringRule']['expectedKeptBoundsFileUnitsIfDeleted'] if delete_rings else spec['poleRule']['expectedKeptBoundsFileUnits']


def reflect_y(box):
    return {'min': [box['min'][0], -box['max'][1], box['min'][2]], 'max': [box['max'][0], -box['min'][1], box['max'][2]]}


def bounds_match_either(box, expected, tolerance, helper):
    """The importer mirrored Y: accept the expected box or its Y-mirror; returns (ok, mirrored, error)."""
    plain = helper.box_error(box, expected)
    mirrored = helper.box_error(box, reflect_y(expected))
    if mirrored <= tolerance and mirrored <= plain:
        return True, True, mirrored
    return plain <= tolerance, False, plain


def plan_poles(spec, body_local_kept_box, east_end_x=None, west_stub_cm=None):
    """World numbers for both poles from the pole-less body's local box (asset units, cm) and the body actor pose."""
    poles = spec['poles']
    body = spec['aronActors']['body']
    scale = body['scale'][0]
    origin = body['location']
    radius = float(poles['radiusCm'])
    east_end = float(poles['eastEndX'] if east_end_x is None else east_end_x)
    west_stub = float(poles['westStubCm'] if west_stub_cm is None else west_stub_cm)
    half_length_world = max(abs(body_local_kept_box['min'][1]), abs(body_local_kept_box['max'][1])) * scale
    body_west_x = origin[0] + body_local_kept_box['min'][0] * scale
    west_end = body_west_x - west_stub
    if east_end <= west_end + 2 * radius:
        raise RuntimeError('Pole east end %.1f is not east of the west end %.1f' % (east_end, west_end))
    length = east_end - west_end
    centre_x = (east_end + west_end) / 2.0
    y = half_length_world + radius + float(poles['gapCm'])
    z = origin[2] + float(poles['modelPoleAxisZFileUnits']) * scale
    cloth = poles['paroches']['clothWorldBoundsCm']
    if not (cloth['min'][0] < east_end < cloth['max'][0]):
        raise RuntimeError('Pole east end %.2f is not inside the paroches cloth X range %r (spec)' % (east_end, [cloth['min'][0], cloth['max'][0]]))
    local_box = {'min': [-length / 2.0, -radius, -radius], 'max': [length / 2.0, radius, radius]}
    actors = {}
    for key, sign in (('north', -1.0), ('south', 1.0)):
        location = [centre_x, sign * y, z]
        actors[key] = {'label': poles['labels'][key], 'location': location, 'rotation': [0.0, 0.0, 0.0], 'scale': [1.0, 1.0, 1.0],
                       'plannedWorldBoundsCm': {'min': [location[i] + local_box['min'][i] for i in range(3)],
                                                'max': [location[i] + local_box['max'][i] for i in range(3)]}}
    envelope = poles['kodeshEnvelope']
    for actor in actors.values():
        box = actor['plannedWorldBoundsCm']
        if not all(box['min'][i] >= envelope['min'][i] - 1e-6 and box['max'][i] <= envelope['max'][i] + 1e-6 for i in range(3)):
            raise RuntimeError('%s leaves the Kodesh envelope: %r' % (actor['label'], box))
    body_box = spec['aronActors']['body']['worldBoundsCm']
    body_east_x = origin[0] + body_local_kept_box['max'][0] * scale
    return {
        'radiusCm': radius, 'lengthCm': length, 'lineLengthCm': length - 2 * radius, 'centreX': centre_x, 'westEndX': west_end,
        'eastEndX': east_end, 'westStubCm': west_stub, 'bodyWestX': body_west_x, 'bodyEastX': body_east_x,
        'eastReachBeyondBodyCm': east_end - body_east_x, 'bodyHalfLengthWorldCm': half_length_world,
        'poleCentreAbsY': y, 'poleCentreZ': z, 'poleHeightAboveFloorCm': z - origin[2],
        'clothPenetrationCm': east_end - cloth['min'][0], 'lengthAmot50cm': length / 50.0,
        'gapToBodyCm': y - radius - half_length_world, 'poleTopBelowBodyTopCm': body_box['max'][2] - (z + radius),
        'meshLocalBoundsCm': local_box, 'actors': actors,
        'asymmetryNote': 'West stub %.1f cm beyond the Aron, east reach %.1f cm beyond it to the paroches: Yoma 54a / Menachot 98a-b '
                         '(the poles lengthened and pressed into the paroches); the book (Lishchno Tidreshu pp. 79-81, 155-156) gives no number.'
                         % (west_stub, east_end - body_east_x),
    }


# --------------------------------------------------------------------------
# Offline check (no engine)
# --------------------------------------------------------------------------

def offline_check(spec=None, expect_meshes=None, delete_rings=False, east_end_x=None, west_stub_cm=None):
    """Consistency checks that need no engine; raises on the first failure.

    expect_meshes: False for a fresh run (NoPoles + pole mesh must be absent), True for -AronPolesPlaceOnly,
    None to record the disk state only.
    """
    spec = spec or load_spec()
    helper, vessels = load_helpers(spec)
    source = spec['source']
    report = {'switches': {'deleteRings': delete_rings, 'eastEndX': east_end_x, 'westStubCm': west_stub_cm}}

    folder = ROOT / source['folder'] / source['slug']
    path = folder / source['file']
    if not (folder / 'LICENSE.txt').exists() or not (folder / 'provenance.json').exists():
        raise RuntimeError('LICENSE.txt / provenance.json missing for ' + source['slug'])
    actual_sha = sha256_of(path)
    if actual_sha != source['sha256']:
        raise RuntimeError('Frozen OBJ hash differs for ' + source['file'])
    vertices, faces = vessels.parse_obj(path)
    box = vessels.bounds_of(vertices)
    if len(vertices) != source['vertices'] or len(faces) != source['triangles']:
        raise RuntimeError('OBJ parsed %d vertices / %d triangles, spec %d / %d' % (len(vertices), len(faces), source['vertices'], source['triangles']))
    if helper.box_error(box, source['boundsFileUnits']) > 1e-3:
        raise RuntimeError('OBJ bounds differ from spec: %r' % box)
    report['sourceFile'] = {'file': str(path), 'sha256': actual_sha, 'triangles': len(faces), 'vertices': len(vertices), 'boundsFileUnits': box,
                            'license': source['license']}

    tip_min = spec['poleRule']['tipMinAbsY']
    ext = tip_extents_from_corners(vertices, tip_min)
    axes = finish_axes(ext, vertices, tip_min)
    check_axes(spec, axes)
    report['poleAxesFileUnits'] = axes

    def corners():
        for tid, (a, b, c) in enumerate(faces):
            yield tid, (vertices[a], vertices[b], vertices[c])
    deleted, summary = classify_all(spec, corners(), axes, 'right', delete_rings)
    expected = expected_kept_bounds(spec, delete_rings)
    error = helper.box_error(summary['keptBounds'], expected)
    if error > spec['poleRule']['keptBoundsToleranceFileUnits']:
        raise RuntimeError('Kept bounds %r differ from spec %r by %.4f' % (summary['keptBounds'], expected, error))
    if not delete_rings and abs(summary['counts']['ringBore'] - spec['poleRule']['expectedRingBoreBandTriangles']) > 50:
        raise RuntimeError('Ring-bore band count %d differs from spec %d' % (summary['counts']['ringBore'], spec['poleRule']['expectedRingBoreBandTriangles']))
    # The pole triangles must be the ONLY triangles reaching beyond the body's long extent.
    body_y = max(abs(expected['min'][1]), abs(expected['max'][1]))
    deleted_set = set(deleted)
    beyond = [tid for tid, (a, b, c) in enumerate(faces) if abs((vertices[a][1] + vertices[b][1] + vertices[c][1]) / 3.0) > body_y + 0.05]
    leaked = [tid for tid in beyond if tid not in deleted_set]
    if leaked:
        raise RuntimeError('%d non-pole triangles lie beyond the body length' % len(leaked))
    summary['trianglesBeyondBodyLength'] = len(beyond)
    summary['bodyLongHalfExtentFileUnits'] = body_y
    summary['poleOverhangFileUnits'] = box['max'][1] - body_y
    summary['trianglesBefore'] = len(faces)
    summary['trianglesAfter'] = len(faces) - len(deleted)
    report['poleSeparation'] = summary

    # Disk state: assets, material, map, receipts.
    body = spec['bodyMesh']
    report['bodyMeshOnDisk'] = helper.disk_path(body['asset']).exists()
    if not report['bodyMeshOnDisk']:
        raise RuntimeError('Imported body mesh missing on disk: ' + body['asset'])
    report['noPolesOnDisk'] = helper.disk_path(body['noPolesAsset']).exists()
    report['poleMeshOnDisk'] = helper.disk_path(spec['poles']['meshAsset']).exists()
    if expect_meshes is False and (report['noPolesOnDisk'] or report['poleMeshOnDisk']):
        raise RuntimeError('Target meshes already exist on disk (use -AronPolesPlaceOnly): NoPoles %s, poles %s' % (report['noPolesOnDisk'], report['poleMeshOnDisk']))
    if expect_meshes is True and not (report['noPolesOnDisk'] and report['poleMeshOnDisk']):
        raise RuntimeError('Place-only needs both meshes on disk: NoPoles %s, poles %s' % (report['noPolesOnDisk'], report['poleMeshOnDisk']))
    report['goldMaterialOnDisk'] = helper.disk_path(body['material']).exists()
    if not report['goldMaterialOnDisk']:
        raise RuntimeError('Gold material missing on disk: ' + body['material'])
    if body['material'] != spec['poles']['material']:
        raise RuntimeError('Spec pole material differs from the body material')
    map_file = ROOT / spec['targetMapFile']
    if not map_file.exists():
        raise RuntimeError('Target map file missing')
    report['mapSha256OnDisk'] = sha256_of(map_file)
    report['mapMatchesLastKnown'] = report['mapSha256OnDisk'] == spec['lastKnownMapSha256']
    rotate = json.loads((ROOT / spec['aronActors']['rotateReceipt']).read_text(encoding='utf-8'))
    after = rotate['actors'][spec['aronActors']['bodyLabel']]['after']
    body_spec = spec['aronActors']['body']
    if max(abs(after['location'][i] - body_spec['location'][i]) for i in range(3)) > 1e-6 or abs(after['yaw'] - body_spec['rotation'][1]) > 1e-6:
        raise RuntimeError('Rotate receipt body pose differs from spec')
    if helper.box_error({'min': after['boundsMin'], 'max': after['boundsMax']}, body_spec['worldBoundsCm']) > 1e-6:
        raise RuntimeError('Rotate receipt body bounds differ from spec')
    report['rotateReceiptConsistent'] = True

    # Pole plan predicted from the offline kept bounds (mirrored like the importer; symmetric enough that both agree).
    plan = plan_poles(spec, reflect_y(summary['keptBounds']), east_end_x, west_stub_cm)
    plan_plain = plan_poles(spec, summary['keptBounds'], east_end_x, west_stub_cm)
    if abs(plan['poleCentreAbsY'] - plan_plain['poleCentreAbsY']) > 0.2:
        raise RuntimeError('Mirror ambiguity changes the pole Y by more than 0.2 cm')
    body_after = expected_body_bounds_after_swap(spec, reflect_y(summary['keptBounds']))
    for actor in plan['actors'].values():
        if helper.boxes_overlap_volume(actor['plannedWorldBoundsCm'], body_after):
            raise RuntimeError('%s planned AABB overlaps the pole-less body AABB %r' % (actor['label'], body_after))
    plan['bodyWorldBoundsAfterSwapPredicted'] = body_after
    if plan['poleTopBelowBodyTopCm'] <= 0:
        raise RuntimeError('Pole top is not below the body top')
    report['plan'] = plan
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side: meshes
# --------------------------------------------------------------------------

def _uasset_sha(helper, asset_path):
    return sha256_of(helper.disk_path(asset_path))


def _outcome_ok(ue, result):
    return ue.GeometryScriptOutcomePins.SUCCESS in (result if isinstance(result, tuple) else (result,))


def _first_of_type(result, cls):
    for item in (result if isinstance(result, tuple) else (result,)):
        if isinstance(item, cls):
            return item
    return None


def load_gold(ue, spec):
    material = ue.load_asset(spec['bodyMesh']['material'])
    if not isinstance(material, ue.MaterialInterface):
        raise RuntimeError('Gold material does not load: ' + spec['bodyMesh']['material'])
    return material


def assign_gold(ue, helper, mesh, material):
    slots = len(mesh.get_editor_property('static_materials'))
    if slots == 0:
        static_material = ue.StaticMaterial()
        static_material.set_editor_property('material_interface', material)
        static_material.set_editor_property('material_slot_name', 'Gold')
        mesh.set_editor_property('static_materials', [static_material])
        slots = 1
    for slot in range(slots):
        mesh.set_material(slot, material)
    wrong = [slot for slot in range(slots) if helper._asset_path(mesh.get_material(slot)) != helper._asset_path(material)]
    if wrong:
        raise RuntimeError('Material slots not assigned on %s: %s' % (mesh.get_name(), wrong))
    return slots


def _bulk_corners(ue, vessels, dynamic, info):
    """All (tid, corners) through the GeometryScript list API, or None if it is unavailable.

    UE Python returns non-const reference parameters (the lists, bHasGaps) in the result tuple; they
    are NOT passed in. Gaps (bSkipGaps False) come back as (-1, -1, -1) triangles and are skipped.
    """
    query = ue.GeometryScript_MeshQueries
    lists = getattr(ue, 'GeometryScript_List', None)
    if lists is None or not all(hasattr(query, n) for n in ('get_all_vertex_positions', 'get_all_triangle_indices')) \
            or not all(hasattr(lists, n) for n in ('convert_vector_list_to_array', 'convert_triangle_list_to_array')):
        return None
    try:
        position_list = _first_of_type(query.get_all_vertex_positions(dynamic, False), ue.GeometryScriptVectorList)
        triangle_list = _first_of_type(query.get_all_triangle_indices(dynamic, False), ue.GeometryScriptTriangleList)
        if position_list is None or triangle_list is None:
            return None
        positions = [vessels._xyz(v) for v in lists.convert_vector_list_to_array(position_list)]
        triangles = [(int(t.x), int(t.y), int(t.z)) for t in lists.convert_triangle_list_to_array(triangle_list)]
    except Exception as error:  # noqa: BLE001 - API shape differs between builds; per-triangle fallback
        info.setdefault('bulkReadErrors', []).append(repr(error))
        return None
    valid = [(tid, tri) for tid, tri in enumerate(triangles) if min(tri) >= 0]
    if len(valid) != dynamic.get_triangle_count() or len(positions) < dynamic.get_vertex_count():
        info.setdefault('bulkReadErrors', []).append('bulk lists: %d valid triangles / %d positions vs %d / %d' % (
            len(valid), len(positions), dynamic.get_triangle_count(), dynamic.get_vertex_count()))
        return None
    info['readMethod'] = 'bulk_lists'
    return [(tid, (positions[a], positions[b], positions[c])) for tid, (a, b, c) in valid]


def read_triangles(ue, vessels, dynamic, info):
    """Yield (tid, corners) for every valid triangle: bulk list API first, per-triangle queries otherwise."""
    bulk = _bulk_corners(ue, vessels, dynamic, info)
    if bulk is not None:
        for item in bulk:
            yield item
        return
    info['readMethod'] = 'per_triangle_loop'
    query = ue.GeometryScript_MeshQueries
    count = dynamic.get_triangle_count()
    seen = 0
    tid = 0
    limit = count * 2 + 16
    while seen < count and tid < limit:
        if query.is_valid_triangle_id(dynamic, tid):
            corners = [vessels._xyz(v) for v in query.get_triangle_positions(dynamic, tid) if isinstance(v, ue.Vector)]
            if len(corners) != 3:
                raise RuntimeError('triangle %d has %d corners' % (tid, len(corners)))
            seen += 1
            yield tid, corners
        tid += 1
    if seen != count:
        raise RuntimeError('Read %d of %d triangles' % (seen, count))


def delete_triangles(ue, dynamic, tids, receipt):
    """Index-list deletion; falls back to per-triangle deletion. Returns the method and count.

    FDynamicMesh3::RemoveTriangle (used by both GeometryScript paths) drops isolated vertices, so the
    mesh bounds shrink to the kept geometry.
    """
    edits = ue.GeometryScript_MeshEdits
    lists = getattr(ue, 'GeometryScript_List', None)
    before = dynamic.get_triangle_count()
    method = None
    if lists is not None and hasattr(lists, 'convert_array_to_index_list') and hasattr(edits, 'delete_triangles_from_mesh'):
        try:
            index_list = _first_of_type(lists.convert_array_to_index_list(list(tids), ue.GeometryScriptIndexType.TRIANGLE), ue.GeometryScriptIndexList)
            if index_list is None or lists.get_index_list_length(index_list) != len(tids):
                raise RuntimeError('index list did not round-trip')
            result = edits.delete_triangles_from_mesh(dynamic, index_list, False)
            deleted = [v for v in (result if isinstance(result, tuple) else (result,)) if isinstance(v, int) and not isinstance(v, bool)]
            if deleted and deleted[0] != len(tids):
                raise RuntimeError('delete_triangles_from_mesh removed %d of %d' % (deleted[0], len(tids)))
            method = 'delete_triangles_from_mesh_index_list'
        except Exception as error:  # noqa: BLE001 - recorded, then the per-triangle path is used
            receipt['limitations'].append('Index-list deletion unavailable (%r); per-triangle deletion used' % (error,))
            method = None
            if dynamic.get_triangle_count() != before:
                raise RuntimeError('Index-list deletion partially applied (%d -> %d); refusing to continue' % (before, dynamic.get_triangle_count()))
    if method is None:
        for tid in tids:
            result = edits.delete_triangle_from_mesh(dynamic, tid, True)
            flags = [v for v in (result if isinstance(result, tuple) else (result,)) if isinstance(v, bool)]
            if flags and not flags[0]:
                raise RuntimeError('delete_triangle_from_mesh refused triangle %d' % tid)
        method = 'delete_triangle_from_mesh_per_triangle'
    after = dynamic.get_triangle_count()
    if before - after != len(tids):
        raise RuntimeError('Deleted %d triangles, expected %d' % (before - after, len(tids)))
    return method, before - after


def _dynamic_box(ue, dynamic):
    box = ue.GeometryScript_MeshQueries.get_mesh_bounding_box(dynamic)
    return {'min': [float(box.min.x), float(box.min.y), float(box.min.z)], 'max': [float(box.max.x), float(box.max.y), float(box.max.z)]}


def write_dynamic_to_static(ue, spec, dynamic, mesh):
    options = ue.GeometryScriptCopyMeshToAssetOptions()
    for key, value in spec['bodyMesh']['rewriteOptions'].items():
        options.set_editor_property(key, value)
    lod = ue.GeometryScriptMeshWriteLOD()
    lod.set_editor_property('write_hi_res_source', False)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic, mesh, options, lod)
    if not _outcome_ok(ue, result):
        raise RuntimeError('copy_mesh_to_static_mesh failed: ' + str(result))


def make_no_poles_mesh(ue, spec, helper, vessels, receipt, delete_rings):
    """Duplicate the body asset, delete the pole triangles, write back, verify, save."""
    body = spec['bodyMesh']
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if assets.does_asset_exist(body['noPolesAsset']):
        raise RuntimeError('NoPoles asset already exists: ' + body['noPolesAsset'])
    source = ue.load_asset(body['asset'])
    if not isinstance(source, ue.StaticMesh):
        raise RuntimeError('Body mesh missing or not a StaticMesh: ' + body['asset'])
    source_box = helper._static_mesh_box(source)
    if source.get_num_triangles(0) != body['importedTriangles'] or helper.box_error(source_box, body['localBoundsCm']) > body['boundsToleranceCm']:
        raise RuntimeError('Body mesh differs from the import receipt: %d triangles, %r' % (source.get_num_triangles(0), source_box))
    info = {'sourceAsset': body['asset'], 'sourceTriangles': source.get_num_triangles(0), 'sourceLocalBoundsCm': source_box,
            'sourceUassetSha256': _uasset_sha(helper, body['asset'])}
    receipt['noPoles'] = info

    duplicate = assets.duplicate_asset(body['asset'], body['noPolesAsset'])
    if not isinstance(duplicate, ue.StaticMesh):
        raise RuntimeError('duplicate_asset did not return a StaticMesh')
    info['asset'] = helper._asset_path(duplicate)
    started = datetime.now(timezone.utc)
    dynamic = vessels._source_dynamic_mesh(ue, duplicate)
    info['dynamicTrianglesBefore'] = dynamic.get_triangle_count()
    info['dynamicVerticesBefore'] = dynamic.get_vertex_count()
    info['dynamicBoundsBefore'] = _dynamic_box(ue, dynamic)
    query = ue.GeometryScript_MeshQueries
    if hasattr(query, 'get_num_connected_components'):
        info['connectedComponentsBefore'] = int(query.get_num_connected_components(dynamic))

    # Pass 1: candidates near the spec axes (+ tip corners for the axis re-derivation).
    rule = spec['poleRule']
    spec_axes = rule['axes']
    candidates = []
    tip_corners = []
    for tid, corners in read_triangles(ue, vessels, dynamic, info):
        cx = sum(v[0] for v in corners) / 3.0
        cz = sum(v[2] for v in corners) / 3.0
        xc, zc, _ = spec_axes['plus' if cx > 0 else 'minus']
        if math.hypot(cx - xc, cz - zc) < rule['candidateRadius'] or (delete_rings and abs(cx) > spec['ringRule']['minAbsX'] - 0.5):
            candidates.append((tid, corners))
            for v in corners:
                if abs(v[1]) > rule['tipMinAbsY']:
                    tip_corners.append(v)
    info['readSeconds'] = (datetime.now(timezone.utc) - started).total_seconds()
    info['candidateTriangles'] = len(candidates)
    axes = finish_axes(tip_extents_from_corners(tip_corners, rule['tipMinAbsY']), tip_corners, rule['tipMinAbsY'])
    check_axes(spec, axes)
    info['poleAxesAssetUnits'] = axes
    deleted, summary = classify_all(spec, candidates, axes, 'ue', delete_rings)
    # Non-candidates are 'other' by construction; the kept bounds must therefore be taken from the whole mesh after deletion.
    info['classification'] = {'counts': summary['counts'], 'tubeSelfCheck': summary['tubeSelfCheck']}
    method, removed = delete_triangles(ue, dynamic, deleted, receipt)
    info['deletion'] = {'method': method, 'deletedTriangles': removed, 'deleteRings': delete_rings}
    info['dynamicTrianglesAfter'] = dynamic.get_triangle_count()
    info['dynamicVerticesAfter'] = dynamic.get_vertex_count()
    kept = _dynamic_box(ue, dynamic)
    info['dynamicBoundsAfter'] = kept
    expected = expected_kept_bounds(spec, delete_rings)
    ok, mirrored, error = bounds_match_either(kept, expected, rule['keptBoundsToleranceFileUnits'], helper)
    if not ok:
        raise RuntimeError('Pole-less bounds %r differ from the expected %r by %.4f' % (kept, expected, error))
    info['keptBoundsMirroredY'] = mirrored
    info['keptBoundsErrorAssetUnits'] = error

    write_dynamic_to_static(ue, spec, dynamic, duplicate)
    triangles = duplicate.get_num_triangles(0)
    if abs(triangles - dynamic.get_triangle_count()) > spec['bodyMesh']['maxTriangleCountDeviationFraction'] * dynamic.get_triangle_count():
        raise RuntimeError('Written asset has %d triangles, dynamic mesh %d' % (triangles, dynamic.get_triangle_count()))
    box = helper._static_mesh_box(duplicate)
    if helper.box_error(box, kept) > body['boundsToleranceCm']:
        raise RuntimeError('Written asset bounds %r differ from the dynamic mesh %r' % (box, kept))
    # Materials: the duplicate inherits the source body's slots (whatever the current gold is); empty slots get the spec gold.
    source_materials = [helper._asset_path(source.get_material(s)) for s in range(len(source.get_editor_property('static_materials')))]
    slots = len(duplicate.get_editor_property('static_materials'))
    materials = [helper._asset_path(duplicate.get_material(s)) for s in range(slots)]
    if slots == 0 or any(m is None for m in materials):
        assign_gold(ue, helper, duplicate, load_gold(ue, spec))
        slots = len(duplicate.get_editor_property('static_materials'))
        materials = [helper._asset_path(duplicate.get_material(s)) for s in range(slots)]
        receipt['limitations'].append('NoPoles duplicate had empty material slots; spec gold assigned')
    if materials != source_materials:
        raise RuntimeError('NoPoles materials %s differ from the source body %s' % (materials, source_materials))
    if not assets.save_loaded_asset(duplicate, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + body['noPolesAsset'])
    info.update({'triangles': triangles, 'vertices': duplicate.get_num_vertices(0), 'localBoundsCm': box, 'materialSlots': slots,
                 'materials': materials, 'sourceMaterials': source_materials, 'uassetSha256': _uasset_sha(helper, body['noPolesAsset']),
                 'secondsTotal': (datetime.now(timezone.utc) - started).total_seconds()})
    return duplicate, info


def load_no_poles_mesh(ue, spec, helper, receipt, delete_rings):
    body = spec['bodyMesh']
    mesh = ue.load_asset(body['noPolesAsset'])
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError('NoPoles mesh missing: ' + body['noPolesAsset'])
    box = helper._static_mesh_box(mesh)
    ok, mirrored, error = bounds_match_either(box, expected_kept_bounds(spec, delete_rings), body['boundsToleranceCm'], helper)
    if not ok:
        raise RuntimeError('Saved NoPoles bounds %r differ from the expectation by %.4f' % (box, error))
    triangles = mesh.get_num_triangles(0)
    expected = body['importedTriangles'] - spec['poleRule']['expectedPoleTriangles']
    if not delete_rings and abs(triangles - expected) > 0.02 * expected:
        raise RuntimeError('Saved NoPoles has %d triangles, expected about %d' % (triangles, expected))
    source = ue.load_asset(body['asset'])
    if not isinstance(source, ue.StaticMesh):
        raise RuntimeError('Body mesh missing: ' + body['asset'])
    source_materials = [helper._asset_path(source.get_material(s)) for s in range(len(source.get_editor_property('static_materials')))]
    slots = len(mesh.get_editor_property('static_materials'))
    materials = [helper._asset_path(mesh.get_material(s)) for s in range(slots)]
    if slots == 0 or any(m is None for m in materials) or materials != source_materials:
        raise RuntimeError('Saved NoPoles materials %s differ from the source body %s' % (materials, source_materials))
    info = {'asset': body['noPolesAsset'], 'reused': True, 'triangles': triangles, 'localBoundsCm': box, 'keptBoundsMirroredY': mirrored,
            'materialSlots': slots, 'materials': materials, 'sourceMaterials': source_materials, 'uassetSha256': _uasset_sha(helper, body['noPolesAsset'])}
    receipt['noPoles'] = info
    return mesh, info


def make_pole_mesh(ue, spec, helper, receipt, plan):
    """One capsule along local X, centred at the origin; gold; saved as spec poles.meshAsset."""
    poles = spec['poles']
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if assets.does_asset_exist(poles['meshAsset']):
        raise RuntimeError('Pole mesh already exists: ' + poles['meshAsset'])
    dynamic = ue.DynamicMesh()
    options = ue.GeometryScriptPrimitiveOptions()
    transform = ue.Transform(ue.Vector(0.0, 0.0, 0.0), ue.Rotator(pitch=90.0, yaw=0.0, roll=0.0), ue.Vector(1.0, 1.0, 1.0))
    ue.GeometryScript_Primitives.append_capsule(dynamic, options, transform, float(plan['radiusCm']), float(plan['lineLengthCm']),
                                                int(poles['hemisphereSteps']), int(poles['circleSteps']), int(poles['segmentSteps']),
                                                ue.GeometryScriptPrimitiveOriginMode.CENTER)
    box = _dynamic_box(ue, dynamic)
    error = helper.box_error(box, plan['meshLocalBoundsCm'])
    if error > spec['verification']['staticBoundsToleranceCm']:
        raise RuntimeError('Capsule bounds %r differ from the plan %r by %.4f (axis orientation?)' % (box, plan['meshLocalBoundsCm'], error))
    info = {'asset': poles['meshAsset'], 'dynamicTriangles': dynamic.get_triangle_count(), 'dynamicBoundsCm': box, 'boundsErrorCm': error,
            'radiusCm': plan['radiusCm'], 'lengthCm': plan['lengthCm'], 'lineLengthCm': plan['lineLengthCm'], 'endCaps': poles['endCaps']}
    mesh = None
    utils = getattr(ue, 'GeometryScript_NewAssetUtils', None)
    if utils is not None and hasattr(utils, 'create_new_static_mesh_asset_from_mesh'):
        try:
            create_options = ue.GeometryScriptCreateNewStaticMeshAssetOptions()
            create_options.set_editor_property('enable_recompute_normals', True)
            create_options.set_editor_property('enable_recompute_tangents', True)
            create_options.set_editor_property('enable_nanite', False)
            result = utils.create_new_static_mesh_asset_from_mesh(dynamic, poles['meshAsset'], create_options)
            candidate = _first_of_type(result, ue.StaticMesh)
            if candidate is None or not _outcome_ok(ue, result):
                raise RuntimeError('outcome ' + str(result))
            mesh = candidate
            info['createMethod'] = 'GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh'
        except Exception as error:  # noqa: BLE001 - recorded, fallback below
            receipt['limitations'].append('create_new_static_mesh_asset_from_mesh unavailable (%r); duplicated /Engine/BasicShapes/Cylinder instead' % (error,))
            mesh = None
    if mesh is None:
        if assets.does_asset_exist(poles['meshAsset']):
            raise RuntimeError('Pole asset path occupied after a failed create; refusing to overwrite')
        mesh = assets.duplicate_asset('/Engine/BasicShapes/Cylinder', poles['meshAsset'])
        if not isinstance(mesh, ue.StaticMesh):
            raise RuntimeError('Fallback duplicate of /Engine/BasicShapes/Cylinder failed')
        options_write = ue.GeometryScriptCopyMeshToAssetOptions()
        for key, value in dict(spec['bodyMesh']['rewriteOptions'], enable_recompute_normals=True, enable_recompute_tangents=True, replace_materials=False).items():
            options_write.set_editor_property(key, value)
        lod = ue.GeometryScriptMeshWriteLOD()
        lod.set_editor_property('write_hi_res_source', False)
        lod.set_editor_property('lod_index', 0)
        result = ue.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic, mesh, options_write, lod)
        if not _outcome_ok(ue, result):
            raise RuntimeError('copy_mesh_to_static_mesh failed for the pole: ' + str(result))
        info['createMethod'] = 'duplicate_engine_cylinder_plus_copy_mesh_to_static_mesh'
    if helper._asset_path(mesh) != poles['meshAsset']:
        raise RuntimeError('Pole mesh path %s differs from spec %s' % (helper._asset_path(mesh), poles['meshAsset']))
    saved_box = helper._static_mesh_box(mesh)
    if helper.box_error(saved_box, box) > spec['verification']['staticBoundsToleranceCm']:
        raise RuntimeError('Pole asset bounds %r differ from the capsule %r' % (saved_box, box))
    material = load_gold(ue, spec)
    slots = assign_gold(ue, helper, mesh, material)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + poles['meshAsset'])
    info.update({'triangles': mesh.get_num_triangles(0), 'localBoundsCm': saved_box, 'materialSlots': slots, 'material': helper._asset_path(material),
                 'uassetSha256': _uasset_sha(helper, poles['meshAsset'])})
    receipt['poleMesh'] = info
    return mesh, info


def load_pole_mesh(ue, spec, helper, receipt, plan):
    poles = spec['poles']
    mesh = ue.load_asset(poles['meshAsset'])
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError('Pole mesh missing: ' + poles['meshAsset'])
    box = helper._static_mesh_box(mesh)
    error = helper.box_error(box, plan['meshLocalBoundsCm'])
    if error > spec['verification']['staticBoundsToleranceCm']:
        raise RuntimeError('Saved pole mesh bounds %r differ from the plan %r by %.4f (different length/radius switches?)' % (box, plan['meshLocalBoundsCm'], error))
    slots = len(mesh.get_editor_property('static_materials'))
    if slots == 0 or any(helper._asset_path(mesh.get_material(s)) != poles['material'] for s in range(slots)):
        raise RuntimeError('Saved pole mesh material is not the gold material')
    info = {'asset': poles['meshAsset'], 'reused': True, 'triangles': mesh.get_num_triangles(0), 'localBoundsCm': box, 'boundsErrorCm': error,
            'materialSlots': slots, 'material': poles['material'], 'uassetSha256': _uasset_sha(helper, poles['meshAsset'])}
    receipt['poleMesh'] = info
    return mesh, info


# --------------------------------------------------------------------------
# Engine side: map
# --------------------------------------------------------------------------

def find_unique(run_state, label):
    rows = [r for r in run_state.snapshot if r['label'] == label]
    if len(rows) != 1:
        raise RuntimeError('Expected exactly one actor labelled %s, found %d' % (label, len(rows)))
    return rows[0]


def verify_body_actor(spec, helper, run_state):
    aron = spec['aronActors']
    row = find_unique(run_state, aron['bodyLabel'])
    if row['meshes'] != [spec['bodyMesh']['asset']]:
        raise RuntimeError('%s carries %s, expected the original body mesh (already swapped?)' % (aron['bodyLabel'], row['meshes']))
    close, error = helper._pose_close(row['pose'], aron['body']['location'], aron['body']['rotation'], aron['body']['scale'], aron['poseToleranceCm'])
    if not close:
        raise RuntimeError('%s pose differs from the rotate receipt by %.4f' % (aron['bodyLabel'], error))
    if helper.box_error(row['bounds'], aron['body']['worldBoundsCm']) > aron['boundsToleranceCm']:
        raise RuntimeError('%s bounds differ from the rotate receipt: %r' % (aron['bodyLabel'], row['bounds']))
    if row['folder'] != aron['folder']:
        raise RuntimeError('%s is in folder %s, expected %s' % (aron['bodyLabel'], row['folder'], aron['folder']))
    lid = find_unique(run_state, aron['lidLabel'])
    close, error = helper._pose_close(lid['pose'], aron['lid']['location'], aron['lid']['rotation'], aron['lid']['scale'], aron['poseToleranceCm'])
    if not close:
        raise RuntimeError('%s pose differs from the rotate receipt by %.4f' % (aron['lidLabel'], error))
    return row, lid


def verify_paroches(spec, helper, run_state, plan):
    paroches = spec['poles']['paroches']
    cloth = find_unique(run_state, paroches['clothLabel'])
    if cloth['meshes'] != [paroches['clothMesh']]:
        raise RuntimeError('Paroches cloth actor carries %s' % cloth['meshes'])
    if helper.box_error(cloth['bounds'], paroches['clothWorldBoundsCm']) > paroches['boundsToleranceCm']:
        raise RuntimeError('Paroches cloth bounds differ from the doors receipt: %r' % cloth['bounds'])
    if not (cloth['bounds']['min'][0] < plan['eastEndX'] < cloth['bounds']['max'][0]):
        raise RuntimeError('Pole east end %.2f is outside the measured cloth X range' % plan['eastEndX'])
    hem = find_unique(run_state, paroches['hemLabel'])
    if hem['meshes'] != [paroches['hemMesh']]:
        raise RuntimeError('Paroches hem actor carries %s' % hem['meshes'])
    return {'clothLabel': cloth['label'], 'clothBounds': cloth['bounds'], 'hemLabel': hem['label'], 'hemBounds': hem['bounds'],
            'measuredClothPenetrationCm': plan['eastEndX'] - cloth['bounds']['min'][0]}


def expected_body_bounds_after_swap(spec, no_poles_box):
    body = spec['aronActors']['body']
    scale = body['scale'][0]
    return {'min': [body['location'][i] + no_poles_box['min'][i] * scale for i in range(3)],
            'max': [body['location'][i] + no_poles_box['max'][i] * scale for i in range(3)]}


def swap_and_place(ue, spec, helper, vessels, run_state, receipt, body_row, no_poles_mesh, no_poles_box, pole_mesh, plan):
    """Clearance, body mesh swap and the two pole actors; nothing is saved here."""
    tolerance = spec['verification']['staticBoundsToleranceCm']
    paroches = spec['poles']['paroches']
    clearance = vessels.VesselPlacement(ue, spec, helper, run_state, receipt)
    # The body is excluded here because its snapshot AABB still includes the model poles (Y +-90);
    # it is checked against the poles AFTER the swap below.
    excluded = {paroches['clothLabel'], paroches['hemLabel'], body_row['label']}
    candidates, boxes_by_key = clearance.clearance_candidates(excluded)
    blockers = {}
    for key, actor in plan['actors'].items():
        hits = clearance.blockers_for(actor['plannedWorldBoundsCm'], candidates, boxes_by_key)
        if hits:
            blockers[actor['label']] = hits
    receipt['clearance']['blockers'] = blockers
    receipt['clearance']['intentionalIntersections'] = sorted(excluded)
    if blockers:
        raise RuntimeError('Planned pole AABBs intersect existing actors; nothing saved: %s' % blockers)

    component = body_row['actor'].get_component_by_class(ue.StaticMeshComponent)
    if component is None or not component.set_static_mesh(no_poles_mesh):
        raise RuntimeError('set_static_mesh failed on ' + body_row['label'])
    if helper._asset_path(component.get_editor_property('static_mesh')) != spec['bodyMesh']['noPolesAsset']:
        raise RuntimeError('Body static mesh readback differs after the swap')
    expected = expected_body_bounds_after_swap(spec, no_poles_box)
    swapped_bounds = helper._actor_bounds(body_row['actor'])
    swap_error = helper.box_error(swapped_bounds, expected)
    if swap_error > tolerance:
        raise RuntimeError('Body bounds after swap %r differ from the expectation %r by %.4f' % (swapped_bounds, expected, swap_error))
    pose_after = helper._actor_pose(body_row['actor'])
    close, error = helper._pose_close(pose_after, body_row['pose']['location'], body_row['pose']['rotation'], body_row['pose']['scale'],
                                      spec['verification']['transformToleranceCm'])
    if not close:
        raise RuntimeError('Body pose moved during the swap by %.4f' % error)
    for actor in plan['actors'].values():
        if helper.boxes_overlap_volume(actor['plannedWorldBoundsCm'], swapped_bounds):
            component.set_static_mesh(ue.load_asset(spec['bodyMesh']['asset']))
            raise RuntimeError('%s AABB overlaps the pole-less body AABB %r' % (actor['label'], swapped_bounds))
    receipt['bodySwap'] = {'label': body_row['label'], 'meshBefore': spec['bodyMesh']['asset'], 'meshAfter': spec['bodyMesh']['noPolesAsset'],
                           'pose': pose_after, 'worldBoundsBefore': body_row['bounds'], 'worldBoundsAfter': swapped_bounds,
                           'boundsErrorCm': swap_error, 'lengthBeforeCm': body_row['bounds']['max'][1] - body_row['bounds']['min'][1],
                           'lengthAfterCm': swapped_bounds['max'][1] - swapped_bounds['min'][1]}

    records = []
    placed = []
    try:
        for key in ('north', 'south'):
            actor_plan = plan['actors'][key]
            tags = ['ReleaseAronPoles', 'pole_' + key, spec['poles']['meshAsset'].rsplit('/', 1)[1]]
            actor, _component = run_state.spawn_static(pole_mesh, actor_plan['location'], actor_plan['rotation'], actor_plan['label'],
                                                       spec['folder'], spec['collisionProfile'], tags)
            placed.append(actor)
            pose = helper._actor_pose(actor)
            close, error = helper._pose_close(pose, actor_plan['location'], actor_plan['rotation'], actor_plan['scale'],
                                              spec['verification']['transformToleranceCm'])
            if not close:
                raise RuntimeError('%s pose differs from plan by %.4f' % (actor_plan['label'], error))
            bounds = helper._actor_bounds(actor)
            bounds_error = helper.box_error(bounds, actor_plan['plannedWorldBoundsCm'])
            if bounds_error > tolerance:
                raise RuntimeError('%s bounds differ from plan by %.4f: %r' % (actor_plan['label'], bounds_error, bounds))
            records.append({'label': actor_plan['label'], 'kind': 'StaticMeshActor', 'role': 'pole_' + key, 'mesh': spec['poles']['meshAsset'],
                            'location': actor_plan['location'], 'rotation': actor_plan['rotation'], 'scale': actor_plan['scale'],
                            'collisionProfile': spec['collisionProfile'], 'plannedWorldBoundsCm': actor_plan['plannedWorldBoundsCm'],
                            'placedWorldBoundsCm': bounds, 'boundsErrorCm': bounds_error, 'actor': actor})
    except Exception:
        run_state.destroy_all(placed)
        component.set_static_mesh(ue.load_asset(spec['bodyMesh']['asset']))
        raise
    return records


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def _strip(record):
    return {k: v for k, v in record.items() if k != 'actor'}


def fresh_receipt_path(spec):
    for _ in range(10):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path = ROOT / spec['receiptFolder'] / (spec['receiptPrefix'] + stamp + '.json')
        if not path.exists():
            return stamp, path
    raise RuntimeError('Could not allocate a fresh receipt stamp')


def run(mesh_only=False, place_only=False, delete_rings=False, east_end_x=None, west_stub_cm=None):
    import unreal as ue
    if mesh_only and place_only:
        raise RuntimeError('-AronPolesMeshOnly and -AronPolesPlaceOnly are mutually exclusive')
    spec = load_spec()
    helper, vessels = load_helpers(spec)
    offline = offline_check(spec, expect_meshes=place_only, delete_rings=delete_rings, east_end_x=east_end_x, west_stub_cm=west_stub_cm)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before the run')
    for name in ('GeometryScript_AssetUtils', 'GeometryScript_MeshQueries', 'GeometryScript_MeshEdits', 'GeometryScript_Primitives'):
        if not hasattr(ue, name):
            raise RuntimeError('GeometryScripting not loaded (%s missing); launch with -EnablePlugins=GeometryScripting' % name)

    stamp, receipt_path = fresh_receipt_path(spec)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnown': map_sha_before == spec['lastKnownMapSha256'], 'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'engineVersion': ue.SystemLibrary.get_engine_version(),
        'offlineCheck': offline,
        'switches': {'meshOnly': mesh_only, 'placeOnly': place_only, 'deleteRings': delete_rings, 'eastEndX': east_end_x, 'westStubCm': west_stub_cm},
        'license': {'source': spec['source']['license'], 'derivative': spec['bodyMesh']['noPolesAsset'],
                    'attribution': 'SourceAssets/third-party/ATTRIBUTION-additions.txt (ShareAlike: the pole-less duplicate stays CC BY-SA)'},
        'sources': spec['sources'], 'noPoles': {}, 'poleMesh': {}, 'plan': None, 'clearance': {}, 'bodySwap': None, 'placed': [],
        'errors': [], 'mapSaved': False, 'collisionProfile': spec['collisionProfile'], 'collisionNote': spec['collisionNote'],
        'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        # -- 1/2. meshes ---------------------------------------------------------------------
        if place_only:
            no_poles_mesh, no_poles_info = load_no_poles_mesh(ue, spec, helper, receipt, delete_rings)
        else:
            no_poles_mesh, no_poles_info = make_no_poles_mesh(ue, spec, helper, vessels, receipt, delete_rings)
        write()
        no_poles_box = no_poles_info['localBoundsCm']
        plan = plan_poles(spec, no_poles_box, east_end_x, west_stub_cm)
        receipt['plan'] = plan
        if place_only:
            pole_mesh, _ = load_pole_mesh(ue, spec, helper, receipt, plan)
        else:
            pole_mesh, _ = make_pole_mesh(ue, spec, helper, receipt, plan)
        receipt['status'] = 'meshes_verified' if place_only else 'meshes_saved'
        write()
        if mesh_only:
            receipt['status'] = 'meshes_saved_mesh_only_no_map_change'
            return receipt

        # -- 3. map guards + checkpoint --------------------------------------------------------
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map' % world.get_outermost().get_name())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present after loading the map')
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[len('/Game/'):]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[len('/Game/'):])
        receipt['checkpoint'] = str(checkpoint)

        run_state = helper.Placement(ue, spec)
        run_state.world = world
        run_state.receipt = receipt
        run_state.receipt_path = receipt_path
        run_state.take_snapshot()
        baseline = run_state.numeric_baseline(run_state.snapshot)
        pole_labels = set(spec['poles']['labels'].values())
        clashes = [r['label'] for r in run_state.snapshot if r['label'] in pole_labels or r['label'].startswith('RELEASE_Aron_Pole')
                   or spec['poles']['meshAsset'] in r['meshes'] or spec['bodyMesh']['noPolesAsset'] in r['meshes']]
        if clashes:
            raise RuntimeError('Pole actors or pole-less body already in the map; refusing: %s' % clashes[:10])
        body_row, lid_row = verify_body_actor(spec, helper, run_state)
        receipt['parochesCheck'] = verify_paroches(spec, helper, run_state, plan)
        receipt['lidUnchanged'] = {'label': lid_row['label'], 'pose': lid_row['pose'], 'bounds': lid_row['bounds']}
        receipt['actorCountBefore'] = len(run_state.snapshot)
        write()

        # -- 4. swap, place, save, reopen, read back --------------------------------------------
        records = swap_and_place(ue, spec, helper, vessels, run_state, receipt, body_row, no_poles_mesh, no_poles_box, pole_mesh, plan)
        receipt['placed'] = [_strip(r) for r in records]
        write()
        current = run_state.numeric_baseline(run_state.take_snapshot())
        body_name = body_row['name']
        changed = [name for name, row in baseline.items() if name != body_name and current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])
        if current[body_name][0] != body_row['label'] or current[body_name][2] != baseline[body_name][2]:
            raise RuntimeError('Body label or pose changed by the swap')
        if not levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha256_of(map_file)
        write()

        if not levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run_state.world = editor.get_editor_world()
        reopened = run_state.take_snapshot()
        reopened_numeric = run_state.numeric_baseline(reopened)
        changed = [name for name, row in baseline.items() if name != body_name and reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])
        verify = spec['verification']
        readback = []
        body_after = find_unique(run_state, spec['aronActors']['bodyLabel'])
        if body_after['meshes'] != [spec['bodyMesh']['noPolesAsset']]:
            raise RuntimeError('Reopened body carries %s' % body_after['meshes'])
        if helper.box_error(body_after['bounds'], receipt['bodySwap']['worldBoundsAfter']) > verify['staticBoundsToleranceCm']:
            raise RuntimeError('Reopened body bounds differ: %r' % body_after['bounds'])
        close, error = helper._pose_close(body_after['pose'], body_row['pose']['location'], body_row['pose']['rotation'], body_row['pose']['scale'],
                                          verify['transformToleranceCm'])
        if not close:
            raise RuntimeError('Reopened body pose differs by %.4f' % error)
        readback.append({'label': body_after['label'], 'folder': body_after['folder'], 'meshPath': body_after['meshes'], 'pose': body_after['pose'],
                         'worldBoundsCm': body_after['bounds'], 'poseErrorCm': error})
        for record in records:
            row = find_unique(run_state, record['label'])
            close, error = helper._pose_close(row['pose'], record['location'], record['rotation'], record['scale'], verify['transformToleranceCm'])
            bounds_error = helper.box_error(row['bounds'], record['plannedWorldBoundsCm'])
            component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
            readback.append({'label': record['label'], 'folder': row['folder'], 'meshPath': row['meshes'], 'pose': row['pose'],
                             'worldBoundsCm': row['bounds'], 'poseErrorCm': error, 'boundsErrorCm': bounds_error,
                             'collisionProfile': str(component.get_collision_profile_name()),
                             'materials': [helper._asset_path(component.get_material(i)) for i in range(component.get_num_materials())]})
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)' % (record['label'], error, bounds_error))
        receipt['reopenedReadback'] = readback
        receipt['actorCountAfter'] = len(reopened)
        receipt['status'] = 'aron_poles_east_west_saved_reopened_visual_acceptance_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif place_only:
            receipt['status'] = 'failed_place_only_map_unchanged_saved_meshes_untouched'
        elif receipt['noPoles'] or receipt['poleMesh']:
            receipt['status'] = 'failed_partial_assets_preserved_map_unchanged'
        else:
            receipt['status'] = 'failed_before_any_change'
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(sha256_of(helper.disk_path(m, 'umap')) == v for m, v in protected.items())
        receipt['placedActorCount'] = len(receipt['placed'])
        write()


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
    return 'release_aron_poles.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _switches(tokens):
    east = None
    west = None
    for token in tokens:
        if token.startswith('-aronpoleseastendx='):
            east = float(token.split('=', 1)[1].strip('"'))
        elif token.startswith('-aronpolesweststubcm='):
            west = float(token.split('=', 1)[1].strip('"'))
    return dict(mesh_only='-aronpolesmeshonly' in tokens, place_only='-aronpolesplaceonly' in tokens,
                delete_rings='-aronpolesdeleterings' in tokens, east_end_x=east, west_stub_cm=west)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    tokens = command_line.split()
    try:
        receipt = run(**_switches(tokens))
        ue.log('release_aron_poles: %s placed %s body_swapped %s' % (receipt['status'], receipt.get('placedActorCount'), bool(receipt.get('bodySwap'))))
    except Exception as error:
        ue.log_error('release_aron_poles failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        import sys
        print(json.dumps(offline_check(delete_rings='--delete-rings' in sys.argv), indent=2))
elif _invoked_as_native_script():
    _main()

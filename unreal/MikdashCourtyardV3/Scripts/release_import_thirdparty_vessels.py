"""Guarded native import of two CC-licensed vessel models and their placement in the combined map,
replacing the rejected procedural Aron/keruvim and the TI-photo menorah study.

What it does, in order (every number comes from Scripts/release_import_thirdparty_vessels.spec.json,
which was filled from SourceAssets/third-party/*/provenance.json and an offline vertex parse):

  1. Guards: right project, no game world, no dirty packages, target namespace
     /Game/MikdashV3/ThirdParty/Vessels absent (or present for -VesselsPlaceOnly), the three
     frozen OBJ hashes intact, GPL folders never touched.
  2. Imports ark_box_with_poles.obj, ark_lid_with_keruvim.obj (davidgra11, CC BY-SA) and
     menorah.obj (Dahan Meir, CC BY) through the reviewed legacy OBJ adapter path (FbxFactory,
     same settings as the keilim/keruvim/reliefs/doors imports, build_nanite False), verifies
     triangle counts and bounds (the importer mirrors Y; recorded), assigns the EXISTING gold
     material to EVERY slot and saves the assets.
  3. Winding check (GeometryScript, needs -EnablePlugins=GeometryScripting): signed volume under
     UE's left-handed face-normal convention must be positive. A negative volume means the mesh
     is inside-out: the triangle order is reversed via GeometryScript (append_buffers_to_mesh +
     copy_mesh_to_static_mesh), the asset re-saved and re-checked; the flip is recorded.
  4. Loads /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough, refuses if any RELEASE_Aron_* /
     RELEASE_Menorah actor or the Release/Vessels folder exists, checkpoints the .umap to
     C:/Mikdash/Working-5.8/ReviewCheckpoints/Vessels-<stamp>/, finds EXACTLY the actors to
     remove (16 x REVIEW_AronIncomplete_*, RELEASE_Keruvim_1, REVIEW_TempleInstituteMenorahStudyV1)
     and the Kodesh/Heikhal floors, derives the transforms from the imported assets' measured
     bounds, checks clearance, destroys the old actors (recording label/folder/mesh/pose/bounds),
     spawns RELEASE_Aron_Body, RELEASE_Aron_Lid, RELEASE_Menorah with uniform scales, saves,
     reopens, reads back numerically and writes
     SourceAssets/third-party/native-import-vessels-<stamp>.json (written at start and in finally).

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_import_thirdparty_vessels.py"
      -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Vessels-01.log"

Optional switches (read from the engine command line):
  -VesselsImportOnly              import + materials + winding check, no map change.
  -VesselsPlaceOnly               skip the import; the three meshes must already exist in the
                                  namespace (re-verified: bounds, triangles, materials, winding).
  -VesselsAllowUnverifiedWinding  place even if the winding check is unavailable/failed.
  -VesselsAronLengthNorthSouth    Aron yaw 0 (length AND poles north-south) instead of the default
                                  poles-east-west yaw 90 (see spec placement.aron.orientationRuleNote).
  -VesselsLidOnTop                lid bottom plane on the body top instead of seating the lip
                                  inside the box.

Offline (no engine):  python Scripts/release_import_thirdparty_vessels.py  -> prints offline_check():
hashes, plain-Python OBJ vertex/face parse (bounds, right-handed signed volume, lid lip and body-top
geometry) and the computed transforms (yaws, scales, menorah y, lid Z, planned world AABBs).

Risks: ~1.0 M source triangles (715k body + 287k lid) through the FBX/OBJ importer without Nanite.
The import and the GeometryScript readback are memory- and time-heavy on a 16 GB machine
(expect minutes per mesh and several GB); run nothing else native at the same time.

Reuses the pure helpers and the Placement snapshot/spawn utilities of
Scripts/release_place_assets.py so the release scripts share one set of rules.
"""
import hashlib
import importlib.util
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_import_thirdparty_vessels.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


# --------------------------------------------------------------------------
# Spec, shared helpers and pure planning (no unreal import)
# --------------------------------------------------------------------------

def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def load_placement_helper(spec):
    """Import Scripts/release_place_assets.py as a module without running its main."""
    path = ROOT / spec['placementHelper']
    module_spec = importlib.util.spec_from_file_location('release_place_assets', path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    for name in ('sha256_of', 'disk_path', 'box_from_min_max', 'box_error', 'rotate_box_yaw',
                 'boxes_overlap_volume', 'verify_union_decomposition', 'Placement', '_pose_close', '_actor_bounds'):
        if not hasattr(module, name):
            raise RuntimeError('release_place_assets.py lacks helper ' + name)
    return module


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scale_box(box, scale):
    return {'min': [v * scale for v in box['min']], 'max': [v * scale for v in box['max']]}


def reflect_y(box):
    return {'min': [box['min'][0], -box['max'][1], box['min'][2]], 'max': [box['max'][0], -box['min'][1], box['max'][2]]}


def box_inside(inner, outer, tolerance=0.0):
    return all(inner['min'][i] >= outer['min'][i] - tolerance and inner['max'][i] <= outer['max'][i] + tolerance for i in range(3))


def parse_obj(path):
    """Plain-Python OBJ parse: vertices [(x, y, z)], triangle index triples (fan-triangulated)."""
    vertices = []
    faces = []
    with open(path, 'r', errors='replace') as handle:
        for line in handle:
            if line.startswith('v '):
                parts = line.split()
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith('f '):
                indices = []
                for token in line.split()[1:]:
                    raw = int(token.split('/')[0])
                    indices.append(raw - 1 if raw > 0 else len(vertices) + raw)
                for k in range(1, len(indices) - 1):
                    faces.append((indices[0], indices[k], indices[k + 1]))
    return vertices, faces


def bounds_of(vertices):
    return {'min': [min(v[i] for v in vertices) for i in range(3)], 'max': [max(v[i] for v in vertices) for i in range(3)]}


def right_handed_signed_volume(vertices, faces):
    """Divergence-theorem volume with the right-handed normal cross(B-A, C-A); positive = outward."""
    total = 0.0
    for a, b, c in faces:
        ax, ay, az = vertices[a]
        bx, by, bz = vertices[b]
        cx, cy, cz = vertices[c]
        ux, uy, uz = bx - ax, by - ay, bz - az
        wx, wy, wz = cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        total += ax * nx + ay * ny + az * nz
    return total / 6.0


def lid_lip_analysis(lid_vertices, lid_faces, body_vertices, body_faces, lid_spec, body_top):
    """Geometry the lid seating rule depends on; every number is compared with the spec."""
    min_z = lid_spec['lipDetectionMinZFileUnits']
    lip_height = min(v[2] for v in lid_vertices if v[2] > min_z)
    lip = [v for v in lid_vertices if v[2] < lip_height - lid_spec['toleranceFileUnits']]
    lip_half = [max(abs(v[0]) for v in lip), max(abs(v[1]) for v in lip)]
    z0, z1 = lid_spec['bodyInnerProbeZFileUnits']
    inner_x = min(abs(v[0]) for v in body_vertices if z0 < v[2] < z1 and abs(v[1]) < 30.0)
    inner_y = min(abs(v[1]) for v in body_vertices if z0 < v[2] < z1 and abs(v[0]) < 15.0)
    interior_top = 0
    rim_top = 0
    for a, b, c in body_faces:
        corners = (body_vertices[a], body_vertices[b], body_vertices[c])
        if min(v[2] for v in corners) > body_top - 1.0:
            cx = sum(v[0] for v in corners) / 3.0
            cy = sum(v[1] for v in corners) / 3.0
            if abs(cx) < 15.0 and abs(cy) < 30.0:
                interior_top += 1
            else:
                rim_top += 1
    return {'lipHeightFileUnits': lip_height, 'lipVertexCount': len(lip), 'lipFootprintHalfFileUnits': lip_half,
            'bodyInnerHalfFileUnits': [inner_x, inner_y], 'bodyTopInteriorTriangles': interior_top,
            'bodyTopRimTriangles': rim_top, 'lipClearanceFileUnits': [inner_x - lip_half[0], inner_y - lip_half[1]]}


def plan_transforms(spec, local_boxes, floor_top_kodesh, floor_top_heikhal, aron_rule=None, lid_on_top=False):
    """Actor transforms and planned world AABBs from the (engine or file) local boxes.

    local_boxes: {'aronBody': box, 'aronLid': box, 'menorah': box} in asset units (file mm read as cm).
    """
    aron = spec['placement']['aron']
    menorah = spec['placement']['menorah']
    rule = aron_rule or aron['orientationRule']
    if rule not in aron['yawByRule']:
        raise RuntimeError('Unknown Aron orientation rule ' + rule)
    yaw = float(aron['yawByRule'][rule])
    scale = float(aron['scale'])
    origin = [aron['origin'][0], aron['origin'][1], floor_top_kodesh]
    body_local = scale_box(local_boxes['aronBody'], scale)
    if abs(body_local['min'][2]) > spec['source']['boundsToleranceCm']:
        raise RuntimeError('Aron body local min Z is not 0: %r' % body_local['min'])
    body_top_world = origin[2] + body_local['max'][2]
    lip_drop = 0.0 if lid_on_top else float(aron['lid']['lipHeightFileUnits']) * scale
    lid_location = [origin[0], origin[1], body_top_world - lip_drop]
    lid_local = scale_box(local_boxes['aronLid'], scale)
    if abs(lid_local['min'][2]) > spec['source']['boundsToleranceCm']:
        raise RuntimeError('Aron lid local min Z is not 0: %r' % lid_local['min'])
    body_world = _rotate(body_local, origin, yaw)
    lid_world = _rotate(lid_local, lid_location, yaw)

    m_scale = float(menorah['scale'])
    m_yaw = float(menorah['yaw'])
    m_local = scale_box(local_boxes['menorah'], m_scale)
    at_zero = _rotate(m_local, [0.0, 0.0, 0.0], m_yaw)
    tip_extent_south = at_zero['max'][1]
    y = float(menorah['southWallY']) - float(menorah['nearestTipClearanceCm']) - tip_extent_south
    z = floor_top_heikhal - m_local['min'][2]
    m_location = [float(menorah['x']), y, z]
    m_world = _rotate(m_local, m_location, m_yaw)
    return {
        'aronOrientationRule': rule,
        'lidSeating': 'lid_bottom_on_body_top' if lid_on_top else aron['lid']['seating'],
        'actors': {
            'body': {'label': aron['bodyLabel'], 'role': 'aronBody', 'location': origin, 'rotation': [0.0, yaw, 0.0],
                     'scale': [scale] * 3, 'plannedWorldBoundsCm': body_world, 'room': 'kodesh'},
            'lid': {'label': aron['lidLabel'], 'role': 'aronLid', 'location': lid_location, 'rotation': [0.0, yaw, 0.0],
                    'scale': [scale] * 3, 'plannedWorldBoundsCm': lid_world, 'room': 'kodesh',
                    'lipDropCm': lip_drop, 'bodyTopWorldZ': body_top_world},
            'menorah': {'label': menorah['label'], 'role': 'menorah', 'location': m_location, 'rotation': [0.0, m_yaw, 0.0],
                        'scale': [m_scale] * 3, 'plannedWorldBoundsCm': m_world, 'room': 'heikhal',
                        'nearestTipToSouthWallCm': float(menorah['southWallY']) - m_world['max'][1],
                        'baseBottomZ': m_world['min'][2]},
        },
        'derived': {'aronYaw': yaw, 'aronScale': scale, 'bodySizeCm': [body_world['max'][i] - body_world['min'][i] for i in range(3)],
                    'lidSizeCm': [lid_world['max'][i] - lid_world['min'][i] for i in range(3)], 'menorahY': y,
                    'menorahZ': z, 'menorahScale': m_scale, 'menorahYaw': m_yaw,
                    'menorahSizeCm': [m_world['max'][i] - m_world['min'][i] for i in range(3)],
                    'menorahHeightCm': m_world['max'][2] - m_world['min'][2]},
    }


def _rotate(local, location, yaw_degrees):
    """Same maths as release_place_assets.rotate_box_yaw (kept local so offline_check has no import order issue)."""
    yaw = math.radians(yaw_degrees)
    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)
    corners = []
    for x in (local['min'][0], local['max'][0]):
        for y in (local['min'][1], local['max'][1]):
            for z in (local['min'][2], local['max'][2]):
                corners.append((location[0] + x * cos_yaw - y * sin_yaw, location[1] + x * sin_yaw + y * cos_yaw, location[2] + z))
    return {'min': [min(c[i] for c in corners) for i in range(3)], 'max': [max(c[i] for c in corners) for i in range(3)]}


def check_rooms(spec, plan):
    envelopes = spec['placement']['clearance']['roomEnvelope']
    for key, actor in plan['actors'].items():
        if not box_inside(actor['plannedWorldBoundsCm'], envelopes[actor['room']]):
            raise RuntimeError('%s planned AABB leaves the %s envelope: %r' % (actor['label'], actor['room'], actor['plannedWorldBoundsCm']))


def offline_check(spec=None, namespace_expected=None, aron_rule=None, lid_on_top=False, parse_faces=True):
    """Consistency checks that need no engine. Raises on the first failure.

    namespace_expected: False for a fresh import (folder must be absent), True for
    -VesselsPlaceOnly (folder must exist), None to record the state only.
    parse_faces: also compute the right-handed signed volumes and the lid/body geometry
    (about a minute in plain Python for the 1M-triangle pair).
    """
    spec = spec or load_spec()
    helper = load_placement_helper(spec)
    source = spec['source']
    report = {'sourceFiles': [], 'materialsOnDisk': {}, 'excludedGplFoldersUntouched': []}

    manifest = json.loads((ROOT / source['thirdPartyManifest']).read_text(encoding='utf-8'))
    by_slug = {a['slug']: a for a in manifest['assets']}
    for folder in source['excludedFolders']:
        entry = by_slug.get(folder)
        if entry is None or 'GPL' not in entry['licenseName']:
            raise RuntimeError('Excluded folder is not the GPL entry expected: ' + folder)
        report['excludedGplFoldersUntouched'].append(folder)

    parsed = {}
    for record in source['meshes']:
        if record['slug'] in source['excludedFolders']:
            raise RuntimeError('Spec mesh comes from an excluded GPL folder: ' + record['name'])
        folder = ROOT / source['folder'] / record['slug']
        provenance = json.loads((folder / 'provenance.json').read_text(encoding='utf-8'))
        file_entry = [f for f in provenance['files'] if f['file'] == record['file']]
        mesh_entry = [m for m in provenance['meshes'] if m['file'] == record['file']]
        if len(file_entry) != 1 or len(mesh_entry) != 1:
            raise RuntimeError('provenance.json lacks ' + record['file'])
        if not (folder / 'LICENSE.txt').exists():
            raise RuntimeError('LICENSE.txt missing for ' + record['slug'])
        path = folder / record['file']
        actual_sha = sha256_of(path)
        if actual_sha != record['sha256'] or file_entry[0]['sha256'] != record['sha256']:
            raise RuntimeError('Frozen OBJ hash differs for ' + record['name'])
        if mesh_entry[0]['triangles'] != record['triangles']:
            raise RuntimeError('Triangle count differs from provenance for ' + record['name'])
        manifest_entry = by_slug[record['slug']]
        if not any(m['file'] == record['file'] for m in manifest_entry['meshes']):
            raise RuntimeError('third-party-manifest.json lacks ' + record['file'])
        if not any(word in manifest_entry['licenseName'] for word in ('Attribution', 'CC BY')) or 'GPL' in manifest_entry['licenseName']:
            raise RuntimeError('Unexpected license for ' + record['slug'])

        vertices, faces = parse_obj(path)
        box = bounds_of(vertices)
        provenance_box = {'min': mesh_entry[0]['bboxMin'], 'max': mesh_entry[0]['bboxMax']}
        error_spec = helper.box_error(box, record['sourceBoundsFileUnits'])
        error_provenance = helper.box_error(box, provenance_box)
        if error_spec > 1e-3 or error_provenance > 1e-3:
            raise RuntimeError('%s parsed bounds differ (spec %.5f, provenance %.5f): %r' % (record['name'], error_spec, error_provenance, box))
        if len(faces) != record['triangles'] or len(vertices) != record['vertices']:
            raise RuntimeError('%s parsed %d vertices / %d triangles, spec %d / %d' % (record['name'], len(vertices), len(faces), record['vertices'], record['triangles']))
        entry = {'name': record['name'], 'role': record['role'], 'file': str(path), 'sha256': actual_sha, 'triangles': len(faces),
                 'vertices': len(vertices), 'boundsFileUnits': box, 'license': record['license']}
        if parse_faces:
            entry['rightHandedSignedVolumeFileUnits3'] = right_handed_signed_volume(vertices, faces)
            if entry['rightHandedSignedVolumeFileUnits3'] <= 0:
                raise RuntimeError('%s right-handed signed volume is not positive: %.3f' % (record['name'], entry['rightHandedSignedVolumeFileUnits3']))
        parsed[record['role']] = (vertices, faces, box)
        report['sourceFiles'].append(entry)

    lid_spec = spec['placement']['aron']['lid']
    if parse_faces:
        body_vertices, body_faces, body_box = parsed['aronBody']
        lid_vertices, lid_faces, _ = parsed['aronLid']
        lip = lid_lip_analysis(lid_vertices, lid_faces, body_vertices, body_faces, lid_spec, body_box['max'][2])
        tolerance = lid_spec['toleranceFileUnits']
        if abs(lip['lipHeightFileUnits'] - lid_spec['lipHeightFileUnits']) > tolerance:
            raise RuntimeError('Lid lip height %.4f differs from spec %.4f' % (lip['lipHeightFileUnits'], lid_spec['lipHeightFileUnits']))
        if max(abs(lip['lipFootprintHalfFileUnits'][i] - lid_spec['lipFootprintHalfFileUnits'][i]) for i in range(2)) > tolerance:
            raise RuntimeError('Lid lip footprint differs from spec: %r' % lip['lipFootprintHalfFileUnits'])
        if max(abs(lip['bodyInnerHalfFileUnits'][i] - lid_spec['bodyInnerHalfFileUnits'][i]) for i in range(2)) > tolerance:
            raise RuntimeError('Body inner half-extents differ from spec: %r' % lip['bodyInnerHalfFileUnits'])
        if min(lip['lipClearanceFileUnits']) <= 0:
            raise RuntimeError('Lid lip does not fit inside the body: %r' % lip['lipClearanceFileUnits'])
        if lip['bodyTopInteriorTriangles'] != 0:
            raise RuntimeError('Body top is not open: %d interior triangles' % lip['bodyTopInteriorTriangles'])
        if abs(body_box['max'][2] - lid_spec['bodyTopFileUnits']) > 1e-3:
            raise RuntimeError('Body top differs from spec')
        report['lidSeatingGeometry'] = lip
    aron_spec = spec['placement']['aron']
    body_box = parsed['aronBody'][2]
    length_axis = 'X' if (body_box['max'][0] - body_box['min'][0]) > (body_box['max'][1] - body_box['min'][1]) else 'Y'
    if length_axis != aron_spec['lengthAxisLocal'] or aron_spec['polesAxisLocal'] != aron_spec['lengthAxisLocal']:
        raise RuntimeError('Aron length axis from bounds (%s) disagrees with spec (%s)' % (length_axis, aron_spec['lengthAxisLocal']))
    menorah_box = parsed['menorah'][2]
    fan_axis = 'X' if (menorah_box['max'][0] - menorah_box['min'][0]) > (menorah_box['max'][1] - menorah_box['min'][1]) else 'Y'
    if fan_axis != spec['placement']['menorah']['fanAxisLocal']:
        raise RuntimeError('Menorah fan axis from bounds (%s) disagrees with spec' % fan_axis)

    namespace_dir = ROOT / 'Content' / source['namespace'][len('/Game/'):]
    report['namespaceFolderExistsOnDisk'] = namespace_dir.exists()
    report['savedMeshFilesOnDisk'] = {m['name']: (namespace_dir / 'Meshes' / (m['name'] + '.uasset')).exists() for m in source['meshes']}
    if namespace_expected is False and namespace_dir.exists():
        raise RuntimeError('Target namespace folder already exists on disk: ' + str(namespace_dir))
    if namespace_expected is True and not all(report['savedMeshFilesOnDisk'].values()):
        raise RuntimeError('Place-only needs all three saved meshes on disk: %r' % report['savedMeshFilesOnDisk'])

    rows = []
    for candidate in spec['materials']['gold']['candidates']:
        rows.append({'path': candidate['path'], 'kind': candidate['kind'], 'onDisk': helper.disk_path(candidate['path']).exists()})
    if not any(r['onDisk'] for r in rows):
        raise RuntimeError('No gold material candidate exists on disk')
    report['materialsOnDisk']['gold'] = rows
    if not (ROOT / spec['targetMapFile']).exists():
        raise RuntimeError('Target map file missing')
    report['mapSha256OnDisk'] = sha256_of(ROOT / spec['targetMapFile'])
    report['mapMatchesLastKnown'] = report['mapSha256OnDisk'] == spec['lastKnownMapSha256']

    # Transforms predicted from the file bounds with the importer's Y mirror applied (the
    # engine run recomputes them from the imported assets' measured bounds).
    floors = spec['placement']['floors']
    predicted_local = {role: reflect_y(parsed[role][2]) for role in ('aronBody', 'aronLid', 'menorah')}
    plan = plan_transforms(spec, predicted_local, floors['kodesh']['topZ'], floors['heikhal']['topZ'], aron_rule, lid_on_top)
    check_rooms(spec, plan)
    unmirrored = plan_transforms(spec, {role: parsed[role][2] for role in predicted_local}, floors['kodesh']['topZ'],
                                 floors['heikhal']['topZ'], aron_rule, lid_on_top)
    plan['menorahYIfImporterDidNotMirror'] = unmirrored['derived']['menorahY']
    for key in ('body', 'lid'):
        planned = plan['actors'][key]['plannedWorldBoundsCm']
        if planned['max'][2] - planned['min'][2] > 2000:
            raise RuntimeError('Implausible vessel height')
    body = plan['actors']['body']['plannedWorldBoundsCm']
    lid = plan['actors']['lid']['plannedWorldBoundsCm']
    if not (body['min'][0] - 1.0 <= lid['min'][0] and lid['max'][0] <= body['max'][0] + 1.0 and body['min'][1] - 1.0 <= lid['min'][1] and lid['max'][1] <= body['max'][1] + 1.0):
        raise RuntimeError('Lid footprint leaves the body footprint (poles included): %r vs %r' % (lid, body))
    menorah_plan = plan['actors']['menorah']
    if abs(menorah_plan['nearestTipToSouthWallCm'] - spec['placement']['menorah']['nearestTipClearanceCm']) > 1e-6:
        raise RuntimeError('Menorah tip clearance arithmetic failed')
    if abs(menorah_plan['baseBottomZ'] - floors['heikhal']['topZ']) > 1e-6:
        raise RuntimeError('Menorah base is not on the floor')
    report['plan'] = plan
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side: import, materials, winding
# --------------------------------------------------------------------------

def _xyz(v):
    return [float(v.x), float(v.y), float(v.z)]


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _static_mesh_box(mesh):
    box = mesh.get_bounding_box()
    return {'min': _xyz(box.min), 'max': _xyz(box.max)}


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _uasset_sha(mesh):
    return sha256_of(ROOT / 'Content' / (_asset_path(mesh)[len('/Game/'):] + '.uasset'))


def pick_material(ue, spec, receipt):
    """First existing MaterialInterface among the gold candidates; records fallbacks."""
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tried = []
    for position, candidate in enumerate(spec['materials']['gold']['candidates']):
        exists = assets.does_asset_exist(candidate['path'])
        material = ue.load_asset(candidate['path']) if exists else None
        ok = isinstance(material, ue.MaterialInterface)
        tried.append({'path': candidate['path'], 'kind': candidate['kind'], 'exists': bool(exists), 'loaded': ok})
        if ok:
            if position > 0:
                receipt['limitations'].append('gold material fell back to %s (%s); preferred candidate missing' % (candidate['path'], candidate['kind']))
            receipt['materials']['gold'] = {'assigned': candidate['path'], 'kind': candidate['kind'], 'tried': tried}
            return material
    raise RuntimeError('No gold material candidate loads: %s' % tried)


def verify_mesh_geometry(spec, record, mesh, box, triangles):
    """Bounds must match the file bounds mirrored in Y (expected) or unmirrored (recorded); triangle loss bounded."""
    source = spec['source']
    expected_mirrored = reflect_y(record['sourceBoundsFileUnits'])
    error_mirrored = max(abs(box[k][i] - expected_mirrored[k][i]) for k in ('min', 'max') for i in range(3))
    error_plain = max(abs(box[k][i] - record['sourceBoundsFileUnits'][k][i]) for k in ('min', 'max') for i in range(3))
    if error_mirrored <= source['boundsToleranceCm']:
        mirrored = True
        error = error_mirrored
    elif error_plain <= source['boundsToleranceCm']:
        mirrored = False
        error = error_plain
    else:
        raise RuntimeError('%s bounds differ from the file bounds (mirrored %.4f, plain %.4f): %r' % (record['name'], error_mirrored, error_plain, box))
    lost = record['triangles'] - triangles
    if lost < 0 or lost > source['maxTriangleLossFraction'] * record['triangles']:
        raise RuntimeError('%s triangles %d differ from %d beyond the allowed loss' % (record['name'], triangles, record['triangles']))
    return {'boundsErrorCm': error, 'importerMirroredY': mirrored, 'trianglesLost': lost,
            'ambiguousMirror': error_plain <= source['boundsToleranceCm'] and error_mirrored <= source['boundsToleranceCm']}


def import_one_mesh(ue, spec, record, material):
    """OBJ -> StaticMesh through the reviewed adapter settings; verifies, assigns gold, saves."""
    source = spec['source']
    settings = spec['importSettings']
    path = ROOT / source['folder'] / record['slug'] / record['file']
    if sha256_of(path) != record['sha256']:
        raise RuntimeError('Frozen OBJ hash changed: ' + record['file'])

    ui = ue.FbxImportUI()
    for key, value in settings['fbxImportUI'].items():
        if key == 'mesh_type_to_import':
            value = getattr(ue.FBXImportType, value)
        ui.set_editor_property(key, value)
    data = ui.get_editor_property('static_mesh_import_data')
    for key, value in settings['staticMeshImportData'].items():
        if key == 'normal_import_method':
            value = getattr(ue.FBXNormalImportMethod, value)
        data.set_editor_property(key, value)

    task = ue.AssetImportTask()
    for key, value in dict(filename=str(path), destination_path=source['meshFolder'], destination_name=record['name'],
                           automated=True, async_=False, replace_existing=False, save=False, options=ui,
                           factory=ue.FbxFactory()).items():
        task.set_editor_property(key, value)
    started = datetime.now(timezone.utc)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    seconds = (datetime.now(timezone.utc) - started).total_seconds()
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
        raise RuntimeError('Import of %s produced %s' % (record['file'], [type(o).__name__ for o in objects]))
    mesh = objects[0]
    if mesh.get_name() != record['name']:
        raise RuntimeError('Imported name %s differs from destination_name %s' % (mesh.get_name(), record['name']))

    box = _static_mesh_box(mesh)
    triangles = mesh.get_num_triangles(0)
    geometry = verify_mesh_geometry(spec, record, mesh, box, triangles)

    slots = len(mesh.get_editor_property('static_materials'))
    for slot in range(slots):
        mesh.set_material(slot, material)
    not_assigned = [slot for slot in range(slots) if _asset_path(mesh.get_material(slot)) != _asset_path(material)]
    if slots == 0 or not_assigned:
        raise RuntimeError('Material slots not assigned on %s: %s of %d' % (record['name'], not_assigned, slots))
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + record['name'])
    info = {'asset': _asset_path(mesh), 'file': str(path), 'sourceTriangles': record['triangles'], 'triangles': triangles,
            'vertices': mesh.get_num_vertices(0), 'localBoundsCm': box, 'materialSlots': slots, 'material': _asset_path(material),
            'importSeconds': seconds, 'buildNanite': False, 'uassetSha256': _uasset_sha(mesh)}
    info.update(geometry)
    return mesh, info


def load_saved_mesh(ue, spec, record, receipt):
    """-VesselsPlaceOnly: load an already imported mesh and re-verify it instead of importing."""
    asset_path = spec['source']['meshFolder'] + '/' + record['name']
    mesh = ue.load_asset(asset_path)
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError('Saved mesh missing or not a StaticMesh: ' + asset_path)
    box = _static_mesh_box(mesh)
    triangles = mesh.get_num_triangles(0)
    geometry = verify_mesh_geometry(spec, record, mesh, box, triangles)
    allowed = {c['path']: c['kind'] for c in spec['materials']['gold']['candidates']}
    slots = len(mesh.get_editor_property('static_materials'))
    assigned = {_asset_path(mesh.get_material(slot)) for slot in range(slots)}
    wrong = sorted(str(p) for p in assigned if p not in allowed)
    if slots == 0 or wrong or len(assigned) != 1:
        raise RuntimeError('%s has %d slots; materials %s (outside spec: %s)' % (record['name'], slots, sorted(map(str, assigned)), wrong))
    material_path = assigned.pop()
    receipt['materials'].setdefault('gold', {'assigned': material_path, 'kind': allowed[material_path], 'verifiedOnSavedMesh': True})
    info = {'asset': _asset_path(mesh), 'file': None, 'sourceTriangles': record['triangles'], 'triangles': triangles,
            'vertices': mesh.get_num_vertices(0), 'localBoundsCm': box, 'materialSlots': slots, 'material': material_path,
            'reused': True, 'uassetSha256': _uasset_sha(mesh)}
    info.update(geometry)
    return mesh, info


def _source_dynamic_mesh(ue, mesh):
    dynamic = ue.DynamicMesh()
    options = ue.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property('apply_build_settings', False)
    options.set_editor_property('request_tangents', False)
    options.set_editor_property('use_build_scale', False)
    lod = ue.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
    if ue.GeometryScriptOutcomePins.SUCCESS not in result:
        raise RuntimeError('copy_mesh_from_static_mesh_v2 failed: ' + str(result))
    return dynamic


def _bulk_triangles(ue, dynamic):
    """(positions, triangles) as Python lists via the GeometryScript list API, or None if unavailable."""
    query = ue.GeometryScript_MeshQueries
    lists = getattr(ue, 'GeometryScript_List', None)
    if lists is None or not hasattr(query, 'get_all_vertex_positions') or not hasattr(query, 'get_all_triangle_indices'):
        return None
    try:
        position_result = query.get_all_vertex_positions(dynamic, ue.GeometryScriptVectorList(), False)
        triangle_result = query.get_all_triangle_indices(dynamic, ue.GeometryScriptTriangleList(), False)
        position_list = [v for v in position_result if isinstance(v, ue.GeometryScriptVectorList)]
        triangle_list = [t for t in triangle_result if isinstance(t, ue.GeometryScriptTriangleList)]
        if len(position_list) != 1 or len(triangle_list) != 1:
            return None
        positions = [_xyz(v) for v in lists.convert_vector_list_to_array(position_list[0])]
        triangles = [(int(t.x), int(t.y), int(t.z)) for t in lists.convert_triangle_list_to_array(triangle_list[0])]
    except Exception:  # noqa: BLE001 - API shape differs between engine builds; the per-triangle loop is the fallback
        return None
    if len(triangles) != dynamic.get_triangle_count() or len(positions) < dynamic.get_vertex_count():
        return None
    return positions, triangles


def winding_report(ue, mesh, spec):
    """Signed volume under UE's left-handed face-normal convention; positive means outward faces."""
    check = spec['windingCheck']
    needed = ('GeometryScript_AssetUtils', 'GeometryScript_MeshQueries')
    if not all(hasattr(ue, n) for n in needed):
        return {'status': 'unavailable', 'passed': False, 'signedVolumeUEcm3': None,
                'reason': 'GeometryScripting not loaded; launch with -EnablePlugins=GeometryScripting'}
    try:
        dynamic = _source_dynamic_mesh(ue, mesh)
    except RuntimeError as error:
        return {'status': 'copy_failed', 'passed': False, 'signedVolumeUEcm3': None, 'reason': str(error)}
    query = ue.GeometryScript_MeshQueries
    count = dynamic.get_triangle_count()
    flux = 0.0
    disagreements = 0
    sampled = 0
    bulk = _bulk_triangles(ue, dynamic)
    if bulk is not None:
        positions, triangles = bulk
        step = max(1, count // max(1, int(check['faceNormalSampleTriangles'])))
        for tid, (ia, ib, ic) in enumerate(triangles):
            a, b, c = positions[ia], positions[ib], positions[ic]
            ue_cross = _cross(_sub(c, a), _sub(b, a))
            flux += _dot(ue_cross, [(a[i] + b[i] + c[i]) / 3.0 for i in range(3)])
            if tid % step == 0:
                face = query.get_triangle_face_normal(dynamic, tid)
                normals = [_xyz(v) for v in face if isinstance(v, ue.Vector)] if isinstance(face, tuple) else [_xyz(face)]
                if len(normals) == 1:
                    sampled += 1
                    if _dot(ue_cross, normals[0]) < 0:
                        disagreements += 1
        method = 'bulk_lists_plus_sampled_face_normals'
        # flux accumulated with the unnormalised cross (2*area*n), so divide by 2 before /3.
        signed_volume = flux / 6.0
    else:
        for tid in range(count):
            positions = [_xyz(v) for v in query.get_triangle_positions(dynamic, tid) if isinstance(v, ue.Vector)]
            if len(positions) != 3:
                return {'status': 'read_failed', 'passed': False, 'signedVolumeUEcm3': None, 'reason': 'triangle %d has %d corners' % (tid, len(positions))}
            face = query.get_triangle_face_normal(dynamic, tid)
            normals = [_xyz(v) for v in face if isinstance(v, ue.Vector)] if isinstance(face, tuple) else [_xyz(face)]
            if len(normals) != 1:
                return {'status': 'read_failed', 'passed': False, 'signedVolumeUEcm3': None, 'reason': 'no face normal for triangle %d' % tid}
            a, b, c = positions
            ue_cross = _cross(_sub(c, a), _sub(b, a))
            sampled += 1
            if _dot(ue_cross, normals[0]) < 0:
                disagreements += 1
            flux += _dot(ue_cross, [(a[i] + b[i] + c[i]) / 3.0 for i in range(3)])
        method = 'per_triangle_loop'
        signed_volume = flux / 6.0
    passed = signed_volume > 0 and disagreements == 0 and sampled > 0
    return {'status': 'checked', 'passed': passed, 'method': method, 'triangles': count, 'signedVolumeUEcm3': signed_volume,
            'faceNormalSamples': sampled, 'faceNormalVsCrossDisagreements': disagreements,
            'passCriterion': 'signedVolumeUEcm3 > 0 and faceNormalVsCrossDisagreements == 0',
            'localBoundsCm': _static_mesh_box(mesh),
            'convention': 'UE left-handed face normal cross(C-A, B-A); volume by divergence theorem (asset units)'}


def flip_winding(ue, mesh, spec):
    """Rebuild LOD0 with reversed triangle order (GeometryScript) and write it back in place."""
    check = spec['windingCheck']
    dynamic = _source_dynamic_mesh(ue, mesh)
    bulk = _bulk_triangles(ue, dynamic)
    query = ue.GeometryScript_MeshQueries
    if bulk is not None:
        positions, triangles = bulk
        vertices = [ue.Vector(*p) for p in positions]
        reversed_triangles = [ue.IntVector(c, b, a) for a, b, c in triangles]
        uv0 = [ue.Vector2D(p[0] / 100.0, p[1] / 100.0) for p in positions]
        method = 'bulk_reversed_indices'
    else:
        vertices, reversed_triangles, uv0 = [], [], []
        for tid in range(dynamic.get_triangle_count()):
            positions = [_xyz(v) for v in query.get_triangle_positions(dynamic, tid) if isinstance(v, ue.Vector)]
            if len(positions) != 3:
                raise RuntimeError('triangle %d has %d corners' % (tid, len(positions)))
            base = len(vertices)
            for corner in (2, 1, 0):
                vertices.append(ue.Vector(*positions[corner]))
                uv0.append(ue.Vector2D(positions[corner][0] / 100.0, positions[corner][1] / 100.0))
            reversed_triangles.append(ue.IntVector(base, base + 1, base + 2))
        method = 'per_triangle_reversed_corners'
    buffers = ue.GeometryScriptSimpleMeshBuffers()
    buffers.set_editor_property('vertices', vertices)
    buffers.set_editor_property('triangles', reversed_triangles)
    buffers.set_editor_property('uv0', uv0)
    rebuilt = ue.DynamicMesh()
    ue.GeometryScript_MeshEdits.append_buffers_to_mesh(rebuilt, buffers)
    if rebuilt.get_triangle_count() != dynamic.get_triangle_count():
        raise RuntimeError('Rebuilt triangle count differs')
    options = ue.GeometryScriptCopyMeshToAssetOptions()
    for key, value in check['rewriteOptions'].items():
        options.set_editor_property(key, value)
    lod = ue.GeometryScriptMeshWriteLOD()
    lod.set_editor_property('write_hi_res_source', False)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(rebuilt, mesh, options, lod)
    if ue.GeometryScriptOutcomePins.SUCCESS not in result:
        raise RuntimeError('copy_mesh_to_static_mesh failed: ' + str(result))
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed after winding flip for ' + mesh.get_name())
    return {'method': method, 'rewriteOptions': check['rewriteOptions'], 'triangles': rebuilt.get_triangle_count()}


# --------------------------------------------------------------------------
# Engine side: removals and placement
# --------------------------------------------------------------------------

class VesselPlacement:
    """Removes the rejected review actors and places the three vessels in the loaded map."""

    def __init__(self, ue, spec, helper, run, receipt):
        self.ue = ue
        self.spec = spec
        self.helper = helper
        self.run = run            # release_place_assets.Placement (snapshot, spawn, destroy)
        self.receipt = receipt

    def find_floor(self, key):
        floors = self.spec['placement']['floors']
        rows = self.run.actors_with_mesh(floors[key]['mesh'])
        if len(rows) != 1:
            raise RuntimeError('Expected one %s clear floor actor, found %d' % (key, len(rows)))
        floor = rows[0]
        if self.helper.box_error(floor['bounds'], floors[key]['worldBoundsCm']) > floors['boundsToleranceCm']:
            raise RuntimeError('%s floor bounds differ from manifest: %r' % (key, floor['bounds']))
        if abs(floor['bounds']['max'][2] - floors[key]['topZ']) > floors['topToleranceCm']:
            raise RuntimeError('%s floor top %.3f differs from spec %.3f' % (key, floor['bounds']['max'][2], floors[key]['topZ']))
        return floor

    def find_removals(self):
        """Exactly the expected review actors, each with the expected mesh and pose; else refuse."""
        removals = self.spec['removals']
        tolerance = removals['poseToleranceCm']
        expected = []
        aron = removals['aronParts']
        for name in aron['partNames']:
            expected.append({'label': aron['labelPrefix'] + name, 'folder': aron['folder'], 'mesh': aron['meshPrefix'] + name,
                             'location': aron['sharedOrigin'], 'yaw': aron['yaw'], 'scale': aron['scale'], 'group': 'aronParts'})
        for key in ('keruvim', 'menorah'):
            entry = removals[key]
            expected.append({'label': entry['label'], 'folder': entry['folder'], 'mesh': entry['mesh'], 'location': entry['location'],
                             'yaw': entry['yaw'], 'scale': entry['scale'], 'group': key})
        found = []
        for item in expected:
            rows = [r for r in self.run.snapshot if r['label'] == item['label']]
            if len(rows) != 1:
                raise RuntimeError('Removal target %s: %d actors with that label' % (item['label'], len(rows)))
            row = rows[0]
            if row['meshes'] != [item['mesh']]:
                raise RuntimeError('Removal target %s carries mesh %s, expected %s' % (item['label'], row['meshes'], item['mesh']))
            if row['folder'] != item['folder']:
                raise RuntimeError('Removal target %s is in folder %s, expected %s' % (item['label'], row['folder'], item['folder']))
            close, error = self.helper._pose_close(row['pose'], item['location'], [0.0, item['yaw'], 0.0], item['scale'], tolerance)
            if not close:
                raise RuntimeError('Removal target %s pose differs from the recorded pose by %.4f' % (item['label'], error))
            found.append(dict(row, group=item['group']))
        stray = [r['label'] for r in self.run.snapshot if r['label'].startswith(aron['labelPrefix']) and r['label'] not in {i['label'] for i in expected}]
        stray += [r['label'] for r in self.run.snapshot if r['folder'] == aron['folder'] and r['label'] not in {i['label'] for i in expected}]
        if stray:
            raise RuntimeError('Unexpected extra Aron review actors: %s' % sorted(set(stray))[:10])
        return found

    def clearance_candidates(self, excluded_labels):
        clearance = self.spec['placement']['clearance']
        manifest = json.loads((ROOT / clearance['architectureManifest']).read_text(encoding='utf-8-sig'))
        entries = {e['assetName']: e for e in manifest['meshes']}
        prefix = clearance['levelAssetPrefix']
        boxes_by_key = {}
        candidates = []
        excluded_terrain = []
        for row in self.run.snapshot:
            if not row['meshes'] or row['label'] in excluded_labels:
                continue
            if any(row['folder'].startswith(f) for f in clearance['terrainFolders']) or \
                    any('/JerusalemContext/Terrain/' in (m or '') or '/FutureMountV1/Terrain/' in (m or '') for m in row['meshes']):
                excluded_terrain.append(row['label'])
                continue
            key = None
            if row['folder'] == clearance['unionFolder'] and len(row['meshes']) == 1 and (row['meshes'][0] or '').startswith(prefix):
                name = row['meshes'][0][len(prefix):]
                entry = entries.get(name)
                if entry is not None and entry.get('semantic') == 'union' and \
                        self.helper.box_error(row['bounds'], entry['expectedBoundsUnrealCm']) <= clearance['unionBoundsToleranceCm']:
                    boxes_by_key[name] = self.helper.verify_union_decomposition(entry, clearance['unionBoundsToleranceCm'])
                    key = name
            candidates.append({'label': row['label'], 'bounds': row['bounds'], 'unionKey': key})
        self.receipt['clearance'] = {'actorsConsidered': len(candidates), 'excludedActors': sorted(excluded_labels),
                                     'excludedTerrainTileCount': len(excluded_terrain),
                                     'unionsDecomposed': {k: len(v) for k, v in boxes_by_key.items()}}
        return candidates, boxes_by_key

    def blockers_for(self, planned, candidates, boxes_by_key):
        blockers = []
        for candidate in candidates:
            if not self.helper.boxes_overlap_volume(planned, candidate['bounds']):
                continue
            boxes = boxes_by_key.get(candidate['unionKey']) if candidate['unionKey'] else None
            if boxes is None:
                blockers.append({'label': candidate['label'], 'kind': 'actor_aabb'})
                continue
            hits = [b['name'] for b in boxes if self.helper.boxes_overlap_volume(planned, b)]
            if hits:
                blockers.append({'label': candidate['label'], 'kind': 'union_constituent_box', 'constituents': hits})
        return blockers

    def place(self, meshes, aron_rule, lid_on_top):
        ue = self.ue
        spec = self.spec
        tolerance = spec['verification']['staticBoundsToleranceCm']
        kodesh = self.find_floor('kodesh')
        heikhal = self.find_floor('heikhal')
        removals = self.find_removals()
        self.receipt['removed'] = [{'label': r['label'], 'name': r['name'], 'folder': r['folder'], 'meshes': r['meshes'], 'group': r['group'],
                                    'pose': r['pose'], 'worldBoundsCm': r['bounds']} for r in removals]
        local_boxes = {role: info['localBoundsCm'] for role, info in meshes.items()}
        plan = plan_transforms(spec, local_boxes, kodesh['bounds']['max'][2], heikhal['bounds']['max'][2], aron_rule, lid_on_top)
        check_rooms(spec, plan)
        self.receipt['plan'] = plan
        excluded = {kodesh['label'], heikhal['label']} | {r['label'] for r in removals}
        candidates, boxes_by_key = self.clearance_candidates(excluded)
        blockers = {}
        for key, actor in plan['actors'].items():
            hits = self.blockers_for(actor['plannedWorldBoundsCm'], candidates, boxes_by_key)
            if hits:
                blockers[actor['label']] = hits
        self.receipt['clearance']['blockers'] = blockers
        if blockers:
            raise RuntimeError('Planned vessel AABBs intersect existing actors; nothing saved: %s' % blockers)
        body_box = plan['actors']['body']['plannedWorldBoundsCm']
        lid_box = plan['actors']['lid']['plannedWorldBoundsCm']
        if lid_on_top and abs(lid_box['min'][2] - body_box['max'][2]) > tolerance:
            raise RuntimeError('Lid bottom does not meet the body top')

        # Removals happen in memory only; they persist only if the level is saved at the end.
        for row in removals:
            if not self.run.actors.destroy_actor(row['actor']):
                raise RuntimeError('destroy_actor returned False for ' + row['label'])
        self.receipt['removedCount'] = len(removals)

        records = []
        placed_actors = []
        try:
            for key in ('body', 'lid', 'menorah'):
                actor_plan = plan['actors'][key]
                info = meshes[actor_plan['role']]
                tags = ['ReleaseVessels', actor_plan['role'], info['asset'].rsplit('/', 1)[1]]
                actor, component = self.run.spawn_static(info['mesh'], actor_plan['location'], actor_plan['rotation'], actor_plan['label'],
                                                         spec['folder'], spec['collisionProfile'], tags)
                placed_actors.append(actor)
                actor.set_actor_scale3d(ue.Vector(*actor_plan['scale']))
                pose = self.helper._actor_pose(actor)
                close, error = self.helper._pose_close(pose, actor_plan['location'], actor_plan['rotation'], actor_plan['scale'],
                                                       spec['verification']['transformToleranceCm'])
                if not close:
                    raise RuntimeError('%s pose differs from plan by %.4f' % (actor_plan['label'], error))
                placed_bounds = self.helper._actor_bounds(actor)
                bounds_error = self.helper.box_error(placed_bounds, actor_plan['plannedWorldBoundsCm'])
                if bounds_error > tolerance:
                    raise RuntimeError('%s bounds differ from plan by %.4f: %r' % (actor_plan['label'], bounds_error, placed_bounds))
                records.append({'label': actor_plan['label'], 'kind': 'StaticMeshActor', 'role': actor_plan['role'], 'mesh': info['asset'],
                                'location': actor_plan['location'], 'rotation': actor_plan['rotation'], 'scale': actor_plan['scale'],
                                'collisionProfile': spec['collisionProfile'], 'plannedWorldBoundsCm': actor_plan['plannedWorldBoundsCm'],
                                'placedWorldBoundsCm': placed_bounds, 'boundsErrorCm': bounds_error, 'actor': actor})
        except Exception:
            self.run.destroy_all(placed_actors)
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


def run(import_only=False, allow_unverified_winding=False, place_only=False, aron_length_north_south=False, lid_on_top=False):
    """Import (or reuse), check winding, remove the old actors, place. Returns the receipt dict."""
    import unreal as ue
    if import_only and place_only:
        raise RuntimeError('-VesselsImportOnly and -VesselsPlaceOnly are mutually exclusive')
    spec = load_spec()
    helper = load_placement_helper(spec)
    aron_rule = 'length_north_south' if aron_length_north_south else spec['placement']['aron']['orientationRule']
    offline = offline_check(spec, namespace_expected=place_only, aron_rule=aron_rule, lid_on_top=lid_on_top)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before import')
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    namespace_exists = assets.does_directory_exist(spec['source']['namespace'])
    if place_only and not namespace_exists:
        raise RuntimeError('Place-only requested but namespace is missing: ' + spec['source']['namespace'])
    if not place_only and namespace_exists:
        raise RuntimeError('Existing native namespace preserved (use -VesselsPlaceOnly): ' + spec['source']['namespace'])

    stamp, receipt_path = fresh_receipt_path(spec)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnown': map_sha_before == spec['lastKnownMapSha256'],
        'protectedMapSha256Before': protected, 'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'offlineCheck': offline,
        'switches': {'importOnly': import_only, 'placeOnly': place_only, 'allowUnverifiedWinding': allow_unverified_winding,
                     'aronLengthNorthSouth': aron_length_north_south, 'lidOnTop': lid_on_top},
        'mode': 'place_only_reusing_saved_meshes' if place_only else 'import_and_place',
        'licenses': {m['name']: {'slug': m['slug'], 'license': m['license'], 'attribution': 'SourceAssets/third-party/ATTRIBUTION-additions.txt'}
                     for m in spec['source']['meshes']},
        'materials': {}, 'meshes': {}, 'windingCheck': {}, 'windingFlips': {}, 'removed': [], 'placed': [], 'errors': [],
        'mapSaved': False, 'collisionProfile': spec['collisionProfile'], 'collisionNote': spec['collisionNote'],
        'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        # -- 1. import + materials (or reuse the saved meshes) ------------------------------
        meshes = {}
        material = None if place_only else pick_material(ue, spec, receipt)
        for record in spec['source']['meshes']:
            if place_only:
                mesh, info = load_saved_mesh(ue, spec, record, receipt)
            else:
                mesh, info = import_one_mesh(ue, spec, record, material)
            info['mesh'] = mesh
            meshes[record['role']] = info
            receipt['meshes'][record['name']] = {k: v for k, v in info.items() if k != 'mesh'}
            write()
        receipt['status'] = 'meshes_verified' if place_only else 'meshes_saved'
        receipt['importerMirroredY'] = {name: m['importerMirroredY'] for name, m in receipt['meshes'].items()}

        # -- 2. winding (flip if inverted) ---------------------------------------------------
        all_passed = True
        for role, info in meshes.items():
            report = winding_report(ue, info['mesh'], spec)
            if report['status'] == 'checked' and report['signedVolumeUEcm3'] is not None and report['signedVolumeUEcm3'] < 0 \
                    and spec['windingCheck']['flipIfNegative']:
                flip = flip_winding(ue, info['mesh'], spec)
                flip['before'] = report
                report = winding_report(ue, info['mesh'], spec)
                flip['after'] = report
                info['localBoundsCm'] = _static_mesh_box(info['mesh'])
                info['triangles'] = info['mesh'].get_num_triangles(0)
                info['uassetSha256'] = _uasset_sha(info['mesh'])
                receipt['meshes'][info['mesh'].get_name()].update({k: v for k, v in info.items() if k != 'mesh'})
                receipt['windingFlips'][info['asset']] = flip
                receipt['limitations'].append('%s imported inside-out (negative UE signed volume); triangle order reversed via GeometryScript and normals recomputed' % info['asset'])
            receipt['windingCheck'][info['asset']] = report
            all_passed = all_passed and report['passed']
        receipt['windingVerifiedOutward'] = all_passed
        write()
        if import_only:
            receipt['status'] = 'meshes_saved_import_only_no_map_change'
            return receipt
        if not all_passed and spec['windingCheck']['requireForPlacement'] and not allow_unverified_winding:
            receipt['status'] = 'meshes_saved_placement_skipped_winding_unverified'
            receipt['limitations'].append('Placement skipped: winding check did not pass or was unavailable; rerun with '
                                          '-EnablePlugins=GeometryScripting (and -VesselsPlaceOnly) or inspect before -VesselsAllowUnverifiedWinding')
            return receipt
        if not all_passed:
            receipt['limitations'].append('Placed with UNVERIFIED winding by explicit switch')

        # -- 3. map guards + checkpoint -------------------------------------------------
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map' % world.get_outermost().get_name())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present after loading the map; resolve before checkpointed placement')
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
        own_labels = {spec['placement']['aron']['bodyLabel'], spec['placement']['aron']['lidLabel'], spec['placement']['menorah']['label']}
        clashes = [r['label'] for r in run_state.snapshot if r['label'] in own_labels or r['label'].startswith('RELEASE_Aron_')
                   or r['folder'] == spec['folder']]
        if clashes:
            raise RuntimeError('Existing vessel release actors preserved; refusing duplicate placement: %s' % clashes[:10])
        others = [r for r in run_state.snapshot if r['label'].startswith(spec['labelPrefix'])]
        receipt['preExistingReleaseActors'] = [{'label': r['label'], 'folder': r['folder'], 'meshes': r['meshes']} for r in others]
        receipt['actorCountBefore'] = len(run_state.snapshot)
        write()

        # -- 4. remove, place, save, reopen, read back ------------------------------------
        placement = VesselPlacement(ue, spec, helper, run_state, receipt)
        records = placement.place(meshes, aron_rule, lid_on_top)
        receipt['placed'] = [_strip(r) for r in records]
        write()
        removed_names = {r['name'] for r in receipt['removed']}
        current = run_state.numeric_baseline(run_state.take_snapshot())
        changed = [name for name, row in baseline.items() if name not in removed_names and current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])
        still_present = [name for name in removed_names if name in current]
        if still_present:
            raise RuntimeError('Removed actors still present before save: %s' % still_present[:10])
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
        changed = [name for name, row in baseline.items() if name not in removed_names and reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])
        removed_labels = {r['label'] for r in receipt['removed']}
        lingering = [r['label'] for r in reopened if r['label'] in removed_labels]
        if lingering:
            raise RuntimeError('Removed actors reappeared after reopen: %s' % lingering)
        verify = spec['verification']
        readback = []
        for record in records:
            matching = [r for r in reopened if r['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
            row = matching[0]
            close, error = helper._pose_close(row['pose'], record['location'], record['rotation'], record['scale'], verify['transformToleranceCm'])
            bounds_error = helper.box_error(row['bounds'], record['plannedWorldBoundsCm'])
            component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
            entry = {'label': record['label'], 'folder': row['folder'], 'meshPath': row['meshes'], 'pose': row['pose'],
                     'worldBoundsCm': row['bounds'], 'poseErrorCm': error, 'boundsErrorCm': bounds_error,
                     'collisionProfile': str(component.get_collision_profile_name()),
                     'materials': [_asset_path(component.get_material(i)) for i in range(component.get_num_materials())]}
            readback.append(entry)
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)' % (record['label'], error, bounds_error))
        receipt['reopenedReadback'] = readback
        receipt['actorCountAfter'] = len(reopened)
        receipt['status'] = 'vessels_saved_reopened_old_review_actors_removed_visual_acceptance_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif place_only:
            receipt['status'] = 'failed_place_only_map_unchanged_saved_meshes_untouched'
        elif receipt['meshes']:
            receipt['status'] = 'failed_partial_assets_preserved_map_unchanged'
        else:
            receipt['status'] = 'failed_before_import_nothing_changed'
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(sha256_of(helper.disk_path(m, 'umap')) == v for m, v in protected.items())
        receipt['placedActorCount'] = len(receipt['placed'])
        receipt['removedActorCount'] = len(receipt['removed'])
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
    return 'release_import_thirdparty_vessels.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    tokens = command_line.split()
    try:
        receipt = run(import_only='-vesselsimportonly' in tokens, allow_unverified_winding='-vesselsallowunverifiedwinding' in tokens,
                      place_only='-vesselsplaceonly' in tokens, aron_length_north_south='-vesselsaronlengthnorthsouth' in tokens,
                      lid_on_top='-vesselslidontop' in tokens)
        ue.log('release_import_thirdparty_vessels: %s placed %s removed %s winding_ok %s' % (
            receipt['status'], receipt.get('placedActorCount'), receipt.get('removedActorCount'), receipt.get('windingVerifiedOutward')))
    except Exception as error:
        ue.log_error('release_import_thirdparty_vessels failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

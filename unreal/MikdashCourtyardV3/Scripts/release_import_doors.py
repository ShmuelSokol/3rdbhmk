"""Guarded native import and placement of the DoorsParochesV1 study in the combined map.

What it does, in order (every number is read from Scripts/release_import_doors.spec.json,
the frozen source manifest and the frozen architecture manifest):

  1. Guards: right project, no game world, no dirty packages, target namespace
     /Game/MikdashV3/MaterialReview/DoorsParochesV1 absent, the nine frozen OBJ hashes
     intact (SourceAssets/sanctuary-detail/DoorsParochesV1/geometry-manifest.json and
     frozen-files.json agree with the files on disk).
  2. Imports the nine OBJ meshes through the reviewed legacy OBJ adapter path
     (FbxFactory with the exact settings of create_heikhal_keilim.run_native, also used by
     create_keruvim_study, create_aron_study_v1 and release_import_reliefs), verifies
     triangle counts and canonical bounds (the source OBJ carries Y reflected and winding
     reversed; the importer reflects Y back, and the asymmetric hardware/fixings bounds
     prove the round trip), assigns EXISTING materials to EVERY slot (the OBJ importer makes
     one slot per 'g' group; SM_KeruvimStudyV1 lesson) and saves the assets.
  3. Winding check (GeometryScript, needs -EnablePlugins=GeometryScripting): the divergence
     volume computed with UE face normals must be positive and agree with the sum of the
     manifest's closed part volumes. Without a passing check the meshes stay saved and
     nothing is placed (override with -DoorsAllowUnverifiedWinding, recorded).
  4. Loads /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough, refuses if any
     RELEASE_Doors_* actor exists, checkpoints the .umap to
     C:/Mikdash/Working-5.8/ReviewCheckpoints/Doors-<stamp>/, finds the measured opening
     actors (architecture_SM_0142/0143 Kodesh partition shoulders, SM_0144 Kodesh partition
     lintel, SM_0146/0147 clear floors, the House walls union SM_2630 decomposed into its
     source boxes for the Heichal doorway jambs and lintel), checks them against the frozen
     manifest, and derives the door openings from the LEVEL geometry.
  5. Places the leaves in their OPEN state (the book: the Kodesh doors are always open,
     opening inward; Middot 4:1 for the folding Heichal leaves) plus the paroches on the
     Heichal face of the Kodesh wall, verifies every planned AABB against the wall boxes,
     every mesh-bearing actor of the level and the y=0 walking corridor, saves, reopens,
     reads back numerically and writes
     SourceAssets/sanctuary-detail/DoorsParochesV1/native-import-<stamp>.json.

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_import_doors.py"
      -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Doors-01.log"

  Second run (meshes already imported and saved by Release-Doors-01, map unchanged):
      ... -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_import_doors.py"
      -DoorsPlaceOnly -DoorsGroups=kodesh,paroches -EnablePlugins=GeometryScripting
      -unattended -nullrhi -abslog="C:/Mikdash/Working-5.8/Release-Doors-02.log"

Optional switches (read from the engine command line):
  -DoorsImportOnly                import + materials + winding check, no map change.
  -DoorsPlaceOnly                 skip the import; the nine meshes must already exist in the
                                  namespace and match the manifest (bounds, triangles, one
                                  material slot per manifest part, every slot on the spec
                                  material). Nothing is re-assigned or re-saved.
  -DoorsGroups=heichal,kodesh,paroches   subset to place (default: spec defaultGroups =
                                  kodesh,paroches). Families not requested are not derived
                                  or asserted at all; the omission is recorded in the receipt
                                  (spec deliberateOmissions: the Heichal folding leaves are
                                  NOT placed because the measured architecture already
                                  carries four gold 'Open Heichal door' slabs).
  -DoorsAllowUnverifiedWinding    place even if the winding check is unavailable/failed.

Plan geometry comes from the EXACT manifest openings; the openings read from the level carry
float32 jitter (floor top 925.00006 instead of 925.0) and are only cross-checked against the
manifest within openings.boundsToleranceCm. JSON-vs-plan agreement (hinge Y on the jamb plane,
leaf bottom = floor + lift, 4 x nominal = opening width) uses doorPlan.planToleranceCm (0.5 cm),
never exact float equality: the first run failed on 927.0 != 925.00006 + 2.

Offline (no engine):
  python Scripts/release_import_doors.py               -> prints the offline check.
  python Scripts/release_import_doors.py --write-plan  -> recomputes the derived plan and
                                                          opening expectations into the spec.

Open-state derivation (also written into the spec as derivedPlan for review):
  * The placement JSON gives CLOSED hinge positions: Heichal banks at X -3325/-3575
    (25 cm inside each face of the 300 cm wall, Middot 4:1 R. Yehudah doorposts), Kodesh
    bank at X -5650 (middle of the 100 cm partition), hinge lines on the jamb planes
    Y = +-opening/2, leaf bottoms 2 cm above the floor.
  * Heichal: each jamb leaf + fold leaf pair is folded 180 degrees with the JSON fold
    formula (child translation (nominal + 8 sin a, 8 - 8 cos a, 0), relative yaw a) and
    the stack swings 90 degrees into the doorway to lie along the jamb reveal: the outer
    bank points west, the inner bank points east, so the two stacks cover the wall
    thickness between them (Middot 4:1, R. Yehudah: "these fold back two and a half
    amot and these two and a half amot"). Because both stacks would put their fold-line
    barrels at the same X -3450, each bank hinge is shifted bankHingeShiftCm toward its
    face; the shift is recorded.
  * Kodesh: the two leaves stay in line (175 cm door) and swing 90 degrees west into the
    Kodesh HaKodashim about the JSON hinge X, lying along the jamb reveal and continuing
    into the room (Lishchno Tidreshu pp. 60, 261: always open, probably inward).
  * The leaf meshes are not mirrored, so the second leaf always stacks on the hinge
    leaf's local +Y side. For each side the hinge Y is placed so the whole stack envelope
    sits jambGapCm inside the jamb plane; the visible envelopes are mirror-symmetric even
    though the hinge lines are not. No leaf ever enters a wall box.

Reuses the pure helpers and the Placement snapshot utilities of
Scripts/release_place_assets.py (AABB maths, union-of-boxes clearance, numeric readback).
"""
import hashlib
import importlib.util
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_import_doors.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
GROUP_ORDER = ('heichal', 'kodesh', 'paroches')


# --------------------------------------------------------------------------
# Spec, shared helpers and pure planning (no unreal import)
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
                 'boxes_overlap_volume', 'union_constituent_boxes', 'verify_union_decomposition',
                 '_pose_close', 'Placement'):
        if not hasattr(module, name):
            raise RuntimeError('release_place_assets.py lacks helper ' + name)
    return module


def normalise_groups(groups):
    if isinstance(groups, str):
        groups = groups.split(',')
    wanted = [g.strip().lower() for g in groups if g.strip()]
    unknown = [g for g in wanted if g not in GROUP_ORDER]
    if unknown:
        raise RuntimeError('Unknown door groups %s; valid: %s' % (unknown, list(GROUP_ORDER)))
    if not wanted:
        raise RuntimeError('No door groups requested')
    return tuple(g for g in GROUP_ORDER if g in wanted)


def union_boxes(boxes):
    return {'min': [min(b['min'][i] for b in boxes) for i in range(3)],
            'max': [max(b['max'][i] for b in boxes) for i in range(3)]}


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def rotate_box_yaw(local, location, yaw_degrees):
    """World AABB of a local AABB after yaw rotation and translation (eight corners)."""
    yaw = math.radians(yaw_degrees)
    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)
    corners = []
    for x in (local['min'][0], local['max'][0]):
        for y in (local['min'][1], local['max'][1]):
            for z in (local['min'][2], local['max'][2]):
                corners.append((location[0] + x * cos_yaw - y * sin_yaw,
                                location[1] + x * sin_yaw + y * cos_yaw,
                                location[2] + z))
    return {'min': [min(c[i] for c in corners) for i in range(3)],
            'max': [max(c[i] for c in corners) for i in range(3)]}


def rotate_point_yaw(point, yaw_degrees):
    yaw = math.radians(yaw_degrees)
    return [point[0] * math.cos(yaw) - point[1] * math.sin(yaw),
            point[0] * math.sin(yaw) + point[1] * math.cos(yaw), point[2]]


def boxes_overlap_volume(a, b):
    """Strictly positive overlap on all three axes; touching planes do not count."""
    for i in range(3):
        if min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) <= 1e-6:
            return False
    return True


def normalise_yaw(yaw):
    while yaw > 180.0:
        yaw -= 360.0
    while yaw <= -180.0:
        yaw += 360.0
    return yaw


def pose_close(pose, location, rotation, scale, tolerance):
    """Numeric pose comparison; angles are compared modulo 360 (UE may return yaw 180 as -180)."""
    errors = [abs(pose['location'][i] - location[i]) for i in range(3)]
    errors += [abs(normalise_yaw(pose['rotation'][i] - rotation[i])) for i in range(3)]
    errors += [abs(pose['scale'][i] - scale[i]) for i in range(3)]
    return max(errors) <= tolerance, max(errors)


def round_list(values, digits=6):
    return [round(float(v), digits) for v in values]


def round_box(box, digits=6):
    return {'min': round_list(box['min'], digits), 'max': round_list(box['max'], digits)}


# -- source and manifest access ------------------------------------------------

def load_geometry_manifest(spec):
    manifest = json.loads((ROOT / spec['source']['manifest']).read_text(encoding='utf-8'))
    if manifest['status'] != spec['source']['manifestStatusRequired']:
        raise RuntimeError('Doors manifest status ' + manifest['status'])
    return manifest


def load_placement_json(spec):
    path = ROOT / spec['source']['placementJson']
    if sha256_of(path) != spec['source']['placementJsonSha256']:
        raise RuntimeError('placement-and-articulation.json hash differs from spec')
    return json.loads(path.read_text(encoding='utf-8'))


def load_architecture_manifest(spec):
    path = ROOT / spec['openings']['architectureManifest']
    if sha256_of(path) != spec['openings']['architectureManifestSha256']:
        raise RuntimeError('architecture-manifest.json hash differs from the frozen value')
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    return {entry['assetName']: entry for entry in manifest['meshes']}


def union_constituent_boxes(entry):
    """World AABBs (cm) of the source boxes a derived union mesh was built from.

    Same convention as release_place_assets.union_constituent_boxes: source elements are
    in amot with X east, Y up, Z south; expectedSourceToUnrealCm is [x*50, z*50, y*50].
    """
    properties = entry.get('sourceProperties') or {}
    if 'source_elements_json' not in properties:
        return None
    scale = float(properties.get('source_metres_per_amah', 0.5)) * 100.0
    boxes = []
    for element in json.loads(properties['source_elements_json']):
        if element.get('shape') != 'box':
            return None
        position = element['position']
        size = element['size']
        centre = [position[0] * scale, position[2] * scale, position[1] * scale]
        half = [size[0] * scale / 2.0, size[2] * scale / 2.0, size[1] * scale / 2.0]
        boxes.append({'name': element.get('name'), 'part': element.get('part'),
                      'min': [centre[i] - half[i] for i in range(3)], 'max': [centre[i] + half[i] for i in range(3)]})
    return boxes


def openings_from_manifest(spec, architecture):
    """Kodesh and Heichal openings from the frozen manifest (expected bounds and union boxes)."""
    cfg = spec['openings']
    tolerance = cfg['boundsToleranceCm']
    kodesh = cfg['kodesh']
    boxes = {}
    for key, asset_name in kodesh['actors'].items():
        entry = architecture.get(asset_name)
        if entry is None:
            raise RuntimeError('Architecture manifest lacks ' + asset_name)
        boxes[key] = entry['expectedBoundsUnrealCm']
    heichal = cfg['heichal']
    union_entry = architecture.get(heichal['unionAsset'])
    if union_entry is None or union_entry.get('semantic') != 'union':
        raise RuntimeError('House union entry missing from the manifest')
    union = union_constituent_boxes(union_entry)
    if not union:
        raise RuntimeError('House union has no box decomposition')
    recomposed = union_boxes(union)
    if box_error(recomposed, union_entry['expectedBoundsUnrealCm']) > tolerance:
        raise RuntimeError('House union decomposition does not reproduce its manifest bounds')
    by_name = {}
    for box in union:
        by_name.setdefault(box['name'], []).append(box)
    named = {}
    for key, element_name in heichal['unionElements'].items():
        matches = by_name.get(element_name, [])
        if len(matches) != 1:
            raise RuntimeError('Expected exactly one union element %r, found %d' % (element_name, len(matches)))
        named[key] = matches[0]
    return derive_openings(spec, boxes, named, union), {'kodeshBoxes': boxes, 'heichalBoxes': named, 'houseUnionBoxes': union}


def derive_openings(spec, kodesh_boxes, heichal_boxes, house_union):
    """Opening dimensions from wall/floor boxes; asserted against the spec expectations."""
    cfg = spec['openings']
    tolerance = cfg['boundsToleranceCm']
    floor_top = kodesh_boxes['heichalFloor']['max'][2]
    if abs(kodesh_boxes['kodeshFloor']['max'][2] - floor_top) > tolerance:
        raise RuntimeError('Kodesh and Heichal floor tops differ')
    kodesh = {
        'xMin': kodesh_boxes['shoulderNorth']['min'][0], 'xMax': kodesh_boxes['shoulderNorth']['max'][0],
        'yMin': kodesh_boxes['shoulderNorth']['max'][1], 'yMax': kodesh_boxes['shoulderSouth']['min'][1],
        'floorZ': floor_top, 'lintelZ': kodesh_boxes['lintel']['min'][2],
    }
    if abs(kodesh_boxes['shoulderSouth']['min'][0] - kodesh['xMin']) > tolerance or abs(kodesh_boxes['lintel']['min'][0] - kodesh['xMin']) > tolerance:
        raise RuntimeError('Kodesh partition pieces do not share one X range')
    heichal = {
        'xMin': heichal_boxes['jambNorth']['min'][0], 'xMax': heichal_boxes['jambNorth']['max'][0],
        'yMin': heichal_boxes['jambNorth']['max'][1], 'yMax': heichal_boxes['jambSouth']['min'][1],
        'floorZ': floor_top, 'lintelZ': heichal_boxes['lintel']['min'][2],
    }
    if abs(heichal_boxes['lintel']['min'][1] - heichal['yMin']) > tolerance or abs(heichal_boxes['lintel']['max'][1] - heichal['yMax']) > tolerance:
        raise RuntimeError('Heichal lintel width differs from the jamb spacing')
    result = {}
    for name, opening in (('Kodesh', kodesh), ('Heichal', heichal)):
        opening['widthCm'] = opening['yMax'] - opening['yMin']
        opening['heightCm'] = opening['lintelZ'] - opening['floorZ']
        opening['depthCm'] = opening['xMax'] - opening['xMin']
        if abs(opening['yMin'] + opening['yMax']) > tolerance:
            raise RuntimeError(name + ' opening is not centred on Y 0')
        expected = cfg['expected'][name]
        for key in ('widthCm', 'heightCm', 'depthCm', 'xMin', 'xMax', 'floorZ'):
            if abs(opening[key] - expected[key]) > tolerance:
                raise RuntimeError('%s opening %s %.3f differs from expected %.3f' % (name, key, opening[key], expected[key]))
        result[name] = opening
    return result


# -- door planning --------------------------------------------------------------

def family_meshes(spec, family):
    return [m for m in spec['source']['meshes'] if m.get('family') == family]


def family_local_box(spec, family, boxes=None):
    """Union of the leaf, relief and hardware local boxes of one family (hinge-leaf frame)."""
    boxes = boxes or {m['name']: m['canonicalBoundsCm'] for m in spec['source']['meshes']}
    return union_boxes([boxes[m['name']] for m in family_meshes(spec, family)])


def second_leaf_offset(nominal, fold_degrees, barrel_offset):
    """Child transform in the hinge-leaf frame from the JSON fold formula."""
    a = math.radians(fold_degrees)
    return [nominal + barrel_offset * math.sin(a), barrel_offset - barrel_offset * math.cos(a), 0.0], fold_degrees


def stack_envelope(local_box, nominal, fold_degrees, barrel_offset):
    translation, relative_yaw = second_leaf_offset(nominal, fold_degrees, barrel_offset)
    child = rotate_box_yaw(local_box, translation, relative_yaw)
    return union_boxes([local_box, child]), translation, relative_yaw


def family_actor_count(spec, family_cfg):
    """Leaf actors one family produces: banks x two sides x (hinge, second) x meshes."""
    return len(family_cfg['banks']) * 2 * 2 * len(family_meshes(spec, family_cfg['family']))


def total_leaf_actor_count(spec):
    return sum(family_actor_count(spec, f) for f in spec['doorPlan']['families'])


def plan_doors(spec, placement_json, openings, boxes=None, families=None):
    """Open-state actor plan for every leaf (three meshes each) from the JSON hinge data.

    openings must be the exact manifest-derived openings (the level values carry float32
    jitter of ~1e-4 cm and are only cross-checked). JSON-vs-opening agreement uses
    doorPlan.planToleranceCm rather than exact equality.

    families (lower-case) restricts the derivation: a family that is not requested is neither
    derived nor asserted. Actor indices stay stable whatever the subset (Heichal 1-24, Kodesh
    25-36), so labels agree with the reviewed derivedPlan in the spec.
    """
    plan_cfg = spec['doorPlan']
    plan_tol = float(plan_cfg.get('planToleranceCm', 0.5))
    leaf_records = []
    skipped = []
    index_offset = 0
    banks_by_family = {}
    for door in placement_json['doors']:
        if door['role'] != 'jamb_leaf':
            continue
        banks_by_family.setdefault(door['mesh_family'], {}).setdefault(door['bank'], {})[door['side']] = door
    fold_doors = [d for d in placement_json['doors'] if d['role'] == 'fold_leaf']
    barrel_offsets = {tuple(d['hinge_axis_in_parent_cm']) for d in fold_doors}
    nominals = {d['mesh_family']: d['closed_local_location_cm'][0] for d in fold_doors}
    if len({b[1] for b in barrel_offsets}) != 1:
        raise RuntimeError('Fold hinge barrel offsets differ between leaves')
    barrel_offset = float(next(iter(barrel_offsets))[1])
    families_out = {}
    for family_cfg in plan_cfg['families']:
        family = family_cfg['family']
        family_first_index = index_offset + 1
        index_offset += family_actor_count(spec, family_cfg)
        if families is not None and family.lower() not in families:
            skipped.append({'family': family, 'actorIndices': [family_first_index, index_offset],
                            'reason': 'not requested; derivation and assertions skipped'})
            continue
        opening = openings[family]
        nominal = nominals[family]
        if abs(nominal * 4 - opening['widthCm']) > plan_tol:
            raise RuntimeError('%s nominal leaf width %.3f x 4 differs from opening width %.3f' % (family, nominal, opening['widthCm']))
        local_box = family_local_box(spec, family, boxes)
        leaf_box = (boxes or {m['name']: m['canonicalBoundsCm'] for m in spec['source']['meshes']})[
            next(m['name'] for m in family_meshes(spec, family) if m['role'] == 'leaf')]
        fit = {
            'leafHeightCm': leaf_box['max'][2] - leaf_box['min'][2], 'openingHeightCm': opening['heightCm'],
            'leafWidthCm': leaf_box['max'][0] - leaf_box['min'][0], 'nominalWidthCm': nominal,
            'fourLeavesCm': 4 * nominal, 'openingWidthCm': opening['widthCm'],
        }
        clearance = opening['heightCm'] - fit['leafHeightCm']
        if not plan_cfg['fit']['minHeightClearanceCm'] <= clearance <= plan_cfg['fit']['maxHeightClearanceCm']:
            raise RuntimeError('%s leaf height clearance %.3f outside the fit window' % (family, clearance))
        if fit['leafWidthCm'] > nominal - plan_cfg['fit']['minEdgeGapCm']:
            raise RuntimeError('%s leaf body wider than nominal minus edge gap' % family)
        fit['heightClearanceCm'] = clearance
        z = opening['floorZ'] + plan_cfg['leafLiftCm']
        fold = float(family_cfg['foldDegrees'])
        envelope, child_translation, child_relative_yaw = stack_envelope(local_box, nominal, fold, barrel_offset)
        banks_out = []
        for bank_cfg in family_cfg['banks']:
            bank = bank_cfg['bank']
            sides = banks_by_family[family][bank]
            json_x = {sides[-1]['closed_location_cm'][0], sides[1]['closed_location_cm'][0]}
            if len(json_x) != 1:
                raise RuntimeError('JSON bank %d of %s has two hinge X values' % (bank, family))
            json_x = float(next(iter(json_x)))
            if abs(json_x - bank_cfg['jsonHingeX']) > 1e-6:
                raise RuntimeError('Spec jsonHingeX %.3f differs from placement JSON %.3f' % (bank_cfg['jsonHingeX'], json_x))
            pointing = int(bank_cfg['pointing'])
            hinge_x = json_x - pointing * float(bank_cfg.get('hingeShiftTowardFaceCm', 0.0))
            hinge_yaw = 180.0 if pointing < 0 else 0.0
            world_envelope = rotate_box_yaw(envelope, [0.0, 0.0, 0.0], hinge_yaw)
            for side in (-1, 1):
                door = sides[side]
                if abs(door['closed_location_cm'][1] - side * opening['widthCm'] / 2.0) > plan_tol:
                    raise RuntimeError('JSON closed hinge Y %.4f is not on the jamb plane %.4f for %s bank %d side %d'
                                       % (door['closed_location_cm'][1], side * opening['widthCm'] / 2.0, family, bank, side))
                if abs(door['closed_location_cm'][2] - z) > plan_tol:
                    raise RuntimeError('JSON leaf bottom Z %.4f differs from floor %.4f + lift %.1f for %s'
                                       % (door['closed_location_cm'][2], opening['floorZ'], plan_cfg['leafLiftCm'], family))
                jamb_y = side * opening['widthCm'] / 2.0
                gap = plan_cfg['jambGapCm']
                if side < 0:
                    hinge_y = jamb_y + gap - world_envelope['min'][1]
                else:
                    hinge_y = jamb_y - gap - world_envelope['max'][1]
                hinge_location = [hinge_x, hinge_y, z]
                child_location = [hinge_location[i] + rotate_point_yaw(child_translation, hinge_yaw)[i] for i in range(3)]
                child_yaw = normalise_yaw(hinge_yaw + child_relative_yaw)
                side_tag = 'N' if side < 0 else 'S'
                for leaf_role, location, yaw in (('Hinge', hinge_location, hinge_yaw), ('Second', child_location, child_yaw)):
                    for mesh in family_meshes(spec, family):
                        mesh_box = (boxes or {m['name']: m['canonicalBoundsCm'] for m in spec['source']['meshes']})[mesh['name']]
                        leaf_records.append({
                            'index': family_first_index + len([r for r in leaf_records if r['family'] == family]),
                            'group': family.lower(), 'family': family, 'bank': bank, 'side': side,
                            'roleTag': '%s%s%s_%s_%s' % (family, 'B%d' % bank, side_tag, leaf_role, mesh['role'].capitalize()),
                            'leafRole': leaf_role.lower() + '_leaf', 'meshRole': mesh['role'], 'meshName': mesh['name'],
                            'location': round_list(location), 'rotation': [0.0, round(yaw, 6), 0.0], 'scale': [1.0, 1.0, 1.0],
                            'plannedWorldBoundsCm': round_box(rotate_box_yaw(mesh_box, location, yaw)),
                            'closedReference': {'jsonHingeLocationCm': door['closed_location_cm'], 'jsonClosedYaw': door['closed_yaw_degrees']},
                        })
            stack_world = {}
            for side in (-1, 1):
                stack_world[str(side)] = union_boxes([r['plannedWorldBoundsCm'] for r in leaf_records
                                                      if r['family'] == family and r['bank'] == bank and r['side'] == side])
            banks_out.append({'bank': bank, 'jsonHingeX': json_x, 'hingeX': hinge_x, 'pointing': pointing, 'hingeYaw': hinge_yaw,
                              'foldDegrees': fold, 'childTranslationInHingeFrame': round_list(child_translation),
                              'childRelativeYaw': child_relative_yaw, 'stackEnvelopeHingeFrame': round_box(envelope),
                              'stackWorldBoundsCm': {k: round_box(v) for k, v in stack_world.items()},
                              'reading': bank_cfg['reading']})
        families_out[family] = {'nominalWidthCm': nominal, 'fit': fit, 'familyLocalBoxCm': round_box(local_box),
                                'barrelOffsetCm': barrel_offset, 'banks': banks_out,
                                'planToleranceCm': plan_tol, 'jsonLeafBottomZ': z}
    return {'families': families_out, 'leaves': leaf_records, 'skippedFamilies': skipped,
            'totalLeafActorsAllFamilies': index_offset}


def plan_paroches(spec, placement_json, boxes=None):
    cfg = spec['paroches']
    curtain = placement_json['curtain']
    location = [float(v) for v in curtain['location_cm']]
    yaw = float(curtain['yaw_degrees'])
    if location != cfg['jsonLocationCm'] or yaw != cfg['jsonYawDegrees']:
        raise RuntimeError('Spec paroches transform differs from placement JSON')
    if set(curtain['meshes']) != {m['name'] for m in spec['source']['meshes'] if m.get('family') == 'Paroches'}:
        raise RuntimeError('Paroches mesh list differs between JSON and spec')
    boxes = boxes or {m['name']: m['canonicalBoundsCm'] for m in spec['source']['meshes']}
    records = []
    for mesh in spec['source']['meshes']:
        if mesh.get('family') != 'Paroches':
            continue
        records.append({'group': 'paroches', 'family': 'Paroches', 'roleTag': 'Paroches_' + mesh['role'].capitalize(),
                        'meshRole': mesh['role'], 'meshName': mesh['name'], 'location': location,
                        'rotation': [0.0, yaw, 0.0], 'scale': [1.0, 1.0, 1.0],
                        'plannedWorldBoundsCm': round_box(rotate_box_yaw(boxes[mesh['name']], location, yaw))})
    return records


def check_paroches_face(spec, records, openings):
    """The cloth must hang just east of the Kodesh wall's Heichal face and cover the opening."""
    cfg = spec['paroches']
    opening = openings['Kodesh']
    cloth = next(r for r in records if r['meshRole'] == 'cloth')
    box = cloth['plannedWorldBoundsCm']
    face_x = opening['xMax']
    standoff = box['min'][0] - face_x
    report = {'wallHeichalFaceX': face_x, 'clothMinX': box['min'][0], 'standoffCm': standoff,
              'clothY': [box['min'][1], box['max'][1]], 'openingY': [opening['yMin'], opening['yMax']],
              'clothZ': [box['min'][2], box['max'][2]], 'openingZ': [opening['floorZ'], opening['lintelZ']]}
    if standoff < 0:
        raise RuntimeError('Paroches cloth enters the Kodesh wall (min X %.2f < face %.2f)' % (box['min'][0], face_x))
    if standoff > cfg['maxStandoffCm']:
        raise RuntimeError('Paroches cloth hangs %.2f cm off the wall face (max %.2f)' % (standoff, cfg['maxStandoffCm']))
    if box['min'][1] > opening['yMin'] or box['max'][1] < opening['yMax']:
        raise RuntimeError('Paroches cloth narrower than the Kodesh opening')
    if box['max'][2] < opening['lintelZ']:
        raise RuntimeError('Paroches cloth does not reach the lintel underside')
    if box['min'][2] < opening['floorZ']:
        raise RuntimeError('Paroches cloth below the floor')
    report['coversOpening'] = True
    return report


def wall_boxes_for_clearance(spec, manifest_boxes, extra=None):
    """Named wall/floor boxes a leaf must never intersect (manifest-derived)."""
    boxes = []
    for key, box in manifest_boxes['kodeshBoxes'].items():
        boxes.append({'name': 'Kodesh:' + key, 'min': box['min'], 'max': box['max']})
    for box in manifest_boxes['houseUnionBoxes']:
        boxes.append({'name': 'HouseUnion:' + str(box['name']), 'min': box['min'], 'max': box['max']})
    for box in extra or []:
        boxes.append(box)
    return boxes


def corridor_box(spec):
    c = spec['corridor']
    return {'min': [c['xMin'], -c['halfWidthCm'], c['floorZ']], 'max': [c['xMax'], c['halfWidthCm'], c['floorZ'] + c['heightCm']]}


def check_plan_clearance(spec, leaves, paroches, wall_boxes, corridor):
    """Leaves versus wall boxes, corridor and each other; paroches versus walls only."""
    report = {'wallBoxesTested': len(wall_boxes), 'leafWallIntersections': [], 'corridorLeafIntersections': [],
              'leafPairIntersections': [], 'parochesWallIntersections': [], 'parochesIntersectsCorridor': False}
    for record in leaves:
        for box in wall_boxes:
            if boxes_overlap_volume(record['plannedWorldBoundsCm'], box):
                report['leafWallIntersections'].append({'leaf': record['roleTag'], 'wall': box['name']})
        if boxes_overlap_volume(record['plannedWorldBoundsCm'], corridor):
            report['corridorLeafIntersections'].append(record['roleTag'])
    # Leaves of different stacks must not interpenetrate (same-stack meshes overlap by design).
    for i, a in enumerate(leaves):
        for b in leaves[i + 1:]:
            same_stack = (a['family'], a['bank'], a['side']) == (b['family'], b['bank'], b['side'])
            if not same_stack and boxes_overlap_volume(a['plannedWorldBoundsCm'], b['plannedWorldBoundsCm']):
                report['leafPairIntersections'].append([a['roleTag'], b['roleTag']])
    for record in paroches:
        for box in wall_boxes:
            if boxes_overlap_volume(record['plannedWorldBoundsCm'], box):
                report['parochesWallIntersections'].append({'mesh': record['roleTag'], 'wall': box['name']})
        if boxes_overlap_volume(record['plannedWorldBoundsCm'], corridor):
            report['parochesIntersectsCorridor'] = True
    if report['leafWallIntersections']:
        raise RuntimeError('Leaf enters wall geometry: %s' % report['leafWallIntersections'][:6])
    if report['corridorLeafIntersections']:
        raise RuntimeError('Leaf blocks the y=0 walking corridor: %s' % report['corridorLeafIntersections'])
    if report['leafPairIntersections']:
        raise RuntimeError('Leaves of different stacks intersect: %s' % report['leafPairIntersections'][:6])
    if report['parochesWallIntersections']:
        raise RuntimeError('Paroches enters wall geometry: %s' % report['parochesWallIntersections'][:6])
    return report


def veneer_boxes_from_spec(spec):
    boxes = []
    for panel in spec['knownLevelGeometry']['sanctuaryVeneerPanels']:
        centre, size = panel['center'], panel['size']
        boxes.append({'name': 'Veneer:' + panel['name'], 'min': [centre[i] - size[i] / 2.0 for i in range(3)],
                      'max': [centre[i] + size[i] / 2.0 for i in range(3)]})
    return boxes


def open_door_primitive_boxes(spec, architecture):
    boxes = []
    for asset_name in spec['knownLevelGeometry']['openHeichalDoorPrimitives']:
        entry = architecture.get(asset_name)
        if entry is None:
            raise RuntimeError('Manifest lacks ' + asset_name)
        box = entry['expectedBoundsUnrealCm']
        boxes.append({'name': 'OpenDoorPrimitive:' + asset_name, 'min': box['min'], 'max': box['max']})
    return boxes


def build_plan(spec, boxes=None, groups=GROUP_ORDER, extra_wall_boxes=None, level_openings=None):
    """Plan for the requested groups from the EXACT manifest openings, plus clearance evidence.

    Only the requested door families are derived and asserted (an excluded family, e.g. the
    Heichal, is skipped entirely and listed in doors['skippedFamilies']). Actor indices are
    stable (Heichal 1-24, Kodesh 25-36, paroches 37-39) whatever subset is requested, so
    labels agree with the reviewed derivedPlan in the spec.

    level_openings (from DoorPlacement.level_openings) are cross-checked against the manifest
    openings within openings.boundsToleranceCm and reported; they never drive the plan.
    """
    groups = normalise_groups(groups)
    placement_json = load_placement_json(spec)
    architecture = load_architecture_manifest(spec)
    openings, manifest_boxes = openings_from_manifest(spec, architecture)
    level_report = compare_openings(spec, openings, level_openings) if level_openings is not None else None
    families = [g for g in groups if g in ('heichal', 'kodesh')]
    doors = plan_doors(spec, placement_json, openings, boxes, families=families)
    paroches = plan_paroches(spec, placement_json, boxes)
    for offset, record in enumerate(paroches, start=total_leaf_actor_count(spec) + 1):
        record['index'] = offset
    face = check_paroches_face(spec, paroches, openings)
    if 'paroches' not in groups:
        paroches = []
    extra = veneer_boxes_from_spec(spec) + open_door_primitive_boxes(spec, architecture) + list(extra_wall_boxes or [])
    walls = wall_boxes_for_clearance(spec, manifest_boxes, extra)
    clearance = check_plan_clearance(spec, doors['leaves'], paroches, walls, corridor_box(spec))
    return {'openings': openings, 'levelOpeningsVsManifest': level_report, 'manifestBoxes': manifest_boxes,
            'doors': doors, 'paroches': paroches, 'parochesFace': face, 'clearance': clearance,
            'corridorBoxCm': corridor_box(spec), 'groups': list(groups),
            'plannedActorsAllGroups': total_leaf_actor_count(spec) + 3,
            'plannedActorsRequested': len(doors['leaves']) + len(paroches)}


def compare_openings(spec, manifest_openings, level_openings):
    """Level-derived openings must agree with the exact manifest openings within tolerance."""
    tolerance = spec['openings']['boundsToleranceCm']
    report = {}
    worst = 0.0
    for name, expected in manifest_openings.items():
        actual = level_openings[name]
        diffs = {key: actual[key] - expected[key] for key in expected}
        worst = max(worst, max(abs(v) for v in diffs.values()))
        report[name] = {'manifest': expected, 'level': actual, 'levelMinusManifestCm': diffs}
    report['worstDifferenceCm'] = worst
    report['toleranceCm'] = tolerance
    if worst > tolerance:
        raise RuntimeError('Level openings differ from the frozen manifest by %.4f cm' % worst)
    return report


def plan_signature(plan):
    """Compact numeric view used to compare the spec's stored plan with a recomputation."""
    rows = []
    for record in plan['doors']['leaves'] + plan['paroches']:
        rows.append([record['roleTag'], record['meshName'], record['location'], record['rotation'], record['plannedWorldBoundsCm']])
    return rows


def offline_check(spec=None, write_plan=False):
    """Consistency checks that need no engine. Raises on the first failure."""
    spec = spec or load_spec()
    helper = load_placement_helper(spec)
    source = spec['source']
    report = {'sourceFiles': [], 'materialsOnDisk': {}, 'namespaceOnDisk': None}

    manifest = load_geometry_manifest(spec)
    if manifest['manifest_sha256'] != spec['openings']['architectureManifestSha256']:
        raise RuntimeError('Doors manifest was exported against a different architecture manifest')
    if sha256_of(ROOT / source['authoringScript']) != source['authoringScriptSha256'] or manifest['script_sha256'] != source['authoringScriptSha256']:
        raise RuntimeError('create_sanctuary_doors.py changed since the frozen export')
    frozen = {Path(f['path']).name: f['sha256'] for f in json.loads((ROOT / source['frozenFiles']).read_text(encoding='utf-8'))}
    by_name = {m['name']: m for m in manifest['meshes']}
    if len(source['meshes']) != 9 or len(manifest['meshes']) != 9:
        raise RuntimeError('Expected nine meshes')
    total_triangles = 0
    for record in source['meshes']:
        entry = by_name.get(record['name'])
        if entry is None:
            raise RuntimeError('Manifest lacks ' + record['name'])
        path = ROOT / source['folder'] / record['file']
        if not path.exists():
            raise RuntimeError('Missing source OBJ ' + str(path))
        actual = sha256_of(path)
        if actual != record['sha256'] or entry['sha256'] != record['sha256'] or frozen.get(record['file']) != record['sha256']:
            raise RuntimeError('Frozen OBJ hash differs for ' + record['name'])
        if entry['triangles'] != record['triangles']:
            raise RuntimeError('Triangle count differs from manifest for ' + record['name'])
        if helper.box_error(entry['bounds_cm'], record['canonicalBoundsCm']) > 1e-6:
            raise RuntimeError('Canonical bounds differ from manifest for ' + record['name'])
        part_volume = sum(p['volume_cm3'] for p in entry['parts'])
        if abs(part_volume - record['partVolumeSumCm3']) > 1e-3:
            raise RuntimeError('Part volume sum differs from manifest for ' + record['name'])
        total_triangles += entry['triangles']
        report['sourceFiles'].append({'file': record['file'], 'sha256': actual, 'triangles': entry['triangles'], 'parts': len(entry['parts'])})
    if total_triangles != source['totalTriangles']:
        raise RuntimeError('Total triangles %d differ from spec %d' % (total_triangles, source['totalTriangles']))

    namespace_dir = helper.disk_path(source['namespace'] + '/x').parent
    report['namespaceOnDisk'] = namespace_dir.exists()
    for role, entry in spec['materials'].items():
        if role == 'rule':
            continue
        report['materialsOnDisk'][role] = [{'path': c['path'], 'exists': helper.disk_path(c['path']).exists()} for c in entry['candidates']]
        if not any(c['exists'] for c in report['materialsOnDisk'][role]):
            raise RuntimeError('No %s material candidate exists on disk' % role)
    if not (ROOT / spec['targetMapFile']).exists():
        raise RuntimeError('Target map file missing')
    settings = spec['importSettings']
    for key in ('fbxImportUI', 'staticMeshImportData'):
        if key not in settings:
            raise RuntimeError('importSettings lacks ' + key)

    plan = build_plan(spec, groups=GROUP_ORDER)
    report['openings'] = plan['openings']
    report['defaultGroups'] = list(normalise_groups(spec['defaultGroups']))
    report['deliberateOmissions'] = spec.get('deliberateOmissions', {})
    for group in GROUP_ORDER:
        if group not in report['defaultGroups'] and group not in report['deliberateOmissions']:
            raise RuntimeError('Group %r is excluded from defaultGroups without a deliberateOmissions entry' % group)
    # The default subset must derive cleanly on its own (this is what the native run executes).
    subset = build_plan(spec, groups=report['defaultGroups'])
    report['defaultSubsetActors'] = subset['plannedActorsRequested']
    report['defaultSubsetSkippedFamilies'] = subset['doors']['skippedFamilies']
    full_rows = {row[0]: row for row in plan_signature(plan)}
    for row in plan_signature(subset):
        if json.dumps(full_rows.get(row[0])) != json.dumps(row):
            raise RuntimeError('Subset plan differs from the full plan for ' + row[0])
    report['parochesFace'] = plan['parochesFace']
    report['clearance'] = plan['clearance']
    report['leafActors'] = len(plan['doors']['leaves'])
    report['parochesActors'] = len(plan['paroches'])
    report['fit'] = {family: data['fit'] for family, data in plan['doors']['families'].items()}
    report['banks'] = {family: data['banks'] for family, data in plan['doors']['families'].items()}
    stored = spec.get('derivedPlan')
    if write_plan:
        spec['derivedPlan'] = {
            'note': 'Generated by release_import_doors.py --write-plan from the placement JSON, the frozen manifests and the '
                    'doorPlan rules above; offline_check() recomputes it and refuses to run if it differs.',
            'openings': plan['openings'], 'families': plan['doors']['families'],
            'actors': [dict(r) for r in plan['doors']['leaves'] + plan['paroches']],
            'parochesFace': plan['parochesFace'], 'clearance': plan['clearance'], 'corridorBoxCm': plan['corridorBoxCm'],
        }
        SPEC_PATH.write_text(json.dumps(spec, indent=2) + '\n', encoding='utf-8')
        report['specWritten'] = True
    elif stored is None:
        raise RuntimeError('Spec has no derivedPlan; run --write-plan and review it')
    else:
        stored_rows = [[a['roleTag'], a['meshName'], a['location'], a['rotation'], a['plannedWorldBoundsCm']] for a in stored['actors']]
        if json.dumps(stored_rows) != json.dumps(plan_signature(plan)):
            raise RuntimeError('Stored derivedPlan differs from the recomputed plan; review and rerun --write-plan')
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


def _enum_name(enum_class, value, candidates):
    for name in candidates:
        if hasattr(enum_class, name) and getattr(enum_class, name) == value:
            return name
    return str(value)


def pick_material(ue, spec, role, receipt):
    """First existing MaterialInterface among the spec candidates; records fallbacks."""
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if role in receipt['materials']:
        return ue.load_asset(receipt['materials'][role]['assigned'])
    tried = []
    for position, candidate in enumerate(spec['materials'][role]['candidates']):
        exists = assets.does_asset_exist(candidate['path'])
        material = ue.load_asset(candidate['path']) if exists else None
        ok = isinstance(material, ue.MaterialInterface)
        tried.append({'path': candidate['path'], 'kind': candidate['kind'], 'exists': bool(exists), 'loaded': ok})
        if ok:
            if position > 0:
                receipt['limitations'].append('%s material fell back to %s (%s); preferred candidate missing' % (role, candidate['path'], candidate['kind']))
            receipt['materials'][role] = {'assigned': candidate['path'], 'kind': candidate['kind'], 'tried': tried}
            return material
    raise RuntimeError('No %s material candidate loads: %s' % (role, tried))


def import_one_mesh(ue, spec, record, material):
    """OBJ -> StaticMesh through the reviewed adapter settings; verifies, assigns, saves."""
    source = spec['source']
    settings = spec['importSettings']
    path = ROOT / source['folder'] / record['file']
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
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
        raise RuntimeError('Import of %s produced %s' % (record['file'], [type(o).__name__ for o in objects]))
    mesh = objects[0]
    if mesh.get_name() != record['name']:
        raise RuntimeError('Imported name %s differs from destination_name %s' % (mesh.get_name(), record['name']))
    info = verify_and_assign(ue, spec, mesh, record, material)
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + record['name'])
    info['uassetSha256'] = sha256_of(ROOT / 'Content' / (_asset_path(mesh)[len('/Game/'):] + '.uasset'))
    return mesh, info


def verify_and_assign(ue, spec, mesh, record, material, assign=True, expected_slots=None):
    """Bounds, triangles and material slots of one StaticMesh against the spec record.

    assign=True (import run) puts `material` on every slot; assign=False (-DoorsPlaceOnly)
    only verifies that every existing slot already carries `material` and mutates nothing.
    expected_slots, when given, is the manifest part count (the OBJ importer makes one slot
    per 'g' group, so slots == parts on every mesh of the first run).
    """
    box = _static_mesh_box(mesh)
    error = max(abs(box[k][i] - record['canonicalBoundsCm'][k][i]) for k in ('min', 'max') for i in range(3))
    triangles = mesh.get_num_triangles(0)
    if error > spec['source']['boundsToleranceCm']:
        raise RuntimeError('%s bounds differ from canonical by %.4f cm (Y reflection did not round-trip?): %r' % (record['name'], error, box))
    if triangles != record['triangles']:
        raise RuntimeError('%s triangles %d differ from %d' % (record['name'], triangles, record['triangles']))
    slots = len(mesh.get_editor_property('static_materials'))
    if slots < 1:
        raise RuntimeError('%s has no material slots' % record['name'])
    if expected_slots is not None and slots != expected_slots:
        raise RuntimeError('%s has %d material slots, manifest has %d parts' % (record['name'], slots, expected_slots))
    if material is not None and assign:
        for slot in range(slots):
            mesh.set_material(slot, material)
    expected = _asset_path(material) if material is not None else None
    slot_paths = [_asset_path(mesh.get_material(slot)) for slot in range(slots)]
    not_assigned = [slot for slot, path in enumerate(slot_paths) if expected is not None and path != expected]
    if not_assigned:
        verb = 'not assigned' if assign else 'do not carry the spec material %s' % expected
        raise RuntimeError('Material slots %s on %s: %s' % (verb, record['name'], not_assigned[:10]))
    collision = {'simpleCollisionElements': None, 'collisionTraceFlag': None}
    try:
        body = mesh.get_editor_property('body_setup')
        if body is not None:
            agg = body.get_editor_property('agg_geom')
            collision['simpleCollisionElements'] = sum(len(agg.get_editor_property(k)) for k in ('convex_elems', 'box_elems', 'sphere_elems', 'sphyl_elems'))
            collision['collisionTraceFlag'] = str(body.get_editor_property('collision_trace_flag'))
    except Exception as error:  # noqa: BLE001 - informational only
        collision['error'] = str(error)
    return {'asset': _asset_path(mesh), 'file': record['file'], 'triangles': triangles, 'localBoundsCm': box,
            'boundsErrorCm': error, 'materialSlots': slots, 'material': expected,
            'slotMaterials': sorted({str(p) for p in slot_paths}), 'slotMaterialsUniform': len(set(slot_paths)) == 1,
            'meshCollision': collision}


def winding_report(ue, mesh, record, spec):
    """Signed divergence volume with UE face normals must be positive and match the manifest.

    Every authored part is a closed solid with positive canonical volume, so the flux sum
    over the imported triangles (UE left-handed face normal cross(C-A, B-A)) must equal the
    manifest's part volume sum. A reversed winding would give the negative value.
    """
    check = spec['windingCheck']
    needed = ('GeometryScript_AssetUtils', 'GeometryScript_MeshQueries')
    if not all(hasattr(ue, n) for n in needed):
        return {'status': 'unavailable', 'passed': False,
                'reason': 'GeometryScripting not loaded; launch with -EnablePlugins=GeometryScripting'}
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
        return {'status': 'copy_failed', 'passed': False, 'reason': str(result)}
    query = ue.GeometryScript_MeshQueries
    flux = 0.0
    disagreements = 0
    count = dynamic.get_triangle_count()
    for tid in range(count):
        positions = [_xyz(v) for v in query.get_triangle_positions(dynamic, tid) if isinstance(v, ue.Vector)]
        if len(positions) != 3:
            return {'status': 'read_failed', 'passed': False, 'reason': 'triangle %d has %d corners' % (tid, len(positions))}
        face = query.get_triangle_face_normal(dynamic, tid)
        normals = [_xyz(v) for v in face if isinstance(v, ue.Vector)] if isinstance(face, tuple) else [_xyz(face)]
        if len(normals) != 1:
            return {'status': 'read_failed', 'passed': False, 'reason': 'no face normal for triangle %d' % tid}
        normal = normals[0]
        a, b, c = positions
        ue_cross = _cross(_sub(c, a), _sub(b, a))
        if _dot(ue_cross, normal) < 0:
            disagreements += 1
        area = 0.5 * math.sqrt(_dot(ue_cross, ue_cross))
        centroid = [(a[i] + b[i] + c[i]) / 3.0 for i in range(3)]
        flux += _dot(normal, centroid) * area
    signed_volume = flux / 3.0
    expected = record['partVolumeSumCm3']
    relative = abs(signed_volume - expected) / expected if expected else None
    passed = signed_volume > 0 and disagreements == 0 and relative is not None and relative <= check['maxRelativeVolumeError']
    return {'status': 'checked', 'passed': passed, 'triangles': count, 'signedVolumeUEcm3': signed_volume,
            'manifestPartVolumeSumCm3': expected, 'relativeVolumeError': relative,
            'faceNormalVsCrossDisagreements': disagreements,
            'convention': 'UE left-handed face normal cross(C-A, B-A); positive volume means front faces point outward'}


# --------------------------------------------------------------------------
# Engine side: opening geometry and placement
# --------------------------------------------------------------------------

class DoorPlacement:
    def __init__(self, ue, spec, helper, run_state, receipt):
        self.ue = ue
        self.spec = spec
        self.helper = helper
        self.run = run_state
        self.receipt = receipt
        self.architecture = load_architecture_manifest(spec)

    def rows_with_mesh(self, asset_path):
        return [row for row in self.run.snapshot if asset_path in row['meshes']]

    def measured_row(self, asset_name):
        """The single identity-transform actor carrying a measured architecture mesh."""
        prefix = self.spec['openings']['levelAssetPrefix']
        rows = self.rows_with_mesh(prefix + asset_name)
        if len(rows) != 1:
            raise RuntimeError('Expected exactly one actor with %s, found %d' % (asset_name, len(rows)))
        row = rows[0]
        close, error = self.helper._pose_close(row['pose'], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [1.0, 1.0, 1.0],
                                               self.spec['verification']['transformToleranceCm'])
        if not close:
            raise RuntimeError('%s is not at identity (error %.4f)' % (asset_name, error))
        entry = self.architecture[asset_name]
        error = self.helper.box_error(row['bounds'], entry['expectedBoundsUnrealCm'])
        if error > self.spec['openings']['boundsToleranceCm']:
            raise RuntimeError('%s level bounds differ from manifest by %.3f cm' % (asset_name, error))
        return row, error

    def level_openings(self):
        """Openings from the LEVEL actors, cross-checked against the manifest."""
        cfg = self.spec['openings']
        found = {}
        kodesh_boxes = {}
        for key, asset_name in cfg['kodesh']['actors'].items():
            row, error = self.measured_row(asset_name)
            kodesh_boxes[key] = row['bounds']
            found[key] = {'asset': asset_name, 'actorLabel': row['label'], 'actorName': row['name'], 'folder': row['folder'],
                          'worldBoundsCm': row['bounds'], 'manifestErrorCm': error}
        union_name = cfg['heichal']['unionAsset']
        row, error = self.measured_row(union_name)
        entry = self.architecture[union_name]
        union = self.helper.verify_union_decomposition(entry, cfg['boundsToleranceCm'])
        by_name = {}
        for box in union:
            by_name.setdefault(box['name'], []).append(box)
        heichal_boxes = {}
        for key, element_name in cfg['heichal']['unionElements'].items():
            matches = by_name.get(element_name, [])
            if len(matches) != 1:
                raise RuntimeError('Union element %r count %d' % (element_name, len(matches)))
            heichal_boxes[key] = matches[0]
            found['heichal_' + key] = {'unionActorLabel': row['label'], 'unionActorName': row['name'], 'element': element_name,
                                       'boxCm': {'min': matches[0]['min'], 'max': matches[0]['max']}}
        found['houseUnion'] = {'asset': union_name, 'actorLabel': row['label'], 'actorName': row['name'], 'folder': row['folder'],
                               'worldBoundsCm': row['bounds'], 'manifestErrorCm': error, 'constituentBoxes': len(union)}
        openings = derive_openings(self.spec, kodesh_boxes, heichal_boxes, union)
        return openings, found, {'kodeshBoxes': kodesh_boxes, 'heichalBoxes': heichal_boxes, 'houseUnionBoxes': union}

    def known_level_geometry(self):
        """Existing open-door primitives and gold veneers, read from the level."""
        cfg = self.spec['knownLevelGeometry']
        primitives = []
        boxes = []
        for asset_name in cfg['openHeichalDoorPrimitives']:
            row, error = self.measured_row(asset_name)
            primitives.append({'asset': asset_name, 'actorLabel': row['label'], 'worldBoundsCm': row['bounds'], 'manifestErrorCm': error})
            boxes.append({'name': 'OpenDoorPrimitive:' + asset_name, 'min': row['bounds']['min'], 'max': row['bounds']['max']})
        veneers = []
        for row in self.rows_with_mesh(cfg['veneerMesh']):
            veneers.append({'actorLabel': row['label'], 'folder': row['folder'], 'worldBoundsCm': row['bounds']})
            boxes.append({'name': 'Veneer:' + row['label'], 'min': row['bounds']['min'], 'max': row['bounds']['max']})
        if len(veneers) != cfg['veneerExpectedCount']:
            self.receipt['limitations'].append('Expected %d veneer actors, found %d; clearance still tested against those found'
                                               % (cfg['veneerExpectedCount'], len(veneers)))
        return {'openHeichalDoorPrimitives': primitives, 'veneers': veneers}, boxes

    def clearance_candidates(self, exclude_labels):
        """Every mesh-bearing actor; verified unions are tested through their constituent boxes."""
        cfg = self.spec['clearance']
        prefix = cfg['levelAssetPrefix']
        boxes_by_key = {}
        candidates = []
        for row in self.run.snapshot:
            if not row['meshes'] or row['label'] in exclude_labels:
                continue
            key = None
            if row['folder'] == cfg['unionFolder']:
                names = [m[len(prefix):] for m in row['meshes'] if m and m.startswith(prefix)]
                entry = self.architecture.get(names[0]) if len(names) == 1 and len(row['meshes']) == 1 else None
                if entry is not None and entry.get('semantic') == 'union' and self.helper.box_error(row['bounds'], entry['expectedBoundsUnrealCm']) <= cfg['unionBoundsToleranceCm']:
                    key = names[0]
                    boxes_by_key[key] = self.helper.verify_union_decomposition(entry, cfg['unionBoundsToleranceCm'])
            extent = [row['bounds']['max'][i] - row['bounds']['min'][i] for i in range(3)]
            candidates.append({'label': row['label'], 'bounds': row['bounds'], 'unionKey': key,
                               'large': max(extent) > cfg['largeActorExtentCm']})
        return candidates, boxes_by_key

    def blockers_for(self, planned, candidates, boxes_by_key):
        blockers, envelopes = [], []
        for candidate in candidates:
            if not boxes_overlap_volume(planned, candidate['bounds']):
                continue
            boxes = boxes_by_key.get(candidate['unionKey']) if candidate['unionKey'] else None
            if boxes is not None:
                hits = [b['name'] for b in boxes if boxes_overlap_volume(planned, b)]
                if hits:
                    blockers.append({'label': candidate['label'], 'kind': 'union_constituent_box', 'constituents': hits})
                else:
                    envelopes.append({'label': candidate['label'], 'kind': 'hollow_union_envelope_aabb_only'})
            elif candidate['large']:
                envelopes.append({'label': candidate['label'], 'kind': 'large_actor_aabb_only_not_decomposable'})
            else:
                blockers.append({'label': candidate['label'], 'kind': 'actor_aabb'})
        return blockers, envelopes

    def spawn(self, mesh, record, collision_profile):
        ue = self.ue
        spec = self.spec
        label = '%s%s_%02d_%s' % (spec['labelPrefix'], spec['group'], record['index'], record['roleTag'])
        actor = self.run.actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(*record['location']),
                                                       ue.Rotator(pitch=0.0, yaw=record['rotation'][1], roll=0.0), transient=False)
        if actor is None:
            raise RuntimeError('StaticMeshActor spawn returned None for ' + label)
        actor.set_actor_label(label)
        actor.set_folder_path(spec['folder'] + '/' + record['family'])
        actor.set_editor_property('tags', [ue.Name(spec['actorTag']), ue.Name('Release' + spec['group']), ue.Name(record['roleTag'])])
        component = actor.get_component_by_class(ue.StaticMeshComponent)
        if component is None:
            raise RuntimeError('Spawned actor has no StaticMeshComponent: ' + label)
        if not component.set_static_mesh(mesh):
            raise RuntimeError('set_static_mesh returned False for ' + label)
        if _asset_path(component.get_editor_property('static_mesh')) != _asset_path(mesh):
            raise RuntimeError('Static mesh readback differs for ' + label)
        if collision_profile:
            component.set_collision_profile_name(collision_profile)
            if collision_profile == 'NoCollision':
                component.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        return actor, component, label

    def place(self, meshes, groups, plan, extra_boxes, manifest_boxes):
        """Spawn the planned actors, verify bounds and clearance; destroy everything on failure."""
        ue = self.ue
        spec = self.spec
        tolerance = spec['verification']['staticBoundsToleranceCm']
        wanted = [r for r in plan['doors']['leaves'] + plan['paroches'] if r['group'] in groups]
        walls = wall_boxes_for_clearance(spec, manifest_boxes, extra_boxes)
        candidates, boxes_by_key = self.clearance_candidates(set())
        corridor = corridor_box(spec)
        clearance = {'wallBoxesTested': len(walls), 'actorsConsidered': len(candidates),
                     'unionsDecomposed': sorted(boxes_by_key), 'perActor': [], 'preExistingCorridorActors': []}
        for candidate in candidates:
            if boxes_overlap_volume(corridor, candidate['bounds']) and not candidate['large'] and candidate['unionKey'] is None:
                clearance['preExistingCorridorActors'].append(candidate['label'])
        placed = []
        records = []
        try:
            for record in wanted:
                mesh = meshes[record['meshName']]['mesh']
                planned = rotate_box_yaw(meshes[record['meshName']]['localBoundsCm'], record['location'], record['rotation'][1])
                if box_error(planned, record['plannedWorldBoundsCm']) > tolerance:
                    raise RuntimeError('Imported bounds change the plan for %s by %.4f' % (record['roleTag'], box_error(planned, record['plannedWorldBoundsCm'])))
                wall_hits = [b['name'] for b in walls if boxes_overlap_volume(planned, b)]
                if wall_hits:
                    raise RuntimeError('%s enters wall geometry %s' % (record['roleTag'], wall_hits))
                blockers, envelopes = self.blockers_for(planned, candidates, boxes_by_key)
                corridor_hit = boxes_overlap_volume(planned, corridor)
                clearance['perActor'].append({'roleTag': record['roleTag'], 'blockers': blockers, 'envelopesOnly': envelopes,
                                              'intersectsCorridor': corridor_hit})
                if blockers:
                    raise RuntimeError('%s intersects existing actors %s' % (record['roleTag'], blockers[:5]))
                if corridor_hit and record['group'] != 'paroches':
                    raise RuntimeError('%s blocks the walking corridor' % record['roleTag'])
                profile = spec['paroches']['collisionProfile'] if record['group'] == 'paroches' else spec['doorPlan']['collisionProfile']
                actor, component, label = self.spawn(mesh, record, profile)
                placed.append(actor)
                placed_bounds = self.helper._actor_bounds(actor)
                if box_error(placed_bounds, planned) > tolerance:
                    raise RuntimeError('Placed %s bounds differ from plan by %.4f' % (label, box_error(placed_bounds, planned)))
                records.append(dict(record, label=label, mesh=_asset_path(mesh), kind='StaticMeshActor',
                                    collisionProfile=str(component.get_collision_profile_name()),
                                    collisionEnabled=_enum_name(ue.CollisionEnabled, component.get_collision_enabled(),
                                                                ['NO_COLLISION', 'QUERY_ONLY', 'PHYSICS_ONLY', 'QUERY_AND_PHYSICS', 'PROBE_ONLY', 'QUERY_AND_PROBE']),
                                    placedWorldBoundsCm=placed_bounds, actor=actor))
        except Exception:
            clearance['failed'] = True
            self.receipt['clearanceCheck'] = clearance
            self.run.destroy_all(placed)
            raise
        self.receipt['clearanceCheck'] = clearance
        return records


def _strip(record):
    return {key: value for key, value in record.items() if key != 'actor'}


def run(import_only=False, place_only=False, groups=None, allow_unverified_winding=False):
    """Import, check, place. Returns the receipt dict; raises on guard failure.

    groups None = spec defaultGroups (kodesh, paroches). Groups not requested are recorded
    under receipt['deliberateOmissions'] with the spec's reason (the Heichal decision).
    """
    import unreal as ue
    spec = load_spec()
    groups = normalise_groups(spec['defaultGroups'] if groups is None else groups)
    omitted = {g: spec.get('deliberateOmissions', {}).get(g, 'not requested by -DoorsGroups') for g in GROUP_ORDER if g not in groups}
    helper = load_placement_helper(spec)
    offline = offline_check(spec)
    manifest_parts = {m['name']: len(m['parts']) for m in load_geometry_manifest(spec)['meshes']}
    if import_only and place_only:
        raise RuntimeError('-DoorsImportOnly and -DoorsPlaceOnly exclude each other')
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before import')
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    namespace_exists = assets.does_directory_exist(spec['source']['namespace'])
    if namespace_exists and not place_only:
        raise RuntimeError('Existing native namespace preserved: ' + spec['source']['namespace'])
    if place_only and not namespace_exists:
        raise RuntimeError('-DoorsPlaceOnly needs the imported namespace ' + spec['source']['namespace'])

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt_path = ROOT / spec['receiptFolder'] / (spec['receiptPrefix'] + stamp + '.json')
    if receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(receipt_path))
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == spec['lastKnownMapSha256'],
        'protectedMapSha256Before': protected, 'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'offlineCheck': offline,
        'switches': {'importOnly': import_only, 'placeOnly': place_only, 'groups': list(groups),
                     'allowUnverifiedWinding': allow_unverified_winding},
        'deliberateOmissions': omitted,
        'sourceReference': spec['sourceReference'],
        'materials': {}, 'meshes': {}, 'windingCheck': {}, 'openingGeometry': {}, 'knownLevelGeometry': {},
        'plan': {}, 'placed': [], 'errors': [], 'mapSaved': False, 'limitations': list(spec['limitations']),
    }
    for group, reason in omitted.items():
        receipt['limitations'].append('Group %r deliberately not placed: %s' % (group, reason))

    def write():
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        # -- 1. import + materials (or verify an existing import) -------------------------
        meshes = {}
        for record in spec['source']['meshes']:
            material = pick_material(ue, spec, record['role'], receipt)
            if place_only:
                asset_path = spec['source']['meshFolder'] + '/' + record['name']
                if not assets.does_asset_exist(asset_path):
                    raise RuntimeError('Missing imported mesh ' + asset_path)
                mesh = ue.load_asset(asset_path)
                if not isinstance(mesh, ue.StaticMesh):
                    raise RuntimeError('Asset is not a StaticMesh: ' + asset_path)
                # Verify only: bounds, triangles, slots == manifest parts, every slot on the spec material.
                info = verify_and_assign(ue, spec, mesh, record, material, assign=False, expected_slots=manifest_parts[record['name']])
                if not info['slotMaterialsUniform']:
                    raise RuntimeError('Existing mesh %s has mixed slot materials' % record['name'])
                info['uassetSha256'] = sha256_of(helper.disk_path(asset_path))
                info['verifiedExistingImport'] = True
            else:
                mesh, info = import_one_mesh(ue, spec, record, material)
            info['mesh'] = mesh
            meshes[record['name']] = info
            receipt['meshes'][record['name']] = {k: v for k, v in info.items() if k != 'mesh'}
            write()
        receipt['status'] = 'meshes_verified' if place_only else 'meshes_saved'
        if place_only and (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('-DoorsPlaceOnly verification dirtied packages; nothing may be re-saved in this mode')

        # -- 2. winding ------------------------------------------------------------------
        all_passed = True
        for record in spec['source']['meshes']:
            report = winding_report(ue, meshes[record['name']]['mesh'], record, spec)
            receipt['windingCheck'][record['name']] = report
            all_passed = all_passed and report['passed']
            write()
        receipt['windingVerified'] = all_passed
        if import_only:
            receipt['status'] = 'meshes_saved_import_only_no_map_change'
            return receipt
        if not all_passed and spec['windingCheck']['requireForPlacement'] and not allow_unverified_winding:
            receipt['status'] = 'meshes_saved_placement_skipped_winding_unverified'
            receipt['limitations'].append('Placement skipped: winding check did not pass or was unavailable; rerun with '
                                          '-DoorsPlaceOnly -EnablePlugins=GeometryScripting, or inspect before -DoorsAllowUnverifiedWinding')
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
        external_copied = []
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[len('/Game/'):]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[len('/Game/'):])
                external_copied.append(str(external))
        receipt['checkpoint'] = str(checkpoint)
        receipt['oneFilePerActorFoldersCopied'] = external_copied

        run_state = helper.Placement(ue, spec)
        run_state.world = world
        run_state.receipt = receipt
        run_state.receipt_path = receipt_path
        run_state.take_snapshot()
        baseline = run_state.numeric_baseline(run_state.snapshot)
        own_prefix = spec['labelPrefix'] + spec['group'] + '_'
        clashes = [r['label'] for r in run_state.snapshot
                   if r['label'].startswith(own_prefix) or r['folder'] == spec['folder'] or r['folder'].startswith(spec['folder'] + '/')]
        if clashes:
            raise RuntimeError('Existing door release actors preserved; refusing duplicate placement: %s' % clashes[:10])
        for mesh_name, info in meshes.items():
            rows = run_state.actors_with_mesh(info['asset'])
            if rows:
                raise RuntimeError('Mesh %s already present in the map: %s' % (mesh_name, [r['label'] for r in rows]))
        others = [r for r in run_state.snapshot if r['label'].startswith(spec['labelPrefix'])]
        receipt['preExistingReleaseActors'] = [{'label': r['label'], 'folder': r['folder'], 'meshes': r['meshes']} for r in others]
        receipt['actorCountBefore'] = len(run_state.snapshot)
        write()

        # -- 4. openings from the level, plan, clearance, spawn ------------------------------
        doors = DoorPlacement(ue, spec, helper, run_state, receipt)
        openings, found, manifest_boxes = doors.level_openings()
        receipt['openingGeometry'] = {'openings': openings, 'actors': found}
        known, extra_boxes = doors.known_level_geometry()
        receipt['knownLevelGeometry'] = known
        imported_boxes = {name: info['localBoundsCm'] for name, info in meshes.items()}
        # Plan from the EXACT manifest openings for the requested groups only; the level
        # openings (float32 jitter, e.g. floor top 925.00006) are cross-checked, not used.
        plan = build_plan(spec, boxes=imported_boxes, groups=groups, extra_wall_boxes=extra_boxes, level_openings=openings)
        receipt['openingGeometry']['levelVsManifest'] = plan['levelOpeningsVsManifest']
        receipt['plan'] = {'groups': plan['groups'], 'openings': plan['openings'], 'families': plan['doors']['families'],
                           'skippedFamilies': plan['doors']['skippedFamilies'], 'parochesFace': plan['parochesFace'],
                           'offlineClearance': plan['clearance'], 'corridorBoxCm': plan['corridorBoxCm'],
                           'plannedActorsAllGroups': plan['plannedActorsAllGroups'],
                           'plannedActorsRequested': plan['plannedActorsRequested'],
                           'actors': plan['doors']['leaves'] + plan['paroches']}
        write()
        records = doors.place(meshes, groups, plan, extra_boxes, manifest_boxes)
        receipt['placed'] = [_strip(r) for r in records]
        write()
        if not records:
            receipt['status'] = 'meshes_saved_nothing_placed_map_unchanged'
            return receipt
        current = run_state.numeric_baseline(run_state.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])

        # -- 5. save, reopen, read back -------------------------------------------------
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
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])
        verify = spec['verification']
        readback = []
        for record in records:
            matching = [r for r in reopened if r['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
            row = matching[0]
            close, error = pose_close(row['pose'], record['location'], record['rotation'], record['scale'], verify['transformToleranceCm'])
            bounds_error = box_error(row['bounds'], record['plannedWorldBoundsCm'])
            component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
            entry = {'label': record['label'], 'folder': row['folder'], 'meshPath': row['meshes'], 'pose': row['pose'],
                     'worldBoundsCm': row['bounds'], 'poseErrorCm': error, 'boundsErrorCm': bounds_error,
                     'collisionProfile': str(component.get_collision_profile_name()),
                     'materials': sorted({_asset_path(component.get_material(i)) for i in range(component.get_num_materials())})}
            readback.append(entry)
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)' % (record['label'], error, bounds_error))
        receipt['reopenedReadback'] = readback
        receipt['actorCountAfter'] = len(reopened)
        receipt['status'] = 'doors_paroches_saved_reopened_visual_and_walk_acceptance_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif receipt['meshes'] and not place_only:
            receipt['status'] = 'failed_partial_assets_preserved_map_unchanged'
        else:
            receipt['status'] = 'failed_before_import_nothing_changed' if not place_only else 'failed_before_save_map_unchanged'
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
    return 'release_import_doors.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    tokens = command_line.split()
    groups = None  # spec defaultGroups unless -DoorsGroups= is given
    for token in tokens:
        if token.startswith('-doorsgroups='):
            groups = normalise_groups(token.split('=', 1)[1].strip('"'))
    try:
        receipt = run(import_only='-doorsimportonly' in tokens, place_only='-doorsplaceonly' in tokens, groups=groups,
                      allow_unverified_winding='-doorsallowunverifiedwinding' in tokens)
        ue.log('release_import_doors: %s placed %s winding_ok %s' % (receipt['status'], receipt.get('placedActorCount'),
                                                                      receipt.get('windingVerified')))
    except Exception as error:
        ue.log_error('release_import_doors failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(write_plan='--write-plan' in sys.argv), indent=2))
elif _invoked_as_native_script():
    _main()

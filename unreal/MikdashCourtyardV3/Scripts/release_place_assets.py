"""Guarded release placement of ready assets into the combined IntegratedReviewV2 map.

Places four ready groups into /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough:
keruvim (SM_KeruvimStudyV1), a small outer-court group of PilgrimRigV2 skeletal
actors, the TransitV2 bus (13 material-group meshes) and the six Kotel detail
overlays. Every number comes from Scripts/release_place_assets.spec.json so a
human can review the plan before running.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_place_assets.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Placement-01.log"

Optional switches (read from the engine command line):
  -ReleaseGroups=pilgrims        comma-separated subset of keruvim,pilgrims,bus,kotel.
                                 Only the named groups are placed. RELEASE_* actors of
                                 groups NOT requested may already exist from earlier
                                 runs; they are recorded in the receipt and must stay
                                 numerically unchanged. RELEASE_<Group>_* actors of a
                                 REQUESTED group still cause a refusal.
  -ReleaseBusGroundZ=<cm>        explicit bus ground Z (skips the support check).

When executed that way the module detects the commandlet command line, loads the
target map itself and runs place(). Importing the module inside a GUI editor does
nothing; call place(load_target=False, groups=('pilgrims',)) there after loading
the combined map.

Safety model:
  * Refuses to run with the wrong project directory, a game world, dirty packages,
    or a loaded world that is not the combined map.
  * Copies Walkthrough.umap (and any One-File-Per-Actor folders) to
    ReviewCheckpoints/Release-<stamp>/ before any mutation and verifies the copy.
  * Each group validates receipts, triangle counts and bounds against the spec.
    A group that fails validation becomes an OMISSION with numeric evidence; its
    partially spawned actors are destroyed. Guard failures before mutation raise.
  * Saves only if at least one group placed, reloads the map, and reads back
    every placed actor's mesh path and world bounds numerically.
  * The receipt JSON is written at start and again in finally, preserving
    partial state on failure.

Known context limitation: the 2026-09-07 native route audit against this exact
map returned no hit for all 128 downward line traces. This script self-tests
traces first. Pilgrims fall back to the measured floor component top read from
the loaded level; the bus is omitted unless the support traces succeed and pass
the gradient/crossfall checks, or bus_ground_z is passed explicitly.

Pilgrim clearance rule (2026-09-07 lesson): the first run refused the pilgrims
because the clearance box "intersected" the actor 'Derived union of source outer
envelope walls' (Measured architecture/union). That actor is a hollow Boolean
union of 116 outer wall boxes whose AABB (+-8100 XY, Z 300..3425) encloses the
whole court, so a plain AABB test flags every point inside the court. Its
constituent walls are NOT placed as separate actors ("originals retained
hidden"), so the union cannot simply be skipped. Instead, for actors in the union
folder the check decomposes the manifest's source_elements_json boxes (exact
Boolean union of boxes, no offsets; recomposing them reproduces every union's
expectedBoundsUnrealCm exactly) into world AABBs and tests the clearance box
against each box. A pilgrim inside an actual wall or the inner platform is still
rejected; a union whose bounds differ from the manifest or has no decomposition
remains a blocker.
"""
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_place_assets.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so offline_check() can run anywhere.
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def box_from_min_max(minimum, maximum):
    return {'min': [float(v) for v in minimum], 'max': [float(v) for v in maximum]}


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def rotate_box_yaw(local, location, yaw_degrees):
    """World AABB of a local AABB after yaw rotation and translation.

    UE computes component bounds as the AABB of the transformed local box, so
    taking the eight rotated corners reproduces get_actor_bounds numerically.
    """
    yaw = math.radians(yaw_degrees)
    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)
    corners = []
    for x in (local['min'][0], local['max'][0]):
        for y in (local['min'][1], local['max'][1]):
            for z in (local['min'][2], local['max'][2]):
                world_x = location[0] + x * cos_yaw - y * sin_yaw
                world_y = location[1] + x * sin_yaw + y * cos_yaw
                corners.append((world_x, world_y, location[2] + z))
    return {
        'min': [min(c[i] for c in corners) for i in range(3)],
        'max': [max(c[i] for c in corners) for i in range(3)],
    }


def boxes_overlap_volume(a, b):
    """Strictly positive overlap on all three axes; touching planes do not count."""
    for i in range(3):
        if min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) <= 1e-6:
            return False
    return True


def point_in_rect(xy, rect):
    return rect['min'][0] <= xy[0] <= rect['max'][0] and rect['min'][1] <= xy[1] <= rect['max'][1]


def facing_vector(yaw_degrees):
    """Authored rig faces local -Y; rotate (0, -1) by yaw."""
    yaw = math.radians(yaw_degrees)
    return [math.sin(yaw), -math.cos(yaw)]


GROUP_ORDER = ('keruvim', 'pilgrims', 'bus', 'kotel')


def normalise_groups(groups):
    """Validate and canonically order requested group names."""
    if isinstance(groups, str):
        groups = groups.split(',')
    wanted = [g.strip().lower() for g in groups if g.strip()]
    unknown = [g for g in wanted if g not in GROUP_ORDER]
    if unknown:
        raise RuntimeError('Unknown release groups %s; valid: %s' % (unknown, list(GROUP_ORDER)))
    if not wanted:
        raise RuntimeError('No release groups requested')
    return tuple(g for g in GROUP_ORDER if g in wanted)


def load_architecture_manifest(spec):
    """Return {assetName: entry} for the measured architecture manifest."""
    manifest = json.loads((ROOT / spec['pilgrims']['clearance']['architectureManifest']).read_text(encoding='utf-8'))
    return {entry['assetName']: entry for entry in manifest['meshes']}


def union_constituent_boxes(entry):
    """World AABBs (cm) of the source boxes a derived union mesh was built from.

    Source elements are in amot with X east, Y up, Z south; the manifest's
    expectedSourceToUnrealCm is [x*50, z*50, y*50]. 'position' is the box centre
    and 'size' the full extent. The centre convention is verified by
    verify_union_decomposition(): recomposing the boxes reproduces each union's
    expectedBoundsUnrealCm exactly.
    """
    properties = entry.get('sourceProperties') or {}
    if 'source_elements_json' not in properties:
        return None
    metres_per_amah = float(properties.get('source_metres_per_amah', 0.5))
    scale = metres_per_amah * 100.0
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


def verify_union_decomposition(entry, tolerance):
    """Boxes of a union entry, or raise if their recomposed AABB differs from the manifest."""
    boxes = union_constituent_boxes(entry)
    if not boxes:
        raise RuntimeError('Union %s has no box decomposition in the manifest' % entry['assetName'])
    recomposed = {'min': [min(b['min'][i] for b in boxes) for i in range(3)], 'max': [max(b['max'][i] for b in boxes) for i in range(3)]}
    error = box_error(recomposed, entry['expectedBoundsUnrealCm'])
    if error > tolerance:
        raise RuntimeError('Union %s decomposition differs from manifest bounds by %.3f cm' % (entry['assetName'], error))
    return boxes


def clearance_box(xy, ground_z, pilgrims_spec):
    half = pilgrims_spec['clearanceBoxHalfWidthCm']
    return {'min': [xy[0] - half, xy[1] - half, ground_z + 1.0],
            'max': [xy[0] + half, xy[1] + half, ground_z + pilgrims_spec['clearanceHeightCm']]}


def xy_distance_to_box(xy, box):
    dx = max(box['min'][0] - xy[0], xy[0] - box['max'][0], 0.0)
    dy = max(box['min'][1] - xy[1], xy[1] - box['max'][1], 0.0)
    return math.hypot(dx, dy)


def evaluate_clearance(clearance, candidates, union_boxes_by_key):
    """Classify AABB overlaps of a clearance box.

    candidates: iterable of dicts with 'label', 'bounds' and 'unionKey' (None for
    ordinary actors). union_boxes_by_key maps unionKey -> constituent world boxes.
    Returns (blockers, excluded) where blockers are real intersections and
    excluded are hollow union envelopes whose AABB merely encloses the box.
    """
    blockers = []
    excluded = []
    centre_xy = [(clearance['min'][0] + clearance['max'][0]) / 2.0, (clearance['min'][1] + clearance['max'][1]) / 2.0]
    for candidate in candidates:
        if not boxes_overlap_volume(clearance, candidate['bounds']):
            continue
        boxes = union_boxes_by_key.get(candidate.get('unionKey')) if candidate.get('unionKey') else None
        if boxes is None:
            blockers.append({'label': candidate['label'], 'kind': 'actor_aabb'})
            continue
        hits = [b['name'] for b in boxes if boxes_overlap_volume(clearance, b)]
        if hits:
            blockers.append({'label': candidate['label'], 'kind': 'union_constituent_box', 'constituents': hits})
        else:
            excluded.append({'label': candidate['label'], 'kind': 'hollow_union_envelope_aabb_only',
                             'constituentBoxes': len(boxes),
                             'nearestConstituentCm': min(xy_distance_to_box(centre_xy, b) for b in boxes)})
    return blockers, excluded


def offline_check(spec=None):
    """Consistency checks that need no engine. Raises on the first failure."""
    spec = spec or load_spec()
    report = {'assetFilesChecked': 0, 'missingFiles': []}

    files = [spec['keruvim']['meshFile'], spec['pilgrims']['skeletalMeshFile'],
             spec['pilgrims']['idleAnimationFile'], spec['pilgrims']['walkAnimationFile'],
             spec['pilgrims']['floor']['meshFile'], spec['kotel']['baseWall']['meshFile'],
             spec['targetMapFile']]
    files += [disk_path(spec['bus']['meshFolder'] + m['name']).relative_to(ROOT).as_posix() for m in spec['bus']['meshes']]
    files += [disk_path(spec['kotel']['meshFolder'] + m['name']).relative_to(ROOT).as_posix() for m in spec['kotel']['meshes']]
    for relative in files:
        report['assetFilesChecked'] += 1
        if not (ROOT / relative).exists():
            report['missingFiles'].append(relative)
    if report['missingFiles']:
        raise RuntimeError('Missing files on disk: ' + ', '.join(report['missingFiles']))

    keruvim = spec['keruvim']
    planned = rotate_box_yaw(keruvim['localBoundsCm'], keruvim['location'], keruvim['rotation']['yaw'])
    if box_error(planned, keruvim['plannedWorldBoundsCm']) > 1e-6:
        raise RuntimeError('Keruvim planned bounds in spec do not match rotation of local bounds')
    cover = keruvim['aron']['coverWorldBoundsCm']
    if abs(planned['min'][2] - cover['max'][2]) > keruvim['aron']['contactToleranceCm']:
        raise RuntimeError('Keruvim do not rest on the cover plane')
    if any(planned['min'][i] < cover['min'][i] or planned['max'][i] > cover['max'][i] for i in (0, 1)):
        raise RuntimeError('Keruvim footprint exceeds the cover')
    report['keruvimPlannedWorldBoundsCm'] = planned

    pilgrims = spec['pilgrims']
    points = [a['xy'] for a in pilgrims['actors']]
    if not 4 <= len(points) <= 6:
        raise RuntimeError('Pilgrim group must have 4 to 6 actors')
    floor = pilgrims['floor']['worldBoundsCm']
    for xy in points:
        if not (floor['min'][0] < xy[0] < floor['max'][0] and floor['min'][1] < xy[1] < floor['max'][1]):
            raise RuntimeError('Pilgrim outside outer court floor: %r' % (xy,))
        for rect in pilgrims['exclusionRectanglesXY']:
            if point_in_rect(xy, rect):
                raise RuntimeError('Pilgrim %r inside exclusion %s' % (xy, rect['name']))
    minimum_pairwise = min(math.dist(points[i], points[j]) for i in range(len(points)) for j in range(i + 1, len(points)))
    nearest = [min(math.dist(points[i], points[j]) for j in range(len(points)) if j != i) for i in range(len(points))]
    if minimum_pairwise < pilgrims['spacing']['minPairwiseCm']:
        raise RuntimeError('Pilgrims closer than %s cm' % pilgrims['spacing']['minPairwiseCm'])
    if max(nearest) > pilgrims['spacing']['maxNearestNeighbourCm']:
        raise RuntimeError('A pilgrim has no neighbour within %s cm' % pilgrims['spacing']['maxNearestNeighbourCm'])
    report['pilgrimMinPairwiseCm'] = minimum_pairwise
    report['pilgrimNearestNeighbourCm'] = nearest
    report['pilgrimFacingVectors'] = {a['index']: facing_vector(a['yaw']) for a in pilgrims['actors']}
    if abs(pilgrims['sourceIdleBoundsCm']['min'][2] - pilgrims['feetRule']['sourceLocalBoundsMinZCm']) > 1e-6:
        raise RuntimeError('feetRule.sourceLocalBoundsMinZCm disagrees with sourceIdleBoundsCm')
    report['pilgrimFeetOffsetCm'] = 0.0 - pilgrims['feetRule']['sourceLocalBoundsMinZCm']

    # Clearance pre-check against the measured architecture manifest (expected
    # world bounds; unions decomposed into their source boxes).
    clearance_spec = pilgrims['clearance']
    manifest = load_architecture_manifest(spec)
    floor_asset = pilgrims['floor']['mesh'].rsplit('/', 1)[1]
    asset_prefix = clearance_spec['levelAssetPrefix'].rsplit('/', 1)[1]
    union_boxes = {}
    candidates = []
    for name, entry in manifest.items():
        if asset_prefix + name == floor_asset:
            continue
        key = None
        if entry.get('semantic') == 'union':
            union_boxes[name] = verify_union_decomposition(entry, clearance_spec['unionBoundsToleranceCm'])
            key = name
        candidates.append({'label': entry['sourceName'], 'bounds': entry['expectedBoundsUnrealCm'], 'unionKey': key})
    offline_clearance = []
    for actor in pilgrims['actors']:
        box = clearance_box(actor['xy'], pilgrims['floor']['topZ'], pilgrims)
        blockers, excluded = evaluate_clearance(box, candidates, union_boxes)
        if blockers:
            raise RuntimeError('Pilgrim %d clearance box intersects manifest geometry %s' % (actor['index'], blockers))
        offline_clearance.append({'index': actor['index'], 'excludedHollowEnvelopes': excluded})
    report['pilgrimOfflineClearance'] = {'manifestMeshes': len(manifest), 'unionsDecomposed': sorted(union_boxes),
                                         'unionConstituentBoxes': {k: len(v) for k, v in union_boxes.items()},
                                         'perPilgrim': offline_clearance}

    bus = spec['bus']
    union = {'min': [min(m['localBoundsCm']['min'][i] for m in bus['meshes']) for i in range(3)],
             'max': [max(m['localBoundsCm']['max'][i] for m in bus['meshes']) for i in range(3)]}
    if box_error(union, bus['assemblyLocalBoundsCm']) > 1e-6:
        raise RuntimeError('Bus mesh union differs from assembly bounds')
    if abs(union['min'][2] - bus['tireContactLocalZ']) > 1e-6:
        raise RuntimeError('Tire contact is not at local Z 0')
    if len(bus['meshes']) != 13 or len(bus['stationMeshesOmitted']) != 12:
        raise RuntimeError('Expected 13 bus and 12 station meshes (25 total)')
    report['busPlannedWorldBoundsAtGroundZeroCm'] = rotate_box_yaw(union, [bus['xy'][0], bus['xy'][1], 0.0], bus['yaw'])
    evidence = bus['offlineGroundEvidence']['surfaceZCm']
    probes = bus['groundProbes']
    front_cross = abs(evidence['wheel_front_left'] - evidence['wheel_front_right'])
    report['offlineBusCrossfallDegrees'] = math.degrees(math.atan(front_cross / probes['trackCm']))
    report['offlineBusSupportWouldPass'] = report['offlineBusCrossfallDegrees'] <= probes['maxCrossfallDegrees']

    if len(spec['kotel']['meshes']) != 6:
        raise RuntimeError('Expected six Kotel overlays')
    report['kotelDetailTriangles'] = sum(m['triangles'] for m in spec['kotel']['meshes'])
    if report['kotelDetailTriangles'] != spec['kotel']['totalDetailTriangles']:
        raise RuntimeError('Kotel triangle total differs from manifest')
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine-side placement
# --------------------------------------------------------------------------

def _vector_list(v):
    return [float(v.x), float(v.y), float(v.z)]


def _rotator_list(r):
    return [float(r.pitch), float(r.yaw), float(r.roll)]


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _actor_bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return box_from_min_max([origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
                            [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z])


def _actor_pose(actor):
    return {'location': _vector_list(actor.get_actor_location()),
            'rotation': _rotator_list(actor.get_actor_rotation()),
            'scale': _vector_list(actor.get_actor_scale3d())}


def _pose_close(pose, location, rotation, scale, tolerance):
    errors = [abs(pose['location'][i] - location[i]) for i in range(3)]
    errors += [abs(pose['rotation'][i] - rotation[i]) for i in range(3)]
    errors += [abs(pose['scale'][i] - scale[i]) for i in range(3)]
    return max(errors) <= tolerance, max(errors)


def _static_mesh_box(mesh):
    box = mesh.get_bounding_box()
    return box_from_min_max([box.min.x, box.min.y, box.min.z], [box.max.x, box.max.y, box.max.z])


def _enum_name(enum_class, value, candidates):
    for name in candidates:
        if hasattr(enum_class, name) and getattr(enum_class, name) == value:
            return name
    return str(value)


class Placement:
    """Holds engine handles, cached scene snapshot and the receipt."""

    def __init__(self, ue, spec, bus_ground_z=None):
        self.ue = ue
        self.spec = spec
        self.bus_ground_z = bus_ground_z
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.world = None
        self.snapshot = None
        self.receipt = None
        self.receipt_path = None
        self.trace_method = None

    # -- receipt -----------------------------------------------------------

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    # -- scene snapshot ------------------------------------------------------

    def take_snapshot(self):
        ue = self.ue
        rows = []
        for actor in self.actors.get_all_level_actors():
            meshes = []
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                meshes.append(_asset_path(component.get_editor_property('static_mesh')))
            for component in actor.get_components_by_class(ue.SkeletalMeshComponent):
                meshes.append(_asset_path(component.get_skeletal_mesh_asset()))
            rows.append({'actor': actor, 'name': actor.get_name(), 'label': actor.get_actor_label(),
                         'folder': str(actor.get_folder_path()), 'meshes': meshes,
                         'pose': _actor_pose(actor), 'bounds': _actor_bounds(actor)})
        self.snapshot = rows
        return rows

    def numeric_baseline(self, rows):
        return {row['name']: (row['label'], tuple(row['meshes']),
                              tuple(row['pose']['location'] + row['pose']['rotation'] + row['pose']['scale'])) for row in rows}

    def actors_with_mesh(self, asset_path):
        return [row for row in self.snapshot if asset_path in row['meshes']]

    # -- tracing ---------------------------------------------------------------

    def trace_down(self, start, end):
        """Try three query styles; return (hit_dict or None, method_name or None)."""
        ue = self.ue
        common = dict(world_context_object=self.world, start=ue.Vector(*start), end=ue.Vector(*end),
                      trace_complex=True, actors_to_ignore=[], draw_debug_type=ue.DrawDebugTrace.NONE, ignore_self=False)
        attempts = [
            ('profile_Pawn', lambda: ue.SystemLibrary.line_trace_single_by_profile(profile_name='Pawn', **common)),
            ('channel_Visibility', lambda: ue.SystemLibrary.line_trace_single(
                trace_channel=getattr(ue.TraceTypeQuery, 'ECC_VISIBILITY', getattr(ue.TraceTypeQuery, 'TRACE_TYPE_QUERY1', None)), **common)),
            ('objects_WorldStatic', lambda: ue.SystemLibrary.line_trace_single_for_objects(
                object_types=[getattr(ue.ObjectTypeQuery, 'ECC_WORLD_STATIC', getattr(ue.ObjectTypeQuery, 'OBJECT_TYPE_QUERY1', None))], **common)),
        ]
        if self.trace_method:
            attempts.sort(key=lambda item: item[0] != self.trace_method)
        for method, call in attempts:
            try:
                hit = call()
            except Exception as error:
                self.receipt.setdefault('traceErrors', []).append({'method': method, 'error': str(error)})
                continue
            if hit is None:
                continue
            parsed = self._parse_hit(hit)
            if parsed is None:
                continue
            self.trace_method = method
            return parsed, method
        return None, None

    def _parse_hit(self, hit):
        ue = self.ue
        try:
            split = ue.GameplayStatics.break_hit_result(hit)
        except Exception as error:
            self.receipt.setdefault('traceErrors', []).append({'method': 'break_hit_result', 'error': str(error)})
            return None
        if len(split) < 16:
            self.receipt.setdefault('traceErrors', []).append({'method': 'break_hit_result', 'error': 'unexpected tuple length %d' % len(split)})
            return None
        blocking = bool(split[0])
        point = split[5]
        normal = split[7]
        actor = split[9]
        component = split[10]
        if not blocking:
            return None
        mesh = None
        if isinstance(component, ue.StaticMeshComponent):
            mesh = _asset_path(component.get_editor_property('static_mesh'))
        return {'pointCm': _vector_list(point), 'normal': _vector_list(normal),
                'actor': actor.get_actor_label() if actor else None,
                'component': component.get_path_name() if component else None, 'mesh': mesh}

    def trace_self_test(self):
        test = self.spec['traceSelfTest']
        rows = []
        passed = 0
        for probe in test['probes']:
            hit, method = self.trace_down(probe['start'], probe['end'])
            row = dict(probe, hit=hit, method=method)
            if hit and abs(hit['pointCm'][2] - probe['expectedZ']) <= test['toleranceCm'] and hit['mesh'] == probe['expectedMesh']:
                row['result'] = 'PASS'
                passed += 1
            elif hit:
                row['result'] = 'HIT_BUT_UNEXPECTED'
            else:
                row['result'] = 'NO_HIT'
            rows.append(row)
        result = {'probes': rows, 'passed': passed == len(rows), 'anyHit': any(r['hit'] for r in rows)}
        self.receipt['traceSelfTest'] = result
        return result

    # -- shared spawn helpers ------------------------------------------------

    def spawn_static(self, mesh, location, rotation, label, folder, collision_profile, extra_tags):
        ue = self.ue
        actor = self.actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(*location),
                                                   ue.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]), transient=False)
        if actor is None:
            raise RuntimeError('StaticMeshActor spawn returned None for ' + label)
        actor.set_actor_label(label)
        actor.set_folder_path(folder)
        actor.set_editor_property('tags', [ue.Name(self.spec['actorTag'])] + [ue.Name(t) for t in extra_tags])
        component = actor.get_component_by_class(ue.StaticMeshComponent)
        if component is None:
            raise RuntimeError('Spawned actor has no StaticMeshComponent: ' + label)
        if not component.set_static_mesh(mesh):
            raise RuntimeError('set_static_mesh returned False for ' + label)
        if _asset_path(component.get_editor_property('static_mesh')) != _asset_path(mesh):
            raise RuntimeError('Static mesh readback differs for ' + label)
        component.set_collision_profile_name(collision_profile)
        if collision_profile == 'NoCollision':
            component.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        return actor, component

    def destroy_all(self, actors):
        for actor in actors:
            try:
                self.actors.destroy_actor(actor)
            except Exception as error:
                self.receipt.setdefault('cleanupErrors', []).append(str(error))

    def check_static_mesh(self, asset_path, triangles, local_bounds, tolerance):
        ue = self.ue
        mesh = ue.load_asset(asset_path)
        if not isinstance(mesh, ue.StaticMesh):
            raise RuntimeError('Not a StaticMesh: ' + asset_path)
        actual_triangles = mesh.get_num_triangles(0)
        if actual_triangles != triangles:
            raise RuntimeError('%s triangles %d differ from receipt %d' % (asset_path, actual_triangles, triangles))
        actual_box = _static_mesh_box(mesh)
        error = box_error(actual_box, local_bounds)
        if error > tolerance:
            raise RuntimeError('%s bounds differ from receipt by %.4f cm' % (asset_path, error))
        return mesh, actual_box

    def refuse_existing_mesh(self, asset_path):
        rows = self.actors_with_mesh(asset_path)
        if rows:
            raise RuntimeError('Mesh already present in map (%s): %s' % (asset_path, [r['label'] for r in rows]))

    # -- group: keruvim ------------------------------------------------------

    def place_keruvim(self):
        ue = self.ue
        spec = self.spec['keruvim']
        tolerance = self.spec['verification']['staticBoundsToleranceCm']
        native = json.loads((ROOT / spec['receipt']).read_text(encoding='utf-8'))
        if native['status'] != spec['receiptStatusRequired']:
            raise RuntimeError('Keruvim native receipt status ' + native['status'])
        if not any(created.split('.')[0] == spec['mesh'] for created in native['created']):
            raise RuntimeError('Keruvim mesh not in native receipt')
        placement = json.loads((ROOT / spec['placementSpec']).read_text(encoding='utf-8'))
        if [float(v) for v in placement['position_cm']] != spec['location'] or float(placement['yaw_degrees']) != spec['rotation']['yaw']:
            raise RuntimeError('Keruvim placement spec disagrees with release spec')
        self.refuse_existing_mesh(spec['mesh'])

        aron = spec['aron']
        manifest = json.loads((ROOT / aron['manifest']).read_text(encoding='utf-8'))
        if len(manifest['parts']) != aron['partCount']:
            raise RuntimeError('Aron manifest part count differs')
        aron_rows = []
        cover_bounds = None
        for record in manifest['parts']:
            label = aron['labelPrefix'] + record['name']
            matching = [row for row in self.snapshot if row['label'] == label]
            if len(matching) != 1:
                raise RuntimeError('Aron part missing or duplicated in combined map: ' + label)
            row = matching[0]
            if row['meshes'] != [aron['meshPrefix'] + record['name']]:
                raise RuntimeError('Aron part mesh differs: ' + label)
            close, error = _pose_close(row['pose'], aron['sharedOrigin'], [0.0, aron['yaw'], 0.0], [1.0, 1.0, 1.0],
                                       self.spec['verification']['transformToleranceCm'])
            if not close:
                raise RuntimeError('Aron transform changed for %s by %.4f' % (label, error))
            expected = rotate_box_yaw(record['expectedBoundsCm'], aron['sharedOrigin'], aron['yaw'])
            if box_error(row['bounds'], expected) > tolerance:
                raise RuntimeError('Aron bounds changed for ' + label)
            aron_rows.append(row)
            if record['name'] == aron['coverPart']:
                cover_bounds = row['bounds']
        if cover_bounds is None or box_error(cover_bounds, aron['coverWorldBoundsCm']) > tolerance:
            raise RuntimeError('Kaporet cover bounds differ from spec')

        mesh, local = self.check_static_mesh(spec['mesh'], spec['triangles'], spec['localBoundsCm'], tolerance)
        planned = rotate_box_yaw(local, spec['location'], spec['rotation']['yaw'])
        if abs(planned['min'][2] - cover_bounds['max'][2]) > aron['contactToleranceCm']:
            raise RuntimeError('Keruvim base %.4f does not meet cover top %.4f' % (planned['min'][2], cover_bounds['max'][2]))
        if any(planned['min'][i] < cover_bounds['min'][i] - tolerance or planned['max'][i] > cover_bounds['max'][i] + tolerance for i in (0, 1)):
            raise RuntimeError('Keruvim footprint leaves the cover')
        for row in aron_rows:
            if boxes_overlap_volume(planned, row['bounds']):
                raise RuntimeError('Keruvim volume intersects Aron part ' + row['label'])
        for row in self.snapshot:
            if row in aron_rows or not row['meshes']:
                continue
            if boxes_overlap_volume(planned, row['bounds']) and all(row['bounds']['max'][i] - row['bounds']['min'][i] < 2000 for i in range(3)):
                raise RuntimeError('Keruvim volume intersects existing small actor ' + row['label'])

        label = self.spec['labelPrefix'] + spec['group'] + '_1'
        actor, component = self.spawn_static(mesh, spec['location'], [0.0, spec['rotation']['yaw'], 0.0], label,
                                             spec['folder'], spec['collisionProfile'], ['Release' + spec['group']])
        placed_bounds = _actor_bounds(actor)
        if box_error(placed_bounds, planned) > tolerance:
            self.destroy_all([actor])
            raise RuntimeError('Placed keruvim bounds differ from plan by %.4f' % box_error(placed_bounds, planned))
        return {'actors': [{'label': label, 'kind': 'StaticMeshActor', 'mesh': spec['mesh'], 'location': spec['location'],
                            'rotation': [0.0, spec['rotation']['yaw'], 0.0], 'scale': [1.0, 1.0, 1.0],
                            'collisionProfile': spec['collisionProfile'], 'plannedWorldBoundsCm': planned,
                            'placedWorldBoundsCm': placed_bounds, 'actor': actor}],
                'coverWorldBoundsCm': cover_bounds, 'coverHeightAddedTwice': False,
                'note': 'Local geometry starts at cover height; actor Z equals shared Aron origin Z.'}

    # -- group: pilgrims -----------------------------------------------------

    def place_pilgrims(self, trace_result):
        ue = self.ue
        spec = self.spec['pilgrims']
        verify = self.spec['verification']
        native = json.loads((ROOT / spec['receipt']).read_text(encoding='utf-8'))
        if native['status'] != spec['receiptStatusRequired']:
            raise RuntimeError('Pilgrim native receipt status ' + native['status'])
        recorded = {a['path'].split('.')[0] for a in native['assets']}
        for key in ('skeletalMesh', 'idleAnimation', 'walkAnimation'):
            if spec[key] not in recorded:
                raise RuntimeError('Pilgrim asset not in native receipt: ' + spec[key])
        self.refuse_existing_mesh(spec['skeletalMesh'])

        mesh = ue.load_asset(spec['skeletalMesh'])
        if not isinstance(mesh, ue.SkeletalMesh):
            raise RuntimeError('Not a SkeletalMesh: ' + spec['skeletalMesh'])
        idle = ue.load_asset(spec['idleAnimation'])
        walk = ue.load_asset(spec['walkAnimation'])
        if not isinstance(idle, ue.AnimSequence) or not isinstance(walk, ue.AnimSequence):
            raise RuntimeError('Pilgrim animations are not AnimSequence assets')
        mesh_skeleton = _asset_path(mesh.get_editor_property('skeleton'))
        for anim in (idle, walk):
            if _asset_path(anim.get_editor_property('skeleton')) != mesh_skeleton:
                raise RuntimeError('Animation skeleton differs from mesh skeleton: ' + _asset_path(anim))
        mesh_box = None
        try:
            bounds = mesh.get_bounds()
            origin = bounds.origin
            extent = bounds.box_extent
            mesh_box = box_from_min_max([origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
                                        [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z])
        except Exception as error:
            self.receipt.setdefault('apiNotes', []).append('SkeletalMesh.get_bounds unavailable: ' + str(error))
        sanity = spec['meshSanity']
        if mesh_box is not None:
            height = mesh_box['max'][2] - mesh_box['min'][2]
            if not (sanity['minFeetZ'] <= mesh_box['min'][2] <= sanity['maxFeetZ']) or not (sanity['minHeight'] <= height <= sanity['maxHeight']):
                raise RuntimeError('Skeletal mesh bounds implausible for a standing figure: %r' % (mesh_box,))

        floor_spec = spec['floor']
        floor_rows = self.actors_with_mesh(floor_spec['mesh'])
        if len(floor_rows) != 1:
            raise RuntimeError('Expected exactly one outer court floor component, found %d' % len(floor_rows))
        floor_row = floor_rows[0]
        close, error = _pose_close(floor_row['pose'], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [1.0, 1.0, 1.0], verify['transformToleranceCm'])
        if not close:
            raise RuntimeError('Outer court floor is not at identity')
        if box_error(floor_row['bounds'], floor_spec['worldBoundsCm']) > 1.0:
            raise RuntimeError('Outer court floor bounds differ from manifest: %r' % (floor_row['bounds'],))
        measured_floor_top = floor_row['bounds']['max'][2]
        if abs(measured_floor_top - floor_spec['topZ']) > 1.0:
            raise RuntimeError('Measured floor top %.3f differs from spec topZ %.3f' % (measured_floor_top, floor_spec['topZ']))

        # Feet rule: the rig origin is at the feet (source idle bounds min Z 0.0,
        # height 182), so actor Z = floor top + (0 - localBoundsMinZ) = floor top.
        feet_offset = 0.0 - float(spec['feetRule']['sourceLocalBoundsMinZCm'])
        if mesh_box is not None and abs(mesh_box['min'][2] - spec['feetRule']['sourceLocalBoundsMinZCm']) > spec['feetRule']['engineMinZToleranceCm']:
            raise RuntimeError('Engine skeletal bounds min Z %.2f disagrees with source feet plane %.2f' % (mesh_box['min'][2], spec['feetRule']['sourceLocalBoundsMinZCm']))

        # Clearance candidates: every mesh-bearing actor except the floor. Actors
        # in the union folder are matched to their manifest entry so the hollow
        # envelope can be tested against its constituent wall boxes.
        clearance_spec = spec['clearance']
        manifest = load_architecture_manifest(self.spec)
        prefix = clearance_spec['levelAssetPrefix']
        union_boxes = {}
        candidates = []
        union_rows = []
        for row in self.snapshot:
            if not row['meshes'] or row is floor_row:
                continue
            key = None
            if row['folder'] == clearance_spec['unionFolder']:
                names = [m[len(prefix):] for m in row['meshes'] if m and m.startswith(prefix)]
                entry = manifest.get(names[0]) if len(names) == 1 and len(row['meshes']) == 1 else None
                if entry is not None and entry.get('semantic') == 'union' and box_error(row['bounds'], entry['expectedBoundsUnrealCm']) <= clearance_spec['unionBoundsToleranceCm']:
                    key = names[0]
                    union_boxes[key] = verify_union_decomposition(entry, clearance_spec['unionBoundsToleranceCm'])
                union_rows.append({'label': row['label'], 'mesh': row['meshes'], 'worldBoundsCm': row['bounds'],
                                   'decomposed': key is not None, 'constituentBoxes': len(union_boxes[key]) if key else 0,
                                   'treatment': 'constituent_box_test' if key else 'aabb_blocker_no_verified_decomposition'})
            candidates.append({'label': row['label'], 'bounds': row['bounds'], 'unionKey': key})
        zone_centre = [sum(a['xy'][0] for a in spec['actors']) / len(spec['actors']), sum(a['xy'][1] for a in spec['actors']) / len(spec['actors'])]
        nearby = sorted(({'label': c['label'], 'worldBoundsCm': c['bounds'], 'xyDistanceCm': xy_distance_to_box(zone_centre, c['bounds'])}
                         for c in candidates if c['unionKey'] is None and xy_distance_to_box(zone_centre, c['bounds']) <= clearance_spec['nearRadiusCm']
                         and c['bounds']['max'][2] > measured_floor_top and c['bounds']['min'][2] < measured_floor_top + spec['clearanceHeightCm']),
                        key=lambda r: r['xyDistanceCm'])
        clearance_report = {'actorsConsidered': len(candidates), 'floorActorExcluded': floor_row['label'],
                            'unionFolder': clearance_spec['unionFolder'], 'unionActors': union_rows,
                            'nearRadiusCm': clearance_spec['nearRadiusCm'], 'zoneCentreXY': zone_centre,
                            'nearbyNonUnionActorsCrossingClearanceHeight': nearby, 'perPilgrim': []}

        placed = []
        records = []
        try:
            for entry in spec['actors']:
                xy = entry['xy']
                if not (floor_row['bounds']['min'][0] < xy[0] < floor_row['bounds']['max'][0] and floor_row['bounds']['min'][1] < xy[1] < floor_row['bounds']['max'][1]):
                    raise RuntimeError('Pilgrim %d outside floor bounds' % entry['index'])
                for rect in spec['exclusionRectanglesXY']:
                    if point_in_rect(xy, rect):
                        raise RuntimeError('Pilgrim %d inside exclusion %s' % (entry['index'], rect['name']))
                hit, method = self.trace_down([xy[0], xy[1], 500.0], [xy[0], xy[1], 200.0])
                if hit and hit['mesh'] == floor_spec['mesh'] and abs(hit['pointCm'][2] - floor_spec['topZ']) <= 2.0:
                    ground_z = hit['pointCm'][2]
                    ground_source = 'line_trace_' + method
                elif hit:
                    raise RuntimeError('Pilgrim %d trace hit unexpected geometry %s at %r' % (entry['index'], hit['mesh'], hit['pointCm']))
                elif trace_result['anyHit']:
                    raise RuntimeError('Pilgrim %d: traces work in this process but nothing under the candidate' % entry['index'])
                else:
                    ground_z = measured_floor_top
                    ground_source = 'floor_component_bounds_fallback'
                clearance = clearance_box(xy, ground_z, spec)
                blockers, excluded = evaluate_clearance(clearance, candidates, union_boxes)
                clearance_report['perPilgrim'].append({'index': entry['index'], 'clearanceBoxCm': clearance, 'blockers': blockers,
                                                       'excludedHollowEnvelopes': excluded})
                if blockers:
                    raise RuntimeError('Pilgrim %d clearance box intersects %s' % (entry['index'], blockers))

                label = self.spec['labelPrefix'] + spec['group'] + '_%d' % entry['index']
                location = [xy[0], xy[1], ground_z + feet_offset]
                rotation = [0.0, float(entry['yaw']), 0.0]
                actor = self.actors.spawn_actor_from_class(ue.SkeletalMeshActor, ue.Vector(*location),
                                                           ue.Rotator(pitch=0.0, yaw=rotation[1], roll=0.0), transient=False)
                if actor is None:
                    raise RuntimeError('SkeletalMeshActor spawn returned None')
                placed.append(actor)
                actor.set_actor_label(label)
                actor.set_folder_path(spec['folder'])
                actor.set_editor_property('tags', [ue.Name(self.spec['actorTag']), ue.Name('Release' + spec['group'])])
                component = actor.get_component_by_class(ue.SkeletalMeshComponent)
                if component is None:
                    raise RuntimeError('SkeletalMeshActor has no SkeletalMeshComponent')
                if hasattr(component, 'set_skeletal_mesh_asset'):
                    component.set_skeletal_mesh_asset(mesh)
                else:
                    component.set_skeletal_mesh(mesh, True)
                if _asset_path(component.get_skeletal_mesh_asset()) != spec['skeletalMesh']:
                    raise RuntimeError('Skeletal mesh readback differs for ' + label)
                component.set_collision_profile_name(spec['collisionProfile'])
                anim = idle if entry['animation'] == 'idle' else walk
                component.set_animation_mode(ue.AnimationMode.ANIMATION_SINGLE_NODE)
                component.override_animation_data(anim, True, True, float(entry['phaseSeconds']), 1.0)
                data = component.get_editor_property('animation_data')
                if _asset_path(data.get_editor_property('anim_to_play')) != _asset_path(anim):
                    raise RuntimeError('Animation data readback differs for ' + label)

                bones = {}
                for bone in ('pelvis', 'head', 'foot_l', 'ball_l', 'hand_l'):
                    if component.does_socket_exist(bone):
                        bones[bone] = _vector_list(component.get_socket_location(bone))
                if 'head' in bones and 'foot_l' in bones:
                    if bones['head'][2] - bones['foot_l'][2] < 120.0:
                        raise RuntimeError('Pilgrim %s is not upright (head-foot dz %.1f)' % (label, bones['head'][2] - bones['foot_l'][2]))
                facing_world = None
                if 'ball_l' in bones and 'foot_l' in bones:
                    dx = bones['ball_l'][0] - bones['foot_l'][0]
                    dy = bones['ball_l'][1] - bones['foot_l'][1]
                    length = math.hypot(dx, dy)
                    facing_world = [dx / length, dy / length] if length > 1e-6 else None
                placed_bounds = _actor_bounds(actor)
                if abs(placed_bounds['min'][2] - ground_z) > verify['skeletalFeetToleranceCm']:
                    raise RuntimeError('Pilgrim %s feet %.1f cm from ground' % (label, placed_bounds['min'][2] - ground_z))
                records.append({'label': label, 'kind': 'SkeletalMeshActor', 'mesh': spec['skeletalMesh'], 'animation': _asset_path(anim),
                                'phaseSeconds': entry['phaseSeconds'], 'location': location, 'rotation': rotation, 'scale': [1.0, 1.0, 1.0],
                                'collisionProfile': spec['collisionProfile'], 'groundZ': ground_z, 'groundSource': ground_source,
                                'feetOffsetCm': feet_offset, 'groundHit': hit, 'expectedFacingXY': facing_vector(entry['yaw']),
                                'boneWorldLocations': bones, 'measuredFacingXY': facing_world, 'placedWorldBoundsCm': placed_bounds, 'actor': actor})
        except Exception:
            clearance_report['failed'] = True
            self.receipt['pilgrimClearanceCheck'] = clearance_report
            self.destroy_all(placed)
            raise
        return {'actors': records, 'skeletalMeshBoundsCm': mesh_box, 'engineMeshLocalBoundsMinZCm': mesh_box['min'][2] if mesh_box else None,
                'measuredFloorTopZ': measured_floor_top, 'floorActor': floor_row['label'], 'floorMesh': floor_spec['mesh'],
                'groundSources': sorted({r['groundSource'] for r in records}), 'traceSelfTestAnyHit': bool(trace_result['anyHit']),
                'feetOffsetCm': feet_offset, 'feetRule': spec['feetRule']['rule'], 'clearanceCheck': clearance_report,
                'walkAnimationAssigned': False, 'note': 'Idle figures only; not goal-directed AI or crowd behaviour.'}

    # -- group: bus ------------------------------------------------------------

    def place_bus(self, trace_result):
        spec = self.spec['bus']
        tolerance = self.spec['verification']['staticBoundsToleranceCm']
        native = json.loads((ROOT / spec['receipt']).read_text(encoding='utf-8'))
        if native['status'] != spec['receiptStatusRequired']:
            raise RuntimeError('TransitV2 native receipt status ' + native['status'])
        created = {c.split('.')[0] for c in native['created']}
        meshes = []
        for record in spec['meshes']:
            asset_path = spec['meshFolder'] + record['name']
            if asset_path not in created:
                raise RuntimeError('Bus mesh not in native receipt: ' + asset_path)
            self.refuse_existing_mesh(asset_path)
            mesh, box = self.check_static_mesh(asset_path, record['triangles'], record['localBoundsCm'], tolerance)
            body = mesh.get_editor_property('body_setup')
            flag = str(body.get_editor_property('collision_trace_flag')) if body else None
            meshes.append({'path': asset_path, 'mesh': mesh, 'local': box, 'collisionTraceFlag': flag})
        union = {'min': [min(m['local']['min'][i] for m in meshes) for i in range(3)],
                 'max': [max(m['local']['max'][i] for m in meshes) for i in range(3)]}
        if box_error(union, spec['assemblyLocalBoundsCm']) > tolerance:
            raise RuntimeError('Bus assembly bounds differ from offline checks')

        probes = spec['groundProbes']
        yaw = math.radians(spec['yaw'])
        support = {}
        for name, (lx, ly) in probes['localPointsCm'].items():
            wx = spec['xy'][0] + lx * math.cos(yaw) - ly * math.sin(yaw)
            wy = spec['xy'][1] + lx * math.sin(yaw) + ly * math.cos(yaw)
            hit, method = self.trace_down([wx, wy, probes['traceStartZ']], [wx, wy, probes['traceEndZ']])
            support[name] = {'xy': [wx, wy], 'hit': hit, 'method': method}
        evidence = {'supportProbes': support, 'offlineGroundEvidence': spec['offlineGroundEvidence']}

        if self.bus_ground_z is not None:
            ground_z = float(self.bus_ground_z)
            ground_source = 'explicit_bus_ground_z_argument'
            evidence['supportCheck'] = 'SKIPPED_EXPLICIT_Z'
        else:
            missing = [name for name, row in support.items() if row['hit'] is None]
            if missing:
                reason = 'No support hit at %s' % missing
                if not trace_result['anyHit']:
                    reason += '; traces returned nothing in this process (see traceSelfTest)'
                raise OmissionError(reason, evidence)
            wrong = [name for name, row in support.items() if not (row['hit']['mesh'] or '').startswith(probes['requiredSupportMeshPrefix'])]
            if wrong:
                raise OmissionError('Support under %s is not a mapped street mesh' % wrong, evidence)
            z = {name: row['hit']['pointCm'][2] for name, row in support.items()}
            spread = max(z.values()) - min(z.values())
            gradient = math.degrees(math.atan(abs((z['wheel_front_left'] + z['wheel_front_right']) - (z['wheel_rear_left'] + z['wheel_rear_right'])) / 2.0 / probes['wheelbaseCm']))
            crossfall = math.degrees(math.atan(max(abs(z['wheel_front_left'] - z['wheel_front_right']), abs(z['wheel_rear_left'] - z['wheel_rear_right'])) / probes['trackCm']))
            evidence['supportCheck'] = {'wheelZ': z, 'spreadCm': spread, 'gradientDegrees': gradient, 'crossfallDegrees': crossfall}
            if spread > probes['maxWheelSpreadCm'] or gradient > probes['maxGradientDegrees'] or crossfall > probes['maxCrossfallDegrees']:
                raise OmissionError('Inconsistent support: spread %.1f cm, gradient %.1f deg, crossfall %.1f deg' % (spread, gradient, crossfall), evidence)
            ground_z = z['center']
            ground_source = 'line_trace_' + support['center']['method']

        location = [spec['xy'][0], spec['xy'][1], ground_z - spec['tireContactLocalZ']]
        rotation = [0.0, spec['yaw'], 0.0]
        placed = []
        records = []
        try:
            for index, entry in enumerate(meshes, start=1):
                label = self.spec['labelPrefix'] + spec['group'] + '_%d' % index
                planned = rotate_box_yaw(entry['local'], location, spec['yaw'])
                actor, component = self.spawn_static(entry['mesh'], location, rotation, label, spec['folder'],
                                                     spec['collisionProfile'], ['Release' + spec['group'], entry['path'].rsplit('/', 1)[1]])
                placed.append(actor)
                placed_bounds = _actor_bounds(actor)
                if box_error(placed_bounds, planned) > tolerance:
                    raise RuntimeError('Bus part %s bounds differ from plan by %.4f' % (label, box_error(placed_bounds, planned)))
                records.append({'label': label, 'kind': 'StaticMeshActor', 'mesh': entry['path'], 'location': location, 'rotation': rotation,
                                'scale': [1.0, 1.0, 1.0], 'collisionProfile': spec['collisionProfile'],
                                'meshCollisionTraceFlag': entry['collisionTraceFlag'], 'plannedWorldBoundsCm': planned,
                                'placedWorldBoundsCm': placed_bounds, 'actor': actor})
        except Exception:
            self.destroy_all(placed)
            raise
        return {'actors': records, 'groundZ': ground_z, 'groundSource': ground_source, 'evidence': evidence,
                'stationMeshesOmitted': spec['stationMeshesOmitted'], 'stationOmissionReason': spec['stationOmissionReason'],
                'pawnBlockingEstablished': False, 'boardingClaimed': False}

    # -- group: kotel ------------------------------------------------------

    def kotel_base_state(self):
        ue = self.ue
        base = self.spec['kotel']['baseWall']
        found = []
        for actor in self.actors.get_all_level_actors():
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                if _asset_path(component.get_editor_property('static_mesh')) == base['mesh']:
                    found.append((actor, component))
        if len(found) != 1:
            raise RuntimeError('Expected exactly one Kotel base component, found %d' % len(found))
        actor, component = found[0]
        mesh = component.get_editor_property('static_mesh')
        if mesh.get_num_triangles(0) != base['triangles']:
            raise RuntimeError('Kotel base triangle count changed')
        location = component.get_world_location()
        rotation = component.get_world_rotation()
        scale = component.get_world_scale()
        if max(abs(v) for v in (location.x, location.y, location.z, rotation.pitch, rotation.yaw, rotation.roll)) > 1e-3:
            raise RuntimeError('Kotel base is not at identity')
        if max(abs(v - 1.0) for v in (scale.x, scale.y, scale.z)) > 1e-3:
            raise RuntimeError('Kotel base scale is not one')
        return {'label': actor.get_actor_label(), 'name': actor.get_name(),
                'materials': [_asset_path(component.get_material(i)) for i in range(component.get_num_materials())],
                'overrides': [_asset_path(m) for m in component.get_editor_property('override_materials')],
                'collisionProfile': str(component.get_collision_profile_name()),
                'collisionEnabled': _enum_name(ue.CollisionEnabled, component.get_collision_enabled(),
                                               ['NO_COLLISION', 'QUERY_ONLY', 'PHYSICS_ONLY', 'QUERY_AND_PHYSICS', 'PROBE_ONLY', 'QUERY_AND_PROBE']),
                'location': _vector_list(location), 'rotation': _rotator_list(rotation), 'scale': _vector_list(scale)}

    def place_kotel(self):
        spec = self.spec['kotel']
        tolerance = self.spec['verification']['staticBoundsToleranceCm']
        native = json.loads((ROOT / spec['receipt']).read_text(encoding='utf-8'))
        if native['status'] != spec['receiptStatusRequired']:
            raise RuntimeError('Kotel native receipt status ' + native['status'])
        recorded = {a['mesh'].split('.')[0] for a in native['assets']}
        manifest = json.loads((ROOT / spec['manifest']).read_text(encoding='utf-8'))
        manifest_rows = {m['name']: m for m in manifest['meshes']}
        base_before = self.kotel_base_state()
        meshes = []
        for record in spec['meshes']:
            asset_path = spec['meshFolder'] + record['name']
            if asset_path not in recorded:
                raise RuntimeError('Kotel mesh not in native receipt: ' + asset_path)
            if manifest_rows[record['name']]['triangles'] != record['triangles']:
                raise RuntimeError('Kotel manifest triangles differ for ' + record['name'])
            self.refuse_existing_mesh(asset_path)
            mesh, box = self.check_static_mesh(asset_path, record['triangles'], record['localBoundsCm'], tolerance)
            meshes.append({'path': asset_path, 'mesh': mesh, 'local': box})
        source = spec['sourceBaseBoundsCm']
        for entry in meshes:
            if entry['local']['max'][0] - source['max'][0] > spec['maxProtrusionCm'] + 1.0 or source['min'][0] - entry['local']['min'][0] > spec['maxProtrusionCm'] + 1.0:
                raise RuntimeError('Kotel overlay extends unexpectedly beyond the source base in X: ' + entry['path'])
        placed = []
        records = []
        try:
            for index, entry in enumerate(meshes, start=1):
                label = self.spec['labelPrefix'] + spec['group'] + '_%d' % index
                actor, component = self.spawn_static(entry['mesh'], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], label, spec['folder'],
                                                     spec['collisionProfile'], ['Release' + spec['group'], entry['path'].rsplit('/', 1)[1]])
                placed.append(actor)
                placed_bounds = _actor_bounds(actor)
                if box_error(placed_bounds, entry['local']) > tolerance:
                    raise RuntimeError('Kotel overlay %s bounds differ at identity by %.4f' % (label, box_error(placed_bounds, entry['local'])))
                records.append({'label': label, 'kind': 'StaticMeshActor', 'mesh': entry['path'], 'location': [0.0, 0.0, 0.0],
                                'rotation': [0.0, 0.0, 0.0], 'scale': [1.0, 1.0, 1.0], 'collisionProfile': spec['collisionProfile'],
                                'plannedWorldBoundsCm': entry['local'], 'placedWorldBoundsCm': placed_bounds, 'actor': actor})
            base_after = self.kotel_base_state()
            if base_after != base_before:
                raise RuntimeError('Kotel base state changed during overlay placement')
        except Exception:
            self.destroy_all(placed)
            raise
        return {'actors': records, 'baseWallState': base_before, 'baseWallPreserved': True}


class OmissionError(Exception):
    """A group cannot be placed safely; carries numeric evidence for the receipt."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


def _strip_actor_handles(record):
    return {key: value for key, value in record.items() if key != 'actor'}


def place(load_target=True, bus_ground_z=None, groups=GROUP_ORDER):
    """Run the guarded placement. Returns the receipt dict; raises on guard failure.

    groups: subset of GROUP_ORDER. RELEASE_* actors of groups that are NOT
    requested may already exist (earlier runs); they are recorded in the receipt
    and must remain numerically unchanged. Existing actors of a requested group
    cause a refusal before any mutation.
    """
    import unreal as ue
    groups = normalise_groups(groups)
    spec = load_spec()
    offline = offline_check(spec)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    run = Placement(ue, spec, bus_ground_z)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target:
        if not run.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed placement')

    integration = json.loads((ROOT / spec['integrationReceipt']).read_text(encoding='utf-8'))
    if integration['status'] != spec['integrationReceiptStatusRequired']:
        raise RuntimeError('Integration receipt status ' + integration['status'])

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    external_copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / TARGET[6:]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / TARGET[6:])
            external_copied.append(str(external))

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    run.receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))
    run.receipt = {
        'status': 'checkpointed_placement_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'integrationTargetSha256Matched': map_sha_before == spec['integrationTargetSha256'],
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'groupsRequested': list(groups),
        'groupsNotRequested': [g for g in GROUP_ORDER if g not in groups],
        'preExistingReleaseActors': [],
        'placed': {},
        'omissions': {},
        'errors': [],
        'mapSaved': False,
        'limitations': [
            'Placement is geometric only: no visual, halachic, walking, collision-route or packaged acceptance is established.',
            'Static idle pilgrims are not goal-directed AI; the bus cannot be boarded; the station is not placed.',
            'Keruvim, vessels and Kotel courses are interpretive studies, not exact revealed or surveyed forms.',
        ],
    }
    run.write_receipt()

    saved = False
    try:
        run.take_snapshot()
        baseline = run.numeric_baseline(run.snapshot)
        pre_existing = [row for row in run.snapshot if row['label'].startswith(spec['labelPrefix']) or row['folder'].startswith(spec['folderPrefix'])]
        run.receipt['preExistingReleaseActors'] = [{'label': row['label'], 'name': row['name'], 'folder': row['folder'], 'meshes': row['meshes'],
                                                    'pose': row['pose'], 'worldBoundsCm': row['bounds']} for row in pre_existing]
        run.receipt['preExistingReleaseActorCount'] = len(pre_existing)
        clashes = []
        for group in groups:
            group_spec = spec[group]
            label_prefix = spec['labelPrefix'] + group_spec['group'] + '_'
            clashes += [row['label'] for row in pre_existing
                        if row['label'].startswith(label_prefix) or row['folder'] == group_spec['folder'] or row['folder'].startswith(group_spec['folder'] + '/')]
        if clashes:
            raise RuntimeError('Existing release actors of a requested group preserved; refusing duplicate placement: %s' % clashes[:10])
        unrelated = [row['label'] for row in pre_existing
                     if not any(row['label'].startswith(spec['labelPrefix'] + spec[g]['group'] + '_') or row['folder'].startswith(spec[g]['folder']) for g in GROUP_ORDER)]
        if unrelated:
            raise RuntimeError('RELEASE_ actors not belonging to any known group: %s' % unrelated[:10])
        trace_result = run.trace_self_test()
        run.write_receipt()

        results = {}
        runners = {'keruvim': lambda: run.place_keruvim(), 'pilgrims': lambda: run.place_pilgrims(trace_result),
                   'bus': lambda: run.place_bus(trace_result), 'kotel': lambda: run.place_kotel()}
        for group in groups:
            try:
                results[group] = runners[group]()
                run.receipt['placed'][group] = dict(results[group], actors=[_strip_actor_handles(r) for r in results[group]['actors']])
            except OmissionError as omission:
                run.receipt['omissions'][group] = {'reason': str(omission), 'evidence': omission.evidence}
            except Exception as error:
                run.receipt['omissions'][group] = {'reason': 'validation_or_api_failure: ' + str(error)}
                run.receipt['errors'].append({'group': group, 'error': repr(error)})
            run.write_receipt()

        placed_records = [record for result in results.values() for record in result['actors']]
        if not placed_records:
            run.receipt['status'] = 'nothing_placed_map_unchanged'
            return run.receipt

        current = run.numeric_baseline(run.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])

        if not run.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()
        if not run.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run.world = run.editor.get_editor_world()
        reopened = run.take_snapshot()
        reopened_numeric = run.numeric_baseline(reopened)
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])

        verify = spec['verification']
        readback = []
        for record in placed_records:
            matching = [row for row in reopened if row['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
            row = matching[0]
            actor = row['actor']
            entry = {'label': record['label'], 'folder': row['folder'], 'meshPath': row['meshes'], 'pose': row['pose'], 'worldBoundsCm': row['bounds']}
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            close, error = _pose_close(row['pose'], record['location'], record['rotation'], record['scale'], verify['transformToleranceCm'])
            entry['poseErrorCm'] = error
            if not close:
                raise RuntimeError('Reopened transform differs for %s by %.4f' % (record['label'], error))
            if record['kind'] == 'StaticMeshActor':
                entry['boundsErrorCm'] = box_error(row['bounds'], record['plannedWorldBoundsCm'])
                if entry['boundsErrorCm'] > verify['staticBoundsToleranceCm']:
                    raise RuntimeError('Reopened bounds differ for %s by %.4f' % (record['label'], entry['boundsErrorCm']))
                component = actor.get_component_by_class(ue.StaticMeshComponent)
                entry['collisionProfile'] = str(component.get_collision_profile_name())
            else:
                component = actor.get_component_by_class(ue.SkeletalMeshComponent)
                data = component.get_editor_property('animation_data')
                entry['animation'] = _asset_path(data.get_editor_property('anim_to_play'))
                entry['savedLooping'] = bool(data.get_editor_property('saved_looping'))
                entry['savedPlaying'] = bool(data.get_editor_property('saved_playing'))
                entry['savedPosition'] = float(data.get_editor_property('saved_position'))
                entry['collisionProfile'] = str(component.get_collision_profile_name())
                entry['feetErrorCm'] = row['bounds']['min'][2] - record['groundZ']
                if entry['animation'] != record['animation'] or not entry['savedLooping'] or not entry['savedPlaying']:
                    raise RuntimeError('Reopened animation data differs for ' + record['label'])
                if abs(entry['feetErrorCm']) > verify['skeletalFeetToleranceCm']:
                    raise RuntimeError('Reopened feet height differs for ' + record['label'])
            readback.append(entry)
        run.receipt['reopenedReadback'] = readback
        if 'kotel' in results:
            base_after = run.kotel_base_state()
            run.receipt['placed']['kotel']['baseWallStateAfterReopen'] = base_after
            if base_after != results['kotel']['baseWallState']:
                raise RuntimeError('Kotel base state differs after reopen')
        run.receipt['status'] = 'release_assets_saved_reopened_visual_runtime_acceptance_pending'
        return run.receipt
    except Exception as error:
        run.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        run.receipt['status'] = 'failed_after_save_checkpoint_available' if saved else 'failed_before_save_map_unchanged'
        raise
    finally:
        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapBytesChanged'] = run.receipt['mapSha256After'] != map_sha_before
        run.receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
        run.receipt['placedActorCount'] = sum(len(g['actors']) for g in run.receipt['placed'].values())
        run.receipt['totalReleaseActorCount'] = run.receipt['placedActorCount'] + len(run.receipt.get('preExistingReleaseActors') or [])
        run.write_receipt()


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    """True only when the engine itself is executing this file as a script."""
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_place_assets.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    bus_ground_z = None
    groups = GROUP_ORDER
    for token in command_line.split():
        if token.startswith('-releasebusgroundz='):
            bus_ground_z = float(token.split('=', 1)[1])
        elif token.startswith('-releasegroups='):
            groups = normalise_groups(token.split('=', 1)[1].strip('"'))
    try:
        receipt = place(load_target=True, bus_ground_z=bus_ground_z, groups=groups)
        ue.log('release_place_assets: %s groups %s placed %s pre-existing %s' % (
            receipt['status'], list(groups), receipt.get('placedActorCount'), receipt.get('preExistingReleaseActorCount')))
    except Exception as error:
        ue.log_error('release_place_assets failed: ' + repr(error))
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

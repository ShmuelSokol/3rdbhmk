"""Guarded exterior fixes for the combined IntegratedReviewV2 map (ExteriorReviewV1).

Implements the scriptable items of SourceAssets/arrival-review/ExteriorReviewV1/review.md.
Every number comes from Scripts/release_exterior_fixes.spec.json.

Fixes (default set: access, tiling, trees; sky is opt-in):
  access  Import the three frozen OpeningV2 meshes (elevated deck, guards, above-wall portal;
          SourceAssets/mount-access/OpeningV2/opening-v2.mesh.json, UE cm east/south/up, world placement
          baked) through the project's native OBJ adapter convention (centimetres, reflected Y, reversed
          winding, explicit normals/UVs; import_mount_platform.prepare_adapters) into the fresh namespace
          /Game/MikdashV3/ArrivalReview/MountAccessV2 and spawn them as RELEASE_MountAccess_* actors at
          identity plus a 2 cm lift, BlockAll, LOD0 complex-as-simple. Result: a continuous walkable
          route from the Kotel plaza level (Z -1432.5) up 82 risers to the Mount platform deck (Z 0).
          Recorded as AUTHORED INTERPRETATION: no retained wall, terrain, plaza or Kotel geometry is
          cut, hidden or moved; the OpeningV2 offline checks (zero wall-box intersections, zero
          protected-buffer overlap) are re-verified here against the design polygons before import.
  tiling  Lower the visible repetition of the context materials (terrain tile and macro noise, asphalt/path
          macro, city-wall block scale, building tint spread). UE 5.8 Python has NO default-parameter setter
          on MaterialEditingLibrary (the 2026-09-08 first run failed on it), so two methods are tried in order
          and the one used is recorded per material: (1) `expression_default` edits the parameter expressions'
          `default_value` (MaterialEditingLibrary.get_material_expressions, BlueprintPure in 5.8), recompiles and
          verifies with the exposed default getters, restoring the nodes on any mismatch; (2) `instance_override`
          creates MI_<Parent>_ExteriorV1 children with the new values (setters return False in 5.8: readback plus
          struct-array fallback) and overrides slot 0 on every StaticMeshComponent of this map carrying the parent.
          -ExteriorRevert restores defaults or clears the overrides according to the recorded method.
  trees   Count tree trunk/crown ISM instances whose XY lies inside the inferred Mount enclosure polygon
          and remove them (expected 0 after the L_FutureMount removal). Removed transforms and custom
          data are recorded so revert can re-add them.
  sky     (opt-in, -ExteriorFixes=...,sky) Lower Cloud_GlobalCoverage on MI_Cloud_Scattered so the
          cloud deck stops reading as a black wall along the horizon in every exterior view. Goes through the
          same readback-verified instance setter as the tiling fallback.

UE 5.8 API facts, checked against the installed engine source (not remembered):
  * Editor/MaterialEditor/Public/MaterialEditingLibrary.h has NO SetMaterialDefault*ParameterValue of any kind
    (that AttributeError killed the 2026-09-08 first run); the BlueprintPure getters
    GetMaterialDefault{Scalar,Vector}ParameterValue and BlueprintPure GetMaterialExpressions DO exist, which is
    exactly what method 1 below needs.
  * SetMaterialInstance{Scalar,Vector}ParameterValue writes through SetXParameterValueEditorOnly and returns a
    bResult that is never assigned: ALWAYS false. Every instance write here is judged by readback only.
  * UMaterial's nodes live in UMaterialEditorOnlyData::ExpressionCollection, a plain UPROPERTY(), so
    get_editor_property('expressions') / ('editor_only_data') is not a usable Python route in 5.8.
  * FMaterialParameterInfo defaults matter: a global parameter is (Name, GlobalParameter, Index -1); a
    Python-default struct is (Name, LayerParameter, 0) and would never be found.
  * StaticMesh.get_num_uv_channels does not exist in 5.8 and is not used here. This script never authors
    material graph nodes, so tonight's pin-name traps (texture sample UVs, Desaturation/Clamp first input
    'None', Noise 'World Position') do not apply to it.

Commandlet invocation (serial; editor closed; never while another native job runs):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_exterior_fixes.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-ExteriorFixes-01.log"

Switches (read from the engine command line):
  -ExteriorDryRun              load the map, read everything, plan every change, write a receipt;
                               no checkpoint, no asset or map write.
  -ExteriorRevert[=<receipt>]  undo the latest (or named) apply receipt: destroy the RELEASE_MountAccess_*
                               actors (imported assets are kept and listed), restore recorded material
                               defaults, re-add removed tree instances, restore the cloud coverage.
  -ExteriorFixes=a,b,c         subset of access,tiling,trees,sky (default access,tiling,trees).
  (no mode switch)             apply.

Offline (no engine): python Scripts/release_exterior_fixes.py  -> prints offline_check() and writes the
adapter OBJs into SourceAssets/arrival-review/ExteriorReviewV1/adapter/.

Safety model (release_place_assets.py pattern):
  * Refuses the wrong project dir, a game world, dirty packages, a loaded world that is not the combined
    map, an existing MountAccessV2 namespace or existing RELEASE_MountAccess_ actors (apply).
  * Checkpoints Walkthrough.umap (+ One-File-Per-Actor folders) and every .uasset it will touch to
    ReviewCheckpoints/ExteriorFixes-<stamp>/ before any mutation, verifying the copies by hash.
  * Snapshots every actor once (keyed by native name) and refuses to save if any unrelated actor changed;
    verifies again after reopen. Protected map hashes are checked before and after.
  * Receipt JSON in SourceAssets/arrival-review/ExteriorReviewV1/ is written at start, after every
    step and in finally, preserving partial state on failure.
"""
import hashlib
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_exterior_fixes.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
FIX_ORDER = ('access', 'tiling', 'trees', 'sky')


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so offline_check() runs anywhere.
# --------------------------------------------------------------------------

def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def stamp_now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def normalise_fixes(fixes):
    if isinstance(fixes, str):
        fixes = fixes.split(',')
    wanted = [f.strip().lower() for f in fixes if f.strip()]
    unknown = [f for f in wanted if f not in FIX_ORDER]
    if unknown:
        raise RuntimeError('Unknown fixes %s; valid: %s' % (unknown, list(FIX_ORDER)))
    if not wanted:
        raise RuntimeError('No fixes requested')
    return tuple(f for f in FIX_ORDER if f in wanted)


def read_json(relative, expected_sha=None, encoding='utf-8-sig'):
    path = ROOT / relative
    if expected_sha is not None and sha256_of(path) != expected_sha:
        raise RuntimeError('%s hash differs from spec (%s)' % (relative, sha256_of(path)))
    return json.loads(path.read_text(encoding=encoding))


def point_in_polygon(xy, polygon):
    """Ray casting; polygon is a list of [x, y] (closure point optional)."""
    x, y = xy
    inside = False
    n = len(polygon)
    for i in range(n):
        x0, y0 = polygon[i]
        x1, y1 = polygon[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            cross_x = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            if cross_x > x:
                inside = not inside
    return inside


def point_segment_distance(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-18:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def polygon_distance(xy, polygon):
    n = len(polygon)
    return min(point_segment_distance(xy, polygon[i], polygon[(i + 1) % n]) for i in range(n))


def footprint_samples(bounds, step):
    """Grid of XY samples covering an AABB (edges included)."""
    x0, y0 = bounds['min'][0], bounds['min'][1]
    x1, y1 = bounds['max'][0], bounds['max'][1]
    nx = max(1, int(math.ceil((x1 - x0) / step)))
    ny = max(1, int(math.ceil((y1 - y0) / step)))
    for i in range(nx + 1):
        x = x0 + (x1 - x0) * i / nx
        for j in range(ny + 1):
            yield (x, y0 + (y1 - y0) * j / ny)


def protected_violations(bounds, polygons, buffer_cm, step):
    """Samples of an AABB footprint inside a protected polygon or closer than the buffer to it."""
    violations = []
    for xy in footprint_samples(bounds, step):
        for name, polygon in polygons:
            if point_in_polygon(xy, polygon):
                violations.append({'xy': list(xy), 'polygon': name, 'kind': 'inside'})
            else:
                distance = polygon_distance(xy, polygon)
                if distance < buffer_cm - 0.5:
                    violations.append({'xy': list(xy), 'polygon': name, 'kind': 'buffer', 'distanceCm': distance})
    return violations


def mesh_bounds(vertices):
    return {'min': [min(v[i] for v in vertices) for i in range(3)], 'max': [max(v[i] for v in vertices) for i in range(3)]}


def signed_volume(vertices, triangles):
    total = 0.0
    for a, b, c in triangles:
        A, B, C = vertices[a], vertices[b], vertices[c]
        total += (A[0] * (B[1] * C[2] - B[2] * C[1]) - A[1] * (B[0] * C[2] - B[2] * C[0]) + A[2] * (B[0] * C[1] - B[1] * C[0])) / 6.0
    return total


def write_adapter_obj(mesh, out_folder):
    """Native import adapter OBJ: centimetres, reflected Y, reversed winding (import_mount_platform convention).

    The JSON is UE cm east/south/up with mathematical CCW (+Z) top faces; the FBX/OBJ importer negates Y and
    flips handedness, so reflecting Y and swapping (a, b, c) -> (a, c, b) lands the mesh at its baked world
    position with outward faces. Returns the record used for native verification.
    """
    vertices, triangles = mesh['verticesUEcm'], mesh['triangles']
    name = mesh['name']
    lines = ['# Native import adapter: centimeters, reflected Y, reversed winding; authored interpretation (OpeningV2)', 'o ' + name]
    index = 1
    adapted_vertices, adapted_triangles = [], []
    top_z = max(v[2] for v in vertices)
    top_pos = top_neg = 0
    for face in triangles:
        a, b, c = [vertices[i] for i in face]
        adapted = [(p[0], -p[1], p[2]) for p in (a, c, b)]
        first, second, third = adapted
        ab = [second[i] - first[i] for i in range(3)]
        ac = [third[i] - first[i] for i in range(3)]
        normal = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]]
        nlen = math.sqrt(sum(v * v for v in normal))
        edge = math.sqrt(sum(v * v for v in ab))
        if nlen <= 1e-8 or edge <= 1e-8:
            raise RuntimeError('Degenerate triangle in ' + name)
        if all(abs(p[2] - top_z) < 1e-6 for p in adapted):
            if normal[2] > 0:
                top_pos += 1
            else:
                top_neg += 1
        unit = [v / edge for v in ab]
        uv = [(0, 0), (edge / 100, 0), (sum(ac[i] * unit[i] for i in range(3)) / 100, nlen / edge / 100)]
        lines.extend('v %.9f %.9f %.9f' % p for p in adapted)
        lines.extend('vt %.9f %.9f' % p for p in uv)
        lines.extend(['vn %.12f %.12f %.12f' % tuple(v / nlen for v in normal)] * 3)
        lines.append('f ' + ' '.join('%d/%d/%d' % (i, i, i) for i in range(index, index + 3)))
        base = len(adapted_vertices)
        adapted_vertices.extend(adapted)
        adapted_triangles.append((base, base + 1, base + 2))
        index += 3
    if top_neg or not top_pos:
        raise RuntimeError('%s top faces are not all +Z after adaptation (+%d / -%d)' % (name, top_pos, top_neg))
    volume = signed_volume(adapted_vertices, adapted_triangles)
    if volume <= 0:
        raise RuntimeError('%s adapted signed volume is not positive (%.3f)' % (name, volume))
    out_folder.mkdir(parents=True, exist_ok=True)
    path = out_folder / (name + '.obj')
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    return {'name': name, 'path': str(path), 'sha256': sha256_of(path), 'triangles': len(triangles),
            'boundsUEcm': mesh_bounds(vertices), 'signedVolumeM3': volume / 1e6, 'topFacesUp': top_pos}


def offline_check(spec=None, fixes=FIX_ORDER):
    """Everything that can be verified without the engine. Raises on a hard inconsistency."""
    spec = spec or load_spec()
    fixes = normalise_fixes(fixes)
    report = {'fixes': list(fixes), 'targetMapSha256': sha256_of(ROOT / spec['targetMapFile'])}
    report['targetMapMatchesLastKnown'] = report['targetMapSha256'] == spec['lastKnownMapSha256']
    report['protectedMapsOnDisk'] = {m: disk_path(m, 'umap').exists() for m in spec['protectedMaps']}
    design = read_json(spec['access']['designJson'], spec['access']['designJsonSha256'])
    boundary = design['boundary']['nativeXYcm']
    report['enclosurePolygonPoints'] = len(boundary)
    if boundary[0] != boundary[-1] or len(boundary) < 4:
        raise RuntimeError('Enclosure polygon is not closed')

    if 'access' in fixes:
        cfg = spec['access']
        checks = read_json(cfg['sourceChecksJson'], cfg['sourceChecksJsonSha256'])
        if checks.get('status') != cfg['sourceChecksStatusRequired']:
            raise RuntimeError('OpeningV2 checks status %s' % checks.get('status'))
        if checks.get('originalWallTrianglesRemoved') != 0 or checks.get('protectedBufferOverlapCm2') != 0.0:
            raise RuntimeError('OpeningV2 checks no longer report zero wall removal / zero protected overlap')
        source = read_json(cfg['sourceMeshJson'], cfg['sourceMeshJsonSha256'])
        by_name = {m['name']: m for m in source['meshes']}
        records = []
        adapter_folder = ROOT / spec['adapterFolder']
        polygons = [(p['name'], p['nativeXYcm']) for p in design['protected']]
        for entry in cfg['meshes']:
            mesh = by_name.get(entry['name'])
            if mesh is None:
                raise RuntimeError('Mesh missing from OpeningV2 json: ' + entry['name'])
            if len(mesh['triangles']) != entry['triangles']:
                raise RuntimeError('%s triangle count %d differs from spec %d' % (entry['name'], len(mesh['triangles']), entry['triangles']))
            if mesh.get('actorLocationUEcm') != [0, 0, 0] or mesh.get('actorRotationDegrees') != [0, 0, 0] or mesh.get('actorScale') != [1, 1, 1]:
                raise RuntimeError('OpeningV2 mesh %s is not identity-placed' % entry['name'])
            record = write_adapter_obj(mesh, adapter_folder)
            record.update(label=entry['label'], materialKey=entry['materialKey'], material=cfg['materials'][entry['materialKey']],
                          plannedLocation=[0.0, 0.0, float(cfg['zLiftCm'])])
            record['plannedWorldBoundsCm'] = {k: [record['boundsUEcm'][k][0], record['boundsUEcm'][k][1], record['boundsUEcm'][k][2] + cfg['zLiftCm']] for k in ('min', 'max')}
            violations = protected_violations(record['boundsUEcm'], polygons, cfg['protectedBufferCm'], cfg['footprintSampleStepCm'])
            record['protectedViolationSamples'] = len(violations)
            record['protectedViolationExamples'] = violations[:5]
            if violations:
                raise RuntimeError('%s footprint violates a protected polygon/buffer at %d samples' % (entry['name'], len(violations)))
            records.append(record)
        platform = read_json(cfg['platformMeshJson'], cfg['platformMeshJsonSha256'])
        deck = by_name[cfg['meshes'][0]['name']]
        deck_bounds = mesh_bounds(deck['verticesUEcm'])
        corridor_y = 0.5 * (deck_bounds['min'][1] + deck_bounds['max'][1])
        crossings = []
        ring = platform['allowedBoundaryRingsXYcm'][0]
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            if (a[1] - corridor_y) * (b[1] - corridor_y) <= 0 and a[1] != b[1]:
                t = (corridor_y - a[1]) / (b[1] - a[1])
                crossings.append(a[0] + t * (b[0] - a[0]))
        west_edge = max(x for x in crossings if x < 0) if any(x < 0 for x in crossings) else None
        report['access'] = {
            'meshes': records, 'namespace': cfg['namespace'], 'namespaceFolderOnDisk': disk_path(cfg['namespace'] + '/x').parent.exists(),
            'materialsOnDisk': {k: disk_path(v).exists() for k, v in cfg['materials'].items()},
            'corridorYcm': corridor_y, 'platformWestEdgeXAtCorridorCm': west_edge, 'deckEastEndXcm': deck_bounds['max'][0],
            'coplanarOverlapWithPlatformDeckCm': (deck_bounds['max'][0] - west_edge) if west_edge is not None else None,
            'zLiftCm': cfg['zLiftCm'], 'openingV2Checks': {k: checks[k] for k in ('allRetainedWallBoxesTested', 'protectedBufferOverlapCm2', 'minimumCrossingDeckToWallGapCm', 'portalClearWidthCm', 'portalMinimumHeadroomCm', 'originalWallTrianglesRemoved') if k in checks},
            'interpretation': cfg['scenario'],
        }
        missing = [k for k, ok in report['access']['materialsOnDisk'].items() if not ok]
        if missing:
            raise RuntimeError('Access materials missing on disk: %s' % missing)

    if 'tiling' in fixes:
        rows = {}
        for path, cfg in spec['tiling']['materials'].items():
            rows[path] = {'onDisk': disk_path(path).exists(), 'scalar': cfg.get('scalar', {}), 'vector': cfg.get('vector', {})}
            if not rows[path]['onDisk']:
                raise RuntimeError('Context material missing on disk: ' + path)
        report['tiling'] = rows

    if 'trees' in fixes:
        report['trees'] = {'components': spec['trees']['components'], 'meshesOnDisk': {c['mesh']: disk_path(c['mesh']).exists() for c in spec['trees']['components']},
                           'expectedInsideCount': spec['trees']['expectedInsideCount']}
        if not all(report['trees']['meshesOnDisk'].values()):
            raise RuntimeError('Tree instance meshes missing on disk')

    if 'sky' in fixes:
        report['sky'] = {'materialInstance': spec['sky']['materialInstance'], 'onDisk': disk_path(spec['sky']['materialInstance']).exists(), 'scalar': spec['sky']['scalar']}
        if not report['sky']['onDisk']:
            raise RuntimeError('MI_Cloud_Scattered missing on disk')

    receipts = sorted((ROOT / spec['receiptFolder']).glob(spec['receiptPrefix'] + '*.json'))
    report['existingReceipts'] = [p.name for p in receipts[-5:]]
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Native helpers
# --------------------------------------------------------------------------

def _vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def _rot(r):
    return [float(r.pitch), float(r.yaw), float(r.roll)]


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj is not None else None


def _round(values, digits=4):
    return tuple(round(float(v), digits) for v in values)


def _box(box):
    return {'min': _vec(box.min), 'max': _vec(box.max)}


def _box_error(a, b):
    return max(abs(a[k][i] - b[k][i]) for k in ('min', 'max') for i in range(3))


def _linear(color):
    return [float(color.r), float(color.g), float(color.b), float(color.a)]


def _instance_transform(component, index):
    """ISM instance world transform; branch on the reflection shape (tuple or Transform or None)."""
    result = component.get_instance_transform(index, True)
    if isinstance(result, tuple):
        if len(result) >= 2 and result[0]:
            return result[1]
        if len(result) >= 2 and not isinstance(result[0], bool):
            return result[1]
        return None
    return result


def _mark_modified(component):
    """UObject::Modify on the component and its owning actor: set_material / remove_instance do not always mark
    the package dirty by themselves, and an undirtied map is never offered to save_current_level."""
    for obj in (component, component.get_owner() if hasattr(component, 'get_owner') else None):
        if obj is not None:
            obj.modify(True)


def _transform_dict(transform):
    rotation = transform.rotation
    rotator = rotation.rotator() if hasattr(rotation, 'rotator') else rotation
    return {'location': _vec(transform.translation), 'rotation': _rot(rotator), 'scale': _vec(transform.scale3d)}


class Engine:
    def __init__(self, ue, spec, receipt, receipt_path):
        self.ue = ue
        self.spec = spec
        self.receipt = receipt
        self.receipt_path = receipt_path
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.ml = ue.MaterialEditingLibrary
        self.snapshot = None

    def write(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    # -- guards ---------------------------------------------------------------

    def common_guards(self):
        ue = self.ue
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
        if self.editor.get_game_world():
            raise RuntimeError('A game world is active; never mutate during play')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present before the run')

    def load_target(self):
        if not self.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        world = self.editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map' % world.get_outermost().get_name())
        return world

    def namespace_exists(self, namespace):
        on_disk = disk_path(namespace + '/x').parent
        return bool(self.assets.does_directory_exist(namespace)) or (on_disk.exists() and any(on_disk.rglob('*.uasset')))

    # -- snapshot -------------------------------------------------------------

    def take_snapshot(self):
        """One pass over every actor, keyed by native name (labels may legitimately repeat)."""
        ue = self.ue
        rows = {}
        for actor in self.actors.get_all_level_actors():
            meshes = []
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                meshes.append(_asset_path(component.get_editor_property('static_mesh')))
            for component in actor.get_components_by_class(ue.SkeletalMeshComponent):
                meshes.append(_asset_path(component.get_skeletal_mesh_asset()))
            rows[actor.get_name()] = {'actor': actor, 'label': actor.get_actor_label(), 'folder': str(actor.get_folder_path()), 'meshes': tuple(meshes),
                                      'pose': _round(_vec(actor.get_actor_location()) + _rot(actor.get_actor_rotation()) + _vec(actor.get_actor_scale3d()))}
        self.snapshot = rows
        return rows

    @staticmethod
    def numeric(rows):
        return {name: (row['label'], row['meshes'], row['pose']) for name, row in rows.items()}

    # -- checkpoint -----------------------------------------------------------

    def checkpoint(self, stamp, asset_paths):
        spec = self.spec
        map_file = ROOT / spec['targetMapFile']
        folder = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        folder.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, folder / map_file.name)
        if sha256_of(folder / map_file.name) != sha256_of(map_file):
            raise RuntimeError('Checkpoint map copy hash differs')
        for name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / name / TARGET[6:]
            if external.exists():
                shutil.copytree(external, folder / name / TARGET[6:])
        copied = []
        for asset_path in asset_paths:
            source = disk_path(asset_path)
            if not source.exists():
                continue
            destination = folder / 'Content' / (asset_path[6:] + '.uasset')
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if sha256_of(source) != sha256_of(destination):
                raise RuntimeError('Checkpoint asset copy differs: ' + asset_path)
            copied.append(asset_path)
        return folder, copied

    # -- fix: tiling ------------------------------------------------------------
    #
    # UE 5.8 Python exposes NO default-parameter setter on MaterialEditingLibrary (only the getters
    # get_material_default_{scalar,vector}_parameter_value). Two methods, chosen at run time:
    #   expression_default  find every MaterialExpression{Scalar,Vector}Parameter node carrying the name
    #                       (MaterialEditingLibrary.get_material_expressions, UFUNCTION(BlueprintPure) in the
    #                       installed 5.8 header; the editor-only ExpressionCollection is NOT a reflected editor
    #                       property, so there is no second route), set their `default_value`, recompile, verify by
    #                       the default getters; any failure restores the nodes and falls through to
    #   instance_override   a MaterialInstanceConstant child per parent with the new values (setters return False in
    #                       5.8, so readback decides, with the *_parameter_values struct fallback), applied as slot-0
    #                       component overrides on every StaticMeshComponent of THIS map that carries the parent.
    #                       Parents and mesh assets stay untouched; revert clears the overrides.

    def read_material_values(self, material, cfg):
        values = {'scalar': {}, 'vector': {}}
        for name in cfg.get('scalar', {}):
            values['scalar'][name] = float(self.ml.get_material_default_scalar_parameter_value(material, name))
        for name in cfg.get('vector', {}):
            values['vector'][name] = _linear(self.ml.get_material_default_vector_parameter_value(material, name))
        return values

    def material_expressions(self, material):
        """(expressions, access route). Raises (-> instance_override fallback) if the route is not exposed.

        UE 5.8 fact: UMaterialEditingLibrary::GetMaterialExpressions is UFUNCTION(BlueprintPure) and is the only
        Python route. UMaterial keeps its nodes in UMaterialEditorOnlyData::ExpressionCollection, declared plain
        UPROPERTY() (no EditAnywhere/BlueprintReadWrite), so get_editor_property('editor_only_data') /
        ('expressions') is NOT reachable from Python; it is attempted only as a last resort and its failure is
        reported as such rather than as a stray AttributeError.
        """
        if hasattr(self.ml, 'get_material_expressions'):
            return list(self.ml.get_material_expressions(material)), 'MaterialEditingLibrary.get_material_expressions'
        try:
            editor_only = material.get_editor_property('editor_only_data')
            collection = editor_only.get_editor_property('expression_collection')
            return list(collection.get_editor_property('expressions')), 'editor_only_data.expression_collection.expressions'
        except Exception as error:  # noqa: BLE001 - reported so fix_tiling can take the instance_override route
            raise RuntimeError('No Python route to the material expressions (get_material_expressions absent; '
                               'editor-only ExpressionCollection is not a reflected editor property): %r' % (error,))

    def parameter_expressions(self, material, scalar_names, vector_names):
        """{'scalar': {name: [expression, ...]}, 'vector': {...}}, route, expression count.

        Every node carrying a wanted parameter name is collected: a name may legitimately appear on more than one
        node, and all of them have to move together or the default getters read back the stale one.
        """
        ue = self.ue
        expressions, route = self.material_expressions(material)
        found = {'scalar': {}, 'vector': {}}
        for expression in expressions:
            if isinstance(expression, ue.MaterialExpressionVectorParameter):
                kind, wanted = 'vector', vector_names
            elif isinstance(expression, ue.MaterialExpressionScalarParameter):
                kind, wanted = 'scalar', scalar_names
            else:
                continue
            name = str(expression.get_editor_property('parameter_name'))
            if name in wanted:
                found[kind].setdefault(name, []).append(expression)
        missing = [n for n in scalar_names if n not in found['scalar']] + [n for n in vector_names if n not in found['vector']]
        if missing:
            raise RuntimeError('Parameter expressions not found: %s' % missing)
        return found, route, len(expressions)

    def _apply_expression_defaults(self, material, cfg, row, pending_scalar, pending_vector, tol_r):
        """Method 1. Returns the access route on success; raises after restoring the nodes on any failure."""
        ue = self.ue
        found, route, count = self.parameter_expressions(material, list(pending_scalar), list(pending_vector))
        row['expressionCount'] = count
        row['parameterNodeCount'] = {n: len(found['scalar'][n]) for n in pending_scalar}
        row['parameterNodeCount'].update({n: len(found['vector'][n]) for n in pending_vector})
        touched = []
        material.modify(True)
        try:
            for name, entry in pending_scalar.items():
                touched.append(('scalar', name))  # recorded before the write: a mid-list failure still restores
                for expression in found['scalar'][name]:
                    expression.set_editor_property('default_value', float(entry['after']))
            for name, entry in pending_vector.items():
                touched.append(('vector', name))
                for expression in found['vector'][name]:
                    expression.set_editor_property('default_value', ue.LinearColor(*entry['after']))
            # RecompileMaterial does PreEditChange/PostEditChange (which rebuilds the cached expression data the
            # default getters read) and returns the material resource's compile errors; recorded, never trusted
            # as the acceptance test - the readback below is.
            row['recompileErrors'] = [str(e) for e in (self.ml.recompile_material(material) or [])][:20]
            readback = self.read_material_values(material, cfg)
            for name, entry in pending_scalar.items():
                if abs(readback['scalar'][name] - entry['after']) > tol_r:
                    raise RuntimeError('%s readback %.5f differs from %.5f' % (name, readback['scalar'][name], entry['after']))
            for name, entry in pending_vector.items():
                if max(abs(readback['vector'][name][i] - entry['after'][i]) for i in range(3)) > tol_r:
                    raise RuntimeError('%s readback %s differs from %s' % (name, readback['vector'][name], entry['after']))
            return route
        except Exception:
            for kind, name in touched:
                entry = row[kind][name]
                value = float(entry['before']) if kind == 'scalar' else ue.LinearColor(*entry['before'])
                for expression in found[kind][name]:
                    expression.set_editor_property('default_value', value)
            if touched:
                self.ml.recompile_material(material)
            raise

    def set_instance_parameter(self, instance, kind, name, value):
        """MIC setter verified by readback; struct-array fallback (release_sanctuary_balance.py idiom).

        UE 5.8 fact: UMaterialEditingLibrary::SetMaterialInstance{Scalar,Vector}ParameterValue writes the value
        through SetXParameterValueEditorOnly and then returns a bResult that was never assigned - it is ALWAYS
        false, success or not. Only the readback decides here. The fallback writes the parameter struct directly
        and must stamp Association=GlobalParameter, Index=-1 (INDEX_NONE); a Python-default struct would carry
        Association=LayerParameter, Index=0 and the global lookup would never find it.
        """
        ue, ml = self.ue, self.ml
        getters = {'scalar': ml.get_material_instance_scalar_parameter_value, 'vector': ml.get_material_instance_vector_parameter_value}
        setters = {'scalar': ml.set_material_instance_scalar_parameter_value, 'vector': ml.set_material_instance_vector_parameter_value}

        def read():
            got = getters[kind](instance, name)
            return float(got) if kind == 'scalar' else _linear(got)

        def matches(got):
            if kind == 'scalar':
                return abs(got - float(value)) <= 1e-4
            return max(abs(a - b) for a, b in zip(got[:3], _linear(value)[:3])) <= 1e-4

        instance.modify(True)
        returned = setters[kind](instance, name, value)
        ml.update_material_instance(instance)
        got = read()
        path = 'MaterialEditingLibrary.set_material_instance_%s_parameter_value (return %s always false, ignored)' % (kind, returned)
        if not matches(got):
            prop = {'scalar': 'scalar_parameter_values', 'vector': 'vector_parameter_values'}[kind]
            struct_cls = {'scalar': ue.ScalarParameterValue, 'vector': ue.VectorParameterValue}[kind]
            values = [v for v in instance.get_editor_property(prop) if str(v.get_editor_property('parameter_info').get_editor_property('name')) != name]
            entry = struct_cls()
            info = ue.MaterialParameterInfo()
            info.set_editor_property('name', name)
            info.set_editor_property('association', ue.MaterialParameterAssociation.GLOBAL_PARAMETER)
            info.set_editor_property('index', -1)
            entry.set_editor_property('parameter_info', info)
            entry.set_editor_property('parameter_value', value)
            values.append(entry)
            instance.set_editor_property(prop, values)
            ml.update_material_instance(instance)
            got = read()
            path = 'set_editor_property(%s) struct fallback' % prop
        if not matches(got):
            raise RuntimeError('Parameter %s on %s read back %r after %s' % (name, instance.get_name(), got, path))
        return {'after': got, 'path': path}

    def ensure_instance(self, parent, parent_path, pending_scalar, pending_vector):
        """Method 2 asset: MI_<Parent>_ExteriorV1 under the spec instance folder; reused if present with the right parent."""
        ue, ml = self.ue, self.ml
        cfg = self.spec['tiling']
        folder = cfg['instanceFolder']
        name = cfg['instancePrefix'] + parent_path.rsplit('/', 1)[1] + cfg['instanceSuffix']
        path = folder + '/' + name
        record = {'asset': path}
        if self.assets.does_asset_exist(path):
            instance = ue.load_asset(path)
            if not isinstance(instance, ue.MaterialInstanceConstant):
                raise RuntimeError('Existing asset at %s is not a MaterialInstanceConstant' % path)
            record['created'] = False
        else:
            instance = ue.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew())
            if not isinstance(instance, ue.MaterialInstanceConstant):
                raise RuntimeError('MaterialInstanceConstant factory failed for ' + path)
            record['created'] = True
        if _asset_path(instance.get_editor_property('parent')) != parent_path:
            ml.set_material_instance_parent(instance, parent)
            if _asset_path(instance.get_editor_property('parent')) != parent_path:
                instance.set_editor_property('parent', parent)
                ml.update_material_instance(instance)
        if _asset_path(instance.get_editor_property('parent')) != parent_path:
            raise RuntimeError('Instance %s parent is not %s' % (path, parent_path))
        record['parameters'] = {}
        for pname, entry in pending_scalar.items():
            record['parameters'][pname] = self.set_instance_parameter(instance, 'scalar', pname, float(entry['after']))
        for pname, entry in pending_vector.items():
            record['parameters'][pname] = self.set_instance_parameter(instance, 'vector', pname, ue.LinearColor(*entry['after']))
        ml.update_material_instance(instance)
        if not self.assets.save_loaded_asset(instance, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        record['uassetSha256'] = sha256_of(disk_path(path))
        return instance, record

    def components_by_material(self, material_paths):
        """One pass over every actor: {material path: [(actor name, component)]} for slot-0 StaticMeshComponents (ISM excluded)."""
        ue = self.ue
        index = {p: [] for p in material_paths}
        for name, row in self.snapshot.items():
            for component in row['actor'].get_components_by_class(ue.StaticMeshComponent):
                if isinstance(component, ue.InstancedStaticMeshComponent):
                    continue
                if component.get_editor_property('static_mesh') is None:
                    continue
                current = _asset_path(component.get_material(0))
                if current in index:
                    index[current].append((name, component))
        return index

    def override_components(self, rows, instance, parent_path):
        """Method 2 map edit: slot-0 override on each listed component; records the previous override for revert."""
        out = []
        new_path = _asset_path(instance)
        for actor_name, component in rows:
            overrides = list(component.get_editor_property('override_materials'))
            previous = _asset_path(overrides[0]) if overrides and overrides[0] is not None else None
            _mark_modified(component)
            component.set_material(0, instance)
            if _asset_path(component.get_material(0)) != new_path:
                raise RuntimeError('Component override readback differs on %s/%s' % (actor_name, component.get_name()))
            out.append({'actor': actor_name, 'component': component.get_name(), 'previousOverride': previous, 'parent': parent_path})
        return out

    def fix_tiling(self, dry_run):
        ue = self.ue
        cfg_all = self.spec['tiling']
        tol_s, tol_v, tol_r = cfg_all['expectedBeforeToleranceScalar'], cfg_all['expectedBeforeToleranceVector'], cfg_all['readbackTolerance']
        out = {'materials': {}, 'reason': cfg_all['reason'], 'methodPolicy': 'expression_default first, instance_override fallback',
               'getMaterialExpressionsExposed': bool(hasattr(self.ml, 'get_material_expressions'))}
        self.receipt['fixes']['tiling'] = out
        component_index = None
        for path, cfg in cfg_all['materials'].items():
            material = ue.load_asset(path)
            if not isinstance(material, ue.Material):
                raise RuntimeError('Not a Material: ' + path)
            current = self.read_material_values(material, cfg)
            row = {'uassetSha256Before': sha256_of(disk_path(path)), 'scalar': {}, 'vector': {}, 'action': 'planned', 'method': None}
            out['materials'][path] = row
            pending_scalar, pending_vector = {}, {}
            for name, (expected_before, after) in cfg.get('scalar', {}).items():
                value = current['scalar'][name]
                state = 'already_applied' if abs(value - after) <= tol_r else ('matches_expected_before' if abs(value - expected_before) <= tol_s else 'unexpected_current_value')
                row['scalar'][name] = {'before': value, 'expectedBefore': expected_before, 'after': after, 'state': state}
                if state == 'unexpected_current_value':
                    raise RuntimeError('%s %s is %.5f, expected %.5f; refusing to overwrite an unreviewed value' % (path, name, value, expected_before))
                if state == 'matches_expected_before':
                    pending_scalar[name] = row['scalar'][name]
            for name, (expected_before, after) in cfg.get('vector', {}).items():
                value = current['vector'][name]
                # RGB decides; the alpha channel is carried over unchanged from the material.
                after = list(after[:3]) + [value[3]]
                close_after = max(abs(value[i] - after[i]) for i in range(3)) <= tol_r
                close_before = max(abs(value[i] - expected_before[i]) for i in range(3)) <= tol_v
                state = 'already_applied' if close_after else ('matches_expected_before' if close_before else 'unexpected_current_value')
                row['vector'][name] = {'before': value, 'expectedBefore': expected_before, 'after': after, 'state': state}
                if state == 'unexpected_current_value':
                    raise RuntimeError('%s %s is %s, expected %s; refusing to overwrite an unreviewed value' % (path, name, value, expected_before))
                if state == 'matches_expected_before':
                    pending_vector[name] = row['vector'][name]
            pending = bool(pending_scalar or pending_vector)
            if dry_run:
                try:
                    found, route, count = self.parameter_expressions(material, list(cfg.get('scalar', {})), list(cfg.get('vector', {})))
                    row['expressionRoute'] = route
                    row['expressionCount'] = count
                    row['plannedMethod'] = 'expression_default'
                except Exception as error:  # noqa: BLE001 - diagnostic only in a dry run
                    row['expressionRouteError'] = repr(error)
                    row['plannedMethod'] = 'instance_override'
                    if component_index is None:
                        component_index = self.components_by_material(list(cfg_all['materials']))
                    row['componentsCarryingParent'] = len(component_index[path])
                row['action'] = 'planned' if pending else 'already_applied'
                continue
            if not pending:
                row['action'] = 'already_applied'
                continue
            row['action'] = 'set_started'
            self.write()
            try:
                route = self._apply_expression_defaults(material, cfg, row, pending_scalar, pending_vector, tol_r)
                if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
                    raise RuntimeError('save_loaded_asset failed for ' + path)
                row.update(method='expression_default', expressionRoute=route, action='set_saved', uassetSha256After=sha256_of(disk_path(path)))
                self.write()
                continue
            except Exception as error:  # noqa: BLE001 - recorded, then the reflected fallback runs
                row['expressionMethodError'] = repr(error)
                self.write()
            if component_index is None:
                component_index = self.components_by_material(list(cfg_all['materials']))
            instance, record = self.ensure_instance(material, path, pending_scalar, pending_vector)
            row['instance'] = record
            row['action'] = 'override_started'
            self.write()
            row['components'] = self.override_components(component_index[path], instance, path)
            row['componentCount'] = len(row['components'])
            if row['components'] and not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
                raise RuntimeError('%s slot-0 overrides were set but no map package is dirty; the save would drop them' % path)
            row.update(method='instance_override', action='overrides_set_pending_map_save', uassetSha256After=sha256_of(disk_path(path)))
            self.write()
        return out

    def tiling_reopen_readback(self, out):
        """After reopen: default values on the parents plus, for instance_override rows, how many components carry the MIC."""
        ue = self.ue
        readback = {}
        counts = None
        for path, cfg in self.spec['tiling']['materials'].items():
            material = ue.load_asset(path)
            entry = {'defaults': self.read_material_values(material, cfg)}
            row = out['materials'].get(path, {})
            if row.get('method') == 'instance_override' and row.get('instance'):
                if counts is None:
                    counts = self.components_by_material([r['instance']['asset'] for r in out['materials'].values() if r.get('instance')])
                entry['componentsCarryingInstance'] = len(counts[row['instance']['asset']])
                if entry['componentsCarryingInstance'] != row.get('componentCount'):
                    raise RuntimeError('%s: %d components carry the instance after reopen, %d were set' % (path, entry['componentsCarryingInstance'], row.get('componentCount')))
            readback[path] = entry
        out['reopenedReadback'] = readback

    def revert_tiling(self, prior):
        ue = self.ue
        out = {'materials': {}}
        self.receipt['fixes']['tiling'] = out
        tol = self.spec['tiling']['readbackTolerance']
        for path, row in prior.get('materials', {}).items():
            method = row.get('method')
            if row.get('action') not in ('set_started', 'set_saved', 'override_started', 'overrides_set_pending_map_save') or method is None:
                out['materials'][path] = {'action': 'nothing_to_revert', 'priorAction': row.get('action'), 'priorMethod': method}
                continue
            material = ue.load_asset(path)
            if not isinstance(material, ue.Material):
                raise RuntimeError('Not a Material: ' + path)
            entry = {'action': 'revert_started', 'method': method, 'scalar': {}, 'vector': {}}
            out['materials'][path] = entry
            self.write()
            if method == 'expression_default':
                cfg = {'scalar': {n: None for n in row.get('scalar', {})}, 'vector': {n: None for n in row.get('vector', {})}}
                pending_scalar = {n: v for n, v in row.get('scalar', {}).items() if v['state'] == 'matches_expected_before'}
                pending_vector = {n: v for n, v in row.get('vector', {}).items() if v['state'] == 'matches_expected_before'}
                found, route, _ = self.parameter_expressions(material, list(pending_scalar), list(pending_vector))
                entry['expressionRoute'] = route
                material.modify(True)
                for name, values in pending_scalar.items():
                    for expression in found['scalar'][name]:
                        expression.set_editor_property('default_value', float(values['before']))
                    entry['scalar'][name] = values['before']
                for name, values in pending_vector.items():
                    for expression in found['vector'][name]:
                        expression.set_editor_property('default_value', ue.LinearColor(*values['before']))
                    entry['vector'][name] = values['before']
                entry['recompileErrors'] = [str(e) for e in (self.ml.recompile_material(material) or [])][:20]
                readback = self.read_material_values(material, cfg)
                for name, value in entry['scalar'].items():
                    if abs(readback['scalar'][name] - value) > tol:
                        raise RuntimeError('Revert readback differs for %s %s' % (path, name))
                for name, value in entry['vector'].items():
                    if max(abs(a - b) for a, b in zip(readback['vector'][name][:3], value[:3])) > tol:
                        raise RuntimeError('Revert readback differs for %s %s' % (path, name))
                if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
                    raise RuntimeError('save_loaded_asset failed for ' + path)
                entry.update(action='reverted_saved', uassetSha256After=sha256_of(disk_path(path)))
            elif method == 'instance_override':
                instance_path = row['instance']['asset']
                entry['instanceRetained'] = instance_path
                cleared = 0
                missing = []
                for record in row.get('components', []):
                    snap = self.snapshot.get(record['actor'])
                    if snap is None:
                        missing.append(record['actor'])
                        continue
                    components = [c for c in snap['actor'].get_components_by_class(ue.StaticMeshComponent) if c.get_name() == record['component']]
                    if len(components) != 1:
                        missing.append(record['actor'] + '/' + record['component'])
                        continue
                    component = components[0]
                    if _asset_path(component.get_material(0)) != instance_path:
                        continue  # already cleared or changed by someone else; never touch
                    previous = ue.load_asset(record['previousOverride']) if record.get('previousOverride') else None
                    _mark_modified(component)
                    component.set_material(0, previous)
                    if _asset_path(component.get_material(0)) not in (record.get('previousOverride'), path):
                        raise RuntimeError('Override clear readback differs on %s/%s' % (record['actor'], record['component']))
                    cleared += 1
                entry.update(clearedComponents=cleared, missingComponents=missing[:20], missingCount=len(missing), action='overrides_cleared_pending_map_save')
            else:
                raise RuntimeError('Unknown tiling method in receipt: %r' % method)
            self.write()
        return out

    # -- fix: sky (opt-in) --------------------------------------------------------

    def fix_sky(self, dry_run):
        ue = self.ue
        cfg = self.spec['sky']
        path = cfg['materialInstance']
        instance = ue.load_asset(path)
        if not isinstance(instance, ue.MaterialInstanceConstant):
            raise RuntimeError('Not a MaterialInstanceConstant: ' + path)
        out = {'materialInstance': path, 'reason': cfg['reason'], 'scalar': {}, 'action': 'planned', 'uassetSha256Before': sha256_of(disk_path(path))}
        self.receipt['fixes']['sky'] = out
        pending = False
        for name, (expected_before, after) in cfg['scalar'].items():
            value = float(self.ml.get_material_instance_scalar_parameter_value(instance, name))
            state = 'already_applied' if abs(value - after) <= 1e-4 else ('matches_expected_before' if abs(value - expected_before) <= cfg['expectedBeforeTolerance'] else 'unexpected_current_value')
            out['scalar'][name] = {'before': value, 'expectedBefore': expected_before, 'after': after, 'state': state}
            if state == 'unexpected_current_value':
                raise RuntimeError('%s %s is %.4f, expected %.4f; refusing' % (path, name, value, expected_before))
            pending = pending or state == 'matches_expected_before'
        if dry_run or not pending:
            out['action'] = 'planned' if pending else 'already_applied'
            return out
        out['action'] = 'set_started'
        self.write()
        # Same 5.8 issue as the tiling instance route: the setter always returns false, so readback decides
        # (set_instance_parameter raises unless the value reads back, struct fallback included).
        for name, entry in out['scalar'].items():
            if entry['state'] == 'matches_expected_before':
                entry['set'] = self.set_instance_parameter(instance, 'scalar', name, float(entry['after']))
        self.ml.update_material_instance(instance)
        for name, entry in out['scalar'].items():
            readback = float(self.ml.get_material_instance_scalar_parameter_value(instance, name))
            entry['readback'] = readback
            if abs(readback - entry['after']) > 1e-4:
                raise RuntimeError('%s %s readback %.4f differs from %.4f' % (path, name, readback, entry['after']))
        if not self.assets.save_loaded_asset(instance, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        out['action'] = 'set_saved'
        out['uassetSha256After'] = sha256_of(disk_path(path))
        self.write()
        return out

    def revert_sky(self, prior):
        ue = self.ue
        out = {'materialInstance': prior.get('materialInstance'), 'action': 'nothing_to_revert'}
        self.receipt['fixes']['sky'] = out
        if prior.get('action') not in ('set_started', 'set_saved'):
            return out
        instance = ue.load_asset(prior['materialInstance'])
        if not isinstance(instance, ue.MaterialInstanceConstant):
            raise RuntimeError('Not a MaterialInstanceConstant: ' + prior['materialInstance'])
        out['action'] = 'revert_started'
        out['scalar'] = {}
        self.write()
        for name, entry in prior['scalar'].items():
            if entry['state'] == 'matches_expected_before':
                self.set_instance_parameter(instance, 'scalar', name, float(entry['before']))
                out['scalar'][name] = entry['before']
        self.ml.update_material_instance(instance)
        for name, value in out['scalar'].items():
            readback = float(self.ml.get_material_instance_scalar_parameter_value(instance, name))
            if abs(readback - float(value)) > 1e-4:
                raise RuntimeError('%s %s revert readback %.4f differs from %.4f' % (prior['materialInstance'], name, readback, value))
        if not self.assets.save_loaded_asset(instance, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + prior['materialInstance'])
        out['action'] = 'reverted_saved'
        self.write()
        return out

    # -- fix: trees -----------------------------------------------------------------

    def tree_components(self):
        ue = self.ue
        found = []
        for entry in self.spec['trees']['components']:
            rows = [row for row in self.snapshot.values() if row['label'] == entry['label']]
            if len(rows) != 1:
                raise RuntimeError('Expected exactly one actor labelled %s, found %d' % (entry['label'], len(rows)))
            components = list(rows[0]['actor'].get_components_by_class(ue.InstancedStaticMeshComponent))
            if len(components) != 1:
                raise RuntimeError('%s has %d ISM components' % (entry['label'], len(components)))
            component = components[0]
            mesh_path = _asset_path(component.get_editor_property('static_mesh'))
            if mesh_path != entry['mesh']:
                raise RuntimeError('%s carries %s, expected %s' % (entry['label'], mesh_path, entry['mesh']))
            found.append((entry, rows[0]['actor'], component))
        return found

    def fix_trees(self, dry_run):
        cfg = self.spec['trees']
        design = read_json(self.spec['access']['designJson'], self.spec['access']['designJsonSha256'])
        polygon = design['boundary']['nativeXYcm']
        out = {'reason': cfg['reason'], 'polygonPoints': len(polygon), 'components': [], 'removedTotal': 0}
        self.receipt['fixes']['trees'] = out
        for entry, actor, component in self.tree_components():
            count = int(component.get_instance_count())
            row = {'label': entry['label'], 'mesh': entry['mesh'], 'instancesBefore': count, 'expectedInstances': entry['expectedInstances'], 'inside': [], 'action': 'scanned'}
            out['components'].append(row)
            unreadable = 0
            for index in range(count):
                transform = _instance_transform(component, index)
                if transform is None:
                    unreadable += 1
                    continue
                location = _vec(transform.translation)
                if point_in_polygon((location[0], location[1]), polygon):
                    record = {'index': index, 'transform': _transform_dict(transform)}
                    row['inside'].append(record)
            row['unreadableTransforms'] = unreadable
            row['insideCount'] = len(row['inside'])
            if unreadable:
                raise RuntimeError('%d instance transforms unreadable on %s' % (unreadable, entry['label']))
            if len(row['inside']) > cfg['maxRemovals']:
                raise RuntimeError('%d instances inside the enclosure on %s exceeds maxRemovals %d; inspect before removing' % (len(row['inside']), entry['label'], cfg['maxRemovals']))
            if dry_run or not row['inside']:
                row['action'] = 'planned_removal' if row['inside'] else 'nothing_inside'
                continue
            floats = 0
            custom = []
            try:
                floats = int(component.get_editor_property('num_custom_data_floats'))
                custom = list(component.get_editor_property('per_instance_sm_custom_data')) if floats else []
            except Exception as error:  # noqa: BLE001 - reflection shape differs by launch mode
                row['customDataReadError'] = repr(error)
            for record in row['inside']:
                if floats and custom:
                    record['customData'] = [float(v) for v in custom[record['index'] * floats:(record['index'] + 1) * floats]]
            row['numCustomDataFloats'] = floats
            row['action'] = 'removal_started'
            self.write()
            _mark_modified(component)
            # Descending index order: InstancedStaticMeshComponent::RemoveInstance compacts the array, so any
            # lower index recorded above stays valid.
            for record in sorted(row['inside'], key=lambda r: r['index'], reverse=True):
                if not component.remove_instance(record['index']):
                    raise RuntimeError('remove_instance(%d) returned False on %s' % (record['index'], entry['label']))
            row['instancesAfter'] = int(component.get_instance_count())
            if row['instancesAfter'] != count - len(row['inside']):
                raise RuntimeError('Instance count after removal differs on ' + entry['label'])
            if not self.ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
                raise RuntimeError('%s instances were removed but no map package is dirty; the save would drop them' % entry['label'])
            row['action'] = 'removed'
            out['removedTotal'] += len(row['inside'])
            self.write()
        return out

    def revert_trees(self, prior):
        ue = self.ue
        out = {'components': [], 'readdedTotal': 0}
        self.receipt['fixes']['trees'] = out
        rows = {row['label']: row for row in prior.get('components', [])}
        for entry, actor, component in self.tree_components():
            row = rows.get(entry['label'])
            result = {'label': entry['label'], 'action': 'nothing_to_revert'}
            out['components'].append(result)
            if not row or row.get('action') not in ('removal_started', 'removed'):
                continue
            result['action'] = 'readd_started'
            result['readded'] = []
            self.write()
            floats = int(row.get('numCustomDataFloats') or 0)
            _mark_modified(component)
            for record in row['inside']:
                t = record['transform']
                transform = ue.Transform(location=ue.Vector(*t['location']), rotation=ue.Rotator(pitch=t['rotation'][0], yaw=t['rotation'][1], roll=t['rotation'][2]), scale=ue.Vector(*t['scale']))
                new_index = int(component.add_instance(transform, True))
                if new_index < 0:
                    raise RuntimeError('add_instance failed on ' + entry['label'])
                for i, value in enumerate(record.get('customData', [])[:floats]):
                    component.set_custom_data_value(new_index, i, float(value), True)
                result['readded'].append(new_index)
            result['instancesAfter'] = int(component.get_instance_count())
            result['action'] = 'readded'
            out['readdedTotal'] += len(result['readded'])
            self.write()
        return out

    # -- fix: access -----------------------------------------------------------------

    def existing_access_actors(self):
        cfg = self.spec['access']
        return [row for row in self.snapshot.values()
                if row['label'].startswith(cfg['labelPrefix']) or any(m and m.startswith(cfg['namespace'] + '/') for m in row['meshes'])]

    def import_adapter(self, record, namespace):
        ue = self.ue
        ui = ue.FbxImportUI()
        for key, value in dict(automated_import_should_detect_type=False, mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
                               import_as_skeletal=False, import_mesh=True, import_animations=False, import_materials=False,
                               import_textures=False, create_physics_asset=False).items():
            ui.set_editor_property(key, value)
        data = ui.get_editor_property('static_mesh_import_data')
        for key, value in dict(combine_meshes=True, transform_vertex_to_absolute=True, bake_pivot_in_vertex=False,
                               convert_scene=False, convert_scene_unit=False, force_front_x_axis=False, import_uniform_scale=1.0,
                               auto_generate_collision=False, build_nanite=False, generate_lightmap_u_vs=False, remove_degenerates=True,
                               normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():
            data.set_editor_property(key, value)
        task = ue.AssetImportTask()
        for key, value in dict(filename=record['path'], destination_path=namespace, destination_name=record['name'], automated=True,
                               async_=False, replace_existing=False, save=False, options=ui, factory=ue.FbxFactory()).items():
            task.set_editor_property(key, value)
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objects = list(task.get_objects())
        if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
            raise RuntimeError('Import of %s produced %s' % (record['name'], [type(o).__name__ for o in objects]))
        return objects[0]

    def fix_access(self, dry_run, offline):
        ue = self.ue
        cfg = self.spec['access']
        plan = offline['access']
        out = {'interpretation': cfg['scenario'], 'namespace': cfg['namespace'], 'zLiftCm': cfg['zLiftCm'], 'meshes': [], 'action': 'planned',
               'offlinePlan': {k: plan[k] for k in ('corridorYcm', 'platformWestEdgeXAtCorridorCm', 'coplanarOverlapWithPlatformDeckCm', 'openingV2Checks')}}
        self.receipt['fixes']['access'] = out
        existing = self.existing_access_actors()
        out['existingAccessActors'] = [row['label'] for row in existing]
        out['namespaceExists'] = bool(self.namespace_exists(cfg['namespace']))
        if existing:
            if dry_run:
                out['action'] = 'blocked_existing_actors'
                return out
            raise RuntimeError('Existing RELEASE_MountAccess actors preserved; refusing duplicate placement: %s' % out['existingAccessActors'][:10])
        # An earlier run may have imported and saved the assets but failed before the map save (2026-09-08 first run):
        # reuse them only if every expected asset exists and verifies against the frozen source; never re-import over them.
        reuse = {}
        if out['namespaceExists']:
            for record in plan['meshes']:
                asset_path = cfg['namespace'] + '/' + record['name']
                if not self.assets.does_asset_exist(asset_path):
                    raise RuntimeError('Namespace exists but %s is missing; inspect before rerun' % asset_path)
                mesh = ue.load_asset(asset_path)
                if not isinstance(mesh, ue.StaticMesh):
                    raise RuntimeError('Existing asset is not a StaticMesh: ' + asset_path)
                error = _box_error(_box(mesh.get_bounding_box()), record['boundsUEcm'])
                triangles = int(mesh.get_num_triangles(0))
                if error > cfg['boundsToleranceCm'] or triangles != record['triangles']:
                    raise RuntimeError('Existing %s differs from source (bounds %.4f cm, %d tris); refusing reuse' % (asset_path, error, triangles))
                reuse[record['name']] = mesh
            out['reusedExistingAssets'] = sorted(_asset_path(m) for m in reuse.values())
        materials = {}
        for key, path in cfg['materials'].items():
            material = ue.load_asset(path)
            if not isinstance(material, ue.MaterialInterface):
                raise RuntimeError('Access material missing: ' + path)
            materials[key] = material
        if dry_run:
            out['meshes'] = [{'name': r['name'], 'label': r['label'], 'material': r['material'], 'triangles': r['triangles'],
                              'plannedWorldBoundsCm': r['plannedWorldBoundsCm'], 'action': 'planned'} for r in plan['meshes']]
            return out
        out['action'] = 'import_started'
        self.write()
        spawned = []
        for record in plan['meshes']:
            row = {'name': record['name'], 'label': record['label'], 'material': record['material'], 'adapterObjSha256': record['sha256'], 'action': 'import_started'}
            out['meshes'].append(row)
            self.write()
            mesh = reuse.get(record['name']) or self.import_adapter(record, cfg['namespace'])
            row['assetReused'] = record['name'] in reuse
            actual = _box(mesh.get_bounding_box())
            row['assetPath'] = _asset_path(mesh)
            row['boundsErrorCm'] = _box_error(actual, record['boundsUEcm'])
            row['triangles'] = int(mesh.get_num_triangles(0))
            if row['boundsErrorCm'] > cfg['boundsToleranceCm']:
                raise RuntimeError('%s imported bounds differ by %.4f cm' % (record['name'], row['boundsErrorCm']))
            if row['triangles'] != record['triangles']:
                raise RuntimeError('%s imported %d triangles, expected %d' % (record['name'], row['triangles'], record['triangles']))
            mesh.set_material(0, materials[record['materialKey']])
            setup = mesh.get_editor_property('body_setup')
            if setup is None:
                setup = ue.BodySetup(outer=mesh)
                mesh.set_editor_property('body_setup', setup)
            setup.set_editor_property('collision_trace_flag', ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            setup.set_editor_property('double_sided_geometry', True)
            mesh.set_editor_property('lod_for_collision', 0)
            if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + record['name'])
            row['action'] = 'asset_saved'
            self.write()
            location = record['plannedLocation']
            actor = self.actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(*location), ue.Rotator(pitch=0.0, yaw=0.0, roll=0.0), transient=False)
            if actor is None:
                raise RuntimeError('StaticMeshActor spawn returned None for ' + record['label'])
            actor.set_actor_label(record['label'])
            actor.set_folder_path(cfg['folder'])
            actor.set_editor_property('tags', [ue.Name(self.spec['actorTag']), ue.Name(self.spec['interpretationTag'])])
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            if component is None or not component.set_static_mesh(mesh):
                raise RuntimeError('set_static_mesh failed for ' + record['label'])
            component.set_mobility(ue.ComponentMobility.STATIC)
            component.set_collision_profile_name(cfg['collisionProfile'])
            row.update(actorName=actor.get_name(), location=location, rotation=[0.0, 0.0, 0.0], scale=[1.0, 1.0, 1.0],
                       plannedWorldBoundsCm=record['plannedWorldBoundsCm'], action='spawned')
            spawned.append((record, row, actor))
            self.write()
        out['action'] = 'spawned_pending_save'
        return out

    def verify_access_after_reopen(self, out):
        ue = self.ue
        cfg = self.spec['access']
        readback = []
        for row in out['meshes']:
            matches = [r for r in self.snapshot.values() if r['label'] == row['label']]
            if len(matches) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (row['label'], len(matches)))
            actor = matches[0]['actor']
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            origin, extent = actor.get_actor_bounds(False)
            bounds = {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z], 'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}
            entry = {'label': row['label'], 'actorName': matches[0]['actor'].get_name(), 'meshPath': matches[0]['meshes'], 'pose': list(matches[0]['pose']),
                     'worldBoundsCm': bounds, 'boundsErrorCm': _box_error(bounds, row['plannedWorldBoundsCm']),
                     'collisionProfile': str(component.get_collision_profile_name()), 'material': _asset_path(component.get_material(0)),
                     'tags': [str(t) for t in actor.get_editor_property('tags')]}
            pose_error = max(abs(a - b) for a, b in zip(matches[0]['pose'], tuple(row['location']) + (0.0, 0.0, 0.0) + (1.0, 1.0, 1.0)))
            entry['poseErrorCm'] = pose_error
            if matches[0]['meshes'] != (row['assetPath'],):
                raise RuntimeError('Reopened mesh differs for ' + row['label'])
            if pose_error > cfg['transformToleranceCm']:
                raise RuntimeError('Reopened transform differs for %s by %.4f' % (row['label'], pose_error))
            if entry['boundsErrorCm'] > cfg['boundsToleranceCm'] + 0.5:
                raise RuntimeError('Reopened bounds differ for %s by %.4f' % (row['label'], entry['boundsErrorCm']))
            if entry['collisionProfile'] != cfg['collisionProfile']:
                raise RuntimeError('Collision profile %s on %s' % (entry['collisionProfile'], row['label']))
            readback.append(entry)
        out['reopenedReadback'] = readback
        out['action'] = 'saved_reopened_visual_walk_acceptance_pending'

    def revert_access(self, prior):
        out = {'destroyed': [], 'assetsRetained': [], 'action': 'nothing_to_revert'}
        self.receipt['fixes']['access'] = out
        out['priorLabels'] = [row['label'] for row in prior.get('meshes', []) if row.get('actorName')]
        out['assetsRetained'] = [row.get('assetPath') for row in prior.get('meshes', []) if row.get('assetPath')]
        # Every RELEASE_MountAccess_ actor / MountAccessV2-mesh actor goes, whether or not the prior receipt listed it.
        targets = self.existing_access_actors()
        if not targets:
            return out
        out['action'] = 'destroy_started'
        self.write()
        for row in targets:
            name = row['actor'].get_name()
            if not self.actors.destroy_actor(row['actor']):
                raise RuntimeError('destroy_actor returned False for ' + row['label'])
            out['destroyed'].append({'label': row['label'], 'actorName': name, 'meshes': list(row['meshes'])})
        out['action'] = 'destroyed_pending_save'
        out['note'] = 'Imported MountAccessV2 assets are kept (never delete an asset namespace automatically); with the editor closed the checkpoint folder is the byte-exact alternative.'
        return out


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------

def _latest_apply_receipt(spec):
    folder = ROOT / spec['receiptFolder']
    rows = []
    for path in sorted(folder.glob(spec['receiptPrefix'] + '*.json')):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        status = str(data.get('status', ''))
        # Anything that may have written assets or the map (asset saves precede the map save).
        if data.get('mode') == 'apply' and data.get('fixes') and (status.startswith('exterior_fixes_saved') or (status.startswith('failed_') and status != 'failed_before_any_write')):
            rows.append(path)
    if not rows:
        raise RuntimeError('No apply receipt to revert in ' + str(folder))
    return rows[-1]


def run(mode, fixes=None, revert_receipt=None):
    import unreal as ue
    spec = load_spec()
    requested = normalise_fixes(fixes) if fixes else None
    fixes = requested or normalise_fixes(spec['defaultFixes'])
    stamp = stamp_now()
    map_file = ROOT / spec['targetMapFile']
    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(receipt_path))
    prior = None
    if mode == 'revert':
        source = Path(revert_receipt) if revert_receipt else _latest_apply_receipt(spec)
        prior = json.loads(source.read_text(encoding='utf-8-sig'))
        # Revert everything the prior run touched unless the caller narrowed it with -ExteriorFixes.
        fixes = normalise_fixes([f for f in prior['fixesRequested'] if requested is None or f in requested])
    offline = offline_check(spec, fixes)
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}
    receipt = {
        'status': 'started', 'mode': mode, 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == spec['lastKnownMapSha256'], 'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'scriptSha256': sha256_of(globals().get('__file__') or (ROOT / 'Scripts' / 'release_exterior_fixes.py')),
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'fixesRequested': list(fixes), 'offlineCheck': offline,
        'revertSource': str(revert_receipt or '') if mode == 'revert' else None, 'fixes': {}, 'errors': [], 'checkpoint': None, 'mapSaved': False,
        'interpretation': spec['interpretationTag'], 'limitations': list(spec['limitations']),
    }
    if mode == 'revert':
        receipt['revertSource'] = str(source)
    engine = Engine(ue, spec, receipt, receipt_path)
    engine.write()
    saved = False
    try:
        engine.common_guards()
        engine.load_target()
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('Map dirty right after load; resolve before continuing')
        snapshot = engine.take_snapshot()
        baseline = Engine.numeric(snapshot)
        receipt['actorCountBefore'] = len(snapshot)
        engine.write()

        dry_run = mode == 'dry_run'
        if mode == 'apply':
            touched = []
            if 'tiling' in fixes:
                touched += list(spec['tiling']['materials'])
            if 'sky' in fixes:
                touched.append(spec['sky']['materialInstance'])
            folder, copied = engine.checkpoint(stamp, touched)
            receipt['checkpoint'] = str(folder)
            receipt['checkpointAssetCopies'] = copied
            engine.write()
        elif mode == 'revert':
            touched = [p for p in prior.get('fixes', {}).get('tiling', {}).get('materials', {})]
            if prior.get('fixes', {}).get('sky', {}).get('materialInstance'):
                touched.append(prior['fixes']['sky']['materialInstance'])
            folder, copied = engine.checkpoint(stamp, touched)
            receipt['checkpoint'] = str(folder)
            receipt['checkpointAssetCopies'] = copied
            engine.write()

        new_actor_names = set()
        for fix in fixes:
            if mode == 'revert':
                prior_fix = prior.get('fixes', {}).get(fix) or {}
                {'access': engine.revert_access, 'tiling': engine.revert_tiling, 'trees': engine.revert_trees, 'sky': engine.revert_sky}[fix](prior_fix)
            elif fix == 'access':
                engine.fix_access(dry_run, offline)
                new_actor_names |= {row.get('actorName') for row in receipt['fixes']['access']['meshes'] if row.get('actorName')}
            elif fix == 'tiling':
                engine.fix_tiling(dry_run)
            elif fix == 'trees':
                engine.fix_trees(dry_run)
            elif fix == 'sky':
                engine.fix_sky(dry_run)
            engine.write()

        if dry_run:
            if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('Dry run left dirty packages; nothing was saved but inspect the log')
            receipt['status'] = 'dry_run_planned_nothing_written'
            return receipt

        # unrelated actors must be untouched before save (new actors excluded; destroyed actors excluded on revert)
        current = Engine.numeric(engine.take_snapshot())
        destroyed = {d['actorName'] for d in receipt['fixes'].get('access', {}).get('destroyed', [])} if mode == 'revert' else set()
        changed = [name for name, row in baseline.items() if name not in destroyed and current.get(name) != row]
        tree_labels = {c['label'] for c in spec['trees']['components']}
        changed = [n for n in changed if baseline[n][0] not in tree_labels]  # ISM edits keep the actor pose; label check keeps this honest
        if changed:
            raise RuntimeError('Unrelated actors changed before save: %s' % changed[:10])
        unexpected_new = [n for n in current if n not in baseline and n not in new_actor_names]
        if unexpected_new:
            raise RuntimeError('Unexpected new actors before save: %s' % unexpected_new[:10])

        dirty_maps = [str(p.get_name()) for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        receipt['dirtyMapPackagesBeforeSave'] = dirty_maps
        if dirty_maps:
            if not engine.levels.save_current_level():
                raise RuntimeError('save_current_level returned False')
            saved = True
            receipt['mapSaved'] = True
            receipt['mapSha256AfterSave'] = sha256_of(map_file)
        receipt['dirtyContentPackagesAfterSave'] = [str(p.get_name()) for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()][:50]
        engine.write()

        # reopen + readback
        engine.load_target()
        reopened = engine.take_snapshot()
        reopened_numeric = Engine.numeric(reopened)
        receipt['actorCountAfter'] = len(reopened)
        changed = [name for name, row in baseline.items() if name not in destroyed and reopened_numeric.get(name) != row and baseline[name][0] not in tree_labels]
        if changed:
            raise RuntimeError('Unrelated actors differ after reopen: %s' % changed[:10])
        if mode == 'apply' and 'access' in fixes:
            engine.verify_access_after_reopen(receipt['fixes']['access'])
        if 'trees' in fixes:
            counts = {}
            for entry, actor, component in engine.tree_components():
                counts[entry['label']] = int(component.get_instance_count())
            receipt['fixes']['trees']['instancesAfterReopen'] = counts
        if 'tiling' in fixes:
            engine.tiling_reopen_readback(receipt['fixes']['tiling'])
        if mode == 'revert':
            remaining = engine.existing_access_actors()
            receipt['fixes'].setdefault('access', {})['remainingAccessActorsAfterReopen'] = [r['label'] for r in remaining]
        receipt['status'] = ('exterior_fixes_saved_reopened_visual_walk_acceptance_pending' if mode == 'apply' else 'exterior_fixes_reverted_saved_reopened')
        return receipt
    except Exception as error:
        receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        if mode == 'dry_run':
            receipt['status'] = 'dry_run_failed_nothing_written'
        else:
            receipt['status'] = 'failed_after_save_checkpoint_available' if saved else ('failed_before_map_save_checkpoint_available' if receipt.get('checkpoint') else 'failed_before_any_write')
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(m, 'umap')) == v for m, v in protected.items())
        if not receipt['protectedMapsUnchanged']:
            receipt['status'] = 'failed_protected_map_hash_changed'
            receipt['errors'].append('Protected map bytes changed')
        engine.write()
        if not receipt['protectedMapsUnchanged'] and sys.exc_info()[0] is None:
            raise RuntimeError('Protected map hash changed')


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

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
    return 'release_exterior_fixes.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    tokens = command_line.split()
    lowered = [t.lower() for t in tokens]
    mode = 'apply'
    revert_receipt = None
    fixes = None
    for token in tokens:
        low = token.lower()
        if low == '-exteriordryrun':
            mode = 'dry_run'
        elif low == '-exteriorrevert' or low.startswith('-exteriorrevert='):
            mode = 'revert'
            if '=' in token:
                revert_receipt = token.split('=', 1)[1].strip('"')
        elif low.startswith('-exteriorfixes='):
            fixes = normalise_fixes(token.split('=', 1)[1].strip('"'))
    if '-exteriordryrun' in lowered and mode == 'revert':
        raise RuntimeError('Pass at most one of -ExteriorDryRun, -ExteriorRevert')
    try:
        receipt = run(mode, fixes=fixes, revert_receipt=revert_receipt)
        ue.log('release_exterior_fixes: %s mode %s fixes %s mapSaved %s' % (receipt['status'], mode, receipt['fixesRequested'], receipt['mapSaved']))
    except Exception as error:
        ue.log_error('release_exterior_fixes failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line.lower() and '-run=pythonscript' not in command_line.lower():
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

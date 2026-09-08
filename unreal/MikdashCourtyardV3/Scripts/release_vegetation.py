"""Guarded release placement of JudeanFloraV1 vegetation into the combined map.

Imports the offline OBJ meshes and PNG textures produced by Scripts/create_vegetation.py,
assembles each species' LOD ladder onto one StaticMesh, and places the planned instances as
hierarchical instanced components in
/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.

Every number comes from Scripts/release_vegetation.spec.json and from the placement plan it
hashes, so a human can review the whole plan before an engine is launched.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_vegetation.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Vegetation-01.log"

Optional switches (read from the engine command line):
  -VegetationImportOnly          import and assemble the meshes, place nothing.
  -VegetationMaxBatches=<n>      place at most n batches this run (default from the spec).
  -VegetationResume=<receipt>    read a previous receipt and skip every batch it completed.
  -VegetationSpecies=Olive,Fig   restrict this run to the named species.
  -VegetationSkipImport          the meshes are already imported; go straight to placement.

BATCHING AND RESUME - why this is not one big run
-------------------------------------------------
This machine has 16 GB and a previous large import here had to be run in groups to survive it.
So the plan is shipped pre-grouped into batches of at most a few thousand instances each,
keyed by 400 m placement cell; a run places at most -VegetationMaxBatches of them, records
every completed batch id in its receipt, and a following run started with
-VegetationResume=<that receipt> skips exactly what was already done. Re-placing a batch is
refused rather than de-duplicated, because a silent de-duplication would hide a resume that
had not actually resumed.

SAFETY MODEL (the same one release_place_assets.py uses)
--------------------------------------------------------
  * Refuses to run with the wrong project directory, a game world, dirty packages, or a loaded
    world that is not the combined map.
  * Copies Walkthrough.umap and any One-File-Per-Actor folders to
    ReviewCheckpoints/Vegetation-<stamp>/ before any mutation, and verifies the copy by hash.
  * Validates the plan and the manifest by SHA256 against the files on disk, and refuses a plan
    whose recorded status is not the expected one.
  * Every planned instance is re-tested in the editor against the Mount enclosure ring and
    against the existing tree instances before it is spawned. A plan error cannot put a tree
    inside the precinct.
  * Saves only if something was placed, reopens the map, and reads back the instance count of
    every component it created numerically.
  * The receipt JSON is written at start and again in finally, so partial state survives a
    failure.

TWO CLEARANCE TRAPS, BOTH REPEATED HERE ON THE LIVE LEVEL
----------------------------------------------------------
The offline generator already excluded these, but the editor sees the real actors and must not
re-introduce them:
  * The 256 SM_JerusalemTerrain_* tiles have 400-800 m AABBs that enclose the whole Temple.
    They are the GROUND. They are skipped by prefix and the skipped count is recorded, so this
    exclusion cannot silently stop matching after a rename.
  * Hollow derived-union meshes have AABBs that enclose the entire outer court. They are
    decomposed into their constituent boxes from the architecture manifest, and the
    recomposition is verified against the manifest's own bounds before the boxes are trusted.
Using raw bounds for either of these gives 100 per cent false blockers, which is a mistake this
project has already paid a day for.
"""
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_vegetation.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so offline_check() runs anywhere, including
# under scripts/verify.py on a machine with no engine open.
# --------------------------------------------------------------------------

def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


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


def load_plan(spec):
    plan = json.loads((ROOT / spec['plan']).read_text(encoding='utf-8'))
    if plan['status'] != spec['planStatusRequired']:
        raise RuntimeError('Placement plan status is %r, expected %r'
                           % (plan['status'], spec['planStatusRequired']))
    return plan


def load_manifest(spec):
    manifest = json.loads((ROOT / spec['manifest']).read_text(encoding='utf-8'))
    if manifest['status'] != spec['manifestStatusRequired']:
        raise RuntimeError('Geometry manifest status is %r, expected %r'
                           % (manifest['status'], spec['manifestStatusRequired']))
    return manifest


def point_in_polygon(x, y, points):
    inside = False
    j = len(points) - 1
    for i in range(len(points)):
        xi, yi = points[i]
        xj, yj = points[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def point_segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    if length < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + dx * t), py - (ay + dy * t))


def distance_to_ring(x, y, points):
    best = float('inf')
    j = len(points) - 1
    for i in range(len(points)):
        best = min(best, point_segment_distance(x, y, points[j][0], points[j][1],
                                                points[i][0], points[i][1]))
        j = i
    return best


def union_constituent_boxes(entry):
    """World AABBs of the boxes a hollow derived-union mesh was built from.

    Identical arithmetic to release_place_assets.union_constituent_boxes: source elements are
    in amot with X east, Y up, Z south, and the manifest's mapping is [x*scale, z*scale, y*scale].
    """
    properties = entry.get('sourceProperties') or {}
    if 'source_elements_json' not in properties:
        return None
    scale = float(properties.get('source_metres_per_amah', 0.5)) * 100.0
    boxes = []
    for element in json.loads(properties['source_elements_json']):
        if element.get('shape') != 'box':
            return None
        position, size = element['position'], element['size']
        centre = [position[0] * scale, position[2] * scale, position[1] * scale]
        half = [size[0] * scale / 2.0, size[2] * scale / 2.0, size[1] * scale / 2.0]
        boxes.append({'name': element.get('name'),
                      'min': [centre[i] - half[i] for i in range(3)],
                      'max': [centre[i] + half[i] for i in range(3)]})
    return boxes


def verify_union_decomposition(entry, tolerance):
    boxes = union_constituent_boxes(entry)
    if not boxes:
        raise RuntimeError('Union %s has no box decomposition in the manifest' % entry['assetName'])
    recomposed = {'min': [min(b['min'][i] for b in boxes) for i in range(3)],
                  'max': [max(b['max'][i] for b in boxes) for i in range(3)]}
    expected = entry['expectedBoundsUnrealCm']
    error = max(abs(recomposed[k][i] - expected[k][i]) for k in ('min', 'max') for i in range(3))
    if error > tolerance:
        raise RuntimeError('Union %s decomposition differs from manifest bounds by %.3f cm'
                           % (entry['assetName'], error))
    return boxes


class Grid2D:
    """Uniform bucket grid, so a proximity query touches a handful of points, not 4265."""

    def __init__(self, cell_cm):
        self.cell = float(cell_cm)
        self.buckets = {}

    def insert(self, x, y, payload=None):
        key = (int(math.floor(x / self.cell)), int(math.floor(y / self.cell)))
        self.buckets.setdefault(key, []).append((x, y, payload))

    def within(self, x, y, radius):
        cx, cy = int(math.floor(x / self.cell)), int(math.floor(y / self.cell))
        span = int(math.ceil(radius / self.cell))
        for dy in range(-span, span + 1):
            for dx in range(-span, span + 1):
                for px, py, payload in self.buckets.get((cx + dx, cy + dy), ()):
                    if (px - x) ** 2 + (py - y) ** 2 <= radius * radius:
                        return payload if payload is not None else True
        return None


def species_form(manifest, key):
    for record in manifest['species']:
        if record['key'] == key:
            return record['form']
    raise KeyError(key)


def lod_screen_size(sphere_radius_cm, distance_cm, minimum):
    """UE screen size for a mesh of this radius at this distance.

    2 * radius / distance is the standard small-angle perspective approximation at a 90 degree
    horizontal field of view. It is an approximation, it is recorded as one in the spec, and it
    is a starting point for a visual tune rather than a final answer.
    """
    if distance_cm <= 0.0:
        return 1.0
    return max(minimum, min(1.0, 2.0 * sphere_radius_cm / distance_cm))


def offline_check(spec=None):
    """Consistency checks that need no engine. Raises on the first failure."""
    spec = spec or load_spec()
    plan = load_plan(spec)
    manifest = load_manifest(spec)
    problems = []

    obj_folder = ROOT / spec['objFolder']
    for record in manifest['meshes']:
        path = obj_folder / record['file']
        if not path.exists():
            problems.append('missing OBJ ' + record['file'])
        elif sha256_of(path) != record['sha256']:
            problems.append('OBJ changed since the manifest was written: ' + record['file'])
    texture_folder = ROOT / spec['textureFolder']
    for entry in manifest['textures']:
        for key in ('leafAtlas', 'barkBaseColour', 'barkNormal', 'billboardTexture'):
            name = entry.get(key)
            if not name:
                continue
            path = texture_folder / name
            if not path.exists():
                problems.append('missing texture ' + name)
            elif sha256_of(path) != entry[key + 'Sha256']:
                problems.append('texture changed since the manifest was written: ' + name)

    total = sum(batch['count'] for batch in plan['batches'])
    if total != plan['totalInstances']:
        problems.append('plan batch counts sum to %d, header says %d' % (total, plan['totalInstances']))
    if total > spec['instanceCapTotal']:
        problems.append('plan holds %d instances, cap is %d' % (total, spec['instanceCapTotal']))
    if len(set(batch['batchId'] for batch in plan['batches'])) != len(plan['batches']):
        problems.append('duplicate batch ids in the plan')
    for batch in plan['batches']:
        if len(batch['instances']) != batch['count']:
            problems.append('batch %s count mismatch' % batch['batchId'])
    if len(plan['instanceFormat']) != 9:
        problems.append('unexpected instance format %r' % (plan['instanceFormat'],))

    ring_receipt = json.loads((ROOT / spec['clearance']['mountEnclosureReceipt']).read_text(encoding='utf-8-sig'))
    ring = [(float(p[0]), float(p[1])) for p in ring_receipt['boundaryXYcm']]
    margin = spec['clearance']['mountEnclosureMarginCm']
    inside = 0
    for batch in plan['batches']:
        for row in batch['instances']:
            if point_in_polygon(row[0], row[1], ring) or distance_to_ring(row[0], row[1], ring) <= margin:
                inside += 1
    if inside:
        problems.append('%d planned instances are inside the Mount enclosure ring or its margin' % inside)

    architecture = json.loads((ROOT / spec['clearance']['architectureManifest']).read_text(encoding='utf-8-sig'))
    unions = [e for e in architecture['meshes'] if (e.get('sourceProperties') or {}).get('source_elements_json')]
    union_boxes = 0
    for entry in unions:
        union_boxes += len(verify_union_decomposition(entry, spec['clearance']['unionDecompositionToleranceCm']))

    if problems:
        raise RuntimeError('offline check failed: ' + '; '.join(problems[:8]))
    return {
        'specSha256': sha256_of(SPEC_PATH),
        'planSha256': sha256_of(ROOT / spec['plan']),
        'manifestSha256': sha256_of(ROOT / spec['manifest']),
        'meshFiles': len(manifest['meshes']),
        'textureSets': len(manifest['textures']),
        'plannedInstances': total,
        'batches': len(plan['batches']),
        'instanceCapTotal': spec['instanceCapTotal'],
        'mountEnclosureRingPoints': len(ring),
        'plannedInstancesInsidePrecinct': inside,
        'hollowUnionsVerified': len(unions),
        'hollowUnionConstituentBoxes': union_boxes,
        'note': ('Every planned instance was re-tested against the Mount enclosure ring here, '
                 'offline, before any engine was launched, and every hollow union decomposition '
                 'was verified against the architecture manifest bounds.'),
    }


# --------------------------------------------------------------------------
# Engine side
# --------------------------------------------------------------------------

def _asset_path(obj):
    return obj.get_path_name() if obj else None


def _vector_list(v):
    return [float(v.x), float(v.y), float(v.z)]


class Release:
    """Engine handles, the cached scene snapshot and the receipt."""

    def __init__(self, ue, spec, plan, manifest):
        self.ue = ue
        self.spec = spec
        self.plan = plan
        self.manifest = manifest
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.world = None
        self.snapshot = None
        self.receipt = None
        self.receipt_path = None
        self.components = {}

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=1, default=str) + '\n',
                                     encoding='utf-8')

    # -- scene -------------------------------------------------------------

    def take_snapshot(self):
        ue = self.ue
        rows = []
        for actor in self.actors.get_all_level_actors():
            meshes = []
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                meshes.append(_asset_path(component.get_editor_property('static_mesh')))
            rows.append({'actor': actor, 'name': actor.get_name(), 'label': actor.get_actor_label(),
                         'folder': str(actor.get_folder_path()), 'meshes': meshes})
        self.snapshot = rows
        return rows

    def baseline(self, rows):
        return {row['name']: (row['label'], tuple(row['meshes']), str(row['folder'])) for row in rows}

    def clearance_from_level(self):
        """Blockers read from the live level, with both AABB traps handled explicitly."""
        ue = self.ue
        clearance = self.spec['clearance']
        prefixes = tuple(clearance['terrainMeshPrefixes'])
        boxes = []
        terrain_skipped = 0
        # SUBSTRING, not startswith: the 256 tiles were imported with a `terrain_` prefix
        # normalisation, so the asset is terrain_SM_JerusalemTerrain_07_07 while the manifest
        # calls it SM_JerusalemTerrain_07_07. A startswith test would match nothing, the
        # exclusion would be silently off, and every point in the court would be blocked again.
        for row in self.snapshot:
            names = [n or '' for n in row['meshes']] + [row['label']]
            if any(token in name for name in names for token in prefixes):
                terrain_skipped += 1
                continue
        self.receipt['clearance'] = {
            'terrainActorsSkippedAsGround': terrain_skipped,
            'terrainMeshPrefixes': list(prefixes),
            'terrainNote': clearance['terrainMeshNote'],
        }
        if terrain_skipped == 0:
            raise RuntimeError('No terrain actor matched %r. The prefix has changed and the '
                               'exclusion is silently off, which is exactly how the 100 per cent '
                               'false-blocker result happened before.' % (prefixes,))

        architecture = json.loads((ROOT / clearance['architectureManifest']).read_text(encoding='utf-8-sig'))
        union_boxes = 0
        for entry in architecture['meshes']:
            decomposition = union_constituent_boxes(entry)
            if decomposition:
                for box in verify_union_decomposition(entry, clearance['unionDecompositionToleranceCm']):
                    boxes.append(box)
                    union_boxes += 1
        self.receipt['clearance']['hollowUnionConstituentBoxes'] = union_boxes
        self.receipt['clearance']['hollowUnionNote'] = clearance['unionNote']

        # Existing illustrative trees: read their real instance transforms and keep out of them.
        tree_grid = Grid2D(clearance['existingTreeProximityCm'] * 2.0)
        existing = 0
        substrings = clearance['existingTreeMeshSubstrings']
        for row in self.snapshot:
            actor = row['actor']
            for component in actor.get_components_by_class(ue.InstancedStaticMeshComponent):
                mesh = _asset_path(component.get_editor_property('static_mesh')) or ''
                if not any(token in mesh for token in substrings):
                    continue
                count = int(component.get_instance_count())
                for index in range(count):
                    ok, transform = component.get_instance_transform(index, True)
                    if not ok:
                        continue
                    location = transform.translation
                    tree_grid.insert(float(location.x), float(location.y))
                    existing += 1
        self.receipt['clearance']['existingTreeInstancesRead'] = existing
        self.receipt['clearance']['existingTreeProximityCm'] = clearance['existingTreeProximityCm']
        self.receipt['clearance']['existingTreeNote'] = clearance['existingTreeNote']

        ring_receipt = json.loads((ROOT / clearance['mountEnclosureReceipt']).read_text(encoding='utf-8-sig'))
        ring = [(float(p[0]), float(p[1])) for p in ring_receipt['boundaryXYcm']]
        self.receipt['clearance']['mountEnclosureRingPoints'] = len(ring)
        self.receipt['clearance']['mountEnclosureNote'] = clearance['mountEnclosureNote']
        return {'boxes': boxes, 'trees': tree_grid, 'ring': ring,
                'ringMargin': clearance['mountEnclosureMarginCm'],
                'treeRadius': clearance['existingTreeProximityCm']}

    @staticmethod
    def blocked(clearance, x, y):
        if point_in_polygon(x, y, clearance['ring']):
            return 'inside_mount_enclosure_ring'
        if distance_to_ring(x, y, clearance['ring']) <= clearance['ringMargin']:
            return 'within_mount_enclosure_margin'
        for box in clearance['boxes']:
            if box['min'][0] <= x <= box['max'][0] and box['min'][1] <= y <= box['max'][1]:
                return 'union_constituent_box:' + str(box.get('name'))
        if clearance['trees'].within(x, y, clearance['treeRadius']):
            return 'existing_tree_instance'
        return None

    # -- import ------------------------------------------------------------

    def import_assets(self):
        """Import every OBJ and PNG, then assemble the LOD ladders."""
        ue = self.ue
        spec = self.spec
        obj_folder = ROOT / spec['objFolder']
        texture_folder = ROOT / spec['textureFolder']
        tasks = []
        for record in self.manifest['meshes']:
            options = ue.FbxImportUI()
            options.set_editor_property('import_mesh', True)
            options.set_editor_property('import_textures', False)
            options.set_editor_property('import_materials', False)
            options.set_editor_property('import_as_skeletal', False)
            options.static_mesh_import_data.set_editor_property('combine_meshes', True)
            options.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs', True)
            options.static_mesh_import_data.set_editor_property('auto_generate_collision', False)
            task = ue.AssetImportTask()
            task.set_editor_property('filename', str(obj_folder / record['file']))
            task.set_editor_property('destination_path', spec['meshFolder'])
            task.set_editor_property('destination_name', record['mesh'])
            task.set_editor_property('replace_existing', True)
            task.set_editor_property('automated', True)
            task.set_editor_property('save', False)
            task.set_editor_property('options', options)
            tasks.append(task)
        for entry in self.manifest['textures']:
            for key in ('leafAtlas', 'barkBaseColour', 'barkNormal', 'billboardTexture'):
                name = entry.get(key)
                if not name:
                    continue
                task = ue.AssetImportTask()
                task.set_editor_property('filename', str(texture_folder / name))
                task.set_editor_property('destination_path', spec['textureAssetFolder'])
                task.set_editor_property('replace_existing', True)
                task.set_editor_property('automated', True)
                task.set_editor_property('save', False)
                tasks.append(task)
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

        imported, missing = [], []
        for record in self.manifest['meshes']:
            path = '%s/%s' % (spec['meshFolder'], record['mesh'])
            asset = ue.EditorAssetLibrary.load_asset(path)
            if asset is None:
                missing.append(record['mesh'])
                continue
            imported.append({'mesh': record['mesh'], 'asset': path,
                             'triangles': record['triangles'],
                             'canonicalBoundsCm': record['canonicalBoundsCm']})
        if missing:
            raise RuntimeError('%d meshes failed to import, first: %s' % (len(missing), missing[:5]))
        self.receipt['importedMeshes'] = len(imported)
        self.receipt['importedMeshList'] = imported
        return imported

    def assemble_lods(self):
        """Fold each species' LOD1/LOD2/billboard meshes into the LOD0 mesh as real LODs."""
        ue = self.ue
        spec = self.spec
        subsystem = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)
        ladders = {}
        for record in self.manifest['meshes']:
            if record.get('variant'):
                continue
            role = record['materialRole']
            key = (record['species'], 'leaf' if role in ('leaf', 'billboard') else 'bark')
            ladders.setdefault(key, []).append(record)
        assembled = []
        for (species, role), records in sorted(ladders.items()):
            records.sort(key=lambda r: r['lodStartDistanceCm'])
            base = records[0]
            base_asset = ue.EditorAssetLibrary.load_asset('%s/%s' % (spec['meshFolder'], base['mesh']))
            radius = 0.5 * math.sqrt(sum((base['canonicalBoundsCm']['max'][i]
                                          - base['canonicalBoundsCm']['min'][i]) ** 2 for i in range(3)))
            screen_sizes = [1.0]
            for index, record in enumerate(records[1:], start=1):
                source = ue.EditorAssetLibrary.load_asset('%s/%s' % (spec['meshFolder'], record['mesh']))
                subsystem.set_lod_from_static_mesh(base_asset, index, source, 0, True)
                screen_sizes.append(lod_screen_size(radius, record['lodStartDistanceCm'],
                                                    spec['lod']['minimumScreenSize']))
            assembled.append({'species': species, 'role': role, 'mesh': base['mesh'],
                              'lodCount': len(records),
                              'lodStartDistanceCm': [r['lodStartDistanceCm'] for r in records],
                              'lodScreenSizes': [round(s, 5) for s in screen_sizes],
                              'boundsSphereRadiusCm': round(radius, 2),
                              'screenSizeRule': spec['lod']['screenSizeRule']})
        self.receipt['lodLadders'] = assembled
        return assembled

    # -- placement ---------------------------------------------------------

    def component_for(self, species, role):
        """One hierarchical instanced component per species and material role."""
        ue = self.ue
        spec = self.spec
        key = (species, role)
        if key in self.components:
            return self.components[key]
        mesh_name = '%s%s_L0_%s' % (spec['meshPrefix'], species, role.capitalize())
        mesh = ue.EditorAssetLibrary.load_asset('%s/%s' % (spec['meshFolder'], mesh_name))
        if mesh is None:
            raise RuntimeError('Mesh not imported: ' + mesh_name)
        label = '%s%s_%s_%s' % (spec['labelPrefix'], spec['group'], species, role.capitalize())
        actor = self.actors.spawn_actor_from_class(ue.Actor, ue.Vector(0.0, 0.0, 0.0))
        actor.set_actor_label(label)
        actor.set_folder_path(spec['folder'])
        actor.tags = [spec['actorTag']]
        component = actor.add_component_by_class(ue.HierarchicalInstancedStaticMeshComponent,
                                                 False, ue.Transform(), False)
        component.set_editor_property('static_mesh', mesh)
        component.set_editor_property('mobility', ue.ComponentMobility.STATIC)
        component.set_collision_profile_name('NoCollision')
        form = species_form(self.manifest, species)
        cull = float(spec['lod']['cullDistanceCm'][form])
        component.set_cull_distances(int(cull * spec['lod']['cullStartFraction']), int(cull))
        self.components[key] = {'actor': actor, 'component': component, 'label': label,
                                'mesh': mesh_name, 'species': species, 'role': role,
                                'added': 0, 'cullDistanceCm': cull}
        return self.components[key]

    def place_batches(self, batches, clearance):
        ue = self.ue
        placed_rows = []
        refused = {}
        for batch in batches:
            species = batch['species']
            roles = ['leaf'] if species_form(self.manifest, species) == 'grass' else ['bark', 'leaf']
            accepted = []
            for row in batch['instances']:
                reason = self.blocked(clearance, row[0], row[1])
                if reason:
                    refused[reason] = refused.get(reason, 0) + 1
                    continue
                accepted.append(row)
            transforms = []
            for row in accepted:
                transforms.append(ue.Transform(
                    ue.Vector(row[0], row[1], row[2]),
                    ue.Rotator(row[4], row[3], row[5]),
                    ue.Vector(row[6], row[6], row[7])))
            for role in roles:
                entry = self.component_for(species, role)
                if transforms:
                    entry['component'].add_instances(transforms, False)
                    entry['added'] += len(transforms)
            placed_rows.append({'batchId': batch['batchId'], 'species': species, 'cell': batch['cell'],
                                'planned': batch['count'], 'placed': len(accepted),
                                'roles': roles})
            self.receipt['completedBatchIds'].append(batch['batchId'])
        self.receipt['refusedByClearance'] = refused
        self.receipt['batchesPlaced'] = placed_rows
        return placed_rows

    def readback(self):
        """Numeric instance counts after the reopen. This is the check that matters."""
        ue = self.ue
        rows = []
        for entry in sorted(self.components.values(), key=lambda e: e['label']):
            matching = [row for row in self.snapshot if row['label'] == entry['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (entry['label'], len(matching)))
            actor = matching[0]['actor']
            components = actor.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent)
            if len(components) != 1:
                raise RuntimeError('%s has %d instanced components after reopen, expected 1'
                                   % (entry['label'], len(components)))
            component = components[0]
            count = int(component.get_instance_count())
            mesh = _asset_path(component.get_editor_property('static_mesh')) or ''
            bounds = actor.get_actor_bounds(False)
            row = {'label': entry['label'], 'species': entry['species'], 'role': entry['role'],
                   'meshPath': mesh, 'expectedInstances': entry['added'],
                   'readbackInstances': count,
                   'cullDistanceCm': entry['cullDistanceCm'],
                   'worldBoundsCentreCm': _vector_list(bounds[0]),
                   'worldBoundsExtentCm': _vector_list(bounds[1])}
            if count != entry['added']:
                raise RuntimeError('%s: %d instances written, %d read back after reopen. '
                                   'Runtime-added instance components did not persist.'
                                   % (entry['label'], entry['added'], count))
            if entry['mesh'] not in mesh:
                raise RuntimeError('%s: reopened mesh %s is not %s' % (entry['label'], mesh, entry['mesh']))
            rows.append(row)
        self.receipt['reopenedReadback'] = rows
        self.receipt['reopenedInstanceTotal'] = sum(r['readbackInstances'] for r in rows)
        return rows


def place(load_target=True, max_batches=None, resume_receipt=None, species_filter=None,
          import_only=False, skip_import=False):
    """Run the guarded placement. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    spec = load_spec()
    plan = load_plan(spec)
    manifest = load_manifest(spec)
    offline = offline_check(spec)

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    run = Release(ue, spec, plan, manifest)
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

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps']
                 if disk_path(m, 'umap').exists()}
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

    already_done = []
    if resume_receipt:
        previous = json.loads(Path(resume_receipt).read_text(encoding='utf-8'))
        if previous.get('planSha256') != offline['planSha256']:
            raise RuntimeError('Resume receipt was made against a different placement plan')
        already_done = list(previous.get('completedBatchIds') or [])

    pending = [b for b in plan['batches'] if b['batchId'] not in set(already_done)]
    if species_filter:
        pending = [b for b in pending if b['species'] in species_filter]
    limit = max_batches if max_batches is not None else spec['batching']['defaultMaxBatchesPerRun']
    selected = pending[:limit] if limit and limit > 0 else pending

    run.receipt = {
        'status': 'checkpointed_vegetation_placement_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': offline['specSha256'],
        'planSha256': offline['planSha256'],
        'manifestSha256': offline['manifestSha256'],
        'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'seed': plan['seed'],
        'resumeReceipt': str(resume_receipt) if resume_receipt else None,
        'batchesAlreadyComplete': len(already_done),
        'batchesPending': len(pending),
        'batchesSelectedThisRun': len(selected),
        'batchesRemainingAfterThisRun': max(0, len(pending) - len(selected)),
        'speciesFilter': sorted(species_filter) if species_filter else None,
        'completedBatchIds': list(already_done),
        'importOnly': bool(import_only),
        'errors': [],
        'mapSaved': False,
        'limitations': list(spec['limitations']),
    }
    run.write_receipt()

    saved = False
    try:
        run.take_snapshot()
        baseline = run.baseline(run.snapshot)
        clashes = [row['label'] for row in run.snapshot
                   if row['label'].startswith(spec['labelPrefix'] + spec['group'] + '_')]
        if clashes and not already_done:
            raise RuntimeError('Vegetation release actors already exist and no resume receipt was '
                               'given; refusing duplicate placement: %s' % clashes[:8])

        if not skip_import:
            run.import_assets()
            run.assemble_lods()
            run.write_receipt()
        if import_only:
            run.receipt['status'] = 'meshes_imported_no_placement'
            if not ue.EditorAssetLibrary.save_directory(spec['assetFolder'], False, True):
                raise RuntimeError('save_directory failed for ' + spec['assetFolder'])
            return run.receipt

        clearance = run.clearance_from_level()
        run.write_receipt()
        placed = run.place_batches(selected, clearance)
        total_added = sum(entry['added'] for entry in run.components.values())
        if total_added == 0:
            run.receipt['status'] = 'nothing_placed_map_unchanged'
            return run.receipt

        current = run.baseline(run.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:8])

        if not ue.EditorAssetLibrary.save_directory(spec['assetFolder'], False, True):
            raise RuntimeError('save_directory failed for ' + spec['assetFolder'])
        if not run.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()

        if not run.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run.world = run.editor.get_editor_world()
        run.take_snapshot()
        reopened_numeric = run.baseline(run.snapshot)
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:8])
        run.readback()

        run.receipt['batchesPlacedThisRun'] = len(placed)
        run.receipt['instancesPlacedThisRun'] = total_added
        run.receipt['status'] = ('vegetation_placed_saved_reopened_visual_runtime_acceptance_pending'
                                 if run.receipt['batchesRemainingAfterThisRun'] == 0 else
                                 'vegetation_batch_placed_saved_reopened_resume_required')
        return run.receipt
    except Exception as error:
        run.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        run.receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                                 else 'failed_before_save_map_unchanged')
        raise
    finally:
        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapBytesChanged'] = run.receipt['mapSha256After'] != map_sha_before
        run.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
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
    return 'release_vegetation.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    lowered = command_line.lower()
    max_batches = None
    resume = None
    species = None
    import_only = '-vegetationimportonly' in lowered
    skip_import = '-vegetationskipimport' in lowered
    for token in command_line.split():
        low = token.lower()
        if low.startswith('-vegetationmaxbatches='):
            max_batches = int(token.split('=', 1)[1])
        elif low.startswith('-vegetationresume='):
            resume = token.split('=', 1)[1].strip('"')
        elif low.startswith('-vegetationspecies='):
            species = set(part for part in token.split('=', 1)[1].strip('"').split(',') if part)
    try:
        receipt = place(load_target=True, max_batches=max_batches, resume_receipt=resume,
                        species_filter=species, import_only=import_only, skip_import=skip_import)
        ue.log('release_vegetation: %s placed %s this run, %s batches remain' % (
            receipt['status'], receipt.get('instancesPlacedThisRun'),
            receipt.get('batchesRemainingAfterThisRun')))
    except Exception as error:
        ue.log_error('release_vegetation failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in lowered and '-run=pythonscript' not in lowered:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

"""Guarded native import and placement of EnclosureV2 - the toggleable Yechezkel precinct.

Imports the four module meshes written by Scripts/create_enclosure.py --export and places ONE
AMikdashEnclosure actor into the combined IntegratedReviewV2 map. That actor builds the whole
1.44 km ring as instances at run time, so this script adds a handful of assets and a single
actor, not a wall.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_enclosure.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Enclosure-01.log"

Optional switches, read from the engine command line:
  -EnclosureState=modern|overlay|yechezkel   the state the placed actor opens in
                                             (default modern - the viewer should recognise the
                                             city before anything is added to it)
  -EnclosureCountOnly=1                      run every guard and every measurement, write the
                                             receipt, and place NOTHING. This is how the
                                             building count is obtained without touching the map.

Run this module outside the editor and it prints offline_check() as JSON and exits; nothing
native happens and nothing is written.

WHERE THE CENTRE COMES FROM
---------------------------
Not from a guess and not from a constant in this file. SourceAssets/architecture-manifest.json
records `coordinateConvention.geometry` = "World positions baked in vertices; all object
transforms identity; spawn every imported asset at origin", and every measured mesh carries
`spawnLocationUnrealCm` [0, 0, 0]. The measured court centre is therefore the world origin by
construction, and the guard PROVES it rather than assuming it: it re-reads
SM_0127_architecture_Outer_court_supporting_platform out of the manifest, requires its bounds
to be +-8100 on both axes about the origin, requires the Altar yesod ring to be centred on
(0, 0), and refuses to run if either has moved. The square is then anchored off that platform
by EnclosureMath.h's rule, and the result is checked against the four outer faces already
shipped in SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json.

THE TRAP THAT COST THIS PROJECT A DAY, AND HOW IT IS AVOIDED HERE
-----------------------------------------------------------------
Counting "which modern buildings fall inside the precinct" by testing actor AABBs against the
square returns a hundred per cent false positives unless two families of actor are handled
first, and both of them are in this map:

  1. THE 256 TERRAIN TILES. /Game/MikdashV3/JerusalemContext/Terrain holds
     SM_JerusalemTerrain_00_00 .. _15_15, plus four _FutureMountCut duplicates in
     /Game/MikdashV3/FutureMountV1/Terrain. Each tile is a 400 m square - two and a half times
     the whole Temple court - and the tiles under the Mount enclose the Temple outright. They
     are excluded BY ASSET PATH AND NAME PREFIX, before any bounds test runs, because no
     bounds test can tell a tile from a building. AGENTS.md records the same rule.

  2. THE HOLLOW BOOLEAN UNIONS. 'Derived union of source outer envelope walls' is 116 outer
     wall boxes fused into one mesh; its AABB is +-8100 XY, Z 300..3425, i.e. the entire court.
     Treated as a solid it makes every point inside the court look occupied. Its constituent
     walls are not separate actors ("originals retained hidden"), so it cannot simply be
     skipped either. As in Scripts/release_place_assets.py, the union is DECOMPOSED from
     `sourceProperties.source_elements_json` in the architecture manifest into its constituent
     world boxes, the decomposition is verified to recompose to the recorded bounds, and the
     boxes are tested individually.

  3. One further family this script adds to the list: JCTX_ISM_* actors under
     /Game/MikdashV3/JerusalemContext/DecorativeInstancesV1 hold 44,793 instances between five
     components, so a single actor AABB is the whole city. Excluded by prefix.

Every exclusion is COUNTED and named in the receipt. An exclusion that silently swallows a
real building is the same bug in the other direction, so the receipt carries the excluded
labels and not only a number.

SAFETY MODEL (identical in shape to Scripts/release_place_assets.py)
  * Refuses to run with the wrong project directory, a game world active, dirty packages, or a
    loaded world that is not the combined map.
  * Copies Walkthrough.umap and any One-File-Per-Actor folders to a checkpoint before any
    mutation, and verifies the copy by hash.
  * Refuses to place if an EnclosureV2 release actor already exists.
  * Saves only if something was actually placed, then RELOADS the map and reads back the
    placed actor numerically - its class, its transform, the four outer faces its own maths
    produces, and the count of buildings it would hide.
  * The receipt JSON is written at start and again in `finally`, so a failure preserves
    partial state with evidence rather than losing it.
  * Nothing is ever deleted. The actor hides modern buildings by visibility at run time and
    restores them on EndPlay; this script never hides anything itself and never edits a
    building actor.
"""
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_enclosure.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
HEADER = ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/EnclosureMath.h'


# --------------------------------------------------------------------------
# Pure helpers - no `unreal` import, so offline_check() runs anywhere.
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def header_constants():
    """The same parse create_enclosure.py does, for the same reason: never restate a number
    that EnclosureMath.h already owns."""
    text = HEADER.read_text(encoding='utf-8')
    found = {}
    for name, value in re.findall(r'constexpr\s+double\s+(\w+)\s*=\s*([^;]+);', text):
        value = value.strip()
        if re.fullmatch(r'-?\d+(\.\d+)?', value):
            found[name] = float(value)
    found['PrecinctSideAmot'] = found['PrecinctReedsPerSide'] * found['AmotPerReed']
    return found


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def boxes_overlap_xy(a, b, tolerance=1e-6):
    for i in range(2):
        if min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) <= tolerance:
            return False
    return True


def union_constituent_boxes(entry):
    """World AABBs of a hollow union's constituent boxes.

    The manifest stores them in SOURCE axes (X east, Y up, Z south) in amot; the swap and the
    scale below are exactly those of Scripts/release_place_assets.union_constituent_boxes, and
    recomposing them must reproduce the union's recorded bounds or the decomposition is
    refused rather than trusted.
    """
    properties = entry.get('sourceProperties') or {}
    raw = properties.get('source_elements_json')
    if not raw:
        return None
    scale = float(properties.get('source_metres_per_amah', 0.5)) * 100.0
    boxes = []
    for element in json.loads(raw):
        if element.get('shape') != 'box':
            return None
        position, size = element['position'], element['size']
        centre = [position[0] * scale, position[2] * scale, position[1] * scale]
        half = [size[0] * scale / 2.0, size[2] * scale / 2.0, size[1] * scale / 2.0]
        boxes.append({'min': [centre[i] - half[i] for i in range(3)],
                      'max': [centre[i] + half[i] for i in range(3)]})
    return boxes


def verify_union_decomposition(entry, tolerance):
    boxes = union_constituent_boxes(entry)
    if not boxes:
        return None, 'no decomposition recorded'
    recomposed = {'min': [min(b['min'][i] for b in boxes) for i in range(3)],
                  'max': [max(b['max'][i] for b in boxes) for i in range(3)]}
    expected = entry['expectedBoundsUnrealCm']
    error = box_error(recomposed, {'min': expected['min'], 'max': expected['max']})
    if error > tolerance:
        return None, 'decomposition recomposes to a different box (%.4f cm)' % error
    return boxes, None


# --------------------------------------------------------------------------
# The square, and the proof that the centre is where the receipts say
# --------------------------------------------------------------------------

def temple_centre_from_receipts(spec):
    """Prove the measured court centre rather than assume it.

    Returns (centre_xy, evidence). Raises if the manifest no longer supports the claim - a
    silently wrong centre would put a 1.44 km wall in the wrong place and everything
    downstream would still look self-consistent.
    """
    manifest_path = ROOT / spec['architectureManifest']
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    convention = (manifest.get('coordinateConvention') or {}).get('geometry', '')
    if 'spawn every imported asset at origin' not in convention:
        raise RuntimeError('architecture-manifest.json no longer states the origin-spawn '
                           'convention; the court centre can no longer be taken as (0, 0). '
                           'Convention read: ' + convention[:200])

    by_name = {}
    non_origin = []
    for entry in manifest.get('meshes', []):
        by_name[entry.get('assetName')] = entry
        spawn = entry.get('spawnLocationUnrealCm')
        if spawn is not None and any(abs(float(v)) > 1e-6 for v in spawn):
            non_origin.append(entry.get('assetName'))
    if non_origin:
        raise RuntimeError('%d measured meshes no longer spawn at the origin (e.g. %s); the '
                           'court centre is no longer the world origin'
                           % (len(non_origin), non_origin[:5]))

    platform_name = spec['courtPlatformAsset']
    platform = by_name.get(platform_name)
    if platform is None:
        raise RuntimeError('architecture-manifest.json no longer contains ' + platform_name)
    bounds = platform['expectedBoundsUnrealCm']
    half = float(spec['courtPlatformHalfExtentCm'])
    worst = max(abs(bounds['min'][0] + half), abs(bounds['max'][0] - half),
                abs(bounds['min'][1] + half), abs(bounds['max'][1] - half))
    if worst > float(spec['verification']['boundsToleranceCm']):
        raise RuntimeError('%s bounds are no longer +-%g about the origin (worst %.4f cm)'
                           % (platform_name, half, worst))

    # Second, independent witness: the Altar yesod ring, which must be centred on (0, 0).
    ring = [by_name[name] for name in spec['altarYesodAssets'] if name in by_name]
    if len(ring) != len(spec['altarYesodAssets']):
        raise RuntimeError('The Altar yesod ring is no longer complete in the manifest')
    ring_min = [min(e['expectedBoundsUnrealCm']['min'][i] for e in ring) for i in range(2)]
    ring_max = [max(e['expectedBoundsUnrealCm']['max'][i] for e in ring) for i in range(2)]
    ring_centre = [(ring_min[i] + ring_max[i]) / 2.0 for i in range(2)]
    if max(abs(v) for v in ring_centre) > float(spec['verification']['boundsToleranceCm']):
        raise RuntimeError('The Altar yesod ring centre has moved to %r' % ring_centre)

    return [0.0, 0.0], dict(
        manifest=str(manifest_path), manifestSha256=sha256_of(manifest_path),
        convention=convention,
        courtPlatformAsset=platform_name, courtPlatformBoundsCm=bounds,
        courtPlatformHalfExtentErrorCm=round(worst, 6),
        altarYesodRingCentreCm=ring_centre,
        meshesCheckedForOriginSpawn=len(by_name))


def square_from(centre_xy, constants):
    side = constants['PrecinctSideAmot'] * constants['ProjectCmPerAmah']
    half_court = constants['CourtPlatformHalfExtentUnrealCm']
    west = centre_xy[0] - half_court - constants['BookClearWestAmot'] * constants['ProjectCmPerAmah']
    north = centre_xy[1] - half_court - constants['BookClearNorthAmot'] * constants['ProjectCmPerAmah']
    return dict(west=west, north=north, east=west + side, south=north + side, sideCm=side,
                centreCm=[west + side / 2.0, north + side / 2.0])


# --------------------------------------------------------------------------
# Offline check
# --------------------------------------------------------------------------

def offline_check(spec=None):
    """Everything that can be established without the engine. Runs first, every time; a
    failure here is a refusal before any package is opened."""
    spec = spec or load_spec()
    constants = header_constants()
    centre, centre_evidence = temple_centre_from_receipts(spec)
    sq = square_from(centre, constants)

    manifest_path = ROOT / spec['geometryManifest']
    if not manifest_path.exists():
        raise RuntimeError('Run Scripts/create_enclosure.py --export first; %s is absent'
                           % manifest_path)
    geometry = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    faces = geometry['square']['outerFacesCm']
    worst = max(abs(faces['xWest'] - sq['west']), abs(faces['xEast'] - sq['east']),
                abs(faces['yNorth'] - sq['north']), abs(faces['ySouth'] - sq['south']))
    if worst > 1e-6:
        raise RuntimeError('geometry-manifest.json square differs from the header rule by '
                           '%g cm' % worst)

    # Every OBJ must still hash to what the manifest recorded, or the import would bring in
    # geometry nobody reviewed.
    mesh_folder = manifest_path.parent / 'EnclosureV2'
    mismatched, missing = [], []
    for record in geometry['meshes']:
        obj = mesh_folder / record['file']
        if not obj.exists():
            missing.append(record['file'])
        elif sha256_of(obj) != record['sha256']:
            mismatched.append(record['file'])
    if missing or mismatched:
        raise RuntimeError('OBJ set does not match the manifest; missing=%r changed=%r'
                           % (missing, mismatched))

    existing_design = ROOT / spec['existingEnclosureDesign']
    design_agreement = 'enclosure-design.json absent'
    if existing_design.exists():
        design = json.loads(existing_design.read_text(encoding='utf-8-sig'))
        existing_faces = design['enclosure']['outerFacesCm']
        error = max(abs(existing_faces['xWest'] - sq['west']),
                    abs(existing_faces['xEast'] - sq['east']),
                    abs(existing_faces['yNorth'] - sq['north']),
                    abs(existing_faces['ySouth'] - sq['south']))
        if error > 1e-6:
            raise RuntimeError('EnclosureV2 square differs from the shipped EnclosureV1 design '
                               'by %g cm; one of the two is wrong and this script will not '
                               'guess which' % error)
        design_agreement = 'identical to EnclosureV1 on all four outer faces'

    return dict(
        status='offline_checks_passed',
        specSha256=sha256_of(SPEC_PATH),
        enclosureMathSha256=sha256_of(HEADER),
        generatorSha256=geometry['generatorSha256'],
        templeCentreEvidence=centre_evidence,
        precinctCentreCm=sq['centreCm'],
        outerFacesCm={k: sq[k] for k in ('west', 'east', 'north', 'south')},
        sideAmot=constants['PrecinctSideAmot'],
        sideReeds=constants['PrecinctSideAmot'] / constants['AmotPerReed'],
        sideMetresUnderAmahOpinions={
            'naeh-48-and-the-books-own': constants['PrecinctSideAmot'] * 48.0 / 100.0,
            'project-50': constants['PrecinctSideAmot'] * 50.0 / 100.0,
            'feinstein-54': constants['PrecinctSideAmot'] * 54.0 / 100.0,
            'chazon-ish-57.6': constants['PrecinctSideAmot'] * 57.6 / 100.0,
            'chazon-ish-stringent-58': constants['PrecinctSideAmot'] * 58.0 / 100.0,
        },
        clearancesAmot=geometry['clearancesAmot'],
        clearanceOrder=geometry['clearanceOrder'],
        instancing=geometry['instancing'],
        modernCityCoverageOffline=geometry['modernCityCoverage'],
        agreementWithEnclosureV1=design_agreement,
        objFiles=[dict(file=r['file'], sha256=r['sha256'], triangles=r['triangles'])
                  for r in geometry['meshes']])


# --------------------------------------------------------------------------
# Native
# --------------------------------------------------------------------------

def _vector_list(v):
    return [float(v.x), float(v.y), float(v.z)]


def _asset_path(obj):
    return None if obj is None else str(obj.get_path_name())


class OmissionError(RuntimeError):
    """A group that could not be placed for a reason with numeric evidence, as opposed to a
    guard failure. Recorded in the receipt; never silently swallowed."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


class Placement(object):
    def __init__(self, ue, spec):
        self.ue = ue
        self.spec = spec
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.assets = ue.AssetToolsHelpers.get_asset_tools()
        self.receipt = {}
        self.receipt_path = None

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=1, ensure_ascii=False),
                                     encoding='utf-8')

    # -- level survey -----------------------------------------------------

    def survey(self):
        """One pass over the level, classifying every actor into building / excluded / other.

        The classification is BY ASSET PATH first and by label second. Labels are duplicable
        and a duplicate label is exactly how a terrain tile could sneak into the building set;
        an asset path is not.
        """
        ue = self.ue
        rows = []
        for actor in self.actors.get_all_level_actors():
            if actor is None:
                continue
            label = str(actor.get_actor_label())
            meshes = []
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                path = _asset_path(component.static_mesh)
                if path:
                    meshes.append(path)
            origin, extent = actor.get_actor_bounds(False)
            rows.append(dict(
                label=label, name=str(actor.get_name()),
                folder=str(actor.get_folder_path()), meshes=sorted(set(meshes)),
                bounds={'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
                        'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]},
                centroid=[origin.x, origin.y],
                actor=actor))
        return rows

    def classify(self, rows, sq):
        """Which modern buildings fall inside, with every exclusion named."""
        spec = self.spec
        excluded, considered = [], []
        for row in rows:
            label = row['label']
            paths = ' '.join(row['meshes'])
            if any(label.startswith(p) for p in spec['excludedLabelPrefixes']) or \
               any(folder in paths for folder in spec['excludedAssetFolders']):
                excluded.append(dict(label=label, reason='excluded_by_name_or_asset_folder',
                                     longestSideCm=max(row['bounds']['max'][i] - row['bounds']['min'][i]
                                                       for i in range(2))))
                continue
            if any(label.startswith(p) for p in spec['modernBuildingLabelPrefixes']):
                considered.append(row)
        inside, straddling, outside = [], [], []
        for row in considered:
            cx, cy = row['centroid']
            if sq['west'] <= cx <= sq['east'] and sq['north'] <= cy <= sq['south']:
                inside.append(row['label'])
            elif boxes_overlap_xy({'min': [sq['west'], sq['north'], -1e9],
                                   'max': [sq['east'], sq['south'], 1e9]}, row['bounds']):
                straddling.append(row['label'])
            else:
                outside.append(row['label'])
        return dict(
            consideredActors=len(considered),
            excludedActors=len(excluded),
            excludedSample=sorted(e['label'] for e in excluded)[:40],
            excludedLongestSideCm=max([e['longestSideCm'] for e in excluded] or [0.0]),
            insideActors=sorted(inside), straddlingActors=sorted(straddling),
            insideActorCount=len(inside), straddlingActorCount=len(straddling),
            outsideActorCount=len(outside),
            note=('Actor counts, not building counts: the Old City is batched one mesh per '
                  '100 m cell, so one actor carries many buildings. '
                  'SourceAssets/enclosure-review/geometry-manifest.json modernCityCoverage.'
                  'exact carries the per-building figure from the OSM source polygons.'))

    def union_envelope_check(self, rows):
        """Prove the hollow unions would have been false positives, and that decomposing them
        is what removes the false positive. This is the day this project lost, asserted."""
        spec = self.spec
        manifest = json.loads((ROOT / spec['architectureManifest']).read_text(encoding='utf-8-sig'))
        by_label = {}
        for entry in manifest.get('meshes', []):
            if entry.get('semantic') == 'union':
                # Actor labels drop the SM_NNNN_union_ prefix.
                by_label[re.sub(r'^SM_\d+_union_', '', entry.get('assetName', ''))] = entry
        report = []
        for row in rows:
            if not row['label'].startswith('Derived union of '):
                continue
            entry = None
            for name, candidate in by_label.items():
                if row['label'].replace(' ', '_').lower().startswith(name.lower()[:24]):
                    entry = candidate
                    break
            longest = max(row['bounds']['max'][i] - row['bounds']['min'][i] for i in range(2))
            record = dict(label=row['label'], actorAabbLongestSideCm=longest)
            if entry is None:
                record['decomposition'] = 'no manifest entry matched; excluded by prefix only'
            else:
                boxes, error = verify_union_decomposition(
                    entry, float(spec['verification']['boundsToleranceCm']))
                if error:
                    record['decomposition'] = 'REFUSED: ' + error
                else:
                    record['decomposition'] = 'verified'
                    record['constituentBoxes'] = len(boxes)
                    record['largestConstituentSideCm'] = max(
                        max(b['max'][i] - b['min'][i] for i in range(2)) for b in boxes)
            report.append(record)
        return report

    # -- import -----------------------------------------------------------

    def import_modules(self, geometry, mesh_folder):
        ue = self.ue
        destination = self.spec['meshFolder']
        imported = []
        for record in geometry['meshes']:
            asset_path = destination + '/' + record['name']
            existing = ue.EditorAssetLibrary.does_asset_exist(asset_path)
            if existing and not self.spec['reimportExisting']:
                raise OmissionError('Mesh already exists and reimport is off: ' + asset_path,
                                    {'asset': asset_path})
            task = ue.AssetImportTask()
            task.filename = str(mesh_folder / record['file'])
            task.destination_path = destination
            task.destination_name = record['name']
            task.automated = True
            task.replace_existing = True
            task.save = False
            self.assets.import_asset_tasks([task])
            mesh = ue.EditorAssetLibrary.load_asset(asset_path)
            if mesh is None:
                raise OmissionError('Import produced no asset for ' + asset_path,
                                    {'obj': record['file']})
            bounds = mesh.get_bounds()
            origin = _vector_list(bounds.origin)
            extent = _vector_list(bounds.box_extent)
            actual = {'min': [origin[i] - extent[i] for i in range(3)],
                      'max': [origin[i] + extent[i] for i in range(3)]}
            # The legacy importer reflects Y back, so the imported bounds must reproduce the
            # CANONICAL bounds. If they do not, the adapter convention has changed and every
            # instance placed from this mesh would be mirrored.
            error = box_error(actual, record['canonicalBoundsCm'])
            if error > float(self.spec['verification']['boundsToleranceCm']):
                raise OmissionError(
                    'Imported bounds differ from canonical by %.4f cm for %s; the Y-reflect '
                    'adapter convention no longer holds' % (error, record['name']),
                    {'asset': asset_path, 'imported': actual,
                     'canonical': record['canonicalBoundsCm']})
            triangles = int(mesh.get_num_triangles(0))
            if triangles != record['triangles']:
                raise OmissionError('Imported triangle count %d != %d for %s'
                                    % (triangles, record['triangles'], record['name']),
                                    {'asset': asset_path})
            imported.append(dict(asset=asset_path, obj=record['file'], triangles=triangles,
                                 importedBoundsCm=actual, boundsErrorCm=round(error, 6),
                                 replacedExisting=bool(existing)))
        return imported

    # -- place ------------------------------------------------------------

    def place_actor(self, imported, initial_state):
        ue = self.ue
        spec = self.spec
        actor_class = getattr(ue, 'MikdashEnclosure', None)
        if actor_class is None:
            raise OmissionError(
                'AMikdashEnclosure is not available to Python. The plugin has not been rebuilt '
                'since Private/MikdashEnclosure.cpp was added, so the class does not exist in '
                'this editor. The meshes above are imported and reviewable; rebuild the '
                'MikdashCourtyardV3Editor target and re-run to place the actor.',
                {'importedMeshes': [entry['asset'] for entry in imported]})
        actor = self.actors.spawn_actor_from_class(actor_class, ue.Vector(0.0, 0.0, 0.0),
                                                   ue.Rotator(0.0, 0.0, 0.0))
        if actor is None:
            raise OmissionError('spawn_actor_from_class returned None for MikdashEnclosure')
        actor.set_actor_label(spec['actorLabel'])
        actor.set_folder_path(spec['folder'])
        actor.tags = [spec['actorTag']]
        by_role = {entry['obj']: entry['asset'] for entry in imported}

        def mesh_for(name):
            for obj, asset in by_role.items():
                if obj.startswith(name):
                    return ue.EditorAssetLibrary.load_asset(asset)
            return None

        actor.set_editor_property('WallModuleMesh', mesh_for('SM_EnclosureV2_WallSegment'))
        actor.set_editor_property('GateModuleMesh', mesh_for('SM_EnclosureV2_Gate'))
        actor.set_editor_property('CornerModuleMesh', mesh_for('SM_EnclosureV2_Corner'))
        actor.set_editor_property('OverlayQuadMesh', mesh_for('SM_EnclosureV2_OverlaySlab'))
        actor.set_editor_property('CourtCentreUnrealCm', ue.Vector2D(0.0, 0.0))
        actor.set_editor_property('CourtPlatformHalfExtentCm',
                                  float(spec['courtPlatformHalfExtentCm']))
        actor.set_editor_property('ModernBuildingLabelPrefixes',
                                  list(spec['modernBuildingLabelPrefixes']))
        actor.set_editor_property('ExcludedLabelPrefixes', list(spec['excludedLabelPrefixes']))
        actor.set_editor_property('InitialState', initial_state)
        return actor


def place(load_target=True, initial_state='modern', count_only=False):
    """Guarded import and placement. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    spec = load_spec()
    offline = offline_check(spec)
    constants = header_constants()
    sq = square_from([0.0, 0.0], constants)

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    run = Placement(ue, spec)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target and not run.levels.load_level(TARGET):
        raise RuntimeError('load_level failed for ' + TARGET)
    world = run.editor.get_editor_world()
    loaded = world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
       ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed placement')

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps']
                 if disk_path(m, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    run.receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))

    checkpoint = None
    external_copied = []
    if not count_only:
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[6:]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[6:])
                external_copied.append(str(external))

    run.receipt = {
        'status': 'measurement_only_started' if count_only else 'checkpointed_placement_started',
        'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint) if checkpoint else None,
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'countOnly': bool(count_only),
        'initialState': initial_state,
        'placed': {}, 'omissions': {}, 'errors': [], 'mapSaved': False,
        'limitations': [
            'Placement is geometric only. No visual, halachic, walking or packaged acceptance '
            'is established by this run.',
            'The instanced wall sits on the level plane; it is not stepped to the terrain the '
            'way SourceAssets/FutureMountV1/EnclosureV1 is. Over the Kidron and the Hinnom the '
            'ring will float or bury until per-instance ground Z is added.',
            'Gate positions along each wall are the project assumption, not the book. Only the '
            'count per side and the 10 x 50 amah opening are sourced.',
            'The 3000-amah reading is one side of a live dispute. Middot 2:1\'s 500-amah Har '
            'HaBayit is offered as the other and is not presented as refuted; see '
            'SourceAssets/enclosure-review/sources.md.',
        ],
    }
    run.write_receipt()

    saved = False
    try:
        rows = run.survey()
        run.receipt['actorCountBefore'] = len(rows)
        existing = [row['label'] for row in rows
                    if row['label'].startswith(spec['actorLabel'])]
        if existing and not count_only:
            raise RuntimeError('An EnclosureV2 release actor already exists: %r' % existing)
        run.receipt['preExistingEnclosureActors'] = existing

        # The trap, measured before anything is placed.
        run.receipt['unionEnvelopeCheck'] = run.union_envelope_check(rows)
        selection = run.classify(rows, sq)
        run.receipt['selection'] = selection

        # And the counterfactual: what the same test returns with the exclusions switched off.
        # Recording both is the only way a reader can see that the exclusion list is doing
        # work rather than being decorative.
        unguarded_inside = 0
        for row in rows:
            cx, cy = row['centroid']
            if sq['west'] <= cx <= sq['east'] and sq['north'] <= cy <= sq['south']:
                unguarded_inside += 1
        run.receipt['selectionWithoutExclusions'] = dict(
            insideActorCount=unguarded_inside,
            falsePositivesAvoided=unguarded_inside - selection['insideActorCount'],
            note=('Every actor whose centroid lands in the square, with no name or asset-folder '
                  'exclusion at all. The difference is what the exclusion list is worth.'))
        run.write_receipt()

        if count_only:
            run.receipt['status'] = 'measurement_only_map_unchanged'
            return run.receipt

        geometry_path = ROOT / spec['geometryManifest']
        geometry = json.loads(geometry_path.read_text(encoding='utf-8-sig'))
        mesh_folder = geometry_path.parent / 'EnclosureV2'
        try:
            imported = run.import_modules(geometry, mesh_folder)
            run.receipt['placed']['meshes'] = imported
        except OmissionError as omission:
            run.receipt['omissions']['meshes'] = {'reason': str(omission),
                                                  'evidence': omission.evidence}
            run.receipt['status'] = 'nothing_placed_map_unchanged'
            return run.receipt

        state_enum = {'modern': 0, 'yechezkel': 1, 'overlay': 2}[initial_state]
        actor = None
        try:
            actor = run.place_actor(imported, state_enum)
            run.receipt['placed']['actor'] = dict(label=spec['actorLabel'],
                                                  folder=spec['folder'],
                                                  initialState=initial_state)
        except OmissionError as omission:
            run.receipt['omissions']['actor'] = {'reason': str(omission),
                                                 'evidence': omission.evidence}

        if actor is None and not imported:
            run.receipt['status'] = 'nothing_placed_map_unchanged'
            return run.receipt

        if not run.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()

        if not run.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        reopened = run.survey()
        run.receipt['actorCountAfterReopen'] = len(reopened)
        readback = dict(meshes=[], actor=None)
        for entry in run.receipt['placed'].get('meshes', []):
            mesh = ue.EditorAssetLibrary.load_asset(entry['asset'])
            if mesh is None:
                raise RuntimeError('Reopened asset missing: ' + entry['asset'])
            bounds = mesh.get_bounds()
            origin = _vector_list(bounds.origin)
            extent = _vector_list(bounds.box_extent)
            actual = {'min': [origin[i] - extent[i] for i in range(3)],
                      'max': [origin[i] + extent[i] for i in range(3)]}
            readback['meshes'].append(dict(asset=entry['asset'],
                                           triangles=int(mesh.get_num_triangles(0)),
                                           worldBoundsCm=actual,
                                           boundsErrorCm=box_error(actual,
                                                                   entry['importedBoundsCm'])))
        matching = [row for row in reopened if row['label'] == spec['actorLabel']]
        if matching:
            if len(matching) != 1:
                raise RuntimeError('Reopened enclosure actor count is %d' % len(matching))
            placed = matching[0]['actor']
            # NUMERIC readback of the actor's own maths, not a screenshot: the four outer
            # faces it computes must equal the four this script computed offline.
            clearances = placed.get_measured_clearances_amot()
            readback['actor'] = dict(
                label=matching[0]['label'], folder=matching[0]['folder'],
                worldBoundsCm=matching[0]['bounds'],
                measuredClearancesAmot=dict(west=float(clearances.x), north=float(clearances.y),
                                            east=float(clearances.z), south=float(clearances.w)),
                sideMetresAtProjectAmah=float(
                    placed.get_precinct_side_metres_under_amah('project')),
                sideMetresAtBookAmah=float(placed.get_precinct_side_metres_under_amah('naeh')),
                unknownAmahKeyReturnsZero=float(
                    placed.get_precinct_side_metres_under_amah('no-such-opinion')),
                modernBuildingsInsideByActor=int(placed.count_modern_buildings_inside()))
            expected = offline['clearancesAmot']
            worst = max(abs(readback['actor']['measuredClearancesAmot'][k] - float(expected[k]))
                        for k in ('west', 'north', 'east', 'south'))
            readback['actor']['clearanceAgreementErrorAmot'] = worst
            if worst > 1e-6:
                raise RuntimeError('The placed actor measures different clearances (%g amot) '
                                   'than this script computed offline' % worst)
            if readback['actor']['unknownAmahKeyReturnsZero'] != 0.0:
                raise RuntimeError('An unknown amah key returned a non-zero side; the lookup is '
                                   'silently defaulting')
        run.receipt['reopenedReadback'] = readback
        run.receipt['status'] = ('enclosure_saved_reopened_visual_acceptance_pending'
                                 if readback['actor']
                                 else 'meshes_only_saved_actor_omitted_rebuild_required')
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
    return 'release_enclosure.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    initial_state = 'modern'
    count_only = False
    for token in command_line.split():
        if token.startswith('-enclosurestate='):
            candidate = token.split('=', 1)[1].strip('"')
            if candidate not in ('modern', 'overlay', 'yechezkel'):
                raise RuntimeError('Unknown -EnclosureState=' + candidate)
            initial_state = candidate
        elif token.startswith('-enclosurecountonly='):
            count_only = token.split('=', 1)[1].strip('"') not in ('0', 'false', '')
    try:
        receipt = place(load_target=True, initial_state=initial_state, count_only=count_only)
        ue.log('release_enclosure: %s; buildings inside %s; false positives avoided %s'
               % (receipt['status'],
                  (receipt.get('selection') or {}).get('insideActorCount'),
                  (receipt.get('selectionWithoutExclusions') or {}).get('falsePositivesAvoided')))
    except Exception as error:
        ue.log_error('release_enclosure failed: ' + repr(error))
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

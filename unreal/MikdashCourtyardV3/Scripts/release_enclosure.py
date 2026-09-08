"""Guarded native import and placement of EnclosureV2 - the Yechezkel precinct, default view.

Imports the five module meshes written by Scripts/create_enclosure.py --export and places ONE
AMikdashEnclosure actor into a target map, opening in YECHEZKEL: the 3000-amah precinct built
exactly as Yechezkel 42:15-20 states it, following the terrain, with the modern buildings
inside it hidden by visibility. That actor builds the whole ring as instances at run time, so
this script adds a handful of assets and a single actor, not a wall, and it never hides,
deletes or edits a building.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_enclosure.py"
      -unattended -nullrhi
      -EnclosureTarget=Main50
      -abslog="C:/Mikdash/Working-5.8/Release-Enclosure-Main50-01.log"

  ... the same with -EnclosureTarget=Candidate48 and its own -abslog for the isolated map.

Optional switches, read from the engine command line:
  -EnclosureTarget=Main50|Candidate48         which map (default Main50). Each target has its own
                                              precinct receipt, amah, court half-extent and
                                              hide set; see the spec.
  -EnclosureState=yechezkel|modern|overlay    the state the placed actor opens in (default
                                              yechezkel, by decision)
  -EnclosureCountOnly=1                       run every guard and every measurement, write the
                                              receipt, and place NOTHING.
  -EnclosureAllowMissingHideLabels=1          place even if some receipt labels are absent from
                                              the loaded map (they are listed; default refuse).

Run this module outside the editor and it prints offline_check() for both targets as JSON and
exits; nothing native happens and nothing is written.

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
by EnclosureMath.h's rule at the target's amah, and the result is checked against the target's
precinct receipt (and, on the main map, against EnclosureV1's shipped faces).

WHAT IS BAKED ONTO THE ACTOR, AND WHY OFFLINE
---------------------------------------------
  * The GROUND PROFILE (601 stations a side, highest/lowest ground under the footprint), from
    the OSM terrain grid, the frozen level grid and the FutureMountV1 tile receipts. Baked so
    the wall meets the same ground in a commandlet, in PIE and in a cooked build; no trace.
  * The HIDE SET, as actor labels AND as the mesh asset names those actors render, computed
    from the frozen OSM partition and the facade manifest. The runtime hides exactly that set.
    This script proves every label exists exactly once in the loaded map and that its mesh is
    the mapped SM_* name before baking either list.

THE TRAP THAT COST THIS PROJECT A DAY, AND HOW IT IS AVOIDED HERE
-----------------------------------------------------------------
Counting "which modern buildings fall inside the precinct" by testing actor AABBs against the
square returns a hundred per cent false positives unless the 256 terrain tiles and the hollow
Boolean unions are kept out BY NAME AND ASSET PATH before any bounds test runs. They still
are, the exclusions are still counted and named in the receipt, and the AABB-based count is
still recorded - but it is now a CROSS-CHECK against the exact list, not the selection.

SAFETY MODEL (identical in shape to Scripts/release_place_assets.py)
  * Refuses to run with the wrong project directory, a game world active, dirty packages, or a
    loaded world that is not the target map.
  * Copies the target .umap and any One-File-Per-Actor folders to a checkpoint before any
    mutation, and verifies the copy by hash.
  * Refuses to place if an EnclosureV2 release actor already exists.
  * Saves only if something was actually placed, then RELOADS the map and reads back the
    placed actor numerically: its faces, clearances, per-side plinth Z ranges, instance counts,
    hide-list resolution and fingerprint - via MeasureWithoutHiding(), which touches no
    building's visibility. Nothing is saved after the readback.
  * The receipt JSON is written at start and again in `finally`, so a failure preserves
    partial state with evidence rather than losing it.
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
HEADER = ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/EnclosureMath.h'
DEFAULT_TARGET = 'Main50'
STATES = ('yechezkel', 'modern', 'overlay')
STATE_ENUM = {'modern': 0, 'yechezkel': 1, 'overlay': 2}   # EMikdashPrecinctState order


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
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    if spec.get('defaultState') not in STATES:
        raise RuntimeError('Spec defaultState must be one of %r' % (STATES,))
    for name, target in spec['targets'].items():
        if disk_path(target['map'], 'umap') != ROOT / target['mapFile']:
            raise RuntimeError('Target %s map and mapFile disagree' % name)
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
    """World AABBs of a hollow union's constituent boxes (legacy 50 cm manifest frame)."""
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


def mesh_name_for_label(spec, label):
    """RELEASE_OldCityFacades_Grid_X -> SM_OldCityFacades_Grid_X, etc. None when no rule applies."""
    for prefix, mesh_prefix in spec['hideListMeshNameRule'].items():
        if label.startswith(prefix):
            return mesh_prefix + label[len(prefix):]
    return None


def fnv1a_labels(labels):
    """Mirror of create_enclosure.hide_set() and AMikdashEnclosure::GetHideSetFingerprint():
    FNV-1a over the UTF-8 of the byte-order-sorted labels, concatenated."""
    fingerprint = 1469598103934665603
    for label in sorted(labels):
        for byte in label.encode('utf-8'):
            fingerprint ^= byte
            fingerprint = (fingerprint * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return '%016x' % fingerprint


# --------------------------------------------------------------------------
# The square, and the proof that the centre is where the receipts say
# --------------------------------------------------------------------------

def temple_centre_from_receipts(spec):
    """Prove the measured court centre rather than assume it (legacy 50 cm manifest)."""
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
    half = float(spec['targets']['Main50']['courtPlatformHalfExtentCm'])
    worst = max(abs(bounds['min'][0] + half), abs(bounds['max'][0] - half),
                abs(bounds['min'][1] + half), abs(bounds['max'][1] - half))
    if worst > float(spec['verification']['boundsToleranceCm']):
        raise RuntimeError('%s bounds are no longer +-%g about the origin (worst %.4f cm)'
                           % (platform_name, half, worst))

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


def square_from(centre_xy, constants, cm_per_amah, half_court):
    side = constants['PrecinctSideAmot'] * cm_per_amah
    west = centre_xy[0] - half_court - constants['BookClearWestAmot'] * cm_per_amah
    north = centre_xy[1] - half_court - constants['BookClearNorthAmot'] * cm_per_amah
    return dict(west=west, north=north, east=west + side, south=north + side, sideCm=side,
                centreCm=[west + side / 2.0, north + side / 2.0])


# --------------------------------------------------------------------------
# Offline check
# --------------------------------------------------------------------------

def load_precinct_receipt(spec, target_name):
    target = spec['targets'][target_name]
    path = ROOT / target['precinctReceipt']
    if not path.exists():
        raise RuntimeError('Run Scripts/create_enclosure.py --export first; %s is absent' % path)
    receipt = json.loads(path.read_text(encoding='utf-8-sig'))
    if receipt.get('target') != target_name:
        raise RuntimeError('%s is for target %r, not %s' % (path.name, receipt.get('target'), target_name))
    generator = ROOT / spec['generatorScript']
    if receipt.get('generatorSha256') != sha256_of(generator):
        raise RuntimeError('%s was written by a different create_enclosure.py (receipt %s, current %s); '
                           're-run --export so the ground profile and hide set match the generator'
                           % (path.name, str(receipt.get('generatorSha256'))[:12], sha256_of(generator)[:12]))
    if receipt.get('enclosureMathSha256') != sha256_of(HEADER):
        raise RuntimeError('%s was written against a different EnclosureMath.h; re-run --export' % path.name)
    return receipt, path


def validate_ground_profile(profile):
    if not profile:
        raise RuntimeError('precinct receipt carries no ground profile; the wall would sit on the level plane')
    steps = int(profile['stepsPerSide'])
    stations = steps + 1
    high, low = profile['highZcm'], profile['lowZcm']
    if steps <= 0 or len(high) != 4 * stations or len(low) != 4 * stations:
        raise RuntimeError('ground profile malformed: %d steps, %d high, %d low' % (steps, len(high), len(low)))
    for h, l in zip(high, low):
        if not (math.isfinite(h) and math.isfinite(l)) or l > h + 1e-6:
            raise RuntimeError('ground profile has a non-finite or inverted station')
    return dict(stepsPerSide=steps, stationsPerSide=stations,
                lowestCm=min(low), highestCm=max(high),
                sides=profile['sides'], sourceUse=profile['sourceUse'])


def validate_hide_set(spec, hide):
    labels = hide.get('labels') or []
    if not labels:
        raise RuntimeError('precinct receipt hide set is empty')
    if hide.get('policy') != spec['straddlingCellPolicy']:
        raise RuntimeError('receipt hide policy %r differs from spec %r' % (hide.get('policy'), spec['straddlingCellPolicy']))
    if fnv1a_labels(labels) != hide.get('labelFingerprintFnv1a'):
        raise RuntimeError('hide set fingerprint does not reproduce from its own labels')
    bad = [l for l in labels if not any(l.startswith(p) for p in spec['modernBuildingLabelPrefixes'])]
    if bad:
        raise RuntimeError('hide set carries labels outside the modern-building prefixes: %r' % bad[:5])
    excluded = [l for l in labels if any(l.startswith(p) for p in spec['excludedLabelPrefixes'])]
    if excluded:
        raise RuntimeError('hide set carries excluded labels: %r' % excluded[:5])
    meshes = [mesh_name_for_label(spec, l) for l in labels]
    if any(m is None for m in meshes):
        raise RuntimeError('a hide label has no mesh-name rule')
    return labels, meshes


def offline_check(spec=None, target_name=DEFAULT_TARGET):
    """Everything that can be established without the engine. Runs first, every time; a
    failure here is a refusal before any package is opened."""
    spec = spec or load_spec()
    if target_name not in spec['targets']:
        raise RuntimeError('Unknown target %r; expected one of %r' % (target_name, sorted(spec['targets'])))
    target = spec['targets'][target_name]
    constants = header_constants()
    centre, centre_evidence = temple_centre_from_receipts(spec)
    a = float(target['cmPerAmah'])
    half = float(target['courtPlatformHalfExtentCm'])
    if abs(half - constants['CourtPlatformHalfExtentUnrealCm'] * a / constants['ProjectCmPerAmah']) > 1e-6:
        raise RuntimeError('target %s court half-extent %g is not 8100 x (%g / 50)' % (target_name, half, a))
    sq = square_from(centre, constants, a, half)

    receipt, receipt_path = load_precinct_receipt(spec, target_name)
    faces = receipt['square']['outerFacesCm']
    worst = max(abs(faces['xWest'] - sq['west']), abs(faces['xEast'] - sq['east']),
                abs(faces['yNorth'] - sq['north']), abs(faces['ySouth'] - sq['south']))
    if worst > 1e-6:
        raise RuntimeError('%s square differs from the header rule by %g cm' % (receipt_path.name, worst))
    if abs(float(receipt['cmPerAmah']) - a) > 1e-9:
        raise RuntimeError('%s amah %g differs from the spec target %g' % (receipt_path.name, receipt['cmPerAmah'], a))

    manifest_path = ROOT / spec['geometryManifest']
    if not manifest_path.exists():
        raise RuntimeError('Run Scripts/create_enclosure.py --export first; %s is absent' % manifest_path)
    geometry = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if geometry.get('generatorSha256') != receipt['generatorSha256']:
        raise RuntimeError('geometry-manifest.json and the precinct receipt come from different exports')

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
        raise RuntimeError('OBJ set does not match the manifest; missing=%r changed=%r' % (missing, mismatched))
    wanted_roles = {'SM_EnclosureV2_WallSegment', 'SM_EnclosureV2_Gate', 'SM_EnclosureV2_Corner',
                    'SM_EnclosureV2_OverlaySlab', 'SM_EnclosureV2_Foundation'}
    if {r['name'] for r in geometry['meshes']} != wanted_roles:
        raise RuntimeError('geometry-manifest.json does not carry exactly the five modules')

    design_agreement = 'not applicable to this target'
    if target.get('checkAgainstEnclosureV1Design'):
        existing_design = ROOT / spec['existingEnclosureDesign']
        design_agreement = 'enclosure-design.json absent'
        if existing_design.exists():
            design = json.loads(existing_design.read_text(encoding='utf-8-sig'))
            existing_faces = design['enclosure']['outerFacesCm']
            error = max(abs(existing_faces['xWest'] - sq['west']), abs(existing_faces['xEast'] - sq['east']),
                        abs(existing_faces['yNorth'] - sq['north']), abs(existing_faces['ySouth'] - sq['south']))
            if error > 1e-6:
                raise RuntimeError('EnclosureV2 square differs from the shipped EnclosureV1 design by %g cm; '
                                   'one of the two is wrong and this script will not guess which' % error)
            design_agreement = 'identical to EnclosureV1 on all four outer faces'

    ground = validate_ground_profile(receipt.get('groundProfile'))
    labels, meshes = validate_hide_set(spec, receipt['modernCity']['hideSet'])

    return dict(
        status='offline_checks_passed',
        target=target_name, map=target['map'], cmPerAmah=a, courtPlatformHalfExtentCm=half,
        specSha256=sha256_of(SPEC_PATH),
        enclosureMathSha256=sha256_of(HEADER),
        generatorSha256=geometry['generatorSha256'],
        precinctReceipt=str(receipt_path), precinctReceiptSha256=sha256_of(receipt_path),
        templeCentreEvidence=centre_evidence,
        precinctCentreCm=sq['centreCm'],
        outerFacesCm={k: sq[k] for k in ('west', 'east', 'north', 'south')},
        sideAmot=constants['PrecinctSideAmot'],
        sideReeds=constants['PrecinctSideAmot'] / constants['AmotPerReed'],
        sideMetresAtThisMapsAmah=sq['sideCm'] / 100.0,
        sideMetresUnderAmahOpinions={
            'naeh-48-and-the-books-own': constants['PrecinctSideAmot'] * 48.0 / 100.0,
            'project-50': constants['PrecinctSideAmot'] * 50.0 / 100.0,
            'feinstein-54': constants['PrecinctSideAmot'] * 54.0 / 100.0,
            'chazon-ish-57.6': constants['PrecinctSideAmot'] * 57.6 / 100.0,
            'chazon-ish-stringent-58': constants['PrecinctSideAmot'] * 58.0 / 100.0,
        },
        clearancesAmot=receipt['clearancesAmot'],
        gates=receipt['gates'],
        wallPlan=receipt['wallPlan'],
        groundProfile=ground,
        groundingsPerSide=(receipt.get('groundings') or {}).get('perSide'),
        gateThresholds=(receipt.get('groundings') or {}).get('gates'),
        hideSet=dict(policy=receipt['modernCity']['hideSet']['policy'],
                     counts=receipt['modernCity']['hideSet']['counts'],
                     collateral=receipt['modernCity']['hideSet']['collateral'],
                     labelFingerprintFnv1a=receipt['modernCity']['hideSet']['labelFingerprintFnv1a'],
                     labels=labels, meshNames=meshes),
        osmBuildingsInsideByCentroid=(receipt['modernCity'].get('exact') or {}).get('buildingsInside'),
        agreementWithEnclosureV1=design_agreement,
        objFiles=[dict(file=r['file'], sha256=r['sha256'], triangles=r['triangles']) for r in geometry['meshes']])


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
    def __init__(self, ue, spec, target_name):
        self.ue = ue
        self.spec = spec
        self.target_name = target_name
        self.target = spec['targets'][target_name]
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
        """One pass over the level, classifying every actor. BY ASSET PATH first and by label
        second: labels are duplicable and a duplicate label is exactly how a terrain tile
        could sneak into the building set; an asset path is not."""
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

    def resolve_hide_list(self, rows, labels):
        """Every receipt label must exist exactly once and render the mapped SM_* mesh."""
        spec = self.spec
        by_label = {}
        for row in rows:
            by_label.setdefault(row['label'], []).append(row)
        missing, duplicated, mesh_mismatch, resolved = [], [], [], []
        for label in labels:
            hits = by_label.get(label, [])
            if not hits:
                missing.append(label)
                continue
            if len(hits) > 1:
                duplicated.append(dict(label=label, count=len(hits), names=[h['name'] for h in hits]))
                continue
            wanted_mesh = mesh_name_for_label(spec, label)
            actual = [m.split('.')[-1] for m in hits[0]['meshes']]
            if actual != [wanted_mesh]:
                mesh_mismatch.append(dict(label=label, expectedMesh=wanted_mesh, actualMeshes=actual))
                continue
            resolved.append(dict(label=label, name=hits[0]['name'], mesh=wanted_mesh))
        return dict(requested=len(labels), resolved=len(resolved), missing=missing, duplicated=duplicated,
                    meshMismatch=mesh_mismatch, resolvedLabels=[r['label'] for r in resolved],
                    resolvedMeshNames=[r['mesh'] for r in resolved],
                    resolvedFingerprintFnv1a=fnv1a_labels([r['label'] for r in resolved]))

    def classify_by_bounds(self, rows, sq, hide_labels):
        """The AABB-centroid cross-check: every exclusion named, and the exact list compared
        against what a bounds test alone would have selected."""
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
        hide = set(hide_labels)
        return dict(
            consideredActors=len(considered),
            excludedActors=len(excluded),
            excludedSample=sorted(e['label'] for e in excluded)[:40],
            excludedLongestSideCm=max([e['longestSideCm'] for e in excluded] or [0.0]),
            aabbCentroidInsideCount=len(inside), aabbStraddlingCount=len(straddling), aabbOutsideCount=len(outside),
            inExactListButAabbCentroidOutside=sorted(hide - set(inside)),
            aabbCentroidInsideButNotInExactList=sorted(set(inside) - hide),
            note=('Cross-check only. The selection is the exact per-actor list from the precinct receipt; '
                  'this is what a bounds-centroid rule over 100 m cell actors would have chosen instead, '
                  'and the two differences are listed.'))

    def union_envelope_check(self, rows):
        """Prove the hollow unions would have been false positives, and that decomposing them
        is what removes the false positive."""
        spec = self.spec
        manifest = json.loads((ROOT / spec['architectureManifest']).read_text(encoding='utf-8-sig'))
        by_label = {}
        for entry in manifest.get('meshes', []):
            if entry.get('semantic') == 'union':
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
                boxes, error = verify_union_decomposition(entry, float(spec['verification']['boundsToleranceCm']))
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
                raise OmissionError('Mesh already exists and reimport is off: ' + asset_path, {'asset': asset_path})
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
                raise OmissionError('Import produced no asset for ' + asset_path, {'obj': record['file']})
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
                    {'asset': asset_path, 'imported': actual, 'canonical': record['canonicalBoundsCm']})
            triangles = int(mesh.get_num_triangles(0))
            if triangles != record['triangles']:
                raise OmissionError('Imported triangle count %d != %d for %s'
                                    % (triangles, record['triangles'], record['name']), {'asset': asset_path})
            imported.append(dict(asset=asset_path, obj=record['file'], triangles=triangles,
                                 importedBoundsCm=actual, boundsErrorCm=round(error, 6),
                                 replacedExisting=bool(existing)))
        return imported

    # -- place ------------------------------------------------------------

    def place_actor(self, imported, initial_state, offline, resolution):
        ue = self.ue
        spec = self.spec
        actor_class = getattr(ue, 'MikdashEnclosure', None)
        if actor_class is None:
            raise OmissionError(
                'AMikdashEnclosure is not available to Python. The plugin has not been rebuilt '
                'since Private/MikdashEnclosure.cpp changed, so the class does not exist in this '
                'editor. The meshes above are imported and reviewable; rebuild the '
                'MikdashCourtyardV3Editor target and re-run to place the actor.',
                {'importedMeshes': [entry['asset'] for entry in imported]})
        actor = self.actors.spawn_actor_from_class(actor_class, ue.Vector(0.0, 0.0, 0.0), ue.Rotator(0.0, 0.0, 0.0))
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
        actor.set_editor_property('FoundationModuleMesh', mesh_for('SM_EnclosureV2_Foundation'))
        actor.set_editor_property('OverlayQuadMesh', mesh_for('SM_EnclosureV2_OverlaySlab'))
        actor.set_editor_property('WorldCmPerAmah', float(offline['cmPerAmah']))
        actor.set_editor_property('CourtCentreUnrealCm', ue.Vector2D(0.0, 0.0))
        actor.set_editor_property('CourtPlatformHalfExtentCm', float(offline['courtPlatformHalfExtentCm']))
        actor.set_editor_property('ModernBuildingLabelPrefixes', list(spec['modernBuildingLabelPrefixes']))
        actor.set_editor_property('ExcludedLabelPrefixes', list(spec['excludedLabelPrefixes']))
        # The enum object when the reflected type is available (its members are the UENUM
        # entries upper-cased), the integer otherwise; both are accepted by set_editor_property.
        state_value = STATE_ENUM[initial_state]
        enum_type = getattr(ue, 'MikdashPrecinctState', None)
        if enum_type is not None and hasattr(enum_type, initial_state.upper()):
            state_value = getattr(enum_type, initial_state.upper())
        actor.set_editor_property('InitialState', state_value)

        # The ground profile, verbatim from the receipt.
        receipt = json.loads(Path(offline['precinctReceipt']).read_text(encoding='utf-8-sig'))
        profile = receipt['groundProfile']
        actor.set_editor_property('GroundProfileStepsPerSide', int(profile['stepsPerSide']))
        actor.set_editor_property('GroundProfileHighZCm', [float(v) for v in profile['highZcm']])
        actor.set_editor_property('GroundProfileLowZCm', [float(v) for v in profile['lowZcm']])

        # The hide set, as the labels that RESOLVED in this map and the meshes they render.
        actor.set_editor_property('ExplicitHideLabels', list(resolution['resolvedLabels']))
        actor.set_editor_property('ExplicitHideMeshNames', list(resolution['resolvedMeshNames']))

        materials = {}
        for key, prop in (('wallMaterial', 'WallMaterial'), ('overlayMaterial', 'OverlayMaterial')):
            path = spec.get(key)
            if not path:
                materials[key] = 'not set (spec null)'
                continue
            if not ue.EditorAssetLibrary.does_asset_exist(path):
                materials[key] = 'OMITTED: asset absent ' + path
                continue
            material = ue.EditorAssetLibrary.load_asset(path)
            if material is None:
                materials[key] = 'OMITTED: could not load ' + path
                continue
            actor.set_editor_property(prop, material)
            materials[key] = path
        return actor, materials


def readback_actor(ue, placed, offline, spec):
    """NUMERIC readback of the actor's own maths in the editor world, without hiding anything."""
    placed.measure_without_hiding()
    tolerance = float(spec['verification']['groundZAgreementToleranceCm'])
    clearances = placed.get_measured_clearances_amot()
    faces = placed.get_outer_faces_cm()
    found, missing, duplicated = placed.get_hide_list_resolution()
    counts = placed.get_instance_counts()
    sides = []
    names = ['north', 'east', 'south', 'west']
    expected_sides = {s['name']: s for s in (offline.get('groundingsPerSide') or [])}
    worst_z = 0.0
    for side in range(4):
        z_range = placed.get_wall_base_z_range_cm(side)
        expected = expected_sides.get(names[side])
        row = dict(side=names[side], plinthZminCm=float(z_range.x), plinthZmaxCm=float(z_range.y),
                   deepestFoundationCm=float(placed.get_deepest_foundation_cm(side)))
        if expected:
            row['receiptPlinthZminCm'] = expected['baseZminCm']
            row['receiptPlinthZmaxCm'] = expected['baseZmaxCm']
            worst_z = max(worst_z, abs(row['plinthZminCm'] - expected['baseZminCm']),
                          abs(row['plinthZmaxCm'] - expected['baseZmaxCm']))
        sides.append(row)
    result = dict(
        measuredClearancesAmot=dict(west=float(clearances.x), north=float(clearances.y),
                                    east=float(clearances.z), south=float(clearances.w)),
        outerFacesCm=dict(west=float(faces.x), north=float(faces.y), east=float(faces.z), south=float(faces.w)),
        sideMetresAtProjectAmah=float(placed.get_precinct_side_metres_under_amah('project')),
        sideMetresAtBookAmah=float(placed.get_precinct_side_metres_under_amah('naeh')),
        unknownAmahKeyReturnsZero=float(placed.get_precinct_side_metres_under_amah('no-such-opinion')),
        groundProfileStatus=str(placed.get_ground_profile_status()),
        instanceCounts=dict(wall=int(counts.x), gate=int(counts.y), corner=int(counts.z),
                            foundation=int(counts.w), overlay=int(placed.get_overlay_instance_count())),
        perSide=sides, worstPlinthZDisagreementCm=worst_z,
        hideListResolution=dict(found=int(found), missing=int(missing), duplicated=int(duplicated)),
        hideSetFingerprintFnv1a=str(placed.get_hide_set_fingerprint()),
        modernBuildingsThatWouldBeHidden=int(placed.count_modern_buildings_inside()))
    # The editor world is left exactly as found: nothing was hidden, but be explicit.
    placed.restore_all_modern_buildings()

    expected_clear = offline['clearancesAmot']
    worst = max(abs(result['measuredClearancesAmot'][k] - float(expected_clear[k])) for k in ('west', 'north', 'east', 'south'))
    result['clearanceAgreementErrorAmot'] = worst
    if worst > float(spec['verification']['clearanceAgreementToleranceAmot']):
        raise RuntimeError('The placed actor measures different clearances (%g amot) than the receipt' % worst)
    exp_faces = offline['outerFacesCm']
    worst_face = max(abs(result['outerFacesCm'][k] - exp_faces[k]) for k in ('west', 'north', 'east', 'south'))
    if worst_face > 1e-3:
        raise RuntimeError('The placed actor computes different outer faces (%g cm) than the receipt' % worst_face)
    if result['unknownAmahKeyReturnsZero'] != 0.0:
        raise RuntimeError('An unknown amah key returned a non-zero side; the lookup is silently defaulting')
    if result['groundProfileStatus'] != 'profile':
        raise RuntimeError('The placed actor did not accept the ground profile (status %s)' % result['groundProfileStatus'])
    if worst_z > tolerance:
        raise RuntimeError('Plinth Z ranges differ from the receipt by %.2f cm' % worst_z)
    plan = offline['wallPlan']
    if result['instanceCounts'] != dict(wall=plan['wallInstances'], gate=plan['gateInstances'],
                                        corner=plan['cornerInstances'], foundation=plan['foundationInstances'],
                                        overlay=plan['overlayInstances']):
        raise RuntimeError('Instance counts %r differ from the plan %r' % (result['instanceCounts'], plan))
    return result


def place(target_name=DEFAULT_TARGET, load_target=True, initial_state=None, count_only=False,
          allow_missing_hide_labels=False):
    """Guarded import and placement. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    spec = load_spec()
    initial_state = initial_state or spec['defaultState']
    if initial_state not in STATES:
        raise RuntimeError('Unknown state ' + initial_state)
    offline = offline_check(spec, target_name)
    target = spec['targets'][target_name]
    target_map = target['map']
    sq = dict(west=offline['outerFacesCm']['west'], east=offline['outerFacesCm']['east'],
              north=offline['outerFacesCm']['north'], south=offline['outerFacesCm']['south'])

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    run = Placement(ue, spec, target_name)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target and not run.levels.load_level(target_map):
        raise RuntimeError('load_level failed for ' + target_map)
    world = run.editor.get_editor_world()
    loaded = world.get_outermost().get_name()
    if loaded != target_map:
        raise RuntimeError('Loaded world %s is not the target map %s' % (loaded, target_map))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
       ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed placement')

    map_file = disk_path(target_map, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in target['protectedMaps']
                 if disk_path(m, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    run.receipt_path = receipt_folder / ('%s%s-%s.json' % (spec['receiptPrefix'], target_name, stamp))
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))

    checkpoint = None
    external_copied = []
    if not count_only:
        checkpoint = Path(spec['checkpointRoot']) / ('%s%s-%s' % (spec['checkpointPrefix'], target_name, stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / target_map[6:]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / target_map[6:])
                external_copied.append(str(external))

    run.receipt = {
        'status': 'measurement_only_started' if count_only else 'checkpointed_placement_started',
        'stamp': stamp, 'target': target_name, 'map': target_map, 'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == target.get('lastKnownMapSha256'),
        'checkpoint': str(checkpoint) if checkpoint else None,
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'scriptSha256': sha256_of(Path(__file__)),
        'offlineCheck': {k: v for k, v in offline.items() if k != 'hideSet'},
        'hideSetSummary': {k: v for k, v in offline['hideSet'].items() if k not in ('labels', 'meshNames')},
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'countOnly': bool(count_only),
        'initialState': initial_state,
        'placed': {}, 'omissions': {}, 'errors': [], 'mapSaved': False,
        'limitations': [
            'Placement is geometric only. No visual, halachic, walking or packaged acceptance is established by this run.',
            'The wall follows the BAKED ground profile from the precinct receipt; if the terrain tiles change, '
            're-export and re-place.',
            'Foundations/substructure and gate positions along each wall are AUTHORED. Only the square, the wall '
            'section, the gate count and the 10 x 50 opening are sourced.',
            'The hide set is exact per ACTOR; cells the wall line cuts are hidden whole under the recorded policy '
            '(collateral in the precinct receipt). Nothing is deleted; MODERN restores every actor.',
            'The 3000-amah reading is one side of a live dispute. Middot 2:1\'s 500-amah Har HaBayit is offered as '
            'the other and is not presented as refuted; see SourceAssets/enclosure-review/sources.md.',
        ],
    }
    run.write_receipt()

    saved = False
    try:
        rows = run.survey()
        run.receipt['actorCountBefore'] = len(rows)
        existing = [row['label'] for row in rows if row['label'].startswith(spec['actorLabel'])]
        if existing and not count_only:
            raise RuntimeError('An EnclosureV2 release actor already exists: %r' % existing)
        run.receipt['preExistingEnclosureActors'] = existing

        run.receipt['unionEnvelopeCheck'] = run.union_envelope_check(rows)
        resolution = run.resolve_hide_list(rows, offline['hideSet']['labels'])
        run.receipt['hideListResolution'] = {k: v for k, v in resolution.items()
                                             if k not in ('resolvedLabels', 'resolvedMeshNames')}
        run.receipt['boundsCrossCheck'] = run.classify_by_bounds(rows, sq, resolution['resolvedLabels'])
        problems = len(resolution['missing']) + len(resolution['duplicated']) + len(resolution['meshMismatch'])
        if problems and not allow_missing_hide_labels:
            raise RuntimeError('%d hide-list labels did not resolve in %s (missing %d, duplicated %d, mesh mismatch %d); '
                               'pass -EnclosureAllowMissingHideLabels=1 to place anyway'
                               % (problems, target_name, len(resolution['missing']), len(resolution['duplicated']),
                                  len(resolution['meshMismatch'])))
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
            run.receipt['omissions']['meshes'] = {'reason': str(omission), 'evidence': omission.evidence}
            run.receipt['status'] = 'nothing_placed_map_unchanged'
            return run.receipt

        actor = None
        try:
            actor, materials = run.place_actor(imported, initial_state, offline, resolution)
            run.receipt['placed']['actor'] = dict(label=spec['actorLabel'], folder=spec['folder'],
                                                  initialState=initial_state, materials=materials,
                                                  hideLabelsBaked=resolution['resolved'],
                                                  groundProfileStations=4 * offline['groundProfile']['stationsPerSide'])
        except OmissionError as omission:
            run.receipt['omissions']['actor'] = {'reason': str(omission), 'evidence': omission.evidence}

        if actor is None and not imported:
            run.receipt['status'] = 'nothing_placed_map_unchanged'
            return run.receipt

        if not run.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()

        if not run.levels.load_level(target_map):
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
            readback['meshes'].append(dict(asset=entry['asset'], triangles=int(mesh.get_num_triangles(0)),
                                           worldBoundsCm=actual,
                                           boundsErrorCm=box_error(actual, entry['importedBoundsCm'])))
        matching = [row for row in reopened if row['label'] == spec['actorLabel']]
        if matching:
            if len(matching) != 1:
                raise RuntimeError('Reopened enclosure actor count is %d' % len(matching))
            placed = matching[0]['actor']
            readback['actor'] = readback_actor(ue, placed, offline, spec)
            readback['actor']['label'] = matching[0]['label']
            readback['actor']['folder'] = matching[0]['folder']
            expected_fp = resolution['resolvedFingerprintFnv1a']
            readback['actor']['hideSetFingerprintMatchesResolvedList'] = \
                readback['actor']['hideSetFingerprintFnv1a'] == expected_fp
            readback['actor']['hideSetFingerprintMatchesReceipt'] = \
                readback['actor']['hideSetFingerprintFnv1a'] == offline['hideSet']['labelFingerprintFnv1a']
            if not readback['actor']['hideSetFingerprintMatchesResolvedList']:
                raise RuntimeError('The placed actor resolves a different hide set (%s) than this script did (%s)'
                                   % (readback['actor']['hideSetFingerprintFnv1a'], expected_fp))
            if readback['actor']['hideListResolution']['missing'] or readback['actor']['hideListResolution']['duplicated']:
                if not allow_missing_hide_labels:
                    raise RuntimeError('Reopened actor reports hide labels missing/duplicated: %r'
                                       % readback['actor']['hideListResolution'])
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
    command_line = ue.SystemLibrary.get_command_line()
    target_name = DEFAULT_TARGET
    initial_state = None
    count_only = False
    allow_missing = False
    for token in command_line.split():
        lowered = token.lower()
        if lowered.startswith('-enclosuretarget='):
            candidate = token.split('=', 1)[1].strip('"')
            names = {'main50': 'Main50', 'candidate48': 'Candidate48'}
            if candidate.lower() not in names:
                raise RuntimeError('Unknown -EnclosureTarget=' + candidate)
            target_name = names[candidate.lower()]
        elif lowered.startswith('-enclosurestate='):
            candidate = lowered.split('=', 1)[1].strip('"')
            if candidate not in STATES:
                raise RuntimeError('Unknown -EnclosureState=' + candidate)
            initial_state = candidate
        elif lowered.startswith('-enclosurecountonly='):
            count_only = lowered.split('=', 1)[1].strip('"') not in ('0', 'false', '')
        elif lowered.startswith('-enclosureallowmissinghidelabels='):
            allow_missing = lowered.split('=', 1)[1].strip('"') not in ('0', 'false', '')
    try:
        receipt = place(target_name=target_name, load_target=True, initial_state=initial_state,
                        count_only=count_only, allow_missing_hide_labels=allow_missing)
        ue.log('release_enclosure[%s]: %s; hide labels resolved %s; state %s'
               % (target_name, receipt['status'],
                  (receipt.get('hideListResolution') or {}).get('resolved'), receipt.get('initialState')))
    except Exception as error:
        ue.log_error('release_enclosure failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line.lower() and '-run=pythonscript' not in command_line.lower():
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        spec = load_spec()
        out = {}
        for name in spec['targets']:
            result = offline_check(spec, name)
            result['hideSet'] = {k: v for k, v in result['hideSet'].items() if k not in ('labels', 'meshNames')}
            out[name] = result
        print(json.dumps(out, indent=2))
elif _invoked_as_native_script():
    _main()

"""Guarded import and placement of GateSecurityV1 at the real gate approaches.

Places a modern security checkpoint on the deck outside the first riser of each of the three
gates that actually exist in this model -- East, North and South -- in
/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough. Every number comes from
Scripts/release_gate_security.spec.json so a human can review the plan before running it.

WHAT IS ASSERTED AND WHAT IS ONLY DEPICTED
------------------------------------------
SourceAssets/security-review/sources.md is the source table and it governs. In one line each:

  * ASSERTED, as halacha, on the sign faces with their citation printed on the sign:
    entering Har HaBayit in shoes is prohibited; the Mount may not be used as a shortcut;
    one may not spit there.  Mishnah Berachos 9:5; Rambam, Hilchos Beis HaBechira 7:2.
  * MODERN STAGING, asserted of nothing but today's Jerusalem: the metal detector arches, the
    bag scanner, the stanchions, the guard booth and the rule about telephones. Modelled on the
    entrance procedure at the Har HaBayit and Kotel plaza approaches TODAY. No classical source
    describes anything of the kind and nothing here is a claim about the Temple or its courts.
    The sign faces say so themselves, not only this file.
  * DEPICTED, NOT ASSERTED: every dimension, material and position of every object.

WHERE THE GATE POSITIONS CAME FROM -- they are derived, not invented
--------------------------------------------------------------------
Offline, out of this project's own receipts, and then confirmed again at run time:

  * Units and axes: cm, X east, +Y south, Z up, measured court centre at the origin.
    SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json.
  * Gate geometry: SourceAssets/architecture-manifest.json expectedBoundsUnrealCm, cross-checked
    against SourceAssets/mount-access/GatewayV3/gateway-approach-audit.json, which also records
    that the deck Z at all three approaches is 0 and that there is NO WEST GATE
    ("NO_SOURCE_GATE_DO_NOT_INVENT_OPENING_OR_STAIRS"). Nothing is placed west.

Two traps, both recorded so they are not rediscovered the hard way:

  1. NO YAW IS RECORDED FOR ANY GATE ANYWHERE. Every gate record is axis-aligned with rotation
     [0,0,0]. The assembly yaw (E 180, N 90, S -90) is DERIVED from each gate's outward axis.
  2. get_actor_location() ON A MEASURED-ARCHITECTURE ACTOR RETURNS (0,0,0). World position is
     baked into the vertices and every such actor is spawned at the origin with an identity
     transform (architecture-manifest.json: spawnLocationUnrealCm [0,0,0],
     objectTransformIdentity true). So this script confirms each gate by reading the
     StaticMeshComponent WORLD BOUNDS of its first riser and its threshold, matched by
     STATIC MESH ASSET PATH -- labels are not unique (ten actors share the label
     'Outer N mount approach terrace'), asset paths are 1:1. A gate whose bounds do not match
     the offline numbers is OMITTED with numeric evidence rather than placed on a guess.

RUN ORDER
---------
  1. python Scripts/create_gate_security.py --export       (offline; writes the OBJs and PNGs)
  2. python Scripts/release_gate_security.py --write-spec  (offline; writes the .spec.json)
  3. python Scripts/release_gate_security.py               (offline; prints offline_check())
  4. the commandlet below                                  (native; imports, places, saves)

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_gate_security.py"
      -unattended -nullrhi -EnablePlugins=GeometryScripting
      -abslog="C:/Mikdash/Working-5.8/Gate-Security-01.log"

Optional switches (read from the engine command line):
  -GateSecurityGates=east,north      comma-separated subset of east,north,south.
  -GateSecurityImportOnly            import and material work only; no map mutation.
  -GateSecurityVerifyOnly            READ-ONLY: re-read every planned actor against the spec
                                     (mesh, pose, bounds, sign material, collision) and write
                                     a verify receipt. No checkpoint, no spawn, no save.
  -GateSecurityAllowUnverifiedWinding    place even if GeometryScripting is unavailable.

UE 5.8 pitfalls this script is written against
----------------------------------------------
  * MATERIAL SETTERS RETURN False EVEN ON SUCCESS. Nothing here trusts a setter's return value;
    every one is RECORDED and the pass/fail decision is always a READBACK of the assigned
    material, the texture parameter or the connected material input.
  * A STATIC-MOBILITY ACTOR DOES NOT DIRTY ITS PACKAGE ON A TRANSFORM CHANGE. So this script
    never moves an actor after spawning it: the final transform is passed to spawn_actor, and a
    pose that comes back wrong is destroyed and RE-SPAWNED, never nudged.
  * NANITE MAKES get_num_triangles(0) RETURN THE FALLBACK COUNT. build_nanite is False in the
    import settings and the receipt asserts nanite_settings.enabled is False before any triangle
    count is compared to the manifest.
  * A ZOMBIE UnrealEditor PROCESS MAKES A SAVE RETURN False WITH NO OTHER SYMPTOM. Before
    believing save_current_level(), this script lists UnrealEditor* processes and records them.

Safety model (the release_place_assets.py model, unchanged):
  * Refuses on the wrong project directory, a game world, dirty packages, or a loaded world that
    is not the target map.
  * Copies Walkthrough.umap and any One-File-Per-Actor folders to a checkpoint before any
    mutation and verifies the copy by hash.
  * A gate that fails validation becomes an OMISSION with numeric evidence and its partially
    spawned actors are destroyed. Guard failures before mutation raise.
  * Saves only if something was placed, reopens the map, and reads back every placed actor's
    mesh path, pose and world bounds numerically.
  * The receipt JSON is written at start and again in finally, so failure receipts are preserved.
"""
import hashlib
import json
import math
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_gate_security.spec.json'
HELPER_PATH = ROOT / 'Scripts' / 'release_place_assets.py'
_HELPER = None


def helper():
    """release_place_assets.py, loaded by path: the one place the before/after comparison
    rules live (snapshot_row, numeric_baseline_rows, diff_baselines, LOAD_CHURN_REGRESSION)."""
    global _HELPER
    if _HELPER is None:
        import importlib.util
        module_spec = importlib.util.spec_from_file_location('release_place_assets', HELPER_PATH)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        for name in ('snapshot_row', 'numeric_baseline_rows', 'baseline_exclusions',
                     'diff_baselines', 'selftest_snapshot_rules', 'LOAD_CHURN_REGRESSION'):
            if not hasattr(module, name):
                raise RuntimeError('release_place_assets.py lacks ' + name)
        _HELPER = module
    return _HELPER

TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
GATE_ORDER = ('east', 'north', 'south')


# ==========================================================================
# Pure helpers -- no unreal import, so offline_check() runs anywhere.
# ==========================================================================

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

    UE computes component bounds as the AABB of the transformed local box, so taking the eight
    rotated corners reproduces get_actor_bounds numerically.
    """
    yaw = math.radians(yaw_degrees)
    cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
    corners = []
    for x in (local['min'][0], local['max'][0]):
        for y in (local['min'][1], local['max'][1]):
            for z in (local['min'][2], local['max'][2]):
                corners.append((location[0] + x * cos_yaw - y * sin_yaw,
                                location[1] + x * sin_yaw + y * cos_yaw,
                                location[2] + z))
    return {'min': [min(c[i] for c in corners) for i in range(3)],
            'max': [max(c[i] for c in corners) for i in range(3)]}


def local_to_world(local_xyz, anchor, yaw_degrees):
    """Assembly-local (x forward toward the gate, y traveller's right, z up) -> world cm."""
    yaw = math.radians(yaw_degrees)
    cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
    x, y, z = local_xyz
    return [anchor[0] + x * cos_yaw - y * sin_yaw,
            anchor[1] + x * sin_yaw + y * cos_yaw,
            anchor[2] + z]


def boxes_overlap_volume(a, b):
    """Strictly positive overlap on all three axes; touching planes do not count."""
    for i in range(3):
        if min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) <= 1e-6:
            return False
    return True


def normalise_gates(gates):
    if isinstance(gates, str):
        gates = [g for g in gates.replace(';', ',').split(',') if g.strip()]
    out = []
    for gate in gates:
        key = gate.strip().lower()
        if key not in GATE_ORDER:
            raise ValueError('Unknown gate %r; known gates are %s' % (gate, ', '.join(GATE_ORDER)))
        if key not in out:
            out.append(key)
    if not out:
        raise ValueError('No gates requested')
    return tuple(g for g in GATE_ORDER if g in out)


# ==========================================================================
# The assembly: what stands where, in assembly-local centimetres.
# ==========================================================================
# Local frame: +X is the direction of travel TOWARDS the gate, +Y is the traveller's right,
# Z is up and the origin is on the deck at the anchor. So an element at a NEGATIVE local x
# stands further OUT from the gate and the visitor meets it first.
#
# Every one of these numbers is DEPICTED, not asserted. There is no measured drawing of a
# Jerusalem checkpoint in this project and none is claimed; the layout is an ordinary one,
# arranged so a visitor walks queue -> bag scanner -> detector -> shoe rack -> stairs.

STANCHION_ROW_Y = 235.0
STANCHION_X = (-900.0, -720.0, -540.0, -360.0)


def assembly_elements(gate_spec):
    """The full element list for one gate, in assembly-local coordinates.

    Returns dicts of: key (mesh key), x, y, z, yaw (local), sign (texture key or None),
    and note (why it is there).
    """
    plate_x = gate_spec['vestibulePlateLocalXCm']
    plate_z = gate_spec['vestibulePlateLocalZCm']
    elements = []

    # --- the queue: two rows of belt stanchions channelling the approach --------------
    # Local yaw -90 turns the mesh's own +Y (the direction its belt is paid out) onto the
    # assembly's +X, so each post's belt reaches the next post in the row.
    for row, side in (('L', -1.0), ('R', 1.0)):
        for i, x in enumerate(STANCHION_X):
            elements.append(dict(key='Stanchion', x=x, y=side * STANCHION_ROW_Y, z=0.0, yaw=-90.0,
                                 sign=None, name='Stanchion%s%d' % (row, i + 1),
                                 note='queue lane, modern staging'))

    # --- the signs the visitor reads on the way in ------------------------------------
    # The printed face is on the panel's local -X, so local yaw 0 makes it read towards the
    # approaching visitor. Two sign lines: one far out, one at the head of the queue.
    for name, x, y, sign in (('SignFar_Shoes', -860.0, -170.0, 'Shoes'),
                             ('SignFar_Security', -860.0, 170.0, 'Security'),
                             ('SignNear_Shoes', -380.0, -170.0, 'Shoes'),
                             ('SignNear_Reverence', -380.0, 170.0, 'Reverence')):
        elements.append(dict(key='SignPostFrame', x=x, y=y, z=0.0, yaw=0.0, sign=None,
                             name=name + '_Frame', note='post-mounted sign panel'))
        elements.append(dict(key='SignPostFace', x=x, y=y, z=0.0, yaw=0.0, sign=sign,
                             name=name + '_Face', note='printed face: ' + sign))

    # --- the screening line -----------------------------------------------------------
    elements.append(dict(key='BagScanner', x=-560.0, y=380.0, z=0.0, yaw=0.0, sign=None,
                         name='BagScanner', note='modern staging: Kotel plaza bag check'))
    for lane, y in (('A', -115.0), ('B', 115.0)):
        elements.append(dict(key='DetectorArch', x=-260.0, y=y, z=0.0, yaw=0.0, sign=None,
                             name='DetectorArch' + lane, note='modern staging: walk-through detector'))
    elements.append(dict(key='Booth', x=-170.0, y=-430.0, z=0.0, yaw=0.0, sign=None,
                         name='Booth', note='modern staging: guard booth, service window faces the queue'))

    # --- wall-mounted plates on the booth's queue-facing wall --------------------------
    # The plate's face is on its local -X and its frame extends +X into whatever it is
    # mounted on, so at x = -287 the frame sits in the booth's -X wall (at x = -286) and
    # the face reads back down the queue.
    for i, y in enumerate((-370.0, -490.0)):
        elements.append(dict(key='SignPlateFrame', x=-287.0, y=y, z=0.0, yaw=0.0, sign=None,
                             name='BoothPlate%d_Frame' % (i + 1), mount='Booth',
                             note='wall plate on the booth'))
        elements.append(dict(key='SignPlateFace', x=-287.0, y=y, z=0.0, yaw=0.0, sign='Entrance',
                             name='BoothPlate%d_Face' % (i + 1), mount='Booth',
                             note='printed face: Entrance'))

    # --- shoes come off past the screening, before the stairs -------------------------
    # x=-30 puts them on the clear deck between the arches and the foot of the stairs. An
    # earlier x=+150 reached into the first riser's own Y span by 3.5 cm -- the checkpoint
    # stands ON THE DECK and touches no part of the measured architecture.
    for i, y in enumerate((-420.0, 420.0)):
        elements.append(dict(key='ShoeRack', x=-30.0, y=y, z=0.0, yaw=0.0, sign=None,
                             name='ShoeRack%d' % (i + 1),
                             note='shoes off before the Mount (rule); the rack itself is staging'))

    # --- wall-mounted plates on the real vestibule wall at the head of the stairs ------
    # These use recorded architecture: the vestibule wall's outward face, which the visitor
    # meets head-on at the top of the stairs. plate_x / plate_z are per gate.
    for i, y in enumerate((-475.0, 475.0)):
        elements.append(dict(key='SignPlateFrame', x=plate_x, y=y, z=plate_z, yaw=0.0, sign=None,
                             name='VestibulePlate%d_Frame' % (i + 1), mount='ARCHITECTURE',
                             note='wall plate on the measured vestibule wall'))
        elements.append(dict(key='SignPlateFace', x=plate_x, y=y, z=plate_z, yaw=0.0, sign='Entrance',
                             name='VestibulePlate%d_Face' % (i + 1), mount='ARCHITECTURE',
                             note='printed face: Entrance'))
    return elements


def plan_gate(spec, gate_key):
    """Full world-space plan for one gate. Pure: no engine, no side effects."""
    gate = spec['gates'][gate_key]
    anchor, yaw = gate['anchorCm'], gate['assemblyYawDegrees']
    meshes = spec['meshes']
    planned = []
    for element in assembly_elements(gate):
        record = meshes[element['key']]
        location = local_to_world((element['x'], element['y'], element['z']), anchor, yaw)
        world_yaw = yaw + element['yaw']
        world_box = rotate_box_yaw(record['localBoundsCm'], location, world_yaw)
        planned.append({
            'label': spec['labelPrefix'] + spec['group'] + '_' + gate['short'] + '_' + element['name'],
            'gate': gate_key,
            'meshKey': element['key'],
            'mesh': record['asset'],
            'triangles': record['triangles'],
            'role': record['role'],
            'sign': element['sign'],
            'localCm': [element['x'], element['y'], element['z']],
            'localYaw': element['yaw'],
            'location': [round(v, 4) for v in location],
            'rotation': {'pitch': 0.0, 'yaw': float(world_yaw), 'roll': 0.0},
            'scale': [1.0, 1.0, 1.0],
            'plannedWorldBoundsCm': {k: [round(x, 4) for x in v] for k, v in world_box.items()},
            'folder': spec['folderPrefix'] + spec['group'] + '/' + gate['short'],
            'mount': element.get('mount'),
            'mountedOnLabel': (None if element.get('mount') in (None, 'ARCHITECTURE') else
                               spec['labelPrefix'] + spec['group'] + '_' + gate['short'] + '_'
                               + element['mount']),
            'note': element['note'],
        })
    return planned


def self_intersections(planned, tolerance_cm):
    """Elements of one gate that overlap each other by more than a tolerated interpenetration.

    Three exemptions, all of them deliberate rather than tolerated: a frame and its printed face
    share a transform; a wall-mounted plate is SUPPOSED to be buried in whatever it declares it
    is mounted on; and nothing else may interpenetrate anything at all.
    """
    clashes = []
    for i in range(len(planned)):
        for j in range(i + 1, len(planned)):
            a, b = planned[i], planned[j]
            if a['location'] == b['location']:
                continue
            if a['label'].rsplit('_', 1)[0] == b['label'].rsplit('_', 1)[0]:
                continue
            if a.get('mountedOnLabel') == b['label'] or b.get('mountedOnLabel') == a['label']:
                continue
            shrunk = {'min': [a['plannedWorldBoundsCm']['min'][k] + tolerance_cm for k in range(3)],
                      'max': [a['plannedWorldBoundsCm']['max'][k] - tolerance_cm for k in range(3)]}
            if any(shrunk['min'][k] >= shrunk['max'][k] for k in range(3)):
                continue
            if boxes_overlap_volume(shrunk, b['plannedWorldBoundsCm']):
                clashes.append([a['label'], b['label']])
    return clashes


def offline_check(spec=None):
    """Everything that can be proved without the engine. Safe to run anywhere."""
    spec = spec or load_spec()
    report = {'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
              'projectDirMatches': Path(spec['projectDir']).resolve() == ROOT,
              'targetMap': spec['targetMap'], 'gates': {}, 'problems': []}

    source = spec['source']
    manifest_path = ROOT / source['manifest']
    report['manifestPresent'] = manifest_path.is_file()
    if report['manifestPresent']:
        report['manifestSha256'] = sha256_of(manifest_path)
        report['manifestSha256Matches'] = report['manifestSha256'] == source['manifestSha256']
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        report['manifestStatus'] = manifest.get('status')
        report['manifestStatusMatches'] = manifest.get('status') == source['manifestStatusRequired']
        if not report['manifestSha256Matches']:
            report['problems'].append('geometry-manifest.json hash differs from the spec; '
                                      're-run create_gate_security.py --export then --write-spec')
        if not report['manifestStatusMatches']:
            report['problems'].append('geometry manifest status is %r' % manifest.get('status'))
    else:
        report['problems'].append('geometry manifest missing: ' + str(manifest_path))

    # every OBJ and every sign PNG must be on disk with the exact hash the spec froze
    files = []
    for key, record in sorted(spec['meshes'].items()):
        path = ROOT / source['folder'] / record['file']
        present = path.is_file()
        entry = {'kind': 'obj', 'key': key, 'file': record['file'], 'present': present}
        if present:
            entry['sha256Matches'] = sha256_of(path) == record['sha256']
            if not entry['sha256Matches']:
                report['problems'].append('OBJ hash changed: ' + record['file'])
        else:
            report['problems'].append('OBJ missing: ' + str(path))
        files.append(entry)
    for key, record in sorted(spec['signs'].items()):
        path = ROOT / source['signFolder'] / record['file']
        present = path.is_file()
        entry = {'kind': 'png', 'key': key, 'file': record['file'], 'present': present,
                 'claim': record['claim']}
        if present:
            entry['sha256Matches'] = sha256_of(path) == record['sha256']
            if not entry['sha256Matches']:
                report['problems'].append('sign PNG hash changed: ' + record['file'])
        else:
            report['problems'].append('sign PNG missing: ' + str(path))
        files.append(entry)
    report['files'] = files

    # the glyph check receipt must exist and must actually have passed
    glyph_path = ROOT / source['glyphCheck']
    report['glyphCheckPresent'] = glyph_path.is_file()
    if report['glyphCheckPresent']:
        glyphs = json.loads(glyph_path.read_text(encoding='utf-8'))
        report['glyphCheck'] = {
            'font': glyphs['fonts'][0]['file'] if glyphs.get('fonts') else None,
            'codepointsChecked': len(glyphs.get('glyphs') or []),
            'missingGlyphs': len(glyphs.get('missingGlyphs') or []),
            'emptyGlyphs': len(glyphs.get('emptyGlyphs') or []),
            'rightToLeftPassed': bool((glyphs.get('rightToLeft') or {}).get('pass_')),
            'arabicShapingPassed': bool((glyphs.get('arabicShaping') or {}).get('allMatch')),
        }
        if glyphs.get('missingGlyphs') or glyphs.get('emptyGlyphs'):
            report['problems'].append('glyph check reports missing or empty glyphs; '
                                      'the signs would ship as mojibake')
        if not report['glyphCheck']['rightToLeftPassed']:
            report['problems'].append('glyph check right-to-left probe did not pass')
        if not report['glyphCheck']['arabicShapingPassed']:
            report['problems'].append('glyph check Arabic shaping did not pass')
    else:
        report['problems'].append('glyph check receipt missing: ' + str(glyph_path))

    # the gate anchors: architecture bounds the spec froze must still be in the manifest
    architecture = json.loads((ROOT / spec['architectureManifest']).read_text(encoding='utf-8'))
    by_asset = {m['assetName']: m for m in architecture['meshes']}
    total = 0
    for gate_key in GATE_ORDER:
        gate = spec['gates'][gate_key]
        entry = {'anchorCm': gate['anchorCm'], 'assemblyYawDegrees': gate['assemblyYawDegrees'],
                 'anchorActors': [], 'elements': 0}
        for anchor_actor in gate['anchorActors']:
            found = by_asset.get(anchor_actor['assetName'])
            row = {'assetName': anchor_actor['assetName'], 'asset': anchor_actor['asset'],
                   'inManifest': found is not None,
                   'uassetOnDisk': disk_path(anchor_actor['asset']).is_file()}
            if found is not None:
                row['boundsMatchManifest'] = box_error(
                    box_from_min_max(found['expectedBoundsUnrealCm']['min'],
                                     found['expectedBoundsUnrealCm']['max']),
                    box_from_min_max(anchor_actor['expectedWorldBoundsCm']['min'],
                                     anchor_actor['expectedWorldBoundsCm']['max'])) <= 1e-4
                if not row['boundsMatchManifest']:
                    report['problems'].append('anchor bounds drifted for ' + anchor_actor['assetName'])
            else:
                report['problems'].append('anchor actor not in architecture manifest: '
                                          + anchor_actor['assetName'])
            if not row['uassetOnDisk']:
                report['problems'].append('anchor uasset missing on disk: ' + anchor_actor['asset'])
            entry['anchorActors'].append(row)

        planned = plan_gate(spec, gate_key)
        entry['elements'] = len(planned)
        entry['triangles'] = sum(p['triangles'] for p in planned)
        total += entry['triangles']
        footprint = {'min': [min(p['plannedWorldBoundsCm']['min'][i] for p in planned) for i in range(3)],
                     'max': [max(p['plannedWorldBoundsCm']['max'][i] for p in planned) for i in range(3)]}
        entry['plannedFootprintCm'] = {k: [round(x, 2) for x in v] for k, v in footprint.items()}
        clashes = self_intersections(planned, spec['verification']['selfIntersectionToleranceCm'])
        entry['selfIntersections'] = clashes
        if clashes:
            report['problems'].append('gate %s: planned elements interpenetrate: %s'
                                      % (gate_key, clashes[:4]))
        # nothing may be planned on or beyond the first riser: the checkpoint stands on the deck
        riser = gate['firstRiserBoundsCm']
        on_stairs = [p['label'] for p in planned
                     if p.get('mount') != 'ARCHITECTURE'
                     and boxes_overlap_volume(p['plannedWorldBoundsCm'], riser)]
        entry['elementsOverlappingFirstRiser'] = on_stairs
        if on_stairs:
            report['problems'].append('gate %s: elements overlap the first riser: %s'
                                      % (gate_key, on_stairs[:4]))
        report['gates'][gate_key] = entry

    report['plannedActorCount'] = sum(g['elements'] for g in report['gates'].values())
    report['plannedTriangles'] = total
    report['triangleBudget'] = spec['verification']['maxTotalTrianglesPlaced']
    if total > report['triangleBudget']:
        report['problems'].append('planned triangles %d exceed the budget %d'
                                  % (total, report['triangleBudget']))
    report['westGateOmitted'] = spec['westGate']
    try:
        report['snapshotRulesSelfTest'] = helper().selftest_snapshot_rules()
    except Exception as error:  # noqa: BLE001
        report['problems'].append('shared snapshot rules self-test failed: %r' % error)
    report['passed'] = not report['problems']
    return report


# ==========================================================================
# The spec writer -- offline. Derives every number from receipts already on disk.
# ==========================================================================

# Gate table. The anchors, yaws and vestibule-wall faces are DERIVED from
# SourceAssets/architecture-manifest.json and SourceAssets/mount-access/GatewayV3/
# gateway-approach-audit.json; see the module docstring and sources.md. No yaw is recorded
# anywhere for any gate, so each assembly yaw comes from that gate's outward axis.
GATE_TABLE = {
    'east': dict(
        short='E', outwardAxis='+X', travelDirection='-X', assemblyYawDegrees=180.0,
        anchorCm=[9300.0, 0.0, 0.0], deckZCm=0.0,
        firstRiserAsset='SM_0261_architecture_Outer_E_stair_1',
        thresholdAsset='SM_0177_architecture_Outer_E_threshold',
        vestibuleFloorZCm=300.0, vestibuleOuterFaceCm=7800.0,
        anchorBasis='Deck (Z 0) 100 cm outward of the first riser at X 9150; gate axis Y 0.'),
    'north': dict(
        short='N', outwardAxis='-Y', travelDirection='+Y', assemblyYawDegrees=90.0,
        anchorCm=[0.0, -9550.0, 0.0], deckZCm=0.0,
        firstRiserAsset='SM_0364_architecture_Outer_N_mount_approach_terrace',
        thresholdAsset='SM_0273_architecture_Outer_N_threshold',
        vestibuleFloorZCm=425.0, vestibuleOuterFaceCm=-7800.0,
        anchorBasis='Deck (Z 0) 100 cm outward of the first terrace riser at Y -9450; gate axis X 0.'),
    'south': dict(
        short='S', outwardAxis='+Y', travelDirection='-Y', assemblyYawDegrees=-90.0,
        anchorCm=[0.0, 9550.0, 0.0], deckZCm=0.0,
        firstRiserAsset='SM_0465_architecture_Outer_S_mount_approach_terrace',
        thresholdAsset='SM_0374_architecture_Outer_S_threshold',
        vestibuleFloorZCm=425.0, vestibuleOuterFaceCm=7800.0,
        anchorBasis='Deck (Z 0) 100 cm outward of the first terrace riser at Y 9450; gate axis X 0.'),
}

ARCH_ASSET_PREFIX = '/Game/MikdashV3/Architecture/architecture_'

ROLE_MATERIALS = {
    'metal_brushed': [('/Game/MikdashV3/ArrivalReview/TransitV2/Materials/M_TransitV2_Aluminium',
                       'brushed aluminium (TransitV2 release)'),
                      ('/Game/MikdashV3/ArrivalReview/BusStudyV1/Materials/M_BusStudyV1_Aluminium',
                       'aluminium_fallback')],
    'metal_dark': [('/Game/MikdashV3/ArrivalReview/TransitV2/Materials/M_TransitV2_DarkTrim',
                    'dark trim (TransitV2 release)'),
                   ('/Game/MikdashV3/ArrivalReview/BusStudyV1/Materials/M_BusStudyV1_DarkTrim',
                    'dark_trim_fallback')],
    'painted_steel': [('/Game/MikdashV3/ArrivalReview/TransitV2/Materials/M_TransitV2_IvoryPaint',
                       'ivory paint (TransitV2 release)'),
                      ('/Game/MikdashV3/ArrivalReview/BusStudyV1/Materials/M_BusStudyV1_IvoryPaint',
                       'ivory_paint_fallback')],
    'timber': [('/Game/MikdashV3/ArrivalReview/TransitV2/Materials/M_TransitV2_BenchWood',
                'bench timber (TransitV2 release)')],
    'sign_face': [],   # always the created parent + a per-sign instance; see signFaceMaterial
}


def write_spec():
    """Regenerate release_gate_security.spec.json from the receipts on disk."""
    source_folder = 'SourceAssets/security-review/GateSecurityV1'
    sign_folder = 'SourceAssets/security-review/signs'
    manifest_path = ROOT / source_folder / 'geometry-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    architecture = json.loads((ROOT / 'SourceAssets/architecture-manifest.json').read_text(encoding='utf-8'))
    by_asset = {m['assetName']: m for m in architecture['meshes']}

    namespace = manifest['namespace'].rstrip('/')
    meshes = {}
    for record in manifest['meshes']:
        key = record['name'].replace('SM_GateSecurityV1_', '')
        path = ROOT / source_folder / record['file']
        meshes[key] = {
            'name': record['name'],
            'asset': namespace + '/Meshes/' + record['name'],
            'file': record['file'],
            'sha256': sha256_of(path),
            'triangles': record['triangles'],
            'role': record['material_role'],
            'claim': record['claim'],
            'what': record['what'],
            'localBoundsCm': box_from_min_max(record['bounds_cm']['min'], record['bounds_cm']['max']),
        }

    signs = {}
    for name, record in manifest['signs'].items():
        path = ROOT / sign_folder / record['file']
        signs[name] = {
            'file': record['file'],
            'sha256': sha256_of(path),
            'texture': namespace + '/Textures/T_GateSecurityV1_Sign_' + name,
            'materialInstance': namespace + '/Materials/MI_GateSecurityV1_Sign_' + name,
            'claim': record['claim'],
            'says': record['says'],
            'form': record['form'],
            'widthPx': record['pixels'][0], 'heightPx': record['pixels'][1],
        }

    gates = {}
    for key, table in GATE_TABLE.items():
        riser = by_asset[table['firstRiserAsset']]
        threshold = by_asset[table['thresholdAsset']]
        anchor_actors = []
        for role, entry in (('firstRiser', riser), ('threshold', threshold)):
            anchor_actors.append({
                'role': role,
                'assetName': entry['assetName'],
                'sourceName': entry['sourceName'],
                'asset': ARCH_ASSET_PREFIX + entry['assetName'],
                'expectedWorldBoundsCm': box_from_min_max(entry['expectedBoundsUnrealCm']['min'],
                                                          entry['expectedBoundsUnrealCm']['max']),
                'matchBy': 'static mesh asset path (labels are NOT unique in this map)',
            })
        # distance from the anchor, along the direction of travel, to the vestibule wall's
        # outward face -- this is the assembly-local x of the wall-mounted vestibule plates.
        yaw = math.radians(table['assemblyYawDegrees'])
        forward = (math.cos(yaw), math.sin(yaw))
        anchor = table['anchorCm']
        if abs(forward[0]) > abs(forward[1]):
            plate_local_x = (table['vestibuleOuterFaceCm'] - anchor[0]) * (1.0 if forward[0] > 0 else -1.0)
        else:
            plate_local_x = (table['vestibuleOuterFaceCm'] - anchor[1]) * (1.0 if forward[1] > 0 else -1.0)
        gates[key] = {
            'short': table['short'],
            'outwardAxis': table['outwardAxis'],
            'travelDirection': table['travelDirection'],
            'assemblyYawDegrees': table['assemblyYawDegrees'],
            'assemblyYawBasis': ('DERIVED from the outward axis. No yaw is recorded for any gate '
                                 'anywhere in this project; every gate record is axis-aligned '
                                 'with rotation [0,0,0].'),
            'anchorCm': anchor,
            'anchorBasis': table['anchorBasis'],
            'deckZCm': table['deckZCm'],
            'deckZBasis': ('gateway-approach-audit.json records bottomPlatformUncoveredAreaCm2 0.0 '
                           'for E, N and S: the deck at all three approaches is Z 0.'),
            'anchorActors': anchor_actors,
            'firstRiserBoundsCm': anchor_actors[0]['expectedWorldBoundsCm'],
            'vestibulePlateLocalXCm': round(plate_local_x, 4),
            'vestibulePlateLocalZCm': table['vestibuleFloorZCm'] - table['deckZCm'],
            'vestibulePlateBasis': ('The vestibule wall outward face at %s cm; the plate reads '
                                    'towards the visitor climbing the stairs.'
                                    % table['vestibuleOuterFaceCm']),
        }

    spec = {
        'specVersion': 1,
        'prepared': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'purpose': ('Human-reviewable import and placement plan consumed by '
                    'Scripts/release_gate_security.py. Every asset path, transform and '
                    'tolerance is here so the plan can be reviewed before it is run.'),
        'sourceTable': 'SourceAssets/security-review/sources.md',
        'claimSummary': {
            'asserted': ('Entering Har HaBayit in shoes is prohibited; the Mount may not be used '
                         'as a shortcut; one may not spit there. Mishnah Berachos 9:5; Rambam, '
                         'Hilchos Beis HaBechira 7:2. Cited on the sign faces themselves.'),
            'modernStaging': ('The detector arches, bag scanner, stanchions, guard booth and the '
                              'telephone rule. Modelled on the Har HaBayit and Kotel plaza '
                              'entrance procedure TODAY. No classical source; no claim about the '
                              'Temple or its courts.'),
            'depictedNotAsserted': 'Every dimension, material, colour and position of every object.',
        },
        'projectDir': str(ROOT),
        'targetMap': TARGET,
        'targetMapFile': 'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap',
        'protectedMaps': ['/Game/MikdashV3/Maps/Courtyard',
                          '/Game/MikdashV3/IntegratedReviewV1/Maps/Walkthrough'],
        'checkpointRoot': r'C:\Mikdash\Working-5.8\ReviewCheckpoints',
        'checkpointPrefix': 'GateSecurity-',
        'receiptFolder': 'SourceAssets/security-review',
        'receiptPrefix': 'native-gate-security-',
        'actorTag': 'GateSecurityV1',
        'labelPrefix': 'RELEASE_',
        'folderPrefix': 'Release/',
        'group': 'GateSecurity',
        'architectureManifest': 'SourceAssets/architecture-manifest.json',
        'westGate': ('NOT PLACED. gateway-approach-audit.json direction W records '
                     '"NO_SOURCE_GATE_DO_NOT_INVENT_OPENING_OR_STAIRS". There is no west gate '
                     'and none is invented.'),
        'source': {
            'folder': source_folder,
            'signFolder': sign_folder,
            'manifest': source_folder + '/geometry-manifest.json',
            'manifestSha256': sha256_of(manifest_path),
            'manifestStatusRequired': 'OFFLINE_VALIDATED_NATIVE_AND_VISUAL_PENDING',
            'glyphCheck': sign_folder + '/glyph-check.json',
            'authoringScript': 'Scripts/create_gate_security.py',
            'namespace': namespace,
            'meshFolder': namespace + '/Meshes',
            'textureFolder': namespace + '/Textures',
            'materialFolder': namespace + '/Materials',
            'objAdapter': manifest['convention'],
        },
        'importSettings': {
            'note': ('Identical to the reviewed keilim / doors / vessels OBJ adapter path '
                     '(FbxFactory). Single-mesh OBJ: destination_name is the exact mesh name. '
                     'build_nanite is False -- with Nanite on, get_num_triangles(0) returns the '
                     'FALLBACK count and every triangle comparison below would be meaningless.'),
            'factory': 'FbxFactory',
            'fbxImportUI': {
                'automated_import_should_detect_type': False,
                'mesh_type_to_import': 'FBXIT_STATIC_MESH',
                'import_as_skeletal': False,
                'import_mesh': True,
                'import_animations': False,
                'import_materials': False,
                'import_textures': False,
                'create_physics_asset': False,
            },
            'staticMeshImportData': {
                'combine_meshes': True,
                'transform_vertex_to_absolute': True,
                'bake_pivot_in_vertex': False,
                'convert_scene': False,
                'convert_scene_unit': False,
                'force_front_x_axis': False,
                'import_uniform_scale': 1.0,
                'auto_generate_collision': False,
                'build_nanite': False,
                'generate_lightmap_u_vs': False,
                'remove_degenerates': True,
                'normal_import_method': 'FBXNIM_IMPORT_NORMALS',
            },
            'textureSettings': {
                'srgb': True,
                'compression': 'TC_Default',
                'note': ('Sign faces are sRGB colour art. The texture is imported with '
                         'TextureFactory and its sRGB flag is READ BACK, never assumed.'),
            },
        },
        'meshes': meshes,
        'signs': signs,
        'materials': {
            'rule': ('First candidate that exists on disk and loads as a MaterialInterface is '
                     'assigned to EVERY slot of the mesh. Falling past the first candidate is '
                     'recorded as a limitation. UE 5.8 material setters can return False on a '
                     'call that took, so the pass/fail decision is ALWAYS the readback.'),
            'roles': {role: {'candidates': [{'path': p, 'kind': k} for p, k in candidates]}
                      for role, candidates in ROLE_MATERIALS.items()},
            'signFaceMaterial': {
                'createParent': namespace + '/Materials/M_GateSecurityV1_SignFace',
                'textureParameterName': 'SignFace',
                'constants': {'metallic': 0.0, 'roughness': 0.62},
                'method': ('MaterialFactoryNew, then a MaterialExpressionTextureSampleParameter2D '
                           'named SignFace wired to BaseColor and Constant nodes wired to '
                           'Metallic and Roughness. connect_material_property can return False on '
                           'a connection that took, so the return value is only RECORDED; the '
                           'decision is the readback of the connected inputs on the SAVED asset.'),
                'instanceMethod': ('One MaterialInstanceConstant per sign, texture parameter set '
                                   'with MaterialEditingLibrary and verified with '
                                   'get_material_instance_texture_parameter_value.'),
                'appliedPerActor': ('The SAME face mesh carries three different sign artworks, so '
                                    'the instance is set on the ACTOR COMPONENT '
                                    '(component.set_material) and NOT on the mesh asset, then '
                                    'read back with component.get_material.'),
            },
        },
        'gates': gates,
        'assembly': {
            'localFrame': ('+X is the direction of travel TOWARDS the gate, +Y is the traveller\'s '
                           'right, Z is up, origin on the deck at the anchor. A NEGATIVE local x '
                           'stands further out from the gate, so the visitor meets it first.'),
            'order': 'queue -> bag scanner -> detector arches -> shoe racks -> stairs',
            'stanchionRowYCm': STANCHION_ROW_Y,
            'stanchionXCm': list(STANCHION_X),
            'elementsPerGate': len(assembly_elements(gates['east'])),
            'depicted': ('Every number in the layout is DEPICTED, not asserted. There is no '
                         'measured drawing of a Jerusalem checkpoint in this project.'),
        },
        'verification': {
            'transformToleranceCm': 0.001,
            'staticBoundsToleranceCm': 0.05,
            'localBoundsToleranceCm': 0.05,
            'anchorBoundsToleranceCm': 1.0,
            'selfIntersectionToleranceCm': 2.0,
            'maxTotalTrianglesPlaced': 2000000,
            'compareRule': ('Numeric location / rotation / scale fields and AABB corners only; '
                            'str(Transform) is not compared.'),
        },
        'windingCheck': {
            'note': ('GeometryScript readback of the imported LOD0 source model (needs '
                     '-EnablePlugins=GeometryScripting): signed volume by the divergence theorem '
                     'with the UE left-handed face normal cross(C-A, B-A). The OBJ carries Y '
                     'reflected and the winding reversed; the importer reflects Y back, so a '
                     'correctly imported mesh has POSITIVE signed volume in Unreal.'),
            'requireForPlacement': False,
            'requireForPlacementNote': ('Recorded rather than required, because the winding is '
                                        'already proved offline part by part in '
                                        'create_gate_security.py (every part asserted closed and '
                                        'positively oriented before writing). Pass '
                                        '-GateSecurityAllowUnverifiedWinding to place when '
                                        'GeometryScripting is not loaded.'),
        },
        'limitations': [
            'Placement is geometric only: no visual, halachic, walking, collision-route or packaged acceptance is established.',
            'The checkpoint, the detectors, the bag scanner, the booth and the telephone rule are MODERN STAGING modelled on Jerusalem today, not sourced from any classical text.',
            'Deck extent outward of the first riser was NOT confirmed offline; the script checks each element against the first riser only, and a visual pass is still required to confirm nothing overhangs the platform edge.',
            'No yaw is recorded for any gate anywhere; every assembly yaw is derived from the gate outward axis.',
            'No nav corridor, spline or queue path exists in this project; the stanchion lane is scenery, not navigation.',
        ],
    }
    SPEC_PATH.write_text(json.dumps(spec, indent=2) + '\n', encoding='utf-8')
    return spec


# ==========================================================================
# Engine side
# ==========================================================================

def _xyz(v):
    return [float(v.x), float(v.y), float(v.z)]


def _vector_list(v):
    return [round(float(v.x), 6), round(float(v.y), 6), round(float(v.z), 6)]


def _rotator_list(r):
    return [round(float(r.pitch), 6), round(float(r.yaw), 6), round(float(r.roll), 6)]


def _asset_path(obj):
    return None if obj is None else obj.get_path_name().split('.')[0]


def _uasset_sha(asset):
    path = disk_path(_asset_path(asset))
    return sha256_of(path) if path.is_file() else None


def _static_mesh_box(mesh):
    bounds = mesh.get_bounding_box()
    return box_from_min_max(_xyz(bounds.min), _xyz(bounds.max))


def _actor_bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    o, e = _xyz(origin), _xyz(extent)
    return {'min': [round(o[i] - e[i], 4) for i in range(3)],
            'max': [round(o[i] + e[i], 4) for i in range(3)]}


def _actor_pose(actor):
    return {'location': _vector_list(actor.get_actor_location()),
            'rotation': _rotator_list(actor.get_actor_rotation()),
            'scale': _vector_list(actor.get_actor_scale3d())}


def _pose_close(pose, location, rotation, scale, tolerance):
    error = max([abs(pose['location'][i] - location[i]) for i in range(3)]
                + [abs(pose['scale'][i] - scale[i]) for i in range(3)]
                + [abs((pose['rotation'][0] - rotation['pitch'] + 180) % 360 - 180),
                   abs((pose['rotation'][1] - rotation['yaw'] + 180) % 360 - 180),
                   abs((pose['rotation'][2] - rotation['roll'] + 180) % 360 - 180)])
    return error <= tolerance, round(error, 6)


def _zombie_editors():
    """A stray UnrealEditor process makes save_current_level() return False with no other
    symptom. This has cost this project a debugging session before, so the process list is
    captured rather than guessed at."""
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UnrealEditor*.exe', '/NH'],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception as error:  # noqa: BLE001
        return {'checked': False, 'reason': repr(error)}
    rows = [line.split()[0] for line in out.splitlines() if 'UnrealEditor' in line]
    return {'checked': True, 'processes': rows, 'count': len(rows)}


class OmissionError(Exception):
    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


class GateSecurity(object):
    def __init__(self, ue, spec):
        self.ue = ue
        self.spec = spec
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors_sub = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.world = None
        self.receipt = {}
        self.receipt_path = None
        self.snapshot = []
        self.materials = {}
        self.sign_materials = {}
        self.excluded_names = set()

    # -- receipt -----------------------------------------------------------
    def write_receipt(self):
        if self.receipt_path is not None:
            self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n',
                                         encoding='utf-8')

    # -- world snapshot ----------------------------------------------------
    # All comparison rules live in release_place_assets.py (see LOAD_CHURN_REGRESSION there).
    # This script compares STRICTLY -- bounds included -- but bounds only ever enter the key
    # for actors with no instanced component, which is exactly what the 2026-09-08 refusal
    # got wrong: it put the instance-derived AABB of ten ISM/HISM carriers into the key.
    def _map_package(self):
        world = self.world or self.editor.get_editor_world()
        return world.get_outermost().get_name()

    def take_snapshot(self):
        h = helper()
        map_package = self._map_package()
        rows = [h.snapshot_row(self.ue, actor, map_package)
                for actor in self.actors_sub.get_all_level_actors() if actor is not None]
        self.snapshot = rows
        return rows

    def numeric_baseline(self, rows):
        return helper().numeric_baseline_rows(rows, strict=True, exclude=self.excluded_names)

    def baseline_exclusions(self, rows):
        return helper().baseline_exclusions(rows, exclude=self.excluded_names)

    def diff(self, before_rows, after_rows):
        return helper().diff_baselines(before_rows, after_rows, strict=True, exclude=self.excluded_names)

    def probe_load_churn(self):
        """Two pristine loads, before any mutation: whatever differs is load churn, recorded
        and excluded. Catches in-level RF_Transient spawns too, which Python cannot flag."""
        first = self.snapshot or self.take_snapshot()
        if not self.levels.load_level(TARGET):
            raise RuntimeError('probe_load_churn: reload failed')
        self.world = self.editor.get_editor_world()
        if self.world.get_outermost().get_name() != TARGET:
            raise RuntimeError('probe_load_churn: reloaded world is not the target')
        second = self.take_snapshot()
        churn = helper().diff_baselines(first, second, strict=True)
        names = sorted({d['name'] for d in churn})
        self.excluded_names |= set(names)
        return {'unstableActors': names, 'evidence': churn,
                'rule': 'differs between two pristine loads with nothing touched -> excluded'}

    # -- gate confirmation -------------------------------------------------
    def confirm_gate(self, gate_key):
        """Confirm the gate really is where the offline receipts say.

        Matched by STATIC MESH ASSET PATH, and read from the component WORLD BOUNDS, because
        measured-architecture actors are all spawned at the origin with an identity transform
        and get_actor_location() on them returns (0,0,0).
        """
        ue = self.ue
        gate = self.spec['gates'][gate_key]
        tolerance = self.spec['verification']['anchorBoundsToleranceCm']
        evidence = {'gate': gate_key, 'anchorCm': gate['anchorCm'], 'actors': []}
        for anchor_actor in gate['anchorActors']:
            found = []
            for row in self.snapshot:
                if anchor_actor['asset'] in row['meshes']:
                    found.append(row)
            entry = {'role': anchor_actor['role'], 'asset': anchor_actor['asset'],
                     'actorsWithThisMesh': len(found),
                     'expectedWorldBoundsCm': anchor_actor['expectedWorldBoundsCm']}
            if len(found) != 1:
                entry['status'] = 'not_uniquely_present'
                evidence['actors'].append(entry)
                raise OmissionError('gate %s: %s mesh matched %d actors, expected exactly 1'
                                    % (gate_key, anchor_actor['role'], len(found)), evidence)
            row = found[0]
            # World bounds, NOT get_actor_location(): every measured-architecture actor is
            # spawned at the origin with an identity transform and its world position lives in
            # the vertices, so the location is (0,0,0) and only the bounds carry the geometry.
            observed = _actor_bounds(row['actor'])
            entry.update({'label': row['label'], 'name': row['name'],
                          'observedWorldBoundsCm': observed,
                          'actorLocation': row['pose']['location'],
                          'actorLocationIsOriginAsExpected':
                              max(abs(v) for v in row['pose']['location']) < 1e-6,
                          'boundsErrorCm': round(box_error(observed,
                                                           anchor_actor['expectedWorldBoundsCm']), 4)})
            entry['status'] = 'confirmed' if entry['boundsErrorCm'] <= tolerance else 'bounds_differ'
            evidence['actors'].append(entry)
            if entry['status'] != 'confirmed':
                raise OmissionError('gate %s: %s world bounds differ by %.4f cm (tolerance %.4f)'
                                    % (gate_key, anchor_actor['role'], entry['boundsErrorCm'],
                                       tolerance), evidence)
        evidence['status'] = 'gate_confirmed_against_offline_receipts'
        return evidence

    # -- assets ------------------------------------------------------------
    def pick_material(self, role):
        ue = self.ue
        tried = []
        for position, candidate in enumerate(self.spec['materials']['roles'][role]['candidates']):
            exists = self.assets.does_asset_exist(candidate['path'])
            material = ue.load_asset(candidate['path']) if exists else None
            ok = isinstance(material, ue.MaterialInterface)
            tried.append({'path': candidate['path'], 'kind': candidate['kind'],
                          'exists': bool(exists), 'loaded': ok})
            if ok:
                if position > 0:
                    self.receipt['limitations'].append(
                        '%s material fell back to %s (%s)' % (role, candidate['path'], candidate['kind']))
                self.receipt['materials'][role] = {'assigned': candidate['path'],
                                                   'kind': candidate['kind'], 'tried': tried}
                return material
        self.receipt['materials'][role] = {'assigned': None, 'tried': tried}
        return None

    def _read_input_expression(self, material, property_name):
        try:
            holder = material.get_editor_property(property_name)
        except Exception:  # noqa: BLE001
            return None, 'property_not_reflected'
        if holder is None:
            return None, 'input_is_none'
        for attr in ('expression', 'Expression'):
            try:
                expression = holder.get_editor_property(attr)
            except Exception:  # noqa: BLE001
                expression = getattr(holder, attr, None)
            if expression is not None:
                return type(expression).__name__, 'connected'
        return None, 'not_connected'

    def sign_face_parent(self):
        """The parent material for every sign face: one texture parameter into BaseColor.

        UE 5.8 can return False from connect_material_property on a connection that took, so the
        returned flags are only RECORDED; the decision is the readback of the saved material.
        """
        ue = self.ue
        cfg = self.spec['materials']['signFaceMaterial']
        path = cfg['createParent']
        record = {'path': path, 'method': cfg['method']}
        if self.assets.does_asset_exist(path):
            material = ue.load_asset(path)
            if not isinstance(material, ue.MaterialInterface):
                raise RuntimeError('Existing sign face asset is not a material: ' + path)
            record.update({'created': False, 'reused': True})
            self.receipt['materials']['sign_face_parent'] = record
            return material
        folder, name = path.rsplit('/', 1)
        material = ue.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, ue.Material, ue.MaterialFactoryNew())
        if not isinstance(material, ue.Material):
            raise RuntimeError('Sign face material creation failed')
        ml = ue.MaterialEditingLibrary
        sampler = ml.create_material_expression(
            material, ue.MaterialExpressionTextureSampleParameter2D, -420, 0)
        sampler.set_editor_property('parameter_name', cfg['textureParameterName'])
        default = ue.load_asset(self.spec['signs']['Shoes']['texture'])
        if default is not None:
            sampler.set_editor_property('texture', default)
        record['connectReturned'] = {
            'baseColor': bool(ml.connect_material_property(sampler, 'RGB', ue.MaterialProperty.MP_BASE_COLOR))}
        for prop_name, value, prop, y in (('metallic', cfg['constants']['metallic'],
                                           ue.MaterialProperty.MP_METALLIC, 220),
                                          ('roughness', cfg['constants']['roughness'],
                                           ue.MaterialProperty.MP_ROUGHNESS, 340)):
            const = ml.create_material_expression(material, ue.MaterialExpressionConstant, -420, y)
            const.set_editor_property('r', value)
            record['connectReturned'][prop_name] = bool(ml.connect_material_property(const, '', prop))
        ml.recompile_material(material)
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for the sign face material')
        reloaded = ue.load_asset(path)
        record['savedInputReadback'] = {n: self._read_input_expression(reloaded, n)[1]
                                        for n in ('base_color', 'metallic', 'roughness')}
        verifiable = [n for n, s in record['savedInputReadback'].items() if s != 'property_not_reflected']
        record['inputsVerifiable'] = verifiable
        if verifiable and record['savedInputReadback'].get('base_color') != 'connected':
            raise RuntimeError('Sign face BaseColor did not read back as connected: %r'
                               % record['savedInputReadback'])
        record.update({'created': True, 'reused': False, 'uassetSha256': _uasset_sha(material),
                       'verifiedBy': 'readback of the saved material inputs, not the setter return value'})
        self.receipt['materials']['sign_face_parent'] = record
        self.receipt['created'].append(path)
        return material

    def import_sign_textures(self):
        ue = self.ue
        source = self.spec['source']
        settings = self.spec['importSettings']['textureSettings']
        out = {}
        for name, record in sorted(self.spec['signs'].items()):
            path = ROOT / source['signFolder'] / record['file']
            if sha256_of(path) != record['sha256']:
                raise RuntimeError('Frozen sign PNG hash changed: ' + record['file'])
            asset_path = record['texture']
            if self.assets.does_asset_exist(asset_path):
                texture = ue.load_asset(asset_path)
                created = False
            else:
                task = ue.AssetImportTask()
                for key, value in dict(filename=str(path), destination_path=source['textureFolder'],
                                       destination_name=asset_path.rsplit('/', 1)[1], automated=True,
                                       async_=False, replace_existing=False, save=False,
                                       factory=ue.TextureFactory()).items():
                    task.set_editor_property(key, value)
                ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                objects = list(task.get_objects())
                if len(objects) != 1 or not isinstance(objects[0], ue.Texture2D):
                    raise RuntimeError('Import of %s produced %s'
                                       % (record['file'], [type(o).__name__ for o in objects]))
                texture = objects[0]
                created = True
            if not isinstance(texture, ue.Texture2D):
                raise RuntimeError('Sign texture is not a Texture2D: ' + asset_path)
            texture.set_editor_property('srgb', settings['srgb'])
            if not self.assets.save_loaded_asset(texture, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + asset_path)
            # readback, not the setter's word for it
            observed_srgb = bool(texture.get_editor_property('srgb'))
            if observed_srgb != settings['srgb']:
                raise RuntimeError('sRGB did not read back on %s' % asset_path)
            self.receipt['textures'][name] = {
                'asset': _asset_path(texture), 'file': str(path), 'created': created,
                'srgbReadback': observed_srgb,
                'sizeXReadback': int(texture.blueprint_get_size_x()),
                'sizeYReadback': int(texture.blueprint_get_size_y()),
                'expectedSizePx': [record['widthPx'], record['heightPx']],
                'claim': record['claim'], 'says': record['says'],
                'uassetSha256': _uasset_sha(texture)}
            if created:
                self.receipt['created'].append(_asset_path(texture))
            out[name] = texture
        return out

    def sign_instances(self, parent, textures):
        """One MaterialInstanceConstant per sign, verified by parameter readback."""
        ue = self.ue
        cfg = self.spec['materials']['signFaceMaterial']
        ml = ue.MaterialEditingLibrary
        out = {}
        for name, record in sorted(self.spec['signs'].items()):
            path = record['materialInstance']
            if self.assets.does_asset_exist(path):
                instance = ue.load_asset(path)
                created = False
            else:
                folder, asset_name = path.rsplit('/', 1)
                instance = ue.AssetToolsHelpers.get_asset_tools().create_asset(
                    asset_name, folder, ue.MaterialInstanceConstant,
                    ue.MaterialInstanceConstantFactoryNew())
                created = True
            if not isinstance(instance, ue.MaterialInstanceConstant):
                raise RuntimeError('Sign material instance creation failed: ' + path)
            instance.set_editor_property('parent', parent)
            set_returned = bool(ml.set_material_instance_texture_parameter_value(
                instance, cfg['textureParameterName'], textures[name]))
            if not self.assets.save_loaded_asset(instance, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + path)
            reloaded = ue.load_asset(path)
            observed = ml.get_material_instance_texture_parameter_value(
                reloaded, cfg['textureParameterName'])
            observed_path = _asset_path(observed)
            self.receipt['signMaterials'][name] = {
                'asset': path, 'created': created,
                'parentReadback': _asset_path(reloaded.get_editor_property('parent')),
                'setterReturned': set_returned,
                'textureParameterReadback': observed_path,
                'expectedTexture': record['texture'],
                'verifiedBy': ('get_material_instance_texture_parameter_value on the reloaded '
                               'asset. The setter return value is recorded only: in UE 5.8 it can '
                               'be False on a call that took.'),
                'claim': record['claim']}
            if observed_path != record['texture']:
                raise RuntimeError('Sign texture parameter did not read back on %s: %r'
                                   % (path, observed_path))
            if created:
                self.receipt['created'].append(path)
            out[name] = instance
        return out

    def import_meshes(self):
        ue = self.ue
        spec, source = self.spec, self.spec['source']
        settings = spec['importSettings']
        tolerance = spec['verification']['localBoundsToleranceCm']
        out = {}
        for key, record in sorted(spec['meshes'].items()):
            path = ROOT / source['folder'] / record['file']
            if sha256_of(path) != record['sha256']:
                raise RuntimeError('Frozen OBJ hash changed: ' + record['file'])
            asset_path = record['asset']
            if self.assets.does_asset_exist(asset_path):
                mesh = ue.load_asset(asset_path)
                created = False
            else:
                ui = ue.FbxImportUI()
                for k, v in settings['fbxImportUI'].items():
                    ui.set_editor_property(k, getattr(ue.FBXImportType, v) if k == 'mesh_type_to_import' else v)
                data = ui.get_editor_property('static_mesh_import_data')
                for k, v in settings['staticMeshImportData'].items():
                    data.set_editor_property(k, getattr(ue.FBXNormalImportMethod, v)
                                             if k == 'normal_import_method' else v)
                task = ue.AssetImportTask()
                for k, v in dict(filename=str(path), destination_path=source['meshFolder'],
                                 destination_name=record['name'], automated=True, async_=False,
                                 replace_existing=False, save=False, options=ui,
                                 factory=ue.FbxFactory()).items():
                    task.set_editor_property(k, v)
                ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                objects = list(task.get_objects())
                if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
                    raise RuntimeError('Import of %s produced %s'
                                       % (record['file'], [type(o).__name__ for o in objects]))
                mesh = objects[0]
                created = True
            if not isinstance(mesh, ue.StaticMesh):
                raise RuntimeError('Mesh missing or not a StaticMesh: ' + asset_path)

            # Nanite must be OFF before any triangle count is believed: with Nanite on,
            # get_num_triangles(0) returns the FALLBACK count, not the real one.
            nanite = mesh.get_editor_property('nanite_settings')
            nanite_enabled = bool(nanite.get_editor_property('enabled'))
            if nanite_enabled:
                raise RuntimeError('Nanite is enabled on %s; triangle counts would be the '
                                   'fallback mesh, not the real geometry' % asset_path)
            triangles = mesh.get_num_triangles(0)
            box = _static_mesh_box(mesh)
            bounds_error = box_error(box, record['localBoundsCm'])

            material = self.materials.get(record['role'])
            slots = len(mesh.get_editor_property('static_materials'))
            assigned = []
            if material is not None:
                for slot in range(slots):
                    mesh.set_material(slot, material)
                assigned = [_asset_path(mesh.get_material(s)) for s in range(slots)]
            if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + record['name'])

            info = {'asset': _asset_path(mesh), 'file': str(path), 'created': created,
                    'role': record['role'], 'naniteEnabled': nanite_enabled,
                    'trianglesReadback': triangles, 'trianglesExpected': record['triangles'],
                    'trianglesMatch': triangles == record['triangles'],
                    'vertices': mesh.get_num_vertices(0),
                    'localBoundsReadback': box, 'localBoundsExpected': record['localBoundsCm'],
                    'localBoundsErrorCm': round(bounds_error, 5),
                    'materialSlots': slots,
                    'materialAssignedReadback': assigned,
                    'materialVerifiedBy': ('mesh.get_material(slot) readback; set_material\'s '
                                           'return value is not trusted'),
                    'uassetSha256': _uasset_sha(mesh)}
            self.receipt['meshes'][key] = info
            if not info['trianglesMatch']:
                raise RuntimeError('Triangle count for %s is %d, manifest says %d'
                                   % (key, triangles, record['triangles']))
            if bounds_error > tolerance:
                raise RuntimeError('Local bounds for %s differ by %.5f cm' % (key, bounds_error))
            if material is not None and any(a != _asset_path(material) for a in assigned):
                raise RuntimeError('Material slots did not read back on %s: %r' % (key, assigned))
            if created:
                self.receipt['created'].append(_asset_path(mesh))
            out[key] = mesh
        return out

    # -- spawning ----------------------------------------------------------
    def spawn(self, meshes, plan):
        """Spawn one planned element AT ITS FINAL TRANSFORM.

        A static-mobility actor does not dirty its package on a transform change, so nothing here
        moves an actor after the fact: the transform goes into spawn_actor_from_object, and a pose
        that comes back wrong is destroyed and re-spawned by the caller, never nudged.
        """
        ue = self.ue
        spec = self.spec
        mesh = meshes[plan['meshKey']]
        actor = self.actors_sub.spawn_actor_from_class(
            ue.StaticMeshActor, ue.Vector(*plan['location']),
            ue.Rotator(pitch=plan['rotation']['pitch'], yaw=plan['rotation']['yaw'],
                       roll=plan['rotation']['roll']), transient=False)
        if actor is None:
            raise RuntimeError('StaticMeshActor spawn returned None for ' + plan['label'])
        actor.set_actor_label(plan['label'])
        actor.set_folder_path(plan['folder'])
        actor.set_editor_property('tags', [ue.Name(spec['actorTag']),
                                           ue.Name('GateSecurity_' + plan['gate'])])
        component = actor.get_component_by_class(ue.StaticMeshComponent)
        if component is None:
            raise RuntimeError('Spawned actor has no StaticMeshComponent: ' + plan['label'])
        if not component.set_static_mesh(mesh):
            raise RuntimeError('set_static_mesh returned False for ' + plan['label'])
        if _asset_path(component.get_editor_property('static_mesh')) != _asset_path(mesh):
            raise RuntimeError('Static mesh readback differs for ' + plan['label'])
        component.set_collision_profile_name('NoCollision')
        component.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        record = dict(plan)
        record['actor'] = actor
        record['kind'] = 'StaticMeshActor'

        # the sign artwork is a PER-ACTOR component override, because the same face mesh
        # carries three different sign faces; verified by component.get_material readback.
        if plan['sign']:
            instance = self.sign_materials[plan['sign']]
            slots = component.get_num_materials()
            for slot in range(slots):
                component.set_material(slot, instance)
            observed = [_asset_path(component.get_material(s)) for s in range(slots)]
            record['signMaterial'] = {
                'sign': plan['sign'], 'instance': _asset_path(instance),
                'componentMaterialReadback': observed,
                'verifiedBy': 'component.get_material readback, not the setter return value'}
            if slots == 0 or any(o != _asset_path(instance) for o in observed):
                raise RuntimeError('Sign material did not read back on %s: %r'
                                   % (plan['label'], observed))
        return record

    def place_gate(self, gate_key, meshes):
        spec = self.spec
        confirmation = self.confirm_gate(gate_key)
        planned = plan_gate(spec, gate_key)
        clashes = self_intersections(planned, spec['verification']['selfIntersectionToleranceCm'])
        if clashes:
            raise OmissionError('gate %s: planned elements interpenetrate' % gate_key,
                                {'clashes': clashes[:8]})
        spawned = []
        try:
            for plan in planned:
                spawned.append(self.spawn(meshes, plan))
            tolerance = spec['verification']['staticBoundsToleranceCm']
            pose_tolerance = spec['verification']['transformToleranceCm']
            for record in spawned:
                pose = _actor_pose(record['actor'])
                close, error = _pose_close(pose, record['location'], record['rotation'],
                                           record['scale'], pose_tolerance)
                record['poseErrorCm'] = error
                if not close:
                    raise OmissionError('gate %s: %s spawned at the wrong pose (%.5f cm)'
                                        % (gate_key, record['label'], error), {'pose': pose})
                observed = _actor_bounds(record['actor'])
                record['spawnedWorldBoundsCm'] = observed
                record['boundsErrorCm'] = round(box_error(observed, record['plannedWorldBoundsCm']), 5)
                if record['boundsErrorCm'] > tolerance:
                    raise OmissionError('gate %s: %s bounds differ by %.5f cm'
                                        % (gate_key, record['label'], record['boundsErrorCm']),
                                        {'observed': observed,
                                         'planned': record['plannedWorldBoundsCm']})
        except Exception:
            for record in spawned:
                try:
                    self.actors_sub.destroy_actor(record['actor'])
                except Exception:  # noqa: BLE001
                    pass
            raise
        return {'gate': gate_key, 'confirmation': confirmation, 'actors': spawned,
                'actorCount': len(spawned),
                'triangles': sum(p['triangles'] for p in planned)}


def _strip(record):
    return {k: v for k, v in record.items() if k != 'actor'}


def run(gates=GATE_ORDER, import_only=False, load_target=True, allow_unverified_winding=False):
    """Guarded import and placement. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    gates = normalise_gates(gates)
    spec = load_spec()
    offline = offline_check(spec)
    if not offline['passed']:
        raise RuntimeError('Offline check failed: %s' % offline['problems'][:6])
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())

    run_state = GateSecurity(ue, spec)
    if run_state.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target:
        if not run_state.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
    run_state.world = run_state.editor.get_editor_world()
    loaded = run_state.world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the target map %s' % (loaded, TARGET))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
            ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
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
    run_state.receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if run_state.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run_state.receipt_path))
    run_state.receipt = {
        'status': 'gate_security_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'sourceTable': spec['sourceTable'],
        'claimSummary': spec['claimSummary'],
        'westGate': spec['westGate'],
        'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'gatesRequested': list(gates),
        'importOnly': bool(import_only),
        'zombieEditorCheckAtStart': _zombie_editors(),
        'created': [],
        'materials': {},
        'textures': {},
        'signMaterials': {},
        'meshes': {},
        'placed': {},
        'omissions': {},
        'errors': [],
        'mapSaved': False,
        'limitations': list(spec['limitations']),
    }
    run_state.write_receipt()

    saved = False
    try:
        # ---- assets first: nothing touches the map until every asset verifies ----
        for role in spec['materials']['roles']:
            if role != 'sign_face':
                run_state.materials[role] = run_state.pick_material(role)
        textures = run_state.import_sign_textures()
        parent = run_state.sign_face_parent()
        run_state.sign_materials = run_state.sign_instances(parent, textures)
        run_state.materials['sign_face'] = parent
        meshes = run_state.import_meshes()
        run_state.receipt['windingCheck'] = {
            'status': 'offline_proof_only',
            'note': spec['windingCheck']['requireForPlacementNote'],
            'offlineEvidence': ('create_gate_security.py asserts every part closed and positively '
                                'oriented before writing, and readback() re-derives the signed '
                                'volume from the written OBJ; see geometry-manifest.json.'),
            'allowUnverifiedWinding': bool(allow_unverified_winding)}
        run_state.write_receipt()

        if import_only:
            run_state.receipt['status'] = 'assets_imported_map_unchanged'
            return run_state.receipt

        # ---- the map ----
        run_state.take_snapshot()
        run_state.receipt['loadChurnProbe'] = run_state.probe_load_churn()
        run_state.receipt['baselineExclusions'] = run_state.baseline_exclusions(run_state.snapshot)
        baseline_rows = list(run_state.snapshot)
        baseline = run_state.numeric_baseline(baseline_rows)
        label_prefix = spec['labelPrefix'] + spec['group'] + '_'
        pre_existing = [row for row in run_state.snapshot
                        if row['label'].startswith(label_prefix)
                        or row['folder'].startswith(spec['folderPrefix'] + spec['group'])]
        run_state.receipt['preExistingGateSecurityActors'] = [
            {'label': r['label'], 'name': r['name'], 'folder': r['folder']} for r in pre_existing]
        clashes = [r['label'] for r in pre_existing
                   if any(r['label'].startswith(label_prefix + spec['gates'][g]['short'] + '_')
                          for g in gates)]
        if clashes:
            raise RuntimeError('Existing GateSecurity actors of a requested gate preserved; '
                               'refusing duplicate placement: %s' % clashes[:10])

        results = {}
        for gate_key in gates:
            try:
                results[gate_key] = run_state.place_gate(gate_key, meshes)
                run_state.receipt['placed'][gate_key] = dict(
                    results[gate_key], actors=[_strip(r) for r in results[gate_key]['actors']])
            except OmissionError as omission:
                run_state.receipt['omissions'][gate_key] = {'reason': str(omission),
                                                            'evidence': omission.evidence}
            except Exception as error:  # noqa: BLE001
                run_state.receipt['omissions'][gate_key] = {
                    'reason': 'validation_or_api_failure: ' + str(error)}
                run_state.receipt['errors'].append({'gate': gate_key, 'error': repr(error)})
            run_state.write_receipt()

        placed_records = [r for result in results.values() for r in result['actors']]
        if not placed_records:
            run_state.receipt['status'] = 'nothing_placed_map_unchanged'
            return run_state.receipt

        current_rows = run_state.take_snapshot()
        current = run_state.numeric_baseline(current_rows)
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            run_state.receipt['baselineDiffBeforeSave'] = run_state.diff(baseline_rows, current_rows)
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])

        run_state.receipt['zombieEditorCheckBeforeSave'] = _zombie_editors()
        if not run_state.levels.save_current_level():
            run_state.receipt['zombieEditorCheckAfterFailedSave'] = _zombie_editors()
            raise RuntimeError('save_current_level returned False (see the zombie editor check '
                               'in the receipt before believing the save really failed)')
        saved = True
        run_state.receipt['mapSaved'] = True
        run_state.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run_state.write_receipt()

        if not run_state.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run_state.world = run_state.editor.get_editor_world()
        reopened = run_state.take_snapshot()
        reopened_numeric = run_state.numeric_baseline(reopened)
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            run_state.receipt['baselineDiffAfterReopen'] = run_state.diff(baseline_rows, reopened)
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])

        verify = spec['verification']
        readback = []
        for record in placed_records:
            matching = [row for row in reopened if row['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d'
                                   % (record['label'], len(matching)))
            row = matching[0]
            entry = {'label': record['label'], 'gate': record['gate'], 'folder': row['folder'],
                     'meshPath': row['meshes'], 'pose': row['pose'],
                     'worldBoundsCm': row['bounds'], 'sign': record['sign']}
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            close, error = _pose_close(row['pose'], record['location'], record['rotation'],
                                       record['scale'], verify['transformToleranceCm'])
            entry['poseErrorCm'] = error
            if not close:
                raise RuntimeError('Reopened transform differs for %s by %.5f'
                                   % (record['label'], error))
            entry['boundsErrorCm'] = box_error(row['bounds'], record['plannedWorldBoundsCm'])
            if entry['boundsErrorCm'] > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened bounds differ for %s by %.5f'
                                   % (record['label'], entry['boundsErrorCm']))
            component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
            entry['collisionProfile'] = str(component.get_collision_profile_name())
            if record['sign']:
                observed = [_asset_path(component.get_material(s))
                            for s in range(component.get_num_materials())]
                entry['signMaterialReadback'] = observed
                expected = spec['signs'][record['sign']]['materialInstance']
                if not observed or any(o != expected for o in observed):
                    raise RuntimeError('Reopened sign material differs for %s: %r'
                                       % (record['label'], observed))
            readback.append(entry)
        run_state.receipt['reopenedReadback'] = readback
        run_state.receipt['status'] = ('gate_security_saved_reopened_'
                                       'visual_runtime_acceptance_pending')
        return run_state.receipt
    except Exception as error:  # noqa: BLE001
        run_state.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        run_state.receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                                       else 'failed_before_save_map_unchanged')
        raise
    finally:
        run_state.receipt['mapSha256After'] = sha256_of(map_file)
        run_state.receipt['mapBytesChanged'] = run_state.receipt['mapSha256After'] != map_sha_before
        run_state.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
        run_state.receipt['placedActorCount'] = sum(
            g['actorCount'] for g in run_state.receipt['placed'].values())
        run_state.write_receipt()


def verify_in_place(gates=GATE_ORDER, load_target=True):
    """READ-ONLY. Load the map, find every RELEASE_GateSecurity_* actor the spec plans, and
    read it back numerically against the plan: mesh path, pose, world bounds, sign material
    override, collision profile. Also re-confirms the gate anchors. No checkpoint, no spawn,
    no save. Writes a receipt and raises if anything planned is missing or different."""
    import unreal as ue
    gates = normalise_gates(gates)
    spec = load_spec()
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    run_state = GateSecurity(ue, spec)
    if run_state.editor.get_game_world():
        raise RuntimeError('A game world is active')
    if load_target and not run_state.levels.load_level(TARGET):
        raise RuntimeError('load_level failed for ' + TARGET)
    run_state.world = run_state.editor.get_editor_world()
    if run_state.world.get_outermost().get_name() != TARGET:
        raise RuntimeError('Loaded world is not the target map')
    map_file = disk_path(TARGET, 'umap')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT / spec['receiptFolder']
    folder.mkdir(parents=True, exist_ok=True)
    run_state.receipt_path = folder / (spec['receiptPrefix'] + 'verify-' + stamp + '.json')
    run_state.receipt = {'status': 'verify_started', 'mode': 'read_only_verify', 'stamp': stamp,
                         'map': TARGET, 'mapSha256': sha256_of(map_file), 'specSha256': sha256_of(SPEC_PATH),
                         'gatesRequested': list(gates), 'gates': {}, 'problems': [], 'mapSaved': False}
    run_state.write_receipt()
    verify = spec['verification']
    try:
        rows = run_state.take_snapshot()
        by_label = {}
        for row in rows:
            by_label.setdefault(row['label'], []).append(row)
        total_ok = 0
        for gate_key in gates:
            entry = {'anchors': None, 'actors': [], 'problems': []}
            try:
                entry['anchors'] = run_state.confirm_gate(gate_key)
            except OmissionError as omission:
                entry['problems'].append('anchor: %s' % omission)
            for plan in plan_gate(spec, gate_key):
                found = by_label.get(plan['label'], [])
                rec = {'label': plan['label'], 'found': len(found)}
                if len(found) != 1:
                    rec['problem'] = 'expected exactly one actor, found %d' % len(found)
                    entry['problems'].append(rec['problem'] + ': ' + plan['label'])
                    entry['actors'].append(rec)
                    continue
                row = found[0]
                rec.update({'meshPath': row['meshes'], 'pose': row['pose'], 'worldBoundsCm': row['bounds'],
                            'folder': row['folder'], 'class': row['class']})
                if row['meshes'] != [plan['mesh']]:
                    rec['problem'] = 'mesh differs'
                close, err = _pose_close(row['pose'], plan['location'], plan['rotation'], plan['scale'],
                                         verify['transformToleranceCm'])
                rec['poseErrorCm'] = err
                if not close:
                    rec['problem'] = 'pose differs by %.5f cm' % err
                rec['boundsErrorCm'] = round(box_error(row['bounds'], plan['plannedWorldBoundsCm']), 5)
                if rec['boundsErrorCm'] > verify['staticBoundsToleranceCm']:
                    rec['problem'] = 'bounds differ by %.5f cm' % rec['boundsErrorCm']
                component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
                rec['collisionProfile'] = str(component.get_collision_profile_name())
                if plan['sign']:
                    observed = [_asset_path(component.get_material(k)) for k in range(component.get_num_materials())]
                    rec['signMaterialReadback'] = observed
                    expected = spec['signs'][plan['sign']]['materialInstance']
                    if not observed or any(o != expected for o in observed):
                        rec['problem'] = 'sign material differs: %r' % observed
                if 'problem' in rec:
                    entry['problems'].append(rec['problem'] + ': ' + plan['label'])
                else:
                    total_ok += 1
                entry['actors'].append(rec)
            entry['verified'] = sum(1 for a in entry['actors'] if 'problem' not in a and a['found'] == 1)
            entry['planned'] = len(entry['actors'])
            run_state.receipt['gates'][gate_key] = entry
            run_state.receipt['problems'] += entry['problems']
            run_state.write_receipt()
        run_state.receipt['verifiedActorCount'] = total_ok
        run_state.receipt['plannedActorCount'] = sum(g['planned'] for g in run_state.receipt['gates'].values())
        run_state.receipt['status'] = ('gate_security_verified_in_place' if not run_state.receipt['problems']
                                       else 'gate_security_verify_failed')
        if run_state.receipt['problems']:
            raise RuntimeError('verify: %d problem(s): %s' % (len(run_state.receipt['problems']),
                                                            run_state.receipt['problems'][:5]))
        return run_state.receipt
    finally:
        run_state.receipt['mapSha256After'] = sha256_of(map_file)
        run_state.receipt['mapBytesChanged'] = run_state.receipt['mapSha256After'] != run_state.receipt['mapSha256']
        run_state.write_receipt()


# ==========================================================================
# Entry points
# ==========================================================================

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
    return 'release_gate_security.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    gates = GATE_ORDER
    verify_only = '-gatesecurityverifyonly' in command_line
    import_only = '-gatesecurityimportonly' in command_line
    allow_unverified = '-gatesecurityallowunverifiedwinding' in command_line
    for token in command_line.split():
        if token.startswith('-gatesecuritygates='):
            gates = normalise_gates(token.split('=', 1)[1].strip('"'))
    try:
        if verify_only:
            receipt = verify_in_place(gates=gates)
            ue.log('release_gate_security VERIFY: %s verified %s of %s planned'
                   % (receipt['status'], receipt.get('verifiedActorCount'), receipt.get('plannedActorCount')))
            return
        receipt = run(gates=gates, import_only=import_only,
                      allow_unverified_winding=allow_unverified)
        ue.log('release_gate_security: %s gates %s placed %s omitted %s'
               % (receipt['status'], list(gates), receipt.get('placedActorCount'),
                  list(receipt.get('omissions') or {})))
    except Exception as error:  # noqa: BLE001
        ue.log_error('release_gate_security failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    elif '--write-spec' in sys.argv:
        written = write_spec()
        print('wrote %s (%d meshes, %d signs, %d gates, %d actors per gate)'
              % (SPEC_PATH, len(written['meshes']), len(written['signs']),
                 len(written['gates']), written['assembly']['elementsPerGate']))
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

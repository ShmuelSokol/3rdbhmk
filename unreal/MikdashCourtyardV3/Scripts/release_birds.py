"""Guarded native import of the BirdsV1 pose meshes and placement of the ambient bird flocks.

Every number a human should review before this runs lives in Scripts/release_birds.spec.json;
the per-mesh geometry facts live in SourceAssets/birds-review/BirdsV1/geometry-manifest.json,
which the spec pins by hash. Nothing numeric is duplicated between the two.

WHAT IT DOES, IN ORDER
  1. Offline checks, no engine: the manifest hash and status; every OBJ present with the exact
     bytes the manifest recorded; four poses per species in MikdashFlock::PoseIndex order; and
     the flock plan itself - every perch point inside its own flock cylinder, no two perches of
     one flock closer than that species' hard separation, no two flocks of the SAME species
     sitting on top of one another, and every budget and distance in a sane order.
  2. Guards: right project, no running game world, no dirty packages, a FRESH compiled plugin
     (unreal.MikdashBirdFlock and unreal.MikdashBirdSpecies both present), the target map not on
     the protected list.
  3. Checkpoints the target .umap to <checkpointRoot>/Birds-<stamp>/ and verifies the copy hash.
  4. Imports the twenty OBJs into /Game/MikdashV3/BirdsV1/Meshes through the reviewed legacy OBJ
     adapter path, verifying reflected bounds and triangle counts against the manifest, then
     saves each asset. NO MATERIAL IS CREATED OR ASSIGNED - see the honesty list.
  5. Resolves each flock's perch anchor against the LOADED LEVEL: the outer-court wall top, the
     Kotel face, the Old City block roof. Where the named actor is found its measured bounds
     replace the authored height and every perch XY is checked to lie inside it; where it is
     not found the authored points are written unchanged and the receipt says which happened.
  6. Spawns one AMikdashBirdFlock per flock, writes every property and READS EACH ONE BACK
     immediately; makes the actor build the flock once so its OWN seeding and perch resolver
     confirm the counts, then CLEARS those instances so nothing transient is serialised into the
     .umap; saves, reopens the map and reads every value back a second time numerically.
  7. Writes SourceAssets/birds-review/BirdsV1/native-birds-<stamp>.json at start, on failure,
     and in finally.

AUDIO IS NOT MINE. This script creates, imports, loads and assigns NO audio asset of any kind.
The hook for the separately-owned soundscape work is on the actor:
    delegate        AMikdashBirdFlock::OnBirdSound  (BlueprintAssignable)
                    (EventName, SpeciesName, WorldLocationCm, Intensity)
    named function  AMikdashBirdFlock::EmitBirdSound(EventName, WorldLocationCm, Intensity)
    events          "Call", "Wingburst", "Startle", "Land"
bAnnounceBirdSounds is written True on every flock, so the delegate fires from the first frame
and the audio work only has to bind to it.

5.8 PITFALLS THIS SCRIPT HANDLES EXPLICITLY
  * set_editor_property and the material/mesh setters return values that do not reliably mean
    success. NOTHING here trusts a return value: every write is read back, and every readback is
    compared numerically.
  * A static-mobility actor does not dirty its package when only its transform changes. These
    flocks are newly SPAWNED actors, which does dirty the level, but the script still calls
    modify() and asserts the map package is actually dirty before saving, and compares the .umap
    hash before and after - a save that "succeeded" without changing a byte is a failure here.
  * A zombie UnrealEditor process holding the map makes save_current_level() return False with no
    other symptom. If a save fails, CHECK FOR A LEFTOVER UnrealEditor-Cmd.exe BEFORE believing
    it: Scripts/verify.py runs that check first for exactly this reason.

COMMANDLET INVOCATION (serial; never while another native job is running; fresh -abslog path):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_birds.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Birds-01.log"

Engine command-line switches:
  -BirdsImportOnly        import and verify the meshes only; the map is never opened or changed.
  -BirdsPlaceOnly         skip the import; the twenty meshes must already exist (re-verified).
  -BirdsMeshesExist       allow an existing namespace (implies re-verification, not import).
  -BirdsOnly=<keys>       comma-separated flock keys to place (default: all five).
  -BirdsDisabled          write bFlockEnabled False on every flock (placed but inert).

Offline (no engine):  python Scripts/release_birds.py --offline-check
"""
import hashlib
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'Scripts' / 'release_birds.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'

# Mirrored from MikdashFlock::Profile() in
# Plugins/MikdashRuntime/Source/MikdashRuntime/Public/FlockMath.h so an illegal flock plan is
# refused before the engine is ever started. Only the fields the OFFLINE checks need are here;
# the runtime reads the real profile, never this table. The wingspan is repeated so a drift
# between the header and this file shows up as an obviously wrong bird rather than silently.
SPECIES_FACTS = {
    'RockDove':       dict(wingspanCm=67.0,  hardSeparationCm=90.0,   perches=True),
    'CommonSwift':    dict(wingspanCm=45.0,  hardSeparationCm=130.0,  perches=False),
    'HoodedCrow':     dict(wingspanCm=98.0,  hardSeparationCm=220.0,  perches=True),
    'CommonKestrel':  dict(wingspanCm=75.0,  hardSeparationCm=600.0,  perches=False),
    'GriffonVulture': dict(wingspanCm=260.0, hardSeparationCm=1200.0, perches=False),
}
# Manifest species keys -> the EMikdashBirdSpecies name. create_birds.py names its meshes from
# the manifest key; FlockMath.h and the UENUM use the CamelCase name.
MANIFEST_SPECIES = {
    'rock_dove': 'RockDove', 'common_swift': 'CommonSwift', 'hooded_crow': 'HoodedCrow',
    'common_kestrel': 'CommonKestrel', 'griffon_vulture': 'GriffonVulture',
}
POSE_ORDER = ('up_stroke', 'level', 'down_stroke', 'perched')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target map differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


# ==========================================================================================
# Offline checks - the whole plan is validated with no engine running
# ==========================================================================================
def _mesh_name(species_key, pose):
    return 'SM_BirdsV1_%s_%s' % (''.join(p.capitalize() for p in species_key.split('_')),
                                 ''.join(p.capitalize() for p in pose.split('_')))


def _flock_meshes(manifest, species_name):
    """The four pose meshes of one species, in MikdashFlock::PoseIndex order."""
    key = next((k for k, v in MANIFEST_SPECIES.items() if v == species_name), None)
    if key is None:
        raise RuntimeError('Unknown species %r' % species_name)
    ordered = []
    for pose in POSE_ORDER:
        name = _mesh_name(key, pose)
        record = next((m for m in manifest['meshes'] if m['name'] == name), None)
        if record is None:
            raise RuntimeError('Manifest has no mesh %s' % name)
        if record['poseIndex'] != POSE_ORDER.index(pose):
            raise RuntimeError('%s carries poseIndex %d, expected %d'
                               % (name, record['poseIndex'], POSE_ORDER.index(pose)))
        ordered.append(record)
    return ordered


def _perch_report(flock):
    """Every offline fact about one flock's perch points, and the reasons it could be refused."""
    home = flock['homePointCm']
    radius = float(flock['radiusCm'])
    lo, hi = min(flock['floorZCm'], flock['ceilingZCm']), max(flock['floorZCm'], flock['ceilingZCm'])
    hard = SPECIES_FACTS[flock['species']]['hardSeparationCm']
    points = flock['perchPointsCm']
    problems = []
    worst_radial, worst_pair = 0.0, float('inf')
    for index, p in enumerate(points):
        radial = math.hypot(p[0] - home[0], p[1] - home[1])
        worst_radial = max(worst_radial, radial)
        # MikdashFlock::Update clamps every bird to the volume AFTER the step, perched birds
        # included, so a perch outside the volume drags its bird off the ledge every update.
        if radial > radius:
            problems.append('perch %d is %.1f cm from home, outside the %.0f cm radius' % (index, radial, radius))
        if not (lo <= p[2] <= hi):
            problems.append('perch %d Z %.1f is outside the volume %.1f..%.1f' % (index, p[2], lo, hi))
        for other in points[index + 1:]:
            d = math.dist(p, other)
            worst_pair = min(worst_pair, d)
    # AMikdashBirdFlock::ResolvePerches silently DROPS a perch closer than the species hard
    # separation to one already accepted. Dropping is correct at runtime but it must not be how
    # a reviewed plan loses half its ledges, so it is a refusal here.
    if points and worst_pair < hard:
        problems.append('two perches are %.1f cm apart; %s needs %.0f cm and the actor would drop one'
                        % (worst_pair, flock['species'], hard))
    if points and not SPECIES_FACTS[flock['species']]['perches']:
        problems.append('%s never perches (Profile bPerches is false) but %d perch points were authored'
                        % (flock['species'], len(points)))
    return dict(count=len(points), worstRadialCm=round(worst_radial, 3),
                closestPairCm=None if worst_pair == float('inf') else round(worst_pair, 3),
                hardSeparationCm=hard, problems=problems)


def offline_check(spec=None):
    spec = spec or load_spec()
    problems = []
    source = spec['source']

    manifest_path = ROOT / source['manifest']
    if not manifest_path.exists():
        raise RuntimeError('Geometry manifest missing: %s (run Scripts/create_birds.py --export)' % manifest_path)
    manifest_sha = sha(manifest_path)
    if manifest_sha != source['manifestSha256']:
        problems.append('geometry-manifest.json hash %s does not match the pinned %s; the geometry was '
                        're-authored and the spec has not been re-reviewed'
                        % (manifest_sha[:16], source['manifestSha256'][:16]))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if manifest['status'] != source['manifestStatusRequired']:
        problems.append('manifest status %r, expected %r' % (manifest['status'], source['manifestStatusRequired']))
    script_sha = sha(ROOT / source['authoringScript'])
    if script_sha != source['authoringScriptSha256']:
        problems.append('%s hash %s does not match the pinned %s'
                        % (source['authoringScript'], script_sha[:16], source['authoringScriptSha256'][:16]))

    # The pose-distinctness guarantee is a property of the generator, and the manifest records
    # the measurement. If it is absent the geometry predates the check and must be regenerated.
    distinct = manifest.get('poseDistinctness')
    if not distinct:
        problems.append('manifest carries no poseDistinctness block; regenerate with the current '
                        'Scripts/create_birds.py, which fails the export if two poses match')
    else:
        for key, report in distinct.items():
            if report['worstPairCm'] is None or report['worstPairCm'] < report['minimumRequiredCm']:
                problems.append('%s poses are only %r cm apart (needs %r)'
                                % (key, report['worstPairCm'], report['minimumRequiredCm']))

    # Every OBJ present, with the exact bytes the manifest recorded.
    obj_folder = ROOT / source['folder']
    checked = 0
    for record in manifest['meshes']:
        path = obj_folder / record['file']
        if not path.exists():
            problems.append('missing OBJ %s' % record['file'])
            continue
        if sha(path) != record['sha256']:
            problems.append('%s bytes differ from the manifest hash' % record['file'])
        checked += 1
    if len(manifest['meshes']) != 20:
        problems.append('expected 20 meshes (5 species x 4 poses), manifest has %d' % len(manifest['meshes']))

    # Four poses per species, in MikdashFlock::PoseIndex order, and the wingspans agree with the
    # table mirrored from FlockMath.h.
    for manifest_key, species_name in MANIFEST_SPECIES.items():
        try:
            _flock_meshes(manifest, species_name)
        except RuntimeError as exc:
            problems.append(str(exc))
        row = manifest['species'].get(manifest_key)
        if not row:
            problems.append('manifest has no species row for %s' % manifest_key)
        elif abs(row['wingspanCm'] - SPECIES_FACTS[species_name]['wingspanCm']) > 1e-6:
            problems.append('%s wingspan %.1f cm in the manifest, %.1f cm in FlockMath.h'
                            % (species_name, row['wingspanCm'], SPECIES_FACTS[species_name]['wingspanCm']))

    # ---- the flock plan ----------------------------------------------------------------
    flocks = spec['flocks']
    keys = [f['key'] for f in flocks]
    if len(set(keys)) != len(keys):
        problems.append('duplicate flock keys: %r' % keys)
    labels = [f['label'] for f in flocks]
    if len(set(labels)) != len(labels):
        problems.append('duplicate flock labels: %r' % labels)

    perches = {}
    for flock in flocks:
        key = flock['key']
        if flock['species'] not in SPECIES_FACTS:
            problems.append('%s: unknown species %r' % (key, flock['species']))
            continue
        if flock['floorZCm'] >= flock['ceilingZCm']:
            problems.append('%s: floor %.1f is not below ceiling %.1f' % (key, flock['floorZCm'], flock['ceilingZCm']))
        if not 0 < flock['birdCount'] <= flock['maxBirds']:
            problems.append('%s: birdCount %d outside 1..%d' % (key, flock['birdCount'], flock['maxBirds']))
        if not 0 < flock['birdsPerUpdate'] <= flock['birdCount']:
            problems.append('%s: birdsPerUpdate %d outside 1..%d' % (key, flock['birdsPerUpdate'], flock['birdCount']))
        if not (flock['nearUpdateIntervalSeconds'] <= flock['midUpdateIntervalSeconds']
                <= flock['farUpdateIntervalSeconds']):
            problems.append('%s: update intervals are not near <= mid <= far' % key)
        if not (flock['nearDistanceCm'] < flock['midDistanceCm'] < flock['cullRadiusCm']):
            problems.append('%s: distances are not near < mid < cull' % key)
        if flock['radiusCm'] <= 0 or flock['sizeScale'] <= 0:
            problems.append('%s: radius and sizeScale must be positive' % key)
        if flock['softBandCm'] <= 0 or flock['radialSoftBandCm'] <= 0:
            problems.append('%s: soft bands must be positive' % key)
        if abs(flock['homePointCm'][0]) < 1.0 and abs(flock['homePointCm'][1]) < 1.0 \
                and abs(flock['homePointCm'][2]) < 1.0:
            # A near-zero HomePointCm means "use the actor location" to the actor; the plan must
            # never rely on that accidentally.
            problems.append('%s: homePointCm is near zero, which the actor reads as "use my own location"' % key)
        report = _perch_report(flock)
        perches[key] = report
        problems.extend('%s: %s' % (key, p) for p in report['problems'])

        # The authored perch points must lie inside the bounds the discovery rule expects, or
        # the run-time check would reject every one of them.
        discovery = flock.get('perchDiscovery')
        if discovery and flock['perchPointsCm']:
            box = discovery['expectedBoundsCm']
            for index, p in enumerate(flock['perchPointsCm']):
                if not (box['min'][0] <= p[0] <= box['max'][0] and box['min'][1] <= p[1] <= box['max'][1]):
                    problems.append('%s: perch %d XY is outside the expected anchor bounds' % (key, index))
            expected_z = discovery['expectedTopZCm']
            lifts = {round(p[2] - expected_z, 3) for p in flock['perchPointsCm']}
            if len(lifts) != 1 or next(iter(lifts)) <= 0:
                problems.append('%s: perch heights are not one consistent positive lift above %.3f'
                                % (key, expected_z))

    # Two flocks of the same bird in the same place read as one flock at double density.
    minimum = spec['verification']['sameSpeciesMinHomeDistanceCm']
    for i, a in enumerate(flocks):
        for b in flocks[i + 1:]:
            if a['species'] != b['species']:
                continue
            if max(a['floorZCm'], b['floorZCm']) >= min(a['ceilingZCm'], b['ceilingZCm']):
                continue                                    # Z ranges do not overlap at all
            d = math.dist(a['homePointCm'][:2] + [0.0], b['homePointCm'][:2] + [0.0])
            if d < minimum:
                problems.append('%s and %s are both %s with overlapping Z and homes only %.0f cm apart'
                                % (a['key'], b['key'], a['species'], d))

    result = dict(status='offline_ok' if not problems else 'offline_failed',
                  manifestSha256=manifest_sha, objFilesChecked=checked,
                  meshCount=len(manifest['meshes']), totalTriangles=manifest['totalTriangles'],
                  poseDistinctnessWorstCm={k: v['worstPairCm'] for k, v in (distinct or {}).items()},
                  flocks={f['key']: dict(species=f['species'], birds=f['birdCount'],
                                         perches=perches.get(f['key'], {}).get('count', 0),
                                         homePointCm=f['homePointCm'], radiusCm=f['radiusCm'])
                          for f in flocks},
                  perchReports=perches, problems=problems)
    if problems:
        raise RuntimeError('Offline checks failed:\n  ' + '\n  '.join(problems))
    return result


# ==========================================================================================
# Native helpers
# ==========================================================================================
def _switch(name):
    import unreal as ue
    return bool(ue.SystemLibrary.parse_param(ue.SystemLibrary.get_command_line(), name))


def _switch_value(name):
    import unreal as ue
    return ue.SystemLibrary.parse_param_value(ue.SystemLibrary.get_command_line(), name)


def _python_property_names(type_object):
    """The real Python names of a UClass's editor properties, taken from the generated
    docstring. Guessing them ('bFlockEnabled' -> ?) is exactly the kind of silent mismatch that
    writes half a flock and reports success."""
    names = set()
    doc = getattr(type_object, '__doc__', '') or ''
    for line in doc.splitlines():
        line = line.strip()
        if line.startswith('- ``'):
            end = line.find('``', 4)
            if end > 4:
                names.add(line[4:end])
    return names


def _resolve_properties(type_object, wanted, label):
    """Map intended CamelCase names to the actual Python names, matching on the letters alone so
    underscore placement and the dropped 'b' of a bool cannot break the write."""
    available = _python_property_names(type_object)
    normal = {name.replace('_', '').lower(): name for name in available}
    mapping, missing = {}, []
    for name in wanted:
        key = name.replace('_', '').lower()
        if key in normal:
            mapping[name] = normal[key]
        else:
            missing.append(name)
    if missing:
        raise RuntimeError('%s is missing %r; it exposes %r' % (label, sorted(missing), sorted(available)))
    return mapping


def _near(a, b, tolerance=1e-2):
    return abs(float(a) - float(b)) <= tolerance


def _set_and_verify(target, name, value, compare=None):
    """set_editor_property return values are not trusted anywhere in this script; every write is
    read back immediately. compare(readback, value) -> bool for values that are not plainly
    equal."""
    target.set_editor_property(name, value)
    got = target.get_editor_property(name)
    ok = compare(got, value) if compare else (got == value)
    if not ok:
        raise RuntimeError('Readback mismatch writing %s: wrote %r, read %r' % (name, value, got))
    return got


def _vectors_match(got, want, tolerance=1e-2):
    got = list(got)
    if len(got) != len(want):
        return False
    for g, w in zip(got, want):
        if not (_near(g.x, w[0], tolerance) and _near(g.y, w[1], tolerance) and _near(g.z, w[2], tolerance)):
            return False
    return True


def _path(asset):
    return asset.get_path_name().split('.')[0] if asset else None


def _folder_path(actor):
    try:
        return str(actor.get_folder_path())
    except Exception:  # noqa: BLE001
        return 'unavailable_in_this_engine_build'


def _species_enum(ue, name):
    """unreal.MikdashBirdSpecies member for an EMikdashBirdSpecies name, resolved rather than
    guessed: the Python name of RockDove could be ROCK_DOVE or ROCKDOVE depending on the
    generator, and a wrong guess would silently place the wrong bird."""
    enum = ue.MikdashBirdSpecies
    key = name.replace('_', '').lower()
    for attribute in dir(enum):
        if attribute.startswith('_'):
            continue
        if attribute.replace('_', '').lower() == key:
            return getattr(enum, attribute)
    raise RuntimeError('unreal.MikdashBirdSpecies has no member matching %r; it has %r'
                       % (name, [a for a in dir(enum) if not a.startswith('_')]))


def _import_mesh(ue, tools, mesh_folder, path, name):
    ui = ue.FbxImportUI()
    for key, value in dict(automated_import_should_detect_type=False,
                           mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
                           import_as_skeletal=False, import_mesh=True, import_animations=False,
                           import_materials=False, import_textures=False,
                           create_physics_asset=False).items():
        ui.set_editor_property(key, value)
    data = ui.get_editor_property('static_mesh_import_data')
    for key, value in dict(combine_meshes=True, transform_vertex_to_absolute=True, bake_pivot_in_vertex=False,
                           convert_scene=False, convert_scene_unit=False, force_front_x_axis=False,
                           import_uniform_scale=1.0, auto_generate_collision=False, build_nanite=False,
                           generate_lightmap_u_vs=False, remove_degenerates=True,
                           normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():
        data.set_editor_property(key, value)
    task = ue.AssetImportTask()
    for key, value in dict(filename=str(path), destination_path=mesh_folder, destination_name=name,
                           automated=True, async_=False, replace_existing=False, save=False,
                           options=ui, factory=ue.FbxFactory()).items():
        task.set_editor_property(key, value)
    tools.import_asset_tasks([task])
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
        raise RuntimeError('OBJ import did not yield exactly one static mesh for ' + name)
    return objects[0]


def _verify_mesh(ue, mesh, record, tolerance):
    """The reflection check: the importer reflects Y back, so the imported bounds must reproduce
    the manifest's canonical bounds. A failed reflection cannot pass this, because every bird is
    strongly asymmetric in X (bill forward, tail back) and symmetric in Y."""
    box = mesh.get_bounding_box()
    actual = {'min': [box.min.x, box.min.y, box.min.z], 'max': [box.max.x, box.max.y, box.max.z]}
    want = record['canonicalBoundsCm']
    error = 0.0
    for side in ('min', 'max'):
        for axis in range(3):
            error = max(error, abs(actual[side][axis] - want[side][axis]))
    nanite = None
    try:
        nanite = bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
    except Exception:  # noqa: BLE001
        nanite = None
    if nanite:
        raise RuntimeError('%s imported with Nanite enabled; get_num_triangles(0) would be the fallback count'
                           % record['name'])
    triangles = mesh.get_num_triangles(0)
    if error > tolerance:
        raise RuntimeError('%s bounds error %.4f cm exceeds %.3f' % (record['name'], error, tolerance))
    if triangles != record['triangles']:
        raise RuntimeError('%s imported %d triangles, expected %d' % (record['name'], triangles, record['triangles']))
    slots = len(list(mesh.get_editor_property('static_materials')))
    if slots != record['materialSlots']:
        raise RuntimeError('%s imported %d material slots, expected %d'
                           % (record['name'], slots, record['materialSlots']))
    return dict(boundsCm=actual, boundsErrorCm=round(error, 6), triangles=triangles,
                materialSlots=slots, naniteEnabled=nanite)


def _actor_bounds(actor):
    """World AABB including NON-COLLIDING components. The ledges this script measures against -
    the Kotel face, the outer envelope walls, the Old City shells - are all placed NoCollision,
    so asking for colliding components only would return zero bounds for every one of them and
    the discovery would silently fall back to the authored numbers with no error anywhere."""
    origin, extent = actor.get_actor_bounds(False)
    return dict(min=[origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
                max=[origin.x + extent.x, origin.y + extent.y, origin.z + extent.z])


def _mesh_paths(actor):
    """Every static mesh asset path on an actor, for matching an actor whose LABEL was never set
    to anything meaningful. Level actors imported in bulk are often labelled by the engine, so
    the asset path is the more reliable identifier of the two."""
    import unreal as ue
    paths = []
    try:
        for component in actor.get_components_by_class(ue.StaticMeshComponent):
            mesh = component.get_editor_property('static_mesh')
            if mesh:
                paths.append(mesh.get_path_name())
    except Exception:  # noqa: BLE001
        pass
    return paths


def _union(boxes):
    return dict(min=[min(b['min'][i] for b in boxes) for i in range(3)],
                max=[max(b['max'][i] for b in boxes) for i in range(3)])


def _resolve_perches(ue, actors, flock):
    """Re-derive one flock's perch points from the level, or keep the authored ones and say so.

    Returns (points, report). The authored points are only ever REPLACED in Z, and only when the
    named anchor actor is actually found and its measured top agrees with the expectation inside
    the spec's tolerance. Any surprise is recorded and the authored points are used unchanged -
    this script never invents a ledge from an actor it did not recognise."""
    authored = [list(p) for p in flock['perchPointsCm']]
    discovery = flock.get('perchDiscovery')
    if not authored:
        return [], dict(source='none', reason='%s has no perch points by design' % flock['key'])
    if not discovery:
        return authored, dict(source='authored_no_discovery_rule')

    method = discovery['method']
    matches = []
    for actor in actors.get_all_level_actors():
        if not actor:
            continue
        label = actor.get_actor_label()
        if method == 'actor_label_exact' and label == discovery['label']:
            matches.append(actor)
        elif method == 'actor_label_prefix_union' and label.startswith(discovery['labelPrefix']):
            matches.append(actor)
        elif method == 'actor_label_substring':
            # The outer envelope union was imported in bulk and its actor LABEL may just be the
            # engine default, so the static mesh asset path is checked too. Mesh path first
            # would be cheaper still, but the label is the identifier the spec quotes.
            if discovery['labelSubstring'] in label or \
                    any(discovery['labelSubstring'] in p for p in _mesh_paths(actor)):
                matches.append(actor)
    if not matches:
        return authored, dict(source='authored_actor_not_found', method=method,
                              looked_for=discovery.get('label') or discovery.get('labelPrefix')
                              or discovery.get('labelSubstring'),
                              note='The named anchor actor is not in this map. The reviewed authored '
                                   'points are written unchanged; their heights come from the receipt '
                                   'named in the spec, not from a measurement made this run.')
    if method == 'actor_label_prefix_union' and len(matches) != discovery.get('expectedActorCount', len(matches)):
        return authored, dict(source='authored_actor_count_mismatch', found=len(matches),
                              expected=discovery['expectedActorCount'],
                              labels=[a.get_actor_label() for a in matches])

    measured = _union([_actor_bounds(a) for a in matches])
    top = measured['max'][2]
    if abs(top - discovery['expectedTopZCm']) > discovery['topZToleranceCm']:
        return authored, dict(source='authored_measured_top_disagrees', measuredTopZCm=round(top, 3),
                              expectedTopZCm=discovery['expectedTopZCm'],
                              toleranceCm=discovery['topZToleranceCm'], measuredBoundsCm=measured,
                              note='The anchor actor exists but is not where the receipt said it was. '
                                   'Rather than move ledges onto an actor this script does not recognise, '
                                   'the authored points are used and this is surfaced.')

    lift = authored[0][2] - discovery['expectedTopZCm']
    outside = []
    resolved = []
    for index, p in enumerate(authored):
        if not (measured['min'][0] <= p[0] <= measured['max'][0]
                and measured['min'][1] <= p[1] <= measured['max'][1]):
            outside.append(index)
        resolved.append([p[0], p[1], top + lift])
    if outside:
        return authored, dict(source='authored_points_outside_measured_bounds', outsideIndices=outside,
                              measuredBoundsCm=measured)
    return resolved, dict(source='measured_from_level', method=method,
                          actors=[a.get_actor_label() for a in matches],
                          measuredBoundsCm=measured, measuredTopZCm=round(top, 3),
                          liftCm=round(lift, 3), shiftCm=round(top - discovery['expectedTopZCm'], 3))


# ==========================================================================================
# The run
# ==========================================================================================
def run():
    import unreal as ue

    spec = load_spec()
    offline = offline_check(spec)
    source = spec['source']
    manifest = json.loads((ROOT / source['manifest']).read_text(encoding='utf-8-sig'))

    # ---- guards ------------------------------------------------------------------------
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project: %s' % ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is running; use a dedicated editor process')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
            ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Unsaved packages present; run on a clean editor')

    flock_class = ue.load_class(None, spec['compiledClassesRequired']['birdFlock'])
    if not flock_class:
        raise RuntimeError('AMikdashBirdFlock is not loaded; compile MikdashRuntime and restart the process')
    for attribute in ('MikdashBirdFlock', spec['compiledClassesRequired']['speciesEnum']):
        if not hasattr(ue, attribute):
            raise RuntimeError('unreal.%s is missing: the loaded MikdashRuntime binary is stale. Compile '
                               'the plugin and restart the editor process.' % attribute)
    props = _resolve_properties(ue.MikdashBirdFlock, [
        'FlockEnabled', 'Species', 'BirdCount', 'HomePointCm', 'RadiusCm', 'CeilingZCm', 'FloorZCm',
        'SoftBandCm', 'RadialSoftBandCm', 'FlockSeed', 'SizeScale', 'PoseMeshes', 'PerchPointsCm',
        'PerchActorTags', 'PerchPointsPerTaggedActor', 'PerchLiftCm', 'NearUpdateIntervalSeconds',
        'MidUpdateIntervalSeconds', 'FarUpdateIntervalSeconds', 'NearDistanceCm', 'MidDistanceCm',
        'CullRadiusCm', 'BirdsPerUpdate', 'MaxBirds', 'AnnounceBirdSounds',
    ], 'MikdashBirdFlock')

    import_only = _switch('BirdsImportOnly')
    place_only = _switch('BirdsPlaceOnly')
    meshes_exist = _switch('BirdsMeshesExist') or place_only
    disabled = _switch('BirdsDisabled')
    only = _switch_value('BirdsOnly')
    wanted_keys = [k.strip() for k in only.split(',') if k.strip()] if only else [f['key'] for f in spec['flocks']]
    unknown = [k for k in wanted_keys if k not in {f['key'] for f in spec['flocks']}]
    if unknown:
        raise RuntimeError('-BirdsOnly= names unknown flocks: %r' % unknown)

    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_dir = ROOT / spec['receiptFolder']
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / (spec['receiptPrefix'] + stamp + '.json')
    map_file = ROOT / spec['targetMapFile']

    receipt = dict(
        status='started', stamp=stamp, map=TARGET, mapFile=str(map_file),
        spec=str(SPEC_PATH.relative_to(ROOT)), specSha256=sha(SPEC_PATH),
        scriptSha256=sha(Path(__file__)), manifestSha256=offline['manifestSha256'],
        engineVersion=ue.SystemLibrary.get_engine_version(),
        offline=offline, mapSha256Before=sha(map_file),
        switches=dict(importOnly=import_only, placeOnly=place_only, meshesExist=meshes_exist,
                      disabled=disabled, only=wanted_keys),
        meshes={}, flocks={}, mapSaved=False,
        audioHook=spec['audioHook'],
        honesty=[
            'Ambient scenery only. No collision on any bird mesh or any flock component; nothing can be '
            'blocked, pushed or traced against a bird. This script never references, loads or modifies '
            'MikdashDovePawn, the player white-dove flight mode.',
            'NO MATERIAL is created or assigned. Plumage is recorded as intent in species.json; until a '
            'material pass runs the ambient rock dove is NOT yet visibly distinct from the player white dove.',
            'NO AUDIO of any kind is created, imported, loaded or assigned. The soundscape hook is a '
            'delegate on the actor and nothing is bound to it here.',
            'Bird counts and volumes are a scenery choice. Nothing here is a census or a claim about how '
            'many birds of any species are over Jerusalem.',
            'Wingspans and body lengths are published field-guide mid-points cited per species in '
            'FlockMath.h and species.json. This project measured no bird.',
            'No PIE, render, cook, packaged run or frame-time measurement on the target GPU is claimed. The '
            'cost figures quoted in the flock notes come from the standalone FlockMathTest, on the build '
            'machine CPU, not from this map.',
        ],
        scope='Native mesh import and map actor placement with save, reopen and numeric readback; no '
              'runtime or visual acceptance.')

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

    write()
    checkpoint = None
    try:
        # ---- meshes --------------------------------------------------------------------
        mesh_folder = spec['meshFolder']
        if assets.does_directory_exist(spec['namespace']) and not meshes_exist:
            raise RuntimeError('Namespace %s exists; pass -BirdsMeshesExist to re-verify instead of importing'
                               % spec['namespace'])
        meshes = {}
        for record in manifest['meshes']:
            asset_path = mesh_folder + '/' + record['name']
            if meshes_exist:
                mesh = ue.load_asset(asset_path)
                if not mesh:
                    raise RuntimeError('Expected existing mesh missing: ' + asset_path)
                imported = False
            else:
                mesh = _import_mesh(ue, tools, mesh_folder,
                                    ROOT / source['folder'] / record['file'], record['name'])
                imported = True
            verified = _verify_mesh(ue, mesh, record, source['boundsToleranceCm'])
            if imported and not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('Mesh save failed: ' + asset_path)
            meshes[record['name']] = mesh
            receipt['meshes'][record['name']] = dict(path=mesh.get_path_name(), imported=imported,
                                                     species=record['species'], pose=record['pose'],
                                                     poseIndex=record['poseIndex'], **verified)
        receipt['status'] = 'meshes_ready'
        write()
        if import_only:
            receipt['status'] = 'import_only_complete_map_unchanged'
            return receipt

        # ---- the map -------------------------------------------------------------------
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            if not levels.load_level(TARGET):
                raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Unexpected editor world after load')
        if TARGET in spec['protectedMaps']:
            raise RuntimeError('Refusing to edit a protected map')

        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'BeforeBirds.umap')
        if sha(checkpoint / 'BeforeBirds.umap') != receipt['mapSha256Before']:
            raise RuntimeError('Checkpoint copy hash mismatch')
        receipt['checkpoint'] = str(checkpoint)
        write()

        existing_labels = {a.get_actor_label() for a in actors.get_all_level_actors() if a}
        clashes = [f['label'] for f in spec['flocks'] if f['key'] in wanted_keys and f['label'] in existing_labels]
        if clashes:
            raise RuntimeError('These flock actors already exist; refusing to place duplicates: %r' % clashes)
        before_actor_count = len(actors.get_all_level_actors())

        placed = []
        for flock in spec['flocks']:
            if flock['key'] not in wanted_keys:
                receipt['flocks'][flock['key']] = dict(status='not_requested')
                continue
            pose_records = _flock_meshes(manifest, flock['species'])
            pose_meshes = [meshes[r['name']] for r in pose_records]
            perch_points, perch_report = _resolve_perches(ue, actors, flock)

            # A perch resolved from the level must still be inside the flock volume; the offline
            # check proved it for the authored heights, and this re-proves it for the measured
            # ones. See verification.perchInsideVolumeRule for why this is fatal and not a warning.
            home = flock['homePointCm']
            lo, hi = min(flock['floorZCm'], flock['ceilingZCm']), max(flock['floorZCm'], flock['ceilingZCm'])
            for index, p in enumerate(perch_points):
                if math.hypot(p[0] - home[0], p[1] - home[1]) > flock['radiusCm'] or not (lo <= p[2] <= hi):
                    raise RuntimeError('%s: resolved perch %d %r is outside the flock volume (%s)'
                                       % (flock['key'], index, [round(v, 2) for v in p], perch_report['source']))

            actor = actors.spawn_actor_from_class(
                flock_class, ue.Vector(*flock['homePointCm']), ue.Rotator(0.0, 0.0, 0.0), transient=False)
            if not actor:
                raise RuntimeError('%s spawn failed' % flock['key'])
            actor.set_actor_label(flock['label'])
            actor.set_folder_path(flock['folder'])
            actor.tags = [ue.Name(spec['actorTag']), ue.Name(flock['key'])]

            _set_and_verify(actor, props['Species'], _species_enum(ue, flock['species']))
            _set_and_verify(actor, props['PoseMeshes'], pose_meshes,
                            compare=lambda got, want: [_path(m) for m in list(got)] == [_path(m) for m in want])
            _set_and_verify(actor, props['BirdCount'], int(flock['birdCount']))
            _set_and_verify(actor, props['MaxBirds'], int(flock['maxBirds']))
            _set_and_verify(actor, props['BirdsPerUpdate'], int(flock['birdsPerUpdate']))
            _set_and_verify(actor, props['FlockSeed'], int(flock['flockSeed']))
            _set_and_verify(actor, props['HomePointCm'], ue.Vector(*flock['homePointCm']),
                            compare=lambda got, want: _vectors_match([got], [[want.x, want.y, want.z]], 1e-3))
            for name, value in (('RadiusCm', flock['radiusCm']), ('CeilingZCm', flock['ceilingZCm']),
                                ('FloorZCm', flock['floorZCm']), ('SoftBandCm', flock['softBandCm']),
                                ('RadialSoftBandCm', flock['radialSoftBandCm']),
                                ('SizeScale', flock['sizeScale']), ('PerchLiftCm', 12.0),
                                ('NearUpdateIntervalSeconds', flock['nearUpdateIntervalSeconds']),
                                ('MidUpdateIntervalSeconds', flock['midUpdateIntervalSeconds']),
                                ('FarUpdateIntervalSeconds', flock['farUpdateIntervalSeconds']),
                                ('NearDistanceCm', flock['nearDistanceCm']),
                                ('MidDistanceCm', flock['midDistanceCm']),
                                ('CullRadiusCm', flock['cullRadiusCm'])):
                _set_and_verify(actor, props[name], float(value), _near)
            _set_and_verify(actor, props['PerchPointsCm'], [ue.Vector(*p) for p in perch_points],
                            compare=lambda got, want: _vectors_match(got, perch_points))
            _set_and_verify(actor, props['PerchActorTags'],
                            [ue.Name(t) for t in flock.get('perchActorTags', [])],
                            compare=lambda got, want: len(list(got)) == len(want))
            _set_and_verify(actor, props['PerchPointsPerTaggedActor'], 8)
            _set_and_verify(actor, props['AnnounceBirdSounds'], bool(flock['announceBirdSounds']))

            # ---- probe: make the actor build the flock ONCE, then clear it -------------
            # This is the only cross-check that the numbers written above actually produce a
            # flock: AMikdashBirdFlock::RebuildFlock seeds the birds and runs its OWN
            # ResolvePerches over the points just written, so the counts it reports back are an
            # independent confirmation of this script's arithmetic - in particular that no perch
            # was silently dropped as a duplicate.
            #
            # The instances are then CLEARED before saving. A HISM instance added in the editor
            # is serialised into the .umap, and BeginPlay rebuilds the flock from scratch, so
            # leaving them would bloat the map with state that is thrown away on the first
            # frame. Clearing is done by rebuilding with bFlockEnabled false, which is the
            # actor's own documented path for it.
            probe = None
            try:
                built = bool(actor.call_method('RebuildFlock'))
                probe = dict(rebuilt=built,
                             liveBirdCount=int(actor.call_method('GetLiveBirdCount')),
                             resolvedPerchCount=int(actor.call_method('GetResolvedPerchCount')),
                             perchSourceStatus=str(actor.call_method('GetPerchSourceStatus')),
                             flockStatus=str(actor.call_method('GetFlockStatus')))
            except Exception as exc:  # noqa: BLE001
                probe = dict(rebuilt=False, unavailable=repr(exc),
                             note='The editor-side probe could not run. The placement itself is '
                                  'still written and read back; only this cross-check is missing.')
            if probe.get('rebuilt'):
                if probe['liveBirdCount'] != flock['birdCount']:
                    raise RuntimeError('%s: the actor built %d birds, not the %d written'
                                       % (flock['key'], probe['liveBirdCount'], flock['birdCount']))
                if probe['resolvedPerchCount'] != len(perch_points):
                    raise RuntimeError('%s: the actor resolved %d perches from the %d written - it drops '
                                       'points closer than the species hard separation, so two ledges '
                                       'collided. %s'
                                       % (flock['key'], probe['resolvedPerchCount'], len(perch_points),
                                          probe['perchSourceStatus']))
            # Clear the instances the probe created, then write the final enabled state.
            actor.set_editor_property(props['FlockEnabled'], False)
            try:
                actor.call_method('RebuildFlock')
            except Exception:  # noqa: BLE001
                pass
            _set_and_verify(actor, props['FlockEnabled'], not disabled)
            probe['instancesClearedBeforeSave'] = True

            actor.modify()
            placed.append((flock, actor, perch_points))
            receipt['flocks'][flock['key']] = dict(
                status='spawned', label=flock['label'], name=actor.get_name(), folder=flock['folder'],
                species=flock['species'], birdCount=flock['birdCount'],
                homePointCm=flock['homePointCm'], radiusCm=flock['radiusCm'],
                floorZCm=flock['floorZCm'], ceilingZCm=flock['ceilingZCm'],
                poseMeshes=[_path(m) for m in pose_meshes],
                perchPointsCm=[[round(v, 3) for v in p] for p in perch_points],
                perchResolution=perch_report,
                placementBasis=flock['placementBasis'],
                editorProbe=probe,
                flockStatus=str(actor.call_method('GetFlockStatus')))
            write()

        after_actor_count = len(actors.get_all_level_actors())
        if after_actor_count != before_actor_count + len(placed):
            raise RuntimeError('Actor count moved by %d, expected exactly %d new actors'
                               % (after_actor_count - before_actor_count, len(placed)))
        receipt['actorCountBefore'] = before_actor_count
        receipt['actorCountAfter'] = after_actor_count

        # A static-mobility actor does not dirty its package for a transform change. These are
        # newly spawned actors so the level MUST be dirty here; if it is not, saving would be a
        # no-op that still returns True.
        dirty = [p.get_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        receipt['dirtyMapPackagesBeforeSave'] = dirty
        if placed and not dirty:
            raise RuntimeError('No map package is dirty after spawning %d actors; a save here would be a '
                               'no-op. Check for a stray UnrealEditor process holding this map.' % len(placed))

        if not levels.save_current_level():
            raise RuntimeError('Level save failed. BEFORE believing this, check for a zombie '
                               'UnrealEditor process holding the map (tasklist /FI "IMAGENAME eq '
                               'UnrealEditor*.exe"); that makes the save return False with no other symptom.')
        receipt['mapSha256AfterSave'] = sha(map_file)
        if receipt['mapSha256AfterSave'] == receipt['mapSha256Before'] and placed:
            raise RuntimeError('save_current_level returned True but the .umap bytes did not change')
        receipt.update(status='saved_reopen_pending', mapSaved=True)
        write()

        # ---- reopen and read every value back ------------------------------------------
        if not levels.load_level(TARGET) or editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Reopen failed')
        by_label = {}
        for actor in actors.get_all_level_actors():
            if actor:
                by_label.setdefault(actor.get_actor_label(), []).append(actor)

        problems = []
        for flock, _spawned, perch_points in placed:
            found = by_label.get(flock['label'], [])
            if len(found) != 1:
                problems.append('%s: %d actors with that label after reopen' % (flock['key'], len(found)))
                continue
            actor = found[0]
            pose_records = _flock_meshes(manifest, flock['species'])
            readback = dict(
                birdCount=int(actor.get_editor_property(props['BirdCount'])),
                birdsPerUpdate=int(actor.get_editor_property(props['BirdsPerUpdate'])),
                flockSeed=int(actor.get_editor_property(props['FlockSeed'])),
                radiusCm=float(actor.get_editor_property(props['RadiusCm'])),
                floorZCm=float(actor.get_editor_property(props['FloorZCm'])),
                ceilingZCm=float(actor.get_editor_property(props['CeilingZCm'])),
                sizeScale=float(actor.get_editor_property(props['SizeScale'])),
                cullRadiusCm=float(actor.get_editor_property(props['CullRadiusCm'])),
                nearUpdateIntervalSeconds=float(actor.get_editor_property(props['NearUpdateIntervalSeconds'])),
                farUpdateIntervalSeconds=float(actor.get_editor_property(props['FarUpdateIntervalSeconds'])),
                flockEnabled=bool(actor.get_editor_property(props['FlockEnabled'])),
                announceBirdSounds=bool(actor.get_editor_property(props['AnnounceBirdSounds'])),
                species=str(actor.get_editor_property(props['Species'])),
                poseMeshes=[_path(m) for m in list(actor.get_editor_property(props['PoseMeshes']))],
                perchCount=len(list(actor.get_editor_property(props['PerchPointsCm']))),
                homePointCm=[actor.get_editor_property(props['HomePointCm']).x,
                             actor.get_editor_property(props['HomePointCm']).y,
                             actor.get_editor_property(props['HomePointCm']).z],
                actorLocationCm=[actor.get_actor_location().x, actor.get_actor_location().y,
                                 actor.get_actor_location().z],
                tags=[str(t) for t in actor.tags],
                # get_folder_path is cosmetic and its presence has moved between engine
                # versions; a missing accessor must not fail an otherwise-good placement, so it
                # is recorded as unavailable rather than raised.
                folder=_folder_path(actor))
            expected_meshes = [spec['meshFolder'] + '/' + r['name'] for r in pose_records]
            if readback['birdCount'] != flock['birdCount']:
                problems.append('%s birdCount %r' % (flock['key'], readback['birdCount']))
            if readback['birdsPerUpdate'] != flock['birdsPerUpdate']:
                problems.append('%s birdsPerUpdate %r' % (flock['key'], readback['birdsPerUpdate']))
            if readback['flockSeed'] != flock['flockSeed']:
                problems.append('%s flockSeed %r' % (flock['key'], readback['flockSeed']))
            if readback['poseMeshes'] != expected_meshes:
                problems.append('%s poseMeshes %r' % (flock['key'], readback['poseMeshes']))
            if readback['perchCount'] != len(perch_points):
                problems.append('%s perchCount %r, expected %d'
                                % (flock['key'], readback['perchCount'], len(perch_points)))
            for name, want in (('radiusCm', flock['radiusCm']), ('floorZCm', flock['floorZCm']),
                               ('ceilingZCm', flock['ceilingZCm']), ('sizeScale', flock['sizeScale']),
                               ('cullRadiusCm', flock['cullRadiusCm'])):
                if not _near(readback[name], want):
                    problems.append('%s %s %r, expected %r' % (flock['key'], name, readback[name], want))
            for axis in range(3):
                if not _near(readback['homePointCm'][axis], flock['homePointCm'][axis], 1e-2):
                    problems.append('%s homePointCm %r' % (flock['key'], readback['homePointCm']))
                if not _near(readback['actorLocationCm'][axis], flock['homePointCm'][axis], 1e-2):
                    problems.append('%s actorLocationCm %r' % (flock['key'], readback['actorLocationCm']))
            if readback['flockEnabled'] == disabled:
                problems.append('%s flockEnabled %r' % (flock['key'], readback['flockEnabled']))
            if flock['species'].lower() not in readback['species'].replace('_', '').lower():
                problems.append('%s species reads back as %r' % (flock['key'], readback['species']))
            # The perch points themselves, numerically, off the reopened actor.
            reopened_perches = list(actor.get_editor_property(props['PerchPointsCm']))
            if not _vectors_match(reopened_perches, perch_points):
                problems.append('%s perch points changed across the round trip' % flock['key'])
            receipt['flocks'][flock['key']]['status'] = 'saved_and_read_back'
            receipt['flocks'][flock['key']]['readback'] = readback
            receipt['flocks'][flock['key']]['flockStatusAfterReopen'] = str(actor.call_method('GetFlockStatus'))
        if problems:
            raise RuntimeError('Readback mismatch after reopen: %r' % problems)

        receipt['totalBirdsPlaced'] = sum(f['birdCount'] for f, _a, _p in placed)
        receipt['performanceNote'] = (
            'The flock actors never tick: each is driven by a timer at %s s inside NearDistanceCm and %s s '
            'beyond MidDistanceCm, stepping at most BirdsPerUpdate birds per tick round-robin, and stops '
            'simulating entirely beyond CullRadiusCm. %d birds are placed in total across %d flocks. '
            'FlockMathTest.cpp measures the engine-free update at about 0.44 ms for 120 birds on the build '
            'machine CPU; at that rate one near flock at 20 Hz plus four far flocks at 4 Hz is about 0.5 ms '
            'of game thread per frame at 60 fps. That figure is a CPU measurement of the math, NOT a frame '
            'time measured in this map on the target GPU, and this script measures nothing.'
            % (spec['flocks'][0]['nearUpdateIntervalSeconds'], spec['flocks'][0]['farUpdateIntervalSeconds'],
               receipt['totalBirdsPlaced'], len(placed)))
        receipt['status'] = 'birds_imported_placed_saved_reopened_visual_and_runtime_acceptance_pending'
    except Exception as exc:  # noqa: BLE001
        receipt.update(status='failed_checkpoint_available' if checkpoint else 'failed_before_map_change',
                       failure=repr(exc))
        raise
    finally:
        receipt['mapSha256After'] = sha(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != receipt['mapSha256Before']
        write()
        try:
            ue.log(json.dumps(receipt, indent=2))
        except Exception:  # noqa: BLE001
            pass
    return receipt


if __name__ == '__main__':
    if '--offline-check' in sys.argv:
        print(json.dumps(offline_check(), indent=2))
    else:
        try:
            import unreal  # noqa: F401
        except ImportError:
            raise SystemExit('Outside the editor use --offline-check; native runs go through '
                             'UnrealEditor-Cmd -run=pythonscript (see the docstring)')
        run()

"""Guarded native adoption of the twenty-four authored inhabitants (people-v3).

Everything numeric and every asset path comes from Scripts/release_people_v3.spec.json.
The authored text itself lives in SourceAssets/runtime-review/people-v3/people.json and is
validated here against a Python mirror of the shipped rules in
Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashPeopleDirectory.h, so an invalid
directory is never staged and never saved into the map.

What it does, in order:
  1. Offline guards (no engine needed): spec hash, frozen people.json hash, full schema and
     loop-geometry validation, garment palette covers every authored variant, and the staged
     copy under Content/Distribution/People matches the source byte for byte.
  2. Engine guards: right project, no running game world, no dirty packages, and a FRESH
     compiled plugin (the population class exposes the new people properties and the
     character class exposes the dialog getters).
  3. Checkpoints the target .umap to <checkpointRoot>/PeopleV3-<stamp>/.
  4. Creates one UMaterialInstanceConstant per authored garment variant. It first tries to
     parent them to the rig's existing pilgrim garment material; because UE 5.8 setters
     return False, the parent is accepted only if a written colour READS BACK from the
     instance. If it does not, a flat master material matching the rig's shading is created
     and used instead, and the receipt says which parent was actually used.
  5. Spawns ONE new MikdashResidentPopulation actor (RELEASE_PeopleV3Population) pointed at
     the staged directory, with the pilgrim rig, idle/walk clips, garment slot names and the
     variant/material table. The original RELEASE_ResidentPopulation pilot is NOT touched.
  6. Whole-scene snapshot before/after (release_resident_crowd helper): only the new actor
     may differ. Saves, reopens, reads back every written value, and writes
     SourceAssets/runtime-review/people-v3/native-apply-<stamp>.json (at start and in finally).

Nothing here is visual, runtime, PIE, cook or packaged acceptance. The residents it
configures are scripted waypoint loops with authored lines: they are not minds, they decide
nothing, and no line they speak is a halachic ruling.

Commandlet invocation (serial; never while another native job is running; fresh -abslog path):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_people_v3.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-PeopleV3-01.log"

Optional engine command-line switches:
  -PeopleV3MaterialsOnly   create the garment materials only; no map change.
  -PeopleV3MaterialsExist  allow an existing garment namespace (re-verified, not recreated).

Offline (no engine):  python Scripts/release_people_v3.py --offline-check
Restage only:         python Scripts/release_people_v3.py --stage-only
"""
import hashlib
import json
import math
import runpy
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'Scripts' / 'release_people_v3.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'

ROLES = ('pilgrim', 'kohen', 'levite', 'host', 'guide', 'vendor')
ZONES = {
    'outer-court': dict(floor=300.0, x=(1500.0, 7000.0), absy=(900.0, 6000.0), absy_open_top=True),
    'mount-deck': dict(floor=0.0, x=(9300.0, 10000.0), absy=(0.0, 3000.0), absy_open_top=False),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


# --------------------------------------------------------------------------
# Pure checks (no unreal import). Mirror of MikdashPeopleDirectory.h.
# --------------------------------------------------------------------------

def slug_ok(text, least, most):
    if not isinstance(text, str) or not least <= len(text) <= most:
        return False
    for index, char in enumerate(text):
        if char.isdigit() or ('a' <= char <= 'z'):
            continue
        if char == '-' and index not in (0, len(text) - 1):
            continue
        return False
    return True


def one_line(text, least, most):
    return isinstance(text, str) and least <= len(text) <= most and not set('\r\n\t') & set(text)


def point_in_zone(zone, x, y):
    rule = ZONES[zone]
    if not (rule['x'][0] <= x <= rule['x'][1]):
        return False
    if rule['absy_open_top']:
        return rule['absy'][0] <= abs(y) < rule['absy'][1]
    return rule['absy'][0] <= abs(y) <= rule['absy'][1]


def loop_length(points):
    n = len(points)
    return sum(math.hypot(points[i][0] - points[(i + 1) % n][0], points[i][1] - points[(i + 1) % n][1]) for i in range(n))


def validate_person(person, index):
    def fail(why):
        raise RuntimeError('person %d (%r): %s' % (index, person.get('id'), why))
    if not slug_ok(person.get('id'), 3, 48):
        fail('id must be 3 to 48 characters of a-z, 0-9 and inner hyphens')
    if not one_line(person.get('name'), 2, 64):
        fail('name must be one line of 2 to 64 characters')
    if person.get('role') not in ROLES:
        fail('role must be one of %s' % (ROLES,))
    if not one_line(person.get('mission'), 8, 200):
        fail('mission must be one line of 8 to 200 characters')
    if not slug_ok(person.get('garment'), 2, 32):
        fail('garment variant key must be a 2 to 32 character slug')
    if person.get('zone') not in ZONES:
        fail('zone must be outer-court or mount-deck')
    zone = person['zone']
    if person['role'] == 'vendor' and zone != 'mount-deck':
        fail('a vendor may only be authored on the mount-deck, never inside the precinct')
    if 'origin' in person and not one_line(person['origin'], 2, 64):
        fail('origin, when present, must be one short line')
    if 'presence' in person and not one_line(person['presence'], 8, 160):
        fail('presence, when present, must be one line of 8 to 160 characters')
    if person['role'] in ('kohen', 'levite') and zone == 'outer-court' and not person.get('presence'):
        fail('a kohen or Levite on the outer-court floor must state a presence reason')
    dialog = person.get('dialog')
    if not isinstance(dialog, list) or not 3 <= len(dialog) <= 5:
        fail('dialog must be 3 to 5 first-person lines')
    for line in dialog:
        if not one_line(line, 12, 300):
            fail('each dialog line must be one line of 12 to 300 characters')
    laps = person.get('laps')
    if not isinstance(laps, int) or isinstance(laps, bool) or not 1 <= laps <= 12:
        fail('laps must be a whole number from 1 to 12')
    route = person.get('route')
    if not isinstance(route, list) or not 4 <= len(route) <= 6:
        fail('route must have 4 to 6 waypoints')
    if len(route) * laps > 64:
        fail('waypoints times laps must not exceed 64 goals')
    points = []
    floor = ZONES[zone]['floor']
    for step, waypoint in enumerate(route):
        at, look = waypoint.get('at'), waypoint.get('look')
        for name, value in (('at', at), ('look', look)):
            if not isinstance(value, list) or len(value) != 3 or not all(isinstance(v, (int, float)) for v in value):
                fail('waypoint %d %s must be three finite numbers' % (step, name))
        if not one_line(waypoint.get('label'), 4, 120) or not one_line(waypoint.get('action'), 4, 120):
            fail('waypoint %d label and action must each be one short line' % step)
        pause = waypoint.get('pause')
        if not isinstance(pause, (int, float)) or not 3.0 <= pause <= 5.0:
            fail('waypoint %d pause must be 3 to 5 seconds' % step)
        if not point_in_zone(zone, at[0], at[1]):
            fail('waypoint %d is outside its authored zone' % step)
        if abs(at[2] - floor) > 12.0:
            fail('waypoint %d is off its zone floor height' % step)
        if max(abs(look[0]), abs(look[1])) > 40000.0:
            fail('waypoint %d look target is implausibly far from the authored world' % step)
        points.append((at[0], at[1]))
    for step in range(len(points)):
        nxt = points[(step + 1) % len(points)]
        if math.hypot(nxt[0] - points[step][0], nxt[1] - points[step][1]) < 200.0:
            fail('waypoints %d and %d are closer than 2 m' % (step, (step + 1) % len(points)))
    length = loop_length(points)
    if not 6000.0 <= length <= 12000.0:
        fail('loop length %.1f cm is outside 60 to 120 m' % length)
    return dict(id=person['id'], role=person['role'], zone=zone, garment=person['garment'],
                waypoints=len(points), laps=laps, goals=len(points) * laps,
                loopLengthCm=length, dialogLines=len(dialog), start=[points[0][0], points[0][1]])


def validate_directory(document):
    if not isinstance(document, dict):
        raise RuntimeError('document root must be an object')
    if not one_line(document.get('version'), 1, 32):
        raise RuntimeError('version must be a short single-line string')
    if 'note' in document and (not isinstance(document['note'], str) or len(document['note']) > 2000):
        raise RuntimeError('note, when present, must be at most 2000 characters')
    basis = document.get('placementBasis')
    if not isinstance(basis, dict) or not basis:
        raise RuntimeError('placementBasis must record in writing why each role stands where it does')
    for role, entry in basis.items():
        if role not in ROLES:
            raise RuntimeError('placementBasis names an unknown role %r' % role)
        if not isinstance(entry, dict):
            raise RuntimeError('each placementBasis entry must be an object')
        if not isinstance(entry.get('decision'), str) or not 20 <= len(entry['decision']) <= 1200:
            raise RuntimeError('placementBasis[%s].decision must be 20 to 1200 characters' % role)
        evidence = entry.get('evidence')
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 8:
            raise RuntimeError('placementBasis[%s].evidence must be 1 to 8 source references' % role)
        for reference in evidence:
            if not one_line(reference, 8, 300):
                raise RuntimeError('placementBasis[%s] evidence entries must be one short line each' % role)
        for optional in ('notClaimed',):
            if optional in entry:
                if not isinstance(entry[optional], list) or len(entry[optional]) > 8:
                    raise RuntimeError('placementBasis[%s].%s must be at most 8 lines' % (role, optional))
                for line in entry[optional]:
                    if not one_line(line, 8, 300):
                        raise RuntimeError('placementBasis[%s].%s entries must be one short line' % (role, optional))
        if 'reviewFlag' in entry and not one_line(entry['reviewFlag'], 1, 200):
            raise RuntimeError('placementBasis[%s].reviewFlag must be one short line' % role)
    people = document.get('people')
    if not isinstance(people, list) or not 1 <= len(people) <= 64:
        raise RuntimeError('people must be an array of 1 to 64 individuals')
    rows, ids, names = [], set(), set()
    for index, person in enumerate(people):
        row = validate_person(person, index)
        if row['id'] in ids:
            raise RuntimeError('duplicate person id %r' % row['id'])
        if person['name'] in names:
            raise RuntimeError('duplicate person name %r' % person['name'])
        ids.add(row['id'])
        names.add(person['name'])
        rows.append(row)
    for role in sorted({row['role'] for row in rows}):
        if role not in basis:
            raise RuntimeError('role %r is used but has no written placementBasis entry' % role)
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            gap = math.hypot(rows[i]['start'][0] - rows[j]['start'][0], rows[i]['start'][1] - rows[j]['start'][1])
            if gap < 150.0:
                raise RuntimeError('start points %s and %s are only %.1f cm apart' % (rows[i]['id'], rows[j]['id'], gap))
    return rows


def stage_directory(spec):
    """Copy the authored directory into Content/Distribution/People and verify the bytes."""
    source = ROOT / spec['directory']['source']
    if sha(source) != spec['directory']['sha256']:
        raise RuntimeError('people.json changed after the spec was prepared; re-prepare the spec')
    staged = ROOT / 'Content' / spec['directory']['stagedRelativeToContent']
    staged.parent.mkdir(parents=True, exist_ok=True)
    replaced = staged.is_file() and sha(staged) != spec['directory']['sha256']
    shutil.copy2(source, staged)
    if sha(staged) != spec['directory']['sha256']:
        raise RuntimeError('staged copy hash differs from the source after copying')
    return dict(source=str(source.relative_to(ROOT)), staged=str(staged.relative_to(ROOT)),
                sha256=spec['directory']['sha256'], replacedExisting=replaced)


def offline_check(spec=None):
    spec = spec or load_spec()
    source = ROOT / spec['directory']['source']
    if sha(source) != spec['directory']['sha256']:
        raise RuntimeError('people.json changed after the spec was prepared')
    document = json.loads(source.read_text(encoding='utf-8-sig'))
    rows = validate_directory(document)
    if len(rows) != spec['directory']['expectedPeople']:
        raise RuntimeError('people count %d differs from the spec expectation' % len(rows))
    if document['version'] != spec['directory']['expectedVersion']:
        raise RuntimeError('directory version differs from the spec expectation')
    variants = sorted({row['garment'] for row in rows})
    palette = spec['garments']['variants']
    missing = [key for key in variants if key not in palette]
    if missing:
        raise RuntimeError('no garment colour is specified for %r' % missing)
    unused = [key for key in palette if key not in variants]
    assets = [palette[key]['asset'] for key in palette]
    if len(set(assets)) != len(assets):
        raise RuntimeError('two garment variants would write the same material asset name')
    staged = ROOT / 'Content' / spec['directory']['stagedRelativeToContent']
    return dict(status='offline_checks_passed', people=len(rows),
                roles={role: sum(1 for row in rows if row['role'] == role) for role in ROLES},
                zones={zone: sum(1 for row in rows if row['zone'] == zone) for zone in ZONES},
                garmentVariants=variants, unusedGarmentVariants=unused,
                totalGoals=sum(row['goals'] for row in rows),
                loopLengthCm={row['id']: round(row['loopLengthCm'], 1) for row in rows},
                stagedCopyPresent=staged.is_file(),
                stagedCopyMatches=staged.is_file() and sha(staged) == spec['directory']['sha256'],
                vendorsInsidePrecinct=[row['id'] for row in rows if row['role'] == 'vendor' and row['zone'] != 'mount-deck'])


# --------------------------------------------------------------------------
# Native (inside the editor)
# --------------------------------------------------------------------------

def _switch(name):
    import unreal as ue
    return ue.SystemLibrary.parse_param(ue.SystemLibrary.get_command_line(), name)


def _path(asset):
    return asset.get_path_name().split('.')[0] if asset else None


def _vec(v):
    return [v.x, v.y, v.z]


def _require_fresh_binary(ue, spec):
    required = spec['compiledClassesRequired']
    population = ue.load_class(None, required['population'])
    character = ue.load_class(None, required['character'])
    controller = ue.load_class(None, required['controller'])
    if not population or not character or not controller:
        raise RuntimeError('Compiled MikdashRuntime classes are not loaded; compile and restart the editor process')
    cdo = ue.get_default_object(population)
    for prop in required['populationPropertiesProvingFreshBinary']:
        try:
            cdo.get_editor_property(prop)
        except Exception as exc:
            raise RuntimeError('Population class lacks %s: stale binary (%r)' % (prop, exc))
    if cdo.get_editor_property('spawn_authored_people_on_begin_play') is not False:
        raise RuntimeError('Population default people opt-in must remain False')
    body = ue.get_default_object(character)
    if not hasattr(body, required['characterMethodProvingFreshBinary']):
        raise RuntimeError('Character class lacks %s: stale binary' % required['characterMethodProvingFreshBinary'])
    return population


def _linear(rgb):
    import unreal as ue
    return ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0)


def _colour_error(actual, expected):
    return max(abs(actual.r - expected[0]), abs(actual.g - expected[1]), abs(actual.b - expected[2]))


def _make_master(ue, tools, assets, garments, sample):
    """A flat master carrying the two named parameters the instances drive."""
    namespace = garments['namespace'] + '/Materials'
    path = namespace + '/' + garments['masterAsset']
    if assets.does_asset_exist(path):
        material = ue.load_asset(path)
        if not material:
            raise RuntimeError('Existing master material failed to load: ' + path)
        return material, False
    ml = ue.MaterialEditingLibrary
    material = tools.create_asset(garments['masterAsset'], namespace, ue.Material, ue.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Material factory failed for ' + garments['masterAsset'])
    colour = ml.create_material_expression(material, ue.MaterialExpressionVectorParameter)
    colour.set_editor_property('parameter_name', garments['colorParameter'])
    colour.set_editor_property('default_value', _linear(sample['baseColor']))
    if not ml.connect_material_property(colour, '', ue.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('BaseColor connection failed on the garment master')
    rough = ml.create_material_expression(material, ue.MaterialExpressionScalarParameter)
    rough.set_editor_property('parameter_name', garments['roughnessParameter'])
    rough.set_editor_property('default_value', float(sample['roughness']))
    if not ml.connect_material_property(rough, '', ue.MaterialProperty.MP_ROUGHNESS):
        raise RuntimeError('Roughness connection failed on the garment master')
    metal = ml.create_material_expression(material, ue.MaterialExpressionConstant)
    metal.set_editor_property('r', 0.0)
    if not ml.connect_material_property(metal, '', ue.MaterialProperty.MP_METALLIC):
        raise RuntimeError('Metallic connection failed on the garment master')
    ml.recompile_material(material)
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Master material save failed')
    return material, True


def _instance(ue, tools, assets, garments, name, parent, colour, roughness):
    """Create (or load) one instance, write the parameters, and prove it by readback.

    UE 5.8 property setters return False, so nothing here trusts a return value: every
    parameter is written and then read back off the saved instance.
    """
    ml = ue.MaterialEditingLibrary
    namespace = garments['namespace'] + '/Materials'
    path = namespace + '/' + name
    created = False
    instance = ue.load_asset(path) if assets.does_asset_exist(path) else None
    if not instance:
        instance = tools.create_asset(name, namespace, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew())
        created = True
    if not instance:
        raise RuntimeError('Material instance factory failed for ' + name)
    ml.set_material_instance_parent(instance, parent)
    ml.set_material_instance_vector_parameter_value(instance, garments['colorParameter'], _linear(colour))
    ml.set_material_instance_scalar_parameter_value(instance, garments['roughnessParameter'], float(roughness))
    ml.update_material_instance(instance)
    read = ml.get_material_instance_vector_parameter_value(instance, garments['colorParameter'])
    error = _colour_error(read, colour)
    scalar = ml.get_material_instance_scalar_parameter_value(instance, garments['roughnessParameter'])
    return instance, created, error, float(scalar)


def _parent_accepts_colour(ue, tools, assets, garments, candidate_path, sample):
    """Try the rig's own garment material as the instance parent, and believe only readback."""
    if not candidate_path or not assets.does_asset_exist(candidate_path):
        return None, 'the rig garment material does not exist at the spec path'
    parent = ue.load_asset(candidate_path)
    if not parent:
        return None, 'the rig garment material failed to load'
    probe_name = garments['masterAsset'] + '_ParentProbe'
    try:
        probe, _created, error, _rough = _instance(ue, tools, assets, garments, probe_name, parent,
                                                   sample['baseColor'], sample['roughness'])
    except Exception as exc:
        return None, 'probe instance could not be created: %r' % (exc,)
    probe_path = _path(probe)
    accepted = error <= garments['readbackToleranceRgb']
    assets.delete_asset(probe_path)
    if assets.does_asset_exist(probe_path):
        raise RuntimeError('The parent probe instance %s could not be deleted; clean it up before rerunning' % probe_path)
    if accepted:
        return parent, None
    return None, ('the rig garment material exposes no %s parameter (probe readback error %.4f), '
                  'so a flat master matching its shading is used instead' % (garments['colorParameter'], error))


def run():
    import unreal as ue
    spec = load_spec()
    garments = spec['garments']
    rig = spec['rig']
    offline = offline_check(spec)
    staging = stage_directory(spec)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is running; use a dedicated editor process')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Unsaved packages present; run on a clean editor')
    population_class = _require_fresh_binary(ue, spec)
    materials_only = _switch('PeopleV3MaterialsOnly')
    materials_exist = _switch('PeopleV3MaterialsExist')
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    helper = runpy.run_path(str(ROOT / 'Scripts/release_resident_crowd.py'))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_dir = ROOT / spec['receiptFolder']
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / (spec['receiptPrefix'] + stamp + '.json')
    map_file = ROOT / spec['targetMapFile']
    receipt = dict(status='started', stamp=stamp, spec=str(SPEC_PATH.relative_to(ROOT)), specSha256=sha(SPEC_PATH),
                   offline=offline, staging=staging, mapBeforeSha256=sha(map_file),
                   switches=dict(materialsOnly=materials_only, materialsExist=materials_exist),
                   garments={}, population={}, mapSaved=False, mainRuntimeAcceptance=False,
                   scope=spec['scope'],
                   honesty=('These residents are scripted waypoint loops reading authored lines. '
                            'They are not minds, they decide nothing, and no line is a ruling.'))

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    write()

    try:
        # ---- rig assets
        mesh = ue.load_asset(rig['skeletalMesh'])
        idle = ue.load_asset(rig['idleAnimation'])
        walk = ue.load_asset(rig['walkAnimation'])
        if not mesh or not idle or not walk:
            raise RuntimeError('The pilgrim rig, idle clip or walk clip is missing')
        if _path(mesh.get_editor_property('skeleton')) != _path(idle.get_editor_property('skeleton')) \
                or _path(mesh.get_editor_property('skeleton')) != _path(walk.get_editor_property('skeleton')):
            raise RuntimeError('The idle/walk clips do not belong to the rig skeleton')
        slot_names = []
        try:
            slot_names = [str(entry.get_editor_property('material_slot_name')) for entry in mesh.get_editor_property('materials')]
        except Exception as exc:
            receipt['garmentSlotIntrospection'] = 'unavailable: %r' % (exc,)
        receipt['rig'] = dict(skeletalMesh=_path(mesh), idle=_path(idle), walk=_path(walk),
                              materialSlots=slot_names, requestedSlots=rig['garmentMaterialSlots'])
        if slot_names:
            unmatched = [name for name in rig['garmentMaterialSlots'] if name not in slot_names]
            if unmatched:
                raise RuntimeError('Requested garment slots %r are not on the rig; slots are %r' % (unmatched, slot_names))
        write()

        # ---- garment materials
        namespace = garments['namespace'] + '/Materials'
        if assets.does_directory_exist(namespace) and not materials_exist:
            raise RuntimeError('Namespace %s exists; pass -PeopleV3MaterialsExist to re-verify instead of creating'
                               % namespace)
        variants = offline['garmentVariants']
        sample = garments['variants'][variants[0]]
        parent, parent_note = _parent_accepts_colour(ue, tools, assets, garments,
                                                     rig.get('existingPilgrimMaterial'), sample)
        if parent is not None:
            parent_source = 'existing pilgrim garment material'
        else:
            master, master_created = _make_master(ue, tools, assets, garments, sample)
            parent = master
            parent_source = 'new flat master derived from the rig shading'
            receipt['garmentMaster'] = dict(path=_path(master), created=master_created, reason=parent_note)
        receipt['garmentParent'] = dict(path=_path(parent), source=parent_source, note=parent_note)
        write()
        keys, instances = [], []
        for key in variants:
            entry = garments['variants'][key]
            instance, created, error, roughness = _instance(ue, tools, assets, garments, entry['asset'], parent,
                                                            entry['baseColor'], entry['roughness'])
            if error > garments['readbackToleranceRgb']:
                raise RuntimeError('Garment %s colour did not read back (error %.4f); UE 5.8 setters return False, '
                                   'so a failed readback is a hard refusal' % (key, error))
            if abs(roughness - float(entry['roughness'])) > 1e-3:
                raise RuntimeError('Garment %s roughness did not read back (%r)' % (key, roughness))
            if not assets.save_loaded_asset(instance, only_if_is_dirty=False):
                raise RuntimeError('Material instance save failed for ' + key)
            keys.append(key)
            instances.append(instance)
            receipt['garments'][key] = dict(path=_path(instance), created=created, parent=_path(parent),
                                            baseColor=entry['baseColor'], roughness=entry['roughness'],
                                            colourReadbackErrorRgb=error, roughnessReadback=roughness)
        receipt['status'] = 'garments_ready'
        write()
        if materials_only:
            receipt['status'] = 'materials_only_complete_map_unchanged'
            return receipt

        # ---- map
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            if not levels.load_level(TARGET):
                raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Unexpected editor world')
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'BeforePeopleV3.umap')
        if sha(checkpoint / 'BeforePeopleV3.umap') != receipt['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy hash mismatch')
        receipt['checkpoint'] = str(checkpoint)
        write()

        conf = spec['population']
        before = helper['_scene_snapshot'](ue, actors)
        existing = [a for a in actors.get_all_level_actors() if a.get_actor_label() == conf['newActorLabel']]
        if existing:
            raise RuntimeError('%s already exists; refusing duplicate' % conf['newActorLabel'])
        pilots = [a for a in actors.get_all_level_actors() if a.get_actor_label() == conf['existingPilotLabel']]
        receipt['population']['existingPilotFound'] = len(pilots)
        pilot_before = [helper['_pose'](a) for a in pilots]

        owner = actors.spawn_actor_from_class(population_class, ue.Vector(*conf['location']), ue.Rotator(), transient=False)
        if not owner:
            raise RuntimeError('People population spawn failed')
        owner.set_actor_label(conf['newActorLabel'])
        owner.set_folder_path(conf['folder'])
        owner.tags = [ue.Name(conf['tag'])]
        owner.set_editor_property('people_directory_file', spec['directory']['stagedRelativeToContent'])
        owner.set_editor_property('resident_mesh', mesh)
        owner.set_editor_property('idle_animation', idle)
        owner.set_editor_property('walk_animation', walk)
        owner.set_editor_property('garment_material_slots', [ue.Name(n) for n in rig['garmentMaterialSlots']])
        owner.set_editor_property('garment_variant_keys', list(keys))
        owner.set_editor_property('garment_materials', list(instances))
        owner.set_editor_property('spawn_authored_people_on_begin_play', bool(conf['startupOptIn']))
        # The pilot's own startup flag is never written here; the two paths are independent
        # actors and the reviewed five-figure pilot keeps whatever it already had.
        owner.modify()
        owner_name = owner.get_name()
        after = helper['_scene_snapshot'](ue, actors)
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        if changed - {owner_name}:
            raise RuntimeError('Unexpected scene changes: %r' % sorted(changed - {owner_name}))
        receipt['sceneChanges'] = sorted(changed)
        if [helper['_pose'](a) for a in actors.get_all_level_actors() if a.get_actor_label() == conf['existingPilotLabel']] != pilot_before:
            raise RuntimeError('The existing pilot population actor moved; refusing to save')
        if not levels.save_current_level():
            raise RuntimeError('Level save failed')
        receipt.update(status='saved_reopen_pending', mapSaved=True, mapAfterSha256=sha(map_file))
        write()

        # ---- reopen and read back
        if not levels.load_level(TARGET) or editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Reopen failed')
        reopened = helper['_scene_snapshot'](ue, actors)
        if set(reopened) != set(after) or any(reopened[k] != before[k] for k in before if k not in changed):
            raise RuntimeError('Reopened scene differs outside the intended actor')
        owners = [a for a in actors.get_all_level_actors() if a.get_actor_label() == conf['newActorLabel']]
        if len(owners) != 1:
            raise RuntimeError('Reopened map lacks exactly one people population actor')
        owner = owners[0]
        readback = dict(
            directoryFile=str(owner.get_editor_property('people_directory_file')),
            residentMesh=_path(owner.get_editor_property('resident_mesh')),
            idleAnimation=_path(owner.get_editor_property('idle_animation')),
            walkAnimation=_path(owner.get_editor_property('walk_animation')),
            garmentMaterialSlots=[str(n) for n in owner.get_editor_property('garment_material_slots')],
            garmentVariantKeys=[str(s) for s in owner.get_editor_property('garment_variant_keys')],
            garmentMaterials=[_path(m) for m in owner.get_editor_property('garment_materials')],
            startupOptIn=owner.get_editor_property('spawn_authored_people_on_begin_play'),
            pilotOptIn=owner.get_editor_property('activate_reviewed_pilot_on_begin_play'))
        expected = dict(
            directoryFile=spec['directory']['stagedRelativeToContent'],
            residentMesh=rig['skeletalMesh'], idleAnimation=rig['idleAnimation'], walkAnimation=rig['walkAnimation'],
            garmentMaterialSlots=list(rig['garmentMaterialSlots']),
            garmentVariantKeys=list(keys),
            garmentMaterials=[_path(m) for m in instances],
            startupOptIn=bool(conf['startupOptIn']), pilotOptIn=False)
        for key in expected:
            if readback[key] != expected[key]:
                raise RuntimeError('Readback mismatch for %s: %r vs %r' % (key, readback[key], expected[key]))
        # The staged file must still be the reviewed bytes after everything above.
        staged = ROOT / 'Content' / spec['directory']['stagedRelativeToContent']
        if sha(staged) != spec['directory']['sha256']:
            raise RuntimeError('The staged people.json changed during the run')
        receipt.update(readback=readback, population=dict(receipt['population'], actor=owner.get_name(),
                       label=conf['newActorLabel'], folder=conf['folder']),
                       status='adopted_saved_reopened_runtime_pie_and_visual_review_pending')
    except Exception as exc:
        receipt.update(status='failed_checkpoint_available' if receipt.get('checkpoint') else 'failed_before_map_change',
                       failure=repr(exc))
        raise
    finally:
        receipt['mapAfterSha256'] = sha(map_file)
        receipt['mapBytesChanged'] = receipt['mapAfterSha256'] != receipt['mapBeforeSha256']
        write()
        ue.log(json.dumps(receipt, indent=2, ensure_ascii=False))
    return receipt


if __name__ == '__main__':
    if '--offline-check' in sys.argv:
        print(json.dumps(offline_check(), indent=2, ensure_ascii=False))
    elif '--stage-only' in sys.argv:
        SPEC = load_spec()
        print(json.dumps(dict(offline=offline_check(SPEC), staging=stage_directory(SPEC)), indent=2, ensure_ascii=False))
    else:
        try:
            import unreal  # noqa: F401
        except ImportError:
            raise SystemExit('Outside the editor use --offline-check or --stage-only; native runs go through '
                             'UnrealEditor-Cmd -run=pythonscript (see docstring)')
        run()

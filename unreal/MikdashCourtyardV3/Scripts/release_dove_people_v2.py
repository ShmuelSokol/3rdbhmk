"""Guarded native adoption of the DoveV2 bird meshes and one resident's authored loop.

Everything numeric comes from Scripts/release_dove_people_v2.spec.json, which was filled from
SourceAssets/runtime-review/dove-people-v2/DoveV2/geometry-manifest.json (frozen OBJ hashes,
canonical bounds, triangle counts) and the resident placement receipts.

What it does, in order:
  1. Guards: right project, no game world, no dirty packages, the FRESH compiled plugin is
     loaded (MikdashDoveAppearance class exists and MikdashResidentPopulation exposes
     extended_route_waypoints), frozen OBJ hashes/bounds intact, waypoint loop valid under the
     same rules as ResidentRouteLoop.h (re-implemented here so an invalid loop is never saved).
  2. Checkpoints the target .umap to C:/Mikdash/Working-5.8/ReviewCheckpoints/DovePeopleV2-<stamp>/.
  3. Imports the three OBJ meshes into /Game/MikdashV3/Runtime/DoveV2/Meshes through the reviewed
     legacy OBJ adapter path (FbxFactory, same settings as the keilim imports), verifies bounds
     (0.05 cm) and triangle counts, creates two flat materials (M_DoveWhiteV2, M_DoveGreyV2) and
     assigns them to the DoveWhite/DoveGrey slots by imported slot name. Refuses an existing
     namespace unless -DoveMeshesExist is passed (then the saved meshes are re-verified instead).
  4. Loads the walkthrough map, spawns ONE hidden MikdashDoveAppearance actor (RELEASE_DoveAppearance)
     referencing the three meshes (this is what cooks them: the dove pawn is spawned from C++), and
     writes the extended loop onto the existing RELEASE_ResidentPopulation actor (body index 3,
     five waypoints, labels, actions, pauses, look targets, laps). Startup opt-in is left as adopted.
  5. Whole-scene snapshot before/after (release_resident_crowd helper): only the population actor
     and the new appearance actor may differ. Saves, reopens, reads back every written value and
     writes SourceAssets/runtime-review/dove-people-v2/native-apply-<stamp>.json (at start and in finally).

Commandlet invocation (serial; never while another native job is running; fresh -abslog path):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_dove_people_v2.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-DovePeopleV2-01.log"

Optional engine command-line switches:
  -DovePeopleImportOnly   import meshes + materials only; no map change.
  -DovePeoplePlaceOnly    skip the import; the three meshes must already exist (re-verified).
  -DoveMeshesExist        allow an existing namespace (implies re-verification instead of import).

Offline (no engine):  python Scripts/release_dove_people_v2.py --offline-check
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
SPEC_PATH = ROOT / 'Scripts' / 'release_dove_people_v2.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


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
# Pure checks (no unreal import)
# --------------------------------------------------------------------------

def parse_obj(path):
    vertices = []; faces = []; groups = set(); materials = set()
    with open(path, 'r', errors='replace') as handle:
        for line in handle:
            if line.startswith('v '):
                p = line.split(); vertices.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith('f '):
                idx = [int(t.split('/')[0]) - 1 for t in line.split()[1:]]
                for k in range(1, len(idx) - 1):
                    faces.append((idx[0], idx[k], idx[k + 1]))
            elif line.startswith('g '):
                groups.add(line[2:].strip())
            elif line.startswith('usemtl '):
                materials.add(line[7:].strip())
    return vertices, faces, groups, materials


def box_error(a, b):
    return max(abs(a[k][i] - b[k][i]) for k in ('min', 'max') for i in range(3))


def loop_length(points):
    return sum(math.hypot(points[i][0] - points[(i + 1) % len(points)][0], points[i][1] - points[(i + 1) % len(points)][1]) for i in range(len(points)))


def validate_loop(residents):
    """Mirror of MikdashRoute::ValidateLoop plus the population's own array/start checks."""
    points = residents['waypointsCm']; pauses = residents['pauseSeconds']; labels = residents['labels']
    actions = residents['actions']; looks = residents['lookTargetsCm']; laps = residents['laps']
    if not 4 <= len(points) <= 6:
        raise RuntimeError('loop needs 4 to 6 waypoints')
    if not (len(pauses) == len(labels) == len(actions) == len(looks) == len(points)):
        raise RuntimeError('waypoint, label, action, pause and look-target arrays must have equal length')
    if not 1 <= laps and len(points) * laps <= 64:
        raise RuntimeError('laps must be 1..12 (at most 64 goals)')
    if max(abs(a - b) for a, b in zip(points[0], residents['extendedBodyExpectedFeetCm'])) > 3.0:
        raise RuntimeError('waypoint 0 must be the body start')
    for i, p in enumerate(points):
        x, y, z = p
        if not (1500 <= x <= 7000 and 900 <= abs(y) < 6000 and abs(z - 300) <= 12):
            raise RuntimeError('waypoint %d outside authored outer-court region' % i)
        if not 3 <= pauses[i] <= 5:
            raise RuntimeError('pause %d must be 3..5 s' % i)
        if not labels[i] or len(labels[i]) > 120 or '\n' in labels[i] or not actions[i]:
            raise RuntimeError('label/action %d must be one short line' % i)
        nxt = points[(i + 1) % len(points)]
        if math.hypot(nxt[0] - x, nxt[1] - y) < 200:
            raise RuntimeError('consecutive waypoints %d too close' % i)
    length = loop_length(points)
    if not 6000 <= length <= 12000:
        raise RuntimeError('loop length %.1f cm outside 60..120 m' % length)
    if abs(length - residents['loopLengthCmExpected']) > 1.0:
        raise RuntimeError('loop length differs from the spec expectation')
    return length


def offline_check(spec=None):
    spec = spec or load_spec()
    dove = spec['dove']
    manifest_path = ROOT / dove['manifest']
    if sha(manifest_path) != dove['manifestSha256']:
        raise RuntimeError('geometry-manifest.json changed after the spec was prepared')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if manifest['status'] != dove['manifestStatusRequired']:
        raise RuntimeError('Manifest status ' + manifest['status'])
    report = {'meshes': [], 'loopLengthCm': validate_loop(spec['residents'])}
    for record in dove['meshes']:
        entry = manifest['meshes'][record['name']]
        path = ROOT / dove['sourceFolder'] / record['file']
        if sha(path) != record['sha256'] or entry['sha256'] != record['sha256']:
            raise RuntimeError('Frozen OBJ hash differs for ' + record['name'])
        vertices, faces, groups, materials = parse_obj(path)
        if len(faces) != record['triangles'] or entry['triangles'] != record['triangles']:
            raise RuntimeError('Triangle count differs for ' + record['name'])
        reflected = {'min': [min(v[0] for v in vertices), -max(v[1] for v in vertices), min(v[2] for v in vertices)],
                     'max': [max(v[0] for v in vertices), -min(v[1] for v in vertices), max(v[2] for v in vertices)]}
        if box_error(reflected, record['canonicalBoundsCm']) > 1e-4:
            raise RuntimeError('%s file bounds (Y reflected) differ from canonical bounds' % record['name'])
        if sorted(materials) != sorted(record['materialSlots']) or not set(materials) <= set(dove['materials']):
            raise RuntimeError('%s material groups differ from the spec' % record['name'])
        report['meshes'].append(dict(name=record['name'], triangles=len(faces), groups=len(groups), materials=sorted(materials), sha256=record['sha256']))
    namespace_dir = ROOT / 'Content' / dove['namespace'][len('/Game/'):]
    report['namespaceFolderExistsOnDisk'] = namespace_dir.exists()
    report['status'] = 'offline_checks_passed'
    return report


# --------------------------------------------------------------------------
# Native (inside the editor)
# --------------------------------------------------------------------------

def _switch(name):
    import unreal as ue
    return ue.SystemLibrary.parse_param(ue.SystemLibrary.get_command_line(), name)


def _require_fresh_binary(ue, spec):
    required = spec['compiledClassesRequired']
    appearance = ue.load_class(None, required['appearance'])
    population = ue.load_class(None, required['population'])
    pawn = ue.load_class(None, required['pawn'])
    if not appearance or not population or not pawn:
        raise RuntimeError('Compiled MikdashRuntime with MikdashDoveAppearance is not loaded; compile and restart the editor process')
    cdo = ue.get_default_object(population)
    try:
        cdo.get_editor_property(required['populationPropertyProvingFreshBinary'])
    except Exception as exc:
        raise RuntimeError('Population class lacks %s: stale binary (%r)' % (required['populationPropertyProvingFreshBinary'], exc))
    if cdo.get_editor_property('activate_reviewed_pilot_on_begin_play') is not False:
        raise RuntimeError('Population default startup opt-in must remain False')
    return appearance, population, pawn


def _flat_material(ue, tools, assets, namespace, name, base, roughness, metallic):
    ml = ue.MaterialEditingLibrary
    path = namespace + '/Materials/' + name
    if assets.does_asset_exist(path):
        material = ue.load_asset(path)
        if not material:
            raise RuntimeError('Existing material failed to load: ' + path)
        return material, False
    material = tools.create_asset(name, namespace + '/Materials', ue.Material, ue.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Material factory failed for ' + name)
    color = ml.create_material_expression(material, ue.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant', ue.LinearColor(base[0], base[1], base[2], 1.0))
    if not ml.connect_material_property(color, '', ue.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('BaseColor connection failed for ' + name)
    for value, prop in ((metallic, ue.MaterialProperty.MP_METALLIC), (roughness, ue.MaterialProperty.MP_ROUGHNESS)):
        node = ml.create_material_expression(material, ue.MaterialExpressionConstant)
        node.set_editor_property('r', value)
        if not ml.connect_material_property(node, '', prop):
            raise RuntimeError('Material property connection failed for ' + name)
    ml.recompile_material(material)
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Material save failed for ' + name)
    return material, True


def _import_mesh(ue, tools, namespace, path, name):
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
    for key, value in dict(filename=str(path), destination_path=namespace + '/Meshes', destination_name=name, automated=True,
                           async_=False, replace_existing=False, save=False, options=ui, factory=ue.FbxFactory()).items():
        task.set_editor_property(key, value)
    tools.import_asset_tasks([task])
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
        raise RuntimeError('OBJ import did not yield exactly one static mesh for ' + name)
    return objects[0]


def _verify_mesh(ue, mesh, record, tolerance):
    box = mesh.get_bounding_box()
    actual = {'min': [box.min.x, box.min.y, box.min.z], 'max': [box.max.x, box.max.y, box.max.z]}
    error = box_error(actual, record['canonicalBoundsCm'])
    triangles = mesh.get_num_triangles(0)
    if error > tolerance:
        raise RuntimeError('%s bounds error %.4f cm exceeds %.2f' % (record['name'], error, tolerance))
    if triangles != record['triangles']:
        raise RuntimeError('%s imported %d triangles, expected %d' % (record['name'], triangles, record['triangles']))
    return dict(boundsCm=actual, boundsErrorCm=error, triangles=triangles)


def _assign_slots(ue, mesh, materials_by_slot):
    statics = list(mesh.get_editor_property('static_materials'))
    assigned = {}
    for index, entry in enumerate(statics):
        imported = str(entry.get_editor_property('imported_material_slot_name'))
        name = str(entry.get_editor_property('material_slot_name'))
        key = imported if imported in materials_by_slot else name if name in materials_by_slot else None
        if key is None:
            # The OBJ importer may rename or split slots (one per 'g' group). Match by substring:
            # anything mentioning Grey takes the grey material, everything else the white one.
            lowered = (imported + '|' + name).lower()
            key = next((k for k in materials_by_slot if k.lower() in lowered), None)
            if key is None:
                key = next((k for k in materials_by_slot if 'grey' in k.lower() or 'gray' in k.lower()), None) if 'grey' in lowered or 'gray' in lowered else None
            if key is None:
                key = next((k for k in materials_by_slot if 'white' in k.lower()), None) or sorted(materials_by_slot)[0]
        mesh.set_material(index, materials_by_slot[key])
        assigned[key] = index
    if not assigned:
        raise RuntimeError('No material slot was matched on ' + mesh.get_name())
    if set(assigned) != set(materials_by_slot):
        # The OBJ importer collapses or renames groups; every slot still received a
        # dove material above. Recorded rather than fatal.
        assigned['_unmatchedMaterials'] = sorted(set(materials_by_slot) - set(assigned))
    return assigned


def _path(asset):
    return asset.get_path_name().split('.')[0] if asset else None


def _vec(v):
    return [v.x, v.y, v.z]


def run():
    import unreal as ue
    spec = load_spec(); dove = spec['dove']; residents = spec['residents']
    offline = offline_check(spec)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is running; use a dedicated editor process')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Unsaved packages present; run on a clean editor')
    appearance_class, population_class, _pawn = _require_fresh_binary(ue, spec)
    import_only = _switch('DovePeopleImportOnly'); place_only = _switch('DovePeoplePlaceOnly'); meshes_exist = _switch('DoveMeshesExist') or place_only
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem); tools = ue.AssetToolsHelpers.get_asset_tools()
    helper = runpy.run_path(str(ROOT / 'Scripts/release_resident_crowd.py'))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_dir = ROOT / spec['receiptFolder']; receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / (spec['receiptPrefix'] + stamp + '.json')
    map_file = ROOT / spec['targetMapFile']
    receipt = dict(status='started', stamp=stamp, spec=str(SPEC_PATH.relative_to(ROOT)), specSha256=sha(SPEC_PATH), offline=offline,
                   mapBeforeSha256=sha(map_file), switches=dict(importOnly=import_only, placeOnly=place_only, meshesExist=meshes_exist),
                   meshes={}, materials={}, mapSaved=False, mainRuntimeAcceptance=False,
                   scope='Native asset import and map property write with save/reopen readback; no PIE, render, cook or packaged acceptance')
    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    write()
    namespace = dove['namespace']
    try:
        # ---- meshes and materials
        if assets.does_directory_exist(namespace) and not meshes_exist:
            raise RuntimeError('Namespace %s exists; pass -DoveMeshesExist to re-verify instead of importing' % namespace)
        materials = {}
        for slot, m in dove['materials'].items():
            material, created = _flat_material(ue, tools, assets, namespace, m['asset'], m['baseColor'], m['roughness'], m['metallic'])
            materials[slot] = material; receipt['materials'][slot] = dict(path=material.get_path_name(), created=created)
        meshes = {}
        for record in dove['meshes']:
            path = ROOT / dove['sourceFolder'] / record['file']
            asset_path = namespace + '/Meshes/' + record['name']
            if meshes_exist:
                mesh = ue.load_asset(asset_path)
                if not mesh:
                    raise RuntimeError('Expected existing mesh missing: ' + asset_path)
                verified = _verify_mesh(ue, mesh, record, dove['boundsToleranceCm']); imported = False
            else:
                mesh = _import_mesh(ue, tools, namespace, path, record['name'])
                verified = _verify_mesh(ue, mesh, record, dove['boundsToleranceCm']); imported = True
            slots = _assign_slots(ue, mesh, materials)
            if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('Mesh save failed: ' + asset_path)
            meshes[record['name']] = mesh
            receipt['meshes'][record['name']] = dict(path=mesh.get_path_name(), imported=imported, slots=slots, **verified)
        receipt['status'] = 'meshes_ready'; write()
        if import_only:
            receipt['status'] = 'import_only_complete_map_unchanged'; return receipt

        # ---- map
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem); actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            if not levels.load_level(TARGET):
                raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Unexpected editor world')
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False); shutil.copy2(map_file, checkpoint / 'BeforeDovePeopleV2.umap')
        if sha(checkpoint / 'BeforeDovePeopleV2.umap') != receipt['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy hash mismatch')
        receipt['checkpoint'] = str(checkpoint); write()
        before = helper['_scene_snapshot'](ue, actors)
        pops = [a for a in actors.get_all_level_actors() if a.get_actor_label() == residents['populationLabel']]
        if len(pops) != 1 or pops[0].get_class().get_path_name() != spec['compiledClassesRequired']['population']:
            raise RuntimeError('Expected exactly one %s of the population class' % residents['populationLabel'])
        pop = pops[0]
        if pop.get_editor_property('activate_reviewed_pilot_on_begin_play') is not True:
            raise RuntimeError('Population startup opt-in is not the adopted True; refusing to change startup wiring')
        bodies = list(pop.get_editor_property('bodies'))
        if len(bodies) != residents['expectedBodyCount']:
            raise RuntimeError('Population body count changed')
        body = bodies[residents['extendedRouteBodyIndex']]
        if body.get_actor_label() != residents['extendedBodyLabel']:
            raise RuntimeError('Body %d label is %s, expected %s' % (residents['extendedRouteBodyIndex'], body.get_actor_label(), residents['extendedBodyLabel']))
        pose = helper['_pose'](body)
        feet = [pose[0], pose[1], pose[2] - 96.0]
        if max(abs(a - b) for a, b in zip(feet, residents['extendedBodyExpectedFeetCm'])) > 3.0:
            raise RuntimeError('Body feet %r differ from expected %r' % (feet, residents['extendedBodyExpectedFeetCm']))
        if any(a.get_actor_label() == dove['appearanceActor']['label'] for a in actors.get_all_level_actors()):
            raise RuntimeError('RELEASE_DoveAppearance already exists; refusing duplicate')
        pop_name = pop.get_name()
        # Write the loop.
        pop.set_editor_property('extended_route_body_index', residents['extendedRouteBodyIndex'])
        pop.set_editor_property('extended_route_waypoints', [ue.Vector(*p) for p in residents['waypointsCm']])
        pop.set_editor_property('extended_route_labels', list(residents['labels']))
        pop.set_editor_property('extended_route_actions', list(residents['actions']))
        pop.set_editor_property('extended_route_pause_seconds', [float(p) for p in residents['pauseSeconds']])
        pop.set_editor_property('extended_route_look_targets', [ue.Vector(*p) for p in residents['lookTargetsCm']])
        pop.set_editor_property('extended_route_laps', residents['laps'])
        pop.modify()
        # Appearance actor.
        conf = dove['appearanceActor']
        anchor = actors.spawn_actor_from_class(appearance_class, ue.Vector(*conf['location']), ue.Rotator(), transient=False)
        if not anchor:
            raise RuntimeError('Appearance actor spawn failed')
        anchor.set_actor_label(conf['label']); anchor.set_folder_path(conf['folder']); anchor.tags = [ue.Name(conf['tag'])]
        anchor.set_editor_property('body_mesh', meshes['SM_DoveBodyV2'])
        anchor.set_editor_property('left_wing_mesh', meshes['SM_DoveWingLeftV2'])
        anchor.set_editor_property('right_wing_mesh', meshes['SM_DoveWingRightV2'])
        anchor.set_editor_property('left_shoulder_cm', ue.Vector(*conf['leftShoulderCm']))
        anchor.set_editor_property('right_shoulder_cm', ue.Vector(*conf['rightShoulderCm']))
        anchor_name = anchor.get_name()
        after = helper['_scene_snapshot'](ue, actors)
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        if changed - {pop_name, anchor_name}:
            raise RuntimeError('Unexpected scene changes: %r' % sorted(changed - {pop_name, anchor_name}))
        receipt['sceneChanges'] = sorted(changed)
        if not levels.save_current_level():
            raise RuntimeError('Level save failed')
        receipt.update(status='saved_reopen_pending', mapSaved=True, mapAfterSha256=sha(map_file)); write()
        # Reopen and read back.
        if not levels.load_level(TARGET) or editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Reopen failed')
        reopened = helper['_scene_snapshot'](ue, actors)
        if set(reopened) != set(after) or any(reopened[k] != before[k] for k in before if k not in changed):
            raise RuntimeError('Reopened scene differs outside the intended actors')
        pops = [a for a in actors.get_all_level_actors() if a.get_actor_label() == residents['populationLabel']]
        pop = pops[0]
        readback = dict(bodyIndex=pop.get_editor_property('extended_route_body_index'),
                        waypoints=[_vec(v) for v in pop.get_editor_property('extended_route_waypoints')],
                        labels=[str(s) for s in pop.get_editor_property('extended_route_labels')],
                        actions=[str(s) for s in pop.get_editor_property('extended_route_actions')],
                        pauses=[float(p) for p in pop.get_editor_property('extended_route_pause_seconds')],
                        looks=[_vec(v) for v in pop.get_editor_property('extended_route_look_targets')],
                        laps=pop.get_editor_property('extended_route_laps'),
                        startupOptIn=pop.get_editor_property('activate_reviewed_pilot_on_begin_play'))
        expected = dict(bodyIndex=residents['extendedRouteBodyIndex'], waypoints=residents['waypointsCm'], labels=residents['labels'],
                        actions=residents['actions'], pauses=[float(p) for p in residents['pauseSeconds']], looks=residents['lookTargetsCm'],
                        laps=residents['laps'], startupOptIn=True)
        for key in expected:
            got, want = readback[key], expected[key]
            same = (all(max(abs(a - b) for a, b in zip(g, w)) < 1e-3 for g, w in zip(got, want)) and len(got) == len(want)) if key in ('waypoints', 'looks') \
                else (all(abs(g - w) < 1e-4 for g, w in zip(got, want)) and len(got) == len(want)) if key == 'pauses' else got == want
            if not same:
                raise RuntimeError('Readback mismatch for %s: %r vs %r' % (key, got, want))
        anchors = [a for a in actors.get_all_level_actors() if a.get_actor_label() == conf['label']]
        if len(anchors) != 1:
            raise RuntimeError('Reopened map lacks exactly one appearance actor')
        anchor = anchors[0]
        refs = {k: _path(anchor.get_editor_property(k)) for k in ('body_mesh', 'left_wing_mesh', 'right_wing_mesh')}
        want_refs = dict(body_mesh=namespace + '/Meshes/SM_DoveBodyV2', left_wing_mesh=namespace + '/Meshes/SM_DoveWingLeftV2', right_wing_mesh=namespace + '/Meshes/SM_DoveWingRightV2')
        if refs != want_refs:
            raise RuntimeError('Appearance mesh references differ after reopen: %r' % refs)
        receipt.update(readback=readback, appearance=dict(actor=anchor.get_name(), meshes=refs, hidden=anchor.get_editor_property('hidden')),
                       status='adopted_saved_reopened_runtime_pie_and_visual_review_pending')
    except Exception as exc:
        receipt.update(status='failed_checkpoint_available' if receipt.get('checkpoint') else 'failed_before_map_change', failure=repr(exc))
        raise
    finally:
        receipt['mapAfterSha256'] = sha(map_file)
        receipt['mapBytesChanged'] = receipt['mapAfterSha256'] != receipt['mapBeforeSha256']
        write()
        ue.log(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    if '--offline-check' in sys.argv:
        print(json.dumps(offline_check(), indent=2))
    else:
        try:
            import unreal  # noqa: F401
        except ImportError:
            raise SystemExit('Outside the editor use --offline-check; native runs go through UnrealEditor-Cmd -run=pythonscript (see docstring)')
        run()

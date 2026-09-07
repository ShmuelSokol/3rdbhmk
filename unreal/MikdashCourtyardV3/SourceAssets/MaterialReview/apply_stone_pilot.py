"""Explicit four-component finish pilot; import has no effects.

Call prepare() to create UNASSIGNED materials; inspect shader compilation.
Call apply() separately to assign them and save the current Courtyard map.
No geometry/material-slot rebuilding; original component overrides are retained
in a separate receipt. Does not overwrite the canonical material receipt.
"""
from pathlib import Path
import hashlib
import json
import runpy
import time
import unreal

FOLDER = Path(__file__).resolve().parent
LEVEL = '/Game/MikdashV3/Maps/Courtyard'
RECEIPT = 'stone-finish-pilot-review.json'
INPUTS = ['stone-pilot-plan.json', 'canonical-material-profiles.json',
          'stone_pilot_material.py', 'stone_pilot.hlsl']


def _path(obj):
    return obj.get_path_name() if obj else None


def _check(condition, message):
    if not condition:
        raise RuntimeError(message)


def _sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def _json(file):
    return json.loads(file.read_text(encoding='utf-8-sig'))


def _write(file, data):
    file.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def _preflight():
    assets = Path(unreal.SystemLibrary.get_project_directory()).resolve() / 'SourceAssets'
    plan = _json(FOLDER / 'stone-pilot-plan.json')
    manifest_file = assets / 'architecture-manifest.json'
    _check(_sha(manifest_file) == plan['manifestSha256'], 'Pilot plan manifest hash mismatch')
    manifest = {r['assetName']: r for r in _json(manifest_file)['meshes']}
    _check(len(manifest) == 2633 and len(plan['targets']) == 4, 'Expected exact 2633-mesh manifest and four pilot targets')
    canonical_file = assets / 'canonical-material-review.json'
    canonical = _json(canonical_file)
    _check(canonical['status'] == 'SAVED_REQUIRES_VISUAL_REVIEW' and canonical['appliedSlotCount'] == 2633,
           'Canonical application receipt is not a completed 2633-slot save')
    _check(canonical['manifestSha256'] == plan['manifestSha256'], 'Canonical receipt manifest hash mismatch')
    prior = {(r['assetName'], r['expectedSlotIndex']): r for r in canonical['componentChanges']}
    _check(len(prior) == 2633, 'Canonical receipt has duplicate/missing component changes')
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    _check(not levels.is_in_play_in_editor(), 'Stop PIE before preparing/applying material overrides')
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    _check(world is not None and world.get_path_name().split('.')[0] == LEVEL, 'Open the saved Courtyard map')
    _check(world.get_world_settings() is not None, 'World settings unavailable')
    _check(levels.get_current_level() is not None and levels.get_current_level().get_outer() == world,
           'Current level does not belong to the expected editor world')
    wanted = {r['assetName']: r for r in plan['targets']}
    found = {name: [] for name in wanted}
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = comp.get_editor_property('static_mesh')
            if not mesh:
                continue
            name = mesh.get_name()
            if name.startswith('architecture_'):
                name = name[len('architecture_'):]
            if name in found:
                found[name].append((actor, comp, mesh))
    operations = []
    for name, target in wanted.items():
        _check(len(found[name]) == 1, 'Missing/duplicate pilot component: ' + name)
        actor, comp, mesh = found[name][0]
        record = manifest[name]
        _check(record['sourceName'] == target['sourceName'] and record['sourcePart'] == target['sourcePart']
               and record['semantic'] == target['semantic'], 'Source label/part/semantic mismatch: ' + name)
        if target['finishKind'] == 'vertical':
            _check(name == 'SM_2630_union_Derived_union_of_source_House_walls_and_' and target['profileKey'] == 'blue'
                   and set(plan['restrictedWallSourceIndices']).issubset(record['sourceModelIndices']), 'Unexpected wall scope')
        else:
            _check(record['semantic'] == 'floor' and record['sourcePart'] in ['inner', 'outer']
                   and target['profileKey'] in ['paving', 'innerPaving'], 'Unexpected paving scope')
        slots = mesh.get_editor_property('static_materials')
        _check(len(slots) == 1 and target['slot'] == 0, 'Expected single-slot pilot mesh: ' + name)
        _check(str(slots[0].get_editor_property('imported_material_slot_name')) == target['importedSlotName'],
               'Imported slot mismatch: ' + name)
        source_slot = record['materialSlots'][0]
        _check(source_slot['sourceMaterialKey'] == target['profileKey'] and source_slot['fbxMaterialName'] == target['importedSlotName'],
               'Source material key/name mismatch')
        b = mesh.get_bounding_box()
        actual = {'min': [b.min.x, b.min.y, b.min.z], 'max': [b.max.x, b.max.y, b.max.z]}
        _check(max(abs(actual[k][i] - target['boundsUnrealCm'][k][i]) for k in ['min', 'max'] for i in range(3)) < .5,
               'Pilot mesh bounds mismatch')
        old = prior[(name, 0)]
        _check(comp.get_path_name() == old['component'] and mesh.get_path_name() == old['actualMesh'], 'Canonical receipt component/mesh mismatch')
        _check(_path(comp.get_material(0)) == old['newMaterial'], 'Component changed since canonical save: ' + name)
        r = actor.get_actor_rotation()
        p, s = actor.get_actor_location(), actor.get_actor_scale3d()
        _check(max(abs(v) for v in [p.x, p.y, p.z, r.pitch, r.yaw, r.roll, s.x-1, s.y-1, s.z-1]) < .0001,
               'Pilot world mask requires original identity actor transform')
        operations.append((comp, target, {'actor': actor.get_path_name(), 'component': comp.get_path_name(),
            'mesh': mesh.get_path_name(), 'assetName': name, 'slot': 0,
            'profileKey': target['profileKey'], 'originalEffectiveMaterial': _path(comp.get_material(0)),
            'originalOverrideMaterials': [_path(m) for m in comp.get_editor_property('override_materials')]}))
    metadata = {'manifestSha256': plan['manifestSha256'], 'canonicalReceiptSha256': _sha(canonical_file),
                'inputSha256': {name: _sha(FOLDER / name) for name in INPUTS},
                'world': world.get_path_name(), 'plan': plan}
    return assets, operations, metadata, levels


def prepare():
    """Create three new unassigned materials; no map changes or save."""
    assets, operations, metadata, _ = _preflight()
    output = assets / RECEIPT
    _check(not output.exists(), 'Preserving existing pilot receipt; inspect/archive before preparing another pilot')
    report = dict(metadata, status='PREFLIGHT_PASSED', createdUtc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  visualAcceptance='UNTESTED', shaderCompilation='UNVERIFIED', appliedSlotCount=0,
                  originalComponents=[r for _, _, r in operations], materials={})
    _write(output, report)
    try:
        builder = runpy.run_path(str(FOLDER / 'stone_pilot_material.py'))['create_finish']
        profiles = _json(FOLDER / 'canonical-material-profiles.json')['profiles']
        for _, target, _ in operations:
            key = target['profileKey']
            if key in report['materials']:
                continue
            rgb = profiles[key]['color']
            # A modest same-hue joint tint; artistic finish, not canonical color revision.
            mortar = [v * .86 for v in rgb]
            made = builder(target['finishKind'], rgb, mortar, suffix='Pilot01_' + key)
            report['materials'][key] = made
            _write(output, report)
        report['status'] = 'CREATED_UNASSIGNED_REQUIRES_SHADER_REVIEW'
        _write(output, report)
        unreal.log('Finish pilot materials created UNASSIGNED. Inspect shader compile errors before calling apply().')
        return report
    except Exception as exc:
        report.update(status='MATERIAL_CREATION_FAILED_NO_COMPONENT_CHANGES', error=str(exc))
        _write(output, report)
        raise


def apply():
    """Apply only the four preflighted overrides; explicit call after preparation."""
    assets, operations, metadata, levels = _preflight()
    output = assets / RECEIPT
    report = _json(output)
    _check(report['status'] == 'CREATED_UNASSIGNED_REQUIRES_SHADER_REVIEW', 'Pilot is not ready for first application')
    for key in ['manifestSha256', 'canonicalReceiptSha256', 'inputSha256', 'world']:
        _check(metadata[key] == report[key], 'Pilot input or source state changed after preparation: ' + key)
    _check([r for _, _, r in operations] == report['originalComponents'], 'Original component overrides changed after preparation')
    materials = {key: unreal.load_asset(value['asset']) for key, value in report['materials'].items()}
    _check(all(isinstance(m, unreal.Material) for m in materials.values()), 'Missing prepared native material')
    _check(set(materials) == {'blue', 'paving', 'innerPaving'}, 'Unexpected prepared material profile set')
    report['status'] = 'APPLYING_FOUR_COMPONENT_PILOT'
    report['changes'] = []
    _write(output, report)
    try:
        for comp, target, original in operations:
            material = materials[target['profileKey']]
            comp.set_material(0, material)
            report['appliedSlotCount'] += 1
            report['changes'].append(dict(original, newMaterial=material.get_path_name()))
            _check(comp.get_material(0) == material, 'Pilot material readback failed')
        _write(output, report)
        _check(levels.save_current_level(), 'Could not save current map after pilot overrides')
        report.update(status='SAVED_FOUR_COMPONENT_PILOT_REQUIRES_VISUAL_REVIEW', mapSaved=LEVEL)
        _write(output, report)
        unreal.log('Four component finish pilot saved. Visual and motion review remain UNTESTED.')
        return report
    except Exception as exc:
        report.update(status='FAILED_PARTIAL_PILOT_APPLICATION', error=str(exc))
        _write(output, report)
        raise

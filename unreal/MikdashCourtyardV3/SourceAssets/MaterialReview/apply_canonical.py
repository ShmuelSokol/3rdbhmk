"""Explicit editor-only canonical palette application; no import-time actions.

Reads the two JSON plans beside this file. Preflights every source mesh/slot,
then creates distinct native materials and applies component overrides only.
Does not rebuild meshes, apply procedural stone, or alter water/geometry.
Receipt preserves effective materials AND original override arrays for rollback.
"""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import math
import re
import time
import unreal


MATERIAL_ROOT = '/Game/MikdashV3/MaterialReview/Canonical'
DEFAULT_MAP = '/Game/MikdashV3/Maps/Courtyard'
ARCHITECTURE_ROOT = '/Game/MikdashV3/Architecture/'


def apply(expected_map=DEFAULT_MAP):
    """Run explicitly after saving the imported map and stopping PIE.

    A prior receipt blocks reruns so the first rollback record is preserved.
    Review/archive it deliberately before requesting another application.
    """
    import v3_materials

    project = Path(unreal.SystemLibrary.get_project_directory()).resolve()
    source_dir = project / 'SourceAssets'
    receipt_path = source_dir / 'canonical-material-review.json'
    if not source_dir.is_dir():
        raise RuntimeError('Current project has no SourceAssets directory')
    if receipt_path.exists():
        raise RuntimeError('Preserving existing canonical-material-review.json; inspect it before any rerun')
    report = {'version': 1, 'status': 'PREFLIGHT_STARTED',
              'createdUtc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'project': str(project), 'engine': unreal.SystemLibrary.get_engine_version(),
              'visualAcceptance': 'UNTESTED', 'gameplayAcceptance': 'UNCHANGED_NOT_TESTED',
              'materialRoot': MATERIAL_ROOT, 'componentChanges': [], 'heldSlots': [],
              'originalComponents': [], 'appliedSlotCount': 0,
              'limitations': ['Canonical colors remain the selected reconstruction palette, not prophetic material certainty.',
                              'No procedural stone or water changes; no screenshot acceptance performed.',
                              'Rollback arrays retain None entries and original lengths; effective materials are recorded separately.']}

    def write():
        receipt_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    def asset_path(value):
        return value.get_path_name() if value else None

    def check(condition, message):
        if not condition:
            raise RuntimeError(message)

    try:
        folder = Path(__file__).resolve().parent
        files = {name: (folder / name).read_bytes() for name in
                 ['canonical-material-profiles.json', 'component-material-overrides.json']}
        palette = json.loads(files['canonical-material-profiles.json'].decode('utf-8-sig'))
        plan = json.loads(files['component-material-overrides.json'].decode('utf-8-sig'))
        report['inputSha256'] = {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}
        manifest_bytes = (source_dir / 'architecture-manifest.json').read_bytes()
        report['manifestSha256'] = hashlib.sha256(manifest_bytes).hexdigest()
        check(report['manifestSha256'] == palette['manifestSha256'], 'Architecture manifest hash differs from palette audit')
        manifest = json.loads(manifest_bytes.decode('utf-8-sig'))
        records = {r['assetName']: r for r in manifest['meshes']}
        check(len(records) == len(manifest['meshes']) == manifest['meshCount'] == plan['meshCount'] == 2633,
              'Expected exactly 2633 distinct manifest meshes')
        overrides, held = plan['overrides'], plan['heldSlots']
        check(len(overrides) == plan['targetSlotCount'], 'Target slot count differs from plan')
        check(dict(Counter(r['targetProfileKey'] for r in overrides)) == plan['countsByTargetProfile'],
              'Target profile counts differ from plan')
        check(all(r['targetProfileKey'] != 'water' for r in overrides), 'Water may only occur in held slots')
        check(len(held) == 1 and held[0]['targetProfileKey'] == 'water', 'Expected one explicitly held water slot')
        assignments = overrides + held
        assignment_pairs = [(r['assetName'], r['expectedSlotIndex']) for r in assignments]
        check(len(set(assignment_pairs)) == len(assignment_pairs), 'Duplicate mesh-slot assignment')
        check(set(r['assetName'] for r in assignments) == set(records), 'Plan does not cover exact manifest mesh set')

        native_profiles = {}
        for key in sorted({r['targetProfileKey'] for r in overrides}):
            p = palette['profiles'][key]
            color = p['color']
            check(len(color) == 3 and all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1 for v in color),
                  'Invalid linear RGB for ' + key)
            check(all(math.isfinite(p[v]) and 0 <= p[v] <= 1 for v in ['metalness', 'roughness']),
                  'Invalid material scalar for ' + key)
            native_profiles[key] = {'kind': 'Canonical_' + re.sub(r'[^A-Za-z0-9_]', '_', key),
                                    'color': color, 'metalness': p['metalness'], 'roughness': p['roughness'],
                                    'specular': .5 if p['metalness'] > .5 else .3}
        check(len({p['kind'] for p in native_profiles.values()}) == len(native_profiles), 'Sanitized profile keys collide')

        levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        check(not levels.is_in_play_in_editor(), 'Stop PIE before applying component materials')
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        check(world is not None, 'No current editor world')
        world_path = world.get_path_name()
        report['world'] = world_path
        check(world_path.split('.')[0] == expected_map, 'Current editor world differs from expected map: ' + world_path)
        settings = world.get_world_settings()
        check(settings is not None, 'World.get_world_settings() returned None')
        report['worldSettings'] = settings.get_path_name()
        report['worldGameMode'] = asset_path(settings.get_editor_property('default_game_mode'))
        report['currentLevel'] = asset_path(levels.get_current_level())
        check(levels.get_current_level() is not None and levels.get_current_level().get_outer() == world,
              'Current level does not belong to the expected editor world')

        components = defaultdict(list)
        unexpected = []
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
                mesh = comp.get_editor_property('static_mesh')
                if not mesh:
                    continue
                name = mesh.get_name()
                canonical = name if name in records else name[len('architecture_'):] if name.startswith('architecture_') else None
                if canonical in records:
                    check(mesh.get_path_name().startswith(ARCHITECTURE_ROOT), 'Matching name from unexpected asset folder: ' + mesh.get_path_name())
                    components[canonical].append((actor, comp, mesh))
                elif mesh.get_path_name().startswith(ARCHITECTURE_ROOT):
                    unexpected.append(mesh.get_path_name())
        check(not unexpected, 'Unexpected architecture mesh assets: ' + str(unexpected[:8]))
        check(set(components) == set(records), 'Current map is missing expected architecture meshes: ' + str(sorted(set(records) - set(components))[:8]))
        check(all(len(v) == 1 for v in components.values()), 'Expected one component per source mesh; duplicate placements found')
        report['matchedMeshCount'] = len(components)

        operations = []
        by_asset = defaultdict(list)
        for entry in assignments:
            by_asset[entry['assetName']].append(entry)
        for name, items in by_asset.items():
            actor, comp, mesh = components[name][0]
            slots = mesh.get_editor_property('static_materials')
            check(len(slots) == len(items), 'Slot count differs from complete plan for ' + name)
            check(set(r['expectedSlotIndex'] for r in items) == set(range(len(slots))), 'Noncontiguous planned slots for ' + name)
            old_overrides = list(comp.get_editor_property('override_materials'))
            report['originalComponents'].append({'actor': actor.get_path_name(), 'component': comp.get_path_name(),
                'mesh': mesh.get_path_name(), 'sourceAssetName': name,
                'overrideMaterialPaths': [asset_path(m) for m in old_overrides],
                'overrideArrayLength': len(old_overrides),
                'effectiveMaterialPaths': [asset_path(comp.get_material(i)) for i in range(len(slots))]})
            for entry in items:
                index = entry['expectedSlotIndex']
                check(isinstance(index, int) and 0 <= index < len(slots), 'Invalid slot index on ' + name)
                actual_slot = str(slots[index].get_editor_property('imported_material_slot_name'))
                check(actual_slot == entry['expectedImportedMaterialSlotName'],
                      'Imported material slot name/index mismatch: ' + name + ' slot ' + str(index) + ' actual=' + actual_slot)
                detail = dict(entry, actor=actor.get_path_name(), component=comp.get_path_name(),
                              actualMesh=mesh.get_path_name(), originalEffectiveMaterial=asset_path(comp.get_material(index)))
                if entry in held:
                    report['heldSlots'].append(detail)
                else:
                    operations.append((comp, index, entry['targetProfileKey'], detail))
        check(len(operations) == len(overrides), 'Resolved operation count differs from plan')
        report['status'] = 'PREFLIGHT_PASSED_ORIGINALS_RECORDED'
        write()  # Rollback evidence exists before any asset or scene changes.

        native = {}
        previous_destination = v3_materials.DEST
        try:
            # Existing creator adds /Materials; canonical assets stay isolated
            # beneath the requested Canonical namespace, never in original assets.
            v3_materials.DEST = MATERIAL_ROOT
            for key, profile in native_profiles.items():
                native[key] = v3_materials.create_native_material(profile)
                check(native[key] is not None, 'Material factory returned None for ' + key)
                check(native[key].get_path_name().startswith(MATERIAL_ROOT + '/Materials/'), 'Unexpected created material path')
        finally:
            v3_materials.DEST = previous_destination
        check(len({m.get_path_name() for m in native.values()}) == len(native), 'Canonical materials were incorrectly deduplicated')
        report['nativeMaterials'] = {key: {'path': m.get_path_name(), 'profile': native_profiles[key]} for key, m in native.items()}
        report['status'] = 'MATERIALS_READY_APPLYING_COMPONENT_OVERRIDES'
        write()

        for comp, index, key, detail in operations:
            comp.set_material(index, native[key])
            detail['newMaterial'] = native[key].get_path_name()
            report['componentChanges'].append(detail)
            report['appliedSlotCount'] += 1
            check(comp.get_material(index) == native[key], 'Component material readback failed: ' + comp.get_path_name())
        for held_item in report['heldSlots']:
            comp = components[held_item['assetName']][0][1]
            check(asset_path(comp.get_material(held_item['expectedSlotIndex'])) == held_item['originalEffectiveMaterial'], 'Held water material changed')
        report['status'] = 'COMPONENT_READBACK_PASSED_AWAITING_MAP_SAVE'
        write()
        check(levels.save_current_level(), 'Map save failed; component overrides may remain unsaved in editor')
        report['status'] = 'SAVED_REQUIRES_VISUAL_REVIEW'
        report['mapSaved'] = expected_map
        report['heldWaterUnchanged'] = True
        write()
        unreal.log('Canonical palette applied; visual review REQUIRED. Receipt: ' + str(receipt_path))
        return report
    except Exception as exc:
        report['status'] = 'FAILED_NO_COMPONENT_CHANGES' if report['appliedSlotCount'] == 0 else 'FAILED_PARTIAL_COMPONENT_APPLICATION'
        report['error'] = str(exc)
        report['rollbackInstruction'] = 'Use originalComponents overrideMaterialPaths (None means inherit mesh slot), not merely effective paths; first inspect applied count. Original mesh materials and geometry were never edited.'
        write()
        raise

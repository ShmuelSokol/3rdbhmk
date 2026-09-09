"""Build near-camera MetaHuman characters from the SHIPPED PRESETS, with no Epic cloud call.

Why this script exists alongside release_metahuman_enable.py
-----------------------------------------------------------
release_metahuman_enable.py takes the blank-character route: create a UMetaHumanCharacter with
MetaHumanCharacterFactoryNew, shape it, then pay RequestAutoRigging + RequestTextureSources,
which are Epic CLOUD service calls. CanBuildMetaHuman() stays false until both succeed
(MetaHumanCharacterEditorSubsystem.cpp:2238-2274 checks GetRiggingState()==Rigged AND
HasHighResolutionTextures()). This machine has NEVER signed in to those services - verified,
not assumed: no Epic/EOS entry in the Windows Credential Manager, an empty
HKCU\\Software\\Epic Games\\EOS\\MainService, and no EOS_Auth_Login / PersistentAuth /
AccountPortal line anywhere in the editor logs. So that route is blocked behind a one-time GUI
sign-in.

This script takes the other route. The 29 assets under /MetaHumanCharacter/Optional/Presets are
themselves UMetaHumanCharacter assets, and they ship ALREADY RIGGED AND ALREADY TEXTURED - each
package serialises bHasHighResolutionTextures and SynthesizedFaceTexturesInfo, and
UMetaHumanCharacter::bHasHighResolutionTextures defaults to false (MetaHumanCharacter.h:402),
so a non-default serialisation means true. They are 8.9-10.0 MB each on disk, which is that
texture payload. Duplicating one therefore produces a character that can be built immediately.

That inference is CHECKED, not trusted: the script reads has_high_resolution_textures and
can_build_meta_human back natively per character and refuses to build any character whose
readback disagrees, recording the refusal instead of silently calling a cloud service.

What it does, per character, from Scripts/release_metahuman_build.spec.json
--------------------------------------------------------------------------
  1. EditorAssetLibrary.duplicate_asset(preset) -> /Game/MetaHumans/Source/<name>
  2. try_add_object_to_edit
  3. CLEAR the Outfits slot. Every preset selects WI_DefaultGarment, and that is a modern
     crewneck T-shirt and shorts - the only outfit in the entire MetaHuman plugin tree. An
     uncleared duplicate walks the courtyard in streetwear.
  4. clear the slots the roster names (Beard/Mustache for the women), then add and select the
     roster's grooms per slot with try_add_item_from_wardrobe_item + try_add_slot_selection
  5. best-effort Melanin on the greying grooms, via assemble_for_preview +
     get_instance_parameters; a failure is recorded, never raised
  6. read has_high_resolution_textures and can_build_meta_human
  7. build_meta_human, OPTIMIZED / MEDIUM, into /Game/MetaHumans
  8. save, drop the edit scope, write the character into the resume marker

Offline (no engine):
    python Scripts/release_metahuman_build.py
Verifies the spec against the engine tree on disk - every preset and every named groom - and
prints the plan and the texture budget. Changes nothing.

Native, ONE character per invocation, serial, no other native job running:

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe" ^
    "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject" ^
    -run=pythonscript ^
    -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_metahuman_build.py" ^
    -MetaHumanBuildRun -unattended -nullrhi ^
    -NoMetaHumanAccountPortalLoginFallback ^
    -abslog="C:/Mikdash/Working-5.8/Release-MetaHumanBuild-01.log"

  Re-run the SAME command once per character; the marker at
  SourceAssets/characters-review/MetaHumanV1/build-progress.json decides what is next, so a
  crash costs one character and never the batch.

  -NoMetaHumanAccountPortalLoginFallback is NOT optional. There is no FApp::IsUnattended() or
  IsRunningCommandlet() guard anywhere in the MetaHuman auth path, so an -unattended commandlet
  that touches a cloud service will still try to raise the EOS account-portal UI and block on an
  invisible window. That switch (MetaHumanCloudAuthentication.cpp:262) makes it fail loudly.
  This script should never reach an auth path at all; the switch is the seatbelt.

Switches:
  -MetaHumanBuildRun          do the native pass (without it, native run does the offline check)
  -MetaHumanBuildCount=N      build N characters in this invocation instead of the spec's 1
  -MetaHumanBuildOnly=<name>  build exactly this roster entry
  -MetaHumanForce             allow overwriting an existing character asset
  -MetaHumanNoBuild           do everything except build_meta_human (asset + grooms only)

The editor target MUST be rebuilt before ANY of this: MetaHumanSDK and MetaHumanCharacter carry
Source modules and this project has its own MikdashRuntime module.

Scope: no map is opened, spawned into or saved. Nothing here is visual acceptance
(AGENTS.md hard rule 7). Placing MetaHumans in the Walkthrough map is a separate, checkpointed
job. These are fictional demonstration figures and assert nothing about priestly status,
purity, census or permission to serve.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_metahuman_build.spec.json'


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    assert spec['specVersion'] == 1, 'unexpected specVersion'
    assert spec['projectDir'] == str(ROOT), 'spec projectDir does not match this file'
    return spec


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def engine_content(spec):
    return Path(spec['engineDir']) / 'Engine/Plugins/MetaHuman/MetaHumanCharacter/Content'


def groom_object_path(spec, slot, item):
    folder = spec['wardrobe']['groomFolderForSlot'][slot]
    return '%s/%s/%s.%s' % (spec['groomBindingFolder'], folder, item, item)


def preset_object_path(spec, preset):
    return '%s/%s.%s' % (spec['presetFolder'], preset, preset)


def marker_path(spec):
    return ROOT / spec['receipts']['marker']


def read_marker(spec):
    path = marker_path(spec)
    if not path.is_file():
        return {'completed': [], 'failed': {}}
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    data.setdefault('completed', [])
    data.setdefault('failed', {})
    return data


def write_marker(spec, data):
    path = marker_path(spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def write_receipt(spec, report, kind):
    folder = ROOT / spec['receipts']['folder']
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ('%s%s-%s.json' % (spec['receipts']['prefix'], kind, stamp()))
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return path


# --------------------------------------------------------------------------
# Offline check - engine tree on disk only, no unreal import
# --------------------------------------------------------------------------

def offline_check(write=True):
    spec = load_spec()
    content = engine_content(spec)
    optional = content / 'Optional'
    report = {
        'kind': 'offline_check',
        'generatedUtc': stamp(),
        'scope': 'Static file inspection of the engine plugin tree. No engine, no asset, no map, '
                 'no visual acceptance.',
        'purpose': spec['purpose'],
        'cloud': spec['cloud'],
        'textureBudget': spec['textureBudget'],
        'optionalCoreDataRoot': {'path': str(optional), 'exists': optional.is_dir()},
        'characters': [],
        'blockers': [],
        'limitations': spec['limitations'],
    }
    if not optional.is_dir():
        report['blockers'].append(
            'MetaHuman Creator Core Data is not installed: %s does not exist. Without it there '
            'are no presets and no grooms, and this whole route is unavailable.' % optional)

    presets_dir = optional / 'Presets'
    report['presetsAvailable'] = sorted(p.stem for p in presets_dir.glob('*.uasset')) if presets_dir.is_dir() else []
    for character in spec['characters']:
        row = {
            'name': character['name'],
            'role': character['role'],
            'preset': character['preset'],
            'presetEvidence': character['presetEvidence'],
            'assetPath': '%s/%s' % (spec['targetFolders']['characterFolder'], character['name']),
            'grooms': {},
            'clearSlots': list(character.get('clearSlots', [])),
            'missing': [],
        }
        preset_file = presets_dir / (character['preset'] + '.uasset')
        row['presetFile'] = {'path': str(preset_file), 'exists': preset_file.is_file(),
                             'bytes': preset_file.stat().st_size if preset_file.is_file() else None}
        if not preset_file.is_file():
            row['missing'].append('preset %s' % character['preset'])
        for slot, item in character['grooms'].items():
            folder = spec['wardrobe']['groomFolderForSlot'][slot]
            item_file = optional / 'Grooms' / 'Bindings' / folder / (item + '.uasset')
            row['grooms'][slot] = {'item': item, 'objectPath': groom_object_path(spec, slot, item),
                                   'exists': item_file.is_file()}
            if not item_file.is_file():
                row['missing'].append('%s %s' % (slot, item))
        if row['missing']:
            report['blockers'].append('%s: missing %s' % (character['name'], row['missing']))
        report['characters'].append(row)

    clothing = optional / 'Clothing'
    report['clothing'] = {
        'path': str(clothing),
        'wardrobeItems': sorted(p.stem for p in clothing.glob('WI_*.uasset')) if clothing.is_dir() else [],
        'note': spec['wardrobe']['whyClear'],
        'periodGarments': spec['wardrobe']['periodGarments'],
    }
    report['marker'] = read_marker(spec)
    report['status'] = 'offline_ok' if not report['blockers'] else 'offline_blockers_recorded'
    if write:
        report['receipt'] = str(write_receipt(spec, report, 'offline'))
    print(json.dumps(report, indent=2))
    return report


# --------------------------------------------------------------------------
# Native
# --------------------------------------------------------------------------

def _switch(u, name):
    try:
        return name.lower() in u.SystemLibrary.get_command_line().lower()
    except Exception:
        return False


def _switch_value(u, name, default):
    try:
        parts = u.SystemLibrary.get_command_line().split()
    except Exception:
        return default
    prefix = name.lower() + '='
    for part in parts:
        if part.lower().lstrip('-').startswith(prefix.lstrip('-')):
            return part.split('=', 1)[1].strip('"')
    return default


def _guards(u, spec, force):
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    assert editor.get_game_world() is None, 'refusing: a game world (PIE) is running'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'refusing: dirty map packages'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'refusing: dirty content packages'
    assert Path(u.Paths.project_dir()).resolve() == ROOT.resolve(), 'refusing: wrong project'
    for cls in ('MetaHumanCharacter', 'MetaHumanCharacterEditorSubsystem',
                'MetaHumanWardrobeItem', 'MetaHumanPipelineSlotSelection', 'MetaHumanPaletteItemKey'):
        assert hasattr(u, cls), (
            'refusing: unreal.%s is not reflected - the MetaHuman plugins are not enabled, or the '
            'editor target has not been rebuilt since they were added' % cls)
    _ = force  # the per-character overwrite check is per character, below


def _clear_slot(u, character, slot, row):
    """Deselect whatever the preset had in this slot. Empty key == nothing selected."""
    try:
        character.internal_collection.default_instance.set_single_slot_selection(
            slot_name=slot, item_key=u.MetaHumanPaletteItemKey())
        row['clearedSlots'].append(slot)
    except Exception as exc:
        row['errors'].append('could not clear slot %r: %r' % (slot, exc))


def _wear_groom(u, spec, character, slot, item, row):
    path = groom_object_path(spec, slot, item)
    wardrobe_item = u.load_asset(path)
    if wardrobe_item is None:
        row['errors'].append('groom wardrobe item not found: %s' % path)
        return None
    key = character.internal_collection.try_add_item_from_wardrobe_item(slot, wardrobe_item)
    if key is None:
        row['errors'].append('try_add_item_from_wardrobe_item failed for %s / %s' % (slot, item))
        return None
    selection = u.MetaHumanPipelineSlotSelection(slot_name=slot, selected_item=key)
    if not character.internal_collection.default_instance.try_add_slot_selection(selection):
        row['errors'].append('try_add_slot_selection failed for %s / %s' % (slot, item))
        return None
    row['groomsWorn'][slot] = item
    return key


def _apply_melanin(u, subsystem, character, keys, wanted, row):
    """Grey a groom. Needs a preview assemble first; best effort, recorded on failure."""
    try:
        subsystem.assemble_for_preview(character=character)
    except Exception as exc:
        row['errors'].append('assemble_for_preview failed, Melanin skipped: %r' % exc)
        return
    for slot, value in wanted.items():
        key = keys.get(slot)
        if key is None:
            row['errors'].append('Melanin skipped for %s: no item key' % slot)
            continue
        try:
            item_path = u.MetaHumanPaletteItemPath(item_key=key)
            parameters = character.internal_collection.default_instance.get_instance_parameters(
                item_path=item_path)
            found = [p for p in parameters if str(p.name) == 'Melanin']
            if not found:
                row['errors'].append('Melanin parameter not offered by the %s groom' % slot)
                continue
            found[0].set_float(value=float(value))
            row['melaninApplied'][slot] = float(value)
        except Exception as exc:
            row['errors'].append('Melanin failed for %s: %r' % (slot, exc))


def build_one(u, spec, character, force, do_build):
    row = {
        'name': character['name'],
        'role': character['role'],
        'preset': character['preset'],
        'presetEvidence': character['presetEvidence'],
        'stage': 'start',
        'clearedSlots': [],
        'groomsWorn': {},
        'melaninApplied': {},
        'errors': [],
    }
    folder = spec['targetFolders']['characterFolder']
    target = '%s/%s' % (folder, character['name'])
    subsystem = u.get_editor_subsystem(u.MetaHumanCharacterEditorSubsystem)

    if u.EditorAssetLibrary.does_asset_exist(target) and not force:
        row['stage'] = 'refused'
        row['errors'].append('%s already exists (AGENTS.md hard rule 4). Checkpoint and rerun '
                             'with -MetaHumanForce.' % target)
        return row

    row['stage'] = 'duplicate'
    source = preset_object_path(spec, character['preset'])
    if u.load_asset(source) is None:
        row['errors'].append('preset not found: %s' % source)
        row['stage'] = 'failed'
        return row
    if u.EditorAssetLibrary.does_asset_exist(target):
        u.EditorAssetLibrary.delete_asset(target)
    duplicated = u.EditorAssetLibrary.duplicate_asset(source, target)
    if duplicated is None:
        row['errors'].append('duplicate_asset returned None for %s -> %s' % (source, target))
        row['stage'] = 'failed'
        return row
    row['assetPath'] = duplicated.get_path_name()

    if not subsystem.try_add_object_to_edit(duplicated):
        row['errors'].append('try_add_object_to_edit failed (already open for edit?)')
        row['stage'] = 'failed'
        return row
    try:
        # What the preset shipped with, before anything is changed. This is the evidence for the
        # whole no-cloud claim, so it is recorded whether or not it is convenient.
        row['stage'] = 'inspect'
        row['presetHadHighResolutionTextures'] = bool(duplicated.has_high_resolution_textures)
        row['presetCanBuild'] = bool(subsystem.can_build_meta_human(duplicated, True))

        row['stage'] = 'wardrobe'
        # The outfit slot goes FIRST and unconditionally: every preset selects WI_DefaultGarment,
        # which is a modern crewneck T-shirt and shorts.
        if spec['wardrobe']['clearOutfitSlotFirst']:
            _clear_slot(u, duplicated, 'Outfits', row)
        for slot in character.get('clearSlots', []):
            _clear_slot(u, duplicated, slot, row)

        keys = {}
        for slot, item in character['grooms'].items():
            key = _wear_groom(u, spec, duplicated, slot, item, row)
            if key is not None:
                keys[slot] = key

        if character.get('groomMelanin'):
            row['stage'] = 'melanin'
            _apply_melanin(u, subsystem, duplicated, keys, character['groomMelanin'], row)

        row['stage'] = 'gate'
        row['hasHighResolutionTextures'] = bool(duplicated.has_high_resolution_textures)
        row['canBuild'] = bool(subsystem.can_build_meta_human(duplicated, True))

        if do_build:
            if not row['canBuild']:
                row['stage'] = 'refused_build'
                row['errors'].append(
                    'can_build_meta_human is false, so nothing was built and NO cloud service was '
                    'called. CanBuildMetaHuman needs GetRiggingState()==Rigged and '
                    'HasHighResolutionTextures(); presetHadHighResolutionTextures=%r, '
                    'presetCanBuild=%r. If the preset itself already failed the gate, the '
                    'no-cloud route does not hold for this preset and the cloud route in '
                    'release_metahuman_enable.py applies, after the one-time GUI sign-in in '
                    'gui-steps.md.' % (row.get('presetHadHighResolutionTextures'),
                                       row.get('presetCanBuild')))
            else:
                row['stage'] = 'build'
                params = u.MetaHumanCharacterEditorBuildParameters()
                params.pipeline_type = getattr(u.MetaHumanDefaultPipelineType,
                                               spec['build']['pipelineType'])
                params.pipeline_quality = getattr(u.MetaHumanQualityLevel,
                                                  spec['build']['pipelineQuality'])
                params.absolute_build_path = spec['targetFolders']['buildFolder']
                params.common_folder_path = spec['targetFolders']['commonFolder']
                params.enable_wardrobe_item_validation = bool(
                    spec['build']['enableWardrobeItemValidation'])
                subsystem.build_meta_human(character=duplicated, params=params)
                row['built'] = True
        else:
            row['built'] = False
            row['errors'].append('-MetaHumanNoBuild: asset and grooms only, nothing assembled')
    except Exception as exc:
        row['errors'].append(repr(exc))
        row['stage'] = 'failed'
    finally:
        if subsystem.is_object_added_for_editing(duplicated):
            subsystem.remove_object_to_edit(duplicated)

    row['saved'] = bool(u.EditorAssetLibrary.save_loaded_asset(duplicated, False))
    if row['stage'] not in ('failed', 'refused', 'refused_build'):
        row['stage'] = 'done'
    return row


def run():
    import unreal as u
    spec = load_spec()
    force = _switch(u, '-MetaHumanForce')
    do_build = not _switch(u, '-MetaHumanNoBuild')
    only = _switch_value(u, '-MetaHumanBuildOnly', None)
    try:
        count = int(_switch_value(u, '-MetaHumanBuildCount', spec['build']['charactersPerInvocation']))
    except (TypeError, ValueError):
        count = int(spec['build']['charactersPerInvocation'])

    marker = read_marker(spec)
    roster = spec['characters']
    if only:
        pending = [c for c in roster if c['name'] == only]
    else:
        pending = [c for c in roster if c['name'] not in marker['completed']]
    pending = pending[:max(1, count)]

    report = {
        'kind': 'native_build',
        'generatedUtc': stamp(),
        'status': 'starting',
        'scope': 'Character assets and their assembled output only. No map opened, spawned into '
                 'or saved. No visual, LOD, performance or packaged acceptance '
                 '(AGENTS.md hard rule 7).',
        'route': 'preset duplication - NO Epic cloud call is made by this script',
        'switches': {'force': force, 'build': do_build, 'only': only, 'count': count},
        'alreadyCompleted': list(marker['completed']),
        'attempting': [c['name'] for c in pending],
        'characters': [],
        'errors': [],
        'limitations': spec['limitations'],
    }
    receipt = write_receipt(spec, report, 'native')

    def flush():
        receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    try:
        _guards(u, spec, force)
        if not pending:
            report['status'] = 'nothing_pending_all_roster_entries_completed'
            return report
        for character in pending:
            row = build_one(u, spec, character, force, do_build)
            report['characters'].append(row)
            if row['stage'] == 'done' and row.get('built'):
                if row['name'] not in marker['completed']:
                    marker['completed'].append(row['name'])
                marker['failed'].pop(row['name'], None)
            else:
                marker['failed'][row['name']] = {'stage': row['stage'], 'errors': row['errors']}
            write_marker(spec, marker)
            flush()
        failed = [r['name'] for r in report['characters'] if r['errors']]
        report['status'] = ('built_pending_visual_review' if not failed
                            else 'partial_see_per_character_errors')
    except Exception as exc:
        report['errors'].append(repr(exc))
        report['status'] = 'failed'
    finally:
        report['finishedUtc'] = stamp()
        report['marker'] = read_marker(spec)
        flush()
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    if 'unreal' in sys.modules:
        import unreal as _u
        if _switch(_u, '-MetaHumanBuildRun'):
            run()
        else:
            offline_check()
    else:
        offline_check()

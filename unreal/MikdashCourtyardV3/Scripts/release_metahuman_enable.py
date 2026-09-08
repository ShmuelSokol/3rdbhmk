"""Enable the UE 5.8 native MetaHuman plugins and author five MetaHuman Character assets from Python.

UE 5.8 ships MetaHuman natively at C:/Program Files/Epic Games/UE_5.8/Engine/Plugins/MetaHuman.
NO Fab download is needed for the plugins themselves. There is exactly one paid-for-with-clicks
prerequisite left, and one cloud dependency:

  * "MetaHuman Creator Core Data" (the plugin's Content/Optional folder) is an Epic Games Launcher
    engine OPTION and is NOT installed on this machine. Without it there is no skin texture
    synthesis, no presets, NO GROOMS AT ALL (so no beards), and no stock clothing.
  * Auto-rigging and high-resolution textures are Epic CLOUD service calls that need a signed-in
    Epic account. CanBuildMetaHuman() stays false until both have run.

Everything else is scriptable, and this script does it. See
SourceAssets/characters-review/MetaHumanV1/gui-steps.md for the click-path that covers the rest.

What it does, in order (every number and every asset path comes from
Scripts/release_metahuman_enable.spec.json):

  1. offline_check() - no engine. Verifies the .uproject Plugins array carries the original three
     entries unchanged plus the three MetaHuman entries; walks the engine plugin tree and reports
     every .uplugin, its EnabledByDefault/Beta/Experimental flags and its dependency list; confirms
     the shipped identity-template / build-pipeline / crowd assets exist; probes for the Optional
     Core Data exactly the way FMetaHumanCharacterEditorModule::IsOptionalMetaHumanContentInstalled()
     does; and prints the authoring plan. Writes a receipt, changes nothing.
  2. run(create=True) - native. Guards (right project, no game world, no dirty packages, plugins
     loaded, target folder empty), then per character in the spec:
       a. AssetTools.create_asset(MetaHumanCharacter, MetaHumanCharacterFactoryNew) into
          /Game/MetaHumans/Source
       b. subsystem.try_add_object_to_edit(character)
       c. get_body_constraints -> resolve the spec's absolute_cm / range_fraction targets against
          each constraint's live Min/Max -> set_body_constraints -> commit_body_state
       d. get_face_model_coefficients -> seeded bounded jitter -> set_face_model_coefficients ->
          commit_face_state   (skipped with -MetaHumanNoFaceVariation)
       e. commit_skin_settings with the spec's tone/roughness/texture indices
          (skipped, with a recorded reason, when the Optional Core Data is missing: the texture
          synthesiser is not on disk and would fall back to 128x128 placeholders)
       f. remove_object_to_edit, save the package
     Writes SourceAssets/characters-review/MetaHumanV1/native-metahuman-<stamp>.json with the
     before/after body constraints, face coefficients and skin settings of every character.
  3. run(build=True)  - native + CLOUD. Per character: request_auto_rigging(JOINTS_ONLY, blocking),
     request_texture_sources(blocking), can_build_meta_human, then build_meta_human into
     /Game/MetaHumans (OPTIMIZED / MEDIUM). Refuses per character rather than as a batch so a
     partial cloud failure still leaves a usable receipt.
  4. run(wardrobe=True) - native. For each entry in spec['wardrobe']['garments'] (currently EMPTY,
     because no period-garment mesh exists in this project yet) creates a UMetaHumanWardrobeItem,
     sets principal_asset and pipeline, adds it to each character's internal_collection with
     try_add_item_from_wardrobe_item and selects it with try_add_slot_selection. The 'pipeline'
     write is the one API here with no shipped Epic example; it is probed and the failure is
     recorded rather than raised.

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_metahuman_enable.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-MetaHuman-01.log"

  The editor target MUST be rebuilt first: all three added plugins carry Source modules.
  -nullrhi is fine for step 2. Step 3 (-MetaHumanBuild) talks to the Epic cloud and needs a
  signed-in account; if the account has never been used in this editor the login flow is a browser
  window, which a -unattended commandlet cannot show - do the FIRST auto-rig from the GUI
  (gui-steps.md step 5) and only then batch the rest.

Switches (read from the engine command line):
  -MetaHumanBuild             also run step 3 (cloud auto-rig + textures + assemble).
  -MetaHumanWardrobe          also run step 4 (needs spec wardrobe.garments to be non-empty).
  -MetaHumanNoFaceVariation   leave all five characters on the identical archetype face.
  -MetaHumanForce             allow writing into a non-empty /Game/MetaHumans/Source.

Offline (no engine):  python Scripts/release_metahuman_enable.py

Risks: MetaHuman Creator is IsBetaVersion=true and MetaHuman Crowd is IsExperimentalVersion=true in
5.8.2. The face-coefficient basis is undocumented. Nothing here is visual acceptance
(AGENTS.md hard rule 7) and no map is opened, spawned into or saved.
"""
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_metahuman_enable.spec.json'
UPROJECT = ROOT / 'MikdashCourtyardV3.uproject'


# --------------------------------------------------------------------------
# Spec and pure helpers (no unreal import)
# --------------------------------------------------------------------------

def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    assert spec['specVersion'] == 1, 'unexpected specVersion'
    assert spec['projectDir'] == str(ROOT), 'spec projectDir does not match this file'
    return spec


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def engine_dir(spec):
    return Path(spec['engineDir'])


def check_uproject(spec):
    """The .uproject Plugins array must still carry the original three entries, in order, first."""
    data = json.loads(UPROJECT.read_text(encoding='utf-8'))
    names = [e['Name'] for e in data.get('Plugins', [])]
    preserved = spec['plugins']['preservedUprojectEntries']
    added = spec['plugins']['addedToUproject']
    return {
        'file': str(UPROJECT),
        'pluginNames': names,
        'preservedIntact': names[:len(preserved)] == preserved,
        'allPreservedEnabled': all(e['Enabled'] for e in data.get('Plugins', [])
                                   if e['Name'] in preserved),
        'addedPresent': [n for n in added if n in names],
        'addedMissing': [n for n in added if n not in names],
        'unexpectedExtra': [n for n in names if n not in preserved + added],
    }


def scan_engine_plugins(spec):
    """Read every MetaHuman .uplugin: flags, modules and declared dependencies."""
    root = engine_dir(spec) / 'Engine' / 'Plugins' / 'MetaHuman'
    out = {}
    if not root.is_dir():
        return {'error': 'MetaHuman plugin folder not found: %s' % root}
    for up in sorted(root.glob('*/*.uplugin')):
        d = json.loads(up.read_text(encoding='utf-8'))
        out[up.stem] = {
            'file': str(up),
            'friendlyName': d.get('FriendlyName'),
            'enabledByDefault': d.get('EnabledByDefault'),
            'beta': d.get('IsBetaVersion'),
            'experimental': d.get('IsExperimentalVersion'),
            'modules': [(m['Name'], m.get('Type'), m.get('LoadingPhase')) for m in d.get('Modules', [])],
            'hasSourceModules': bool(d.get('Modules')),
            'dependencies': [p['Name'] for p in d.get('Plugins', [])],
        }
    return out


def check_engine_assets(spec):
    base = engine_dir(spec)
    rows = []
    for rel in spec['engineInventory']['requiredEngineFiles']:
        p = base / rel
        rows.append({'path': str(p), 'exists': p.exists(),
                     'bytes': (p.stat().st_size if p.is_file() else None)})
    return rows


def check_optional_content(spec):
    """Mirror of FMetaHumanCharacterEditorModule::IsOptionalMetaHumanContentInstalled()."""
    probe = spec['engineInventory']['optionalContentProbe']
    root = engine_dir(spec) / probe['root']
    result = {'root': str(root), 'rootExists': root.is_dir(), 'subdirs': {}, 'arFiles': 0}
    for sub in probe['mustContain']:
        result['subdirs'][sub] = (root / sub).is_dir()
    if result['subdirs'].get('TextureSynthesis'):
        result['arFiles'] = len(list((root / 'TextureSynthesis').rglob('*.ar')))
    result['installed'] = bool(result['rootExists']
                               and all(result['subdirs'].values())
                               and result['arFiles'] > 0)
    result['consequencesIfMissing'] = probe['whatIsMissingWithoutIt']
    result['howToInstall'] = probe['howToInstall']
    return result


def resolve_constraint_target(entry, min_v, max_v):
    """Spec constraint -> absolute TargetMeasurement, clamped to the model's own live range."""
    if entry['mode'] == 'absolute_cm':
        value = float(entry['value'])
    elif entry['mode'] == 'range_fraction':
        frac = min(1.0, max(0.0, float(entry['value'])))
        value = min_v + frac * (max_v - min_v)
    else:
        raise ValueError('unknown constraint mode %r' % entry['mode'])
    clamped = min(max_v, max(min_v, value))
    return clamped, (abs(clamped - value) > 1e-6)


def jitter_coefficients(coeffs, seed, scale, floor):
    """Deterministic, bounded perturbation of the face model coefficient vector."""
    rng = random.Random(seed)
    out = []
    for c in coeffs:
        span = max(abs(float(c)) * scale, floor)
        out.append(float(c) + rng.uniform(-span, span))
    return out


def write_receipt(spec, report, kind):
    folder = ROOT / spec['receipts']['folder']
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ('%s%s-%s.json' % (spec['receipts']['prefix'], kind, stamp()))
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return path


# --------------------------------------------------------------------------
# Offline check
# --------------------------------------------------------------------------

def offline_check(write=True):
    spec = load_spec()
    report = {
        'kind': 'offline_check',
        'generatedUtc': stamp(),
        'scope': 'Static file inspection only. No engine, no asset, no map, no visual acceptance.',
        'uproject': check_uproject(spec),
        'enginePlugins': scan_engine_plugins(spec),
        'engineAssets': check_engine_assets(spec),
        'optionalCoreData': check_optional_content(spec),
        'cloud': spec['cloud'],
        'build': spec['build'],
        'plan': [],
        'blockers': [],
        'limitations': spec['limitations'],
    }

    for ch in spec['characters']:
        report['plan'].append({
            'name': ch['name'],
            'role': ch['role'],
            'assetPath': '%s/%s' % (spec['targetFolders']['characterFolder'], ch['name']),
            'constraints': ch['bodyConstraints'],
            'skin': ch['skin'],
            'faceSeed': ch['faceSeed'],
            'faceVariation': spec['faceVariation']['enabled'],
        })

    up = report['uproject']
    if not up['preservedIntact']:
        report['blockers'].append('uproject: the original three plugin entries are no longer first/intact')
    if up['addedMissing']:
        report['blockers'].append('uproject: missing plugin entries %s' % up['addedMissing'])
    missing_assets = [r['path'] for r in report['engineAssets'] if not r['exists']]
    if missing_assets:
        report['blockers'].append('engine assets missing: %s' % missing_assets)
    if not report['optionalCoreData']['installed']:
        report['blockers'].append(
            'MetaHuman Creator Core Data is NOT installed. Skin synthesis, presets, ALL grooms '
            '(including beards) and stock clothing are unavailable. See gui-steps.md step 1.')
    for name in ('MetaHumanCharacter', 'MetaHumanSDK', 'MetaHumanCrowd'):
        if name not in report['enginePlugins']:
            report['blockers'].append('engine plugin not found: %s' % name)

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


def _guards(u, spec, report, force):
    ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    assert ed.get_game_world() is None, 'refusing: a game world (PIE) is running'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'refusing: dirty map packages'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'refusing: dirty content packages'
    assert Path(u.Paths.project_dir()).resolve() == ROOT.resolve(), 'refusing: wrong project'

    for cls in ('MetaHumanCharacter', 'MetaHumanCharacterFactoryNew', 'MetaHumanCharacterEditorSubsystem'):
        assert hasattr(u, cls), 'refusing: unreal.%s not reflected - plugins not enabled or editor not rebuilt' % cls

    folder = spec['targetFolders']['characterFolder']
    registry = u.AssetRegistryHelpers.get_asset_registry()
    existing = [str(a.package_name) for a in registry.get_assets_by_path(folder, recursive=True)]
    report['preexistingInCharacterFolder'] = existing
    if existing and not force:
        raise AssertionError(
            'refusing: %s already contains %d assets (AGENTS.md hard rule 4). '
            'Checkpoint and rerun with -MetaHumanForce.' % (folder, len(existing)))
    return ed


def _apply_body(u, subsystem, character, ch, row):
    live = list(subsystem.get_body_constraints(character))
    by_name = {str(c.name): c for c in live}
    row['bodyConstraintsAvailable'] = sorted(by_name)
    row['bodyConstraintsBefore'] = {str(c.name): {'active': c.is_active,
                                                  'target': c.target_measurement,
                                                  'min': c.min_measurement,
                                                  'max': c.max_measurement} for c in live}
    applied = {}
    for entry in ch['bodyConstraints']:
        name = entry['name']
        if name not in by_name:
            row['errors'].append('body constraint %r not offered by the model' % name)
            continue
        c = by_name[name]
        value, was_clamped = resolve_constraint_target(entry, c.min_measurement, c.max_measurement)
        c.is_active = True
        c.target_measurement = value
        applied[name] = {'mode': entry['mode'], 'spec': entry['value'],
                         'resolved': value, 'clamped': was_clamped,
                         'range': [c.min_measurement, c.max_measurement]}
    row['bodyConstraintsApplied'] = applied
    subsystem.set_body_constraints(character, list(by_name.values()))
    subsystem.commit_body_state(character)
    after = list(subsystem.get_body_constraints(character))
    row['bodyConstraintsAfter'] = {str(c.name): {'active': c.is_active, 'target': c.target_measurement}
                                   for c in after if str(c.name) in applied}


def _apply_face(u, subsystem, character, ch, spec, row):
    fv = spec['faceVariation']
    before = list(subsystem.get_face_model_coefficients(character))
    row['faceCoefficientCount'] = len(before)
    row['faceCoefficientsBefore'] = [float(x) for x in before]
    after = jitter_coefficients(before, ch['faceSeed'], fv['scale'], fv['absoluteFloor'])
    subsystem.set_face_model_coefficients(character, after)
    subsystem.commit_face_state(character)
    readback = [float(x) for x in subsystem.get_face_model_coefficients(character)]
    row['faceCoefficientsRequested'] = after
    row['faceCoefficientsAfter'] = readback
    row['faceCoefficientsChanged'] = any(abs(a - b) > 1e-6 for a, b in zip(before, readback))


def _apply_skin(u, subsystem, character, ch, row):
    s = ch['skin']
    props = u.MetaHumanCharacterSkinProperties()
    props.u = float(s['u'])
    props.v = float(s['v'])
    props.roughness = float(s['roughness'])
    props.face_texture_index = int(s['faceTextureIndex'])
    props.body_texture_index = int(s['bodyTextureIndex'])
    settings = u.MetaHumanCharacterSkinSettings()
    settings.skin = props
    character.preview_material_type = u.MetaHumanCharacterSkinPreviewMaterial.EDITABLE
    subsystem.commit_skin_settings(character, settings)
    row['skinApplied'] = dict(s)


def run(create=True, build=None, wardrobe=None, force=None, face_variation=None):
    import unreal as u
    spec = load_spec()

    build = _switch(u, '-MetaHumanBuild') if build is None else build
    wardrobe = _switch(u, '-MetaHumanWardrobe') if wardrobe is None else wardrobe
    force = _switch(u, '-MetaHumanForce') if force is None else force
    if face_variation is None:
        face_variation = spec['faceVariation']['enabled'] and not _switch(u, '-MetaHumanNoFaceVariation')

    report = {
        'kind': 'native',
        'generatedUtc': stamp(),
        'status': 'starting',
        'scope': 'Asset creation only. No map opened, spawned into or saved. No visual, LOD, '
                 'performance or packaged acceptance (AGENTS.md hard rule 7).',
        'switches': {'create': create, 'build': build, 'wardrobe': wardrobe,
                     'force': force, 'faceVariation': face_variation},
        'optionalCoreData': check_optional_content(spec),
        'characters': [],
        'errors': [],
        'limitations': spec['limitations'],
    }
    receipt = write_receipt(spec, report, 'native')

    def flush():
        receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    try:
        _guards(u, spec, report, force)
        subsystem = u.get_editor_subsystem(u.MetaHumanCharacterEditorSubsystem)
        asset_tools = u.AssetToolsHelpers.get_asset_tools()
        folder = spec['targetFolders']['characterFolder']
        skin_ok = report['optionalCoreData']['installed']
        if not skin_ok:
            report['errors'].append(
                'Skin settings SKIPPED for every character: the texture synthesis model '
                '(Content/Optional/TextureSynthesis) is not installed, so commit_skin_settings '
                'would fall back to 128x128 placeholders. Install MetaHuman Creator Core Data '
                'and rerun, or set skin in the Materials > Skin panel by hand.')

        for ch in spec['characters']:
            row = {'name': ch['name'], 'role': ch['role'], 'errors': [], 'stage': 'create'}
            report['characters'].append(row)
            flush()
            try:
                character = asset_tools.create_asset(
                    asset_name=ch['name'],
                    package_path=folder,
                    asset_class=u.MetaHumanCharacter,
                    factory=u.new_object(type=u.MetaHumanCharacterFactoryNew))
                assert character is not None, 'create_asset returned None'
                row['assetPath'] = character.get_path_name()

                if not subsystem.try_add_object_to_edit(character):
                    raise AssertionError('try_add_object_to_edit failed (already open for edit?)')
                try:
                    row['stage'] = 'body'
                    _apply_body(u, subsystem, character, ch, row)

                    if face_variation:
                        row['stage'] = 'face'
                        _apply_face(u, subsystem, character, ch, spec, row)
                    else:
                        row['faceVariation'] = 'disabled'

                    if skin_ok:
                        row['stage'] = 'skin'
                        _apply_skin(u, subsystem, character, ch, row)
                    else:
                        row['skinApplied'] = None

                    if build:
                        row['stage'] = 'cloud'
                        rig = u.MetaHumanCharacterAutoRiggingRequestParams()
                        rig.blocking = True
                        rig.report_progress = False
                        rig.rig_type = getattr(u.MetaHumanRigType, spec['build']['rigType'])
                        subsystem.request_auto_rigging(character, rig)

                        tex = u.MetaHumanCharacterTextureRequestParams()
                        tex.blocking = True
                        tex.report_progress = False
                        subsystem.request_texture_sources(character, tex)
                        row['hasHighResolutionTextures'] = bool(character.has_high_resolution_textures)

                        row['canBuild'] = bool(subsystem.can_build_meta_human(character, True))
                        if not row['canBuild']:
                            row['errors'].append(
                                'can_build_meta_human is false after the cloud calls - the Epic '
                                'account is probably not signed in, or a service request failed. '
                                'Do one auto-rig from the GUI first (gui-steps.md step 5).')
                        else:
                            row['stage'] = 'assemble'
                            params = u.MetaHumanCharacterEditorBuildParameters()
                            params.pipeline_type = getattr(u.MetaHumanDefaultPipelineType,
                                                           spec['build']['pipelineType'])
                            params.pipeline_quality = getattr(u.MetaHumanQualityLevel,
                                                              spec['build']['pipelineQuality'])
                            params.absolute_build_path = spec['targetFolders']['buildFolder']
                            params.common_folder_path = spec['targetFolders']['commonFolder']
                            params.enable_wardrobe_item_validation = bool(
                                spec['build']['enableWardrobeItemValidation'])
                            subsystem.build_meta_human(character=character, params=params)
                            row['built'] = True
                finally:
                    if subsystem.is_object_added_for_editing(character):
                        subsystem.remove_object_to_edit(character)

                row['stage'] = 'save'
                row['saved'] = bool(u.EditorAssetLibrary.save_loaded_asset(character, False))
                row['stage'] = 'done'
            except Exception as exc:
                row['errors'].append(repr(exc))
                row['stage'] = 'failed'
            flush()

        if wardrobe:
            report['wardrobe'] = _run_wardrobe(u, spec, subsystem)
            flush()

        failed = [r['name'] for r in report['characters'] if r['errors']]
        report['status'] = 'created_pending_visual_review' if not failed else 'partial_see_per_character_errors'
    except Exception as exc:
        report['errors'].append(repr(exc))
        report['status'] = 'failed'
    finally:
        report['finishedUtc'] = stamp()
        flush()
    return report


def _run_wardrobe(u, spec, subsystem):
    """Create wardrobe items for spec['wardrobe']['garments'] and equip them on every character."""
    out = {'garments': [], 'note': spec['wardrobe']['garmentsNote'], 'errors': []}
    garments = spec['wardrobe']['garments']
    if not garments:
        out['errors'].append('spec wardrobe.garments is empty - no period-garment mesh exists in '
                             'this project yet. Nothing to equip.')
        return out

    asset_tools = u.AssetToolsHelpers.get_asset_tools()
    for g in garments:
        row = {'name': g['name'], 'slot': g['slot'], 'errors': []}
        out['garments'].append(row)
        try:
            principal = u.load_asset(g['principalAsset'])
            assert principal is not None, 'principal asset not found: %s' % g['principalAsset']
            item = asset_tools.create_asset(
                asset_name='WI_%s' % g['name'],
                package_path=spec['targetFolders']['wardrobeFolder'],
                asset_class=u.MetaHumanWardrobeItem,
                factory=u.new_object(type=u.MetaHumanWardrobeItemFactory))
            assert item is not None, 'wardrobe item create_asset returned None'
            row['wardrobeItem'] = item.get_path_name()

            # principal_asset is an FEditorOnlyAssetReference (UPROPERTY EditAnywhere).
            item.set_editor_property('principal_asset', principal)
            row['principalAssetSet'] = True

            # 'pipeline' is UPROPERTY(EditAnywhere, Instanced) but private in C++ and has no
            # shipped Python example. Probe it; a failure is a GUI step, not a crash.
            try:
                pipeline_cls = getattr(u, g['pipelineClass'])
                item.set_editor_property('pipeline', u.new_object(type=pipeline_cls, outer=item))
                row['pipelineSet'] = True
            except Exception as exc:
                row['pipelineSet'] = False
                row['errors'].append(
                    'could not set the item pipeline from Python (%r). Open %s and set '
                    'Pipeline by hand - gui-steps.md step 9.' % (exc, row['wardrobeItem']))

            u.EditorAssetLibrary.save_loaded_asset(item, False)

            equipped = []
            for ch in spec['characters']:
                path = '%s/%s.%s' % (spec['targetFolders']['characterFolder'], ch['name'], ch['name'])
                character = u.load_asset(path)
                if character is None:
                    row['errors'].append('character not found: %s' % path)
                    continue
                key = character.internal_collection.try_add_item_from_wardrobe_item(g['slot'], item)
                if key is None:
                    row['errors'].append('try_add_item_from_wardrobe_item failed for %s' % ch['name'])
                    continue
                selection = u.MetaHumanPipelineSlotSelection(slot_name=g['slot'], selected_item=key)
                if character.internal_collection.default_instance.try_add_slot_selection(selection):
                    equipped.append(ch['name'])
                    u.EditorAssetLibrary.save_loaded_asset(character, False)
                else:
                    row['errors'].append('try_add_slot_selection failed for %s' % ch['name'])
            row['equipped'] = equipped
        except Exception as exc:
            row['errors'].append(repr(exc))
    return out


if __name__ == '__main__':
    if 'unreal' in sys.modules:
        run()
    else:
        offline_check()

"""Import PilgrimRigV3 and, only when explicitly allowed, repoint the population.

Two halves, both refusable:

  offline_check()   pure Python. No Unreal. Re-hashes every authored file against
                    Scripts/release_pilgrim_v3.spec.json, re-decodes each GLB and
                    confirms the V3 rest pose still matches PilgrimRigV2's, so the
                    already-imported Idle/Walk clips stay valid motion.

  run(...)          root-only, inside the intended editor. Imports the nine GLBs
                    (skeletal) and OBJs (static crowd) into an isolated namespace,
                    reads the skeleton back, and tries to bind the new meshes to
                    the EXISTING PilgrimRigV2 Skeleton so the existing clips play.
                    It touches the map only when the caller passes
                    allow_population_swap=True, and even then only sets one
                    property on the one population actor named in the spec.

This worker launched no Unreal process and edited no other script, no plugin C++
and no spec it does not own. Nothing here is a visual, cook, packaging or
performance acceptance, and nothing here is a halachic or historical ruling.
"""
import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/PilgrimRigV3'
SPEC = ROOT / 'Scripts/release_pilgrim_v3.spec.json'
MANIFEST = OUT / 'geometry-manifest.json'
DEST = '/Game/MikdashV3/CharacterReview/PilgrimRigV3'
V2_SKELETON_HINT = '/Game/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes'
PEOPLE_SPEC = ROOT / 'Scripts/release_people_v3.spec.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def author():
    """Load the owning generator as a module for its independent GLB decoder."""
    spec = importlib.util.spec_from_file_location('pilgrim_v3', ROOT / 'Scripts/create_pilgrim_v3.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# spec
# ---------------------------------------------------------------------------


def write_spec():
    """Regenerate the human-reviewable plan from the authored manifest."""
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    primary = manifest['variants'][0]['id']
    document = {
        'specVersion': 1,
        'prepared': datetime.now(timezone.utc).date().isoformat(),
        'purpose': ('Human-reviewable plan consumed by Scripts/release_pilgrim_v3.py: import the '
                    'PilgrimRigV3 character set into an isolated review namespace, bind it to the '
                    'existing PilgrimRigV2 Skeleton when the rest pose readback proves compatible, '
                    'and, only on an explicit opt-in, repoint one population actor property. '
                    'Nothing here is visual, runtime, PIE, cook or packaged acceptance.'),
        'projectDir': str(ROOT),
        'destination': DEST,
        'sourceFolder': str(OUT.relative_to(ROOT)).replace('\\', '/'),
        'generator': 'Scripts/create_pilgrim_v3.py',
        'generatorSha256': sha(ROOT / 'Scripts/create_pilgrim_v3.py'),
        'manifestSha256': sha(MANIFEST),
        'triangleBudgetPerCharacter': manifest['triangleBudgetPerCharacter'],
        'rigCompatibility': manifest['rigCompatibility'],
        'existingClipsExpectedToRemainValid': [
            '/Game/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes/PilgrimRigV2A_Pilgrim_Original_Idle',
            '/Game/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes/PilgrimRigV2A_Pilgrim_Original_Walk'],
        'existingSkeletonSearchRoot': V2_SKELETON_HINT,
        'primaryVariant': primary,
        'population': {
            'spec': 'Scripts/release_people_v3.spec.json',
            'actorLabel': 'RELEASE_PeopleV3Population',
            'actorClass': '/Script/MikdashRuntime.MikdashResidentPopulation',
            'propertyToSwap': 'resident_mesh',
            'currentValue': json.loads(PEOPLE_SPEC.read_text(encoding='utf-8-sig'))['rig']['skeletalMesh']
                            if PEOPLE_SPEC.is_file() else None,
            'proposedValue': DEST + '/' + primary + '/SkeletalMeshes/' + primary,
            'gate': ('The swap is refused unless the caller passes allow_population_swap=True AND the '
                     'imported mesh reads back on a skeleton whose bone names and reference transforms '
                     'match PilgrimRigV2. release_people_v3.spec.json is NOT edited by this script.')},
        'variants': [{'id': v['id'], 'label': v['label'], 'triangles': v['triangles'],
                      'skeletalFile': v['skeletalFile'], 'skeletalSha256': v['skeletalSha256'],
                      'staticFile': v['staticFile'], 'staticSha256': v['staticSha256'],
                      'recommendedActorScale': v['recommendedActorScale'],
                      'recommendedIdleClip': v['recommendedIdleClip'],
                      'prop': v['prop']} for v in manifest['variants']],
        'limits': manifest['limits'] + [
            'This script never edits release_people_v3.spec.json, the plugin C++, or any other script.',
            'The five existing RELEASE_Pilgrims_* SkeletalMeshActors are left alone; repointing them is '
            'a separate reviewed decision.']}
    SPEC.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    return document


# ---------------------------------------------------------------------------
# offline
# ---------------------------------------------------------------------------


def offline_check():
    module = author()
    spec = json.loads(SPEC.read_text(encoding='utf-8-sig'))
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'UNKNOWN',
              'destination': DEST, 'variants': [], 'problems': []}
    if sha(ROOT / 'Scripts/create_pilgrim_v3.py') != spec['generatorSha256']:
        report['problems'].append('Generator changed since the spec was written; rerun --write-spec.')
    if sha(MANIFEST) != spec['manifestSha256']:
        report['problems'].append('geometry-manifest.json changed since the spec was written.')
    bones = module.skeleton()
    rig = module.assert_rig_matches_v2(bones)
    if not rig.get('identical_rest_pose'):
        report['problems'].append('Rest pose could not be compared to PilgrimRigV2; existing clips unproven.')
    report['rigCompatibility'] = rig
    for entry in spec['variants']:
        glb = OUT / entry['skeletalFile']
        obj = OUT / entry['staticFile']
        row = {'id': entry['id'], 'triangles': entry['triangles']}
        if not glb.is_file() or not obj.is_file():
            report['problems'].append('Missing authored file for ' + entry['id'])
            row['present'] = False
            report['variants'].append(row)
            continue
        row['present'] = True
        row['skeletalHashMatches'] = sha(glb) == entry['skeletalSha256']
        row['staticHashMatches'] = sha(obj) == entry['staticSha256']
        if not (row['skeletalHashMatches'] and row['staticHashMatches']):
            report['problems'].append('Hash drift for ' + entry['id'] + '; re-author before importing.')
        if entry['triangles'] > spec['triangleBudgetPerCharacter']:
            report['problems'].append('Over triangle budget: ' + entry['id'])
        try:
            row['decode'] = module.glb_decode_checks(glb, bones, entry['triangles'])
        except Exception as error:                                   # noqa: BLE001
            row['decode'] = {'error': str(error)}
            report['problems'].append('GLB decode failed for ' + entry['id'])
        report['variants'].append(row)
    report['status'] = 'READY_FOR_NATIVE_IMPORT' if not report['problems'] else 'BLOCKED'
    report['scope'] = ('Offline byte and rig verification only. Native import, skeleton binding, '
                       'animation playback and any visual judgement remain unperformed.')
    return report


# ---------------------------------------------------------------------------
# native
# ---------------------------------------------------------------------------


def _path(asset):
    return asset.get_path_name().split('.')[0] if asset else None


def _bone_readout(ue, mesh):
    """Bone names and component-space rest positions, via whichever API exists.

    UE's Python surface for Skeleton rest poses moves between versions, so this
    tries a transient component first and records exactly which strategy worked.
    Nothing here guesses: if no strategy returns bones, the caller must treat
    compatibility as UNPROVEN rather than assume it.
    """
    try:
        component = ue.new_object(ue.SkeletalMeshComponent)
        component.set_skeletal_mesh_asset(mesh)
        count = component.get_num_bones()
        if count:
            rows = []
            for i in range(count):
                name = str(component.get_bone_name(i))
                t = component.get_bone_transform(i).translation
                rows.append((name, (t.x, t.y, t.z)))
            return rows, 'transient SkeletalMeshComponent'
    except Exception:                                                # noqa: BLE001
        pass
    try:
        skeleton = mesh.get_editor_property('skeleton')
        tree = skeleton.get_editor_property('bone_tree')
        if tree:
            return [(None, None)] * len(tree), 'bone_tree length only'
    except Exception:                                                # noqa: BLE001
        pass
    return [], 'unavailable'


def _find_existing_skeleton(ue, assets):
    for path in assets.list_assets(V2_SKELETON_HINT, recursive=True, include_folder=False):
        asset = ue.load_asset(path)
        if isinstance(asset, ue.Skeleton):
            return asset
    return None


def _compare_to_reference(ue, mesh, reference_mesh, bones):
    """Compare the imported mesh's bones with the authored rig and, when a
    PilgrimRigV2 mesh is available, with that mesh as actually stored."""
    rows, strategy = _bone_readout(ue, mesh)
    result = {'strategy': strategy, 'boneCount': len(rows), 'expectedBoneCount': len(bones),
              'boneNamesMatchAuthoredRig': None, 'maxRestPositionErrorCm': None,
              'comparedToExistingMesh': _path(reference_mesh)}
    if not rows or rows[0][0] is None:
        result['proven'] = False
        result['reason'] = 'No Python API on this build returned bone names; treat as unproven.'
        return result
    result['boneNamesMatchAuthoredRig'] = [n for n, _ in rows] == [b['name'] for b in bones]
    if reference_mesh is not None:
        other, _ = _bone_readout(ue, reference_mesh)
        if other and other[0][0] is not None and len(other) == len(rows):
            result['boneNamesMatchExistingMesh'] = [n for n, _ in other] == [n for n, _ in rows]
            result['maxRestPositionErrorCm'] = max(
                max(abs(a - b) for a, b in zip(p, q)) for (_, p), (_, q) in zip(rows, other))
    result['proven'] = bool(result['boneNamesMatchAuthoredRig']
                            and result.get('boneNamesMatchExistingMesh')
                            and result['maxRestPositionErrorCm'] is not None
                            and result['maxRestPositionErrorCm'] < 0.01)
    return result


def run(apply=False, allow_population_swap=False, variants=None):
    """Root only, in the intended editor. Import first; swap only when told to."""
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('Stop gameplay first; this never runs against a live PIE session')
    if (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved work preserved; save or discard before importing')

    module = author()
    bones = module.skeleton()
    offline = offline_check()
    if offline['status'] != 'READY_FOR_NATIVE_IMPORT':
        raise RuntimeError('Offline verification blocked: ' + '; '.join(offline['problems']))
    spec = json.loads(SPEC.read_text(encoding='utf-8-sig'))
    selected = [v for v in spec['variants'] if not variants or v['id'] in variants]

    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    receipt = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'started',
               'destination': DEST, 'applyRequested': bool(apply),
               'populationSwapRequested': bool(allow_population_swap),
               'mapMutated': False, 'offline': offline, 'imported': [], 'remaining': []}
    output = OUT / ('native-import-' + stamp() + '.json')
    try:
        if not apply:
            receipt['status'] = 'AUDIT_ONLY_NO_MUTATION'
            receipt['namespaceExists'] = assets.does_directory_exist(DEST)
            receipt['existingSkeleton'] = _path(_find_existing_skeleton(ue, assets))
            receipt['remaining'] = ['Rerun with apply=True to import the authored files.']
            return receipt

        if assets.does_directory_exist(DEST):
            raise RuntimeError('Preserve the existing review namespace; import a distinct version instead')
        existing_skeleton = _find_existing_skeleton(ue, assets)
        receipt['existingSkeleton'] = _path(existing_skeleton)
        if existing_skeleton is None:
            receipt['remaining'].append(
                'PilgrimRigV2 Skeleton not found; the V3 meshes will carry their own skeletons and '
                'the V3 copies of the Idle/Walk clips must be used.')

        for entry in selected:
            folder = DEST + '/' + entry['id']
            row = {'id': entry['id'], 'skeletalMesh': None, 'staticMesh': None,
                   'animations': [], 'skeletonBoundToExisting': False}

            task = ue.AssetImportTask()
            for key, value in dict(filename=str(OUT / entry['skeletalFile']), destination_path=folder,
                                   automated=True, async_=False, replace_existing=False,
                                   save=False).items():
                task.set_editor_property(key, value)
            tools.import_asset_tasks([task])
            objects = list(task.get_objects())
            if not objects:
                objects = [ue.load_asset(p) for p in assets.list_assets(folder, recursive=True,
                                                                        include_folder=False)]
            skeletal = [a for a in objects if isinstance(a, ue.SkeletalMesh)]
            animations = [a for a in objects if isinstance(a, ue.AnimSequence)]
            if len(skeletal) != 1:
                raise RuntimeError('Expected exactly one SkeletalMesh for ' + entry['id']
                                   + '; inspect the partial Interchange assets before retrying')
            mesh = skeletal[0]
            row['skeletalMesh'] = _path(mesh)
            row['animations'] = sorted(_path(a) for a in animations)
            row['importedAnimationCount'] = len(animations)

            if existing_skeleton is not None:
                comparison = _compare_skeletons(ue, mesh.get_editor_property('skeleton'),
                                                existing_skeleton, bones)
                row['skeletonComparison'] = comparison
                compatible = comparison.get('boneNamesMatch') and (
                    comparison.get('maxRestPositionErrorCm') is not None
                    and comparison['maxRestPositionErrorCm'] < 0.01)
                if compatible:
                    # UE 5.8 property setters can silently no-op, so read back.
                    mesh.set_editor_property('skeleton', existing_skeleton)
                    row['skeletonBoundToExisting'] = (
                        _path(mesh.get_editor_property('skeleton')) == _path(existing_skeleton))
                    if not row['skeletonBoundToExisting']:
                        receipt['remaining'].append(
                            entry['id'] + ': skeleton reassignment did not read back; use the V3 '
                            'clips imported alongside this mesh, or retarget in the editor.')
                else:
                    receipt['remaining'].append(
                        entry['id'] + ': skeleton readback did not prove compatibility; existing '
                        'Idle/Walk assets are NOT proven to play on this mesh.')

            for asset in objects:
                assert assets.save_loaded_asset(asset, only_if_is_dirty=False)

            static_task = ue.AssetImportTask()
            for key, value in dict(filename=str(OUT / entry['staticFile']),
                                   destination_path=folder + '/StaticMeshes',
                                   destination_name='SM_' + entry['id'], automated=True, async_=False,
                                   replace_existing=False, save=False).items():
                static_task.set_editor_property(key, value)
            tools.import_asset_tasks([static_task])
            static = [a for a in static_task.get_objects() if isinstance(a, ue.StaticMesh)]
            if len(static) == 1:
                assert assets.save_loaded_asset(static[0], only_if_is_dirty=False)
                row['staticMesh'] = _path(static[0])
                row['staticTriangles'] = static[0].get_num_triangles(0)
            else:
                receipt['remaining'].append(entry['id'] + ': static OBJ import did not yield one '
                                                          'StaticMesh; the crowd copy is missing.')
            receipt['imported'].append(row)

        receipt['status'] = 'IMPORTED_UNPLACED_NATIVE_VISUAL_REVIEW_PENDING'

        # ---- optional, gated, single-property map edit -----------------------
        if allow_population_swap:
            primary = next((r for r in receipt['imported'] if r['id'] == spec['primaryVariant']), None)
            if primary is None or not primary['skeletonBoundToExisting']:
                receipt['remaining'].append(
                    'Population swap refused: the primary variant is not bound to the existing '
                    'PilgrimRigV2 Skeleton, so the population\'s idle/walk references would break.')
            else:
                world = editor.get_editor_world()
                target = spec['population']
                map_file = ROOT / ('Content/' + world.get_outermost().get_name()[6:] + '.umap')
                before = sha(map_file)
                actors = [a for a in ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
                          if a.get_actor_label() == target['actorLabel']]
                if len(actors) != 1:
                    receipt['remaining'].append(
                        'Population swap refused: expected exactly one actor labelled '
                        + target['actorLabel'] + ', found %d.' % len(actors))
                else:
                    owner = actors[0]
                    previous = _path(owner.get_editor_property('resident_mesh'))
                    owner.set_editor_property('resident_mesh', ue.load_asset(primary['skeletalMesh']))
                    now = _path(owner.get_editor_property('resident_mesh'))
                    receipt['populationSwap'] = {'actor': target['actorLabel'], 'previous': previous,
                                                 'requested': primary['skeletalMesh'], 'readback': now,
                                                 'applied': now == primary['skeletalMesh'],
                                                 'mapShaBefore': before}
                    if now == primary['skeletalMesh']:
                        ue.EditorLoadingAndSavingUtils.save_current_level()
                        receipt['mapMutated'] = True
                        receipt['populationSwap']['mapShaAfter'] = sha(map_file)
                    else:
                        receipt['remaining'].append('Population swap did not read back; map left alone.')
        else:
            receipt['remaining'].append(
                'Population still points at PilgrimRigV2. Rerun with allow_population_swap=True, or '
                'set resident_mesh on ' + spec['population']['actorLabel'] + ' by hand to '
                + spec['population']['proposedValue'] + '.')
        receipt['remaining'].append(
            'The five existing RELEASE_Pilgrims_* actors, per-variant assignment, LODs, collision, '
            'navigation, cook and packaged verification all remain open.')
    except Exception as error:                                       # noqa: BLE001
        receipt.update(status='FAILED_PARTIAL_ASSETS_PRESERVED', error=str(error))
        raise
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-spec', action='store_true', help='regenerate the plan from the manifest')
    parser.add_argument('--check', action='store_true', help='offline byte and rig verification')
    args = parser.parse_args()
    if args.write_spec:
        print(json.dumps({'spec': str(SPEC), 'variants': len(write_spec()['variants'])}, indent=2))
    elif args.check:
        result = offline_check()
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result['status'] == 'READY_FOR_NATIVE_IMPORT' else 1)
    else:
        parser.print_help()

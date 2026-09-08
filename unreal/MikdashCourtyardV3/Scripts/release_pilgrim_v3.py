"""Import the PilgrimRigV3 character set into an isolated review namespace.

This script IMPORTS ASSETS. It never places, moves or re-points an actor, and it
never edits the population: the twenty-four existing residents belong to another
system, and repointing them is that system's decision, not this script's. What
this produces is nine SkeletalMeshes with their clips, nine StaticMesh crowd
copies and the materials the OBJ/GLB carry, all under one namespace, verified by
reading the numbers back off the saved assets. The exact command the coordinator
must run to swap them in is printed in the receipt under `handoff`, and running
it is a separate, reviewed decision.

Two halves, both refusable:

  offline_check()   pure Python, no Unreal. Re-hashes every authored file against
                    Scripts/release_pilgrim_v3.spec.json, re-decodes each GLB,
                    re-proves the rig is clip-compatible with PilgrimRigV2, and
                    re-proves that no two variants are the same figure.

  run(apply=True)   root only, inside the intended editor. Guards on project
                    directory, live PIE, the loaded map, and dirty packages;
                    checkpoints the target .umap; imports in resumable batches;
                    saves; reloads each asset from disk and reads triangle
                    counts, bone counts, material slots and clip lengths back
                    numerically; then asserts the .umap is byte-identical,
                    because an import has no business changing the map.

5.8 notes honoured here:
  * property setters (materials included) return False even when they worked, so
    nothing is trusted until it has been read back off the reloaded asset;
  * StaticMesh.get_num_uv_channels() does not exist on this build - UV channel
    count is read off the StaticMeshDescription instead, and recorded as
    unavailable rather than guessed if that fails too;
  * with Nanite enabled get_num_triangles(0) reports the FALLBACK mesh, so the
    tolerance on the triangle readback is stated and the Nanite flag is recorded
    beside it instead of the check silently passing on the wrong number;
  * a zombie UnrealEditor process makes save_loaded_asset return False with no
    other symptom, so a save failure prints that as the first thing to check.

Large imports on this project have had to run in groups to survive memory
limits, so `run` takes a batch size and keeps a resume marker: rerun the same
command and it picks up at the first variant that is not already saved.

Nothing here is a visual, cook, packaging or performance acceptance, and nothing
here is a halachic or historical ruling.
"""
import argparse
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/PilgrimRigV3'
SPEC = ROOT / 'Scripts/release_pilgrim_v3.spec.json'
MANIFEST = OUT / 'geometry-manifest.json'
GENERATOR = ROOT / 'Scripts/create_pilgrim_v3.py'
DEST = '/Game/MikdashV3/CharacterReview/PilgrimRigV3'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
V2_SKELETON_HINT = '/Game/MikdashV3/CharacterReview/PilgrimRigV2'
PEOPLE_SPEC = ROOT / 'Scripts/release_people_v3.spec.json'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
PROGRESS = OUT / 'native-import-progress.json'
DEFAULT_BATCH = 3


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def author():
    """Load the owning generator as a module for its independent GLB decoder."""
    spec = importlib.util.spec_from_file_location('pilgrim_v3', GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# spec
# ---------------------------------------------------------------------------


def write_spec():
    """Regenerate the human-reviewable plan from the authored manifest."""
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    document = {
        'specVersion': 2,
        'prepared': datetime.now(timezone.utc).date().isoformat(),
        'purpose': ('Human-reviewable plan consumed by Scripts/release_pilgrim_v3.py: import the '
                    'PilgrimRigV3 character set into an isolated review namespace and verify it by '
                    'numeric readback off the saved assets. This plan places no actor, edits no '
                    'map and repoints no population. Nothing here is visual, runtime, PIE, cook or '
                    'packaged acceptance.'),
        'projectDir': str(ROOT),
        'destination': DEST,
        'targetMap': TARGET,
        'mapMustNotChange': True,
        'sourceFolder': str(OUT.relative_to(ROOT)).replace('\\', '/'),
        'generator': 'Scripts/create_pilgrim_v3.py',
        'generatorSha256': sha(GENERATOR),
        'manifestSha256': sha(MANIFEST),
        'triangleBudgetPerCharacter': manifest['triangleBudgetPerCharacter'],
        'rigCompatibility': manifest['rigCompatibility'],
        'distinctness': manifest.get('distinctness'),
        'proportionSource': manifest.get('proportionSource'),
        'defaultBatchSize': DEFAULT_BATCH,
        'progressMarker': str(PROGRESS.relative_to(ROOT)).replace('\\', '/'),
        'checkpointRoot': str(CHECKPOINT_ROOT),
        'checkpointPrefix': 'PilgrimV3-',
        'skeleton': {
            'existingSearchRoot': V2_SKELETON_HINT,
            'expectation': ('Each GLB import creates its OWN Skeleton because UE stores a reference '
                            'pose per Skeleton and V3 lengthened the arm and foot bones. The four '
                            'clips travel inside each GLB, so no retarget is needed to play them. '
                            'The already-imported A_Pilgrim_Original_Idle/_Walk assets remain valid '
                            'MOTION for this rig (rotation curves are length-independent) but they '
                            'live on the V2 Skeleton; playing them on a V3 mesh needs a one-click '
                            'retarget in the editor and is NOT attempted by this script.'),
            'jointCount': manifest['rigCompatibility'].get('joints'),
            'movedJoints': manifest['rigCompatibility'].get('movedJoints')},
        'materials': {
            'policy': ('The OBJ carries an MTL with one named material per garment part and the GLB '
                       'carries baseColorFactor plus COLOR_0, so the palette arrives with the mesh. '
                       'This script does NOT flatten the slots onto a shared master - that would '
                       'erase the per-variant palette. It asserts every slot on every saved mesh '
                       'resolves to a non-null MaterialInterface, by readback, and records the '
                       'paths.'),
            'expectedSlotNames': ['Skin', 'Linen', 'Mantle', 'Headcloth', 'Sash', 'Leather',
                                  'Hair', 'Eyes', 'Iris', 'Trim', 'Prop', 'PropGlass', 'Denim'],
            'minimumSlotsPerStaticMesh': 6},
        'population': {
            'spec': 'Scripts/release_people_v3.spec.json',
            'currentValue': (json.loads(PEOPLE_SPEC.read_text(encoding='utf-8-sig'))['rig']['skeletalMesh']
                             if PEOPLE_SPEC.is_file() else None),
            'ownedByThisScript': False,
            'note': ('The twenty-four placed residents and the population actor belong to another '
                     'system. This script never touches them. See `handoff` in the receipt for the '
                     'exact command their owner has to run.')},
        'variants': [{'id': v['id'], 'label': v['label'], 'triangles': v['triangles'],
                      'vertices': v['vertices'],
                      'skeletalFile': v['skeletalFile'], 'skeletalSha256': v['skeletalSha256'],
                      'staticFile': v['staticFile'], 'staticSha256': v['staticSha256'],
                      'staticMaterialFile': v['staticMaterialFile'],
                      'staticVertexFingerprint': v['staticVertexFingerprint'],
                      'recommendedActorScale': v['recommendedActorScale'],
                      'recommendedIdleClip': v['recommendedIdleClip'],
                      'animations': v['animations'],
                      'measuredCm': v['measuredCm'],
                      'prop': v['prop'], 'dress': v['dress']} for v in manifest['variants']],
        'limits': manifest['limits'] + [
            'This script never edits release_people_v3.spec.json, the plugin C++, any map, or any '
            'other script.',
            'No actor of any kind is spawned, moved, deleted or repointed.',
            'Import success is not visual acceptance: nobody has looked at these in the engine.']}
    SPEC.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    return document


# ---------------------------------------------------------------------------
# offline
# ---------------------------------------------------------------------------


def offline_check():
    module = author()
    spec = json.loads(SPEC.read_text(encoding='utf-8-sig'))
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'status': 'UNKNOWN',
              'destination': DEST, 'variants': [], 'problems': []}
    if sha(GENERATOR) != spec['generatorSha256']:
        report['problems'].append('Generator changed since the spec was written; rerun --write-spec.')
    if sha(MANIFEST) != spec['manifestSha256']:
        report['problems'].append('geometry-manifest.json changed since the spec was written.')

    bones = module.skeleton()
    rig = module.assert_rig_matches_v2(bones)
    if not rig.get('existingClipsRemainValid'):
        report['problems'].append('Rig compatibility could not be proven against PilgrimRigV2.')
    report['rigCompatibility'] = rig

    # Re-prove distinctness from the shipped files, not from the manifest's word
    # for it: V3-a claimed nine variants and shipped two identical figures.
    prints = {}
    for entry in spec['variants']:
        obj = OUT / entry['staticFile']
        if obj.is_file():
            verts = [l for l in obj.read_text(encoding='ascii').splitlines() if l.startswith('v ')]
            prints[entry['id']] = hashlib.sha256('\n'.join(verts).encode('ascii')).hexdigest()
    duplicates = [(a, b) for i, a in enumerate(prints) for b in list(prints)[i + 1:]
                  if prints[a] == prints[b]]
    report['distinctStaticGeometry'] = not duplicates
    if duplicates:
        report['problems'].append('Identical static geometry: ' + '; '.join('%s == %s' % p for p in duplicates))
    report['distinctness'] = manifest.get('distinctness')

    for entry in spec['variants']:
        glb = OUT / entry['skeletalFile']
        obj = OUT / entry['staticFile']
        mtl = OUT / 'meshes' / entry['staticMaterialFile']
        row = {'id': entry['id'], 'triangles': entry['triangles']}
        if not (glb.is_file() and obj.is_file() and mtl.is_file()):
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
    report['scope'] = ('Offline byte, rig and distinctness verification only. Native import, '
                       'material readback, animation playback and every visual judgement remain '
                       'unperformed.')
    return report


# ---------------------------------------------------------------------------
# native helpers
# ---------------------------------------------------------------------------


def _path(asset):
    return asset.get_path_name().split('.')[0] if asset else None


def disk_path(asset_path, extension='uasset'):
    return ROOT / 'Content' / (asset_path[len('/Game/'):] + '.' + extension)


def _bone_readout(ue, mesh):
    """Bone names and component-space rest positions, via whichever API exists.

    UE's Python surface for skeleton rest poses moves between versions. If no
    strategy returns bones the caller must treat compatibility as UNPROVEN
    rather than assume it; nothing here guesses.
    """
    try:
        component = ue.new_object(ue.SkeletalMeshComponent)
        component.set_skeletal_mesh_asset(mesh)
        count = component.get_num_bones()
        if count:
            rows = []
            for i in range(count):
                t = component.get_bone_transform(i).translation
                rows.append((str(component.get_bone_name(i)), (t.x, t.y, t.z)))
            return rows, 'transient SkeletalMeshComponent'
    except Exception:                                                # noqa: BLE001
        pass
    try:
        tree = mesh.get_editor_property('skeleton').get_editor_property('bone_tree')
        if tree:
            return [(None, None)] * len(tree), 'bone_tree length only'
    except Exception:                                                # noqa: BLE001
        pass
    return [], 'unavailable'


def _uv_channels(ue, mesh):
    """StaticMesh.get_num_uv_channels() does not exist on this build.

    Read it off the mesh description; if that surface is missing too, say so
    rather than reporting a number nobody measured.
    """
    for getter in ('get_num_uv_channels', 'get_num_uv_channels_static_mesh'):
        fn = getattr(ue.StaticMesh, getter, None)
        if fn is not None:
            try:
                return {'channels': int(fn(mesh, 0)), 'via': 'StaticMesh.' + getter}
            except Exception:                                        # noqa: BLE001
                pass
    try:
        desc = ue.StaticMesh.get_static_mesh_description(mesh, 0)
        return {'channels': int(desc.get_num_uv_elements()), 'via': 'StaticMeshDescription'}
    except Exception as error:                                       # noqa: BLE001
        return {'channels': None, 'via': 'unavailable', 'reason': str(error)[:160]}


def _static_readback(ue, mesh, entry, spec):
    """Everything numeric that can be read off a saved StaticMesh."""
    nanite = False
    try:
        nanite = bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
    except Exception:                                                # noqa: BLE001
        pass
    slots = list(mesh.get_editor_property('static_materials'))
    materials = [_path(mesh.get_material(i)) for i in range(len(slots))]
    box = mesh.get_bounding_box()
    row = {
        'asset': _path(mesh),
        'triangles': mesh.get_num_triangles(0),
        'vertices': mesh.get_num_vertices(0),
        'lods': mesh.get_num_lods(),
        'naniteEnabled': nanite,
        'triangleReadbackTrustworthy': not nanite,
        'materialSlots': len(slots),
        'slotNames': [str(s.get_editor_property('material_slot_name')) for s in slots],
        'materials': materials,
        'unassignedSlots': [i for i, m in enumerate(materials) if not m],
        'uvChannels': _uv_channels(ue, mesh),
        'localBoundsCm': {'min': [box.min.x, box.min.y, box.min.z],
                          'max': [box.max.x, box.max.y, box.max.z]},
    }
    problems = []
    if row['materialSlots'] < spec['materials']['minimumSlotsPerStaticMesh']:
        problems.append('%s: only %d material slots' % (entry['id'], row['materialSlots']))
    if row['unassignedSlots']:
        problems.append('%s: unassigned material slots %s' % (entry['id'], row['unassignedSlots']))
    if not nanite and abs(row['triangles'] - entry['triangles']) > max(64, entry['triangles'] * .02):
        problems.append('%s: triangles read back %d, authored %d'
                        % (entry['id'], row['triangles'], entry['triangles']))
    return row, problems


def _skeletal_readback(ue, mesh, animations, entry, bones):
    rows, strategy = _bone_readout(ue, mesh)
    row = {'asset': _path(mesh), 'skeleton': _path(mesh.get_editor_property('skeleton')),
           'boneReadoutStrategy': strategy, 'boneCount': len(rows),
           'expectedBoneCount': len(bones),
           'boneNamesMatchAuthoredRig': None, 'maxRestPositionErrorCm': None,
           'animations': sorted(_path(a) for a in animations),
           'animationCount': len(animations)}
    problems = []
    if rows and rows[0][0] is not None:
        row['boneNamesMatchAuthoredRig'] = [n for n, _ in rows] == [b['name'] for b in bones]
        row['maxRestPositionErrorCm'] = max(
            max(abs(a - b) for a, b in zip(p, tuple(q['position_cm'])))
            for (_, p), q in zip(rows, bones))
        if not row['boneNamesMatchAuthoredRig']:
            problems.append(entry['id'] + ': imported bone names differ from the authored rig')
        if row['maxRestPositionErrorCm'] > 0.05:
            problems.append('%s: rest pose readback off by %.4f cm'
                            % (entry['id'], row['maxRestPositionErrorCm']))
    else:
        row['proven'] = False
        row['reason'] = 'No Python API on this build returned bone names; treat as unproven.'
    if row['animationCount'] != len(entry['animations']):
        problems.append('%s: %d clips imported, %d authored'
                        % (entry['id'], row['animationCount'], len(entry['animations'])))
    return row, problems


def _import(ue, tools, assets, filename, folder, name=None):
    task = ue.AssetImportTask()
    options = dict(filename=str(filename), destination_path=folder, automated=True,
                   async_=False, replace_existing=False, save=False)
    if name:
        options['destination_name'] = name
    for key, value in options.items():
        task.set_editor_property(key, value)
    tools.import_asset_tasks([task])
    objects = list(task.get_objects())
    if not objects:
        objects = [ue.load_asset(p) for p in assets.list_assets(folder, recursive=True,
                                                                include_folder=False)]
    return [o for o in objects if o]


def _load_progress():
    if PROGRESS.is_file():
        try:
            return json.loads(PROGRESS.read_text(encoding='utf-8-sig'))
        except Exception:                                            # noqa: BLE001
            pass
    return {'completed': [], 'generatorSha256': None}


def _save_progress(progress):
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS.write_text(json.dumps(progress, indent=2) + '\n', encoding='utf-8')


# ---------------------------------------------------------------------------
# native
# ---------------------------------------------------------------------------


def run(apply=False, batch=DEFAULT_BATCH, variants=None, fresh=False):
    """Root only, in the intended editor. Imports assets; places nothing."""
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never import against a live PIE session')
    world = editor.get_editor_world()
    loaded = world.get_outermost().get_name() if world else None
    if loaded != TARGET:
        raise RuntimeError('Loaded world is %s, expected %s; open the target map first'
                           % (loaded, TARGET))
    if (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Unsaved work present; save or discard before importing')

    module = author()
    bones = module.skeleton()
    offline = offline_check()
    if offline['status'] != 'READY_FOR_NATIVE_IMPORT':
        raise RuntimeError('Offline verification blocked: ' + '; '.join(offline['problems']))
    spec = json.loads(SPEC.read_text(encoding='utf-8-sig'))

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha(map_file)
    marker = stamp()
    progress = {'completed': [], 'generatorSha256': spec['generatorSha256']} if fresh else _load_progress()
    if progress.get('generatorSha256') not in (None, spec['generatorSha256']):
        raise RuntimeError('Resume marker was written against a different generator build; '
                           'rerun with fresh=True after deciding what to do with the partial import')
    progress['generatorSha256'] = spec['generatorSha256']

    wanted = [v for v in spec['variants'] if not variants or v['id'] in variants]
    todo = [v for v in wanted if v['id'] not in progress['completed']]
    this_run = todo[:max(1, int(batch))]

    receipt = {'utc': datetime.now(timezone.utc).isoformat(), 'stamp': marker,
               'status': 'started', 'destination': DEST, 'targetMap': TARGET,
               'mapSha256Before': map_sha_before, 'mapMutated': False,
               'applyRequested': bool(apply), 'batchSize': int(batch),
               'alreadyCompleted': list(progress['completed']),
               'thisBatch': [v['id'] for v in this_run],
               'remainingAfterThisBatch': [v['id'] for v in todo[len(this_run):]],
               'offline': offline, 'imported': [], 'readback': [], 'problems': [],
               'remaining': []}
    receipt_path = OUT / ('native-import-' + marker + '.json')

    def flush():
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()

    if not apply:
        receipt['status'] = 'AUDIT_ONLY_NO_MUTATION'
        receipt['namespaceExists'] = assets.does_directory_exist(DEST)
        receipt['remaining'] = ['Rerun with apply=True to import this batch.']
        flush()
        return receipt

    # Checkpoint the map even though we intend never to touch it: if some
    # importer side effect dirties it, there is a byte-identical copy to restore.
    CHECKPOINT_ROOT.mkdir(parents=True, exist_ok=True)
    checkpoint = CHECKPOINT_ROOT / (spec['checkpointPrefix'] + marker)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs from the map on disk')
    receipt['checkpoint'] = str(checkpoint)
    flush()

    saved_any = False
    try:
        for entry in this_run:
            folder = DEST + '/' + entry['id']
            if assets.does_directory_exist(folder):
                raise RuntimeError('Namespace %s already exists; import a distinct version rather '
                                   'than overwriting a reviewed one' % folder)
            row = {'id': entry['id'], 'skeletalMesh': None, 'staticMesh': None, 'animations': []}

            objects = _import(ue, tools, assets, OUT / entry['skeletalFile'], folder)
            skeletal = [a for a in objects if isinstance(a, ue.SkeletalMesh)]
            animations = [a for a in objects if isinstance(a, ue.AnimSequence)]
            if len(skeletal) != 1:
                raise RuntimeError('Expected exactly one SkeletalMesh for %s, got %d; inspect the '
                                   'partial Interchange assets before retrying'
                                   % (entry['id'], len(skeletal)))
            row['skeletalMesh'] = _path(skeletal[0])
            row['animations'] = sorted(_path(a) for a in animations)
            row['skeleton'] = _path(skeletal[0].get_editor_property('skeleton'))

            statics = _import(ue, tools, assets, OUT / entry['staticFile'],
                              folder + '/StaticMeshes', 'SM_' + entry['id'])
            static = [a for a in statics if isinstance(a, ue.StaticMesh)]
            if len(static) != 1:
                raise RuntimeError('Static OBJ import for %s yielded %d StaticMeshes'
                                   % (entry['id'], len(static)))
            row['staticMesh'] = _path(static[0])

            for asset in objects + statics:
                if not assets.save_loaded_asset(asset, only_if_is_dirty=False):
                    raise RuntimeError('save_loaded_asset returned False for %s. FIRST thing to '
                                       'check: a zombie UnrealEditor process holding the package '
                                       '(tasklist /FI "IMAGENAME eq UnrealEditor*.exe").'
                                       % _path(asset))
            saved_any = True
            receipt['imported'].append(row)
            progress['completed'].append(entry['id'])
            _save_progress(progress)
            flush()

        # ---- readback: reload from disk, trust nothing that was only set -----
        for entry in this_run:
            static = ue.load_asset(DEST + '/' + entry['id'] + '/StaticMeshes/SM_' + entry['id'])
            if not isinstance(static, ue.StaticMesh):
                raise RuntimeError('Saved StaticMesh missing on reload for ' + entry['id'])
            static_row, problems = _static_readback(ue, static, entry, spec)
            receipt['problems'].extend(problems)

            imported = next(r for r in receipt['imported'] if r['id'] == entry['id'])
            skeletal = ue.load_asset(imported['skeletalMesh'])
            if not isinstance(skeletal, ue.SkeletalMesh):
                raise RuntimeError('Saved SkeletalMesh missing on reload for ' + entry['id'])
            anims = [ue.load_asset(p) for p in imported['animations']]
            skeletal_row, more = _skeletal_readback(ue, skeletal, anims, entry, bones)
            receipt['problems'].extend(more)
            receipt['readback'].append({'id': entry['id'], 'static': static_row,
                                        'skeletal': skeletal_row,
                                        'uassetSha256': {
                                            'static': sha(disk_path(static_row['asset'])),
                                            'skeletal': sha(disk_path(skeletal_row['asset']))}})
            flush()

        receipt['status'] = ('IMPORTED_AND_READ_BACK_VISUAL_REVIEW_PENDING' if not receipt['problems']
                             else 'IMPORTED_WITH_READBACK_PROBLEMS')
        receipt['remaining'] = ([] if not receipt['remainingAfterThisBatch'] else
                                ['Rerun the same command to import the next batch: '
                                 + ', '.join(receipt['remainingAfterThisBatch'])])
        receipt['handoff'] = {
            'ownedElsewhere': ('The twenty-four placed residents and the population actor are '
                               'owned by another system. This script did not touch them.'),
            'toSwapTheCrowd': [
                '1. Look at the imported assets in the editor. Nothing here is visual acceptance.',
                '2. For the instanced crowd, point the resident mesh list at the StaticMeshes '
                'under ' + DEST + '/<variant>/StaticMeshes/SM_<variant>; each is already baked '
                'in its own stance and photo pose, so do NOT give them all one shared idle.',
                '3. For skeletal residents, use the SkeletalMesh under ' + DEST + '/<variant>/ '
                'together with the four clips imported beside it. The existing '
                'A_Pilgrim_Original_Idle/_Walk assets are valid motion for this rig but live on '
                'the PilgrimRigV2 Skeleton; retarget them in the editor or use the GLB copies.',
                '4. Apply recommendedActorScale per variant from the spec (0.84 - 1.04): they are '
                'authored at one stature and a crowd of identical heights is the next thing that '
                'will read as wrong.'],
            'variantScales': {v['id']: v['recommendedActorScale'] for v in spec['variants']},
            'photoPoseVariants': [v['id'] for v in spec['variants'] if v['prop']]}
    except Exception as error:                                       # noqa: BLE001
        receipt['status'] = ('failed_partial_assets_saved_resume_marker_written' if saved_any
                             else 'failed_before_any_save')
        receipt['error'] = repr(error)
        raise
    finally:
        receipt['mapSha256After'] = sha(map_file)
        receipt['mapMutated'] = receipt['mapSha256After'] != map_sha_before
        receipt['dirtyMapPackagesAfter'] = [str(p.get_name()) for p in
                                            ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if receipt['mapMutated'] or receipt['dirtyMapPackagesAfter']:
            receipt['problems'].append(
                'The target map changed or is dirty after an import that should not have touched '
                'it. Restore from ' + str(receipt.get('checkpoint')) + ' before doing anything else.')
        receipt['progressMarker'] = {'file': str(PROGRESS), 'completed': progress['completed']}
        flush()
    return receipt


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-spec', action='store_true', help='regenerate the plan from the manifest')
    parser.add_argument('--check', action='store_true', help='offline byte, rig and distinctness verification')
    args = parser.parse_args()
    if args.write_spec:
        print(json.dumps({'spec': str(SPEC), 'variants': len(write_spec()['variants'])}, indent=2))
    elif args.check:
        result = offline_check()
        print(json.dumps(result, indent=2))
        raise SystemExit(0 if result['status'] == 'READY_FOR_NATIVE_IMPORT' else 1)
    else:
        parser.print_help()

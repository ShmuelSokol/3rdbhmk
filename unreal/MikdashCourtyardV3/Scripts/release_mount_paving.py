"""Adopt a visually reviewed PIE paving comparison; exact component override only."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
MESH = '/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface'
MATERIAL = '/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_PavingSlabs'
OLD = '/Game/MikdashV3/MaterialReview/JerusalemStoneV2/M_JerusalemStoneV2_PavingReview'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def helper(name):
    spec = importlib.util.spec_from_file_location('paving_' + name, ROOT/'Scripts'/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(comparison_receipt, visual_review):
    import unreal as u
    comparison_path = Path(comparison_receipt).resolve()
    review_path = Path(visual_review).resolve()
    comparison = json.loads(comparison_path.read_text(encoding='utf-8-sig'))
    review = json.loads(review_path.read_text(encoding='utf-8-sig'))
    if review.get('decision') != 'ADOPT_PAVING_MATERIAL_ONLY' or review.get('comparisonSha256') != sha(comparison_path):
        raise RuntimeError('Require a visual decision bound to this exact comparison')
    if comparison.get('errors') or not comparison.get('mapBytesUnchanged') or not comparison.get('pieEnded'):
        raise RuntimeError('Comparison failed or did not preserve/close its world')
    if len(comparison.get('pavingComparison', [])) != 2 or comparison.get('pavingMaterialCandidate') != MATERIAL+'.MI_PBR_PavingSlabs':
        raise RuntimeError('Need the exact two-view material comparison')
    for still in comparison['pavingComparison']:
        if sha(still['file']) != still['sha256']:
            raise RuntimeError('Reviewed image changed')
    if Path(u.SystemLibrary.get_project_directory()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Live or dirty world')
    if ed.get_editor_world().get_outermost().get_name() != MAP:
        raise RuntimeError('Main must already be loaded')
    units = helper('release_amah48_candidate')
    protected = units.offline_plan()
    mapfile = units.disk(MAP)
    if sha(mapfile) != comparison['mapShaBefore']:
        raise RuntimeError('Map changed since visual comparison')
    for folder in ('__ExternalActors__', '__ExternalObjects__'):
        if (ROOT/'Content'/folder/MAP[6:]).exists():
            raise RuntimeError('External package checkpoint support required')
    snapshot = helper('release_resident_crowd')
    before = snapshot._scene_snapshot(u, actors)
    matches = []
    for actor in actors.get_all_level_actors():
        for component in actor.get_components_by_class(u.StaticMeshComponent):
            if snapshot._path(component.get_editor_property('static_mesh')) == MESH:
                matches.append((actor, component))
    if len(matches) != 1:
        raise RuntimeError('Need exactly one platform surface')
    actor, component = matches[0]
    if component.get_num_materials() != 1 or snapshot._path(component.get_material(0)) != OLD:
        raise RuntimeError('Unexpected original platform material')
    name = actor.get_name()
    shared = list((ROOT/'Content/MikdashV3/Materials/PBR').rglob('*.uasset'))
    shared += [ROOT/'Content'/(asset[6:]+'.uasset') for asset in (MESH, OLD)]
    hashes = {str(path): sha(path) for path in shared}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint = ROOT.parent/'ReviewCheckpoints'/('MountPaving-'+stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(mapfile, checkpoint/'Main.umap')
    if sha(checkpoint/'Main.umap') != sha(mapfile):
        raise RuntimeError('Checkpoint mismatch')
    report = dict(status='STARTED', before=sha(mapfile), checkpoint=str(checkpoint),
                  comparison=str(comparison_path), comparisonSha256=sha(comparison_path),
                  visualReviewSha256=sha(review_path), sharedAssets=hashes, actor=name,
                  scope='One platform material override; geometry, collision, lighting and Kotel unchanged')
    out = ROOT/'SourceAssets/visual-review'/('native-mount-paving-'+stamp+'.json')
    def write():
        out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    write()
    try:
        material = u.load_asset(MATERIAL)
        if material is None:
            raise RuntimeError('Paving material missing')
        actor.modify(True)
        component.modify(True)
        component.set_material(0, material)
        expected = snapshot._scene_snapshot(u, actors)
        normalized = json.loads(json.dumps(expected))
        for original, current in zip(before[name]['components'], normalized[name]['components']):
            if 'materials' in current:
                current['materials'] = original['materials']
        if normalized != before:
            raise RuntimeError('Unrelated actor change')
        if not levels.save_current_level():
            raise RuntimeError('Save failed')
        report.update(status='SAVED_REOPEN_PENDING', after=sha(mapfile))
        write()
        if not levels.load_level(MAP) or snapshot._scene_snapshot(u, actors) != expected:
            raise RuntimeError('Saved scene readback mismatch')
        report.update(status='SAVED_REOPENED_REVIEWED_PAVING', material=MATERIAL)
    except Exception as exc:
        report.update(status='FAILED_CHECKPOINT_AVAILABLE', error=repr(exc))
        raise
    finally:
        after = units.offline_plan()
        report['after'] = sha(mapfile)
        report['protectedUnchanged'] = all(after[k] == protected[k] for k in ('assets', 'configSha256', 'manifestSha256', 'protectedMapHashes')) and all(sha(p) == h for p, h in hashes.items())
        if not report['protectedUnchanged']:
            report['status'] = 'FAILED_PROTECTED_HASH_MISMATCH'
        write()
        if not report['protectedUnchanged']:
            raise RuntimeError('Protected files changed')
    return report

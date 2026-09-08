"""Opt-in partial architecture-only 48cm candidate. Never promotes or edits main."""
import hashlib
import importlib.util
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RATIO = 48.0 / 50.0
ORIGIN = (0.0, 0.0, 0.0)
PROTECTED_MAPS = ('/Game/MikdashV3/Maps/Courtyard',
                  '/Game/MikdashV3/FutureMountV1/L_FutureMount',
                  '/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold')
PENDING = ['fitted finishes, doors, paroches, friezes and relief',
           'vessels and source-dependent props', 'player start/floor plus physical eye and capsule offsets',
           'resident/crowd/transit routes and spawning', 'service/preparation/access rules and triggers',
           'water channel geometry/cavities and runtime', 'tour/camera targets and framing',
           'acoustic zones, smoke/FX and lighting placement', 'enclosure and metric-context junctions',
           'material world-space masks/texel scale', 'historical save decoding/version migration',
           'walking, collision, visual acceptance, cook and package']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disk(package):
    if not package.startswith('/Game/'):
        raise ValueError('Only project packages allowed')
    return ROOT / 'Content' / (package[6:] + '.umap')


def offline_plan():
    config = ROOT / 'Config/DefaultEngine.ini'
    matches = re.findall(r'^GameDefaultMap=(/Game/[^\r\n]+)', config.read_text(encoding='utf-8-sig'), re.M)
    if len(matches) != 1:
        raise ValueError('Need one explicit active GameDefaultMap')
    source = matches[0].split('.')[0]
    manifest_path = ROOT / 'SourceAssets/architecture-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    assets = {}
    for row in manifest['meshes']:
        package = '/Game/MikdashV3/Architecture/architecture_' + row['assetName']
        path = ROOT / 'Content' / (package[6:] + '.uasset')
        if not path.is_file():
            raise ValueError('Exact original architecture asset missing: ' + package)
        assets[package] = {'sha256': sha(path), 'triangles': row['triangles']}
    return dict(status='PARTIAL_CANDIDATE_ONLY_NO_PROMOTION', source=source,
                sourceSha256=sha(disk(source)), configSha256=sha(config),
                manifestSha256=sha(manifest_path), ratio=RATIO, fixedOriginCm=ORIGIN,
                protectedMapHashes={p: sha(disk(p)) for p in PROTECTED_MAPS},
                assets=assets, unconvertedDependencies=PENDING)


def run(*, apply=False):
    if not apply:
        return offline_plan()
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT.resolve():
        raise RuntimeError('Wrong project directory: refuse native mutation')
    plan = offline_plan()
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('Live game: refuse')
    if editor.get_editor_world().get_path_name().split('.')[0] != plan['source']:
        raise RuntimeError('Already loaded editor world must equal current main')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages: refuse')
    helper_path = ROOT / 'Scripts/release_resident_crowd.py'
    module_spec = importlib.util.spec_from_file_location('amah48_scene_snapshot', helper_path)
    helper = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(helper)
    baseline = helper._scene_snapshot(ue, actors)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    candidate = '/Game/MikdashV3/Amah48Candidate_' + stamp + '/Maps/Walkthrough'
    if ue.EditorAssetLibrary.does_asset_exist(candidate):
        raise RuntimeError('Candidate already exists')
    checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('Amah48-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(disk(plan['source']), checkpoint / 'Main.umap')
    for folder in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder / plan['source'][6:]
        if external.exists():
            raise RuntimeError('External actors/objects require expanded checkpoint support; refusing before duplication')
    if sha(checkpoint / 'Main.umap') != plan['sourceSha256']:
        raise RuntimeError('Checkpoint mismatch')
    report = dict(plan, candidate=candidate, checkpoint=str(checkpoint), changes=[],
                  snapshotHelperSha256=sha(helper_path), sourceSnapshot=baseline)
    receipt = checkpoint / 'receipt.json'
    public_receipt = ROOT / 'SourceAssets/scale-review' / ('amah48-candidate-' + stamp + '.json')
    def write():
        receipt.write_text(json.dumps(report, indent=2), encoding='utf-8')
        compact = {k:v for k,v in report.items() if k not in ('sourceSnapshot', 'assets')}
        compact['sourceActorCount'] = len(baseline)
        compact['exactAssetCount'] = len(plan['assets'])
        compact['sourceSnapshotSha256'] = hashlib.sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest()
        compact['architectureAssetHashesSha256'] = hashlib.sha256(json.dumps(plan['assets'], sort_keys=True).encode()).hexdigest()
        public_receipt.write_text(json.dumps(compact, indent=2), encoding='utf-8')
    write()
    try:
        if offline_plan() != plan:
            raise RuntimeError('Source changed during preflight')
        if not ue.EditorAssetLibrary.duplicate_asset(plan['source'], candidate):
            raise RuntimeError('Duplicate failed')
        if not levels.load_level(candidate) or editor.get_editor_world().get_path_name().split('.')[0] != candidate:
            raise RuntimeError('Wrong candidate world')
        if helper._scene_snapshot(ue, actors) != baseline:
            raise RuntimeError('Duplicate scene mismatch')
        selected = []
        seen_assets = {}
        for actor in actors.get_all_level_actors():
            comps = actor.get_components_by_class(ue.StaticMeshComponent)
            matches = [c for c in comps if helper._path(c.get_editor_property('static_mesh')) in plan['assets']]
            if not matches:
                continue
            if not isinstance(actor, ue.StaticMeshActor) or len(comps) != 1 or len(matches) != 1 or actor.get_attach_parent_actor() or actor.get_attached_actors():
                raise RuntimeError('Ambiguous architecture/attachment: ' + actor.get_name())
            if any(abs(a-b)>0.0001 for a,b in zip(helper._pose(actor), [0,0,0,0,0,0,1,1,1])):
                raise RuntimeError('Architecture is not original identity placement; refuse possible double scale: ' + actor.get_name())
            selected.append(actor)
            package = helper._path(matches[0].get_editor_property('static_mesh'))
            seen_assets.setdefault(package, []).append(actor.get_name())
        absent = sorted(set(plan['assets']) - set(seen_assets))
        duplicates = {p:names for p,names in seen_assets.items() if len(names) != 1}
        report['architectureCoverage'] = dict(expected=2633, selected=len(selected), absent=absent, duplicates=duplicates)
        write()
        if len(plan['assets']) != 2633 or len(selected) != 2633 or absent or duplicates:
            raise RuntimeError('Architecture coverage incomplete/duplicated; see receipt')
        for actor in selected:
            before = helper._pose(actor)
            b0 = actor.get_actor_bounds(False)
            actor.modify(True)
            actor.set_actor_location(ue.Vector(*(x * RATIO for x in before[:3])), False, True)
            actor.set_actor_scale3d(ue.Vector(*(x * RATIO for x in before[6:9])))
            b1 = actor.get_actor_bounds(False)
            bounds = lambda b: [[v.x, v.y, v.z] for v in b]
            for old, new in zip(bounds(b0), bounds(b1)):
                if max(abs(x * RATIO - y) for x, y in zip(old, new)) > 0.1:
                    raise RuntimeError('Scaled bounds mismatch: ' + actor.get_name())
            report['changes'].append(dict(name=actor.get_name(), before=before, after=helper._pose(actor),
                                          boundsBefore=bounds(b0), boundsAfter=bounds(b1)))
        changed = {r['name'] for r in report['changes']}
        expected = helper._scene_snapshot(ue, actors)
        if {k:v for k,v in expected.items() if k not in changed} != {k:v for k,v in baseline.items() if k not in changed}:
            raise RuntimeError('Untouched scene changed')
        if not levels.save_current_level() or not levels.load_level(candidate):
            raise RuntimeError('Candidate save/reopen failed')
        if editor.get_editor_world().get_path_name().split('.')[0] != candidate or helper._scene_snapshot(ue, actors) != expected:
            raise RuntimeError('Candidate readback differs')
        report['status'] = 'PARTIAL_ARCHITECTURE48_SAVED_REOPENED_DEPENDENCIES_UNCONVERTED'
    except Exception as error:
        report.update(status='FAILED_CANDIDATE_ONLY', error=repr(error))
        raise
    finally:
        report['protectedUnchanged'] = offline_plan() == plan
        if not report['protectedUnchanged']:
            report['status'] = 'FAILED_PROTECTED_HASH_MISMATCH'
        write()
        if not report['protectedUnchanged']:
            raise RuntimeError('Protected hashes changed; inspect receipt')
    return report


if __name__ == '__main__':
    p = offline_plan()
    print(json.dumps({k:v for k,v in p.items() if k != 'assets'}, indent=2))
    print('Exact asset allowlist count:', len(p['assets']))

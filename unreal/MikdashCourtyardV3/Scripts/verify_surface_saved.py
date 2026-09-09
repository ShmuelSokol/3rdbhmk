"""Read-only fresh commandlet check of an already-saved surface placement receipt.

Requires -SurfaceSavedReceipt=<absolute path without spaces>. Never replays placement.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
import release_surface_detail as h

stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out = ROOT / 'SourceAssets/surface-review' / ('fresh-verify-' + stamp + '.json')
report = {'status': 'started_read_only', 'errors': [], 'mapSaved': False}


def map_hashes():
    return {str(p): h.sha256_of(p) for p in (ROOT / 'Content').rglob('*.umap')}


before = map_hashes()
try:
    assert Path(u.Paths.project_dir()).resolve() == ROOT
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    match = re.search(r'-SurfaceSavedReceipt=([^\s"]+)', u.SystemLibrary.get_command_line())
    assert match, 'Missing receipt argument'
    source = Path(match.group(1))
    prior = json.loads(source.read_text(encoding='utf-8-sig'))
    report.update(sourceReceipt=str(source), sourceSha256=h.sha256_of(source))
    assert prior['mapSaved'] and prior['map'] == h.TARGET
    assert prior['specSha256'] == h.sha256_of(h.SPEC_PATH)
    assert h.sha256_of(h.disk_path(h.TARGET, 'umap')) == prior['mapSha256AfterSave']
    spec = h.load_spec()
    run = h.SurfacePass(u, spec, h.load_plan(spec))
    assert run.levels.load_level(h.TARGET)
    run.world = run.editor.get_editor_world()
    report['decals'] = run.read_back_decals(prior['placed']['decals']['actors'], 40)
    assert report['decals']['checked'] == prior['placed']['decals']['placedCount']
    expected = prior['placed']['manager']
    managers = [a for a in run.actors.get_all_level_actors() if a.get_actor_label() == expected['label']]
    assert len(managers) == 1
    manager = managers[0]
    assert u.MathLibrary.class_is_child_of(manager.get_class(), u.load_class(None, "/Script/MikdashRuntime.MikdashSurfaceDetail"))
    observed = {'decalBudget': int(manager.get_editor_property('decal_budget')),
                'surfaceWearTag': str(manager.get_editor_property('surface_wear_tag')),
                'dustPuffMaterial': h._asset_path(manager.get_editor_property('dust_puff_material')),
                'rippleMaterial': h._asset_path(manager.get_editor_property('ripple_material'))}
    assert all(observed[k] == expected[k] for k in observed), 'Manager mismatch'
    report['manager'] = observed
    protected = prior['protectedMaterialSha256Before']
    assert all(h.sha256_of(h.disk_path(p)) == value for p, value in protected.items())
    report['protectedMaterialsUnchanged'] = True
    report['status'] = 'fresh_process_decals_and_manager_verified_visual_pending'
except Exception as exc:
    report['status'] = 'failed_read_only_verification'
    report['errors'].append(repr(exc))
    raise
finally:
    report['mapsUnchanged'] = map_hashes() == before
    if not report['mapsUnchanged']:
        report['status'] = 'failed_map_guard'
        report['errors'].append('Map bytes changed')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    u.log('SURFACE_FRESH_VERIFY ' + str(out) + ' ' + report['status'])

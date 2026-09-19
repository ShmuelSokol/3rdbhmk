"""Backed-up replacement of five accepted sleeve repairs; preserve native bindings."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Scripts'))
import release_resident_v4 as release

OUT = ROOT/'SourceAssets/characters-review/ResidentShoulderAdopt01'
SELECTED = ['Youth', 'Man_Standard', 'Man_Elder', 'Woman_Young', 'Woman_Elder']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def snapshot():
    paths = list((ROOT/'Content').rglob('*.umap'))
    for folder in ('Characters/ResidentV4', 'Characters/PilgrimRigV3', 'Runtime/CrowdVATV1', 'Runtime/CrowdNearV1'):
        paths += list((ROOT/'Content/MikdashV3'/folder).rglob('*.uasset'))
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def state(mesh):
    return dict(skeleton=mesh.skeleton.get_path_name(),
                materials={str(m.material_slot_name): m.material_interface.get_path_name()
                           for m in mesh.materials},
                morphs=sorted(str(n) for n in mesh.get_all_morph_target_names()))


def run():
    apply = '-ResidentShoulderApply' in ue.SystemLibrary.get_command_line()
    assert apply != ('-ResidentShoulderVerify' in ue.SystemLibrary.get_command_line())
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt = OUT/('shoulder-adopt-'+('apply-' if apply else 'verify-')+stamp+'.json')
    report = dict(status='starting', variants={}, scope='Five skeletal mesh sleeve repairs only; Heavy unchanged; no map edits')
    try:
        before = snapshot()
        report['before'] = before
        if apply:
            review = json.loads((ROOT/'SourceAssets/characters-review/ResidentShoulderCast02/review01.json').read_text())
            assert review['selectedForIntegration'] == SELECTED
            cp = ROOT.parent/'ReviewCheckpoints'/('ResidentShoulders-'+stamp)
            cp.mkdir(parents=True, exist_ok=False)
            report['checkpoint'] = str(cp)
        else:
            prior = sorted(OUT.glob('shoulder-adopt-apply-*.json'))
            assert prior
            accepted = json.loads(prior[-1].read_text())
            assert accepted['status'] == 'applied-readback-passed'
        allowed = set()
        for variant in SELECTED:
            name = 'SK_RV4_'+variant
            package = '/Game/MikdashV3/Characters/ResidentV4/'+variant+'/'+name
            mesh = ue.load_asset(package)
            assert isinstance(mesh, ue.SkeletalMesh)
            disk = ROOT/'Content'/(package[6:]+'.uasset')
            relative = str(disk.relative_to(ROOT))
            allowed.add(relative)
            expected = state(mesh)
            source = OUT/(name+'.glb')
            study = ROOT/'SourceAssets/characters-review'/('ResidentShoulderStudy05' if variant=='Youth' else 'ResidentShoulderCast02/'+variant)
            assert sha(source) == json.loads((study/'review.json').read_text())['candidateSha256']
            if apply:
                backup = cp/(name+'.uasset')
                shutil.copy2(disk, backup)
                assert sha(backup) == before[relative]
                materials = {str(m.material_slot_name): m.material_interface for m in mesh.materials}
                skeleton = mesh.skeleton
                override, pipeline = release._mesh_pipeline(ue, skeleton)
                task = ue.AssetImportTask()
                for key, value in dict(filename=str(source), destination_path=package.rsplit('/',1)[0],
                                       automated=True, replace_existing=True, save=False, options=override).items():
                    task.set_editor_property(key, value)
                ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                imported = [o for o in task.get_objects() if isinstance(o, ue.SkeletalMesh)]
                assert len(imported) == 1 and imported[0].get_path_name() == package+'.'+name
                mesh = imported[0]
                slots = list(mesh.materials)
                assert {str(m.material_slot_name) for m in slots} == set(materials)
                for slot in slots:
                    slot.material_interface = materials[str(slot.material_slot_name)]
                mesh.materials = slots
                assert state(mesh) == expected, 'Bindings or morph targets changed'
                assert ue.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
            else:
                assert expected == accepted['variants'][variant]['state']
                assert sha(disk) == accepted['variants'][variant]['assetSha256']
            report['variants'][variant] = dict(state=state(mesh), sourceSha256=sha(source),
                                                assetSha256=sha(disk), asset=package)
            receipt.write_text(json.dumps(report, indent=2)+'\n')
        after = snapshot()
        changed = sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
        assert not set(changed)-(allowed if apply else set()), 'Unexpected protected asset changes'
        if apply:
            assert set(changed) == allowed, 'Expected five replaced mesh files'
        report.update(after=after, changedFiles=changed,
                      status='applied-readback-passed' if apply else 'fresh-process-readback-passed')
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        receipt.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    run()

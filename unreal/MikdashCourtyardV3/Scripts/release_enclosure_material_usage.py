"""Repair only the observed LimestoneAshlar instancing usage; fresh verification is separate.

Run in a clean real-RHI commandlet with -EnclosureUsageApply, or -EnclosureUsageVerify.
Existing material parameters, other usage bits, parent and map packages are protected.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil
import os

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = '/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_LimestoneAshlar'
SOURCE_LOG = ROOT.parent / 'Astra-Enclosure-Runtime-02.log'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    import unreal as u
    cmd = u.SystemLibrary.get_command_line()
    apply = '-EnclosureUsageApply' in cmd
    assert apply != ('-EnclosureUsageVerify' in cmd), 'Choose apply or verify'
    assert '-nullrhi' not in cmd.lower(), 'Real RHI required'
    assert Path(u.Paths.project_dir()).resolve() == ROOT, 'Wrong project'
    ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    assert not ed.get_game_world(), 'PIE active'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Dirty map'
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Dirty content'
    evidence = SOURCE_LOG.read_text(encoding='utf-8-sig', errors='replace')
    assert PACKAGE + '.MI_PBR_LimestoneAshlar missing usage flag InstancedStaticMeshes!' in evidence
    target = ROOT / 'Content' / (PACKAGE[6:] + '.uasset')
    protected_files = set((ROOT / 'Content').rglob('*.umap'))
    protected_files.update((ROOT / 'Content/MikdashV3/Materials/PBR').rglob('*.uasset'))
    protected_files.discard(target)
    protected = {str(p): sha(p) for p in protected_files}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'SourceAssets/enclosure-review' / ('material-instancing-' + stamp + '.json')
    report = dict(status='starting', apply=apply, processId=os.getpid(), package=PACKAGE,
                  beforeSha256=sha(target), sourceLogSha256=sha(SOURCE_LOG), errors=[])
    def write():
        out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    if apply:
        backup = ROOT.parent / 'ReviewCheckpoints' / ('EnclosureMaterial-' + stamp)
        backup.mkdir(parents=True, exist_ok=False)
        shutil.copy2(target, backup / target.name)
        assert sha(backup / target.name) == report['beforeSha256']
        report['checkpoint'] = str(backup)
    write()
    usage = u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES
    ml = u.MaterialEditingLibrary
    def snapshot(material):
        overrides = material.get_editor_property('base_property_overrides').export_text()
        overrides = re.sub(r'\b(?:bOverride_UsageFlags|UsageFlags)=(?:0x[0-9a-fA-F]+|[0-9]+),?', '', overrides)
        return dict(parent=material.get_editor_property('parent').get_path_name(),
                    parameters={field: [v.export_text() for v in material.get_editor_property(field)] for field in
                                ('scalar_parameter_values', 'vector_parameter_values', 'texture_parameter_values')},
                    otherBaseOverrides=overrides.replace(',)', ')').replace('(,', '('),
                    otherUsage={name: [bool(ml.has_material_usage(material, getattr(u.MaterialUsage, name))),
                                      bool(ml.has_material_usage_override(material, getattr(u.MaterialUsage, name)))]
                                for name in dir(u.MaterialUsage) if name.startswith('MATUSAGE_') and
                                name not in ('MATUSAGE_INSTANCED_STATIC_MESHES', 'MATUSAGE_MAX')})
    try:
        material = u.load_asset(PACKAGE)
        assert isinstance(material, u.MaterialInstanceConstant)
        before = snapshot(material)
        if apply:
            material.modify(True)
            ml.set_material_usage_override(material, usage, True, True)
            ml.update_material_instance(material)
        assert ml.has_material_usage(material, usage) and ml.has_material_usage_override(material, usage)
        stats = ml.get_statistics(material)
        report['pixelInstructions'] = int(stats.get_editor_property('num_pixel_shader_instructions'))
        assert report['pixelInstructions'] > 0, 'No compiled pixel resource'
        assert snapshot(material) == before, 'Unrelated material values changed'
        if apply:
            assert u.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
            report['saved'] = True
            write()
        report['status'] = 'saved_compiled_fresh_process_pending' if apply else 'read_only_usage_and_compilation_verified'
    except Exception as exc:
        report['status'] = 'failed_checkpoint_available'
        report['errors'].append(repr(exc))
        raise
    finally:
        report['afterSha256'] = sha(target)
        report['protectedUnchanged'] = all(sha(Path(p)) == value for p, value in protected.items())
        if not report['protectedUnchanged'] or (not apply and report['beforeSha256'] != report['afterSha256']):
            report['status'] = 'failed_protected_hashes'
        write()
        assert report['status'] != 'failed_protected_hashes'


if __name__ == '__main__':
    import unreal as u
    try:
        run()
    finally:
        if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
            u.SystemLibrary.quit_editor()

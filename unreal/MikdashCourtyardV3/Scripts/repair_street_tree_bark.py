"""Audit or repair existing bark texture bindings, with verified backups and readback."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/vegetation-review/StreetTreesV1'
FOLDER = '/Game/MikdashV3/Vegetation/StreetTreesV1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    paths = list((ROOT / 'Content').rglob('*.umap'))
    paths += list((ROOT / 'Content/MikdashV3/Vegetation/StreetTreesV1').rglob('*.uasset'))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}


def disk(asset):
    return ROOT / 'Content' / (asset.get_path_name().split('.')[0].removeprefix('/Game/') + '.uasset')


def run():
    command = ue.SystemLibrary.get_command_line()
    modes = [m for m in ('Audit', 'Apply', 'Verify') if '-Bark' + m in command]
    if len(modes) != 1:
        raise RuntimeError('Choose exactly one bark mode')
    mode = modes[0]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = OUT / ('bark-' + mode.lower() + '-' + stamp + '.json')
    report = {'status': 'started', 'mode': mode, 'scope': 'Existing bark texture bindings only; native GPU compilation, not packaged acceptance'}
    before = snapshot()
    report['before'] = before
    try:
        master = ue.load_asset(FOLDER + '/Materials/M_StreetTrees_Bark')
        if not isinstance(master, ue.Material):
            raise RuntimeError('Missing bark master')
        mel = ue.MaterialEditingLibrary
        nodes = [n for n in mel.get_material_expressions(master) if isinstance(n, ue.MaterialExpressionTextureSampleParameter2D)]
        by_name = {str(n.get_editor_property('parameter_name')): n for n in nodes}
        if len(nodes) != 2 or set(by_name) != {'BarkBaseColour', 'BarkNormal'}:
            raise RuntimeError('Unexpected bark graph')
        entries = json.loads((OUT / 'street-trees-manifest.json').read_text())['textures']
        prepared = []
        for entry in entries:
            instance = ue.load_asset(FOLDER + '/Materials/MI_StreetTreesV1_' + entry['species'] + '_Bark')
            textures = {param: ue.load_asset(FOLDER + '/Textures/' + Path(entry[key]).stem)
                        for param, key in (('BarkBaseColour', 'barkBaseColour'), ('BarkNormal', 'barkNormal'))}
            if not isinstance(instance, ue.MaterialInstanceConstant) or instance.get_editor_property('parent') != master:
                raise RuntimeError('Unexpected instance or parent: ' + entry['species'])
            if any(not isinstance(t, ue.Texture2D) for t in textures.values()):
                raise RuntimeError('Missing species texture')
            normal = textures['BarkNormal']
            if normal.get_editor_property('srgb') or normal.get_editor_property('compression_settings') != ue.TextureCompressionSettings.TC_NORMALMAP:
                raise RuntimeError('Species normal is not a linear normal map')
            prepared.append((entry['species'], instance, textures))
        if len(prepared) != 6:
            raise RuntimeError('Expected six species')
        assets = [master] + [i for _, i, _ in prepared]
        report['masterBefore'] = {k: {'texture': n.get_editor_property('texture').get_path_name() if n.get_editor_property('texture') else None,
                                     'sampler': str(n.get_editor_property('sampler_type'))} for k, n in by_name.items()}
        report['instancesBefore'] = {name: {p: (t.get_path_name() if t else None)
                                           for p in textures
                                           for t in [mel.get_material_instance_texture_parameter_value(instance, p)]}
                                     for name, instance, textures in prepared}
        if mode == 'Apply':
            checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('StreetTreeBark-' + stamp)
            checkpoint.mkdir(parents=True, exist_ok=False)
            report['checkpoint'] = str(checkpoint)
            for asset in assets:
                source = disk(asset)
                target = checkpoint / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                if sha(target) != before[str(source.relative_to(ROOT))]:
                    raise RuntimeError('Backup hash mismatch')
            path.write_text(json.dumps(report, indent=2) + '\n')
            for param, texture in prepared[0][2].items():
                by_name[param].set_editor_property('texture', texture)
            mel.recompile_material(master)
            for _, instance, textures in prepared:
                for param, texture in textures.items():
                    mel.set_material_instance_texture_parameter_value(instance, param, texture)
                    if mel.get_material_instance_texture_parameter_value(instance, param) != texture:
                        raise RuntimeError('Texture parameter assignment failed')
                mel.update_material_instance(instance)
            ue.AutomationLibrary.finish_loading_before_screenshot()
            for asset in assets:
                if not ue.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
                    raise RuntimeError('Material save failed')
        report['readback'] = []
        for name, instance, textures in prepared:
            actual = {p: mel.get_material_instance_texture_parameter_value(instance, p) for p in textures}
            matches = all(actual[p] == textures[p] for p in textures)
            report['readback'].append({'species': name, 'matches': matches,
                                      'textures': {p: t.get_path_name() if t else None for p, t in actual.items()}})
            if mode != 'Audit' and not matches:
                raise RuntimeError('Species binding mismatch: ' + name)
        if mode != 'Audit':
            for param, texture in prepared[0][2].items():
                if by_name[param].get_editor_property('texture') != texture:
                    raise RuntimeError('Master default mismatch')
            if by_name['BarkNormal'].get_editor_property('sampler_type') != ue.MaterialSamplerType.SAMPLERTYPE_NORMAL:
                raise RuntimeError('Normal sampler type changed')
        ue.AutomationLibrary.finish_loading_before_screenshot()
        report['status'] = {'Audit': 'audit-complete', 'Apply': 'applied-readback-passed', 'Verify': 'fresh-process-readback-passed'}[mode]
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        after = snapshot()
        report['after'] = after
        changed = [k for k in set(before) | set(after) if before.get(k) != after.get(k)]
        report['changedFiles'] = sorted(changed)
        allowed = {str(disk(a).relative_to(ROOT)) for a in assets} if mode == 'Apply' and 'assets' in locals() else set()
        if set(changed) - allowed:
            report['status'] = 'failed_unexpected_file_change'
        path.write_text(json.dumps(report, indent=2) + '\n')
        if report['status'].startswith('failed'):
            raise RuntimeError(report.get('error', report['status']))


if __name__ == '__main__':
    run()

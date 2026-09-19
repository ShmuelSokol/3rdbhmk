"""Backed-up native color repair, or fresh-process readback; no mesh/map binding changes."""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue
sys.path.insert(0, str(Path(__file__).resolve().parent))


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/perf-review/crowd-vat/NearResidentV4'

def hashes():
    paths=list((ROOT/'Content').rglob('*.umap'))
    paths+=list((ROOT/'Content/MikdashV3/Characters/ResidentV4').rglob('*.uasset'))
    paths+=list((ROOT/'Content/MikdashV3/Runtime/CrowdVATV1').rglob('*.uasset'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def disk(asset):
    name = asset.get_path_name().split('.')[0]
    if not name.startswith('/Game/'):
        raise RuntimeError('Only project assets allowed')
    return ROOT / 'Content' / (name[6:] + '.uasset')


def decode(mat):
    nodes = list(ue.MaterialEditingLibrary.get_material_expressions(mat))
    scalars = [n for n in nodes if isinstance(n, ue.MaterialExpressionScalarParameter)
               and str(n.get_editor_property('parameter_name')) == 'VCDecodeExponent']
    powers = [n for n in nodes if isinstance(n, ue.MaterialExpressionPower)]
    if len(scalars) != 1 or len(powers) != 1:
        raise RuntimeError('Unexpected decode graph')
    return scalars[0], powers[0]


def run():
    command = ue.SystemLibrary.get_command_line()
    apply = '-ResidentLinearApply' in command
    if apply == ('-ResidentLinearVerify' in command):
        raise RuntimeError('Choose exactly one apply/verify mode')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt = OUT / ('linear-color-' + ('apply-' if apply else 'verify-') + stamp + '.json')
    report = {'status': 'started', 'mode': 'apply' if apply else 'verify',
              'scope': 'Color material graphs/parameters only; no scene or mesh binding change'}
    try:
        marker=json.loads((ROOT/'SourceAssets/characters-review/ResidentV4/resident-v4-import-marker.json').read_text())
        master,study=(ue.load_asset(marker['masters'][k]) for k in ('cloth','skin'))
        assert isinstance(master,ue.Material) and isinstance(study,ue.Material)
        instances={path:ue.load_asset(path) for group in ('slotInstances','garmentInstances') for path in marker[group].values()}
        assert len(instances)==14, 'Expected six slot and eight garment instances'
        for instance in instances.values():
            assert isinstance(instance,ue.MaterialInstanceConstant)
            parent=instance.get_editor_property('parent')
            assert parent in (master,study) or parent in instances.values()
        assets=[master,study]+list(instances.values())
        paths = [disk(a) for a in assets]
        before = hashes()
        for path in paths:
            before[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        report['before'] = before
        allowed = {str(p.relative_to(ROOT)) for p in paths}
        if apply:
            calibration = json.loads((ROOT / 'SourceAssets/characters-review/KohenSkinV2/color-calibration-20260918T210959Z.json').read_text())
            if calibration['status'] != 'linear-vertex-color-calibration-passed' or calibration['maximumLinearError'] > 2 / 255:
                raise RuntimeError('Native color calibration missing or failed')
            report['calibration'] = 'SourceAssets/characters-review/KohenSkinV2/color-calibration-20260918T210959Z.json'
            checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('ResidentLinearColors-' + stamp)
            checkpoint.mkdir(parents=True, exist_ok=False)
            report['checkpoint'] = str(checkpoint)
            for path in paths:
                target = checkpoint / path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                if hashlib.sha256(target.read_bytes()).hexdigest() != before[str(path.relative_to(ROOT))]:
                    raise RuntimeError('Checkpoint hash mismatch')
            receipt.write_text(json.dumps(report, indent=2) + '\n')
            for material in (master, study):
                scalar, power = decode(material)
                scalar.set_editor_property('default_value', 1.0)
                if not ue.MaterialEditingLibrary.connect_material_expressions(scalar, '', power, 'Exp'):
                    raise RuntimeError('Decode connection failed')
                ue.MaterialEditingLibrary.recompile_material(material)
            for instance in instances.values():
                ue.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(instance, 'VCDecodeExponent', 1.0)
                ue.MaterialEditingLibrary.update_material_instance(instance)
            for asset in assets:
                if not ue.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
                    raise RuntimeError('Material save failed: ' + asset.get_path_name())
        report['materials'] = []
        for material in (master, study):
            scalar, power = decode(material)
            inputs = list(ue.MaterialEditingLibrary.get_inputs_for_material_expression(material, power))
            names = list(ue.MaterialEditingLibrary.get_material_expression_input_names(power))
            exponent = names.index('Exp')
            if len(inputs) <= exponent or inputs[exponent] != scalar or abs(float(scalar.get_editor_property('default_value')) - 1.) > 1e-6:
                raise RuntimeError('Decode graph readback failed')
            report['materials'].append({'path': material.get_path_name(), 'exponent': 1., 'connected': True})
        report['instances'] = {}
        for name, instance in instances.items():
            value = float(ue.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(instance, 'VCDecodeExponent'))
            if abs(value - 1.) > 1e-6:
                raise RuntimeError('Instance readback failed: ' + name)
            report['instances'][name] = value
        after = hashes()
        for path in paths:
            after[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        report['after'] = after
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        report['changedFiles'] = changed
        if set(changed) - (allowed if apply else set()):
            raise RuntimeError('Unexpected protected file change')
        report['status'] = 'applied-readback-passed' if apply else 'fresh-process-readback-passed'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    run()

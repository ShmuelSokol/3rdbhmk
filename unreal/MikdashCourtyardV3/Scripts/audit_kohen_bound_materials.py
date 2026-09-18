"""Read-only native audit of the approved Kohen mesh's bound material graphs."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
MESH = '/Game/MikdashV3/Characters/KohenGadolV1/Mesh/SK_KohenGadol_V1'


def hashes():
    paths = list((ROOT / 'Content/MikdashV3/Characters/KohenGadolV1').rglob('*.uasset'))
    paths += list((ROOT / 'Content').rglob('*.umap'))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def run():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = ROOT / 'SourceAssets/characters-review/KohenSkinV2' / ('bound-materials-' + stamp + '.json')
    report = {'status': 'started', 'scope': 'Read-only asset graph audit; no render or asset save',
              'mesh': MESH, 'before': hashes(), 'slots': [], 'masters': {}}
    try:
        mesh = ue.load_asset(MESH)
        if not isinstance(mesh, ue.SkeletalMesh):
            raise RuntimeError('Approved mesh missing')
        mel = ue.MaterialEditingLibrary
        for slot in mesh.get_editor_property('materials'):
            material = slot.get_editor_property('material_interface')
            if material is None:
                raise RuntimeError('Unbound material')
            row = {'slot': str(slot.get_editor_property('material_slot_name')),
                   'material': material.get_path_name(), 'parents': []}
            seen = set()
            while isinstance(material, ue.MaterialInstance):
                if material.get_path_name() in seen:
                    raise RuntimeError('Cyclic material parent chain')
                seen.add(material.get_path_name())
                if 'decodeExponent' not in row:
                    row['decodeExponent'] = float(mel.get_material_instance_scalar_parameter_value(material, 'VCDecodeExponent'))
                material = material.get_editor_property('parent')
                if material is None:
                    raise RuntimeError('Missing material parent')
                row['parents'].append(material.get_path_name())
            if not isinstance(material, ue.Material):
                raise RuntimeError('Expected material master')
            report['slots'].append(row)
            key = material.get_path_name()
            if key in report['masters']:
                continue
            nodes = []
            for node in mel.get_material_expressions(material):
                inputs = list(mel.get_inputs_for_material_expression(material, node))
                item = {'name': node.get_name(), 'class': node.get_class().get_name(),
                        'inputNames': [str(x) for x in mel.get_material_expression_input_names(node)],
                        'connections': [x.get_name() if x else None for x in inputs]}
                for prop in ('parameter_name', 'default_value', 'const_exponent'):
                    try:
                        item[prop] = str(node.get_editor_property(prop))
                    except Exception:
                        pass
                nodes.append(item)
            report['masters'][key] = nodes
        if not report['slots'] or not all(report['masters'].values()):
            raise RuntimeError('Empty material audit')
        report['after'] = hashes()
        if report['before'] != report['after']:
            raise RuntimeError('Protected source changed during read-only audit')
        report['status'] = 'read-only-audit-passed'
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = repr(error)
        raise
    finally:
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        ue.log('KOHEN_BOUND_MATERIAL_AUDIT: ' + str(output))


if __name__ == '__main__':
    run()

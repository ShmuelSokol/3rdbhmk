"""Read-only, asset-only Unreal commandlet audit of Epic's cavity function."""
import json
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
TARGET = '/MetaHumanCharacter/Lookdev_UHM/Skin/Material_Functions/MF_skin_cavity'


def run():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = ROOT / 'SourceAssets/characters-review/KohenSkinV2' / ('cavity-function-' + stamp + '.json')
    report = {'status': 'started', 'target': TARGET,
              'scope': 'Read-only material-function inspection; no map load, asset creation or save.', 'nodes': []}
    try:
        function = ue.load_asset(TARGET)
        if not isinstance(function, ue.MaterialFunction):
            raise RuntimeError('Cavity function not found')
        editing = ue.MaterialEditingLibrary
        for node in editing.get_material_function_expressions(function):
            sources = list(editing.get_inputs_for_material_function_expression(function, node))
            row = {'name': node.get_name(), 'class': node.get_class().get_name(),
                   'inputs': [str(x) for x in editing.get_material_expression_input_names(node)],
                   'connections': [x.get_name() if x else None for x in sources],
                   'source_outputs': [
                       editing.get_input_node_output_name_for_material_expression(node, source)
                       if source else None for source in sources]}
            for prop in ('input_name', 'output_name', 'description', 'parameter_name',
                         'r', 'g', 'b', 'a', 'const_a', 'const_b', 'constant', 'code',
                         'default_value', 'material_function', 'texture',
                         'input', 'alpha', 'declaration', 'name'):
                try:
                    value = node.get_editor_property(prop)
                    row['property_' + prop] = value.get_path_name() if isinstance(value, ue.Object) else str(value)
                except Exception:
                    pass
            report['nodes'].append(row)
        if not report['nodes']:
            raise RuntimeError('Function graph empty')
        report['status'] = 'read-only-audit-passed'
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = repr(error)
        raise
    finally:
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        ue.log('KOHEN_SKIN_FUNCTION_AUDIT: ' + str(output))


if __name__ == '__main__':
    run()

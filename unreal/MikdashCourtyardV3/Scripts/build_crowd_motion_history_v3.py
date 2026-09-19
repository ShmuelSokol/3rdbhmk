"""Fresh CrowdVATV3 materials only. No map/mesh/original material writes.

Pass -CrowdHistoryBuild once to create the candidate; default is fresh-process
readback. The runtime opt-in resolves these names from the original mesh slots.
This asset gate does not establish shader compilation or rendered acceptance.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'Scripts'))
import create_crowd_vat_v2 as vat
from crowd_motion_history_v3 import previous_wpo, CUSTOM_FLOATS, HISTORY_LAYOUT

NS = '/Game/MikdashV3/Runtime/CrowdVATV3'
MASTER = NS + '/Materials/M_CrowdVAT_V3'
FOLDER = ROOT / 'SourceAssets/perf-review/crowd-vat/MotionHistoryV3'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parameters(ue, material):
    ml = ue.MaterialEditingLibrary
    result = {'scalars': {}, 'vectors': {}, 'textures': {}}
    for name in ml.get_scalar_parameter_names(material):
        result['scalars'][str(name)] = float(ml.get_material_instance_scalar_parameter_value(material, name))
    for name in ml.get_vector_parameter_names(material):
        value = ml.get_material_instance_vector_parameter_value(material, name)
        result['vectors'][str(name)] = [float(v) for v in (value.r, value.g, value.b, value.a)]
    for name in ml.get_texture_parameter_names(material):
        value = ml.get_material_instance_texture_parameter_value(material, name)
        result['textures'][str(name)] = value.get_path_name() if value else None
    return result


def verify_history_wiring(ue, material):
    ml = ue.MaterialEditingLibrary
    def inputs(node):
        names = list(map(str, ml.get_material_expression_input_names(node)))
        values = list(ml.get_inputs_for_material_expression(material, node))
        assert len(names) == len(values), (node.get_name(), names, values)
        return dict(zip(names, values))
    root = ml.get_material_property_input_node(material, ue.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    assert root.get_class().get_name() == 'MaterialExpressionPreviousFrameSwitch'
    switch = inputs(root)
    current, previous = switch['Current Frame'], switch['Previous Frame']
    assert previous.get_class().get_name() == 'MaterialExpressionIf'
    select = inputs(previous)
    assert select['A > B'] == current and select['A == B'] == current
    assert select['A'].get_class().get_name() == 'MaterialExpressionTime'
    assert select['B'].get_class().get_name() == 'MaterialExpressionPerInstanceCustomData'
    assert select['B'].get_editor_property('data_index') == 25
    assert previous.get_editor_property('equals_threshold') == 0.0
    def dependencies(node):
        seen, data = set(), set()
        def visit(n):
            if not n or n.get_path_name() in seen:
                return
            seen.add(n.get_path_name())
            if n.get_class().get_name() == 'MaterialExpressionPerInstanceCustomData':
                data.add(int(n.get_editor_property('data_index')))
            for child in inputs(n).values():
                visit(child)
        visit(node)
        return sorted(data)
    current_data = dependencies(current)
    old_data = dependencies(select['A < B'])
    assert current_data == [0, 2, 3, 4, 5, 6, 7, 8, 9, 10], current_data
    assert old_data == [9] + list(range(11, 25)), old_data
    return dict(wpoRoot='PreviousFrameSwitch', boundaryCustomIndex=25, equalityUsesCurrent=True,
                currentWpoData=current_data, oldWpoData=old_data)


def main():
    import unreal as ue
    build = '-CrowdHistoryBuild' in ue.SystemLibrary.get_command_line().split()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    FOLDER.mkdir(parents=True, exist_ok=True)
    output = FOLDER / ('native-' + stamp + '.json')
    protected = sorted((ROOT / 'Content/MikdashV3/Runtime/CrowdVATV1').rglob('*.uasset'))
    protected += sorted((ROOT / 'Content').rglob('*.umap'))
    before = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    candidate_files = sorted((ROOT / 'Content/MikdashV3/Runtime/CrowdVATV3').rglob('*.uasset'))
    candidate_before = {str(p.relative_to(ROOT)): sha(p) for p in candidate_files}
    report = dict(status='starting', build=build, customFloats=CUSTOM_FLOATS,
                  layout=HISTORY_LAYOUT, protectedHashes=before, assets=[], variants=[])
    try:
        assets, ml = ue.EditorAssetLibrary, ue.MaterialEditingLibrary
        spec = json.loads((ROOT / 'Scripts/create_crowd_vat_v2.spec.json').read_text())
        found = vat._newest(spec, 'crowd-vat-bake-*.json', 'baked_saved_verify_pending', spec['namespace'])
        assert found, 'Missing completed bake'
        bake_file, bake = found
        report['bakeReceiptSha256'] = sha(bake_file)
        first = bake['variants'][0]
        defaults = {key + 'Texture': ue.load_asset(first['textures'][key])
                    for key in ('WalkPosition', 'WalkNormal', 'IdlePosition', 'IdleNormal')}
        defaults.update(WalkMinBBox=first['walkBake']['minBBox'], WalkSizeBBox=first['walkBake']['sizeBBox'],
                        IdleMinBBox=first['idleBake']['minBBox'], IdleSizeBBox=first['idleBake']['sizeBBox'])
        assert all(defaults.values()), 'Missing texture or bounds'
        if build:
            assert not candidate_files and not list(assets.list_assets(NS, True, False)), 'Fresh namespace required'
            master = vat.build_master_v2(ue, spec, NS, 'M_CrowdVAT_V3', defaults, report, previous_wpo)
        else:
            master = ue.load_asset(MASTER)
        assert master, 'Missing candidate master'
        expressions = list(ml.get_material_expressions(master))
        census = {}
        indices = set()
        for node in expressions:
            cls = node.get_class().get_name()
            census[cls] = census.get(cls, 0) + 1
            if cls == 'MaterialExpressionPerInstanceCustomData':
                indices.add(int(node.get_editor_property('data_index')))
        assert indices == set(range(CUSTOM_FLOATS)), indices
        assert census.get('MaterialExpressionPreviousFrameSwitch') == 1
        assert census.get('MaterialExpressionPreSkinnedPosition') == 1
        assert not census.get('MaterialExpressionCustom')
        assert bool(master.get_editor_property('used_with_instanced_static_meshes'))
        assert not bool(master.get_editor_property('tangent_space_normal'))
        report['census'] = census
        report['historyWiring'] = verify_history_wiring(ue, master)
        seen = set()
        for variant in bake['variants']:
            mesh = ue.load_asset(variant['mesh'])
            assert mesh, variant['mesh']
            bindings = []
            for slot in range(len(mesh.get_editor_property('static_materials'))):
                original = mesh.get_material(slot)
                assert original and original.get_name().startswith('MI_CrowdVAT2_')
                path = NS + '/Materials/' + original.get_name()
                expected = parameters(ue, original)
                if build and path not in seen:
                    candidate = assets.duplicate_asset(original.get_path_name(), path)
                    assert candidate, path
                    ml.set_material_instance_parent(candidate, master)
                    # Make inherited V2 values explicit too, preserving the exact
                    # currently released appearance even if defaults have evolved.
                    for name, value in expected['scalars'].items():
                        ml.set_material_instance_scalar_parameter_value(candidate, name, value)
                    for name, value in expected['vectors'].items():
                        ml.set_material_instance_vector_parameter_value(candidate, name, ue.LinearColor(*value))
                    for name, value in expected['textures'].items():
                        assert value, 'Missing texture: ' + name
                        ml.set_material_instance_texture_parameter_value(candidate, name, ue.load_asset(value))
                    assert assets.save_loaded_asset(candidate, False)
                else:
                    candidate = ue.load_asset(path)
                assert candidate and candidate.get_editor_property('parent') == master, path
                assert parameters(ue, candidate) == expected, 'Parameter drift: ' + path
                assert mesh.get_material(slot) == original, 'Original mesh binding changed'
                if path not in seen:
                    report['assets'].append(dict(path=path, sha256=sha(vat.disk_uasset(path)), parameters=expected))
                seen.add(path)
                bindings.append(dict(slot=slot, original=original.get_path_name(), candidate=path))
            report['variants'].append(dict(mesh=variant['mesh'], bindings=bindings))
        report['masterSha256'] = sha(vat.disk_uasset(MASTER))
        assert len(report['variants']) == 6
        report['status'] = 'built-needs-fresh-readback' if build else 'verified-fresh-assets-not-rendered'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['protectedFilesUnchanged'] = before == {str(p.relative_to(ROOT)): sha(p) for p in protected}
        report['candidateFilesUnchanged'] = build or candidate_before == {
            str(p.relative_to(ROOT)): sha(p) for p in candidate_files}
        if not report['protectedFilesUnchanged'] or not report['candidateFilesUnchanged']:
            report.update(status='failed', error='Protected files changed')
        with output.open('x', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2)
            handle.write('\n')
        ue.log('Crowd history: ' + str(output))


if __name__ == '__main__':
    main()

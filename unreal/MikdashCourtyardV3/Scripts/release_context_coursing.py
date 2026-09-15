"""Small asset-only correction; never loads or saves a project map.

Default audit; -CoursingStudy creates before/after review copies only;
-CoursingApply checkpoints and patches exactly three existing masters;
-CoursingVerify requires their corrected code in a fresh process.
Use a fresh UnrealEditor-Cmd -run=pythonscript -nullrhi process, serially.
"""
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'SourceAssets/context-review/ContextCoursingV2'
STUDY = '/Game/MikdashV3/MaterialReview/ContextCoursingV2'
TARGETS = (
    '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building',
    '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall',
    '/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/M_CityFacadeV1',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset_file(path):
    return ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')


def codes():
    spec = importlib.util.spec_from_file_location('coursing_context', ROOT / 'Scripts/release_context_materials.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    surface = mod.HLSL_TRIPLANAR_SURFACE.strip()
    normal = mod.HLSL_TRIPLANAR_NORMAL.strip()
    old_surface = surface.replace('// Keep world height in texture V on both wall projections (horizontal courses).\n', '').replace('uvX = p.yz;', 'uvX = p.zy;')
    old_normal = normal.replace('NrmSampler, p.yz)', 'NrmSampler, p.zy)').replace('tX.xy + n.yz', 'tX.xy + n.zy').replace('tX.zxy *', 'tX.zyx *')
    return {'surface': (old_surface, surface), 'normal': (old_normal, normal)}


def graph(ue, material):
    result = []
    for node in ue.MaterialEditingLibrary.get_material_expressions(material):
        row = {'name': node.get_name(), 'kind': node.get_class().get_name(),
               'connections': [n.get_name() if n else None for n in ue.MaterialEditingLibrary.get_inputs_for_material_expression(material, node)]}
        if isinstance(node, ue.MaterialExpressionCustom):
            row['code'] = node.get_editor_property('code').strip()
        result.append(row)
    return result


def matching_nodes(ue, material, expected):
    # An earlier CityFacade rebuild left disconnected copies of its old graph.
    # Follow the live outputs; do not edit or count unreachable historical nodes.
    ml = ue.MaterialEditingLibrary
    pending = [ml.get_material_property_input_node(material, getattr(ue.MaterialProperty, key))
               for key in ('MP_BASE_COLOR', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_METALLIC')]
    visited, custom = set(), []
    while pending:
        node = pending.pop()
        if node is None or node.get_name() in visited:
            continue
        visited.add(node.get_name())
        if isinstance(node, ue.MaterialExpressionCustom):
            custom.append(node)
        pending.extend(ml.get_inputs_for_material_expression(material, node))
    found = {}
    for key, code in expected.items():
        matches = [n for n in custom if n.get_editor_property('code').strip() == code]
        if len(matches) != 1:
            raise RuntimeError('%s: expected exactly one %s node, found %s' % (material.get_path_name(), key, [(n.get_path_name(), n.get_outer().get_path_name()) for n in matches]))
        found[key] = matches[0]
    return found


def patch(ue, material, old, new):
    before = graph(ue, material)
    nodes = matching_nodes(ue, material, old)
    for key, node in nodes.items():
        node.set_editor_property('code', new[key])
    after = graph(ue, material)
    changed = {node.get_name(): new[key] for key, node in nodes.items()}
    expected = [{**row, **({'code': changed[row['name']]} if row['name'] in changed else {})} for row in before]
    if after != expected:
        raise RuntimeError('Unexpected graph mutation')
    ue.MaterialEditingLibrary.recompile_material(material)
    if not ue.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Material save failed')
    matching_nodes(ue, material, new)
    return {'nodes': len(before), 'customNodesChanged': 2, 'connectionsUnchanged': True}


def run():
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    cl = ue.SystemLibrary.get_command_line().lower()
    modes = [m for m in ('study', 'apply', 'verify') if '-coursing' + m in cl]
    if len(modes) > 1:
        raise RuntimeError('Choose one mode')
    mode = modes[0] if modes else 'audit'
    pairs = codes()
    old, new = ({k: v[i] for k, v in pairs.items()} for i in (0, 1))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    REVIEW.mkdir(parents=True, exist_ok=True)
    receipt_path = REVIEW / ('native-' + mode + '-' + stamp + '.json')
    maps = {str(p.relative_to(ROOT)): digest(p) for p in (ROOT / 'Content').rglob('*.umap')}
    before = {a: digest(asset_file(a)) for a in TARGETS}
    receipt = {'status': 'started', 'mode': mode, 'materials': {}, 'mapsBefore': maps, 'before': before, 'mapLoaded': False, 'mapSaved': False}
    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    write()
    try:
        materials = {a: ue.EditorAssetLibrary.load_asset(a) for a in TARGETS}
        receipt['graphsBefore'] = {a: graph(ue, m) for a, m in materials.items()}
        write()
        for a, m in materials.items():
            if not isinstance(m, ue.Material):
                raise RuntimeError('Missing master: ' + a)
            matching_nodes(ue, m, new if mode == 'verify' else old)
        if mode == 'apply':
            checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('ContextCoursing-' + stamp)
            for a in TARGETS:
                dst = checkpoint / asset_file(a).relative_to(ROOT)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset_file(a), dst)
                if digest(dst) != before[a]:
                    raise RuntimeError('Checkpoint hash mismatch')
            receipt['checkpoint'] = str(checkpoint)
            write()
        for a, material in materials.items():
            if mode == 'study':
                base = a.rsplit('/', 1)[1]
                for suffix in ('Before', 'After'):
                    destination = STUDY + '/' + base + '_' + suffix
                    if ue.EditorAssetLibrary.does_asset_exist(destination):
                        raise RuntimeError('Refusing to overwrite review asset: ' + destination)
                    copy = ue.EditorAssetLibrary.duplicate_asset(a, destination)
                    if not isinstance(copy, ue.Material):
                        raise RuntimeError('Review duplication failed')
                    if suffix == 'After':
                        patch(ue, copy, old, new)
                    elif not ue.EditorAssetLibrary.save_loaded_asset(copy, only_if_is_dirty=False):
                        raise RuntimeError('Review save failed')
                receipt['materials'][a] = {'studyCopiesCreated': True}
            elif mode == 'apply':
                receipt['materials'][a] = patch(ue, material, old, new)
            else:
                receipt['materials'][a] = {'codeMatches': 'corrected' if mode == 'verify' else 'original', 'nodes': len(graph(ue, material))}
            write()
        receipt['status'] = mode + '_passed'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['error'] = repr(error)
        raise
    finally:
        receipt['after'] = {a: digest(asset_file(a)) for a in TARGETS}
        receipt['mapsUnchanged'] = {str(p.relative_to(ROOT)): digest(p) for p in (ROOT / 'Content').rglob('*.umap')} == maps
        receipt['mastersUnchanged'] = receipt['after'] == before
        if not receipt['mapsUnchanged'] or (mode != 'apply' and not receipt['mastersUnchanged']):
            receipt['status'] = 'failed'
            receipt['error'] = 'Protected assets changed; inspect receipt'
            write()
            raise RuntimeError('Protected assets changed; inspect receipt')
        write()
    ue.log('CONTEXT_COURSING: ' + str(receipt_path))


if __name__ == '__main__':
    run()

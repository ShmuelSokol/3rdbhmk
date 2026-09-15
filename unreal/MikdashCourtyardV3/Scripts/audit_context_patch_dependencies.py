"""Read-only Entry-world material dependency audit; --self-test needs no Unreal.

Native launch requires -ContextPatchDependencyAudit and an already open Engine
Entry world. Only registry-selected material instances and the three masters are
loaded. No maps/assets are saved, no material setters/recompilation are called.
An owned validated editor is quit normally after the receipt is flushed.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/context-review/ContextCoursingV2'
MASTERS = (
    '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building',
    '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall',
    '/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/M_CityFacadeV1',
)
MAX_DESCENDANTS = 256
BASE_FIELDS = (
    'bOverride_OpacityMaskClipValue', 'bOverride_BlendMode', 'bOverride_ShadingModel',
    'bOverride_DitheredLODTransition', 'bOverride_CastDynamicShadowAsMasked',
    'bOverride_TwoSided', 'bOverride_bIsThinSurface', 'bOverride_OutputTranslucentVelocity',
    'bOverride_bHasPixelAnimation', 'bOverride_bEnableTessellation',
    'bOverride_DisplacementScaling', 'bOverride_bEnableDisplacementFade',
    'bOverride_DisplacementFadeRange', 'bOverride_MaxWorldPositionOffsetDisplacement',
    'bOverride_CompatibleWithLumenCardSharing', 'bOverride_UsageFlags',
    'TwoSided', 'bIsThinSurface', 'DitheredLODTransition', 'bCastDynamicShadowAsMasked',
    'bOutputTranslucentVelocity', 'bHasPixelAnimation', 'bEnableTessellation',
    'bEnableDisplacementFade', 'bCompatibleWithLumenCardSharing', 'BlendMode',
    'ShadingModel', 'OpacityMaskClipValue', 'DisplacementScaling',
    'DisplacementFadeRange', 'MaxWorldPositionOffsetDisplacement', 'UsageFlags',
)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def package_path(value):
    """Registry export-text/object/package paths -> normalized package path."""
    if not value:
        return None
    if isinstance(value, (tuple, list)):
        if any(v is False for v in value):
            return None
        values = [v for v in value if isinstance(v, str)]
        if len(values) != 1:
            return None
        value = values[0]
    match = re.search(r"(/[^'\"\s]+)", str(value))
    if not match:
        return None
    path = match.group(1)
    # Export text can start with /Script/Engine.Material'/Game/...'.
    matches = re.findall(r"(/[^'\"\s]+)", str(value))
    if len(matches) > 1:
        path = matches[-1]
    return path.split('.', 1)[0]


def descendants(parents, roots):
    """Exact parent edges, transitive closure; no prefix/substr matching."""
    result = set()
    frontier = set(roots)
    while frontier:
        following = {child for child, parent in parents.items()
                     if parent in frontier and child not in result and child not in roots}
        result.update(following)
        frontier = following
    return sorted(result)


def parent_chain(child, parents, roots):
    result, seen = [], set()
    while child:
        if child in seen:
            raise ValueError('Parent cycle: ' + child)
        seen.add(child)
        result.append(child)
        if child in roots:
            return result
        child = parents.get(child)
    raise ValueError('Parent chain does not reach corrected master: ' + str(result))


def plain(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if hasattr(value, 'get_path_name'):
        return value.get_path_name()
    if isinstance(value, (list, tuple)) or type(value).__name__ == 'Array':
        return [plain(v) for v in value]
    # Export is diagnostic text, not an interpreted empty override set.
    if hasattr(value, 'export_text'):
        return {'exportText': value.export_text()}
    return {'text': str(value), 'pythonType': type(value).__name__}


def snake(name):
    name = re.sub(r'^b(?=[A-Z])', '', name)
    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    return name.lower()


def prop(obj, cpp_name):
    """Read reflected fields only; inability to expose private fields is UNKNOWN."""
    errors = []
    for name in dict.fromkeys((snake(cpp_name), cpp_name)):
        try:
            value = obj.get_editor_property(name)
            return value, {'status': 'read', 'property': name, 'value': plain(value)}
        except Exception as exc:
            errors.append(str(exc)[:400])
    return None, {'status': 'unknown', 'cppProperty': cpp_name, 'errors': errors}


def read_struct(obj, cpp_name, fields):
    value, evidence = prop(obj, cpp_name)
    if evidence['status'] == 'read' and value is not None:
        evidence['fields'] = {name: prop(value, name)[1] for name in fields}
    return evidence


def material_evidence(ue, obj):
    result = {
        'class': obj.get_class().get_name(),
        'hasStaticPermutationResource': prop(obj, 'bHasStaticPermutationResource')[1],
        'basePropertyOverrides': read_struct(obj, 'BasePropertyOverrides', BASE_FIELDS),
        'staticParametersRuntime': read_struct(obj, 'StaticParametersRuntime',
            ('StaticSwitchParameters', 'bHasMaterialLayers', 'MaterialLayers')),
        'naniteOverrideMaterial': prop(obj, 'NaniteOverrideMaterial')[1],
    }
    editor_data, result['editorOnlyData'] = prop(obj, 'EditorOnlyData')
    if editor_data is not None:
        result['editorOnlyStaticParameters'] = read_struct(editor_data, 'StaticParameters',
            ('StaticComponentMaskParameters', 'TerrainLayerWeightParameters', 'MaterialLayers'))
    else:
        result['editorOnlyStaticParameters'] = {'status': 'unknown', 'reason': 'EditorOnlyData unavailable'}
    try:
        names = sorted(str(n) for n in ue.MaterialEditingLibrary.get_static_switch_parameter_names(obj))
        result['effectiveGlobalStaticSwitches'] = {'status': 'read', 'names': names, 'values': {}}
        if isinstance(obj, ue.MaterialInstanceConstant):
            for name in names:
                # Blueprint API defaults to GlobalParameter association. It is not
                # a complete enumeration of layer/blend association parameter keys.
                result['effectiveGlobalStaticSwitches']['values'][name] = bool(
                    ue.MaterialEditingLibrary.get_material_instance_static_switch_parameter_value(obj, name))
    except Exception as exc:
        result['effectiveGlobalStaticSwitches'] = {'status': 'unknown', 'reason': str(exc)}
    result['recookDecision'] = 'not_decided_by_this_audit'
    return result


def file_for_package(package):
    if package.startswith('/Game/'):
        return ROOT / 'Content' / (package[6:] + '.uasset')
    return None


def dirty(ue):
    packages = list(ue.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    packages += list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    return sorted({p.get_name() for p in packages if p.get_name().startswith('/Game/')})


def run_native():
    import unreal as ue
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-%d' % os.getpid()
    receipt = OUT / ('dependency-audit-' + stamp + '.json')
    # Outside the receipt-writing/quit finally: never overwrite earlier evidence.
    if receipt.exists():
        raise RuntimeError('Receipt collision; prior evidence left unchanged')
    report = {'schemaVersion': 1, 'status': 'started', 'stamp': stamp,
              'scriptSha256': sha(Path(__file__)), 'engineVersion': ue.SystemLibrary.get_engine_version(),
              'masters': list(MASTERS), 'instances': [], 'errors': [], 'ownedContext': False,
              'mapSaved': False, 'assetSaved': False, 'sourceHashesBefore': {},
              'sourceHashesAfter': {}, 'sourceHashUnavailable': [], 'unknowns': [
                  'This audit does not inspect cp24 cooked bindings, material slots or shader bytecode.',
                  'Global-name switch API is not a complete layer/blend association enumeration.',
                  'Private reflected properties may be inaccessible in Python; unknown is not false.',
                  'Registry discovery covers mounted registered assets, not unmounted content.']}
    before_maps = None

    def flush():
        receipt.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    def hash_source(package):
        path = file_for_package(package)
        if path and path.is_file():
            report['sourceHashesBefore'].setdefault(package, sha(path))
        elif package not in report['sourceHashUnavailable']:
            report['sourceHashUnavailable'].append(package)

    try:
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        if '-contextpatchdependencyaudit' not in ue.SystemLibrary.get_command_line().lower().split():
            raise RuntimeError('Explicit -ContextPatchDependencyAudit required')
        editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        world = editor.get_editor_world()
        if not world or world.get_outermost().get_name() != '/Engine/Maps/Entry' or editor.get_game_world():
            raise RuntimeError('Already-open Engine Entry with no game/PIE required; no map is loaded by this script')
        report['ownedContext'] = True
        report['world'] = world.get_outermost().get_name()
        report['dirtyBefore'] = dirty(ue)
        if report['dirtyBefore']:
            raise RuntimeError('Production packages already dirty')
        before_maps = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT/'Content').rglob('*.umap'))}
        report['mapHashesBefore'] = before_maps
        registry = ue.AssetRegistryHelpers.get_asset_registry()
        registry.search_all_assets(True)
        registry.wait_for_completion()
        data = registry.get_assets_by_class(ue.TopLevelAssetPath('/Script/Engine', 'MaterialInstanceConstant'), True)
        parents, missing = {}, []
        for asset in data:
            child = str(asset.package_name)
            parent = package_path(ue.AssetRegistryHelpers.get_tag_value(asset, 'Parent'))
            if parent:
                if child in parents and parents[child] != parent:
                    raise RuntimeError('Conflicting registry parent: ' + child)
                parents[child] = parent
            else:
                missing.append(child)
        selected = descendants(parents, MASTERS)
        report['registry'] = {'micAssetCount': len(data), 'missingParentTags': sorted(missing),
                              'descendantsFromParentTags': selected,
                              'isLoadingAssetsAfterWait': bool(registry.is_loading_assets())}
        if report['registry']['isLoadingAssetsAfterWait']:
            raise RuntimeError('Registry still gathering; descendant census is incomplete')
        if len(selected) > MAX_DESCENDANTS:
            raise RuntimeError('Descendant bound exceeded; review before expanding')
        # Different query over the SAME registry tags, not independent source truth.
        # Public API traverses direct Parent tags (MaterialEditingLibrary.cpp1779).
        loaded, native_edges = {}, {}
        queue = list(MASTERS)
        for package in queue:
            hash_source(package)  # before loading
            obj = ue.load_asset(package)
            if not isinstance(obj, ue.MaterialInterface):
                raise RuntimeError('Selected package is not a material interface: ' + package)
            loaded[package] = obj
            for child_data in ue.MaterialEditingLibrary.get_child_instances(obj):
                child = str(child_data.package_name)
                if child in MASTERS:
                    raise RuntimeError('Cycle into root material')
                if child in native_edges and native_edges[child] != package:
                    raise RuntimeError('Duplicate/cyclic parent evidence: ' + child)
                native_edges[child] = package
                if child not in queue:
                    queue.append(child)
                if len(native_edges) > MAX_DESCENDANTS:
                    raise RuntimeError('Public-child-API descendant bound exceeded')
        report['registry']['descendantsFromChildAPI'] = sorted(native_edges)
        report['registry']['discoveryMethodsAgree'] = sorted(native_edges) == selected
        if not report['registry']['discoveryMethodsAgree']:
            raise RuntimeError('Registry parent scan and recursive child API disagree')
        for package in selected:
            obj = loaded[package]
            if not isinstance(obj, ue.MaterialInstanceConstant):
                raise RuntimeError('Descendant is not MIC: ' + package)
            parent = obj.get_editor_property('parent')
            actual = package_path(parent.get_path_name()) if parent else None
            if actual != parents[package] or native_edges[package] != actual:
                raise RuntimeError('Loaded parent disagrees with registry: ' + package)
            row = {'package': package, 'parent': actual, 'parentChain': parent_chain(package, parents, MASTERS)}
            row.update(material_evidence(ue, obj))
            report['instances'].append(row)
            flush()
        report['masterEvidence'] = {p: material_evidence(ue, loaded[p]) for p in MASTERS}
        report['status'] = 'audited_with_explicit_unknowns'
    except Exception as exc:
        report['errors'].append(str(exc))
        report['status'] = 'refused_or_failed'
    finally:
        if report['ownedContext']:
            try:
                report['dirtyAfter'] = dirty(ue)
                after_maps = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT/'Content').rglob('*.umap'))}
                report['mapHashesAfter'] = after_maps
                report['mapsUnchanged'] = before_maps is not None and before_maps == after_maps
                for package in report['sourceHashesBefore']:
                    path = file_for_package(package)
                    report['sourceHashesAfter'][package] = sha(path) if path and path.is_file() else None
                report['sourceAssetsUnchanged'] = report['sourceHashesBefore'] == report['sourceHashesAfter']
                if report.get('dirtyAfter') or not report['mapsUnchanged'] or not report['sourceAssetsUnchanged']:
                    report['errors'].append('Dirty package or disk-hash verification failed')
                    report['status'] = 'refused_or_failed'
            except Exception as exc:
                report['errors'].append('Final verification: ' + str(exc))
                report['status'] = 'refused_or_failed'
        report['finishedUtc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        flush()
        ue.log('Context patch dependency audit: ' + str(receipt) + ' ' + report['status'])
        # Never close an editor unless marker/project/Entry/noPIE were all proved.
        if report['ownedContext']:
            ue.SystemLibrary.quit_editor()
    return report


def self_test():
    import unittest

    class Checks(unittest.TestCase):
        def test_recursive_exact_edges(self):
            self.assertEqual(descendants({'/Game/A': '/Game/Root', '/Game/B': '/Game/A',
                                         '/Game/C': '/Game/Rootish'}, ['/Game/Root']), ['/Game/A', '/Game/B'])

        def test_parent_cycle_and_missing_root(self):
            for parents in ({'a': 'b', 'b': 'a'}, {'a': 'b'}):
                with self.assertRaises(ValueError):
                    parent_chain('a', parents, ['root'])

        def test_chain(self):
            self.assertEqual(parent_chain('b', {'b': 'a', 'a': 'root'}, ['root']), ['b', 'a', 'root'])

        def test_export_paths(self):
            for value in ("Material'/Game/A.A'", "/Script/Engine.Material'/Game/A.A'", '/Game/A.A', ('/Game/A.A', True)):
                self.assertEqual(package_path(value), '/Game/A')
            self.assertIsNone(package_path((False, '/Game/A.A')))

        def test_private_property_unknown(self):
            class Hidden:
                def get_editor_property(self, name):
                    raise RuntimeError('not exposed')
            value, evidence = prop(Hidden(), 'bHasStaticPermutationResource')
            self.assertIsNone(value)
            self.assertEqual(evidence['status'], 'unknown')
            self.assertNotIn('value', evidence)

        def test_bool_false_remains_read(self):
            class Visible:
                def get_editor_property(self, name):
                    return False
            self.assertEqual(prop(Visible(), 'bHasStaticPermutationResource')[1]['value'], False)

        def test_production_mutator_calls_absent(self):
            import ast
            tree = ast.parse(Path(__file__).read_text(encoding='utf-8'))
            forbidden = {'load_map', 'load_level', 'save_loaded_asset', 'save_asset', 'save_current_level',
                         'set_editor_property', 'recompile_material', 'update_material_instance', 'collect_garbage'}
            calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
            self.assertFalse(calls & forbidden)

    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        self_test()
    else:
        run_native()

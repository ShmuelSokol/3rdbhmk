"""Small offline source/contract checks for the isolated executable prototype.

No Unreal/UBT/compiler invocation and no clearance/solver candidate run.
"""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
import numpy as np
import study_kohen_cloth_architecture as A
import study_kohen_cloth_preflight as P
import study_kohen_cloth_exec_readback as R
from study_kohen_cloth_parts import body_parts

OUT = A.ROOT / 'SourceAssets/characters-review/KohenClothExecutableV1'
PROJECT = OUT / 'ReviewProject'


def check(scope='active'):
    import runpy, uuid
    evidence_dir = OUT / ('SourceChecks-v4-' + scope + '-' + uuid.uuid4().hex)
    evidence_dir.mkdir()
    gate = runpy.run_path(str(OUT / 'source_contract.py'))
    source_scope = gate['inspect'](A.ROOT, OUT)
    publication_files = None
    if scope == 'publication':
        allowlist = json.loads((OUT / 'publish-allowlist-v4.json').read_text())
        publication_files = gate['audit'](A.ROOT, allowlist['publicationFiles'])
    R.atomic(evidence_dir / 'source-scope.json', dict(scope=scope, executionRoot=str(A.ROOT),
        **source_scope, publicationFiles=publication_files, nativeEligibility=False,
        boundary='Publication scope checks source/prerequisites only; missing historical originals explicitly reported, not waived for native.'))
    assert source_scope['requiredPrerequisites']['completeMatch'], 'Required source prerequisites missing/changed; see source-scope.json'
    assert not source_scope['historicalNativeInventory']['changed'], 'Present historical originals changed; see source-scope.json'
    if scope == 'active':
        assert source_scope['historicalNativeInventory']['completeMatch'], 'Active baseline incomplete; see source-scope.json'
    else:
        assert publication_files['completeMatch'], 'Publication source hashes differ; see source-scope.json'
    tests = []
    def passed(name):
        tests.append(name)
        print('PASS', name)

    model = json.loads((OUT / 'prepared-study-input-v2.json').read_text())
    assert P.validate(model) == 11340
    manifest_v2 = json.loads((OUT / 'source-manifest-v4.json').read_text())
    for path, expected in manifest_v2['inputs'].items():
        assert A.digest(A.ROOT / path) == expected, path
    passed('actual prepared input and source/animation hashes')
    original_input = json.loads((A.OUT / 'prepared-input.json').read_text())
    assert {k:v for k,v in model.items() if k != 'studyPhysics'} == original_input
    passed('v2 input preserves all original prepared geometry, weights and source identity')
    for p in model['patterns']:
        v, f = np.asarray(p['verticesCm']), np.asarray(p['faces'])
        assert np.min(np.linalg.norm(np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]), axis=1)) > 1e-6
    passed('all physical triangles nondegenerate; one dynamic pattern')
    physics = model['studyPhysics']
    assert physics['densityKgM2'] == .35 and physics['minParticleMassKg'] == .0001
    assert physics['geodesicTethers'] and physics['tetherStiffness'] == physics['tetherScale'] == 1
    outer = model['patterns'][0]
    v, f, md = np.asarray(outer['verticesCm']), np.asarray(outer['faces']), np.asarray(outer['maxDistanceCm'])
    adjacency = [set() for _ in v]
    for tri in f:
        for i in tri:
            adjacency[i].update(int(j) for j in tri if j != i)
    reachable = set(np.flatnonzero(md == 0).tolist()); pending = list(reachable)
    while pending:
        for j in adjacency[pending.pop()]:
            if j not in reachable:
                reachable.add(j); pending.append(j)
    assert len(reachable) == len(v) and int((md > 0).sum()) == 616
    passed('explicit study mass and every dynamic outer vertex connected to fixed outer anchors')
    # Zero-physics fixture intentionally differs from the original rig reference.
    fixture = dict(simulationRestAuthorCm=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]],
        simulationBoneInfluences=[[[0,1.]]]*3, boneNames=['pelvis'], axisDeterminant=1,
        patterns=[dict(start=0,faces=[[0,1,2]])], renderPositionMappings=[[0,1,2,1.,0.,0.,0.,0.]])
    original = np.array([[9.,0.,0.]])
    matched = R.matched_binding_control(fixture, {'pelvis':0}, np.array([np.eye(3)]), np.array([[2.,0.,0.]]), original)
    assert np.allclose(matched, [[2.,0.,0.]]) and np.linalg.norm(matched-original) > 1
    assert np.linalg.norm(matched-matched) == 0
    fixture['renderPositionMappings'][0][-1] = .5
    assert np.allclose(R.matched_binding_control(fixture, {'pelvis':0}, np.array([np.eye(3)]), np.array([[2.,0.,0.]]), original), [[5.5,0,0]])
    fixture['renderPositionMappings'][0][-1] = 0
    fixture['renderPositionMappings'][0][-2] = 1
    assert np.allclose(R.matched_binding_control(fixture, {'pelvis':0}, np.array([np.eye(3)]), np.array([[2.,0.,0.]]), original), [[2,0,-1]])
    passed('matched control uses solver weights and blend; original-rig difference cannot imply physics')
    fixture['tethers'] = [[], [[0,1.]], [[0,1.]]]
    tm = dict(patterns=[dict(verticesCm=fixture['simulationRestAuthorCm'],maxDistanceCm=[0,60,60])])
    assert R.validate_tethers(fixture, tm) == 2
    fixture['tethers'][1] = [[2,1.]]
    try:
        R.validate_tethers(fixture, tm)
    except AssertionError:
        passed('tether validator refuses nonfixed anchor')
    else:
        raise AssertionError('Dynamic anchor accepted')
    for invalid in ([], [[0,-1.]], [[0,.01]], [[0,1.],[0,1.]]):
        fixture['tethers'][1] = invalid
        try:
            R.validate_tethers(fixture, tm)
        except AssertionError:
            pass
        else:
            raise AssertionError('Invalid tether accepted')
    passed('missing, negative, shorter-than-chord and duplicate tethers refused')
    A.K.KNEE_TOP, A.K.KNEE_BOT = 65, 20
    from unittest.mock import patch
    import importlib.abc
    class RefuseHead(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == 'create_kohen_gadol_head_v5':
                raise AssertionError('Cloth checks attempted head import')
    blocker = RefuseHead()
    sys.meta_path.insert(0, blocker)
    try:
        with patch.object(A.K, 'assembly', side_effect=AssertionError('Full character assembly forbidden')):
            _, _, parts, *_ = body_parts()
    finally:
        sys.meta_path.remove(blocker)
    assert 'create_kohen_gadol_head_v5' not in sys.modules
    passed('garment construction succeeds with full assembly and missing head module forbidden')
    by = {p['name']: p for p in parts}
    for pattern in model['patterns'][1:]:
        assert np.array_equal(by[pattern['name']]['vertices'], pattern['verticesCm'])
        assert np.array_equal(by[pattern['name']]['faces'], pattern['faces'])
    passed('garment-only inner/body geometry exactly matches prepared source')
    helper = OUT / 'mesh_import_pipeline.py'
    text = helper.read_text()
    tree = ast.parse(text)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    provenance = json.loads((OUT / 'dependency-provenance-v3.json').read_text())
    assert hashlib.sha256(ast.get_source_segment(text, fn).encode()).hexdigest() == provenance['compared'][0]['functionSha256'] == provenance['compared'][1]['functionSha256']
    assert all(isinstance(n, (ast.Expr, ast.FunctionDef)) for n in tree.body)
    import builtins, symtable
    external = set()
    def inspect_scope(scope):
        external.update(s.get_name() for s in scope.get_symbols() if s.is_global() and s.is_referenced())
        for child in scope.get_children():
            inspect_scope(child)
    inspect_scope(symtable.symtable(text, str(helper), 'exec'))
    assert external <= set(dir(builtins)), external
    assert not fn.decorator_list and all(isinstance(n, ast.Constant) for n in fn.args.defaults)
    passed('isolated helper matches active and published reviewed function with no release module execution')
    matched = R.correspondence(np.asarray(by['Meil']['vertices']), np.asarray(model['selectedSourceRenderPositionsCm']))
    assert len(matched) == len(by['Meil']['vertices']) and all(matched)
    passed('actual full Meil to source KG_Meil render correspondence')
    try:
        R.correspondence(np.array([[999., 0., 0.]]), np.array([[0., 0., 0.]]))
    except AssertionError:
        passed('missing render correspondence refused')
    else:
        raise AssertionError('Bad correspondence was accepted')
    # Put test files in the new review tree; never default TEMP/other agent directories.
    with tempfile.TemporaryDirectory(prefix='contract-', dir=OUT) as folder:
        fixture_root = Path(folder)
        present = fixture_root / 'present.glb'; present.write_bytes(b'fixture')
        rows = [dict(path='present.glb', sha256=gate['sha'](present)),
                dict(path='absent.glb', sha256='0'*64)]
        result = gate['audit'](fixture_root, rows)
        assert result['presentMatches'] == ['present.glb'] and len(result['missing']) == 1 and not result['completeMatch']
        present.write_bytes(b'changed')
        assert len(gate['audit'](fixture_root, rows)['changed']) == 1
        passed('source scope reports missing inventory explicitly and rejects changed existing assets')
        path = Path(folder) / 'frame.f32'
        topo = dict(simulationVertices=3, renderVertices=4, frameSchemaVersion=2)
        values = np.arange((3 + 12 + 27) * 3, dtype='<f4')
        values.tofile(path)
        assert [len(x) for x in R.read_frame(path, topo)] == [3, 4, 4, 4, 27]
        passed('binary frame layout/offsets')
        values[:-1].tofile(path)
        try:
            R.read_frame(path, topo)
        except AssertionError:
            passed('partial frame refused')
        else:
            raise AssertionError('Partial frame accepted')
        values[0] = np.nan
        values.tofile(path)
        try:
            R.read_frame(path, topo)
        except AssertionError:
            passed('nonfinite frame refused')
        else:
            raise AssertionError('Nonfinite frame accepted')
        receipt = Path(folder) / 'atomic.json'
        R.atomic(receipt, dict(complete=True))
        assert json.loads(receipt.read_text())['complete'] and not list(Path(folder).glob('*.tmp'))
        try:
            R.atomic(receipt, dict(complete=False))
        except FileExistsError:
            assert json.loads(receipt.read_text())['complete']
            passed('atomic JSON publication preserves existing receipt')
        else:
            raise AssertionError('Existing receipt replaced')
    # Source-level API availability checks, NOT C++ compile or ABI validation.
    required = {
        'Plugins/ChaosClothAsset/Source/ChaosClothAssetEngine/Public/ChaosClothAsset/ClothEngineTools.h': ['GenerateTethers('],
        'Plugins/ChaosClothAsset/Source/ChaosClothAssetEngine/Public/ChaosClothAsset/ClothAsset.h': ['void Build(', 'HasValidClothSimulationModels'],
        'Plugins/ChaosClothAsset/Source/ChaosClothAssetEngine/Public/ChaosClothAsset/ClothAssetSKMClothingAsset.h': ['void SetAsset('],
        'Plugins/ChaosClothAsset/Source/ChaosClothAsset/Public/ChaosClothAsset/CollectionClothFacade.h': ['AddGetSimPattern', 'AddGetRenderPattern', 'GetSimBoneWeights'],
        'Plugins/ChaosClothAsset/Source/ChaosClothAsset/Public/ChaosClothAsset/CollectionClothRenderPatternFacade.h': ['GetRenderDeformerPositionBaryCoordsAndDist', 'SetRenderDeformerNumInfluences'],
        'Source/Runtime/ClothingSystemRuntimeInterface/Public/ClothingSimulationInstance.h': ['void Simulate()', 'void AppendSimulationData(', 'FillContextAndPrepareTick'],
        'Source/Runtime/ClothingSystemRuntimeInterface/Public/ClothingSystemRuntimeTypes.h': ['FTransform Transform;', 'Positions;'],
        'Source/Runtime/Engine/Public/SkinnedAssetCompiler.h': ['void FinishCompilation('],
        'Source/Runtime/ClothingSystemRuntimeCommon/Public/Utils/ClothingMeshUtils.h': ['GenerateMeshToMeshVertData', 'FMeshToMeshFilterSet'],
    }
    evidence = []
    for rel, symbols in required.items():
        path = A.ENGINE / rel
        text = path.read_text(encoding='utf-8-sig')
        assert all(s in text for s in symbols), rel
        evidence.append(dict(path=str(path), sha256=A.digest(path), symbols=symbols))
    passed('installed headers contain all primary build/mapping/readback entry points')
    scripts = list(OUT.glob('*.py')) + list((A.ROOT / 'Scripts').glob('study_kohen_cloth_exec_*.py'))
    for path in scripts:
        ast.parse(path.read_text(), filename=str(path))
    for path in [*OUT.rglob('*.json'), *OUT.rglob('*.uproject'), *OUT.rglob('*.uplugin')]:
        json.loads(path.read_text(encoding='utf-8-sig'))
    passed('new Python syntax and all JSON/project/plugin descriptors parse')
    builder = next(PROJECT.rglob('KohenClothBuilder.cpp')).read_text()
    assert 'Cloth.DefineSchema(EClothCollectionExtendedSchemas::RenderDeformer)' in builder
    assert 'Filter.SourceTriangles.Add(I)' in builder and 'Cross-layer render mapping refused' in builder
    assert 'SourceMeshVertIndices[K]<S.OuterCount' in builder and 'Base->BindToSkeletalMesh' in builder
    assert 'Digest(S.Clone.Get(),S.Section)==S.UnboundDigest' in builder
    assert 'FClothEngineTools::GenerateTethers' in builder and 'BuiltTethers==S.TetherCount' in builder
    assert 'C->MassMode=EClothMassMode::Density' in builder
    passed('source guards cover optional deformer schema, outer-only mapping, binding and immutable sections')
    before = json.loads((A.OUT / 'preservation-before.json').read_text())
    protected = {p: sha for p, sha in before.items() if Path(p).suffix.lower() in ('.uasset', '.umap', '.glb')}
    changed = source_scope['historicalNativeInventory']['changed']
    assert not changed, changed
    passed('full active native inventory matches' if scope == 'active' else 'publication contract matches; historical omissions reported; NOT native preservation proof')
    manifest_path = OUT / 'source-manifest.json'
    if not manifest_path.exists():
        paths = [A.SOURCE, A.OUT / 'prepared-input.json', A.ROOT / model['walk']['glb'],
                 A.ROOT / 'Scripts/release_kohen_gadol_v1.py']
        R.atomic(manifest_path, dict(combinedSource=str(A.SOURCE.relative_to(A.ROOT)),
            preparedInput=str((A.OUT / 'prepared-input.json').relative_to(A.ROOT)),
            inputs={str(p.relative_to(A.ROOT)): A.digest(p) for p in paths}))
    R.atomic(evidence_dir / 'offline-contract-checks.json', dict(passed=True, tests=tests,
        scope=scope, executionRoot=str(A.ROOT), sourceScope=source_scope, nativeEligibility=False,
        apiEvidence=evidence, protectedOriginalAssets=len(protected), changes=changed,
        compile='notrun', native='notrun', solver='notrun', sourceOnly=True))
    R.atomic(evidence_dir / 'files.json', dict(files=[dict(path=str(p.relative_to(A.ROOT)), bytes=p.stat().st_size,
        sha256=A.digest(p)) for p in [*scripts, *OUT.rglob('*')] if p.is_file()],
        note='Inventory excludes itself. Compiler/native artifacts do not exist.'))
    print(len(tests), 'offline checks passed; C++/native NOT RUN')
    print(evidence_dir)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', choices=['active','publication'], default='active')
    check(parser.parse_args().scope)

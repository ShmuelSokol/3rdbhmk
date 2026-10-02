"""Emit exact review publication paths and unchanged project prerequisites; no git writes."""
import sys
sys.dont_write_bytecode = True
import ast
import hashlib
import json
from pathlib import Path
from study_kohen_cloth_exec_readback import atomic

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/KohenClothExecutableV1'

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    checks = Path(sys.argv[1]).resolve()
    assert checks.parent == OUT and (checks / 'offline-contract-checks.json').is_file()
    os_receipt = json.loads((OUT / 'OS-JOB-INTEGRATION.json').read_text())
    for name, expected in os_receipt['wrapperHashes'].items():
        assert digest(OUT / name).upper() == expected.upper(), name
    assert digest(OUT / 'Test-OwnedJobIntegration.ps1').upper() == os_receipt['integrationTestHash'].upper()
    names = ['Build-Reviewed.ps1','Run-Reviewed.ps1','Owned-ReviewWatchdog.ps1','OwnedChildJob.cs',
        'Test-WrappersOffline.ps1','Test-OwnedJobIntegration.ps1','OS-JOB-INTEGRATION.json',
        'REVIEW.txt','WRAPPER-REVISION.txt','PHYSICS-REVISION-v2.txt','run_in_editor.py',
        'source-manifest.json','source-manifest-v2.json','source-manifest-v3.json','prepared-study-input-v2.json',
        'mesh_import_pipeline.py','dependency-provenance-v3.json','publication-dependency-check-v3.json','DEPENDENCIES-REVISION-v3.txt',
        'source_contract.py','publication-source-contract-v4.json','source-manifest-v4.json','SOURCE-SCOPE-v4.txt',
        'publication-inventory-audit-v4.json']
    files = {OUT / n for n in names}
    files.update(p for p in (OUT / 'ReviewProject').rglob('*') if p.is_file()
        and not {'Binaries','Intermediate','Saved'}.intersection(p.parts))
    files.add(checks / 'offline-contract-checks.json')
    files.add(checks / 'files.json')
    files.add(checks / 'source-scope.json')
    files.update([OUT.parent / 'KohenClothFeasibilityV1' / n for n in ['prepared-input.json','preservation-before.json']])
    todo = [ROOT / 'Scripts' / n for n in ['study_kohen_cloth_exec_verify.py',
        'study_kohen_cloth_exec_input_v2.py','study_kohen_cloth_exec_publish.py']]
    dependencies = set(); seen = set()
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        (files if p.name.startswith('study_') else dependencies).add(p)
        for node in ast.walk(ast.parse(p.read_text(encoding='utf-8-sig'))):
            modules = [node.module] if isinstance(node, ast.ImportFrom) else [n.name for n in node.names] if isinstance(node, ast.Import) else []
            for name in modules:
                local = ROOT / 'Scripts' / ((name or '').split('.')[0] + '.py')
                # Optional FaceV5 assembly route is never used by garment-only cloth checks.
                # The focused verifier blocks that import and the full assembly entry point.
                if local.is_file() and local.name != 'create_kohen_gadol_head_v5.py':
                    todo.append(local)
    manifest = json.loads((OUT / 'source-manifest-v4.json').read_text())
    dependencies.update(ROOT / p for p in manifest['inputs'] if ROOT / p not in files)
    def row(p):
        assert p.is_file() and not {'Binaries','Intermediate','Saved','verify-temp'}.intersection(p.parts)
        assert p.suffix.lower() not in ('.log','.pyc','.dll','.exe')
        return dict(path=p.relative_to(ROOT).as_posix(), sha256=digest(p), bytes=p.stat().st_size)
    atomic(OUT / 'publish-allowlist-v4.json', dict(
        publicationFiles=[row(p) for p in sorted(files)],
        requiredExistingProjectFiles=[row(p) for p in sorted(dependencies-files)],
        companion='SourceAssets/characters-review/KohenClothExecutableV1/publish-allowlist-v4.json (this manifest)',
        verificationCommand='python -B Scripts/study_kohen_cloth_exec_verify.py --scope publication',
        copiedReceiptsAreFreshProof=False,
        copiedCheckScope=json.loads((checks / 'offline-contract-checks.json').read_text())['scope'],
        freshPublicationVerification='notrun; verifier must run in clone after coordinator copies this exact allowlist',
        dependencyRevision='DEPENDENCIES-REVISION-v3.txt; runtime manifest v3 supersedes v2 full-release pin',
        excludedOptionalImports=['create_kohen_gadol_head_v5: unreachable full-character MH_HEAD_OBJ branch; blocked-import test passed'],
        boundary='Project-relative source package. Existing source GLBs/generators remain immutable prerequisites, not new adoption. Do not stage requiredExistingProjectFiles as new work.',
        focusedOfflineChecks=len(json.loads((checks / 'offline-contract-checks.json').read_text())['tests']),
        tests='Focused offline checks; project verify --quick7/7; separately pinned watchdog OS integration passed',
        compile='notrun', nativeCloth='notrun', full986='notrun', productionAdoption=False,
        physicsNotes='PHYSICS-REVISION-v2.txt supersedes cloth sections only of frozen REVIEW.txt',
        excluded=['logs','Binaries','Intermediate','Saved','verify-temp','temporary fixtures','earlier receipts not explicitly listed']))

if __name__ == '__main__':
    main()

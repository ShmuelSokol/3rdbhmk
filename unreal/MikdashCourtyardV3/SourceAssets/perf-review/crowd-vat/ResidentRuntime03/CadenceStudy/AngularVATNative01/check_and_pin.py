"""Offline-only final source guard/pinning; no native imports or launches."""
import ast,hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[5]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in BASE.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
for p in BASE.glob('*.json'):json.loads(p.read_text())
inputs=json.loads((BASE/'inputs.json').read_text())
assert sha(BASE/'candidate_builder.py')==inputs['frozenBuilderSha256']==sha(BASE.parent/'AngularVATStudy01/candidate_builder.py')
assert sha(BASE/'OwnedChildJob.cs')==inputs['helperSha256']
project=BASE/'P';descriptor=json.loads((project/'AngularVATReview.uproject').read_text())
assert not descriptor.get('Modules') and not any((project/name).exists() for name in ('Source','Plugins','Binaries'))
assert {p.name for p in project.glob('*.uproject')}=={'AngularVATReview.uproject'}
assert not list((project/'Content').rglob('*.umap'))
actual={str(p.relative_to(project)).replace('\\','/') for p in (project/'Content').rglob('*.uasset')}
assert actual=={r['relative'] for r in inputs['files'].values()}
for row in inputs['files'].values():
    assert sha(project/row['relative'])==row['sha256']==sha(ROOT/row['relative'])
native=(BASE/'native.py').read_text();wrapper=(BASE/'run_native.ps1').read_text()
assert "require(mode=='Compile'" in native and "[ValidateSet('Compile')]" in wrapper
assert 'ue.get_default_object(ue.UnrealEditorSubsystem)' in native
assert 'builder.create_candidate(' not in native
assert native.index("if mode=='Compile':") < native.index('actors=ue.get_editor_subsystem')
assert 'ue.SystemLibrary.quit_editor()' in native and "if mode=='Render':ue.SystemLibrary.quit_editor()" in native
assert not any(x in native for x in ('save_loaded_asset(', 'save_current_level(', 'load_class('))
assert 'Assert-AngularDeadline $clock.Elapsed.TotalSeconds $DeadlineSeconds\n    $owned=' in wrapper
faults=sorted((BASE/'fault-tests').glob('*/result.json'),key=lambda p:p.stat().st_mtime)
fault=json.loads(faults[-1].read_text());assert fault['passed'] and len(fault['cases'])==20
summary={'passed':True,'pythonSyntax':True,'packages':len(actual),'totalCopiedBytes':inputs['totalBytes'],
    'compileOnly':True,'projectDLLBuildRequired':False,'originalFrozenBuilderUnchanged':True,'helperMatchesOSProof':True,
    'offlineFaultReceipt':str(faults[-1].relative_to(BASE)),'offlineFaultCases':20,'noNativeLaunch':True}
(BASE/'offline-ready.json').write_text(json.dumps(summary,indent=2)+'\n')
files=[p for p in BASE.iterdir() if p.is_file() and p.suffix in ('.py','.ps1','.cs','.json') and p.name!='harness-hashes.json']
files += [project/'AngularVATReview.uproject',project/'Config/DefaultEngine.ini']
manifest={str(p.relative_to(BASE)).replace('\\','/'):sha(p) for p in sorted(files)}
(BASE/'harness-hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'ready':True,'pinnedFiles':len(manifest),'manifestSha256':sha(BASE/'harness-hashes.json'),'noNativeLaunch':True}))

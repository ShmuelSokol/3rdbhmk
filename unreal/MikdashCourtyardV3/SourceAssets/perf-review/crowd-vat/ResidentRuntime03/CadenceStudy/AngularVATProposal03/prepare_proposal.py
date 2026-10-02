"""Fresh external Compile03 derivative; only offline staging/tests. Never launches UE."""
import ast,hashlib,json,shutil,subprocess,tempfile
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[5]
OLD=Path('C:/Mikdash/Verification/angular-native02-20261002/runner')
WORK=Path('C:/Mikdash/Verification/angular-native03-20261002')
PIN='de94eed20f3037a8251f84dea1d4e2b6638a207384509dfd2d231fc6be1ab357'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def change(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b)

def main():
    assert sha(OLD/'harness-hashes.json')==PIN
    pins=json.loads((OLD/'harness-hashes.json').read_text())
    for name,h in pins.items():assert sha(OLD/name)==h,name
    inputs=json.loads((OLD/'inputs.json').read_text())
    for row in inputs['files'].values():assert sha(OLD/'P'/row['relative'])==row['sha256']==sha(ROOT/row['relative'])
    assert not WORK.exists(),'Fresh outputs only'
    runner=WORK/'runner';runner.mkdir(parents=True)
    for name in pins:
        dst=runner/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OLD/name,dst)
    for row in inputs['files'].values():
        dst=runner/'P'/row['relative'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OLD/'P'/row['relative'],dst)
    context=json.loads((runner/'source-context.json').read_text())
    context.update(workspace=WORK.as_posix(),faultRoot=(WORK/'fault-tests').as_posix(),compile02ManifestSha256=PIN)
    write(runner/'source-context.json',context)
    wrapper=(runner/'run_native.ps1').read_text()
    wrapper=change(wrapper,"'-ini:Engine:[DevOptions.Shaders]:MaxShaderJobBatchSize=1',",
        "'-forceAllowShaderCompilerJobCache','-LogCmds=LogShaderCompilers VeryVerbose',\n        '-ini:Engine:[DevOptions.Shaders]:bLogJobCompletionTimes=True',\n        '-ini:Engine:[DevOptions.Shaders]:MaxShaderJobBatchSize=1',")
    wrapper=change(wrapper,'^(-script=|-abslog=|-ExecutePythonScript=)(.*)$','^(-script=|-abslog=|-ExecutePythonScript=|-LogCmds=)(.*)$')
    wrapper=change(wrapper,"if($native.status -ne $wanted){throw 'Native receipt proof failed'}",
        "if($native.status -ne $wanted){throw 'Native receipt proof failed'}\n            if($native.compileCoverage -ne 'representative_vertex_pixel_only_not_full_ODSC_material_or_HISM_coverage'){throw 'Explicit partial-coverage boundary required'}")
    (runner/'run_native.ps1').write_text(wrapper)
    native=(runner/'native.py').read_text()
    marker="        require(Path(ue.Paths.project_dir()).resolve()==(BASE/'P').resolve(),'Wrong project mount')"
    extra="""
        require('-forceallowshadercompilerjobcache' in cmd.lower(),'Per-job cache force flag missing')
        expected={'r.ShaderCompiler.JobCacheDDC':1,'r.ShaderCompiler.PerShaderDDCGlobal':1,
                  'r.VelocityOutputPass':1,'r.Velocity.EnableVertexDeformation':1}
        report['cachePolicyReadback']={key:ue.SystemLibrary.get_console_variable_int_value(key) for key in expected}
        require(report['cachePolicyReadback']==expected,'Cache/velocity policy differs')
        report['cachePolicyLimit']='Non-cook force flag selects per-job DDC and ODSC; positive representative statistics still mandatory; no full-map completeness claim'
        report['compileCoverage']='representative_vertex_pixel_only_not_full_ODSC_material_or_HISM_coverage'
"""
    native=change(native,marker,marker+extra)
    (runner/'native.py').write_text(native)
    shutil.copyfile(BASE/'summarize_progress.py',runner/'summarize_progress.py')
    review={'scope':'Proposed Compile03, not launch authorization','parentManifestSha256':PIN,
      'changes':['forceAllowShaderCompilerJobCache','VeryVerbose shader DDC-hit diagnostics','bLogJobCompletionTimes=True','Live cache and unchanged velocity readbacks'],
      'same':['DX12/SM6','batch1 / one worker','VelocityOutputPass1 and vertex deformation1','positive shader statistics and clean diagnostics','6GiB start /4GiB aggregate owned /2GiB reserve /300s deadline /5s cleanup','Entry only; no project DLL/UBT'],
      'policyEffect':'Non-cook commandlet now enables per-job DDC and disables whole material-map DDC/uses ODSC policy. Statistics still submits missing jobs, finishes compilation and must prove positive representative vertex/pixel shaders.',
      'cacheLimit':'Success/no bypass and default/global PerShaderDDCGlobal1 permit async per-job puts. Pending puts can be lost on termination. No cache durability or compile success claimed.',
      'sourceGuard':'Exact 20 parent pins and19 source/staged asset pairs checked before derivative; original sources unchanged',
      'nativeLaunches':0}
    engine=Path('C:/Program Files/Epic Games/UE_5.8/Engine')
    specs={
      'Source/Runtime/Engine/Private/ShaderCompiler/ShaderCompilerJobCache.cpp':'57-60 PerShaderDDCGlobal default1;159-185 force flag enables commandlet job DDC and changes whole-material-map/ODSC policy;1627-1631 success/no-bypass gate;1925 async hit log;2251-2269 async Put (no durable acknowledgement)',
      'Source/Runtime/Engine/Private/ShaderCompiler/ShaderCompiler.cpp':'831-834 batch and completion-log ini reads;1651-1667 completion messages',
      'Source/Editor/MaterialEditor/Private/MaterialEditingLibrary.cpp':'2116-2150 candidate Resource, incomplete map submit, FinishCompilation, actual representative counts; null resource all0',
      'Source/Editor/MaterialEditor/Private/MaterialStatsCommon.cpp':'470-550 candidate GetGameThreadShaderMap; non-UI mesh map and actual ShaderEntry required for vertex/pixel counts; no default material substitution here',
      'Source/Runtime/Engine/Private/Materials/MaterialShader.cpp':'3353-3366 IsComplete excludes IsODSCOnly permutations; cannot treat complete or positive stats as full permutation coverage',
      'Source/Runtime/Engine/Private/Materials/MaterialShared.cpp':'4482-4500 SubmitCompileJobs requires pending map/id and can do nothing; gate must still require actual positive shader counts;4522+ sampler usage from own shader map',
      'Source/Runtime/Engine/Classes/Kismet/KismetSystemLibrary.h':'631 reflected GetConsoleVariableIntValue readback'}
    review['engineEvidence']=[{'path':str(engine/path),'sha256':sha(engine/path),'finding':finding} for path,finding in specs.items()]
    review['parentPins']=pins
    review['originalAssetPins']={row['relative']:row['sha256'] for row in inputs['files'].values()}
    review['recipeHashes']={p.name:sha(p) for p in (Path(__file__),BASE/'summarize_progress.py')}
    write(runner/'compile-review.json',review);write(runner/'reviewer-delta.json',review)
    for p in runner.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    python='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe'
    for command in ([python,'-B',str(runner/'test_shader_gate.py')],
                    [shutil.which('pwsh'),'-NoProfile','-File',str(runner/'test_offline.ps1')],
                    [python,'-B',str(runner/'check_and_pin.py')]):subprocess.run(command,cwd=runner,check=True)
    # Parser fixtures external; no malformed receipts under SourceAssets.
    from summarize_progress import summarize
    fixture=WORK/'progress-fixture.log'
    fixture.write_text('LogShaderCompilers: Found an async DDC result for job with ihash AABB.\n'
        'LogShaderCompilers: Found an async DDC result for job with ihash AABB.\n'
        'LogShaderCompilers: There is already a cached job with the ihash CCDD, processing the new one immediately.\n'
        'LogShaderCompilers: Job Example compile time exceeded threshold (0.1s)\n')
    parsed=summarize(fixture)
    assert parsed['uniqueDdcHitInputHashes']==['aabb'] and parsed['uniqueInProcessHitInputHashes']==['ccdd'] and parsed['completedJobMessages']==1
    assert sha(runner/'P/Config/DefaultEngine.ini')==pins['P/Config/DefaultEngine.ini']
    assert sha(runner/'OwnedChildJob.cs')==pins['OwnedChildJob.cs']
    for name,h in pins.items():assert sha(OLD/name)==h,name
    for row in inputs['files'].values():assert sha(ROOT/row['relative'])==row['sha256']==sha(runner/'P'/row['relative'])
    result={'offlineReady':True,'newManifestSha256':sha(runner/'harness-hashes.json'),
      'parentManifestSha256':PIN,'shaderGateCases':12,'wrapperCases':20,'progressParserFixturePassed':True,
      'parentPreserved':True,'velocityConfigAndOwnedHelperExact':True,'nativeLaunches':0,
      'reviewCommand':f'pwsh -NoProfile -File "{runner.as_posix()}/run_native.ps1" -RunId angular-compile03 -Mode Compile -CoordinatorNativeRun -DeadlineSeconds 300',
      'terminalProgressCommand':f'"{python}" -B "{runner.as_posix()}/summarize_progress.py" --run "{runner.as_posix()}/runs/angular-compile03/compile"'}
    write(WORK/'preparation.json',result)
    write(BASE/'review-contract.json',review);write(BASE/'offline-ready.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()

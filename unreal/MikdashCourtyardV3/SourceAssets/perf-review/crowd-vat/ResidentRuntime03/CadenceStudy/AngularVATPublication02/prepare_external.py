"""Offline-only fresh external staging of a reviewed Compile01 derivative. Never launches UE.
Frozen Native01 and Publication01 are historical inputs, never modified.
"""
import argparse, ast, hashlib, json, shutil, subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
MANIFEST = '199bbc388482f58a437b059735815fec0fe63a764e1ad756955c26f437cf600a'
REL = Path('SourceAssets/perf-review/crowd-vat/ResidentRuntime03/CadenceStudy')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')

def replace_once(text, old, new):
    assert text.count(old) == 1, ('Unexpected frozen source', old)
    return text.replace(old, new)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    root, work = args.project_root.resolve(), args.workspace.resolve()
    verification = Path('C:/Mikdash/Verification').resolve()
    assert work.is_relative_to(verification) and work != verification
    assert not work.is_relative_to(root) and not root.is_relative_to(work)
    assert not work.exists(), 'Fresh external workspace required; never overwrite evidence'
    old = root/REL/'AngularVATNative01'
    assert sha(old/'harness-hashes.json') == MANIFEST
    pins = json.loads((old/'harness-hashes.json').read_text())
    templates = root/REL/'AngularVATPublication01/source-templates'
    # P text descriptors are recoverable from the published exact-byte templates.
    inputs = {name: (templates/name.removeprefix('P/').removeprefix('Config/')
                     if name.startswith('P/') else old/name) for name in pins}
    for name, digest in pins.items():
        assert sha(inputs[name]) == digest, name
    requirements = json.loads((root/REL/'AngularVATPublication01/prerequisites.json').read_text())['requirements']
    for name, row in requirements.items():
        assert sha(root/name) == row['sha256'], name
    work.mkdir(parents=True)
    snapshot = work/'compile01-source'; snapshot.mkdir()
    for name, path in inputs.items():
        target = snapshot/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert sha(target) == pins[name]
    shutil.copyfile(old/'harness-hashes.json', snapshot/'harness-hashes.json')
    runner = work/'runner'; runner.mkdir()
    # Frozen prepare.py is historical only. Never execute its in-source staging recipe.
    for name, path in inputs.items():
        if name in ('prepare.py', 'offline-ready.json') or name.startswith('P/'):
            continue
        shutil.copyfile(path, runner/name)
    project = runner/'P'; (project/'Config').mkdir(parents=True)
    shutil.copyfile(templates/'AngularVATReview.uproject', project/'AngularVATReview.uproject')
    config = (templates/'DefaultEngine.ini').read_text()
    config += ('\n[/Script/WindowsTargetPlatform.WindowsTargetSettings]\n'
               'DefaultGraphicsRHI=DefaultGraphicsRHI_DX12\n'
               '-D3D12TargetedShaderFormats=PCD3D_SM5\n'
               '+D3D12TargetedShaderFormats=PCD3D_SM6\n')
    (project/'Config/DefaultEngine.ini').write_text(config)
    proof = json.loads((runner/'inputs.json').read_text())
    for row in proof['files'].values():
        src, dst = root/row['relative'], project/row['relative']
        assert sha(src) == row['sha256']
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)
        assert sha(dst) == row['sha256']
    context = {'projectRoot':root.as_posix(), 'workspace':work.as_posix(),
               'faultRoot':(work/'fault-tests').as_posix(), 'historicalManifestSha256':MANIFEST}
    write_json(runner/'source-context.json', context)
    wrapper = (runner/'run_native.ps1').read_text()
    wrapper = replace_once(wrapper, "$root=[IO.Path]::GetFullPath((Join-Path $base '../../../../../..'))",
        "$context=Get-Content -LiteralPath \"$base/source-context.json\" -Raw|ConvertFrom-Json\n$root=$context.projectRoot")
    wrapper = replace_once(wrapper, "$frozen=Join-Path $base '../AngularVATStudy01/candidate_builder.py'",
        "$frozen=Join-Path $root '"+(REL/'AngularVATStudy01/candidate_builder.py').as_posix()+"'")
    wrapper = replace_once(wrapper, "'-ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreads=999',",
        "'-ini:Engine:[DevOptions.Shaders]:MaxShaderJobBatchSize=1',\n        '-ini:Engine:[DevOptions.Shaders]:NumUnusedShaderCompilingThreads=999',")
    (runner/'run_native.ps1').write_text(wrapper)
    test = (runner/'test_offline.ps1').read_text()
    test = replace_once(test, "$dir=Join-Path $PSScriptRoot ('fault-tests/'+[guid]::NewGuid().ToString('N'))",
        "$context=Get-Content -LiteralPath \"$PSScriptRoot/source-context.json\" -Raw|ConvertFrom-Json\n$dir=Join-Path $context.faultRoot ([guid]::NewGuid().ToString('N'))")
    (runner/'test_offline.ps1').write_text(test)
    check = (runner/'check_and_pin.py').read_text()
    check = replace_once(check, 'ROOT=BASE.parents[5]', "CONTEXT=json.loads((BASE/'source-context.json').read_text())\nROOT=Path(CONTEXT['projectRoot'])")
    check = replace_once(check, "BASE.parent/'AngularVATStudy01/candidate_builder.py'", "ROOT/'"+(REL/'AngularVATStudy01/candidate_builder.py').as_posix()+"'")
    check = replace_once(check, "(BASE/'fault-tests').glob('*/result.json')", "Path(CONTEXT['faultRoot']).glob('*/result.json')")
    check = replace_once(check, "str(faults[-1].relative_to(BASE))", 'str(faults[-1])')
    (runner/'check_and_pin.py').write_text(check)
    review = {'scope':'External Compile02 preparation only; native review/launch still coordinator-only',
        'historicalManifestSha256':MANIFEST, 'changes':['External project/output/fault roots',
        'Restore threshold07 DX12/SM6 target', 'MaxShaderJobBatchSize=1'],
        'unchanged':['6GiB start / 4GiB aggregate owned private / 2GiB reserve / 300s deadline',
        'Exact OS-proven owned Job helper', 'Positive shader statistics plus clean diagnostics',
        'Frozen stock-node generator', 'GI0/reflection0/VSM0; textures/normals/Nanite defaults unchanged'],
        'notClaimed':['Native shader success','Pixels','Temporal velocity','Production acceptance'],
        'nativeLaunches':0}
    write_json(runner/'compile-review.json', review)
    write_json(runner/'reviewer-delta.json', review)
    for p in runner.glob('*.py'): ast.parse(p.read_text(encoding='utf-8-sig'))
    python = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe')
    pwsh = shutil.which('pwsh'); assert pwsh
    for argv in ([str(python),'-B',str(runner/'test_shader_gate.py')],
                 [pwsh,'-NoProfile','-File',str(runner/'test_offline.ps1')],
                 [str(python),'-B',str(runner/'check_and_pin.py')]):
        subprocess.run(argv, check=True, cwd=runner)
    for name, digest in pins.items(): assert sha(inputs[name]) == digest, name
    assert sha(old/'harness-hashes.json') == MANIFEST
    for name, row in requirements.items(): assert sha(root/name) == row['sha256'], name
    result = {'offlineReady':True,'nativeLaunches':0,'sourcePreserved':True,
        'historicalManifestSha256':MANIFEST,'newManifestSha256':sha(runner/'harness-hashes.json'),
        'runner':runner.as_posix(),'sourceSnapshot':snapshot.as_posix(),
        'guardedCommandForCoordinatorReviewOnly':f'pwsh -NoProfile -File "{runner.as_posix()}/run_native.ps1" -RunId angular-compile02 -Mode Compile -CoordinatorNativeRun -DeadlineSeconds 300'}
    write_json(work/'preparation.json', result)
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()

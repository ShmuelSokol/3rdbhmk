"""Offline reconstruction from published source bytes + explicitly pinned local assets.
No dependency on an old external runner. No Unreal, asset saves, or native launch.
"""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--project-root',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args()
    root=a.project_root.resolve();work=a.workspace.resolve();verify=Path('C:/Mikdash/Verification').resolve()
    assert work.is_relative_to(verify) and work!=verify and not work.is_relative_to(root) and not root.is_relative_to(work)
    assert not work.exists(),'Fresh workspace only'
    source=BASE/'runner-source';pins=json.loads((BASE/'runner-source-pins.json').read_text())
    for name,row in pins.items():assert sha(source/row['source'])==row['sha256'],name
    proof=json.loads((source/'inputs.json').read_text())
    builder=root/'SourceAssets/perf-review/crowd-vat/ResidentRuntime03/CadenceStudy/AngularVATStudy01/candidate_builder.py'
    assert sha(builder)==proof['frozenBuilderSha256']
    for row in proof['files'].values():assert sha(root/row['relative'])==row['sha256'],row['relative']
    runner=work/'runner';runner.mkdir(parents=True)
    for name,row in pins.items():
        dst=runner/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/row['source'],dst)
    for row in proof['files'].values():
        dst=runner/'P'/row['relative'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/row['relative'],dst)
    context=json.loads((runner/'source-context.json').read_text())
    context.update(projectRoot=root.as_posix(),workspace=work.as_posix(),faultRoot=(work/'fault-tests').as_posix())
    (runner/'source-context.json').write_text(json.dumps(context,indent=2)+'\n')
    python='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe'
    for command in ([python,'-B',str(runner/'test_shader_gate.py')],
                    [shutil.which('pwsh'),'-NoProfile','-File',str(runner/'test_offline.ps1')],
                    [python,'-B',str(runner/'check_and_pin.py')]):subprocess.run(command,cwd=runner,check=True)
    for name,row in pins.items():assert sha(source/row['source'])==row['sha256']
    for row in proof['files'].values():assert sha(root/row['relative'])==row['sha256']==sha(runner/'P'/row['relative'])
    print(json.dumps({'offlineReconstructed':True,'nativeLaunches':0,'runner':str(runner),
        'newManifestSha256':sha(runner/'harness-hashes.json'),
        'scope':'Historical1/1 profile replay only. Compile04 STOP remains; no additional run authorized. Separate shipping0/2 was implemented and failed its300s bounded attempt before Python; see additive Shipping01 outcome.'}))
if __name__=='__main__':main()

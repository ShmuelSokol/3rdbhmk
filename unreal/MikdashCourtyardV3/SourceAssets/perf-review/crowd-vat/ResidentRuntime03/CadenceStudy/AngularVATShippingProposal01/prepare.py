"""Offline-only shipping-setting parity proposal. No native execution or historical edits."""
import hashlib,json,shutil,subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[5]
PUB=BASE.parent/'AngularVATPublication03'
OLD=Path('C:/Mikdash/Verification/angular-native03-20261002/runner')
WORK=Path('C:/Mikdash/Verification/angular-shipping02-20261002')
PARENT='c0b3c5fa69e5f9c93a72109a3f9634376b51a3d830c7a3bdd7410cf7411b7b2d'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def replace(data,old,new):
    assert data.count(old)==1,old
    return data.replace(old,new)
def main():
    assert not WORK.exists(),'Fresh workspace only'
    assert sha(OLD/'harness-hashes.json')==PARENT
    oldpins=json.loads((OLD/'harness-hashes.json').read_text())
    for name,digest in oldpins.items():assert sha(OLD/name)==digest
    assert sha(PUB/'publish-allowlist.json')=='b5e5490239df4358dc3e2337c930aac5e242d4de81ca8fbed3e8a3aba7a8414f'
    for row in json.loads((PUB/'publish-allowlist.json').read_text())['entries']:
        assert sha(ROOT/row['path'])==row['sha256']
    auditpath=BASE.parent/'AngularVATOutcome04/shipping-velocity-audit.json'
    audit=json.loads(auditpath.read_text())
    for row in audit['packagedReadbacks']:assert sha(ROOT/row['path'])==row['sha256']
    for row in audit['engineEvidence']:assert sha(Path(row['path']))==row['sha256']
    assert audit['compile04']['comparison']['boundedExperimentProgress'] is False
    pins=json.loads((PUB/'runner-source-pins.json').read_text())
    inputs=json.loads((PUB/'runner-source/inputs.json').read_text())
    for name,row in pins.items():assert sha(PUB/'runner-source'/row['source'])==row['sha256']==oldpins[name]
    for row in inputs['files'].values():assert sha(ROOT/row['relative'])==row['sha256']
    runner=WORK/'runner';runner.mkdir(parents=True)
    for name,row in pins.items():
        dst=runner/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PUB/'runner-source'/row['source'],dst)
    for row in inputs['files'].values():
        dst=runner/'P'/row['relative'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/row['relative'],dst)
    cfg=runner/'P/Config/DefaultEngine.ini'
    data=replace(cfg.read_bytes(),b'r.VelocityOutputPass=1',b'r.VelocityOutputPass=0')
    data=replace(data,b'r.Velocity.EnableVertexDeformation=1',b'r.Velocity.EnableVertexDeformation=2');cfg.write_bytes(data)
    path=runner/'native.py'
    path.write_bytes(replace(path.read_bytes(),b"'r.VelocityOutputPass':1,'r.Velocity.EnableVertexDeformation':1",b"'r.VelocityOutputPass':0,'r.Velocity.EnableVertexDeformation':2"))
    context=json.loads((runner/'source-context.json').read_text())
    context.update(projectRoot=ROOT.as_posix(),workspace=WORK.as_posix(),faultRoot=(WORK/'fault-tests').as_posix())
    write(runner/'source-context.json',context)
    review={'scope':'New packaged-setting parity hypothesis; NOT another authorized iteration of the stopped1/1 cache experiment',
      'parentManifestSha256':PARENT,'historicalCompile04Decision':'STOP remains unchanged',
      'semanticDelta':{'r.VelocityOutputPass':{'before':1,'proposed':0},'r.Velocity.EnableVertexDeformation':{'before':1,'proposed':2}},
      'expectedReadback':'Native script requires0/2; cache settings stay1/1',
      'unchanged':'Graph,builder,helper,wrapper,realRHI/DX12/SM6,Entry,cache force flag,batch1,diagnostics/5positive stats,6/4/2/300 and5s cleanup',
      'authoritativePackagedReadbacks':audit['packagedReadbacks'],'sourceEvidence':audit['engineEvidence'],
      'auditSha256':sha(auditpath),'originalAssetPins':{r['relative']:r['sha256'] for r in inputs['files'].values()},
      'candidateGraphSha256':sha(runner/'candidate_builder.py'),'ownedHelperSha256':sha(runner/'OwnedChildJob.cs'),
      'limits':['No HISM/pixels/temporal/full permutation coverage claim','Recorded packaged runs prove those settings, not every current build','No guarantee of cache reuse or completion within deadline','Outcome03 comparator is frozen to1/1 and MUST NOT be used as acceptance for this proposal'],
      'acceptance':'Only successful wrapper cleanup/preservation with fresh matching native manifest,0/2 readbacks,positive5 statistics/clean diagnostics and expected graph. Timeout is failed candidate proof; no automatic repeat.',
      'reviewRoute':'Confucius via coordinator; no native launch by author','nativeLaunches':0}
    write(runner/'compile-review.json',review);write(runner/'reviewer-delta.json',review)
    # Prove the only executable/config differences are the two settings/readbacks.
    assert replace(replace(cfg.read_bytes(),b'r.VelocityOutputPass=0',b'r.VelocityOutputPass=1'),b'r.Velocity.EnableVertexDeformation=2',b'r.Velocity.EnableVertexDeformation=1')==(OLD/'P/Config/DefaultEngine.ini').read_bytes()
    assert replace(path.read_bytes(),b"'r.VelocityOutputPass':0,'r.Velocity.EnableVertexDeformation':2",b"'r.VelocityOutputPass':1,'r.Velocity.EnableVertexDeformation':1")== (OLD/'native.py').read_bytes()
    for name in pins:
        if name.endswith(('.ps1','.cs','.py')) and name!='native.py':assert sha(runner/name)==oldpins[name],name
    python='C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe'
    for cmd in ([python,'-B',str(runner/'test_shader_gate.py')],
                [shutil.which('pwsh'),'-NoProfile','-File',str(runner/'test_offline.ps1')],
                [python,'-B',str(runner/'check_and_pin.py')]):subprocess.run(cmd,check=True,cwd=runner)
    for name,digest in oldpins.items():assert sha(OLD/name)==digest
    for row in inputs['files'].values():assert sha(ROOT/row['relative'])==row['sha256']==sha(runner/'P'/row['relative'])
    result={'frozenForIndependentReview':True,'manifestSha256':sha(runner/'harness-hashes.json'),
      'shaderGateCases':12,'wrapperCases':20,'exactSemanticDeltaReversalPassed':True,'historicalPinsUnchanged':True,
      'nativeLaunches':0,'commandForReviewOnly':f'pwsh -NoProfile -File "{runner.as_posix()}/run_native.ps1" -RunId angular-shipping01 -Mode Compile -CoordinatorNativeRun -DeadlineSeconds 300'}
    write(WORK/'preparation.json',result);write(BASE/'review-contract.json',review);write(BASE/'offline-ready.json',result)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()

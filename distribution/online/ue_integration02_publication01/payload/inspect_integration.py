"""Post-probe evidence inspection only. Cannot execute native tools."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from stage import verify

def inspect(expected):
    manifest=verify(ROOT,expected,exact=False)
    r=json.loads((ROOT/'run/receipt.json').read_text())
    if (ROOT/'run/deadline-overrun.txt').exists() or (ROOT/'native.pending').exists():raise ValueError('Unresolved/overrun probe')
    if r.get('status')!='ubt_zero_object_review_required' or r.get('exitCode')!=0 or \
       not all(r.get(k) is True for k in ('cleanupConfirmed','sourceStable','withinTotalDeadline')) or \
       r.get('manifestSha256')!=expected:raise ValueError('Accepted owned probe receipt required')
    build=ROOT/'P/Intermediate/Build'
    objects=[p for p in build.rglob('*.obj') if p.stat().st_size>0]
    required={}
    for e in manifest['entries']:
        n=e['path']
        if n.endswith('.cpp') and '/Source/' in n:
            module='MikdashRuntime' if '/Plugins/MikdashRuntime/' in n else 'Receiver04Compile'
            key=(module,Path(n).name+'.obj')
            if key in required:raise ValueError('Ambiguous source object basename')
            matches=[p for p in objects if p.name==key[1] and module in p.parts]
            if len(matches)!=1:raise ValueError('Missing/ambiguous real source object: '+n)
            required[key]=matches[0]
    reflected={'Receiver04Compile':{'OnlineController':['AReceiver04Controller'],
        'OnlineMovement':['UReceiver04WalkerMovement','UReceiver04DoveMovement'],
        'OnlinePawnBases':['AReceiverPossessionWalkerBase','AReceiverPossessionDove'],
        'IsolatedGameMode':['AReceiverIsolatedGameMode']},
        'MikdashRuntime':{'MikdashPlayerController':['AMikdashPlayerController'],'MikdashDovePawn':['AMikdashDovePawn']}}
    for module,stems in reflected.items():
        compiled=[]
        for obj in objects:
            if module in obj.parts and '.gen.' in obj.name:
                compiled.extend(p for p in build.rglob(obj.name[:-4]) if module in p.parts)
        merged='\n'.join(p.read_text(encoding='utf-8-sig') for p in compiled)
        for stem,classes in stems.items():
            cpp=[p for p in build.rglob(stem+'.gen.cpp') if module in p.parts]
            headers=[p for p in build.rglob(stem+'.generated.h') if module in p.parts]
            if len(cpp)!=1 or len(headers)!=1 or stem+'.gen.cpp' not in merged:raise ValueError('Missing actual compiled UHT output: '+stem)
            if not all(c in cpp[0].read_text(encoding='utf-8-sig') for c in classes):raise ValueError('Missing UHT class registration')
    return {'status':'actual-source-UHT-objects-only','sourceObjects':len(required),
            'objects':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in required.values()},
            'runtimeProven':False,'blueprintProven':False,'fixtureExecuted':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--expect-manifest',required=True);a=p.parse_args()
    print(json.dumps(inspect(a.expect_manifest),indent=2))

"""Replay exact reviewed numerical modules using pinned public blobs + payload.

No engine, network, native compilation, installation, publication-tree writes,
full cloth solve or raw author-history preservation claims.
"""
import sys
sys.dont_write_bytecode=True
import argparse,hashlib,importlib,io,json,subprocess,unittest
from pathlib import Path
import numpy as np

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repository',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();base=Path(__file__).resolve().parent;payload=base.parents[4]
    plan=json.loads((base/'allowlist.json').read_text());out=a.output.absolute();repo=a.repository.resolve()
    if out.exists() or out.resolve().is_relative_to(repo) or out.resolve().is_relative_to(payload):raise ValueError('Fresh external output required')
    for p in (out,*out.parents):
        if p.exists() and (p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Reparse output refused')
    contents={}
    for r in plan['files']:
        b=(payload/r['path']).read_bytes()
        if sha(b)!=r['sha256']:raise ValueError('Payload hash mismatch: '+r['path'])
        contents[r['path']]=b
    for r in plan['dependencies']:
        obj=subprocess.check_output(['git','-C',str(repo),'rev-parse',plan['dependency_commit']+':'+r['path']]).decode().strip()
        if obj!=r['blob_oid']:raise ValueError('Dependency object mismatch')
        b=subprocess.check_output(['git','-C',str(repo),'cat-file','blob',obj])
        if sha(b)!=r['sha256']:raise ValueError('Dependency content mismatch')
        contents[r['path']]=b
    out.mkdir();checks={}
    for n,b in contents.items():
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);checks[str(p)]=sha(b)
    project=out/'unreal/MikdashCourtyardV3';v3=project/'SourceAssets/characters-review/KohenBothLayerDrapeV3'
    evidence=base/'evidence';fixture=out/'fixture';(fixture/'Probe03').mkdir(parents=True)
    data=json.loads((evidence/'inner-witness.json').read_text());inner=np.array(data['values'],dtype=data['dtype'])
    if list(inner.shape)!=data['shape'] or sha(inner.tobytes(order='C'))!=data['array_sha256']:raise ValueError('Witness array differs')
    # Generated scratch binary only; NO binary is in publication payload.
    np.savez(fixture/'Probe03/failed-or-diagnostic-state.npz',inner=inner)
    resultdir=out/'results';resultdir.mkdir()
    import portable_inputs as adapter
    adapter.configure(project,fixture,resultdir,checks);sys.modules['inputs']=adapter
    sys.path.insert(0,str(v3))
    witness=importlib.import_module('test_witness');witness.main()
    moving=importlib.import_module('moving_step');sys.argv=['moving_step.py','--frame','31','--out','closing_step_replay'];moving.main()
    ops=importlib.import_module('test_operators')
    names=['test_finite_triangle_interior_edge_vertex_derivatives','test_zero_distance_refuses_normal_invention',
           'test_hinge_angle_derivative','test_rotation_covariance_nonzero_offset']
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(ops.Operators(n) for n in names))
    closing=json.loads((resultdir/'closing_step_replay.json').read_text())
    reviewed=json.loads((evidence/'closing_step01.json').read_text())
    ignored={'elapsedSeconds','V2FilesPreserved','iterations','message'}
    mismatches=[]
    def compare(old,new,path):
        if isinstance(old,dict):
            for k,v in old.items():
                if k not in ignored:compare(v,new.get(k),path+'.'+k)
        elif isinstance(old,(int,float)) and not isinstance(old,bool):
            if not isinstance(new,(int,float)) or not np.isclose(old,new,atol=1e-7,rtol=1e-6):mismatches.append(path)
        elif isinstance(old,list):
            if not isinstance(new,list) or len(old)!=len(new):mismatches.append(path)
            else:
                for i,(x,y) in enumerate(zip(old,new)):compare(x,y,path+'.'+str(i))
        elif old!=new:mismatches.append(path)
    compare(reviewed,closing,'receipt')
    arraychecks={};arrayfixture=json.loads((evidence/'closing-arrays.json').read_text())
    with np.load(resultdir/'closing_step_replay.npz') as z:
        for name,item in arrayfixture['arrays'].items():
            expectedArray=np.asarray(item['values'],dtype=item['dtype'])
            assert list(expectedArray.shape)==item['shape'] and sha(expectedArray.tobytes(order='C'))==item['sha256']
            # 1e-7 cm position tolerance; velocity is displacement / (1/240 s).
            tol=2.4e-5 if name=='velocity' else 1e-7
            actual=z[name];equal=actual.shape==expectedArray.shape and np.allclose(actual,expectedArray,rtol=0,atol=0 if name=='coarseIds' else tol)
            arraychecks[name]=dict(passed=bool(equal),absoluteTolerance=0 if name=='coarseIds' else tol,
                maxAbsoluteDifference=float(np.max(np.abs(actual-expectedArray))) if actual.shape==expectedArray.shape else None)
    reviewedMatch=not mismatches and all(v['passed'] for v in arraychecks.values())
    local=(closing['optimizerSuccess'] and closing['activeContacts']==1 and min(closing['contactGapMinusMarginAfter'])>=-1e-7
           and closing['stationarityMaxKgCmPerS2']<1e-5 and closing['complementarityMax']<1e-7)
    # Reproduce the exact prepared native input from the owned V1 rest descriptor.
    # Same support transformation; no native/vendor asset, new solver or fake API.
    import copy
    model=json.loads((project/'SourceAssets/characters-review/KohenBothLayerDrapeV1/prepared-input.json').read_text());m=copy.deepcopy(model)
    m['schema']='kohen-both-layer-v3-support';m['status']='native-support-input-uncompiled-unrun'
    bones,index,*_=adapter.s.source_parts()
    tethers=[]
    for p,o in zip(m['patterns'][:2],model['patterns'][:2]):
        c=adapter.s.Layer(o);p['maxDistanceCm']=np.where(c.pin,0.,1.).tolist()
        for j in np.flatnonzero(c.pin):p['boneInfluences'][int(j)]=[[index['chest'],1.]]
        tethers.append(dict(layer=p['name'],diagnosticNearestAnchor=c.anchor.tolist(),restGraphGeodesicCm=c.tether.tolist(),
            note='Native GenerateTethers regenerates actual batches; read all native anchors/lengths. This array is an independent nearest-anchor check, not substituted native data.'))
    m['nativeSupportContract']=dict(version=1,maxDistancePropertyEnabled=False,
        maxDistanceMapRole='0/1 mass classification and tether anchors ONLY; spherical constraint disabled',
        expectedDynamic=1936,expectedKinematic=1264,firstWalkFrames=72,rateHz=240,
        ornaments='Exact group/anchor input supplied separately; no shared-material retarget and no ornament dynamics claim')
    # Frozen author's atomic() used Windows text-mode CRLF. Reproduce exact
    # historical bytes explicitly, including when replay runs on another OS.
    prepared=(json.dumps(m,indent=2)+'\n').replace('\n','\r\n').encode();expected=(v3/'NativeBridge01/prepared-input.json').read_bytes()
    exactPrepared=prepared==expected
    tetherExact=(json.dumps(tethers,indent=2)+'\n').replace('\n','\r\n').encode()==(v3/'NativeBridge01/rest-tethers.json').read_bytes()
    anchorbytes=(project/'SourceAssets/characters-review/KohenBothLayerContactAuditV1/attachment-anchor-map.json').read_bytes()
    anchors=json.loads(anchorbytes);ornaments=json.loads((v3/'NativeBridge01/ornament-anchor-input.json').read_text())
    anchorExact=len(anchors['rows'])==144 and ornaments['rows']==anchors['rows'] and ornaments['sourceSha256']==sha(anchorbytes)
    adapter.preserved()
    report=dict(passed=r.wasSuccessful() and local and exactPrepared and tetherExact and anchorExact and reviewedMatch,public_commit=plan['dependency_commit'],public_blobs=len(plan['dependencies']),
        reviewedClosingComparison=dict(passed=reviewedMatch,receiptMismatches=mismatches,receiptAbsoluteTolerance=1e-7,
            receiptRelativeTolerance=1e-6,ignoredReceiptFields=sorted(ignored),arrays=arraychecks,bitwiseCrossPlatformIdentityClaim=False),
        restTethersExact=tetherExact,all144AnchorRowsExact=anchorExact,
        exactPayloadFiles=len(plan['files']),operatorTests=r.testsRun,operatorFailures=len(r.failures)+len(r.errors),
        exactReviewedJacobianModuleReplayed=True,actual240HzLocalStepReplayed=local,preparedNativeInputExact=exactPrepared,
        preparedInputSha256=sha(prepared),jacobian=json.loads((resultdir/'jacobian-tests01.json').read_text()),
        closingStep=closing,omittedAuthorTest='test_preserved_failure_and_active_step_receipts requires private historical file inventory. Not marked passed. Public closure and new step checked separately.',
        nativeCompiled=False,nativeExecuted=False,fullClothAcceptance=False,privateAuthorHistoryReplayed=False,
        python=sys.version.split()[0],numpy=np.__version__,testOutput=stream.getvalue())
    (out/'replay-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('jacobian','closingStep','testOutput')},indent=2))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()

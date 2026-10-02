"""Offline terminal comparison. Does not modify runners, caches, or their receipts."""
import argparse,collections,hashlib,json,re
from pathlib import Path
BASE=Path(__file__).resolve().parent
RUNNER=Path('C:/Mikdash/Verification/angular-native03-20261002/runner')
PIN='c0b3c5fa69e5f9c93a72109a3f9634376b51a3d830c7a3bdd7410cf7411b7b2d'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
DEADLINE='Total deadline: reserve cleanup5s plus poll margin'
def approved_terminal(w):
    guards=(w.get('cleanupConfirmed') is True and w.get('sourcePreserved') is True and
            w.get('minimumStartCommitBytes')==6*1024**3 and w.get('maximumOwnedJobBytes')==4*1024**3 and
            w.get('reserveCommitBytes')==2*1024**3 and w.get('deadlineSeconds')==300 and
            w.get('cleanupDeadlineMilliseconds')==5000 and w.get('startFreeCommitBytes',0)>=6*1024**3 and
            type(w.get('ownedElapsedSeconds')) in (int,float) and 0<=w['ownedElapsedSeconds']<=300 and
            w.get('slotBlocked') is False and not w.get('cleanupError') and not w.get('markerError') and
            not w.get('preservationError') and not w.get('changed') and
            type(w.get('peakPrivateBytes')) is int and 0<=w['peakPrivateBytes']<4*1024**3)
    return bool(guards and ((w.get('status')=='failed' and w.get('error')==DEADLINE) or
                (w.get('status')=='child_exited_zero' and w.get('exitCode')==0 and not w.get('error'))))

def validate_candidate(w,native,run_id,log_errors=False):
    try:
        assert approved_terminal(w) and w['status']=='child_exited_zero' and not log_errors
        assert isinstance(native,dict) and native['status']=='compile_readback_passed' and native['mode']=='Compile'
        assert native['harnessHashesSha256']==PIN
        assert native['compileCoverage']=='representative_vertex_pixel_only_not_full_ODSC_material_or_HISM_coverage'
        assert not native.get('error') and not native.get('cleanupErrors')
        assert native['cachePolicyReadback']=={'r.ShaderCompiler.JobCacheDDC':1,'r.ShaderCompiler.PerShaderDDCGlobal':1,'r.VelocityOutputPass':1,'r.Velocity.EnableVertexDeformation':1}
        assert native['worldGuard']['noPIE'] is True
        assert native['worldGuard']['editorWorld']=='/Engine/Maps/Entry.Entry'
        assert native['worldGuard']['loadReturn']=='/Engine/Maps/Entry.Entry'
        rows=native['compilers'];assert isinstance(rows,list) and len(rows)==1
        row=rows[0];assert row['positiveResourceShaderEvidence'] is True
        assert row['label']=='unaltered_generated_real_Time_graph'
        name='M_Angular_'+run_id.replace('-','_')
        assert row['path']=='/Game/MikdashV3/Runtime/AngularVATStudy01/Materials/'+name+'.'+name
        assert row['compilerErrors']==[] and row['compilerErrorsAfterStatistics']==[]
        for key in ('num_vertex_shader_instructions','num_pixel_shader_instructions','num_vertex_texture_samples','num_pixel_texture_samples','num_samplers'):
            assert type(row['statistics'][key]) is int and row['statistics'][key]>0
        g=native['graph']
        assert sorted(g['currentWpo'])==sorted({0,2,3,4,5,6,7,8,9,10,26,27})
        assert sorted(g['oldWpo'])==sorted({9,*range(11,25),28,29})
        assert {26,27}.issubset(g['normal']) and not {28,29}.intersection(g['normal'])
        assert all(type(x) is int and 0<=x<30 for x in g['normal']) and g['historyBoundary']==25
        assert g['census'].get('MaterialExpressionCustom',0)==0
        assert g['census']['MaterialExpressionPerInstanceCustomData']==30
        assert g['census']['MaterialExpressionPreviousFrameSwitch']>=1
        return True
    except (AssertionError,KeyError,TypeError,ValueError):return False
def analyze(run):
    w=json.loads((run/'wrapper.json').read_text())
    log=run/'native.log';assert log.stat().st_size<=64*1024**2
    hits=set();memory=set();completed=[];dispatches=[];pending=None;lastjob=None
    python=False;log_errors=False
    for line in log.read_text(errors='replace').splitlines():
        m=re.search(r'Found an async DDC result for job with ihash ([a-fA-F0-9]+)',line)
        if m:hits.add(m[1].lower())
        m=re.search(r'already a cached job with the ihash ([a-fA-F0-9]+)',line)
        if m:memory.add(m[1].lower())
        m=re.search(r'Job (\S+)\(permutation (\d+), format (\w+)\) compile time exceeded threshold',line)
        if m:lastjob=(m[1],int(m[2]),m[3]);completed.append(lastjob)
        m=re.search(r'shaders left to compile (\d+)',line)
        if m:pending=int(m[1])
        m=re.search(r"Started (\d+) 'Local' shader compile jobs with '(\w+)' priority",line)
        if m:dispatches.append({'pending':pending,'priority':m[2],'precedingCompletedJob':lastjob})
        if 'LogPythonScriptCommandlet: Display: Running Python script:' in line:python=True
        if re.search(r'Failed to compile Material|Default Material will be used|LogShaderCompilers: Error|LogMaterial: Error|Fatal error:',line):log_errors=True
    native=json.loads((run/'native.json').read_text()) if (run/'native.json').exists() else None
    vsm=[p for name,p,fmt in completed if name=='FVirtualShadowMapProjectionCS']
    return {'wrapper':w,'approvedTerminal':approved_terminal(w),'logErrors':log_errors,
      'logSha256':sha(log),'wrapperSha256':sha(run/'wrapper.json'),'arguments':w['arguments'],
      'ddcHitHashes':sorted(hits),'inProcessHitCount':len(memory),'completedJobMessages':len(completed),
      'completionIdentities':[list(x) for x in sorted(set(completed))],
      'completionTypes':dict(collections.Counter(x[0] for x in completed)),
      'lastDispatch':dispatches[-1] if dispatches else None,'maxVsmPermutationCompleted':max(vsm) if vsm else None,
      'pythonStarted':python,'nativeStatus':native.get('status') if native else None,
      'candidateProof':validate_candidate(w,native,run.parent.name,log_errors)}

def normalized(args):
    return [x for x in args if not x.startswith(('-AngularRun=','-abslog='))]

def compare(a,b):
    assert normalized(a['arguments'])==normalized(b['arguments']),'Not an identical configuration comparison'
    if not approved_terminal(a['wrapper']) or not approved_terminal(b['wrapper']) or b.get('logErrors'):
        return {'boundedExperimentProgress':False,'candidateProof':False,'decision':'STOP: terminal/guard/diagnostic failure; cache growth cannot override this'}
    if b['wrapper']['status']=='child_exited_zero' and not b['candidateProof']:
        return {'boundedExperimentProgress':False,'candidateProof':False,'decision':'STOP: success status lacks independently validated candidate evidence'}
    old,new=set(a['ddcHitHashes']),set(b['ddcHitHashes'])
    d=b['lastDispatch'];prior=a['lastDispatch']
    same_stage=bool(d and prior and d['priority']==prior['priority']=='High' and
        d['precedingCompletedJob'] and d['precedingCompletedJob'][0]=='FVirtualShadowMapProjectionCS' and
        prior['precedingCompletedJob'] and prior['precedingCompletedJob'][0]=='FVirtualShadowMapProjectionCS')
    advancement=bool(same_stage and d['pending']<=prior['pending']-100 and
        b['maxVsmPermutationCompleted']>a['maxVsmPermutationCompleted'])
    progress=len(new-old)>=100 and advancement
    return {'newDdcHitCount':len(new-old),'priorDdcHitsSeenAgain':len(old&new),'priorHitsNotObserved':len(old-new),
      'sameTerminalStageComparable':same_stage,'sameStageAdvanceAtLeast100':advancement,
      'boundedExperimentProgress':progress,'candidateProof':b['candidateProof'],
      'decision':'candidate proof reached' if b['candidateProof'] else ('measured progress; stop and review, no further run authorized' if progress else 'STOP: no qualifying progress or stage incomparable; diagnose before any additional run'),
      'attributionLimit':'New DDC hits establish newly observed persisted reuse, not exact attribution to Compile03 writes; completion messages lack matching input hashes. Shared DDC writers can also contribute.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path);p.add_argument('--record-baseline',action='store_true');args=p.parse_args()
    assert sha(RUNNER/'harness-hashes.json')==PIN
    for name,digest in json.loads((RUNNER/'harness-hashes.json').read_text()).items():assert sha(RUNNER/name)==digest
    baseline=analyze(RUNNER/'runs/angular-compile03/compile')
    known=json.loads((RUNNER/'runs/angular-compile03/compile/cache-progress.json').read_text())
    assert baseline['ddcHitHashes']==known['uniqueDdcHitInputHashes']
    assert baseline['completedJobMessages']==known['completedJobMessages']
    if args.candidate:
        candidate=args.candidate.resolve()
        assert candidate.is_relative_to(RUNNER/'runs')
        print(json.dumps(compare(baseline,analyze(candidate)),indent=2))
    elif args.record_baseline:
        target=BASE/'terminal-baseline.json'
        with target.open('x',encoding='utf-8') as f:json.dump(baseline,f,indent=2);f.write('\n')
        print(json.dumps({'ddcHits':len(baseline['ddcHitHashes']),'completed':baseline['completedJobMessages'],
            'lastDispatch':baseline['lastDispatch'],'completionTypes':baseline['completionTypes']}))
    else:print(json.dumps({'ddcHits':len(baseline['ddcHitHashes']),'lastDispatch':baseline['lastDispatch']}))

if __name__=='__main__':main()

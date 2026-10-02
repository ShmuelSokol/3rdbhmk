"""Focused fail-closed tests, no native execution or runner writes."""
import copy,json
from pathlib import Path
from compare_progress import analyze,compare,validate_candidate,RUNNER,PIN,approved_terminal
BASE=Path(__file__).resolve().parent
cases=[]
def check(name,ok):
    assert ok,name
    cases.append(name)
a=analyze(RUNNER/'runs/angular-compile03/compile')
b=copy.deepcopy(a);b['ddcHitHashes']+=['new'+str(x) for x in range(100)]
b['lastDispatch']['pending']=3051;b['maxVsmPermutationCompleted']=609
check('exact deadline plus both progress thresholds',compare(a,b)['boundedExperimentProgress'])
for name,key,value in [('memory','error','Owned job private cap'),('reserve','error','2GiB reserve guard'),
 ('other error','error','Child failed'),('cleanup','cleanupConfirmed',False),('preservation','sourcePreserved',False),
 ('blocked','slotBlocked',True),('raised memory cap','maximumOwnedJobBytes',5*1024**3),
 ('lower reserve','reserveCommitBytes',1),('lower start','minimumStartCommitBytes',1),
 ('raised deadline','deadlineSeconds',600),('cleanup deadline','cleanupDeadlineMilliseconds',6000),
 ('over elapsed','ownedElapsedSeconds',301),('peak cap','peakPrivateBytes',4*1024**3)]:
    bad=copy.deepcopy(b);bad['wrapper'][key]=value
    check('stop despite cache growth: '+name,not compare(a,bad)['boundedExperimentProgress'])
bad=copy.deepcopy(a);bad['ddcHitHashes']=b['ddcHitHashes'];bad['pythonStarted']=True
check('Python start alone fails',not compare(a,bad)['boundedExperimentProgress'])
bad=copy.deepcopy(b);bad['ddcHitHashes']=a['ddcHitHashes']
check('queue advance alone fails',not compare(a,bad)['boundedExperimentProgress'])
bad=copy.deepcopy(b);bad['lastDispatch']['priority']='ExtraHigh'
check('incomparable priority fails',not compare(a,bad)['boundedExperimentProgress'])
w=copy.deepcopy(a['wrapper']);w.update(status='child_exited_zero',exitCode=0);w.pop('error')
n={'status':'compile_readback_passed','mode':'Compile','harnessHashesSha256':PIN,
 'compileCoverage':'representative_vertex_pixel_only_not_full_ODSC_material_or_HISM_coverage',
 'cachePolicyReadback':{'r.ShaderCompiler.JobCacheDDC':1,'r.ShaderCompiler.PerShaderDDCGlobal':1,'r.VelocityOutputPass':1,'r.Velocity.EnableVertexDeformation':1},
 'worldGuard':{'noPIE':True,'editorWorld':'/Engine/Maps/Entry.Entry','loadReturn':'/Engine/Maps/Entry.Entry'},
 'compilers':[{'positiveResourceShaderEvidence':True,'label':'unaltered_generated_real_Time_graph',
 'path':'/Game/MikdashV3/Runtime/AngularVATStudy01/Materials/M_Angular_test.M_Angular_test',
 'compilerErrors':[],'compilerErrorsAfterStatistics':[],
 'statistics':{k:1 for k in ('num_vertex_shader_instructions','num_pixel_shader_instructions','num_vertex_texture_samples','num_pixel_texture_samples','num_samplers')}}],
 'graph':{'currentWpo':sorted({0,2,3,4,5,6,7,8,9,10,26,27}),'oldWpo':sorted({9,*range(11,25),28,29}),
 'normal':[26,27],'historyBoundary':25,'census':{'MaterialExpressionPerInstanceCustomData':30,'MaterialExpressionPreviousFrameSwitch':1}}}
check('valid synthetic representative receipt',validate_candidate(w,n,'test'))
for key in n['compilers'][0]['statistics']:
    bad=copy.deepcopy(n);bad['compilers'][0]['statistics'][key]=0
    check('zero statistic rejected '+key,not validate_candidate(w,bad,'test'))
for key,value in [('harnessHashesSha256','wrong'),('compilers',[]),('graph',{}),('status','failed')]:
    bad=copy.deepcopy(n);bad[key]=value
    check('candidate rejects '+key,not validate_candidate(w,bad,'test'))
for key in ('compilerErrors','compilerErrorsAfterStatistics'):
    bad=copy.deepcopy(n);bad['compilers'][0][key]=['diagnostic']
    check('candidate rejects '+key,not validate_candidate(w,bad,'test'))
for key,value in [('currentWpo',[]),('oldWpo',[]),('normal',[28,29]),('historyBoundary',24),('census',{'MaterialExpressionCustom':1})]:
    bad=copy.deepcopy(n);bad['graph'][key]=value
    check('candidate rejects graph '+key,not validate_candidate(w,bad,'test'))
check('candidate rejects log diagnostics',not validate_candidate(w,n,'test',True))
bad=copy.deepcopy(w);bad['exitCode']=1
check('candidate rejects nonzero exit',not validate_candidate(bad,n,'test'))
bad=copy.deepcopy(b);bad['wrapper']=w;bad['candidateProof']=False
check('success string without evidence stops progress',not compare(a,bad)['boundedExperimentProgress'])
result={'passed':True,'cases':cases,'count':len(cases),'nativeLaunches':0,'scope':'Synthetic negative receipts and actual terminal03 parsing; no native candidate proof'}
(BASE/'comparison-tests.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'cases':len(cases)}))

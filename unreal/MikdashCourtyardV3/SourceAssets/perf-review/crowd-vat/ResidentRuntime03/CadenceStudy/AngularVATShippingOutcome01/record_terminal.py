"""Create sanitized terminal evidence; never writes the frozen runner or raw log."""
import collections,hashlib,json,re
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[5]
RUNNER=Path('C:/Mikdash/Verification/angular-shipping02-20261002/runner')
RUN=RUNNER/'runs/angular-shipping01/compile'
PIN='fcf110bc7e2bc11711fe4872225d6e333bdcbc2f5f4f48be9cd582ae4f098832'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(RUNNER/'harness-hashes.json')==PIN
pins=json.loads((RUNNER/'harness-hashes.json').read_text())
for name,digest in pins.items():assert sha(RUNNER/name)==digest
w=json.loads((RUN/'wrapper.json').read_text())
assert w['status']=='failed' and w['error']=='Total deadline: reserve cleanup5s plus poll margin'
assert w['cleanupConfirmed'] and w['sourcePreserved'] and not w['slotBlocked'] and not w['changed']
assert not (RUN/'native.json').exists()
text=(RUN/'native.log').read_text(errors='replace')
hits=set(re.findall(r'Found an async DDC result for job with ihash ([a-fA-F0-9]+)',text))
memory=set(re.findall(r'already a cached job with the ihash ([a-fA-F0-9]+)',text))
jobs=re.findall(r'Job (\S+)\(permutation (\d+), format (\w+)\) compile time exceeded threshold',text)
queues=re.findall(r'shaders left to compile (\d+)',text)
python='LogPythonScriptCommandlet: Display: Running Python script:' in text
assert not python
settings=dict(re.findall(r'Set CVar \[\[(r.VelocityOutputPass|r.Velocity.EnableVertexDeformation):([0-9]+)\]\]',text))
assert settings=={'r.VelocityOutputPass':'0','r.Velocity.EnableVertexDeformation':'2'}
patterns=['Fatal error:',r'Log\w+: Error:',r'Failed to compile Material',r'Default Material will be used']
counts={p:len(re.findall(p,text)) for p in patterns}
receipt={'scope':'Shipping0/2 attempt terminal failure; sanitized evidence only',
 'manifestSha256':PIN,'all21RunnerPinsVerified':True,
 'wrapper':{k:w[k] for k in ('status','error','ownedElapsedSeconds','peakPrivateBytes','startFreeCommitBytes','cleanupConfirmed','sourcePreserved','slotBlocked','changed')},
 'peakGiB':w['peakPrivateBytes']/1024**3,'nativeReceiptPresent':False,'pythonScriptReached':python,
 'startupLoggedSettings':settings,'nativePythonPolicyReadback':'not reached',
 'progress':{'uniqueDdcHits':len(hits),'uniqueInProcessHits':len(memory),'completionMessages':len(jobs),
   'completionTypes':dict(collections.Counter(j[0] for j in jobs)),'lastCompletion':jobs[-1],
   'lastReportedPendingCount':int(queues[-1]),'limit':'Pending count is one dispatch priority, not total remaining startup work or ETA'},
 'diagnosticPatternCounts':counts,
 'rawEvidenceNeverPublish':{name:{'sha256':sha(RUN/name),'path':str(RUN/name)} for name in ('wrapper.json','launch.json','native.log')},
 'conclusion':'Shipping-aligned0/2 reached startup shader work but did not reach Python or candidate graph within300s. It is not a shader compile, HISM, pixel or temporal success. No automatic retry.',
 'comparisonLimit':'Do not compare this changed velocity profile using the frozen1/1 Compile03/04 acceptance rule. Existing04 STOP stays intact.',
 'productionClaim':False,'retryLaunched':False}
out=BASE/'terminal-outcome.json'
with out.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps({'seconds':w['ownedElapsedSeconds'],'peakGiB':receipt['peakGiB'],'progress':receipt['progress'],
 'cleanup':w['cleanupConfirmed'],'preserved':w['sourcePreserved'],'slotBlocked':w['slotBlocked'],'errorCounts':counts}))

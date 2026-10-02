"""Summarize a terminal external run without publishing its raw log or invoking Unreal."""
import argparse,hashlib,json,re
from pathlib import Path

def summarize(log):
    ddc=set();memory=set();completed=0;dispatch=0;lines=0
    assert log.stat().st_size<=64*1024**2,'Log exceeds bounded offline analysis limit'
    with log.open(encoding='utf-8',errors='replace') as stream:
        for line in stream:
            lines+=1
            m=re.search(r'Found an async DDC result for job with ihash ([a-fA-F0-9]+)',line)
            if m:ddc.add(m.group(1).lower())
            m=re.search(r'already a cached job with the ihash ([a-fA-F0-9]+)',line)
            if m:memory.add(m.group(1).lower())
            if 'LogShaderCompilers:' in line and ' compile time exceeded threshold (' in line:completed+=1
            if 'LogShaderCompilers:' in line and 'shaders left to compile' in line:dispatch+=1
    return {'lines':lines,'uniqueDdcHitInputHashes':sorted(ddc),'uniqueInProcessHitInputHashes':sorted(memory),
            'completedJobMessages':completed,'workerDispatchMessages':dispatch}

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);a=p.parse_args()
    run=a.run.resolve();assert run.is_relative_to(Path('C:/Mikdash/Verification').resolve())
    wrapper=json.loads((run/'wrapper.json').read_text())
    assert wrapper['cleanupConfirmed'] and not wrapper['slotBlocked'],'Terminal confirmed cleanup required'
    result=summarize(run/'native.log')
    result.update({'wrapperStatus':wrapper['status'],'logSha256':hashlib.sha256((run/'native.log').read_bytes()).hexdigest(),
        'nativeReceiptPresent':(run/'native.json').exists(),'scope':'Observed log messages, not shader acceptance',
        'limits':['DDC hits prove returned cache entries, not that this attempt wrote them',
        'In-process hits are not persistence evidence','Completion messages do not establish successful compilation or acknowledged durable DDC writes',
        'A killed process can lose pending asynchronous puts; no automatic retry or guaranteed accumulated progress']})
    out=run/'cache-progress.json'
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'receipt':str(out),'ddcHits':len(result['uniqueDdcHitInputHashes']),
                      'completedJobMessages':result['completedJobMessages']}))

if __name__=='__main__':main()

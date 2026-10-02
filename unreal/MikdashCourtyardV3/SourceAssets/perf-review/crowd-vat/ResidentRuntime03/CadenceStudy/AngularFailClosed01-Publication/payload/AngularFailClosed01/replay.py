import argparse,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('case',choices=['run01','run02','inject01','inject02']);p.add_argument('--check-only',action='store_true');a=p.parse_args()
B=Path(__file__).resolve().parent/a.case
r=json.loads((B/'receipt.json').read_text());sources={}
for name,h in r['sources'].items():
    raw=gzip.decompress((B/(name+'.gz')).read_bytes())
    assert hashlib.sha256(raw).hexdigest()==h,name
    sources[name]=raw
csvs={f.name[:-3]:gzip.decompress(f.read_bytes()) for f in B.glob('*.csv.gz')}
for name,h in r['artifacts'].items():
    if name=='run.log.gz':continue # local-only; never needed to reproduce
    assert hashlib.sha256((B/name).read_bytes()).hexdigest()==h,name
if a.check_only:
    print('pinned sources and',len(csvs),'CSV artifacts verified; no run log needed')
    raise SystemExit(0)
W=Path(tempfile.mkdtemp(prefix='placed-exact-replay-'))
for name,raw in sources.items():(W/name).write_bytes(raw)
batch='@echo off\ncall "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\ncl /nologo /std:c++17 /EHsc /W4 /O2 fixture.cpp /Fe:fixture.exe\nif errorlevel 1 exit /b 2\nfixture.exe '+str(r['seconds'])+(' inject' if r.get('injected') else '')+'\n'
(W/'replay.cmd').write_text(batch)
x=subprocess.run(['cmd.exe','/c','replay.cmd'],cwd=str(W),capture_output=True,timeout=300)
log=x.stdout+x.stderr;(W/'replay.log').write_bytes(log)
assert x.returncode==r['exitCode'],str(W)
expected='CrowdBoundaryMath: %d checks, %d failures'%(r['checks'],r['failures'])
assert expected in log.decode(errors='replace'),str(W)
for name,raw in csvs.items():assert (W/name).read_bytes()==raw,name
print('Exact rejected result reproduced:',expected,';',len(csvs),'CSVs match. Local log:',W/'replay.log')

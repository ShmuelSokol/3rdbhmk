import csv,gzip,hashlib,json,re,subprocess,sys,tempfile
from pathlib import Path
B=Path(__file__).resolve().parent
Seconds=int(sys.argv[1]);Label=sys.argv[2];Injected=len(sys.argv)>3 and sys.argv[3]=='inject'
assert Seconds in [120,600] and Label.isalnum()
Out=B/Label;Out.mkdir();Work=Path(tempfile.mkdtemp(prefix='shared-actual-'+Label+'-'))
sources={}
for p in B.iterdir():
    if p.suffix not in ['.cpp','.h']:continue
    data=p.read_bytes();(Work/p.name).write_bytes(data);(Out/(p.name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    sources[p.name]=hashlib.sha256(data).hexdigest()
batch='@echo off\ncall "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /EHsc /W4 /O2 /I. fixture.cpp /Fe:fixture.exe\nif errorlevel 1 exit /b 1\nfixture.exe '+str(Seconds)+(' inject' if Injected else '')+'\n'
(Work/'run.cmd').write_text(batch)
Result=subprocess.run(['cmd.exe','/c','run.cmd'],cwd=str(Work),capture_output=True,timeout=300)
Log=Result.stdout+Result.stderr;(Work/'run.log').write_bytes(Log);(Out/'run.log.gz').write_bytes(gzip.compress(Log,mtime=0))
Rows={}
for p in Work.glob('*.csv'):
    data=p.read_bytes();(Out/(p.name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    if p.stem in ['group-metrics','member-metrics','recovery']:Rows[p.stem]=list(csv.DictReader(data.decode().splitlines()))
Match=re.search(rb'CrowdBoundaryMath: (\d+) checks, (\d+) failures',Log)
Receipt=dict(seconds=Seconds,injected=Injected,exitCode=Result.returncode,checks=int(Match[1]) if Match else None,failures=int(Match[2]) if Match else None,
    sources=sources,sourceUnchanged=all(hashlib.sha256((B/n).read_bytes()).hexdigest()==h for n,h in sources.items()),rows=Rows,localLogs=str(Work))
Receipt['walking']=[]
if Rows:
    keys=['population','fps','scale','members','budget','fault','terminal']
    for r in Rows['recovery']:
        if r['fault']!='0':continue
        mm=[m for m in Rows['member-metrics'] if m['recovery']=='1' and all(m[k]==r[k] for k in keys)]
        minimum=min(float(m[c]) for m in mm for c in ['late0','late1','late2'])
        Receipt['walking'].append(dict({k:r[k] for k in keys},minimumMember10sCm=minimum,passes=minimum>80,phase=r['phase'],entries=r['entries'],completions=r['completions']))
Receipt['artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Out.iterdir() if p.is_file()}
(Out/'receipt.json').write_text(json.dumps(Receipt,indent=2)+'\n')
print(json.dumps({k:Receipt[k] for k in ['seconds','exitCode','checks','failures','sourceUnchanged','localLogs']}))
print('walking',sum(x['passes'] for x in Receipt['walking']),len(Receipt['walking']))
print(Log.decode(errors='replace')[-2500:] if not Match else '\n'.join([x for x in Log.decode(errors='replace').splitlines() if not x.startswith(('group ','scheduled '))][-40:]))

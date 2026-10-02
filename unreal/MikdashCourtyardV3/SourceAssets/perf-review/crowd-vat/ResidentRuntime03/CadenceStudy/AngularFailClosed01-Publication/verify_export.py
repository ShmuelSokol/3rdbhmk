import argparse,csv,gzip,hashlib,json,pathlib,shutil,subprocess,sys,tempfile
p=argparse.ArgumentParser();p.add_argument('--compile-unit',action='store_true');args=p.parse_args()
B=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((B/'publication-manifest.json').read_text());checks=0
for name,h in m['files'].items():
    f=B/name
    assert f.resolve().is_relative_to(B.resolve()) if hasattr(f.resolve(),'is_relative_to') else '..' not in pathlib.Path(name).parts
    assert f.is_file() and sha(f)==h,name
    assert f.suffix.lower() not in ['.exe','.dll','.obj','.pdb','.uasset','.umap','.log'],name
    assert not name.endswith('.log.gz'),name
    checks+=1
    if f.suffix in ['.json','.py','.h','.cpp']:
        text=f.read_text(encoding='utf-8')
        assert not any(('C:'+sep+'Users'+sep) in text for sep in [chr(92),chr(92)*2,'/']),name
c=json.loads((B/'dependency-closure.json').read_text())
for name,r in c['originFiles'].items():assert sha(B/name)==r['exportSha256'];checks+=1
F=B/'payload/AngularFailClosed01'
for case in ['run01','run02','inject01','inject02']:
    result=subprocess.run([sys.executable,str(F/'replay.py'),case,'--check-only'],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    checks+=1
def outcomes(path):
    rows=list(csv.DictReader(gzip.decompress(path.read_bytes()).decode().splitlines()));groups={}
    for r in rows:
        if any(r[k]!=v for k,v in [('recovery','1'),('fault','0'),('terminal','0'),('enabled','1'),('sharedHold','0')]):continue
        key=tuple(r[k] for k in ['population','fps','scale','members','budget'])
        groups[key]=min(groups.get(key,float('inf')),*(float(r[k]) for k in ['late0','late1','late2']))
    return groups
comparison={}
for seconds,case in [(120,'run01'),(600,'run02')]:
    before=outcomes(B/('comparison-inputs/placed%d.member-metrics.csv.gz'%seconds))
    after=outcomes(F/case/'member-metrics.csv.gz');assert before.keys()==after.keys() and len(after)==81
    assert gzip.decompress((B/('comparison-inputs/angular%d.member-metrics.csv.gz'%seconds)).read_bytes())==gzip.decompress((F/case/'member-metrics.csv.gz').read_bytes())
    comparison[str(seconds)]={'naturalBefore':sum(v>80 for v in before.values()),'naturalAfter':sum(v>80 for v in after.values()),'total':81,
        'lostWalkingPasses':sum(before[k]>80 and after[k]<=80 for k in before),'minimumWindowRegressions':sum(after[k]<before[k]-1e-7 for k in before)}
    checks+=3
assert comparison['120']['naturalBefore']==9 and comparison['600']['naturalBefore']==6
assert all(x['naturalAfter']==15 and x['lostWalkingPasses']==0 for x in comparison.values())
unit=False
if args.compile_unit:
    W=pathlib.Path(tempfile.mkdtemp(prefix='angular-fc-export-review-'))
    for name in m['files']:
        target=W/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(B/name,target)
    r=subprocess.run([sys.executable,str(W/'payload/AngularFailClosed01/verify_commit_gates.py')],capture_output=True,text=True,timeout=90)
    assert r.returncode==0,r.stdout+r.stderr
    assert 'commit gate checks=88 failures=0' in r.stdout
    unit=True;checks+=1
print(json.dumps(dict(status='source-only export verified; NOT ADOPTED',checks=checks,files=len(m['files']),unit88ExecutedInUniqueTemp=unit,
    comparison=comparison,validWalkingFailures=134,metadataSanitization=len(c['metadataSanitization']),rawLogsExported=0,executablesExported=0,privateReviewReceiptsExported=0),indent=2))

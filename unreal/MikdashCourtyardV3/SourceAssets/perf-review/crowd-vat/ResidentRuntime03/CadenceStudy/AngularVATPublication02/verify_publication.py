"""Read-only source publication audit; no preparation, fault injection or native launch."""
import argparse, hashlib, json
from pathlib import Path
BASE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=BASE.parents[5]);a=p.parse_args()
root=a.root.resolve()
manifest=json.loads((BASE/'publish-allowlist.json').read_text())
def status(name,digest):
    path=(root/name).resolve()
    assert path.is_relative_to(root)
    if not path.is_file():return 'missing'
    return 'match' if hashlib.sha256(path.read_bytes()).hexdigest()==digest else 'changed'
entries=manifest['entries'];assert len({r['path'] for r in entries})==len(entries)
for row in entries:
    assert not set(Path(row['path']).parts)&{'P','ReviewProject','runs','fault-tests','Saved','Intermediate','DerivedDataCache','DDC','Binaries','__pycache__'}
    assert Path(row['path']).suffix.lower() in {'.py','.ps1','.cs','.json','.txt','.ini','.uproject','.fragment'}
sources={r['path']:status(r['path'],r['sha256']) for r in entries}
requirements=json.loads((BASE.parent/'AngularVATPublication01/prerequisites.json').read_text())['requirements']
prereqs={name:status(name,row['sha256']) for name,row in requirements.items()}
ok=all(v=='match' for v in sources.values())
print(json.dumps({'sourcePayloadValid':ok,'sourceFiles':len(entries),
    'sourceMismatches':{k:v for k,v in sources.items() if v!='match'},
    'preparationInputsAvailable':ok and all(v=='match' for v in prereqs.values()),
    'prerequisiteCounts':{v:list(prereqs.values()).count(v) for v in ('match','missing','changed')},
    'nativeLaunchAuthorizedByThisCheck':False,'nativeCompileProof':False,
    'entrypoint':'Publication02/prepare_external.py only; legacy preparation/testing recipes are historical',
    'noNativeExecution':True,'noPublicationPerformed':True},indent=2))
raise SystemExit(0 if ok else 1)

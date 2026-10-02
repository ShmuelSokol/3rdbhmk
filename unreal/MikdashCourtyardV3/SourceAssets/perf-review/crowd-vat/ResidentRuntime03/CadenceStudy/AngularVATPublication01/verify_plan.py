"""Read-only exact-path source/prerequisite audit. No staging or native execution."""
import argparse,hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,default=BASE.parents[5])
args=parser.parse_args()
root=args.root.resolve()
manifest=json.loads((BASE/'publish-allowlist.json').read_text())
def file_status(path,expected):
    p=(root/path).resolve()
    if not p.is_relative_to(root):raise ValueError('Path outside project')
    if not p.is_file():return 'missing'
    return 'match' if hashlib.sha256(p.read_bytes()).hexdigest()==expected else 'changed'
source={row['path']:file_status(row['path'],row['sha256']) for row in manifest['entries']}
assert len(source)==len(manifest['entries']),'Duplicate allowlist paths'
for path in source:
    assert not any(part in ('P','ReviewProject','runs','fault-tests','Saved','Intermediate','DerivedDataCache','DDC','Binaries','__pycache__') for part in Path(path).parts),path
    assert Path(path).suffix not in ('.uasset','.umap','.ubulk','.uexp','.png','.exr','.dll','.exe','.zip','.log'),path
required=json.loads((BASE/'prerequisites.json').read_text())['requirements']
prereqs={path:file_status(path,row['sha256']) for path,row in required.items()}
source_ok=all(s=='match' for s in source.values())
prereq_ok=all(s=='match' for s in prereqs.values())
print(json.dumps({'sourcePayloadValid':source_ok,'sourceFiles':len(source),'sourceMismatches':{p:s for p,s in source.items() if s!='match'},
    'prerequisiteCounts':{s:list(prereqs.values()).count(s) for s in ('match','missing','changed')},
    'nativeEligibility':source_ok and prereq_ok,'nativeEligibilityMeaning':'Exact preparation inputs available only; NOT launch authorization or native proof',
    'missingOrChangedPrerequisites':{p:s for p,s in prereqs.items() if s!='match'},'noNativeExecution':True,'noPublicationPerformed':True},indent=2))
raise SystemExit(0 if source_ok else 1)

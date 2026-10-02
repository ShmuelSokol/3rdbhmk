"""Portable explicit-closure verifier/exporter. No compiler, process or network."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re

CONTROL=Path(__file__).resolve().parent
ROOT=CONTROL.parent
MANIFEST='interaction_publication01/allowlist-01.json'

def sha(data):return hashlib.sha256(data).hexdigest()
def safe(root,name):
    value=PurePosixPath(name)
    if not re.fullmatch(r'[A-Za-z0-9_./-]{1,240}',name) or value.is_absolute() or '..' in value.parts or str(value)!=name:
        raise ValueError('Unsafe relative name')
    path=root/name
    for part in (path,*path.parents):
        if part.exists() and (part.is_symlink() or getattr(part.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Reparse path refused')
    path.resolve().relative_to(root.resolve())
    return path

def verify(expected,root=ROOT,publication=None):
    raw=safe(root,MANIFEST).read_bytes()
    if sha(raw)!=expected:raise ValueError('Manifest mismatch')
    m=json.loads(raw);seen=set()
    for entry in m['entries']:
        name=entry['path']
        if name.casefold() in seen:raise ValueError('Duplicate entry')
        seen.add(name.casefold())
        data=safe(root,name).read_bytes()
        if len(data)!=entry['bytes'] or sha(data)!=entry['sha256']:raise ValueError('Pinned file mismatch')
        # Every listed artifact is source/text. Never allow raw logs/executables.
        if Path(name).name!='.gitattributes' and Path(name).suffix.lower() not in {'.py','.h','.cpp','.md','.json','.txt','.patch'}:raise ValueError('Unsupported artifact')
        text=data.decode('utf-8-sig')
        if re.search(r'(?i)[a-z]:[\\/]',text) or any(prefix in text for prefix in ('/'+'Users'+'/', '/'+'home'+'/')):
            raise ValueError('Private workstation path in payload')
    # Shared existing publication trees may contain unrelated files; enforce exact
    # contents only inside our three new directories.
    actual=set()
    for directory in ('runtime_interaction01','runtime_interaction01_evidence01','interaction_publication01'):
        actual.update(p.relative_to(root).as_posix() for p in safe(root,directory).rglob('*') if p.is_file())
    if actual!={e['path'] for e in m['entries']}|{MANIFEST}:raise ValueError('Closure mismatch')
    evidence=json.loads((root/'runtime_interaction01_evidence01/receipt-01.json').read_text())
    for name,digest in evidence['exactBaseSourceSha256'].items():
        if sha(safe(root,'runtime_interaction01/'+name).read_bytes())!=digest:raise ValueError('Executed source differs')
    if evidence['cases']!=10 or evidence['checks']!=28 or not evidence['casesExecuted']:raise ValueError('Execution receipt mismatch')
    if any(p['exitCode']!=0 or not p['cleanupConfirmed'] for p in evidence['phases']):raise ValueError('Cleanup evidence mismatch')
    if publication:
        context=json.loads((root/'interaction_publication01/publication-context.json').read_text())
        for e in context['existingDependencies']:
            if sha(safe(publication,e['repositoryPath']).read_bytes()) not in {e['sha256'],e['repositoryBlobSha256']}:raise ValueError('Published dependency drift')
    return m,raw

def export(expected,destination):
    m,raw=verify(expected);destination=destination.absolute()
    safe(destination,'probe')
    if destination.exists():raise ValueError('Fresh destination required')
    if ROOT==destination or ROOT in destination.parents or destination in ROOT.parents:raise ValueError('Overlapping destination')
    destination.mkdir()
    for e in m['entries']:
        p=safe(destination,e['path']);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as stream:stream.write(safe(ROOT,e['path']).read_bytes())
    with safe(destination,MANIFEST).open('xb') as stream:stream.write(raw)
    verify(expected,destination)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--expect-manifest',required=True)
    p.add_argument('--export',type=Path);p.add_argument('--publication-root',type=Path)
    a=p.parse_args();m,_=verify(a.expect_manifest,publication=a.publication_root)
    if a.export:export(a.expect_manifest,a.export)
    print(json.dumps({'status':'portable-source-verified','files':len(m['entries'])+1,'executedHeaderCases':10,'executedHeaderChecks':28,'compilerRunByVerifier':False}))

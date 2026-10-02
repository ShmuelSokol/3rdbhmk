"""Optional OFFLINE asset-copy preparation. Does not launch Unreal or reparent."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parent
def clean(p):
    p=Path(p).absolute()
    for q in (p,*p.parents):
        if q.exists() and (q.is_symlink() or getattr(q.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Reparse refused')
    return p.resolve()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def prepare(content,dest,expected):
    content=clean(content);dest=clean(dest)
    if dest.exists() or dest.parent.name!='Verification' or not dest.name.startswith('ReceiverIntegrationAssets'):
        raise ValueError('Fresh designated isolated copy required')
    for root in (ROOT,content):
        if dest==root or root in dest.parents or dest in root.parents:raise ValueError('Overlap refused')
    if sha(ROOT/'allowlist.json')!=expected:raise ValueError('Stage manifest mismatch')
    entries=json.loads((ROOT/'allowlist.json').read_text())['entries']
    for e in entries:
        p=clean(ROOT/e['path'])
        if ROOT not in p.parents or sha(p)!=e['sha256']:raise ValueError('Stage pin mismatch')
    files=[clean(p) for p in content.rglob('*') if p.is_file() and p.suffix.lower() in ('.uasset','.umap','.ubulk','.uexp')]
    if len(files)>20000 or not files:raise ValueError('Asset count refused')
    if any(not re.fullmatch(r'[A-Za-z0-9_./-]+',p.relative_to(content).as_posix()) for p in files):
        raise ValueError('Asset name outside reviewed wrapper allowlist grammar')
    size=sum(p.stat().st_size for p in files)
    if size>10*1024**3 or shutil.disk_usage(dest.parent).free<size+6*1024**3:raise ValueError('Asset-copy disk guard')
    spec=json.loads((ROOT/'integration.json').read_text())
    for n,h in spec['blueprintInputPins'].items():
        if sha(content/n)!=h:raise ValueError('Blueprint source pin changed')
    dest.mkdir()
    # No binaries, config from active project, Python startup files, symlinks or
    # junctions. Only the reviewed stage plus project-owned Unreal asset data.
    for e in entries:
        target=dest/e['path'];target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write((ROOT/e['path']).read_bytes())
    parent_raw=(ROOT/'allowlist.json').read_bytes()
    with (dest/'source-stage-allowlist.json').open('xb') as f:f.write(parent_raw)
    child_entries=list(entries)+[{'path':'source-stage-allowlist.json','bytes':len(parent_raw),
                                 'sha256':hashlib.sha256(parent_raw).hexdigest()}]
    assets=[]
    for p in sorted(files):
        n=p.relative_to(content).as_posix();before=sha(p);target=dest/'P/Content'/n
        target.parent.mkdir(parents=True,exist_ok=True)
        with p.open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst,1024*1024)
        if sha(p)!=before or sha(target)!=before:raise ValueError('Asset changed during copy; discard isolated copy')
        assets.append({'path':n,'sha256':before})
        child_entries.append({'path':'P/Content/'+n,'bytes':target.stat().st_size,'sha256':before})
    marker={'schema':1,'purpose':'isolated-blueprint-validation-only','sourceStageManifestSha256':expected,
            'project':str((dest/'P/Receiver04Compile.uproject').resolve()),'assets':assets}
    raw=(json.dumps(marker,indent=2)+'\n').encode()
    with (dest/'blueprint-copy.json').open('xb') as f:f.write(raw)
    child_entries.append({'path':'blueprint-copy.json','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    raw=(json.dumps({'schema':1,'entries':child_entries},indent=2)+'\n').encode()
    with (dest/'allowlist.json').open('xb') as f:f.write(raw)
    return {'copiedAssets':len(assets),'bytes':size,'manifestSha256':hashlib.sha256(raw).hexdigest(),'nativeLaunched':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--content',type=Path,required=True);p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--expect-manifest',required=True);a=p.parse_args()
    print(json.dumps(prepare(a.content,a.destination,a.expect_manifest)))

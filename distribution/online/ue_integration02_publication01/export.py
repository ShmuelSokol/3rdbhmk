"""Offline exact Git-blob/payload export. Never runs engine, build or network."""
import argparse, hashlib, json, re, subprocess
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def clean(p):
    p=Path(p).absolute()
    for q in (p,*p.parents):
        if q.exists() and (q.is_symlink() or getattr(q.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Reparse refused')
    return p.resolve()
def relative(n):
    p=PurePosixPath(n)
    if not re.fullmatch(r'[A-Za-z0-9_./-]{1,240}',n) or p.is_absolute() or '..' in p.parts or p.as_posix()!=n:raise ValueError('Invalid path')
    return n
def git(repo,*args):
    return subprocess.run(['git','-C',str(clean(repo)),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30).stdout
def export(repo,dest,expected):
    raw=(ROOT/'publication.json').read_bytes()
    if sha(raw)!=expected:raise ValueError('Manifest mismatch')
    m=json.loads(raw);out={};seen=set()
    for e in m['entries']:
        n=relative(e['path'])
        if n.casefold() in seen or n=='allowlist.json':raise ValueError('Duplicate/reserved path')
        seen.add(n.casefold())
        if 'blob' in e:
            if not re.fullmatch('[a-f0-9]{40}',e['blob']):raise ValueError('Invalid blob')
            # Prove both exact content and the dependency's path in pinned commit.
            oid=git(repo,'rev-parse',m['gitCommit']+':'+relative(e['gitPath'])).decode().strip()
            if oid!=e['blob']:raise ValueError('Git dependency mismatch')
            b=git(repo,'cat-file','blob',e['blob'])
        else:b=clean(ROOT/'payload'/relative(e['payload'])).read_bytes()
        if len(b)!=e['bytes'] or sha(b)!=e['sha256']:raise ValueError('Content mismatch: '+n)
        out[n]=b
    dest=clean(dest)
    if dest.exists():raise ValueError('Fresh export only')
    dest.mkdir(parents=False)
    for n,b in out.items():
        p=dest/n;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(b)
    allow={'schema':1,'entries':[{k:e[k] for k in ('path','bytes','sha256')} for e in m['entries']]}
    raw=(json.dumps(allow,indent=2)+'\n').encode()
    with (dest/'allowlist.json').open('xb') as f:f.write(raw)
    for n,b in out.items():
        if (dest/n).read_bytes()!=b:raise ValueError('Export readback mismatch')
    actual={p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file()}
    if actual!=set(out)|{'allowlist.json'}:raise ValueError('Unexpected exported files')
    return {'status':'exact-source-export','files':len(out)+1,'manifestSha256':sha(raw),'nativeExecuted':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=Path);p.add_argument('--destination',required=True,type=Path);p.add_argument('--manifest',required=True)
    a=p.parse_args();print(json.dumps(export(a.repo,a.destination,a.manifest)))

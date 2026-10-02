"""Build a fresh minimal offline Git object store for exact publication replay.

Copies only existing commit/tree/blob objects required for manifest path proofs.
No new commit, refs, remotes, credentials, alternates, network or worktree edits.
The result is a deliberately partial object store, not a full repository clone.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
def git(repo,*args,data=None):
    return subprocess.run(['git','-C',str(repo),*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=30).stdout
def copy(repo,manifest,dest):
    if dest.exists():raise ValueError('Fresh object store required')
    m=json.loads(manifest.read_text());objects={};trees={}
    def read(kind,h):
        if h not in objects:
            b=git(repo,'cat-file',kind,h)
            if hashlib.sha1(kind.encode()+b' '+str(len(b)).encode()+b'\0'+b).hexdigest()!=h:raise ValueError('Object mismatch')
            objects[h]=(kind,b)
        return objects[h][1]
    for e in m['entries']:
        if 'blob' not in e:continue
        c=e.get('commit',m['gitCommit']);b=read('commit',c)
        tree=b.splitlines()[0].split(b' ')[1].decode()
        parts=e['gitPath'].split('/')
        for i,part in enumerate(parts):
            read('tree',tree)
            if tree not in trees:
                entries=git(repo,'ls-tree',tree).decode().splitlines()
                trees[tree]={line.split('\t',1)[1]:line.split('\t',1)[0].split()[2] for line in entries}
            found=trees[tree][part]
            if i==len(parts)-1:
                if found!=e['blob']:raise ValueError('Path mismatch')
                read('blob',found)
            else:tree=found
    if sum(len(b) for _,b in objects.values())>64*1024**2:raise ValueError('Replay object byte cap')
    subprocess.run(['git','init','--bare',str(dest)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    for h,(kind,b) in objects.items():
        if git(dest,'hash-object','-w','-t',kind,'--stdin',data=b).decode().strip()!=h:raise ValueError('Copy mismatch')
    return {'existingObjectsCopied':len(objects),'bytes':sum(len(b) for _,b in objects.values()),'newCommitCreated':False,'remoteConfigured':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=Path);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();print(json.dumps(copy(a.repo,a.manifest,a.output)))

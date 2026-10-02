"""Materialize exact published Git-blob prerequisites in a fresh offline root.
Run with -I -B. No active author tree, native compiler, UE or network required.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_portable import path,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--expect-manifest',required=True)
    a=p.parse_args();repo=a.repository.resolve();out=a.output.absolute();source=Path(__file__).resolve().parent.parent
    for parent in (out,*out.parents):
        if parent.exists() and (parent.is_symlink() or getattr(parent.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Reparse destination refused')
    if out.exists() or out.resolve().is_relative_to(repo) or out.resolve().is_relative_to(source):raise ValueError('Fresh separate replay root required')
    raw=(source/'settings_publication02/allowlist.json').read_bytes()
    if sha(raw)!=a.expect_manifest:raise ValueError('Manifest differs')
    m=json.loads(raw);content={}
    for x in m['files']:
        b=path(source,x['path']).read_bytes()
        if sha(b)!=x['sha256']:raise ValueError('Source payload differs')
        content[x['path']]=b
    for x in m['dependencies']:
        oid=subprocess.check_output(['git','-C',str(repo),'rev-parse',m['dependency_commit']+':'+x['repository_path']]).decode().strip()
        if oid!=x['git_blob_oid']:raise ValueError('Committed prerequisite differs')
        b=subprocess.check_output(['git','-C',str(repo),'cat-file','blob',oid])
        if sha(b)!=x['git_blob_sha256']:raise ValueError('Blob differs')
        if x['path'] in content:raise ValueError('Dependency overwrites payload')
        content[x['path']]=b
    content['settings_publication02/allowlist.json']=raw
    out.mkdir(parents=True,exist_ok=False)
    for n,b in content.items():
        f=path(out,n);f.parent.mkdir(parents=True,exist_ok=True)
        with f.open('xb') as h:h.write(b)
    subprocess.run([sys.executable,'-I','-B',str(out/'settings_publication02/verify_portable.py'),
                    '--root',str(out),'--expect-manifest',a.expect_manifest],check=True)
if __name__=='__main__':main()

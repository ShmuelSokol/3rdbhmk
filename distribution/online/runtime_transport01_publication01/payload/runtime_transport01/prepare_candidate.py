"""Prepare one portable source overlay, with exact published Git dependencies.

Writes only a fresh candidate directory. No staging/commit/build/engine/network.
Private composed source is compared against the private integration02 base;
unchanged files use the published portable baseline instead of local path payloads.
"""
import argparse,ast,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE_PREFIX='distribution/online/ue_integration02_publication01/'
COMMIT='8d804acb4b2525f482c33e325916fe25623faa63'
PRIVATE_BASE='4517e4008c9392082752f996fc7825b4bc89ba7f0a07c94b242da890abaf485e'
def sha(b):return hashlib.sha256(b).hexdigest()
def oid(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def git(repo,*args):return subprocess.run(['git','-C',str(repo),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30).stdout
def stage_files(root,expected=None):
    raw=(root/'allowlist.json').read_bytes()
    if expected and sha(raw)!=expected:raise ValueError('Frozen input changed')
    out={}
    for e in json.loads(raw)['entries']:
        b=(root/e['path']).read_bytes()
        if sha(b)!=e['sha256'] or len(b)!=e['bytes']:raise ValueError('Stage changed')
        out[e['path']]=b
    return out
def prepare(repo,stage,private_base,dest):
    if dest.exists():raise ValueError('Fresh candidate required')
    original=stage_files(private_base,PRIVATE_BASE);current=stage_files(stage)
    baseline=json.loads(git(repo,'show',COMMIT+':'+BASE_PREFIX+'publication.json'))
    out={};origins={}
    for e in baseline['entries']:
        if 'blob' in e:
            c=baseline['gitCommit'];path=e['gitPath'];b=git(repo,'cat-file','blob',e['blob'])
        else:
            c=COMMIT;path=BASE_PREFIX+'payload/'+e['payload'];b=git(repo,'show',c+':'+path)
        if sha(b)!=e['sha256']:raise ValueError('Published base changed')
        out[e['path']]=b;origins[e['path']]=(c,path,oid(b))
    for n,b in current.items():
        if n in original and original[n]==b and n in out:continue
        out[n]=b;origins.pop(n,None)
    # Current author source and checks; preserve earlier review receipt separately.
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or 'publication' in p.relative_to(ROOT).parts or '__pycache__' in p.parts or p.name in ('allowlist01.json','review-request.json'):continue
        if p.suffix not in ('.py','.mjs','.h','.cpp','.json','.inc','.md','.html','.css'):continue
        n='runtime_transport01/'+p.relative_to(ROOT).as_posix();out[n]=p.read_bytes();origins.pop(n,None)
    out['README.md']=(ROOT/'README.md').read_bytes();origins.pop('README.md',None)
    # Published namespace dependencies, recursively discovered from real imports.
    listing=git(repo,'ls-tree','-r','--format=%(objectname) %(path)',COMMIT,'distribution/online').decode().splitlines()
    tree={line.split(' ',1)[1]:line.split(' ',1)[0] for line in listing}
    available={p[len('distribution/online/'):]:h for p,h in tree.items()}
    scanned=set()
    def add(n):
        if n in out:return
        h=available.get(n)
        if not h:raise ValueError('Missing published dependency: '+n)
        out[n]=git(repo,'cat-file','blob',h);origins[n]=(COMMIT,'distribution/online/'+n,h)
    for _ in range(20):
        pending=[n for n in out if n.endswith('.py') and n not in scanned]
        if not pending:break
        for n in pending:
            scanned.add(n)
            for node in ast.walk(ast.parse(out[n].decode('utf-8-sig'))):
                names=[]
                if isinstance(node,ast.Import):names=[v.name for v in node.names]
                elif isinstance(node,ast.ImportFrom) and not node.level and node.module:
                    names=[node.module]+[node.module+'.'+v.name for v in node.names]
                for name in names:
                    dep=name.replace('.','/')+'.py'
                    if dep in available:add(dep)
    else:raise ValueError('Dependency recursion bound')
    # The real settings03 Win32 predicate loader consumes its exact historical
    # manifest (already published as evidence), plus the actual unchanged code.
    path='distribution/online/settings_publication01/evidence/frozen02-manifest.json'
    b=git(repo,'show',COMMIT+':'+path)
    if sha(b)!='c42a8257ee837aa7c458e5c40ed0e26ef28075c3ccd90764a9a8fe4b6814ba3b':raise ValueError('Settings02 predicate manifest changed')
    out['runtime_settings02/manifest.json']=b;origins['runtime_settings02/manifest.json']=(COMMIT,path,oid(b))
    add('runtime_settings02/win32_predicate.py')
    for n in ['session_core.py','upstream-lock.json']:add(n)
    # Keep prior independent/single-header evidence as explicitly historical.
    for folder in ['runtime_readiness01','runtime_adoption01','runtime_flight01']:
        p=ROOT.parent/folder/'receipt01.json'
        out['history/'+folder+'-receipt01.json']=p.read_bytes()
    # Superset of runtime Python dependency pins, rooted at this export. No
    # runtime settings algorithm is changed and no missing lease is synthesized.
    pins={n:sha(b) for n,b in sorted(out.items()) if n.endswith('.py') and
        n!='runtime_transport01/integrity.py' and (n.startswith(('runtime_','adapters/')) or n=='session_core.py')}
    pins['runtime_settings02/manifest.json']=sha(out['runtime_settings02/manifest.json'])
    raw=(json.dumps(pins,indent=2)+'\n').encode();out['runtime_transport01/host-pins.json']=raw
    name='runtime_transport01/integrity.py'
    out[name]=out[name].replace(b'EXPECTED = None',('EXPECTED = '+repr(sha(raw))).encode())
    # Reject new private path payloads. Existing exact published baseline objects
    # remain attributed to their original Git blobs and historical scope.
    for n,b in out.items():
        if n in origins:continue
        if re.search(rb'C:[/\\]+(?:Mikdash|Users)',b,re.I):raise ValueError('Private path in additive payload: '+n)
        if n.endswith(('.exe','.dll','.lib','.obj','.pdb','.log')):raise ValueError('Binary/log refused')
    dest.mkdir();entries=[]
    by_oid={h:p for p,h in tree.items()}
    for n,b in sorted(out.items()):
        entry={'path':n,'bytes':len(b),'sha256':sha(b)}
        origin=origins.get(n)
        if not origin and oid(b) in by_oid:origin=(COMMIT,by_oid[oid(b)],oid(b))
        if origin:
            c,path,h=origin;entry.update(commit=c,gitPath=path,blob=h)
        else:
            entry['payload']=n;p=dest/'payload'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        entries.append(entry)
    export=git(repo,'show',COMMIT+':'+BASE_PREFIX+'export.py').decode()
    export=export.replace("m['gitCommit']+':'+relative(e['gitPath'])", "e.get('commit',m['gitCommit'])+':'+relative(e['gitPath'])")
    (dest/'export.py').write_bytes(export.encode('utf-8'))
    manifest={'schema':1,'gitCommit':COMMIT,'scope':'Local authenticated transport source, UE/media unexecuted','entries':entries}
    raw=(json.dumps(manifest,indent=2)+'\n').encode();(dest/'publication.json').write_bytes(raw)
    return {'files':len(entries),'gitDependencies':sum('blob' in e for e in entries),'payload':sum('payload' in e for e in entries),'manifestSha256':sha(raw)}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True,type=Path);p.add_argument('--stage',required=True,type=Path);p.add_argument('--private-base',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.repo,a.stage,a.private_base,a.output)))

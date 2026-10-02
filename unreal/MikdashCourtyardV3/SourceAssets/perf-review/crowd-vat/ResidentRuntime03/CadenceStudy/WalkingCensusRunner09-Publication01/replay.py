"""Offline publication replay. Only explicit Git objects and capsule files are read.
Never calls the native launcher, local09 verifier, a compiler or an engine.
"""
import argparse, hashlib, json, os, re, shutil, stat, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXTENSIONS={'.py','.ps1','.cs','.cpp','.h','.json','.txt','.patch','.uproject'}
def need(ok,message):
    if not ok:raise ValueError(message)
def digest(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def safe(root,name):
    need(isinstance(name,str) and name and not name.startswith('/') and '\\' not in name and ':' not in name,'unsafe relative path')
    need(all(x not in ('','.','..') for x in name.split('/')),'path escape')
    p=Path(root)/name
    for q in (p,*p.parents):
        if q.exists():need(not q.is_symlink() and not(getattr(q.lstat(),'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024)),'reparse path')
    return p
def git(repo,*args):
    env=os.environ.copy();env['GIT_NO_LAZY_FETCH']='1';env['GIT_TERMINAL_PROMPT']='0'
    return subprocess.check_output(['git','--no-replace-objects','-C',str(repo),*args],env=env,stderr=subprocess.PIPE,timeout=30)
def blob(repo,e):
    need(re.fullmatch('[0-9a-f]{40}',e['commit']) and re.fullmatch('[0-9a-f]{40}',e['blob']),'Git pin format')
    safe(ROOT,e['path'])
    oid=git(repo,'rev-parse',e['commit']+':'+e['path']).decode().strip()
    need(oid==e['blob'],'commit/path/blob mismatch')
    data=git(repo,'cat-file','blob',oid);need(digest(data)==e['sha256'],'public blob SHA256 mismatch')
    return data
def audit():
    m=read(ROOT/'manifest.json');actual=set()
    for p in ROOT.rglob('*'):
        n=p.relative_to(ROOT).as_posix();safe(ROOT,n)
        if not p.is_file():continue
        actual.add(n)
        need(p.suffix in EXTENSIONS,'forbidden extension: '+n)
        need(not any(x.lower() in {'engine','vendor','thirdparty','binaries','saved','ddc','__pycache__','node_modules','runs'} for x in p.relative_to(ROOT).parts),'forbidden directory: '+n)
        need(p.stat().st_size<2*1024*1024,'unexpected large payload')
        need(not p.read_bytes().startswith(b'MZ'),'binary executable disguised as source')
    need(actual==set(m['files'])|{'manifest.json'},'explicit allowlist mismatch')
    for n,h in m['files'].items():need(digest(safe(ROOT,n).read_bytes())==h,'capsule pin changed: '+n)
    c=read(ROOT/'closure.json');original=read(ROOT/'evidence/frozen09-manifest.json')
    need(digest((ROOT/'evidence/frozen09-manifest.json').read_bytes())==c['frozenManifestSha256'],'frozen manifest changed')
    need(set(c['files'])==set(original['files']),'incomplete author closure')
    for n,e in c['files'].items():
        need(e.get('frozenSha256',e['sha256'])==original['files'][n],'frozen source correspondence')
        if n not in c['sanitizedFiles']:need(e['sha256']==original['files'][n],'unlisted transformation')
    return m,c
def replay(repo,output,pwsh):
    m,c=audit();out=Path(output).absolute();need(not out.exists(),'fresh output required')
    # Resolve ALL public references first, with lazy network fetching disabled.
    material={}
    for n,e in c['files'].items():
        if e['kind']=='git':material[n]=blob(repo,e)
        elif e['kind']=='file':material[n]=safe(ROOT,e['path']).read_bytes()
        else:need(e['kind']=='alias','unknown closure kind')
    for n,e in c['files'].items():
        if e['kind']=='alias':material[n]=material[e['target']]
        need(digest(material[n])==e['sha256'],'materialized author mismatch')
    native=read(ROOT/'native-prerequisites.json');transforms=0
    frozen_inputs=json.loads(material['inputs.json'])
    need(set(native['publicProjectSourcePins'])==set(frozen_inputs['pluginFiles']),'native source allowlist mismatch')
    need(native['assetPins']==frozen_inputs['packages'] and native['nativeEligibility']=='HOLD','native prerequisites drift')
    for n,e in native['publicProjectSourcePins'].items():
        data=blob(repo,e)
        if e.get('transform')=='lf-to-crlf':data=data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n');transforms+=1
        else:need(e.get('transform','identity')=='identity','unknown byte transform')
        need(digest(data)==e.get('materializedSha256',e['sha256']),'native declared-source reconstruction')
        need(digest(data)==frozen_inputs['pluginFiles'][n]['sha256'],'native source differs from frozen09')
    need(not native['unpublishedOrDifferentProjectSources'],'unpublished native source dependency: native HOLD')
    out.mkdir(parents=True);source=out/'source';source.mkdir()
    for n,data in material.items():
        p=safe(source,n);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(data)
    # Reviewed tests import runner definitions only. Local native verifier is NEVER called.
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    a=subprocess.run([sys.executable,'-B',str(source/'test_runner.py')],cwd=source,env=env,capture_output=True,text=True,timeout=60)
    (out/'python-local.txt').write_text(a.stdout+a.stderr,encoding='utf-8')
    need(a.returncode==0 and 'Ran 23 tests' in a.stderr,'reviewed Python tests failed')
    ps=pwsh or shutil.which('pwsh');need(ps,'PowerShell7 prerequisite absent: policy replay HOLD')
    b=subprocess.run([ps,'-NoProfile','-File',str(source/'test_policy.ps1')],cwd=source,env=env,capture_output=True,text=True,timeout=60)
    (out/'policy-local.txt').write_text(b.stdout+b.stderr,encoding='utf-8')
    need(b.returncode==0,'reviewed PowerShell policy tests failed')
    policy=json.loads(b.stdout);need(policy['checks']==25 and policy['failures']==0 and policy['processesLaunched']==0,'policy evidence mismatch')
    for n,e in c['files'].items():need(digest((source/n).read_bytes())==e['sha256'],'test mutated author source')
    result={'status':'offline_publication_replay_pass','manifestSha256':digest((ROOT/'manifest.json').read_bytes()),
      'frozen09Manifest':c['frozenManifestSha256'],'publicCommit':c['publicCommit'],'pythonTests':23,'policyChecks':25,
      'authorFiles':len(material),'publicAuthorDependencies':3,'publicNativeSourcePinsChecked':len(native['publicProjectSourcePins']),
      'explicitCRLFReconstructions':transforms,'forbiddenFileAudit':'pass','networkDuringReplay':False,
      'activeProjectInputsRead':False,'UEExecuted':False,'compilerExecuted':False,'nativeEligibility':'HOLD','worldReady':False}
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--output',required=True);p.add_argument('--pwsh');a=p.parse_args()
    replay(Path(a.repo),a.output,a.pwsh)

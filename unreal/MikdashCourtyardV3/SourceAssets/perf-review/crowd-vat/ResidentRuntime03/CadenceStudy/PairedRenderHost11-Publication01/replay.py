"""Portable source-only closure replay. Never executes UE, UBT or native proposal."""
import argparse,hashlib,json,os,re,shutil,subprocess,sys,tempfile,gzip
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sha=lambda data:hashlib.sha256(data).hexdigest()
def need(ok,why):
 if not ok:raise RuntimeError(why)
def safe(root,name):
 need(isinstance(name,str) and name and ':' not in name and '\\' not in name and not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe relative path')
 p=root/name
 for q in [root,*list(p.relative_to(root).parents)[:-1]]:
  q=q if q==root else root/q
  if q.exists():need(not q.is_symlink() and not(getattr(q.lstat(),'st_file_attributes',0)&0x400),'reparse directory')
 if p.exists():need(not p.is_symlink() and not(getattr(p.lstat(),'st_file_attributes',0)&0x400),'reparse file')
 return p

def metadata_paths(value,key=''):
 # Inspect decoded JSON values, not prose/code/URLs or Unreal package references.
 # Drive-rooted, UNC and file URI values are host-specific in every field.
 # POSIX roots are rejected in explicitly filesystem-valued fields only.
 host_fields={'projectdir','receiptfolder','locallog','outputdir','workdir','cwd','homedir','temppath'}
 if isinstance(value,dict):
  for k,v in value.items():metadata_paths(v,k)
 elif isinstance(value,list):
  for v in value:metadata_paths(v,key)
 elif isinstance(value,str):
  windows=bool(re.match(r'^[A-Za-z]:[\\/]',value)) or value.startswith(('\\\\','//'))
  host_uri=value.lower().startswith('file:')
  posix=key.lower() in host_fields and value.startswith('/')
  need(not (windows or host_uri or posix),'absolute host path in metadata field '+key)

def git(repo,*args,input=None):
 env=os.environ.copy();env['GIT_NO_LAZY_FETCH']='1';env['GIT_NO_REPLACE_OBJECTS']='1'
 return subprocess.check_output(['git','-C',str(repo),*args],input=input,stderr=subprocess.PIPE,env=env,timeout=60)
def dependency(repo,row):
 entry=git(repo,'ls-tree',row['commit'],'--',row['path']).decode().strip()
 need(entry=='100644 blob '+row['blob']+'\t'+row['path'],'public Git path/blob mismatch')
 data=git(repo,'cat-file','blob',row['blob']);need(sha(data)==row['sha256'],'public Git bytes mismatch');return data


def audit(root=ROOT):
 m=json.loads((root/'publication-manifest.json').read_text());c=json.loads((root/'closure.json').read_text())
 actual={str(f.relative_to(root)).replace('\\','/') for f in root.rglob('*') if f.is_file()}
 need(actual==set(m['files'])|{'publication-manifest.json'},'unlisted/missing publication file')
 for n,h in m['files'].items():
  f=safe(root,n);need(sha(f.read_bytes())==h,'publication hash '+n)
  need(f.suffix.lower() in ['.py','.cpp','.h','.cs','.json','.uplugin','.txt'] or n=='.gitattributes','binary/non-author file '+n)
  text=f.read_text(encoding='utf-8')
  if f.suffix.lower() in ['.json','.uplugin']:metadata_paths(json.loads(text))
  need(not re.search(r'[A-Za-z]:[\\/]+Users[\\/]',text,re.I),'private machine path '+n)
 need((root/'.gitattributes').read_bytes()==b'* -text\n','exact-byte attributes required')
 expected={}
 for label,origin in c['origins'].items():
  f=safe(root,origin['manifestPath']);need(sha(f.read_bytes())==origin['manifestSha256'],'origin manifest hash')
  original=json.loads(f.read_text());need(len(original['files'])==origin['payloadCount'],'origin count')
  expected.update({label+'/'+n:h for n,h in original['files'].items()});expected[label+'/manifest.json']=origin['manifestSha256']
 need(set(expected)==set(c['files']),'incomplete original source accounting')
 for name,row in c['files'].items():
  safe(root,name);need(row['sha256']==expected[name],'original hash mismatch '+name)
  if row['kind']=='file':need(sha(safe(root,row['path']).read_bytes())==row['sha256'],'export bytes mismatch')
  else:need(row['kind']=='git' and row['mode']=='100644' and row['commit']==c['publicCommit'],'invalid Git prerequisite')
 return m,c

def execute(root,repo,output,vcvars):
 m,c=audit(root);o=Path(output).absolute();need(not o.exists(),'fresh output required');o.mkdir(parents=True);work=o/'reconstructed';work.mkdir()
 for name,row in c['files'].items():
  f=safe(work,name);f.parent.mkdir(parents=True,exist_ok=True)
  data=dependency(repo,row) if row['kind']=='git' else safe(root,row['path']).read_bytes()
  need(sha(data)==row['sha256'],'reconstructed bytes mismatch');f.write_bytes(data)
 before={str(f.relative_to(work)):sha(f.read_bytes()) for f in work.rglob('*') if f.is_file()}
 # Original portable author runner, unchanged. It builds ONLY ProtocolTest.cpp;
 # UE-facing sources are examined as TEXT by the original structural test.
 r=subprocess.run([sys.executable,'-B',str(work/'Host11/replay.py'),'--output',str(o/'standalone'),'--vcvars',vcvars],cwd=work/'Host11',capture_output=True,timeout=120)
 (o/'replay-local.log').write_bytes(r.stdout+r.stderr);need(r.returncode==0,'original offline replay failed')
 actual=json.loads((o/'standalone/receipt.json').read_text());expected=json.loads((work/'Host11/offline-receipt.json').read_text())
 need(actual==expected,'original offline receipt differs')
 need(actual['sourceChecks']==43 and '1751 protocol checks, 0 failures' in actual['protocol'],'required offline counts')
 after={str(f.relative_to(work)):sha(f.read_bytes()) for f in work.rglob('*') if f.is_file()};need(after==before,'reconstructed source mutated');audit(root)
 result={'status':'AUTHOR_CLOSURE_REPLAY_PASS_NATIVE_HOLD','publicationManifestSha256':sha((root/'publication-manifest.json').read_bytes()),'publicationFilesIncludingManifest':len(m['files'])+1,'publicCommit':c['publicCommit'],'gitDependencyBlobs':len({row['blob'] for row in c['files'].values() if row['kind']=='git'}),'reconstructedOriginalFilesIncludingManifests':len(c['files']),'host11ProtocolChecks':1751,'host11StructuralChecks':43,'failures':0,'exactOriginalOfflineReceipt':True,'bothOriginalSourceTreesUnchanged':True,'host10ReplayExecuted':False,'host10Disposition':'Preserved rejected predecessor, not acceptance','installedApiSourceAuditExecuted':False,'ueFacingModuleCompiled':False,'renderExecutionProved':False,'nativeChecksExecuted':0,'rawLogsExported':0,'binaryFilesExported':0,'vendorImplementationExported':False,'metadataPrivacyAudit':'decoded JSON drive/UNC/file URI and host-field POSIX roots; URLs and Unreal package refs unchanged'}
 (o/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
 a=argparse.ArgumentParser();a.add_argument('--repo');a.add_argument('--output');a.add_argument('--vcvars');a.add_argument('--check-only',action='store_true');x=a.parse_args()
 if x.check_only:m,c=audit();print(json.dumps({'publicationFiles':len(m['files'])+1,'originalFiles':len(c['files']),'nativeChecksExecuted':0}));return
 need(all([x.repo,x.output,x.vcvars]),'supply --repo --output --vcvars');print(json.dumps(execute(ROOT,x.repo,x.output,x.vcvars)))
if __name__=='__main__':main()

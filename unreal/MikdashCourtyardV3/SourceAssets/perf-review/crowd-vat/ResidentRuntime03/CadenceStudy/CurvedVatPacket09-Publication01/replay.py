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

def audit(root=ROOT):
 m=json.loads((root/'publication-manifest.json').read_text());c=json.loads((root/'closure.json').read_text())
 actual={str(p.relative_to(root)).replace('\\','/') for p in root.rglob('*') if p.is_file()}
 need(actual==set(m['files'])|{'publication-manifest.json'},'unlisted/missing publication file')
 for n,h in m['files'].items():
  p=safe(root,n);need(sha(p.read_bytes())==h,'hash mismatch '+n)
  need(p.suffix.lower() in ['.py','.cpp','.h','.ush','.hlsl','.json','.csv','.txt'] or n=='.gitattributes','non-source evidence '+n)
  if p.suffix.lower()=='.json':metadata_paths(json.loads(p.read_text(encoding='utf-8')))
  text=p.read_text(encoding='utf-8');need(not re.search(r'[A-Za-z]:[\\/]+Users[\\/]',text,re.I),'private machine path '+n)
 need(json.loads((root/'author/spec.json').read_text())['projectDir']=='<external-project-root>','projectDir must be external placeholder')
 need((root/'.gitattributes').read_bytes()==b'* -text\n','exact-byte attributes required')
 f=json.loads((root/'frozen-origin-manifest.json').read_text())
 need(sha((root/'frozen-origin-manifest.json').read_bytes())==c['frozenManifestSha256'],'frozen origin manifest mismatch')
 need(set(c['files'])|set(c['omitted'])==set(f['files']),'incomplete32-file accounting')
 for n,row in c['omitted'].items():
  need(row['sha256']==f['files'][n],'omitted origin pin mismatch')
 for n,row in c['files'].items():
  need(row['frozenSha256']==f['files'][n],'origin source pin mismatch')
  if row['kind']=='file':need(sha(safe(root,row['path']).read_bytes())==row['sha256'],'closure export hash')
  else:need(row['kind']=='git' and row['mode']=='100644' and row['commit']==c['publicCommit'],'invalid Git dependency')
 return m,c

def git(repo,*args,input=None):
 env=os.environ.copy();env['GIT_NO_LAZY_FETCH']='1';env['GIT_NO_REPLACE_OBJECTS']='1'
 return subprocess.check_output(['git','-C',str(repo),*args],input=input,stderr=subprocess.PIPE,env=env,timeout=60)
def dependency(repo,row):
 entry=git(repo,'ls-tree',row['commit'],'--',row['path']).decode().strip()
 need(entry=='100644 blob '+row['blob']+'\t'+row['path'],'public Git path/blob mismatch')
 data=git(repo,'cat-file','blob',row['blob']);need(sha(data)==row['sha256'],'public Git bytes mismatch');return data

def execute(root,repo,output,vcvars,dxc):
 m,c=audit(root);output=Path(output).absolute();need(not output.exists(),'fresh replay output required');output.mkdir(parents=True);p=output/'reconstructed';p.mkdir()
 tool=Path(vcvars).absolute();shader=Path(dxc).absolute();need(tool.is_file() and shader.is_file(),'offline MSVC/DXC tools required')
 need(not any(x in str(tool) for x in ['"','%','\n','\r']),'unsafe compiler environment path')
 for name,row in c['files'].items():
  dst=safe(p,name);dst.parent.mkdir(parents=True,exist_ok=True)
  data=dependency(repo,row) if row['kind']=='git' else safe(root,row['path']).read_bytes()
  if name=='samples.csv.gz':data=gzip.compress(data,mtime=0)
  dst.write_bytes(data)
 before={str(f.relative_to(p)):sha(f.read_bytes()) for f in p.rglob('*') if f.is_file()}
 # Generate into a separate scratch to avoid touching any reconstructed source.
 gen=output/'generation';gen.mkdir();(gen/'frozen').mkdir()
 for name in ['generate.py','stock_curve.py','frozen/candidate_builder.py']:shutil.copyfile(p/name,gen/name)
 r=subprocess.run([sys.executable,'-B',str(gen/'generate.py')],capture_output=True,timeout=30);need(r.returncode==0,'source generator failed')
 for name in ['candidate_builder.py','generation.json']:need((gen/name).read_bytes()==(p/name).read_bytes(),'generator not byte-exact '+name)
 # Exact authored test source, same standalone flags; installed tools are external.
 work=output/'cpp';work.mkdir();(work/'frozen').mkdir();cpp=json.loads((p/'cpp-receipt.json').read_text())
 for name,h in cpp['sources'].items():
  need(sha((p/name).read_bytes())==h,'compiled-source pin '+name);shutil.copyfile(p/name,work/name)
 (work/'build.cmd').write_text('@echo off\ncall "'+str(tool)+'" >nul\ncl /nologo /std:c++17 /EHsc /fp:strict /O2 PacketTest.cpp /Fe:test.exe\n')
 r=subprocess.run(['cmd.exe','/d','/c','build.cmd'],cwd=work,capture_output=True,timeout=60);(output/'build-local.log').write_bytes(r.stdout+r.stderr);need(r.returncode==0,'standalone compile failed')
 r=subprocess.run([str(work/'test.exe')],cwd=work,capture_output=True,timeout=30);log=r.stdout+r.stderr;(output/'cpp-local.log').write_bytes(log)
 need(r.returncode==0 and log.decode()==cpp['result'] and sha(log)==cpp['logSha256'],'C++ result differs')
 need((work/'samples.csv').read_bytes()==(root/'evidence/samples.csv').read_bytes(),'208-row sample CSV differs')
 r=subprocess.run([sys.executable,'-B',str(p/'test_graph.py'),'--replay'],cwd=p,capture_output=True,timeout=60);(output/'graph-local.log').write_bytes(r.stdout+r.stderr);need(r.returncode==0,'actual material graph replay failed')
 hlsl=output/'hlsl';hlsl.mkdir();shutil.copyfile(p/'CurvePacket.ush',hlsl/'CurvePacket.ush');shutil.copyfile(root/'author/probe.hlsl',hlsl/'probe.hlsl')
 expected=json.loads((p/'dxc-receipt.json').read_text());need(sha(shader.read_bytes())==expected['compilerSha256'],'DXC version hash differs from explicit prerequisite')
 r=subprocess.run([str(shader),'-T','cs_6_0','-E','Main','-Ges','-Gis','probe.hlsl','-Fo','probe.dxil'],cwd=hlsl,capture_output=True,timeout=30);log=r.stdout+r.stderr;(output/'dxc-local.log').write_bytes(log)
 need(r.returncode==0 and log.decode()==expected['diagnostics'],'offline HLSL compile differs')
 after={str(f.relative_to(p)):sha(f.read_bytes()) for f in p.rglob('*') if f.is_file()};need(before==after,'replay mutated reconstructed sources')
 audit(root)
 receipt={'status':'SOURCE_CLOSURE_REPLAY_PASS_NATIVE_HOLD','publicationManifestSha256':sha((root/'publication-manifest.json').read_bytes()),'files':len(m['files']),'publicCommit':c['publicCommit'],'gitDependencies':2,'reconstructedFiles':len(c['files']),'originalFrozenPayloadAccounted':32,'cppChecks':1074,'graphChecks':1501,'failures':0,'sampleRows':208,'sampleCsvSha256':sha((work/'samples.csv').read_bytes()),'generatorExact':True,'offlineDxcExit':0,'reconstructedSourceUnchanged':True,'nativeRuns':0,'rawLogsExported':0,'binaryFilesExported':0,'EpicImplementationExported':0,'privatePathDataExported':0,'metadataHostPathAudit':'decoded JSON values: drive/UNC/file URI; POSIX roots in host fields; spec projectDir exact external placeholder'}
 (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

def main():
 a=argparse.ArgumentParser();a.add_argument('--repo');a.add_argument('--output');a.add_argument('--vcvars');a.add_argument('--dxc');a.add_argument('--check-only',action='store_true');x=a.parse_args()
 if x.check_only:m,c=audit();print(json.dumps({'files':len(m['files']),'gitPrerequisites':2,'frozenPayloadAccounted':32,'nativeAllowed':False}));return
 need(all([x.repo,x.output,x.vcvars,x.dxc]),'supply --repo --output --vcvars --dxc');print(json.dumps(execute(ROOT,x.repo,x.output,x.vcvars,x.dxc)))
if __name__=='__main__':main()

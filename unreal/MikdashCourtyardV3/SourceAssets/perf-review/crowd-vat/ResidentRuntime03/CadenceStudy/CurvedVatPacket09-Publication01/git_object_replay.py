"""Fresh detached public HEAD + author capsule tree. No new commits, no active Git writes."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import replay

def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--output',required=True);p.add_argument('--vcvars',required=True);p.add_argument('--dxc',required=True);a=p.parse_args()
 m,c=replay.audit();out=Path(a.output).absolute();replay.need(not out.exists(),'fresh output required');out.mkdir(parents=True)
 store=out/'objects.git';replay.git(out,'init','--bare',str(store));commit=c['publicCommit']
 # Import only the EXISTING public commit, path-ancestor trees and two author
 # blobs. No new commit is manufactured; no assets or engine objects are copied.
 objects={commit}
 objects.add(replay.git(a.repo,'rev-parse',commit+'^{tree}').decode().strip())
 for row in c['files'].values():
  if row['kind']!='git':continue
  replay.dependency(a.repo,row);objects.add(row['blob'])
  parts=row['path'].split('/')
  for n in range(1,len(parts)):objects.add(replay.git(a.repo,'rev-parse',commit+':'+ '/'.join(parts[:n])).decode().strip())
 for oid in sorted(objects):
  kind=replay.git(a.repo,'cat-file','-t',oid).decode().strip();data=replay.git(a.repo,'cat-file',kind,oid)
  actual=replay.git(store,'hash-object','-w','-t',kind,'--stdin',input=data).decode().strip();replay.need(actual==oid,'public object transfer mismatch')
 replay.git(store,'update-ref','--no-deref','HEAD',commit)
 detached=subprocess.run(['git','-C',str(store),'symbolic-ref','-q','HEAD'],capture_output=True);replay.need(detached.returncode==1,'HEAD is not detached')
 env=os.environ.copy();env['GIT_INDEX_FILE']=str(store/'capsule-index');env['GIT_NO_LAZY_FETCH']='1'
 records=[]
 for name in sorted([*m['files'],'publication-manifest.json']):
  data=replay.safe(replay.ROOT,name).read_bytes();oid=replay.git(store,'hash-object','-w','--stdin',input=data).decode().strip();records.append('100644 '+oid+'\t'+name+'\n')
 def private(*args,input=None):return subprocess.check_output(['git','--git-dir='+str(store),*args],input=input,env=env,stderr=subprocess.PIPE,timeout=60)
 private('update-index','--index-info',input=''.join(records).encode());tree=private('write-tree').decode().strip()
 export=out/'export';export.mkdir();private('--work-tree='+str(export),'-c','core.autocrlf=true','checkout-index','--all','--prefix='+str(export).replace('\\','/')+'/')
 replay.audit(export)
 r=subprocess.run([sys.executable,'-B',str(export/'test_publication.py')],cwd=export,capture_output=True,timeout=60);(out/'fault-tests-local.log').write_bytes(r.stdout+r.stderr);replay.need(r.returncode==0,'publication fault tests failed')
 r=subprocess.run([sys.executable,'-B',str(export/'replay.py'),'--repo',str(store),'--output',str(out/'replay'),'--vcvars',a.vcvars,'--dxc',a.dxc],cwd=export,capture_output=True,timeout=180);(out/'replay-local.log').write_bytes(r.stdout+r.stderr);replay.need(r.returncode==0,'detached reconstruction replay failed; inspect local logs')
 result=json.loads((out/'replay/receipt.json').read_text());result.update(detachedHead=commit,capsuleTree=tree,newCommits=0,activeTreeOrIndexWrites=0,importedExistingPublicObjects=len(objects),gitExportedFiles=len(records),publicationFaultTests=9)
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()

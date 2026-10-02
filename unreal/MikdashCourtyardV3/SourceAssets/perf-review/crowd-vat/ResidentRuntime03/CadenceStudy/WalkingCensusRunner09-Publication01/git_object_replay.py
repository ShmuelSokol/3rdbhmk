"""Export capsule via an isolated Git tree and replay it. Writes NO commit/ref."""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
import replay

def run(args,**kwargs):return subprocess.check_output(args,stderr=subprocess.PIPE,timeout=120,**kwargs)
def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--output',required=True);p.add_argument('--pwsh',required=True);a=p.parse_args()
    m,c=replay.audit();out=Path(a.output).absolute();replay.need(not out.exists(),'fresh Git replay output required');out.mkdir(parents=True)
    store=out/'capsule.git';run(['git','init','--bare',str(store)])
    env=os.environ.copy();env['GIT_INDEX_FILE']=str(store/'private-index')
    rows=[]
    for name in sorted([*m['files'],'manifest.json']):
        data=replay.safe(replay.ROOT,name).read_bytes()
        oid=run(['git','-C',str(store),'hash-object','-w','--stdin'],input=data).decode().strip()
        rows.append('100644 '+oid+'\t'+name+'\n')
    run(['git','-C',str(store),'update-index','--index-info'],input=''.join(rows).encode(),env=env)
    tree=run(['git','-C',str(store),'write-tree'],env=env).decode().strip()
    export=out/'export';export.mkdir();count=0
    for row in run(['git','-C',str(store),'ls-tree','-rz',tree]).split(b'\0'):
        if not row:continue
        meta,name=row.split(b'\t',1);mode,kind,oid=meta.decode().split();replay.need(mode=='100644' and kind=='blob','unexpected Git object')
        target=replay.safe(export,name.decode());target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(run(['git','-C',str(store),'cat-file','blob',oid]));count+=1
    fault=subprocess.run([sys.executable,'-B',str(export/'test_publication.py')],cwd=export,capture_output=True,text=True,timeout=60)
    (out/'publication-tests-local.txt').write_text(fault.stdout+fault.stderr,encoding='utf-8')
    replay.need(fault.returncode==0 and 'Ran 4 tests' in fault.stderr,'publication fault tests failed')
    result=subprocess.run([sys.executable,'-B',str(export/'replay.py'),'--repo',str(Path(a.repo).absolute()),'--output',str(out/'replay'),'--pwsh',a.pwsh],cwd=export,capture_output=True,text=True,timeout=120)
    (out/'replay-local.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    replay.need(result.returncode==0,'fresh Git object export replay failed; see local result')
    receipt=json.loads((out/'replay/receipt.json').read_text())
    receipt.update(capsuleGitTree=tree,gitExportedFiles=count,publicationFaultTests=4,commitsCreated=0,refsCreated=0)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt))
if __name__=='__main__':main()

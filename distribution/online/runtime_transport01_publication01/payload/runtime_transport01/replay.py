"""Offline source/byte-adapter replay only; never UE or listening sockets."""
import argparse,hashlib,json,subprocess,sys,tempfile
from pathlib import Path

def run(args,timeout=30):
    r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if r.returncode:raise RuntimeError('Offline check failed: '+Path(args[0]).name)
    return r.stdout.decode('utf-8')
def replay(root,node,cache,output):
    root=root.resolve();output=output.resolve()
    if output.exists():raise ValueError('Fresh output required')
    output.mkdir();own=root/'runtime_transport01'
    counts={}
    for name,count in [('test_gateway.py',25),('test_server.py',12),('test_owned_host.py',5),('test_integrity.py',4)]:
        run([sys.executable,'-I','-B',str(own/name)]);counts[name]=count
    run([sys.executable,'-I','-B',str(own/'test_composed.py'),'--root',str(root)]);counts['composedSource']=7
    build=json.loads(run([str(node),str(own/'build.mjs'),str(cache),str(output/'browser')],60))
    flow=json.loads(run([str(node),str(own/'browser_flow.test.mjs'),str(output/'browser/app.js'),str(own/'browser_driver.py'),sys.executable],25))
    if flow.get('cases')!=7 or flow.get('testChildExit')!=0:raise ValueError('Browser flow incomplete')
    receipt={'schema':1,'offline':True,'checks':counts,'browserFlow':flow,'browserBuild':build,
        'ueCompiled':False,'listenersStarted':False,'mediaExecuted':False,
        'sourceHashes':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(own.rglob('*')) if p.is_file()}}
    raw=(json.dumps(receipt,indent=2)+'\n').encode();(output/'receipt.json').write_bytes(raw)
    return {'checks':counts,'browserCases':flow['cases'],'receiptSha256':hashlib.sha256(raw).hexdigest(),'ueExecuted':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--node',required=True,type=Path);p.add_argument('--cache',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();print(json.dumps(replay(a.root,a.node,a.cache,a.output)))

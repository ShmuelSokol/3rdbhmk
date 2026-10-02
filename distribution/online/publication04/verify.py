"""Stdlib source-only publication check/export. No native/process-host execution.

Use -I -B in a fresh Python interpreter. --copy-to requires a nonexistent target;
it copies only explicit manifest entries and never changes an existing tree.
"""
import argparse
from contextlib import ExitStack, redirect_stdout
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import runpy
import shutil
import sys
from unittest.mock import patch

RECEIPT02='2d0f82b8c0c492b4721c2e8c2d0ab1e87699d71e936fbf5ef1d34078d14c5e1f'
MANIFEST='publication04/allowlist.json'


def sha(data):return hashlib.sha256(data).hexdigest()


def pairs(items):
    out={}
    for key,value in items:
        if key in out:raise ValueError('Duplicate manifest field')
        out[key]=value
    return out


def safe_path(root, name):
    if type(name) is not str or len(name)>240 or not re.fullmatch(r'[A-Za-z0-9_./-]+',name):
        raise ValueError('Unsafe manifest path')
    parts=PurePosixPath(name).parts
    if not parts or name.startswith('/') or any(p in ('.','..') for p in parts) or '/'.join(parts)!=name:
        raise ValueError('Unsafe manifest path')
    path=root
    for part in parts:
        path=path/part
        if path.exists() and (path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&0x400):
            raise ValueError('Reparse paths refused')
    if root not in path.resolve().parents:raise ValueError('Manifest path outside root')
    return path


def read_manifest(root, expected=None):
    raw=safe_path(root,MANIFEST).read_bytes()
    if len(raw)>1024*1024 or (expected is not None and sha(raw)!=expected):
        raise ValueError('Manifest hash/size mismatch')
    m=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs)
    if m.get('schema')!=1 or m.get('receipt02Sha256')!=RECEIPT02 or type(m.get('entries')) is not list:
        raise ValueError('Unsupported manifest')
    seen=set()
    for e in m['entries']:
        if type(e) is not dict or set(e)!={'path','sha256','bytes','group'}:
            raise ValueError('Invalid manifest entry')
        safe_path(root,e['path'])
        if e['path'].casefold() in seen or e['path']==MANIFEST:
            raise ValueError('Duplicate manifest path')
        seen.add(e['path'].casefold())
        if type(e['sha256']) is not str or not re.fullmatch('[a-f0-9]{64}',e['sha256']):
            raise ValueError('Invalid hash')
        if type(e['bytes']) is not int or not 0<e['bytes']<=4*1024*1024:
            raise ValueError('Invalid source size')
    return m,sha(raw)


def verify_tree(root, expected=None, exact=False):
    root=Path(root).resolve()
    m,manifest_hash=read_manifest(root,expected)
    entries={e['path']:e for e in m['entries']}
    for name,e in entries.items():
        data=safe_path(root,name).read_bytes()
        if len(data)!=e['bytes'] or sha(data)!=e['sha256']:raise ValueError('File hash mismatch: '+name)
        if b'\0' in data:raise ValueError('Nontext payload refused')
        data.decode('utf-8')
    # Independent receipt anchors: a self-consistent manifest cannot silently
    # replace the reviewed 29-file revision or omit its dependency closure.
    rpath='adapters/process04/receipt-02.json'
    if entries.get(rpath,{}).get('sha256')!=RECEIPT02:raise ValueError('Missing reviewed receipt02')
    r=json.loads(safe_path(root,rpath).read_text(encoding='utf-8'))
    expected_files=dict(r['fileSha256'])
    if len(expected_files)!=29:raise ValueError('Reviewed source count mismatch')
    anchors={
        'adapters/process04/receipt-01.json':r['frozenEvidence']['process04PriorReceiptSha256'],
        'adapters/receipt-real-stream-source-02.json':r['frozenEvidence']['adapters/receipt-real-stream-source-02.json']['sha256'],
        'native/receiver03/receipt-01.json':r['frozenEvidence']['native/receiver03/receipt-01.json']['sha256'],
        'native/receiver04/semantic-expiry-oracle/model-results-01.json':r['frozenEvidence']['oracle']['originalReceiptSha256'],
        'native/receiver04/semantic-expiry-oracle/suppression-results-01.json':r['frozenEvidence']['oracle']['suppressionReceiptSha256'],
    }
    expected_files.update(anchors);expected_files[rpath]=RECEIPT02
    for path in ('adapters/receipt-real-stream-source-02.json','native/receiver03/receipt-01.json'):
        old=json.loads(safe_path(root,path).read_text(encoding='utf-8'))
        for name,h in old['fileSha256'].items():
            if name in expected_files and expected_files[name]!=h:raise ValueError('Frozen receipt conflict')
            expected_files[name]=h
    oracle='native/receiver04/semantic-expiry-oracle/'
    old=json.loads(safe_path(root,oracle+'model-results-01.json').read_text(encoding='utf-8'))
    expected_files.update({oracle+n:h for n,h in old['sourceSha256'].items()})
    extension=json.loads(safe_path(root,oracle+'suppression-results-01.json').read_text(encoding='utf-8'))
    expected_files[oracle+'test_suppression.py']=extension['sourceSha256']
    if len(expected_files)!=81:raise ValueError('Dependency closure count mismatch')
    for name,h in expected_files.items():
        if entries.get(name,{}).get('sha256')!=h:raise ValueError('Receipt dependency missing: '+name)
    tooling={'publication04/verify.py','publication04/test_verify.py','publication04/README.md'}
    if set(entries)!=set(expected_files)|tooling:raise ValueError('Unexpected allowlist membership')
    if exact:
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        if actual!=set(entries)|{MANIFEST}:raise ValueError('Standalone tree has extra/missing files')
    return dict(manifestSha256=manifest_hash,listedFiles=len(entries),payloadFiles=81,
                reviewedFiles=29,frozenSource02=26,frozenReceiver03=15)


def copy_tree(root, destination, expected):
    root=Path(root).resolve();destination=Path(destination).resolve()
    if destination==root or root in destination.parents or destination in root.parents:
        raise ValueError('Stage must be separate from source')
    verify_tree(root,expected)
    m,_=read_manifest(root,expected)
    destination.mkdir(parents=False,exist_ok=False)
    for name in [e['path'] for e in m['entries']]+[MANIFEST]:
        src=safe_path(root,name);dst=safe_path(destination,name)
        dst.parent.mkdir(parents=True,exist_ok=True)
        with dst.open('xb') as out:out.write(src.read_bytes())
    verify_tree(destination,expected,exact=True)
    return destination


def replay(root):
    """Test-only execution; common launch/I/O entry points fail immediately.

    These guards prevent accidental side effects in reviewed tests. This is NOT
    a sandbox for hostile Python. No fixture/host/native executable is invoked.
    """
    root=Path(root).resolve();sys.dont_write_bytecode=True
    sys.path.insert(0,str(root))
    old_argv=sys.argv;output=io.StringIO()
    def refused(*args,**kwargs):raise RuntimeError('Publication replay forbids runtime I/O')
    try:
        with ExitStack() as stack:
            for name in ('socket.socket','os.pipe','os.system','subprocess.Popen','threading.Thread.start'):
                stack.enter_context(patch(name,refused))
            import ctypes
            if hasattr(ctypes,'WinDLL'):stack.enter_context(patch('ctypes.WinDLL',refused))
            sys.argv=['adapters.process04.validate']
            with redirect_stdout(output):
                try:runpy.run_module('adapters.process04.validate',run_name='__main__')
                except SystemExit as result:
                    if result.code not in (0,None):raise ValueError('Offline validation failed') from None
        result=json.loads(output.getvalue())
        if result.get('status')!='offline-source-review-candidate' or result.get('tests')!=97 or not result.get('sourceStable'):
            raise ValueError('Unexpected replay result')
        for name,module in tuple(sys.modules.items()):
            if name=='session_core' or name=='model' or name.startswith(('adapters.','oracle_')):
                file=getattr(module,'__file__',None)
                if file and root not in Path(file).resolve().parents:raise ValueError('Import escaped standalone tree')
        return result
    finally:sys.argv=old_argv;sys.path.pop(0)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--expect-manifest',required=True)
    p.add_argument('--exact',action='store_true')
    p.add_argument('--run-tests',action='store_true')
    p.add_argument('--copy-to',type=Path)
    args=p.parse_args();root=args.root.resolve()
    report=verify_tree(root,args.expect_manifest,args.exact)
    if args.copy_to:
        root=copy_tree(root,args.copy_to,args.expect_manifest)
        report['stage']=str(root)
    if args.run_tests:
        report['tests']=replay(root)['tests']
        verify_tree(root,args.expect_manifest,args.exact or bool(args.copy_to))
    report['status']='passed';print(json.dumps(report))


if __name__=='__main__':main()

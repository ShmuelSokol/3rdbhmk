"""Offline source/codec replay only; never launches OS/native/UE fixtures."""
import argparse,ast,hashlib,json,re,sys,unittest
from pathlib import Path,PurePosixPath
from unittest.mock import patch

def sha(b):return hashlib.sha256(b).hexdigest()
def path(root,name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or str(p)!=name:raise ValueError('Unsafe path')
    f=root/name
    if not f.resolve().is_relative_to(root.resolve()) or f.is_symlink():raise ValueError('Escaped path')
    return f
def verify(root,expected):
    raw=(root/'settings_publication02/allowlist.json').read_bytes()
    if sha(raw)!=expected:raise ValueError('Manifest pin mismatch')
    m=json.loads(raw)
    for x in m['files']:
        b=path(root,x['path']).read_bytes()
        if sha(b)!=x['sha256'] or len(b)!=x['bytes']:raise ValueError('Payload changed: '+x['path'])
        forbidden=[b'C:/'+b'Mikdash',b'C:\\'+b'Mikdash',b'C:\\\\'+b'Mikdash',b'C:/'+b'Users/',b'C:\\\\'+b'Users\\']
        if any(n in b for n in forbidden):raise ValueError('Private path detected')
        if x['path'].endswith('.py'):ast.parse(b,filename=x['path'])
    for x in m['dependencies']:
        if sha(path(root,x['path']).read_bytes())!=x['git_blob_sha256']:raise ValueError('Dependency changed')
    return m
def replay(root):
    sys.path.insert(0,str(root))
    def forbidden(*a,**k):raise AssertionError('Process/socket/Windows fixture IO forbidden')
    with patch('subprocess.Popen',forbidden),patch('socket.socket',forbidden):
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in
            ('runtime_settings05.test_codec','runtime_settings05.test_composition'))
        result=unittest.TextTestRunner().run(suite)
    if result.testsRun!=9 or not result.wasSuccessful():raise ValueError('Replay failed')
    for name,module in tuple(sys.modules.items()):
        if name.split('.')[0] in ('adapters','session_core','runtime_candidate05','runtime_settings01','runtime_settings03','runtime_settings05'):
            f=getattr(module,'__file__',None)
            if f and not Path(f).resolve().is_relative_to(root.resolve()):raise ValueError('Import escaped replay')
    return result.testsRun
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--expect-manifest',required=True)
    a=p.parse_args();root=a.root.resolve();m=verify(root,a.expect_manifest);n=replay(root);verify(root,a.expect_manifest)
    print(json.dumps(dict(status='passed',files=len(m['files']),dependencies=len(m['dependencies']),source_codec_tests=n,
        windows_evidence_rerun=False,ue=False,settings06_scope='source AST and pinned historical Windows evidence, not UE runtime')))
if __name__=='__main__':main()

"""Portable source/evidence verifier. Never launches native/OS lifecycle fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(root,expected):
    manifest=root/'settings_publication01/allowlist.json'
    if digest(manifest)!=expected:raise ValueError('Publication manifest differs')
    data=json.loads(manifest.read_text())
    for record in data['files']:
        name=record['path'];p=root/name
        if Path(name).is_absolute() or '..' in Path(name).parts or not p.resolve().is_relative_to(root.resolve()):raise ValueError('Unsafe manifest path')
        raw=p.read_bytes()
        if len(raw)!=record['bytes'] or hashlib.sha256(raw).hexdigest()!=record['sha256']:raise ValueError('Payload changed: '+name)
        needles=[b'C:/'+b'Mikdash',b'C:\\'+b'Mikdash',b'C:\\\\'+b'Mikdash',b'C:/'+b'Users/',b'C:\\\\'+b'Users\\']
        if any(needle in raw for needle in needles):
            raise ValueError('Private path in payload: '+name)
    for dependency in data['dependencies']:
        p=root/dependency['path']
        if digest(p)!=dependency['git_blob_sha256']:raise ValueError('Published dependency blob mismatch: '+dependency['path'])
    return data

def replay(root):
    sys.path[:0]=[str(root),str(root/'runtime_settings01')]
    suite=unittest.TestSuite()
    for module in ('runtime_settings01.test_paths','runtime_settings03.test_integration'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(module))
    def forbidden(*a,**k):raise AssertionError('Runtime/network/process IO forbidden in portable source replay')
    with patch('subprocess.Popen',forbidden),patch('socket.socket',forbidden):
        result=unittest.TextTestRunner(verbosity=1).run(suite)
    if result.testsRun!=18 or not result.wasSuccessful():raise ValueError('Portable source tests failed')
    for name,module in list(sys.modules.items()):
        if name.split('.')[0] in ('adapters','session_core','runtime_settings01','runtime_settings03','runtime_candidate05'):
            path=getattr(module,'__file__',None)
            if path and not Path(path).resolve().is_relative_to(root.resolve()):raise ValueError('Import escaped portable root')
    return result.testsRun

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--expect-manifest',required=True);ap.add_argument('--tests',action='store_true')
    args=ap.parse_args();root=args.root.resolve()
    data=verify(root,args.expect_manifest)
    tests=replay(root) if args.tests else 0
    verify(root,args.expect_manifest)
    print(json.dumps({'status':'passed','payload_files':len(data['files']),'published_dependencies':len(data['dependencies']),
                      'portable_source_tests':tests,'ue':False,'windows_lifecycle_rerun':False}))

if __name__=='__main__':main()

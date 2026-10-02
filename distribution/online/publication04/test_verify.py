"""Verifier regressions; no lifecycle/core/native code is run by these tests."""
import importlib.util
import json
from pathlib import Path
import tempfile
import shutil
import unittest

spec=importlib.util.spec_from_file_location('publication_verifier',Path(__file__).with_name('verify.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.base=Path(tempfile.gettempdir()).resolve()
        self.root=Path(tempfile.mkdtemp(prefix='receiver04-verifier-',dir=str(self.base))).resolve()
    def tearDown(self):
        # Exact freshly allocated temporary directory checked before recursion.
        assert self.root.parent==self.base and self.root.name.startswith('receiver04-verifier-')
        shutil.rmtree(str(self.root))
    def test_path_traversal_and_windows_aliases_refused(self):
        for path in ('../x','/x','C:/x','a\\b','a//b','a/./b','a/../b'):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):v.safe_path(self.root,path)
    def test_duplicate_json_keys_refused(self):
        with self.assertRaises(ValueError):json.loads('{"x":1,"x":2}',object_pairs_hook=v.pairs)
    def test_manifest_hash_tampering_refused(self):
        (self.root/'publication04').mkdir()
        (self.root/v.MANIFEST).write_text('{}')
        with self.assertRaises(ValueError):v.read_manifest(self.root,'0'*64)
    def test_missing_reviewed_receipt_anchor_refused(self):
        (self.root/'publication04').mkdir()
        raw=json.dumps(dict(schema=1,receipt02Sha256=v.RECEIPT02,entries=[])).encode()
        (self.root/v.MANIFEST).write_bytes(raw)
        with self.assertRaises(ValueError):v.verify_tree(self.root,v.sha(raw))
    def test_case_colliding_paths_refused(self):
        (self.root/'publication04').mkdir()
        entries=[dict(path=n,sha256='0'*64,bytes=1,group='test') for n in ('a.py','A.py')]
        raw=json.dumps(dict(schema=1,receipt02Sha256=v.RECEIPT02,entries=entries)).encode()
        (self.root/v.MANIFEST).write_bytes(raw)
        with self.assertRaises(ValueError):v.read_manifest(self.root,v.sha(raw))
    def test_changed_payload_bytes_refused(self):
        (self.root/'publication04').mkdir();(self.root/'a.py').write_bytes(b'changed')
        raw=json.dumps(dict(schema=1,receipt02Sha256=v.RECEIPT02,entries=[
            dict(path='a.py',sha256=v.sha(b'original'),bytes=8,group='test')])).encode()
        (self.root/v.MANIFEST).write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'File hash mismatch'):v.verify_tree(self.root,v.sha(raw))


if __name__=='__main__':unittest.main()

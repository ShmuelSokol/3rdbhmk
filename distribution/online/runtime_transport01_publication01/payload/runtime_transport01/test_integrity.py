"""Portable preparation hashes only; no allocator/process/native acquisition."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from session_core import SessionError
from runtime_transport01.integrity import verify_host_sources
from runtime_transport01.owned_host import TransportProcesses
from adapters.process04.host import OwnedProcesses

class IntegrityTests(unittest.TestCase):
    def test_complete_portable_sources_verify(self):verify_host_sources()
    def test_exact_prepare_delegation_after_verification(self):
        obj=TransportProcesses.__new__(TransportProcesses);obj.verified=True
        def base(p):self.assertFalse(p.verified);p.verified=True
        with patch.object(OwnedProcesses,'prepare',base):obj.prepare()
        self.assertTrue(obj.verified)
    def test_missing_and_modified_source_fail_without_rebinding_pins(self):
        source=Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(prefix='transport-integrity-') as td:
            root=Path(td).resolve()
            self.assertEqual(root.parent,Path(tempfile.gettempdir()).resolve())
            pins=json.loads((source/'host-pins.json').read_text())
            for n in list(pins)+['runtime_transport01/host-pins.json','runtime_transport01/integrity.py']:
                p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((source.parent/n).read_bytes())
            spec=importlib.util.spec_from_file_location('isolated_integrity',root/'runtime_transport01/integrity.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            module.verify_host_sources()
            target=root/'runtime_settings02/win32_predicate.py';b=target.read_bytes();target.write_bytes(b+b'\n# altered\n')
            with self.assertRaises(SessionError):module.verify_host_sources()
            target.unlink()
            with self.assertRaises(SessionError):module.verify_host_sources()
    def test_allocator_and_predicate_code_is_unmodified_git_dependency(self):
        # Exact Git blob identity is checked by export. This verifies the runtime
        # verifier covers the real implementations, not a replacement predicate.
        pins=json.loads((Path(__file__).parent/'host-pins.json').read_text())
        for n in ['runtime_settings02/win32_predicate.py','runtime_settings03/owned_settings_host.py',
                  'runtime_settings05/owned_host.py','runtime_settings06/allocator.py',
                  'adapters/process04/win32_child.py','session_core.py']:
            self.assertIn(n,pins)
if __name__=='__main__':unittest.main(verbosity=2)

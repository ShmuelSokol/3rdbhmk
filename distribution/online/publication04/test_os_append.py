"""Copy/hash negative checks only; no fixture import or OS process launch."""
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_os_append import APPEND, export, verify

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = hashlib.sha256((ROOT / APPEND).read_bytes()).hexdigest()


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.container = Path(tempfile.mkdtemp(prefix='receiver04-os-export-tests-')).resolve()
        self.tree = export(ROOT, self.container / 'fresh', EXPECTED)

    def tearDown(self):
        # Delete only our resolved temporary container, never source/publication.
        if self.container.parent != Path(tempfile.gettempdir()).resolve() or not self.container.name.startswith('receiver04-os-export-tests-'):
            raise ValueError('Unsafe test cleanup')
        shutil.rmtree(self.container)

    def test_exact_export_and_no_overwrite(self):
        self.assertEqual(verify(self.tree, EXPECTED, True)['totalWithManifests'], 100)
        with self.assertRaises(FileExistsError):
            export(ROOT, self.tree, EXPECTED)
        verify(self.tree, EXPECTED, True)

    def test_changed_executed_fixture_refused(self):
        p = self.tree / 'os_fixture04/child.py'
        p.write_bytes(p.read_bytes() + b'\n# changed\n')
        with self.assertRaises(ValueError):
            verify(self.tree, EXPECTED, True)

    def test_evidence_tamper_refused(self):
        p = self.tree / 'publication04/os-evidence/receipt-sanitized-01.json'
        p.write_bytes(b'{}\n')
        with self.assertRaises(ValueError):
            verify(self.tree, EXPECTED, True)

    def test_extra_file_and_bad_manifest_refused(self):
        (self.tree / 'unlisted.log').write_bytes(b'synthetic')
        with self.assertRaises(ValueError):
            verify(self.tree, EXPECTED, True)
        with self.assertRaises(ValueError):
            verify(self.tree, '0' * 64)


if __name__ == '__main__':
    unittest.main()

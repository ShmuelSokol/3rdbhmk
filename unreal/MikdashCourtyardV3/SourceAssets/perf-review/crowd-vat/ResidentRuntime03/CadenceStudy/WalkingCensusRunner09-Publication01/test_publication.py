"""Publication-only fault checks. Never reads active project inputs."""
import tempfile, unittest, shutil
from pathlib import Path
import replay

class PublicationFaults(unittest.TestCase):
    def test_path_escape_refused(self):
        for name in ('../x','/x','a/../x','a\\x','C:/x','a//x'):
            with self.subTest(name=name),self.assertRaises(ValueError):replay.safe(Path.cwd(),name)
    def copied_audit(self,mutate):
        original=replay.ROOT
        with tempfile.TemporaryDirectory(prefix='census09-pub-fault-') as t:
            copied=Path(t)/'capsule';shutil.copytree(original,copied)
            try:
                replay.ROOT=copied;mutate(copied)
                with self.assertRaises(ValueError):replay.audit()
            finally:replay.ROOT=original
    def test_extra_file_refused(self):self.copied_audit(lambda p:(p/'extra.txt').write_text('unlisted'))
    def test_binary_refused(self):self.copied_audit(lambda p:(p/'extra.dll').write_bytes(b'MZ'))
    def test_source_mutation_refused(self):self.copied_audit(lambda p:(p/'author/runner.py').write_text('changed'))

if __name__=='__main__':unittest.main(verbosity=2)

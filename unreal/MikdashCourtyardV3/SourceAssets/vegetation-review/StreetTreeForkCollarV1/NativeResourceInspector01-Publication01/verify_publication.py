"""Read-only allowlist, hash, accounting and source privacy checks."""
from pathlib import Path
import ast
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent


def main():
    manifest = json.loads((ROOT/'manifest.json').read_bytes())
    files = manifest['files']
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
    assert actual == set(files) | {'manifest.json'}, 'Unexpected/missing payload'
    allowed = {'.py', '.cpp', '.h', '.cs', '.uplugin', '.json', '.txt', '.patch'}
    for name, pin in files.items():
        p = ROOT/name
        assert p.suffix in allowed and not p.is_symlink(), name
        data = p.read_bytes()
        assert hashlib.sha256(data).hexdigest() == pin, name
        text = data.decode('utf-8')
        assert not re.search(r'(?i)\b[a-z]:[/\\]|\\\\[a-z0-9]|/(?:home|Users|mnt)/', text), ('machine path', name)
        if p.suffix == '.py':
            ast.parse(text)
        if p.suffix in ('.json', '.uplugin'):
            json.loads(text)
    accounting = json.loads((ROOT/'source-accounting.json').read_bytes())
    assert len(accounting['files']) == 14
    included = [f for f in accounting['files'] if f['disposition'] == 'included unchanged']
    assert len(included) == 6
    for f in included:
        assert files[f['originalFile']] == f['originalSHA256']
    provenance = json.loads((ROOT/'test-provenance.json').read_bytes())
    assert files[provenance['derivedFile']] == provenance['derivedSHA256']
    print(json.dumps(dict(status='PASS_PORTABLE_SOURCE_ALLOWLIST_PRIVACY',
                          payloadFiles=len(files), originalIncluded=6, originalOmitted=8,
                          manifestSHA256=hashlib.sha256((ROOT/'manifest.json').read_bytes()).hexdigest(),
                          UEProof=False)))


if __name__ == '__main__':
    main()

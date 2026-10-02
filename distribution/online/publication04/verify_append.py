"""Verify/export separately pinned append evidence; never compiles or executes it."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify import safe_path, sha, pairs, verify_tree, copy_tree, read_manifest

BASE = 'a1d32b7bc5616f42b6a6566f296ca6fc408cff1bca0f58d3fa060f53a1d0b594'
APPEND = 'publication04/append-mailbox-01.json'
NAMES = {
    'publication04/verify_append.py',
    'publication04/mailbox-evidence/SemanticMailboxStandalone.cpp',
    'publication04/mailbox-evidence/receipt-sanitized-01.json',
    'publication04/mailbox-evidence/README.md',
}


def verify(root, expected, exact=False):
    verify_tree(root, BASE)
    raw = safe_path(root, APPEND).read_bytes()
    if len(raw) > 16384 or sha(raw) != expected:
        raise ValueError('Append manifest mismatch')
    m = json.loads(raw, object_pairs_hook=pairs)
    if m['baseManifestSha256'] != BASE or {e['path'] for e in m['entries']} != NAMES or len(m['entries']) != len(NAMES):
        raise ValueError('Append membership mismatch')
    for e in m['entries']:
        data = safe_path(root, e['path']).read_bytes()
        if len(data) != e['bytes'] or sha(data) != e['sha256'] or b'\0' in data:
            raise ValueError('Append source mismatch')
        data.decode('utf-8')
    evidence = json.loads(safe_path(root, 'publication04/mailbox-evidence/receipt-sanitized-01.json').read_bytes())
    for name, digest in evidence['sourceHashes'].items():
        if sha(safe_path(root, 'native/' + name).read_bytes()) != digest:
            raise ValueError('Mailbox header evidence mismatch')
    driver = safe_path(root, 'publication04/mailbox-evidence/SemanticMailboxStandalone.cpp')
    if sha(driver.read_bytes()) != evidence['driverSha256']:
        raise ValueError('Mailbox driver mismatch')
    if exact:
        base, _ = read_manifest(root, BASE)
        allowed = {e['path'] for e in base['entries']} | NAMES | {APPEND, 'publication04/allowlist.json'}
        if {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} != allowed:
            raise ValueError('Append tree has extra/missing files')
    return {'baseListedFiles': 84, 'appendListedFiles': 4, 'totalWithManifests': 90,
            'appendSha256': expected, 'status': 'passed', 'execution': 'none'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--expect-append', required=True)
    p.add_argument('--exact', action='store_true')
    p.add_argument('--copy-to', type=Path)
    a = p.parse_args()
    root = a.root.resolve()
    result = verify(root, a.expect_append, a.exact)
    if a.copy_to:
        target = copy_tree(root, a.copy_to, BASE)
        for name in sorted(NAMES | {APPEND}):
            dest = safe_path(target, name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as out:
                out.write(safe_path(root, name).read_bytes())
        result = verify(target, a.expect_append, True)
    print(json.dumps(result))


if __name__ == '__main__':
    main()

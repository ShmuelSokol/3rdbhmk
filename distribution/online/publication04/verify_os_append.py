"""Source/hash export only. Never imports or executes the OS fixture."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify import safe_path, sha, pairs, read_manifest, copy_tree
from verify_append import verify as verify_mailbox, NAMES as MAILBOX_NAMES, APPEND as MAILBOX_PATH, BASE

MAILBOX_HASH = '5a07c8a9e65ea0647593f257fb3cefe60145668df9d48efb34aa68d81a4d44d9'
FIXTURE_HASH = '61d11a37f6109749675fd1e56d6b1f301f44beb94bf167639b3e43cf067f8595'
FIXTURE_PATH = 'os_fixture04/allowlist-03.json'
APPEND = 'publication04/append-os-01.json'
FIXTURE_FILES = {'child.py', 'run_reviewed.py', 'verify_source.py', 'README.md'}
NAMES = { 'os_fixture04/' + name for name in FIXTURE_FILES } | {
    FIXTURE_PATH, 'publication04/os-evidence/receipt-sanitized-01.json',
    'publication04/os-evidence/LIMITS.md', 'publication04/verify_os_append.py',
    'publication04/test_os_append.py',
}


def verify(root, expected, exact=False):
    root = Path(root).resolve()
    verify_mailbox(root, MAILBOX_HASH)
    raw = safe_path(root, APPEND).read_bytes()
    if len(raw) > 16384 or sha(raw) != expected:
        raise ValueError('OS append manifest mismatch')
    m = json.loads(raw, object_pairs_hook=pairs)
    if (m['schema'] != 1 or m['baseManifestSha256'] != BASE or
            m['mailboxManifestSha256'] != MAILBOX_HASH or m['fixtureManifestSha256'] != FIXTURE_HASH or
            len(m['entries']) != len(NAMES) or {e['path'] for e in m['entries']} != NAMES):
        raise ValueError('OS append membership/anchor mismatch')
    for e in m['entries']:
        data = safe_path(root, e['path']).read_bytes()
        if len(data) != e['bytes'] or sha(data) != e['sha256'] or b'\0' in data:
            raise ValueError('OS append source mismatch')
        data.decode('utf-8')
    raw_fixture = safe_path(root, FIXTURE_PATH).read_bytes()
    if sha(raw_fixture) != FIXTURE_HASH:
        raise ValueError('Executed fixture manifest mismatch')
    fixture = json.loads(raw_fixture, object_pairs_hook=pairs)
    if len(fixture['entries']) != 4 or {e['path'] for e in fixture['entries']} != FIXTURE_FILES:
        raise ValueError('Executed fixture membership mismatch')
    for e in fixture['entries']:
        data = safe_path(root, 'os_fixture04/' + e['path']).read_bytes()
        if sha(data) != e['sha256'] or len(data) != e['bytes']:
            raise ValueError('Executed fixture bytes changed')
    receipt = json.loads(safe_path(root, 'publication04/os-evidence/receipt-sanitized-01.json').read_bytes(), object_pairs_hook=pairs)
    if (receipt['status'] != 'passed' or receipt['completedCases'] != 6 or receipt['expectedCases'] != 6 or
            len(receipt['cases']) != 6 or receipt['unresolvedOwnedLeases'] != 0 or receipt['sentinelClosed'] is not True or
            receipt['baseManifestSha256'] != BASE or receipt['fixtureManifestSha256'] != FIXTURE_HASH or
            any(receipt[k] != 0 for k in ('nativeGameLaunches', 'socketOperations', 'productionCredentials'))):
        raise ValueError('OS evidence scope/anchor mismatch')
    if exact:
        base, _ = read_manifest(root, BASE)
        allowed = {e['path'] for e in base['entries']} | MAILBOX_NAMES | NAMES | {
            'publication04/allowlist.json', MAILBOX_PATH, APPEND}
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        if actual != allowed:
            raise ValueError('Combined tree has extra/missing files')
    return dict(status='passed', osAppendSha256=expected, osAppendListedFiles=9,
                totalWithManifests=100, osFixtureExecution='none; historical evidence verified only')


def export(root, destination, expected):
    root = Path(root).resolve()
    verify(root, expected)
    target = copy_tree(root, destination, BASE)
    for name in sorted(MAILBOX_NAMES | NAMES | {MAILBOX_PATH, APPEND}):
        dest = safe_path(target, name)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as out:
            out.write(safe_path(root, name).read_bytes())
    verify(target, expected, True)
    return target


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--expect-os-append', required=True)
    p.add_argument('--exact', action='store_true')
    p.add_argument('--copy-to', type=Path)
    a = p.parse_args()
    root = a.root.resolve()
    report = verify(root, a.expect_os_append, a.exact)
    if a.copy_to:
        report = verify(export(root, a.copy_to, a.expect_os_append), a.expect_os_append, True)
    print(json.dumps(report))


if __name__ == '__main__':
    main()

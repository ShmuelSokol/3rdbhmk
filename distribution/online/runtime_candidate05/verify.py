"""Read-only exact candidate/dependency verifier. Does not invoke engine or tests."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-manifest', required=True)
    args = parser.parse_args()
    manifest = ROOT / 'allowlist-01.json'
    assert digest(manifest) == args.expect_manifest, 'Manifest pin mismatch'
    entries = json.loads(manifest.read_text())['entries']
    expected = {entry['path'] for entry in entries} | {'allowlist-01.json'}
    assert len(expected) == len(entries) + 1, 'Duplicate entries'
    assert {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()} == expected, 'Closure mismatch'
    for entry in entries:
        path = ROOT / entry['path']
        path.resolve().relative_to(ROOT)  # raises for escape; Python 3.8 compatible
        assert path.stat().st_size == entry['bytes'] and digest(path) == entry['sha256'], 'Source mismatch'
    context = json.loads((ROOT / 'source-context.json').read_text())
    for path, sha in context['dependencySha256'].items():
        assert digest(Path(path)) == sha, 'Dependency mismatch'
    print(f"Exact {len(expected)} candidate files; {len(context['dependencySha256'])} dependency pins match. No native execution.")


if __name__ == '__main__':
    main()

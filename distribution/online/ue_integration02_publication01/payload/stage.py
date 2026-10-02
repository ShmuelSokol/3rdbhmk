"""Source-only pinned copy/verification. No subprocesses, engine or compilation."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def clean(path):
    path = Path(path).absolute()
    for p in (path, *path.parents):
        if p.exists() and (p.is_symlink() or getattr(p.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('Reparse source/destination refused')
    return path.resolve()


def relative(root, name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_./-]{1,240}', name):
        raise ValueError('Invalid relative name')
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '/'.join(p.parts) != name:
        raise ValueError('Invalid relative name')
    result = clean(root / name)
    if root not in result.parents:
        raise ValueError('Path escapes root')
    return result


def manifest(root, expected):
    raw = (root / 'allowlist.json').read_bytes()
    if len(raw) > 512000 or digest(raw) != expected:
        raise ValueError('Manifest mismatch')
    m = json.loads(raw)
    seen = set()
    for e in m['entries']:
        relative(root, e['path'])
        if e['path'].casefold() in seen or e['path'] == 'allowlist.json':
            raise ValueError('Duplicate entry')
        seen.add(e['path'].casefold())
    return m


def check_file(path, entry):
    raw = clean(path).read_bytes()
    if len(raw) != entry['bytes'] or digest(raw) != entry['sha256']:
        raise ValueError('Pinned source mismatch: ' + entry['path'])
    return raw


def verify(root, expected, exact=True):
    root = clean(root)
    m = manifest(root, expected)
    for e in m['entries']:
        check_file(relative(root, e['path']), e)
    if exact:
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
        if actual != {e['path'] for e in m['entries']} | {'allowlist.json'}:
            raise ValueError('Unexpected/missing staged file')
    return m


def copy(root, destination, expected, original=False):
    root, destination = clean(root), clean(destination)
    if root == destination or root in destination.parents or destination in root.parents:
        raise ValueError('Overlapping destination')
    m = manifest(root, expected) if original else verify(root, expected)
    # Validate entire pinned input before creating any destination.
    for e in m['entries']:
        check_file(Path(e['source']) if original else relative(root, e['path']), e)
    destination.mkdir(exist_ok=False)
    for e in m['entries']:
        data = check_file(Path(e['source']) if original else relative(root, e['path']), e)
        dst = relative(destination, e['path'])
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open('xb') as f:
            f.write(data)
    with (destination / 'allowlist.json').open('xb') as f:
        f.write((root / 'allowlist.json').read_bytes())
    verify(destination, expected)
    return destination


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--expect-manifest', required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument('--stage', type=Path, help='Copy original sources using pinned source paths')
    g.add_argument('--copy-to', type=Path, help='Clone this complete standalone source tree')
    a = p.parse_args()
    root = Path(__file__).resolve().parent
    if a.stage or a.copy_to:
        root = copy(root, a.stage or a.copy_to, a.expect_manifest, bool(a.stage))
    m = verify(root, a.expect_manifest)
    print(json.dumps(dict(status='source-only-verified', listedFiles=len(m['entries']),
                         manifestSha256=a.expect_manifest, buildExecuted=False)))

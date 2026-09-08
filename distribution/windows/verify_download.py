"""Verify and extract the two release ZIPs into a fresh folder (no game launch)."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verify(app, data, destination, original):
    if destination.exists():
        raise ValueError('Use a destination that does not exist')
    names = set()
    for archive in (app, data):
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None, 'CRC mismatch'
            for entry in z.infolist():
                path = PurePosixPath(entry.filename)
                assert not path.is_absolute() and '..' not in path.parts
                assert ':' not in entry.filename and '\\' not in entry.filename
                assert entry.filename.lower() not in names
                names.add(entry.filename.lower())
    destination.mkdir(parents=True)
    for archive in (app, data):
        with zipfile.ZipFile(archive) as z:
            z.extractall(destination)
    checked = []
    for line in (destination / 'SHA256SUMS.txt').read_text(encoding='utf-8-sig').splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(None, 1)
        relative = relative.lstrip('* ')
        file_path = destination / relative
        assert file_path.resolve().is_relative_to(destination.resolve()), relative
        assert digest(file_path) == expected.lower(), relative
        checked.append(relative)
    original_checked = 0
    for source in original.rglob('*'):
        if not source.is_file():
            continue
        relative = source.relative_to(original).as_posix()
        if source.suffix.lower() == '.pdb' or relative.startswith('MikdashCourtyardV3/Saved/'):
            continue
        target = destination / relative
        assert target.is_file(), 'Missing original runtime file: ' + relative
        assert digest(target) == digest(source), 'Original runtime mismatch: ' + relative
        original_checked += 1
    assert original_checked > 0
    data_path = 'MikdashCourtyardV3/Content/Paks/MikdashCourtyardV3-Windows.ucas'
    assert data_path in checked and 'MikdashCourtyardV3.exe' in checked
    assert 'CREDITS.txt' in checked
    actual = {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
    assert actual == set(checked) | {'SHA256SUMS.txt'}, 'Missing/unlisted file'
    return {'status': 'passed', 'filesChecked': len(checked), 'totalFiles': len(actual),
            'archives': [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in (app, data)],
            'archiveCrc': 'passed', 'installedFileHashes': 'passed', 'gameLaunched': False, 'originalRuntimeFilesMatched': original_checked}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('app', type=Path)
    parser.add_argument('data', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('--original', required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.app, args.data, args.destination, args.original)
    args.receipt.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


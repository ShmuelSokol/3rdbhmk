"""Read-only source scope checks. Publication success never grants native eligibility."""
import hashlib
import json
from pathlib import Path

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def audit(root, rows):
    root = Path(root).resolve()
    result = dict(expected=len(rows), presentMatches=[], missing=[], changed=[])
    for row in rows:
        p = (root / row['path']).resolve()
        if not p.is_relative_to(root):
            raise ValueError('Source contract path escapes root')
        if not p.is_file():
            result['missing'].append(row)
        elif sha(p).lower() != row['sha256'].lower():
            result['changed'].append(dict(row, actualSha256=sha(p)))
        else:
            result['presentMatches'].append(row['path'])
    result['completeMatch'] = not result['missing'] and not result['changed']
    return result

def inspect(root, review):
    contract = json.loads((Path(review) / 'publication-source-contract-v4.json').read_text())
    baseline = Path(root) / contract['nativeBaseline']['path']
    if sha(baseline) != contract['nativeBaseline']['sha256']:
        raise ValueError('Historical baseline inventory hash changed')
    before = json.loads(baseline.read_text())
    rows = [dict(path=p, sha256=h) for p,h in before.items()
            if Path(p).suffix.lower() in ('.uasset','.umap','.glb')]
    return dict(requiredPrerequisites=audit(root, contract['requiredProjectFiles']),
                historicalNativeInventory=audit(root, rows))

def require_native(root, review):
    result = inspect(root, review)
    if not all(r['completeMatch'] for r in result.values()):
        raise RuntimeError('Native source baseline incomplete/changed: ' + json.dumps(result))
    return result

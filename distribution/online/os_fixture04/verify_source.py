"""Text/hash/AST verification ONLY. Never imports or runs the OS fixture."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAMES = {'child.py', 'run_reviewed.py', 'verify_source.py', 'README.md'}


def verify(expected):
    raw = (ROOT / 'allowlist-03.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected:
        raise ValueError('Fixture manifest mismatch')
    m = json.loads(raw)
    if len(m['entries']) != 4 or {e['path'] for e in m['entries']} != NAMES:
        raise ValueError('Fixture membership mismatch')
    for e in m['entries']:
        data = (ROOT / e['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != e['sha256'] or len(data) != e['bytes']:
            raise ValueError('Fixture source mismatch')
        if e['path'].endswith('.py'):
            ast.parse(data, filename=e['path'])
    return digest


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--expect-fixture', required=True)
    args = p.parse_args()
    print(json.dumps(dict(status='source-only-verified', sha256=verify(args.expect_fixture),
                         files=4, pythonSyntaxFiles=3, osFixtureExecuted=False)))

"""Offline post-build evidence only. Does not launch tools or load UE binaries."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage import verify


def inspect(root, expected):
    verify(root, expected, exact=False)
    if (root / 'run/deadline-overrun.txt').exists():
        raise ValueError('Wrapper total deadline overrun')
    receipt = json.loads((root / 'run/receipt.json').read_bytes())
    if (receipt['status'] != 'ubt_zero_object_review_required' or receipt['exitCode'] != 0 or
            receipt['cleanupConfirmed'] is not True or receipt['sourceStable'] is not True or
            receipt['withinTotalDeadline'] is not True or receipt['cleanupFinishedSeconds'] >= receipt['totalBudgetSeconds'] or
            receipt['manifestSha256'] != expected):
        raise ValueError('Accepted compile/cleanup receipt required')
    build = root / 'P/Intermediate/Build'
    objects = [p for p in build.rglob('*.obj') if 'Receiver04Compile' in p.parts and p.stat().st_size > 0]
    required = {'Wire.cpp.obj', 'Authority.cpp.obj', 'Receiver.cpp.obj', 'Bootstrap.cpp.obj',
                'OnlineController.cpp.obj', 'OnlineMovement.cpp.obj',
                'Receiver04CompileModule.cpp.obj', 'Receiver04CompileApi.cpp.obj'}
    if not required <= {p.name for p in objects}:
        raise ValueError('Missing production/API object files')
    generated = [p for p in build.rglob('*.gen.cpp') if 'Receiver04Compile' in p.parts]
    for stem, classes in {'OnlineController': ['AReceiver04Controller'],
                          'OnlineMovement': ['UReceiver04WalkerMovement', 'UReceiver04DoveMovement']}.items():
        matches = [p for p in generated if p.name == stem + '.gen.cpp']
        headers = [p for p in build.rglob(stem + '.generated.h') if 'Receiver04Compile' in p.parts]
        if len(matches) != 1 or len(headers) != 1:
            raise ValueError('Missing/ambiguous genuine UHT output')
        if not all(name in matches[0].read_text(encoding='utf-8-sig') for name in classes):
            raise ValueError('UHT class registration missing')
    # UBT always merges generated CPP, even with ordinary unity disabled. Require
    # compiled generated unity sources containing both real reflected code files.
    compiled_generated = []
    for obj in objects:
        source_name = obj.name[:-4]
        if '.gen.' not in source_name:
            continue
        for source in build.rglob(source_name):
            if 'Receiver04Compile' in source.parts and source.suffix == '.cpp':
                compiled_generated.append(source)
    text = '\n'.join(p.read_text(encoding='utf-8-sig') for p in compiled_generated)
    if not all(n + '.gen.cpp' in text for n in ('OnlineController', 'OnlineMovement')):
        raise ValueError('Cannot prove reflected code inclusion in compiled generated objects')
    return dict(status='uht-production-object-api-proof', runtimeProven=False,
                manifestSha256=expected, objectSha256={p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in objects})


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--expect-manifest', required=True)
    a = p.parse_args()
    print(json.dumps(inspect(Path(__file__).resolve().parent, a.expect_manifest), indent=2))

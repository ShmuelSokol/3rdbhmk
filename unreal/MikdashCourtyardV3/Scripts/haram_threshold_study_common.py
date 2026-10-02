"""Pure, offline evidence and exact triangle policy for HaramThresholdSidesV1."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/context-review/HaramThresholdSidesV1'
NS = '/Game/MikdashV3/MaterialReview/HaramThresholdSidesV1'
SOURCE = '/Game/MikdashV3/HaramPrecinctV3/SM_Haram_ThresholdsV2'
STAIRS = '/Game/MikdashV3/HaramPrecinctV3/SM_Haram_AccessV4'
PAVING = '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Materials/M_PrecinctPlaza_Paving'
ASHLAR = '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Materials/MI_PrecinctPlaza_Ashlar'
OBJ = 'SourceAssets/enclosure-review/HaramPrecinctV1/obj/SM_Haram_ThresholdsV2.obj'
PINNED = {
    SOURCE: '5de223e83e5d48abaf698710639d08b22595c25404cbaa6d03e392ace958b42b',
    STAIRS: '8dd3f4b274d0733aa1b91e6ad3ec2733b51c9a08696231b51e91f7e2a64770a1',
    PAVING: '40918a0589e5128fd99597208f3518e4c08f1d9d670f95f3e33e9f344a87f4c4',
    ASHLAR: '0d9bbba56518034c5ef80a65ecb74f5db9d4c5256ef88526b062ea8d0aa451f8',
}
OBJ_SHA = 'da91ef5f617b72e96f7252fa34e8f3903260c85a81d78db4eb032f52eacd04e6'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def disk(asset):
    require(asset.startswith('/Game/'), 'Only project assets allowed')
    return ROOT / 'Content' / (asset[6:] + '.uasset')


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def face_role(points):
    """UE clockwise source winding: horizontal top has NEGATIVE cross Z."""
    require(len(points) == 3 and all(math.isfinite(v) for p in points for v in p), 'Invalid triangle')
    a, b, c = points
    u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
    n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    require(sum(x*x for x in n) > 0, 'Degenerate triangle')
    if a[2] == b[2] == c[2]:
        require(n[2] != 0, 'Invalid horizontal face')
        return 'top' if n[2] < 0 else 'bottom'
    require(abs(n[2]) < 1e-6, 'Unexpected sloped face; do not guess a material')
    return 'side'


def oriented_key(points):
    """Exact values; allow cyclic corner start only, never reverse winding."""
    p = tuple(tuple(v for v in point) for point in points)
    return min(p, p[1:]+p[:1], p[2:]+p[:2])


def geometry_counter(triangles):
    return Counter(oriented_key(p) for p in triangles)


def source_triangles():
    require(sha(ROOT / OBJ) == OBJ_SHA, 'Source OBJ hash changed')
    vertices, triangles = [], []
    for line in (ROOT / OBJ).read_text().splitlines():
        fields = line.split()
        if fields and fields[0] == 'v':
            x, y, z = map(float, fields[1:])
            vertices.append([f32(x), f32(-y), f32(z)])
        elif fields and fields[0] == 'f':
            require(len(fields) == 4, 'Source must already be triangulated')
            triangles.append([vertices[int(f.split('/')[0])-1] for f in fields[1:]])
    require(len(triangles) == 180, 'Expected exactly 180 source triangles')
    return triangles


def snapshot(paths):
    return {p: sha(ROOT / p) for p in paths}


def validate_pins():
    for asset, digest in PINNED.items():
        require(sha(disk(asset)) == digest, 'Accepted asset changed: ' + asset)


def revision_hashes():
    paths = ['Scripts/haram_threshold_study_common.py', 'Scripts/study_haram_threshold_sides.py',
             'Scripts/run_haram_threshold_study.ps1', 'Scripts/haram_threshold_png.py',
             'SourceAssets/context-review/HaramThresholdSidesV1/source-audit.json',
             'SourceAssets/context-review/HaramThresholdSidesV1/query-source-evidence.json']
    return snapshot(paths)


def validate_preflight_record(record, wrapper, native_hash, current_revision, current_inputs, now):
    require(record.get('status') == 'preflight-passed', 'Native preflight did not pass')
    require(wrapper.get('status') == 'preflight-passed' and wrapper.get('exitCode') == 0,
            'Preflight wrapper did not pass clean exit/log/protection gates')
    require(wrapper.get('nativeReceiptSha256') == native_hash, 'Preflight receipt not authenticated by wrapper')
    require(record.get('revisionHashes') == current_revision, 'Preflight script/evidence revision changed')
    require(record.get('protectedBefore') == record.get('protectedAfter') == current_inputs,
            'Preflight protected input hashes changed')
    age = (now - datetime.fromisoformat(record['completedUtc'])).total_seconds()
    require(0 <= age <= 3600, 'Preflight must be from this run and within one hour')
    require(record.get('entryNoPIE') == {'world': '/Engine/Maps/Entry', 'gameWorld': None}, 'Missing Entry/no-PIE proof')
    probe = record.get('queries', {})
    require(probe.get('collisionEnabled') is True and probe.get('castShadow') is True,
            'Expected positive collision/shadow query proof')
    require(probe.get('collisionNumeric') == probe.get('shadowNumeric') == 1 and
            probe.get('auditedFunctions') == 5 and record.get('sourceTriangleCount') == 180,
            'Incomplete numeric/query/geometry preflight proof')


def require_preflight(run_id):
    import re
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,48}', run_id) is not None, 'Invalid run ID')
    folder = OUT / run_id / 'preflight'
    native_path, wrapper_path = folder / 'native.json', folder / 'wrapper.json'
    record = json.loads(native_path.read_text(encoding='utf-8-sig'))
    wrapper = json.loads(wrapper_path.read_text(encoding='utf-8-sig'))
    require(record.get('runId') == wrapper.get('runId') == run_id, 'Wrong preflight run')
    validate_preflight_record(record, wrapper, sha(native_path), revision_hashes(),
                              snapshot(sorted(record['protectedBefore'])), datetime.now(timezone.utc))
    require(sha(folder / 'native.log') == wrapper.get('logSha256'), 'Preflight log changed')
    return {'receipt': str(native_path), 'sha256': sha(native_path), 'completedUtc': record['completedUtc']}


def prepare():
    validate_pins()
    triangles = source_triangles()
    roles = [face_role(p) for p in triangles]
    require(set(roles) == {'top', 'side', 'bottom'}, 'Incomplete surface classification')
    # The authoritative receipt supplies a bounded map list, not a Content tree crawl.
    native = json.loads((ROOT / 'SourceAssets/context-review/KotelCutClosureV1/runtime-20260916T173423495Z.json').read_text())
    paths = {Path(p).relative_to(ROOT).as_posix() for p in native['mapHashesBefore']}
    paths.update(str(disk(a).relative_to(ROOT)).replace('\\', '/') for a in PINNED)
    # Hash the small, named material families and texture inputs. The native run also
    # protects the exact project dependency closure resolved by AssetRegistry.
    for folder in ('FutureMountV1/PrecinctPlazaV1/Materials', 'MaterialReview/HerodianAshlarV4',
                   'MaterialReview/JerusalemPavingV2'):
        paths.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'Content/MikdashV3' / folder).rglob('*.uasset'))
    require(sum(p.endswith('.umap') for p in paths) == 20, 'Expected 20 protected map paths')
    report = dict(status='offline-prepared-native-not-run', namespace=NS, source=SOURCE,
                  sourceObj=OBJ, sourceObjSha256=OBJ_SHA, pinnedAssets=PINNED,
                  triangleCount=180, counts=dict(Counter(roles)),
                  policy='Clockwise upward horizontal top = slot 0 original paving; vertical side and downward bottom = slot 1 existing ashlar',
                  protectedPaths=sorted(paths), preparedHashes=snapshot(sorted(paths)),
                  triangles=[dict(index=i, positions=p, role=roles[i], materialId=0 if roles[i]=='top' else 1)
                             for i, p in enumerate(triangles)])
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'source-audit.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=report['status'], triangles=180, counts=report['counts'], protectedFiles=len(paths))))


def check():
    report = json.loads((OUT / 'source-audit.json').read_text())
    triangles = source_triangles()
    require([r['positions'] for r in report['triangles']] == triangles, 'Manifest geometry mismatch')
    require([r['role'] for r in report['triangles']] == [face_role(p) for p in triangles], 'Manifest policy mismatch')
    # Independent export-normal sign check: OBJ Y reflection reverses cross-product
    # handedness; explicit exported normals must agree with classified top/bottom.
    normals = [list(map(float, s.split()[1:])) for s in (ROOT / OBJ).read_text().splitlines() if s.startswith('vn ')]
    require(len(normals) == 180, 'Expected one authored normal per face')
    for row, normal in zip(report['triangles'], normals):
        role = 'top' if normal[2] > .999 else 'bottom' if normal[2] < -.999 else 'side'
        require(role == row['role'], 'Winding/normal classification mismatch')
        require(row['materialId'] == (0 if role == 'top' else 1), 'Wrong material policy')
    # Deliberately reversed winding and a moved corner must never pass exact proof.
    baseline = geometry_counter(triangles)
    changed = [[list(p) for p in t] for t in triangles]
    changed[0][0][0] += .001
    require(geometry_counter(changed) != baseline, 'Moved corner not detected')
    changed = list(triangles)
    changed[0] = list(reversed(changed[0]))
    require(geometry_counter(changed) != baseline, 'Reversed winding not detected')
    require(geometry_counter([t[1:]+t[:1] for t in triangles]) == baseline, 'Cyclic order rejected')
    validate_pins()
    print(json.dumps(dict(status='offline-check-passed-native-not-run', counts=report['counts'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--check-preflight')
    args = parser.parse_args()
    if args.check_preflight:
        print(json.dumps(require_preflight(args.check_preflight)))
    else:
        prepare() if args.prepare else check()

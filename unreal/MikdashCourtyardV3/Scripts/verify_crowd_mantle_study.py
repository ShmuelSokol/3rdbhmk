"""Read back a mantle GLB, prove edit boundaries, then check held-out poses."""
import argparse
import copy
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
import build_crowd_mantle_study as S
from measure_pilgrim_walk import Rig, read_accessor, read_glb


def verify(folder, full=False):
    variant, bones, parts, doc, binary, mapping = S.source_parts()
    path = folder / 'V3_Pilgrim_Man_Standard_MantleStudy.glb'
    candidate_doc, candidate_binary = read_glb(path)
    expected_doc = copy.deepcopy(doc)
    allowed = set()
    changed = {'Mantle', 'MantleHem', 'MantleEdge-1', 'MantleEdge1'}
    changed_accessors = set()
    for part in parts:
        attrs, offset, count = mapping[part['name']]
        if part['name'] in changed:
            names = ['POSITION', 'NORMAL'] + ([] if part['name'] == 'Mantle' else ['JOINTS_0', 'WEIGHTS_0'])
            for name in names:
                acc = doc['accessors'][attrs[name]]
                view = doc['bufferViews'][acc['bufferView']]
                size = 8 if name == 'JOINTS_0' else (16 if name == 'WEIGHTS_0' else 12)
                stride = view.get('byteStride', size)
                start = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
                for i in range(offset, offset + count):
                    allowed.update(range(start + i * stride, start + i * stride + size))
                if name == 'POSITION':
                    changed_accessors.add(attrs[name])
        positions, joints, weights = [np.asarray(read_accessor(candidate_doc, candidate_binary, attrs[name])[offset:offset + count])
                                      for name in ('POSITION', 'JOINTS_0', 'WEIGHTS_0')]
        part['vertices'] = np.column_stack((positions[:, 0], -positions[:, 2], positions[:, 1])) * 100
        part['joints'], part['weights'] = joints.astype(int), weights
        assert np.isfinite(positions).all() and np.isfinite(weights).all()
        assert np.allclose(weights.sum(axis=1), 1, atol=1e-6)
    for idx in changed_accessors:
        positions = np.asarray(read_accessor(candidate_doc, candidate_binary, idx))
        for key, value in [('min', positions.min(axis=0).tolist()), ('max', positions.max(axis=0).tolist())]:
            expected_doc['accessors'][idx][key] = value
    assert candidate_doc == expected_doc, 'Unexpected GLB JSON edits'
    assert len(candidate_binary) == len(binary)
    byte_changes = {i for i, (a, b) in enumerate(zip(binary, candidate_binary)) if a != b}
    assert byte_changes and byte_changes <= allowed, 'Unexpected binary edits'
    rows = []
    for clip in ('Walk', 'Idle'):
        rig = Rig(S.SOURCE, 'A_Pilgrim_Original_' + clip)
        count = round(rig.duration * (240 if clip == 'Walk' else 30)) if full else 8
        for i in range(count):
            time = rig.duration * (i if full else i + 0.5) / count
            result = S.overlap(S.posed(parts, bones, rig, time))
            row = dict(clip=clip, time=time, result=result)
            rows.append(row)
            print(json.dumps(row), flush=True)
    return dict(passed=all(v['insideSamples'] == 0 for r in rows for v in r['result'].values()),
                sourceSha256=hashlib.sha256(S.SOURCE.read_bytes()).hexdigest(),
                candidateSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                binaryChanges=len(byte_changes), exactEditBoundariesPassed=True,
                scope=('Full walk at 240 Hz and idle at 30 Hz, end excluded.' if full else 'Sixteen held-out source poses, halfway between fitting samples.') + ' Tests mantle vertices/face centres against tunic and sash only; not continuous or native animated clearance.', samples=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Fresh verification output required')
    result = verify(args.folder, args.full)
    args.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(0 if result['passed'] else 1)

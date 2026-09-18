"""Read back a beard study and prove its scope against the approved source GLB."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from build_kohen_neck_tone_study import SOURCE, SOURCE_SHA
from measure_pilgrim_walk import read_glb, read_accessor


def verify(path):
    path = Path(path)
    report = json.loads(path.with_suffix('.json').read_text())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    assert hashlib.sha256(path.read_bytes()).hexdigest() == report['outputSha256']
    before, old_binary = read_glb(SOURCE)
    after, new_binary = read_glb(path)
    assert new_binary[:len(old_binary)] == old_binary, 'Original binary changed'
    # Normalize precisely the allowed document edits, then compare everything else.
    normalized = copy.deepcopy(after)
    normalized['accessors'] = normalized['accessors'][:len(before['accessors'])]
    normalized['bufferViews'] = normalized['bufferViews'][:len(before['bufferViews'])]
    normalized['buffers'] = before['buffers']
    matched = 0
    for mi, mesh in enumerate(before['meshes']):
        for pi, old in enumerate(mesh['primitives']):
            if before['materials'][old['material']]['name'] != 'KG_Hair':
                continue
            matched += 1
            new = after['meshes'][mi]['primitives'][pi]
            normalized['meshes'][mi]['primitives'][pi] = old
            arrays = {k: np.asarray(read_accessor(before, old_binary, v)) for k, v in old['attributes'].items()}
            result = {k: np.asarray(read_accessor(after, new_binary, v)) for k, v in new['attributes'].items()}
            assert arrays.keys() == result.keys()
            triangles = np.asarray(read_accessor(before, old_binary, old['indices'])).reshape(-1, 3)
            heights = arrays['POSITION'][:, 1] * 100
            retained = triangles[np.all(heights[triangles] >= report['cutoffCm'], axis=1)]
            used = np.unique(retained)
            remap = np.full(len(heights), -1, dtype=int)
            remap[used] = np.arange(len(used))
            actual = np.asarray(read_accessor(after, new_binary, new['indices'])).reshape(-1, 3)
            assert np.array_equal(actual, remap[retained]), 'Unexpected topology'
            assert len(actual) == report['retainedFaces'] and len(used) == report['retainedVertices']
            for key in arrays.keys() - {'POSITION', 'NORMAL'}:
                assert np.array_equal(result[key], arrays[key][used]), key + ' changed'
            upper = heights[used] >= report['unchangedPositionAtAndAboveCm']
            assert np.array_equal(result['POSITION'][upper], arrays['POSITION'][used][upper]), 'Upper beard moved'
            assert np.isfinite(result['POSITION']).all() and np.isfinite(result['NORMAL']).all()
            assert np.all(np.linalg.norm(result['NORMAL'], axis=1) > .99), 'Degenerate normal'
    assert matched == 1 and normalized == before, 'Unexpected document changes'
    return {'status': 'source-preservation-passed', 'studySha256': report['outputSha256'],
            'proof': 'Read-back confirms all non-beard data, rig, upper beard positions and retained colors/UVs/weights preserved.',
            'limits': 'Native appearance and animation acceptance remain separate.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study')
    args = parser.parse_args()
    print(json.dumps(verify(args.study), indent=2))

"""Offline validation, plus optional read-only native layout receipt validation.

Run with scientific Python, -B. Never imports Unreal or launches a process.
Native bridge receipt is optional; absence always means native validation NOT RUN.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import copy
import itertools
import json
from pathlib import Path
import numpy as np
import study_kohen_cloth_architecture as A


def validate(m):
    assert m['schema'] == 'kohen-cloth-feasibility-v1'
    assert m['sourceSha256'] == A.digest(A.SOURCE)
    assert len(m['bones']) == 27
    assert m['selectedMaterial'] == 'KG_Meil'
    assert m['limits']['noSave'] and m['limits']['noProductionBinding']
    assert [p['name'] for p in m['patterns']] == ['Meil', 'Ketonet', 'ShinR', 'FootR', 'ShinL', 'FootL']
    count = 0
    for n, p in enumerate(m['patterns']):
        v = np.asarray(p['verticesCm'], dtype=float)
        f = np.asarray(p['faces'], dtype=int)
        md = np.asarray(p['maxDistanceCm'])
        assert v.ndim == 2 and v.shape[1] == 3 and np.isfinite(v).all()
        assert f.ndim == 2 and f.shape[1] == 3 and f.min() >= 0 and f.max() < len(v)
        assert len(md) == len(v) and np.isfinite(md).all() and (md >= 0).all()
        assert len(p['boneInfluences']) == len(v)
        assert p['dynamic'] == (n == 0)
        if n:
            assert (md == 0).all()
        else:
            assert (md == 0).any() and (md > 0).any()
        for inf in p['boneInfluences']:
            assert inf and abs(sum(w for _, w in inf) - 1) < 1e-6
            for j, w in inf:
                assert isinstance(j, int) and 0 <= j < 27 and np.isfinite(w) and w > 0
                if n == 0:
                    assert not any(x in m['bones'][j]['name'].lower() for x in ('calf', 'foot', 'thigh'))
        count += len(v)
    assert count <= m['limits']['maxSimulationVertices'] <= 16384
    assert A.digest(A.ROOT / m['walk']['glb']) == m['walk']['animationSha256']
    return count


def native_correspondence(m, r):
    assert r['passed'] and not r['nativeBindingPerformed'] and not r['clothSimulationPerformed']
    assert r['mesh'].startswith('/Game/KohenClothFeasibilityV1/')
    source = {b['name']: b['positionCm'] for b in m['bones']}
    native = {b['name']: b['positionCm'] for b in r['bones']}
    assert set(source) == set(native) and len(native) == 27
    a = np.asarray(list(source.values()))
    b = np.asarray([native[n] for n in source])
    fits = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1, 1), repeat=3):
            error = float(np.linalg.norm(a[:, perm] * signs - b, axis=1).max())
            if error < .05:
                fits.append((perm, signs, error))
    assert len(fits) == 1, 'No unique axis mapping within0.05cm; do not guess.'
    perm, signs, error = fits[0]
    sections = [s for s in r['sections'] if s['importedMaterialSlotName'] == 'KG_Meil']
    assert len(sections) == 1, 'Split/ambiguous native section requires review.'
    p = np.asarray(m['selectedSourceRenderPositionsCm'])[:, perm] * signs
    q = np.asarray(sections[0]['positionsCm'])
    # Quantized multiset includes multiplicity; import splits are not silently waived.
    def points(x):
        return sorted(map(tuple, np.rint(x / .005).astype(np.int64)))
    assert points(p) == points(q), 'Native KG_Meil geometry differs or import split vertices.'
    return dict(axisPermutation=perm, axisSigns=signs, maxBoneErrorCm=error,
                section=sections[0]['index'], renderVertices=len(q),
                scope='Rest layout correspondence only, no binding/cloth/clearance proof.')


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-receipt', type=Path)
    args = parser.parse_args()
    m = json.loads((A.OUT / 'prepared-input.json').read_text())
    count = validate(m)
    refused = []
    for name, mutate in (
        ('bad-source', lambda x: x.update(sourceSha256='0' * 64)),
        ('head-as-dynamic', lambda x: x['patterns'][0].update(name='Head')),
        ('dynamic-inner', lambda x: x['patterns'][1].update(dynamic=True)),
        ('out-of-range-face', lambda x: x['patterns'][0]['faces'][0].__setitem__(0, 999999)),
        ('nonfinite-position', lambda x: x['patterns'][0]['verticesCm'][0].__setitem__(0, float('nan'))),
        ('kinematic-contact-unpinned', lambda x: x['patterns'][1]['maxDistanceCm'].__setitem__(0, 1)),
    ):
        bad = copy.deepcopy(m)
        mutate(bad)
        try:
            validate(bad)
        except AssertionError:
            refused.append(name)
        else:
            raise AssertionError('Unsafe input accepted: ' + name)
    receipt = dict(passed=True, simulationVertices=count, rejectedInvalidInputs=refused,
                   nativeStatus='notrun', clothDrapeStatus='notrun', clearanceStatus='notrun')
    if args.native_receipt:
        receipt['nativeLayout'] = native_correspondence(m, json.loads(args.native_receipt.read_text()))
        receipt['nativeStatus'] = 'layout-only'
    A.save('preflight-checks.json', receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    run()

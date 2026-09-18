"""Offline diagnostic sweep at the measured worst walk pose; never an acceptance gate."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import create_kohen_gadol_v1 as K
import measure_kohen_garment_clearance as M


def measure(offset, time, lower_ease=0.0):
    saved = K.OFF_MEIL
    saved_ease = K.MEIL_LOWER_EASE_CM
    try:
        K.OFF_MEIL = offset
        K.MEIL_LOWER_EASE_CM = lower_ease
        parts = K.Parts()
        K.ketonet(parts)
        K.meil(parts)
    finally:
        K.OFF_MEIL = saved
        K.MEIL_LOWER_EASE_CM = saved_ease
    by_name = {p['name']: p for p in parts.parts}
    bones = M.C.skeleton()
    index = {b['name']: i for i, b in enumerate(bones)}
    robe, outer = by_name['Ketonet'], by_name['Meil']
    rv, rj, rw = M.skin_arrays(robe, K.influence, index)
    ov, oj, ow = M.skin_arrays(outer, K.influence, index)
    _, _, _, nring = M.loft_triangles(robe, K.KETONET_SEGMENTS)
    faces, wall, hem, onring = M.loft_triangles(outer, K.MEIL_SEGMENTS)
    mask = np.zeros(len(rv), dtype=bool)
    mask[:nring] = ((rv[:nring, 2] > ov[hem, 2].max() + 1.5)
                   & (rv[:nring, 2] < min(80, ov[:onring, 2].max() - 3))
                   & ((np.arange(nring) % K.KETONET_SEGMENTS) % 2 == 0))
    clip = M.CLIPS[0]
    rig = M.Rig(clip[1], clip[2])
    a, b = M.joint_affines(rig, rig.pose(time), bones)
    posed_inner = M.skin(rv, rj, rw, a, b)
    posed_outer = M.skin(ov, oj, ow, a, b)
    distances = M.conjunction(posed_inner[mask], posed_outer, faces, wall, hem,
        np.ones(len(faces), dtype=bool), wall, M.tube_signs(ov, wall), M.MEIL_HEM_MARGIN_CM)
    indices = np.flatnonzero(mask)
    hits = np.flatnonzero(distances > 0)
    return {'offsetCm': offset, 'lowerEaseCm': lower_ease,
            'easeFullZ': K.MEIL_EASE_FULL_Z, 'easeZeroZ': K.MEIL_EASE_ZERO_Z,
            'timeSeconds': time, 'maximumCm': float(distances.max()),
            'intersections': [{'vertex': int(indices[i]), 'distanceCm': float(distances[i]),
                               'rest': rv[indices[i]].tolist(),
                               'posed': posed_inner[indices[i]].tolist()} for i in hits]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--offsets', default='2.2,2.8,3.4')
    parser.add_argument('--time', type=float, default=71 / 240)
    parser.add_argument('--lower-ease', type=float, default=0.0)
    parser.add_argument('--full', action='store_true', help='Measure all clips with candidate lower ease')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        raise RuntimeError('Fresh output required')
    if args.full:
        saved_ease = K.MEIL_LOWER_EASE_CM
        try:
            K.MEIL_LOWER_EASE_CM = args.lower_ease
            report = M.run('kohen')
        finally:
            K.MEIL_LOWER_EASE_CM = saved_ease
        report['candidateLowerEaseCm'] = args.lower_ease
        report['easeFullZ'] = K.MEIL_EASE_FULL_Z
        report['easeZeroZ'] = K.MEIL_EASE_ZERO_Z
        report['generatorSha256'] = hashlib.sha256(Path(K.__file__).read_bytes()).hexdigest()
        report['acceptanceScope'] = 'Candidate generator only; not exported, native or rendered acceptance'
        out.write_text(json.dumps(report, indent=2) + '\n')
    else:
        rows = [measure(float(offset), args.time, args.lower_ease) for offset in args.offsets.split(',')]
        out.write_text(json.dumps({'scope': 'Single-pose diagnostic only; no source edits or acceptance',
                                   'rows': rows}, indent=2) + '\n')
        print(json.dumps([{k: v for k, v in row.items() if k != 'intersections'} for row in rows]))

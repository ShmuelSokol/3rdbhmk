"""Measure an isolated garment skinning candidate; never mutate production assets."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import create_kohen_gadol_v1 as K
import measure_kohen_garment_clearance as M


def run(top, bottom, clips, rate_scale=1.0):
    if not all(math.isfinite(v) for v in (top, bottom, rate_scale)):
        raise ValueError('Finite settings required')
    if not 5 <= bottom < top <= K.F_FULL or not 0 < rate_scale <= 1:
        raise ValueError('Knee range must stay within lower garment; rate scale in (0,1]')
    if not clips or any(c not in ('walk', 'tend', 'idle') for c in clips):
        raise ValueError('Explicit walk/tend/idle clips required')
    before = K.KNEE_TOP, K.KNEE_BOT
    try:
        K.KNEE_TOP, K.KNEE_BOT = top, bottom
        report = M.run('kohen', rate_scale=rate_scale, clips=clips)
    finally:
        K.KNEE_TOP, K.KNEE_BOT = before
    report['candidate'] = dict(kneeTopCm=top, kneeBottomCm=bottom,
        productionKneeTopCm=before[0], productionKneeBottomCm=before[1],
        lowerEaseCm=K.MEIL_LOWER_EASE_CM, hemBandCm=K.BAND_HEM)
    report['scope'] = ('Full configured sampling of selected clips; generator candidate only'
        if rate_scale == 1 else 'Sparse diagnostic only; not full-clip clearance acceptance')
    report['limitations'] = ['No exported/native geometry or rendered acceptance.',
        'Existing measurement covers legs/ketonet and ketonet/meil, not every garment layer.']
    report['sourceHashes'] = {Path(p).name: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        for p in (K.__file__, M.__file__, __file__)}
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--top', type=float, required=True)
    parser.add_argument('--bottom', type=float, required=True)
    parser.add_argument('--clips', required=True)
    parser.add_argument('--rate-scale', type=float, default=1.0)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    # Reserve the evidence name before measurement; an interrupted empty file
    # must be retained and a retry must choose a fresh destination.
    with args.out.open('x', encoding='utf-8') as handle:
        report = run(args.top, args.bottom, args.clips.split(','), args.rate_scale)
        json.dump(report, handle, indent=2)
        handle.write('\n')

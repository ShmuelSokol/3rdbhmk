"""Offline check of the approach flank retaining against the world band grid (cp19, 11 Sep 2026).

The cp17b P2 frame showed the south face at the S1 approach "stepping down as a staircase of ledges".
Cause: release_precinct_approaches.Plan._stack started each 25-amah flank column at its own tread Z and
battered by the band index counted from that tread, so joints and ledges fell one tread lower every column.
This runs the planner on the frozen level grid (no engine) and reports, for every approach:
  offGridBands        band tops not on deck - k*h (the precinct ring's own levels)      -> must be 0
  distinctLedgeZ      Z levels at which a flank face steps out                            -> multiples of 5h only
  faceSpreadCm        per ledge-group, spread of the face offset (along the flank normal) across columns -> 0
  washes              rolled ledge-wash instances
  python Scripts/check_approach_band_grid.py [--out <json>]
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_precinct_approaches as A   # noqa: E402


def main():
    cfg = A.target_config('Candidate48')
    height, prov = A.offline_height(False)
    plan = A.Plan(cfg).build(height)
    h = plan.band_h
    deck = plan.deck_z
    boxes = {'S1': (-29280.0, 109776.0, 18624.0, 116064.0), 'S2': (44352.0, 109776.0, 66624.0, 115872.0),
             'E': (109824.0, -2400.0, 122640.0, 2400.0), 'N': (-2400.0, -39456.0, 2400.0, -29424.0)}
    out = {'provenance': str(prov)[:200], 'bandHeightCm': h, 'deckZcm': deck, 'counts': {
        'bands': sum(1 for r in plan.bands if r[4] == 'band'),
        'washes': sum(1 for r in plan.bands if r[4] == 'bandWash')}, 'approaches': {}}
    for aid, (x0, y0, x1, y1) in boxes.items():
        rows = [r for r in plan.bands if x0 - 2000 <= r[0] <= x1 + 2000 and y0 - 2000 <= r[1] <= y1 + 2000]
        bands = [r for r in rows if r[4] == 'band']
        off = [r for r in bands if abs(((deck - r[2]) / h) - round((deck - r[2]) / h)) > 1e-6]
        # group bands into stacks by (yaw, position along the flank): quantise the along-flank coordinate
        stacks = defaultdict(list)
        for r in bands:
            yaw = round(r[3], 3)
            # flank normal from yaw: local +Y = (-sin yaw, cos yaw)
            ny = (-math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
            along = round(r[0] * ny[1] - r[1] * ny[0], -2)
            stacks[(yaw, along)].append((r[2], r[0] * ny[0] + r[1] * ny[1]))
        ledge_z = set()
        by_level = defaultdict(list)       # (yaw, band level k) -> face offsets across stacks
        for (yaw, along), items in stacks.items():
            items.sort(key=lambda t: -t[0])
            for (za, fa), (zb, fb) in zip(items, items[1:]):
                if fb - fa > 1.0:
                    ledge_z.add(round(zb, 1))
            for z, f in items:
                by_level[(yaw, round((deck - z) / h, 3))].append(f)
        spread = max((max(v) - min(v) for v in by_level.values() if len(v) > 1), default=0.0)
        out['approaches'][aid] = {
            'bands': len(bands), 'washes': len(rows) - len(bands), 'offGridBands': len(off),
            'distinctLedgeZ': sorted(ledge_z, reverse=True)[:40], 'distinctLedgeZCount': len(ledge_z),
            'ledgeZNotOnBatterGrid': [z for z in ledge_z if abs(((deck - z) / (5 * h)) - round((deck - z) / (5 * h))) > 1e-6][:20],
            'faceSpreadCmSameLevelAcrossColumns': round(spread, 3)}
    out['summary'] = plan.summary()
    txt = json.dumps(out, indent=1, default=str)
    if '--out' in sys.argv:
        Path(sys.argv[sys.argv.index('--out') + 1]).write_text(txt, encoding='utf-8')
    print(txt[:6000])


if __name__ == '__main__':
    main()

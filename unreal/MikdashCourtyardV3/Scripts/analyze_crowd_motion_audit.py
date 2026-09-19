"""Recompute logged live root-history errors independently of the native audit."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def fields(line):
    return dict(re.findall(r'(\w+)=(\([^)]*\)|[^\s]+)', line))


def vector(value):
    result = tuple(map(float, value.strip('()').split(',')))
    if len(result) != 3 or not all(map(math.isfinite, result)):
        raise ValueError('Invalid vector')
    return result


def number(data, key):
    value = float(data[key])
    if not math.isfinite(value):
        raise ValueError('Non-finite scalar: ' + key)
    return value


def analyze(path):
    raw = path.read_bytes()
    lines = raw.decode('utf-8-sig', errors='strict').splitlines()
    summaries = [fields(line) for line in lines if 'CrowdMotionAuditV1 complete ' in line]
    if len(summaries) != 1 or int(summaries[0]['samples']) != 4096:
        raise ValueError('Expected one complete 4096-update audit')
    summary = summaries[0]
    for counter in ('rootErrorsOverPointOneCm', 'headingChangesOverPointOneDegree'):
        if not 0 <= int(summary[counter]) <= 4096:
            raise ValueError('Invalid summary count: ' + counter)
    if not 0 <= int(summary['logged']) <= 64:
        raise ValueError('Invalid logged count')
    rows = []
    for line in lines:
        if 'CrowdMotionAuditV1 sample=' not in line:
            continue
        data = fields(line)
        now, frame = number(data, 'now'), number(data, 'frame')
        if not 0 < frame <= 1:
            raise ValueError('Invalid frame time')
        previous = now - frame
        roots = []
        for prefix in ('old', 'new'):
            pos, vel = vector(data[prefix + 'Pos']), vector(data[prefix + 'Vel'])
            horizon, anchor_time = number(data, prefix + 'Horizon'), number(data, prefix + 'Time')
            if horizon < 0:
                raise ValueError('Negative horizon')
            dt = min(horizon, max(-.25, previous - anchor_time))
            roots.append(tuple(p + v * dt for p, v in zip(pos, vel)))
        if not all(math.isfinite(c) for root in roots for c in root):
            raise ValueError('Non-finite reconstructed root')
        error = math.dist(*roots)
        if not math.isfinite(error):
            raise ValueError('Non-finite reconstructed error')
        native_error = number(data, 'rootErrorCm')
        if native_error < 0:
            raise ValueError('Negative error')
        residual = abs(error - native_error)
        if residual > .001:
            raise ValueError('Native root error differs from independent reconstruction')
        heading = abs((number(data, 'newYaw') - number(data, 'oldYaw') + 180) % 360 - 180)
        native_heading = number(data, 'headingDelta')
        if not math.isfinite(heading) or not 0 <= native_heading <= 180 or abs(heading - native_heading) > .001:
            raise ValueError('Heading delta mismatch')
        rows.append(dict(sample=int(data['sample']), agent=int(data['agent']), zone=int(data['zone']),
                         frameSeconds=frame, rootErrorCm=error, headingChangeDegrees=heading,
                         residualCm=residual, oldIdle=int(data['oldIdle']), newIdle=int(data['newIdle']),
                         oldVelocityCmPerSecond=vector(data['oldVel']), newVelocityCmPerSecond=vector(data['newVel'])))
    indices = [r['sample'] for r in rows]
    if len(rows) != int(summary['logged']) or len(rows) > 64 or indices != sorted(set(indices)):
        raise ValueError('Invalid bounded sample set')
    if any(not 1 <= i <= 4096 for i in indices):
        raise ValueError('Sample outside audit window')
    maximum = number(summary, 'maxRootErrorCm')
    if maximum < 0 or any(r['rootErrorCm'] > maximum + .001 for r in rows):
        raise ValueError('Invalid maximum error')
    return dict(status='live-root-model-recomputed-not-pixel-velocity-acceptance',
                logSha256=hashlib.sha256(raw).hexdigest(), nativeSummary=summary,
                samples=rows, maximumRecomputationResidualCm=max((r['residualCm'] for r in rows), default=0),
                limitations=['First 4096 simulated social updates after two seconds, not all visitors or a long-run frequency',
                             'Only first 64 changed rows retained; summary counters cannot all be reconstructed from them',
                             'Uses authored -0.25 second material clamp; excludes VAT vertex/phase/blend deformation',
                             'Not a velocity-buffer measurement or visual smearing fix'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('log', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.log)
    with args.out.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2)
        handle.write('\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'samples'}, indent=2))

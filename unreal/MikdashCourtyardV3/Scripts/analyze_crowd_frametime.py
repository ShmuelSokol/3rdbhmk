"""Summarise CSV-profiler frame-time captures from Scripts/capture_crowd_frametime.ps1.

Drops the settle window by cumulative FrameTime (the capture starts at boot), then reports
median / mean / p95 / p99 of FrameTime, GameThreadTime, RenderThreadTime and GPU time over the
record window, per capture, and the crowd-on minus crowd-off deltas when both are given.

    python Scripts/analyze_crowd_frametime.py --settle 45 <csv> [<csv> ...] [--pair ON OFF --pair ON OFF] [--out receipt.json]
"""
import argparse
import csv
import json
import math
import statistics
from pathlib import Path

# The CSV profiler's EVENTS column and its metadata footer carry fields far larger than csv's
# default 131072-byte limit (measured on the cp17 capture). 32-bit Python: sys.maxsize overflows here.
csv.field_size_limit(2 ** 31 - 1)

WANTED = {
    'frame': ('FrameTime',),
    'game': ('GameThreadTime',),
    'render': ('RenderThreadTime',),
    'gpu': ('GPUTime', 'GPU/Total', 'GPU0Time', 'GpuTime'),
    'rhi': ('RHIThreadTime',),
}


def _pct(values, p):
    if not values:
        return None
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, int(round(p / 100.0 * (len(ordered) - 1)))))
    return round(ordered[k], 3)


def summarise(path, settle, record=None):
    with open(path, newline='', encoding='utf-8', errors='replace') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    index = {}
    for key, names in WANTED.items():
        for name in names:
            if name in header:
                index[key] = header.index(name)
                break
    if 'frame' not in index:
        raise RuntimeError('%s: no FrameTime column; header starts %r' % (path, header[:12]))
    data = {k: [] for k in index}
    elapsed = 0.0
    kept = 0
    window_seconds = 0.0
    for row in rows[1:]:
        if not row or row == header or row[0].startswith('['):
            continue
        try:
            frame = float(row[index['frame']])
        except (ValueError, IndexError) as exc:
            raise RuntimeError('%s: malformed frame row' % path) from exc
        if not math.isfinite(frame) or frame <= 0:
            raise RuntimeError('%s: invalid frame time %r' % (path, frame))
        start = elapsed
        elapsed += frame / 1000.0
        if start + 1e-9 < settle:
            continue
        if record is not None and start >= settle + record - 1e-9:
            break
        kept += 1
        window_seconds += frame / 1000.0
        for key, col in index.items():
            try:
                value = float(row[col])
                if not math.isfinite(value) or value < 0:
                    raise ValueError('invalid metric')
                data[key].append(value)
            except (ValueError, IndexError) as exc:
                raise RuntimeError('%s: invalid %s metric' % (path, key)) from exc
    if record is not None and elapsed + 1e-9 < settle + record:
        raise RuntimeError('%s: capture ends at %.3fs; need %.3fs' % (path, elapsed, settle + record))
    if not kept or (record is not None and window_seconds < record * 0.99):
        raise RuntimeError('%s: insufficient complete-frame coverage of analysis window' % path)
    out = dict(file=str(path), columns={k: header[c] for k, c in index.items()}, framesKept=kept,
               recordSeconds=round(window_seconds, 2), requestedRecordSeconds=record)
    for key, values in data.items():
        if values:
            out[key] = dict(median=round(statistics.median(values), 3), mean=round(statistics.mean(values), 3),
                            p95=_pct(values, 95), p99=_pct(values, 99))
    if data.get('frame'):
        out['fpsFromMedian'] = round(1000.0 / statistics.median(data['frame']), 1)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csvs', nargs='*')
    parser.add_argument('--settle', type=float, default=45.0)
    parser.add_argument('--record', type=float, help='Fixed analysis window; fail if capture is too short')
    parser.add_argument('--pair', nargs=2, action='append', default=[], metavar=('ON', 'OFF'))
    parser.add_argument('--out')
    args = parser.parse_args()
    if args.settle < 0 or not math.isfinite(args.settle) or (args.record is not None and (args.record <= 0 or not math.isfinite(args.record))):
        parser.error('settle must be finite and nonnegative; record must be finite and positive')
    files = list(dict.fromkeys(list(args.csvs) + [p for pair in args.pair for p in pair]))
    results = {f: summarise(Path(f), args.settle, args.record) for f in files}
    deltas = []
    for on, off in args.pair:
        a, b = results[on], results[off]
        row = dict(on=on, off=off)
        for key in ('frame', 'game', 'render', 'gpu'):
            if key in a and key in b:
                row[key + 'MedianDeltaMs'] = round(a[key]['median'] - b[key]['median'], 3)
                row[key + 'P95DeltaMs'] = round(a[key]['p95'] - b[key]['p95'], 3)
        deltas.append(row)
    report = dict(settleSeconds=args.settle, requestedRecordSeconds=args.record, captures=results, crowdCostDeltas=deltas)
    text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(text + '\n', encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()

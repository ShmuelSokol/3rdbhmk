"""Summarise CSV-profiler frame-time captures from Scripts/capture_crowd_frametime.ps1.

Drops the settle window by cumulative FrameTime (the capture starts at boot), then reports
median / mean / p95 / p99 of FrameTime, GameThreadTime, RenderThreadTime and GPU time over the
record window, per capture, and the crowd-on minus crowd-off deltas when both are given.

    python Scripts/analyze_crowd_frametime.py --settle 45 <csv> [<csv> ...] [--pair ON OFF --pair ON OFF] [--out receipt.json]
"""
import argparse
import csv
import json
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


def summarise(path, settle):
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
    for row in rows[1:]:
        if len(row) <= index['frame'] or row[0].startswith('['):
            continue
        try:
            frame = float(row[index['frame']])
        except ValueError:
            continue
        elapsed += frame / 1000.0
        if elapsed < settle:
            continue
        kept += 1
        for key, col in index.items():
            try:
                data[key].append(float(row[col]))
            except (ValueError, IndexError):
                pass
    out = dict(file=str(path), columns={k: header[c] for k, c in index.items()}, framesKept=kept,
               recordSeconds=round(elapsed - settle, 2) if elapsed > settle else 0.0)
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
    parser.add_argument('--pair', nargs=2, action='append', default=[], metavar=('ON', 'OFF'))
    parser.add_argument('--out')
    args = parser.parse_args()
    files = list(dict.fromkeys(list(args.csvs) + [p for pair in args.pair for p in pair]))
    results = {f: summarise(Path(f), args.settle) for f in files}
    deltas = []
    for on, off in args.pair:
        a, b = results[on], results[off]
        row = dict(on=on, off=off)
        for key in ('frame', 'game', 'render', 'gpu'):
            if key in a and key in b:
                row[key + 'MedianDeltaMs'] = round(a[key]['median'] - b[key]['median'], 3)
                row[key + 'P95DeltaMs'] = round(a[key]['p95'] - b[key]['p95'], 3)
        deltas.append(row)
    report = dict(settleSeconds=args.settle, captures=results, crowdCostDeltas=deltas)
    text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(text + '\n', encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()

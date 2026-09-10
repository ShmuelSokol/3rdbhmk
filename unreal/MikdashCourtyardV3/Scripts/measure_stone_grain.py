"""Compare a stone albedo against the APPROVED Jerusalem paving on the two axes that decide whether a
surface reads as rock or as rendered plaster: hue and micro-contrast. Offline, stdlib only.

Why this exists: cp05b-01 puts the Azarah paving and the Herodian wall in ONE frame under ONE light,
and the paving reads as stone while the wall does not. Same-frame comparison is the only reliable
judgement here, so the offline numbers have to be measured the same way on both - at a MATCHED spatial
resolution, because the two source images are authored at different px/cm (paving 2.51, wall 6.83) and
every high-frequency metric is meaningless until that is equalised.

    python Scripts/measure_stone_grain.py [--px-per-cm 2.5] [extra.png=<cmPerSide> ...]

Reports per image, after box-downsampling to the common px/cm:
    mean sRGB, G/R, B/R            - hue. Meleke is a pale cream-honey; B/R near 0.7 is orange.
    luminance std                  - overall value spread
    |laplacian| mean / p99         - micro-contrast at ~1 cm, i.e. the pitting that says 'rock'.
                                     This is the number the V4 wall lost by 18x.
"""
import argparse
import struct
import zlib
from array import array
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# image -> centimetres across the whole tile (its authored world size)
DEFAULT_IMAGES = {
    'SourceAssets/visual-review/JerusalemPavingV1/jerusalem-paving-albedo.png': 500.0,
    'SourceAssets/material-review/HerodianAshlarV4/T_HerodianV4_Ashlar_Albedo.png': 300.0,
    'SourceAssets/material-review/HerodianAshlarV5/T_HerodianV5_Ashlar_Albedo.png': 300.0,
    'SourceAssets/material-review/HerodianAshlarV4/T_HerodianV4_Trim_Albedo.png': 300.0,
    'SourceAssets/material-review/HerodianAshlarV5/T_HerodianV5_Trim_Albedo.png': 300.0,
}


def decode_png_rgb8(path):
    data = Path(path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path
    pos, idat, width, height, channels = 8, [], None, None, None
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b'IHDR':
            width, height, depth, colour, _, _, interlace = struct.unpack('>IIBBBBB', body)
            assert depth == 8 and colour in (2, 6) and interlace == 0, 'unsupported PNG layout: %s' % path
            channels = 3 if colour == 2 else 4
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
    raw = zlib.decompress(b''.join(idat))
    stride = width * channels
    previous, rows, offset = bytearray(stride), [], 0
    for _ in range(height):
        f = raw[offset]
        line = bytearray(raw[offset + 1:offset + 1 + stride])
        offset += 1 + stride
        if f == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 255
        elif f == 3:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + previous[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                c = previous[i - channels] if i >= channels else 0
                b = previous[i]
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        elif f != 0:
            raise RuntimeError('filter %d' % f)
        rows.append(line)
        previous = line
    return width, height, channels, rows


def downsample_to(width, height, channels, rows, target):
    """Box filter to target x target. Averaging is what a mip does, which is the point."""
    out = [array('f', bytes(4 * target * 3)) for _ in range(target)]
    counts = [array('f', bytes(4 * target)) for _ in range(target)]
    sy = target / float(height)
    sx = target / float(width)
    for y in range(height):
        oy = min(target - 1, int(y * sy))
        orow, crow, src = out[oy], counts[oy], rows[y]
        for x in range(width):
            ox = min(target - 1, int(x * sx))
            base = x * channels
            orow[3 * ox] += src[base]
            orow[3 * ox + 1] += src[base + 1]
            orow[3 * ox + 2] += src[base + 2]
            crow[ox] += 1.0
    for y in range(target):
        orow, crow = out[y], counts[y]
        for x in range(target):
            n = crow[x] or 1.0
            orow[3 * x] /= n * 255.0
            orow[3 * x + 1] /= n * 255.0
            orow[3 * x + 2] /= n * 255.0
    return out


def percentile(values, p):
    values = sorted(values)
    if not values:
        return 0.0
    k = min(len(values) - 1, max(0, int(round((p / 100.0) * (len(values) - 1)))))
    return values[k]


def stats(rows, n):
    total = [0.0, 0.0, 0.0]
    lum = [array('f', bytes(4 * n)) for _ in range(n)]
    for y in range(n):
        r = rows[y]
        lr = lum[y]
        for x in range(n):
            a, b, c = r[3 * x], r[3 * x + 1], r[3 * x + 2]
            total[0] += a
            total[1] += b
            total[2] += c
            lr[x] = 0.2126 * a + 0.7152 * b + 0.0722 * c
    count = float(n * n)
    mean = [t / count for t in total]
    lmean = sum(sum(row) for row in lum) / count
    lvar = sum((v - lmean) ** 2 for row in lum for v in row) / count
    lap = []
    for y in range(1, n - 1):
        up, mid, dn = lum[y - 1], lum[y], lum[y + 1]
        for x in range(1, n - 1):
            lap.append(abs(4.0 * mid[x] - up[x] - dn[x] - mid[x - 1] - mid[x + 1]))
    return {'meanSRGB': [round(v, 4) for v in mean],
            'GoverR': round(mean[1] / max(1e-6, mean[0]), 4),
            'BoverR': round(mean[2] / max(1e-6, mean[0]), 4),
            'luminanceMean': round(lmean, 4), 'luminanceStd': round(lvar ** 0.5, 4),
            'absLaplacianMean': round(sum(lap) / max(1, len(lap)), 5),
            'absLaplacianP99': round(percentile(lap, 99), 5)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--px-per-cm', type=float, default=2.5,
                    help='common sampling resolution; 2.5 is the approved paving native rate')
    ap.add_argument('extra', nargs='*', help='path=cmPerSide')
    args = ap.parse_args()

    images = dict(DEFAULT_IMAGES)
    for item in args.extra:
        path, _, cm = item.partition('=')
        images[path] = float(cm or 300.0)

    print('matched at %.2f px/cm (box-downsampled, which is what a mip does)\n' % args.px_per_cm)
    header = '%-46s %-22s %6s %6s %7s %9s %9s' % ('image', 'mean sRGB', 'G/R', 'B/R', 'lumStd', '|lap|mean', '|lap|p99')
    print(header)
    print('-' * len(header))
    out = {}
    for path, cm in images.items():
        full = ROOT / path
        if not full.exists():
            print('%-46s  (missing)' % Path(path).name)
            continue
        w, h, ch, rows = decode_png_rgb8(full)
        target = max(16, int(round(cm * args.px_per_cm)))
        s = stats(downsample_to(w, h, ch, rows, target), target)
        out[path] = dict(s, cmPerSide=cm, sourcePx=w, sampledPx=target)
        print('%-46s %-22s %6.3f %6.3f %7.4f %9.5f %9.5f' % (
            Path(path).name, '/'.join('%.3f' % v for v in s['meanSRGB']),
            s['GoverR'], s['BoverR'], s['luminanceStd'], s['absLaplacianMean'], s['absLaplacianP99']))
    return out


if __name__ == '__main__':
    main()

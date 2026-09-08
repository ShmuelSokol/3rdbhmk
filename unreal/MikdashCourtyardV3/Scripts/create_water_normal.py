"""Tiling water normal map for M_MikdashWaterV1_Water - offline, stdlib only.

The water pass shipped with T_Plaster_Normal as a stand-in (release_water.spec.json
materials.water.normalCandidates[0], "this project has no water normal"). This writes a real one:
  SourceAssets/water-review/textures/T_Water_Normal.png           2048 x 2048, seamless
  SourceAssets/water-review/textures/previews/T_Water_Normal_1024.png
  SourceAssets/water-review/textures/previews/Lit_Water_1024.png  software shading check
  SourceAssets/water-review/textures/water-normal-manifest.json   parameters, hash, statistics, spec hand-off

Surface model (heights in texture units, all wave vectors integer cycles per tile so the map wraps):
  * swell:      3 long low sine trains, 2-4 cycles per tile, within +-20 deg of the flow, gently Gerstner-sharpened;
  * wind waves: 5 shorter trains, 7-13 cycles per tile, spread +-50 deg around the flow direction (30 deg);
  * ripple:     periodic value-noise fBm (grids 32..512), small amplitude, slightly stretched along the
                flow so the fine layer reads as wind ripple rather than as sand.
Normal = normalize(-dh/du, -dh/dv, 1) with u = column, v = row index (DirectX / UE default green;
import with flip_green_channel False). Amplitude is moderate on purpose: the material adds a second
2.7x-tiled sample and halves the sum, then refracts by IOR 1.333; a xy deviation p95 near 0.25-0.30
gives visible ripple without turning the stream into a shattered mirror.

Spec hand-off for the coordinator (release_water.py pick_texture loads an EXISTING /Game asset; it
does not import PNGs):
  1. import this PNG to /Game/MikdashV3/MaterialReview/MikdashWaterV1/Textures/T_Water_Normal
     (TC_Normalmap, sRGB off, flip_green_channel False, TEXTUREGROUP_WORLD_NORMAL_MAP);
  2. put {"path": that asset path, "kind": "authored tiling water normal (create_water_normal.py)"}
     FIRST in Scripts/release_water.spec.json materials.water.normalCandidates (index 0), keeping the
     plaster entry as the fallback at index 1;
  3. re-run the water material stage; the receipt's materials.water.normalTexture must read the new path.
Run:
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\ThirdParty\\Python3\\Win64\\python.exe" Scripts\\create_water_normal.py [--size 512]
"""
import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_limestone_textures_v2 import PeriodicNoise, downsample2, normal_stats, write_png_rgb, linear_to_srgb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets' / 'water-review' / 'textures'
WATER_SPEC = ROOT / 'Scripts' / 'release_water.spec.json'
ASSET_PATH = '/Game/MikdashV3/MaterialReview/MikdashWaterV1/Textures/T_Water_Normal'
SEED = 4707                     # Yechezkel 47 : 7
PARAMS = {
    'swell': {'count': 3, 'cyclesPerTile': (2, 4), 'amplitude': 0.0052, 'spreadDeg': 20.0, 'sharpen': 0.25},
    'wind': {'count': 5, 'cyclesPerTile': (7, 13), 'amplitude': 0.0016, 'spreadDeg': 50.0, 'sharpen': 0.15},
    'ripple': {'grids': (32, 64, 128, 256, 512), 'amplitude': 0.0009, 'stretch': 1.6},
    'flowDirectionDeg': 30.0,
}


def build(size, params, rng, log):
    t0 = time.time()
    flow = math.radians(params['flowDirectionDeg'])
    trains = []
    for key in ('swell', 'wind'):
        p = params[key]
        for i in range(p['count']):
            ang = flow + math.radians(rng.uniform(-p['spreadDeg'], p['spreadDeg']))
            cycles = rng.uniform(*p['cyclesPerTile'])
            kx = round(cycles * math.cos(ang))
            ky = round(cycles * math.sin(ang))
            if kx == 0 and ky == 0:
                kx = 1
            amp = p['amplitude'] * rng.uniform(0.7, 1.3) / (1.0 + 0.15 * i)
            trains.append(dict(kind=key, kx=kx, ky=ky, amp=amp, phase=rng.uniform(0, 2 * math.pi), sharpen=p['sharpen']))
    rp = params['ripple']
    noises = [PeriodicNoise(random.Random(rng.random()), g, size) for g in rp['grids']]
    log('  %d wave trains, %d ripple octaves' % (len(trains), len(noises)))

    two_pi = 2.0 * math.pi
    # per-column phase increments for each train
    col_phase = [[two_pi * t['kx'] * (x + 0.5) / size for x in range(size)] for t in trains]
    height = []
    for y in range(size):
        row = [0.0] * size
        for t, cp in zip(trains, col_phase):
            py = two_pi * t['ky'] * (y + 0.5) / size + t['phase']
            a, s = t['amp'], t['sharpen']
            if s:
                row = [h + a * (math.sin(c + py) + s * math.sin(2.0 * (c + py) + 0.5)) for h, c in zip(row, cp)]
            else:
                row = [h + a * math.sin(c + py) for h, c in zip(row, cp)]
        # ripple: fBm of the periodic octaves; the stretch is applied by sampling a compressed row index
        # (still periodic because size is a multiple of every grid)
        r = [0.0] * size
        w = 1.0
        for n in noises:
            nr = n.row(int(y / rp['stretch']) % size)
            r = [a + w * v for a, v in zip(r, nr)]
            w *= 0.55
        row = [h + rp['amplitude'] * v for h, v in zip(row, r)]
        height.append(row)
    log('  height %.1fs' % (time.time() - t0))

    normal_rows = []
    inv2 = size / 2.0          # slopes in texture units: dh / (2 px), px = 1/size
    for y in range(size):
        up, dn, row = height[(y - 1) % size], height[(y + 1) % size], height[y]
        out = bytearray(3 * size)
        for x in range(size):
            gx = (row[(x + 1) % size] - row[x - 1]) * inv2
            gy = (dn[x] - up[x]) * inv2
            inv = 1.0 / math.sqrt(gx * gx + gy * gy + 1.0)
            out[3 * x] = int(-gx * inv * 127.5 + 127.5 + 0.5)
            out[3 * x + 1] = int(-gy * inv * 127.5 + 127.5 + 0.5)
            out[3 * x + 2] = min(255, int(inv * 127.5 + 127.5 + 0.5))
        normal_rows.append(out)
    log('  normal %.1fs' % (time.time() - t0))
    return normal_rows, trains, time.time() - t0


def lit(normal_rows):
    """Glassy shading check: deep-water colour plus a sun highlight from the normals."""
    lx, ly, lz = -0.4, -0.5, 0.77
    n = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / n, ly / n, lz / n
    out = []
    for nr in normal_rows:
        o = bytearray(len(nr))
        for x in range(len(nr) // 3):
            i = 3 * x
            nx, ny, nz = nr[i] / 127.5 - 1.0, nr[i + 1] / 127.5 - 1.0, nr[i + 2] / 127.5 - 1.0
            ndl = max(0.0, nx * lx + ny * ly + nz * lz)
            spec = ndl ** 60 * 0.9
            base = 0.35 + 0.65 * ndl
            o[i] = int(linear_to_srgb(0.03 * base + spec) * 255 + 0.5)
            o[i + 1] = int(linear_to_srgb(0.13 * base + spec) * 255 + 0.5)
            o[i + 2] = int(linear_to_srgb(0.19 * base + spec) * 255 + 0.5)
        out.append(o)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--size', type=int, default=2048)
    ap.add_argument('--out', type=Path, default=OUT)
    args = ap.parse_args(argv)
    if args.size & (args.size - 1) or args.size < 512:
        raise SystemExit('size must be a power of two >= 512 (ripple grids up to 512 must divide it)')
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()

    def log(msg):
        print(msg, flush=True)

    log('water normal at %d' % args.size)
    rows, trains, seconds = build(args.size, PARAMS, random.Random(SEED), log)
    suffix = '' if args.size == 2048 else '_%d' % args.size
    png = out / ('T_Water_Normal%s.png' % suffix)
    digest = write_png_rgb(png, args.size, args.size, rows)
    stats = normal_stats(rows)
    log('  stats %s' % stats)
    pv = downsample2(rows) if args.size > 1024 else rows
    psize = args.size // 2 if args.size > 1024 else args.size
    preview = out / 'previews' / ('T_Water_Normal_%d.png' % psize)
    preview_sha = write_png_rgb(preview, psize, psize, pv)
    lit_path = out / 'previews' / ('Lit_Water_%d.png' % psize)
    lit_sha = write_png_rgb(lit_path, psize, psize, lit(pv))
    spec_note = None
    if WATER_SPEC.exists():
        spec = json.loads(WATER_SPEC.read_text(encoding='utf-8-sig'))
        current = spec['materials']['water']['normalCandidates'][0]['path']
        spec_note = {'file': 'Scripts/release_water.spec.json', 'key': 'materials.water.normalCandidates[0]', 'currentlyPointsAt': current,
                     'shouldPointAt': ASSET_PATH, 'edited': False, 'note': 'Not edited by this script (spec is owned by the water pass). Coordinator: import the PNG, then insert the entry at index 0.'}
    manifest = {
        'status': 'OFFLINE_GENERATED_NATIVE_IMPORT_PENDING', 'generator': 'Scripts/create_water_normal.py',
        'generatorSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'seed': SEED, 'size': args.size, 'seconds': round(time.time() - started, 1),
        'parameters': PARAMS, 'waveTrains': trains,
        'file': {'path': str(png.relative_to(ROOT)) if png.is_relative_to(ROOT) else str(png), 'sha256': digest, 'bytes': png.stat().st_size},
        'previews': {'normal': {'path': str(preview.relative_to(ROOT)) if preview.is_relative_to(ROOT) else str(preview), 'sha256': preview_sha},
                     'lit': {'path': str(lit_path.relative_to(ROOT)) if lit_path.is_relative_to(ROOT) else str(lit_path), 'sha256': lit_sha}},
        'statistics': stats,
        'convention': 'normalize(-dh/du, -dh/dv, 1), u = column, v = row (DirectX / UE default); import flip_green_channel False, TC_Normalmap, sRGB off',
        'importTarget': ASSET_PATH,
        'specHandOff': spec_note,
        'candidateEntry': {'path': ASSET_PATH, 'kind': 'authored tiling water normal (create_water_normal.py): 3 swell + 5 wind trains + periodic ripple fBm, moderate amplitude; source SourceAssets/water-review/textures/T_Water_Normal.png sha256 ' + digest},
    }
    mp = out / ('water-normal-manifest%s.json' % suffix)
    mp.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    log('manifest ' + str(mp))
    return manifest


if __name__ == '__main__':
    main()

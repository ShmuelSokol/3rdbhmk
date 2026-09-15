"""ResidentV4 tileable texture set, authored offline (numpy only, no third-party image).

  python Scripts/create_resident_v4_textures.py

Writes SourceAssets/characters-review/ResidentV4/textures/:
  T_RV4_WeaveN.png     256^2 tangent-space normal, plain (tabby) weave, 8 x 8 threads per tile
  T_RV4_SlubMottle.png 512^2 grey: horizontal slub threads + low-frequency dye mottle (albedo/roughness)
  T_RV4_PoresN.png     256^2 tangent-space normal, fine skin pores and micro-creases
  T_RV4_StrandN.png    256^2 tangent-space normal, hair strands running along V
All tile seamlessly (periodic construction). Materials sample them at UV * tiling, UV = cm / 10.
"""
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/ResidentV4/textures'


def png(path, arr):
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    h, w = arr.shape[:2]
    ch = 1 if arr.ndim == 2 else arr.shape[2]
    ctype = {1: 0, 3: 2, 4: 6}[ch]
    raw = b''.join(b'\x00' + arr[y].tobytes() for y in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ctype, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def periodic_noise(n, freqs, seed):
    """Sum of random-phase sinusoids on integer frequencies: exactly periodic on an n x n tile."""
    rng = np.random.RandomState(seed)
    y, x = np.mgrid[0:n, 0:n] / float(n)
    out = np.zeros((n, n))
    for f, amp in freqs:
        for _ in range(4):
            kx, ky = rng.randint(-f, f + 1), rng.randint(-f, f + 1)
            if kx == 0 and ky == 0:
                continue
            out += amp * np.cos(2 * np.pi * (kx * x + ky * y) + rng.uniform(0, 2 * np.pi))
    return out / max(1e-6, np.abs(out).max())


def height_to_normal(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * .5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * .5 * strength
    n = np.stack([-dx, -dy, np.ones_like(h)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return (n * .5 + .5) * 255


def weave(n=256, threads=8, seed=3):
    y, x = np.mgrid[0:n, 0:n] / float(n) * threads
    i, j = np.floor(x), np.floor(y)
    fx, fy = x - i, y - j
    over = ((i + j) % 2) == 0
    warp = np.sin(np.pi * fx) ** .7 * (0.55 + .45 * np.where(over, np.sin(np.pi * fy), -np.sin(np.pi * fy) * .3))
    weft = np.sin(np.pi * fy) ** .7 * (0.55 + .45 * np.where(~over, np.sin(np.pi * fx), -np.sin(np.pi * fx) * .3))
    h = np.maximum(warp, weft) + .08 * periodic_noise(n, [(16, 1.0), (32, .5)], seed)
    return height_to_normal(h, 5.0)


def slub_mottle(n=512, seed=5):
    rng = np.random.RandomState(seed)
    low = periodic_noise(n, [(2, 1.0), (3, .7), (5, .45)], seed)
    img = .5 + .16 * low
    y = np.arange(n)
    for _ in range(90):                                    # slubs: thicker weft threads, 2-3 px tall
        row = rng.randint(0, n)
        x0, ln = rng.randint(0, n), rng.randint(n // 12, n // 3)
        amp = rng.uniform(-.13, .15)
        xs = (np.arange(ln) + x0) % n
        prof = np.sin(np.linspace(0, np.pi, ln)) ** .6 * amp
        for dy, k in ((-1, .45), (0, 1.0), (1, .45)):
            img[(row + dy) % n, xs] += prof * k
    img += .035 * periodic_noise(n, [(48, 1.0), (96, .6)], seed + 1)
    return np.clip(img, 0, 1) * 255


def pores(n=256, seed=7):
    rng = np.random.RandomState(seed)
    h = .25 * periodic_noise(n, [(24, 1.0), (40, .6)], seed)
    yy, xx = np.mgrid[0:n, 0:n]
    for _ in range(900):
        cx, cy, r = rng.randint(0, n), rng.randint(0, n), rng.uniform(1.0, 2.2)
        d2 = ((xx - cx + n / 2) % n - n / 2) ** 2 + ((yy - cy + n / 2) % n - n / 2) ** 2
        h -= .55 * np.exp(-d2 / (2 * r * r))
    return height_to_normal(h, 2.2)


def strands(n=256, seed=9):
    x = np.arange(n) / float(n)
    rng = np.random.RandomState(seed)
    col = np.zeros(n)
    for f in (13, 29, 57, 91):
        col += np.cos(2 * np.pi * f * x + rng.uniform(0, 6.28)) / f ** .35
    h = np.tile(col, (n, 1)) + .15 * periodic_noise(n, [(3, 1.0)], seed)
    return height_to_normal(h / np.abs(h).max(), 3.0)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {'T_RV4_WeaveN.png': weave(), 'T_RV4_SlubMottle.png': slub_mottle(),
             'T_RV4_PoresN.png': pores(), 'T_RV4_StrandN.png': strands()}
    manifest = {}
    for name, arr in files.items():
        p = OUT / name
        png(p, arr)
        manifest[name] = {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                          'kind': 'normal' if name.endswith('N.png') else 'grey', 'size': arr.shape[0]}
    (OUT / 'textures-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    sys.exit(main())

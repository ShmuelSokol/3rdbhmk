"""Offline before/after at the stand-in's worst walk frame: the pilgrim stand-in robe (left) and KG-V1 (right),
both posed by the SHIPPED WalkV2 clip through the same skinning as measure_kohen_garment_clearance.py.

  python Scripts/render_kohen_before_after.py [--t 0.5167] [--view side]
Writes SourceAssets/characters-review/KohenGadolV1/previews/before-after-walk-t<t>-<view>.png
"""
import argparse
import math
import struct
import sys
import zlib
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import create_pilgrim_v3 as C                  # noqa: E402
import create_kohen_gadol_v1 as K              # noqa: E402
import measure_kohen_garment_clearance as M    # noqa: E402
from measure_pilgrim_walk import Rig           # noqa: E402

OUT = K.OUT / 'previews'
VIEWS = {'side': math.pi / 2, 'front': 0.0, 'three-quarter': .62, 'rear-quarter': math.pi - .62}


def posed(which, t):
    bones, index, parts, infl, *_ = M.body_parts(which)
    clips = {n: (g, c) for n, g, c, _ in M.CLIPS}
    rig = Rig(*clips['walk'])
    A, b = M.joint_affines(rig, rig.pose(t), bones)
    if which == 'current':
        variant = [v for v in C.VARIANTS if v['id'] == 'V3_Pilgrim_Man_Standard'][0]
        colours = C.variant_materials(variant)
        for p in parts:
            p['colours'] = [colours[p['material']]] * len(p['vertices'])
    out = []
    for p in parts:
        v, J, W = M.skin_arrays(p, infl, index)
        out.append((p, [tuple(r) for r in M.skin(v, J, W, A, b)]))
    return out


def read_png(path):
    data = path.read_bytes()
    pos, idat, w, h = 8, b'', 0, 0
    while pos < len(data):
        n = struct.unpack('>I', data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        if tag == b'IHDR':
            w, h = struct.unpack('>II', body[:8])
        elif tag == b'IDAT':
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    rows = [raw[y * (w * 3 + 1) + 1:(y + 1) * (w * 3 + 1)] for y in range(h)]
    return w, h, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--t', type=float, default=0.5167)
    ap.add_argument('--view', default='side', choices=sorted(VIEWS))
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = []
    for which in ('current', 'kohen'):
        path = OUT / ('_tmp-%s-t%.4f-%s.png' % (which, a.t, a.view))   # unique: parallel runs must not collide
        K.render_vc(posed(which, a.t), path, VIEWS[a.view])
        tmp.append(path)
    (w, h, left), (_, _, right) = read_png(tmp[0]), read_png(tmp[1])
    gap = bytes((60, 60, 64)) * 6
    rows = [l + gap + r for l, r in zip(left, right)]
    out = OUT / ('before-after-walk-t%.4f-%s.png' % (a.t, a.view))
    C.write_png(out, w * 2 + 6, h, bytearray(b''.join(rows)))
    for p in tmp:
        p.unlink()
    print(out)


if __name__ == '__main__':
    main()

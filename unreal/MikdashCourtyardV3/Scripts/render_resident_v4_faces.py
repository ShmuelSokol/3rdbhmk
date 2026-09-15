"""All six ResidentV4 faces side by side in ONE image, same camera, for review. Offline.

  python Scripts/render_resident_v4_faces.py [--yaw 0.55] [--out <png>]

Rebuilds each variant's parts from the generator (no GLB read) and renders the head region with the
same vertex-colour z-buffer renderer as the previews, then composes one strip with a label bar.
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
import create_resident_v4 as R            # noqa: E402
import create_kohen_gadol_v1 as K         # noqa: E402
import create_pilgrim_v3 as C             # noqa: E402


def read_png(path):
    data = path.read_bytes()
    pos, w, h, idat = 8, 0, 0, b''
    while pos < len(data):
        n, typ = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if typ == b'IHDR':
            w, h = struct.unpack('>II', body[:8])
        elif typ == b'IDAT':
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    rows, stride = [], w * 3
    for y in range(h):
        f = raw[y * (stride + 1)]
        assert f == 0, 'unexpected PNG filter %d' % f
        rows.append(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
    return w, h, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--yaw', type=float, default=.55)
    ap.add_argument('--out', default=str(R.OUT / 'previews' / 'faces-lineup.png'))
    a = ap.parse_args()
    tmp = R.OUT / 'previews' / '_face_tmp'
    tmp.mkdir(parents=True, exist_ok=True)
    tiles = []
    for vid in R.CAST:
        v = R.variant(vid)
        parts = R.assembly(v)
        tint = C.variant_materials(v)['Mantle']
        parts = [dict(p, colours=[tuple(x * y for x, y in zip(c, tint)) for c in p['colours']])
                 if p['material'] == 'RV4_Garment' else p for p in parts]
        f = tmp / (vid + '.png')
        K.render_vc([(p, p['vertices']) for p in parts], f, a.yaw, width=330, height=440, top=186.0, scale=13.5)
        tiles.append((vid.replace('V3_Pilgrim_', ''), read_png(f)))
        print('rendered', vid, flush=True)
    W = sum(t[1][0] for t in tiles)
    H = tiles[0][1][1]
    out_rows = []
    for y in range(H):
        out_rows.append(b''.join(t[1][2][y] for t in tiles))
    pix = bytearray(b''.join(out_rows))
    C.write_png(Path(a.out), W, H, pix)
    print('wrote', a.out, W, H, ' left to right:', ', '.join(t[0] for t in tiles))


if __name__ == '__main__':
    main()

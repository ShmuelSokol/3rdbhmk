"""Offline face previewer for the FaceV5 pass: a PERSPECTIVE camera at a real distance.

  python Scripts/render_face_v5.py --variant V3_Pilgrim_Man_Elder --dist 2.0 --out <png>
  python Scripts/render_face_v5.py --kohen --dist 1.0 2.0 3.5 --out-dir <dir>

Why this exists
---------------
`create_kohen_gadol_v1.render_vc` is an orthographic, three-light, flat vertex-colour rasteriser.
It cannot answer the question this pass is about ("does this face hold up at 2 m?") for three
reasons: it has no perspective, so nothing is at a distance at all; it has no specular term, so an
eye can never catch a light; and it supersamples nothing, so a polygon edge is always a hard stair.
Every defect in the cp23 frames - the saw-tooth beard edge, the dark-smear eye, the flat cheek -
is either invisible or indistinguishable from an artefact in that renderer.

This one:
  * true perspective, framed so that `--dist` metres means what it means in the packaged frame
    (horizontal FOV 40 deg, the project's default camera, so a head at 2 m fills the same
    fraction of the frame as it does in a capture);
  * 3x supersampling, box-downfiltered, so a real silhouette stair is distinguishable from
    rasteriser aliasing;
  * Blinn-Phong specular per material plus a wrap-diffuse term for skin, so a cornea can show a
    catchlight and lips can separate from cheek;
  * per-material visible-pixel counts and a local-variance ("flatness") readout, so "the cheek is
    a flat plane" and "the eye is a dark smear" become numbers that can be compared before/after.

It is a REVIEW instrument, not an engine preview: it does not sample the pore/mottle textures and
it is not the acceptance gate. Only a real-RHI frame closes a face (AGENTS.md rule 11,
`nullrhi-cannot-verify-materials`). Use it to catch defects BEFORE spending an engine slot.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import create_pilgrim_v3 as C                 # noqa: E402

TAU = math.tau
# Material -> (specular strength, Blinn exponent, wrap-diffuse amount). Wrap fakes subsurface:
# light bleeds past the terminator, which is most of what makes skin look like skin and not plaster.
SHADING = {
    'skin':    (.22, 34.0, .38),
    'eye':     (.95, 220.0, .02),
    'hair':    (.16, 22.0, .10),
    'cloth':   (.06, 12.0, .16),
    'garment': (.06, 12.0, .16),
    'leather': (.20, 26.0, .08),
    'gold':    (.90, 90.0, .00),
    'stone':   (.60, 70.0, .05),
    'default': (.10, 20.0, .12),
}


def _kind(material):
    m = material.lower()
    for key in ('skin', 'eye', 'hair', 'leather', 'garment', 'cloth'):
        if key in m:
            return key
    if 'gold' in m:
        return 'gold'
    if 'stone' in m:
        return 'stone'
    if 'iris' in m:
        return 'eye'
    if 'linen' in m or 'meil' in m or 'ephod' in m or 'wool' in m:
        return 'cloth'
    return 'default'


class Camera:
    """Perspective camera looking at `target` from `dist` metres along -Y, rotated by `yaw`."""

    def __init__(self, target, dist_m, yaw, width, height, hfov_deg=40.0):
        self.W, self.H = width, height
        d = dist_m * 100.0                       # the generator works in centimetres
        self.eye = (target[0] + d * math.sin(yaw), target[1] - d * math.cos(yaw), target[2])
        self.target = target
        self.yaw = yaw
        self.focal = (width * .5) / math.tan(math.radians(hfov_deg) * .5)

    def project(self, pts):
        """pts: (n,3) world cm -> (n,3) of (px, py, view-depth cm). Depth > 0 is in front."""
        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        x = pts[:, 0] - self.eye[0]
        y = pts[:, 1] - self.eye[1]
        z = pts[:, 2] - self.eye[2]
        # camera forward is (-sin yaw, +cos yaw, 0); right is (cos yaw, sin yaw, 0); up is +Z
        depth = -x * sy + y * cy
        right = x * cy + y * sy
        safe = np.maximum(depth, 1e-3)
        px = self.W * .5 + self.focal * right / safe
        py = self.H * .5 - self.focal * z / safe
        return np.stack([px, py, depth], axis=1)

    def dirs(self, pts):
        """Unit vector from each point toward the eye."""
        v = np.array(self.eye, dtype=np.float32)[None, :] - pts
        n = np.linalg.norm(v, axis=1, keepdims=True)
        return v / np.maximum(n, 1e-6)


def _normals(vertices, faces):
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int64)
    n = np.zeros_like(v)
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    for k in range(3):
        np.add.at(n, f[:, k], fn)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.maximum(ln, 1e-9)


def render(parts, path, dist_m=2.0, yaw=0.0, target=None, width=900, height=1100, ss=3,
           hfov_deg=40.0, key=(-.42, -.80, .46), background=(26, 28, 31), stats=False):
    """Rasterise `parts` (the generator's part dicts, with 'vertices'/'faces'/'colours'/'material').

    Returns a dict of measurements when `stats`, else None. Always writes the PNG.
    """
    target = target or (C.HEAD_C[0], C.HEAD_C[1], C.HEAD_C[2])
    W, H = width * ss, height * ss
    cam = Camera(target, dist_m, yaw, W, H, hfov_deg)
    colour = np.zeros((H, W, 3), dtype=np.float32)
    colour[:] = np.array(background, dtype=np.float32) / 255.0
    depth = np.full((H, W), -1e18, dtype=np.float32)
    matid = np.full((H, W), -1, dtype=np.int16)
    materials = []

    kdir = np.array(key, dtype=np.float32)
    kdir /= np.linalg.norm(kdir)
    fdir = np.array((.74, -.30, .16), dtype=np.float32)
    fdir /= np.linalg.norm(fdir)
    rdir = np.array((.10, .88, .30), dtype=np.float32)
    rdir /= np.linalg.norm(rdir)

    for part in parts:
        verts = np.asarray(part['vertices'], dtype=np.float64)
        faces = np.asarray(part['faces'], dtype=np.int64)
        if len(faces) == 0:
            continue
        mat = part.get('material', 'default')
        if mat not in materials:
            materials.append(mat)
        mid = materials.index(mat)
        spec, shin, wrap = SHADING[_kind(mat)]
        nrm = np.asarray(part.get('normals') or _normals(verts, faces), dtype=np.float32)
        if len(nrm) != len(verts):
            nrm = _normals(verts, faces).astype(np.float32)
        cols = np.asarray(part['colours'], dtype=np.float32)[:, :3]
        view = cam.dirs(verts.astype(np.float32))
        # per-vertex shade: wrapped diffuse + two fills + Blinn specular toward the eye
        def lambert(ld):
            raw = nrm @ ld
            return np.clip((raw + wrap) / (1.0 + wrap), 0.0, None)
        shade = .20 + .86 * lambert(kdir) + .24 * lambert(fdir) + .16 * np.clip(nrm @ rdir, 0, None) ** 2
        hv = kdir[None, :] + view
        hv /= np.maximum(np.linalg.norm(hv, axis=1, keepdims=True), 1e-6)
        gloss = spec * np.clip(np.sum(nrm * hv, axis=1), 0, None) ** shin
        lit = np.clip(cols * shade[:, None] + gloss[:, None], 0.0, 4.0)

        proj = cam.project(verts.astype(np.float32))
        tri = proj[faces]                                     # (m,3,3)
        if np.all(tri[:, :, 2] <= 0):
            continue
        ax, ay = tri[:, 0, 0], tri[:, 0, 1]
        bx, by = tri[:, 1, 0], tri[:, 1, 1]
        cx, cy = tri[:, 2, 0], tri[:, 2, 1]
        area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        live = (np.abs(area) > 1e-9) & np.all(tri[:, :, 2] > 1.0, axis=1)
        x0 = np.clip(np.floor(np.minimum(np.minimum(ax, bx), cx)).astype(np.int32), 0, W - 1)
        x1 = np.clip(np.ceil(np.maximum(np.maximum(ax, bx), cx)).astype(np.int32), 0, W - 1)
        y0 = np.clip(np.floor(np.minimum(np.minimum(ay, by), cy)).astype(np.int32), 0, H - 1)
        y1 = np.clip(np.ceil(np.maximum(np.maximum(ay, by), cy)).astype(np.int32), 0, H - 1)
        live &= (x1 >= x0) & (y1 >= y0)
        for t in np.nonzero(live)[0]:
            i0, i1, i2 = faces[t]
            xs = np.arange(x0[t], x1[t] + 1, dtype=np.float32)
            ys = np.arange(y0[t], y1[t] + 1, dtype=np.float32)
            if xs.size == 0 or ys.size == 0:
                continue
            gx, gy = np.meshgrid(xs, ys)
            inv = 1.0 / area[t]
            w0 = ((bx[t] - gx) * (cy[t] - gy) - (by[t] - gy) * (cx[t] - gx)) * inv
            w1 = ((cx[t] - gx) * (ay[t] - gy) - (cy[t] - gy) * (ax[t] - gx)) * inv
            w2 = 1.0 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not inside.any():
                continue
            zt = w0 * tri[t, 0, 2] + w1 * tri[t, 1, 2] + w2 * tri[t, 2, 2]
            key_d = -zt                                        # nearer = larger
            sub = (slice(y0[t], y1[t] + 1), slice(x0[t], x1[t] + 1))
            win = depth[sub]
            take = inside & (key_d > win)
            if not take.any():
                continue
            px = (w0[..., None] * lit[i0] + w1[..., None] * lit[i1] + w2[..., None] * lit[i2])
            win[take] = key_d[take]
            depth[sub] = win
            cwin = colour[sub]
            cwin[take] = px[take]
            colour[sub] = cwin
            mwin = matid[sub]
            mwin[take] = mid
            matid[sub] = mwin

    srgb = np.clip(colour, 0.0, 1.0) ** (1.0 / 2.2)
    img = (srgb * 255.0 + .5).astype(np.uint8)
    down = img.reshape(height, ss, width, ss, 3).mean(axis=(1, 3))
    mdown = matid.reshape(height, ss, width, ss)[:, 0, :, 0]
    out = (np.clip(down, 0, 255) + .5).astype(np.uint8)
    C.write_png(Path(path), width, height, bytearray(out.tobytes()))
    if not stats:
        return None
    return measure(out, mdown, materials)


def measure(img, matid, materials):
    """Numbers that make the cp23 verdict testable: how much of the frame each material wins,
    and how much local variation the skin actually carries (a 'flat plane' scores near zero)."""
    total = int((matid >= 0).sum())
    per = {}
    for i, m in enumerate(materials):
        n = int((matid == i).sum())
        if n:
            per[m] = n
    grey = img.astype(np.float32).mean(axis=2)
    skin_ids = [i for i, m in enumerate(materials) if _kind(m) == 'skin']
    mask = np.isin(matid, skin_ids) if skin_ids else np.zeros_like(matid, dtype=bool)
    flat = None
    if mask.sum() > 400:
        # local standard deviation over 5x5 windows, averaged over skin pixels: the cp23 cheek,
        # hundreds of pixels of one RGB value, scores ~0.
        k = 5
        pad = np.where(mask, grey, np.nan)
        wins = []
        for dy in range(-(k // 2), k // 2 + 1):
            for dx in range(-(k // 2), k // 2 + 1):
                wins.append(np.roll(np.roll(pad, dy, axis=0), dx, axis=1))
        stack = np.stack(wins, axis=0)
        with np.errstate(invalid='ignore'):
            sd = np.nanstd(stack, axis=0)
        vals = sd[mask & np.isfinite(sd)]
        flat = float(np.nanmean(vals)) if vals.size else None
    eye_ids = [i for i, m in enumerate(materials) if _kind(m) == 'eye']
    eye_px = int(np.isin(matid, eye_ids).sum()) if eye_ids else 0
    return {'bodyPixels': total, 'perMaterialPixels': per, 'skinLocalStdDev': flat,
            'eyePixels': eye_px, 'eyeFractionOfBody': (eye_px / total) if total else 0.0}


def variant_parts(vid):
    import create_resident_v4 as R
    v = R.variant(vid)
    parts = R.assembly(v)
    tint = C.variant_materials(v)['Mantle']
    return [dict(p, colours=[tuple(a * b for a, b in zip(c, tint)) for c in p['colours']])
            if p['material'] == 'RV4_Garment' else p for p in parts], v


def kohen_parts():
    import create_kohen_gadol_v1 as K
    return K.assembly(), K.VARIANT


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--variant', default='')
    ap.add_argument('--kohen', action='store_true')
    ap.add_argument('--dist', type=float, nargs='+', default=[2.0])
    ap.add_argument('--yaw', type=float, nargs='+', default=[0.0])
    ap.add_argument('--out-dir', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--tag', default='')
    ap.add_argument('--width', type=int, default=900)
    ap.add_argument('--height', type=int, default=1100)
    ap.add_argument('--ss', type=int, default=3)
    ap.add_argument('--head-only', action='store_true', help='drop parts below the collar')
    a = ap.parse_args()
    if a.kohen:
        parts, v = kohen_parts()
        label = 'KohenGadol'
    elif a.variant:
        parts, v = variant_parts(a.variant)
        label = a.variant.replace('V3_Pilgrim_', '')
    else:
        ap.error('pass --variant or --kohen')
    if a.head_only:
        parts = [p for p in parts if max(q[2] for q in p['vertices']) > 140.0]
    out_dir = Path(a.out_dir) if a.out_dir else Path(a.out).parent if a.out else Path('.')
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {'subject': label, 'shots': []}
    for d in a.dist:
        for y in a.yaw:
            name = a.out if (a.out and len(a.dist) == 1 and len(a.yaw) == 1) else str(
                out_dir / ('%s%s-%.1fm-yaw%.2f.png' % (label, ('-' + a.tag) if a.tag else '', d, y)))
            st = render(parts, name, dist_m=d, yaw=y, width=a.width, height=a.height, ss=a.ss, stats=True)
            st.update(file=str(name), distanceM=d, yaw=y)
            report['shots'].append(st)
            print('%s  %.1f m yaw %.2f  body %d px  skinSD %s  eye %d px'
                  % (Path(name).name, d, y, st['bodyPixels'],
                     ('%.2f' % st['skinLocalStdDev']) if st['skinLocalStdDev'] is not None else 'n/a',
                     st['eyePixels']), flush=True)
    print(json.dumps(report, indent=1))
    return report


if __name__ == '__main__':
    main()

"""Measure how far any LEG vertex sits outside the ROBE, across whole clips. Offline.

  python Scripts/measure_kohen_garment_clearance.py --body current   (the stand-in: V3_Pilgrim_Man_Standard)
  python Scripts/measure_kohen_garment_clearance.py --body kohen     (Scripts/create_kohen_gadol_v1.py)

The motion is read off the SHIPPED GLBs (glTF LINEAR sampling, measure_pilgrim_walk.Rig), not
re-authored: the walk is `A_Pilgrim_Original_Walk` from walk-v2/meshes/V3_Pilgrim_Man_Standard.glb
(the WalkV2 clip the actor plays), the tend clip is `A_Pilgrim_V3_TendLamp` from tend-v1, the idle
is `A_Pilgrim_Original_Idle`. The mesh and its skin weights come from the generator, whose parts and
influences are what it writes into the GLB.

Definition, fixed so before and after are the same measurement (v3: two independent tests must agree)
-----------------------------------------------------------------------------------------------------
robe       the innermost full-length garment's TUBE (the loft's ring faces; any real cap ignored),
           skinned by its own weights. Kohen: the `Ketonet`. Stand-in: the `Tunic` part.
test A     closed-volume parity: three horizontal rays against the tube CLOSED by a virtual cap (a fan
           from the posed hem ring's centroid); outside if the majority parity is even, and not under
           that cap.
test B     signed distance: the nearest posed tube triangle (lower tube), distance along its outward
           normal (sign fixed once at rest, away from the body axis); outside if > 0.
clipping   a leg vertex (Shin*, Foot*) that BOTH tests call outside, and that is higher than the
           nearest posed hem-ring vertex (a foot below the hem is simply visible under it).
distance   test B's signed distance. Report: the maximum over every sampled frame of every clip.
Why both: each test alone has a false-positive mode on a sheared, open hem (A: a virtual fan through
the interior; B: a flipped triangle in the centre shear), and the two modes do not coincide. On the
stand-in the two tests agree to the millimetre at every frame checked (walk 23.85 cm, tend 2.45 cm).
Kohen only, same rule: ketonet vertices against the me'il tube, counted only more than 1.5 cm
above the nearest posed me'il hem vertex (below that the ketonet is simply showing under the hem,
as it is meant to).
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import create_pilgrim_v3 as C                 # noqa: E402
from measure_pilgrim_walk import Rig          # noqa: E402

RIG3 = ROOT / 'SourceAssets/characters-review/PilgrimRigV3'
CLIPS = [
    # name, glb, clip, sample rate (Hz). Walk: the full 1.2 s cycle at 240 Hz.
    ('walk', RIG3 / 'walk-v2/meshes/V3_Pilgrim_Man_Standard.glb', 'A_Pilgrim_Original_Walk', 240.0),
    ('tend', RIG3 / 'tend-v1/meshes/V3_Pilgrim_Man_Standard_TendLamp.glb', 'A_Pilgrim_V3_TendLamp', 60.0),
    ('idle', RIG3 / 'walk-v2/meshes/V3_Pilgrim_Man_Standard.glb', 'A_Pilgrim_Original_Idle', 30.0),
]
# The ketonet is MEANT to show under the me'il hem. A ketonet point within this height of the posed
# me'il hem is that reveal, not a poke-through, so the me'il test only counts points above it.
MEIL_HEM_MARGIN_CM = 1.5
RAY_DIRS = [(math.cos(a), math.sin(a), 0.0) for a in (0.31, 2.43, 4.52)]
CHUNK = 48


def body_parts(which):
    bones = C.skeleton()
    index = {b['name']: i for i, b in enumerate(bones)}
    if which == 'current':
        variant = [v for v in C.VARIANTS if v['id'] == 'V3_Pilgrim_Man_Standard'][0]
        parts = C.assembly(variant)
        return bones, index, parts, C.influence, 'Tunic', 76, None, None
    import create_kohen_gadol_v1 as K         # noqa: E402
    parts = K.assembly()
    return bones, index, parts, K.influence, 'Ketonet', K.KETONET_SEGMENTS, 'Meil', K.MEIL_SEGMENTS


def skin_arrays(part, influence, index):
    v = np.array(part['vertices'], dtype=np.float64)
    J = np.zeros((len(v), 4), dtype=np.int32)
    W = np.zeros((len(v), 4), dtype=np.float64)
    for i, p in enumerate(part['vertices']):
        for k, (j, w) in enumerate(influence(part, p, index)):
            J[i, k] = j
            W[i, k] = w
    return v, J, W


def joint_affines(rig, world, bones):
    """Per joint (A, b) with skinned = A @ rest + b, from the rig's own point() mapping."""
    A = np.zeros((len(bones), 3, 3))
    b = np.zeros((len(bones), 3))
    for j, bone in enumerate(bones):
        node = rig.index[bone['name']]
        bind = np.array(bone['position_cm'], dtype=np.float64)
        o = np.array(rig.point(world, node, (0.0, 0.0, 0.0)))
        for k in range(3):
            e = [0.0, 0.0, 0.0]
            e[k] = 1.0
            A[j, :, k] = np.array(rig.point(world, node, tuple(e))) - o
        b[j] = o - A[j] @ bind
    return A, b


def skin(v, J, W, A, b):
    out = np.zeros_like(v)
    for k in range(4):
        out += W[:, k:k + 1] * (np.einsum('nij,nj->ni', A[J[:, k]], v) + b[J[:, k]])
    return out


def inside(points, tri):
    """Majority vote of horizontal-ray parity against triangles tri (m,3,3).

    A horizontal ray at height z can only hit a triangle whose z-range contains z, so the
    points are sorted by z and each chunk is tested against the triangles overlapping its
    own z band only. Same answer as testing them all, an order of magnitude faster.
    """
    # Rays exactly at a shared ring height graze triangle edges and flip the parity; lift the
    # test point by an irrational hair (7.3 um) so no ray lies in a ring plane.
    order = np.argsort(points[:, 2])
    pts = points[order] + np.array([0.0, 0.0, 7.31e-4])
    tz0, tz1 = tri[:, :, 2].min(axis=1), tri[:, :, 2].max(axis=1)
    votes = np.zeros(len(points), dtype=np.int32)
    for d in RAY_DIRS:
        d = np.array(d)
        hits = np.zeros(len(points), dtype=np.int32)
        for s0 in range(0, len(pts), CHUNK):
            P = pts[s0:s0 + CHUNK]
            sel = (tz0 <= P[:, 2].max()) & (tz1 >= P[:, 2].min())
            if not sel.any():
                continue
            T = tri[sel]
            v0, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
            h = np.cross(np.broadcast_to(d, e2.shape), e2)
            a = np.einsum('mi,mi->m', e1, h)
            ok = np.abs(a) > 1e-12
            f = np.where(ok, 1.0 / np.where(ok, a, 1.0), 0.0)
            s = P[:, None, :] - v0[None]
            u = f[None] * np.einsum('nmi,mi->nm', s, h)
            q = np.cross(s, e1[None])
            vv = f[None] * np.einsum('i,nmi->nm', d, q)
            t = f[None] * np.einsum('mi,nmi->nm', e2, q)
            hit = ok[None] & (u >= 0) & (vv >= 0) & (u + vv <= 1) & (t > 1e-9)
            hits[s0:s0 + CHUNK] = hit.sum(axis=1)
        votes += (hits % 2 == 1)
    out = np.zeros(len(points), dtype=bool)
    out[order] = votes >= 2
    return out


def _seg(P, p0, p1):
    e = p1 - p0
    ee = np.maximum(np.einsum('mi,mi->m', e, e), 1e-12)
    t = np.clip(np.einsum('nmi,mi->nm', P - p0[None], e) / ee[None], 0, 1)
    return np.linalg.norm(P - (p0[None] + e[None] * t[..., None]), axis=2)


def point_tri_distance(points, tri):
    """Min distance from each point to the triangle set: interior projection or the three edges."""
    best = np.full(len(points), np.inf)
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    n = np.cross(b - a, c - a)
    nn = np.linalg.norm(n, axis=1)
    good = nn > 1e-12
    n = n / np.where(good, nn, 1.0)[:, None]
    for s0 in range(0, len(points), CHUNK):
        P = points[s0:s0 + CHUNK][:, None, :]
        dp = np.einsum('nmi,mi->nm', P - a[None], n)
        proj = P - dp[..., None] * n[None]
        c1 = np.einsum('nmi,mi->nm', np.cross(b - a, proj - a[None]), n)
        c2 = np.einsum('nmi,mi->nm', np.cross(c - b, proj - b[None]), n)
        c3 = np.einsum('nmi,mi->nm', np.cross(a - c, proj - c[None]), n)
        interior = good[None] & (c1 >= 0) & (c2 >= 0) & (c3 >= 0)
        dist = np.where(interior, np.abs(dp), np.inf)
        dist = np.minimum(dist, np.minimum(_seg(P, a, b), np.minimum(_seg(P, b, c), _seg(P, c, a))))
        best[s0:s0 + CHUNK] = dist.min(axis=1)
    return best


def nearest_signed(points, tri, sign):
    """For each point: signed distance to the nearest triangle along its (sign-fixed) normal."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    n = np.cross(b - a, c - a) * sign[:, None]
    nn = np.linalg.norm(n, axis=1)
    good = nn > 1e-12
    n = n / np.where(good, nn, 1.0)[:, None]
    tz0, tz1 = tri[:, :, 2].min(axis=1), tri[:, :, 2].max(axis=1)
    order = np.argsort(points[:, 2])
    pts = points[order]
    out = np.zeros(len(points))
    for s0 in range(0, len(pts), CHUNK):
        P3 = pts[s0:s0 + CHUNK]
        band = 20.0
        sel = np.where((tz0 <= P3[:, 2].max() + band) & (tz1 >= P3[:, 2].min() - band))[0]
        A, B, Cc, N = a[sel], b[sel], c[sel], n[sel]
        P = P3[:, None, :]
        dp = np.einsum('nmi,mi->nm', P - A[None], N)
        proj = P - dp[..., None] * N[None]
        c1 = np.einsum('nmi,mi->nm', np.cross(B - A, proj - A[None]), N)
        c2 = np.einsum('nmi,mi->nm', np.cross(Cc - B, proj - B[None]), N)
        c3 = np.einsum('nmi,mi->nm', np.cross(A - Cc, proj - Cc[None]), N)
        interior = good[sel][None] & (c1 >= 0) & (c2 >= 0) & (c3 >= 0)
        dist = np.where(interior, np.abs(dp), np.inf)
        dist = np.minimum(dist, np.minimum(_seg(P, A, B), np.minimum(_seg(P, B, Cc), _seg(P, Cc, A))))
        k = dist.argmin(axis=1)
        rows = np.arange(len(P3))
        # signed along the nearest triangle's normal: its plane offset (edge-nearest keeps the sign)
        out[s0:s0 + CHUNK] = np.sign(dp[rows, k]) * dist[rows, k]
    res = np.zeros(len(points))
    res[order] = out
    return res


def tube_signs(rest_pts, faces):
    """+1/-1 per triangle so that its normal points away from the body axis at rest."""
    tri = rest_pts[faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    cen = tri.mean(axis=1)
    radial = cen.copy()
    radial[:, 2] = 0.0
    return np.where(np.einsum('mi,mi->m', n, radial) >= 0, 1.0, -1.0)


def signed_outside(points, robe_pts, wall, sign, hem_idx, hem_margin=0.0):
    """Clipping distance per point: > 0 only if outside the nearest cloth AND more than `hem_margin`
    above the nearest posed hem vertex."""
    d = nearest_signed(points, robe_pts[wall], sign)
    hem = robe_pts[hem_idx]
    d2 = ((points[:, None, :] - hem[None]) ** 2).sum(axis=2)
    hem_z = hem[d2.argmin(axis=1), 2]
    return np.where((d > 0) & (points[:, 2] > hem_z + hem_margin), d, 0.0)


def loft_triangles(part, segments):
    """All faces, wall faces (no cap centre) and hem-ring indices of a C.loft part."""
    faces = np.array(part['faces'], dtype=np.int32)
    n_ring_verts = (len(part['vertices']) // segments) * segments
    wall = faces[(faces < n_ring_verts).all(axis=1)]
    return faces, wall, np.arange(segments), n_ring_verts


def under_cap(points, cap_tri):
    """True where a vertical ray UP from the point crosses the hem cap: the point is under the hem."""
    if cap_tri is None or not len(cap_tri):
        return np.zeros(len(points), dtype=bool)
    a, b, c = cap_tri[:, 0, :2], cap_tri[:, 1, :2], cap_tri[:, 2, :2]
    out = np.zeros(len(points), dtype=bool)
    for s0 in range(0, len(points), CHUNK):
        P = points[s0:s0 + CHUNK, None, :]
        def cr(p0, p1):
            return (p1[None, :, 0] - p0[None, :, 0]) * (P[..., 1] - p0[None, :, 1]) -                    (p1[None, :, 1] - p0[None, :, 1]) * (P[..., 0] - p0[None, :, 0])
        d1, d2, d3 = cr(a, b), cr(b, c), cr(c, a)
        inside2d = ((d1 >= 0) & (d2 >= 0) & (d3 >= 0)) | ((d1 <= 0) & (d2 <= 0) & (d3 <= 0))
        zc = cap_tri[:, :, 2].max(axis=1)
        out[s0:s0 + CHUNK] = (inside2d & (P[..., 2] < zc[None] + 0.01)).any(axis=1)
    return out


def outside_above(points, robe_pts, faces, wall, hem_idx, lower_mask, virtual_cap=False):
    """Clipping = outside the robe tube, NOT under its hem, and higher than the nearest hem vertex.

    `under the hem` uses a VIRTUAL cap - a fan from the posed hem ring's centroid - for every body,
    whether or not the mesh has a real cap, so the stand-in and the Kohen are measured the same way.
    Real cap faces (a centre vertex) are excluded from the parity test."""
    n_ring = int(wall.max()) + 1 if len(wall) else 0
    tube_faces = faces[(faces < n_ring).all(axis=1) & lower_mask] if len(faces) else faces
    hem = robe_pts[hem_idx]
    cap_tri = None
    if virtual_cap:
        c = hem.mean(axis=0)
        nxt = np.roll(np.arange(len(hem)), -1)
        cap_tri = np.stack([np.broadcast_to(c, hem.shape), hem, hem[nxt]], axis=1)
    # The virtual cap CLOSES the tube for the parity test too: a ray from a point between a low back
    # hem and a raised front hem must not escape under the front and read as "outside".
    tri = robe_pts[tube_faces] if cap_tri is None else np.concatenate([robe_pts[tube_faces], cap_tri])
    inn = inside(points, tri)
    d2 = ((points[:, None, :] - hem[None]) ** 2).sum(axis=2)
    hem_z = hem[d2.argmin(axis=1), 2]
    below = under_cap(points, cap_tri)
    cand = (~inn) & (~below) & (points[:, 2] > hem_z)
    dist = np.zeros(len(points))
    if cand.any():
        dist[cand] = point_tri_distance(points[cand], robe_pts[wall])
    return dist


def conjunction(points, robe_pts, faces, wall, hem_idx, lower_mask, signed_wall, sign, hem_margin=0.0):
    """The v3 rule, evaluated cheapest-first: above the hem -> signed distance -> parity."""
    hem = robe_pts[hem_idx]
    d2 = ((points[:, None, :] - hem[None]) ** 2).sum(axis=2)
    above = np.where(points[:, 2] > hem[d2.argmin(axis=1), 2] + hem_margin)[0]
    out = np.zeros(len(points))
    if not len(above):
        return out
    s = signed_outside(points[above], robe_pts, signed_wall, sign, hem_idx, hem_margin)
    pos = np.where(s > 0)[0]
    if not len(pos):
        return out
    p = outside_above(points[above][pos], robe_pts, faces, wall, hem_idx, lower_mask, virtual_cap=True)
    out[above[pos]] = np.where(p > 0, s[pos], 0.0)
    return out


def run(which, rate_scale=1.0, clips=None, quiet=False, keep_frames=True):
    started = time.time()
    bones, index, parts, influence, robe_name, segments, outer_name, outer_segments = body_parts(which)
    by_name = {p['name']: p for p in parts}
    robe = by_name[robe_name]
    faces, wall, hem_idx, nring = loft_triangles(robe, segments)
    rv, rJ, rW = skin_arrays(robe, influence, index)
    lower = rv[faces].mean(axis=1)[:, 2] < 70.0
    low_wall = wall[rv[wall].mean(axis=1)[:, 2] < 60.0]
    rsign = tube_signs(rv, low_wall)
    legs = [p for p in parts if p['name'].startswith(('Shin', 'Foot'))]
    lv, lJ, lW, lname = [], [], [], []
    for p in legs:
        v, J, W = skin_arrays(p, influence, index)
        lv.append(v); lJ.append(J); lW.append(W); lname += [p['name']] * len(v)
    lv, lJ, lW = np.concatenate(lv), np.concatenate(lJ), np.concatenate(lW)
    outer = by_name.get(outer_name) if outer_name else None
    if outer is not None:
        ofaces, owall, ohem, onring = loft_triangles(outer, outer_segments)
        ov, oJ, oW = skin_arrays(outer, influence, index)
        oall = np.ones(len(ofaces), dtype=bool)
        osign = tube_signs(ov, owall)
        meil_hem_z = float(ov[ohem, 2].max())
        kmask = np.zeros(len(rv), dtype=bool)
        kmask[:nring] = (rv[:nring, 2] > meil_hem_z + 1.5) & (rv[:nring, 2] < min(80.0, float(ov[:onring, 2].max()) - 3.0))
        kmask[:nring] &= (np.arange(nring) % segments) % 2 == 0      # every second segment (reported)
    report = {'body': which, 'definition': 'v3 closed-volume parity AND signed distance must both say outside, above the local hem',
              'meilTestSampling': 'ketonet ring vertices from 1.5 cm above the me\'il hem to rest z 80, every 2nd segment',
              'robe': robe_name, 'legVertices': int(len(lv)),
              'legParts': sorted({p['name'] for p in legs}),
              'robeTriangles': int(len(faces)), 'clips': {}}
    for name, glb, clip, rate in CLIPS:
        if clips and name not in clips:
            continue
        rig = Rig(glb, clip)
        n = max(2, int(round(rig.duration * rate * rate_scale)))
        worst = dict(cm=0.0, t=None, part=None, restZ=None)
        worst_k = dict(cm=0.0, t=None, restZ=None)
        frames_clipping = 0
        per_frame = []
        for i in range(n + (0 if name == 'walk' else 1)):
            t = i * rig.duration / n
            A, b = joint_affines(rig, rig.pose(t), bones)
            R = skin(rv, rJ, rW, A, b)
            L = skin(lv, lJ, lW, A, b)
            dist = conjunction(L, R, faces, wall, hem_idx, lower, low_wall, rsign)
            m = float(dist.max()) if len(dist) else 0.0
            per_frame.append(round(m, 3))
            if m > 0:
                frames_clipping += 1
            if m > worst['cm']:
                k = int(dist.argmax())
                worst = dict(cm=round(m, 3), t=round(t, 4), part=lname[k], restZ=round(float(lv[k, 2]), 2),
                             posed=[round(float(x), 2) for x in L[k]])
            if outer is not None:
                O = skin(ov, oJ, oW, A, b)
                dk = conjunction(R[kmask], O, ofaces, owall, ohem, oall, owall, osign, MEIL_HEM_MARGIN_CM)
                mk = float(dk.max()) if len(dk) else 0.0
                if mk > worst_k['cm']:
                    kk = int(dk.argmax())
                    worst_k = dict(cm=round(mk, 3), t=round(t, 4), restZ=round(float(rv[kmask][kk, 2]), 2))
        row = {'glb': str(glb.relative_to(ROOT)).replace('\\', '/'), 'clip': clip,
               'durationSeconds': round(rig.duration, 4), 'framesSampled': len(per_frame),
               'sampleRateHz': rate * rate_scale,
               'maxLegOutsideRobeCm': worst['cm'], 'worst': worst,
               'framesWithAnyClipping': frames_clipping}
        if keep_frames:
            row['perFrameMaxCm'] = per_frame
        if outer is not None:
            row['maxKetonetOutsideMeilCm'] = worst_k['cm']
            row['worstKetonetOutsideMeil'] = worst_k
        report['clips'][name] = row
        if not quiet:
            print(name, 'max leg outside robe %.2f cm' % worst['cm'], worst,
                  ('ketonet outside meil %.2f' % worst_k['cm']) if outer is not None else '', flush=True)
    report['seconds'] = round(time.time() - started, 1)
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--body', choices=('current', 'kohen'), required=True)
    ap.add_argument('--rate-scale', type=float, default=1.0)
    ap.add_argument('--clips', default='')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    rep = run(a.body, a.rate_scale, [c for c in a.clips.split(',') if c])
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: (v if k != 'clips' else {c: {kk: vv for kk, vv in r.items() if kk != 'perFrameMaxCm'}
                                               for c, r in v.items()}) for k, v in rep.items()}, indent=1))

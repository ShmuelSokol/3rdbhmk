"""ResidentV4: the six cast resident bodies rebuilt to read as PEOPLE at 3-5 m. Offline only.

  python Scripts/create_resident_v4.py --build             six GLBs + manifest + previews
  python Scripts/create_resident_v4.py --build --only V3_Pilgrim_Man_Standard --fast

Same pipeline as Scripts/create_kohen_gadol_v1.py: imports create_pilgrim_v3 (C) and the Kohen Gadol
generator (K) and modifies NEITHER. The skeleton is C.skeleton() unchanged, so each mesh imports onto
the EXISTING per-variant Skeleton (V3_<variant>_Skeleton) and plays that variant's shipped WalkV2 / Idle
clips as they are. No bone, clip, gait code or skeleton is touched.

What changed against the V3 residents (cp11 verdict: "painted wooden mannequins at 3 m")
  FACE     one dense sculpted head per variant (front-weighted grid, ~0.15 cm at the eyes and mouth):
           eye sockets carved round a real eyeball (sclera, iris, limbal ring, pupil, corneal bulge);
           upper and lower lids wrap the ball and leave a palpebral opening; a lash line; brows as
           hair shells; nose, alae, lips with a mouth line, philtrum, chin, jaw, cheekbones,
           naso-labial folds and age lines sculpted INTO the head, not pasted on; ears with helix,
           concha and lobe; beard / moustache / hair as offset shells of the head with strand clumps.
           Six different faces (FACES below) plus four face-shape morph targets (Face0..Face3) so the
           population can give each of the 24 residents a different face from one mesh.
  SHADING  per-vertex skin tint (cheek / nose / ear flush, lip colour, orbit shadow, beard shadow),
           baked cavity shading on every part (fold valleys, sockets, mouth corners), authored UVs
           on every part (cm-true, seams split) for a weave / slub / pore texture set in engine.
  DRESS    tunic to mid-calf for men, lower shin for women, below the knee for the youth, so the
           72 cm WalkV2 stride finally shows; tunic skinned by the Kohen Gadol weight field (pelvis ->
           same-side thigh -> calf), which measured 0 cm leg clipping there; two clavi; bloused over
           the belt; the mantle built as an OFFSET of the tunic surface with the tunic's own weights
           (anchors), so it cannot be pierced by the tunic folds (the V3 'torn paper' edge was the
           tunic breaking through the mantle by up to 6.9 cm at rest - measured, not an alpha edge);
           tzitzit on the four corners of the men's mantles; sandals with ankle thongs; anatomical
           legs (calf, shin, malleoli, knee) instead of cylinders.

SOURCES (sourced vs authored is also written into the manifest)
  S  Tzitzit on four-cornered garments, with a thread of techelet: Numbers 15:38-39, Deuteronomy
     22:12. Women exempt (time-bound): Menachot 43a. Placement on this draped panel is AUTHORED.
  S  Married women cover their hair in public: Mishnah Ketubot 7:6 ("goes out with her head
     uncovered" is grounds for divorce). The shawl-over-the-head form is AUTHORED.
  S- Tunics woven as two sheets with a pair of coloured vertical bands (clavi) over the shoulders,
     mantles with notched-band ("gamma") corners, leather sandals with thongs: Y. Yadin, The Finds
     from the Bar-Kokhba Period in the Cave of Letters (1963) and the Masada textile reports -
     cited from general knowledge, NOT re-read in this pass (flagged R in the manifest).
  A  Hem heights, colours, fold amplitudes, every face, every clearance offset, the bloused belt.
"""
import argparse
import hashlib
import json
import math
import random
import struct
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import create_pilgrim_v3 as C                                   # noqa: E402
import create_kohen_gadol_v1 as K                               # noqa: E402
from create_pilgrim_v3 import (add, sub, scale, dot, cross, length, normalize, clamp, smooth,  # noqa: E402
                               gauss, HEAD_C, HEAD_RX, HEAD_RY, HEAD_RZ)

OUT = ROOT / 'SourceAssets/characters-review/ResidentV4'
TRIANGLE_BUDGET = 60000       # per resident; see the manifest's budget note
UV_CM = 10.0                  # 1 UV unit = 10 cm of cloth or skin, everywhere
MORPHS = ('Face0', 'Face1', 'Face2', 'Face3')   # nose, jaw, brow, lips (see morph_field)

# Slot -> (roughness, specular, kind). kind picks the engine master: skin (subsurface) or cloth.
SLOTS = {
    'RV4_Skin': (.52, .45, 'skin'),
    'RV4_Eye': (.07, .80, 'cloth'),
    'RV4_Hair': (.62, .38, 'cloth'),
    'RV4_Cloth': (.88, .40, 'cloth'),
    'RV4_Garment': (.90, .38, 'cloth'),     # the per-resident garment slot (population tint)
    'RV4_Leather': (.66, .42, 'cloth'),
}

# ----------------------------------------------------------------------------- the six cast variants
# Body facts (girth, shoulder, age, skin tone, palette, seeds) come from C.VARIANTS unchanged; these
# override the dress and add the face. Hems are rest z of the lowest hem point, cm (authored).
# Women at 18 cm (lower shin): at 12-15 cm the swing foot, lifted to z 16, pierced the lowest
# cloth rings by 0.07-0.27 cm; 18 cm is also the Kohen Gadol me'il hem that measured clean.
# Women's mantles end at 58 cm (upper thigh): at 46-48 cm their lowest row sat in the knee handover band
# (82% calf), swung up with the flexing knee and crossed the thigh-weighted tunic by 2.3 cm in the walk.
# 58 cm is Man_Elder's mantle hem, which measured 0.00.
DRESS = {
    'V3_Pilgrim_Man_Standard': dict(tunic_hem=32.0, mantle_hem=54.0, sex='m', headwear='cloth',
                                    cloth_span=72, tzitzit=True, clavi=(.30, .22, .13)),
    'V3_Pilgrim_Man_Heavy': dict(tunic_hem=30.0, mantle_hem=52.0, sex='m', headwear='turban',
                                 tzitzit=True, clavi=(.20, .15, .10)),
    'V3_Pilgrim_Man_Elder': dict(tunic_hem=24.0, mantle_hem=58.0, sex='m', headwear='cloth',
                                 cloth_span=106, tzitzit=True, clavi=(.36, .28, .18)),
    'V3_Pilgrim_Woman_Young': dict(tunic_hem=18.0, mantle_hem=58.0, sex='f', headwear='shawl',
                                   tzitzit=False, clavi=(.14, .17, .30)),
    'V3_Pilgrim_Woman_Elder': dict(tunic_hem=18.0, mantle_hem=58.0, sex='f', headwear='shawl',
                                   tzitzit=False, clavi=(.34, .16, .14)),
    'V3_Pilgrim_Youth': dict(tunic_hem=44.0, mantle_hem=None, sex='m', headwear='cap',
                             tzitzit=False, clavi=(.40, .26, .12)),
}

# Faces (all AUTHORED). Scales are relative to the V3 head; hair/brow/iris colours linear RGB.
FACES = {
    'V3_Pilgrim_Man_Standard': dict(female=0, soft=0.0, nose_len=1.00, nose_w=1.00, hook=.35, jaw=1.00, chin=1.00,
                                    brow=1.00, eye_sp=1.00, lip=1.00, cheek=.15, sunken=.0, wrinkle=.15,
                                    open=1.00, tilt=.05, beard='short', brow_bush=1.0,
                                    iris=(.075, .045, .022), hair=(.045, .028, .018)),
    'V3_Pilgrim_Man_Heavy': dict(female=0, soft=0.0, nose_len=.94, nose_w=1.28, hook=.10, jaw=1.12, chin=.80,
                                 brow=1.25, eye_sp=1.04, lip=1.15, cheek=.85, sunken=.0, wrinkle=.30,
                                 open=.88, tilt=-.02, beard='full', brow_bush=1.3,
                                 iris=(.040, .025, .014), hair=(.022, .016, .013)),
    'V3_Pilgrim_Man_Elder': dict(female=0, soft=0.0, nose_len=1.12, nose_w=.95, hook=.85, jaw=.93, chin=1.10,
                                 brow=1.10, eye_sp=.97, lip=.78, cheek=.0, sunken=.90, wrinkle=1.0,
                                 open=.82, tilt=-.10, beard='long', brow_bush=1.7,
                                 iris=(.110, .085, .050), hair=(.600, .585, .555)),
    'V3_Pilgrim_Woman_Young': dict(female=1, soft=1.0, refine=1.0, nose_len=.76, nose_w=.74, hook=.0, jaw=.86, chin=.86,
                                   brow=.10, eye_sp=1.02, lip=1.25, cheek=.85, sunken=.0, wrinkle=.0,
                                   open=1.08, tilt=.14, beard='none', brow_bush=.7,
                                   iris=(.090, .060, .030), hair=(.030, .020, .014)),
    'V3_Pilgrim_Woman_Elder': dict(female=1, soft=.70, nose_len=.96, nose_w=1.06, hook=.30, jaw=1.00, chin=.95,
                                   brow=.40, eye_sp=1.00, lip=.88, cheek=.55, sunken=.40, wrinkle=.85,
                                   open=.90, tilt=-.04, beard='none', brow_bush=.8,
                                   iris=(.060, .045, .030), hair=(.330, .310, .290)),
    'V3_Pilgrim_Youth': dict(female=0, soft=.80, refine=.65, nose_len=.84, nose_w=.90, hook=.0, jaw=.88, chin=.85,
                             brow=.50, eye_sp=1.00, lip=1.05, cheek=.50, sunken=.0, wrinkle=.0,
                             open=1.05, tilt=.06, beard='none', brow_bush=.8,
                             iris=(.050, .032, .018), hair=(.028, .019, .013)),
}
CAST = list(DRESS)


def variant(vid):
    base = [v for v in C.VARIANTS if v['id'] == vid][0]
    v = dict(base)
    v.update(DRESS[vid])
    v['face'] = FACES[vid]
    v['mesh_id'] = 'SK_RV4_' + vid.replace('V3_Pilgrim_', '')
    return v


# ----------------------------------------------------------------------------- small helpers
def lerp3(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def mul3(a, b):
    return tuple(x * y for x, y in zip(a, b))


def hash01(*k):
    h = 2166136261
    for x in k:
        h = ((h ^ (int(x) & 0xffffffff)) * 16777619) & 0xffffffff
    h ^= h >> 13
    h = (h * 1274126177) & 0xffffffff
    return (h & 0xffffff) / float(0xffffff)


def vnoise(u, v, seed, freq=1.0):
    """Smooth value noise in [-1, 1] (for tint and mottle; not for geometry that must be exact)."""
    u, v = u * freq, v * freq
    i, j = math.floor(u), math.floor(v)
    fu, fv = u - i, v - j
    su, sv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)

    def h(a, b):
        return hash01(a, b, seed) * 2 - 1
    a = h(i, j) + (h(i + 1, j) - h(i, j)) * su
    b = h(i, j + 1) + (h(i + 1, j + 1) - h(i, j + 1)) * su
    return a + (b - a) * sv


def warp(n, lo, hi, density, fine=6000, endpoint=True):
    """n (+1 if endpoint) samples in [lo, hi] spaced inversely to `density`."""
    xs = [lo + (hi - lo) * i / fine for i in range(fine + 1)]
    cum = [0.0]
    for a, b in zip(xs, xs[1:]):
        cum.append(cum[-1] + .5 * (density(a) + density(b)) * (b - a))
    total = cum[-1]
    out, k = [], 0
    count = n + 1 if endpoint else n
    for s in range(count):
        target = total * s / n
        while k < fine - 1 and cum[k + 1] < target:
            k += 1
        seg = cum[k + 1] - cum[k]
        u = 0.0 if seg <= 0 else (target - cum[k]) / seg
        out.append(xs[k] + (xs[k + 1] - xs[k]) * clamp(u))
    return out


def grid_faces(rows, cols, wrap):
    f = []
    for r in range(rows - 1):
        for c in range(cols if wrap else cols - 1):
            a = r * cols + c
            b = r * cols + (c + 1) % cols
            f += [(a, b, b + cols), (a, b + cols, a + cols)]
    return f


# ----------------------------------------------------------------------------- UV and seams
def split_seams(part):
    """Duplicate vertices of faces that straddle a periodic U seam (part['uvPeriod'])."""
    P = part.get('uvPeriod')
    if not P:
        return part
    v, f, uv = part['vertices'], part['faces'], part['uv']
    extra = {}
    keys = ('vertices', 'uv', 'normals', 'colours', 'anchors')
    new = {k: list(part[k]) for k in keys if part.get(k) is not None}
    faces = []
    for tri in f:
        us = [uv[i][0] for i in tri]
        if max(us) - min(us) <= P / 2:
            faces.append(tri)
            continue
        t2 = []
        for i in tri:
            if uv[i][0] < P / 2:
                if i not in extra:
                    extra[i] = len(new['vertices'])
                    for k in new:
                        item = part[k][i]
                        new[k].append((item[0] + P, item[1]) if k == 'uv' else item)
                i = extra[i]
            t2.append(i)
        faces.append(tuple(t2))
    out = dict(part)
    out.update(new)
    out['faces'] = faces
    out['seamVerticesAdded'] = len(extra)
    return out


def cylinder_uv(verts, centre_xy=(0.0, 0.0), radius=None, v_of=None):
    """U = angle around a vertical axis (integer period, cm-true at `radius`), V = z / UV_CM."""
    if radius is None:
        radius = sum(math.hypot(p[0] - centre_xy[0], p[1] - centre_xy[1]) for p in verts) / max(1, len(verts))
    P = max(1, round(math.tau * radius / UV_CM))
    uv = []
    for p in verts:
        a = math.atan2(p[1] - centre_xy[1], p[0] - centre_xy[0]) % math.tau
        uv.append((a / math.tau * P, (v_of(p) if v_of else p[2]) / UV_CM))
    return uv, P


def planar_uv(verts, axis='y'):
    k = {'x': (1, 2), 'y': (0, 2), 'z': (0, 1)}[axis]
    return [(p[k[0]] / UV_CM, p[k[1]] / UV_CM) for p in verts], None


# ----------------------------------------------------------------------------- baked cavity shading
def cavity(part, strength=1.0, radius_cm=1.2):
    """Per-vertex concavity from the 1-ring: (mean neighbour - vertex) . normal, normalised by the
    local edge length. >0 in a valley (fold, socket, crease) -> darkened; ridges slightly lifted."""
    v, f = part['vertices'], part['faces']
    n = part['normals']
    nb = [set() for _ in v]
    for a, b, c in f:
        nb[a].update((b, c)); nb[b].update((a, c)); nb[c].update((a, b))
    out = []
    for i, p in enumerate(v):
        if not nb[i]:
            out.append(1.0)
            continue
        m = [0.0, 0.0, 0.0]
        el = 0.0
        for j in nb[i]:
            q = v[j]
            for k in range(3):
                m[k] += q[k]
            el += length(sub(q, p))
        m = [x / len(nb[i]) for x in m]
        el = max(el / len(nb[i]), 1e-4)
        conc = dot(sub(tuple(m), p), n[i]) / el          # ~ curvature * edge length
        conc *= min(1.0, radius_cm / el) ** .5          # fine meshes read their fine valleys
        out.append(clamp(1.0 - strength * 2.2 * max(0.0, conc) + strength * .35 * max(0.0, -conc), .45, 1.12))
    # one smoothing pass so it reads as occlusion, not as a wireframe
    sm = []
    for i in range(len(v)):
        s, w = out[i] * 2.0, 2.0
        for j in nb[i]:
            s += out[j]; w += 1.0
        sm.append(s / w)
    return sm


# ============================================================================= assembly
PER_VERTEX = ('vertices', 'uv', 'normals', 'colours', 'anchors', 'mdelta', 'ndelta')


def split_seams2(part):
    """split_seams for every per-vertex list, including the morph deltas."""
    P = part.get('uvPeriod')
    if not P:
        return part
    n0 = len(part['vertices'])
    keys = [k for k in PER_VERTEX if part.get(k) is not None]
    new = {k: list(part[k]) for k in keys}
    extra, faces = {}, []
    for tri in part['faces']:
        us = [part['uv'][i][0] for i in tri]
        if max(us) - min(us) <= P / 2:
            faces.append(tri)
            continue
        t2 = []
        for i in tri:
            if part['uv'][i][0] < P / 2:
                if i not in extra:
                    extra[i] = len(new['vertices'])
                    for k in keys:
                        item = part[k][i]
                        new[k].append((item[0] + P, item[1]) if k == 'uv' else item)
                i = extra[i]
            t2.append(i)
        faces.append(tuple(t2))
    out = dict(part)
    out.update(new)
    out['faces'] = faces
    out['seamVerticesAdded'] = len(extra)
    assert len(out['vertices']) == n0 + len(extra)
    return out


class Parts:
    def __init__(self, variant):
        self.v = variant
        self.parts = []

    def add(self, name, material, mesh, skin, colours, anchors=None, closed=True, cavity_k=1.0, morph=False):
        v, f = mesh[0], mesh[1]
        uv = mesh[2] if len(mesh) > 2 and mesh[2] is not None else None
        P = mesh[3] if len(mesh) > 3 else None
        if closed:
            vol = sum(dot(v[a], cross(v[b], v[c])) for a, b, c in f)
            if vol < 0:
                f = [(a, c, b) for a, b, c in f]
        if uv is None:
            uv, P = cylinder_uv(v) if (max(p[2] for p in v) - min(p[2] for p in v)) > 6 else planar_uv(v)
        if callable(colours):
            colours = [colours(p, i) for i, p in enumerate(v)]
        elif not isinstance(colours, list):
            colours = [colours] * len(v)
        assert len(colours) == len(v) == len(uv), name
        part = {'name': name, 'material': material, 'vertices': v, 'faces': f, 'skin': skin, 'uv': uv,
                'uvPeriod': P, 'colours': colours, 'morph': morph}
        if anchors is not None:
            assert len(anchors) == len(v), name
            part['anchors'] = [tuple(a) for a in anchors]
        part['normals'] = C.normals(part)
        if cavity_k and len(v) > 60:
            cv = cavity(part, cavity_k)
            part['colours'] = [tuple(k * s for k in c) for c, s in zip(colours, cv)]
        self.parts.append(part)
        return part

    def adder(self, rename, drop=()):
        def add_(name, material, mesh, skin):
            if name.startswith(tuple(drop)):
                return
            mat = rename[material]
            self.add(name, mat, mesh, skin, self.colour_of(material), cavity_k=.6)
        return add_

    def colour_of(self, material):
        pal = C.variant_materials(self.v)
        return pal.get(material, (.5, .5, .5))


def head_covering(P, variant, palette):
    """Headcloth (men), turban, shawl over the head (women; Ketubot 7:6), youth's cap - on the V4 head.
    The cloth stands off the ear (+1.8 cm at ear height) and, for Man_Standard, is cut behind it."""
    import create_resident_v4_face as FA
    kind = variant['headwear']
    folds = C.fold_field(variant['fold_seed'] + 9, .38, ((11, 1.0), (6, .7), (19, .35)))
    cy = HEAD_C[1] + .40
    cloth = palette['Headcloth']
    hs = C.head_skin
    if kind == 'turban':
        P.add('TurbanCrown', 'RV4_Cloth', FA.ellipsoid_uv((0, cy, HEAD_C[2] + 10.6), (8.75, 10.65, 5.2), 36, 14),
              hs, cloth, morph=True)
        for layer in range(3):
            pts = [(8.45 * math.cos(i * math.tau / 34), cy + 10.3 * math.sin(i * math.tau / 34),
                    HEAD_C[2] + 7.4 + layer * 2.05 + 1.0 * math.cos(i * math.tau / 34 + .5)) for i in range(35)]
            P.add('TurbanBand%d' % layer, 'RV4_Cloth', FA.tube_uv(pts, [(.90, 1.28)] * 35, 12), hs,
                  R_shade(cloth, .92 + .04 * layer), morph=True)
        return
    if kind == 'cap':
        P.add('Cap', 'RV4_Cloth', FA.loft_uv([(HEAD_C[2] + 5.6, 8.50, 10.20, 0, cy), (HEAD_C[2] + 7.0, 8.75, 10.45, 0, cy + .05),
                                             (HEAD_C[2] + 9.2, 8.30, 9.95, 0, cy + .1), (HEAD_C[2] + 11.0, 6.80, 8.10, 0, cy + .1),
                                             (HEAD_C[2] + 12.3, 4.10, 4.90, 0, cy + .1), (HEAD_C[2] + 12.9, 1.30, 1.55, 0, cy + .1)],
                                            40, radial=lambda t, z, l: folds(t, z, .35)), hs, cloth, morph=True)   # a rounded skullcap
        return
    long = kind == 'shawl'
    vmat, vcol = ('RV4_Garment', (.96, .96, .96)) if long else ('RV4_Cloth', cloth)
    rim = 4.3 if long else 5.0
    P.add('HeadCap', vmat, FA.loft_uv([(HEAD_C[2] + rim, 8.75, 10.60, 0, cy), (HEAD_C[2] + 7.4, 8.90, 10.75, 0, cy + .05),
                                             (HEAD_C[2] + 9.1, 8.25, 9.95, 0, cy + .1), (HEAD_C[2] + 11.9, 5.55, 6.65, 0, cy + .1),
                                             (HEAD_C[2] + 13.0, 2.40, 2.85, 0, cy + .1)], 36,
                                            radial=lambda t, z, l: folds(t, z, .40)), hs, vcol, morph=True)
    rows, cols = (17 if long else 14), 27
    span = math.radians(126 if long else variant.get('cloth_span', 112))
    grid = []
    for r in range(rows):
        u = r / (rows - 1)
        row = []
        for c in range(cols):
            a = -span + 2 * span * c / (cols - 1)
            back = .5 + .5 * math.cos(a)
            face = 1.0 - abs(a) / span
            base_z = 124.0 if long else 136.0
            bottom = base_z + (150.0 - base_z) * (1 - face) ** 1.4      # frames the face down past the chin
            z = (HEAD_C[2] + rim + .4) - ((HEAD_C[2] + rim + .4) - bottom) * smooth(u)
            flare = ((4.2 if long else 2.4) * smooth(u) * (.45 + .75 * back) + 1.8 * gauss(z - HEAD_C[2], 0.0, 3.5)
                     + 1.6 * gauss(z - HEAD_C[2], -7.5, 3.5) * (1 - back))                     # clear of the jaw and beard
            ripple = folds(a * 2.2 + u * 1.4, z, .60 + .90 * u)
            rx, ry = 8.90 + flare, 10.75 + flare * 1.10
            row.append(((rx + ripple) * math.sin(a), cy + (ry + ripple) * math.cos(a), z + ripple * .35))
        grid.append(row)
    P.add('HeadCloth', vmat, FA.panel_uv(grid, .34), hs, vcol, closed=False, morph=True)
    if long:
        return                                     # a woman's veil has no cord band
    band = [(8.70 * math.cos(i * math.tau / 30), cy + 10.55 * math.sin(i * math.tau / 30),
             HEAD_C[2] + 7.4 + .8 * math.cos(i * math.tau / 30)) for i in range(31)]
    P.add('HeadBand', 'RV4_Cloth', FA.tube_uv(band, [(.56, .84)] * 31, 10), hs, palette['Trim'], morph=True)


def R_shade(c, k):
    return tuple(x * k for x in c)


def assembly(variant):
    import create_resident_v4_face as FA
    import create_resident_v4_body as B
    P = Parts(variant)
    pal = C.variant_materials(variant)
    F = variant['face']
    skin = pal['Skin']
    youth = variant['mantle_hem'] is None
    hs = C.head_skin
    # ---- head, eyes, shells, ears, neck
    G = FA.head_grid(variant)
    head = P.add('Head', 'RV4_Skin', FA.head_mesh(G), hs, FA.skin_colours(G, variant), cavity_k=1.2, morph=True)
    normals = head['normals']
    for part in (head,):
        part['colours'] = [tuple(k * (1 - .30 * smooth((-n[2] - .15) / .6) * smooth((HEAD_C[2] - 4.0 - p[2]) / 2.0)) for k in c)
                           for c, n, p in zip(part['colours'], part['normals'], part['vertices'])]
    for s, E in sorted(G['eyes'].items()):
        ev, ef, al, rg = FA.eyeball(E)
        P.add('Eye%d' % s, 'RV4_Eye', (ev, ef, planar_uv(ev)[0], None), hs,
              FA.eye_colours(al, rg, F['iris'], variant['fold_seed']), cavity_k=0, morph=True)
    # brows are painted flush onto the sculpted brow ridge (skin_colours), not a floating shell
    for fn, name in ((FA.beard_shell, 'Beard'), (FA.hair_shell, 'Hair')):
        r = fn(G, normals, variant)
        if r and r[1]:
            P.add(name, 'RV4_Hair', r[:4], hs, r[4], closed=False, cavity_k=.8, morph=True)
    hang = FA.beard_hang(variant)
    if hang:
        seed = variant['fold_seed'] + 31
        P.add('BeardHang', 'RV4_Hair', hang, hs,
              lambda p, i: FA.strand_colour(F['hair'], skin, math.atan2(p[0], -p[1]), p[2] - HEAD_C[2], 1.0, seed),
              cavity_k=.9, morph=True)
    for s in (-1, 1):
        ev, ef, euv, eP, ec = FA.ear(variant, s)
        P.add('Ear%d' % s, 'RV4_Skin', (ev, ef, euv, None), hs, ec, cavity_k=1.4, morph=True)
    neck_part = P.add('Neck', 'RV4_Skin', FA.neck(variant), C.neck_skin, skin, morph=True)
    # the upper neck sits in the jaw's shadow; without this it reads as a flat lit plane under the chin
    neck_part['colours'] = [tuple(k * (1 - .32 * smooth((p[2] - 152.0) / 8.0) * smooth((.35 - n[1] * 0 - n[2]) / .6)) for k in c)
                            for c, n, p in zip(neck_part['colours'], neck_part['normals'], neck_part['vertices'])]
    # (the V3 sternocleidomastoid tubes are gone: on the narrower, set-back V4 neck they stood out as two stalks)
    head_covering(P, variant, pal)
    # ---- tunic, collar, belt and its tail
    tun = B.Tunic(variant)
    tv, tf, tuv, tP = tun.mesh()
    seg = B.TUNIC_SEGMENTS
    tcols = [tun.colour(pal, variant['clavi'], (i % seg) * math.tau / seg, tun.zs[i // seg], youth) for i in range(len(tv))]
    P.add('Tunic', 'RV4_Garment' if youth else 'RV4_Cloth', (tv, tf, tuv, tP), B.garment_skin, tcols,
          closed=False, cavity_k=1.3)
    g = variant['girth']
    P.add('Collar', 'RV4_Garment' if youth else 'RV4_Cloth',
          FA.loft_uv([(148.2, 12.9 * g, 9.4 * g, 0, 0), (149.2, 13.4 * g, 9.8 * g, 0, 0),
                      (151.4, 8.6 * g, 7.3 * g, 0, 0), (152.2, 7.9 * g, 6.8 * g, 0, 0)], 36),
          C.torso_skin, (.85, .85, .85) if youth else pal['Trim'])
    span = (100.0, 110.4)
    pads = [1.0, 2.0, 2.3, 2.3, 2.0, 1.0]
    rings = []
    for i, pad in enumerate(pads):
        z = span[0] + (span[1] - span[0]) * i / (len(pads) - 1)
        mx = max(tun.radial(k * math.tau / 96, z) for k in range(96))
        rx, ry = tun.section(z)
        rings.append((z, rx + mx + pad, ry + mx + pad, 0.0, 0.0))
    P.add('Belt', 'RV4_Cloth', FA.loft_uv(rings, 64, exponent=tun.exponent,
                                          radial=lambda t, z, l: .30 * math.cos(t * 7 + z)), B.garment_skin, pal['Sash'])
    grid, anch = [], []
    for r in range(12):
        z = 101.0 - r * 2.6
        row, arow = [], []
        for c in range(4):
            t = 1.5 * math.pi + .09 + c * .05          # inside the mantle's front opening (24 deg)
            mx = max(tun.radial(t + k * .01, z) for k in range(-4, 5)) - tun.radial(t, z)
            row.append(tun.point(t, z, mx + 1.6 + .25 * math.sin(r * .7 + c)))
            arow.append(tun.point(t, z, 0.0))
        grid.append(row)
        anch.append(arow)
    tv2, tf2, tuv2, _ = FA.panel_uv(grid, .28)
    flat = [a for row in anch for a in row]
    P.add('BeltTail', 'RV4_Cloth', (tv2, tf2, tuv2, None), B.garment_skin, pal['Sash'], anchors=flat + flat)
    # ---- mantle and tzitzit
    if not youth:
        mv, mf, muv, manch, mgrid, mzs, mcols = B.mantle(variant, tun)
        P.add('Mantle', 'RV4_Garment', (mv, mf, muv, None), B.garment_skin,
              B.mantle_colour(variant, mgrid, mzs, mcols), anchors=manch, cavity_k=1.2)
        if variant['tzitzit']:
            rows = len(mgrid)
            agrid = [manch[r * mcols:(r + 1) * mcols] for r in range(rows)]
            for k, (pts, colour, a) in enumerate(B.tzitzit(variant, mgrid, agrid)):
                m = FA.tube_uv(pts, [(.10, .10)] * len(pts), 5)
                P.add('Tzitzit%02d' % k, 'RV4_Cloth', m, B.garment_skin, colour, anchors=[a] * len(m[0]), cavity_k=0)
    # ---- arms: sleeves (V4 UVs) + the V3 forearm, hand and fingers
    sleeve_mat = 'RV4_Garment' if youth else 'RV4_Cloth'
    sleeve_col = (.95, .95, .95) if youth else pal['Linen']
    sh = variant['shoulder']
    sf = C.fold_field(variant['fold_seed'] + 2, .32, ((5, 1.0), (9, .55), (13, .35)))
    prof = [(0.0, 4.8 * g, 4.6 * g), (5.0, 7.15 * g * sh, 6.85 * g), (11.0, 7.35 * g * sh, 7.05 * g),
            (18.0, 6.65 * g, 6.35 * g), (26.0, 6.05 * g, 5.80 * g), (32.0, 5.75 * g, 5.55 * g),
            (40.0, 5.20 * g, 5.00 * g), (47.0, 4.65 * g, 4.45 * g), (53.0, 4.35 * g, 4.15 * g)]
    for s in (-1, 1):
        tag = 'R' if s < 0 else 'L'
        ts = [t for t, _, _ in prof]
        pts = [C.arm_point(s, t) for t in ts]
        P.add('Sleeve' + tag, sleeve_mat,
              FA.tube_uv(pts, [(a, b) for _, a, b in prof], 28,
                         radial=lambda th, i, k=s: (sf(th + k * .8, 140 - i * 8, .70 + .60 * i / 8)
                                                    + .55 * gauss(i, 5.0, .8) * math.cos(2 * th))),
              C.sleeve_skin, sleeve_col, cavity_k=1.2)
        P.add('Cuff' + tag, sleeve_mat, FA.tube_uv([C.arm_point(s, 52.1), C.arm_point(s, 54.4)],
                                                   [(4.65 * g, 4.45 * g)] * 2, 28), C.sleeve_skin,
              (.80, .80, .80) if youth else pal['Trim'])
        C.arm_parts(P.adder({'Skin': 'RV4_Skin', 'Linen': 'RV4_Cloth', 'Trim': 'RV4_Cloth'},
                            drop=('Sleeve', 'Cuff')), variant, s)
    # ---- legs, feet, toes, sandals
    leather = pal['Leather']
    for s in (-1, 1):
        tag = 'R' if s < 0 else 'L'
        P.add('Leg' + tag, 'RV4_Skin', B.leg(variant, s), B.leg_skin, skin, closed=False, cavity_k=.8)
        fmesh, toes = B.foot(variant, s)
        P.add('Foot' + tag, 'RV4_Skin', fmesh, C.foot_skin, skin, cavity_k=.8)
        for i, (pts, radii) in enumerate(toes):
            P.add('Toe%s%d' % (tag, i), 'RV4_Skin', FA.tube_uv(pts, radii, 8), C.foot_skin, skin, cavity_k=0)
        sole, straps = B.sandal(variant, s)
        P.add('SandalSole' + tag, 'RV4_Leather', sole, C.foot_skin, leather)
        for i, pts in enumerate(straps):
            ankle = i == len(straps) - 1
            P.add('SandalStrap%s%d' % (tag, i), 'RV4_Leather', FA.tube_uv(pts, [(.55, .22)] * len(pts), 8),
                  B.leg_skin if ankle else C.foot_skin, R_shade(leather, 1.15), cavity_k=0)
    return P.parts


def finalize(parts, variant):
    """Morph deltas on head-region parts, then split UV seams (every per-vertex list follows)."""
    import create_resident_v4_face as FA
    F = variant['face']
    out = []
    for p in parts:
        n = len(p['vertices'])
        if p['morph']:
            md, nd = [], []
            disp = [[FA.morph_disp(k, q, F) for k in range(len(MORPHS))] for q in p['vertices']]
            new_normals = []
            for k in range(len(MORPHS)):
                moved = dict(p, vertices=[add(q, d[k]) for q, d in zip(p['vertices'], disp)])
                new_normals.append(C.normals(moved))
            for i in range(n):
                md.append(tuple(disp[i]))
                nd.append(tuple(sub(new_normals[k][i], p['normals'][i]) for k in range(len(MORPHS))))
            p['mdelta'], p['ndelta'] = md, nd
        out.append(split_seams2(p))
    return out


def influence(part, i, index):
    anchors = part.get('anchors')
    weights = part['skin'](anchors[i] if anchors else part['vertices'][i])
    entries = sorted([(index[k], w) for k, w in weights.items() if w > 1e-6], key=lambda a: -a[1])[:4]
    total = sum(w for _, w in entries)
    entries = [(j, w / total) for j, w in entries]
    return entries + [(0, 0.0)] * (4 - len(entries))


# ============================================================================= export
class GLB2(C.GLB):
    def accessor(self, rows, typ, component=5126, target=None, bounds_=False, normalized=False):
        sizes = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
        n = sizes[typ]
        flat = [x for row in rows for x in row] if n > 1 else rows
        while len(self.buffer) % 4:
            self.buffer.append(0)
        offset = len(self.buffer)
        fmt = {5126: 'f', 5123: 'H', 5125: 'I'}[component]
        self.buffer.extend(struct.pack('<' + fmt * len(flat), *flat))
        view = {'buffer': 0, 'byteOffset': offset, 'byteLength': len(self.buffer) - offset}
        if target:
            view['target'] = target
        vi = len(self.doc['bufferViews'])
        self.doc['bufferViews'].append(view)
        entry = {'bufferView': vi, 'componentType': component, 'count': len(rows), 'type': typ}
        if bounds_:
            values = struct.unpack('<' + fmt * len(flat), self.buffer[offset:])
            entry['min'] = [min(values[k::n]) for k in range(n)]
            entry['max'] = [max(values[k::n]) for k in range(n)]
        self.doc['accessors'].append(entry)
        return len(self.doc['accessors']) - 1


def gvec(p):
    return [p[0] * .01, p[2] * .01, -p[1] * .01]


def export_glb(path, parts, bones, index, variant):
    asset = GLB2('Original ResidentV4 Python author (Scripts/create_resident_v4.py, %s)' % variant['id'])
    doc = asset.doc
    for i, b in enumerate(bones):
        node = {'name': b['name'], 'translation': C.gltf_vec(b['local_translation_cm'])}
        kids = [j for j, k in enumerate(bones) if k['parent_index'] == i]
        if kids:
            node['children'] = kids
        doc['nodes'].append(node)
    mats = []
    for b in bones:
        x, y, z = C.gltf_vec(b['position_cm'])
        mats.append([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1])
    doc['skins'] = [{'name': 'OriginalPilgrimHumanoid', 'joints': list(range(len(bones))), 'skeleton': 0,
                     'inverseBindMatrices': asset.accessor(mats, 'MAT4')}]
    prims = []
    zero3 = (0.0, 0.0, 0.0)
    for mat, (rough, spec, _) in SLOTS.items():
        members = [p for p in parts if p['material'] == mat]
        if not members:
            continue
        doc['materials'].append({'name': mat, 'pbrMetallicRoughness': {
            'baseColorFactor': [1., 1., 1., 1.], 'metallicFactor': 0.0, 'roughnessFactor': rough}})
        pos, nor, uvs, col, jo, we, idx = [], [], [], [], [], [], []
        tpos = [[] for _ in MORPHS]
        tnor = [[] for _ in MORPHS]
        for p in members:
            o = len(pos)
            pos += [gvec(q) for q in p['vertices']]
            nor += [[n[0], n[2], -n[1]] for n in p['normals']]
            uvs += [[u, v] for u, v in p['uv']]
            col += [[clamp(c[0]), clamp(c[1]), clamp(c[2]), 1.0] for c in p['colours']]
            for i in range(len(p['vertices'])):
                inf = influence(p, i, index)
                jo.append([j for j, _ in inf])
                we.append([w for _, w in inf])
                for k in range(len(MORPHS)):
                    d = p['mdelta'][i][k] if p.get('mdelta') else zero3
                    nd = p['ndelta'][i][k] if p.get('ndelta') else zero3
                    tpos[k].append(gvec(d))
                    tnor[k].append([nd[0], nd[2], -nd[1]])
            idx += [o + i for face in p['faces'] for i in face]
        attrs = {'POSITION': asset.accessor(pos, 'VEC3', target=34962, bounds_=True),
                 'NORMAL': asset.accessor(nor, 'VEC3', target=34962),
                 'TEXCOORD_0': asset.accessor(uvs, 'VEC2', target=34962),
                 'COLOR_0': asset.accessor(col, 'VEC4', target=34962),
                 'JOINTS_0': asset.accessor(jo, 'VEC4', 5123, target=34962),
                 'WEIGHTS_0': asset.accessor(we, 'VEC4', target=34962)}
        targets = [{'POSITION': asset.accessor(tpos[k], 'VEC3', bounds_=True),
                    'NORMAL': asset.accessor(tnor[k], 'VEC3')} for k in range(len(MORPHS))]
        prims.append({'attributes': attrs, 'indices': asset.accessor(idx, 'SCALAR', 5125, 34963),
                      'material': len(doc['materials']) - 1, 'mode': 4, 'targets': targets})
    doc['meshes'] = [{'name': variant['mesh_id'], 'primitives': prims, 'weights': [0.0] * len(MORPHS),
                      'extras': {'targetNames': list(MORPHS)}}]
    doc['nodes'].append({'name': variant['mesh_id'] + '_Mesh', 'mesh': 0, 'skin': 0})
    doc['scenes'] = [{'name': 'ResidentV4', 'nodes': [0, len(bones)]}]
    doc['extras'] = {'variant': variant['id'],
                     'provenance': 'Original mesh authored in this project (Scripts/create_resident_v4.py).',
                     'coordinates': 'Author centimetres XYZ, front -Y, Z up; glTF metres X,Z,-Y.',
                     'vertexColour': 'COLOR_0 is LINEAR RGB (tint, pattern and baked cavity).',
                     'uv': 'TEXCOORD_0 = centimetres / 10 on every part; periodic seams split.',
                     'morphTargets': list(MORPHS)}
    asset.save(path)


# ============================================================================= previews, checks, build
def posed(parts, variant, clip, t):
    import numpy as np
    import measure_kohen_garment_clearance as M
    from measure_pilgrim_walk import Rig
    bones = C.skeleton()
    index = {b['name']: i for i, b in enumerate(bones)}
    glb = M.RIG3 / 'walk-v2/meshes' / (variant['id'] + '.glb')
    name = {'walk': 'A_Pilgrim_Original_Walk', 'idle': 'A_Pilgrim_Original_Idle'}[clip]
    rig = Rig(glb, name)
    A, b = M.joint_affines(rig, rig.pose(t), bones)
    out = []
    for p in parts:
        v = np.array(p['vertices'], dtype=np.float64)
        J = np.zeros((len(v), 4), dtype=np.int32)
        W = np.zeros((len(v), 4))
        for i in range(len(v)):
            for k, (j, w) in enumerate(influence(p, i, index)):
                J[i, k], W[i, k] = j, w
        out.append((p, [tuple(r) for r in M.skin(v, J, W, A, b)]))
    return out


def previews(parts, variant, folder):
    folder.mkdir(parents=True, exist_ok=True)
    shots = []
    # previews only: the garment slot is neutral in the mesh (the population's instance colours it in
    # engine), so tint it with this variant's own mantle colour or the review sees white cloth
    tint = C.variant_materials(variant)['Mantle']
    parts = [dict(p, colours=[tuple(a * b for a, b in zip(c, tint)) for c in p['colours']])
             if p['material'] == 'RV4_Garment' else p for p in parts]
    rest = [(p, p['vertices']) for p in parts]
    for name, yaw in (('front', 0.0), ('three-quarter', .62), ('side', math.pi / 2), ('back', math.pi)):
        f = folder / ('%s-rest-%s.png' % (variant['id'], name))
        K.render_vc(rest, f, yaw)
        shots.append(f.name)
    f = folder / ('%s-face-three-quarter.png' % variant['id'])
    K.render_vc(rest, f, .55, width=420, height=460, top=184.0, scale=16.0)
    shots.append(f.name)
    for t in (.30, .60):
        f = folder / ('%s-walk-t%.2f-side.png' % (variant['id'], t))
        K.render_vc(posed(parts, variant, 'walk', t), f, math.pi / 2)
        shots.append(f.name)
    return shots


SOURCES = [
    {'id': 'RV4-TZITZIT', 'grade': 'S', 'claim': 'tassels with a thread of techelet on the four corners of a man\'s four-cornered garment',
     'source': 'Numbers 15:38-39; Deuteronomy 22:12', 'authored': 'string count drawn (8), length, placement on this draped panel'},
    {'id': 'RV4-TZITZIT-WOMEN', 'grade': 'S', 'claim': 'no tzitzit on the women\'s mantles', 'source': 'Menachot 43a (time-bound precept)'},
    {'id': 'RV4-HAIR-COVER', 'grade': 'S', 'claim': 'married women cover their hair in public',
     'source': 'Mishnah Ketubot 7:6', 'authored': 'the shawl-over-the-head form and the hair showing at the brow'},
    {'id': 'RV4-CLAVI', 'grade': 'R', 'claim': 'tunic with two coloured vertical bands over the shoulders; mantle corners with notched bands',
     'source': 'Y. Yadin, The Finds from the Bar-Kokhba Period in the Cave of Letters (1963) - cited from general knowledge, NOT re-read in this pass'},
    {'id': 'RV4-SANDALS', 'grade': 'R', 'claim': 'leather sandals with toe and instep thongs',
     'source': 'Cave of Letters / Masada finds - cited from general knowledge, NOT re-read in this pass'},
    {'id': 'RV4-AUTHORED', 'grade': 'A', 'claim': 'every face, colour, hem height, fold amplitude, the bloused belt, all clearance offsets'},
]


def build(only=None, fast=False):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'meshes').mkdir(exist_ok=True)
    bones = C.skeleton()
    rig = C.assert_rig_matches_v2(bones)
    index = {b['name']: i for i, b in enumerate(bones)}
    manifest = {'generatedUtc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'generator': 'Scripts/create_resident_v4.py',
                'generatorSha256': {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in
                                    ('create_resident_v4.py', 'create_resident_v4_face.py', 'create_resident_v4_body.py')},
                'skeleton': 'C.skeleton() unchanged: import onto each variant\'s EXISTING V3 Skeleton',
                'rigCompatibility': rig, 'jointNames': sorted(b['name'] for b in bones),
                'slots': {k: {'roughness': v[0], 'specular': v[1], 'master': v[2]} for k, v in SLOTS.items()},
                'garmentSlot': 'RV4_Garment', 'morphTargets': list(MORPHS), 'uvCm': UV_CM,
                'triangleBudget': TRIANGLE_BUDGET, 'sources': SOURCES, 'variants': []}
    prints = {}
    for vid in CAST:
        if only and vid not in only:
            continue
        t0 = time.time()
        v = variant(vid)
        parts = finalize(assembly(v), v)
        tris = sum(len(p['faces']) for p in parts)
        by = {}
        for p in parts:
            by[p['material']] = by.get(p['material'], 0) + len(p['faces'])
        assert tris <= TRIANGLE_BUDGET, (vid, tris)
        path = OUT / 'meshes' / (v['mesh_id'] + '.glb')
        export_glb(path, parts, bones, index, v)
        fp = hashlib.sha256(b''.join(struct.pack('<3f', *q) for p in parts if p['name'] == 'Head'
                                     for q in p['vertices'])).hexdigest()
        assert fp not in prints.values(), ('two variants share a face', vid)
        prints[vid] = fp
        row = {'id': vid, 'mesh': v['mesh_id'], 'file': 'meshes/' + path.name,
               'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'triangles': tris,
               'trianglesByMaterial': by, 'vertices': sum(len(p['vertices']) for p in parts),
               'parts': len(parts), 'faceFingerprint': fp, 'face': v['face'], 'dress': DRESS[vid],
               'materialsUsed': sorted(by), 'seconds': round(time.time() - t0, 1)}
        if not fast:
            row['previews'] = previews(parts, v, OUT / 'previews')
        manifest['variants'].append(row)
        print('%-26s %6d tris  %5.1fs' % (vid, tris, time.time() - t0), flush=True)
    name = 'resident-v4-manifest.json' if not only else 'resident-v4-manifest-partial.json'
    (OUT / name).write_text(json.dumps(manifest, indent=2, default=str) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--fast', action='store_true', help='GLBs + manifest, no previews')
    ap.add_argument('--only', nargs='*')
    a = ap.parse_args()
    if a.build:
        build(set(a.only) if a.only else None, a.fast)
    else:
        ap.print_help()

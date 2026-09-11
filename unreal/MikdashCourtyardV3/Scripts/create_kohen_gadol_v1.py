"""The Kohen Gadol in the eight golden garments, as ONE skinned body on the PilgrimRigV3 27-bone rig.

Offline Python -> GLB, the same pipeline as Scripts/create_pilgrim_v3.py (which it imports and does
NOT modify: the 24 residents and V3_Kohen_White keep their meshes). The skeleton is C.skeleton()
unchanged - identical names, hierarchy and rest positions - so the mesh imports onto the EXISTING
V3_Pilgrim_Man_Standard Skeleton and plays the shipped Idle / WalkV2 / TendLamp clips as they are.

  python Scripts/create_kohen_gadol_v1.py --build          GLB + manifest + previews + clearance
  python Scripts/create_kohen_gadol_v1.py --build --fast   GLB + manifest only

SOURCES (what is sourced and what is authored is also written into the manifest and sources.md)
  Book "Lishchno Tidreshu", PDF p. 350 (printed p. 245), figure 2 "Kohen Gadol wearing 8 golden
  garments" (figure 3 is the Yom Kippur white set). It shows: a white checkered ketonet with long
  sleeves to just above the feet; a sleeveless techelet me'il to the lower shin; the ephod "ma'aseh
  choshev" behind and at the sides from the belt to about 40 cm above the floor, open at the front;
  its belt knotted at the front with two hanging ends; the choshen, 4 x 3 stones, on gold chains to
  the shoulders; a wound mitznefet with the tzitz on the forehead and a cord up its front; avnet and
  michnasayim labelled "under the garments"; bare feet.
  Rambam, Klei HaMikdash 8:1-2 (eight garments), 8:15 (ketonet boxed weave, to just above the heel,
  sleeves to the wrist), 9:1-2 (tzitz two fingerbreadths, ear to ear, techelet cord at the nape),
  9:3-4 (me'il all techelet, no sleeves, woven neck; 72 gold bells and 72 closed pomegranates of
  techelet, argaman and tola'at shani, alternating on the hem), 9:5 (28-ply thread with gold),
  9:6 (choshen a zeret square), 9:8-10 (rings, gold chains above, techelet cords below; ephod
  behind, choshen over the heart, shoham stones on the shoulder straps).
AUTHORED (the book and Rambam are silent): every colour value except those sampled from the book
figure, the checker size, the ephod's floral weave pattern (it follows the book's rendered cloth),
the mitznefet's exact shape and wrap count, stone colours beyond the book figure's own swatches,
fold amplitudes, and every clearance offset. The tzitz inscription is NOT modelled (below mesh
resolution at 2 m); the hidden avnet and michnasayim are not modelled (book: under the garments).

CLOTH SKINNING (the clipping fix). The pilgrim robe follows skirt_r/skirt_l, which the clip drives at
0.45 of the hip-ankle angle; against the 72 cm stride that leaves the shin up to ~24 cm outside the
robe. Here every lower garment (ketonet, me'il, ephod, bells) uses ONE weight field over rest space:
pelvis at the hip line, handing over to the SAME-SIDE thigh by z 74 and to the calf below the knee,
split left/right by a band that is wide at the thigh (a soft front) and narrow at the hem (so the
cloth round each shin travels with that shin). The existing clips' thigh and calf tracks carry it;
no new bone and no new clip. Measured by Scripts/measure_kohen_garment_clearance.py.
"""
import argparse
import hashlib
import json
import math
import random
import struct
import sys
import time
import zlib
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import create_pilgrim_v3 as C                                   # noqa: E402
from create_pilgrim_v3 import (add, sub, scale, dot, cross, length, normalize, clamp, smooth,  # noqa: E402
                               gauss, loft, tube, ellipsoid, cloth_panel, box, fold_field,
                               HEAD_C, HEAD_RX, HEAD_RY, HEAD_RZ)

OUT = ROOT / 'SourceAssets/characters-review/KohenGadolV1'
MESH_ID = 'SK_KohenGadol_V1'
VARIANT = dict(id='V3_KohenGadol_Gold', label='Kohen Gadol, eight golden garments',
               dress='kohen', girth=1.00, shoulder=1.02, age=.62, beard='full', headwear='mitznefet',
               mantle=False, tunic_hem=6.0, barefoot=True, prop=None, skin_tone='olive-grey',
               actor_scale=1.00, fold_seed=131)
TRIANGLE_BUDGET = 90000

# ----------------------------------------------------------------------------- dimensions (cm)
KETONET_HEM = 6.0          # Rambam 8:15 "until slightly above the heel"; book fig.: just above the feet
MEIL_HEM = 18.0            # book fig. 2: me'il to the lower shin (measured off the figure, ~18 cm)
EPHOD_BOTTOM = 40.0        # book fig. 2: ~40 cm above the floor (Rambam 9:9 says "to the feet": R)
EPHOD_TOP = 107.8
EPHOD_FRONT_EDGE_X = 11.5  # book fig. 2: the me'il shows at the front between the ephod's edges
BELT = (101.4, 108.6)
CHOSHEN_C = (0.0, 122.0)   # book fig. 2: directly above the belt; Rambam 9:10 "over the heart"
CHOSHEN_SIDE = 23.0        # Rambam 9:6 a zeret square; zeret = half an amah = 24 cm at 48 cm (drawn 23)
TZITZ_H = 3.8              # Rambam 9:1 two fingerbreadths (2 x ~2 cm)
OFF_MEIL, OFF_EPHOD, OFF_BELT = 2.2, 3.5, 4.7   # outward from the ketonet surface (authored)

KETONET_SEGMENTS = 176     # 0.85 cm at the hem: fine enough for a 3.2 cm vertex-colour checker
MEIL_SEGMENTS = 176        # SAME angles as the ketonet: the me'il is then an exact radial offset of
                           # it, which is what keeps the ketonet inside it through the centre shear
CHECK_CM = 3.2             # authored checker cell ("boxlike", Rambam 8:15, size not given)

# ----------------------------------------------------------------------------- skin field
BAND_HEM, BAND_THIGH = 6.0, 14.0   # hem band 6 cm: measured sweep 2.2 -> 0.84 cm, 3.6 -> 0.25, 4.4 -> 0.03, 6.0 -> 0
F_TOP, F_FULL = 99.0, 74.0
KNEE_TOP, KNEE_BOT = 52.0, 30.0
F_MAX = 1.0


def srgb(c):
    return tuple(round(max(0.0, v) ** 2.2, 4) for v in c)


# Linear colours. BOOK = sampled off the book figure (sRGB, converted); others authored.
COL = {
    'linenA': (.830, .815, .775), 'linenB': (.690, .676, .640), 'turban': (.800, .790, .760),
    'meil': srgb((.36, .56, .80)),                     # BOOK me'il blue (.40,.60,.82), a shade deeper
    'meilDark': srgb((.24, .40, .64)),
    'ephodRed': srgb((.56, .17, .16)),                 # BOOK ephod ground (.51,.17,.17)
    'ephodPurple': srgb((.42, .30, .60)),              # BOOK floral motif (authored reading)
    'techelet': srgb((.20, .36, .66)),
    'argaman': srgb((.45, .12, .42)),
    'shani': srgb((.72, .08, .10)),
    'goldThread': srgb((.86, .68, .30)),
    'shesh': (.80, .79, .76),
    'gold': (1.0, .766, .336),
    'skin': (.440, .268, .175), 'hair': (.690, .676, .640),
    'eyes': (.760, .742, .715), 'iris': (.135, .098, .062),
}
# Choshen stones, viewer's left to right, top row first, sampled off the book figure (sRGB).
BOOK_STONES = [
    [(.46, .16, .20), (.30, .66, .38), (.74, .30, .36)],
    [(.90, .89, .87), (.36, .38, .50), (.72, .84, .90)],
    [(.84, .20, .22), (.86, .85, .83), (.50, .70, .90)],
    [(.16, .15, .17), (.44, .46, .56), (.97, .97, .96)],
]
SHOHAM = [srgb((.14, .09, .07)), srgb((.62, .52, .42))]   # banded sardonyx (authored, R: identity)

# Slot -> (roughness, metallic, specular) for the engine material instances.
SLOTS = {
    'KG_Linen': (.90, 0.0, .45), 'KG_Meil': (.92, 0.0, .40), 'KG_Ephod': (.58, .28, .50),
    'KG_Gold': (.30, 1.0, .50), 'KG_Stones': (.08, 0.0, .90), 'KG_Wool': (.90, 0.0, .40),
    'KG_Skin': (.70, 0.0, .45), 'KG_Hair': (.88, 0.0, .35), 'KG_Eyes': (.30, 0.0, .50),
    'KG_Iris': (.28, 0.0, .50),
}
RENAME = {'Skin': 'KG_Skin', 'Hair': 'KG_Hair', 'Eyes': 'KG_Eyes', 'Iris': 'KG_Iris',
          'Linen': 'KG_Linen', 'Trim': 'KG_Linen', 'Headcloth': 'KG_Linen'}
SLOT_DEFAULT = {'KG_Skin': COL['skin'], 'KG_Hair': COL['hair'], 'KG_Eyes': COL['eyes'],
                'KG_Iris': COL['iris'], 'KG_Linen': COL['linenA'], 'KG_Meil': COL['meil'],
                'KG_Ephod': COL['ephodRed'], 'KG_Gold': COL['gold'], 'KG_Stones': (.5, .5, .5),
                'KG_Wool': COL['techelet']}


def lerp3(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


# ============================================================================= skinning
def lower_skin(p):
    """Pelvis at the hip line -> same-side thigh by z 74 -> calf below the knee."""
    x, y, z = p
    f = F_MAX * smooth(clamp((F_TOP - z) / (F_TOP - F_FULL)))
    k = smooth(clamp((KNEE_TOP - z) / (KNEE_TOP - KNEE_BOT)))
    band = BAND_HEM + (BAND_THIGH - BAND_HEM) * smooth(clamp((z - 25.0) / (F_FULL - 25.0)))
    s = smooth(clamp((x + band) / (2.0 * band)))          # 0 = right side (x < 0), 1 = left
    # Below z 21 the SHIN itself is skinned calf -> foot (C.leg_skin: foot weight 1 - (z - 5) / 16),
    # so the cloth round it takes the same split; otherwise the ankle's rotation moves the lower
    # shin up to ~3 cm relative to a calf-only hem.
    ft = 1.0 - clamp((z - 5.0) / 16.0)
    return {'pelvis': 1.0 - f,
            'thigh_r': f * (1 - s) * (1 - k), 'calf_r': f * (1 - s) * k * (1 - ft), 'foot_r': f * (1 - s) * k * ft,
            'thigh_l': f * s * (1 - k), 'calf_l': f * s * k * (1 - ft), 'foot_l': f * s * k * ft}


def garment_skin(p):
    return C.torso_skin(p) if p[2] >= F_TOP else lower_skin(p)


def influence(part, p, index):
    """Skin weights. Outer layers carry an anchor per vertex: the KETONET point they are offset
    from. Evaluating the field there, not at the vertex, gives every layer identical weights, so a
    0.2 cm radial offset cannot turn into centimetres of relative motion in the narrow centre band."""
    weights = part['skin'](part.get('anchor_map', {}).get(p, p))
    entries = sorted([(index[k], w) for k, w in weights.items() if w > 1e-6], key=lambda a: -a[1])[:4]
    total = sum(w for _, w in entries)
    entries = [(j, w / total) for j, w in entries]
    return entries + [(0, 0.0)] * (4 - len(entries))


# ============================================================================= ketonet profile
def fold_damp(z):
    """The hidden avnet cinches the ketonet at the waist, so folds die out there."""
    return 1.0 - .75 * gauss(z, 104.0, 6.5)


_FOLDS = fold_field(VARIANT['fold_seed'], 1.30)


TOE_EASE_CM = 3.4
CENTRE_EASE_CM = 3.0     # lower front/back centre ease (authored)
LEG_FRONT_T = (1.5 * math.pi - .35, 1.5 * math.pi + .35)   # loft angles in front of each foot


def ketonet_radial(t, z):
    f = .62 * _FOLDS(t, z, C.tunic_amplitude(z, KETONET_HEM)) * fold_damp(z)
    if z < 74.0:
        # The pilgrims' "two columns" term also pulls the front and back centre IN (cos 2t = -1);
        # on a 72 cm stride that centre cloth sweeps diagonally across the stance shin. Keep only
        # the push-out over the legs, and ease the lower front and back centre OUT instead.
        f += 2.4 * max(0.0, math.cos(2 * t)) * smooth((74.0 - z) / 42.0)
    if z < 44.0:
        centre = sum(math.exp(-(((t - c + math.pi) % math.tau - math.pi) / .42) ** 2)
                     for c in (.5 * math.pi, 1.5 * math.pi))
        f += CENTRE_EASE_CM * centre * smooth((44.0 - z) / 26.0)
    if z < 30.0:
        # Ease over the instep in front of each foot, so the hem rides over the toes at heel
        # strike instead of the dorsiflexed foot rising past it (authored).
        ease = sum(math.exp(-(((t - c + math.pi) % math.tau - math.pi) / .32) ** 2) for c in LEG_FRONT_T)
        f += TOE_EASE_CM * ease * smooth((30.0 - z) / 18.0)
    return f


def ketonet_exponent(z, level=0):
    bump = smooth((z - 92) / 14) * smooth((140 - z) / 16)
    return 1.0 - .17 * bump


def ring_zs(start, dense_top=21.5, dense=.8, step=3.5):
    zs, z = [], start
    while z < dense_top:
        zs.append(round(z, 3)); z += dense
    while z < 100.0:
        zs.append(round(z, 3)); z += step
    for az, _, _ in C.GARMENT_ANCHORS:
        if az > zs[-1] + 1.0:
            zs.append(az)
    return zs


def section(z, g=1.0, sh=1.02):
    rx, ry = C.anchor_at(z)
    return rx * g * (sh if z > 130 else 1.0), ry * g


HEM_FRONT_RISE = 1.6       # C uses 2.8; lower so the front hem covers more of the instep


def hem_break(t, level, k=1.0):
    if level > 2:
        return 0.0
    kk = (1.0, .85, .35)[level] * k
    return kk * (HEM_FRONT_RISE * max(0.0, -math.sin(t)) - 1.5 * max(0.0, math.sin(t)))


def surface_point(t, z, offset, g=1.0, sh=1.02):
    """Point on the ketonet surface (+offset outward) at loft angle t, height z (no hem break)."""
    rx, ry = section(z, g, sh)
    e = ketonet_exponent(z)
    f = ketonet_radial(t, z) + offset
    ct, st = math.cos(t), math.sin(t)
    ct = math.copysign(abs(ct) ** e, ct)
    st = math.copysign(abs(st) ** e, st)
    return ((rx + f) * ct, (ry + f) * st, z)


def surface_y(x, z, offset, back):
    """y of the (offset) surface where it crosses x at height z, front (back=False) or back."""
    best = None
    lo, hi = (0.0, math.pi) if back else (math.pi, 2 * math.pi)
    for i in range(721):
        t = lo + (hi - lo) * i / 720
        p = surface_point(t, z, offset)
        d = abs(p[0] - x)
        if best is None or d < best[0]:
            best = (d, p[1], t)
    return best[1], best[2]


# ============================================================================= colours
def ketonet_colour(t, z):
    u = int(math.floor(t * 23.5 / CHECK_CM))
    v = int(math.floor((z - KETONET_HEM) / CHECK_CM))
    return COL['linenA'] if (u + v) % 2 == 0 else COL['linenB']


def _noise(u, v, seed):
    rng = random.Random(seed)
    s = 0.0
    for f, a in ((.11, 1.0), (.23, .55), (.47, .28)):
        ph1, ph2, ang = rng.uniform(0, 6.3), rng.uniform(0, 6.3), rng.uniform(0, 3.1)
        ca, sa = math.cos(ang), math.sin(ang)
        s += a * math.sin(f * (u * ca + v * sa) + ph1) * math.cos(f * (-u * sa + v * ca) + ph2)
    return s / 1.83


def ephod_colour(u, v):
    """Woven ground of argaman / tola'at shani with techelet, gold and shesh threads (Rambam 9:5),
    carrying the book figure's purple-blue floral motif as low-frequency blotches (authored)."""
    motif = smooth(clamp((_noise(u, v, 7) - .10) / .30))
    c = lerp3(COL['ephodRed'], COL['ephodPurple'], .90 * motif)
    # the 28-ply thread (Rambam 9:5): gold and the other colours read as a fine sheen, not dots
    sheen = .5 + .5 * math.sin(u * 2.1 + 1.3 * math.sin(v * .9)) * math.sin(v * 2.3)
    c = lerp3(c, COL['goldThread'], .04 + .06 * sheen)      # a sheen; the book's cloth reads deep red
    h = (int(u * 1.37) * 73856093 ^ int(v * 1.61) * 19349663) & 1023
    if h < 22:
        c = lerp3(c, COL['techelet'], .35)
    elif h < 36:
        c = lerp3(c, COL['shesh'], .25)
    return c


# ============================================================================= parts
class Parts:
    def __init__(self):
        self.parts = []

    def add(self, name, material, mesh, skin, colours=None, anchors=None):
        v, f = mesh
        volume = sum(dot(v[a], cross(v[b], v[c])) / 6 for a, b, c in f)
        if volume < 0:
            f = [(a, c, b) for a, b, c in f]
        if colours is None:
            colours = [SLOT_DEFAULT[material]] * len(v)
        elif callable(colours):
            colours = [colours(p, i) for i, p in enumerate(v)]
        assert len(colours) == len(v), name
        part = {'name': name, 'material': material, 'vertices': v, 'faces': f,
                'skin': skin, 'colours': colours}
        if anchors is not None:
            assert len(anchors) == len(v), name
            part['anchor_map'] = {tuple(a): tuple(b) for a, b in zip(v, anchors)}
        self.parts.append(part)

    def adder(self, drop=(), rename=RENAME):
        def add_(name, material, mesh, skin):
            if name.startswith(tuple(drop)):
                return
            self.add(name, rename.get(material, material), mesh, skin)
        return add_


def ketonet(P):
    zs = ring_zs(KETONET_HEM)
    rings = []
    for z in zs:
        rx, ry = section(z)
        rings.append((z, rx, ry, 0.0, 0.0))
    # OPEN at the hem, as a robe is: a hem cap becomes a slanted membrane between the legs once
    # the hem shears with the stride (it showed as a white sheet between the feet).
    v, f = loft(rings, KETONET_SEGMENTS, radial=lambda t, z, l: ketonet_radial(t, z),
                exponent=ketonet_exponent, zshift=lambda t, l: hem_break(t, l), cap=False)
    cols = []
    for i, p in enumerate(v):
        if i < len(zs) * KETONET_SEGMENTS:
            t = (i % KETONET_SEGMENTS) * math.tau / KETONET_SEGMENTS
            cols.append(ketonet_colour(t, zs[i // KETONET_SEGMENTS]))
        else:
            cols.append(COL['linenA'])
    P.add('Ketonet', 'KG_Linen', (v, f), garment_skin, cols)
    P.add('KetonetCollar', 'KG_Linen', loft([(148.2, 12.9, 9.4, 0, 0), (149.2, 13.4, 9.8, 0, 0),
                                             (151.4, 8.6, 7.3, 0, 0), (152.2, 7.9, 6.8, 0, 0)], 26),
          C.torso_skin)


def meil(P):
    """Solid techelet, sleeveless, woven neck (Rambam 9:3); hem at the lower shin (book)."""
    # EXACTLY the ketonet's ring heights above the me'il hem: the folds drift in phase with height,
    # so a different ring set would chord inside the ketonet between rings.
    zs = [z for z in ring_zs(KETONET_HEM) if MEIL_HEM - 1e-6 <= z <= 150.5]
    assert abs(zs[0] - MEIL_HEM) < 1e-6, zs[:3]
    rings = [(z,) + section(z) + (0.0, 0.0) for z in zs]
    v, f = loft(rings, MEIL_SEGMENTS, radial=lambda t, z, l: ketonet_radial(t, z) + OFF_MEIL,
                exponent=ketonet_exponent, cap=False)   # hem level: an exact offset of the ketonet ring
    v0, _ = loft(rings, MEIL_SEGMENTS, radial=lambda t, z, l: ketonet_radial(t, z),
                 exponent=ketonet_exponent, cap=False)   # hem level: an exact offset of the ketonet ring
    shade = []
    for i, p in enumerate(v):
        shade.append(lerp3(COL['meil'], COL['meilDark'], .10 + .08 * math.sin(p[2] * .9 + i * .37)))
    P.add('Meil', 'KG_Meil', (v, f), garment_skin, shade, anchors=v0)
    hem = v[:MEIL_SEGMENTS] + [v[0]]
    hem0 = v0[:MEIL_SEGMENTS] + [v0[0]]
    bv, bf = tube([add(p, (0, 0, .15)) for p in hem], [(.45, .45)] * len(hem), 6)
    banch = [hem0[min(i // 6, len(hem0) - 1)] for i in range(len(hem) * 6)] + [hem0[0], hem0[-1]]
    P.add('MeilHemBinding', 'KG_Meil', (bv, bf), garment_skin, lambda p, i: COL['meilDark'], anchors=banch)
    top = len(zs) - 1
    neck = v[top * MEIL_SEGMENTS:(top + 1) * MEIL_SEGMENTS] + [v[top * MEIL_SEGMENTS]]
    P.add('MeilNeckBinding', 'KG_Meil', tube(neck, [(.65, .65)] * len(neck), 8), C.torso_skin,
          lambda p, i: COL['meilDark'])
    return v, v0


def bells_and_pomegranates(P, meil_vv):
    """72 gold bells and 72 closed pomegranates, alternating on the hem (Rambam 9:4)."""
    meil_v, meil_v0 = meil_vv
    bell_v, bell_f, pom_v, pom_f, pom_c = [], [], [], [], []
    bell_a, pom_a = [], []
    n = 144
    for i in range(n):
        t = (i + .5) * math.tau / n
        j = int(round(t / math.tau * MEIL_SEGMENTS)) % MEIL_SEGMENTS
        base = meil_v[j]
        out = normalize((math.cos(t), math.sin(t), 0.0))
        c = add(base, scale(out, .55))
        if i % 2 == 0:
            rings = [(c[2] - .15, .22, .22, c[0], c[1]), (c[2] - .45, .45, .45, c[0], c[1]),
                     (c[2] - 1.00, .66, .66, c[0], c[1]), (c[2] - 1.35, .72, .72, c[0], c[1]),
                     (c[2] - 1.45, .58, .58, c[0], c[1])]
            v, f = loft(rings, 6)
            o = len(bell_v); bell_v += v; bell_f += [(a + o, b + o, d + o) for a, b, d in f]
            bell_a += [meil_v0[j]] * len(v)
        else:
            v, f = ellipsoid((c[0], c[1], c[2] - 1.25), (.62, .62, .95), 6, 5)
            o = len(pom_v); pom_v += v; pom_f += [(a + o, b + o, d + o) for a, b, d in f]
            pom_a += [meil_v0[j]] * len(v)
            for p in v:                                  # three twisted wools, as three bands
                a = (math.atan2(p[1] - c[1], p[0] - c[0]) + p[2] * 2.2) % math.tau
                pom_c.append((COL['techelet'], COL['argaman'], COL['shani'])[int(a / math.tau * 3) % 3])
    P.add('MeilBells', 'KG_Gold', (bell_v, bell_f), garment_skin, anchors=bell_a)
    P.add('MeilPomegranates', 'KG_Wool', (pom_v, pom_f), garment_skin, pom_c, anchors=pom_a)


def ephod(P):
    """Apron behind and at the sides, belt to ~40 cm (book fig.), open at the front."""
    rows, rstep = [], 2.0
    z = EPHOD_TOP
    while z > EPHOD_BOTTOM:
        rows.append(z); z -= rstep
    rows.append(EPHOD_BOTTOM)
    rx0, _ = section(70.0)
    delta = math.asin(clamp(EPHOD_FRONT_EDGE_X / (rx0 + 3.0), 0, .99))
    t0, t1 = -math.pi / 2 + delta, 3 * math.pi / 2 - delta
    cols = 64
    grid, colours, anchor_grid = [], [], []
    for z in rows:
        row, arow = [], []
        for c in range(cols):
            t = t0 + (t1 - t0) * c / (cols - 1)
            row.append(surface_point(t, z, OFF_EPHOD))
            arow.append(surface_point(t, z, 0.0))
        grid.append(row)
        anchor_grid.append(arow)
    v, f = cloth_panel(grid, .45)
    flat = [a for row in anchor_grid for a in row]
    arc = [(c / (cols - 1)) * 118.0 for c in range(cols)]
    for k, p in enumerate(v):
        i = k % (len(rows) * cols)
        colours.append(ephod_colour(arc[i % cols], rows[i // cols]))
    P.add('Ephod', 'KG_Ephod', (v, f), garment_skin, colours, anchors=flat + flat)
    for side, c in ((0, 0), (1, cols - 1)):
        edge = [grid[r][c] for r in range(len(rows))]
        ea = [anchor_grid[r][c] for r in range(len(rows))]
        tv, tf = tube(edge, [(.28, .28)] * len(edge), 6)
        P.add('EphodEdge%d' % side, 'KG_Gold', (tv, tf), garment_skin,
              anchors=[ea[min(i // 6, len(ea) - 1)] for i in range(len(edge) * 6)] + [ea[0], ea[-1]])


def belt_and_knot(P):
    """The cheshev: same weave as the ephod, tied at the front (book fig. 2)."""
    zs = [BELT[0], BELT[0] + .9, (BELT[0] + BELT[1]) / 2, BELT[1] - .9, BELT[1]]
    pads = [.5, 1.0, 1.1, 1.0, .5]
    v, f = [], []
    seg = 96
    for li, z in enumerate(zs):
        mx = max(ketonet_radial(i * math.tau / 96, z) for i in range(96))
        for i in range(seg):
            t = i * math.tau / seg
            rx, ry = section(z)
            e = ketonet_exponent(z)
            ct, st = math.cos(t), math.sin(t)
            ct = math.copysign(abs(ct) ** e, ct)
            st = math.copysign(abs(st) ** e, st)
            r = mx + OFF_BELT + pads[li] - 1.0
            v.append(((rx + r) * ct, (ry + r) * st, z))
    for j in range(len(zs) - 1):
        for i in range(seg):
            a = j * seg + i; b = j * seg + (i + 1) % seg
            f += [(a, b, b + seg), (a, b + seg, a + seg)]
    cols = [ephod_colour(i % seg * 1.15, zs[i // seg] * 3) for i in range(len(v))]
    P.add('Cheshev', 'KG_Ephod', (v, f), garment_skin, cols)
    front = min(p[1] for p in v)
    knot_c = (0.0, front - 1.4, 104.6)
    P.add('CheshevKnot', 'KG_Ephod', ellipsoid(knot_c, (3.3, 2.2, 2.7), 18, 10,
          lambda p: (p[0] * (1 + .12 * math.sin(p[2] * 3)), p[1], p[2] * (1 + .10 * math.cos(p[0] * 2)))),
          garment_skin, lambda p, i: ephod_colour(p[0] * 3, p[2] * 3))
    for side in (-1, 1):
        grid = []
        for r in range(16):
            z = 102.5 - r * 1.9
            yy = min(surface_y(side * 2.6 + c, z, OFF_BELT, False)[0] for c in (-2.2, 0, 2.2)) - .6
            grid.append([(side * (1.6 + .10 * r) + c * 1.5, yy - .15 * math.sin(r * .5 + c), z)
                         for c in range(4)])
        P.add('CheshevTail%d' % side, 'KG_Ephod', cloth_panel(grid, .40), garment_skin,
              lambda p, i: ephod_colour(p[0] * 4, p[2] * 2.5))


def straps_and_shoham(P):
    """Shoulder straps of the ephod with the two shoham stones in gold settings (Rambam 9:9)."""
    settings = {}
    for side in (-1, 1):
        cols_x = [side * (13.0 + c * 2.0) for c in range(4)]
        path = []
        for z in (108.0, 114.0, 120.0, 126.0, 132.0, 138.0, 143.0, 146.5):
            path.append(('back', z))
        path += [('top', .6), ('top', .0), ('top', -.6)]
        for z in (146.5, 144.0):
            path.append(('front', z))
        grid = []
        for kind, val in path:
            row = []
            for x in cols_x:
                if kind == 'top':
                    yb, _ = surface_y(x, 148.2, OFF_EPHOD, True)
                    yf, _ = surface_y(x, 148.2, OFF_EPHOD, False)
                    row.append((x, (yb + yf) / 2 + val * (yb - yf) / 2 * .9, 149.6 - 1.4 * abs(val)))
                else:
                    y, _ = surface_y(x, val, OFF_EPHOD + .5, kind == 'back')
                    row.append((x, y, val))
            grid.append(row)
        P.add('EphodStrap%d' % side, 'KG_Ephod', cloth_panel(grid, .40), C.torso_skin,
              lambda p, i: ephod_colour(p[1] * 3, p[2] * 3))
        x = side * 16.0
        y, _ = surface_y(x, 144.5, OFF_EPHOD + .9, False)
        c = (x, y - .5, 144.5)
        settings[side] = c
        P.add('ShohamSetting%d' % side, 'KG_Gold', tube([(c[0], c[1] + .35, c[2]), (c[0], c[1] - .45, c[2])],
                                                        [(2.55, 2.1), (2.55, 2.1)], 16), C.torso_skin)
        P.add('Shoham%d' % side, 'KG_Stones', ellipsoid((c[0], c[1] - .55, c[2]), (2.05, .75, 1.65), 16, 9),
              C.torso_skin, lambda p, i, c=c: SHOHAM[int(((p[2] - c[2]) + 2) * 1.6) % 2])
    return settings


def choshen(P, settings):
    cx, cz = CHOSHEN_C
    h = CHOSHEN_SIDE / 2
    back = min(surface_y(x, z, OFF_MEIL, False)[0] for x in (-h, -h / 2, 0, h / 2, h)
               for z in (cz - h, cz, cz + h)) - .45
    th = 1.1
    yc = back - th / 2
    P.add('Choshen', 'KG_Ephod', box((cx, yc, cz), (h, th / 2, h), .35), C.torso_skin,
          lambda p, i: ephod_colour(p[0] * 4, p[2] * 4))
    front = yc - th / 2
    frame = [(-h, front, cz - h), (h, front, cz - h), (h, front, cz + h), (-h, front, cz + h), (-h, front, cz - h)]
    for k in range(4):
        a, b = frame[k], frame[k + 1]
        P.add('ChoshenFrame%d' % k, 'KG_Gold', tube([a, b], [(.42, .42), (.42, .42)], 8), C.torso_skin)
    colw, rowh = (CHOSHEN_SIDE - 3.2) / 3, (CHOSHEN_SIDE - 3.2) / 4
    for r in range(4):
        for c in range(3):
            x = cx - h + 1.6 + colw * (c + .5)
            z = cz + h - 1.6 - rowh * (r + .5)
            col = srgb(BOOK_STONES[r][c])
            P.add('ChoshenBezel%d%d' % (r, c), 'KG_Gold', box((x, front - .20, z), (colw / 2 - .25, .28, rowh / 2 - .20), .25),
                  C.torso_skin)
            P.add('ChoshenStone%d%d' % (r, c), 'KG_Stones',
                  box((x, front - .62, z), (colw / 2 - .75, .42, rowh / 2 - .68), .35), C.torso_skin,
                  lambda p, i, col=col: col)
    for side in (-1, 1):                     # gold chains from the upper rings to the shoulders
        a = (side * (h - .6), front - .3, cz + h - .4)
        b = settings[side]
        pts = []
        for k in range(12):
            u = k / 11
            p = lerp3(a, (b[0], b[1] - .2, b[2] - 1.9), u)
            sy, _ = surface_y(p[0], p[2], OFF_MEIL + .9, False)
            pts.append((p[0], min(p[1], sy), p[2] - 1.2 * math.sin(math.pi * u)))
        P.add('ChoshenChain%d' % side, 'KG_Gold', tube(pts, [(.36, .36)] * len(pts), 6), C.torso_skin)
        P.add('ChoshenRingTop%d' % side, 'KG_Gold', ellipsoid(a, (.7, .35, .7), 10, 6), C.torso_skin)
        lo = (side * (h - .6), front - .3, cz - h + .4)
        to = (side * (h + 3.6), None, BELT[1] + .8)
        ty, _ = surface_y(to[0], to[2], OFF_BELT + .6, False)
        P.add('ChoshenCord%d' % side, 'KG_Wool', tube([lo, lerp3(lo, (to[0], ty, to[2]), .5), (to[0], ty, to[2])],
                                                      [(.30, .30)] * 3, 6), C.torso_skin,
              lambda p, i: COL['techelet'])
        P.add('ChoshenRingLow%d' % side, 'KG_Gold', ellipsoid(lo, (.7, .35, .7), 10, 6), C.torso_skin)


def sleeves(P):
    """Ketonet sleeves to the wrist (Rambam 8:15), dense enough for the checker."""
    g, sh = VARIANT['girth'], VARIANT['shoulder']
    folds = fold_field(VARIANT['fold_seed'] + 2, .32, ((5, 1.0), (9, .55), (13, .35)))
    prof = [(0.0, 4.8 * g, 4.6 * g), (5.0, 7.15 * g * sh, 6.85 * g), (11.0, 7.35 * g * sh, 7.05 * g),
            (18.0, 6.65 * g, 6.35 * g), (26.0, 6.05 * g, 5.80 * g), (32.0, 5.75 * g, 5.55 * g),
            (40.0, 5.20 * g, 5.00 * g), (47.0, 4.65 * g, 4.45 * g), (53.0, 4.35 * g, 4.15 * g)]

    def at(t):
        for (t0, a0, b0), (t1, a1, b1) in zip(prof, prof[1:]):
            if t <= t1:
                u = (t - t0) / (t1 - t0)
                return a0 + (a1 - a0) * u, b0 + (b1 - b0) * u
        return prof[-1][1], prof[-1][2]
    ts = [i * 1.0 for i in range(53)] + [53.0]
    seg = 40
    for s in (-1, 1):
        tag = 'R' if s < 0 else 'L'
        pts = [C.arm_point(s, t) for t in ts]
        radii = [at(t) for t in ts]
        v, f = tube(pts, radii, seg, radial=lambda th, i, k=s: (
            folds(th + k * .8, 140 - ts[min(i, len(ts) - 1)] * 1.2, .70 + .60 * ts[min(i, len(ts) - 1)] / 53)))
        cols = []
        for k, p in enumerate(v):
            if k < len(ts) * seg:
                i, j = divmod(k, seg)
                u = int(math.floor(ts[i] / CHECK_CM)); w = int(math.floor(j * math.tau / seg * 5.6 / CHECK_CM))
                cols.append(COL['linenA'] if (u + w) % 2 == 0 else COL['linenB'])
            else:
                cols.append(COL['linenA'])
        P.add('Sleeve' + tag, 'KG_Linen', (v, f), C.sleeve_skin, cols)
        P.add('Cuff' + tag, 'KG_Linen', tube([C.arm_point(s, 52.1), C.arm_point(s, 54.4)],
                                             [(4.65 * g, 4.45 * g)] * 2, 24), C.sleeve_skin)


def legs(P):
    """Bare feet (the kohanim serve barefoot); a dense shin stump for the clearance measurement."""
    g = VARIANT['girth']
    add_ = P.adder(drop=('Shin',))
    for s in (-1, 1):
        C.leg_parts(add_, VARIANT, s)
        tag = 'R' if s < 0 else 'L'
        ankle_z, top = 3.65, 24.0
        prof = [(ankle_z - .9, 3.60 * g, 3.95 * g), (11.0, 4.25 * g, 4.55 * g),
                (top * .55, 5.20 * g, 5.55 * g), (top, 5.70 * g, 6.00 * g)]
        rings = []
        z = prof[0][0]
        while z < top:
            for (z0, a0, b0), (z1, a1, b1) in zip(prof, prof[1:]):
                if z <= z1:
                    u = (z - z0) / (z1 - z0)
                    rings.append((z, a0 + (a1 - a0) * u, b0 + (b1 - b0) * u, s * 8, .4))
                    break
            z += 1.5
        rings.append((top, prof[-1][1], prof[-1][2], s * 8, .4))
        P.add('Shin' + tag, 'KG_Skin', loft(rings, 20), C.leg_skin)


def head_probe(parts):
    """Radius of the head surface in the horizontal direction phi (0 = straight ahead) at height z."""
    pts = []
    for p in parts:
        if p['name'] in ('Head',) or p['name'].startswith(('Brow', 'Ear', 'Sideburn', 'Lid')):
            pts += p['vertices']
    cy = HEAD_C[1]

    def radius(phi, z, win=1.0, ang=math.radians(7)):
        d = (math.sin(phi), -math.cos(phi))
        best = 0.0
        for x, y, zz in pts:
            if abs(zz - z) > win:
                continue
            rr = math.hypot(x, y - cy)
            if rr < 1e-6:
                continue
            a = math.atan2(x, -(y - cy))
            if abs((a - phi + math.pi) % math.tau - math.pi) > ang:
                continue
            best = max(best, rr)
        return best
    return radius, cy


def mitznefet_and_tzitz(P):
    radius, cy = head_probe(P.parts)
    # tzitz: from ear to ear (Rambam 9:1), two fingerbreadths high, on the forehead
    z0 = HEAD_C[2] + 5.0
    brows = [p for p in P.parts if p['name'].startswith('Brow')]
    brow_top = max(v[2] for p in brows for v in p['vertices'])
    z0 = max(z0, brow_top + .7)
    z1 = z0 + TZITZ_H
    grid = []
    cols = 29
    for r in range(4):
        z = z0 + (z1 - z0) * r / 3
        row = []
        for c in range(cols):
            phi = math.radians(-84 + 168 * c / (cols - 1))
            rr = max(radius(phi, z), 4.0) + .55
            row.append((rr * math.sin(phi), cy - rr * math.cos(phi), z))
        grid.append(row)
    P.add('Tzitz', 'KG_Gold', cloth_panel(grid, .14), C.head_skin)
    # techelet cords from the tzitz ends to the nape
    zc = (z0 + z1) / 2
    for side in (-1, 1):
        pts = []
        for k in range(9):
            phi = side * math.radians(84 + 96 * k / 8)
            rr = max(radius(phi, zc - 1.0 * k / 8), 4.0) + .75
            pts.append((rr * math.sin(phi), cy - rr * math.cos(phi), zc - 1.0 * k / 8))
        P.add('TzitzCord%d' % side, 'KG_Wool', tube(pts, [(.30, .30)] * len(pts), 6), C.head_skin,
              lambda p, i: COL['techelet'])
    # mitznefet: a wound linen turban, bulbous (book fig. 2), its front edge just above the tzitz
    front_z, back_z = z1 + .5, HEAD_C[2] + 2.4
    base_z = (front_z + back_z) / 2
    tilt = (front_z - back_z) / 2
    fr = max(radius(0.0, front_z), 4.0) + 1.1
    bk = max(radius(math.pi, back_z), 4.0) + 1.3
    sd = max(radius(math.pi / 2, base_z), radius(-math.pi / 2, base_z), 4.0) + 1.2
    ry0 = (fr + bk) / 2
    cy0 = cy + (bk - fr) / 2
    table = [(0.0, sd, ry0, cy0, 1.0), (1.6, sd + 2.6, ry0 + 2.6, cy0, .92), (4.0, 12.3, 13.2, cy0 - .2, .75),
             (8.0, 13.2, 14.0, cy0 - .3, .50), (12.0, 12.8, 13.5, cy0 - .3, .28), (15.0, 10.8, 11.4, cy0 - .2, .12),
             (17.2, 7.2, 7.6, cy0, .03), (18.4, 3.0, 3.2, cy0, 0.0)]
    hs = [i * .55 for i in range(int(18.4 / .55) + 1)] + [18.4]

    def interp(hh):
        for a, b in zip(table, table[1:]):
            if hh <= b[0]:
                u = (hh - a[0]) / (b[0] - a[0])
                return tuple(a[k] + (b[k] - a[k]) * u for k in range(1, 5))
        return table[-1][1:]
    rings, tilts = [], []
    for hh in hs:
        rx, ry, ccy, tk = interp(hh)
        rings.append((base_z + hh, rx, ry, 0.0, ccy))
        tilts.append(tk)

    def wraps(t, z, level):
        hh = hs[min(level, len(hs) - 1)]
        if hh < 1.2 or hh > 16.5:
            return 0.0
        return .60 * abs(math.sin(math.pi * (hh + t * .9) / 2.5)) - .3

    v, f = loft(rings, 56, radial=wraps, zshift=lambda t, l: tilt * tilts[min(l, len(tilts) - 1)] * -math.sin(t))
    P.add('Mitznefet', 'KG_Linen', (v, f), C.head_skin,
          lambda p, i: lerp3(COL['turban'], COL['linenB'], .35 * abs(math.sin(p[2] * 2.4 + i * .01))))
    # the cord up the front of the mitznefet (book fig. 2)
    pts = []
    for k in range(10):
        hh = 1.2 + 15.5 * k / 9
        rx, ry, ccy, tk = interp(hh)
        z = base_z + hh + tilt * tk
        pts.append((0.0, ccy - ry - .9, z))
    pts.insert(0, (0.0, cy - (max(radius(0.0, z1), 4.0) + .75), z1))
    P.add('MitznefetCord', 'KG_Wool', tube(pts, [(.38, .38)] * len(pts), 6), C.head_skin,
          lambda p, i: COL['techelet'])


def assembly():
    P = Parts()
    ketonet(P)
    meil_vv = meil(P)
    bells_and_pomegranates(P, meil_vv)
    ephod(P)
    belt_and_knot(P)
    settings = straps_and_shoham(P)
    choshen(P, settings)
    sleeves(P)
    for s in (-1, 1):
        C.arm_parts(P.adder(drop=('Sleeve', 'Cuff')), VARIANT, s)
    legs(P)
    C.face_parts(P.adder(), VARIANT)
    mitznefet_and_tzitz(P)
    return P.parts


# ============================================================================= export
def export_glb(path, parts, bones, index):
    asset = C.GLB('Original Kohen Gadol V1 Python author (Scripts/create_kohen_gadol_v1.py)')
    doc = asset.doc
    for i, b in enumerate(bones):
        node = {'name': b['name'], 'translation': C.gltf_vec(b['local_translation_cm'])}
        children = [j for j, k in enumerate(bones) if k['parent_index'] == i]
        if children:
            node['children'] = children
        doc['nodes'].append(node)
    matrices = []
    for b in bones:
        x, y, z = C.gltf_vec(b['position_cm'])
        matrices.append([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1])
    doc['skins'] = [{'name': 'OriginalPilgrimHumanoid', 'joints': list(range(len(bones))), 'skeleton': 0,
                     'inverseBindMatrices': asset.accessor(matrices, 'MAT4')}]
    primitives = []
    for mat in SLOTS:
        members = [p for p in parts if p['material'] == mat]
        if not members:
            continue
        rough, metal, _ = SLOTS[mat]
        mi = len(doc['materials'])
        doc['materials'].append({'name': mat, 'pbrMetallicRoughness': {
            'baseColorFactor': [1., 1., 1., 1.], 'metallicFactor': metal, 'roughnessFactor': rough}})
        positions, norms, joints, weights, vcol, indices = [], [], [], [], [], []
        for p in members:
            offset = len(positions)
            positions.extend(C.gltf_vec(a) for a in p['vertices'])
            norms.extend([n[0], n[2], -n[1]] for n in C.normals(p))
            for point in p['vertices']:
                inf = influence(p, point, index)
                joints.append([j for j, _ in inf])
                weights.append([w for _, w in inf])
            vcol.extend(list(c) + [1.0] for c in p['colours'])
            indices.extend(offset + i for face in p['faces'] for i in face)
        attrs = {'POSITION': asset.accessor(positions, 'VEC3', target=34962, bounds_=True),
                 'NORMAL': asset.accessor(norms, 'VEC3', target=34962),
                 'COLOR_0': asset.accessor(vcol, 'VEC4', target=34962),
                 'JOINTS_0': asset.accessor(joints, 'VEC4', 5123, target=34962),
                 'WEIGHTS_0': asset.accessor(weights, 'VEC4', target=34962)}
        primitives.append({'attributes': attrs, 'indices': asset.accessor(indices, 'SCALAR', 5125, 34963),
                           'material': mi, 'mode': 4})
    doc['meshes'] = [{'name': MESH_ID, 'primitives': primitives}]
    doc['nodes'].append({'name': MESH_ID + '_Mesh', 'mesh': 0, 'skin': 0})
    doc['scenes'] = [{'name': 'KohenGadolV1', 'nodes': [0, len(bones)]}]
    doc['extras'] = {'variant': VARIANT['id'],
                     'provenance': 'Original mesh authored in this project (Scripts/create_kohen_gadol_v1.py).',
                     'coordinates': 'Author centimetres XYZ, front -Y, Z up; glTF metres X,Z,-Y.',
                     'vertexColour': 'COLOR_0 is LINEAR RGB; it carries every garment colour and pattern.'}
    asset.save(path)
    return doc


# ============================================================================= preview render
def render_vc(parts_xyz, path, yaw, width=460, height=800, top=196.0, scale=3.72, look=None):
    """Z-buffer render with per-vertex colour; three lights. Shape and colour read, not a shader."""
    W, H = width, height
    bg = (26, 28, 31)
    pix = bytearray(bg * (W * H))
    depth = [-1e9] * (W * H)
    key = normalize((-.45, -.78, .62)); fill = normalize((.72, -.35, .18)); rim = normalize((.15, .85, .35))
    cy, sy = math.cos(yaw), math.sin(yaw)
    cx0, cz0 = (look or (0.0, 0.0))
    for p, verts in parts_xyz:
        v = verts
        ns = C.normals(dict(p, vertices=v))
        proj, shade = [], []
        for (x, y, z), n in zip(v, ns):
            xx = (x - cx0) * cy - y * sy
            yy = (x - cx0) * sy + y * cy
            proj.append((W / 2 + xx * scale, (top - z) * scale, -yy))
            nx = n[0] * cy - n[1] * sy
            ny = n[0] * sy + n[1] * cy
            nn = (nx, ny, n[2])
            shade.append(.24 + .82 * max(0, dot(nn, key)) + .26 * max(0, dot(nn, fill)) + .30 * max(0, dot(nn, rim)) ** 3)
        metal = p['material'] in ('KG_Gold',)
        cols = p['colours']
        for tri in p['faces']:
            a, b, c = [proj[i] for i in tri]
            area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if abs(area) < 1e-9:
                continue
            x0 = max(0, int(min(a[0], b[0], c[0]))); x1 = min(W - 1, int(max(a[0], b[0], c[0])) + 1)
            y0 = max(0, int(min(a[1], b[1], c[1]))); y1 = min(H - 1, int(max(a[1], b[1], c[1])) + 1)
            if x1 < x0 or y1 < y0:
                continue
            sh = [shade[i] for i in tri]
            cc = [cols[i] for i in tri]
            for yv in range(y0, y1 + 1):
                base = yv * W
                for xv in range(x0, x1 + 1):
                    u = ((b[0] - xv) * (c[1] - yv) - (b[1] - yv) * (c[0] - xv)) / area
                    if u < 0:
                        continue
                    w2 = ((c[0] - xv) * (a[1] - yv) - (c[1] - yv) * (a[0] - xv)) / area
                    if w2 < 0:
                        continue
                    w3 = 1 - u - w2
                    if w3 < 0:
                        continue
                    d = u * a[2] + w2 * b[2] + w3 * c[2]
                    idx = base + xv
                    if d <= depth[idx]:
                        continue
                    depth[idx] = d
                    s = u * sh[0] + w2 * sh[1] + w3 * sh[2]
                    if metal:
                        s = .35 + 1.1 * s ** 2
                    o = idx * 3
                    for k in range(3):
                        col = u * cc[0][k] + w2 * cc[1][k] + w3 * cc[2][k]
                        pix[o + k] = int(255 * min(1.0, col * s) ** (1 / 2.2))
    C.write_png(path, W, H, pix)


# ============================================================================= checks
def checks(parts, bones, index):
    tris = sum(len(p['faces']) for p in parts)
    by = {}
    for p in parts:
        by.setdefault(p['material'], 0)
        by[p['material']] += len(p['faces'])
    worst_inf = max(len([w for _, w in influence(p, v, index) if w > 0]) for p in parts for v in p['vertices'][::7])
    ket = [p for p in parts if p['name'] == 'Ketonet'][0]
    hem_z = [v[2] for v in ket['vertices'][:KETONET_SEGMENTS]]
    meil_p = [p for p in parts if p['name'] == 'Meil'][0]
    mhem = [v[2] for v in meil_p['vertices'][:MEIL_SEGMENTS]]
    return {'triangles': tris, 'trianglesByMaterial': by, 'budget': TRIANGLE_BUDGET,
            'maxInfluencesSampled': worst_inf,
            'ketonetHemZcm': [round(min(hem_z), 2), round(max(hem_z), 2)],
            'meilHemZcm': [round(min(mhem), 2), round(max(mhem), 2)],
            'bells': 72, 'pomegranates': 72,
            'choshenStones': 12, 'shohamStones': 2}


def build(fast=False):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'meshes').mkdir(exist_ok=True)
    bones = C.skeleton()
    rig = C.assert_rig_matches_v2(bones)
    index = {b['name']: i for i, b in enumerate(bones)}
    started = time.time()
    parts = assembly()
    info = checks(parts, bones, index)
    assert info['triangles'] <= TRIANGLE_BUDGET, info['triangles']
    path = OUT / 'meshes' / (MESH_ID + '.glb')
    export_glb(path, parts, bones, index)
    manifest = {'generatedUtc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'generator': 'Scripts/create_kohen_gadol_v1.py',
                'generatorSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'mesh': MESH_ID, 'file': 'meshes/' + MESH_ID + '.glb',
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'skeleton': 'C.skeleton() unchanged: import onto the EXISTING V3_Pilgrim_Man_Standard Skeleton',
                'rigCompatibility': rig, 'jointNames': sorted(b['name'] for b in bones),
                'slots': {k: {'roughness': v[0], 'metallic': v[1], 'specular': v[2]} for k, v in SLOTS.items()},
                'checks': info,
                'skinField': {'bandHemCm': BAND_HEM, 'bandThighCm': BAND_THIGH, 'followTopZ': F_TOP,
                              'followFullZ': F_FULL, 'kneeTopZ': KNEE_TOP, 'kneeBottomZ': KNEE_BOT, 'followMax': F_MAX},
                'seconds': round(time.time() - started, 1)}
    (OUT / 'kohen-gadol-v1-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest, parts


def previews(parts, times=None):
    import numpy as np
    import measure_kohen_garment_clearance as M
    from measure_pilgrim_walk import Rig
    bones = C.skeleton()
    index = {b['name']: i for i, b in enumerate(bones)}
    arrays = [(p,) + M.skin_arrays(p, influence, index) for p in parts]
    shots = []
    (OUT / 'previews').mkdir(exist_ok=True)
    plan = times or [('rest', None, 0.0, [('front', 0.0), ('three-quarter', .62)]),
                     ('walk', 'walk', None, [('side', math.pi / 2)]),
                     ('tend', 'tend', 7.6, [('three-quarter', .62), ('side', math.pi / 2)])]
    clips = {n: (g, c) for n, g, c, _ in M.CLIPS}
    for label, clip, t, views in plan:
        if clip is None:
            posed = [(p, p['vertices']) for p in parts]
        else:
            rig = Rig(*clips[clip])
            if t is None:
                continue
            A, b = M.joint_affines(rig, rig.pose(t), bones)
            posed = [(p, [tuple(r) for r in M.skin(v, J, W, A, b)]) for p, v, J, W in arrays]
        for name, yaw in views:
            out = OUT / 'previews' / ('%s-t%05.2f-%s.png' % (label, t or 0.0, name))
            render_vc(posed, out, yaw)
            shots.append(str(out.relative_to(OUT)).replace('\\', '/'))
    return shots


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--fast', action='store_true')
    ap.add_argument('--preview', default='', help='comma list clip:time:view, e.g. walk:0.52:side')
    a = ap.parse_args()
    if a.build:
        m, parts = build(a.fast)
        print(json.dumps(m['checks'], indent=1))
        if not a.fast:
            print(previews(parts))
    elif a.preview:
        parts = assembly()
        views = {'front': 0.0, 'side': math.pi / 2, 'three-quarter': .62, 'back': math.pi, 'rear-quarter': math.pi - .62}
        plan = []
        for item in a.preview.split(','):
            clip, t, view = item.split(':')
            plan.append((clip, None if clip == 'rest' else clip, float(t), [(view, views[view])]))
        print(previews(parts, plan))
    else:
        ap.print_help()

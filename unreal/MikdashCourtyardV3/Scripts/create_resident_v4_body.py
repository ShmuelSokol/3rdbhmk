"""ResidentV4 body and dress. Imported by create_resident_v4.py; see its docstring for sources."""
import math

import create_pilgrim_v3 as C
import create_kohen_gadol_v1 as K
from create_pilgrim_v3 import add, sub, scale, dot, cross, length, normalize, clamp, smooth, gauss, HEAD_C
import create_resident_v4 as R
import create_resident_v4_face as FA

TAU = math.tau
TUNIC_SEGMENTS = 112
MANTLE_OFFSET = 1.25      # cm outward from the TUNIC surface (incl. its folds): the mantle cannot be pierced
MANTLE_OPEN = math.radians(24)


# ============================================================================= skinning
def lower_skin(p):
    """The Kohen Gadol weight field (pelvis -> same-side thigh -> calf), with ONE change: behind the
    knee the thigh -> calf handover sits higher (57 -> 42 cm instead of 52 -> 30), blended in by the
    rest y of the point. On a mid-calf hem the back-of-knee cloth otherwise follows the thigh while
    the flexing swing calf comes back through it (measured 0.07-0.11 cm on Man_Elder at t 0.92-0.98 s;
    more ease made it worse, because ease only moves cloth along the thigh's path)."""
    x, y, z = p
    back = smooth(clamp((y + 2.0) / 8.0))                 # 0 in front and at the sides, 1 behind
    knee_top = K.KNEE_TOP + 5.0 * back                  # +10 left the back-of-THIGH cloth on the calf (Man_Heavy 0.02 cm at z 56)
    knee_bot = K.KNEE_BOT + 12.0 * back
    f = K.F_MAX * smooth(clamp((K.F_TOP - z) / (K.F_TOP - K.F_FULL)))
    k = smooth(clamp((knee_top - z) / (knee_top - knee_bot)))
    band = K.BAND_HEM + (K.BAND_THIGH - K.BAND_HEM) * smooth(clamp((z - 25.0) / (K.F_FULL - 25.0)))
    s = smooth(clamp((x + band) / (2.0 * band)))
    ft = 1.0 - clamp((z - 5.0) / 16.0)
    return {'pelvis': 1.0 - f,
            'thigh_r': f * (1 - s) * (1 - k), 'calf_r': f * (1 - s) * k * (1 - ft), 'foot_r': f * (1 - s) * k * ft,
            'thigh_l': f * s * (1 - k), 'calf_l': f * s * k * (1 - ft), 'foot_l': f * s * k * ft}


def garment_skin(p):
    return C.torso_skin(p) if p[2] >= K.F_TOP else lower_skin(p)


def leg_skin(p):
    """Anatomical leg: foot below the ankle, calf, calf -> thigh across the knee (z 44..54)."""
    x, y, z = p
    s = 'r' if x < 0 else 'l'
    if z < 21.0:
        return C.blend('foot_' + s, 'calf_' + s, (z - 5) / 16)
    if z < 44.0:
        return {'calf_' + s: 1.0}
    if z < 90.0:
        return C.blend('calf_' + s, 'thigh_' + s, (z - 44.0) / 10.0)
    return C.blend('thigh_' + s, 'pelvis', (z - 90.0) / 6.0)


# ============================================================================= tunic
class Tunic:
    """Loft tunic whose surface can be queried at any (t, z): the mantle is built ON it."""

    def __init__(self, variant):
        self.v = variant
        self.hem = variant['tunic_hem']
        self.g, self.sh = variant['girth'], variant['shoulder']
        self.folds = C.fold_field(variant['fold_seed'], 1.30)
        zs, z = [], self.hem
        while z < 30.0:
            zs.append(round(z, 3)); z += 1.2
        while z < 99.0:
            zs.append(round(z, 3)); z += 3.0
        for az, _, _ in C.GARMENT_ANCHORS:
            if az > zs[-1] + 1.0:
                zs.append(az)
        self.zs = zs

    def section(self, z):
        rx, ry = C.anchor_at(z)
        return rx * self.g * (self.sh if z > 130 else 1.0), ry * self.g

    def radial(self, t, z):
        f = .62 * self.folds(t, z, C.tunic_amplitude(z, self.hem)) * K.fold_damp(z)
        if z < 74.0:
            f += 2.4 * max(0.0, math.cos(2 * t)) * smooth((74.0 - z) / 42.0)
        if z < 44.0:
            centre = sum(math.exp(-(((t - c + math.pi) % TAU - math.pi) / .42) ** 2) for c in (.5 * math.pi, 1.5 * math.pi))
            f += 3.0 * centre * smooth((44.0 - z) / 26.0)
        if z < 58.0:
            # ease over the front of each knee: the swing knee flexes forward into the cloth (measured 0.40 cm)
            knee = sum(math.exp(-(((t - c + math.pi) % TAU - math.pi) / .34) ** 2) for c in K.LEG_FRONT_T)
            f += 1.6 * knee * gauss(z, 44.0, 9.0)
            # and BEHIND each knee: the thigh/calf blend on the back panel collapses onto the calf
            # bulge as the swing knee flexes (measured 0.40 cm at t 1.03 s, back of the right calf)
            back = sum(math.exp(-(((t - c + math.pi) % TAU - math.pi) / .38) ** 2) for c in (.5 * math.pi - .35, .5 * math.pi + .35))
            f += 2.0 * back * gauss(z, 42.0, 8.0)
        # blousing over the belt (authored): the tunic pulled up and let fall over the girdle
        f += 1.1 * gauss(z, 111.5, 2.6) * (.7 + .3 * math.cos(3 * t))
        return f

    @staticmethod
    def exponent(z, level=0):
        return 1.0 - .17 * smooth((z - 92) / 14) * smooth((140 - z) / 16)

    def point(self, t, z, offset=0.0):
        rx, ry = self.section(z)
        e = self.exponent(z)
        f = self.radial(t, z) + offset
        ct, st = math.cos(t), math.sin(t)
        ct = math.copysign(abs(ct) ** e, ct)
        st = math.copysign(abs(st) ** e, st)
        return ((rx + f) * ct, (ry + f) * st, z)

    def hem_break(self, t, level):
        if level > 2:
            return 0.0
        return (1.0, .85, .35)[level] * (1.6 * max(0.0, -math.sin(t)) - 1.5 * max(0.0, math.sin(t)))

    def mesh(self):
        rings = [(z,) + self.section(z) + (0.0, 0.0) for z in self.zs]
        return FA.loft_uv(rings, TUNIC_SEGMENTS, radial=lambda t, z, l: self.radial(t, z),
                          exponent=self.exponent, zshift=self.hem_break, cap=False)

    def colour(self, vid_palette, clavi, t, z, garment):
        """Tunic colour. Clavi: two bands over the shoulders, front and back (Yadin, R)."""
        base = (1.0, 1.0, 1.0) if garment else vid_palette['Linen']
        x = math.cos(t)
        band = smooth((1.1 - abs(abs(x * 18.0) - 6.6)) / .5) if z > self.hem + 3 else 0.0
        c = R.lerp3(base, (.55, .55, .55) if garment else clavi, band * .9)
        m = 1 + .05 * R.vnoise(t * 9, z * .12, self.v['fold_seed'], 1.0)
        if z < self.hem + 14:                                        # road dust at the hem
            c = R.lerp3(c, R.mul3(c, (.80, .74, .64)), .5 * smooth((self.hem + 14 - z) / 14))
        return tuple(k * m for k in c)


# ============================================================================= mantle (on the tunic)
def mantle(variant, tun):
    """A rectangle wrapped round the body under the arms, open at the front. Built as an OFFSET of
    the tunic surface on the tunic's own ring heights, each vertex anchored to the tunic point it is
    offset from, so both layers carry identical weights (the Kohen Gadol me'il rule)."""
    hem = variant['mantle_hem']
    zs = [hem] + [z for z in tun.zs if hem + .5 < z < 143.0] + [143.0, 146.0]
    cols = 72
    ripple = C.fold_field(variant['fold_seed'] + 1, .95, ((5, 1.0), (8, .6), (12, .35)))
    belt_mx = {}
    grid, anch = [], []
    for z in zs:
        row, arow = [], []
        for c in range(cols):
            u = c / (cols - 1)
            t = 1.5 * math.pi + MANTLE_OPEN + u * (TAU - 2 * MANTLE_OPEN)     # 1.5 pi = front (-Y)
            out = MANTLE_OFFSET + max(0.0, .9 * ripple(t * 1.9, z, .5 + .9 * smooth((140 - z) / 80)))
            if 97.0 < z < 114.0:
                # the belt (tunic max fold + up to 2.6 cm) is worn UNDER the mantle: rise over it
                if z not in belt_mx:
                    belt_mx[z] = max(tun.radial(k * TAU / 96, z) for k in range(96))
                need = belt_mx[z] - tun.radial(t, z) + 2.6 + .8
                w = smooth((z - 97.0) / 2.5) * smooth((114.0 - z) / 2.5)
                out = max(out, out * (1 - w) + need * w)
            row.append(tun.point(t, z, out))
            arow.append(tun.point(t, z, 0.0))
        grid.append(row)
        anch.append(arow)
    v, f, uv, _ = FA.panel_uv(grid, .36)
    flat = [a for row in anch for a in row]
    return v, f, uv, flat + flat, grid, zs, cols


def mantle_colour(variant, grid, zs, cols):
    """Neutral luminance (the population's garment instance supplies the colour); darker notched
    'gamma' corner bands and a hem band (Cave of Letters textiles, R)."""
    out = []
    for r, z in enumerate(zs):
        for c in range(cols):
            u = c / (cols - 1)
            k = .93 + .06 * R.vnoise(u * 30, z * .1, variant['fold_seed'] + 2, 1.0)
            hemb = smooth((zs[0] + 5.5 - z) / 1.0) * smooth((z - zs[0] - 2.0) / 1.0)
            edge = min(u, 1 - u) * (TAU - 2 * MANTLE_OPEN) * 20.0            # cm from the front edge
            gam = (smooth((9.0 - edge) / 1.0) * smooth((edge - 6.0) / 1.0) * smooth((zs[0] + 22 - z) / 1.0)
                   + smooth((zs[0] + 22 - z) / 1.0) * smooth((z - zs[0] - 19.0) / 1.0) * smooth((9.0 - edge) / 1.0))
            k *= 1 - .45 * clamp(hemb + gam)
            out.append((k, k, k))
    return out + out


def tzitzit(variant, grid, anchors_grid):
    """Four tassels at the four corners of the wrapped rectangle (Numbers 15:38): all four corners of
    a rectangle wrapped round the back fall at the two front edges, top and bottom. Seven undyed
    strings and one of techelet each (the count of strings drawn is authored)."""
    tassels = []
    rows, cols = len(grid), len(grid[0])
    for r, c in ((0, 0), (0, cols - 1), (rows - 1, 0), (rows - 1, cols - 1)):
        p = grid[r][c]
        a = anchors_grid[r][c]
        out = normalize((p[0], p[1], 0.0))
        top = add(p, scale(out, .5))
        length_cm = 13.0 if r == 0 else 11.0
        for k in range(8):
            ang = k * TAU / 8
            dx, dy = .35 * math.cos(ang), .35 * math.sin(ang)
            pts = [add(top, (dx * s, dy * s + 0.0, -length_cm * s - .8 * s * s)) for s in (0.0, .35, .7, 1.0)]
            pts = [add(q, scale(out, .25 + .15 * s)) for q, s in zip(pts, (0, .35, .7, 1))]
            colour = (.18, .30, .62) if k == 0 else (.80, .78, .72)
            tassels.append((pts, colour, a))
        tassels.append(([add(top, (0, 0, -.2)), add(top, (0, 0, -2.4))], (.80, .78, .72), a))   # the wound knots
    return tassels


# ============================================================================= legs, feet, sandals
def leg_profile(z, g, fem):
    """(half-width x, half-depth y, y-centre offset) of the bare leg at height z. Calf bulge at the
    back, flat shin in front, knee, lower thigh (authored against the 179 cm figure)."""
    k = .93 if fem else 1.0
    table = [(3.0, 3.30, 3.70, .6), (6.0, 3.00, 3.60, .4), (9.5, 2.80, 3.30, .5), (15.0, 3.10, 3.60, .9),
             (24.0, 3.90, 4.50, 1.4), (32.0, 4.60, 5.30, 1.8), (38.0, 4.95, 5.60, 1.8), (43.0, 4.70, 5.10, 1.2),
             (48.0, 4.60, 4.70, .3), (52.0, 5.20, 5.10, -.2), (60.0, 6.10, 6.10, 0.0), (75.0, 7.10, 7.00, 0.0),
             (92.0, 7.80, 7.60, 0.0)]
    for (z0, a0, b0, c0), (z1, a1, b1, c1) in zip(table, table[1:]):
        if z <= z1:
            u = clamp((z - z0) / (z1 - z0))
            return (a0 + (a1 - a0) * u) * g * k, (b0 + (b1 - b0) * u) * g * k, c0 + (c1 - c0) * u
    return table[-1][1] * g * k, table[-1][2] * g * k, 0.0


def leg(variant, s):
    g = variant['girth']
    fem = variant['sex'] == 'f'
    # capped at 58: never higher than any variant needs, and inside the region the clearance tool
    # measures (its signed wall is the tunic below rest z 60); the Youth's knee-length tunic had put
    # his leg top at 70, where both of the tool's tests misread it as 11 cm outside
    top = min(58.0, variant['tunic_hem'] + 26.0)
    ankle_z = 4.7
    zs, z = [], ankle_z - 1.0
    while z < top:
        zs.append(z)
        z += 1.6 if z < 50 else 3.0
    zs.append(top)
    rings = []
    for z in zs:
        a, b, cy = leg_profile(z, g, fem)
        rings.append((z, a, b, s * 8.0, cy))

    def radial(t, z, level):
        # medial calf bulge, flat anterior shin, malleoli, patella (t = -pi/2 is the front, -Y)
        med = math.cos(t) * -s
        f = .45 * max(0.0, med) * gauss(z, 34.0, 6.0)
        f -= .35 * max(0.0, -math.sin(t)) * gauss(z, 26.0, 9.0) * gauss(math.cos(t), 0.0, .35)
        f += .45 * gauss(z, 6.6, 1.1) * (gauss(math.cos(t), 1.0, .3) + gauss(math.cos(t), -1.0, .3))
        f += .55 * gauss(z, 49.0, 2.2) * max(0.0, -math.sin(t)) ** 3
        return f
    v, f, uv, P = FA.loft_uv(rings, 26, radial=radial, cap=False)
    return v, f, uv, P


def foot(variant, s):
    """Foot with a heel, arch, ball and five toes as one sculpted shell (the rig gives ball_* no
    weight, so the forefoot is rigid, as the walk was authored)."""
    g = variant['girth'] * (.92 if variant['sex'] == 'f' else 1.0)
    z0 = 4.7

    def sculpt(p):
        x, y, z = p
        yy = y
        x *= 1 - .20 * gauss(yy, -11.0, 4.5) + .06 * gauss(yy, -6.0, 3.0)
        z *= 1 - .30 * gauss(yy, -10.5, 5.0)
        if z < 0:
            z *= .55
        z -= .6 * gauss(yy, 6.5, 2.0) * (z < 0)
        z += .45 * gauss(yy, -1.0, 3.0) * gauss(x, -s * 2.0, 1.6) * (z < 0)       # arch (medial)
        return x, y, z
    v, f, uv, P = FA.ellipsoid_uv((s * 8, -5.6, z0), (4.60 * g, 13.4, 3.1), 26, 14, sculpt)
    toes = []
    # toe lengths keep every tip at y >= -19.4, inside the V3 foot envelope the Kohen Gadol measurement
    # proved clean; 4.2 cm put the big-toe tip at y -20.7, which pierced the women's low hems in swing
    for i, (dx, ln, r) in enumerate(((-1.9, 3.0, .95), (-.2, 2.7, .80), (1.3, 2.4, .72), (2.6, 2.1, .66), (3.7, 1.7, .60))):
        x = s * 8 - s * dx * g
        y0 = -16.4 + (.9 if i else 0.0) + .45 * i
        toes.append(([(x, y0, z0 - 1.9), (x, y0 - ln * .6, z0 - 2.1), (x, y0 - ln, z0 - 2.35)],
                     [(r, r * .85), (r * .95, r * .8), (r * .75, r * .62)]))
    return (v, f, uv, P), toes


def sandal(variant, s):
    g = variant['girth'] * (.92 if variant['sex'] == 'f' else 1.0)
    sole = FA.loft_uv([(0.0, 4.60 * g, 14.6, s * 8, -5.9), (.6, 5.05 * g, 15.1, s * 8, -5.9),
                       (1.6, 5.05 * g, 15.1, s * 8, -5.9), (2.0, 4.75 * g, 14.6, s * 8, -5.9)], 30)
    straps = []
    cx = s * 8
    for y in (-14.0, -6.0):                                   # two instep thongs
        straps.append([(cx - 4.4, y, 1.8), (cx - 3.1, y, 5.6), (cx, y + .5, 7.0), (cx + 3.1, y, 5.6), (cx + 4.4, y, 1.8)])
    straps.append([(cx - s * 1.6, -17.8, 1.9), (cx - s * 1.2, -13.0, 5.4), (cx, -6.0, 7.2)])   # toe thong
    ring = [(cx + 3.95 * math.cos(a), .9 + 4.35 * math.sin(a), 7.9 + .5 * math.sin(a)) for a in
            [i * TAU / 16 for i in range(17)]]                 # ankle thong round the back of the heel
    straps.append(ring)
    return sole, straps

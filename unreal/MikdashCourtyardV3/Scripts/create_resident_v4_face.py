"""ResidentV4 face and UV-aware primitives. Imported by create_resident_v4.py; see its docstring."""
import math

import create_pilgrim_v3 as C
from create_pilgrim_v3 import add, sub, scale, dot, cross, length, normalize, clamp, smooth, gauss
from create_pilgrim_v3 import HEAD_C, HEAD_RX, HEAD_RY, HEAD_RZ
import create_resident_v4 as R

TAU = math.tau
# refine-only lower-face shape (see face_shape); zero effect on faces without 'refine'
JAW_W, JAW_Z, JAW_S, TAPER, MOUTH_IN, MOUTH_Z = .6, -8.2, 2.1, .28, .20, -3.2
LIP_UP, LIP_LO = 1.4, 1.3
CHEEK_FILL, MUZZLE_BACK = .85, .75
BROW_MIN_W, LIPS_BACK = .30, .90


# ============================================================================= UV-aware primitives
def _period(radius):
    return max(1, round(TAU * max(radius, .05) / R.UV_CM))


def loft_uv(rings, segments, radial=None, exponent=None, cap=True, zshift=None):
    v, f = C.loft(rings, segments, radial, exponent, cap, zshift)
    P = _period(sum(.5 * (r[1] + r[2]) for r in rings) / len(rings))
    uv = []
    for level in range(len(rings)):
        for i in range(segments):
            uv.append((i / segments * P, v[level * segments + i][2] / R.UV_CM))
    while len(uv) < len(v):
        uv.append((0.0, v[len(uv)][2] / R.UV_CM))
    return v, f, uv, P


def tube_uv(points, radii, segments=12, radial=None):
    v, f = C.tube(points, radii, segments, radial)
    rr = [r if isinstance(r, tuple) else (r, r) for r in radii]
    P = _period(sum(.5 * (a + b) for a, b in rr) / len(rr))
    arc = [0.0]
    for a, b in zip(points, points[1:]):
        arc.append(arc[-1] + length(sub(b, a)))
    uv = [(j / segments * P, arc[i] / R.UV_CM) for i in range(len(points)) for j in range(segments)]
    uv += [(0.0, arc[0] / R.UV_CM), (0.0, arc[-1] / R.UV_CM)]
    return v, f, uv, P


def ellipsoid_uv(centre, radii, segments=32, levels=20, sculpt=None):
    v, f = C.ellipsoid(centre, radii, segments, levels, sculpt)
    P = _period(.5 * (radii[0] + radii[1]))
    uv = [(0.0, v[0][2] / R.UV_CM)]
    for j in range(1, levels):
        for i in range(segments):
            uv.append((i / segments * P, v[len(uv)][2] / R.UV_CM))
    uv.append((0.0, v[-1][2] / R.UV_CM))
    return v, f, uv, P


def panel_uv(grid, thickness=.35):
    v, f = C.cloth_panel(grid, thickness)
    rows, cols = len(grid), len(grid[0])
    us = [0.0]
    for c in range(1, cols):
        us.append(us[-1] + length(sub(grid[rows // 2][c], grid[rows // 2][c - 1])))
    vs = [0.0]
    for r in range(1, rows):
        vs.append(vs[-1] + length(sub(grid[r][cols // 2], grid[r - 1][cols // 2])))
    front = [(us[c] / R.UV_CM, vs[r] / R.UV_CM) for r in range(rows) for c in range(cols)]
    return v, f, front + front, None


def orient_open(v, f, outward):
    """Flip an OPEN sheet so its faces point along outward(p)."""
    s = 0.0
    for a, b, c in f[::max(1, len(f) // 400)]:
        n = cross(sub(v[b], v[a]), sub(v[c], v[a]))
        s += dot(n, outward(v[a]))
    return f if s >= 0 else [(a, c, b) for a, b, c in f]


# ============================================================================= head
def head_radii(variant):
    g = variant['girth']
    fem = .95 if variant['face']['female'] else 1.0
    return HEAD_RX * (.96 + .04 * g) * fem, HEAD_RY, HEAD_RZ


def eye_centre_xz(F):
    return 3.3 * F['eye_sp'], 1.1


def nose_geom(F):
    root = 1.7
    tip = -2.1 - .55 * (F['nose_len'] - 1.0) * 2.0
    base = tip - 1.05 * F['nose_len']
    return root, tip, base


def mouth_geom(F):
    mw = 2.35 * (1 + .06 * (F['lip'] - 1)) * (.93 if F['female'] else 1.0)
    zm = -5.4 if F['female'] else -5.6
    return mw, zm


def face_shape(p, F):
    """Sculpt the face INTO the skull surface (local head coords, front -Y). Returns (p, tags)."""
    x, y, z = p
    tags = {}
    if y >= 4.5:
        return p, tags
    front = smooth((1.0 - y) / 4.0)
    wj = smooth((4.5 - y) / 5.0)          # the jaw reaches back to the gonion, below the ear
    soft = F.get('soft', 0.0)
    # refine (Woman_Young 1.0, Youth partial; 0 = unchanged): an oval lower face widest at the cheekbones,
    # a jaw that tapers to a small rounded chin with no shelf under it, fuller cheeks, a finer brow.
    # fr = the female-only part of it (fuller lips, lighter mouth line, the brow ridge nearly gone).
    r = F.get('refine', 0.0)
    fr = r * F['female']
    djaw = 0.0
    ax = abs(x)
    sx = 1.0 if x >= 0 else -1.0
    dy = dx = dz = 0.0
    # brow ridge (men), cheekbones, cheek fullness / hollow
    # the skull sculpt tapers the jaw to ~0.73 at the mouth: an egg. Put back a real lower face -
    # zygomatic width, a jaw with an angle, a squarer chin and a dental arch the lips sit on.
    djaw += sx * (.75 * gauss(z, -2.8, 2.4) + (.45 if F['female'] else 1.10) * gauss(z, -7.2, 2.6)) * smooth(ax / 3.0)
    # the mandible's lower border: a slight ridge, then the surface turns UNDER and back toward the
    # neck, so the jaw catches a shadow line instead of melting into the neck as one slab
    under = smooth((-8.3 - z) / 1.5)
    djaw += sx * (1 - r) * (.30 * gauss(z, -7.9, .6) - 1.7 * under) * smooth((ax - .8) / 2.2)
    # refine: the mandible turns under as a PROPORTIONAL taper, so the jaw line is a rounded U into a small
    # chin; a constant inset (above) squeezes every |x| into the same narrow band and leaves a chin tab.
    # The mandible body is carried wider toward the gonion (dxb, weighted to reach the back of the jaw),
    # and the width at mouth level comes in, so the widest point of the face is the cheekbone.
    dxb = -x * r * TAPER * smooth((-8.0 - z) / 3.0)
    dxb += sx * r * (JAW_W * gauss(z, JAW_Z, JAW_S) - MOUTH_IN * gauss(z, MOUTH_Z, 1.3)) * smooth(ax / 3.0)
    dyj = 1.5 * under * smooth((ax - 1.2) / 1.8) + 2.2 * (1 - .35 * r) * smooth((-10.0 - z) / (1.1 + 1.0 * r)) * smooth((3.0 - ax) / 1.2)
    # soft (young / female): undo most of the skull sculpt's brow ridge and cheek hollow, fuller cheeks
    dy += .75 * soft * gauss(ax, 3.5, 2.3) * gauss(z, 2.8, 1.6)
    dy -= .55 * soft * gauss(ax, 3.6, 1.9) * gauss(z, -5.4, 2.2)
    dy -= .55 * soft * gauss(ax, 3.3, 1.4) * gauss(z, -2.9, 1.3)
    dx += sx * .55 * (1 - .85 * r) * gauss(z, -10.2, 1.3) * smooth(ax / 1.6) * smooth((3.2 - ax) / 1.2)
    dy += (.25 * r + .30 * fr) * gauss(ax, 3.5, 2.3) * gauss(z, 2.8, 1.6)            # finer brow ridge
    dy -= .50 * r * gauss(ax, 3.7, 1.7) * gauss(z, -3.0, 1.7)                        # fuller cheeks
    dy -= CHEEK_FILL * r * gauss(ax, 3.4, 1.4) * gauss(z, -5.4, 1.6)                 # fill the hollow beside the mouth
    dy += MUZZLE_BACK * r * gauss(ax, 0.0, 1.9) * gauss(z, -6.6, 1.8)                # less muzzle: the mouth sits IN the face
    dy += LIPS_BACK * r * gauss(ax, 0.0, 2.0) * gauss(z, -5.5, 1.1)                  # the lips set back level with the cheeks
    dy -= .18 * fr * gauss(ax, 0.0, 1.3) * gauss(z, -9.1, .9)                        # a small rounded chin
    dy -= .50 * gauss(ax, 0.0, 2.6) * gauss(z, -5.6, 2.1)
    dy -= .50 * F['brow'] * gauss(ax, 3.4, 2.0) * gauss(z, 3.2, .95)
    dy -= (.30 + .35 * F['cheek']) * gauss(ax, 4.6, 1.5) * gauss(z, -1.7, 1.5)
    dx += sx * .55 * F['cheek'] * (1 - .6 * r) * gauss(ax, 5.2, 1.6) * gauss(z, -4.0, 2.2)
    dy += .55 * F['sunken'] * gauss(ax, 3.9, 1.3) * gauss(z, -4.6, 1.6)
    # nose: ridge profile, width profile, alae, hook
    root, tip, base = nose_geom(F)
    h = 0.0
    if base - .5 < z < root + 1.3:
        if z >= root:
            h = .55 * smooth((root + 1.3 - z) / 1.3)
        elif z >= tip:
            u = (root - z) / (root - tip)
            h = .60 + (2.85 * F['nose_len'] - .60) * u ** 1.15 + F['hook'] * .38 * math.sin(math.pi * u)
        else:
            u = (tip - z) / (tip - base)
            h = 2.85 * F['nose_len'] * (1 - u ** 1.7) + .50 * u
            if z < base:
                h = .45 * smooth((z - (base - .5)) / .5)
        if tip < z < root:
            wz = .70 + (1.25 * F['nose_w'] - .70) * ((root - z) / (root - tip)) ** 1.4
        else:
            wz = 1.25 * F['nose_w'] + .35 * F['nose_w'] * smooth((tip - z) / .8)
        dy -= h * (1 - .30 * soft) * math.exp(-(ax / wz) ** 2.2)      # soft faces: a less projecting nose
    al = gauss(ax, 1.45 * F['nose_w'], .52) * gauss(z, base + .38, .45)
    dy -= .62 * F['nose_w'] * (1 - .20 * soft) * al
    tags['nostril'] = gauss(ax, .75 * F['nose_w'], .35) * gauss(z, base - .05, .22)
    # mouth: upper lip with a cupid's bow, fuller lower lip, a real mouth-line groove
    mw, zm = mouth_geom(F)
    lx = smooth((mw - ax) / .45)
    zc = zm + .06 * (ax / mw) ** 2            # neutral, relaxed corners
    bow = .18 * gauss(ax, .55, .28) - .12 * gauss(ax, 0.0, .20)
    up = .34 * F['lip'] * (1 + LIP_UP * fr) * lx * gauss(z, zc + .30 + bow, .19 + .05 * fr)
    up += .10 * lx * gauss(z, zc + .52 + bow, .06)                          # vermilion border
    lo = .48 * F['lip'] * (1 - .25 * soft + LIP_LO * fr) * lx * gauss(z, zc - .46 * F['lip'], .27 + .07 * fr)
    dy += .12 * gauss(ax, mw + .25, .22) * gauss(z, zc, .30)                # relaxed corners (modiolus)
    groove = .34 * (1 - .40 * r) * lx * math.exp(-((z - zc) / .075) ** 2)
    dy += -up - lo + groove
    dy -= .10 * gauss(ax, .42, .16) * gauss(z, zc + 1.05, .45)          # philtral columns
    dy += .06 * gauss(ax, 0.0, .20) * gauss(z, zc + 1.05, .45)
    tags['lip'] = lx * max(gauss(z, zc + .30 + bow, .26 + .06 * fr), gauss(z, zc - .40 * F['lip'], .32 + .08 * fr))
    tags['mouth'] = lx * math.exp(-((z - zc) / .11) ** 2)
    # chin, mentolabial sulcus, jaw width
    dy -= .40 * F['chin'] * (1 - .40 * soft) * gauss(ax, 0.0, 2.1 + .6 * soft) * gauss(z, -9.3, 1.3 + .4 * soft)
    dy += .22 * (1 - .55 * soft) * gauss(ax, 0.0, 1.7) * gauss(z, zc - 1.30, .38 + .20 * soft)
    djaw += sx * (F['jaw'] - 1.0) * 4.0 * gauss(z, -7.2, 2.4) * smooth(ax / 4.0)
    # naso-labial fold and age lines
    a0 = (1.75 * F['nose_w'], base + .1)
    a1 = (mw + .75, zc - .45)
    ex, ez = a1[0] - a0[0], a1[1] - a0[1]
    t = clamp(((ax - a0[0]) * ex + (z - a0[1]) * ez) / (ex * ex + ez * ez))
    d = math.hypot(ax - (a0[0] + ex * t), z - (a0[1] + ez * t))
    side = 1.0 if (ax - a0[0]) * ez - (z - a0[1]) * ex < 0 else -1.0
    age = F['wrinkle']
    dy += (.015 + .22 * age) * math.exp(-(d / .22) ** 2)
    dy -= (.015 + .20 * age) * math.exp(-((d - .55) / .38) ** 2) * (side > 0)
    if age > 0:
        dy += .05 * age * gauss(z, 6.2, 1.8) * math.sin(z * 5.1) * smooth((5.0 - ax) / 2.0)
        dy -= .14 * age * gauss(ax, 3.3, 1.0) * gauss(z, -.55, .35)        # under-eye bag
        dy += .10 * age * gauss(ax, 5.1, .4) * gauss(z, 1.0, .9)           # crow's feet crease
    # extra eye socket depth (the skull sculpt already has 1.35)
    xe, ze = eye_centre_xz(F)
    dy += .55 * gauss(ax, xe, 1.8) * gauss(z, ze + .25, 1.25)
    zc0 = mouth_geom(F)[1]
    dz += (zc0 + (z - zc0) * (.82 - .06 * r) - z) * smooth((zc0 - z) / 1.0)
    return (x + dx * front + djaw * wj + dxb * smooth((4.5 - y) / 2.5), y + dy * front + dyj * wj, z + dz * wj), tags


def surface(theta, phi, variant):
    rx, ry, rz = head_radii(variant)
    d = (math.cos(theta) * math.sin(phi), -math.cos(theta) * math.cos(phi), math.sin(theta))
    p = C.head_sculpt((rx * d[0], ry * d[1], rz * d[2]))
    return face_shape(p, variant['face'])


def find_front(x0, z0, variant):
    """Local point of the (pre-eye) face surface nearest (x0, z0) in the front view."""
    rx, ry, rz = head_radii(variant)
    best = None
    t0 = math.asin(clamp(z0 / rz, -.99, .99))
    p0 = math.asin(clamp(x0 / (rx * math.cos(t0)), -.99, .99))
    for i in range(-20, 21):
        for j in range(-20, 21):
            th, ph = t0 + i * .006, p0 + j * .006
            p, _ = surface(th, ph, variant)
            e = (p[0] - x0) ** 2 + (p[2] - z0) ** 2
            if best is None or e < best[0]:
                best = (e, p)
    return best[1]


def eye_rigs(variant):
    F = variant['face']
    xe, ze = eye_centre_xz(F)
    Re = 1.15 if F['female'] else 1.19
    rigs = {}
    for s in (-1, 1):
        apex = find_front(s * xe, ze, variant)
        rigs[s] = dict(x=s * xe, z=ze, R=Re, cy=apex[1] + .06 + Re, hw=.94 * Re,   # the opening always lands on the ball
                       open=F['open'], tilt=F['tilt'], side=s)
    return rigs


def lid_curves(E, x):
    lat = (x - E['x']) * E['side']
    u = (x - E['x']) / E['hw']
    k = max(0.0, 1 - u * u)
    zu = E['z'] + E['tilt'] * lat / E['hw'] + .42 * E['open'] * k ** .75 - .04
    zl = E['z'] + E['tilt'] * lat / E['hw'] - .38 * k ** .9 - .06
    return u, zu, zl


def eye_stage(p, eyes, tags):
    """Lids that cannot fail: outside the palpebral opening the skin is never BEHIND the eyeball
    (skin = the more forward of the carved socket and the ball + a 0.12 cm lid), and past the
    ball's rim the lid surface recedes smoothly into the socket instead of jumping to the ball's
    equator (which caved a black trench round every eye and let the sclera poke through)."""
    x, y, z = p
    for E in eyes.values():
        dxe, dze = x - E['x'], z - E['z']
        r = math.hypot(dxe, dze)
        Rb = E['R']
        if r > Rb + 1.2 or y > E['cy'] + .5:     # never the back of the skull at eye height
            continue
        yb = E['cy'] - math.sqrt(max(0.0, Rb * Rb - r * r)) if r < Rb else E['cy'] + 1.6 * (r - Rb)
        u, zu, zl = lid_curves(E, x)
        if abs(u) < 1 and zl < z < zu:
            y = max(y, yb + .08)
            tags['inside'] = 1.0
            continue
        fold = .10 * gauss(z, zu + .36, .16) if (z > zu and r < Rb) else 0.0
        cover = yb - .12 + fold
        if cover < y:
            tags['lid'] = max(tags.get('lid', 0.0), 1.0 if z > E['z'] else .5)
            y = cover
        if abs(u) < .95:                         # the lash line stops at the corners
            if 0 <= z - zu < .17:
                tags['lash'] = max(tags.get('lash', 0.0), 1 - (z - zu) / .17)
            if 0 <= zl - z < .10:
                tags['lash'] = max(tags.get('lash', 0.0), .45 * (1 - (zl - z) / .10))
    return (x, y, z), tags


def head_grid(variant, cols=100, rows=84):
    F = variant['face']
    xe, ze = eye_centre_xz(F)
    _, zm = mouth_geom(F)
    rz = HEAD_RZ
    te, tm = math.asin(ze / rz), math.asin(zm / rz)
    dth = lambda t: 1 + 2.4 * gauss(t, -.25, .42) + 3.0 * gauss(t, te + .01, .06) + 2.6 * gauss(t, tm, .055) + 1.6 * gauss(t, math.asin((ze + 1.6) / rz), .05) + .8 * gauss(t, math.asin(4.3 / rz), .06)
    dph = lambda a: 1 + 3.2 * gauss(a, 0.0, .50)
    thetas = R.warp(rows - 1, -math.pi / 2 + .05, math.pi / 2 - .05, dth)
    phis = R.warp(cols, -math.pi, math.pi, dph, endpoint=False)
    eyes = eye_rigs(variant)
    pts, tags, grid_tp = [], [], []
    for th in thetas:
        for ph in phis:
            p, tg = surface(th, ph, variant)
            p, tg = eye_stage(p, eyes, tg)
            pts.append(p)
            tags.append(tg)
            grid_tp.append((th, ph))
    return dict(points=pts, tags=tags, tp=grid_tp, rows=len(thetas), cols=len(phis), eyes=eyes,
                thetas=thetas, phis=phis)


def to_world(p):
    return (HEAD_C[0] + p[0], HEAD_C[1] + p[1], HEAD_C[2] + p[2])


def head_mesh(G):
    rows, cols = G['rows'], G['cols']
    v = [to_world(p) for p in G['points']]
    f = R.grid_faces(rows, cols, True)
    bot, top = len(v), len(v) + 1
    v.append(to_world((0, 0, -HEAD_RZ + .05)))
    v.append(to_world((0, 0, HEAD_RZ - .05)))
    for c in range(cols):
        f.append((bot, (c + 1) % cols, c))
        f.append((top, (rows - 1) * cols + c, (rows - 1) * cols + (c + 1) % cols))
    vol = sum(dot(v[a], cross(v[b], v[c])) for a, b, c in f)
    if vol < 0:
        f = [(a, c, b) for a, b, c in f]
    P = _period(8.6)
    uv = [((ph + math.pi) / TAU * P, p[2] / R.UV_CM) for (th, ph), p in zip(G['tp'], G['points'])]
    uv += [(0.0, v[bot][2] / R.UV_CM), (0.0, v[top][2] / R.UV_CM)]
    return v, f, uv, P


def skin_colours(G, variant):
    F = variant['face']
    base = C.SKIN_TONES[variant['skin_tone']][0]
    hair = F['hair']
    seed = variant['fold_seed']
    out = []
    beard = F['beard'] != 'none'
    for p, tg in zip(G['points'], G['tags']):
        x, y, z = p
        ax = abs(x)
        c = base
        fw = smooth((1.0 - y) / 4.0)                 # face tints never reach the back of the head
        tg = {k: v * fw for k, v in tg.items()}
        flush = .55 * gauss(ax, 4.0, 1.6) * gauss(z, -2.4, 1.8) + .65 * gauss(ax, 0, 1.0) * gauss(z, -2.2, 1.0)
        c = R.lerp3(c, R.mul3(base, (1.10, .78, .72)), clamp(flush * .40 * fw))
        xe, ze = eye_centre_xz(F)
        orb = gauss(ax, xe, 1.5) * gauss(z, ze + .15, 1.15)
        c = R.mul3(c, R.lerp3((1, 1, 1), (.84, .81, .86), orb * fw))
        c = R.lerp3(c, R.mul3(base, (.78, .44, .43) if F['female'] else (.80, .52, .49)),
                    clamp(tg.get('lip', 0) * (.95 if F['female'] else .80)))
        c = R.lerp3(c, R.mul3(base, (.35, .20, .19)), clamp(tg.get('mouth', 0) * (.9 - .35 * F.get('refine', 0.0))))
        c = R.lerp3(c, R.mul3(base, (.30, .20, .19)), clamp(tg.get('nostril', 0) * 1.2))
        c = R.mul3(c, R.lerp3((1, 1, 1), (.80, .75, .77), clamp(tg.get('lid', 0) * .85)))
        bz = ze + 1.55 + (.45 if F['female'] else .30) * math.sin(math.pi * clamp((ax - 1.2) / 4.4)) + (.10 if F['female'] else 0.0)
        wb = (.16 if F['female'] else .27) * F['brow_bush'] ** .5
        # refine: the band is at least one head-grid row (~0.25 cm at the brow) tall, so an arched brow
        # cannot fall between two rows and break into dashes
        wb = max(wb, BROW_MIN_W * F.get('refine', 0.0))
        bm = math.exp(-((z - bz) / wb) ** 4) * smooth((ax - 1.05) / .45) * smooth((5.7 - ax) / .9) * (y < 0)
        if bm > .01:
            streak = .80 + .40 * R.hash01(int(x * 9 + 90), int(z * 22 + 90), seed + 3)
            c = R.lerp3(c, tuple(min(1.0, h * streak) for h in hair), clamp(.88 * bm))
        if beard and not F['female'] and z < -1.0 and y < 2:
            c = R.mul3(c, R.lerp3((1, 1, 1), (.80, .82, .85), .35 * smooth((-1.0 - z) / 2.0)))
        m = 1 + .06 * R.vnoise(x + 20, z, seed, .55) + .035 * R.vnoise(x, z + 9, seed + 1, 1.9)
        if F['wrinkle'] > .5 and R.hash01(int(x * 3.1 + 40), int(z * 3.3 + 40), seed) > .985:
            m *= .82
        c = tuple(k * m for k in c)
        lash = tg.get('lash', 0.0)
        if lash:
            c = R.lerp3(c, tuple(min(h, .030) for h in hair), clamp(lash * .92))
        if tg.get('inside'):
            c = R.mul3(base, (.42, .26, .24))    # canthal tissue in shadow, not a black hole
        out.append(c)
    out += [base, base]
    return out


# ============================================================================= eyes
def eyeball(E):
    """Sphere with its poles on the gaze axis (-Y), so iris, limbus and pupil are exact rings."""
    c = to_world((E['x'], E['cy'], E['z']))
    Rr = E['R']
    alphas = [0, 4, 8, 12, 17, 23, 28.5, 31, 33.5, 38, 46, 58, 72, 88, 108, 135, 160, 180]
    seg = 28
    v, cols = [], []
    iris_c = None
    for a in alphas:
        ar = math.radians(a)
        bulge = .11 * math.cos(min(ar / math.radians(33), 1) * math.pi / 2) if a < 33 else 0.0
        n = 1 if a in (0, 180) else seg
        for j in range(n):
            b = j * TAU / seg
            d0 = (math.sin(ar) * math.cos(b), -math.cos(ar), math.sin(ar) * math.sin(b))
            ga = math.radians(3.0)                     # a relaxed gaze, a little below the horizon
            d = (d0[0], d0[1] * math.cos(ga) - d0[2] * math.sin(ga), d0[1] * math.sin(ga) + d0[2] * math.cos(ga))
            v.append(add(c, scale(d, Rr + bulge)))
    f = []
    rings = [1 if a in (0, 180) else seg for a in alphas]
    starts = [sum(rings[:i]) for i in range(len(rings))]
    for i in range(len(alphas) - 1):
        s0, s1, n0, n1 = starts[i], starts[i + 1], rings[i], rings[i + 1]
        for j in range(seg):
            if n0 == 1:
                f.append((s0, s1 + j, s1 + (j + 1) % seg))
            elif n1 == 1:
                f.append((s0 + j, s1, s0 + (j + 1) % seg))
            else:
                a0, b0 = s0 + j, s0 + (j + 1) % seg
                f += [(a0, s1 + j, s1 + (j + 1) % seg), (a0, s1 + (j + 1) % seg, b0)]
    return v, f, alphas, rings


def eye_colours(alphas, rings, iris, seed):
    out = []
    for a, n in zip(alphas, rings):
        for j in range(n):
            if a <= 8:
                c = (.012, .010, .010)
            elif a <= 28.5:
                k = .75 + .5 * R.hash01(j, int(a), seed)
                c = tuple(min(1.0, x * k * (1.30 if a < 15 else 1.0)) for x in iris)
            elif a <= 31:
                c = tuple(x * .45 for x in iris)
            else:
                t = smooth((a - 60) / 60)
                c = R.lerp3((.80, .76, .70), (.74, .60, .56), t * .6)
            out.append(c)
    return out


# ============================================================================= hair and beard shells
def shell(G, normals, mask_fn, thick_fn, colour_fn, thr=.12):
    rows, cols = G['rows'], G['cols']
    idx, v, uv, colours = {}, [], [], []
    P = _period(8.6)
    for r in range(rows):
        for c in range(cols):
            k = r * cols + c
            p, tg, (th, ph) = G['points'][k], G['tags'][k], G['tp'][k]
            m = mask_fn(p, th, ph, tg)
            if m <= thr:
                continue
            t = .03 + (thick_fn(p, th, ph, m) - .03) * smooth((m - thr) / .45)
            idx[k] = len(v)
            v.append(add(to_world(p), scale(normals[k], t)))
            uv.append(((ph + math.pi) / TAU * P, p[2] / R.UV_CM))
            colours.append(colour_fn(p, th, ph, m))
    f = []
    for r in range(rows - 1):
        for c in range(cols):
            a, b = r * cols + c, r * cols + (c + 1) % cols
            q = (a, b, b + cols, a + cols)
            if all(x in idx for x in q):
                f += [(idx[a], idx[b], idx[b + cols]), (idx[a], idx[b + cols], idx[a + cols])]
    hc = to_world((0, 0, 0))
    f = orient_open(v, f, lambda p: sub(p, hc))
    return v, f, uv, P, colours


def strand_colour(hair, skin, ph, z, m, seed, edge=.35):
    k = .70 + .60 * R.hash01(int((ph + 4) * 70), int(z * 1.7), seed)
    c = tuple(min(1.0, h * k) for h in hair)
    return R.lerp3(skin, c, smooth(m / edge) if m < edge else 1.0)


def beard_shell(G, normals, variant):
    F = variant['face']
    if F['beard'] == 'none':
        return None
    root, tip, base = nose_geom(F)
    mw, zm = mouth_geom(F)
    skin = C.SKIN_TONES[variant['skin_tone']][0]
    seed = variant['fold_seed'] + 31

    lim = 2.05
    if variant['headwear'] == 'cloth':
        lim = min(lim, math.radians(180 - variant.get('cloth_span', 112)) + .05)

    def mask(p, th, ph, tg):
        x, y, z = p
        ax = abs(x)
        if abs(ph) > lim:
            return 0.0
        line = (-3.7 + .95 * (ax - 3.0)) if ax >= 3.0 else (base - .20)
        m = smooth((line - z) / .45) * smooth((lim - abs(ph)) / .25)
        zc = zm - .20 * (ax / mw) ** 2
        lipzone = smooth((mw + .25 - ax) / .3) * smooth((z - (zc - 1.0)) / .16) * smooth(((zc + .60) - z) / .10)
        m *= 1 - lipzone
        if ax < 1.3 and base - 1.0 < z < base:          # nostril sill stays skin
            m *= smooth((base - .55 - z) / .3)
        return m

    def thick(p, th, ph, m):
        x, y, z = p
        style = F['beard']
        if style == 'short':
            t = .26 + .42 * smooth((-7.0 - z) / 3.0)
        elif style == 'full':
            t = .55 + 1.55 * smooth((-6.0 - z) / 4.0)
        else:
            t = .45 + 1.25 * smooth((-6.5 - z) / 4.0)
        t *= 1 + .22 * math.cos(ph * 41 + 3 * math.sin(z * 1.3))
        return .06 + t * m ** .7

    return shell(G, normals, mask, thick, lambda p, th, ph, m: strand_colour(F['hair'], skin, ph, p[2], m, seed))


def brow_shell(G, normals, variant):
    F = variant['face']
    xe, ze = eye_centre_xz(F)
    skin = C.SKIN_TONES[variant['skin_tone']][0]
    wb = (.22 if F['female'] else .30) * F['brow_bush'] ** .5

    def mask(p, th, ph, tg):
        x, y, z = p
        ax = abs(x)
        if y > 0:
            return 0.0
        bz = ze + 1.55 + .30 * math.sin(math.pi * clamp((ax - 1.2) / 4.4)) - (.15 if F['female'] else 0.0)
        return math.exp(-((z - bz) / wb) ** 2) * smooth((ax - 1.05) / .45) * smooth((5.7 - ax) / .9)

    def thick(p, th, ph, m):
        return .06 + .15 * m * F['brow_bush']

    return shell(G, normals, mask, thick,
                 lambda p, th, ph, m: strand_colour(F['hair'], skin, ph * 3, p[2] * 4, m, variant['fold_seed'] + 7, .5),
                 thr=.15)


def hair_shell(G, normals, variant):
    F = variant['face']
    skin = C.SKIN_TONES[variant['skin_tone']][0]
    wear = variant['headwear']
    top = 6.4 if wear == 'cap' else 6.0
    curly = wear == 'cap'

    def mask(p, th, ph, tg):
        x, y, z = p
        a = abs(ph)
        if a < 1.25:
            zh = (3.7 if F['female'] else 4.4) + .3 * (a / 1.25) ** 2
        elif a < 1.75:
            zh = (4.0 if F['female'] else 4.7) - (4.2 if F['female'] else 4.2) * smooth((a - 1.25) / .5)
        else:
            zh = .5 - 3.5 * smooth((a - 1.75) / .5)
        m = smooth((z - zh) / .35) * smooth((top - z) / .4)
        if F['female'] and y < 0:
            m *= 1 - .85 * math.exp(-(x / .28) ** 2) * smooth((z - 3.4) / .5)
        return m

    def thick(p, th, ph, m):
        t = .40 if not curly else .70 + .30 * abs(math.sin(ph * 18) * math.sin(p[2] * 4.1))
        return .05 + t * m ** .6

    return shell(G, normals, mask, thick,
                 lambda p, th, ph, m: strand_colour(F['hair'], skin, ph, p[2], m, variant['fold_seed'] + 13))


def beard_hang(variant):
    """The hanging part of a full / long beard under the chin (the shell covers the face)."""
    F = variant['face']
    if F['beard'] not in ('full', 'long'):
        return None
    bottom = -15.0 if F['beard'] == 'full' else -19.0
    folds = C.fold_field(variant['fold_seed'] + 3, .30, ((13, 1.0), (23, .5), (7, .6)))
    rings = []
    n = 9
    for i in range(n):
        u = i / (n - 1)
        z = bottom + (-8.3 - bottom) * u
        k = smooth(u ** .75)
        rings.append((HEAD_C[2] + z, 1.6 + 4.6 * k, 1.8 + 4.4 * k, 0.0, HEAD_C[1] - 4.2 + 2.6 * k))
    return loft_uv(rings, 40, radial=lambda t, z, l: folds(t, z, .9))


# ============================================================================= ears and neck
def ear(variant, s):
    rx, ry, rz = head_radii(variant)
    I, J = 16, 10
    grid = []
    for i in range(I):
        ii = i / (I - 1)
        z = -3.0 + 6.3 * ii
        w = 2.80 * math.sin(math.pi * (.06 + .88 * ii)) ** .32 * (.62 + .38 * smooth(ii / .35))
        yf = 1.0 + .27 * z                         # tilted back ~15 degrees
        row = []
        for j in range(J):
            jj = j / (J - 1)
            y = yf + w * jj
            k = max(.15, 1 - (y / ry) ** 2 - (z / rz) ** 2)
            xs = rx * math.sqrt(k) - .35
            hinge = (.15 + 1.05 * jj ** 1.3) * (.55 + .45 * smooth(ii / .25))
            d = hinge + .32 * smooth((jj - .78) / .22) + .28 * smooth((ii - .86) / .14)
            d -= .55 * gauss(jj, .36, .17) * gauss(ii, .45, .17)
            d += .22 * gauss(jj, .62, .08) * smooth((ii - .30) / .2)
            row.append(to_world((s * (xs + d), y, z)))
        grid.append(row)
    v, f, uv, P = panel_uv(grid, .32)
    f = orient_open(v, f, lambda p: (s, 0.0, 0.0)) if False else f
    vol = sum(dot(v[a], cross(v[b], v[c])) for a, b, c in f)
    if vol < 0:
        f = [(a, c, b) for a, b, c in f]
    skin = C.SKIN_TONES[variant['skin_tone']][0]
    colours = [R.lerp3(skin, R.mul3(skin, (1.12, .80, .74)), .45 * smooth((abs(p[0] - HEAD_C[0]) - rx - .6) / 1.0))
               for p in v]
    return v, f, uv, P, colours


def neck(variant):
    g = variant['girth']
    n = 5.5 * (.95 + .05 * g)
    r = variant['face'].get('refine', 0.0)
    k = 1 - .10 * r                     # refine: a narrower neck ...
    b = .9 * r                          # ... set further back under the jaw
    return loft_uv([(146.0, n * 1.12, n * 1.04, 0, .6), (150.0, n * .98 * k, n * .90 * k, 0, .5 + .3 * b),
                    (154.0, n * .94 * k, n * .86 * k, 0, .5 + .7 * b), (158.0, n * .97 * k, n * .90 * k, 0, .8 + b),
                    (161.5, n * 1.04 * k, n * .98 * k, 0, 1.3 + b), (164.0, n * 1.10 * k, n * 1.04 * k, 0, 1.8 + b)], 28)


# ============================================================================= morph fields
def _eye_guard(x, z, F):
    xe, ze = eye_centre_xz(F)
    g = 0.0
    for s in (-1, 1):
        g = max(g, smooth((2.4 - math.hypot(x - s * xe, z - ze)) / .8))
    return 1.0 - g


def morph_disp(k, pw, F):
    """Displacement (cm) of morph target k at rest world point pw. Smooth, front-weighted, zero round
    the eyes (lids and eyeballs never separate) and zero away from the face."""
    x, y, z = pw[0] - HEAD_C[0], pw[1] - HEAD_C[1], pw[2] - HEAD_C[2]
    if z < -24 or z > 9:
        return (0.0, 0.0, 0.0)
    ax = abs(x)
    sx = 1.0 if x >= 0 else -1.0
    front = smooth((2.0 - y) / 5.0)
    guard = _eye_guard(x, z, F)
    if k == 0:                                           # longer, more projecting nose
        a = gauss(ax, 0, 1.5) * gauss(z, -1.2, 1.6) * clamp((1.8 - z) / 3.5) * front
        return (0.0, -.50 * a, -.18 * a)
    if k == 1:                                           # broader jaw, longer chin
        a = gauss(z, -7.4, 2.4) * smooth(ax / 2.5) * front
        c = gauss(ax, 0, 2.0) * gauss(z, -9.6, 1.4) * front
        return (sx * .45 * a, -.28 * c, -.25 * c)
    if k == 2:                                           # heavier brow, higher cheekbones
        b = gauss(z, 3.5, 1.1) * gauss(ax, 3.2, 2.4) * front * guard
        c = gauss(ax, 4.9, 1.3) * gauss(z, -1.9, 1.3) * front * guard
        return (sx * .28 * c, -.30 * b - .20 * c, -.10 * b)
    a = gauss(ax, 0, 2.0) * gauss(z, -5.8, 1.0) * front   # fuller lips, wider mouth
    w = gauss(ax, 2.3, .6) * gauss(z, -5.7, .8) * front
    return (sx * .25 * w, -.28 * a, 0.0)

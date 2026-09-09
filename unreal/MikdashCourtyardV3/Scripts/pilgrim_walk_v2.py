"""PilgrimRigV3 walk cycle, re-authored. Offline; launches nothing.

Why
---
The shipped A_Pilgrim_Original_Walk (inherited verbatim from PilgrimRigV2) is two
counter-phase sinusoids on the ankles plus a 0.5 cm pelvis wobble. Measured by
forward kinematics off the source GLB at 240 Hz:

    ankle excursion   32.0 cm      pelvis bob      0.50 cm
    foot lift          5.0 cm      lateral sway    0.00 cm
    ground speed      53.3 cm/s    STANCE DRIFT    6.46 cm

That last number is the whole complaint. A sinusoid has no flat part, so the
"planted" foot is never still: against the best-fit ground speed it slides
+-6.5 cm inside every stance, i.e. it skates ~13 cm each step at any actor
speed. That is what "stilting" is, and no pace fix can hide it.

How this one is built instead
-----------------------------
The stance foot is authored as a RIGID BODY WITH A FIXED FOOTPRINT and the ankle
is derived from it, not the other way round. Over one stance the foot's contact
frame translates backwards in clip space at exactly one constant speed V - which
is what "in-place clip + actor moving forward at V" means - and it rotates only
about points that are themselves on the ground (Perry's rockers):

    s 0.00-0.10  heel rocker  pivot = rear sole point,  pitch -20deg -> 0
    s 0.10-0.52  foot flat    no motion at all beyond the constant V
    s 0.52-1.00  toe rocker   pivot = front sole point,  pitch  0 -> +36deg

Rotating a body about one of its own contact points cannot slide it, so the
footprint is stationary in world space for the whole stance BY CONSTRUCTION, and
the two feet stop being mirror images: one holds while the other flies.

The pivot is not a choice: the mesh weights the whole sandal sole to foot_* and
give ball_* no skin weight, so the foot is one rigid flat plate from y = +8.5 to
y = -19.7 in the foot bone's frame. A rigid flat sole tipped by theta touches the
ground at its rear point for theta < 0 and its front point for theta > 0, and at
theta = 0 the two coincide - so pivoting there is both the only non-penetrating
choice and automatically continuous. (Weighting the toe box to ball_* and giving
it a real MTP break is the geometry change that would let the forefoot roll over
the ball like a real foot; that is a rig job, not a clip job.)

The swing foot then gets a real trajectory - a cubic Hermite whose end tangents
are taken from the stance curve itself, so there is no velocity pop at toe-off
or heel strike - plus a raised-cosine lift solved to a 12 cm peak.

Everything else follows the six determinants of gait: pelvic transverse rotation,
pelvic list, stance-knee flexion, the two foot rockers and lateral pelvic
displacement, with trunk and arms counter-rotating against the pelvis.

The one compromise, stated plainly
----------------------------------
This rig's leg is short. skeleton() puts thigh_* at z = 88 and the ankle at
z = 6, so hip-to-ankle is 82.0 cm on a 179.4 cm figure = 0.457 H, where the
script's own PROPORTIONS table asks for a 0.53 H hip joint (94.9 cm, i.e. an
88.9 cm leg). A 72 cm step at 100 spm needs ~76 cm of fore-aft ankle travel, and
an 82 cm leg can only reach that by carrying the pelvis lower and the stance knee
more flexed than a real walker does: mean pelvis 93.4 cm against 95.8 in the old
clip and 98.0 standing, mid-stance knee ~32 deg against a real 15-20 deg. Under a
tunic at crowd distance that reads as a walk; the honest fix underneath it is to
raise thigh_* in the rig, which is a geometry change and out of scope here.

Sources for the gait numbers
----------------------------
J. Perry & J. Burnfield, *Gait Analysis: Normal and Pathological Function*,
2nd ed., Slack 2010, ch. 4 (stance/swing division, the rockers, joint ranges);
D. A. Winter, *Biomechanics and Motor Control of Human Movement*, 4th ed., Wiley
2009, ch. 2 and 14 (stride/cadence/speed relations, COM vertical displacement
~4-5 cm at twice stride frequency, lateral displacement ~4-5 cm at stride
frequency); Bohannon & Williams Andrews, Physiotherapy 97(3) 2011 (free walking
speed 1.2-1.45 m/s, step length near 0.41 x stature).

Nothing here is a native import, an in-engine acceptance, or a render.
"""
import math

TAU = 2.0 * math.pi

# --------------------------------------------------------------------------- gait
CYCLE_SECONDS = 1.2               # unchanged: 1.2 s stride = 100 steps/min
STEP_LENGTH_CM = 72.0             # 0.401 x the 179.4 cm stature of the V3 body
GROUND_SPEED_CM_S = 2.0 * STEP_LENGTH_CM / CYCLE_SECONDS      # 120.0 cm/s exactly
STANCE_DUTY = 0.58                # fraction of the cycle each foot is on the ground

HEEL_ROCKER_END = 0.10            # fractions of STANCE
TOE_ROCKER_START = 0.52
HEEL_STRIKE_PITCH = math.radians(-20.0)   # foot inclined toes-up at contact
TOE_OFF_PITCH = math.radians(36.0)        # heel high at push-off

# Solved by `python Scripts/pilgrim_walk_v2.py --calibrate`: the pair that puts
# the pelvis as high as an 82 cm leg allows while never straightening the knee
# to within REACH_MARGIN_CM of locked.
ANCHOR0_CM = -35.1
PELVIS_HEIGHT_CM = 93.40
REACH_MARGIN_CM = 1.2

PELVIS_BOB_CM = 2.0               # +-2 cm = 4 cm peak to peak, at TWICE stride frequency
PELVIS_SWAY_CM = 2.2              # +-2.2 cm toward the stance foot, at stride frequency
PELVIS_LIST = math.radians(4.0)   # swing-side hip drops
PELVIS_ROTATION = math.radians(4.0)    # swing-side hip swings forward
SHOULDER_COUNTER = math.radians(5.0)   # shoulder girdle rotates the other way
TRUNK_LEAN = math.radians(2.2)    # small forward lean of the whole walk

FOOT_HALF_WIDTH_CM = 5.5          # footprint x, i.e. an 11 cm step width
ANKLE_PEAK_Z_CM = 18.0            # 12 cm of lift over the 6 cm flat-stance ankle
SWING_LIFT_EXPONENT = 1.15        # >1 pushes the peak of the lift past mid-swing

ARM_SWING = math.radians(19.0)    # +-19 deg at the shoulder, opposite the same-side leg
ARM_BIAS = math.radians(-2.0)
ELBOW_MID = math.radians(26.0)
ELBOW_SWING = math.radians(12.0)

# Sole geometry in the foot bone's own rest frame, author cm (front -Y, Z up),
# read straight off the built SandalSole* parts: the plate runs from y = +8.5
# (rear) to y = -19.7 (front) and its underside is 6.0 cm below the ankle.
SOLE_Z_CM = -6.0
SOLE_REAR_Y_CM = 8.5
SOLE_FRONT_Y_CM = -19.7


# --------------------------------------------------------------------------- small math
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smoother(x):
    x = clamp(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def length(a):
    return math.sqrt(dot(a, a))


def normalize(a):
    n = length(a)
    return (0.0, 0.0, 1.0) if n < 1e-12 else (a[0] / n, a[1] / n, a[2] / n)


def qaxis(axis, angle):
    s = math.sin(angle / 2.0)
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(angle / 2.0))


def qmul(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return (w * X + x * W + y * Z - z * Y, w * Y - x * Z + y * W + z * X,
            w * Z + x * Y - y * X + z * W, w * W - x * X - y * Y - z * Z)


def qconj(q):
    return (-q[0], -q[1], -q[2], q[3])


def qrotate(q, p):
    return qmul(qmul(q, (p[0], p[1], p[2], 0.0)), qconj(q))[:3]


def shortest_arc(a, b):
    a, b = normalize(a), normalize(b)
    d = clamp(dot(a, b), -1.0, 1.0)
    if d > 1 - 1e-9:
        return (0.0, 0.0, 0.0, 1.0)
    if d < -1 + 1e-9:
        axis = cross(a, (1, 0, 0))
        if length(axis) < 1e-6:
            axis = cross(a, (0, 1, 0))
        axis = normalize(axis)
        return (axis[0], axis[1], axis[2], 0.0)
    axis = cross(a, b)
    s = math.sqrt((1 + d) * 2)
    return (axis[0] / s, axis[1] / s, axis[2] / s, s / 2)


def rot_x(angle, p):
    c, s = math.cos(angle), math.sin(angle)
    return (p[0], p[1] * c - p[2] * s, p[1] * s + p[2] * c)


# --------------------------------------------------------------------------- foot track
def stance_pitch(s):
    """Foot inclination during stance. +ve = heel up, -ve = toes up."""
    if s < HEEL_ROCKER_END:
        return HEEL_STRIKE_PITCH * (1.0 - smoother(s / HEEL_ROCKER_END))
    if s < TOE_ROCKER_START:
        return 0.0
    return TOE_OFF_PITCH * smoother((s - TOE_ROCKER_START) / (1.0 - TOE_ROCKER_START))


def swing_pitch(v):
    """Push-off plantarflexion unwinds fast, then a toes-up set for contact."""
    return (TOE_OFF_PITCH * (1.0 - smoother(v / 0.32))
            + HEEL_STRIKE_PITCH * smoother((v - 0.42) / 0.58))


def stance_ankle(u, side_x, anchor0=None):
    """Ankle position in clip space while this foot is planted, u in [0, STANCE_DUTY).

    The foot's contact frame sits at anchor0 + V t and never leaves it; the ankle
    is wherever the rigid foot puts it once the rocker rotation is applied. That
    is the whole trick: the ankle is an OUTPUT here, not the thing being animated.
    """
    anchor0 = ANCHOR0_CM if anchor0 is None else anchor0
    pitch = stance_pitch(u / STANCE_DUTY)
    # y of the ankle's ground projection with the sole flat: this is the rigid
    # foot's anchor, and it moves backwards at exactly V for the whole stance.
    flat = anchor0 + GROUND_SPEED_CM_S * u * CYCLE_SECONDS
    edge = SOLE_REAR_Y_CM if pitch < 0.0 else SOLE_FRONT_Y_CM
    pivot = (side_x, flat + edge, 0.0)
    return add(pivot, rot_x(pitch, (0.0, -edge, -SOLE_Z_CM))), pitch


def _stance_derivative(u, side_x, anchor0, h=1e-4):
    a = stance_ankle(u + h, side_x, anchor0)[0]
    b = stance_ankle(u - h, side_x, anchor0)[0]
    return scale(sub(a, b), 1.0 / (2 * h))


def _hermite(p0, m0, p1, m1, v):
    v2 = v * v
    v3 = v2 * v
    return tuple((2 * v3 - 3 * v2 + 1) * p0[i] + (v3 - 2 * v2 + v) * m0[i]
                 + (-2 * v3 + 3 * v2) * p1[i] + (v3 - v2) * m1[i] for i in range(3))


class FootTrack(object):
    """One foot's ankle path and pitch over the whole cycle, u in [0, 1)."""

    def __init__(self, side_x, anchor0=None, lift=None):
        anchor0 = ANCHOR0_CM if anchor0 is None else anchor0
        self.side_x = side_x
        self.anchor0 = anchor0
        swing = 1.0 - STANCE_DUTY
        self.p0, _ = stance_ankle(STANCE_DUTY - 1e-6, side_x, anchor0)
        # The clip plays in place, so in CLIP space the loop closes: whatever the
        # stance carried backwards, the swing carries forward again.
        self.p1, _ = stance_ankle(0.0, side_x, anchor0)
        self.m0 = scale(_stance_derivative(STANCE_DUTY - 2e-4, side_x, anchor0), swing)
        self.m1 = scale(_stance_derivative(2e-4, side_x, anchor0), swing)
        self.lift = _solve_lift(self) if lift is None else lift

    def raw(self, v):
        return _hermite(self.p0, self.m0, self.p1, self.m1, v)

    def __call__(self, u):
        u = u % 1.0
        if u < STANCE_DUTY:
            p, pitch = stance_ankle(u, self.side_x, self.anchor0)
            return p, pitch, True
        v = (u - STANCE_DUTY) / (1.0 - STANCE_DUTY)
        p = self.raw(v)
        p = (p[0], p[1], p[2] + self.lift * math.sin(math.pi * v ** SWING_LIFT_EXPONENT) ** 2)
        return p, swing_pitch(v), False


def _solve_lift(track, samples=480):
    """Bisect the raised-cosine amplitude so the ankle peaks at ANKLE_PEAK_Z_CM."""
    swing = 1.0 - STANCE_DUTY
    base = [(v / float(samples), track.raw(v / float(samples))[2]) for v in range(samples)]
    del swing
    lo, hi = 0.0, 40.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        peak = max(z + mid * math.sin(math.pi * v ** SWING_LIFT_EXPONENT) ** 2 for v, z in base)
        if peak < ANKLE_PEAK_Z_CM:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


TRACKS = {}


def _rebuild_tracks():
    TRACKS['r'] = FootTrack(-FOOT_HALF_WIDTH_CM)
    TRACKS['l'] = FootTrack(FOOT_HALF_WIDTH_CM)


_rebuild_tracks()


# --------------------------------------------------------------------------- the clip
def _leg(q, side, target, pitch, q_pelvis, pelvis_pos, hip_local, seg):
    """Two-bone IK in the pelvis frame; the knee is pushed toward the front."""
    inv = qconj(q_pelvis)
    local = qrotate(inv, sub(target, pelvis_pos))
    delta = sub(local, hip_local)
    d = length(delta)
    reach = 2.0 * seg - REACH_MARGIN_CM
    if d > reach:
        delta = scale(delta, reach / d)
        local = add(hip_local, delta)
        d = reach
    u = normalize(delta)
    front = qrotate(inv, (0.0, -1.0, 0.0))
    pole = sub(front, scale(u, dot(front, u)))
    if length(pole) < 1e-6:
        pole = sub((0.0, 0.0, -1.0), scale(u, dot((0.0, 0.0, -1.0), u)))
    pole = normalize(pole)
    knee = math.acos(clamp(d / (2.0 * seg), -1.0, 1.0))
    thigh_dir = add(scale(u, math.cos(knee)), scale(pole, math.sin(knee)))
    q_thigh = shortest_arc((0.0, 0.0, -1.0), thigh_dir)
    knee_pos = add(hip_local, scale(thigh_dir, seg))
    q_calf = shortest_arc((0.0, 0.0, -1.0), normalize(sub(local, knee_pos)))
    q['thigh_' + side] = q_thigh
    q['calf_' + side] = qmul(qconj(q_thigh), q_calf)
    q['foot_' + side] = qmul(qconj(q_calf), qmul(inv, qaxis((1.0, 0.0, 0.0), pitch)))
    return d, 2.0 * knee


def pelvis_state(u_r):
    """Pelvis translation and rotation at right-leg phase u_r."""
    bob = PELVIS_BOB_CM * math.cos(2.0 * TAU * (u_r - 0.30))
    sway = -PELVIS_SWAY_CM * math.cos(TAU * (u_r - 0.30))
    listing = -PELVIS_LIST * math.cos(TAU * (u_r - 0.80))
    rotation = PELVIS_ROTATION * math.cos(TAU * (u_r - 0.95))
    q = qmul(qaxis((0.0, 0.0, 1.0), rotation), qaxis((0.0, 1.0, 0.0), listing))
    return (sway, 0.0, PELVIS_HEIGHT_CM + bob), q, listing, rotation


def walk_pose(bones, time):
    """Joint-local rotations and the pelvis translation track for the new walk.

    Returns (rotations, translations) exactly as create_pilgrim_v3.pose() does.
    """
    rig = {b['name']: b for b in bones}
    seg = length(rig['calf_r']['local_translation_cm'])
    assert abs(seg - length(rig['foot_r']['local_translation_cm'])) < 1e-6, 'unequal thigh/calf'
    q = {b['name']: (0.0, 0.0, 0.0, 1.0) for b in bones}

    u_r = (time / CYCLE_SECONDS) % 1.0                 # right heel strike at u = 0
    u_l = (u_r + 0.5) % 1.0
    pelvis_pos, q_pelvis, listing, rotation = pelvis_state(u_r)
    q['pelvis'] = q_pelvis

    # ---- trunk: counter-rotate the shoulder girdle, lean a little into the walk
    counter = -(SHOULDER_COUNTER + PELVIS_ROTATION) * math.cos(TAU * (u_r - 0.95))
    upright = -listing * 0.75
    breathe = 0.006 * math.sin(2.0 * TAU * u_r)
    q['spine_01'] = qmul(qaxis((0, 0, 1), counter * 0.40),
                         qmul(qaxis((0, 1, 0), upright * 0.5),
                              qaxis((1, 0, 0), TRUNK_LEAN * 0.55)))
    q['spine_02'] = qmul(qaxis((0, 0, 1), counter * 0.35),
                         qmul(qaxis((0, 1, 0), upright * 0.3),
                              qaxis((1, 0, 0), TRUNK_LEAN * 0.45 + breathe)))
    q['chest'] = qaxis((0, 0, 1), counter * 0.25)
    chest_yaw = rotation + counter
    q['neck_01'] = qmul(qaxis((0, 0, 1), -chest_yaw * 0.55),
                        qaxis((1, 0, 0), -TRUNK_LEAN * 0.45 + 0.004 * math.sin(2.0 * TAU * u_r + 0.6)))
    q['head'] = qmul(qaxis((0, 0, 1), -chest_yaw * 0.45), qaxis((1, 0, 0), -TRUNK_LEAN * 0.55))

    # ---- legs: the stance foot is planted, the swing foot has its own trajectory
    reach = {}
    for side, u in (('r', u_r), ('l', u_l)):
        target, pitch, planted = TRACKS[side](u)
        d, _knee = _leg(q, side, target, pitch, q_pelvis, pelvis_pos,
                        rig['thigh_' + side]['local_translation_cm'], seg)
        reach[side] = d

    # ---- arms: opposite the same-side leg, elbow flexing on the forward swing
    for s, side, u in ((-1, 'r', u_r), (1, 'l', u_l)):
        swing = ARM_BIAS + ARM_SWING * math.cos(TAU * u)
        q['upperarm_' + side] = qmul(qaxis((0, 1, 0), s * math.radians(24.0)),
                                     qmul(qaxis((1, 0, 0), swing),
                                          qaxis((0, 1, 0), s * math.radians(3.0) * math.cos(TAU * u))))
        q['lowerarm_' + side] = qaxis((1, 0, 0), -(ELBOW_MID - ELBOW_SWING * math.cos(TAU * u)))
        q['clavicle_' + side] = qaxis((0, 0, 1), -counter * 0.15)

    # ---- cloth: the skirt panels trail the thigh, the mantle rides the bob
    for side, u in (('r', u_r), ('l', u_l)):
        lagged = TRACKS[side]((u - 0.055) % 1.0)[0]
        angle = _sagittal(lagged, pelvis_pos, q_pelvis,
                          rig['thigh_' + side]['local_translation_cm'])
        q['skirt_' + side] = qaxis((1, 0, 0), angle * 0.45)
    q['mantle_front'] = qaxis((1, 0, 0), 0.022 * math.sin(TAU * u_r) - TRUNK_LEAN * 0.30)
    q['mantle_back'] = qaxis((1, 0, 0), -0.018 * math.sin(TAU * u_r + 0.35))

    assert max(reach.values()) <= 2.0 * seg - REACH_MARGIN_CM + 1e-6, (
        'leg over-reached at t=%.4f: %s - re-run --calibrate' % (time, reach))
    return q, {'pelvis': pelvis_pos}


def _sagittal(target, pelvis_pos, q_pelvis, hip_local):
    """Angle of the hip->ankle line in the sagittal plane, for the cloth panels."""
    local = qrotate(qconj(q_pelvis), sub(target, pelvis_pos))
    d = sub(local, hip_local)
    return math.atan2(d[1], -d[2])


# --------------------------------------------------------------------------- calibration
def _max_reach(bones, samples=720):
    rig = {b['name']: b for b in bones}
    worst = 0.0
    for i in range(samples):
        u_r = i / float(samples)
        pelvis_pos, q_pelvis, _, _ = pelvis_state(u_r)
        inv = qconj(q_pelvis)
        for side, u in (('r', u_r), ('l', (u_r + 0.5) % 1.0)):
            target = TRACKS[side](u)[0]
            local = qrotate(inv, sub(target, pelvis_pos))
            worst = max(worst, length(sub(local, rig['thigh_' + side]['local_translation_cm'])))
    return worst


def _headroom(bones, samples=720):
    """How much higher the pelvis could sit before the knee locks.

    Raising PELVIS_HEIGHT_CM by d translates every hip joint up by d and leaves
    the foot tracks and the pelvis rotation alone, so the reach constraint at one
    sample is (h + d)^2 + r^2 <= limit^2 with h the current hip-above-ankle rise
    and r the horizontal offset. One pass gives the exact answer.
    """
    rig = {b['name']: b for b in bones}
    seg = length(rig['calf_r']['local_translation_cm'])
    limit = 2.0 * seg - REACH_MARGIN_CM
    room = 1e9
    worst = 0.0
    for i in range(samples):
        u_r = i / float(samples)
        pelvis_pos, q_pelvis, _, _ = pelvis_state(u_r)
        for side, u in (('r', u_r), ('l', (u_r + 0.5) % 1.0)):
            target = TRACKS[side](u)[0]
            hip = add(pelvis_pos, qrotate(q_pelvis, rig['thigh_' + side]['local_translation_cm']))
            delta = sub(hip, target)
            r = math.hypot(delta[0], delta[1])
            h = delta[2]
            worst = max(worst, math.sqrt(r * r + h * h))
            if r >= limit:
                return -1e9, worst
            room = min(room, math.sqrt(limit * limit - r * r) - h)
    return room, worst


def _max_reach(bones, samples=720):
    return _headroom(bones, samples)[1]


def calibrate(bones):
    """Pick ANCHOR0_CM and PELVIS_HEIGHT_CM: the highest pelvis an 82 cm leg allows."""
    global ANCHOR0_CM, PELVIS_HEIGHT_CM
    rig = {b['name']: b for b in bones}
    seg = length(rig['calf_r']['local_translation_cm'])
    limit = 2.0 * seg - REACH_MARGIN_CM
    keep = (ANCHOR0_CM, PELVIS_HEIGHT_CM)
    base = PELVIS_HEIGHT_CM
    best = None
    for step in range(-600, 1):
        ANCHOR0_CM = step / 10.0
        _rebuild_tracks()
        PELVIS_HEIGHT_CM = base
        room, _ = _headroom(bones, 240)
        if room < -1e8:
            continue
        height = base + room
        if best is None or height > best[1]:
            best = (ANCHOR0_CM, height)
    ANCHOR0_CM = round(best[0], 2)
    _rebuild_tracks()
    PELVIS_HEIGHT_CM = base
    room, _ = _headroom(bones, 1440)
    PELVIS_HEIGHT_CM = round(base + room - 0.02, 2)
    _rebuild_tracks()
    result = {'anchor0Cm': ANCHOR0_CM, 'pelvisHeightCm': PELVIS_HEIGHT_CM,
              'maxHipToAnkleCm': round(_max_reach(bones, 1440), 3),
              'reachLimitCm': round(limit, 3),
              'swingLiftCm': round(TRACKS['r'].lift, 3),
              'groundSpeedCmPerSec': GROUND_SPEED_CM_S,
              'stepLengthCm': STEP_LENGTH_CM, 'stanceDuty': STANCE_DUTY}
    ANCHOR0_CM, PELVIS_HEIGHT_CM = keep
    _rebuild_tracks()
    return result


if __name__ == '__main__':
    import json
    import pathlib
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from create_pilgrim_v3 import skeleton
    bones = skeleton()
    if '--calibrate' in sys.argv:
        print(json.dumps(calibrate(bones), indent=2))
    else:
        seg = length({b['name']: b for b in bones}['calf_r']['local_translation_cm'])
        print(json.dumps({'anchor0Cm': ANCHOR0_CM, 'pelvisHeightCm': PELVIS_HEIGHT_CM,
                          'swingLiftCm': round(TRACKS['r'].lift, 3),
                          'groundSpeedCmPerSec': GROUND_SPEED_CM_S,
                          'maxHipToAnkleCm': round(_max_reach(bones), 3),
                          'reachLimitCm': round(2 * seg - REACH_MARGIN_CM, 3)}, indent=2))

"""PilgrimRigV3 lamp-tending clip (hatavat haneiros), authored offline as FK curves.

Offline; launches nothing. Same method as pilgrim_walk_v2: every joint's local rotation
is a function of time, legs and arms are solved by two-bone IK, and the GLB is written by
Scripts/retend_pilgrim_v3.py through the same create_pilgrim_v3 geometry path.

WHAT IT DEPICTS, per the station's own action text in ServiceScheduleMath.h
("Tending a lamp: clearing the spent wick and oil, setting a fresh wick and oil,
kindling it" -- Rambam, Temidin uMusafin 3:11-3:12, SVC-HATAVAH):
    0.0-1.6   weight comes forward over the stone (hip hinge + trunk lean + a small
              twist toward the lamp), head drops to look into the bowl, right arm rises
    1.6-4.1   hand at the bowl: two slow circles of the wrist -- clearing the spent wick
    4.1-5.2   hand draws back to the left hand held at the belt (the kuz he carries,
              which the next station leaves on the second step, Temidin 3:17) -- no
              prop is modelled, the hand only meets the other hand
    5.2-6.4   reach again; 6.1-7.3 the wrist rolls over and back -- fresh wick and oil
    7.3-8.6   hand held at the wick. THE LAMP IS KINDLED AT KINDLE_AT = 7.6 s
              (AMikdashServiceActor::KindleAtClipSeconds must carry the same number)
    8.6-10.0  withdraw, straighten, back to the Idle clip's t = 0 pose exactly
Nothing here asserts which hand, the gesture, or the durations. Those are design (D).

GEOMETRY IT IS AUTHORED TO -- MEASURED, not guessed
(SourceAssets/service-review/tend-geometry-probe-20260911T003954381275Z.json, Candidate48,
the map that ships):
    his feet on the top tread       X -5306.33 (decoded TendingStonePoint), Z 936.0
    top tread                       X -5320.3 .. -5290 (30 cm deep; 16 cm risers)
    lamp flames (FX anchors)        X -5364.8, Z 1028.80 = the lid crown of each bowl
    lamp bowls (SM_MenorahV4_Lamps) X -5375.0 .. -5359.1, Z 1023.98 .. 1032.33
    => the wick is 58.5 cm ahead of his feet and 92.8 cm above his soles; the near rim of
       the bowl is 52.8 cm ahead and its top 96.3 cm up. His shoulder joint is 143 cm up
       (V3 Man_Standard reference pose), so the wick is 50 cm below his shoulder: level
       with his hip joint. With feet planted and an unleaned trunk the wrist would need
       75 cm of reach against 56.4; the hinge + twist below bring that to ~45 cm.
Main50's stone and stand differ (stand 91 cm from the lamps); this clip is NOT authored
to it. See the receipt.
"""
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import create_pilgrim_v3 as C          # noqa: E402

CLIP = 'Tend'
ANIM_NAME = 'A_Pilgrim_V3_TendLamp'
DURATION = 10.0
FPS = 30
KINDLE_AT = 7.6

# ---- measured scene geometry, author frame (feet at origin, front -Y, Z up) --------------
STAND_X_CM = -5306.33
WICK_WORLD = (-5364.8, 1028.803)
SOLE_Z_WORLD = 936.0
WICK = (0.0, -(STAND_X_CM - WICK_WORLD[0]), WICK_WORLD[1] - SOLE_Z_WORLD)   # (0, -58.47, 92.8)
BOWL_NEAR_RIM_Y = -(STAND_X_CM - (-5359.12))                                  # -52.79
BOWL_TOP_Z = 1032.33 - SOLE_Z_WORLD                                           # 96.33

# ---- posture limits (design) ---------------------------------------------------------------
LEAN_MAX = math.radians(22.0)      # total forward pitch, hips to chest
TWIST_MAX = math.radians(12.0)     # trunk yaw that brings the right shoulder toward the lamp
HEAD_DOWN = math.radians(30.0)     # neck + head, on top of the trunk lean
PELVIS_BACK_CM = 1.5
PELVIS_DROP_CM = 2.5               # soft knees: also keeps the IK off a locked knee
HAND_TIP_CM = 13.0                 # wrist -> middle of the fingers along the hand axis
IDLE_ARM_ABDUCT = math.radians(24.0)
IDLE_ELBOW = -0.045

ANKLES = {'r': (-8.0, 0.0, 6.0), 'l': (8.0, 0.0, 6.0)}


# --------------------------------------------------------------------------- small math
qaxis, qmul, qconj, qrotate = C.qaxis, C.qmul, C.qconj, C.qrotate
add, sub, scale, length, normalize, cross, dot = C.add, C.sub, C.scale, C.length, C.normalize, C.cross, C.dot


def smoother(x):
    x = 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
    return x * x * x * (x * (x * 6 - 15) + 10)


def qslerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0.0:
        b, d = tuple(-x for x in b), -d
    if d > 0.9995:
        r = tuple(x + (y - x) * t for x, y in zip(a, b))
    else:
        th = math.acos(d)
        s = math.sin(th)
        wa, wb = math.sin((1 - t) * th) / s, math.sin(t * th) / s
        r = tuple(wa * x + wb * y for x, y in zip(a, b))
    n = math.sqrt(sum(x * x for x in r))
    return tuple(x / n for x in r)


def keyed(t, keys):
    """Piecewise quintic-smooth interpolation through (time, value) keys; values are
    floats or tuples, or callables of t returning either."""
    def val(v):
        return v(t) if callable(v) else v
    if t <= keys[0][0]:
        return val(keys[0][1])
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = smoother((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            a, b = val(v0), val(v1)
            if isinstance(a, tuple):
                return tuple(x + (y - x) * u for x, y in zip(a, b))
            return a + (b - a) * u
    return val(keys[-1][1])


# --------------------------------------------------------------------------- timeline
LEAN_KEYS = [(0.2, 0.0), (1.6, 1.0), (4.1, 1.0), (4.9, 0.55), (5.3, 0.55), (6.1, 1.0),
             (8.6, 1.0), (9.9, 0.0)]
LOOK_KEYS = [(0.1, 0.0), (1.3, 1.0), (4.1, 1.0), (4.8, 0.6), (5.4, 0.6), (6.0, 1.0),
             (8.7, 1.0), (9.8, 0.0)]
ARM_R_KEYS = [(0.3, 0.0), (1.6, 1.0), (8.6, 1.0), (9.9, 0.0)]
ARM_L_KEYS = [(0.3, 0.0), (1.5, 1.0), (8.9, 1.0), (9.95, 0.0)]
HOVER = (3.0, BOWL_NEAR_RIM_Y + 3.0, BOWL_TOP_Z + 8.0)
AT_BOWL = (1.0, BOWL_NEAR_RIM_Y - 1.5, BOWL_TOP_Z + 1.5)
AT_WICK = (0.0, WICK[1] + 2.0, WICK[2] + 4.0)     # fingers just east of and above the wick


def _deposit(state):
    return lambda t: state['left_tip']


def right_tip_keys(state):
    dep = _deposit(state)
    return [(1.6, HOVER), (2.0, AT_BOWL), (3.9, AT_BOWL), (4.2, HOVER),
            (4.95, lambda t: add(dep(t), (-2.0, -2.5, 4.0))), (5.25, lambda t: add(dep(t), (-2.0, -2.5, 4.0))),
            (6.0, (0.5, BOWL_NEAR_RIM_Y + 0.5, BOWL_TOP_Z + 5.5)),
            (6.4, (0.5, BOWL_NEAR_RIM_Y - 1.5, BOWL_TOP_Z + 2.0)), (7.3, (0.5, BOWL_NEAR_RIM_Y - 1.5, BOWL_TOP_Z + 2.0)),
            (7.55, AT_WICK), (8.6, AT_WICK), (9.6, (3.0, -44.0, 104.0))]


def _dir(pitch_down_deg, lateral=0.0):
    p = math.radians(pitch_down_deg)
    return normalize((lateral, -math.cos(p), -math.sin(p)))


R_DIR_KEYS = [(1.6, _dir(30)), (2.0, _dir(42)), (3.9, _dir(42)), (4.3, _dir(25)),
              (4.95, normalize((0.65, -0.45, -0.6))), (5.25, normalize((0.65, -0.45, -0.6))),
              (6.0, _dir(35)), (6.4, _dir(45)), (7.3, _dir(45)), (7.55, _dir(40)), (8.6, _dir(40)),
              (9.6, _dir(20))]


def right_roll(t):
    """Rotation of the hand about its own axis (pronation +)."""
    clean = 0.0
    if 2.0 <= t <= 3.9:
        env = smoother((t - 2.0) / 0.3) * smoother((3.9 - t) / 0.3)
        clean = math.radians(16.0) * env * math.sin(math.tau * 1.05 * (t - 2.0))
    pour = keyed(t, [(6.1, 0.0), (6.6, math.radians(38.0)), (7.0, math.radians(38.0)),
                     (7.45, math.radians(6.0)), (8.6, math.radians(6.0)), (9.4, 0.0)])
    return clean + pour


def right_circle(t):
    """Two slow circles of the fingers in the bowl: lifting out the spent wick."""
    if not 2.0 <= t <= 3.9:
        return (0.0, 0.0, 0.0)
    env = smoother((t - 2.0) / 0.3) * smoother((3.9 - t) / 0.3)
    a = math.tau * 1.05 * (t - 2.0)
    return (2.0 * env * math.cos(a) - 2.0 * env, 1.6 * env * math.sin(a), 0.9 * env * math.sin(2 * a))


LEFT_WRIST_REST = (10.0, -22.0, 104.0)             # parent-rest frame: left hand at the belt
LEFT_DIR_REST = normalize((-0.62, -0.55, -0.35))


# --------------------------------------------------------------------------- rig helpers
def _idle_q(bones):
    q = {b['name']: (0.0, 0.0, 0.0, 1.0) for b in bones}
    for s, side in ((-1, 'r'), (1, 'l')):
        q['upperarm_' + side] = qaxis((0, 1, 0), s * IDLE_ARM_ABDUCT)
        q['lowerarm_' + side] = qaxis((1, 0, 0), IDLE_ELBOW)
    return q


def fk(bones, q, trans):
    out = []
    for b in bones:
        lq = q[b['name']]
        lt = trans.get(b['name'], b['local_translation_cm'])
        if b['parent_index'] is None:
            out.append((lq, lt))
        else:
            pq, pt = out[b['parent_index']]
            out.append((qmul(pq, lq), add(pt, qrotate(pq, lt))))
    return out


def _leg(q, side, target, q_pelvis, pelvis_pos, hip_local, seg):
    """Two-bone IK in the pelvis frame, feet flat, knee toward the front. Margin 0 so
    the unleaned rest (hip-to-ankle exactly 2 x seg) solves to identity."""
    inv = qconj(q_pelvis)
    local = qrotate(inv, sub(target, pelvis_pos))
    delta = sub(local, hip_local)
    d = length(delta)
    if d > 2.0 * seg:
        delta = scale(delta, 2.0 * seg / d)
        local = add(hip_local, delta)
        d = 2.0 * seg
    u = normalize(delta)
    front = qrotate(inv, (0.0, -1.0, 0.0))
    pole = sub(front, scale(u, dot(front, u)))
    pole = normalize(pole) if length(pole) > 1e-6 else (0.0, -1.0, 0.0)
    knee = math.acos(max(-1.0, min(1.0, d / (2.0 * seg))))
    thigh_dir = add(scale(u, math.cos(knee)), scale(pole, math.sin(knee)))
    q_thigh = C.shortest_arc((0.0, 0.0, -1.0), thigh_dir)
    knee_pos = add(hip_local, scale(thigh_dir, seg))
    q_calf = C.shortest_arc((0.0, 0.0, -1.0), normalize(sub(local, knee_pos)))
    q['thigh_' + side] = q_thigh
    q['calf_' + side] = qmul(qconj(q_thigh), q_calf)
    q['foot_' + side] = qmul(qconj(q_calf), inv)
    return d


def _hand_rest_dir(side):
    s = -1 if side == 'r' else 1
    return normalize((s * C.ARM_DIR[0], 0.0, C.ARM_DIR[2]))


def _arm_to(bones, q, trans, side, wrist_world, pole_rest, hand_dir_world, roll, weight, idx):
    """Solve one arm for a WORLD wrist target in its clavicle's frame, then blend with the
    idle arm by `weight`. Returns the unclamped shoulder-to-wrist distance for the report."""
    s = -1 if side == 'r' else 1
    g = fk(bones, q, trans)
    qc, _ = g[idx['clavicle_' + side]]
    _, shoulder = g[idx['upperarm_' + side]]
    root_rest = (s * C.ARM_SHOULDER_X, 0.0, C.ARM_SHOULDER_Z)
    target_rest = add(root_rest, qrotate(qconj(qc), sub(wrist_world, shoulder)))
    qu, ql = C.arm_ik(side, target_rest, pole_rest)
    hand_dir_rest = qrotate(qconj(qc), hand_dir_world)
    qh_rest = qmul(qaxis(hand_dir_rest, roll), C.shortest_arc(_hand_rest_dir(side), hand_dir_rest))
    qhand = qmul(qconj(qmul(qu, ql)), qh_rest)
    idle = _idle_q(bones)
    q['upperarm_' + side] = qslerp(idle['upperarm_' + side], qu, weight)
    q['lowerarm_' + side] = qslerp(idle['lowerarm_' + side], ql, weight)
    q['hand_' + side] = qslerp((0.0, 0.0, 0.0, 1.0), qhand, weight)
    return length(sub(target_rest, root_rest))


def _arm_rest_target(bones, q, side, wrist_rest, pole_rest, hand_dir_rest, weight):
    qu, ql = C.arm_ik(side, wrist_rest, pole_rest)
    qh_rest = C.shortest_arc(_hand_rest_dir(side), hand_dir_rest)
    qhand = qmul(qconj(qmul(qu, ql)), qh_rest)
    idle = _idle_q(bones)
    q['upperarm_' + side] = qslerp(idle['upperarm_' + side], qu, weight)
    q['lowerarm_' + side] = qslerp(idle['lowerarm_' + side], ql, weight)
    q['hand_' + side] = qslerp((0.0, 0.0, 0.0, 1.0), qhand, weight)


def tend_pose(bones, time, report=None):
    """Joint-local rotations and the pelvis translation, like create_pilgrim_v3.pose()."""
    idx = {b['name']: i for i, b in enumerate(bones)}
    rig = {b['name']: b for b in bones}
    seg = length(rig['calf_r']['local_translation_cm'])
    t = max(0.0, min(DURATION, time))
    q = _idle_q(bones)
    lw = keyed(t, LEAN_KEYS)
    look = keyed(t, LOOK_KEYS)
    lean, twist = LEAN_MAX * lw, TWIST_MAX * lw
    breathe = 0.0   # the Idle clip's own breathing is not layered: both ends must equal Idle t=0

    q_pelvis = qaxis((1, 0, 0), 0.35 * lean)
    pelvis_pos = (0.0, PELVIS_BACK_CM * lw, 98.0 - PELVIS_DROP_CM * lw)
    trans = {'pelvis': pelvis_pos}
    q['pelvis'] = q_pelvis
    q['spine_01'] = qmul(qaxis((0, 0, 1), 0.30 * twist), qaxis((1, 0, 0), 0.30 * lean))
    q['spine_02'] = qmul(qaxis((0, 0, 1), 0.35 * twist), qaxis((1, 0, 0), 0.20 * lean + breathe))
    q['chest'] = qmul(qaxis((0, 0, 1), 0.35 * twist), qaxis((1, 0, 0), 0.15 * lean))
    q['neck_01'] = qmul(qaxis((0, 0, 1), -0.5 * twist), qaxis((1, 0, 0), 0.45 * HEAD_DOWN * look))
    q['head'] = qmul(qaxis((0, 0, 1), -0.5 * twist), qaxis((1, 0, 0), 0.55 * HEAD_DOWN * look - breathe * .6))
    for side in ('r', 'l'):
        _leg(q, side, ANKLES[side], q_pelvis, pelvis_pos, rig['thigh_' + side]['local_translation_cm'], seg)
        q['skirt_' + side] = qaxis((1, 0, 0), -0.35 * lean * 0.8)
    q['mantle_front'] = qaxis((1, 0, 0), -0.65 * lean * 0.45)
    q['mantle_back'] = qaxis((1, 0, 0), -0.65 * lean * 0.20)

    # left hand to the belt, riding with the chest (targets in the clavicle's rest frame)
    wl = keyed(t, ARM_L_KEYS)
    _arm_rest_target(bones, q, 'l', LEFT_WRIST_REST, (52.0, 18.0, 102.0), LEFT_DIR_REST, wl)
    g = fk(bones, q, trans)
    hq, hp = g[idx['hand_l']]
    state = {'left_tip': add(hp, scale(qrotate(hq, _hand_rest_dir('l')), HAND_TIP_CM))}

    # right hand to the lamp
    wr = keyed(t, ARM_R_KEYS)
    tip = add(keyed(t, right_tip_keys(state)), right_circle(t))
    hand_dir = normalize(keyed(t, R_DIR_KEYS))
    wrist = sub(tip, scale(hand_dir, HAND_TIP_CM))
    reach = _arm_to(bones, q, trans, 'r', wrist, (-58.0, 14.0, 104.0), hand_dir, right_roll(t), wr, idx)
    if report is not None:
        report.update(lean=lw, armR=wr, armL=wl, tipTarget=tip, wristTarget=wrist, reachCm=reach)
    return q, trans


def hand_tip(bones, q, trans, side='r'):
    idx = {b['name']: i for i, b in enumerate(bones)}
    g = fk(bones, q, trans)
    hq, hp = g[idx['hand_' + side]]
    return add(hp, scale(qrotate(hq, _hand_rest_dir(side)), HAND_TIP_CM))


def measure(bones, rate=60.0):
    """Offline checks on the authored curves (same FK the exporter samples)."""
    idx = {b['name']: i for i, b in enumerate(bones)}
    limit = C.length(C.ARM_CHAIN['r'][1]) + C.length(C.ARM_CHAIN['r'][2]) - 0.8
    idle = C.pose(bones, 'Idle', 0.0)[0]
    n = int(round(DURATION * rate))
    ankle0 = None
    worst_ankle, min_sole, worst_reach = 0.0, 1e9, 0.0
    tips = []
    for i in range(n + 1):
        t = i / rate
        rep = {}
        q, trans = tend_pose(bones, t, rep)
        g = fk(bones, q, trans)
        ankles = [g[idx['foot_r']][1], g[idx['foot_l']][1]]
        if ankle0 is None:
            ankle0 = ankles
        worst_ankle = max(worst_ankle, max(length(sub(a, b)) for a, b in zip(ankles, ankle0)))
        for side in ('r', 'l'):
            fq, fp = g[idx['foot_' + side]]
            for y in (8.5, 0.0, -19.7):
                min_sole = min(min_sole, add(fp, qrotate(fq, (0.0, y, -6.0)))[2])
        worst_reach = max(worst_reach, rep['reachCm'] if rep['armR'] > 0.99 else 0.0)
        tips.append((t, hand_tip(bones, q, trans), rep))
    at_kindle = min(tips, key=lambda r: abs(r[0] - KINDLE_AT))
    wick_d = length(sub(at_kindle[1], WICK))
    clean = [r for r in tips if 2.0 <= r[0] <= 3.9]
    bowl_centre = (0.0, WICK[1], BOWL_TOP_Z)
    q0 = tend_pose(bones, 0.0)[0]
    q1 = tend_pose(bones, DURATION)[0]

    def qdiff(a, b):
        return max(min(sum(abs(x - y) for x, y in zip(a[k], b[k])),
                       sum(abs(x + y) for x, y in zip(a[k], b[k]))) for k in a)
    return {
        'durationSeconds': DURATION, 'fps': FPS, 'kindleAtSeconds': KINDLE_AT,
        'wickAuthorCm': [round(v, 2) for v in WICK],
        'handTipAtKindleCm': [round(v, 2) for v in at_kindle[1]],
        'handTipToWickAtKindleCm': round(wick_d, 2),
        'handTipToBowlCentreDuringClearingCm': [round(min(length(sub(r[1], bowl_centre)) for r in clean), 2),
                                                round(max(length(sub(r[1], bowl_centre)) for r in clean), 2)],
        'maxShoulderToWristWhileReachingCm': round(worst_reach, 2),
        'armReachLimitCm': round(limit, 2),
        'reachNeverClamped': worst_reach <= limit,
        'plantedAnkleMaxDriftCm': round(worst_ankle, 4),
        'lowestSolePointCm': round(min_sole, 3),
        'startMatchesIdleT0MaxQuatAbsDiff': round(qdiff(q0, idle), 6),
        'endMatchesIdleT0MaxQuatAbsDiff': round(qdiff(q1, idle), 6),
        'maxLeanDegrees': round(math.degrees(LEAN_MAX), 1), 'maxTwistDegrees': round(math.degrees(TWIST_MAX), 1),
    }


if __name__ == '__main__':
    import json
    print(json.dumps(measure(C.skeleton()), indent=2))

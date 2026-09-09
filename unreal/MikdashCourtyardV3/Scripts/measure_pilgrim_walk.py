"""Measure a PilgrimRig walk clip by forward kinematics off the source GLB.

Offline only: parses the GLB container itself, samples every animation channel the
way a player does (glTF LINEAR: lerp on translation, slerp on rotation), runs FK
down the joint hierarchy and reports the gait numbers that decide whether a walk
reads as a walk.

Definitions, fixed here so "before" and "after" are the same measurement
-----------------------------------------------------------------------
ankleExcursionCm   peak-to-peak fore-aft travel of one ankle joint (foot_r) in
                   clip space over one cycle. This is the number the earlier
                   diagnosis called "step length" (32.0 cm on V3).
peakFootSeparation max fore-aft distance between the two ankles at any instant.
                   For a clip with no stance plant these two coincide; for a real
                   gait the excursion is larger than the separation by the stance
                   duty factor, and that difference is itself the plant.
contact            a foot is in contact while the lowest of its three sole
                   markers (heel / ball / toe, taken in the foot bone's own rest
                   frame) is within CONTACT_Z_CM of the ground plane.
groundSpeed        the clip is in place, so a foot that is really planted must
                   travel backwards in clip space at exactly the actor's forward
                   ground speed. One least-squares fit of that speed over every
                   contact window of both feet is the clip's own ground speed -
                   the number MikdashResidentPopulation.cpp has to carry.
stanceDriftCm      with that fitted speed applied, the residual world-space
                   movement of the planted contact point, max over the window.
                   Near zero = the foot plants. Large = the figure stilts.
footFlatPlantDrift the same residual restricted to the frames where the WHOLE
                   sole is on the floor. Threshold-proof - a flat foot is
                   unambiguously down - so this is the headline plant number;
                   stanceDrift additionally carries the touchdown and lift-off
                   frames, where a contact point is a millimetre off the floor
                   and already moving.
"""
import argparse
import json
import math
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True

# A sole point counts as planted while it is on the ground plane to within
# CONTACT_Z_CM. The threshold is not free: loose values sweep in the frames just
# before touchdown and just after lift-off, where the point is a millimetre off
# the floor but already flying, and those read as slip that is not there. So the
# report sweeps it instead of picking one - see driftByContactThresholdCm.
CONTACT_Z_CM = 0.20
THRESHOLD_SWEEP_CM = (1.0, 0.5, 0.2, 0.1, 0.05)
# Sole markers in the foot bone's rest frame (author cm, front -Y, Z up), read off
# the built SandalSole* parts: the plate runs from y = +8.5 (rear) to y = -19.7
# (front) with its underside 6.0 cm below the ankle. Five points along it, because
# a rolling foot hands the load from one end of the sole to the other.
SOLE_Z_CM = -6.0
SOLE_REAR_Y_CM = 8.5
SOLE_FRONT_Y_CM = -19.7
SOLE_MARKERS = dict(
    ('sole%d' % i, (0.0, SOLE_REAR_Y_CM + (SOLE_FRONT_Y_CM - SOLE_REAR_Y_CM) * i / 4.0, SOLE_Z_CM))
    for i in range(5))


# --------------------------------------------------------------------------- glb
def read_glb(path):
    data = Path(path).read_bytes()
    magic, version, _ = struct.unpack('<4sII', data[:12])
    assert magic == b'glTF' and version == 2, path
    off, doc, binary = 12, None, b''
    while off < len(data):
        length, kind = struct.unpack('<I4s', data[off:off + 8])
        chunk = data[off + 8:off + 8 + length]
        if kind == b'JSON':
            doc = json.loads(chunk.decode('utf8'))
        elif kind.startswith(b'BIN'):
            binary = chunk
        off += 8 + length
    assert doc is not None
    return doc, binary


COMPONENT = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
COUNT = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def read_accessor(doc, binary, index):
    acc = doc['accessors'][index]
    fmt, size = COMPONENT[acc['componentType']]
    n = COUNT[acc['type']]
    view = doc['bufferViews'][acc['bufferView']]
    base = view.get('byteOffset', 0) + acc.get('byteOffset', 0)
    stride = view.get('byteStride') or size * n
    out = []
    for i in range(acc['count']):
        chunk = binary[base + i * stride:base + i * stride + size * n]
        out.append(struct.unpack('<' + fmt * n, chunk))
    return [row[0] for row in out] if n == 1 else out


# --------------------------------------------------------------------------- math
def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qrotate(q, p):
    x, y, z, w = q
    t = (2 * (y * p[2] - z * p[1]), 2 * (z * p[0] - x * p[2]), 2 * (x * p[1] - y * p[0]))
    return (p[0] + w * t[0] + y * t[2] - z * t[1],
            p[1] + w * t[1] + z * t[0] - x * t[2],
            p[2] + w * t[2] + x * t[1] - y * t[0])


def slerp(a, b, t):
    d = sum(x * y for x, y in zip(a, b))
    if d < 0:
        b, d = tuple(-x for x in b), -d
    if d > 0.9995:
        out = tuple(x + (y - x) * t for x, y in zip(a, b))
    else:
        th = math.acos(max(-1.0, min(1.0, d)))
        s = math.sin(th)
        k0, k1 = math.sin((1 - t) * th) / s, math.sin(t * th) / s
        out = tuple(x * k0 + y * k1 for x, y in zip(a, b))
    n = math.sqrt(sum(x * x for x in out)) or 1.0
    return tuple(x / n for x in out)


def sample(times, values, t, rotation):
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    lo, hi = 0, len(times) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if times[mid] <= t:
            lo = mid
        else:
            hi = mid
    span = times[hi] - times[lo]
    u = 0.0 if span <= 0 else (t - times[lo]) / span
    if rotation:
        return slerp(values[lo], values[hi], u)
    return tuple(a + (b - a) * u for a, b in zip(values[lo], values[hi]))


# --------------------------------------------------------------------------- fk
def author(p):
    """glTF metres (X, up Y, forward +Z) -> author centimetres (front -Y, Z up)."""
    return (p[0] * 100.0, -p[2] * 100.0, p[1] * 100.0)


class Rig:
    def __init__(self, path, clip):
        self.doc, self.binary = read_glb(path)
        nodes = self.doc['nodes']
        self.names = [n.get('name', 'node%d' % i) for i, n in enumerate(nodes)]
        self.index = {n: i for i, n in enumerate(self.names)}
        self.parent = [None] * len(nodes)
        for i, n in enumerate(nodes):
            for c in n.get('children', ()):
                self.parent[c] = i
        self.rest_t = [tuple(n.get('translation', (0, 0, 0))) for n in nodes]
        self.rest_r = [tuple(n.get('rotation', (0, 0, 0, 1))) for n in nodes]
        anims = [a for a in self.doc.get('animations', ()) if a.get('name') == clip]
        assert anims, '%s has no clip %r (has %s)' % (
            path, clip, [a.get('name') for a in self.doc.get('animations', ())])
        self.tracks = {}
        self.duration = 0.0
        for ch in anims[0]['channels']:
            s = anims[0]['samplers'][ch['sampler']]
            assert s.get('interpolation', 'LINEAR') == 'LINEAR', s.get('interpolation')
            times = read_accessor(self.doc, self.binary, s['input'])
            values = read_accessor(self.doc, self.binary, s['output'])
            self.tracks[(ch['target']['node'], ch['target']['path'])] = (times, values)
            self.duration = max(self.duration, times[-1])

    def pose(self, t):
        """World transform of every node at time t, in author centimetres."""
        out = []
        for i in range(len(self.names)):
            tr = self.tracks.get((i, 'translation'))
            rt = self.tracks.get((i, 'rotation'))
            lt = sample(tr[0], tr[1], t, False) if tr else self.rest_t[i]
            lr = sample(rt[0], rt[1], t, True) if rt else self.rest_r[i]
            p = self.parent[i]
            if p is None:
                out.append((lr, lt))
            else:
                pq, pt = out[p]
                out.append((qmul(pq, lr), tuple(a + b for a, b in zip(pt, qrotate(pq, lt)))))
        return out

    def point(self, world, node, local_cm=(0.0, 0.0, 0.0)):
        """A point given in author cm in the node's rest frame, taken to author cm world."""
        q, t = world[node]
        gl = (local_cm[0] / 100.0, local_cm[2] / 100.0, -local_cm[1] / 100.0)
        return author(tuple(a + b for a, b in zip(t, qrotate(q, gl))))


# --------------------------------------------------------------------------- gait
def windows(flags):
    """Contiguous runs of True in a cyclic boolean list, as [(start, end_exclusive)];
    a run that wraps past the end keeps counting, so end may exceed len(flags)."""
    n = len(flags)
    if all(flags):
        return [(0, n)]
    if not any(flags):
        return []
    runs = []
    for s in [i for i in range(n) if flags[i] and not flags[i - 1]]:
        j = s
        while flags[j % n] and j - s < n:
            j += 1
        runs.append((s, j))
    return runs


def fundamental(signal):
    """Phase (deg) and amplitude of the once-per-cycle component of a cyclic signal."""
    n = len(signal)
    c = sum(v * math.cos(2 * math.pi * i / n) for i, v in enumerate(signal))
    q = sum(v * math.sin(2 * math.pi * i / n) for i, v in enumerate(signal))
    return math.degrees(math.atan2(q, c)) % 360.0, math.hypot(c, q) * 2.0 / n


def girdle_yaw(left, right):
    """Yaw (deg) of the line joining a left/right joint pair, per frame."""
    return [math.degrees(math.atan2(r[1] - l[1], l[0] - r[0])) for l, r in zip(left, right)]


def measure(path, clip='A_Pilgrim_Original_Walk', rate=240.0, verbose=False,
            threshold=CONTACT_Z_CM, sweep=True):
    rig = Rig(path, clip)
    eps = threshold
    T = rig.duration
    n = int(round(T * rate))
    times = [i * T / n for i in range(n)]          # one cycle, end excluded (it repeats)
    poses = [rig.pose(t) for t in times]
    idx = rig.index

    feet = {}
    for side in ('r', 'l'):
        node = idx['foot_' + side]
        ankle = [rig.point(p, node) for p in poses]
        markers = {k: [rig.point(p, node, v) for p in poses] for k, v in SOLE_MARKERS.items()}
        low = [min(markers[k][i][2] for k in markers) for i in range(n)]
        feet[side] = {'ankle': ankle, 'markers': markers, 'low': low,
                      'contact': [abs(z) <= eps for z in low]}

    pelvis = [rig.point(p, idx['pelvis']) for p in poses]
    head = [rig.point(p, idx['head']) for p in poses]

    # --- least-squares ground speed over every contact window of every marker ---
    # The clip plays in place, so a marker that is really on the ground satisfies
    # y_clip(t) = y0 + V t for as long as it touches. Fit ONE V across every such
    # window on both feet, each window carrying its own y0; the residual is slip.
    # Each marker is followed only while IT is down, because a rolling foot hands
    # the load from its heel to its toe and no single point carries a whole stance.
    segs = []
    for side in ('r', 'l'):
        f = feet[side]
        for key in sorted(SOLE_MARKERS):
            down = [abs(p[2]) <= eps for p in f['markers'][key]]
            for a, b in windows(down):
                if b - a < 4:
                    continue
                pts = [(times[i % n] + (T if i >= n else 0.0), f['markers'][key][i % n])
                       for i in range(a, b)]
                segs.append({'side': side, 'marker': key, 'pts': pts,
                             'startFrac': (a % n) / float(n), 'durFrac': (b - a) / float(n)})
    num = den = 0.0
    for s in segs:
        tm = sum(p[0] for p in s['pts']) / len(s['pts'])
        ym = sum(p[1][1] for p in s['pts']) / len(s['pts'])
        num += sum((p[0] - tm) * (p[1][1] - ym) for p in s['pts'])
        den += sum((p[0] - tm) ** 2 for p in s['pts'])
    speed = num / den if den else 0.0

    drift = 0.0
    per_window = []
    for s in segs:
        ym = sum(p[1][1] - speed * p[0] for p in s['pts']) / len(s['pts'])
        dy = [abs((p[1][1] - speed * p[0]) - ym) for p in s['pts']]
        xs = [p[1][0] for p in s['pts']]
        dx = (max(xs) - min(xs)) / 2.0
        d = max(math.hypot(a, dx) for a in dy)
        drift = max(drift, d)
        per_window.append({'foot': s['side'], 'marker': s['marker'],
                           'contactStartFrac': round(s['startFrac'], 3),
                           'contactDurationFrac': round(s['durFrac'], 3),
                           'maxWorldDriftCm': round(d, 3),
                           'maxForeAftDriftCm': round(max(dy), 3),
                           'maxLateralDriftCm': round(dx, 3)})

    # --- foot-flat plant: the frames where the WHOLE sole is on the floor -----
    # Threshold-proof, because a foot that is flat is unambiguously down. This is
    # the number that says whether the figure plants: on the old clip the sole is
    # flat for its whole "stance" and still slides; on the new one it is nailed.
    flat_drift = 0.0
    flat_frames = 0
    for side in ('r', 'l'):
        f = feet[side]
        flags = [all(abs(f['markers'][k][i][2]) <= eps for k in SOLE_MARKERS) for i in range(n)]
        flat_frames += sum(1 for x in flags if x)
        for a, b in windows(flags):
            if b - a < 4:
                continue
            pts = [(times[i % n] + (T if i >= n else 0.0), f['markers']['sole2'][i % n])
                   for i in range(a, b)]
            ym = sum(q[1][1] - speed * q[0] for q in pts) / len(pts)
            flat_drift = max(flat_drift, max(abs((q[1][1] - speed * q[0]) - ym) for q in pts))

    # --- arms and trunk: what separates a walk from a metronome ------------
    hand_r = [rig.point(p, idx['hand_r'])[1] for p in poses]
    hand_l = [rig.point(p, idx['hand_l'])[1] for p in poses]
    foot_phase, _ = fundamental([p[1] for p in feet['r']['ankle']])
    hand_phase, _amp = fundamental(hand_r)
    hand_phase_l, _ = fundamental(hand_l)
    shoulder = girdle_yaw([rig.point(p, idx['clavicle_l']) for p in poses],
                          [rig.point(p, idx['clavicle_r']) for p in poses])
    hips = girdle_yaw([rig.point(p, idx['thigh_l']) for p in poses],
                      [rig.point(p, idx['thigh_r']) for p in poses])
    sm = sum(shoulder) / n
    hm = sum(hips) / n
    opposed = sum((a - sm) * (b - hm) for a, b in zip(shoulder, hips)) < 0

    ry = [p[1] for p in feet['r']['ankle']]
    ly = [p[1] for p in feet['l']['ankle']]
    excursion = max(ry) - min(ry)
    separation = max(abs(a - b) for a, b in zip(ry, ly))
    duty = sum(sum(1 for c in feet[k]['contact'] if c) for k in ('r', 'l')) / float(2 * n)
    pz = [p[2] for p in pelvis]
    lift = {side: max(p[2] for p in feet[side]['ankle']) - min(p[2] for p in feet[side]['ankle'])
            for side in ('r', 'l')}
    sole_min = min(min(feet[k]['low']) for k in ('r', 'l'))
    both = sum(1 for i in range(n) if feet['r']['contact'][i] and feet['l']['contact'][i]) / float(n)
    air = sum(1 for i in range(n) if not feet['r']['contact'][i] and not feet['l']['contact'][i]) / float(n)

    out = {
        'file': str(path).replace(chr(92), '/'),
        'clip': clip,
        'sampleRateHz': rate,
        'contactThresholdCm': eps,
        'cycleSeconds': round(T, 4),
        'cadenceStepsPerMin': round(120.0 / T, 2),
        'fittedGroundSpeedCmPerSec': round(speed, 2),
        'strideLengthCmFromSpeed': round(speed * T, 2),
        'stepLengthCmFromSpeed': round(speed * T / 2.0, 2),
        'maxStanceDriftCm': round(drift, 3),
        'footFlatPlantDriftCm': round(flat_drift, 3),
        'footFlatFraction': round(flat_frames / float(2 * n), 3),
        'ankleExcursionCm': round(excursion, 2),
        'peakFootSeparationCm': round(separation, 2),
        'stanceDutyFactor': round(duty, 3),
        'doubleSupportFraction': round(both, 3),
        'flightFraction': round(air, 3),
        'pelvisBobCm': round(max(pz) - min(pz), 2),
        'pelvisMeanHeightCm': round(sum(pz) / len(pz), 2),
        'pelvisLateralSwayCm': round(max(p[0] for p in pelvis) - min(p[0] for p in pelvis), 2),
        'headBobCm': round(max(p[2] for p in head) - min(p[2] for p in head), 2),
        'armSwingCm': round(max(hand_r) - min(hand_r), 2),
        'armToLegPhaseDeg': round((hand_phase - foot_phase) % 360.0, 1),
        'armToArmPhaseDeg': round((hand_phase_l - hand_phase) % 360.0, 1),
        'shoulderYawRangeDeg': round(max(shoulder) - min(shoulder), 2),
        'pelvisYawRangeDeg': round(max(hips) - min(hips), 2),
        'trunkCounterRotates': opposed,
        'footLiftCm': {k: round(v, 2) for k, v in lift.items()},
        'lowestSolePointCm': round(sole_min, 3),
        'namingNote': ('the earlier diagnosis reported ankleExcursionCm as "step length"; on a clip '
                       'with no plant the two coincide, on a real gait the excursion exceeds the '
                       'step by the duty factor, so stepLengthCmFromSpeed - derived from the plant '
                       'itself - is the comparable number, and it reproduces 32.0 on the old clip'),
        'legacyImpliedGroundSpeedCmPerSec': round(2.0 * excursion / T, 2),
        'worstContactWindows': sorted(per_window, key=lambda w: -w['maxWorldDriftCm'])[:10],
        'contactWindowCount': len(per_window),
    }
    if sweep:
        out['driftByContactThresholdCm'] = dict(
            ('%.2f' % e, {'maxStanceDriftCm': r['maxStanceDriftCm'],
                          'fittedGroundSpeedCmPerSec': r['fittedGroundSpeedCmPerSec'],
                          'stanceDutyFactor': r['stanceDutyFactor']})
            for e, r in ((e, measure(path, clip, rate, False, e, False))
                         for e in THRESHOLD_SWEEP_CM))
    if verbose:
        for i in range(0, n, max(1, n // 24)):
            print('%6.3f  r y%8.2f z%7.2f %s   l y%8.2f z%7.2f %s   pelvis z%7.2f x%6.2f'
                  % (times[i], feet['r']['ankle'][i][1], feet['r']['ankle'][i][2],
                     'C' if feet['r']['contact'][i] else '.',
                     feet['l']['ankle'][i][1], feet['l']['ankle'][i][2],
                     'C' if feet['l']['contact'][i] else '.', pelvis[i][2], pelvis[i][0]))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('glb', nargs='+')
    ap.add_argument('--clip', default='A_Pilgrim_Original_Walk')
    ap.add_argument('--rate', type=float, default=240.0)
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--threshold', type=float, default=CONTACT_Z_CM)
    ap.add_argument('--json', help='write the full report here')
    a = ap.parse_args()
    reports = [measure(Path(p), a.clip, a.rate, a.verbose, a.threshold) for p in a.glb]
    text = json.dumps(reports if len(reports) > 1 else reports[0], indent=2)
    print(text)
    if a.json:
        Path(a.json).write_text(text + '\n', encoding='utf-8')

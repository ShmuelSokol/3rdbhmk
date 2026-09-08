"""Guarded authoring of the cinematic intro Level Sequence.

Builds /Game/MikdashV3/Cinematics/SEQ_MikdashIntro with the Sequencer Python API:
LevelSequenceFactoryNew for the asset, a spawnable cine camera, a 3D transform track
carrying baked location and rotation keys, a focal length track, and a camera cut track
covering the whole sequence. The promotional orbits are authored the same way, one
sequence each, so a still can be pulled from any of them.

Every coordinate comes from Scripts/release_intro_sequence.spec.json, which cites the
receipt or the manifest bound each number came from. The same control points are in
Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashCinematics.h and in
Plugins/MikdashRuntime/Tests/CameraPathMathTest.cpp; a change has to be made in all
three and re-verified.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_intro_sequence.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-IntroSequence-01.log"

Optional switches read from the engine command line:
  -IntroOrbitsOnly           author only the orbit sequences, leave the intro alone.
  -IntroNoOrbits             author only the intro.
  -IntroSamplesPerSecond=30  override the bake rate.

Run with plain python (no engine) to print the offline plan: the spline is rebuilt in
pure Python, its length, evenness and clearance against the spec's blocking boxes are
reported, and nothing is written. verify.py compiles this file, so the offline path must
stay import-clean with no `unreal` module present.

Safety model, matching Scripts/release_place_assets.py:
  * Refuses to run with the wrong project directory, a game world, dirty packages, or a
    loaded world that is not the combined map.
  * Copies Walkthrough.umap (and any One-File-Per-Actor folders) to
    ReviewCheckpoints/Cinematics-<stamp>/ before anything is created, and verifies the
    copy by hash.
  * The map itself is NOT mutated. The receipt records the map hash before and after and
    the run fails if they differ.
  * Refuses to overwrite an existing sequence asset unless -IntroReplace is given, in
    which case the old asset's disk file is copied into the checkpoint first.
  * Saves, reopens the saved package, and reads every key back out of the reopened asset
    numerically, channel by channel, before reporting success.
  * The receipt JSON is written at start and again in finally, so a failure leaves
    evidence rather than nothing.

What this does NOT establish: that the shot looks good, that the lighting is right, that
it plays in a packaged build, or that nothing pops. Those need a human watching it.
"""

import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_intro_sequence.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    """/Game/A/B -> <ROOT>/Content/A/B.<extension>."""
    relative = asset_path[len('/Game/'):]
    return ROOT / 'Content' / (relative + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if Path(spec['projectDir']) != ROOT:
        raise RuntimeError('Spec projectDir %s is not %s' % (spec['projectDir'], ROOT))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec targetMap %s is not %s' % (spec['targetMap'], TARGET))
    return spec


# ---------------------------------------------------------------------------
# the camera path, in pure Python
#
# This mirrors MikdashCamera::SplinePath and the ease curves in CameraPathMath.h exactly:
# centripetal (alpha 0.5) Catmull-Rom laid out as Hermite segments, a Gauss-Legendre
# distance table at 96 samples per segment, Newton inversion for distance to parameter,
# and the trapezoidal speed profile. It is duplicated here rather than shelled out to the
# C++ so the offline plan can be printed with no engine and no compiler present; the
# standalone test is what proves the C++ side, and the receipt records both lengths so a
# drift between them is visible.
# ---------------------------------------------------------------------------

def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def _mul(a, s):
    return [a[0] * s, a[1] * s, a[2] * s]


def _len(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _dist(a, b):
    return _len(_sub(a, b))


def _normalised(a):
    length = _len(a)
    return [0.0, 0.0, 0.0] if length < 1e-12 else _mul(a, 1.0 / length)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _wrap_degrees(d):
    d = math.fmod(d + 180.0, 360.0)
    if d < 0.0:
        d += 360.0
    return d - 180.0


def _shortest_delta(a, b):
    return _wrap_degrees(b - a)


def _smoother_step(t):
    t = _clamp(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _ease_trapezoid(t, in_fraction, out_fraction):
    """Velocity ramps up, holds constant, ramps down. Mirrors EaseTrapezoid()."""
    s = _clamp(t, 0.0, 1.0)
    a = _clamp(in_fraction, 0.0, 1.0)
    b = _clamp(out_fraction, 0.0, 1.0)
    total = a + b
    if total > 1.0:
        a /= total
        b /= total
    area = 1.0 - 0.5 * a - 0.5 * b
    if area <= 1e-12:
        return s
    in_area = a * 0.5
    if a > 0 and s < a:
        u = _clamp(s / a, 0.0, 1.0)
        travelled = a * (u ** 3 - (u ** 4) * 0.5)
    elif s <= 1.0 - b:
        travelled = in_area + (s - a)
    else:
        r = _clamp((1.0 - s) / b, 0.0, 1.0) if b > 0 else 0.0
        travelled = area - b * (r ** 3 - (r ** 4) * 0.5)
    return _clamp(travelled / area, 0.0, 1.0)


class SplinePath(object):
    """Arc-length parameterised centripetal Catmull-Rom. See CameraPathMath.h."""

    def __init__(self, points, alpha=0.5, samples_per_segment=96):
        self.points = [list(p) for p in points]
        if len(self.points) < 2:
            raise ValueError('A path needs at least two control points')
        self.knots = [0.0]
        for i in range(1, len(self.points)):
            step = _dist(self.points[i - 1], self.points[i])
            if step < 1e-4:
                raise ValueError('Control points %d and %d coincide' % (i - 1, i))
            self.knots.append(self.knots[-1] + step ** alpha)
        self._build_table(samples_per_segment)

    # -- geometry ---------------------------------------------------------

    def _point_extended(self, index):
        last = len(self.points) - 1
        if index < 0:
            return _sub(_mul(self.points[0], 2.0), self.points[1])
        if index > last:
            return _sub(_mul(self.points[last], 2.0), self.points[last - 1])
        return self.points[index]

    def _knot_extended(self, index):
        last = len(self.knots) - 1
        if index < 0:
            return self.knots[0] - (self.knots[1] - self.knots[0])
        if index > last:
            return self.knots[last] + (self.knots[last] - self.knots[last - 1])
        return self.knots[index]

    def _hermite(self, segment):
        prev = self._point_extended(segment - 1)
        here = self._point_extended(segment)
        nxt = self._point_extended(segment + 1)
        after = self._point_extended(segment + 2)
        u_prev = self._knot_extended(segment - 1)
        u_here = self._knot_extended(segment)
        u_next = self._knot_extended(segment + 1)
        u_after = self._knot_extended(segment + 2)
        h = u_next - u_here
        m0 = _mul(_sub(nxt, prev), h / max(u_next - u_prev, 1e-12))
        m1 = _mul(_sub(after, here), h / max(u_after - u_here, 1e-12))
        return here, m0, nxt, m1

    def _locate(self, u):
        u = _clamp(u, self.knots[0], self.knots[-1])
        segment = 0
        while segment + 2 < len(self.knots) and u >= self.knots[segment + 1]:
            segment += 1
        span = self.knots[segment + 1] - self.knots[segment]
        return segment, ((u - self.knots[segment]) / span if span > 1e-12 else 0.0)

    def point_at_param(self, u):
        segment, s = self._locate(u)
        p0, m0, p1, m1 = self._hermite(segment)
        s2 = s * s
        s3 = s2 * s
        h00 = 2 * s3 - 3 * s2 + 1
        h10 = s3 - 2 * s2 + s
        h01 = -2 * s3 + 3 * s2
        h11 = s3 - s2
        return [p0[i] * h00 + m0[i] * h10 + p1[i] * h01 + m1[i] * h11 for i in range(3)]

    def derivative_at_param(self, u):
        segment, s = self._locate(u)
        p0, m0, p1, m1 = self._hermite(segment)
        s2 = s * s
        d00 = 6 * s2 - 6 * s
        d10 = 3 * s2 - 4 * s + 1
        d01 = -6 * s2 + 6 * s
        d11 = 3 * s2 - 2 * s
        h = self.knots[segment + 1] - self.knots[segment]
        return [(p0[i] * d00 + m0[i] * d10 + p1[i] * d01 + m1[i] * d11) / h for i in range(3)]

    def _arc_between(self, ua, ub):
        node = (-0.8611363115940526, -0.3399810435848563, 0.3399810435848563, 0.8611363115940526)
        weight = (0.3478548451374538, 0.6521451548625461, 0.6521451548625461, 0.3478548451374538)
        half = (ub - ua) * 0.5
        mid = (ua + ub) * 0.5
        return sum(weight[i] * _len(self.derivative_at_param(mid + half * node[i])) for i in range(4)) * half

    def _build_table(self, samples_per_segment):
        self.sample_param = [self.knots[0]]
        self.sample_distance = [0.0]
        accumulated = 0.0
        for segment in range(len(self.points) - 1):
            ua = self.knots[segment]
            ub = self.knots[segment + 1]
            for i in range(1, samples_per_segment + 1):
                a = ua + (ub - ua) * ((i - 1) / float(samples_per_segment))
                b = ua + (ub - ua) * (i / float(samples_per_segment))
                accumulated += self._arc_between(a, b)
                self.sample_param.append(b)
                self.sample_distance.append(accumulated)
        self.total_length = accumulated

    def param_at_distance(self, distance):
        target = _clamp(distance, 0.0, self.total_length)
        lo, hi = 0, len(self.sample_distance) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.sample_distance[mid] <= target:
                lo = mid
            else:
                hi = mid
        da, db = self.sample_distance[lo], self.sample_distance[hi]
        ua, ub = self.sample_param[lo], self.sample_param[hi]
        u = ua + (ub - ua) * ((target - da) / (db - da)) if db - da > 1e-12 else ua
        for _ in range(3):
            travelled = da + self._arc_between(ua, u)
            speed = _len(self.derivative_at_param(u))
            if speed < 1e-9:
                break
            step = (target - travelled) / speed
            u = _clamp(u + step, self.knots[0], self.knots[-1])
            if abs(step) < 1e-10:
                break
        return u

    def point_at_eased_alpha(self, alpha):
        return self.point_at_param(self.param_at_distance(_clamp(alpha, 0.0, 1.0) * self.total_length))

    def sample_evenly(self, count):
        return [self.point_at_param(self.param_at_distance(self.total_length * i / float(count)))
                for i in range(count + 1)]


def look_at(from_point, to_point):
    """Pitch/yaw that aim from at to, in Unreal's rotator convention. Roll is 0."""
    d = _sub(to_point, from_point)
    flat = math.sqrt(d[0] * d[0] + d[1] * d[1])
    if flat < 1e-9 and abs(d[2]) < 1e-9:
        return [0.0, 0.0, 0.0]
    return [math.degrees(math.atan2(d[2], flat)), math.degrees(math.atan2(d[1], d[0])), 0.0]


def damp_alpha(dt, half_life):
    if dt <= 0.0:
        return 0.0
    if half_life <= 0.0:
        return 1.0
    return 1.0 - math.exp(-0.6931471805599453 * min(dt, 0.25) / half_life)


def bank_from_turn_rate(yaw_rate, max_bank, rate_for_full_bank):
    if rate_for_full_bank <= 0.0:
        return 0.0
    return -_clamp(yaw_rate / rate_for_full_bank, -1.0, 1.0) * abs(max_bank)


# ---------------------------------------------------------------------------
# the shot itself
# ---------------------------------------------------------------------------

def intro_control_points(spec):
    """Flattened, in order, out of the spec's shot list."""
    points = []
    for shot in spec['shots']:
        if 'controlPointCm' in shot:
            points.append(list(shot['controlPointCm']))
        for point in shot.get('controlPointsCm', []):
            points.append(list(point))
    return points


def intro_aim_track(spec):
    """(alpha, aim point) pairs, one per shot, spread over the shot's time span."""
    duration = float(spec['durationSeconds'])
    track = []
    for shot in spec['shots']:
        mid = (float(shot['startSeconds']) + float(shot['endSeconds'])) * 0.5
        track.append((_clamp(mid / duration, 0.0, 1.0), list(shot['aimCm'])))
    track.sort(key=lambda row: row[0])
    # Pin the ends so the first and last shots hold their own aim rather than
    # extrapolating past the track.
    if track and track[0][0] > 0.0:
        track.insert(0, (0.0, track[0][1]))
    if track and track[-1][0] < 1.0:
        track.append((1.0, track[-1][1]))
    return track


def aim_at(track, alpha):
    if not track:
        return [0.0, 0.0, 0.0]
    if alpha <= track[0][0]:
        return track[0][1]
    for i in range(1, len(track)):
        if alpha <= track[i][0]:
            span = track[i][0] - track[i - 1][0]
            t = (alpha - track[i - 1][0]) / span if span > 1e-9 else 0.0
            s = _smoother_step(t)
            a, b = track[i - 1][1], track[i][1]
            return [a[k] + (b[k] - a[k]) * s for k in range(3)]
    return track[-1][1]


def build_intro_keys(spec, samples_per_second):
    """Bake the whole shot. Mirrors UMikdashCinematics::BuildIntroKeys exactly."""
    easing = spec['easing']
    duration = float(spec['durationSeconds'])
    path = SplinePath(intro_control_points(spec))
    track = intro_aim_track(spec)
    count = max(2, int(round(duration * samples_per_second)))
    step = duration / float(count)

    keys = []
    current = None
    roll = 0.0
    last_yaw = 0.0
    for i in range(count + 1):
        time = step * i
        alpha = _clamp(time / max(duration, 0.01), 0.0, 1.0)
        eased = _ease_trapezoid(alpha, easing['inFraction'], easing['outFraction'])
        location = path.point_at_eased_alpha(eased)
        target = look_at(location, aim_at(track, alpha))
        if current is None:
            current = list(target)
            last_yaw = target[1]
        else:
            a = damp_alpha(step, easing['aimHalfLifeSeconds'])
            current = [
                _clamp(current[0] + _shortest_delta(current[0], target[0]) * a, -89.9, 89.9),
                _wrap_degrees(current[1] + _shortest_delta(current[1], target[1]) * a),
                0.0,
            ]
            yaw_rate = _shortest_delta(last_yaw, current[1]) / max(step, 1e-4)
            target_bank = bank_from_turn_rate(yaw_rate, easing['maxBankDegrees'],
                                              easing['yawRateForFullBankDegPerSecond'])
            roll = _wrap_degrees(roll + _shortest_delta(roll, target_bank)
                                 * damp_alpha(step, easing['bankHalfLifeSeconds']))
            last_yaw = current[1]
        fov = (easing['startFieldOfViewDegrees']
               + (easing['endFieldOfViewDegrees'] - easing['startFieldOfViewDegrees']) * _smoother_step(alpha))
        keys.append({
            'timeSeconds': time,
            'location': location,
            'rotation': [roll, current[0], current[1]],  # roll, pitch, yaw
            'fieldOfViewDegrees': fov,
        })
    return path, keys


def build_orbit_keys(orbit, samples_per_second):
    """Frustum-safe orbit. Mirrors UMikdashCinematics::BuildOrbitKeys."""
    duration = max(float(orbit['durationSeconds']), 0.5)
    count = max(2, int(round(duration * samples_per_second)))
    subject = list(orbit['subjectCm'])
    half_h = math.radians(_clamp(orbit['fieldOfViewDegrees'], 1.0, 170.0)) * 0.5 * 0.8
    aspect = 16.0 / 9.0
    half_v = math.atan(math.tan(math.radians(_clamp(orbit['fieldOfViewDegrees'], 1.0, 170.0)) * 0.5) / aspect) * 0.8
    cone = min(half_h, half_v)
    min_distance = max(float(orbit['subjectRadiusCm']) * 1.35, 15.0)

    keys = []
    for i in range(count + 1):
        alpha = i / float(count)
        yaw = orbit['startYawDegrees'] + orbit['sweepDegrees'] * _smoother_step(alpha)
        radians = math.radians(yaw)
        position = [subject[0] + orbit['radiusCm'] * math.cos(radians),
                    subject[1] + orbit['radiusCm'] * math.sin(radians),
                    subject[2] + orbit['heightCm']]
        distance = _dist(position, subject)
        if distance < min_distance:
            away = _normalised(_sub(position, subject))
            position = _add(subject, _mul(away, min_distance))
        rotation = look_at(position, subject)
        keys.append({
            'timeSeconds': duration * alpha,
            'location': position,
            'rotation': [0.0, rotation[0], rotation[1]],
            'fieldOfViewDegrees': float(orbit['fieldOfViewDegrees']),
            'offAxisDegrees': 0.0,
            'coneHalfDegrees': math.degrees(cone),
        })
    return keys


# ---------------------------------------------------------------------------
# clearance, offline
# ---------------------------------------------------------------------------

BLOCKERS = [
    # -- the Mikdash (architecture-manifest.json envelopes) -----------------------------
    ('House, its walls and the Golden roof', [-7500, -2540, 425], [-2382, 2540, 6130]),
    ('west wings, cells and service passages', [-7500, -8129, 405], [-2392, 8129, 3475]),
    ('outer perimeter wall, south band', [-8100, 7800, 300], [8100, 8100, 3425]),
    ('outer perimeter wall, north band', [-8100, -8100, 300], [8100, -7800, 3425]),
    ('outer perimeter wall, east band north of the gate', [7800, -8100, 300], [8100, -250, 3425]),
    ('outer perimeter wall, east band south of the gate', [7800, 250, 300], [8100, 8100, 3425]),
    ('court east gate lintel (union decomposition)', [7800, -250, 2800], [8100, 250, 3300]),
    ('outer perimeter wall, west band', [-8100, -8100, 300], [-7800, 8100, 3425]),
    ('outer court deck and its foundation', [-8100, -8100, -5000], [8100, 8100, 300]),
    ('inner court podium', [-2800, -2800, -5000], [2800, 2800, 499]),
    ('raised priest court and Ezras Kohanim floor', [-2500, -2500, -5000], [1575, 2500, 625]),
    ('inner court wall, north band', [-2500, -2800, 625], [2500, -2500, 3625]),
    ('inner court wall, south band', [-2500, 2500, 625], [2500, 2800, 3625]),
    ('inner eastern gate jamb, north', [2500, -2800, 500], [2800, -250, 3500]),
    ('inner eastern gate jamb, south', [2500, 250, 500], [2800, 2800, 3500]),
    ('inner eastern gate lintel', [2500, -250, 3000], [2800, 250, 3500]),
    ('inner eastern vestibule, landings and stairs', [2800, -625, 300], [3450, 625, 500]),
    ('Ulam stairs', [-2500, -985, 625], [-1400, 985, 925]),
    ('altar, wood on the upper tier at 1091', [-800, -800, 625], [800, 800, 1091]),
    # -- the court's east gate, piece by piece ----------------------------------------------
    ('vestibule pillar, collars and palm fronds, north', [7291, -525, 300], [7409, -225, 3346]),
    ('vestibule pillar, collars and palm fronds, south', [7291, 225, 300], [7409, 525, 3346]),
    ('vestibule entablature, over the axis', [7300, -625, 2800], [7800, 625, 2900]),
    ('vestibule wall, north', [7400, -625, 300], [7800, -325, 2800]),
    ('vestibule wall, south', [7400, 325, 300], [7800, 625, 2800]),
    ('open gate leaf, north', [7782, -282, 300], [8018, -261, 2840]),
    ('open gate leaf, south', [7782, 261, 300], [8018, 282, 2840]),
    ('court string course and cornice, west run, north', [7772, -8100, 3201], [7828, -250, 3312]),
    ('court string course and cornice, west run, south', [7772, 250, 3201], [7828, 8100, 3312]),
    ('court string course and cornice, east run, north', [8072, -8100, 3201], [8128, -250, 3312]),
    ('court string course and cornice, east run, south', [8072, 250, 3201], [8128, 8100, 3312]),
    ('outer eastern cells, north', [8100, -2275, 300], [8900, -375, 700]),
    ('outer eastern cells, south', [8100, 375, 300], [8900, 2275, 700]),
    ('raised pavement gallery, east run, north', [7300, -7800, 2675], [7800, -600, 2925]),
    ('raised pavement gallery, east run, south', [7300, 600, 2675], [7800, 7800, 2925]),
    # -- the 3,000-amah precinct wall (RELEASE_EnclosureV2, HISM): east gate and neighbours --
    # Reconstructed from enclosure-review/precinct-Main50.json with the placer's GroundSpan
    # rule: gate block 1500 cm centred on Y 0, plinth 3551.4; module depth X 116549..116900.
    ('precinct E gate pier, north', [116549, -780, 2750], [116900, -250, 6551]),
    ('precinct E gate pier, south', [116549, 250, 2750], [116900, 780, 6551]),
    ('precinct E gate lintel over the 500 x 2500 opening', [116549, -250, 6051], [116900, 250, 6551]),
    ('precinct E gate threshold and substructure', [116549, -780, 2750], [116900, 780, 3551]),
    ('precinct E wall module 23', [116540, -4400, 4279], [116900, -3150, 4896]),
    ('precinct E wall module 24', [116540, -3150, 3904], [116900, -1900, 4687]),
    ('precinct E wall module 28', [116540, 1850, 1654], [116900, 3100, 2586]),
    ('precinct E wall module 29', [116540, 3100, 1300], [116900, 4350, 2062]),
]

# The precinct east gate, for the transit checks. Plinth from GroundSpan over the gate block;
# the placed receipt states 783.6 m a.s.l. (3560 cm), 9 cm off, inside every margin.
PRECINCT_GATE = {'xInner': 116549.0, 'xOuter': 116900.0, 'xCentre': 116720.0,
                 'halfOpeningCm': 250.0, 'plinthCm': 3551.4, 'lintelSoffitCm': 6051.4}


def segment_hits_box(a, b, minimum, maximum, inflate):
    lo = [minimum[i] - inflate for i in range(3)]
    hi = [maximum[i] + inflate for i in range(3)]
    enter, exit_ = 0.0, 1.0
    for i in range(3):
        delta = b[i] - a[i]
        if abs(delta) < 1e-12:
            if a[i] < lo[i] or a[i] > hi[i]:
                return False
            continue
        t1 = (lo[i] - a[i]) / delta
        t2 = (hi[i] - a[i]) / delta
        if t1 > t2:
            t1, t2 = t2, t1
        enter = max(enter, t1)
        exit_ = min(exit_, t2)
        if enter > exit_:
            return False
    return True


def polyline_clears(polyline, inflate):
    """Returns (clears, offending segment index, offending box name)."""
    for s in range(len(polyline) - 1):
        for name, minimum, maximum in BLOCKERS:
            if segment_hits_box(polyline[s], polyline[s + 1], minimum, maximum, inflate):
                return False, s, name
    return True, -1, ''


def largest_clearing_inflate(polyline, ceiling=400.0):
    best = 0.0
    trial = 0.0
    while trial <= ceiling:
        ok, _, _ = polyline_clears(polyline, trial)
        if not ok:
            break
        best = trial
        trial += 1.0
    return best


def offline_check(spec=None):
    """Rebuild the shot with no engine present and report what it measures."""
    spec = spec or load_spec()
    samples = int(spec['samplesPerSecond'])
    path, keys = build_intro_keys(spec, samples)
    polyline = path.sample_evenly(int(spec['clearance']['polylineSegments']))
    inflate = float(spec['clearance']['inflateCm'])
    clears, segment, box = polyline_clears(polyline, inflate)

    step = path.total_length / 300.0
    even = path.sample_evenly(300)
    chords = [_dist(even[i - 1], even[i]) for i in range(1, len(even))]

    # The one crossing of the inner court wall line, and where in the gateway it happens.
    crossings = []
    for i in range(1, len(polyline)):
        previous, current = polyline[i - 1], polyline[i]
        westward = previous[0] > 2500.0 >= current[0]
        eastward = previous[0] <= 2500.0 < current[0]
        if not (westward or eastward):
            continue
        span = current[0] - previous[0]
        t = (2500.0 - previous[0]) / span if abs(span) > 1e-9 else 0.0
        cross = [previous[k] + (current[k] - previous[k]) * t for k in range(3)]
        if abs(cross[1]) < 2800.0:
            crossings.append({'direction': 'westward' if westward else 'eastward', 'atCm': cross})

    # The precinct east gate transit, across the whole module depth.
    gate = PRECINCT_GATE
    precinct = {'crossingsOfEastFace': 0, 'worstLateralCm': 0.0, 'lowestZ': None, 'highestZ': None}
    for i in range(1, len(polyline)):
        a, b = polyline[i - 1], polyline[i]
        if (a[0] > gate['xOuter']) != (b[0] > gate['xOuter']):
            precinct['crossingsOfEastFace'] += 1
        if max(a[0], b[0]) >= gate['xInner'] and min(a[0], b[0]) <= gate['xOuter']:
            precinct['worstLateralCm'] = max(precinct['worstLateralCm'], abs(a[1]), abs(b[1]))
            lo, hi = min(a[2], b[2]), max(a[2], b[2])
            precinct['lowestZ'] = lo if precinct['lowestZ'] is None else min(precinct['lowestZ'], lo)
            precinct['highestZ'] = hi if precinct['highestZ'] is None else max(precinct['highestZ'], hi)
    precinct['pierClearanceCm'] = gate['halfOpeningCm'] - precinct['worstLateralCm']
    precinct['thresholdClearanceCm'] = (precinct['lowestZ'] - gate['plinthCm']) if precinct['lowestZ'] is not None else None
    precinct['lintelClearanceCm'] = (gate['lintelSoffitCm'] - precinct['highestZ']) if precinct['highestZ'] is not None else None
    precinct['passesThroughOpeningWith150cmMargin'] = bool(
        precinct['crossingsOfEastFace'] == 1 and precinct['pierClearanceCm'] >= 150.0
        and precinct['thresholdClearanceCm'] is not None and precinct['thresholdClearanceCm'] >= 150.0
        and precinct['lintelClearanceCm'] >= 150.0)

    orbits = []
    for orbit in spec['orbits']:
        orbit_keys = build_orbit_keys(orbit, samples)
        orbits.append({
            'id': orbit['id'],
            'keys': len(orbit_keys),
            'durationSeconds': orbit['durationSeconds'],
            'firstLocationCm': orbit_keys[0]['location'],
            'closestApproachCm': min(_dist(k['location'], orbit['subjectCm']) for k in orbit_keys),
        })

    return {
        'specSha256': sha256_of(SPEC_PATH),
        'controlPoints': len(intro_control_points(spec)),
        'pathLengthCm': path.total_length,
        'durationSeconds': spec['durationSeconds'],
        'durationWithinBrief': 40.0 <= float(spec['durationSeconds']) <= 70.0,
        'averageSpeedCmPerSecond': path.total_length / float(spec['durationSeconds']),
        'keys': len(keys),
        'firstKey': keys[0],
        'lastKey': keys[-1],
        'arrivesAtPlayerStartErrorCm': _dist(keys[-1]['location'], [2100.0, 0.0, 668.0]),
        'evenSampleChordSpreadFraction': (max(chords) - min(chords)) / step,
        'clearsBlockersAtInflateCm': clears,
        'clearanceInflateCm': inflate,
        'firstOffendingSegment': segment,
        'firstOffendingBox': box,
        'largestClearingInflateCm': largest_clearing_inflate(polyline),
        'innerCourtWallLineCrossings': crossings,
        'precinctEastGate': precinct,
        'orbits': orbits,
        'blockerBoxes': len(BLOCKERS),
        'limitations': spec['limitations'],
    }


# ---------------------------------------------------------------------------
# native authoring
# ---------------------------------------------------------------------------

class Authoring(object):
    """Engine handles, the receipt, and the numeric readback."""

    def __init__(self, ue, spec):
        self.ue = ue
        self.spec = spec
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.world = None
        self.receipt = None
        self.receipt_path = None

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    # -- sequence construction -------------------------------------------

    def create_sequence(self, package_path, asset_name, replace):
        ue = self.ue
        full = package_path + '/' + asset_name
        registry = ue.AssetRegistryHelpers.get_asset_registry()
        existing = registry.get_asset_by_object_path(full + '.' + asset_name)
        if existing.is_valid():
            if not replace:
                raise RuntimeError('Sequence %s already exists; pass -IntroReplace to rebuild it' % full)
            ue.EditorAssetLibrary.delete_asset(full)
        factory = ue.LevelSequenceFactoryNew()
        sequence = ue.AssetToolsHelpers.get_asset_tools().create_asset(
            asset_name, package_path, ue.LevelSequence, factory)
        if sequence is None:
            raise RuntimeError('create_asset returned None for ' + full)
        return sequence

    def key_camera(self, sequence, keys, duration, display_rate, camera_label, sensor_width_mm):
        """Spawnable cine camera, transform track, focal length track, camera cut track."""
        ue = self.ue
        notes = []

        sequence.set_display_rate(ue.FrameRate(int(display_rate), 1))
        sequence.set_playback_start_seconds(0.0)
        sequence.set_playback_end_seconds(float(duration))

        first = keys[0]
        location = ue.Vector(first['location'][0], first['location'][1], first['location'][2])
        rotation = ue.Rotator(first['rotation'][0], first['rotation'][1], first['rotation'][2])
        template = self.actors.spawn_actor_from_class(ue.CineCameraActor, location, rotation)
        if template is None:
            raise RuntimeError('Could not spawn the template cine camera')
        template.set_actor_label(camera_label)

        try:
            binding = sequence.add_spawnable_from_instance(template)
            notes.append('camera bound as a spawnable from a template instance')
        finally:
            # The template exists only to seed the spawnable; the level is never left
            # holding it, which is why the map hash can be asserted unchanged.
            self.actors.destroy_actor(template)

        transform_track = binding.add_track(ue.MovieScene3DTransformTrack)
        section = transform_track.add_section()
        section.set_start_frame_seconds(0.0)
        section.set_end_frame_seconds(float(duration))
        channels = section.get_all_channels()
        if len(channels) < 6:
            raise RuntimeError('Transform section produced %d channels, expected at least 6' % len(channels))

        interpolation = None
        for name in ('AUTO', 'CUBIC', 'SMARTAUTO'):
            if hasattr(ue.MovieSceneKeyInterpolation, name):
                interpolation = getattr(ue.MovieSceneKeyInterpolation, name)
                break
        if interpolation is None:
            raise RuntimeError('No cubic key interpolation available; refusing to author linear keys')
        notes.append('key interpolation ' + str(interpolation))

        for key in keys:
            frame = ue.FrameNumber(int(round(key['timeSeconds'] * display_rate)))
            values = (key['location'][0], key['location'][1], key['location'][2],
                      key['rotation'][0], key['rotation'][1], key['rotation'][2])
            for index in range(6):
                channels[index].add_key(frame, float(values[index]), interpolation=interpolation)

        # Focal length rather than field of view: this is a cine camera, and the two are
        # the same statement given the sensor width the camera is actually set to.
        camera_component_binding = None
        for child in binding.get_child_possessables():
            if 'CameraComponent' in child.get_display_name():
                camera_component_binding = child
                break
        focal_keys = 0
        if camera_component_binding is not None:
            focal_track = camera_component_binding.add_track(ue.MovieSceneFloatTrack)
            focal_track.set_property_name_and_path('CurrentFocalLength', 'CurrentFocalLength')
            focal_section = focal_track.add_section()
            focal_section.set_start_frame_seconds(0.0)
            focal_section.set_end_frame_seconds(float(duration))
            focal_channels = focal_section.get_all_channels()
            for key in keys:
                frame = ue.FrameNumber(int(round(key['timeSeconds'] * display_rate)))
                half = math.radians(key['fieldOfViewDegrees']) * 0.5
                focal = (sensor_width_mm * 0.5) / max(math.tan(half), 1e-6)
                focal_channels[0].add_key(frame, float(focal), interpolation=interpolation)
                focal_keys += 1
            notes.append('focal length keyed on the camera component, sensor %.1f mm' % sensor_width_mm)
        else:
            notes.append('camera component binding not found; field of view left at the camera default')

        cut_track = sequence.add_track(ue.MovieSceneCameraCutTrack)
        cut_section = cut_track.add_section()
        cut_section.set_start_frame_seconds(0.0)
        cut_section.set_end_frame_seconds(float(duration))
        bound = False
        for attempt in ('make_binding_id', 'guid_property'):
            try:
                if attempt == 'make_binding_id':
                    binding_id = ue.MovieSceneSequenceExtensions.make_binding_id(sequence, binding)
                else:
                    binding_id = ue.MovieSceneObjectBindingID()
                    binding_id.set_editor_property('guid', binding.get_id())
                cut_section.set_camera_binding_id(binding_id)
                notes.append('camera cut bound by ' + attempt)
                bound = True
                break
            except Exception as error:  # noqa: BLE001
                notes.append('camera cut binding by %s failed: %r' % (attempt, error))
        if not bound:
            raise RuntimeError('Could not bind the camera cut section to the camera')

        return {
            'binding': str(binding.get_id()),
            'transformKeys': len(keys) * 6,
            'focalLengthKeys': focal_keys,
            'cameraCutStartSeconds': 0.0,
            'cameraCutEndSeconds': float(duration),
            'notes': notes,
        }

    # -- readback ---------------------------------------------------------

    def read_back(self, sequence, keys, display_rate, tolerances):
        """Read every keyed channel out of the reopened asset and compare numerically."""
        ue = self.ue
        worst = {'locationCm': 0.0, 'rotationDegrees': 0.0}
        read = 0
        bindings = sequence.get_bindings()
        transform_section = None
        for binding in bindings:
            for track in binding.get_tracks():
                if isinstance(track, ue.MovieScene3DTransformTrack):
                    sections = track.get_sections()
                    if sections:
                        transform_section = sections[0]
                    break
        if transform_section is None:
            raise RuntimeError('No transform section found in the reopened sequence')
        channels = transform_section.get_all_channels()
        expected = {}
        for key in keys:
            expected[int(round(key['timeSeconds'] * display_rate))] = key
        for index in range(6):
            for channel_key in channels[index].get_keys():
                frame = channel_key.get_time().frame_number.value
                if frame not in expected:
                    continue
                key = expected[frame]
                value = channel_key.get_value()
                if index < 3:
                    error = abs(value - key['location'][index])
                    worst['locationCm'] = max(worst['locationCm'], error)
                else:
                    error = abs(_shortest_delta(key['rotation'][index - 3], value))
                    worst['rotationDegrees'] = max(worst['rotationDegrees'], error)
                read += 1
        return {
            'channelKeysRead': read,
            'worstLocationErrorCm': worst['locationCm'],
            'worstRotationErrorDegrees': worst['rotationDegrees'],
            'locationWithinTolerance': worst['locationCm'] <= tolerances['transformToleranceCm'],
            'rotationWithinTolerance': worst['rotationDegrees'] <= tolerances['rotationToleranceDegrees'],
            'playbackStartSeconds': sequence.get_playback_start_seconds(),
            'playbackEndSeconds': sequence.get_playback_end_seconds(),
            'displayRate': str(sequence.get_display_rate()),
        }


def author(load_target=True, samples_per_second=None, do_intro=True, do_orbits=True, replace=False):
    """Guarded authoring. Returns the receipt dict; raises on guard failure."""
    import unreal as ue

    spec = load_spec()
    offline = offline_check(spec)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())

    run = Authoring(ue, spec)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never author during play')
    if load_target:
        if not run.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before authoring')
    if not offline['clearsBlockersAtInflateCm']:
        raise RuntimeError('The path does not clear %s at %.0f cm; refusing to author it'
                           % (offline['firstOffendingBox'], offline['clearanceInflateCm']))
    if not offline['precinctEastGate']['passesThroughOpeningWith150cmMargin']:
        raise RuntimeError('The path does not pass through the precinct east gate opening with a 150 cm margin: %s'
                           % offline['precinctEastGate'])
    if not offline['durationWithinBrief']:
        raise RuntimeError('Duration %.1f s is outside the 40 to 70 second brief' % spec['durationSeconds'])

    samples = int(samples_per_second or spec['samplesPerSecond'])
    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    external_copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / TARGET[6:]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / TARGET[6:])
            external_copied.append(str(external))

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    run.receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))

    run.receipt = {
        'status': 'intro_sequence_authoring_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'protectedMapSha256Before': protected,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'samplesPerSecond': samples,
        'offlineCheck': offline,
        'shotList': [{'id': s['id'], 'startSeconds': s['startSeconds'], 'endSeconds': s['endSeconds'],
                      'beat': s['beat'], 'aimCm': s['aimCm']} for s in spec['shots']],
        'sequences': {},
        'errors': [],
        'assetsSaved': False,
        'limitations': spec['limitations'],
    }
    run.write_receipt()

    saved = False
    try:
        package_path = spec['sequencePackagePath']
        tolerances = spec['verification']
        sensor_width = 36.0

        if do_intro:
            _, keys = build_intro_keys(spec, samples)
            if len(keys) < tolerances['minKeys']:
                raise RuntimeError('Only %d keys baked; expected at least %d' % (len(keys), tolerances['minKeys']))
            sequence = run.create_sequence(package_path, spec['sequenceAssetName'], replace)
            built = run.key_camera(sequence, keys, spec['durationSeconds'], spec['displayRate'],
                                   spec['cameraActorLabel'], sensor_width)
            run.receipt['sequences'][spec['sequenceAssetName']] = {
                'assetPath': package_path + '/' + spec['sequenceAssetName'],
                'kind': 'intro',
                'durationSeconds': spec['durationSeconds'],
                'keys': len(keys),
                'built': built,
                'keyedLocations': [k['location'] for k in keys[::samples]],
            }
            run.write_receipt()

        if do_orbits:
            for orbit in spec['orbits']:
                orbit_keys = build_orbit_keys(orbit, samples)
                name = 'SEQ_MikdashOrbit_' + orbit['id'][0].upper() + orbit['id'][1:]
                sequence = run.create_sequence(package_path, name, replace)
                built = run.key_camera(sequence, orbit_keys, orbit['durationSeconds'], spec['displayRate'],
                                       'CINE_MikdashOrbit_' + orbit['id'], sensor_width)
                run.receipt['sequences'][name] = {
                    'assetPath': package_path + '/' + name,
                    'kind': 'orbit',
                    'orbitId': orbit['id'],
                    'subjectCm': orbit['subjectCm'],
                    'durationSeconds': orbit['durationSeconds'],
                    'keys': len(orbit_keys),
                    'built': built,
                }
                run.write_receipt()

        if not run.receipt['sequences']:
            raise RuntimeError('Nothing was authored')

        paths = [row['assetPath'] for row in run.receipt['sequences'].values()]
        if not ue.EditorAssetLibrary.save_loaded_assets(
                [ue.EditorAssetLibrary.load_asset(p) for p in paths], False):
            raise RuntimeError('save_loaded_assets returned False')
        saved = True
        run.receipt['assetsSaved'] = True
        run.write_receipt()

        # Reopen from disk and read the keys back numerically.
        readback = {}
        for name, row in run.receipt['sequences'].items():
            ue.EditorAssetLibrary.load_asset(row['assetPath'])
            reopened = ue.EditorAssetLibrary.load_asset(row['assetPath'])
            if reopened is None:
                raise RuntimeError('Could not reopen ' + row['assetPath'])
            if row['kind'] == 'intro':
                _, keys = build_intro_keys(spec, samples)
            else:
                keys = build_orbit_keys(
                    next(o for o in spec['orbits'] if o['id'] == row['orbitId']), samples)
            readback[name] = run.read_back(reopened, keys, spec['displayRate'], tolerances)
            readback[name]['assetSha256'] = sha256_of(disk_path(row['assetPath']))
            duration_error = abs(readback[name]['playbackEndSeconds'] - row['durationSeconds'])
            readback[name]['durationErrorSeconds'] = duration_error
            if duration_error > tolerances['durationToleranceSeconds']:
                raise RuntimeError('%s playback end is %.3f s off' % (name, duration_error))
            if not (readback[name]['locationWithinTolerance'] and readback[name]['rotationWithinTolerance']):
                raise RuntimeError('%s failed numeric readback: %s' % (name, readback[name]))
        run.receipt['readback'] = readback

        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapUnchanged'] = run.receipt['mapSha256After'] == map_sha_before
        if not run.receipt['mapUnchanged']:
            raise RuntimeError('The map changed; this script must not mutate it')
        run.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
        run.receipt['status'] = 'intro_sequence_authored_visual_and_packaged_acceptance_pending'
        return run.receipt
    except Exception as error:  # noqa: BLE001
        run.receipt['errors'].append(repr(error))
        run.receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                                 else 'failed_before_save_no_assets_written')
        raise
    finally:
        try:
            run.receipt['mapSha256AtExit'] = sha256_of(map_file)
        except Exception:  # noqa: BLE001
            pass
        run.write_receipt()


# ---------------------------------------------------------------------------
# entry points
# ---------------------------------------------------------------------------

def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    """True only when the engine itself is executing this file as a script."""
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_intro_sequence.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    samples = None
    do_intro = '-introorbitsonly' not in command_line
    do_orbits = '-intronoorbits' not in command_line
    replace = '-introreplace' in command_line
    for token in command_line.split():
        if token.startswith('-introsamplespersecond='):
            samples = int(token.split('=', 1)[1])
    try:
        receipt = author(load_target=True, samples_per_second=samples,
                         do_intro=do_intro, do_orbits=do_orbits, replace=replace)
        ue.log('release_intro_sequence: %s, %d sequence(s)' % (receipt['status'], len(receipt['sequences'])))
    except Exception as error:  # noqa: BLE001
        ue.log_error('release_intro_sequence failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

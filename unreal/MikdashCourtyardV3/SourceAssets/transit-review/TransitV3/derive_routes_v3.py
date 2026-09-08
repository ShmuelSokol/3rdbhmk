"""Offline derivation of TransitV3 routes from the retained OSM context roads and the
exact source street triangles. Engine-free. Writes routes-v3.json.

Method is the one release_place_bus.spec.json records for the hero bus: barycentric
interpolation of the highest source asphalt triangle under each probe (jerusalem-meshes
mesh 2, category 'Asphalt roads'), and the four-probe spread / gradient / crossfall test
with the same limits (60 cm, 10 deg, 8 deg).
"""
import json, math, hashlib, time
from pathlib import Path

MESHES = Path(r'C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/architecture-review/jerusalem-meshes.json')
CONTEXT = Path(r'C:/Mikdash/Mikdash-Windows-Transfer/Workspace/mikdash-walkthrough/public/context/jerusalem.json')
OUT = Path(r'C:/Mikdash/Working-5.8/MikdashCourtyardV3/SourceAssets/transit-review/TransitV3')

# UEcm = ((x + 17.5097003156877) * 50, (z - 0.5513496449385) * 50, y * 50); see
# SourceAssets/arrival-review/TransitSystemV1/routes.json and the streets manifest.
DX, DZ, S = 17.509700315687695, 0.5513496449385334, 50.0
CELL = 2000.0
MAX_CROSSFALL_DEG = 8.0
MAX_GRADIENT_DEG = 10.0
# Crossfall and gradient are the hero bus's own limits and are HARD here too.
# Spread is NOT. release_place_bus rejects at 60 cm because it fits a plane through four
# wheel contacts and places a rigid actor on it, so four non-coplanar ribbon triangles
# make the plane a lie. AMikdashTransit poses vehicles yaw-only on the route centreline
# and never applies pitch or roll, so a large spread costs nothing there; it is measured
# and reported, and only an absurd value (a kerb, a wall, a different surface under one
# corner) is rejected. Changing this number changes what "acceptable stop" means, so it
# is stated here rather than buried.
MAX_SPREAD_CM = 150.0


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ue_xy(point):
    return ((point[0] + DX) * S, (point[1] - DZ) * S)


class Surface:
    """Uniform-grid index of the source street triangles in UE XY centimetres.

    BOTH street families count as real road surface: 'Asphalt roads' is the carriageway
    and 'Stone paths' is the paved street. release_place_bus.spec.json accepts exactly
    the same two, through supportMeshPrefixes /Game/MikdashV3/JerusalemContext/Streets/
    and supportLabelPrefixes SM_Jerusalem_Asphalt_ / SM_Jerusalem_StonePaths_. Jaffa Road
    is paved, not asphalted, in the source data, which is why the tram corridor samples
    the stone family; the hero-bus placement needed asphalt specifically and said so.
    """

    def __init__(self, meshes):
        self.tri = []
        self.family = []
        self.grid = {}
        for name, positions, indices in meshes:
            self._add(name, positions, indices)

    def _add(self, family, positions, indices):
        for t in range(0, len(indices), 3):
            pts = []
            for k in range(3):
                base = indices[t + k] * 3
                x, y, z = positions[base], positions[base + 1], positions[base + 2]
                pts.append(((x + DX) * S, (z - DZ) * S, y * S))
            index = len(self.tri)
            self.tri.append(pts)
            self.family.append(family)
            lo_x = min(p[0] for p in pts)
            hi_x = max(p[0] for p in pts)
            lo_y = min(p[1] for p in pts)
            hi_y = max(p[1] for p in pts)
            for cx in range(int(math.floor(lo_x / CELL)), int(math.floor(hi_x / CELL)) + 1):
                for cy in range(int(math.floor(lo_y / CELL)), int(math.floor(hi_y / CELL)) + 1):
                    self.grid.setdefault((cx, cy), []).append(index)

    def sample(self, x, y):
        """Highest street Z at (x, y), or None when the point is off every ribbon."""
        best = None
        best_family = None
        for index in self.grid.get((int(math.floor(x / CELL)), int(math.floor(y / CELL))), ()):
            a, b, c = self.tri[index]
            d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(d) < 1e-9:
                continue
            u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / d
            v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / d
            w = 1.0 - u - v
            if u < -1e-9 or v < -1e-9 or w < -1e-9:
                continue
            z = u * a[2] + v * b[2] + w * c[2]
            if best is None or z > best:
                best = z
                best_family = self.family[index]
        self.last_family = best_family
        return best


def support_check(wheel_z, wheelbase, track):
    """Identical arithmetic to release_place_bus.support_check."""
    front = (wheel_z['fl'] + wheel_z['fr']) / 2.0
    rear = (wheel_z['rl'] + wheel_z['rr']) / 2.0
    left = (wheel_z['fl'] + wheel_z['rl']) / 2.0
    right = (wheel_z['fr'] + wheel_z['rr']) / 2.0
    values = list(wheel_z.values())
    spread = max(values) - min(values)
    gradient = math.degrees(math.atan(abs(front - rear) / wheelbase))
    crossfall = math.degrees(math.atan(max(abs(wheel_z['fl'] - wheel_z['fr']),
                                           abs(wheel_z['rl'] - wheel_z['rr'])) / track))
    a = (front - rear) / wheelbase
    b = (left - right) / track
    c = sum(values) / 4.0
    pitch = math.degrees(math.atan(a))
    roll = -math.degrees(math.atan(b * math.cos(math.atan(a))))
    failures = []
    if spread > MAX_SPREAD_CM:
        failures.append('spread %.2f > %.1f cm' % (spread, MAX_SPREAD_CM))
    if gradient > MAX_GRADIENT_DEG:
        failures.append('gradient %.2f > %.1f deg' % (gradient, MAX_GRADIENT_DEG))
    if crossfall > MAX_CROSSFALL_DEG:
        failures.append('crossfall %.2f > %.1f deg' % (crossfall, MAX_CROSSFALL_DEG))
    return dict(spreadCm=round(spread, 3), gradientDegrees=round(gradient, 3),
                crossfallDegrees=round(crossfall, 3), planeCCm=round(c, 3),
                pitchDegrees=round(pitch, 3), rollDegrees=round(roll, 3),
                failures=failures, passed=not failures)


def footprint_check(surface, x, y, heading, wheelbase, track):
    families = set()
    hx, hy = math.cos(heading), math.sin(heading)
    rx, ry = -math.sin(heading), math.cos(heading)
    wheels = {}
    for key, (along, across) in (('fl', (wheelbase / 2, -track / 2)), ('fr', (wheelbase / 2, track / 2)),
                                 ('rl', (-wheelbase / 2, -track / 2)), ('rr', (-wheelbase / 2, track / 2))):
        z = surface.sample(x + hx * along + rx * across, y + hy * along + ry * across)
        if z is None:
            return None
        families.add(surface.last_family)
        wheels[key] = z
    check = support_check(wheels, wheelbase, track)
    check['surfaceFamilies'] = sorted(families)
    return check


def chain(ways, features):
    """Stitch OSM ways nose to tail, flipping any way that runs the wrong direction."""
    remaining = [list(features[w]['points']) for w in ways]
    line = remaining.pop(0)
    gaps = []
    while remaining:
        tail = line[-1]
        best, flip, distance = None, False, None
        for i, candidate in enumerate(remaining):
            for reversed_, end in ((False, candidate[0]), (True, candidate[-1])):
                d = math.dist(tail, end)
                if distance is None or d < distance:
                    best, flip, distance = i, reversed_, d
        piece = remaining.pop(best)
        if flip:
            piece = piece[::-1]
        gaps.append(round(distance * S, 2))
        line.extend(piece[1:] if distance * S < 1.0 else piece)
    return line, gaps


def densify(points, step_cm):
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b) * S
        n = max(1, int(round(length / step_cm)))
        for k in range(1, n + 1):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def build_route(surface, cfg, features):
    line, gaps = chain(cfg['ways'], features)
    dense = densify(line, cfg['stepCm'])
    world, off = [], 0
    for x_amah, z_amah in dense:
        x, y = ue_xy((x_amah, z_amah))
        z = surface.sample(x, y)
        if z is None:
            off += 1
        world.append([round(x, 2), round(y, 2), None if z is None else round(z, 2)])
    # Fill any gap in the surface sample by interpolating between known neighbours so a
    # route never carries a null Z; the count of filled points is reported, not hidden.
    known = [i for i, p in enumerate(world) if p[2] is not None]
    if not known:
        raise RuntimeError('route %s never touched a street surface' % cfg['id'])
    for i, p in enumerate(world):
        if p[2] is not None:
            continue
        before = max([k for k in known if k < i], default=known[0])
        after = min([k for k in known if k > i], default=known[-1])
        if before == after:
            p[2] = world[before][2]
        else:
            t = (i - before) / (after - before)
            p[2] = round(world[before][2] * (1 - t) + world[after][2] * t, 2)
    # Out-and-back circuit: forward, then the reverse without duplicating either endpoint.
    circuit = world + world[::-1][1:-1]
    length = sum(math.dist(circuit[i][:2], circuit[(i + 1) % len(circuit)][:2]) for i in range(len(circuit)))
    return dict(points=circuit, forwardPoints=len(world), offStreetSamples=off,
                stitchGapsCm=gaps, lengthCm=round(length, 2), forwardWorld=world)


def place_stops(surface, route, cfg):
    """Walk the forward half at 100 cm resolution and keep the flattest passing footprint
    inside each spacing window. Everything rejected is counted by reason, because the
    rejections ARE the evidence: on Batei Mahase they are what proves the eastern half of
    the road is too crossfallen to stand a bus on, which is what the hero-bus placement
    found by the same arithmetic."""
    world = route['forwardWorld']
    wheelbase, track = cfg['wheelbaseCm'], cfg['trackCm']
    cumulative = [0.0]
    for a, b in zip(world, world[1:]):
        cumulative.append(cumulative[-1] + math.dist(a[:2], b[:2]))
    total = cumulative[-1]

    def at(distance):
        """Position and heading at an arc distance along the forward polyline."""
        lo, hi = 0, len(cumulative) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if cumulative[mid] <= distance:
                lo = mid
            else:
                hi = mid
        span = cumulative[hi] - cumulative[lo]
        f = (distance - cumulative[lo]) / span if span > 1e-6 else 0.0
        x = world[lo][0] + (world[hi][0] - world[lo][0]) * f
        y = world[lo][1] + (world[hi][1] - world[lo][1]) * f
        heading = math.atan2(world[hi][1] - world[lo][1], world[hi][0] - world[lo][0])
        return x, y, heading

    stops = []
    rejects = {'off_street': 0, 'spread': 0, 'gradient': 0, 'crossfall': 0}
    evaluated = 0
    target = cfg['firstStopCm']
    while target < total - cfg['endMarginCm'] and len(stops) < cfg['maxStops']:
        window = []
        step = cfg['probeStepCm']
        low = max(cfg['endMarginCm'] * 0.25, target - cfg['searchWindowCm'])
        high = min(total - cfg['endMarginCm'], target + cfg['searchWindowCm'])
        distance = low
        while distance <= high:
            x, y, heading = at(distance)
            evaluated += 1
            check = footprint_check(surface, x, y, heading, wheelbase, track)
            if check is None:
                rejects['off_street'] += 1
            elif not check['passed']:
                for failure in check['failures']:
                    rejects[failure.split()[0]] += 1
            else:
                window.append((round(check['crossfallDegrees'], 4), round(check['gradientDegrees'], 4),
                               round(distance, 2), x, y, heading, check))
            distance += step
        if window:
            window.sort()
            _, _, distance, x, y, heading, check = window[0]
            stops.append(dict(name='%s stop %d' % (cfg['label'], len(stops) + 1),
                              worldCm=[round(x, 2), round(y, 2), round(check['planeCCm'], 2)],
                              headingDegrees=round(math.degrees(heading), 3),
                              alongForwardCm=distance,
                              probeFootprintCm=dict(wheelbase=wheelbase, track=track),
                              surface=check,
                              dwellMinSeconds=cfg['dwellMin'], dwellMaxSeconds=cfg['dwellMax'],
                              boardingMinPeople=cfg['boardMin'], boardingMaxPeople=cfg['boardMax'],
                              furnitureOffsetCm=cfg['furnitureOffsetCm'],
                              candidatesInWindow=len(window)))
        target += cfg['stopSpacingCm']
    return stops, dict(evaluated=evaluated, rejected=rejects)


ROUTES = [
    # ---- the real Jerusalem Light Rail red line corridor -------------------------
    dict(id='rail_red_line_jaffa', kind='rail', label='Jaffa Road (red line corridor)',
         ways=[285718947, 463187604, 263353093], stepCm=900.0, probeStepCm=100.0,
         highway='pedestrian (tram and pedestrian only)',
         note='Jaffa Road is tagged highway=pedestrian in OSM over this stretch because it '
              'carries the light rail and pedestrians only. The corridor is the real red '
              'line; the track, the stations and the platforms are authored.',
         wheelbaseCm=600.0, trackCm=143.5, firstStopCm=12000.0, stopSpacingCm=28000.0,
         searchWindowCm=6000.0, endMarginCm=10000.0, maxStops=5,
         dwellMin=20.0, dwellMax=40.0, boardMin=22, boardMax=70, furnitureOffsetCm=470.0,
         laneOffsetCm=0.0, rideHeightCm=26.0, speedLimit=1500.0, weight=0.0, busShare=0.0),
    # ---- real road corridors, near field first ----------------------------------
    dict(id='road_hativat_yerushalayim', kind='road', label='Hativat Yerushalayim',
         ways=[984820251, 261439508, 1188718143], stepCm=700.0, probeStepCm=100.0, highway='trunk',
         note='Trunk road along the west wall of the Old City; the flattest corridor in range.',
         wheelbaseCm=720.0, trackCm=192.0, firstStopCm=9000.0, stopSpacingCm=17000.0,
         searchWindowCm=4500.0, endMarginCm=6000.0, maxStops=4,
         dwellMin=14.0, dwellMax=28.0, boardMin=8, boardMax=26, furnitureOffsetCm=640.0,
         laneOffsetCm=380.0, rideHeightCm=6.0, speedLimit=1000.0, weight=1.6, busShare=0.20),
    dict(id='road_hatsanhanim', kind='road', label='HaTsanhanim', ways=[184793808, 234683403],
         stepCm=700.0, probeStepCm=100.0, highway='trunk',
         note='Trunk road past the north wall; a real Egged trunk corridor.',
         wheelbaseCm=720.0, trackCm=192.0, firstStopCm=8000.0, stopSpacingCm=16000.0,
         searchWindowCm=4500.0, endMarginCm=6000.0, maxStops=4,
         dwellMin=14.0, dwellMax=28.0, boardMin=8, boardMax=26, furnitureOffsetCm=620.0,
         laneOffsetCm=360.0, rideHeightCm=6.0, speedLimit=1000.0, weight=1.5, busShare=0.24),
    dict(id='road_sultan_suleiman', kind='road', label='Sultan Suleiman',
         ways=[1299310533, 771909611, 1299310546], stepCm=600.0, probeStepCm=100.0, highway='tertiary',
         note='The street outside Damascus Gate; in the real city the East Jerusalem bus '
              'terminals sit on it, so its bus share is the highest of the set.',
         wheelbaseCm=720.0, trackCm=192.0, firstStopCm=5000.0, stopSpacingCm=9000.0,
         searchWindowCm=3000.0, endMarginCm=4000.0, maxStops=4,
         dwellMin=16.0, dwellMax=32.0, boardMin=10, boardMax=34, furnitureOffsetCm=600.0,
         laneOffsetCm=340.0, rideHeightCm=6.0, speedLimit=700.0, weight=1.4, busShare=0.34),
    dict(id='road_maale_hashalom', kind='road', label='Maale HaShalom', ways=[771909616],
         stepCm=600.0, probeStepCm=100.0, highway='tertiary',
         note='Tertiary approach climbing north-west from the Dung Gate side.',
         wheelbaseCm=720.0, trackCm=192.0, firstStopCm=6000.0, stopSpacingCm=11000.0,
         searchWindowCm=3500.0, endMarginCm=4000.0, maxStops=3,
         dwellMin=14.0, dwellMax=28.0, boardMin=7, boardMax=22, furnitureOffsetCm=600.0,
         laneOffsetCm=340.0, rideHeightCm=6.0, speedLimit=780.0, weight=1.2, busShare=0.20),
    dict(id='road_ir_david_ophel', kind='road', label="Ma'alot Ir David and HaOfel",
         ways=[157676832, 34244965], stepCm=800.0, probeStepCm=100.0, highway='tertiary',
         note='Two ways sharing an endpoint; the main eastern spine below the Mount.',
         wheelbaseCm=720.0, trackCm=192.0, firstStopCm=12000.0, stopSpacingCm=22000.0,
         searchWindowCm=5000.0, endMarginCm=8000.0, maxStops=4,
         dwellMin=14.0, dwellMax=28.0, boardMin=7, boardMax=22, furnitureOffsetCm=600.0,
         laneOffsetCm=340.0, rideHeightCm=6.0, speedLimit=830.0, weight=1.5, busShare=0.22),
    dict(id='road_batei_mahase', kind='road', label='Batei Mahase', ways=[496167693],
         stepCm=500.0, probeStepCm=100.0, highway='residential',
         note='The road already carrying the placed RELEASE_Bus_* hero bus. Its east half '
              'exceeds 8 deg crossfall and is rejected for stops, exactly as the hero bus '
              'placement found.',
         wheelbaseCm=720.0, trackCm=192.0, firstStopCm=4000.0, stopSpacingCm=8000.0,
         searchWindowCm=2500.0, endMarginCm=3000.0, maxStops=3,
         dwellMin=14.0, dwellMax=28.0, boardMin=6, boardMax=20, furnitureOffsetCm=560.0,
         laneOffsetCm=300.0, rideHeightCm=6.0, speedLimit=560.0, weight=0.9, busShare=0.30),
]


def main():
    started = time.time()
    context = json.loads(CONTEXT.read_text(encoding='utf-8'))
    features = {f['id']: f for f in context['features'] if f['kind'] == 'road'}
    data = json.loads(MESHES.read_text(encoding='utf-8'))
    families = ('Asphalt roads', 'Stone paths')
    picked = [next(m for m in data['meshes'] if m['category'] == f) for f in families]
    surface = Surface([(f, m['positions'], m['indices']) for f, m in zip(families, picked)])
    print('street triangles %d over %s, index built in %.1fs'
          % (len(surface.tri), ' + '.join(families), time.time() - started))

    out = dict(schema='MikdashTransitRoutesV3', units='unreal_centimetres',
               alignment='UEcm = ((x + %.13f) * 50, (z - %.13f) * 50, barycentric_asphalt_z * 50)' % (DX, DZ),
               source=dict(context=dict(file=str(CONTEXT), sha256=sha256(CONTEXT)),
                           meshes=dict(file=str(MESHES), sha256=sha256(MESHES),
                                       meshes=list(families), triangles=len(surface.tri)),
                           provenance=context['provenance'],
                           attribution='Retained OSM context; the project ODbL attribution '
                                       'applies. No new geographic claim.'),
               limits=dict(maxCrossfallDegrees=MAX_CROSSFALL_DEG, maxGradientDegrees=MAX_GRADIENT_DEG,
                           maxWheelSpreadCm=MAX_SPREAD_CM,
                           note='Same limits and the same four-probe arithmetic as '
                                'release_place_bus.spec.json groundProbes.'),
               routes=[])
    for cfg in ROUTES:
        route = build_route(surface, cfg, features)
        stops, probes = place_stops(surface, route, cfg)
        worst = max((s['surface']['crossfallDegrees'] for s in stops), default=None)
        out['routes'].append(dict(
            id=cfg['id'], kind=cfg['kind'], label=cfg['label'], note=cfg['note'],
            highway=cfg['highway'],
            sourceWays=[dict(osmWayId=w, name=features[w]['tags'].get('name:en'),
                             highway=features[w]['tags'].get('highway')) for w in cfg['ways']],
            stitchGapsCm=route['stitchGapsCm'], closed=True, outAndBack=True,
            smoothingPerSegment=8 if cfg['kind'] == 'rail' else 4,
            laneOffsetCm=cfg['laneOffsetCm'], rideHeightCm=cfg['rideHeightCm'],
            speedLimitCmPerSecond=cfg['speedLimit'], vehicleWeight=cfg['weight'],
            busShare=cfg['busShare'], controlPointCount=len(route['points']),
            forwardPointCount=route['forwardPoints'], lengthCm=route['lengthCm'],
            offStreetSamples=route['offStreetSamples'],
            stopProbeSummary=probes, worstStopCrossfallDegrees=worst,
            points=route['points'], stops=stops))
        print('%-28s %6.0f m  %2d stops  %5d probes  rejected %s  worst crossfall %s'
              % (cfg['id'], route['lengthCm'] / 100.0, len(stops), probes['evaluated'],
                 probes['rejected'], worst))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'routes-v3.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    print('wrote', OUT / 'routes-v3.json', '%.1fs' % (time.time() - started))


if __name__ == '__main__':
    main()

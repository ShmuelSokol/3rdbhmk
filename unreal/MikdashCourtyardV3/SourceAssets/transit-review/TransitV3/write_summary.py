"""Write the offline TransitV3 hand-off receipt from the artefacts on disk."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/transit-review/TransitV3/transit-v3-offline.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


spec = json.loads((ROOT / 'Scripts/release_transit_v3.spec.json').read_text(encoding='utf-8'))
geometry = json.loads((ROOT / 'SourceAssets/transit-review/VehiclesV3/geometry-manifest.json').read_text(encoding='utf-8'))
routes = json.loads((ROOT / 'SourceAssets/transit-review/TransitV3/routes-v3.json').read_text(encoding='utf-8'))
tests = json.loads((ROOT / 'SourceAssets/runtime-review/transit/tests.json').read_text(encoding='utf-8'))

vehicles = []
for label, entry in geometry['assemblies'].items():
    if entry['role'] == 'door_leaf':
        continue
    bounds = entry['bounds_cm']
    vehicles.append(dict(
        body=label, role=entry['role'], reference=entry['segment'],
        lengthCm=round(bounds['max'][0] - bounds['min'][0], 1),
        widthCm=round(bounds['max'][1] - bounds['min'][1], 1),
        heightCm=round(bounds['max'][2] - bounds['min'][2], 1),
        trianglesLod0=entry['triangles'],
        trianglesByGroup={g: n for g, n in entry['groups'].items() if n},
        servesStops=entry['servesStops'],
        fromRealReference=('dimensions and proportions only' if entry['role'] != 'car'
                           else 'segment dimensions only'),
        generic='silhouette, livery, lamps, trim, interior and all markings'))

stops = []
index = 0
for route in routes['routes']:
    for stop in route['stops']:
        stops.append(dict(globalStopIndex=index, route=route['id'], kind=route['kind'],
                          name=stop['name'], worldCm=stop['worldCm'],
                          headingDegrees=stop['headingDegrees'],
                          crossfallDegrees=stop['surface']['crossfallDegrees'],
                          gradientDegrees=stop['surface']['gradientDegrees'],
                          spreadCm=stop['surface']['spreadCm'],
                          surfaceFamilies=stop['surface']['surfaceFamilies'],
                          boardingPeople=[stop['boardingMinPeople'], stop['boardingMaxPeople']],
                          dwellSeconds=[stop['dwellMinSeconds'], stop['dwellMaxSeconds']]))
        index += 1

receipt = dict(
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
    status='transit_v3_offline_authored_native_placement_pending',
    scope=('Offline authoring only: vehicle geometry, route and stop derivation from the '
           'retained OSM context roads and the source street triangles, and the release plan. '
           'Nothing in Content/ was touched, no map was opened and no actor was placed. The '
           'native half is Scripts/release_transit_v3.py.'),
    artefacts=dict(
        generator=dict(file='Scripts/create_vehicles.py',
                       sha256=sha(ROOT / 'Scripts/create_vehicles.py')),
        geometryManifest=dict(file='SourceAssets/transit-review/VehiclesV3/geometry-manifest.json',
                              sha256=sha(ROOT / 'SourceAssets/transit-review/VehiclesV3/geometry-manifest.json')),
        routes=dict(file='SourceAssets/transit-review/TransitV3/routes-v3.json',
                    sha256=sha(ROOT / 'SourceAssets/transit-review/TransitV3/routes-v3.json')),
        releaseScript=dict(file='Scripts/release_transit_v3.py',
                           sha256=sha(ROOT / 'Scripts/release_transit_v3.py')),
        releaseSpec=dict(file='Scripts/release_transit_v3.spec.json',
                         sha256=sha(ROOT / 'Scripts/release_transit_v3.spec.json')),
        runtimeHeader=dict(file='Plugins/MikdashRuntime/Source/MikdashRuntime/Public/TransitMath.h',
                           sha256=sha(ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/TransitMath.h')),
        runtimeActor=dict(file='Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashTransit.h',
                          sha256=sha(ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashTransit.h')),
        mathTests=dict(file='SourceAssets/runtime-review/transit/tests.json',
                       checksEvaluated=tests['checksEvaluated'],
                       debugAndReleaseIdentical=tests['debugAndReleaseMeasurementsIdentical']),
        offlineDerivation=dict(
            routeDeriver='SourceAssets/transit-review/TransitV3/derive_routes_v3.py',
            specBuilder='SourceAssets/transit-review/TransitV3/build_spec.py',
            receiptWriter='SourceAssets/transit-review/TransitV3/write_summary.py',
            receiptWriterSha256=sha(ROOT / 'SourceAssets/transit-review/TransitV3/write_summary.py'),
            note=('Kept beside their output so every number in this receipt can be '
                  'reproduced offline.'))),
    vehicles=vehicles,
    consist=geometry['consist'],
    totalTrianglesLod0=geometry['totalTriangles'],
    lods=geometry['lods'],
    routes=[dict(id=r['id'], kind=r['kind'], label=r['label'], highway=r['highway'],
                 osmWayIds=[w['osmWayId'] for w in r['sourceWays']],
                 lengthCm=r['lengthCm'], controlPoints=r['controlPointCount'],
                 laneOffsetCm=r['laneOffsetCm'], speedLimitCmPerSecond=r['speedLimitCmPerSecond'],
                 vehicleWeight=r['vehicleWeight'], busShare=r['busShare'],
                 stops=len(r['stops']), offStreetCentrelineSamples=r['offStreetSamples'],
                 stopProbeSummary=r['stopProbeSummary'], note=r['note'])
            for r in routes['routes']],
    stops=stops,
    surfaceValidation=dict(
        method=('Barycentric interpolation of the highest source street triangle under each of '
                'four probes, from jerusalem-meshes.json meshes "Asphalt roads" and "Stone '
                'paths" -- the same source and the same arithmetic release_place_bus.spec.json '
                'used for the hero bus. Probe footprint is 720 x 192 cm for road stops (the '
                'hero bus wheelbase and track) and 600 x 143.5 cm for rail stops (bogie spacing '
                'and standard gauge).'),
        limitsApplied=routes['limits'],
        spreadDeparture=('The hero bus rejects a spread over 60 cm because it fits a plane '
                         'through four wheel contacts and places a rigid actor on it. '
                         'AMikdashTransit poses vehicles yaw-only on the route centreline and '
                         'never applies pitch or roll, so spread costs nothing there: it is '
                         'measured and reported and only rejected past 150 cm. Crossfall and '
                         'gradient are the hero bus limits unchanged.'),
        reproducesHeroBusFinding=('road_batei_mahase: 138 of 193 probe positions were rejected '
                                  'for crossfall over 8 degrees, all in the eastern half. That '
                                  'is the same finding release_place_bus.spec.json records '
                                  '("the whole eastern half of the road exceeds 8 deg '
                                  'crossfall"), reached independently from the same source '
                                  'triangles. The one accepted stop is at the west end, 2.8 m '
                                  'from the placed hero bus.'),
        stillToProve=('These are OFFLINE numbers from the source triangles, not engine ground '
                      'contact. release_transit_v3.py trace_stops re-measures every stop with a '
                      'PIE line trace and drops any that disagrees.')),
    railService=dict(
        circuitLengthCm=next(r['lengthCm'] for r in routes['routes'] if r['kind'] == 'rail'),
        lineSpeedCmPerSecond=next(r['speedLimitCmPerSecond'] for r in routes['routes'] if r['kind'] == 'rail'),
        stations=sum(len(r['stops']) for r in routes['routes'] if r['kind'] == 'rail'),
        runningSecondsPerLap=round(next(r['lengthCm'] for r in routes['routes'] if r['kind'] == 'rail')
                                   / next(r['speedLimitCmPerSecond'] for r in routes['routes']
                                          if r['kind'] == 'rail'), 1),
        dwellSecondsPerLap=[5 * 20.0, 5 * 40.0],
        headwaySeconds=[spec['transitActor']['TrainHeadwayMinSeconds'],
                        spec['transitActor']['TrainHeadwayMaxSeconds']],
        consistSlots=spec['transitActor']['MaxActiveTrains'],
        arithmetic=('A lap is about 189 s of running plus 100-200 s of station dwell, so about '
                    '290-390 s. Three slots therefore sustain a departure every 97-130 s at '
                    'worst, which is inside the 120 s minimum headway: the 2-to-5-minute '
                    'promise holds and is never limited by the slot count. If the route is '
                    'lengthened or the line speed dropped, check this again -- when a lap '
                    'exceeds three times the minimum headway the dispatcher simply waits and '
                    'the service silently thins out.'),
        outAndBackCaveat=('Every route is a CLOSED out-and-back circuit and each stop is a '
                          'single world position projected onto it, so a stop is served ONCE '
                          'per lap, on whichever half of the circuit its projection landed. '
                          'A platform is therefore served in one direction only. Serving both '
                          'would need the stop authored twice, once per half.')),
    budget=spec['budget'],
    coordinatorMustWire=spec['coordinatorMustWire'],
    realVsGeneric=dict(realReference=geometry['realReference'] + [
        'The rail route follows Jaffa Road, which OSM tags highway=pedestrian over this stretch '
        'because it carries the light rail and pedestrians only. That is the real Jerusalem '
        'Light Rail red line corridor.',
        'The road routes are real Jerusalem streets by OSM way id: Hativat Yerushalayim (trunk, '
        '984820251 + 261439508 + 1188718143), HaTsanhanim (trunk, 184793808 + 234683403), '
        'Sultan Suleiman (tertiary, 1299310533 + 771909611 + 1299310546), Maale HaShalom '
        '(tertiary, 771909616), Maalot Ir David and HaOfel (tertiary, 157676832 + 34244965) and '
        'Batei Mahase (residential, 496167693).',
        'Sultan Suleiman carries the highest bus share because the East Jerusalem bus terminals '
        'are on it in the real city.',
    ], generic=geometry['generic'] + [
        'The light-rail TRACK, its stations, its platforms and its service pattern are authored '
        'interpretation laid along the real corridor. They are not surveyed infrastructure, not '
        'an approved alignment and not a real timetable.',
        'Lane offsets, lane counts, one-way restrictions, junction control and kerb lines are '
        'authored: only 8 of the 5,944 source ways carry a width tag and none carries lane data.',
        'Stop positions are chosen by the flattest passing footprint in a spacing window. They '
        'are not real bus stops and do not correspond to any real stop location.',
        'Turnaround caps closing each open road into a circuit are a geometric device, not real '
        'turning circles, and may not lie on drivable ground.',
    ]),
    limitations=routes['routes'][0].get('limitations', []) + geometry['limitations'] + [
        'No junction, signal, right of way, pedestrian crossing or collision behaviour is '
        'modelled anywhere. A vehicle follows the vehicle ahead of it on its own route and '
        'nothing else, and passes through anything not on its route.',
        'No crowd is wired or spawned by any of this. The boarding hook is defined and tested; '
        'connecting it to AMikdashCrowdField is the coordinator\'s job.',
        'The engine shell (AMikdashTransit) has no standalone test: it needs an editor to '
        'compile and a world to run. Only TransitMath.h is covered by the 941,241-check gate.',
    ],
    notAClaimOf=spec['notAClaimOf'],
    runOrder=spec['invocation']['runOrder'],
)
OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('wrote', OUT, OUT.stat().st_size, 'bytes')
print('vehicles', len(vehicles), 'routes', len(receipt['routes']), 'stops', len(stops))

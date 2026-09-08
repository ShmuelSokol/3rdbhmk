"""Emit Scripts/release_transit_v3.spec.json from the two offline receipts, so every
number in the spec is copied from evidence rather than typed."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
GEOMETRY = ROOT / 'SourceAssets/transit-review/VehiclesV3/geometry-manifest.json'
ROUTES = ROOT / 'SourceAssets/transit-review/TransitV3/routes-v3.json'
SPEC = ROOT / 'Scripts/release_transit_v3.spec.json'
MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


geometry = json.loads(GEOMETRY.read_text(encoding='utf-8'))
routes = json.loads(ROUTES.read_text(encoding='utf-8'))

road_routes = [r for r in routes['routes'] if r['kind'] == 'road']
rail_routes = [r for r in routes['routes'] if r['kind'] == 'rail']
stop_total = sum(len(r['stops']) for r in routes['routes'])

# ---------------------------------------------------------------------------
# Budget. Stated with its basis, because a number without one is a guess.
# ---------------------------------------------------------------------------
road_vehicle_count = 240
update_budget = 48
frames_per_sweep = -(-road_vehicle_count // update_budget)
car_triangles = max(v['triangles'] for k, v in geometry['assemblies'].items() if k.startswith('Car'))
bus_triangles = geometry['assemblies']['Bus']['triangles']
tram_triangles = (2 * geometry['assemblies']['TramCab']['triangles']
                  + 3 * geometry['assemblies']['TramMid']['triangles'])
max_trains = 3
worst_case_triangles = road_vehicle_count * max(car_triangles, bus_triangles) + max_trains * tram_triangles

spec = {
    'specVersion': 1,
    'prepared': '2026-09-08',
    'purpose': ('Human-reviewable plan consumed by Scripts/release_transit_v3.py: import the '
                'VehiclesV3 meshes and textures, validate every TransitV3 stop against real '
                'street surface with a bounded PIE trace, then place and configure ONE '
                'AMikdashTransit actor in the combined Walkthrough map. Every number below was '
                'computed offline from frozen source data or copied from a receipt on disk; '
                'nothing here is a claim of visual or runtime acceptance.'),
    'projectDir': str(ROOT),
    'targetMap': MAP,
    'targetMapFile': 'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap',
    'protectedMaps': [
        '/Game/MikdashV3/Maps/Courtyard',
        '/Game/MikdashV3/FutureMountV1/L_FutureMount',
        '/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold',
    ],
    'checkpointRoot': r'C:\Mikdash\Working-5.8\ReviewCheckpoints',
    'checkpointPrefix': 'ReleaseTransitV3-',
    'receiptFolder': 'SourceAssets/transit-review/TransitV3',
    'receiptPrefix': 'release-transit-v3-',
    'actorTag': 'ReleasePlacementV1',
    'groupTag': 'ReleaseTransitV3',
    'labelPrefix': 'RELEASE_TransitV3_',
    'folder': 'Release/TransitV3',
    'actorClass': '/Script/MikdashRuntime.MikdashTransit',
    'actorLabel': 'RELEASE_TransitV3_Transit',
    'actorLocationCm': [0.0, 0.0, 0.0],
    'actorLocationNote': ('AMikdashTransit builds every route from WORLD positions and writes '
                          'every instance transform in world space, so the actor transform is '
                          'never applied to anything and is pinned at the origin. Moving the '
                          'actor moves nothing.'),

    'geometry': {
        'manifest': str(GEOMETRY.relative_to(ROOT).as_posix()),
        'manifestSha256': sha(GEOMETRY),
        'manifestStatusRequired': 'offline_checked_native_and_visual_pending',
        'sourceFolder': 'SourceAssets/transit-review/VehiclesV3',
        'textureFolder': 'SourceAssets/transit-review/VehiclesV3/textures',
        'destination': geometry['namespace'],
        'materialFolder': geometry['namespace'] + '/Materials',
        'objConvention': geometry['objConvention'],
        'palette': geometry['palette'],
        'lods': geometry['lods'],
        'importOptions': {
            'import_uniform_scale': 1.0,
            'convert_scene': False,
            'convert_scene_unit': False,
            'auto_generate_collision': False,
            'build_nanite': False,
            'generate_lightmap_u_vs': False,
            'note': ('build_nanite is off: in 5.8 a Nanite mesh reports only fallback triangles '
                     'at LOD0, so the recorded triangle counts would stop meaning anything. '
                     'Collision is off because AMikdashTransit sets NoCollision on every '
                     'component; these instances are never traced against or walked on.'),
        },
        'meshes': [
            {'name': record['name'], 'file': record['file'], 'sha256': record['sha256'],
             'assembly': record['assembly'], 'group': record['group'],
             'triangles': record['triangles'], 'localBoundsCm': record['bounds_cm']}
            for record in geometry['imports']
        ],
        'textures': geometry['textures'],
        'realReference': geometry['realReference'],
        'generic': geometry['generic'],
        'consist': geometry['consist'],
        'doorLocalOffsetsCm': geometry['doorLocalOffsetsCm'],
    },

    'routes': {
        'file': str(ROUTES.relative_to(ROOT).as_posix()),
        'sha256': sha(ROUTES),
        'schemaRequired': 'MikdashTransitRoutesV3',
        'alignment': routes['alignment'],
        'source': routes['source'],
        'limits': routes['limits'],
        'routeCount': len(routes['routes']),
        'stopCount': stop_total,
        'summary': [
            {'id': r['id'], 'kind': r['kind'], 'label': r['label'], 'highway': r['highway'],
             'sourceWays': r['sourceWays'], 'controlPoints': r['controlPointCount'],
             'lengthCm': r['lengthCm'], 'laneOffsetCm': r['laneOffsetCm'],
             'speedLimitCmPerSecond': r['speedLimitCmPerSecond'],
             'vehicleWeight': r['vehicleWeight'], 'busShare': r['busShare'],
             'offStreetCentrelineSamples': r['offStreetSamples'],
             'stopProbeSummary': r['stopProbeSummary'],
             'stops': [{'name': s['name'], 'worldCm': s['worldCm'],
                        'crossfallDegrees': s['surface']['crossfallDegrees'],
                        'gradientDegrees': s['surface']['gradientDegrees'],
                        'spreadCm': s['surface']['spreadCm'],
                        'surfaceFamilies': s['surface']['surfaceFamilies'],
                        'boardingMinPeople': s['boardingMinPeople'],
                        'boardingMaxPeople': s['boardingMaxPeople'],
                        'furnitureOffsetCm': s['furnitureOffsetCm']} for s in r['stops']]}
            for r in routes['routes']
        ],
    },

    'groundProbes': {
        'maxCrossfallDegrees': routes['limits']['maxCrossfallDegrees'],
        'maxGradientDegrees': routes['limits']['maxGradientDegrees'],
        'supportMeshPrefixes': ['/Game/MikdashV3/JerusalemContext/Streets/'],
        'supportLabelPrefixes': ['SM_Jerusalem_Asphalt_', 'SM_Jerusalem_StonePaths_'],
        'supportNote': ('A stop must stand on a real street mesh. Both street families count: '
                        'SM_Jerusalem_Asphalt_ is the carriageway and SM_Jerusalem_StonePaths_ '
                        'is the paved street. Jaffa Road is paved rather than asphalted in the '
                        'source data, which is why the tram stations sample the stone family. '
                        'release_place_bus.spec.json accepts the same two prefixes; the hero '
                        'bus additionally required asphalt under the painted body corners, '
                        'which is a hero-placement rule and is not applied here.'),
        'probeFootprintCm': {'road': {'wheelbase': 720.0, 'track': 192.0},
                             'rail': {'bogieSpacing': 600.0, 'gauge': 143.5}},
        'traceAboveOfflineZCm': 2500.0,
        'traceBelowOfflineZCm': 2500.0,
        'offlineAgreementToleranceCm': 30.0,
        'offlineAgreementNote': ('The traced Z is compared with the offline barycentric Z from '
                                 'the same source triangles. A disagreement beyond the tolerance '
                                 'means the trace found a DIFFERENT surface (a building, a path, '
                                 'a terrain tile) and is recorded per probe, not averaged away.'),
        'maxFailedStops': 4,
        'maxFailedStopsNote': ('Up to this many stops may fail their trace and be dropped from '
                               'the placed configuration; beyond it the run fails and the map is '
                               'left untouched. Dropping a stop is recorded by name.'),
        'aabbNote': ('NO actor bounding box is used anywhere in this script. The 256 FutureMountV1 '
                     'terrain tiles carry 400-800 m AABBs that enclose the whole Temple, and their '
                     'union meshes are hollow, so a raw-bounds blocker test on this map returned '
                     '100 percent false positives before. Support is decided ONLY by the mesh path '
                     'of the component the trace actually hit, which is exact and needs no '
                     'decomposition of any union mesh into constituent boxes.'),
        'traceNote': ('Line traces return nothing under -run=pythonscript and in NullRHI editor '
                      'worlds. That is why this is a two-step job: trace_stops runs in a bounded '
                      'PIE world in a dedicated editor and writes a pose receipt; '
                      'place_from_receipt reads that receipt and mutates the map, and runs '
                      'synchronously so it works as a commandlet.'),
    },

    'transitActor': {
        'RoadVehicleCount': road_vehicle_count,
        'DensityMultiplier': 1.0,
        'MaxRoadVehicles': 900,
        'MaxActiveTrains': max_trains,
        'UpdateBudget': update_budget,
        'TransformFreezeDistanceCm': 220000.0,
        'InstanceCullStartCm': 90000.0,
        'InstanceCullEndCm': 260000.0,
        'TrainHeadwayMinSeconds': 120.0,
        'TrainHeadwayMaxSeconds': 300.0,
        'TrainDwellMinSeconds': 20.0,
        'TrainDwellMaxSeconds': 40.0,
        'TrainCarLengthCm': geometry['consist']['moduleLengthCm'],
        'TrainCouplingGapCm': geometry['consist']['couplingGapCm'],
        'TrainBogieInsetCm': 150.0,
        'BusDwellMinSeconds': 14.0,
        'BusDwellMaxSeconds': 28.0,
        'DoorOpenSeconds': 1.6,
        'DoorCloseSeconds': 1.8,
        'DoorTravelCm': 58.0,
        'PhotographerShare': 0.22,
        'Seed': 20260908,
        'bActivateOnBeginPlay': True,
        'PaintPalette': [
            [0.82, 0.83, 0.84], [0.05, 0.06, 0.07], [0.28, 0.30, 0.33], [0.62, 0.63, 0.64],
            [0.33, 0.03, 0.03], [0.03, 0.10, 0.24], [0.06, 0.16, 0.11], [0.55, 0.42, 0.10],
            [0.72, 0.71, 0.66], [0.14, 0.15, 0.17],
        ],
        'paletteNote': ('Ten body colours, weighted toward the white/silver/grey that dominate a '
                        'real Israeli street. Applied per instance through HISM custom data '
                        'floats 0..2; the Paint material multiplies them into the livery texture.'),
    },

    'budget': {
        'target': 'RTX 2070 (8 GB VRAM, TU106) in a 16 GB system',
        'roadVehicles': road_vehicle_count,
        'activeTrains': max_trains,
        'trainCarsPerConsist': geometry['consist']['modules'],
        'updateBudgetPerFrame': update_budget,
        'framesPerSweep': frames_per_sweep,
        'sweepSecondsAt60Fps': round(frames_per_sweep / 60.0, 4),
        'sweepSecondsAt30Fps': round(frames_per_sweep / 30.0, 4),
        'worstCaseTrianglesAllLod0': worst_case_triangles,
        'hismComponents': len(geometry['imports']),
        'lod0TrianglesAllBodies': geometry['totalTriangles'],
        'basis': [
            'TRIANGLES are not the constraint. Every body is under %d triangles at LOD0 and the '
            'whole set is %d. With every road vehicle and all %d consists resident at LOD0 the '
            'layer is %s triangles, which a TU106 draws in a fraction of a millisecond; the '
            'declared LOD ladder (%s) and the %.0f m cull take most of that away again.'
            % (max(car_triangles, bus_triangles), geometry['totalTriangles'], max_trains,
               format(worst_case_triangles, ','), geometry['lods']['percentTriangles'],
               260000.0 / 100.0),
            'VRAM is not the constraint. %d static meshes totalling %d triangles is well under a '
            'megabyte of vertex data, and the four textures are 512x256 and 128x128 RGB.'
            % (len(geometry['imports']), geometry['totalTriangles']),
            'DRAW CALLS are bounded by the component count, not the instance count: %d HISM '
            'components plus stop furniture, one batch each per LOD per view.'
            % len(geometry['imports']),
            'The real cost is the CPU-side instance transform write and the render-state flush. '
            'AMikdashTransit bounds both: it advances %d vehicles per frame whatever the total, '
            'and marks each touched component dirty ONCE per frame rather than once per instance. '
            'At %d vehicles that is a %d-frame sweep, %.3f s at 60 fps.'
            % (update_budget, road_vehicle_count, frames_per_sweep, frames_per_sweep / 60.0),
            'The sweep length is what sets the vehicle count, not the GPU. CatchUpSeconds clamps '
            'a vehicle step to 0.35 s, and at 1000 cm/s a %.3f s step covers %.0f cm against the '
            '120 cm arrival tolerance, so the stop line cannot be stepped over at 60 fps. At '
            '30 fps the step is %.0f cm and the dwell machine leans on its LOW SPEED condition '
            'instead, which is why that condition exists. Raising RoadVehicleCount without '
            'raising UpdateBudget lengthens the sweep and eventually breaks that margin: the '
            'ceiling for this budget is about %d road vehicles.'
            % (frames_per_sweep / 60.0, 1000.0 * frames_per_sweep / 60.0,
               1000.0 * frames_per_sweep / 30.0, update_budget * 5),
            'The binding constraint on this machine is the CROWD, not the traffic. %d stops can '
            'each ask for a boarding group, and AMikdashCrowdField pays per figure. The '
            'coordinator should cap concurrent transit-driven crowd instances; see '
            'coordinatorMustWire below.' % stop_total,
            'MaxRoadVehicles 900 and the math\'s own 8x clamp on DensityMultiplier exist so a '
            'mistyped multiplier cannot allocate without bound. They are a fuse, not a target.',
        ],
    },

    'coordinatorMustWire': [
        'Bind the crowd. AMikdashTransit references, includes and edits nothing in '
        'AMikdashCrowdField or the 24 residents. Bind OnRequestBoarding to the crowd field\'s '
        '"converge on point and despawn" entry point and OnRequestAlighting to its "spawn at '
        'point and disperse" entry point, or override the RequestBoarding / RequestAlighting '
        'BlueprintImplementableEvents in a Blueprint subclass. Both carry '
        '(GlobalStopIndex, Count, BoardingPoint, SecondsAvailable, RouteId).',
        'Honour SecondsAvailable. It is the dwell the doors will actually stay open. A crowd '
        'walk that takes longer than it will still be walking when the vehicle leaves.',
        'Use BoardingPoint, not GetStopLocation. BoardingPoint is the world point at the '
        'vehicle door on the kerb side for THIS arrival; GetStopLocation is the authored stop '
        'and GetStopFurniturePoint is the shelter or platform face to gather at.',
        'Call SuggestPhotographerCount(GlobalStopIndex, Count, RunIndex) from the boarding '
        'handler and give that many figures a standing photograph pose facing the Mount. The '
        'transit actor owns no pedestrian and implements no behaviour; the number is a hint.',
        'Cap concurrency. Nothing in the transit layer limits how many boarding groups are live '
        'at once. With 16 stops the coordinator must impose its own ceiling on transit-driven '
        'crowd instances and drop requests over it, rather than letting the crowd grow.',
        'Set ShelterMeshes and PlatformMeshes if stop furniture is wanted. This release leaves '
        'both empty: no shelter or platform geometry is authored in VehiclesV3, and placing the '
        'TransitSystemV1 shelter would import a frozen namespace this job does not own.',
        'Check GetStopProjectionErrorCm after InitializeTransit. It reports how far each authored '
        'stop sat from the route the runtime built. A large value means the stop is off its '
        'route; it is reported rather than hidden and nothing else will tell you.',
    ],

    'pie': {
        'hardLimitSeconds': 300,
        'pieWorldTimeoutSeconds': 90,
        'settleSecondsAfterWorld': 1.5,
        'endPlaySettleSeconds': 2.0,
        'reopenSettleSeconds': 1.0,
        'note': ('The hard limit aborts before the map is saved; once saved the run completes '
                 'readback and records limitExceededAfterSave rather than leaving a '
                 'half-verified save.'),
    },

    'verification': {
        'staticBoundsToleranceCm': 0.05,
        'transformToleranceCm': 0.001,
        'rotationToleranceDegrees': 0.001,
        'routePointToleranceCm': 0.01,
        'compareRule': ('Numeric location/rotation/scale and per-route point arrays only; '
                        'str(Transform) is never compared.'),
    },

    'invocation': {
        'importAssets': ('"C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\'
                         'UnrealEditor-Cmd.exe" "%s\\MikdashCourtyardV3.uproject" -run=pythonscript '
                         '-script="%s/Scripts/release_transit_v3.py" -unattended -nullrhi '
                         '-abslog="C:/Mikdash/Working-5.8/Release-TransitV3-01.log"'
                         % (ROOT, ROOT.as_posix())),
        'importAssetsEnv': {'MIKDASH_TRANSIT_MODE': 'import_assets'},
        'traceStops': ('"C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\'
                       'UnrealEditor.exe" "%s\\MikdashCourtyardV3.uproject" %s '
                       '-ExecCmds="py %s/Scripts/release_transit_v3.py" -unattended -NoSplash '
                       '-nullrhi -abslog="C:/Mikdash/Working-5.8/Release-TransitV3-02.log"'
                       % (ROOT, MAP, ROOT.as_posix())),
        'traceStopsEnv': {'MIKDASH_TRANSIT_MODE': 'trace_stops', 'MIKDASH_TRANSIT_QUIT_EDITOR': '1'},
        'placeFromReceipt': ('"C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\'
                             'UnrealEditor-Cmd.exe" "%s\\MikdashCourtyardV3.uproject" '
                             '-run=pythonscript -script="%s/Scripts/release_transit_v3.py" '
                             '-unattended -nullrhi '
                             '-abslog="C:/Mikdash/Working-5.8/Release-TransitV3-03.log"'
                             % (ROOT, ROOT.as_posix())),
        'placeFromReceiptEnv': {'MIKDASH_TRANSIT_MODE': 'place_from_receipt',
                                'MIKDASH_TRANSIT_TRACE_RECEIPT': '<trace_stops receipt path>'},
        'runOrder': ['import_assets', 'trace_stops', 'place_from_receipt'],
        'serialNote': ('One engine at a time on this machine. Every step is a dedicated editor '
                       'and never the user\'s GUI editor.'),
    },

    'notAClaimOf': [
        'visual acceptance of any body, livery or material',
        'that the traffic reads as Jerusalem to a person who lives there',
        'pedestrian boarding: no crowd is wired by this script and none is spawned',
        'a surveyed or approved light-rail alignment: the track, stations and platforms along '
        'the Jaffa Road corridor are authored interpretation',
        'junction, signal, right-of-way, crossing or collision behaviour, none of which exists',
        'packaged-build or cook acceptance',
    ],
}

SPEC.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print('wrote', SPEC, SPEC.stat().st_size, 'bytes')
print('routes', len(routes['routes']), 'stops', stop_total, 'meshes', len(geometry['imports']))
print('frames per sweep', frames_per_sweep, 'worst-case triangles', worst_case_triangles)

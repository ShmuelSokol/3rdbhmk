"""Read-only PIE diagnosis of resident spawn refusals on the isolated 48 cm candidate.

Runs inside the editor via -ExecCmds="py ...". Opens PIE on the already-loaded candidate
map, waits for the resident population to finish its BeginPlay spawn pass, then for every
authored person recomputes the decoded (selected48) waypoint 0 and performs the SAME
physical query the spawner performs: a 34 x 96 capsule on the Pawn profile at feet+96.
Every blocking hit is recorded with its component, static mesh path, mesh collision setup,
component world box and penetration depth. Floor, ceiling and horizontal probes plus a
sweep of every route leg give the surrounding geometry. Nothing is saved; map bytes and
user save files are hashed before/after. Real-RHI PIE only: NullRHI results are refused.
"""
from pathlib import Path
import hashlib, json, math, os, re, time, traceback
from datetime import datetime, timezone
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'Scripts/diagnose_candidate_spawns.spec.json').read_text(encoding='utf-8-sig'))
MAP = SPEC['candidateMap']
MAIN = SPEC['mainMap']
RATIO = 48.0 / 50.0
RADIUS, HALF = 34.0, 96.0
LIFT = 96.0
ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
actors_sub = u.get_editor_subsystem(u.EditorActorSubsystem)
command_line = u.SystemLibrary.get_command_line()
assert '-nullrhi' not in command_line.lower(), 'NullRHI traces are not evidence'
assert ed.get_game_world() is None
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
assert ed.get_editor_world().get_outermost().get_name() == MAP, 'Candidate map must be the loaded editor world'
prefix_match = re.search(r'-TestSavePrefix=((?:AstraProbe|FableProbe)_[A-Za-z0-9_]+)', command_line)
assert prefix_match, 'Require a unique -TestSavePrefix=FableProbe_<stamp> and Game ini overrides'
test_prefix = prefix_match.group(1)
for section, key, value in [('MikdashSaveSystem', 'SlotNamePrefix', test_prefix), ('MikdashSettingsSubsystem', 'SaveSlot', test_prefix + '_Settings')]:
    assert ('[/Script/MikdashRuntime.' + section + ']:' + key + '=' + value) in command_line, 'Missing save-isolation ini override'

map_file = ROOT / 'Content' / (MAP[6:] + '.umap')
main_file = ROOT / 'Content' / (MAIN[6:] + '.umap')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
save_roots = [ROOT / 'Saved/SaveGames', Path(os.environ['LOCALAPPDATA']) / 'MikdashCourtyardV3/Saved/SaveGames']
def user_save_hashes():
    return {str(p): sha(p) for folder in save_roots if folder.exists() for p in folder.glob('*.sav')
            if not (p.name.startswith('AstraProbe_') or p.name.startswith('FableProbe_'))}
original_saves = user_save_hashes()
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
out = ROOT / 'SourceAssets/scale-review' / ('spawn-diagnosis-' + stamp + '.json')
report = dict(status='starting', map=MAP, mapShaBefore=sha(map_file), mainShaBefore=sha(main_file), errors=[],
              scope='Real-RHI PIE capsule/floor queries at decoded waypoint 0 and along route legs; no map writes; not a navmesh or visual acceptance',
              commandLine=command_line, saveIsolation=dict(testPrefix=test_prefix, originalSaveFileCount=len(original_saves)))
def write(): out.write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')
def xyz(v): return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]
def V(p): return u.Vector(p[0], p[1], p[2])

# ---------------------------------------------------------------------------------------
# Decoder replica (PopulationSceneMath.h): outer-court feet x RATIO, mount-deck metric,
# plus the three authored selected48 route extensions (25 cm outward edge moves).
# ---------------------------------------------------------------------------------------
people = json.loads((ROOT / 'Content/Distribution/People/people.json').read_text(encoding='utf-8-sig'))
EXT = {'chananel-ben-mattisyahu': (2, 25.0), 'rivka-bas-yoezer': (0, -25.0), 'nechemya-ben-tzuriel': (2, 25.0)}
def decode(person):
    pts = []
    for w in person['route']:
        x, y, z = w['at']
        pts.append([x * RATIO, y * RATIO, z * RATIO] if person['zone'] == 'outer-court' else [x, y, z])
    if person['id'] in EXT:
        first, dy = EXT[person['id']]
        pts[first][1] += dy; pts[first + 1][1] += dy
    return pts
def in_zone48(x, y, zone):
    if zone == 'mount-deck': return 9300 <= x <= 10000 and abs(y) <= 3000
    return 1440 <= x <= 6720 and 864 <= abs(y) < 5760
REFUSED = set(SPEC['previouslyRefused'])
PILOT_LEGACY = [[4900, 1000, 300], [5120, 1120, 300], [4980, 1260, 300], [5240, 1330, 300], [4760, 1180, 300]]

# ---------------------------------------------------------------------------------------
# Editor-world readback of both population actors (read-only).
# ---------------------------------------------------------------------------------------
def describe_population(pop):
    row = dict(name=pop.get_name(), label=pop.get_actor_label(), location=xyz(pop.get_actor_location()))
    for key in ('spawn_authored_people_on_begin_play', 'people_directory_file', 'source_coordinate_revision',
                'activate_reviewed_pilot_on_begin_play', 'extended_route_body_index', 'extended_route_laps'):
        try: row[key] = str(pop.get_editor_property(key))
        except Exception as exc: row[key] = 'unavailable: ' + repr(exc)
    try:
        row['extendedRouteWaypoints'] = [xyz(v) for v in pop.get_editor_property('extended_route_waypoints')]
        row['extendedRouteLookTargets'] = [xyz(v) for v in pop.get_editor_property('extended_route_look_targets')]
        row['extendedRouteLabels'] = [str(s) for s in pop.get_editor_property('extended_route_labels')]
    except Exception as exc: row['extendedRoute'] = 'unavailable: ' + repr(exc)
    bodies = []
    try:
        for i, body in enumerate(pop.get_editor_property('bodies')):
            if body is None: bodies.append(None); continue
            cap = body.get_component_by_class(u.CapsuleComponent)
            loc = body.get_actor_location()
            item = dict(index=i, label=body.get_actor_label(), actorLocation=xyz(loc), scale=xyz(body.get_actor_scale3d()))
            if cap:
                item['capsuleRadius'] = cap.get_scaled_capsule_radius(); item['capsuleHalfHeight'] = cap.get_scaled_capsule_half_height()
                item['feet'] = [round(loc.x, 3), round(loc.y, 3), round(loc.z - cap.get_scaled_capsule_half_height(), 3)]
            if i < 5:
                lp = PILOT_LEGACY[i]; conv = [lp[0] * RATIO, lp[1] * RATIO, lp[2] * RATIO]
                item['legacyPilotFeet'] = lp; item['selected48PilotFeet'] = conv
                if 'feet' in item:
                    item['distanceToSelected48FeetCm'] = round(math.dist(item['feet'], conv), 3)
                    item['distanceToLegacyFeetCm'] = round(math.dist(item['feet'], lp), 3)
            bodies.append(item)
    except Exception as exc: bodies = 'unavailable: ' + repr(exc)
    row['bodies'] = bodies
    return row
populations = [a for a in actors_sub.get_all_level_actors() if isinstance(a, u.MikdashResidentPopulation)]
report['editorPopulations'] = [describe_population(p) for p in populations]
descriptors = [a for a in actors_sub.get_all_level_actors() if isinstance(a, u.MikdashSceneUnits)]
report['sceneDescriptors'] = [dict(name=d.get_name(), revision=str(d.get_editor_property('scene_revision'))) for d in descriptors]
# Old extended-route look targets that TryLook would refuse (the allowlist in PopulationSceneMath.h).
def look_classified(p):
    near = lambda a, b: abs(a - b) < .01
    x, y, z = p
    if near(x, 11500) and near(y, 0) and near(z, 0): return 'metric'
    if (near(x, 0) or near(x, 7800)) and near(y, 0) and near(z, 300): return 'temple'
    if near(x, 8600) and near(y, 0) and near(z, 0): return 'temple'
    return None
for row in report['editorPopulations']:
    looks = row.get('extendedRouteLookTargets')
    if isinstance(looks, list):
        row['extendedRouteLookClassification'] = [dict(look=p, classification=look_classified(p)) for p in looks]
write()

# ---------------------------------------------------------------------------------------
# Physical queries.
# ---------------------------------------------------------------------------------------
OBJECT_TYPES = [u.ObjectTypeQuery.OBJECT_TYPE_QUERY1, u.ObjectTypeQuery.OBJECT_TYPE_QUERY2,
                u.ObjectTypeQuery.OBJECT_TYPE_QUERY3, u.ObjectTypeQuery.OBJECT_TYPE_QUERY4]
VISIBILITY = u.TraceTypeQuery.TRACE_TYPE_QUERY1
NODRAW = u.DrawDebugTrace.NONE
mesh_cache = {}
def mesh_info(mesh):
    if mesh is None: return None
    path = mesh.get_path_name()
    if path in mesh_cache: return mesh_cache[path]
    info = dict(path=path)
    try:
        info['triangles'] = mesh.get_num_triangles(0)
        b = mesh.get_bounds(); info['localBoxExtent'] = xyz(b.box_extent); info['localOrigin'] = xyz(b.origin)
    except Exception as exc: info['meshStats'] = 'unavailable: ' + repr(exc)
    try:
        body = mesh.get_editor_property('body_setup')
        info['collisionTraceFlag'] = str(body.get_editor_property('collision_trace_flag'))
        agg = body.get_editor_property('agg_geom')
        info['simpleCollision'] = dict(boxes=len(agg.get_editor_property('box_elems')), convex=len(agg.get_editor_property('convex_elems')),
                                       spheres=len(agg.get_editor_property('sphere_elems')), capsules=len(agg.get_editor_property('sphyl_elems')))
    except Exception as exc: info['collision'] = 'unavailable: ' + repr(exc)
    mesh_cache[path] = info
    return info
def component_info(comp):
    if comp is None: return None
    owner = comp.get_owner()
    row = dict(component=comp.get_name(), actor=owner.get_name() if owner else None, actorLabel=owner.get_actor_label() if owner else None,
               componentClass=comp.get_class().get_name())
    try:
        origin, extent, _ = u.SystemLibrary.get_component_bounds(comp)
        row['worldBoxMin'] = xyz(origin - extent); row['worldBoxMax'] = xyz(origin + extent)
    except Exception as exc: row['bounds'] = 'unavailable: ' + repr(exc)
    try:
        row['collisionProfile'] = str(comp.get_collision_profile_name()); row['collisionEnabled'] = str(comp.get_collision_enabled())
        row['responseToPawn'] = str(comp.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN))
        row['worldScale'] = xyz(comp.get_component_scale())
    except Exception as exc: row['collisionState'] = 'unavailable: ' + repr(exc)
    if isinstance(comp, u.StaticMeshComponent):
        row['mesh'] = mesh_info(comp.get_editor_property('static_mesh'))
    return row
def hit_rows(hits):
    rows = []
    for h in hits or []:
        if h is None: continue
        try: data = h.to_dict()
        except Exception as exc:
            rows.append(dict(blocking=True, error='to_dict failed: ' + repr(exc))); continue
        low = {str(k).lower().replace('_', ''): v for k, v in data.items()}
        if 'hitResultKeys' not in report: report['hitResultKeys'] = sorted(str(k) for k in data.keys())
        def vec(*names):
            for n in names:
                v = low.get(n)
                if v is not None:
                    try: return xyz(v)
                    except Exception: return str(v)
            return None
        def num(*names):
            for n in names:
                v = low.get(n)
                if v is not None:
                    try: return round(float(v), 3)
                    except Exception: return str(v)
            return None
        row = dict(blocking=bool(low.get('blockinghit', True)), initialOverlap=bool(low.get('initialoverlap', False)),
                   distance=num('distance'), location=vec('location'), impactPoint=vec('impactpoint'),
                   impactNormal=vec('impactnormal', 'normal'), faceIndex=low.get('faceindex'), penetrationDepth=num('penetrationdepth'))
        comp = low.get('hitcomponent') or low.get('component')
        info = guard(component_info, comp)
        if isinstance(info, dict): row.update(info)
        rows.append(row)
    return rows
def guard(fn, *args, **kw):
    try: return fn(*args, **kw)
    except Exception as exc:
        report.setdefault('queryErrors', []).append(dict(function=getattr(fn, '__name__', str(fn)), error=repr(exc)))
        return dict(error=repr(exc))
def unwrap(result):
    if result is None: return []
    if isinstance(result, tuple): result = result[-1]
    return list(result) if result is not None else []
def capsule_hits(world, centre, ignore):
    start = centre + u.Vector(0, 0, 0.5); end = centre - u.Vector(0, 0, 0.5)
    return hit_rows(unwrap(u.SystemLibrary.capsule_trace_multi_by_profile(world, start, end, RADIUS, HALF, 'Pawn', False, ignore, NODRAW, True)))
def capsule_overlaps(world, centre, ignore):
    comps = unwrap(u.SystemLibrary.capsule_overlap_components(world, centre, RADIUS, HALF, OBJECT_TYPES, None, ignore))
    return [component_info(c) for c in comps]
def line(world, a, b, ignore, profile=None):
    if profile: h = u.SystemLibrary.line_trace_single_by_profile(world, a, b, profile, False, ignore, NODRAW, True)
    else: h = u.SystemLibrary.line_trace_single(world, a, b, VISIBILITY, False, ignore, NODRAW, True)
    if isinstance(h, tuple): h = h[-1]
    rows = hit_rows([h] if h is not None else [])
    return rows[0] if rows else None
def floor_check(world, feet, ignore):
    h = line(world, feet + u.Vector(0, 0, 30), feet - u.Vector(0, 0, 30), ignore)
    ok = bool(h and h['blocking'] and isinstance(h.get('impactPoint'), list) and isinstance(h.get('impactNormal'), list)
              and abs(h['impactPoint'][2] - feet.z) <= 3.0 and h['impactNormal'][2] >= 0.95)
    return ok, h
def probe_point(world, feet, ignore, deep=True):
    centre = feet + u.Vector(0, 0, LIFT)
    row = dict(feet=xyz(feet), capsuleCentre=xyz(centre), capsuleZRange=[round(feet.z, 3), round(feet.z + 2 * HALF, 3)])
    row['capsuleHits'] = capsule_hits(world, centre, ignore)
    row['capsuleClear'] = not any(h['blocking'] for h in row['capsuleHits'])
    row['overlappingComponents'] = guard(capsule_overlaps, world, centre, ignore)
    fl = guard(floor_check, world, feet, ignore)
    row['floorOk'], row['floorTrace'] = fl if isinstance(fl, tuple) else (False, fl)
    if deep:
        row['floorBelowFrom250'] = guard(line, world, feet + u.Vector(0, 0, 250), feet - u.Vector(0, 0, 400), ignore)
        row['ceilingAbove'] = guard(line, world, feet + u.Vector(0, 0, 2), feet + u.Vector(0, 0, 500), ignore, 'Pawn')
        walls = {}
        for label, d in (('+X', (1, 0)), ('-X', (-1, 0)), ('+Y', (0, 1)), ('-Y', (0, -1))):
            for hname, hz in (('knee20', 20), ('waist96', 96), ('head180', 180)):
                a = feet + u.Vector(0, 0, hz); b = a + u.Vector(d[0] * 400, d[1] * 400, 0)
                h = guard(line, world, a, b, ignore, 'Pawn')
                if isinstance(h, dict) and 'error' in h: walls[label + '/' + hname] = h; continue
                walls[label + '/' + hname] = None if h is None else dict(distance=h.get('distance'), component=h.get('component'), actorLabel=h.get('actorLabel'),
                                                                        mesh=(h.get('mesh') or {}).get('path'), impactPoint=h.get('impactPoint'))
        row['horizontalPawnProbes400cm'] = walls
    return row
def leg_sweep(world, a, b, ignore):
    A = a + u.Vector(0, 0, LIFT + 2); B = b + u.Vector(0, 0, LIFT + 2)
    hits = hit_rows(unwrap(u.SystemLibrary.capsule_trace_multi_by_profile(world, A, B, RADIUS, HALF, 'Pawn', False, ignore, NODRAW, True)))
    n = max(1, int(math.ceil(math.dist([a.x, a.y, a.z], [b.x, b.y, b.z]) / 100.0)))
    floor_fail = []
    for s in range(n + 1):
        t = s / n; feet = u.Vector(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t)
        ok, h = floor_check(world, feet, ignore)
        if not ok: floor_fail.append(dict(feet=xyz(feet), trace=None if h is None else dict(impactPoint=h.get('impactPoint'), impactNormal=h.get('impactNormal'), mesh=(h.get('mesh') or {}).get('path'), actorLabel=h.get('actorLabel'))))
    blocking = [h for h in hits if h['blocking']]
    first = min(blocking, key=lambda h: h.get('distance') or 0.0) if blocking else None
    return dict(fromFeet=xyz(a), toFeet=xyz(b), lengthCm=round(math.dist([a.x, a.y], [b.x, b.y]), 1), sweepBlocked=bool(blocking),
                firstBlock=None if first is None else dict(distance=first['distance'], initialOverlap=first['initialOverlap'], component=first.get('component'),
                                                            actorLabel=first.get('actorLabel'), mesh=(first.get('mesh') or {}).get('path'), impactPoint=first['impactPoint']),
                floorSamples=n + 1, floorFailures=floor_fail[:12], floorFailureCount=len(floor_fail))
def nearest_clear(world, feet, zone, ignore):
    best = None
    for r in range(25, 425, 25):
        for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r), (r, r), (r, -r), (-r, r), (-r, -r)):
            x, y = feet.x + dx, feet.y + dy
            if not in_zone48(x, y, zone): continue
            f = u.Vector(x, y, feet.z)
            ok, _ = floor_check(world, f, ignore)
            if not ok: continue
            if any(h['blocking'] for h in capsule_hits(world, f + u.Vector(0, 0, LIFT), ignore)): continue
            d = math.hypot(dx, dy)
            if best is None or d < best['distanceCm']: best = dict(feet=[x, y, feet.z], offset=[dx, dy], distanceCm=round(d, 1))
        if best: return best
    return None

state = dict(start=time.monotonic(), phase='world', at=time.monotonic(), stopping=False)
settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse = settings.get_editor_property('GameGetsMouseControl')
def finish(status):
    if state['stopping']: return
    report['status'] = status; state['stopping'] = True; state['at'] = time.monotonic()
    levels.editor_request_end_play(); write()
def run_diagnosis(world):
    ignore = list(u.GameplayStatics.get_all_actors_of_class(world, u.MikdashResidentCharacter))
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    if pawn: ignore.append(pawn)
    report['rhi'] = 'see -abslog LogRHI/LogD3D12RHI lines; -nullrhi refused at startup'
    pops = list(u.GameplayStatics.get_all_actors_of_class(world, u.MikdashResidentPopulation))
    report['piePopulations'] = []
    for p in pops:
        row = dict(name=p.get_name(), living=p.get_living_resident_count(), directoryStatus=p.get_directory_status())
        for fn in ('get_extended_route_status', 'get_status', 'is_extended_route_active', 'is_population_active'):
            try: row[fn] = getattr(p, fn)()
            except Exception: pass
        report['piePopulations'].append(row)
    spawned = {}
    for body in u.GameplayStatics.get_all_actors_of_class(world, u.MikdashResidentCharacter):
        spawned[body.get_actor_label()] = xyz(body.get_actor_location())
    report['spawnedResidentActors'] = spawned
    rows = []
    for person in people['people']:
        pts = decode(person)
        feet = V(pts[0])
        row = dict(id=person['id'], name=person['name'], role=person['role'], zone=person['zone'],
                   legacyWaypoint0=person['route'][0]['at'], selected48Waypoint0=[round(v, 4) for v in pts[0]],
                   previouslyRefused=person['id'] in REFUSED, spawnedThisRun=('Resident_' + person['id']) in spawned)
        row['waypoint0'] = probe_point(world, feet, ignore)
        legs = []
        for i in range(len(pts)):
            legs.append(leg_sweep(world, V(pts[i]), V(pts[(i + 1) % len(pts)]), ignore))
        row['legs'] = legs
        row['legsBlocked'] = sum(1 for l in legs if l['sweepBlocked'])
        row['legsWithFloorFailures'] = sum(1 for l in legs if l['floorFailureCount'])
        if not row['waypoint0']['capsuleClear'] or not row['waypoint0']['floorOk']:
            row['nearestClearSpot'] = guard(nearest_clear, world, feet, person['zone'], ignore)
        rows.append(row); report['residents'] = rows; write()
    pilot = []
    for i, lp in enumerate(PILOT_LEGACY):
        conv = V([lp[0] * RATIO, lp[1] * RATIO, lp[2] * RATIO])
        item = dict(index=i, legacyFeet=lp, selected48Feet=xyz(conv), selected48=probe_point(world, conv, ignore, deep=False),
                    legacyPositionInCandidate=probe_point(world, V(lp), ignore, deep=False))
        step = conv + u.Vector(-80 if i == 3 else 80, 0, 0)
        item['firstPilotLeg'] = leg_sweep(world, conv, step, ignore)
        pilot.append(item)
    report['pilotSupports'] = pilot
    ext = []
    for p in report['editorPopulations']:
        for w in p.get('extendedRouteWaypoints') or []:
            conv = V([w[0] * RATIO, w[1] * RATIO, w[2] * RATIO])
            ext.append(dict(legacy=w, selected48=xyz(conv), probe=probe_point(world, conv, ignore, deep=False)))
    report['extendedRouteWaypointProbes'] = ext
    summary = dict(total=len(rows), capsuleClearAtWaypoint0=sum(1 for r in rows if r['waypoint0']['capsuleClear']),
                   floorOkAtWaypoint0=sum(1 for r in rows if r['waypoint0']['floorOk']), spawnedThisRun=sum(1 for r in rows if r['spawnedThisRun']),
                   refusedIds=[r['id'] for r in rows if not r['spawnedThisRun']],
                   agreementWithSpawner=all(r['spawnedThisRun'] == (r['waypoint0']['capsuleClear']) for r in rows))
    report['summary'] = summary
def tick(dt):
    try:
        now = time.monotonic(); world = ed.get_game_world()
        if state['stopping']:
            if world and now - state['at'] < 15: return
            if world: report['errors'].append('PIE teardown timeout')
            report['pieEnded'] = world is None
            report['mapShaAfter'] = sha(map_file); report['mapBytesUnchanged'] = report['mapShaAfter'] == report['mapShaBefore']
            report['mainBytesUnchanged'] = sha(main_file) == report['mainShaBefore']
            report['saveIsolation']['originalSavesUnchanged'] = user_save_hashes() == original_saves
            if not report['mainBytesUnchanged']: report['errors'].append('Main map bytes changed')
            if not report['saveIsolation']['originalSavesUnchanged']: report['errors'].append('Original save files changed')
            try: settings.set_editor_property('GameGetsMouseControl', old_mouse)
            except Exception as exc: report['errors'].append('Cleanup: ' + repr(exc))
            if report['errors'] or not report['mapBytesUnchanged']: report['status'] = 'failed_cleanup_or_verification'
            try: write()
            finally:
                u.unregister_slate_post_tick_callback(handle); u.SystemLibrary.quit_editor()
            return
        if now - state['start'] > 300: finish('failed_watchdog'); return
        if not world: return
        if state['phase'] == 'world':
            pops = list(u.GameplayStatics.get_all_actors_of_class(world, u.MikdashResidentPopulation))
            ready = any('Directory' in str(p.get_directory_status()) for p in pops)
            if not ready and now - state['at'] < 20: return
            state['phase'] = 'diagnose'; state['at'] = now
            report['populationReadyWaitSeconds'] = round(now - state['start'], 2)
            return
        if state['phase'] == 'diagnose':
            run_diagnosis(world)
            finish('diagnosis_complete_pie_evidence')
    except Exception as exc:
        report['errors'].append(traceback.format_exc())
        if state['stopping']:
            report['status'] = 'failed_cleanup_exception'
            try: write()
            finally:
                u.unregister_slate_post_tick_callback(handle); u.SystemLibrary.quit_editor()
        else: finish('failed_exception')
handle = None
try:
    settings.set_editor_property('GameGetsMouseControl', False)
    write(); handle = u.register_slate_post_tick_callback(tick); levels.editor_request_begin_play()
except Exception as exc:
    report['status'] = 'failed_setup'; report['errors'].append(repr(exc))
    if handle is not None:
        try: u.unregister_slate_post_tick_callback(handle)
        except Exception as cleanup: report['errors'].append('Callback cleanup: ' + repr(cleanup))
    try: settings.set_editor_property('GameGetsMouseControl', old_mouse)
    except Exception: pass
    report['mapBytesUnchanged'] = sha(map_file) == report['mapShaBefore']
    try: write()
    finally: u.SystemLibrary.quit_editor()
    raise

"""Candidate-only resident spawn fix for the isolated 48 cm map. See the .spec.json.

Offline: ``plan()`` builds and validates the candidate people directory (parser-equivalent
rules plus a 48 cm clearance check against the blocker boxes measured in PIE). Nothing is
written.

Native (editor, -ExecCmds): ``run(apply=True)`` checkpoints the candidate .umap, stages
``people-candidate48.json``, repoints ONLY the candidate's RELEASE_PeopleV3Population actor,
moves the five pilot bodies to their converted supports, saves, hashes, reopens, reads back,
then runs PIE and records what actually spawned. Failure receipts are preserved.
"""
import hashlib, importlib.util, json, math, os, re, shutil, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'Scripts/release_candidate_spawn_fix.spec.json').read_text(encoding='utf-8-sig'))
RATIO = 48.0 / 50.0
RADIUS, HALF = 34.0, 96.0
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def disk(package): return ROOT / 'Content' / (package[6:] + '.umap')
def loop_length(pts): return sum(math.dist(pts[i][:2], pts[(i + 1) % len(pts)][:2]) for i in range(len(pts)))
def in_legacy_region(x, y): return 1500 <= x <= 7000 and 900 <= abs(y) < 6000
# PopulationSceneMath.h::TryAuthoredRouteExtension: three unchanged reviewed loops get one
# outward edge moved 25 cm at 48 (indices, delta Y). Their source routes are NOT edited here.
EXT = {'chananel-ben-mattisyahu': (2, 25.0), 'rivka-bas-yoezer': (0, -25.0), 'nechemya-ben-tzuriel': (2, 25.0)}
def decode48(person):
    pts = [[x * RATIO, y * RATIO, z * RATIO] if person['zone'] == 'outer-court' else [x, y, z] for x, y, z in (w['at'] for w in person['route'])]
    if person['id'] in EXT:
        first, dy = EXT[person['id']]; pts[first][1] += dy; pts[first + 1][1] += dy
    return pts

def build_candidate_directory():
    source = ROOT / SPEC['directory']['sourceStaged']
    if sha(source) != SPEC['directory']['sourceSha256']:
        raise RuntimeError('Staged people.json differs from the reviewed hash; refuse to derive a candidate copy')
    data = json.loads(source.read_text(encoding='utf-8-sig'))
    if data['version'] != SPEC['directory']['versionMustStay']:
        raise RuntimeError('Unexpected directory version')
    edits = {k: v for k, v in SPEC['routeEdits'].items() if k != 'note'}
    seen = set()
    for person in data['people']:
        if person['id'] not in edits: continue
        edit = edits[person['id']]
        if len(edit['at']) != len(person['route']): raise RuntimeError('Edit shape differs for ' + person['id'])
        for step, at in zip(person['route'], edit['at']):
            step['at'] = [float(v) for v in at]
        seen.add(person['id'])
    if seen != set(edits): raise RuntimeError('Missing people for edits: %r' % sorted(set(edits) - seen))
    data['note'] = data['note'] + SPEC['directory']['noteSuffix']
    if len(data['note']) > 2000: raise RuntimeError('Note exceeds the parser limit')
    return data

def validate_person(person):
    """Parser-equivalent geometry rules (MikdashPeopleDirectory.h / ResidentRouteLoop.h)."""
    pts = [w['at'] for w in person['route']]
    if not 4 <= len(pts) <= 6: raise RuntimeError(person['id'] + ': 4..6 waypoints')
    for w in person['route']:
        x, y, z = w['at']
        if person['zone'] == 'outer-court':
            if not in_legacy_region(x, y): raise RuntimeError('%s: waypoint outside authored zone %r' % (person['id'], w['at']))
            if abs(z - 300) > 12: raise RuntimeError(person['id'] + ': off floor')
        if not 3 <= w['pause'] <= 5: raise RuntimeError(person['id'] + ': pause')
    for i in range(len(pts)):
        if math.dist(pts[i][:2], pts[(i + 1) % len(pts)][:2]) < 200: raise RuntimeError(person['id'] + ': consecutive waypoints too close')
    legacy = loop_length(pts)
    selected = loop_length(decode48(person))
    if not 6000 <= legacy <= 12000: raise RuntimeError('%s: legacy loop %.1f cm outside 60..120 m' % (person['id'], legacy))
    if not 6000 < selected <= 12000: raise RuntimeError('%s: selected48 loop %.2f cm not strictly inside 60..120 m' % (person['id'], selected))
    return dict(legacyLoopCm=round(legacy, 2), selected48LoopCm=round(selected, 2))

def clearance_at48(person):
    """Every 48 cm waypoint and leg sample must stay >= radius+margin outside each measured blocker box (XY)."""
    boxes = SPEC['clearanceCheckAt48']['measuredBlockerBoxes']
    need = RADIUS + SPEC['clearanceCheckAt48']['minimumMarginBeyondRadiusCm']
    pts = decode48(person)
    worst = None
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n = max(1, int(math.ceil(math.dist(a[:2], b[:2]) / 25.0)))
        for s in range(n + 1):
            t = s / n; x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            for name, box in boxes.items():
                if box['min'][2] >= 288 + 2 * HALF: continue
                dx = max(box['min'][0] - x, 0, x - box['max'][0]); dy = max(box['min'][1] - y, 0, y - box['max'][1])
                d = math.hypot(dx, dy)
                if worst is None or d < worst['distanceCm']: worst = dict(box=name, distanceCm=round(d, 2), at=[round(x, 2), round(y, 2)])
    if worst and worst['distanceCm'] < need:
        raise RuntimeError('%s: only %.1f cm from %s at %r (need %.0f)' % (person['id'], worst['distanceCm'], worst['box'], worst['at'], need))
    return worst

def plan():
    data = build_candidate_directory()
    edits = {k for k in SPEC['routeEdits'] if k != 'note'}
    rows = {}
    for person in data['people']:
        row = validate_person(person)
        if person['id'] in edits:
            row['clearanceAt48'] = clearance_at48(person)
            row['selected48Waypoints'] = [[round(v * RATIO, 3) for v in w['at']] for w in person['route']]
        rows[person['id']] = row
    text = json.dumps(data, indent=1, ensure_ascii=False) + '\n'
    return dict(status='PLAN_ONLY_NO_WRITES', candidateDirectorySha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
                candidateDirectoryText=text, people=rows, edits=sorted(edits), notApplied=SPEC['notApplied'])

# ---------------------------------------------------------------------------------------
def run(*, apply=False):
    planned = plan()
    if not apply:
        return {k: v for k, v in planned.items() if k != 'candidateDirectoryText'}
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT.resolve(): raise RuntimeError('Wrong project directory: refuse native mutation')
    command_line = ue.SystemLibrary.get_command_line()
    assert '-nullrhi' not in command_line.lower(), 'NullRHI is not evidence'
    prefix_match = re.search(r'-TestSavePrefix=((?:AstraProbe|FableProbe)_[A-Za-z0-9_]+)', command_line)
    assert prefix_match, 'Require -TestSavePrefix=FableProbe_<stamp> and Game ini save-slot overrides'
    test_prefix = prefix_match.group(1)
    for section, key, value in [('MikdashSaveSystem', 'SlotNamePrefix', test_prefix), ('MikdashSettingsSubsystem', 'SaveSlot', test_prefix + '_Settings')]:
        assert ('[/Script/MikdashRuntime.' + section + ']:' + key + '=' + value) in command_line, 'Missing save-isolation ini override'
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    MAP = SPEC['candidateMap']; MAIN = SPEC['mainMap']
    map_file = disk(MAP); main_file = disk(MAIN)
    if editor.get_game_world(): raise RuntimeError('Live game: refuse')
    if editor.get_editor_world().get_outermost().get_name() != MAP: raise RuntimeError('Candidate map must be the loaded editor world')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages: refuse')
    save_roots = [ROOT / 'Saved/SaveGames', Path(os.environ['LOCALAPPDATA']) / 'MikdashCourtyardV3/Saved/SaveGames']
    def user_save_hashes():
        return {str(p): sha(p) for folder in save_roots if folder.exists() for p in folder.glob('*.sav')
                if not (p.name.startswith('AstraProbe_') or p.name.startswith('FableProbe_'))}
    original_saves = user_save_hashes()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_path = ROOT / SPEC['receiptFolder'] / (SPEC['receiptPrefix'] + stamp + '.json')
    receipt = dict(status='starting', candidateMap=MAP, mapBeforeSha256=sha(map_file), mainBeforeSha256=sha(main_file),
                   spec=str(ROOT / 'Scripts/release_candidate_spawn_fix.spec.json'), evidenceReceipt=SPEC['evidenceReceipt'],
                   edits=planned['edits'], people=planned['people'], notApplied=planned['notApplied'], errors=[],
                   saveIsolation=dict(testPrefix=test_prefix, originalSaveFileCount=len(original_saves)))
    def write(): receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    if receipt['mapBeforeSha256'] != SPEC['expectedCandidateMapSha256Before']:
        receipt.update(status='failed_before_map_change', failure='Candidate map hash differs from the handoff/spec; inspect before applying'); write()
        raise RuntimeError(receipt['failure'])
    helper_path = ROOT / 'Scripts/release_resident_crowd.py'
    module_spec = importlib.util.spec_from_file_location('spawnfix_scene_snapshot', helper_path)
    helper = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(helper)
    def find_label(label):
        found = [a for a in actors.get_all_level_actors() if a.get_actor_label() == label]
        if len(found) != 1: raise RuntimeError('Expected exactly one actor labelled %s, found %d' % (label, len(found)))
        return found[0]
    xyz = lambda v: [round(v.x, 3), round(v.y, 3), round(v.z, 3)]
    try:
        # ---- checkpoint -----------------------------------------------------------------
        checkpoint = Path(SPEC['checkpointRoot']) / (SPEC['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'BeforeSpawnFix.umap')
        shutil.copy2(ROOT / SPEC['directory']['sourceStaged'], checkpoint / 'people.json')
        if sha(checkpoint / 'BeforeSpawnFix.umap') != receipt['mapBeforeSha256']: raise RuntimeError('Checkpoint copy mismatch')
        receipt['checkpoint'] = str(checkpoint); write()
        baseline = helper._scene_snapshot(ue, actors)
        # ---- stage candidate directory ------------------------------------------------
        staged = ROOT / SPEC['directory']['candidateStaged']
        if staged.exists():
            shutil.copy2(staged, checkpoint / 'people-candidate48.previous.json')
        staged.write_bytes(planned['candidateDirectoryText'].encode('utf-8'))  # bytes: no CRLF translation, hash must match plan
        if sha(staged) != planned['candidateDirectorySha256']: raise RuntimeError('Staged candidate directory hash mismatch')
        receipt['candidateDirectory'] = dict(path=str(staged), sha256=planned['candidateDirectorySha256'])
        # ---- repoint the candidate population actor ----------------------------------
        conf = SPEC['populationActor']
        owner = find_label(conf['label'])
        before_prop = str(owner.get_editor_property(conf['property']))
        if before_prop != conf['expectedBefore']: raise RuntimeError('Population actor already repointed: %s' % before_prop)
        if not bool(owner.get_editor_property('spawn_authored_people_on_begin_play')): raise RuntimeError('Wrong population actor (not the people-v3 spawner)')
        owner.modify(True)
        owner.set_editor_property(conf['property'], SPEC['directory']['candidateRelativeToContent'])
        receipt['populationActor'] = dict(name=owner.get_name(), label=conf['label'], before=before_prop, after=str(owner.get_editor_property(conf['property'])))
        # ---- move the five pilot bodies to converted supports -------------------------
        pilot = SPEC['pilotBodies']; moved = []
        for label, legacy in zip(pilot['labels'], pilot['legacyFeetCm']):
            body = find_label(label)
            cap = body.get_component_by_class(ue.CapsuleComponent)
            if cap is None or abs(cap.get_scaled_capsule_half_height() - 96) > .01 or abs(cap.get_scaled_capsule_radius() - 34) > .01:
                raise RuntimeError(label + ': capsule is not the physical 34 x 96')
            loc = body.get_actor_location(); pose = helper._pose(body)
            expected_actor = [legacy[0], legacy[1], legacy[2] + pilot['capsuleHalfHeightCm']]
            if max(abs(loc.x - expected_actor[0]), abs(loc.y - expected_actor[1]), abs(loc.z - expected_actor[2])) > 0.01:
                raise RuntimeError('%s is not at its legacy support %r (actor %r); refuse possible double conversion' % (label, expected_actor, xyz(loc)))
            if any(abs(s - 1) > 1e-4 for s in pose[6:9]): raise RuntimeError(label + ': body scale is not 1')
            target = ue.Vector(legacy[0] * RATIO, legacy[1] * RATIO, legacy[2] * RATIO + pilot['capsuleHalfHeightCm'])
            body.modify(True)
            body.set_actor_location(target, False, True)
            after = body.get_actor_location()
            if max(abs(after.x - target.x), abs(after.y - target.y), abs(after.z - target.z)) > 0.01: raise RuntimeError(label + ': move did not take effect')
            moved.append(dict(label=label, name=body.get_name(), before=xyz(loc), after=xyz(after), feetAfter=[round(after.x, 3), round(after.y, 3), round(after.z - 96, 3)]))
        receipt['pilotBodies'] = moved
        expected_changed = {owner.get_name()} | {m['name'] for m in moved}
        after_snapshot = helper._scene_snapshot(ue, actors)
        changed = {k for k in set(baseline) | set(after_snapshot) if baseline.get(k) != after_snapshot.get(k)}
        if changed - expected_changed: raise RuntimeError('Unexpected scene changes: %r' % sorted(changed - expected_changed)[:20])
        receipt['sceneChanges'] = sorted(changed); write()
        # ---- save, hash, reopen, read back ----------------------------------------------
        if not levels.save_current_level(): raise RuntimeError('Level save failed')
        receipt.update(mapSaved=True, mapAfterSha256=sha(map_file), status='saved_reopen_pending'); write()
        if not levels.load_level(MAP) or editor.get_editor_world().get_outermost().get_name() != MAP: raise RuntimeError('Reopen failed')
        owner = find_label(conf['label'])
        readback = dict(directoryFile=str(owner.get_editor_property(conf['property'])), bodies=[])
        if readback['directoryFile'] != SPEC['directory']['candidateRelativeToContent']: raise RuntimeError('Readback: directory file not persisted')
        for m in moved:
            body = find_label(m['label']); loc = body.get_actor_location()
            if max(abs(loc.x - m['after'][0]), abs(loc.y - m['after'][1]), abs(loc.z - m['after'][2])) > 0.01: raise RuntimeError(m['label'] + ': moved pose not persisted')
            readback['bodies'].append(dict(label=m['label'], location=xyz(loc)))
        receipt['readback'] = readback
        receipt['mainAfterSha256'] = sha(main_file); receipt['mainUnchanged'] = receipt['mainAfterSha256'] == receipt['mainBeforeSha256']
        if not receipt['mainUnchanged']: raise RuntimeError('Main map bytes changed')
        receipt['status'] = 'saved_reopened_pie_pending'; write()
    except Exception as exc:
        receipt.update(status='failed_checkpoint_available' if receipt.get('checkpoint') else 'failed_before_map_change', failure=repr(exc), traceback=traceback.format_exc())
        write(); ue.SystemLibrary.quit_editor(); raise

    # ---- PIE spawn test in the same process -----------------------------------------------
    people = json.loads((ROOT / SPEC['directory']['candidateStaged']).read_text(encoding='utf-8-sig'))
    decode = decode48
    NODRAW = ue.DrawDebugTrace.NONE; VIS = ue.TraceTypeQuery.TRACE_TYPE_QUERY1
    def unwrap(r):
        if r is None: return []
        if isinstance(r, tuple): r = r[-1]
        return list(r) if r is not None else []
    def hit_row(h):
        d = {str(k).lower().replace('_', ''): v for k, v in h.to_dict().items()}
        comp = d.get('hitcomponent'); owner_actor = comp.get_owner() if comp else None
        ip = d.get('impactpoint'); n = d.get('impactnormal')
        return dict(blocking=bool(d.get('blockinghit', True)), initialOverlap=bool(d.get('initialoverlap', False)), distance=round(float(d.get('distance') or 0), 3),
                    impactPoint=xyz(ip) if ip is not None else None, impactNormal=xyz(n) if n is not None else None,
                    component=comp.get_name() if comp else None, actorLabel=owner_actor.get_actor_label() if owner_actor else None)
    def is_floor(h, feet): return h['impactPoint'] is not None and h['impactNormal'] is not None and h['impactNormal'][2] > 0.9 and abs(h['impactPoint'][2] - feet.z) <= 2.0
    def capsule_blockers(world, feet, ignore):
        c = feet + ue.Vector(0, 0, HALF)
        hits = [hit_row(h) for h in unwrap(ue.SystemLibrary.capsule_trace_multi_by_profile(world, c + ue.Vector(0, 0, .5), c - ue.Vector(0, 0, .5), RADIUS, HALF, 'Pawn', False, ignore, NODRAW, True))]
        return [h for h in hits if h['blocking'] and not is_floor(h, feet)]
    def floor_ok(world, feet, ignore):
        h = ue.SystemLibrary.line_trace_single(world, feet + ue.Vector(0, 0, 30), feet - ue.Vector(0, 0, 30), VIS, False, ignore, NODRAW, True)
        if isinstance(h, tuple): h = h[-1]
        if h is None: return False, None
        r = hit_row(h)
        return bool(r['blocking'] and r['impactPoint'] and abs(r['impactPoint'][2] - feet.z) <= 3 and r['impactNormal'][2] >= .95), r
    def leg(world, a, b, ignore):
        A = a + ue.Vector(0, 0, HALF + 2); B = b + ue.Vector(0, 0, HALF + 2)
        hits = [hit_row(h) for h in unwrap(ue.SystemLibrary.capsule_trace_multi_by_profile(world, A, B, RADIUS, HALF, 'Pawn', False, ignore, NODRAW, True))]
        blocking = [h for h in hits if h['blocking']]
        n = max(1, int(math.ceil(math.dist([a.x, a.y], [b.x, b.y]) / 100.0))); fails = 0
        for s in range(n + 1):
            t = s / n
            if not floor_ok(world, ue.Vector(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z), ignore)[0]: fails += 1
        first = min(blocking, key=lambda h: h['distance']) if blocking else None
        return dict(fromFeet=xyz(a), toFeet=xyz(b), sweepBlocked=bool(blocking), firstBlock=first, floorFailures=fails, floorSamples=n + 1)
    state = dict(start=time.monotonic(), phase='world', at=time.monotonic(), stopping=False)
    settings = ue.get_default_object(ue.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
    old_mouse = settings.get_editor_property('GameGetsMouseControl')
    def finish(status):
        if state['stopping']: return
        receipt['status'] = status; state['stopping'] = True; state['at'] = time.monotonic()
        levels.editor_request_end_play(); write()
    def pie_test(world):
        ignore = list(ue.GameplayStatics.get_all_actors_of_class(world, ue.MikdashResidentCharacter))
        pawn = ue.GameplayStatics.get_player_pawn(world, 0)
        if pawn: ignore.append(pawn)
        pops = []
        for p in ue.GameplayStatics.get_all_actors_of_class(world, ue.MikdashResidentPopulation):
            pops.append(dict(name=p.get_name(), living=p.get_living_resident_count(), directoryStatus=p.get_directory_status(),
                             extendedRouteStatus=p.get_extended_route_status(), active=p.is_population_active()))
        spawned = {b.get_actor_label(): xyz(b.get_actor_location()) for b in ue.GameplayStatics.get_all_actors_of_class(world, ue.MikdashResidentCharacter)}
        rows = []
        for person in people['people']:
            pts = decode(person); feet = ue.Vector(*pts[0])
            row = dict(id=person['id'], edited=person['id'] in planned['edits'], selected48Waypoint0=[round(v, 3) for v in pts[0]],
                       spawned=('Resident_' + person['id']) in spawned, capsuleBlockers=capsule_blockers(world, feet, ignore))
            row['floorOk'], row['floorTrace'] = floor_ok(world, feet, ignore)
            row['legs'] = [leg(world, ue.Vector(*pts[i]), ue.Vector(*pts[(i + 1) % len(pts)]), ignore) for i in range(len(pts))]
            row['legsBlocked'] = sum(1 for l in row['legs'] if l['sweepBlocked']); row['legsWithFloorFailures'] = sum(1 for l in row['legs'] if l['floorFailures'])
            rows.append(row)
        pilot_rows = []
        for m in receipt['pilotBodies']:
            feet = ue.Vector(*m['feetAfter'])
            pilot_rows.append(dict(label=m['label'], feet=m['feetAfter'], liveLocation=spawned.get(m['label']), capsuleBlockers=capsule_blockers(world, feet, ignore), floorOk=floor_ok(world, feet, ignore)[0]))
        receipt['pie'] = dict(populations=pops, spawnedResidentActors=spawned, residents=rows, pilotBodies=pilot_rows,
                              summary=dict(authored=len(rows), spawned=sum(1 for r in rows if r['spawned']), refused=[r['id'] for r in rows if not r['spawned']],
                                           editedSpawned=[r['id'] for r in rows if r['edited'] and r['spawned']], editedRefused=[r['id'] for r in rows if r['edited'] and not r['spawned']],
                                           editedWithAllLegsClear=[r['id'] for r in rows if r['edited'] and r['legsBlocked'] == 0 and r['legsWithFloorFailures'] == 0],
                                           capsuleAgreementWithSpawner=all(r['spawned'] == (not r['capsuleBlockers']) for r in rows)))
    def tick(dt):
        try:
            now = time.monotonic(); world = editor.get_game_world()
            if state['stopping']:
                if world and now - state['at'] < 15: return
                if world: receipt['errors'].append('PIE teardown timeout')
                receipt['pieEnded'] = world is None
                receipt['mapAfterPieSha256'] = sha(map_file); receipt['mapUnchangedByPie'] = receipt['mapAfterPieSha256'] == receipt['mapAfterSha256']
                receipt['mainUnchanged'] = sha(main_file) == receipt['mainBeforeSha256']
                receipt['saveIsolation']['originalSavesUnchanged'] = user_save_hashes() == original_saves
                if not receipt['mainUnchanged']: receipt['errors'].append('Main map bytes changed')
                if not receipt['saveIsolation']['originalSavesUnchanged']: receipt['errors'].append('Original save files changed')
                if not receipt['mapUnchangedByPie']: receipt['errors'].append('Candidate map changed during PIE')
                try: settings.set_editor_property('GameGetsMouseControl', old_mouse)
                except Exception as exc: receipt['errors'].append('Cleanup: ' + repr(exc))
                if receipt['errors']: receipt['status'] = 'applied_but_pie_verification_failed'
                try: write()
                finally:
                    ue.unregister_slate_post_tick_callback(handle); ue.SystemLibrary.quit_editor()
                return
            if now - state['start'] > 300: finish('applied_pie_watchdog_failed'); return
            if not world: return
            if state['phase'] == 'world':
                pops = list(ue.GameplayStatics.get_all_actors_of_class(world, ue.MikdashResidentPopulation))
                if not any('Directory' in str(p.get_directory_status()) for p in pops) and now - state['at'] < 20: return
                state['phase'] = 'test'; return
            if state['phase'] == 'test':
                pie_test(world)
                s = receipt['pie']['summary']
                finish('applied_saved_reopened_pie_observed_%d_of_%d_spawned' % (s['spawned'], s['authored']))
        except Exception:
            receipt['errors'].append(traceback.format_exc())
            if state['stopping']:
                receipt['status'] = 'applied_pie_cleanup_exception'
                try: write()
                finally:
                    ue.unregister_slate_post_tick_callback(handle); ue.SystemLibrary.quit_editor()
            else: finish('applied_pie_exception')
    handle = None
    try:
        settings.set_editor_property('GameGetsMouseControl', False)
        write(); handle = ue.register_slate_post_tick_callback(tick); levels.editor_request_begin_play()
    except Exception as exc:
        receipt['status'] = 'applied_pie_setup_failed'; receipt['errors'].append(repr(exc)); write()
        if handle is not None: ue.unregister_slate_post_tick_callback(handle)
        ue.SystemLibrary.quit_editor(); raise
    return receipt

if __name__ == '__main__':
    native = 'unreal' in sys.modules and '-SpawnFixApply' in __import__('unreal').SystemLibrary.get_command_line()
    try:
        result = run(apply=native)
        print(json.dumps({k: v for k, v in result.items() if k not in ('candidateDirectoryText',)}, indent=2, default=str)[:6000])
    except Exception:
        if native:
            import unreal as _ue
            failure = ROOT / SPEC['receiptFolder'] / (SPEC['receiptPrefix'] + 'setup-failure-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
            failure.write_text(json.dumps(dict(status='failed_before_or_during_apply', error=traceback.format_exc()), indent=2), encoding='utf-8')
            _ue.SystemLibrary.quit_editor()
        raise

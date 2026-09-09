"""Resident bodies V3: the 24 people-v3 residents on the PilgrimRigV3 variants.

Layers on Scripts/release_resident_routes_v2.py: the staged directories are the Routes V2
documents plus one "body": {"variant", "visualScale"} per person from the reviewed casting
(Scripts/release_pilgrim_v3_review.spec.json residentSwap.casting). Asset paths come from the
import marker (review-native-progress.json), never from assumed names.

Offline (bundled UE Python, no engine):
    python Scripts/release_resident_bodies_v3.py --plan     validate casting + marker, print the plan
    python Scripts/release_resident_bodies_v3.py --stage    write both staged files, print the plan

Native apply (commandlet-safe, -nullrhi allowed; strictly serial with other native jobs):
    "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
        "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
        -run=pythonscript -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_resident_bodies_v3.py"
        -BodiesApply -BodiesTarget=Candidate48 -unattended -nullrhi
        -abslog="C:/Mikdash/Working-5.8/Release-ResidentBodiesV3-Candidate48-01.log"
  Requires the FRESH compiled plugin (the population exposes body_variants). Guards, checkpoint
  (target .umap + previous staged JSONs), stages both directories, loads the target map, fills
  RELEASE_PeopleV3Population.body_variants from the marker for the cast variants (skeletal mesh,
  idle/walk clips on the mesh's own skeleton, garment slot, mesh relative yaw), keeps the V2
  default body as the fallback, whole-scene snapshot diff, saves only when the actor changed,
  reopens, reads back every variant, writes a receipt.

PIE verification (real RHI, editor GUI process; the coordinator runs it):
    "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
        "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
        /Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough
        -ExecCmds="py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_resident_bodies_v3.py"
        -BodiesVerify -BodiesTarget=Candidate48
        -TestSavePrefix=FableProbe_BodiesV3_01
        -ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FableProbe_BodiesV3_01,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FableProbe_BodiesV3_01_Settings
        -unattended -NoSplash -abslog="C:\\Mikdash\\Working-5.8\\Fable-BodiesV3-Candidate48-01.log"
  Per resident: which skeletal mesh actually spawned vs the cast variant, component relative
  scale / yaw / location, capsule 34/96 and actor scale 1, ball_r/ball_l world Z vs the floor
  (min over a 16 s sample window, so walk contact frames are included), head bone Z vs floor +
  166 x scale, toes ahead of the pelvis along the actor forward, walkers moving toward their
  toes, garment slot material readback, spawned/skipped with the log reason, leg sweeps,
  displacement between two samples, and the average frame time over the window. Nothing saved.
"""
import hashlib, importlib.util, json, math, os, re, shutil, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'Scripts/release_resident_bodies_v3.spec.json'
SPEC = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
if Path(SPEC['projectDir']).resolve() != ROOT:
    raise RuntimeError('Spec project directory differs from the script root')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp_now(): return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

def _load_routes():
    spec = importlib.util.spec_from_file_location('release_resident_routes_v2', ROOT / SPEC['routesLayer'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module
ROUTES = _load_routes()
TARGETS = ROUTES.SPEC['targets']
def disk(package): return ROOT / 'Content' / (package[6:] + '.umap')

# ---------------------------------------------------------------------------------------
# Casting and import marker.
# ---------------------------------------------------------------------------------------
def casting():
    src = SPEC['castingSource']
    review = json.loads((ROOT / src['spec']).read_text(encoding='utf-8-sig'))
    cast = review['residentSwap']['casting']
    rendered = json.loads((ROOT / src['renderedPlan']).read_text(encoding='utf-8-sig'))
    by_id = {r['id']: r for r in rendered['residents']}
    for pid, c in cast.items():
        r = by_id.get(pid)
        if not r or r['variant'] != c['variant'] or abs(r['visualComponentScale'] - c['scale']) > 1e-9:
            raise RuntimeError('Rendered swap plan disagrees with the spec casting for ' + pid)
    return cast

def marker():
    m = json.loads((ROOT / SPEC['importMarker']).read_text(encoding='utf-8-sig'))
    if m.get('namespace') != SPEC['expectedNamespace']: raise RuntimeError('Import marker namespace differs from the spec')
    return m['completed']

def _object_path(path):
    """Import markers store package paths; native readback returns object paths."""
    if path is None or '.' in path.rsplit('/', 1)[-1]:
        return path
    return path + '.' + path.rsplit('/', 1)[-1]


def variant_assets(name):
    """Resolved asset set for one imported variant, from the marker only."""
    entry = marker().get(name)
    if not entry: raise RuntimeError('Variant %s is not listed as imported in the marker' % name)
    clips = {}
    for role, suffix in SPEC['clipSuffixes'].items():
        found = [a for a in entry['animations'] if a.endswith(suffix)]
        if len(found) != 1: raise RuntimeError('%s: expected exactly one clip ending %s, found %r' % (name, suffix, found))
        clips[role] = found[0]
    slot = SPEC['garmentSlotByVariant'].get(name, SPEC['garmentSlotByVariant']['default'])
    slots = [s['slot'] for s in entry['materialSlots']]
    if slot not in slots: raise RuntimeError('%s: garment slot %s not among imported slots %r' % (name, slot, slots))
    facing = entry['facing']
    if facing['meshFacesUE'] != SPEC['expectedFacing'] or abs(float(facing['relativeYawForActorForwardX']) - SPEC['expectedMeshRelativeYaw']) > 1e-9:
        raise RuntimeError('%s: receipt facing %r disagrees with the spec expectation' % (name, facing))
    return dict(id=name, skeletalMesh=_object_path(entry['skeletalMesh']), skeleton=_object_path(entry['skeleton']), idle=_object_path(clips['idle']), walk=_object_path(clips['walk']),
                garmentSlot=slot, meshRelativeYaw=float(facing['relativeYawForActorForwardX']), receipt=entry['receipt'])

# ---------------------------------------------------------------------------------------
# Directory composition: Routes V2 + body per person.
# ---------------------------------------------------------------------------------------
def build_directory(target_key):
    data = ROUTES.build_directory(target_key)
    cast = casting(); lo, hi = SPEC['reviewedScaleRange']
    for person in data['people']:
        c = cast.get(person['id'])
        if not c: raise RuntimeError('No casting for ' + person['id'])
        if not lo <= c['scale'] <= hi: raise RuntimeError('%s: scale %r outside %r' % (person['id'], c['scale'], SPEC['reviewedScaleRange']))
        person['body'] = dict(variant=c['variant'], visualScale=float(c['scale']))
    data['note'] = data['note'] + SPEC['targets'][target_key]['noteSuffix']
    if len(data['note']) > 2000: raise RuntimeError('Note exceeds the parser limit')
    return data

def plan():
    cast = casting(); completed = marker()
    result = dict(status='PLAN_ONLY_NO_WRITES', targets={}, variants={}, residents={}, failures=[])
    variants_used = sorted({c['variant'] for c in cast.values()})
    for v in variants_used:
        try: result['variants'][v] = variant_assets(v)
        except Exception as exc: result['failures'].append(repr(exc))
    docs = {}
    for key in TARGETS:
        data = build_directory(key); text = ROUTES.serialize(data); docs[key] = text
        staged = ROOT / TARGETS[key]['staged']
        row = dict(staged=TARGETS[key]['staged'], relativeToContent=TARGETS[key]['relativeToContent'], map=TARGETS[key]['map'], frame=TARGETS[key]['frame'],
                   plannedSha256=hashlib.sha256(text).hexdigest(), stagedExists=staged.exists(), stagedSha256=sha(staged) if staged.exists() else None)
        row['stagedMatchesPlan'] = row['stagedSha256'] == row['plannedSha256']
        result['targets'][key] = row
    people = json.loads(docs['Main50'].decode('utf-8'))['people']
    # Neighbour rules from the swap plan, re-checked against the Routes V2 start points.
    radius = SPEC['castingSource']['neighbourRadiusCm']; gap_min = SPEC['castingSource']['minScaleGapSameVariant']
    scales_by_variant = {}
    for p in people:
        b = p['body']; scales_by_variant.setdefault(b['variant'], []).append(b['visualScale'])
        result['residents'][p['id']] = dict(role=p['role'], zone=p['zone'], variant=b['variant'], visualScale=b['visualScale'],
                                            garmentSlot=SPEC['garmentSlotByVariant'].get(b['variant'], SPEC['garmentSlotByVariant']['default']),
                                            start=p['route'][0]['at'], imported=b['variant'] in completed)
        if b['variant'] not in completed: result['failures'].append(p['id'] + ': variant not imported')
    for v, scales in scales_by_variant.items():
        if len(scales) != len(set(scales)): result['failures'].append('duplicate scale inside ' + v)
    pairs = 0
    for i, a in enumerate(people):
        for b in people[i + 1:]:
            d = math.hypot(a['route'][0]['at'][0] - b['route'][0]['at'][0], a['route'][0]['at'][1] - b['route'][0]['at'][1])
            if d > radius: continue
            pairs += 1
            gap = abs(a['body']['visualScale'] - b['body']['visualScale'])
            if gap < 1e-9: result['failures'].append('neighbours share a scale: %s / %s' % (a['id'], b['id']))
            if a['body']['variant'] == b['body']['variant'] and gap < gap_min - 1e-9:
                result['failures'].append('neighbours share variant %s with gap %.2f: %s / %s' % (a['body']['variant'], gap, a['id'], b['id']))
    result['neighbourPairsChecked'] = pairs
    result['variantUse'] = {v: len(s) for v, s in sorted(scales_by_variant.items())}
    result['offlineOk'] = not result['failures']
    result['_documents'] = docs
    return result

def stage(planned=None):
    planned = planned or plan()
    if not planned['offlineOk']: raise RuntimeError('Offline plan has failures; nothing staged: %r' % planned['failures'])
    written = {}
    for key in TARGETS:
        staged = ROOT / TARGETS[key]['staged']; staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(planned['_documents'][key])
        if sha(staged) != planned['targets'][key]['plannedSha256']: raise RuntimeError('Staged hash mismatch for ' + key)
        written[key] = dict(path=str(staged), sha256=planned['targets'][key]['plannedSha256'])
    return written

def public(planned): return {k: v for k, v in planned.items() if k != '_documents'}

# ---------------------------------------------------------------------------------------
# Native helpers.
# ---------------------------------------------------------------------------------------
def _target_from_command_line(command_line):
    m = re.search(r'-BodiesTarget=(Main50|Candidate48)', command_line)
    if not m: raise RuntimeError('Pass -BodiesTarget=Main50 or -BodiesTarget=Candidate48')
    return m.group(1)

def _receipt_path(kind, stamp):
    folder = ROOT / SPEC['receiptFolder']; folder.mkdir(parents=True, exist_ok=True)
    return folder / (SPEC['receiptPrefix'] + kind + '-' + stamp + '.json')

def _find_label(actors, label):
    found = [a for a in actors.get_all_level_actors() if a.get_actor_label() == label]
    if len(found) != 1: raise RuntimeError('Expected exactly one actor labelled %s, found %d' % (label, len(found)))
    return found[0]

def _path(obj):
    return obj.get_path_name() if obj is not None else None

def run_apply(target_key):
    import unreal as ue
    target = TARGETS[target_key]
    if Path(ue.Paths.project_dir()).resolve() != ROOT.resolve(): raise RuntimeError('Wrong project directory: refuse native mutation')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    if editor.get_game_world(): raise RuntimeError('Live game: refuse')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages: refuse')
    if not hasattr(ue, 'MikdashResidentBodyVariant'):
        raise RuntimeError('Compiled plugin does not expose MikdashResidentBodyVariant: rebuild before applying')
    MAP = target['map']; map_file = disk(MAP)
    others = {k: disk(v['map']) for k, v in TARGETS.items() if k != target_key}
    stamp = stamp_now(); receipt_path = _receipt_path('apply-' + target_key, stamp)
    planned = plan()
    receipt = dict(status='starting', mode='apply', target=target_key, map=MAP, mapBeforeSha256=sha(map_file),
                   otherMapsBefore={k: sha(v) for k, v in others.items()}, spec=str(SPEC_PATH), plan=public(planned), errors=[])
    def write(): receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    if not planned['offlineOk']:
        receipt.update(status='failed_offline_plan', failure=repr(planned['failures'])); write(); raise RuntimeError(receipt['failure'])
    try:
        checkpoint = Path(SPEC['checkpointRoot']) / (SPEC['checkpointPrefix'] + target_key + '-' + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'BeforeBodiesV3.umap')
        if sha(checkpoint / 'BeforeBodiesV3.umap') != receipt['mapBeforeSha256']: raise RuntimeError('Checkpoint copy mismatch')
        for key, t in TARGETS.items():
            staged = ROOT / t['staged']
            if staged.exists(): shutil.copy2(staged, checkpoint / (Path(t['staged']).name.replace('.json', '.previous.json')))
        receipt['checkpoint'] = str(checkpoint); write()
        receipt['staged'] = stage(planned); write()
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            if not levels.load_level(MAP): raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != MAP: raise RuntimeError('Unexpected editor world')
        helper_spec = importlib.util.spec_from_file_location('bodiesv3_scene_snapshot', ROOT / 'Scripts/release_resident_crowd.py')
        helper = importlib.util.module_from_spec(helper_spec); helper_spec.loader.exec_module(helper)
        baseline = helper._scene_snapshot(ue, actors)
        owner = _find_label(actors, target['populationActorLabel'])
        if not bool(owner.get_editor_property('spawn_authored_people_on_begin_play')): raise RuntimeError('Wrong population actor (not the people-v3 spawner)')
        if str(owner.get_editor_property('people_directory_file')) != target['relativeToContent']:
            raise RuntimeError('Population actor points at %r, not the target file; run the Routes V2 apply first' % str(owner.get_editor_property('people_directory_file')))
        # Default (V2) body must be present as the fallback.
        fallback = dict(mesh=_path(owner.get_editor_property('resident_mesh')), idle=_path(owner.get_editor_property('idle_animation')),
                        walk=_path(owner.get_editor_property('walk_animation')), slots=[str(n) for n in owner.get_editor_property('garment_material_slots')],
                        yaw=float(owner.get_editor_property('default_mesh_relative_yaw')))
        if not (fallback['mesh'] and fallback['idle'] and fallback['walk']): raise RuntimeError('Default body incomplete on the actor: %r' % fallback)
        receipt['defaultBody'] = fallback
        # Build the variant array from the marker: load, type-check, skeleton-check, read back.
        structs, planned_rows = [], []
        for name, va in sorted(planned['variants'].items()):
            mesh = ue.load_asset(va['skeletalMesh']); idle = ue.load_asset(va['idle']); walk = ue.load_asset(va['walk'])
            if not isinstance(mesh, ue.SkeletalMesh): raise RuntimeError('%s: skeletal mesh missing or wrong class at %s' % (name, va['skeletalMesh']))
            for clip, label in ((idle, va['idle']), (walk, va['walk'])):
                if not isinstance(clip, ue.AnimSequence): raise RuntimeError('%s: clip missing or wrong class at %s' % (name, label))
            skel = mesh.get_editor_property('skeleton')
            if skel is None or _path(skel) != va['skeleton']: raise RuntimeError('%s: mesh skeleton %r differs from the marker %r' % (name, _path(skel), va['skeleton']))
            for clip in (idle, walk):
                if _path(clip.get_editor_property('skeleton')) != va['skeleton']: raise RuntimeError('%s: clip %s is not on the mesh skeleton' % (name, _path(clip)))
            slot_names = [str(m.get_editor_property('material_slot_name')) for m in mesh.get_editor_property('materials')]
            if va['garmentSlot'] not in slot_names: raise RuntimeError('%s: garment slot %s not on the loaded mesh %r' % (name, va['garmentSlot'], slot_names))
            s = ue.MikdashResidentBodyVariant()
            s.set_editor_property('id', name)
            s.set_editor_property('skeletal_mesh', mesh)
            s.set_editor_property('idle_animation', idle)
            s.set_editor_property('walk_animation', walk)
            s.set_editor_property('garment_material_slots', [ue.Name(va['garmentSlot'])])
            s.set_editor_property('mesh_relative_yaw', va['meshRelativeYaw'])
            structs.append(s)
            planned_rows.append(dict(id=name, skeletalMesh=va['skeletalMesh'], idle=va['idle'], walk=va['walk'], garmentSlots=[va['garmentSlot']], meshRelativeYaw=va['meshRelativeYaw']))
        def read_variants(actor):
            rows = []
            for s in actor.get_editor_property('body_variants'):
                rows.append(dict(id=str(s.get_editor_property('id')), skeletalMesh=_path(s.get_editor_property('skeletal_mesh')),
                                 idle=_path(s.get_editor_property('idle_animation')), walk=_path(s.get_editor_property('walk_animation')),
                                 garmentSlots=[str(n) for n in s.get_editor_property('garment_material_slots')],
                                 meshRelativeYaw=float(s.get_editor_property('mesh_relative_yaw'))))
            return rows
        before_rows = read_variants(owner)
        changed_needed = before_rows != planned_rows
        receipt['bodyVariantsBefore'] = before_rows
        if changed_needed:
            owner.modify(True)
            owner.set_editor_property('body_variants', structs)
        after_rows = read_variants(owner)
        if after_rows != planned_rows: raise RuntimeError('body_variants did not read back as planned: %r' % after_rows)
        after = helper._scene_snapshot(ue, actors)
        changed = {k for k in set(baseline) | set(after) if baseline.get(k) != after.get(k)}
        allowed = {owner.get_name()} if changed_needed else set()
        if changed - allowed: raise RuntimeError('Unexpected scene changes: %r' % sorted(changed - allowed)[:20])
        receipt['sceneChanges'] = sorted(changed)
        if changed_needed:
            if not levels.save_current_level(): raise RuntimeError('Level save failed')
            receipt.update(mapSaved=True, mapAfterSha256=sha(map_file), status='saved_reopen_pending'); write()
            if not levels.load_level(MAP) or editor.get_editor_world().get_outermost().get_name() != MAP: raise RuntimeError('Reopen failed')
            owner = _find_label(actors, target['populationActorLabel'])
        else:
            receipt.update(mapSaved=False, mapAfterSha256=sha(map_file), status='no_map_change_needed'); write()
        readback = read_variants(owner)
        if readback != planned_rows: raise RuntimeError('Readback after reopen differs from the plan')
        receipt['readback'] = dict(bodyVariants=readback, directoryFile=str(owner.get_editor_property('people_directory_file')),
                                   defaultMesh=_path(owner.get_editor_property('resident_mesh')))
        receipt['otherMapsUnchanged'] = all(sha(v) == receipt['otherMapsBefore'][k] for k, v in others.items())
        if not receipt['otherMapsUnchanged']: raise RuntimeError('Another map changed bytes during the apply')
        for key, t in TARGETS.items():
            if sha(ROOT / t['staged']) != planned['targets'][key]['plannedSha256']: raise RuntimeError('Staged file changed during the run: ' + key)
        receipt['mapBytesChanged'] = receipt['mapAfterSha256'] != receipt['mapBeforeSha256']
        receipt['status'] = ('applied_saved_reopened' if changed_needed else 'staged_variants_already_registered_map_untouched') + '_pie_verification_pending'
    except Exception as exc:
        receipt.update(status='failed_checkpoint_available' if receipt.get('checkpoint') else 'failed_before_map_change', failure=repr(exc), traceback=traceback.format_exc())
        write(); raise
    finally:
        write(); ue.log(json.dumps({k: v for k, v in receipt.items() if k != 'plan'}, indent=2, default=str))
    return receipt

def run_verify(target_key):
    import unreal as u
    target = TARGETS[target_key]; V = SPEC['verify']; B = SPEC['bones']; REST = SPEC['restCm']
    ratio, floor_z = float(target['ratio']), float(target['floorZ'])
    ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors_sub = u.get_editor_subsystem(u.EditorActorSubsystem)
    command_line = u.SystemLibrary.get_command_line()
    if '-nullrhi' in command_line.lower(): raise RuntimeError('NullRHI traces are not evidence')
    if ed.get_game_world() is not None: raise RuntimeError('A game world is already running')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages(): raise RuntimeError('Dirty packages: refuse')
    MAP = target['map']
    if ed.get_editor_world().get_outermost().get_name() != MAP: raise RuntimeError('Target map %s must be the loaded editor world' % MAP)
    test_prefix = ROUTES._save_isolation(command_line)
    map_file = disk(MAP); others = {k: disk(v['map']) for k, v in TARGETS.items() if k != target_key}
    original_saves = ROUTES._user_save_hashes()
    staged = ROOT / target['staged']
    people = json.loads(staged.read_text(encoding='utf-8-sig'))
    stamp = stamp_now(); out = _receipt_path('verify-' + target_key, stamp)
    abslog = re.search(r'-abslog=("?)([^"]+)\1', command_line)
    report = dict(status='starting', mode='verify', target=target_key, map=MAP, frame=target['frame'], ratio=ratio, floorZ=floor_z, mapShaBefore=sha(map_file),
                  otherMapsBefore={k: sha(v) for k, v in others.items()}, stagedDirectory=dict(path=str(staged), sha256=sha(staged)), errors=[],
                  scope='Real-RHI PIE: body identity, component pose, bone heights over a sample window, capsule invariants, garment readback, spawn accounting, legs, motion, frame time; no map writes; not visual acceptance',
                  commandLine=command_line, abslog=abslog.group(2) if abslog else None, saveIsolation=dict(testPrefix=test_prefix, originalSaveFileCount=len(original_saves)))
    def write(): out.write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')
    def xyz(v): return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]
    pops = [a for a in actors_sub.get_all_level_actors() if isinstance(a, u.MikdashResidentPopulation)]
    rows = []
    for pop in pops:
        row = dict(name=pop.get_name(), label=pop.get_actor_label())
        for key in ('spawn_authored_people_on_begin_play', 'people_directory_file', 'source_coordinate_revision', 'default_mesh_relative_yaw'):
            try: row[key] = str(pop.get_editor_property(key))
            except Exception as exc: row[key] = 'unavailable: ' + repr(exc)
        try:
            row['bodyVariants'] = [dict(id=str(s.get_editor_property('id')), skeletalMesh=_path(s.get_editor_property('skeletal_mesh')),
                                        meshRelativeYaw=float(s.get_editor_property('mesh_relative_yaw')),
                                        garmentSlots=[str(n) for n in s.get_editor_property('garment_material_slots')])
                                   for s in pop.get_editor_property('body_variants')]
        except Exception as exc: row['bodyVariants'] = 'unavailable: ' + repr(exc)
        rows.append(row)
    report['editorPopulations'] = rows
    write()
    NODRAW = u.DrawDebugTrace.NONE; VIS = u.TraceTypeQuery.TRACE_TYPE_QUERY1
    RADIUS, HALF = ROUTES.RADIUS, ROUTES.HALF
    def unwrap(r):
        if r is None: return []
        if isinstance(r, tuple): r = r[-1]
        return list(r) if r is not None else []
    def hit_row(h):
        d = {str(k).lower().replace('_', ''): v for k, v in h.to_dict().items()}
        comp = d.get('hitcomponent'); owner_actor = comp.get_owner() if comp else None
        ip = d.get('impactpoint'); n = d.get('impactnormal')
        return dict(blocking=bool(d.get('blockinghit', True)), distance=round(float(d.get('distance') or 0), 3),
                    impactPoint=xyz(ip) if ip is not None else None, impactNormal=xyz(n) if n is not None else None,
                    component=comp.get_name() if comp else None, actorLabel=owner_actor.get_actor_label() if owner_actor else None)
    def is_floor(h, feet): return h['impactPoint'] is not None and h['impactNormal'] is not None and h['impactNormal'][2] > 0.9 and abs(h['impactPoint'][2] - feet.z) <= 2.0
    def capsule_blockers(world, feet, ignore):
        c = feet + u.Vector(0, 0, HALF)
        hits = [hit_row(h) for h in unwrap(u.SystemLibrary.capsule_trace_multi_by_profile(world, c + u.Vector(0, 0, .5), c - u.Vector(0, 0, .5), RADIUS, HALF, 'Pawn', False, ignore, NODRAW, True))]
        return [h for h in hits if h['blocking'] and not is_floor(h, feet)]
    def floor_ok(world, feet, ignore):
        h = u.SystemLibrary.line_trace_single(world, feet + u.Vector(0, 0, 30), feet - u.Vector(0, 0, 30), VIS, False, ignore, NODRAW, True)
        if isinstance(h, tuple): h = h[-1]
        if h is None: return False, None
        r = hit_row(h)
        return bool(r['blocking'] and r['impactPoint'] and abs(r['impactPoint'][2] - feet.z) <= 3 and r['impactNormal'][2] >= .95), r
    def leg(world, a, b, ignore):
        A = a + u.Vector(0, 0, HALF + 2); Bv = b + u.Vector(0, 0, HALF + 2)
        hits = [hit_row(h) for h in unwrap(u.SystemLibrary.capsule_trace_multi_by_profile(world, A, Bv, RADIUS, HALF, 'Pawn', False, ignore, NODRAW, True))]
        blocking = [h for h in hits if h['blocking']]
        n = max(1, int(math.ceil(math.dist([a.x, a.y], [b.x, b.y]) / 100.0))); fails = 0
        for s in range(n + 1):
            t = s / n
            if not floor_ok(world, u.Vector(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z), ignore)[0]: fails += 1
        first = min(blocking, key=lambda h: h['distance']) if blocking else None
        return dict(fromFeet=xyz(a), toFeet=xyz(b), sweepBlocked=bool(blocking), firstBlock=first, floorSamples=n + 1, floorFailureCount=fails)
    state = dict(start=time.monotonic(), phase='world', at=time.monotonic(), stopping=False, motion={}, bones={}, frames=0, frameStart=None, nextBone=0.0)
    settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
    old_mouse = settings.get_editor_property('GameGetsMouseControl')
    def finish(status):
        if state['stopping']: return
        report['status'] = status; state['stopping'] = True; state['at'] = time.monotonic()
        levels.editor_request_end_play(); write()
    def resident_bodies(world):
        return {b.get_actor_label(): b for b in u.GameplayStatics.get_all_actors_of_class(world, u.MikdashResidentCharacter)}
    def sample_bones(world):
        for label, body in resident_bodies(world).items():
            mesh = body.get_component_by_class(u.SkeletalMeshComponent)
            if mesh is None: continue
            rec = state['bones'].setdefault(label, dict(samples=0, ballMinZ=None, ballMaxZ=None, headMinZ=None, headMaxZ=None, toesAheadSamples=0, movingSamples=0, movingTowardToesSamples=0))
            try:
                br = mesh.get_socket_location(u.Name(B['ballRight'])); bl = mesh.get_socket_location(u.Name(B['ballLeft']))
                head = mesh.get_socket_location(u.Name(B['head'])); pelvis = mesh.get_socket_location(u.Name(B['pelvis']))
            except Exception as exc:
                rec['error'] = repr(exc); continue
            ball = min(br.z, bl.z)
            rec['samples'] += 1
            rec['ballMinZ'] = ball if rec['ballMinZ'] is None else min(rec['ballMinZ'], ball)
            rec['ballMaxZ'] = max(br.z, bl.z) if rec['ballMaxZ'] is None else max(rec['ballMaxZ'], br.z, bl.z)
            rec['headMinZ'] = head.z if rec['headMinZ'] is None else min(rec['headMinZ'], head.z)
            rec['headMaxZ'] = head.z if rec['headMaxZ'] is None else max(rec['headMaxZ'], head.z)
            fwd = body.get_actor_forward_vector()
            toes = (br.x - pelvis.x) * fwd.x + (br.y - pelvis.y) * fwd.y
            if toes > 0: rec['toesAheadSamples'] += 1
            vel = body.get_velocity()
            if math.hypot(vel.x, vel.y) > 5.0:
                rec['movingSamples'] += 1
                if vel.x * fwd.x + vel.y * fwd.y > 0: rec['movingTowardToesSamples'] += 1
    def read_log_reasons():
        reasons = {}
        try:
            u.log_flush()
            path = report.get('abslog')
            if not path: return reasons
            for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
                m = re.search(r'MikdashResidentPopulation_\d+: (skipped|note) ([a-z0-9-]+): (.*)$', line)
                if m: reasons.setdefault(m.group(2), []).append(m.group(1) + ': ' + m.group(3).strip())
        except Exception as exc:
            report['errors'].append('log read: ' + repr(exc))
        return reasons
    def diagnose(world):
        bodies = resident_bodies(world)
        ignore = list(bodies.values())
        pawn = u.GameplayStatics.get_player_pawn(world, 0)
        if pawn: ignore.append(pawn)
        pop_rows = []
        for p in u.GameplayStatics.get_all_actors_of_class(world, u.MikdashResidentPopulation):
            row = dict(name=p.get_name(), living=p.get_living_resident_count(), directoryStatus=p.get_directory_status(), status=p.get_population_status(), active=p.is_population_active())
            for fn in ('get_variant_body_count', 'get_fallback_body_count', 'get_extended_route_status'):
                try: row[fn] = getattr(p, fn)()
                except Exception as exc: row[fn] = 'unavailable: ' + repr(exc)
            pop_rows.append(row)
        report['piePopulations'] = pop_rows
        log_reasons = read_log_reasons()
        garment_ns = SPEC['garmentInstanceNamespace']
        rows = []
        for person in people['people']:
            pts, extended = ROUTES.decode(person, ratio)
            descriptors = list(u.GameplayStatics.get_all_actors_of_class(world, u.MikdashSceneUnits))
            if target_key == 'Candidate48':
                if len(descriptors) != 1: raise RuntimeError('Candidate requires one live scene frame')
                origin = descriptors[0].get_editor_property('fixed_architecture_origin_cm')
                report['fixedArchitectureOriginCm'] = xyz(origin)
                if person['zone'] == 'outer-court':
                    delta = [v * (1.0 - ratio) for v in xyz(origin)]
                    pts = [[p[i] + delta[i] for i in range(3)] for p in pts]
            feet = u.Vector(*pts[0]); label = 'Resident_' + person['id']
            body = bodies.get(label)
            cast = person.get('body') or {}
            row = dict(id=person['id'], role=person['role'], zone=person['zone'], castVariant=cast.get('variant'), castScale=cast.get('visualScale'),
                       expectedGarmentSlot=SPEC['garmentSlotByVariant'].get(cast.get('variant'), SPEC['garmentSlotByVariant']['default']),
                       decodedWaypoint0=[round(v, 3) for v in pts[0]], spawned=body is not None, logReasons=log_reasons.get(person['id'], []))
            zone_floor = floor_z if person['zone'] == 'outer-court' else 0.0
            if body is not None:
                mesh = body.get_component_by_class(u.SkeletalMeshComponent)
                cap = body.get_component_by_class(u.CapsuleComponent)
                asset = mesh.get_skeletal_mesh_asset() if mesh else None
                rel_scale = mesh.get_editor_property('relative_scale3d'); rel_rot = mesh.get_editor_property('relative_rotation'); rel_loc = mesh.get_editor_property('relative_location')
                actor_scale = body.get_actor_scale3d()
                try: reported = dict(variantId=str(body.get_body_variant_id()), visualScale=float(body.get_body_visual_scale()), fallback=bool(body.is_body_fallback()))
                except Exception as exc: reported = dict(error=repr(exc))
                expected_scale = float(cast.get('visualScale', 1.0)) if reported.get('variantId') else 1.0
                expected_yaw = SPEC['expectedMeshRelativeYaw'] if reported.get('variantId') else SPEC['defaultBody']['meshRelativeYaw']
                slot_readback = None
                try:
                    idx = mesh.get_material_index(u.Name(row['expectedGarmentSlot']))
                    slot_readback = dict(slotIndex=idx, material=_path(mesh.get_material(idx)) if idx >= 0 else None, slotNames=[str(n) for n in mesh.get_material_slot_names()])
                except Exception as exc: slot_readback = dict(error=repr(exc))
                bone = state['bones'].get(label, {})
                head_expected = zone_floor + REST['head'] * expected_scale
                ball_expected = zone_floor + REST['ball'] * expected_scale
                row.update(
                    actualMesh=_path(asset), reportedBody=reported,
                    meshMatchesCast=bool(asset is not None and cast.get('variant') and _path(asset) == variant_assets(cast['variant'])['skeletalMesh']),
                    component=dict(relativeScale3d=xyz(rel_scale), relativeYaw=round(float(rel_rot.yaw), 3), relativeLocation=xyz(rel_loc)),
                    componentOk=(abs(rel_scale.x - expected_scale) <= V['scaleToleranceAbs'] and abs(rel_scale.y - expected_scale) <= V['scaleToleranceAbs'] and abs(rel_scale.z - expected_scale) <= V['scaleToleranceAbs']
                                 and abs(((float(rel_rot.yaw) - expected_yaw + 180) % 360) - 180) <= V['yawToleranceDeg']
                                 and abs(rel_loc.z + 96.0) <= 0.01 and abs(rel_loc.x) <= 0.01 and abs(rel_loc.y) <= 0.01),
                    capsule=dict(radius=round(cap.get_scaled_capsule_radius(), 3), halfHeight=round(cap.get_scaled_capsule_half_height(), 3), actorScale=xyz(actor_scale)),
                    capsuleOk=(abs(cap.get_scaled_capsule_radius() - V['capsule']['radiusCm']) <= V['capsule']['toleranceCm'] and abs(cap.get_scaled_capsule_half_height() - V['capsule']['halfHeightCm']) <= V['capsule']['toleranceCm']
                               and all(abs(s - 1.0) <= 1e-4 for s in (actor_scale.x, actor_scale.y, actor_scale.z))),
                    bones=bone, zoneFloor=zone_floor,
                    feet=dict(ballMinZ=bone.get('ballMinZ'), expectedBallZ=round(ball_expected, 2), errorCm=None if bone.get('ballMinZ') is None else round(bone['ballMinZ'] - zone_floor, 2),
                              ok=bone.get('ballMinZ') is not None and abs(bone['ballMinZ'] - zone_floor) <= V['feetToleranceCm'] + REST['ball'] * expected_scale),
                    head=dict(headMinZ=bone.get('headMinZ'), headMaxZ=bone.get('headMaxZ'), expectedZ=round(head_expected, 2),
                              ok=bone.get('headMaxZ') is not None and abs(bone['headMaxZ'] - head_expected) <= V['headToleranceCm']),
                    facing=dict(toesAheadFraction=None if not bone.get('samples') else round(bone['toesAheadSamples'] / bone['samples'], 3),
                                movingTowardToesFraction=None if not bone.get('movingSamples') else round(bone['movingTowardToesSamples'] / bone['movingSamples'], 3)),
                    garment=slot_readback,
                    garmentOk=bool(slot_readback and slot_readback.get('material') and garment_ns in slot_readback['material']))
                row['capsuleBlockers'] = capsule_blockers(world, feet, ignore)
                row['floorOk'], row['floorTrace'] = floor_ok(world, feet, ignore)
                row['legs'] = [leg(world, u.Vector(*pts[i]), u.Vector(*pts[(i + 1) % len(pts)]), ignore) for i in range(len(pts))]
                row['legsBlocked'] = sum(1 for l in row['legs'] if l['sweepBlocked']); row['legsWithFloorFailures'] = sum(1 for l in row['legs'] if l['floorFailureCount'])
                motion = state['motion'].get(label); row['motion'] = motion
                row['walkedInPie'] = bool(motion and motion.get('movedCm') is not None and motion['movedCm'] >= V['movedThresholdCm'])
            else:
                row['capsuleBlockers'] = capsule_blockers(world, feet, ignore)
                row['floorOk'], row['floorTrace'] = floor_ok(world, feet, ignore)
            rows.append(row)
        report['residents'] = rows
        spawned = [r for r in rows if r['spawned']]
        report['frameTime'] = dict(framesInWindow=state['frames'], windowSeconds=None if state['frameStart'] is None else round(time.monotonic() - state['frameStart'], 2),
                                   averageMs=None if not state['frames'] or state['frameStart'] is None else round(1000.0 * (time.monotonic() - state['frameStart']) / state['frames'], 2))
        report['summary'] = dict(authored=len(rows), spawned=len(spawned), skipped=[r['id'] for r in rows if not r['spawned']],
                                 variantBodies=[r['id'] for r in spawned if r['reportedBody'].get('variantId')], fallbackBodies=[r['id'] for r in spawned if not r['reportedBody'].get('variantId') or r['reportedBody'].get('fallback')],
                                 meshMatchesCast=[r['id'] for r in spawned if r['meshMatchesCast']], meshMismatch=[r['id'] for r in spawned if not r['meshMatchesCast']],
                                 componentOk=sum(1 for r in spawned if r['componentOk']), capsuleOk=sum(1 for r in spawned if r['capsuleOk']),
                                 feetOk=sum(1 for r in spawned if r['feet']['ok']), headOk=sum(1 for r in spawned if r['head']['ok']), garmentOk=sum(1 for r in spawned if r['garmentOk']),
                                 feetFailed=[r['id'] for r in spawned if not r['feet']['ok']], headFailed=[r['id'] for r in spawned if not r['head']['ok']],
                                 componentFailed=[r['id'] for r in spawned if not r['componentOk']], garmentFailed=[r['id'] for r in spawned if not r['garmentOk']],
                                 extremeScales={r['id']: r['castScale'] for r in spawned if r['castScale'] in (0.84, 1.04)},
                                 spawnedWithAllLegsClear=[r['id'] for r in spawned if r['legsBlocked'] == 0 and r['legsWithFloorFailures'] == 0],
                                 movedMoreThanThreshold=[r['id'] for r in spawned if r['walkedInPie']],
                                 capsuleAgreementWithSpawner=all(r['spawned'] == (not r['capsuleBlockers']) for r in rows))
    def tick(dt):
        try:
            now = time.monotonic(); world = ed.get_game_world()
            if state['stopping']:
                if world and now - state['at'] < 15: return
                if world: report['errors'].append('PIE teardown timeout')
                report['pieEnded'] = world is None
                report['mapShaAfter'] = sha(map_file); report['mapBytesUnchanged'] = report['mapShaAfter'] == report['mapShaBefore']
                report['otherMapsUnchanged'] = all(sha(v) == report['otherMapsBefore'][k] for k, v in others.items())
                report['saveIsolation']['originalSavesUnchanged'] = ROUTES._user_save_hashes() == original_saves
                report['stagedDirectory']['unchanged'] = sha(staged) == report['stagedDirectory']['sha256']
                for name, ok in (('Target map bytes changed', report['mapBytesUnchanged']), ('Another map changed', report['otherMapsUnchanged']),
                                 ('Original save files changed', report['saveIsolation']['originalSavesUnchanged']), ('Staged directory changed', report['stagedDirectory']['unchanged'])):
                    if not ok: report['errors'].append(name)
                try: settings.set_editor_property('GameGetsMouseControl', old_mouse)
                except Exception as exc: report['errors'].append('Cleanup: ' + repr(exc))
                if report['errors']: report['status'] = 'failed_cleanup_or_verification'
                try: write()
                finally:
                    u.unregister_slate_post_tick_callback(handle); u.SystemLibrary.quit_editor()
                return
            if now - state['start'] > V['watchdogSeconds']: finish('failed_watchdog'); return
            if not world: return
            if state['phase'] == 'world':
                controller = u.GameplayStatics.get_player_controller(world, 0)
                if controller is None: return
                if not state.get('resumed'):
                    controller.resume_walkthrough()
                    state['resumed'] = True
                    return
                cinematic = u.MikdashCinematics.get(world)
                if cinematic and cinematic.is_playing(): cinematic.skip_intro()
                if u.GameplayStatics.is_game_paused(world) or controller.is_walkthrough_menu_open():
                    raise RuntimeError('Walkthrough did not resume before resident sampling')
                report['samplingUnpaused'] = True
                pops = list(u.GameplayStatics.get_all_actors_of_class(world, u.MikdashResidentPopulation))
                ready = any('Directory' in str(p.get_directory_status()) for p in pops)
                if not ready and now - state['at'] < V['populationWaitSeconds']: return
                state['phase'] = 'window'; state['at'] = now; state['frameStart'] = now; state['gameAt'] = u.GameplayStatics.get_time_seconds(world)
                report['populationReadyWaitSeconds'] = round(now - state['start'], 2)
                return
            if state['phase'] == 'window':
                elapsed = u.GameplayStatics.get_time_seconds(world) - state['gameAt']; state['frames'] += 1
                if u.GameplayStatics.is_game_paused(world): raise RuntimeError('Game paused during resident sampling')
                report['simulatedSampleSeconds'] = round(elapsed, 3)
                lo, hi = V['boneSampleWindowSeconds']
                if lo <= elapsed <= hi and elapsed >= state['nextBone']:
                    sample_bones(world); state['nextBone'] = elapsed + V['boneSampleIntervalSeconds']
                m0, m1 = V['motionSampleSeconds']
                if elapsed >= m0 and not state.get('m0done'):
                    for label, body in resident_bodies(world).items():
                        state['motion'][label] = dict(first=xyz(body.get_actor_location()), firstAtSeconds=round(elapsed, 2))
                    state['m0done'] = True
                if elapsed >= m1:
                    for label, body in resident_bodies(world).items():
                        m = state['motion'].setdefault(label, dict(first=None))
                        m['second'] = xyz(body.get_actor_location()); m['secondAtSeconds'] = round(elapsed, 2)
                        m['movedCm'] = None if m['first'] is None else round(math.dist(m['first'][:2], m['second'][:2]), 2)
                    state['phase'] = 'diagnose'
                return
            if state['phase'] == 'diagnose':
                diagnose(world)
                s = report['summary']
                finish('verify_complete_pie_evidence_%d_of_%d_spawned_%d_variant_bodies_%d_moved' % (s['spawned'], s['authored'], len(s['variantBodies']), len(s['movedMoreThanThreshold'])))
        except Exception:
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
    return report

# ---------------------------------------------------------------------------------------
def _main():
    try:
        import unreal  # noqa: F401
        native = True
    except ImportError:
        native = False
    if not native:
        planned = plan()
        if '--stage' in sys.argv:
            written = stage(planned); planned = plan(); planned['written'] = written
        print(json.dumps(public(planned), indent=2, ensure_ascii=False, default=str))
        if not planned['offlineOk']: raise SystemExit('Offline plan has failures: %r' % planned['failures'])
        return
    import unreal
    command_line = unreal.SystemLibrary.get_command_line()
    try:
        if '-BodiesVerify' in command_line:
            run_verify(_target_from_command_line(command_line))   # quits the editor itself when PIE ends
        elif '-BodiesApply' in command_line:
            run_apply(_target_from_command_line(command_line))
        else:
            raise RuntimeError('release_resident_bodies_v3: nothing done. Pass -BodiesApply or -BodiesVerify with -BodiesTarget=Main50|Candidate48')
    except Exception:
        failure = _receipt_path('failure', stamp_now())
        failure.write_text(json.dumps(dict(status='failed_before_or_during_run', commandLine=command_line, error=traceback.format_exc()), indent=2), encoding='utf-8')
        if '-BodiesVerify' in command_line: unreal.SystemLibrary.quit_editor()
        raise

if __name__ == '__main__':
    _main()

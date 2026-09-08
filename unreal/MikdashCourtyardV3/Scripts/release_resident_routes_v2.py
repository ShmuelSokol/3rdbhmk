"""Resident routes V2: people-v3 loops relocated off the hollow architecture shells.

Everything numeric comes from Scripts/release_resident_routes_v2.spec.json. Both staged
directories (main 50 cm people.json and the isolated 48 cm people-candidate48.json) are
regenerated from the frozen people-v3 source, differing only in the trailing note.

Offline (bundled UE Python, no engine):
    python Scripts/release_resident_routes_v2.py --plan     print the plan; nothing written
    python Scripts/release_resident_routes_v2.py --stage    write both staged files, print plan
  plan() validates every person with a mirror of MikdashPeopleDirectory.h / ResidentRouteLoop.h,
  decodes each route exactly as PopulationSceneMath.h does (x .96 outer court, metric deck,
  signature-locked +25 cm extension only while the signature still matches), and checks every
  waypoint and every 25 cm leg sample against the architecture manifest at BOTH scales:
  unions are decomposed into their source boxes (never a whole-part AABB), the floor under
  each waypoint must be the outer-court floor at the frame's floor Z, the capsule column must
  keep >= radius + margin from every box in the 288/300..480/492 band, and headroom over each
  waypoint must be >= 190 cm. The check is recorded per waypoint in the plan and receipt.

Native apply (commandlet-safe, -nullrhi allowed; strictly serial with other native jobs):
    "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
        "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
        -run=pythonscript -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_resident_routes_v2.py"
        -RoutesV2Apply -RoutesV2Target=Candidate48 -unattended -nullrhi
        -abslog="C:/Mikdash/Working-5.8/Release-ResidentRoutesV2-Candidate48-01.log"
  Guards (project, no game world, no dirty packages), checkpoints the target .umap and the
  previous staged files, stages both directories, loads the target map, repoints the
  RELEASE_PeopleV3Population actor's people_directory_file ONLY if it does not already name
  the target file, saves ONLY when something changed, reopens, reads back, writes a receipt.

PIE verification (real RHI, the coordinator runs it; the editor GUI process, not -Cmd):
    "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
        "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
        /Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough
        -ExecCmds="py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_resident_routes_v2.py"
        -RoutesV2Verify -RoutesV2Target=Candidate48
        -TestSavePrefix=FableProbe_RoutesV2_01
        -ini:Game:[/Script/MikdashRuntime.MikdashSaveSystem]:SlotNamePrefix=FableProbe_RoutesV2_01,[/Script/MikdashRuntime.MikdashSettingsSubsystem]:SaveSlot=FableProbe_RoutesV2_01_Settings
        -unattended -NoSplash -abslog="C:\\Mikdash\\Working-5.8\\Fable-RoutesV2-Candidate48-01.log"
  (For Main50 pass the main map path and -RoutesV2Target=Main50.) Opens PIE on the loaded
  map, waits for the population, records per resident: spawned or skipped (with the log
  reason), the spawner's own 34 x 96 Pawn capsule query at waypoint 0, floor, a capsule sweep
  and floor samples for every leg, and actual displacement between two time samples. Also
  records the five-body pilot population's extended-route status. Nothing is saved; map bytes
  and user save files are hashed before and after. NullRHI is refused as evidence.
"""
import hashlib, json, math, os, re, shutil, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'Scripts/release_resident_routes_v2.spec.json'
SPEC = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
if Path(SPEC['projectDir']).resolve() != ROOT:
    raise RuntimeError('Spec project directory differs from the script root')
RADIUS = float(SPEC['pilgrimEnvelope']['capsuleRadiusCm'])
HALF = float(SPEC['pilgrimEnvelope']['capsuleHalfHeightCm'])
MARGIN = float(SPEC['pilgrimEnvelope']['offlineMarginBeyondRadiusCm'])
HEADROOM = float(SPEC['pilgrimEnvelope']['headroomRequiredCm'])
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp_now(): return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
def disk(package): return ROOT / 'Content' / (package[6:] + '.umap')
def dist2(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
def loop_length(pts): return sum(dist2(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))
def in_legacy_region(x, y): return 1500 <= x <= 7000 and 900 <= abs(y) < 6000
def in_mount_region(x, y): return 9300 <= x <= 10000 and abs(y) <= 3000

# ---------------------------------------------------------------------------------------
# Directory construction (both targets from the frozen people-v3 source).
# ---------------------------------------------------------------------------------------
def source_directory():
    source = ROOT / SPEC['source']['frozenPeopleV3']
    if sha(source) != SPEC['source']['sha256']:
        raise RuntimeError('Frozen people-v3 source differs from the spec hash; refuse to derive V2 from it')
    data = json.loads(source.read_text(encoding='utf-8-sig'))
    if data['version'] != SPEC['source']['versionMustStay']: raise RuntimeError('Unexpected directory version')
    if len(data['people']) != SPEC['source']['expectedPeople']: raise RuntimeError('Unexpected people count in the source')
    return data

def build_directory(target_key):
    target = SPEC['targets'][target_key]
    data = source_directory()
    edits = {k: v for k, v in SPEC['routeEdits'].items() if k != 'note'}
    seen = set()
    for person in data['people']:
        if person['id'] not in edits: continue
        edit = edits[person['id']]
        if len(edit['at']) != len(person['route']): raise RuntimeError('Edit shape differs for ' + person['id'])
        for step, was, at in zip(person['route'], edit['was'], edit['at']):
            if [float(step['at'][0]), float(step['at'][1])] != [float(was[0]), float(was[1])]:
                raise RuntimeError('%s: source waypoint %r is not the recorded "was" %r' % (person['id'], step['at'], was))
            step['at'] = [float(v) for v in at]
        seen.add(person['id'])
    if seen != set(edits): raise RuntimeError('Missing people for edits: %r' % sorted(set(edits) - seen))
    pilgrim = data['placementBasis']['pilgrim']
    pilgrim['decision'] = SPEC['pilgrimEnvelope']['decision']
    pilgrim['exclusionsLegacyCm'] = [dict(name=e['name'], rect=e['rect']) for e in SPEC['pilgrimEnvelope']['exclusionsLegacyCm']]
    pilgrim['capsuleRadiusCm'] = SPEC['pilgrimEnvelope']['capsuleRadiusCm']
    if not 20 <= len(pilgrim['decision']) <= 1200: raise RuntimeError('pilgrim decision length outside the parser limits')
    data['note'] = data['note'] + target['noteSuffix']
    if len(data['note']) > 2000: raise RuntimeError('Note exceeds the parser limit')
    return data

def serialize(data): return (json.dumps(data, indent=1, ensure_ascii=False) + '\n').encode('utf-8')

# ---------------------------------------------------------------------------------------
# Parser mirror and decoder replica.
# ---------------------------------------------------------------------------------------
def locked_signature_matches(person):
    lock = SPEC['lockedRoutes'].get(person['id'])
    if not lock or person['zone'] != 'outer-court' or person['role'] != lock['role'] or len(person['route']) != 4: return None
    r = lock['rect']; corners = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]; pauses = [4, 3, 5, 4]
    for i, step in enumerate(person['route']):
        look_x = 7800.0 if (i == 3 or (lock['first'] == 0 and i == 1)) else 0.0
        x, y, z = step['at']
        if (x, y, z) != (corners[i][0], corners[i][1], 300.0) or step['pause'] != pauses[i] or list(step['look']) != [look_x, 0.0, 300.0]:
            return None
    return lock

def decode(person, ratio):
    pts = [[x * ratio, y * ratio, z * ratio] if person['zone'] == 'outer-court' else [x, y, z] for x, y, z in (w['at'] for w in person['route'])]
    lock = locked_signature_matches(person) if ratio != 1.0 else None
    if lock:
        pts[lock['first']][1] += lock['deltaY']; pts[lock['first'] + 1][1] += lock['deltaY']
    return pts, bool(lock)

def validate_person(person):
    pts = [w['at'] for w in person['route']]
    if not 4 <= len(pts) <= 6: raise RuntimeError(person['id'] + ': 4..6 waypoints')
    for w in person['route']:
        x, y, z = w['at']
        if person['zone'] == 'outer-court':
            if not in_legacy_region(x, y): raise RuntimeError('%s: waypoint outside authored zone %r' % (person['id'], w['at']))
            if abs(z - 300) > 12: raise RuntimeError(person['id'] + ': off floor')
        else:
            if not in_mount_region(x, y) or abs(z) > 12: raise RuntimeError(person['id'] + ': waypoint outside the mount-deck zone')
        if not 3 <= w['pause'] <= 5: raise RuntimeError(person['id'] + ': pause')
        if not (4 <= len(w['label']) <= 120 and 4 <= len(w['action']) <= 120): raise RuntimeError(person['id'] + ': label/action length')
    for i in range(len(pts)):
        if dist2(pts[i], pts[(i + 1) % len(pts)]) < 200: raise RuntimeError(person['id'] + ': consecutive waypoints too close')
    legacy = loop_length(pts)
    selected = loop_length(decode(person, 0.96)[0])
    if not 6000 <= legacy <= 12000: raise RuntimeError('%s: legacy loop %.1f cm outside 60..120 m' % (person['id'], legacy))
    if person['zone'] == 'outer-court' and not 6000 < selected <= 12000:
        raise RuntimeError('%s: selected48 loop %.2f cm not strictly inside 60..120 m' % (person['id'], selected))
    return dict(legacyLoopCm=round(legacy, 2), selected48LoopCm=round(selected, 2) if person['zone'] == 'outer-court' else round(legacy, 2))

def shell_clearance(pts, ratio):
    """Mirror of PopulationSceneMath.h::TryShellClearance at the given scale (radius only, no margin)."""
    for shell in SPEC['pilgrimEnvelope']['exclusionsLegacyCm']:
        r = [v * ratio for v in shell['rect']]
        r = [r[0] - RADIUS, r[1] - RADIUS, r[2] + RADIUS, r[3] + RADIUS]
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            n = max(1, int(math.ceil(dist2(a, b) / 25.0)))
            for s in range(n + 1):
                t = s / n; x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                if r[0] < x < r[2] and r[1] < y < r[3]: return shell['name']
    return None

# ---------------------------------------------------------------------------------------
# Manifest geometry: constituent boxes, legacy centimetres.
# ---------------------------------------------------------------------------------------
_BOXES = None
def manifest_boxes():
    """Every box that can touch the outer-court capsule band, at legacy scale: (name, lo, hi, kind)."""
    global _BOXES
    if _BOXES is not None: return _BOXES
    path = ROOT / SPEC['geometry']['manifest']
    if sha(path) != SPEC['geometry']['manifestSha256']: raise RuntimeError('Architecture manifest hash differs from the spec')
    m = json.loads(path.read_text(encoding='utf-8-sig'))
    A = float(SPEC['geometry']['sourceAmahCm'])
    zone = SPEC['geometry']['zoneLegacy']; slack = float(SPEC['geometry']['sweepSlackCm'])
    boxes, unions = [], []
    for e in m['meshes']:
        if e.get('unionGroup'):
            elements = json.loads(e['sourceProperties']['source_elements_json'])
            lo_all = [1e18] * 3; hi_all = [-1e18] * 3
            for el in elements:
                if el.get('shape') != 'box': raise RuntimeError('Union %s has a non-box constituent %r' % (e['sourceName'], el.get('shape')))
                px, py, pz = el['position']; sx, sy, sz = el['size']
                lo = [(px - sx / 2) * A, (pz - sz / 2) * A, (py - sy / 2) * A]; hi = [(px + sx / 2) * A, (pz + sz / 2) * A, (py + sy / 2) * A]
                for k in range(3): lo_all[k] = min(lo_all[k], lo[k]); hi_all[k] = max(hi_all[k], hi[k])
                boxes.append((e['sourceName'] + ' :: ' + el['name'], lo, hi, 'union-constituent'))
            b = e['expectedBoundsUnrealCm']
            if any(abs(lo_all[k] - b['min'][k]) > 0.5 or abs(hi_all[k] - b['max'][k]) > 0.5 for k in range(3)):
                raise RuntimeError('Union %s constituents do not rebuild its bounds' % e['sourceName'])
            unions.append(e['sourceName'])
        else:
            b = e['expectedBoundsUnrealCm']
            boxes.append((e['sourceName'], list(b['min']), list(b['max']), 'mesh-aabb (8-vertex box)' if e['vertices'] == 8 else 'mesh-aabb'))
    keep = []
    for name, lo, hi, kind in boxes:
        if hi[0] < zone['x'][0] - slack or lo[0] > zone['x'][1] + slack: continue
        if hi[1] < -zone['absY'][1] - slack or lo[1] > zone['absY'][1] + slack: continue
        if hi[2] <= 300.0 - 40 or lo[2] >= 300.0 + 2 * HALF + 40: continue
        keep.append((name, lo, hi, kind))
    _BOXES = dict(boxes=keep, unionsDecomposed=unions, totalMeshes=len(m['meshes']))
    return _BOXES

def check_route(person, ratio, floor_z):
    """Per-waypoint floor, headroom and nearest-blocker record plus leg clearance, offline, at one scale."""
    pts, extended = decode(person, ratio)
    geo = manifest_boxes()
    floor_name = SPEC['geometry']['floorMeshSourceName']
    scaled = [(n, [v * ratio for v in lo], [v * ratio for v in hi], k) for n, lo, hi, k in geo['boxes']]
    band_lo, band_hi = floor_z + 0.5, floor_z + 2 * HALF
    def xy_distance(x, y, lo, hi):
        dx = max(lo[0] - x, 0.0, x - hi[0]); dy = max(lo[1] - y, 0.0, y - hi[1]); return math.hypot(dx, dy)
    def blockers_near(x, y, reach):
        out = []
        for n, lo, hi, k in scaled:
            if hi[2] <= band_lo or lo[2] >= band_hi: continue
            d = xy_distance(x, y, lo, hi)
            if d <= reach: out.append((d, n, lo, hi, k))
        return sorted(out)
    rows = []
    for i, (x, y, z) in enumerate(pts):
        floors = [(n, lo, hi) for n, lo, hi, k in scaled if n == floor_name and lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1]]
        floor_ok = bool(floors) and abs(floors[0][2][2] - floor_z) < 0.05 and abs(z - floor_z) < 0.05
        overhead = [lo[2] - floor_z for n, lo, hi, k in scaled if lo[2] >= floor_z + 0.5 and xy_distance(x, y, lo, hi) <= RADIUS]
        headroom = min(overhead) if overhead else None
        near = blockers_near(x, y, 600.0)
        rows.append(dict(index=i, feet=[round(x, 3), round(y, 3), round(z, 3)], floorMesh=floors[0][0] if floors else None,
                         floorTopZ=round(floors[0][2][2], 3) if floors else None, floorOk=floor_ok,
                         headroomCm=None if headroom is None else round(headroom, 2), headroomOk=headroom is None or headroom >= HEADROOM,
                         nearestBlocker=None if not near else dict(name=near[0][1], distanceCm=round(near[0][0], 2), kind=near[0][4],
                                                                     boxMin=[round(v, 2) for v in near[0][2]], boxMax=[round(v, 2) for v in near[0][3]]),
                         clearanceOk=(not near) or near[0][0] >= RADIUS + MARGIN))
    legs = []
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n = max(1, int(math.ceil(dist2(a, b) / 25.0)))
        worst = None; floor_fail = 0
        for s in range(n + 1):
            t = s / n; x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            if not any(nm == floor_name and lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1] for nm, lo, hi, k in scaled): floor_fail += 1
            near = blockers_near(x, y, RADIUS + MARGIN + 1)
            if near and (worst is None or near[0][0] < worst['distanceCm']):
                worst = dict(distanceCm=round(near[0][0], 2), name=near[0][1], at=[round(x, 2), round(y, 2)])
        legs.append(dict(index=i, fromFeet=[round(v, 3) for v in a], toFeet=[round(v, 3) for v in b], samples=n + 1,
                         floorSampleFailures=floor_fail, closestBlocker=worst, clearanceOk=worst is None or worst['distanceCm'] >= RADIUS + MARGIN))
    shell = shell_clearance(pts, ratio) if person['zone'] == 'outer-court' else None
    ok = all(r['floorOk'] and r['headroomOk'] and r['clearanceOk'] for r in rows) and all(l['clearanceOk'] and l['floorSampleFailures'] == 0 for l in legs) and shell is None
    return dict(ratio=ratio, floorZ=floor_z, extensionApplied=extended, loopCm=round(loop_length(pts), 2), waypoints=rows, legs=legs,
                shellEntered=shell, ok=ok)

def plan():
    edits = {k for k in SPEC['routeEdits'] if k != 'note'}
    result = dict(status='PLAN_ONLY_NO_WRITES', targets={}, people={}, edits=sorted(edits))
    docs = {}
    for key, target in SPEC['targets'].items():
        data = build_directory(key); text = serialize(data); docs[key] = (data, text)
        staged = ROOT / target['staged']
        result['targets'][key] = dict(staged=target['staged'], relativeToContent=target['relativeToContent'], map=target['map'], frame=target['frame'],
                                      plannedSha256=hashlib.sha256(text).hexdigest(), stagedExists=staged.exists(),
                                      stagedSha256=sha(staged) if staged.exists() else None)
        result['targets'][key]['stagedMatchesPlan'] = result['targets'][key]['stagedSha256'] == result['targets'][key]['plannedSha256']
    people = docs['Main50'][0]['people']
    if [p['route'] for p in people] != [p['route'] for p in docs['Candidate48'][0]['people']]:
        raise RuntimeError('The two targets must carry identical legacy routes')
    outer = [p for p in people if p['zone'] == 'outer-court']
    failures = []
    for person in people:
        row = validate_person(person); row.update(role=person['role'], zone=person['zone'], edited=person['id'] in edits)
        if person['zone'] == 'outer-court':
            row['checks'] = {key: check_route(person, SPEC['targets'][key]['ratio'], SPEC['targets'][key]['floorZ']) for key in SPEC['targets']}
            for key, chk in row['checks'].items():
                if not chk['ok']: failures.append('%s at %s' % (person['id'], key))
        else:
            row['checks'] = 'mount-deck: metric, unchanged, no Temple architecture in the band'
        result['people'][person['id']] = row
    # Spawn points must not collide with each other at either scale.
    sep = {}
    for key, target in SPEC['targets'].items():
        best = None
        starts = {p['id']: decode(p, target['ratio'])[0][0] for p in outer}
        ids = sorted(starts)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                d = dist2(starts[ids[i]], starts[ids[j]])
                if best is None or d < best[0]: best = (d, ids[i], ids[j])
        sep[key] = dict(minimumWaypoint0SeparationCm=round(best[0], 2), pair=[best[1], best[2]], ok=best[0] >= SPEC['geometry']['minimumSpawnSeparationCm'])
        if not sep[key]['ok']: failures.append('spawn separation at ' + key)
    result['spawnSeparation'] = sep
    result['extensionApplied48'] = sorted(p['id'] for p in outer if decode(p, 0.96)[1])
    if result['extensionApplied48'] != ['chananel-ben-mattisyahu']: failures.append('unexpected extension set %r' % result['extensionApplied48'])
    result['geometry'] = dict(boxesInBand=len(manifest_boxes()['boxes']), unionsDecomposed=manifest_boxes()['unionsDecomposed'], totalMeshes=manifest_boxes()['totalMeshes'])
    result['failures'] = failures
    result['offlineOk'] = not failures
    result['_documents'] = {k: v[1] for k, v in docs.items()}
    return result

def stage(planned=None):
    planned = planned or plan()
    if not planned['offlineOk']: raise RuntimeError('Offline plan has failures; nothing staged: %r' % planned['failures'])
    written = {}
    for key, target in SPEC['targets'].items():
        staged = ROOT / target['staged']; staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(planned['_documents'][key])  # bytes: no CRLF translation; the hash must match the plan
        if sha(staged) != planned['targets'][key]['plannedSha256']: raise RuntimeError('Staged hash mismatch for ' + key)
        written[key] = dict(path=str(staged), sha256=planned['targets'][key]['plannedSha256'])
    return written

def public(planned): return {k: v for k, v in planned.items() if k != '_documents'}

# ---------------------------------------------------------------------------------------
# Native helpers.
# ---------------------------------------------------------------------------------------
def _target_from_command_line(command_line):
    m = re.search(r'-RoutesV2Target=(Main50|Candidate48)', command_line)
    if not m: raise RuntimeError('Pass -RoutesV2Target=Main50 or -RoutesV2Target=Candidate48')
    return m.group(1)

def _save_isolation(command_line):
    prefix_match = re.search(r'-TestSavePrefix=((?:AstraProbe|FableProbe)_[A-Za-z0-9_]+)', command_line)
    if not prefix_match: raise RuntimeError('Require a unique -TestSavePrefix=FableProbe_<stamp> and Game ini overrides')
    prefix = prefix_match.group(1)
    for section, key, value in [('MikdashSaveSystem', 'SlotNamePrefix', prefix), ('MikdashSettingsSubsystem', 'SaveSlot', prefix + '_Settings')]:
        if ('[/Script/MikdashRuntime.' + section + ']:' + key + '=' + value) not in command_line: raise RuntimeError('Missing save-isolation ini override for ' + key)
    return prefix

def _user_save_hashes():
    roots = [ROOT / 'Saved/SaveGames', Path(os.environ.get('LOCALAPPDATA', '')) / 'MikdashCourtyardV3/Saved/SaveGames']
    return {str(p): sha(p) for folder in roots if folder.exists() for p in folder.glob('*.sav')
            if not (p.name.startswith('AstraProbe_') or p.name.startswith('FableProbe_'))}

def _receipt_path(kind, stamp):
    folder = ROOT / SPEC['receiptFolder']; folder.mkdir(parents=True, exist_ok=True)
    return folder / (SPEC['receiptPrefix'] + kind + '-' + stamp + '.json')

def _find_label(ue, actors, label):
    found = [a for a in actors.get_all_level_actors() if a.get_actor_label() == label]
    if len(found) != 1: raise RuntimeError('Expected exactly one actor labelled %s, found %d' % (label, len(found)))
    return found[0]

def run_apply(target_key):
    import unreal as ue
    target = SPEC['targets'][target_key]
    if Path(ue.Paths.project_dir()).resolve() != ROOT.resolve(): raise RuntimeError('Wrong project directory: refuse native mutation')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    if editor.get_game_world(): raise RuntimeError('Live game: refuse')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages: refuse')
    MAP = target['map']; map_file = disk(MAP)
    others = {k: disk(v['map']) for k, v in SPEC['targets'].items() if k != target_key}
    stamp = stamp_now(); receipt_path = _receipt_path('apply-' + target_key, stamp)
    planned = plan()
    receipt = dict(status='starting', mode='apply', target=target_key, map=MAP, mapBeforeSha256=sha(map_file),
                   otherMapsBefore={k: sha(v) for k, v in others.items()}, spec=str(SPEC_PATH), plan=public(planned), errors=[])
    def write(): receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    if not planned['offlineOk']:
        receipt.update(status='failed_offline_plan', failure=repr(planned['failures'])); write(); raise RuntimeError(receipt['failure'])
    try:
        # ---- checkpoint: target map plus both previous staged files ---------------------
        checkpoint = Path(SPEC['checkpointRoot']) / (SPEC['checkpointPrefix'] + target_key + '-' + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'BeforeRoutesV2.umap')
        if sha(checkpoint / 'BeforeRoutesV2.umap') != receipt['mapBeforeSha256']: raise RuntimeError('Checkpoint copy mismatch')
        for key, t in SPEC['targets'].items():
            staged = ROOT / t['staged']
            if staged.exists(): shutil.copy2(staged, checkpoint / (Path(t['staged']).name.replace('.json', '.previous.json')))
        receipt['checkpoint'] = str(checkpoint); write()
        # ---- stage both directories ------------------------------------------------------
        receipt['staged'] = stage(planned); write()
        # ---- load the target map, repoint only if needed ---------------------------------
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            if not levels.load_level(MAP): raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != MAP: raise RuntimeError('Unexpected editor world')
        import importlib.util
        helper_spec = importlib.util.spec_from_file_location('routesv2_scene_snapshot', ROOT / 'Scripts/release_resident_crowd.py')
        helper = importlib.util.module_from_spec(helper_spec); helper_spec.loader.exec_module(helper)
        baseline = helper._scene_snapshot(ue, actors)
        owner = _find_label(ue, actors, target['populationActorLabel'])
        if not bool(owner.get_editor_property('spawn_authored_people_on_begin_play')): raise RuntimeError('Wrong population actor (not the people-v3 spawner)')
        before_prop = str(owner.get_editor_property('people_directory_file'))
        repointed = before_prop != target['relativeToContent']
        if repointed:
            owner.modify(True)
            owner.set_editor_property('people_directory_file', target['relativeToContent'])
        receipt['populationActor'] = dict(name=owner.get_name(), label=target['populationActorLabel'], before=before_prop,
                                          after=str(owner.get_editor_property('people_directory_file')), repointed=repointed)
        after = helper._scene_snapshot(ue, actors)
        changed = {k for k in set(baseline) | set(after) if baseline.get(k) != after.get(k)}
        allowed = {owner.get_name()} if repointed else set()
        if changed - allowed: raise RuntimeError('Unexpected scene changes: %r' % sorted(changed - allowed)[:20])
        receipt['sceneChanges'] = sorted(changed)
        if repointed:
            if not levels.save_current_level(): raise RuntimeError('Level save failed')
            receipt.update(mapSaved=True, mapAfterSha256=sha(map_file), status='saved_reopen_pending'); write()
            if not levels.load_level(MAP) or editor.get_editor_world().get_outermost().get_name() != MAP: raise RuntimeError('Reopen failed')
            owner = _find_label(ue, actors, target['populationActorLabel'])
        else:
            receipt.update(mapSaved=False, mapAfterSha256=sha(map_file), status='no_map_change_needed'); write()
        readback = str(owner.get_editor_property('people_directory_file'))
        if readback != target['relativeToContent']: raise RuntimeError('Readback: directory file is %r, expected %r' % (readback, target['relativeToContent']))
        receipt['readback'] = dict(directoryFile=readback)
        receipt['otherMapsUnchanged'] = all(sha(v) == receipt['otherMapsBefore'][k] for k, v in others.items())
        if not receipt['otherMapsUnchanged']: raise RuntimeError('Another map changed bytes during the apply')
        for key, t in SPEC['targets'].items():
            if sha(ROOT / t['staged']) != planned['targets'][key]['plannedSha256']: raise RuntimeError('Staged file changed during the run: ' + key)
        receipt['mapBytesChanged'] = receipt['mapAfterSha256'] != receipt['mapBeforeSha256']
        receipt['status'] = ('applied_saved_reopened' if repointed else 'staged_actor_already_pointed_map_untouched') + '_pie_verification_pending'
    except Exception as exc:
        receipt.update(status='failed_checkpoint_available' if receipt.get('checkpoint') else 'failed_before_map_change', failure=repr(exc), traceback=traceback.format_exc())
        write(); raise
    finally:
        write(); ue.log(json.dumps({k: v for k, v in receipt.items() if k != 'plan'}, indent=2, default=str))
    return receipt

def run_verify(target_key):
    import unreal as u
    target = SPEC['targets'][target_key]
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
    test_prefix = _save_isolation(command_line)
    map_file = disk(MAP); others = {k: disk(v['map']) for k, v in SPEC['targets'].items() if k != target_key}
    original_saves = _user_save_hashes()
    staged = ROOT / target['staged']
    people = json.loads(staged.read_text(encoding='utf-8-sig'))
    stamp = stamp_now(); out = _receipt_path('verify-' + target_key, stamp)
    abslog = re.search(r'-abslog=("?)([^"]+)\1', command_line)
    report = dict(status='starting', mode='verify', target=target_key, map=MAP, frame=target['frame'], ratio=ratio, mapShaBefore=sha(map_file),
                  otherMapsBefore={k: sha(v) for k, v in others.items()}, stagedDirectory=dict(path=str(staged), sha256=sha(staged)), errors=[],
                  scope='Real-RHI PIE: spawner-equivalent capsule/floor queries per resident, leg sweeps, motion samples, log skip reasons; no map writes; not navmesh or visual acceptance',
                  commandLine=command_line, abslog=abslog.group(2) if abslog else None, saveIsolation=dict(testPrefix=test_prefix, originalSaveFileCount=len(original_saves)))
    def write(): out.write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')
    def xyz(v): return [round(v.x, 3), round(v.y, 3), round(v.z, 3)]
    # Editor-world readback of the population actors (read-only).
    pops = [a for a in actors_sub.get_all_level_actors() if isinstance(a, u.MikdashResidentPopulation)]
    rows = []
    for pop in pops:
        row = dict(name=pop.get_name(), label=pop.get_actor_label())
        for key in ('spawn_authored_people_on_begin_play', 'people_directory_file', 'source_coordinate_revision', 'activate_reviewed_pilot_on_begin_play', 'extended_route_body_index'):
            try: row[key] = str(pop.get_editor_property(key))
            except Exception as exc: row[key] = 'unavailable: ' + repr(exc)
        rows.append(row)
    report['editorPopulations'] = rows
    pointed = [r for r in rows if r.get('people_directory_file') == target['relativeToContent']]
    report['populationPointedAtTarget'] = len(pointed) == 1
    write()
    NODRAW = u.DrawDebugTrace.NONE; VIS = u.TraceTypeQuery.TRACE_TYPE_QUERY1
    def unwrap(r):
        if r is None: return []
        if isinstance(r, tuple): r = r[-1]
        return list(r) if r is not None else []
    def hit_row(h):
        d = {str(k).lower().replace('_', ''): v for k, v in h.to_dict().items()}
        comp = d.get('hitcomponent'); owner_actor = comp.get_owner() if comp else None
        ip = d.get('impactpoint'); n = d.get('impactnormal')
        mesh = None
        try:
            if isinstance(comp, u.StaticMeshComponent):
                sm = comp.get_editor_property('static_mesh'); mesh = sm.get_path_name() if sm else None
        except Exception: pass
        return dict(blocking=bool(d.get('blockinghit', True)), initialOverlap=bool(d.get('initialoverlap', False)), distance=round(float(d.get('distance') or 0), 3),
                    impactPoint=xyz(ip) if ip is not None else None, impactNormal=xyz(n) if n is not None else None,
                    component=comp.get_name() if comp else None, actorLabel=owner_actor.get_actor_label() if owner_actor else None, mesh=mesh)
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
    def ceiling(world, feet, ignore):
        h = u.SystemLibrary.line_trace_single_by_profile(world, feet + u.Vector(0, 0, 2), feet + u.Vector(0, 0, 500), 'Pawn', False, ignore, NODRAW, True)
        if isinstance(h, tuple): h = h[-1]
        if h is None: return None
        r = hit_row(h); r['headroomCm'] = None if r['impactPoint'] is None else round(r['impactPoint'][2] - feet.z, 2)
        return r
    def leg(world, a, b, ignore):
        A = a + u.Vector(0, 0, HALF + 2); B = b + u.Vector(0, 0, HALF + 2)
        hits = [hit_row(h) for h in unwrap(u.SystemLibrary.capsule_trace_multi_by_profile(world, A, B, RADIUS, HALF, 'Pawn', False, ignore, NODRAW, True))]
        blocking = [h for h in hits if h['blocking']]
        n = max(1, int(math.ceil(math.dist([a.x, a.y], [b.x, b.y]) / 100.0))); fails = []
        for s in range(n + 1):
            t = s / n; feet = u.Vector(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z)
            ok, tr = floor_ok(world, feet, ignore)
            if not ok: fails.append(dict(feet=xyz(feet), hit=None if tr is None else dict(impactPoint=tr.get('impactPoint'), actorLabel=tr.get('actorLabel'))))
        first = min(blocking, key=lambda h: h['distance']) if blocking else None
        return dict(fromFeet=xyz(a), toFeet=xyz(b), lengthCm=round(math.dist([a.x, a.y], [b.x, b.y]), 1), sweepBlocked=bool(blocking), firstBlock=first,
                    floorSamples=n + 1, floorFailureCount=len(fails), floorFailures=fails[:6])
    state = dict(start=time.monotonic(), phase='world', at=time.monotonic(), stopping=False, motion={})
    settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
    old_mouse = settings.get_editor_property('GameGetsMouseControl')
    samples = SPEC['verify']['motionSampleSeconds']; moved_threshold = float(SPEC['verify']['movedThresholdCm'])
    def finish(status):
        if state['stopping']: return
        report['status'] = status; state['stopping'] = True; state['at'] = time.monotonic()
        levels.editor_request_end_play(); write()
    def resident_bodies(world):
        return {b.get_actor_label(): b for b in u.GameplayStatics.get_all_actors_of_class(world, u.MikdashResidentCharacter)}
    def read_log_reasons():
        reasons = {}
        try:
            u.log_flush()
            path = report.get('abslog')
            if not path: return reasons
            for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
                m = re.search(r'MikdashResidentPopulation_\d+: (skipped|note) ([a-z0-9-]+): (.*)$', line)
                if m: reasons.setdefault(m.group(2), []).append(m.group(1) + ': ' + m.group(3).strip())
                m2 = re.search(r'(authored route extension not applied: .*)$', line)
                if m2: reasons.setdefault('_extensionNotes', []).append(m2.group(1).strip())
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
            pop_rows.append(dict(name=p.get_name(), living=p.get_living_resident_count(), directoryStatus=p.get_directory_status(),
                                 extendedRouteStatus=p.get_extended_route_status(), extendedRouteActive=p.is_extended_route_active(), active=p.is_population_active(),
                                 status=p.get_population_status()))
        report['piePopulations'] = pop_rows
        pilot = [r for r in pop_rows if 'Directory' not in str(r['directoryStatus'])]
        report['pilotExtendedRoute'] = dict(active=any(r['extendedRouteActive'] for r in pilot), status=[r['extendedRouteStatus'] for r in pilot],
                                            expectation='TryLook now classifies (5000,1180,300); an "unclassified converted points" refusal means the compiled binary predates this change')
        log_reasons = read_log_reasons()
        report['logExtensionNotes'] = log_reasons.pop('_extensionNotes', [])
        rows = []
        for person in people['people']:
            pts, extended = decode(person, ratio)
            feet = u.Vector(*pts[0]); label = 'Resident_' + person['id']
            row = dict(id=person['id'], name=person['name'], role=person['role'], zone=person['zone'], edited=person['id'] in SPEC['routeEdits'],
                       decodedWaypoint0=[round(v, 3) for v in pts[0]], extensionApplied=extended, spawned=label in bodies,
                       logReasons=log_reasons.get(person['id'], []))
            row['capsuleBlockers'] = capsule_blockers(world, feet, ignore)
            row['floorOk'], row['floorTrace'] = floor_ok(world, feet, ignore)
            row['ceilingAbove'] = ceiling(world, feet, ignore)
            row['legs'] = [leg(world, u.Vector(*pts[i]), u.Vector(*pts[(i + 1) % len(pts)]), ignore) for i in range(len(pts))]
            row['legsBlocked'] = sum(1 for l in row['legs'] if l['sweepBlocked']); row['legsWithFloorFailures'] = sum(1 for l in row['legs'] if l['floorFailureCount'])
            motion = state['motion'].get(label)
            row['motion'] = motion
            row['walkedInPie'] = bool(motion and motion.get('movedCm') is not None and motion['movedCm'] >= moved_threshold)
            rows.append(row)
        report['residents'] = rows
        report['summary'] = dict(authored=len(rows), spawned=sum(1 for r in rows if r['spawned']), skipped=[r['id'] for r in rows if not r['spawned']],
                                 spawnedWithAllLegsClear=[r['id'] for r in rows if r['spawned'] and r['legsBlocked'] == 0 and r['legsWithFloorFailures'] == 0],
                                 spawnedWithBlockedLegs={r['id']: r['legsBlocked'] for r in rows if r['spawned'] and r['legsBlocked']},
                                 movedMoreThanThreshold=[r['id'] for r in rows if r['walkedInPie']],
                                 capsuleAgreementWithSpawner=all(r['spawned'] == (not r['capsuleBlockers']) for r in rows),
                                 editedSpawned=[r['id'] for r in rows if r['edited'] and r['spawned']], editedSkipped=[r['id'] for r in rows if r['edited'] and not r['spawned']])
    def tick(dt):
        try:
            now = time.monotonic(); world = ed.get_game_world()
            if state['stopping']:
                if world and now - state['at'] < 15: return
                if world: report['errors'].append('PIE teardown timeout')
                report['pieEnded'] = world is None
                report['mapShaAfter'] = sha(map_file); report['mapBytesUnchanged'] = report['mapShaAfter'] == report['mapShaBefore']
                report['otherMapsUnchanged'] = all(sha(v) == report['otherMapsBefore'][k] for k, v in others.items())
                report['saveIsolation']['originalSavesUnchanged'] = _user_save_hashes() == original_saves
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
            if now - state['start'] > SPEC['verify']['watchdogSeconds']: finish('failed_watchdog'); return
            if not world: return
            if state['phase'] == 'world':
                pops = list(u.GameplayStatics.get_all_actors_of_class(world, u.MikdashResidentPopulation))
                ready = any('Directory' in str(p.get_directory_status()) for p in pops)
                if not ready and now - state['at'] < SPEC['verify']['populationWaitSeconds']: return
                state['phase'] = 'sample0'; state['at'] = now; state['pie0'] = world.get_time_seconds() if hasattr(world, 'get_time_seconds') else None
                report['populationReadyWaitSeconds'] = round(now - state['start'], 2)
                return
            if state['phase'] == 'sample0':
                if now - state['at'] < samples[0]: return
                for label, body in resident_bodies(world).items():
                    state['motion'][label] = dict(first=xyz(body.get_actor_location()), firstAtSeconds=round(now - state['start'], 2))
                state['phase'] = 'sample1'; return
            if state['phase'] == 'sample1':
                if now - state['at'] < samples[1]: return
                for label, body in resident_bodies(world).items():
                    m = state['motion'].setdefault(label, dict(first=None))
                    m['second'] = xyz(body.get_actor_location()); m['secondAtSeconds'] = round(now - state['start'], 2)
                    m['movedCm'] = None if m['first'] is None else round(math.dist(m['first'][:2], m['second'][:2]), 2)
                state['phase'] = 'diagnose'; return
            if state['phase'] == 'diagnose':
                diagnose(world)
                s = report['summary']
                finish('verify_complete_pie_evidence_%d_of_%d_spawned_%d_moved' % (s['spawned'], s['authored'], len(s['movedMoreThanThreshold'])))
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
        if '-RoutesV2Verify' in command_line:
            run_verify(_target_from_command_line(command_line))   # quits the editor itself when PIE ends
        elif '-RoutesV2Apply' in command_line:
            run_apply(_target_from_command_line(command_line))
        else:
            raise RuntimeError('release_resident_routes_v2: nothing done. Pass -RoutesV2Apply or -RoutesV2Verify with -RoutesV2Target=Main50|Candidate48')
    except Exception:
        failure = _receipt_path('failure', stamp_now())
        failure.write_text(json.dumps(dict(status='failed_before_or_during_run', commandLine=command_line, error=traceback.format_exc()), indent=2), encoding='utf-8')
        if '-RoutesV2Verify' in command_line: unreal.SystemLibrary.quit_editor()
        raise

if __name__ == '__main__':
    _main()

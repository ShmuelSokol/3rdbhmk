"""Guarded rigid XY translation of the TEMPLE actor set (route A) so the Aron footprint centre
sits over the Dome of the Rock centroid (Even HaShetiyah / es-Sakhra) - see
SourceAssets/scale-review/ARON-ON-EVEN-HASHETIYAH-20260908.md and the plan receipt written by
Scripts/plan_aron_alignment.py.  Every number comes from Scripts/release_aron_alignment.spec.json.

APPLY IS GATED OFF BY DEFAULT.  Without -AronAlignApply the script never mutates anything.

Commandlet invocation (serial; never while another native job runs; never the GUI editor):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_aron_alignment.py"
      -unattended -nullrhi
      -AronAlignTarget=Candidate48 -AronAlignDryRun
      -abslog="C:/Mikdash/Working-5.8/Release-AronAlignment-DryRun-01.log"

Switches (case-insensitive):
  -AronAlignTarget=Main50|Candidate48   which spec target (required)
  -AronAlignDryRun                      load the map, classify EVERY actor, print every actor that would
                                        move with before/after locations, write a receipt; no mutation
  -AronAlignApply                       actually move (checkpoint, re-spawn, save, reopen, read back)
  -AronAlignAllowNotRecommended         required in addition to -AronAlignApply for a target whose spec
                                        says "recommended": false (Main50)
  Neither -AronAlignDryRun nor -AronAlignApply -> usage is printed and nothing happens.

Offline (no Unreal):  python Scripts/release_aron_alignment.py [--target Candidate48] [--dry-run]
  --dry-run classifies the read-only main-map inventory receipt as a preview of the live classification.

Safety model (after release_kotel_stone_v2.py / release_aron_poles.py):
  * Refuses the wrong project directory, a game world, dirty packages before and after load, a
    loaded world other than the target, a map whose SHA-256 differs from the spec's lastKnown value,
    an Aron not at the expected pre-move location, a descriptor count/value other than expected,
    and ANY actor that does not classify into exactly one bucket (Temple / context / global /
    frame-adapted).  Refusal happens before the checkpoint when possible and always before save.
  * Copies the .umap (and OFPA folders) to ReviewCheckpoints/AronAlignment-<stamp>/ and verifies the
    copy hash before any mutation.  Protected maps are hashed before and after.
  * Whole-scene snapshot once before and once after; non-Temple actors must be numerically unchanged
    (pose, meshes, label) before save and after reopen; Temple actors must equal snapshot + delta.
  * StaticMeshActors are RE-SPAWNED at the new location (static mobility does not reliably dirty a
    package on a transform change); the old actor is destroyed only after the new one reads back.
    The few non-static-mesh Temple actors (PlayerStart, cameras, lights, residents, sound) use the
    modify(True) + set_actor_location pattern proven by release_amah48_frame.py.
  * Saves only after every readback passes, reopens the map and reads everything back again; the
    receipt SourceAssets/scale-review/aron-alignment-release-<stamp>.json is written at start, after
    each phase and in finally, so a failure leaves its evidence on disk.
"""
import hashlib
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_aron_alignment.spec.json'
INVENTORY_FOR_OFFLINE_PREVIEW = ROOT / 'SourceAssets' / 'scale-review' / 'native-scale-inventory-20260908T133142315573Z.json'


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='umap'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    for name, target in spec['targets'].items():
        if disk_path(target['map']) != ROOT / target['mapFile']:
            raise RuntimeError('Spec map/mapFile disagree for ' + name)
        d = target['deltaCm']
        if len(d) != 3 or d[2] != 0.0:
            raise RuntimeError('This script is XY only; deltaCm[2] must be 0 for ' + name)
        if target.get('descriptor'):
            ratio = 48.0 / 50.0
            pivot = target['descriptor']['after']
            # scaling legacy point P about pivot Q by r: Q + (P - Q) r = rP + Q (1 - r)  ->  translation Q (1 - r)
            implied = [p * (1.0 - ratio) for p in pivot]
            if max(abs(implied[i] - d[i]) for i in range(3)) > 1e-6:
                raise RuntimeError('Descriptor pivot %r does not imply deltaCm %r for %s (implied %r)' % (pivot, d, name, implied))
    return spec


def offline_check(spec, target_name):
    target = spec['targets'][target_name]
    map_file = ROOT / target['mapFile']
    result = {'spec': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'target': target_name, 'map': target['map'],
              'mapFileExists': map_file.is_file(), 'mapSha256': sha256_of(map_file) if map_file.is_file() else None,
              'mapMatchesLastKnown': map_file.is_file() and sha256_of(map_file) == target['lastKnownMapSha256'],
              'deltaCm': target['deltaCm'], 'recommended': target['recommended'], 'reason': target['reason']}
    dome = spec['domeOfTheRockCentroidCm']
    before = target['aron']['expectedLocationBeforeCm']
    after = [before[0] + target['deltaCm'][0], before[1] + target['deltaCm'][1]]
    result['aronBeforeCm'] = before
    result['aronAfterCm'] = after + [before[2]]
    result['aronAfterToDomeCentroidCm'] = round(math.hypot(after[0] - dome[0], after[1] - dome[1]), 3)
    if result['aronAfterToDomeCentroidCm'] > spec['verification']['aronToDomeCentroidMaxCm']:
        raise RuntimeError('Planned Aron position is outside the rock uncertainty radius')
    return result


# --------------------------------------------------------------------------------------------
# Classification (pure; shared by offline preview and the live run)
# --------------------------------------------------------------------------------------------

class Classifier:
    def __init__(self, spec):
        c = spec['classification']
        self.temple_mesh = tuple(c['templeMeshPrefixes'])
        self.temple_label = tuple(c['templeLabelPrefixes'])
        self.temple_classes = set(c['templeMovableClasses'])
        self.temple_half = float(c['templeMovableClassesRequireInsideHalfCm'])
        self.context_mesh = tuple(c['contextMeshPrefixes'])
        self.context_label = tuple(c['contextLabelPrefixes'])
        self.context_classes = set(c['contextClasses'])
        self.global_classes = set(c['globalClasses'])
        self.frame_classes = set(c['frameAdaptedClasses']['classes'])

    def bucket(self, label, class_name, meshes, location):
        """Returns one of temple_respawn / temple_move / context / global / frame / UNKNOWN / AMBIGUOUS."""
        votes = set()
        meshes = [m for m in meshes if m]
        if class_name in self.global_classes:
            votes.add('global')
        if class_name in self.frame_classes:
            votes.add('frame')
        if class_name in self.context_classes or label.startswith(self.context_label) or any(m.startswith(self.context_mesh) for m in meshes):
            votes.add('context')
        is_temple_geometry = any(m.startswith(self.temple_mesh) for m in meshes) or label.startswith(self.temple_label)
        if class_name == 'StaticMeshActor':
            if is_temple_geometry:
                votes.add('temple_respawn')
        elif class_name in self.temple_classes:
            inside = abs(location[0]) <= self.temple_half and abs(location[1]) <= self.temple_half
            if inside or is_temple_geometry:
                votes.add('temple_move')
            elif class_name == 'CameraActor':
                votes.add('global')   # a distant framing camera (e.g. "04 Entire Temple" at 155 m) is not Temple geometry
        elif is_temple_geometry and class_name not in self.global_classes and class_name not in self.frame_classes:
            votes.add('temple_move')
        if not votes:
            return 'UNKNOWN'
        if len(votes) > 1:
            # a context label wins over a Temple-mesh vote only if nothing Temple-specific voted
            if votes == {'context', 'temple_respawn'} or votes == {'context', 'temple_move'}:
                return 'AMBIGUOUS'
            return 'AMBIGUOUS'
        return votes.pop()


def offline_preview(spec, target_name):
    """Classify the read-only main-map inventory as a preview of what the live run would move."""
    inventory = json.loads(INVENTORY_FOR_OFFLINE_PREVIEW.read_text(encoding='utf-8-sig'))
    classifier = Classifier(spec)
    delta = spec['targets'][target_name]['deltaCm']
    buckets = {}
    moves = []
    problems = []
    for a in inventory['actors']:
        label = a['label'] or a['name']
        cls = a['classPath'].split('.')[-1]
        meshes = [c.get('mesh') or '' for c in a.get('components', [])]
        b = classifier.bucket(label, cls, meshes, a['locationCm'])
        buckets[b] = buckets.get(b, 0) + 1
        if b.startswith('temple'):
            moves.append({'name': a['name'], 'label': label, 'class': cls, 'method': 'respawn' if b == 'temple_respawn' else 'modify+move',
                          'before': a['locationCm'], 'after': [a['locationCm'][i] + delta[i] for i in range(3)]})
        elif b in ('UNKNOWN', 'AMBIGUOUS'):
            problems.append({'name': a['name'], 'label': label, 'class': cls, 'bucket': b, 'meshes': meshes[:2]})
    return {'source': 'inventory preview (main map 2026-09-08T13:31Z), not the live target map', 'inventorySha256': sha256_of(INVENTORY_FOR_OFFLINE_PREVIEW),
            'buckets': buckets, 'wouldMove': len(moves), 'problems': problems, 'moves': moves}


# --------------------------------------------------------------------------------------------
# Engine helpers
# --------------------------------------------------------------------------------------------

def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def _pose(actor):
    r = actor.get_actor_rotation()
    return {'location': _vec(actor.get_actor_location()), 'rotation': [float(r.pitch), float(r.yaw), float(r.roll)], 'scale': _vec(actor.get_actor_scale3d())}


def _bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z], 'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}


def _max_abs_diff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


class Job:
    def __init__(self, ue, spec, target_name, apply):
        self.ue = ue
        self.spec = spec
        self.target_name = target_name
        self.target = spec['targets'][target_name]
        self.apply = apply
        self.classifier = Classifier(spec)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        folder = ROOT / spec['receiptFolder']
        folder.mkdir(parents=True, exist_ok=True)
        self.receipt_path = folder / ('%s%s-%s.json' % (spec['receiptPrefix'], target_name, self.stamp))
        self.receipt = {'status': 'started', 'apply': apply, 'dryRun': not apply, 'stamp': self.stamp, 'target': target_name,
                        'map': self.target['map'], 'deltaCm': self.target['deltaCm'], 'recommended': self.target['recommended'],
                        'specSha256': sha256_of(SPEC_PATH), 'scriptSha256': sha256_of(__file__),
                        'engineVersion': ue.SystemLibrary.get_engine_version(), 'mapSaved': False, 'errors': [], 'moved': [], 'problems': []}

    def write(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    # -- snapshot -----------------------------------------------------------------------------

    def snapshot(self):
        ue = self.ue
        rows = {}
        handles = {}
        for actor in self.actors.get_all_level_actors():
            comps = []
            for c in actor.get_components_by_class(ue.StaticMeshComponent):
                comps.append({'name': c.get_name(), 'mesh': _asset_path(c.get_editor_property('static_mesh')),
                              'materials': [_asset_path(c.get_material(i)) for i in range(c.get_num_materials())],
                              'collision': str(c.get_collision_profile_name()), 'collisionEnabled': str(c.get_collision_enabled()),
                              'mobility': str(c.get_editor_property('mobility')),
                              'visible': bool(c.get_editor_property('visible')), 'hidden': bool(c.get_editor_property('hidden_in_game')),
                              'castShadow': bool(c.get_editor_property('cast_shadow'))})
            name = actor.get_name()
            rows[name] = {'label': actor.get_actor_label(), 'class': actor.get_class().get_name(), 'folder': str(actor.get_folder_path()),
                          'tags': [str(t) for t in actor.get_editor_property('tags')], 'pose': _pose(actor), 'bounds': _bounds(actor), 'components': comps}
            handles[name] = actor
        return rows, handles

    def classify_all(self, rows):
        plan = {'temple_respawn': [], 'temple_move': [], 'context': [], 'global': [], 'frame': []}
        problems = []
        for name, row in rows.items():
            b = self.classifier.bucket(row['label'], row['class'], [c['mesh'] for c in row['components']], row['pose']['location'])
            if b in plan:
                plan[b].append(name)
            else:
                problems.append({'name': name, 'label': row['label'], 'class': row['class'], 'bucket': b,
                                 'meshes': [c['mesh'] for c in row['components']][:2], 'location': row['pose']['location']})
        return plan, problems

    def check_aron(self, rows):
        label = self.target['aron']['label']
        matches = [n for n, r in rows.items() if r['label'] == label]
        if len(matches) != 1:
            raise RuntimeError('Expected exactly one %s, found %d' % (label, len(matches)))
        loc = rows[matches[0]]['pose']['location']
        if _max_abs_diff(loc, self.target['aron']['expectedLocationBeforeCm']) > self.spec['verification']['transformToleranceCm']:
            raise RuntimeError('%s is at %r, not the expected %r' % (label, loc, self.target['aron']['expectedLocationBeforeCm']))
        return matches[0], loc

    def check_descriptor(self, handles):
        d = self.target.get('descriptor')
        if not d:
            return None
        cls = getattr(self.ue, d['className'], None)
        if cls is None:
            raise RuntimeError('Compiled class %s missing' % d['className'])
        found = [a for a in handles.values() if isinstance(a, cls)]
        if len(found) != d['expectedCount']:
            raise RuntimeError('Expected %d %s descriptors, found %d' % (d['expectedCount'], d['className'], len(found)))
        value = _vec(found[0].get_editor_property(d['property']))
        if _max_abs_diff(value, d['before']) > 1e-6:
            raise RuntimeError('Descriptor %s is %r, expected %r' % (d['property'], value, d['before']))
        return found[0], value

    # -- mutation -------------------------------------------------------------------------------

    def respawn(self, actor, row, delta):
        """Spawn a fresh StaticMeshActor at row.location + delta with the same mesh/materials/flags; destroy the old one after readback."""
        ue = self.ue
        tol = self.spec['verification']['transformToleranceCm']
        src = row['components']
        if len(src) != 1:
            raise RuntimeError('%s has %d static mesh components; only single-component actors are re-spawned' % (row['label'], len(src)))
        old_comp = actor.get_component_by_class(ue.StaticMeshComponent)
        mesh = old_comp.get_editor_property('static_mesh')
        loc = [row['pose']['location'][i] + delta[i] for i in range(3)]
        rot = row['pose']['rotation']
        new = self.actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(*loc), ue.Rotator(pitch=rot[0], yaw=rot[1], roll=rot[2]), transient=False)
        if new is None:
            raise RuntimeError('spawn_actor_from_class returned None for ' + row['label'])
        try:
            comp = new.get_component_by_class(ue.StaticMeshComponent)
            comp.set_editor_property('mobility', old_comp.get_editor_property('mobility'))
            if not comp.set_static_mesh(mesh):
                raise RuntimeError('set_static_mesh failed for ' + row['label'])
            for i in range(old_comp.get_num_materials()):
                comp.set_material(i, old_comp.get_material(i))
            comp.set_collision_profile_name(old_comp.get_collision_profile_name())
            comp.set_collision_enabled(old_comp.get_collision_enabled())
            comp.set_editor_property('visible', old_comp.get_editor_property('visible'))
            comp.set_editor_property('hidden_in_game', old_comp.get_editor_property('hidden_in_game'))
            comp.set_editor_property('cast_shadow', old_comp.get_editor_property('cast_shadow'))
            new.set_actor_scale3d(ue.Vector(*row['pose']['scale']))
            new.set_actor_label(row['label'])
            new.set_folder_path(ue.Name(row['folder']) if row['folder'] and row['folder'] != 'None' else ue.Name(''))
            new.set_editor_property('tags', [ue.Name(t) for t in row['tags']])
            pose = _pose(new)
            if _max_abs_diff(pose['location'], loc) > tol or _max_abs_diff(pose['rotation'], rot) > tol or _max_abs_diff(pose['scale'], row['pose']['scale']) > tol:
                raise RuntimeError('Re-spawned %s pose differs from plan' % row['label'])
            if _asset_path(comp.get_editor_property('static_mesh')) != src[0]['mesh']:
                raise RuntimeError('Re-spawned %s mesh differs' % row['label'])
            mats = [_asset_path(comp.get_material(i)) for i in range(comp.get_num_materials())]
            if mats != src[0]['materials']:
                raise RuntimeError('Re-spawned %s materials differ: %r vs %r' % (row['label'], mats, src[0]['materials']))
            expected_bounds = {k: [row['bounds'][k][i] + delta[i] for i in range(3)] for k in ('min', 'max')}
            got = _bounds(new)
            err = max(abs(got[k][i] - expected_bounds[k][i]) for k in ('min', 'max') for i in range(3))
            if err > self.spec['verification']['boundsToleranceCm']:
                raise RuntimeError('Re-spawned %s bounds differ by %.4f cm' % (row['label'], err))
        except Exception:
            self.actors.destroy_actor(new)
            raise
        if not self.actors.destroy_actor(actor):
            raise RuntimeError('destroy_actor failed for the old ' + row['label'])
        return {'oldName': None, 'newName': new.get_name(), 'label': row['label'], 'method': 'respawn', 'before': row['pose']['location'], 'after': loc, 'boundsErrorCm': err}

    def move(self, actor, row, delta):
        ue = self.ue
        loc = [row['pose']['location'][i] + delta[i] for i in range(3)]
        actor.modify(True)
        root = actor.get_editor_property('root_component')
        if root is not None:
            root.modify(True)
        if not actor.set_actor_location(ue.Vector(*loc), False, True):
            raise RuntimeError('set_actor_location failed for ' + row['label'])
        got = _vec(actor.get_actor_location())
        if _max_abs_diff(got, loc) > self.spec['verification']['transformToleranceCm']:
            raise RuntimeError('%s did not land on the planned location' % row['label'])
        return {'oldName': actor.get_name(), 'newName': actor.get_name(), 'label': row['label'], 'method': 'modify+move', 'before': row['pose']['location'], 'after': got}

    # -- verification -----------------------------------------------------------------------------

    def verify_after(self, before_rows, plan, delta, phase):
        rows, handles = self.snapshot()
        tol = self.spec['verification']['transformToleranceCm']
        errors = []
        by_label_after = {}
        for name, row in rows.items():
            by_label_after.setdefault((row['label'], row['class']), []).append(row)
        # non-Temple actors unchanged (matched by native name)
        for bucket in ('context', 'global', 'frame'):
            for name in plan[bucket]:
                if name not in rows:
                    errors.append('%s actor %s vanished' % (bucket, before_rows[name]['label']))
                    continue
                a, b = before_rows[name], rows[name]
                if a['label'] != b['label'] or a['components'] != b['components'] or _max_abs_diff(a['pose']['location'], b['pose']['location']) > tol \
                        or _max_abs_diff(a['pose']['rotation'], b['pose']['rotation']) > tol or _max_abs_diff(a['pose']['scale'], b['pose']['scale']) > tol:
                    errors.append('%s actor %s changed' % (bucket, a['label']))
        # moved actors: matched by (label, class) because re-spawned actors have new native names
        for bucket in ('temple_respawn', 'temple_move'):
            for name in plan[bucket]:
                a = before_rows[name]
                expected = [a['pose']['location'][i] + delta[i] for i in range(3)]
                candidates = by_label_after.get((a['label'], a['class']), [])
                hit = [r for r in candidates if _max_abs_diff(r['pose']['location'], expected) <= tol and _max_abs_diff(r['pose']['rotation'], a['pose']['rotation']) <= tol
                       and _max_abs_diff(r['pose']['scale'], a['pose']['scale']) <= tol and [c['mesh'] for c in r['components']] == [c['mesh'] for c in a['components']]]
                if len(hit) != 1:
                    errors.append('%s: expected exactly one %s at %r after %s, found %d' % (bucket, a['label'], expected, phase, len(hit)))
        if len(rows) != len(before_rows):
            errors.append('actor count %d after %s differs from %d before' % (len(rows), phase, len(before_rows)))
        if errors:
            raise RuntimeError('Verification failed after %s: %s' % (phase, errors[:20]))
        return rows, handles

    def check_aron_after(self, rows):
        label = self.target['aron']['label']
        matches = [r for r in rows.values() if r['label'] == label]
        if len(matches) != 1:
            raise RuntimeError('Aron count after move: %d' % len(matches))
        loc = matches[0]['pose']['location']
        dome = self.spec['domeOfTheRockCentroidCm']
        dist = math.hypot(loc[0] - dome[0], loc[1] - dome[1])
        if dist > self.spec['verification']['aronToDomeCentroidMaxCm']:
            raise RuntimeError('Aron after move is %.1f cm from the Dome centroid' % dist)
        return {'locationCm': loc, 'domeCentroidCm': dome, 'distanceCm': round(dist, 3)}


# --------------------------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------------------------

def run(target_name, apply=False, allow_not_recommended=False):
    import unreal as ue
    spec = load_spec()
    if target_name not in spec['targets']:
        raise RuntimeError('Unknown target %r; expected one of %s' % (target_name, sorted(spec['targets'])))
    target = spec['targets'][target_name]
    offline = offline_check(spec, target_name)
    if apply and not target['recommended'] and not allow_not_recommended:
        raise RuntimeError('Target %s is not recommended by the spec (%s); pass -AronAlignAllowNotRecommended to override' % (target_name, target['reason']))
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    job = Job(ue, spec, target_name, apply)
    job.receipt['offlineCheck'] = offline
    job.receipt['allowNotRecommended'] = allow_not_recommended
    job.write()
    if job.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before the run')
    map_file = ROOT / target['mapFile']
    map_sha_before = sha256_of(map_file)
    job.receipt['mapSha256Before'] = map_sha_before
    job.receipt['mapMatchesLastKnown'] = map_sha_before == target['lastKnownMapSha256']
    if apply and not job.receipt['mapMatchesLastKnown']:
        raise RuntimeError('Map SHA-256 %s differs from the reviewed spec value; re-run plan_aron_alignment.py and review before applying' % map_sha_before)
    protected = {m: sha256_of(disk_path(m)) for m in target['protectedMaps'] if disk_path(m).exists()}
    job.receipt['protectedBefore'] = protected

    if not job.levels.load_level(target['map']):
        raise RuntimeError('load_level failed for ' + target['map'])
    world = job.editor.get_editor_world()
    if world.get_outermost().get_name() != target['map']:
        raise RuntimeError('Loaded world %s is not the target' % world.get_outermost().get_name())
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present after loading the map')

    rows, handles = job.snapshot()
    plan, problems = job.classify_all(rows)
    job.receipt['actorCountBefore'] = len(rows)
    job.receipt['bucketCounts'] = {k: len(v) for k, v in plan.items()}
    job.receipt['problems'] = problems
    aron_name, aron_loc = job.check_aron(rows)
    job.receipt['aronBefore'] = {'name': aron_name, 'locationCm': aron_loc}
    descriptor = job.check_descriptor(handles)
    if descriptor:
        job.receipt['descriptorBefore'] = descriptor[1]
    delta = target['deltaCm']
    would_move = []
    for bucket, method in (('temple_respawn', 'respawn'), ('temple_move', 'modify+move')):
        for name in plan[bucket]:
            r = rows[name]
            would_move.append({'name': name, 'label': r['label'], 'class': r['class'], 'method': method, 'before': r['pose']['location'],
                               'after': [r['pose']['location'][i] + delta[i] for i in range(3)]})
    job.receipt['wouldMove'] = would_move
    job.receipt['wouldMoveCount'] = len(would_move)
    job.write()

    if not apply:
        for m in would_move:
            ue.log('DRY RUN %-12s %-45s %-24s %r -> %r' % (m['method'], m['label'][:45], m['class'], [round(v, 2) for v in m['before']], [round(v, 2) for v in m['after']]))
        for p in problems:
            ue.log_warning('DRY RUN UNCLASSIFIED %r' % p)
        job.receipt['status'] = 'dry_run_complete_nothing_mutated' if not problems else 'dry_run_complete_with_unclassified_actors_apply_would_refuse'
        job.write()
        return job.receipt
    if problems:
        raise RuntimeError('%d actors did not classify; refusing to apply: %s' % (len(problems), problems[:10]))

    # -- checkpoint ------------------------------------------------------------------------------
    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + target_name + '-' + job.stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / target['map'][len('/Game/'):]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / target['map'][len('/Game/'):])
    job.receipt['checkpoint'] = str(checkpoint)
    job.receipt['status'] = 'checkpointed_move_started'
    job.write()

    saved = False
    try:
        moved = []
        for name in plan['temple_respawn']:
            moved.append(job.respawn(handles[name], rows[name], delta))
        for name in plan['temple_move']:
            moved.append(job.move(handles[name], rows[name], delta))
        job.receipt['moved'] = moved
        if descriptor:
            d = target['descriptor']
            actor = descriptor[0]
            actor.modify(True)
            actor.set_editor_property(d['property'], ue.Vector(*d['after']))
            got = _vec(actor.get_editor_property(d['property']))
            if _max_abs_diff(got, d['after']) > 1e-6:
                raise RuntimeError('Descriptor readback %r differs from %r' % (got, d['after']))
            job.receipt['descriptorAfter'] = got
        after_rows, _ = job.verify_after(rows, plan, delta, 'move')
        job.receipt['aronAfter'] = job.check_aron_after(after_rows)
        job.receipt['status'] = 'verified_before_save'
        job.write()
        if not job.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        job.receipt['mapSaved'] = True
        job.receipt['mapSha256After'] = sha256_of(map_file)
        job.receipt['mapBytesChanged'] = job.receipt['mapSha256After'] != map_sha_before
        job.receipt['protectedAfter'] = {m: sha256_of(disk_path(m)) for m in target['protectedMaps'] if disk_path(m).exists()}
        job.receipt['protectedUnchanged'] = job.receipt['protectedAfter'] == protected
        if not job.receipt['protectedUnchanged']:
            raise RuntimeError('A protected map changed on disk')
        if not job.levels.load_level(target['map']) or job.editor.get_editor_world().get_outermost().get_name() != target['map']:
            raise RuntimeError('Reopen failed')
        reopened_rows, reopened_handles = job.verify_after(rows, plan, delta, 'reopen')
        job.receipt['aronReopened'] = job.check_aron_after(reopened_rows)
        if descriptor:
            cls = getattr(ue, target['descriptor']['className'])
            found = [a for a in reopened_handles.values() if isinstance(a, cls)]
            got = _vec(found[0].get_editor_property(target['descriptor']['property']))
            if len(found) != 1 or _max_abs_diff(got, target['descriptor']['after']) > 1e-6:
                raise RuntimeError('Descriptor after reopen %r' % got)
            job.receipt['descriptorReopened'] = got
        job.receipt['actorCountAfter'] = len(reopened_rows)
        job.receipt['restore'] = {'howTo': 'Copy the checkpoint .umap (and OFPA folders) back over the target map.', 'checkpoint': str(checkpoint)}
        job.receipt['status'] = 'aligned_saved_reopened_runtime_acceptance_pending'
        job.write()
        return job.receipt
    except Exception as error:
        job.receipt['errors'].append(repr(error))
        job.receipt['status'] = 'failed_after_save_checkpoint_available' if saved else 'failed_before_save_nothing_saved'
        job.write()
        raise
    finally:
        job.write()


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_aron_alignment.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _switches(tokens):
    target = None
    for token in tokens:
        if token.startswith('-aronaligntarget='):
            target = token.split('=', 1)[1].strip('"')
    names = {'main50': 'Main50', 'candidate48': 'Candidate48'}
    return {'target_name': names.get(target) if target else None, 'dry_run': '-aronaligndryrun' in tokens, 'apply': '-aronalignapply' in tokens,
            'allow_not_recommended': '-aronalignallownotrecommended' in tokens}


USAGE = ('release_aron_alignment: nothing done. Pass -AronAlignTarget=Main50|Candidate48 with -AronAlignDryRun (no mutation) '
         'or -AronAlignApply (mutates after checkpoint). Apply defaults OFF.')


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    switches = _switches(command_line.split())
    try:
        if switches['target_name'] is None or not (switches['dry_run'] or switches['apply']):
            ue.log_warning(USAGE)
            return
        if switches['dry_run'] and switches['apply']:
            raise RuntimeError('-AronAlignDryRun and -AronAlignApply are mutually exclusive')
        receipt = run(switches['target_name'], apply=switches['apply'], allow_not_recommended=switches['allow_not_recommended'])
        ue.log('release_aron_alignment: %s wouldMove=%s moved=%s' % (receipt['status'], receipt.get('wouldMoveCount'), len(receipt.get('moved', []))))
    except Exception as error:
        ue.log_error('release_aron_alignment failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        args = sys.argv[1:]
        target_name = 'Candidate48'
        if '--target' in args:
            target_name = args[args.index('--target') + 1]
        spec = load_spec()
        out = {'offlineCheck': offline_check(spec, target_name)}
        if '--dry-run' in args:
            preview = offline_preview(spec, target_name)
            out['inventoryPreview'] = {k: v for k, v in preview.items() if k != 'moves'}
            out['inventoryPreview']['firstMoves'] = preview['moves'][:5]
        print(json.dumps(out, indent=2))
elif _invoked_as_native_script():
    _main()

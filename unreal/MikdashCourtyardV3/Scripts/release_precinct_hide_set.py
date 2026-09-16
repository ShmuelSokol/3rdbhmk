"""PrecinctHideSetV1 - retarget the placed enclosure from the SQUARE to the HARAM RING.

AUTHORED_OFFLINE_SOURCE for its inputs; this file is the guarded NATIVE step. It edits exactly
one actor - the placed AMikdashEnclosure - and changes exactly three properties on it. It
imports nothing, creates no asset, spawns and destroys no actor, and saves the map once.

WHY A SEPARATE SCRIPT AND NOT release_enclosure.py
---------------------------------------------------
`release_enclosure.place()` REFUSES when an EnclosureV2 actor already exists (its own docstring
and guard), and `repair=True` only re-points mesh properties - "Nothing else on the actor
changes". Neither can retarget a placed actor's hide set. So this does that one job, with the
same guard shape: checkpoint before mutation, previous values recorded for revert, save once at
the end, readback in a FRESH process.

WHAT IT CHANGES, AND WHY EACH ONE
----------------------------------
1. `ExplicitHideLabels`    270 square labels -> 49 ring labels.
2. `ExplicitHideMeshNames` derived from those labels by the spec's hideListMeshNameRule.
   Together these are the whole of S4: 221 modern building actors come back into view with no
   geometry moved, because the built precinct is now today's Temple Mount outline and those
   buildings no longer stand inside it.
3. `bBuildPlaza` true -> false.
   DECISION, coordinator, 16 September 2026, recorded rather than assumed. The plaza is a
   2.07 km2 flat deck at Z 0 built for the 3000-amah square - a boundary the owner replaced on
   15 September. Left on, it renders at BeginPlay and BURIES the 221 buildings this pass
   restores: the frame would appear to confirm the change while misrepresenting it. It is not
   a feature being switched off; it is the artefact of the square, and S5 rebuilds it on the
   ring. One boolean, previous value recorded, fully revertible.

WHAT IT DELIBERATELY DOES NOT CHANGE
-------------------------------------
The wall ring. The enclosure still builds the 3000-amah SQUARE wall - 6 amot (about 2.9 m)
high, running through the restored city. That is a STATED LIMITATION of this stage, not a
defect to hide: re-planning the wall on the 66-point ring is S5. Any frame taken now is
captioned "city restored, boundary not yet rebuilt".

MODES
  -HideSetPreflight  read-only: actor found, current values, what would change. Saves nothing.
  -HideSetApply      set the three properties, save. Readback is -HideSetVerify, fresh process.
  -HideSetVerify     reopen-style readback only. Saves nothing.
  -HideSetRevert     restore the values recorded by the apply receipt, save.

MEMORY (AGENTS.md, 16 Sep): this script touches NO mesh data at any point - only actor
properties and labels - so it never triggers the level's static-mesh compilation flush. Run it
with -asyncstaticmeshcompilationmaxconcurrency=1 anyway; it costs nothing.
"""
import hashlib
import json
import re
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SCRIPT_TOKEN = 'release_precinct_hide_set.py'
REVIEW = ROOT / 'SourceAssets' / 'enclosure-review'
RECEIPTS = REVIEW / 'HideSetV1'
SPEC_PATH = ROOT / 'Scripts' / 'release_enclosure.spec.json'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
ENCLOSURE_LABEL = 'RELEASE_EnclosureV2_Precinct'
TARGETS = {
    'Candidate48': dict(map='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
                        receipt='SourceAssets/enclosure-review/precinct-Candidate48.json'),
    'Main50': dict(map='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
                   receipt='SourceAssets/enclosure-review/precinct-Main50.json'),
}


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    return ROOT / 'Content' / (asset_path[len('/Game/'):] + '.' + extension)


def all_maps():
    return sorted(str(p) for p in (ROOT / 'Content').rglob('*.umap'))


def fnv1a_labels(labels):
    fingerprint = 1469598103934665603
    for label in sorted(labels):
        for byte in label.encode('utf-8'):
            fingerprint ^= byte
            fingerprint = (fingerprint * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return '%016x' % fingerprint


def mesh_name_for_label(spec, label):
    for prefix, mesh_prefix in spec['hideListMeshNameRule'].items():
        if label.startswith(prefix):
            return mesh_prefix + label[len(prefix):]
    return None


def load_inputs(target):
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    receipt = json.loads((ROOT / TARGETS[target]['receipt']).read_text(encoding='utf-8-sig'))
    if receipt.get('builtBoundary') != 'haramRing':
        raise RuntimeError('precinct receipt builtBoundary is %r, not haramRing; re-run '
                           'Scripts/create_haram_outline.py --export then create_enclosure.py --export'
                           % receipt.get('builtBoundary'))
    ring = receipt.get('modernCityRing')
    if not ring:
        raise RuntimeError('precinct receipt carries no modernCityRing')
    labels = sorted(ring['labels'])
    if not labels:
        raise RuntimeError('ring hide set is empty')
    if fnv1a_labels(labels) != ring['labelFingerprintFnv1a']:
        raise RuntimeError('ring hide set fingerprint does not reproduce from its own labels')
    still_whole = [c for c in ring.get('cutCells', []) if c.get('decision') != 'split']
    if still_whole:
        raise RuntimeError('%d cut cells are still set to hide whole; that would destroy %d '
                           'buildings outside the ring. Run create_precinct_cell_split.py --export '
                           'and release_precinct_cell_split.py -SplitApply first.'
                           % (len(still_whole), sum(c['componentsOutside'] for c in still_whole)))
    bad = [l for l in labels if not any(l.startswith(p) for p in spec['modernBuildingLabelPrefixes'])]
    if bad:
        raise RuntimeError('ring hide set carries labels outside the modern-building prefixes: %r' % bad[:5])
    meshes = [mesh_name_for_label(spec, l) for l in labels]
    if any(m is None for m in meshes):
        raise RuntimeError('a hide label has no mesh-name rule')
    return spec, receipt, labels, meshes


class Run(object):
    def __init__(self, ue, target, mode):
        self.ue = ue
        self.target = target
        self.mode = mode
        self.stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        RECEIPTS.mkdir(parents=True, exist_ok=True)
        self.path = RECEIPTS / ('hide-set-%s-%s-%s.json' % (mode, target, self.stamp))
        self.receipt = {'status': 'running', 'mode': mode, 'target': target, 'stamp': self.stamp,
                        'script': SCRIPT_TOKEN, 'scriptSha256': sha256_of(ROOT / 'Scripts' / SCRIPT_TOKEN),
                        'engineVersion': str(ue.SystemLibrary.get_engine_version())}
        self._labels = None

    def write(self):
        self.path.write_text(json.dumps(self.receipt, indent=1), encoding='utf-8')

    def enclosure(self):
        # ONE enumeration, labels only - never touches mesh data. See AGENTS.md 16 Sep.
        if self._labels is None:
            self._labels = {a.get_actor_label(): a for a in self.actors.get_all_level_actors()}
        actor = self._labels.get(ENCLOSURE_LABEL)
        if actor is None:
            raise RuntimeError('%s is not in this map' % ENCLOSURE_LABEL)
        return actor

    def snapshot(self, actor):
        return dict(
            explicitHideLabels=[str(x) for x in actor.get_editor_property('ExplicitHideLabels')],
            explicitHideMeshNames=[str(x) for x in actor.get_editor_property('ExplicitHideMeshNames')],
            bBuildPlaza=bool(actor.get_editor_property('bBuildPlaza')))

    def resolve(self, labels):
        """How many of the wanted labels actually exist in this map."""
        present = set(self._labels or {})
        missing = [l for l in labels if l not in present]
        return missing


def run(target, mode, revert_receipt=None, allow_missing=False):
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('wrong project')
    r = Run(ue, target, mode)
    map_path = TARGETS[target]['map']
    map_file = disk_path(map_path, 'umap')
    saved = False
    others = [m for m in all_maps() if Path(m) != map_file]
    protected = {m: sha256_of(m) for m in others}
    before = sha256_of(map_file)
    r.receipt.update({'map': map_path, 'mapSha256Before': before, 'protectedSha256Before': protected})
    r.write()
    try:
        spec, precinct, labels, meshes = load_inputs(target)
        r.receipt['ringLabelCount'] = len(labels)
        r.receipt['ringFingerprint'] = fnv1a_labels(labels)
        r.receipt['haramRing'] = {k: v for k, v in (precinct.get('haramRing') or {}).items()
                                  if k in ('sha256', 'pointCount', 'areaHectares', 'closureGapCm')}
        r.receipt['squareHideSetReplaced'] = precinct['modernCity']['hideSet']['counts']
        if r.editor.get_game_world():
            raise RuntimeError('a game world is active')
        if not r.levels.load_level(map_path):
            raise RuntimeError('load_level failed')
        world = r.editor.get_editor_world()
        if world.get_outermost().get_name() != map_path:
            raise RuntimeError('loaded world is not the target')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('dirty map packages before mutation')

        actor = r.enclosure()
        current = r.snapshot(actor)
        r.receipt['before'] = dict(current, explicitHideLabels=len(current['explicitHideLabels']),
                                   explicitHideMeshNames=len(current['explicitHideMeshNames']))
        missing = r.resolve(labels)
        r.receipt['labelsMissingInMap'] = missing
        r.receipt['splitOutActorsPresent'] = sum(
            1 for l in (r._labels or {}) if l.startswith('RELEASE_PrecinctCellSplit_'))

        if mode == 'preflight':
            r.receipt['wouldSet'] = dict(explicitHideLabels=len(labels), bBuildPlaza=False)
            r.receipt['status'] = 'preflight_ok_nothing_saved'
            return r.receipt
        if mode == 'verify':
            want = [l for l in labels if l not in set(missing)]
            ok = (sorted(current['explicitHideLabels']) == sorted(want)
                  and sorted(current['explicitHideMeshNames']) == sorted(
                      mesh_name_for_label(spec, l) for l in want)
                  and current['bBuildPlaza'] is False)
            r.receipt['expectedLabelCount'] = len(want)
            r.receipt['labelsDroppedMissing'] = missing
            r.receipt['matchesRingHideSet'] = ok
            r.receipt['observed'] = dict(labels=len(current['explicitHideLabels']),
                                         meshNames=len(current['explicitHideMeshNames']),
                                         bBuildPlaza=current['bBuildPlaza'],
                                         fingerprint=fnv1a_labels(current['explicitHideLabels']))
            if not ok:
                raise RuntimeError('placed actor does not carry the ring hide set')
            r.receipt['status'] = 'verified_read_back_nothing_saved'
            return r.receipt
        if missing and not allow_missing:
            raise RuntimeError('%d hide labels do not resolve in this map: %r. Pass '
                               '-HideSetAllowMissing to apply the resolvable subset, and read '
                               'labelsDroppedMissing in the receipt before you do.'
                               % (len(missing), missing[:5]))
        if missing:
            # Deliberate, acknowledged, and RECORDED - never silent. Same precedent as
            # release_enclosure.spec.json's -EnclosureAllowMissingHideLabels.
            r.receipt['labelsDroppedMissing'] = missing
            r.receipt['labelsDroppedNote'] = (
                'These labels are in the computed ring hide set but NO ACTOR carries them in '
                'this map, so there is nothing to hide. This is PRE-EXISTING, not introduced '
                'by this pass: the square hide set computes 270 labels and the placed actor has '
                'only ever carried 269, dropping the same one. SM_JerusalemBuildings_Large_07279 '
                'is Al-Aqsa Mosque (OSM 280309331, X -9449..2622, Y 15887..25507) - its mesh '
                'asset exists on disk but no actor was spawned for it. Consequence: if some '
                'other actor renders Al-Aqsa, it will stand inside the precinct in YECHEZKEL '
                'and this hide set cannot reach it. THE FRAME IS THE CHECK.')
            labels = [l for l in labels if l not in set(missing)]
            meshes = [mesh_name_for_label(spec, l) for l in labels]
            r.receipt['labelsAppliedCount'] = len(labels)

        checkpoint = CHECKPOINT_ROOT / ('PrecinctHideSet-%s-%s-%s' % (mode, target, r.stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != before:
            raise RuntimeError('checkpoint copy hash differs')
        r.receipt['checkpoint'] = str(checkpoint)
        r.write()

        if mode == 'revert':
            prior = json.loads(Path(revert_receipt).read_text(encoding='utf-8-sig'))
            restore = prior.get('beforeFull')
            if not restore:
                raise RuntimeError('revert needs an apply receipt carrying beforeFull')
            actor.set_editor_property('ExplicitHideLabels', restore['explicitHideLabels'])
            actor.set_editor_property('ExplicitHideMeshNames', restore['explicitHideMeshNames'])
            actor.set_editor_property('bBuildPlaza', restore['bBuildPlaza'])
            r.receipt['restoredFrom'] = str(revert_receipt)
        else:
            r.receipt['beforeFull'] = current          # the whole revert payload
            actor.set_editor_property('ExplicitHideLabels', labels)
            actor.set_editor_property('ExplicitHideMeshNames', meshes)
            actor.set_editor_property('bBuildPlaza', False)
            r.receipt['plazaDecision'] = (
                'bBuildPlaza true -> false. Coordinator decision, 16 September 2026. The plaza '
                'is a 2.07 km2 deck at Z 0 built for the 3000-amah square, which the owner '
                'replaced on 15 September; left on it renders at BeginPlay and buries the 221 '
                'buildings this pass restores. S5 rebuilds it on the ring. Previous value is in '
                'beforeFull for revert.')
            r.receipt['wallStillOnSquare'] = (
                'STATED LIMITATION, not a defect: the enclosure still builds the 3000-amah '
                'SQUARE wall (6 amot, about 2.9 m) through the restored city. Re-planning it on '
                'the 66-point ring is S5. Frames from this stage are captioned "city restored, '
                'boundary not yet rebuilt".')

        after = r.snapshot(actor)
        r.receipt['after'] = dict(explicitHideLabels=len(after['explicitHideLabels']),
                                  explicitHideMeshNames=len(after['explicitHideMeshNames']),
                                  bBuildPlaza=after['bBuildPlaza'],
                                  fingerprint=fnv1a_labels(after['explicitHideLabels']))
        if not ue.EditorLoadingAndSavingUtils.save_map(world, map_path):
            raise RuntimeError('save_map failed')
        saved = True
        r.receipt['mapSaved'] = True
        r.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        r.receipt['status'] = ('reverted_saved_verify_pending' if mode == 'revert'
                               else 'applied_saved_verify_pending')
        r.receipt['nextStep'] = ('run -HideSetVerify -SplitTarget in a FRESH editor process; '
                                 'this receipt is not acceptance until that passes')
        return r.receipt
    except Exception as error:
        r.receipt['status'] = 'failed'
        r.receipt['error'] = repr(error)
        r.receipt['traceback'] = traceback.format_exc()
        raise
    finally:
        r.receipt['mapSha256After'] = sha256_of(map_file)
        r.receipt['mapBytesChanged'] = r.receipt['mapSha256After'] != before
        r.receipt['mapSavedFlag'] = saved
        changed = [m for m in others if sha256_of(m) != protected[m]]
        r.receipt['protectedMapsUnchanged'] = not changed
        r.receipt['protectedMapsChanged'] = changed
        r.write()


def _invoked_as_native_script():
    try:
        import unreal as ue
    except ImportError:
        return False
    return SCRIPT_TOKEN.lower() in ue.SystemLibrary.get_command_line().lower()


def _main():
    import unreal as ue
    cl = ue.SystemLibrary.get_command_line()
    lowered = cl.lower()
    modes = [m for f, m in (('-hidesetpreflight', 'preflight'), ('-hidesetapply', 'apply'),
                            ('-hidesetverify', 'verify'), ('-hidesetrevert', 'revert')) if f in lowered]
    if len(modes) != 1:
        raise RuntimeError('exactly one of -HideSetPreflight/-HideSetApply/-HideSetVerify/-HideSetRevert')
    match = re.search(r'-HideSetTarget=(?:"([^"]+)"|(\S+))', cl, re.IGNORECASE)
    name = (match.group(1) or match.group(2)) if match else 'Candidate48'
    names = {'main50': 'Main50', 'candidate48': 'Candidate48'}
    if name.lower() not in names:
        raise RuntimeError('Unknown -HideSetTarget=' + name)
    revert_receipt = None
    if modes[0] == 'revert':
        rm = re.search(r'-HideSetRevertFrom=(?:"([^"]+)"|(\S+))', cl, re.IGNORECASE)
        if not rm:
            raise RuntimeError('-HideSetRevert needs -HideSetRevertFrom=<apply receipt path>')
        revert_receipt = rm.group(1) or rm.group(2)
    allow_missing = '-hidesetallowmissing' in lowered
    try:
        receipt = run(names[name.lower()], modes[0], revert_receipt, allow_missing)
        ue.log('release_precinct_hide_set[%s/%s]: %s' % (names[name.lower()], modes[0], receipt['status']))
    except Exception as error:
        ue.log_error('release_precinct_hide_set failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in lowered and '-run=pythonscript' not in lowered:
            ue.SystemLibrary.quit_editor()


if _invoked_as_native_script():
    _main()

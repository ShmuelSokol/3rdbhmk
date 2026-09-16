"""Remove the illustrative MountAccessV2 stair that spans the Old City alleys. 15 September 2026.

THE DEFECT THIS CLOSES (cp26 review defect D1)
----------------------------------------------
`SourceAssets/visual-review/city-facade/cp26-K1-kotel-plaza-walking-facing-jewish-quarter.png`
(and cp21c/cp24 before it) shows a huge flat-white stepped soffit hanging over the alley.
It is RELEASE_MountAccess_Deck / _Guards / _Portal: the elevated replacement deck, its
parapets and the above-wall portal that `Scripts/create_kotel_opening.py` authored for an
ILLUSTRATIVE future access stair (X -18400..-12500 at Y 19822..20122, 45 cm slabs, so from
below it is a stepped underside). `SourceAssets/context-review/KotelPlazaV1/kotel-plaza-findings.json`
already recorded it: "RELEASE_MountAccess_Deck and _Guards are visible in MODERN ... a
faithful present-day Old City should not show them". They carry no state tag, so the
enclosure never hides them, and their material is the unaccepted `M_JerusalemStoneV2_*Review`
pilot - untextured near-white - which is why they read as white cardboard.

They are not on any tested route: the Kotel stair replay (Scripts/Test-KotelStairRuntime.ps1)
walks the plaza's own flight, and the KotelApproachCorridor crowd zone is fitted to the
surveyed ground route, not to this deck.

WHAT THIS DOES
--------------
Destroys every RELEASE_MountAccess_* actor in the target map. The imported MountAccessV2
assets stay on disk (a namespace is never deleted automatically), so the placement can be
redone, and the checkpointed .umap is the byte-exact undo.

GUARD PATTERN
-------------
checkpoint (.umap copied to ReviewCheckpoints), protected hashes (the other map and the
MountAccessV2 assets), load, readback before, destroy, save, reopen, readback that the
actors are gone and that the total actor count fell by exactly that many, receipt, and an
offline byte-exact revert.

MODES (one per run; commandlet, -nullrhi, never while another engine runs)
  -Candidate48 | -Main50              target map (Candidate48 FIRST - it is the cook map)
  -MountAccessRemoveApply             destroy and save
  -MountAccessRemoveVerify=<receipt>  fresh process; reopen and confirm; saves nothing
Offline, no engine:
  python Scripts/release_remove_mount_access.py --revert=<apply receipt>
"""
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
CHECKPOINTS = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
RECEIPTS = ROOT / 'SourceAssets' / 'context-review' / 'KotelViewsV1'
MAPS = {
    'Candidate48': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'Main50': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}
LABEL_PREFIX = 'RELEASE_MountAccess_'
ASSETS = ['/Game/MikdashV3/ArrivalReview/MountAccessV2/KotelApproach_ElevatedDeck_V2',
          '/Game/MikdashV3/ArrivalReview/MountAccessV2/KotelApproach_ElevatedGuards_V2',
          '/Game/MikdashV3/ArrivalReview/MountAccessV2/KotelApproach_AboveWallPortal_V2']


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk(package, ext='uasset'):
    return ROOT / 'Content' / (package[len('/Game/'):] + '.' + ext)


def other_engines(pid):
    import csv
    import io
    import subprocess
    rows = list(csv.reader(io.StringIO(subprocess.run(
        ['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, check=True, timeout=30).stdout)))
    names = ('unrealeditor.exe', 'unrealeditor-cmd.exe', 'mikdashcourtyardv3.exe')
    return [r[:2] for r in rows if len(r) > 1 and r[0].lower() in names and int(r[1]) != pid]


def read_access(ue):
    rows = []
    for actor in ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors():
        label = actor.get_actor_label()
        if not label.startswith(LABEL_PREFIX):
            continue
        comp = actor.get_component_by_class(ue.StaticMeshComponent)
        mesh = comp.get_editor_property('static_mesh') if comp is not None else None
        origin, extent = actor.get_actor_bounds(False)
        rows.append(dict(actor=actor, label=label, actorName=actor.get_name(),
                         mesh=(mesh.get_path_name().split('.')[0] if mesh is not None else None),
                         tags=[str(t) for t in actor.get_editor_property('tags')],
                         boundsCm=[[round(origin.x - extent.x, 3), round(origin.y - extent.y, 3), round(origin.z - extent.z, 3)],
                                   [round(origin.x + extent.x, 3), round(origin.y + extent.y, 3), round(origin.z + extent.z, 3)]]))
    return sorted(rows, key=lambda r: r['label'])


def public(rows):
    return [{k: v for k, v in r.items() if k != 'actor'} for r in rows]


def run(target, mode, earlier=None):
    import unreal as ue
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = RECEIPTS / ('mount-access-remove-%s-%s-%s.json' % (mode, target, stamp))
    mapfile = disk(MAPS[target], 'umap')
    receipt = dict(status='started', mode=mode, target=target, map=MAPS[target], stamp=stamp,
                   pid=os.getpid(), labelPrefix=LABEL_PREFIX, assetsRetained=ASSETS, errors=[], mapSaved=False,
                   scope='Destroys the illustrative MountAccessV2 placement only. Assets are retained on disk.')

    def write():
        RECEIPTS.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

    write()
    try:
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        others = other_engines(os.getpid())
        if others:
            raise RuntimeError('Another engine process is running: %r' % others)
        receipt['mapSha256Before'] = sha(mapfile)
        protected = {str(disk(m, 'umap')): sha(disk(m, 'umap')) for k, m in MAPS.items() if k != target}
        for asset in ASSETS:
            if disk(asset).is_file():
                protected[str(disk(asset))] = sha(disk(asset))
        receipt['protectedBefore'] = protected
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        if not levels.load_level(MAPS[target]):
            raise RuntimeError('load_level failed')
        before = read_access(ue)
        receipt['accessBefore'] = public(before)
        receipt['actorCountBefore'] = len(actors.get_all_level_actors())
        if mode == 'verify':
            reference = json.loads(Path(earlier).read_text(encoding='utf-8-sig'))
            if reference.get('status') != 'applied_saved_reopened' or reference.get('target') != target:
                raise RuntimeError('Verify needs a successful apply receipt for this target')
            receipt['mapChangedSinceApply'] = receipt['mapSha256Before'] != reference['mapSha256After']
            if before:
                raise RuntimeError('MountAccess actors are still placed: %r' % public(before))
            receipt['expectedDestroyed'] = [r['label'] for r in reference['accessBefore']]
            receipt['status'] = 'verified_fresh_process'
            return
        if not before:
            raise RuntimeError('No %s* actor found; nothing to remove' % LABEL_PREFIX)
        checkpoint = CHECKPOINTS / ('MountAccessRemove-%s-%s' % (target, stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(mapfile, checkpoint / mapfile.name)
        receipt['checkpoint'] = str(checkpoint / mapfile.name)
        receipt['checkpointSha256'] = sha(checkpoint / mapfile.name)
        write()
        destroyed = []
        for row in before:
            if not actors.destroy_actor(row['actor']):
                raise RuntimeError('destroy_actor returned False for ' + row['label'])
            destroyed.append(row['label'])
        receipt['destroyed'] = destroyed
        if not levels.save_current_level():
            raise RuntimeError('save_current_level failed')
        receipt['mapSaved'] = True
        if not levels.load_level(MAPS[target]):
            raise RuntimeError('reopen failed')
        after = read_access(ue)
        receipt['accessAfter'] = public(after)
        receipt['actorCountAfter'] = len(actors.get_all_level_actors())
        if after:
            raise RuntimeError('Reopened map still carries %d access actor(s)' % len(after))
        if receipt['actorCountBefore'] - receipt['actorCountAfter'] != len(destroyed):
            raise RuntimeError('Actor count fell by %d, expected %d'
                               % (receipt['actorCountBefore'] - receipt['actorCountAfter'], len(destroyed)))
        receipt['mapSha256After'] = sha(mapfile)
        bad = [p for p, h in protected.items() if sha(p) != h]
        receipt['protectedChanged'] = bad
        if bad:
            raise RuntimeError('Protected files changed: %r' % bad)
        receipt['status'] = 'applied_saved_reopened'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['errors'].append(repr(error))
        ue.log_error('MOUNT_ACCESS_REMOVE failed: %r' % error)
    finally:
        receipt['finishedUtc'] = datetime.now(timezone.utc).isoformat()
        write()
        ue.log('MOUNT_ACCESS_REMOVE %s %s' % (receipt['status'], path))


def revert(receipt_path, dry_run=False):
    receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
    source = Path(receipt['checkpoint'])
    target = disk(receipt['map'], 'umap')
    if sha(source) != receipt['checkpointSha256'] or sha(source) != receipt['mapSha256Before']:
        raise SystemExit('Checkpoint copy does not match the recorded before-hash')
    print(('would copy ' if dry_run else 'copy ') + str(source) + ' -> ' + str(target))
    if not dry_run:
        shutil.copy2(source, target)
        print('reverted, byte-exact' if sha(target) == receipt['mapSha256Before'] else 'REVERT MISMATCH')


if __name__ == '__main__':
    offline = [a for a in sys.argv[1:] if a.startswith('--revert=')]
    if offline:
        revert(offline[0].split('=', 1)[1], dry_run='--dry-run' in sys.argv)
    else:
        import unreal as _ue
        line = _ue.SystemLibrary.get_command_line()
        target = 'Candidate48' if re.search(r'-candidate48\b', line, re.I) else ('Main50' if re.search(r'-main50\b', line, re.I) else None)
        verify = re.search(r'-MountAccessRemoveVerify=(\S+)', line, re.I)
        apply_ = re.search(r'-MountAccessRemoveApply\b', line, re.I)
        if target is None or bool(verify) == bool(apply_):
            _ue.log_error('MOUNT_ACCESS_REMOVE: choose -Candidate48|-Main50 and exactly one of '
                          '-MountAccessRemoveApply / -MountAccessRemoveVerify=<receipt>')
        else:
            run(target, 'verify' if verify else 'apply', verify.group(1).strip('"') if verify else None)

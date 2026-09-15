"""Swap the placed Kotel-plaza terrain twin from the V1 cut to the V2 cut. 11 September 2026.

WHY
---
Version 1 of the Kotel plaza plan (Scripts/create_kotel_plaza.py) laid the upper paving over
nine of the ten treads of the flight between its two levels. The plan is fixed in the generator
(version 2): the flight's footprint is now paved at the LOWER level under the treads. The
terrain twin under the plaza was cut to the plan's deck undersides, so under the flight it still
stands at the UPPER underside, 175 cm above the first tread. Scripts/release_precinct_terrain_cut.py
-CutAssets builds the V2 twin (/Game/MikdashV3/KotelPlazaCutV2/...) from the version-2 plan; this
script points the ONE placed twin actor (label RELEASE_KotelPlazaCut_07_08) at it. Nothing else
about the actor changes: label, tags, hidden/collision flags, transform and material stay.

GUARD PATTERN
-------------
checkpoint (the .umap copied to ReviewCheckpoints), protected hashes (every other map plus the
V1 and V2 twin assets), load, swap, save, reopen, numeric readback (mesh path, flags, tags,
transform), receipt, and an offline byte-exact revert from the checkpoint.

MODES (one per run; commandlet, -nullrhi, never while another engine runs)
  -Candidate48 | -Main50        target map (Candidate48 FIRST)
  -TwinSwapApply                swap V1 -> V2
  -TwinSwapVerify=<receipt>     reopen and read back; saves nothing
Offline, no engine:
  python Scripts/release_kotel_twin_v2.py --revert=<apply receipt>   (byte-exact .umap restore)
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
RECEIPTS = ROOT / 'SourceAssets' / 'context-review' / 'KotelPlazaV1'
MAPS = {
    'Candidate48': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'Main50': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}
V1 = '/Game/MikdashV3/KotelPlazaCutV1/SM_JerusalemTerrain_07_08_FutureMountCut_KotelPlazaCut'
V2 = '/Game/MikdashV3/KotelPlazaCutV2/SM_JerusalemTerrain_07_08_FutureMountCut_KotelPlazaCut'
LABEL_PREFIX = 'RELEASE_KotelPlazaCut_'
TWIN_TAG = 'KotelPlazaCutTwin'


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


def mesh_path(obj):
    return obj.get_path_name().split('.')[0] if obj is not None else None


def read_twins(ue):
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
    rows = []
    for actor in actors:
        if not actor.get_actor_label().startswith(LABEL_PREFIX):
            continue
        comp = actor.get_component_by_class(ue.StaticMeshComponent)
        if comp is None or isinstance(comp, ue.InstancedStaticMeshComponent):
            continue
        t = actor.get_actor_transform()
        loc, rot, scl = t.translation, t.rotation.rotator(), t.scale3d
        rows.append(dict(actor=actor, component=comp, label=actor.get_actor_label(),
                         mesh=mesh_path(comp.get_editor_property('static_mesh')),
                         tags=[str(x) for x in actor.get_editor_property('tags')],
                         hidden=bool(actor.is_hidden_ed() if False else actor.get_editor_property('hidden')),
                         collision=bool(actor.get_actor_enable_collision()),
                         profile=str(comp.get_collision_profile_name()),
                         material=mesh_path(comp.get_material(0)),
                         transform=[round(v, 4) for v in (loc.x, loc.y, loc.z, rot.pitch, rot.yaw, rot.roll,
                                                           scl.x, scl.y, scl.z)]))
    return rows


def public(rows):
    return [{k: v for k, v in r.items() if k not in ('actor', 'component')} for r in rows]


def run(target, mode, earlier=None):
    import unreal as ue
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = RECEIPTS / ('kotel-twin-v2-%s-%s-%s.json' % (mode, target, stamp))
    mapfile = disk(MAPS[target], 'umap')
    receipt = dict(status='started', mode=mode, target=target, map=MAPS[target], stamp=stamp,
                   pid=os.getpid(), v1=V1, v2=V2, errors=[], mapSaved=False)

    def write():
        path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

    write()
    try:
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        others = other_engines(os.getpid())
        if others:
            raise RuntimeError('Another engine process is running: %r' % others)
        for asset in (V1, V2):
            if not disk(asset).is_file():
                raise RuntimeError('Missing twin asset on disk: ' + asset)
        receipt['mapSha256Before'] = sha(mapfile)
        protected = {str(disk(m, 'umap')): sha(disk(m, 'umap')) for k, m in MAPS.items() if k != target}
        for asset in (V1, V2):
            protected[str(disk(asset))] = sha(disk(asset))
        receipt['protectedBefore'] = protected
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.load_level(MAPS[target]):
            raise RuntimeError('load_level failed')
        before = read_twins(ue)
        receipt['twinsBefore'] = public(before)
        if len(before) != 1:
            raise RuntimeError('Expected exactly one %s* terrain-twin actor, found %d' % (LABEL_PREFIX, len(before)))
        row = before[0]
        if TWIN_TAG not in row['tags']:
            raise RuntimeError('The twin actor lacks its %s tag' % TWIN_TAG)
        if mode == 'verify':
            ref = json.loads(Path(earlier).read_text(encoding='utf-8-sig'))
            if ref.get('status') != 'applied_saved_reopened' or ref.get('target') != target:
                raise RuntimeError('Verify needs a successful apply receipt for this target')
            # The map itself legitimately moves after the swap: release_kotel_plaza.py
            # -PlazaRebuild saves the same map straight afterwards. So the verify compares the
            # TWIN ACTOR against what the apply read back, field by field, and only records
            # whether the map bytes moved.
            receipt['mapChangedSinceApply'] = receipt['mapSha256Before'] != ref['mapSha256After']
            expected = (ref.get('twinsAfter') or [None])[0]
            if expected is None:
                raise RuntimeError('The apply receipt carries no twinsAfter readback')
            if row['mesh'] != V2:
                raise RuntimeError('The twin points at %s, not V2' % row['mesh'])
            for key in ('mesh', 'label', 'tags', 'hidden', 'collision', 'profile', 'material', 'transform'):
                if row[key] != expected[key]:
                    raise RuntimeError('Twin %s differs from the apply readback: %r vs %r'
                                       % (key, row[key], expected[key]))
            receipt['status'] = 'verified_fresh_process'
            return
        if row['mesh'] != V1:
            raise RuntimeError('The twin points at %s, expected V1 %s' % (row['mesh'], V1))
        checkpoint = CHECKPOINTS / ('KotelTwinV2-%s-%s' % (target, stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(mapfile, checkpoint / mapfile.name)
        receipt['checkpoint'] = str(checkpoint / mapfile.name)
        receipt['checkpointSha256'] = sha(checkpoint / mapfile.name)
        write()
        v2 = ue.load_asset(V2)
        if not isinstance(v2, ue.StaticMesh):
            raise RuntimeError('V2 did not load as a StaticMesh')
        actor, comp = row['actor'], row['component']
        actor.modify()
        comp.modify()
        if not comp.set_static_mesh(v2):
            raise RuntimeError('set_static_mesh(V2) failed')
        comp.set_material(0, ue.load_asset(row['material']))
        if not levels.save_current_level():
            raise RuntimeError('save_current_level failed')
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha(mapfile)
        if not levels.load_level(MAPS[target]):
            raise RuntimeError('reopen failed')
        after = read_twins(ue)
        receipt['twinsAfter'] = public(after)
        if len(after) != 1 or after[0]['mesh'] != V2:
            raise RuntimeError('Reopened twin does not point at V2: %r' % public(after))
        for key in ('label', 'tags', 'hidden', 'collision', 'profile', 'material', 'transform'):
            if after[0][key] != row[key]:
                raise RuntimeError('Twin %s changed: %r -> %r' % (key, row[key], after[0][key]))
        receipt['mapSha256After'] = sha(mapfile)
        bad = [p for p, h in protected.items() if sha(p) != h]
        receipt['protectedChanged'] = bad
        if bad:
            raise RuntimeError('Protected files changed: %r' % bad)
        receipt['status'] = 'applied_saved_reopened'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['errors'].append(repr(error))
        ue.log_error('KOTEL_TWIN_V2 failed: %r' % error)
    finally:
        receipt['finishedUtc'] = datetime.now(timezone.utc).isoformat()
        write()
        ue.log('KOTEL_TWIN_V2 %s %s' % (receipt['status'], path))


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
        # Optional -TwinFrom=<mesh path> / -TwinTo=<mesh path> (defaults V1 -> V2). Used for the
        # V2 -> V3 re-cut of the same day, which only snaps the cut regions' edges.
        swap_from = re.search(r'-TwinFrom=(\S+)', line, re.I)
        swap_to = re.search(r'-TwinTo=(\S+)', line, re.I)
        if swap_from:
            V1 = swap_from.group(1).strip('"')
        if swap_to:
            V2 = swap_to.group(1).strip('"')
        verify = re.search(r'-TwinSwapVerify=(\S+)', line, re.I)
        apply_ = re.search(r'-TwinSwapApply\b', line, re.I)
        if target is None or bool(verify) == bool(apply_):
            _ue.log_error('KOTEL_TWIN_V2: choose -Candidate48|-Main50 and exactly one of -TwinSwapApply / -TwinSwapVerify=<receipt>')
        else:
            run(target, 'verify' if verify else 'apply', verify.group(1).strip('"') if verify else None)

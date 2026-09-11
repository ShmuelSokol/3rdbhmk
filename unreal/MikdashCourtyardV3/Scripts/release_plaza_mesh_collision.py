"""Box simple collision on five PrecinctPlazaV1 modules, so the Kotel plaza and the outside
approaches can actually be walked on. 11 September 2026.

WHY
---
All seven PrecinctPlazaV1 meshes were imported with `auto_generate_collision False`
(release_precinct_plaza.spec.json importSettings.staticMeshImportData). A static mesh with no
simple shape gives a CharacterMovement capsule NOTHING to sweep against, whatever the
component's collision profile says. So:

  * RELEASE_KotelPlaza's four HISMs are BlockAll (release_kotel_plaza.py:629) and switched on
    in MODERN by ApplyStateTaggedActors - and a visitor still falls straight through them;
  * the PrecinctApproachV1 actor's four HISMs take their default profile - and the same.

Every one of those modules IS a box (create_precinct_plaza.py: deck_tile, way_tile, kerb,
retaining_band and step_module are each one `box(...)`), so one box simple-collision element
computed from the mesh's own bounds is its exact collision. Collision is not drawn: nothing
here changes how anything looks, and no material is touched.

NOT given collision: SM_PlazaV1_Rib and SM_PlazaV1_Channel (decorative, a few cm proud; the
crowd's capsule sweeps cross them on the east way). The enclosure's OWN plaza components are
unaffected by this pass either way - AMikdashEnclosure builds its deck proxy boxes and turns
its step/retaining/scarp instance bodies on in C++ (EnclosureMath.h section 6c), game worlds only.

MODES (one per run, hidden editor on /Engine/Maps/Entry - no map is loaded or saved)
  -PlazaMeshCollision=apply
  -PlazaMeshCollision=verify:<absolute apply receipt>     fresh process; saves nothing
Offline, no engine:
  python Scripts/release_plaza_mesh_collision.py --revert=<apply receipt>
      byte-exact restore of the five .uasset files from the run's ReviewCheckpoints copy.

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject" /Engine/Maps/Entry
      -ExecutePythonScript="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_plaza_mesh_collision.py"
      -PlazaMeshCollision=apply -unattended -nosplash -nullrhi -abslog=...
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
CHECKPOINTS = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
RECEIPTS = ROOT / 'SourceAssets' / 'enclosure-review'
FOLDER = '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Meshes/'
MESHES = ['SM_PlazaV1_DeckTile', 'SM_PlazaV1_WayTile', 'SM_PlazaV1_Step',
          'SM_PlazaV1_Kerb', 'SM_PlazaV1_RetainingBand']
EXCLUDED = ['SM_PlazaV1_Rib', 'SM_PlazaV1_Channel']
MAPS = [ROOT / 'Content/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough.umap',
        ROOT / 'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap']


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk(name):
    return ROOT / 'Content' / (FOLDER[6:] + name + '.uasset')


def protected_set():
    """Every Content file except the five this pass is allowed to write. Includes both maps."""
    mine = {str(disk(n)) for n in MESHES}
    return {str(p): sha(p) for p in (ROOT / 'Content').rglob('*')
            if p.is_file() and str(p) not in mine}


def changed(expected):
    return [p for p, h in expected.items() if not Path(p).is_file() or sha(p) != h]


def other_engines(ue_pid):
    import csv
    import io
    import subprocess
    rows = list(csv.reader(io.StringIO(subprocess.run(
        ['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, check=True, timeout=30).stdout)))
    names = ('unrealeditor.exe', 'unrealeditor-cmd.exe', 'mikdashcourtyardv3.exe')
    return [r[:2] for r in rows if len(r) > 1 and r[0].lower() in names and int(r[1]) != ue_pid]


def box_elements(ue, mesh):
    """The box elements, read off the saved BodySetup (None when 5.8 Python will not expose them)."""
    try:
        body = mesh.get_editor_property('body_setup')
        geom = body.get_editor_property('agg_geom')
        boxes = geom.get_editor_property('box_elems')
        out = []
        for b in boxes:
            c = b.get_editor_property('center')
            out.append(dict(center=[round(c.x, 4), round(c.y, 4), round(c.z, 4)],
                            size=[round(float(b.get_editor_property('x')), 4),
                                  round(float(b.get_editor_property('y')), 4),
                                  round(float(b.get_editor_property('z')), 4)]))
        return out
    except Exception as error:  # reported, not fatal: the count and the bounds still gate
        return {'unreadable': repr(error)}


def measure(ue, subsystem, name):
    mesh = ue.load_asset(FOLDER + name)
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError('Missing mesh ' + name)
    bounds = mesh.get_bounding_box()
    lo, hi = bounds.min, bounds.max
    row = dict(mesh=FOLDER + name,
               boundsMin=[round(lo.x, 4), round(lo.y, 4), round(lo.z, 4)],
               boundsMax=[round(hi.x, 4), round(hi.y, 4), round(hi.z, 4)],
               simpleCollisionCount=int(subsystem.get_simple_collision_count(mesh)),
               collisionComplexity=str(subsystem.get_collision_complexity(mesh)),
               boxes=box_elements(ue, mesh),
               nanite=bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled')))
    return mesh, row


def box_matches_bounds(row):
    """The one box must BE the mesh's bounding box (within 0.05 cm)."""
    boxes = row['boxes']
    if not isinstance(boxes, list):
        return None
    if len(boxes) != 1:
        return False
    box = boxes[0]
    for axis in range(3):
        centre = 0.5 * (row['boundsMin'][axis] + row['boundsMax'][axis])
        size = row['boundsMax'][axis] - row['boundsMin'][axis]
        if abs(box['center'][axis] - centre) > 0.05 or abs(box['size'][axis] - size) > 0.05:
            return False
    return True


def run(mode, receipt_in=None):
    import unreal as ue
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    path = RECEIPTS / ('plaza-mesh-collision-%s-%s.json' % (mode, stamp))
    receipt = dict(status='started', mode=mode, stamp=stamp, pid=os.getpid(), meshes=MESHES,
                   excluded=EXCLUDED, errors=[], saved=False,
                   scope='Box simple collision on five PrecinctPlazaV1 modules. No map is loaded or '
                         'saved. Visual appearance unchanged by construction (collision is not drawn). '
                         'Walking acceptance is the packaged-build walk probe, not this receipt.')

    def write():
        path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

    write()
    try:
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        others = other_engines(os.getpid())
        if others:
            raise RuntimeError('Another engine process is running: %r' % others)
        subsystem = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)
        if subsystem is None:
            raise RuntimeError('StaticMeshEditorSubsystem unavailable - use the hidden-editor recipe')
        receipt['meshSha256Before'] = {n: sha(disk(n)) for n in MESHES}
        receipt['mapSha256Before'] = {str(m): sha(m) for m in MAPS}
        protected = protected_set()
        receipt['protectedFileCount'] = len(protected)
        write()

        if mode == 'verify':
            earlier = json.loads(Path(receipt_in).read_text(encoding='utf-8-sig'))
            if earlier.get('status') != 'applied_saved_readback' or earlier.get('pid') == os.getpid():
                raise RuntimeError('Verify needs a successful apply receipt from ANOTHER process')
            receipt['applyReceipt'] = str(receipt_in)
            moved = [n for n in MESHES if receipt['meshSha256Before'][n] != earlier['meshSha256After'][n]]
            if moved:
                raise RuntimeError('Mesh bytes differ from the apply receipt: %r' % moved)
            rows = {}
            for name in MESHES:
                _, row = measure(ue, subsystem, name)
                rows[name] = row
                if row['simpleCollisionCount'] != 1:
                    raise RuntimeError('%s: %d simple shapes after reopen, want 1' % (name, row['simpleCollisionCount']))
                if box_matches_bounds(row) is False:
                    raise RuntimeError('%s: box does not match the mesh bounds: %r' % (name, row['boxes']))
            receipt['readback'] = rows
            for name in EXCLUDED:
                _, row = measure(ue, subsystem, name)
                receipt.setdefault('excludedReadback', {})[name] = row
                if row['simpleCollisionCount'] != 0:
                    raise RuntimeError('%s should carry no collision' % name)
            if changed(protected) or {n: sha(disk(n)) for n in MESHES} != receipt['meshSha256Before']:
                raise RuntimeError('verify must not change any file, and it did')
            receipt['status'] = 'verified_fresh_process'
            return

        # ---- apply
        checkpoint = CHECKPOINTS / ('PlazaMeshCollision-' + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        for name in MESHES:
            shutil.copy2(disk(name), checkpoint / (name + '.uasset'))
        receipt['checkpoint'] = str(checkpoint)
        before = {}
        for name in MESHES:
            _, row = measure(ue, subsystem, name)
            before[name] = row
            if row['simpleCollisionCount'] != 0:
                raise RuntimeError('%s already has %d simple shapes; refusing to add more'
                                   % (name, row['simpleCollisionCount']))
        receipt['before'] = before
        write()
        after = {}
        for name in MESHES:
            mesh = ue.load_asset(FOLDER + name)
            index = subsystem.add_simple_collisions(mesh, ue.ScriptCollisionShapeType.BOX)
            if index is None or int(index) < 0:
                raise RuntimeError('%s: add_simple_collisions returned %r' % (name, index))
            if not ue.EditorAssetLibrary.save_loaded_asset(mesh, False):
                raise RuntimeError('%s: save failed' % name)
            receipt['saved'] = True
        # Numeric readback from the reloaded assets in this process.
        for name in MESHES:
            _, row = measure(ue, subsystem, name)
            after[name] = row
            if row['simpleCollisionCount'] != 1:
                raise RuntimeError('%s: %d simple shapes after save, want 1' % (name, row['simpleCollisionCount']))
            if box_matches_bounds(row) is False:
                raise RuntimeError('%s: box does not match the mesh bounds: %r' % (name, row['boxes']))
            if row['boundsMin'] != before[name]['boundsMin'] or row['boundsMax'] != before[name]['boundsMax']:
                raise RuntimeError('%s: render bounds moved - the look may have changed' % name)
        receipt['after'] = after
        receipt['meshSha256After'] = {n: sha(disk(n)) for n in MESHES}
        receipt['boxMatchesBounds'] = {n: box_matches_bounds(after[n]) for n in MESHES}
        bad = changed(protected)
        receipt['protectedChanged'] = bad[:20]
        if bad:
            raise RuntimeError('%d protected files changed, e.g. %s' % (len(bad), bad[:3]))
        receipt['mapSha256After'] = {str(m): sha(m) for m in MAPS}
        if receipt['mapSha256After'] != receipt['mapSha256Before']:
            raise RuntimeError('A map changed - this pass must not touch either map')
        receipt['status'] = 'applied_saved_readback'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['errors'].append(repr(error))
        ue.log_error('PLAZA_MESH_COLLISION failed: %r' % error)
    finally:
        receipt['finishedUtc'] = datetime.now(timezone.utc).isoformat()
        write()
        ue.log('PLAZA_MESH_COLLISION %s %s' % (receipt['status'], path))


def revert(receipt_path, dry_run=False):
    receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
    checkpoint = Path(receipt['checkpoint'])
    plan = []
    for name in MESHES:
        source = checkpoint / (name + '.uasset')
        if sha(source) != receipt['meshSha256Before'][name]:
            raise SystemExit('checkpoint copy of %s does not match the recorded before-hash' % name)
        plan.append((source, disk(name)))
    for source, target in plan:
        print(('would copy ' if dry_run else 'copy ') + str(source) + ' -> ' + str(target))
        if not dry_run:
            shutil.copy2(source, target)
    if not dry_run:
        bad = [n for n in MESHES if sha(disk(n)) != receipt['meshSha256Before'][n]]
        print('reverted, byte-exact' if not bad else 'REVERT MISMATCH: %r' % bad)


def _mode_from_command_line():
    try:
        import unreal as ue
        line = ue.SystemLibrary.get_command_line()
    except Exception:
        return None, None
    for token in line.split():
        if token.lower().startswith('-plazameshcollision='):
            value = token.split('=', 1)[1].strip('"')
            if value.lower() == 'apply':
                return 'apply', None
            if value.lower().startswith('verify:'):
                return 'verify', value.split(':', 1)[1]
    return None, None


if __name__ == '__main__':
    offline = [a for a in sys.argv[1:] if a.startswith('--revert=')]
    if offline:
        revert(offline[0].split('=', 1)[1], dry_run='--dry-run' in sys.argv)
    else:
        mode, argument = _mode_from_command_line()
        if mode is None:
            print('No -PlazaMeshCollision=apply|verify:<receipt> on the command line; nothing done.')
        else:
            run(mode, argument)

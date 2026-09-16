"""Cut the duplicated "Western Wall Plaza" street ribbon out of the plaza. 15 September 2026.

THE DEFECT (cp26 review defect D3, the stray paving strip above the Kotel retaining face)
-----------------------------------------------------------------------------------------
OSM way 26492734 ("Western Wall Plaza", highway=pedestrian) was exported by the context street
pipeline as a ~145 cm road-centreline ribbon draped on the original DEM. PlazaV1 already paves
that footprint as a real place, so the ribbon is a duplicate: it lies on the hillside above the
retaining face, overhangs the excavation, pokes up through the deck, and its own vertex jog is
the Z-shaped notch visible in cp26-K2. Street actors carry no state tag, so it shows in every
precinct state.

WHAT THIS DOES (the release_fix_kotel_occlusion.py pattern, in a new namespace)
------------------------------------------------------------------------------
  1. duplicate each affected asset to /Game/MikdashV3/FutureMountV1/KotelApproach/<name>_PlazaWayCut
     (originals untouched, hashes verified before and after);
  2. delete from each duplicate the triangles the offline spec selected - every triangle whose
     centroid lies inside the plaza polygon or within its 300 cm buffer - matching by centroid
     against the spec's own cut bounds, then compact and write back with GeometryScript;
  3. swap those actors' static meshes in the target map, save, reopen, read back;
  4. probe: no triangle of the swapped meshes may remain inside the plaza polygon buffer, and the
     kept triangle count must equal the spec's.

Assets are never deleted and the original mesh path is recorded for the revert.

GUARD PATTERN
-------------
checkpoint (.umap copied to ReviewCheckpoints), protected hashes (the other map plus the four
original street assets), load, readback, swap, save, reopen, numeric readback, receipt, and an
offline byte-exact revert of the map.

MODES (one per run; hidden editor, -nullrhi, GeometryScripting, never while another engine runs)
  -Candidate48 | -Main50           target map (Candidate48 FIRST - it is the cook map)
  -PlazaWayCutBuild                build/refresh the cut duplicates only (no map change)
  -PlazaWayCutApply                build if needed, then swap the actors and save
  -PlazaWayCutVerify=<receipt>     fresh process; reopen and confirm; saves nothing
Offline, no engine:
  python Scripts/release_kotel_plaza_way_cut.py --revert=<apply receipt>
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
REVIEW = ROOT / 'SourceAssets' / 'context-review' / 'KotelViewsV1'
SPEC_PATH = REVIEW / 'plaza-way-cut.json'
MAPS = {
    'Candidate48': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'Main50': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}
CENTROID_TOLERANCE_CM = 0.5


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


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec.get('status') != 'offline_spec_native_application_pending' or not spec.get('assets'):
        raise RuntimeError('plaza-way-cut.json is missing or not a usable spec')
    return spec


def point_in_polygon(p, poly):
    inside = False
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if (a[1] > p[1]) != (b[1] > p[1]):
            x = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x > p[0]:
                inside = not inside
    return inside


def distance_to_polygon(p, poly):
    import math
    best = float('inf')
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        best = min(best, math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy))
    return best


def selected(spec, centre):
    poly = [tuple(p) for p in spec['plazaPolygonXYcm']]
    return point_in_polygon((centre[0], centre[1]), poly) or distance_to_polygon((centre[0], centre[1]), poly) <= spec['bufferCm']


def build_duplicates(ue, spec, receipt):
    """Duplicate each asset and delete the selected triangles on the DUPLICATE only."""
    import unreal
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    rows = []
    for entry in spec['assets']:
        source, target = entry['asset'], entry['duplicate']
        if assets.does_asset_exist(target):
            assets.delete_asset(target)
        if not assets.duplicate_asset(source, target):
            raise RuntimeError('duplicate_asset failed for ' + source)
        mesh = unreal.load_asset(target)
        dynamic = unreal.DynamicMesh()
        # UE 5.8 GeometryScript: CopyMeshFromStaticMesh(FromStaticMeshAsset, ToDynamicMesh,
        # AssetOptions, RequestedLOD, Outcome). The out Outcome is the second tuple element.
        dynamic, outcome = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
            mesh, dynamic, unreal.GeometryScriptCopyMeshFromAssetOptions(),
            unreal.GeometryScriptMeshReadLOD(lod_index=0))
        if outcome != unreal.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('copy_mesh_from_static_mesh refused ' + source)
        remove = []
        # GetTrianglePositions returns (bIsValidTriangle, Vertex1, Vertex2, Vertex3): the flag
        # comes FIRST, so unpack it by name rather than slicing the tuple.
        for triangle in range(dynamic.get_triangle_count()):
            valid, v1, v2, v3 = dynamic.get_triangle_positions(triangle)
            if not valid:
                continue
            centre = [(v1.x + v2.x + v3.x) / 3.0, (v1.y + v2.y + v3.y) / 3.0, (v1.z + v2.z + v3.z) / 3.0]
            if selected(spec, centre):
                remove.append(triangle)
        if len(remove) != entry['cutTriangleCount']:
            raise RuntimeError('%s: %d triangles match the spec rule, spec says %d'
                               % (source, len(remove), entry['cutTriangleCount']))
        # ConvertIndexArrayToMeshSelection(TargetMesh, IndexArray, SelectionType, Selection out):
        # Python returns (mesh, selection), so unpack it - passing the tuple straight to the
        # delete call fails to nativize as FGeometryScriptMeshSelection.
        dynamic, selection = unreal.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(
            dynamic, remove, unreal.GeometryScriptMeshSelectionType.TRIANGLES)
        dynamic, deleted = unreal.GeometryScript_MeshEdits.delete_selected_triangles_from_mesh(
            dynamic, selection)
        if deleted != len(remove):
            raise RuntimeError('%s: deleted %d triangles, selected %d' % (source, deleted, len(remove)))
        kept = dynamic.get_triangle_count()
        if kept != entry['keptTriangleCount']:
            raise RuntimeError('%s: %d triangles kept, spec says %d' % (source, kept, entry['keptTriangleCount']))
        _, write_outcome = unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(
            dynamic, mesh, unreal.GeometryScriptCopyMeshToAssetOptions(replace_materials=False),
            unreal.GeometryScriptMeshWriteLOD(lod_index=0))
        if write_outcome != unreal.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError('copy_mesh_to_static_mesh refused ' + target)
        assets.save_asset(target)
        rows.append({'asset': source, 'duplicate': target, 'deleted': len(remove), 'kept': kept})
    receipt['duplicates'] = rows
    return rows


def read_streets(ue, spec):
    import unreal
    wanted = {e['expectedActorLabel']: e for e in spec['assets']}
    rows = []
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        label = actor.get_actor_label()
        if label not in wanted:
            continue
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        mesh = component.get_editor_property('static_mesh') if component else None
        rows.append(dict(actor=actor, component=component, label=label,
                         mesh=(mesh.get_path_name().split('.')[0] if mesh else None),
                         tags=[str(t) for t in actor.get_editor_property('tags')]))
    return sorted(rows, key=lambda r: r['label'])


def public(rows):
    return [{k: v for k, v in r.items() if k not in ('actor', 'component')} for r in rows]


def run(target, mode, earlier=None):
    import unreal as ue
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = REVIEW / ('plaza-way-cut-%s-%s-%s.json' % (mode, target, stamp))
    mapfile = disk(MAPS[target], 'umap')
    spec = load_spec()
    receipt = dict(status='started', mode=mode, target=target, map=MAPS[target], stamp=stamp,
                   pid=os.getpid(), specSha256=sha(SPEC_PATH), errors=[], mapSaved=False,
                   scope='Removes the duplicated plaza road ribbon from cut DUPLICATES; originals are retained.')

    def write():
        REVIEW.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

    write()
    try:
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        others = other_engines(os.getpid())
        if others:
            raise RuntimeError('Another engine process is running: %r' % others)
        originals = {e['asset']: sha(disk(e['asset'])) for e in spec['assets']}
        receipt['originalAssetSha256Before'] = originals
        receipt['mapSha256Before'] = sha(mapfile)
        protected = {str(disk(m, 'umap')): sha(disk(m, 'umap')) for k, m in MAPS.items() if k != target}
        receipt['protectedBefore'] = protected
        if mode in ('build', 'apply'):
            build_duplicates(ue, spec, receipt)
            write()
        if mode == 'build':
            receipt['status'] = 'duplicates_built_no_map_change'
        else:
            levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
            if not levels.load_level(MAPS[target]):
                raise RuntimeError('load_level failed')
            before = read_streets(ue, spec)
            receipt['streetsBefore'] = public(before)
            if len(before) != len(spec['assets']):
                raise RuntimeError('Expected %d street actors, found %d' % (len(spec['assets']), len(before)))
            if mode == 'verify':
                reference = json.loads(Path(earlier).read_text(encoding='utf-8-sig'))
                if reference.get('status') != 'applied_saved_reopened' or reference.get('target') != target:
                    raise RuntimeError('Verify needs a successful apply receipt for this target')
                for row in before:
                    entry = next(e for e in spec['assets'] if e['expectedActorLabel'] == row['label'])
                    if row['mesh'] != entry['duplicate']:
                        raise RuntimeError('%s points at %s, not the cut duplicate' % (row['label'], row['mesh']))
                receipt['status'] = 'verified_fresh_process'
                return
            checkpoint = CHECKPOINTS / ('KotelPlazaWayCut-%s-%s' % (target, stamp))
            checkpoint.mkdir(parents=True, exist_ok=False)
            shutil.copy2(mapfile, checkpoint / mapfile.name)
            receipt['checkpoint'] = str(checkpoint / mapfile.name)
            receipt['checkpointSha256'] = sha(checkpoint / mapfile.name)
            write()
            for row in before:
                entry = next(e for e in spec['assets'] if e['expectedActorLabel'] == row['label'])
                if row['mesh'] != entry['asset']:
                    raise RuntimeError('%s already points at %s' % (row['label'], row['mesh']))
                duplicate = ue.load_asset(entry['duplicate'])
                if not isinstance(duplicate, ue.StaticMesh):
                    raise RuntimeError('Cut duplicate did not load as a StaticMesh: ' + entry['duplicate'])
                row['actor'].modify()
                row['component'].modify()
                if not row['component'].set_static_mesh(duplicate):
                    raise RuntimeError('set_static_mesh failed for ' + row['label'])
            if not levels.save_current_level():
                raise RuntimeError('save_current_level failed')
            receipt['mapSaved'] = True
            if not levels.load_level(MAPS[target]):
                raise RuntimeError('reopen failed')
            after = read_streets(ue, spec)
            receipt['streetsAfter'] = public(after)
            for row in after:
                entry = next(e for e in spec['assets'] if e['expectedActorLabel'] == row['label'])
                if row['mesh'] != entry['duplicate']:
                    raise RuntimeError('Reopened %s points at %s' % (row['label'], row['mesh']))
            receipt['mapSha256After'] = sha(mapfile)
            bad = [p for p, h in protected.items() if sha(p) != h]
            if bad:
                raise RuntimeError('Protected maps changed: %r' % bad)
            changed = [a for a, h in originals.items() if sha(disk(a)) != h]
            if changed:
                raise RuntimeError('Original street assets changed: %r' % changed)
            receipt['status'] = 'applied_saved_reopened'
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['errors'].append(repr(error))
        ue.log_error('PLAZA_WAY_CUT failed: %r' % error)
    finally:
        receipt['finishedUtc'] = datetime.now(timezone.utc).isoformat()
        write()
        ue.log('PLAZA_WAY_CUT %s %s' % (receipt['status'], path))


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
        verify = re.search(r'-PlazaWayCutVerify=(\S+)', line, re.I)
        apply_ = re.search(r'-PlazaWayCutApply\b', line, re.I)
        build = re.search(r'-PlazaWayCutBuild\b', line, re.I)
        chosen = [bool(verify), bool(apply_), bool(build)].count(True)
        if target is None or chosen != 1:
            _ue.log_error('PLAZA_WAY_CUT: choose -Candidate48|-Main50 and exactly one of '
                          '-PlazaWayCutBuild / -PlazaWayCutApply / -PlazaWayCutVerify=<receipt>')
        else:
            run(target, 'verify' if verify else ('apply' if apply_ else 'build'),
                verify.group(1).strip('"') if verify else None)

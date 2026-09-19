"""Import fresh outlet assets, or verify persisted assets, without loading a map."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import shutil
import sys
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
from audit_crowd_street_ground import extract, sha
from build_court_outlet_v2 import frozen_triangles, BASE, PINNED
from release_water import _static_mesh_box, box_error

FOLDER = ROOT / 'SourceAssets/water-review/CourtOutletV2'
DEST = '/Game/MikdashV3/MaterialReview/CourtOutletV2'
OLD = '/Game/MikdashV3/MaterialReview/MikdashWaterV1/Meshes/SM_MikdashWaterV1_'
APPLY = '-CourtOutletImport' in ue.SystemLibrary.get_command_line()
COLLISION = '-CourtOutletCollision' in ue.SystemLibrary.get_command_line()


def disk(asset):
    return ROOT / ('Content/' + asset.removeprefix('/Game/') + '.uasset')


def key(points):
    # Importer storage is float32. Preserve winding and duplicate triangles.
    points = tuple(tuple(struct.unpack('<f', struct.pack('<f', c))[0] for c in p) for p in points)
    return min(points, points[1:] + points[:1], points[2:] + points[:2])


def native_triangles(mesh, lod):
    data = extract(ue, mesh, lod)
    return Counter(key([data['vertices'][i] for i in t]) for t in data['triangles'])


def geometry(mesh, lod, expected):
    actual = native_triangles(mesh, lod)
    if actual != expected:
        missing, extra = expected - actual, actual - expected
        raise RuntimeError('Native triangles differ: %s expected=%d actual=%d missing=%d extra=%d samples=%r / %r' % (
            lod, sum(expected.values()), sum(actual.values()), sum(missing.values()), sum(extra.values()),
            list(missing)[:2], list(extra)[:2]))
    return sum(actual.values())


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = FOLDER / ('native-' + stamp + '.json')
    assert not (APPLY and COLLISION)
    report = dict(status='running', apply=APPLY, collisionApply=COLLISION,
                  scope='Two candidate assets only; no map integration or visual acceptance', assets=[])
    protected = list((ROOT / 'Content').rglob('*.umap'))
    protected += [disk(OLD + suffix) for suffix in ('CourtChannel', 'CourtWater')]
    before = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    try:
        manifest = json.loads((FOLDER / 'candidate.json').read_text())
        assert manifest['destination'] == DEST
        settings = json.loads((ROOT / 'Scripts/release_water.spec.json').read_text())['importSettings']
        destination = ROOT / ('Content/' + DEST.removeprefix('/Game/'))
        allowed = {r['candidate']['name'] + '.uasset' for r in manifest['records']}
        if destination.exists():
            assert all(p.is_file() and p.name in allowed for p in destination.iterdir()), 'Unexpected namespace contents'
        # A failed import may leave a candidate asset. Never replace it: validate
        # its complete geometry and settings, then import only missing siblings.
        existing_hashes = {str(p): sha(p) for p in destination.glob('*.uasset')}
        for row in manifest['records']:
            record = row['candidate']
            source = FOLDER / record['file']
            assert sha(source) == record['sha256'], 'Candidate OBJ changed'
            path = DEST + '/' + record['name']
            original = ue.load_asset(OLD + row['suffix'])
            assert isinstance(original, ue.StaticMesh)
            baseline_obj = BASE / ('SM_MikdashWaterV1_' + row['suffix'] + '.obj')
            assert sha(baseline_obj) == PINNED[row['suffix']]
            baseline = Counter()
            for triangle, count in frozen_triangles(baseline_obj).items():
                baseline[key((triangle[0], triangle[2], triangle[1]))] += count
            # UE's left-handed triangle order is opposite the canonical solid
            # authoring convention. Require the existing released asset to prove
            # that adapter, independently in source and render geometry.
            for lod in (ue.GeometryScriptLODType.SOURCE_MODEL, ue.GeometryScriptLODType.RENDER_DATA):
                geometry(original, lod, baseline)
            materials = [s.material_interface for s in original.get_editor_property('static_materials')]
            assert materials and all(materials), 'Original has missing material'
            body = original.get_editor_property('body_setup')
            collision = body.get_editor_property('collision_trace_flag')
            if APPLY and not disk(path).exists():
                assert not ue.EditorAssetLibrary.does_asset_exist(path), 'Unexpected unsaved asset'
                ui = ue.FbxImportUI()
                for prop, value in settings['fbxImportUI'].items():
                    ui.set_editor_property(prop, getattr(ue.FBXImportType, value) if prop == 'mesh_type_to_import' else value)
                data = ui.get_editor_property('static_mesh_import_data')
                for prop, value in settings['staticMeshImportData'].items():
                    data.set_editor_property(prop, getattr(ue.FBXNormalImportMethod, value) if prop == 'normal_import_method' else value)
                task = ue.AssetImportTask()
                for prop, value in dict(filename=str(source), destination_path=DEST,
                                        destination_name=record['name'], automated=True, async_=False,
                                        replace_existing=False, save=False, options=ui, factory=ue.FbxFactory()).items():
                    task.set_editor_property(prop, value)
                ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                objects = list(task.get_objects())
                assert len(objects) == 1 and isinstance(objects[0], ue.StaticMesh)
                mesh = objects[0]
                assert mesh.get_path_name().split('.')[0] == path
                slots = len(mesh.get_editor_property('static_materials'))
                assert len(materials) == 1 or len(materials) == slots, 'Ambiguous material mapping'
                for index in range(slots):
                    mesh.set_material(index, materials[0] if len(materials) == 1 else materials[index])
                mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag', collision)
                mesh.set_editor_property('lod_for_collision', original.get_editor_property('lod_for_collision'))
                assert ue.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
            else:
                mesh = ue.load_asset(path)
            assert isinstance(mesh, ue.StaticMesh)
            expected = Counter()
            for triangle, count in frozen_triangles(source).items():
                expected[key((triangle[0], triangle[2], triangle[1]))] += count
            source_count = geometry(mesh, ue.GeometryScriptLODType.SOURCE_MODEL, expected)
            render_count = geometry(mesh, ue.GeometryScriptLODType.RENDER_DATA, expected)
            assert source_count == render_count == record['triangles']
            assert box_error(_static_mesh_box(mesh), record['canonicalBoundsCm']) < 0.05
            slots = list(mesh.get_editor_property('static_materials'))
            assert slots and all(s.material_interface == (materials[0] if len(materials) == 1 else materials[i]) for i, s in enumerate(slots))
            assert mesh.get_editor_property('lod_for_collision') == original.get_editor_property('lod_for_collision')
            original_simple = body.get_editor_property('agg_geom').export_text()
            candidate_simple = mesh.get_editor_property('body_setup').get_editor_property('agg_geom').export_text()
            assert 'ConvexElems=,' in candidate_simple and 'BoxElems=,' in candidate_simple, 'Unexpected candidate hulls'
            candidate_body = mesh.get_editor_property('body_setup')
            if COLLISION:
                backup = ROOT / 'ReviewCheckpoints' / ('court-outlet-collision-' + stamp)
                backup.mkdir(parents=True, exist_ok=True)
                target = backup / disk(path).name
                assert not target.exists()
                shutil.copy2(disk(path), target)
                assert sha(target) == existing_hashes[str(disk(path))]
                candidate_body.set_editor_property('collision_trace_flag', ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                assert ue.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
                report.setdefault('backups', []).append(dict(path=str(target), sha256=sha(target)))
            candidate_flag = candidate_body.get_editor_property('collision_trace_flag')
            report['assets'].append(dict(asset=path, sha256=sha(disk(path)), sourceTriangles=source_count,
                                         renderTriangles=render_count, exactFloat32PositionsAndWinding=True,
                                         nativeWinding='Reversed from canonical, independently matched on frozen V1 source/render',
                                         materials=[s.material_interface.get_path_name() for s in slots],
                                         collisionTraceFlag=str(candidate_flag), originalCollisionTraceFlag=str(collision),
                                         triangleCollision=candidate_flag == ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
                                         simpleCollision=candidate_simple,
                                         originalSimpleCollision=original_simple,
                                         simpleCollisionMatchesOriginal=candidate_simple == original_simple,
                                         bounds=_static_mesh_box(mesh)))
        if not COLLISION:
            assert all(sha(Path(p)) == digest for p, digest in existing_hashes.items()), 'Existing candidate changed'
        report['status'] = 'imported-needs-fresh-verification' if APPLY or COLLISION else 'verified-fresh-native'
        if any(not asset['triangleCollision'] for asset in report['assets']):
            report['status'] = 'geometry-verified-collision-review-required'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        after = {str(p.relative_to(ROOT)): sha(p) for p in protected}
        report['protectedHashes'] = before
        report['protectedFilesUnchanged'] = before == after
        if before != after:
            report.update(status='failed', error='Protected original mesh or map changed')
        with output.open('x', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2)
            handle.write('\n')
        ue.log('Court outlet: ' + str(output))


if __name__ == '__main__':
    main()

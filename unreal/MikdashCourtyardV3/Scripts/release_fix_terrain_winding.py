"""Diagnose and fix inverted triangle winding on the four FutureMountV1 terrain cut tiles.

Background
----------
Scripts/import_future_mount_terrain.py built SM_JerusalemTerrain_*_FutureMountCut from
SourceAssets/FutureMountV1/terrain-generated/*.mesh.json.  Those JSON faces are wound
CCW in the mathematical x/y sense (cross(B-A, C-A).z > 0).  Unreal is left-handed and its
geometry code computes the triangle normal as cross(C-A, B-A) (GeometryCore VectorUtil.h:84,
"Unreal has Left-Hand Coordinate System so we need to reverse this cross-product").  The
original 252 terrain tiles are wound the other way, so their front faces point up; the cut
tiles' front faces point down.  The one-sided M_JerusalemTerrain_VertexColor is back-face
culled when seen from above and the ground renders black.  Per-vertex normals and colors
were copied from the originals and are correct, only the index order is wrong.

Native APIs (all previously proven in this repo unless noted):
  GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2   import_future_mount_terrain.extract()
  GeometryScript_MeshQueries.get_triangle_positions/normals/vertex_colors
                                                            import_future_mount_terrain.extract()
  GeometryScript_MeshQueries.get_triangle_face_normal       MeshQueryFunctions.h:152 (new here;
                                                            wraps FDynamicMesh3::GetTriNormal)
  GeometryScript_MeshEdits.append_buffers_to_mesh           import_future_mount_terrain.run()
  GeometryScript_AssetUtils.copy_mesh_to_static_mesh        MeshAssetFunctions.h:301 (new here;
                                                            in-place LOD0 source-model rewrite,
                                                            bReplaceMaterials=False keeps slots)
  StaticMeshEditorSubsystem.has_vertex_colors, get_bounding_box, get_num_triangles(0)
                                                            audit_future_mount_routes.audit()
  EditorAssetSubsystem.save_loaded_asset                    import_future_mount_terrain.run()

Invocation (hidden editor, both modes share the runner; the flag goes on the editor line):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject /Engine/Maps/Entry
      -ExecutePythonScript=C:/Mikdash/Working-5.8/run-release-fix-terrain-winding.py
      -unattended -nosplash -nullrhi -EnablePlugins=GeometryScripting [-DiagnoseOnly]
      -abslog=C:/Mikdash/Working-5.8/Release-Terrain-Winding-01.log
"""
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUTPUT = ROOT / 'SourceAssets/FutureMountV1'
MANIFEST = OUTPUT / 'terrain-generated/terrain-cut-manifest.json'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
CUT_FOLDER = '/Game/MikdashV3/FutureMountV1/Terrain/'
ORIGINAL_FOLDER = '/Game/MikdashV3/JerusalemContext/Terrain/'
WALKTHROUGH_MAP = ROOT / 'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap'
EXPECTED_MATERIAL = ('/Game/MikdashV3/JerusalemContext/Materials/M_JerusalemTerrain_VertexColor.'
                     'M_JerusalemTerrain_VertexColor')
CONTROL_ORIGINALS = ['SM_JerusalemTerrain_07_07', 'SM_JerusalemTerrain_08_08']
CONFIRM_FRACTION = 0.99
BOUNDS_TOLERANCE_CM = 0.05


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def xyz(v):
    return [v.x, v.y, v.z]


def rgba(c):
    return [c.r, c.g, c.b, c.a]


def content_file(asset_path):
    """/Game/... asset path -> Content/....uasset file."""
    assert asset_path.startswith('/Game/')
    return ROOT / ('Content/' + asset_path[len('/Game/'):] + '.uasset')


def ue_face_normal_z(a, b, c):
    """Unnormalized z of Unreal's left-handed triangle normal cross(C-A, B-A)."""
    e1 = [b[i] - a[i] for i in range(3)]
    e2 = [c[i] - a[i] for i in range(3)]
    return e2[0] * e1[1] - e2[1] * e1[0]


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


class Native:
    """Thin wrapper around the GeometryScript calls this fix relies on."""

    def __init__(self):
        import unreal as ue
        self.ue = ue
        for name in ['GeometryScript_MeshEdits', 'GeometryScript_AssetUtils', 'GeometryScript_MeshQueries']:
            assert hasattr(ue, name), 'Launch with -EnablePlugins=GeometryScripting: ' + name
        self.edits = ue.GeometryScript_MeshEdits
        self.asset_utils = ue.GeometryScript_AssetUtils
        self.query = ue.GeometryScript_MeshQueries
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.static_mesh_editor = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)

    def load_static_mesh(self, asset_path):
        mesh = self.assets.load_asset(asset_path)
        assert isinstance(mesh, self.ue.StaticMesh), 'Not a StaticMesh: ' + asset_path
        return mesh

    def source_dynamic_mesh(self, mesh):
        """Source-model LOD0 -> DynamicMesh, exactly as import_future_mount_terrain.extract()."""
        ue = self.ue
        dynamic = ue.DynamicMesh()
        options = ue.GeometryScriptCopyMeshFromAssetOptions()
        options.set_editor_property('apply_build_settings', False)
        options.set_editor_property('request_tangents', False)
        options.set_editor_property('use_build_scale', False)
        lod = ue.GeometryScriptMeshReadLOD()
        lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
        lod.set_editor_property('lod_index', 0)
        result = self.asset_utils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
        assert ue.GeometryScriptOutcomePins.SUCCESS in result, 'Source-mesh extraction failed'
        return dynamic

    def triangles(self, dynamic):
        """Per-triangle corner positions, stored normals, colors and both face-normal readings."""
        ue = self.ue
        rows = []
        for tid in range(dynamic.get_triangle_count()):
            position_result = self.query.get_triangle_positions(dynamic, tid)
            positions = [xyz(v) for v in position_result if isinstance(v, ue.Vector)]
            assert True in position_result and len(positions) == 3
            normal_result = self.query.get_triangle_normals(dynamic, tid)
            normals = [xyz(v) for v in normal_result if isinstance(v, ue.Vector)]
            color_result = self.query.get_triangle_vertex_colors(dynamic, tid)
            colors = [rgba(c) for c in color_result if isinstance(c, ue.LinearColor)]
            assert len(normals) == 3 and True in normal_result, 'Triangle %d has no stored normals' % tid
            assert len(colors) == 3 and True in color_result, 'Triangle %d has no vertex colors' % tid
            face_result = self.query.get_triangle_face_normal(dynamic, tid)
            face_normals = [xyz(v) for v in face_result if isinstance(v, ue.Vector)] if isinstance(face_result, tuple) else [xyz(face_result)]
            assert len(face_normals) == 1
            rows.append(dict(positions=positions, normals=normals, colors=colors,
                             faceNormal=face_normals[0],
                             crossZ=ue_face_normal_z(*positions)))
        return rows

    def build_reversed(self, rows):
        """Rebuild a DynamicMesh with identical corner attributes and reversed winding."""
        ue = self.ue
        positions, normals, colors = [], [], []
        for row in rows:
            for corner in (2, 1, 0):
                positions.append(row['positions'][corner])
                normals.append(row['normals'][corner])
                colors.append(row['colors'][corner])
        buffers = ue.GeometryScriptSimpleMeshBuffers()
        buffers.set_editor_property('vertices', [ue.Vector(*v) for v in positions])
        buffers.set_editor_property('normals', [ue.Vector(*v) for v in normals])
        buffers.set_editor_property('vertex_colors', [ue.LinearColor(*c) for c in colors])
        buffers.set_editor_property('triangles', [ue.IntVector(i, i + 1, i + 2) for i in range(0, len(positions), 3)])
        # Same metric UV policy as the original import: nondegenerate UVs for tangent generation only.
        buffers.set_editor_property('uv0', [ue.Vector2D(v[0] / 100, v[1] / 100) for v in positions])
        dynamic = ue.DynamicMesh()
        self.edits.append_buffers_to_mesh(dynamic, buffers)
        assert dynamic.get_triangle_count() == len(rows)
        return dynamic

    def write_in_place(self, dynamic, mesh):
        """Overwrite LOD0 source model of an existing asset; materials/slots untouched."""
        ue = self.ue
        options = ue.GeometryScriptCopyMeshToAssetOptions()
        settings = dict(enable_recompute_normals=False,
                        enable_recompute_tangents=True,
                        enable_remove_degenerates=False,
                        use_original_vertex_order=True,
                        replace_materials=False,
                        apply_nanite_settings=False,
                        emit_transaction=False,
                        defer_mesh_post_edit_change=False)
        for key, value in settings.items():
            options.set_editor_property(key, value)
        lod = ue.GeometryScriptMeshWriteLOD()
        lod.set_editor_property('write_hi_res_source', False)
        lod.set_editor_property('lod_index', 0)
        result = self.asset_utils.copy_mesh_to_static_mesh(dynamic, mesh, options, lod)
        assert ue.GeometryScriptOutcomePins.SUCCESS in result, 'copy_mesh_to_static_mesh failed'
        return settings

    def render_summary(self, mesh):
        bounds = mesh.get_bounding_box()
        material = mesh.get_material(0)
        setup = mesh.get_editor_property('body_setup')
        try:
            slots = len(mesh.get_editor_property('static_materials'))
        except Exception:  # noqa: BLE001 - property exposure differs between engine builds
            slots = None
        return dict(renderTriangles=mesh.get_num_triangles(0),
                    renderVertices=mesh.get_num_vertices(0),
                    vertexColorsPresent=bool(self.static_mesh_editor.has_vertex_colors(mesh)),
                    boundsCm={'min': xyz(bounds.min), 'max': xyz(bounds.max)},
                    material=material.get_path_name() if material else None,
                    materialSlots=slots,
                    collisionTraceFlag=str(setup.get_editor_property('collision_trace_flag')) if setup else None,
                    doubleSidedCollision=bool(setup.get_editor_property('double_sided_geometry')) if setup else None,
                    lodForCollision=mesh.get_editor_property('lod_for_collision'))

    def reload_from_disk(self, asset_path):
        """Best effort: drop the in-memory package and reload the saved file."""
        ue = self.ue
        package = ue.load_package(asset_path)
        assert package is not None
        result = ue.EditorLoadingAndSavingUtils.reload_packages(
            [package], ue.ReloadPackagesInteractionMode.ASSUME_POSITIVE)
        reloaded = bool(result[0]) if isinstance(result, tuple) else bool(result)
        return reloaded, self.load_static_mesh(asset_path)


def summarize(rows):
    total = len(rows)
    faces_up = sum(1 for r in rows if r['faceNormal'][2] > 0)
    faces_down = sum(1 for r in rows if r['faceNormal'][2] < 0)
    cross_up = sum(1 for r in rows if r['crossZ'] > 0)
    disagreements = sum(1 for r in rows if (r['faceNormal'][2] > 0) != (r['crossZ'] > 0))
    normal_z = [n[2] for r in rows for n in r['normals']]
    return dict(triangles=total,
                facesUp=faces_up,
                facesDown=faces_down,
                facesFlat=total - faces_up - faces_down,
                crossProductUp=cross_up,
                faceNormalVsCrossDisagreements=disagreements,
                vertexNormalUpFraction=(sum(1 for z in normal_z if z > 0) / len(normal_z)) if normal_z else None,
                vertexNormalMinZ=min(normal_z) if normal_z else None)


def classify(summary):
    if summary['triangles'] == 0:
        return 'empty'
    if summary['facesUp'] >= CONFIRM_FRACTION * summary['triangles']:
        return 'up'
    if summary['facesDown'] >= CONFIRM_FRACTION * summary['triangles']:
        return 'down'
    return 'mixed'


def diagnose(native, tiles):
    """Step 1: winding-vs-stored-normal report for the cut tiles and two original controls."""
    entries = []
    for asset_path, role, expected_triangles in tiles:
        mesh = native.load_static_mesh(asset_path)
        rows = native.triangles(native.source_dynamic_mesh(mesh))
        summary = summarize(rows)
        summary.update(asset=asset_path, role=role, expectedTriangles=expected_triangles,
                       orientation=classify(summary), render=native.render_summary(mesh))
        entries.append(summary)
    originals_up = all(e['orientation'] == 'up' and e['vertexNormalUpFraction'] >= CONFIRM_FRACTION
                       for e in entries if e['role'] == 'original')
    cuts_down = all(e['orientation'] == 'down' and e['vertexNormalUpFraction'] >= CONFIRM_FRACTION
                    for e in entries if e['role'] == 'cut')
    counts_ok = all(e['triangles'] == e['expectedTriangles'] == e['render']['renderTriangles']
                    for e in entries if e['role'] == 'cut')
    reasons = []
    if not originals_up:
        reasons.append('Original control tiles are not uniformly front-facing up; readback convention unverified')
    if not cuts_down:
        reasons.append('Cut tiles are not uniformly front-facing down while vertex normals point up')
    if not counts_ok:
        reasons.append('Cut tile source/render triangle counts differ from manifest')
    return dict(entries=entries, inversionConfirmed=originals_up and cuts_down and counts_ok, reasons=reasons,
                convention='faceNormal from GeometryScript get_triangle_face_normal (FDynamicMesh3::GetTriNormal, '
                           'left-handed cross(C-A,B-A)); crossZ computed independently with the same convention; '
                           'up means the rendered front face is visible from +Z')


def fix_tile(native, asset_path, before_entry, checkpoint_dir, report_item):
    """Step 2 for one asset: back up, rebuild with reversed winding, save, verify."""
    ue = native.ue
    name = asset_path.rsplit('/', 1)[1]
    uasset = content_file(asset_path)
    mesh = native.load_static_mesh(asset_path)
    rows = native.triangles(native.source_dynamic_mesh(mesh))
    assert len(rows) == before_entry['triangles']
    render_before = native.render_summary(mesh)
    assert render_before['material'] == EXPECTED_MATERIAL, 'Unexpected material on ' + asset_path

    # Backup: full corner data as JSON plus a byte copy of the .uasset.
    backup = dict(asset=asset_path, sourceUassetSha256=sha(uasset), triangles=len(rows),
                  positions=[p for r in rows for p in r['positions']],
                  normals=[n for r in rows for n in r['normals']],
                  colors=[c for r in rows for c in r['colors']],
                  faces=[[3 * i, 3 * i + 1, 3 * i + 2] for i in range(len(rows))],
                  render=render_before)
    write_json(checkpoint_dir / (name + '.before.json'), backup)
    shutil.copy2(uasset, checkpoint_dir / uasset.name)
    assert sha(checkpoint_dir / uasset.name) == backup['sourceUassetSha256']
    report_item.update(backupJson=str(checkpoint_dir / (name + '.before.json')),
                       backupUasset=str(checkpoint_dir / uasset.name),
                       uassetSha256Before=backup['sourceUassetSha256'], renderBefore=render_before)

    # Rebuild in memory and prove the new DynamicMesh is up-facing before touching the asset.
    reversed_dynamic = native.build_reversed(rows)
    rebuilt = summarize(native.triangles(reversed_dynamic))
    assert rebuilt['triangles'] == len(rows) and rebuilt['facesUp'] == len(rows), 'Rebuilt DynamicMesh not uniformly up'
    report_item['rebuiltDynamicMesh'] = rebuilt

    # Write in place, restore asset-level collision settings if PostEditChange touched them, save.
    report_item['copyOptions'] = native.write_in_place(reversed_dynamic, mesh)
    setup = mesh.get_editor_property('body_setup')
    assert setup is not None
    if setup.get_editor_property('collision_trace_flag') != ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
        setup.set_editor_property('collision_trace_flag', ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        report_item['restoredCollisionTraceFlag'] = True
    if not setup.get_editor_property('double_sided_geometry'):
        setup.set_editor_property('double_sided_geometry', True)
        report_item['restoredDoubleSidedGeometry'] = True
    assert native.assets.save_loaded_asset(mesh, only_if_is_dirty=False), 'Save failed: ' + asset_path
    report_item['saved'] = True
    report_item['uassetSha256After'] = sha(uasset)

    # Verify: reload (from disk where possible) and re-run the diagnostic.
    try:
        reloaded, mesh = native.reload_from_disk(asset_path)
    except Exception as error:  # noqa: BLE001 - verification falls back to in-memory asset
        reloaded, mesh = False, native.load_static_mesh(asset_path)
        report_item['reloadError'] = str(error)
    report_item['reloadedFromDisk'] = reloaded
    after_rows = native.triangles(native.source_dynamic_mesh(mesh))
    after = summarize(after_rows)
    render_after = native.render_summary(mesh)
    after.update(render=render_after, orientation=classify(after))
    report_item['after'] = after

    problems = []
    if after['triangles'] != before_entry['triangles']:
        problems.append('triangle count changed')
    if after['facesUp'] != after['triangles']:
        problems.append('not all faces up after fix')
    if render_after['renderTriangles'] != before_entry['expectedTriangles']:
        problems.append('render triangle count %s != %s' % (render_after['renderTriangles'], before_entry['expectedTriangles']))
    for key in ('min', 'max'):
        for axis in range(3):
            delta = abs(render_after['boundsCm'][key][axis] - render_before['boundsCm'][key][axis])
            if delta > BOUNDS_TOLERANCE_CM:
                problems.append('bounds %s[%d] moved %.4f cm' % (key, axis, delta))
    if not render_after['vertexColorsPresent']:
        problems.append('vertex colors missing after fix')
    if render_after['material'] != EXPECTED_MATERIAL:
        problems.append('material changed to %s' % render_after['material'])
    if render_after['materialSlots'] != render_before['materialSlots']:
        problems.append('material slot count changed')
    # Corner attributes must be identical to the backup, only the order within each triangle reversed.
    max_position = max_normal = max_color = 0.0
    for before_row, after_row in zip(rows, after_rows):
        for corner in range(3):
            source = 2 - corner
            max_position = max(max_position, max(abs(before_row['positions'][source][k] - after_row['positions'][corner][k]) for k in range(3)))
            max_normal = max(max_normal, max(abs(before_row['normals'][source][k] - after_row['normals'][corner][k]) for k in range(3)))
            max_color = max(max_color, max(abs(before_row['colors'][source][k] - after_row['colors'][corner][k]) for k in range(4)))
    report_item.update(maxPositionErrorCm=max_position, maxNormalError=max_normal, maxLinearColorError=max_color)
    if max_position > 0.01 or max_normal > 1e-5 or max_color > 1e-5:
        problems.append('corner attributes drifted (pos %.5f, normal %.2e, color %.2e)' % (max_position, max_normal, max_color))
    report_item['problems'] = problems
    report_item['status'] = 'fixed_and_verified' if not problems else 'saved_but_verification_failed'
    return not problems


def main(diagnose_only=None):
    import unreal as ue
    assert Path(ue.Paths.project_dir()).resolve() == ROOT
    command_line = ue.SystemLibrary.get_command_line().lower()
    if diagnose_only is None:
        diagnose_only = '-diagnoseonly' in command_line
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    native = Native()
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    assert not editor.get_game_world(), 'PIE active; refusing to run'
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()

    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    cut_tiles = [(CUT_FOLDER + t['replacementAssetName'], 'cut', t['outputTriangles']) for t in manifest['tiles']]
    control_tiles = [(ORIGINAL_FOLDER + n, 'original', 512) for n in CONTROL_ORIGINALS]
    protected = {str(content_file(p)): sha(content_file(p)) for p, _, _ in control_tiles}
    protected[str(WALKTHROUGH_MAP)] = sha(WALKTHROUGH_MAP)

    diagnostic = diagnose(native, cut_tiles + control_tiles)
    diagnostic.update(stamp=stamp, mode='diagnose_only' if diagnose_only else 'diagnose_and_fix',
                      status='inversion_confirmed' if diagnostic['inversionConfirmed'] else 'inversion_not_confirmed')
    diagnostic_path = OUTPUT / ('terrain-winding-diagnostic-%s.json' % stamp)
    write_json(diagnostic_path, diagnostic)
    ue.log('release_fix_terrain_winding: diagnostic %s -> %s' % (diagnostic['status'], diagnostic_path))
    if diagnose_only:
        return diagnostic
    if not diagnostic['inversionConfirmed']:
        ue.log_warning('release_fix_terrain_winding: not confirmed, nothing modified: %s' % '; '.join(diagnostic['reasons']))
        return diagnostic

    checkpoint_dir = CHECKPOINT_ROOT / ('TerrainWinding-' + stamp)
    checkpoint_dir.mkdir(parents=True, exist_ok=False)
    receipt_path = OUTPUT / ('terrain-winding-fix-%s.json' % stamp)
    receipt = dict(status='started', stamp=stamp, diagnostic=str(diagnostic_path), checkpoint=str(checkpoint_dir),
                   walkthroughMapLoaded=False, tiles=[], protectedHashes=protected)
    by_asset = {e['asset']: e for e in diagnostic['entries']}
    try:
        for asset_path, _, _ in cut_tiles:
            item = dict(asset=asset_path, status='started', before=by_asset[asset_path])
            receipt['tiles'].append(item)
            write_json(receipt_path, receipt)
            ok = fix_tile(native, asset_path, by_asset[asset_path], checkpoint_dir, item)
            write_json(receipt_path, receipt)
            assert ok, 'Verification failed for %s: %s' % (asset_path, item['problems'])
        assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'A map became dirty'
        dirty = ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()
        receipt['dirtyContentPackagesAfterSave'] = [p.get_name() for p in dirty]
        receipt['status'] = 'four_cut_tiles_rewound_saved_verified_visual_review_pending'
    except Exception as error:  # noqa: BLE001 - receipt must record partial state
        receipt.update(status='failed_partial_state_preserved', error=str(error))
        raise
    finally:
        receipt['protectedFilesUnchanged'] = {p: sha(p) == h for p, h in protected.items()}
        receipt['allProtectedUnchanged'] = all(receipt['protectedFilesUnchanged'].values())
        write_json(receipt_path, receipt)
        ue.log('release_fix_terrain_winding: %s -> %s' % (receipt['status'], receipt_path))
    return receipt

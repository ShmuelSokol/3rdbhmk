"""Coordinator-only Entry study. Never loads a project map or edits a source asset.

Build: fresh duplicates, polygon groups only, optional ONE isolated asset save.
Verify: separate process loads that saved candidate and repeats exact proof/captures.
All native behavior remains unverified until the guarded coordinator run succeeds.
"""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import struct
import sys
import traceback

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from haram_threshold_study_common import (ROOT, OUT, NS, SOURCE, STAIRS, PAVING, ASHLAR,
    require, sha, disk, snapshot, validate_pins, source_triangles, face_role, geometry_counter,
    revision_hashes, require_preflight)
from haram_threshold_png import sanitize_new_export


class AuditedMeshQueries:
    """CDO access limited to the FIVE locally audited stateless getters. No setters."""
    def __init__(self, ue):
        self._cdo = ue.get_default_object(ue.StaticMeshEditorSubsystem)
        require(self._cdo is not None, 'StaticMeshEditorSubsystem CDO unavailable')
        self.identity = self._cdo.get_path_name()

    def get_lod_build_settings(self, mesh, lod):
        return self._cdo.get_lod_build_settings(mesh, lod)

    def get_simple_collision_count(self, mesh):
        return self._cdo.get_simple_collision_count(mesh)

    def get_convex_collision_count(self, mesh):
        return self._cdo.get_convex_collision_count(mesh)

    def is_section_collision_enabled(self, mesh, lod, section):
        return self._cdo.is_section_collision_enabled(mesh, lod, section)

    def is_section_cast_shadow_enabled(self, mesh, lod, section):
        return self._cdo.is_section_cast_shadow_enabled(mesh, lod, section)


QUERIES = None


def initialize_entry_world(ue, report):
    """One permitted startup load; the positional commandlet map argument is inert."""
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    require(editor is not None, 'UnrealEditorSubsystem unavailable')
    def identity(world):
        return None if world is None else dict(package=world.get_outermost().get_name(), objectPath=world.get_path_name())
    initial = editor.get_editor_world()
    report['initialWorld'] = identity(initial)
    report['initialGameWorld'] = identity(editor.get_game_world())
    ue.log('HARAM_THRESHOLD_INITIAL_WORLD '+json.dumps(report['initialWorld']))
    require(report['initialGameWorld'] is None, 'PIE/game world exists before Entry load')
    require(initial is None or not initial.get_outermost().get_name().startswith('/Game/'),
            'Refusing startup in a project map; never discard or save it')
    # User-authorized exact literal ONLY: no project map or dynamic-path fallback.
    loaded = ue.EditorLoadingAndSavingUtils.load_map('/Engine/Maps/Entry')
    report['entryLoadReturn'] = identity(loaded)
    ue.log('HARAM_THRESHOLD_ENTRY_LOAD_RETURN '+json.dumps(report['entryLoadReturn']))
    require(loaded is not None, 'Hardcoded Engine Entry load returned null')
    world = entry_world(ue)
    require(loaded == world, 'LoadMap return differs from current editor world')
    report['loadedWorld'] = identity(world)
    return world


def entry_world(ue):
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    require(editor is not None, 'UnrealEditorSubsystem unavailable; no substitute CDO allowed')
    world = editor.get_editor_world()
    require(world is not None and world.get_outermost().get_name() == '/Engine/Maps/Entry',
            'Expected Engine Entry after the single hardcoded startup load; no fallback')
    require(editor.get_game_world() is None, 'PIE/game world exists')
    return world


def probe_queries(ue, original):
    global QUERIES
    entry_world(ue)
    require(original.get_num_lods() == 1 and original.get_num_sections(0) == 1, 'Expected one source LOD/section')
    q = AuditedMeshQueries(ue)
    body = original.get_editor_property('body_setup')
    require(body is not None, 'Missing BodySetup')
    agg = body.get_editor_property('agg_geom')
    direct = {k: len(agg.get_editor_property(k)) for k in ('box_elems','sphere_elems','sphyl_elems','convex_elems')}
    simple, convex = q.get_simple_collision_count(original), q.get_convex_collision_count(original)
    require(type(simple) is int and simple >= 0 and simple == sum(direct[k] for k in ('box_elems','sphere_elems','sphyl_elems')),
            'Simple collision query invalid or disagrees with direct BodySetup')
    require(type(convex) is int and convex >= 0 and convex == direct['convex_elems'], 'Convex query invalid or disagrees with BodySetup')
    collision = q.is_section_collision_enabled(original, 0, 0)
    shadow = q.is_section_cast_shadow_enabled(original, 0, 0)
    require(collision is True and shadow is True, 'Expected TRUE source collision/shadow; false/error ambiguity refused')
    settings = q.get_lod_build_settings(original, 0)
    require(isinstance(settings, ue.MeshBuildSettings), 'Build settings return type invalid')
    scale = settings.get_editor_property('build_scale3d')
    require([scale.x, scale.y, scale.z] == [1.0,1.0,1.0], 'Unexpected source build scale')
    lightmap = settings.get_editor_property('min_lightmap_resolution')
    require(type(lightmap) is int and lightmap > 0, 'Invalid numeric build settings')
    require(body.get_editor_property('collision_trace_flag') == ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
            'Unexpected source collision policy')
    QUERIES = q  # Only install after every positive guard proof has passed.
    return dict(cdo=q.identity, auditedFunctions=5, directBodySetupCounts=direct,
                simpleCount=simple, convexCount=convex, collisionEnabled=collision, castShadow=shadow,
                collisionNumeric=int(collision), shadowNumeric=int(shadow), buildScale=[scale.x,scale.y,scale.z],
                minLightmapResolution=lightmap, buildSettings=settings.export_text(),
                rationale='Positive section queries and nonnegative direct-matching counts pass the shared game-thread/editor/no-PIE helper; no subsystem instance state is read.')


def query_source_evidence():
    evidence = json.loads((OUT / 'query-source-evidence.json').read_text())
    for row in evidence['files']:
        require(sha(row['path']) == row['sha256'], 'Audited engine source changed: '+row['path'])
    return evidence


def mapping_render_profile(ue):
    expected = {'r.DynamicGlobalIlluminationMethod': 0, 'r.ReflectionMethod': 0,
                'r.Shadow.Virtual.Enable': 0, 'r.Nanite': 1}
    actual = {name: ue.SystemLibrary.get_console_variable_int_value(name) for name in expected}
    require(actual == expected, 'Unexpected mapping-review render profile: '+repr(actual))
    return dict(name='direct-sun-mapping-v1', cvars=actual, resolution=[960,720],
                limitation='Isolated mapping/shading comparison; not production lighting acceptance. No texture quality or Nanite reduction.')


def probe_build_api(ue, original):
    """Check only Build dependencies; never invoke clone/save/mesh mutation methods."""
    checked = []
    def methods(owner, label, names):
        for name in names:
            require(callable(getattr(owner, name, None)), 'Missing callable '+label+'.'+name)
            checked.append(label+'.'+name)
    methods(ue, 'unreal', ('StaticMaterial', 'TriangleID'))
    methods(getattr(ue, 'SourceControl', None), 'SourceControl', ('is_enabled',))
    enabled = ue.SourceControl.is_enabled()
    require(enabled is False, 'Source control must be disabled before duplication')
    methods(getattr(ue, 'AssetToolsHelpers', None), 'AssetToolsHelpers', ('get_asset_tools',))
    methods(ue.AssetToolsHelpers.get_asset_tools(), 'AssetTools', ('duplicate_asset',))
    methods(getattr(ue, 'EditorAssetLibrary', None), 'EditorAssetLibrary',
            ('does_directory_exist', 'save_loaded_asset'))
    methods(original, 'StaticMesh', ('get_static_mesh_description', 'build_from_static_mesh_descriptions', 'set_material',
                                    'get_editor_property', 'set_editor_property'))
    desc = original.get_static_mesh_description(0)
    require(desc is not None, 'Source MeshDescription unavailable')
    methods(desc, 'StaticMeshDescription', ('get_triangle_count', 'is_triangle_valid',
        'get_triangle_vertex_instance', 'get_vertex_position', 'get_vertex_instance_vertex',
        'get_polygon_group_count', 'get_triangle_polygon_group', 'get_triangle_polygon',
        'set_polygon_group_material_slot_name', 'create_polygon_group', 'set_polygon_polygon_group'))
    require(desc.get_polygon_group_count() == 1, 'Expected one source polygon group')
    require(len(description_rows(ue, desc)) == 180, 'Source MeshDescription read failed')
    return dict(sourceControlEnabled=enabled, callableChecks=checked, sourceDescriptionTriangles=180,
                scope='Availability plus source-only reads; mutation signatures/behavior require Build proof')


def validate_isolated_files(files, candidate, save, verify, status, saved):
    allowed = {candidate} if save or verify else set()
    require(set(files) <= allowed, 'Unexpected isolated files saved: '+repr(files))
    if verify or saved or (save and status == 'captured-review-pending'):
        require(files == [candidate], 'Required saved candidate missing: '+repr(files))


def preflight(ue, run_id, output, candidate_path, manifest):
    protected = snapshot(manifest['protectedPaths'])
    report = dict(status='started', mode='preflight', runId=run_id, revisionHashes=revision_hashes(),
                  protectedBefore=protected, captures=[], scope='Read-only Entry CDO query preflight; no actors/candidate/save/render')
    try:
        world = initialize_entry_world(ue, report)
        report['renderProfile'] = mapping_render_profile(ue)
        report['entryNoPIE'] = dict(world=world.get_outermost().get_name(), gameWorld=None)
        report['querySourceEvidence'] = query_source_evidence()
        validate_pins()
        require(not disk(candidate_path).parent.exists(), 'Preflight requires fresh candidate namespace')
        protected.update(snapshot(dependency_paths(ue)))
        (output / 'native-protected.json').write_text(json.dumps(protected, indent=2)+'\n')
        original = ue.load_asset(SOURCE)
        require(isinstance(original, ue.StaticMesh), 'Source missing')
        ue.AutomationLibrary.finish_loading_before_screenshot()
        report['queries'] = probe_queries(ue, original)
        report['buildApi'] = probe_build_api(ue, original)
        data = rows(ue, original)
        require(len(data) == 180 and all(r['materialId'] == 0 for r in data), 'Unexpected source triangles/material')
        require(geometry_counter(r['positions'] for r in data) == geometry_counter(source_triangles()), 'Pinned OBJ/source mismatch')
        report['sourceTriangleCount'] = len(data)
        report['status'] = 'preflight-passed'
    except Exception:
        report.update(status='failed', error=traceback.format_exc())
    finally:
        try:
            report['protectedAfter'] = snapshot(sorted(protected))
            require(protected == report['protectedAfter'], 'Protected inputs changed')
            require(not disk(candidate_path).parent.exists(), 'Preflight created candidate content')
            require(report['revisionHashes'] == revision_hashes(), 'Study revision changed during preflight')
        except Exception:
            report.update(status='failed', preservationError=traceback.format_exc())
        report['completedUtc'] = datetime.now(timezone.utc).isoformat()
        (output / 'native.json').write_text(json.dumps(report, indent=2)+'\n')
    require(report['status'] == 'preflight-passed', 'Read-only preflight failed; inspect native.json')
    ue.log('HARAM_THRESHOLD_STUDY_COMPLETE preflight '+run_id)


def rows(ue, mesh, render=False):
    """GeometryScript is READ-ONLY here; no conversion back through DynamicMesh."""
    dynamic = ue.DynamicMesh()
    options = ue.GeometryScriptCopyMeshFromAssetOptions()
    for key in ('apply_build_settings', 'use_build_scale', 'request_tangents'):
        options.set_editor_property(key, False)
    lod = ue.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', ue.GeometryScriptLODType.RENDER_DATA if render else ue.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
    require(ue.GeometryScriptOutcomePins.SUCCESS in result, 'Mesh read failed')
    q = ue.GeometryScript_MeshQueries
    require(not q.get_has_triangle_id_gaps(dynamic), 'Sparse triangle IDs unsupported')

    def vectors(value, typ, fields):
        require([v for v in value if type(v) is bool] == [True], 'Invalid triangle data')
        points = [[getattr(v, f) for f in fields] for v in value if isinstance(v, typ)]
        require(len(points) == 3, 'Expected three corners')
        return points

    output = []
    for tid in range(dynamic.get_triangle_count()):
        p = vectors(q.get_triangle_positions(dynamic, tid), ue.Vector, ('x','y','z'))
        mid = ue.GeometryScript_Materials.get_triangle_material_id(dynamic, tid)
        require([v for v in mid if type(v) is bool] == [True], 'Invalid material ID')
        ids = [v for v in mid if type(v) is int]
        require(len(ids) == 1, 'Ambiguous material ID')
        attrs = {}
        if q.get_has_triangle_normals(dynamic):
            attrs['normal'] = vectors(q.get_triangle_normals(dynamic, tid), ue.Vector, ('x','y','z'))
        if q.get_has_vertex_colors(dynamic):
            attrs['color'] = vectors(q.get_triangle_vertex_colors(dynamic, tid), ue.LinearColor, ('r','g','b','a'))
        uv_query = getattr(q, 'get_triangle_uvs', None) or getattr(q, 'get_triangle_u_vs', None)
        for uv in range(q.get_num_uv_sets(dynamic)):
            attrs['uv'+str(uv)] = vectors(uv_query(dynamic, uv, tid), ue.Vector2D, ('x','y'))
        output.append(dict(positions=p, materialId=ids[0], attrs=attrs))
    return output


def attributed_counter(data):
    # Preserve corner associations as well as geometry, with cyclic starts allowed.
    result = Counter()
    for row in data:
        corners = [tuple(row['positions'][i]) + tuple((k, tuple(v[i])) for k, v in sorted(row['attrs'].items())) for i in range(3)]
        key = min(tuple(corners), tuple(corners[1:]+corners[:1]), tuple(corners[2:]+corners[:2]))
        result[key] += 1
    return result


def policy(ue, mesh):
    require(QUERIES is not None, 'Positive CDO preflight required')
    editor = QUERIES
    body = mesh.get_editor_property('body_setup')
    require(body is not None, 'Missing collision body')
    return dict(lods=mesh.get_num_lods(),
                nanite=mesh.get_editor_property('nanite_settings').export_text(),
                build=editor.get_lod_build_settings(mesh, 0).export_text(),
                complexity=str(body.get_editor_property('collision_trace_flag')),
                simpleGeometry=body.get_editor_property('agg_geom').export_text(),
                simpleCount=editor.get_simple_collision_count(mesh),
                convexCount=editor.get_convex_collision_count(mesh),
                collisionLod=mesh.get_editor_property('lod_for_collision'),
                neverStream=mesh.get_editor_property('never_stream'))


def description_rows(ue, desc):
    require(desc is not None and desc.get_triangle_count() == 180, 'Expected 180 native source triangles')
    result = []
    for i in range(180):
        tid = ue.TriangleID(id_value=i)
        require(desc.is_triangle_valid(tid), 'Sparse MeshDescription IDs unsupported')
        points = []
        for corner in range(3):
            vi = desc.get_triangle_vertex_instance(tid, corner)
            p = desc.get_vertex_position(desc.get_vertex_instance_vertex(vi))
            points.append([p.x, p.y, p.z])
        result.append((tid, points))
    return result


def prove(ue, original, candidate):
    old, new = rows(ue, original), rows(ue, candidate)
    require(len(old) == len(new) == 180, 'Triangle count changed')
    require(geometry_counter(r['positions'] for r in old) == geometry_counter(source_triangles()), 'Native source differs from pinned float32 OBJ')
    require(attributed_counter(old) == attributed_counter(new), 'Source corner geometry/normal/UV/color changed')
    require([p for _, p in description_rows(ue, original.get_static_mesh_description(0))] ==
            [p for _, p in description_rows(ue, candidate.get_static_mesh_description(0))], 'Ordered source positions or winding changed')
    require(all(r['materialId'] == 0 for r in old), 'Unexpected baseline material sections')
    for row in new:
        wanted = 0 if face_role(row['positions']) == 'top' else 1
        require(row['materialId'] == wanted, 'Incorrect triangle material section')
    require(candidate.get_material(0) == original.get_material(0) == ue.load_asset(PAVING), 'Top material identity changed')
    require(candidate.get_material(1) == ue.load_asset(ASHLAR), 'Wrong side material')
    require(len(candidate.get_editor_property('static_materials')) == 2, 'Expected exactly two materials')
    require(policy(ue, original) == policy(ue, candidate), 'Collision/build/Nanite policy changed')
    render_old, render_new = rows(ue, original, True), rows(ue, candidate, True)
    require(len(render_old) == len(render_new) == 180, 'Render/fallback must retain all 180 triangles')
    require(geometry_counter(r['positions'] for r in render_old) == geometry_counter(r['positions'] for r in render_new), 'Render geometry/winding changed')
    require(attributed_counter(render_old) == attributed_counter(render_new), 'Render corner geometry/normal/UV/color changed')
    for row in render_new:
        require(row['materialId'] == (0 if face_role(row['positions']) == 'top' else 1), 'Render material split changed')
    editor = QUERIES
    require(all(editor.is_section_collision_enabled(candidate, 0, i) == editor.is_section_collision_enabled(original, 0, 0) for i in (0,1)), 'Section collision changed')
    require(all(editor.is_section_cast_shadow_enabled(candidate, 0, i) == editor.is_section_cast_shadow_enabled(original, 0, 0) for i in (0,1)), 'Section shadow behavior changed')
    def simple_physical_material(mesh):
        material = mesh.get_editor_property('body_setup').get_editor_property('phys_material')
        return None if material is None else material.get_path_name()
    physical_before, physical_after = simple_physical_material(original), simple_physical_material(candidate)
    require(physical_before == physical_after, 'Simple BodySetup physical material changed')
    return dict(sourceTriangles=180, renderTriangles=180, exactOrderedPositionsAndWinding=True,
                sourceCornerAttributesUnchanged=True, renderCornerAttributesUnchanged=True, topMaterialIdentityPreserved=True,
                physicalMaterial=dict(simpleBodySetupBefore=physical_before, simpleBodySetupAfter=physical_after,
                    limitation='Simple BodySetup readback only, not effective per-triangle physical material. Different section material IDs may change collision surface behavior. Cooked Chaos equivalence and production actor slot-1 overrides are not proven.'),
                policyUnchanged=True, counts=dict(Counter(face_role(r['positions']) for r in new)),
                collisionPolicy=policy(ue, candidate))


def create_candidate(ue, original, folder):
    require(ue.SourceControl.is_enabled() is False, 'SCC must be disabled: AssetTools duplication otherwise may save implicitly')
    require(not ue.EditorAssetLibrary.does_directory_exist(folder), 'Fresh study asset namespace required')
    require(not disk(folder + '/SM_ThresholdSides').parent.exists(), 'Study disk namespace already exists')
    require(original.get_num_lods() == 1, 'Expected one source LOD')
    # Separate working copy avoids giving BuildFromStaticMeshDescriptions a reference
    # to the candidate description that its rebuild replaces. Neither copy is saved here.
    tools = ue.AssetToolsHelpers.get_asset_tools()
    working = tools.duplicate_asset('SM_SectionWorkingCopy', folder, original)
    candidate = tools.duplicate_asset('SM_ThresholdSides', folder, original)
    require(working is not None and candidate is not None, 'Isolated duplication failed')
    require(candidate.get_editor_property('body_setup') != original.get_editor_property('body_setup'), 'Shared BodySetup refused')
    desc = working.get_static_mesh_description(0)
    require(desc != original.get_static_mesh_description(0), 'Shared MeshDescription refused')
    require(desc.get_polygon_group_count() == 1, 'Expected single source material group')
    source_rows = description_rows(ue, desc)
    first_group = desc.get_triangle_polygon_group(source_rows[0][0])
    side_group = desc.create_polygon_group()
    polygon_policy = {}
    for tid, points in source_rows:
        polygon = desc.get_triangle_polygon(tid)
        key = polygon.get_editor_property('id_value')
        slot = 0 if face_role(points) == 'top' else 1
        require(key not in polygon_policy or polygon_policy[key] == slot, 'Polygon straddles material policies')
        polygon_policy[key] = slot
        desc.set_polygon_polygon_group(polygon, first_group if slot == 0 else side_group)
    slots = []
    for material, name in ((ue.load_asset(PAVING), 'PavingTop'), (ue.load_asset(ASHLAR), 'AshlarSidesBottom')):
        slot = ue.StaticMaterial()
        slot.set_editor_property('material_interface', material)
        slot.set_editor_property('material_slot_name', name)
        slots.append(slot)
    candidate.set_editor_property('static_materials', slots)
    # Slow Build uses imported names. SetMaterial initializes these read-only fields
    # through the supported native API; never guess a Python constructor override.
    for index, material_path in enumerate((PAVING, ASHLAR)):
        candidate.set_material(index, ue.load_asset(material_path))
    built_slots = candidate.get_editor_property('static_materials')
    require(len(built_slots) == 2, 'Expected exactly two material slots')
    imported = [s.get_editor_property('imported_material_slot_name') for s in built_slots]
    require(all(str(n) not in ('', 'None') for n in imported) and imported[0] != imported[1],
            'Native imported slot initialization failed')
    for group, name in zip((first_group, side_group), imported):
        desc.set_polygon_group_material_slot_name(group, name)
    # Local StaticMesh render-data build, NOT UBT. No simplification/reimport/remesh.
    old_never_stream = candidate.get_editor_property('never_stream')
    candidate.build_from_static_mesh_descriptions([desc], build_simple_collision=False, fast_build=False)
    candidate.set_editor_property('never_stream', old_never_stream)
    ue.AutomationLibrary.finish_loading_before_screenshot()
    return candidate, working


def dependency_paths(ue):
    registry = ue.AssetRegistryHelpers.get_asset_registry()
    options = ue.AssetRegistryDependencyOptions(include_hard_package_references=True,
        include_soft_package_references=True, include_searchable_names=False,
        include_soft_management_references=False, include_hard_management_references=False)
    pending, visited, paths = [SOURCE, STAIRS, PAVING, ASHLAR], set(), set()
    while pending:
        asset = pending.pop()
        if asset in visited or not asset.startswith('/Game/'):
            continue
        require(len(visited) < 128, 'Unexpectedly large dependency closure')
        visited.add(asset)
        path = disk(asset)
        require(path.exists(), 'Missing protected project dependency: ' + asset)
        paths.add(path.relative_to(ROOT).as_posix())
        pending.extend(str(p) for p in registry.get_dependencies(asset, options))
    return sorted(paths)


def run():
    import unreal as ue
    command = ue.SystemLibrary.get_command_line()
    match = re.search(r'(?:^|\s)-ThresholdRun=([A-Za-z0-9_-]+)(?:\s|$)', command)
    require(match is not None and '-ThresholdCoordinator' in command, 'Use guarded coordinator wrapper')
    run_id = match.group(1)
    verify = '-ThresholdVerify' in command
    is_preflight = '-ThresholdPreflight' in command
    save = '-ThresholdSave' in command
    require(not ((verify or is_preflight) and save) and not (verify and is_preflight), 'Invalid mode/save combination')
    mode = 'preflight' if is_preflight else 'verify' if verify else 'build'
    run_folder = OUT / run_id
    output = run_folder / mode
    require(output.is_dir() and not (output / 'native.json').exists(), 'Wrapper must create fresh output')
    folder = NS + '/' + run_id
    candidate_path = folder + '/SM_ThresholdSides'
    manifest = json.loads((OUT / 'source-audit.json').read_text())
    if is_preflight:
        return preflight(ue, run_id, output, candidate_path, manifest)
    preflight_receipt = require_preflight(run_id)
    query_source_evidence()
    protected = snapshot(manifest['protectedPaths'])
    report = dict(status='started', mode=mode, world=None, candidate=candidate_path,
                  scope='Isolated Entry mesh/material study; no production adoption or packaged acceptance',
                  protectedBefore=protected, captures=[], preflight=preflight_receipt, revisionHashes=revision_hashes())
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    spawned = []

    def spawn(cls, pos, rot=None):
        obj = actors.spawn_actor_from_class(cls, ue.Vector(*pos), rot or ue.Rotator(), transient=True)
        require(obj is not None, 'Transient actor spawn failed')
        spawned.append(obj)
        return obj

    try:
        world = initialize_entry_world(ue, report)
        report['renderProfile'] = mapping_render_profile(ue)
        report['world'] = world.get_outermost().get_name()
        require(report['world'] == '/Engine/Maps/Entry', 'Only Engine Entry is permitted')
        validate_pins()
        protected.update(snapshot(dependency_paths(ue)))
        # Persist before any candidate operation, for wrapper checks even on crash/kill.
        (output / 'native-protected.json').write_text(json.dumps(protected, indent=2)+'\n')
        original = ue.load_asset(SOURCE)
        require(isinstance(original, ue.StaticMesh), 'Source mesh missing')
        report['queries'] = probe_queries(ue, original)
        if verify:
            previous = json.loads((run_folder / 'build/native.json').read_text())
            require(previous['status'] == 'captured-review-pending' and previous.get('savedCandidateSha256'), 'Successful saved build required')
            require(sha(disk(candidate_path)) == previous['savedCandidateSha256'], 'Saved candidate changed')
            candidate = ue.load_asset(candidate_path)
        else:
            candidate, working = create_candidate(ue, original, folder)
        ue.AutomationLibrary.finish_loading_before_screenshot()
        report['proof'] = prove(ue, original, candidate)
        study = spawn(ue.StaticMeshActor, (0,0,0)).static_mesh_component
        study.set_static_mesh(original)
        study.set_collision_profile_name('BlockAll')
        stairs = spawn(ue.StaticMeshActor, (0,0,0)).static_mesh_component
        stairs.set_static_mesh(ue.load_asset(STAIRS))
        light = spawn(ue.DirectionalLight, (0,0,1000), ue.Rotator(pitch=-45, yaw=0, roll=0))
        light.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        light.light_component.set_editor_property('intensity', 3.0)
        capture = spawn(ue.SceneCapture2D, (-15000,19300,-1300))
        component = capture.get_component_by_class(ue.SceneCaptureComponent2D)
        component.set_editor_property('capture_every_frame', False)
        component.set_editor_property('capture_on_movement', False)
        component.set_editor_property('capture_source', ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        target = ue.RenderingLibrary.create_render_target2d(world, 960, 720, ue.TextureRenderTargetFormat.RTF_RGBA8)
        component.set_editor_property('texture_target', target)
        settings = component.get_editor_property('post_process_settings')
        for key, value in dict(override_auto_exposure_min_brightness=True, override_auto_exposure_max_brightness=True,
                auto_exposure_min_brightness=1.0, auto_exposure_max_brightness=1.0,
                override_auto_exposure_bias=True, auto_exposure_bias=0.0,
                override_bloom_intensity=True, bloom_intensity=0.0).items():
            settings.set_editor_property(key, value)
        component.set_editor_property('post_process_settings', settings)
        cameras = [('accepted', (-15000,19300,-1300), (10,-10,0), 70),
                   ('edge-oblique', (-14300,19480,-1330), (-17,-35,0), 55),
                   ('top', (-13843.5,19087.25,-600), (-90,0,0), 40)]
        for view, position, rotation, fov in cameras:
            require(mapping_render_profile(ue) == report['renderProfile'], 'Render profile changed between views')
            capture.set_actor_location(ue.Vector(*position), False, False)
            capture.set_actor_rotation(ue.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]), False)
            component.set_editor_property('fov_angle', fov)
            for label, mesh in [('baseline', original), ('candidate', candidate), ('baseline-return', original)]:
                study.set_static_mesh(mesh)
                require(study.get_material(0) == ue.load_asset(PAVING), 'Rendered top material changed')
                ue.AutomationLibrary.finish_loading_before_screenshot()
                for _ in range(8):
                    component.capture_scene()
                    ue.RenderingLibrary.read_render_target_pixel(world, target, 480, 360)
                path = output / (view+'-'+label+'.png')
                require(not path.exists(), 'Capture overwrite refused')
                raw_path = output / (view+'-'+label+'.local-export.png')
                require(not raw_path.exists(), 'Staging export overwrite refused')
                ue.RenderingLibrary.export_render_target(world, target, str(output), raw_path.name)
                png_proof = sanitize_new_export(raw_path, path)
                report['captures'].append(dict(file=path.name, **png_proof, camera=position,
                    pitchYawRoll=rotation, fov=fov, mesh=mesh.get_path_name(), topMaterial=PAVING))
        report['proofAfterCaptures'] = prove(ue, original, candidate)
        require(snapshot(sorted(protected)) == protected, 'Protected source changed before save')
        if save:
            require(candidate.get_path_name().split('.')[0] == candidate_path and candidate_path.startswith(NS+'/'), 'Save outside isolated namespace refused')
            require(not disk(candidate_path).exists(), 'Existing candidate save refused')
            require(ue.EditorAssetLibrary.save_loaded_asset(candidate, only_if_is_dirty=False), 'Candidate save failed')
            report['savedCandidateSha256'] = sha(disk(candidate_path))
        report['status'] = 'captured-review-pending'
    except Exception:
        report['status'] = 'failed'
        report['error'] = traceback.format_exc()
    finally:
        errors = []
        for actor in reversed(spawned):
            try:
                require(actors.destroy_actor(actor), 'Transient cleanup failed')
            except Exception as error:
                errors.append(repr(error))
        try:
            report['protectedAfter'] = snapshot(sorted(protected))
            require(report['protectedAfter'] == protected, 'Protected maps/assets changed')
            files = sorted(p.relative_to(ROOT).as_posix() for p in disk(candidate_path).parent.rglob('*') if p.is_file())
            report['isolatedFiles'] = files
            validate_isolated_files(files, disk(candidate_path).relative_to(ROOT).as_posix(),
                                    save, verify, report['status'], 'savedCandidateSha256' in report)
        except Exception as error:
            errors.append(repr(error))
        if errors:
            report['status'] = 'failed'
            report['cleanupOrPreservationErrors'] = errors
        (output / 'native.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    require(report['status'] == 'captured-review-pending', 'Study failed; inspect '+str(output / 'native.json'))
    ue.log('HARAM_THRESHOLD_STUDY_COMPLETE '+mode+' '+run_id)


if __name__ == '__main__':
    import unreal as ue
    try:
        run()
    except Exception:
        # A clean editor exit code alone cannot signal success. The wrapper requires
        # the successful receipt AND exactly one completion marker and no errors.
        ue.log_error('HARAM_THRESHOLD_STUDY_FAILED\n' + traceback.format_exc())
        raise
    # PythonScriptCommandlet returns 0 on success and -1 for propagated Python errors.
    # Never call quit_editor in commandlet mode.

"""Owned GPU editor, Engine Entry only: transient Kotel seam A0/B/A1.

Coordinator launches -KotelClosureStudy -ExecCmds="py <absolute script>" after native-slot review.
No map/asset saves, asset imports, full-map loading, PIE, or native launch here.
The initial <2 GiB target was not met. The coordinator's external watchdog owns
the revised launch/headroom/private-memory limits; this script records counters.

First native A/B/A (20260915T162119Z-828) failed visual acceptance: A0/A1 showed
the same black gap; B showed only thin magenta strips. The mathematical +X
backdrop was culled from its camera-facing side. Convert canonical mathematical
CCW triangles to Unreal clockwise front faces at dynamic import, leaving the
canonical geometry and cavity normals unchanged. Never mask this with two-sided
materials. The coordinator will rerun; this correction is not visual acceptance.
"""
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import struct
import time
import traceback
import unreal as ue

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
V3 = '/Game/MikdashV3/KotelPlazaCutV3/SM_JerusalemTerrain_07_08_FutureMountCut_KotelPlazaCut'
DECK = '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Meshes/SM_PlazaV1_DeckTile'
POSE = (-20732.0, 19230.0, -814.0)
ROTATION = (6.0, 175.0, 0.0)
FOV = 90.0
SIZE = (1280, 720)
SEQUENCE = (('A0', False), ('B', True), ('A1', False))
EXPOSURE = {'override_auto_exposure_min_brightness': True,
            'override_auto_exposure_max_brightness': True,
            'auto_exposure_min_brightness': 1.0, 'auto_exposure_max_brightness': 1.0,
            'override_auto_exposure_bias': True, 'auto_exposure_bias': 0.0,
            'override_bloom_intensity': True, 'bloom_intensity': 0.0,
            'override_vignette_intensity': True, 'vignette_intensity': 0.0}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def production_snapshot():
    # Stream every map and native asset, including external bulk-data sidecars.
    suffixes = {'.umap', '.uasset', '.ubulk', '.uexp', '.uptnl'}
    files = sorted(p for p in (ROOT / 'Content').rglob('*') if p.is_file() and p.suffix.lower() in suffixes)
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in files}


def memory():
    class ProcessCounters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
            (n, ctypes.c_size_t) for n in ('PeakWorkingSetSize', 'WorkingSetSize',
            'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]
    class Performance(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong)] + [(n, ctypes.c_size_t) for n in (
            'CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal', 'PhysicalAvailable',
            'SystemCache', 'KernelTotal', 'KernelPaged', 'KernelNonpaged', 'PageSize')] + [
            (n, ctypes.c_ulong) for n in ('HandleCount', 'ProcessCount', 'ThreadCount')]
    current = ctypes.windll.kernel32.GetCurrentProcess
    current.restype = ctypes.c_void_p
    get_process = ctypes.windll.psapi.GetProcessMemoryInfo
    get_process.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessCounters), ctypes.c_ulong]
    counters = ProcessCounters(); counters.cb = ctypes.sizeof(counters)
    perf = Performance(); perf.cb = ctypes.sizeof(perf)
    if not get_process(current(), ctypes.byref(counters), counters.cb):
        raise RuntimeError('Process memory readback failed')
    if not ctypes.windll.psapi.GetPerformanceInfo(ctypes.byref(perf), perf.cb):
        raise RuntimeError('System commit readback failed')
    return {'workingSetBytes': counters.WorkingSetSize, 'privateBytes': counters.PrivateUsage,
            'systemCommitBytes': perf.CommitTotal * perf.PageSize,
            'systemCommitLimitBytes': perf.CommitLimit * perf.PageSize}


def vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def rotation():
    return ue.Rotator(pitch=ROTATION[0], yaw=ROTATION[1], roll=ROTATION[2])


def dirty_production():
    packages = list(ue.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    packages += list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    return sorted({p.get_name() for p in packages if p.get_name().startswith('/Game/')})


class Study:
    def __init__(self):
        self.handle = None
        self.spawned = []
        self.materials = []
        self.busy = False
        self.finished = False
        self.owned_context = False
        self.piloted = False
        self.before = None
        self.previous_camera = None
        self.previous_screen_percentage = None
        self.previous_exact_view = None
        self.started = time.monotonic()
        self.stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-%d' % os.getpid()
        self.path = HERE / ('native-study-' + self.stamp + '.json')
        if self.path.exists():
            raise RuntimeError('Unique study receipt already exists')
        self.report = {'status': 'setup_started', 'pid': os.getpid(), 'mapSaved': False,
                       'assetSaved': False, 'captures': [], 'errors': [], 'memory': [],
                       'nativeFrontFaceSideCamera': 'pending',
                       'visualAcceptance': 'pending_human_pixel_review',
                       'scriptSha256': digest(Path(__file__)), 'engineVersion': ue.SystemLibrary.get_engine_version(),
                       'memorySoftBudgetBytes': 2 * 1024**3, 'watchdogOwner': 'coordinator',
                       'initialMemorySoftBudgetMet': False,
                       'watchdogLimitsReportedByCoordinator': {
                           'launchFreeCommitGiB': 9.0, 'hardPrivateGiB': 6.5, 'minimumFreeCommitGiB': 2.0},
                       'priorVisualFailure': {
                           'receipt': 'native-study-20260915T162119Z-828.json',
                           'finding': 'A0/A1 same black gap; B only thin magenta strips; camera-facing backdrop culled',
                           'reviewer': 'coordinator',
                           'correction': 'Reverse dynamic triangle winding at import only; keep one-sided materials and cavity normals'},
                       'dynamicImports': []}
        self.write()
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        if '-kotelclosurestudy' not in ue.SystemLibrary.get_command_line().lower().split():
            raise RuntimeError('Owned launch requires explicit -KotelClosureStudy marker')
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.world = self.editor.get_editor_world()
        if not self.world or self.world.get_outermost().get_name() != '/Engine/Maps/Entry':
            raise RuntimeError('Explicitly launched Engine Entry world required; no level loading is performed')
        if self.editor.get_game_world():
            raise RuntimeError('Game/PIE world active')
        self.owned_context = True
        self.report['world'] = self.world.get_outermost().get_name()
        self.report['dirtyProductionBefore'] = dirty_production()
        if self.report['dirtyProductionBefore']:
            raise RuntimeError('Production packages already dirty')
        self.previous_camera = self.editor.get_level_viewport_camera_info()
        self.viewport = self.levels.get_active_viewport_config_key()
        if self.levels.get_pilot_level_actor(self.viewport):
            raise RuntimeError('Viewport already piloting an actor')
        self.previous_exact_view = self.levels.get_exact_camera_view(self.viewport)
        self.previous_screen_percentage = ue.SystemLibrary.get_console_variable_float_value('r.ScreenPercentage')
        self.before = production_snapshot()
        if sum(k.endswith('.umap') for k in self.before) != 20:
            raise RuntimeError('Expected the reviewed twenty project maps')
        self.report['productionBefore'] = self.before
        self.report['productionAssetCount'] = sum(k.endswith('.uasset') for k in self.before)
        self.mark('before_load')
        offline = runpy.run_path(str(HERE / 'generate_study_closure.py'))
        generated = offline['generate']()
        self.geometry = json.loads((HERE / 'closure-study.json').read_text(encoding='utf-8'))
        if generated != self.geometry or len(self.geometry['triangles']) != 841:
            raise RuntimeError('Frozen closure study differs from fresh offline generation')
        self.report['geometrySha256'] = digest(HERE / 'closure-study.json')
        self.report['geometrySources'] = self.geometry['sourceHashesSha256']
        self.plan = json.loads(offline['M']['PLAN'].read_text(encoding='utf-8-sig'))
        self.setup_scene()
        self.report['status'] = 'warming_A0'
        self.index = -1
        self.next_capture()
        self.handle = ue.register_slate_post_tick_callback(self.tick)

    def write(self):
        self.path.write_text(json.dumps(self.report, indent=2) + '\n', encoding='utf-8')

    def mark(self, phase):
        self.report['phase'] = phase
        self.report['memory'].append(dict(memory(), phase=phase, elapsedSeconds=time.monotonic()-self.started))
        self.write()
        ue.log('KOTEL_CLOSURE_STUDY: ' + phase)

    def spawn(self, cls, location=None, rot=None):
        actor = self.actors.spawn_actor_from_class(cls, location or ue.Vector(), rot or ue.Rotator(), transient=True)
        if actor is None:
            raise RuntimeError('Transient actor creation failed: ' + str(cls))
        self.spawned.append(actor)
        actor.set_actor_enable_collision(False)
        return actor

    def no_collision(self, component):
        component.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        component.set_editor_property('can_ever_affect_navigation', False)
        component.set_editor_property('generate_overlap_events', False)
        component.set_editor_property('cast_shadow', False)
        if component.get_collision_enabled() != ue.CollisionEnabled.NO_COLLISION:
            raise RuntimeError('Study component collision did not remain disabled')

    def material(self, name, rgb, instanced=False):
        # PyCore::NewObject defaults to GetTransientPackage when outer is omitted.
        mat = ue.new_object(ue.Material, name='KotelClosureStudy_' + name + '_' + self.stamp.replace('-', '_'))
        if mat.get_outermost().get_name() != '/Engine/Transient':
            raise RuntimeError('Study material escaped transient package')
        self.materials.append(mat)
        mat.set_editor_property('blend_mode', ue.BlendMode.BLEND_OPAQUE)
        mat.set_editor_property('shading_model', ue.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property('two_sided', False)
        node = ue.MaterialEditingLibrary.create_material_expression(mat, ue.MaterialExpressionConstant3Vector, 0, 0)
        node.set_editor_property('constant', ue.LinearColor(*rgb, 1.0))
        if not ue.MaterialEditingLibrary.connect_material_property(node, '', ue.MaterialProperty.MP_EMISSIVE_COLOR):
            raise RuntimeError('Transient unlit material connection failed')
        if instanced:
            ue.MaterialEditingLibrary.set_material_usage(mat, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
            ue.MaterialEditingLibrary.set_material_usage(mat, ue.MaterialUsage.MATUSAGE_NANITE)
        ue.MaterialEditingLibrary.recompile_material(mat)
        return mat

    def dynamic(self, data, material):
        actor = self.spawn(ue.DynamicMeshActor)
        component = actor.get_dynamic_mesh_component()
        self.no_collision(component)
        dynamic = component.get_dynamic_mesh()
        if dynamic.get_triangle_count() != 0:
            raise RuntimeError('New DynamicMeshActor is not empty')
        buffers = ue.GeometryScriptSimpleMeshBuffers()
        buffers.set_editor_property('vertices', [ue.Vector(*v) for v in data['vertices']])
        buffers.set_editor_property('normals', [ue.Vector(*n) for n in data['normals']])
        buffers.set_editor_property('uv0', [ue.Vector2D(*v) for v in data['uv0']])
        # Canonical arrays use mathematical CCW about the supplied cavity normal.
        # The first native A/B/A proved these fronts were culled in Unreal.
        # Convert only indices; source positions, normals, UVs and JSON stay intact.
        native_triangles = [(a, c, b) for a, b, c in data['triangles']]
        buffers.set_editor_property('triangles', [ue.IntVector(*t) for t in native_triangles])
        ue.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic, buffers)
        component.set_material(0, material)
        if dynamic.get_triangle_count() != len(data['triangles']):
            raise RuntimeError('Dynamic mesh count mismatch')
        worst = 0.0
        worst_normal = 0.0
        for i, indices in enumerate(native_triangles):
            actual = [vec(v) for v in ue.GeometryScript_MeshQueries.get_triangle_positions(dynamic, i) if isinstance(v, ue.Vector)]
            actual_normals = [vec(v) for v in ue.GeometryScript_MeshQueries.get_triangle_normals(dynamic, i) if isinstance(v, ue.Vector)]
            if len(actual) != 3 or len(actual_normals) != 3:
                raise RuntimeError('Incomplete native dynamic triangle readback')
            for a, normal, index in zip(actual, actual_normals, indices):
                worst = max(worst, max(abs(a[k]-data['vertices'][index][k]) for k in range(3)))
                worst_normal = max(worst_normal, max(abs(normal[k]-data['normals'][index][k]) for k in range(3)))
        if worst > 0.01:
            raise RuntimeError('Dynamic geometry readback differs by more than 0.01 cm')
        if worst_normal > 1e-4:
            raise RuntimeError('Supplied cavity normals changed during dynamic import')
        self.report['dynamicImports'].append({
            'actor': actor.get_path_name(), 'triangles': len(native_triangles),
            'windingConversion': 'canonical (a,b,c) -> Unreal clockwise (a,c,b)',
            'positionsNormalsUVsUnchanged': True, 'canonicalInputMutated': False,
            'maximumPositionErrorCm': worst, 'maximumNormalError': worst_normal,
            'twoSided': bool(material.get_editor_property('two_sided'))})
        return actor, component, worst

    def deck_component(self, actor):
        # Proven editor component creation used by import_instances_ue58._inst_component.
        # The owner actor here is transient. Never save the Entry package.
        sub = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
        lib = ue.SubobjectDataBlueprintFunctionLibrary
        handles = sub.k2_gather_subobject_data_for_instance(actor)
        parent = next((h for h in handles if lib.get_associated_object(lib.get_data(h)) == actor), None)
        if parent is None:
            raise RuntimeError('Transient deck actor has no editor subobject handle')
        params = ue.AddNewSubobjectParams(parent_handle=parent,
                    new_class=ue.HierarchicalInstancedStaticMeshComponent,
                    blueprint_context=None, conform_transform_to_parent=True)
        handle, reason = sub.add_new_subobject(params)
        if not lib.is_handle_valid(handle):
            raise RuntimeError('Deck HISM creation failed: ' + str(reason))
        component = lib.get_associated_object(lib.get_data(handle))
        if not isinstance(component, ue.HierarchicalInstancedStaticMeshComponent) or component.get_owner() != actor:
            raise RuntimeError('Transient deck HISM ownership mismatch')
        self.no_collision(component)
        return component

    def setup_scene(self):
        terrain_material = self.material('Terrain', (0.22, 0.14, 0.065))
        deck_material = self.material('Deck', (0.48, 0.48, 0.48), instanced=True)
        closure_material = self.material('Closure', (0.75, 0.025, 0.36))
        backdrop_material = self.material('Backdrop', (0.025, 0.18, 0.8))
        self.terrain_actor = self.spawn(ue.StaticMeshActor)
        self.terrain = self.terrain_actor.static_mesh_component
        self.no_collision(self.terrain)
        terrain_mesh = ue.EditorAssetLibrary.load_asset(V3)
        if not isinstance(terrain_mesh, ue.StaticMesh) or terrain_mesh.get_num_triangles(0) != 2714:
            raise RuntimeError('Saved V3 mesh/count mismatch')
        self.terrain.set_static_mesh(terrain_mesh)
        self.terrain.set_material(0, terrain_material)
        self.mark('v3_loaded')
        self.deck_actor = self.spawn(ue.Actor)
        self.deck = self.deck_component(self.deck_actor)
        deck_mesh = ue.EditorAssetLibrary.load_asset(DECK)
        if not isinstance(deck_mesh, ue.StaticMesh):
            raise RuntimeError('Missing reviewed deck module')
        self.deck.set_static_mesh(deck_mesh)
        self.deck.set_material(0, deck_material)
        transforms = []
        for row in self.plan['deck']:
            if any(abs(v) > 1e-9 for v in row['rot']):
                raise RuntimeError('Reviewed deck row rotation changed')
            t = ue.Transform()
            t.set_editor_property('translation', ue.Vector(*row['loc']))
            t.set_editor_property('rotation', ue.Quat(0, 0, 0, 1))
            t.set_editor_property('scale3d', ue.Vector(*row['scale']))
            transforms.append(t)
        self.deck.add_instances(transforms, False, True, False)
        if self.deck.get_instance_count() != 959:
            raise RuntimeError('Expected 959 deck instances')
        worst = 0.0
        for i, expected in enumerate(transforms):
            actual = self.deck.get_instance_transform(i, True)
            for p in (ue.Vector(), ue.Vector(100, 0, 0), ue.Vector(0, 100, 0), ue.Vector(0, 0, 100)):
                worst = max(worst, (actual.transform_location(p)-expected.transform_location(p)).length())
        if worst > 0.1:
            raise RuntimeError('Native deck transforms differ')
        self.closure_actor, self.closure, closure_error = self.dynamic(self.geometry, closure_material)
        self.closure.set_visibility(False, False)
        # Behind the western edge, never changed between A0/B/A1. Blue background
        # distinguishes an open seam without loading any other city assets.
        backdrop = {'vertices': [[-45000,-70000,-30000],[-45000,100000,-30000],
                                 [-45000,100000,50000],[-45000,-70000,50000]],
                    'normals': [[1,0,0]]*4, 'uv0': [[0,0],[1,0],[1,1],[0,1]],
                    'triangles': [[0,1,2],[0,2,3]]}
        self.backdrop_actor, self.backdrop, unused = self.dynamic(backdrop, backdrop_material)
        self.camera = self.spawn(ue.CameraActor, ue.Vector(*POSE), rotation())
        self.camera.camera_component.set_editor_property('field_of_view', FOV)
        self.camera.camera_component.set_editor_property('post_process_blend_weight', 1.0)
        pp = self.camera.camera_component.get_editor_property('post_process_settings')
        for name, value in EXPOSURE.items():
            pp.set_editor_property(name, value)
        self.camera.camera_component.set_editor_property('post_process_settings', pp)
        self.editor.set_level_viewport_camera_info(ue.Vector(*POSE), rotation())
        self.levels.pilot_level_actor(self.camera, self.viewport)
        self.piloted = True
        self.levels.set_exact_camera_view(True, self.viewport)
        ue.SystemLibrary.execute_console_command(self.world, 'r.ScreenPercentage 100')
        self.report['nativeGeometry'] = {'terrainTriangles': terrain_mesh.get_num_triangles(0),
            'deckInstances': self.deck.get_instance_count(), 'deckMaximumProbeErrorCm': worst,
            'closureTriangles': self.closure.get_dynamic_mesh().get_triangle_count(),
            'closureMaximumPositionErrorCm': closure_error,
            'terrainTransform': str(self.terrain_actor.get_actor_transform()),
            'deckTransform': str(self.deck_actor.get_actor_transform()),
            'closureTransform': str(self.closure_actor.get_actor_transform()),
            'objects': [a.get_path_name() for a in self.spawned],
            'materials': [m.get_path_name() for m in self.materials]}
        self.mark('scene_prepared')
        ue.AutomationLibrary.finish_loading_before_screenshot()

    def camera_state(self):
        position, rot = self.editor.get_level_viewport_camera_info()
        actor_position, actor_rotation = self.camera.get_actor_location(), self.camera.get_actor_rotation()
        for p, r in ((position, rot), (actor_position, actor_rotation)):
            if (p-ue.Vector(*POSE)).length() > 0.1 or abs(r.pitch-ROTATION[0]) > 0.1 or abs((r.yaw-ROTATION[1]+180)%360-180) > 0.1 or abs(r.roll) > 0.1:
                raise RuntimeError('Actual study camera differs from fixed requested pose')
        fov = self.camera.camera_component.get_editor_property('field_of_view')
        if abs(fov-FOV) > 0.01:
            raise RuntimeError('Camera FOV changed')
        post = self.camera.camera_component.get_editor_property('post_process_settings')
        read_exposure = {name: post.get_editor_property(name) for name in EXPOSURE}
        if read_exposure != EXPOSURE:
            raise RuntimeError('Fixed exposure changed')
        return {'viewportLocationCm': vec(position), 'viewportPitchYawRoll': [rot.pitch,rot.yaw,rot.roll],
                'actorLocationCm': vec(actor_position), 'actorPitchYawRoll': [actor_rotation.pitch,actor_rotation.yaw,actor_rotation.roll],
                'fieldOfView': fov, 'exposure': read_exposure, 'resolution': list(SIZE)}

    def next_capture(self):
        self.index += 1
        if self.index >= len(SEQUENCE):
            self.finish('captured_visual_review_pending')
            return
        self.label, visible = SEQUENCE[self.index]
        self.closure.set_visibility(visible, False)
        if self.closure.is_visible() != visible:
            raise RuntimeError('Closure visibility readback mismatch')
        self.phase = 'warmup'
        self.phase_started = time.monotonic()
        self.ticks = 0
        self.task = None
        self.filename = HERE / ('native-study-' + self.stamp + '-' + self.label + '.png')
        self.mark('warmup_' + self.label)

    def tick(self, delta):
        if self.busy or self.finished:
            return
        self.busy = True
        try:
            now = time.monotonic()
            if now-self.started > 420:
                raise RuntimeError('Study deadline reached')
            self.levels.editor_invalidate_viewports()
            self.ticks += 1
            warmup = 45 if self.index == 0 else 12
            if self.phase == 'warmup' and now-self.phase_started >= warmup and self.ticks >= 120:
                self.actual_camera = self.camera_state()
                self.mark('capture_' + self.label)
                self.task = ue.AutomationLibrary.take_high_res_screenshot(*SIZE, str(self.filename), camera=self.camera,
                    mask_enabled=False, capture_hdr=False, delay=0.0, force_game_view=True)
                if not self.task or not self.task.is_valid_task():
                    raise RuntimeError('Invalid native screenshot task')
                self.phase, self.phase_started = 'capture', now
            elif self.phase == 'capture' and self.task.is_task_done() and self.filename.exists():
                data = self.filename.read_bytes()
                if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != SIZE:
                    raise RuntimeError('Native screenshot is not expected PNG/resolution')
                after_camera = self.camera_state()
                if after_camera != self.actual_camera:
                    raise RuntimeError('Camera changed during native screenshot')
                self.report['captures'].append({'label': self.label, 'closureVisible': self.closure.is_visible(),
                    'file': str(self.filename), 'sha256': hashlib.sha256(data).hexdigest(),
                    'camera': after_camera, 'nativeTaskDone': True,
                    'terrainVisible': self.terrain.is_visible(), 'deckVisible': self.deck.is_visible(),
                    'backdropVisible': self.backdrop.is_visible()})
                self.write()
                self.next_capture()
            elif self.phase == 'capture' and now-self.phase_started > 90:
                raise RuntimeError('Native screenshot deadline reached')
        except Exception:
            self.report['errors'].append(traceback.format_exc())
            self.finish('failed_capture')
        finally:
            self.busy = False

    def finish(self, status):
        if self.finished:
            return
        self.finished = True
        self.report['status'] = status
        if self.handle is not None:
            ue.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        try:
            if self.piloted:
                self.levels.eject_pilot_level_actor(self.viewport)
                if self.previous_exact_view is not None:
                    self.levels.set_exact_camera_view(self.previous_exact_view, self.viewport)
            for actor in reversed(self.spawned):
                self.actors.destroy_actor(actor)
            if self.previous_camera:
                self.editor.set_level_viewport_camera_info(*self.previous_camera)
            if self.previous_screen_percentage is not None:
                ue.SystemLibrary.execute_console_command(self.world, 'r.ScreenPercentage %s' % self.previous_screen_percentage)
        except Exception:
            self.report['errors'].append(traceback.format_exc())
            self.report['status'] = 'failed_cleanup'
        try:
            self.report['dirtyProductionAfter'] = dirty_production()
            if self.before is not None:
                after = production_snapshot()
                self.report['productionAfter'] = after
                changed = [k for k in sorted(set(after) | set(self.before)) if after.get(k) != self.before.get(k)]
                self.report['changedProductionFiles'] = changed
                self.report['all20MapsUnchanged'] = not any(k.endswith('.umap') for k in changed)
                self.report['allProductionAssetsUnchanged'] = not changed
                if changed or self.report['dirtyProductionAfter']:
                    self.report['status'] = 'failed_production_preservation'
            self.mark('cleanup_complete')
        except Exception:
            self.report['errors'].append(traceback.format_exc())
            self.report['status'] = 'failed_cleanup'
        finally:
            self.report['elapsedSeconds'] = time.monotonic()-self.started
            self.report['quitRequested'] = self.owned_context
            self.write()
            ue.log('KOTEL_CLOSURE_STUDY_RECEIPT: ' + str(self.path))
            if self.owned_context:
                ue.SystemLibrary.quit_editor()


# Strong reference retained for the asynchronous Slate callback lifecycle.
STUDY = Study.__new__(Study)
try:
    STUDY.__init__()
except Exception:
    error = traceback.format_exc()
    if hasattr(STUDY, 'report'):
        STUDY.report['errors'].append(error)
        STUDY.finish('failed_setup')
    else:
        ue.log_error(error)
        if getattr(STUDY, 'owned_context', False):
            ue.SystemLibrary.quit_editor()

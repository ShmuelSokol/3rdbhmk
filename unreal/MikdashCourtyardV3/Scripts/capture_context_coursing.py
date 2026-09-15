"""Native lit before/after study in Engine Entry, never the main map.

Start a fresh editor on /Engine/Maps/Entry with -ExecCmds="py <this file>".
Before cube is screen-left, corrected cube screen-right. Both show +X/+Y walls.
Nothing is saved; the owned editor exits after three native PNG captures.
-CoursingSingle runs only the first material for a capture-helper smoke check.
"""
import hashlib
import json
from pathlib import Path
import struct
import time
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'SourceAssets/context-review/ContextCoursingV2'
STUDY = '/Game/MikdashV3/MaterialReview/ContextCoursingV2/'
NAMES = ('M_Context_Building', 'M_Context_CityWall', 'M_CityFacadeV1')


class Capture:
    def __init__(self):
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        world = self.editor.get_editor_world()
        if world.get_outermost().get_name() != '/Engine/Maps/Entry':
            raise RuntimeError('Only an explicitly launched Engine Entry world is allowed')
        self.maps = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'Content').rglob('*.umap')}
        self.report = {'status': 'started', 'before': 'left cube', 'after': 'right cube', 'captures': [],
                       'world': world.get_outermost().get_name(), 'mapSaved': False}
        self.limit = 1 if '-coursingsingle' in ue.SystemLibrary.get_command_line().lower() else len(NAMES)
        self.report['expectedCaptures'] = self.limit
        self.path = FOLDER / ('capture-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '.json')
        self.spawned = []
        self.handle = None
        self.busy = False
        self.index = -1
        self.started = time.monotonic()
        self.write()
        cube = ue.EditorAssetLibrary.load_asset('/Engine/BasicShapes/Cube')
        self.cubes = []
        for x, y in ((-270, 270), (270, -270)):
            actor = self.spawn(ue.StaticMeshActor, ue.Vector(x, y, 200))
            comp = actor.static_mesh_component
            comp.set_static_mesh(cube)
            actor.set_actor_scale3d(ue.Vector(4, 4, 4))
            self.cubes.append(comp)
        light = self.spawn(ue.DirectionalLight, ue.Vector(0, 0, 1000), ue.Rotator(pitch=-40, yaw=225, roll=0))
        light.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        light.light_component.set_editor_property('intensity', 5.0)
        pp = self.spawn(ue.PostProcessVolume, ue.Vector(0, 0, 0))
        pp.set_editor_property('unbound', True)
        settings = pp.get_editor_property('settings')
        for name, value in {'override_auto_exposure_min_brightness': True, 'override_auto_exposure_max_brightness': True,
                            'auto_exposure_min_brightness': 1.0, 'auto_exposure_max_brightness': 1.0,
                            'override_auto_exposure_bias': True, 'auto_exposure_bias': 0.0,
                            'override_bloom_intensity': True, 'bloom_intensity': 0.0,
                            'override_vignette_intensity': True, 'vignette_intensity': 0.0}.items():
            settings.set_editor_property(name, value)
        pp.set_editor_property('settings', settings)
        self.editor.set_level_viewport_camera_info(ue.Vector(1150, 1150, 760), ue.Rotator(pitch=-19, yaw=225, roll=0))
        self.camera = self.spawn(ue.CameraActor, ue.Vector(1150, 1150, 760), ue.Rotator(pitch=-19, yaw=225, roll=0))
        self.camera.camera_component.set_editor_property('field_of_view', 70.0)
        ue.SystemLibrary.execute_console_command(world, 'r.ScreenPercentage 100')
        self.next()
        self.handle = ue.register_slate_post_tick_callback(self.tick)

    def spawn(self, cls, location, rotation=None):
        actor = self.actors.spawn_actor_from_class(cls, location, rotation or ue.Rotator(), transient=True)
        if actor is None:
            raise RuntimeError('Study actor spawn failed')
        self.spawned.append(actor)
        return actor

    def write(self):
        self.path.write_text(json.dumps(self.report, indent=2) + '\n', encoding='utf-8')

    def next(self):
        self.index += 1
        if self.index == self.limit:
            self.finish('captured_visual_review_pending')
            return
        for comp, suffix in zip(self.cubes, ('Before', 'After')):
            material = ue.EditorAssetLibrary.load_asset(STUDY + NAMES[self.index] + '_' + suffix)
            if material is None:
                raise RuntimeError('Missing study material')
            comp.set_material(0, material)
        ue.AutomationLibrary.finish_loading_before_screenshot()
        self.phase = 'warmup'
        self.phase_started = time.monotonic()
        self.ticks = 0
        self.task = None
        self.filename = FOLDER / (self.path.stem + '-' + NAMES[self.index] + '.png')

    def tick(self, delta):
        if self.busy:
            return
        self.busy = True
        try:
            now = time.monotonic()
            if now - self.started > 420:
                raise RuntimeError('Study deadline reached')
            self.levels.editor_invalidate_viewports()
            self.ticks += 1
            if self.phase == 'warmup':
                viewport = self.levels.get_active_viewport_config_key()
                self.levels.set_level_viewport_camera_info(ue.Vector(1150, 1150, 760),
                    ue.Rotator(pitch=-19, yaw=225, roll=0), viewport)
            if self.phase == 'warmup' and now - self.phase_started >= 45 and self.ticks >= 120:
                position, rotation = self.editor.get_level_viewport_camera_info()
                if (position - ue.Vector(1150, 1150, 760)).length() > 0.1 or abs(rotation.pitch + 19) > 0.1 or abs((rotation.yaw - 225 + 180) % 360 - 180) > 0.1 or abs(rotation.roll) > 0.1:
                    raise RuntimeError('Review camera differs from requested pose')
                self.report['cameraAtCapture'] = {'position': [position.x, position.y, position.z], 'pitchYawRoll': [rotation.pitch, rotation.yaw, rotation.roll]}
                self.write()
                self.task = ue.AutomationLibrary.take_high_res_screenshot(1280, 720, str(self.filename), camera=self.camera,
                    mask_enabled=False, capture_hdr=False, delay=0.0, force_game_view=True)
                if not self.task or not self.task.is_valid_task():
                    raise RuntimeError('Screenshot task invalid')
                self.phase = 'capture'
                self.phase_started = time.monotonic()
            elif self.phase == 'capture' and self.task.is_task_done() and self.filename.exists():
                data = self.filename.read_bytes()
                if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != (1280, 720):
                    raise RuntimeError('Invalid PNG')
                self.report['captures'].append({'material': NAMES[self.index], 'file': str(self.filename),
                                                'sha256': hashlib.sha256(data).hexdigest(), 'nativeTaskDone': True})
                self.write()
                self.next()
            elif self.phase == 'capture' and now - self.phase_started > 90:
                raise RuntimeError('Screenshot timed out')
        except Exception as error:
            self.report['error'] = repr(error)
            self.finish('failed')
        finally:
            self.busy = False

    def finish(self, status):
        if self.handle is not None:
            ue.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        for actor in reversed(self.spawned):
            self.actors.destroy_actor(actor)
        self.report['mapsUnchanged'] = self.maps == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'Content').rglob('*.umap')}
        self.report['status'] = status if self.report['mapsUnchanged'] else 'failed_maps_changed'
        self.write()
        ue.SystemLibrary.quit_editor()


CAPTURE = Capture.__new__(Capture)
try:
    CAPTURE.__init__()
except Exception as error:
    if hasattr(CAPTURE, 'report'):
        CAPTURE.report.update(status='failed_setup', error=repr(error))
        CAPTURE.write()
    ue.log_error('Context coursing capture setup failed')
    ue.SystemLibrary.quit_editor()
    raise

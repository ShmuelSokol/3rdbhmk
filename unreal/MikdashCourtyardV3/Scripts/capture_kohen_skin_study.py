"""Native isolated Kohen skin A/B in Engine Entry; transient actors only, no saves."""
import hashlib
import json
from pathlib import Path
import struct
import time
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'SourceAssets/characters-review/KohenSkinV2'
NAMES = ('baseline', 'skin-study')


class Capture:
    def __init__(self):
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        world = self.editor.get_editor_world()
        if world.get_outermost().get_name() != '/Engine/Maps/Entry':
            raise RuntimeError('Only an explicitly launched Engine Entry world is allowed')
        self.maps = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'Content').rglob('*.umap')}
        self.report = {'status': 'started', 'before': 'baseline frame', 'after': 'skin-study frame', 'captures': [],
                       'world': world.get_outermost().get_name(), 'mapSaved': False}
        self.limit = len(NAMES)
        self.report['expectedCaptures'] = self.limit
        self.path = FOLDER / ('capture-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '.json')
        self.spawned = []
        self.handle = None
        self.busy = False
        self.index = -1
        self.started = time.monotonic()
        self.write()
        mesh = ue.load_asset('/Game/MikdashV3/Characters/KohenGadolV1/Mesh/SK_KohenGadol_V1')
        self.skin = ue.load_asset('/Game/Characters/KohenSkinV2Study03/M_KohenWalter_Skin_V2')
        if not mesh or not self.skin:
            raise RuntimeError('Missing approved head or skin study')
        actor = self.spawn(ue.SkeletalMeshActor, ue.Vector(0, 0, 0))
        self.body = actor.skeletal_mesh_component
        self.body.set_skeletal_mesh_asset(mesh)
        slots = list(self.body.get_material_slot_names())
        self.report['slots'] = [str(s) for s in slots]
        self.head_slot = next(i for i, s in enumerate(slots) if str(s) == 'KG_MHHead')
        self.original = self.body.get_material(self.head_slot)
        self.report['originalMaterial'] = self.original.get_path_name()
        self.report['candidateMaterial'] = self.skin.get_path_name()
        light = self.spawn(ue.DirectionalLight, ue.Vector(0, 0, 1000), ue.Rotator(pitch=-40, yaw=180, roll=0))
        light.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        light.light_component.set_editor_property('intensity', 3.0)
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
        self.editor.set_level_viewport_camera_info(ue.Vector(135, 0, 155), ue.Rotator(pitch=0, yaw=180, roll=0))
        self.camera = self.spawn(ue.CameraActor, ue.Vector(135, 0, 155), ue.Rotator(pitch=0, yaw=180, roll=0))
        self.camera.camera_component.set_editor_property('field_of_view', 35.0)
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
        self.body.set_material(self.head_slot, self.original if self.index == 0 else self.skin)
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
                self.levels.set_level_viewport_camera_info(ue.Vector(135, 0, 155),
                    ue.Rotator(pitch=0, yaw=180, roll=0), viewport)
            if self.phase == 'warmup' and now - self.phase_started >= 30 and self.ticks >= 120:
                position, rotation = self.editor.get_level_viewport_camera_info()
                if (position - ue.Vector(135, 0, 155)).length() > 0.1 or abs(rotation.pitch) > 0.1 or abs((rotation.yaw - 180 + 180) % 360 - 180) > 0.1 or abs(rotation.roll) > 0.1:
                    raise RuntimeError('Review camera differs from requested pose')
                self.report['cameraAtCapture'] = {'position': [position.x, position.y, position.z], 'pitchYawRoll': [rotation.pitch, rotation.yaw, rotation.roll]}
                self.write()
                self.task = ue.AutomationLibrary.take_high_res_screenshot(960, 720, str(self.filename), camera=self.camera,
                    mask_enabled=False, capture_hdr=False, delay=0.0, force_game_view=True)
                if not self.task or not self.task.is_valid_task():
                    raise RuntimeError('Screenshot task invalid')
                self.phase = 'capture'
                self.phase_started = time.monotonic()
            elif self.phase == 'capture' and self.task.is_task_done() and self.filename.exists():
                data = self.filename.read_bytes()
                if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != (960, 720):
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
    ue.log_error('Kohen skin capture setup failed')
    ue.SystemLibrary.quit_editor()
    raise

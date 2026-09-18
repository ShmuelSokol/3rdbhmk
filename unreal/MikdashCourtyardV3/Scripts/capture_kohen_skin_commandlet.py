"""Asset-only native GPU A/B using a render target, without the editor viewport."""
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/KohenSkinV2'


def run():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt = OUT / ('render-target-' + stamp + '.json')
    maps = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'Content').rglob('*.umap')}
    report = {'status': 'started', 'scope': 'Native isolated render-target A/B; not in-scene acceptance', 'captures': []}
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    spawned = []

    def spawn(cls, position, rotation=ue.Rotator()):
        actor = actors.spawn_actor_from_class(cls, position, rotation, transient=True)
        if actor is None:
            raise RuntimeError('Actor spawn failed')
        spawned.append(actor)
        return actor

    try:
        mesh = ue.load_asset('/Game/MikdashV3/Characters/KohenGadolV1/Mesh/SK_KohenGadol_V1')
        skin = ue.load_asset('/Game/Characters/KohenSkinV2Study03/M_KohenWalter_Skin_V2')
        if not mesh or not skin:
            raise RuntimeError('Missing approved mesh or study material')
        ue.AutomationLibrary.finish_loading_before_screenshot()
        world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        if world.get_outermost().get_name().startswith('/Game/'):
            raise RuntimeError('Refusing production map')
        report['world'] = world.get_outermost().get_name()
        body = spawn(ue.SkeletalMeshActor, ue.Vector()).skeletal_mesh_component
        body.set_skeletal_mesh_asset(mesh)
        slot = next(i for i, name in enumerate(body.get_material_slot_names()) if str(name) == 'KG_MHHead')
        baseline = body.get_material(slot)
        light = spawn(ue.DirectionalLight, ue.Vector(0, 0, 1000), ue.Rotator(pitch=-35, yaw=-115.0169, roll=0))
        light.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        light.light_component.set_editor_property('intensity', 3.0)
        capture = spawn(ue.SceneCapture2D, ue.Vector(70, 150, 162), ue.Rotator(pitch=0, yaw=-115.0169, roll=0))
        report['camera'] = {'positionCm': [70, 150, 162], 'pitchYawRoll': [0, -115.0169, 0], 'fovDegrees': 35}
        component = capture.get_component_by_class(ue.SceneCaptureComponent2D)
        if component is None:
            raise RuntimeError('Scene capture component missing')
        component.set_editor_property('capture_every_frame', False)
        component.set_editor_property('capture_on_movement', False)
        component.set_editor_property('fov_angle', 35.0)
        component.set_editor_property('capture_source', ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        target = ue.RenderingLibrary.create_render_target2d(world, 960, 720, ue.TextureRenderTargetFormat.RTF_RGBA8)
        component.set_editor_property('texture_target', target)
        settings = component.get_editor_property('post_process_settings')
        for prop, value in {'override_auto_exposure_min_brightness': True, 'override_auto_exposure_max_brightness': True,
                            'auto_exposure_min_brightness': 1.0, 'auto_exposure_max_brightness': 1.0,
                            'override_auto_exposure_bias': True, 'auto_exposure_bias': 0.0,
                            'override_bloom_intensity': True, 'bloom_intensity': 0.0}.items():
            settings.set_editor_property(prop, value)
        component.set_editor_property('post_process_settings', settings)
        linear_study = body.create_dynamic_material_instance(slot, skin)
        if linear_study is None:
            raise RuntimeError('Transient linear-color study failed')
        linear_study.set_scalar_parameter_value('VCDecodeExponent', 1.0)
        for label, material in (('baseline', baseline), ('skin-study', skin), ('skin-linear', linear_study),
                                ('skin-linear-no-beard', linear_study)):
            body.set_material(slot, material)
            hidden = []
            if label == 'skin-linear-no-beard':
                hair_slot = next(i for i, name in enumerate(body.get_material_slot_names()) if str(name) == 'KG_Hair')
                subsystem = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem)
                for section in range(subsystem.get_num_sections(mesh, 0)):
                    if subsystem.get_lod_material_slot(mesh, 0, section) == hair_slot:
                        body.show_material_section(hair_slot, section, False, 0)
                        hidden.append(section)
                if not hidden:
                    raise RuntimeError('No hair sections found for isolation')
            ue.AutomationLibrary.finish_loading_before_screenshot()
            path = OUT / ('render-target-' + stamp + '-' + label + '.png')
            if path.exists():
                raise RuntimeError('Fresh output required')
            for _ in range(8):
                component.capture_scene()
                ue.RenderingLibrary.read_render_target_pixel(world, target, 480, 360)
            ue.RenderingLibrary.export_render_target(world, target, str(OUT), path.name)
            data = path.read_bytes()
            if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != (960, 720):
                raise RuntimeError('Invalid render target export')
            report['captures'].append({'file': path.name, 'material': material.get_path_name(),
                                       'hiddenHairSectionsLod0': hidden,
                                       'sha256': hashlib.sha256(data).hexdigest()})
        report['status'] = 'captured_visual_review_pending'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        for actor in reversed(spawned):
            actors.destroy_actor(actor)
        report['mapsUnchanged'] = maps == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'Content').rglob('*.umap')}
        if not report['mapsUnchanged']:
            report['status'] = 'failed_maps_changed'
        receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    run()

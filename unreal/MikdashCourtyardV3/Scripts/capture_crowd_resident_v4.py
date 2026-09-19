"""Read-only reference-pose review of the six existing ResidentV4 figures."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/perf-review/crowd-vat/NearResidentV4'
LINEAR = '-RV4LinearColor' in ue.SystemLibrary.get_command_line()


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = OUT / ('render-' + stamp + '.json')
    report = dict(status='running', scope='Existing ResidentV4 full-body and face reference poses; no animation or crowd adoption.', linearColorStudy=LINEAR, captures=[])
    protected = list((ROOT/'Content').rglob('*.umap'))
    for name in ('CrowdVATV1', 'CrowdNearV1'):
        protected += list((ROOT/'Content/MikdashV3/Runtime'/name).rglob('*.uasset'))
    protected += list((ROOT/'Content/MikdashV3/Characters/ResidentV4').rglob('*.uasset'))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    before = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    spawned = []
    def spawn(cls, pos, rot=ue.Rotator()):
        actor = actors.spawn_actor_from_class(cls, pos, rot, transient=True)
        assert actor
        spawned.append(actor)
        return actor
    try:
        world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        assert not world.get_outermost().get_name().startswith('/Game/'), 'Production map refused'
        report['world'] = world.get_outermost().get_name()
        body = spawn(ue.SkeletalMeshActor, ue.Vector()).skeletal_mesh_component
        body.set_mobility(ue.ComponentMobility.MOVABLE)
        lights = []
        for intensity, yaw in ((3., -115.), (1., -45.)):
            light = spawn(ue.DirectionalLight, ue.Vector(0,0,1000), ue.Rotator(pitch=-25,yaw=yaw))
            light.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
            light.light_component.set_editor_property('intensity', intensity)
            lights.append((light,yaw))
        camera = spawn(ue.SceneCapture2D, ue.Vector(80,240,105), ue.Rotator(yaw=-108.435))
        component = camera.get_component_by_class(ue.SceneCaptureComponent2D)
        for key,value in dict(capture_every_frame=False,capture_on_movement=False,fov_angle=45.,
                              capture_source=ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR).items():
            component.set_editor_property(key,value)
        target = ue.RenderingLibrary.create_render_target2d(world,960,960,ue.TextureRenderTargetFormat.RTF_RGBA8)
        component.set_editor_property('texture_target',target)
        settings = component.get_editor_property('post_process_settings')
        for key,value in dict(override_auto_exposure_min_brightness=True,override_auto_exposure_max_brightness=True,
                              auto_exposure_min_brightness=1.,auto_exposure_max_brightness=1.,
                              override_auto_exposure_bias=True,auto_exposure_bias=0.,
                              override_bloom_intensity=True,bloom_intensity=0.).items():
            settings.set_editor_property(key,value)
        component.set_editor_property('post_process_settings',settings)
        report['camera'] = dict(position=[80,240,105],pitchYawRoll=[0,-108.435,0],fov=45,resolution=[960,960])
        marker=json.loads((ROOT/'SourceAssets/characters-review/ResidentV4/resident-v4-import-marker.json').read_text())
        report['meshes']=marker['meshes']
        for variant,path,view in [(variant,path,view) for variant,path in marker['meshes'].items() for view in ('body','face')]:
            label=variant.removeprefix('V3_Pilgrim_')+'-'+view
            mesh=ue.load_asset(path)
            assert mesh
            body.set_skeletal_mesh_asset(mesh)
            # Reset overrides to each source mesh's own material set.
            bindings=[]
            for i,slot in enumerate(mesh.get_editor_property('materials')):
                body.set_material(i,slot.get_editor_property('material_interface'))
                source=slot.get_editor_property('material_interface')
                bindings.append(dict(slot=i,material=source.get_path_name(),
                                     parameterNames=[str(n) for n in ue.MaterialEditingLibrary.get_scalar_parameter_names(source)]))
                if LINEAR:
                    dynamic = body.create_dynamic_material_instance(i, slot.get_editor_property('material_interface'))
                    assert dynamic
                    dynamic.set_scalar_parameter_value('VCDecodeExponent', 1.0)
            position=ue.Vector(80,240,105) if view=='body' else ue.Vector(24,72,165)
            yaw=-108.435
            camera.set_actor_location(position,False,False)
            camera.set_actor_rotation(ue.Rotator(yaw=yaw),False)
            ue.AutomationLibrary.finish_loading_before_screenshot()
            image = OUT/('render-'+stamp+'-'+label+'.png')
            assert not image.exists()
            for _ in range(8):
                component.capture_scene()
                ue.RenderingLibrary.read_render_target_pixel(world,target,480,480)
            ue.RenderingLibrary.export_render_target(world,target,str(OUT),image.name)
            data=image.read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24]) == (960,960)
            report['captures'].append(dict(label=label,mesh=path,triangles=None,file=image.name,sha256=sha(image),
                                           cameraPosition=[position.x,position.y,position.z],cameraYaw=yaw,
                                           lightYawOffset=yaw+108.435,bindings=bindings))
        report['status']='captured-review-pending'
    except Exception as error:
        report.update(status='failed',error=repr(error))
        raise
    finally:
        for actor in reversed(spawned): actors.destroy_actor(actor)
        report['protectedUnchanged'] = before == {str(p.relative_to(ROOT)):sha(p) for p in protected}
        if not report['protectedUnchanged']: report['status']='failed-protected-changed'
        output.write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__': run()

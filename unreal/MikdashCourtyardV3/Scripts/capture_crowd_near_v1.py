"""Transient native GPU comparison at walk frame zero; no map/asset saves."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/perf-review/crowd-vat/NearV1'


def run():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = OUT / ('render-' + stamp + '.json')
    report = dict(status='running', scope='Static VAT walk-frame-zero A/B plus skeletal reference pose; skeleton is not pose-matched. No animated/in-scene acceptance.', captures=[])
    protected = list((ROOT/'Content').rglob('*.umap'))
    for name in ('CrowdVATV1', 'CrowdNearV1'):
        protected += list((ROOT/'Content/MikdashV3/Runtime'/name).rglob('*.uasset'))
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
        body = spawn(ue.StaticMeshActor, ue.Vector()).static_mesh_component
        body.set_mobility(ue.ComponentMobility.MOVABLE)
        for intensity, yaw in ((3., -115.), (1., -45.)):
            light = spawn(ue.DirectionalLight, ue.Vector(0,0,1000), ue.Rotator(pitch=-25,yaw=yaw))
            light.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
            light.light_component.set_editor_property('intensity', intensity)
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
        source='/Game/MikdashV3/Characters/PilgrimRigV3/V3_Pilgrim_Man_Standard/'
        for label, path in [('distant-proxy','/Game/MikdashV3/Runtime/CrowdVATV1/Meshes/SM_CrowdVAT_Man_Standard'),
                            ('full-source','/Game/MikdashV3/Runtime/CrowdNearV1/Meshes/SM_CrowdNear_Man_Standard'),
                            ('skeletal-reference',source+'V3_Pilgrim_Man_Standard/SkeletalMeshes/V3_Pilgrim_Man_Standard')]:
            mesh = ue.load_asset(path)
            assert mesh
            if label == 'skeletal-reference':
                body.set_visibility(False)
                rig=spawn(ue.SkeletalMeshActor,ue.Vector()).skeletal_mesh_component
                rig.set_skeletal_mesh_asset(mesh)
                # SetPosition alone changes single-node time but does not evaluate
                # bones inside this commandlet. Keep this explicitly reference pose.
            else:
                assert body.set_static_mesh(mesh)
            ue.AutomationLibrary.finish_loading_before_screenshot()
            image = OUT/('render-'+stamp+'-'+label+'.png')
            assert not image.exists()
            for _ in range(8):
                component.capture_scene()
                ue.RenderingLibrary.read_render_target_pixel(world,target,480,480)
            ue.RenderingLibrary.export_render_target(world,target,str(OUT),image.name)
            data=image.read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24]) == (960,960)
            report['captures'].append(dict(label=label,mesh=path,triangles=mesh.get_num_triangles(0) if label != 'skeletal-reference' else None,file=image.name,sha256=sha(image)))
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

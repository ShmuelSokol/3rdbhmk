"""Transient native GPU shoulder reference-pose comparison; no asset/map saves."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/ResidentShoulderStudy05'


def run():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = OUT / ('render-' + stamp + '.json')
    report = dict(status='running', scope='Source/candidate skeletal reference-pose A/B with identical baseline materials; not animated/in-scene acceptance.', captures=[])
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
        source = OUT / 'SK_RV4_Youth_ShoulderStudy.glb'
        review = json.loads((OUT/'review.json').read_text())
        assert sha(source) == review['candidateSha256']
        baseline = ue.load_asset('/Game/MikdashV3/Characters/ResidentV4/Youth/SK_RV4_Youth')
        assert baseline
        folder = '/Game/Characters/ResidentShoulderStudy_' + stamp
        assert not ue.EditorAssetLibrary.does_directory_exist(folder)
        task = ue.AssetImportTask()
        for key, value in dict(filename=str(source), destination_path=folder, automated=True,
                               replace_existing=False, save=False).items():
            task.set_editor_property(key,value)
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        meshes = [o for o in task.get_objects() if isinstance(o,ue.SkeletalMesh)]
        assert len(meshes) == 1
        candidate = meshes[0]
        body.set_skeletal_mesh_asset(baseline)
        bindings = {str(n):body.get_material(i) for i,n in enumerate(body.get_material_slot_names())}
        report['candidateSourceSha256'] = sha(source)
        report['candidatePackage'] = candidate.get_path_name()
        views = [('front', ue.Vector(80,240,105), -108.435),
                 ('side', ue.Vector(260,0,105), 180.),
                 ('back', ue.Vector(-80,-240,105), 71.565)]
        for label, mesh, position, yaw in [(name+'-'+side, mesh, position, yaw)
                                          for name, position, yaw in views
                                          for side, mesh in [('before',baseline),('after',candidate)]]:
            path = mesh.get_path_name()
            camera.set_actor_location(position,False,False)
            camera.set_actor_rotation(ue.Rotator(yaw=yaw),False)
            for light, original_yaw in lights:
                light.set_actor_rotation(ue.Rotator(pitch=-25,yaw=original_yaw+yaw+108.435),False)
            body.set_skeletal_mesh_asset(mesh)
            slots = [str(n) for n in body.get_material_slot_names()]
            assert set(slots) == set(bindings)
            for i,n in enumerate(slots): body.set_material(i,bindings[n])
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
                                           lightYawOffset=yaw+108.435))
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

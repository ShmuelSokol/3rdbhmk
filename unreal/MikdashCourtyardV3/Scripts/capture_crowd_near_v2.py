"""Instanced VAT before/after at four frozen walk phases; no asset/map saves."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/perf-review/crowd-vat/NearV2'


def run():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = OUT / ('render-' + stamp + '.json')
    report = dict(status='running', scope='Four frozen instanced VAT walk phases with native source/candidate bone-pose comparison. Not real-time movie or in-scene acceptance.', captures=[])
    protected = list((ROOT/'Content').rglob('*.umap'))
    for name in ('CrowdVATV1', 'CrowdNearV1', 'CrowdNearV2b'):
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
        owner = spawn(ue.MikdashCrowdField,ue.Vector())
        components = owner.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent)
        assert components and all(c.get_instance_count()==0 for c in components)
        body = next(c for c in components if c.get_name()=='CrowdPose0')
        body.set_num_custom_data_floats(11)
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
        builds=[json.loads(p.read_text()) for p in OUT.glob('native-*.json')]
        built=next(r for r in builds if r.get('status')=='built-needs-fresh-readback-and-render')
        new_skel=ue.load_asset(built['sourceImport']['skeletalMesh'])
        old_skel=ue.load_asset('/Game/MikdashV3/Characters/PilgrimRigV3/V3_Pilgrim_Man_Standard/V3_Pilgrim_Man_Standard/SkeletalMeshes/V3_Pilgrim_Man_Standard')
        old_clip=ue.load_asset('/Game/MikdashV3/Characters/PilgrimRigV3/V3_Pilgrim_Man_Standard/WalkV2/V3_Pilgrim_Man_StandardA_Pilgrim_Original_Walk')
        new_clip=ue.load_asset(built['sourceImport']['walk'])
        assert old_clip and new_clip and old_skel and new_skel
        poses=[]
        for frame in (0,18,36,54):
            pair=[]
            for clip,skel in ((old_clip,old_skel),(new_clip,new_skel)):
                options=ue.AnimPoseEvaluationOptions()
                options.set_editor_property('optional_skeletal_mesh',skel)
                pose=ue.AnimPoseExtensions.get_anim_pose_at_time(clip,frame/60.,options)
                assert ue.AnimPoseExtensions.is_valid(pose)
                bones=ue.AnimPoseExtensions.get_bone_names(pose)
                transforms={}
                for bone in bones:
                    tr=ue.AnimPoseExtensions.get_bone_pose(pose,bone,ue.AnimPoseSpaces.WORLD)
                    v,q,sc=tr.translation,tr.rotation,tr.scale3d
                    transforms[str(bone)]=[v.x,v.y,v.z,q.x,q.y,q.z,q.w,sc.x,sc.y,sc.z]
                pair.append(transforms)
            assert set(pair[0])==set(pair[1]) and len(pair[0])>=27
            max_error=max(abs(a-b) for name in pair[0] for a,b in zip(pair[0][name],pair[1][name]))
            poses.append(dict(frame=frame,time=frame/60.,bones=len(pair[0]),maxComponentError=max_error,before=pair[0],after=pair[1]))
            assert max_error<.001
        report['nativePoseComparison']=poses
        meshes=[('before','/Game/MikdashV3/Runtime/CrowdNearV1/Meshes/SM_CrowdNear_Man_Standard'),
                ('after',built['variant']['mesh'])]
        custom=[0.,.5,0.,0.,0.,0.,0.,0.,-1000.,.5,0.]
        instance_created=False
        for frame,label,path in [(frame,label,path) for frame in (0,18,36,54) for label,path in meshes]:
            label='frame%02d-'%frame+label
            mesh=ue.load_asset(path)
            assert mesh and body.set_static_mesh(mesh)
            if not instance_created:
                assert body.add_instance(ue.Transform())==0
                instance_created=True
            custom[0]=frame/72.
            for idx,value in enumerate(custom):
                assert body.set_custom_data_value(0,idx,value,True)
            readback=list(body.get_editor_property('per_instance_sm_custom_data'))
            assert len(readback)==11 and all(abs(a-b)<1e-6 for a,b in zip(readback,custom))
            ue.AutomationLibrary.finish_loading_before_screenshot()
            image = OUT/('render-'+stamp+'-'+label+'.png')
            assert not image.exists()
            for _ in range(8):
                component.capture_scene()
                ue.RenderingLibrary.read_render_target_pixel(world,target,480,480)
            ue.RenderingLibrary.export_render_target(world,target,str(OUT),image.name)
            data=image.read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24]) == (960,960)
            report['captures'].append(dict(label=label,mesh=path,triangles=mesh.get_num_triangles(0),frame=frame,customData=readback,file=image.name,sha256=sha(image)))
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

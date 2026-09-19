"""Resident crowd candidates versus saved skeletal source at selectable frozen walk phases; no saves."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import re
import math
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
match = re.search(r'-ResidentCrowdStudy=(01|02|03|04|05|06|07|08|09|10)\b', ue.SystemLibrary.get_command_line())
STUDY = match.group(1) if match else '03'
OUT = ROOT / ('SourceAssets/perf-review/crowd-vat/ResidentStudy'+STUDY)
variant_match=re.search(r'-ResidentCrowdVariant=(\w+)',ue.SystemLibrary.get_command_line())
VARIANT=variant_match.group(1) if variant_match else 'Man_Standard'
assert VARIANT in ('Man_Standard','Man_Heavy','Man_Elder','Woman_Young','Woman_Elder','Youth')
if VARIANT!='Man_Standard':OUT=OUT/'Cast'/VARIANT
distance_match=re.search(r'-ResidentCrowdDistanceCm=(\d+(?:\.\d+)?)\b',ue.SystemLibrary.get_command_line())
DISTANCE=float(distance_match.group(1)) if distance_match else math.hypot(80,240)
assert math.isfinite(DISTANCE) and 100<=DISTANCE<=10000
view_match=re.search(r'-ResidentCrowdView=(\w+)',ue.SystemLibrary.get_command_line())
VIEW=view_match.group(1) if view_match else 'Front'
assert VIEW in ('Front','Right','Rear','Left')
SWEEP=bool(re.search(r'-ResidentCrowdSweep\b',ue.SystemLibrary.get_command_line()))
SHADOW_PARITY=bool(re.search(r'-ResidentCrowdShadowParity\b',ue.SystemLibrary.get_command_line()))
NO_NORMAL_DETAIL=bool(re.search(r'-ResidentCrowdNoNormalDetail\b',ue.SystemLibrary.get_command_line()))
NORMAL_CORRECTION=bool(re.search(r'-ResidentCrowdNormalCorrection\b',ue.SystemLibrary.get_command_line()))
FRAMES=tuple(range(0,72,6)) if SWEEP else (0,18,36,54)
assert not NORMAL_CORRECTION or (STUDY=='10' and not SWEEP and VARIANT in ('Man_Elder','Woman_Young'))



def run():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = OUT / ('render-' + stamp + '.json')
    report = dict(status='running', scope='Frozen instanced VAT walk phases against the saved skeletal source. Not continuous clearance, real-time movie or in-scene acceptance.', view=VIEW, frames=list(FRAMES), noNormalDetail=NO_NORMAL_DETAIL, materials={}, captures=[])
    protected = list((ROOT/'Content').rglob('*.umap'))
    for name in ('CrowdVATV1', 'CrowdNearV1', 'CrowdResidentStudy'+STUDY):
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
        owner = spawn(ue.MikdashCrowdField,ue.Vector())
        components = owner.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent)
        assert components and all(c.get_instance_count()==0 for c in components)
        body = next(c for c in components if c.get_name()=='CrowdPose0')
        body.set_num_custom_data_floats(11)
        body.set_mobility(ue.ComponentMobility.MOVABLE)
        scale=DISTANCE/math.hypot(80,240)
        camera_position,camera_yaw={
            'Front':([80*scale,240*scale,105],-108.435),
            'Right':([DISTANCE,0,105],180.),
            'Rear':([0,-DISTANCE,105],90.),
            'Left':([-DISTANCE,0,105],0.)}[VIEW]
        light_rotation=camera_yaw+108.435
        report['lightYawOffset']=light_rotation
        for intensity, yaw in ((3., -115.+light_rotation), (1., -45.+light_rotation)):
            light = spawn(ue.DirectionalLight, ue.Vector(0,0,1000), ue.Rotator(pitch=-25,yaw=yaw))
            light.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
            light.light_component.set_editor_property('intensity', intensity)
        camera = spawn(ue.SceneCapture2D, ue.Vector(*camera_position), ue.Rotator(yaw=camera_yaw))
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
        report['camera'] = dict(position=camera_position,distanceCm=DISTANCE,pitchYawRoll=[0,camera_yaw,0],fov=45,resolution=[960,960])
        builds=[json.loads(p.read_text()) for p in OUT.glob('native-*.json')]
        built=next(r for r in builds if r.get('status')=='built-needs-fresh-readback-and-render')
        correction_texture=None
        if NORMAL_CORRECTION:
            correction_path=next(OUT.glob('posed-correction-*.json'))
            correction=json.loads(correction_path.read_text())['correction']
            assert correction['frames']==list(FRAMES)
            png=OUT/correction['file'];assert sha(png)==correction['sha256']
            destination='/Game/MikdashV3/Runtime/ResidentNormalTransient_'+stamp
            assert not ue.EditorAssetLibrary.does_directory_exist(destination)
            task=ue.AssetImportTask()
            for key,value in dict(filename=str(png),destination_path=destination,destination_name='T_NormalDiagnostic',automated=True,replace_existing=False,save=False).items():task.set_editor_property(key,value)
            ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            imported=[o for o in task.get_objects() if isinstance(o,ue.Texture2D)]
            assert len(imported)==1
            correction_texture=imported[0]
            for key,value in dict(srgb=False,compression_settings=ue.TextureCompressionSettings.TC_HDR,
                                  filter=ue.TextureFilter.TF_NEAREST,mip_gen_settings=ue.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                                  never_stream=True,address_x=ue.TextureAddress.TA_WRAP,address_y=ue.TextureAddress.TA_WRAP,
                                  flip_green_channel=False).items():
                correction_texture.set_editor_property(key,value)
                assert correction_texture.get_editor_property(key)==value
            assert correction_texture.blueprint_get_size_x()==built['variants'][0]['walkBake']['width']
            assert correction_texture.blueprint_get_size_y()==built['variants'][0]['walkBake']['height']
            report['normalCorrection']=dict(**correction,asset=correction_texture.get_path_name(),saved=False)
        skel=ue.load_asset(built['sourceMesh'])
        clip=ue.load_asset(built['clips']['walk'])
        source=spawn(ue.SkeletalMeshActor,ue.Vector()).skeletal_mesh_component
        source.set_mobility(ue.ComponentMobility.MOVABLE)
        source.set_skeletal_mesh_asset(skel)
        if SHADOW_PARITY:
            source.set_cast_shadow(False)
            body.set_cast_shadow(False)
        report['shadowComparison'] = dict(parityRequested=SHADOW_PARITY,
                                          sourceCastsShadow=bool(source.get_editor_property('cast_shadow')),
                                          crowdCastsShadow=bool(body.get_editor_property('cast_shadow')))
        if SHADOW_PARITY:
            assert not any(report['shadowComparison'][k] for k in ('sourceCastsShadow','crowdCastsShadow'))
        meshes=[('source',built['sourceMesh'])]+[(str(row['target']),row['mesh']) for row in built['variants']]
        custom=[0.,.5,0.,0.,0.,0.,0.,0.,-1000.,.5/13.7,0.]
        instance_created=False
        material_cache={}
        def bind_review_materials(mesh, mesh_component, is_source):
            path=mesh.get_path_name()
            if path not in material_cache:
                bindings=[]
                rows=[]
                slots=mesh.get_editor_property('materials' if is_source else 'static_materials')
                for index,slot in enumerate(slots):
                    original=slot.get_editor_property('material_interface')
                    assert original
                    parent=original
                    chain=[]
                    while isinstance(parent,ue.MaterialInstance):
                        overrides=parent.get_editor_property('base_property_overrides')
                        chain.append(dict(path=parent.get_path_name(),
                                          overrideTwoSided=bool(overrides.get_editor_property('override_two_sided')),
                                          twoSided=bool(overrides.get_editor_property('two_sided'))))
                        parent=parent.get_editor_property('parent')
                        assert parent
                    row=dict(slot=index,material=original.get_path_name(),instanceChain=chain,
                             master=parent.get_path_name(),twoSided=bool(parent.get_editor_property('two_sided')),
                             tangentSpaceNormal=bool(parent.get_editor_property('tangent_space_normal')),disabledParameters={})
                    row['effectiveTwoSided']=next((entry['twoSided'] for entry in chain if entry['overrideTwoSided']),row['twoSided'])
                    binding=original
                    if NO_NORMAL_DETAIL or (NORMAL_CORRECTION and not is_source):
                        binding=mesh_component.create_dynamic_material_instance(index,original)
                        assert binding
                    if NO_NORMAL_DETAIL:
                        names={str(n) for n in ue.MaterialEditingLibrary.get_scalar_parameter_names(original)}
                        parameters=names.intersection(('PoreStrength','WeaveStrength') if is_source else ('DetailStrength',))
                        assert parameters, 'Missing normal-detail controls: '+original.get_path_name()
                        for parameter in sorted(parameters):
                            binding.set_scalar_parameter_value(parameter,0.)
                            value=float(binding.get_scalar_parameter_value(parameter))
                            assert value==0.
                            row['disabledParameters'][parameter]=value
                    if NORMAL_CORRECTION and not is_source:
                        binding.set_texture_parameter_value('WalkNormalTexture',correction_texture)
                        assert binding.get_texture_parameter_value('WalkNormalTexture')==correction_texture
                        row['walkNormalOverride']=correction_texture.get_path_name()
                    bindings.append(binding)
                    rows.append(row)
                material_cache[path]=bindings
                report['materials'][path]=rows
            if NO_NORMAL_DETAIL or NORMAL_CORRECTION:
                for index,binding in enumerate(material_cache[path]):
                    mesh_component.set_material(index,binding)
                    assert mesh_component.get_material(index)==binding
        for frame,label,path in [(frame,label,path) for frame in FRAMES for label,path in meshes]:
            label='frame%02d-'%frame+label
            is_source=path==built['sourceMesh']
            body.set_visibility(not is_source)
            source.set_visibility(is_source)
            readback=[]
            mesh=ue.load_asset(path)
            assert mesh
            if is_source:
                assert ue.MikdashAnimationReviewLibrary.evaluate_review_pose(source,clip,frame/60.)
            else:
                if body.get_editor_property('static_mesh') != mesh:
                    assert body.set_static_mesh(mesh)
                assert body.get_editor_property('static_mesh') == mesh
                if not instance_created:
                    assert body.add_instance(ue.Transform())==0
                    instance_created=True
                custom[0]=frame/72.
                for idx,value in enumerate(custom):
                    assert body.set_custom_data_value(0,idx,value,True)
                readback=list(body.get_editor_property('per_instance_sm_custom_data'))
                assert len(readback)==11 and all(abs(a-b)<1e-6 for a,b in zip(readback,custom))
            bind_review_materials(mesh,source if is_source else body,is_source)
            ue.AutomationLibrary.finish_loading_before_screenshot()
            image = OUT/('render-'+stamp+'-'+label+'.png')
            assert not image.exists()
            for _ in range(8):
                component.capture_scene()
                ue.RenderingLibrary.read_render_target_pixel(world,target,480,480)
            ue.RenderingLibrary.export_render_target(world,target,str(OUT),image.name)
            data=image.read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',data[16:24]) == (960,960)
            report['captures'].append(dict(label=label,mesh=path,triangles=None if is_source else mesh.get_num_triangles(0),frame=frame,customData=readback,file=image.name,sha256=sha(image)))
        report['status']='captured-review-pending'
    except Exception as error:
        report.update(status='failed',error=repr(error))
        raise
    finally:
        for actor in reversed(spawned): actors.destroy_actor(actor)
        if NORMAL_CORRECTION and 'normalCorrection' in report:
            package=report['normalCorrection']['asset'].split('.')[0].removeprefix('/Game/')
            assert not (ROOT/'Content'/(package+'.uasset')).exists(), 'Diagnostic texture unexpectedly saved'
        report['protectedUnchanged'] = before == {str(p.relative_to(ROOT)):sha(p) for p in protected}
        if not report['protectedUnchanged']: report['status']='failed-protected-changed'
        output.write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__': run()

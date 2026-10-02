"""Controlled angular pose proof only. No temporal-velocity acceptance."""
import math

def run(ue,builder,master,body,world,inputs,spawn,out,report,png_safe):
    def require(ok,msg):
        if not ok:raise RuntimeError(msg)
    bindings=[]
    for index,slot,path in inputs['slots']:
        mid=body.create_dynamic_material_instance(index,master)
        require(mid is not None,'Transient candidate MID failed')
        for key,value in inputs['parameters'][path.rsplit('.',1)[-1]].items():
            if isinstance(value,str):mid.set_texture_parameter_value(key,ue.load_asset(value))
            elif isinstance(value,list):mid.set_vector_parameter_value(key,ue.LinearColor(*value,1))
            else:mid.set_scalar_parameter_value(key,float(value))
        bindings.append(mid)
    report['materialScope']='Single lit candidate master for angular/normal proof; source per-slot texture/scalar/vector overrides copied. Skin subsurface parity is not claimed.'
    report['bindings']=[{'slot':i,'material':body.get_material(i).get_path_name()} for i in range(len(bindings))]
    for intensity,yaw in ((3.,-115.),(1.,-45.)):
        light=spawn(ue.DirectionalLight,(0,0,1000),ue.Rotator(pitch=-25,yaw=yaw))
        light.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        light.light_component.set_editor_property('intensity',intensity)
    capture=spawn(ue.SceneCapture2D,(80,340,95),ue.Rotator(yaw=-103.24))
    component=capture.get_component_by_class(ue.SceneCaptureComponent2D)
    for key,value in dict(capture_every_frame=False,capture_on_movement=False,always_persist_rendering_state=True,fov_angle=40.).items():component.set_editor_property(key,value)
    target=ue.RenderingLibrary.create_render_target2d(world,960,720,ue.TextureRenderTargetFormat.RTF_RGBA8)
    component.set_editor_property('texture_target',target)
    settings=component.get_editor_property('post_process_settings')
    for key,value in dict(override_auto_exposure_min_brightness=True,override_auto_exposure_max_brightness=True,auto_exposure_min_brightness=1.,auto_exposure_max_brightness=1.,override_auto_exposure_bias=True,auto_exposure_bias=0.,override_bloom_intensity=True,bloom_intensity=0.).items():settings.set_editor_property(key,value)
    component.set_editor_property('post_process_settings',settings)
    report['posePlan']={'resolution':[960,720],'cases':['90deg','180deg','wrap170to190'],'scales':[.92,1.08],
        'sampleTimes':'start, midpoint, end; endpoint fixed-basis oracle for beauty and normals',
        'rateDegreesPerSyntheticSecond':90,'actualWorldTicksAdvanced':False,'velocityEvidence':'NOT collected or accepted in this commandlet pose stage'}
    def state(basis,delta,seconds,scale):
        transform=ue.Transform(location=ue.Vector(0,0,0),rotation=ue.Rotator(yaw=basis-90),scale=ue.Vector(scale,scale,scale))
        require(body.update_instance_transform(0,transform,False,True,True),'Instance transform update failed')
        cd=[0.]*30;cd[1]=.5;cd[2]=1.;cd[8]=-1000.;cd[9]=.3;cd[14]=1.;cd[22]=1.;cd[23]=-1000.
        cd[25]=-1000.;cd[26]=0.;cd[27]=delta;cd[28]=0.;cd[29]=delta
        for i,value in enumerate(cd):require(body.set_custom_data_value(0,i,value,True),'Per-instance setter failed')
        for mid in bindings:
            mid.set_scalar_parameter_value('ReviewTime',seconds)
            mid.set_scalar_parameter_value('ReviewPreviousTime',max(0,seconds-1/60))
        actual=list(body.get_editor_property('per_instance_sm_custom_data'))
        require(len(actual)==30 and all(abs(a-b)<1e-5 for a,b in zip(actual,cd)),'Custom data readback differs')
        got=body.get_instance_transform(0,True)
        require(abs(got.translation.x)+abs(got.translation.y)+abs(got.translation.z)<1e-6,'Root moved')
        require(actual[5:8]==[0,0,0] and actual[10]==0,'Linear drift/horizon nonzero')
        return {'basisDegrees':basis,'deltaDegrees':delta,'controlledTime':seconds,'previousControlledTime':max(0,seconds-1/60),
            'scale':scale,'root':[got.translation.x,got.translation.y,got.translation.z],'customData':actual}
    def shot(label,kind,proof):
        source=ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR if kind=='beauty' else ue.SceneCaptureSource.SCS_NORMAL
        component.set_editor_property('capture_source',source)
        # Bounded priming is not a convergence or temporal proof; image metrics gate visibility.
        for _ in range(3):
            component.capture_scene();ue.RenderingLibrary.read_render_target_pixel(world,target,480,360)
        raw=out/(label+'-'+kind+'.local-export.png');clean=out/(label+'-'+kind+'.png')
        ue.RenderingLibrary.export_render_target(world,target,str(out),raw.name)
        info=png_safe.sanitize_new_export(raw,clean)
        rgba,decoded=png_safe.decode(clean)
        require(decoded['visibleRgbPixels']>1000,'Empty or tiny render')
        report['captures'].append({'file':clean.name,'kind':kind,'state':proof,'png':decoded})
        return rgba
    for name,start,delta,scale in (('turn90',0.,90.,.92),('turn180',0.,180.,1.08),('wrap',170.,20.,1.08)):
        duration=abs(delta)/90.
        endpoint={}
        for label,time in (('start',0.),('mid',duration/2),('end',duration)):
            proof=state(start,delta,time,scale)
            for kind in ('beauty','normal'):
                pixels=shot(name+'-'+label,kind,proof)
                if label=='end':endpoint[kind]=pixels
        # Identical final pose via instance basis, with zero angular WPO. Same
        # controlled idle phase, camera and textures; tests normals as well as shape.
        proof=state(start+delta,0.,duration,scale)
        for kind in ('beauty','normal'):
            oracle=shot(name+'-basis-oracle',kind,proof)
            ref=endpoint[kind]
            error=sum(abs(a-b) for i,(a,b) in enumerate(zip(ref,oracle)) if i%4!=3)/(960*720*3)
            report.setdefault('endpointOracles',[]).append({'case':name,'kind':kind,'meanAbsoluteRgb8Error':error,'limit':2.0})
            require(error<=2.0,'Angular endpoint differs from equivalent instance basis')
    report['heldRootAllSamples']=True
    report['temporalAcceptance']=False

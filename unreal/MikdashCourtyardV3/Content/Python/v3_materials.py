"""Native Unreal v2 material/exposure/camera setup. Runtime QA still required."""
from pathlib import Path
import hashlib,json,math,re,runpy
import unreal

PROJECT=Path(__file__).resolve().parents[2]
ASSETS=PROJECT/'SourceAssets'
DEST='/Game/MikdashV3'
LEVEL=DEST+'/Maps/KiyorInspectionV2'


def normalize(name):
    return re.sub(r'[^a-z0-9]','',str(name).lower())


def physical_exposure():
    settings=unreal.PostProcessSettings()
    values={
        'auto_exposure_method':unreal.AutoExposureMethod.AEM_MANUAL,
        'auto_exposure_apply_physical_camera_exposure':True,
        'auto_exposure_bias':0.0,'camera_iso':100.0,'camera_shutter_speed':125.0,
        'depth_of_field_fstop':8.0,'depth_of_field_scale':0.0,
        'bloom_intensity':0.0,'motion_blur_amount':0.0,'vignette_intensity':0.12,
    }
    for key,value in values.items():
        settings.set_editor_property('override_'+key,True)
        settings.set_editor_property(key,value)
    for key,value in [('dynamic_global_illumination_method',unreal.DynamicGlobalIlluminationMethod.LUMEN),('reflection_method',unreal.ReflectionMethod.LUMEN)]:
        settings.set_editor_property('override_'+key,True);settings.set_editor_property(key,value)
    return settings


def material_profile(record):
    source=record['material'];category=record['category'];rgb=source['color']
    metal=float(source.get('metalness',0));rough=float(source.get('roughness',.8))
    water=source.get('transmission',0)>.1
    if water:return dict(kind='Water',color=[.90,.96,.97],metalness=0,roughness=.09,specular=.25,opacity=.16,ior=1.333)
    if category=='Kiyor':return dict(kind='Copper',color=[min(.72,max(.04,c)) for c in rgb],metalness=.95,roughness=max(.30,rough),specular=.5)
    if category=='Architecture' and metal<.2 and max(rgb)>.15:
        # Quiet, moderate diffuse reflectance; warmth is an artistic finish choice.
        return dict(kind='Limestone',color=[min(.58,c*.76) for c in rgb],metalness=0,roughness=.80,specular=.30)
    if category=='Character_pose_reference' and rough>=.85:
        return dict(kind='Cloth',color=[min(.72,c*.88) for c in rgb],metalness=0,roughness=.91,specular=.22)
    return dict(kind='SkinOrDetail' if category=='Character_pose_reference' else 'ArchitecturalDetail',color=[min(.72,c) for c in rgb],metalness=metal,roughness=max(.32,rough),specular=.32)


def create_native_material(profile):
    digest=hashlib.sha1(json.dumps(profile,sort_keys=True).encode()).hexdigest()[:10]
    name='M_'+profile['kind']+'_'+digest
    existing=unreal.load_asset(DEST+'/Materials/'+name)
    if existing:return existing
    material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    if not material:raise RuntimeError('Material creation failed: '+name)
    if profile['kind']=='Water':
        material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('translucency_lighting_mode',unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        material.set_editor_property('two_sided',True)
    edit=unreal.MaterialEditingLibrary
    color=edit.create_material_expression(material,unreal.MaterialExpressionConstant3Vector,-400,0)
    color.set_editor_property('constant',unreal.LinearColor(*profile['color'],1.0))
    if not edit.connect_material_property(color,'',unreal.MaterialProperty.MP_BASE_COLOR):raise RuntimeError('Base color connection failed')
    for row,(key,prop) in enumerate([('metalness','MP_METALLIC'),('roughness','MP_ROUGHNESS'),('specular','MP_SPECULAR'),('opacity','MP_OPACITY'),('ior','MP_REFRACTION')]):
        if key not in profile:continue
        expression=edit.create_material_expression(material,unreal.MaterialExpressionConstant,-400,140+row*90)
        expression.set_editor_property('r',float(profile[key]))
        if not edit.connect_material_property(expression,'',getattr(unreal.MaterialProperty,prop)):
            raise RuntimeError('Material connection failed: '+prop)
    edit.recompile_material(material)
    unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).save_loaded_asset(material)
    return material


def apply_materials(mesh):
    records=json.loads((ASSETS/'material-manifest.json').read_text())
    by_name={normalize(r['fbxMaterialName']):r for r in records}
    matches=[];unmatched=[]
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        names=[]
        for key in ('imported_material_slot_name','material_slot_name'):
            try:names.append(str(slot.get_editor_property(key)))
            except Exception:pass
        previous=slot.get_editor_property('material_interface')
        if previous:names.append(previous.get_name())
        record=next((by_name[normalize(n)] for n in names if normalize(n) in by_name),None)
        if record is None:
            unmatched.append({'slot':index,'names':names})
            continue
        profile=material_profile(record);native=create_native_material(profile)
        mesh.set_material(index,native)
        matches.append({'slot':index,'sourceMaterial':record['fbxMaterialName'],'sourceObject':record['sourceName'],'nativeMaterial':native.get_path_name(),'profile':profile})
    unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).save_loaded_asset(mesh)
    return {'matched':matches,'unmatched':unmatched}


def infer_axes(import_module):
    mesh,_=import_module['static_import']('axis-probe.fbx','SM_AxisProbe')
    actor=import_module['place'](mesh,'Temporary_AxisProbe',(0,0,0))
    _,center=import_module['dimensions_cm'](actor)
    mapping=[]
    for value in center:
        index=min(range(3),key=lambda i:abs(abs(value)-(i+1)*50))
        if abs(abs(value)-(index+1)*50)>.1:raise RuntimeError('Axis probe coordinate mismatch: '+str(center))
        mapping.append((index,1 if value>0 else -1))
    if len({pair[0] for pair in mapping})!=3:raise RuntimeError('Axis probe is not a signed permutation')
    return mapping,center


def convert(point,mapping):
    return unreal.Vector(*(point[index]*50*sign for index,sign in mapping))


def setup_camera(actors,name,eye,look,mapping,fov):
    location=convert(eye,mapping);target=convert(look,mapping)
    rotation=unreal.MathLibrary.find_look_at_rotation(location,target)
    actor=actors.spawn_actor_from_class(unreal.CameraActor,location,rotation)
    actor.set_actor_label(name)
    component=actor.get_component_by_class(unreal.CameraComponent)
    component.set_field_of_view(fov)
    component.set_editor_property('post_process_settings',physical_exposure())
    component.set_editor_property('post_process_blend_weight',1.0)
    return actor,dict(name=name,sourceEyeAmot=eye,sourceLookAmot=look,unrealEyeCm=[location.x,location.y,location.z],unrealLookCm=[target.x,target.y,target.z],horizontalFov=fov)


def setup_lighting(actors):
    # Keywords avoid positional Rotator ambiguity. Verified in the cloud editor:
    # roll 0, pitch -51, yaw 153 illuminates the kiyor-facing foundation wall.
    sun=actors.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,8000),unreal.Rotator(pitch=-51,yaw=153,roll=0))
    sun.set_actor_label('V3 daylight daylight — 20000 lux')
    component=sun.get_component_by_class(unreal.DirectionalLightComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE);component.set_intensity(20000);component.set_atmosphere_sun_light(True)
    atmosphere=actors.spawn_actor_from_class(unreal.SkyAtmosphere,unreal.Vector(0,0,0));atmosphere.set_actor_label('V3 daylight sky')
    sky=actors.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,8000));sky.set_actor_label('V2 skylight')
    component=sky.get_component_by_class(unreal.SkyLightComponent)
    component.set_mobility(unreal.ComponentMobility.MOVABLE);component.set_intensity(1.0);component.set_real_time_capture(True)
    volume=actors.spawn_actor_from_class(unreal.PostProcessVolume,unreal.Vector(0,0,0))
    volume.set_actor_label('V3 FIXED exposure — ISO100 f8 1-125s EV13')
    volume.set_editor_property('unbound',True);volume.set_editor_property('priority',1000.0)
    volume.set_editor_property('settings',physical_exposure())
    return dict(sunLux=20000,sunRotation={'roll':0,'pitch':-51,'yaw':153},iso=100,shutterSpeedReciprocalSeconds=125,aperture=8,EV100=math.log2(8*8*125),compensation=0,bloom=0,autoExposure=False,lightingStatus='technical setup; visual QA required')

import unreal,json
from pathlib import Path
names=['r.EyeAdaptation.CachedLightingPreExposure','sg.GlobalIlluminationQuality','r.Lumen.DiffuseIndirect.Allow','r.SkyLight.RealTimeReflectionCapture','r.SkyAtmosphere','r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange','Slate.bAllowThrottling']
r={k:unreal.SystemLibrary.get_console_variable_float_value(k) for k in names}
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
r['camera']=str(e.get_level_viewport_camera_info())
r['postProcess']=[]
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
 if isinstance(a,unreal.PostProcessVolume):
  p=a.get_editor_property('settings');row={}
  for k in ['auto_exposure_method','auto_exposure_apply_physical_camera_exposure','camera_iso','camera_shutter_speed','depth_of_field_fstop','auto_exposure_bias','override_auto_exposure_bias','override_camera_iso','override_camera_shutter_speed','override_depth_of_field_fstop']:
   try:row[k]=str(p.get_editor_property(k))
   except Exception as ex:row[k]=str(ex)
  r['postProcess'].append(row)
Path(unreal.Paths.project_dir(),'SourceAssets/visual-review/live-lighting-settings.json').write_text(json.dumps(r,indent=2))
unreal.log('LIVE_LIGHTING_SETTINGS_RECORDED')

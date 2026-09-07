import json,unreal
from pathlib import Path
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
r=[]
def props(o,ks):
 d={}
 for k in ks:
  try:d[k]=str(o.get_editor_property(k))
  except Exception as e:d[k]=str(e)
 return d
for a in actors:
 if any(k in a.get_class().get_name() for k in ['Sky','Light','Fog','PostProcess']):
  row={'label':a.get_actor_label(),'class':a.get_class().get_name(),'components':[]}
  for c in a.get_components_by_class(unreal.ActorComponent):
   if any(k in c.get_class().get_name() for k in ['Sky','Light','Fog']):row['components'].append({'class':c.get_class().get_name(),'props':props(c,['intensity','mobility','source_type','cubemap','real_time_capture','visible','hidden_in_game','affects_world','indirect_lighting_intensity','lower_hemisphere_is_black','atmosphere_sun_light'])})
  if isinstance(a,unreal.PostProcessVolume):row['settings']=props(a.get_editor_property('settings'),['auto_exposure_method','auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','dynamic_global_illumination_method','override_dynamic_global_illumination_method'])
  r.append(row)
Path(unreal.Paths.project_dir(),'SourceAssets/lighting-diagnostic.json').write_text(json.dumps(r,indent=2))

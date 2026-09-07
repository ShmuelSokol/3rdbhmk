import json, unreal
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert root==Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/MikdashV3/Maps/Courtyard')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
report={"actorCount":len(actors),"lights":[],"postProcess":[],"savedMapChanged":False}
def read(obj, names):
 out={}
 for name in names:
  try:out[name]=str(obj.get_editor_property(name))
  except Exception:pass
 return out
for actor in actors:
 for comp in actor.get_components_by_class(unreal.LightComponent):
  report["lights"].append({"actor":actor.get_actor_label(),"class":comp.get_class().get_name(),"location":str(actor.get_actor_location()),"settings":read(comp,["intensity","indirect_lighting_intensity","affects_world","visible","mobility","attenuation_radius"])})
 if isinstance(actor,unreal.PostProcessVolume):
  report["postProcess"].append({"actor":actor.get_actor_label(),"settings":read(actor.get_editor_property('settings'),["auto_exposure_method","auto_exposure_bias","auto_exposure_apply_physical_camera_exposure","camera_iso","camera_shutter_speed","depth_of_field_fstop","lumen_scene_lighting_quality","lumen_scene_detail","lumen_scene_view_distance","lumen_max_trace_distance"])})
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
(root/'SourceAssets/runtime-review/inner-lighting-audit.json').write_text(json.dumps(report,indent=2)+'\n')
unreal.log('MIKDASH_INNER_LIGHTING_AUDIT '+str(len(report['lights']))+' lights; map unchanged')

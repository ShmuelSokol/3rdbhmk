"""Bounded one-component visual comparison; restores original overrides, never saves map."""
import sys, types
assert 'mikdash_grain_review' not in sys.modules or not getattr(sys.modules['mikdash_grain_review'],'active',False)
m=types.ModuleType('mikdash_grain_review');sys.modules[m.__name__]=m
exec('''
import unreal,time,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert root==Path(r"C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3")
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);w=e.get_editor_world()
assert not e.get_game_world()
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
cs=[]
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
 for c in a.get_components_by_class(unreal.StaticMeshComponent):
  mesh=c.get_editor_property('static_mesh')
  if mesh and mesh.get_name().startswith('architecture_SM_0130_'):cs.append(c)
assert len(cs)==1,len(cs)
c=cs[0];old_overrides=list(c.get_editor_property('override_materials'));original=c.get_material(0)
pilot=unreal.load_asset('/Game/MikdashV3/MaterialReview/GrainPilotV1/M_InnerPaving_GrainReviewV1')
assert pilot and original and original.get_name()=='M_StonePilot_Paving_Pilot01_innerPaving'
oldcam=e.get_level_viewport_camera_info();oldthrottle=unreal.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
report={'status':'running','component':c.get_path_name(),'original':original.get_path_name(),'pilot':pilot.get_path_name(),'mapSaved':False,'events':[],'limits':'Editor still comparison; no packaged, motion or broad material acceptance.'}
path=root/'SourceAssets/material-review/GrainPilotV1/bounded-comparison.json'
def record(stage):
 report['events'].append({'stage':stage,'seconds':round(time.monotonic()-start,2)})
 path.write_text(json.dumps(report,indent=2),encoding='utf-8')
def stop():
 global active
 if not active:return
 c.set_editor_property('override_materials',old_overrides)
 e.set_level_viewport_camera_info(oldcam[0],oldcam[1])
 unreal.SystemLibrary.execute_console_command(w,'Slate.bAllowThrottling '+str(oldthrottle))
 unreal.unregister_slate_post_tick_callback(handle);active=False
 report['status']='restored'
 report['materialRestored']=c.get_material(0)==original
 report['overridesRestored']=list(c.get_editor_property('override_materials'))==old_overrides
 record('restored');unreal.log('GRAIN_REVIEW_RESTORED')
def tick(delta):
 global phase
 try:
  elapsed=time.monotonic()-start
  if elapsed>=150:stop()
  elif elapsed>=75 and phase==0:
   c.set_material(0,pilot);phase=1;record('candidate_applied')
 except Exception as error:
  report['error']=str(error);stop();raise
start=time.monotonic();phase=0;active=True
handle=unreal.register_slate_post_tick_callback(tick)
try:
 unreal.SystemLibrary.execute_console_command(w,'Slate.bAllowThrottling 0')
 for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
  if isinstance(a,unreal.SkyLight):a.get_component_by_class(unreal.SkyLightComponent).recapture_sky()
 e.set_level_viewport_camera_info(unreal.Vector(1200,-1500,820),unreal.Rotator(pitch=-40,yaw=180,roll=0))
 record('baseline');unreal.log('GRAIN_REVIEW_STARTED')
except Exception:
 stop();raise
''',m.__dict__)

"""One-stop exposure review; automatic restore; no map save."""
import sys,types
m=types.ModuleType('mikdash_exterior_exposure_review');sys.modules[m.__name__]=m
exec('''
import unreal,time,json
from pathlib import Path
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);w=e.get_editor_world()
assert not e.get_game_world()
volumes=[a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if isinstance(a,unreal.PostProcessVolume)]
assert len(volumes)==1
v=volumes[0];original=v.get_editor_property('settings')
oldbias=float(original.get_editor_property('auto_exposure_bias'));assert oldbias==0
oldcam=e.get_level_viewport_camera_info();oldthrottle=unreal.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
path=Path(unreal.Paths.project_dir(),'SourceAssets/visual-review/exterior-exposure-comparison.json')
r={'status':'running','originalBias':oldbias,'candidateBias':1,'events':[],'mapSaved':False,'scope':'Fixed physical exposure compensation pilot only; no source colors, sun or geometry changed.'}
start=time.monotonic();phase=0;active=True
def record(stage):
 r['events'].append({'stage':stage,'seconds':round(time.monotonic()-start,2)});path.write_text(json.dumps(r,indent=2))
def stop():
 global active
 if not active:return
 p=v.get_editor_property('settings');p.set_editor_property('auto_exposure_bias',oldbias);v.set_editor_property('settings',p)
 e.set_level_viewport_camera_info(oldcam[0],oldcam[1]);unreal.SystemLibrary.execute_console_command(w,'Slate.bAllowThrottling '+str(oldthrottle))
 unreal.unregister_slate_post_tick_callback(handle);active=False
 r['status']='restored';r['biasRestored']=v.get_editor_property('settings').get_editor_property('auto_exposure_bias')==oldbias;record('restored')
 unreal.log('EXTERIOR_EXPOSURE_REVIEW_RESTORED')
def tick(delta):
 global phase
 try:
  elapsed=time.monotonic()-start
  if elapsed>=120:stop()
  elif elapsed>=60 and phase==0:
   p=v.get_editor_property('settings');p.set_editor_property('auto_exposure_bias',1.0);v.set_editor_property('settings',p)
   phase=1;record('plus_one_stop')
 except Exception as ex:
  r['error']=str(ex);stop();raise
handle=unreal.register_slate_post_tick_callback(tick)
try:
 unreal.SystemLibrary.execute_console_command(w,'Slate.bAllowThrottling 0')
 e.set_level_viewport_camera_info(unreal.Vector(6500,-1800,468),unreal.Rotator(pitch=0,yaw=155,roll=0));record('baseline')
except Exception:
 stop();raise
''',m.__dict__)


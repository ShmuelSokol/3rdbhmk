import sys,types
m=types.ModuleType('mikdash_stone_visual');sys.modules[m.__name__]=m
exec('''
import unreal,time,json
from pathlib import Path
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);w=e.get_editor_world()
assert not e.get_game_world()
old=e.get_level_viewport_camera_info();oldthrottle=unreal.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
unreal.SystemLibrary.execute_console_command(w,'Slate.bAllowThrottling 0')
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
 if isinstance(a,unreal.SkyLight):a.get_component_by_class(unreal.SkyLightComponent).recapture_sky()
e.set_level_viewport_camera_info(unreal.Vector(-1200,0,1450),unreal.Rotator(pitch=-15,yaw=180,roll=0))
start=time.monotonic()
def tick(delta):
 if time.monotonic()-start>90:
  e.set_level_viewport_camera_info(old[0],old[1])
  unreal.SystemLibrary.execute_console_command(w,'Slate.bAllowThrottling '+str(oldthrottle))
  unreal.unregister_slate_post_tick_callback(handle)
  unreal.log('STONE_VISUAL_REVIEW_CAMERA_RESTORED')
handle=unreal.register_slate_post_tick_callback(tick)
''',m.__dict__)

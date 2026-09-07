import unreal,time,sys,types
m=types.ModuleType('mikdash_visual_tick');sys.modules[m.__name__]=m
exec('''
import unreal,time
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_editor_world()
old=unreal.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
unreal.SystemLibrary.execute_console_command(world,'Slate.bAllowThrottling 0')
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if isinstance(a,unreal.SkyLight):a.get_component_by_class(unreal.SkyLightComponent).recapture_sky()
start=time.monotonic()
def tick(delta):
    if time.monotonic()-start>90:
        unreal.SystemLibrary.execute_console_command(world,'Slate.bAllowThrottling '+str(old))
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.log('VISUAL_THROTTLE_RESTORED')
handle=unreal.register_slate_post_tick_callback(tick)
''',m.__dict__)

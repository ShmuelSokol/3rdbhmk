"""Dedicated editor bounded PIE flight/return test. No map writes or UI injection."""
from pathlib import Path
import hashlib,json,time
from datetime import datetime,timezone
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
MAP='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
assert ed.get_game_world() is None
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
assert ed.get_editor_world().get_outermost().get_name()==MAP
file=ROOT/'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap'
sha=lambda:hashlib.sha256(file.read_bytes()).hexdigest()
out=ROOT/'SourceAssets/runtime-review/dove-flight'/('native-flight-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
out.parent.mkdir(parents=True,exist_ok=True)
report=dict(status='starting',mapShaBefore=sha(),errors=[],samples=[],scope='Synthetic PIE movement, pause and walking-pawn restoration; visual and keyboard tests separate')
state=dict(start=time.monotonic(),phase='world',at=time.monotonic(),stopping=False)
settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse=settings.get_editor_property('GameGetsMouseControl')
old_throttle=u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
def xyz(v):return [v.x,v.y,v.z]
def write():out.write_text(json.dumps(report,indent=2)+'\n')
def phase(name):state.update(phase=name,at=time.monotonic())
def finish(status):
 if state['stopping']:return
 report['status']=status;state['stopping']=True;phase('stopping')
 levels.editor_request_end_play();write()
def tick(dt):
 try:
  now=time.monotonic();world=ed.get_game_world()
  if state['stopping']:
   if world and now-state['at']<10:return
   if world:report['errors'].append('PIE teardown timeout')
   report['pieEnded']=world is None;report['mapBytesUnchanged']=sha()==report['mapShaBefore']
   for restore in (lambda:settings.set_editor_property('GameGetsMouseControl',old_mouse),lambda:u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling '+str(old_throttle))):
    try:restore()
    except Exception as exc:report['errors'].append('Cleanup: '+repr(exc))
   if report['errors'] or not report['mapBytesUnchanged']:report['status']='failed_cleanup_or_verification'
   try:write()
   finally:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
   return
  if now-state['start']>100:finish('failed_watchdog');return
  if not world:return
  c=u.GameplayStatics.get_player_controller(world,0)
  if not c:return
  if state['phase']=='world':
   cls=u.load_class(None,'/Script/MikdashRuntime.MikdashResidentPopulation')
   populations=list(u.GameplayStatics.get_all_actors_of_class(world,cls))
   assert len(populations)==1 and populations[0].is_population_active(),'Authored population did not auto-initialize'
   state['bodies']=list(populations[0].get_editor_property('bodies'))
   assert len(state['bodies'])==5
   state['bodyStarts']=[b.get_actor_location() for b in state['bodies']]
   c.resume_walkthrough();state['resumed']=now;phase('settle');return
  elapsed=now-state['at']
  if state['phase']=='settle':
   if elapsed<2:return
   state['walker']=u.GameplayStatics.get_player_pawn(world,0);state['walkPos']=state['walker'].get_actor_location()
   report['walkerClass']=state['walker'].get_class().get_path_name();report['walkingStart']=xyz(state['walkPos'])
   c.toggle_dove_flight();assert c.is_dove_flight_active(),'Flight did not activate'
   state['bird']=u.GameplayStatics.get_player_pawn(world,0);assert state['bird']!=state['walker']
   state['birdStart']=state['bird'].get_actor_location();report['birdClass']=state['bird'].get_class().get_path_name()
   phase('forward');return
  bird=state['bird']
  if state['phase']=='forward':
   bird.add_movement_input(u.Vector(1,0,0),1.0,False)
   if elapsed>=1.5:
    delta=bird.get_actor_location()-state['birdStart'];report['forwardDisplacement']=xyz(delta)
    assert delta.length()>100,'No meaningful flight movement'
    state['riseStart']=bird.get_actor_location();phase('rise')
   return
  if state['phase']=='rise':
   bird.add_movement_input(u.Vector(0,0,1),1.0,False)
   if elapsed>=1:
    report['riseCm']=bird.get_actor_location().z-state['riseStart'].z
    assert report['riseCm']>100,'Ascent failed'
    u.GameplayStatics.set_game_paused(world,True);state['pausePos']=bird.get_actor_location();phase('paused')
   return
  if state['phase']=='paused':
   if elapsed<1:return
   report['pauseDriftCm']=(bird.get_actor_location()-state['pausePos']).length();assert report['pauseDriftCm']<.1
   u.GameplayStatics.set_game_paused(world,False);c.toggle_dove_flight()
   assert not c.is_dove_flight_active() and u.GameplayStatics.get_player_pawn(world,0)==state['walker'],'Walking pawn not restored'
   report['returnErrorCm']=(u.GameplayStatics.get_player_pawn(world,0).get_actor_location()-state['walkPos']).length()
   assert report['returnErrorCm']<3,'Return position changed'
   report['walkerCollisionEnabled']=u.GameplayStatics.get_player_pawn(world,0).get_actor_enable_collision();assert report['walkerCollisionEnabled']
   phase('residents');return
  if state['phase']=='residents':
   if now-state['resumed']<24:return
   rows=[]
   for b,start in zip(state['bodies'],state['bodyStarts']):
    moved=(b.get_actor_location()-start).length()
    row=dict(movedCm=moved,diagnostic=b.get_route_diagnostic(),state=b.get_resident_state())
    rows.append(row)
    # Body 04 now walks an extended 69 m loop, so the old 50-100 cm window no longer applies.
    assert moved > 40 and row['diagnostic']=='Physical arrival confirmed','Resident failed to arrive in main world (moved %.1f cm)' % moved
   report['residents']=rows
   finish('passed_flight_ascent_pause_return_and_main_residents_visual_pending')
 except Exception as exc:
  report['errors'].append(repr(exc))
  if state['stopping']:
   report['status']='failed_cleanup_exception'
   try:write()
   finally:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:finish('failed_exception')
settings.set_editor_property('GameGetsMouseControl',False)
u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling 0')
write();handle=u.register_slate_post_tick_callback(tick);levels.editor_request_begin_play()

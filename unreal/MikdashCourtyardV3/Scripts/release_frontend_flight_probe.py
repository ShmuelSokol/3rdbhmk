"""Bounded frontend state and dove flight test; no map writes or UI injection."""
from pathlib import Path
import hashlib,json,time,os,re
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
out=ROOT/'SourceAssets/runtime-review/frontend-flight'/('native-frontend-flight-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
out.parent.mkdir(parents=True,exist_ok=True)
report=dict(status='starting',mapShaBefore=sha(),errors=[],samples=[],scope='Native frontend transitions and dove movement/pause/return; visual, physical keyboard and resident behavior are separate')
direct_intro='-directintroflight' in u.SystemLibrary.get_command_line().lower()
report['flightEntry']='direct_toggle_during_intro' if direct_intro else 'menu_request_during_intro'
state=dict(start=time.monotonic(),phase='world',at=time.monotonic(),stopping=False)
settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse=settings.get_editor_property('GameGetsMouseControl')
old_throttle=u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
command_line=u.SystemLibrary.get_command_line()
prefix_match=re.search(r'-TestSavePrefix=(AstraProbe_[A-Za-z0-9_]+)',command_line)
assert prefix_match,'Require a unique -TestSavePrefix=AstraProbe_<stamp> and Game ini overrides'
test_prefix=prefix_match.group(1)
for section,key,value in [('MikdashSaveSystem','SlotNamePrefix',test_prefix),('MikdashSettingsSubsystem','SaveSlot',test_prefix+'_Settings')]:
 assert ('[/Script/MikdashRuntime.'+section+']:'+key+'='+value) in command_line,'Missing save-isolation ini override'
save_roots=[ROOT/'Saved/SaveGames',Path(os.environ['LOCALAPPDATA'])/'MikdashCourtyardV3/Saved/SaveGames']
def user_save_hashes():
 return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in save_roots
         if folder.exists() for p in folder.glob('*.sav') if not p.name.startswith('AstraProbe_')}
original_saves=user_save_hashes()
report['saveIsolation']=dict(testPrefix=test_prefix,originalSaveFileCount=len(original_saves))
def xyz(v):return [v.x,v.y,v.z]
def write():out.write_text(json.dumps(report,indent=2)+'\n')
def phase(name):
 world=ed.get_game_world()
 state.update(phase=name,at=time.monotonic(),phaseTicks=0,
              gameAt=u.GameplayStatics.get_time_seconds(world) if world else 0.0)
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
   report['saveIsolation']['originalSavesUnchanged']=user_save_hashes()==original_saves
   if not report['saveIsolation']['originalSavesUnchanged']:report['errors'].append('Original save files changed')
   for restore in (lambda:settings.set_editor_property('GameGetsMouseControl',old_mouse),lambda:u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling '+str(old_throttle))):
    try:restore()
    except Exception as exc:report['errors'].append('Cleanup: '+repr(exc))
   if report['errors'] or not report['mapBytesUnchanged']:report['status']='failed_cleanup_or_verification'
   try:write()
   finally:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
   return
  if now-state['start']>180:finish('failed_watchdog');return
  if not world:return
  c=u.GameplayStatics.get_player_controller(world,0)
  if not c:return
  if state['phase']=='world':
   front=u.MikdashFrontEnd.get(world)
   if front is None or not front.is_front_end_visible():return
   state['front']=front
   saves=u.MikdashSaveSystem.get(world)
   assert all(str(slot.slot_name).startswith(test_prefix+'_') for slot in saves.get_slot_infos(True)),'Save slot isolation did not reach live subsystem'
   assert c.is_walkthrough_menu_open() and u.GameplayStatics.is_game_paused(world)
   front.show_settings();phase('settings');return
  if state['phase']=='settings':
   front=state['front'];assert front.get_screen()==u.MikdashScreen.SETTINGS
   front.go_back();phase('main_return');return
  if state['phase']=='main_return':
   front=state['front'];assert front.get_screen()==u.MikdashScreen.MAIN_MENU
   front.show_preparation_lesson();phase('preparation');return
  if state['phase']=='preparation':
   front=state['front'];assert front.get_screen()==u.MikdashScreen.PREPARATION
   front.go_back();phase('preparation_return');return
  if state['phase']=='preparation_return':
   front=state['front'];assert front.get_screen()==u.MikdashScreen.MAIN_MENU
   report['frontendTransitions']=['main','settings','main','preparation','main','resume']
   c.resume_walkthrough();state['resumed']=now;phase('intro_handover');return
  elapsed=now-state['at']
  state['phaseTicks']=state.get('phaseTicks',0)+1
  game_elapsed=u.GameplayStatics.get_time_seconds(world)-state.get('gameAt',0.0)
  if state['phase']=='intro_handover':
   cinematic=u.MikdashCinematics.get(world)
   assert cinematic and cinematic.is_playing(),'Menu flight regression requires the active first-entry intro'
   report['introPlaybackRoute']=cinematic.get_playback_route()
   report['introMoveInputInitiallyIgnored']=c.is_move_input_ignored()
   assert report['introMoveInputInitiallyIgnored'],'Intro must own movement before requesting flight'
   state['walker']=u.GameplayStatics.get_player_pawn(world,0)
   if direct_intro:
    if elapsed<2:return
    c.toggle_dove_flight()
   else:c.request_dove_flight_from_menu()
   assert not cinematic.is_playing(),'Flight request did not stop the intro'
   report['flightRequestSkippedIntro']=True
   assert not c.is_move_input_ignored(),'Movement remains ignored after intro handover'
   assert not c.is_look_input_ignored(),'Look remains ignored after intro handover'
   phase('settle');return
  if state['phase']=='settle':
   if not c.is_dove_flight_active():
    assert elapsed<5,'Menu flight did not activate after grounding'
    return
   state['walkPos']=state['walker'].get_actor_location()
   report['walkerClass']=state['walker'].get_class().get_path_name();report['walkingStart']=xyz(state['walkPos'])
   state['bird']=u.GameplayStatics.get_player_pawn(world,0);assert state['bird']!=state['walker']
   assert c.get_view_target()==state['bird'],'Flight view target is not the bird'
   report['flightOwnsView']=True
   state['birdStart']=state['bird'].get_actor_location();report['birdClass']=state['bird'].get_class().get_path_name()
   phase('forward');return
  bird=state['bird']
  if state['phase']=='forward':
   bird.add_movement_input(u.Vector(1,0,0),1.0,False)
   if state['phaseTicks']<=3 or state['phaseTicks']%10==0:
    report['samples'].append(dict(phase='forward',wallSeconds=elapsed,gameSeconds=game_elapsed,
      ticks=state['phaseTicks'],position=xyz(bird.get_actor_location()),velocity=xyz(bird.get_velocity()),
      paused=u.GameplayStatics.is_game_paused(world),menuOpen=c.is_walkthrough_menu_open(),
      moveInputIgnored=c.is_move_input_ignored()))
   if game_elapsed>=1.5 and state['phaseTicks']>=20:
    delta=bird.get_actor_location()-state['birdStart'];report['forwardDisplacement']=xyz(delta)
    assert delta.length()>100,'No meaningful flight movement'
    state['riseStart']=bird.get_actor_location();phase('rise')
   return
  if state['phase']=='rise':
   bird.add_movement_input(u.Vector(0,0,1),1.0,False)
   if game_elapsed>=1 and state['phaseTicks']>=20:
    report['riseCm']=bird.get_actor_location().z-state['riseStart'].z
    assert report['riseCm']>100,'Ascent failed'
    state['front'].show_pause_menu();assert state['front'].get_screen()==u.MikdashScreen.PAUSE_MENU and c.is_walkthrough_menu_open();state['pausePos']=bird.get_actor_location();phase('paused')
   return
  if state['phase']=='paused':
   if elapsed<1:return
   report['pauseDriftCm']=(bird.get_actor_location()-state['pausePos']).length();assert report['pauseDriftCm']<.1
   state['front'].resume_walkthrough();assert not c.is_walkthrough_menu_open();c.toggle_dove_flight()
   assert not c.is_dove_flight_active() and u.GameplayStatics.get_player_pawn(world,0)==state['walker'],'Walking pawn not restored'
   report['returnErrorCm']=(u.GameplayStatics.get_player_pawn(world,0).get_actor_location()-state['walkPos']).length()
   assert report['returnErrorCm']<3,'Return position changed'
   report['walkerCollisionEnabled']=u.GameplayStatics.get_player_pawn(world,0).get_actor_enable_collision();assert report['walkerCollisionEnabled']
   phase('final_state');return
  if state['phase']=='final_state':
   assert not c.is_walkthrough_menu_open() and not u.GameplayStatics.is_game_paused(world)
   assert not state['front'].is_front_end_visible()
   if '-testtour' in u.SystemLibrary.get_command_line().lower():
    guides=list(u.GameplayStatics.get_all_actors_of_class(world,u.MikdashTourGuide))
    books=list(u.GameplayStatics.get_all_actors_of_class(world,u.MikdashCodex))
    assert len(guides)==1 and len(books)==1,'Missing or duplicated tour/codex'
    guide=guides[0];book=books[0]
    assert guide.is_route_loaded() and guide.get_stop_count()==18,'Tour route not loaded'
    assert book.is_loaded() and book.num()==76,'Codex not loaded'
    assert 'Content/Distribution/Tour/' in guide.get_content_path().replace('\\','/'),'Tour using development path'
    assert 'Content/Distribution/Tour/' in book.get_content_path().replace('\\','/'),'Codex using development path'
    assert state['front'].is_guided_tour_available(),'Frontend tour action unbound'
    state['front'].request_guided_tour();assert guide.is_tour_running(),'Tour menu request did not start tour'
    guide.pause_tour();assert guide.is_tour_paused(),'Tour did not pause'
    guide.resume_tour();assert not guide.is_tour_paused(),'Tour did not resume'
    guide.toggle_codex_panel();assert guide.is_codex_panel_visible(),'Codex panel did not open'
    guide.toggle_codex_panel();assert not guide.is_codex_panel_visible(),'Codex panel did not close'
    guide.leave_tour();assert not guide.is_tour_running(),'Tour did not end'
    report['tour']=dict(stops=guide.get_stop_count(),codexEntries=book.num(),
      transitions=['menu request','pause','resume','open codex','close codex','leave'],
      scope='Live API interaction and staged content paths; route walking, narration and packaged readback remain unverified')
   if '-testintegratedsystems' in u.SystemLibrary.get_command_line().lower():
    crowds=list(u.GameplayStatics.get_all_actors_of_class(world,u.MikdashCrowdField))
    effects=list(u.GameplayStatics.get_all_actors_of_class(world,u.MikdashFXDirector))
    assert len(crowds)==1 and len(effects)==1,'Missing or duplicated integrated systems'
    crowd=crowds[0];fx=effects[0]
    report['integratedSystems']=dict(crowdSeeded=crowd.get_seeded_agent_count(),
      crowdInstances=crowd.get_total_instance_count(),crowdRefused=crowd.get_refused_seed_count(),
      groundTraceMisses=crowd.get_ground_trace_miss_count(),zones=list(crowd.get_zone_instance_counts()),
      liveFxCards=fx.get_live_card_count(),fxStatus=fx.get_status(),
      scope='Live presence and activity; appearance, paths and performance not accepted')
    assert report['integratedSystems']['crowdSeeded']==240,'Configured crowd did not seed fully'
    assert report['integratedSystems']['liveFxCards']>0,'No active FX cards'
   if '-takediagnosticstill' in u.SystemLibrary.get_command_line().lower():
    c.set_control_rotation(u.Rotator(pitch=0,yaw=180,roll=0))
    if '-diagnosticheikhal' in u.SystemLibrary.get_command_line().lower():
     cameras=list(u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor))
     assert cameras,'No PIE camera actor for sanctuary diagnostic'
     camera=cameras[0]
     # Legacy review cameras carry fixed ISO100/f8/1/125 outdoor exposure.
     # This PIE-only diagnostic must use the same global exposure as walking.
     component=camera.get_component_by_class(u.CameraComponent)
     component.set_editor_property('post_process_blend_weight',0.0)
     assert component.get_editor_property('post_process_blend_weight')==0.0
     camera.set_actor_location(u.Vector(-4000,0,1093),False,True)
     camera.set_actor_rotation(u.Rotator(pitch=0,yaw=180,roll=0),True)
     c.set_view_target_with_blend(camera,0.0)
     state['diagnosticExpectedCamera']=u.Vector(-4000,0,1093)
     report['diagnosticCameraPostProcessBlendWeight']=0.0
    phase('diagnostic_warm');return
   finish('passed_intro_flight_ascent_pause_exact_return_visual_pending')
  if state['phase']=='diagnostic_warm':
   if elapsed<20:return
   path=ROOT/'SourceAssets/visual-review'/('runtime-diagnostic-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.png')
   state['diagnosticPath']=path
   camera=u.GameplayStatics.get_player_camera_manager(world,0)
   if 'diagnosticExpectedCamera' in state:
    assert (camera.get_camera_location()-state['diagnosticExpectedCamera']).length()<1,'Wrong PIE diagnostic camera'
   report['diagnosticStill']=dict(file=str(path),cameraCm=xyz(camera.get_camera_location()),
     scope='Actual PIE view after 20 seconds; derived-data barrier NOT completed, lighting/quality acceptance pending')
   u.SystemLibrary.execute_console_command(world,'HighResShot 1280x720 filename="'+str(path)+'"',c)
   phase('diagnostic_wait');return
  if state['phase']=='diagnostic_wait':
   path=state['diagnosticPath']
   if not path.exists():
    assert elapsed<30,'Diagnostic screenshot did not arrive'
    return
   data=path.read_bytes()
   assert data[:8]==b'\x89PNG\r\n\x1a\n','Screenshot is not PNG'
   report['diagnosticStill'].update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
   finish('passed_intro_flight_ascent_pause_exact_return_visual_pending')
 except Exception as exc:
  report['errors'].append(repr(exc))
  if state['stopping']:
   report['status']='failed_cleanup_exception'
   try:write()
   finally:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:finish('failed_exception')
handle=None
try:
 settings.set_editor_property('GameGetsMouseControl',False)
 u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling 0')
 write();handle=u.register_slate_post_tick_callback(tick);levels.editor_request_begin_play()
except Exception as exc:
 report['status']='failed_setup';report['errors'].append(repr(exc))
 if handle is not None:
  try:u.unregister_slate_post_tick_callback(handle)
  except Exception as cleanup:report['errors'].append('Callback cleanup: '+repr(cleanup))
 for restore in (lambda:levels.editor_request_end_play(),lambda:settings.set_editor_property('GameGetsMouseControl',old_mouse),lambda:u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling '+str(old_throttle))):
  try:restore()
  except Exception as cleanup:report['errors'].append('Setup cleanup: '+repr(cleanup))
 report['mapBytesUnchanged']=sha()==report['mapShaBefore']
 try:write()
 finally:u.SystemLibrary.quit_editor()
 raise

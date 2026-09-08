"""Bounded frontend state and dove flight test; no map writes or UI injection."""
from pathlib import Path
import hashlib,json,time,os,re
from datetime import datetime,timezone
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
MAP='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
selected48='-candidate48' in u.SystemLibrary.get_command_line().lower()
if selected48:MAP='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
assert ed.get_game_world() is None
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
assert ed.get_editor_world().get_outermost().get_name()==MAP
file=ROOT/'Content'/(MAP[6:]+'.umap')
main_file=ROOT/'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap'
main_before=hashlib.sha256(main_file.read_bytes()).hexdigest()
sha=lambda:hashlib.sha256(file.read_bytes()).hexdigest()
out=ROOT/'SourceAssets/runtime-review/frontend-flight'/('native-frontend-flight-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
out.parent.mkdir(parents=True,exist_ok=True)
report=dict(status='starting',mapShaBefore=sha(),errors=[],samples=[],scope='Native frontend transitions and dove movement/pause/return; visual, physical keyboard and resident behavior are separate')
report['map']=MAP
direct_intro='-directintroflight' in u.SystemLibrary.get_command_line().lower()
report['flightEntry']='direct_toggle_during_intro' if direct_intro else 'menu_request_during_intro'
state=dict(start=time.monotonic(),phase='world',at=time.monotonic(),stopping=False)
settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse=settings.get_editor_property('GameGetsMouseControl')
old_throttle=u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
command_line=u.SystemLibrary.get_command_line()
comparison_flags=[f for f in ('-comparepaving','-comparejerusalempaving','-comparefloors','-comparedaylight','-comparecooldaylight') if f in command_line.lower()]
assert len(comparison_flags)<=1,'Run one isolated comparison at a time'
assert not (selected48 and comparison_flags),'Material/light comparisons are for main only'
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

def exposure_snapshot(world):
 # Settings only: actual adapted exposure can respond to changed scene luminance.
 keys=('auto_exposure_method','auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias',
       'override_auto_exposure_method','override_auto_exposure_min_brightness','override_auto_exposure_max_brightness','override_auto_exposure_bias')
 def fields(settings):
  result={}
  for key in keys:
   value=settings.get_editor_property(key)
   result[key]=value if isinstance(value,(float,int,bool,str)) else str(value)
  return result
 volumes={}
 for volume in u.GameplayStatics.get_all_actors_of_class(world,u.PostProcessVolume):
  volumes[volume.get_name()]={'settings':fields(volume.get_editor_property('settings')),
    'blendWeight':volume.get_editor_property('blend_weight'),'priority':volume.get_editor_property('priority')}
 assert volumes,'Need actual postprocess exposure settings'
 target=u.GameplayStatics.get_player_controller(world,0).get_view_target()
 camera=target.get_component_by_class(u.CameraComponent)
 assert camera,'Need diagnostic camera exposure state'
 return {'volumes':volumes,'camera':{'blendWeight':camera.get_editor_property('post_process_blend_weight'),
   'settings':fields(camera.get_editor_property('post_process_settings'))}}
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
   report['mainBytesUnchanged']=hashlib.sha256(main_file.read_bytes()).hexdigest()==main_before
   if not report['mainBytesUnchanged']:report['errors'].append('Main map bytes changed')
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
  if state['phase']=='group_observe':
   if game_elapsed-state.get('lastGroupSample',-1)>=1:
    state['lastGroupSample']=game_elapsed
    report['groupSamples'].append({'seconds':game_elapsed,'state':state['groupProbe'].snapshot(state['groupCrowd'])})
   if game_elapsed<10:return
   report['groupAssessment']=state['groupProbe'].assess(report['groupSamples'])
   state['groupsObserved']=True;phase('final_state');return
  if state['phase']=='final_state':
   assert not c.is_walkthrough_menu_open() and not u.GameplayStatics.is_game_paused(world)
   assert not state['front'].is_front_end_visible()
   if '-testvisitorgroups' in command_line.lower() and not state.get('groupsObserved'):
    import release_crowd_group_probe as group_probe
    crowds=list(u.GameplayStatics.get_all_actors_of_class(world,u.MikdashCrowdField));assert len(crowds)==1
    state['groupProbe']=group_probe;state['groupCrowd']=crowds[0]
    report['groupSamples']=[];phase('group_observe');return
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
    if '-testvisitorgroups' in command_line.lower():
     # Cohorts refuse unsafe placement atomically; never split them just to meet a count.
     assert report['integratedSystems']['crowdInstances']==240,'Requested crowd allocation changed'
     assert report['integratedSystems']['crowdSeeded']+report['integratedSystems']['crowdRefused']==240,'Unaccounted visitor allocation'
     report['integratedSystems']['coverage']='partial_safe_refusal' if report['integratedSystems']['crowdRefused'] else 'all_requested_seeded'
     report['integratedSystems']['scope']+='; explicit cohort refusals are reported, not full-population acceptance'
    else:assert report['integratedSystems']['crowdSeeded']==240,'Configured crowd did not seed fully'
    assert report['integratedSystems']['liveFxCards']>0,'No active FX cards'
   if selected48:
    descriptors=list(u.GameplayStatics.get_all_actors_of_class(world,u.MikdashSceneUnits))
    assert len(descriptors)==1 and str(descriptors[0].get_editor_property('scene_revision'))=='Selected48.v1','Wrong scene frame'
    assert abs(state['walkPos'].x-2016)<3 and abs(state['walkPos'].z-576)<5,'Unexpected selected48 starting support'
    crowd=list(u.GameplayStatics.get_all_actors_of_class(world,u.MikdashCrowdField))[0]
    assert crowd.get_coordinate_status().startswith('Selected48'),'Crowd did not select48 frame'
    report['selected48']={'descriptor':str(descriptors[0].validate_descriptor()),'crowdStatus':crowd.get_coordinate_status(),'zones':[]}
    for source in crowd.get_editor_property('zones'):
     name=source.get_editor_property('name');runtime=crowd.get_runtime_zone(name)
     if isinstance(runtime,tuple):
      assert len(runtime)==2 and runtime[0] is True,'Runtime zone getter refused'
      runtime=runtime[1]
     assert runtime is not None,'Missing runtime zone'
     legacy_z=source.get_editor_property('ground_z_base');actual_z=runtime.get_editor_property('ground_z_base')
     ratio=.96 if name in ('OuterCourtEast','OuterCourtWestTerrace') else 1.0
     assert abs(actual_z-legacy_z*ratio)<.001,'Wrong runtime crowd support'
     old_poly=source.get_editor_property('polygon_cm');new_poly=runtime.get_editor_property('polygon_cm')
     assert len(old_poly)==len(new_poly)
     assert all(abs(n.x-o.x*ratio)<.001 and abs(n.y-o.y*ratio)<.001 for o,n in zip(old_poly,new_poly)),'Wrong spatial scope conversion'
     report['selected48']['zones'].append({'name':name,'legacyZ':legacy_z,'runtimeZ':actual_z,'ratio':ratio})
    populations=list(u.GameplayStatics.get_all_actors_of_class(world,u.MikdashResidentPopulation))
    report['selected48']['residents']=[{'living':p.get_living_resident_count(),'status':p.get_directory_status()} for p in populations]
   if '-testsaveroundtrip' in command_line.lower():
    saves=u.MikdashSaveSystem.get(world);pawn=u.GameplayStatics.get_player_pawn(world,0);saved_pos=pawn.get_actor_location()
    assert saves.save_to_slot(0,'Isolated Astra runtime verification'),'Native save write failed'
    pawn.set_actor_location(saved_pos+u.Vector(50,0,0),False,True)
    moved=(pawn.get_actor_location()-saved_pos).length()
    assert moved>45,'Deliberate save-test displacement did not occur'
    assert saves.load_from_slot(0),'Native save load failed'
    error=(pawn.get_actor_location()-saved_pos).length()
    report['saveRoundTrip']={'displacementBeforeLoadCm':moved,'positionErrorCm':error,'outcome':str(saves.get_last_location_restore_outcome()),'message':saves.get_last_location_restore_message(),'scope':'Same-layout native save/load in unique test slot; cross-layout test separate'}
    assert saves.get_last_location_restore_outcome()==u.MikdashLocationRestoreOutcome.SAVED_POSITION_RESTORED,'Saved location was not accepted for restoration'
    assert error<3,'Save did not restore verified location'
   if '-takediagnosticstill' in u.SystemLibrary.get_command_line().lower():
    if '-diagnosticneutralsun' in u.SystemLibrary.get_command_line().lower():
     suns=list(u.GameplayStatics.get_all_actors_of_class(world,u.DirectionalLight))
     assert len(suns)==1,'Neutral-sun comparison requires one directional light'
     light=suns[0].get_component_by_class(u.DirectionalLightComponent)
     report['diagnosticSunTemperatureBefore']=light.get_editor_property('temperature')
     light.set_editor_property('use_temperature',True)
     light.set_temperature(6500.0)
     report['diagnosticSunTemperatureAfter']=light.get_editor_property('temperature')
     assert report['diagnosticSunTemperatureAfter']==6500.0
     report['diagnosticSunScope']='PIE-only color comparison; no map or lighting adoption'
    c.set_control_rotation(u.Rotator(pitch=0,yaw=180,roll=0))
    if any(flag in u.SystemLibrary.get_command_line().lower() for flag in ('-diagnosticheikhal','-diagnosticparoches','-diagnosticmount','-diagnostickotel','-diagnosticpaving','-diagnosticfloors')):
     cameras=list(u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor))
     assert cameras,'No PIE camera actor for sanctuary diagnostic'
     camera=cameras[0]
     # Legacy review cameras carry fixed ISO100/f8/1/125 outdoor exposure.
     # This PIE-only diagnostic must use the same global exposure as walking.
     component=camera.get_component_by_class(u.CameraComponent)
     component.set_editor_property('post_process_blend_weight',0.0)
     assert component.get_editor_property('post_process_blend_weight')==0.0
     paroches='-diagnosticparoches' in u.SystemLibrary.get_command_line().lower()
     mount='-diagnosticmount' in u.SystemLibrary.get_command_line().lower()
     kotel='-diagnostickotel' in u.SystemLibrary.get_command_line().lower()
     paving='-diagnosticpaving' in u.SystemLibrary.get_command_line().lower()
     floors='-diagnosticfloors' in command_line.lower()
     position=u.Vector(-5100,0,1081) if paroches else u.Vector(-4000,0,1093)
     if paroches:component.set_field_of_view(55.0)
     if mount:
      position=u.Vector(0,0,75000)
      component.set_field_of_view(60.0)
     if kotel:
      position=u.Vector(-17000,14254,1800)
      component.set_field_of_view(70.0)
     if paving:
      position=u.Vector(10500,12000,180)
      component.set_field_of_view(80.0)
     if floors:
      position=u.Vector(6000,3500,468)
      component.set_field_of_view(80.0)
     if selected48 and not (mount or kotel or paving):
      support=300 if floors else 925
      position=u.Vector(position.x*.96,position.y*.96,support*.96+(position.z-support))
     camera.set_actor_location(position,False,True)
     camera.set_actor_rotation(u.Rotator(pitch=-15 if paving or floors else (-25 if kotel else (-90 if mount else 0)),yaw=-135 if paving else (-9.79 if kotel else (0 if mount else 180)),roll=0),True)
     c.set_view_target_with_blend(camera,0.0)
     state['diagnosticExpectedCamera']=position
     report['diagnosticSubject']='kotel-platform-join' if kotel else ('mount' if mount else ('paroches' if paroches else 'heikhal'))
     if paving:report['diagnosticSubject']='mount-paving'
     if floors:report['diagnosticSubject']='courtyard-floors'
     report['diagnosticCameraPostProcessBlendWeight']=0.0
     report['diagnosticSkylights']=[]
     for sky in u.GameplayStatics.get_all_actors_of_class(world,u.SkyLight):
      skyc=sky.get_component_by_class(u.SkyLightComponent);row={'label':sky.get_actor_label()}
      for key in ('intensity','light_color','source_type','cubemap','real_time_capture','visible','cast_shadows'):
       try:row[key]=str(skyc.get_editor_property(key))
       except Exception:row[key]='unavailable'
      report['diagnosticSkylights'].append(row)
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
   if any(flag in command_line.lower() for flag in ('-comparepaving','-comparejerusalempaving')):
    report.setdefault('pavingComparison',[]).append(dict(report['diagnosticStill']))
    if len(report['pavingComparison'])==1:
     matches=[]
     for actor in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor):
      comp=actor.get_component_by_class(u.StaticMeshComponent)
      mesh=comp.get_editor_property('static_mesh')
      if mesh and mesh.get_path_name()=='/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface.SM_MountPlatform_Surface':matches.append(comp)
     assert len(matches)==1,'Need exactly one PIE platform'
     comp=matches[0];assert comp.get_num_materials()==1
     material_path='/Game/MikdashV3/MaterialReview/JerusalemPavingV2/M_JerusalemPaving_500cm' if '-comparejerusalempaving' in command_line.lower() else '/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_PavingSlabs'
     material=u.load_asset(material_path)
     assert material is not None,'Missing photographic paving material'
     report['pavingMaterialBefore']=comp.get_material(0).get_path_name()
     comp.set_material(0,material)
     assert comp.get_material(0)==material
     report['pavingMaterialCandidate']=material.get_path_name()
     if '-comparejerusalempaving' in command_line.lower():
      folder=ROOT/'Content/MikdashV3/MaterialReview/JerusalemPavingV2'
      report['pavingAssetHashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.uasset')}
      assert len(report['pavingAssetHashes'])==2,'Need exact material and texture bytes'
     report['pavingComparisonScope']='PIE-only component override; no shared asset or saved map change'
     phase('diagnostic_warm');return
   if '-comparefloors' in command_line.lower():
    report.setdefault('floorComparison',[]).append(dict(report['diagnosticStill']))
    if len(report['floorComparison'])==1:
     import release_jerusalem_floor_slabs as slabs
     floor_plan=slabs.plan();rows={r['mesh']:r for r in floor_plan['rows']}
     matched={}
     for actor in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor):
      comp=actor.get_component_by_class(u.StaticMeshComponent);mesh=comp.get_editor_property('static_mesh')
      package=mesh.get_path_name().split('.')[0] if mesh else ''
      if package not in rows:continue
      assert package not in matched,'Duplicate floor mesh'
      row=rows[package]
      assert actor.get_name()==row['actorName'] and comp.get_name()==row['componentName'],'Floor identity changed'
      assert comp.get_num_materials()==1 and comp.get_material(0).get_path_name()==row['nativeMaterials'][0],'Original floor material changed'
      matched[package]=comp
     assert set(matched)==set(rows) and len(matched)==57,'Missing exact floor scope'
     material=u.load_asset(slabs.MATERIAL);assert material
     for comp in matched.values():
      comp.set_material(0,material);assert comp.get_material(0)==material
     report['floorMeshes']=sorted(matched)
     report['floorMaterialCandidate']=material.get_path_name()
     report['floorAssetHashes']={str(slabs.assetfile(p)):slabs.sha(slabs.assetfile(p)) for p in (slabs.MATERIAL,slabs.TEXTURE)}
     phase('diagnostic_warm');return
   if any(f in command_line.lower() for f in ('-comparedaylight','-comparecooldaylight')):
    report.setdefault('daylightComparison',[]).append(dict(report['diagnosticStill']))
    if len(report['daylightComparison'])==1:
     suns=list(u.GameplayStatics.get_all_actors_of_class(world,u.DirectionalLight))
     skies=list(u.GameplayStatics.get_all_actors_of_class(world,u.SkyLight))
     assert len(suns)==1 and len(skies)==1,'Daylight comparison requires exactly one sun and sky'
     sun=suns[0];light=sun.get_component_by_class(u.DirectionalLightComponent);sky=skies[0].get_component_by_class(u.SkyLightComponent)
     rot=sun.get_actor_rotation()
     report['daylightBefore']={'sunIntensity':light.get_editor_property('intensity'),'temperature':light.get_editor_property('temperature'),'useTemperature':light.get_editor_property('use_temperature'),'rotation':[rot.pitch,rot.yaw,rot.roll],'skyIntensity':sky.get_editor_property('intensity')}
     report['daylightExposureBefore']=exposure_snapshot(world)
     cool_only='-comparecooldaylight' in command_line.lower()
     light.set_editor_property('use_temperature',True);light.set_temperature(6500.0)
     if not cool_only:
      light.set_intensity(45000.0)
      sun.set_actor_rotation(u.Rotator(pitch=-50,yaw=rot.yaw,roll=rot.roll),True)
     sky.set_intensity(1.3)
     report['daylightPreset']='cool_source_more_fill' if cool_only else 'higher_sun_brighter_source'
     rot=sun.get_actor_rotation()
     report['daylightCandidate']={'sunIntensity':light.get_editor_property('intensity'),'temperature':light.get_editor_property('temperature'),'useTemperature':light.get_editor_property('use_temperature'),'rotation':[rot.pitch,rot.yaw,rot.roll],'skyIntensity':sky.get_editor_property('intensity')}
     report['daylightScope']='PIE-only daylight study, not an ephemeris or a saved preset'
     phase('diagnostic_warm');return
    report['daylightExposureAfter']=exposure_snapshot(world)
    assert report['daylightExposureAfter']==report['daylightExposureBefore'],'Exposure settings changed during comparison'
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
 if '-comparefloors' in command_line.lower():
  import release_jerusalem_floor_slabs as slabs
  candidate=u.load_asset(slabs.MATERIAL);assert candidate
  report['candidateShaderErrors']=list(u.MaterialEditingLibrary.recompile_material(candidate))
  assert not report['candidateShaderErrors'],'Floor material compile failed'
  report['candidateMaterialStatistics']=str(u.MaterialEditingLibrary.get_statistics(candidate))
 if '-comparejerusalempaving' in command_line.lower():
  candidate=u.load_asset('/Game/MikdashV3/MaterialReview/JerusalemPavingV2/M_JerusalemPaving_500cm')
  assert candidate is not None,'Missing paving candidate'
  report['candidateShaderErrors']=list(u.MaterialEditingLibrary.recompile_material(candidate))
  assert not report['candidateShaderErrors'],'Candidate shader compilation failed'
  # Engine source: GetStatistics finishes this material's shader compilation only.
  # Avoid waiting for the entire city's unrelated mesh derived-data queue.
  stats=u.MaterialEditingLibrary.get_statistics(candidate)
  report['candidateMaterialStatistics']=str(stats)
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

"""Actual main-map40second scene preview to PNG, for local MP4 encoding.
Dedicated real-RHI editor only, isolated AstraProbe_ save overrides required.
Set SHOTS before launch; each is8seconds with start/end XYZ, rotation [pitch,yaw,roll], fov.
No map save, no source/old asset writes, no overwrite. GameModeBase avoids the game menu.
"""
import hashlib,json,os,struct,time,math,shutil
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAP='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
NAMESPACE='/Game/MikdashV3/ShareVideo_20260909_V5'
OUTPUT=ROOT.parent/'ShareVideo-20260909-V5'
WIDTH,HEIGHT=896,504
FRAMES=OUTPUT/'Frames'
FPS=24
SHOT_SECONDS=8
SHOTS=[
 {'name':'aerial','start':[16000,-15000,13000],'end':[12000,-12000,11000],'lookTarget':[-1500,0,1600],'fov':60},
 {'name':'courtyard','start':[7600,0,468],'end':[6000,0,468],'rotation':[0,180,0],'fov':75},
 {'name':'Kotel','start':[-16750,13700,-700],'end':[-16600,14000,-700],'lookTarget':[-14800,13800,-100],'fov':65},
 {'name':'Heikhal','start':[-3900,-100,1093],'end':[-4100,100,1093],'lookTarget':[-5350,0,1200],'fov':75},
 {'name':'Aron','start':[-5850,-140,1093],'end':[-5900,140,1093],'lookTarget':[-6200,0,1063.5],'fov':50}]
def rotation_at(shot,point):
 if 'rotation' in shot:return shot['rotation']
 dx,dy,dz=[shot['lookTarget'][i]-point[i] for i in range(3)]
 return [math.degrees(math.atan2(dz,math.hypot(dx,dy))),math.degrees(math.atan2(dy,dx)),0.0]


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def maps():return {str(p):sha(p) for p in (ROOT/'Content').rglob('*.umap')}
def saves():
 dirs=[ROOT/'Saved/SaveGames',Path(os.environ.get('LOCALAPPDATA','C:/nonexistent'))/'MikdashCourtyardV3/Saved/SaveGames']
 return {str(p):sha(p) for d in dirs if d.exists() for p in d.glob('*.sav') if not p.name.startswith('AstraProbe_')}
def run(shots=None):
 import unreal as u
 global CAPTURE, CALLBACK, TICK_HANDLE, REPORT, START, FINISHED
 shots=SHOTS if shots is None else shots
 assert len(shots)==5,'Five coordinator shots required'
 for shot in shots:
  assert set(shot) in ({'name','start','end','rotation','fov'},{'name','start','end','lookTarget','fov'}) and len(shot['start'])==3 and len(shot['end'])==3
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 OUTPUT.mkdir(parents=True,exist_ok=True);receipt=OUTPUT/('render-'+stamp+'.json')
 REPORT={'status':'starting','map':MAP,'pid':os.getpid(),'shots':shots,'fps':FPS,'expectedFrames':960,'errors':[],
  'mapsBefore':maps(),'savesBefore':saves(),'scope':'Actual scene actors rendered with sequence cameras, GameModeBase; not packaged gameplay/input acceptance'}
 def write():receipt.write_text(json.dumps(REPORT,indent=2)+'\n',encoding='utf-8')
 write();START=time.monotonic();FINISHED=False;TICK_HANDLE=None
 def done(success):
  global FINISHED
  if FINISHED:return
  FINISHED=True
  try:
   files=sorted(FRAMES.glob('*.png'));REPORT['frameCount']=len(files)
   bad=[]
   for path in files:
    with path.open('rb') as f:header=f.read(24)
    if len(header)!=24 or header[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',header[16:24])!=(WIDTH,HEIGHT):bad.append(path.name)
   REPORT['badImageHeaders']=bad;REPORT['captureReportedSuccess']=bool(success)
   REPORT['mapsUnchanged']=maps()==REPORT['mapsBefore'];REPORT['originalSavesUnchanged']=saves()==REPORT['savesBefore']
   REPORT['status']='frames_complete_visual_review_pending' if success and len(files)==960 and not bad and REPORT['mapsUnchanged'] and REPORT['originalSavesUnchanged'] else 'failed_or_incomplete'
   write()
  finally:
   if TICK_HANDLE is not None:u.unregister_slate_post_tick_callback(TICK_HANDLE)
   u.SystemLibrary.quit_editor()
 def tick(dt):
  if not FINISHED:
   world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
   if world:
    front=u.MikdashFrontEnd.get(world);cine=u.MikdashCinematics.get(world)
    if (front and front.is_front_end_visible()) or (cine and cine.is_playing()):
     REPORT['errors'].append('Runtime menu/intro interfered with movie capture');done(False);return
    REPORT['runtimeNoMenuIntroSamples']=REPORT.get('runtimeNoMenuIntroSamples',0)+1
  if not FINISHED and time.monotonic()-START>1800:
   REPORT['errors'].append('1800second wall watchdog exceeded');done(False)
 try:
  import sys
  sys.path.insert(0,str(ROOT/'Scripts'))
  from release_surface_soft import inventory
  inventory()
  assert Path(u.Paths.project_dir()).resolve()==ROOT
  cmd=u.SystemLibrary.get_command_line()
  assert 'SlotNamePrefix=AstraProbe_' in cmd and 'SaveSlot=AstraProbe_' in cmd,'Save isolation required'
  assert '[/Script/MikdashRuntime.MikdashSettingsSubsystem]:bApplyGraphicsToEngine=False' in cmd,'Settings subsystem must not resize the capture viewport'
  for section in ('MikdashFrontEnd','MikdashCinematics'):
   assert '[/Script/MikdashRuntime.'+section+']:bEnabled=False' in cmd,'Capture must disable '+section+' via process-only ini override'
  ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
  assert not ed.get_game_world(),'PIE already running'
  assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'Dirty packages'
  assert ed.get_editor_world().get_outermost().get_name()==MAP,'Exact main map must be open'
  capture_cvars={'r.ScreenPercentage':100,'r.SecondaryScreenPercentage.GameViewport':100,'r.DynamicRes.OperationMode':0,'r.AntiAliasingMethod':4,'r.TemporalAA.Upsampling':1}
  for key,value in capture_cvars.items():u.SystemLibrary.execute_console_command(ed.get_editor_world(),key+' '+str(value))
  REPORT['captureCVars']={key:u.SystemLibrary.get_console_variable_float_value(key) for key in capture_cvars}
  assets=u.get_editor_subsystem(u.EditorAssetSubsystem)
  assert not assets.does_directory_exist(NAMESPACE) and not (ROOT/'Content'/NAMESPACE[6:]).exists(),'Create-once namespace already exists'
  assert not FRAMES.exists(),'Fresh Frames output required'
  checkpoint=ROOT.parent/'ReviewCheckpoints'/('ShareVideo-'+stamp)
  checkpoint.mkdir(parents=True,exist_ok=False)
  mapfile=ROOT/'Content'/(MAP[6:]+'.umap')
  shutil.copy2(mapfile,checkpoint/'Walkthrough.umap')
  assert sha(checkpoint/'Walkthrough.umap')==sha(mapfile),'Map checkpoint differs'
  REPORT['checkpoint']=str(checkpoint);write()
  FRAMES.mkdir(parents=True,exist_ok=False)
  seq=u.AssetToolsHelpers.get_asset_tools().create_asset('SEQ_ShareCurrent',NAMESPACE,u.LevelSequence,u.LevelSequenceFactoryNew())
  assert seq is not None
  seq.set_display_rate(u.FrameRate(FPS,1));seq.set_playback_start(0);seq.set_playback_end(960)
  cuts=seq.add_track(u.MovieSceneCameraCutTrack)
  for index,shot in enumerate(shots):
   start=index*192;end=start+192
   initial=rotation_at(shot,shot['start'])
   template=actors.spawn_actor_from_class(u.CameraActor,u.Vector(*shot['start']),u.Rotator(pitch=initial[0],yaw=initial[1],roll=initial[2]),transient=True)
   assert template
   try:
    component=template.get_component_by_class(u.CameraComponent)
    component.set_editor_property('post_process_blend_weight',0.0);component.set_editor_property('field_of_view',float(shot['fov']))
    component.set_editor_property('aspect_ratio',1280.0/720.0)
    binding=seq.add_spawnable_from_instance(template)
   finally:actors.destroy_actor(template)
   section=binding.add_track(u.MovieScene3DTransformTrack).add_section();section.set_range(start,end)
   channels=section.get_all_channels();assert len(channels)>=6
   # Transform channels are XYZ followed by roll,pitch,yaw.
   for frame,point in [(start,shot['start']),(end-1,shot['end'])]:
    angles=rotation_at(shot,point)
    angles=[initial[i]+((angles[i]-initial[i]+180.0)%360.0-180.0) for i in range(3)]
    rotation=[angles[2],angles[0],angles[1]]
    for c,value in zip(channels[:6],list(point)+rotation):c.add_key(u.FrameNumber(frame),float(value),interpolation=u.MovieSceneKeyInterpolation.LINEAR)
   for c in channels[6:9]:c.set_default(1.0)
   cut=cuts.add_section();cut.set_range(start,end)
   identity=u.MovieSceneObjectBindingID();identity.set_editor_property('guid',binding.get_id());cut.set_camera_binding_id(identity)
  assert assets.save_loaded_asset(seq,only_if_is_dirty=False),'Sequence save refused'
  seqfile=ROOT/'Content'/NAMESPACE[6:]/'SEQ_ShareCurrent.uasset'
  REPORT['sequence']=seq.get_path_name();REPORT['sequenceSha256']=sha(seqfile)
  assert maps()==REPORT['mapsBefore'],'Map bytes changed while authoring'
  CAPTURE=u.AutomatedLevelSequenceCapture();cs=CAPTURE.settings
  cs.output_directory=u.DirectoryPath(str(FRAMES));cs.output_format='frame_{frame}';cs.overwrite_existing=False
  cs.use_relative_frame_numbers=True;cs.handle_frames=0;cs.zero_pad_frame_numbers=5
  cs.use_custom_frame_rate=True;cs.custom_frame_rate=u.FrameRate(FPS,1)
  cs.resolution.res_x=WIDTH;cs.resolution.res_y=HEIGHT
  cs.game_mode_override=u.load_class(None,'/Script/Engine.GameModeBase')
  cs.enable_texture_streaming=True;cs.cinematic_engine_scalability=False;cs.cinematic_mode=True
  cs.allow_movement=False;cs.allow_turning=False;cs.show_player=False;cs.show_hud=False
  CAPTURE.use_separate_process=False;CAPTURE.close_editor_when_capture_starts=False
  CAPTURE.additional_command_line_arguments='';CAPTURE.inherited_command_line_arguments=''
  CAPTURE.use_custom_start_frame=False;CAPTURE.use_custom_end_frame=False
  CAPTURE.custom_start_frame=u.FrameNumber(0);CAPTURE.custom_end_frame=u.FrameNumber(959)
  CAPTURE.warm_up_frame_count=24;CAPTURE.delay_before_warm_up=5.0;CAPTURE.delay_before_shot_warm_up=3.0
  CAPTURE.write_edit_decision_list=False;CAPTURE.level_sequence_asset=u.SoftObjectPath(seq.get_path_name())
  CAPTURE.set_image_capture_protocol_type(u.load_class(None,'/Script/MovieSceneCapture.ImageSequenceProtocol_PNG'))
  CAPTURE.get_image_capture_protocol().compression_quality=100
  burn=u.LevelSequenceBurnInOptions();burn.use_burn_in=False;CAPTURE.burn_in_options=burn
  CALLBACK=u.OnRenderMovieStopped();CALLBACK.bind_callable(done)
  TICK_HANDLE=u.register_slate_post_tick_callback(tick)
  REPORT['status']='rendering';write()
  accepted=u.SequencerTools.render_movie(CAPTURE,CALLBACK)
  if accepted is False:raise RuntimeError('SequencerTools refused capture')
 except Exception as error:
  REPORT['errors'].append(repr(error));write();done(False);raise
if __name__=='__main__':run()

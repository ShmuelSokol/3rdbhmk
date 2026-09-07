"""Continuous walk into source east jamb, hold contact, retreat, return. No teleport."""
import unreal,json,time,math,hashlib
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert root==Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
l=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert not e.get_game_world() and not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
assert e.get_editor_world().get_path_name().split('.')[0]=='/Game/MikdashV3/Maps/Courtyard'
mp=root/'SourceAssets/architecture-manifest.json'
m=json.loads(mp.read_text(encoding='utf-8-sig'))
wall=next(r for r in m['meshes'] if r['assetName']=='SM_0138_architecture_Inner_eastern_gate_wall_jamb_1')
assert wall['expectedBoundsUnrealCm']=={'min':[2500.,250.,500.],'max':[2800.,2800.,3500.]}
settings=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.LevelEditorPlaySettings'))
oldmouse=settings.get_editor_property('GameGetsMouseControl')
oldthrottle=unreal.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
output=root/'SourceAssets/runtime-review/east-jamb-contact-walk.json'
r={'status':'running','scope':'Synthetic CharacterMovement into one source wall, sustained contact and retreat; not universal collision/access or physical input acceptance','sourceWall':wall['assetName'],'sourceBounds':wall['expectedBoundsUnrealCm'],'manifestSha256':hashlib.sha256(mp.read_bytes()).hexdigest(),'samples':[],'reached':[],'errors':[]}
start=time.monotonic();phase=0;holdstart=None;handle=None;done=False;lastsample=0;lastprogress=start;lastpos=None

def finish(status):
 global done
 done=True;r['status']=status
 try:l.editor_request_end_play()
 finally:
  settings.set_editor_property('GameGetsMouseControl',oldmouse)
  unreal.SystemLibrary.execute_console_command(e.get_editor_world(),'Slate.bAllowThrottling '+str(oldthrottle))
  unreal.unregister_slate_post_tick_callback(handle)
  r['stopRequested']=True;output.write_text(json.dumps(r,indent=2))

def tick(delta):
 global phase,holdstart,lastsample,lastprogress,lastpos
 if done:return
 try:
  now=time.monotonic();elapsed=now-start
  if elapsed>60:raise RuntimeError('Timeout')
  w=e.get_game_world();p=unreal.GameplayStatics.get_player_pawn(w,0) if w else None
  if not p:
   if elapsed>15:raise RuntimeError('No pawn')
   return
  assert isinstance(p,unreal.Character)
  t=unreal.GameplayStatics.get_time_seconds(w)
  if t<.05:
   if elapsed>15:raise RuntimeError('Game clock did not advance')
   lastprogress=now;return
  pos=p.get_actor_location();xyz=[pos.x,pos.y,pos.z];v=p.get_velocity()
  if not all(math.isfinite(x) for x in xyz) or not(1900<pos.x<2501 and -100<pos.y<1700 and 480<pos.z<700):raise RuntimeError('Safety envelope exceeded')
  cm=p.get_component_by_class(unreal.CharacterMovementComponent)
  if not cm.is_walking():raise RuntimeError('Lost grounded walking')
  cap=p.get_component_by_class(unreal.CapsuleComponent);radius=cap.get_scaled_capsule_radius()
  if abs(pos.z-cap.get_scaled_capsule_half_height()-502)>3:raise RuntimeError('Unexpected floor support')
  if now-lastsample>.1:
   r['samples'].append({'seconds':elapsed,'gameSeconds':t,'phase':phase,'positionCm':xyz,'velocity':[v.x,v.y,v.z]});lastsample=now
  if elapsed<2:return
  tx,ty=[(2100,1500),(2700,1500),(2100,1500),(2100,0)][phase]
  if phase==1:
   contact=2500-radius
   if pos.x>contact+2:raise RuntimeError('Capsule penetrated source wall plane')
   if abs(pos.x-contact)<3 and abs(pos.y-1500)<35 and math.hypot(v.x,v.y)<2:
    if holdstart is None:holdstart=t
    if t-holdstart>=3:
     r['reached'].append({'phase':phase,'positionCm':xyz,'heldGameSeconds':t-holdstart,'expectedContactX':contact})
     phase=2;tx,ty=2100,1500;lastprogress=now;lastpos=xyz
   elif holdstart is not None:raise RuntimeError('Wall contact did not remain stable')
  elif math.hypot(pos.x-tx,pos.y-ty)<25:
   r['reached'].append({'phase':phase,'positionCm':xyz});phase+=1;lastprogress=now;lastpos=xyz
   if phase==4:finish('passed_contact_hold_retreat_return');return
   tx,ty=[(2100,1500),(2700,1500),(2100,1500),(2100,0)][phase]
  if lastpos is None or math.dist(xyz,lastpos)>15:lastpos=xyz;lastprogress=now
  elif now-lastprogress>8 and not(phase==1 and holdstart is not None):raise RuntimeError('Unexpected stuck movement')
  dx,dy=tx-pos.x,ty-pos.y;n=math.hypot(dx,dy)
  p.add_movement_input(unreal.Vector(dx/n,dy/n,0),1.,True)
 except Exception as ex:
  r['errors'].append(str(ex));finish('failed')

settings.set_editor_property('GameGetsMouseControl',False)
unreal.SystemLibrary.execute_console_command(e.get_editor_world(),'Slate.bAllowThrottling 0')
output.write_text(json.dumps(r));handle=unreal.register_slate_post_tick_callback(tick)
try:l.editor_request_begin_play()
except Exception:
 finish('failed_start');raise

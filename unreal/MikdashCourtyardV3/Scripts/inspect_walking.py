"""Inert UE 5.7 editor-side PIE inspection; never moves pawn or injects input.
exec(open(PATH).read()); walk_snapshot('initial'); begin_walk_recording(12)
Return focus to PIE, manually hold W briefly/release. stop_walk_recording() optional.
Not a packaged-runtime Python solution. Optional diagnose_routes() only traces.
"""
from pathlib import Path
import json, math, time, uuid
import unreal
_WALK_RECORDING=None

def _vec(v): return [float(v.x),float(v.y),float(v.z)]
def _path(o): return o.get_path_name() if o else None

def _live():
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if world is None: raise RuntimeError('Start PIE first; editor-world pawn is not runtime evidence')
    pawn=unreal.GameplayStatics.get_player_pawn(world,0)
    if not isinstance(pawn,unreal.Character): raise RuntimeError('Player zero is not a possessed Character; no flying-pawn substitution')
    controller=unreal.GameplayStatics.get_player_controller(world,0)
    if controller is None or pawn.get_controller()!=controller: raise RuntimeError('Player possession mismatch')
    return world,pawn,controller

def _data(label):
    world,pawn,controller=_live()
    movement=pawn.get_component_by_class(unreal.CharacterMovementComponent)
    capsule=pawn.get_component_by_class(unreal.CapsuleComponent)
    if movement is None or capsule is None: raise RuntimeError('Character movement/capsule absent')
    rotation=pawn.get_actor_rotation();control=controller.get_control_rotation()
    return dict(label=label,monotonicSeconds=time.monotonic(),world=_path(world),pawn=_path(pawn),pawnClass=_path(pawn.get_class()),controllerClass=_path(controller.get_class()),positionCm=_vec(pawn.get_actor_location()),velocityCmPerSecond=_vec(pawn.get_velocity()),movementMode=str(movement.get_editor_property('movement_mode')),customMovementMode=int(movement.get_editor_property('custom_movement_mode')),isWalking=bool(movement.is_walking()),isFalling=movement.get_editor_property('movement_mode')==unreal.MovementMode.MOVE_FALLING,maxStepHeightCm=float(movement.get_editor_property('max_step_height')),walkableFloorAngleDegrees=float(movement.get_walkable_floor_angle()),maxWalkSpeedCmPerSecond=float(movement.get_editor_property('max_walk_speed')),capsuleHalfHeightCm=float(capsule.get_scaled_capsule_half_height()),capsuleRadiusCm=float(capsule.get_scaled_capsule_radius()),actorRotation=dict(roll=rotation.roll,pitch=rotation.pitch,yaw=rotation.yaw),controlRotation=dict(roll=control.roll,pitch=control.pitch,yaw=control.yaw),lastMovementInput=_vec(pawn.get_last_movement_input_vector()))

def _write(prefix,payload):
    directory=Path(unreal.Paths.project_dir())/'SourceAssets/runtime-review'
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/(prefix+'-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:6]+'.json')
    path.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    unreal.log('Runtime inspection: '+str(path));return str(path)

def walk_snapshot(label='manual snapshot'):
    data=_data(str(label));_write('snapshot',data);unreal.log(str(data));return data

def stop_walk_recording(reason='manual stop'):
    global _WALK_RECORDING
    record=_WALK_RECORDING
    if record is None:return None
    _WALK_RECORDING=None
    unreal.unregister_slate_post_tick_callback(record['handle'])
    samples=record['samples'];first=samples[0];last=samples[-1]
    delta=[last['positionCm'][i]-first['positionCm'][i] for i in range(3)]
    payload=dict(status=reason,scope='Observed manually controlled PIE; no input injection/teleport; not a cook or ceremony verification',samples=samples,deltaPositionCm=delta,maxObservedSpeedCmPerSecond=max(math.sqrt(sum(v*v for v in s['velocityCmPerSecond'])) for s in samples),movementModes=sorted({s['movementMode'] for s in samples}),error=record.get('error'))
    return _write('manual-walk',payload)

def begin_walk_recording(seconds=12.0,sample_interval=.1):
    global _WALK_RECORDING
    if _WALK_RECORDING is not None:raise RuntimeError('Recording already active; stop it before starting another')
    if not(1<=seconds<=30 and .05<=sample_interval<=1):raise ValueError('Duration 1–30s; interval .05–1s')
    first=_data('initial before manual input');started=time.monotonic()
    record=dict(samples=[first],started=started,last=started,handle=None)
    _WALK_RECORDING=record
    def tick(_delta):
        if _WALK_RECORDING is not record:return
        now=time.monotonic()
        try:
            if now-record['last']>=sample_interval:
                sample=_data('manual input observation')
                if sample['pawn']!=first['pawn'] or sample['world']!=first['world']:raise RuntimeError('Pawn/world changed during recording')
                record['samples'].append(sample);record['last']=now
            if now-started>=seconds:stop_walk_recording('duration completed')
        except Exception as exc:
            record['error']=str(exc);stop_walk_recording('stopped: runtime context/error')
    try:record['handle']=unreal.register_slate_post_tick_callback(tick)
    except Exception:
        _WALK_RECORDING=None;raise
    unreal.log('Recording started. Return focus to PIE; manually press/release movement keys. No input is generated by this helper.')
    return first

def diagnose_routes(route_file):
    """Read-only point support + raw capsule clearance; no pawn placement.
    Full capsule collision at stair/ramp samples is diagnostic, not automatic fail:
    CharacterMovement performs step-up/slope resolution that this static test does not.
    """
    world,pawn,_controller=_live();cap=pawn.get_component_by_class(unreal.CapsuleComponent)
    half=float(cap.get_scaled_capsule_half_height());radius=float(cap.get_scaled_capsule_radius())
    routes=json.loads(Path(route_file).read_text(encoding='utf-8-sig'))
    out=[]
    for route in routes['routes']:
        checks=[]
        for point in route['points']:
            x,y,hint=point['floorPositionCm'];top=hint+60;low=hint-60
            def hit(z):
                return unreal.SystemLibrary.line_trace_single_by_profile(world_context_object=world,start=unreal.Vector(x,y,top),end=unreal.Vector(x,y,z),profile_name='Pawn',trace_complex=False,actors_to_ignore=[pawn],draw_debug_type=unreal.DrawDebugTrace.NONE,ignore_self=True) is not None
            item=dict(label=point['label'],sourceFloorPositionCm=[x,y,hint])
            if not hit(low):item['support']='no collision floor within source +/-60cm bracket'
            elif hit(top-.01):item['support']='probe origin blocked; review obstacle/bracket'
            else:
                lo,hi=low,top
                for _ in range(17):
                    mid=(lo+hi)/2
                    if hit(mid):lo=mid
                    else:hi=mid
                floor=(lo+hi)/2;z=floor+half+2
                blocked=unreal.SystemLibrary.capsule_trace_single_by_profile(world_context_object=world,start=unreal.Vector(x,y,z+.1),end=unreal.Vector(x,y,z),radius=radius,half_height=half,profile_name='Pawn',trace_complex=False,actors_to_ignore=[pawn],draw_debug_type=unreal.DrawDebugTrace.NONE,ignore_self=True) is not None
                item.update(support='collision floor found',measuredFloorCm=floor,sourceFloorErrorCm=floor-hint,rawStaticCapsuleBlocked=blocked)
            checks.append(item)
        out.append(dict(name=route['name'],access=route['access'],checks=checks))
    return _write('route-collision-points',dict(scope='Read-only sparse point traces, not continuous walkability, character step-up, visitor-access enforcement or manual input test',capsuleHalfHeightCm=half,capsuleRadiusCm=radius,routes=out))

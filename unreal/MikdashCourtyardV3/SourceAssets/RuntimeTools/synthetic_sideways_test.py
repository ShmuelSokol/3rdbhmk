"""Inert editor-only SYNTHETIC Enhanced Input test; never physical keyboard proof.
exec(open(PATH).read()); start_synthetic_sideways_test()
Fixed 2 s maximum, 200 cm observed displacement guard. stop_synthetic_sideways_test()
can release early. Do not provide other input or pause PIE during this test.
"""
import json,math,time,uuid
from pathlib import Path
import unreal
if '_SYNTHETIC_SIDEWAYS' not in globals():_SYNTHETIC_SIDEWAYS=None
_START='Input.+key Gamepad_Left2D X=0.35 Y=0'
_STOP='Input.-key Gamepad_Left2D'
_EXPECTED='/Game/MikdashV3/Gameplay/BP_MikdashWalker.BP_MikdashWalker_C'

def _syn_vector(v):return [float(v.x),float(v.y),float(v.z)]
def _syn_context():
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if world is None:raise RuntimeError('Start PIE first')
    pawn=unreal.GameplayStatics.get_player_pawn(world,0)
    pc=unreal.GameplayStatics.get_player_controller(world,0)
    if not isinstance(pawn,unreal.Character) or pawn.get_class().get_path_name()!=_EXPECTED:
        raise RuntimeError('Requires the actual BP_MikdashWalker Character')
    if pc is None or pawn.get_controller()!=pc:raise RuntimeError('Possession mismatch')
    return world,pawn,pc

def _syn_sample(pawn,pc):
    m=pawn.get_component_by_class(unreal.CharacterMovementComponent)
    if m is None:raise RuntimeError('CharacterMovement absent')
    return dict(t=time.monotonic(),positionCm=_syn_vector(pawn.get_actor_location()),velocityCmPerSecond=_syn_vector(pawn.get_velocity()),movementMode=str(m.get_editor_property('movement_mode')),walking=bool(m.is_walking()),lastMovementInput=_syn_vector(pawn.get_last_movement_input_vector()),controlYawDegrees=float(pc.get_control_rotation().yaw))

def stop_synthetic_sideways_test(reason='manual stop'):
    global _SYNTHETIC_SIDEWAYS
    r=_SYNTHETIC_SIDEWAYS
    if r is None:return None
    r['stopping']=True
    errors=[];attempts=[]
    # Original context first; also release in a changed current world if present.
    contexts=[(r['world'],r['pc'],'original PIE')]
    try:
        current=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if current is not None and current!=r['world']:
            contexts.append((current,unreal.GameplayStatics.get_player_controller(current,0),'current PIE'))
    except Exception as exc:errors.append('Context lookup: '+str(exc))
    released=False
    for world,pc,label in contexts:
        try:
            unreal.SystemLibrary.execute_console_command(world_context_object=world,command=_STOP,specific_player=pc)
            attempts.append(label+': release command dispatched');released=True
        except Exception as exc:errors.append(label+': '+str(exc))
    if not released:
        try:
            editor_world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            unreal.SystemLibrary.execute_console_command(world_context_object=editor_world,command=_STOP)
            attempts.append('editor fallback: release command dispatched');released=True
        except Exception as exc:errors.append('Editor fallback: '+str(exc))
    if r.get('handle') is not None:
        try:unreal.unregister_slate_post_tick_callback(r['handle']);r['handle']=None
        except Exception as exc:errors.append('Unregister: '+str(exc))
    samples=r['samples'];first=samples[0];last=samples[-1]
    delta=[last['positionCm'][i]-first['positionCm'][i] for i in range(3)]
    receipt=dict(evidenceType='SYNTHETIC_GAMEPAD_INPUT_NOT_PHYSICAL_KEYBOARD',reason=reason,engine=unreal.SystemLibrary.get_engine_version(),startCommand=_START,releaseCommand=_STOP,durationLimitSeconds=2.0,displacementGuardCm=200.0,elapsedWallSeconds=time.monotonic()-r['started'],samples=samples,deltaPositionCm=delta,maxObservedSpeedCmPerSecond=max(math.sqrt(sum(v*v for v in s['velocityCmPerSecond']))for s in samples),releaseAttempts=attempts,releaseDispatchReturned=released,releaseEffectVerified=False,errors=errors,testError=r.get('error'),scope='Tests configured Enhanced Input mapping and Character movement via simulated gamepad key. No teleport, actor movement command, direct AddMovementInput or configuration edits. Not physical W, full-route, visitor-access, cooked-build or production-quality verification.')
    try:
        r['receipt'].write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        unreal.log('SYNTHETIC test receipt: '+str(r['receipt']))
    finally:
        # Retain a failed-release guard so another start is refused until stop retries.
        if released:_SYNTHETIC_SIDEWAYS=None
    if not released:unreal.log_error('Release dispatch failed. Run Input.-key Gamepad_Left2D manually; inspect receipt before another test.')
    return receipt

def start_synthetic_sideways_test():
    global _SYNTHETIC_SIDEWAYS
    if _SYNTHETIC_SIDEWAYS is not None or globals().get('_WALK_RECORDING') is not None:
        raise RuntimeError('Another recording/test is active; stop it first')
    world,pawn,pc=_syn_context();first=_syn_sample(pawn,pc)
    cap=pawn.get_component_by_class(unreal.CapsuleComponent)
    if cap is None:raise RuntimeError('Capsule absent')
    radius=float(cap.get_scaled_capsule_radius());x,y,z=first['positionCm']
    if not(1700+radius<=x<=2500-radius and abs(y)<=1800):
        raise RuntimeError('Requires visitor strip X1700..2500cm, capsule margin and 200cm north/south test reserve')
    if not first['walking'] or math.sqrt(sum(v*v for v in first['velocityCmPerSecond']))>1:
        raise RuntimeError('Start stationary on the courtyard floor')
    if abs(z-float(cap.get_scaled_capsule_half_height())-500)>5:
        raise RuntimeError('Requires stable visitor floor Z500cm')
    directory=Path(unreal.Paths.project_dir())/'SourceAssets/runtime-review';directory.mkdir(parents=True,exist_ok=True)
    receipt=directory/('SYNTHETIC-sideways-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:6]+'.json')
    # Confirm the receipt can be written before activating input.
    receipt.write_text(json.dumps(dict(evidenceType='SYNTHETIC',status='prepared_not_started'))+'\n')
    r=dict(world=world,pawn=pawn,pc=pc,started=time.monotonic(),samples=[first],receipt=receipt,handle=None,stopping=False)
    _SYNTHETIC_SIDEWAYS=r
    def tick(_dt):
        if _SYNTHETIC_SIDEWAYS is not r or r['stopping']:return
        try:
            cw,cp,cc=_syn_context()
            if cw!=world or cp!=pawn or cc!=pc:raise RuntimeError('PIE world/pawn/controller changed')
            s=_syn_sample(pawn,pc);r['samples'].append(s)
            distance=math.dist(s['positionCm'],first['positionCm']);sx,sy,_sz=s['positionCm']
            if distance>=200:stop_synthetic_sideways_test('200cm observed displacement guard');return
            if not(1700+radius<=sx<=2500-radius and abs(sy)<2000):stop_synthetic_sideways_test('visitor strip margin guard');return
            if not s['walking']:stop_synthetic_sideways_test('left Walking mode');return
            if time.monotonic()-r['started']>=2:stop_synthetic_sideways_test('2 second duration reached')
        except Exception as exc:
            r['error']=str(exc);stop_synthetic_sideways_test('failure/world change')
    try:
        # Install cleanup callback BEFORE dispatching any simulated input.
        r['handle']=unreal.register_slate_post_tick_callback(tick)
        unreal.SystemLibrary.execute_console_command(world_context_object=world,command=_START,specific_player=pc)
    except Exception as exc:
        r['error']=str(exc);stop_synthetic_sideways_test('start failed');raise
    unreal.log('SYNTHETIC gamepad sideways test active for at most 2 seconds of responsive editor ticks. Do not touch movement/look input.')
    return str(receipt)

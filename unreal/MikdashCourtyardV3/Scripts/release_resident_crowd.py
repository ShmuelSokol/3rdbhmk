"""Read-only audit by default; opt-in timestamped resident review-copy placement.
Requires compiled native population bridge. Never edits the source map. Separate
finite probe initializes only an explicitly selected, already-running review game.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/'Scripts/release_place_assets.spec.json'
HEADER=ROOT/'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashResidentCharacter.h'
ADAPTER=ROOT/'Plugins/MikdashRuntime/Source/MikdashRuntime/Private/MikdashResidentCharacter.cpp'
RUNTIME=ROOT/'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/ResidentCrowdRuntime.h'
CONTROLLER=ROOT/'Plugins/MikdashRuntime/Source/MikdashRuntime/Private/MikdashPlayerController.cpp'
POPULATION_HEADER=HEADER.with_name('MikdashResidentPopulation.h')
POPULATION_CPP=ADAPTER.with_name('MikdashResidentPopulation.cpp')
BUILD_LOG=ROOT.parent/'Astra-Dove-Resident-Editor-Build.log'
BUILD_DLL=ROOT/'Plugins/MikdashRuntime/Binaries/Win64/UnrealEditor-MikdashRuntime.dll'
PLACEMENT=ROOT/'SourceAssets/IntegratedReviewV2/release-placement-20260907T161402552292Z.json'
TARGET='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
MISSING=[
 'A world/game-owned C++ coordinator must own one TSharedPtr<MikdashCrowd::Runtime>, configure five stable identities and tick its clock once per simulation second.',
 'A reflected UObject/actor integration boundary must perform BindResident inside C++, installing an authoritative segment-review TFunction; Python cannot supply either native ownership or callback.',
 'The coordinator must map role-reviewed semantic feet waypoints, obtain grounded navigation, submit routes, and confirm passage physically clear before releasing stopped reservations.',
 'A persistent character visual descriptor and velocity-driven idle/walk transition controller are required for the original 27-joint rig.',
 'Runtime save/load, pause/menu synchronization and any near/far transitions must preserve one identity/clock and body reservations; existing controller ResidentSimulation is a separate model.'
]


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def visitor_point_cm(x,y):
    # Literal source-role gate in ResidentCrowdRuntime.h, converted cm/50 once.
    x/=50;y/=50
    return (34<=x<50 and abs(y)<40) or (75<x<150 and abs(y)<50)


def offline_check():
    spec=read(SPEC);pilgrims=spec['pilgrims'];header=HEADER.read_text(encoding='utf-8-sig')
    assert spec['targetMap']==TARGET and len(pilgrims['actors'])==5
    assert 'TSharedPtr<MikdashCrowd::Runtime>' in header and 'FMikdashResidentSegmentReview' in header
    methods=['BindResident','RequestReviewedRoute','ConfirmPassageCleared','RequestResidentStop']
    reflected={name:bool(re.search(r'UFUNCTION\s*\([^)]*\)\s*[^;{}]*\b'+name+r'\s*\(',header)) for name in methods}
    callers=[]
    for path in (ROOT/'Plugins/MikdashRuntime/Source').rglob('*.cpp'):
        for number,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
            if re.search(r'(?:->|\.)BindResident\s*\(',line):callers.append(dict(file=str(path.relative_to(ROOT)),line=number))
    historical={row['label']:row for row in read(PLACEMENT)['reopenedReadback'] if row['label'].startswith('RELEASE_Pilgrims_')}
    assert len(historical)==5
    plans=[]
    for actor in pilgrims['actors']:
        label=spec['labelPrefix']+pilgrims['group']+'_'+str(actor['index'])
        x,y=actor['xy'];row=historical[label]
        assert row['meshPath']==[pilgrims['skeletalMesh']] and row['animation']==pilgrims['idleAnimation']
        assert all(visitor_point_cm(x+dx,y+dy) for dx in (-34,34) for dy in (-34,34))
        assert 4700<=x-34 and x+34<=5300 and 900<=y-34 and y+34<=1450
        assert actor['animation']=='idle'
        plans.append(dict(label=label,proposedStableId='authored-outer-visitor-%02d'%actor['index'],
            role='Visitor',historicalSavedPose=row['pose'],historicalFeetAabbErrorCm=row['feetErrorCm'],
            pointWithinExistingSourceVisitorEnvelope=True,proposedCharacterOriginCm=[x,y,row['pose']['location'][2]+96],
            proposedMeshRelativeLocationCm=[0,0,-96],proposedMeshRelativeYawDegrees=90,
            proposedCharacterYawDegrees=actor['yaw']-90,routeApproval='NONE: point gate is not segment access or purity evidence'))
    return dict(status='BLOCKED_MISSING_CPP_RUNTIME_BRIDGE' if not any(reflected.values()) and not callers else 'SOURCE_CHANGED_REVIEW_NEW_BRIDGE_REQUIRED',
        map=TARGET,reflectedMutationMethods=reflected,externalBindCallSites=callers,
        controllerUsesSeparateResidentSimulation='ResidentSimulation.AdvanceTo' in CONTROLLER.read_text(encoding='utf-8-sig'),
        expectedVisualActorCount=5,mesh=pilgrims['skeletalMesh'],idleAnimation=pilgrims['idleAnimation'],walkAnimation=pilgrims['walkAnimation'],
        residents=plans,missingCppRequirements=MISSING,
        sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in [SPEC,HEADER,ADAPTER,RUNTIME,CONTROLLER,PLACEMENT,POPULATION_HEADER,POPULATION_CPP]},
        mutationAllowed=False,scope='Source preflight only; no native visual, navigation, floor, gait or packaged verification')


def run(apply=False, allow_review_copy=False):
    """Audit current saved map only; no load/switch, save, actor or asset mutation."""
    if apply:
        if not allow_review_copy:raise RuntimeError("Explicit allow_review_copy=True required; main map is never edited")
        return prepare_review_copy()
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():raise RuntimeError('User PIE preserved; stop this audit without touching gameplay')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Unsaved work preserved; run the audit on an idle saved map')
    world=editor.get_editor_world()
    if not world or world.get_outermost().get_name()!=TARGET:raise RuntimeError('Load the saved combined map explicitly before this read-only audit')
    report=offline_check();report['nativeActors']=[]
    map_file=ROOT/('Content/'+TARGET[6:]+'.umap');before=sha(map_file)
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
    spec=read(SPEC)['pilgrims']
    actor_class=ue.load_class(None,'/Script/MikdashRuntime.MikdashResidentCharacter')
    if actor_class:
        default=ue.get_default_object(actor_class)
        report['nativeBindingMethodExposed']=hasattr(default,'bind_resident')
        report['nativeDefaultResidentState']=default.get_resident_state()
    else:report['nativeAdapterClassAvailable']=False
    expected_labels={entry['label'] for entry in report['residents']}
    found=[]
    for actor in actors:
        components=actor.get_components_by_class(ue.SkeletalMeshComponent)
        for component in components:
            mesh=component.get_skeletal_mesh_asset()
            if mesh and mesh.get_path_name().split('.')[0]==spec['skeletalMesh']:
                found.append((actor,component))
    if len(found)!=5 or {a.get_actor_label() for a,c in found}!=expected_labels:raise RuntimeError('Saved five-actor visual inventory changed; review before mapping identities')
    for actor,component in found:
        if not isinstance(actor,ue.SkeletalMeshActor):raise RuntimeError('Actor class changed; do not replace or rebind automatically')
        p=actor.get_actor_location();r=actor.get_actor_rotation();s=actor.get_actor_scale3d()
        planned=next(entry for entry in report['residents'] if entry['label']==actor.get_actor_label())
        historical=planned['historicalSavedPose']
        if max(abs(a-b) for a,b in zip([p.x,p.y,p.z],historical['location']))>.1:raise RuntimeError('Visual position changed; re-review safe envelope and feet')
        if max(abs(a-b) for a,b in zip([r.pitch,r.yaw,r.roll],historical['rotation']))>.01 or max(abs(v-1) for v in [s.x,s.y,s.z])>.001:
            raise RuntimeError('Visual orientation/scale changed')
        animation=component.get_editor_property('animation_data')
        clip=animation.get_editor_property('anim_to_play')
        clip_path=clip.get_path_name().split('.')[0] if clip else None
        if clip_path!=spec['idleAnimation']:raise RuntimeError('Expected saved idle clip; do not override a changed animation setup')
        report['nativeActors'].append(dict(label=actor.get_actor_label(),actorClass=actor.get_class().get_path_name(),
            locationCm=[p.x,p.y,p.z],skeletalMesh=spec['skeletalMesh'],animation=clip_path,
            looping=animation.get_editor_property('saved_looping'),playing=animation.get_editor_property('saved_playing'),
            collisionProfile=str(component.get_collision_profile_name()),binding='NOT_BOUND'))
    report.update(mapBytesUnchanged=sha(map_file)==before,mapSha256=before,nativeInventoryVerified=True,applyRequested=bool(apply),nativeMutationPerformed=False)
    assert report['mapBytesUnchanged']
    ue.log(json.dumps(report,indent=2))
    if apply:raise RuntimeError('Resident integration refused before mutation: native shared-runtime coordinator and reflected C++ binding boundary are missing. See resident-integration-plan.md.')
    return report


def _path(asset):
    return asset.get_path_name().split('.')[0] if asset else None


def _pose(actor):
    p=actor.get_actor_location();r=actor.get_actor_rotation();s=actor.get_actor_scale3d()
    return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]


def _scene_snapshot(ue, actors):
    """One linear snapshot: identities, all components, meshes/materials and settings."""
    result={}
    def value(v):
        if v is None or isinstance(v,(bool,int,float,str)):return v
        if hasattr(v,'get_path_name'):return v.get_path_name()
        if isinstance(v,(list,tuple)):return [value(x) for x in v]
        # Convert exposed UE structs recursively through public non-callable fields,
        # never use struct repr (contains unstable addresses).
        fields={}
        for name in dir(v):
            if name.startswith('_'):continue
            try:entry=getattr(v,name)
            except Exception:continue
            if isinstance(entry,(bool,int,float,str)):fields[name]=entry
            elif name in ('translation','rotation','scale3d'):
                fields[name]=value(entry)
        return fields
    for actor in actors.get_all_level_actors():
        label=actor.get_actor_label();identity=actor.get_name()
        if identity in result:raise RuntimeError('Duplicate native actor name prevents exact scene comparison')
        components=[]
        for comp in actor.get_components_by_class(ue.ActorComponent):
            row=dict(name=comp.get_name(),kind=comp.get_class().get_path_name(),active=comp.is_active())
            if isinstance(comp,ue.SceneComponent):
                for key in ('relative_location','relative_rotation','relative_scale3d','visible','hidden_in_game','mobility'):
                    row[key]=value(comp.get_editor_property(key))
            if isinstance(comp,ue.PrimitiveComponent):
                row['collision']=str(comp.get_collision_profile_name())
                row['collisionEnabled']=str(comp.get_collision_enabled())
            if isinstance(comp,ue.MeshComponent):
                row['materials']=[_path(comp.get_material(i)) for i in range(comp.get_num_materials())]
            if isinstance(comp,ue.StaticMeshComponent):row['mesh']=_path(comp.get_editor_property('static_mesh'))
            if isinstance(comp,ue.SkeletalMeshComponent):row['mesh']=_path(comp.get_skeletal_mesh_asset())
            if isinstance(comp,ue.InstancedStaticMeshComponent):
                row['instances']=[value(comp.get_instance_transform(i,False)) for i in range(comp.get_instance_count())]
            # Known scene-wide settings; property availability is recorded explicitly.
            for key in ('intensity','light_color','cast_shadows','fog_density','fog_height_falloff','settings'):
                try:row[key]=value(comp.get_editor_property(key))
                except Exception:pass
            components.append(row)
        result[identity]=dict(label=label,kind=actor.get_class().get_path_name(),pose=_pose(actor),
            tags=[str(t) for t in actor.tags],components=sorted(components,key=lambda c:c['name']))
    return result


def _compiled_bridge_evidence():
    text=BUILD_LOG.read_text(encoding='utf-8-sig',errors='replace')
    if 'Result: Succeeded' not in text or 'MikdashResidentPopulation.cpp' not in text:
        raise RuntimeError('Missing successful population compilation evidence')
    latest=max(POPULATION_HEADER.stat().st_mtime_ns,POPULATION_CPP.stat().st_mtime_ns)
    if BUILD_DLL.stat().st_mtime_ns < latest or BUILD_LOG.stat().st_mtime_ns < latest:
        raise RuntimeError('Population sources are newer than successful binary/log; compile again')
    return {'log':str(BUILD_LOG),'logSha256':sha(BUILD_LOG),'binary':str(BUILD_DLL),
        'binarySha256':sha(BUILD_DLL),'sources':{str(p.relative_to(ROOT)):sha(p) for p in (POPULATION_HEADER,POPULATION_CPP)},
        'limitation':'Successful disk build evidence; launch a fresh editor to avoid a stale loaded DLL.'}


def prepare_review_copy():
    """Explicit review-copy placement; leaves the saved source map untouched."""
    import unreal as ue
    import shutil
    from datetime import datetime, timezone
    preflight=run(apply=False)
    compiled=_compiled_bridge_evidence()
    character=ue.load_class(None,'/Script/MikdashRuntime.MikdashResidentCharacter')
    population=ue.load_class(None,'/Script/MikdashRuntime.MikdashResidentPopulation')
    if not character or not population or not hasattr(ue.get_default_object(population),'initialize_reviewed_pilot'):
        raise RuntimeError('Compile the native population bridge before placement')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target='/Game/MikdashV3/ResidentCrowdReview/'+stamp+'/Walkthrough'
    if ue.EditorAssetLibrary.does_asset_exist(target):raise RuntimeError('Unique target exists; refusing overwrite')
    source=ROOT/('Content/'+TARGET[6:]+'.umap')
    checkpoint=ROOT.parent/'ReviewCheckpoints'/('ResidentCrowd-'+stamp)
    checkpoint.mkdir(parents=True,exist_ok=False)
    shutil.copy2(source,checkpoint/'BeforeResidents.umap')
    original_hash=sha(source)
    assert sha(checkpoint/'BeforeResidents.umap')==original_hash
    assets=read(SPEC)['pilgrims']
    protected={key:ROOT/('Content/'+assets[key][6:]+'.uasset') for key in ('skeletalMesh','idleAnimation','walkAnimation')}
    protected_hashes={key:sha(file) for key,file in protected.items()}
    receipt_path=ROOT/'SourceAssets/characters-review'/('native-resident-review-'+stamp+'.json')
    receipt=dict(status='preflight',sourceMap=TARGET,targetMap=target,checkpoint=str(checkpoint),sourceSha256=original_hash,
        nativeBehaviorVerified=False,placementOnly=True,sourceAssetHashes=protected_hashes,
        sourceHashes=preflight['sourceHashes'],compiledBridge=compiled)
    def write():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    write()
    levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    expected={row['label']:row for row in preflight['residents']}
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    def require_target():
        if editor.get_editor_world().get_outermost().get_name()!=target:raise RuntimeError('Actual editor world differs from review target')
    try:
        source_scene=_scene_snapshot(ue,actors)
        selected=[row for row in source_scene.values() if row['label'] in expected]
        assert len(selected)==5 and len({row['label'] for row in selected})==5
        baseline={name:row for name,row in source_scene.items() if row['label'] not in expected}
        if not ue.EditorAssetLibrary.duplicate_asset(TARGET,target):raise RuntimeError('Map duplication failed')
        if not levels.load_level(target):raise RuntimeError('Review map load failed')
        require_target()
        assert _scene_snapshot(ue,actors)==source_scene
        assert all(sha(ROOT/name)==digest for name,digest in preflight['sourceHashes'].items())
        old={a.get_actor_label():a for a in actors.get_all_level_actors() if a.get_actor_label() in expected}
        assert len(old)==5
        mesh=ue.load_asset(assets['skeletalMesh']);idle=ue.load_asset(assets['idleAnimation']);walk=ue.load_asset(assets['walkAnimation'])
        assert mesh and idle and walk
        assert _path(mesh.get_editor_property('skeleton'))==_path(idle.get_editor_property('skeleton'))==_path(walk.get_editor_property('skeleton'))
        bodies=[]
        for label,plan in expected.items():
            body=actors.spawn_actor_from_class(character,ue.Vector(*plan['proposedCharacterOriginCm']),
                ue.Rotator(pitch=0,yaw=plan['proposedCharacterYawDegrees'],roll=0),transient=False)
            if not body:raise RuntimeError('Character spawn failed')
            body.set_actor_label('REVIEW_Resident_'+plan['proposedStableId'])
            component=body.get_component_by_class(ue.SkeletalMeshComponent)
            component.set_skeletal_mesh_asset(mesh)
            component.set_relative_location(ue.Vector(0,0,-96),False,False)
            component.set_relative_rotation(ue.Rotator(pitch=0,yaw=90,roll=0),False,False)
            component.set_collision_profile_name('NoCollision')
            component.set_animation_mode(ue.AnimationMode.ANIMATION_SINGLE_NODE)
            component.override_animation_data(idle,True,True,0.0,1.0)
            capsule=body.get_component_by_class(ue.CapsuleComponent)
            capsule.set_collision_profile_name('Pawn')
            assert abs(capsule.get_scaled_capsule_radius()-34)<.01 and abs(capsule.get_scaled_capsule_half_height()-96)<.01
            assert _path(component.get_skeletal_mesh_asset())==assets['skeletalMesh']
            bodies.append(body)
        owner=actors.spawn_actor_from_class(population,ue.Vector(0,0,0),ue.Rotator(),transient=False)
        if not owner:raise RuntimeError('Population spawn failed')
        owner.set_actor_label('REVIEW_ResidentPopulation')
        owner.set_editor_property('bodies',bodies)
        owner.set_editor_property('idle_animation',idle);owner.set_editor_property('walk_animation',walk)
        assert len(owner.get_editor_property('bodies'))==5
        # Remove only the exact copied idle visuals after replacements are configured.
        for actor in old.values():
            if not actors.destroy_actor(actor):raise RuntimeError('Copied idle actor removal failed')
        require_target()
        current=_scene_snapshot(ue,actors)
        new_labels={body.get_name() for body in bodies}|{owner.get_name()}
        assert set(current)==set(baseline)|new_labels
        assert all(current.get(label)==row for label,row in baseline.items())
        receipt['expectedBodies']={body.get_actor_label():_pose(body) for body in bodies}
        if not levels.save_current_level():raise RuntimeError('Review save failed')
        receipt['status']='saved_reopen_pending';receipt['reviewMapSha256']=sha(ROOT/('Content/'+target[6:]+'.umap'));write()
        if not levels.load_level(target):raise RuntimeError('Review reopen failed')
        require_target()
        reopened_scene=_scene_snapshot(ue,actors)
        assert set(reopened_scene)==set(baseline)|new_labels
        assert all(reopened_scene.get(label)==row for label,row in baseline.items())
        reloaded={a.get_actor_label():a for a in actors.get_all_level_actors()}
        assert all(label not in reloaded for label in expected)
        pop=reloaded['REVIEW_ResidentPopulation'];references=list(pop.get_editor_property('bodies'))
        assert len(references)==5 and len({a.get_path_name() for a in references})==5
        for body in references:
            assert _pose(body)==receipt['expectedBodies'][body.get_actor_label()]
            component=body.get_component_by_class(ue.SkeletalMeshComponent)
            assert _path(component.get_skeletal_mesh_asset())==assets['skeletalMesh']
            assert _path(component.get_editor_property('animation_data').get_editor_property('anim_to_play'))==assets['idleAnimation']
            assert str(component.get_collision_profile_name())=='NoCollision'
            capsule=body.get_component_by_class(ue.CapsuleComponent)
            assert str(capsule.get_collision_profile_name())=='Pawn'
            assert abs(capsule.get_scaled_capsule_radius()-34)<.01 and abs(capsule.get_scaled_capsule_half_height()-96)<.01
            relative=component.get_editor_property('relative_location')
            assert max(abs(relative.x),abs(relative.y),abs(relative.z+96))<.01
            rotation=component.get_editor_property('relative_rotation')
            assert max(abs(rotation.pitch),abs(rotation.roll),abs(rotation.yaw-90))<.01
        assert _path(pop.get_editor_property('idle_animation'))==assets['idleAnimation']
        assert _path(pop.get_editor_property('walk_animation'))==assets['walkAnimation']
        receipt['status']='saved_reopened_behavior_unverified'
    except Exception as exc:
        receipt['failure']=repr(exc);receipt['status']='failed_review_copy_preserved'
        raise
    finally:
        receipt['sourceMapUnchanged']=sha(source)==original_hash
        receipt['sourceAssetsUnchanged']=all(sha(file)==protected_hashes[key] for key,file in protected.items())
        if not receipt['sourceMapUnchanged'] or not receipt['sourceAssetsUnchanged']:
            receipt['status']='failed_protected_source_hash_mismatch'
        write()
        # Root owns the editor session; restore source only after successful save/readback.
        if receipt['status']=='saved_reopened_behavior_unverified':levels.load_level(TARGET)
    assert receipt['sourceMapUnchanged'] and receipt['sourceAssetsUnchanged']
    ue.log(json.dumps(receipt,indent=2));return receipt


_PROBE=None

def probe_active_review_game(allow_initialize=False, duration_seconds=20):
    """Opt-in finite probe of an already running REVIEW game; never starts/stops PIE."""
    import unreal as ue
    import time
    from datetime import datetime, timezone
    global _PROBE
    if not allow_initialize:raise RuntimeError('Explicit allow_initialize=True required')
    if _PROBE and _PROBE.get('active'):raise RuntimeError('Probe already active')
    if not 1<=duration_seconds<=60:raise RuntimeError('Probe duration must be 1..60 seconds')
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem);world=editor.get_game_world()
    if not world or '/ResidentCrowdReview/' not in world.get_outermost().get_name():raise RuntimeError('Only an already running isolated review world may be initialized')
    cls=ue.load_class(None,'/Script/MikdashRuntime.MikdashResidentPopulation')
    populations=ue.GameplayStatics.get_all_actors_of_class(world,cls)
    if len(populations)!=1:raise RuntimeError('Expected one review population')
    if populations[0].is_population_active():raise RuntimeError('Already active population preserved; use existing probe receipt or restart review deliberately')
    population=populations[0];bodies=list(population.get_editor_property('bodies'))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path=ROOT/'SourceAssets/characters-review'/('native-resident-probe-'+stamp+'.json')
    state=dict(active=True,initialized=False,samples=[],started=time.monotonic(),status='pre_initialization',nativeAcceptance=False)
    _PROBE=state
    def write():path.write_text(json.dumps({k:v for k,v in state.items() if k!='handle'},indent=2),encoding='utf-8')
    def finish(status):
        state['status']=status;state['active']=False
        try:
            if editor.get_game_world()==world:
                population.set_population_paused(True)
                state['pauseRequested']=True
                velocities=[[b.get_velocity().x,b.get_velocity().y,b.get_velocity().z] for b in bodies]
                state['finalVelocities']=velocities
                state['stoppedAtReadback']=all(sum(v*v for v in xyz)<.01 for xyz in velocities)
                # If still moving, capture one subsequent tick after the adapter sees pause.
                if not state['stoppedAtReadback']:state['status']+='; stop_readback_pending'
        finally:
            if state.get('handle') is not None:
                ue.unregister_slate_post_tick_callback(state.pop('handle'))
            write()
    def tick(delta):
        try:
            if editor.get_game_world()!=world:finish('review_game_ended_or_changed');return
            elapsed=time.monotonic()-state['started']
            if state.get('pauseAt') is not None:
                if all(sum(v*v for v in (b.get_velocity().x,b.get_velocity().y,b.get_velocity().z))<.01 for b in bodies):finish('probe_complete_paused_review_required')
                elif elapsed-state['pauseAt']>=2:finish('failed_pause_stop_verification')
                return
            if len(state['samples'])<=int(elapsed):
                state['samples'].append(dict(seconds=elapsed,population=population.get_population_status(),
                    residents=[dict(id=b.get_resident_id(),state=b.get_resident_state(),goal=b.get_resident_goal(),
                        routeDiagnostic=b.get_route_diagnostic(),
                        pose=_pose(b),velocity=[b.get_velocity().x,b.get_velocity().y,b.get_velocity().z]) for b in bodies]))
            if elapsed>=duration_seconds:
                population.set_population_paused(True);state['pauseAt']=elapsed
        except Exception as exc:
            state['failure']=repr(exc);finish('probe_failed')
    try:
        write()  # Ensure receipt storage works before changing gameplay.
        state['handle']=ue.register_slate_post_tick_callback(tick)
        state['initialized']=bool(population.initialize_reviewed_pilot())
        state['status']='sampling' if state['initialized'] else 'initialization_refused'
        write()
        if not state['initialized']:finish('initialization_refused_check_ground_visual_setup_and_world')
    except Exception as exc:
        state['failure']=repr(exc);finish('probe_start_failed');raise
    return {'initialized':state['initialized'],'receipt':str(path),'durationSeconds':duration_seconds,
        'note':'Bounded probe pauses its population at completion; reservations retained. Idle may indicate nav or collision rejection.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--offline-check',action='store_true');args=parser.parse_args()
    if not args.offline_check:parser.error('Use --offline-check, or explicitly call run(apply=False) inside the editor')
    print(json.dumps(offline_check(),indent=2))

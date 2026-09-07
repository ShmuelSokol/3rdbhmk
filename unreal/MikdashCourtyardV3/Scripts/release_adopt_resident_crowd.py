"""Explicit five-resident adoption into CURRENT main map, never donor-map overwrite.
Requires fresh compiled BeginPlay opt-in, native route/pause evidence, idle saved editor.
Native execution belongs to root. run(apply=False) is preflight only.
"""
from pathlib import Path
import json
import runpy
import shutil
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
HELPER=runpy.run_path(str(ROOT/'Scripts/release_resident_crowd.py'))
MAIN=HELPER['TARGET']
DONOR='/Game/MikdashV3/ResidentCrowdReview/20260907T222556423474Z/Walkthrough'
PROBE=ROOT/'SourceAssets/characters-review/native-resident-probe-20260907T225710719481Z.json'
PLACEMENT=ROOT/'SourceAssets/characters-review/native-resident-review-20260907T222556423474Z.json'


def evidence():
    probe=json.loads(PROBE.read_text(encoding='utf-8-sig'))
    placement=json.loads(PLACEMENT.read_text(encoding='utf-8-sig'))
    assert probe['initialized'] and probe['stoppedAtReadback'] and probe['pauseRequested']
    assert placement['targetMap']==DONOR and placement['status']=='saved_reopened_behavior_unverified'
    rows=[]
    for index in range(5):
        first=probe['samples'][0]['residents'][index];last=probe['samples'][-1]['residents'][index]
        assert last['routeDiagnostic']=='Physical arrival confirmed' and last['state']=='Attending to goal'
        distance=sum((a-b)**2 for a,b in zip(first['pose'][:3],last['pose'][:3]))**.5
        assert 50<distance<100 and first['id']==last['id']
        rows.append(dict(id=last['id'],distanceCm=distance))
    return dict(probe=str(PROBE),probeSha256=HELPER['sha'](PROBE),movement=rows,
        limitations=['18cm endpoint tolerance','30-second task completion not shown','no persistent save/load proof','visual gait review pending'])


def run(apply=False):
    import unreal as ue
    proof=evidence();preflight=HELPER['run'](apply=False)
    if not apply:return dict(status='preflight_only',proof=proof,next='Requires explicit apply=True and fresh BeginPlay-enabled binary')
    compiled=HELPER['_compiled_bridge_evidence']()
    character=ue.load_class(None,'/Script/MikdashRuntime.MikdashResidentCharacter')
    population=ue.load_class(None,'/Script/MikdashRuntime.MikdashResidentPopulation')
    assert character and population
    assert ue.get_default_object(population).get_editor_property('activate_reviewed_pilot_on_begin_play') is False
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem);levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    def world_is(package):
        if editor.get_editor_world().get_outermost().get_name()!=package:raise RuntimeError('Unexpected actual editor world')
    source=ROOT/('Content/'+MAIN[6:]+'.umap');donor_file=ROOT/('Content/'+DONOR[6:]+'.umap')
    source_hash=HELPER['sha'](source);donor_hash=HELPER['sha'](donor_file)
    saved_placement=json.loads(PLACEMENT.read_text(encoding='utf-8-sig'))
    assert donor_hash==saved_placement['reviewMapSha256']
    original=HELPER['_scene_snapshot'](ue,actors)
    old_labels={row['label'] for row in preflight['residents']}
    baseline={name:row for name,row in original.items() if row['label'] not in old_labels}
    assert len(original)-len(baseline)==5
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint=ROOT.parent/'ReviewCheckpoints'/('AdoptResidents-'+stamp)
    checkpoint.mkdir(parents=True,exist_ok=False);shutil.copy2(source,checkpoint/'BeforeResidents.umap')
    assert HELPER['sha'](checkpoint/'BeforeResidents.umap')==source_hash
    receipt_path=ROOT/'SourceAssets/characters-review'/('native-resident-adoption-'+stamp+'.json')
    receipt=dict(status='preflight',sourceMap=MAIN,donorMap=DONOR,sourceBeforeSha256=source_hash,donorSha256=donor_hash,
        checkpoint=str(checkpoint),proof=proof,compiled=compiled,mainRuntimeAcceptance=False)
    def write():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    write();mutated=False
    spec=HELPER['read'](HELPER['SPEC'])['pilgrims']
    assets={key:ROOT/('Content/'+spec[key][6:]+'.uasset') for key in ('skeletalMesh','idleAnimation','walkAnimation')}
    hashes={key:HELPER['sha'](file) for key,file in assets.items()}
    try:
        assert levels.load_level(DONOR);world_is(DONOR)
        selected=[a for a in actors.get_all_level_actors() if a.get_actor_label().startswith('REVIEW_Resident_authored-outer-visitor-')]
        assert len(selected)==5
        descriptors=[]
        for body in sorted(selected,key=lambda a:a.get_actor_label()):
            pose=HELPER['_pose'](body);label=body.get_actor_label()
            assert pose==saved_placement['expectedBodies'][label]
            mesh_component=body.get_component_by_class(ue.SkeletalMeshComponent)
            assert HELPER['_path'](mesh_component.get_skeletal_mesh_asset())==spec['skeletalMesh']
            descriptors.append(dict(label=label.replace('REVIEW_','RELEASE_'),pose=pose))
        assert levels.load_level(MAIN);world_is(MAIN)
        assert HELPER['_scene_snapshot'](ue,actors)==original and HELPER['sha'](source)==source_hash
        old=[a for a in actors.get_all_level_actors() if a.get_actor_label() in old_labels]
        assert len(old)==5 and len({a.get_actor_label() for a in old})==5
        mesh=ue.load_asset(spec['skeletalMesh']);idle=ue.load_asset(spec['idleAnimation']);walk=ue.load_asset(spec['walkAnimation'])
        bodies=[]
        for row in descriptors:
            pose=row['pose'];body=actors.spawn_actor_from_class(character,ue.Vector(*pose[:3]),ue.Rotator(pitch=pose[3],yaw=pose[4],roll=pose[5]),transient=False)
            if not body:raise RuntimeError('Resident spawn failed')
            mutated=True;body.set_actor_label(row['label'])
            component=body.get_component_by_class(ue.SkeletalMeshComponent)
            component.set_skeletal_mesh_asset(mesh);component.set_relative_location(ue.Vector(0,0,-96),False,False)
            component.set_relative_rotation(ue.Rotator(pitch=0,yaw=90,roll=0),False,False)
            component.set_collision_profile_name('NoCollision');component.set_animation_mode(ue.AnimationMode.ANIMATION_SINGLE_NODE)
            component.override_animation_data(idle,True,True,0.,1.)
            body.get_component_by_class(ue.CapsuleComponent).set_collision_profile_name('Pawn');bodies.append(body)
        owner=actors.spawn_actor_from_class(population,ue.Vector(),ue.Rotator(),transient=False)
        if not owner:raise RuntimeError('Population spawn failed')
        owner.set_actor_label('RELEASE_ResidentPopulation');owner.set_editor_property('bodies',bodies)
        owner.set_editor_property('idle_animation',idle);owner.set_editor_property('walk_animation',walk)
        # Only after all five references and visual assets are configured.
        owner.set_editor_property('activate_reviewed_pilot_on_begin_play',True)
        for actor in old:
            assert actors.destroy_actor(actor)
        current=HELPER['_scene_snapshot'](ue,actors);added={b.get_name() for b in bodies}|{owner.get_name()}
        assert set(current)==set(baseline)|added
        assert all(current[name]==row for name,row in baseline.items())
        expected={b.get_actor_label():HELPER['_pose'](b) for b in bodies}
        world_is(MAIN)
        assert levels.save_current_level()
        receipt.update(status='saved_reopen_pending',mapSaved=True,sourceAfterSha256=HELPER['sha'](source));write()
        assert levels.load_level(MAIN);world_is(MAIN)
        reopened=HELPER['_scene_snapshot'](ue,actors)
        assert set(reopened)==set(current) and all(reopened[name]==row for name,row in baseline.items())
        pop=[a for a in actors.get_all_level_actors() if a.get_actor_label()=='RELEASE_ResidentPopulation']
        assert len(pop)==1 and pop[0].get_editor_property('activate_reviewed_pilot_on_begin_play') is True
        refs=list(pop[0].get_editor_property('bodies'));assert len(refs)==5 and len({b.get_name() for b in refs})==5
        for body in refs:
            assert HELPER['_pose'](body)==expected[body.get_actor_label()]
            assert reopened[body.get_name()]==current[body.get_name()]
        assert HELPER['_path'](pop[0].get_editor_property('idle_animation'))==spec['idleAnimation']
        assert HELPER['_path'](pop[0].get_editor_property('walk_animation'))==spec['walkAnimation']
        receipt.update(status='adopted_saved_reopened_main_runtime_unverified',residentLabels=list(expected))
    except Exception as exc:
        receipt.update(status='failed_checkpoint_available',failure=repr(exc),sceneMutated=mutated)
        raise
    finally:
        receipt['donorUnchanged']=HELPER['sha'](donor_file)==donor_hash
        receipt['sourceAssetsUnchanged']=all(HELPER['sha'](file)==hashes[key] for key,file in assets.items())
        if not receipt['donorUnchanged'] or not receipt['sourceAssetsUnchanged']:receipt['status']='failed_protected_hash_mismatch'
        write()
    assert receipt['donorUnchanged'] and receipt['sourceAssetsUnchanged']
    return receipt

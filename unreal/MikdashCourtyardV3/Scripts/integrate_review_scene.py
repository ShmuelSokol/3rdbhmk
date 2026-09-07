"""Explicit collection/build for a combined review map; no action on import.

Default sanctuary donor is Gold. Polish requires sanctuary_source='polish'; it
is a candidate, not accepted. FutureMount exposure/geometry remain the base.
Cloud/wind sequences are recreated with new actor/component bindings by default.
Run in a separate idle native commandlet, never the user's active play session.
V2 preserves partial V1. V1's snapshot comparison recomputed the full scene for
each actor (quadratic); V2 computes one numeric snapshot per verification phase.
"""
import hashlib
import json
from pathlib import Path
ROOT=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
BASE='/Game/MikdashV3/FutureMountV1/L_FutureMount'
TARGET='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
GOLD='/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold'
POLISH='/Game/MikdashV3/MaterialReview/SanctuaryPolishV1/Maps/CourtyardPolish'
FOLDER=ROOT/'SourceAssets/IntegratedReviewV2'
VENEER_TAG='SanctuaryFinishesV1Review'
VENEER='/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/SM_InteriorVeneerCube'
VESSELS={
 '/Game/MikdashV3/MaterialReview/HeikhalKeilimV1/Meshes/SM_GoldenIncenseAltarStudy',
 '/Game/MikdashV3/MaterialReview/HeikhalKeilimV1/Meshes/SM_ShulchanStudy',
 '/Game/MikdashV3/MaterialReview/TempleInstituteMenorahStudyV1/Meshes/SM_MenorahStudyV1'}
ARON='/Game/MikdashV3/MaterialReview/AronStudyV3/Meshes/'
FINISH_MATERIALS={
 '/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/M_Sanctuary_gold',
 '/Game/MikdashV3/MaterialReview/SanctuaryPolishV1/M_GoldWall',
 '/Game/MikdashV3/MaterialReview/SanctuaryPolishV1/M_GoldFloor'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def disk(asset):
    assert asset.startswith('/Game/')
    return ROOT/('Content/'+asset[6:]+'.umap')
def xyz(v):return [v.x,v.y,v.z]
def rotation(v):return [v.pitch,v.yaw,v.roll]
def actor_pose(actor):
    return dict(location=xyz(actor.get_actor_location()),rotation=rotation(actor.get_actor_rotation()),scale=xyz(actor.get_actor_scale3d()))
def path_of(asset):return asset.get_path_name().split('.')[0] if asset else None


def collect(sanctuary_source='gold',include_aron=True,include_atmosphere=True):
    import unreal as ue
    assert sanctuary_source in ('gold','polish')
    assert Path(ue.Paths.project_dir()).resolve()==ROOT
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    assert not editor.get_game_world()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    donor=GOLD if sanctuary_source=='gold' else POLISH
    sources=list(dict.fromkeys([donor,GOLD]))
    if include_atmosphere:sources.append(ATMOSPHERE_MAP)
    hashes={source:sha(disk(source)) for source in sources}
    initial=editor.get_editor_world().get_outermost().get_name()
    restore=initial if assets.does_asset_exist(initial) else BASE
    report=dict(version=1,status='collecting',sanctuarySource=sanctuary_source,donorMap=donor,
        sourceMapHashes=hashes,architectureOverrides=[],veneers=[],vessels=[],aron=[],doorwayLight=None,
        baseExposure='Preserve adopted FutureMount histogram exposure; no donor postprocess copy.',
        missing=['Cloud and wind need new native actors and rebuilt sequence binding GUIDs; not integrated here.',
        'This combines review assets only. Visual/halachic acceptance, complete vessels, runtime walking and packaging remain separate.'])
    def mesh_record(actor,component):
        assert len(actor.get_components_by_class(ue.StaticMeshComponent))==1,'Complex actor requires explicit integration adapter'
        pose=actor_pose(actor)
        world=dict(location=xyz(component.get_world_location()),rotation=rotation(component.get_world_rotation()),scale=xyz(component.get_world_scale()))
        assert pose==world,'Nonidentity component-relative transform needs explicit adapter'
        return dict(label=actor.get_actor_label(),mesh=path_of(component.get_editor_property('static_mesh')),
            pose=pose,materials=[path_of(component.get_material(i)) for i in range(component.get_num_materials())],
            overrideMaterials=[path_of(m) for m in component.get_editor_property('override_materials')],
            collisionProfile=str(component.get_collision_profile_name()),
            collisionEnabled=next(name for name in ['NO_COLLISION','QUERY_ONLY','PHYSICS_ONLY','QUERY_AND_PHYSICS','PROBE_ONLY','QUERY_AND_PROBE'] if hasattr(ue.CollisionEnabled,name) and getattr(ue.CollisionEnabled,name)==component.get_collision_enabled()),
            mobility=next(name for name in ['STATIC','STATIONARY','MOVABLE'] if getattr(ue.ComponentMobility,name)==component.get_editor_property('mobility')),
            tags=[str(t) for t in actor.get_editor_property('tags')],folder=str(actor.get_folder_path()))
    try:
        vessels={}
        for source_map in sources:
            assert levels.load_level(source_map)
            for actor in actors.get_all_level_actors():
                for component in actor.get_components_by_class(ue.StaticMeshComponent):
                    mesh=path_of(component.get_editor_property('static_mesh'))
                    if not mesh:continue
                    if mesh in VESSELS and mesh not in vessels:
                        vessels[mesh]=dict(mesh_record(actor,component),sourceMap=source_map)
                    if source_map==GOLD and include_aron and mesh.startswith(ARON):
                        report['aron'].append(dict(mesh_record(actor,component),sourceMap=source_map))
                    if source_map!=donor:continue
                    if VENEER_TAG in [str(t) for t in actor.get_editor_property('tags')]:
                        assert mesh==VENEER
                        report['veneers'].append(dict(mesh_record(actor,component),sourceMap=source_map))
                    elif mesh.startswith('/Game/MikdashV3/Architecture/') and any(path_of(component.get_material(i)) in FINISH_MATERIALS for i in range(component.get_num_materials())):
                        report['architectureOverrides'].append(dict(mesh_record(actor,component),sourceMap=source_map))
                if source_map==donor and actor.get_actor_label()=='Review_DoorwayDaylightProxy':
                    assert report['doorwayLight'] is None and isinstance(actor,ue.RectLight)
                    c=actor.get_component_by_class(ue.RectLightComponent)
                    assert c.get_editor_property('intensity_units')==ue.LightUnits.LUMENS
                    color=c.get_editor_property('light_color')
                    report['doorwayLight']=dict(label=actor.get_actor_label(),pose=actor_pose(actor),
                        properties={key:c.get_editor_property(key) for key in ['intensity','source_width','source_height','attenuation_radius','use_temperature','temperature','cast_shadows','indirect_lighting_intensity','volumetric_scattering_intensity']},
                        lightColor=[color.r,color.g,color.b,color.a],interpretation='Render-only doorway daylight proxy, not a historical fixture.')
        assert len(report['architectureOverrides'])==6 and len(report['veneers'])==7
        assert len({r['mesh'] for r in report['architectureOverrides']})==6
        assert len({r['label'] for r in report['veneers']})==7
        assert set(vessels)==VESSELS,'Three saved vessel studies required'
        report['vessels']=[vessels[key] for key in sorted(vessels)]
        assert len(report['aron']) in (0,16),'Partial Aron placement must be resolved in Gold donor first'
        if report['aron']:assert len({r['mesh'] for r in report['aron']})==16
        else:report['missing'].append('Aron not collected: donor placement absent or include_aron=False.')
        if report['doorwayLight'] is None:report['missing'].append('No doorway proxy in selected donor; no extra light fabricated.')
        if include_atmosphere:
            report['atmosphere']=_collect_atmosphere(ue)
            report['missing']=[m for m in report['missing'] if not m.startswith('Cloud and wind need')]
            report['missing'].append(report['atmosphere']['limitation'])
        else:report['atmosphere']=None
        report['status']='source_collection_verified_integration_pending'
    finally:
        assert levels.load_level(restore),'Restore saved starting map after collection'
        assert all(sha(disk(source))==value for source,value in hashes.items()),'Source map bytes changed'
        report['sourceMapsUnchanged']=True
        FOLDER.mkdir(exist_ok=True)
        (FOLDER/'source-collection.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def build(sanctuary_source='gold',include_aron=True,include_atmosphere=True):
    import unreal as ue
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    assert not assets.does_asset_exist(TARGET),'Existing integrated review preserved; use explicit versioned migration'
    # Requires the prior Mount stages, not merely the presence of overlay assets.
    terrain=json.loads((ROOT/'SourceAssets/FutureMountV1/terrain-generated/native-terrain-cut.json').read_text())
    trees=json.loads((ROOT/'SourceAssets/FutureMountV1/native-mount-tree-removal.json').read_text())
    assert terrain['status'].startswith('four_tiles_replaced_saved_reopened') and terrain['originalMapAndAssetsUnchanged']
    assert trees['status'].startswith('saved_reopened_source_linked_mount_trees_removed') and trees['outsideTreesPreserved']
    selection=collect(sanctuary_source,include_aron,include_atmosphere)
    protected={source:sha(disk(source)) for source in {BASE,GOLD,POLISH,ATMOSPHERE_MAP,'/Game/MikdashV3/Maps/Courtyard'} if disk(source).exists()}
    report=dict(status='building',target=TARGET,sanctuarySource=sanctuary_source,sourceMapHashes=protected,created=[],
        sourceCollectionSha256=sha(FOLDER/'source-collection.json'),missing=selection['missing'],cloudWindIntegrated=False)
    receipt=FOLDER/'native-integration.json';assert not receipt.exists(),'Prior receipt preserved'
    def component(actor):return actor.get_component_by_class(ue.StaticMeshComponent)
    def mesh_path(actor):
        c=component(actor);return path_of(c.get_editor_property('static_mesh')) if c else None
    def pose_key(p):return tuple(p['location']+p['rotation']+p['scale'])
    def numeric_snapshot():
        return {a.get_name():(a.get_actor_label(),mesh_path(a),pose_key(actor_pose(a))) for a in actors.get_all_level_actors()}
    def loaded_materials(paths):return [assets.load_asset(p) if p else None for p in paths]
    def apply_materials(c,record):
        c.set_editor_property('override_materials',loaded_materials(record['overrideMaterials']))
        assert [path_of(c.get_material(i)) for i in range(c.get_num_materials())]==record['materials']
    def verify_mesh(actor,record):
        c=component(actor)
        assert mesh_path(actor)==record['mesh'] and pose_key(actor_pose(actor))==pose_key(record['pose'])
        assert [path_of(c.get_material(i)) for i in range(c.get_num_materials())]==record['materials']
        assert c.get_collision_enabled()==getattr(ue.CollisionEnabled,record['collisionEnabled'])
        assert str(c.get_collision_profile_name())==record['collisionProfile']
    try:
        assert levels.load_level(BASE)
        baseline=numeric_snapshot()
        assert not any(a.get_actor_label().startswith('IntegratedReview_') for a in actors.get_all_level_actors())
        world=ue.EditorLoadingAndSavingUtils.new_map_from_template(BASE,False)
        assert world and world.get_outermost().get_name()!=BASE and numeric_snapshot()==baseline
        # Save a unique baseline before applying donor overrides; all later writes
        # target this new package. Source maps are never saved.
        assert ue.EditorLoadingAndSavingUtils.save_map(world,TARGET)
        assert levels.load_level(TARGET)
        assert numeric_snapshot()==baseline
        base_exposure=[a.get_editor_property('settings').export_text() for a in actors.get_all_level_actors() if isinstance(a,ue.PostProcessVolume)]
        assigned=[]
        for record in selection['architectureOverrides']:
            matching=[a for a in actors.get_all_level_actors() if mesh_path(a)==record['mesh']]
            assert len(matching)==1
            actor=matching[0];assert pose_key(actor_pose(actor))==pose_key(record['pose'])
            apply_materials(component(actor),record);assigned.append(record)
        donor_records=selection['veneers']+selection['vessels']+selection['aron']
        for record in donor_records:
            matches=[a for a in actors.get_all_level_actors() if mesh_path(a)==record['mesh'] and (record['mesh']!=VENEER or a.get_actor_label()==record['label'])]
            assert len(matches)<=1
            if matches:
                actor=matches[0];assert pose_key(actor_pose(actor))==pose_key(record['pose'])
            else:
                p=record['pose'];r=p['rotation']
                actor=actors.spawn_actor_from_class(ue.StaticMeshActor,ue.Vector(*p['location']),ue.Rotator(pitch=r[0],yaw=r[1],roll=r[2]),transient=False)
                assert actor;actor.set_actor_label(record['label']);actor.set_actor_scale3d(ue.Vector(*p['scale']))
                actor.set_folder_path('Integrated review/'+record['folder']);actor.set_editor_property('tags',[ue.Name(t) for t in record['tags']])
                assert component(actor).set_static_mesh(assets.load_asset(record['mesh']))
                report['created'].append(record['label'])
            c=component(actor);c.set_mobility(getattr(ue.ComponentMobility,record['mobility']))
            c.set_collision_profile_name(record['collisionProfile']);c.set_collision_enabled(getattr(ue.CollisionEnabled,record['collisionEnabled']))
            apply_materials(c,record);verify_mesh(actor,record)
        light_record=selection['doorwayLight']
        if light_record:
            assert not any(a.get_actor_label()==light_record['label'] for a in actors.get_all_level_actors())
            p=light_record['pose'];r=p['rotation']
            actor=actors.spawn_actor_from_class(ue.RectLight,ue.Vector(*p['location']),ue.Rotator(pitch=r[0],yaw=r[1],roll=r[2]),transient=False);assert actor
            actor.set_actor_label(light_record['label']);actor.set_actor_scale3d(ue.Vector(*p['scale']))
            c=actor.get_component_by_class(ue.RectLightComponent);c.set_mobility(ue.ComponentMobility.MOVABLE)
            c.set_editor_property('intensity_units',ue.LightUnits.LUMENS)
            for key,value in light_record['properties'].items():c.set_editor_property(key,value)
            c.set_editor_property('light_color',ue.Color(*light_record['lightColor']))
            report['created'].append(light_record['label'])
        if selection['atmosphere']:
            report['atmosphere']=_build_atmosphere(ue,selection['atmosphere'])
            report['created'].extend(report['atmosphere']['createdActorLabels'])
        current_snapshot=numeric_snapshot()
        assert all(current_snapshot.get(name)==row for name,row in baseline.items()),'Base actor transform/mesh changed'
        assert base_exposure==[a.get_editor_property('settings').export_text() for a in actors.get_all_level_actors() if isinstance(a,ue.PostProcessVolume)]
        assert levels.save_current_level() and levels.load_level(TARGET)
        for record in assigned+donor_records:
            matches=[a for a in actors.get_all_level_actors() if mesh_path(a)==record['mesh'] and (record['mesh']!=VENEER or a.get_actor_label()==record['label'])]
            assert len(matches)==1
            if record in assigned:
                assert [path_of(component(matches[0]).get_material(i)) for i in range(component(matches[0]).get_num_materials())]==record['materials']
            else:verify_mesh(matches[0],record)
        current_snapshot=numeric_snapshot()
        assert all(current_snapshot.get(name)==row for name,row in baseline.items())
        assert base_exposure==[a.get_editor_property('settings').export_text() for a in actors.get_all_level_actors() if isinstance(a,ue.PostProcessVolume)]
        if light_record:
            matching=[a for a in actors.get_all_level_actors() if a.get_actor_label()==light_record['label']];assert len(matching)==1
            c=matching[0].get_component_by_class(ue.RectLightComponent)
            assert pose_key(actor_pose(matching[0]))==pose_key(light_record['pose'])
            assert all(c.get_editor_property(k)==v for k,v in light_record['properties'].items())
        if selection['atmosphere']:
            report['atmosphere'].update(_verify_atmosphere(ue,selection['atmosphere']))
            report['cloudWindIntegrated']=True
        report.update(status='integrated_review_saved_reopened_visual_runtime_acceptance_pending',
            architectureOverrideCount=len(assigned),veneerCount=len(selection['veneers']),vesselCount=len(selection['vessels']),aronPartCount=len(selection['aron']),
            baseExposureUnchanged=True,baseActorGeometryTransformsUnchanged=True,targetSha256=sha(disk(TARGET)))
    except Exception as error:
        report.update(status='failed_partial_integrated_review_preserved',error=str(error));raise
    finally:
        report['sourceMapsUnchanged']=all(sha(disk(source))==value for source,value in protected.items())
        if selection['atmosphere']:
            report['atmosphereSourceAssetsUnchanged']=all(sha(Path(path))==value for path,value in selection['atmosphere']['sourceAssetHashes'].items())
            assert report['atmosphereSourceAssetsUnchanged']
        receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        assert report['sourceMapsUnchanged']
    return report


ATMOSPHERE_MAP='/Game/MikdashV3/MaterialReview/AtmospherePilotV1/Maps/CourtyardAtmosphere'
ATMOSPHERE_SEQUENCE='/Game/MikdashV3/MaterialReview/AtmospherePilotV1/LS_GentleVariableWind'
ATMOSPHERE_NEW='/Game/MikdashV3/IntegratedReviewV2/Atmosphere/LS_GentleVariableWind'
WIND_KEYS=((0,.18,.25),(12,.24,.32),(26,.42,.48),(39,.21,.29),(55,.32,.40),(72,.18,.25))


def _sequence_keys(sequence):
    """SequencerScripting native key APIs; times use display-rate frames."""
    rows={}
    for binding in sequence.get_bindings():
        for track in binding.get_tracks():
            name=str(track.get_property_name())
            assert name in ('Strength','Speed') and name not in rows
            sections=track.get_sections();assert len(sections)==1
            channels=sections[0].get_all_channels();assert len(channels)==1
            values=[]
            for key in channels[0].get_keys():
                frame=key.get_time()
                assert abs(frame.sub_frame)<1e-6
                values.append([frame.frame_number.value,key.get_value()])
            rows[name]=sorted(values)
    assert set(rows)=={'Strength','Speed'}
    for name,index in [('Strength',1),('Speed',2)]:
        expected=[[key[0]*30,key[index]] for key in WIND_KEYS]
        assert len(rows[name])==len(expected)
        assert all(a[0]==b[0] and abs(a[1]-b[1])<1e-6 for a,b in zip(rows[name],expected))
    return rows


def _collect_atmosphere(ue):
    levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    assert levels.load_level(ATMOSPHERE_MAP)
    all_actors=actors.get_all_level_actors()
    def one(cls,label):
        matches=[a for a in all_actors if isinstance(a,cls) and a.get_actor_label()==label]
        assert len(matches)==1;return matches[0]
    cloud=one(ue.VolumetricCloud,'Review_VolumetricCloud')
    wind=one(ue.WindDirectionalSource,'Review_GentleVariableWind')
    player=one(ue.LevelSequenceActor,'Review_WindSequence')
    cc=cloud.get_component_by_class(ue.VolumetricCloudComponent)
    wc=wind.get_component_by_class(ue.WindDirectionalSourceComponent)
    sequence=player.get_sequence();assert path_of(sequence)==ATMOSPHERE_SEQUENCE
    rate=sequence.get_display_rate();assert rate.numerator==30 and rate.denominator==1
    assert sequence.get_playback_start()==0 and sequence.get_playback_end()==2160
    material=path_of(cc.get_editor_property('material'))
    assert material=='/Game/MikdashV3/MaterialReview/AtmospherePilotV1/MI_Cloud'
    asset_files=[ROOT/('Content/'+p[6:]+'.uasset') for p in (material,ATMOSPHERE_SEQUENCE)]
    return dict(sourceMap=ATMOSPHERE_MAP,sourceMapSha256=sha(disk(ATMOSPHERE_MAP)),
        sourceAssetHashes={str(p):sha(p) for p in asset_files},cloudMaterial=material,
        cloudPose=actor_pose(cloud),windPose=actor_pose(wind),
        cloudProperties={p:cc.get_editor_property(p) for p in ['layer_bottom_altitude','layer_height']},
        windProperties={p:wc.get_editor_property(p) for p in ['strength','speed','min_gust_amount','max_gust_amount','point_wind']},
        sequenceKeys=_sequence_keys(sequence),sourceBindingIds=[b.get_id().export_text() for b in sequence.get_bindings()],
        sourceRecipeSha256=sha(ROOT/'Scripts/build_atmosphere_pilot.py'),
        limitation='Cloud visual donor integrated; wind motion and generic tree/cloth response remain unverified. No automatic cloud-wind coupling.')


def _build_atmosphere(ue,record):
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    assert not assets.does_asset_exist(ATMOSPHERE_NEW)
    existing=actors.get_all_level_actors()
    assert not any(isinstance(a,(ue.VolumetricCloud,ue.WindDirectionalSource)) for a in existing)
    assert not any(a.get_actor_label()=='IntegratedReview_WindSequence' for a in existing)
    def spawn(cls,label,pose):
        r=pose['rotation'];a=actors.spawn_actor_from_class(cls,ue.Vector(*pose['location']),ue.Rotator(pitch=r[0],yaw=r[1],roll=r[2]),transient=False)
        assert a;a.set_actor_scale3d(ue.Vector(*pose['scale']));a.set_actor_label(label)
        a.set_folder_path('Integrated review/Atmosphere');a.set_editor_property('tags',[ue.Name('IntegratedReviewAtmosphereV1')])
        assert not a.get_editor_property('is_editor_only_actor');return a
    cloud=spawn(ue.VolumetricCloud,'IntegratedReview_VolumetricCloud',record['cloudPose'])
    cc=cloud.get_component_by_class(ue.VolumetricCloudComponent)
    cc.set_material(assets.load_asset(record['cloudMaterial']))
    cc.set_layer_bottom_altitude(record['cloudProperties']['layer_bottom_altitude'])
    cc.set_layer_height(record['cloudProperties']['layer_height'])
    wind=spawn(ue.WindDirectionalSource,'IntegratedReview_GentleVariableWind',record['windPose'])
    wc=wind.get_component_by_class(ue.WindDirectionalSourceComponent)
    assert not record['windProperties']['point_wind']
    wc.set_strength(record['windProperties']['strength']);wc.set_speed(record['windProperties']['speed'])
    wc.set_minimum_gust_amount(record['windProperties']['min_gust_amount']);wc.set_maximum_gust_amount(record['windProperties']['max_gust_amount'])
    sequence=ue.AssetToolsHelpers.get_asset_tools().create_asset('LS_GentleVariableWind',ATMOSPHERE_NEW.rsplit('/',1)[0],ue.LevelSequence,ue.LevelSequenceFactoryNew());assert sequence
    sequence.set_display_rate(ue.FrameRate(30,1));sequence.set_playback_start(0);sequence.set_playback_end(2160)
    # New bindings are created from actual actors in the NEW saved map. No donor
    # sequence duplication, donor GUID substitution, or stale object path copying.
    parent=sequence.add_possessable(wind);child=sequence.add_possessable(wc);child.set_parent(parent)
    for prop,keys in record['sequenceKeys'].items():
        track=child.add_track(ue.MovieSceneFloatTrack);track.set_property_name_and_path(prop,prop)
        section=track.add_section();section.set_range(0,2161)
        channels=section.get_all_channels();assert len(channels)==1
        for frame,value in keys:channels[0].add_key(ue.FrameNumber(frame),value,interpolation=ue.MovieSceneKeyInterpolation.LINEAR)
    assert assets.save_loaded_asset(sequence,only_if_is_dirty=False)
    identity=dict(location=[0,0,0],rotation=[0,0,0],scale=[1,1,1])
    player=spawn(ue.LevelSequenceActor,'IntegratedReview_WindSequence',identity)
    settings=ue.MovieSceneSequencePlaybackSettings();settings.set_editor_property('auto_play',True)
    settings.set_editor_property('loop_count',ue.MovieSceneSequenceLoopCount(-1))
    settings.set_editor_property('disable_camera_cuts',True)
    settings.set_editor_property('disable_movement_input',False);settings.set_editor_property('disable_look_at_input',False)
    player.set_editor_property('playback_settings',settings);player.set_sequence(sequence)
    return dict(sequence=ATMOSPHERE_NEW,cloudMaterial=record['cloudMaterial'],
        createdActorLabels=['IntegratedReview_VolumetricCloud','IntegratedReview_GentleVariableWind','IntegratedReview_WindSequence'],
        bindingIds=[parent.get_id().export_text(),child.get_id().export_text()],runtimeMotionAcceptance='PENDING')


def _verify_atmosphere(ue,record):
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
    def one(label):
        matches=[a for a in actors if a.get_actor_label()==label];assert len(matches)==1;return matches[0]
    cloud=one('IntegratedReview_VolumetricCloud');wind=one('IntegratedReview_GentleVariableWind');player=one('IntegratedReview_WindSequence')
    assert actor_pose(cloud)==record['cloudPose'] and actor_pose(wind)==record['windPose']
    cc=cloud.get_component_by_class(ue.VolumetricCloudComponent);wc=wind.get_component_by_class(ue.WindDirectionalSourceComponent)
    assert path_of(cc.get_editor_property('material'))==record['cloudMaterial']
    assert all(abs(cc.get_editor_property(k)-v)<1e-6 for k,v in record['cloudProperties'].items())
    assert all(abs(wc.get_editor_property(k)-v)<1e-6 for k,v in record['windProperties'].items())
    sequence=player.get_sequence();assert path_of(sequence)==ATMOSPHERE_NEW
    assert _sequence_keys(sequence)==record['sequenceKeys']
    bindings=sequence.get_bindings();assert len(bindings)==2
    assert all(b.get_id().export_text() not in record['sourceBindingIds'] for b in bindings)
    parent_matches=[b for b in bindings if wind in sequence.locate_bound_objects(b,editor.get_editor_world())]
    assert len(parent_matches)==1,'New actor binding must resolve in integrated world'
    parent=parent_matches[0]
    children=[b for b in bindings if b.get_parent().get_id().export_text()==parent.get_id().export_text()]
    assert len(children)==1 and wc in sequence.locate_bound_objects(children[0],wind),'New component binding must resolve against new actor'
    settings=player.get_editor_property('playback_settings')
    assert settings.get_editor_property('auto_play') and settings.get_editor_property('disable_camera_cuts')
    assert settings.get_editor_property('loop_count').get_editor_property('value')==-1
    assert not settings.get_editor_property('disable_movement_input') and not settings.get_editor_property('disable_look_at_input')
    return dict(serializedBindingsResolveToNewActorAndComponent=True,loopKeysAndCloudReadbackPassed=True,
        windMotion='PENDING bounded runtime sampling; serialization is not motion proof')

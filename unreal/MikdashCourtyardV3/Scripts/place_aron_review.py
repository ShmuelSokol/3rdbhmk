"""Explicit place_review() for existing16 Aron study parts in CourtyardGold.

No engine launch. Missing keruvim remain explicit; this is not a complete Aron.
"""
import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone

ROOT=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
FOLDER=ROOT/'SourceAssets/vessels-review/AronStudyV1'
SPEC=ROOT/'SourceAssets/vessels-review/aron-placement-spec.json'
REVIEW='/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold'


def rotate_bounds(local, position):
    return {'min':[position[0]-local['max'][1],position[1]+local['min'][0],position[2]+local['min'][2]],
            'max':[position[0]-local['min'][1],position[1]+local['max'][0],position[2]+local['max'][2]]}


def place_review():
    import unreal as ue
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem);world=editor.get_editor_world()
    if Path(ue.Paths.project_dir()).resolve()!=ROOT or editor.get_game_world():raise RuntimeError('Use intended editor outside gameplay')
    if world.get_outermost().get_name()!=REVIEW:raise RuntimeError('Load saved CourtyardGold first')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Resolve dirty work before checkpointed placement')
    spec=json.loads(SPEC.read_text());position=spec['position_cm']
    native=json.loads((FOLDER/'native-import-v3.json').read_text())
    if native['status']!='unassigned_native_study_parts_saved_visual_review_pending':raise RuntimeError('Successful AronV3 import receipt required')
    source=json.loads((FOLDER/'geometry-manifest.json').read_text())
    records={p['name']:p for p in source['parts']}
    if len(records)!=16:raise RuntimeError('Expected16 source parts')
    api=ue.get_editor_subsystem(ue.EditorActorSubsystem);actors=api.get_all_level_actors()
    labels=['REVIEW_AronIncomplete_'+name for name in records]
    if any(a.get_actor_label() in labels for a in actors):raise RuntimeError('Existing Aron review actors preserved')
    floors=[]
    for actor in actors:
        for component in actor.get_components_by_class(ue.StaticMeshComponent):
            mesh=component.get_editor_property('static_mesh')
            if mesh and mesh.get_path_name().split('.')[0]==spec['floor_asset']:floors.append((actor,component,mesh))
    if len(floors)!=1:raise RuntimeError('Expected exactly one measured Kodesh floor component')
    floor,component,floor_mesh=floors[0]
    loc=component.get_world_location();rot=component.get_world_rotation();scale=component.get_world_scale()
    if max(abs(v) for v in (loc.x,loc.y,loc.z,rot.pitch,rot.yaw,rot.roll))>.001 or max(abs(v-1) for v in (scale.x,scale.y,scale.z))>.001:raise RuntimeError('Floor transform changed')
    b=floor_mesh.get_bounding_box();actual_floor={'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]}
    if max(abs(actual_floor[k][i]-spec['floor_bounds_cm'][k][i]) for k in actual_floor for i in range(3))>.05:raise RuntimeError('Floor dimensions changed')
    planned=[]
    for name,record in records.items():
        path='/Game/MikdashV3/MaterialReview/AronStudyV3/Meshes/'+name
        mesh=ue.load_asset(path)
        if not isinstance(mesh,ue.StaticMesh) or mesh.get_path_name() not in native['created']:raise RuntimeError('Reviewed Aron part missing: '+name)
        b=mesh.get_bounding_box();local={'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]}
        if max(abs(local[k][i]-record['expectedBoundsCm'][k][i]) for k in local for i in range(3))>.05 or mesh.get_num_triangles(0)!=record['triangles']:raise RuntimeError('Aron native geometry changed: '+name)
        planned.append(dict(name=name,mesh=mesh,bounds=rotate_bounds(local,position)))
    total={key:[fn(p['bounds'][key][i] for p in planned) for i in range(3)] for key,fn in [('min',min),('max',max)]}
    if any(total['min'][i]<=actual_floor['min'][i] or total['max'][i]>=actual_floor['max'][i] for i in (0,1)) or abs(total['min'][2]-actual_floor['max'][2])>.05:raise RuntimeError('Assembly does not fit measured Kodesh floor')
    for fx in (.05,.5,.95):
        for fy in (.05,.5,.95):
            x=total['min'][0]+fx*(total['max'][0]-total['min'][0]);y=total['min'][1]+fy*(total['max'][1]-total['min'][1])
            hit=ue.SystemLibrary.line_trace_single_by_profile(world_context_object=world,start=ue.Vector(x,y,925.5),end=ue.Vector(x,y,total['max'][2]+.5),profile_name='Pawn',trace_complex=True,actors_to_ignore=[floor],draw_debug_type=ue.DrawDebugTrace.NONE,ignore_self=False)
            if hit:raise RuntimeError('Existing blocking geometry at Aron clearance probe')
    original=ROOT/'Content/MikdashV3/Maps/Courtyard.umap'
    review_file=ROOT/'Content/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold.umap'
    before=hashlib.sha256(original.read_bytes()).hexdigest();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint=ROOT.parent/'ReviewCheckpoints'/('Aron-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False);shutil.copy2(review_file,checkpoint/'CourtyardGold.umap')
    receipt=dict(status='checkpointed_placement_started',review_map=REVIEW,checkpoint=str(checkpoint),original_courtyard_sha_before=before,review_sha_before=hashlib.sha256(review_file.read_bytes()).hexdigest(),position_cm=position,yaw_degrees=90,assembly_bounds_cm=total,actors=[],keruvim='NOT_MODELED_INCOMPLETE_ARON',limitations=spec['limitations'])
    receipt_path=FOLDER/('placement-'+stamp+'.json')
    def write():receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    write()
    try:
        for p in planned:
            actor=api.spawn_actor_from_class(ue.StaticMeshActor,ue.Vector(*position),ue.Rotator(pitch=0,yaw=90,roll=0),transient=False)
            if not actor:raise RuntimeError('Aron actor creation failed')
            label='REVIEW_AronIncomplete_'+p['name'];actor.set_actor_label(label);actor.set_folder_path('Review/Aron_Incomplete_NoKeruvim')
            component=actor.get_component_by_class(ue.StaticMeshComponent)
            if not component.set_static_mesh(p['mesh']):raise RuntimeError('Aron mesh assignment failed')
            component.set_collision_profile_name('NoCollision')
            receipt['actors'].append(dict(label=label,asset=p['mesh'].get_path_name(),expected_bounds_cm=p['bounds']))
        levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.save_current_level() or not levels.load_level(REVIEW):raise RuntimeError('Review save/reopen failed')
        reopened=api.get_all_level_actors()
        for entry in receipt['actors']:
            matching=[a for a in reopened if a.get_actor_label()==entry['label']]
            if len(matching)!=1:raise RuntimeError('Reopened part count differs')
            actor=matching[0];component=actor.get_component_by_class(ue.StaticMeshComponent)
            if component.get_editor_property('static_mesh').get_path_name()!=entry['asset']:raise RuntimeError('Reopened mesh assignment differs')
            o,e=actor.get_actor_bounds(False);actual={'min':[o.x-e.x,o.y-e.y,o.z-e.z],'max':[o.x+e.x,o.y+e.y,o.z+e.z]}
            error=max(abs(actual[k][i]-entry['expected_bounds_cm'][k][i]) for k in actual for i in range(3))
            if error>.05:raise RuntimeError('Reopened Aron part bounds differ')
            entry['reopened_bounds_error_cm']=error
        after=hashlib.sha256(original.read_bytes()).hexdigest();receipt.update(original_courtyard_sha_after=after,original_courtyard_unchanged=before==after)
        if before!=after:raise RuntimeError('Original Courtyard changed')
        receipt['status']='sixteen_aron_parts_saved_reopened_in_review_keruvim_missing_visual_review_pending'
    except Exception as error:
        receipt.update(status='failed_partial_review_state_preserved',error=str(error));raise
    finally:write()
    return receipt

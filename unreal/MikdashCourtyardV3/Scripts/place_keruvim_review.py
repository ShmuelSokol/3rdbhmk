"""Explicit review-only keruvim placement; root runs place_review(), no auto execution."""
import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime,timezone
ROOT=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
FOLDER=ROOT/'SourceAssets/vessels-review/KeruvimStudyV1'
REVIEW='/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold'
DEST='/Game/MikdashV3/MaterialReview/KeruvimStudyV1/Meshes/SM_KeruvimStudyV1'
LABEL='REVIEW_KeruvimStudyV1_Interpretive'


def bounds(actor):
    o,e=actor.get_actor_bounds(False)
    return {'min':[o.x-e.x,o.y-e.y,o.z-e.z],'max':[o.x+e.x,o.y+e.y,o.z+e.z]}


def rotate(local,p):
    return {'min':[p[0]-local['max'][1],p[1]+local['min'][0],p[2]+local['min'][2]],'max':[p[0]-local['min'][1],p[1]+local['max'][0],p[2]+local['max'][2]]}


def error(a,b):return max(abs(a[k][i]-b[k][i]) for k in a for i in range(3))


def place_review():
    import unreal as ue
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem);world=editor.get_editor_world()
    if Path(ue.Paths.project_dir()).resolve()!=ROOT or editor.get_game_world():raise RuntimeError('Use intended editor outside gameplay')
    if world.get_outermost().get_name()!=REVIEW:raise RuntimeError('Load saved CourtyardGold first')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Resolve dirty work first')
    spec=json.loads((FOLDER/'placement-spec.json').read_text());pos=spec['position_cm']
    native=json.loads((FOLDER/'native-import.json').read_text());source=json.loads((FOLDER/'geometry-manifest.json').read_text());model=json.loads((FOLDER/'model-spec.json').read_text())
    if native['status']!='native_asset_saved_unassigned_visual_review_pending':raise RuntimeError('Successful native receipt required')
    if hashlib.sha256((FOLDER/source['file']).read_bytes()).hexdigest()!=source['sha256'] or hashlib.sha256((FOLDER/'model-spec.json').read_bytes()).hexdigest()!=source['source_spec_sha256']:raise RuntimeError('Source changed')
    if hashlib.sha256((ROOT/'SourceAssets/vessels-review/aron-study-v1-spec.json').read_bytes()).hexdigest()!=model['ark_spec_sha256']:raise RuntimeError('Coupled Aron source changed')
    api=ue.get_editor_subsystem(ue.EditorActorSubsystem);actors=api.get_all_level_actors()
    if any(a.get_actor_label()==LABEL for a in actors):raise RuntimeError('Existing study preserved')
    aron=json.loads((ROOT/'SourceAssets/vessels-review/AronStudyV1/geometry-manifest.json').read_text())
    if len(aron['parts'])!=16:raise RuntimeError('Expected sixteen Aron parts')
    existing=[];cover=None
    for record in aron['parts']:
        matching=[a for a in actors if a.get_actor_label()=='REVIEW_AronIncomplete_'+record['name']]
        if len(matching)!=1:raise RuntimeError('Missing or duplicated Aron part '+record['name'])
        actor=matching[0];component=actor.get_component_by_class(ue.StaticMeshComponent);mesh=component.get_editor_property('static_mesh')
        if not mesh or mesh.get_path_name().split('.')[0]!='/Game/MikdashV3/MaterialReview/AronStudyV3/Meshes/'+record['name']:raise RuntimeError('Aron asset changed')
        loc=component.get_world_location();rot=component.get_world_rotation();scale=component.get_world_scale()
        if max(abs(loc.x-pos[0]),abs(loc.y-pos[1]),abs(loc.z-pos[2]),abs(rot.yaw-90),abs(rot.pitch),abs(rot.roll),abs(scale.x-1),abs(scale.y-1),abs(scale.z-1))>.001:raise RuntimeError('Aron transform changed')
        if error(bounds(actor),rotate(record['expectedBoundsCm'],pos))>.05:raise RuntimeError('Aron bounds changed')
        existing.append(actor)
        if 'KaporetCover' in record['name']:cover=bounds(actor)
    if not cover or abs(cover['max'][2]-pos[2]-spec['cover_top_local_cm'])>.05:raise RuntimeError('Measured kaporet top changed')
    mesh=ue.load_asset(DEST)
    if not isinstance(mesh,ue.StaticMesh) or mesh.get_path_name() not in native['created']:raise RuntimeError('Imported keruvim missing')
    b=mesh.get_bounding_box();local={'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]}
    if error(local,source['bounds_cm'])>.05 or mesh.get_num_triangles(0)!=source['triangles']:raise RuntimeError('Keruvim geometry changed')
    planned=rotate(local,pos)
    if abs(planned['min'][2]-cover['max'][2])>.05 or any(planned['min'][i]<cover['min'][i] or planned['max'][i]>cover['max'][i] for i in (0,1)):raise RuntimeError('Keruvim contact or cover footprint invalid')
    if abs(source['wing_underside_clearance_cm']-spec['wing_clearance_cm'])>.001:raise RuntimeError('Wing clearance source differs')
    original=ROOT/'Content/MikdashV3/Maps/Courtyard.umap';review_file=ROOT/'Content/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold.umap'
    before=hashlib.sha256(original.read_bytes()).hexdigest();stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint=ROOT.parent/'ReviewCheckpoints'/('Keruvim-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False);shutil.copy2(review_file,checkpoint/'CourtyardGold.umap')
    receipt=dict(status='checkpointed_placement_started',checkpoint=str(checkpoint),review_map=REVIEW,position_cm=pos,yaw_degrees=90,cover_world_bounds_cm=cover,planned_world_bounds_cm=planned,original_courtyard_sha_before=before,limitations=spec['limitations'])
    receipt_path=FOLDER/('placement-'+stamp+'.json')
    def write():receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    write()
    try:
        actor=api.spawn_actor_from_class(ue.StaticMeshActor,ue.Vector(*pos),ue.Rotator(pitch=0,yaw=90,roll=0),transient=False)
        if not actor:raise RuntimeError('Actor creation failed')
        actor.set_actor_label(LABEL);actor.set_folder_path('Review/Aron_InterpretiveKeruvim')
        component=actor.get_component_by_class(ue.StaticMeshComponent)
        if not component.set_static_mesh(mesh):raise RuntimeError('Mesh assignment failed')
        component.set_collision_profile_name('NoCollision')
        levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.save_current_level() or not levels.load_level(REVIEW):raise RuntimeError('Save/reopen failed')
        reopened=api.get_all_level_actors();matching=[a for a in reopened if a.get_actor_label()==LABEL]
        if len(matching)!=1:raise RuntimeError('Reopened count differs')
        actor=matching[0];component=actor.get_component_by_class(ue.StaticMeshComponent)
        if component.get_editor_property('static_mesh').get_path_name().split('.')[0]!=DEST or error(bounds(actor),planned)>.05:raise RuntimeError('Reopened mesh/bounds differ')
        for record in aron['parts']:
            matching=[a for a in reopened if a.get_actor_label()=='REVIEW_AronIncomplete_'+record['name']]
            if len(matching)!=1 or error(bounds(matching[0]),rotate(record['expectedBoundsCm'],pos))>.05:raise RuntimeError('Reopened Aron changed')
        after=hashlib.sha256(original.read_bytes()).hexdigest();receipt.update(original_courtyard_sha_after=after,original_courtyard_unchanged=before==after,reopened_world_bounds_cm=bounds(actor))
        if before!=after:raise RuntimeError('Original Courtyard changed')
        receipt['status']='keruvim_saved_reopened_review_visual_acceptance_pending'
    except Exception as exc:receipt.update(status='failed_partial_review_preserved',error=str(exc));raise
    finally:write()
    return receipt

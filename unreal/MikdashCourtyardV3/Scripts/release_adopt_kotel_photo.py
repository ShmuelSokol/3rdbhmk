"""Explicit adoption of a visually accepted Kotel photo review, V1 or V2 only.
run(version='V2', apply=False) audits donor/main. apply=True additionally requires
visual_accepted=True. Root alone runs native. No image/material/mesh changes.
"""
from pathlib import Path
import json,hashlib,shutil
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
MAIN='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
BASE='/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N002_P001'
OLD='/Game/MikdashV3/MaterialReview/KotelStoneV1/Meshes/SM_KotelFace_Tint'
def disk(p,ext='uasset'):return ROOT/'Content'/(p[6:]+'.'+ext)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(version='V2',apply=False,visual_accepted=False):
 import unreal as u
 assert version in ('V1','V2') and (not apply or visual_accepted),'Explicit visual acceptance required for adoption'
 assert Path(u.Paths.project_dir()).resolve()==ROOT
 ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
 assert not ed.get_game_world() and not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
 assert ed.get_editor_world().get_outermost().get_name()==MAIN,'Load saved main explicitly'
 namespace='/Game/MikdashV3/MaterialReview/KotelPhotoSurface'+version
 donor=namespace+'/Maps/Walkthrough';assert disk(donor,'umap').is_file()
 def path(o):return o.get_path_name().split('.')[0] if o else None
 def vec(v):return [v.x,v.y,v.z]
 def pose(a):
  r=a.get_actor_rotation();return [*vec(a.get_actor_location()),r.pitch,r.yaw,r.roll,*vec(a.get_actor_scale3d())]
 def pose_close(a,b):
  return (max(abs(a[i]-b[i]) for i in range(3))<=.01
   and max(abs((a[i]-b[i]+180)%360-180) for i in range(3,6))<=.01
   and max(abs(a[i]-b[i]) for i in range(6,9))<=1e-4)
 def snapshot():
  rows={}
  for a in actors.get_all_level_actors():
   components=[]
   for c in a.get_components_by_class(u.StaticMeshComponent):
    components.append(dict(name=c.get_name(),mesh=path(c.get_editor_property('static_mesh')),materials=[path(c.get_material(i)) for i in range(c.get_num_materials())],collision=str(c.get_collision_profile_name()),visible=bool(c.get_editor_property('visible')),hidden=bool(c.get_editor_property('hidden_in_game'))))
   rows[a.get_name()]=dict(label=a.get_actor_label(),actorClass=a.get_class().get_path_name(),pose=pose(a),components=components)
  return rows
 def selected(rows,photo=False):
  return {k:v for k,v in rows.items() if (v['label'].startswith('REVIEW_KotelPhoto_') if photo else any(c['mesh']==BASE or (c['mesh'] or '').startswith(OLD) for c in v['components']))}
 def without_visibility(rows):
  result=json.loads(json.dumps(rows))
  for r in result.values():
   for c in r['components']:c.pop('visible');c.pop('hidden')
  return result
 original=snapshot();assert not selected(original,True),'Photo panels already in main; refuse duplicate adoption'
 main_scoped=selected(original);assert len(main_scoped)==7
 protected=[disk(donor,'umap'),disk(BASE),disk('/Game/MikdashV3/Maps/Courtyard','umap'),disk('/Game/MikdashV3/FutureMountV1/L_FutureMount','umap')]
 protected+=list((ROOT/'Content'/namespace[6:]).rglob('*.uasset'))
 protected+=list((ROOT/'Content/MikdashV3/MaterialReview/KotelStoneV1').rglob('*.uasset'))
 before={str(p):sha(p) for p in protected};main_before=sha(disk(MAIN,'umap'))
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=ROOT/'SourceAssets/kotel-detail';receipt=out/('photo-adoption-'+stamp+'.json')
 report=dict(status='started',apply=apply,visualAccepted=visual_accepted,donor=donor,mainBefore=main_before,protectedBefore=before,verificationScope='Actor identity/class/label/pose; all static mesh paths/material slots/collision/visibility. No lighting or other actor properties written.',mapSaved=False)
 try:
  assert levels.load_level(donor) and ed.get_editor_world().get_outermost().get_name()==donor
  donor_rows=snapshot();panels=selected(donor_rows,True);assert len(panels)==4
  assert {r['label'] for r in panels.values()}=={'REVIEW_KotelPhoto_'+str(i) for i in (24,25,0,1)}
  assert without_visibility(selected(donor_rows))==without_visibility(main_scoped),'Donor base/overlay mismatch'
  donor_actors={a.get_name():a for a in actors.get_all_level_actors()}
  for name,row in panels.items():
   actor=donor_actors[name];component=actor.get_component_by_class(u.StaticMeshComponent)
   assert component==actor.get_editor_property('root_component'),'Photo mesh must be actor root'
   # A root component relative transform is the actor transform, not an identity
   # offset. Reject attachments so copying actor pose copies the complete plane pose.
   assert component.get_attach_parent() is None,'Photo root must be unattached'
   relative_location=component.get_editor_property('relative_location')
   relative_rotation=component.get_editor_property('relative_rotation')
   relative_scale=component.get_editor_property('relative_scale3d')
   relative=[*vec(relative_location),relative_rotation.pitch,relative_rotation.yaw,relative_rotation.roll,*vec(relative_scale)]
   assert pose_close(relative,row['pose']),'Root relative transform differs from actor pose'
   assert len(row['components'])==1
   c=row['components'][0];assert c['mesh']=='/Engine/BasicShapes/Plane' and c['collision']=='NoCollision' and c['visible'] and not c['hidden']
   assert c['materials'] and all((m or '').startswith(namespace+'/') for m in c['materials'])
  for row in selected(donor_rows).values():
   for c in row['components']:
    if (c['mesh'] or '').startswith(OLD):assert not c['visible'] and c['hidden']
  assert levels.load_level(MAIN) and ed.get_editor_world().get_outermost().get_name()==MAIN and snapshot()==original
  report['panels']=panels
  if not apply:report['status']='dry_run_donor_main_verified_no_mutation';return report
  cp=ROOT.parent/'ReviewCheckpoints'/('AdoptKotelPhoto-'+stamp);cp.mkdir(parents=True,exist_ok=False)
  allfiles=[disk(MAIN,'umap')]+protected
  for f in allfiles:
   q=cp/f.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,q);assert sha(q)==sha(f)
  # Preserve external actor packages if a future map enables OFPA.
  for directory in ('__ExternalActors__','__ExternalObjects__'):
   folder=ROOT/'Content'/directory/MAIN[6:]
   if folder.exists():shutil.copytree(folder,cp/'Content'/directory/MAIN[6:])
  report['checkpoint']=str(cp);receipt.write_text(json.dumps(report,indent=2))
  new_names=[]
  for row in panels.values():
   p=row['pose'];a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*p[:3]),u.Rotator(pitch=p[3],yaw=p[4],roll=p[5]),transient=False);assert a
   new_names.append(a.get_name());a.set_actor_label(row['label']);a.set_actor_scale3d(u.Vector(*p[6:]))
   c=a.get_component_by_class(u.StaticMeshComponent);state=row['components'][0];assert c.set_static_mesh(u.load_asset(state['mesh']))
   c.set_collision_profile_name('NoCollision')
   assert c.get_num_materials()==len(state['materials'])
   for i,m in enumerate(state['materials']):c.set_material(i,u.load_asset(m))
  for a in actors.get_all_level_actors():
   if a.get_name() in main_scoped:
    for c in a.get_components_by_class(u.StaticMeshComponent):
     if (path(c.get_editor_property('static_mesh')) or '').startswith(OLD):c.set_visibility(False,True);c.set_hidden_in_game(True,True)
  def verify():
   current=snapshot();assert len(current)==len(original)+4
   for name,row in original.items():
    if name in main_scoped:assert without_visibility({name:current[name]})==without_visibility({name:row})
    else:assert current[name]==row,'Unrelated actor state changed'
   assert selected(current)==selected(donor_rows),'Base/overlay state differs from accepted donor'
   actual={r['label']:r for r in selected(current,True).values()}
   for row in panels.values():
    got=actual[row['label']];assert got['actorClass']==row['actorClass'] and pose_close(got['pose'],row['pose'])
    assert [{k:v for k,v in c.items() if k!='name'} for c in got['components']]==[{k:v for k,v in c.items() if k!='name'} for c in row['components']]
  verify();assert levels.save_current_level();report.update(mapSaved=True,mainAfterSave=sha(disk(MAIN,'umap')),status='saved_reopen_pending');receipt.write_text(json.dumps(report,indent=2))
  assert levels.load_level(MAIN) and ed.get_editor_world().get_outermost().get_name()==MAIN
  verify();report['status']='adopted_saved_reopened_visual_previously_accepted';return report
 except Exception as exc:report.update(status='failed_after_save' if report['mapSaved'] else 'failed_before_save',error=repr(exc));raise
 finally:
  report['mainAfter']=sha(disk(MAIN,'umap'));report['protectedAfter']={str(p):sha(p) for p in protected};report['protectedUnchanged']=report['protectedAfter']==before
  if not report['protectedUnchanged']:report['status']='failed_protected_hash_guard'
  receipt.write_text(json.dumps(report,indent=2)+'\n');assert report['protectedUnchanged']

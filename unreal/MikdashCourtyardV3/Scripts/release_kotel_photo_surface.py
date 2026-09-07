"""Photo-based Kotel review only. Explicit run(apply=False/True); no auto execution.
Uses root-approved cleaned project PNG only, never private original attachments.
Four audited contiguous original wall faces share ONE panorama without repeating.
Source wall/collision retained, six invented coursing overlays hidden in review only.
Plane photo is a visual study: captured lighting, resolution and left/right alignment
require acceptance; no inferred relief, archaeological measurement or exact future claim.
"""
from pathlib import Path
import json,hashlib,math,shutil,struct
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
MAIN='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
DEST='/Game/MikdashV3/MaterialReview/KotelPhotoSurfaceV1'
OLD='/Game/MikdashV3/MaterialReview/KotelStoneV1'
FOLDER=ROOT/'SourceAssets/kotel-detail/PhotoSurfaceV1'
IMAGE=FOLDER/'kotel-wall-cleaned.png'
MANIFEST=ROOT/'SourceAssets/kotel-detail/KotelStoneV1/manifest.json'
BASE='/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N002_P001'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def disk(p,ext='uasset'):return ROOT/'Content'/(p[6:]+'.'+ext)
def plan():
 m=json.loads(MANIFEST.read_text());faces=sorted(m['faces'],key=lambda f:f['a'][1]);assert [f['edge'] for f in faces]==[24,25,0,1]
 for a,b in zip(faces,faces[1:]):assert math.dist(a['b'],b['a'])<.001
 lo=m['sourceBase']['boundsCm']['min'][2];hi=m['sourceBase']['boundsCm']['max'][2];assert abs(hi-lo-2000)<.001
 total=sum(f['lengthCm'] for f in faces);offset=0;rows=[]
 for f in faces:
  t=f['tangent'];n=f['normal'];assert n[0]<-.8 and abs(sum(a*b for a,b in zip(t,n)))<1e-6
  rows.append(dict(edge=f['edge'],a=f['a'],b=f['b'],tangent=t,normal=n,lengthCm=f['lengthCm'],startCm=offset,
   centerCm=[(f['a'][k]+f['b'][k])/2+n[k]*1.0 for k in range(2)]+[(lo+hi)/2],
   uRange=[offset/total,(offset+f['lengthCm'])/total]))
  offset+=f['lengthCm']
 return dict(sourceManifestSha256=sha(MANIFEST),faces=rows,totalWidthCm=total,bottomCm=lo,topCm=hi,heightCm=hi-lo,
  targetAspect=total/(hi-lo),offsetCm=1.0,scope='Source footprint-derived photo-facing planes; 1 panorama across 4 faces; no image repeating or per-block mortar; source wall/collision retained',
  approval='Cleaned supplied photo derivative only; original attachments stay private; left/right orientation, photo perspective/lighting and aspect fit unapproved')
def run(apply=False,flip_u=False,uv_scale=(1.0,1.0),uv_offset=(0.0,0.0)):
 import unreal as u
 assert Path(u.Paths.project_dir()).resolve()==ROOT
 ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);lib=u.EditorAssetLibrary
 assert not ed.get_game_world() and not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
 assert ed.get_editor_world().get_outermost().get_name()==MAIN
 assert len(uv_scale)==2 and len(uv_offset)==2 and all(math.isfinite(x) for x in (*uv_scale,*uv_offset))
 assert all(.1<=x<=10 for x in uv_scale) and all(abs(x)<=2 for x in uv_offset)
 p=plan();assert IMAGE.is_file(),'Root must supply cleaned project PNG'
 header=IMAGE.read_bytes()[:24];assert header[:8]==b'\x89PNG\r\n\x1a\n';width,height=struct.unpack('>II',header[16:24]);assert width>=512 and height>=128
 def path(o):return o.get_path_name().split('.')[0] if o else None
 def pose(a):
  v=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d();return [v.x,v.y,v.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
 def inventory():return {a.get_name():[a.get_actor_label(),a.get_class().get_path_name(),pose(a)] for a in actors.get_all_level_actors()}
 def scoped():
  overlays=[];base=[]
  for a in actors.get_all_level_actors():
   c=a.get_component_by_class(u.StaticMeshComponent);m=c.get_editor_property('static_mesh') if c else None
   if path(m)==BASE:base.append((a,c))
   if path(m) and path(m).startswith(OLD+'/Meshes/SM_KotelFace_Tint'):
    assert a.get_actor_label().startswith('RELEASE_Kotel') and str(c.get_collision_profile_name())=='NoCollision'
    overlays.append((a,c))
  assert len(overlays)==6 and len(base)==1
  for a,c in overlays+base:
   v=pose(a);assert max(abs(x) for x in v[:6])<.001 and max(abs(x-1) for x in v[6:])<.001
  return overlays,base[0]
 overlays,base=scoped();baseline=inventory()
 base_state=dict(pose=pose(base[0]),slots=[path(base[1].get_material(i)) for i in range(base[1].get_num_materials())],collision=str(base[1].get_collision_profile_name()))
 protected=[disk(MAIN,'umap'),disk(BASE),MANIFEST,IMAGE]+list((ROOT/'Content'/OLD[6:]).rglob('*.uasset'))
 protected += [disk('/Game/MikdashV3/Maps/Courtyard','umap'),disk('/Game/MikdashV3/FutureMountV1/L_FutureMount','umap')]
 before={str(f):sha(f) for f in protected};stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');FOLDER.mkdir(parents=True,exist_ok=True)
 receipt=FOLDER/('native-photo-'+stamp+'.json');report=dict(status='dry_run',apply=apply,plan=p,flipU=flip_u,uvScale=list(uv_scale),uvOffset=list(uv_offset),imageSha256=sha(IMAGE),imagePixels=[width,height],imageAspect=width/height,aspectRatioFit=(width/height)/p['targetAspect'],protectedBefore=before,baseBefore=base_state)
 try:
  if not apply:return report
  assert not lib.does_directory_exist(DEST),'Preserve prior/partial native photo study'
  cp=ROOT.parent/'ReviewCheckpoints'/('KotelPhoto-'+stamp);cp.mkdir(parents=True,exist_ok=False)
  for f in protected:
   q=cp/f.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,q);assert sha(q)==before[str(f)]
  report['checkpoint']=str(cp);target=DEST+'/Maps/Walkthrough'
  assert lib.duplicate_asset(MAIN,target) and levels.load_level(target)
  assert ed.get_editor_world().get_outermost().get_name()==target and inventory()==baseline
  overlays,base=scoped()
  task=u.AssetImportTask()
  for k,v in dict(filename=str(IMAGE),destination_path=DEST,destination_name='T_KotelWallPhoto',automated=True,replace_existing=False,save=False).items():task.set_editor_property(k,v)
  tools=u.AssetToolsHelpers.get_asset_tools();tools.import_asset_tasks([task]);objects=task.get_objects();assert len(objects)==1 and isinstance(objects[0],u.Texture2D)
  texture=objects[0];texture.set_editor_property('srgb',True);texture.set_editor_property('address_x',u.TextureAddress.TA_CLAMP);texture.set_editor_property('address_y',u.TextureAddress.TA_CLAMP);assert lib.save_loaded_asset(texture,only_if_is_dirty=False)
  plane=u.load_asset('/Engine/BasicShapes/Plane');assert isinstance(plane,u.StaticMesh)
  bb=plane.get_bounding_box();assert abs(bb.max.x-bb.min.x-100)<.01 and abs(bb.max.y-bb.min.y-100)<.01 and abs(bb.max.z-bb.min.z)<.01
  edit=u.MaterialEditingLibrary;created=[]
  for face in p['faces']:
   mat=tools.create_asset('M_PhotoFace_'+str(face['edge']),DEST,u.Material,u.MaterialFactoryNew());assert mat
   mat.set_editor_property('two_sided',True)
   wp=edit.create_material_expression(mat,u.MaterialExpressionWorldPosition)
   custom=edit.create_material_expression(mat,u.MaterialExpressionCustom);inp=u.CustomInput();inp.set_editor_property('input_name','P');custom.set_editor_property('inputs',[inp]);custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT2)
   ax,ay=face['a'];tx,ty=face['tangent']
   code='float uu=(dot(P.xy-float2(%0.9f,%0.9f),float2(%0.12f,%0.12f))+%0.9f)/%0.9f; return float2(%s,1.0-(P.z-(%0.9f))/%0.9f);'%(ax,ay,tx,ty,face['startCm'],p['totalWidthCm'],'1.0-uu' if flip_u else 'uu',p['bottomCm'],p['heightCm'])
   code=code.replace('return float2(', 'float2 mapped=float2(')
   code+=' return (mapped-.5)*float2(%0.9f,%0.9f)+.5+float2(%0.9f,%0.9f);'%(*uv_scale,*uv_offset)
   custom.set_editor_property('code',code);assert edit.connect_material_expressions(wp,'',custom,'P')
   sample=edit.create_material_expression(mat,u.MaterialExpressionTextureSample);sample.set_editor_property('texture',texture)
   assert edit.connect_material_expressions(custom,'',sample,'UVs');assert edit.connect_material_property(sample,'RGB',u.MaterialProperty.MP_BASE_COLOR)
   rough=edit.create_material_expression(mat,u.MaterialExpressionConstant);rough.set_editor_property('r',.86);assert edit.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
   edit.recompile_material(mat);assert lib.save_loaded_asset(mat,only_if_is_dirty=False)
   # Plane local X follows tangent; local Y is world up; local Z is east-facing.
   # Material is two-sided; the west-facing audited facade remains visible.
   rot=u.MathLibrary.make_rotation_from_axes(u.Vector(tx,ty,0),u.Vector(0,0,1),u.Vector(ty,-tx,0))
   actor=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*face['centerCm']),rot,transient=False);assert actor
   actor.set_actor_label('REVIEW_KotelPhoto_'+str(face['edge']));actor.set_actor_scale3d(u.Vector(face['lengthCm']/100,p['heightCm']/100,1))
   component=actor.get_component_by_class(u.StaticMeshComponent);assert component.set_static_mesh(plane);component.set_collision_profile_name('NoCollision');component.set_material(0,mat)
   created.append(dict(label=actor.get_actor_label(),pose=pose(actor),material=path(mat)))
  for a,c in overlays:c.set_visibility(False,True);c.set_hidden_in_game(True,True)
  current_inventory=inventory()
  assert all(current_inventory.get(k)==v for k,v in baseline.items())
  assert levels.save_current_level();report.update(status='saved_reopen_pending',created=created,reviewMap=target);receipt.write_text(json.dumps(report,indent=2))
  assert levels.load_level(target) and ed.get_editor_world().get_outermost().get_name()==target
  reopened_inventory=inventory()
  assert all(reopened_inventory.get(k)==v for k,v in baseline.items())
  actual={a.get_actor_label():a for a in actors.get_all_level_actors()}
  for row in created:
   a=actual[row['label']];c=a.get_component_by_class(u.StaticMeshComponent);assert max(abs(x-y) for x,y in zip(pose(a),row['pose']))<.001
   assert path(c.get_editor_property('static_mesh'))=='/Engine/BasicShapes/Plane'
   assert path(c.get_material(0))==row['material'] and str(c.get_collision_profile_name())=='NoCollision'
  overlays,base=scoped()
  assert all(not c.get_editor_property('visible') and c.get_editor_property('hidden_in_game') for a,c in overlays)
  assert dict(pose=pose(base[0]),slots=[path(base[1].get_material(i)) for i in range(base[1].get_num_materials())],collision=str(base[1].get_collision_profile_name()))==base_state
  report.update(status='saved_reopened_photo_alignment_visual_pending',reviewSha256=sha(disk(target,'umap')))
  return report
 except Exception as exc:report.update(status='failed_partial_photo_review_preserved',error=repr(exc));raise
 finally:
  report['protectedAfter']={str(f):sha(f) for f in protected};report['protectedUnchanged']=report['protectedAfter']==before
  if not report['protectedUnchanged']:report['status']='failed_protected_hash_guard'
  receipt.write_text(json.dumps(report,indent=2)+'\n');assert report['protectedUnchanged']

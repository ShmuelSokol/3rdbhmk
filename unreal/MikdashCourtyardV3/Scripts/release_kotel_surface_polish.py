"""Explicit isolated Kotel surface pilot. run(apply=False) is native read-only.
run(apply=True) duplicates the saved main map and creates six unique materials;
never edits source meshes/materials or main map. Root launches native execution.
World-cm continuous procedural limestone color/roughness and filtered grain normal;
artistic amplitude/scale, not measured geology. No mortar texture, WPO or PDO.
"""
from pathlib import Path
import json,hashlib,shutil
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
MAIN='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
DEST='/Game/MikdashV3/MaterialReview/KotelSurfacePolishV2'
OLD='/Game/MikdashV3/MaterialReview/KotelStoneV1'
# V1 diagonal wave bands rejected. V2: smooth 3D value noise with analytic
# gradient, no periodic sine stripes. Scales/amplitudes remain artistic.
NOISE = r"""
struct LimestoneNoise {
 float hash3(float3 p) {
  p=frac(p*.1031); p+=dot(p,p.yzx+33.33);
  return frac((p.x+p.y)*p.z);
 }
 float4 sample3(float3 p) {
  float3 i=floor(p), f=frac(p);
  float3 u=f*f*f*(f*(f*6.0-15.0)+10.0);
  float3 du=30.0*f*f*(f*(f-2.0)+1.0);
  float a=hash3(i),b=hash3(i+float3(1,0,0));
  float c=hash3(i+float3(0,1,0)),d=hash3(i+float3(1,1,0));
  float e=hash3(i+float3(0,0,1)),g=hash3(i+float3(1,0,1));
  float h=hash3(i+float3(0,1,1)),j=hash3(i+float3(1,1,1));
  float z0=lerp(lerp(a,b,u.x),lerp(c,d,u.x),u.y);
  float z1=lerp(lerp(e,g,u.x),lerp(h,j,u.x),u.y);
  float dx=lerp(lerp(b-a,d-c,u.y),lerp(g-e,j-h,u.y),u.z)*du.x;
  float dy=lerp(lerp(c-a,d-b,u.x),lerp(h-e,j-g,u.x),u.z)*du.y;
  float dz=(z1-z0)*du.z;
  return float4(lerp(z0,z1,u.z),dx,dy,dz);
 }
};
LimestoneNoise noise;
float3 n=normalize(N);
// Shift origin for GPU precision; world cm remain shared across existing blocks.
float3 p=P-float3(-14500,13000,0);
"""
SURFACE=NOISE+r"""
float broad=noise.sample3(p/38.0).x*.57+noise.sample3(p/17.0+13.7).x*.29+noise.sample3(p/7.3-8.1).x*.14;
float medium=noise.sample3(p/2.1+31.3).x;
float3 q=p/.22;
float footprint=max(length(ddx(q)),length(ddy(q)));
float fade=1.0-smoothstep(.3,1.2,footprint);
float grain=(noise.sample3(q).x-.5)*fade;
float shade=1.0+(broad-.5)*.15+(medium-.5)*.035+grain*.012;
return float4(saturate(Base.rgb*shade),clamp(.84+(medium-.5)*.08+grain*.025,.78,.90));
"""
NORMAL=NOISE+r"""
float3 q=p/.22;
float footprint=max(length(ddx(q)),length(ddy(q)));
float fade=1.0-smoothstep(.3,1.2,footprint);
float3 grad=noise.sample3(q).yzw;
grad-=n*dot(grad,n);
return normalize(n-grad*(.055*fade));
"""

def file(p,ext='uasset'):return ROOT/'Content'/(p[6:]+'.'+ext)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(apply=False):
 import unreal as u
 assert Path(u.Paths.project_dir()).resolve()==ROOT
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);lib=u.EditorAssetLibrary
 assert not editor.get_game_world()
 assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
 assert editor.get_editor_world().get_outermost().get_name()==MAIN,'Explicitly load saved main in dedicated editor'
 manifest=json.loads((ROOT/'SourceAssets/kotel-detail/KotelStoneV1/manifest.json').read_text())
 meshes={OLD+'/Meshes/'+r['name']:i for i,r in enumerate(manifest['meshes'])};assert len(meshes)==6
 def path(o):return o.get_path_name().split('.')[0] if o else None
 def pose(a):
  p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d();return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
 def inventory():return sorted((a.get_name(),a.get_actor_label(),a.get_class().get_path_name(),pose(a)) for a in actors.get_all_level_actors())
 def overlays():
  result=[]
  for a in actors.get_all_level_actors():
   c=a.get_component_by_class(u.StaticMeshComponent);m=c.get_editor_property('static_mesh') if c else None
   if path(m) in meshes:
    assert a.get_actor_label().startswith('RELEASE_Kotel')
    assert c.get_num_materials()>0,'Overlay has no material slots'
    assert str(c.get_collision_profile_name())=='NoCollision'
    assert max(abs(v) for v in pose(a)[:6])<.001 and max(abs(v-1) for v in pose(a)[6:])<.001
    result.append((a,c,m,meshes[path(m)]))
  assert len(result)==6 and len({i for a,c,m,i in result})==6
  return result
 selected=overlays();baseline=inventory()
 protected=[file(MAIN,'umap'),file('/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N002_P001')]
 protected+=list((ROOT/'Content'/OLD[6:]).rglob('*.uasset'))
 protected+= [file('/Game/MikdashV3/Maps/Courtyard','umap'),file('/Game/MikdashV3/FutureMountV1/L_FutureMount','umap')]
 before={str(p):sha(p) for p in protected}
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 folder=ROOT/'SourceAssets/kotel-detail';receipt=folder/('surface-polish-v2-'+stamp+'.json')
 report=dict(status='dry_run_no_mutation',apply=apply,protectedBefore=before,
   selected=[dict(label=a.get_actor_label(),mesh=path(m),pose=pose(a),slots=[path(c.get_material(j)) for j in range(c.get_num_materials())]) for a,c,m,i in selected],
   authoredDetail=dict(version=2,rejectedPrior='V1 visible diagonal sine bands',broadCellCm=[38,17,7.3],mediumCellCm=2.1,grainCellCm=.22,broadAmplitude=.075,normalSlope=.055,roughnessRange=[.78,.90],units='cm; artistic 3D quintic value noise, not measured geology'),created=[])
 try:
  if not apply:return report
  assert not lib.does_directory_exist(DEST),'Preserve existing/partial pilot'
  checkpoint=ROOT.parent/'ReviewCheckpoints'/('KotelSurfaceV2-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
  for p in protected:
   dest=checkpoint/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
   assert sha(dest)==before[str(p)],'Checkpoint copy hash mismatch'
  report['checkpoint']=str(checkpoint)
  target=DEST+'/Maps/Walkthrough'
  assert lib.duplicate_asset(MAIN,target)
  assert levels.load_level(target) and editor.get_editor_world().get_outermost().get_name()==target
  assert inventory()==baseline
  selected=overlays();edit=u.MaterialEditingLibrary
  def node(mat,cls,**props):
   n=edit.create_material_expression(mat,cls)
   assert n
   for k,v in props.items():n.set_editor_property(k,v)
   return n
  def custom(mat,code,kind,inputs):
   slots=[]
   for name in inputs:
    slot=u.CustomInput();slot.set_editor_property('input_name',name);slots.append(slot)
   n=node(mat,u.MaterialExpressionCustom,code=code,inputs=slots,output_type=kind)
   for name,source in inputs.items():assert edit.connect_material_expressions(source,'',n,name)
   return n
  materials={}
  for i in range(6):
   mat=u.AssetToolsHelpers.get_asset_tools().create_asset('M_KotelSurface_'+str(i),DEST+'/Materials',u.Material,u.MaterialFactoryNew());assert mat
   mat.set_editor_property('tangent_space_normal',False)
   factor=(.93,.965,1,1.025,.95,.985)[i]
   inputs={'P':node(mat,u.MaterialExpressionWorldPosition),'N':node(mat,u.MaterialExpressionVertexNormalWS),'Base':node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.61*factor,.575*factor,.505*factor,1))}
   surface=custom(mat,SURFACE,u.CustomMaterialOutputType.CMOT_FLOAT4,inputs)
   normal=custom(mat,NORMAL,u.CustomMaterialOutputType.CMOT_FLOAT3,{k:inputs[k] for k in ('P','N')})
   rgb=node(mat,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
   rough=node(mat,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
   for mask in (rgb,rough):assert edit.connect_material_expressions(surface,'',mask,'')
   for src,prop in [(rgb,u.MaterialProperty.MP_BASE_COLOR),(rough,u.MaterialProperty.MP_ROUGHNESS),(normal,u.MaterialProperty.MP_NORMAL)]:assert edit.connect_material_property(src,'',prop)
   assert edit.get_material_property_input_node(mat,u.MaterialProperty.MP_WORLD_POSITION_OFFSET) is None
   edit.recompile_material(mat);assert lib.save_loaded_asset(mat,only_if_is_dirty=False)
   materials[i]=mat;report['created'].append(path(mat))
  for a,c,m,i in selected:
   for j in range(c.get_num_materials()):c.set_material(j,materials[i])
  assert inventory()==baseline
  assert levels.save_current_level()
  report['status']='review_saved_reopen_pending';receipt.write_text(json.dumps(report,indent=2))
  assert levels.load_level(target) and editor.get_editor_world().get_outermost().get_name()==target
  assert inventory()==baseline
  for a,c,m,i in overlays():assert all(path(c.get_material(j))==DEST+'/Materials/M_KotelSurface_'+str(i) for j in range(c.get_num_materials()))
  report.update(status='saved_reopened_shader_visual_acceptance_pending',reviewMap=target,reviewSha256=sha(file(target,'umap')))
  return report
 except Exception as exc:
  report.update(status='failed_partial_review_preserved',error=repr(exc));raise
 finally:
  report['protectedAfter']={str(p):sha(p) for p in protected};report['protectedUnchanged']=report['protectedAfter']==before
  if not report['protectedUnchanged']:report['status']='failed_protected_hash_guard'
  receipt.write_text(json.dumps(report,indent=2)+'\n')
  assert report['protectedUnchanged']

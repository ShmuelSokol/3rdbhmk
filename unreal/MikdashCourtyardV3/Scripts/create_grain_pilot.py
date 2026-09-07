import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve();assert root==Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
a=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not e.get_game_world()
dest='/Game/MikdashV3/MaterialReview/GrainPilotV1';assert not a.does_directory_exist(dest),'Existing pilot namespace; inspect rather than overwrite'
folder=root/'SourceAssets/material-review/GrainPilotV1';r={'status':'started','assigned':False,'visualAcceptance':'PENDING','shaderCompileAcceptance':'PENDING','created':[]}
try:
 t=unreal.AssetImportTask();t.filename=str(folder/'limestone-grain-v1.png');t.destination_path=dest;t.destination_name='T_LimestoneGrain_V1';t.automated=True;t.replace_existing=False;t.save=False
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);objs=list(t.get_objects());assert len(objs)==1 and isinstance(objs[0],unreal.Texture2D)
 tex=objs[0];r['created'].append(tex.get_path_name())
 tex.set_editor_property('srgb',False);tex.set_editor_property('address_x',unreal.TextureAddress.TA_MIRROR);tex.set_editor_property('address_y',unreal.TextureAddress.TA_MIRROR)
 tex.set_editor_property('power_of_two_mode',unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO);tex.set_editor_property('max_texture_size',2048)
 assert a.save_loaded_asset(tex,only_if_is_dirty=False)
 src='/Game/MikdashV3/MaterialReview/FinishPilot/M_StonePilot_Paving_Pilot01_innerPaving'
 mat=a.duplicate_asset(src,dest+'/M_InnerPaving_GrainReviewV1');assert isinstance(mat,unreal.Material);r['created'].append(mat.get_path_name())
 edit=unreal.MaterialEditingLibrary;prop=unreal.MaterialProperty.MP_BASE_COLOR
 base=edit.get_material_property_input_node(mat,prop);pin=edit.get_material_property_input_node_output_name(mat,prop);assert base
 def node(cls,x,y,**kw):
  n=edit.create_material_expression(mat,cls,x,y);assert n
  for k,v in kw.items():n.set_editor_property(k,v)
  return n
 def wire(n,p,q,out=''):
  if not edit.connect_material_expressions(n,out,p,q):raise RuntimeError('Connection '+str(n.get_class().get_name())+' output '+repr(out)+' -> '+str(p.get_class().get_name())+' input '+repr(q)+' failed; inputs='+str(edit.get_material_expression_input_names(p))+' outputs='+str(edit.get_material_expression_output_names(n)))
 pos=node(unreal.MaterialExpressionWorldPosition,-800,-500)
 xy=node(unreal.MaterialExpressionComponentMask,-600,-500,r=True,g=True,b=False,a=False);wire(pos,xy,'')
 scale=node(unreal.MaterialExpressionMultiply,-400,-500,const_b=.025);wire(xy,scale,'A')
 sample=node(unreal.MaterialExpressionTextureSample,-200,-500,texture=tex,sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(scale,sample,edit.get_material_expression_input_names(sample)[0])
 normal=node(unreal.MaterialExpressionPixelNormalWS,-200,-800)
 inputs=[]
 for name in ['C','G','N']:
  ci=unreal.CustomInput();ci.set_editor_property('input_name',name);inputs.append(ci)
 mean=json.loads((folder/'texture-provenance.json').read_text())['redMeanNormalized']
 blend=node(unreal.MaterialExpressionCustom,600,-300,inputs=inputs,output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3,description='Subtle generated grain, upward paving faces only; artistic texture',code='float mask=pow(saturate(N.z),64.0); return C*(1.0+(G-'+repr(mean)+')*0.14*mask);')
 wire(base,blend,'C',pin);wire(sample,blend,'G','R');wire(normal,blend,'N')
 assert edit.connect_material_property(blend,'',prop)
 edit.recompile_material(mat);assert a.save_loaded_asset(mat,only_if_is_dirty=False)
 r.update(status='texture_and_unassigned_material_saved',sourceMaterial=src,textureTileCm=40,meanRed=mean,grainStrength=.14,addressing='Mirror',textureBuild='StretchToPowerOfTwo max2048',limits='Unassigned review material. Native compiler/visual/motion checks pending. No normal, roughness, geometry, collision or source material changed.')
except Exception as ex:r.update(status='failed_partial_review_required',error=str(ex));raise
finally:(folder/'native-grain-pilot.json').write_text(json.dumps(r,indent=2))

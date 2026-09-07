import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve();assert root==Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
a=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);assert not e.get_game_world()
dest='/Game/MikdashV3/MaterialReview/GrainPilotV1';folder=root/'SourceAssets/material-review/GrainPilotV1'
r=json.loads((folder/'native-grain-pilot.json').read_text());assert r['status']=='failed_partial_review_required' and len(r['created'])==1
assert not a.does_asset_exist(dest+'/M_InnerPaving_GrainReviewV1')
tex=a.load_asset(dest+'/T_LimestoneGrain_V1');assert isinstance(tex,unreal.Texture2D)
assert not tex.get_editor_property('srgb') and tex.get_editor_property('address_x')==unreal.TextureAddress.TA_MIRROR
r['recoveredFrom']='Source/destination duplicate argument reversal; original unchanged'
r.pop('error',None)
try:
 src='/Game/MikdashV3/MaterialReview/FinishPilot/M_StonePilot_Paving_Pilot01_innerPaving'
 mat=a.duplicate_asset(src,dest+'/M_InnerPaving_GrainReviewV1');assert isinstance(mat,unreal.Material);r['created'].append(mat.get_path_name())
 edit=unreal.MaterialEditingLibrary;prop=unreal.MaterialProperty.MP_BASE_COLOR
 base=edit.get_material_property_input_node(mat,prop);pin=edit.get_material_property_input_node_output_name(mat,prop);assert base
 def node(cls,x,y,**kw):
  n=edit.create_material_expression(mat,cls,x,y);assert n
  for k,v in kw.items():n.set_editor_property(k,v)
  return n
 def wire(n,p,q,out=''):assert edit.connect_material_expressions(n,out,p,q)
 pos=node(unreal.MaterialExpressionWorldPosition,-800,-500)
 xy=node(unreal.MaterialExpressionComponentMask,-600,-500,r=True,g=True,b=False,a=False);wire(pos,xy,'Input')
 scale=node(unreal.MaterialExpressionMultiply,-400,-500,const_b=.025);wire(xy,scale,'A')
 sample=node(unreal.MaterialExpressionTextureSample,-200,-500,texture=tex,sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);wire(scale,sample,'UVs')
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

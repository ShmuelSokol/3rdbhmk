import unreal,json,shutil,hashlib
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve();assert root==Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
for name in ['duchan-step55-trial.json','east-gate-step55-trial.json','east-jamb-step55-trial.json']:
 r=json.loads((root/'SourceAssets/runtime-review'/name).read_text());assert not r['errors'] and r['stopRequested'] and r['reached']
path='/Game/MikdashV3/Gameplay/BP_MikdashWalker'
bp=unreal.load_asset(path);cdo=unreal.get_default_object(unreal.load_class(None,path+'.BP_MikdashWalker_C'))
cm=cdo.get_component_by_class(unreal.CharacterMovementComponent);assert cm.get_editor_property('max_step_height')==45.0
asset=root/'Content/MikdashV3/Gameplay/BP_MikdashWalker.uasset';checkpoint=root.parent/'Checkpoints/Before-Step55';checkpoint.mkdir(exist_ok=False);shutil.copy2(asset,checkpoint/asset.name)
oldhash=hashlib.sha256(asset.read_bytes()).hexdigest()
cm.modify();cm.set_editor_property('max_step_height',55.0)
assert unreal.BlueprintEditorLibrary.compile_blueprint(bp),'Blueprint compile failed'
assert unreal.get_editor_subsystem(unreal.EditorAssetSubsystem).save_loaded_asset(bp),'Save failed'
cdo=unreal.get_default_object(unreal.load_class(None,path+'.BP_MikdashWalker_C'))
assert cdo.get_component_by_class(unreal.CharacterMovementComponent).get_editor_property('max_step_height')==55.0
r={'status':'blueprint_compiled_saved_cdo_readback_passed','maxStepHeightCm':55,'previous':45,'checkpoint':str(checkpoint),'previousSha256':oldhash,'savedSha256':hashlib.sha256(asset.read_bytes()).hexdigest(),'remaining':'Fresh PIE spawn readback and Duchan up/back without test override; packaged verification pending','geometryChanged':False}
(root/'SourceAssets/runtime-review/step55-saved.json').write_text(json.dumps(r,indent=2));unreal.log('STEP55_BLUEPRINT_SAVED')

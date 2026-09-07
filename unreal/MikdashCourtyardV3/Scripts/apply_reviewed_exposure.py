"""Apply reviewed +1 exposure bias, preserve checkpoint, save/reopen/read back."""
import unreal,json,hashlib,shutil
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert root==Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not e.get_game_world()
assert e.get_editor_world().get_path_name().split('.')[0]=='/Game/MikdashV3/Maps/Courtyard'
for name in ['exposure-comparison.json','exterior-exposure-comparison.json']:
 r=json.loads((root/'SourceAssets/visual-review'/name).read_text())
 assert r['status']=='restored' and r['biasRestored']
g=json.loads((root/'SourceAssets/material-review/GrainPilotV1/bounded-comparison.json').read_text())
assert g['overridesRestored']
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
assert len(actors)==7281,len(actors)
volumes=[a for a in actors if isinstance(a,unreal.PostProcessVolume)];assert len(volumes)==1
v=volumes[0];p=v.get_editor_property('settings');assert p.get_editor_property('auto_exposure_bias')==0
for a in actors:
 for c in a.get_components_by_class(unreal.StaticMeshComponent):
  for i in range(c.get_num_materials()):
   mat=c.get_material(i)
   assert not mat or '/GrainPilotV1/' not in mat.get_path_name(),'Unaccepted grain remains assigned'
mapfile=root/'Content/MikdashV3/Maps/Courtyard.umap'
checkpoint=root.parent/'Checkpoints/Before-Exposure-Plus-One'
checkpoint.mkdir(exist_ok=False)
shutil.copy2(mapfile,checkpoint/'Courtyard.umap')
oldhash=hashlib.sha256(mapfile.read_bytes()).hexdigest()
p.set_editor_property('auto_exposure_bias',1.0);v.set_editor_property('settings',p)
v.set_actor_label('V3 daylight exposure - physical EV13 with +1 stop compensation')
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.save_current_level(),'Save failed'
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
assert level.load_level('/Game/MikdashV3/Maps/Courtyard'),'Reload failed'
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
volumes=[a for a in actors if isinstance(a,unreal.PostProcessVolume)];assert len(volumes)==1
p=volumes[0].get_editor_property('settings')
assert p.get_editor_property('auto_exposure_bias')==1.0
assert len(actors)==7281
report={'status':'saved_and_reopened','bias':1.0,'actorCount':len(actors),'previousMapSha256':oldhash,'savedMapSha256':hashlib.sha256(mapfile.read_bytes()).hexdigest(),'checkpoint':str(checkpoint),'visualBasis':['exposure-baseline.jpg','exposure-plus-one.jpg','exterior-exposure-baseline.jpg','exterior-exposure-plus-one.jpg'],'limits':'Two native editor still comparisons. Motion, deeper interiors, packaged runtime and final realism acceptance pending. Geometry and source tint unchanged; grain remains unassigned.'}
(root/'SourceAssets/visual-review/exposure-saved-readback.json').write_text(json.dumps(report,indent=2))
unreal.log('EXPOSURE_PLUS_ONE_SAVED_REOPENED')

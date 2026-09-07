import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve();assert root==Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);a=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
assert not e.get_game_world()
dest='/Game/MikdashV3/Runtime/Audio/SoftFootstepsV1'
assert not a.does_directory_exist(dest),'Existing destination: review instead of duplicate import'
files=sorted((root/'SourceAssets/audio-review/Fantozzi/Wav').glob('*Sand*.wav'));assert len(files)==6
r={'status':'started','source':'Fantozzi / qubodup CC0; same archive as stone samples','surfaceUse':'Illustrative soft-ground footsteps; not a surveyed terrain material classification','audition':'PENDING','runtimePlayback':'PENDING','assets':[]}
out=root/'SourceAssets/audio-review/soft-native-import.json'
try:
 for f in files:
  t=unreal.AssetImportTask();t.filename=str(f);t.destination_path=dest;t.destination_name='SW_'+f.stem.replace('-','_');t.automated=True;t.replace_existing=False;t.save=False
  unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);objects=list(t.get_objects());assert len(objects)==1 and isinstance(objects[0],unreal.SoundWave)
  s=objects[0];s.set_editor_property('looping',False);s.set_editor_property('volume',.18)
  assert 0<float(s.get_editor_property('duration'))<1
  assert a.save_loaded_asset(s,only_if_is_dirty=False)
  r['assets'].append({'path':s.get_path_name(),'duration':float(s.get_editor_property('duration'))})
 r['status']='six_soft_footsteps_saved_native_properties_checked'
except Exception as ex:r.update(status='failed_partial_review_required',error=str(ex));raise
finally:out.write_text(json.dumps(r,indent=2))

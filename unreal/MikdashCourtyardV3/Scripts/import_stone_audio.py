import unreal,json
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert root==Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);l=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem);a=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
assert not e.get_game_world() and not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
assert e.get_editor_world().get_path_name().split('.')[0]=='/Game/MikdashV3/Maps/Courtyard'
dest='/Game/MikdashV3/Runtime/Audio/StoneFootstepsV1'
assert not a.does_directory_exist(dest),'Existing namespace; review instead of duplicate import'
files=sorted((root/'SourceAssets/audio-review/Fantozzi/Wav').glob('*.wav'));assert len(files)==6
out=root/'SourceAssets/audio-review/stone-native-import.json'
r={'status':'started','source':'Fantozzi / qubodup, CC0','audition':'PENDING','movementSynchronization':'PENDING','assets':[]}
out.write_text(json.dumps(r))
try:
 for f in files:
  t=unreal.AssetImportTask();t.filename=str(f);t.destination_path=dest;t.destination_name='SW_'+f.stem.replace('-','_');t.automated=True;t.replace_existing=False;t.save=False
  unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);objects=list(t.get_objects());assert len(objects)==1 and isinstance(objects[0],unreal.SoundWave)
  sound=objects[0];sound.set_editor_property('looping',False);sound.set_editor_property('volume',0.18)
  assert 0.25<float(sound.get_editor_property('duration'))<0.5
  assert a.save_loaded_asset(sound,only_if_is_dirty=False)
  r['assets'].append(sound.get_path_name())
 ambient=[x for x in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if isinstance(x,unreal.AmbientSound)]
 matches=[]
 for actor in ambient:
  c=actor.get_component_by_class(unreal.AudioComponent);s=c.get_editor_property('sound')
  if s and s.get_path_name().split('.')[0]=='/Game/MikdashV3/Runtime/Audio/SW_CourtyardOriginal_Pilot01':matches.append((actor,c))
 assert len(matches)==1
 actor,c=matches[0];r['previousAutoActivate']=bool(c.get_editor_property('auto_activate'));c.set_editor_property('auto_activate',False)
 assert not c.get_editor_property('auto_activate')
 r['retiredLoopActor']=actor.get_path_name();assert l.save_current_level()
 del actor,c,ambient,matches,s,sound,objects
 assert l.load_level('/Game/MikdashV3/Maps/Courtyard')
 for p in r['assets']:
  sound=a.load_asset(p);assert isinstance(sound,unreal.SoundWave) and not sound.get_editor_property('looping')
  assert abs(float(sound.get_editor_property('volume'))-.18)<1e-5
 matches=[]
 for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
  if isinstance(actor,unreal.AmbientSound):
   c=actor.get_component_by_class(unreal.AudioComponent);s=c.get_editor_property('sound')
   if s and s.get_path_name().split('.')[0]=='/Game/MikdashV3/Runtime/Audio/SW_CourtyardOriginal_Pilot01':matches.append(bool(c.get_editor_property('auto_activate')))
 assert matches==[False]
 r.update(status='saved_reopened_six_samples_and_retired_loop_autoplay',oldLoopPreserved=True)
except Exception as ex:r.update(status='failed_partial_review_required',error=str(ex));raise
finally:out.write_text(json.dumps(r,indent=2))

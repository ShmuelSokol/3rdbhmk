"""Create user-selected future Mount scenario from saved working map.

Explicit build() only, with editor idle. This stage removes exactly two audited
context actors in the duplicate; platform/stairs are subsequent implementation.
"""
import unreal as ue, json, hashlib
from pathlib import Path
ROOT=Path(ue.Paths.project_dir()).resolve()
SOURCE='/Game/MikdashV3/Maps/Courtyard'
DEST='/Game/MikdashV3/FutureMountV1/L_FutureMount'
REMOVALS={
 '/Game/MikdashV3/JerusalemContext/Streets/SM_Jerusalem_Landmark_09_Whole',
 '/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Large_07279'}
PROTECTED='/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N002_P001'
def mesh_path(actor):
 comp=actor.get_component_by_class(ue.StaticMeshComponent)
 mesh=comp.get_editor_property('static_mesh') if comp else None
 return mesh.get_path_name().split('.')[0] if mesh else None
def build():
 assert not ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world(), 'Do not run during play'
 assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Resolve unsaved map work first'
 assert not ue.EditorAssetLibrary.does_asset_exist(DEST), 'Existing scenario preserved'
 audit=json.loads((ROOT/'SourceAssets/visual-review/mount-platform-scenario-audit.json').read_text())
 assert {r['asset'] for r in audit['scenario_hide_candidates']}==REMOVALS
 source_file=ROOT/'Content/MikdashV3/Maps/Courtyard.umap'
 before=hashlib.sha256(source_file.read_bytes()).hexdigest()
 levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
 actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
 assert levels.load_level(SOURCE)
 original=list(actors.get_all_level_actors())
 protected=[(a.get_actor_label(),str(a.get_actor_transform())) for a in original if mesh_path(a)==PROTECTED]
 assert protected, 'Western Wall shared mesh absent'
 matches=[a for a in original if mesh_path(a) in REMOVALS]
 assert len(matches)==2 and {mesh_path(a) for a in matches}==REMOVALS
 world=ue.EditorLoadingAndSavingUtils.new_map_from_template(SOURCE,False)
 assert world and world.get_outermost().get_name()!=SOURCE
 copied=list(actors.get_all_level_actors());assert len(copied)==len(original)
 removed=[]
 for actor in copied:
  if mesh_path(actor) in REMOVALS:
   removed.append({'label':actor.get_actor_label(),'mesh':mesh_path(actor)})
   assert actors.destroy_actor(actor)
 assert len(removed)==2
 assert ue.EditorLoadingAndSavingUtils.save_map(world,DEST)
 assert levels.load_level(DEST)
 reopened=list(actors.get_all_level_actors())
 assert len(reopened)==len(original)-2
 assert not any(mesh_path(a) in REMOVALS for a in reopened)
 assert [(a.get_actor_label(),str(a.get_actor_transform())) for a in reopened if mesh_path(a)==PROTECTED]==protected
 assert hashlib.sha256(source_file.read_bytes()).hexdigest()==before
 report={'status':'scenario_saved_reopened_platform_not_yet_built','map':DEST,'removedActors':removed,'sourceMapUnchanged':True,'sourceSha256':before,'protectedWesternWallSharedMeshUnchanged':True,'limitations':['Platform, stairs, plaza surface and visual acceptance remain pending','User-selected future scenario; not a prediction of future architecture']}
 (ROOT/'SourceAssets/visual-review/future-mount-scenario-execution.json').write_text(json.dumps(report,indent=2)+'\n')
 return report

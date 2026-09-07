import unreal,json,sys
from pathlib import Path
r={'dirtyMaps':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],'dirtyContent':[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],'playWorldPresent':bool(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()),'stages':{}}
for mod,attr in [('mikdash_terrain_stage','STAGE'),('mikdash_buildings_stage','_BUILDINGS_STAGE'),('mikdash_streets_stage','STAGE'),('mikdash_instances_stage','_INST_STAGE')]:
 m=sys.modules.get(mod);r['stages'][mod]=str(getattr(m,attr,None))[:250] if m else 'not_loaded'
Path(unreal.Paths.project_dir(),'SourceAssets/pre-cook-editor-state.json').write_text(json.dumps(r,indent=2));unreal.log('PRE_COOK_EDITOR_STATE_RECORDED')

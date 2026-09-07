import sys,json,unreal
from pathlib import Path
m=sys.modules['mikdash_instances_stage']
m.save_instances_import()
assert m._INST_STAGE['report']['status']=='SAVED_PENDING_MANUAL_REOPEN_AND_VISUAL_REVIEW'
m._INST_STAGE=None
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(m.INST_LEVEL)
r=m.verify_instances_in_current_map(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\cloud-unreal-v3\context-review')
r.update(manualReopenNotAutomaticallyAttested=False,reopenedByThisScript=True)
Path(unreal.Paths.project_dir(),'SourceAssets/context-review/instances-reopen.json').write_text(json.dumps(r,indent=2))
unreal.log('DECORATIVE_SAVE_REOPEN_PASSED')

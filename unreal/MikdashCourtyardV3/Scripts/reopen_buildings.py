import json, sys
from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir()).resolve()
if root != Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3'): raise RuntimeError('Wrong project')
module=sys.modules.get('mikdash_buildings_stage')
if module is None or module._BUILDINGS_STAGE is None: raise RuntimeError('Missing expected building stage')
stage=module._BUILDINGS_STAGE
if stage['report']['status']!='saved_requires_native_visual_collision_and_cook_review': raise RuntimeError('Buildings must be saved first')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(): raise RuntimeError('Unexpected dirty map')
module._BUILDINGS_STAGE=None
del stage
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/MikdashV3/Maps/Courtyard'): raise RuntimeError('Reopen failed')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
owned=[a for a in actors if 'MikdashJerusalemBuildingsV1' in [str(t) for t in a.get_editor_property('tags')]]
manifest=json.loads(Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\cloud-unreal-v3\context-review\buildings-manifest.json').read_text())
records={r['assetName']:r for r in manifest['meshes']}
meshes=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
checks=[]
for a in owned:
 c=a.get_component_by_class(unreal.StaticMeshComponent)
 m=c.get_editor_property('static_mesh')
 if m is None or m.get_name() not in records: raise RuntimeError('Unknown building after reopen')
 check=module._buildings_check_mesh(m,records[m.get_name()],meshes)
 if str(c.get_collision_profile_name())!='BlockAll': raise RuntimeError('Building collision profile changed')
 check['actor']=a.get_path_name()
 checks.append(check)
report={'status':'reopened_geometry_checks_passed_visual_collision_and_cook_pending','actorCount':len(actors),'buildingActors':len(owned),'uniqueBuildingMeshes':len({c['asset'] for c in checks}),'meshChecks':checks}
if len(owned)!=1499 or report['uniqueBuildingMeshes']!=1499: raise RuntimeError('Building coverage differs after reopen')
(root/'SourceAssets/context-review/buildings-reopen.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log(report['status'])

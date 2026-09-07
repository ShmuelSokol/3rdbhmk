import sys,json
from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir()).resolve()
if root!=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3'):raise RuntimeError('Wrong project')
module=sys.modules.get('mikdash_streets_stage')
if module is None or module.STAGE is None:raise RuntimeError('Missing street stage')
if module.STAGE['report']['status']!='saved_requires_reload_native_visual_collision_and_cook_review':raise RuntimeError('Street save not completed')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Unexpected map edits')
data=module.STAGE['data']
module.STAGE=None
if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/MikdashV3/Maps/Courtyard'):raise RuntimeError('Map reload failed')
records={r['assetName']:r for r in data['effective_records']}
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
found={}
checks=[]
for actor in actors:
 for c in actor.get_components_by_class(unreal.StaticMeshComponent):
  mesh=c.get_editor_property('static_mesh')
  if not mesh or not mesh.get_path_name().startswith(module.DEST+'/'):continue
  name=mesh.get_name()
  if name not in records:raise RuntimeError('Held or unexpected street actor: '+name)
  if name in found:raise RuntimeError('Duplicate street actor: '+name)
  found[name]=actor.get_path_name()
  module._identity(actor)
  check=module._mesh_check(mesh,records[name])
  material_name=records[name]['materialSlots'][0]['fbxMaterialName']
  if mesh.get_material(0).get_path_name().split('.')[0]!=module.MATERIAL_DEST+'/'+material_name:raise RuntimeError('Street material differs')
  if str(c.get_collision_profile_name())!='BlockAll' or not c.is_query_collision_enabled():raise RuntimeError('Street collision disabled')
  if mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')!=unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:raise RuntimeError('Street collision policy changed')
  checks.append(check)
if set(found)!=set(records):raise RuntimeError('Street coverage mismatch')
report={'status':'reopened_street_geometry_and_coverage_passed_runtime_visual_pending','totalActors':len(actors),'streetActors':len(found),'triangles':sum(r['triangles'] for r in records.values()),'heldOriginalActors':0,'meshChecks':checks}
(root/'SourceAssets/context-review/streets-reopen.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log(report['status'])

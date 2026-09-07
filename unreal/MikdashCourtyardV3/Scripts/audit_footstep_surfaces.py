"""Read-only scene audit of production footstep asset-prefix coverage."""
import unreal,json,re,collections
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve()
assert root==Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
code=(root/'Plugins/MikdashRuntime/Source/MikdashRuntime/Private/MikdashPlayerController.cpp').read_text(encoding='utf-8-sig')
section=code.split('const bool SoftGround =',1)[1].split('// Unknown/new floor',1)[0]
prefixes=re.findall(r'StartsWith\(TEXT\("([^"]+)"\)\)',section)
assert len(prefixes)==4
counts=collections.Counter();unknown=[];examples={}
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
 for c in a.get_components_by_class(unreal.StaticMeshComponent):
  mesh=c.get_editor_property('static_mesh')
  if not mesh or not c.is_query_collision_enabled():continue
  path=mesh.get_path_name();matched=next((p for p in prefixes if path.startswith(p)),None)
  family=('soft' if matched==prefixes[0] else 'hard') if matched else 'unassigned'
  counts[family]+=1
  if matched:examples.setdefault(matched,path)
  else:unknown.append({'actor':a.get_actor_label(),'mesh':path,'collision':str(c.get_collision_profile_name())})
r={'status':'native_scene_prefix_audit_completed','prefixesReadFromProductionCode':prefixes,'queryCollisionComponentsByFamily':dict(counts),'examples':examples,'unassigned':unknown,'limits':'Asset-family coverage only. Does not prove actual floor hits, physical surface material, audio playback, audibility or compiled controller behavior.'}
(root/'SourceAssets/audio-review/native-surface-prefix-audit.json').write_text(json.dumps(r,indent=2))
unreal.log('FOOTSTEP_NATIVE_SURFACE_AUDIT_COMPLETED')

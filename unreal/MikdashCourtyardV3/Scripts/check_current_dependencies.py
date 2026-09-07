"""Current native registry dependency evidence. Not cook or runtime acceptance."""
import unreal,json,time,hashlib
from pathlib import Path
root=Path(unreal.Paths.project_dir()).resolve();assert root==Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
e=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);assert not e.get_game_world()
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
registry=unreal.AssetRegistryHelpers.get_asset_registry();assert not registry.is_loading_assets()
options=unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
start=time.monotonic();seen=set();queue=['/Game/MikdashV3/Maps/Courtyard'];missing=[];external=set();edges=0
while queue:
 if len(seen)>20000 or time.monotonic()-start>60:raise RuntimeError('Bounded dependency scan exceeded; no readiness claim')
 package=queue.pop()
 if package in seen:continue
 seen.add(package)
 if not registry.get_assets_by_package_name(package):missing.append(package)
 for dep in registry.get_dependencies(package,options) or []:
  name=str(dep);edges+=1
  if name.startswith('/Game/') and name not in seen:queue.append(name)
  elif not name.startswith('/Game/'):external.add(name)
expected=[]
for family,prefix in [('StoneFootstepsV1','Stone'),('SoftFootstepsV1','Sand')]:
 for side in ['L','R']:
  for i in range(1,4):
   name='/Game/MikdashV3/Runtime/Audio/'+family+'/SW_Fantozzi_'+prefix+side+str(i)
   expected.append({'package':name,'registryPresent':bool(registry.get_assets_by_package_name(name)),'reachableFromMap':name in seen})
mapfile=root/'Content/MikdashV3/Maps/Courtyard.umap'
r={'status':'project_dependency_scan_passed' if not missing and all(x['registryPresent'] for x in expected) else 'missing_dependencies','engine':unreal.SystemLibrary.get_engine_version(),'mapSha256':hashlib.sha256(mapfile.read_bytes()).hexdigest(),'projectPackagesVisited':len(seen),'edgesRead':edges,'missingProjectPackages':missing,'externalPackageCountNotRecursed':len(external),'futureRuntimeAudio':expected,'elapsedSeconds':time.monotonic()-start,'limits':'Native registry saved-map project dependencies only. External engine/plugin graph not recursively validated. No cook, plugin compilation, startup, packaging or distribution acceptance. Audio currently unused by saved map needs enabled runtime plugin hard references at cook.'}
(root/'SourceAssets/current-native-dependency-preflight.json').write_text(json.dumps(r,indent=2))
unreal.log('CURRENT_DEPENDENCY_PREFLIGHT '+r['status'])

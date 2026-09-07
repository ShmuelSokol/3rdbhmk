"""Read-only current-map architecture reconciliation against preserved manifest."""
import json, math, hashlib
from pathlib import Path
import unreal
root=Path(unreal.Paths.project_dir()).resolve()
if root != Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3'): raise RuntimeError('Wrong project')
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_editor_world()
if editor.get_game_world() or world.get_path_name().split('.')[0]!='/Game/MikdashV3/Maps/Courtyard': raise RuntimeError('Need saved editor Courtyard')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(): raise RuntimeError('Save/reopen map before reconciliation')
manifest_path=root/'SourceAssets/architecture-manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
records={r['assetName']:r for r in manifest['meshes']}
if len(records)!=2633: raise RuntimeError('Unexpected architecture manifest')
report={'scope':'Native editor mesh identity, triangle, bounds and placement reconciliation; not source interpretation, visuals, walking or cook acceptance','manifestSha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'expectedMeshes':2633,'checks':[],'errors':[]}
found={name:[] for name in records}
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
for actor in actors:
    for component in actor.get_components_by_class(unreal.StaticMeshComponent):
        mesh=component.get_editor_property('static_mesh')
        if not mesh or not mesh.get_path_name().startswith('/Game/MikdashV3/Architecture/'): continue
        name=mesh.get_name()
        if not name.startswith('architecture_') or name[len('architecture_'):] not in records:
            report['errors'].append('Unrecognized architecture asset: '+mesh.get_path_name());continue
        key=name[len('architecture_'):]
        found[key].append(component.get_path_name())
        record=records[key]
        bb=mesh.get_bounding_box()
        actual={'min':[bb.min.x,bb.min.y,bb.min.z],'max':[bb.max.x,bb.max.y,bb.max.z]}
        error=max(abs(actual[k][i]-record['expectedBoundsUnrealCm'][k][i]) for k in ('min','max') for i in range(3))
        transform=component.get_world_transform()
        loc=transform.translation
        rot=transform.rotation.rotator()
        scale=transform.scale3d
        placement=max(abs(v) for v in [loc.x,loc.y,loc.z,rot.pitch,rot.yaw,rot.roll,scale.x-1,scale.y-1,scale.z-1])
        triangles=int(mesh.get_num_triangles(0))
        failures=[]
        if not math.isfinite(error) or error>.5: failures.append('bounds')
        if triangles!=record['triangles']: failures.append('triangles')
        if not math.isfinite(placement) or placement>1e-4: failures.append('transform')
        report['checks'].append({'assetName':key,'component':component.get_path_name(),'triangles':triangles,'boundsErrorCm':error,'placementError':placement,'failures':failures})
        if failures:report['errors'].append(key+': '+','.join(failures))
report['missing']=[key for key,items in found.items() if not items]
report['duplicates']={key:items for key,items in found.items() if len(items)>1}
report['status']='geometry_inventory_passed_other_acceptance_pending' if not report['errors'] and not report['missing'] and not report['duplicates'] else 'failed'
(root/'SourceAssets/architecture-current-inventory.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('Architecture inventory: '+report['status'])

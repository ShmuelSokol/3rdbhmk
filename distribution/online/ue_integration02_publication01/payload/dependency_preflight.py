"""Real UE Asset Registry preflight; never imported/executed by offline staging."""
from pathlib import Path
import json

def validate(root):
    import unreal
    root=Path(root)
    spec=json.loads((root/'dependency-evidence.json').read_text())
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous(['/Game'],force_rescan=True)
    options=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,
        include_soft_package_references=True,include_searchable_names=False,
        include_hard_management_references=False,include_soft_management_references=False)
    queue=list(spec['roots']);seen=set();unresolved=[]
    while queue:
        package=queue.pop()
        if package in seen or package.startswith('/Script/'):continue
        if len(seen)>=20000:raise RuntimeError('Dependency bound exceeded')
        seen.add(package)
        if not registry.get_assets_by_package_name(unreal.Name(package)):
            unresolved.append(package);continue
        for name in registry.get_dependencies(unreal.Name(package),options):
            item=str(name)
            if item not in seen:queue.append(item)
        if len(queue)>80000:raise RuntimeError('Dependency work bound exceeded')
    if unresolved:raise RuntimeError('Unresolved real registry packages; no reparent/save permitted')
    for path in spec['requiredClasses']:
        if not unreal.load_class(None,path):raise RuntimeError('Required real plugin class unavailable')
    return {'packages':len(seen),'unresolved':0,'kind':'actual asset registry, not cook/runtime proof'}

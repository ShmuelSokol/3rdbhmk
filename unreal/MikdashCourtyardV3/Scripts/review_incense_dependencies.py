"""Reopen smoke without authoring converter; inspect recursive package dependencies."""
import unreal, json, time
from pathlib import Path
root = Path(unreal.Paths.project_dir()).resolve()
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.search_all_assets(True)
options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True, include_searchable_names=False, include_soft_management_references=False, include_hard_management_references=False)
package = '/Game/MikdashV3/MaterialReview/IncenseSmokeV1/NS_FiniteIncenseStudy'
asset = unreal.load_asset(package)
assert isinstance(asset, unreal.NiagaraSystem), 'Niagara system failed to reopen'
queue, seen, scripts, missing = [package], set(), set(), []
start = time.monotonic()
while queue:
    assert len(seen) < 10000 and time.monotonic() - start < 120
    current = queue.pop()
    if current in seen:
        continue
    seen.add(current)
    if current.startswith('/Script/'):
        scripts.add(current)
        continue
    if not registry.get_assets_by_package_name(current):
        missing.append(current)
    queue.extend(str(p) for p in registry.get_dependencies(current, options) or [] if str(p) not in seen)
converter = sorted(p for p in seen if 'CascadeToNiagara' in p or 'NiagaraConverter' in p)
report = dict(status='reopen_and_registry_scan_passed' if not missing and not converter else 'dependency_review_required', asset=asset.get_path_name(), className=asset.get_class().get_name(), packages=sorted(seen), missingPackages=missing, converterReferences=converter, scriptPackages=sorted(scripts), limitations='Registry graph and native reopen only; editor modules and cook stripping require a cook test; no visual or runtime acceptance.')
(root / 'SourceAssets/runtime-review/incense-native-dependencies.json').write_text(json.dumps(report, indent=2)+'\n')
unreal.log('INCENSE_DEPENDENCY_REVIEW ' + report['status'])
assert not converter, 'Authoring converter dependency retained'
assert not missing, 'Missing dependency packages'

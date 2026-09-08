"""Preparation only: audit prospective water hosts; NEVER modifies Unreal assets.

Offline: python Scripts/release_water_openings.py
Native (root's serial slot): import release_water_openings as w; report=w.audit_native()
No automatic native entry, map load/save, boolean, actor change or receipt write.
Candidate subtraction is intentionally unavailable until closed cutters are reviewed.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
GEOMETRY = ROOT / 'SourceAssets/water-review/MikdashWaterV1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def base_name(value):
    return ''.join(c for c in value if not c.isdigit()).strip().rstrip('-').strip()


def route_literals(path):
    # Read the actual cover/bed flags, which exported waypoints omit. Do not import
    # an authoring module or evaluate arbitrary source expressions.
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == 'COURT_ROUTE' for t in node.targets):
            rows = []
            for item in node.value.elts:
                if not isinstance(item, ast.Call) or not isinstance(item.func, ast.Name) or item.func.id != 'dict' or item.args:
                    raise ValueError('Unexpected route syntax; audit must be updated explicitly')
                rows.append({k.arg: ast.literal_eval(k.value) for k in item.keywords})
            return rows
    raise ValueError('COURT_ROUTE missing')


def offline_plan():
    manifest_path = GEOMETRY / 'geometry-manifest.json'
    arch_path = ROOT / 'SourceAssets/architecture-manifest.json'
    script_path = ROOT / 'Scripts/create_water_geometry.py'
    manifest = read_json(manifest_path)
    if digest(script_path) != manifest['scriptSha256']:
        raise ValueError('Generator differs from frozen geometry; regenerate/review before planning')
    if digest(arch_path) != manifest['architectureManifest']['sha256']:
        raise ValueError('Architecture manifest changed')
    boxes_path = GEOMETRY / manifest['clearanceBoxesFile']
    if digest(boxes_path) != manifest['clearanceBoxesSha256']:
        raise ValueError('Clearance sections changed')
    hosts = {h['mesh']: h for h in manifest['clearance']['hosts']}
    candidates = []
    for mesh in read_json(arch_path)['meshes']:
        name = base_name(mesh['sourceName'])
        if name in hosts:
            candidates.append(dict(assetName=mesh['assetName'], sourceName=mesh['sourceName'],
                                   evidence=hosts[name], sourceBoundsCm=mesh['expectedBoundsUnrealCm']))
    return dict(status='PREPARATION_ONLY_CUTTERS_AND_NATIVE_ACCEPTANCE_MISSING',
                target=TARGET, amahCm=manifest['amahCm'],
                hashes={str(p.relative_to(ROOT)): digest(p) for p in
                        (manifest_path, arch_path, script_path, boxes_path)},
                route=route_literals(script_path), hostCandidates=candidates,
                warning='Host family membership is NOT permission to cut every matching instance. '
                        'Decomposed masonry boxes are NOT void/cutter solids.',
                blockers=['No reviewed closed cavity cutters with preserved bridge roofs',
                          'No per-triangle intersection proof for live transformed host geometry',
                          'No replacement collision cooking or walking proof',
                          'Far-field terrain is excluded by current water clearance'])


def audit_native():
    """Read ONLY the already loaded accepted editor world; refuse PIE and wrong map."""
    import unreal as ue
    plan = offline_plan()
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('Live game world; postpone audit')
    world = editor.get_editor_world()
    actual = world.get_path_name().split('.')[0]
    if actual != TARGET:
        raise RuntimeError('Expected already loaded target, got ' + actual)
    map_path = ROOT / 'Content' / (TARGET[6:] + '.umap')
    before = digest(map_path)
    candidates = {r['assetName'] for r in plan['hostCandidates']}
    found = []
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
    for actor in actors:
        for component in actor.get_components_by_class(ue.StaticMeshComponent):
            mesh = component.get_editor_property('static_mesh')
            if mesh is None or mesh.get_name() not in candidates:
                continue
            transform = component.get_world_transform()
            p, s, q = transform.translation, transform.scale3d, transform.rotation
            found.append(dict(actor=actor.get_name(), label=actor.get_actor_label(),
                              component=component.get_name(), mesh=mesh.get_path_name(),
                              position=[p.x, p.y, p.z], scale=[s.x, s.y, s.z],
                              quaternion=[q.x, q.y, q.z, q.w],
                              materials=[str(component.get_material(i)) for i in range(component.get_num_materials())],
                              collisionProfile=str(component.get_collision_profile_name()),
                              renderTriangles=mesh.get_num_triangles(0)))
    if digest(map_path) != before:
        raise RuntimeError('Map changed during read-only audit')
    plan.update(nativeCandidates=found, mapSha256=before,
                missingAssetNames=sorted(candidates - {r['mesh'].split('.')[-1] for r in found}))
    return plan


def apply(*args, **kwargs):
    raise RuntimeError('Mutation unavailable: reviewed closed cutters and bridge/collision proof required')


if __name__ == '__main__':
    print(json.dumps(offline_plan(), indent=2))

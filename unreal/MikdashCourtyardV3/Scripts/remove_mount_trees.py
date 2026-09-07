"""Remove only source-linked trees rooted on the Mount in the future scenario.

prepare_manifest() is offline. apply() is explicit, idle-editor-only and saves
only L_FutureMount after survivor readback. No whole actor/component deletion.
UE5.8 native references: InstancedStaticMeshComponent.h:417/421 RemoveInstance(s),
InstancedStaticMesh.cpp:4172 reverse-index removal; either stable or swap compaction
is accepted only when complete surviving transforms/custom colors match.
"""
import collections
import hashlib
import json
import math
import shutil
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
FOLDER = ROOT/'SourceAssets/FutureMountV1'
SOURCE = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\cloud-unreal-v3\context-review\instances-manifest.json')
BUILDER = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\mikdash-walkthrough\lib\mikdash\jerusalem.ts')
DESIGN = ROOT/'SourceAssets/visual-review/mount-platform-design.json'
MANIFEST = FOLDER/'mount-tree-removal-manifest.json'
MAP = '/Game/MikdashV3/FutureMountV1/L_FutureMount'
INST = '/Game/MikdashV3/JerusalemContext/DecorativeInstancesV1/Meshes/'
SOURCE_SHA = '5b80379b80b891dc20809a025bb69a15c5219123d23f6a25e0bc1de81199ec33'
BUILDER_SHA = '61a2c2400bb80e1530fb30356b5ecd05da62121df874942988b049993051b924'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside_or_boundary(point, ring):
    x, y = point
    inside = False
    for a, b in zip(ring, ring[1:]+ring[:1]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length2 = dx*dx+dy*dy
        if length2:
            t = min(1, max(0, ((x-a[0])*dx+(y-a[1])*dy)/length2))
            if math.hypot(x-a[0]-t*dx, y-a[1]-t*dy) <= .001:
                return True
        if (a[1] > y) != (b[1] > y) and x < a[0]+(y-a[1])*dx/dy:
            inside = not inside
    return inside


def prepare_manifest():
    assert sha(SOURCE) == SOURCE_SHA and sha(BUILDER) == BUILDER_SHA
    builder = BUILDER.read_text()
    assert 'trunks.setMatrixAt(i,dummy.matrix)' in builder and 'crowns.setMatrixAt(i*3+k,dummy.matrix)' in builder
    data = json.loads(SOURCE.read_text())
    groups = {g['sourceCategory']: g for g in data['groups']}
    trunks, crowns = groups['Tree trunks'], groups['Tree crowns']
    assert crowns['instanceCount'] == 3*trunks['instanceCount'] == 13227
    ring = json.loads(DESIGN.read_text())['boundary']['nativeXYcm']
    assert len(ring) == 66 and ring[0] == ring[-1]
    removals = []
    for index, trunk in enumerate(trunks['instances']):
        assert trunk['sourceInstanceIndex'] == index
        if inside_or_boundary(trunk['translationUnrealCm'][:2], ring):
            linked = [3*index+k for k in range(3)]
            assert all(crowns['instances'][i]['sourceInstanceIndex'] == i for i in linked)
            removals.append(dict(sourceTreeId='jerusalem-tree-'+str(index), trunkSourceIndex=index,
                crownSourceIndices=linked, trunkAnchorXYcm=trunk['translationUnrealCm'][:2]))
    report = dict(version=1, status='source_verified_native_apply_pending', scenarioMap=MAP,
        sourceManifest=str(SOURCE), sourceSha256=SOURCE_SHA, builderSource=str(BUILDER), builderSha256=BUILDER_SHA,
        designSha256=sha(DESIGN), boundaryXYcm=ring,
        classification='Trunk root XY inside or within 0.001cm of full original inferred Mount enclosure. Not inset platform boundary.',
        linkage='Retained jerusalem.ts line89: trunk i has crowns 3*i,3*i+1,3*i+2. Not proximity matching.',
        removedTrees=len(removals), removedCrowns=len(removals)*3, retainedTrees=trunks['instanceCount']-len(removals),
        groups={k: dict(asset=INST+groups[k]['assetName'], sourceCount=groups[k]['instanceCount']) for k in ['Tree trunks','Tree crowns']},
        removals=removals,
        limitations=['Existing trees are illustrative OSM-polygon samples, not individually surveyed trees.',
            'Outside-rooted trees are preserved including any crown overhang across the inferred boundary.',
            'No outside vegetation upgrade, terrain clipping, road or transit change.',
            'Future scenario choice; inferred enclosure awaits native visual overlay acceptance.'])
    MANIFEST.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def apply():
    import unreal as ue
    assert Path(ue.Paths.project_dir()).resolve() == ROOT
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    assert not editor.get_game_world(), 'Stop play first'
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Preserve unsaved map work'
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Preserve unsaved assets'
    manifest = json.loads(MANIFEST.read_text())
    assert sha(SOURCE) == manifest['sourceSha256'] == SOURCE_SHA
    assert sha(BUILDER) == manifest['builderSha256'] == BUILDER_SHA
    assert sha(DESIGN) == manifest['designSha256']
    assert manifest['boundaryXYcm'] == json.loads(DESIGN.read_text())['boundary']['nativeXYcm']
    # Recompute classification before trusting any deletion indices in the manifest.
    data = json.loads(SOURCE.read_text())
    groups = {g['sourceCategory']: g for g in data['groups']}
    remove_trunks = [i for i,r in enumerate(groups['Tree trunks']['instances']) if inside_or_boundary(r['translationUnrealCm'][:2],manifest['boundaryXYcm'])]
    assert remove_trunks == [r['trunkSourceIndex'] for r in manifest['removals']]
    assert all(r['crownSourceIndices'] == [3*r['trunkSourceIndex']+k for k in range(3)] for r in manifest['removals'])
    remove = {'Tree trunks': remove_trunks, 'Tree crowns': [3*i+k for i in remove_trunks for k in range(3)]}
    assert remove_trunks, 'No removals: inspect classification'
    receipt = FOLDER/'native-mount-tree-removal.json'
    checkpoint = FOLDER/'Checkpoints/BeforeTreeRemoval/L_FutureMount.umap'
    assert not receipt.exists() and not checkpoint.exists(), 'Prior run preserved; inspect before retry'
    original = ROOT/'Content/MikdashV3/Maps/Courtyard.umap'
    scenario = ROOT/'Content/MikdashV3/FutureMountV1/L_FutureMount.umap'
    original_sha = sha(original)
    report = dict(status='started', manifestSha256=sha(MANIFEST), map=MAP, groups=[], limitations=manifest['limitations'])
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    try:
        assert levels.load_level(MAP)
        def transform_numbers(transform):
            values=[]
            for point in [(0,0,0),(100,0,0),(0,100,0),(0,0,100)]:
                p=transform.transform_location(ue.Vector(*point));values.extend((p.x,p.y,p.z))
            return tuple(values)
        def actor_snapshot():
            return sorted((a.get_name(), transform_numbers(a.get_actor_transform())) for a in actors.get_all_level_actors())
        baseline_actors = actor_snapshot()
        def components():
            found = {}
            for actor in actors.get_all_level_actors():
                for component in actor.get_components_by_class(ue.InstancedStaticMeshComponent):
                    mesh = component.get_editor_property('static_mesh')
                    if mesh and mesh.get_path_name().split('.')[0].startswith(INST):
                        path = mesh.get_path_name().split('.')[0]
                        assert path not in found, 'Duplicate decorative ISM mesh'
                        assert component.get_class() == ue.InstancedStaticMeshComponent.static_class(), 'Unexpected derived ISM removal semantics'
                        found[path] = component
            assert set(found) == {INST+g['assetName'] for g in data['groups']}
            return found
        def read(component):
            stride = int(component.get_editor_property('num_custom_data_floats'))
            colors = list(component.get_editor_property('per_instance_sm_custom_data'))
            assert len(colors) == component.get_instance_count()*stride
            rows = []
            for index in range(component.get_instance_count()):
                transform = component.get_instance_transform(index, world_space=True)
                probes = []
                for point in [(0,0,0),(100,0,0),(0,100,0),(0,0,100)]:
                    p = transform.transform_location(ue.Vector(*point))
                    probes.extend((p.x,p.y,p.z))
                values = probes+colors[index*stride:(index+1)*stride]
                assert all(math.isfinite(v) for v in values)
                rows.append(tuple(values))
            state = (component.get_editor_property('static_mesh').get_path_name(), component.get_material(0).get_path_name(),
                transform_numbers(component.get_world_transform()), str(component.get_collision_enabled()),
                str(component.get_editor_property('mobility')), stride,
                component.get_editor_property('can_ever_affect_navigation'),component.get_editor_property('generate_overlap_events'))
            return rows,state
        before = {}
        refs = components()
        for category, group in groups.items():
            path = INST+group['assetName']
            component = refs[path]
            rows,state = read(component)
            assert len(rows) == group['instanceCount']
            for index, record in enumerate(group['instances']):
                matrix = record['matrixUnrealRowMajor']
                expected = []
                for point in [(0,0,0),(100,0,0),(0,100,0),(0,0,100)]:
                    expected.extend(sum(matrix[k*4+j]*point[j] for j in range(3))+matrix[k*4+3] for k in range(3))
                assert max(abs(a-b) for a,b in zip(rows[index][:12],expected)) < .1
                if category == 'Tree crowns':
                    assert len(rows[index]) == 15
                    assert max(abs(a-b) for a,b in zip(rows[index][12:],record['linearTint'])) < 1e-6
            before[category] = (rows,state)
        checkpoint.parent.mkdir(parents=True)
        shutil.copy2(scenario,checkpoint)
        assert sha(checkpoint) == sha(scenario)
        report['checkpoint'] = str(checkpoint)
        expected_survivors = {}
        for category, group in groups.items():
            indices = set(remove.get(category,[]))
            rows,state = before[category]
            survivors = [row for i,row in enumerate(rows) if i not in indices]
            expected_survivors[category] = collections.Counter(survivors)
            if indices:
                component = refs[INST+group['assetName']]
                component.modify()
                assert component.remove_instances(sorted(indices,reverse=True))
        def verify():
            assert actor_snapshot() == baseline_actors, 'Actor inventory/transform changed'
            current = components()
            results = []
            for category, group in groups.items():
                rows,state = read(current[INST+group['assetName']])
                assert state == before[category][1], 'ISM material/transform/settings changed'
                assert collections.Counter(rows) == expected_survivors[category], 'Survivor transform/color mismatch: '+category
                results.append(dict(category=category, before=group['instanceCount'], after=len(rows),
                    removed=len(remove.get(category,[])), everySurvivorTransformAndColorPreserved=True))
            return results
        verify()
        world = editor.get_editor_world()
        assert world.get_outermost().get_name() == MAP
        assert ue.EditorLoadingAndSavingUtils.save_map(world,MAP)
        assert levels.load_level(MAP)
        report['groups'] = verify()
        assert sha(original) == original_sha
        report.update(status='saved_reopened_source_linked_mount_trees_removed_visual_review_pending',
            originalMapUnchanged=True, originalMapSha256=original_sha, scenarioSha256=sha(scenario),
            outsideTreesPreserved=True, otherDecorativeInstancesPreserved=True)
    except Exception as error:
        report.update(status='failed_partial_state_preserved',error=str(error))
        raise
    finally:
        report['originalMapUnchanged'] = sha(original) == original_sha
        receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report

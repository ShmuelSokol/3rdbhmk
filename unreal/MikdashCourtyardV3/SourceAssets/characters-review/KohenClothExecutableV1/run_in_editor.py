"""Actual isolated import/build/bind/one-walk entry point. DO NOT run before review."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import runpy
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic(path, data):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    temp.rename(path)


def execute():
    import unreal as ue
    if Path(ue.Paths.get_project_file_path()).resolve() != (HERE / 'ReviewProject/KohenClothReview.uproject').resolve():
        raise RuntimeError('Wrong project. Active courtyard project is prohibited.')
    manifest = json.loads((HERE / 'source-manifest-v4.json').read_text())
    for path, expected in manifest['inputs'].items():
        if sha(ROOT / path) != expected:
            raise RuntimeError('Pinned source changed: ' + path)
    # Publication-only offline success cannot substitute for every active original.
    runpy.run_path(str(HERE / 'source_contract.py'))['require_native'](ROOT, HERE)
    prepared = ROOT / manifest['preparedInput']
    model = json.loads(prepared.read_text())
    source = ROOT / manifest['combinedSource']
    walk_source = ROOT / model['walk']['glb']
    namespace = '/Game/KohenClothFeasibilityV1/Import/' + uuid.uuid4().hex
    if ue.EditorAssetLibrary.does_directory_exist(namespace):
        raise RuntimeError('Fresh import namespace required')
    # Preserve all existing active-project native files and original GLBs by bytes.
    protected = [p for p in (ROOT / 'Content').rglob('*') if p.suffix in ('.uasset', '.umap')]
    protected += list((ROOT / 'SourceAssets/characters-review').rglob('*.glb'))
    protected += [ROOT / p for p in manifest['inputs']]
    before = {str(p): sha(p) for p in protected}
    output = HERE / 'ReviewProject/Saved/KohenClothWalk' / uuid.uuid4().hex
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        tools = ue.AssetToolsHelpers.get_asset_tools()

        def import_task(path, folder, override):
            task = ue.AssetImportTask()
            for key, value in dict(filename=str(path), destination_path=folder,
                                   automated=True, replace_existing=False, save=False, options=override).items():
                task.set_editor_property(key, value)
            tools.import_asset_tasks([task])
            return list(task.get_objects())

        # Fresh reference rig and unchanged walk source. No production packages are mounted/copied.
        pipeline = ue.InterchangeGenericAssetsPipeline()
        mesh_options = pipeline.get_editor_property('mesh_pipeline')
        mesh_options.set_editor_property('import_static_meshes', False)
        mesh_options.set_editor_property('import_skeletal_meshes', True)
        mesh_options.set_editor_property('create_physics_asset', False)
        pipeline.get_editor_property('material_pipeline').set_editor_property('import_materials', False)
        animation_options = pipeline.get_editor_property('animation_pipeline')
        for key, value in dict(import_animations=True, use30_hz_to_bake_bone_animation=False,
                               custom_bone_animation_sample_rate=60, snap_to_closest_frame_boundary=False).items():
            animation_options.set_editor_property(key, value)
            if animation_options.get_editor_property(key) != value:
                raise RuntimeError('Walk import setting not retained: ' + key)
        override = ue.InterchangePipelineStackOverride()
        override.add_pipeline(pipeline)
        rig_objects = import_task(walk_source, namespace + '/Rig', override)
        skeletons = [o for o in rig_objects if isinstance(o, ue.Skeleton)]
        walks = [o for o in rig_objects if isinstance(o, ue.AnimSequence) and model['walk']['clip'] in o.get_name()]
        if len(skeletons) != 1 or len(walks) != 1:
            raise RuntimeError('Expected one fresh skeleton and uniquely named walk animation')
        skeleton, walk = skeletons[0], walks[0]
        builder = runpy.run_path(str(HERE / 'mesh_import_pipeline.py'))['_mesh_pipeline']
        override, settings = builder(ue, skeleton, import_materials=False)
        objects = import_task(source, namespace + '/Combined', override)
        meshes = [o for o in objects if isinstance(o, ue.SkeletalMesh)]
        if len(meshes) != 1 or any(isinstance(o, (ue.Skeleton, ue.AnimSequence)) for o in objects):
            raise RuntimeError('Combined import must preserve fresh reference skeleton and add only one mesh')
        if meshes[0].get_editor_property('skeleton') != skeleton or walk.get_editor_property('skeleton') != skeleton:
            raise RuntimeError('Import rig identity mismatch')
        receipt = json.loads(ue.KohenClothExecutableLibrary.run_one_walk(meshes[0], walk, str(prepared), str(output)))
        if not output.exists():
            output.mkdir()
        atomic(output / 'python-return.json', receipt)
        atomic(output / 'import.json', dict(sourceSha256=sha(source), walkSha256=sha(walk_source),
            preparedSha256=sha(prepared), namespace=namespace, settings=settings,
            sourceMesh=meshes[0].get_path_name(), walk=walk.get_path_name(), noSave=True))
        if not receipt.get('apiFeasibilityCompleted'):
            raise RuntimeError('Native feasibility failed; retained readback: ' + str(output))
    finally:
        changed = [p for p, expected in before.items() if sha(p) != expected]
        output.mkdir(parents=True, exist_ok=True)
        atomic(output / 'source-preservation.json', dict(passed=not changed, filesChecked=len(before), changed=changed))
        if changed:
            raise RuntimeError('Protected source changed; do not advance')
    ue.log('KOHEN_CLOTH_READBACK=' + str(output))


if __name__ == '__main__':
    execute()

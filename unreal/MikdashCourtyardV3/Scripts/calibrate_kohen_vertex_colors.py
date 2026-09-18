"""Native skeletal GLB color calibration in a fresh, unsaved asset namespace."""
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/KohenSkinV2'
COLOR = (.25, .5, .75, 1.)


def fixture(path):
    binary = bytearray()
    views, accessors = [], []

    def add(rows, kind, component, fmt, bounds=False):
        while len(binary) % 4:
            binary.append(0)
        start = len(binary)
        for row in rows:
            binary.extend(struct.pack('<' + fmt * len(row), *row))
        views.append({'buffer': 0, 'byteOffset': start, 'byteLength': len(binary) - start})
        accessor = {'bufferView': len(views) - 1, 'componentType': component,
                    'count': len(rows), 'type': kind}
        if bounds:
            accessor.update(min=[min(x) for x in zip(*rows)], max=[max(x) for x in zip(*rows)])
        accessors.append(accessor)
        return len(accessors) - 1

    position = add([(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0)], 'VEC3', 5126, 'f', True)
    normal = add([(0, 0, 1)] * 4, 'VEC3', 5126, 'f')
    color = add([COLOR] * 4, 'VEC4', 5126, 'f')
    joints = add([(0, 0, 0, 0)] * 4, 'VEC4', 5123, 'H')
    weights = add([(1, 0, 0, 0)] * 4, 'VEC4', 5126, 'f')
    indices = add([(x,) for x in (0, 1, 2, 0, 2, 3)], 'SCALAR', 5123, 'H')
    inverse = add([(1., 0, 0, 0, 0, 1., 0, 0, 0, 0, 1., 0, 0, 0, 0, 1.)], 'MAT4', 5126, 'f')
    doc = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0, 1]}],
           'nodes': [{'name': 'CalibrationRoot'}, {'name': 'ColorSwatch', 'mesh': 0, 'skin': 0}],
           'skins': [{'joints': [0], 'skeleton': 0, 'inverseBindMatrices': inverse}],
           'meshes': [{'name': 'ColorSwatch', 'primitives': [{'attributes': {'POSITION': position,
               'NORMAL': normal, 'COLOR_0': color, 'JOINTS_0': joints, 'WEIGHTS_0': weights},
               'indices': indices, 'material': 0}]}],
           'materials': [{'name': 'Calibration', 'doubleSided': True}],
           'bufferViews': views, 'accessors': accessors, 'buffers': [{'byteLength': len(binary)}]}
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary.extend(b'\0' * (-len(binary) % 4))
    data = struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(binary))
    data += struct.pack('<I4s', len(encoded), b'JSON') + encoded
    data += struct.pack('<I4s', len(binary), b'BIN\0') + binary
    with path.open('xb') as stream:
        stream.write(data)


def run():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    source = OUT / ('color-calibration-' + stamp + '.glb')
    output = source.with_suffix('.json')
    folder = '/Game/Characters/VertexColorCalibration_' + stamp
    report = {'status': 'started', 'scope': 'Fresh unsaved skeletal GLB; raw BaseColor render target',
              'sourceColorLinear': COLOR, 'folder': folder, 'source': source.name}
    spawned = []
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    try:
        fixture(source)
        report['sourceSha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        task = ue.AssetImportTask()
        for key, value in {'filename': str(source), 'destination_path': folder, 'automated': True,
                           'replace_existing': False, 'save': False}.items():
            task.set_editor_property(key, value)
        tools = ue.AssetToolsHelpers.get_asset_tools()
        tools.import_asset_tasks([task])
        objects = list(task.get_objects())
        report['imported'] = {o.get_path_name(): o.get_class().get_name() for o in objects}
        meshes = [o for o in objects if isinstance(o, ue.SkeletalMesh)]
        if len(meshes) != 1:
            raise RuntimeError('Calibration requires exactly one skeletal mesh')
        mat = tools.create_asset('M_VertexLinear', folder, ue.Material, ue.MaterialFactoryNew())
        mat.set_editor_property('used_with_skeletal_mesh', True)
        mat.set_editor_property('two_sided', True)
        mel = ue.MaterialEditingLibrary
        vertex = mel.create_material_expression(mat, ue.MaterialExpressionVertexColor)
        mask = mel.create_material_expression(mat, ue.MaterialExpressionComponentMask)
        for key, value in {'r': True, 'g': True, 'b': True, 'a': False}.items():
            mask.set_editor_property(key, value)
        if not mel.connect_material_expressions(vertex, '', mask, '') or not mel.connect_material_property(mask, '', ue.MaterialProperty.MP_BASE_COLOR):
            raise RuntimeError('Calibration graph connection failed')
        mel.recompile_material(mat)
        ue.AutomationLibrary.finish_loading_before_screenshot()
        world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        if world.get_outermost().get_name().startswith('/Game/'):
            raise RuntimeError('Production map refused')
        body = actors.spawn_actor_from_class(ue.SkeletalMeshActor, ue.Vector(), transient=True)
        spawned.append(body)
        body.skeletal_mesh_component.set_skeletal_mesh_asset(meshes[0])
        body.skeletal_mesh_component.set_material(0, mat)
        camera = actors.spawn_actor_from_class(ue.SceneCapture2D, ue.Vector(0, 150, 0), ue.Rotator(yaw=-90), transient=True)
        spawned.append(camera)
        capture = camera.get_component_by_class(ue.SceneCaptureComponent2D)
        capture.set_editor_property('capture_source', ue.SceneCaptureSource.SCS_BASE_COLOR)
        capture.set_editor_property('capture_every_frame', False)
        capture.set_editor_property('capture_on_movement', False)
        capture.set_editor_property('projection_type', ue.CameraProjectionMode.ORTHOGRAPHIC)
        capture.set_editor_property('ortho_width', 120.)
        target = ue.RenderingLibrary.create_render_target2d(world, 64, 64, ue.TextureRenderTargetFormat.RTF_RGBA32F)
        capture.set_editor_property('texture_target', target)
        ue.AutomationLibrary.finish_loading_before_screenshot()
        capture.capture_scene()
        samples = []
        for x, y in ((32, 32), (28, 28), (36, 28), (28, 36), (36, 36)):
            value = ue.RenderingLibrary.read_render_target_raw_pixel(world, target, x, y, False)
            samples.append([value.r, value.g, value.b])
        report['rawBaseColorSamples'] = samples
        report['maximumLinearError'] = max(abs(v - wanted) for row in samples for v, wanted in zip(row, COLOR))
        srgb = [12.92 * x if x <= .0031308 else 1.055 * x ** (1 / 2.4) - .055 for x in COLOR[:3]]
        report['maximumSrgbError'] = max(abs(v - wanted) for row in samples for v, wanted in zip(row, srgb))
        if report['maximumLinearError'] > 2 / 255:
            raise RuntimeError('Imported raw colors do not match linear source within two quantization steps')
        report['status'] = 'linear-vertex-color-calibration-passed'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        for actor in reversed(spawned):
            actors.destroy_actor(actor)
        disk_folder = ROOT / 'Content' / folder.removeprefix('/Game/')
        report['nativeAssetsSaved'] = [str(p.relative_to(ROOT)) for p in disk_folder.rglob('*.uasset')]
        if report['nativeAssetsSaved']:
            report['status'] = 'failed_unexpected_asset_save'
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    run()

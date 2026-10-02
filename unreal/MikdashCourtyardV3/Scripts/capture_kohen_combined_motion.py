"""Transient native posed comparison: shipped, fresh source control, combined study.

Uses the approved skeleton/clips and original material bindings. Selected poses
are visual evidence only, not continuous animation or all-layer clearance proof.
Run through run_kohen_skin_study.ps1 -CombinedMotion; never saves assets/maps.
"""
import hashlib
import json
import runpy
import struct
from datetime import datetime, timezone
from pathlib import Path

import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/KohenCombinedV1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected():
    paths = list((ROOT / 'Content').rglob('*.umap'))
    for subtree in ('MikdashV3/Characters/KohenGadolV1', 'MikdashV3/Characters/PilgrimRigV3'):
        paths.extend((ROOT / 'Content' / subtree).rglob('*.uasset'))
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(paths))}


def run():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt = OUT / ('native-poses-' + stamp + '.json')
    report = {'status': 'started', 'scope': 'Selected native poses, not continuous motion or production adoption',
              'captures': [], 'imports': []}
    before = None
    spawned = []
    namespaces = []
    actors = None

    def spawn(cls, position, rotation=ue.Rotator()):
        actor = actors.spawn_actor_from_class(cls, position, rotation, transient=True)
        if actor is None:
            raise RuntimeError('Transient actor spawn failed')
        spawned.append(actor)
        return actor

    try:
        before = protected()
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        if world.get_outermost().get_name().startswith('/Game/'):
            raise RuntimeError('Refusing production map')
        production = ue.load_asset('/Game/MikdashV3/Characters/KohenGadolV1/Mesh/SK_KohenGadol_V1')
        if not isinstance(production, ue.SkeletalMesh):
            raise RuntimeError('Missing production body')
        skeleton = production.get_editor_property('skeleton')
        pipeline_builder = runpy.run_path(str(ROOT / 'Scripts/release_kohen_gadol_v1.py'))['_mesh_pipeline']
        source = OUT / 'SK_Kohen_KneeHairStudy01.glb'
        proof = json.loads(source.with_suffix('.json').read_text(encoding='utf-8-sig'))
        if digest(source) != proof['outputSha256'] or proof['outputSha256'] != 'b542efdc1a053fd5ae59720a578701355a4a6e5a203691d999755d6ee4f67535':
            raise RuntimeError('Combined source differs from reviewed study')
        original = ROOT / 'SourceAssets/characters-review/KohenGadolV1/meshes/SK_KohenGadol_V1.glb'
        original_hash = next(value for key, value in proof['sourceHashes'].items()
                             if key.replace('\\', '/').endswith('KohenGadolV1/meshes/SK_KohenGadol_V1.glb'))
        if digest(original) != original_hash:
            raise RuntimeError('Approved original source differs')
        variants = [('production', production)]
        for label, path in (('fresh-control', original), ('combined', source)):
            folder = '/Game/Characters/KohenPoseStudy_' + stamp + '/' + label.replace('-', '_')
            namespaces.append(folder)
            if ue.EditorAssetLibrary.does_directory_exist(folder):
                raise RuntimeError('Fresh namespace required')
            # Every slot is rebound to production materials below. Compiling the
            # unused GLB materials adds cost and can fail unrelated shader jobs.
            override, settings = pipeline_builder(ue, skeleton, import_materials=False)
            task = ue.AssetImportTask()
            for key, value in {'filename': str(path), 'destination_path': folder, 'automated': True,
                               'replace_existing': False, 'save': False, 'options': override}.items():
                task.set_editor_property(key, value)
            ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            objects = task.get_objects()
            meshes = [obj for obj in objects if isinstance(obj, ue.SkeletalMesh)]
            if len(meshes) != 1 or any(isinstance(obj, (ue.Skeleton, ue.AnimSequence)) for obj in objects):
                raise RuntimeError('Expected one mesh and no skeleton/animation creation')
            mesh = meshes[0]
            if mesh.get_editor_property('skeleton') != skeleton:
                raise RuntimeError('Imported body uses a different skeleton')
            variants.append((label, mesh))
            report['imports'].append({'label': label, 'sourceSha256': digest(path), 'mesh': mesh.get_path_name(),
                                      'pipeline': settings})
        body_actor = spawn(ue.SkeletalMeshActor, ue.Vector())
        body = body_actor.skeletal_mesh_component
        body.set_skeletal_mesh_asset(production)
        bindings = {str(name): body.get_material(i) for i, name in enumerate(body.get_material_slot_names())}
        light = spawn(ue.DirectionalLight, ue.Vector(0, 0, 1000), ue.Rotator(pitch=-35, yaw=-115, roll=0))
        light.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        light.light_component.set_editor_property('intensity', 3.0)
        capture = spawn(ue.SceneCapture2D, ue.Vector(0, 340, 92), ue.Rotator(yaw=-90))
        component = capture.get_component_by_class(ue.SceneCaptureComponent2D)
        component.set_editor_property('capture_every_frame', False)
        component.set_editor_property('capture_on_movement', False)
        component.set_editor_property('fov_angle', 35.0)
        component.set_editor_property('capture_source', ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        target = ue.RenderingLibrary.create_render_target2d(world, 720, 960, ue.TextureRenderTargetFormat.RTF_RGBA8)
        component.set_editor_property('texture_target', target)
        settings = component.get_editor_property('post_process_settings')
        for prop, value in {'override_auto_exposure_min_brightness': True, 'override_auto_exposure_max_brightness': True,
                            'auto_exposure_min_brightness': 1.0, 'auto_exposure_max_brightness': 1.0,
                            'override_auto_exposure_bias': True, 'auto_exposure_bias': 0.0,
                            'override_bloom_intensity': True, 'bloom_intensity': 0.0}.items():
            settings.set_editor_property(prop, value)
        component.set_editor_property('post_process_settings', settings)
        walk_record = json.loads((ROOT / 'SourceAssets/characters-review/PilgrimRigV3/walk-v2/walkv2-import-progress.json').read_text())['completed']['V3_Pilgrim_Man_Standard']
        tend_record = json.loads((ROOT / 'SourceAssets/characters-review/PilgrimRigV3/tend-v1/tend-import-progress.json').read_text())
        idle = next(path for path in walk_record['clips'] if 'Original_Idle' in path)
        poses = [('idle', idle, 0.5), ('walk-early', walk_record['newWalk'], 71 / 240),
                 ('walk-late', walk_record['newWalk'], 280 / 240), ('tend', tend_record['clip'], 7.6)]
        for pose_name, clip_path, seconds in poses:
            clip = ue.load_asset(clip_path)
            if not isinstance(clip, ue.AnimSequence) or clip.get_editor_property('skeleton') != skeleton:
                raise RuntimeError('Clip missing or off-skeleton: ' + clip_path)
            options = ue.AnimPoseEvaluationOptions()
            try:
                expected = ue.AnimPoseExtensions.get_anim_pose_at_time(clip, seconds, options)
            except TypeError:
                expected = ue.AnimPoseExtensions.get_anim_pose_at_time(clip, seconds, options, ue.AnimPose())
            for label, mesh in variants:
                # A commandlet stays on one engine frame. Reusing an anim instance
                # across clips can retain a cached pose even after OverrideAnimationData.
                # A fresh component per sample avoids that state; bone readback still gates it.
                if not actors.destroy_actor(body_actor):
                    raise RuntimeError('Previous sample body destruction failed')
                spawned.remove(body_actor)
                body_actor = spawn(ue.SkeletalMeshActor, ue.Vector())
                body = body_actor.skeletal_mesh_component
                body.set_skeletal_mesh_asset(mesh)
                names = [str(name) for name in body.get_material_slot_names()]
                if set(names) != set(bindings):
                    raise RuntimeError('Material slots differ')
                for i, name in enumerate(names):
                    body.set_material(i, bindings[name])
                # Native OverrideAnimationData ticks and refreshes the pose synchronously.
                body.override_animation_data(clip, False, False, seconds, 1.0)
                errors = {}
                for bone in ('pelvis', 'foot_r', 'head', 'hand_r'):
                    want = ue.AnimPoseExtensions.get_bone_pose(expected, bone, ue.AnimPoseSpaces.WORLD).translation
                    got = body.get_socket_location(bone)
                    errors[bone] = ((got.x-want.x)**2 + (got.y-want.y)**2 + (got.z-want.z)**2)**0.5
                if max(errors.values()) > 0.05:
                    raise RuntimeError('Rendered component pose disagrees with clip at '
                                       + pose_name + '/' + label + ': ' + repr(errors))
                for view, position, yaw in (('front', [0, 340, 92], -90), ('side', [340, 0, 92], 180)):
                    capture.set_actor_location(ue.Vector(*position), False, False)
                    capture.set_actor_rotation(ue.Rotator(yaw=yaw), False)
                    ue.AutomationLibrary.finish_loading_before_screenshot()
                    for _ in range(8):
                        component.capture_scene()
                        ue.RenderingLibrary.read_render_target_pixel(world, target, 360, 480)
                    filename = 'native-poses-' + stamp + '-' + pose_name + '-' + label + '-' + view + '.png'
                    path = OUT / filename
                    if path.exists():
                        raise RuntimeError('Fresh output required')
                    ue.RenderingLibrary.export_render_target(world, target, str(OUT), filename)
                    data = path.read_bytes()
                    if data[:8] != b'\x89PNG\r\n\x1a\n' or struct.unpack('>II', data[16:24]) != (720, 960):
                        raise RuntimeError('Invalid PNG')
                    report['captures'].append({'file': filename, 'sha256': digest(path), 'variant': label,
                                               'clip': clip_path, 'seconds': seconds, 'view': view,
                                               'positionCm': position, 'yaw': yaw, 'poseErrorCm': errors})
        report['status'] = 'captured_visual_review_pending'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        errors = []
        for actor in reversed(spawned):
            try:
                if not actors.destroy_actor(actor):
                    errors.append('Actor destruction returned false')
            except Exception as error:
                errors.append(repr(error))
        report['protectedAssetCount'] = len(before or {})
        report['protectedUnchanged'] = False
        try:
            report['protectedUnchanged'] = before is not None and before == protected()
            report['savedStudyAssets'] = [str(p) for folder in namespaces
                                         for p in (ROOT / 'Content' / folder.removeprefix('/Game/')).rglob('*.uasset')]
        except Exception as error:
            errors.append('Preservation check: ' + repr(error))
        report['cleanupErrors'] = errors
        if errors or not report['protectedUnchanged'] or report.get('savedStudyAssets'):
            report['status'] = 'failed_preservation_or_cleanup'
        receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if report['status'].startswith('failed'):
            raise RuntimeError('Native pose review failed; inspect ' + str(receipt))


if __name__ == '__main__':
    run()

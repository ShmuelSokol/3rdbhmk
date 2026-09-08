"""Explicit scene frame + one support-relative PlayerStart; isolated candidate only.

Default invocation is an offline plan. The coordinator owns the serial native slot
and may invoke run(apply=True) in the exact, clean candidate editor world.
"""
import hashlib
import importlib.util
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
PLAYER = 'PlayerStart_0'
LABEL = 'RELEASE_SceneUnits_Selected48_V1'
OLD_POSE = [2100.0, 0.0, 598.0001907348633, 0.0, 180.0, 0.0, 1.0, 1.0, 1.0]
NEW_POSE = [2016.0, 0.0, 578.0001907348633, 0.0, 180.0, 0.0, 1.0, 1.0, 1.0]
OFFSET = OLD_POSE[2] - 500.0


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name):
    spec = importlib.util.spec_from_file_location('frame48_' + name, ROOT / 'Scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def offline_plan():
    candidate = ROOT / 'Content' / (TARGET[6:] + '.umap')
    return dict(status='OFFLINE_PLAN_NATIVE_UNVERIFIED', candidate=TARGET,
                candidateSha256=sha(candidate), playerNativeName=PLAYER,
                oldPose=OLD_POSE, newPose=NEW_POSE, legacySupportCm=[2100, 0, 500],
                selectedSupportCm=[2016, 0, 480], physicalSupportOffsetCm=OFFSET,
                descriptor=dict(schema=1, coordinateRevision='Selected48V1',
                                sceneRevision='Selected48.v1', fixedOriginCm=[0, 0, 0]),
                scope='One new descriptor and PlayerStart_0 position only; no main/config/asset changes',
                runtimeAcceptance='PENDING: live collision, walking, wider 48 cm runtime dependencies')


def normalized(value):
    """Only floating serialization noise / equivalent Euler wrapping is normalized."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RuntimeError('Non-finite snapshot value')
        return round(value, 6)
    if isinstance(value, list):
        return [normalized(v) for v in value]
    if isinstance(value, dict):
        result = {k: normalized(v) for k, v in value.items()}
        if 'pose' in result:
            result['pose'][3:6] = [round((v + 180.0) % 360.0 - 180.0, 6)
                                    for v in result['pose'][3:6]]
        for axis in ('pitch', 'yaw', 'roll'):
            if axis in result and isinstance(result[axis], (float, int)):
                result[axis] = round((result[axis] + 180.0) % 360.0 - 180.0, 6)
        return result
    return value


def assert_pose(actor, expected, helper):
    actual = helper._pose(actor)
    for index, (a, b) in enumerate(zip(actual, expected)):
        delta = (a - b + 180.0) % 360.0 - 180.0 if 3 <= index <= 5 else a - b
        if not math.isfinite(a) or abs(delta) > 0.00001:
            raise RuntimeError('Unexpected pose for ' + actor.get_name() + ': ' + repr(actual))
    if actor.get_attach_parent_actor() or actor.get_attached_actors():
        raise RuntimeError('Attached actor requires separate migration: ' + actor.get_name())


def selected_enum(ue):
    enum = getattr(ue, 'MikdashSceneCoordinateRevision', None)
    if enum is None:
        raise RuntimeError('Compiled scene revision enum missing')
    # Named reflected member only, never infer a revision from its numeric ordinal.
    names = [n for n in dir(enum) if n.replace('_', '').lower() == 'selected48v1']
    if len(names) != 1:
        raise RuntimeError('Cannot resolve unique Selected48V1 enum: ' + repr(names))
    return getattr(enum, names[0])


def descriptor_readback(actor, selected):
    origin = actor.get_editor_property('fixed_architecture_origin_cm')
    values = dict(schema=actor.get_editor_property('descriptor_schema_version'),
                  coordinateRevision=str(actor.get_editor_property('coordinate_revision')),
                  sceneRevision=str(actor.get_editor_property('scene_revision')),
                  fixedOriginCm=[origin.x, origin.y, origin.z])
    if (values['schema'] != 1 or actor.get_editor_property('coordinate_revision') != selected
            or values['sceneRevision'] != 'Selected48.v1'
            or values['fixedOriginCm'] != [0.0, 0.0, 0.0]):
        raise RuntimeError('Descriptor reflected readback mismatch: ' + repr(values))
    result = actor.validate_descriptor()
    # Bindings may retain the success bool or use it to unpack the out string.
    # In this native method every failure supplies a nonempty Error; None and
    # arbitrary truthy tuples must never count as validation success.
    valid = result is True or (isinstance(result, str) and result == '')
    valid = valid or (isinstance(result, tuple) and len(result) == 2
                      and result[0] is True and result[1] == '')
    if not valid:
        raise RuntimeError('Native descriptor validation did not explicitly succeed: ' + repr(result))
    return values


def run(apply=False):
    report = offline_plan()
    if not apply:
        return report
    import unreal as ue
    if Path(ue.SystemLibrary.get_project_directory()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    ed = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    if ed.get_game_world() or ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Live or dirty world; refuse migration')
    if not ed.get_editor_world() or ed.get_editor_world().get_path_name().split('.')[0] != TARGET:
        raise RuntimeError('Exact isolated candidate required: ' + TARGET)
    descriptor_class = getattr(ue, 'MikdashSceneUnits', None)
    if descriptor_class is None:
        raise RuntimeError('Compiled MikdashSceneUnits class missing')
    selected = selected_enum(ue)
    all_actors = list(actors.get_all_level_actors())
    if any(isinstance(a, descriptor_class) for a in all_actors):
        raise RuntimeError('An existing descriptor must not be overwritten or duplicated')
    if any(a.get_actor_label() == LABEL or a.get_name() == LABEL for a in all_actors):
        raise RuntimeError('Descriptor identity collision')
    starts = [a for a in all_actors if a.get_name() == PLAYER]
    if len(starts) != 1 or starts[0].get_class().get_path_name() != '/Script/Engine.PlayerStart':
        raise RuntimeError('Exact native PlayerStart_0 required')
    player = starts[0]
    helper = module('release_resident_crowd')
    assert_pose(player, OLD_POSE, helper)
    units = module('release_amah48_candidate')
    protected = units.offline_plan()
    config_hashes = {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'Config').rglob('*.ini'))}
    if protected['source'] == TARGET:
        raise RuntimeError('Candidate must not be the default map')
    for folder in ('__ExternalActors__', '__ExternalObjects__'):
        if (ROOT / 'Content' / folder / TARGET[6:]).exists():
            raise RuntimeError('External packages unsupported')
    baseline = normalized(helper._scene_snapshot(ue, actors))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('Frame48-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    path = units.disk(TARGET)
    if sha(path) != report['candidateSha256']:
        raise RuntimeError('Candidate changed during preflight')
    shutil.copy2(path, checkpoint / 'Candidate.umap')
    if sha(checkpoint / 'Candidate.umap') != report['candidateSha256']:
        raise RuntimeError('Checkpoint hash mismatch')
    (checkpoint / 'baseline.json').write_text(json.dumps(baseline, indent=2), encoding='utf-8')
    receipt = ROOT / 'SourceAssets/scale-review' / ('amah48-frame-' + stamp + '.json')
    report.update(status='CHECKPOINTED_NATIVE_MUTATION_STARTED', checkpoint=str(checkpoint),
                  mapSaved=False, mapReopened=False, initialActorCount=len(baseline))

    def write_receipt():
        receipt.write_text(json.dumps(report, indent=2), encoding='utf-8')

    write_receipt()
    try:
        descriptor = actors.spawn_actor_from_class(descriptor_class, ue.Vector(0, 0, 0), ue.Rotator(0, 0, 0))
        if descriptor is None:
            raise RuntimeError('Descriptor spawn failed')
        descriptor_name = descriptor.get_name()  # Cache before reload invalidates handles.
        descriptor.set_actor_label(LABEL)
        descriptor.modify(True)
        descriptor.set_editor_property('descriptor_schema_version', 1)
        descriptor.set_editor_property('coordinate_revision', selected)
        descriptor.set_editor_property('scene_revision', 'Selected48.v1')
        descriptor.set_editor_property('fixed_architecture_origin_cm', ue.Vector(0, 0, 0))
        report['descriptorReadback'] = descriptor_readback(descriptor, selected)
        assert_pose(descriptor, [0, 0, 0, 0, 0, 0, 1, 1, 1], helper)
        player.modify(True)
        player.get_editor_property('root_component').modify(True)
        player.set_actor_location(ue.Vector(*NEW_POSE[:3]), False, True)
        assert_pose(player, NEW_POSE, helper)
        expected = normalized(helper._scene_snapshot(ue, actors))
        if set(expected) != set(baseline) | {descriptor_name} or len(expected) != len(baseline) + 1:
            raise RuntimeError('Unexpected actor creation/deletion')
        if {k: v for k, v in expected.items() if k not in (PLAYER, descriptor_name)} != {k: v for k, v in baseline.items() if k != PLAYER}:
            raise RuntimeError('Unrelated scene changed')
        # PlayerStart may change only translation, including its root translation.
        player_expected = json.loads(json.dumps(baseline[PLAYER]))
        player_expected['pose'][:3] = normalized(NEW_POSE[:3])
        for comp in player_expected['components']:
            if comp['name'] == player.get_editor_property('root_component').get_name():
                comp['relative_location'].update(x=NEW_POSE[0], y=NEW_POSE[1], z=NEW_POSE[2])
        if normalized(player_expected) != expected[PLAYER]:
            raise RuntimeError('PlayerStart changed beyond its support-relative translation')
        if sha(path) != report['candidateSha256']:
            raise RuntimeError('Candidate saved externally during mutation')
        if not levels.save_current_level():
            raise RuntimeError('Save returned false; checkpoint retained')
        report.update(mapSaved=True, savedMapSha256=sha(path), descriptorNativeName=descriptor_name)
        write_receipt()  # Preserve proof of disk mutation even if reload fails.
        if not levels.load_level(TARGET):
            raise RuntimeError('Reload failed after save')
        if ed.get_editor_world().get_path_name().split('.')[0] != TARGET:
            raise RuntimeError('Wrong world after reload')
        reopened = list(actors.get_all_level_actors())
        descriptors = [a for a in reopened if isinstance(a, descriptor_class)]
        if len(descriptors) != 1 or descriptors[0].get_name() != descriptor_name:
            raise RuntimeError('Descriptor identity/count changed on reload')
        report['descriptorReadback'] = descriptor_readback(descriptors[0], selected)
        fresh_player = [a for a in reopened if a.get_name() == PLAYER]
        if len(fresh_player) != 1:
            raise RuntimeError('PlayerStart missing after reload')
        assert_pose(fresh_player[0], NEW_POSE, helper)
        if normalized(helper._scene_snapshot(ue, actors)) != expected:
            raise RuntimeError('Saved/reopened scene snapshot mismatch')
        report.update(status='FRAME_AND_PLAYERSTART_SAVED_REOPENED_RUNTIME_ACCEPTANCE_PENDING',
                      mapReopened=True, finalActorCount=len(expected),
                      finalSnapshotSha256=hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest())
    except Exception as error:
        report.update(status='FAILED_CHECKPOINT_AVAILABLE', error=repr(error))
        raise
    finally:
        try:
            unchanged = units.offline_plan() == protected and config_hashes == {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / 'Config').rglob('*.ini'))}
            report.update(protectedUnchanged=unchanged, finalCandidateSha256=sha(path))
            if not unchanged:
                report['status'] = 'FAILED_PROTECTED_HASHES'
        except Exception as error:
            report.update(protectedUnchanged=False, protectionError=repr(error), status='FAILED_PROTECTION_AUDIT')
        write_receipt()
        if not report.get('protectedUnchanged'):
            raise RuntimeError('Protected files changed or protection audit failed; inspect checkpoint and receipt')
    return report


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))

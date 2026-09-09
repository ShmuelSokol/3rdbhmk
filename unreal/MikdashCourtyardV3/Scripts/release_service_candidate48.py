"""Candidate48 service placement only; no startup or runtime acceptance.

Native switches: -Service48ExpectedHash=<candidate sha256> to apply, or
-Service48Verify=<absolute apply receipt> in a fresh process. No default action.
Requires the compiled version-1 service scene-frame adapter. Station UPROPERTY
values deliberately remain legacy50: the native adapter converts them exactly once.
"""
import json
import os
from pathlib import Path
import re
import shutil
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
from release_surface_soft import sha, inventory, check_hashes
from release_place_assets import snapshot_row, numeric_baseline_rows
from release_kohen_service import load_spec, offline_check, _write_properties, _read_properties, _compare_properties

TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
LABEL = 'RELEASE_KohenGadolService_Selected48_V1'
TAG = 'ReleaseKohenServiceSelected48V1'
CLASS = '/Script/MikdashRuntime.MikdashServiceActor'
# Actor origin alone is decoded; station properties never are.
ORIGIN = [-3320.0, 0.0, 888.0]


def run(expected=None, verify=None):
    import unreal as u
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT / 'SourceAssets/service-review'
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / ('candidate-service-' + stamp + '.json')
    mapfile = ROOT / 'Content' / (TARGET[6:] + '.umap')
    report = {'status': 'started', 'map': TARGET, 'pid': os.getpid(),
              'mapSaved': False, 'errors': [], 'runtimeAcceptance': 'pending',
              'stationCoordinateContract': 'legacy50; native decode once', 'startupEnabled': False}
    before = sha(mapfile)
    protected = {}

    def write():
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    write()
    try:
        if bool(expected) == bool(verify):
            raise RuntimeError('Choose explicit expected-hash apply or fresh verification')
        inventory()
        if Path(u.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        spec = load_spec()
        if spec['actorProperties'].get('service_scenario') != 'ORDINARY_DAY':
            raise RuntimeError('Candidate placement supports ORDINARY_DAY only')
        report['legacyPlanOfflineCheck'] = offline_check(spec)
        props = dict(spec['actorProperties'])
        props.update(sequence_enabled=True, start_on_begin_play=False)
        report['properties'] = props
        report['sourceSpecSha256'] = sha(ROOT / 'Scripts/release_kohen_service.spec.json')
        earlier = json.loads(Path(verify).read_text(encoding='utf-8-sig')) if verify else None
        if earlier:
            if earlier.get('status') != 'saved_reopened' or earlier.get('map') != TARGET or earlier.get('pid') == os.getpid():
                raise RuntimeError('Invalid fresh verification receipt')
            if earlier['properties'] != props or earlier['sourceSpecSha256'] != report['sourceSpecSha256']:
                raise RuntimeError('Configuration changed since placement')
            if check_hashes(earlier['protected']):
                raise RuntimeError('Protected content changed since placement')
            expected = earlier['mapSha256After']
        if not re.fullmatch('[0-9a-fA-F]{64}', expected or '') or before != expected.lower():
            raise RuntimeError('Candidate hash mismatch')
        cls = u.load_class(None, CLASS)
        if cls is None:
            raise RuntimeError('Service class absent')
        descriptor_class = u.load_class(None, '/Script/MikdashRuntime.MikdashSceneUnits')
        if descriptor_class is None:
            raise RuntimeError('Scene descriptor class absent')
        default = u.get_default_object(cls)
        marker = getattr(default, 'get_service_scene_frame_adapter_version', None)
        if marker is None or marker() != 1:
            raise RuntimeError('Native service scene-frame adapter v1 is not compiled/loaded')
        if default.get_editor_property('sequence_enabled') or default.get_editor_property('start_on_begin_play'):
            raise RuntimeError('Unexpected active service class defaults')
        editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)

        def clean():
            if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('Game world or dirty packages')

        clean()
        protected = {str(p): sha(p) for p in (ROOT / 'Content').rglob('*') if p.is_file() and p != mapfile}
        report['protected'] = protected
        if not levels.load_level(TARGET):
            raise RuntimeError('Candidate load failed')
        clean()
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Wrong world')

        def discover():
            aa = list(actors.get_all_level_actors())
            descriptors = [a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(), descriptor_class)]
            if len(descriptors) != 1:
                raise RuntimeError('Scene descriptor class/subclass count must be exactly one')
            d = descriptors[0]
            if d.get_actor_label() != 'RELEASE_SceneUnits_Selected48_V1' or d.get_outermost().get_name() != TARGET:
                raise RuntimeError('Selected48 descriptor label/ownership mismatch')
            pivot = d.get_editor_property('fixed_architecture_origin_cm')
            if int(d.get_editor_property('descriptor_schema_version')) != 1 or int(d.get_editor_property('coordinate_revision').value) != 1 or str(d.get_editor_property('scene_revision')) != 'Selected48.v1' or [pivot.x, pivot.y, pivot.z] != [-6200, 0, 0]:
                raise RuntimeError('Selected48 frame mismatch')
            found = [a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(), cls)]
            owned = [a for a in aa if a.get_actor_label() == LABEL or TAG in [str(t) for t in a.tags]]
            return found, owned

        def snapshot():
            aa = [a for a in actors.get_all_level_actors() if a.get_outermost().get_name() == TARGET]
            result = numeric_baseline_rows([snapshot_row(u, a, TARGET) for a in aa], strict=True)
            for a in aa:
                for c in a.get_components_by_class(u.StaticMeshComponent):
                    for slot in range(c.get_num_materials()):
                        mat = c.get_material(slot)
                        result['material:' + c.get_path_name() + ':' + str(slot)] = mat.get_path_name() if mat else None
            return result

        found, owned = discover()
        if not verify and (found or owned):
            raise RuntimeError('Existing service or ownership collision; no replacement allowed')
        baseline = snapshot()
        clean()
        if not levels.load_level(TARGET):
            raise RuntimeError('Pristine reload failed')
        clean()
        if snapshot() != baseline:
            raise RuntimeError('Pristine persistent snapshot churn; review before mutation')
        if not verify:
            checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('ServiceCandidate48-' + stamp)
            checkpoint.mkdir(parents=True, exist_ok=False)
            shutil.copy2(mapfile, checkpoint / mapfile.name)
            if sha(checkpoint / mapfile.name) != before:
                raise RuntimeError('Checkpoint hash mismatch')
            for name in ('__ExternalActors__', '__ExternalObjects__'):
                source = ROOT / 'Content' / name / TARGET[6:]
                if source.exists():
                    shutil.copytree(source, checkpoint / name / TARGET[6:])
            report['checkpoint'] = str(checkpoint)
            write()
            actor = actors.spawn_actor_from_class(cls, u.Vector(*ORIGIN))
            if actor is None:
                raise RuntimeError('Spawn failed')
            actor.set_actor_label(LABEL)
            actor.set_folder_path('Runtime/KohenService')
            actor.set_editor_property('tags', [u.Name(TAG)])
            _compare_properties(_write_properties(u, actor, props), props, spec, 'before save')
            report['actorName'] = actor.get_name()
            delta = snapshot()
            if set(delta) - set(baseline) != {actor.get_name()} or any(delta.get(k) != v for k, v in baseline.items()):
                raise RuntimeError('Unexpected actor/component changes before save')
            if check_hashes(protected):
                raise RuntimeError('Protected content changed')
            if not levels.save_current_level():
                raise RuntimeError('Save refused')
            report['mapSaved'] = True
            report['mapSha256After'] = sha(mapfile)
            write()
            if not levels.load_level(TARGET):
                raise RuntimeError('Reopen failed')
        found, owned = discover()
        if len(found) != 1 or owned != found:
            raise RuntimeError('Exactly one owned service actor required')
        actor = found[0]
        if actor.get_class() != cls or actor.get_actor_label() != LABEL or [str(t) for t in actor.tags] != [TAG]:
            raise RuntimeError('Actor identity changed')
        if actor.get_name() != (earlier['actorName'] if verify else report['actorName']):
            raise RuntimeError('Saved actor identity differs')
        point = actor.get_actor_location()
        if max(abs(a-b) for a,b in zip([point.x,point.y,point.z], ORIGIN)) > .001:
            raise RuntimeError('Actor origin differs')
        _compare_properties(_read_properties(u, actor, props), props, spec, 'reloaded')
        after = snapshot()
        if not verify:
            after.pop(actor.get_name(), None)
            if after != baseline:
                raise RuntimeError('Unrelated persistent scene changes')
        elif after != baseline:
            raise RuntimeError('Verification changed scene')
        clean()
        report['actorName'] = actor.get_name()
        report['status'] = 'fresh_verified' if verify else 'saved_reopened'
    except Exception as error:
        report['status'] = 'failed'
        report['errors'].append(repr(error))
        raise
    finally:
        report['mapSha256After'] = sha(mapfile)
        report['protectedDifferences'] = check_hashes(protected)
        if report['protectedDifferences'] or (verify and report['mapSha256After'] != before):
            report['status'] = 'failed_preservation'
        write()
    if report['status'].startswith('failed'):
        raise RuntimeError(report['status'])
    return report


if __name__ == '__main__':
    try:
        import unreal as u
    except ImportError:
        print('Offline helper only; compiled adapter and native verification still required')
    else:
        command = u.SystemLibrary.get_command_line()
        args = {x.split('=', 1)[0].lower(): x.split('=', 1)[1].strip('"') for x in command.split() if '=' in x}
        try:
            run(expected=args.get('-service48expectedhash'), verify=args.get('-service48verify'))
        finally:
            if '-executepythonscript' in command.lower() and '-run=pythonscript' not in command.lower():
                u.SystemLibrary.quit_editor()

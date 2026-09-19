"""Guarded two-binding Candidate48 update; default is fresh-process verification."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import unreal as ue

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/water-review/CourtOutletV2'
MAP = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
BASE_SHA = '9daa88a181a44009467ab6a3f296dcff3ed9ff8b93500ddee593adc84ff0367e'
DEST = '/Game/MikdashV3/MaterialReview/CourtOutletV2/'
OLD = '/Game/MikdashV3/MaterialReview/MikdashWaterV1/Meshes/'
ASSETS = {'CourtChannel': 'cc4ee54d3385db0393bcd2e95b924bb91db8d5328286aac9229ca1610f4d5c8a',
          'CourtWater': 'f84c1fa375fcbb2b0f69380c5ea07d965fd05942372a231cd4a4d75f955413dd'}
APPLY = '-CourtOutletMapApply' in ue.SystemLibrary.get_command_line()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disk(path, extension='.uasset'):
    return ROOT / ('Content/' + path.removeprefix('/Game/') + extension)


def snapshot(actors):
    rows = {}
    for actor in actors:
        components = {}
        for component in actor.get_components_by_class(ue.StaticMeshComponent):
            mesh = component.get_editor_property('static_mesh')
            components[component.get_name()] = dict(
                mesh=mesh.get_path_name() if mesh else None,
                transform=component.get_editor_property('relative_location').export_text() +
                          component.get_editor_property('relative_rotation').export_text() +
                          component.get_editor_property('relative_scale3d').export_text(),
                materials=[m.get_path_name() if m else None for m in component.get_editor_property('override_materials')],
                profile=str(component.get_collision_profile_name()),
                collision=str(component.get_collision_enabled()),
                visible=component.get_editor_property('visible'),
                hiddenInGame=component.get_editor_property('hidden_in_game'))
        rows[actor.get_path_name()] = dict(label=actor.get_actor_label(),
            transform=actor.get_actor_transform().export_text(), tags=[str(t) for t in actor.tags],
            hidden=actor.get_editor_property('hidden'), collision=actor.get_actor_enable_collision(),
            components=components)
    return rows


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    report = dict(status='running', apply=APPLY, scope='Candidate48 two mesh bindings; no rendered or walking acceptance')
    output = OUT / ('map-' + stamp + '.json')
    map_file = disk(MAP, '.umap')
    protected = list((ROOT / 'Content').rglob('*.umap'))
    protected.remove(map_file)
    protected += [disk(OLD + 'SM_MikdashWaterV1_' + suffix) for suffix in ASSETS]
    before_protected = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    try:
        report['mapSha256Before'] = sha(map_file)
        meshes = {}
        # Preload these assets before the heavy map load.
        for suffix, digest in ASSETS.items():
            path = DEST + 'SM_CourtOutletV2_' + suffix
            assert sha(disk(path)) == digest, 'Unverified candidate asset'
            meshes[suffix] = ue.load_asset(path)
            assert meshes[suffix]
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        actors_api = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        if APPLY:
            assert sha(map_file) == BASE_SHA, 'Unexpected starting map'
            backup = ROOT / 'ReviewCheckpoints' / ('court-outlet-map-' + stamp)
            backup.mkdir(parents=True, exist_ok=False)
            shutil.copy2(map_file, backup / 'Walkthrough.umap')
            assert sha(backup / 'Walkthrough.umap') == BASE_SHA
            report['backup'] = str(backup / 'Walkthrough.umap')
        else:
            matching = []
            for path in OUT.glob('map-*.json'):
                prior = json.loads(path.read_text())
                if prior.get('status') == 'applied-needs-fresh-verification' and prior.get('mapSha256After') == sha(map_file):
                    matching.append((path, prior))
            assert len(matching) == 1, 'Expected one successful apply receipt for current map'
            prior_path, prior = matching[0]
            assert sha(Path(prior['backup'])) == BASE_SHA
            expected_file = Path(prior['snapshotAfter'])
            assert sha(expected_file) == prior['snapshotAfterSha256']
            report['applyReceipt'] = str(prior_path)
            report['applyReceiptSha256'] = sha(prior_path)
        assert levels.load_level(MAP), 'Map load failed'
        actors = list(actors_api.get_all_level_actors())
        before = snapshot(actors)
        expected = json.loads(json.dumps(before)) if APPLY else json.loads(expected_file.read_text())
        bindings = []
        for suffix, mesh in meshes.items():
            matches = [a for a in actors if a.get_actor_label() == 'RELEASE_Water_' + suffix]
            assert len(matches) == 1, 'Water actor must be unique'
            actor = matches[0]
            components = actor.get_components_by_class(ue.StaticMeshComponent)
            assert len(components) == 1, 'Water actor component ambiguity'
            component = components[0]
            required_profile = 'NoCollision' if suffix == 'CourtWater' else 'BlockAll'
            assert str(component.get_collision_profile_name()) == required_profile
            transform = actor.get_actor_transform()
            assert (transform.translation - ue.Vector(-248, 0, 0)).length() < 0.001
            assert (transform.scale3d - ue.Vector(.96, .96, .96)).length() < 0.001
            if APPLY:
                assert component.static_mesh.get_path_name().split('.')[0] == OLD + 'SM_MikdashWaterV1_' + suffix
                component.set_static_mesh(mesh)
                expected[actor.get_path_name()]['components'][component.get_name()]['mesh'] = mesh.get_path_name()
            assert component.static_mesh == mesh
            bindings.append(dict(actor=actor.get_path_name(), mesh=mesh.get_path_name(), profile=required_profile))
        after = snapshot(actors_api.get_all_level_actors())
        assert after == expected, 'Unexpected actor/component change'
        if APPLY:
            assert levels.save_current_level(), 'Map save failed'
            snapshot_path = backup / 'actors-after.json'
            snapshot_path.write_text(json.dumps(after, sort_keys=True), encoding='utf-8')
            report.update(snapshotAfter=str(snapshot_path), snapshotAfterSha256=sha(snapshot_path))
        else:
            assert sha(map_file) == report['mapSha256Before'], 'Verification modified map'
        report.update(mapSha256After=sha(map_file), actorCount=len(after), bindings=bindings,
                      status='applied-needs-fresh-verification' if APPLY else 'verified-fresh-map')
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['protectedHashes'] = before_protected
        report['protectedFilesUnchanged'] = all(sha(ROOT / p) == digest for p, digest in before_protected.items())
        if not report['protectedFilesUnchanged']:
            report.update(status='failed', error='Protected files changed')
        with output.open('x', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2)
            handle.write('\n')
        ue.log('Court outlet map: ' + str(output))


if __name__ == '__main__':
    main()

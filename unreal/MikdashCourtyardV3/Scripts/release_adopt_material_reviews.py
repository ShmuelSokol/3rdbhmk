"""Adopt reviewed component materials only; explicit -AdoptBus/-AdoptKotel.

Dedicated commandlet. Checkpoints the combined map, preserves donor maps/assets,
requires matching actor mesh/pose, and verifies a save/reopen. Never copies worlds.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
MAIN = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
GROUPS = {
    'bus': ('/Game/MikdashV3/MaterialReview/BusVisualAuditV1/Maps/Walkthrough', 'RELEASE_Bus_', 13),
    'kotel': ('/Game/MikdashV3/MaterialReview/KotelSurfacePolishV2/Maps/Walkthrough', 'RELEASE_Kotel_', 6),
}


def path(asset, extension='uasset'):
    return ROOT / 'Content' / (asset[6:] + '.' + extension)


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def run(groups):
    import unreal as ue
    assert groups and all(g in GROUPS for g in groups)
    assert Path(ue.Paths.project_dir()).resolve() == ROOT
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    assert not editor.get_game_world()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    def load(target):
        assert levels.load_level(target)
        assert editor.get_editor_world().get_outermost().get_name() == target
    def relative(comp):
        loc = comp.get_editor_property('relative_location')
        rot = comp.get_editor_property('relative_rotation')
        scale = comp.get_editor_property('relative_scale3d')
        return [loc.x, loc.y, loc.z, rot.pitch, rot.yaw, rot.roll, scale.x, scale.y, scale.z]
    def scene_snapshot(selected):
        result = {}
        for actor in actors.get_all_level_actors():
            loc, rot, scale = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
            row = dict(label=actor.get_actor_label(), cls=actor.get_class().get_path_name(),
                       pose=[loc.x,loc.y,loc.z,rot.pitch,rot.yaw,rot.roll,scale.x,scale.y,scale.z], components={})
            for comp in actor.get_components_by_class(ue.SceneComponent):
                item = dict(cls=comp.get_class().get_path_name(), relative=relative(comp))
                if isinstance(comp, ue.StaticMeshComponent):
                    mesh = comp.get_editor_property('static_mesh')
                    item.update(mesh=mesh.get_path_name() if mesh else None, collision=str(comp.get_collision_profile_name()))
                    if row['label'] not in selected:
                        item['materials'] = [comp.get_material(i).get_path_name() if comp.get_material(i) else None for i in range(comp.get_num_materials())]
                row['components'][comp.get_name()] = item
            result[actor.get_name()] = row
        return result
    def inventory(prefix):
        rows = {}
        for actor in actors.get_all_level_actors():
            label = actor.get_actor_label()
            if not label.startswith(prefix):
                continue
            assert label not in rows
            comp = actor.get_component_by_class(ue.StaticMeshComponent)
            assert comp and comp.get_num_materials() > 0
            mesh = comp.get_editor_property('static_mesh')
            assert mesh
            loc, rot, scale = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
            materials = [comp.get_material(i) for i in range(comp.get_num_materials())]
            assert all(materials)
            rows[label] = dict(mesh=mesh.get_path_name(),
                pose=[loc.x, loc.y, loc.z, rot.pitch, rot.yaw, rot.roll, scale.x, scale.y, scale.z],
                relative=relative(comp), collision=str(comp.get_collision_profile_name()), materials=[m.get_path_name() for m in materials])
        return rows
    protected = [path('/Game/MikdashV3/Maps/Courtyard', 'umap'),
                 path('/Game/MikdashV3/FutureMountV1/L_FutureMount', 'umap')]
    desired = {}
    for group in groups:
        donor, prefix, count = GROUPS[group]
        protected.append(path(donor, 'umap'))
        load(donor)
        desired[group] = inventory(prefix)
        assert len(desired[group]) == count
        for row in desired[group].values():
            protected.append(path(row['mesh'].split('.')[0]))
            protected.extend(path(m.split('.')[0]) for m in row['materials'])
    protected = sorted(set(protected))
    before_hashes = {str(p): sha(p) for p in protected}
    load(MAIN)
    baseline = {group: inventory(GROUPS[group][1]) for group in groups}
    for group in groups:
        assert baseline[group].keys() == desired[group].keys()
        for label, row in baseline[group].items():
            target = desired[group][label]
            assert all(row[k] == target[k] for k in ('mesh', 'pose', 'relative', 'collision')), label
            assert len(row['materials']) == len(target['materials'])
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    main_file = path(MAIN, 'umap')
    before = sha(main_file)
    checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('AdoptMaterials-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(main_file, checkpoint / 'Walkthrough.umap')
    assert sha(checkpoint / 'Walkthrough.umap') == before
    folder = ROOT / 'SourceAssets' / 'IntegratedReviewV2'
    receipt = folder / ('adopt-materials-' + stamp + '.json')
    report = dict(status='checkpointed', checkpoint=str(checkpoint), mapSha256Before=before,
                  groups=groups, before=baseline, desired=desired, protectedBefore=before_hashes, errors=[], mapSaved=False)
    def write():
        receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    write()
    try:
        actor_count = len(actors.get_all_level_actors())
        combined = {label: row for rows in desired.values() for label, row in rows.items()}
        unchanged_scene = scene_snapshot(set(combined))
        for actor in actors.get_all_level_actors():
            row = combined.get(actor.get_actor_label())
            if row is None:
                continue
            comp = actor.get_component_by_class(ue.StaticMeshComponent)
            for i, material_path in enumerate(row['materials']):
                material = ue.load_asset(material_path)
                assert isinstance(material, ue.MaterialInterface)
                comp.set_material(i, material)
        assert all(inventory(GROUPS[g][1]) == desired[g] for g in groups)
        assert scene_snapshot(set(combined)) == unchanged_scene, 'Unrelated scene state changed before save'
        assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()
        assert levels.save_current_level()
        report['mapSaved'] = True
        report['mapSha256AfterSave'] = sha(main_file)
        write()
        load(MAIN)
        assert len(actors.get_all_level_actors()) == actor_count
        assert all(inventory(GROUPS[g][1]) == desired[g] for g in groups)
        assert scene_snapshot(set(combined)) == unchanged_scene, 'Unrelated scene state changed after reopen'
        report['unrelatedSceneSnapshotUnchanged'] = True
        report['status'] = 'materials_adopted_saved_reopened'
    except Exception as exc:
        report['errors'].append(repr(exc))
        report['status'] = 'failed_after_save' if report['mapSaved'] else 'failed_before_save'
        raise
    finally:
        report['mapSha256After'] = sha(main_file)
        report['protectedUnchanged'] = all(sha(Path(p)) == digest for p, digest in before_hashes.items())
        if not report['protectedUnchanged']:
            report['status'] = 'failed_protected_hash_guard'
        write()
        assert report['protectedUnchanged']
    return report


if __name__ == '__main__':
    import unreal
    command = unreal.SystemLibrary.get_command_line().lower()
    run([group for group in GROUPS if ('-adopt' + group) in command])

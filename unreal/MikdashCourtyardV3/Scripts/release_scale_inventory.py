"""Read-only inventory of the active map for the approved 48 cm amah migration.

Run serially with -run=pythonscript -script=<this file> -nullrhi.
No asset import, actor mutation, package save, or world rescale is performed.
Whole-actor bounds are inventory evidence, never a collision-clearance test.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
PROTECTED = [
    'Content/MikdashV3/Maps/Courtyard.umap',
    'Content/MikdashV3/FutureMountV1/L_FutureMount.umap',
    'Content/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold.umap',
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def xyz(v):
    return [float(v.x), float(v.y), float(v.z)]

def run():
    import unreal as u
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = ROOT / 'SourceAssets/scale-review' / ('native-scale-inventory-' + stamp + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    map_file = ROOT / 'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap'
    files = [map_file] + [ROOT / p for p in PROTECTED]
    before = {str(p.relative_to(ROOT)): sha(p) for p in files}
    report = dict(status='started', map=MAP, actors=[], errors=[], beforeHashes=before,
                  scope='Read-only pre-migration inventory; not geometric or runtime acceptance',
                  legacyArchitectureAmahCm=50, userSelectedBookAmahCm=48)
    def write():
        out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    write()
    try:
        if Path(u.Paths.project_dir()).resolve() != ROOT.resolve():
            raise RuntimeError('Wrong project')
        ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        if ed.get_game_world() is not None:
            raise RuntimeError('PIE is running')
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages before inventory')
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if not levels.load_level(MAP):
            raise RuntimeError('Map load failed')
        if ed.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Wrong loaded world')
        actors = list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
        for actor in actors:
            try:
                loc, rot, scale = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
                origin, extent = actor.get_actor_bounds(False)
                parent = actor.get_attach_parent_actor()
                row = dict(name=actor.get_name(), label=actor.get_actor_label(),
                           classPath=actor.get_class().get_path_name(),
                           locationCm=xyz(loc), rotationDegrees=[rot.pitch, rot.yaw, rot.roll],
                           scale=xyz(scale), parent=parent.get_name() if parent else None,
                           boundsCm=dict(min=xyz(origin-extent), max=xyz(origin+extent)),
                           tags=[str(t) for t in actor.get_editor_property('tags')], components=[])
                for comp in actor.get_components_by_class(u.StaticMeshComponent):
                    mesh = comp.static_mesh
                    if mesh:
                        entry = dict(name=comp.get_name(), mesh=mesh.get_path_name(),
                                     materials=[comp.get_material(i).get_path_name() if comp.get_material(i) else None
                                                for i in range(comp.get_num_materials())])
                        if isinstance(comp, u.InstancedStaticMeshComponent):
                            entry['instanceCount'] = comp.get_instance_count()
                        row['components'].append(entry)
                for comp in actor.get_components_by_class(u.SkeletalMeshComponent):
                    mesh = comp.get_editor_property('skeletal_mesh_asset')
                    if mesh:
                        row['components'].append(dict(name=comp.get_name(), skeletalMesh=mesh.get_path_name()))
                report['actors'].append(row)
            except Exception as exc:
                report['errors'].append(dict(actor=actor.get_name(), error=repr(exc)))
        report['actorCount'] = len(actors)
        report['status'] = 'inventory_complete' if not report['errors'] else 'failed_incomplete_inventory'
    except Exception as exc:
        report['errors'].append(dict(error=repr(exc)))
        report['status'] = 'failed_inventory'
    finally:
        report['afterHashes'] = {str(p.relative_to(ROOT)): sha(p) for p in files}
        report['mapAndProtectedBytesUnchanged'] = report['afterHashes'] == before
        if not report['mapAndProtectedBytesUnchanged']:
            report['status'] = 'failed_unexpected_map_change'
        write()
        u.log('SCALE_INVENTORY ' + report['status'] + ' ' + str(out))
    if report['status'] != 'inventory_complete':
        raise RuntimeError('Inventory incomplete; inspect receipt before planning migration')
    return report

if __name__ == '__main__':
    run()
else:
    try:
        import unreal as u
    except ImportError:
        pass
    else:
        if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower():
            run()

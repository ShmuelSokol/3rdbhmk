"""Candidate48-only create-once StepStone collision duplicate; source untouched.
Use -CandidateStairCollisionExpectedHash=<reviewed candidate SHA256> to apply, or
-CandidateStairCollisionVerify=<absolute apply receipt> from a fresh process. Never auto-runs.
Collision flag persistence only. Real native traces and stair traversal remain pending.
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

TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
EXPECTED = '0099080da4e350b387e75ad49160976582ed73f26d5d9f29500a097f9ba9e8cb'
SOURCE = '/Game/MikdashV3/MaterialReview/MenorahV4/Meshes/SM_MenorahV4_StepStone'
NAMESPACE = '/Game/MikdashV3/CandidateStairCollisionV2'
CLONE = NAMESPACE + '/SM_MenorahV4_StepStone_Complex'


def disk(package):
    return ROOT/'Content'/(package[6:]+'.uasset')


def run(expected=None, verify=None):
    import unreal as u
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT / 'SourceAssets/lighting-review'
    folder.mkdir(parents=True, exist_ok=True)
    receipt = folder / ('candidate-stair-collision-' + stamp + '.json')
    mapfile = ROOT / 'Content' / (TARGET[6:] + '.umap')
    report = {'status':'started', 'map':TARGET, 'pid':os.getpid(), 'errors':[],
              'mapSaved':False, 'review':'Collision experiment only; native runtime/visual acceptance pending',
              'source':SOURCE, 'clone':CLONE}
    protected = {}
    before = sha(mapfile)
    report['mapSha256Before'] = before
    def write():
        receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    write()
    try:
        if bool(expected) == bool(verify):
            raise RuntimeError('Choose explicit expected-hash apply or fresh verify')
        inventory()
        if Path(u.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        earlier = json.loads(Path(verify).read_text(encoding='utf-8-sig')) if verify else None
        if earlier:
            if earlier.get('status') != 'saved_reopened' or earlier.get('map') != TARGET or earlier.get('pid') == os.getpid():
                raise RuntimeError('Invalid fresh verification receipt')
            if earlier.get('source') != SOURCE or earlier.get('clone') != CLONE:
                raise RuntimeError('Receipt scope differs')
            if check_hashes(earlier['protected']):
                raise RuntimeError('Protected content changed since apply')
            expected = earlier['mapSha256After']
        elif expected != EXPECTED:
            raise RuntimeError('Explicit hash must match reviewed candidate state')
        if not re.fullmatch('[0-9a-f]{64}', expected or '') or before != expected:
            raise RuntimeError('Map hash mismatch')
        editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)
        def clean():
            if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('PIE or dirty packages')
        clean()
        protected = {str(p):sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file() and p != mapfile}
        report['protected'] = protected
        if not levels.load_level(TARGET):
            raise RuntimeError('Load failed')
        clean()
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Wrong world')
        source_mesh = u.load_asset(SOURCE)
        if source_mesh is None: raise RuntimeError('StepStone source absent')
        report['sourceSha256'] = sha(disk(SOURCE))
        assets = u.EditorAssetLibrary
        if verify:
            if sha(disk(CLONE)) != earlier['cloneSha256']: raise RuntimeError('Clone changed since apply')
        elif assets.does_directory_exist(NAMESPACE) or disk(CLONE).parent.exists():
            raise RuntimeError('Create-once namespace already exists; do not overwrite')
        descriptor_class = u.load_class(None, '/Script/MikdashRuntime.MikdashSceneUnits')
        if descriptor_class is None:
            raise RuntimeError('Scene descriptor class absent')
        def validate_frame():
            descriptors = [a for a in actors.get_all_level_actors()
                           if u.MathLibrary.class_is_child_of(a.get_class(), descriptor_class)]
            if len(descriptors) != 1:
                raise RuntimeError('Exactly one scene descriptor class/subclass required')
            descriptor = descriptors[0]
            pivot = descriptor.get_editor_property('fixed_architecture_origin_cm')
            if descriptor.get_actor_label() != 'RELEASE_SceneUnits_Selected48_V1' or descriptor.get_outermost().get_name() != TARGET:
                raise RuntimeError('Descriptor label/ownership mismatch')
            if int(descriptor.get_editor_property('descriptor_schema_version')) != 1 or int(descriptor.get_editor_property('coordinate_revision').value) != 1 or str(descriptor.get_editor_property('scene_revision')) != 'Selected48.v1' or [pivot.x,pivot.y,pivot.z] != [-6200,0,0]:
                raise RuntimeError('Selected48 version/pivot mismatch')
            report['sceneFrame'] = {'schema':1, 'revision':'Selected48.v1', 'pivot':[-6200,0,0]}
        def discover():
            validate_frame()
            found = []
            for actor in actors.get_all_level_actors():
                for comp in actor.get_components_by_class(u.StaticMeshComponent):
                    mesh = comp.get_editor_property('static_mesh')
                    if mesh and mesh.get_path_name().split('.')[0] in (SOURCE,CLONE):
                        if actor.get_outermost().get_name() != TARGET: raise RuntimeError('Wrong owner')
                        found.append((actor,comp))
            if len(found) != 1: raise RuntimeError('Exactly one StepStone component required')
            return found
        def identity(found):
            return [[a.get_name(),c.get_name()] for a,c in found]
        def snapshot():
            aa = list(actors.get_all_level_actors())
            rows = [snapshot_row(u,a,TARGET) for a in aa]
            for row in rows:
                # snapshot_row uses _asset_path(), which returns package-only paths.
                row['meshes'] = [SOURCE if p == CLONE else p for p in row['meshes']]
            result = numeric_baseline_rows(rows, strict=True)
            for actor in aa:
                if actor.get_outermost().get_name() != TARGET:
                    continue
                for comp in actor.get_components_by_class(u.StaticMeshComponent):
                    mesh = comp.get_editor_property('static_mesh')
                    package = mesh.get_path_name().split('.')[0] if mesh else None
                    for slot in range(comp.get_num_materials()):
                        mat = comp.get_material(slot)
                        result['material:' + comp.get_path_name() + ':' + str(slot)] = mat.get_path_name() if mat else None
            return result
        found = discover()
        identities = identity(found)
        if earlier and earlier['components'] != identities:
            raise RuntimeError('Fresh component identity differs')
        report['components'] = identities
        baseline = snapshot()
        clean()
        if not levels.load_level(TARGET):
            raise RuntimeError('Pristine reload failed')
        clean()
        found = discover()
        if identity(found) != identities or snapshot() != baseline:
            raise RuntimeError('Pristine reload churn: review before mutation')
        if not verify:
            if found[0][1].get_editor_property('static_mesh') != source_mesh:
                raise RuntimeError('Original component binding required')
            checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('CandidateStairCollision-' + stamp)
            checkpoint.mkdir(parents=True, exist_ok=False)
            shutil.copy2(mapfile, checkpoint/mapfile.name)
            if sha(checkpoint/mapfile.name) != before:
                raise RuntimeError('Checkpoint hash mismatch')
            for name in ('__ExternalActors__','__ExternalObjects__'):
                source = ROOT/'Content'/name/TARGET[6:]
                if source.exists():
                    shutil.copytree(source, checkpoint/name/TARGET[6:])
            report['checkpoint'] = str(checkpoint)
            write()
            clone = assets.duplicate_asset(SOURCE,CLONE)
            if clone is None: raise RuntimeError('Duplicate failed')
            body = clone.get_editor_property('body_setup')
            if body is None: raise RuntimeError('Duplicated mesh has no BodySetup')
            if body == source_mesh.get_editor_property('body_setup') or body.get_outer() != clone:
                raise RuntimeError('Duplicate must own an independent BodySetup before mutation')
            body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            if body.get_editor_property('collision_trace_flag') != u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
                raise RuntimeError('Collision flag readback failed')
            # Existing project importer uses BodySetup setter + save_loaded_asset.
            # Fresh process and real traces still must verify physics cook behavior.
            if not assets.save_loaded_asset(clone,only_if_is_dirty=False): raise RuntimeError('Clone save failed')
            report['cloneSha256'] = sha(disk(CLONE))
            write()
            actor,comp = found[0]
            actor.modify(True); comp.modify(True)
            comp.set_static_mesh(clone)
            if comp.get_editor_property('static_mesh') != clone: raise RuntimeError('Binding failed')
            current_snapshot = snapshot()
            if current_snapshot != baseline or check_hashes(protected):
                changed = [k for k in sorted(set(baseline)|set(current_snapshot)) if baseline.get(k)!=current_snapshot.get(k)]
                report['snapshotDifferenceCountBeforeSave'] = len(changed)
                report['snapshotDifferencesBeforeSave'] = {k:{'before':baseline.get(k),'after':current_snapshot.get(k)}
                    for k in changed[:20]}
                write()
                raise RuntimeError('Unrelated state changed before save')
            if not levels.save_current_level():
                raise RuntimeError('Save refused')
            report['mapSaved'] = True
            report['mapSha256After'] = sha(mapfile)
            write()
            if not levels.load_level(TARGET):
                raise RuntimeError('Reopen failed')
        found = discover()
        if identity(found) != identities or snapshot() != baseline:
            raise RuntimeError('Unrelated state or component identity changed')
        clone = found[0][1].get_editor_property('static_mesh')
        if clone.get_path_name().split('.')[0] != CLONE: raise RuntimeError('Saved clone binding differs')
        saved_body = clone.get_editor_property('body_setup')
        if saved_body is None or saved_body == source_mesh.get_editor_property('body_setup') or saved_body.get_outer() != clone:
            raise RuntimeError('Saved BodySetup ownership differs')
        if clone.get_editor_property('body_setup').get_editor_property('collision_trace_flag') != u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
            raise RuntimeError('Saved collision flag differs')
        if clone.get_num_triangles(0) != source_mesh.get_num_triangles(0): raise RuntimeError('Triangle count differs')
        def material_signature(mesh):
            return [(str(v.get_editor_property('material_slot_name')),
                     v.get_editor_property('material_interface').get_path_name() if v.get_editor_property('material_interface') else None)
                    for v in mesh.get_editor_property('static_materials')]
        if material_signature(clone) != material_signature(source_mesh):
            raise RuntimeError('Render materials differ')
        report['cloneSha256'] = sha(disk(CLONE))
        clean()
        report['runtimeCollisionAcceptance'] = 'PENDING; saved flag is not a physics trace'
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
        print('Prepared helper only; no native execution')
    else:
        command = u.SystemLibrary.get_command_line()
        args = {x.split('=',1)[0].lower():x.split('=',1)[1].strip('"') for x in command.split() if '=' in x}
        try:
            run(expected=args.get('-candidatestaircollisionexpectedhash'), verify=args.get('-candidatestaircollisionverify'))
        finally:
            if '-executepythonscript' in command.lower() and '-run=pythonscript' not in command.lower():
                u.SystemLibrary.quit_editor()

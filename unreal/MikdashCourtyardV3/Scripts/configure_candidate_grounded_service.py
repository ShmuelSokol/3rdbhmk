"""Opt in one Candidate48 service to the compiled physical motor, startup OFF.

Apply: -GroundedServiceExpectedHash=<reviewed hash>
Fresh readback: -GroundedServiceVerify=<absolute apply receipt>
Only the authored top-tread stance X and movement mode may change. No route acceptance.
"""
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Scripts'))
from release_surface_soft import sha, inventory, check_hashes
from release_place_assets import snapshot_row, numeric_baseline_rows
from release_kohen_service import load_spec, _read_properties

TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
EXPECTED = '0d997af5802b99fbecfe77f09d94c52b6f62bb3f2900a9b6682b8025be0773cf'
LABEL = 'RELEASE_KohenGadolService_Selected48_V1'
TAG = 'ReleaseKohenServiceSelected48V1'
OLD_POINT = [-5239.0,315.176,975.0]
NEW_POINT = [-5269.09,315.176,975.0]


def run(expected=None, verify=None):
    import unreal as u
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT/'SourceAssets/service-review'/('candidate-grounded-config-'+stamp+'.json')
    mapfile = ROOT/'Content'/(TARGET[6:]+'.umap')
    before = sha(mapfile)
    report = {'status':'started','pid':os.getpid(),'map':TARGET,'mapSaved':False,
              'errors':[],'startupEnabled':False,'mapSha256Before':before,
              'scope':'Authored top-tread X and opt-in motor configuration only; native traversal pending.'}
    protected = {}
    def write():
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    write()
    try:
        if bool(expected)==bool(verify):
            raise RuntimeError('Choose explicit apply or fresh verification')
        inventory()
        if Path(u.Paths.project_dir()).resolve()!=ROOT:
            raise RuntimeError('Wrong project')
        earlier = json.loads(Path(verify).read_text(encoding='utf-8-sig')) if verify else None
        if earlier:
            if earlier.get('status')!='saved_reopened' or earlier.get('map')!=TARGET or earlier.get('pid')==os.getpid():
                raise RuntimeError('Invalid independent verification receipt')
            if check_hashes(earlier['protected']):
                raise RuntimeError('Protected content changed since apply')
            expected = earlier['mapSha256After']
        elif expected!=EXPECTED:
            raise RuntimeError('Apply requires the reviewed candidate hash')
        if before!=expected:
            raise RuntimeError('Map hash mismatch')
        cls = u.load_class(None,'/Script/MikdashRuntime.MikdashServiceActor')
        descriptor_cls = u.load_class(None,'/Script/MikdashRuntime.MikdashSceneUnits')
        if cls is None or descriptor_cls is None:
            raise RuntimeError('Compiled classes absent')
        default = u.get_default_object(cls)
        marker = getattr(default,'get_service_grounded_adapter_version',None)
        if marker is None or marker()!=1 or default.get_editor_property('use_grounded_movement'):
            raise RuntimeError('Compiled opt-in grounded adapter v1 required')
        editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)
        def clean():
            if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('PIE or dirty packages')
        clean()
        protected = {str(p):sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file() and p!=mapfile}
        report['protected'] = protected
        if not levels.load_level(TARGET):
            raise RuntimeError('Candidate load failed')
        clean()
        spec = load_spec()
        def point(actor):
            p = actor.get_editor_property('tending_stone_point')
            return [p.x,p.y,p.z]
        def near(a,b):
            return len(a)==len(b) and max(abs(x-y) for x,y in zip(a,b))<.001
        def discover():
            if editor.get_editor_world().get_outermost().get_name()!=TARGET:
                raise RuntimeError('Wrong world')
            aa = list(actors.get_all_level_actors())
            ds = [a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),descriptor_cls)]
            if len(ds)!=1:
                raise RuntimeError('Exactly one scene descriptor required')
            d=ds[0]; pivot=d.get_editor_property('fixed_architecture_origin_cm')
            if d.get_actor_label()!='RELEASE_SceneUnits_Selected48_V1' or d.get_outermost().get_name()!=TARGET or int(d.get_editor_property('descriptor_schema_version'))!=1 or int(d.get_editor_property('coordinate_revision').value)!=1 or str(d.get_editor_property('scene_revision'))!='Selected48.v1' or [pivot.x,pivot.y,pivot.z]!=[-6200,0,0]:
                raise RuntimeError('Selected48 frame mismatch')
            ss=[a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),cls)]
            owned=[a for a in aa if a.get_actor_label()==LABEL or TAG in [str(t) for t in a.tags]]
            if len(ss)!=1 or owned!=ss:
                raise RuntimeError('Exactly one owned service required')
            a=ss[0]
            if a.get_class()!=cls or a.get_outermost().get_name()!=TARGET or a.get_actor_label()!=LABEL or [str(t) for t in a.tags]!=[TAG]:
                raise RuntimeError('Service identity mismatch')
            if a.get_editor_property('start_on_begin_play') or a.get_editor_property('authored_body') or a.get_editor_property('service_scenario').name!='ORDINARY_DAY':
                raise RuntimeError('Requires startup-off ordinary-day spawned body')
            return a
        def snapshot():
            aa=list(actors.get_all_level_actors())
            result=numeric_baseline_rows([snapshot_row(u,a,TARGET) for a in aa],strict=True)
            service=discover()
            route=_read_properties(u,service,spec['actorProperties'])
            # Explicitly normalize ONLY the authorized new stance back to old X.
            if near(route['tending_stone_point'],NEW_POINT):
                route['tending_stone_point']=OLD_POINT
            result['serviceRoute']=route
            for key in ('configured_mesh','idle_animation','walk_animation','garment_material','configured_body_visual_scale','configured_body_yaw_degrees','garment_material_slots'):
                value=service.get_editor_property(key)
                result['serviceBody:'+key]=value.get_path_name() if hasattr(value,'get_path_name') else [str(v) for v in value] if key=='garment_material_slots' else value
            for a in aa:
                if a.get_outermost().get_name()!=TARGET: continue
                for c in a.get_components_by_class(u.StaticMeshComponent):
                    for i in range(c.get_num_materials()):
                        material=c.get_material(i)
                        result['material:'+c.get_path_name()+':'+str(i)]=material.get_path_name() if material else None
            return result
        actor=discover()
        if not verify and (actor.get_editor_property('use_grounded_movement') or not near(point(actor),OLD_POINT)):
            raise RuntimeError('Unexpected prior service configuration')
        baseline=snapshot(); actor_name=actor.get_name()
        if earlier and actor_name!=earlier['actorName']:
            raise RuntimeError('Fresh service identity changed')
        if not levels.load_level(TARGET): raise RuntimeError('Pristine reload failed')
        clean()
        pristine=snapshot()
        if pristine!=baseline:
            changed=[k for k in sorted(set(baseline)|set(pristine)) if baseline.get(k)!=pristine.get(k)]
            report['pristineDifferenceCount']=len(changed)
            report['pristineDifferences']={k:{'before':baseline.get(k),'after':pristine.get(k)} for k in changed[:20]}
            write()
            raise RuntimeError('Pristine snapshot churn')
        if not verify:
            checkpoint=ROOT.parent/'ReviewCheckpoints'/('CandidateGroundedService-'+stamp)
            checkpoint.mkdir(parents=True,exist_ok=False)
            shutil.copy2(mapfile,checkpoint/mapfile.name)
            if sha(checkpoint/mapfile.name)!=before: raise RuntimeError('Checkpoint mismatch')
            for name in ('__ExternalActors__','__ExternalObjects__'):
                source=ROOT/'Content'/name/TARGET[6:]
                if source.exists(): shutil.copytree(source,checkpoint/name/TARGET[6:])
            report['checkpoint']=str(checkpoint); write()
            actor=discover(); actor.modify(True)
            actor.set_editor_property('use_grounded_movement',True)
            actor.set_editor_property('tending_stone_point',u.Vector(*NEW_POINT))
            if snapshot()!=baseline or check_hashes(protected):
                raise RuntimeError('Unexpected change before save')
            if not levels.save_current_level(): raise RuntimeError('Map save refused')
            report['mapSaved']=True; report['mapSha256After']=sha(mapfile); write()
            if not levels.load_level(TARGET): raise RuntimeError('Reopen failed')
        actor=discover()
        if actor.get_name()!=actor_name or not actor.get_editor_property('use_grounded_movement') or not near(point(actor),NEW_POINT) or snapshot()!=baseline:
            raise RuntimeError('Saved configuration or unrelated state differs')
        clean()
        report.update(actorName=actor_name,legacyTendingStone=point(actor),status='fresh_verified' if verify else 'saved_reopened')
    except Exception as error:
        report['status']='failed'; report['errors'].append(repr(error)); raise
    finally:
        report['mapSha256After']=sha(mapfile)
        report['protectedDifferences']=check_hashes(protected)
        if report['protectedDifferences'] or (verify and report['mapSha256After']!=before):
            report['status']='failed_preservation'
        write()
    if report['status'].startswith('failed'): raise RuntimeError(report['status'])


if __name__=='__main__':
    try:
        import unreal as u
    except ImportError:
        print('Prepared helper only; compiled physical motor and native verification required')
    else:
        command=u.SystemLibrary.get_command_line()
        args={x.split('=',1)[0].lower():x.split('=',1)[1].strip('"') for x in command.split() if '=' in x}
        try:
            run(expected=args.get('-groundedserviceexpectedhash'),verify=args.get('-groundedserviceverify'))
        finally:
            if '-executepythonscript' in command.lower() and '-run=pythonscript' not in command.lower():
                u.SystemLibrary.quit_editor()

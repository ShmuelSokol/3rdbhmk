"""Candidate-only four existing photo material clones with persisted Nanite usage.
run(mode='dry-run'|'apply'|'verify', expected=..., verify_receipt=...).
No auto-run, original asset writes or photography copies. Fresh render/cook pending.
"""
import json
import os
import re
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from release_surface_soft import sha, inventory, check_hashes
from release_place_assets import snapshot_row, numeric_baseline_rows
from kotel_photo_pie_review import PHOTO, STONE, EDGES, _hashes, _state

TARGET='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
SCOPE='four_candidate_photo_nanite_material_clones'
NAMESPACE='/Game/MikdashV3/CandidateKotelPhotoCookV1'


def run(mode='dry-run',expected=None,verify_receipt=None):
    import unreal as u
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'SourceAssets/kotel-detail/KotelPhotoCook';out.mkdir(parents=True,exist_ok=True)
    receipt=out/('candidate-photo-cook-'+stamp+'.json')
    mapfile=ROOT/'Content'/(TARGET[6:]+'.umap')
    before=sha(mapfile);protected={}
    report={'status':'started','mode':mode,'pid':os.getpid(),'map':TARGET,'scope':SCOPE,
            'mapSha256Before':before,'mapSaved':False,'errors':[],
            'acceptance':'Nanite usage persistence only; fresh rendered appearance and actual cook remain pending'}
    def write():receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    def content():return {str(p):sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file() and p!=mapfile}
    try:
        if mode not in ('dry-run','apply','verify'):raise RuntimeError('Explicit supported mode required')
        earlier=None
        if mode=='verify':
            earlier=json.loads(Path(verify_receipt).read_text(encoding='utf-8-sig'))
            pid=earlier.get('pid')
            if (earlier.get('status')!='saved_reopened' or earlier.get('map')!=TARGET or earlier.get('scope')!=SCOPE
                    or type(pid) is not int or pid<=0 or pid==os.getpid() or earlier.get('mapSaved') is not True):
                raise RuntimeError('Successful distinct-process apply receipt required')
            expected=earlier['mapSha256After']
            current=content()
            if check_hashes(earlier['protected']) or set(current)!=set(earlier['protected'])|set(earlier['cloneHashes']):raise RuntimeError('Protected inventory changed since apply')
            if any(current[p]!=h for p,h in earlier['cloneHashes'].items()):raise RuntimeError('Saved clone bytes changed')
        elif not re.fullmatch('[0-9a-f]{64}',expected or '') or verify_receipt:
            raise RuntimeError('Explicit reviewed candidate hash required')
        if before!=expected:raise RuntimeError('Candidate map hash differs')
        report['sourceAssetHashes']=_hashes()
        if earlier and report['sourceAssetHashes']!=earlier['sourceAssetHashes']:raise RuntimeError('Photo source hashes changed')
        inventory()
        if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
        ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
        actors=u.get_editor_subsystem(u.EditorActorSubsystem)
        def clean():
            if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('Dirty packages or PIE present')
        clean();protected=content();report['protected']=protected
        if mode!='verify' and (u.EditorAssetLibrary.does_directory_exist(NAMESPACE) or (ROOT/'Content'/NAMESPACE[6:]).exists()):raise RuntimeError('Create-once namespace already exists')
        if not levels.load_level(TARGET):raise RuntimeError('Candidate load failed')
        clean()
        def path(obj):return obj.get_path_name().split('.')[0] if obj else None
        def discover():
            if ed.get_editor_world().get_outermost().get_name()!=TARGET:raise RuntimeError('Wrong world')
            aa=list(actors.get_all_level_actors())
            cls=u.load_class(None,'/Script/MikdashRuntime.MikdashSceneUnits')
            if cls is None:raise RuntimeError('Missing descriptor class')
            dd=[a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),cls)]
            if len(dd)!=1:raise RuntimeError('Exactly one scene descriptor required')
            d=dd[0];p=d.get_editor_property('fixed_architecture_origin_cm')
            if (d.get_actor_label()!='RELEASE_SceneUnits_Selected48_V1' or d.get_outermost().get_name()!=TARGET
                    or int(d.get_editor_property('descriptor_schema_version'))!=1
                    or int(d.get_editor_property('coordinate_revision').value)!=1
                    or str(d.get_editor_property('scene_revision'))!='Selected48.v1' or [p.x,p.y,p.z]!=[-6200,0,0]):
                raise RuntimeError('Selected48 descriptor identity/version/pivot differs')
            found={}
            for edge in EDGES:
                mesh=STONE+'/Meshes/SM_KotelAshlarV2_E'+str(edge)
                hits=[(a,c) for a in aa for c in a.get_components_by_class(u.StaticMeshComponent) if path(c.get_editor_property('static_mesh'))==mesh]
                if len(hits)!=1:raise RuntimeError('Exactly one component required: '+mesh)
                a,c=hits[0];p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
                if (a.get_outermost().get_name()!=TARGET or a.get_actor_label()!='RELEASE_KotelStoneV2_E'+str(edge)
                        or c.get_num_materials()!=1 or [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]!=[0,0,0,0,0,0,1,1,1]):
                    raise RuntimeError('Component ownership/pose/slot identity differs')
                found[edge]=(a,c)
            return found
        def identities(found):return {str(k):[a.get_name(),c.get_name()] for k,(a,c) in found.items()}
        def snapshot(found):
            aa=list(actors.get_all_level_actors());target_paths={c.get_path_name() for a,c in found.values()}
            result=numeric_baseline_rows([snapshot_row(u,a,TARGET) for a in aa],strict=True)
            for a in aa:
                if a.get_outermost().get_name()!=TARGET:continue
                for c in a.get_components_by_class(u.StaticMeshComponent):
                    if c.get_path_name() in target_paths:continue
                    for i in range(c.get_num_materials()):
                        m=c.get_material(i);result['material:'+c.get_path_name()+':'+str(i)]=m.get_path_name() if m else None
            for k,(a,c) in found.items():
                result['targetState:'+str(k)]=_state(a,c)
                # Exactly one effective slot is allowed to change. Refuse hidden
                # trailing override slots, which a slot-zero edit must not erase.
                overrides=list(c.get_editor_property('override_materials'))
                if len(overrides)>1:raise RuntimeError('Unexpected target override slots')
            return json.loads(json.dumps(result))
        found=discover();ids=identities(found);baseline=snapshot(found)
        if earlier and (ids!=earlier['components'] or baseline!=earlier['baseline']):raise RuntimeError('Persisted unrelated baseline differs')
        report['components']=ids;report['baseline']=baseline
        if not levels.load_level(TARGET):raise RuntimeError('Pristine reload failed')
        clean();found=discover()
        if identities(found)!=ids or snapshot(found)!=baseline:raise RuntimeError('Pristine reload churn; no mutation allowed')
        sources={k:u.load_asset(PHOTO+'/M_PhotoFace_'+str(k)) for k in EDGES}
        def textures(material):
            if not isinstance(material,u.Material):raise RuntimeError('Expected base material')
            values=sorted(path(t) for t in u.MaterialEditingLibrary.get_used_textures(material))
            report.setdefault('usedTextureReadbacks',{})[path(material)]=values
            # NullRHI receipt094847 returns [] from the compiled-resource query.
            # Read authored expressions instead; never treat [] as texture proof.
            ml=u.MaterialEditingLibrary;nodes=list(ml.get_material_expressions(material))
            expected_classes={'MaterialExpressionWorldPosition','MaterialExpressionCustom',
                              'MaterialExpressionTextureSample','MaterialExpressionConstant'}
            if len(nodes)!=4 or {n.get_class().get_name() for n in nodes}!=expected_classes:
                raise RuntimeError('Unexpected photo graph; nested/function textures are not allowed')
            graph={}
            for node in nodes:
                kind=node.get_class().get_name()
                row={'inputs':[n.get_class().get_name() if n else None for n in ml.get_inputs_for_material_expression(material,node)]}
                if isinstance(node,u.MaterialExpressionTextureSample):
                    texture=node.get_editor_property('texture');row['texture']=path(texture)
                    if row['texture']!=PHOTO+'/T_KotelWallPhoto':raise RuntimeError('Authored photo texture differs')
                    row['samplerType']=str(node.get_editor_property('sampler_type'))
                if isinstance(node,u.MaterialExpressionCustom):row['code']=str(node.get_editor_property('code'))
                if isinstance(node,u.MaterialExpressionConstant):row['r']=float(node.get_editor_property('r'))
                graph[kind]=row
            if 'MaterialExpressionCustom' not in graph['MaterialExpressionTextureSample']['inputs'] or graph['MaterialExpressionCustom']['inputs']!=['MaterialExpressionWorldPosition']:
                raise RuntimeError('Photo projection graph links differ')
            if abs(graph['MaterialExpressionConstant']['r']-.86)>1e-6:raise RuntimeError('Photo roughness differs')
            report.setdefault('authoredGraphReadbacks',{})[path(material)]=graph
            return graph
        source_graphs={k:textures(source) for k,source in sources.items()}
        mats={k:u.load_asset(NAMESPACE+'/M_PhotoFace_'+str(k)) for k in EDGES} if earlier else sources
        if any(not isinstance(m,u.MaterialInterface) for m in mats.values()):raise RuntimeError('Missing photo material')
        for k,(a,c) in found.items():
            wanted=(NAMESPACE if earlier else PHOTO)+'/M_PhotoFace_'+str(k)
            if path(c.get_material(0))!=wanted:raise RuntimeError('Unexpected current material')
        clean()
        if mode=='apply':
            checkpoint=ROOT.parent/'ReviewCheckpoints'/('CandidateKotelPhotoCook-'+stamp)
            checkpoint.mkdir(parents=True,exist_ok=False);shutil.copy2(mapfile,checkpoint/mapfile.name)
            if sha(checkpoint/mapfile.name)!=before:raise RuntimeError('Checkpoint mismatch')
            for name in ('__ExternalActors__','__ExternalObjects__'):
                source=ROOT/'Content'/name/TARGET[6:]
                if source.exists():shutil.copytree(source,checkpoint/name/TARGET[6:])
            report['checkpoint']=str(checkpoint);write()
            mats={}
            for k in EDGES:
                source=sources[k]
                if not isinstance(source,u.Material):raise RuntimeError('Expected source base material')
                clone=u.EditorAssetLibrary.duplicate_asset(PHOTO+'/M_PhotoFace_'+str(k),NAMESPACE+'/M_PhotoFace_'+str(k))
                if not isinstance(clone,u.Material) or clone==source:raise RuntimeError('Independent material clone failed')
                u.MaterialEditingLibrary.set_base_material_usage(clone,u.MaterialUsage.MATUSAGE_NANITE,True)
                compile_errors=list(u.MaterialEditingLibrary.recompile_material(clone))
                if compile_errors:raise RuntimeError('Material compiler errors: '+repr(compile_errors))
                if textures(clone)!=source_graphs[k]:raise RuntimeError('Cloned photo graph differs from exact source')
                if not u.MaterialEditingLibrary.has_material_usage(clone,u.MaterialUsage.MATUSAGE_NANITE):raise RuntimeError('Nanite usage readback false')
                if not u.EditorAssetLibrary.save_loaded_asset(clone,only_if_is_dirty=False):raise RuntimeError('Clone save failed')
                mats[k]=clone
            report['cloneHashes']={str(ROOT/'Content'/(NAMESPACE[6:]+'/M_PhotoFace_'+str(k)+'.uasset')):sha(ROOT/'Content'/(NAMESPACE[6:]+'/M_PhotoFace_'+str(k)+'.uasset')) for k in EDGES}
            write()
            for k,(a,c) in found.items():
                a.modify(True);c.modify(True);c.set_material(0,mats[k])
                if c.get_material(0)!=mats[k]:raise RuntimeError('Immediate readback failed')
            if snapshot(found)!=baseline or check_hashes(protected) or set(content())!=set(protected)|set(report['cloneHashes']):raise RuntimeError('Unrelated state changed before save')
            if not levels.save_current_level():raise RuntimeError('Save refused')
            report['mapSaved']=True;report['mapSha256After']=sha(mapfile);write()
            if not levels.load_level(TARGET):raise RuntimeError('Saved reopen failed')
            found=discover()
        if identities(found)!=ids or snapshot(found)!=baseline:raise RuntimeError('Unrelated persisted state differs')
        if mode!='dry-run' and any(c.get_material(0)!=mats[k] for k,(a,c) in found.items()):raise RuntimeError('Saved material readback failed')
        if mode!='dry-run':
            for k,material in mats.items():
                if not u.MaterialEditingLibrary.has_material_usage(material,u.MaterialUsage.MATUSAGE_NANITE):raise RuntimeError('Saved Nanite usage differs')
                if textures(material)!=source_graphs[k]:raise RuntimeError('Saved clone photo graph differs')
            if earlier:report['cloneHashes']=earlier['cloneHashes']
        clean();_hashes()
        report['verifiedSlots']=4;report['status']={'dry-run':'dry_run_passed','apply':'saved_reopened','verify':'fresh_verified'}[mode]
    except Exception as exc:
        report['status']='failed';report['errors'].append(repr(exc));raise
    finally:
        report['mapSha256After']=sha(mapfile)
        report['protectedDifferences']=check_hashes(protected)
        report['newContentFiles']=sorted(set(content())-set(protected)-{str(ROOT/'Content'/(NAMESPACE[6:]+'/M_PhotoFace_'+str(k)+'.uasset')) for k in EDGES}) if protected else []
        if report['protectedDifferences'] or report['newContentFiles'] or (mode!='apply' and sha(mapfile)!=before):report['status']='failed_preservation'
        write()
    if report['status'].startswith('failed'):raise RuntimeError(report['status'])
    return report


if __name__=='__main__':
    try:import unreal as u
    except ImportError:
        print('Prepared only. Native flags: -PhotoCookApply OR -PhotoCookDryRun with -PhotoCookExpectedHash=<SHA>; fresh -PhotoCookVerify="<receipt>"')
    else:
        command=u.SystemLibrary.get_command_line()
        def arg(key):
            found=re.search(r'(?:^|\s)'+re.escape(key)+r'=(?:"([^"]+)"|(\S+))',command,re.I)
            return (found.group(1) or found.group(2)) if found else None
        verify=arg('-PhotoCookVerify')
        modes=[bool(re.search(r'(?:^|\s)-PhotoCookApply(?:\s|$)',command,re.I)),
               bool(re.search(r'(?:^|\s)-PhotoCookDryRun(?:\s|$)',command,re.I)),bool(verify)]
        try:
            if sum(modes)!=1:raise RuntimeError('Choose one explicit photo cook mode')
            run(mode='verify' if verify else ('apply' if modes[0] else 'dry-run'),expected=arg('-PhotoCookExpectedHash'),verify_receipt=verify)
        finally:
            if '-executepythonscript' in command.lower() and '-run=pythonscript' not in command.lower():u.SystemLibrary.quit_editor()

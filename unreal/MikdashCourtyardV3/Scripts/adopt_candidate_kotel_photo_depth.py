"""Prepared candidate-only four-slot adoption. Never launches Unreal or auto-adopts.
run(mode='dry-run'|'apply'|'verify', expected=..., ab_receipt=...,
    acceptance_receipt=..., verify_receipt=...) is the native entry point.
Root must author the separate visual acceptance only after inspecting both images.
"""
import json
import os
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from release_surface_soft import sha, inventory, check_hashes
from release_place_assets import snapshot_row, numeric_baseline_rows
from kotel_photo_pie_review import PHOTO, STONE, ORIGINAL, EDGES, _hashes, _state

TARGET='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
EXPECTED='cd3348ec8c0cf6f40291a5f85e338207d22c7d770a7855be0dd443d88964d1a7'
SCOPE='four_candidate_v2_material_slots'
VARIANT='kotel_photo_on_stone'


def evidence(ab_path,acceptance_path):
    """Read-only fail-closed evidence contract, usable offline before native work."""
    ab_path=Path(ab_path); acceptance_path=Path(acceptance_path)
    ab=json.loads(ab_path.read_text(encoding='utf-8-sig'))
    accepted=json.loads(acceptance_path.read_text(encoding='utf-8-sig'))
    if (ab.get('status')!='captured_pie_ab_requires_visual_review' or ab.get('map')!=TARGET
            or ab.get('mapShaBefore')!=EXPECTED or ab.get('errors')!=[] or ab.get('failures')!=[]
            or any(ab.get(k) is not True for k in ('allMapsUnchanged','mapBytesUnchanged','originalSavesUnchanged'))):
        raise RuntimeError('Final successful preserved candidate A/B receipt required')
    applied=[x for x in ab.get('variantsApplied',[]) if x.get('variant')==VARIANT]
    hashes=_hashes()
    if len(applied)!=1 or applied[0].get('photoTrial',{}).get('slots')!=4 or applied[0]['photoTrial'].get('assetHashes')!=hashes:
        raise RuntimeError('Exactly four pinned photo assignments required')
    restored=ab.get('kotelPhotoRestore',{})
    if restored.get('status')!='original_pie_material_arrays_restored' or restored.get('slots')!=4:
        raise RuntimeError('A/B restoration not verified')
    if (accepted.get('status')!='accepted_candidate_kotel_photo_depth'
            or accepted.get('abReceiptSha256')!=sha(ab_path)
            or accepted.get('candidateMapSha256')!=EXPECTED
            or accepted.get('scope')!=SCOPE or accepted.get('acceptedVariant')!=VARIANT
            or not isinstance(accepted.get('limitations'),list) or not accepted['limitations']):
        raise RuntimeError('Separate explicit visual acceptance contract differs')
    reviewed=accepted.get('reviewedImages')
    if not isinstance(reviewed,list) or len(reviewed)<2:raise RuntimeError('Reviewed baseline and trial images required')
    variants=set()
    for image in reviewed:
        path=Path(image['path'])
        if not path.is_absolute() or sha(path)!=image['sha256']:raise RuntimeError('Reviewed image bytes differ')
        captures=[c for c in ab.get('captures',[]) if c.get('sha256')==image['sha256']]
        if len(captures)!=1:raise RuntimeError('Reviewed image absent/ambiguous in A/B captures')
        variants.add(captures[0]['variant'])
    if not {'baseline',VARIANT}.issubset(variants):raise RuntimeError('Both A/B variants must be reviewed')
    return {'abReceipt':str(ab_path.resolve()),'abReceiptSha256':sha(ab_path),
            'acceptanceReceipt':str(acceptance_path.resolve()),'acceptanceReceiptSha256':sha(acceptance_path),
            'photoAssetHashes':hashes,'limitations':accepted['limitations'],'reviewedImages':reviewed}


def run(mode='dry-run',expected=None,ab_receipt=None,acceptance_receipt=None,verify_receipt=None):
    import unreal as u
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'SourceAssets/kotel-detail/KotelPhotoDepthAdoption';out.mkdir(parents=True,exist_ok=True)
    receipt=out/('candidate-photo-depth-'+stamp+'.json')
    mapfile=ROOT/'Content'/(TARGET[6:]+'.umap')
    before=sha(mapfile);protected={}
    report={'status':'started','mode':mode,'pid':os.getpid(),'map':TARGET,'scope':SCOPE,
            'mapSha256Before':before,'mapSaved':False,'errors':[]}
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
            ab_receipt=earlier['evidence']['abReceipt'];acceptance_receipt=earlier['evidence']['acceptanceReceipt']
            if content()!=earlier['protected']:raise RuntimeError('Protected content changed since apply')
        elif expected!=EXPECTED or verify_receipt:
            raise RuntimeError('Explicit reviewed candidate hash required')
        if before!=expected:raise RuntimeError('Candidate map hash differs')
        report['evidence']=evidence(ab_receipt,acceptance_receipt)
        if earlier and report['evidence']!=earlier['evidence']:raise RuntimeError('Evidence changed since apply')
        inventory()
        if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
        ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
        actors=u.get_editor_subsystem(u.EditorActorSubsystem)
        def clean():
            if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('Dirty packages or PIE present')
        clean();protected=content();report['protected']=protected
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
        mats={k:u.load_asset(PHOTO+'/M_PhotoFace_'+str(k)) for k in EDGES}
        if any(not isinstance(m,u.MaterialInterface) for m in mats.values()):raise RuntimeError('Missing photo material')
        for k,(a,c) in found.items():
            wanted=PHOTO+'/M_PhotoFace_'+str(k) if earlier else ORIGINAL
            if path(c.get_material(0))!=wanted:raise RuntimeError('Unexpected current material')
        clean()
        if mode=='apply':
            checkpoint=ROOT.parent/'ReviewCheckpoints'/('CandidateKotelPhotoDepth-'+stamp)
            checkpoint.mkdir(parents=True,exist_ok=False);shutil.copy2(mapfile,checkpoint/mapfile.name)
            if sha(checkpoint/mapfile.name)!=before:raise RuntimeError('Checkpoint mismatch')
            for name in ('__ExternalActors__','__ExternalObjects__'):
                source=ROOT/'Content'/name/TARGET[6:]
                if source.exists():shutil.copytree(source,checkpoint/name/TARGET[6:])
            report['checkpoint']=str(checkpoint);write()
            for k,(a,c) in found.items():
                a.modify(True);c.modify(True);c.set_material(0,mats[k])
                if c.get_material(0)!=mats[k]:raise RuntimeError('Immediate readback failed')
            if snapshot(found)!=baseline or content()!=protected:raise RuntimeError('Unrelated state changed before save')
            if not levels.save_current_level():raise RuntimeError('Save refused')
            report['mapSaved']=True;report['mapSha256After']=sha(mapfile);write()
            if not levels.load_level(TARGET):raise RuntimeError('Saved reopen failed')
            found=discover()
        if identities(found)!=ids or snapshot(found)!=baseline:raise RuntimeError('Unrelated persisted state differs')
        if mode!='dry-run' and any(c.get_material(0)!=mats[k] for k,(a,c) in found.items()):raise RuntimeError('Saved material readback failed')
        clean();_hashes()
        report['verifiedSlots']=4;report['status']={'dry-run':'dry_run_passed','apply':'saved_reopened','verify':'fresh_verified'}[mode]
    except Exception as exc:
        report['status']='failed';report['errors'].append(repr(exc));raise
    finally:
        report['mapSha256After']=sha(mapfile)
        report['protectedDifferences']=check_hashes(protected)
        report['newContentFiles']=sorted(set(content())-set(protected)) if protected else []
        if report['protectedDifferences'] or report['newContentFiles'] or (mode!='apply' and sha(mapfile)!=before):report['status']='failed_preservation'
        write()
    if report['status'].startswith('failed'):raise RuntimeError(report['status'])
    return report

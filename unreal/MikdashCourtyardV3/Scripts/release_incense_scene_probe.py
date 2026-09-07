"""Dedicated full-editor transient diagnostic. begin() is dry-run; stop() always available.
No map saves, scheduled-service claim, or automatic editor shutdown.
"""
import hashlib
import json
import math
import time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
MAP='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
SYSTEM='/Game/MikdashV3/MaterialReview/IncenseSmokeV4/NS_FiniteIncenseStudy'
_active=None


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def source_hearth():
    folder=ROOT/'SourceAssets/vessels-review/IncenseAltarV2'
    manifest=json.loads((folder/'geometry-manifest.json').read_text())
    record=next(m for m in manifest['meshes'] if m['name']=='SM_IncenseAltarV2_Body')
    obj=folder/record['file']
    if digest(obj)!=record['sha256']:raise RuntimeError('Altar OBJ hash differs')
    vertices=[];heights=[]
    for line in obj.read_text().splitlines():
        words=line.split()
        if not words:continue
        if words[0]=='v':vertices.append(tuple(map(float,words[1:4])))
        if words[0]!='f':continue
        if len(words)!=4:raise RuntimeError('Expected triangular source faces')
        a,b,c=[vertices[int(w.split('/')[0])-1] for w in words[1:]]
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-10:continue
        u=((b[1]-c[1])*(-c[0])+(c[0]-b[0])*(-c[1]))/den
        v=((c[1]-a[1])*(-c[0])+(a[0]-c[0])*(-c[1]))/den;w=1-u-v
        if min(u,v,w)>=-1e-8:heights.append(u*a[2]+v*b[2]+w*c[2])
    z=max(heights)
    if abs(z-77.5)>.001 or z>=manifest['height_to_horn_tops_cm']:raise RuntimeError('Central source hearth no longer matches reviewed geometry')
    return z,record


def stop(reason='manual_stop'):
    global _active
    if not _active:return
    import unreal as ue
    state=_active;_active=None
    try:
        if state.get('callback') is not None:ue.unregister_slate_post_tick_callback(state['callback'])
        if state.get('actor'):
            state['component'].deactivate()
            if not ue.get_editor_subsystem(ue.EditorActorSubsystem).destroy_actor(state['actor']):raise RuntimeError('Transient actor cleanup failed')
        state['receipt']['status']=reason
    except Exception as exc:state['receipt'].update(status='cleanup_failed',error=repr(exc))
    finally:
        state['receipt']['map_sha_after']=digest(state['mapfile'])
        state['receipt']['map_bytes_unchanged']=state['receipt']['map_sha_after']==state['receipt']['map_sha_before']
        if not state['receipt']['map_bytes_unchanged']:state['receipt']['status']='failed_map_bytes_changed'
        state['path'].write_text(json.dumps(state['receipt'],indent=2)+'\n')


def begin(activate=False, approval_receipt=None):
    """Activation additionally requires explicit validated visual/lifetime approval JSON.
    Schema: status=approved_for_transient_scene_probe, system=SYSTEM,
    system_sha256=<uasset hash>, authoring_sha256=<native-authoring receipt hash>,
    visual_review_passed=true, finite_lifetime_verified=true.
    This is an integration gate, not a fabricated acceptance artifact.
    """
    global _active
    import unreal as ue
    if _active:raise RuntimeError('A probe is already active')
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem);world=editor.get_editor_world()
    if Path(ue.Paths.project_dir()).resolve()!=ROOT or editor.get_game_world() or world.get_outermost().get_name()!=MAP:raise RuntimeError('Load intended saved map in dedicated editor outside gameplay')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Resolve dirty work before diagnostic')
    folder=ROOT/'SourceAssets/IncenseRepairV4';folder.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');path=folder/('scene-probe-'+stamp+'.json')
    mapfile=ROOT/'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap'
    receipt=dict(status='diagnostic_started',map=MAP,map_sha_before=digest(mapfile),activation_requested=activate,scheduled_service=False,notes=['No map save; source geometry contact rather than unreliable editor trace','Numbers describe artistic geometry and VFX, not ritual service duration'],samples=[])
    state=dict(path=path,receipt=receipt,mapfile=mapfile);_active=state
    try:
        actors=ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
        found=[a for a in actors if a.get_actor_label()=='RELEASE_IncenseAltar_Body']
        if len(found)!=1:raise RuntimeError('Expected one saved RELEASE altar')
        actor=found[0];component=actor.get_component_by_class(ue.StaticMeshComponent);mesh=component.get_editor_property('static_mesh')
        if mesh.get_path_name().split('.')[0]!='/Game/MikdashV3/MaterialReview/IncenseAltarV2/Meshes/SM_IncenseAltarV2_Body':raise RuntimeError('Altar mesh differs')
        loc=component.get_world_location();rot=component.get_world_rotation();scale=component.get_world_scale()
        if max(abs(rot.pitch),abs(rot.yaw),abs(rot.roll),abs(scale.x-1),abs(scale.y-1),abs(scale.z-1))>.001:raise RuntimeError('Recalibrate nonidentity altar rotation/scale')
        z,record=source_hearth();b=mesh.get_bounding_box()
        actual={'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]}
        if max(abs(actual[k][i]-record['bounds_cm'][k][i]) for k in actual for i in range(3))>.05 or mesh.get_num_triangles(0)!=record['triangles']:raise RuntimeError('Altar native geometry differs')
        manifest=json.loads((ROOT/'SourceAssets/architecture-manifest.json').read_text(encoding='utf-8-sig'))
        roof=next(m for m in manifest['meshes'] if m['sourceName']=='Sanctuary ceiling');roofpath='/Game/MikdashV3/Architecture/architecture_'+roof['assetName'];ceilings=[]
        for a in actors:
            for c in a.get_components_by_class(ue.StaticMeshComponent):
                m=c.get_editor_property('static_mesh')
                if m and m.get_path_name().split('.')[0]==roofpath:
                    q=c.get_world_location();t=c.get_world_rotation();v=c.get_world_scale()
                    if max(abs(q.x),abs(q.y),abs(q.z),abs(t.pitch),abs(t.yaw),abs(t.roll),abs(v.x-1),abs(v.y-1),abs(v.z-1))>.001:raise RuntimeError('Ceiling transform changed')
                    bb=m.get_bounding_box();expected=roof['expectedBoundsUnrealCm']
                    if max(abs(x-y) for x,y in zip([bb.min.x,bb.min.y,bb.min.z,bb.max.x,bb.max.y,bb.max.z],expected['min']+expected['max']))>.05:raise RuntimeError('Ceiling source/native bounds differ')
                    if bb.min.x<loc.x<bb.max.x and bb.min.y<loc.y<bb.max.y:ceilings.append(bb.min.z)
        if len(ceilings)!=1:raise RuntimeError('Expected unique source ceiling above altar')
        origin=[loc.x,loc.y,loc.z+z+.5];clearance=ceilings[0]-origin[2]
        receipt.update(altar_origin_cm=[loc.x,loc.y,loc.z],hearth_local_z_cm=z,artistic_spawn_offset_cm=.5,spawn_cm=origin,ceiling_underside_cm=ceilings[0],rise_clearance_cm=clearance)
        assetfile=ROOT/('Content/'+SYSTEM[6:]+'.uasset');authoring=ROOT/'SourceAssets/vessels-review/IncenseRepairV4/native-authoring.json'
        missing=[str(p) for p in (assetfile,authoring) if not p.exists()];receipt['missing_assets_or_evidence']=missing
        if missing:stop('dry_run_missing_v4_assets_or_authoring');return receipt
        authored=json.loads(authoring.read_text());params=authored['design_parameters'];receipt['vfx_parameters']=params
        if abs(params['ceiling_height_cm']-clearance)>1:stop('dry_run_vfx_ceiling_mismatch_reauthor_required');return receipt
        if not activate:stop('dry_run_calibrated_no_activation');return receipt
        if not approval_receipt:raise RuntimeError('Visual and finite-lifetime approval receipt required')
        approval=json.loads(Path(approval_receipt).read_text())
        if approval.get('status')!='approved_for_transient_scene_probe' or approval.get('system')!=SYSTEM or approval.get('system_sha256')!=digest(assetfile) or approval.get('authoring_sha256')!=digest(authoring) or approval.get('visual_review_passed') is not True or approval.get('finite_lifetime_verified') is not True:raise RuntimeError('Approval evidence missing or stale')
        duration=sum(params[k] for k in ('emission_seconds','rise_seconds','spread_seconds'))
        if not math.isfinite(duration) or not 0<duration<=20:raise RuntimeError('Diagnostic duration outside bounded20s limit')
        system=ue.load_asset(SYSTEM)
        if not isinstance(system,ue.NiagaraSystem):raise RuntimeError('Niagara system load failed')
        api=ue.get_editor_subsystem(ue.EditorActorSubsystem)
        transient=api.spawn_actor_from_class(ue.NiagaraActor,ue.Vector(*origin),ue.Rotator(pitch=0,yaw=0,roll=0),transient=True)
        if not transient:raise RuntimeError('Transient actor spawn failed')
        state['actor']=transient;comp=transient.get_component_by_class(ue.NiagaraComponent);state['component']=comp
        comp.deactivate();comp.set_editor_property('auto_activate',False);comp.set_asset(system);comp.set_force_solo(True)
        state.update(start=time.monotonic(),activated=None,last_sample=-1,duration=duration)
        def tick(delta):
            try:
                elapsed=time.monotonic()-state['start']
                if elapsed>40:stop('timeout_stopped_not_completion_proof');return
                if state['activated'] is None:
                    if elapsed<10:return
                    comp.activate(True);state['activated']=time.monotonic();receipt['activation_count']=1
                age=time.monotonic()-state['activated']
                if int(age)>state['last_sample']:
                    state['last_sample']=int(age);receipt['samples'].append(dict(wall_age_seconds=age,active=comp.is_active()));path.write_text(json.dumps(receipt,indent=2)+'\n')
                if age>duration+2:stop('bounded_preview_stopped_completion_not_proven')
            except Exception as exc:receipt['error']=repr(exc);stop('probe_failed')
        state['callback']=ue.register_slate_post_tick_callback(tick);receipt['status']='transient_preview_waiting_readiness';path.write_text(json.dumps(receipt,indent=2)+'\n');return receipt
    except Exception as exc:
        receipt['error']=repr(exc);stop('diagnostic_failed');raise

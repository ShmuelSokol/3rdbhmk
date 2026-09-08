"""Candidate-only calibrated menorah/Aron migration with physical pole dimensions retained."""
import hashlib
import importlib.util
import json
import shutil
import math
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REVIEW=ROOT/'SourceAssets/scale-review'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name):
    s=importlib.util.spec_from_file_location('am48_'+name,ROOT/'Scripts'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def offline_plan():
    inventory_path=REVIEW/'native-scale-inventory-20260908T133142315573Z.json'
    inventory=json.loads(inventory_path.read_text())
    manifest_path=ROOT/'SourceAssets/vessels-review/MenorahV4/geometry-manifest.json'
    manifest=json.loads(manifest_path.read_text());radius=manifest['parameters']['tier_lower_R']
    if manifest['amah_cm']!=50 or manifest['parameters']['total_height']!=150:raise RuntimeError('Menorah calibration changed')
    prefixes=['/Game/MikdashV3/MaterialReview/MenorahV4/Meshes/SM_MenorahV4_'+s for s in ('Base','Shaft','BranchesL','BranchesR','Ornaments','Lamps','StepStone')]
    aron=['/Game/MikdashV3/ThirdParty/Vessels/Meshes/SM_ThirdParty_AronBody_davidgra11_NoPoles',
          '/Game/MikdashV3/ThirdParty/Vessels/Meshes/SM_ThirdParty_AronLid_davidgra11',
          '/Game/MikdashV3/MaterialReview/AronStudyV3/Meshes/SM_AronPolesEW']
    proposals=[]
    for a in inventory['actors']:
        meshes=[c.get('mesh','').split('.')[0] for c in a['components']]
        if len(meshes)!=1 or meshes[0] not in prefixes+aron:continue
        mesh=meshes[0];p=a['locationCm'];scale=a['scale'];rotation=a['rotationDegrees']
        if mesh in prefixes:
            if abs(p[2]-925)>.001 or scale!=[1,1,1]:raise RuntimeError('Menorah support/scale drift')
            location=[p[0]*.96,p[1]*.96,888+p[2]-925];newscale=[.96]*3
            policy='18tefach overall150→144; photo proportions follow calibrated book height'
            if mesh.endswith('_StepStone'):
                newscale=[1,1,.96];yaw=math.radians(rotation[1]);delta=-.04*radius
                location[0]+=-math.sin(yaw)*delta;location[1]+=math.cos(yaw)*delta
                policy='Keep90cm width,30cm treads,12cm corners,10cm gap; scale2tefach risers only; shift localY by plinth-radius change'
        else:
            location=[p[0]*.96,p[1]*.96,888+(p[2]-925)*.96];newscale=[s*.96 for s in scale]
            policy='Original import spec explicitly says scale1.471 incorporates book-size fit; body/lid dimensions and relative lid height scale .96'
            if mesh.endswith('/SM_AronPolesEW'):
                newscale=scale
                location[1]=math.copysign((abs(p[1])-4.5)*.96+4.5,p[1])
                policy='Ring height/body-side offset follow resized body; retain radius4cm and gap.5cm, full authored pole geometry unchanged; tip-to-curtain fit remains pending'
        proposals.append(dict(name=a['name'],label=a['label'],mesh=mesh,oldPose=p+rotation+scale,location48=location,scale48=newscale,policy=policy))
    if len(proposals)!=11 or sum(p['mesh'] in prefixes for p in proposals)!=7:raise RuntimeError('Incomplete assembly')
    return dict(status='ARON_SUPPORT_MENORAH_CALIBRATION_PLAN',proposals=proposals,inventorySha256=sha(inventory_path),manifestSha256=sha(manifest_path),
        thirdPartySpecSha256=sha(ROOT/'Scripts/release_import_thirdparty_vessels.spec.json'),poleSpecSha256=sha(ROOT/'Scripts/release_aron_poles.spec.json'),
        unknowns=['Aron body/lid photographic analogue retains artistic/source disagreements despite explicit original book-size calibration.',
                  'Aron pole-tip relation to curtain after whole-room migration remains pending; no art/curtain changes.',
                  'Photo-derived menorah proportions and tending-stone metric choices remain authored, not exact future measurements.'])

def run(apply=False):
    plan=offline_plan()
    if not apply:return plan
    import unreal as u
    if Path(u.SystemLibrary.get_project_directory()).resolve()!=ROOT:raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Live/dirty world')
    target=ed.get_editor_world().get_path_name().split('.')[0]
    if not target.startswith('/Game/MikdashV3/Amah48Candidate_') or not target.endswith('/Maps/Walkthrough'):raise RuntimeError('Candidate only')
    units=module('release_amah48_candidate');protected=units.offline_plan()
    if target==protected['source']:raise RuntimeError('Never main')
    for folder in ('__ExternalActors__','__ExternalObjects__'):
        if (ROOT/'Content'/folder/target[6:]).exists():raise RuntimeError('External packages unsupported')
    h=module('release_resident_crowd');baseline=h._scene_snapshot(u,actors);byname={a.get_name():a for a in actors.get_all_level_actors()};selected=[];hashes={}
    for row in plan['proposals']:
        a=byname.get(row['name'])
        if a is None or a.get_attach_parent_actor() or a.get_attached_actors():raise RuntimeError('Assembly member missing/attached')
        cs=a.get_components_by_class(u.StaticMeshComponent)
        if len(cs)!=1 or h._path(cs[0].get_editor_property('static_mesh'))!=row['mesh'] or any(abs(x-y)>.001 for x,y in zip(h._pose(a),row['oldPose'])):raise RuntimeError('Mesh/pose changed; refuse mixed versions')
        for asset in [cs[0].get_editor_property('static_mesh')]+[cs[0].get_material(i) for i in range(cs[0].get_num_materials())]:
            p=h._path(asset)
            if p and p.startswith('/Game/'):
                f=ROOT/'Content'/(p[6:]+'.uasset');hashes[str(f)]=sha(f)
        selected.append((a,row))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');checkpoint=ROOT.parent/'ReviewCheckpoints'/('AronMenorah48-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
    f=units.disk(target);before=sha(f);shutil.copy2(f,checkpoint/'Candidate.umap')
    if sha(checkpoint/'Candidate.umap')!=before:raise RuntimeError('Checkpoint mismatch')
    report=dict(plan,candidate=target,checkpoint=str(checkpoint),candidateShaBefore=before,status='STARTED',protectedAssets=hashes)
    receipt=REVIEW/('amah48-aron-menorah-'+stamp+'.json')
    def write():receipt.write_text(json.dumps(report,indent=2))
    write()
    try:
        if offline_plan()!=plan or units.offline_plan()!=protected:raise RuntimeError('Input hashes changed')
        for a,row in selected:
            a.modify(True);a.set_actor_location(u.Vector(*row['location48']),False,True);a.set_actor_scale3d(u.Vector(*row['scale48']))
        expected=h._scene_snapshot(u,actors);names={r['name'] for _,r in selected}
        if {k:v for k,v in expected.items() if k not in names}!={k:v for k,v in baseline.items() if k not in names}:raise RuntimeError('Unrelated scene changed')
        if not levels.save_current_level() or not levels.load_level(target):raise RuntimeError('Save/reopen failed')
        if ed.get_editor_world().get_path_name().split('.')[0]!=target or h._scene_snapshot(u,actors)!=expected:raise RuntimeError('Readback mismatch')
        report['status']='ELEVEN_PARTS_SAVED_REOPENED_POLE_TIP_FIT_PENDING'
    except Exception as error:report.update(status='FAILED_CHECKPOINT_AVAILABLE',error=repr(error));raise
    finally:
        report['protectedUnchanged']=units.offline_plan()==protected and all(sha(Path(p))==v for p,v in hashes.items())
        if not report['protectedUnchanged']:report['status']='FAILED_PROTECTED_HASHES'
        write()
        if not report['protectedUnchanged']:raise RuntimeError('Protected hashes changed')
    return report
if __name__=='__main__':print(json.dumps(offline_plan(),indent=2))

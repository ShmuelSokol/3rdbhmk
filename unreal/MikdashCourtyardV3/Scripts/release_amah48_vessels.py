"""Candidate-only exact TI assembly scaling; unknown Aron/Menorah remain explicit."""
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'SourceAssets/scale-review'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name):
    s=importlib.util.spec_from_file_location('v48_'+name,ROOT/'Scripts'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def offline_plan():
    spec_path=ROOT/'Scripts/release_import_keilim_ti.spec.json'
    inventory_path=REVIEW/'native-scale-inventory-20260908T133142315573Z.json'
    spec=json.loads(spec_path.read_text());inventory=json.loads(inventory_path.read_text())
    proposals=[]
    for key,group in spec['groups'].items():
        for mesh in group['meshes']:
            package='/Game/MikdashV3/MaterialReview/KeilimTIV1/Meshes/'+mesh['name']
            matches=[a for a in inventory['actors'] if any(c.get('mesh','').split('.')[0]==package for c in a['components'])]
            if len(matches)!=1:raise RuntimeError('Exact TI assembly member missing/duplicated')
            a=matches[0];old=a['locationCm']
            if max(abs(old[i]-group['placement']['origin'][i]) for i in (0,1))>.001 or abs(old[2]-925)>.001 or a['scale']!=[1,1,1]:raise RuntimeError('TI source support/scale mismatch')
            proposals.append(dict(name=a['name'],label=a['label'],mesh=package,oldPose=old+a['rotationDegrees']+a['scale'],
                location48=[old[0]*.96,old[1]*.96,888+(old[2]-925)],scale48=[.96,.96,.96],
                bounds48={k:[x*.96 for x in mesh['canonicalBoundsCm'][k]] for k in ('min','max')}))
    if len(proposals)!=8:raise RuntimeError('Expected complete7-part table+1altar')
    deferred=[dict(name=a['name'],label=a['label'],meshes=[c.get('mesh') for c in a['components']]) for a in inventory['actors']
              if any(any(x in c.get('mesh','') for x in ('Aron','MenorahV4')) for c in a['components'])]
    return dict(status='TI_EIGHT_PART_CANDIDATE_PLAN',proposals=proposals,deferred=deferred,
        specSha256=sha(spec_path),inventorySha256=sha(inventory_path),
        tableCoreDimensions48=[96,48,144],altarCoreDimensions48=[40,40,80],
        policy='TI assembly artwork/proportions follow authored amah/tefach dimensions together, including ornaments and loaves. No claim each ornament is independently sourced. Preserve numerical floor jitter as a physical placement offset; floor925 becomes888.',
        unknowns=['Aron uses third-party Body_NoPoles/Lid at1.471 plus separate study poles: preserve until exact body/lid/pole calibration reconciled.',
                  'MenorahV4 includes independently authored base/shaft/branches/ornaments/lamps/step; source calibration must be audited before sizing.',
                  'Historical inventory: native entry requires all exact mesh/pose matches. Later vessel replacements must refuse.',
                  'No source art/material changes; no curtain adoption; no main promotion.'])
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
    box_helper=module('release_import_doors')
    for row in plan['proposals']:
        a=byname.get(row['name'])
        if a is None or a.get_attach_parent_actor() or a.get_attached_actors():raise RuntimeError('Assembly member missing/attached')
        cs=a.get_components_by_class(u.StaticMeshComponent)
        if len(cs)!=1 or h._path(cs[0].get_editor_property('static_mesh'))!=row['mesh'] or any(abs(x-y)>.001 for x,y in zip(h._pose(a),row['oldPose'])):raise RuntimeError('Mesh/pose changed; refuse mixed versions')
        local=box_helper._static_mesh_box(cs[0].get_editor_property('static_mesh'))
        if max(abs(local[k][i]*.96-row['bounds48'][k][i]) for k in ('min','max') for i in range(3))>.1:raise RuntimeError('Source mesh dimensions differ from exact TI spec')
        for asset in [cs[0].get_editor_property('static_mesh')]+[cs[0].get_material(i) for i in range(cs[0].get_num_materials())]:
            p=h._path(asset)
            if p and p.startswith('/Game/'):
                f=ROOT/'Content'/(p[6:]+'.uasset');hashes[str(f)]=sha(f)
        selected.append((a,row))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');checkpoint=ROOT.parent/'ReviewCheckpoints'/('Vessels48-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
    f=units.disk(target);before=sha(f);shutil.copy2(f,checkpoint/'Candidate.umap')
    if sha(checkpoint/'Candidate.umap')!=before:raise RuntimeError('Checkpoint mismatch')
    report=dict(plan,candidate=target,checkpoint=str(checkpoint),candidateShaBefore=before,status='STARTED',protectedAssets=hashes)
    receipt=REVIEW/('amah48-vessels-'+stamp+'.json')
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
        report['status']='EIGHT_TI_PARTS_SAVED_REOPENED_ARON_MENORAH_PENDING'
    except Exception as error:report.update(status='FAILED_CHECKPOINT_AVAILABLE',error=repr(error));raise
    finally:
        report['protectedUnchanged']=units.offline_plan()==protected and all(sha(Path(p))==v for p,v in hashes.items())
        if not report['protectedUnchanged']:report['status']='FAILED_PROTECTED_HASHES'
        write()
        if not report['protectedUnchanged']:raise RuntimeError('Protected hashes changed')
    return report
if __name__=='__main__':print(json.dumps(offline_plan(),indent=2))

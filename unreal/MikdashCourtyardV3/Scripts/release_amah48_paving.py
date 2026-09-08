"""Synchronize58 accepted material overrides to the isolated48 candidate only."""
import json
import shutil
from datetime import datetime,timezone
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
TARGET='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
MAIN_SHA='480ea53fd3864b7adcaa14a3cc96419768710b8e33bed0dacd90a3731329f1b0'
def helper(name):
    s=importlib.util.spec_from_file_location('sync48_'+name,ROOT/'Scripts'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def plan():
    slabs=helper('release_jerusalem_floor_slabs');source=slabs.plan();units=helper('release_amah48_candidate');protected=units.offline_plan()
    if protected['sourceSha256']!=MAIN_SHA:raise RuntimeError('Approved main changed; explicit re-review required')
    floor_receipt=ROOT/'SourceAssets/visual-review/JerusalemPavingV1/native-floor-slabs-20260908T164354150280Z.json'
    platform_receipt=ROOT/'SourceAssets/visual-review/native-mount-paving-20260908T162815394171Z.json'
    f=json.loads(floor_receipt.read_text());p=json.loads(platform_receipt.read_text())
    if f['status']!='57_FLOOR_OVERRIDES_SAVED_REOPENED' or f['mainSha256After']!=MAIN_SHA or not f['protectedUnchanged'] or p['status']!='SAVED_REOPENED_REVIEWED_PAVING':raise RuntimeError('Accepted adoption evidence mismatch')
    rows=[dict(name=r['actorName'],label=r['actorLabel'],component=r['componentName'],mesh=r['mesh'],old=[x.split('.')[0] for x in r['nativeMaterials']],new=slabs.MATERIAL) for r in source['rows']]
    invpath=ROOT/'SourceAssets/scale-review/native-scale-inventory-20260908T133142315573Z.json'
    inv=json.loads(invpath.read_text());mesh='/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface'
    matches=[(a,c) for a in inv['actors'] for c in a['components'] if c.get('mesh','').split('.')[0]==mesh]
    if len(matches)!=1:raise RuntimeError('Exact platform identity missing')
    a,c=matches[0];rows.append(dict(name=a['name'],label=a['label'],component=c['name'],mesh=mesh,old=[x.split('.')[0] for x in c['materials']],new='/Game/MikdashV3/MaterialReview/JerusalemPavingV2/M_JerusalemPaving_500cm'))
    if rows[-1]['old']!=['/Game/MikdashV3/MaterialReview/JerusalemStoneV2/M_JerusalemStoneV2_PavingReview']:raise RuntimeError('Unexpected historical platform material')
    hashes={str(path):slabs.sha(path) for path in (floor_receipt,platform_receipt,invpath,ROOT/'SourceAssets/visual-review/JerusalemPavingV1/floor-scope.json')}
    for row in rows:
        for package in [row['mesh'],row['new']]+row['old']:
            path=slabs.assetfile(package);hashes[str(path)]=slabs.sha(path)
    hashes[str(slabs.assetfile(slabs.TEXTURE))]=slabs.TEXTURE_SHA
    # Bind approved materials to recorded native asset hashes, not merely their names.
    if slabs.sha(slabs.assetfile(slabs.MATERIAL))!=f['protectedAssets'][str(slabs.assetfile(slabs.MATERIAL))]:raise RuntimeError('Approved slab material changed')
    native_import=json.loads((ROOT/'SourceAssets/visual-review/JerusalemPavingV1/native-import-20260908T162400705624Z.json').read_text())
    if slabs.sha(slabs.assetfile(rows[-1]['new']))!=native_import['assets'][rows[-1]['new']]:raise RuntimeError('Approved platform material changed')
    return dict(status='58_ACCEPTED_MATERIALS_CANDIDATE_SYNC_PLAN',candidate=TARGET,rows=rows,protectedAssets=hashes,mainSha256=MAIN_SHA,textureTileCm=500,visualAcceptance='Candidate PIE pending'),protected
def run(apply=False):
    report,protected=plan()
    if not apply:return report
    import unreal as u
    if Path(u.SystemLibrary.get_project_directory()).resolve()!=ROOT:raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Live/dirty editor')
    if ed.get_editor_world().get_path_name().split('.')[0]!=TARGET or TARGET==protected['source']:raise RuntimeError('Exact isolated candidate must already be loaded')
    descriptors=[a for a in actors.get_all_level_actors() if isinstance(a,u.MikdashSceneUnits)]
    if len(descriptors)!=1 or str(descriptors[0].get_editor_property('scene_revision'))!='Selected48.v1' or descriptors[0].get_editor_property('fixed_architecture_origin_cm').length()>.0001:raise RuntimeError('Valid selected48 origin-zero descriptor required')
    for folder in ('__ExternalActors__','__ExternalObjects__'):
        if (ROOT/'Content'/folder/TARGET[6:]).exists():raise RuntimeError('External objects unsupported')
    h=helper('release_resident_crowd');slabs=helper('release_jerusalem_floor_slabs');units=helper('release_amah48_candidate');baseline=h._scene_snapshot(u,actors);byname={a.get_name():a for a in actors.get_all_level_actors()};selected=[]
    for row in report['rows']:
        a=byname.get(row['name'])
        if not a or a.get_actor_label()!=row['label']:raise RuntimeError('Exact actor mismatch')
        cs=a.get_components_by_class(u.StaticMeshComponent)
        if len(cs)!=1 or cs[0].get_name()!=row['component'] or h._path(cs[0].get_editor_property('static_mesh'))!=row['mesh']:raise RuntimeError('Exact component/mesh mismatch')
        c=cs[0]
        if [h._path(c.get_material(i)) for i in range(c.get_num_materials())]!=row['old'] or len(row['old'])!=1:raise RuntimeError('Original material mismatch or already applied')
        selected.append((a,c,row))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');checkpoint=ROOT.parent/'ReviewCheckpoints'/('Paving48-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
    path=units.disk(TARGET);before=slabs.sha(path);shutil.copy2(path,checkpoint/'Candidate.umap')
    if slabs.sha(checkpoint/'Candidate.umap')!=before:raise RuntimeError('Checkpoint mismatch')
    report.update(status='STARTED',checkpoint=str(checkpoint),candidateShaBefore=before);receipt=ROOT/'SourceAssets/scale-review'/('amah48-paving-'+stamp+'.json')
    def write():receipt.write_text(json.dumps(report,indent=2),encoding='utf8')
    write()
    try:
        fresh,current=plan()
        if current!=protected or fresh['protectedAssets']!=report['protectedAssets']:raise RuntimeError('Source/main changed before mutation')
        for a,c,row in selected:
            material=u.load_asset(row['new'])
            if not material:raise RuntimeError('Approved material missing')
            a.modify(True);c.modify(True);c.set_material(0,material)
        expected=h._scene_snapshot(u,actors);normalized=json.loads(json.dumps(expected))
        for a,c,row in selected:
            for b,n in zip(baseline[a.get_name()]['components'],normalized[a.get_name()]['components']):
                if 'materials'in n:n['materials']=b['materials']
        if normalized!=baseline:raise RuntimeError('Unexpected non-material scene change')
        if not levels.save_current_level() or not levels.load_level(TARGET) or ed.get_editor_world().get_path_name().split('.')[0]!=TARGET or h._scene_snapshot(u,actors)!=expected:raise RuntimeError('Save/reopen mismatch')
        report['status']='58_MATERIALS_SAVED_REOPENED_CANDIDATE_VISUAL_PENDING'
    except Exception as error:report.update(status='FAILED_CHECKPOINT_AVAILABLE',error=repr(error));raise
    finally:
        report['protectedUnchanged']=units.offline_plan()==protected and all(slabs.sha(Path(p))==v for p,v in report['protectedAssets'].items())
        report['candidateShaAfter']=slabs.sha(path)
        if not report['protectedUnchanged']:report['status']='FAILED_PROTECTED_HASHES'
        write()
        if not report['protectedUnchanged']:raise RuntimeError('Protected main/assets/source changed')
    return report

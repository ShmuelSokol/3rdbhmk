"""Candidate marker migration; C++ reads unchanged legacy JSON through scene descriptor."""
import json
import hashlib
import shutil
import importlib.util
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
KEYS=('mount-and-house','immersion','soreg-and-cheil','east-outer-gate','outer-court','north-gate-and-inner-wall','east-inner-gate','ezras-yisroel','duchan','outer-altar','kiyor','twelve-steps','ulam','heikhal','menorah','shulchan','golden-altar','paroches')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name):
    s=importlib.util.spec_from_file_location('tour48_'+name,ROOT/'Scripts'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def offline_plan():
    source=ROOT/'SourceAssets/tour-review/tour-stops.json';staged=ROOT/'Content/Distribution/Tour/tour-stops.json'
    data=json.loads(source.read_text(encoding='utf-8-sig'));copy=json.loads(staged.read_text(encoding='utf-8-sig'))
    if data!=copy:raise RuntimeError('Staged/source route differ')
    if tuple(s['key'] for s in data['stops'])!=KEYS:raise RuntimeError('Unknown/missing stop scope')
    rows=[]
    for s in data['stops']:
        rows.append(dict(key=s['key'],legacyStand=s['stand'],stand48=[v*.96 for v in s['stand']],look48=[v*.96 for v in s['look']],
            approaches48=[[v*.96 for v in p] for p in s.get('approach',[])],marker48=[s['stand'][0]*.96,s['stand'][1]*.96,s['stand'][2]*.96+4],
            arriveRadiusCm=s.get('arriveRadiusCm',data['defaults']['arriveRadiusCm']),classification='named Temple feature or authored Temple apron stop; not geographic Kotel/city'))
    return dict(status='18_CLASSIFIED_LEGACY_STOPS_CANDIDATE_PLAN',stops=rows,sourceSha256=sha(source),stagedSha256=sha(staged),
                physicalEyeHeightCm=168,physicalMarkerOffsetCm=4,traceAcceptance='PENDING_REAL_RUNTIME_ONLY')
def run(apply=False):
    report=offline_plan()
    if not apply:return report
    import unreal as u
    if Path(u.SystemLibrary.get_project_directory()).resolve()!=ROOT:raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Live/dirty world')
    target=ed.get_editor_world().get_path_name().split('.')[0]
    if not target.startswith('/Game/MikdashV3/Amah48Candidate_'):raise RuntimeError('Candidate only')
    descriptors=[a for a in actors.get_all_level_actors() if isinstance(a,u.MikdashSceneUnits)]
    if len(descriptors)!=1 or str(descriptors[0].get_editor_property('scene_revision'))!='Selected48.v1':raise RuntimeError('Selected48 descriptor required')
    origin=descriptors[0].get_editor_property('fixed_architecture_origin_cm')
    if origin.length()>.0001:raise RuntimeError('This marker plan requires origin zero')
    units=module('release_amah48_candidate');protected=units.offline_plan()
    if target==protected['source']:raise RuntimeError('Never main')
    for folder in ('__ExternalActors__','__ExternalObjects__'):
        if (ROOT/'Content'/folder/target[6:]).exists():raise RuntimeError('External packages unsupported')
    h=module('release_resident_crowd');baseline=h._scene_snapshot(u,actors);selected=[]
    for row in report['stops']:
        found=[a for a in actors.get_all_level_actors() if 'MikdashTourMarker' in [str(t) for t in a.tags] and row['key'] in [str(t) for t in a.tags]]
        if len(found)!=1:raise RuntimeError('Need unique marker '+row['key'])
        a=found[0];expected=row['legacyStand'][:];expected[2]+=4
        if any(abs(x-y)>.1 for x,y in zip(h._pose(a)[:3],expected)):raise RuntimeError('Marker was moved/grounded differently; fresh physical audit needed')
        selected.append((a,row))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');checkpoint=ROOT.parent/'ReviewCheckpoints'/('Tour48-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
    path=units.disk(target);before=sha(path);shutil.copy2(path,checkpoint/'Candidate.umap')
    if sha(checkpoint/'Candidate.umap')!=before:raise RuntimeError('Checkpoint mismatch')
    receipt=ROOT/'SourceAssets/scale-review'/('amah48-tour-'+stamp+'.json');report.update(candidate=target,checkpoint=str(checkpoint))
    try:
        for a,row in selected:a.modify(True);a.set_actor_location(u.Vector(*row['marker48']),False,True)
        expected=h._scene_snapshot(u,actors);names={a.get_name() for a,_ in selected}
        if {k:v for k,v in expected.items() if k not in names}!={k:v for k,v in baseline.items() if k not in names}:raise RuntimeError('Unrelated scene changed')
        if not levels.save_current_level() or not levels.load_level(target):raise RuntimeError('Save/reopen failed')
        if ed.get_editor_world().get_path_name().split('.')[0]!=target or h._scene_snapshot(u,actors)!=expected:raise RuntimeError('Readback mismatch')
        report['status']='18_MARKERS_SAVED_REOPENED_RUNTIME_ROUTE_AND_CLEARANCE_PENDING'
    except Exception as error:report.update(status='FAILED_CHECKPOINT_AVAILABLE',error=repr(error));raise
    finally:
        report['protectedUnchanged']=units.offline_plan()==protected and offline_plan()['sourceSha256']==report['sourceSha256'] and offline_plan()['stagedSha256']==report['stagedSha256']
        if not report['protectedUnchanged']:report['status']='FAILED_PROTECTED_HASHES'
        receipt.write_text(json.dumps(report,indent=2))
        if not report['protectedUnchanged']:raise RuntimeError('Protected hashes changed')
    return report

"""Opt-in twelve-actor replacement in an already loaded Amah48 candidate only."""
import importlib.util
import json
import hashlib
import shutil
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):
    s=importlib.util.spec_from_file_location('d48_'+name,ROOT/'Scripts'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def preflight():
    spec=json.loads((HERE/'spec.json').read_text())
    for m in spec['meshes']:
        if sha(HERE/m['file'])!=m['sha256']:raise RuntimeError('OBJ changed')
    if len(spec['meshes'])!=3 or len(spec['replacements'])!=12:raise RuntimeError('Unexpected coverage')
    if sha(HERE/'generate.py')!=spec['generatorSha256']:raise RuntimeError('Generator changed')
    return spec
def run(apply=False):
    spec=preflight()
    if not apply:return spec
    import unreal as u
    if Path(u.SystemLibrary.get_project_directory()).resolve()!=ROOT:raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Live/dirty world')
    target=editor.get_editor_world().get_path_name().split('.')[0]
    if not target.startswith('/Game/MikdashV3/Amah48Candidate_') or not target.endswith('/Maps/Walkthrough'):raise RuntimeError('Candidate-only')
    units=load('release_amah48_candidate');protected=units.offline_plan()
    if target==protected['source']:raise RuntimeError('Never main')
    if u.EditorAssetLibrary.does_directory_exist(spec['namespace']):raise RuntimeError('Namespace already exists')
    for folder in ('__ExternalActors__','__ExternalObjects__'):
        if (ROOT/'Content'/folder/target[6:]).exists():raise RuntimeError('External packages unsupported')
    h=load('release_resident_crowd');baseline=h._scene_snapshot(u,actors);selected=[];hashes={}
    for row in spec['replacements']:
        matches=[a for a in actors.get_all_level_actors() if a.get_actor_label()==row['label']]
        if len(matches)!=1:raise RuntimeError('Target label not unique '+row['label'])
        a=matches[0];cs=a.get_components_by_class(u.StaticMeshComponent)
        if len(cs)!=1 or h._path(cs[0].get_editor_property('static_mesh'))!=row['oldMesh'] or a.get_attach_parent_actor() or a.get_attached_actors():raise RuntimeError('Target identity/attachment mismatch')
        if any(abs(x-y)>.001 for x,y in zip(h._pose(a),row['oldLocation']+row['oldRotation']+[1,1,1])):raise RuntimeError('Original pose changed')
        for asset in [cs[0].get_editor_property('static_mesh')]+[cs[0].get_material(i) for i in range(cs[0].get_num_materials())]:
            p=h._path(asset)
            if p and p.startswith('/Game/'):
                f=ROOT/'Content'/(p[6:]+'.uasset');hashes[str(f)]=sha(f)
        selected.append((a,cs[0],row))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');checkpoint=ROOT.parent/'ReviewCheckpoints'/('Doors48-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
    mapfile=units.disk(target);before=sha(mapfile);shutil.copy2(mapfile,checkpoint/'Candidate.umap')
    if sha(checkpoint/'Candidate.umap')!=before:raise RuntimeError('Checkpoint mismatch')
    report=dict(status='STARTED',candidate=target,before=before,checkpoint=str(checkpoint),protectedAssets=hashes,imports=[])
    receipt=HERE/('native-'+stamp+'.json')
    def write():receipt.write_text(json.dumps(report,indent=2))
    write()
    try:
        importer=load('release_import_doors');config=importer.load_spec()
        config['source']['folder']=str(HERE.relative_to(ROOT));config['source']['meshFolder']=spec['namespace']
        imported={}
        for row in spec['meshes']:
            material=next(c.get_material(0) for _,c,r in selected if r['oldMesh']==row['oldMesh'])
            record=dict(name=row['newMesh'].split('/')[-1],file=row['file'],sha256=row['sha256'],triangles=row['triangles'],canonicalBoundsCm=row['bounds'])
            mesh,info=importer.import_one_mesh(u,config,record,material);imported[row['newMesh']]=mesh;report['imports'].append(info);write()
        for a,c,row in selected:
            a.modify(True);c.modify(True);c.set_static_mesh(imported[row['newMesh']])
            a.set_actor_location(u.Vector(*row['location']),False,True);a.set_actor_rotation(u.Rotator(pitch=row['rotation'][0],yaw=row['rotation'][1],roll=row['rotation'][2]),True)
            b=a.get_actor_bounds(False);actual={'min':[b[0].x-b[1].x,b[0].y-b[1].y,b[0].z-b[1].z],'max':[b[0].x+b[1].x,b[0].y+b[1].y,b[0].z+b[1].z]}
            if max(abs(actual[k][i]-row['bounds'][k][i]) for k in ('min','max') for i in range(3))>.1:raise RuntimeError('Placed bounds mismatch')
        names={a.get_name() for a,_,_ in selected};expected=h._scene_snapshot(u,actors)
        if {k:v for k,v in expected.items() if k not in names}!={k:v for k,v in baseline.items() if k not in names}:raise RuntimeError('Unrelated scene changed')
        if not levels.save_current_level() or not levels.load_level(target):raise RuntimeError('Save/reopen failed')
        if editor.get_editor_world().get_path_name().split('.')[0]!=target or h._scene_snapshot(u,actors)!=expected:raise RuntimeError('Readback mismatch')
        report.update(status='TWELVE_KODESH48_PARTS_SAVED_REOPENED_RUNTIME_PENDING',selected=sorted(names))
    except Exception as error:report.update(status='FAILED_CHECKPOINT_AVAILABLE',error=repr(error));raise
    finally:
        report['protectedUnchanged']=units.offline_plan()==protected and all(sha(Path(p))==v for p,v in hashes.items())
        if not report['protectedUnchanged']:report['status']='FAILED_PROTECTED_HASHES'
        write()
        if not report['protectedUnchanged']:raise RuntimeError('Protected hashes changed')
    return report

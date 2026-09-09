"""Reviewed global decal attenuation; source-plan/per-entry opacity stays untouched.
Native switches: -SurfaceSoftApply OR -SurfaceSoftVerify=<absolute apply receipt>.
Create-once children, no overwrites/deletes. Importing this module does nothing.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
EXPECTED = '66845552ba0b3d45b76dd2f1e9089492b6f80302f569bf5832bd9755eeee85d8'
NAMESPACE = '/Game/MikdashV3/SurfaceDetailSoftV1'
TAG = 'MikdashSurfaceWearV1'
OPACITY = 0.12
sys.path.insert(0, str(ROOT / 'Scripts'))
from release_place_assets import snapshot_row, numeric_baseline_rows

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def disk(package, ext='uasset'):
    if not package.startswith('/Game/'): raise RuntimeError('Nonproject package: ' + package)
    return ROOT / 'Content' / (package.split('.')[0][6:] + '.' + ext)

def files_before():
    # Includes source materials, meshes, all other maps and sidecar packages.
    target = disk(TARGET, 'umap')
    return {str(p): sha(p) for p in (ROOT/'Content').rglob('*')
            if p.is_file() and p != target}

def check_hashes(expected):
    return [p for p,h in expected.items() if not Path(p).is_file() or sha(p)!=h]

def inventory():
    proc = subprocess.run(['tasklist','/FO','CSV','/NH'],capture_output=True,text=True,check=True,timeout=30)
    rows = list(csv.reader(io.StringIO(proc.stdout)))
    if not rows or any(len(r)<2 for r in rows): raise RuntimeError('Malformed process inventory')
    others = [r[:2] for r in rows if r[0].lower() in ('unrealeditor.exe','unrealeditor-cmd.exe') and int(r[1])!=os.getpid()]
    if others: raise RuntimeError('Other editor present: '+repr(others))

def run(apply=False, verify=None):
    import unreal as ue
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=ROOT/'SourceAssets/surface-review';folder.mkdir(parents=True,exist_ok=True)
    path=folder/('surface-soft-'+('verify-' if verify else 'apply-')+stamp+'.json')
    receipt={'status':'started','map':TARGET,'stamp':stamp,'processId':os.getpid(),'mapSaved':False,'errors':[],
             'opacity':OPACITY,'scope':'Reviewed global attenuation, not per-entry opacity repair',
             'runtimeVisualAcceptance':'PENDING; numeric persistence only'}
    def write(): path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    write();mapfile=disk(TARGET,'umap');before=sha(mapfile);protected={}
    receipt['mapSha256Before']=before
    try:
        if bool(apply)==bool(verify): raise RuntimeError('Choose exactly one apply or verify')
        if Path(ue.Paths.project_dir()).resolve()!=ROOT: raise RuntimeError('Wrong project')
        inventory()
        editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
        assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        if editor.get_game_world(): raise RuntimeError('Game world active')
        def clean():
            if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('Dirty packages; refusing')
        clean()
        earlier=json.loads(Path(verify).read_text(encoding='utf-8-sig')) if verify else None
        if earlier:
            if earlier.get('status')!='saved_reopened' or earlier.get('map')!=TARGET: raise RuntimeError('Invalid apply receipt')
            if earlier.get('processId')==os.getpid(): raise RuntimeError('Verification requires a different process')
            if before!=earlier['mapSha256After']: raise RuntimeError('Map differs from apply receipt')
            if check_hashes(earlier['oldFileHashes']): raise RuntimeError('Old content differs from apply receipt')
        elif before!=EXPECTED: raise RuntimeError('Main differs from reviewed wear checkpoint')
        if apply and (assets.does_directory_exist(NAMESPACE) or disk(NAMESPACE).with_suffix('').exists()):
            raise RuntimeError('Create-once namespace exists; preserve it')
        protected=files_before();receipt['oldFileHashes']=protected
        if not levels.load_level(TARGET): raise RuntimeError('Target load failed')
        world=editor.get_editor_world()
        if world is None or world.get_outermost().get_name()!=TARGET: raise RuntimeError('Wrong loaded map')
        clean()
        def selected():
            result={}
            for a in actors.get_all_level_actors():
                if isinstance(a,ue.DecalActor) and TAG in [str(t) for t in a.get_editor_property('tags')]:
                    label=a.get_actor_label()
                    if label in result: raise RuntimeError('Duplicate decal label '+label)
                    result[label]=(a,a.get_component_by_class(ue.DecalComponent))
            if len(result)!=460: raise RuntimeError('Expected460tagged decals, got '+str(len(result)))
            return result
        excluded=[set(),set(),set()]
        def snapshot():
            rows=[snapshot_row(ue,a,TARGET) for a in actors.get_all_level_actors()]
            bindings={}
            tags={}
            for a in actors.get_all_level_actors():
                if a.get_outermost().get_name()!=TARGET: continue
                tags[a.get_name()]=[str(t) for t in a.get_editor_property('tags')]
                for c in a.get_components_by_class(ue.StaticMeshComponent):
                    bindings[c.get_path_name()]=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
            raw=(numeric_baseline_rows(rows,strict=True),bindings,tags)
            return tuple({k:v for k,v in part.items() if k not in excluded[i]} for i,part in enumerate(raw))
        # Observe the exact clean reload churn before mutation. Never broadly ignore
        # generated actors/components, and never exclude a selected decal's identity.
        first=snapshot()
        first_decals=selected()
        selected_names={a.get_name() for a,c in first_decals.values()}
        first_labels=set(first_decals)
        clean()
        if not levels.load_level(TARGET): raise RuntimeError('Pristine reload failed')
        clean()
        second=snapshot()
        if set(selected())!=first_labels: raise RuntimeError('Selected decals churn on clean reload')
        evidence=[]
        for i,(left,right) in enumerate(zip(first,second)):
            for key in sorted(set(left)|set(right)):
                if left.get(key)!=right.get(key):
                    if i in (0,2) and key in selected_names:
                        raise RuntimeError('Selected decal transform/tag changes on pristine reload: '+key)
                    excluded[i].add(key)
                    evidence.append({'section':('persistentActors','staticMeshBindings','persistentTags')[i],
                                     'key':key,'before':left.get(key),'after':right.get(key)})
        receipt['pristineReloadChurn']=evidence
        receipt['snapshotExcludedKeys']=[sorted(keys) for keys in excluded]
        if sha(mapfile)!=before: raise RuntimeError('Pristine reload changed map bytes')
        write()
        baseline=snapshot();decals=selected()
        if apply:
            checkpoint=ROOT.parent/'ReviewCheckpoints'/('SurfaceSoft-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
            shutil.copy2(mapfile,checkpoint/mapfile.name)
            if sha(checkpoint/mapfile.name)!=before: raise RuntimeError('Checkpoint hash mismatch')
            for name in ('__ExternalActors__','__ExternalObjects__'):
                src=ROOT/'Content'/name/TARGET[6:]
                if src.exists(): shutil.copytree(src,checkpoint/name/TARGET[6:])
            receipt['checkpoint']=str(checkpoint)
            parents={};original={}
            for label,(a,c) in decals.items():
                mat=c.get_decal_material()
                if mat is None or not isinstance(mat,ue.MaterialInstanceConstant) or not mat.get_path_name().startswith('/Game/MikdashV3/SurfaceDetailV2/'):
                    raise RuntimeError('Unexpected original material '+label)
                original[label]=mat.get_path_name();parents[mat.get_path_name()]=mat
            receipt['originalDecalMaterials']=original;children={};records=[]
            tools=ue.AssetToolsHelpers.get_asset_tools()
            for index,parent_path in enumerate(sorted(parents)):
                name='MI_Soft_%02d'%index
                child=tools.create_asset(name,NAMESPACE,ue.MaterialInstanceConstant,ue.MaterialInstanceConstantFactoryNew())
                if child is None: raise RuntimeError('Child creation failed')
                ue.MaterialEditingLibrary.set_material_instance_parent(child,parents[parent_path])
                ue.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(child,'Opacity',OPACITY)
                ue.MaterialEditingLibrary.update_material_instance(child)
                if abs(ue.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(child,'Opacity')-OPACITY)>1e-6: raise RuntimeError('Opacity readback differs')
                if not assets.save_loaded_asset(child,only_if_is_dirty=False): raise RuntimeError('Child save failed')
                children[parent_path]=child
                records.append({'path':child.get_path_name(),'parent':parent_path,'sha256':sha(disk(child.get_path_name()))})
            receipt['children']=records
            receipt['decalMaterials']={label:children[parent].get_path_name() for label,parent in original.items()}
            write()
            for label,(a,c) in decals.items():
                a.modify(True);c.modify(True);c.set_decal_material(children[original[label]])
            if snapshot()!=baseline: raise RuntimeError('Transforms/tags/static-mesh materials changed before save')
            if check_hashes(protected): raise RuntimeError('Old content changed before save')
            if not levels.save_current_level(): raise RuntimeError('Map save returned false')
            receipt['mapSaved']=True;receipt['mapSha256After']=sha(mapfile);receipt['mapSha256AfterSave']=receipt['mapSha256After'];write()
            if not levels.load_level(TARGET): raise RuntimeError('Reopen failed')
        else:
            receipt['applyReceipt']=str(verify);receipt['children']=earlier['children'];receipt['decalMaterials']=earlier['decalMaterials']
        actual=selected()
        if set(actual)!=set(receipt['decalMaterials']): raise RuntimeError('Decal labels differ')
        for label,(a,c) in actual.items():
            if c.get_decal_material().get_path_name()!=receipt['decalMaterials'][label]: raise RuntimeError('Decal binding differs '+label)
        for row in receipt['children']:
            material=assets.load_asset(row['path'])
            if material is None or sha(disk(row['path']))!=row['sha256']: raise RuntimeError('Child bytes differ')
            if material.get_editor_property('parent').get_path_name()!=row['parent']: raise RuntimeError('Child parent differs')
            if abs(ue.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material,'Opacity')-OPACITY)>1e-6: raise RuntimeError('Child opacity differs')
        if snapshot()!=baseline: raise RuntimeError('Transforms/tags/static-mesh materials changed after reopen')
        receipt['verifiedDecals']=len(actual);receipt['status']='fresh_process_verified' if verify else 'saved_reopened'
    except Exception as e:
        receipt['errors'].append(repr(e));receipt['status']='failed';raise
    finally:
        receipt['mapSha256After']=sha(mapfile);receipt['mapBytesChanged']=receipt['mapSha256After']!=before
        receipt['oldFileDifferences']=check_hashes(protected);receipt['oldFilesUnchanged']=not receipt['oldFileDifferences']
        if receipt['oldFileDifferences']: receipt['status']='failed_old_content_changed'
        if verify and receipt['mapBytesChanged']: receipt['status']='failed_verify_changed_map'
        write()
    if receipt['status'].startswith('failed'): raise RuntimeError(receipt['status'])
    return receipt

if __name__=='__main__':
    try:
        import unreal as ue
    except ImportError:
        print('Offline: main-only460decal create-once Opacity0.12; native unverified')
    else:
        command=ue.SystemLibrary.get_command_line();tokens=command.split()
        verify=next((t.split('=',1)[1].strip('"') for t in tokens if t.lower().startswith('-surfacesoftverify=')),None)
        try: run(apply=any(t.lower()=='-surfacesoftapply' for t in tokens),verify=verify)
        finally:
            if '-executepythonscript' in command.lower() and '-run=pythonscript' not in command.lower(): ue.SystemLibrary.quit_editor()

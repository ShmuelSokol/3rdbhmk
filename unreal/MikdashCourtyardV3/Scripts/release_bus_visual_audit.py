"""Bus source/slot audit. Offline is read-only; native defaults to dry run.
Native apply repairs only mismatched component material slots on a NEW review map.
No mesh winding, source materials, collision, transforms, lighting or main map edits.
"""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'SourceAssets/arrival-review/TransitV2'
OUT = ROOT/'SourceAssets/transit-review'
MAIN = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
REVIEW = '/Game/MikdashV3/MaterialReview/BusVisualAuditV1/Maps/Walkthrough'

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]

def dot(a,b): return sum(x*y for x,y in zip(a,b))
def sub(a,b): return [x-y for x,y in zip(a,b)]
def package(p,ext='uasset'): return ROOT/'Content'/(p[len('/Game/') :]+'.'+ext)

def offline():
    manifest=json.loads((SOURCE/'offline-checks.json').read_text())
    rows=[]
    for rec in manifest['imports']:
        if rec['assembly']!='Bus': continue
        p=SOURCE/rec['file']; assert sha(p)==rec['sha256'],p
        vertices=[];normals=[];uv=[];faces=[]
        for line in p.read_text().splitlines():
            w=line.split()
            if not w: continue
            if w[0]=='v':vertices.append(list(map(float,w[1:])))
            elif w[0]=='vn':normals.append(list(map(float,w[1:])))
            elif w[0]=='vt':uv.append(list(map(float,w[1:])))
            elif w[0]=='f':faces.append([[int(i)-1 for i in x.split('/')] for x in w[1:]])
        worst=1.;minuv=float('inf')
        for face in faces:
            assert len(face)==3
            a,b,c=[vertices[x[0]] for x in face];n=cross(sub(b,a),sub(c,a));length=math.sqrt(dot(n,n));assert length>1e-9
            for x in face:worst=min(worst,dot(n,normals[x[2]])/length)
            u,v,w=[uv[x[1]] for x in face];area=abs((v[0]-u[0])*(w[1]-u[1])-(v[1]-u[1])*(w[0]-u[0]));minuv=min(minuv,area)
        assert worst>.999999 and minuv>1e-12
        assert len(faces)==rec['triangles']
        rows.append(dict(mesh=rec['name'],triangles=len(faces),minimumFaceNormalDot=worst,minimumUVDoubleArea=minuv,sha256=sha(p)))
    assert len(rows)==13
    return dict(status='source_obj_normals_uvs_pass_native_slots_pending',meshes=rows,
                note='OBJ right-handed face-normal agreement verified before legacy import. Native rendering winding is not inferred from OBJ cross product.')

def native(apply=False):
    import unreal as ue
    assert Path(ue.Paths.project_dir()).resolve()==ROOT
    assert not ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world(),'PIE preserved'
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Dirty map preserved'
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'Dirty assets preserved'
    levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    spec=json.loads((ROOT/'Scripts/release_place_bus.spec.json').read_text(encoding='utf-8-sig'))
    refs={spec['meshFolder']+r['name']:r for r in spec['meshes']}
    def path(o):return o.get_path_name().split('.')[0] if o else None
    def snapshot():
        result=[]
        for a in actors.get_all_level_actors():
            c=a.get_component_by_class(ue.StaticMeshComponent)
            m=c.get_editor_property('static_mesh') if c else None
            if path(m) not in refs:continue
            p=path(m);r=refs[p];assert m.get_num_triangles(0)==r['triangles']
            loc=a.get_actor_location();rot=a.get_actor_rotation();scale=a.get_actor_scale3d()
            expected='/Game/MikdashV3/ArrivalReview/TransitV2/Materials/M_TransitV2_'+p.rsplit('_Bus_',1)[1]
            result.append(dict(label=a.get_actor_label(),mesh=p,expected=expected,
              pose=[loc.x,loc.y,loc.z,rot.pitch,rot.yaw,rot.roll,scale.x,scale.y,scale.z],
              collision=str(c.get_collision_profile_name()),
              slots=[path(c.get_material(i)) for i in range(c.get_num_materials())]))
        assert len(result)==13 and len({r['mesh'] for r in result})==13,'Expected exactly original 13 bus parts'
        assert all(r['slots'] for r in result)
        return sorted(result,key=lambda r:r['mesh'])
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    OUT.mkdir(parents=True,exist_ok=True);receipt=OUT/('bus-visual-audit-'+stamp+'.json')
    protected=[package(MAIN,'umap')]+[package(p,'umap') for p in spec['protectedMaps']]
    protected+=sorted((ROOT/'Content/MikdashV3/ArrivalReview/TransitV2').rglob('*.uasset'))
    before={str(p):sha(p) for p in protected}
    report=dict(status='started',apply=apply,source=offline(),protectedBefore=before)
    try:
        assert levels.load_level(MAIN)
        rows=snapshot();report['before']=rows
        def scene_inventory():
            result=[]
            for actor in actors.get_all_level_actors():
                loc=actor.get_actor_location();rot=actor.get_actor_rotation();scale=actor.get_actor_scale3d()
                result.append((actor.get_name(),actor.get_actor_label(),actor.get_class().get_path_name(),
                  (loc.x,loc.y,loc.z,rot.pitch,rot.yaw,rot.roll,scale.x,scale.y,scale.z)))
            return sorted(result)
        scene_before=scene_inventory();report['sceneActorCount']=len(scene_before)
        mismatch=[dict(mesh=r['mesh'],slot=i,actual=m,expected=r['expected']) for r in rows for i,m in enumerate(r['slots']) if m!=r['expected']]
        report['mismatches']=mismatch
        if not apply or not mismatch:
            report['status']='dry_run_slots_mismatch' if mismatch else 'slots_correct_no_correction_supported'
            return report
        assert not assets.does_asset_exist(REVIEW),'Unique review map already exists; preserve it'
        assert not package(REVIEW,'umap').exists()
        checkpoint=ROOT.parent/'ReviewCheckpoints'/('BusVisualAudit-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
        for p in protected:
            target=checkpoint/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        (checkpoint/'sha256.json').write_text(json.dumps(before,indent=2))
        report['checkpoint']=str(checkpoint)
        world=ue.EditorLoadingAndSavingUtils.new_map_from_template(MAIN,False)
        assert world
        editor_world=ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        assert world==editor_world
        assert world.get_outermost().get_name()!=MAIN,'Template returned original main world'
        assert scene_inventory()==scene_before,'Template changed scene inventory'
        assert snapshot()==rows,'Duplicate changed bus state'
        for a in actors.get_all_level_actors():
            c=a.get_component_by_class(ue.StaticMeshComponent)
            m=c.get_editor_property('static_mesh') if c else None
            if path(m) not in refs:continue
            expected='/Game/MikdashV3/ArrivalReview/TransitV2/Materials/M_TransitV2_'+path(m).rsplit('_Bus_',1)[1]
            material=ue.load_asset(expected);assert isinstance(material,ue.MaterialInterface),expected
            for i in range(c.get_num_materials()):
                if path(c.get_material(i))!=expected:c.set_material(i,material)
        assert scene_inventory()==scene_before,'Unexpected actor state change'
        after=snapshot()
        for old,new in zip(rows,after):
            assert {k:v for k,v in old.items() if k!='slots'}=={k:v for k,v in new.items() if k!='slots'}
            assert len(old['slots'])==len(new['slots']) and all(v==new['expected'] for v in new['slots'])
        assert ue.EditorLoadingAndSavingUtils.save_map(world,REVIEW)
        assert levels.load_level(REVIEW) and snapshot()==after
        report.update(status='review_saved_reopened_visual_pending',reviewMap=REVIEW,after=after,reviewSha256=sha(package(REVIEW,'umap')))
        return report
    except Exception as exc:
        report.update(status='failed_preserve_partial_review',error=repr(exc));raise
    finally:
        report['protectedAfter']={str(p):sha(p) for p in protected}
        report['protectedUnchanged']=report['protectedAfter']==before
        if not report['protectedUnchanged']:report.update(status='failed_protected_hash_guard',error='Protected file changed')
        receipt.write_text(json.dumps(report,indent=2)+'\n')
        assert report['protectedUnchanged'],'Protected file changed; inspect receipt'

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args()
    if args.offline:print(json.dumps(offline(),indent=2))
    else:parser.error('Use --offline; native explicit native(apply=False), then native(apply=True) only after slot evidence')

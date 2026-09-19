"""Export evaluated skeletal source normals with reference-to-VAT correspondence."""
from datetime import datetime,timezone
from pathlib import Path
import gzip,hashlib,json,re,sys
import unreal as ue

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
import create_crowd_vat_v2 as vat

def run():
    command=ue.SystemLibrary.get_command_line()
    study=re.search(r'-ResidentCrowdStudy=(09|10)\b',command).group(1)
    variant=re.search(r'-ResidentCrowdVariant=(Man_Elder|Woman_Young)\b',command).group(1)
    folder=ROOT/('SourceAssets/perf-review/crowd-vat/ResidentStudy'+study)/'Cast'/variant
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=folder/('posed-normals-'+stamp+'.json')
    report=dict(status='running',scope='Evaluated source-model skeletal positions/normals at four walk phases, with exact reference position/UV/material/normal correspondence to VAT UVs. Not GPU or continuous visual acceptance.',frames=[0,18,36,54],files={})
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    built=next(r for p in folder.glob('native-*.json') if (r:=json.loads(p.read_text())).get('status')=='built-needs-fresh-readback-and-render')
    reference_path=next(p for p in sorted(folder.glob('normals-*.json'),reverse=True) if json.loads(p.read_text()).get('status')=='audited-reference-normals')
    reference=json.loads(reference_path.read_text())
    protected={**built['protectedBefore'],**built['assets']}
    before={p:sha(ROOT/p) for p in protected};assert before==protected
    actor=None
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    try:
        world=ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        assert not world.get_outermost().get_name().startswith('/Game/')
        row=built['variants'][0]
        report.update(referenceAudit=reference_path.name,referenceAuditSha256=sha(reference_path),walkBake=row['walkBake'],source=reference['source'])
        static_file=next(folder/name for name in reference['files'] if name.endswith('-static.json.gz'))
        assert sha(static_file)==reference['files'][static_file.name]
        with gzip.open(static_file,'rt',encoding='utf-8') as stream:static=json.load(stream)
        key=lambda m,p,u,n:(m,tuple(p),tuple(u),tuple(n))
        mapped={key(m,p,u,n):tuple(b) for m,p,u,n,b in static['rows']}
        assert len(mapped)==len(static['rows'])
        mesh=ue.load_asset(reference['source']);assert mesh
        dynamic=ue.DynamicMesh()
        options=ue.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=False,use_build_scale=True)
        lod=ue.GeometryScriptMeshReadLOD(lod_type=ue.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)
        assert vat._outcome_ok(ue,ue.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,dynamic,options,lod))
        query=ue.GeometryScript_MeshQueries
        def triangle(data,tid):
            p=query.get_triangle_positions(data,tid);n=query.get_triangle_normals(data,tid);u=query.get_triangle_u_vs(data,0,tid)
            assert True in p and True in n and True in u
            p=[(float(v.x),float(v.y),float(v.z)) for v in p if isinstance(v,ue.Vector)]
            n=[(float(v.x),float(v.y),float(v.z)) for v in n if isinstance(v,ue.Vector)]
            u=[(float(v.x),float(v.y)) for v in u if isinstance(v,ue.Vector2D)]
            m,valid=ue.GeometryScript_Materials.get_triangle_material_id(data,tid);assert valid and len(p)==len(n)==len(u)==3
            return m,p,u,n
        triangles=[triangle(dynamic,tid) for tid in range(dynamic.get_triangle_count())]
        expected_keys={key(m,p,u,n) for m,ps,us,ns in triangles for p,u,n in zip(ps,us,ns)}
        assert expected_keys==set(mapped)
        actor=actors.spawn_actor_from_class(ue.SkeletalMeshActor,ue.Vector(),ue.Rotator(),transient=True);assert actor
        component=actor.skeletal_mesh_component
        component.set_mobility(ue.ComponentMobility.MOVABLE);component.set_skeletal_mesh_asset(mesh)
        clip=ue.load_asset(built['clips']['walk']);assert clip
        copy_options=ue.GeometryScriptCopyMeshFromComponentOptions(want_normals=True,want_tangents=False,requested_lod=lod)
        report['poses']=[]
        for frame in report['frames']:
            assert ue.MikdashAnimationReviewLibrary.evaluate_review_pose(component,clip,frame/60.)
            posed=ue.DynamicMesh()
            assert vat._outcome_ok(ue,ue.GeometryScript_SceneUtils.copy_mesh_from_component(component,posed,copy_options,False))
            assert posed.get_triangle_count()==len(triangles)
            values={};duplicates=0
            for tid,(material,rest_positions,uvs,rest_normals) in enumerate(triangles):
                m,positions,uv,normal=triangle(posed,tid)
                assert m==material and uv==uvs,'Posed triangle correspondence changed'
                for p,u,n,q,v in zip(rest_positions,uvs,rest_normals,positions,normal):
                    identity=key(m,p,u,n);entry=(m,p,mapped[identity],q,v)
                    if identity in values:
                        assert values[identity]==entry,'Inconsistent shared-corner deformation'
                        duplicates+=1
                    values[identity]=entry
            assert set(values)==expected_keys
            data=folder/('posed-normals-'+stamp+'-frame%02d.json.gz'%frame);assert not data.exists()
            with gzip.open(data,'wt',encoding='utf-8') as stream:json.dump(dict(fields=['material','referencePosition','vatUV','posedPosition','posedNormal'],frame=frame,rows=sorted(values.values())),stream,separators=(',',':'))
            report['files'][data.name]=sha(data)
            report['poses'].append(dict(frame=frame,uniqueRows=len(values),validatedDuplicateCorners=duplicates,file=data.name))
        texture=ue.load_asset(row['textures']['WalkPosition']);assert texture
        export=folder/('posed-normals-'+stamp+'-position.png');assert not export.exists()
        task=ue.AssetExportTask()
        for name,value in dict(object=texture,filename=str(export),exporter=ue.TextureExporterPNG(),automated=True,prompt=False,replace_identical=False).items():task.set_editor_property(name,value)
        assert ue.Exporter.run_asset_export_task(task) and export.is_file()
        report['files'][export.name]=sha(export)
        report['normalTexture']=next(name for name in reference['files'] if name.endswith('-walk.png'))
        report['normalTextureSha256']=reference['files'][report['normalTexture']]
        report['status']='exported-posed-normals'
    except Exception as error:
        report.update(status='failed',error=repr(error));raise
    finally:
        if actor:actors.destroy_actor(actor)
        report['protectedUnchanged']=before=={p:sha(ROOT/p) for p in before}
        report['protectedFileCount']=len(before)
        if not report['protectedUnchanged']:report['status']='failed-protected-changed'
        output.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':run()

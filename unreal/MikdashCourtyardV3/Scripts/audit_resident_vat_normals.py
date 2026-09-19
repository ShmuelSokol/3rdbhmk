"""Read-only source/conversion normal audit and lossless VAT texture export."""
from datetime import datetime, timezone
from pathlib import Path
import gzip
import hashlib
import json
import math
import re
import sys
import unreal as ue

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
import create_crowd_vat_v2 as vat

def run():
    command=ue.SystemLibrary.get_command_line()
    study=re.search(r'-ResidentCrowdStudy=(09|10|12)\b',command).group(1)
    variant=re.search(r'-ResidentCrowdVariant=(Man_Elder|Woman_Young)\b',command).group(1)
    folder=ROOT/('SourceAssets/perf-review/crowd-vat/ResidentStudy'+study)/'Cast'/variant
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=folder/('normals-'+stamp+'.json')
    report=dict(status='running',scope='Reference source versus converted corner normals, shared VAT texel normal splits, exported walk normal texture. Not a posed normal or visual acceptance.',files={})
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    builds=[json.loads(p.read_text()) for p in folder.glob('native-*.json')]
    built=next(r for r in builds if r.get('status')=='built-needs-fresh-readback-and-render')
    protected={**built['protectedBefore'],**built['assets']}
    before={p:sha(ROOT/p) for p in protected}
    assert before==protected
    try:
        source_path=built.get('structuredSource',{}).get('mesh',built['sourceMesh'])
        row=built['variants'][0]
        report.update(source=source_path,static=row['mesh'],walkBake=row['walkBake'])
        queries=ue.GeometryScript_MeshQueries
        mesh_rows={}
        for label,path in (('source',source_path),('static',row['mesh'])):
            mesh=ue.load_asset(path);assert mesh
            dynamic=ue.DynamicMesh()
            options=ue.GeometryScriptCopyMeshFromAssetOptions()
            for key,value in [('apply_build_settings',False),('request_tangents',False),('use_build_scale',True)]:
                options.set_editor_property(key,value)
            lod=ue.GeometryScriptMeshReadLOD(lod_type=ue.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)
            copy=ue.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh if label=='source' else ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh
            assert vat._outcome_ok(ue,copy(mesh,dynamic,options,lod))
            records=set()
            for tid in range(dynamic.get_triangle_count()):
                positions=queries.get_triangle_positions(dynamic,tid)
                normals=queries.get_triangle_normals(dynamic,tid)
                uvs=queries.get_triangle_u_vs(dynamic,0,tid)
                assert True in positions and True in normals and True in uvs
                positions=[(float(v.x),float(v.y),float(v.z)) for v in positions if isinstance(v,ue.Vector)]
                normals=[(float(v.x),float(v.y),float(v.z)) for v in normals if isinstance(v,ue.Vector)]
                uvs=[(float(v.x),float(v.y)) for v in uvs if isinstance(v,ue.Vector2D)]
                material,valid=ue.GeometryScript_Materials.get_triangle_material_id(dynamic,tid);assert valid
                baked_uvs=[None]*3
                if label=='static':
                    result=queries.get_triangle_u_vs(dynamic,row['walkBake']['uvChannel'],tid)
                    assert True in result
                    baked_uvs=[(float(v.x),float(v.y)) for v in result if isinstance(v,ue.Vector2D)]
                assert len(positions)==len(normals)==len(uvs)==len(baked_uvs)==3
                records.update((material,p,u,n,b) for p,u,n,b in zip(positions,uvs,normals,baked_uvs))
            records=sorted(records)
            data=folder/('normals-'+stamp+'-'+label+'.json.gz')
            assert not data.exists()
            with gzip.open(data,'wt',encoding='utf-8') as stream:json.dump(dict(fields=['material','position','uv0','normal','vatUV'],triangles=dynamic.get_triangle_count(),rows=records),stream,separators=(',',':'))
            report['files'][data.name]=sha(data)
            mesh_rows[label]=records
        def angle(a,b):
            length=math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
            assert length>1e-12
            return math.degrees(math.acos(max(-1.,min(1.,sum(x*y for x,y in zip(a,b))/length))))
        source={}
        for material,p,u,n,_ in mesh_rows['source']:source.setdefault((material,p,u),set()).add(n)
        errors=[];missing=0;groups={}
        for material,p,u,n,b in mesh_rows['static']:
            matches=source.get((material,p,u))
            if matches:errors.append((min(angle(n,m) for m in matches),material,p))
            else:missing+=1
            groups.setdefault(b,set()).add(n)
        splits=[]
        for uv,normals in groups.items():
            if len(normals)>1:
                normals=list(normals)
                maximum=max(angle(a,b) for i,a in enumerate(normals) for b in normals[i+1:])
                if maximum>0.01:splits.append(dict(uv=uv,normalCount=len(normals),maximumAngle=maximum))
        report['conversion']=dict(sourceRows=len(mesh_rows['source']),staticRows=len(mesh_rows['static']),exactPositionUVMatches=len(errors),missingKeys=missing,maximumNormalAngle=max(e[0] for e in errors),overOneDegree=sum(e[0]>1 for e in errors),worst=sorted(errors,reverse=True)[:20])
        report['sharedVATTexels']=dict(count=len(groups),divergentCornerNormals=len(splits),worst=sorted(splits,key=lambda v:v['maximumAngle'],reverse=True)[:20])
        texture=ue.load_asset(row['textures']['WalkNormal']);assert texture
        # AnimToTexture SIXTEEN_BITS writes integer RGBA16, not HDR float.
        # EXR's SupportsTexture rejects this format with a native assertion.
        output.write_text(json.dumps(report,indent=2)+'\n')
        export=folder/('normals-'+stamp+'-walk.png');assert not export.exists()
        task=ue.AssetExportTask()
        for key,value in dict(object=texture,filename=str(export),exporter=ue.TextureExporterPNG(),automated=True,prompt=False,replace_identical=False).items():task.set_editor_property(key,value)
        assert ue.Exporter.run_asset_export_task(task) and export.is_file()
        report['files'][export.name]=sha(export)
        report['status']='audited-reference-normals'
    except Exception as error:
        report.update(status='failed',error=repr(error));raise
    finally:
        report['protectedUnchanged']=before=={p:sha(ROOT/p) for p in before}
        report['protectedFileCount']=len(before)
        if not report['protectedUnchanged']:report['status']='failed-protected-changed'
        output.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':run()

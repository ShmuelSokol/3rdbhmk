"""Complete direct skeletal normal clips on an isolated geometry copy (11 from10;13 from12)."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,math,re,struct,sys,time,zlib
import unreal as ue

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
import create_crowd_vat_v2 as vat
from build_crowd_near_v2 import mesh_stats

def run():
    command=ue.SystemLibrary.get_command_line()
    study=re.search(r'-ResidentCrowdStudy=(11|13)\b',command).group(1)
    source_study={'11':'10','13':'12'}[study]
    variant=re.search(r'-ResidentCrowdVariant=(Man_Elder|Woman_Young)\b',command).group(1)
    build=bool(re.search(r'-ResidentCrowdBuild\b',command))
    old_folder=ROOT/('SourceAssets/perf-review/crowd-vat/ResidentStudy'+source_study)/'Cast'/variant
    folder=ROOT/('SourceAssets/perf-review/crowd-vat/ResidentStudy'+study)/'Cast'/variant
    folder.mkdir(parents=True,exist_ok=True)
    ns='/Game/MikdashV3/Runtime/CrowdResidentStudy'+study+'/Cast/'+variant
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=folder/('native-'+stamp+'.json')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    disk=lambda p:ROOT/('Content/'+p.split('.')[0].removeprefix('/Game/')+'.uasset')
    old_path=next(p for p in old_folder.glob('native-*.json') if json.loads(p.read_text()).get('status')=='built-needs-fresh-readback-and-render')
    old=json.loads(old_path.read_text())
    protected={**old['protectedBefore'],**old['assets']}
    protected.update({str(p.relative_to(ROOT)):sha(p) for p in (ROOT/('Content/MikdashV3/Runtime/CrowdResidentStudy'+source_study)).rglob('*.uasset')})
    protected.update({str(disk(p).relative_to(ROOT)):sha(disk(p)) for p in old['clips'].values()})
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    report=dict(status='running',scope='Study'+source_study+' geometry/material copy with complete direct skeletal walk/idle normals; no runtime adoption.',castVariant=variant,sourceStudy=old_path.relative_to(ROOT).as_posix(),sourceStudySha256=sha(old_path),sourceMesh=old['sourceMesh'],structuredSource=old['structuredSource'],clips=old['clips'],protectedBefore=protected,variants=[],assets={},files={})
    write=lambda:output.write_text(json.dumps(report,indent=2)+'\n')
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem);actor=None
    assets=ue.EditorAssetLibrary;ml=ue.MaterialEditingLibrary
    try:
        if build:
            assert not assets.does_directory_exist(ns),'Fresh candidate namespace required'
            world=ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
            assert not world.get_outermost().get_name().startswith('/Game/')
            source=ue.load_asset(old['structuredSource']['mesh']);assert source
            old_row=old['variants'][0];original=ue.load_asset(old_row['mesh']);assert original
            options=ue.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=False,use_build_scale=True)
            lod=ue.GeometryScriptMeshReadLOD(lod_type=ue.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)
            dynamic=ue.DynamicMesh();static=ue.DynamicMesh()
            assert vat._outcome_ok(ue,ue.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(source,dynamic,options,lod))
            assert vat._outcome_ok(ue,ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(original,static,options,lod))
            query=ue.GeometryScript_MeshQueries
            def vectors(result,cls):
                assert True in result
                return [tuple(float(getattr(v,c)) for c in ('x','y','z')[:3 if cls==ue.Vector else 2]) for v in result if isinstance(v,cls)]
            def triangle(data,tid):
                p=vectors(query.get_triangle_positions(data,tid),ue.Vector)
                n=vectors(query.get_triangle_normals(data,tid),ue.Vector)
                uv=vectors(query.get_triangle_u_vs(data,0,tid),ue.Vector2D)
                m,valid=ue.GeometryScript_Materials.get_triangle_material_id(data,tid);assert valid
                assert len(p)==len(n)==len(uv)==3
                return m,p,n,uv
            key=lambda m,p,n,u:(m,p,n,u)
            pixels={clip:{} for clip in ('walk','idle')}
            for tid in range(static.get_triangle_count()):
                m,ps,normals,uvs=triangle(static,tid)
                for clip in pixels:
                    layout=old_row[clip+'Bake']
                    vat_uvs=vectors(query.get_triangle_u_vs(static,layout['uvChannel'],tid),ue.Vector2D)
                    for p,n,u,b in zip(ps,normals,uvs,vat_uvs):
                        x,y=b[0]*layout['width'],b[1]*layout['height'];px,py=int(x),int(y)
                        assert abs(x-px-.5)<.002 and abs(y-py-.5)<.002 and 0<=py<layout['rowsPerFrame']
                        identity=key(m,p,n,u);value=(px,py)
                        assert identity not in pixels[clip] or pixels[clip][identity]==value
                        pixels[clip][identity]=value
            assert set(pixels['walk'])==set(pixels['idle'])
            samples={};seen=set()
            for tid in range(dynamic.get_triangle_count()):
                m,ps,normals,uvs=triangle(dynamic,tid)
                corners=[]
                for corner,(p,n,u) in enumerate(zip(ps,normals,uvs)):
                    identity=key(m,p,n,u);assert identity in pixels['walk']
                    if identity not in seen:corners.append((corner,identity));seen.add(identity)
                if corners:samples[tid]=(m,uvs,corners)
            assert seen==set(pixels['walk'])
            for clip in pixels:assert len(set(pixels[clip].values()))==len(seen)
            report['correspondence']=dict(uniqueRows=len(seen),sampledTriangles=len(samples),sourceTriangles=dynamic.get_triangle_count(),staticTriangles=static.get_triangle_count(),method='Exact reference material/position/normal/UV0 key; independent native UV1 and UV2 readback; posed UV/material correspondence checked every sampled triangle and frame.')
            actor=actors.spawn_actor_from_class(ue.SkeletalMeshActor,ue.Vector(),ue.Rotator(),transient=True);assert actor
            component=actor.skeletal_mesh_component;component.set_mobility(ue.ComponentMobility.MOVABLE);component.set_skeletal_mesh_asset(source)
            copy_options=ue.GeometryScriptCopyMeshFromComponentOptions(want_normals=True,want_tangents=False,requested_lod=lod)
            report['normalClips']={};pngs={}
            # UObjects survive Python reference deletion until Unreal GC. Reuse
            # one native mesh so long clips do not accumulate hundreds of copies.
            posed=ue.DynamicMesh()
            for clip_name in ('walk','idle'):
                layout=old_row[clip_name+'Bake'];clip=ue.load_asset(old['clips'][clip_name]);assert clip
                width,height=layout['width'],layout['height'];pixels_per_frame=width*layout['rowsPerFrame']
                buffer=bytearray(width*height*8);frame_reports=[];start=time.monotonic()
                for frame in range(layout['frames']):
                    assert ue.MikdashAnimationReviewLibrary.evaluate_review_pose(component,clip,frame/layout['sampleRateHz'])
                    assert vat._outcome_ok(ue,ue.GeometryScript_SceneUtils.copy_mesh_from_component(component,posed,copy_options,False))
                    assert posed.get_triangle_count()==dynamic.get_triangle_count()
                    written=0
                    for tid,(material,reference_uv,corners) in samples.items():
                        uv=vectors(query.get_triangle_u_vs(posed,0,tid),ue.Vector2D)
                        m,valid=ue.GeometryScript_Materials.get_triangle_material_id(posed,tid);assert valid and m==material and uv==reference_uv
                        normals=vectors(query.get_triangle_normals(posed,tid),ue.Vector);assert len(normals)==3
                        for corner,identity in corners:
                            n=normals[corner];length=math.sqrt(sum(v*v for v in n));assert math.isfinite(length) and length>1e-8
                            encoded=[max(0,min(65535,round((v/length+1.)*.5*65535))) for v in n]
                            x,y=pixels[clip_name][identity];texel=(frame*layout['rowsPerFrame']+y)*width+x
                            struct.pack_into('>4H',buffer,texel*8,*encoded,0);written+=1
                    assert written==len(seen)
                    frame_data=buffer[frame*pixels_per_frame*8:(frame+1)*pixels_per_frame*8]
                    frame_reports.append(dict(frame=frame,timeSeconds=frame/layout['sampleRateHz'],writtenTexels=written,rgba16BigEndianSha256=hashlib.sha256(frame_data).hexdigest()))
                    if frame%12==0:
                        report['progress']=dict(clip=clip_name,completedFrames=frame+1,totalFrames=layout['frames'],elapsedSeconds=time.monotonic()-start);write();ue.log('Direct resident normals: '+str(report['progress']))
                def chunk(name,payload):return struct.pack('>I',len(payload))+name+payload+struct.pack('>I',zlib.crc32(name+payload)&0xffffffff)
                raw=b''.join(b'\0'+buffer[y*width*8:(y+1)*width*8] for y in range(height))
                png=folder/('direct-'+stamp+'-'+clip_name+'.png');assert not png.exists()
                png.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,16,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
                pngs[clip_name]=png;report['files'][png.name]=sha(png)
                report['normalClips'][clip_name]=dict(frames=frame_reports,width=width,height=height,elapsedSeconds=time.monotonic()-start,sourcePNG=png.name)
                del buffer,raw
                write()
            actors.destroy_actor(actor);actor=None
            row=json.loads(json.dumps(old_row));row['target']='direct-normal-source';row['textures']=dict(old_row['textures']);row['slots']=[];row['materialInstances']={}
            for clip_name,png in pngs.items():
                task=ue.AssetImportTask()
                for name,value in dict(filename=str(png),destination_path=ns+'/Textures',destination_name='T_'+clip_name.title()+'Normal',automated=True,replace_existing=False,save=False).items():task.set_editor_property(name,value)
                ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);textures=[o for o in task.get_objects() if isinstance(o,ue.Texture2D)];assert len(textures)==1
                texture=textures[0]
                for name,value in dict(srgb=False,compression_settings=ue.TextureCompressionSettings.TC_HDR,filter=ue.TextureFilter.TF_NEAREST,mip_gen_settings=ue.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True,address_x=ue.TextureAddress.TA_WRAP,address_y=ue.TextureAddress.TA_WRAP,flip_green_channel=False).items():texture.set_editor_property(name,value);assert texture.get_editor_property(name)==value
                assert assets.save_loaded_asset(texture,False)
                row['textures'][clip_name.title()+'Normal']=texture.get_path_name()
            mesh=assets.duplicate_asset(original.get_path_name(),ns+'/SM_ResidentDirectNormals');assert mesh
            for i,name,path in old_row['slots']:
                original_mi=ue.load_asset(path);mi=assets.duplicate_asset(path,ns+'/Materials/'+original_mi.get_name());assert mi
                expected=dict(old_row['materialInstances'][original_mi.get_name()])
                for clip_name in ('Walk','Idle'):
                    parameter=clip_name+'NormalTexture';new_path=row['textures'][clip_name+'Normal']
                    ml.set_material_instance_texture_parameter_value(mi,parameter,ue.load_asset(new_path));expected[parameter]=new_path
                assert assets.save_loaded_asset(mi,False);mesh.set_material(i,mi)
                row['slots'].append([i,name,mi.get_path_name()]);row['materialInstances'][mi.get_name()]=expected
            assert assets.save_loaded_asset(mesh,False)
            row['mesh']=mesh.get_path_name();assert mesh_stats(mesh)==old_row['stats'];report['variants']=[row]
            report['assets']={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/('Content/MikdashV3/Runtime/CrowdResidentStudy'+study)/'Cast'/variant).rglob('*.uasset')}
            assert len(report['assets'])==9
            report['status']='built-needs-fresh-readback-and-render'
        else:
            receipt_path=next(p for p in folder.glob('native-*.json') if json.loads(p.read_text()).get('status')=='built-needs-fresh-readback-and-render')
            receipt=json.loads(receipt_path.read_text());report['buildReceipt']=receipt_path.name
            for p,h in receipt['assets'].items():assert sha(ROOT/p)==h
            for name,h in receipt['files'].items():assert sha(folder/name)==h
            row=receipt['variants'][0];mesh=ue.load_asset(row['mesh']);assert mesh and mesh_stats(mesh)==row['stats']
            def geometry_digest(asset):
                data=ue.DynamicMesh()
                options=ue.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=False,use_build_scale=True)
                lod=ue.GeometryScriptMeshReadLOD(lod_type=ue.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)
                assert vat._outcome_ok(ue,ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(asset,data,options,lod))
                q=ue.GeometryScript_MeshQueries;digest=hashlib.sha256()
                assert q.get_num_uv_sets(data)==3
                for tid in range(data.get_triangle_count()):
                    material,valid=ue.GeometryScript_Materials.get_triangle_material_id(data,tid);assert valid
                    values=[]
                    for result,cls,fields in [(q.get_triangle_positions(data,tid),ue.Vector,('x','y','z')),(q.get_triangle_normals(data,tid),ue.Vector,('x','y','z'))]+[(q.get_triangle_u_vs(data,channel,tid),ue.Vector2D,('x','y')) for channel in range(3)]+[(q.get_triangle_vertex_colors(data,tid),ue.LinearColor,('r','g','b','a'))]:
                        assert True in result
                        items=[v for v in result if isinstance(v,cls)];assert len(items)==3
                        values.extend(float(getattr(v,f)) for v in items for f in fields)
                    assert len(values)==48;digest.update(struct.pack('<i48d',material,*values))
                return digest.hexdigest()
            original=ue.load_asset(old['variants'][0]['mesh']);assert original
            report['geometryDigest']=dict(source=geometry_digest(original),candidate=geometry_digest(mesh),scope='Ordered material IDs, triangle positions/normals, UV0/1/2 and RGBA vertex colors')
            assert report['geometryDigest']['source']==report['geometryDigest']['candidate']
            for direction in ('positive','negative'):assert vat._v3(mesh.get_editor_property(direction+'_bounds_extension'))==vat._v3(original.get_editor_property(direction+'_bounds_extension'))
            for i,name,path in row['slots']:
                mi=mesh.get_material(i);assert mi.get_path_name()==path
                assert mi.get_editor_property('parent')==original.get_material(i).get_editor_property('parent')
                for parameter,value in row['materialInstances'][mi.get_name()].items():
                    if isinstance(value,str):assert ml.get_material_instance_texture_parameter_value(mi,parameter).get_path_name()==value
                    elif isinstance(value,list):
                        actual=ml.get_material_instance_vector_parameter_value(mi,parameter);assert all(abs(a-b)<1e-5 for a,b in zip((actual.r,actual.g,actual.b),value))
                    else:assert abs(ml.get_material_instance_scalar_parameter_value(mi,parameter)-value)<1e-5
            for clip_name in ('walk','idle'):
                texture=ue.load_asset(row['textures'][clip_name.title()+'Normal']);layout=row[clip_name+'Bake']
                assert texture.blueprint_get_size_x()==layout['width'] and texture.blueprint_get_size_y()==layout['height']
                for name,value in dict(srgb=False,compression_settings=ue.TextureCompressionSettings.TC_HDR,filter=ue.TextureFilter.TF_NEAREST,mip_gen_settings=ue.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True,address_x=ue.TextureAddress.TA_WRAP,address_y=ue.TextureAddress.TA_WRAP,flip_green_channel=False).items():assert texture.get_editor_property(name)==value
                png=folder/('readback-'+stamp+'-'+clip_name+'.png');assert not png.exists()
                task=ue.AssetExportTask()
                for name,value in dict(object=texture,filename=str(png),exporter=ue.TextureExporterPNG(),automated=True,prompt=False,replace_identical=False).items():task.set_editor_property(name,value)
                assert ue.Exporter.run_asset_export_task(task) and png.is_file();report['files'][png.name]=sha(png)
            report.update(variants=receipt['variants'],assets=receipt['assets'],normalClips=receipt['normalClips'],status='verified-fresh-candidate-not-rendered')
    except Exception as error:
        report.update(status='failed',error=repr(error));raise
    finally:
        if actor:actors.destroy_actor(actor)
        report['protectedUnchanged']=all(sha(ROOT/p)==h for p,h in protected.items())
        if not report['protectedUnchanged']:report['status']='failed-protected-changed'
        write()

if __name__=='__main__':run()

"""Read-only source audit / fresh wall twins for the authored S5 gate passages.

No map writes. Native boolean subtraction retains source attributes and material
slots, and closes the cut wall edges. Original assets are hash-protected.
"""
import json
import math
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from release_haram_precinct import ROOT, OUT, MAP, sha, disk, position_keys
from release_precinct_terrain_cut import Native

NS='/Game/MikdashV3/HaramWallPassagesV1'

def limits(g):
    return (-242.,242.,-200.,g['runCm']+150.,min(g['thresholdZCm'],.5)-100.,max(g['thresholdZCm'],.5)+350.)

def local(p,g):
    x,y=p[0]-g['positionCm'][0],p[1]-g['positionCm'][1]
    return (x*g['tangent'][0]+y*g['tangent'][1],x*g['inward'][0]+y*g['inward'][1],p[2])

def intersects(points,g):
    ps=[local(p,g) for p in points];bounds=limits(g)
    if not all(max(p[i] for p in ps)>bounds[2*i] and min(p[i] for p in ps)<bounds[2*i+1] for i in range(3)):return False
    if len(points)!=3:return True  # asset bounding-box broad phase
    for axis in range(3):
        for lower in (True,False):
            edge=bounds[2*axis+(0 if lower else 1)]
            out=[]
            for a,b in zip(ps,ps[1:]+ps[:1]):
                da=(a[axis]-edge)*(1 if lower else -1);db=(b[axis]-edge)*(1 if lower else -1)
                if da>=0:out.append(a)
                if (da>=0)!=(db>=0):
                    f=da/(da-db);out.append(tuple(a[i]+f*(b[i]-a[i]) for i in range(3)))
            ps=out
            if len(ps)<3:return False
    area=[0.,0.,0.]
    for a,b in zip(ps,ps[1:]+ps[:1]):
        for i in range(3):area[i]+=a[(i+1)%3]*b[(i+2)%3]-a[(i+2)%3]*b[(i+1)%3]
    return sum(v*v for v in area)>1e-8

def inside(p,g,margin=0):
    v=local(p,g);b=limits(g)
    return all(b[2*i]+margin<v[i]<b[2*i+1]-margin for i in range(3))

def main():
    import unreal as ue
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    platform_audit='-PlatformAudit' in ue.SystemLibrary.get_command_line()
    street_audit='-StreetAudit' in ue.SystemLibrary.get_command_line()
    audit='-WallAudit' in ue.SystemLibrary.get_command_line() or platform_audit or street_audit
    mode='audit' if audit else 'import'
    assert audit or '-WallImport' in ue.SystemLibrary.get_command_line()
    report={'status':'started','mode':mode,'scriptSha256':sha(Path(__file__))}
    receipt=OUT/('wall-'+mode+'-'+stamp+'.json')
    before=sha(disk(MAP,'.umap'))
    native=Native(ue,'Candidate48',mode,stamp)
    plan=json.loads((OUT/'plan.json').read_text())
    gates=plan['gates'];sources={}
    try:
        if audit:
            files=list((ROOT/'Content/MikdashV3/JerusalemContext/Streets').glob('*CityWalls*.uasset'))
            files+=list((ROOT/'Content/MikdashV3/FutureMountV1/KotelApproach').glob('*CityWalls*.uasset'))
            if platform_audit:
                files=[ROOT/'Content/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface.uasset',ROOT/'Content/MikdashV3/CandidateKotelSkirtV2/SM_MountPlatform_Skirt_Notched.uasset']
            if street_audit:
                files=[ROOT/'Content/MikdashV3/JerusalemContext/Streets/SM_Jerusalem_StonePaths_03_Grid_N002_N002.uasset']
            for file in files:
                path='/Game/'+file.relative_to(ROOT/'Content').with_suffix('').as_posix()
                mesh=ue.load_asset(path);bounds=mesh.get_bounding_box()
                points=[[x,y,z] for x in (bounds.min.x,bounds.max.x) for y in (bounds.min.y,bounds.max.y) for z in (bounds.min.z,bounds.max.z)]
                near=[g for g in gates if intersects(points,g)]
                if not near:continue
                triangles=native.extract(mesh)
                near=[g for g in near if any(intersects(t['positions'],g) for t in triangles)]
                if near:
                    sources[path]=dict(mesh=mesh,sha256=sha(file),triangles=triangles,gateIds=[g['osmId'] for g in near])
            assert native.levels.load_level(MAP)
            rows=json.loads((OUT/'wall-cuts.json').read_text())['walls'] if platform_audit or street_audit else []
            for actor in native.actors.get_all_level_actors():
                component=actor.get_component_by_class(ue.StaticMeshComponent)
                if not component or not component.static_mesh:continue
                path=component.static_mesh.get_path_name().split('.')[0]
                if path not in sources or actor.get_editor_property('hidden') or not actor.get_actor_enable_collision():continue
                transform=actor.get_actor_transform();identity=ue.Transform()
                assert transform.translation==identity.translation and transform.rotation==identity.rotation and transform.scale3d==identity.scale3d
                src=sources[path]
                name=component.static_mesh.get_name()
                source_file='wall-source-'+name+'.json'
                (OUT/source_file).write_text(json.dumps(src['triangles']))
                rows.append(dict(label=actor.get_actor_label(),mesh=path,sha256=src['sha256'],sourceFile=source_file,
                                 sourceSha256=sha(OUT/source_file),gateIds=src['gateIds'],
                                 twin=NS+'/'+name+'_HaramPassages',tags=[str(t) for t in actor.tags]))
            assert rows
            (OUT/'wall-sources.json').write_text(json.dumps(dict(mapSha256=before,walls=rows),indent=2)+'\n')
            report['walls']=rows
        else:
            specs=json.loads((OUT/'wall-sources.json').read_text())['walls']
            report['walls']=[]
            for spec in specs:
                assert sha(disk(spec['mesh']))==spec['sha256']
                assert sha(OUT/spec['sourceFile'])==spec['sourceSha256']
                source=ue.load_asset(spec['mesh']);sources[spec['mesh']]=dict(sha256=spec['sha256'])
                if native.assets.does_asset_exist(spec['twin']):
                    saved=next(w for w in json.loads((OUT/'wall-cuts.json').read_text())['walls'] if w['twin']==spec['twin'])
                    assert saved['sha256']==spec['sha256'] and sha(disk(spec['twin']))==saved['twinSha256']
                    report['walls'].append(saved)
                    continue  # Reuse only previously hash-pinned twins; never overwrite.
                expected=json.loads((OUT/spec['sourceFile']).read_text())
                assert position_keys(t['positions'] for t in native.extract(source))==position_keys(t['positions'] for t in expected)
                relevant=[g for g in gates if g['osmId'] in spec['gateIds'] and any(intersects(t['positions'],g) for t in expected)]
                spec=dict(spec,gateIds=[g['osmId'] for g in relevant])
                assert not native.assets.does_asset_exist(spec['twin']), 'Fresh twins only'
                dynamic=ue.DynamicMesh();options=ue.GeometryScriptCopyMeshFromAssetOptions()
                options.set_editor_property('apply_build_settings',False)
                options.set_editor_property('use_build_scale',False)
                lod=ue.GeometryScriptMeshReadLOD();lod.set_editor_property('lod_type',ue.GeometryScriptLODType.SOURCE_MODEL)
                assert ue.GeometryScriptOutcomePins.SUCCESS in native.asset_utils.copy_mesh_from_static_mesh_v2(source,dynamic,options,lod)
                for gate in relevant:
                    u0,u1,d0,d1,z0,z1=limits(gate);d=(d0+d1)/2
                    q=gate['positionCm'];v=gate['inward'];t=gate['tangent']
                    tool=ue.DynamicMesh()
                    transform=ue.Transform(location=ue.Vector(q[0]+v[0]*d,q[1]+v[1]*d,z0),rotation=ue.Rotator(pitch=0,yaw=math.degrees(math.atan2(t[1],t[0])),roll=0))
                    ue.GeometryScript_Primitives.append_box(tool,ue.GeometryScriptPrimitiveOptions(),transform,u1-u0,d1-d0,z1-z0)
                    corners=[local([p.x,p.y,p.z],gate) for tid in range(tool.get_triangle_count()) for p in native.query.get_triangle_positions(tool,tid) if isinstance(p,ue.Vector)]
                    measured=[value for i in range(3) for value in (min(p[i] for p in corners),max(p[i] for p in corners))]
                    assert max(abs(a-b) for a,b in zip(measured,limits(gate)))<.01, ('Cutter transform',measured,limits(gate))
                    opts=ue.GeometryScriptMeshBooleanOptions();opts.set_editor_property('simplify_output',False)
                    is_open_surface=any(s in spec['mesh'] for s in ('SM_MountPlatform_', 'SM_Jerusalem_StonePaths_'))
                    opts.set_editor_property('fill_holes',not is_open_surface)
                    operation=ue.GeometryScriptBooleanOperation.TRIM_INSIDE if is_open_surface else ue.GeometryScriptBooleanOperation.SUBTRACT
                    ue.GeometryScript_MeshBooleans.apply_mesh_boolean(dynamic,ue.Transform(),tool,ue.Transform(),operation,opts)
                options=ue.GeometryScriptCreateNewStaticMeshAssetOptions()
                for key,value in dict(enable_recompute_normals=False,enable_recompute_tangents=True,enable_nanite=native.nanite_enabled(source),enable_collision=True,collision_mode=ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,use_original_vertex_order=True).items():options.set_editor_property(key,value)
                result=native.creator.create_new_static_mesh_asset_from_mesh(dynamic,spec['twin'],options)
                assert ue.GeometryScriptOutcomePins.SUCCESS in result
                twin=next(x for x in result if isinstance(x,ue.StaticMesh))
                for index,slot in enumerate(source.get_editor_property('static_materials')):twin.set_material(index,slot.material_interface)
                ns=twin.get_editor_property('nanite_settings');ns.set_editor_property('fallback_target',ue.NaniteFallbackTarget.PERCENT_TRIANGLES);ns.set_editor_property('fallback_percent_triangles',1.);ns.set_editor_property('fallback_relative_error',0.);twin.set_editor_property('nanite_settings',ns)
                actual=native.extract(twin)
                (OUT/('wall-boolean-debug-'+source.get_name()+'.json')).write_text(json.dumps(actual))
                # Untouched triangles must survive by full position identity.
                untouched=[t for t in expected if not any(intersects(t['positions'],g) for g in relevant)]
                have=position_keys(t['positions'] for t in actual);want=position_keys(t['positions'] for t in untouched)
                assert not want-have, 'Boolean changed wall outside passage bounds: '+str(list((want-have).items())[:3])
                assert all(not any(inside([sum(p[i] for p in t['positions'])/3 for i in range(3)],g,1) for g in relevant) for t in actual), 'Wall remains inside passage'
                assert position_keys(t['positions'] for t in actual)!=position_keys(t['positions'] for t in expected), 'No wall geometry changed'
                assert native.assets.save_loaded_asset(twin,only_if_is_dirty=False)
                read_file='wall-result-'+twin.get_name()+'.json';(OUT/read_file).write_text(json.dumps(actual))
                row=dict(spec,trianglesBefore=len(expected),trianglesAfter=len(actual),unchangedTriangles=len(untouched),resultFile=read_file,resultSha256=sha(OUT/read_file),twinSha256=sha(disk(spec['twin'])))
                report['walls'].append(row);receipt.write_text(json.dumps(report,indent=2)+'\n')
            (OUT/'wall-cuts.json').write_text(json.dumps(dict(walls=report['walls']),indent=2)+'\n')
        report['status']='passed'
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();ue.log_error(report['error'])
    finally:
        report['mapSha256Before']=before;report['mapSha256After']=sha(disk(MAP,'.umap'))
        report['originalHashesUnchanged']=all(sha(disk(path))==src['sha256'] for path,src in sources.items())
        if before!=report['mapSha256After'] or not report['originalHashesUnchanged']:report['status']='failed-hash-guard'
        receipt.write_text(json.dumps(report,indent=2)+'\n');ue.SystemLibrary.quit_editor()

if __name__=='__main__':main()

"""Original palm architectural relief. Offline --export; explicit run_native(materials).

No engine calls on import, no map changes, no new material creation. The partial
palm study does not supply the cherubim required for a complete Ezekiel 41 scheme.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/sanctuary-detail/PalmReliefV1'
DEST = '/Game/MikdashV3/MaterialReview/SanctuaryPalmReliefV1'


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def volume(vertices, faces):
    return sum(sum(vertices[a][i]*cross(vertices[b], vertices[c])[i] for i in range(3))/6 for a,b,c in faces)


def curved_blade(start, control, end, width, depth, segments=18):
    """Closed tapered carved ribbon with pointed ends and elliptical bevels.

    Width is in the panel's XZ plane; depth is Y. No zero-width duplicate poles.
    """
    vertices = [tuple(start)]
    rings = [[0]]
    for j in range(1, segments):
        t = j/segments
        p = [(1-t)**2*start[i]+2*(1-t)*t*control[i]+t*t*end[i] for i in range(3)]
        dx = 2*((1-t)*(control[0]-start[0])+t*(end[0]-control[0]))
        dz = 2*((1-t)*(control[2]-start[2])+t*(end[2]-control[2]))
        length = math.hypot(dx,dz)
        assert length > 1e-8
        taper = math.sin(math.pi*t)**0.65
        ring = []
        for k in range(8):
            a = math.tau*k/8
            ring.append(len(vertices))
            vertices.append((p[0]-dz/length*width*taper*math.cos(a),
                             p[1]+depth*taper*math.sin(a),
                             p[2]+dx/length*width*taper*math.cos(a)))
        rings.append(ring)
    rings.append([len(vertices)])
    vertices.append(tuple(end))
    faces = []
    for a,b in zip(rings,rings[1:]):
        for k in range(8):
            n = (k+1)%8
            if len(a)==1: faces.append((a[0],b[k],b[n]))
            elif len(b)==1: faces.append((a[k],b[0],a[n]))
            else: faces.extend([(a[k],b[k],b[n]),(a[k],b[n],a[n])])
    if volume(vertices,faces)<0: faces = [(a,c,b) for a,b,c in faces]
    return vertices,faces


def geometry():
    spec = importlib.util.spec_from_file_location('_sanctuary_bevel', ROOT/'Scripts/create_heikhal_keilim.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    backing = [('Panel',helper.bevel_box((0,0.8,130),(120,1.6,260),0.35))]
    # Narrow layered carved border leaves room around the palm silhouette.
    for name,center,size in [('Left',(-57,2.0,130),(3,2.2,254)),('Right',(57,2.0,130),(3,2.2,254)),
                             ('Bottom',(0,2,3),(112,2.2,3)),('Top',(0,2,257),(112,2.2,3))]:
        backing.append(('Moulding'+name,helper.bevel_box(center,size,0.45)))
    palm = [('Trunk',curved_blade((0,3,18),(-3,3.8,104),(0,3.8,183),5.3,2.3,48))]
    # Low-profile diagonal scars; individual editable carving pieces.
    for j in range(15):
        z=32+j*8.6
        for sign in (-1,1):
            palm.append(('TrunkScar_%02d_%s'%(j,sign),curved_blade((0,5,z-2),(sign*2.8,5.6,z),(sign*4,4.4,z+4),.8,.6,8)))
    crown=(0,4,177)
    # Three ascending and three drooping fronds on each side; no copied motif.
    for side in (-1,1):
        for f,(reach,lift,control_lift) in enumerate([(22,63,55),(38,48,60),(49,25,49),(49,1,32),(42,-21,14),(28,-34,0)]):
            end=(side*reach,3.5,177+lift)
            ctl=(side*reach*.48,4.6,177+control_lift)
            palm.append(('FrondRib_%s_%d'%(side,f),curved_blade(crown,ctl,end,1.35,.85,24)))
            for n in range(2,10):
                t=n/11
                p=[(1-t)**2*crown[i]+2*(1-t)*t*ctl[i]+t*t*end[i] for i in range(3)]
                dx=2*((1-t)*(ctl[0]-crown[0])+t*(end[0]-ctl[0]))
                dz=2*((1-t)*(ctl[2]-crown[2])+t*(end[2]-ctl[2]))
                norm=math.hypot(dx,dz)
                for leaf_side in (-1,1):
                    length=8.5*(1-.62*t)
                    tip=(p[0]+dx/norm*3+leaf_side*(-dz/norm)*length,
                         3.7,p[2]+dz/norm*3+leaf_side*(dx/norm)*length)
                    control=((p[0]+tip[0])/2,5,(p[2]+tip[2])/2+2)
                    palm.append(('Leaflet_%s_%d_%d_%s'%(side,f,n,leaf_side),curved_blade(p,control,tip,.8,.42,10)))
    palm.append(('CrownSpear',curved_blade((0,4,174),(2,4,220),(0,3.4,246),3.2,1.0,32)))
    return {'SM_CedarPalmBackingV1':backing,'SM_PalmCarvingV1':palm}


def export():
    assert not OUT.exists(), 'Preserve frozen source: use a new version for regeneration'
    meshes=geometry()
    OUT.mkdir(parents=True)
    report=dict(status='OFFLINE_VALIDATED_NATIVE_AND_VISUAL_PENDING',namespace=DEST,meshes=[],
        canonical_axes='Unreal XYZ cm: panel width X, outward projection +Y, vertical Z; bottom pivot',
        obj_adapter='Y reflected and triangle winding reversed for project legacy OBJ importer',
        helper_sha256=hashlib.sha256((ROOT/'Scripts/create_heikhal_keilim.py').read_bytes()).hexdigest())
    editable={}
    for name,parts in meshes.items():
        lines=['# Original editable palm relief; legacy Unreal OBJ adapter','o '+name]
        index=1
        all_vertices=[]
        part_reports=[]
        for part,(v,f) in parts:
            lines.append('g '+part)
            all_vertices.extend(v)
            edges={}
            keys=[tuple(round(x,6) for x in p) for p in v]
            for a,b,c in f:
                for i,j in ((a,b),(b,c),(c,a)):
                    key=tuple(sorted((keys[i],keys[j])))
                    edges[key]=edges.get(key,0)+1
                adapted=[(v[i][0],-v[i][1],v[i][2]) for i in (a,c,b)]
                p,q,r=adapted
                ab=[q[i]-p[i] for i in range(3)]; ac=[r[i]-p[i] for i in range(3)]
                normal=cross(ab,ac)
                nl=math.sqrt(sum(x*x for x in normal)); length=math.sqrt(sum(x*x for x in ab))
                assert nl>1e-8
                normal=tuple(x/nl for x in normal)
                for point in adapted: lines.append('v %.9f %.9f %.9f'%point)
                for uv in ((0,0),(length/10,0),(sum(ac[i]*ab[i]/length for i in range(3))/10,nl/length/10)):
                    lines.append('vt %.9f %.9f'%uv)
                for _ in range(3): lines.append('vn %.9f %.9f %.9f'%normal)
                lines.append('f '+' '.join('%d/%d/%d'%(k,k,k) for k in range(index,index+3)))
                index+=3
            vol=volume(v,f)
            assert vol>0 and all(n==2 for n in edges.values()), part
            part_reports.append(dict(name=part,triangles=len(f),signed_volume_cm3=vol,closed_edges=True))
        path=OUT/(name+'.obj')
        path.write_text('\n'.join(lines)+'\n',encoding='ascii')
        report['meshes'].append(dict(name=name,file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            triangles=(index-1)//3,parts=part_reports,bounds_cm={k:[fn(p[i] for p in all_vertices) for i in range(3)] for k,fn in [('min',min),('max',max)]}))
        editable[name]=[dict(name=n,vertices_cm=v,triangles=f) for n,(v,f) in parts]
    (OUT/'editable-meshes.json').write_text(json.dumps(editable,separators=(',',':'))+'\n')
    # Pull placement extents from the frozen measured sanctuary source, never the union exterior.
    manifest_path=ROOT/'SourceAssets/architecture-manifest.json'
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()=='40c4a0feae391868c6c840f76bc72f0df0bab8c3be9406c6b5dbb6f508f9333d'
    records=json.loads(manifest_path.read_text(encoding='utf-8-sig'))['meshes']
    floor=next(r['expectedBoundsUnrealCm'] for r in records if r['sourceName']=='Heichal clear floor')
    x=(floor['min'][0]+floor['max'][0])/2
    placements=[dict(wall='Heichal negative-Y inner face',location_cm=[x,-499.75,floor['max'][2]+40],yaw_degrees=0),
                dict(wall='Heichal positive-Y inner face',location_cm=[x,499.75,floor['max'][2]+40],yaw_degrees=180)]
    report['placement_proposals']=placements
    report['placement_status']='Two isolated review panels only; both meshes share each transform. No repeat scheme or map edits.'
    report['limitations']=['Palm motif only; cherubim absent, hence incomplete Ezekiel 41 wall scheme',
        '120 x 260cm module and all carving profiles are artistic, not text-measured',
        'Wood species cedar follows Rashi commentary; geometry has no wood texture',
        'Intersecting closed carving parts are intentional relief assembly, not a watertight Boolean union',
        'Per-triangle UV charts support flat materials; authored texture UV unwrap and LOD still needed',
        'Native shading, material choice, visual scale/readability, collision and performance unverified']
    (OUT/'geometry-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def run_native(materials):
    """Root only. materials maps both mesh names to EXISTING material asset paths.

    Saves isolated mesh assets; never spawns actors, saves maps or edits originals.
    """
    import unreal as ue
    assert Path(ue.Paths.project_dir()).resolve()==ROOT
    assert not ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world()
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    assert not assets.does_directory_exist(DEST), 'Existing namespace preserved'
    report=json.loads((OUT/'geometry-manifest.json').read_text())
    checked={}
    for record in report['meshes']:
        path=OUT/record['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
        material=ue.load_asset(materials[record['name']])
        assert isinstance(material,ue.MaterialInterface), 'Provide an existing reviewed material'
        checked[record['name']]=material
    receipt=dict(status='STARTED',map_changed=False,new_materials=False,meshes=[])
    try:
        for record in report['meshes']:
            ui=ue.FbxImportUI()
            for key,value in dict(automated_import_should_detect_type=False,mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
                import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=False).items():
                ui.set_editor_property(key,value)
            data=ui.get_editor_property('static_mesh_import_data')
            for key,value in dict(combine_meshes=True,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,
                convert_scene=False,convert_scene_unit=False,force_front_x_axis=False,import_uniform_scale=1.0,
                auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,
                normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items(): data.set_editor_property(key,value)
            task=ue.AssetImportTask()
            for key,value in dict(filename=str(OUT/record['file']),destination_path=DEST+'/Meshes',destination_name=record['name'],
                automated=True,async_=False,replace_existing=False,save=False,options=ui,factory=ue.FbxFactory()).items(): task.set_editor_property(key,value)
            ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            objects=list(task.get_objects())
            assert len(objects)==1 and isinstance(objects[0],ue.StaticMesh)
            mesh=objects[0]; bb=mesh.get_bounding_box()
            actual={'min':[bb.min.x,bb.min.y,bb.min.z],'max':[bb.max.x,bb.max.y,bb.max.z]}
            error=max(abs(actual[k][i]-record['bounds_cm'][k][i]) for k in actual for i in range(3))
            assert error<.05 and mesh.get_num_triangles(0)==record['triangles']
            for slot in range(len(mesh.get_editor_property('static_materials'))): mesh.set_material(slot,checked[record['name']])
            assert assets.save_loaded_asset(mesh,only_if_is_dirty=False)
            receipt['meshes'].append(dict(asset=mesh.get_path_name(),bounds_error_cm=error,triangles=mesh.get_num_triangles(0)))
        receipt['status']='SAVED_ASSETS_UNPLACED_VISUAL_REVIEW_PENDING'
    except Exception as error:
        receipt.update(status='FAILED_PARTIAL_ASSETS_PRESERVED',error=str(error))
        raise
    finally: (OUT/'native-import.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    if '--export' not in sys.argv: raise SystemExit('Use --export offline; native root calls run_native(materials) separately')
    result=export()
    print(json.dumps({r['name']:{'triangles':r['triangles'],'parts':len(r['parts']),'bounds':r['bounds_cm']} for r in result['meshes']},indent=2))

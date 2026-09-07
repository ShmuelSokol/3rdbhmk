"""Original BusStudyV1: offline editable geometry; explicit run_native imports only.

No scene placement or engine startup. Canonical coordinates: Unreal cm, +X front,
+Y door side, Z up, tire contact Z0. No manufacturer geometry, logo or livery.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/arrival-review/BusStudyV1'
DEST = '/Game/MikdashV3/ArrivalReview/BusStudyV1'
PALETTE = {
    'IvoryPaint': ([.78, .75, .65], .25, .28),
    'TealPaint': ([.025, .19, .20], .3, .3),
    'Rubber': ([.018, .022, .025], 0, .8),
    'Glass': ([.035, .085, .11], .25, .12),
    'Aluminium': ([.48, .51, .54], .85, .25),
    'DarkTrim': ([.028, .035, .04], .3, .42),
    'Headlamp': ([.85, .89, .8], .2, .18),
    'RedLens': ([.5, .015, .009], .1, .24),
    'AmberLens': ([.95, .35, .015], .1, .25),
}


def prism(poly, depth, axis, offset=(0, 0, 0)):
    """Closed extrusion of a convex 2D profile; output face winding normalized."""
    v = []
    for side in (-depth / 2, depth / 2):
        for a, b in poly:
            p = [a, b]
            p.insert(axis, side)
            v.append(tuple(p[i] + offset[i] for i in range(3)))
    n = len(poly)
    f = []
    for i in range(1, n - 1):
        f.extend([(0, i + 1, i), (n, n + i, n + i + 1)])
    for i in range(n):
        j = (i + 1) % n
        f.extend([(i, j, n + j), (i, n + j, n + i)])
    return orient(v, f)


def orient(v, f):
    volume = sum(dot(v[a], cross(v[b], v[c])) for a, b, c in f) / 6
    return v, [(a, c, b) for a, b, c in f] if volume < 0 else f


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def box(center, size, bevel=1.5):
    x, y, z = size
    r = min(bevel, x / 4, y / 4)
    poly = [(-x/2+r,-y/2),(x/2-r,-y/2),(x/2,-y/2+r),(x/2,y/2-r),
            (x/2-r,y/2),(-x/2+r,y/2),(-x/2,y/2-r),(-x/2,-y/2+r)]
    return prism(poly, z, 2, center)


def wheel_profile(x, y, profile, segments=64):
    """Surface of revolution around Y, closed profile; no overlapping pole verts."""
    v, rings, f = [], [], []
    for r, depth in profile:
        ring = []
        for i in range(1 if r == 0 else segments):
            a = math.tau*i/segments
            ring.append(len(v)); v.append((x+r*math.cos(a), y+depth, 50+r*math.sin(a)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]+rings[:1]):
        if len(a) == len(b) == 1:
            continue
        for i in range(segments):
            j = (i+1) % segments
            if len(a) == 1: f.append((a[0],b[i],b[j]))
            elif len(b) == 1: f.append((a[i],b[0],a[j]))
            else: f.extend([(a[i],b[i],b[j]),(a[i],b[j],a[j])])
    return orient(v, f)


def assembly():
    parts = []
    def add(name, mat, mesh):
        parts.append(dict(name=name, material=mat, vertices=mesh[0], triangles=mesh[1]))
    def b(name, mat, c, s, bevel=1.5): add(name, mat, box(c, s, bevel))
    b('Underfloor', 'DarkTrim', (0,0,77), (1150,216,24), 12)
    # Lower body skirt follows actual clear wheel arches instead of hiding tires.
    for side in (-1, 1):
        xs = sorted(set([-575,575] + list(range(-570,571,10)) + [-422,-298,298,422]))
        def lower(x):
            return max([65] + [50+math.sqrt(max(0,62**2-(x-a)**2)) for a in (-360,360) if abs(x-a)<62])
        for i,(a,c) in enumerate(zip(xs,xs[1:])):
            add('Skirt_%s_%03d'%(side,i),'TealPaint',prism([(a,lower(a)),(c,lower(c)),(c,137),(a,137)],7,1,(0,side*120,0)))
        b('BeltRail_%s'%side,'IvoryPaint',(0,side*120,147),(1150,9,22),3)
        b('UpperFascia_%s'%side,'IvoryPaint',(0,side*118,283),(1150,12,36),5)
        b('WindowGasket_%s'%side,'Rubber',(0,side*122,212),(1150,5,109),4)
        for i,(a,c) in enumerate([(-564,-407),(-397,-239),(-229,-71),(-61,97),(107,265),(275,433),(443,566)]):
            if side == 1 and i in (3,6): continue
            b('SideWindow_%s_%02d'%(side,i),'Glass',((a+c)/2,side*125,213),(c-a,2,94),3)
            b('WindowTopVent_%s_%02d'%(side,i),'Aluminium',((a+c)/2,side*126.5,244),(c-a-4,1,1.3),.3)
        for i,x in enumerate([-520,-200,140,510]):
            b('SideMarker_%s_%s'%(side,i),'AmberLens',(x,side*126,116),(8,2,4),1)
        for x in (-360,360):
            # Bead, curved shoulders, tread and separate machined rims.
            add('Tire_%s_%s'%(side,x),'Rubber',wheel_profile(x,side*108,[(30,-14),(43,-14),(48,-10),(50,-5),(50,5),(48,10),(43,14),(30,14)]))
            add('Rim_%s_%s'%(side,x),'Aluminium',wheel_profile(x,side*122,[(0,-2),(29,-2),(32,0),(32,3),(28,5),(20,2),(12,4),(0,4)]))
            for k in range(10):
                a=k*math.tau/10
                b('HubBolt_%s_%s_%s'%(side,x,k),'DarkTrim',(x+18*math.cos(a),side*128,50+18*math.sin(a)),(3,2,3),.5)
            # Raised tread blocks: small facets aid side/three-quarter close views.
            for k in range(48):
                a=k*math.tau/48
                for dy in (-5,5):
                    # Radius stays below ground contact envelope of the tire.
                    cx=x+49.5*math.cos(a);cz=50+49.5*math.sin(a)
                    tangent=(-math.sin(a),math.cos(a));radial=(math.cos(a),math.sin(a))
                    poly=[(cx+t*tangent[0]+r*radial[0],cz+t*tangent[1]+r*radial[1]) for t,r in [(-1.3,-.4),(1.3,-.4),(1.3,.25),(-1.3,.25)]]
                    add('Tread_%s_%s_%s_%s'%(side,x,k,dy),'Rubber',prism(poly,7,1,(0,side*108+dy,0)))
    # Formed roof with shallow rounded crown, separate HVAC equipment.
    add('RoofCrown','IvoryPaint',prism([(-123,296),(-115,308),(-85,314),(85,314),(115,308),(123,296)],1160,0))
    b('RoofHVAC','IvoryPaint',(-70,0,321),(330,165,18),20)
    for i in range(17): b('HVACLouvre_%02d'%i,'DarkTrim',(-215+i*18,0,331),(6,132,1.5),.5)
    # Nose and rear use rounded-corner extruded profiles; glass remains opaque study.
    for front in (-1,1):
        x=front*583
        add('EndLower_%s'%front,'IvoryPaint',prism([(-120,66),(120,66),(124,80),(124,157),(-124,157),(-124,80)],28,0,(x,0,0)))
        add('EndUpper_%s'%front,'DarkTrim',prism([(-124,157),(124,157),(119,282),(104,300),(-104,300),(-119,282)],18,0,(x,0,0)))
        add('EndGlass_%s'%front,'Glass',prism([(-112,170),(112,170),(106,267),(-106,267)],2,0,(front*594,0,0)))
        b('Bumper_%s'%front,'DarkTrim',(front*598,0,77),(10,246,17),4)
        b('Plate_%s'%front,'AmberLens',(front*604,0,99),(1.5,36,10),.5)
        for side in (-1,1):
            b('LightHousing_%s_%s'%(front,side),'DarkTrim',(front*599,side*88,120),(4,40,22),3)
            b('Lamp_%s_%s'%(front,side),'Headlamp' if front==1 else 'RedLens',(front*602,side*83,123),(2,21,12),3)
            b('Indicator_%s_%s'%(front,side),'AmberLens',(front*602,side*104,123),(2,9,12),2)
        b('DestinationPanel_%s'%front,'Rubber',(front*595,0,282),(2,156,19),2)
    # Two distinct twin-leaf passenger doors, flush glazing and visible handles.
    for door,x,w in [('Front',506,116),('Middle',18,142)]:
        b('DoorFrame_'+door,'Rubber',(x,127,163),(w+8,4,199),2)
        for leaf in (-1,1):
            cx=x+leaf*w/4
            b('DoorGlass_%s_%s'%(door,leaf),'Glass',(cx,130,167),(w/2-5,2,174),1)
            b('DoorLower_%s_%s'%(door,leaf),'TealPaint',(cx,131,85),(w/2-5,2,16),1)
            b('DoorHandle_%s_%s'%(door,leaf),'Aluminium',(x+leaf*7,133,153),(2,3,18),.5)
        b('DoorThreshold_'+door,'Aluminium',(x,130,64),(w,9,3),1)
    for side in (-1,1):
        b('MirrorArm_%s'%side,'DarkTrim',(556,side*143,252),(10,43,5),2)
        b('MirrorCase_%s'%side,'DarkTrim',(550,side*166,235),(16,12,34),4)
        b('MirrorFace_%s'%side,'Aluminium',(541,side*166,235),(1,9,28),2)
    for y in (-49,49):
        b('Wiper_%s'%y,'DarkTrim',(596,y,188),(2,3,48),.6)
    for i in range(12): b('RearVent_%02d'%i,'DarkTrim',(-600,-66+i*12,147),(2,6,11),1)
    return parts


def bounds(vertices):
    return {k:[fn(v[i] for v in vertices) for i in range(3)] for k,fn in [('min',min),('max',max)]}


def write_obj(path, parts, native):
    lines=['# Original BusStudyV1; cm; '+('Unreal legacy reflected-Y adapter' if native else 'canonical Unreal XYZ')]
    n=1
    for p in parts:
        lines.append('g '+p['name']);lines.append('s off')
        for face in p['triangles']:
            a,b,c=[p['vertices'][i] for i in face]
            if native:a,b,c=[(v[0],-v[1],v[2]) for v in (a,c,b)]
            ab=tuple(b[i]-a[i] for i in range(3));ac=tuple(c[i]-a[i] for i in range(3))
            normal=cross(ab,ac);length=math.sqrt(dot(normal,normal));edge=math.sqrt(dot(ab,ab))
            uv=[(0,0),(edge/100,0),(dot(ac,ab)/edge/100,length/edge/100)]
            lines.extend('v %.8f %.8f %.8f'%v for v in (a,b,c))
            lines.extend('vt %.8f %.8f'%v for v in uv)
            lines.extend(['vn %.9f %.9f %.9f'%tuple(v/length for v in normal)]*3)
            lines.append('f '+' '.join('%d/%d/%d'%(i,i,i) for i in range(n,n+3)));n+=3
    path.write_text('\n'.join(lines)+'\n',encoding='ascii')


def preview(parts):
    # A depth buffer is necessary: sorting large mesh faces gives false artifacts.
    import runpy
    runpy.run_path(str(ROOT/'SourceAssets/arrival-review/render_offline_preview.py'))
    (OUT/'geometry-preview.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1300" height="820"><rect width="1300" height="820" fill="#c4cbd0"/><image href="geometry-preview.png" width="1300" height="760"/><text x="30" y="790" font-family="sans-serif" font-size="18">Original BusStudyV1 - offline geometry preview; native lighting, collision and motion unverified.</text></svg>',encoding='utf-8')


def export():
    if OUT.exists(): raise RuntimeError('Version exists; preserve evidence and author a new version')
    parts=assembly();checks=[]
    for p in parts:
        v,f=p['vertices'],p['triangles'];edges={};minimum=1e30
        for a,b,c in f:
            assert len({a,b,c})==3
            ab=[v[b][i]-v[a][i] for i in range(3)];ac=[v[c][i]-v[a][i] for i in range(3)]
            area=math.sqrt(dot(cross(ab,ac),cross(ab,ac)))/2;minimum=min(minimum,area)
            assert area>1e-8,p['name']
            for i,j in [(a,b),(b,c),(c,a)]:
                key=tuple(sorted((i,j)));edges[key]=edges.get(key,0)+1
        assert all(n==2 for n in edges.values()),p['name']
        volume=sum(dot(v[a],cross(v[b],v[c])) for a,b,c in f)/6
        assert volume>0 and all(math.isfinite(c) for point in v for c in point),p['name']
        checks.append(dict(name=p['name'],closed_indexed_edges=True,signed_volume_cm3=volume,min_triangle_area_cm2=minimum))
    OUT.mkdir(parents=True)
    (OUT/'bus-editable.mesh.json').write_text(json.dumps(dict(units='centimeters',axis='Unreal XYZ +X front +Y door side',parts=parts),separators=(',',':'))+'\n')
    write_obj(OUT/'bus-canonical.obj',parts,False)
    records=[]
    for mat in PALETTE:
        selected=[p for p in parts if p['material']==mat];name='SM_BusStudyV1_'+mat;path=OUT/(name+'.obj')
        write_obj(path,selected,True)
        records.append(dict(name=name,material=mat,file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),triangles=sum(len(p['triangles']) for p in selected),bounds_cm=bounds([v for p in selected for v in p['vertices']])))
    report=dict(status='offline_geometry_pass_native_visual_pending',part_count=len(parts),triangles=sum(len(p['triangles']) for p in parts),bounds_cm=bounds([v for p in parts for v in p['vertices']]),checks=checks,imports=records,palette=PALETTE)
    (OUT/'offline-checks.json').write_text(json.dumps(report,indent=2)+'\n');preview(parts)
    print(json.dumps({k:report[k] for k in ['status','part_count','triangles','bounds_cm']},indent=2))


def run_native():
    """ROOT ONLY: assets-only import; no actor/map operations or collision promises."""
    import unreal as ue
    assert Path(ue.Paths.project_dir()).resolve()==ROOT
    assert not ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    assert not assets.does_directory_exist(DEST),'Preserve partial/native previous attempt'
    report=json.loads((OUT/'offline-checks.json').read_text());receipt=dict(status='started',created=[])
    try:
        tools=ue.AssetToolsHelpers.get_asset_tools();ml=ue.MaterialEditingLibrary
        materials={}
        for name,(color,metal,rough) in report['palette'].items():
            mat=tools.create_asset('M_BusStudyV1_'+name,DEST+'/Materials',ue.Material,ue.MaterialFactoryNew())
            node=ml.create_material_expression(mat,ue.MaterialExpressionConstant3Vector)
            node.set_editor_property('constant',ue.LinearColor(*color,1))
            assert ml.connect_material_property(node,'',ue.MaterialProperty.MP_BASE_COLOR)
            for value,prop in [(metal,ue.MaterialProperty.MP_METALLIC),(rough,ue.MaterialProperty.MP_ROUGHNESS)]:
                node=ml.create_material_expression(mat,ue.MaterialExpressionConstant);node.set_editor_property('r',value)
                assert ml.connect_material_property(node,'',prop)
            ml.recompile_material(mat);assert assets.save_loaded_asset(mat,only_if_is_dirty=False)
            materials[name]=mat;receipt['created'].append(mat.get_path_name())
        for rec in report['imports']:
            path=OUT/rec['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==rec['sha256']
            ui=ue.FbxImportUI()
            for key,value in dict(automated_import_should_detect_type=False,mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=False).items():ui.set_editor_property(key,value)
            data=ui.get_editor_property('static_mesh_import_data')
            for key,value in dict(combine_meshes=True,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,convert_scene=False,convert_scene_unit=False,force_front_x_axis=False,import_uniform_scale=1.0,auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():data.set_editor_property(key,value)
            task=ue.AssetImportTask()
            for key,value in dict(filename=str(path),destination_path=DEST+'/Meshes',destination_name=rec['name'],automated=True,async_=False,replace_existing=False,save=False,options=ui,factory=ue.FbxFactory()).items():task.set_editor_property(key,value)
            tools.import_asset_tasks([task]);objects=list(task.get_objects())
            assert len(objects)==1 and isinstance(objects[0],ue.StaticMesh)
            mesh=objects[0];bb=mesh.get_bounding_box();actual=dict(min=[bb.min.x,bb.min.y,bb.min.z],max=[bb.max.x,bb.max.y,bb.max.z])
            assert max(abs(actual[k][i]-rec['bounds_cm'][k][i]) for k in actual for i in range(3))<.05
            assert mesh.get_num_triangles(0)==rec['triangles']
            mesh.set_material(0,materials[rec['material']]);assert assets.save_loaded_asset(mesh,only_if_is_dirty=False)
            receipt['created'].append(mesh.get_path_name())
        receipt['status']='assets_saved_unplaced_native_visual_collision_motion_pending'
    except Exception as exc:
        receipt.update(status='failed_partial_assets_preserved',error=str(exc));raise
    finally:(OUT/'native-import.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',action='store_true');args=parser.parse_args()
    if args.export: export()
    else: parser.error('Use --export offline; root invokes run_native() separately')

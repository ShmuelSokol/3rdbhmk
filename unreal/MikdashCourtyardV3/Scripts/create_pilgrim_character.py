"""Original civilian garment/character study. Offline export; native import is explicit.

No engine launch, no map mutation. This is an editable static art study, NOT a
skinned crowd character or historical/halachic garment certification.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/PilgrimStudyV1'
DEST = '/Game/MikdashV3/CharacterReview/PilgrimStudyV1'
MATERIALS = {
    'Skin': ((.47, .265, .155), .72),
    'Linen': ((.63, .55, .39), .93),
    'Mantle': ((.16, .235, .215), .94),
    'Headwrap': ((.72, .68, .54), .95),
    'Leather': ((.115, .06, .028), .81),
    'Hair': ((.075, .035, .018), .90),
    'Eyes': ((.28, .20, .115), .55),
    'Trim': ((.37, .28, .13), .91),
}


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def sub(a, b):
    return tuple(a[i]-b[i] for i in range(3))


def dot(a, b):
    return sum(a[i]*b[i] for i in range(3))


def normalize(a):
    length = math.sqrt(dot(a, a))
    return tuple(v/length for v in a)


def loft(rings, segments=40, folds=0, fold_size=0, cap=True):
    """Horizontal anatomical/cloth profiles (z, width, depth, x, y); welded caps."""
    vertices, faces = [], []
    for level, (z, rx, ry, cx, cy) in enumerate(rings):
        for i in range(segments):
            t = i*math.tau/segments
            f = fold_size*math.cos(folds*t + .12*level) if folds else 0
            vertices.append((cx+(rx+f)*math.cos(t), cy+(ry+f)*math.sin(t), z))
    for j in range(len(rings)-1):
        for i in range(segments):
            a=j*segments+i; b=j*segments+(i+1)%segments; c=b+segments; d=a+segments
            faces.extend([(a,b,c),(a,c,d)])
    if cap:
        for ring, reverse in [(0,True),(len(rings)-1,False)]:
            z,rx,ry,cx,cy=rings[ring]
            center=len(vertices); vertices.append((cx,cy,z))
            for i in range(segments):
                tri=(center,ring*segments+i,ring*segments+(i+1)%segments)
                faces.append(tuple(reversed(tri)) if reverse else tri)
    return vertices,faces


def ellipsoid(center, radii, segments=32, levels=20, sculpt=None):
    # Explicit poles avoid degenerate latitude triangles.
    v=[(center[0],center[1],center[2]-radii[2])]; f=[]
    for j in range(1,levels):
        latitude=-math.pi/2+j*math.pi/levels
        for i in range(segments):
            t=i*math.tau/segments
            p=(radii[0]*math.cos(latitude)*math.cos(t),radii[1]*math.cos(latitude)*math.sin(t),radii[2]*math.sin(latitude))
            if sculpt:p=sculpt(p)
            v.append(tuple(center[k]+p[k] for k in range(3)))
    top=len(v);v.append((center[0],center[1],center[2]+radii[2]))
    for i in range(segments):
        f.append((0,1+(i+1)%segments,1+i))
        f.append((top,1+(levels-2)*segments+i,1+(levels-2)*segments+(i+1)%segments))
    for j in range(levels-2):
        for i in range(segments):
            a=1+j*segments+i;b=1+j*segments+(i+1)%segments;c=b+segments;d=a+segments
            f.extend([(a,b,c),(a,c,d)])
    return v,f


def tube(points, radii, segments=16):
    v=[];f=[]
    for i,p in enumerate(points):
        tangent=normalize(sub(points[min(i+1,len(points)-1)],points[max(i-1,0)]))
        ref=(0,1,0) if abs(tangent[1])<.9 else (1,0,0)
        u=normalize(cross(ref,tangent));w=cross(tangent,u)
        rx,ry=radii[i] if isinstance(radii[i],tuple) else (radii[i],radii[i])
        for j in range(segments):
            t=j*math.tau/segments
            v.append(tuple(p[k]+rx*math.cos(t)*u[k]+ry*math.sin(t)*w[k] for k in range(3)))
    for i in range(len(points)-1):
        for j in range(segments):
            a=i*segments+j;b=i*segments+(j+1)%segments;c=b+segments;d=a+segments
            f.extend([(a,b,c),(a,c,d)])
    for i,rev in [(0,True),(len(points)-1,False)]:
        c=len(v);v.append(points[i])
        for j in range(segments):
            tri=(c,i*segments+j,i*segments+(j+1)%segments)
            f.append(tuple(reversed(tri)) if rev else tri)
    return v,f


def cloth_panel(grid, thickness=.35):
    """Closed thin cloth shell including hem edges, for an open-front mantle."""
    rows=len(grid);cols=len(grid[0]);front=[p for row in grid for p in row]
    v=front+[(x,y+thickness,z) for x,y,z in front];n=len(front);f=[]
    for r in range(rows-1):
        for c in range(cols-1):
            a=r*cols+c;b=a+1;d=a+cols;e=d+1
            f.extend([(a,d,e),(a,e,b),(a+n,e+n,d+n),(a+n,b+n,e+n)])
    boundary=list(range(cols))+[r*cols+cols-1 for r in range(1,rows)]+list(range(rows*cols-2,(rows-1)*cols-1,-1))+[r*cols for r in range(rows-2,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):f.extend([(a,b,b+n),(a,b+n,a+n)])
    return v,f


def assembly():
    parts=[]
    def add(name,mat,mesh):
        v,f=mesh
        volume=sum(dot(v[a],cross(v[b],v[c]))/6 for a,b,c in f)
        if volume<0:f=[(a,c,b) for a,b,c in f]
        parts.append({'name':name,'material':mat,'vertices':v,'faces':f})
    # Human scale: soles at 0, headwrap to 182cm. A-pose arms angled down.
    add('LongPleatedTunic','Linen',loft([
        (17,20,13,0,1),(20,20.5,13.1,0,1),(34,19,12.8,0,1),(51,18,12.5,0,.8),
        (72,16.5,11.8,0,.4),(90,15,11,0,0),(105,14.5,10.5,0,0),
        (116,16,11.3,0,0),(129,19,12,0,0),(140,22,11,0,0),(146,19,9.5,0,0),
        (151,12,7,0,0),(153,5.6,5,0,0)],64,12,.75))
    add('WovenWaistSash','Trim',loft([(101,15.6,11.65,0,0),(102,15.9,11.9,0,0),(108,15.9,11.9,0,0),(109,15.6,11.65,0,0)],48))
    # Hanging, slightly curved textile sash tail.
    add('SashTail','Trim',cloth_panel([[(5+c*.85,-12.5-.8*math.sin(r*.7),103-r*3.3) for c in range(7)] for r in range(10)],.22))
    add('Neck','Skin',loft([(148,5.4,4.7,0,0),(154,5,4.5,0,-.2),(160,5.6,5,0,-.2)],32))
    def face_sculpt(p):
        x,y,z=p
        # Face points -Y: shaped jaw, cheek pads and brow rather than a sphere.
        jaw=.73+.27*min(1,max(0,(z+11)/11))
        x*=jaw
        if y<0:
            y-=.9*math.exp(-((abs(x)-4.3)/2.2)**2-((z+1.1)/3)**2)
            y+=.75*math.exp(-((abs(x)-3.4)/1.8)**2-((z-2.1)/1.6)**2)
        return x,y,z
    add('SculptedHead','Skin',ellipsoid((0,-.4,166.5),(8.3,7.4,11.8),48,32,face_sculpt))
    add('NoseBridge','Skin',loft([(162,1.1,.75,0,-7.3),(164,1.55,1.5,0,-8.2),(165,1.4,1.65,0,-8.5),(168,1.05,1,0,-7.8),(170,.65,.4,0,-7.4)],24))
    for side in (-1,1):
        add('Ear'+str(side),'Skin',ellipsoid((side*8,-.05,166),(1.5,1.05,2.8),24,16))
        add('Eye'+str(side),'Eyes',ellipsoid((side*3.15,-7.15,168.1),(1.12,.25,.42),24,12))
        add('Brow'+str(side),'Hair',tube([(side*1.8,-7.4,169.6),(side*3.0,-7.6,169.9),(side*4.5,-7.25,169.6)], [.26,.34,.17],12))
    add('UpperLip','Skin',ellipsoid((0,-7.55,161.7),(2.35,.45,.43),24,12))
    add('LowerLip','Skin',ellipsoid((0,-7.50,161),(2.1,.42,.38),24,12))
    add('ShortBeard','Hair',loft([(154.8,1.8,1,0,-2.8),(156,3.4,2.4,0,-2.6),(158.2,5.0,4.1,0,-2.1),(160.0,5.7,4.7,0,-1.8)],40,11,.13))
    # Full covered calves; separate shaped feet and garment sleeves.
    for s in (-1,1):
        tag='L' if s<0 else 'R'
        add('Calf'+tag,'Linen',loft([(4,3.2,3.5,s*8,.5),(12,3.4,3.9,s*8,.5),(28,4.8,5.1,s*8,.5),(43,5.2,5.5,s*8,.5),(56,4.6,4.7,s*8,.5)],32))
        add('Foot'+tag,'Skin',ellipsoid((s*8,-4.1,4.5),(4.05,10,3.2),32,16))
        add('SandalSole'+tag,'Leather',loft([(0,3.8,10.5,s*8,-4.1),(.6,4.4,11,s*8,-4.1),(1.9,4.4,11,s*8,-4.1),(2.3,4.1,10.5,s*8,-4.1)],40))
        for idx,y in enumerate((-8.5,-3.8)):
            add('SandalStrap'+tag+str(idx),'Leather',tube([(s*8-3.8,y,3.2),(s*8-2.7,y,6.5),(s*8,y,7.6),(s*8+2.7,y,6.5),(s*8+3.8,y,3.2)],[(.85,.32)]*5,12))
        sleeve_points=[(s*17,0,143),(s*23,-.2,138),(s*29,-.5,128),(s*35,-.8,117),(s*40,-1,108),(s*42,-1,104)]
        add('LongSleeve'+tag,'Linen',tube(sleeve_points,[(9,8.5),(9.2,8),(8.5,7.5),(7,6),(5.5,4.8),(4.5,4.1)],32))
        add('SleeveCuff'+tag,'Trim',tube([(s*41,-1,105.5),(s*42,-1,103.5)],[(4.7,4.35),(4.7,4.35)],32))
        add('Wrist'+tag,'Skin',tube([(s*42,-1,104),(s*44,-1,99)],[(3.25,2.6),(3.3,2.3)],24))
        add('Palm'+tag,'Skin',ellipsoid((s*45,-1,95.7),(3.8,2.1,5.8),24,18))
        for i, length in enumerate((5.2,6.1,5.7,4.5)):
            x=s*(42.55+i*1.65)
            add('Finger'+tag+str(i),'Skin',tube([(x,-1,92.5),(x+s*.25,-1.25,90),(x+s*.25,-1.8,92.5-length)],[(.8,.85),(.76,.78),(.57,.64)],12))
        add('Thumb'+tag,'Skin',tube([(s*42.5,-1,97),(s*40.6,-1.5,94.7),(s*40.1,-2.2,92.8)],[(1.05,1),(1,.94),(.72,.72)],12))
    # Open-front outer garment drapes over both shoulders and down back; no weapon.
    for s in (-1,1):
        grid=[]
        for r in range(24):
            u=r/23; z=149-91*u
            row=[]
            for c in range(9):
                t=c/8; x=s*(7+14*t+2*u)
                y=-7.5-4.8*math.sin(t*math.pi)+1.4*math.sin(t*math.pi*4+u)*u
                row.append((x,y,z-4*math.sin(t*math.pi)*(1-u)))
            grid.append(row)
        add('MantleFront'+str(s),'Mantle',cloth_panel(grid,.4))
    grid=[]
    for r in range(28):
        u=r/27;row=[]
        for c in range(25):
            t=c/24;x=(t-.5)*(43+4*u)
            row.append((x,9.5+3*math.sin(t*math.pi)+1.3*u*math.cos(t*math.pi*14),147-100*u-3*math.cos(t*math.pi*2)*(1-u)))
        grid.append(row)
    add('MantleBack','Mantle',cloth_panel(grid,.4))
    for s in (-1,1):
        grid=[[(s*(7+14*c/8),-8+19*r/8,150-3*math.sin(math.pi*c/8)-2*abs(r/8-.5)) for c in range(9)] for r in range(9)]
        add('MantleShoulder'+str(s),'Mantle',cloth_panel(grid,.4))
    # Modest original wrapped cap: overlapping ellipsoidal cloth bands.
    add('HeadwrapCrown','Headwrap',ellipsoid((0,0,177.2),(8.8,8.1,4.8),40,16))
    for layer in range(4):
        pts=[]
        for i in range(65):
            t=i*math.tau/64
            pts.append((8.25*math.cos(t),7.8*math.sin(t),174.0+layer*1.7+1.05*math.cos(t+.4)))
        # Tiny overlap at rear; each closed capped strip is a separate editable piece.
        add('WrappedBand%d'%layer,'Headwrap',tube(pts,[(.7,1.14)]*65,12))
    return parts


def normals(part):
    acc=[[0.,0.,0.] for _ in part['vertices']]
    for a,b,c in part['faces']:
        n=cross(sub(part['vertices'][b],part['vertices'][a]),sub(part['vertices'][c],part['vertices'][a]))
        for idx in (a,b,c):
            for k in range(3):acc[idx][k]+=n[k]
    return [normalize(n) for n in acc]


def write_obj(path, parts, adapter=False):
    lines=['# Original editable civilian study; centimeters, front -Y, Z up.', 'mtllib PilgrimStudyV1.mtl']
    offset=1; uv_offset=1
    for p in parts:
        lines+=['o '+p['name'],'usemtl '+p['material'],'s 1']
        v=p['vertices'];n=normals(p)
        for x,y,z in v:lines.append('v %.7f %.7f %.7f'%(x,-y if adapter else y,z))
        for x,y,z in n:lines.append('vn %.8f %.8f %.8f'%(x,-y if adapter else y,z))
        # Nondegenerate face charts; not a production garment texture unwrap.
        for tri in p['faces']:
            a,b,c=(v[idx] for idx in tri);ab=sub(b,a);ac=sub(c,a);length=math.sqrt(dot(ab,ab))
            u=dot(ab,ac)/length;h=math.sqrt(dot(cross(ab,ac),cross(ab,ac)))/length
            lines+=['vt 0 0','vt %.8f 0'%(length/10),'vt %.8f %.8f'%(u/10,h/10)]
        for j,tri in enumerate(p['faces']):
            order=(0,2,1) if adapter else (0,1,2)
            lines.append('f '+' '.join('%d/%d/%d'%(offset+tri[k],uv_offset+j*3+k,offset+tri[k]) for k in order))
        offset+=len(v);uv_offset+=3*len(p['faces'])
    path.write_text('\n'.join(lines)+'\n',encoding='ascii')


def check(parts):
    report=[]
    for p in parts:
        v=p['vertices'];edges=collections.Counter();volume=0;min_area=float('inf')
        assert all(math.isfinite(x) for a in v for x in a)
        for a,b,c in p['faces']:
            n=cross(sub(v[b],v[a]),sub(v[c],v[a]));area=math.sqrt(dot(n,n))/2
            assert area>1e-7,(p['name'],area)
            min_area=min(min_area,area);volume+=dot(v[a],cross(v[b],v[c]))/6
            for e in ((a,b),(b,c),(c,a)):edges[tuple(sorted(e))]+=1
        assert all(c==2 for c in edges.values()),p['name']
        assert volume>0,p['name']
        report.append({'name':p['name'],'material':p['material'],'vertices':len(v),'triangles':len(p['faces']),
                       'closed_index_topology':True,'min_triangle_area_cm2':min_area,'signed_volume_cm3':volume})
    return report


def bounds(parts):
    v=[a for p in parts for a in p['vertices']]
    return {key:[fn(a[i] for a in v) for i in range(3)] for key,fn in [('min',min),('max',max)]}


def preview(parts, path, yaw):
    """Dependency-free shaded Z-buffer BMP; honest source mesh review, not UE."""
    width,height=620,1000;pixels=bytearray([28,30,32])*(width*height);depth=[-1e9]*(width*height)
    light=normalize((-.4,-.65,.9));scale=4.6
    for p in parts:
        v=p['vertices'];ns=normals(p);projected=[]
        for x,y,z in v:
            xx=x*math.cos(yaw)-y*math.sin(yaw);yy=x*math.sin(yaw)+y*math.cos(yaw)
            projected.append((width/2+xx*scale,930-z*scale,-yy))
        rgb=MATERIALS[p['material']][0]
        for tri in p['faces']:
            a,b,c=[projected[i] for i in tri]
            area=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            if abs(area)<1e-6:continue
            x0=max(0,int(min(a[0],b[0],c[0])));x1=min(width-1,int(max(a[0],b[0],c[0]))+1)
            y0=max(0,int(min(a[1],b[1],c[1])));y1=min(height-1,int(max(a[1],b[1],c[1]))+1)
            shades=[.28+.72*max(0,dot(ns[i],light)) for i in tri]
            for y in range(y0,y1+1):
                for x in range(x0,x1+1):
                    u=((b[0]-x)*(c[1]-y)-(b[1]-y)*(c[0]-x))/area
                    vv=((c[0]-x)*(a[1]-y)-(c[1]-y)*(a[0]-x))/area;w=1-u-vv
                    if min(u,vv,w)<0:continue
                    d=u*a[2]+vv*b[2]+w*c[2];idx=y*width+x
                    if d<=depth[idx]:continue
                    depth[idx]=d;shade=u*shades[0]+vv*shades[1]+w*shades[2]
                    color=[int(255*min(1,c*shade)**(1/2.2)) for c in rgb]
                    pixels[idx*3:idx*3+3]=bytes(reversed(color))
    rowbytes=(width*3+3)//4*4;size=54+rowbytes*height
    header=b'BM'+struct.pack('<IHHI',size,0,0,54)+struct.pack('<IiiHHIIiiII',40,width,height,1,24,0,rowbytes*height,2835,2835,0,0)
    with path.open('wb') as f:
        f.write(header)
        for y in range(height-1,-1,-1):f.write(pixels[y*width*3:(y+1)*width*3]+b'\0'*(rowbytes-width*3))


def export():
    if OUT.exists():raise RuntimeError('Preserve frozen study; author new version rather than overwrite')
    parts=assembly();checks=check(parts);OUT.mkdir(parents=True)
    mtl=[]
    for name,(rgb,rough) in MATERIALS.items():
        mtl+=['newmtl '+name,'Kd %.5f %.5f %.5f'%rgb,'Ka 0 0 0','Ks .02 .02 .02','Ns 8','d 1','illum 2','']
    (OUT/'PilgrimStudyV1.mtl').write_text('\n'.join(mtl),encoding='ascii')
    write_obj(OUT/'PilgrimStudyV1-editable.obj',parts)
    files=[]
    for mat in MATERIALS:
        selected=[p for p in parts if p['material']==mat];path=OUT/('SM_PilgrimStudyV1_'+mat+'.obj')
        write_obj(path,selected,True)
        files.append({'file':path.name,'material':mat,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                      'triangles':sum(len(p['faces']) for p in selected),'bounds_cm':bounds(selected)})
    report={'status':'offline_geometry_validated_native_and_animation_pending','namespace':DEST,'units':'centimeters',
            'front':'-Y canonical; native OBJ adapter reflects Y and reverses winding','bounds_cm':bounds(parts),
            'parts':checks,'native_files':files,'triangles':sum(len(p['faces']) for p in parts),
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'limits':['Static A-pose; no skeleton, skin weights, animation or facial rig','Separate intersecting closed component shells; not watertight union',
                      'Face-local UV charts overlap; not a production texture unwrap','Authored clothing design, not period or ritual certification',
                      'Native import, renders, collision, cloth deformation, LOD and crowd performance unverified']}
    (OUT/'geometry-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    preview(parts,OUT/'source-front.bmp',0)
    preview(parts,OUT/'source-three-quarter.bmp',.60)
    return report


def run_native():
    """Root only, in intended UE editor; imports eight static material shells, no actors."""
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():raise RuntimeError('Stop gameplay first')
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if assets.does_directory_exist(DEST):raise RuntimeError('Preserve existing review namespace')
    report=json.loads((OUT/'geometry-manifest.json').read_text())
    for f in report['native_files']:
        if hashlib.sha256((OUT/f['file']).read_bytes()).hexdigest()!=f['sha256']:raise RuntimeError('Changed OBJ '+f['file'])
    receipt={'status':'started','map_mutated':False,'skeletal':False,'assets':[]}
    try:
        tools=ue.AssetToolsHelpers.get_asset_tools();ml=ue.MaterialEditingLibrary
        for source in report['native_files']:
            name=source['material'];rgb,rough=MATERIALS[name]
            material=tools.create_asset('M_Pilgrim_'+name,DEST+'/Materials',ue.Material,ue.MaterialFactoryNew())
            if not material:raise RuntimeError('Material creation failed')
            color=ml.create_material_expression(material,ue.MaterialExpressionConstant3Vector)
            color.set_editor_property('constant',ue.LinearColor(*rgb,1))
            assert ml.connect_material_property(color,'',ue.MaterialProperty.MP_BASE_COLOR)
            r=ml.create_material_expression(material,ue.MaterialExpressionConstant);r.set_editor_property('r',rough)
            assert ml.connect_material_property(r,'',ue.MaterialProperty.MP_ROUGHNESS)
            ml.recompile_material(material)
            assert assets.save_loaded_asset(material,only_if_is_dirty=False)
            ui=ue.FbxImportUI()
            for key,value in dict(automated_import_should_detect_type=False,mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
                                  import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,
                                  import_textures=False,create_physics_asset=False).items():ui.set_editor_property(key,value)
            data=ui.get_editor_property('static_mesh_import_data')
            for key,value in dict(combine_meshes=True,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,
                                  convert_scene=False,convert_scene_unit=False,force_front_x_axis=False,import_uniform_scale=1.,
                                  auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,
                                  normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():data.set_editor_property(key,value)
            task=ue.AssetImportTask();path=OUT/source['file']
            for key,value in dict(filename=str(path),destination_path=DEST+'/Meshes',destination_name=path.stem,
                                  automated=True,async_=False,replace_existing=False,save=False,options=ui,factory=ue.FbxFactory()).items():task.set_editor_property(key,value)
            tools.import_asset_tasks([task]);objects=list(task.get_objects())
            assert len(objects)==1 and isinstance(objects[0],ue.StaticMesh)
            mesh=objects[0];b=mesh.get_bounding_box();actual={'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]}
            error=max(abs(actual[k][i]-source['bounds_cm'][k][i]) for k in actual for i in range(3))
            assert error<.05 and mesh.get_num_triangles(0)==source['triangles'],name
            for slot in range(len(mesh.get_editor_property('static_materials'))):mesh.set_material(slot,material)
            assert assets.save_loaded_asset(mesh,only_if_is_dirty=False)
            receipt['assets'].append({'mesh':mesh.get_path_name(),'material':material.get_path_name(),'bounds_error_cm':error,'triangles':mesh.get_num_triangles(0)})
        receipt['status']='native_static_assets_saved_unplaced_visual_and_skeletal_review_pending'
    except Exception as exc:
        receipt.update(status='failed_partial_assets_preserved',error=str(exc));raise
    finally:(OUT/'native-import.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',action='store_true');parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.export:print(json.dumps({'triangles':export()['triangles'],'output':str(OUT)}))
    elif args.check:print(json.dumps({'closed_parts':len(check(assembly())),'bounds_cm':bounds(assembly())}))
    else:parser.print_help()

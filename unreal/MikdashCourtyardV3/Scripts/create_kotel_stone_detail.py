"""Original Kotel facade review; export() offline, run_native() explicit Unreal import.
No map placement, shared grid edits, base removal, engine launch or openings changes.
"""
import json, math, hashlib, random
from pathlib import Path
from collections import defaultdict
ROOT=Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
SOURCE=Path(r"C:\Mikdash\Mikdash-Windows-Transfer\Workspace")
FOLDER=ROOT/"SourceAssets/kotel-detail/KotelStoneV1"
DEST="/Game/MikdashV3/MaterialReview/KotelStoneV1"
SOURCE_SHA="cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb"

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(v):return {k:[fn(p[i] for p in v) for i in range(3)] for k,fn in (("min",min),("max",max))}

def bevel_box(center, size, radius=0.5):
    """Six subdivided rounded faces; outward triangle winding, centimeters."""
    half = [v/2 for v in size]
    assert 0 < radius < min(half)
    vertices, faces = [], []
    for axis in range(3):
        u, v = (axis+1)%3, (axis+2)%3
        for sign in (-1, 1):
            start = len(vertices)
            for a in (-half[u], -half[u]+radius, half[u]-radius, half[u]):
                for b in (-half[v], -half[v]+radius, half[v]-radius, half[v]):
                    p = [0., 0., 0.]; p[axis] = sign*half[axis]; p[u] = a; p[v] = b
                    q = [max(-half[i]+radius, min(half[i]-radius, p[i])) for i in range(3)]
                    d = [p[i]-q[i] for i in range(3)]; length = math.sqrt(sum(x*x for x in d))
                    vertices.append(tuple(center[i]+q[i]+d[i]*radius/length for i in range(3)))
            for i in range(3):
                for j in range(3):
                    a = start+i*4+j; b = a+4; c = b+1; d = a+1
                    triangles = [(a,b,c),(a,c,d)]
                    faces.extend(triangles if sign == 1 else [(x,z,y) for x,y,z in triangles])
    return vertices, faces

def write_obj(name, triangles):
    # Canonical UE XYZ converted to OBJ import adapter: reflectY and reversewinding.
    lines=["# Original Kotel source/detail; UE legacy OBJ adapter cm", "o "+name]
    all_vertices=[]; n=1; minimum_uv_area=1e30
    for original in triangles:
        all_vertices.extend(original)
        a,b,c=[(v[0],-v[1],v[2]) for v in (original[0],original[2],original[1])]
        ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)]
        normal=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        nl=math.sqrt(sum(v*v for v in normal));edge=math.sqrt(sum(v*v for v in ab))
        assert nl>1e-8 and edge>1e-8
        normal=[v/nl for v in normal];u=sum(ac[i]*ab[i]/edge for i in range(3))/100;v=nl/edge/100
        minimum_uv_area=min(minimum_uv_area,edge/100*v/2)
        for p in (a,b,c):lines.append("v %.8f %.8f %.8f"%p)
        for uv in ((0,0),(edge/100,0),(u,v)):lines.append("vt %.8f %.8f"%uv)
        for _ in range(3):lines.append("vn %.8f %.8f %.8f"%tuple(normal))
        lines.append("f "+" ".join("%d/%d/%d"%(i,i,i) for i in range(n,n+3)));n+=3
    p=FOLDER/(name+".obj");p.write_text("\n".join(lines)+"\n",encoding="ascii")
    return dict(name=name,file=p.name,sha256=digest(p),triangles=len(triangles),boundsCm=bounds(all_vertices),minimumUVArea=minimum_uv_area)


def export():
    assert not FOLDER.exists(),"Preserve previous source artifacts"
    mp=SOURCE/"output/architecture-review/jerusalem-meshes.json";assert digest(mp)==SOURCE_SHA
    manifest_path=SOURCE/"output/cloud-unreal-v3/context-review/buildings-manifest.json"
    manifest=json.loads(manifest_path.read_text());source=json.loads(mp.read_text())["meshes"][1]
    target=next(c for c in manifest["components"] if c["componentId"]==7085)
    grid=next(g for g in manifest["meshes"] if 7085 in g["sourceComponentIds"])
    positions=source["positions"];indices=source["indices"]
    def tri(t):return [positions[3*indices[3*t+j]:3*indices[3*t+j]+3] for j in range(3)]
    parent={t:t for t in grid["sourceTriangleIndices"]};seen={}
    def find(t):
        while parent[t]!=t:parent[t]=parent[parent[t]];t=parent[t]
        return t
    for t in parent:
        for p in tri(t):
            key=tuple(round(v,4) for v in p)
            if key in seen:parent[find(t)]=find(seen[key])
            seen[key]=t
    groups=defaultdict(list)
    for t in parent:groups[find(t)].append(t)
    assert len(groups)==len(grid["sourceComponentIds"])
    chosen=[]
    for ids in groups.values():
        bb=bounds([v for t in ids for v in tri(t)])
        if len(ids)==target["triangles"] and max(abs(bb[k][i]-target["sourceBoundsAmos"][k][i]) for k in bb for i in range(3))<.001:chosen.append(ids)
    assert len(chosen)==1 and len(chosen[0])==100
    tx,_,tz=manifest["alignment"]["translationSourceAmos"]
    convert=lambda p:((p[0]+tx)*50,(p[2]+tz)*50,p[1]*50)
    # Coordinate swap reverses handedness: reverse source triangle to retain outward normals.
    base_triangles=[[convert(p) for p in (tri(t)[0],tri(t)[2],tri(t)[1])] for t in chosen[0]]
    canonical_bounds=bounds([v for tr in base_triangles for v in tr]);lo=canonical_bounds["min"][2];hi=canonical_bounds["max"][2];assert abs(hi-lo-2000)<.01
    osm_path=SOURCE/"mikdash-walkthrough/public/context/jerusalem.json"
    feature=next(f for f in json.loads(osm_path.read_text(encoding="utf-8"))["features"] if f["id"]==817206833)
    polygon=[((p[0]+tx)*50,(p[1]+tz)*50) for p in feature["points"]]
    area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(polygon,polygon[1:]))
    faces=[]
    for i,(a,b) in enumerate(zip(polygon,polygon[1:])):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        if length<100:continue
        tangent=(dx/length,dy/length);normal=(tangent[1],-tangent[0]) if area>0 else (-tangent[1],tangent[0])
        if normal[0]<-.8:faces.append(dict(edge=i,a=a,b=b,tangent=tangent,normal=normal,lengthCm=length))
    assert faces
    #28-course artistic distribution across existing20m model, NOT a facade survey.
    courses=[110]*12+[55]*8+[30]*8;assert sum(courses)==2000
    mesh_groups=[[] for _ in range(6)];blocks=[];rng=random.Random(7085)
    def solid(face,u,z,w,h,depth,offset,bevel,group):
        vertices,inds=bevel_box((u,offset,z),(w,depth,h),bevel)
        # local Y points OUT; basis(tangent,normal,up) may be left-handed.
        t,n,a=face["tangent"],face["normal"],face["a"]
        det=t[0]*n[1]-t[1]*n[0]
        transformed=[(a[0]+v[0]*t[0]+v[1]*n[0],a[1]+v[0]*t[1]+v[1]*n[1],v[2]) for v in vertices]
        for f in inds:
            order=f if det>0 else (f[0],f[2],f[1]);mesh_groups[group].append([transformed[j] for j in order])
    for face in faces:
        z=lo
        for row,height in enumerate(courses):
            length=face["lengthCm"];x=0
            width_range=(180,320) if row<12 else (95,175) if row<20 else (45,90)
            while x<length-.01:
                width=min(rng.uniform(*width_range),length-x)
                if length-x-width<25:width=length-x
                if width<3:break
                group=rng.randrange(6);gap=.8;w=width-gap;h=height-gap
                solid(face,x+width/2,z+height/2,w,h,2,1.15,.35,group)
                # Raised central boss leaves visible drafted margin on larger lower blocks.
                if row<20 and w>20:
                    margin=5 if row<12 else 3
                    solid(face,x+width/2,z+height/2,w-2*margin,h-2*margin,1.4,2.5,.45,group)
                blocks.append(dict(edge=face["edge"],course=row,widthCm=round(width,3),heightCm=height,tint=group))
                x+=width
            z+=height
    count=sum(len(t) for t in mesh_groups);assert count<650000
    FOLDER.mkdir(parents=True)
    base=write_obj("SM_Kotel7085_SourceReference",base_triangles)
    meshes=[write_obj("SM_KotelFace_Tint%d"%i,t) for i,t in enumerate(mesh_groups)]
    report=dict(status="EXPORTED_NATIVE_PENDING",namespace=DEST,sourceMeshSha256=SOURCE_SHA,buildingManifestSha256=digest(manifest_path),osmSourceSha256=digest(osm_path),sourceTriangleIds=chosen[0],sourceComponent=target,sharedGrid=grid["assetName"],sourceBase=base,meshes=meshes,faces=faces,blockCount=len(blocks),detailTriangles=count,coursesCm=courses,blocks=blocks,
        convention="Canonical UE XYZ cm. OBJ reflectsY and reverses trianglewinding; pertriangle planarUV100cm/unit. Source base is reference only and not imported bynativehelper. Existingbase remains live.",
        interpretation="Original drafted-margin limestone visual study;28course distribution and everyblockwidth/height/bevel/tint/projection are artistic, not surveyed presentKotel courses. Existing20m OSM extrusion/location unchanged. No exactfuturewallclaim.",
        surfacePolicy="Only long west-facing footprint segments;2cm plate and1.4cm boss,frontmax3.2cm beyondsourceface; no collision, no cutoutsadded, no doorsclosed, no sharedgrid materialchanges. Source footprint currentlysolid; preserveitsprofile.",
        limitations=["No exactstoneby-stone survey","Currentmapped wallbase/groundheight needsnativeplaza review","Projection andseams atfootprintbends needvisualinspection","No distantLOD/performance acceptance","No vegetation/notes automaticallyadded","No texture rights reused"],
        references=["https://thekotel.org/en/visitor-info/","https://thekotel.org/wp-content/uploads/2023/03/n2r3.jpg","https://hadashot.iaa.org.il/Report_Detail_eng.aspx?id=25029&mag_id=124&print=all"])
    (FOLDER/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    return {k:report[k] for k in ("status","blockCount","detailTriangles")}


def run_native():
    import unreal as u
    assert Path(u.Paths.project_dir()).resolve()==ROOT
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    lib=u.EditorAssetLibrary;assert not lib.does_directory_exist(DEST)
    manifest=json.loads((FOLDER/"manifest.json").read_text());result={"status":"importing","assets":[],"mapChanged":False}
    try:
        for i,record in enumerate(manifest["meshes"]):
            p=FOLDER/record["file"];assert digest(p)==record["sha256"]
            tools=u.AssetToolsHelpers.get_asset_tools();edit=u.MaterialEditingLibrary
            material=tools.create_asset("M_KotelStone_Tint%d"%i,DEST,u.Material,u.MaterialFactoryNew());assert material
            factor=(.93,.965,1,1.025,.95,.985)[i]
            color=edit.create_material_expression(material,u.MaterialExpressionConstant3Vector)
            color.set_editor_property("constant",u.LinearColor(.61*factor,.575*factor,.505*factor,1))
            assert edit.connect_material_property(color,"",u.MaterialProperty.MP_BASE_COLOR)
            rough=edit.create_material_expression(material,u.MaterialExpressionConstant);rough.set_editor_property("r",.78+i*.015)
            assert edit.connect_material_property(rough,"",u.MaterialProperty.MP_ROUGHNESS)
            edit.recompile_material(material);assert lib.save_loaded_asset(material,only_if_is_dirty=False)
            ui=u.FbxImportUI()
            for k,v in dict(automated_import_should_detect_type=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH,import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=False).items():ui.set_editor_property(k,v)
            data=ui.get_editor_property("static_mesh_import_data")
            for k,v in dict(combine_meshes=True,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,convert_scene=False,convert_scene_unit=False,force_front_x_axis=False,import_uniform_scale=1.0,auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():data.set_editor_property(k,v)
            task=u.AssetImportTask()
            for k,v in dict(filename=str(p),destination_path=DEST+"/Meshes",destination_name=record["name"],automated=True,replace_existing=False,save=False,options=ui,factory=u.FbxFactory()).items():task.set_editor_property(k,v)
            tools.import_asset_tasks([task]);objects=list(task.get_objects());assert len(objects)==1 and isinstance(objects[0],u.StaticMesh)
            mesh=objects[0];b=mesh.get_bounding_box();actual={"min":[b.min.x,b.min.y,b.min.z],"max":[b.max.x,b.max.y,b.max.z]}
            assert mesh.get_num_triangles(0)==record["triangles"]
            assert max(abs(actual[k][j]-record["boundsCm"][k][j]) for k in actual for j in range(3))<.05
            mesh.set_material(0,material);assert lib.save_loaded_asset(mesh,only_if_is_dirty=False)
            result["assets"].append(dict(mesh=mesh.get_path_name(),material=material.get_path_name(),triangles=mesh.get_num_triangles(0)))
        result["status"]="NATIVE_ASSETS_SAVED_UNPLACED_VISUAL_PENDING"
    except Exception as error:result.update(status="FAILED_PARTIAL_ASSETS_PRESERVED",error=str(error));raise
    finally:(FOLDER/"native-import.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

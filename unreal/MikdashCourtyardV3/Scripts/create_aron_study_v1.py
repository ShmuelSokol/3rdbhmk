"""Aron study: --export, --adapt handedness, --adapt-uv tangents, run_native UE.

No map or actor operations. Cherubim are reserved metadata anchors, not models.
All generated meshes remain separate, editable OBJ parts in assembly coordinates.
"""
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
FOLDER = ROOT / "SourceAssets/vessels-review/AronStudyV1"
SPEC = ROOT / "SourceAssets/vessels-review/aron-study-v1-spec.json"
DEST = "/Game/MikdashV3/MaterialReview/AronStudyV3"
ADAPTER_FOLDER = FOLDER / "UnrealImport"
UV_FOLDER = FOLDER / "UnrealImportUV"


def box(center, size):
    x, y, z = center
    a, b, c = (v/2 for v in size)
    points = [(x+dx*a, y+dy*b, z+dz*c)
              for dx, dy, dz in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                                  (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
    quads = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return points, [(q[0],q[1],q[2]) for q in quads]+[(q[0],q[2],q[3]) for q in quads]


def torus_y(center, major=4.0, minor=1.2, segments=64, sides=16):
    points, faces = [], []
    for i in range(segments):
        u = i*2*math.pi/segments
        for j in range(sides):
            v = j*2*math.pi/sides
            radial = major+minor*math.cos(v)
            points.append((center[0]+radial*math.cos(u), center[1]+minor*math.sin(v),
                           center[2]+radial*math.sin(u)))
    for i in range(segments):
        for j in range(sides):
            a=i*sides+j; b=((i+1)%segments)*sides+j
            c=((i+1)%segments)*sides+(j+1)%sides; d=i*sides+(j+1)%sides
            faces.extend([(a,b,c),(a,c,d)])
    return points, [(a,c,b) for a,b,c in faces]


def cylinder_y(center, radius=1.5, length=250.0, segments=64):
    points = [(center[0]+radius*math.cos(i*2*math.pi/segments),
               center[1]+side*length/2, center[2]+radius*math.sin(i*2*math.pi/segments))
              for side in (-1,1) for i in range(segments)]
    points.extend([(center[0],center[1]-length/2,center[2]),
                   (center[0],center[1]+length/2,center[2])])
    faces=[]
    for i in range(segments):
        j=(i+1)%segments
        faces.extend([(i,j,segments+j),(i,segments+j,segments+i),
                      (2*segments,j,i),(2*segments+1,segments+i,segments+j)])
    return points, [(a,c,b) for a,b,c in faces]


def geometry(spec):
    length, width, height = spec["bodyCm"]
    wall = spec["interpretiveGeometryCm"]["woodWallThickness"]
    cover = spec["coverCm"][2]
    parts = [("BodyBottom", box((0,0,wall/2),(length,width,wall)))]
    for sign, label in ((-1,"Minus"),(1,"Plus")):
        parts.append(("BodyLongWallY"+label, box((0,sign*(width-wall)/2,(height+wall)/2),
                                                (length,wall,height-wall))))
        parts.append(("BodyEndWallX"+label, box((sign*(length-wall)/2,0,(height+wall)/2),
                                               (wall,width-2*wall,height-wall))))
    parts.append(("KaporetCover", box((0,0,height+cover/2),(length,width,cover))))
    # A reserved plain crown frame, deliberately not a fabricated ornate relief.
    crown = spec["interpretiveGeometryCm"]["crownFrameThickness"]
    crown_h = spec["interpretiveGeometryCm"]["crownFrameHeight"]
    for sign, label in ((-1,"Minus"),(1,"Plus")):
        parts.append(("CrownLongY"+label,box((0,sign*(width+crown)/2,height+cover),
                                           (length+2*crown,crown,crown_h))))
        parts.append(("CrownEndX"+label,box((sign*(length+crown)/2,0,height+cover),
                                          (crown,width,crown_h))))
    r = spec["interpretiveGeometryCm"]
    for sign, label in ((-1,"Minus"),(1,"Plus")):
        x = sign*r["poleAxisX"]
        parts.append(("PoleX"+label,cylinder_y((x,0,r["ringCenterZ"]),
                                               r["poleRadius"],r["poleLength"])))
        for sy, ring_label in ((-1,"Minus"),(1,"Plus")):
            parts.append(("RingX"+label+"Y"+ring_label,torus_y(
                (x,sy*r["ringCenterY"],r["ringCenterZ"]),r["ringMajorRadius"],r["ringTubeRadius"])))
    return parts


def _bounds(points):
    return {"min":[min(p[i] for p in points) for i in range(3)],
            "max":[max(p[i] for p in points) for i in range(3)]}


def export():
    spec=json.loads(SPEC.read_text(encoding="utf-8"))
    assert not FOLDER.exists(), "Existing source geometry: inspect rather than overwrite"
    FOLDER.mkdir(parents=True)
    records=[]
    for part, (points, faces) in geometry(spec):
        name="SM_AronStudyV1_"+part
        lines=["# Original Mikdash Aron study; units centimeters; X length Y width Z up",
               "# Keruvim absent: this assembly is deliberately incomplete", "o "+name]
        lines.extend("v %.9f %.9f %.9f" % p for p in points)
        normals=[]
        for a,b,c in faces:
            u=[points[b][i]-points[a][i] for i in range(3)]
            v=[points[c][i]-points[a][i] for i in range(3)]
            n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            magnitude=math.sqrt(sum(x*x for x in n));assert magnitude>1e-9
            normals.append(tuple(x/magnitude for x in n))
        lines.extend("vn %.9f %.9f %.9f" % n for n in normals)
        lines.extend("f %d//%d %d//%d %d//%d" % (a+1,i+1,b+1,i+1,c+1,i+1)
                     for i,(a,b,c) in enumerate(faces))
        path=FOLDER/(name+".obj");path.write_text("\n".join(lines)+"\n",encoding="ascii")
        records.append({"name":name,"file":path.name,"vertices":len(points),"triangles":len(faces),
                        "expectedBoundsCm":_bounds(points),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest={"status":"ORIGINAL_EDITABLE_GEOMETRY_EXPORTED_NATIVE_PENDING", "parts":records,
              "assemblyTransform":"All parts authored together in centimeter coordinates; import with identity transforms",
              "keruvimMode":"RESERVED_ANCHORS_ONLY_NOT_MODELED", "keruvimAnchorsCm":spec["keruvimAnchorsCm"],
              "sourceSpecSha256":hashlib.sha256(SPEC.read_bytes()).hexdigest(),
              "totalTriangles":sum(x["triangles"] for x in records),
              "limitations":spec["limitations"]}
    (FOLDER/"geometry-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print("Exported",len(records),"editable original OBJ parts;",manifest["totalTriangles"],"triangles; keruvim incomplete.")


def adapt_for_unreal():
    """Preserve canonical source; compensate observed legacy OBJ Y reflection."""
    source_path = FOLDER / "geometry-manifest.json"
    manifest = json.loads(source_path.read_text(encoding="utf-8"))
    assert not ADAPTER_FOLDER.exists(), "Existing adapter: inspect rather than overwrite"
    assert manifest["sourceSpecSha256"] == hashlib.sha256(SPEC.read_bytes()).hexdigest()
    ADAPTER_FOLDER.mkdir()
    result = {
        "status": "ADAPTER_EXPORTED_NATIVE_V2_PENDING",
        "convention": "ImportOBJ=(SourceX,-SourceY,SourceZ); normals transformed identically; triangle winding reversed. Legacy UE OBJ importer observed to reflect Y. Native output must equal original source bounds.",
        "evidence": "native-import.json: BodyLongWallYMinus imported Y+34.5..37.5 instead of Y-37.5..-34.5",
        "nativeNamespace": "/Game/MikdashV3/MaterialReview/AronStudyV2",
        "sourceManifestSha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "sourceSpecSha256": manifest["sourceSpecSha256"],
        "parts": []}
    for record in manifest["parts"]:
        path = FOLDER / record["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        lines = ["# Import-only Y-reflection adapter; canonical source OBJ remains unchanged"]
        for line in path.read_text(encoding="ascii").splitlines():
            tokens = line.split()
            if tokens and tokens[0] in ("v", "vn"):
                assert len(tokens) == 4
                x, y, z = map(float, tokens[1:])
                line = tokens[0] + " %.9f %.9f %.9f" % (x, -y, z)
            elif tokens and tokens[0] == "f":
                assert len(tokens) == 4
                line = " ".join((tokens[0], tokens[1], tokens[3], tokens[2]))
            lines.append(line)
        adapted = ADAPTER_FOLDER / record["file"]
        adapted.write_text("\n".join(lines)+"\n", encoding="ascii")
        result["parts"].append({
            "name": record["name"], "file": record["file"],
            "sourceSha256": record["sha256"],
            "adapterSha256": hashlib.sha256(adapted.read_bytes()).hexdigest(),
            "expectedNativeBoundsCm": record["expectedBoundsCm"],
            "triangles": record["triangles"]})
    (ADAPTER_FOLDER / "adapter-manifest.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print("Exported 16 import-only handedness adapters; originals and Native01 failure preserved.")


def adapt_uv_for_unreal():
    """Add nondegenerate geometric UVs without touching V2 source or geometry."""
    prior_path = ADAPTER_FOLDER / "adapter-manifest.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    assert not UV_FOLDER.exists(), "Existing UV adapter: inspect rather than overwrite"
    UV_FOLDER.mkdir()
    result = dict(prior)
    result.update(status="UV_ADAPTER_EXPORTED_NATIVE_V3_PENDING", nativeNamespace=DEST,
        priorAdapterManifestSha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(),
        uvConvention="Independent planar triangle charts, 10cm per UV unit. U follows first edge, V is face normal cross U; positive signed UV area. Deliberate chart seams/overlap are acceptable for uniform procedural gold, not a production painted atlas. Existing positions, normals and winding unchanged.",
        parts=[])
    for record in prior["parts"]:
        source = ADAPTER_FOLDER / record["file"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == record["adapterSha256"]
        lines = source.read_text(encoding="ascii").splitlines()
        vertices = [tuple(map(float,line.split()[1:])) for line in lines if line.startswith("v ")]
        faces = [[tuple(int(value)-1 for value in token.split("//")) for token in line.split()[1:]]
                 for line in lines if line.startswith("f ")]
        uv, output_faces, areas = [], [], []
        for face in faces:
            a,b,c = [vertices[entry[0]] for entry in face]
            ab = [b[i]-a[i] for i in range(3)]
            ac = [c[i]-a[i] for i in range(3)]
            edge = math.sqrt(sum(value*value for value in ab)); assert edge > 1e-8
            u = [value/edge for value in ab]
            normal = [ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
            length = math.sqrt(sum(value*value for value in normal)); assert length > 1e-8
            n = [value/length for value in normal]
            v = [n[1]*u[2]-n[2]*u[1],n[2]*u[0]-n[0]*u[2],n[0]*u[1]-n[1]*u[0]]
            cu = sum(ac[i]*u[i] for i in range(3))/10.0
            cv = sum(ac[i]*v[i] for i in range(3))/10.0
            area = (edge/10.0)*cv*0.5; assert area > 1e-10
            offset = len(uv)
            uv.extend([(0.0,0.0),(edge/10.0,0.0),(cu,cv)])
            output_faces.append("f " + " ".join("%d/%d/%d" % (vi+1,offset+i+1,ni+1)
                                                for i,(vi,ni) in enumerate(face)))
            areas.append(area)
        output = ["# Original V2 geometry with nondegenerate independent UV charts"]
        output.extend(line for line in lines if not line.startswith("f "))
        output.extend("vt %.12f %.12f" % entry for entry in uv)
        output.extend(output_faces)
        target = UV_FOLDER / record["file"]
        target.write_text("\n".join(output)+"\n",encoding="ascii")
        copied = dict(record)
        copied.update(priorAdapterSha256=record["adapterSha256"],
                      adapterSha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                      uvCount=len(uv),minimumTriangleUvArea=min(areas))
        result["parts"].append(copied)
    (UV_FOLDER/"adapter-manifest.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("Exported16 UV adapters; original/V2 geometry and receipts preserved.")


def run_native():
    import unreal
    assert Path(unreal.Paths.project_dir()).resolve()==ROOT
    assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    assert not assets.does_directory_exist(DEST), "Existing native namespace: inspect partial run"
    manifest=json.loads((FOLDER/"geometry-manifest.json").read_text(encoding="utf-8"))
    assert manifest["sourceSpecSha256"]==hashlib.sha256(SPEC.read_bytes()).hexdigest()
    adapter_path=UV_FOLDER/"adapter-manifest.json"
    adapter=json.loads(adapter_path.read_text(encoding="utf-8"))
    assert adapter["sourceManifestSha256"]==hashlib.sha256((FOLDER/"geometry-manifest.json").read_bytes()).hexdigest()
    assert adapter["sourceSpecSha256"]==manifest["sourceSpecSha256"]
    adapter_records={record["name"]:record for record in adapter["parts"]}
    assert set(adapter_records)=={record["name"] for record in manifest["parts"]}
    result={"status":"started","created":[],"assigned":False,"mapSaved":False,
            "keruvim":"INCOMPLETE_RESERVED_ANCHORS_ONLY","visualAcceptance":"PENDING",
            "adapterManifestSha256":hashlib.sha256(adapter_path.read_bytes()).hexdigest(),
            "adapterConvention":adapter["convention"],"uvConvention":adapter["uvConvention"],
            "nativeBoundsChecks":[]}
    try:
        tools=unreal.AssetToolsHelpers.get_asset_tools();edit=unreal.MaterialEditingLibrary
        gold=tools.create_asset("M_AronStudyV3_Gold",DEST,unreal.Material,unreal.MaterialFactoryNew())
        assert isinstance(gold,unreal.Material);result["created"].append(gold.get_path_name())
        color=edit.create_material_expression(gold,unreal.MaterialExpressionConstant3Vector,-300,0)
        color.set_editor_property("constant",unreal.LinearColor(1.0,0.766,0.336,1.0))
        assert edit.connect_material_property(color,"",unreal.MaterialProperty.MP_BASE_COLOR)
        for value,prop,y in ((1.0,unreal.MaterialProperty.MP_METALLIC,200),
                             (0.28,unreal.MaterialProperty.MP_ROUGHNESS,400)):
            n=edit.create_material_expression(gold,unreal.MaterialExpressionConstant,-300,y)
            n.set_editor_property("r",value);assert edit.connect_material_property(n,"",prop)
        edit.recompile_material(gold);assert assets.save_loaded_asset(gold,only_if_is_dirty=False)
        for record in manifest["parts"]:
            assert hashlib.sha256((FOLDER/record["file"]).read_bytes()).hexdigest()==record["sha256"]
            adapted=adapter_records[record["name"]]
            assert adapted["sourceSha256"]==record["sha256"]
            assert adapted["expectedNativeBoundsCm"]==record["expectedBoundsCm"]
            path=UV_FOLDER/adapted["file"]
            assert hashlib.sha256(path.read_bytes()).hexdigest()==adapted["adapterSha256"]
            ui=unreal.FbxImportUI()
            for key,value in dict(automated_import_should_detect_type=False,
                mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH, import_as_skeletal=False,
                import_mesh=True,import_animations=False,import_materials=False,import_textures=False,
                create_physics_asset=False).items():ui.set_editor_property(key,value)
            options=ui.get_editor_property("static_mesh_import_data")
            for key,value in dict(combine_meshes=True,transform_vertex_to_absolute=True,
                bake_pivot_in_vertex=False,convert_scene=False,convert_scene_unit=False,
                force_front_x_axis=False,import_uniform_scale=1.0,auto_generate_collision=False,
                build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,
                normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():
                options.set_editor_property(key,value)
            task=unreal.AssetImportTask()
            for key,value in dict(filename=str(path),destination_path=DEST+"/Meshes",
                destination_name=record["name"],automated=True,async_=False,
                replace_existing=False,save=False,options=ui,factory=unreal.FbxFactory()).items():
                task.set_editor_property(key,value)
            tools.import_asset_tasks([task]);objects=list(task.get_objects())
            assert len(objects)==1 and isinstance(objects[0],unreal.StaticMesh)
            mesh=objects[0];result["created"].append(mesh.get_path_name())
            assert mesh.get_name()==record["name"], "Unexpected OBJ import name"
            b=mesh.get_bounding_box()
            actual={"min":[b.min.x,b.min.y,b.min.z],"max":[b.max.x,b.max.y,b.max.z]}
            error=max(abs(actual[k][i]-record["expectedBoundsCm"][k][i]) for k in actual for i in range(3))
            result["nativeBoundsChecks"].append({"name":record["name"],"actualCm":actual,"maxErrorCm":error})
            assert error<0.05, "OBJ axes/units differ; inspect before proceeding: "+str(actual)
            assert mesh.get_num_triangles(0)==record["triangles"]
            mesh.set_material(0,gold)
            assert assets.save_loaded_asset(mesh,only_if_is_dirty=False)
        result["status"]="unassigned_native_study_parts_saved_visual_review_pending"
    except Exception as error:
        result.update(status="failed_partial_assets_require_inspection",error=str(error));raise
    finally:
        (FOLDER/"native-import-v3.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    if "--export" in sys.argv:
        export()
    elif "--adapt" in sys.argv:
        adapt_for_unreal()
    elif "--adapt-uv" in sys.argv:
        adapt_uv_for_unreal()
    else:
        run_native()

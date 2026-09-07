"""Explicit run(template_map) creates a separate Kotel overlay review map.
Only FutureMount/IntegratedReview templates accepted. No source/grid/material edits.
"""
import json,hashlib,shutil,time
from pathlib import Path
ROOT=Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
FOLDER=ROOT/"SourceAssets/kotel-detail/KotelStoneV1"
DEST="/Game/MikdashV3/MaterialReview/KotelStoneV1"
TEMPLATES={"/Game/MikdashV3/FutureMountV1/L_FutureMount":DEST+"/Maps/FutureMountDetail",
           "/Game/MikdashV3/IntegratedReviewV1/Maps/Walkthrough":DEST+"/Maps/IntegratedDetail"}
BASE="/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N002_P001"
TAG="KotelStoneV1OverlayReview"
def file(asset,ext="uasset"):return ROOT/"Content"/(asset[6:]+"."+ext)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run(template_map):
    import unreal as u
    assert template_map in TEMPLATES
    path=TEMPLATES[template_map]
    assert Path(u.Paths.project_dir()).resolve()==ROOT
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);level=u.get_editor_subsystem(u.LevelEditorSubsystem);api=u.get_editor_subsystem(u.EditorActorSubsystem)
    assert not editor.get_game_world()
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages() and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert file(template_map,"umap").exists() and not u.EditorAssetLibrary.does_asset_exist(path)
    manifest=json.loads((FOLDER/"manifest.json").read_text())
    native=json.loads((FOLDER/"native-import.json").read_text());assert native["status"]=="NATIVE_ASSETS_SAVED_UNPLACED_VISUAL_PENDING"
    planned=[]
    for r in manifest["meshes"]:
        mesh=u.load_asset(DEST+"/Meshes/"+r["name"]);assert isinstance(mesh,u.StaticMesh)
        assert mesh.get_num_triangles(0)==r["triangles"]
        bb=mesh.get_bounding_box()
        for k,v in (("min",bb.min),("max",bb.max)):
            assert max(abs(a-b) for a,b in zip((v.x,v.y,v.z),r["boundsCm"][k]))<.05
        planned.append(mesh)
    assert len(planned)==6
    def base_state():
        found=[]
        for a in api.get_all_level_actors():
            for c in a.get_components_by_class(u.StaticMeshComponent):
                if c.static_mesh and c.static_mesh.get_path_name().split(".")[0]==BASE:found.append((a,c))
        assert len(found)==1
        a,c=found[0];assert c.static_mesh.get_num_triangles(0)==284
        pos,rot,s=c.get_world_location(),c.get_world_rotation(),c.get_world_scale()
        assert max(abs(v) for v in (pos.x,pos.y,pos.z,rot.pitch,rot.yaw,rot.roll))<.001
        assert max(abs(v-1) for v in (s.x,s.y,s.z))<.001
        materials=[c.get_material(i).get_path_name().split(".")[0] if c.get_material(i) else None for i in range(c.get_num_materials())]
        hashes={BASE:sha(file(BASE))}
        for m in materials:
            if m and m.startswith("/Game/"):hashes[m]=sha(file(m))
        return dict(label=a.get_actor_label(),transform=c.get_world_transform().export_text(),materials=materials,
            overrides=[m.get_path_name() if m else None for m in c.get_editor_property("override_materials")],collision=str(c.get_collision_enabled()),profile=str(c.get_collision_profile_name()),assetHashes=hashes)
    oldmap=editor.get_editor_world().get_path_name().split(".")[0];assert file(oldmap,"umap").exists()
    camera=editor.get_level_viewport_camera_info()
    stamp=time.strftime("%Y%m%dT%H%M%S");receipt=FOLDER/("placement-"+stamp+".json");assert not receipt.exists()
    source_sha=sha(file(template_map,"umap"))
    checkpoint=ROOT.parent/"ReviewCheckpoints"/("KotelDetail-"+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
    shutil.copy2(file(template_map,"umap"),checkpoint/"template.umap")
    assert sha(checkpoint/"template.umap")==source_sha
    report=dict(status="preparing",source=template_map,sourceSha256=source_sha,map=path,checkpoint=str(checkpoint),placement="Six identity transforms; noncolliding stoneoverlay, existing Kotelbase retained.",visualAcceptance="PENDING")
    try:
        assert level.load_level(template_map)
        original=base_state();count=len(api.get_all_level_actors());assert not any(TAG in [str(t) for t in a.tags] for a in api.get_all_level_actors())
        world=u.EditorLoadingAndSavingUtils.new_map_from_template(template_map,False);assert world and base_state()==original
        created=[]
        for mesh in planned:
            a=api.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,0),u.Rotator());assert a
            a.set_actor_label("REVIEW_Kotel_"+mesh.get_name());a.set_folder_path("Review/Kotel stone detail")
            a.set_editor_property("tags",[u.Name(TAG)])
            c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            created.append(a)
        assert base_state()==original and len(api.get_all_level_actors())==count+6
        assert u.EditorLoadingAndSavingUtils.save_map(world,path)
        assert level.load_level(path)
        overlays=[a for a in api.get_all_level_actors() if TAG in [str(t) for t in a.tags]];assert len(overlays)==6
        for a in overlays:
            p,r,s=a.get_actor_location(),a.get_actor_rotation(),a.get_actor_scale3d()
            assert max(abs(v) for v in (p.x,p.y,p.z,r.pitch,r.yaw,r.roll))<.001
            assert max(abs(v-1) for v in (s.x,s.y,s.z))<.001
            assert a.static_mesh_component.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION
        assert base_state()==original and len(api.get_all_level_actors())==count+6
        report.update(status="SAVED_REOPENED_BASE_PRESERVED_VISUAL_PENDING",baseState=original,mapSha256=sha(file(path,"umap")),overlayCount=6,sourceUnchanged=sha(file(template_map,"umap"))==source_sha)
        assert report["sourceUnchanged"]
    except Exception as error:report.update(status="FAILED_PARTIAL_REVIEW_MAP_PRESERVED",error=str(error));raise
    finally:
        try:
            assert level.load_level(oldmap)
            if camera:editor.set_level_viewport_camera_info(*camera)
            report["editorMapRestored"]=True
        except Exception as error:report.update(status="FAILED_EDITOR_RESTORATION_REVIEW_MAP_PRESERVED",restoreError=str(error))
        report["sourceUnchanged"]=sha(file(template_map,"umap"))==source_sha
        receipt.write_text(json.dumps(report,indent=2)+"\n")
    return report

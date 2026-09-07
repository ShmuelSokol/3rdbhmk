"""Explicit build(review_map_path, finish='gold') in a saved review copy only.
Creates original finish assets and noncolliding interior veneers; never saves map.
No engine action on import. Gold overlay is an interpretation, not a Yechezkel mandate.
"""
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
DEST = "/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1"
SHA = "40c4a0feae391868c6c840f76bc72f0df0bab8c3be9406c6b5dbb6f508f9333d"
TAG = "SanctuaryFinishesV1Review"


def plan():
    path = ROOT/"SourceAssets/architecture-manifest.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SHA
    records = json.loads(path.read_text(encoding="utf-8-sig"))["meshes"]
    by_name = {r["sourceName"]: r for r in records}
    house = next(r for r in records if r["assetName"].startswith("SM_2630_"))
    elements = json.loads(house["sourceProperties"]["source_elements_json"])
    sides = [e for e in elements if e["name"] == "House six-amah side wall"]
    assert len(sides) == 2
    assert all(abs(abs(e["position"][2])-e["size"][2]/2-10) < 1e-6 for e in sides)
    rear = next(e for e in elements if e["name"] == "House rear six-amah wall")
    assert (rear["position"][0]+rear["size"][0]/2)*50 == -6700
    ceiling = by_name["Sanctuary ceiling"]["expectedBoundsUnrealCm"]["min"][2]
    panels = []
    # 0.2 cm artistic veneer straddles source face: 0.1 cm proud only.
    for room in ("Heichal", "Kodesh"):
        floor = by_name[room+" clear floor"]["expectedBoundsUnrealCm"]
        x0,x1 = floor["min"][0],floor["max"][0]
        z0 = floor["max"][2]
        for sign in (-1,1):
            y = sign*500
            panels.append(dict(name=room+"Side"+str(sign), center=[(x0+x1)/2,y,(z0+ceiling)/2],size=[x1-x0,.2,ceiling-z0],sourceFace="House inner side +/-500cm"))
        if room == "Kodesh":
            panels.append(dict(name="KodeshRear",center=[x0,0,(z0+ceiling)/2],size=[.2,1000,ceiling-z0],sourceFace="House rear inner face -6700cm"))
    # Entrance jamb backs only; leave the 500cm clear opening unobstructed.
    for sign in (-1,1):
        panels.append(dict(name="HeichalEntranceJamb"+str(sign),center=[-3600,sign*375,1925],size=[.2,250,2000],sourceFace="Heichal doorway western face; y outside +/-250cm"))
    names = {"Heichal clear floor","Kodesh clear floor","Sanctuary ceiling","Kodesh partition shoulder","Kodesh partition lintel"}
    originals = [r for r in records if r["sourceName"] in names]
    assert len(originals) == 6
    return panels, originals, house


def build(review_map_path, finish="gold"):
    import unreal
    assert finish in ("gold", "wood")
    assert review_map_path.startswith(DEST+"/Maps/"), "Use separate saved review map"
    assert Path(unreal.Paths.project_dir()).resolve() == ROOT
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assert not editor.get_game_world(), "Stop PIE first"
    assert editor.get_editor_world().get_path_name().split(".")[0] == review_map_path
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Need saved review baseline"
    all_actors = actors.get_all_level_actors()
    assert not any(TAG in [str(t) for t in a.tags] for a in all_actors), "Review already applied"
    panels, records, house = plan()
    selected = []
    # Validate native measured geometry and identity before any material/actor edits.
    for record in records+[house]:
        mesh_path = "/Game/MikdashV3/Architecture/architecture_"+record["assetName"]
        matches=[]
        for actor in all_actors:
            for component in actor.get_components_by_class(unreal.StaticMeshComponent):
                mesh=component.static_mesh
                if mesh and mesh.get_path_name().split(".")[0] == mesh_path:
                    matches.append((actor,component,mesh))
        assert len(matches)==1, mesh_path
        actor,component,mesh=matches[0]
        assert mesh.get_num_triangles(0)==record["triangles"]
        bounds=mesh.get_bounding_box()
        for side,vec in (("min",bounds.min),("max",bounds.max)):
            assert max(abs(a-b) for a,b in zip((vec.x,vec.y,vec.z),record["expectedBoundsUnrealCm"][side]))<.05
        loc,rot,scale=component.get_world_location(),component.get_world_rotation(),component.get_world_scale()
        assert max(abs(v) for v in (loc.x,loc.y,loc.z,rot.pitch,rot.yaw,rot.roll))<.001
        assert max(abs(v-1) for v in (scale.x,scale.y,scale.z))<.001
        if record != house:
            assert component.get_num_materials()==1
            selected.append((component,list(component.get_editor_property("override_materials")),record))
    assetlib=unreal.EditorAssetLibrary
    material_path=DEST+"/M_Sanctuary_"+finish
    cube_path=DEST+"/SM_InteriorVeneerCube"
    assert not assetlib.does_asset_exist(material_path), "Unique review asset already exists"
    receipt=ROOT/"SourceAssets/visual-review"/("sanctuary-finishes-native-"+time.strftime("%Y%m%dT%H%M%S")+".json")
    assert not receipt.exists()
    report=dict(status="building",map=review_map_path,finish=finish,mapSaved=False,panels=panels,originalOverrides=[],missingFigurativeReliefs=True,interpretation="Gold overlay follows earlier Temple analogy; wood follows Yechezkel41 paneling description. Neither prototype is a complete sanctuary.")
    created=[]
    try:
        material=unreal.AssetToolsHelpers.get_asset_tools().create_asset("M_Sanctuary_"+finish,DEST,unreal.Material,unreal.MaterialFactoryNew())
        assert material
        edit=unreal.MaterialEditingLibrary
        color=edit.create_material_expression(material,unreal.MaterialExpressionConstant3Vector,-300,0)
        rgb=(1,.766,.336) if finish=="gold" else (.22,.085,.028)
        color.set_editor_property("constant",unreal.LinearColor(*rgb,1))
        assert edit.connect_material_property(color,"",unreal.MaterialProperty.MP_BASE_COLOR)
        for value,prop,y in ((1 if finish=="gold" else 0,unreal.MaterialProperty.MP_METALLIC,180),(.34 if finish=="gold" else .62,unreal.MaterialProperty.MP_ROUGHNESS,320)):
            n=edit.create_material_expression(material,unreal.MaterialExpressionConstant,-300,y)
            n.set_editor_property("r",value)
            assert edit.connect_material_property(n,"",prop)
        edit.recompile_material(material)
        assert assetlib.save_loaded_asset(material,only_if_is_dirty=False)
        cube=unreal.load_asset(cube_path) if assetlib.does_asset_exist(cube_path) else assetlib.duplicate_asset("/Engine/BasicShapes/Cube",cube_path)
        assert isinstance(cube,unreal.StaticMesh)
        bb=cube.get_bounding_box()
        assert all(abs(v-50)<.001 for v in (bb.max.x,bb.max.y,bb.max.z)) and all(abs(v+50)<.001 for v in (bb.min.x,bb.min.y,bb.min.z))
        assert assetlib.save_loaded_asset(cube,only_if_is_dirty=False)
        for p in panels:
            a=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*p["center"]),unreal.Rotator())
            assert a
            created.append(a)
            a.set_actor_label("Review_"+p["name"])
            a.set_editor_property("tags",[unreal.Name(TAG)])
            a.set_folder_path("Material review/Sanctuary finishes")
            comp=a.static_mesh_component
            comp.set_static_mesh(cube)
            a.set_actor_scale3d(unreal.Vector(*(s/100 for s in p["size"])))
            comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            comp.set_material(0,material)
            assert comp.get_material(0)==material
        # Wood variant leaves established gold floors/ceiling/partition unchanged;
        # gold variant reviews their original gold material response consistently.
        if finish=="gold":
            for comp,overrides,record in selected:
                report["originalOverrides"].append(dict(asset=record["assetName"],materials=[m.get_path_name() if m else None for m in overrides]))
                comp.set_material(0,material)
                assert comp.get_material(0)==material
        report.update(status="APPLIED_IN_REVIEW_MAP_UNSAVED_VISUAL_ACCEPTANCE_PENDING",createdActorCount=len(created),material=material_path)
    except Exception as error:
        errors=[]
        for comp,overrides,record in selected:
            try: comp.set_editor_property("override_materials",overrides)
            except Exception as restore_error: errors.append(str(restore_error))
        for actor in created:
            try: assert actors.destroy_actor(actor)
            except Exception as restore_error: errors.append(str(restore_error))
        report.update(status="FAILED_REVIEW_MAP_DISCARD_REQUIRED",error=str(error),restoreErrors=errors)
        raise
    finally:
        receipt.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

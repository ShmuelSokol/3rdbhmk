"""Explicit build(review_map_path): existing StoneV2 on exact courtyard meshes.
Root opens a separate saved review template; no engine launch, map save or new shader.
"""
import hashlib
import json
from pathlib import Path
import time
ROOT=Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
DEST="/Game/MikdashV3/MaterialReview/ExteriorStoneV1"
SHA="40c4a0feae391868c6c840f76bc72f0df0bab8c3be9406c6b5dbb6f508f9333d"
WALL="/Game/MikdashV3/MaterialReview/JerusalemStoneV2/M_JerusalemStoneV2_WallReview"
PAVING="/Game/MikdashV3/MaterialReview/JerusalemStoneV2/M_JerusalemStoneV2_PavingReview"
INDICES=tuple(range(129,140))
CAMERA={"position":[6500,-1800,468],"pitch":0,"yaw":155,"roll":0,"fov":75}


def plan():
    p=ROOT/"SourceAssets/architecture-manifest.json"
    assert hashlib.sha256(p.read_bytes()).hexdigest()==SHA
    records=json.loads(p.read_text(encoding="utf-8-sig"))["meshes"]
    selected=[r for r in records if int(r["assetName"][3:7]) in INDICES]
    assert len(selected)==11
    for r in selected:
        assert len(r["materialSlots"])==1
        assert r["materialSlots"][0]["sourceMaterialKey"] in ("stone","paving","innerPaving")
        assert r["unionGroup"] is None,"Shared source unions excluded"
        assert r["sourcePart"] not in ("heichal","kodesh","ulam")
    return selected


def build(review_map_path):
    import unreal as u
    assert review_map_path.startswith(DEST+"/Maps/")
    assert Path(u.Paths.project_dir()).resolve()==ROOT
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    world=editor.get_editor_world()
    assert world.get_path_name().split(".")[0]==review_map_path
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),"Need saved review baseline"
    materials={"wall":u.load_asset(WALL),"paving":u.load_asset(PAVING)}
    assert all(isinstance(m,u.Material) for m in materials.values())
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    selected=[]
    for r in plan():
        path="/Game/MikdashV3/Architecture/architecture_"+r["assetName"]
        found=[]
        for a in actors:
            for c in a.get_components_by_class(u.StaticMeshComponent):
                mesh=c.static_mesh
                if mesh and mesh.get_path_name().split(".")[0]==path:found.append(c)
        assert len(found)==1,path
        c=found[0];mesh=c.static_mesh
        assert mesh.get_num_triangles(0)==r["triangles"] and c.get_num_materials()==1
        b=mesh.get_bounding_box()
        for key,v in (("min",b.min),("max",b.max)):
            assert max(abs(a-b) for a,b in zip((v.x,v.y,v.z),r["expectedBoundsUnrealCm"][key]))<.05
        loc,rot,scale=c.get_world_location(),c.get_world_rotation(),c.get_world_scale()
        assert max(abs(v) for v in (loc.x,loc.y,loc.z,rot.pitch,rot.yaw,rot.roll))<.001
        assert max(abs(v-1) for v in (scale.x,scale.y,scale.z))<.001
        kind="paving" if r["sourceName"] in ("Outer court floor","Inner court clear floor") else "wall"
        assert c.get_material(0)!=materials[kind],"Already assigned; inspect existing review"
        selected.append((c,r,kind,list(c.get_editor_property("override_materials"))))
    receipt=ROOT/"SourceAssets/visual-review"/("exterior-stone-native-"+time.strftime("%Y%m%dT%H%M%S")+".json")
    assert not receipt.exists()
    report=dict(status="applying",map=review_map_path,mapSaved=False,camera=CAMERA,assignments=[],houseUnionUntouched=True,originalStoneMaterialsUnchanged=True)
    try:
        for c,r,kind,overrides in selected:
            report["assignments"].append(dict(asset=r["assetName"],sourceName=r["sourceName"],bounds=r["expectedBoundsUnrealCm"],originalEffectiveMaterial=c.get_material(0).get_path_name() if c.get_material(0) else None,originalOverrides=[m.get_path_name() if m else None for m in overrides],candidate=materials[kind].get_path_name(),collisionBefore=str(c.get_collision_enabled())))
            collision=c.get_collision_enabled()
            c.set_material(0,materials[kind])
            assert c.get_material(0)==materials[kind] and c.get_collision_enabled()==collision
        report.update(status="APPLIED_REVIEW_MAP_UNSAVED_VISUAL_ACCEPTANCE_PENDING",targetCount=len(selected),wallCount=9,pavingCount=2)
    except Exception as error:
        errors=[]
        for c,r,kind,overrides in selected:
            try:c.set_editor_property("override_materials",overrides)
            except Exception as restore_error:errors.append(str(restore_error))
        report.update(status="FAILED_REVIEW_MAP_DISCARD_REQUIRED",error=str(error),restoreErrors=errors)
        raise
    finally:receipt.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

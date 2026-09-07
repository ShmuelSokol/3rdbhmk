"""Explicit run(): source-preserving intensity-only saved-map variants.
No engine action on import. Never modifies materials or saves the source map.
"""
import hashlib,json,shutil,time
from pathlib import Path
import unreal
ROOT=Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
SOURCE="/Game/MikdashV3/MaterialReview/SanctuaryPolishV1/Maps/CourtyardPolish"
BASE="/Game/MikdashV3/MaterialReview/SanctuaryPolishV2/Maps/"
VARIANTS=((BASE+"MaterialOnly",0.0),(BASE+"LowFill",120.0))
FILL_LABEL="Review_DoorwayDaylightProxy"

def map_file(path):
    assert path.startswith("/Game/")
    return ROOT/"Content"/(path[6:]+".umap")

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def normalized(value, world):
    if hasattr(value, "export_text"):
        text = value.export_text()
    elif isinstance(value, unreal.Object):
        text = value.get_path_name()
    else:
        text = str(value)
    return text.replace(world.get_path_name(), "<WORLD>").replace(
        world.get_path_name().split(".")[0], "<MAP>")

def scene_snapshot(editor):
    """Compare actors, transforms, meshes, instance transforms, materials and lights.

    This is a defined semantic inventory, not every serialized UObject property.
    Full postprocess settings are checked separately, including unchanged fields.
    """
    world = editor.get_editor_world()
    rows = []
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        row = {
            "name": actor.get_name(), "label": actor.get_actor_label(),
            "class": actor.get_class().get_path_name(),
            "transform": actor.get_actor_transform().export_text(),
            "components": [],
        }
        for component in actor.get_components_by_class(unreal.SceneComponent):
            entry = {
                "name": component.get_name(), "class": component.get_class().get_path_name(),
                "transform": component.get_world_transform().export_text(),
                "mobility": str(component.get_editor_property("mobility")),
                "visible": component.get_editor_property("visible"),
            }
            if isinstance(component, unreal.StaticMeshComponent):
                mesh = component.get_editor_property("static_mesh")
                entry["mesh"] = mesh.get_path_name() if mesh else None
                entry["materials"] = [
                    component.get_material(i).get_path_name() if component.get_material(i) else None
                    for i in range(component.get_num_materials())
                ]
                entry["collisionProfile"] = str(component.get_collision_profile_name())
                entry["collisionEnabled"] = str(component.get_collision_enabled())
                if isinstance(component, unreal.InstancedStaticMeshComponent):
                    entry["instanceCount"] = component.get_instance_count()
                    entry["instancesHash"] = digest([
                        component.get_instance_transform(i, world_space=True).export_text()
                        for i in range(component.get_instance_count())
                    ])
            # LightComponentBase also includes SkyLightComponent, unlike LightComponent.
            if isinstance(component, unreal.LightComponentBase):
                entry["light"] = {key: normalized(component.get_editor_property(key), world)
                                  for key in ("intensity", "light_color", "affects_world")}
            if isinstance(component, unreal.RectLightComponent):
                entry["rect"]={key:normalized(component.get_editor_property(key),world) for key in (
                    "intensity_units","source_width","source_height","attenuation_radius",
                    "use_temperature","temperature","cast_shadows","indirect_lighting_intensity")}
                if actor.get_actor_label()==FILL_LABEL:
                    # Normalize the single permitted difference in an unattached dict.
                    entry["light"]["intensity"]="1200.0"
            if isinstance(component, unreal.SkyLightComponent):
                entry["sky"] = {key: normalized(component.get_editor_property(key), world)
                                for key in ("source_type", "real_time_capture", "cubemap")}
            row["components"].append(entry)
        row["components"].sort(key=lambda item: item["name"])
        rows.append(row)
    rows.sort(key=lambda item: item["name"])
    return {"actorCount": len(rows), "semanticInventorySha256": digest(rows)}

def fill():
    matches=[a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label()==FILL_LABEL]
    assert len(matches)==1 and isinstance(matches[0],unreal.RectLight)
    c=matches[0].get_component_by_class(unreal.RectLightComponent)
    assert str(c.get_editor_property("intensity_units"))==str(unreal.LightUnits.LUMENS)
    return c


def postprocess():
    result={}
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if isinstance(a,unreal.PostProcessVolume):
            settings=a.get_editor_property("settings")
            result[a.get_name()]={"allSettings":settings.export_text(),"priority":float(a.get_editor_property("priority")),"blendWeight":float(a.get_editor_property("blend_weight")),"unbound":bool(a.get_editor_property("unbound"))}
    assert result
    return result



def polish_material_hashes():
    result={}
    for name in ("Wall","Floor","Vessel"):
        path=ROOT/("Content/MikdashV3/MaterialReview/SanctuaryPolishV1/M_Gold"+name+".uasset")
        assert path.exists()
        result[str(path)]=sha(path)
    return result


def run():
    assert Path(unreal.Paths.project_dir()).resolve()==ROOT
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assert not editor.get_game_world()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert map_file(SOURCE).exists()
    assert all(not map_file(p).exists() and not unreal.EditorAssetLibrary.does_asset_exist(p) for p,v in VARIANTS)
    old_map=editor.get_editor_world().get_path_name().split(".")[0]
    assert old_map.startswith("/Game/") and map_file(old_map).exists()
    camera=editor.get_level_viewport_camera_info()
    stamp=time.strftime("%Y%m%dT%H%M%S")
    folder=ROOT/"SourceAssets/visual-review"/("sanctuary-fill-variants-"+stamp)
    assert not folder.exists();folder.mkdir()
    checkpoint=ROOT.parent/"ReviewCheckpoints"/("SanctuaryFillV2-"+stamp)
    checkpoint.mkdir(parents=True,exist_ok=False)
    source_sha=sha(map_file(SOURCE))
    shutil.copy2(map_file(SOURCE),checkpoint/"CourtyardPolish.umap")
    assert sha(checkpoint/"CourtyardPolish.umap")==source_sha
    report={"status":"creating","source":SOURCE,"sourceSha256":source_sha,"checkpoint":str(checkpoint),"variants":[],"permittedDifference":"Existing Review_DoorwayDaylightProxy RectLight intensity only.0=material-only lighting variant;120=10percent of1200lm baseline. Globalpostprocess and material assignments unchanged.","visualAcceptance":"PENDING","limits":"Semantic all-actor/component inventory and complete PP settings check, not bytecomparison of every serialized UObject property."}
    receipt=folder/"variants.json"
    def write():receipt.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    try:
        assert level.load_level(SOURCE)
        assert abs(float(fill().get_editor_property("intensity"))-1200.0)<.001
        before=scene_snapshot(editor);pp=postprocess();material_hashes=polish_material_hashes()
        report["sourceInventory"]=before;report["sourcePostprocess"]=pp;report["sourceGoldMaterialAssetHashes"]=material_hashes
        write()
        for path,value in VARIANTS:
            world=unreal.EditorLoadingAndSavingUtils.new_map_from_template(SOURCE,False)
            assert world
            assert scene_snapshot(editor)==before and postprocess()==pp
            component=fill();assert abs(float(component.get_editor_property("intensity"))-1200)<.001
            component.set_intensity(value)
            assert abs(float(component.get_editor_property("intensity"))-value)<.001
            assert scene_snapshot(editor)==before,"Other actor/material/light/transform field changed"
            assert postprocess()==pp,"Postprocess changed"
            assert unreal.EditorLoadingAndSavingUtils.save_map(world,path)
            assert level.load_level(path)
            assert abs(float(fill().get_editor_property("intensity"))-value)<.001
            assert scene_snapshot(editor)==before and postprocess()==pp
            assert sha(map_file(SOURCE))==source_sha
            assert polish_material_hashes()==material_hashes,"Original gold material bytes changed"
            report["variants"].append({"map":path,"intensityLumens":value,"sha256":sha(map_file(path)),"status":"saved_reopened_intensity_only_verified_visual_pending","normalizedSceneInventory":scene_snapshot(editor),"postprocessUnchanged":True})
            write()
        report["status"]="SAVED_REOPENED_INTENSITY_ONLY_VERIFIED_VISUAL_PENDING"
    except Exception as error:
        report.update(status="FAILED_PARTIAL_REVIEW_MAPS_PRESERVED",error=str(error));raise
    finally:
        errors=[]
        try:
            assert level.load_level(old_map)
            if camera:editor.set_level_viewport_camera_info(camera[0],camera[1])
            report["originalEditorMapRestored"]=editor.get_editor_world().get_path_name().split(".")[0]==old_map
        except Exception as error:errors.append(str(error))
        report["sourceMapUnchanged"]=sha(map_file(SOURCE))==source_sha
        if errors or not report["sourceMapUnchanged"]:report.update(status="FAILED_RESTORATION_REQUIRES_REVIEW",restoreErrors=errors)
        write()
    return report

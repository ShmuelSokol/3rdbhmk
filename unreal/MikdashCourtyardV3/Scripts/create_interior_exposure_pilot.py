"""Create a unique exposure-only map pilot; never run concurrently with editor work.

No lights, source geometry, materials, project settings or production maps are edited.
Run through native Unreal Python. Root owns native execution and visual acceptance.
"""
import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
SOURCE = "/Game/MikdashV3/Maps/Courtyard"
DESTINATION = "/Game/MikdashV3/MaterialReview/InteriorExposureV1/Courtyard_InteriorExposureV1"
SOURCE_FILE = ROOT / "Content/MikdashV3/Maps/Courtyard.umap"
DESTINATION_FILE = ROOT / "Content/MikdashV3/MaterialReview/InteriorExposureV1/Courtyard_InteriorExposureV1.umap"
SPEC_FILE = ROOT / "SourceAssets/visual-review/interior-exposure-pilot-spec.json"


def sha_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
            if isinstance(component, unreal.SkyLightComponent):
                entry["sky"] = {key: normalized(component.get_editor_property(key), world)
                                for key in ("source_type", "real_time_capture", "cubemap")}
            row["components"].append(entry)
        row["components"].sort(key=lambda item: item["name"])
        rows.append(row)
    rows.sort(key=lambda item: item["name"])
    return {"actorCount": len(rows), "semanticInventorySha256": digest(rows)}


def get_volume():
    volumes = [actor for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
               if isinstance(actor, unreal.PostProcessVolume)]
    assert len(volumes) == 1, "Expected the existing single global postprocess volume"
    return volumes[0]


def run():
    assert Path(unreal.Paths.project_dir()).resolve() == ROOT
    spec = json.loads(SPEC_FILE.read_text(encoding="utf-8"))
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    assert not editor.get_game_world(), "Stop PIE first"
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Preserve unsaved map work first"
    assert not assets.does_asset_exist(DESTINATION) and not DESTINATION_FILE.exists(), "Pilot already exists; inspect it, do not overwrite"
    assert not assets.does_directory_exist(DESTINATION.rsplit("/", 1)[0]), "Pilot namespace already exists"
    assert level.load_level(SOURCE), "Source map load failed"
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    before_sha = sha_file(SOURCE_FILE)
    before_scene = scene_snapshot(editor)
    assert before_scene["actorCount"] == 7281, "Unexpected source-map inventory; review before creating pilot"
    source_settings = get_volume().get_editor_property("settings").copy()
    assert source_settings.get_editor_property("auto_exposure_method") == unreal.AutoExposureMethod.AEM_MANUAL
    assert source_settings.get_editor_property("auto_exposure_bias") == 1.0
    extended = unreal.SystemLibrary.get_console_variable_int_value(
        "r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange")
    assert extended in (0, 1)
    # Installed RenderUtils.h: EV100ToLuminance(LuminanceMax, EV)=LuminanceMax*2**EV.
    # In legacy mode PostProcessEyeAdaptation.cpp uses LuminanceMax=1 and treats
    # Min/MaxBrightness as luminance. Preserve project mode; translate pilot bounds.
    settings = {
        "auto_exposure_method": unreal.AutoExposureMethod.AEM_HISTOGRAM,
        "auto_exposure_min_brightness": 0.0 if extended else 1.0,
        "auto_exposure_max_brightness": 16.0 if extended else 65536.0,
        "histogram_log_min": -4.0,
        "histogram_log_max": 20.0,
        "auto_exposure_speed_up": 3.0,
        "auto_exposure_speed_down": 1.0,
        "auto_exposure_low_percent": 10.0,
        "auto_exposure_high_percent": 90.0,
    }
    for name in list(settings):
        settings["override_" + name] = True
    # Validate all reflected Python names and override flags before mutation.
    original_values = {name: source_settings.get_editor_property(name) for name in settings}
    camera = editor.get_level_viewport_camera_info()
    report = {
        "status": "creating", "sourceMap": SOURCE, "pilotMap": DESTINATION,
        "originalMapSha256": before_sha, "beforeScene": before_scene,
        "extendedLuminanceRange": extended,
        "appliedSettings": {name: str(value) for name, value in settings.items()},
        "visualAcceptance": "PENDING", "packagedAcceptance": "PENDING",
    }
    try:
        # EditorLoadingAndSavingUtils.NewMapFromTemplate creates a separate unsaved
        # world from the source package; SaveMap receives only the unique pilot path.
        world = unreal.EditorLoadingAndSavingUtils.new_map_from_template(SOURCE, False)
        assert world, "Template copy failed"
        assert scene_snapshot(editor) == before_scene, "Template-copy inventory differs"
        volume = get_volume()
        candidate = volume.get_editor_property("settings")
        assert candidate.export_text() == source_settings.export_text(), "Template settings differ"
        for name, value in settings.items():
            candidate.set_editor_property(name, value)
        volume.set_editor_property("settings", candidate)
        assert unreal.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(), DESTINATION), "Pilot save failed"
        assert DESTINATION_FILE.exists()
        assert sha_file(SOURCE_FILE) == before_sha, "Original map changed"
        assert level.load_level(DESTINATION), "Pilot reopen failed"
        assert editor.get_editor_world().get_path_name().split(".")[0] == DESTINATION
        reopened = get_volume().get_editor_property("settings")
        for name, expected in settings.items():
            assert reopened.get_editor_property(name) == expected, "Readback mismatch: " + name
        restored_copy = reopened.copy()
        for name, old_value in original_values.items():
            restored_copy.set_editor_property(name, old_value)
        assert restored_copy.export_text() == source_settings.export_text(), "Unexpected postprocess field change"
        after_scene = scene_snapshot(editor)
        assert after_scene == before_scene, "Pilot semantic scene inventory differs"
        assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        report.update(status="saved_reopened_semantically_verified", afterScene=after_scene,
                      onlySelectedPostprocessFieldsChanged=True,
                      pilotMapSha256=sha_file(DESTINATION_FILE))
    except Exception as error:
        report.update(status="failed_partial_pilot_requires_review", error=str(error))
        raise
    finally:
        # Restore production map for the next serialized task. No save is requested.
        report["originalMapUnchanged"] = sha_file(SOURCE_FILE) == before_sha
        try:
            report["sourceMapRestored"] = bool(level.load_level(SOURCE))
            if report["sourceMapRestored"] and camera:
                editor.set_level_viewport_camera_info(camera[0], camera[1])
        finally:
            spec["execution"] = report
            SPEC_FILE.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        assert report["originalMapUnchanged"], "Original map hash mismatch"
        assert report["sourceMapRestored"], "Could not restore source-map view"
    unreal.log("INTERIOR_EXPOSURE_PILOT_SAVED_REOPENED_VISUAL_REVIEW_PENDING")


run()

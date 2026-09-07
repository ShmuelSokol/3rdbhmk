"""Explicit build(review_map_path, portal_fill=False): isolated material/light test.
No engine action on import. Preserve original review assets, exposure and geometry.
"""
import json
from pathlib import Path
import time
ROOT=Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
DEST="/Game/MikdashV3/MaterialReview/SanctuaryPolishV1"
GOLD="/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/M_Sanctuary_gold"
KEILIM="/Game/MikdashV3/MaterialReview/HeikhalKeilimV1/M_HeikhalKeilim_Gold"
ROUGHNESS={"Wall":.48,"Floor":.55,"Vessel":.38}


def build(review_map_path,portal_fill=False):
    import unreal as u
    assert review_map_path.startswith(DEST+"/Maps/")
    assert Path(u.Paths.project_dir()).resolve()==ROOT
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    assert not editor.get_game_world()
    assert editor.get_editor_world().get_path_name().split(".")[0]==review_map_path
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    original=actors.get_all_level_actors()
    selected=[]; exposure=[]; lights=[]
    for a in original:
        if isinstance(a,u.PostProcessVolume):
            exposure.append((a,a.get_editor_property("settings").export_text()))
        for c in a.get_components_by_class(u.LightComponentBase):
            lights.append(dict(actor=a.get_path_name(),type=c.get_class().get_name(),intensity=float(c.get_editor_property("intensity"))))
        for c in a.get_components_by_class(u.StaticMeshComponent):
            if c.get_num_materials()!=1:continue
            mat=c.get_material(0)
            path=mat.get_path_name().split(".")[0] if mat else ""
            if path not in (GOLD,KEILIM):continue
            mesh=c.static_mesh.get_path_name() if c.static_mesh else ""
            kind="Vessel" if path==KEILIM else "Floor" if "clear_floor" in mesh else "Wall"
            selected.append((c,list(c.get_editor_property("override_materials")),kind))
    assert sum(k=="Vessel" for c,o,k in selected)==2,"Need both studied keilim in template"
    assert sum(k=="Floor" for c,o,k in selected)==2
    assert sum(k=="Wall" for c,o,k in selected)>=11,"Need sanctuary veneer/partition/ceiling scope"
    assets=u.EditorAssetLibrary
    assert all(not assets.does_asset_exist(DEST+"/M_Gold"+k) for k in ROUGHNESS)
    receipt=ROOT/"SourceAssets/visual-review"/("sanctuary-polish-native-"+time.strftime("%Y%m%dT%H%M%S")+".json")
    assert not receipt.exists()
    report=dict(status="building",map=review_map_path,mapSaved=False,portalFillRequested=portal_fill,originalLights=lights,overrides=[],interpretation="Roughness is artistic finish response. Optional rectangle is a render-only doorway daylight proxy, not a historical fixture or claim of real measured lighting.")
    created=[]
    try:
        materials={};edit=u.MaterialEditingLibrary
        for kind,roughness in ROUGHNESS.items():
            m=u.AssetToolsHelpers.get_asset_tools().create_asset("M_Gold"+kind,DEST,u.Material,u.MaterialFactoryNew());assert m
            color=edit.create_material_expression(m,u.MaterialExpressionConstant3Vector,-300,0)
            color.set_editor_property("constant",u.LinearColor(1,.766,.336,1))
            assert edit.connect_material_property(color,"",u.MaterialProperty.MP_BASE_COLOR)
            for value,prop in ((1,u.MaterialProperty.MP_METALLIC),(roughness,u.MaterialProperty.MP_ROUGHNESS)):
                n=edit.create_material_expression(m,u.MaterialExpressionConstant)
                n.set_editor_property("r",value);assert edit.connect_material_property(n,"",prop)
            edit.recompile_material(m);assert assets.save_loaded_asset(m,only_if_is_dirty=False)
            materials[kind]=m
        for c,overrides,kind in selected:
            report["overrides"].append(dict(component=c.get_path_name(),kind=kind,original=[m.get_path_name() if m else None for m in overrides]))
            c.set_material(0,materials[kind]);assert c.get_material(0)==materials[kind]
        if portal_fill:
            # Inside verified doorway X[-3600,-3300], Y[-250,250], Z[925,3425].
            # Rect emitter faces west; area stays inside aperture, camera is unchanged.
            a=actors.spawn_actor_from_class(u.RectLight,u.Vector(-3590,0,1900),u.Rotator(pitch=0,yaw=180,roll=0));assert a
            created.append(a);a.set_actor_label("Review_DoorwayDaylightProxy")
            a.set_folder_path("Material review/Sanctuary polish")
            c=a.get_component_by_class(u.RectLightComponent)
            c.set_mobility(u.ComponentMobility.MOVABLE)
            c.set_editor_property("intensity_units",u.LightUnits.LUMENS)
            c.set_intensity(1200)
            c.set_editor_property("source_width",400.0)
            c.set_editor_property("source_height",1000.0)
            c.set_attenuation_radius(2600)
            c.set_editor_property("use_temperature",True)
            c.set_temperature(5500)
            report["portalFill"]=dict(locationCm=[-3590,0,1900],yaw=180,widthCm=400,heightCm=1000,lumens=1200,kelvin=5500,attenuationRadiusCm=2600)
        assert all(a.get_editor_property("settings").export_text()==text for a,text in exposure),"Global postprocess changed"
        assert len(actors.get_all_level_actors())==len(original)+len(created)
        report.update(status="APPLIED_REVIEW_MAP_UNSAVED_VISUAL_ACCEPTANCE_PENDING",targetCount=len(selected),globalExposureUnchanged=True,geometryUnchanged=True)
    except Exception as error:
        errors=[]
        for c,o,k in selected:
            try:c.set_editor_property("override_materials",o)
            except Exception as restore_error:errors.append(str(restore_error))
        for a in created:
            try:assert actors.destroy_actor(a)
            except Exception as restore_error:errors.append(str(restore_error))
        report.update(status="FAILED_DISCARD_REVIEW_MAP",error=str(error),restoreErrors=errors)
        raise
    finally:receipt.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

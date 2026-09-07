"""Explicit build(review_map_path) only; no startup or editor execution on import.
Adds runtime cloud/wind/sequence to a separate review map. Never saves a map.
Wind is an artistic bounded loop, not real meteorology or generic foliage physics.
"""
import json
from pathlib import Path
import time

ROOT=Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
DEST="/Game/MikdashV3/MaterialReview/AtmospherePilotV1"
CLOUD="/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst"
TAG="AtmospherePilotV1"
FPS=30
# Seconds, strength, speed: bounded artistic values, not metres/second.
WIND_KEYS=((0,.18,.25),(12,.24,.32),(26,.42,.48),(39,.21,.29),(55,.32,.40),(72,.18,.25))


def build(review_map_path):
    import unreal
    assert review_map_path.startswith(DEST+"/Maps/"), "Open a separate saved review map copy"
    assert Path(unreal.Paths.project_dir()).resolve()==ROOT
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assert not editor.get_game_world(), "Stop PIE first"
    assert editor.get_editor_world().get_path_name().split(".")[0]==review_map_path
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    original=actors.get_all_level_actors()
    assert not any(TAG in [str(t) for t in a.tags] for a in original)
    assert not any(isinstance(a,unreal.VolumetricCloud) for a in original), "Existing cloud needs explicit reconciliation"
    assert not any(isinstance(a,unreal.WindDirectionalSource) for a in original), "Existing wind needs explicit reconciliation"
    assert any(isinstance(a,unreal.SkyAtmosphere) for a in original)
    sun=[a.get_component_by_class(unreal.DirectionalLightComponent) for a in original if isinstance(a,unreal.DirectionalLight)]
    assert any(c.get_editor_property("atmosphere_sun_light") for c in sun)
    library=unreal.EditorAssetLibrary
    paths=(DEST+"/MI_Cloud",DEST+"/LS_GentleVariableWind")
    assert all(not library.does_asset_exist(p) for p in paths), "Fresh namespace required; prior assets preserved"
    material=unreal.load_asset(CLOUD)
    assert isinstance(material,unreal.MaterialInterface)
    created=[]
    report=dict(status="building",map=review_map_path,mapSaved=False,originalActorCount=len(original),cloudParent=CLOUD,windKeys=WIND_KEYS,originalSkyLightingExposureChanged=False,treesChanged=False)
    receipt=ROOT/"SourceAssets/visual-review"/("atmosphere-native-"+time.strftime("%Y%m%dT%H%M%S")+".json")
    assert not receipt.exists()
    def spawn(cls,label,rotation=None):
        a=actors.spawn_actor_from_class(cls,unreal.Vector(0,0,0),rotation or unreal.Rotator())
        assert a
        created.append(a)
        a.set_actor_label(label)
        a.set_folder_path("Material review/Atmosphere")
        a.set_editor_property("tags",[unreal.Name(TAG)])
        assert not a.get_editor_property("is_editor_only_actor")
        return a
    try:
        cloud_material=library.duplicate_asset(CLOUD,paths[0])
        assert cloud_material
        assert library.save_loaded_asset(cloud_material,only_if_is_dirty=False)
        cloud=spawn(unreal.VolumetricCloud,"Review_VolumetricCloud")
        component=cloud.get_component_by_class(unreal.VolumetricCloudComponent)
        component.set_material(cloud_material)
        component.set_layer_bottom_altitude(1.8)
        component.set_layer_height(2.4)
        assert abs(component.get_editor_property("layer_bottom_altitude")-1.8)<.001
        assert abs(component.get_editor_property("layer_height")-2.4)<.001
        assert component.get_editor_property("material")==cloud_material
        # Engine defaults for density, drift, scattering/sample count remain intact.
        # Their live parameter values are captured instead of guessing names/units.
        edit=unreal.MaterialEditingLibrary
        report["cloudScalarParameterNames"]=[str(n) for n in edit.get_scalar_parameter_names(cloud_material)]
        report["cloudVectorParameterNames"]=[str(n) for n in edit.get_vector_parameter_names(cloud_material)]
        wind=spawn(unreal.WindDirectionalSource,"Review_GentleVariableWind",unreal.Rotator(0,25,0))
        wc=wind.get_component_by_class(unreal.WindDirectionalSourceComponent)
        wc.set_strength(.18);wc.set_speed(.25)
        wc.set_minimum_gust_amount(.05);wc.set_maximum_gust_amount(.15)
        assert not wc.get_editor_property("point_wind")
        sequence=unreal.AssetToolsHelpers.get_asset_tools().create_asset("LS_GentleVariableWind",DEST,unreal.LevelSequence,unreal.LevelSequenceFactoryNew())
        assert sequence
        sequence.set_display_rate(unreal.FrameRate(FPS,1))
        sequence.set_playback_start(0);sequence.set_playback_end(72*FPS)
        parent=sequence.add_possessable(wind)
        binding=sequence.add_possessable(wc)
        binding.set_parent(parent)
        for prop,index in (("Strength",1),("Speed",2)):
            track=binding.add_track(unreal.MovieSceneFloatTrack)
            track.set_property_name_and_path(prop,prop)
            section=track.add_section();section.set_range(0,72*FPS+1)
            channels=section.get_all_channels();assert len(channels)==1
            for key in WIND_KEYS:
                channels[0].add_key(unreal.FrameNumber(key[0]*FPS),key[index],interpolation=unreal.MovieSceneKeyInterpolation.LINEAR)
        assert library.save_loaded_asset(sequence,only_if_is_dirty=False)
        player=spawn(unreal.LevelSequenceActor,"Review_WindSequence")
        settings=unreal.MovieSceneSequencePlaybackSettings()
        settings.set_editor_property("auto_play",True)
        settings.set_editor_property("loop_count",unreal.MovieSceneSequenceLoopCount(-1))
        settings.set_editor_property("disable_camera_cuts",True)
        settings.set_editor_property("disable_movement_input",False)
        settings.set_editor_property("disable_look_at_input",False)
        player.set_editor_property("playback_settings",settings)
        player.set_sequence(sequence)
        # No Play call here: runtime autoplay after approved map save/reopen.
        assert len(actors.get_all_level_actors())==len(original)+3
        report.update(status="APPLIED_UNSAVED_NATIVE_RUNTIME_AND_VISUAL_ACCEPTANCE_PENDING",createdActors=[a.get_path_name() for a in created],sequence=paths[1],cloudMaterial=paths[0],windConsumerLimitation="Engine directional wind affects SpeedTree-compatible materials. Current generic context trees and cloth have no verified response; no implied coupling with cloud drift.")
    except Exception as error:
        errors=[]
        for a in reversed(created):
            try: assert actors.destroy_actor(a)
            except Exception as restore_error: errors.append(str(restore_error))
        report.update(status="FAILED_REVIEW_MAP_DISCARD_REQUIRED",error=str(error),restoreErrors=errors)
        raise
    finally:
        receipt.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

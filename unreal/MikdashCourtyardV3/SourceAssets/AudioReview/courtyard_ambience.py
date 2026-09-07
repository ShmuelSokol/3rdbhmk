"""UE5.7 editor authoring only; importing this module is inert.
Explicit apply creates a cooked SoundWave reference and one AmbientSound actor.
No Python tick, browser audio, cloud/network activity or playback success claim.
"""
from pathlib import Path
import hashlib
import json
import math
import wave

MAP = "/Game/MikdashV3/Maps/Courtyard"
DEST = "/Game/MikdashV3/Runtime/Audio"
NAME = "SW_CourtyardOriginal_Pilot01"
LABEL = "Courtyard original ambience pilot"
TAG = "MikdashCourtyardOriginalAmbience"


def apply(*, architecture_and_placement_validated=False,
          source_coordinates=(110.0, 9.0, 24.0), volume=0.28,
          inner_radius_cm=1200.0, falloff_cm=7000.0, save_map=False,
          wav_path=None, receipt_path=None):
    """Explicit authoring call, AFTER actual map/placement validation.

    Default candidate lies in the source outer visitor zone, above its level6
    floor. Source coordinate order is amos [east,up,south]; UE is cm [x,z,y]*50.
    This zoning check does not replace cloud geometry/collision/source review.
    By default the actor dirties the map but does not save unrelated map changes.
    Save the reviewed map explicitly (or pass save_map=True) before packaging.
    """
    if not architecture_and_placement_validated:
        raise RuntimeError("Validate current architecture, source axes and this outer-court placement first")
    values = (*source_coordinates, volume, inner_radius_cm, falloff_cm)
    if len(source_coordinates) != 3 or not all(math.isfinite(v) for v in values):
        raise ValueError("Finite source coordinates/parameters required")
    x, y, z = source_coordinates
    if not (75 < x < 150 and abs(z) < 50 and 6 < y < 15):
        raise ValueError("This bounded pilot only supports the reviewed outer-court candidate zone")
    if not (0 <= volume <= .5 and 100 <= inner_radius_cm <= 3000 and 500 <= falloff_cm <= 10000):
        raise ValueError("Keep the pilot volume0..0.5, inner radius1..30m and falloff5..100m")
    wav = Path(wav_path) if wav_path else Path(__file__).with_name("courtyard_pcm.wav")
    receipt = Path(receipt_path) if receipt_path else Path(__file__).with_name("authoring-receipt.json")
    if receipt.exists():
        raise FileExistsError("Refusing to overwrite authoring receipt: " + str(receipt))
    with wave.open(str(wav)) as stream:
        if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (2, 2, 24000):
            raise ValueError("Expected bundled stereo24kHz16-bit PCM WAV")
        duration = stream.getnframes()/stream.getframerate()
    sha = hashlib.sha256(wav.read_bytes()).hexdigest()
    manifest = json.loads(Path(__file__).with_name("provenance.json").read_text())
    expected_sha = next(f["sha256"] for f in manifest["files"] if f["path"].endswith("courtyard_pcm.wav"))
    if sha != expected_sha:
        raise ValueError("WAV does not match reviewed provenance manifest")

    import unreal
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if levels.is_in_play_in_editor():
        raise RuntimeError("Stop PIE before editor asset authoring")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or world.get_path_name().split(".")[0] != MAP:
        raise RuntimeError("Open the saved Courtyard map; helper never opens/replaces maps")
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    sound_path = DEST + "/" + NAME
    if assets.does_asset_exist(sound_path):
        raise FileExistsError("Refusing existing sound asset: " + sound_path)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # Loaded actor list only, no filesystem/asset-tree discovery.
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label() == LABEL or TAG in [str(t) for t in actor.get_editor_property("tags")]:
            raise RuntimeError("Pilot ambience already placed; refusing duplicate source")

    task = unreal.AssetImportTask()
    for key, value in dict(filename=str(wav.resolve()), destination_path=DEST,
                           destination_name=NAME, automated=True, replace_existing=False,
                           save=False).items():
        task.set_editor_property(key, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sound = unreal.load_asset(sound_path)
    if not isinstance(sound, unreal.SoundWave):
        raise RuntimeError("SoundWave import failed; inspect the new import before retry")
    sound.set_editor_property("looping", True)
    sound.set_editor_property("volume", 1.0)
    sound.set_editor_property("pitch", 1.0)
    sound.set_editor_property("comment", "Original project synthesized ambience, seed46. Temporary mix; not ancient melody, voice recording or ceremony evidence.")
    if not assets.save_loaded_asset(sound):
        raise RuntimeError("Saving new SoundWave failed")
    position = unreal.Vector(x*50, z*50, y*50)
    actor = actors.spawn_actor_from_class(unreal.AmbientSound, position, unreal.Rotator(), transient=False)
    if not actor:
        raise RuntimeError("AmbientSound placement failed; new sound asset remains for review")
    actor.set_actor_label(LABEL)
    actor.set_editor_property("tags", [unreal.Name(TAG)])
    component = actor.get_editor_property("audio_component")
    attenuation = unreal.SoundAttenuationSettings()
    settings = dict(attenuate=True, spatialize=True,
                    distance_algorithm=unreal.AttenuationDistanceModel.LINEAR,
                    attenuation_shape=unreal.AttenuationShape.SPHERE,
                    attenuation_shape_extents=unreal.Vector(inner_radius_cm,0,0),
                    falloff_distance=falloff_cm, stereo_spread=400.0,
                    non_spatialized_radius_start=1200.0, non_spatialized_radius_end=400.0,
                    apply_normalization_to_stereo_sounds=True,
                    spatialization_algorithm=unreal.SoundSpatializationAlgorithm.SPATIALIZATION_DEFAULT,
                    enable_occlusion=False)
    for key, value in settings.items():
        attenuation.set_editor_property(key, value)
    for key, value in dict(sound=sound, auto_activate=True, volume_multiplier=volume,
                           override_attenuation=True, attenuation_overrides=attenuation).items():
        component.set_editor_property(key, value)
    # No play() call: persistent component activation supplies runtime playback.
    if save_map and not levels.save_current_level():
        raise RuntimeError("Saving current level failed; inspect unsaved new actor")
    result = dict(status="authored_not_auditioned", map=MAP, sound=sound_path,
                  actor=actor.get_path_name(), sourceCoordinatesAmos=list(source_coordinates),
                  unrealCoordinatesCm=[x*50,z*50,y*50], volumeMultiplier=volume,
                  innerRadiusCm=inner_radius_cm, falloffCm=falloff_cm,
                  stereoSpreadCm=400, stereoNormalization=True, looping=True,
                  nearSpatialBlendStartCm=1200, nearFullyNonSpatialCm=400,
                  durationSeconds=duration, wavSHA256=sha, mapSaved=save_map,
                  heardInUnreal=False, heardThroughRemotePath=False,
                  cookStatus="NOT TESTED; saved map must retain actor-to-SoundWave reference",
                  next="Audition60s, check seam/distance/mute/remote audio, then packaged build")
    with receipt.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    unreal.log(json.dumps(result))
    return result

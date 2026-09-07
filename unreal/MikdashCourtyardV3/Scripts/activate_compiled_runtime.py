import unreal, json, shutil, hashlib
from pathlib import Path

root = Path(unreal.Paths.project_dir()).resolve()
assert root == Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level('/Game/MikdashV3/Maps/Courtyard')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
settings = world.get_world_settings()
old_mode = settings.get_editor_property('default_game_mode')
assert old_mode and 'BP_MikdashGameMode_C' in old_mode.get_path_name()
controller = unreal.load_class(None, '/Script/MikdashRuntime.MikdashPlayerController')
assert controller, 'Compiled controller unavailable'
destination = '/Game/MikdashV3/Gameplay/BP_MikdashRuntimeGameMode'
assert not assets.does_asset_exist(destination), 'Already created; inspect before rerunning'
checkpoint = root.parent / 'Checkpoints' / 'Before-Runtime-Activation'
checkpoint.mkdir(exist_ok=False)
map_file = root / 'Content/MikdashV3/Maps/Courtyard.umap'
shutil.copy2(map_file, checkpoint / map_file.name)
bp = assets.duplicate_asset('/Game/MikdashV3/Gameplay/BP_MikdashGameMode', destination)
assert bp
mode_class = unreal.load_class(None, destination + '.BP_MikdashRuntimeGameMode_C')
cdo = unreal.get_default_object(mode_class)
old_cdo = unreal.get_default_object(old_mode)
pawn = cdo.get_editor_property('default_pawn_class')
assert pawn == old_cdo.get_editor_property('default_pawn_class')
assert 'BP_MikdashWalker_C' in pawn.get_path_name()
cdo.modify()
cdo.set_editor_property('player_controller_class', controller)
assert unreal.BlueprintEditorLibrary.compile_blueprint(bp)
assert assets.save_loaded_asset(bp)
settings.modify()
settings.set_editor_property('default_game_mode', mode_class)
assert level.save_current_level()
assert level.load_level('/Game/MikdashV3/Maps/Courtyard')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
saved_mode = world.get_world_settings().get_editor_property('default_game_mode')
saved_cdo = unreal.get_default_object(saved_mode)
assert saved_cdo.get_editor_property('player_controller_class') == controller
assert saved_cdo.get_editor_property('default_pawn_class') == pawn
result = {'status': 'saved_reopened', 'controller': controller.get_path_name(),
          'gameMode': saved_mode.get_path_name(), 'pawn': pawn.get_path_name(),
          'mapSha256': hashlib.sha256(map_file.read_bytes()).hexdigest(),
          'checkpoint': str(checkpoint), 'runtimeTested': False}
(root / 'SourceAssets/runtime-review/runtime-activation.json').write_text(json.dumps(result, indent=2))
unreal.log('MIKDASH_RUNTIME_ACTIVATION_SAVED_REOPENED')

"""UE 5.7 editor helper DRAFT; no runtime Python or import-time side effects.

Requires a migrated, already working first-person Character and its GameMode
Blueprint, including all controller/input dependencies. This does not create an
input event graph, migrate assets, cook/package, or claim gameplay passed.
"""
import unreal


def _child(asset_path, parent_class):
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    if assets.does_asset_exist(asset_path):
        raise RuntimeError('Refusing to overwrite existing Blueprint: ' + asset_path)
    bp = unreal.BlueprintEditorLibrary.create_blueprint_asset_with_parent(asset_path, parent_class)
    if not bp:
        raise RuntimeError('Blueprint creation failed: ' + asset_path)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cls = unreal.BlueprintEditorLibrary.generated_class(bp)
    if not cls:
        raise RuntimeError('No generated class: ' + asset_path)
    return bp, cls


def prepare_gameplay(template_character_path, template_game_mode_path,
                     player_start_cm, yaw_degrees,
                     destination='/Game/MikdashV3/Gameplay'):
    """Create children + PlayerStart in CURRENT editor map; caller saves map.

    player_start_cm is the pawn capsule CENTER, not floor/eye position. Obtain
    actual capsule half-height from the migrated pawn before choosing it.
    Destination must be unused. Function deliberately fails on repeated use.
    """
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character_parent = assets.load_blueprint_class(template_character_path)
    mode_parent = assets.load_blueprint_class(template_game_mode_path)
    if not character_parent or not mode_parent:
        raise RuntimeError('Migrate the actual Character + GameMode dependencies first')
    if not isinstance(unreal.get_default_object(character_parent), unreal.Character):
        raise RuntimeError('Requires a walking Character, not DefaultPawn/SpectatorPawn')
    if not isinstance(unreal.get_default_object(mode_parent), unreal.GameModeBase):
        raise RuntimeError('Template mode is not a GameModeBase subclass')
    existing_starts = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
    if existing_starts:
        raise RuntimeError('Resolve existing PlayerStarts first; do not create random competing spawns')
    settings = [unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()]
    if len(settings) != 1:
        raise RuntimeError('Cannot uniquely identify current map WorldSettings')
    for name in ['BP_MikdashWalker', 'BP_MikdashGameMode']:
        if assets.does_asset_exist(destination + '/' + name):
            raise RuntimeError('Destination already used: ' + destination)
    assets.make_directory(destination)
    pawn_bp, pawn_cls = _child(destination + '/BP_MikdashWalker', character_parent)
    mode_bp, mode_cls = _child(destination + '/BP_MikdashGameMode', mode_parent)
    # Inherit the template controller, input mapping graph and camera unchanged.
    # Changing the mode's class defaults is editor authoring of cooked runtime data.
    unreal.get_default_object(mode_cls).set_editor_property('default_pawn_class', pawn_cls)
    if not assets.save_loaded_asset(pawn_bp) or not assets.save_loaded_asset(mode_bp):
        raise RuntimeError('Could not save gameplay Blueprints')
    settings[0].set_editor_property('default_game_mode', mode_cls)
    start = actors.spawn_actor_from_class(
        unreal.PlayerStart, unreal.Vector(*player_start_cm),
        unreal.Rotator(roll=0.0, pitch=0.0, yaw=float(yaw_degrees)), transient=False)
    if not start:
        raise RuntimeError('PlayerStart creation failed')
    start.set_actor_label('Mikdash_PlayerStart')
    report = {
        'status': 'AUTHORED_NOT_RUNTIME_TESTED',
        'walker_class': pawn_cls.get_path_name(),
        'game_mode_class': mode_cls.get_path_name(),
        'inherited_controller_class': str(unreal.get_default_object(mode_cls).get_editor_property('player_controller_class')),
        'player_start_cm': list(player_start_cm),
        'world_game_mode': str(settings[0].get_editor_property('default_game_mode')),
        'map_must_be_saved_by_caller': True,
        'remaining': ['verify inherited input mappings and first-person camera',
                      'validate capsule/floor/wall/stair/ramp collisions',
                      'save map and configure GameDefaultMap',
                      'cook/package Windows and test exe without editor'],
    }
    unreal.log(str(report))
    return report


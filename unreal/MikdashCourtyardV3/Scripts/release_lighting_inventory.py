"""Read-only saved lighting/camera exposure diagnosis; serial native commandlet."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


def run():
    import unreal as u
    assert Path(u.Paths.project_dir()).resolve() == ROOT.resolve()
    assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    map_file = ROOT / 'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap'
    sha = lambda: hashlib.sha256(map_file.read_bytes()).hexdigest()
    before = sha()
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP)
    report = dict(status='read_only_lighting_inventory', beforeMapSha256=before,
                  cameras=[], volumes=[], lights=[])
    fields = ['auto_exposure_method', 'auto_exposure_min_brightness', 'auto_exposure_max_brightness',
              'auto_exposure_bias', 'auto_exposure_apply_physical_camera_exposure',
              'override_auto_exposure_method', 'override_auto_exposure_min_brightness',
              'override_auto_exposure_max_brightness', 'override_auto_exposure_bias']

    def props(obj, names):
        row = {}
        for name in names:
            try:
                value = obj.get_editor_property(name)
                row[name] = value if isinstance(value, (int, float, str, bool)) else str(value)
            except Exception as exc:
                row[name] = dict(unavailable=str(exc))
        return row

    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        if isinstance(actor, u.PostProcessVolume):
            report['volumes'].append(dict(label=actor.get_actor_label(),
                exposure=props(actor.get_editor_property('settings'), fields),
                volume=props(actor, ['enabled', 'unbound', 'blend_weight', 'priority'])))
        if isinstance(actor, u.CameraActor):
            component = actor.get_component_by_class(u.CameraComponent)
            report['cameras'].append(dict(label=actor.get_actor_label(),
                exposure=props(component.get_editor_property('post_process_settings'), fields),
                blendWeight=component.get_editor_property('post_process_blend_weight')))
        for component in actor.get_components_by_class(u.LightComponent):
            report['lights'].append(dict(label=actor.get_actor_label(),
                properties=props(component, ['intensity', 'use_temperature', 'temperature', 'light_color',
                                             'visible', 'indirect_lighting_intensity', 'attenuation_radius'])))
    report['afterMapSha256'] = sha()
    report['mapBytesUnchanged'] = before == report['afterMapSha256']
    out = ROOT / 'SourceAssets/lighting-review' / ('lighting-inventory-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    assert report['mapBytesUnchanged']
    u.log('LIGHTING_INVENTORY ' + str(out))


if __name__ == '__main__':
    run()

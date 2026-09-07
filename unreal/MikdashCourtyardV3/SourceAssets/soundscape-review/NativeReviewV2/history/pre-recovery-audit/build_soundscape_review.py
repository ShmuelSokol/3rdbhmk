"""Native review authoring, explicit invocation only; importing this module does nothing.
Root must first prepare and open a saved duplicate inside DEST/Maps/.
No automatic playback; audition is a separate bounded call. Never a runtime adapter.
"""
from pathlib import Path
import hashlib
import json
import math
import random
import time

ROOT = Path(__file__).resolve().parents[1]
DEST = '/Game/MikdashV3/SoundscapeReview/NativeReviewV2'
OUT = ROOT / 'SourceAssets/soundscape-review/NativeReviewV2'
TAG = 'SoundscapeNativeReviewV2'
ACTIVE = None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan():
    frozen = json.loads((OUT.parent / 'signal-review.json').read_text())
    sources = [dict(item, name='SW_' + Path(item['path']).stem.replace('-', '_'))
               for item in [frozen['wind']] + frozen['derived']]
    require(len(sources) == 13, 'Expected wind plus twelve mono footsteps')
    for item in sources:
        require(sha(ROOT / item['path']) == item['sha256'], 'Frozen audio changed')
    return sources


def guard(map_path, clean=True):
    import unreal as ue
    require(map_path.startswith(DEST + '/Maps/') and '..' not in map_path and '.' not in map_path,
            'Use a separately saved review map under the owned namespace')
    require(Path(ue.Paths.project_dir()).resolve() == ROOT, 'Wrong project')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    require(not editor.get_game_world(), 'Stop PIE before authoring/audition')
    require(editor.get_editor_world().get_path_name().split('.')[0] == map_path, 'Open intended review copy first')
    if clean:
        require(not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Unsaved maps; preserve work')
        require(not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Unsaved assets; preserve work')
    return ue


def original_hashes():
    paths = [ROOT / 'Content/MikdashV3/Maps/Courtyard.umap',
             ROOT / 'Content/MikdashV3/FutureMountV1/L_FutureMount.umap']
    return {str(p): sha(p) for p in paths if p.exists()}


def build(map_path, foot_location_cm, wind_location_cm):
    """Root supplies reviewed floor and outdoor positions. Saves owned assets/map only.
    Any failure leaves explicit partial state for inspection, never deletes or retries.
    """
    global ACTIVE
    require(ACTIVE is None, 'Stop active audition first')
    for pos in (foot_location_cm, wind_location_cm):
        require(len(pos) == 3 and all(math.isfinite(v) for v in pos), 'Finite XYZ required')
    sources = plan()
    ue = guard(map_path)
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    require(not assets.does_directory_exist(DEST + '/Audio'), 'Existing import; inspect receipt, do not rerun')
    require(not any(TAG in [str(t) for t in a.tags] for a in actors.get_all_level_actors()), 'Actors already exist')
    before = original_hashes()
    report = dict(status='started', map=map_path, originals_before=before, assets=[], actors=[],
                  audition='PENDING', native_import='PENDING', interior='quiet; no room-tone asset',
                  floor_location_cm=foot_location_cm, wind_location_cm=wind_location_cm)
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = OUT / ('native-' + time.strftime('%Y%m%dT%H%M%S') + '.json')
    require(not receipt.exists(), 'Receipt name collision')
    try:
        for item in sources:
            task = ue.AssetImportTask()
            task.filename = str(ROOT / item['path'])
            task.destination_path = DEST + '/Audio'
            task.destination_name = item['name']
            task.automated = True
            task.replace_existing = False
            task.save = False
            ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            objects = list(task.get_objects())
            require(len(objects) == 1 and isinstance(objects[0], ue.SoundWave), 'Expected one SoundWave')
            sound = objects[0]
            sound.set_editor_property('looping', False)
            sound.set_editor_property('volume', 1.0)
            require(abs(float(sound.get_editor_property('duration')) - item['duration_seconds']) < .02,
                    'Native duration mismatch')
            require(assets.save_loaded_asset(sound, only_if_is_dirty=False), 'Owned sound save failed')
            report['assets'].append(sound.get_path_name())
            is_wind = item['name'] == 'SW_park_ambience_wind'
            position = wind_location_cm if is_wind else foot_location_cm
            actor = actors.spawn_actor_from_class(ue.AmbientSound, ue.Vector(*position))
            require(actor is not None, 'Actor spawn failed')
            actor.set_actor_label(TAG + '_' + item['name'])
            actor.set_editor_property('tags', [ue.Name(TAG)])
            component = actor.get_component_by_class(ue.AudioComponent)
            component.stop()
            component.set_editor_property('auto_activate', False)
            component.set_sound(sound)
            component.set_volume_multiplier(.12 if is_wind else .18)
            attenuation = ue.SoundAttenuationSettings()
            attenuation.set_editor_property('attenuate', not is_wind)
            attenuation.set_editor_property('spatialize', not is_wind)
            attenuation.set_editor_property('attenuation_shape_extents', ue.Vector(150, 0, 0))
            attenuation.set_editor_property('falloff_distance', 1650.)
            attenuation.set_editor_property('enable_occlusion', not is_wind)
            component.set_editor_property('override_attenuation', True)
            component.set_attenuation_overrides(attenuation)
            require(not component.get_editor_property('auto_activate'), 'Autoplay must remain off')
            report['actors'].append(dict(path=actor.get_path_name(), label=actor.get_actor_label(), wind=is_wind))
        require(original_hashes() == before, 'Original map changed unexpectedly')
        require(ue.get_editor_subsystem(ue.LevelEditorSubsystem).save_current_level(), 'Review save failed')
        report.update(status='saved_review_requires_reopen_and_audition', native_import='saved; reopen unverified')
        return report
    except Exception as error:
        report.update(status='failed_partial_state_do_not_rerun', error=str(error))
        raise
    finally:
        report['originals_after'] = original_hashes()
        report['originals_unchanged'] = report['originals_after'] == before
        receipt.write_text(json.dumps(report, indent=2) + '\n')


def wind_gain(seconds):
    # Slow, bounded, nonperiodic authored control points; recording itself is never looped.
    knots = [(0,.08),(23,.105),(61,.085),(104,.12),(149,.095),(180,.08)]
    for (a,x),(b,y) in zip(knots, knots[1:]):
        if seconds <= b:
            t = max(0., (seconds-a)/(b-a))
            t = t*t*(3-2*t)
            return x+(y-x)*t
    return knots[-1][1]


def stop_audition():
    global ACTIVE
    if ACTIVE is not None:
        import unreal as ue
        state, ACTIVE = ACTIVE, None
        ue.unregister_slate_post_tick_callback(state['handle'])
        for component in state['components'].values():
            component.stop()
        state['components']['SW_park_ambience_wind'].set_volume_multiplier(.12)
        (OUT / ('audition-' + state['stamp'] + '.json')).write_text(json.dumps(dict(
            status='bounded_preview_stopped_not_listener_acceptance', elapsed=time.monotonic()-state['start'],
            bank=state['bank'], errors=state['errors'], listening='PENDING human verdict'), indent=2)+'\n')


def audition(map_path, seconds=120., bank='Stone'):
    """Explicit editor preview only, NOT walking or surface-hit simulation.
    Route real floor hits with MikdashSurfaceAudioRouting.h in production. No short loops.
    """
    global ACTIVE
    require(ACTIVE is None, 'Preview already active')
    require(5 <= seconds <= 180 and bank in ('Stone','Sand','Silent'), 'Invalid bounded preview')
    ue = guard(map_path)
    components = {}
    for actor in ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors():
        if TAG in [str(t) for t in actor.tags]:
            component = actor.get_component_by_class(ue.AudioComponent)
            sound = component.get_editor_property('sound')
            require(sound and sound.get_path_name().startswith(DEST + '/Audio/'), 'Foreign tagged sound')
            components[sound.get_name()] = component
    require(len(components) == 13, 'Expected full saved review rig')
    state = dict(components=components, start=time.monotonic(), stamp=time.strftime('%Y%m%dT%H%M%S'),
                 bank=bank, errors=[], next_step=2., side='L', previous={}, random=random.Random(771))
    def tick(_delta):
        try:
            elapsed = time.monotonic()-state['start']
            guard(map_path, clean=False)
            if elapsed >= seconds:
                stop_audition()
                return
            components['SW_park_ambience_wind'].set_volume_multiplier(wind_gain(elapsed))
            if bank != 'Silent' and elapsed >= state['next_step']:
                side = state['side']
                choices = [n for n in (1,2,3) if n != state['previous'].get(side)]
                index = state['random'].choice(choices)
                state['previous'][side] = index
                components['SW_Fantozzi_'+bank+side+str(index)+'_mono'].play()
                state['side'] = 'R' if side == 'L' else 'L'
                state['next_step'] = elapsed + state['random'].uniform(.58,.81)
        except Exception as error:
            state['errors'].append(str(error))
            stop_audition()
    state['handle'] = ue.register_slate_post_tick_callback(tick)
    ACTIVE = state
    try:
        components['SW_park_ambience_wind'].set_volume_multiplier(wind_gain(0))
        components['SW_park_ambience_wind'].play()
    except Exception:
        stop_audition()
        raise

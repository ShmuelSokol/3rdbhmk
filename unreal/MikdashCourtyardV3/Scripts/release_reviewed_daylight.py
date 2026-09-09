"""Save only a daylight preset reviewed in three actual PIE camera comparisons."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]

# The reviewed preset was adopted on the legacy map only, so the map that actually ships
# was still on the pre-review 5000 K sun and 1.0 skylight when this was found (9 Sep).
# -Target=Candidate48 (the configured default and cook map) or -Main50 (legacy).
_TARGETS = {
    'candidate48': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'main50': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}


def _target_from_command_line():
    import sys
    tokens = [t.lower() for t in sys.argv]
    try:
        import unreal as _ue
        tokens += _ue.SystemLibrary.get_command_line().lower().split()
    except Exception:  # noqa: BLE001 - offline syntax checks have no engine
        pass
    for token in tokens:
        for key in _TARGETS:
            if token in ('-' + key, '--' + key) or token.endswith('=' + key):
                return key
    return 'main50'          # unchanged default: never retarget a run that did not ask


TARGET = _target_from_command_line()
MAP = _TARGETS[TARGET]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def helper(name):
    spec = importlib.util.spec_from_file_location('daylight_'+name, ROOT/'Scripts'/(name+'.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def close(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    return abs(a-b) < .0001 if isinstance(a, (int, float)) else a == b


def validate_preset(decision, receipts):
    """Offline-testable review policy; missing legacy tags never authorize cool preset."""
    preset = decision.get('daylightPreset', 'higher_sun_brighter_source')
    if preset not in ('cool_source_more_fill', 'higher_sun_brighter_source'):
        raise RuntimeError('Unknown daylight preset')
    if len(receipts) != 3 or {r['diagnosticSubject'] for r in receipts} != {'mount-paving', 'heikhal', 'kotel-platform-join'}:
        raise RuntimeError('Require exactly three distinct subject comparisons')
    baseline, proposed = receipts[0]['daylightBefore'], receipts[0]['daylightCandidate']
    if any(not close(r['daylightBefore'], baseline) or not close(r['daylightCandidate'], proposed) for r in receipts):
        raise RuntimeError('Compared lighting presets differ')
    if len({r['mapShaBefore'] for r in receipts}) != 1:
        raise RuntimeError('Comparisons must use the same unchanged main')
    if any(r.get('daylightPreset', 'higher_sun_brighter_source') != preset for r in receipts):
        raise RuntimeError('Different preset or old images supplied')
    expected_baseline = dict(sunIntensity=30000.0, temperature=5000.0, useTemperature=True,
                             rotation=[-30.0,-160.0,0.0], skyIntensity=1.0)
    if preset == 'cool_source_more_fill':
        expected = dict(sunIntensity=30000.0, temperature=6500.0, useTemperature=True,
                        rotation=[-30.0,-160.0,0.0], skyIntensity=1.3)
        if not close(baseline, expected_baseline) or not close(proposed, expected):
            raise RuntimeError('Cool-source preset requires exact reviewed baseline and proposed values')
        exposure = receipts[0].get('daylightExposureBefore')
        if not isinstance(exposure, dict) or not exposure:
            raise RuntimeError('Cool-source comparison needs actual exposure snapshots')
        for r in receipts:
            if r.get('daylightExposureBefore') != exposure or r.get('daylightExposureAfter') != exposure:
                raise RuntimeError('Exposure changed or missing during cool-source comparison')
    else:
        # Historical recipe is distinct; its image hashes/main equality are still required.
        expected = dict(sunIntensity=45000.0, temperature=6500.0, useTemperature=True,
                        rotation=[-50.0,-160.0,0.0], skyIntensity=1.3)
        if not close(baseline, expected_baseline) or not close(proposed, expected):
            raise RuntimeError('Brighter-source recipe differs from its named preset')
    return preset, baseline, proposed


def run(visual_decision):
    import unreal as u
    decision = json.loads(Path(visual_decision).read_text(encoding='utf-8-sig'))
    if decision.get('decision') != 'ADOPT_REVIEWED_DAYLIGHT':
        raise RuntimeError('No visual adoption decision')
    receipts = []
    for entry in decision['comparisons']:
        if sha(entry['file']) != entry['sha256']:
            raise RuntimeError('Comparison receipt changed')
        r = json.loads(Path(entry['file']).read_text(encoding='utf-8-sig'))
        if r.get('errors') or not r.get('pieEnded') or not r.get('mapBytesUnchanged') or len(r.get('daylightComparison', [])) != 2:
            raise RuntimeError('Incomplete or failed comparison')
        for still in r['daylightComparison']:
            if sha(still['file']) != still['sha256']:
                raise RuntimeError('Compared image changed')
        receipts.append(r)
    preset, baseline, proposed = validate_preset(decision, receipts)
    if Path(u.SystemLibrary.get_project_directory()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Live or dirty world')
    if ed.get_editor_world().get_outermost().get_name() != MAP:
        raise RuntimeError('Main must be loaded')
    units = helper('release_amah48_candidate')
    protected = units.offline_plan()
    mapfile = units.disk(MAP)
    if any(r['mapShaBefore'] != sha(mapfile) for r in receipts):
        raise RuntimeError('Map changed since reviews')
    for folder in ('__ExternalActors__', '__ExternalObjects__'):
        if (ROOT/'Content'/folder/MAP[6:]).exists():
            raise RuntimeError('Expanded checkpoint support required')
    def targets():
        all_actors = actors.get_all_level_actors()
        suns = [a for a in all_actors if isinstance(a, u.DirectionalLight)]
        skies = [a for a in all_actors if isinstance(a, u.SkyLight)]
        if len(suns) != 1 or len(skies) != 1:
            raise RuntimeError('Need exactly one sun and sky')
        return suns[0], skies[0]
    def values(sun, sky):
        light = sun.get_component_by_class(u.DirectionalLightComponent)
        skylight = sky.get_component_by_class(u.SkyLightComponent)
        rot = sun.get_actor_rotation()
        return dict(sunIntensity=light.get_editor_property('intensity'), temperature=light.get_editor_property('temperature'),
                    useTemperature=light.get_editor_property('use_temperature'), rotation=[rot.pitch,rot.yaw,rot.roll],
                    skyIntensity=skylight.get_editor_property('intensity'))
    sun, sky = targets()
    if not close(values(sun, sky), baseline):
        raise RuntimeError('Current lighting differs from reviewed baseline')
    h = helper('release_resident_crowd')
    before_scene = h._scene_snapshot(u, actors)
    selected = {sun.get_name(), sky.get_name()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint = ROOT.parent/'ReviewCheckpoints'/('ReviewedDaylight-'+stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(mapfile, checkpoint/'Main.umap')
    if sha(checkpoint/'Main.umap') != sha(mapfile):
        raise RuntimeError('Checkpoint mismatch')
    out = ROOT/'SourceAssets/lighting-review'/('native-reviewed-daylight-'+stamp+'.json')
    report = dict(status='STARTED', beforeMapSha256=sha(mapfile), checkpoint=str(checkpoint),
                  before=baseline, expected=proposed, daylightPreset=preset,
                  exposurePolicy='unchanged', visualDecisionSha256=sha(visual_decision))
    def write():
        out.write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    write()
    try:
        light = sun.get_component_by_class(u.DirectionalLightComponent)
        skylight = sky.get_component_by_class(u.SkyLightComponent)
        for obj in (sun, sky, light, skylight):
            obj.modify(True)
        light.set_editor_property('use_temperature', proposed['useTemperature'])
        light.set_temperature(proposed['temperature'])
        light.set_intensity(proposed['sunIntensity'])
        skylight.set_intensity(proposed['skyIntensity'])
        p, y, r = proposed['rotation']
        sun.set_actor_rotation(u.Rotator(pitch=p, yaw=y, roll=r), True)
        expected_scene = h._scene_snapshot(u, actors)
        if {k:v for k,v in before_scene.items() if k not in selected} != {k:v for k,v in expected_scene.items() if k not in selected}:
            raise RuntimeError('Unrelated scene change')
        if not close(values(sun, sky), proposed) or not levels.save_current_level():
            raise RuntimeError('Readback or save failed')
        report.update(status='SAVED_REOPEN_PENDING', afterMapSha256=sha(mapfile))
        write()
        if not levels.load_level(MAP) or h._scene_snapshot(u, actors) != expected_scene or not close(values(*targets()), proposed):
            raise RuntimeError('Reopened lighting/scene mismatch')
        report['status'] = 'SAVED_REOPENED_THREE_VIEW_REVIEWED_DAYLIGHT'
    except Exception as exc:
        report.update(status='FAILED_CHECKPOINT_AVAILABLE', error=repr(exc))
        raise
    finally:
        after = units.offline_plan()
        report['afterMapSha256'] = sha(mapfile)
        report['protectedUnchanged'] = all(after[k] == protected[k] for k in ('assets','configSha256','manifestSha256','protectedMapHashes'))
        if not report['protectedUnchanged']:
            report['status'] = 'FAILED_PROTECTED_HASH_MISMATCH'
        write()
        if not report['protectedUnchanged']:
            raise RuntimeError('Protected files changed')
    return report

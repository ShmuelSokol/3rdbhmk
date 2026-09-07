"""Transient V4 particle evidence. begin(); allow editor frames; sample(1/3/6/9/12).

Never saves Unreal assets/maps. Each sample advances only the delta from the
previous requested age; capture validity is recorded separately from empty data.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue

MAP = '/Game/MikdashV3/MaterialReview/IncenseSmokeReviewV3/L_IncenseSmokeReview'
SYSTEM = '/Game/MikdashV3/MaterialReview/IncenseSmokeV4/NS_FiniteIncenseStudy'
REPORT = Path(ue.Paths.project_dir()) / 'SourceAssets/vessels-review/IncenseRepairV4/particle-inspection.json'
_comp = None
_age = 0.0
_report = {}


def _write():
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(_report, indent=2) + '\n', encoding='utf-8')


def begin():
    global _comp, _age, _report
    world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
    if world.get_outermost().get_name() != MAP:
        raise RuntimeError('Load the saved V3 isolated review map first')
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
    found = [a for a in actors if a.get_actor_label() == 'REVIEW_FiniteIncense_InactiveByDefault']
    if len(found) != 1:
        raise RuntimeError('Expected exactly one isolated review actor')
    system = ue.load_asset(SYSTEM)
    if not isinstance(system, ue.NiagaraSystem):
        raise RuntimeError('V4 study is missing')
    previous = json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else None
    _report = dict(started_utc=datetime.now(timezone.utc).isoformat(), system=SYSTEM,
                   map=MAP, samples=[], limits=['Transient diagnostic, no asset saves',
                   'Capture failure is not evidence of zero particles',
                   'Requested age is not claimed actual age; cache start_seconds records evidence'])
    if previous:
        _report['previous_execution'] = previous
    _comp = found[0].get_component_by_class(ue.NiagaraComponent)
    _comp.deactivate()
    _comp.set_editor_property('auto_activate', False)
    _comp.set_asset(system)
    _comp.set_force_solo(True)
    _comp.set_age_update_mode(ue.NiagaraAgeUpdateMode.DESIRED_AGE)
    _comp.set_desired_age(0.0)
    _comp.activate(True)
    _age = 0.0
    _write()
    return 'Initialized. Allow editor frames for readiness, then call sample(1).'


def sample(seconds):
    global _age
    if _comp is None or not math.isfinite(seconds) or seconds < _age or seconds > 20:
        raise ValueError('Call begin, then monotonically sample finite ages within 0..20')
    if ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world().get_outermost().get_name() != MAP:
        raise RuntimeError('Review map changed')
    ticks = round((seconds - _age) * 60)
    if abs(ticks / 60.0 - (seconds - _age)) > 0.0001:
        raise ValueError('Use ages on 1/60-second boundaries')
    entry = dict(requested_age_seconds=seconds, advance_ticks=ticks,
                 active=_comp.is_active(), solo=_comp.get_force_solo(),
                 tick_enabled=_comp.is_component_tick_enabled(), paused=_comp.is_paused())
    _report['samples'].append(entry)
    try:
        # Reactivate after shader/system readiness; startup compilation may
        # deactivate the initial component before the first sample.
        if _age == 0.0:
            _comp.activate(True)
        entry['active_before_advance'] = _comp.is_active()
        _comp.advance_simulation(ticks, 1.0 / 60.0)
        _comp.set_desired_age(float(seconds))
        _age = seconds
        cache = ue.NiagaraSimCacheFunctionLibrary.create_niagara_sim_cache(_comp)
        params = ue.NiagaraSimCacheCreateParameters()
        result = ue.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(
            cache, params, _comp, False, 1.0 / 60.0)
        entry['capture_return'] = str(result)
        # Python versions may return (success, OutSimCache) or the successful
        # output cache. The supplied cache is always the object inspected here.
        entry['cache_valid'] = cache.is_cache_valid()
        entry['frames'] = cache.get_num_frames()
        if not entry['cache_valid'] or entry['frames'] == 0:
            entry['status'] = 'capture_unavailable_not_zero_particles'
        else:
            entry['cache_start_seconds'] = cache.get_start_seconds()
            entry['emitters'] = []
            for name in cache.get_emitter_names():
                positions = cache.read_position_attribute('Position', name, False, 0)
                velocities = cache.read_vector_attribute('Velocity', name, 0)
                sizes = cache.read_vector2_attribute('SpriteSize', name, 0)
                row = dict(name=str(name), position_count=len(positions),
                           positions=[[v.x, v.y, v.z] for v in positions],
                           velocities=[[v.x, v.y, v.z] for v in velocities],
                           sprite_sizes=[[v.x, v.y] for v in sizes],
                           lifetimes=list(cache.read_float_attribute('Lifetime', name, 0)),
                           ages=list(cache.read_float_attribute('Age', name, 0)))
                if positions:
                    row['z_range_cm'] = [min(v.z for v in positions), max(v.z for v in positions)]
                entry['emitters'].append(row)
            entry['status'] = 'captured_attributes_not_visual_acceptance'
            entry['origin_check'] = check_wisp_origins(entry)
    except Exception as error:
        entry.update(status='diagnostic_api_failure', error=str(error))
        raise
    finally:
        _write()
    return entry


def stop():
    if _comp is not None:
        _comp.deactivate()
        _comp.set_editor_property('auto_activate', False)
    _report['stopped_without_asset_save'] = True
    _write()


def check_wisp_origins(entry, ceiling_height_cm=900.0, spread_seconds=2.0):
    """Validate actual cached local positions, never requested screenshot ages.

    Default near-point spawn z865 then vz-12 => alive z841..865cm.
    A 2cm tolerance accommodates fixed-step age ordering; rejects V2 floor wisps.
    Only a valid, live 6-second cache with all eight emitters establishes this gate.
    This does not establish visible smoke, collision, scheduler or cooked behavior.
    """
    actual = entry.get('cache_start_seconds')
    if not entry.get('cache_valid') or actual is None or abs(actual - 6.0) > 0.05:
        return dict(status='not_assessed', reason='Requires valid actual-age6 cache')
    rows = entry.get('emitters', [])
    errors = []
    expected = {'CeilingWisp_%02d' % i for i in range(8)}
    wisps = [r for r in rows if r['name'] in expected]
    if len(wisps) != 8 or {r['name'] for r in wisps} != expected:
        errors.append('Expected exactly eight named ceiling emitters')
    origin = ceiling_height_cm - 35.0
    for row in wisps:
        positions, ages = row['positions'], row['ages']
        if not positions or len(positions) != len(ages):
            errors.append(row['name'] + ': missing/mismatched positions/ages')
            continue
        for pos, age in zip(positions, ages):
            if (not all(math.isfinite(v) for v in pos + [age]) or
                    not 0 <= age <= spread_seconds + 0.05 or
                    not origin - 12 * spread_seconds - 2 <= pos[2] <= origin + 2 or
                    abs(pos[2] - (origin - 12 * age)) > 2):
                errors.append(row['name'] + ': local origin/vertical trajectory mismatch')
                break
    return dict(status='pass_attributes_only' if not errors else 'fail', errors=errors,
                actual_age_seconds=actual, expected_origin_z_cm=origin,
                tolerance_cm=2.0)

"""Independent offline validator. Inputs are native receipts, never generated evidence."""
import json
import math
from pathlib import Path

ASSET_ROOT = '/Game/MikdashV3/MaterialReview/IncenseSmokeV4'
SYSTEM = ASSET_ROOT + '/NS_FiniteIncenseStudy'
NAMES = {'FiniteShaft'} | {'CeilingWisp_%02d' % i for i in range(8)}
REQUIRED_AGES = (1.0, 3.0, 6.0, 9.5, 12.0)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_lifetime(report, emission=6.0, rise=3.0, spread=2.0, ceiling=900.0):
    """Once: shaft last death <= emission+rise; wisps <= rise+emission+spread.

    Sampling protocol is for defaults. Explicitly reject non-default durations
    instead of silently applying an unsuitable fixed sampling window.
    """
    if (emission, rise, spread, ceiling) != (6.0, 3.0, 2.0, 900.0):
        raise ValueError('This V1 protocol accepts default build parameters only')
    errors, missing = [], []
    if report.get('system') != SYSTEM:
        errors.append('Receipt system does not match V4')
    samples = report.get('samples', [])
    valid = []
    last_age = -1.0
    for index, sample in enumerate(samples):
        actual = sample.get('cache_start_seconds')
        if not sample.get('cache_valid') or not finite(actual) or sample.get('frames', 0) < 1:
            missing.append('sample %d has no valid actual-age cache; cannot infer empty effect' % index)
            continue
        if actual <= last_age:
            errors.append('Actual cache ages are not strictly increasing')
        last_age = actual
        valid.append(sample)
        rows = sample.get('emitters', [])
        if len(rows) != 9 or {r.get('name') for r in rows} != NAMES:
            missing.append('actual %.3f lacks complete nine-emitter inventory' % actual)
        for row in rows:
            name = row.get('name')
            if name not in NAMES:
                errors.append('Unexpected emitter ' + str(name))
                continue
            positions, ages = row.get('positions', []), row.get('ages', [])
            count = row.get('position_count')
            if not isinstance(count, int) or count < 0 or count != len(positions) or count != len(ages):
                errors.append(name + ': inconsistent particle count/attribute arrays')
                continue
            is_wisp = name.startswith('CeilingWisp_')
            delay, life = (rise, spread) if is_wisp else (0, rise)
            death_bound = delay + emission + life
            if actual > death_bound + 0.05 and count:
                errors.append(name + ': particles persist past finite bound %.2f' % death_bound)
            if is_wisp and actual < delay - 0.05 and count:
                errors.append(name + ': wisps emitted before configured delay')
            for pos, age in zip(positions, ages):
                if len(pos) != 3 or not all(finite(v) for v in pos) or not finite(age):
                    errors.append(name + ': nonfinite/malformed particle state')
                    continue
                if not -0.02 <= age <= life + 0.05:
                    errors.append(name + ': particle age exceeds configured lifetime')
                if is_wisp:
                    origin = ceiling - 35
                    if not origin - 12*spread - 2 <= pos[2] <= origin + 2:
                        errors.append(name + ': floor/out-of-band wisp')
                    if abs(pos[2] - (origin - 12*age)) > 2:
                        errors.append(name + ': vertical trajectory disagrees with particle age')
        if abs(actual - 6.0) <= 0.05:
            if any(r.get('position_count', 0) <= 0 for r in rows) or len(rows) != 9:
                errors.append('Actual-age6 must show all nine emitters live')
    for requested in REQUIRED_AGES:
        if not any(abs(s['cache_start_seconds'] - requested) <= 0.05 for s in valid):
            missing.append('Missing valid actual-age sample near %.1f' % requested)
    return dict(status='fail' if errors else ('incomplete' if missing else 'pass_sampled_attributes_only'),
                errors=sorted(set(errors)), missing=sorted(set(missing)),
                shaft_death_bound_seconds=emission+rise,
                wisp_death_bound_seconds=rise+emission+spread,
                limitations=['Finite sampled CPU/SimCache evidence only, not continuous or rendered acceptance',
                             'Invalid late cache is not proof of extinction',
                             'Defaults only; no scheduler/restart/pause/cook verification'])


def validate_dependencies(report):
    """Validate a source AssetRegistry traversal receipt, not cooked closure.

    New wrapper metadata is deliberately required; a flat old package list
    cannot establish root identity, recursive coverage or disabled converter.
    """
    errors, missing = [], []
    required = {'asset': SYSTEM, 'recursive': True, 'hard': True, 'soft': True,
                'converter_enabled': False, 'scope': 'source_asset_registry'}
    for key, value in required.items():
        if report.get(key) != value:
            missing.append('Require explicit verified metadata %s=%r' % (key, value))
    packages = report.get('packages', [])
    if not isinstance(packages, list) or not packages:
        missing.append('No package inventory')
        packages = []
    if SYSTEM not in packages or ASSET_ROOT + '/M_OriginalSoftSmoke' not in packages:
        missing.append('System/material packages absent')
    for package in packages:
        if not isinstance(package, str):
            errors.append('Malformed package path')
            continue
        if 'CascadeToNiagaraConverter' in package:
            errors.append('Converter dependency: ' + package)
        elif package.startswith('/Game/') and not package.startswith(ASSET_ROOT + '/'):
            errors.append('Unexpected project dependency (including V1-V3): ' + package)
        elif not package.startswith((ASSET_ROOT+'/', '/Engine/', '/Niagara/', '/Script/')):
            errors.append('Unexpected mount: ' + package)
    if report.get('missing_packages') != []:
        errors.append('Missing-package check absent or nonempty')
    return dict(status='fail' if errors else ('incomplete' if missing else 'pass_source_registry_only'),
                errors=errors, missing=missing,
                limitations=['Source registry closure does not prove cooked editor-module stripping or runtime availability',
                             '/Niagara/DefaultAssets/Templates/CascadeConversion is ordinary Niagara content, not the converter plugin',
                             '/Script editor references require separate cooked dependency validation'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['lifetime', 'dependencies'])
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    result = (validate_lifetime if args.kind == 'lifetime' else validate_dependencies)(json.loads(args.receipt.read_text(encoding='utf-8')))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'].startswith('pass_') else 1)

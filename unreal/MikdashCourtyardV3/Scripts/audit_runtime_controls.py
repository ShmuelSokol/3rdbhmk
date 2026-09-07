"""Offline controls evidence audit. Never imports Unreal or launches native processes."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/runtime-review/control-audit'
CPP = ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Private/MikdashPlayerController.cpp'
PREP = CPP.with_name('SMikdashPreparation.h')
RECEIPTS = ['packaged-ui-first-pass.json', 'preparation-ui-v4-build.json',
            'walkthrough-05-build.json', 'step55-saved.json', 'ulam-connected-summary.json',
            'mute-restart-v2.json', 'preparation-ui-v3.json']


def main():
    source = CPP.read_text(encoding='utf-8-sig')
    prep = PREP.read_text(encoding='utf-8-sig')
    receipts = {name: json.loads((OUT.parent / name).read_text(encoding='utf-8-sig')) for name in RECEIPTS}
    checks = {
        'controller_p_bound_when_paused': 'BindKey(EKeys::P, IE_Pressed, this, &AMikdashPlayerController::ToggleWalkthroughMenu).bExecuteWhenPaused = true' in source,
        'controller_escape_bound_when_paused': 'BindKey(EKeys::Escape, IE_Pressed, this, &AMikdashPlayerController::ToggleWalkthroughMenu).bExecuteWhenPaused = true' in source,
        'diagonal_clamped': 'Direction.GetClampedToMaxSize(1.f)' in source,
        'menu_stops_velocity': 'StopMovementImmediately()' in source,
        'unlocked_cursor_policy': 'EMouseLockMode::DoNotLock' in source,
        'startup_requires_start': 'if (bHasStarted) ResumeWalkthrough();' in source,
        'saved_step55_receipt': receipts['step55-saved.json']['maxStepHeightCm'] == 55,
        'build05_physical_p_pending': 'Physical P input not yet accepted' in receipts['walkthrough-05-build.json']['limitations'],
    }
    probe = OUT / 'native_control_probe.py'
    tree = ast.parse(probe.read_text(encoding='utf-8-sig'))
    forbidden = {'add_movement_input', 'resume_walkthrough', 'toggle_walkthrough_menu', 'set_actor_location', 'set_control_rotation'}
    called = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    checks['probe_passive_no_input_or_controller_mutation'] = not bool(forbidden & called)
    checks['probe_has_stop_and_callback_cleanup'] = {'unregister_slate_post_tick_callback'} <= called and 'levels.editor_request_end_play' in probe.read_text(encoding='utf-8-sig')
    checks['probe_import_inert'] = all(not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Call) for n in tree.body)
    report = {'status': 'offline_source_contracts_pass' if all(checks.values()) else 'failed',
        'checks': checks, 'nativeExecuted': False,
        'preparationPHandlerPresent': 'EKeys::P' in prep,
        'limitations': ['Source text checks are not C++ compilation or binding execution',
                        'Historical receipts do not establish current map/package acceptance',
                        'Native probe API/runtime behavior remains unexecuted']}
    (OUT / 'offline-checks.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    paths = [Path(__file__), probe, OUT / 'test_probe_offline.py', OUT / 'AUDIT.md', OUT / 'offline-checks.json', CPP, PREP]
    paths += [OUT.parent / name for name in RECEIPTS]
    manifest = {'scope': 'Frozen audit deliverables and inspected inputs; manifest excludes itself', 'files': []}
    for path in paths:
        data = path.read_bytes()
        manifest['files'].append({'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()


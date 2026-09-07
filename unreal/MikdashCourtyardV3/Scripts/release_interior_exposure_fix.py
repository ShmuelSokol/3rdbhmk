"""Guarded correction of the EV8 floor that blackened the Kodesh capture.

Run with UnrealEditor-Cmd -run=pythonscript; -ExposureDryRun is read-only.
Changes only the histogram lower bound and descriptive volume label. The
exterior upper bound, lighting, materials and geometry remain unchanged.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_lighting_polish as lp


def run():
    import unreal as ue
    spec = lp.load_spec()
    p = lp.Polish(ue, spec)
    p.guard_world(True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    map_file = lp.ROOT / spec['targetMapFile']
    before = lp.sha256_of(map_file)
    protected = lp._protected_hashes(spec)
    p.receipt_path = lp._fresh_receipt(spec, 'native-interior-exposure-', stamp)
    p.receipt = dict(status='started', stamp=stamp, map=lp.TARGET,
                     mapSha256Before=before, protectedSha256Before=protected,
                     cvars=p.read_cvars(), changes=[], errors=[], mapSaved=False,
                     created=[], notes=['EV8 floor made Kodesh nearly black in release-capture-20260907T213307Z. Restore EV0 lower bound from pre-polish exposure; retain EV14 maximum. Visual acceptance required.'])
    try:
        volumes = [a for a in p.actors.get_all_level_actors() if isinstance(a, ue.PostProcessVolume)]
        if len(volumes) != 1:
            raise RuntimeError('Expected exactly one post-process volume')
        actor = volumes[0]
        actor_name = actor.get_name()
        settings = actor.get_editor_property('settings')
        expected = lp.spec_value(ue, {'$ev100': 8.0}, p.context)
        actual = settings.get_editor_property('auto_exposure_min_brightness')
        maximum = settings.get_editor_property('auto_exposure_max_brightness')
        if abs(maximum - lp.spec_value(ue, {'$ev100': 14.0}, p.context)) > 1e-4:
            raise RuntimeError('Upper exposure bound changed unexpectedly')
        corrected = lp.spec_value(ue, {'$ev100': 0.0}, p.context)
        if abs(actual - corrected) < 1e-4 and actor.get_actor_label() == 'V3 cinematic exposure - histogram EV 0-14, filmic':
            p.receipt['status'] = 'already_corrected_reopened_readback_visual_pending'
            p.receipt['verifiedMinBrightness'] = actual
            p.receipt['verifiedMaxBrightness'] = settings.get_editor_property('auto_exposure_max_brightness')
            return
        if abs(actual - expected) > 1e-4:
            raise RuntimeError('Exposure floor does not match prior EV8 pass: %r vs %r' % (actual, expected))
        baseline = p.snapshot_unrelated({actor_name})
        if '-exposuredryrun' in ue.SystemLibrary.get_command_line().lower():
            p.receipt['status'] = 'dry_run_no_mutation'
            return
        checkpoint, copied = lp._checkpoint(spec, 'InteriorExposure-', stamp, map_file, before)
        p.receipt['checkpoint'] = str(checkpoint)
        p.receipt['oneFilePerActorFoldersCopied'] = copied
        p.write_receipt()
        p.set_prop('postProcess', settings, 'auto_exposure_min_brightness', {'$ev100': 0.0}, True,
                   actor=actor, component_class=None, struct='settings')
        actor.set_editor_property('settings', settings)
        p.set_label('postProcess', actor, 'V3 cinematic exposure - histogram EV 0-14, filmic')
        if p.snapshot_unrelated({actor_name}) != baseline:
            raise RuntimeError('Unrelated actors changed')
        p.save_and_reopen()
        p.receipt['mapSaved'] = True
        p.receipt['mapSha256AfterSave'] = lp.sha256_of(map_file)
        failures = p.readback(p.receipt['changes'], 'afterReopen', 'desired')
        if failures or p.snapshot_unrelated({actor_name}) != baseline:
            raise RuntimeError('Readback or unrelated actor verification failed: %r' % failures)
        p.receipt['status'] = 'saved_reopened_visual_acceptance_pending'
    except Exception as exc:
        p.receipt['errors'].append(repr(exc))
        p.receipt['status'] = 'failed_after_save' if p.receipt['mapSaved'] else 'failed_before_save'
        raise
    finally:
        p.receipt['mapSha256After'] = lp.sha256_of(map_file)
        p.receipt['protectedUnchanged'] = lp._protected_hashes(spec) == protected
        if not p.receipt['protectedUnchanged']:
            p.receipt['status'] = 'failed_protected_hash_guard'
            p.receipt['errors'].append('Protected file hash changed')
        p.write_receipt()
        if not p.receipt['protectedUnchanged']:
            raise RuntimeError('Protected file hash changed')


if __name__ == '__main__':
    run()

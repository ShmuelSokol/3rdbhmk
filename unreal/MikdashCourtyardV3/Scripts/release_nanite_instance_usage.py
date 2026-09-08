"""Guarded UE5.8 per-instance Nanite usage repair. Offline by default.

Native run(apply=True) modifies only nine explicitly observed instance packages.
run(verify_only=True) in a fresh real-RHI process verifies persistence without saves.
No map, parent material, texture, or source geometry is changed by this helper.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT.parent / 'Astra-Groups-Main01-20260908.log'
BASE = '/Game/MikdashV3/Materials/PBR/Instances/'
PARENT = '/Game/MikdashV3/Materials/PBR/M_PBR_Tiled'
WARNINGS = ('MI_PBR_Marble', 'MI_PBR_GoldHammered', 'MI_PBR_CedarPlanks')
AUTO_SET = ('MI_PBR_LimestoneTrim', 'MI_PBR_LimestoneAshlar', 'MI_PBR_PavingSlabs',
            'MI_PBR_GoldFloor', 'MI_PBR_RoughStone', 'MI_PBR_Plaster')
ALLOWLIST = tuple(sorted(BASE + name for name in WARNINGS + AUTO_SET))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disk(package):
    if not package.startswith('/Game/') or '.' in package or '..' in package:
        raise RuntimeError('Invalid exact package path: ' + package)
    return ROOT / 'Content' / (package[6:] + '.uasset')


def observed(text):
    pattern = r'Material (/Game/MikdashV3/[^\s]+) (needed to set usage flag Nanite|missing usage flag Nanite!)'
    found = {}
    for path, message in re.findall(pattern, text):
        package, name = path.rsplit('.', 1)
        if package.rsplit('/', 1)[-1] != name:
            raise RuntimeError('Unexpected logged object identity')
        found[package] = 'runtime_usage_failure' if message.startswith('missing') else 'editor_auto_set_not_yet_persistence_proof'
    return found


def plan():
    found = observed(LOG.read_text(encoding='utf-8-sig', errors='replace'))
    if set(found) != set(ALLOWLIST):
        raise RuntimeError('Observed paths differ from the exact reviewed nine-instance allowlist')
    for name in WARNINGS:
        if found[BASE + name] != 'runtime_usage_failure':
            raise RuntimeError('Runtime warning classification changed')
    return dict(status='OFFLINE_NINE_INSTANCE_PLAN_NATIVE_UNVERIFIED', sourceLog=str(LOG),
                sourceLogSha256=sha(LOG), parent=PARENT,
                targets=[dict(package=p, reason=found[p], originalSha256=sha(disk(p))) for p in ALLOWLIST],
                scope='Nanite usage override on exact instances only; parent/material parameters unchanged',
                visualAcceptance='PENDING fresh-process usage, real-RHI capture, and packaged cook')


def protected_hashes():
    targets = {disk(p) for p in ALLOWLIST}
    files = set((ROOT / 'Content').rglob('*.umap'))
    files.update((ROOT / 'Config').rglob('*.ini'))
    files.update((ROOT / 'Content/MikdashV3/Materials/PBR').rglob('*.uasset'))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(files - targets)}


def immutable_snapshot(ue, instance):
    ml = ue.MaterialEditingLibrary
    parent = instance.get_editor_property('parent')
    if not parent or parent.get_path_name().split('.')[0] != PARENT:
        raise RuntimeError('Unreviewed parent on ' + instance.get_path_name())
    values = dict(parent=parent.get_path_name())
    for field in ('scalar_parameter_values', 'vector_parameter_values', 'texture_parameter_values'):
        values[field] = [entry.export_text() for entry in instance.get_editor_property(field)]
    # Preserve every other base-property override. Known Nanite mask fields alone
    # are removed here; independent per-usage readback below protects other bits.
    overrides = instance.get_editor_property('base_property_overrides').export_text()
    stripped = re.sub(r'\b(?:bOverride_UsageFlags|UsageFlags)=(?:0x[0-9a-fA-F]+|[0-9]+),?', '', overrides)
    values['otherBaseOverrides'] = stripped.replace(',)', ')').replace('(,', '(')
    values['otherUsage'] = {}
    for name in dir(ue.MaterialUsage):
        if name.startswith('MATUSAGE_') and name != 'MATUSAGE_NANITE' and name != 'MATUSAGE_MAX':
            usage = getattr(ue.MaterialUsage, name)
            values['otherUsage'][name] = [bool(ml.has_material_usage(instance, usage)),
                                         bool(ml.has_material_usage_override(instance, usage))]
    return values


def usage_readback(ue, instance):
    ml = ue.MaterialEditingLibrary
    usage = ue.MaterialUsage.MATUSAGE_NANITE
    result = dict(enabled=bool(ml.has_material_usage(instance, usage)),
                  explicitlyOverridden=bool(ml.has_material_usage_override(instance, usage)))
    if result != dict(enabled=True, explicitlyOverridden=True):
        raise RuntimeError('Nanite instance override did not read back true: ' + instance.get_path_name())
    return result


def compile_readback(ue, instance, current_log, before):
    # Installed MaterialEditingLibrary.cpp:2116 submits missing jobs and calls
    # Resource->FinishCompilation for this material interface, not all materials.
    stats = ue.MaterialEditingLibrary.get_statistics(instance)
    result = {name: int(stats.get_editor_property(name)) for name in
              ('num_vertex_shader_instructions', 'num_pixel_shader_instructions', 'num_samplers')}
    tail = current_log.read_bytes()[before:].decode('utf-8', errors='replace')
    failures = [line for line in tail.splitlines() if re.search(r'(?i)(error:|failed to compile|shader.*error)', line)]
    if failures:
        raise RuntimeError('Compilation log failure: ' + '\n'.join(failures[:8]))
    # Sampler sharing makes a hard three-sampler threshold unsound. Exact parent,
    # unchanged texture parameters, explicit usage and a completed positive-size
    # pixel resource are checked independently; sampler count is evidence only.
    if result['num_pixel_shader_instructions'] <= 0:
        raise RuntimeError('No usable compiled textured PBR resource: ' + repr(result))
    return dict(statistics=result, compileFailures=failures,
                limit='Current-RHI resource statistics and local compile log; fresh render/cook still required')


def run(apply=False, verify_only=False, repair_receipt=None):
    report = plan()
    if not apply and not verify_only:
        return report
    if apply and verify_only:
        raise RuntimeError('Choose repair OR fresh-process read-only verification')
    if verify_only:
        if not repair_receipt:
            raise RuntimeError('Fresh-process verification needs the successful repair receipt path')
        prior = json.loads(Path(repair_receipt).read_text(encoding='utf-8-sig'))
        if (prior.get('status') != 'NINE_INSTANCE_USAGE_SAVED_COMPILED_FRESH_PROCESS_RENDER_COOK_PENDING'
                or prior.get('processId') == os.getpid() or not prior.get('protectedUnchanged')
                or prior.get('finalTargetHashes') != {p: sha(disk(p)) for p in ALLOWLIST}):
            raise RuntimeError('Repair receipt/process/package hashes do not authorize fresh verification')
    import unreal as ue
    if Path(ue.SystemLibrary.get_project_directory()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    command = ue.SystemLibrary.get_command_line()
    if '-nullrhi' in command.lower():
        raise RuntimeError('Real RHI required for material compilation evidence')
    match = re.search(r'(?i)-abslog=(?:"([^"]+)"|([^\s]+))', command)
    if not match:
        raise RuntimeError('A unique absolute native log is required for compile readback')
    current_log = Path(match.group(1) or match.group(2)).resolve()
    if current_log == LOG.resolve() or not current_log.is_file():
        raise RuntimeError('Do not overwrite the source evidence log')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world() or ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Clean non-PIE process required; do not discard existing edits')
    protected = protected_hashes()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('NaniteInstances-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    receipt = ROOT / 'SourceAssets/perf-review' / ('nanite-instance-usage-' + stamp + '.json')
    report.update(status='CHECKPOINTING', verifyOnly=verify_only, checkpoint=str(checkpoint),
                  currentNativeLog=str(current_log), materials=[], processId=os.getpid(),
                  receipt=str(receipt), repairReceipt=str(repair_receipt) if repair_receipt else None)

    def write():
        receipt.write_text(json.dumps(report, indent=2), encoding='utf-8')

    # All originals checkpointed before ANY instance is loaded or auto-updated.
    for row in report['targets']:
        source = disk(row['package'])
        saved = checkpoint / source.relative_to(ROOT)
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, saved)
        if sha(saved) != row['originalSha256'] or sha(source) != row['originalSha256']:
            raise RuntimeError('Original/checkpoint hash changed during preflight')
    write()
    try:
        instances = []
        for target in report['targets']:
            instance = ue.load_asset(target['package'])
            if not isinstance(instance, ue.MaterialInstanceConstant):
                raise RuntimeError('Allowlisted object is not an instance constant')
            snapshot = immutable_snapshot(ue, instance)
            instances.append((instance, snapshot, target))
        # All class/parent/parameter preflight completes before the first mutation.
        for instance, before, target in instances:
            row = dict(package=target['package'], beforeSha256=target['originalSha256'], saved=False)
            report['materials'].append(row)
            compile_log_offset = current_log.stat().st_size
            if apply:
                instance.modify(True)
                ue.MaterialEditingLibrary.set_material_usage_override(instance, ue.MaterialUsage.MATUSAGE_NANITE, True, True)
                ue.MaterialEditingLibrary.update_material_instance(instance)
            row['usage'] = usage_readback(ue, instance)
            row['compile'] = compile_readback(ue, instance, current_log, compile_log_offset)
            if immutable_snapshot(ue, instance) != before:
                raise RuntimeError('Unrelated instance parameters/overrides changed')
            if apply:
                if not ue.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False):
                    raise RuntimeError('Instance save failed')
                row.update(saved=True, afterSha256=sha(disk(target['package'])))
                write()  # Preserve exact disk mutation before any later failure.
            else:
                row['afterSha256'] = sha(disk(target['package']))
                if row['afterSha256'] != row['beforeSha256']:
                    raise RuntimeError('Read-only verification changed package bytes')
            row['savedReadback'] = usage_readback(ue, ue.load_asset(target['package']))
            write()
        report['status'] = ('FRESH_PROCESS_USAGE_COMPILE_VERIFIED_RENDER_COOK_PENDING' if verify_only else
                            'NINE_INSTANCE_USAGE_SAVED_COMPILED_FRESH_PROCESS_RENDER_COOK_PENDING')
    except Exception as error:
        report.update(status='FAILED_CHECKPOINT_AVAILABLE', error=repr(error))
        raise
    finally:
        try:
            report['protectedUnchanged'] = protected_hashes() == protected and sha(LOG) == report['sourceLogSha256']
            report['finalTargetHashes'] = {p: sha(disk(p)) for p in ALLOWLIST}
            if verify_only and any(sha(disk(r['package'])) != r['originalSha256'] for r in report['targets']):
                report['protectedUnchanged'] = False
        except Exception as error:
            report.update(protectedUnchanged=False, protectionError=repr(error))
        if not report['protectedUnchanged']:
            report['status'] = 'FAILED_PROTECTED_HASHES'
        write()
        if not report['protectedUnchanged']:
            raise RuntimeError('Protected maps/config/PBR assets or source evidence changed')
    return report


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))

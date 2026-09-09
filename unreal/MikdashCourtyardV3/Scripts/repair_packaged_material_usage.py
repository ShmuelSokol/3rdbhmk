"""Six reviewed Windows12 Nanite usage flags only; no graph or map writes.

Native: -PackagedUsageApply OR -PackagedUsageVerify=<successful apply receipt>.
Offline invocation prints the SHA-pinned plan without importing Unreal.
"""
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
from release_surface_soft import sha, inventory

LOG = ROOT.parent / 'RuntimeBuild-12-Attempt2/StartupSmoke/runtime.log'
LOG_SHA = '600635f25818db91aa419bb3f6be453714d3cbaefdc297ce9ba1851e35e6ceea'
BASE = '/Game/MikdashV3/MaterialReview/KotelSurfacePolishV2/Materials/M_KotelSurface_'
HASHES = [
    '5be077894bab948a62938720333b6b3b344a3686e5129804abd2ec9b98f17fa6',
    '2dc5b3de4e7bc3828ea57cf7123c78a3283389c74ebce326e864ca0bbde7d093',
    'f1448db51c3c3b99ce6863bd2b7e77973b9c4268a944dd4ffa372b34301152a0',
    '4ecc1add665be7b380871ce08ea7ceb76305fd05ef96f57df014b05cbb52c997',
    '4190ec312686d21dc41696d603d9986e69a50ac950c96fcc5ef2bf5ce0e0c77b',
    '0e670dcc8f0e9c4fa36b7a74bc9705127a7e2316bc6c455eba12c71f85487c7d',
]


def plan():
    if sha(LOG) != LOG_SHA:
        raise RuntimeError('Reviewed startup log changed')
    text = LOG.read_text(encoding='utf-8-sig', errors='replace')
    rows = []
    for i, digest in enumerate(HASHES):
        package = BASE + str(i)
        object_path = package + '.' + package.rsplit('/', 1)[1]
        if ('Material ' + object_path + ' missing usage flag Nanite! Default Material will be used in game.') not in text:
            raise RuntimeError('Exact reviewed warning absent: ' + package)
        rows.append(dict(path=package, file='Content/' + package[6:] + '.uasset', originalSha256=digest))
    return rows


def content_hashes():
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in (ROOT / 'Content').rglob('*') if p.is_file()}


def run(apply=False, verify=None):
    import unreal as u
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT / 'SourceAssets/perf-review'; folder.mkdir(parents=True, exist_ok=True)
    output = folder / ('packaged-material-usage-' + stamp + '.json')
    report = dict(status='started', processId=os.getpid(), sourceLog=str(LOG), sourceLogSha256=LOG_SHA,
                  mapSaved=False, errors=[], materials=[], scope='Six Nanite flags only; recook and packaged visual acceptance pending')
    before = None
    def write():
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    write()
    try:
        if bool(apply) == bool(verify): raise RuntimeError('Choose apply or fresh verify')
        if Path(u.Paths.project_dir()).resolve() != ROOT: raise RuntimeError('Wrong project')
        inventory()
        if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(): raise RuntimeError('PIE active')
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages before operation')
        rows = plan(); targets = {r['file'] for r in rows}
        before = content_hashes()
        protected = {p: h for p, h in before.items() if p not in targets}
        report['protectedHashes'] = protected
        report['mapHashesBefore'] = {p: h for p, h in before.items() if p.endswith('.umap')}
        if len(report['mapHashesBefore']) != 19: raise RuntimeError('Expected all 19 maps')
        if verify:
            earlier = json.loads(Path(verify).read_text(encoding='utf-8-sig'))
            pid = earlier.get('processId')
            if type(pid) is not int or pid <= 0 or pid == os.getpid(): raise RuntimeError('Distinct positive apply PID required')
            if earlier.get('status') != 'saved_six_usage_flags' or earlier.get('sourceLogSha256') != LOG_SHA or earlier.get('errors'):
                raise RuntimeError('Not a successful matching apply receipt')
            if earlier.get('protectedHashes') != protected: raise RuntimeError('Protected content changed since apply')
            expected = {r['file']: r['savedSha256'] for r in earlier['materials']}
            if set(expected) != targets: raise RuntimeError('Apply material scope differs')
            report['applyReceipt'] = str(Path(verify).resolve()); report['applyReceiptSha256'] = sha(Path(verify))
        else:
            expected = {r['file']: r['originalSha256'] for r in rows}
        if any(before.get(p) != h for p, h in expected.items()): raise RuntimeError('Six material bytes differ from pinned plan/receipt')
        if apply:
            checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('PackagedMaterialUsage-' + stamp)
            checkpoint.mkdir(parents=True, exist_ok=False)
            report['checkpoint'] = str(checkpoint)
            # All originals copied before ANY material load can auto-update usage.
            for row in rows:
                dest = checkpoint / row['file']; dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / row['file'], dest)
                if sha(dest) != row['originalSha256']: raise RuntimeError('Checkpoint mismatch')
        report['materials'] = rows; write()
        for row in rows:
            material = u.load_asset(row['path'])
            if not isinstance(material, u.Material): raise RuntimeError('Expected base Material')
            row['beforeUsage'] = bool(u.MaterialEditingLibrary.has_material_usage(material, u.MaterialUsage.MATUSAGE_NANITE))
            if apply:
                u.MaterialEditingLibrary.set_base_material_usage(material, u.MaterialUsage.MATUSAGE_NANITE, True)
            row['afterUsage'] = bool(u.MaterialEditingLibrary.has_material_usage(material, u.MaterialUsage.MATUSAGE_NANITE))
            if not row['afterUsage']: raise RuntimeError('Nanite usage false: ' + row['path'])
            if apply and not u.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
                raise RuntimeError('Material save refused: ' + row['path'])
            row['savedSha256'] = sha(ROOT / row['file']); row['saved'] = apply
            write()
        report['status'] = 'saved_six_usage_flags' if apply else 'fresh_six_usage_flags_verified'
    except Exception as exc:
        report['status'] = 'failed'; report['errors'].append(repr(exc))
    finally:
        if before is not None:
            after = content_hashes()
            target_files = { 'Content/' + (BASE + str(i))[6:] + '.uasset' for i in range(6) }
            changed = [p for p in set(before) | set(after) if before.get(p) != after.get(p)]
            report['changedFiles'] = sorted(changed)
            report['mapHashesAfter'] = {p: h for p, h in after.items() if p.endswith('.umap')}
            report['allMapsUnchanged'] = report.get('mapHashesBefore') == report['mapHashesAfter']
            report['protectedContentUnchanged'] = not any(p not in target_files for p in changed)
            if not report['protectedContentUnchanged'] or not report['allMapsUnchanged'] or (verify and changed):
                report['status'] = 'failed'; report['errors'].append('Unexpected disk mutation')
        write()
        u.log('PACKAGED_MATERIAL_USAGE ' + report['status'] + ' ' + str(output))
    if report['status'] == 'failed': raise RuntimeError('Repair/verification failed; inspect ' + str(output))
    return report


if __name__ == '__main__':
    try:
        import unreal
    except ImportError:
        print(json.dumps(plan(), indent=2))
    else:
        cmd = unreal.SystemLibrary.get_command_line()
        match = re.search(r'-PackagedUsageVerify=(?:"([^"]+)"|(\S+))', cmd, re.I)
        run(apply='-packagedusageapply' in cmd.lower(), verify=(match.group(1) or match.group(2)) if match else None)

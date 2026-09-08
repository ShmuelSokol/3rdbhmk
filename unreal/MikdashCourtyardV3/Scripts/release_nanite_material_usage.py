"""Persist only Nanite material usage warnings found in the takeover render log.

Run serially as a Python commandlet after the capture editor exits. Checkpoints
each affected material before loading it, never saves a map, and reads usage back.
The next fresh native render/cook must verify persistence, not cached editor state.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT.parent / 'Astra-Resume-Capture-20260908.log'
MAPS = [
    'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap',
    'Content/MikdashV3/Maps/Courtyard.umap',
    'Content/MikdashV3/FutureMountV1/L_FutureMount.umap',
    'Content/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold.umap',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan():
    paths = sorted(set(re.findall(
        r'Material (/Game/MikdashV3/[^\s]+) was missing the usage flag Nanite',
        LOG.read_text(encoding='utf-8-sig', errors='replace'))))
    if not paths:
        raise RuntimeError('No observed Nanite material warnings in capture log')
    return paths


def run():
    import unreal as u
    verify_only = '-nanitematerialverifyonly' in u.SystemLibrary.get_command_line().lower()
    if Path(u.Paths.project_dir()).resolve() != ROOT.resolve():
        raise RuntimeError('Wrong project')
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('PIE active')
    if (u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Dirty packages before repair')
    paths = plan()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('NaniteMaterialUsage-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    folder = ROOT / 'SourceAssets/perf-review'
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / ('nanite-material-usage-' + stamp + '.json')
    before_maps = {p: sha(ROOT / p) for p in MAPS}
    report = dict(status='started', verifyOnly=verify_only, sourceLog=str(LOG), sourceLogSha256=sha(LOG),
                  checkpoint=str(checkpoint), beforeMapHashes=before_maps,
                  materials=[], errors=[], scope='Saved material usage only; render and cook pending')

    def write():
        out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    write()
    try:
        # Snapshot every target before any load can auto-update its usage.
        for path in paths:
            package = path.split('.')[0]
            relative = 'Content/' + package[6:] + '.uasset'
            source = ROOT / relative
            saved_copy = checkpoint / relative
            saved_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, saved_copy)
            digest = sha(source)
            if sha(saved_copy) != digest:
                raise RuntimeError('Checkpoint mismatch: ' + path)
            report['materials'].append(dict(path=path, file=relative, beforeSha256=digest))
        write()
        for row in report['materials']:
            material = u.load_asset(row['path'])
            if not isinstance(material, u.Material):
                raise RuntimeError('Observed warning did not resolve to a base material: ' + row['path'])
            row['beforeUsage'] = bool(u.MaterialEditingLibrary.has_material_usage(material, u.MaterialUsage.MATUSAGE_NANITE))
            if not verify_only:
                u.MaterialEditingLibrary.set_base_material_usage(material, u.MaterialUsage.MATUSAGE_NANITE, True)
            row['afterUsage'] = bool(u.MaterialEditingLibrary.has_material_usage(material, u.MaterialUsage.MATUSAGE_NANITE))
            if not row['afterUsage']:
                raise RuntimeError('Nanite usage readback false: ' + row['path'])
            if not verify_only and not u.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
                raise RuntimeError('Material save failed: ' + row['path'])
            row['afterSha256'] = sha(ROOT / row['file'])
            row['saved'] = not verify_only
            if verify_only and row['afterSha256'] != row['beforeSha256']:
                raise RuntimeError('Material changed during read-only verification')
            write()
        report['status'] = ('fresh_process_usage_verified_render_pending' if verify_only
                            else 'saved_usage_verified_fresh_process_render_pending')
    except Exception as exc:
        report['status'] = 'failed_material_usage_repair'
        report['errors'].append(repr(exc))
    finally:
        report['afterMapHashes'] = {p: sha(ROOT / p) for p in MAPS}
        report['allMapBytesUnchanged'] = before_maps == report['afterMapHashes']
        if not report['allMapBytesUnchanged']:
            report['status'] = 'failed_unexpected_map_change'
        write()
        u.log('NANITE_MATERIAL_USAGE ' + report['status'] + ' ' + str(out))
    if report['errors'] or not report['allMapBytesUnchanged']:
        raise RuntimeError('Material usage repair failed; inspect receipt')
    return report


if __name__ == '__main__':
    try:
        import unreal
    except ImportError:
        print(json.dumps(dict(observedMaterialPaths=plan()), indent=2))
    else:
        run()

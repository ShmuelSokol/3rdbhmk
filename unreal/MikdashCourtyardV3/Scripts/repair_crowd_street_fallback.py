"""Backed-up, one-asset fallback repair; default mode is fresh-process verification."""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
import unreal as ue
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_crowd_street_ground import ROOT, sha, extract
from generate_kotel_retaining_wall import Terrain

ASSET = '/Game/MikdashV3/JerusalemContext/Terrain/SM_JerusalemTerrain_07_09'
FILE = ROOT / ('Content/' + ASSET.removeprefix('/Game/') + '.uasset')
BASE = ROOT / 'SourceAssets/perf-review/crowd-vat/street-native-mesh-20260919T010523238528Z.json'
BASE_SHA = '446dd502d3e30d4290ace09f6eec3a1f9a01736d7f25af29fc4409dda2c97d38'
APPLY = '-StreetFallbackApply' in ue.SystemLibrary.get_command_line()


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT / 'SourceAssets/perf-review/crowd-vat'
    output = folder / ('street-fallback-' + stamp + '.json')
    report = dict(status='running', apply=APPLY, asset=ASSET)
    try:
        assert sha(BASE) == BASE_SHA, 'Baseline changed'
        baseline = next(a for a in json.loads(BASE.read_text())['assets'] if a['asset'] == ASSET)
        report['beforeSha256'] = sha(FILE)
        if APPLY:
            assert sha(FILE) == baseline['assetSha256Before'], 'Only original audited asset may be repaired'
        mesh = ue.load_asset(ASSET)
        original = extract(ue, mesh, ue.GeometryScriptLODType.SOURCE_MODEL)
        assert original == baseline['geometry']['source'], 'Source geometry changed'
        settings = mesh.get_editor_property('nanite_settings')
        report['settingsBefore'] = settings.export_text()
        materials = [m.export_text() for m in mesh.get_editor_property('static_materials')]
        report['originalMaterials'] = materials
        if not APPLY:
            candidates = []
            for path in folder.glob('street-fallback-*.json'):
                if path.name.startswith('street-fallback-run-'):
                    continue
                prior = json.loads(path.read_text(encoding='utf-8-sig'))
                if (prior.get('status') == 'applied-needs-fresh-verification'
                        and prior.get('afterSha256') == report['beforeSha256']):
                    candidates.append((path, prior))
            assert len(candidates) == 1, 'Expected one matching successful apply receipt'
            prior_path, prior = candidates[0]
            assert sha(Path(prior['backup'])) == baseline['assetSha256Before'], 'Backup changed'
            assert materials == prior['originalMaterials'], 'Persisted materials changed'
            assert settings.export_text() == prior['settingsAfter'], 'Persisted settings changed'
            report['applyReceipt'] = str(prior_path)
            report['applyReceiptSha256'] = sha(prior_path)
        assert settings.get_editor_property('enabled'), 'Nanite unexpectedly disabled'
        if APPLY:
            backup = ROOT / 'ReviewCheckpoints' / ('street-fallback-' + stamp)
            backup.mkdir(parents=True, exist_ok=False)
            shutil.copy2(FILE, backup / FILE.name)
            assert sha(backup / FILE.name) == report['beforeSha256']
            report['backup'] = str(backup / FILE.name)
            settings.set_editor_property('fallback_target', ue.NaniteFallbackTarget.PERCENT_TRIANGLES)
            settings.set_editor_property('fallback_percent_triangles', 1.0)
            expected = settings.export_text()
            subsystem = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)
            if subsystem is not None:
                subsystem.set_nanite_settings(mesh, settings, True)
            else:
                # Commandlets can omit editor subsystems. Python property writes
                # send editor change notifications; geometry readback below is mandatory.
                mesh.set_editor_property('nanite_settings', settings)
            assert mesh.get_editor_property('nanite_settings').export_text() == expected, 'Unexpected settings mutation'
        readback = mesh.get_editor_property('nanite_settings')
        assert readback.get_editor_property('fallback_target') == ue.NaniteFallbackTarget.PERCENT_TRIANGLES
        assert readback.get_editor_property('fallback_percent_triangles') == 1.0
        assert extract(ue, mesh, ue.GeometryScriptLODType.SOURCE_MODEL) == original
        assert [m.export_text() for m in mesh.get_editor_property('static_materials')] == materials
        assert str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')) == baseline['collisionTraceFlag']
        assert mesh.get_editor_property('lod_for_collision') == baseline['lodForCollision']
        render = extract(ue, mesh, ue.GeometryScriptLODType.RENDER_DATA)
        source_surface, render_surface = Terrain(original), Terrain(render)
        # Check every source corner and all reviewed contacts, not just triangle count.
        points = [(v[0], v[1]) for v in original['vertices']]
        points += [(s['x'], s['y']) for s in baseline['samples']]
        residuals = []
        for x, y in points:
            a, b = source_surface.z(x, y), render_surface.z(x, y)
            assert a is not None and b is not None, 'Missing surface support'
            residuals.append(abs(a-b))
        assert max(residuals) < 0.001, 'Fallback still differs from source'
        assert len(render['triangles']) == len(original['triangles']) == 512
        report.update(sourceTriangles=512, renderTriangles=len(render['triangles']),
                      checkedPoints=len(points), maximumSurfaceDifferenceCm=max(residuals),
                      settingsAfter=readback.export_text(), sourceUnchanged=True, materialsUnchanged=True)
        if APPLY:
            assert ue.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
        report['afterSha256'] = sha(FILE)
        if not APPLY:
            assert report['afterSha256'] == report['beforeSha256'], 'Verification changed asset'
        report['status'] = 'applied-needs-fresh-verification' if APPLY else 'verified-fresh-native'
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        with output.open('x', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2)
            handle.write('\n')
        ue.log('Street fallback: ' + str(output))


if __name__ == '__main__':
    main()

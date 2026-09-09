"""Reviewed main-only vessel slot substitution; existing material, no asset edits.
Use -VesselGoldExpectedHash=<current main SHA256> to apply, or
-VesselGoldVerify=<absolute apply receipt> from a fresh process. Never auto-runs.
Acceptance is reduced vessel glare from A/B 045055Z, not full scene quality.
"""
import json
import os
from pathlib import Path
import re
import shutil
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
from release_surface_soft import sha, inventory, check_hashes
from release_place_assets import snapshot_row, numeric_baseline_rows

TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
EXPECTED = '478d326fc715e6690272e07043dd1238912d1c53a47066fb18cb432b0027e76c'
MATERIAL = '/Game/MikdashV3/IntegratedReviewV2/Lighting/MI_PBR_GoldMatte_Partition'
MATERIAL_SHA = '50d935da7fe496da45c08b32d22d3b8e988000d96b121b1c5364cad71c3a1d43'
ORIGINAL = '/Game/MikdashV3/MaterialReview/HeikhalKeilimV1/M_HeikhalKeilim_Gold'
MESHES = {'/Game/MikdashV3/MaterialReview/KeilimTIV1/Meshes/SM_KeilimTIV1_' + n: count
          for n, count in [('IncenseAltar',607), ('Shulchan_Bazichin',2),
                           ('Shulchan_Kanim',28), ('Shulchan_Rings',4),
                           ('Shulchan_Snifim',248), ('Shulchan_Table',224)]}


def run(expected=None, verify=None):
    import unreal as u
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT / 'SourceAssets/lighting-review'
    folder.mkdir(parents=True, exist_ok=True)
    receipt = folder / ('vessel-gold-' + stamp + '.json')
    mapfile = ROOT / 'Content' / (TARGET[6:] + '.umap')
    report = {'status':'started', 'map':TARGET, 'pid':os.getpid(), 'errors':[],
              'mapSaved':False, 'review':'Main vessel A/B 045055Z: reduced glare only',
              'material':MATERIAL, 'materialSha256':MATERIAL_SHA, 'meshSlots':MESHES}
    protected = {}
    before = sha(mapfile)
    report['mapSha256Before'] = before
    def write():
        receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    write()
    try:
        if bool(expected) == bool(verify):
            raise RuntimeError('Choose explicit expected-hash apply or fresh verify')
        inventory()
        if Path(u.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        earlier = json.loads(Path(verify).read_text(encoding='utf-8-sig')) if verify else None
        if earlier:
            if earlier.get('status') != 'saved_reopened' or earlier.get('map') != TARGET or earlier.get('pid') == os.getpid():
                raise RuntimeError('Invalid fresh verification receipt')
            if earlier.get('meshSlots') != MESHES or earlier.get('materialSha256') != MATERIAL_SHA:
                raise RuntimeError('Receipt scope differs')
            if check_hashes(earlier['protected']):
                raise RuntimeError('Protected content changed since apply')
            expected = earlier['mapSha256After']
        elif expected != EXPECTED:
            raise RuntimeError('Explicit hash must match reviewed main state')
        if not re.fullmatch('[0-9a-f]{64}', expected or '') or before != expected:
            raise RuntimeError('Map hash mismatch')
        if sha(ROOT / 'Content' / (MATERIAL[6:] + '.uasset')) != MATERIAL_SHA:
            raise RuntimeError('Reviewed material changed')
        editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)
        def clean():
            if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('PIE or dirty packages')
        clean()
        protected = {str(p):sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file() and p != mapfile}
        report['protected'] = protected
        if not levels.load_level(TARGET):
            raise RuntimeError('Load failed')
        clean()
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Wrong world')
        material = u.load_asset(MATERIAL)
        if material is None:
            raise RuntimeError('Material absent')
        def discover():
            found = {}
            for actor in actors.get_all_level_actors():
                for comp in actor.get_components_by_class(u.StaticMeshComponent):
                    mesh = comp.get_editor_property('static_mesh')
                    package = mesh.get_path_name().split('.')[0] if mesh else None
                    if package in MESHES:
                        if package in found or comp.get_num_materials() != MESHES[package] or actor.get_outermost().get_name() != TARGET:
                            raise RuntimeError('Vessel identity/slot count/ownership differs: ' + package)
                        found[package] = (actor, comp)
            if set(found) != set(MESHES) or sum(MESHES.values()) != 1113:
                raise RuntimeError('Expected exactly six vessel components and 1113 slots')
            return found
        def identity(found):
            return {k:[a.get_name(),c.get_name()] for k,(a,c) in found.items()}
        def snapshot():
            aa = list(actors.get_all_level_actors())
            result = numeric_baseline_rows([snapshot_row(u,a,TARGET) for a in aa], strict=True)
            for actor in aa:
                if actor.get_outermost().get_name() != TARGET:
                    continue
                for comp in actor.get_components_by_class(u.StaticMeshComponent):
                    mesh = comp.get_editor_property('static_mesh')
                    package = mesh.get_path_name().split('.')[0] if mesh else None
                    if package in MESHES:
                        continue
                    for slot in range(comp.get_num_materials()):
                        mat = comp.get_material(slot)
                        result['material:' + comp.get_path_name() + ':' + str(slot)] = mat.get_path_name() if mat else None
            return result
        found = discover()
        identities = identity(found)
        if earlier and earlier['components'] != identities:
            raise RuntimeError('Fresh component identity differs')
        report['components'] = identities
        baseline = snapshot()
        clean()
        if not levels.load_level(TARGET):
            raise RuntimeError('Pristine reload failed')
        clean()
        found = discover()
        if identity(found) != identities or snapshot() != baseline:
            raise RuntimeError('Pristine reload churn: review before mutation')
        if not verify:
            for package, (actor, comp) in found.items():
                for slot in range(MESHES[package]):
                    old = comp.get_material(slot)
                    if old is None or old.get_path_name().split('.')[0] != ORIGINAL:
                        raise RuntimeError('Unexpected original slot: ' + package + ':' + str(slot))
            checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('VesselGold-' + stamp)
            checkpoint.mkdir(parents=True, exist_ok=False)
            shutil.copy2(mapfile, checkpoint/mapfile.name)
            if sha(checkpoint/mapfile.name) != before:
                raise RuntimeError('Checkpoint hash mismatch')
            for name in ('__ExternalActors__','__ExternalObjects__'):
                source = ROOT/'Content'/name/TARGET[6:]
                if source.exists():
                    shutil.copytree(source, checkpoint/name/TARGET[6:])
            report['checkpoint'] = str(checkpoint)
            write()
            for package, (actor, comp) in found.items():
                actor.modify(True)
                comp.modify(True)
                for slot in range(MESHES[package]):
                    comp.set_material(slot, material)
                    if comp.get_material(slot) != material:
                        raise RuntimeError('Immediate material readback failed')
            if snapshot() != baseline or check_hashes(protected):
                raise RuntimeError('Unrelated state changed before save')
            if not levels.save_current_level():
                raise RuntimeError('Save refused')
            report['mapSaved'] = True
            report['mapSha256After'] = sha(mapfile)
            write()
            if not levels.load_level(TARGET):
                raise RuntimeError('Reopen failed')
        found = discover()
        if identity(found) != identities or snapshot() != baseline:
            raise RuntimeError('Unrelated state or component identity changed')
        for package, (actor, comp) in found.items():
            if any(comp.get_material(i) != material for i in range(MESHES[package])):
                raise RuntimeError('Saved material readback failed: ' + package)
        clean()
        report['verifiedSlots'] = 1113
        report['status'] = 'fresh_verified' if verify else 'saved_reopened'
    except Exception as error:
        report['status'] = 'failed'
        report['errors'].append(repr(error))
        raise
    finally:
        report['mapSha256After'] = sha(mapfile)
        report['protectedDifferences'] = check_hashes(protected)
        if report['protectedDifferences'] or (verify and report['mapSha256After'] != before):
            report['status'] = 'failed_preservation'
        write()
    if report['status'].startswith('failed'):
        raise RuntimeError(report['status'])
    return report


if __name__ == '__main__':
    try:
        import unreal as u
    except ImportError:
        print('Prepared helper only; no native execution')
    else:
        command = u.SystemLibrary.get_command_line()
        args = {x.split('=',1)[0].lower():x.split('=',1)[1].strip('"') for x in command.split() if '=' in x}
        try:
            run(expected=args.get('-vesselgoldexpectedhash'), verify=args.get('-vesselgoldverify'))
        finally:
            if '-executepythonscript' in command.lower() and '-run=pythonscript' not in command.lower():
                u.SystemLibrary.quit_editor()

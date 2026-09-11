"""Put the vertex-animated crowd on RELEASE_CrowdField, both maps, Candidate48 first.

WHAT CHANGES (one actor per map, nothing else):
  * PoseMeshes -> the six SM_CrowdVAT_<body> meshes of Scripts/create_crowd_vat_v2.py, in bake order
  * bUseVertexAnimation on, and the numbers in release_crowd_vat.spec.json "wanted"
  * CrowdMaterialOverride cleared, and every pose component's per-slot override materials cleared
    (the 8 Sep tint fix left fifteen per component; they would replace the VAT material)
  * the editor preview rebuilt through BuildEditorPreview so the saved map holds VAT instances

GUARDS (the project's full pattern): right project, no PIE world, no dirty packages, compiled
AMikdashCrowdField exposes every property this writes (else the editor binary is stale), the VAT
bake receipt is verified-after-reopen, checkpoint copy of the .umap hash-equal to the before hash,
protected-asset hashes before/after (VAT assets, resident bodies and clips, the other map), a
whole-scene snapshot before save that may differ ONLY in RELEASE_CrowdField, save, REOPEN, numeric
readback of every written value, pointers resolved against disk, receipt at start / failure /
finally. -CrowdVatRevert restores the apply receipt's before block through the same pass.

Launch (hidden editor, one engine at a time):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject" /Engine/Maps/Entry
      -ExecutePythonScript="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_crowd_vat.py"
      -CrowdVatApplyAll -unattended -nullrhi -NoSplash -abslog=<unique>
  Modes: -CrowdVatApplyAll | -CrowdVatApply -CrowdVatTarget=Candidate48|Main50 |
         -CrowdVatRevert -CrowdVatTarget=... | -CrowdVatRevertAndReapply -CrowdVatTarget=... |
         -CrowdVatMapVerify (read-only, both maps)
Offline:  python Scripts/release_crowd_vat.py --offline-check
"""
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'Scripts' / 'release_crowd_vat.spec.json'
BAKE_SPEC_PATH = ROOT / 'Scripts' / 'create_crowd_vat_v2.spec.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp_now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def utc():
    return datetime.now(timezone.utc).isoformat()


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if Path(spec['projectDir']).resolve() != ROOT.resolve():
        raise RuntimeError('Spec project directory differs from the script root')
    return spec


def disk_umap(package):
    return ROOT / 'Content' / (package[len('/Game/'):] + '.umap')


def disk_uasset(path):
    return ROOT / 'Content' / (path.split('.')[0][len('/Game/'):] + '.uasset')


def _load(name, relative):
    module_spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def receipt_folder(spec):
    folder = ROOT / spec['receiptFolder']
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def verified_bake(spec):
    """The newest bake that was verified in a fresh process, and the bake receipt it verified."""
    folder = receipt_folder(spec)
    for f in sorted(folder.glob('crowd-vat-verify-*.json'), reverse=True):
        data = json.loads(f.read_text(encoding='utf-8-sig'))
        if data.get('status') == spec['bakeVerifyStatus']:
            bake_file = folder / data['bakeReceipt']
            bake = json.loads(bake_file.read_text(encoding='utf-8-sig'))
            if bake.get('namespace') != spec['bakeNamespace']:
                continue
            return f, data, bake_file, bake
    raise RuntimeError('No verified VAT bake receipt: run create_crowd_vat_v2.py -CrowdVatVerify first')


def offline_check():
    spec = load_spec()
    problems = []
    try:
        _, _, bake_file, bake = verified_bake(spec)
        meshes = [v['mesh'] for v in bake['variants']]
        if len(meshes) != spec['poseComponents']:
            problems.append('bake has %d meshes, the actor has %d pose components' % (len(meshes), spec['poseComponents']))
        for m in meshes:
            if not disk_uasset(m).is_file():
                problems.append('VAT mesh missing on disk: ' + m)
    except RuntimeError as exc:
        problems.append(str(exc))
    for key, package in spec['targets'].items():
        if not disk_umap(package).is_file():
            problems.append('map missing: ' + package)
    bake_spec = json.loads(BAKE_SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec['customDataFloats'] != bake_spec['customData']['count']:
        problems.append('custom data float count differs between the bake material and the actor')
    if abs(spec['wanted']['vat_walk_ground_speed_cm_per_second'] - bake_spec['walk']['groundSpeedCmPerSecAtRate1']) > 1e-6:
        problems.append('actor ground speed differs from the baked clip ground speed: the crowd would slide')
    if abs(spec['wanted']['vat_walk_cycle_seconds'] - bake_spec['walk']['expectedLengthSec']) > 1e-6:
        problems.append('actor cycle seconds differ from the baked clip length')
    if abs(spec['wanted']['mesh_yaw_offset_degrees'] - bake_spec['meshYawOffsetDegrees']) > 1e-6:
        problems.append('yaw offset differs from the bake spec')
    if spec['wanted']['garment_palette_size'] != len(bake_spec['material']['palette']):
        problems.append('garment palette size differs from the material palette')
    if spec['order'][0] != 'Candidate48':
        problems.append('Candidate48 must be first')
    return problems


# =============================================================================================
# Engine
# =============================================================================================
def _doc_props(type_object):
    names = set()
    for line in (getattr(type_object, '__doc__', '') or '').splitlines():
        line = line.strip()
        if line.startswith('- ``'):
            end = line.find('``', 4)
            if end > 4:
                names.add(line[4:end])
    return names


def _path(obj):
    return obj.get_path_name() if obj else None


def _same(a, b, tol=1e-3):
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same(a[k], b[k], tol) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= tol
    return a == b


def _guards(ue):
    if Path(ue.Paths.project_dir()).resolve() != ROOT.resolve():
        raise RuntimeError('Wrong project directory: refuse native mutation')
    if ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Live PIE world; refuse')
    dirty = list(ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + \
        list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty:
        raise RuntimeError('Dirty packages present: %r' % [p.get_name() for p in dirty][:10])


def _find_field(ue, spec):
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    found = [a for a in actors.get_all_level_actors() if a.get_actor_label() == spec['actorLabel']]
    if len(found) != 1:
        raise RuntimeError('Expected exactly one %s, found %d' % (spec['actorLabel'], len(found)))
    if found[0].get_class().get_path_name() != spec['actorClass']:
        raise RuntimeError('%s is a %s' % (spec['actorLabel'], found[0].get_class().get_path_name()))
    return found[0]


def _components(ue, field, spec):
    comps = sorted(field.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent), key=lambda c: c.get_name())
    if len(comps) != spec['poseComponents']:
        raise RuntimeError('Expected %d pose components, found %d' % (spec['poseComponents'], len(comps)))
    return comps


def _snapshot(ue, field, spec):
    props = {}
    for name in spec['wanted']:
        value = field.get_editor_property(name)
        props[name] = value if isinstance(value, (bool, int, float)) else float(value)
    comps = []
    for c in _components(ue, field, spec):
        try:
            custom = list(c.get_editor_property('per_instance_sm_custom_data'))
        except Exception:                                            # noqa: BLE001
            custom = None
        comps.append(dict(name=c.get_name(), staticMesh=_path(c.get_editor_property('static_mesh')),
                          overrideMaterials=[_path(m) for m in list(c.get_editor_property('override_materials'))],
                          numCustomDataFloats=int(c.get_editor_property('num_custom_data_floats')),
                          instances=int(c.get_instance_count()),
                          customDataFloatsSaved=len(custom) if custom is not None else None,
                          customDataSample=[round(float(x), 5) for x in custom[:22]] if custom else None))
    return dict(properties=props,
                poseMeshes=[_path(m) for m in list(field.get_editor_property('pose_meshes'))],
                crowdMaterialOverride=_path(field.get_editor_property('crowd_material_override')),
                components=comps,
                summary=str(field.get_crowd_summary()))


def _write(ue, field, spec, wanted):
    """wanted = dict(properties, poseMeshes, crowdMaterialOverride, overrides=[list per component])."""
    missing = sorted(set(wanted['properties']) - _doc_props(ue.MikdashCrowdField))
    if missing:
        raise RuntimeError('Compiled AMikdashCrowdField lacks %r: the editor binary is stale, run UnrealBuildTool' % missing)
    for name, value in wanted['properties'].items():
        field.set_editor_property(name, value)
    meshes = []
    for path in wanted['poseMeshes']:
        mesh = ue.load_asset(path)
        if not mesh:
            raise RuntimeError('Pose mesh does not load: ' + path)
        meshes.append(mesh)
    field.set_editor_property('pose_meshes', meshes)
    override = ue.load_asset(wanted['crowdMaterialOverride']) if wanted['crowdMaterialOverride'] else None
    field.set_editor_property('crowd_material_override', override)
    for comp, paths in zip(_components(ue, field, spec), wanted['overrides']):
        mats = [ue.load_asset(p) if p else None for p in paths]
        comp.set_editor_property('override_materials', mats)
    field.build_editor_preview()


def _resolve_on_disk(ue, snapshot, master_path):
    rows = []
    for path in snapshot['poseMeshes']:
        row = dict(mesh=path, onDisk=disk_uasset(path).is_file())
        mesh = ue.load_asset(path)
        row['loads'] = bool(mesh)
        slots = []
        if mesh:
            for i, _ in enumerate(mesh.get_editor_property('static_materials')):
                mat = mesh.get_material(i)
                parent = mat.get_editor_property('parent') if mat and hasattr(mat, 'get_editor_property') and \
                    'parent' in _doc_props(type(mat)) else None
                slots.append(dict(material=_path(mat), parent=_path(parent),
                                  materialOnDisk=disk_uasset(_path(mat)).is_file() if mat else False))
        row['slots'] = slots
        row['allSlotsOnVatMaster'] = bool(slots) and all(s['parent'] == master_path and s['materialOnDisk'] for s in slots)
        rows.append(row)
    return rows


def _protected(spec, bake, targets_excluded):
    out = {}
    ns_dir = ROOT / 'Content' / spec['bakeNamespace'][len('/Game/'):]
    for f in sorted(ns_dir.rglob('*.uasset')):
        out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    bake_spec = json.loads(BAKE_SPEC_PATH.read_text(encoding='utf-8-sig'))
    for v in bake_spec['variants']:
        for key in ('skeletalMesh', 'walk', 'idle'):
            f = disk_uasset(v[key])
            out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    for key, package in spec['targets'].items():
        if key in targets_excluded:
            continue
        f = disk_umap(package)
        out[str(f.relative_to(ROOT)).replace('\\', '/')] = sha(f)
    return out


def _pass(ue, spec, target, kind, wanted_fn):
    stamp = stamp_now()
    MAP = spec['targets'][target]
    map_file = disk_umap(MAP)
    out = receipt_folder(spec) / ('crowd-vat-%s-%s-%s.json' % (kind, target, stamp))
    receipt = dict(status='starting', mode=kind, target=target, map=MAP, utc=utc(), stamp=stamp,
                   mapBeforeSha256=sha(map_file), errors=[])

    def write():
        out.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    try:
        _guards(ue)
        verify_file, _, bake_file, bake = verified_bake(spec)
        receipt['bake'] = dict(verifyReceipt=verify_file.name, bakeReceipt=bake_file.name, bakeReceiptSha256=sha(bake_file))
        protected_before = _protected(spec, bake, {target})
        receipt['protectedBefore'] = protected_before
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + target + '-' + kind + '-' + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'BeforeCrowdVAT.umap')
        if sha(checkpoint / 'BeforeCrowdVAT.umap') != receipt['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy mismatch')
        receipt['checkpoint'] = str(checkpoint)
        write()
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            if not levels.load_level(MAP):
                raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Unexpected editor world')
        crowd = _load('crowd_vat_scene_snapshot', 'Scripts/release_resident_crowd.py')
        scene_before = crowd._scene_snapshot(ue, actors)
        field = _find_field(ue, spec)
        before = _snapshot(ue, field, spec)
        receipt['before'] = before
        write()
        wanted = wanted_fn(ue, bake, before)
        receipt['wanted'] = wanted
        _write(ue, field, spec, wanted)
        after_set = _snapshot(ue, field, spec)
        receipt['afterSet'] = after_set
        write()
        if not _same(after_set['properties'], wanted['properties']) or after_set['poseMeshes'] != wanted['poseMeshes']:
            raise RuntimeError('Properties did not read back as planned before the save')
        scene_after = crowd._scene_snapshot(ue, actors)
        moved = sorted(k for k in set(scene_before) | set(scene_after) if scene_before.get(k) != scene_after.get(k))
        receipt['sceneChanges'] = moved
        if set(moved) - {field.get_name()}:
            raise RuntimeError('Unexpected scene changes outside %s: %r' % (field.get_name(), sorted(set(moved) - {field.get_name()})[:20]))
        if not levels.save_current_level():
            raise RuntimeError('Level save failed (check for a zombie UnrealEditor holding the map)')
        receipt.update(mapSaved=True, mapAfterSha256=sha(map_file), status='saved_reopen_pending')
        write()
        if receipt['mapAfterSha256'] == receipt['mapBeforeSha256']:
            raise RuntimeError('save_current_level returned True but the .umap bytes did not change')
        if not levels.load_level(MAP) or editor.get_editor_world().get_outermost().get_name() != MAP:
            raise RuntimeError('Reopen failed')
        field = _find_field(ue, spec)
        readback = _snapshot(ue, field, spec)
        receipt['readbackAfterReopen'] = readback
        problems = []
        if not _same(readback['properties'], wanted['properties']):
            problems.append('properties differ after reopen')
        if readback['poseMeshes'] != wanted['poseMeshes']:
            problems.append('pose meshes differ after reopen')
        if readback['crowdMaterialOverride'] != wanted['crowdMaterialOverride']:
            problems.append('crowd material override differs after reopen')
        for comp, paths in zip(readback['components'], wanted['overrides']):
            if comp['overrideMaterials'] != [p for p in paths]:
                problems.append('%s override materials %r' % (comp['name'], comp['overrideMaterials']))
        if wanted['properties'].get('use_vertex_animation'):
            master = spec.get('vatMaster') or bake['master']['path']
            disk = _resolve_on_disk(ue, readback, master)
            receipt['poseMeshesResolvedOnDisk'] = disk
            if not all(r['onDisk'] and r['loads'] and r['allSlotsOnVatMaster'] for r in disk):
                problems.append('a pose mesh or one of its slot materials does not resolve on disk to the VAT master')
            master_asset = ue.load_asset(master)
            if not master_asset or not master_asset.get_editor_property('used_with_instanced_static_meshes'):
                problems.append('VAT master is not flagged used_with_instanced_static_meshes')
            for comp, mesh in zip(readback['components'], wanted['poseMeshes']):
                if comp['staticMesh'] != mesh:
                    problems.append('%s draws %s' % (comp['name'], comp['staticMesh']))
                if comp['instances'] > 0 and comp['numCustomDataFloats'] != spec['customDataFloats']:
                    problems.append('%s has %d custom floats' % (comp['name'], comp['numCustomDataFloats']))
        if problems:
            raise RuntimeError('Readback after reopen: %r' % problems)
        protected_after = _protected(spec, bake, {target})
        receipt['protectedAfter'] = protected_after
        moved_assets = sorted(k for k in set(protected_before) | set(protected_after)
                              if protected_before.get(k) != protected_after.get(k))
        receipt['protectedChanged'] = moved_assets
        if moved_assets:
            raise RuntimeError('Protected assets changed bytes: %r' % moved_assets)
        receipt['status'] = '%s_saved_reopened_readback_frame_review_pending' % kind
        write()
    except Exception:
        receipt['status'] = 'failed'
        receipt['errors'].append(traceback.format_exc())
        try:
            receipt['mapAfterSha256'] = sha(map_file)
        except Exception:                                            # noqa: BLE001
            pass
        write()
        raise
    return receipt


def run_apply(ue, spec, target):
    def wanted_fn(ue_, bake, before):
        return dict(properties=dict(spec['wanted']),
                    poseMeshes=[v['mesh'] for v in bake['variants']],
                    crowdMaterialOverride=None,
                    overrides=[[] for _ in range(spec['poseComponents'])])
    return _pass(ue, spec, target, 'apply', wanted_fn)


def run_revert(ue, spec, target):
    previous = sorted(receipt_folder(spec).glob('crowd-vat-apply-%s-*.json' % target))
    source = None
    for f in reversed(previous):
        data = json.loads(f.read_text(encoding='utf-8-sig'))
        if data.get('status', '').startswith('apply_saved') and 'before' in data:
            source = (f, data)
            break
    if not source:
        raise RuntimeError('No successful apply receipt for %s to revert to' % target)

    def wanted_fn(ue_, bake, before):
        rows = source[1]['before']
        return dict(properties=rows['properties'], poseMeshes=rows['poseMeshes'],
                    crowdMaterialOverride=rows['crowdMaterialOverride'],
                    overrides=[c['overrideMaterials'] for c in rows['components']],
                    revertSource=source[0].name, revertSourceSha256=sha(source[0]))
    return _pass(ue, spec, target, 'revert', wanted_fn)


def run_map_verify(ue, spec):
    stamp = stamp_now()
    out = receipt_folder(spec) / ('crowd-vat-mapverify-%s.json' % stamp)
    receipt = dict(status='starting', utc=utc(), maps={}, errors=[])
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    try:
        _, _, _, bake = verified_bake(spec)
        for target in spec['order']:
            MAP = spec['targets'][target]
            before = sha(disk_umap(MAP))
            if not levels.load_level(MAP) or editor.get_editor_world().get_outermost().get_name() != MAP:
                raise RuntimeError('load failed: ' + MAP)
            snap = _snapshot(ue, _find_field(ue, spec), spec)
            snap['poseMeshesResolvedOnDisk'] = _resolve_on_disk(ue, snap, spec.get('vatMaster') or bake['master']['path'])
            snap['mapSha256'] = before
            snap['mapUnchanged'] = sha(disk_umap(MAP)) == before
            receipt['maps'][target] = snap
        receipt['status'] = 'read_only_verify_complete'
    except Exception:
        receipt['status'] = 'failed'
        receipt['errors'].append(traceback.format_exc())
        raise
    finally:
        out.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')


def _main():
    try:
        import unreal as ue
    except ImportError:
        problems = offline_check()
        print(json.dumps(dict(offlineCheck='pass' if not problems else 'fail', problems=problems), indent=2))
        sys.exit(1 if problems else 0)
    spec = load_spec()
    line = ue.SystemLibrary.get_command_line()
    m = re.search(r'-CrowdVatTarget=(Candidate48|Main50)', line)
    target = m.group(1) if m else None
    try:
        problems = offline_check()
        if problems:
            raise RuntimeError('Offline check failed: %r' % problems)
        if '-CrowdVatApplyAll' in line:
            for key in spec['order']:
                run_apply(ue, spec, key)
        elif '-CrowdVatRevertAndReapply' in line:
            if not target:
                raise RuntimeError('Pass -CrowdVatTarget=')
            run_revert(ue, spec, target)
            run_apply(ue, spec, target)
        elif '-CrowdVatApply' in line:
            if not target:
                raise RuntimeError('Pass -CrowdVatTarget=')
            run_apply(ue, spec, target)
        elif '-CrowdVatRevert' in line:
            if not target:
                raise RuntimeError('Pass -CrowdVatTarget=')
            run_revert(ue, spec, target)
        elif '-CrowdVatMapVerify' in line:
            run_map_verify(ue, spec)
        else:
            raise RuntimeError('release_crowd_vat: nothing done; pass a mode')
    except Exception:
        failure = receipt_folder(spec) / ('crowd-vat-failure-%s.json' % stamp_now())
        failure.write_text(json.dumps(dict(status='failed_before_or_during_run', commandLine=line,
                                           error=traceback.format_exc()), indent=2), encoding='utf-8')
        raise


if __name__ == '__main__':
    _main()

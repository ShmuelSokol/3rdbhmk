"""Sanctuary interior finish V2 - Kodesh HaKodashim, Heikhal, Ulam.

Two native modes, both driven by Scripts/release_sanctuary_finish_v2.spec.json:

  -SanctuaryV2Inventory
      READ ONLY. Loads the target map, walks every StaticMeshComponent whose
      bounds fall inside the House volume, and records mesh, per-slot material,
      bounds and screen-relevant area, plus every light, post-process volume and
      the FX director's authored anchors. Saves nothing, dirties nothing.

  -SanctuaryV2Apply   [-SanctuaryV2ExpectedHash=<64hex>]
      Applies the reviewed instance parameters and component-slot overrides from
      the spec under the full guard pattern: process inventory, protected-hash of
      every other Content file before and after, checkpoint of the .umap and both
      One-File-Per-Actor trees into ReviewCheckpoints, apply, save, reopen,
      numeric readback of every changed value, receipt at every step.

  -SanctuaryV2Verify=<absolute apply receipt>
      Fresh process, reloads and re-reads every number the apply receipt claims.
      Saves nothing; refuses if the map bytes moved.

  -SanctuaryV2VerifyLoose=<absolute apply receipt>
      Same readback, but for a map that other passes have legitimately saved since.
      It does NOT require the map bytes to be the ones this pass wrote; it asserts
      that every value this pass applied is still present on the map as it stands,
      and records the current hash and any concurrent content changes as evidence
      rather than as a failure. Use only when the strict verify has been refused
      because another pass saved the same map.

  -SanctuaryV2Revert=<absolute apply receipt>
      Restores the checkpointed .umap and OFPA trees recorded in that receipt,
      after confirming their hashes still match what the checkpoint recorded.

  -SanctuaryV2Target=candidate|main   (default candidate)

WHAT THIS DOES NOT ESTABLISH
  Nothing here is visual acceptance. Every parameter is an authored proposal read
  back numerically. Roughness, tiling and light intensity are artistic choices; a
  human looking at a frame is the only acceptance test. A numeric pass on this
  script is evidence that the intended numbers persisted, not that the room looks
  right, and certainly not that it is "cinematic".

HARD PROHIBITIONS ENFORCED IN CODE
  - /Game/MikdashV3/Materials/PBR/M_PBR_Tiled (the shared master) is hashed with
    the protected set and any change fails the run.
  - The nine repaired PBR instances, M_Sanctuary_gold, both KeruvFriezeV2
    materials, the ParochesV15 artwork and the menorah materials are in the
    protected set: this pass creates NEW instances and re-points COMPONENT SLOTS,
    it never edits a shared material.
  - Any component currently carrying a KeruvFriezeV2 material is refused as an
    override target, because a previous pass flattened that relief and had to be
    reverted from a checkpoint.
"""

import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'Scripts' / 'release_sanctuary_finish_v2.spec.json'
RECEIPTS = ROOT / 'SourceAssets' / 'sanctuary-detail' / 'SanctuaryFinishV2'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
CHECKPOINT_PREFIX = 'SanctuaryFinishV2-'

MAPS = {
    'candidate': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'main': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}

# Materials that must never be edited, and never be replaced on a component slot.
FRIEZE = (
    '/Game/MikdashV3/MaterialReview/KeruvFriezeV2/Materials/M_KeruvFriezeV2',
    '/Game/MikdashV3/MaterialReview/KeruvFriezeV2/Materials/M_KeruvFriezeV2_Displaced',
)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def disk(package, ext='uasset'):
    if not package.startswith('/Game/'):
        raise RuntimeError('Non-project package: ' + package)
    return ROOT / 'Content' / (package.split('.')[0][6:] + '.' + ext)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec.get('specVersion') != 1:
        raise RuntimeError('Unexpected specVersion')
    if set(spec['targetMaps'].values()) != set(MAPS.values()):
        raise RuntimeError('Spec target maps differ from script')
    return spec


def protected_snapshot(map_file, owned=()):
    """Every Content file except the one map we may change and this pass's own new
    instances. `owned` exists because the instances are create-once: on a re-run they
    already exist on disk and re-saving them re-serialises the bytes, which would
    otherwise trip the protected-hash guard against assets this pass authored itself.
    Nothing outside the spec's newInstances list is ever excluded."""
    owned_paths = {str(Path(o)) for o in owned}
    return {str(p): sha(p) for p in (ROOT / 'Content').rglob('*')
            if p.is_file() and p != Path(map_file) and str(p) not in owned_paths}


def check_hashes(expected):
    return [p for p, h in expected.items() if not Path(p).is_file() or sha(p) != h]


def process_inventory():
    proc = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'],
                          capture_output=True, text=True, check=True, timeout=30)
    rows = list(csv.reader(io.StringIO(proc.stdout)))
    if not rows:
        raise RuntimeError('Malformed process inventory')
    others = [r[:2] for r in rows
              if len(r) >= 2 and r[0].lower() in ('unrealeditor.exe', 'unrealeditor-cmd.exe')
              and int(r[1]) != os.getpid()]
    if others:
        raise RuntimeError('Another editor is running: ' + repr(others))


def close(a, b, rel=1e-4):
    if a is None or b is None:
        return a == b
    return abs(float(a) - float(b)) <= rel * max(1.0, abs(float(b)))


def offline_check():
    spec = load_spec()
    problems = []
    for name, body in spec.get('newInstances', {}).items():
        if not body['package'].startswith('/Game/MikdashV3/'):
            problems.append('instance outside project namespace: ' + name)
        if body['parent'] in spec['protectedAssets']:
            pass  # parenting to a protected master is fine; editing it is not
        for k, v in body.get('scalars', {}).items():
            if not isinstance(v, (int, float)):
                problems.append('non-numeric scalar %s.%s' % (name, k))
    for entry in spec.get('componentOverrides', []):
        target = entry['material']
        if target.startswith('$new:') and target[5:] not in spec['newInstances']:
            problems.append('override names an undeclared instance: ' + target)
        if entry.get('expectedBefore') in FRIEZE:
            problems.append('override would replace a frieze material: ' + entry['meshAsset'])
    for light in spec.get('lights', []):
        if light['action'] == 'spawn' and not light['label'].startswith('RELEASE_SanctuaryV2_'):
            problems.append('spawned light outside this pass namespace: ' + light['label'])
        if light['action'] == 'edit' and light['label'] != light['targetLabel']:
            problems.append('an edit must not rename a light: ' + light['targetLabel'])
    print('offline check:', 'OK' if not problems else problems)
    return problems


# ---------------------------------------------------------------------------
# Native
# ---------------------------------------------------------------------------

def _vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def _path_of(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def inventory_run(target_key):
    """Read-only census of the House interior. Saves nothing."""
    import unreal as ue
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    spec = load_spec()
    target = MAPS[target_key]
    map_file = disk(target, 'umap')
    out = RECEIPTS / ('sanctuary-v2-inventory-%s-%s.json' % (target_key, stamp))
    report = {'status': 'started', 'stamp': stamp, 'target': target_key, 'map': target,
              'mapSha256Before': sha(map_file), 'errors': [],
              'scope': 'READ ONLY census. No visual acceptance is claimed.'}

    def write():
        out.write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    try:
        process_inventory()
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        if editor.get_game_world():
            raise RuntimeError('A game world is running')
        if not levels.load_level(target):
            raise RuntimeError('Load failed: ' + target)
        if editor.get_editor_world().get_outermost().get_name() != target:
            raise RuntimeError('Wrong world loaded')

        box = spec['houseVolume'][target_key]
        lo, hi = box['minCm'], box['maxCm']

        def inside(origin):
            return all(lo[i] <= origin[i] <= hi[i] for i in range(3))

        rows = []
        by_material = {}
        scanned = 0
        bounds_failures = []
        seen_x = []
        all_actors = list(actors.get_all_level_actors())
        for a in all_actors:
            try:
                comps = a.get_components_by_class(ue.StaticMeshComponent)
            except Exception:
                continue
            for c in comps:
                mesh = c.get_editor_property('static_mesh')
                if mesh is None:
                    continue
                scanned += 1
                origin = extent = None
                try:
                    lo_b, hi_b = c.get_local_bounds()
                    xf = c.get_world_transform()
                    corners = []
                    for cx in (lo_b.x, hi_b.x):
                        for cy in (lo_b.y, hi_b.y):
                            for cz in (lo_b.z, hi_b.z):
                                w = xf.transform_location(ue.Vector(cx, cy, cz))
                                corners.append([w.x, w.y, w.z])
                    mn = [min(p[i] for p in corners) for i in range(3)]
                    mx = [max(p[i] for p in corners) for i in range(3)]
                    origin = [(mn[i] + mx[i]) * 0.5 for i in range(3)]
                    extent = [(mx[i] - mn[i]) * 0.5 for i in range(3)]
                except Exception as exc:
                    if len(bounds_failures) < 5:
                        bounds_failures.append(repr(exc))
                    try:
                        w = c.get_world_location()
                        origin = [w.x, w.y, w.z]
                        extent = [0.0, 0.0, 0.0]
                    except Exception:
                        continue
                if len(seen_x) < 40000:
                    seen_x.append(round(origin[0], 0))
                if not inside(origin):
                    continue
                slots = []
                for s in range(c.get_num_materials()):
                    m = c.get_material(s)
                    p = _path_of(m)
                    slots.append(p)
                    face = 8.0 * (extent[0] * extent[1] + extent[1] * extent[2] + extent[0] * extent[2])
                    agg = by_material.setdefault(p, {'slots': 0, 'aabbFaceCm2': 0.0, 'meshes': {}})
                    agg['slots'] += 1
                    agg['aabbFaceCm2'] += face
                    agg['meshes'][_path_of(mesh)] = agg['meshes'].get(_path_of(mesh), 0) + 1
                rows.append({'actor': a.get_actor_label(), 'actorName': a.get_name(),
                             'component': c.get_name(), 'mesh': _path_of(mesh),
                             'originCm': [round(v, 1) for v in origin],
                             'extentCm': [round(v, 1) for v in extent],
                             'materials': slots,
                             'nanite': bool(mesh.get_editor_property('nanite_settings').enabled)
                             if hasattr(mesh, 'get_editor_property') else None})
        report['componentCount'] = len(rows)
        report['componentsScanned'] = scanned
        report['boundsFailures'] = bounds_failures
        if seen_x:
            xs = sorted(seen_x)
            report['worldXQuantiles'] = {q: xs[min(len(xs) - 1, int(len(xs) * q / 100.0))]
                                         for q in (0, 1, 5, 25, 50, 75, 95, 99, 100)}
            report['worldXBelowMinus2000'] = sum(1 for v in xs if v < -2000)
        report['components'] = rows
        for v in by_material.values():
            v['aabbFaceCm2'] = round(v['aabbFaceCm2'], 0)
        report['byMaterial'] = dict(sorted(by_material.items(),
                                           key=lambda kv: -kv[1]['aabbFaceCm2']))

        # Lights and post-process, whole map (there are only a handful).
        lights = []
        for a in all_actors:
            comps = []
            try:
                comps = list(a.get_components_by_class(ue.LightComponent))
            except Exception:
                comps = []
            if not comps:
                continue
            lc = comps[0]
            row = {'class': a.get_class().get_name(), 'label': a.get_actor_label(),
                   'componentClass': lc.get_class().get_name(),
                   'locationCm': _vec(a.get_actor_location()),
                   'rotation': [a.get_actor_rotation().pitch, a.get_actor_rotation().yaw,
                                a.get_actor_rotation().roll]}
            for prop in ('intensity', 'attenuation_radius', 'source_radius', 'light_color',
                         'temperature', 'use_temperature', 'cast_shadows',
                         'volumetric_scattering_intensity', 'indirect_lighting_intensity',
                         'specular_scale', 'intensity_units'):
                try:
                    row[prop] = str(lc.get_editor_property(prop))
                except Exception:
                    pass
            lights.append(row)
        report['lights'] = lights

        pps = []
        for a in all_actors:
            if isinstance(a, ue.PostProcessVolume):
                pps.append({'label': a.get_actor_label(),
                            'unbound': bool(a.get_editor_property('unbound')),
                            'priority': float(a.get_editor_property('priority'))})
        report['postProcessVolumes'] = pps

        fx = [a for a in all_actors if a.get_class().get_name() == 'MikdashFXDirector']
        report['fxDirectors'] = []
        for a in fx:
            row = {'label': a.get_actor_label(), 'locationCm': _vec(a.get_actor_location())}
            for prop in ('lamp_flame_cm', 'lamp_light_cm', 'shaft_transforms', 'heat_haze_cm',
                         'effects_quality', 'heat_haze_strength', 'full_detail_cm', 'cutoff_cm',
                         'flame_lamp_material', 'light_shaft_material', 'dust_mote_material',
                         'card_mesh', 'heikhal_ceiling_z_cm'):
                try:
                    v = a.get_editor_property(prop)
                    if hasattr(v, 'get_path_name'):
                        row[prop] = v.get_path_name()
                    elif isinstance(v, (list, ue.Array)):
                        row[prop] = [(_vec(x) if hasattr(x, 'x') else str(x)) for x in v]
                    else:
                        row[prop] = v if isinstance(v, (int, float, bool)) else str(v)
                except Exception as exc:
                    row[prop] = 'unavailable: %r' % (exc,)
            report['fxDirectors'].append(row)

        # Parameters of every material the House uses that we might parent from.
        params = {}
        for path in list(report['byMaterial']) + spec.get('inspectMaterials', []):
            if not path or path in params:
                continue
            asset = ue.load_asset(path)
            if asset is None:
                params[path] = {'load': 'failed'}
                continue
            try:
                on_disk = disk(path)
                disk_sha = sha(on_disk) if Path(on_disk).is_file() else None
            except Exception:
                disk_sha = None
            row = {'class': asset.get_class().get_name(), 'diskSha256': disk_sha}
            try:
                row['parent'] = _path_of(asset.get_editor_property('parent'))
            except Exception:
                row['parent'] = None
            for prop, key in (('base_color', 'baseColorConst'), ('roughness', 'roughnessConst'),
                              ('metallic', 'metallicConst')):
                try:
                    row[key] = str(asset.get_editor_property(prop))
                except Exception:
                    pass
            try:
                lib = ue.MaterialEditingLibrary
                names = [str(n) for n in lib.get_scalar_parameter_names(asset)]
                row['scalars'] = {n: float(lib.get_material_instance_scalar_parameter_value(asset, n))
                                  if row['class'].startswith('MaterialInstance')
                                  else None for n in names}
                vnames = [str(n) for n in lib.get_vector_parameter_names(asset)]
                row['vectors'] = {}
                for n in vnames:
                    try:
                        v = lib.get_material_instance_vector_parameter_value(asset, n)
                        row['vectors'][n] = [v.r, v.g, v.b, v.a]
                    except Exception:
                        row['vectors'][n] = None
                tnames = [str(n) for n in lib.get_texture_parameter_names(asset)]
                row['textures'] = {}
                for n in tnames:
                    try:
                        t = lib.get_material_instance_texture_parameter_value(asset, n)
                        row['textures'][n] = _path_of(t)
                    except Exception:
                        row['textures'][n] = None
            except Exception as exc:
                row['parameterProbe'] = 'unavailable: %r' % (exc,)
            params[path] = row
        report['materials'] = params

        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
                ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            report['errors'].append('Inventory left dirty packages (unexpected for a read)')
        report['status'] = 'inventory_complete'
    except Exception as exc:
        report['status'] = 'failed'
        report['errors'].append(repr(exc))
        raise
    finally:
        report['mapSha256After'] = sha(map_file)
        report['mapBytesUnchanged'] = report['mapSha256After'] == report['mapSha256Before']
        if not report['mapBytesUnchanged']:
            report['status'] = 'failed_preservation'
        write()
        print('RECEIPT ' + str(out))
    return report



# ---------------------------------------------------------------------------
# Apply / verify / revert
# ---------------------------------------------------------------------------

SCALARS = ('TilingCm', 'NormalStrength', 'RoughnessScale', 'Metallic', 'AlbedoFlatness')
TEXTURES = ('Albedo', 'Normal', 'ARM')
LIGHT_PROPS = ('intensity', 'attenuation_radius', 'source_radius', 'temperature',
               'use_temperature', 'cast_shadows', 'specular_scale',
               'volumetric_scattering_intensity', 'indirect_lighting_intensity')


def _light_component(ue, actor):
    comps = list(actor.get_components_by_class(ue.LightComponent))
    if len(comps) != 1:
        raise RuntimeError('Expected exactly one light component on ' + actor.get_actor_label())
    return comps[0]


def _read_light(ue, actor):
    lc = _light_component(ue, actor)
    row = {'label': actor.get_actor_label(),
           'componentClass': lc.get_class().get_name(),
           'locationCm': _vec(actor.get_actor_location()),
           'mobility': str(lc.get_editor_property('mobility'))}
    for prop in LIGHT_PROPS:
        try:
            v = lc.get_editor_property(prop)
            if isinstance(v, bool):
                row[prop] = bool(v)
            elif isinstance(v, (int, float)):
                row[prop] = float(v)
            else:
                row[prop] = str(v)
        except Exception:
            pass
    try:
        c = lc.get_editor_property('light_color')
        row['light_color'] = [int(c.r), int(c.g), int(c.b), int(c.a)]
    except Exception:
        pass
    try:
        row['intensity_units'] = str(lc.get_editor_property('intensity_units'))
    except Exception:
        pass
    return row


def _read_instance(ue, inst):
    lib = ue.MaterialEditingLibrary
    row = {'path': _path_of(inst), 'parent': _path_of(inst.get_editor_property('parent')),
           'scalars': {}, 'textures': {}}
    for n in SCALARS:
        row['scalars'][n] = float(lib.get_material_instance_scalar_parameter_value(inst, n))
    v = lib.get_material_instance_vector_parameter_value(inst, 'Tint')
    row['Tint'] = [float(v.r), float(v.g), float(v.b), float(v.a)]
    for n in TEXTURES:
        row['textures'][n] = _path_of(lib.get_material_instance_texture_parameter_value(inst, n))
    return row


def _ensure_instance(ue, name, body, report):
    """Create-once. Never overwrites an existing asset; parameters are set then read back,
    because the 5.8 MaterialEditingLibrary setters return False whether or not they worked."""
    lib = ue.MaterialEditingLibrary
    package = body['package']
    existing = ue.load_asset(package)
    created = False
    if existing is None:
        tools = ue.AssetToolsHelpers.get_asset_tools()
        folder, leaf = package.rsplit('/', 1)
        existing = tools.create_asset(leaf, folder, ue.MaterialInstanceConstant,
                                      ue.MaterialInstanceConstantFactoryNew())
        if existing is None:
            raise RuntimeError('create_asset returned None for ' + package)
        created = True
    parent = ue.load_asset(body['parent'])
    if parent is None:
        raise RuntimeError('Parent material missing: ' + body['parent'])
    lib.set_material_instance_parent(existing, parent)
    source = ue.load_asset(body['copyTexturesFrom'])
    if source is None:
        raise RuntimeError('Texture source instance missing: ' + body['copyTexturesFrom'])
    for n in TEXTURES:
        tex = lib.get_material_instance_texture_parameter_value(source, n)
        if tex is None:
            raise RuntimeError('Texture parameter %s unset on %s' % (n, body['copyTexturesFrom']))
        lib.set_material_instance_texture_parameter_value(existing, n, tex)
    for n in SCALARS:
        lib.set_material_instance_scalar_parameter_value(existing, n, float(body['scalars'][n]))
    t = body['tint']
    lib.set_material_instance_vector_parameter_value(existing, 'Tint',
                                                     ue.LinearColor(t[0], t[1], t[2], t[3]))
    ue.EditorAssetLibrary.save_loaded_asset(existing, False)
    read = _read_instance(ue, existing)
    if read['parent'] != body['parent']:
        raise RuntimeError('Parent readback mismatch on ' + package)
    for n in SCALARS:
        if not close(read['scalars'][n], body['scalars'][n]):
            raise RuntimeError('Scalar readback mismatch %s.%s: %r != %r'
                               % (package, n, read['scalars'][n], body['scalars'][n]))
    for i in range(4):
        if not close(read['Tint'][i], t[i]):
            raise RuntimeError('Tint readback mismatch on ' + package)
    for n in TEXTURES:
        if read['textures'][n] is None:
            raise RuntimeError('Texture %s did not persist on %s' % (n, package))
    report.setdefault('instances', {})[name] = dict(read, created=created,
                                                    diskSha256=sha(disk(package)))
    return existing


def _find_override_targets(ue, actors, spec):
    """Resolve each spec override to exactly the components the spec says exist."""
    found = []
    all_actors = list(actors.get_all_level_actors())
    for entry in spec['componentOverrides']:
        matches = []
        for a in all_actors:
            try:
                comps = a.get_components_by_class(ue.StaticMeshComponent)
            except Exception:
                continue
            for c in comps:
                mesh = c.get_editor_property('static_mesh')
                if mesh is None or _path_of(mesh) != entry['meshAsset']:
                    continue
                if 'actorLabel' in entry and a.get_actor_label() != entry['actorLabel']:
                    continue
                matches.append((a, c))
        expected_count = int(entry.get('expectCount', 1))
        if len(matches) != expected_count:
            raise RuntimeError('Override %s matched %d components, spec says %d'
                               % (entry['meshAsset'], len(matches), expected_count))
        target = entry['material']
        if target.startswith('$new:'):
            target = spec['newInstances'][target[5:]]['package']
        mat = ue.load_asset(target)
        if mat is None:
            raise RuntimeError('Override material not loadable: ' + target)
        for a, c in matches:
            slot = int(entry['slot'])
            if slot >= c.get_num_materials():
                raise RuntimeError('Slot %d out of range on %s' % (slot, a.get_actor_label()))
            current = _path_of(c.get_material(slot))
            if current in FRIEZE:
                raise RuntimeError('Refusing to replace a frieze material on '
                                   + a.get_actor_label())
            found.append({'actor': a, 'component': c, 'slot': slot, 'entry': entry,
                          'material': mat, 'materialPath': target, 'before': current})
    return found


def _lights_for(spec, target_key):
    """Light entries that apply to this map. candidateOnly / mainOnly scope them."""
    out = []
    for entry in spec['lights']:
        if entry.get('candidateOnly') and target_key != 'candidate':
            continue
        if entry.get('mainOnly') and target_key != 'main':
            continue
        out.append(entry)
    return out


def _fx_directors(ue, actors):
    return [a for a in actors.get_all_level_actors()
            if a.get_class().get_name() == 'MikdashFXDirector']


def _read_fx(ue, actor, props):
    row = {'label': actor.get_actor_label()}
    for name in props:
        v = actor.get_editor_property(name)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            row[name] = float(v)
        else:
            row[name] = [_vec(x) for x in v]
    return row


def _rescale_candidate(value):
    """0.96 about the fixed architecture origin [-6200,0,0]: x'=0.96x-248, y'=0.96y, z'=0.96z."""
    if isinstance(value, (int, float)):
        return 0.96 * float(value)
    return [0.96 * value[0] - 248.0, 0.96 * value[1], 0.96 * value[2]]


def _light_index(ue, actors):
    index = {}
    for a in actors.get_all_level_actors():
        try:
            if a.get_components_by_class(ue.LightComponent):
                index.setdefault(a.get_actor_label(), []).append(a)
        except Exception:
            pass
    return index


def apply_run(target_key, expected_hash=None, verify_receipt=None, loose=False):
    import unreal as ue
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    spec = load_spec()
    target = MAPS[target_key]
    map_file = disk(target, 'umap')
    mode = 'verify' if verify_receipt else 'apply'
    out = RECEIPTS / ('sanctuary-v2-%s-%s-%s.json' % (mode, target_key, stamp))
    before = sha(map_file)
    report = {'status': 'started', 'stamp': stamp, 'mode': mode, 'target': target_key,
              'map': target, 'processId': os.getpid(), 'mapSha256Before': before,
              'mapSaved': False, 'errors': [], 'specSha256': sha(SPEC_PATH),
              'scope': 'Numeric persistence only. Nothing here is visual acceptance, and no '
                       'claim of cinematic quality follows from a parameter change.'}
    protected = {}

    def write():
        out.write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    try:
        process_inventory()
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)

        def clean():
            if editor.get_game_world():
                raise RuntimeError('A game world is running')
            if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
                    ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('Dirty packages present')

        if verify_receipt:
            earlier = json.loads(Path(verify_receipt).read_text(encoding='utf-8-sig'))
            if earlier.get('status') != 'applied_saved_reopened' or earlier.get('map') != target:
                raise RuntimeError('Verify source is not a completed apply for this map')
            if earlier.get('processId') == os.getpid():
                raise RuntimeError('Verification must run in a fresh process')
            if earlier.get('specSha256') != report['specSha256']:
                raise RuntimeError('Spec changed since the apply')
            expected_hash = earlier['mapSha256After']
            report['appliedMapSha256'] = expected_hash
        if loose:
            # The map is shared with other passes. A loose verify does not require the
            # bytes to be the ones this pass wrote; it re-reads every value this pass
            # applied and asserts each one on the map AS IT STANDS NOW. It still writes
            # nothing, and it still fails if any of this pass's values has been undone.
            report['looseVerify'] = True
            report['mapMovedSinceApply'] = before.lower() != (expected_hash or '').lower()
        else:
            if not expected_hash:
                raise RuntimeError('An explicit -SanctuaryV2ExpectedHash is required')
            if before.lower() != expected_hash.lower():
                raise RuntimeError('Map hash is not the reviewed one: %s != %s'
                                   % (before, expected_hash))

        clean()
        owned = [disk(body['package']) for body in spec['newInstances'].values()]
        protected = protected_snapshot(map_file, owned)
        report['protectedFileCount'] = len(protected)
        report['ownedInstanceFiles'] = [str(o) for o in owned]
        for path in spec['protectedAssets']:
            if str(disk(path)) not in protected:
                raise RuntimeError('Protected asset not on disk: ' + path)
        if not levels.load_level(target):
            raise RuntimeError('Load failed: ' + target)
        clean()
        if editor.get_editor_world().get_outermost().get_name() != target:
            raise RuntimeError('Wrong world loaded')

        report['instances'] = {}
        if mode == 'apply':
            for name, body in spec['newInstances'].items():
                _ensure_instance(ue, name, body, report)
        else:
            for name, body in spec['newInstances'].items():
                inst = ue.load_asset(body['package'])
                if inst is None:
                    raise RuntimeError('Instance missing at verify: ' + body['package'])
                read = _read_instance(ue, inst)
                for n in SCALARS:
                    if not close(read['scalars'][n], body['scalars'][n]):
                        raise RuntimeError('Verify scalar mismatch %s.%s' % (name, n))
                report['instances'][name] = dict(read, diskSha256=sha(disk(body['package'])))
        write()

        found = _find_override_targets(ue, actors, spec)
        report['componentOverrides'] = [
            {'actor': f['actor'].get_actor_label(), 'component': f['component'].get_name(),
             'mesh': f['entry']['meshAsset'], 'slot': f['slot'],
             'before': f['before'], 'after': f['materialPath']} for f in found]

        light_actors = _light_index(ue, actors)
        report['lightsBefore'] = [_read_light(ue, a)
                                  for lst in light_actors.values() for a in lst]
        light_entries = _lights_for(spec, target_key)
        report['lightEntriesInScope'] = [e['label'] for e in light_entries]

        fx_targets = spec['fxAnchors'][target_key].get('absolute') or {}
        fx_props = list(fx_targets)
        fx_actors = _fx_directors(ue, actors)
        if fx_props and len(fx_actors) != 1:
            raise RuntimeError('Expected exactly one FX director, found %d' % len(fx_actors))
        report['fxBefore'] = [_read_fx(ue, a, fx_props) for a in fx_actors] if fx_props else []

        if mode == 'apply':
            already = []
            for f in found:
                if f['before'] == f['materialPath']:
                    already.append(f['actor'].get_actor_label())
                    continue
                if f['before'] != f['entry']['expectedBefore']:
                    raise RuntimeError('Unexpected before material on %s: %s (spec says %s)'
                                       % (f['actor'].get_actor_label(), f['before'],
                                          f['entry']['expectedBefore']))
            report['slotsAlreadyPointed'] = already
            checkpoint = CHECKPOINT_ROOT / (CHECKPOINT_PREFIX + target_key + '-' + stamp)
            checkpoint.mkdir(parents=True, exist_ok=False)
            shutil.copy2(map_file, checkpoint / map_file.name)
            if sha(checkpoint / map_file.name) != before:
                raise RuntimeError('Checkpoint copy hash mismatch')
            for tree in ('__ExternalActors__', '__ExternalObjects__'):
                folder = ROOT / 'Content' / tree / target[6:]
                if folder.exists():
                    shutil.copytree(folder, checkpoint / tree / target[6:])
            report['checkpoint'] = str(checkpoint)
            write()

            for f in found:
                f['actor'].modify(True)
                f['component'].modify(True)
                f['component'].set_material(f['slot'], f['material'])

            applied_lights = []
            for entry in light_entries:
                label = entry['label']
                if entry['action'] == 'edit':
                    matches = light_actors.get(entry['targetLabel'], [])
                    if len(matches) != 1:
                        raise RuntimeError('Light to edit not unique: ' + entry['targetLabel'])
                    a = matches[0]
                    lc = _light_component(ue, a)
                    a.modify(True)
                    lc.modify(True)
                    for prop, value in entry['properties'].items():
                        lc.set_editor_property(prop, value)
                    a.set_actor_label(label)
                    applied_lights.append(label)
                elif entry['action'] == 'spawn':
                    existing = light_actors.get(label, [])
                    if len(existing) > 1:
                        raise RuntimeError('More than one light already carries the label: ' + label)
                    if existing:
                        # Re-running this pass retunes the light it placed; it never
                        # places a second one.
                        a = existing[0]
                        a.modify(True)
                        if a.get_class().get_name() != entry['class']:
                            raise RuntimeError('Existing light has the wrong class: ' + label)
                    else:
                        loc = ue.Vector(*entry['locationCm'])
                        cls = getattr(ue, entry['class'])
                        a = actors.spawn_actor_from_class(cls, loc, ue.Rotator(0.0, 0.0, 0.0))
                        if a is None:
                            raise RuntimeError('spawn_actor_from_class returned None for ' + label)
                        a.set_actor_label(label)
                    lc = _light_component(ue, a)
                    lc.modify(True)
                    lc.set_editor_property('mobility', ue.ComponentMobility.MOVABLE)
                    for prop, value in entry['properties'].items():
                        lc.set_editor_property(prop, value)
                    if 'lightColor' in entry:
                        c = entry['lightColor']
                        lc.set_light_color(ue.LinearColor(c[0], c[1], c[2], 1.0))
                    applied_lights.append(label)
                else:
                    raise RuntimeError('Unknown light action: ' + entry['action'])
            report['lightsApplied'] = applied_lights

            fx_applied = {}
            if fx_props:
                # ABSOLUTE targets, never a transform of the live value: applying a
                # rescale to whatever is stored is not idempotent and did in fact
                # double-scale these anchors on a second run.
                fx = fx_actors[0]
                fx.modify(True)
                for name, want in fx_targets.items():
                    current = fx.get_editor_property(name)
                    if isinstance(want, (int, float)):
                        before_value = float(current)
                        fx.set_editor_property(name, float(want))
                    else:
                        before_value = [_vec(v) for v in current]
                        if len(before_value) != len(want):
                            raise RuntimeError('FX anchor %s has %d entries, spec has %d'
                                               % (name, len(before_value), len(want)))
                        fx.set_editor_property(name, [ue.Vector(*v) for v in want])
                    fx_applied[name] = {'before': before_value, 'after': want}
            report['fxApplied'] = fx_applied

            changed = check_hashes(protected)
            if changed:
                report['protectedDifferences'] = changed
                raise RuntimeError('Protected content changed during apply: %r' % (changed[:5],))
            if not levels.save_current_level():
                raise RuntimeError('save_current_level refused')
            report['mapSaved'] = True
            report['mapSha256After'] = sha(map_file)
            write()
            if not levels.load_level(target):
                raise RuntimeError('Reopen failed')

        found = _find_override_targets(ue, actors, spec)
        for f in found:
            if _path_of(f['component'].get_material(f['slot'])) != f['materialPath']:
                raise RuntimeError('Component slot readback mismatch on '
                                   + f['actor'].get_actor_label())
        after_lights = _light_index(ue, actors)
        report['lightsAfter'] = [_read_light(ue, a)
                                 for lst in after_lights.values() for a in lst]
        for entry in _lights_for(spec, target_key):
            matches = after_lights.get(entry['label'], [])
            if len(matches) != 1:
                raise RuntimeError('Light not uniquely present after readback: ' + entry['label'])
            lc = _light_component(ue, matches[0])
            for prop, value in entry['properties'].items():
                got = lc.get_editor_property(prop)
                if isinstance(value, bool):
                    ok = bool(got) == value
                elif isinstance(value, (int, float)):
                    ok = close(float(got), float(value))
                else:
                    ok = str(got) == str(value)
                if not ok:
                    raise RuntimeError('Light readback mismatch %s.%s: %r != %r'
                                       % (entry['label'], prop, got, value))
        fx_targets = spec['fxAnchors'][target_key].get('absolute') or {}
        fx_props = list(fx_targets)
        if fx_props:
            fx_actors = _fx_directors(ue, actors)
            if len(fx_actors) != 1:
                raise RuntimeError('FX director missing after reopen')
            report['fxAfter'] = [_read_fx(ue, fx_actors[0], fx_props)]
            for name, want in fx_targets.items():
                got = report['fxAfter'][0][name]
                if isinstance(want, (int, float)):
                    ok = close(got, want)
                else:
                    ok = (len(got) == len(want)
                          and all(close(got[i][j], want[i][j])
                                  for i in range(len(want)) for j in range(3)))
                if not ok:
                    raise RuntimeError('FX anchor readback mismatch on ' + name)
        if mode == 'apply':
            report['status'] = 'applied_saved_reopened'
        else:
            report['status'] = 'fresh_verified_loose' if loose else 'fresh_verified'
    except Exception as exc:
        report['status'] = 'failed'
        report['errors'].append(repr(exc))
        raise
    finally:
        report['mapSha256After'] = sha(map_file)
        report['mapBytesChanged'] = report['mapSha256After'] != before
        report['protectedDifferences'] = check_hashes(protected) if protected else []
        if report['protectedDifferences'] and not loose:
            report['status'] = 'failed_preservation'
        if mode == 'verify' and report['mapBytesChanged']:
            report['status'] = 'failed_preservation'
        write()
        print('RECEIPT ' + str(out))
    return report


def revert_run(receipt_path):
    """Restore the checkpointed map recorded by an apply receipt."""
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    earlier = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
    target = earlier['map']
    map_file = disk(target, 'umap')
    out = RECEIPTS / ('sanctuary-v2-revert-%s.json' % stamp)
    report = {'status': 'started', 'stamp': stamp, 'source': str(receipt_path),
              'map': target, 'mapSha256Before': sha(map_file), 'errors': []}

    def write():
        out.write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')
    write()
    try:
        process_inventory()
        checkpoint = Path(earlier['checkpoint'])
        saved = checkpoint / map_file.name
        if not saved.is_file():
            raise RuntimeError('Checkpoint map missing: ' + str(saved))
        if sha(saved) != earlier['mapSha256Before']:
            raise RuntimeError('Checkpoint no longer matches the pre-apply hash')
        shutil.copy2(saved, map_file)
        for tree in ('__ExternalActors__', '__ExternalObjects__'):
            src = checkpoint / tree / target[6:]
            if src.exists():
                dst = ROOT / 'Content' / tree / target[6:]
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
        report['mapSha256After'] = sha(map_file)
        if report['mapSha256After'] != earlier['mapSha256Before']:
            raise RuntimeError('Restored map hash does not match the checkpoint')
        report['status'] = 'reverted'
    except Exception as exc:
        report['status'] = 'failed'
        report['errors'].append(repr(exc))
        raise
    finally:
        write()
        print('RECEIPT ' + str(out))
    return report


if __name__ == '__main__':
    try:
        import unreal as ue
    except ImportError:
        raise SystemExit(0 if not offline_check() else 1)
    cmd = ue.SystemLibrary.get_command_line()
    args = {t.split('=', 1)[0].lower(): t.split('=', 1)[1].strip('"')
            for t in cmd.split() if '=' in t}
    target_key = args.get('-sanctuaryv2target', 'candidate')
    if target_key not in MAPS:
        raise SystemExit('Unknown -SanctuaryV2Target')
    try:
        low_cmd = cmd.lower()
        if '-sanctuaryv2inventory' in low_cmd:
            inventory_run(target_key)
        elif '-sanctuaryv2verifyloose' in low_cmd:
            apply_run(target_key, verify_receipt=args['-sanctuaryv2verifyloose'], loose=True)
        elif '-sanctuaryv2verify' in low_cmd:
            apply_run(target_key, verify_receipt=args['-sanctuaryv2verify'])
        elif '-sanctuaryv2revert' in low_cmd:
            revert_run(args['-sanctuaryv2revert'])
        elif '-sanctuaryv2apply' in low_cmd:
            apply_run(target_key, expected_hash=args.get('-sanctuaryv2expectedhash'))
        else:
            print('No SanctuaryV2 mode switch given; nothing done.')
    finally:
        low = cmd.lower()
        if '-executepythonscript' in low and '-run=pythonscript' not in low:
            ue.SystemLibrary.quit_editor()

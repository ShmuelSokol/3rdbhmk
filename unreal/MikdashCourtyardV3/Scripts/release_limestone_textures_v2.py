"""Limestone V2: import the authored meleke ashlar set and swap it onto the walls, reversibly (commandlet-safe).

Consumes Scripts/release_limestone_textures_v2.spec.json and the offline manifest written by
Scripts/create_limestone_textures_v2.py. Four modes, parsed from the engine command line:

  -LimestoneV2Import                  import the six PNGs (Albedo / Normal / ARM x Ashlar / Trim) into
                                      /Game/MikdashV3/MaterialReview/LimestoneV2/Textures/, create the NEW
                                      instances MI_LimestoneV2_Ashlar / MI_LimestoneV2_Trim parented on the
                                      EXISTING MI_PBR_LimestoneAshlar / MI_PBR_LimestoneTrim, set every
                                      parameter explicitly, set the Nanite usage override, save, reload, read
                                      back                                     -> limestone-v2-import-<stamp>.json
  -LimestoneV2Apply=<import receipt>  load the main map, plan every StaticMeshComponent slot whose EFFECTIVE
                                      material is one of the two old instances (expected 1155 + 335), checkpoint
                                      the map, set the per-component override_materials slot to the new
                                      instance, read back, save, reopen, read back  -> limestone-v2-apply-<stamp>.json
  -LimestoneV2Verify=<apply receipt>  fresh-process readback only, no save          -> limestone-v2-verify-<stamp>.json
  -LimestoneV2Revert=<apply receipt>  restore the checkpointed map bytes (or the recorded per-slot
                                      before-values if the map has moved on), reopen, read back
                                                                                     -> limestone-v2-revert-<stamp>.json
  -LimestoneV2AllowCountDrift         accept slot counts that differ from spec expectedSlotCount (default refuses)

Never touched: M_PBR_Tiled, the ten MI_PBR_* instances, every other protected asset/map (hashed before
and after every mode; a mismatch fails the run). MaterialEditingLibrary setters return False even on
success in 5.8, so every set is verified by readback. The receipt is written at start, after each stage
and in finally, so partial state is preserved for resume; a save returning False raises.

Commandlet (strictly serial; check Get-Process UnrealEditor,UnrealEditor-Cmd first; unique -abslog):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe" "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript -unattended -nullrhi -abslog="C:/Mikdash/Working-5.8/LimestoneV2-Import-01.log"
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_limestone_textures_v2.py" -LimestoneV2Import
Offline:  python Scripts/release_limestone_textures_v2.py   -> offline_check(): spec/manifest/PNG sanity and the planned table.
"""
import glob
import hashlib
import json
import re
import shutil
import struct
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_limestone_textures_v2.spec.json'
KINDS = ('Albedo', 'Normal', 'ARM')
SCALARS = ('TilingCm', 'NormalStrength', 'RoughnessScale', 'Metallic', 'AlbedoFlatness')


def load_spec():
    return json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk(asset, ext='uasset'):
    assert asset.startswith('/Game/') and '.' not in asset, asset
    return ROOT / 'Content' / (asset[6:] + '.' + ext)


def asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def close(a, b, tol=1e-4):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol * max(1.0, abs(a), abs(b))
    return a == b


def png_size(path):
    head = Path(path).read_bytes()[:33]
    if head[:8] != b'\x89PNG\r\n\x1a\n' or head[12:16] != b'IHDR':
        raise RuntimeError('Not a PNG: %s' % path)
    w, h, depth, colour = struct.unpack('!2I2B', head[16:26])
    return w, h, depth, colour


def source_files(spec, manifest=None):
    """{variant: {kind: {'path': Path, 'sha256': str, 'size': [w, h]}}} from the offline manifest, verified on disk."""
    manifest = manifest or json.loads((ROOT / spec['sourceManifest']).read_text(encoding='utf-8-sig'))
    if manifest.get('status') != spec['sourceManifestStatusRequired']:
        raise RuntimeError('Source manifest status %r, need %r' % (manifest.get('status'), spec['sourceManifestStatusRequired']))
    if int(manifest.get('size', 0)) != int(spec['requiredSize']) or float(manifest.get('tileCm', 0)) != 300.0:
        raise RuntimeError('Source manifest size/tile differ from the spec (size %s, tile %s)' % (manifest.get('size'), manifest.get('tileCm')))
    out = {}
    for variant, cfg in spec['variants'].items():
        record = manifest['variants'].get(variant)
        if not record:
            raise RuntimeError('Manifest lacks variant ' + variant)
        out[variant] = {}
        for kind in KINDS:
            entry = record['files'][kind]
            path = ROOT / entry['path']
            if path.name != cfg['sourcePrefix'] + kind + '.png':
                raise RuntimeError('Unexpected source file name %s for %s/%s' % (path.name, variant, kind))
            if not path.exists():
                raise RuntimeError('Missing source PNG ' + str(path))
            digest = sha(path)
            if digest != entry['sha256']:
                raise RuntimeError('Source PNG hash differs from manifest: ' + str(path))
            w, h, depth, colour = png_size(path)
            if (w, h, depth, colour) != (spec['requiredSize'], spec['requiredSize'], 8, 2):
                raise RuntimeError('Source PNG %s is %dx%d depth %d colour %d' % (path.name, w, h, depth, colour))
            out[variant][kind] = {'path': path, 'sha256': digest, 'size': [w, h]}
    return out


def protected_paths(spec):
    paths = {disk(a) for a in spec['protectedAssets']}
    paths |= {disk(m, 'umap') for m in spec['protectedMaps']}
    for pattern in spec.get('protectedGlobs', []):
        paths |= {Path(p) for p in glob.glob(str(ROOT / pattern), recursive=True)}
    return sorted(paths)


def protected_hashes(spec):
    return {str(p.relative_to(ROOT)): sha(p) for p in protected_paths(spec) if p.exists()}


def offline_check(spec=None):
    spec = spec or load_spec()
    problems = []
    try:
        files = source_files(spec)
        sources = {v: {k: {'path': str(e['path'].relative_to(ROOT)), 'sha256': e['sha256'], 'size': e['size']} for k, e in kinds.items()} for v, kinds in files.items()}
    except Exception as exc:  # noqa: BLE001
        problems.append('source set: ' + str(exc))
        sources = {}
    for variant, cfg in spec['variants'].items():
        if not disk(cfg['parentInstance']).exists():
            problems.append('missing parent instance ' + cfg['parentInstance'])
        if disk(cfg['newInstance']).exists():
            problems.append('new instance already exists on disk (fresh namespace expected): ' + cfg['newInstance'])
        if set(cfg['scalars']) != set(SCALARS):
            problems.append('variant %s must set exactly %s' % (variant, SCALARS))
    for asset in spec['protectedAssets']:
        if not disk(asset).exists():
            problems.append('missing protected asset ' + asset)
    for m in spec['protectedMaps']:
        if not disk(m, 'umap').exists():
            problems.append('missing protected map ' + m)
    for kind in KINDS:
        if kind not in spec['textures']:
            problems.append('spec textures lacks ' + kind)
    plan = {v: {'parent': c['parentInstance'], 'new': c['newInstance'], 'expectedSlots': c['expectedSlotCount'], 'scalars': c['scalars'], 'tint': c['tint']} for v, c in spec['variants'].items()}
    return {'status': 'offline_ok' if not problems else 'offline_problems', 'problems': problems, 'sources': sources, 'plan': plan,
            'protectedFiles': len(protected_paths(spec)), 'mapSha256Now': sha(ROOT / spec['targetMapFile']) if (ROOT / spec['targetMapFile']).exists() else None}


# ------------------------------------------------------------------------------------------ native
class Native:
    def __init__(self, ue, spec, mode, stamp, allow_drift=False):
        self.u = ue
        self.spec = spec
        self.mode = mode
        self.stamp = stamp
        self.allow_drift = allow_drift
        self.ed = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.ml = ue.MaterialEditingLibrary
        self.map_file = ROOT / spec['targetMapFile']
        self.receipt_path = ROOT / spec['receiptFolder'] / ('%s%s-%s.json' % (spec['receiptPrefix'], mode, stamp))
        assert not self.receipt_path.exists()
        self.report = {'status': 'STARTED', 'mode': mode, 'stamp': stamp, 'map': spec['targetMap'], 'specSha256': sha(SPEC_PATH),
                       'scriptSha256': sha(Path(__file__)), 'engineVersion': ue.SystemLibrary.get_engine_version(),
                       'commandLine': ue.SystemLibrary.get_command_line(), 'errors': [], 'stages': []}
        self.write()

    def write(self):
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(self.report, indent=2, default=str) + '\n', encoding='utf-8')

    def stage(self, name, **extra):
        row = {'stage': name, 'utc': datetime.now(timezone.utc).isoformat()}
        row.update(extra)
        self.report['stages'].append(row)
        self.write()

    # -- guards
    def guard_project(self):
        u = self.u
        if Path(u.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project directory')
        if self.ed.get_game_world():
            raise RuntimeError('Game world active')
        dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()] + [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
        if dirty:
            raise RuntimeError('Dirty packages before start: %s' % dirty)

    def guard_world(self):
        u = self.u
        if not self.levels.load_level(self.spec['targetMap']):
            raise RuntimeError('load_level failed')
        world = self.ed.get_editor_world()
        if world.get_outermost().get_name() != self.spec['targetMap']:
            raise RuntimeError('Wrong map loaded')
        for folder in ('__ExternalActors__', '__ExternalObjects__'):
            if (ROOT / 'Content' / folder / self.spec['targetMap'][6:]).exists():
                raise RuntimeError('One-file-per-actor map needs expanded checkpoint support')
        return world

    def dirty_content_names(self):
        return sorted(p.get_name() for p in self.u.EditorLoadingAndSavingUtils.get_dirty_content_packages())

    # -- material instance readback
    def instance_values(self, inst):
        u, ml = self.u, self.ml
        row = {'path': asset_path(inst), 'class': inst.get_class().get_name(), 'parent': asset_path(inst.get_editor_property('parent')),
               'scalars': {n: float(ml.get_material_instance_scalar_parameter_value(inst, n)) for n in SCALARS},
               'textures': {t: asset_path(ml.get_material_instance_texture_parameter_value(inst, t)) for t in KINDS}}
        tint = ml.get_material_instance_vector_parameter_value(inst, 'Tint')
        row['tint'] = [float(tint.r), float(tint.g), float(tint.b), float(tint.a)]
        nan = u.MaterialUsage.MATUSAGE_NANITE
        row['naniteUsage'] = {'enabled': bool(ml.has_material_usage(inst, nan)), 'explicitlyOverridden': bool(ml.has_material_usage_override(inst, nan))}
        explicit = {}
        for entry in inst.get_editor_property('scalar_parameter_values'):
            explicit[str(entry.get_editor_property('parameter_info').get_editor_property('name'))] = float(entry.get_editor_property('parameter_value'))
        row['explicitScalarOverrides'] = explicit
        return row

    def expected_instance(self, variant):
        cfg = self.spec['variants'][variant]
        folder = self.spec['textureFolder']
        return {'parent': cfg['parentInstance'], 'scalars': {k: float(v) for k, v in cfg['scalars'].items()},
                'textures': {k: '%s/%s%s' % (folder, cfg['sourcePrefix'], k) for k in KINDS}, 'tint': [float(x) for x in cfg['tint']]}

    def check_instance(self, row, variant):
        want = self.expected_instance(variant)
        if row['parent'] != want['parent']:
            raise RuntimeError('%s parent is %s, want %s' % (row['path'], row['parent'], want['parent']))
        if row['textures'] != want['textures']:
            raise RuntimeError('%s textures %s, want %s' % (row['path'], row['textures'], want['textures']))
        if not close(row['scalars'], want['scalars']) or not close(row['tint'], want['tint']):
            raise RuntimeError('%s scalars/tint read back %s / %s' % (row['path'], row['scalars'], row['tint']))
        if set(row['explicitScalarOverrides']) != set(SCALARS):
            raise RuntimeError('%s must carry explicit overrides for all of %s, has %s' % (row['path'], SCALARS, sorted(row['explicitScalarOverrides'])))
        if self.spec['nanite']['requireExplicitUsageOverride'] and row['naniteUsage'] != {'enabled': True, 'explicitlyOverridden': True}:
            raise RuntimeError('%s Nanite usage read back %s' % (row['path'], row['naniteUsage']))

    # -- texture helpers
    def texture_values(self, tex):
        row = {'path': asset_path(tex), 'class': tex.get_class().get_name(), 'srgb': bool(tex.get_editor_property('srgb')),
               'compression': str(tex.get_editor_property('compression_settings')), 'lodGroup': str(tex.get_editor_property('lod_group')),
               'size': None}
        for getter in ('blueprint_get_size_x', 'get_size_x'):      # 5.8 exposes blueprint_get_size_x; keep the older name as fallback
            if hasattr(tex, getter):
                row['size'] = [int(getattr(tex, getter)()), int(getattr(tex, getter.replace('_x', '_y'))())]
                break
        try:
            row['virtualTextureStreaming'] = bool(tex.get_editor_property('virtual_texture_streaming'))
        except Exception as error:  # noqa: BLE001
            row['virtualTextureStreaming'] = 'unavailable: %r' % (error,)
        try:
            row['flipGreenChannel'] = bool(tex.get_editor_property('flip_green_channel'))
        except Exception:  # noqa: BLE001
            row['flipGreenChannel'] = None
        return row

    def check_texture(self, row, kind):
        cfg = self.spec['textures'][kind]
        size = int(self.spec['requiredSize'])
        if row['class'] != 'Texture2D' or row['size'] != [size, size]:
            raise RuntimeError('%s is %s %s' % (row['path'], row['class'], row['size']))
        if row['srgb'] != bool(cfg['srgb']) or cfg['compression'] not in row['compression'] or cfg['lodGroup'] not in row['lodGroup']:
            raise RuntimeError('%s settings read back %s' % (row['path'], row))
        if kind == 'Normal' and row['flipGreenChannel'] is not False:
            raise RuntimeError('%s flip_green_channel read back %s' % (row['path'], row['flipGreenChannel']))
        if row['virtualTextureStreaming'] is True and not self.spec['virtualTextureStreaming']:
            raise RuntimeError('%s is virtual-texture streamed' % row['path'])

    def import_texture(self, variant, kind, file_info):
        u = self.u
        cfg = self.spec['textures'][kind]
        folder = self.spec['textureFolder']
        name = self.spec['variants'][variant]['sourcePrefix'] + kind
        path = folder + '/' + name
        record = {'asset': path, 'source': str(file_info['path'].relative_to(ROOT)), 'sourceSha256': file_info['sha256']}
        if self.assets.does_asset_exist(path):
            tex = u.load_asset(path)
            record['reused'] = True          # resume from a partial earlier import: verified below like a fresh one
        else:
            task = u.AssetImportTask()
            for key, value in dict(filename=str(file_info['path']), destination_path=folder, destination_name=name, automated=True, replace_existing=False, save=False).items():
                task.set_editor_property(key, value)
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            objects = list(task.get_objects())
            if len(objects) != 1 or not isinstance(objects[0], u.Texture2D):
                raise RuntimeError('Import of %s produced %s' % (file_info['path'].name, [type(o).__name__ for o in objects]))
            tex = objects[0]
            record['reused'] = False
        tex.set_editor_property('compression_settings', getattr(u.TextureCompressionSettings, cfg['compression']))
        tex.set_editor_property('srgb', bool(cfg['srgb']))
        tex.set_editor_property('lod_group', getattr(u.TextureGroup, cfg['lodGroup']))
        if kind == 'Normal':
            tex.set_editor_property('flip_green_channel', bool(cfg['flipGreenChannel']))
        try:
            tex.set_editor_property('virtual_texture_streaming', bool(self.spec['virtualTextureStreaming']))
        except Exception as error:  # noqa: BLE001
            record['virtualTextureStreamingSet'] = 'unavailable: %r' % (error,)
        if not self.assets.save_loaded_asset(tex, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        record['readback'] = self.texture_values(tex)
        self.check_texture(record['readback'], kind)
        record['uassetSha256'] = sha(disk(path))
        return tex, record

    def set_param(self, inst, kind, name, value):
        """Set + readback; the 5.8 setters' bool is meaningless (always False)."""
        u, ml = self.u, self.ml
        if kind == 'scalar':
            ml.set_material_instance_scalar_parameter_value(inst, name, float(value))
            got = float(ml.get_material_instance_scalar_parameter_value(inst, name))
            if abs(got - float(value)) > 1e-5:
                raise RuntimeError('Scalar %s read back %r, want %r' % (name, got, value))
        elif kind == 'vector':
            ml.set_material_instance_vector_parameter_value(inst, name, u.LinearColor(*value))
            got = ml.get_material_instance_vector_parameter_value(inst, name)
            if not close([got.r, got.g, got.b, got.a], list(value)):
                raise RuntimeError('Vector %s read back %r, want %r' % (name, got, value))
        else:
            ml.set_material_instance_texture_parameter_value(inst, name, value)
            got = asset_path(ml.get_material_instance_texture_parameter_value(inst, name))
            if got != asset_path(value):
                raise RuntimeError('Texture %s read back %r, want %r' % (name, got, asset_path(value)))

    def build_instance(self, variant, textures):
        u, ml = self.u, self.ml
        cfg = self.spec['variants'][variant]
        path = cfg['newInstance']
        folder, name = path.rsplit('/', 1)
        record = {'asset': path, 'parent': cfg['parentInstance']}
        parent = u.load_asset(cfg['parentInstance'])
        if not isinstance(parent, u.MaterialInstanceConstant):
            raise RuntimeError('Parent %s is not a MaterialInstanceConstant' % cfg['parentInstance'])
        if self.assets.does_asset_exist(path):
            inst = u.load_asset(path)
            if not isinstance(inst, u.MaterialInstanceConstant):
                raise RuntimeError('Existing asset at %s is not a MaterialInstanceConstant' % path)
            record['reused'] = True
        else:
            inst = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
            if not isinstance(inst, u.MaterialInstanceConstant):
                raise RuntimeError('MaterialInstanceConstant factory failed for ' + path)
            record['reused'] = False
        if asset_path(inst.get_editor_property('parent')) != cfg['parentInstance']:
            ml.set_material_instance_parent(inst, parent)
            if asset_path(inst.get_editor_property('parent')) != cfg['parentInstance']:
                inst.set_editor_property('parent', parent)
                ml.update_material_instance(inst)
        if asset_path(inst.get_editor_property('parent')) != cfg['parentInstance']:
            raise RuntimeError('Parent did not take on ' + path)
        for kind in KINDS:
            self.set_param(inst, 'texture', self.spec['textures'][kind]['parameter'], textures[kind])
        for pname, value in cfg['scalars'].items():
            self.set_param(inst, 'scalar', pname, value)
        self.set_param(inst, 'vector', 'Tint', cfg['tint'])
        if self.spec['nanite']['requireExplicitUsageOverride']:
            ml.set_material_usage_override(inst, u.MaterialUsage.MATUSAGE_NANITE, True, True)
        ml.update_material_instance(inst)
        if not self.assets.save_loaded_asset(inst, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        record['readback'] = self.instance_values(inst)
        self.check_instance(record['readback'], variant)
        record['uassetSha256'] = sha(disk(path))
        return inst, record

    # ---------------------------------------------------------------------------------- IMPORT
    def do_import(self):
        u = self.u
        spec = self.spec
        r = self.report
        self.guard_project()
        manifest = json.loads((ROOT / spec['sourceManifest']).read_text(encoding='utf-8-sig'))
        files = source_files(spec, manifest)
        r['sourceManifest'] = {'path': spec['sourceManifest'], 'sha256': sha(ROOT / spec['sourceManifest']), 'generatorSha256': manifest.get('generatorSha256')}
        r['sourceStatistics'] = {v: manifest['variants'][v].get('statistics') for v in spec['variants']}
        r['sourceSchedule'] = {v: manifest['variants'][v].get('schedule') for v in spec['variants']}
        r['diagnosisBaseline'] = manifest.get('diagnosisBaseline_sandstone_blocks_08')
        r['measuredBaselineNormal'] = manifest.get('measuredBaselineNormal')
        r['protectedBefore'] = protected_hashes(spec)
        r['parentInstancesBefore'] = {v: self.instance_values(u.load_asset(c['parentInstance'])) for v, c in spec['variants'].items()}
        self.stage('discovered')
        r['textures'], r['instances'] = {}, {}
        for variant in spec['variants']:
            handles = {}
            r['textures'][variant] = {}
            for kind in KINDS:
                tex, record = self.import_texture(variant, kind, files[variant][kind])
                handles[kind] = tex
                r['textures'][variant][kind] = record
                self.write()
            self.stage('textures_saved_' + variant)
            inst, record = self.build_instance(variant, handles)
            r['instances'][variant] = record
            self.stage('instance_saved_' + variant)
        dirty = self.dirty_content_names()
        if dirty:
            raise RuntimeError('Packages still dirty after saves: %s' % dirty)
        # parents untouched (values and bytes)
        r['parentInstancesAfter'] = {v: self.instance_values(u.load_asset(c['parentInstance'])) for v, c in spec['variants'].items()}
        if r['parentInstancesAfter'] != r['parentInstancesBefore']:
            raise RuntimeError('Parent instance values changed')
        # reload from disk and read back
        r['reloaded'] = {}
        for variant, cfg in spec['variants'].items():
            for kind in KINDS:
                path = r['textures'][variant][kind]['asset']
                self.assets.load_asset(path)
            inst = u.load_asset(cfg['newInstance'])
            row = self.instance_values(inst)
            self.check_instance(row, variant)
            r['reloaded'][variant] = {'instance': row, 'textures': {k: self.texture_values(u.load_asset(r['textures'][variant][k]['asset'])) for k in KINDS}}
            for kind in KINDS:
                self.check_texture(r['reloaded'][variant]['textures'][kind], kind)
        r['newAssetHashes'] = {a: sha(disk(a)) for v in spec['variants'] for a in [spec['variants'][v]['newInstance']] + [r['textures'][v][k]['asset'] for k in KINDS]}
        r['status'] = 'IMPORTED_SAVED_READBACK_APPLY_PENDING'
        return r

    # ---------------------------------------------------------------------------------- SLOT ENUMERATION
    def enumerate_slots(self):
        """[(actor, component, slot, effectivePath, overrideArrayPaths)] for every StaticMeshComponent slot in the level, plus a Counter of effective materials."""
        u = self.u
        rows, counts = [], Counter()
        for actor in self.actors.get_all_level_actors():
            for component in actor.get_components_by_class(u.StaticMeshComponent):
                overrides = [asset_path(m) for m in component.get_editor_property('override_materials')]
                for slot in range(component.get_num_materials()):
                    effective = asset_path(component.get_material(slot))
                    counts[effective or 'None'] += 1
                    rows.append((actor, component, slot, effective, overrides))
        return rows, counts

    def build_plan(self, rows):
        spec = self.spec
        mapping = {c['parentInstance']: (v, c['newInstance']) for v, c in spec['variants'].items()}
        plan = []
        for actor, component, slot, effective, overrides in rows:
            if effective in mapping:
                variant, new = mapping[effective]
                plan.append({'actor': actor.get_path_name(), 'label': actor.get_actor_label(), 'folder': str(actor.get_folder_path()),
                             'component': component.get_path_name(), 'componentClass': component.get_class().get_name(), 'slot': slot,
                             'mesh': asset_path(component.get_editor_property('static_mesh')), 'variant': variant, 'effectiveBefore': effective,
                             'overrideArrayBefore': list(overrides), 'newMaterial': new, 'handle': component})
        counts = Counter(item['variant'] for item in plan)
        drift = {v: {'expected': c['expectedSlotCount'], 'found': counts.get(v, 0)} for v, c in spec['variants'].items()}
        mismatch = [v for v, d in drift.items() if d['expected'] != d['found']]
        if mismatch and spec['countPolicy']['refuseOnMismatch'] and not self.allow_drift:
            raise RuntimeError('Slot counts differ from the inventory %s; inspect the scene, or pass %s' % (drift, spec['countPolicy']['allowSwitch']))
        return plan, drift

    def scene_snapshot(self):
        rows = {}
        for a in self.actors.get_all_level_actors():
            loc, rot, sc = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
            comps = len(a.get_components_by_class(self.u.StaticMeshComponent))
            rows[a.get_name()] = (a.get_actor_label(), round(loc.x, 3), round(loc.y, 3), round(loc.z, 3), round(rot.pitch, 3), round(rot.yaw, 3), round(rot.roll, 3),
                                  round(sc.x, 4), round(sc.y, 4), round(sc.z, 4), comps)
        return rows

    def components_by_path(self):
        u = self.u
        out = {}
        for actor in self.actors.get_all_level_actors():
            for component in actor.get_components_by_class(u.StaticMeshComponent):
                out[component.get_path_name()] = component
        return out

    def save_map(self):
        u = self.u
        dirty = self.dirty_content_names()
        if dirty:
            raise RuntimeError('Dirty content packages before map save: %s' % dirty)
        if not self.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('Map still dirty after save')

    def readback_plan(self, plan, expect_new=True):
        by_path = self.components_by_path()
        bad = []
        for item in plan:
            component = by_path.get(item['component'])
            if component is None:
                bad.append((item['component'], 'missing'))
                continue
            got = asset_path(component.get_material(item['slot']))
            want = item['newMaterial'] if expect_new else item['effectiveBefore']
            if got != want:
                bad.append((item['component'], item['slot'], got, want))
        return bad

    # ---------------------------------------------------------------------------------- APPLY
    def do_apply(self, import_receipt):
        u = self.u
        spec = self.spec
        r = self.report
        prior = json.loads(Path(import_receipt).read_text(encoding='utf-8-sig'))
        r['importReceipt'] = {'path': str(import_receipt), 'sha256': sha(import_receipt), 'status': prior.get('status')}
        if prior.get('status') != 'IMPORTED_SAVED_READBACK_APPLY_PENDING':
            raise RuntimeError('Import receipt status %r does not authorize apply' % prior.get('status'))
        for asset, digest in prior['newAssetHashes'].items():
            if not disk(asset).exists() or sha(disk(asset)) != digest:
                raise RuntimeError('Imported asset changed or missing since the import receipt: ' + asset)
        r['sourceStatistics'] = prior.get('sourceStatistics')
        self.guard_project()
        r['protectedBefore'] = protected_hashes(spec)
        r['mapSha256Before'] = sha(self.map_file)
        instances = {}
        for variant, cfg in spec['variants'].items():
            inst = u.load_asset(cfg['newInstance'])
            row = self.instance_values(inst)
            self.check_instance(row, variant)
            instances[variant] = inst
        r['newInstances'] = {v: self.instance_values(i) for v, i in instances.items()}
        self.guard_world()
        rows, counts_before = self.enumerate_slots()
        r['materialCountsBefore'] = dict(counts_before)
        plan, drift = self.build_plan(rows)
        r['slotCounts'] = drift
        r['plannedSlots'] = len(plan)
        r['componentsTouched'] = len({item['component'] for item in plan})
        r['plan'] = [{k: v for k, v in item.items() if k != 'handle'} for item in plan]
        self.stage('planned', planned=len(plan))
        # checkpoint (map only: no existing asset is edited)
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + self.stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(self.map_file, checkpoint / self.map_file.name)
        if sha(checkpoint / self.map_file.name) != r['mapSha256Before']:
            raise RuntimeError('Map checkpoint hash differs')
        (checkpoint / 'protected.json').write_text(json.dumps(r['protectedBefore'], indent=2), encoding='utf-8')
        r['checkpoint'] = str(checkpoint)
        self.stage('checkpointed')
        before_scene = self.scene_snapshot()
        # mutate: group by component, pad the override array, set the slot, read back immediately
        by_component = defaultdict(list)
        for item in plan:
            by_component[item['component']].append(item)
        applied = 0
        for component_path, items in by_component.items():
            component = items[0]['handle']
            component.get_owner().modify(True)
            component.modify(True)
            overrides = list(component.get_editor_property('override_materials'))
            while len(overrides) < component.get_num_materials():
                overrides.append(None)
            for item in items:
                overrides[item['slot']] = instances[item['variant']]
            component.set_editor_property('override_materials', overrides)
            for item in items:
                got = asset_path(component.get_material(item['slot']))
                if got != item['newMaterial']:
                    raise RuntimeError('Override did not take on %s slot %d: %s' % (component_path, item['slot'], got))
                applied += 1
        r['applied'] = applied
        if self.scene_snapshot() != before_scene:
            raise RuntimeError('Unrelated scene change detected before save')
        _, counts_after = self.enumerate_slots()
        expected_after = Counter(counts_before)
        for variant, cfg in spec['variants'].items():
            moved = expected_after.pop(cfg['parentInstance'], 0)
            expected_after[cfg['newInstance']] += moved
        if counts_after != expected_after:
            raise RuntimeError('Material slot census after apply differs from the expected move: %s' % {k: (counts_after.get(k), expected_after.get(k)) for k in set(counts_after) | set(expected_after) if counts_after.get(k) != expected_after.get(k)})
        r['materialCountsAfter'] = dict(counts_after)
        self.stage('applied_in_memory', applied=applied)
        self.save_map()
        r['mapSaved'] = True
        r['mapSha256AfterSave'] = sha(self.map_file)
        self.stage('map_saved')
        if not self.levels.load_level(spec['targetMap']):
            raise RuntimeError('Reopen failed')
        bad = self.readback_plan(plan, expect_new=True)
        _, counts_reopened = self.enumerate_slots()
        r['reopened'] = {'badSlots': bad[:20], 'badSlotCount': len(bad), 'materialCounts': dict(counts_reopened), 'sceneUnchanged': self.scene_snapshot() == before_scene}
        if bad or counts_reopened != counts_after or not r['reopened']['sceneUnchanged']:
            raise RuntimeError('Reopened readback mismatch: %d bad slots, census equal %s' % (len(bad), counts_reopened == counts_after))
        r['status'] = 'APPLIED_SAVED_REOPENED_VISUAL_REVIEW_PENDING'
        return r

    # ---------------------------------------------------------------------------------- VERIFY
    def do_verify(self, apply_receipt):
        spec = self.spec
        r = self.report
        prior = json.loads(Path(apply_receipt).read_text(encoding='utf-8-sig'))
        r['applyReceipt'] = {'path': str(apply_receipt), 'sha256': sha(apply_receipt), 'status': prior.get('status')}
        r['mapSha256Now'] = sha(self.map_file)
        r['mapMatchesApplyAfter'] = r['mapSha256Now'] == prior.get('mapSha256AfterSave')
        r['protectedNow'] = protected_hashes(spec)
        r['protectedUnchangedSinceApply'] = r['protectedNow'] == prior.get('protectedBefore')
        self.guard_project()
        for variant, cfg in spec['variants'].items():
            self.check_instance(self.instance_values(self.u.load_asset(cfg['newInstance'])), variant)
        self.guard_world()
        bad = self.readback_plan(prior['plan'], expect_new=True)
        _, counts = self.enumerate_slots()
        r['badSlots'] = bad[:20]
        r['badSlotCount'] = len(bad)
        r['materialCounts'] = dict(counts)
        r['censusMatchesApply'] = dict(counts) == prior.get('materialCountsAfter')
        ok = r['mapMatchesApplyAfter'] and r['protectedUnchangedSinceApply'] and not bad and r['censusMatchesApply']
        r['status'] = 'FRESH_PROCESS_VERIFIED' if ok else 'FRESH_PROCESS_MISMATCH'
        return r

    # ---------------------------------------------------------------------------------- REVERT
    def do_revert(self, apply_receipt):
        u = self.u
        spec = self.spec
        r = self.report
        prior = json.loads(Path(apply_receipt).read_text(encoding='utf-8-sig'))
        r['applyReceipt'] = {'path': str(apply_receipt), 'sha256': sha(apply_receipt), 'status': prior.get('status')}
        checkpoint = Path(prior['checkpoint'])
        r['mapSha256Before'] = sha(self.map_file)
        self.guard_project()
        if r['mapSha256Before'] == prior.get('mapSha256AfterSave'):
            src = checkpoint / self.map_file.name
            if sha(src) != prior['mapSha256Before']:
                raise RuntimeError('Checkpoint map bytes do not match the apply receipt')
            shutil.copy2(src, self.map_file)
            r['mapRestoreMode'] = 'checkpoint_bytes'
            self.stage('map_bytes_restored')
            self.guard_world()
        else:
            r['mapRestoreMode'] = 'property_level_before_values'
            self.guard_world()
            by_path = self.components_by_path()
            by_component = defaultdict(list)
            for item in prior['plan']:
                by_component[item['component']].append(item)
            restored = 0
            for component_path, items in by_component.items():
                component = by_path.get(component_path)
                if component is None:
                    raise RuntimeError('Component missing for revert: ' + component_path)
                component.get_owner().modify(True)
                component.modify(True)
                before = items[0]['overrideArrayBefore']
                overrides = [u.load_asset(p) if p else None for p in before]
                component.set_editor_property('override_materials', overrides)
                for item in items:
                    got = asset_path(component.get_material(item['slot']))
                    if got != item['effectiveBefore']:
                        raise RuntimeError('Revert did not take on %s slot %d: %s' % (component_path, item['slot'], got))
                    restored += 1
            r['restoredSlots'] = restored
            self.save_map()
            self.stage('map_saved')
            if not self.levels.load_level(spec['targetMap']):
                raise RuntimeError('Reopen failed')
        bad = self.readback_plan(prior['plan'], expect_new=False)
        _, counts = self.enumerate_slots()
        r['mapSha256After'] = sha(self.map_file)
        r['reopened'] = {'badSlots': bad[:20], 'badSlotCount': len(bad), 'materialCounts': dict(counts), 'censusMatchesApplyBefore': dict(counts) == prior.get('materialCountsBefore')}
        r['newAssetsLeftOnDisk'] = [c['newInstance'] for c in spec['variants'].values() if disk(c['newInstance']).exists()]   # revert leaves them; unreferenced
        ok = not bad and (r['mapRestoreMode'] == 'property_level_before_values' or r['reopened']['censusMatchesApplyBefore'])
        r['status'] = 'REVERTED_REOPENED' if ok else 'REVERT_READBACK_MISMATCH'
        return r


def _native_main():
    import unreal as ue
    cmd = ue.SystemLibrary.get_command_line()
    spec = load_spec()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    import_m = re.search(r'-LimestoneV2Import(?=\s|$)', cmd)
    apply_m = re.search(r'-LimestoneV2Apply=(?:"([^"]+)"|([^\s]+))', cmd)
    verify_m = re.search(r'-LimestoneV2Verify=(?:"([^"]+)"|([^\s]+))', cmd)
    revert_m = re.search(r'-LimestoneV2Revert=(?:"([^"]+)"|([^\s]+))', cmd)
    allow_drift = '-limestonev2allowcountdrift' in cmd.lower()
    modes = [m for m, hit in (('import', import_m), ('apply', apply_m), ('verify', verify_m), ('revert', revert_m)) if hit]
    if len(modes) != 1:
        raise RuntimeError('Pass exactly one of -LimestoneV2Import, -LimestoneV2Apply=<receipt>, -LimestoneV2Verify=<receipt>, -LimestoneV2Revert=<receipt>')
    mode = modes[0]
    arg = None
    if mode != 'import':
        m = {'apply': apply_m, 'verify': verify_m, 'revert': revert_m}[mode]
        arg = Path(m.group(1) or m.group(2))
        if not arg.exists():
            raise RuntimeError('Receipt not found: %s' % arg)
    native = Native(ue, spec, mode, stamp, allow_drift)
    protected_before = protected_hashes(spec)
    try:
        if mode == 'import':
            native.do_import()
        elif mode == 'apply':
            native.do_apply(arg)
        elif mode == 'verify':
            native.do_verify(arg)
        else:
            native.do_revert(arg)
    except Exception as exc:  # noqa: BLE001
        native.report['status'] = 'FAILED_' + mode.upper() + ('_CHECKPOINT_AVAILABLE' if native.report.get('checkpoint') else '')
        native.report['errors'].append(repr(exc))
        native.report['traceback'] = traceback.format_exc()
        raise
    finally:
        native.report['protectedAfter'] = protected_hashes(spec)
        native.report['protectedUnchanged'] = native.report['protectedAfter'] == protected_before
        native.report['mapSha256Final'] = sha(native.map_file)
        if not native.report['protectedUnchanged']:
            native.report['status'] = 'FAILED_PROTECTED_HASH_MISMATCH'
        native.write()
        ue.log('LIMESTONE_V2_%s %s status=%s' % (mode.upper(), native.receipt_path, native.report['status']))


if __name__ == '__main__':
    try:
        import unreal  # noqa: F401
        _native_main()
    except ImportError:
        print(json.dumps(offline_check(), indent=2, default=str))

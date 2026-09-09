"""Herodian ashlar V4: import the authored Second-Temple-outer-wall set and swap it onto the walls, reversibly (commandlet-safe).

Shmuel, verbatim: "I want the temple stones used for wall wherever you are using stones to be the large
style stones used for the 2nd temple outer wall." Consumes Scripts/release_herodian_ashlar_v4.spec.json
and the offline manifest written by Scripts/create_herodian_ashlar_v4.py. Modelled on
Scripts/release_limestone_textures_v2.py; the differences are the two map targets, the reassignment
RULE TABLE (several source materials, not two), the enclosure actor property, and the RoughStone
inspection.

  -HerodianV4Plan -Main50|-Candidate48   READ-ONLY. Loads the target map, censuses every static-mesh
                                      material slot, enumerates what each rule would touch and every
                                      MI_PBR_RoughStone slot (actor, folder, mesh) for human judgement,
                                      and writes the numbers a missing expectedVariantSlotCount needs.
                                      Changes nothing, saves nothing.  -> herodian-v4-plan-<target>-<stamp>.json
  -HerodianV4Import                   import the six PNGs (Albedo / Normal / ARM x Ashlar / Trim) into
                                      /Game/MikdashV3/MaterialReview/HerodianAshlarV4/Textures/, create the
                                      THREE NEW instances MI_HerodianV4_Ashlar / _Trim / _AshlarWeathered
                                      parented on the EXISTING MI_PBR_LimestoneAshlar / MI_PBR_LimestoneTrim,
                                      set every parameter explicitly, set the Nanite AND InstancedStaticMeshes
                                      usage overrides, save, reload, read back  -> herodian-v4-import-<stamp>.json
  -HerodianV4Apply=<import receipt> -Main50|-Candidate48
                                      load the target map, plan every StaticMeshComponent slot whose
                                      EFFECTIVE material matches a reassign rule, plus every actor whose
                                      WallMaterial property matches, checkpoint the map, set the
                                      per-component override_materials slot / the actor property, read back,
                                      save, reopen, read back  -> herodian-v4-apply-<target>-<stamp>.json
  -HerodianV4Verify=<apply receipt>   fresh-process readback only, no save   -> herodian-v4-verify-<stamp>.json
  -HerodianV4Revert=<apply receipt>   restore the checkpointed map bytes (or the recorded per-slot and
                                      per-actor before-values if the map has moved on), reopen, read back
                                                                             -> herodian-v4-revert-<stamp>.json
  -HerodianV4AllowCountDrift          accept slot counts that differ from the target's expectedVariantSlotCount
  -HerodianV4IncludeRoughStone        also reassign the MI_PBR_RoughStone slots (see the spec's reassign entry:
                                      by default they are inspected and left alone, because RoughStone is the
                                      ground/foundation profile, not a dressed wall face)
  -HerodianV4IncludeMenorahStone      cancel the default exclusion of the 3 Release/MenorahV4 slots (the
                                      menorah's stone of three steps; see the spec's excludeSlots entry)
  -HerodianV4ExcludeNarrowTrim        exclude the 128 Trim members whose visible face is 14-15 cm, i.e.
                                      narrower than two drafted margins (string course and cornice, hearth
                                      stone surround, facade recessed field rail). Off by default; see the
                                      spec's excludeSlots entry for the measurements and the argument.

APPLY ORDER: Candidate48 FIRST. It is the configured default and the cook map, and its census shows it is
still on the ORIGINAL flat set (MI_PBR_LimestoneAshlar / MI_PBR_LimestoneTrim, the ~2 % albedo contrast
stand-in) - the V3 upgrade only ever reached the legacy Main50. The shipping build has the old walls.

Never touched: M_PBR_Tiled, the ten MI_PBR_* instances (including their usage flags), the LimestoneV2
instances and textures, the Kotel photo/stone materials, the paving and floor slabs, gold/cedar/marble/
plaster/frieze, every other protected asset, and the map that is NOT the selected target (it is added to
the protected set for the duration of the run). All hashed before and after every mode; a mismatch fails
the run. MaterialEditingLibrary setters return False even on success in 5.8, so every set is verified by
readback. The receipt is written at start, after each stage and in finally, so partial state is preserved
for resume; a save returning False raises.

Commandlet (strictly serial; check Get-Process UnrealEditor,UnrealEditor-Cmd first; unique -abslog):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe" "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript -unattended -nullrhi -abslog="C:/Mikdash/Working-5.8/HerodianV4-Import-01.log"
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_herodian_ashlar_v4.py" -HerodianV4Import
Offline:  python Scripts/release_herodian_ashlar_v4.py   -> offline_check(): spec/manifest/PNG sanity, the
tiling consistency check and the planned rule table.
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
SPEC_PATH = ROOT / 'Scripts' / 'release_herodian_ashlar_v4.spec.json'
KINDS = ('Albedo', 'Normal', 'ARM')
SCALARS = ('TilingCm', 'NormalStrength', 'RoughnessScale', 'Metallic', 'AlbedoFlatness')
USAGE_FLAGS = ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES')


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


def texture_asset(spec, variant_cfg, kind):
    return '%s/%s%s' % (spec['textureFolder'], variant_cfg['sourcePrefix'], kind)


def source_files(spec, manifest=None):
    """{variant: {kind: {'path': Path, 'sha256': str, 'size': [w, h]}}} from the offline manifest, verified on disk.
    Variants that share a sourcePrefix (AshlarWeathered reuses the Ashlar maps) resolve to the same files."""
    manifest = manifest or json.loads((ROOT / spec['sourceManifest']).read_text(encoding='utf-8-sig'))
    if manifest.get('status') != spec['sourceManifestStatusRequired']:
        raise RuntimeError('Source manifest status %r, need %r' % (manifest.get('status'), spec['sourceManifestStatusRequired']))
    if int(manifest.get('size', 0)) != int(spec['requiredSize']):
        raise RuntimeError('Source manifest size %s, need %s' % (manifest.get('size'), spec['requiredSize']))
    if float(manifest.get('tileCm', 0)) != float(spec['requiredTileCm']):
        raise RuntimeError('Source manifest tileCm %s, need %s' % (manifest.get('tileCm'), spec['requiredTileCm']))
    out = {}
    for variant, cfg in spec['variants'].items():
        record = manifest['variants'].get(cfg['manifestVariant'])
        if not record:
            raise RuntimeError('Manifest lacks variant ' + cfg['manifestVariant'])
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


def tiling_problems(spec, manifest=None):
    """The block sizes quoted in the spec are only true at TilingCm 300, so the three places that carry it must agree."""
    problems = []
    want = float(spec['tiling']['tilingCm'])
    if want != float(spec['requiredTileCm']):
        problems.append('spec tiling.tilingCm %s != requiredTileCm %s' % (want, spec['requiredTileCm']))
    for variant, cfg in spec['variants'].items():
        got = float(cfg['scalars']['TilingCm'])
        if got != want:
            problems.append('variant %s TilingCm %s != tiling.tilingCm %s' % (variant, got, want))
    try:
        manifest = manifest or json.loads((ROOT / spec['sourceManifest']).read_text(encoding='utf-8-sig'))
        if float(manifest.get('tileCm', 0)) != want:
            problems.append('manifest tileCm %s != tiling.tilingCm %s (the generator TILE_CM)' % (manifest.get('tileCm'), want))
        for variant, quoted in spec['tiling']['resultingBlockSizeCm'].items():
            schedule = manifest['variants'][variant]['schedule']
            for key in ('courseHeightsCm', 'blocksPerCourse', 'blockLengthCmMinMax', 'draftedMarginCmMinMax', 'bossProudCmMinMax',
                        'jointCm', 'jointDepthCm', 'courseSetbackCm'):
                if key in quoted and not close(quoted[key], schedule.get(key)):
                    problems.append('spec tiling.resultingBlockSizeCm.%s.%s %r != manifest schedule %r' % (variant, key, quoted[key], schedule.get(key)))
    except Exception as exc:  # noqa: BLE001
        problems.append('tiling cross-check against the manifest failed: %r' % (exc,))
    return problems


def protected_paths(spec, other_target_map_file=None):
    paths = {disk(a) for a in spec['protectedAssets']}
    paths |= {disk(m, 'umap') for m in spec['protectedMaps']}
    for pattern in spec.get('protectedGlobs', []):
        paths |= {Path(p) for p in glob.glob(str(ROOT / pattern), recursive=True)}
    if other_target_map_file:
        paths.add(ROOT / other_target_map_file)
    return sorted(paths)


def protected_hashes(spec, other_target_map_file=None):
    return {str(p.relative_to(ROOT)): sha(p) for p in protected_paths(spec, other_target_map_file) if p.exists()}


def active_exclusions(spec, switches):
    """Exclusion entries in force for this run. An entry excludes by default unless its cancelSwitch was
    passed; an entry with excludeByDefault false only bites when its enableSwitch was passed."""
    out = []
    for entry in spec.get('excludeSlots', []):
        if entry.get('excludeByDefault', True):
            if entry.get('cancelSwitch') and entry['cancelSwitch'].lower() in switches:
                continue
        else:
            if not (entry.get('enableSwitch') and entry['enableSwitch'].lower() in switches):
                continue
        out.append(entry)
    return out


def slot_excluded(entry, folder, mesh, label):
    if entry.get('folderEquals') and folder == entry['folderEquals']:
        return True
    if entry.get('folderStartsWith') and folder.startswith(entry['folderStartsWith']):
        return True
    for needle in entry.get('meshNameContains', []):
        if needle in (mesh or ''):
            return True
    for needle in entry.get('labelContains', []):
        if needle.lower() in (label or '').lower():
            return True
    return False


def active_rules(spec, include_rough_stone=False):
    out = []
    for rule in spec['reassign']:
        switch = rule.get('requiresSwitch')
        if switch and not (switch == '-HerodianV4IncludeRoughStone' and include_rough_stone):
            continue
        out.append(rule)
    return out


def offline_check(spec=None):
    spec = spec or load_spec()
    problems = list(tiling_problems(spec))
    try:
        files = source_files(spec)
        sources = {v: {k: {'path': str(e['path'].relative_to(ROOT)), 'sha256': e['sha256'], 'size': e['size']} for k, e in kinds.items()} for v, kinds in files.items()}
    except Exception as exc:  # noqa: BLE001
        problems.append('source set: ' + str(exc))
        sources = {}
    if not (ROOT / spec['sourcesDocument']).exists():
        problems.append('missing sources document ' + spec['sourcesDocument'])
    for variant, cfg in spec['variants'].items():
        if not disk(cfg['parentInstance']).exists():
            problems.append('missing parent instance ' + cfg['parentInstance'])
        if disk(cfg['newInstance']).exists():
            problems.append('new instance already exists on disk (fresh namespace expected): ' + cfg['newInstance'])
        if set(cfg['scalars']) != set(SCALARS):
            problems.append('variant %s must set exactly %s' % (variant, SCALARS))
    for rule in spec['reassign']:
        if rule['variant'] not in spec['variants']:
            problems.append('reassign rule points at unknown variant ' + rule['variant'])
        if rule['from'] in spec['doNotTouch']['materials']:
            problems.append('reassign rule would touch a doNotTouch material: ' + rule['from'])
    for asset in spec['protectedAssets']:
        if not disk(asset).exists():
            problems.append('missing protected asset ' + asset)
    for m in spec['protectedMaps']:
        if not disk(m, 'umap').exists():
            problems.append('missing protected map ' + m)
    for name, target in spec['targets'].items():
        path = ROOT / target['mapFile']
        if not path.exists():
            problems.append('missing target map file ' + target['mapFile'])
        elif sha(path) != target['observedMapSha256']:
            problems.append('NOTE (not fatal): %s map hash has moved since the spec was written (%s now); the receipts record the live value.' % (name, sha(path)[:16]))
    for kind in KINDS:
        if kind not in spec['textures']:
            problems.append('spec textures lacks ' + kind)
    plan = {v: {'parent': c['parentInstance'], 'new': c['newInstance'], 'scalars': c['scalars'], 'tint': c['tint'],
                'applyByDefault': c['applyByDefault']} for v, c in spec['variants'].items()}
    rules = [{'from': r['from'], 'variant': r['variant'], 'requiresSwitch': r.get('requiresSwitch')} for r in spec['reassign']]
    for entry in spec.get('excludeSlots', []):
        if entry.get('excludeByDefault', True) and not entry.get('cancelSwitch'):
            problems.append('exclusion %s excludes by default with no cancelSwitch' % entry['name'])
    fatal = [p for p in problems if not p.startswith('NOTE')]
    return {'status': 'offline_ok' if not fatal else 'offline_problems', 'problems': problems, 'sources': sources,
            'instances': plan, 'reassignRules': rules,
            'actorMaterialProperties': [{'property': r['property'], 'from': r['from'], 'variant': r['variant']} for r in spec['actorMaterialProperties']],
            'excludeSlots': [{'name': e['name'], 'excludeByDefault': e.get('excludeByDefault', True),
                              'cancelSwitch': e.get('cancelSwitch'), 'enableSwitch': e.get('enableSwitch'),
                              'measuredSlots': e.get('measuredSlots')} for e in spec.get('excludeSlots', [])],
            'applyOrder': spec['applyOrder']['first'],
            'tilingCm': spec['tiling']['tilingCm'], 'blockSizeCm': spec['tiling']['resultingBlockSizeCm'],
            'protectedFiles': len(protected_paths(spec)),
            'targets': {n: {'map': t['map'], 'mapSha256Now': sha(ROOT / t['mapFile']) if (ROOT / t['mapFile']).exists() else None,
                            'expectedVariantSlotCount': t['expectedVariantSlotCount']} for n, t in spec['targets'].items()}}


# ------------------------------------------------------------------------------------------ native
class Native:
    def __init__(self, ue, spec, mode, stamp, target=None, allow_drift=False, include_rough_stone=False, switches=()):
        self.u = ue
        self.spec = spec
        self.mode = mode
        self.stamp = stamp
        self.target = target
        self.allow_drift = allow_drift
        self.include_rough_stone = include_rough_stone
        self.switches = set(switches)
        self.exclusions = active_exclusions(spec, self.switches)
        self.ed = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.ml = ue.MaterialEditingLibrary
        cfg = spec['targets'][target] if target else None
        self.map_file = (ROOT / cfg['mapFile']) if cfg else None
        self.map_asset = cfg['map'] if cfg else None
        self.other_map_file = None
        if target:
            others = [t['mapFile'] for n, t in spec['targets'].items() if n != target]
            self.other_map_file = others[0] if others else None
        suffix = ('%s-%s' % (target, stamp)) if target else stamp
        self.receipt_path = ROOT / spec['receiptFolder'] / ('%s%s-%s.json' % (spec['receiptPrefix'], mode, suffix))
        assert not self.receipt_path.exists()
        self.report = {'status': 'STARTED', 'mode': mode, 'stamp': stamp, 'target': target, 'map': self.map_asset,
                       'specSha256': sha(SPEC_PATH), 'scriptSha256': sha(Path(__file__)),
                       'engineVersion': ue.SystemLibrary.get_engine_version(), 'commandLine': ue.SystemLibrary.get_command_line(),
                       'includeRoughStone': include_rough_stone, 'allowCountDrift': allow_drift,
                       'switches': sorted(self.switches),
                       'exclusionsInForce': [{'name': e['name'], 'why': e['why']} for e in self.exclusions],
                       'errors': [], 'stages': []}
        self.write()

    def write(self):
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(self.report, indent=2, default=str) + '\n', encoding='utf-8')

    def stage(self, name, **extra):
        row = {'stage': name, 'utc': datetime.now(timezone.utc).isoformat()}
        row.update(extra)
        self.report['stages'].append(row)
        self.write()

    def protected(self):
        return protected_hashes(self.spec, self.other_map_file)

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
        problems = tiling_problems(self.spec)
        if problems:
            raise RuntimeError('Tiling consistency failed (the quoted block sizes are only true at TilingCm %s): %s' % (self.spec['tiling']['tilingCm'], problems))

    def guard_world(self):
        u = self.u
        if not self.levels.load_level(self.map_asset):
            raise RuntimeError('load_level failed for ' + str(self.map_asset))
        world = self.ed.get_editor_world()
        if world.get_outermost().get_name() != self.map_asset:
            raise RuntimeError('Wrong map loaded: %s' % world.get_outermost().get_name())
        for folder in ('__ExternalActors__', '__ExternalObjects__'):
            if (ROOT / 'Content' / folder / self.map_asset[6:]).exists():
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
        row['usage'] = {}
        for name in USAGE_FLAGS:
            flag = getattr(u.MaterialUsage, name)
            row['usage'][name] = {'enabled': bool(ml.has_material_usage(inst, flag)), 'explicitlyOverridden': bool(ml.has_material_usage_override(inst, flag))}
        explicit = {}
        for entry in inst.get_editor_property('scalar_parameter_values'):
            explicit[str(entry.get_editor_property('parameter_info').get_editor_property('name'))] = float(entry.get_editor_property('parameter_value'))
        row['explicitScalarOverrides'] = explicit
        return row

    def expected_instance(self, variant):
        cfg = self.spec['variants'][variant]
        return {'parent': cfg['parentInstance'], 'scalars': {k: float(v) for k, v in cfg['scalars'].items()},
                'textures': {k: texture_asset(self.spec, cfg, k) for k in KINDS}, 'tint': [float(x) for x in cfg['tint']]}

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
        if float(row['scalars']['TilingCm']) != float(self.spec['tiling']['tilingCm']):
            raise RuntimeError('%s TilingCm %s does not match the spec tiling %s' % (row['path'], row['scalars']['TilingCm'], self.spec['tiling']['tilingCm']))
        need = [('MATUSAGE_NANITE', self.spec['usage']['requireExplicitNaniteOverride']),
                ('MATUSAGE_INSTANCED_STATIC_MESHES', self.spec['usage']['requireExplicitInstancedStaticMeshOverride'])]
        for name, required in need:
            if required and row['usage'][name] != {'enabled': True, 'explicitlyOverridden': True}:
                raise RuntimeError('%s %s read back %s (the enclosure HISMs and Nanite need both)' % (row['path'], name, row['usage'][name]))

    # -- texture helpers
    def texture_values(self, tex):
        row = {'path': asset_path(tex), 'class': tex.get_class().get_name(), 'srgb': bool(tex.get_editor_property('srgb')),
               'compression': str(tex.get_editor_property('compression_settings')), 'lodGroup': str(tex.get_editor_property('lod_group')), 'size': None}
        for getter in ('blueprint_get_size_x', 'get_size_x'):      # 5.8 exposes blueprint_get_size_x
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
            record['reused'] = True          # a shared prefix (AshlarWeathered) or a resumed import; verified below either way
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
        record = {'asset': path, 'parent': cfg['parentInstance'], 'applyByDefault': cfg['applyByDefault']}
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
        for name_, required in (('MATUSAGE_NANITE', self.spec['usage']['requireExplicitNaniteOverride']),
                                ('MATUSAGE_INSTANCED_STATIC_MESHES', self.spec['usage']['requireExplicitInstancedStaticMeshOverride'])):
            if required:
                ml.set_material_usage_override(inst, getattr(u.MaterialUsage, name_), True, True)
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
        r['sourceManifest'] = {'path': spec['sourceManifest'], 'sha256': sha(ROOT / spec['sourceManifest']), 'generatorSha256': manifest.get('generatorSha256'),
                               'iteration': manifest.get('iteration'), 'tileCm': manifest.get('tileCm')}
        r['sourcesDocumentSha256'] = sha(ROOT / spec['sourcesDocument'])
        r['sourceStatistics'] = {v: manifest['variants'][v].get('statistics') for v in manifest['variants']}
        r['sourceSchedule'] = {v: manifest['variants'][v].get('schedule') for v in manifest['variants']}
        r['previousIterationV3'] = manifest.get('previousIterationV3')
        r['photoReference'] = manifest.get('photoReference')
        r['diagnosisBaseline'] = manifest.get('diagnosisBaseline_sandstone_blocks_08')
        r['measuredBaselineNormal'] = manifest.get('measuredBaselineNormal')
        r['tilingCm'] = spec['tiling']['tilingCm']
        r['resultingBlockSizeCm'] = spec['tiling']['resultingBlockSizeCm']
        r['protectedBefore'] = self.protected()
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
        r['parentInstancesAfter'] = {v: self.instance_values(u.load_asset(c['parentInstance'])) for v, c in spec['variants'].items()}
        if r['parentInstancesAfter'] != r['parentInstancesBefore']:
            raise RuntimeError('Parent instance values changed')
        r['reloaded'] = {}
        for variant, cfg in spec['variants'].items():
            for kind in KINDS:
                self.assets.load_asset(r['textures'][variant][kind]['asset'])
            inst = u.load_asset(cfg['newInstance'])
            row = self.instance_values(inst)
            self.check_instance(row, variant)
            r['reloaded'][variant] = {'instance': row, 'textures': {k: self.texture_values(u.load_asset(r['textures'][variant][k]['asset'])) for k in KINDS}}
            for kind in KINDS:
                self.check_texture(r['reloaded'][variant]['textures'][kind], kind)
        r['newAssetHashes'] = {a: sha(disk(a)) for v in spec['variants'] for a in
                               [spec['variants'][v]['newInstance']] + [r['textures'][v][k]['asset'] for k in KINDS]}
        r['status'] = 'IMPORTED_SAVED_READBACK_APPLY_PENDING'
        return r

    # ---------------------------------------------------------------------------------- ENUMERATION
    def enumerate_slots(self):
        """[(actor, component, slot, effectivePath, overrideArrayPaths)] for every StaticMeshComponent slot, plus a Counter."""
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

    def guarded_actor(self, actor):
        needles = self.spec['kotelActorGuard']['labelOrFolderContains']
        text = (actor.get_actor_label() or '') + '|' + str(actor.get_folder_path())
        return any(n.lower() in text.lower() for n in needles)

    def build_plan(self, rows):
        spec = self.spec
        rules = active_rules(spec, self.include_rough_stone)
        mapping = {rule['from']: rule for rule in rules}
        forbidden = set(spec['doNotTouch']['materials'])
        prefixes = tuple(spec['doNotTouch']['assetPathPrefixes'])
        plan, guarded, excluded = [], [], []
        for actor, component, slot, effective, overrides in rows:
            rule = mapping.get(effective)
            if not rule:
                continue
            if effective in forbidden or (effective or '').startswith(prefixes):
                raise RuntimeError('A reassign rule matched a doNotTouch material: ' + str(effective))
            folder = str(actor.get_folder_path())
            label = actor.get_actor_label()
            mesh_now = asset_path(component.get_editor_property('static_mesh'))
            hit = next((e for e in self.exclusions if slot_excluded(e, folder, mesh_now, label)), None)
            if hit:
                excluded.append({'exclusion': hit['name'], 'actor': actor.get_path_name(), 'label': label, 'folder': folder,
                                 'component': component.get_path_name(), 'slot': slot, 'mesh': mesh_now,
                                 'effectiveBefore': effective, 'wouldHaveBeen': rule['variant']})
                continue
            if self.guarded_actor(actor):
                guarded.append({'actor': actor.get_path_name(), 'label': actor.get_actor_label(), 'folder': str(actor.get_folder_path()),
                                'component': component.get_path_name(), 'slot': slot, 'effectiveBefore': effective})
                continue
            mesh = asset_path(component.get_editor_property('static_mesh'))
            needle = rule.get('expectedMeshContains')
            if needle and needle not in (mesh or ''):
                raise RuntimeError('Rule for %s expects a mesh containing %r, found %s on %s slot %d' % (rule['from'], needle, mesh, component.get_path_name(), slot))
            plan.append({'actor': actor.get_path_name(), 'label': actor.get_actor_label(), 'folder': str(actor.get_folder_path()),
                         'component': component.get_path_name(), 'componentClass': component.get_class().get_name(), 'slot': slot,
                         'mesh': mesh, 'variant': rule['variant'], 'rule': rule['from'], 'effectiveBefore': effective,
                         'overrideArrayBefore': list(overrides), 'newMaterial': spec['variants'][rule['variant']]['newInstance'], 'handle': component})
        return plan, guarded, excluded

    def rough_stone_inventory(self, rows):
        """Every MI_PBR_RoughStone slot, with enough context for a human to judge wall versus foundation/ground."""
        rule = next((r for r in self.spec['reassign'] if r['from'].endswith('MI_PBR_RoughStone')), None)
        if not rule:
            return {}
        out = []
        for actor, component, slot, effective, _overrides in rows:
            if effective == rule['from']:
                out.append({'actor': actor.get_path_name(), 'label': actor.get_actor_label(), 'folder': str(actor.get_folder_path()),
                            'component': component.get_path_name(), 'slot': slot,
                            'mesh': asset_path(component.get_editor_property('static_mesh')),
                            'locationCm': [round(v, 1) for v in (actor.get_actor_location().x, actor.get_actor_location().y, actor.get_actor_location().z)]})
        return {'material': rule['from'], 'slots': len(out), 'reassigned': self.include_rough_stone,
                'why': rule['why'], 'switch': rule['requiresSwitch'], 'rows': out}

    def enumerate_actor_properties(self):
        """Actors exposing one of the spec's actorMaterialProperties whose current value matches a listed source."""
        found = []
        for spec_rule in self.spec['actorMaterialProperties']:
            if spec_rule.get('requiresSwitch'):
                continue
            prop = spec_rule['property']
            wanted = set(spec_rule['from'])
            for actor in self.actors.get_all_level_actors():
                try:
                    value = actor.get_editor_property(prop)
                except Exception:  # noqa: BLE001 - most actors do not expose it
                    continue
                current = asset_path(value)
                if current in wanted:
                    found.append({'actor': actor.get_path_name(), 'label': actor.get_actor_label(), 'folder': str(actor.get_folder_path()),
                                  'property': prop, 'before': current, 'variant': spec_rule['variant'],
                                  'newMaterial': self.spec['variants'][spec_rule['variant']]['newInstance'], 'handle': actor})
        return found

    def check_counts(self, plan):
        spec = self.spec
        expected = spec['targets'][self.target]['expectedVariantSlotCount']
        counts = Counter(item['variant'] for item in plan)
        per_rule = Counter(item['rule'] for item in plan)
        drift = {'found': dict(counts), 'foundPerRule': dict(per_rule), 'expected': expected}
        if expected is None:
            drift['note'] = 'No census exists for this target (%s). Run -HerodianV4Plan first and put these numbers in the spec.' % self.target
            if spec['countPolicy']['refuseOnMismatch'] and not self.allow_drift:
                raise RuntimeError('Target %s has no expectedVariantSlotCount. Run -HerodianV4Plan=%s, record the census in the spec, or pass %s. Found: %s'
                                   % (self.target, self.target, spec['countPolicy']['allowSwitch'], dict(counts)))
            return drift
        mismatch = {v: (expected.get(v), counts.get(v, 0)) for v in set(expected) | set(counts) if int(expected.get(v, 0)) != int(counts.get(v, 0))}
        drift['mismatch'] = mismatch
        if mismatch and spec['countPolicy']['refuseOnMismatch'] and not self.allow_drift:
            raise RuntimeError('Slot counts differ from the census %s; inspect the scene, or pass %s' % (mismatch, spec['countPolicy']['allowSwitch']))
        return drift

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

    def actors_by_path(self):
        return {a.get_path_name(): a for a in self.actors.get_all_level_actors()}

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

    def readback_actor_properties(self, rows, expect_new=True):
        by_path = self.actors_by_path()
        bad = []
        for item in rows:
            actor = by_path.get(item['actor'])
            if actor is None:
                bad.append((item['actor'], 'missing'))
                continue
            got = asset_path(actor.get_editor_property(item['property']))
            want = item['newMaterial'] if expect_new else item['before']
            if got != want:
                bad.append((item['actor'], item['property'], got, want))
        return bad

    # ---------------------------------------------------------------------------------- PLAN (read only)
    def do_plan(self):
        r = self.report
        self.guard_project()
        r['protectedBefore'] = self.protected()
        r['mapSha256Before'] = sha(self.map_file)
        r['mapSha256InSpec'] = self.spec['targets'][self.target]['observedMapSha256']
        r['mapMatchesSpecObservation'] = r['mapSha256Before'] == r['mapSha256InSpec']
        self.guard_world()
        rows, counts = self.enumerate_slots()
        r['materialCounts'] = dict(counts)
        r['staticMeshSlots'] = len(rows)
        plan, guarded, excluded = self.build_plan(rows)
        r['excludedSlots'] = {'count': len(excluded), 'byExclusion': dict(Counter(e['exclusion'] for e in excluded)),
                              'byVariantWouldHaveBeen': dict(Counter(e['wouldHaveBeen'] for e in excluded)), 'rows': excluded}
        r['wouldTouchSlots'] = len(plan)
        r['wouldTouchComponents'] = len({item['component'] for item in plan})
        r['countsByVariant'] = dict(Counter(item['variant'] for item in plan))
        r['countsByRule'] = dict(Counter(item['rule'] for item in plan))
        r['countsByFolder'] = dict(Counter(item['folder'] for item in plan))
        r['kotelGuardSkipped'] = guarded
        r['roughStoneInventory'] = self.rough_stone_inventory(rows)
        actor_rows = self.enumerate_actor_properties()
        r['actorMaterialProperties'] = [{k: v for k, v in item.items() if k != 'handle'} for item in actor_rows]
        r['sampleSlots'] = [{k: v for k, v in item.items() if k != 'handle'} for item in plan[:40]]
        r['suggestedSpecExpectedVariantSlotCount'] = r['countsByVariant']
        r['mapSha256After'] = sha(self.map_file)
        if r['mapSha256After'] != r['mapSha256Before']:
            raise RuntimeError('Plan is read-only but the map file changed')
        r['status'] = 'PLANNED_READ_ONLY'
        return r

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
        r['sourceSchedule'] = prior.get('sourceSchedule')
        r['tilingCm'] = prior.get('tilingCm')
        r['resultingBlockSizeCm'] = prior.get('resultingBlockSizeCm')
        r['targetRole'] = spec['targets'][self.target]['role']
        r['applyOrderNote'] = spec['applyOrder']['note']
        self.guard_project()
        r['protectedBefore'] = self.protected()
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
        plan, guarded, excluded = self.build_plan(rows)
        r['kotelGuardSkipped'] = guarded
        r['excludedSlots'] = {'count': len(excluded), 'byExclusion': dict(Counter(e['exclusion'] for e in excluded)),
                              'byVariantWouldHaveBeen': dict(Counter(e['wouldHaveBeen'] for e in excluded)), 'rows': excluded}
        r['roughStoneInventory'] = self.rough_stone_inventory(rows)
        r['slotCounts'] = self.check_counts(plan)
        r['plannedSlots'] = len(plan)
        r['componentsTouched'] = len({item['component'] for item in plan})
        r['plan'] = [{k: v for k, v in item.items() if k != 'handle'} for item in plan]
        actor_rows = self.enumerate_actor_properties()
        r['actorPropertyPlan'] = [{k: v for k, v in item.items() if k != 'handle'} for item in actor_rows]
        self.stage('planned', planned=len(plan), actorProperties=len(actor_rows))
        # checkpoint (map only: no existing asset is edited)
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + self.target + '-' + self.stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(self.map_file, checkpoint / self.map_file.name)
        if sha(checkpoint / self.map_file.name) != r['mapSha256Before']:
            raise RuntimeError('Map checkpoint hash differs')
        (checkpoint / 'protected.json').write_text(json.dumps(r['protectedBefore'], indent=2), encoding='utf-8')
        r['checkpoint'] = str(checkpoint)
        self.stage('checkpointed')
        before_scene = self.scene_snapshot()
        # mutate slots: group by component, pad the override array, set the slot, read back immediately
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
        # mutate actor material properties (the enclosure's WallMaterial: HISMs built in BeginPlay do not
        # read component slot overrides, so without this the precinct wall keeps the old material)
        actor_applied = 0
        for item in actor_rows:
            actor = item['handle']
            actor.modify(True)
            actor.set_editor_property(item['property'], instances[item['variant']])
            got = asset_path(actor.get_editor_property(item['property']))
            if got != item['newMaterial']:
                raise RuntimeError('Actor property %s did not take on %s: %s' % (item['property'], item['actor'], got))
            actor_applied += 1
        r['actorPropertiesApplied'] = actor_applied
        if self.scene_snapshot() != before_scene:
            raise RuntimeError('Unrelated scene change detected before save')
        _, counts_after = self.enumerate_slots()
        expected_after = Counter(counts_before)
        for item in plan:
            expected_after[item['effectiveBefore']] -= 1
            expected_after[item['newMaterial']] += 1
        expected_after = Counter({k: v for k, v in expected_after.items() if v})
        if counts_after != expected_after:
            raise RuntimeError('Material slot census after apply differs from the expected move: %s'
                               % {k: (counts_after.get(k), expected_after.get(k)) for k in set(counts_after) | set(expected_after) if counts_after.get(k) != expected_after.get(k)})
        r['materialCountsAfter'] = dict(counts_after)
        self.stage('applied_in_memory', applied=applied, actorProperties=actor_applied)
        self.save_map()
        r['mapSaved'] = True
        r['mapSha256AfterSave'] = sha(self.map_file)
        self.stage('map_saved')
        if not self.levels.load_level(self.map_asset):
            raise RuntimeError('Reopen failed')
        bad = self.readback_plan(plan, expect_new=True)
        bad_actors = self.readback_actor_properties(r['actorPropertyPlan'], expect_new=True)
        _, counts_reopened = self.enumerate_slots()
        r['reopened'] = {'badSlots': bad[:20], 'badSlotCount': len(bad), 'badActorProperties': bad_actors[:20], 'badActorPropertyCount': len(bad_actors),
                         'materialCounts': dict(counts_reopened), 'sceneUnchanged': self.scene_snapshot() == before_scene}
        if bad or bad_actors or counts_reopened != counts_after or not r['reopened']['sceneUnchanged']:
            raise RuntimeError('Reopened readback mismatch: %d bad slots, %d bad actor properties, census equal %s'
                               % (len(bad), len(bad_actors), counts_reopened == counts_after))
        r['status'] = 'APPLIED_SAVED_REOPENED_VISUAL_REVIEW_PENDING'
        return r

    # ---------------------------------------------------------------------------------- VERIFY
    def do_verify(self, apply_receipt):
        spec = self.spec
        r = self.report
        prior = json.loads(Path(apply_receipt).read_text(encoding='utf-8-sig'))
        r['applyReceipt'] = {'path': str(apply_receipt), 'sha256': sha(apply_receipt), 'status': prior.get('status'), 'target': prior.get('target')}
        r['mapSha256Now'] = sha(self.map_file)
        r['mapMatchesApplyAfter'] = r['mapSha256Now'] == prior.get('mapSha256AfterSave')
        r['protectedNow'] = self.protected()
        r['protectedUnchangedSinceApply'] = r['protectedNow'] == prior.get('protectedBefore')
        self.guard_project()
        for variant, cfg in spec['variants'].items():
            self.check_instance(self.instance_values(self.u.load_asset(cfg['newInstance'])), variant)
        self.guard_world()
        bad = self.readback_plan(prior['plan'], expect_new=True)
        bad_actors = self.readback_actor_properties(prior.get('actorPropertyPlan', []), expect_new=True)
        _, counts = self.enumerate_slots()
        r['badSlots'] = bad[:20]
        r['badSlotCount'] = len(bad)
        r['badActorProperties'] = bad_actors[:20]
        r['badActorPropertyCount'] = len(bad_actors)
        r['materialCounts'] = dict(counts)
        r['censusMatchesApply'] = dict(counts) == prior.get('materialCountsAfter')
        ok = r['mapMatchesApplyAfter'] and r['protectedUnchangedSinceApply'] and not bad and not bad_actors and r['censusMatchesApply']
        r['status'] = 'FRESH_PROCESS_VERIFIED' if ok else 'FRESH_PROCESS_MISMATCH'
        return r

    # ---------------------------------------------------------------------------------- REVERT
    def do_revert(self, apply_receipt):
        u = self.u
        r = self.report
        prior = json.loads(Path(apply_receipt).read_text(encoding='utf-8-sig'))
        r['applyReceipt'] = {'path': str(apply_receipt), 'sha256': sha(apply_receipt), 'status': prior.get('status'), 'target': prior.get('target')}
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
            actors = self.actors_by_path()
            restored_actors = 0
            for item in prior.get('actorPropertyPlan', []):
                actor = actors.get(item['actor'])
                if actor is None:
                    raise RuntimeError('Actor missing for revert: ' + item['actor'])
                actor.modify(True)
                actor.set_editor_property(item['property'], u.load_asset(item['before']) if item['before'] else None)
                got = asset_path(actor.get_editor_property(item['property']))
                if got != item['before']:
                    raise RuntimeError('Actor property revert did not take on %s: %s' % (item['actor'], got))
                restored_actors += 1
            r['restoredActorProperties'] = restored_actors
            self.save_map()
            self.stage('map_saved')
            if not self.levels.load_level(self.map_asset):
                raise RuntimeError('Reopen failed')
        bad = self.readback_plan(prior['plan'], expect_new=False)
        bad_actors = self.readback_actor_properties(prior.get('actorPropertyPlan', []), expect_new=False)
        _, counts = self.enumerate_slots()
        r['mapSha256After'] = sha(self.map_file)
        r['reopened'] = {'badSlots': bad[:20], 'badSlotCount': len(bad), 'badActorProperties': bad_actors[:20], 'badActorPropertyCount': len(bad_actors),
                         'materialCounts': dict(counts), 'censusMatchesApplyBefore': dict(counts) == prior.get('materialCountsBefore')}
        r['newAssetsLeftOnDisk'] = [c['newInstance'] for c in self.spec['variants'].values() if disk(c['newInstance']).exists()]
        ok = not bad and not bad_actors and (r['mapRestoreMode'] == 'property_level_before_values' or r['reopened']['censusMatchesApplyBefore'])
        r['status'] = 'REVERTED_REOPENED' if ok else 'REVERT_READBACK_MISMATCH'
        return r


def _target_from_command_line(spec, cmd, receipt=None):
    chosen = [name for name, cfg in spec['targets'].items() if re.search(re.escape(cfg['flag']) + r'(?=\s|$)', cmd)]
    if len(chosen) > 1:
        raise RuntimeError('Choose exactly one target: %s' % [c['flag'] for c in spec['targets'].values()])
    if chosen:
        if receipt and receipt.get('target') and receipt['target'] != chosen[0]:
            raise RuntimeError('Receipt target %r does not match the flag %r' % (receipt['target'], chosen[0]))
        return chosen[0]
    if receipt and receipt.get('target'):
        return receipt['target']
    raise RuntimeError('Choose the target with %s' % ' or '.join(c['flag'] for c in spec['targets'].values()))


def _native_main():
    import unreal as ue
    cmd = ue.SystemLibrary.get_command_line()
    spec = load_spec()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    plan_m = re.search(r'-HerodianV4Plan(?=\s|$)', cmd)
    import_m = re.search(r'-HerodianV4Import(?=\s|$)', cmd)
    apply_m = re.search(r'-HerodianV4Apply=(?:"([^"]+)"|([^\s]+))', cmd)
    verify_m = re.search(r'-HerodianV4Verify=(?:"([^"]+)"|([^\s]+))', cmd)
    revert_m = re.search(r'-HerodianV4Revert=(?:"([^"]+)"|([^\s]+))', cmd)
    lower = cmd.lower()
    allow_drift = '-herodianv4allowcountdrift' in lower
    include_rough = '-herodianv4includeroughstone' in lower
    known = ('-herodianv4allowcountdrift', '-herodianv4includeroughstone',
             '-herodianv4includemenorahstone', '-herodianv4excludenarrowtrim')
    switches = tuple(sw for sw in known if sw in lower)
    modes = [m for m, hit in (('plan', plan_m), ('import', import_m), ('apply', apply_m), ('verify', verify_m), ('revert', revert_m)) if hit]
    if len(modes) != 1:
        raise RuntimeError('Pass exactly one of -HerodianV4Plan, -HerodianV4Import, -HerodianV4Apply=<receipt>, -HerodianV4Verify=<receipt>, -HerodianV4Revert=<receipt>')
    mode = modes[0]
    arg, receipt = None, None
    if mode in ('apply', 'verify', 'revert'):
        m = {'apply': apply_m, 'verify': verify_m, 'revert': revert_m}[mode]
        arg = Path(m.group(1) or m.group(2))
        if not arg.exists():
            raise RuntimeError('Receipt not found: %s' % arg)
        receipt = json.loads(arg.read_text(encoding='utf-8-sig'))
    target = None
    if mode != 'import':
        target = _target_from_command_line(spec, cmd, receipt if mode in ('verify', 'revert') else None)
    native = Native(ue, spec, mode, stamp, target, allow_drift, include_rough, switches)
    protected_before = native.protected()
    try:
        if mode == 'plan':
            native.do_plan()
        elif mode == 'import':
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
        native.report['protectedAfter'] = native.protected()
        native.report['protectedUnchanged'] = native.report['protectedAfter'] == protected_before
        if native.map_file:
            native.report['mapSha256Final'] = sha(native.map_file)
        if not native.report['protectedUnchanged']:
            changed = sorted(k for k in set(protected_before) | set(native.report['protectedAfter'])
                             if protected_before.get(k) != native.report['protectedAfter'].get(k))
            native.report['protectedChangedFiles'] = changed
            native.report['status'] = 'FAILED_PROTECTED_HASH_MISMATCH'
        native.write()
        ue.log('HERODIAN_V4_%s %s status=%s' % (mode.upper(), native.receipt_path, native.report['status']))


if __name__ == '__main__':
    try:
        import unreal  # noqa: F401
        _native_main()
    except ImportError:
        print(json.dumps(offline_check(), indent=2, default=str))

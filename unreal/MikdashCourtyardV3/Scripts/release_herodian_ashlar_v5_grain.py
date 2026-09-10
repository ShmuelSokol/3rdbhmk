"""Herodian ashlar V5 "grain": repoint the three live V4 instances at a re-authored texture set.

WHY THIS PASS EXISTS
Frame SourceAssets/visual-review/cp05b-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png is the
only walking-height photograph of the Herodian wall. Judged against the paving in the same lighting
(cp05b-01) the wall reads as rendered plaster, and the reasons are measurable, not matters of taste:

  Scripts/measure_stone_grain.py, both albedos box-downsampled to a COMMON 2.5 px/cm (without that
  the images are authored at different px/cm and every high-frequency number is meaningless):
                                       V4 wall     approved paving      V5 wall
    mean sRGB                     0.747/0.652/0.531  0.745/0.724/0.697  0.752/0.706/0.666
    B/R                                 0.712            0.935            0.885   <- the orange, fixed
    luminance std                       0.062            0.122            0.098   <- +58 %
    |laplacian| mean                    0.0175           0.1367           0.0208  <- still 6.6x short
    boss-bevel share of the tile        1.04 %             -              4.91 %  <- 0.4 -> 1.9 cm ramp

  The laplacian row is the honest weak spot and is not hidden: at 2.5 px/cm a 1-texel laplacian
  measures ~0.4 cm features, and the paving is a PHOTOGRAPH, so most of its number is pixel-scale
  photographic tooth. V5's grit sits at 1.95 and 5.4 cm because that is the finest band surviving the
  mip actually sampled at 4 m. Per-pixel noise would raise the number without changing the image and
  would shimmer in motion, so it was not added. The frame decides whether the mid-band is enough.

  1. COLOUR. V4's palette was calibrated on kotel-wall-cleaned.png, an AI-cleaned photo derivative whose
     own PROVENANCE.md says lighting is partly baked in. Warm sunlight was therefore baked into the
     albedo and then lit by warm sunlight again in the engine. Meleke is a pale cream-honey; the
     ordinance stone on the Temple Mount courses is not orange. Corrected at the source values.
  2. MICRO-GRAIN. The approved paving carries its entire rock read in the ALBEDO -
     M_JerusalemFloorSlabs_500cm has no normal map at all, a constant 0.8 roughness and one texture
     fetch (release_jerusalem_floor_slabs.py:113-131). It is also COARSER than the wall (2.5 px/cm
     against 6.83) and still has 18x the local contrast. So the mechanism to copy is the albedo, not a
     shading node. V4's finest noise band sat below 1.2 cm, i.e. under one texel of the mip the eye
     actually samples at 4 m, so it averaged to nothing before it reached the screen. V5 adds pitting
     and grit in the 1.5-5 cm band and a 10x denser pore field, and raises roughness to the paving's
     neighbourhood so the wall stops reading glossy.
  3. THE BOSS. A normal map cannot change a silhouette or self-shadow at a grazing angle, so a boss can
     only be sold by shading gradients that SURVIVE MIPPING. V4's arris was physically right and
     visually useless: a 0.4 cm ramp is 2.7 texels at mip 0 and under one texel at mip 2 (0.586 cm),
     which is the mip selected at 4 m - hence a thin incised line instead of a step. V5 widens the ramp
     to 1.9 cm (weathered arrises really are rounded over; marked authored), raises the boss from
     1.4-2.0 cm to 3.2-4.6 cm proud (the brief's 2-5 cm), crowns the boss 0.55 cm so it BULGES, and
     deepens cavity AO. Bevel share of the tile goes 1.04 % -> 4.8 %.

WHY NO GEOMETRY AND NO PARALLAX
Geometry is not available: SM_0138_architecture_Inner_eastern_gate_wall_jamb_1 is a single box, 8
vertices / 12 triangles / zero UV layers (SourceAssets/architecture-manifest.json), and so is the whole
2,633-mesh architecture set. Nothing is instanced per block; the ashlar exists only in the triplanar
projection. Parallax/POM would need a height input on M_PBR_Tiled, which is a protected asset, so it
would mean a new master material - a second, riskier change stacked on this one, and the in-frame
control says albedo does most of the work. Recorded as the next candidate, not done here.

WHAT THIS TOUCHES - deliberately the smallest possible surface
NO MAP IS OPENED OR SAVED. The 1,156 Ashlar and 332 Trim component slot overrides on BOTH targets
already point at MI_HerodianV4_Ashlar / _Trim, so changing the TEXTURE PARAMETERS on those instances
reaches Candidate48 and Main50 at once with zero map mutation. Six new textures are imported under new
names (T_HerodianV5_*) because release_herodian_ashlar_v4.py's importer REUSES an existing asset path
without re-reading the file - regenerating the V4 PNGs in place would have silently kept the old pixels
and still passed every check.

  -V5GrainApply             hash the whole Content tree, checkpoint the three instance .uassets, import
                            the six V5 PNGs, set Albedo/Normal/ARM on MI_HerodianV4_Ashlar / _Trim /
                            _AshlarWeathered, re-assert the Nanite + InstancedStaticMeshes usage
                            overrides, save, RELOAD FROM DISK, read back, re-hash and prove nothing
                            outside the allow-list moved   -> herodian-v5-apply-<stamp>.json
  -V5GrainVerify=<receipt>  fresh-process readback only, no writes
  -V5GrainRevert=<receipt>  restore the checkpointed instance bytes, reload, read back

Commandlet (strictly serial; check Get-Process UnrealEditor,UnrealEditor-Cmd first; unique -abslog):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe" <uproject>
      -run=pythonscript -unattended -nullrhi -abslog="C:/Mikdash/Working-5.8/HerodianV5-Apply-01.log"
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_herodian_ashlar_v5_grain.py" -V5GrainApply
Offline:  python Scripts/release_herodian_ashlar_v5_grain.py    -> manifest/PNG sanity + the plan.
"""
import hashlib
import json
import re
import shutil
import struct
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
CONTENT = ROOT / 'Content'
MANIFEST = ROOT / 'SourceAssets' / 'material-review' / 'HerodianAshlarV5' / 'manifest.json'
RECEIPTS = ROOT / 'SourceAssets' / 'material-review' / 'HerodianAshlarV5'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
TEXTURE_FOLDER = '/Game/MikdashV3/MaterialReview/HerodianAshlarV4/Textures'
KINDS = ('Albedo', 'Normal', 'ARM')
REQUIRED_TILE_CM = 300.0
REQUIRED_SIZE = 2048

# variant -> (instance asset, manifest variant whose maps it uses, source-PNG prefix)
VARIANTS = {
    'Ashlar':          ('/Game/MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_Ashlar', 'Ashlar', 'T_HerodianV5_Ashlar_'),
    'Trim':            ('/Game/MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_Trim', 'Trim', 'T_HerodianV5_Trim_'),
    'AshlarWeathered': ('/Game/MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_AshlarWeathered', 'Ashlar', 'T_HerodianV5_Ashlar_'),
}

# -V5GrainTag=<tag> renames the IMPORTED assets to T_HerodianV5<tag>_*. The source PNG names never
# change - the generator always writes T_HerodianV5_*. This exists because the importer must never
# reuse an existing asset path (that is the V4 trap this whole pass was built to avoid), so a SECOND
# round of the same textures needs fresh asset names. One round = one tag; the tag goes in the receipt.
TEXTURE_TAG = ''


def asset_prefix(source_prefix):
    return source_prefix.replace('T_HerodianV5_', 'T_HerodianV5%s_' % TEXTURE_TAG, 1)

TEXTURE_SETTINGS = {
    'Albedo': dict(compression='TC_DEFAULT', srgb=True, lod_group='TEXTUREGROUP_WORLD', parameter='Albedo'),
    'Normal': dict(compression='TC_NORMALMAP', srgb=False, lod_group='TEXTUREGROUP_WORLD_NORMAL_MAP', parameter='Normal', flip_green=False),
    'ARM':    dict(compression='TC_MASKS', srgb=False, lod_group='TEXTUREGROUP_WORLD', parameter='ARM'),
}

# Everything below MUST be byte-identical before and after. The whole Content tree is hashed; only the
# paths in MUTABLE_PREFIXES are permitted to differ, and every difference is listed in the receipt.
MUTABLE_PREFIXES = (
    'MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_Ashlar.uasset',
    'MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_Trim.uasset',
    'MikdashV3/MaterialReview/HerodianAshlarV4/MI_HerodianV4_AshlarWeathered.uasset',
    'MikdashV3/MaterialReview/HerodianAshlarV4/Textures/T_HerodianV5',   # any round tag
)
# Named for the receipt so a reader can see the guard is real, not just a tree hash.
NAMED_PROTECTED = [
    '/Game/MikdashV3/Materials/PBR/M_PBR_Tiled',
    '/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_LimestoneAshlar',
    '/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_LimestoneTrim',
    '/Game/MikdashV3/MaterialReview/JerusalemFloorSlabsV1/M_JerusalemFloorSlabs_500cm',
    '/Game/MikdashV3/MaterialReview/JerusalemPavingV2/M_JerusalemPaving_500cm',
    '/Game/MikdashV3/MaterialReview/KotelStoneV2/M_KotelAshlarV2',
    '/Game/MikdashV3/MaterialReview/KeruvFriezeV2/Materials/M_KeruvFriezeV2',
    '/Game/MikdashV3/MaterialReview/KeruvFriezeV2/Materials/M_KeruvFriezeV2_Displaced',
    '/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/M_Sanctuary_gold',
]
MAPS = [
    'MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough.umap',
    'MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap',
]


def now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + 'Z'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def disk(asset, ext='uasset'):
    assert asset.startswith('/Game/') and '.' not in asset, asset
    return ROOT / 'Content' / (asset[6:] + '.' + ext)


def rel_content(path):
    return str(Path(path).relative_to(CONTENT)).replace('\\', '/')


def tree_hashes():
    """sha256 of every file under Content, keyed by forward-slash relative path."""
    out = {}
    for p in CONTENT.rglob('*'):
        if p.is_file():
            out[rel_content(p)] = sha(p)
    return out


def is_mutable(rel):
    return any(rel.startswith(prefix) or rel == prefix for prefix in MUTABLE_PREFIXES)


def png_size(path):
    head = Path(path).read_bytes()[:26]
    if head[:8] != b'\x89PNG\r\n\x1a\n' or head[12:16] != b'IHDR':
        raise RuntimeError('Not a PNG: %s' % path)
    w, h, depth, colour = struct.unpack('!2I2B', head[16:26])
    return w, h, depth, colour


def load_manifest():
    m = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    if m.get('status') != 'OFFLINE_GENERATED_NATIVE_IMPORT_PENDING':
        raise RuntimeError('Manifest status %r' % m.get('status'))
    if int(m.get('size', 0)) != REQUIRED_SIZE or float(m.get('tileCm', 0)) != REQUIRED_TILE_CM:
        raise RuntimeError('Manifest size/tileCm %s/%s, need %s/%s' % (m.get('size'), m.get('tileCm'), REQUIRED_SIZE, REQUIRED_TILE_CM))
    return m


def source_files(manifest):
    """{variant: {kind: {'path', 'sha256'}}} verified on disk. AshlarWeathered shares the Ashlar maps."""
    out = {}
    for variant, (_inst, mvar, prefix) in VARIANTS.items():
        record = manifest['variants'].get(mvar)
        if not record:
            raise RuntimeError('Manifest lacks variant ' + mvar)
        out[variant] = {}
        for kind in KINDS:
            entry = record['files'][kind]
            path = ROOT / entry['path']
            if path.name != prefix + kind + '.png':
                raise RuntimeError('Source name %s does not match prefix %s for %s/%s' % (path.name, prefix, variant, kind))
            got = sha(path)
            if got != entry['sha256']:
                raise RuntimeError('%s sha256 %s, manifest says %s' % (path, got, entry['sha256']))
            w, h, depth, colour = png_size(path)
            if (w, h, depth, colour) != (REQUIRED_SIZE, REQUIRED_SIZE, 8, 2):
                raise RuntimeError('%s is %dx%d depth %d colour %d' % (path, w, h, depth, colour))
            out[variant][kind] = {'path': path, 'sha256': got}
    return out


# ----------------------------------------------------------------------------------- offline
def offline_check():
    manifest = load_manifest()
    files = source_files(manifest)
    plan = {'status': 'OFFLINE_OK', 'manifest': str(MANIFEST.relative_to(ROOT)), 'iteration': manifest.get('iteration'),
            'generator': manifest.get('generator'), 'generatorSha256': manifest.get('generatorSha256'),
            'tileCm': manifest['tileCm'], 'size': manifest['size'],
            'instances': {v: VARIANTS[v][0] for v in VARIANTS},
            'newTextures': sorted({TEXTURE_FOLDER + '/' + asset_prefix(VARIANTS[v][2]) + k for v in VARIANTS for k in KINDS}),
            'sources': {v: {k: str(files[v][k]['path'].relative_to(ROOT)) for k in KINDS} for v in files},
            'mapsMutated': False, 'mutablePrefixes': list(MUTABLE_PREFIXES)}
    for v in ('Ashlar', 'Trim'):
        s = manifest['variants'][v]['statistics']
        plan.setdefault('statistics', {})[v] = {
            'albedoMeanSRGB': [s['albedoSRGB'][c]['mean'] for c in 'RGB'],
            'GoverR': s['albedoChroma']['GoverR_mean'], 'BoverR': s['albedoChroma']['BoverR_mean'],
            'albedoStdPerChannelMean': s['albedoStdPerChannelMean'],
            'roughness_p5_p50_p95': [s['roughness'][k] for k in ('p5', 'p50', 'p95')],
            'bossBevelPixelFraction': manifest['variants'][v]['schedule']['pixelFraction']['bossBevel'],
            'bossProudCmMinMax': manifest['variants'][v]['schedule']['bossProudCmMinMax'],
            'bossEdgeBevelCm': manifest['variants'][v]['schedule']['bossEdgeBevelCm']}
    print(json.dumps(plan, indent=2))
    return plan


# ------------------------------------------------------------------------------------ native
class Run:
    def __init__(self, u, mode):
        self.u = u
        self.ml = u.MaterialEditingLibrary
        self.assets = u.get_editor_subsystem(u.EditorAssetSubsystem)
        self.mode = mode
        self.stamp = now()
        self.path = RECEIPTS / ('herodian-v5-%s-%s.json' % (mode, self.stamp))
        self.r = {'status': 'started', 'mode': mode, 'startedUtc': datetime.now(timezone.utc).isoformat(),
                  'script': 'Scripts/release_herodian_ashlar_v5_grain.py', 'mapsOpened': [], 'mapsSaved': []}
        self.save()

    def save(self):
        RECEIPTS.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.r, indent=2) + '\n', encoding='utf-8')

    # -------------------------------------------------------------- readback
    def texture_values(self, tex):
        row = {'class': tex.get_class().get_name(), 'path': tex.get_path_name().split('.')[0], 'size': None,
               'compression': str(tex.get_editor_property('compression_settings')),
               'srgb': bool(tex.get_editor_property('srgb')),
               'lodGroup': str(tex.get_editor_property('lod_group'))}
        for getter in ('blueprint_get_size_x', 'get_size_x'):   # 5.8 exposes blueprint_get_size_x
            if hasattr(tex, getter):
                row['size'] = [int(getattr(tex, getter)()), int(getattr(tex, getter.replace('_x', '_y'))())]
                break
        for key, prop in (('flipGreenChannel', 'flip_green_channel'), ('virtualTextureStreaming', 'virtual_texture_streaming')):
            try:
                row[key] = bool(tex.get_editor_property(prop))
            except Exception:  # noqa: BLE001
                row[key] = None
        return row

    def instance_values(self, inst):
        u, ml = self.u, self.ml
        parent = inst.get_editor_property('parent')
        out = {'path': inst.get_path_name().split('.')[0],
               'parent': parent.get_path_name().split('.')[0] if parent else None, 'textures': {}, 'scalars': {}}
        for kind in KINDS:
            got = ml.get_material_instance_texture_parameter_value(inst, TEXTURE_SETTINGS[kind]['parameter'])
            out['textures'][kind] = got.get_path_name().split('.')[0] if got else None
        for name in ('TilingCm', 'NormalStrength', 'RoughnessScale', 'Metallic', 'AlbedoFlatness'):
            out['scalars'][name] = round(float(ml.get_material_instance_scalar_parameter_value(inst, name)), 6)
        tint = ml.get_material_instance_vector_parameter_value(inst, 'Tint')
        out['tint'] = [round(tint.r, 6), round(tint.g, 6), round(tint.b, 6), round(tint.a, 6)]
        for name in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            usage = getattr(u.MaterialUsage, name)
            out[name] = {'has': bool(ml.has_material_usage(inst, usage)),
                         'override': bool(ml.has_material_usage_override(inst, usage))}
        return out

    def reload(self, asset):
        """Same idiom as release_herodian_ashlar_v4.py:577-584. In-process this returns the cached
        object, so it proves the SAVE took, not that the bytes on disk are right. The genuine reopen is
        a separate -V5GrainVerify commandlet in a fresh process, which is where the receipt points."""
        try:
            self.assets.load_asset(asset)
        except Exception:  # noqa: BLE001
            pass
        return self.u.load_asset(asset)

    # -------------------------------------------------------------- apply
    def do_apply(self):
        u, ml, r = self.u, self.ml, self.r
        manifest = load_manifest()
        files = source_files(manifest)
        r['manifest'] = {'iteration': manifest.get('iteration'), 'generator': manifest.get('generator'),
                         'generatorSha256': manifest.get('generatorSha256'), 'tileCm': manifest['tileCm'], 'size': manifest['size']}

        r['stage'] = 'hashing_content_before'
        self.save()
        before = tree_hashes()
        r['contentFilesHashed'] = len(before)
        r['namedProtectedBefore'] = {a: sha(disk(a)) for a in NAMED_PROTECTED if disk(a).exists()}
        r['mapsBefore'] = {m: sha(CONTENT / m) for m in MAPS if (CONTENT / m).exists()}
        if len(r['mapsBefore']) != len(MAPS):
            raise RuntimeError('A target map is missing: %s' % [m for m in MAPS if not (CONTENT / m).exists()])

        # checkpoint the only three assets that may change
        cp = CHECKPOINT_ROOT / ('HerodianV5-%s' % self.stamp)
        cp.mkdir(parents=True, exist_ok=True)
        r['checkpoint'] = str(cp)
        r['checkpointed'] = {}
        for variant, (asset, _m, _p) in VARIANTS.items():
            src = disk(asset)
            if not src.exists():
                raise RuntimeError('Live instance missing: %s' % src)
            dst = cp / (asset.rsplit('/', 1)[1] + '.uasset')
            shutil.copy2(src, dst)
            r['checkpointed'][asset] = {'file': str(dst), 'sha256': sha(dst)}
        self.save()

        r['stage'] = 'import'
        self.save()
        textures, r['textures'] = {}, {}
        for variant in VARIANTS:
            prefix = asset_prefix(VARIANTS[variant][2])
            textures[variant] = {}
            for kind in KINDS:
                name = prefix + kind
                path = TEXTURE_FOLDER + '/' + name
                if path in r['textures']:
                    textures[variant][kind] = u.load_asset(path)
                    continue
                info = files[variant][kind]
                record = {'asset': path, 'source': str(info['path'].relative_to(ROOT)), 'sourceSha256': info['sha256']}
                if self.assets.does_asset_exist(path):
                    raise RuntimeError('%s already exists; V5 imports to fresh names on purpose so no stale '
                                       'pixels can be reused. Delete it deliberately or bump the prefix.' % path)
                task = u.AssetImportTask()
                for key, value in dict(filename=str(info['path']), destination_path=TEXTURE_FOLDER,
                                       destination_name=name, automated=True, replace_existing=False, save=False).items():
                    task.set_editor_property(key, value)
                u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                objects = list(task.get_objects())
                if len(objects) != 1 or not isinstance(objects[0], u.Texture2D):
                    raise RuntimeError('Import of %s produced %s' % (info['path'].name, [type(o).__name__ for o in objects]))
                tex = objects[0]
                cfg = TEXTURE_SETTINGS[kind]
                tex.set_editor_property('compression_settings', getattr(u.TextureCompressionSettings, cfg['compression']))
                tex.set_editor_property('srgb', bool(cfg['srgb']))
                tex.set_editor_property('lod_group', getattr(u.TextureGroup, cfg['lod_group']))
                if kind == 'Normal':
                    tex.set_editor_property('flip_green_channel', False)
                try:
                    tex.set_editor_property('virtual_texture_streaming', False)
                except Exception as err:  # noqa: BLE001
                    record['virtualTextureStreamingSet'] = 'unavailable: %r' % (err,)
                if not self.assets.save_loaded_asset(tex, only_if_is_dirty=False):
                    raise RuntimeError('save_loaded_asset failed for ' + path)
                record['readback'] = self.texture_values(tex)
                rb = record['readback']
                if rb['size'] != [REQUIRED_SIZE, REQUIRED_SIZE] or rb['srgb'] != bool(cfg['srgb']) \
                        or cfg['compression'] not in rb['compression'] or cfg['lod_group'] not in rb['lodGroup']:
                    raise RuntimeError('%s read back %s' % (path, rb))
                if kind == 'Normal' and rb['flipGreenChannel'] is not False:
                    raise RuntimeError('%s flip_green_channel %s' % (path, rb['flipGreenChannel']))
                record['uassetSha256'] = sha(disk(path))
                r['textures'][path] = record
                textures[variant][kind] = tex
            self.save()

        r['stage'] = 'repoint_instances'
        self.save()
        r['instances'] = {}
        for variant, (asset, _m, _p) in VARIANTS.items():
            inst = u.load_asset(asset)
            if not isinstance(inst, u.MaterialInstanceConstant):
                raise RuntimeError('%s is not a MaterialInstanceConstant' % asset)
            entry = {'before': self.instance_values(inst)}
            for kind in KINDS:
                param = TEXTURE_SETTINGS[kind]['parameter']
                target = textures[variant][kind]
                ml.set_material_instance_texture_parameter_value(inst, param, target)
                got = ml.get_material_instance_texture_parameter_value(inst, param)
                got_path = got.get_path_name().split('.')[0] if got else None
                want = target.get_path_name().split('.')[0]
                if got_path != want:
                    raise RuntimeError('%s.%s read back %r, want %r' % (asset, param, got_path, want))
            # the flag that silently substitutes the default material in a cooked build
            for name in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
                ml.set_material_usage_override(inst, getattr(u.MaterialUsage, name), True, True)
            ml.update_material_instance(inst)
            if not self.assets.save_loaded_asset(inst, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + asset)
            entry['afterInMemory'] = self.instance_values(inst)
            entry['uassetSha256'] = sha(disk(asset))
            r['instances'][asset] = entry
            self.save()

        r['stage'] = 'reload_and_readback'
        r['reopenNote'] = ('In-process readback. The genuine fresh-process reopen is '
                           '-V5GrainVerify=<this receipt> in a new commandlet.')
        self.save()
        for variant, (asset, _m, _p) in VARIANTS.items():
            inst = self.reload(asset)
            rb = self.instance_values(inst)
            r['instances'][asset]['afterReload'] = rb
            for kind in KINDS:
                want = TEXTURE_FOLDER + '/' + asset_prefix(VARIANTS[variant][2]) + kind
                if rb['textures'][kind] != want:
                    raise RuntimeError('%s %s reloaded as %r, want %r' % (asset, kind, rb['textures'][kind], want))
            for name in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
                if not rb[name]['has'] or not rb[name]['override']:
                    raise RuntimeError('%s lost usage %s: %s' % (asset, name, rb[name]))
            if abs(rb['scalars']['TilingCm'] - REQUIRED_TILE_CM) > 1e-4:
                raise RuntimeError('%s TilingCm %s' % (asset, rb['scalars']['TilingCm']))

        r['stage'] = 'hashing_content_after'
        self.save()
        after = tree_hashes()
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
        r['contentDiff'] = {'added': added, 'removed': removed, 'changed': changed}
        illegal = [k for k in added + removed + changed if not is_mutable(k)]
        r['illegalChanges'] = illegal
        r['namedProtectedAfter'] = {a: sha(disk(a)) for a in NAMED_PROTECTED if disk(a).exists()}
        r['mapsAfter'] = {m: sha(CONTENT / m) for m in MAPS if (CONTENT / m).exists()}
        if r['namedProtectedAfter'] != r['namedProtectedBefore']:
            raise RuntimeError('A named protected asset changed')
        if r['mapsAfter'] != r['mapsBefore']:
            raise RuntimeError('A target map changed; this pass must not mutate a map')
        if illegal:
            raise RuntimeError('Files outside the allow-list changed: %s' % illegal[:20])
        r['status'] = 'applied_visual_acceptance_pending'
        r['limits'] = ('Offline readback only. Acceptance is a frame from the cp05b-02 camera in a cooked '
                       'build. No map was opened or saved; both target maps are byte-identical.')
        return r

    # -------------------------------------------------------------- verify / revert
    def do_verify(self, receipt_path):
        r = self.r
        prior = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
        r['verifying'] = str(receipt_path)
        r['instances'] = {}
        ok = True
        for variant, (asset, _m, _p) in VARIANTS.items():
            rb = self.instance_values(self.u.load_asset(asset))
            want = {k: TEXTURE_FOLDER + '/' + asset_prefix(VARIANTS[variant][2]) + k for k in KINDS}
            match = rb['textures'] == want and all(rb[n]['has'] and rb[n]['override']
                                                   for n in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'))
            ok = ok and match
            r['instances'][asset] = {'readback': rb, 'matchesV5': match}
        r['namedProtectedNow'] = {a: sha(disk(a)) for a in NAMED_PROTECTED if disk(a).exists()}
        r['namedProtectedUnchanged'] = r['namedProtectedNow'] == prior.get('namedProtectedAfter', prior.get('namedProtectedBefore'))
        r['mapsNow'] = {m: sha(CONTENT / m) for m in MAPS if (CONTENT / m).exists()}
        r['mapsUnchanged'] = r['mapsNow'] == prior.get('mapsAfter')
        r['status'] = 'verified' if (ok and r['namedProtectedUnchanged'] and r['mapsUnchanged']) else 'verify_failed'
        return r

    def do_revert(self, receipt_path):
        u, r = self.u, self.r
        prior = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
        r['reverting'] = str(receipt_path)
        cp = prior.get('checkpointed') or {}
        if not cp:
            raise RuntimeError('Receipt has no checkpoint')
        r['restored'] = {}
        for asset, info in cp.items():
            src = Path(info['file'])
            if not src.exists():
                raise RuntimeError('Checkpoint file missing: %s' % src)
            if sha(src) != info['sha256']:
                raise RuntimeError('Checkpoint file changed since the apply: %s' % src)
            dst = disk(asset)
            shutil.copy2(src, dst)
            r['restored'][asset] = {'from': str(src), 'sha256': sha(dst)}
        # force the editor to forget the in-memory versions
        for asset in cp:
            try:
                u.EditorAssetLibrary.load_asset(asset)
            except Exception:  # noqa: BLE001
                pass
        # The bytes on disk are now the checkpointed ones; an in-process load_asset would hand back the
        # stale cached object, so the on-disk hash is the evidence here and a fresh -V5GrainVerify is the
        # confirmation. Both are recorded.
        r['restoredHashesMatchCheckpoint'] = all(r['restored'][a]['sha256'] == cp[a]['sha256'] for a in cp)
        if not r['restoredHashesMatchCheckpoint']:
            raise RuntimeError('Restored bytes do not match the checkpoint')
        r['readbackInProcess'] = {}
        for asset in cp:
            try:
                r['readbackInProcess'][asset] = self.instance_values(self.reload(asset))
            except Exception as err:  # noqa: BLE001
                r['readbackInProcess'][asset] = 'unavailable: %r' % (err,)
        r['confirmWith'] = 'Run -V5GrainVerify=<the apply receipt> in a FRESH process; matchesV5 must be false.'
        r['namedProtectedNow'] = {a: sha(disk(a)) for a in NAMED_PROTECTED if disk(a).exists()}
        r['mapsNow'] = {m: sha(CONTENT / m) for m in MAPS if (CONTENT / m).exists()}
        r['status'] = 'reverted'
        r['note'] = ('The V5 texture assets are left in place, unreferenced. Delete them separately if wanted; '
                     'leaving them makes a re-apply cheap and cannot affect rendering.')
        return r


def main():
    try:
        import unreal as u
    except ImportError:
        offline_check()
        return
    # A commandlet's flags are NOT in sys.argv - UE consumes them. They live on the engine command
    # line, exactly as release_herodian_ashlar_v4.py:1017 reads them. Getting this wrong makes the
    # script exit having silently done nothing, which is what the first run of it did.
    cmd = u.SystemLibrary.get_command_line()
    apply_m = re.search(r'-V5GrainApply(?=\s|$)', cmd)
    verify_m = re.search(r'-V5GrainVerify=(?:"([^"]+)"|([^\s]+))', cmd)
    revert_m = re.search(r'-V5GrainRevert=(?:"([^"]+)"|([^\s]+))', cmd)
    modes = [name for name, hit in (('apply', apply_m), ('verify', verify_m), ('revert', revert_m)) if hit]
    if len(modes) != 1:
        raise RuntimeError('Pass exactly one of -V5GrainApply, -V5GrainVerify=<receipt>, '
                           '-V5GrainRevert=<receipt>. Command line was: %s' % cmd)
    mode = modes[0]
    tag_m = re.search(r'-V5GrainTag=([A-Za-z0-9]{1,8})', cmd)
    if tag_m:
        globals()['TEXTURE_TAG'] = tag_m.group(1)
    arg = None
    if mode != 'apply':
        m = verify_m if mode == 'verify' else revert_m
        arg = Path(m.group(1) or m.group(2))
        if not arg.exists():
            raise RuntimeError('Receipt not found: %s' % arg)
    run = Run(u, mode)
    run.r['commandLine'] = cmd
    run.r['textureTag'] = TEXTURE_TAG
    run.r['importedAssetPrefix'] = 'T_HerodianV5%s_' % TEXTURE_TAG
    try:
        if mode == 'apply':
            run.do_apply()
        elif mode == 'verify':
            run.do_verify(arg)
        else:
            run.do_revert(arg)
    except Exception as err:  # noqa: BLE001
        run.r['status'] = 'failed'
        run.r['error'] = repr(err)
        run.r['traceback'] = traceback.format_exc()
        run.save()
        u.log_error('HERODIAN_V5_%s FAILED %s: %r' % (mode.upper(), run.path, err))
        raise
    finally:
        run.save()
    u.log('HERODIAN_V5_%s %s status=%s' % (mode.upper(), run.path, run.r['status']))


main()

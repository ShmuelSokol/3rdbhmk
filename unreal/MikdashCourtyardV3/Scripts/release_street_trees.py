"""StreetTreesV1 native apply: import, materials, LODs, and the instance swap.

WHAT THIS DOES, in one sentence: it takes the 4,265 illustrative OSM blob trees out of the
level and puts StreetTreesV1 trees on the anchors they were standing on.

Run offline (no engine on the path) it performs `offline_check()` and writes nothing. Run
inside the editor it performs the full guarded apply. Run with `--revert=<receipt>` it restores
the checkpointed map bytes, offline, with the editor closed.

    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=Scripts/release_street_trees.py
        -unattended -nullrhi -abslog=<log> -Candidate48

THE GUARD, which is not negotiable and is AGENTS.md hard rule 10:
  refuse wrong project / open game world / dirty packages  ->  hash the target map and every
  protected map  ->  copy the .umap plus __ExternalActors__ and __ExternalObjects__ into
  ReviewCheckpoints  ->  verify the copy hashes equal  ->  mutate  ->  save  ->  REOPEN  ->
  numeric readback of every instance count  ->  re-hash  ->  receipt  ->  a working -Revert.

ORDER OF OPERATIONS, and the reasons are paid for in this project's own history:

  1. Import every OBJ and PNG. A re-import puts every mesh slot back on WorldGridMaterial, so
     materials MUST follow the import and never precede it.
  2. Author the materials. Three masters in a NEW namespace - AGENTS.md hard rule 4 forbids
     rerunning a creator into an existing folder, so this does not touch JudeanFloraV1's
     masters even though the two families want the same shading.
  3. Assemble the LOD ladders and the billboard rung.
  4. Remove the blob instances, then add the new ones.

USAGE FLAGS, and this is the single most expensive lesson in the vegetation history. A material
without `bUsedWithInstancedStaticMeshes` CANNOT be used on an instanced static mesh, and a
COOKED build silently substitutes WorldGridMaterial - opaque, one-sided, no opacity mask. The
EDITOR adds the flag on the fly and merely warns, so parameter parity, save/reopen readback and
every -nullrhi receipt stay green while the shipped build draws the default material. That is
exactly how checkpoint cp05b shipped cardboard foliage. Flags are therefore set BEFORE the
first compile and read back off the SAVED asset.

There is NO `bUsedWithFoliage` in UE 5.8. Verified against
Engine/Source/Runtime/Engine/Public/Materials/Material.h, which declares
bUsedWithInstancedStaticMeshes, bUsedWithStaticMesh and bUsedWithNanite and no foliage flag at
all - foliage is drawn through instanced static mesh components, so the ISM flag IS the foliage
flag. Nanite usage is set on the BARK master only: the leaf and billboard masters are
alpha-masked, and this project's own Nanite eligibility rule deliberately excluded the
decorative foliage HISMs.

A -nullrhi run CANNOT verify a material. Acceptance is a frame from a packaged build.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SCRIPTS = ROOT / 'Scripts'
sys.path.insert(0, str(SCRIPTS))
import map_targets as mt  # noqa: E402

FAMILY = 'StreetTreesV1'
OUT = ROOT / 'SourceAssets' / 'vegetation-review' / FAMILY
MANIFEST_PATH = OUT / 'street-trees-manifest.json'
def plan_path(label='Candidate48'):
    """The plan is per target: the two maps hold the architecture in different frames and so
    have different blocker sets. See create_street_tree_placement.plan_path."""
    return OUT / ('placement-plan-%s.json' % label)
OBJ_DIR = OUT / 'obj'
TEX_DIR = OUT / 'textures'
RECEIPT_DIR = OUT
RECEIPT_PREFIX = 'release-street-trees-'

ASSET_FOLDER = '/Game/MikdashV3/Vegetation/%s' % FAMILY
MESH_FOLDER = ASSET_FOLDER + '/Meshes'
TEXTURE_FOLDER = ASSET_FOLDER + '/Textures'
MATERIAL_FOLDER = ASSET_FOLDER + '/Materials'
MASTER_PREFIX = 'M_StreetTrees_'

ACTOR_TAG = 'StreetTreesV1'
LABEL_PREFIX = 'RELEASE_StreetTrees_'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
CHECKPOINT_PREFIX = 'StreetTrees-'

# The blob family being retired. Instances are REMOVED from these components, and the
# components, actors and meshes are left in place: another pass owns those assets, and an empty
# ISM is reversible in a way that a deleted actor is not.
BLOB_MESH_SUBSTRINGS = ('JerusalemInstance_Tree_trunks', 'JerusalemInstance_Tree_crowns')

LOD_SCREEN_MINIMUM = 0.002
CULL_DISTANCE_CM = 60000.0
CULL_START_FRACTION = 0.85

MASTERS = {
    'bark': {
        'name': MASTER_PREFIX + 'Bark', 'blendMode': 'BLEND_OPAQUE', 'twoSided': False,
        'shadingModel': 'MSM_DEFAULT_LIT',
        'usageFlags': ['used_with_instanced_static_meshes', 'used_with_static_mesh',
                       'used_with_nanite'],
        'why': 'A trunk is a closed solid: the manifest proves signed volume > 0 on every bark '
               'part, so two-sided would only double the shading cost and leak light through '
               'the backfaces.',
    },
    'leaf': {
        'name': MASTER_PREFIX + 'Leaf', 'blendMode': 'BLEND_MASKED', 'twoSided': True,
        'shadingModel': 'MSM_TWO_SIDED_FOLIAGE', 'shadingModelFallback': 'MSM_DEFAULT_LIT',
        'opacityMaskClipValue': 0.5,
        'usageFlags': ['used_with_instanced_static_meshes', 'used_with_static_mesh'],
        'why': 'A leaf card rendered OPAQUE is a solid rectangle, and rendered ONE-SIDED it '
               'disappears from half the angles. Masked plus two-sided is the single thing that '
               'decides whether the mesh reads as a plant. TWO_SIDED_FOLIAGE lights the back '
               'face through the leaf, which is where the pale underside of an olive comes '
               'from; if the enum is absent the fallback is recorded, not implied.',
    },
    'billboard': {
        'name': MASTER_PREFIX + 'Billboard', 'blendMode': 'BLEND_MASKED', 'twoSided': True,
        'shadingModel': 'MSM_DEFAULT_LIT', 'opacityMaskClipValue': 0.5,
        'usageFlags': ['used_with_instanced_static_meshes', 'used_with_static_mesh'],
        'why': 'The impostor is one open quad, so it is invisible from behind unless two-sided '
               'and a solid rectangle unless masked. DEFAULT_LIT rather than foliage '
               'transmission, because running transmission over a picture of a trunk makes the '
               'far LOD glow.',
    },
}


def sha256_of(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def lod_screen_size(sphere_radius_cm, distance_cm):
    """The engine's own ComputeBoundsScreenSize, which is radius/d at a 90 degree horizontal FOV.

    NOT 2*radius/d. That error shipped once already: every threshold came out twice too large,
    so every LOD engaged at half its intended distance and the cp08 frames showed faceted
    low-poly trees at 15-30 m.
    """
    if distance_cm <= 0.0:
        return 1.0
    return max(LOD_SCREEN_MINIMUM, float(sphere_radius_cm) / float(distance_cm))


# =====================================================================================
# OFFLINE
# =====================================================================================
def offline_check(label='Candidate48'):
    """Prove the inputs are coherent without opening anything."""
    report = {'status': 'offline_check', 'checked': datetime.now(timezone.utc).isoformat(),
              'target': label}
    manifest = read_json(MANIFEST_PATH)
    plan = read_json(plan_path(label))
    report['manifestStatus'] = manifest['status']
    report['planStatus'] = plan['status']
    report['meshCount'] = manifest['meshCount']
    report['planInstances'] = plan['totalInstances']
    report['planTarget'] = plan['target']

    missing = []
    for record in manifest['meshes']:
        path = OBJ_DIR / record['file']
        if not path.exists():
            missing.append(record['file'])
        elif sha256_of(path) != record['sha256']:
            missing.append(record['file'] + ' (sha mismatch)')
    for entry in manifest['textures']:
        for key in ('leafAtlas', 'barkBaseColour', 'barkNormal', 'billboardTexture'):
            name = entry.get(key)
            if name and not (TEX_DIR / name).exists():
                missing.append(name)
    report['missingOrChangedSourceFiles'] = missing
    if missing:
        raise RuntimeError('%d generated files are missing or changed since the manifest was '
                           'written; regenerate with create_street_trees.py' % len(missing))

    proof = plan['intersectionProof']
    report['residualIntersections'] = proof['residualIntersectionsAfterPlacement']
    if proof['residualIntersectionsAfterPlacement'] != 0:
        raise RuntimeError('the placement plan does not prove zero intersections; refusing')
    species = set(b['species'] for b in plan['batches'])
    generated = set(r['species'] for r in manifest['meshes'])
    unknown = species - generated
    if unknown:
        raise RuntimeError('the plan places species with no generated mesh: %s' % sorted(unknown))
    report['speciesPlaced'] = sorted(species)

    # EVERY (species, seed variant) THE PLAN USES MUST HAVE A MESH.
    #
    # The planner draws `variantSeed` from the live SPECIES table while the meshes come from
    # whatever the last generation actually wrote, so raising a species' seed count and
    # replanning before regenerating produces a plan referencing meshes that do not exist. The
    # apply would then hit `mesh is None` and, before this check, skip those instances quietly -
    # trees missing from the level with a green receipt and nothing in the log. This project has
    # already shipped one silent substitution (WorldGridMaterial on every leaf card); it does not
    # need a second one.
    have = set()
    for record in manifest['meshes']:
        if record.get('materialRole') in ('bark', 'leaf') and record.get('lod') == 0:
            have.add((record['species'], int(record.get('variantSeed', 0))))
    wanted = set()
    for batch in plan['batches']:
        for row in batch['instances']:
            wanted.add((batch['species'], int(row[8])))
    missing = sorted(wanted - have)
    report['planVariantsUsed'] = len(wanted)
    report['planVariantsMissingMesh'] = missing
    if missing:
        raise RuntimeError('the plan uses %d (species, seed) pairs with no LOD0 mesh: %s. '
                           'Regenerate with create_street_trees.py before applying.'
                           % (len(missing), missing[:6]))
    report['ok'] = True
    return report


# =====================================================================================
# NATIVE
# =====================================================================================
class Graph(object):
    """Stock-node-only material graph builder. Port of release_vegetation_materials.Graph.

    Refuses author-written HLSL by construction: EnclosureMath.h 6b cost this project a day of
    packaging, and a Custom node in a foliage graph is how that happened.
    """

    def __init__(self, ue, material, record):
        self.ue = ue
        self.ml = ue.MaterialEditingLibrary
        self.material = material
        self.record = record

    def node(self, cls, x, y, **props):
        if cls.__name__.endswith('Custom'):
            raise RuntimeError('EnclosureMath.h 6b: no author-written HLSL in a foliage graph')
        expression = self.ml.create_material_expression(self.material, cls, x, y)
        if expression is None:
            raise RuntimeError('create_material_expression failed for ' + cls.__name__)
        for key, value in props.items():
            expression.set_editor_property(key, value)
        self.record['nodes'].append(cls.__name__)
        return expression

    def input_name(self, expression, wanted):
        names = [str(n) for n in self.ml.get_material_expression_input_names(expression)]
        for candidate in names:
            if candidate.lower() == wanted.lower():
                return candidate
        if len(names) == 1:
            return names[0]
        raise RuntimeError('%s has no input %r (inputs %s)'
                           % (expression.get_class().get_name(), wanted, names))

    def wire(self, source, output, target, wanted):
        pin = self.input_name(target, wanted)
        if not self.ml.connect_material_expressions(source, output, target, pin):
            raise RuntimeError('connection %s[%r] -> %s[%r] failed'
                               % (source.get_class().get_name(), output,
                                  target.get_class().get_name(), pin))
        self.record['connections'].append('%s.%s -> %s.%s' % (
            source.get_class().get_name(), output or 'out',
            target.get_class().get_name(), pin))
        return target

    def to_property(self, source, output, prop_name):
        prop = getattr(self.ue.MaterialProperty, prop_name)
        if not self.ml.connect_material_property(source, output, prop):
            raise RuntimeError('connect_material_property %s -> %s failed'
                               % (source.get_class().get_name(), prop_name))
        self.record['connections'].append('%s.%s -> %s'
                                          % (source.get_class().get_name(),
                                             output or 'out', prop_name))

    def binary(self, cls, a, a_out, b, b_out, x, y, **props):
        n = self.node(cls, x, y, **props)
        self.wire(a, a_out, n, 'A')
        self.wire(b, b_out, n, 'B')
        return n

    def lerp(self, a, a_out, b, b_out, alpha, alpha_out, x, y):
        n = self.node(self.ue.MaterialExpressionLinearInterpolate, x, y)
        self.wire(a, a_out, n, 'A')
        self.wire(b, b_out, n, 'B')
        self.wire(alpha, alpha_out, n, 'Alpha')
        return n

    def scalar(self, name, x, y, default):
        return self.node(self.ue.MaterialExpressionScalarParameter, x, y,
                         parameter_name=name, default_value=float(default))

    def vector(self, name, x, y, default):
        return self.node(self.ue.MaterialExpressionVectorParameter, x, y,
                         parameter_name=name,
                         default_value=self.ue.LinearColor(*default))


class Release(object):
    def __init__(self, ue, target_key, stamp):
        self.ue = ue
        self.target_key = target_key
        self.config = mt.target_config(target_key)
        self.target = self.config['map']
        self.label = self.config['key']
        self.stamp = stamp
        self.manifest = read_json(MANIFEST_PATH)
        self.plan = read_json(plan_path(self.label))
        self.receipt_path = RECEIPT_DIR / ('%s%s-%s.json' % (RECEIPT_PREFIX, self.label, stamp))
        self.checkpoint = CHECKPOINT_ROOT / ('%s%s-%s' % (CHECKPOINT_PREFIX, self.label, stamp))
        self.receipt = {'status': 'started', 'script': 'Scripts/release_street_trees.py',
                        'scriptSha256': sha256_of(Path(__file__)),
                        'target': self.label, 'map': self.target, 'stamp': stamp,
                        'offlineCheck': offline_check(self.label)}

    # -- guards ---------------------------------------------------------
    def refuse_unless_idle(self):
        ue = self.ue
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('wrong project')
        subsystem = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        if subsystem.get_game_world() is not None:
            raise RuntimeError('a PIE world is open; refusing')
        dirty = [p.get_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        dirty += [p.get_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
        if dirty:
            raise RuntimeError('unsaved packages are open: %s' % dirty[:8])
        if self.receipt_path.exists() or self.checkpoint.exists():
            raise RuntimeError('a receipt or checkpoint for this stamp already exists')

    def protected_maps(self):
        """Every map this pass must leave byte-identical."""
        maps = ['/Game/MikdashV3/Maps/Courtyard', '/Game/MikdashV3/FutureMountV1/L_FutureMount']
        for key, entry in mt.TARGETS.items():
            if entry['map'] != self.target:
                maps.append(entry['map'])
        return sorted(set(maps))

    def hash_maps(self):
        out = {}
        for asset in [self.target] + self.protected_maps():
            path = mt.disk_path(asset, 'umap')
            out[asset] = sha256_of(path) if Path(path).exists() else None
        return out

    def make_checkpoint(self):
        self.checkpoint.mkdir(parents=True, exist_ok=False)
        source = Path(mt.disk_path(self.target, 'umap'))
        destination = self.checkpoint / source.name
        shutil.copy2(source, destination)
        if sha256_of(destination) != sha256_of(source):
            raise RuntimeError('checkpoint copy does not match the map it copied')
        for folder in ('__ExternalActors__', '__ExternalObjects__'):
            src = source.parent / folder / source.stem
            if src.exists():
                shutil.copytree(src, self.checkpoint / folder / source.stem)
        self.receipt['checkpoint'] = str(self.checkpoint)

    def write_receipt(self):
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(self.receipt, indent=1) + '\n', encoding='utf-8')

    # -- assets ---------------------------------------------------------
    def import_assets(self):
        ue = self.ue
        tasks = []
        for record in self.manifest['meshes']:
            options = ue.FbxImportUI()
            options.set_editor_property('import_mesh', True)
            options.set_editor_property('import_textures', False)
            options.set_editor_property('import_materials', False)
            options.set_editor_property('import_as_skeletal', False)
            options.static_mesh_import_data.set_editor_property('combine_meshes', True)
            options.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs', True)
            options.static_mesh_import_data.set_editor_property('auto_generate_collision', False)
            task = ue.AssetImportTask()
            task.set_editor_property('filename', str(OBJ_DIR / record['file']))
            task.set_editor_property('destination_path', MESH_FOLDER)
            task.set_editor_property('destination_name', record['mesh'])
            task.set_editor_property('replace_existing', True)
            task.set_editor_property('automated', True)
            task.set_editor_property('save', False)
            task.set_editor_property('options', options)
            tasks.append(task)
        for entry in self.manifest['textures']:
            for key in ('leafAtlas', 'barkBaseColour', 'barkNormal', 'billboardTexture'):
                name = entry.get(key)
                if not name:
                    continue
                task = ue.AssetImportTask()
                task.set_editor_property('filename', str(TEX_DIR / name))
                task.set_editor_property('destination_path', TEXTURE_FOLDER)
                task.set_editor_property('replace_existing', True)
                task.set_editor_property('automated', True)
                task.set_editor_property('save', False)
                tasks.append(task)
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

        missing = []
        for record in self.manifest['meshes']:
            if ue.EditorAssetLibrary.load_asset('%s/%s' % (MESH_FOLDER, record['mesh'])) is None:
                missing.append(record['mesh'])
        self.receipt['import'] = {'meshes': len(self.manifest['meshes']), 'missing': missing}
        if missing:
            raise RuntimeError('%d meshes failed to import' % len(missing))

        # THE ATLAS TRAP: a WRAPPING atlas bleeds the neighbouring cell across the alpha edge
        # and puts half a leaf on the far side of every card. Atlases are CLAMP.
        clamped = 0
        for entry in self.manifest['textures']:
            for key in ('leafAtlas', 'billboardTexture'):
                name = entry.get(key)
                if not name:
                    continue
                asset = ue.EditorAssetLibrary.load_asset(
                    '%s/%s' % (TEXTURE_FOLDER, Path(name).stem))
                if asset is None:
                    continue
                asset.set_editor_property('address_x', ue.TextureAddress.TA_CLAMP)
                asset.set_editor_property('address_y', ue.TextureAddress.TA_CLAMP)
                clamped += 1
            normal = entry.get('barkNormal')
            if normal:
                asset = ue.EditorAssetLibrary.load_asset(
                    '%s/%s' % (TEXTURE_FOLDER, Path(normal).stem))
                if asset is not None:
                    asset.set_editor_property('compression_settings',
                                              ue.TextureCompressionSettings.TC_NORMALMAP)
                    asset.set_editor_property('srgb', False)
        self.receipt['texturesClamped'] = clamped

        # THE SAVE TRAP, and it cost a whole cook and a whole set of frames to find. The import
        # tasks above set save=False, and nothing ever saved the imported textures. Meshes,
        # masters and material instances were each saved explicitly, so every in-editor check
        # passed: the atlases were live in the very session that imported them, `texturesClamped`
        # counted 12, and set_material_instance_texture_parameter_value bound them happily. But
        # the packages were never written to disk. The saved material instances therefore
        # referenced texture packages that did not exist, the cook resolved them to nothing, and
        # every leaf card rendered as an opaque near-black rectangle - see
        # trees01b-A1-west-gate-approach-into-old-city.png, which is indistinguishable from the
        # empty-graph bug that preceded it. A texture that loads inside the authoring session is
        # NOT a texture that shipped. Save it, then prove the .uasset is on disk.
        saved, missing_textures = [], []
        for entry in self.manifest['textures']:
            for key in ('leafAtlas', 'barkBaseColour', 'barkNormal', 'billboardTexture'):
                name = entry.get(key)
                if not name:
                    continue
                package = '%s/%s' % (TEXTURE_FOLDER, Path(name).stem)
                if ue.EditorAssetLibrary.load_asset(package) is None:
                    missing_textures.append(package + ' (did not import)')
                    continue
                ue.EditorAssetLibrary.save_asset(package, only_if_is_dirty=False)
                on_disk = ROOT / 'Content' / (package.replace('/Game/', '') + '.uasset')
                if not on_disk.is_file():
                    missing_textures.append(package + ' (saved but no .uasset on disk)')
                    continue
                saved.append(package)
        self.receipt['texturesSaved'] = len(saved)
        self.receipt['texturesMissing'] = missing_textures
        if missing_textures:
            raise RuntimeError(
                '%d StreetTrees textures are not on disk after import. The material instances '
                'would reference packages the cook cannot resolve, and every masked card would '
                'render as a solid rectangle: %s'
                % (len(missing_textures), ', '.join(missing_textures[:6])))

    def build_masters(self):
        """Three masters: flags set BEFORE the first compile, THEN a real graph wired.

        THE BUG THIS EXISTS FOR, and it took a frame to find it. The first version of this
        method set blend mode, two-sidedness, shading model, clip value and the usage flags,
        saved the asset, and stopped. It never created a single expression. A BLEND_MASKED
        material with nothing connected to OpacityMask is opaque EVERYWHERE, and an unconnected
        BaseColor is black - so every leaf card rendered as a solid near-black rectangle, and
        `trees01-A1-west-gate-approach-into-old-city.png` shows exactly that. The material
        instances then set a `LeafAtlas` parameter that did not exist on the parent, so the
        atlas silently bound to nothing.

        Nothing caught it earlier because nothing could: the cook log was clean (no
        substitution - the material existed and compiled), the usage flags read back true, and
        `-nullrhi` cannot draw a pixel. This is `nullrhi-cannot-verify-materials` exactly:
        parameter parity is not visual acceptance.

        The graph below is a port of release_vegetation_materials.build_master, stock nodes
        only. The one line that matters is `to_property(atlas, 'A', 'MP_OPACITY_MASK')`.
        """
        ue = self.ue
        tools = ue.AssetToolsHelpers.get_asset_tools()
        ml = ue.MaterialEditingLibrary
        records = {}
        for role, cfg in MASTERS.items():
            path = '%s/%s' % (MATERIAL_FOLDER, cfg['name'])
            # ALWAYS rebuild fresh. Re-authoring into an existing Material SUPERIMPOSES the old
            # graph on the new one - release_vegetation_materials.py saw 35 expressions where 24
            # were created, with two LeafAtlas samplers and duplicate parameter names, and that
            # superimposed material is what cp05b cooked into solid opaque cards. A fresh asset
            # is the only way to be certain the graph is what was authored; the instances are
            # re-parented immediately afterwards by assign_materials().
            existing = ue.EditorAssetLibrary.load_asset(path)
            if existing is not None:
                if not isinstance(existing, ue.Material):
                    raise RuntimeError('existing asset at %s is not a Material' % path)
                if not ue.EditorAssetLibrary.delete_asset(path):
                    raise RuntimeError('delete_asset failed for ' + path)
            material = tools.create_asset(cfg['name'], MATERIAL_FOLDER, ue.Material,
                                          ue.MaterialFactoryNew())
            if not isinstance(material, ue.Material):
                raise RuntimeError('material factory failed for ' + path)

            record = {'path': path, 'role': role, 'why': cfg['why']}
            blend = getattr(ue.BlendMode, cfg['blendMode'])
            material.set_editor_property('blend_mode', blend)
            material.set_editor_property('two_sided', bool(cfg['twoSided']))
            wanted = cfg['shadingModel']
            shading = getattr(ue.MaterialShadingModel, wanted, None)
            if shading is None:
                wanted = cfg.get('shadingModelFallback', 'MSM_DEFAULT_LIT')
                shading = getattr(ue.MaterialShadingModel, wanted)
                record['shadingModelIsFallback'] = True
            material.set_editor_property('shading_model', shading)
            record['shadingModelApplied'] = wanted
            if 'opacityMaskClipValue' in cfg:
                material.set_editor_property('opacity_mask_clip_value',
                                             float(cfg['opacityMaskClipValue']))

            usage = {}
            for flag in cfg['usageFlags']:
                try:
                    material.set_editor_property(flag, True)
                    usage[flag] = bool(material.get_editor_property(flag))
                except Exception as error:                              # noqa: BLE001
                    usage[flag] = 'UNAVAILABLE: %r' % (error,)
            record['usageFlags'] = usage
            bad = [k for k, v in usage.items() if v is not True]
            if bad:
                raise RuntimeError('%s could not set usage flags %s' % (cfg['name'], bad))

            # ---- THE GRAPH. Flags are already set, so the first compile is the masked,
            # two-sided one and no stale shader map has to be fought afterwards.
            record['nodes'] = []
            record['connections'] = []
            g = Graph(ue, material, record)
            colour_sampler = ue.MaterialSamplerType.SAMPLERTYPE_COLOR
            normal_sampler = ue.MaterialSamplerType.SAMPLERTYPE_NORMAL

            if role == 'bark':
                exemplar = next(e for e in self.manifest['textures'] if e.get('barkNormal'))
                defaults = {key: ue.load_asset('%s/%s' % (TEXTURE_FOLDER, Path(exemplar[key]).stem))
                            for key in ('barkBaseColour', 'barkNormal')}
                if any(value is None for value in defaults.values()):
                    raise RuntimeError('Bark master requires valid default color and normal textures')
                if (defaults['barkNormal'].get_editor_property('srgb') or
                        defaults['barkNormal'].get_editor_property('compression_settings') !=
                        ue.TextureCompressionSettings.TC_NORMALMAP):
                    raise RuntimeError('Bark default normal texture has incorrect compression or sRGB')
                base = g.node(ue.MaterialExpressionTextureSampleParameter2D, -1600, -300,
                              parameter_name='BarkBaseColour', sampler_type=colour_sampler,
                              texture=defaults['barkBaseColour'])
                g.to_property(base, 'RGB', 'MP_BASE_COLOR')
                normal = g.node(ue.MaterialExpressionTextureSampleParameter2D, -1600, 120,
                                parameter_name='BarkNormal', sampler_type=normal_sampler,
                                texture=defaults['barkNormal'])
                g.to_property(normal, 'RGB', 'MP_NORMAL')
                g.to_property(g.scalar('Roughness', -900, 420, 0.85), '', 'MP_ROUGHNESS')
                g.to_property(g.scalar('Specular', -900, 520, 0.25), '', 'MP_SPECULAR')
                g.to_property(g.node(ue.MaterialExpressionConstant, -900, 620, r=0.0),
                              '', 'MP_METALLIC')
            else:
                leaf = role == 'leaf'
                atlas_param = 'LeafAtlas' if leaf else 'BillboardAtlas'
                tints = ('LeafTintA', 'LeafTintB') if leaf else ('BillboardTintA',
                                                                 'BillboardTintB')
                atlas = g.node(ue.MaterialExpressionTextureSampleParameter2D, -1600, -300,
                               parameter_name=atlas_param, sampler_type=colour_sampler)
                # THE ONE THAT MATTERS. Without this the card is a solid rectangle however
                # correct every flag is, which is exactly what the first trees01 A1 frame showed.
                g.to_property(atlas, 'A', 'MP_OPACITY_MASK')

                per_instance = g.node(ue.MaterialExpressionPerInstanceRandom, -1500, 380)
                tint_a = g.vector(tints[0], -1500, 520, (1.0, 1.0, 1.0, 1.0))
                tint_b = g.vector(tints[1], -1500, 660, (1.0, 1.0, 1.0, 1.0))
                tint = g.lerp(tint_a, '', tint_b, '', per_instance, '', -1200, 560)
                tinted = g.binary(ue.MaterialExpressionMultiply, atlas, 'RGB', tint, '', -950, 0)
                g.to_property(tinted, '', 'MP_BASE_COLOR')
                g.to_property(g.scalar('Roughness', -900, 420, 0.7), '', 'MP_ROUGHNESS')
                g.to_property(g.scalar('Specular', -900, 520, 0.2), '', 'MP_SPECULAR')
                g.to_property(g.node(ue.MaterialExpressionConstant, -900, 620, r=0.0),
                              '', 'MP_METALLIC')
                if leaf and record.get('shadingModelApplied') == 'MSM_TWO_SIDED_FOLIAGE':
                    sub = g.vector('SubsurfaceTint', -1500, 800, (0.45, 0.55, 0.35, 1.0))
                    g.to_property(sub, '', 'MP_SUBSURFACE_COLOR')

            ml.recompile_material(material)

            # ---- THE ASSERTION WHOSE ABSENCE LET AN EMPTY GRAPH SHIP.
            expressions = len(ml.get_material_expressions(material))
            record['expressionCount'] = expressions
            if expressions == 0:
                raise RuntimeError('%s compiled with an EMPTY graph' % cfg['name'])
            if cfg['blendMode'] == 'BLEND_MASKED' and not any(
                    'MP_OPACITY_MASK' in c for c in record['connections']):
                raise RuntimeError('%s is BLEND_MASKED with nothing wired to OpacityMask; every '
                                   'card would render as a solid rectangle' % cfg['name'])
            records[role] = record
            ue.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)

        # read the flags back off the SAVED assets, which is the only reading that counts
        for role, record in records.items():
            ue.EditorAssetLibrary.load_asset(record['path'])
            material = ue.EditorAssetLibrary.load_asset(record['path'])
            record['readback'] = {
                'blendMode': str(material.get_editor_property('blend_mode')),
                'twoSided': bool(material.get_editor_property('two_sided')),
                'usageFlags': dict((f, bool(material.get_editor_property(f)))
                                   for f in MASTERS[role]['usageFlags']),
            }
        self.receipt['masters'] = records
        return records

    def assign_materials(self):
        """One material instance per species and role, pointed at that species' textures."""
        ue = self.ue
        tools = ue.AssetToolsHelpers.get_asset_tools()
        instances = {}
        for entry in self.manifest['textures']:
            key = entry['species']
            for role, texture_key, parameter in (('bark', 'barkBaseColour', 'BarkBaseColour'),
                                                 ('leaf', 'leafAtlas', 'LeafAtlas'),
                                                 ('billboard', 'billboardTexture',
                                                  'BillboardAtlas')):
                name = 'MI_%s_%s_%s' % (FAMILY, key, role.capitalize())
                path = '%s/%s' % (MATERIAL_FOLDER, name)
                instance = ue.EditorAssetLibrary.load_asset(path)
                if instance is None:
                    instance = tools.create_asset(name, MATERIAL_FOLDER,
                                                  ue.MaterialInstanceConstant,
                                                  ue.MaterialInstanceConstantFactoryNew())
                parent = ue.EditorAssetLibrary.load_asset(
                    '%s/%s' % (MATERIAL_FOLDER, MASTERS[role]['name']))
                instance.set_editor_property('parent', parent)
                texture_name = entry.get(texture_key)
                if texture_name:
                    texture = ue.EditorAssetLibrary.load_asset(
                        '%s/%s' % (TEXTURE_FOLDER, Path(texture_name).stem))
                    if texture is not None:
                        ue.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                            instance, parameter, texture)
                if role == 'bark':
                    normal = ue.load_asset('%s/%s' % (TEXTURE_FOLDER, Path(entry['barkNormal']).stem))
                    if normal is None:
                        raise RuntimeError('Missing bark normal for ' + key)
                    ue.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                        instance, 'BarkNormal', normal)
                    if ue.MaterialEditingLibrary.get_material_instance_texture_parameter_value(
                            instance, 'BarkNormal') != normal:
                        raise RuntimeError('Bark normal parameter assignment failed for ' + key)
                ue.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
                instances['%s/%s' % (key, role)] = path

        assigned, errors = 0, []
        for record in self.manifest['meshes']:
            mesh = ue.EditorAssetLibrary.load_asset('%s/%s' % (MESH_FOLDER, record['mesh']))
            if mesh is None:
                errors.append(record['mesh'])
                continue
            role = record['materialRole']
            path = instances.get('%s/%s' % (record['species'], role))
            if path is None:
                continue
            material = ue.EditorAssetLibrary.load_asset(path)
            # THE STRUCT-COPY TRAP, and it is what actually put cardboard in three cooks.
            # `get_editor_property('static_materials')` hands back a COPY of the array, and
            # indexing it yields a COPY of each StaticMaterial struct. Calling
            # set_editor_property on that temporary changed nothing that survived, so
            # `set_editor_property('static_materials', slots)` wrote the ORIGINAL array back,
            # save_asset saved it faithfully, and `assigned += 1` recorded a success. Every mesh
            # kept /Engine/EngineMaterials/WorldGridMaterial - an opaque grey default - which is
            # why every leaf card AND every trunk rendered as the same flat dark shape while the
            # masters, the instances, the atlases and the UVs were all provably correct.
            # Rebuild the array from FRESH structs instead of mutating copies.
            slots = mesh.get_editor_property('static_materials')
            rebuilt = []
            for slot in slots:
                entry = ue.StaticMaterial()
                entry.set_editor_property('material_interface', material)
                for name_property in ('material_slot_name', 'imported_material_slot_name'):
                    try:
                        entry.set_editor_property(
                            name_property, slot.get_editor_property(name_property))
                    except Exception:                                   # noqa: BLE001
                        pass
                rebuilt.append(entry)
            mesh.set_editor_property('static_materials', rebuilt)
            ue.EditorAssetLibrary.save_asset('%s/%s' % (MESH_FOLDER, record['mesh']),
                                             only_if_is_dirty=False)
            # READ THE SLOT BACK. A counter is not a material: the previous version reported
            # meshSlotsAssigned 138 and meshSlotErrors [] across three cooks while every mesh
            # was still on the engine default. Assert the BINDING, not the loop iteration.
            check = ue.EditorAssetLibrary.load_asset('%s/%s' % (MESH_FOLDER, record['mesh']))
            wanted = material.get_path_name()
            bound = [s.get_editor_property('material_interface')
                     for s in check.get_editor_property('static_materials')]
            wrong = [(b.get_path_name() if b else 'None') for b in bound
                     if b is None or b.get_path_name() != wanted]
            if not bound:
                wrong = ['no material slots at all']
            if wrong:
                errors.append('%s kept %s instead of %s'
                              % (record['mesh'], wrong[0], wanted))
                continue
            assigned += 1
        self.receipt['materialInstances'] = len(instances)
        self.receipt['meshSlotsAssigned'] = assigned
        self.receipt['meshSlotErrors'] = errors
        if errors:
            raise RuntimeError('%d meshes could not take a material' % len(errors))

    # -- the swap -------------------------------------------------------
    def clear_blob_instances(self, world):
        """Empty the OSM tree ISM components. Actors, components and meshes are left alone."""
        ue = self.ue
        cleared = []
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
        for actor in actors:
            for component in actor.get_components_by_class(ue.InstancedStaticMeshComponent):
                mesh = component.get_editor_property('static_mesh')
                name = mesh.get_path_name() if mesh else ''
                if not any(token in name for token in BLOB_MESH_SUBSTRINGS):
                    continue
                before = int(component.get_instance_count())
                component.modify()
                component.clear_instances()
                cleared.append({'actor': actor.get_actor_label(), 'mesh': name,
                                'instancesBefore': before,
                                'instancesAfter': int(component.get_instance_count())})
        self.receipt['blobInstancesCleared'] = cleared
        total = sum(row['instancesBefore'] for row in cleared)
        self.receipt['blobInstancesClearedTotal'] = total
        if not cleared:
            raise RuntimeError('no OSM tree ISM component matched %s; the blob trees would stay '
                               'in the level beside the new ones' % (BLOB_MESH_SUBSTRINGS,))
        return cleared

    def new_hism(self, actor):
        """A PERSISTENT hierarchical instanced component, created the editor's own way.

        THE BUG THIS EXISTS FOR, paid for in receipt
        release-street-trees-Candidate48-20260916T003800086526Z.json: constructing
        `ue.HierarchicalInstancedStaticMeshComponent(actor)` yields a component that works
        perfectly in the running editor - instances add, counts read back, the save reports
        success - and that the level NEVER OWNS. Reopen the map and every component is there
        with zero instances. All 7,288 placed instances evaporated, and because the blob
        clearing had already been saved, the map was left with no trees of either kind.

        UE 5.8 declares AActor::AddComponentByClass with meta=(ScriptNoExport,
        BlueprintInternalUseOnly), so it is deliberately absent from the Python bindings and
        `actor.add_component_by_class` raises AttributeError. The editor's subobject path is
        the only route to a component the map serialises. This is release_vegetation.new_hism
        (line 755), which solved the identical failure for the hillside flora, with the same
        three ownership verifications before a single instance is added.

        The save/reopen/readback guard is what caught this. It is the whole reason it exists.
        """
        ue = self.ue
        subsystem = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
        library = ue.SubobjectDataBlueprintFunctionLibrary
        handles = subsystem.k2_gather_subobject_data_for_instance(actor)
        parent = next((handle for handle in handles
                       if library.get_associated_object(library.get_data(handle)) == actor), None)
        if parent is None:
            raise RuntimeError('editor actor subobject handle missing for ' + actor.get_actor_label())
        params = ue.AddNewSubobjectParams(
            parent_handle=parent,
            new_class=ue.HierarchicalInstancedStaticMeshComponent,
            blueprint_context=None, conform_transform_to_parent=True)
        handle, reason = subsystem.add_new_subobject(params)
        if not library.is_handle_valid(handle):
            raise RuntimeError('persistent HISM creation failed: ' + str(reason))
        data = library.get_data(handle)
        component = library.get_associated_object(data)
        if not isinstance(component, ue.HierarchicalInstancedStaticMeshComponent):
            raise RuntimeError('subobject is a %s, not a HISM' % type(component).__name__)
        if component.get_owner() != actor or not library.is_instanced_component(data):
            raise RuntimeError('HISM ownership/instance creation not verified')
        if component not in actor.get_components_by_class(
                ue.HierarchicalInstancedStaticMeshComponent):
            raise RuntimeError('HISM absent from the actor component readback')
        return component

    def place(self, world):
        ue = self.ue
        by_mesh = {}
        for batch in self.plan['batches']:
            for row in batch['instances']:
                variant = int(row[8])
                mesh = 'SM_%s_%s_S%d_L0_%s' % (FAMILY, batch['species'], variant, 'Bark')
                by_mesh.setdefault((batch['species'], variant), []).append(row)

        placed = []
        subsystem = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        for (species, variant), rows in sorted(by_mesh.items()):
            for role in ('Bark', 'Leaf'):
                mesh_name = 'SM_%s_%s_S%d_L0_%s' % (FAMILY, species, variant, role)
                mesh = ue.EditorAssetLibrary.load_asset('%s/%s' % (MESH_FOLDER, mesh_name))
                if mesh is None:
                    # NEVER skip quietly: a missing mesh here means instances silently vanish
                    # from the level while the receipt still reports success. offline_check()
                    # proves this cannot happen before the apply starts; if it happens anyway,
                    # the import is broken and the run must stop.
                    raise RuntimeError('%s is missing after import; refusing to place %d '
                                       'instances into nothing' % (mesh_name, len(rows)))
                label = '%s%s_S%d_%s' % (LABEL_PREFIX, species, variant, role)
                actor = subsystem.spawn_actor_from_class(ue.Actor, ue.Vector(0, 0, 0))
                actor.set_actor_label(label)
                actor.tags = [ACTOR_TAG]
                component = self.new_hism(actor)
                component.set_editor_property('static_mesh', mesh)
                component.set_editor_property('instance_start_cull_distance',
                                              int(CULL_DISTANCE_CM * CULL_START_FRACTION))
                component.set_editor_property('instance_end_cull_distance',
                                              int(CULL_DISTANCE_CM))
                transforms = []
                for row in rows:
                    transforms.append(ue.Transform(
                        ue.Vector(row[0], row[1], row[2]),
                        ue.Rotator(pitch=row[4], yaw=row[3], roll=row[5]),
                        ue.Vector(row[6], row[6], row[7])))
                component.add_instances(transforms, False)
                placed.append({'label': label, 'mesh': mesh_name, 'added': len(transforms)})
        self.receipt['placed'] = placed
        self.receipt['placedTotal'] = sum(row['added'] for row in placed)
        return placed

    def readback(self, placed):
        """After save AND reopen, every component must still report what it was given."""
        ue = self.ue
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()
        by_label = dict((a.get_actor_label(), a) for a in actors)
        problems = []
        for entry in placed:
            actor = by_label.get(entry['label'])
            if actor is None:
                problems.append('%s is gone after reopen' % entry['label'])
                continue
            components = actor.get_components_by_class(ue.InstancedStaticMeshComponent)
            count = sum(int(c.get_instance_count()) for c in components)
            entry['reopenedInstances'] = count
            if count != entry['added']:
                problems.append('%s reopened with %d of %d instances'
                                % (entry['label'], count, entry['added']))
        self.receipt['readbackProblems'] = problems
        if problems:
            raise RuntimeError('instance readback failed: %s' % problems[:4])


def apply(target_key, materials_only=False):
    """Full apply, or `-StreetTreesMaterialsOnly`: rebuild the masters and reassign the mesh
    slots WITHOUT touching a map.

    Masters, material instances and mesh material slots are ASSETS. Re-running the FULL apply to
    fix a material would clear an already-empty blob family and then place a SECOND 7,288
    instances on top of the first - the trees would silently double. That is why this mode
    exists, and why it asserts every map is byte-identical afterwards.
    """
    import unreal as ue
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run = Release(ue, target_key, stamp)
    try:
        run.refuse_unless_idle()
        hashes = run.hash_maps()
        run.receipt['mapHashesBefore'] = hashes
        # map_targets.restore_checkpoint() reads exactly two top-level keys - `map` and
        # `mapSha256Before` - and refuses with "records no map / mapSha256Before to restore to"
        # without them. The first Candidate48 apply recorded only the `mapHashesBefore` dict, so
        # its documented `--revert=<receipt>` did not work and the failed map had to be restored
        # by hand. A revert that has never been exercised is not a revert.
        run.receipt['mapSha256Before'] = hashes.get(run.target)
        run.receipt['materialsOnly'] = bool(materials_only)
        if not materials_only:
            run.make_checkpoint()
        run.write_receipt()

        run.import_assets()
        run.build_masters()
        run.assign_materials()

        if materials_only:
            after = run.hash_maps()
            run.receipt['mapHashesAfter'] = after
            unchanged = all(hashes.get(k) == after.get(k) for k in hashes)
            run.receipt['allMapsUnchanged'] = unchanged
            if not unchanged:
                raise RuntimeError('a materials-only pass changed a map; refusing')
            run.receipt['status'] = 'materials_rebuilt_maps_untouched_visual_acceptance_pending'
            return run.receipt

        ue.EditorLoadingAndSavingUtils.load_map(run.target)
        world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        run.clear_blob_instances(world)
        placed = run.place(world)

        ue.EditorLoadingAndSavingUtils.save_map(world, run.target)
        run.receipt['mapSha256AfterSave'] = sha256_of(mt.disk_path(run.target, 'umap'))
        ue.EditorLoadingAndSavingUtils.load_map(run.target)
        run.readback(placed)

        after = run.hash_maps()
        run.receipt['mapHashesAfter'] = after
        unchanged = True
        for asset in run.protected_maps():
            if run.receipt['mapHashesBefore'].get(asset) != after.get(asset):
                unchanged = False
        run.receipt['protectedMapsUnchanged'] = unchanged
        if not unchanged:
            raise RuntimeError('a protected map changed')
        run.receipt['status'] = 'saved_reopened_readback_ok_visual_acceptance_pending'
        run.receipt['limitations'] = [
            'A -nullrhi run cannot verify a material. Visual acceptance requires a frame from a '
            'packaged build; until one exists this receipt claims geometry and flags only.',
            'Old City building shells were not blockers in the placement plan; see the plan.',
        ]
    except Exception as error:                                          # noqa: BLE001
        run.receipt['status'] = 'FAILED'
        run.receipt['error'] = repr(error)
        raise
    finally:
        run.write_receipt()
    return run.receipt


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _main():
    import unreal as ue
    target = mt.target_from_command_line()
    command_line = str(ue.SystemLibrary.get_command_line())
    materials_only = '-StreetTreesMaterialsOnly' in command_line
    receipt = apply(target, materials_only=materials_only)
    print('LogPython: street trees %s: %s (materialsOnly=%s)'
          % (receipt['status'], receipt.get('placedTotal'), materials_only))


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        revert = mt.revert_from_command_line(sys.argv)
        if revert:
            print(json.dumps(mt.restore_checkpoint(revert['receipt'], revert['dryRun'], ROOT),
                             indent=1))
        else:
            print(json.dumps(offline_check(), indent=1))

"""Guarded release of the Mikdash surface-wear pass into the combined Walkthrough map.

Places the authored wear decals as ADecalActors, builds the one deferred-decal master
material and its instances, creates the quantised meleke stone-variant instances, applies
them as per-component slot-0 overrides, and spawns one AMikdashSurfaceDetail to budget and
fade the set at run time.

Every number comes from SourceAssets/surface-review/surface-detail.json (written by
Scripts/create_decals.py, which derives it from architecture-manifest.json) and from
Scripts/release_surface_detail.spec.json, so a human can review the whole plan before this
is run.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_surface_detail.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-SurfaceDetail-01.log"

Optional switches (read from the engine command line):
  -SurfaceStages=assets OR -SurfaceStages=decals,manager
        comma-separated subset of the four stages. Default: assets only; fresh-process decals,manager follows verified asset receipt.
        assets   import textures, build the master material and the instances
        decals   place the decal actors
        stone    create and apply the meleke stone variants
        manager  spawn AMikdashSurfaceDetail
  -SurfaceRevert
        destroy every actor this pass placed and clear every component override it
        applied, from the receipt of the last run. Created assets are left on disk;
        removing them is a separate, manual decision.

Offline, with no engine at all:
  python Scripts/release_surface_detail.py
        runs offline_check() and prints it. This is what CI and scripts/verify.py can
        exercise; it reads the plan and the spec and reconciles them without touching
        anything.

WHAT THIS SCRIPT IS ALLOWED TO CHANGE
  * new assets under /Game/MikdashV3/SurfaceDetailV2 (textures, one master material,
    material instances)
  * new ADecalActor actors and one AMikdashSurfaceDetail actor in the target map
  * slot-0 material overrides on StaticMeshComponents whose current slot-0 material is
    one of the three stone PBR instances

WHAT IT MUST NEVER CHANGE, AND HOW THAT IS ENFORCED
  * No existing actor's transform, mesh list or world bounds. A full numeric snapshot is
    taken before any mutation and compared again before the save AND after the reopen; a
    single difference aborts the run with the map unsaved.
  * No shared material asset. On 2026-09-07 a pass meant to rebalance the sanctuary
    flattened the frieze wall relief by editing a shared parent, and had to be reverted
    from a checkpoint. Since then the rule is absolute: this script creates
    MaterialInstanceConstants and never opens a parent. M_PBR_Tiled in particular is the
    shared parent of BOTH the limestone instances and the gold instances, so editing it
    would move the gold. Every path in the spec's protectedMaterials is SHA-256'd before
    and after and must be byte-identical; nothing under protectedMaterialPrefixes (the
    Kotel ashlar and photo surfaces) is written at all.
  * No geometry is moved or deleted. destroy_actor is only ever called on an actor this
    run spawned in this process, tracked by handle, not by label.

UE 5.8 facts this script depends on
  * MaterialEditingLibrary.set_material_instance_{scalar,vector}_parameter_value returns a
    bResult that is never assigned and is therefore ALWAYS false. Only the readback
    decides. The struct-array fallback must stamp Association=GlobalParameter and
    Index=-1; a Python-default MaterialParameterInfo carries LayerParameter/0 and the
    global lookup would never find it.
  * Desaturation's first input pin is named 'None', not 'Input'.
  * Clamp's first input pin is also named 'None'.
  * Noise's position pin is 'World Position'.
  * TextureSampleParameter2D's UV pin is 'UVs', not 'UV'.
"""
import hashlib
import json

import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_surface_detail.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
import sys
sys.path.insert(0, str(ROOT / 'Scripts'))
STAGE_ORDER = ('assets', 'decals', 'manager')
DEFAULT_STAGES = ('assets',)


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so offline_check() runs anywhere.
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def load_plan(spec):
    path = ROOT / spec['plan']
    plan = json.loads(path.read_text(encoding='utf-8'))
    if plan['status'] != spec['planStatusRequired']:
        raise RuntimeError('Plan status is %r, expected %r' % (plan['status'], spec['planStatusRequired']))
    # Preserve source manifest bytes; namespace rebasing is explicit and receipted.
    source = spec['sourceNamespace']
    if plan['namespace'] != source:
        raise RuntimeError('Unexpected source namespace')
    def rebase(value):
        if isinstance(value, str):
            return spec['namespace'] + value[len(source):] if value.startswith(source) else value
        if isinstance(value, list):
            return [rebase(v) for v in value]
        if isinstance(value, dict):
            return {k: rebase(v) for k, v in value.items()}
        return value
    return rebase(plan)


def normalise_stages(stages):
    if isinstance(stages, str):
        stages = [part.strip() for part in stages.split(',')]
    chosen = [s for s in STAGE_ORDER if s in set(stages)]
    unknown = sorted(set(stages) - set(STAGE_ORDER) - {''})
    if unknown:
        raise ValueError('Unknown stage(s): %s' % unknown)
    if not chosen:
        raise ValueError('No stage selected')
    return tuple(chosen)


def hash32(value):
    """The same Murmur3 finalizer as MikdashWear::Hash32, so the variant a component gets
    here is the variant the offline planner would have predicted for it."""
    value &= 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x85EBCA6B) & 0xFFFFFFFF
    value ^= value >> 13
    value = (value * 0xC2B2AE35) & 0xFFFFFFFF
    value ^= value >> 16
    return value


def stable_key(text):
    """A stable 32-bit key for a component path. Deliberately NOT Python's hash(), which is
    salted per process and would hand the same component a different variant every run."""
    return int.from_bytes(hashlib.sha256(text.encode('utf-8')).digest()[:4], 'big')


def age_tier_for(plan, x, y):
    radius = max(abs(float(x)), abs(float(y)))
    for tier in plan['ageTiers']:
        if radius >= tier['minRadiusCm']:
            return tier
    return plan['ageTiers'][-1]


def variant_for_component(plan, family_id, component_path, x, y):
    """(instance name, tier id). Pure: a component path and a position decide everything."""
    family = next(f for f in plan['stoneVariation']['families'] if f['id'] == family_id)
    tier = age_tier_for(plan, x, y)
    index = hash32(stable_key(component_path)) % int(family['variants'])
    candidates = [i for i in family['instances']
                  if i['ageTier'] == tier['id'] and i['variantIndex'] == index]
    if len(candidates) != 1:
        raise RuntimeError('Variant lookup for %s/%s/%d returned %d rows'
                           % (family_id, tier['id'], index, len(candidates)))
    return candidates[0], tier


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def offline_check(spec=None):
    """Reconcile the spec, the plan and the files on disk without an engine.

    Everything here is checkable from a plain Python process, which means it is checkable
    before an editor is ever launched.
    """
    spec = spec or load_spec()
    report = {'spec': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'problems': []}

    plan_path = ROOT / spec['plan']
    report['plan'] = spec['plan']
    if not plan_path.exists():
        report['problems'].append('plan missing: ' + spec['plan'])
        report['ok'] = False
        return report
    plan_sha = sha256_of(plan_path)
    report['planSha256'] = plan_sha
    report['planSha256MatchesSpec'] = plan_sha == spec['planSha256']
    if not report['planSha256MatchesSpec']:
        report['problems'].append(
            'plan SHA-256 differs from the spec; re-run create_decals.py --export and '
            'regenerate the spec, or the two disagree about what is being placed')

    plan = load_plan(spec)

    # Textures exist on disk and hash as the plan says.
    textures = []
    for texture in plan['textures']:
        path = ROOT / texture['file']
        row = {'name': texture['name'], 'file': texture['file'], 'exists': path.exists()}
        if path.exists():
            row['sha256Matches'] = sha256_of(path) == texture['sha256']
            row['sizeBytes'] = path.stat().st_size
            if not row['sha256Matches']:
                report['problems'].append('texture bytes differ from the plan: ' + texture['file'])
        else:
            report['problems'].append('texture missing: ' + texture['file'])
        textures.append(row)
    report['textures'] = textures

    # Every decal names a material instance that the plan actually defines, and every
    # instance names a texture the plan actually bakes.
    instance_names = {row['name'] for row in plan['decalInstances']}
    texture_names = {row['name'] for row in plan['textures']}
    for row in plan['decalInstances']:
        if row['texture'] not in texture_names:
            report['problems'].append('instance %s wants texture %s, which is not baked'
                                      % (row['name'], row['texture']))
    unresolved = sorted({d['material'] for d in plan['decals']} - instance_names)
    if unresolved:
        report['problems'].append('decals reference undefined material instances: %s' % unresolved[:5])

    # Category counts match the budget plan the C++ allocator is tested against.
    per_category = {}
    for category in plan['categories']:
        count = len([d for d in plan['decals'] if d['category'] == category['id']])
        per_category[category['id']] = count
        if count != category['requested']:
            report['problems'].append('category %s holds %d decals, plan requests %d'
                                      % (category['id'], count, category['requested']))
    report['decalsByCategory'] = per_category
    report['decalCount'] = len(plan['decals'])

    labels = [d['label'] for d in plan['decals']]
    if len(set(labels)) != len(labels):
        report['problems'].append('duplicate decal labels in the plan')

    # Nothing in the plan may name a protected material.
    protected = set(spec['protectedMaterials'])
    prefixes = tuple(spec['protectedMaterialPrefixes'])
    touched = set()
    for family in plan['stoneVariation']['families']:
        touched.add(family['parent'])
        for instance in family['instances']:
            touched.add(instance['parent'])
    overlap = sorted(touched & protected)
    if overlap and 'stone' in STAGE_ORDER:
        report['problems'].append('the stone variant plan parents onto protected materials: %s' % overlap)
    bad_prefix = sorted(p for p in touched if p.startswith(prefixes))
    if bad_prefix and 'stone' in STAGE_ORDER:
        report['problems'].append('the stone variant plan touches protected namespaces: %s' % bad_prefix)
    # Parenting ONTO an instance is allowed and is the whole point; editing one is not.
    report['stoneVariantParents'] = sorted(touched)

    protected_on_disk = {}
    for path in spec['protectedMaterials']:
        file = disk_path(path)
        protected_on_disk[path] = sha256_of(file) if file.exists() else None
    report['protectedMaterialSha256'] = protected_on_disk
    missing_protected = [p for p, v in protected_on_disk.items() if v is None]
    if missing_protected:
        # Not fatal: a protected material that does not exist cannot be damaged. It is
        # reported so a rename is noticed rather than silently reducing the guard.
        report['protectedMaterialsAbsent'] = missing_protected

    variants = sum(len(f['instances']) for f in plan['stoneVariation']['families'])
    report['stoneVariantInstanceCount'] = variants
    report['budget'] = plan['budget']
    report['costEstimate'] = plan['costEstimate']
    report['targetMapExists'] = disk_path(TARGET, 'umap').exists()
    if not report['targetMapExists']:
        report['problems'].append('target map missing on disk: ' + spec['targetMapFile'])

    report['ok'] = not report['problems']
    return report


# --------------------------------------------------------------------------
# Engine-side
# --------------------------------------------------------------------------

def _vector_list(v):
    return [float(v.x), float(v.y), float(v.z)]


def _rotator_list(r):
    return [float(r.pitch), float(r.yaw), float(r.roll)]


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _linear(colour):
    return [float(colour.r), float(colour.g), float(colour.b), float(colour.a)]


def _enum_value(ue, enum_name, candidates):
    """First candidate that exists on the enum. UE renames these between versions and a
    hard-coded name that has moved would fail with an AttributeError three stages in."""
    enum_class = getattr(ue, enum_name, None)
    if enum_class is None:
        raise RuntimeError('Enum %s is not exposed to Python in this build' % enum_name)
    for name in candidates:
        value = getattr(enum_class, name, None)
        if value is not None:
            return value, name
    raise RuntimeError('None of %s exist on %s' % (candidates, enum_name))


class OmissionError(Exception):
    """A stage that could not run, with numeric evidence. Never a silent skip."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


class SurfacePass:
    """Engine handles, texture import, the material graph, placement and readback."""

    def __init__(self, ue, spec, plan):
        self.ue = ue
        self.spec = spec
        self.plan = plan
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.ml = ue.MaterialEditingLibrary
        self.world = None
        self.snapshot = []
        self.receipt = {}
        self.receipt_path = None
        self.excluded_names = set()
        self.spawned = []            # actor handles this run created, for revert only

    # -- receipt ---------------------------------------------------------------

    def write_receipt(self):
        if not self.receipt_path:
            return
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(self.receipt, indent=1) + '\n', encoding='utf-8')

    # -- partial-failure cleanup -----------------------------------------------

    def rollback_spawned(self, mark):
        """Destroy the actors spawned since `mark`. Handles only, never labels.

        A stage that raises halfway through has left actors in the level. The map is not
        saved on failure so nothing reaches disk either way, but leaving them would mean a
        retry in the same editor session hits the "already present" refusal and the
        operator has to work out which half is real. Only actors this process spawned in
        this run are touched: the list is built from spawn return values, so it cannot
        name something that was already in the map.
        """
        destroyed = 0
        for actor in self.spawned[mark:]:
            if actor and self.actors.destroy_actor(actor):
                destroyed += 1
        del self.spawned[mark:]
        return destroyed

    # -- snapshot --------------------------------------------------------------

    def take_snapshot(self):
        import release_place_assets as h
        package = self.world.get_outermost().get_name()
        self.snapshot = [h.snapshot_row(self.ue, actor, package)
                         for actor in self.actors.get_all_level_actors() if actor]
        return self.snapshot

    def numeric_baseline(self, rows):
        import release_place_assets as h
        return h.numeric_baseline_rows(rows, strict=True, exclude=self.excluded_names)

    def probe_load_churn(self):
        import release_place_assets as h
        first = self.take_snapshot()
        if not self.levels.load_level(TARGET):
            raise RuntimeError('Pristine reload failed')
        self.world = self.editor.get_editor_world()
        second = self.take_snapshot()
        churn = h.diff_baselines(first, second, strict=True)
        self.excluded_names = {row['name'] for row in churn}
        return {'evidence': churn, 'excludedNames': sorted(self.excluded_names)}

    def component_baseline(self):
        """Slot-0 material of every StaticMeshComponent, so an override that was applied to
        the wrong component is visible in the receipt rather than only in the render."""
        ue = self.ue
        index = {}
        for row in self.snapshot:
            for component in row['actor'].get_components_by_class(ue.StaticMeshComponent):
                if isinstance(component, ue.InstancedStaticMeshComponent):
                    continue
                if component.get_editor_property('static_mesh') is None:
                    continue
                index[component.get_path_name()] = _asset_path(component.get_material(0))
        return index

    # -- assets ----------------------------------------------------------------

    def import_textures(self):
        ue = self.ue
        folder = self.spec['textureFolder']
        records = []
        for texture in self.plan['textures']:
            source = ROOT / texture['file']
            if not source.exists():
                raise OmissionError('texture source missing: ' + texture['file'])
            if sha256_of(source) != texture['sha256']:
                raise OmissionError('texture bytes differ from the plan: ' + texture['file'])
            path = folder + '/' + texture['name']
            record = {'asset': path, 'source': texture['file'], 'sourceSha256': texture['sha256']}
            if self.assets.does_asset_exist(path):
                raise OmissionError('Refuse existing texture: ' + path)
            else:
                task = ue.AssetImportTask()
                task.set_editor_property('filename', str(source))
                task.set_editor_property('destination_path', folder)
                task.set_editor_property('destination_name', texture['name'])
                task.set_editor_property('automated', True)
                task.set_editor_property('replace_existing', False)
                task.set_editor_property('save', False)
                ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                asset = ue.load_asset(path)
                record['created'] = True
            if not isinstance(asset, ue.Texture2D):
                raise OmissionError('imported asset is not a Texture2D: ' + path)
            compression, compression_name = _enum_value(
                ue, 'TextureCompressionSettings', ['TC_MASKS', 'TC_DEFAULT'])
            mip, mip_name = _enum_value(ue, 'TextureMipGenSettings',
                                        ['TMGS_SIMPLE_AVERAGE', 'TMGS_FROM_TEXTURE_GROUP'])
            address, address_name = _enum_value(
                ue, 'TextureAddress',
                ['TA_WRAP'] if texture['addressX'] == 'TA_Wrap' else ['TA_CLAMP'])
            asset.set_editor_property('compression_settings', compression)
            asset.set_editor_property('srgb', bool(texture['srgb']))
            asset.set_editor_property('mip_gen_settings', mip)
            asset.set_editor_property('address_x', address)
            asset.set_editor_property('address_y', address)
            if not self.assets.save_loaded_asset(asset, only_if_is_dirty=False):
                raise OmissionError('save_loaded_asset failed for ' + path)
            record.update({
                'compressionSettings': compression_name,
                'mipGenSettings': mip_name,
                'address': address_name,
                'srgb': bool(asset.get_editor_property('srgb')),
                'sizeX': int(asset.blueprint_get_size_x()),
                'sizeY': int(asset.blueprint_get_size_y()),
                'uassetSha256': sha256_of(disk_path(path)),
            })
            if record['sizeX'] != texture['width'] or record['sizeY'] != texture['height']:
                raise OmissionError('imported %s is %dx%d, plan says %dx%d'
                                    % (path, record['sizeX'], record['sizeY'],
                                       texture['width'], texture['height']))
            records.append(record)
        return records

    def build_master_material(self):
        """One deferred-decal material. Built node by node so the graph is reviewable here
        rather than only in the editor.

        R -> opacity, G -> roughness delta, B -> within-decal colour variety. One texture
        fetch does all three jobs, which is why the offline bakery packs them that way.
        """
        ue, ml = self.ue, self.ml
        cfg = self.plan['masterDecalMaterial']
        folder = self.spec['materialFolder']
        path = folder + '/' + cfg['name']
        record = {'asset': path, 'graph': []}

        if self.assets.does_asset_exist(path):
            raise OmissionError('Refuse existing master; choose a fresh namespace: ' + path)

        material = ue.AssetToolsHelpers.get_asset_tools().create_asset(
            cfg['name'], folder, ue.Material, ue.MaterialFactoryNew())
        if not isinstance(material, ue.Material):
            raise OmissionError('Material factory failed for ' + path)
        record['created'] = True

        domain, domain_name = _enum_value(ue, 'MaterialDomain', ['MD_DEFERRED_DECAL'])
        blend, blend_name = _enum_value(ue, 'BlendMode', ['BLEND_TRANSLUCENT'])
        # UE5.8 Material.h: DecalBlendMode is DeprecatedProperty, no longer used.
        # Domain + translucent blend + connected color/roughness/opacity outputs determine this decal.
        material.set_editor_property('material_domain', domain)
        material.set_editor_property('blend_mode', blend)
        record.update({'materialDomain': domain_name, 'blendMode': blend_name,
                       'decalBlendMode': 'deprecated_not_written_no_normal_output'})

        def node(cls, x, y):
            return ml.create_material_expression(material, cls, x, y)

        def link(src, out_name, dst, in_name):
            ok = ml.connect_material_expressions(src, out_name, dst, in_name)
            record['graph'].append({'from': src.get_class().get_name(), 'output': out_name,
                                    'to': dst.get_class().get_name(), 'input': in_name,
                                    'connected': bool(ok)})
            if not ok:
                raise OmissionError('connect_material_expressions failed: %s.%s -> %s.%s'
                                    % (src.get_class().get_name(), out_name,
                                       dst.get_class().get_name(), in_name))

        def link_property(src, out_name, prop, prop_name):
            ok = ml.connect_material_property(src, out_name, prop)
            record['graph'].append({'from': src.get_class().get_name(), 'output': out_name,
                                    'property': prop_name, 'connected': bool(ok)})
            if not ok:
                raise OmissionError('connect_material_property failed: %s -> %s'
                                    % (src.get_class().get_name(), prop_name))

        scalars = cfg['scalarParameters']
        sample = node(ue.MaterialExpressionTextureSampleParameter2D, -900, 0)
        sample.set_editor_property('parameter_name', cfg['textureParameters']['WearMask'])
        default_texture = ue.load_asset(self.spec['textureFolder'] + '/'
                                        + self.plan['textures'][0]['name'])
        if default_texture:
            sample.set_editor_property('texture', default_texture)
        sampler_type, sampler_name = _enum_value(ue, 'MaterialSamplerType',
                                                 ['SAMPLERTYPE_MASKS', 'SAMPLERTYPE_LINEAR_COLOR'])
        sample.set_editor_property('sampler_type', sampler_type)
        record['samplerType'] = sampler_name
        # NOTE: this node's UV pin is named 'UVs' in 5.8. Nothing is connected to it - the
        # decal's own projection supplies the coordinates - but the name is recorded here
        # because getting it wrong is a silent no-connect, not an error.
        record['uvPinName'] = 'UVs'

        opacity_p = node(ue.MaterialExpressionScalarParameter, -900, 300)
        opacity_p.set_editor_property('parameter_name', 'Opacity')
        opacity_p.set_editor_property('default_value', float(scalars['Opacity']))

        rough_p = node(ue.MaterialExpressionScalarParameter, -900, 400)
        rough_p.set_editor_property('parameter_name', 'RoughnessDelta')
        rough_p.set_editor_property('default_value', float(scalars['RoughnessDelta']))

        darken_p = node(ue.MaterialExpressionScalarParameter, -900, 500)
        darken_p.set_editor_property('parameter_name', 'AlbedoDarken')
        darken_p.set_editor_property('default_value', float(scalars['AlbedoDarken']))

        detail_p = node(ue.MaterialExpressionScalarParameter, -900, 600)
        detail_p.set_editor_property('parameter_name', 'DetailWeight')
        detail_p.set_editor_property('default_value', float(scalars['DetailWeight']))

        tint_p = node(ue.MaterialExpressionVectorParameter, -900, 700)
        tint_p.set_editor_property('parameter_name', 'WearTint')
        tint_p.set_editor_property('default_value',
                                   ue.LinearColor(*cfg['vectorParameters']['WearTint']))

        # -- base colour: lerp the tint toward a desaturated copy of itself by the B
        #    channel, so one decal is not one flat colour, then scale by (1 - AlbedoDarken).
        desat = node(ue.MaterialExpressionDesaturation, -600, 700)
        # 5.8: Desaturation's first input pin is named 'None'.
        link(tint_p, '', desat, 'None')

        detail_mul = node(ue.MaterialExpressionMultiply, -600, 620)
        link(sample, 'B', detail_mul, 'A')
        link(detail_p, '', detail_mul, 'B')

        base_lerp = node(ue.MaterialExpressionLinearInterpolate, -380, 700)
        link(tint_p, '', base_lerp, 'A')
        link(desat, '', base_lerp, 'B')
        link(detail_mul, '', base_lerp, 'Alpha')

        one = node(ue.MaterialExpressionConstant, -600, 520)
        one.set_editor_property('r', 1.0)
        darken_scale = node(ue.MaterialExpressionSubtract, -450, 520)
        link(one, '', darken_scale, 'A')
        link(darken_p, '', darken_scale, 'B')

        base_colour = node(ue.MaterialExpressionMultiply, -200, 640)
        link(base_lerp, '', base_colour, 'A')
        link(darken_scale, '', base_colour, 'B')

        # -- opacity
        opacity = node(ue.MaterialExpressionMultiply, -200, 300)
        link(sample, 'R', opacity, 'A')
        link(opacity_p, '', opacity, 'B')

        # -- roughness: 0.5 +/- delta, weighted by G, clamped away from a mirror finish.
        rough_mul = node(ue.MaterialExpressionMultiply, -600, 400)
        link(sample, 'G', rough_mul, 'A')
        link(rough_p, '', rough_mul, 'B')

        half = node(ue.MaterialExpressionConstant, -600, 320)
        half.set_editor_property('r', 0.5)
        rough_add = node(ue.MaterialExpressionAdd, -420, 400)
        link(half, '', rough_add, 'A')
        link(rough_mul, '', rough_add, 'B')

        rough_clamp = node(ue.MaterialExpressionClamp, -200, 400)
        # 5.8: Clamp's first input pin is also named 'None'.
        link(rough_add, '', rough_clamp, 'None')
        rough_clamp.set_editor_property('min_default', 0.02)
        rough_clamp.set_editor_property('max_default', 1.0)

        mp_base, _ = _enum_value(ue, 'MaterialProperty', ['MP_BASE_COLOR'])
        mp_opacity, _ = _enum_value(ue, 'MaterialProperty', ['MP_OPACITY'])
        mp_rough, _ = _enum_value(ue, 'MaterialProperty', ['MP_ROUGHNESS'])
        link_property(base_colour, '', mp_base, 'MP_BASE_COLOR')
        link_property(opacity, '', mp_opacity, 'MP_OPACITY')
        link_property(rough_clamp, '', mp_rough, 'MP_ROUGHNESS')

        ml.recompile_material(material)
        stats = ml.get_statistics(material)
        record['pixelInstructions'] = int(stats.get_editor_property('num_pixel_shader_instructions'))
        if record['pixelInstructions'] <= 0:
            raise OmissionError('No compiled render resource; use real RHI editor, not NullRHI')
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise OmissionError('save_loaded_asset failed for ' + path)
        record['uassetSha256'] = sha256_of(disk_path(path))
        record['expressionCount'] = len(record['graph'])
        return material, record

    def set_instance_parameter(self, instance, kind, name, value):
        """MIC setter verified by readback; struct-array fallback.

        UE 5.8 fact: SetMaterialInstance{Scalar,Vector}ParameterValue returns a bResult that
        was never assigned - it is ALWAYS false, success or not. Only the readback decides.
        The fallback must stamp Association=GlobalParameter and Index=-1 (INDEX_NONE); a
        Python-default struct carries LayerParameter/0 and the global lookup would miss it.
        """
        ue, ml = self.ue, self.ml
        getters = {'scalar': ml.get_material_instance_scalar_parameter_value,
                   'vector': ml.get_material_instance_vector_parameter_value}
        setters = {'scalar': ml.set_material_instance_scalar_parameter_value,
                   'vector': ml.set_material_instance_vector_parameter_value}
        tolerance = (self.spec['verification']['scalarParameterTolerance'] if kind == 'scalar'
                     else self.spec['verification']['vectorParameterTolerance'])

        def read():
            got = getters[kind](instance, name)
            return float(got) if kind == 'scalar' else _linear(got)

        def matches(got):
            if kind == 'scalar':
                return abs(got - float(value)) <= tolerance
            return max(abs(a - b) for a, b in zip(got[:3], _linear(value)[:3])) <= tolerance

        instance.modify(True)
        returned = setters[kind](instance, name, value)
        ml.update_material_instance(instance)
        got = read()
        route = ('MaterialEditingLibrary.set_material_instance_%s_parameter_value '
                 '(return %s, always false in 5.8, ignored)' % (kind, returned))
        if not matches(got):
            prop = {'scalar': 'scalar_parameter_values', 'vector': 'vector_parameter_values'}[kind]
            struct_cls = {'scalar': ue.ScalarParameterValue, 'vector': ue.VectorParameterValue}[kind]
            values = [v for v in instance.get_editor_property(prop)
                      if str(v.get_editor_property('parameter_info').get_editor_property('name')) != name]
            entry = struct_cls()
            info = ue.MaterialParameterInfo()
            info.set_editor_property('name', name)
            info.set_editor_property('association', ue.MaterialParameterAssociation.GLOBAL_PARAMETER)
            info.set_editor_property('index', -1)
            entry.set_editor_property('parameter_info', info)
            entry.set_editor_property('parameter_value', value)
            values.append(entry)
            instance.set_editor_property(prop, values)
            ml.update_material_instance(instance)
            got = read()
            route = 'set_editor_property(%s) struct fallback' % prop
        if not matches(got):
            raise OmissionError('parameter %s on %s read back %r after %s'
                                % (name, instance.get_name(), got, route))
        return {'after': got, 'route': route}

    def ensure_instance(self, path, parent_path, scalars, vectors):
        ue, ml = self.ue, self.ml
        folder, _, name = path.rpartition('/')
        record = {'asset': path, 'parent': parent_path}
        if self.assets.does_asset_exist(path):
            raise OmissionError('Refuse existing instance: ' + path)
        else:
            instance = ue.AssetToolsHelpers.get_asset_tools().create_asset(
                name, folder, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew())
            if not isinstance(instance, ue.MaterialInstanceConstant):
                raise OmissionError('MaterialInstanceConstant factory failed for ' + path)
            record['created'] = True

        parent = ue.load_asset(parent_path)
        if parent is None:
            raise OmissionError('parent material missing: ' + parent_path)
        if _asset_path(instance.get_editor_property('parent')) != parent_path:
            ml.set_material_instance_parent(instance, parent)
            if _asset_path(instance.get_editor_property('parent')) != parent_path:
                instance.set_editor_property('parent', parent)
                ml.update_material_instance(instance)
        if _asset_path(instance.get_editor_property('parent')) != parent_path:
            raise OmissionError('instance %s parent is not %s' % (path, parent_path))

        record['parameters'] = {}
        for pname, value in (scalars or {}).items():
            record['parameters'][pname] = self.set_instance_parameter(instance, 'scalar', pname, float(value))
        for pname, value in (vectors or {}).items():
            record['parameters'][pname] = self.set_instance_parameter(
                instance, 'vector', pname, ue.LinearColor(*[float(v) for v in value]))
        ml.update_material_instance(instance)
        if not self.assets.save_loaded_asset(instance, only_if_is_dirty=False):
            raise OmissionError('save_loaded_asset failed for ' + path)
        record['uassetSha256'] = sha256_of(disk_path(path))
        return instance, record

    def build_decal_instances(self, master_path):
        records = []
        folder = self.spec['materialFolder']
        for row in self.plan['decalInstances']:
            path = folder + '/' + row['name']
            texture = self.ue.load_asset(self.spec['textureFolder'] + '/' + row['texture'])
            if texture is None:
                raise OmissionError('texture not imported: ' + row['texture'])
            instance, record = self.ensure_instance(path, master_path, row['scalars'],
                                                    {'WearTint': row['tint']})
            # The texture parameter has no numeric getter; set it and read the object back.
            self.ml.set_material_instance_texture_parameter_value(instance, 'WearMask', texture)
            self.ml.update_material_instance(instance)
            got = self.ml.get_material_instance_texture_parameter_value(instance, 'WearMask')
            record['texture'] = _asset_path(got)
            if record['texture'] != _asset_path(texture):
                raise OmissionError('WearMask on %s read back as %s, expected %s'
                                    % (path, record['texture'], _asset_path(texture)))
            if not self.assets.save_loaded_asset(instance, only_if_is_dirty=False):
                raise OmissionError('save_loaded_asset failed for ' + path)
            record['uassetSha256'] = sha256_of(disk_path(path))
            record['note'] = row['note']
            records.append(record)
        return records

    # -- decal placement -------------------------------------------------------

    def place_decals(self):
        ue = self.ue
        spec = self.spec
        label_prefix = spec['labelPrefix']
        existing = [row['label'] for row in self.snapshot if row['label'].startswith(label_prefix)]
        if existing:
            raise OmissionError('surface-wear actors already present; refusing duplicate placement',
                                {'existing': existing[:10], 'count': len(existing)})

        placed = []
        for entry in self.plan['decals']:
            material_path = spec['materialFolder'] + '/' + entry['material']
            material = ue.load_asset(material_path)
            if material is None:
                raise OmissionError('decal material not built: ' + material_path)
            location = ue.Vector(*[float(v) for v in entry['locationCm']])
            rotation = ue.Rotator(pitch=float(entry['rotation']['pitch']),
                                  yaw=float(entry['rotation']['yaw']),
                                  roll=float(entry['rotation']['roll']))
            actor = self.actors.spawn_actor_from_class(ue.DecalActor, location, rotation)
            if actor is None:
                raise OmissionError('spawn_actor_from_class returned None for ' + entry['label'])
            self.spawned.append(actor)
            actor.set_actor_label(label_prefix + entry['label'])
            actor.set_folder_path(spec['folder'] + '/' + entry['category'])
            tags = [ue.Name(spec['actorTag']),
                    ue.Name(spec['categoryTagPrefix'] + entry['category']),
                    ue.Name(spec['importanceTagPrefix'] + str(int(round(entry['importance'] * 1000.0))))]
            actor.set_editor_property('tags', tags)

            decal = actor.get_component_by_class(ue.DecalComponent)
            if decal is None:
                raise OmissionError('DecalActor has no decal component: ' + entry['label'])
            decal.set_decal_material(material)
            decal.set_editor_property('decal_size', ue.Vector(*[float(v) for v in entry['sizeCm']]))
            decal.set_editor_property('sort_order', int(entry['sortOrder']))
            # The renderer's own screen-size fade; the runtime budget re-derives the same
            # number, so the two never disagree about where a decal disappears.
            extent = max(float(v) for v in entry['sizeCm'])
            decal.set_editor_property(
                'fade_screen_size',
                max(0.0005, min(0.05, extent / max(1.0, float(entry['fadeEndCm'])))))
            decal.set_editor_property('fade_start_delay', 0.0)
            decal.set_editor_property('fade_duration', 0.0)

            placed.append({
                'label': label_prefix + entry['label'],
                'name': actor.get_name(),
                'category': entry['category'],
                'material': material_path,
                'plannedLocationCm': entry['locationCm'],
                'plannedRotation': entry['rotation'],
                'plannedSizeCm': entry['sizeCm'],
                'importance': entry['importance'],
                'sortOrder': entry['sortOrder'],
                'rationale': entry['rationale'],
            })
        return {'placedCount': len(placed), 'actors': placed}

    # -- stone variation -------------------------------------------------------

    def build_stone_variants(self):
        records = []
        folder = self.spec['stoneVariantFolder']
        for family in self.plan['stoneVariation']['families']:
            for instance in family['instances']:
                path = folder + '/' + instance['name']
                _handle, record = self.ensure_instance(path, instance['parent'],
                                                       instance['scalars'], instance['vectors'])
                record.update({'family': instance['family'], 'ageTier': instance['ageTier'],
                               'variantIndex': instance['variantIndex']})
                records.append(record)
        return records

    def apply_stone_variants(self):
        """Slot-0 component overrides only. The three source instances and their shared
        parent are read, never written."""
        ue = self.ue
        folder = self.spec['stoneVariantFolder']
        by_parent = {f['parent']: f['id'] for f in self.plan['stoneVariation']['families']}
        applied = []
        per_family = {}
        skipped = {}
        for row in self.snapshot:
            actor = row['actor']
            if actor.get_actor_label().startswith(self.spec['labelPrefix']):
                continue
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                if isinstance(component, ue.InstancedStaticMeshComponent):
                    skipped['instanced static mesh component'] = skipped.get('instanced static mesh component', 0) + 1
                    continue
                if component.get_editor_property('static_mesh') is None:
                    continue
                current = _asset_path(component.get_material(0))
                family_id = by_parent.get(current)
                if family_id is None:
                    continue
                component_path = component.get_path_name()
                location = component.get_world_location()
                variant, tier = variant_for_component(self.plan, family_id, component_path,
                                                      location.x, location.y)
                target_path = folder + '/' + variant['name']
                target = ue.load_asset(target_path)
                if target is None:
                    raise OmissionError('stone variant instance missing: ' + target_path)
                component.set_material(0, target)
                readback = _asset_path(component.get_material(0))
                if readback != target_path:
                    raise OmissionError('slot-0 override on %s read back as %s, expected %s'
                                        % (component_path, readback, target_path))
                per_family[family_id] = per_family.get(family_id, 0) + 1
                applied.append({'component': component_path, 'family': family_id,
                                'ageTier': tier['id'], 'from': current, 'to': target_path})
        return {'appliedCount': len(applied), 'perFamily': per_family, 'skipped': skipped,
                'overrides': applied}

    # -- manager ---------------------------------------------------------------

    def spawn_manager(self):
        ue = self.ue
        spec = self.spec
        manager_class = getattr(ue, spec['managerClass'], None)
        if manager_class is None:
            raise OmissionError(
                'AMikdashSurfaceDetail is not exposed to Python in this editor build; the '
                'MikdashRuntime module has not been compiled with MikdashSurfaceDetail.cpp. '
                'The decals are placed and will render; they are simply unmanaged until the '
                'module is rebuilt and this stage is re-run with -SurfaceStages=manager.',
                {'requestedClass': spec['managerClass']})
        existing = [row['label'] for row in self.snapshot if row['label'] == spec['managerLabel']]
        if existing:
            raise OmissionError('manager already present', {'existing': existing})
        location = ue.Vector(*[float(v) for v in spec['managerLocationCm']])
        actor = self.actors.spawn_actor_from_class(manager_class, location, ue.Rotator(0, 0, 0))
        if actor is None:
            raise OmissionError('spawn_actor_from_class returned None for the manager')
        self.spawned.append(actor)
        actor.set_actor_label(spec['managerLabel'])
        actor.set_folder_path(spec['managerFolder'])
        actor.set_editor_property('surface_wear_tag', ue.Name(spec['actorTag']))
        actor.set_editor_property('decal_budget', int(spec['decalBudget']))
        puff = ue.load_asset(spec['materialFolder'] + '/MI_Wear_DustPuff')
        ripple = ue.load_asset(spec['materialFolder'] + '/MI_Wear_Ripple')
        if puff:
            actor.set_editor_property('dust_puff_material', puff)
        if ripple:
            actor.set_editor_property('ripple_material', ripple)
        return {
            'label': actor.get_actor_label(),
            'name': actor.get_name(),
            'class': actor.get_class().get_name(),
            'locationCm': _vector_list(actor.get_actor_location()),
            'decalBudget': int(actor.get_editor_property('decal_budget')),
            'surfaceWearTag': str(actor.get_editor_property('surface_wear_tag')),
            'dustPuffMaterial': _asset_path(actor.get_editor_property('dust_puff_material')),
            'rippleMaterial': _asset_path(actor.get_editor_property('ripple_material')),
        }

    # -- readback --------------------------------------------------------------

    def read_back_decals(self, planned, sample_size):
        ue = self.ue
        by_label = {}
        for row in self.take_snapshot():
            by_label.setdefault(row['label'], []).append(row)
        verify = self.spec['verification']
        readback = []
        checked = 0
        for record in planned:
            rows = by_label.get(record['label'], [])
            if len(rows) != 1:
                raise OmissionError('reopened actor count for %s is %d' % (record['label'], len(rows)))
            actor = rows[0]['actor']
            decal = actor.get_component_by_class(ue.DecalComponent)
            if decal is None:
                raise OmissionError('reopened decal component missing for ' + record['label'])
            location = _vector_list(actor.get_actor_location())
            rotation = _rotator_list(actor.get_actor_rotation())
            size = _vector_list(decal.get_editor_property('decal_size'))
            material = _asset_path(decal.get_decal_material())
            pose_error = max(abs(location[i] - float(record['plannedLocationCm'][i])) for i in range(3))
            size_error = max(abs(size[i] - float(record['plannedSizeCm'][i])) for i in range(3))
            rotation_error = max(abs((rotation[i] - float(record['plannedRotation'][key]) + 180.0) % 360.0 - 180.0)
                                 for i, key in enumerate(('pitch', 'yaw', 'roll')))
            if pose_error > verify['transformToleranceCm']:
                raise OmissionError('reopened location for %s differs by %.4f cm'
                                    % (record['label'], pose_error))
            if size_error > verify['decalSizeToleranceCm']:
                raise OmissionError('reopened decal size for %s differs by %.4f cm'
                                    % (record['label'], size_error))
            if rotation_error > verify['transformToleranceCm']:
                raise OmissionError('reopened rotation for %s differs by %.4f degrees'
                                    % (record['label'], rotation_error))
            if material != record['material']:
                raise OmissionError('reopened material for %s is %s, expected %s'
                                    % (record['label'], material, record['material']))
            tags = [str(t) for t in actor.get_editor_property('tags')]
            if self.spec['actorTag'] not in tags:
                raise OmissionError('reopened %s lost its wear tag' % record['label'])
            checked += 1
            if len(readback) < sample_size:
                readback.append({
                    'label': record['label'], 'category': record['category'],
                    'locationCm': location, 'rotation': rotation, 'decalSizeCm': size,
                    'material': material, 'tags': tags,
                    'sortOrder': int(decal.get_editor_property('sort_order')),
                    'fadeScreenSize': float(decal.get_editor_property('fade_screen_size')),
                    'locationErrorCm': round(pose_error, 6),
                    'decalSizeErrorCm': round(size_error, 6),
                })
        return {'checked': checked, 'sample': readback}

    def read_back_instances(self, records):
        ue, ml = self.ue, self.ml
        out = []
        for record in records:
            instance = ue.load_asset(record['asset'])
            if not isinstance(instance, ue.MaterialInstanceConstant):
                raise OmissionError('reopened asset is not a MaterialInstanceConstant: ' + record['asset'])
            values = {}
            for name in record.get('parameters', {}):
                try:
                    values[name] = float(ml.get_material_instance_scalar_parameter_value(instance, name))
                except Exception:  # noqa: BLE001 - it is a vector, then
                    values[name] = _linear(ml.get_material_instance_vector_parameter_value(instance, name))
            out.append({'asset': record['asset'],
                        'parent': _asset_path(instance.get_editor_property('parent')),
                        'values': values,
                        'uassetSha256': sha256_of(disk_path(record['asset']))})
        return out


# --------------------------------------------------------------------------

def _strip_handles(record):
    return {k: v for k, v in record.items() if k != 'actor'}


def place(load_target=True, stages=DEFAULT_STAGES):
    """Run the guarded pass. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    stages = normalise_stages(stages)
    spec = load_spec()
    plan = load_plan(spec)
    offline = offline_check(spec)
    if not offline['ok']:
        raise RuntimeError('Offline check failed: %s' % offline['problems'][:5])

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())

    run = SurfacePass(ue, spec, plan)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Dirty packages present before target load')
    if 'assets' in stages and len(stages) != 1:
        raise RuntimeError('Build assets alone, then fresh-process decals,manager')
    if 'assets' in stages:
        namespace_disk = ROOT / 'Content' / spec['namespace'][6:]
        if namespace_disk.exists() and any(namespace_disk.rglob('*.uasset')):
            raise RuntimeError('Fresh namespace required; never overwrite existing assets')
    if 'assets' not in stages:
        receipts = sorted((ROOT / spec['receiptFolder']).glob(spec['receiptPrefix'] + '*.json'), reverse=True)
        ready = None
        for receipt_file in receipts:
            candidate = json.loads(receipt_file.read_text(encoding='utf-8-sig'))
            if (candidate.get('status') == 'assets_created_shader_readback_complete_map_unchanged'
                    and candidate.get('specSha256') == sha256_of(SPEC_PATH)):
                ready = candidate
                break
        if ready is None:
            raise RuntimeError('No successful assets-only receipt for this exact spec')
        def verify_asset_records(value):
            if isinstance(value, dict):
                if 'asset' in value and 'uassetSha256' in value:
                    file = disk_path(value['asset'])
                    if not file.exists() or sha256_of(file) != value['uassetSha256']:
                        raise RuntimeError('Saved asset differs from successful receipt: ' + str(file))
                for child in value.values():
                    verify_asset_records(child)
            elif isinstance(value, list):
                for child in value:
                    verify_asset_records(child)
        verify_asset_records(ready['assets'])
        if 'manager' in stages and not hasattr(ue, spec['managerClass']):
            raise RuntimeError('Required compiled manager class is absent')
    if load_target:
        if not run.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Dirty packages present; resolve before checkpointed placement')

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected_maps = {'/Game/' + f.relative_to(ROOT / 'Content').as_posix()[:-5]: sha256_of(f)
                      for f in (ROOT / 'Content').rglob('*.umap') if f != map_file}
    protected_materials = {p: sha256_of(disk_path(p))
                           for p in spec['protectedMaterials'] if disk_path(p).exists()}
    for prefix in spec['protectedMaterialPrefixes']:
        for f in (ROOT / 'Content' / prefix[6:]).rglob('*.uasset'):
            protected_materials['/Game/' + f.relative_to(ROOT / 'Content').as_posix()[:-7]] = sha256_of(f)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    external_copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / TARGET[6:]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / TARGET[6:])
            external_copied.append(str(external))

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    run.receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))

    run.receipt = {
        'status': 'surface_detail_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected_maps,
        'protectedMaterialSha256Before': protected_materials,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'plan': spec['plan'],
        'planSha256': sha256_of(ROOT / spec['plan']),
        'namespaceRemap': {'source': spec['sourceNamespace'], 'target': spec['namespace'], 'sourceManifestUnmodified': True},
        'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'stagesRequested': list(stages),
        'stagesNotRequested': [s for s in STAGE_ORDER if s not in stages],
        'assets': {},
        'placed': {},
        'omissions': {},
        'errors': [],
        'mapSaved': False,
        'limitations': list(spec['limitations']) + list(plan['limitations']),
        'honesty': plan['honesty'],
    }
    run.write_receipt()

    saved = False
    try:
        run.receipt['loadChurnProbe'] = run.probe_load_churn()
        baseline = run.numeric_baseline(run.snapshot)
        component_before = run.component_baseline()
        run.receipt['actorCountBefore'] = len(run.snapshot)
        run.receipt['staticMeshComponentCountBefore'] = len(component_before)

        # --- stage: assets ---------------------------------------------------
        master_path = spec['materialFolder'] + '/' + plan['masterDecalMaterial']['name']
        if 'assets' in stages:
            try:
                run.receipt['assets']['textures'] = run.import_textures()
                _material, master_record = run.build_master_material()
                run.receipt['assets']['masterMaterial'] = master_record
                run.receipt['assets']['decalInstances'] = run.build_decal_instances(master_path)
            except OmissionError as omission:
                run.receipt['omissions']['assets'] = {'reason': str(omission), 'evidence': omission.evidence}
            except Exception as error:  # noqa: BLE001
                run.receipt['omissions']['assets'] = {'reason': 'asset_stage_failure: ' + str(error)}
                run.receipt['errors'].append({'stage': 'assets', 'error': repr(error)})
            run.write_receipt()

        # --- stage: stone variants -------------------------------------------
        if 'stone' in stages and 'assets' not in run.receipt['omissions']:
            try:
                run.receipt['assets']['stoneVariants'] = run.build_stone_variants()
                run.receipt['placed']['stone'] = run.apply_stone_variants()
            except OmissionError as omission:
                run.receipt['omissions']['stone'] = {'reason': str(omission), 'evidence': omission.evidence}
            except Exception as error:  # noqa: BLE001
                run.receipt['omissions']['stone'] = {'reason': 'stone_stage_failure: ' + str(error)}
                run.receipt['errors'].append({'stage': 'stone', 'error': repr(error)})
            run.write_receipt()
        elif 'stone' in stages:
            run.receipt['omissions']['stone'] = {'reason': 'assets stage was omitted; variants cannot be parented'}

        # --- stage: decals ---------------------------------------------------
        if 'decals' in stages:
            mark = len(run.spawned)
            try:
                run.receipt['placed']['decals'] = run.place_decals()
            except OmissionError as omission:
                run.receipt['omissions']['decals'] = {
                    'reason': str(omission), 'evidence': omission.evidence,
                    'partialActorsDestroyed': run.rollback_spawned(mark)}
            except Exception as error:  # noqa: BLE001
                run.receipt['omissions']['decals'] = {
                    'reason': 'decal_stage_failure: ' + str(error),
                    'partialActorsDestroyed': run.rollback_spawned(mark)}
                run.receipt['errors'].append({'stage': 'decals', 'error': repr(error)})
            run.write_receipt()

        # --- stage: manager --------------------------------------------------
        if 'manager' in stages:
            mark = len(run.spawned)
            try:
                run.receipt['placed']['manager'] = run.spawn_manager()
            except OmissionError as omission:
                run.receipt['omissions']['manager'] = {
                    'reason': str(omission), 'evidence': omission.evidence,
                    'partialActorsDestroyed': run.rollback_spawned(mark)}
            except Exception as error:  # noqa: BLE001
                run.receipt['omissions']['manager'] = {
                    'reason': 'manager_stage_failure: ' + str(error),
                    'partialActorsDestroyed': run.rollback_spawned(mark)}
                run.receipt['errors'].append({'stage': 'manager', 'error': repr(error)})
            run.write_receipt()

        if run.receipt['omissions'] or run.receipt['errors']:
            raise RuntimeError('Requested stage incomplete; refuse map save')
        mutated = bool(run.receipt['placed'].get('decals') or run.receipt['placed'].get('manager')
                       or run.receipt['placed'].get('stone', {}).get('appliedCount'))
        if not mutated:
            run.receipt['status'] = 'assets_created_shader_readback_complete_map_unchanged'
            return run.receipt

        # --- nothing existing may have moved ---------------------------------
        current = run.numeric_baseline(run.take_snapshot())
        moved = [name for name, row in baseline.items() if current.get(name) != row]
        if moved:
            raise RuntimeError('Pre-existing actors changed before save: %s' % moved[:10])
        component_after = run.component_baseline()
        vanished = sorted(set(component_before) - set(component_after))
        if vanished:
            raise RuntimeError('Static mesh components disappeared: %s' % vanished[:5])
        expected_overrides = {row['component']: row['to']
                              for row in run.receipt['placed'].get('stone', {}).get('overrides', [])}
        unexpected = []
        for path, before in component_before.items():
            after = component_after.get(path)
            if after == before:
                continue
            if expected_overrides.get(path) == after:
                continue
            unexpected.append({'component': path, 'before': before, 'after': after})
        if unexpected:
            raise RuntimeError('Slot-0 materials changed on components the plan did not name: %s'
                               % unexpected[:5])
        run.receipt['componentOverridesApplied'] = len(expected_overrides)

        # --- protected assets untouched --------------------------------------
        for path, before in protected_materials.items():
            after = sha256_of(disk_path(path)) if disk_path(path).exists() else None
            if after != before:
                raise RuntimeError('PROTECTED MATERIAL CHANGED: %s. This is the frieze-flattening '
                                   'failure mode; the checkpoint at %s holds the map as it was.'
                                   % (path, checkpoint))
        for prefix in spec['protectedMaterialPrefixes']:
            written = [row['asset'] for row in run.receipt['assets'].get('stoneVariants', [])
                       if row['asset'].startswith(prefix)]
            if written:
                raise RuntimeError('Wrote into a protected namespace: %s' % written[:5])

        # --- save, reopen, read back -----------------------------------------
        if not run.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()

        if not run.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run.world = run.editor.get_editor_world()
        reopened = run.take_snapshot()
        reopened_numeric = run.numeric_baseline(reopened)
        moved = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if moved:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % moved[:10])

        if run.receipt['placed'].get('decals'):
            run.receipt['reopenedDecalReadback'] = run.read_back_decals(
                run.receipt['placed']['decals']['actors'],
                int(spec['verification']['sampleDecalsForFullReadback']))
        if run.receipt['assets'].get('decalInstances'):
            run.receipt['reopenedInstanceReadback'] = run.read_back_instances(
                run.receipt['assets']['decalInstances'])
        if run.receipt['assets'].get('stoneVariants'):
            run.receipt['reopenedStoneVariantReadback'] = run.read_back_instances(
                run.receipt['assets']['stoneVariants'][:24])

        reopened_components = run.component_baseline()
        mismatched = [path for path, expected in expected_overrides.items()
                      if reopened_components.get(path) != expected]
        if mismatched:
            raise RuntimeError('Component overrides did not survive the reopen: %s' % mismatched[:5])

        manager_record = run.receipt['placed'].get('manager')
        if manager_record:
            managers = [row['actor'] for row in reopened if row['label'] == spec['managerLabel']]
            if len(managers) != 1:
                raise RuntimeError('Manager missing or duplicated after reopen')
            manager = managers[0]
            observed = {'decalBudget': int(manager.get_editor_property('decal_budget')),
                        'surfaceWearTag': str(manager.get_editor_property('surface_wear_tag')),
                        'dustPuffMaterial': _asset_path(manager.get_editor_property('dust_puff_material')),
                        'rippleMaterial': _asset_path(manager.get_editor_property('ripple_material'))}
            if any(observed[k] != manager_record[k] for k in observed):
                raise RuntimeError('Manager configuration did not persist')
            run.receipt['reopenedManagerReadback'] = observed

        run.receipt['status'] = 'surface_detail_saved_reopened_visual_runtime_acceptance_pending'
        return run.receipt
    except Exception as error:  # noqa: BLE001
        run.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        run.receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                                 else 'failed_before_save_map_unchanged')
        raise
    finally:
        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapBytesChanged'] = run.receipt['mapSha256After'] != map_sha_before
        run.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected_maps.items())
        run.receipt['protectedMaterialsUnchanged'] = all(
            (sha256_of(disk_path(p)) if disk_path(p).exists() else None) == value
            for p, value in protected_materials.items())
        run.receipt['actorCountAfter'] = len(run.take_snapshot()) if run.world else None
        run.write_receipt()


def revert(receipt_path=None):
    raise RuntimeError('Legacy label-based revert disabled; restore reviewed checkpoint explicitly')
    """Undo the last run: destroy the actors it placed and restore the slot-0 materials it
    overrode. Reads the receipt, so it can only ever touch what that run recorded."""
    import unreal as ue
    spec = load_spec()
    folder = ROOT / spec['receiptFolder']
    if receipt_path is None:
        candidates = sorted(folder.glob(spec['receiptPrefix'] + '*.json'))
        if not candidates:
            raise RuntimeError('No receipt to revert')
        receipt_path = candidates[-1]
    prior = json.loads(Path(receipt_path).read_text(encoding='utf-8'))

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    run = SurfacePass(ue, spec, load_plan(spec))
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if not run.levels.load_level(TARGET):
        raise RuntimeError('load_level failed for ' + TARGET)
    run.world = run.editor.get_editor_world()
    run.take_snapshot()

    labels = {row['label'] for row in prior.get('placed', {}).get('decals', {}).get('actors', [])}
    manager = prior.get('placed', {}).get('manager') or {}
    if manager.get('label'):
        labels.add(manager['label'])
    destroyed = []
    for row in run.snapshot:
        if row['label'] in labels:
            run.actors.destroy_actor(row['actor'])
            destroyed.append(row['label'])

    restored = []
    by_path = {}
    for row in run.snapshot:
        for component in row['actor'].get_components_by_class(ue.StaticMeshComponent):
            by_path[component.get_path_name()] = component
    for override in prior.get('placed', {}).get('stone', {}).get('overrides', []):
        component = by_path.get(override['component'])
        if component is None:
            continue
        source = ue.load_asset(override['from'])
        if source is None:
            continue
        component.set_material(0, source)
        if _asset_path(component.get_material(0)) == override['from']:
            restored.append(override['component'])

    saved = bool(run.levels.save_current_level())
    return {'status': 'surface_detail_reverted' if saved else 'revert_not_saved',
            'receipt': str(receipt_path), 'actorsDestroyed': destroyed,
            'actorsDestroyedCount': len(destroyed),
            'componentsRestored': len(restored), 'mapSaved': saved}


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    """True only when the engine itself is executing this file as a script."""
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return ('release_surface_detail.py' in command_line
            and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line))


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    stages = DEFAULT_STAGES
    do_revert = '-surfacerevert' in command_line
    for token in command_line.split():
        if token.startswith('-surfacestages='):
            stages = normalise_stages(token.split('=', 1)[1].strip('"'))
    try:
        if do_revert:
            result = revert()
            ue.log('release_surface_detail revert: %s destroyed %d restored %d'
                   % (result['status'], result['actorsDestroyedCount'], result['componentsRestored']))
        else:
            receipt = place(load_target=True, stages=stages)
            ue.log('release_surface_detail: %s stages %s decals %s omissions %s'
                   % (receipt['status'], list(stages),
                      receipt.get('placed', {}).get('decals', {}).get('placedCount'),
                      sorted(receipt.get('omissions', {}))))
    except Exception as error:  # noqa: BLE001
        ue.log_error('release_surface_detail failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

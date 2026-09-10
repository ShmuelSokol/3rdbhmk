"""Bark, leaf and billboard materials for JudeanFloraV1, and their assignment on both maps.

THE DEFECT THIS CLOSES
----------------------
release_vegetation.py placed 225,780 instances across 27 hierarchical instanced components on
both Walkthrough maps and recorded the hole itself in its own spec:

    "Materials are created unassigned unless a material is already present at the expected path."

There was no material at the expected path. `Content/MikdashV3/Vegetation/JudeanFloraV1/` held
Meshes/ and Textures/ and nothing else -- no M_*, no MI_* -- so every tree, shrub and grass clump
in the shipping build renders with the engine's default grey. This pass authors the materials and
points every slot at them.

WHAT THE MATERIALS HAVE TO GET RIGHT, AND WHY
---------------------------------------------
  * LEAF AND BILLBOARD ARE MASKED AND TWO-SIDED. A foliage card rendered opaque is a solid
    rectangle; rendered one-sided it disappears from half the angles. Nothing else in this file
    matters as much. The flags are set BEFORE the first compile so no stale shader map has to be
    fought afterwards.
  * The leaf master is MSM_TWO_SIDED_FOLIAGE, so the back face is lit through the leaf from the
    Subsurface Colour input. That is where the pale silvery underside of an olive comes from. If
    the enum is missing the graph falls back to DEFAULT_LIT, still masked and still two-sided,
    and the receipt says so rather than implying transmission that is not there.
  * JUDEAN FLORA IS NOT ENGLISH GREEN. Olive is grey-green, cypress and Jerusalem pine near
    black, date palm yellow-green, sage and hyssop grey and dusty, dry grass straw. Every species
    carries its own target colour and its own roughness in the spec, and the material CORRECTS
    the atlas onto that target (tint = targetLinear / atlasLinear) instead of tinting an already
    coloured texture a second time.
  * PER-INSTANCE VARIATION. BaseColour is TextureRGB * Lerp(TintA, TintB, PerInstanceRandom),
    with TintA and TintB straddling the target in hue as well as value. 225,780 instances of
    fourteen meshes is the worst possible case for "I don't wanna see repeating patterns all
    over"; this costs nothing and breaks up the mass planting more than any amount of texture
    work would.

THE HARD CONSTRAINT (EnclosureMath.h section 6b)
------------------------------------------------
NEVER PUT AUTHOR-WRITTEN HLSL BETWEEN PER-INSTANCE DATA AND THE OUTPUT. A Custom node taking
PerInstanceCustomData as an argument is hoisted into the vertex stage, where a non-instanced
vertex factory has no instance data, and ShaderCompileWorker dies with an access violation
(-1073741819) instead of failing cleanly -- that blocked all packaging for hours on 9 September.
Every node in every graph here is a stock node and `build_master` REFUSES to create a
MaterialExpressionCustom at all. MaterialExpressionPerInstanceRandom is exempt and is used: it is
a plain float on every vertex factory, not per-instance CUSTOM data, and it feeds nothing but
stock Lerp/Multiply nodes.

INVOCATION -- serial, never while another native job is running
---------------------------------------------------------------
Assets only (no map is loaded, no map is touched):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -ExecutePythonScript="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_vegetation_materials.py"
      -VegMatAssetsOnly -unattended -nosplash -nullrhi -abslog="C:/Mikdash/Working-5.8/VegMat-Assets.log"

Then apply, once per map, CANDIDATE FIRST because it is the only map that ships:

      ... -VegMatApplyOnly -Candidate48 ...
      ... -VegMatApplyOnly -Main50 ...

  -Main50        the legacy 50 cm map. THE DEFAULT, so no existing invocation is retargeted.
  -Candidate48   the configured GameDefaultMap and the cook map: the one that ships.

A material has no coordinates, so unlike a placement this pass is INDIFFERENT to the 0.96
similarity between the two maps: the same instance assets are assigned on both.

Revert (OFFLINE, with no editor open):
  python Scripts/release_vegetation_materials.py --revert=<receipt> [--dry-run]

Offline check (no engine):
  python Scripts/release_vegetation_materials.py

WHAT THIS DOES NOT ESTABLISH
----------------------------
No rendered frame. A real-RHI editor cannot start on this box, so nobody has seen any of this.
Every receipt this writes is stamped visual_acceptance_pending and the limitation is the first
line of the list.
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_vegetation_materials.spec.json'
sys.path.insert(0, str(ROOT / 'Scripts'))
import map_targets as mt  # noqa: E402

TARGET_KEY = mt.target_from_command_line()
TARGET_CONFIG = mt.target_config(TARGET_KEY)
TARGET = TARGET_CONFIG['map']
TARGET_LABEL = TARGET_CONFIG['key']

ENGINE_DEFAULT_PREFIX = '/Engine/'

# THE BISECT LADDER for the leaf master, most-suspect term first.
#
# Checkpoint cp05 died with ShaderCompileWorker return code -1073741819 (0xC0000005) on
# M_JudeanFlora_Leaf / FLocalVertexFactory and produced NO HLSL diagnostic of any kind: the
# compiler process died rather than rejecting the graph, exactly as M_PrecinctPlaza_Paving did.
# An access violation leaves nothing to read, so the terms come off one at a time and each rung
# is cooked.
#
# M_JudeanFlora_Bark carries PerInstanceRandom too and compiled clean in the SAME cook, so
# per-instance random is not first on trial. What is unique to the leaf is ObjectPositionWS --
# PRIMITIVE data, in a graph whose failing permutations are FLumenCardVS and TLightMapDensityVS --
# and the two-sided-foliage subsurface output.
LEAF_VARIANTS = {
    'full': {
        'perInstanceRandom': True, 'spatialBrightness': True, 'twoSidedFoliage': True,
        'note': 'as shipped in the cook that crashed'},
    'noSpatial': {
        'perInstanceRandom': True, 'spatialBrightness': False, 'twoSidedFoliage': True,
        'note': 'drop Frac(dot(ObjectPositionWS.xy, k)): primitive data, and purely decorative'},
    'noVariation': {
        'perInstanceRandom': False, 'spatialBrightness': False, 'twoSidedFoliage': True,
        'note': 'THE SHIPPABLE FALLBACK: drop BOTH variation sources, keep the per-species colour, '
                'the masked/two-sided flags and the foliage transmission. A hillside without '
                'instance-level hue variation is worth far more than a project that cannot package.'},
    'noFoliage': {
        'perInstanceRandom': True, 'spatialBrightness': False, 'twoSidedFoliage': False,
        'note': 'also drop MSM_TWO_SIDED_FOLIAGE and MP_SUBSURFACE_COLOR; still masked, still two-sided'},
    'minimal': {
        'perInstanceRandom': False, 'spatialBrightness': False, 'twoSidedFoliage': False,
        'note': 'also drop PerInstanceRandom: the Lerp alpha becomes a constant 0.5, so the MEAN '
                'species colour is unchanged and only the instance-to-instance spread is lost'},
}
DEFAULT_LEAF_VARIANT = 'full'


def leaf_variant_from_command_line(command_line):
    """-VegMatLeafVariant=<name> off the engine command line. Defaults to the full graph."""
    for token in command_line.split():
        if token.lower().startswith('-vegmatleafvariant='):
            name = token.split('=', 1)[1].strip('"')
            if name not in LEAF_VARIANTS:
                raise RuntimeError('Unknown leaf variant %r; known: %s'
                                   % (name, sorted(LEAF_VARIANTS)))
            return name
    return DEFAULT_LEAF_VARIANT


# ---------------------------------------------------------------------------
# offline: nothing below imports unreal
# ---------------------------------------------------------------------------

def sha256_of(path):
    path = Path(path)
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    return ROOT / 'Content' / (asset_path[len('/Game/'):] + '.' + extension)


def load_spec():
    return json.loads(SPEC_PATH.read_text(encoding='utf-8'))


def load_manifest(spec):
    manifest = json.loads((ROOT / spec['manifest']).read_text(encoding='utf-8'))
    if manifest.get('status') != spec['manifestStatusRequired']:
        raise RuntimeError('Manifest status is %r, expected %r'
                           % (manifest.get('status'), spec['manifestStatusRequired']))
    return manifest


def srgb_to_linear(value):
    """8-bit sRGB channel to linear float, the exact IEC 61966-2-1 curve UE uses."""
    c = value / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(value):
    value = max(0.0, min(1.0, value))
    c = value * 12.92 if value <= 0.0031308 else 1.055 * (value ** (1 / 2.4)) - 0.055
    return int(round(c * 255.0))


def tint_for(atlas_srgb, target_srgb, clamp):
    """Per-channel correction carrying the atlas colour onto the target colour.

    The material multiplies the sampled (linear) texture by this, so the mean instance lands on
    the target instead of on the target tinted a second time by the colour already in the atlas.
    """
    tint = []
    for atlas, target in zip(atlas_srgb, target_srgb):
        a = srgb_to_linear(atlas)
        t = srgb_to_linear(target)
        raw = t / a if a > 1e-6 else 1.0
        tint.append(max(clamp[0], min(clamp[1], raw)))
    return tint


def spread_pair(tint, spread, hue):
    """TintA / TintB straddling `tint` in value AND hue, so instances differ in colour."""
    a = [tint[0] * (1.0 - spread * hue['r']), tint[1] * (1.0 - spread * hue['g']),
         tint[2] * (1.0 - spread * hue['b'])]
    b = [tint[0] * (1.0 + spread * hue['r']), tint[1] * (1.0 + spread * hue['g']),
         tint[2] * (1.0 + spread * hue['b'])]
    return a, b


def predicted_srgb(atlas_srgb, tint):
    return [linear_to_srgb(srgb_to_linear(atlas_srgb[i]) * tint[i]) for i in range(3)]


def species_plan(spec):
    """Every material instance this pass will create, with its numbers resolved. Pure."""
    defaults = spec['speciesDefaults']
    clamp = spec['tintClamp']
    hue = spec['perInstanceVariation']['hueShift']
    plan = {}
    for name, cfg in sorted(spec['species'].items()):
        spread = defaults['shrubVariationSpread'] if cfg['form'] in ('shrub', 'grass') \
            else defaults['variationSpread']
        entry = {'species': name, 'form': cfg['form'], 'reading': cfg['reading'],
                 'variationSpread': spread, 'roles': {}}
        leaf_tint = tint_for(cfg['leafAtlasSrgb'], cfg['leafTargetSrgb'], clamp)
        leaf_a, leaf_b = spread_pair(leaf_tint, spread, hue)
        entry['roles']['leaf'] = {
            'instance': spec['instancePrefix'] + name + '_Leaf',
            'master': 'M_JudeanFlora_Leaf',
            'textureParameters': {'LeafAtlas': 'T_%s_Leaf_BCA' % name},
            'vectors': {'LeafTintA': leaf_a + [1.0], 'LeafTintB': leaf_b + [1.0],
                        'SubsurfaceTint': [srgb_to_linear(v) for v in cfg['subsurfaceSrgb']] + [1.0]},
            'scalars': {'Roughness': cfg['leafRoughness'], 'Specular': defaults['leafSpecular'],
                        'SubsurfaceStrength': defaults['subsurfaceStrength'],
                        'BrightnessSpread': defaults['brightnessSpread']},
            'atlasSrgb': cfg['leafAtlasSrgb'], 'targetSrgb': cfg['leafTargetSrgb'],
            'tint': leaf_tint, 'predictedSrgb': predicted_srgb(cfg['leafAtlasSrgb'], leaf_tint),
        }
        if cfg['hasBark']:
            bark_tint = tint_for(cfg['barkAtlasSrgb'], cfg['barkTargetSrgb'], clamp)
            bark_a, bark_b = spread_pair(bark_tint, spread * 0.6, hue)
            entry['roles']['bark'] = {
                'instance': spec['instancePrefix'] + name + '_Bark',
                'master': 'M_JudeanFlora_Bark',
                'textureParameters': {'BarkBaseColour': 'T_%s_Bark_BC' % name,
                                      'BarkNormal': 'T_%s_Bark_N' % name},
                'vectors': {'BarkTintA': bark_a + [1.0], 'BarkTintB': bark_b + [1.0]},
                'scalars': {'Roughness': cfg['barkRoughness'], 'Specular': defaults['barkSpecular'],
                            'Tiling': defaults['barkTiling'],
                            'NormalStrength': defaults['barkNormalStrength']},
                'atlasSrgb': cfg['barkAtlasSrgb'], 'targetSrgb': cfg['barkTargetSrgb'],
                'tint': bark_tint, 'predictedSrgb': predicted_srgb(cfg['barkAtlasSrgb'], bark_tint),
            }
        if cfg['hasBillboard']:
            # The impostor is an orthographic render of this species' own LOD1 mesh, so it is
            # already the species' colour. It carries the LEAF correction so the far LOD does not
            # change hue as it swaps in, and that reuse is recorded rather than implied.
            entry['roles']['billboard'] = {
                'instance': spec['instancePrefix'] + name + '_Billboard',
                'master': 'M_JudeanFlora_Billboard',
                'textureParameters': {'BillboardAtlas': 'T_%s_Billboard_BCA' % name},
                'vectors': {'BillboardTintA': leaf_a + [1.0], 'BillboardTintB': leaf_b + [1.0]},
                'scalars': {'Roughness': cfg['leafRoughness'],
                            'Specular': defaults['leafSpecular']},
                'atlasSrgb': cfg['leafAtlasSrgb'], 'targetSrgb': cfg['leafTargetSrgb'],
                'tint': leaf_tint, 'predictedSrgb': predicted_srgb(cfg['leafAtlasSrgb'], leaf_tint),
                'tintSource': 'the leaf correction, so the LOD swap does not change hue',
            }
        plan[name] = entry
    return plan


def mesh_role(spec, mesh_name):
    """(species, role) for a JudeanFloraV1 mesh asset name, or (None, None)."""
    prefix = spec['meshPrefix']
    if not mesh_name.startswith(prefix):
        return None, None
    rest = mesh_name[len(prefix):]
    parts = rest.split('_')
    species = parts[0]
    if species not in spec['species']:
        return None, None
    tail = parts[-1].lower()
    if tail == 'billboard':
        return species, 'billboard'
    if tail in ('bark', 'trunk'):
        return species, 'bark'
    if tail in ('leaf', 'frond', 'blade', 'needle'):
        return species, 'leaf'
    return species, None


def role_from_slot_name(spec, slot_name, fallback):
    lowered = (slot_name or '').lower()
    for role, words in spec['slotRoleFromName'].items():
        # Only list values are word lists. A prose annotation added beside them iterates as
        # CHARACTERS and matches everything -- that is exactly how a note named 'measured'
        # turned every slot into a role called 'measured' on the first Candidate48 attempt.
        if not isinstance(words, list):
            continue
        if any(word in lowered for word in words):
            return role, 'slot name %r' % slot_name
    return fallback, 'fallback to the mesh role (slot name %r said nothing)' % slot_name


def offline_check(spec=None):
    """Everything checkable with no engine. Returns a dict; never raises for content problems."""
    errors = []
    spec = spec or load_spec()
    result = {'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'errors': errors}
    try:
        manifest = load_manifest(spec)
    except Exception as error:                                              # noqa: BLE001
        errors.append(repr(error))
        result['passed'] = False
        return result
    result['manifestSha256'] = sha256_of(ROOT / spec['manifest'])

    manifest_species = sorted({m['species'] for m in manifest['meshes']})
    if manifest_species != sorted(spec['species']):
        errors.append('Species differ: manifest %s, spec %s' % (manifest_species, sorted(spec['species'])))

    # Every mesh in the manifest must resolve to a species and a role this pass can serve.
    unresolved = []
    role_counts = {'bark': 0, 'leaf': 0, 'billboard': 0}
    for record in manifest['meshes']:
        species, role = mesh_role(spec, record['mesh'])
        if species is None or role is None or role != record['materialRole']:
            unresolved.append({'mesh': record['mesh'], 'derived': [species, role],
                               'manifest': record['materialRole']})
        else:
            role_counts[role] += 1
    if unresolved:
        errors.append('%d meshes did not resolve to the manifest role, first %s'
                      % (len(unresolved), unresolved[:3]))
    result['meshRoleCounts'] = role_counts

    # Every texture a planned instance asks for must be a texture the generator actually wrote.
    written = set()
    for entry in manifest['textures']:
        for key in ('leafAtlas', 'barkBaseColour', 'barkNormal', 'billboardTexture'):
            if entry.get(key):
                written.add(entry[key].rsplit('.', 1)[0])
    plan = species_plan(spec)
    missing = []
    for species, entry in plan.items():
        for role, cfg in entry['roles'].items():
            for texture in cfg['textureParameters'].values():
                if texture not in written:
                    missing.append('%s/%s -> %s' % (species, role, texture))
    if missing:
        errors.append('Planned textures the generator never wrote: %s' % missing[:5])

    # A species with no bark mesh must not plan a bark instance, and vice versa.
    have_bark = {m['species'] for m in manifest['meshes'] if m['materialRole'] == 'bark'}
    have_bb = {m['species'] for m in manifest['meshes'] if m['materialRole'] == 'billboard'}
    for species, cfg in spec['species'].items():
        if bool(cfg['hasBark']) != (species in have_bark):
            errors.append('%s hasBark=%s but the manifest %s a bark mesh'
                          % (species, cfg['hasBark'], 'has' if species in have_bark else 'has no'))
        if bool(cfg['hasBillboard']) != (species in have_bb):
            errors.append('%s hasBillboard=%s but the manifest %s a billboard mesh'
                          % (species, cfg['hasBillboard'], 'has' if species in have_bb else 'has no'))

    # The colour work must actually differentiate the species: this is the point of the pass.
    targets = {s: tuple(c['leafTargetSrgb']) for s, c in spec['species'].items()}
    if len(set(targets.values())) != len(targets):
        errors.append('Two species share a leaf target colour; that is the repetition being fixed')
    roughs = {s: c['leafRoughness'] for s, c in spec['species'].items()}
    if len(set(roughs.values())) < 6:
        errors.append('Leaf roughness takes only %d distinct values across 14 species' % len(set(roughs.values())))
    greenest = max(targets.items(), key=lambda kv: kv[1][1] - (kv[1][0] + kv[1][2]) / 2.0)
    result['colourSpread'] = {
        'distinctLeafTargets': len(set(targets.values())),
        'distinctLeafRoughness': len(set(roughs.values())),
        'darkestLeaf': min(targets.items(), key=lambda kv: sum(kv[1]))[0],
        'lightestLeaf': max(targets.items(), key=lambda kv: sum(kv[1]))[0],
        'greenestLeaf': greenest[0],
        'leafTargetLumaRange': [min(sum(v) / 3.0 for v in targets.values()),
                                max(sum(v) / 3.0 for v in targets.values())],
    }
    if result['colourSpread']['leafTargetLumaRange'][1] - result['colourSpread']['leafTargetLumaRange'][0] < 40:
        errors.append('The leaf targets span less than 40/255 of brightness; that is one green parameterised')

    # The rule that cost a cook.
    if spec['customNodePolicy']['allowed']:
        errors.append('customNodePolicy.allowed must stay false (EnclosureMath.h 6b)')
    source = Path(__file__).read_text(encoding='utf-8')
    if "cls.__name__.endswith('Custom')" not in source:
        errors.append('The Graph.node guard that refuses author-written HLSL is gone (EnclosureMath.h 6b)')
    if 'create_material_expression(self.material, cls' not in source:
        errors.append('Node creation no longer funnels through the guarded Graph.node')

    for path in (spec['vegetationSpec'], spec['manifest'], spec['generator']):
        if not (ROOT / path).exists():
            errors.append('Missing referenced file: ' + path)

    result['plan'] = plan
    result['instancesPlanned'] = sum(len(e['roles']) for e in plan.values())
    result['passed'] = not errors
    return result


# ---------------------------------------------------------------------------
# engine
# ---------------------------------------------------------------------------

def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _enum(ue, enum_name, *candidates):
    enum = getattr(ue, enum_name)
    for name in candidates:
        if name and hasattr(enum, name):
            return getattr(enum, name), name
    raise RuntimeError('%s has none of %s' % (enum_name, candidates))


def _enum_name(value):
    """'TC_DEFAULT' from a Python enum whose repr is '<TextureCompressionSettings.TC_DEFAULT: 0>'.

    Splitting on the dot alone leaves the ': 0>' tail, and every flag comparison then fails
    against a plain name. That cost one full assets run.
    """
    text = str(value)
    if '.' in text:
        text = text.rsplit('.', 1)[-1]
    return text.split(':')[0].strip().rstrip('>').strip()


def _assets(ue):
    return ue.get_editor_subsystem(ue.EditorAssetSubsystem)


def stamp_now():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


class Graph:
    """A stock-node-only material graph builder. Refuses author-written HLSL by construction."""

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
            raise RuntimeError('Connection %s[%r] -> %s[%r] failed; outputs=%s' % (
                source.get_class().get_name(), output, target.get_class().get_name(), pin,
                [str(n) for n in self.ml.get_material_expression_output_names(source)]))
        self.record['connections'].append('%s.%s -> %s.%s' % (
            source.get_class().get_name(), output or 'out', target.get_class().get_name(), pin))
        return target

    def to_property(self, source, output, prop_name):
        prop = getattr(self.ue.MaterialProperty, prop_name)
        if not self.ml.connect_material_property(source, output, prop):
            raise RuntimeError('connect_material_property %s -> %s failed'
                               % (source.get_class().get_name(), prop_name))
        self.record['connections'].append('%s.%s -> %s'
                                          % (source.get_class().get_name(), output or 'out', prop_name))

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


def build_master(ue, spec, name, sample_textures, receipt, variant=None, force_rebuild=False):
    """Create one master material. FLAGS ARE SET BEFORE ANY NODE EXISTS, so the first compile is
    already the masked/two-sided one and no stale shader map has to be fought afterwards.

    `variant` selects a rung of LEAF_VARIANTS for the leaf master; `force_rebuild` empties an
    existing graph and rebuilds it IN PLACE rather than reusing it.
    """
    cfg = spec['masters'][name]
    folder = spec['materialFolder']
    path = folder + '/' + name
    ml = ue.MaterialEditingLibrary
    assets = _assets(ue)
    record = {'asset': path, 'role': cfg['role'], 'nodes': [], 'connections': [], 'status': 'started'}
    receipt['masters'][name] = record

    if assets.does_asset_exist(path) and not force_rebuild:
        material = ue.load_asset(path)
        if not isinstance(material, ue.Material):
            raise RuntimeError('Existing asset at %s is not a Material' % path)
        record['created'] = False
        record['status'] = 'reused_existing'
        record['blendMode'] = _enum_name(material.get_editor_property('blend_mode'))
        record['twoSided'] = bool(material.get_editor_property('two_sided'))
        record['shadingModelApplied'] = _enum_name(material.get_editor_property('shading_model'))
        names = [str(n) for n in ue.MaterialEditingLibrary.get_vector_parameter_names(material)]
        record['subsurfaceWired'] = 'SubsurfaceTint' in names
        return material
    if assets.does_asset_exist(path):
        # DELETE AND RECREATE, and the reason is a bug this file shipped.
        #
        # The first version rebuilt "in place" with delete_all_material_expressions() to avoid
        # orphaning the instances' parent pointer. That call DID NOT EMPTY THE GRAPH: the leaf
        # master came back with 35 expressions where 24 had been created - two LeafAtlas
        # samplers, seven ScalarParameters where there should be four - i.e. the old graph and
        # the new one superimposed, with duplicate parameter names. That material is what
        # checkpoint cp05b cooked, and the frames from it show solid opaque cards.
        #
        # A fresh asset is the only way to be sure the graph is exactly what was authored. The
        # instances are re-parented and re-verified immediately afterwards by build_instances,
        # which is what makes this safe.
        existing = ue.load_asset(path)
        if existing is not None and not isinstance(existing, ue.Material):
            raise RuntimeError('Existing asset at %s is not a Material' % path)
        before = len(ml.get_material_expressions(existing)) if existing is not None else None
        if not ue.EditorAssetLibrary.delete_asset(path):
            raise RuntimeError('delete_asset failed for ' + path)
        material = ue.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, ue.Material, ue.MaterialFactoryNew())
        if not isinstance(material, ue.Material):
            raise RuntimeError('Material factory failed after delete for ' + path)
        record.update(created=True, rebuiltFresh=True, expressionsBeforeDelete=before)
    else:
        material = ue.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, ue.Material, ue.MaterialFactoryNew())
        if not isinstance(material, ue.Material):
            raise RuntimeError('Material factory failed for ' + path)
        record.update(created=True, rebuiltInPlace=False)

    if cfg['role'] == 'leaf':
        variant = dict(variant or LEAF_VARIANTS[DEFAULT_LEAF_VARIANT])
    else:
        variant = {'perInstanceRandom': True, 'spatialBrightness': False, 'twoSidedFoliage': False,
                   'note': 'bark and billboard are not on the bisect ladder'}
    record['variant'] = variant

    # ---- flags first ------------------------------------------------------
    blend, blend_name = _enum(ue, 'BlendMode', cfg['blendMode'])
    material.set_editor_property('blend_mode', blend)
    material.set_editor_property('two_sided', bool(cfg['twoSided']))
    wanted_shading = cfg['shadingModel']
    if cfg['role'] == 'leaf' and not variant['twoSidedFoliage']:
        wanted_shading = cfg.get('shadingModelFallback') or 'MSM_DEFAULT_LIT'
    shading, shading_name = _enum(ue, 'MaterialShadingModel', wanted_shading,
                                  cfg.get('shadingModelFallback'))
    material.set_editor_property('shading_model', shading)
    if 'opacityMaskClipValue' in cfg:
        material.set_editor_property('opacity_mask_clip_value', float(cfg['opacityMaskClipValue']))

    # ---- USAGE FLAGS. THE BUG THAT PUT CARDBOARD IN THE BUILD. -------------
    #
    # All 225,780 instances live on HierarchicalInstancedStaticMeshComponents. A material
    # without bUsedWithInstancedStaticMeshes CANNOT be used on an instanced static mesh, and a
    # COOKED build silently falls back to WorldGridMaterial - opaque, one-sided, no opacity mask,
    # no species colour. That is exactly what checkpoint cp05b rendered.
    #
    # WHY EVERY EARLIER CHECK STAYED GREEN, and this is the part worth remembering: the EDITOR
    # adds a missing usage flag on the fly and only warns that the asset needs resaving. So
    # parameter parity, the save/reopen readback and every -nullrhi receipt all passed while the
    # shipped build drew the default material. The packaged build's own log named the fault:
    # "Material ... needs to be recompiled ... bUsedWithInstancedStaticMeshes". Flags are set
    # HERE, before the first compile, alongside blend mode and two-sidedness, and read back off
    # the saved asset below.
    usage = {}
    for flag in spec.get('usageFlags', ['used_with_instanced_static_meshes']):
        try:
            material.set_editor_property(flag, True)
            usage[flag] = bool(material.get_editor_property(flag))
        except Exception as error:                                       # noqa: BLE001
            usage[flag] = 'UNAVAILABLE: %r' % (error,)
    record['usageFlags'] = usage
    missing = [k for k, v in usage.items() if v is not True]
    if missing:
        raise RuntimeError('%s could not set usage flags %s (%s)' % (name, missing, usage))
    record.update(blendModeRequested=cfg['blendMode'], blendModeApplied=blend_name,
                  shadingModelRequested=wanted_shading, shadingModelApplied=shading_name,
                  shadingModelIsFallback=shading_name != wanted_shading,
                  twoSided=bool(material.get_editor_property('two_sided')),
                  opacityMaskClipValue=round(float(material.get_editor_property('opacity_mask_clip_value')), 4))

    g = Graph(ue, material, record)
    defaults = spec['speciesDefaults']
    colour_sampler, _ = _enum(ue, 'MaterialSamplerType', 'SAMPLERTYPE_COLOR')
    normal_sampler, _ = _enum(ue, 'MaterialSamplerType', 'SAMPLERTYPE_NORMAL')

    # Per-instance random, or a constant 0.5 when the bisect has taken it out. 0.5 is the exact
    # midpoint of Lerp(TintA, TintB), so the MEAN species colour is identical either way and only
    # the instance-to-instance spread is lost.
    if variant['perInstanceRandom']:
        per_instance = g.node(ue.MaterialExpressionPerInstanceRandom, -1500, 380)
    else:
        per_instance = g.node(ue.MaterialExpressionConstant, -1500, 380, r=0.5)
    record['perInstanceRandom'] = bool(variant['perInstanceRandom'])

    if cfg['role'] == 'bark':
        uv = g.node(ue.MaterialExpressionTextureCoordinate, -2100, -260, coordinate_index=0)
        tiling = g.scalar('Tiling', -2100, -120, defaults['barkTiling'])
        scaled_uv = g.binary(ue.MaterialExpressionMultiply, uv, '', tiling, '', -1900, -200)
        base = g.node(ue.MaterialExpressionTextureSampleParameter2D, -1600, -300,
                      parameter_name='BarkBaseColour', texture=sample_textures['BarkBaseColour'],
                      sampler_type=colour_sampler)
        g.wire(scaled_uv, '', base, 'UVs')
        normal = g.node(ue.MaterialExpressionTextureSampleParameter2D, -1600, 60,
                        parameter_name='BarkNormal', texture=sample_textures['BarkNormal'],
                        sampler_type=normal_sampler)
        g.wire(scaled_uv, '', normal, 'UVs')
        tint_a = g.vector('BarkTintA', -1500, 520, (1.0, 1.0, 1.0, 1.0))
        tint_b = g.vector('BarkTintB', -1500, 660, (1.0, 1.0, 1.0, 1.0))
        tint = g.lerp(tint_a, '', tint_b, '', per_instance, '', -1200, 560)
        base_colour = g.binary(ue.MaterialExpressionMultiply, base, 'RGB', tint, '', -900, 0)
        g.to_property(base_colour, '', 'MP_BASE_COLOR')
        strength = g.scalar('NormalStrength', -1300, 200, defaults['barkNormalStrength'])
        flat = g.node(ue.MaterialExpressionConstant3Vector, -1300, 300,
                      constant=ue.LinearColor(0.0, 0.0, 1.0, 1.0))
        bent = g.lerp(flat, '', normal, 'RGB', strength, '', -1000, 240)
        g.to_property(bent, '', 'MP_NORMAL')
        g.to_property(g.scalar('Roughness', -900, 420, 0.85), '', 'MP_ROUGHNESS')
        g.to_property(g.scalar('Specular', -900, 520, defaults['barkSpecular']), '', 'MP_SPECULAR')
        g.to_property(g.node(ue.MaterialExpressionConstant, -900, 620, r=0.0), '', 'MP_METALLIC')

    elif cfg['role'] in ('leaf', 'billboard'):
        leaf = cfg['role'] == 'leaf'
        atlas_param = 'LeafAtlas' if leaf else 'BillboardAtlas'
        tint_names = ('LeafTintA', 'LeafTintB') if leaf else ('BillboardTintA', 'BillboardTintB')
        atlas = g.node(ue.MaterialExpressionTextureSampleParameter2D, -1600, -300,
                       parameter_name=atlas_param, texture=sample_textures[atlas_param],
                       sampler_type=colour_sampler)
        # THE ONE THAT MATTERS: alpha -> opacity mask, with the material already BLEND_MASKED.
        g.to_property(atlas, 'A', 'MP_OPACITY_MASK')

        tint_a = g.vector(tint_names[0], -1500, 520, (1.0, 1.0, 1.0, 1.0))
        tint_b = g.vector(tint_names[1], -1500, 660, (1.0, 1.0, 1.0, 1.0))
        tint = g.lerp(tint_a, '', tint_b, '', per_instance, '', -1200, 560)
        tinted = g.binary(ue.MaterialExpressionMultiply, atlas, 'RGB', tint, '', -950, 0)

        base_colour = tinted
        if leaf and not variant['spatialBrightness']:
            record['spatialBrightness'] = {
                'applied': False,
                'removedByVariant': variant.get('note'),
                'reason': ('ObjectPositionWS is PRIMITIVE data. This is the first term off the '
                           'bisect ladder because it is the only primitive-data read unique to '
                           'the leaf, and it is decorative.')}
        elif leaf:
            # A second, DECORRELATED variation source so two neighbours that draw the same
            # per-instance random still differ. Stock nodes only.
            spatial = spec['perInstanceVariation'].get('spatialBrightness') or {}
            try:
                position = g.node(ue.MaterialExpressionObjectPositionWS, -1900, 900)
                xy = g.node(ue.MaterialExpressionComponentMask, -1700, 900,
                            r=True, g=True, b=False, a=False)
                g.wire(position, '', xy, 'Input')
                k = spatial.get('kPerCm') or [0.0007123, 0.0009377]
                key = g.node(ue.MaterialExpressionConstant2Vector, -1700, 1020,
                             r=float(k[0]), g=float(k[1]))
                dotted = g.binary(ue.MaterialExpressionDotProduct, xy, '', key, '', -1500, 940)
                fraction = g.node(ue.MaterialExpressionFrac, -1350, 940)
                g.wire(dotted, '', fraction, 'Input')
                spread = g.scalar('BrightnessSpread', -1700, 1140, defaults['brightnessSpread'])
                one = g.node(ue.MaterialExpressionConstant, -1500, 1200, r=1.0)
                low = g.binary(ue.MaterialExpressionSubtract, one, '', spread, '', -1350, 1140)
                high = g.binary(ue.MaterialExpressionAdd, one, '', spread, '', -1350, 1240)
                brightness = g.lerp(low, '', high, '', fraction, '', -1150, 1180)
                base_colour = g.binary(ue.MaterialExpressionMultiply, tinted, '', brightness, '',
                                       -800, 60)
                record['spatialBrightness'] = {'applied': True, 'kPerCm': list(k)}
            except Exception as error:                                       # noqa: BLE001
                record['spatialBrightness'] = {'applied': False, 'error': repr(error)[:200]}
        g.to_property(base_colour, '', 'MP_BASE_COLOR')

        g.to_property(g.scalar('Roughness', -900, 420, 0.7), '', 'MP_ROUGHNESS')
        g.to_property(g.scalar('Specular', -900, 520, defaults['leafSpecular']), '', 'MP_SPECULAR')
        g.to_property(g.node(ue.MaterialExpressionConstant, -900, 620, r=0.0), '', 'MP_METALLIC')

        if leaf and record['shadingModelApplied'] == 'MSM_TWO_SIDED_FOLIAGE':
            # The transmission that makes a leaf read as a leaf: the back face is lit THROUGH it.
            sub_tint = g.vector('SubsurfaceTint', -1500, 800, (0.6, 0.65, 0.5, 1.0))
            sub_strength = g.scalar('SubsurfaceStrength', -1500, 900, defaults['subsurfaceStrength'])
            sub = g.binary(ue.MaterialExpressionMultiply, sub_tint, '', sub_strength, '', -1150, 820)
            through = g.binary(ue.MaterialExpressionMultiply, atlas, 'RGB', sub, '', -900, 800)
            g.to_property(through, '', 'MP_SUBSURFACE_COLOR')
            record['subsurfaceWired'] = True
        else:
            record['subsurfaceWired'] = False
    else:
        raise RuntimeError('Unknown master role ' + cfg['role'])

    errors = list(ml.recompile_material(material))
    record['recompileMessages'] = [str(e) for e in errors][:20]
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + path)

    record['nodeCount'] = len(record['nodes'])
    # THE CHECK WHOSE ABSENCE LET A DUPLICATED GRAPH REACH A COOK. The saved material must hold
    # exactly the expressions this function created - no leftovers from a previous graph, which
    # would give duplicate parameter names and an unpredictable material.
    live = list(ml.get_material_expressions(material))
    record['expressionsInAsset'] = len(live)
    if len(live) != len(record['nodes']):
        classes = {}
        for e in live:
            key = e.get_class().get_name()
            classes[key] = classes.get(key, 0) + 1
        record['expressionClasses'] = classes
        raise RuntimeError('%s holds %d expressions but %d were created; the graph is duplicated '
                           '(classes %s)' % (name, len(live), len(record['nodes']), classes))
    parameter_classes = (ue.MaterialExpressionTextureSampleParameter2D,
                         ue.MaterialExpressionScalarParameter,
                         ue.MaterialExpressionVectorParameter)
    seen = set()
    dupes = set()
    for expression in live:
        if isinstance(expression, parameter_classes):
            pname = str(expression.get_editor_property('parameter_name'))
            if pname in seen:
                dupes.add(pname)
            seen.add(pname)
    record['parameterNamesInAsset'] = sorted(seen)
    if dupes:
        raise RuntimeError('%s has duplicate parameter names %s' % (name, sorted(dupes)))
    record['scalarParameters'] = sorted(str(n) for n in ml.get_scalar_parameter_names(material))
    record['vectorParameters'] = sorted(str(n) for n in ml.get_vector_parameter_names(material))
    record['textureParameters'] = sorted(str(n) for n in ml.get_texture_parameter_names(material))
    for group, wanted in (('scalarParameters', cfg['scalarParameters']),
                          ('vectorParameters', cfg['vectorParameters']),
                          ('textureParameters', list(cfg['textureParameters'].values()))):
        if not record.get('subsurfaceWired', False):
            wanted = [w for w in wanted if not w.startswith('Subsurface')]
        missing = set(wanted) - set(record[group])
        if missing:
            raise RuntimeError('%s lacks %s %s' % (name, group, sorted(missing)))
    record['uassetSha256'] = sha256_of(disk_path(path))
    record['status'] = 'saved'
    return material


def set_instance_parameter(ue, instance, kind, parameter, value, record):
    """Set one MIC parameter and VERIFY BY READBACK.

    MaterialEditingLibrary's setters apply the value but always return False in 5.8 (bResult is
    never assigned in MaterialEditingLibrary.cpp), so the bool is ignored and the readback is the
    check. release_pbr_architecture.py settled this; the struct fallback is kept for the same
    reason it is kept there.
    """
    ml = ue.MaterialEditingLibrary
    getters = {'texture': ml.get_material_instance_texture_parameter_value,
               'scalar': ml.get_material_instance_scalar_parameter_value,
               'vector': ml.get_material_instance_vector_parameter_value}
    setters = {'texture': ml.set_material_instance_texture_parameter_value,
               'scalar': ml.set_material_instance_scalar_parameter_value,
               'vector': ml.set_material_instance_vector_parameter_value}

    def matches():
        got = getters[kind](instance, parameter)
        if kind == 'texture':
            return _asset_path(got) == _asset_path(value), _asset_path(got)
        if kind == 'scalar':
            return abs(float(got) - float(value)) <= 1e-4, float(got)
        got_list = [float(got.r), float(got.g), float(got.b), float(got.a)]
        want = [float(value.r), float(value.g), float(value.b), float(value.a)]
        return all(abs(a - b) <= 1e-4 for a, b in zip(got_list, want)), got_list

    returned = setters[kind](instance, parameter, value)
    ok, got = matches()
    how = 'MaterialEditingLibrary.set_material_instance_%s_parameter_value (return %s ignored)' % (kind, returned)
    if not ok:
        prop = {'texture': 'texture_parameter_values', 'scalar': 'scalar_parameter_values',
                'vector': 'vector_parameter_values'}[kind]
        struct_cls = {'texture': ue.TextureParameterValue, 'scalar': ue.ScalarParameterValue,
                      'vector': ue.VectorParameterValue}[kind]
        values = [v for v in instance.get_editor_property(prop)
                  if str(v.get_editor_property('parameter_info').get_editor_property('name')) != parameter]
        entry = struct_cls()
        info = ue.MaterialParameterInfo()
        info.set_editor_property('name', parameter)
        entry.set_editor_property('parameter_info', info)
        entry.set_editor_property('parameter_value', value)
        values.append(entry)
        instance.set_editor_property(prop, values)
        ml.update_material_instance(instance)
        ok, got = matches()
        how = 'set_editor_property(%s) struct fallback' % prop
    record.setdefault('parameterPaths', {})[parameter] = how
    if not ok:
        raise RuntimeError('Parameter %s on %s read back %s after %s'
                           % (parameter, instance.get_name(), got, how))


def fix_textures(ue, spec, receipt):
    """Read every flag back, fix only what is wrong for the texture's role, record before/after."""
    assets = _assets(ue)
    folder = spec['textureAssetFolder']
    flags = spec['textureFlags']
    handles = {}
    for asset_path in sorted(ue.EditorAssetLibrary.list_assets(folder, recursive=False, include_folder=False)):
        clean = asset_path.split('.')[0]
        name = clean.rsplit('/', 1)[-1]
        texture = ue.load_asset(clean)
        if not isinstance(texture, ue.Texture2D):
            continue
        handles[name] = texture
        if name.endswith('_N'):
            want = flags['normal']
        elif name.endswith('_BCA'):
            want = flags['alphaAtlas']
        else:
            want = flags['baseColour']

        def read():
            state = {'srgb': bool(texture.get_editor_property('srgb')),
                     'compression': _enum_name(texture.get_editor_property('compression_settings')),
                     'addressX': _enum_name(texture.get_editor_property('address_x')),
                     'addressY': _enum_name(texture.get_editor_property('address_y'))}
            try:
                state['compressionNoAlpha'] = bool(texture.get_editor_property('compression_no_alpha'))
            except Exception:                                                # noqa: BLE001
                state['compressionNoAlpha'] = None
            return state

        before = read()
        changes = []
        if before['srgb'] != bool(want['srgb']):
            texture.set_editor_property('srgb', bool(want['srgb']))
            changes.append('srgb')
        compression, _ = _enum(ue, 'TextureCompressionSettings', want['compression'])
        if before['compression'] != want['compression']:
            texture.set_editor_property('compression_settings', compression)
            changes.append('compression')
        address_x, _ = _enum(ue, 'TextureAddress', want['addressX'])
        address_y, _ = _enum(ue, 'TextureAddress', want['addressY'])
        if before['addressX'] != want['addressX']:
            texture.set_editor_property('address_x', address_x)
            changes.append('addressX')
        if before['addressY'] != want['addressY']:
            texture.set_editor_property('address_y', address_y)
            changes.append('addressY')
        if 'compressionNoAlpha' in want and before['compressionNoAlpha'] not in (None, bool(want['compressionNoAlpha'])):
            texture.set_editor_property('compression_no_alpha', bool(want['compressionNoAlpha']))
            changes.append('compressionNoAlpha')
        if changes:
            if not assets.save_loaded_asset(texture, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + clean)
        after = read()
        wrong = {k: (after[k], want[k]) for k in ('srgb', 'compression', 'addressX', 'addressY')
                 if after[k] != want[k]}
        receipt['textures'][name] = {'asset': clean, 'role': want['reason'], 'before': before,
                                     'after': after, 'changed': changes,
                                     'stillWrong': wrong or None,
                                     'uassetSha256': sha256_of(disk_path(clean))}
        if wrong:
            raise RuntimeError('Texture %s did not take its flags: %s' % (name, wrong))
    receipt['textureSummary'] = {
        'inspected': len(receipt['textures']),
        'changed': sorted(n for n, r in receipt['textures'].items() if r['changed']),
        'unchanged': sum(1 for r in receipt['textures'].values() if not r['changed']),
    }
    return handles


def build_instances(ue, spec, masters, textures, receipt):
    """One MaterialInstanceConstant per species per role, parameters verified by readback."""
    ml = ue.MaterialEditingLibrary
    assets = _assets(ue)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    folder = spec['materialFolder']
    plan = species_plan(spec)
    out = {}
    for species, entry in sorted(plan.items()):
        for role, cfg in sorted(entry['roles'].items()):
            name = cfg['instance']
            path = folder + '/' + name
            record = {'asset': path, 'species': species, 'role': role, 'master': cfg['master'],
                      'reading': entry['reading'], 'atlasSrgb': cfg['atlasSrgb'],
                      'targetSrgb': cfg['targetSrgb'], 'tint': cfg['tint'],
                      'predictedSrgb': cfg['predictedSrgb'], 'status': 'started'}
            receipt['instances'][name] = record
            if assets.does_asset_exist(path):
                instance = ue.load_asset(path)
                if not isinstance(instance, ue.MaterialInstanceConstant):
                    raise RuntimeError('Existing asset at %s is not a MaterialInstanceConstant' % path)
                record['created'] = False
            else:
                instance = tools.create_asset(name, folder, ue.MaterialInstanceConstant,
                                              ue.MaterialInstanceConstantFactoryNew())
                if not isinstance(instance, ue.MaterialInstanceConstant):
                    raise RuntimeError('MaterialInstanceConstant factory failed for ' + path)
                record['created'] = True
            master = masters[cfg['master']]
            if _asset_path(instance.get_editor_property('parent')) != _asset_path(master):
                ml.set_material_instance_parent(instance, master)
                if _asset_path(instance.get_editor_property('parent')) != _asset_path(master):
                    instance.set_editor_property('parent', master)
                    ml.update_material_instance(instance)
            if _asset_path(instance.get_editor_property('parent')) != _asset_path(master):
                raise RuntimeError('Instance %s did not adopt its master' % name)

            for parameter, texture_name in cfg['textureParameters'].items():
                texture = textures.get(texture_name)
                if texture is None:
                    raise RuntimeError('Texture %s absent for %s' % (texture_name, name))
                set_instance_parameter(ue, instance, 'texture', parameter, texture, record)
            for parameter, value in cfg['vectors'].items():
                if parameter.startswith('Subsurface') and not receipt['masters'][cfg['master']].get('subsurfaceWired', True):
                    continue
                set_instance_parameter(ue, instance, 'vector', parameter,
                                       ue.LinearColor(*value), record)
            for parameter, value in cfg['scalars'].items():
                if parameter.startswith('Subsurface') and not receipt['masters'][cfg['master']].get('subsurfaceWired', True):
                    continue
                set_instance_parameter(ue, instance, 'scalar', parameter, float(value), record)
            ml.update_material_instance(instance)
            if not assets.save_loaded_asset(instance, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + path)
            record['readback'] = {
                'parent': _asset_path(instance.get_editor_property('parent')),
                'textures': {p: _asset_path(ml.get_material_instance_texture_parameter_value(instance, p))
                             for p in cfg['textureParameters']},
                'scalars': {p: round(float(ml.get_material_instance_scalar_parameter_value(instance, p)), 6)
                            for p in cfg['scalars'] if not (p.startswith('Subsurface') and not receipt['masters'][cfg['master']].get('subsurfaceWired', True))},
                'vectors': {p: [round(float(getattr(ml.get_material_instance_vector_parameter_value(instance, p), c)), 6)
                                for c in ('r', 'g', 'b', 'a')]
                            for p in cfg['vectors'] if not (p.startswith('Subsurface') and not receipt['masters'][cfg['master']].get('subsurfaceWired', True))},
            }
            record['uassetSha256'] = sha256_of(disk_path(path))
            record['status'] = 'saved'
            out[name] = instance
    return out


def assign_mesh_slots(ue, spec, instances, receipt):
    """Point every material slot on every JudeanFloraV1 static mesh at the right instance.

    Component overrides on the level would be enough for what renders today, but leaving the mesh
    assets themselves on the engine default means the next thing that places one is grey again.
    Slot count is NOT knowable offline -- set_lod_from_static_mesh folded L1/L2/Billboard into the
    L0 asset with bReuseExistingMaterialSlots=True -- so the slots are read back and each one's
    role is decided from its imported slot name, with the mesh's own role as the fallback.
    """
    assets = _assets(ue)
    folder = spec['meshFolder']
    assigned = 0
    total_slots = 0
    for asset_path in sorted(ue.EditorAssetLibrary.list_assets(folder, recursive=False, include_folder=False)):
        clean = asset_path.split('.')[0]
        name = clean.rsplit('/', 1)[-1]
        species, role = mesh_role(spec, name)
        if species is None or role is None:
            receipt['meshes'][name] = {'asset': clean, 'skipped': 'name did not resolve'}
            continue
        mesh = ue.load_asset(clean)
        if not isinstance(mesh, ue.StaticMesh):
            continue
        slots = list(mesh.get_editor_property('static_materials'))
        record = {'asset': clean, 'species': species, 'meshRole': role,
                  'slotCount': len(slots), 'slots': [], 'path': None}
        changed = False
        for index, slot in enumerate(slots):
            total_slots += 1
            slot_name = str(slot.get_editor_property('imported_material_slot_name'))
            slot_role, why = role_from_slot_name(spec, slot_name, role)
            if not spec['species'][species]['hasBark'] and slot_role == 'bark':
                slot_role, why = 'leaf', 'species has no bark part; slot served as leaf'
            if not spec['species'][species]['hasBillboard'] and slot_role == 'billboard':
                slot_role, why = 'leaf', 'species has no billboard; slot served as leaf'
            wanted = spec['instancePrefix'] + species + '_' + slot_role.capitalize()
            instance = instances.get(wanted)
            before = _asset_path(slot.get_editor_property('material_interface'))
            if instance is None:
                record['slots'].append({'slot': index, 'importedName': slot_name,
                                        'role': slot_role, 'why': why, 'before': before,
                                        'after': before, 'error': 'no instance ' + wanted})
                continue
            if before != _asset_path(instance):
                slot.set_editor_property('material_interface', instance)
                changed = True
            record['slots'].append({'slot': index, 'importedName': slot_name, 'role': slot_role,
                                    'why': why, 'before': before, 'material': wanted})
        if changed:
            try:
                mesh.set_editor_property('static_materials', slots)
                record['path'] = 'set_editor_property(static_materials)'
            except Exception as error:                                       # noqa: BLE001
                record['path'] = 'set_editor_property failed: %r' % (error,)
                for index, slot in enumerate(slots):
                    mesh.set_material(index, slot.get_editor_property('material_interface'))
                record['path'] = 'StaticMesh.set_material fallback'
            if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + clean)
        # Read back off the saved asset, not off the list we just mutated.
        after = [_asset_path(s.get_editor_property('material_interface'))
                 for s in mesh.get_editor_property('static_materials')]
        for index, entry in enumerate(record['slots']):
            entry['after'] = after[index] if index < len(after) else None
            if entry.get('material') and entry['after'] and entry['after'].endswith('/' + entry['material']):
                assigned += 1
            elif entry.get('material'):
                entry['mismatch'] = True
        record['uassetSha256'] = sha256_of(disk_path(clean))
        receipt['meshes'][name] = record
    mismatched = [n for n, r in receipt['meshes'].items()
                  for s in r.get('slots', []) if s.get('mismatch')]
    receipt['meshSummary'] = {'meshes': len([r for r in receipt['meshes'].values() if 'slots' in r]),
                              'slots': total_slots, 'slotsAssigned': assigned,
                              'slotsMismatched': sorted(set(mismatched))}
    if mismatched:
        raise RuntimeError('Mesh slots did not take: %s' % sorted(set(mismatched))[:5])
    return receipt['meshSummary']


def ensure_assets(ue, spec, receipt, force_rebuild=False, variant=None):
    """Textures, masters, instances, mesh slots. Map-independent: no level is loaded.

    force_rebuild deletes and recreates every master from scratch, then re-parents and
    re-verifies all 40 instances against it.
    """
    textures = fix_textures(ue, spec, receipt)
    sample = {}
    first = sorted(spec['species'])[0]
    for master_name, cfg in spec['masters'].items():
        for kind, parameter in cfg['textureParameters'].items():
            suffix = {'baseColour': '_Bark_BC', 'normal': '_Bark_N'}.get(kind)
            if suffix is None:
                suffix = '_Billboard_BCA' if cfg['role'] == 'billboard' else '_Leaf_BCA'
            key = 'T_' + first + suffix
            if key not in textures:
                raise RuntimeError('Sample texture %s missing for %s' % (key, parameter))
            sample[parameter] = textures[key]
    masters = {name: build_master(ue, spec, name, sample, receipt, variant=variant,
                                  force_rebuild=force_rebuild)
               for name in spec['masters']}
    instances = build_instances(ue, spec, masters, textures, receipt)
    assign_mesh_slots(ue, spec, instances, receipt)
    return masters, instances


def reopen_material_readback(ue, spec, receipt):
    """Read the flags off the SAVED assets after a forced reload, not off what we built."""
    out = {}
    for name in spec['masters']:
        path = spec['materialFolder'] + '/' + name
        ue.EditorAssetLibrary.load_asset(path)
        material = ue.load_asset(path)
        out[name] = {
            'blendMode': _enum_name(material.get_editor_property('blend_mode')),
            'twoSided': bool(material.get_editor_property('two_sided')),
            'shadingModel': _enum_name(material.get_editor_property('shading_model')),
            'opacityMaskClipValue': round(float(material.get_editor_property('opacity_mask_clip_value')), 4),
        }
        # The flag whose absence made the cooked build draw WorldGridMaterial while every
        # in-editor check passed. Read it off the SAVED asset, and fail if it is not there.
        for flag in spec.get('usageFlags', ['used_with_instanced_static_meshes']):
            try:
                out[name][flag] = bool(material.get_editor_property(flag))
            except Exception as error:                                   # noqa: BLE001
                out[name][flag] = 'UNAVAILABLE: %r' % (error,)
        want = spec['masters'][name]
        problems = []
        for flag in spec.get('usageFlags', ['used_with_instanced_static_meshes']):
            if out[name].get(flag) is not True:
                problems.append('%s is %r, not True' % (flag, out[name].get(flag)))
        if not out[name]['blendMode'].endswith(want['blendMode'].split('_')[-1]):
            problems.append('blendMode %s != %s' % (out[name]['blendMode'], want['blendMode']))
        if out[name]['twoSided'] != bool(want['twoSided']):
            problems.append('twoSided %s != %s' % (out[name]['twoSided'], want['twoSided']))
        out[name]['problems'] = problems or None
        if problems:
            raise RuntimeError('%s read back wrong after save: %s' % (name, problems))
    receipt['savedMaterialReadback'] = out
    return out


# ---------------------------------------------------------------------------
# the map
# ---------------------------------------------------------------------------

def vegetation_components(ue, spec, world_actors):
    """Every static mesh component in the level whose mesh lives in the JudeanFloraV1 folder."""
    folder = spec['meshFolder'] + '/'
    found = []
    for actor in world_actors:
        for component in actor.get_components_by_class(ue.StaticMeshComponent):
            mesh = component.get_editor_property('static_mesh')
            mesh_path = _asset_path(mesh)
            if not mesh_path or not mesh_path.startswith(folder):
                continue
            found.append({'actor': actor, 'label': actor.get_actor_label(),
                          'component': component, 'mesh': mesh, 'meshPath': mesh_path,
                          'meshName': mesh_path.rsplit('/', 1)[-1]})
    return found


def plan_overrides(ue, spec, instances, components, receipt):
    plan = []
    for row in components:
        species, role = mesh_role(spec, row['meshName'])
        if species is None or role is None:
            receipt['unresolvedComponents'].append({'label': row['label'], 'mesh': row['meshPath']})
            continue
        component = row['component']
        slots = list(row['mesh'].get_editor_property('static_materials'))
        overrides_before = [_asset_path(m) for m in component.get_editor_property('override_materials')]
        count = component.get_num_materials()
        entry = {'label': row['label'], 'component': component.get_path_name(),
                 'componentClass': component.get_class().get_name(),
                 'species': species, 'meshRole': role, 'mesh': row['meshPath'],
                 'slotCount': count, 'slots': [], 'handle': component,
                 'overrideMaterialsBefore': overrides_before,
                 'instanceCount': int(component.get_instance_count())
                 if hasattr(component, 'get_instance_count') else None}
        for index in range(count):
            slot_name = str(slots[index].get_editor_property('imported_material_slot_name')) \
                if index < len(slots) else ''
            slot_role, why = role_from_slot_name(spec, slot_name, role)
            if not spec['species'][species]['hasBark'] and slot_role == 'bark':
                slot_role, why = 'leaf', 'species has no bark part'
            if not spec['species'][species]['hasBillboard'] and slot_role == 'billboard':
                slot_role, why = 'leaf', 'species has no billboard'
            wanted = spec['instancePrefix'] + species + '_' + slot_role.capitalize()
            before = _asset_path(component.get_material(index))
            entry['slots'].append({
                'slot': index, 'importedName': slot_name, 'role': slot_role, 'why': why,
                'before': before,
                'overrideBefore': (overrides_before[index] if index < len(overrides_before) else None),
                'beforeWasEngineDefault': bool(before is None or before.startswith(ENGINE_DEFAULT_PREFIX)),
                'material': wanted, 'materialPath': spec['materialFolder'] + '/' + wanted,
                'exists': wanted in instances})
        plan.append(entry)
    return plan


def apply_overrides(ue, plan, instances):
    applied = 0
    for entry in plan:
        component = entry['handle']
        overrides = list(component.get_editor_property('override_materials'))
        while len(overrides) < entry['slotCount']:
            overrides.append(None)
        for slot in entry['slots']:
            instance = instances.get(slot['material'])
            if instance is None:
                raise RuntimeError('No material instance %s for %s' % (slot['material'], entry['component']))
            overrides[slot['slot']] = instance
        component.set_editor_property('override_materials', overrides)
        for slot in entry['slots']:
            after = _asset_path(component.get_material(slot['slot']))
            if after != slot['materialPath']:
                raise RuntimeError('Override did not take on %s slot %d: %s'
                                   % (entry['component'], slot['slot'], after))
            slot['after'] = after
            applied += 1
    return applied


def apply(spec=None):
    """Guarded assignment on one map. Returns the receipt dict; raises on any guard failure."""
    import unreal as ue
    spec = spec or load_spec()
    offline = offline_check(spec)
    if not offline['passed']:
        raise RuntimeError('Offline check failed: %s' % offline['errors'][:5])
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actors_subsystem = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before the run')

    stamp = stamp_now()
    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected_maps = [config['map'] for config in mt.TARGETS.values() if config['map'] != TARGET]
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in protected_maps
                 if disk_path(m, 'umap').exists()}
    for asset in spec['protectedAssets']:
        # A protected path that does not exist is a SPEC ERROR, not 'nothing to protect'. The
        # first version of this spec guessed the wrong folder for M_PBR_Tiled and the guard
        # silently watched an empty set.
        if not disk_path(asset).exists():
            raise RuntimeError('Protected asset does not exist, so nothing is guarding it: ' + asset)
        protected[asset] = sha256_of(disk_path(asset))

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_folder / (spec['receiptPrefix'] + TARGET_LABEL + '-' + stamp + '.json')
    receipt = {
        'status': 'started', 'stamp': stamp, 'stage': 'apply',
        'target': TARGET_LABEL, 'targetRole': TARGET_CONFIG['role'], 'map': TARGET,
        'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'protectedSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': offline['specSha256'],
        'manifestSha256': offline['manifestSha256'],
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'offlineCheck': {k: v for k, v in offline.items() if k != 'plan'},
        'materialsAreMapIndependent': ('A material has no coordinates, so unlike a placement this '
                                       'pass is indifferent to the 0.96 similarity between the two '
                                       'maps: the same instance assets are assigned on both.'),
        'unresolvedComponents': [], 'errors': [], 'mapSaved': False,
        'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        instances = {}
        for species, entry in species_plan(spec).items():
            for role, cfg in entry['roles'].items():
                path = spec['materialFolder'] + '/' + cfg['instance']
                asset = ue.load_asset(path)
                if not isinstance(asset, ue.MaterialInstanceConstant):
                    raise RuntimeError('Material instance missing; run -VegMatAssetsOnly first: ' + path)
                instances[cfg['instance']] = asset
        receipt['instancesLoaded'] = sorted(instances)
        reopen_material_readback(ue, spec, receipt)
        write()

        if not levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world %s is not the target' % world.get_outermost().get_name())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present after loading the map')

        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + TARGET_LABEL + '-' + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        external_copied = []
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[len('/Game/'):]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[len('/Game/'):])
                external_copied.append(str(external))
        receipt['checkpoint'] = str(checkpoint)
        receipt['oneFilePerActorFoldersCopied'] = external_copied
        write()

        all_actors = actors_subsystem.get_all_level_actors()
        receipt['actorCountBefore'] = len(all_actors)
        components = vegetation_components(ue, spec, all_actors)
        plan = plan_overrides(ue, spec, instances, components, receipt)
        slots_before_default = sum(1 for e in plan for s in e['slots'] if s['beforeWasEngineDefault'])
        receipt['before'] = {
            'components': len(plan),
            'slots': sum(e['slotCount'] for e in plan),
            'slotsOnEngineDefault': slots_before_default,
            'slotsWithNoOverrideBefore': sum(1 for e in plan for s in e['slots']
                                             if s['overrideBefore'] is None),
            'effectiveBeforeNote': ('component.get_material() resolves through the MESH slot, and '
                                    'the assets stage has already pointed those at the new '
                                    'instances -- so slotsOnEngineDefault reads 0 here even though '
                                    'the defect was real. The untouched evidence of the defect is '
                                    'slotsWithNoOverrideBefore (no component carried any override '
                                    'at all) plus the assets receipt, which records every mesh '
                                    "slot's material BEFORE this pass changed it."),
            'instanceTotal': sum(e['instanceCount'] or 0 for e in plan),
            'perSpecies': {},
        }
        for entry in plan:
            key = '%s_%s' % (entry['species'], entry['meshRole'])
            receipt['before']['perSpecies'][key] = {
                'label': entry['label'], 'instances': entry['instanceCount'],
                'slots': entry['slotCount'],
                'materialBefore': [s['before'] for s in entry['slots']]}
        write()
        if not plan:
            receipt['status'] = 'no_vegetation_components_found_map_unchanged'
            return receipt

        applied = apply_overrides(ue, plan, instances)
        receipt['appliedSlots'] = applied
        receipt['restore'] = [{'component': e['component'],
                               'overrideBefore': [s['before'] for s in e['slots']]} for e in plan]
        write()

        if not levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha256_of(map_file)
        write()

        # ---- reopen and read back, off the reloaded level -------------------
        if not levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        reopened_actors = actors_subsystem.get_all_level_actors()
        receipt['actorCountAfter'] = len(reopened_actors)
        if len(reopened_actors) != receipt['actorCountBefore']:
            raise RuntimeError('Actor count changed across the save: %d -> %d'
                               % (receipt['actorCountBefore'], len(reopened_actors)))
        reopened = vegetation_components(ue, spec, reopened_actors)
        ml = ue.MaterialEditingLibrary
        readback = []
        still_default = []
        assigned = 0
        total = 0
        for row in reopened:
            component = row['component']
            species, role = mesh_role(spec, row['meshName'])
            entry = {'label': row['label'], 'species': species, 'meshRole': role,
                     'mesh': row['meshPath'], 'slots': [],
                     'instances': int(component.get_instance_count())
                     if hasattr(component, 'get_instance_count') else None}
            for index in range(component.get_num_materials()):
                total += 1
                material = component.get_material(index)
                path = _asset_path(material)
                slot = {'slot': index, 'material': path}
                if path is None or path.startswith(ENGINE_DEFAULT_PREFIX):
                    still_default.append({'label': row['label'], 'slot': index, 'material': path})
                    slot['engineDefault'] = True
                else:
                    assigned += 1
                    # THE COLOUR, read off the material the placed component actually points at.
                    try:
                        parent = _asset_path(material.get_editor_property('parent'))
                        slot['parent'] = parent
                        for parameter in ('LeafTintA', 'LeafTintB', 'BarkTintA', 'BarkTintB',
                                          'BillboardTintA', 'BillboardTintB', 'SubsurfaceTint'):
                            value = ml.get_material_instance_vector_parameter_value(material, parameter)
                            vector = [round(float(getattr(value, c)), 5) for c in ('r', 'g', 'b')]
                            if any(abs(v - 1.0) > 1e-6 for v in vector):
                                slot[parameter] = vector
                        slot['Roughness'] = round(float(
                            ml.get_material_instance_scalar_parameter_value(material, 'Roughness')), 5)
                        base = ue.load_asset(parent) if parent else None
                        if base is not None:
                            slot['blendMode'] = _enum_name(base.get_editor_property('blend_mode'))
                            slot['twoSided'] = bool(base.get_editor_property('two_sided'))
                            slot['shadingModel'] = _enum_name(base.get_editor_property('shading_model'))
                    except Exception as error:                               # noqa: BLE001
                        slot['readbackError'] = repr(error)[:200]
                entry['slots'].append(slot)
            readback.append(entry)
        receipt['reopenedReadback'] = sorted(readback, key=lambda e: (e['species'] or '', e['meshRole'] or ''))
        receipt['after'] = {
            'components': len(readback),
            'slots': total,
            'slotsAssigned': assigned,
            'slotsStillOnEngineDefault': still_default,
            'instanceTotal': sum(e['instances'] or 0 for e in readback),
        }
        # The per-species colour, read off the instances rather than off the source.
        colours = {}
        for entry in readback:
            for slot in entry['slots']:
                for parameter in ('LeafTintA', 'LeafTintB', 'BarkTintA', 'BarkTintB'):
                    if parameter in slot:
                        mean = [(slot[parameter][i]) for i in range(3)]
                        colours.setdefault('%s_%s' % (entry['species'], entry['meshRole']), {})[parameter] = mean
                if 'Roughness' in slot:
                    colours.setdefault('%s_%s' % (entry['species'], entry['meshRole']), {})['Roughness'] = slot['Roughness']
                for key in ('blendMode', 'twoSided', 'shadingModel'):
                    if key in slot:
                        colours.setdefault('%s_%s' % (entry['species'], entry['meshRole']), {})[key] = slot[key]
        receipt['reopenedPerSpecies'] = colours
        if still_default:
            raise RuntimeError('%d slots are still on an engine default after the reopen: %s'
                               % (len(still_default), still_default[:5]))
        if assigned != total:
            raise RuntimeError('Assigned %d of %d slots' % (assigned, total))
        receipt['status'] = 'vegetation_materials_assigned_saved_reopened_visual_acceptance_pending'
        return receipt
    except Exception as error:                                               # noqa: BLE001
        receipt['errors'].append(repr(error))
        receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                             else 'failed_map_unchanged')
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        after_protected = {}
        for path in protected:
            extension = 'umap' if path.endswith('/Walkthrough') or '/Maps/' in path else 'uasset'
            after_protected[path] = sha256_of(disk_path(path, extension))
        receipt['protectedSha256After'] = after_protected
        receipt['protectedUnchanged'] = all(after_protected[p] == protected[p] for p in protected)
        write()
        receipt['receiptPath'] = str(receipt_path)


def rebuild_leaf(variant_name, spec=None):
    """Rebuild M_JudeanFlora_Leaf at one rung of the bisect ladder. ASSET ONLY -- no map is
    loaded, no map is saved, and the material instances keep their parent and their colours
    because the master is emptied and refilled in place rather than replaced."""
    import unreal as ue
    spec = spec or load_spec()
    variant = LEAF_VARIANTS[variant_name]
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    if ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')

    stamp = stamp_now()
    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_folder / (spec['receiptPrefix'] + 'leaf-' + variant_name + '-' + stamp + '.json')
    map_shas = {c['map']: sha256_of(disk_path(c['map'], 'umap')) for c in mt.TARGETS.values()}

    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + 'leaf-' + variant_name + '-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'Content' / spec['materialFolder'][len('/Game/'):]
    if source.exists():
        shutil.copytree(source, checkpoint / 'Materials')

    receipt = {
        'status': 'started', 'stamp': stamp, 'stage': 'leaf_variant_rebuild',
        'targetIndependent': True,
        'variantName': variant_name, 'variant': variant,
        'bisectLadder': LEAF_VARIANTS,
        'why': ('Checkpoint cp05 cook died with ShaderCompileWorker return code -1073741819 '
                '(0xC0000005) on M_JudeanFlora_Leaf/FLocalVertexFactory with no HLSL diagnostic. '
                'An access violation is the compiler dying rather than rejecting the graph, so '
                'there is nothing to read and the terms come off one at a time.'),
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'checkpoint': str(checkpoint),
        'mapSha256Before': map_shas,
        'masters': {}, 'errors': [], 'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    try:
        textures = {}
        folder = spec['textureAssetFolder']
        for asset_path in ue.EditorAssetLibrary.list_assets(folder, recursive=False, include_folder=False):
            clean = asset_path.split('.')[0]
            texture = ue.load_asset(clean)
            if isinstance(texture, ue.Texture2D):
                textures[clean.rsplit('/', 1)[-1]] = texture
        first = sorted(spec['species'])[0]
        sample = {'LeafAtlas': textures['T_' + first + '_Leaf_BCA']}
        build_master(ue, spec, 'M_JudeanFlora_Leaf', sample, receipt,
                     variant=variant, force_rebuild=True)
        write()

        # The instances keep their parent; refresh and re-save them so the cook sees a consistent
        # parent/instance pair rather than a stale cached parameter set.
        ml = ue.MaterialEditingLibrary
        assets = _assets(ue)
        refreshed = []
        for species in sorted(spec['species']):
            path = spec['materialFolder'] + '/' + spec['instancePrefix'] + species + '_Leaf'
            instance = ue.load_asset(path)
            if not isinstance(instance, ue.MaterialInstanceConstant):
                continue
            ml.update_material_instance(instance)
            if not assets.save_loaded_asset(instance, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + path)
            refreshed.append({'asset': path,
                              'parent': _asset_path(instance.get_editor_property('parent')),
                              'uassetSha256': sha256_of(disk_path(path))})
        receipt['instancesRefreshed'] = refreshed
        reopen_material_readback(ue, spec, receipt)
        receipt['status'] = 'leaf_variant_rebuilt_saved_cook_pending'
        return receipt
    except Exception as error:                                               # noqa: BLE001
        receipt['errors'].append(repr(error))
        receipt['status'] = 'failed_leaf_variant_rebuild'
        raise
    finally:
        receipt['mapSha256After'] = {c['map']: sha256_of(disk_path(c['map'], 'umap'))
                                     for c in mt.TARGETS.values()}
        receipt['mapsUnchanged'] = receipt['mapSha256After'] == map_shas
        write()
        receipt['receiptPath'] = str(receipt_path)


def assets_only(spec=None, force_rebuild=False):
    """Create the materials and point the mesh slots at them. NO LEVEL IS LOADED OR SAVED."""
    import unreal as ue
    spec = spec or load_spec()
    offline = offline_check(spec)
    if not offline['passed']:
        raise RuntimeError('Offline check failed: %s' % offline['errors'][:5])
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    if ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')

    stamp = stamp_now()
    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_folder / (spec['receiptPrefix'] + 'assets-' + stamp + '.json')
    protected = {}
    for asset in spec['protectedAssets']:
        if not disk_path(asset).exists():
            raise RuntimeError('Protected asset does not exist, so nothing is guarding it: ' + asset)
        protected[asset] = sha256_of(disk_path(asset))
    map_shas = {c['map']: sha256_of(disk_path(c['map'], 'umap')) for c in mt.TARGETS.values()}

    # Checkpoint the two folders this stage writes into. 18 MB; there is no excuse not to.
    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + 'assets-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    for folder in ('Meshes', 'Textures'):
        source = ROOT / 'Content' / (spec['assetFolder'][len('/Game/'):]) / folder
        if source.exists():
            shutil.copytree(source, checkpoint / folder)

    receipt = {
        'status': 'started', 'stamp': stamp,
        'stage': 'assets_force_rebuild' if force_rebuild else 'assets',
        'targetIndependent': True,
        'targetIndependentNote': ('A material has no coordinates. This stage touches no map and is '
                                  'shared by both. It deliberately carries no "target" key: '
                                  'verify.py check_map_parity buckets any receipt with one as a '
                                  'pass that ran on that map only.'),
        'specFile': str(SPEC_PATH), 'specSha256': offline['specSha256'],
        'manifestSha256': offline['manifestSha256'],
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'checkpoint': str(checkpoint),
        'offlineCheck': offline,
        'protectedSha256Before': protected,
        'mapSha256Before': map_shas,
        'materialFolder': spec['materialFolder'],
        'textures': {}, 'masters': {}, 'instances': {}, 'meshes': {},
        'errors': [], 'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    try:
        assets = _assets(ue)
        receipt['materialFolderExistedBefore'] = assets.does_directory_exist(spec['materialFolder'])
        receipt['forceRebuild'] = bool(force_rebuild)
        ensure_assets(ue, spec, receipt, force_rebuild=force_rebuild)
        write()
        reopen_material_readback(ue, spec, receipt)
        receipt['summary'] = {
            'masters': sorted(receipt['masters']),
            'instancesCreated': sorted(n for n, r in receipt['instances'].items() if r.get('created')),
            'instancesReused': sorted(n for n, r in receipt['instances'].items() if r.get('created') is False),
            'meshSlotsAssigned': receipt['meshSummary']['slotsAssigned'],
            'meshSlotsTotal': receipt['meshSummary']['slots'],
            'texturesChanged': receipt['textureSummary']['changed'],
        }
        receipt['status'] = 'vegetation_materials_authored_saved_visual_acceptance_pending'
        return receipt
    except Exception as error:                                               # noqa: BLE001
        receipt['errors'].append(repr(error))
        receipt['status'] = 'failed_assets_stage'
        raise
    finally:
        receipt['protectedSha256After'] = {a: sha256_of(disk_path(a)) for a in protected}
        receipt['protectedUnchanged'] = all(
            receipt['protectedSha256After'][a] == protected[a] for a in protected)
        receipt['mapSha256After'] = {c['map']: sha256_of(disk_path(c['map'], 'umap'))
                                     for c in mt.TARGETS.values()}
        receipt['mapsUnchanged'] = receipt['mapSha256After'] == map_shas
        write()
        receipt['receiptPath'] = str(receipt_path)


# ---------------------------------------------------------------------------

def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_vegetation_materials.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    lowered = ue.SystemLibrary.get_command_line().lower()
    try:
        if '-vegmatforcerebuild' in lowered:
            receipt = assets_only(force_rebuild=True)
            ue.log('release_vegetation_materials [assets force]: %s, %d mesh slots assigned'
                   % (receipt['status'], receipt['summary']['meshSlotsAssigned']))
        elif '-vegmatrebuildleaf' in lowered:
            name = leaf_variant_from_command_line(ue.SystemLibrary.get_command_line())
            receipt = rebuild_leaf(name)
            ue.log('release_vegetation_materials [leaf %s]: %s' % (name, receipt['status']))
        elif '-vegmatassetsonly' in lowered:
            receipt = assets_only()
            ue.log('release_vegetation_materials [assets]: %s, %d mesh slots assigned'
                   % (receipt['status'], receipt['summary']['meshSlotsAssigned']))
        else:
            receipt = apply()
            ue.log('release_vegetation_materials [%s]: %s, %d/%d slots assigned'
                   % (TARGET_LABEL, receipt['status'], receipt['after']['slotsAssigned'],
                      receipt['after']['slots']))
    except Exception as error:                                               # noqa: BLE001
        ue.log_error('release_vegetation_materials failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in lowered and '-run=pythonscript' not in lowered:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    elif mt.revert_from_command_line():
        _action = mt.revert_from_command_line()
        print(json.dumps(mt.restore_checkpoint(_action['receipt'], dry_run=_action['dryRun']), indent=2))
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

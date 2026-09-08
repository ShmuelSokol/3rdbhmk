"""Place the Mikdash fire, smoke, ember, light-shaft and haze set into the combined map.

Imports the six data textures baked offline by Scripts/create_fx_materials.py, authors
five master materials and eleven instances with MaterialEditingLibrary, spawns ONE
AMikdashFXDirector, saves, reopens, reads every number back, and writes a receipt.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_fx.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-FX-01.log"

Run WITHOUT the engine to get the offline check only (no map is touched):

  python Scripts/release_fx.py

Dry-run the material graph builders against a fake `unreal`, in under a second, to
catch a bad pin name or a missing director parameter before a commandlet run:

  python SourceAssets/fx-review/dry-run-materials.py

Safety model:
  - Refuses unless unreal.Paths.project_dir() is this project, no game world is
    running, the combined walkthrough map is the loaded world, and no package is
    already dirty.
  - Copies the .umap and both One-File-Per-Actor trees to a fresh, hash-verified
    checkpoint directory before touching anything.
  - Refuses if RELEASE_MikdashFXDirector already exists, rather than placing a
    second one.
  - Refuses if the editor binary predates AMikdashFXDirector, because an actor of a
    missing class would place silently and drive nothing.
  - Writes the receipt at the start, after every meaningful step, and in a finally
    block, so a crash leaves evidence rather than a mystery.
  - Records the process list before believing save_current_level(). A save that
    "fails" in this project has, more than once, been a leftover UnrealEditor
    holding the package.

UE 5.8 pitfalls this script is built around:
  - MaterialEditingLibrary's instance setters return False whether or not they
    worked. Every one is verified by reading the value back; the bool is recorded
    and ignored.
  - Material expression input pin names are not what they look like:
    Desaturation's and Clamp's first input is "None", TextureSample's UV pin is
    "UVs", Noise's position pin is "World Position". Rather than hardcode any of
    them, every connection resolves its pin through
    MaterialEditingLibrary.get_material_expression_input_names and records the name
    that worked.
  - recompile_material only schedules a compile and returns errors, not success.
    It is recorded and never used as the acceptance test.
  - Enum members are looked up by NAME. EnumBase has no int(), so an integer would
    be a silent wrong value.

Niagara: the run probes the Niagara Python surface first and records exactly what it
found. In 5.8 that surface can create an empty NiagaraSystem and nothing else - there
is no scripted way to add an emitter stage, a module or a renderer - so the effect set
is material-driven cards, which is the path this project already uses successfully.
The probe output is in the receipt so the choice is evidence rather than assertion.

What this does NOT establish: that anything looks right. Colour, opacity, density,
flicker depth and duration are artistic choices and need a human looking at a
screenshot. Nothing here is rabbinic approval, and the straight smoke column over the
outer altar is a depiction of a cited claim (Avos 5:5), not a physical result.
"""

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_fx.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'

# The six parameters AMikdashFXDirector writes on every card every frame. If a master
# material does not expose all six, the actor's writes go nowhere and the effect is a
# static decal. This is checked by readback, not assumed.
SHARED_DYNAMIC = ('FXFade', 'FXErosion', 'FXSeed', 'FXAge', 'FXFlicker', 'VFlip')


# ---------------------------------------------------------------------------
# Pure helpers. Everything above the engine section runs with no unreal import, so
# offline_check() can be read and re-run by a human anywhere.
# ---------------------------------------------------------------------------

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


def load_manifest(spec):
    path = ROOT / spec['manifest']
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    if manifest.get('schemaVersion') != 1:
        raise RuntimeError('Unexpected manifest schemaVersion: %r' % manifest.get('schemaVersion'))
    return manifest


def running_editor_processes():
    """Zombie check. A 'failed' save is often a leftover editor holding the file."""
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UnrealEditor*.exe', '/NH'],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception as error:                                   # noqa: BLE001
        return ['tasklist_failed: ' + repr(error)]
    return [line.strip() for line in out.splitlines() if line.strip() and 'UnrealEditor' in line]


def offline_check(spec=None):
    """Everything that can be established without opening the editor.

    Deliberately strict about the textures: a manifest that no longer matches the
    bytes on disk means someone re-baked without re-running --verify, and importing
    it would put a texture in the project that no receipt describes.
    """
    spec = spec or load_spec()
    manifest = load_manifest(spec)
    report = {
        'status': 'offline_fx_plan_verified',
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'manifestFile': spec['manifest'],
        'manifestSha256': sha256_of(ROOT / spec['manifest']),
        'generatorSha256Recorded': manifest.get('generatorSha256'),
        'targetMap': TARGET,
        'targetMapExists': disk_path(TARGET, 'umap').exists(),
        'textures': [],
        'materials': [m['name'] for m in manifest['materials']],
        'instances': [i['name'] for m in manifest['materials'] for i in m.get('instances', [])],
        'effects': [],
        'sourceClaims': [c['id'] for c in manifest['sourceClaims']],
        'problems': [],
        'notEstablished': spec['limitations'],
    }

    for entry in manifest['textures']:
        path = ROOT / entry['file']
        row = {'name': entry['name'], 'file': entry['file'], 'exists': path.exists()}
        if path.exists():
            row['sha256Matches'] = sha256_of(path) == entry['sha256']
            row['bytes'] = path.stat().st_size
            if not row['sha256Matches']:
                report['problems'].append('%s: bytes on disk do not match the manifest sha256; '
                                          're-run create_fx_materials.py --export' % entry['name'])
        else:
            report['problems'].append('%s: missing at %s' % (entry['name'], entry['file']))
        report['textures'].append(row)

    derived = manifest['derived']
    ket = derived['ketores']
    # The indoor column must stop under the roof. This is one of the acceptance
    # gates in Research/ketores-service-and-smoke.md, and it is cheap to check here
    # rather than discovering it as smoke on the skyline.
    if ket['columnTopZCm'] > ket['ceilingZCm']:
        report['problems'].append('ketores column top %.3f is above the ceiling %.3f'
                                  % (ket['columnTopZCm'], ket['ceilingZCm']))
    lamps = derived['lamps']
    if len(lamps['positions']) != spec['verification']['requireLampCount']:
        report['problems'].append('lamp count %d, expected %d'
                                  % (len(lamps['positions']), spec['verification']['requireLampCount']))
    if not 8.0 < lamps['puffingHz'] < 30.0:
        report['problems'].append('lamp puffing %.3f Hz is not wick scale' % lamps['puffingHz'])
    altar = derived['outerAltarColumn']
    if altar['puffingHz'] > 0.5 * lamps['puffingHz']:
        report['problems'].append('the altar and the lamps flicker at similar rates; '
                                  'the perceptual difference the sizes imply is gone')

    # Every instance override must name a parameter its master actually declares. An
    # override of a parameter that does not exist is not an error in the editor; it is
    # silently stored and never read, which is the worst of both worlds. This is the
    # cheap offline version of the readback create_instances() does in the editor.
    for cfg in manifest['materials']:
        known_s = set(cfg.get('scalars', {}))
        known_v = set(cfg.get('vectors', {}))
        known_t = set(cfg.get('textures', {}))
        for inst in cfg.get('instances', []):
            for kind, known in (('scalars', known_s), ('vectors', known_v), ('textures', known_t)):
                unknown = sorted(set(inst.get(kind, {})) - known)
                if unknown:
                    report['problems'].append(
                        '%s overrides %s %s, which %s does not declare'
                        % (inst['name'], kind, unknown, cfg['name']))

    for effect in manifest['effects']:
        report['effects'].append({
            'id': effect['id'],
            'location': effect['location'],
            'material': effect['material'],
            'continuous': effect['continuous'],
            'sourceClaims': effect['sourceClaims'],
            'needsReview': effect.get('needsReview'),
        })

    # The six director-driven parameters are graph parameters this script creates,
    # not authored defaults in the manifest, so there is nothing to check offline.
    # They are checked against the real material by readback in create_materials().
    report['sharedDynamicParameters'] = list(SHARED_DYNAMIC)

    if report['problems']:
        report['status'] = 'offline_fx_plan_failed'
    return report


# ---------------------------------------------------------------------------
# Engine section
# ---------------------------------------------------------------------------

def _enum(ue, enum_name, *candidates):
    enum = getattr(ue, enum_name)
    for name in candidates:
        if name and hasattr(enum, name):
            return getattr(enum, name), name
    raise RuntimeError('%s has none of %s' % (enum_name, candidates))


def _asset_path(asset):
    return asset.get_path_name() if asset else None


def probe_niagara(ue):
    """Record exactly what the Niagara Python surface offers, before falling back.

    The instruction for this feature was to try Niagara and expect to fall back. This
    is the trying, written down: which symbols exist, and specifically whether any of
    them can add an emitter, a module or a renderer to a system. Creating an empty
    UNiagaraSystem is not authoring an effect, and a receipt that said "used
    materials" without this would be an assertion instead of a finding.
    """
    wanted = ['NiagaraSystem', 'NiagaraEmitter', 'NiagaraComponent', 'NiagaraActor',
              'NiagaraSystemFactoryNew', 'NiagaraEmitterFactoryNew',
              'NiagaraFunctionLibrary', 'NiagaraEditorLibrary', 'NiagaraScript',
              'NiagaraDataInterface', 'NiagaraSystemEditorData']
    present = {name: hasattr(ue, name) for name in wanted}

    authoring = {}
    system_cls = getattr(ue, 'NiagaraSystem', None)
    if system_cls is not None:
        # Anything that could add a stage, a module or a renderer would be here.
        methods = [m for m in dir(system_cls) if not m.startswith('_')]
        authoring['NiagaraSystem.methods'] = methods
        authoring['NiagaraSystem.addsEmitters'] = any(
            k in m.lower() for m in methods for k in ('add_emitter', 'set_emitter', 'emitter_handle'))
    emitter_cls = getattr(ue, 'NiagaraEmitter', None)
    if emitter_cls is not None:
        methods = [m for m in dir(emitter_cls) if not m.startswith('_')]
        authoring['NiagaraEmitter.addsModules'] = any(
            k in m.lower() for m in methods for k in ('add_module', 'add_renderer', 'set_renderer'))

    can_author = bool(authoring.get('NiagaraSystem.addsEmitters')) and \
        bool(authoring.get('NiagaraEmitter.addsModules'))
    return {
        'symbolsPresent': present,
        'authoringSurface': {k: v for k, v in authoring.items() if not k.endswith('.methods')},
        'niagaraGraphAuthoringAvailable': can_author,
        'decision': ('material_driven_cards' if not can_author else 'niagara_available_review_required'),
        'reason': ('Niagara exists in the Python surface but exposes no way to add an emitter stage, '
                   'a module or a renderer, so a system created from script would be empty. The '
                   'effect set is therefore material-driven translucent cards driven by '
                   'AMikdashFXDirector, which is the path this project already uses.'
                   if not can_author else
                   'An authoring surface appeared that was not present when this was written. Do not '
                   'switch paths automatically; review it first.'),
    }


class Graph(object):
    """One material's node graph, with every pin name resolved from the engine.

    Nothing here hardcodes a pin name. The 5.8 traps that have cost this project time
    (Desaturation and Clamp take "None", TextureSample takes "UVs", Noise takes
    "World Position") are all avoided by asking the expression what its inputs are
    called and matching case-insensitively, and every resolved name is recorded so a
    future engine version that renames one shows up in the receipt.
    """

    def __init__(self, ue, material, record):
        self.ue = ue
        self.ml = ue.MaterialEditingLibrary
        self.material = material
        self.record = record
        record.setdefault('nodes', [])
        record.setdefault('connections', [])
        record.setdefault('resolvedPins', {})

    def node(self, cls, x, y, **props):
        expression = self.ml.create_material_expression(self.material, cls, x, y)
        if expression is None:
            raise RuntimeError('create_material_expression failed for ' + cls.__name__)
        for key, value in props.items():
            expression.set_editor_property(key, value)
        self.record['nodes'].append(cls.__name__)
        return expression

    def input_name(self, expression, wanted, strict=True):
        """Resolve a pin from a list of candidate spellings, asking the engine.

        `wanted` is a string or a tuple of them, most-likely first. Candidates and
        not a single name because 5.8 reports several pins under a name that is not
        the one in the header: UMaterialExpressionClamp declares Input/Min/Max and
        reports the first as "None", and this project has been bitten by exactly that
        on Clamp and on Desaturation. Two more are known from the engine headers and
        have no precedent here: UMaterialExpressionPower's second input is declared
        `Exponent` while the editor shows "Exp", and UMaterialExpressionDepthFade's
        first is declared `InOpacity` while the editor shows "Opacity". Rather than
        bet on either spelling, ask, and record which one answered.
        """
        candidates = (wanted,) if isinstance(wanted, str) else tuple(wanted)
        names = [str(n) for n in self.ml.get_material_expression_input_names(expression)]
        lowered = {n.lower(): n for n in names}
        key = '%s.%s' % (expression.get_class().get_name(), candidates[0])
        for candidate in candidates:
            if candidate.lower() in lowered:
                self.record['resolvedPins'][key] = lowered[candidate.lower()]
                return lowered[candidate.lower()]
        if len(names) == 1:
            self.record['resolvedPins'][key] = names[0]
            return names[0]
        if not strict:
            return None
        raise RuntimeError('%s has no input among %r (inputs %s)'
                           % (expression.get_class().get_name(), candidates, names))

    def wire(self, source, target, wanted, output=''):
        pin = self.input_name(target, wanted)
        if not self.ml.connect_material_expressions(source, output, target, pin):
            raise RuntimeError('Connection %s[%r] -> %s[%r] failed; outputs=%s' % (
                source.get_class().get_name(), output, target.get_class().get_name(), pin,
                [str(n) for n in self.ml.get_material_expression_output_names(source)]))
        self.record['connections'].append('%s.%s -> %s.%s' % (
            source.get_class().get_name(), output or 'out', target.get_class().get_name(), pin))
        return target

    def try_wire(self, source, target, wanted, output=''):
        """wire() that reports failure instead of raising. Returns the pin or None."""
        pin = self.input_name(target, wanted, strict=False)
        if pin is None:
            return None
        if not self.ml.connect_material_expressions(source, output, target, pin):
            return None
        self.record['connections'].append('%s.%s -> %s.%s' % (
            source.get_class().get_name(), output or 'out', target.get_class().get_name(), pin))
        return pin

    def to_property(self, source, prop_name, output=''):
        prop = getattr(self.ue.MaterialProperty, prop_name)
        if not self.ml.connect_material_property(source, output, prop):
            raise RuntimeError('connect_material_property %s -> %s failed'
                               % (source.get_class().get_name(), prop_name))
        self.record['connections'].append('%s.%s -> %s' % (source.get_class().get_name(), output or 'out', prop_name))

    # ---- small combinators -------------------------------------------------
    def scalar(self, name, value, x, y, group='FX'):
        return self.node(self.ue.MaterialExpressionScalarParameter, x, y,
                         parameter_name=name, default_value=float(value), group=group)

    def vector(self, name, rgba, x, y, group='FX'):
        return self.node(self.ue.MaterialExpressionVectorParameter, x, y, parameter_name=name,
                         default_value=self.ue.LinearColor(float(rgba[0]), float(rgba[1]),
                                                           float(rgba[2]), float(rgba[3])),
                         group=group)

    def const(self, value, x, y):
        # MaterialExpressionConstant's property is `r`, not `constant`. That mismatch
        # with Constant3Vector is a silent wrong-value trap, so it is spelled out.
        return self.node(self.ue.MaterialExpressionConstant, x, y, r=float(value))

    def mul(self, a, b, x, y, a_out='', b_out=''):
        n = self.node(self.ue.MaterialExpressionMultiply, x, y)
        self.wire(a, n, 'A', a_out)
        self.wire(b, n, 'B', b_out)
        return n

    def add(self, a, b, x, y, a_out='', b_out=''):
        n = self.node(self.ue.MaterialExpressionAdd, x, y)
        self.wire(a, n, 'A', a_out)
        self.wire(b, n, 'B', b_out)
        return n

    def sub(self, a, b, x, y, a_out='', b_out=''):
        n = self.node(self.ue.MaterialExpressionSubtract, x, y)
        self.wire(a, n, 'A', a_out)
        self.wire(b, n, 'B', b_out)
        return n

    def div(self, a, b, x, y, a_out='', b_out=''):
        n = self.node(self.ue.MaterialExpressionDivide, x, y)
        self.wire(a, n, 'A', a_out)
        self.wire(b, n, 'B', b_out)
        return n

    def lerp(self, a, b, alpha, x, y, a_out='', b_out='', alpha_out=''):
        n = self.node(self.ue.MaterialExpressionLinearInterpolate, x, y)
        self.wire(a, n, 'A', a_out)
        self.wire(b, n, 'B', b_out)
        self.wire(alpha, n, 'Alpha', alpha_out)
        return n

    def clamp01(self, source, x, y, output=''):
        n = self.node(self.ue.MaterialExpressionClamp, x, y, min_default=0.0, max_default=1.0)
        # Declared `Input`, reported as "None" in 5.8. Both are offered.
        self.wire(source, n, ('None', 'Input', ''), output)
        return n

    def mask(self, source, x, y, r=False, g=False, b=False, a=False, output=''):
        n = self.node(self.ue.MaterialExpressionComponentMask, x, y, r=r, g=g, b=b, a=a)
        self.wire(source, n, ('Input', 'None', ''), output)
        return n

    def append(self, a, b, x, y, a_out='', b_out=''):
        n = self.node(self.ue.MaterialExpressionAppendVector, x, y)
        self.wire(a, n, 'A', a_out)
        self.wire(b, n, 'B', b_out)
        return n

    def sampler(self, param_name, texture, uv, x, y, sampler_type):
        n = self.node(self.ue.MaterialExpressionTextureSampleParameter2D, x, y,
                      parameter_name=param_name, texture=texture, sampler_type=sampler_type)
        # "UVs", not "UV" and not "". The alternatives are offered anyway.
        self.wire(uv, n, ('UVs', 'UV', 'Coordinates'))
        return n

    # ---- the pieces every FX material shares -------------------------------
    def shared_uv(self, x=-2600):
        """UV0 with the V axis optionally flipped by the VFlip parameter.

        VFlip exists because the engine plane's V direction is a fact about a mesh
        this script does not own, and a flame baked tip-up would otherwise need a
        re-bake to fix. One scalar, driven from the actor, settles it.
        """
        uv = self.node(self.ue.MaterialExpressionTextureCoordinate, x, 0, coordinate_index=0)
        u = self.mask(uv, x + 200, -120, r=True)
        v = self.mask(uv, x + 200, 40, g=True)
        flip = self.scalar('VFlip', 0.0, x + 200, 200)
        inv = self.node(self.ue.MaterialExpressionOneMinus, x + 380, 40)
        self.wire(v, inv, ('Input', 'None', ''))
        chosen = self.lerp(v, inv, flip, x + 540, 60)
        return self.append(u, chosen, x + 700, 0)

    def scroll_offset(self, x=-2600, y=520):
        """A float2 of (Time*PanSpeedU + FXSeed, Time*PanSpeedV + FXSeed).

        FXSeed is per card, so two cards in the same fire never show the same frame
        of the same noise, which is what makes a handful of cards read as one body of
        flame instead of as copies.
        """
        time = self.node(self.ue.MaterialExpressionTime, x, y)
        seed = self.scalar('FXSeed', 0.0, x, y + 160)
        su = self.scalar('PanSpeedU', 0.03, x, y + 320)
        sv = self.scalar('PanSpeedV', 0.35, x, y + 480)
        tu = self.add(self.mul(time, su, x + 220, y), seed, x + 400, y)
        tv = self.add(self.mul(time, sv, x + 220, y + 300), seed, x + 400, y + 300)
        return self.append(tu, tv, x + 600, y + 150)

    def noise_uv(self, uv, offset, x=-1500, y=520):
        tiling = self.scalar('NoiseTiling', 2.0, x, y)
        return self.add(self.mul(uv, tiling, x + 200, y - 120), offset, x + 400, y - 120)

    def erosion(self, noise_r, ramp, x=-900, y=300, noise_out='', ramp_out=''):
        """Masked erosion: a dissolve whose threshold comes from the actor.

        product = noise * ramp; e = clamp((product - (bias + FXErosion)) / soft + 1).
        The +1 puts the fully-eroded edge at product == threshold rather than one
        softness below it, so FXErosion = 0 means "nothing eroded" and 1 means "gone",
        which is the range the director writes.
        """
        bias = self.scalar('ErosionBias', 0.40, x, y)
        dyn = self.scalar('FXErosion', 0.0, x, y + 160)
        soft = self.scalar('ErosionSoftness', 0.20, x, y + 320)
        threshold = self.add(bias, dyn, x + 200, y + 60)
        product = self.mul(noise_r, ramp, x + 200, y - 200, noise_out, ramp_out)
        delta = self.sub(product, threshold, x + 400, y - 100)
        scaled = self.div(delta, soft, x + 560, y - 100)
        one = self.const(1.0, x + 560, y + 60)
        return self.clamp01(self.add(scaled, one, x + 720, y - 60), x + 880, y - 60)

    def fade(self, x=-700, y=-400):
        return self.scalar('FXFade', 1.0, x, y)

    def rgb(self, source, x, y, output=''):
        """float4 -> float3.

        MP_EMISSIVE_COLOR takes three components. Feeding it a VectorParameter's
        four-component output is a material compile error, not a silent truncation,
        so every colour goes through here on its way to the emissive input.
        """
        return self.mask(source, x, y, r=True, g=True, b=True, output=output)

    def pad(self, names, x, y):
        """Keep director-driven parameters this material does not otherwise use alive
        in the compiled graph, at exactly zero weight.

        AMikdashFXDirector writes the same six parameters on every card. A material
        that does not use one still has to HAVE it, or the write lands nowhere and
        the effect quietly stops responding. A parameter node that feeds nothing is
        not reliably part of the compiled material, so each unused one is multiplied
        by zero and summed into the opacity: present, and provably worth nothing.
        Returns None for an empty list.
        """
        if not names:
            return None
        zero = self.const(0.0, x, y - 100)
        acc = None
        for i, name in enumerate(names):
            term = self.mul(self.scalar(name, 0.0, x, y + i * 120), zero, x + 220, y + i * 120)
            acc = term if acc is None else self.add(acc, term, x + 440, y + i * 120)
        return acc

    def try_depth_fade(self, alpha, x, y, distance=90.0):
        """Soften the line where a translucent card cuts into solid geometry.

        Optional on purpose. MaterialExpressionDepthFade has no precedent in this
        project, so if its pin names are not what this expects in some engine
        version, the effect ships without the softening and the receipt says so,
        rather than failing an entire placement run over a nicety.
        """
        try:
            node = self.node(self.ue.MaterialExpressionDepthFade, x, y)
            # Declared InOpacity, shown as "Opacity". Both offered.
            self.wire(alpha, node, ('Opacity', 'InOpacity', 'None', ''))
            self.wire(self.scalar('DepthFadeDistance', float(distance), x - 220, y + 160),
                      node, ('FadeDistance', 'Fade Distance', 'Distance'))
            self.record['depthFade'] = 'wired'
            return node
        except Exception as error:                               # noqa: BLE001
            self.record['depthFade'] = 'not wired, shipping without it: %r' % (error,)
            return alpha

    def opacity(self, alpha, pad_names, x, y):
        """Clamp the alpha, folding in the zero-weight pad, and wire MP_OPACITY."""
        padding = self.pad(pad_names, x - 600, y + 300)
        if padding is not None:
            alpha = self.add(alpha, padding, x, y)
        self.to_property(self.clamp01(alpha, x + 200, y), 'MP_OPACITY')


def _create_material(ue, assets, tools, folder, name, record):
    path = folder + '/' + name
    if assets.does_asset_exist(path):
        raise RuntimeError('Material already exists; namespace must be fresh: ' + path)
    material = tools.create_asset(name, folder, ue.Material, ue.MaterialFactoryNew())
    if not isinstance(material, ue.Material):
        raise RuntimeError('Material factory failed for ' + path)
    record['asset'] = path
    return material


def build_flame_material(ue, graph, textures):
    """Additive flame card. Emissive is the whole look; opacity gates the additive."""
    g = graph
    mask_type, _ = _enum(ue, 'MaterialSamplerType', 'SAMPLERTYPE_MASKS', 'SAMPLERTYPE_LINEAR_COLOR')

    uv = g.shared_uv()
    offset = g.scroll_offset()
    nuv = g.noise_uv(uv, offset)

    flame = g.sampler('FlameTex', textures['T_FX_Flame_Card_512'], uv, -1200, -600, mask_type)
    noise = g.sampler('NoiseTex', textures['T_FX_Noise_fBm_512'], nuv, -1000, 520, mask_type)

    body = g.mask(flame, -1000, -700, r=True)
    ramp = g.mask(flame, -1000, -560, g=True)
    core = g.mask(flame, -1000, -420, b=True)
    noise_r = g.mask(noise, -800, 520, r=True)

    erode = g.erosion(noise_r, ramp)
    shape = g.mul(body, erode, -500, -650)

    core_boost = g.scalar('CoreBoost', 3.2, -1000, -260)
    core_lit = g.clamp01(g.mul(core, core_boost, -820, -300), -640, -300)
    edge_colour = g.vector('EdgeColour', (1.0, 0.33, 0.06, 1.0), -1000, -120)
    core_colour = g.vector('CoreColour', (1.0, 0.86, 0.56, 1.0), -1000, 40)
    colour = g.rgb(g.lerp(edge_colour, core_colour, core_lit, -640, -60), -460, -60)

    # Flicker to a strictly positive multiplier: 1 + depth * FXFlicker, clamped at
    # zero so a runaway value can never make the emissive negative.
    depth = g.scalar('FlickerDepth', 0.28, -1000, 200)
    flick = g.scalar('FXFlicker', 0.0, -1000, 340)
    one = g.const(1.0, -820, 260)
    mult = g.node(ue.MaterialExpressionMax, -520, 260)
    raw = g.add(one, g.mul(depth, flick, -820, 400), -660, 320)
    g.wire(raw, mult, 'A')
    g.wire(g.const(0.0, -660, 460), mult, 'B')

    emissive_scale = g.scalar('EmissiveScale', 24.0, -1000, 700)
    fade = g.fade()

    lit = g.mul(colour, shape, -300, -300)
    lit = g.mul(lit, mult, -140, -300)
    lit = g.mul(lit, emissive_scale, 20, -300)
    lit = g.mul(lit, fade, 180, -300)
    g.to_property(lit, 'MP_EMISSIVE_COLOR')

    # FXAge drives nothing on a flame card: a flame is not aged, it is flickered.
    # It still has to exist, because the director writes it on every card.
    g.opacity(g.mul(shape, fade, 20, 120), ['FXAge'], 180, 120)


def build_smoke_material(ue, graph, textures):
    """Translucent smoke puff. Unlit: the colour ramp does the lighting by hand."""
    g = graph
    mask_type, _ = _enum(ue, 'MaterialSamplerType', 'SAMPLERTYPE_MASKS', 'SAMPLERTYPE_LINEAR_COLOR')

    uv = g.shared_uv()
    offset = g.scroll_offset()
    nuv = g.noise_uv(uv, offset)
    noise = g.sampler('NoiseTex', textures['T_FX_Noise_fBm_512'], nuv, -1000, 520, mask_type)
    noise_r = g.mask(noise, -800, 480, r=True)
    noise_g = g.mask(noise, -800, 620, g=True)

    # Distort the smoke UV with the noise so the puff boils instead of sliding.
    strength = g.scalar('DistortStrength', 0.055, -1000, 760)
    half = g.const(0.5, -1000, 900)
    du = g.mul(g.sub(noise_r, half, -640, 480), strength, -480, 480)
    dv = g.mul(g.sub(noise_g, half, -640, 620), strength, -480, 620)
    smoke_uv = g.add(uv, g.append(du, dv, -320, 550), -160, 400)

    smoke = g.sampler('SmokeTex', textures['T_FX_Smoke_Puff_512'], smoke_uv, 0, 400, mask_type)
    density = g.mask(smoke, 200, 340, r=True)
    ramp = g.mask(smoke, 200, 480, g=True)

    erode = g.erosion(noise_r, ramp, x=300, y=900)
    shape = g.mul(density, erode, 1300, 400)

    # Smoke leaving a fire is lit by it; smoke thirty metres up is not. FXAge is the
    # normalised height along the column, so the colour ramp is a height ramp.
    age = g.scalar('FXAge', 0.0, -1000, -700)
    lit_colour = g.vector('LitColour', (0.92, 0.62, 0.36, 1.0), -1000, -560)
    smoke_colour = g.vector('SmokeColour', (0.36, 0.34, 0.32, 1.0), -1000, -420)
    colour = g.rgb(g.lerp(lit_colour, smoke_colour, age, -700, -520), -520, -520)
    g.to_property(colour, 'MP_EMISSIVE_COLOR')

    scale = g.scalar('OpacityScale', 0.55, -1000, -260)
    floor = g.scalar('OpacityFloor', 0.05, -1000, -120)
    fade = g.fade(x=-1000, y=20)
    alpha = g.mul(g.mul(shape, scale, 1500, 400), fade, 1660, 400)
    # A floor so a very tall column never reads as perfectly clear, matching
    # FPlumeProfile::MinOpacity. Max, not Add, so the floor is a floor.
    floored = g.node(ue.MaterialExpressionMax, 1820, 400)
    g.wire(alpha, floored, 'A')
    g.wire(g.mul(floor, fade, 1660, 560), floored, 'B')
    # Smoke does not flicker; the fire under it does. FXFlicker exists here only
    # because the director writes it on every card.
    softened = g.try_depth_fade(floored, 1980, 400)
    g.opacity(softened, ['FXFlicker'], 2180, 400)


def build_point_material(ue, graph, textures):
    """Additive point sprite: embers, and dust motes through an instance override."""
    g = graph
    mask_type, _ = _enum(ue, 'MaterialSamplerType', 'SAMPLERTYPE_MASKS', 'SAMPLERTYPE_LINEAR_COLOR')
    uv = g.shared_uv()
    point = g.sampler('PointTex', textures['T_FX_Ember_64'], uv, -1200, 0, mask_type)
    soft = g.mask(point, -1000, -80, r=True)
    hard = g.mask(point, -1000, 60, g=True)
    hardness = g.scalar('Hardness', 0.5, -1000, 200)
    dot = g.lerp(soft, hard, hardness, -800, 0)

    colour = g.vector('Colour', (1.0, 0.46, 0.12, 1.0), -1000, 360)
    scale = g.scalar('EmissiveScale', 18.0, -1000, 500)
    fade = g.fade(x=-1000, y=640)
    colour3 = g.rgb(colour, -800, 360)
    lit = g.mul(g.mul(g.mul(colour3, dot, -600, 200), scale, -440, 200), fade, -280, 200)
    g.to_property(lit, 'MP_EMISSIVE_COLOR')
    # A point sprite has no UV motion of its own, so it is the one material that does
    # not build a scroll offset, and FXSeed lands in the pad with the rest.
    g.opacity(g.mul(dot, fade, -440, 560), ['FXSeed', 'FXErosion', 'FXAge', 'FXFlicker'], -200, 560)


def build_shaft_material(ue, graph, textures):
    """Additive light-shaft beam. Fades out when you look along it, not across it."""
    g = graph
    mask_type, _ = _enum(ue, 'MaterialSamplerType', 'SAMPLERTYPE_MASKS', 'SAMPLERTYPE_LINEAR_COLOR')
    uv = g.shared_uv()
    offset = g.scroll_offset()
    nuv = g.noise_uv(uv, offset)

    shaft = g.sampler('ShaftTex', textures['T_FX_LightShaft_256'], uv, -1200, -400, mask_type)
    noise = g.sampler('NoiseTex', textures['T_FX_Noise_fBm_512'], nuv, -1000, 520, mask_type)
    cross = g.mask(shaft, -1000, -480, r=True)
    length = g.mask(shaft, -1000, -340, g=True)
    grain = g.mask(noise, -800, 520, r=True)

    # A shaft is a sheet of lit air. Seen edge on it should vanish, and a card that
    # does not do this is the single most obvious way a fake shaft gives itself away.
    camera = g.node(ue.MaterialExpressionCameraVectorWS, -1200, 900)
    normal = g.node(ue.MaterialExpressionVertexNormalWS, -1200, 1040)
    facing = g.node(ue.MaterialExpressionDotProduct, -1000, 960)
    g.wire(camera, facing, 'A')
    g.wire(normal, facing, 'B')
    facing_abs = g.node(ue.MaterialExpressionAbs, -840, 960)
    g.wire(facing, facing_abs, 'Input')
    # Declared `Exponent`, shown as "Exp". If neither spelling resolves, the falloff
    # becomes a constant on the node instead of a tunable parameter, and the receipt
    # says so: a shaft that cannot be re-tuned per instance is a much smaller problem
    # than a placement run that will not finish.
    power = g.node(ue.MaterialExpressionPower, -680, 960, const_exponent=2.5)
    g.wire(facing_abs, power, 'Base')
    falloff = g.scalar('ViewFalloffPower', 2.5, -840, 1120)
    g.record['viewFalloffPin'] = g.try_wire(falloff, power, ('Exp', 'Exponent', 'None')) \
        or 'not wired; const_exponent 2.5 stands and ViewFalloffPower is inert'

    grain_strength = g.scalar('GrainStrength', 0.25, -1000, 700)
    one = g.const(1.0, -1000, 840)
    half = g.const(0.5, -820, 700)
    grain_mult = g.add(one, g.mul(g.sub(grain, half, -640, 640), grain_strength, -480, 640), -320, 700)

    beam = g.mul(g.mul(cross, length, -600, -400), power, -440, -400)
    beam = g.mul(beam, grain_mult, -280, -400)

    colour = g.vector('Colour', (1.0, 0.93, 0.78, 1.0), -1000, -100)
    scale = g.scalar('EmissiveScale', 1.1, -1000, 40)
    fade = g.fade(x=-1000, y=180)
    colour3 = g.rgb(colour, -820, -100)
    lit = g.mul(g.mul(g.mul(colour3, beam, -100, -200), scale, 60, -200), fade, 220, -200)
    g.to_property(lit, 'MP_EMISSIVE_COLOR')
    g.opacity(g.mul(beam, fade, 60, 60), ['FXErosion', 'FXAge', 'FXFlicker'], 260, 60)


def build_haze_material(ue, graph, textures):
    """Translucent refraction-only card: heat shimmer over the courts, no colour."""
    g = graph
    mask_type, _ = _enum(ue, 'MaterialSamplerType', 'SAMPLERTYPE_MASKS', 'SAMPLERTYPE_LINEAR_COLOR')
    uv = g.shared_uv()
    offset = g.scroll_offset()
    nuv = g.noise_uv(uv, offset)
    noise = g.sampler('NoiseTex', textures['T_FX_Noise_fBm_512'], nuv, -1000, 0, mask_type)
    noise_r = g.mask(noise, -800, -60, r=True)

    fade = g.fade(x=-1000, y=400)
    strength = g.scalar('RefractionStrength', 1.012, -1000, 540)
    one = g.const(1.0, -1000, 680)
    # Blend the index of refraction toward 1 as the card fades, so a hidden card
    # distorts nothing at all rather than being invisible but still bending light.
    blend = g.mul(noise_r, fade, -600, 0)
    ior = g.lerp(one, strength, blend, -400, 300)
    if hasattr(ue.MaterialProperty, 'MP_REFRACTION'):
        g.to_property(ior, 'MP_REFRACTION')
        graph.record['refractionWired'] = True
    else:
        graph.record['refractionWired'] = False

    scale = g.scalar('OpacityScale', 0.02, -1000, 820)
    g.opacity(g.mul(scale, fade, -600, 820), ['FXErosion', 'FXAge', 'FXFlicker'], -380, 820)
    black = g.node(ue.MaterialExpressionConstant3Vector, -600, 1000,
                   constant=ue.LinearColor(0.0, 0.0, 0.0, 1.0))
    g.to_property(black, 'MP_EMISSIVE_COLOR')


MATERIAL_BUILDERS = {
    'M_FX_Flame': build_flame_material,
    'M_FX_Smoke': build_smoke_material,
    'M_FX_Point': build_point_material,
    'M_FX_Shaft': build_shaft_material,
    'M_FX_HeatHaze': build_haze_material,
}

BLEND_MODES = {'Additive': 'BLEND_ADDITIVE', 'Translucent': 'BLEND_TRANSLUCENT',
               'Masked': 'BLEND_MASKED', 'Opaque': 'BLEND_OPAQUE'}
SHADING_MODELS = {'Unlit': 'MSM_UNLIT', 'DefaultLit': 'MSM_DEFAULT_LIT'}


def import_textures(ue, spec, manifest, assets, tools, receipt):
    """Import the six baked PNGs as mask textures, verified by readback.

    sRGB is forced off and the compression is TC_MASKS: every channel here is a
    number, not a colour, and a gamma curve on a mask is the classic way an effect
    that is right in the bake is wrong in the engine.
    """
    cfg = spec['textureImport']
    folder = spec['textureFolder']
    out = {}
    receipt['textures'] = []
    compression, compression_name = _enum(ue, 'TextureCompressionSettings',
                                          cfg['compression'], cfg['compressionFallback'])
    for entry in manifest['textures']:
        source = ROOT / entry['file']
        if sha256_of(source) != entry['sha256']:
            raise RuntimeError('%s on disk does not match the manifest sha256' % entry['name'])
        path = folder + '/' + entry['name']
        if assets.does_asset_exist(path):
            raise RuntimeError('Texture already exists; namespace must be fresh: ' + path)
        task = ue.AssetImportTask()
        for prop, value in dict(filename=str(source), destination_path=folder,
                                destination_name=entry['name'], automated=True,
                                replace_existing=False, save=False).items():
            task.set_editor_property(prop, value)
        tools.import_asset_tasks([task])
        objects = list(task.get_objects())
        if len(objects) != 1 or not isinstance(objects[0], ue.Texture2D):
            raise RuntimeError('Texture import of %s produced %s'
                               % (source, [type(o).__name__ for o in objects]))
        tex = objects[0]
        tex.set_editor_property('compression_settings', compression)
        tex.set_editor_property('srgb', bool(cfg['srgb']))
        try:
            tex.set_editor_property('virtual_texture_streaming', bool(cfg['virtualTextureStreaming']))
        except Exception:                                        # noqa: BLE001
            pass
        for axis, key in (('address_x', 'addressX'), ('address_y', 'addressY')):
            try:
                mode, _ = _enum(ue, 'TextureAddress', entry[key].upper())
                tex.set_editor_property(axis, mode)
            except Exception:                                    # noqa: BLE001
                pass
        if not assets.save_loaded_asset(tex, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + entry['name'])

        # Readback. Setter return values are not trusted anywhere in this script.
        srgb_now = bool(tex.get_editor_property('srgb'))
        compression_now = str(tex.get_editor_property('compression_settings'))
        if srgb_now != bool(cfg['srgb']):
            raise RuntimeError('%s sRGB read back %r' % (entry['name'], srgb_now))
        size = None
        for getter in ('blueprint_get_size_x', 'get_size_x'):
            if hasattr(tex, getter):
                try:
                    size = [int(getattr(tex, getter)()), int(getattr(tex, getter.replace('_x', '_y'))())]
                except Exception:                                # noqa: BLE001
                    size = None
                break
        if size and size != [entry['width'], entry['height']]:
            raise RuntimeError('%s imported at %r, manifest says %r'
                               % (entry['name'], size, [entry['width'], entry['height']]))
        out[entry['name']] = tex
        receipt['textures'].append({
            'name': entry['name'], 'asset': path, 'sourceSha256': entry['sha256'],
            'srgb': srgb_now, 'compression': compression_now,
            'compressionRequested': compression_name, 'size': size,
            'channels': entry['channels'],
        })
    return out


def create_materials(ue, spec, manifest, assets, tools, textures, receipt):
    """Author the five masters. Every pin name is resolved from the engine."""
    ml = ue.MaterialEditingLibrary
    folder = spec['materialFolder']
    out = {}
    receipt['materials'] = []
    for cfg in manifest['materials']:
        record = {'name': cfg['name']}
        material = _create_material(ue, assets, tools, folder, cfg['name'], record)
        blend, blend_name = _enum(ue, 'BlendMode', BLEND_MODES[cfg['blendMode']])
        shading, shading_name = _enum(ue, 'MaterialShadingModel', SHADING_MODELS[cfg['shadingModel']])
        material.set_editor_property('blend_mode', blend)
        material.set_editor_property('shading_model', shading)
        material.set_editor_property('two_sided', bool(cfg['twoSided']))
        if cfg.get('refraction'):
            try:
                value, name = _enum(ue, 'RefractionMode', 'RM_INDEX_OF_REFRACTION', 'IOR')
                material.set_editor_property('refraction_method', value)
                record['refractionMode'] = name
            except Exception as error:                           # noqa: BLE001
                record['refractionMode'] = 'unavailable: %r' % (error,)

        graph = Graph(ue, material, record)
        MATERIAL_BUILDERS[cfg['name']](ue, graph, textures)

        record['recompileErrors'] = [str(e) for e in (ml.recompile_material(material) or [])][:20]
        if not assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + record['asset'])

        # Acceptance, by readback rather than by the setters' return values.
        scalar_names = [str(n) for n in ml.get_scalar_parameter_names(material)]
        missing = [n for n in SHARED_DYNAMIC if n not in scalar_names]
        if spec['verification']['requireEveryDynamicParameter'] and missing:
            raise RuntimeError('%s is missing the director-driven parameters %s; '
                               'the actor would write into nothing' % (cfg['name'], missing))
        record['scalarParameters'] = sorted(scalar_names)
        record['vectorParameters'] = sorted(str(n) for n in ml.get_vector_parameter_names(material))
        record['blendMode'] = blend_name
        record['shadingModel'] = shading_name
        record['twoSided'] = bool(material.get_editor_property('two_sided'))
        record['inputsWired'] = {}
        for prop_name in ('MP_EMISSIVE_COLOR', 'MP_OPACITY', 'MP_REFRACTION'):
            if not hasattr(ue.MaterialProperty, prop_name):
                continue
            wired = ml.get_material_property_input_node(material, getattr(ue.MaterialProperty, prop_name))
            record['inputsWired'][prop_name] = wired.get_class().get_name() if wired else None
        receipt['materials'].append(record)
        out[cfg['name']] = material
    return out


def _linear(value):
    return [float(value.r), float(value.g), float(value.b), float(value.a)]


def set_instance_parameter(ue, ml, instance, kind, name, value, record):
    """One MIC parameter, verified by readback, with the struct-array fallback.

    UE 5.8 fact: set_material_instance_{scalar,vector,texture}_parameter_value writes
    the value and then returns a bResult that was never assigned, so it is always
    False. Only the readback decides. The fallback writes the parameter struct
    directly and must stamp Association = GlobalParameter and Index = -1; a
    Python-default struct would carry LayerParameter/0 and the global lookup would
    never find it.
    """
    getters = {'scalar': ml.get_material_instance_scalar_parameter_value,
               'vector': ml.get_material_instance_vector_parameter_value,
               'texture': ml.get_material_instance_texture_parameter_value}
    setters = {'scalar': ml.set_material_instance_scalar_parameter_value,
               'vector': ml.set_material_instance_vector_parameter_value,
               'texture': ml.set_material_instance_texture_parameter_value}

    def read():
        got = getters[kind](instance, name)
        if kind == 'scalar':
            return float(got)
        if kind == 'vector':
            return _linear(got)
        return _asset_path(got)

    def matches(got):
        if kind == 'scalar':
            return abs(got - float(value)) <= 1e-4
        if kind == 'vector':
            return max(abs(a - b) for a, b in zip(got[:3], _linear(value)[:3])) <= 1e-4
        return got == _asset_path(value)

    instance.modify(True)
    returned = setters[kind](instance, name, value)
    ml.update_material_instance(instance)
    got = read()
    path = 'set_material_instance_%s_parameter_value (return %s, always False, ignored)' % (kind, returned)
    if not matches(got) and kind in ('scalar', 'vector'):
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
        path = 'set_editor_property(%s) struct fallback' % prop
    if not matches(got):
        raise RuntimeError('Parameter %s on %s read back %r after %s'
                           % (name, instance.get_name(), got, path))
    record[name] = {'value': got, 'path': path}
    return got


def create_instances(ue, spec, manifest, assets, tools, materials, textures, receipt):
    ml = ue.MaterialEditingLibrary
    folder = spec['materialFolder']
    out = {}
    receipt['instances'] = []
    for cfg in manifest['materials']:
        master = materials[cfg['name']]
        for inst in cfg.get('instances', []):
            path = folder + '/' + inst['name']
            if assets.does_asset_exist(path):
                raise RuntimeError('Instance already exists; namespace must be fresh: ' + path)
            instance = tools.create_asset(inst['name'], folder, ue.MaterialInstanceConstant,
                                          ue.MaterialInstanceConstantFactoryNew())
            if not isinstance(instance, ue.MaterialInstanceConstant):
                raise RuntimeError('MaterialInstanceConstant factory failed for ' + path)
            # Parent first: parameters only resolve against a compiled parent, and
            # the master above was recompiled and saved before we got here.
            ml.set_material_instance_parent(instance, master)
            if _asset_path(instance.get_editor_property('parent')) != _asset_path(master):
                instance.set_editor_property('parent', master)
                ml.update_material_instance(instance)
            if _asset_path(instance.get_editor_property('parent')) != _asset_path(master):
                raise RuntimeError('Instance %s did not take its parent' % inst['name'])

            record = {'name': inst['name'], 'asset': path, 'parent': _asset_path(master),
                      'parameters': {}}
            for name, value in inst.get('scalars', {}).items():
                set_instance_parameter(ue, ml, instance, 'scalar', name, float(value), record['parameters'])
            for name, rgba in inst.get('vectors', {}).items():
                set_instance_parameter(ue, ml, instance, 'vector', name,
                                       ue.LinearColor(*[float(c) for c in rgba]), record['parameters'])
            for name, tex_name in inst.get('textures', {}).items():
                set_instance_parameter(ue, ml, instance, 'texture', name, textures[tex_name],
                                       record['parameters'])
            ml.update_material_instance(instance)
            if not assets.save_loaded_asset(instance, only_if_is_dirty=False):
                raise RuntimeError('save_loaded_asset failed for ' + path)
            receipt['instances'].append(record)
            out[inst['name']] = instance
    return out


def _encode(value):
    """JSON-safe view of a UE value, for the receipt."""
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, str):
        return value
    if isinstance(value, float):
        return round(value, 5)
    if hasattr(value, 'x') and hasattr(value, 'y') and hasattr(value, 'z'):
        return [round(float(value.x), 4), round(float(value.y), 4), round(float(value.z), 4)]
    if isinstance(value, (list, tuple)):
        return [_encode(v) for v in value]
    try:
        return [_encode(v) for v in list(value)]
    except TypeError:
        return str(value)


def _set_actor_property(actor, name, value, record, required=True):
    """Write one property and read it straight back. No setter return is trusted."""
    try:
        actor.set_editor_property(name, value)
    except Exception as error:                                   # noqa: BLE001
        if required:
            raise RuntimeError('set_editor_property(%s) failed: %r' % (name, error))
        record[name] = 'unavailable: %r' % (error,)
        return None
    got = actor.get_editor_property(name)
    record[name] = _encode(got) if not hasattr(got, 'get_path_name') else _asset_path(got)
    return got


def place(load_target=True):
    """Run the guarded placement. Returns the receipt dict; raises on any guard."""
    import unreal as ue

    spec = load_spec()
    manifest = load_manifest(spec)
    offline = offline_check(spec)
    if offline['problems']:
        raise RuntimeError('Offline check failed: %s' % offline['problems'][:5])

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())

    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()

    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target and not levels.load_level(TARGET):
        raise RuntimeError('load_level failed for ' + TARGET)
    world = editor.get_editor_world()
    loaded = world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
            ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed placement')

    # The binary must already contain the class this whole feature is. An actor of a
    # class the editor does not know would place as a broken stub and drive nothing.
    required = spec['compiledClassesRequired']
    actor_class = getattr(ue, required['fxDirector'], None)
    if actor_class is None:
        raise RuntimeError('unreal.%s is missing; rebuild MikdashRuntime before running this'
                           % required['fxDirector'])
    try:
        ue.get_default_object(actor_class).get_editor_property(required['propertyProvingFreshBinary'])
    except Exception as error:                                   # noqa: BLE001
        raise RuntimeError('%s has no %s; the editor binary predates this feature (%r)'
                           % (required['fxDirector'], required['propertyProvingFreshBinary'], error))

    conf = spec['actor']
    if conf['refuseIfLabelExists']:
        existing = [a.get_actor_label() for a in actors.get_all_level_actors()
                    if a and a.get_actor_label() == conf['label']]
        if existing:
            raise RuntimeError('%s already exists; refusing duplicate placement' % conf['label'])

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps']
                 if disk_path(m, 'umap').exists()}

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
    receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(receipt_path))

    receipt = {
        'status': 'checkpointed_placement_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'manifestSha256': sha256_of(ROOT / spec['manifest']),
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'offlineCheck': offline,
        'mathHeader': manifest['mathHeader'],
        'mathTest': manifest['mathTest'],
        'sourceClaims': manifest['sourceClaims'],
        'effectTable': manifest['effects'],
        'gpuBudget': manifest['derived']['budget'],
        'honesty': manifest['honesty'],
        'limitations': spec['limitations'] + manifest['limitations'],
        'niagaraProbe': None,
        'placed': None,
        'errors': [],
        'mapSaved': False,
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, default=str),
                                encoding='utf-8')

    write()

    saved = False
    spawned = None
    try:
        # Try Niagara first and record what was actually there, then take the
        # material path deliberately rather than by omission.
        receipt['niagaraProbe'] = probe_niagara(ue)
        receipt['effectPath'] = receipt['niagaraProbe']['decision']
        write()

        textures = import_textures(ue, spec, manifest, assets, tools, receipt)
        materials = create_materials(ue, spec, manifest, assets, tools, textures, receipt)
        instances = create_instances(ue, spec, manifest, assets, tools, materials, textures, receipt)
        write()

        card_mesh = ue.load_asset(spec['cardMesh'])
        if card_mesh is None:
            raise RuntimeError('Card mesh not found: ' + spec['cardMesh'])

        spawned = actors.spawn_actor_from_class(
            actor_class, ue.Vector(*[float(v) for v in conf['spawnLocation']]),
            ue.Rotator(), transient=False)
        if not spawned:
            raise RuntimeError('FX director spawn failed')
        spawned.set_actor_label(conf['label'])
        spawned.set_folder_path(conf['folder'])
        spawned.set_editor_property('tags', [ue.Name(conf['tag'])])
        spawned_name = spawned.get_name()

        props = {}
        _set_actor_property(spawned, 'card_mesh', card_mesh, props)
        for prop, inst_name in (
                ('flame_altar_material', 'MI_FX_Flame_Altar'),
                ('flame_lamp_material', 'MI_FX_Flame_Lamp'),
                ('smoke_column_material', 'MI_FX_Smoke_Column'),
                ('smoke_ketores_material', 'MI_FX_Smoke_Ketores'),
                ('smoke_ceiling_material', 'MI_FX_Smoke_Ceiling'),
                ('smoke_haze_material', 'MI_FX_Haze_Smoke'),
                ('ember_material', 'MI_FX_Ember'),
                ('dust_mote_material', 'MI_FX_DustMote'),
                ('light_shaft_material', 'MI_FX_LightShaft'),
                ('heat_haze_material', 'MI_FX_HeatHaze')):
            _set_actor_property(spawned, prop, instances[inst_name], props)

        anchors = manifest['anchors']
        fire = list(anchors['outerAltarCentre']['value']) + [anchors['outerAltarFireTopZ']['value']]
        _set_actor_property(spawned, 'outer_altar_fire_cm', ue.Vector(*[float(v) for v in fire]), props)
        golden = anchors['goldenAltarCentre']['value']
        _set_actor_property(spawned, 'golden_altar_top_cm',
                            ue.Vector(float(golden[0]), float(golden[1]),
                                      float(anchors['goldenAltarTopZ']['value'])), props)

        lamps = manifest['derived']['lamps']
        _set_actor_property(spawned, 'lamp_flame_cm',
                            [ue.Vector(*[float(c) for c in p]) for p in lamps['positions']], props)
        _set_actor_property(spawned, 'lamp_light_cm',
                            [ue.Vector(float(p[0]), float(p[1]), float(lamps['lightZCm']))
                             for p in lamps['positions']], props)

        for name, value in spec['actorProperties'].items():
            _set_actor_property(spawned, name, value, props, required=False)

        spawned.modify()

        # The shaft transforms are deliberately NOT written: the Heikhal window
        # arrangement is not settled, so the actor resolves its own authored
        # defaults at BeginPlay and the receipt records that as needs_review rather
        # than baking an unreviewed number into the map.
        receipt['shaftTransforms'] = ('left to the actor defaults; needs_review, see '
                                      'anchorProvenance.shaft_transforms')

        numeric = {str(k): round(float(v), 4)
                   for k, v in dict(spawned.get_numeric_readback()).items()}
        receipt['placed'] = {
            'label': spawned.get_actor_label(),
            'name': spawned_name,
            'class': spawned.get_class().get_name(),
            'folder': str(spawned.get_folder_path()),
            'tags': [str(t) for t in spawned.tags],
            'location': _encode(spawned.get_actor_location()),
            'properties': props,
            'numeric': numeric,
        }

        if spec['verification']['requireKetoresBelowCeiling']:
            top = numeric.get('ketoresColumnTopZCm')
            ceiling = numeric.get('heikhalCeilingZCm')
            if top is None or ceiling is None or top > ceiling:
                raise RuntimeError('Ketores column top %r is not under the ceiling %r; the smoke '
                                   'would leave the roof' % (top, ceiling))
        if int(numeric.get('lampCount', 0)) != spec['verification']['requireLampCount']:
            raise RuntimeError('lampCount read back as %r' % numeric.get('lampCount'))
        if numeric.get('outerAltarStraightColumn') != 1.0:
            raise RuntimeError('The outer altar column is not the Avos 5:5 straight column')
        if abs(numeric.get('outerAltarAxisOffsetAtTopCm', 1.0)) > 1e-6:
            raise RuntimeError('The straight column has a lateral offset of %r cm'
                               % numeric.get('outerAltarAxisOffsetAtTopCm'))
        write()

        # UE 5.8: the spawn itself dirties the map. Prove it rather than assume.
        if not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('The map is not dirty after the spawn; nothing would be saved')
        if ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            dirty = [p.get_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
            raise RuntimeError('Dirty content packages before the map save '
                               '(assets must be saved explicitly): %s' % dirty)

        receipt['editorProcessesAtSave'] = running_editor_processes()
        if not levels.save_current_level():
            raise RuntimeError(
                'save_current_level returned False. Before treating this as a real failure, check '
                'the process list recorded in editorProcessesAtSave for a leftover UnrealEditor '
                'holding the package: %r' % receipt['editorProcessesAtSave'])
        saved = True
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha256_of(map_file)
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('Map still dirty after save')
        write()

        if not levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Reopened world is not the target map')
        matching = [a for a in actors.get_all_level_actors()
                    if a and a.get_actor_label() == conf['label']]
        if len(matching) != 1:
            raise RuntimeError('Reopened actor count for %s is %d' % (conf['label'], len(matching)))
        reopened = matching[0]
        if not reopened.get_class().get_name().startswith(required['fxDirector']):
            raise RuntimeError('Reopened actor class is %s' % reopened.get_class().get_name())

        reopened_numeric = {str(k): round(float(v), 4)
                            for k, v in dict(reopened.get_numeric_readback()).items()}
        drift = sorted(k for k, v in reopened_numeric.items()
                       if abs(v - numeric.get(k, v)) > spec['verification']['scalarTolerance'])
        if drift:
            raise RuntimeError('Numbers changed across the save/reopen: %r' % drift[:10])

        tol = spec['verification']['transformToleranceCm']
        location = _encode(reopened.get_actor_location())
        if max(abs(a - b) for a, b in zip(location, conf['spawnLocation'])) > tol:
            raise RuntimeError('Reopened location %r differs from %r'
                               % (location, conf['spawnLocation']))

        reopened_assets = {}
        for prop in ('flame_altar_material', 'flame_lamp_material', 'smoke_column_material',
                     'smoke_ketores_material', 'smoke_ceiling_material', 'smoke_haze_material',
                     'ember_material', 'dust_mote_material', 'light_shaft_material',
                     'heat_haze_material', 'card_mesh'):
            reopened_assets[prop] = _asset_path(reopened.get_editor_property(prop))
            if reopened_assets[prop] is None:
                raise RuntimeError('%s is empty after the reopen' % prop)

        receipt['reopenedReadback'] = {
            'label': reopened.get_actor_label(),
            'name': reopened.get_name(),
            'class': reopened.get_class().get_name(),
            'folder': str(reopened.get_folder_path()),
            'tags': [str(t) for t in reopened.tags],
            'location': location,
            'numeric': reopened_numeric,
            'assets': reopened_assets,
            'lampFlameCm': _encode(reopened.get_editor_property('lamp_flame_cm')),
            'sourceNote': str(reopened.get_source_note()),
            'status': str(reopened.get_status()),
        }
        receipt['status'] = 'fx_materials_and_director_saved_reopened_visual_acceptance_pending'
        write()
        return receipt

    except Exception as error:                                   # noqa: BLE001
        receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                             else 'failed_before_save_map_unchanged')
        if not saved and spawned:
            try:
                actors.destroy_actor(spawned)
                receipt['partialActorDestroyed'] = True
            except Exception as cleanup:                         # noqa: BLE001
                receipt['errors'].append({'stage': 'cleanup', 'error': repr(cleanup)})
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
        receipt['editorProcessesAtEnd'] = running_editor_processes()
        write()


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
    return ('release_fx.py' in command_line
            and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line))


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    try:
        receipt = place(load_target=True)
        ue.log('release_fx: %s (%d textures, %d materials, %d instances)'
               % (receipt['status'], len(receipt.get('textures', [])),
                  len(receipt.get('materials', [])), len(receipt.get('instances', []))))
    except Exception as error:                                   # noqa: BLE001
        ue.log_error('release_fx failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2, ensure_ascii=False))
elif _invoked_as_native_script():
    _main()

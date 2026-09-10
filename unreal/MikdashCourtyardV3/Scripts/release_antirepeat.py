"""Break the tiling repetition in the material graph, reversibly, without touching one texel of an approved texture.

Shmuel, verbatim, 2026-09-09: "I don't wanna see, like, repeating patterns all over."

Consumes Scripts/release_antirepeat.spec.json and the offline measurement written by
Scripts/create_antirepeat_materials.py. Builds TWO NEW master materials and FIVE NEW instances under
/Game/MikdashV3/MaterialReview/AntiRepeatV1/ that render the SAME approved textures through a
repetition-breaking UV and macro-variation layer, then moves component material slot overrides onto
them. Modelled on Scripts/release_herodian_ashlar_v4.py; the guard pattern is identical.

  -AntiRepeatPlan -Candidate48|-Main50    READ-ONLY census: every static-mesh material slot, what each
                                          rule would touch, the enclosure WallMaterial actors, and the
                                          numbers a null expectedVariantSlotCount needs. Saves nothing.
  -AntiRepeatBuild [-AntiRepeatRebuild]   import the macro-noise texture, build M_AntiRepeat_Triplanar
                                          and M_AntiRepeat_Planar, create the five instances, set both
                                          usage overrides, save, reload, read back, and record the
                                          compiled shader statistics against M_PBR_Tiled's.
  -AntiRepeatApply=<build receipt> -Candidate48|-Main50 [-AntiRepeatPriority=N]
                                          checkpoint the map, move the slots and the enclosure actor
                                          property, read back, save, reopen, read back.
  -AntiRepeatVerify=<apply receipt>       fresh-process readback only, no save.
  -AntiRepeatRevert=<apply receipt>       restore the checkpointed map bytes, or the recorded per-slot
                                          and per-actor before-values if the map has moved on.
  -AntiRepeatPriority=1                   stone only (default). =2 adds the paving.
  -AntiRepeatAllowCountDrift              accept a slot count that differs from the target's census.

Never touched: M_PBR_Tiled, the ten MI_PBR_* instances, the three MI_HerodianV4_* instances and their
usage flags, every approved texture, the Kotel materials, the Old City context materials, and the map
that is NOT the selected target (it joins the protected set for the run). Everything is hashed before
and after; a mismatch fails the run. 5.8's MaterialEditingLibrary setters return False even on success,
so every set is verified by readback. The receipt is written at start, after each stage and in finally.

Commandlet (strictly serial; check Get-Process UnrealEditor,UnrealEditor-Cmd first; unique -abslog):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe" "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript -unattended -nullrhi -abslog="C:/Mikdash/Working-5.8/AntiRepeat-Build-01.log"
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_antirepeat.py" -AntiRepeatBuild
Offline:  python Scripts/release_antirepeat.py  -> offline_check(): spec/manifest cross-check, the
scheme consistency check and the planned rule table.
"""
import glob
import hashlib
import json
import re
import shutil
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_antirepeat.spec.json'
USAGE_FLAGS = ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES')

# ---------------------------------------------------------------------------------------------
# HLSL. One hash, one UV warp, used by every node in both masters, so the shipped transform and the
# transform Scripts/create_antirepeat_materials.py measured are the same transform.
#
# AR_HASH  frac(sin(fmod(a, 2*pi)) * 43758.5453). The fmod is load-bearing: without it the argument
#          on a cell a thousand tiles from the origin is ~1e5 and fp32 sin has lost the precision
#          that makes neighbouring cells independent. This scene is 1.44 km across.
# AR_WARP  band offset (a whole course band slides along u by a hash of its OWN index, so the shift
#          is constant along the wall and no vertical seam exists), then per-cell mirror in u (a
#          mirrored cell still meets its neighbours edge to edge because the tile is periodic).
#          Returns a WRAPPED uv so the address mode is irrelevant, plus derivatives taken from the
#          CONTINUOUS pre-warp uv with the mirror sign applied - without those, the one-pixel row
#          where the band offset jumps would take the coarsest mip and draw a line at every bed joint.
# ---------------------------------------------------------------------------------------------
def _hash(x, y, salt):
    """frac(sin(fmod(a, 2*pi)) * 43758.5453), inline.

    The fmod is load-bearing: without it the argument on a cell a thousand tiles from the origin is
    ~1e5, where fp32 sin has lost the precision that makes neighbouring cells independent - and this
    scene is 1.44 km across. Generated from Python rather than an HLSL #define, so no preprocessor
    directive ever lands inside the function body UE wraps a Custom node in."""
    return ('frac(sin(fmod(((%s) + 0.5) * 12.9898 + ((%s) + 0.5) * 78.233 + %s, 6.2831853)) * 43758.5453)'
            % (x, y, salt))


def _warp(uv_expr, tag):
    """The whole anti-repeat UV transform for one sampling plane.

    1. Band offset: the course band (one tile high in v) slides along u by a hash of its OWN index,
       so the shift does not vary along the wall - no vertical seam exists anywhere, and the shift
       shows up only across a bed joint, which is what running bond is.
    2. Cell mirror: the cell is mirrored in u by a hash of its cell index. A mirrored cell still meets
       its neighbours edge to edge because the tile is periodic, and mirroring only in u leaves the
       bed joints, the per-course setback ledge and the downward weather run-off where they were.
    3. The uv handed to the sampler is WRAPPED into [0,1), so the texture address mode cannot change
       the result - T_JerusalemPaving_BaseColor is TA_MIRROR, the architecture textures are TA_WRAP.
    4. The derivatives come from the CONTINUOUS pre-warp uv with the mirror sign applied to u.
       Sampling with implicit derivatives instead would give the one pixel row where the band offset
       jumps a huge gradient, the coarsest mip, and a blurred line along every bed joint."""
    return """
float2 d0_{t} = ddx({uv});
float2 d1_{t} = ddy({uv});
float bj_{t} = floor(({uv}).y);
float uu_{t} = ({uv}).x + BandOffsetEnable * {hband};
float ci_{t} = floor(uu_{t});
float fu_{t} = uu_{t} - ci_{t};
float s_{t} = ((MirrorEnable > 0.5) && ({hmirror} > 0.5)) ? -1.0 : 1.0;
fu_{t} = (s_{t} < 0.0) ? (1.0 - fu_{t}) : fu_{t};
float2 uv_{t} = float2(fu_{t}, ({uv}).y - bj_{t});
float2 dx_{t} = float2(d0_{t}.x * s_{t}, d0_{t}.y);
float2 dy_{t} = float2(d1_{t}.x * s_{t}, d1_{t}.y);
""".format(t=tag, uv=uv_expr, hband=_hash('bj_' + tag, '0.0', '5.71'),
           hmirror=_hash('ci_' + tag, 'bj_' + tag, '0.0'))


# Identical projection and blend exponent to M_PBR_Tiled, so no surface changes which plane it samples.
HLSL_TRIPLANAR_SETUP = """
float3 ar_n = normalize(N);
float3 ar_a = pow(abs(ar_n), max(BlendExponent, 0.001));
float3 ar_w = ar_a / max(dot(ar_a, float3(1.0, 1.0, 1.0)), 1e-6);
float3 ar_q = P / max(TilingCm, 1.0);
""" + _warp('ar_q.yz', 'X') + _warp('ar_q.xz', 'Y') + _warp('ar_q.xy', 'Z')

# Two decorrelated oblique projections of world position. No axis is degenerate on a wall or a floor,
# and the periods are non-harmonic with the tile and with each other, so nothing realigns.
HLSL_MACRO_UV = """
float2 ar_ma = float2(dot(P, float3(1.00, 0.61, 0.23)), dot(P, float3(0.29, -0.37, 1.00))) / max(MacroCm, 1.0);
float2 ar_mb = float2(dot(P, float3(0.44, -0.83, 0.31)), dot(P, float3(0.77, 0.36, -0.52))) / max(MidCm, 1.0);
"""

HLSL_MID_UV = """
float2 ar_mb = float2(dot(P, float3(0.44, -0.83, 0.31)), dot(P, float3(0.77, 0.36, -0.52))) / max(MidCm, 1.0);
"""

HLSL_MACRO_APPLY = """
float3 ar_n1 = Texture2DSampleLevel(MacroNoise, MacroNoiseSampler, ar_ma, 0).rgb;
float  ar_n2 = Texture2DSampleLevel(MacroNoise, MacroNoiseSampler, ar_mb, 0).b;
float ar_inst = (PerInstanceRand > 1e-6) ? (PerInstanceRand - 0.5) * PerInstanceJitter : 0.0;
float ar_gain = 1.0 + MacroAmount * (ar_n1.r - 0.5) + MidAmount * (ar_n2 - 0.5) + ar_inst;
float ar_warm = MacroWarm * (ar_n1.g - 0.5);
ar_c *= max(ar_gain, 0.0);
ar_c.r *= 1.0 + ar_warm;
ar_c.b *= 1.0 - ar_warm;
return max(ar_c, 0.0);
"""

HLSL_ALBEDO = HLSL_TRIPLANAR_SETUP + HLSL_MACRO_UV + """
float3 ar_c = Texture2DSampleGrad(Albedo, AlbedoSampler, uv_X, dx_X, dy_X).rgb * ar_w.x
            + Texture2DSampleGrad(Albedo, AlbedoSampler, uv_Y, dx_Y, dy_Y).rgb * ar_w.y
            + Texture2DSampleGrad(Albedo, AlbedoSampler, uv_Z, dx_Z, dy_Z).rgb * ar_w.z;
""" + HLSL_MACRO_APPLY

HLSL_ARM = HLSL_TRIPLANAR_SETUP + HLSL_MID_UV + """
float3 ar_v = Texture2DSampleGrad(ARM, ARMSampler, uv_X, dx_X, dy_X).rgb * ar_w.x
            + Texture2DSampleGrad(ARM, ARMSampler, uv_Y, dx_Y, dy_Y).rgb * ar_w.y
            + Texture2DSampleGrad(ARM, ARMSampler, uv_Z, dx_Z, dy_Z).rgb * ar_w.z;
float ar_n2 = Texture2DSampleLevel(MacroNoise, MacroNoiseSampler, ar_mb, 0).b;
ar_v.g = saturate(ar_v.g * (1.0 + MidRoughness * (ar_n2 - 0.5) * 2.0));
return ar_v;
"""

# Per-plane tangent deviations swizzled into world axes exactly as M_PBR_Tiled does, with the mirror
# sign applied to the u component of each plane (u is world Y on the X plane, world X on the others).
# A TC_NORMALMAP sample inside a Custom node is raw, so it is decoded here rather than by the sampler.
HLSL_NORMAL = HLSL_TRIPLANAR_SETUP + """
float2 ar_nx = Texture2DSampleGrad(Normal, NormalSampler, uv_X, dx_X, dy_X).rg * 2.0 - 1.0;
float2 ar_ny = Texture2DSampleGrad(Normal, NormalSampler, uv_Y, dx_Y, dy_Y).rg * 2.0 - 1.0;
float2 ar_nz = Texture2DSampleGrad(Normal, NormalSampler, uv_Z, dx_Z, dy_Z).rg * 2.0 - 1.0;
float3 ar_dev = float3(0.0, ar_nx.x * s_X, ar_nx.y) * ar_w.x
              + float3(ar_ny.x * s_Y, 0.0, ar_ny.y) * ar_w.y
              + float3(ar_nz.x * s_Z, ar_nz.y, 0.0) * ar_w.z;
return normalize(ar_n + ar_dev * NormalStrength);
"""

HLSL_PLANAR = HLSL_MACRO_UV + """
float2 ar_uv0 = float2(P.x, P.y) / max(TilingCm, 1.0);
""" + _warp('ar_uv0', 'P') + """
float3 ar_c = Texture2DSampleGrad(Albedo, AlbedoSampler, uv_P, dx_P, dy_P).rgb;
float ar_t = lerp(1.0, smoothstep(0.85, 0.98, normalize(N).z), saturate(SlopeTintEnable));
ar_c = lerp(SlopeTint.rgb, ar_c, ar_t);
""" + HLSL_MACRO_APPLY


TRIPLANAR_NODES = {
    'Albedo': {'code': HLSL_ALBEDO, 'output': 'CMOT_FLOAT3',
               'scalars': ['TilingCm', 'BlendExponent', 'MirrorEnable', 'BandOffsetEnable', 'MacroCm',
                           'MacroAmount', 'MacroWarm', 'MidCm', 'MidAmount', 'PerInstanceJitter'],
               'textures': ['Albedo', 'MacroNoise'], 'perInstanceRandom': True},
    'ARM': {'code': HLSL_ARM, 'output': 'CMOT_FLOAT3',
            'scalars': ['TilingCm', 'BlendExponent', 'MirrorEnable', 'BandOffsetEnable', 'MidCm', 'MidRoughness'],
            'textures': ['ARM', 'MacroNoise'], 'perInstanceRandom': False},
    'Normal': {'code': HLSL_NORMAL, 'output': 'CMOT_FLOAT3',
               'scalars': ['TilingCm', 'BlendExponent', 'MirrorEnable', 'BandOffsetEnable', 'NormalStrength'],
               'textures': ['Normal'], 'perInstanceRandom': False},
}

SCALAR_DEFAULTS = {
    'TilingCm': 300.0, 'NormalStrength': 1.0, 'RoughnessScale': 1.0, 'Metallic': 0.0, 'AlbedoFlatness': 0.0,
    'BlendExponent': 4.0, 'MirrorEnable': 1.0, 'BandOffsetEnable': 1.0, 'MacroCm': 3733.0, 'MacroAmount': 0.13,
    'MacroWarm': 0.045, 'MidCm': 1187.0, 'MidAmount': 0.07, 'MidRoughness': 0.05, 'PerInstanceJitter': 0.06,
    'Roughness': 0.8, 'SlopeTintEnable': 0.0,
}


def _sampler_type(ue, name):
    """5.8 spells some MaterialSamplerType members with an underscore between words and some without."""
    for candidate in (name, name.replace('LINEAR_COLOR', 'LINEARCOLOR'), name.replace('LINEARCOLOR', 'LINEAR_COLOR')):
        if hasattr(ue.MaterialSamplerType, candidate):
            return getattr(ue.MaterialSamplerType, candidate)
    raise RuntimeError('No MaterialSamplerType %r; available: %s'
                       % (name, [n for n in dir(ue.MaterialSamplerType) if n.startswith('SAMPLERTYPE')]))


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


def load_measurement(spec):
    path = ROOT / spec['measurement']['manifest']
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    if manifest.get('status') != spec['measurement']['manifestStatusRequired']:
        raise RuntimeError('Measurement manifest status %r, need %r' % (manifest.get('status'), spec['measurement']['manifestStatusRequired']))
    return manifest


def scheme_problems(spec, manifest=None):
    """The receipt quotes the manifest's before/after numbers, so the shipped parameters must BE the
    measured parameters. Same idea as the Herodian pass's TilingCm cross-check."""
    problems = []
    try:
        manifest = manifest or load_measurement(spec)
    except Exception as exc:  # noqa: BLE001
        return ['measurement manifest: %r' % (exc,)]
    measured = manifest['scheme']['variants']
    for name, cfg in spec['variants'].items():
        key = cfg['schemeVariant']
        if key not in measured:
            problems.append('variant %s names an unmeasured scheme %r' % (name, key))
            continue
        want = measured[key]
        got = cfg['scalars']
        pairs = [('TilingCm', 'tilingCm'), ('MacroCm', 'MacroCm'), ('MacroAmount', 'MacroAmount'),
                 ('MacroWarm', 'MacroWarm'), ('MidCm', 'MidCm'), ('MidAmount', 'MidAmount'),
                 ('MirrorEnable', 'MirrorEnable')]
        if cfg['master'] == 'Triplanar':
            pairs += [('MidRoughness', 'MidRoughness'), ('PerInstanceJitter', 'PerInstanceJitter')]
        for spec_key, manifest_key in pairs:
            if spec_key not in got or manifest_key not in want:
                problems.append('variant %s missing %s/%s' % (name, spec_key, manifest_key))
            elif not close(float(got[spec_key]), float(want[manifest_key])):
                problems.append('variant %s %s %s != measured %s %s' % (name, spec_key, got[spec_key], manifest_key, want[manifest_key]))
        for numerator, denominator in (('MacroCm', 'TilingCm'), ('MidCm', 'TilingCm'), ('MacroCm', 'MidCm')):
            ratio = float(got[numerator]) / float(got[denominator])
            if abs(ratio - round(ratio)) < 0.1:
                problems.append('variant %s %s/%s = %.3f is too close to a whole number; a harmonic ratio does '
                                'not remove the grid, it builds a bigger one' % (name, numerator, denominator, ratio))
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


def active_rules(spec, priority):
    return [r for r in spec['reassign'] if int(r.get('priority', 1)) <= int(priority)]


def active_actor_rules(spec, priority):
    return [r for r in spec['actorMaterialProperties'] if int(r.get('priority', 1)) <= int(priority)]


def offline_check(spec=None):
    spec = spec or load_spec()
    problems = list(scheme_problems(spec))
    noise = ROOT / spec['noiseTexture']['source']
    if not noise.exists():
        problems.append('missing noise texture source %s (run Scripts/create_antirepeat_materials.py)' % spec['noiseTexture']['source'])
    for name, cfg in spec['variants'].items():
        replaced = disk(cfg['replaces'])
        if not replaced.exists():
            problems.append('variant %s replaces a missing asset %s' % (name, cfg['replaces']))
        elif sha(replaced) != cfg['replacesSha256']:
            problems.append('NOTE (not fatal): %s replaces %s whose hash has moved since the spec was written (%s now)'
                            % (name, cfg['replaces'], sha(replaced)[:16]))
        for kind, path in cfg['textures'].items():
            if not disk(path).exists():
                problems.append('variant %s texture %s missing: %s' % (name, kind, path))
        if cfg['replaces'] in spec['doNotTouch']['materials']:
            problems.append('variant %s replaces a doNotTouch material' % name)
        if cfg['master'] not in spec['masters']:
            problems.append('variant %s names an unknown master %r' % (name, cfg['master']))
    for rule in spec['reassign']:
        if rule['variant'] not in spec['variants']:
            problems.append('reassign rule points at unknown variant ' + rule['variant'])
        if rule['from'] != spec['variants'][rule['variant']]['replaces']:
            problems.append('reassign rule %r disagrees with variant %s replaces' % (rule['from'], rule['variant']))
    for asset in spec['protectedAssets']:
        if not disk(asset).exists():
            problems.append('missing protected asset ' + asset)
    for m in spec['protectedMaps']:
        if not disk(m, 'umap').exists():
            problems.append('missing protected map ' + m)
    for name, target in spec['targets'].items():
        if not (ROOT / target['mapFile']).exists():
            problems.append('missing target map file ' + target['mapFile'])
    manifest = None
    try:
        manifest = load_measurement(spec)
    except Exception:  # noqa: BLE001 - already reported above
        pass
    fatal = [p for p in problems if not p.startswith('NOTE')]
    summary = {}
    if manifest:
        for name, block in manifest.get('measurement', {}).items():
            if 'schemes' in block:
                summary[name] = {s: {'combEnergyFraction': row['combEnergyFraction'], 'acPeakU': row['acPeakU'],
                                     'acPeakV': row['acPeakV'], 'courseProfileVsBaseline': row['courseProfileVsBaseline'],
                                     'edgeEnergyVsBaseline': row['edgeEnergyVsBaseline']}
                                 for s, row in block['schemes'].items()}
    return {'status': 'offline_ok' if not fatal else 'offline_problems', 'problems': problems,
            'variants': {n: {'master': c['master'], 'new': c['newInstance'], 'replaces': c['replaces'],
                             'priority': c.get('priority', 1), 'scalars': c['scalars']} for n, c in spec['variants'].items()},
            'reassignRules': [{'from': r['from'], 'variant': r['variant'], 'priority': r.get('priority', 1)} for r in spec['reassign']],
            'measurement': summary,
            'protectedFiles': len(protected_paths(spec)),
            'targets': {n: {'map': t['map'], 'mapSha256Now': sha(ROOT / t['mapFile']) if (ROOT / t['mapFile']).exists() else None,
                            'expectedVariantSlotCount': t['expectedVariantSlotCount']} for n, t in spec['targets'].items()}}


# ------------------------------------------------------------------------------------------ native
class Native:
    def __init__(self, ue, spec, mode, stamp, target=None, allow_drift=False, priority=1, rebuild=False):
        self.u = ue
        self.spec = spec
        self.mode = mode
        self.stamp = stamp
        self.target = target
        self.allow_drift = allow_drift
        self.priority = int(priority)
        self.rebuild = rebuild
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
                       'instruction': spec['instruction'], 'priority': self.priority,
                       'specSha256': sha(SPEC_PATH), 'scriptSha256': sha(Path(__file__)),
                       'engineVersion': ue.SystemLibrary.get_engine_version(),
                       'commandLine': ue.SystemLibrary.get_command_line(),
                       'allowCountDrift': allow_drift, 'errors': [], 'stages': []}
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

    # -- guards ------------------------------------------------------------------------------
    def guard_project(self):
        u = self.u
        if Path(u.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project directory')
        if self.ed.get_game_world():
            raise RuntimeError('Game world active')
        dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()] + \
                [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
        if dirty:
            raise RuntimeError('Dirty packages before start: %s' % dirty)
        problems = scheme_problems(self.spec)
        if problems:
            raise RuntimeError('The shipped scheme does not match the measured scheme: %s' % problems)

    def guard_world(self):
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

    # -- readback ----------------------------------------------------------------------------
    def instance_values(self, inst, cfg):
        u, ml = self.u, self.ml
        row = {'path': asset_path(inst), 'class': inst.get_class().get_name(),
               'parent': asset_path(inst.get_editor_property('parent')),
               'scalars': {n: float(ml.get_material_instance_scalar_parameter_value(inst, n)) for n in sorted(cfg['scalars'])},
               'textures': {t: asset_path(ml.get_material_instance_texture_parameter_value(inst, t))
                            for t in sorted(list(cfg['textures']) + ['MacroNoise'])}}
        tint = ml.get_material_instance_vector_parameter_value(inst, 'Tint')
        row['tint'] = [float(tint.r), float(tint.g), float(tint.b), float(tint.a)]
        if 'slopeTint' in cfg:
            st = ml.get_material_instance_vector_parameter_value(inst, 'SlopeTint')
            row['slopeTint'] = [float(st.r), float(st.g), float(st.b), float(st.a)]
        row['usage'] = {}
        for name in USAGE_FLAGS:
            flag = getattr(u.MaterialUsage, name)
            row['usage'][name] = {'enabled': bool(ml.has_material_usage(inst, flag)),
                                  'explicitlyOverridden': bool(ml.has_material_usage_override(inst, flag))}
        row['explicitScalarOverrides'] = sorted(
            str(e.get_editor_property('parameter_info').get_editor_property('name'))
            for e in inst.get_editor_property('scalar_parameter_values'))
        return row

    def check_instance(self, row, name, cfg):
        want_parent = self.spec['masters'][cfg['master']]['asset']
        if row['parent'] != want_parent:
            raise RuntimeError('%s parent is %s, want %s' % (row['path'], row['parent'], want_parent))
        want_tex = dict(cfg['textures'])
        want_tex['MacroNoise'] = self.spec['noiseTexture']['asset']
        if row['textures'] != want_tex:
            raise RuntimeError('%s textures %s, want %s' % (row['path'], row['textures'], want_tex))
        if not close(row['scalars'], {k: float(v) for k, v in cfg['scalars'].items()}):
            raise RuntimeError('%s scalars read back %s' % (row['path'], row['scalars']))
        if not close(row['tint'], [float(x) for x in cfg['tint']]):
            raise RuntimeError('%s tint read back %s' % (row['path'], row['tint']))
        if 'slopeTint' in cfg and not close(row['slopeTint'], [float(x) for x in cfg['slopeTint']]):
            raise RuntimeError('%s slopeTint read back %s' % (row['path'], row['slopeTint']))
        if set(row['explicitScalarOverrides']) != set(cfg['scalars']):
            raise RuntimeError('%s must carry explicit overrides for exactly %s, has %s'
                               % (row['path'], sorted(cfg['scalars']), row['explicitScalarOverrides']))
        for flag, required in (('MATUSAGE_NANITE', self.spec['usage']['requireExplicitNaniteOverride']),
                               ('MATUSAGE_INSTANCED_STATIC_MESHES', self.spec['usage']['requireExplicitInstancedStaticMeshOverride'])):
            if required and row['usage'][flag] != {'enabled': True, 'explicitlyOverridden': True}:
                raise RuntimeError('%s %s read back %s (Nanite and the precinct-wall HISMs need both)'
                                   % (row['path'], flag, row['usage'][flag]))

    def parity_row(self, path):
        """Read the material this variant replaces, so the receipt shows the look is unchanged apart
        from the anti-repeat layer. Read only; the asset is in the protected set."""
        u, ml = self.u, self.ml
        obj = u.load_asset(path)
        row = {'path': path, 'class': obj.get_class().get_name(), 'uassetSha256': sha(disk(path))}
        if isinstance(obj, u.MaterialInstanceConstant):
            row['parent'] = asset_path(obj.get_editor_property('parent'))
            row['scalars'] = {}
            for entry in obj.get_editor_property('scalar_parameter_values'):
                row['scalars'][str(entry.get_editor_property('parameter_info').get_editor_property('name'))] = \
                    float(entry.get_editor_property('parameter_value'))
            row['textures'] = {}
            for entry in obj.get_editor_property('texture_parameter_values'):
                row['textures'][str(entry.get_editor_property('parameter_info').get_editor_property('name'))] = \
                    asset_path(entry.get_editor_property('parameter_value'))
            tint = ml.get_material_instance_vector_parameter_value(obj, 'Tint')
            row['tint'] = [float(tint.r), float(tint.g), float(tint.b), float(tint.a)]
        return row

    def check_parity(self, parity, name, cfg):
        """Every parameter the OLD material set explicitly must survive unchanged on the new one."""
        want = cfg.get('parityWith')
        if not want or 'scalars' not in parity:
            return {'checked': False, 'why': 'source is a Material, not an instance; hash frozen in the spec instead'}
        bad = {}
        for key, value in want.items():
            old = parity['scalars'].get(key, SCALAR_DEFAULTS.get(key))
            if not close(float(old), float(value)):
                bad[key] = {'old': old, 'new': value}
        if not close(parity.get('tint', [1.0, 1.0, 1.0, 1.0]), [float(x) for x in cfg['tint']]):
            bad['Tint'] = {'old': parity.get('tint'), 'new': cfg['tint']}
        old_tex = {k: v for k, v in parity.get('textures', {}).items() if k in cfg['textures']}
        if old_tex and old_tex != dict(cfg['textures']):
            bad['textures'] = {'old': old_tex, 'new': cfg['textures']}
        if bad:
            raise RuntimeError('%s would change the look, not only the repetition: %s' % (name, bad))
        return {'checked': True, 'parameters': sorted(want), 'textures': sorted(cfg['textures'])}


    # ------------------------------------------------------------------ disk-resolved readback
    def resolve_on_disk(self, owner, pointers):
        """Resolve every asset POINTER the built material carries against the file system.

        A previous defect in this project produced a green receipt whose five mesh pointers were all
        null, because the receipt only ever compared derived numbers with each other. So this does
        not trust the in-memory graph: each pointer must be non-null, its /Game path must resolve
        through the asset registry, the .uasset must exist on disk, and its sha256 is recorded. A
        null pointer or a missing file raises."""
        rows = {}
        for label, path in pointers.items():
            row = {'owner': owner, 'pointer': label, 'asset': path}
            if not path:
                row['status'] = 'NULL_POINTER'
                rows[label] = row
                raise RuntimeError('%s: pointer %r is null after reopen' % (owner, label))
            row['assetRegistryResolves'] = bool(self.assets.does_asset_exist(path))
            loaded = self.u.load_asset(path)
            row['loads'] = loaded is not None
            row['class'] = loaded.get_class().get_name() if loaded else None
            file_path = disk(path)
            row['diskPath'] = str(file_path.relative_to(ROOT))
            row['diskExists'] = file_path.exists()
            row['sha256'] = sha(file_path) if file_path.exists() else None
            row['status'] = 'OK' if (row['assetRegistryResolves'] and row['loads'] and row['diskExists']) else 'UNRESOLVED'
            rows[label] = row
            if row['status'] != 'OK':
                raise RuntimeError('%s: pointer %r -> %s did not resolve on disk: %s' % (owner, label, path, row))
        return rows

    # -- master construction -----------------------------------------------------------------
    def _custom(self, material, code, output, inputs):
        u, ml = self.u, self.ml
        node = ml.create_material_expression(material, u.MaterialExpressionCustom)
        node.set_editor_property('Code', code)
        node.set_editor_property('OutputType', getattr(u.CustomMaterialOutputType, output))
        pins = []
        for name in inputs:
            pin = u.CustomInput()
            pin.set_editor_property('InputName', name)
            pins.append(pin)
        node.set_editor_property('Inputs', pins)
        return node

    def _input_name(self, expression, wanted):
        """Resolve a pin against the LIVE pin list instead of guessing its name.

        MEASURED, 2026-09-09, this build: connect_material_expressions(custom, '', mask, 'Input')
        returns False - MaterialExpressionComponentMask's sole input is NOT called 'Input' through
        the 5.8 Python API, and the API returns False rather than raising, so the failure surfaces
        only if the caller checks. The same trap is on file elsewhere in this project (Python drops
        the b from bRail; PerInstanceCustomData wants const_default_value, not default_value). The
        rule that works, and the one Scripts/release_pbr_architecture.py uses to build M_PBR_Tiled:
        match the requested name case-insensitively against get_material_expression_input_names, and
        fall back to the only pin when the node has exactly one. Every resolution is recorded in the
        receipt under resolvedPinNames so the next person reads the real names instead of deriving
        them again. Treat a False return as a wrong name until proved otherwise."""
        names = [str(n) for n in self.ml.get_material_expression_input_names(expression)]
        for candidate in names:
            if candidate.lower() == wanted.lower():
                return candidate
        if len(names) == 1:
            return names[0]
        raise RuntimeError('%s has no input %r (inputs %s)'
                           % (expression.get_class().get_name(), wanted, names))

    def _wire(self, material, source, target, pin):
        resolved = self._input_name(target, pin)
        self.report.setdefault('resolvedPinNames', {}).setdefault(
            target.get_class().get_name(), {})[pin] = resolved
        if not self.ml.connect_material_expressions(source, '', target, resolved):
            raise RuntimeError('Wire %s -> %s.%s (resolved %r) failed; outputs=%s'
                               % (source.get_class().get_name(), target.get_class().get_name(), pin, resolved,
                                  [str(n) for n in self.ml.get_material_expression_output_names(source)]))

    def build_master(self, key, noise_texture, defaults):
        u, ml = self.u, self.ml
        cfg = self.spec['masters'][key]
        path = cfg['asset']
        folder, name = path.rsplit('/', 1)
        record = {'asset': path, 'kind': key}
        if self.assets.does_asset_exist(path):
            if not self.rebuild:
                raise RuntimeError('%s already exists; pass -AntiRepeatRebuild to rebuild its graph' % path)
            material = u.load_asset(path)
            if not isinstance(material, u.Material):
                raise RuntimeError('Existing asset at %s is not a Material' % path)
            ml.delete_all_material_expressions(material)
            record['rebuilt'] = True
        else:
            material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Material, u.MaterialFactoryNew())
            if not isinstance(material, u.Material):
                raise RuntimeError('Material factory failed for ' + path)
            record['rebuilt'] = False
        material.set_editor_property('tangent_space_normal', bool(cfg['tangentSpaceNormal']))

        scalars, textures = {}, {}
        for pname in cfg['scalarParameters']:
            node = ml.create_material_expression(material, u.MaterialExpressionScalarParameter, -1600, 200 * len(scalars))
            node.set_editor_property('parameter_name', pname)
            node.set_editor_property('default_value', float(defaults.get(pname, SCALAR_DEFAULTS.get(pname, 0.0))))
            scalars[pname] = node
        for pname, sampler in cfg['textureParameters'].items():
            node = ml.create_material_expression(material, u.MaterialExpressionTextureObjectParameter, -1900, 200 * len(textures))
            node.set_editor_property('parameter_name', pname)
            node.set_editor_property('sampler_type', _sampler_type(u, sampler))
            if pname == 'MacroNoise':
                node.set_editor_property('texture', noise_texture)
            else:
                default = self.default_texture_for(pname)
                if default:
                    node.set_editor_property('texture', default)
            textures[pname] = node
        vectors = {}
        for pname in cfg['vectorParameters']:
            node = ml.create_material_expression(material, u.MaterialExpressionVectorParameter, -1600, -400 - 200 * len(vectors))
            node.set_editor_property('parameter_name', pname)
            node.set_editor_property('default_value', u.LinearColor(1.0, 1.0, 1.0, 1.0) if pname == 'Tint'
                                     else u.LinearColor(0.58, 0.55, 0.48, 1.0))
            vectors[pname] = node

        world = ml.create_material_expression(material, u.MaterialExpressionWorldPosition, -2200, -200)
        vertex_normal = ml.create_material_expression(material, u.MaterialExpressionVertexNormalWS, -2200, 100)
        # PerInstanceRandom is 0.0 on every non-instanced component, which the HLSL reads as "not
        # instanced" and leaves alone; it does real work only on the precinct wall's HISM instances.
        # If the expression is not exposed in this build, fall back to a literal 0.0 and say so in
        # the receipt rather than silently shipping a different material.
        if hasattr(u, 'MaterialExpressionPerInstanceRandom'):
            per_instance = ml.create_material_expression(material, u.MaterialExpressionPerInstanceRandom, -2200, 300)
            record['perInstanceRandom'] = 'MaterialExpressionPerInstanceRandom'
        else:
            per_instance = ml.create_material_expression(material, u.MaterialExpressionConstant, -2200, 300)
            per_instance.set_editor_property('r', 0.0)
            record['perInstanceRandom'] = 'UNAVAILABLE_IN_THIS_BUILD_CONSTANT_ZERO'

        def feed(node, scalar_names, texture_names, want_random):
            self._wire(material, world, node, 'P')
            self._wire(material, vertex_normal, node, 'N')
            for pname in scalar_names:
                self._wire(material, scalars[pname], node, pname)
            for pname in texture_names:
                self._wire(material, textures[pname], node, pname)
            if want_random:
                self._wire(material, per_instance, node, 'PerInstanceRand')

        if key == 'Triplanar':
            outs = {}
            for node_name, node_cfg in TRIPLANAR_NODES.items():
                pins = ['P', 'N'] + node_cfg['scalars'] + node_cfg['textures'] + (['PerInstanceRand'] if node_cfg['perInstanceRandom'] else [])
                node = self._custom(material, node_cfg['code'], node_cfg['output'], pins)
                feed(node, node_cfg['scalars'], node_cfg['textures'], node_cfg['perInstanceRandom'])
                outs[node_name] = node
            flat = ml.create_material_expression(material, u.MaterialExpressionLinearInterpolate, -700, -600)
            flat.set_editor_property('const_b', 1.0)
            self._wire(material, outs['Albedo'], flat, 'A')
            self._wire(material, scalars['AlbedoFlatness'], flat, 'Alpha')
            base = ml.create_material_expression(material, u.MaterialExpressionMultiply, -500, -600)
            self._wire(material, flat, base, 'A')
            self._wire(material, vectors['Tint'], base, 'B')
            ao = ml.create_material_expression(material, u.MaterialExpressionComponentMask, -700, -100)
            ao.set_editor_property('r', True)
            self._wire(material, outs['ARM'], ao, 'Input')
            rough_raw = ml.create_material_expression(material, u.MaterialExpressionComponentMask, -700, 0)
            rough_raw.set_editor_property('g', True)
            self._wire(material, outs['ARM'], rough_raw, 'Input')
            rough = ml.create_material_expression(material, u.MaterialExpressionMultiply, -500, 0)
            self._wire(material, rough_raw, rough, 'A')
            self._wire(material, scalars['RoughnessScale'], rough, 'B')
            wiring = [(base, 'MP_BASE_COLOR'), (rough, 'MP_ROUGHNESS'), (scalars['Metallic'], 'MP_METALLIC'),
                      (outs['Normal'], 'MP_NORMAL'), (ao, 'MP_AMBIENT_OCCLUSION')]
        else:
            pins = ['P', 'N', 'TilingCm', 'MirrorEnable', 'BandOffsetEnable', 'MacroCm', 'MacroAmount',
                    'MacroWarm', 'MidCm', 'MidAmount', 'SlopeTintEnable', 'PerInstanceJitter',
                    'SlopeTint', 'Albedo', 'MacroNoise', 'PerInstanceRand']
            node = self._custom(material, HLSL_PLANAR, 'CMOT_FLOAT3', pins)
            feed(node, ['TilingCm', 'MirrorEnable', 'BandOffsetEnable', 'MacroCm', 'MacroAmount', 'MacroWarm',
                        'MidCm', 'MidAmount', 'SlopeTintEnable', 'PerInstanceJitter'],
                 ['Albedo', 'MacroNoise'], True)
            self._wire(material, vectors['SlopeTint'], node, 'SlopeTint')
            base = ml.create_material_expression(material, u.MaterialExpressionMultiply, -500, -600)
            self._wire(material, node, base, 'A')
            self._wire(material, vectors['Tint'], base, 'B')
            wiring = [(base, 'MP_BASE_COLOR'), (scalars['Roughness'], 'MP_ROUGHNESS'), (scalars['Metallic'], 'MP_METALLIC')]

        for node, prop_name in wiring:
            if not hasattr(u.MaterialProperty, prop_name):
                continue
            if not ml.connect_material_property(node, '', getattr(u.MaterialProperty, prop_name)):
                raise RuntimeError('connect_material_property %s failed on %s' % (prop_name, path))
        for flag in USAGE_FLAGS:
            ml.set_base_material_usage(material, getattr(u.MaterialUsage, flag), True)
        errors = [str(e) for e in ml.recompile_material(material)]
        record['compileErrors'] = errors
        if errors:
            raise RuntimeError('%s failed to compile: %s' % (path, errors))
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        record['scalarParameters'] = sorted(str(n) for n in ml.get_scalar_parameter_names(material))
        record['textureParameters'] = sorted(str(n) for n in ml.get_texture_parameter_names(material))
        record['vectorParameters'] = sorted(str(n) for n in ml.get_vector_parameter_names(material))
        missing = set(cfg['scalarParameters']) - set(record['scalarParameters'])
        missing |= set(cfg['textureParameters']) - set(record['textureParameters'])
        missing |= set(cfg['vectorParameters']) - set(record['vectorParameters'])
        if missing:
            raise RuntimeError('%s lacks parameters %s' % (path, sorted(missing)))
        record['inputsWired'] = {}
        for prop_name in ('MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_AMBIENT_OCCLUSION'):
            if hasattr(u.MaterialProperty, prop_name):
                wired = ml.get_material_property_input_node(material, getattr(u.MaterialProperty, prop_name))
                record['inputsWired'][prop_name] = wired.get_class().get_name() if wired else None
        record['usage'] = {f: bool(ml.has_material_usage(material, getattr(u.MaterialUsage, f))) for f in USAGE_FLAGS}
        record['tangentSpaceNormal'] = bool(material.get_editor_property('tangent_space_normal'))
        record['nodeCount'] = len(list(ml.get_material_expressions(material)))
        record['statistics'] = self.material_statistics(material)
        record['uassetSha256'] = sha(disk(path))
        return material, record

    def default_texture_for(self, parameter):
        for cfg in self.spec['variants'].values():
            if parameter in cfg['textures']:
                return self.u.load_asset(cfg['textures'][parameter])
        return None

    def material_statistics(self, material):
        """Compiled shader cost. get_statistics is not in every 5.x Python API and needs a shader map,
        so it is reported when available and recorded as unavailable when not - never invented."""
        ml = self.ml
        if not hasattr(ml, 'get_statistics'):
            return {'available': False, 'why': 'MaterialEditingLibrary.get_statistics is not exposed in this build'}
        try:
            stats = ml.get_statistics(material)
        except Exception as exc:  # noqa: BLE001
            return {'available': False, 'why': repr(exc)}
        out = {'available': True}
        for field in ('num_pixel_shader_instructions', 'num_vertex_shader_instructions', 'num_texture_samples',
                      'num_virtual_texture_lookups', 'num_dependent_texture_reads', 'num_interpolator_scalars',
                      'num_samplers'):
            try:
                out[field] = int(stats.get_editor_property(field))
            except Exception:  # noqa: BLE001
                pass
        numbers = [v for k, v in out.items() if k != 'available']
        if numbers and not any(numbers):
            # -nullrhi compiles no shader map, so every counter reads back 0. Zero is not a measurement
            # of a free material: say so rather than let a receipt imply a 0-instruction shader.
            out['available'] = False
            out['why'] = ('every counter read back 0: -nullrhi builds no shader map, so instruction and '
                          'sampler counts are not measurable in this process. The exact per-pixel texture '
                          'fetch count in shaderCost.textureFetchesPerPixel is counted from the graph and '
                          'is the honest cost figure here.')
        return out

    # -- instance construction ---------------------------------------------------------------
    def set_param(self, inst, kind, name, value):
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

    def build_instance(self, name, cfg, masters, noise_texture):
        u, ml = self.u, self.ml
        path = cfg['newInstance']
        folder, asset_name = path.rsplit('/', 1)
        parent = masters[cfg['master']]
        record = {'asset': path, 'master': asset_path(parent), 'replaces': cfg['replaces'], 'priority': cfg.get('priority', 1)}
        if self.assets.does_asset_exist(path):
            inst = u.load_asset(path)
            if not isinstance(inst, u.MaterialInstanceConstant):
                raise RuntimeError('Existing asset at %s is not a MaterialInstanceConstant' % path)
            record['reused'] = True
        else:
            inst = u.AssetToolsHelpers.get_asset_tools().create_asset(
                asset_name, folder, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
            if not isinstance(inst, u.MaterialInstanceConstant):
                raise RuntimeError('MaterialInstanceConstant factory failed for ' + path)
            record['reused'] = False
        if asset_path(inst.get_editor_property('parent')) != asset_path(parent):
            ml.set_material_instance_parent(inst, parent)
            if asset_path(inst.get_editor_property('parent')) != asset_path(parent):
                inst.set_editor_property('parent', parent)
                ml.update_material_instance(inst)
        if asset_path(inst.get_editor_property('parent')) != asset_path(parent):
            raise RuntimeError('Parent did not take on ' + path)
        for pname, texture in cfg['textures'].items():
            self.set_param(inst, 'texture', pname, u.load_asset(texture))
        self.set_param(inst, 'texture', 'MacroNoise', noise_texture)
        for pname, value in cfg['scalars'].items():
            self.set_param(inst, 'scalar', pname, value)
        self.set_param(inst, 'vector', 'Tint', cfg['tint'])
        if 'slopeTint' in cfg:
            self.set_param(inst, 'vector', 'SlopeTint', cfg['slopeTint'])
        for flag, required in (('MATUSAGE_NANITE', self.spec['usage']['requireExplicitNaniteOverride']),
                               ('MATUSAGE_INSTANCED_STATIC_MESHES', self.spec['usage']['requireExplicitInstancedStaticMeshOverride'])):
            if required:
                ml.set_material_usage_override(inst, getattr(u.MaterialUsage, flag), True, True)
        ml.update_material_instance(inst)
        if not self.assets.save_loaded_asset(inst, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        record['readback'] = self.instance_values(inst, cfg)
        self.check_instance(record['readback'], name, cfg)
        record['statistics'] = self.material_statistics(inst)
        record['uassetSha256'] = sha(disk(path))
        return inst, record

    def import_noise(self):
        u = self.u
        cfg = self.spec['noiseTexture']
        source = ROOT / cfg['source']
        path = cfg['asset']
        folder, name = path.rsplit('/', 1)
        record = {'asset': path, 'source': cfg['source'], 'sourceSha256': sha(source)}
        if self.assets.does_asset_exist(path):
            tex = u.load_asset(path)
            record['reused'] = True
        else:
            task = u.AssetImportTask()
            for key, value in dict(filename=str(source), destination_path=folder, destination_name=name,
                                   automated=True, replace_existing=False, save=False).items():
                task.set_editor_property(key, value)
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            objects = list(task.get_objects())
            if len(objects) != 1 or not isinstance(objects[0], u.Texture2D):
                raise RuntimeError('Noise import produced %s' % [type(o).__name__ for o in objects])
            tex = objects[0]
            record['reused'] = False
        tex.set_editor_property('compression_settings', getattr(u.TextureCompressionSettings, cfg['compression']))
        tex.set_editor_property('srgb', bool(cfg['srgb']))
        tex.set_editor_property('lod_group', getattr(u.TextureGroup, cfg['lodGroup']))
        if not self.assets.save_loaded_asset(tex, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + path)
        record['srgb'] = bool(tex.get_editor_property('srgb'))
        record['compression'] = str(tex.get_editor_property('compression_settings'))
        for getter in ('blueprint_get_size_x', 'get_size_x'):
            if hasattr(tex, getter):
                record['size'] = [int(getattr(tex, getter)()), int(getattr(tex, getter.replace('_x', '_y'))())]
                break
        if record.get('size') != [int(cfg['size']), int(cfg['size'])]:
            raise RuntimeError('Noise texture read back %s' % record.get('size'))
        if record['srgb'] is not False:
            raise RuntimeError('Noise texture must be linear, not sRGB')
        record['uassetSha256'] = sha(disk(path))
        return tex, record

    # ---------------------------------------------------------------------------------- BUILD
    def do_build(self):
        u = self.u
        spec = self.spec
        r = self.report
        self.guard_project()
        manifest = load_measurement(spec)
        r['measurement'] = {'path': spec['measurement']['manifest'], 'sha256': sha(ROOT / spec['measurement']['manifest']),
                            'generatorSha256': manifest.get('generatorSha256'),
                            'grid': manifest.get('measurementGrid'),
                            'schemes': {name: block.get('schemes') for name, block in manifest.get('measurement', {}).items()
                                        if 'schemes' in block}}
        r['technique'] = spec['technique']
        r['protectedBefore'] = self.protected()
        r['parityBefore'] = {n: self.parity_row(c['replaces']) for n, c in spec['variants'].items()}
        r['parityChecks'] = {n: self.check_parity(r['parityBefore'][n], n, c) for n, c in spec['variants'].items()}
        r['referenceMaster'] = {'asset': '/Game/MikdashV3/Materials/PBR/M_PBR_Tiled',
                                'statistics': self.material_statistics(u.load_asset('/Game/MikdashV3/Materials/PBR/M_PBR_Tiled'))}
        self.stage('discovered')
        noise, r['noiseTexture'] = self.import_noise()
        self.stage('noise_imported')
        defaults = dict(SCALAR_DEFAULTS)
        r['masters'] = {}
        masters = {}
        for key in spec['masters']:
            material, record = self.build_master(key, noise, defaults)
            masters[key] = material
            r['masters'][key] = record
            self.stage('master_saved_' + key)
        r['instances'] = {}
        for name, cfg in spec['variants'].items():
            _, record = self.build_instance(name, cfg, masters, noise)
            r['instances'][name] = record
            self.stage('instance_saved_' + name)
        dirty = self.dirty_content_names()
        if dirty:
            raise RuntimeError('Packages still dirty after saves: %s' % dirty)
        r['parityAfter'] = {n: self.parity_row(c['replaces']) for n, c in spec['variants'].items()}
        if r['parityAfter'] != r['parityBefore']:
            raise RuntimeError('A replaced material changed during the build')
        # Reopen every built asset from disk and read it back. Nothing below is derived from the
        # objects that were just written in memory: each is loaded fresh by path.
        r['reloaded'] = {}
        r['diskResolved'] = {}
        for key, cfg in spec['masters'].items():
            master = u.load_asset(cfg['asset'])
            if master is None or not isinstance(master, u.Material):
                raise RuntimeError('Master %s did not reload as a Material' % cfg['asset'])
            r['reloaded']['master:' + key] = {
                'path': asset_path(master), 'class': master.get_class().get_name(),
                'scalarParameters': sorted(str(n) for n in self.ml.get_scalar_parameter_names(master)),
                'textureParameters': sorted(str(n) for n in self.ml.get_texture_parameter_names(master)),
                'vectorParameters': sorted(str(n) for n in self.ml.get_vector_parameter_names(master)),
                'usage': {f: bool(self.ml.has_material_usage(master, getattr(u.MaterialUsage, f))) for f in USAGE_FLAGS},
                'tangentSpaceNormal': bool(master.get_editor_property('tangent_space_normal')),
                'expressionCount': len(list(self.ml.get_material_expressions(master)))}
            for field in ('scalarParameters', 'textureParameters', 'vectorParameters'):
                missing = set(cfg[field]) - set(r['reloaded']['master:' + key][field])
                if missing:
                    raise RuntimeError('%s lost %s after reopen: %s' % (cfg['asset'], field, sorted(missing)))
            if not all(r['reloaded']['master:' + key]['usage'].values()):
                raise RuntimeError('%s lost a usage flag after reopen: %s'
                                   % (cfg['asset'], r['reloaded']['master:' + key]['usage']))
            r['diskResolved']['master:' + key] = self.resolve_on_disk(cfg['asset'], {'self': cfg['asset']})
        for name, cfg in spec['variants'].items():
            inst = u.load_asset(cfg['newInstance'])
            if inst is None or not isinstance(inst, u.MaterialInstanceConstant):
                raise RuntimeError('Instance %s did not reload as a MaterialInstanceConstant' % cfg['newInstance'])
            row = self.instance_values(inst, cfg)
            self.check_instance(row, name, cfg)
            r['reloaded'][name] = row
            pointers = {'self': cfg['newInstance'], 'parent': row['parent']}
            for pname, path in row['textures'].items():
                pointers['texture:' + pname] = path
            r['diskResolved'][name] = self.resolve_on_disk(cfg['newInstance'], pointers)
            # The approved texture files must be the SAME BYTES the Herodian / paving passes wrote.
            for pname, path in row['textures'].items():
                if pname == 'MacroNoise':
                    continue
                if path != cfg['textures'][pname]:
                    raise RuntimeError('%s texture %s points at %s, not the approved %s'
                                       % (name, pname, path, cfg['textures'][pname]))
        r['diskResolvedSummary'] = {
            'pointersChecked': sum(len(v) for v in r['diskResolved'].values()),
            'nullPointers': 0, 'unresolved': 0,
            'why': 'Every pointer was resolved through the asset registry AND against the .uasset on '
                   'disk after save and reopen, and its sha256 recorded. A null or unresolved pointer '
                   'raises rather than being reported as a number that happens to agree with itself.'}
        r['repetitionNumbers'] = self.repetition_block(r)
        r['shaderCost'] = self.cost_summary(r)
        r['newAssetHashes'] = {spec['noiseTexture']['asset']: r['noiseTexture']['uassetSha256']}
        r['newAssetHashes'].update({m['asset']: m['uassetSha256'] for m in r['masters'].values()})
        r['newAssetHashes'].update({i['asset']: i['uassetSha256'] for i in r['instances'].values()})
        r['status'] = 'BUILT_SAVED_READBACK_APPLY_PENDING'
        return r


    def repetition_block(self, r):
        """The before/after repetition numbers, tied to the parameters actually read back from disk.

        These are computed by Scripts/create_antirepeat_materials.py on the approved texture PNG,
        applying the same UV warp and the same macro bands this material compiles. They are NOT a
        measurement of a rendered frame: PERFORMANCE-BUDGET.md and this machine's ~4-7 GB of free
        memory rule out a real-RHI capture here, and no such capture is claimed. What IS verified in
        the engine is that the parameters the shipped material carries are, field by field, the
        parameters the measurement used - which is checked against the manifest by scheme_problems()
        before the run starts and re-checked here from the disk readback."""
        manifest = load_measurement(self.spec)
        measured = manifest.get('measurement', {})
        scheme = manifest['scheme']['variants']
        out = {'source': 'offline model, Scripts/create_antirepeat_materials.py',
               'renderedFrameMeasurement': 'NOT ATTEMPTED. A real-RHI capture is what would measure '
                                           'the shipped pixels; this machine cannot run one (captures '
                                           'get killed). Nothing here claims a rendered result.',
               'metricNote': 'combEnergyFraction is the fraction of non-DC 2-D spectral power on the '
                             'harmonic comb of the tile period: 1.0 is wallpaper. acPeakU/acPeakV are '
                             'the normalized autocorrelation one tile across and one tile up. '
                             'courseProfileVsBaseline and edgeEnergyVsBaseline are QUALITY guards - '
                             'a scheme that lowers the comb by flattening those has destroyed the '
                             'masonry, which is exactly why stochastic bombing is not shipped.',
               'variants': {}}
        for name, cfg in self.spec['variants'].items():
            key = cfg['schemeVariant']
            built = r['reloaded'].get(name, {}).get('scalars', {})
            drift = {}
            for spec_key, manifest_key in (('TilingCm', 'tilingCm'), ('MacroCm', 'MacroCm'),
                                           ('MacroAmount', 'MacroAmount'), ('MacroWarm', 'MacroWarm'),
                                           ('MidCm', 'MidCm'), ('MidAmount', 'MidAmount'),
                                           ('MirrorEnable', 'MirrorEnable')):
                if spec_key in built and manifest_key in scheme.get(key, {}):
                    if not close(float(built[spec_key]), float(scheme[key][manifest_key])):
                        drift[spec_key] = {'builtOnDisk': built[spec_key], 'measured': scheme[key][manifest_key]}
            if drift:
                raise RuntimeError('%s: the material on disk does not carry the parameters the quoted '
                                   'measurement used: %s' % (name, drift))
            out['variants'][name] = {
                'schemeVariant': key,
                'parametersReadBackFromDisk': {k: built.get(k) for k in sorted(built)},
                'parametersMatchTheMeasurement': True,
                'schemes': measured.get(key, {}).get('schemes'),
                'regionCm': measured.get(key, {}).get('regionCm'),
                'previews': measured.get(key, {}).get('previews'),
                'note': measured.get(key, {}).get('skipped')}
        return out

    def cost_summary(self, r):
        """Texture fetches per pixel are counted from the graph and are exact. Instruction counts come
        from the compiled shader map when the engine exposes them, and say so when it does not."""
        out = {'textureFetchesPerPixel': {key: cfg['textureFetchesPerPixel'] for key, cfg in self.spec['masters'].items()},
               'referenceMaster': r['referenceMaster'],
               'masters': {key: rec.get('statistics') for key, rec in r['masters'].items()},
               'measuredFrameContext': {
                   'source': 'PERFORMANCE-BUDGET.md, perf-probe-20260908T115107Z',
                   'basepassMs': 0.28, 'naniteBasepassMs': 0.56, 'gpuMs': 17.0, 'gameThreadMs': 28.7,
                   'note': 'Base-pass shading is 0.84 ms of a 17.0 ms GPU frame and the frame is game-thread '
                           'bound at 28.7 ms. Shadow depth passes do not evaluate base colour, so this pass '
                           'adds nothing to the 1.15 ms ShadowDepths. No frame time is claimed here: this '
                           'machine cannot run a real-RHI capture.'}}
        base = r['referenceMaster'].get('statistics', {})
        for key, rec in r['masters'].items():
            stats = rec.get('statistics') or {}
            if stats.get('available') and base.get('available'):
                out.setdefault('deltaVsM_PBR_Tiled', {})[key] = {
                    field: stats.get(field, 0) - base.get(field, 0)
                    for field in ('num_pixel_shader_instructions', 'num_texture_samples', 'num_samplers')
                    if field in stats and field in base}
        return out

    # ---------------------------------------------------------------------------- ENUMERATION
    def enumerate_slots(self):
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
        mapping = {rule['from']: rule for rule in active_rules(spec, self.priority)}
        forbidden = set(spec['doNotTouch']['materials'])
        prefixes = tuple(spec['doNotTouch']['assetPathPrefixes'])
        plan, guarded = [], []
        for actor, component, slot, effective, overrides in rows:
            rule = mapping.get(effective)
            if not rule:
                continue
            if effective in forbidden or (effective or '').startswith(prefixes):
                raise RuntimeError('A reassign rule matched a doNotTouch material: ' + str(effective))
            if self.guarded_actor(actor):
                guarded.append({'actor': actor.get_path_name(), 'label': actor.get_actor_label(),
                                'folder': str(actor.get_folder_path()), 'component': component.get_path_name(),
                                'slot': slot, 'effectiveBefore': effective})
                continue
            plan.append({'actor': actor.get_path_name(), 'label': actor.get_actor_label(),
                         'folder': str(actor.get_folder_path()), 'component': component.get_path_name(),
                         'componentClass': component.get_class().get_name(), 'slot': slot,
                         'mesh': asset_path(component.get_editor_property('static_mesh')),
                         'variant': rule['variant'], 'rule': rule['from'], 'effectiveBefore': effective,
                         'overrideArrayBefore': list(overrides),
                         'newMaterial': spec['variants'][rule['variant']]['newInstance'], 'handle': component})
        return plan, guarded

    def enumerate_actor_properties(self):
        found = []
        for rule in active_actor_rules(self.spec, self.priority):
            prop = rule['property']
            wanted = set(rule['from'])
            for actor in self.actors.get_all_level_actors():
                try:
                    value = actor.get_editor_property(prop)
                except Exception:  # noqa: BLE001 - most actors do not expose it
                    continue
                current = asset_path(value)
                if current in wanted:
                    found.append({'actor': actor.get_path_name(), 'label': actor.get_actor_label(),
                                  'folder': str(actor.get_folder_path()), 'property': prop, 'before': current,
                                  'variant': rule['variant'],
                                  'newMaterial': self.spec['variants'][rule['variant']]['newInstance'], 'handle': actor})
        return found

    def check_counts(self, plan):
        spec = self.spec
        expected = spec['targets'][self.target]['expectedVariantSlotCount']
        counts = Counter(item['variant'] for item in plan)
        drift = {'found': dict(counts), 'foundPerRule': dict(Counter(item['rule'] for item in plan)),
                 'expected': expected, 'priority': self.priority}
        if expected is None:
            drift['note'] = 'No census recorded for %s. Run -AntiRepeatPlan first and put the numbers in the spec.' % self.target
            if spec['countPolicy']['refuseOnMismatch'] and not self.allow_drift:
                raise RuntimeError('Target %s has no expectedVariantSlotCount. Run -AntiRepeatPlan %s, record the '
                                   'census in the spec, or pass %s. Found: %s'
                                   % (self.target, spec['targets'][self.target]['flag'],
                                      spec['countPolicy']['allowSwitch'], dict(counts)))
            return drift
        wanted = {v: n for v, n in expected.items() if int(spec['variants'][v].get('priority', 1)) <= self.priority}
        mismatch = {v: (wanted.get(v), counts.get(v, 0)) for v in set(wanted) | set(counts)
                    if int(wanted.get(v, 0)) != int(counts.get(v, 0))}
        drift['mismatch'] = mismatch
        if mismatch and spec['countPolicy']['refuseOnMismatch'] and not self.allow_drift:
            raise RuntimeError('Slot counts differ from the census %s; inspect the scene, or pass %s'
                               % (mismatch, spec['countPolicy']['allowSwitch']))
        return drift

    def scene_snapshot(self):
        rows = {}
        for a in self.actors.get_all_level_actors():
            loc, rot, sc = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
            rows[a.get_name()] = (a.get_actor_label(), round(loc.x, 3), round(loc.y, 3), round(loc.z, 3),
                                  round(rot.pitch, 3), round(rot.yaw, 3), round(rot.roll, 3),
                                  round(sc.x, 4), round(sc.y, 4), round(sc.z, 4),
                                  len(a.get_components_by_class(self.u.StaticMeshComponent)))
        return rows

    def components_by_path(self):
        out = {}
        for actor in self.actors.get_all_level_actors():
            for component in actor.get_components_by_class(self.u.StaticMeshComponent):
                out[component.get_path_name()] = component
        return out

    def actors_by_path(self):
        return {a.get_path_name(): a for a in self.actors.get_all_level_actors()}

    def save_map(self):
        dirty = self.dirty_content_names()
        if dirty:
            raise RuntimeError('Dirty content packages before map save: %s' % dirty)
        if not self.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        if self.u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
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

    # ---------------------------------------------------------------------------- PLAN (read only)
    def do_plan(self):
        r = self.report
        self.guard_project()
        r['protectedBefore'] = self.protected()
        r['mapSha256Before'] = sha(self.map_file)
        self.guard_world()
        rows, counts = self.enumerate_slots()
        r['materialCounts'] = dict(counts)
        r['staticMeshSlots'] = len(rows)
        plan, guarded = self.build_plan(rows)
        r['wouldTouchSlots'] = len(plan)
        r['wouldTouchComponents'] = len({item['component'] for item in plan})
        r['countsByVariant'] = dict(Counter(item['variant'] for item in plan))
        r['countsByRule'] = dict(Counter(item['rule'] for item in plan))
        r['countsByFolder'] = dict(Counter(item['folder'] for item in plan))
        r['instancedComponents'] = dict(Counter(item['componentClass'] for item in plan))
        r['kotelGuardSkipped'] = guarded
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
    def do_apply(self, build_receipt):
        u = self.u
        spec = self.spec
        r = self.report
        prior = json.loads(Path(build_receipt).read_text(encoding='utf-8-sig'))
        r['buildReceipt'] = {'path': str(build_receipt), 'sha256': sha(build_receipt), 'status': prior.get('status')}
        if prior.get('status') != 'BUILT_SAVED_READBACK_APPLY_PENDING':
            raise RuntimeError('Build receipt status %r does not authorize apply' % prior.get('status'))
        for asset, digest in prior['newAssetHashes'].items():
            if not disk(asset).exists() or sha(disk(asset)) != digest:
                raise RuntimeError('Built asset changed or missing since the build receipt: ' + asset)
        r['measurement'] = prior.get('measurement')
        r['shaderCost'] = prior.get('shaderCost')
        r['technique'] = prior.get('technique')
        r['parityChecks'] = prior.get('parityChecks')
        r['targetRole'] = spec['targets'][self.target]['role']
        r['applyOrderNote'] = spec['applyOrder']['note']
        self.guard_project()
        r['protectedBefore'] = self.protected()
        r['mapSha256Before'] = sha(self.map_file)
        instances = {}
        for name, cfg in spec['variants'].items():
            inst = u.load_asset(cfg['newInstance'])
            self.check_instance(self.instance_values(inst, cfg), name, cfg)
            instances[name] = inst
        self.guard_world()
        rows, counts_before = self.enumerate_slots()
        r['materialCountsBefore'] = dict(counts_before)
        plan, guarded = self.build_plan(rows)
        r['kotelGuardSkipped'] = guarded
        r['slotCounts'] = self.check_counts(plan)
        r['plannedSlots'] = len(plan)
        r['componentsTouched'] = len({item['component'] for item in plan})
        r['plan'] = [{k: v for k, v in item.items() if k != 'handle'} for item in plan]
        actor_rows = self.enumerate_actor_properties()
        r['actorPropertyPlan'] = [{k: v for k, v in item.items() if k != 'handle'} for item in actor_rows]
        self.stage('planned', planned=len(plan), actorProperties=len(actor_rows))

        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + self.target + '-' + self.stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(self.map_file, checkpoint / self.map_file.name)
        if sha(checkpoint / self.map_file.name) != r['mapSha256Before']:
            raise RuntimeError('Map checkpoint hash differs')
        (checkpoint / 'protected.json').write_text(json.dumps(r['protectedBefore'], indent=2), encoding='utf-8')
        r['checkpoint'] = str(checkpoint)
        self.stage('checkpointed')

        before_scene = self.scene_snapshot()
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
                               % {k: (counts_after.get(k), expected_after.get(k))
                                  for k in set(counts_after) | set(expected_after) if counts_after.get(k) != expected_after.get(k)})
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
        r['reopened'] = {'badSlots': bad[:20], 'badSlotCount': len(bad), 'badActorProperties': bad_actors[:20],
                         'badActorPropertyCount': len(bad_actors), 'materialCounts': dict(counts_reopened),
                         'sceneUnchanged': self.scene_snapshot() == before_scene}
        if bad or bad_actors or counts_reopened != counts_after or not r['reopened']['sceneUnchanged']:
            raise RuntimeError('Reopened readback mismatch: %d bad slots, %d bad actor properties, census equal %s'
                               % (len(bad), len(bad_actors), counts_reopened == counts_after))
        r['revertCommand'] = ('-AntiRepeatRevert="%s" %s' % (self.receipt_path, spec['targets'][self.target]['flag']))
        r['status'] = 'APPLIED_SAVED_REOPENED_VISUAL_REVIEW_PENDING'
        return r

    # ---------------------------------------------------------------------------------- VERIFY
    def do_verify(self, apply_receipt):
        spec = self.spec
        r = self.report
        prior = json.loads(Path(apply_receipt).read_text(encoding='utf-8-sig'))
        r['applyReceipt'] = {'path': str(apply_receipt), 'sha256': sha(apply_receipt),
                             'status': prior.get('status'), 'target': prior.get('target')}
        r['mapSha256Now'] = sha(self.map_file)
        r['mapMatchesApplyAfter'] = r['mapSha256Now'] == prior.get('mapSha256AfterSave')
        r['protectedNow'] = self.protected()
        r['protectedUnchangedSinceApply'] = r['protectedNow'] == prior.get('protectedBefore')
        self.guard_project()
        for name, cfg in spec['variants'].items():
            self.check_instance(self.instance_values(self.u.load_asset(cfg['newInstance']), cfg), name, cfg)
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
        r['applyReceipt'] = {'path': str(apply_receipt), 'sha256': sha(apply_receipt),
                             'status': prior.get('status'), 'target': prior.get('target')}
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
            before_scene = self.scene_snapshot()
            _, counts_before_revert = self.enumerate_slots()
            r['materialCountsBeforeRevert'] = dict(counts_before_revert)
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
                # Restore ONLY the slots this pass wrote, each to whatever its override entry was
                # before - an asset, or None. The override array is deliberately NOT written back
                # wholesale: other passes save these maps between an apply and its revert, and
                # replacing the whole array would silently undo any entry they added to a component
                # this pass happens to share. The current array is read, padded, and only the
                # recorded slot indices are touched.
                current = list(component.get_editor_property('override_materials'))
                while len(current) < component.get_num_materials():
                    current.append(None)
                before_array = items[0]['overrideArrayBefore']
                for item in items:
                    slot = item['slot']
                    was = before_array[slot] if slot < len(before_array) else None
                    current[slot] = u.load_asset(was) if was else None
                component.set_editor_property('override_materials', current)
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
            # Did anything move that this pass did not write? Compare the scene snapshot and the
            # material census taken moments ago, inside this same process, against the state after
            # the restore. Only the four counts this pass moved may differ; every other material,
            # actor transform and component count must be identical. This does NOT claim other
            # passes left the map alone since the apply - they did change it, legitimately - it
            # claims this revert touched nothing but its own slots.
            after_scene = self.scene_snapshot()
            _, counts_after_revert = self.enumerate_slots()
            r['materialCountsAfterRevert'] = dict(counts_after_revert)
            r['sceneUnchangedDuringRevert'] = after_scene == before_scene
            if not r['sceneUnchangedDuringRevert']:
                moved = sorted(k for k in set(before_scene) | set(after_scene)
                               if before_scene.get(k) != after_scene.get(k))
                r['sceneActorsMovedDuringRevert'] = moved[:40]
                raise RuntimeError('Revert disturbed %d actors beyond its own slots: %s' % (len(moved), moved[:10]))
            delta = {k: [counts_before_revert.get(k, 0), counts_after_revert.get(k, 0)]
                     for k in set(counts_before_revert) | set(counts_after_revert)
                     if counts_before_revert.get(k, 0) != counts_after_revert.get(k, 0)}
            r['materialCountDeltaDuringRevert'] = delta
            expected_moved = {self.spec['variants'][v]['newInstance'] for v in self.spec['variants']}
            expected_moved |= {self.spec['variants'][v]['replaces'] for v in self.spec['variants']}
            unexpected = sorted(set(delta) - expected_moved)
            r['unexpectedMaterialsMovedDuringRevert'] = unexpected
            if unexpected:
                raise RuntimeError('Revert changed material counts it does not own: %s' % unexpected)
            self.save_map()
            self.stage('map_saved')
            if not self.levels.load_level(self.map_asset):
                raise RuntimeError('Reopen failed')
        bad = self.readback_plan(prior['plan'], expect_new=False)
        bad_actors = self.readback_actor_properties(prior.get('actorPropertyPlan', []), expect_new=False)
        _, counts = self.enumerate_slots()
        r['mapSha256After'] = sha(self.map_file)
        r['reopened'] = {'badSlots': bad[:20], 'badSlotCount': len(bad), 'badActorProperties': bad_actors[:20],
                         'badActorPropertyCount': len(bad_actors), 'materialCounts': dict(counts),
                         'censusMatchesApplyBefore': dict(counts) == prior.get('materialCountsBefore')}
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
    plan_m = re.search(r'-AntiRepeatPlan(?=\s|$)', cmd)
    build_m = re.search(r'-AntiRepeatBuild(?=\s|$)', cmd)
    apply_m = re.search(r'-AntiRepeatApply=(?:"([^"]+)"|([^\s]+))', cmd)
    verify_m = re.search(r'-AntiRepeatVerify=(?:"([^"]+)"|([^\s]+))', cmd)
    revert_m = re.search(r'-AntiRepeatRevert=(?:"([^"]+)"|([^\s]+))', cmd)
    priority_m = re.search(r'-AntiRepeatPriority=(\d+)', cmd)
    lower = cmd.lower()
    allow_drift = '-antirepeatallowcountdrift' in lower
    rebuild = '-antirepeatrebuild' in lower
    priority = int(priority_m.group(1)) if priority_m else 1
    modes = [m for m, hit in (('plan', plan_m), ('build', build_m), ('apply', apply_m),
                              ('verify', verify_m), ('revert', revert_m)) if hit]
    if len(modes) != 1:
        raise RuntimeError('Pass exactly one of -AntiRepeatPlan, -AntiRepeatBuild, -AntiRepeatApply=<receipt>, '
                           '-AntiRepeatVerify=<receipt>, -AntiRepeatRevert=<receipt>')
    mode = modes[0]
    arg, receipt = None, None
    if mode in ('apply', 'verify', 'revert'):
        m = {'apply': apply_m, 'verify': verify_m, 'revert': revert_m}[mode]
        arg = Path(m.group(1) or m.group(2))
        if not arg.exists():
            raise RuntimeError('Receipt not found: %s' % arg)
        receipt = json.loads(arg.read_text(encoding='utf-8-sig'))
        if mode in ('verify', 'revert'):
            priority = int(receipt.get('priority', priority))
    target = None
    if mode != 'build':
        target = _target_from_command_line(spec, cmd, receipt if mode in ('verify', 'revert') else None)
    native = Native(ue, spec, mode, stamp, target, allow_drift, priority, rebuild)
    protected_before = native.protected()
    try:
        if mode == 'plan':
            native.do_plan()
        elif mode == 'build':
            native.do_build()
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
        ue.log('ANTIREPEAT_%s %s status=%s' % (mode.upper(), native.receipt_path, native.report['status']))


if __name__ == '__main__':
    try:
        import unreal  # noqa: F401
        _native_main()
    except ImportError:
        print(json.dumps(offline_check(), indent=2, default=str))

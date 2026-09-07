"""Guarded lighting polish of the combined IntegratedReviewV2 map.

Moves /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough from the flat 20,000 lux
noon sun with a fixed EV 12 camera toward a low warm sun, bounded histogram auto
exposure, filmic tonemapping, height/volumetric fog, cloud shadows, a soft Heikhal
entrance fill and higher Lumen quality on the gold. Every number comes from
Scripts/release_lighting_polish.spec.json; the design reasoning lives in
SourceAssets/lighting-review/design-notes.md.

Commandlet invocation (serial, never while another native job or the GUI editor
holds the map):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_lighting_polish.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Lighting-Polish-01.log"

Optional switches (read from the engine command line):
  -LightingSun=morning|afternoon|<azimuth>,<elevation>   sun preset (default morning: az 110, el 30).
  -UseHdri            import SourceAssets/lighting-review/kiara_4_mid-morning_2k.hdr as a TextureCube
                      (namespace /Game/MikdashV3/IntegratedReviewV2/Lighting) and switch the SkyLight to
                      SLS_SpecifiedCubemap. Default off: SkyAtmosphere drives the look.
  -LightingNoFill     do not create the RELEASE_HeikhalEntranceFill rect light.
  -LightingNoFog      do not create the RELEASE_HeightFog actor.
  -LightingNoClouds   do not duplicate MI_Cloud / lower the cloud coverage.
  -LightingDryRun     guards, actor discovery and before-value readback only; no mutation, no
                      checkpoint, receipt status dry_run_no_mutation_map_unchanged.
  -LightingRevert[=<receipt.json>]
                      restore every before-value recorded by an earlier apply receipt (latest saved
                      native-apply-*.json by default), destroy the created actors, save, reopen, read
                      back and write native-revert-<stamp>.json.

Offline (no engine):  python release_lighting_polish.py [--sun morning] [--use-hdri]
                      prints the spec consistency check (sun vectors, exposure conversions, fill light
                      inside the Heikhal, HDRI hash against its provenance).

Safety model (release_place_assets.py pattern):
  * Refuses to run with the wrong project directory, a game world, dirty packages, a loaded world that
    is not the combined map, unexpected counts of lighting actors, an existing ExponentialHeightFog, or
    actors already carrying the ReleaseLightingPolishV1 tag (revert first).
  * Copies Walkthrough.umap (and any One-File-Per-Actor folders) to ReviewCheckpoints/Lighting-<stamp>/
    before any mutation and verifies the copy.
  * Every property change is recorded as {target, actor, component, property, before, after} with typed,
    revertible before-values; unavailable properties are recorded and skipped unless the spec marks them
    required. Unrelated actors are snapshotted and must be numerically unchanged before save and after
    reopen.
  * Saves, reopens the map and reads every changed property back numerically. The receipt is written at
    start, after each stage and in finally, preserving partial state on failure. Protected maps and the
    donor cloud material are hashed before and after.
"""
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_lighting_polish.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'

APPLIED_STATUS = 'lighting_polish_saved_reopened_visual_acceptance_pending'
REVERTED_STATUS = 'lighting_reverted_saved_reopened'


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so offline_check() can run anywhere.
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


def sun_direction(azimuth_deg, elevation_deg):
    """Unit light-travel direction in UE axes (+X east, +Y south, +Z up)."""
    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    return [-math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), -math.sin(el)]


def sun_rotator(azimuth_deg, elevation_deg):
    """(pitch, yaw, roll) whose forward vector is sun_direction()."""
    d = sun_direction(azimuth_deg, elevation_deg)
    return [-float(elevation_deg), math.degrees(math.atan2(d[1], d[0])), 0.0]


def rotator_forward(pitch_deg, yaw_deg):
    p = math.radians(pitch_deg)
    y = math.radians(yaw_deg)
    return [math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def resolve_sun(spec, token=None):
    """Sun preset name or 'az,el' -> dict with azimuth, elevation, rotator, direction."""
    presets = spec['sun']['presets']
    token = (token or spec['sun']['default']).strip().strip('"')
    if token.lower() in presets:
        preset = presets[token.lower()]
        record = {'preset': token.lower(), 'azimuthDeg': float(preset['azimuthDeg']), 'elevationDeg': float(preset['elevationDeg']), 'why': preset.get('why')}
    else:
        parts = token.split(',')
        if len(parts) != 2:
            raise RuntimeError('Sun must be a preset (%s) or <azimuth>,<elevation>: %r' % (sorted(presets), token))
        record = {'preset': 'custom', 'azimuthDeg': float(parts[0]), 'elevationDeg': float(parts[1]), 'why': 'explicit -LightingSun value'}
    if not 0.0 <= record['azimuthDeg'] < 360.0 or not 0.0 < record['elevationDeg'] <= 90.0:
        raise RuntimeError('Sun azimuth must be in [0, 360) and elevation in (0, 90]: %r' % record)
    record['rotatorPitchYawRoll'] = sun_rotator(record['azimuthDeg'], record['elevationDeg'])
    record['directionUE'] = sun_direction(record['azimuthDeg'], record['elevationDeg'])
    forward = rotator_forward(record['rotatorPitchYawRoll'][0], record['rotatorPitchYawRoll'][1])
    record['rotatorForwardDot'] = dot(forward, record['directionUE'])
    return record


def luminance_max(extended_range, lens_attenuation=0.78):
    """PostProcessEyeAdaptation.cpp LuminanceMaxFromLensAttenuation()."""
    if not extended_range:
        return 1.0
    return 0.78 / max(float(lens_attenuation), 0.01)


def ev100_to_brightness_field(ev100, extended_range, lens_attenuation=0.78):
    """Value to write into AutoExposureMin/MaxBrightness for a wanted EV100.

    Extended luminance range on: the field IS EV100. Off: the field is raw scene
    luminance and the engine's own conversion (LuminanceMax * 2^EV, LuminanceMax
    1.0 when the range is not extended) is applied here instead.
    """
    if extended_range:
        return float(ev100)
    return luminance_max(False, lens_attenuation) * math.pow(2.0, float(ev100))


def point_in_box(point, box, margin=0.0):
    return all(box['min'][i] + margin <= point[i] <= box['max'][i] - margin for i in range(3))


def hdri_check(spec, require=False):
    cfg = spec['hdri']
    file_path = ROOT / cfg['file']
    provenance_path = ROOT / cfg['provenance']
    report = {'file': str(file_path), 'exists': file_path.exists(), 'provenance': str(provenance_path), 'provenanceExists': provenance_path.exists()}
    if not (file_path.exists() and provenance_path.exists()):
        if require:
            raise RuntimeError('HDRI or provenance missing: %s' % report)
        return report
    provenance = json.loads(provenance_path.read_text(encoding='utf-8-sig'))
    report['bytes'] = file_path.stat().st_size
    report['sha256'] = sha256_of(file_path)
    report['license'] = provenance.get('license')
    report['sha256MatchesProvenance'] = report['sha256'] == provenance.get('sha256')
    report['bytesMatchProvenance'] = report['bytes'] == provenance.get('bytes')
    if require and not (report['sha256MatchesProvenance'] and report['bytesMatchProvenance']):
        raise RuntimeError('HDRI on disk differs from its provenance record: %s' % report)
    return report


def offline_check(spec=None, sun=None, use_hdri=False):
    """Consistency checks that need no engine. Raises on the first failure."""
    spec = spec or load_spec()
    report = {}
    presets = {}
    for name in spec['sun']['presets']:
        record = resolve_sun(spec, name)
        if record['rotatorForwardDot'] < spec['verification']['directionDotMinimum']:
            raise RuntimeError('Sun preset %s: rotator forward does not reproduce the direction' % name)
        if abs(dot(record['directionUE'], record['directionUE']) - 1.0) > 1e-9:
            raise RuntimeError('Sun preset %s direction is not unit length' % name)
        if record['directionUE'][2] >= 0.0:
            raise RuntimeError('Sun preset %s does not shine downward' % name)
        presets[name] = record
    report['sunPresets'] = presets
    report['sunSelected'] = resolve_sun(spec, sun)

    exposure = spec['postProcess']['exposure']
    if not exposure['minEV100'] < exposure['maxEV100']:
        raise RuntimeError('minEV100 must be below maxEV100')
    report['exposureFieldValues'] = {
        'extendedRange': {'min': ev100_to_brightness_field(exposure['minEV100'], True), 'max': ev100_to_brightness_field(exposure['maxEV100'], True)},
        'rawLuminance': {'min': ev100_to_brightness_field(exposure['minEV100'], False), 'max': ev100_to_brightness_field(exposure['maxEV100'], False)},
    }
    for key in ('auto_exposure_min_brightness', 'auto_exposure_max_brightness'):
        raw = spec['postProcess']['settings']['properties'][key]
        if not (isinstance(raw, dict) and '$ev100' in raw):
            raise RuntimeError('%s must be an $ev100 entry so the run-time unit rule applies' % key)

    fill = spec['fill']
    box = fill['heikhalInteriorBoundsCm']
    if not point_in_box(fill['location'], box, margin=50.0):
        raise RuntimeError('Fill light %r is not inside the Heikhal interior with 50 cm margin' % (fill['location'],))
    if fill['location'][0] - box['max'][0] > 0 or box['max'][0] - fill['location'][0] > 400.0:
        raise RuntimeError('Fill light must sit within 4 m of the doorway plane')
    forward = rotator_forward(fill['rotation']['pitch'], fill['rotation']['yaw'])
    if forward[0] >= 0.0 or forward[2] >= 0.0:
        raise RuntimeError('Fill light must aim west (-X) and downward; forward %r' % (forward,))
    report['fillForward'] = forward

    fog = spec['fog']['component']['properties']
    if not 0.0 < fog['fog_density'] <= 0.02 or not 0.0 < fog['fog_height_falloff'] <= 2.0:
        raise RuntimeError('Fog density/falloff outside the reviewed range')
    if fog['volumetric_fog_distance'] < fog['start_distance']:
        raise RuntimeError('Volumetric fog distance below the fog start distance')

    clouds = spec['clouds']
    if not 0.0 <= clouds['coverage'] <= 1.0:
        raise RuntimeError('Cloud coverage must be 0..1')
    if clouds['expectedSourceMaterial'] not in spec['protectedAssets']:
        raise RuntimeError('The donor cloud material must be listed as protected')
    if not clouds['scatteredMaterial'].startswith(spec['assetNamespace'] + '/'):
        raise RuntimeError('Scattered cloud material must live in the lighting namespace')

    for block_name, block in (('sun', spec['sun']['component']), ('skyLight', spec['skyLight']['component']), ('skyAtmosphere', spec['skyAtmosphere']['component']),
                              ('fog', spec['fog']['component']), ('fill', spec['fill']['component']), ('postProcess', spec['postProcess']['settings']),
                              ('hdri', spec['hdri']['skyLightProperties'])):
        missing = [p for p in block['required'] if p not in block['properties']]
        if missing:
            raise RuntimeError('%s: required properties missing from the block: %s' % (block_name, missing))
        for prop, raw in block['properties'].items():
            if isinstance(raw, dict):
                keys = set(raw)
                if not keys & {'$enum', '$linearColor', '$color', '$asset', '$ev100', '$importedHdri'}:
                    raise RuntimeError('%s.%s: unknown value encoding %s' % (block_name, prop, sorted(keys)))
    report['hdri'] = hdri_check(spec, require=use_hdri)
    if not (ROOT / spec['targetMapFile']).exists():
        raise RuntimeError('Target map file missing on disk')
    report['targetMapSha256'] = sha256_of(ROOT / spec['targetMapFile'])
    report['targetMapMatchesLastKnown'] = report['targetMapSha256'] == spec['lastKnownMapSha256']
    report['status'] = 'offline_spec_consistent'
    return report


def latest_apply_receipt(spec):
    folder = ROOT / spec['receiptFolder']
    candidates = sorted(folder.glob(spec['receiptPrefix'] + '*.json'))
    for path in reversed(candidates):
        receipt = json.loads(path.read_text(encoding='utf-8-sig'))
        if receipt.get('mapSaved') and receipt.get('status') == APPLIED_STATUS and not receipt.get('revertedBy'):
            return path, receipt
    raise RuntimeError('No saved, unreverted apply receipt found in ' + str(folder))


# --------------------------------------------------------------------------
# Typed value encoding (revertible before-values)
# --------------------------------------------------------------------------

_ENUM_REPR = re.compile(r'<(\w+)\.(\w+): (-?\d+)>')


def encode_value(ue, value):
    """Engine value -> JSON record that decode_value() can turn back into a value."""
    if value is None:
        return {'type': 'none'}
    if isinstance(value, ue.EnumBase):
        # UE 5.8 EnumBase does not support int(value); restore by verified member name.
        name = getattr(value, 'name', None)
        match = _ENUM_REPR.match(repr(value))
        if not isinstance(name, str) and match:
            name = match.group(2)
        if not isinstance(name, str) or getattr(type(value), name, None) != value:
            raise ValueError('Cannot identify a reversible enum member: ' + repr(value))
        return {'type': 'enum', 'class': type(value).__name__, 'name': name,
                'int': int(match.group(3)) if match else None}
    if isinstance(value, bool):
        return {'type': 'bool', 'value': value}
    if isinstance(value, int):
        return {'type': 'int', 'value': int(value)}
    if isinstance(value, float):
        return {'type': 'float', 'value': float(value)}
    if isinstance(value, str):
        return {'type': 'str', 'value': value}
    if isinstance(value, ue.Name):
        return {'type': 'Name', 'value': str(value)}
    if isinstance(value, ue.Rotator):
        return {'type': 'Rotator', 'value': [float(value.pitch), float(value.yaw), float(value.roll)]}
    if isinstance(value, ue.Vector):
        return {'type': 'Vector', 'value': [float(value.x), float(value.y), float(value.z)]}
    if isinstance(value, ue.LinearColor):
        return {'type': 'LinearColor', 'value': [float(value.r), float(value.g), float(value.b), float(value.a)]}
    if isinstance(value, ue.Color):
        return {'type': 'Color', 'value': [int(value.r), int(value.g), int(value.b), int(value.a)]}
    if isinstance(value, ue.Object):
        return {'type': 'object', 'path': value.get_path_name(), 'class': value.get_class().get_name()}
    return {'type': 'repr', 'value': str(value), 'class': type(value).__name__}


def decode_value(ue, record):
    kind = record['type']
    if kind == 'none':
        return None
    if kind in ('bool', 'int', 'float', 'str'):
        return record['value']
    if kind == 'Name':
        return ue.Name(record['value'])
    if kind == 'Rotator':
        v = record['value']
        return ue.Rotator(pitch=v[0], yaw=v[1], roll=v[2])
    if kind == 'Vector':
        return ue.Vector(*record['value'])
    if kind == 'LinearColor':
        return ue.LinearColor(*record['value'])
    if kind == 'Color':
        return ue.Color(*record['value'])
    if kind == 'enum':
        enum_class = getattr(ue, record['class'])
        if hasattr(enum_class, record['name']):
            return getattr(enum_class, record['name'])
        return enum_class.cast(record['int'])
    if kind == 'object':
        path = record['path']
        obj = ue.load_asset(path) if '.' in path else None
        if obj is None:
            obj = ue.load_asset(path.split('.')[0])
        if obj is None:
            obj = ue.find_object(None, path)
        if obj is None:
            raise RuntimeError('Cannot resolve object for revert: ' + path)
        return obj
    raise RuntimeError('Value of type %s is not revertible: %r' % (kind, record))


def values_match(a, b, tolerance=1e-4):
    """Compare two encoded records numerically (floats with relative tolerance)."""
    if a is None or b is None or a.get('type') != b.get('type'):
        return False
    kind = a['type']
    if kind == 'none':
        return True
    if kind == 'float':
        return abs(a['value'] - b['value']) <= tolerance * max(1.0, abs(b['value']))
    if kind in ('Rotator', 'Vector', 'LinearColor'):
        return all(abs(x - y) <= tolerance * max(1.0, abs(y)) for x, y in zip(a['value'], b['value']))
    if kind == 'enum':
        return a['int'] == b['int']
    if kind == 'object':
        return a['path'].split('.')[0] == b['path'].split('.')[0]
    return a.get('value') == b.get('value')


def spec_value(ue, raw, context):
    """Spec entry -> engine value. context: dict with 'extendedRange', 'lensAttenuation', 'hdri'."""
    if isinstance(raw, dict):
        if '$enum' in raw:
            class_name, member = raw['$enum'].split('.')
            return getattr(getattr(ue, class_name), member)
        if '$linearColor' in raw:
            return ue.LinearColor(*raw['$linearColor'])
        if '$color' in raw:
            return ue.Color(*raw['$color'])
        if '$asset' in raw:
            asset = ue.load_asset(raw['$asset'])
            if asset is None:
                raise RuntimeError('Asset not found: ' + raw['$asset'])
            return asset
        if '$ev100' in raw:
            return ev100_to_brightness_field(raw['$ev100'], context['extendedRange'], context['lensAttenuation'])
        if '$importedHdri' in raw:
            if context.get('hdri') is None:
                raise RuntimeError('HDRI cubemap requested but nothing was imported')
            return context['hdri']
        raise RuntimeError('Unknown spec value encoding: %r' % (raw,))
    return raw


# --------------------------------------------------------------------------
# Engine-side work
# --------------------------------------------------------------------------

class Polish:
    """Engine handles, discovered actors, change log and receipt."""

    def __init__(self, ue, spec):
        self.ue = ue
        self.spec = spec
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.world = None
        self.receipt = None
        self.receipt_path = None
        self.context = {'extendedRange': False, 'lensAttenuation': 0.78, 'hdri': None}
        self.created = []

    # -- receipt -----------------------------------------------------------

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    # -- guards ------------------------------------------------------------

    def guard_world(self, load_target):
        ue = self.ue
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
        if self.editor.get_game_world():
            raise RuntimeError('A game world is active; never mutate during play')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present before loading target; refusing to discard unsaved work')
        if load_target and not self.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        self.world = self.editor.get_editor_world()
        loaded = self.world.get_outermost().get_name()
        if loaded != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present; resolve before a checkpointed lighting change')

    def read_cvars(self):
        ue = self.ue
        extended = ue.SystemLibrary.get_console_variable_int_value('r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange')
        lens = ue.SystemLibrary.get_console_variable_float_value('r.EyeAdaptation.LensAttenuation')
        if not lens or lens <= 0.0:
            lens = 0.78
        self.context['extendedRange'] = bool(extended)
        self.context['lensAttenuation'] = float(lens)
        exposure = self.spec['postProcess']['exposure']
        return {
            'r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange': int(extended),
            'r.EyeAdaptation.LensAttenuation': float(lens),
            'r.Shadow.Virtual.Enable': ue.SystemLibrary.get_console_variable_int_value('r.Shadow.Virtual.Enable'),
            'r.DynamicGlobalIlluminationMethod': ue.SystemLibrary.get_console_variable_int_value('r.DynamicGlobalIlluminationMethod'),
            'r.ReflectionMethod': ue.SystemLibrary.get_console_variable_int_value('r.ReflectionMethod'),
            'exposureBoundsUnits': 'EV100' if extended else 'raw scene luminance (2^EV100 written)',
            'exposureBoundsWritten': {'min': ev100_to_brightness_field(exposure['minEV100'], bool(extended), lens),
                                      'max': ev100_to_brightness_field(exposure['maxEV100'], bool(extended), lens)},
            'exposureBoundsEV100': {'min': exposure['minEV100'], 'max': exposure['maxEV100']},
        }

    # -- discovery ---------------------------------------------------------

    def discover(self, require_clean=True):
        ue = self.ue
        found = {'DirectionalLight': [], 'SkyLight': [], 'SkyAtmosphere': [], 'VolumetricCloud': [], 'PostProcessVolume': [], 'ExponentialHeightFog': [], 'tagged': [], 'kodesh': []}
        tag = self.spec['actorTag']
        for actor in self.actors.get_all_level_actors():
            if isinstance(actor, ue.DirectionalLight):
                found['DirectionalLight'].append(actor)
            elif isinstance(actor, ue.SkyLight):
                found['SkyLight'].append(actor)
            elif isinstance(actor, ue.SkyAtmosphere):
                found['SkyAtmosphere'].append(actor)
            elif isinstance(actor, ue.VolumetricCloud):
                found['VolumetricCloud'].append(actor)
            elif isinstance(actor, ue.PostProcessVolume):
                found['PostProcessVolume'].append(actor)
            elif isinstance(actor, ue.ExponentialHeightFog):
                found['ExponentialHeightFog'].append(actor)
            if tag in [str(t) for t in actor.tags]:
                found['tagged'].append(actor)
            if actor.get_actor_label() == self.spec['kodeshLightLabel']:
                found['kodesh'].append(actor)
        summary = {key: [{'name': a.get_name(), 'label': a.get_actor_label(), 'class': a.get_class().get_name()} for a in value] for key, value in found.items()}
        if require_clean:
            for key, expected in self.spec['expectedActorCounts'].items():
                if len(found[key]) != expected:
                    raise RuntimeError('Expected %d %s actor(s), found %d: %s' % (expected, key, len(found[key]), summary[key]))
            if found['tagged']:
                raise RuntimeError('Lighting polish already applied (tagged actors present); run -LightingRevert first: %s' % summary['tagged'])
            sun_component = found['DirectionalLight'][0].get_component_by_class(ue.DirectionalLightComponent)
            if not sun_component.get_editor_property('atmosphere_sun_light'):
                raise RuntimeError('The directional light is not the atmosphere sun light')
        return found, summary

    def snapshot_unrelated(self, exclude_names):
        rows = {}
        for actor in self.actors.get_all_level_actors():
            name = actor.get_name()
            if name in exclude_names:
                continue
            loc = actor.get_actor_location()
            rot = actor.get_actor_rotation()
            scale = actor.get_actor_scale3d()
            rows[name] = (actor.get_actor_label(), round(loc.x, 3), round(loc.y, 3), round(loc.z, 3), round(rot.pitch, 3), round(rot.yaw, 3), round(rot.roll, 3),
                          round(scale.x, 4), round(scale.y, 4), round(scale.z, 4))
        return rows

    # -- property changes --------------------------------------------------

    def read_prop(self, obj, prop):
        try:
            return encode_value(self.ue, obj.get_editor_property(prop))
        except Exception as error:
            return {'type': 'unavailable', 'error': str(error)}

    def record_only(self, target, obj, props):
        return {prop: self.read_prop(obj, prop) for prop in props}

    def set_prop(self, target, obj, prop, raw, required, actor=None, component_class=None, struct=None):
        """Read before, set, read after; append a change record. Returns the record."""
        ue = self.ue
        record = {'target': target, 'property': prop, 'required': required, 'applied': False,
                  'actorName': actor.get_name() if actor else None, 'actorLabel': actor.get_actor_label() if actor else None,
                  'componentClass': component_class, 'struct': struct}
        record['before'] = self.read_prop(obj, prop)
        if record['before']['type'] == 'unavailable':
            record['note'] = 'property unavailable in this engine build; skipped'
            self.receipt['changes'].append(record)
            if required:
                raise RuntimeError('Required property %s.%s unavailable: %s' % (target, prop, record['before']['error']))
            return record
        try:
            value = spec_value(ue, raw, self.context)
            record['desired'] = encode_value(ue, value)
            obj.set_editor_property(prop, value)
            record['after'] = self.read_prop(obj, prop)
            record['applied'] = True
            record['matches'] = values_match(record['after'], record['desired'], self.spec['verification']['floatRelativeTolerance'])
            if not record['matches']:
                raise RuntimeError('Readback differs for %s.%s: %r vs %r' % (target, prop, record['after'], record['desired']))
        except Exception as error:
            record['error'] = repr(error)
            self.receipt['changes'].append(record)
            if required or record['applied']:
                raise
            record['note'] = 'set failed; skipped (not required)'
            return record
        self.receipt['changes'].append(record)
        return record

    def apply_block(self, target, obj, block, actor, component_class):
        required = set(block['required'])
        for prop, raw in block['properties'].items():
            self.set_prop(target, obj, prop, raw, prop in required, actor=actor, component_class=component_class)

    def set_label(self, target, actor, label):
        record = {'target': target, 'property': 'actor_label', 'required': False, 'actorName': actor.get_name(), 'actorLabel': actor.get_actor_label(),
                  'before': {'type': 'str', 'value': actor.get_actor_label()}, 'desired': {'type': 'str', 'value': label}}
        actor.set_actor_label(label)
        record['after'] = {'type': 'str', 'value': actor.get_actor_label()}
        record['applied'] = True
        record['matches'] = record['after']['value'] == label
        self.receipt['changes'].append(record)

    # -- stages ------------------------------------------------------------

    def apply_sun(self, actor, sun):
        ue = self.ue
        component = actor.get_component_by_class(ue.DirectionalLightComponent)
        rot = sun['rotatorPitchYawRoll']
        record = {'target': 'sun', 'property': 'actor_rotation', 'required': True, 'actorName': actor.get_name(), 'actorLabel': actor.get_actor_label(),
                  'before': encode_value(ue, actor.get_actor_rotation()), 'desired': {'type': 'Rotator', 'value': rot}}
        forward_before = actor.get_actor_forward_vector()
        record['forwardBefore'] = [float(forward_before.x), float(forward_before.y), float(forward_before.z)]
        actor.set_actor_rotation(ue.Rotator(pitch=rot[0], yaw=rot[1], roll=rot[2]), False)
        record['after'] = encode_value(ue, actor.get_actor_rotation())
        forward = actor.get_actor_forward_vector()
        record['forwardAfter'] = [float(forward.x), float(forward.y), float(forward.z)]
        record['forwardDotDesired'] = dot(record['forwardAfter'], sun['directionUE'])
        record['applied'] = True
        record['matches'] = record['forwardDotDesired'] >= self.spec['verification']['directionDotMinimum']
        self.receipt['changes'].append(record)
        if not record['matches']:
            raise RuntimeError('Sun forward vector %r does not match the wanted direction %r' % (record['forwardAfter'], sun['directionUE']))
        self.apply_block('sun', component, self.spec['sun']['component'], actor, 'DirectionalLightComponent')
        self.set_label('sun', actor, '%s %s az %g el %g' % (self.spec['sun']['labelAfter'], sun['preset'], sun['azimuthDeg'], sun['elevationDeg']))

    def apply_sky_atmosphere(self, actor):
        ue = self.ue
        component = actor.get_component_by_class(ue.SkyAtmosphereComponent)
        self.receipt['recordedOnly']['skyAtmosphere'] = self.record_only('skyAtmosphere', component, self.spec['skyAtmosphere']['recordOnly'])
        self.apply_block('skyAtmosphere', component, self.spec['skyAtmosphere']['component'], actor, 'SkyAtmosphereComponent')

    def import_hdri(self):
        ue = self.ue
        cfg = self.spec['hdri']
        check = hdri_check(self.spec, require=True)
        asset_path = self.spec['assetNamespace'] + '/' + cfg['assetName']
        library = ue.EditorAssetLibrary
        record = {'check': check, 'assetPath': asset_path, 'imported': False, 'reusedExisting': False}
        if library.does_asset_exist(asset_path):
            texture = ue.load_asset(asset_path)
            record['reusedExisting'] = True
        else:
            task = ue.AssetImportTask()
            task.set_editor_property('filename', str(ROOT / cfg['file']))
            task.set_editor_property('destination_path', self.spec['assetNamespace'])
            task.set_editor_property('destination_name', cfg['assetName'])
            task.set_editor_property('automated', True)
            task.set_editor_property('replace_existing', False)
            task.set_editor_property('save', True)
            ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            record['importedObjectPaths'] = [str(p) for p in task.get_editor_property('imported_object_paths')]
            texture = ue.load_asset(asset_path)
            record['imported'] = texture is not None
        if not isinstance(texture, ue.TextureCube):
            raise RuntimeError('HDRI did not import as a TextureCube: %r' % (texture,))
        if not library.save_loaded_asset(texture, only_if_is_dirty=True):
            raise RuntimeError('Saving the HDRI texture failed')
        record['class'] = texture.get_class().get_name()
        record['uassetSha256'] = sha256_of(disk_path(asset_path)) if disk_path(asset_path).exists() else None
        self.context['hdri'] = texture
        self.receipt['hdri'] = record
        return texture

    def apply_sky_light(self, actor, use_hdri):
        ue = self.ue
        component = actor.get_component_by_class(ue.SkyLightComponent)
        self.receipt['recordedOnly']['skyLight'] = self.record_only('skyLight', component, self.spec['skyLight']['recordOnly'])
        if use_hdri:
            self.import_hdri()
            self.apply_block('skyLight', component, self.spec['hdri']['skyLightProperties'], actor, 'SkyLightComponent')
        else:
            self.apply_block('skyLight', component, self.spec['skyLight']['component'], actor, 'SkyLightComponent')
        try:
            component.recapture_sky()
        except Exception as error:
            self.receipt['notes'].append('recapture_sky unavailable in this process: ' + repr(error))

    def apply_clouds(self, actor, enabled):
        ue = self.ue
        cfg = self.spec['clouds']
        component = actor.get_component_by_class(ue.VolumetricCloudComponent)
        current = component.get_editor_property('material')
        current_path = current.get_path_name().split('.')[0] if current else None
        record = {'currentMaterial': current_path, 'expectedSourceMaterial': cfg['expectedSourceMaterial'], 'enabled': enabled, 'parameters': {}}
        ml = ue.MaterialEditingLibrary
        if current is not None:
            for name in cfg['recordParameters']:
                try:
                    record['parameters'][name] = float(ml.get_material_instance_scalar_parameter_value(current, name))
                except Exception as error:
                    record['parameters'][name] = 'unavailable: ' + repr(error)
        self.receipt['clouds'] = record
        if not enabled:
            record['note'] = 'coverage untouched by switch'
            return
        if current_path != cfg['expectedSourceMaterial']:
            record['note'] = 'cloud material is not the expected donor; coverage untouched'
            return
        library = ue.EditorAssetLibrary
        target_path = cfg['scatteredMaterial']
        if library.does_asset_exist(target_path):
            scattered = ue.load_asset(target_path)
            record['scatteredReusedExisting'] = True
        else:
            scattered = library.duplicate_asset(cfg['expectedSourceMaterial'], target_path)
            record['scatteredDuplicated'] = scattered is not None
        if not isinstance(scattered, ue.MaterialInstanceConstant):
            raise RuntimeError('Scattered cloud material is not a MaterialInstanceConstant: %r' % (scattered,))
        record['coverageBefore'] = float(ml.get_material_instance_scalar_parameter_value(scattered, cfg['coverageParameter']))
        # UE 5.8 MaterialEditingLibrary setters always return False; verify by readback instead.
        ml.set_material_instance_scalar_parameter_value(scattered, cfg['coverageParameter'], float(cfg['coverage']))
        ml.update_material_instance(scattered)
        if abs(float(ml.get_material_instance_scalar_parameter_value(scattered, cfg['coverageParameter'])) - float(cfg['coverage'])) > 1e-4:
            raise RuntimeError('scalar parameter readback mismatch for ' + cfg['coverageParameter'])
        ml.update_material_instance(scattered)
        record['coverageAfter'] = float(ml.get_material_instance_scalar_parameter_value(scattered, cfg['coverageParameter']))
        if abs(record['coverageAfter'] - cfg['coverage']) > 1e-6:
            raise RuntimeError('Coverage readback differs: %r' % record['coverageAfter'])
        if not library.save_loaded_asset(scattered, only_if_is_dirty=False):
            raise RuntimeError('Saving the scattered cloud material failed')
        record['scatteredMaterial'] = target_path
        record['scatteredUassetSha256'] = sha256_of(disk_path(target_path))
        self.set_prop('clouds', component, 'material', {'$asset': target_path}, True, actor=actor, component_class='VolumetricCloudComponent')

    def apply_post_process(self, actor):
        ue = self.ue
        block = self.spec['postProcess']['settings']
        settings = actor.get_editor_property('settings')
        self.receipt['recordedOnly']['postProcess'] = self.record_only('postProcess', settings, self.spec['postProcess']['recordOnly'])
        required = set(block['required'])
        records = []
        for prop, raw in block['properties'].items():
            records.append(self.set_prop('postProcess', settings, prop, raw, prop in required, actor=actor, component_class=None, struct='settings'))
        actor.set_editor_property('settings', settings)
        committed = actor.get_editor_property('settings')
        for record in records:
            if record.get('applied'):
                record['afterCommit'] = self.read_prop(committed, record['property'])
                record['matches'] = values_match(record['afterCommit'], record['desired'], self.spec['verification']['floatRelativeTolerance'])
                if not record['matches']:
                    raise RuntimeError('Post-process field %s differs after commit: %r' % (record['property'], record['afterCommit']))
        self.receipt['recordedOnly']['postProcessVolume'] = {'unbound': self.read_prop(actor, 'unbound'), 'blend_weight': self.read_prop(actor, 'blend_weight'), 'enabled': self.read_prop(actor, 'enabled')}
        self.set_label('postProcess', actor, self.spec['postProcess']['labelAfter'])

    def spawn(self, cls, label, location, rotation):
        ue = self.ue
        actor = self.actors.spawn_actor_from_class(cls, ue.Vector(*location), ue.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]))
        if actor is None:
            raise RuntimeError('spawn_actor_from_class returned None for ' + label)
        actor.set_actor_label(label)
        actor.set_folder_path(self.spec['folder'])
        actor.set_editor_property('tags', [ue.Name(self.spec['actorTag'])])
        self.created.append(actor)
        return actor

    def create_fog(self):
        ue = self.ue
        cfg = self.spec['fog']
        actor = self.spawn(ue.ExponentialHeightFog, cfg['label'], cfg['location'], [0.0, 0.0, 0.0])
        component = actor.get_component_by_class(ue.ExponentialHeightFogComponent)
        self.apply_block('fog', component, cfg['component'], actor, 'ExponentialHeightFogComponent')
        self.receipt['created'].append({'target': 'fog', 'label': cfg['label'], 'name': actor.get_name(), 'class': actor.get_class().get_name(),
                                        'location': list(cfg['location']), 'folder': self.spec['folder']})

    def create_fill(self):
        ue = self.ue
        cfg = self.spec['fill']
        rotation = [cfg['rotation']['pitch'], cfg['rotation']['yaw'], cfg['rotation']['roll']]
        actor = self.spawn(ue.RectLight, cfg['label'], cfg['location'], rotation)
        component = actor.get_component_by_class(ue.RectLightComponent)
        mobility = getattr(ue.ComponentMobility, cfg['mobility'])
        component.set_mobility(mobility)
        self.apply_block('fill', component, cfg['component'], actor, 'RectLightComponent')
        forward = actor.get_actor_forward_vector()
        self.receipt['created'].append({'target': 'fill', 'label': cfg['label'], 'name': actor.get_name(), 'class': actor.get_class().get_name(),
                                        'location': list(cfg['location']), 'rotation': rotation, 'forward': [float(forward.x), float(forward.y), float(forward.z)],
                                        'mobility': encode_value(ue, component.get_editor_property('mobility')), 'folder': self.spec['folder']})

    # -- save / reopen / readback ------------------------------------------

    def find_actor(self, name, label):
        by_label = []
        for actor in self.actors.get_all_level_actors():
            if actor.get_name() == name:
                return actor
            if label and actor.get_actor_label() == label:
                by_label.append(actor)
        return by_label[0] if len(by_label) == 1 else None

    def readback(self, changes, key, compare_to):
        """Re-read every applied change from the (reloaded) level into record[key]."""
        ue = self.ue
        failures = []
        struct_cache = {}
        for record in changes:
            if not record.get('applied'):
                continue
            actor = self.find_actor(record['actorName'], record['actorLabel'])
            if actor is None:
                failures.append('%s: actor %s missing' % (record['target'], record['actorName']))
                continue
            if record['property'] == 'actor_label':
                value = {'type': 'str', 'value': actor.get_actor_label()}
            elif record['property'] == 'actor_rotation':
                value = encode_value(ue, actor.get_actor_rotation())
            elif record.get('struct'):
                struct_key = (actor.get_name(), record['struct'])
                if struct_key not in struct_cache:
                    struct_cache[struct_key] = actor.get_editor_property(record['struct'])
                value = self.read_prop(struct_cache[struct_key], record['property'])
            else:
                component = actor.get_component_by_class(getattr(ue, record['componentClass']))
                value = self.read_prop(component, record['property'])
            record[key] = value
            expected = record.get(compare_to)
            ok = values_match(value, expected, self.spec['verification']['floatRelativeTolerance'])
            if record['property'] == 'actor_rotation' and expected and value['type'] == 'Rotator':
                ok = dot(rotator_forward(value['value'][0], value['value'][1]), rotator_forward(expected['value'][0], expected['value'][1])) >= self.spec['verification']['directionDotMinimum']
            record[key + 'Matches'] = ok
            if not ok:
                failures.append('%s.%s: %r vs %r' % (record['target'], record['property'], value, expected))
        return failures

    def save_and_reopen(self):
        ue = self.ue
        if ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            dirty = [p.get_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
            raise RuntimeError('Dirty content packages before the map save (assets must be saved explicitly): %s' % dirty)
        if not self.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        self.receipt['mapSaved'] = True
        self.receipt['mapSha256AfterSave'] = sha256_of(ROOT / self.spec['targetMapFile'])
        self.write_receipt()
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('Map still dirty after save')
        if not self.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        self.world = self.editor.get_editor_world()


def _checkpoint(spec, prefix, stamp, map_file, map_sha_before):
    checkpoint = Path(spec['checkpointRoot']) / (prefix + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / TARGET[6:]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / TARGET[6:])
            copied.append(str(external))
    return checkpoint, copied


def _protected_hashes(spec):
    hashes = {}
    for asset in spec['protectedMaps']:
        path = disk_path(asset, 'umap')
        if not path.exists():
            raise RuntimeError('Required protected map missing: ' + str(path))
        hashes[asset] = sha256_of(path)
    for asset in spec.get('protectedAssets', []):
        path = disk_path(asset)
        if not path.exists():
            raise RuntimeError('Required protected asset missing: ' + str(path))
        hashes[asset] = sha256_of(path)
    return hashes


def _fresh_receipt(spec, prefix, stamp):
    folder = ROOT / spec['receiptFolder']
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (prefix + stamp + '.json')
    if path.exists():
        raise RuntimeError('Receipt already exists: ' + str(path))
    return path


def run(load_target=True, sun=None, use_hdri=False, fill=None, fog=None, clouds=None, dry_run=False):
    """Apply the lighting polish. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    spec = load_spec()
    fill = spec['fill']['enabledByDefault'] if fill is None else fill
    fog = spec['fog']['enabledByDefault'] if fog is None else fog
    clouds = spec['clouds']['enabledByDefault'] if clouds is None else clouds
    offline = offline_check(spec, sun=sun, use_hdri=use_hdri)
    sun_record = offline['sunSelected']
    polish = Polish(ue, spec)
    polish.guard_world(load_target)

    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = _protected_hashes(spec)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    polish.receipt_path = _fresh_receipt(spec, spec['receiptPrefix'], stamp)
    polish.receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == spec['lastKnownMapSha256'], 'protectedSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'engineVersion': ue.SystemLibrary.get_engine_version(),
        'switches': {'sun': sun_record['preset'], 'useHdri': use_hdri, 'fill': fill, 'fog': fog, 'clouds': clouds, 'dryRun': dry_run},
        'sun': sun_record, 'offlineCheck': offline, 'cvars': polish.read_cvars(), 'actors': {}, 'recordedOnly': {}, 'changes': [], 'created': [],
        'clouds': {}, 'hdri': None, 'notes': [], 'errors': [], 'mapSaved': False, 'checkpoint': None, 'limitations': list(spec['limitations']),
    }
    polish.write_receipt()

    saved = False
    try:
        found, summary = polish.discover(require_clean=True)
        polish.receipt['actors'] = summary
        polish.receipt['actorCountBefore'] = len(polish.actors.get_all_level_actors())
        if not found['kodesh']:
            polish.receipt['notes'].append('Kodesh interior light %s not found; nothing depends on it' % spec['kodeshLightLabel'])
        sun_actor = found['DirectionalLight'][0]
        ppv = found['PostProcessVolume'][0]
        exclude = {sun_actor.get_name(), ppv.get_name(), found['VolumetricCloud'][0].get_name(), found['SkyLight'][0].get_name(), found['SkyAtmosphere'][0].get_name()}
        baseline = polish.snapshot_unrelated(exclude)
        polish.receipt['unrelatedActorBaselineCount'] = len(baseline)

        if dry_run:
            sun_component = sun_actor.get_component_by_class(ue.DirectionalLightComponent)
            polish.receipt['recordedOnly']['sunBefore'] = polish.record_only('sun', sun_component, list(spec['sun']['component']['properties']))
            polish.receipt['recordedOnly']['sunRotationBefore'] = encode_value(ue, sun_actor.get_actor_rotation())
            polish.receipt['recordedOnly']['postProcessBefore'] = polish.record_only('postProcess', ppv.get_editor_property('settings'), list(spec['postProcess']['settings']['properties']) + spec['postProcess']['recordOnly'])
            polish.receipt['recordedOnly']['skyLightBefore'] = polish.record_only('skyLight', found['SkyLight'][0].get_component_by_class(ue.SkyLightComponent), list(spec['skyLight']['component']['properties']) + spec['skyLight']['recordOnly'])
            polish.receipt['recordedOnly']['skyAtmosphereBefore'] = polish.record_only('skyAtmosphere', found['SkyAtmosphere'][0].get_component_by_class(ue.SkyAtmosphereComponent), list(spec['skyAtmosphere']['component']['properties']) + spec['skyAtmosphere']['recordOnly'])
            polish.apply_clouds(found['VolumetricCloud'][0], enabled=False)
            polish.receipt['status'] = 'dry_run_no_mutation_map_unchanged'
            return polish.receipt

        checkpoint, copied = _checkpoint(spec, spec['checkpointPrefix'], stamp, map_file, map_sha_before)
        polish.receipt['checkpoint'] = str(checkpoint)
        polish.receipt['oneFilePerActorFoldersCopied'] = copied
        polish.receipt['status'] = 'checkpointed_apply_started'
        polish.write_receipt()

        polish.apply_sun(sun_actor, sun_record)
        polish.write_receipt()
        polish.apply_sky_atmosphere(found['SkyAtmosphere'][0])
        polish.apply_sky_light(found['SkyLight'][0], use_hdri)
        polish.write_receipt()
        polish.apply_clouds(found['VolumetricCloud'][0], enabled=clouds)
        polish.write_receipt()
        polish.apply_post_process(ppv)
        polish.write_receipt()
        if fog:
            polish.create_fog()
        if fill:
            polish.create_fill()
        polish.write_receipt()

        created_names = {a.get_name() for a in polish.created}
        current = polish.snapshot_unrelated(exclude | created_names)
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed or len(current) != len(baseline):
            raise RuntimeError('Unrelated actors changed before save: %s' % (changed or 'count differs')[:10])
        polish.receipt['unrelatedActorsUnchangedBeforeSave'] = True

        polish.save_and_reopen()
        saved = True
        polish.receipt['mapSaved'] = True
        polish.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        polish.write_receipt()

        reopened = polish.snapshot_unrelated(exclude | created_names)
        # created actors keep their names across save/reload; exclude by name again
        changed = [name for name, row in baseline.items() if reopened.get(name) != row]
        if changed:
            raise RuntimeError('Unrelated actors differ after reopen: %s' % changed[:10])
        polish.receipt['unrelatedActorsUnchangedAfterReopen'] = True
        failures = polish.readback(polish.receipt['changes'], 'afterReopen', 'desired')
        for created in polish.receipt['created']:
            actor = polish.find_actor(created['name'], created['label'])
            created['presentAfterReopen'] = actor is not None
            if actor is None:
                failures.append('created actor missing after reopen: ' + created['label'])
            else:
                created['tagPresentAfterReopen'] = spec['actorTag'] in [str(t) for t in actor.tags]
        polish.receipt['reopenReadbackFailures'] = failures
        polish.receipt['actorCountAfter'] = len(polish.actors.get_all_level_actors())
        if failures:
            raise RuntimeError('Reopen readback failed: %s' % failures[:10])
        polish.receipt['status'] = APPLIED_STATUS
        return polish.receipt
    except Exception as error:
        polish.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        polish.receipt['status'] = 'failed_after_save_checkpoint_available' if polish.receipt.get('mapSaved') or sha256_of(map_file) != map_sha_before else 'failed_before_save_map_unchanged'
        raise
    finally:
        polish.receipt['mapSha256After'] = sha256_of(map_file)
        polish.receipt['mapBytesChanged'] = polish.receipt['mapSha256After'] != map_sha_before
        polish.receipt['protectedUnchanged'] = _protected_hashes(spec) == protected
        polish.receipt['appliedChangeCount'] = sum(1 for c in polish.receipt['changes'] if c.get('applied'))
        polish.receipt['skippedChangeCount'] = sum(1 for c in polish.receipt['changes'] if not c.get('applied'))
        if not polish.receipt['protectedUnchanged']:
            polish.receipt['status'] = 'failed_protected_hash_guard'
            polish.receipt['errors'].append({'stage': 'verification', 'error': 'Protected hash changed'})
        polish.write_receipt()
        if not polish.receipt['protectedUnchanged']:
            raise RuntimeError('Protected hash changed')


def revert(receipt_path=None, load_target=True):
    """Restore the before-values of an apply receipt, destroy created actors, save, reopen, read back."""
    import unreal as ue
    spec = load_spec()
    if receipt_path:
        source_path = Path(receipt_path)
        source = json.loads(source_path.read_text(encoding='utf-8-sig'))
        if not source.get('mapSaved'):
            raise RuntimeError('Apply receipt never saved the map; nothing to revert: ' + str(source_path))
    else:
        source_path, source = latest_apply_receipt(spec)
    polish = Polish(ue, spec)
    polish.guard_world(load_target)

    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = _protected_hashes(spec)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    polish.receipt_path = _fresh_receipt(spec, spec['revertReceiptPrefix'], stamp)
    polish.receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'revertedFrom': str(source_path), 'revertedFromStamp': source.get('stamp'), 'mapMatchesApplySave': map_sha_before == source.get('mapSha256AfterSave'),
        'protectedSha256Before': protected, 'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'engineVersion': ue.SystemLibrary.get_engine_version(),
        'changes': [], 'destroyed': [], 'assetsLeftOnDisk': [], 'errors': [], 'notes': [], 'mapSaved': False, 'checkpoint': None,
    }
    polish.write_receipt()
    if not polish.receipt['mapMatchesApplySave']:
        polish.receipt['notes'].append('Map changed since the apply receipt saved it; before-values are still restored property by property.')

    saved = False
    try:
        found, summary = polish.discover(require_clean=False)
        polish.receipt['actors'] = summary
        checkpoint, copied = _checkpoint(spec, spec['revertCheckpointPrefix'], stamp, map_file, map_sha_before)
        polish.receipt['checkpoint'] = str(checkpoint)
        polish.receipt['oneFilePerActorFoldersCopied'] = copied
        polish.receipt['status'] = 'checkpointed_revert_started'
        polish.write_receipt()

        created_names = {c['name'] for c in source.get('created', [])}
        structs = {}
        for record in reversed(source['changes']):
            if not record.get('applied') or record.get('actorName') in created_names:
                continue
            before = record['before']
            entry = {'target': record['target'], 'property': record['property'], 'actorName': record['actorName'], 'actorLabel': record['actorLabel'],
                     'componentClass': record.get('componentClass'), 'struct': record.get('struct'), 'desired': before, 'applied': False}
            actor = polish.find_actor(record['actorName'], record.get('after', {}).get('value') if record['property'] == 'actor_label' else record['actorLabel'])
            if actor is None:
                actor = polish.find_actor(record['actorName'], record['actorLabel'])
            if actor is None:
                entry['error'] = 'actor not found'
                polish.receipt['changes'].append(entry)
                raise RuntimeError('Revert: actor %s (%s) not found' % (record['actorName'], record['actorLabel']))
            if record['property'] == 'actor_label':
                entry['before'] = {'type': 'str', 'value': actor.get_actor_label()}
                actor.set_actor_label(before['value'])
                entry['after'] = {'type': 'str', 'value': actor.get_actor_label()}
            elif record['property'] == 'actor_rotation':
                entry['before'] = encode_value(ue, actor.get_actor_rotation())
                actor.set_actor_rotation(decode_value(ue, before), False)
                entry['after'] = encode_value(ue, actor.get_actor_rotation())
            elif record.get('struct'):
                key = (actor.get_name(), record['struct'])
                if key not in structs:
                    structs[key] = (actor, actor.get_editor_property(record['struct']))
                struct = structs[key][1]
                entry['before'] = polish.read_prop(struct, record['property'])
                struct.set_editor_property(record['property'], decode_value(ue, before))
                entry['after'] = polish.read_prop(struct, record['property'])
            else:
                component = actor.get_component_by_class(getattr(ue, record['componentClass']))
                entry['before'] = polish.read_prop(component, record['property'])
                component.set_editor_property(record['property'], decode_value(ue, before))
                entry['after'] = polish.read_prop(component, record['property'])
            entry['applied'] = True
            entry['matches'] = values_match(entry['after'], before, spec['verification']['floatRelativeTolerance'])
            polish.receipt['changes'].append(entry)
            if not entry['matches']:
                raise RuntimeError('Revert readback differs for %s.%s: %r vs %r' % (record['target'], record['property'], entry['after'], before))
        for (name, struct_name), (actor, struct) in structs.items():
            actor.set_editor_property(struct_name, struct)
        polish.write_receipt()

        for created in source.get('created', []):
            actor = polish.find_actor(created['name'], created['label'])
            if actor is None:
                polish.receipt['notes'].append('created actor already absent: ' + created['label'])
                continue
            if spec['actorTag'] not in [str(t) for t in actor.tags]:
                raise RuntimeError('Refusing to destroy untagged actor ' + created['label'])
            if not polish.actors.destroy_actor(actor):
                raise RuntimeError('destroy_actor failed for ' + created['label'])
            polish.receipt['destroyed'].append({'name': created['name'], 'label': created['label']})
        for key in ('hdri', 'clouds'):
            block = source.get(key) or {}
            for path_key in ('assetPath', 'scatteredMaterial'):
                if block.get(path_key):
                    polish.receipt['assetsLeftOnDisk'].append(block[path_key])
        polish.write_receipt()

        polish.save_and_reopen()
        saved = True
        polish.receipt['mapSaved'] = True
        polish.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        failures = polish.readback(polish.receipt['changes'], 'afterReopen', 'desired')
        remaining = [a.get_actor_label() for a in polish.actors.get_all_level_actors() if spec['actorTag'] in [str(t) for t in a.tags]]
        if remaining:
            failures.append('tagged actors remain after reopen: %s' % remaining)
        polish.receipt['reopenReadbackFailures'] = failures
        if failures:
            raise RuntimeError('Revert readback failed: %s' % failures[:10])
        polish.receipt['status'] = REVERTED_STATUS
        source['revertedBy'] = str(polish.receipt_path)
        source_path.write_text(json.dumps(source, indent=2, default=str) + '\n', encoding='utf-8')
        return polish.receipt
    except Exception as error:
        polish.receipt['errors'].append({'stage': 'revert', 'error': repr(error)})
        polish.receipt['status'] = 'failed_after_save_checkpoint_available' if polish.receipt.get('mapSaved') or sha256_of(map_file) != map_sha_before else 'failed_before_save_map_unchanged'
        raise
    finally:
        polish.receipt['mapSha256After'] = sha256_of(map_file)
        polish.receipt['mapBytesChanged'] = polish.receipt['mapSha256After'] != map_sha_before
        polish.receipt['protectedUnchanged'] = _protected_hashes(spec) == protected
        if not polish.receipt['protectedUnchanged']:
            polish.receipt['status'] = 'failed_protected_hash_guard'
            polish.receipt['errors'].append({'stage': 'verification', 'error': 'Protected hash changed'})
        polish.write_receipt()
        if not polish.receipt['protectedUnchanged']:
            raise RuntimeError('Protected hash changed')


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

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
    return 'release_lighting_polish.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def parse_switches(tokens):
    lowered = [t.lower() for t in tokens]
    switches = {'sun': None, 'use_hdri': '-usehdri' in lowered, 'fill': not ('-lightingnofill' in lowered), 'fog': not ('-lightingnofog' in lowered),
                'clouds': not ('-lightingnoclouds' in lowered), 'dry_run': '-lightingdryrun' in lowered, 'revert': False, 'revert_receipt': None}
    for token in tokens:
        low = token.lower()
        if low.startswith('-lightingsun='):
            switches['sun'] = token.split('=', 1)[1].strip('"')
        elif low == '-lightingrevert':
            switches['revert'] = True
        elif low.startswith('-lightingrevert='):
            switches['revert'] = True
            switches['revert_receipt'] = token.split('=', 1)[1].strip('"')
    return switches


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    switches = parse_switches(command_line.split())
    try:
        if switches['revert']:
            receipt = revert(receipt_path=switches['revert_receipt'], load_target=True)
            ue.log('release_lighting_polish revert: %s restored %d destroyed %d' % (receipt['status'], len(receipt['changes']), len(receipt['destroyed'])))
        else:
            receipt = run(load_target=True, sun=switches['sun'], use_hdri=switches['use_hdri'], fill=switches['fill'], fog=switches['fog'],
                          clouds=switches['clouds'], dry_run=switches['dry_run'])
            ue.log('release_lighting_polish: %s sun %s applied %s skipped %s created %d' % (
                receipt['status'], receipt['sun']['preset'], receipt.get('appliedChangeCount'), receipt.get('skippedChangeCount'), len(receipt['created'])))
    except Exception as error:
        ue.log_error('release_lighting_polish failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line.lower() and '-run=pythonscript' not in command_line.lower():
            ue.SystemLibrary.quit_editor()


def _offline_main():
    import argparse
    parser = argparse.ArgumentParser(description='Offline consistency check for the lighting polish spec')
    parser.add_argument('--sun', help='preset name or <azimuth>,<elevation>')
    parser.add_argument('--use-hdri', action='store_true', help='also require the HDRI and its provenance hash')
    args = parser.parse_args()
    print(json.dumps(offline_check(load_spec(), sun=args.sun, use_hdri=args.use_hdri), indent=2))


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        _offline_main()
elif _invoked_as_native_script():
    _main()

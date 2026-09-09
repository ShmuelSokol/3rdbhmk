"""Guarded placement of the runtime time-of-day and weather actors into the combined map.

Adds RELEASE_SkyTimeOfDay (AMikdashTimeOfDay) and RELEASE_SkyWeather (AMikdashWeather)
to /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough, wired to the existing sun, sky
light, sky atmosphere, volumetric cloud, height fog and post-process volume. Every
number comes from Scripts/release_sky_tod.spec.json.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_sky_tod.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-SkyTOD-02.log"

A -run=pythonscript commandlet starts with NO map loaded. This module therefore loads
the target map itself (LevelEditorSubsystem.load_level) after the project-dir, game-world
and dirty-package guards, exactly like release_place_assets.py. Importing it inside a GUI
editor does nothing; call place(load_target=False) there after opening the map.

Optional switches (read from the engine command line):
  -Target=Candidate48   (alias: -SkyToDTarget=; Main50 | Candidate48, plus the usual aliases)
        Explicit reviewed48cm map; main remains default. Placement-only, no bake/revert.
        Input map hash and Selected48 descriptor/pivot must match the reviewed checkpoint.
        Both maps' hashes are pinned WITH PROVENANCE in MAP_HASH_PROVENANCE below (which
        pass last wrote each map, and which hash it superseded) -- never refreshed blindly.
  -SkyToDBake=<dawn|sunrise|morning|midday|afternoon|sunset|dusk|night>
        Also write that one preset into the existing lighting actors for editor preview.
        Default: none. Without it NO existing actor property is written by this pass.
  -SkyToDRevert=<path to a native-place receipt>
        Write every recorded "before" value back, destroy the placed actors, save, reopen.
  -SkyToDPort
        PORT the adopted daylight (sun 6500 K, sky light 1.3) onto the target's existing sun
        and sky light. This is a PORT, not a review: the three PIE comparisons that adopted
        these numbers were run on Main50, and no comparison has been run on the target. The
        receipt says so in words and names the three receipts. Refuses unless the target is
        on the exact reviewed BASELINE (30,000 lux / 5000 K / use_temperature / sky 1.0);
        it will not adjust a map sitting on some third setting. Guard pattern in full:
        read-before-write of every recorded lighting value, checkpoint under
        ReviewCheckpoints, before/after map hashes, save, reopen, numeric readback, and a
        whole-level comparison through release_place_assets.py's shared snapshot rules.
        release_reviewed_daylight.py is IMPORTED (validate_preset) and never weakened.
  -SkyToDPortRevert=<path to a native-daylight-port receipt>
        Replay that receipt's revert block: the recorded before values and sun label are
        written back, saved, reopened and read back.
  -SkyToDFixSunLabel   (alias -SkyToDRelabel)
        Label only. The sun actor's label states its own colour temperature; where that no
        longer matches the light, correct it in the same guarded pass. Writes no value.
  -SkyToDVerify
        Read-only. Load the target, confirm RELEASE_SkyTimeOfDay / RELEASE_SkyWeather are
        still present with the spec's settings after later passes have saved over the map,
        read every recorded lighting value and the reviewed daylight, write a
        native-verify-<target>-<stamp>.json receipt. Saves nothing, mutates nothing.

Run WITHOUT the engine for the offline check only (no map is touched):

  python Scripts/release_sky_tod.py

Safety model (the release_place_assets.py pattern):
  * Refuses to run with the wrong project directory, a game world, dirty packages, or a
    loaded world that is not the combined map. The map hash is RECORDED, never gated.
  * Records every lighting value listed in the spec BEFORE any mutation, so the receipt
    alone is enough to revert, and copies Walkthrough.umap (plus any One-File-Per-Actor
    folders) to ReviewCheckpoints/SkyTOD-<stamp>/ and verifies the copy.
  * The time-of-day class is required (the binary must contain it). The weather class is
    optional: if the binary predates MikdashWeather.h it becomes an OMISSION with evidence.
  * Refuses to duplicate: an existing RELEASE_SkyTimeOfDay or RELEASE_SkyWeather is a
    refusal before mutation.
  * Lists live UnrealEditor processes before believing a save failure. A save that
    "fails" in this project has more than once been a leftover editor holding the file.
  * Saves, reopens, reads every placed property and every recorded lighting value back
    numerically. The authored fog/skylight tune from the spec is asserted byte-identical
    unless a twilight/night bake was requested (then the delta is the point and is
    recorded).
  * The reviewed daylight adopted by Shmuel (sun 6500 K / 30,000 lux, sky light 1.3, fog
    0.0015 / 0.15 / 8000, volumetric fog off -- spec.reviewedDaylight) is HONOURED, not
    re-written: in default mode this pass writes no existing lighting value at all, so the
    check is that a reviewed value which agreed BEFORE the pass still agrees after it. A
    value that already diverged is reported as a pre-existing divergence, not blamed on
    this run; a -SkyToDBake preset may deliberately differ at its time of day and the
    delta is recorded instead.
  * The receipt JSON is written at start and again in finally, preserving partial state.

UE 5.8 pitfalls this script is built around:
  * MaterialEditingLibrary instance getters are used read-only here (the pass never edits
    a material asset); the cloud parameters are recorded from the assigned instance.
  * Property setters are verified by reading the value back; return values are ignored.
"""
import csv
import io
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_sky_tod.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
CANDIDATE = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'

# Map hashes are PINNED WITH PROVENANCE, never refreshed blindly: a spec that silently
# adopts whatever is on disk cannot tell a reviewed input from a damaged one. Each entry
# says which pass last wrote the map, so a mismatch is a question ("what saved it since?"),
# not a nuisance.
MAP_HASH_PROVENANCE = {
    'Candidate48': {
        'map': CANDIDATE,
        'sha256': '97556e02e5ceaa6c53ea73dd2ebaf9280467265055724555fd4b1e6625f66fd0',
        'bytes': 23575718,
        'observedUtc': '2026-09-09',
        'writtenBy': ('release_sky_tod.py -SkyToDPort -- the reviewed daylight PORTED from the '
                      'Main50 review (sun 5000 K -> 6500 K, sky light 1.0 -> 1.3, sun label '
                      'corrected), receipt native-daylight-port-Candidate48-20260909T172832268438Z.json'),
        'supersedes': ('b44632dcebddd81abbd530cfc318457f29bb26fe935ff0dbeab21957262a339c '
                       '(release_herodian_ashlar_v4.py, 2026-09-09, publication clone commit '
                       'c4dbf2b7, after the 2026-09-08 Aron re-pivot that set '
                       'FixedArchitectureOriginCm (-6200,0,0)); before that '
                       'd494549bc433bacfec672d456a2e871258537cbb6d558562ac2b96810c7fa785, the '
                       'reviewed 24-resident checkpoint of 2026-09-08)'),
    },
    'Main50': {
        'map': TARGET,
        'sha256': '7214046fa3454907784efeae0a20b7a32ac8853179bcac13a5eb79a5e6ab89fd',
        'bytes': 25601239,
        'observedUtc': '2026-09-09',
        'writtenBy': ('release_sky_tod.py -SkyToDFixSunLabel -- label only, no lighting value '
                      'written; the sun actor still said 5000 K after the 2026-09-08 review moved '
                      'it to 6500 K. Receipt native-relabel-Main50-20260909T172939800657Z.json'),
        'supersedes': ('c1fe80080e4496c4cf370c9590e1688c664c96f8ce91b135534ae368ae19346c '
                       '(release_herodian_ashlar_v4.py, 2026-09-09, same pass as the candidate); '
                       'before that 9d2c492069359e356064b7cf5f2f7759e529c93706360ab7fc4ac395210bd273, '
                       'the spec lastKnownMapSha256 of 2026-09-08)'),
    },
}
CANDIDATE_SHA = MAP_HASH_PROVENANCE['Candidate48']['sha256']

PRESET_NAMES = ('dawn', 'sunrise', 'morning', 'midday', 'afternoon', 'sunset', 'dusk', 'night')


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so offline_check() can run anywhere.
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


TARGET_ALIASES = {
    'main50': 'Main50', 'main': 'Main50', 'legacy': 'Main50',
    'integratedreviewv2': 'Main50',
    'candidate48': 'Candidate48', 'candidate': 'Candidate48', 'amah48': 'Candidate48',
    '48': 'Candidate48', 'selected48': 'Candidate48',
}


def _normalise_target(value):
    """-Target / -SkyToDTarget accept either canonical name or a common alias."""
    key = (value or '').strip().strip('"').lower()
    if key in TARGET_ALIASES:
        return TARGET_ALIASES[key]
    raise RuntimeError('Unknown sky target %r; use Main50 or Candidate48' % value)


def load_spec(target_name="Main50"):
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    if target_name not in ('Main50', 'Candidate48'):
        raise RuntimeError('Unknown sky target: ' + target_name)
    if target_name == 'Candidate48':
        spec['targetMap'] = CANDIDATE
        spec['targetMapFile'] = 'Content/' + CANDIDATE[6:] + '.umap'
        spec['checkpointPrefix'] += 'Candidate48-'
        spec['receiptPrefix'] += 'Candidate48-'
    spec['targetName'] = target_name
    # The pinned hash for THIS target, with the provenance that justifies it.
    spec['lastKnownMapSha256'] = MAP_HASH_PROVENANCE[target_name]['sha256']
    spec['lastKnownMapSha256Provenance'] = MAP_HASH_PROVENANCE[target_name]
    maps = set(spec['protectedMaps'])
    maps.update('/Game/' + p.relative_to(ROOT / 'Content').with_suffix('').as_posix()
                for p in (ROOT / 'Content').rglob('*.umap'))
    maps.discard(spec['targetMap'])
    spec['protectedMaps'] = sorted(maps)
    return spec


def editor_processes():
    """Zombie check. A 'failed' save is often a leftover editor holding the file."""
    result = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'],
                            capture_output=True, text=True, timeout=30, check=True)
    rows = list(csv.reader(io.StringIO(result.stdout)))
    if not rows or any(len(row) < 2 for row in rows):
        raise RuntimeError('Unparseable process inventory; refusing to assume no editor')
    return [row for row in rows if row[0].lower() in ('unrealeditor.exe', 'unrealeditor-cmd.exe')]



def relative_close(a, b, tolerance):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        # Whole daylight records are compared as dicts; without this they fell to exact
        # equality, which no float readback survives reliably.
        return a.keys() == b.keys() and all(relative_close(a[k], b[k], tolerance) for k in a)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        scale = max(1.0, abs(a), abs(b))
        return abs(a - b) <= tolerance * scale
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return all(relative_close(x, y, tolerance) for x, y in zip(a, b))
    return a == b


def offline_check(spec=None):
    """Everything that can be established without opening the editor."""
    spec = spec or load_spec()
    problems = []
    map_file = ROOT / spec['targetMapFile']
    if not map_file.exists():
        problems.append('target map missing: ' + str(map_file))
    header = ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashTimeOfDay.h'
    weather_header = ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashWeather.h'
    dll = ROOT / 'Plugins/MikdashRuntime/Binaries/Win64/UnrealEditor-MikdashRuntime.dll'
    uht = ROOT / 'Plugins/MikdashRuntime/Intermediate/Build/Win64/UnrealEditor/Inc/MikdashRuntime/UHT'
    report = {
        'status': 'offline_check',
        'targetMapExists': map_file.exists(),
        'targetMapSha256': sha256_of(map_file) if map_file.exists() else None,
        'timeOfDayHeaderExists': header.exists(),
        'weatherHeaderExists': weather_header.exists(),
        'pluginDllExists': dll.exists(),
        'pluginDllModified': datetime.fromtimestamp(dll.stat().st_mtime, timezone.utc).isoformat() if dll.exists() else None,
        'uhtHasTimeOfDay': (uht / 'MikdashTimeOfDay.generated.h').exists(),
        'uhtHasWeather': (uht / 'MikdashWeather.generated.h').exists(),
        'liveEditorProcesses': editor_processes(),
    }
    if map_file.exists():
        report['targetMapMatchesLastKnown'] = report['targetMapSha256'] == spec['lastKnownMapSha256']
    for key in ('timeOfDay', 'weather'):
        for field in ('label', 'tag', 'settings'):
            if field not in spec['actors'][key]:
                problems.append('spec actors.%s.%s missing' % (key, field))
    if not report['uhtHasTimeOfDay']:
        problems.append('UHT has not generated MikdashTimeOfDay: rebuild MikdashRuntime before the commandlet run')
    if header.exists() and dll.exists() and header.stat().st_mtime > dll.stat().st_mtime:
        problems.append('MikdashTimeOfDay.h is newer than the plugin DLL: rebuild before the commandlet run')
    if weather_header.exists() and not report['uhtHasWeather']:
        report['weatherWillBeOmitted'] = True
    report['problems'] = problems
    return report


# --------------------------------------------------------------------------
# Engine-side helpers
# --------------------------------------------------------------------------

def _plain(value):
    """Reduce an unreal value to JSON-safe plain data. Structs of unknown shape become
    their string form under a marker so they are never compared numerically."""
    try:
        import unreal as ue
    except ImportError:  # pragma: no cover
        return value
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, ue.Name):
        return str(value)
    if isinstance(value, ue.LinearColor):
        return [value.r, value.g, value.b, value.a]
    if isinstance(value, ue.Color):
        return [value.r, value.g, value.b, value.a]
    if isinstance(value, ue.Vector):
        return [value.x, value.y, value.z]
    if isinstance(value, ue.Rotator):
        return [value.pitch, value.yaw, value.roll]
    if isinstance(value, ue.Object):
        return value.get_path_name()
    if isinstance(value, ue.EnumBase):
        return str(value).split(':')[0].strip('<').strip()
    if isinstance(value, (list, tuple)) or type(value).__name__ == 'Array':
        return [_plain(v) for v in value]
    text = str(value)
    if text.startswith('<Struct'):
        return {'$struct': text.split('(')[0].strip()}
    return text


def _component_props(component, names):
    out = {}
    for name in names:
        try:
            out[name] = _plain(component.get_editor_property(name))
        except Exception as error:  # noqa: BLE001
            out[name] = {'unavailable': str(error)[:160]}
    return out


class Placement:
    def __init__(self, ue, spec):
        self.ue = ue
        self.spec = spec
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.world = None
        self.receipt = {}
        self.receipt_path = None

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    # -- inventory -----------------------------------------------------------

    def find_existing(self):
        ue = self.ue
        found = {'DirectionalLight': [], 'SkyLight': [], 'SkyAtmosphere': [], 'VolumetricCloud': [],
                 'ExponentialHeightFog': [], 'PostProcessVolume': []}
        classes = {'DirectionalLight': ue.DirectionalLight, 'SkyLight': ue.SkyLight, 'SkyAtmosphere': ue.SkyAtmosphere,
                   'VolumetricCloud': ue.VolumetricCloud, 'ExponentialHeightFog': ue.ExponentialHeightFog,
                   'PostProcessVolume': ue.PostProcessVolume}
        for actor in self.actors.get_all_level_actors():
            for key, cls in classes.items():
                if isinstance(actor, cls):
                    found[key].append(actor)
        return found

    def check_counts(self, found):
        for key, bounds in self.spec['expectedExisting'].items():
            n = len(found[key])
            if n < bounds['min'] or n > bounds['max']:
                raise RuntimeError('Expected %d..%d %s actors, found %d' % (bounds['min'], bounds['max'], key, n))

    def pick_sun(self, found):
        ue = self.ue
        best, best_intensity = None, -1.0
        for actor in found['DirectionalLight']:
            comp = actor.get_component_by_class(ue.DirectionalLightComponent)
            if comp is None:
                continue
            if comp.get_editor_property('atmosphere_sun_light') and comp.get_editor_property('atmosphere_sun_light_index') == 0:
                return actor
            intensity = float(comp.get_editor_property('intensity'))
            if intensity > best_intensity:
                best, best_intensity = actor, intensity
        return best

    def pick_post_process(self, found):
        for actor in found['PostProcessVolume']:
            if actor.get_editor_property('unbound'):
                return actor
        return found['PostProcessVolume'][0] if found['PostProcessVolume'] else None

    def snapshot(self, wired):
        """Every value in spec.recordBeforeAndAfter, keyed by actor label."""
        ue = self.ue
        rec = self.spec['recordBeforeAndAfter']
        snap = {}

        def light_block(actor, comp_cls, keys):
            comp = actor.get_component_by_class(comp_cls)
            block = _component_props(comp, [k for k in keys if k != 'mobility'])
            if 'mobility' in keys:
                block['mobility'] = _plain(comp.get_editor_property('mobility'))
            rot = actor.get_actor_rotation()
            block['actorRotation'] = [rot.pitch, rot.yaw, rot.roll]
            return {'name': actor.get_name(), 'label': actor.get_actor_label(), 'props': block}

        if wired.get('sun'):
            snap['sun'] = light_block(wired['sun'], ue.DirectionalLightComponent, rec['DirectionalLight'])
        if wired.get('skyLight'):
            snap['skyLight'] = light_block(wired['skyLight'], ue.SkyLightComponent, rec['SkyLight'])
        if wired.get('skyAtmosphere'):
            comp = wired['skyAtmosphere'].get_component_by_class(ue.SkyAtmosphereComponent)
            snap['skyAtmosphere'] = {'name': wired['skyAtmosphere'].get_name(), 'label': wired['skyAtmosphere'].get_actor_label(),
                                     'props': _component_props(comp, rec['SkyAtmosphere'])}
        if wired.get('cloud'):
            comp = wired['cloud'].get_component_by_class(ue.VolumetricCloudComponent)
            block = _component_props(comp, rec['VolumetricCloud'])
            params = {'scalars': {}, 'vectors': {}}
            material = comp.get_editor_property('material')
            if material is not None and isinstance(material, ue.MaterialInstanceConstant):
                for name in rec['cloudMaterialScalarParameters']:
                    try:
                        params['scalars'][name] = float(ue.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(material, name))
                    except Exception as error:  # noqa: BLE001
                        params['scalars'][name] = {'unavailable': str(error)[:120]}
                for name in rec['cloudMaterialVectorParameters']:
                    try:
                        params['vectors'][name] = _plain(ue.MaterialEditingLibrary.get_material_instance_vector_parameter_value(material, name))
                    except Exception as error:  # noqa: BLE001
                        params['vectors'][name] = {'unavailable': str(error)[:120]}
            block['materialParameters'] = params
            snap['cloud'] = {'name': wired['cloud'].get_name(), 'label': wired['cloud'].get_actor_label(), 'props': block}
        if wired.get('fog'):
            comp = wired['fog'].get_component_by_class(ue.ExponentialHeightFogComponent)
            snap['fog'] = {'name': wired['fog'].get_name(), 'label': wired['fog'].get_actor_label(),
                           'props': _component_props(comp, rec['ExponentialHeightFog'])}
        if wired.get('postProcess'):
            volume = wired['postProcess']
            settings = volume.get_editor_property('settings')
            snap['postProcess'] = {'name': volume.get_name(), 'label': volume.get_actor_label(),
                                   'settings': _component_props(settings, rec['PostProcessVolumeSettings']),
                                   'overrides': _component_props(settings, rec['PostProcessVolumeOverrides']),
                                   'unbound': bool(volume.get_editor_property('unbound')),
                                   'priority': float(volume.get_editor_property('priority'))}
        return snap

    # -- placement -----------------------------------------------------------

    def resolve_value(self, value):
        ue = self.ue
        if isinstance(value, dict) and '$enum' in value:
            enum_name, member = value['$enum'].split('.')
            enum_type = getattr(ue, enum_name)
            if enum_name == 'MikdashWeather' and not hasattr(enum_type, member):
                # UE Python exports the actor and enum under the same short name.
                cls = ue.load_class(None, '/Script/MikdashRuntime.MikdashWeather')
                enum_type = type(ue.get_default_object(cls).get_editor_property('start_weather'))
            return getattr(enum_type, member)
        return value

    def apply_settings(self, actor, settings, label):
        """Set each property and read it back; mismatches raise with the pair."""
        readback = {}
        for key, raw in settings.items():
            value = self.resolve_value(raw)
            actor.set_editor_property(key, value)
            got = actor.get_editor_property(key)
            readback[key] = _plain(got)
            expect = _plain(value)
            if not relative_close(readback[key], expect, self.spec['verification']['floatRelativeTolerance']):
                raise RuntimeError('%s.%s readback %r != %r' % (label, key, readback[key], expect))
        return readback

    def spawn(self, cls, entry, extra_refs=None):
        ue = self.ue
        loc = ue.Vector(*entry['location'])
        actor = self.actors.spawn_actor_from_class(cls, loc, ue.Rotator(0.0, 0.0, 0.0))
        if actor is None:
            raise RuntimeError('spawn_actor_from_class failed for ' + entry['label'])
        actor.set_actor_label(entry['label'])
        actor.set_folder_path(self.spec['folder'])
        actor.set_editor_property('tags', [ue.Name(entry['tag'])])
        readback = self.apply_settings(actor, entry['settings'], entry['label'])
        refs = {}
        for key, target in (extra_refs or {}).items():
            if target is None:
                continue
            actor.set_editor_property(key, target)
            got = actor.get_editor_property(key)
            if got is None or got.get_name() != target.get_name():
                raise RuntimeError('%s.%s reference readback failed' % (entry['label'], key))
            refs[key] = {'name': target.get_name(), 'label': target.get_actor_label()}
        return actor, readback, refs

    def find_by_label(self, label):
        return [a for a in self.actors.get_all_level_actors() if a.get_actor_label() == label]

    def read_placed(self, actor, settings):
        return {key: _plain(actor.get_editor_property(key)) for key in settings}


def _preset_enum(ue, name):
    return getattr(ue.MikdashTimePreset, name.upper())


# --------------------------------------------------------------------------
# Reviewed-daylight PORT (not a review)
# --------------------------------------------------------------------------
#
# 2026-09-09. The daylight adopted on 8 September -- sun 30,000 lux at 6500 K with
# use_temperature, sky light 1.3, against a 5000 K / 1.0 baseline -- was accepted after
# three real PIE camera comparisons, ALL OF THEM ON MAIN50. release_reviewed_daylight.py
# therefore (correctly) declines to write it anywhere else: validate_preset requires the
# three comparisons to share one mapShaBefore, and that hash is Main50's. That guard is
# right and is NOT weakened or bypassed here -- this module IMPORTS validate_preset and
# calls it, rather than reimplementing or relaxing it.
#
# What this mode does instead is an honest PORT. The candidate is the same daylight rig as
# Main50 (one DirectionalLight, one SkyLight, identical component values); it differs in
# scale, 0.48 vs 0.50 amah, and in what has been placed -- not in its lighting. It was still
# sitting on the exact pre-review baseline the reviewers compared AGAINST. Carrying the two
# adopted numbers across is completing an adopted decision, and shipping the map on the
# superseded 5000 K / 1.0 is the worse outcome. But it is not a review, and the receipt says
# so in words: no PIE comparison has been run on the candidate.
#
# The port refuses unless the target's current values are byte-for-byte the reviewed
# BASELINE. It will not "fix up" a map that is on some third setting -- that would be a new
# lighting decision, and this mode does not make one.
REVIEWED_DAYLIGHT_PORT = {
    'decisionFile': 'SourceAssets/lighting-review/cool-daylight-acceptance-20260908.json',
    'reviewedOnMap': TARGET,
    'reviewedOnMapSha256': '480ea53fd3864b7adcaa14a3cc96419768710b8e33bed0dacd90a3731329f1b0',
    'comparisonReceipts': [
        'SourceAssets/runtime-review/frontend-flight/native-frontend-flight-20260908T165802894653Z.json',
        'SourceAssets/runtime-review/frontend-flight/native-frontend-flight-20260908T170147884224Z.json',
        'SourceAssets/runtime-review/frontend-flight/native-frontend-flight-20260908T170356069458Z.json',
    ],
    'comparisonSubjects': ['mount-paving', 'heikhal', 'kotel-platform-join'],
    'statement': (
        'PORTED, NOT REVIEWED ON THIS MAP. The sun temperature and sky light intensity written '
        'here are the values Shmuel adopted on 2026-09-08 after three PIE camera comparisons '
        '(subjects mount-paving, heikhal and kotel-platform-join) run on '
        '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough at map sha256 480ea53f...f1b0, '
        'recorded in the three native-frontend-flight receipts named in comparisonReceipts and '
        'adopted in cool-daylight-acceptance-20260908.json. NO PIE COMPARISON HAS BEEN RUN ON '
        'THIS MAP. The port is justified by the two maps sharing one daylight rig (a single '
        'DirectionalLight and a single SkyLight) and by this map having been on the exact '
        'pre-review baseline the reviewers compared against; it is not justified by any visual '
        'evidence captured here. Visual acceptance on this map is still pending. '
        'release_reviewed_daylight.py declined this map and was neither weakened nor bypassed: '
        'its validate_preset is imported and called unchanged to derive the numbers below.'),
}

# The label the sun actor carries states its own colour temperature. After the port it
# misreports the value, so it is corrected in the same guarded pass (and on Main50, where the
# value moved on 8 September and the label was never updated).
_LABEL_TEMPERATURE = re.compile(r'(?<![\d.])(\d{3,5})\s*K\b')


def _relabelled_sun(label, temperature_k):
    """The same label with its stated colour temperature corrected, or None if it already
    agrees (or states no temperature at all -- this never invents text)."""
    if not label:
        return None
    wanted = '%d K' % int(round(float(temperature_k)))
    matches = _LABEL_TEMPERATURE.findall(label)
    if not matches:
        return None
    if all(int(m) == int(round(float(temperature_k))) for m in matches):
        return None
    return _LABEL_TEMPERATURE.sub(wanted, label)


def _reviewed_daylight_evidence():
    """Re-check the adoption evidence and return (preset, baseline, proposed, evidence).

    Every hash in the decision file is re-verified, then release_reviewed_daylight's own
    validate_preset() decides -- imported, not copied, so this can never drift from, or
    soften, the policy that script enforces."""
    import importlib.util
    decision_path = ROOT / REVIEWED_DAYLIGHT_PORT['decisionFile']
    decision = json.loads(decision_path.read_text(encoding='utf-8-sig'))
    if decision.get('decision') != 'ADOPT_REVIEWED_DAYLIGHT':
        raise RuntimeError('No visual adoption decision in ' + str(decision_path))
    receipts, files = [], []
    for entry in decision['comparisons']:
        path = Path(entry['file'])
        if sha256_of(path) != entry['sha256']:
            raise RuntimeError('Comparison receipt changed since adoption: %s' % path)
        record = json.loads(path.read_text(encoding='utf-8-sig'))
        if record.get('errors') or not record.get('pieEnded') or not record.get('mapBytesUnchanged'):
            raise RuntimeError('Incomplete or failed comparison: %s' % path)
        receipts.append(record)
        files.append({'file': str(path), 'sha256': entry['sha256'],
                      'subject': record.get('diagnosticSubject'),
                      'mapShaBefore': record.get('mapShaBefore')})
    named = {Path(f['file']).name for f in files}
    if named != {Path(p).name for p in REVIEWED_DAYLIGHT_PORT['comparisonReceipts']}:
        raise RuntimeError('Adoption cites different comparison receipts than this port records')
    reviewed_sha = {f['mapShaBefore'] for f in files}
    if reviewed_sha != {REVIEWED_DAYLIGHT_PORT['reviewedOnMapSha256']}:
        raise RuntimeError('Comparisons were run on %s, not the recorded reviewed map' % reviewed_sha)

    spec_module = importlib.util.spec_from_file_location(
        'release_reviewed_daylight_for_port', ROOT / 'Scripts' / 'release_reviewed_daylight.py')
    module = importlib.util.module_from_spec(spec_module)
    spec_module.loader.exec_module(module)
    preset, baseline, proposed = module.validate_preset(decision, receipts)   # unchanged policy
    evidence = dict(REVIEWED_DAYLIGHT_PORT)
    evidence['decisionSha256'] = sha256_of(decision_path)
    evidence['comparisons'] = files
    evidence['preset'] = preset
    evidence['validatedBy'] = 'release_reviewed_daylight.validate_preset (imported unmodified)'
    return preset, baseline, proposed, evidence


def port_reviewed_daylight(load_target=True, target_name="Candidate48", revert=None, relabel_only=False):
    """Write the adopted daylight onto the target's existing sun and sky light as a PORT.

    Full guard pattern, the release_place_assets.py model: every existing lighting value is
    read into the receipt BEFORE anything is written, the umap is checkpointed under
    ReviewCheckpoints, before/after map hashes are recorded, the level is saved, reopened and
    every written value read back numerically, the rest of the level is compared with the
    shared snapshot rules, and the receipt carries a revert block that this same function
    replays with -SkyToDPortRevert.

    relabel_only=True skips the value write and only corrects the sun actor's label where it
    misstates the temperature the light actually has."""
    import unreal as ue
    spec = load_spec(target_name)
    target = spec['targetMap']
    offline = offline_check(spec)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())

    preset, baseline, proposed, evidence = _reviewed_daylight_evidence()
    revert_record = None
    if revert:
        revert_record = json.loads(Path(revert).read_text(encoding='utf-8'))
        if revert_record.get('map') != target:
            raise RuntimeError('Revert receipt is for %s, not %s' % (revert_record.get('map'), target))
        if not revert_record.get('revert'):
            raise RuntimeError('Revert receipt carries no revert block')

    run = Placement(ue, spec)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before map load; refusing to discard changes')
    if load_target and not run.levels.load_level(target):
        raise RuntimeError('load_level failed for ' + target)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name() if run.world is not None else ''
    if loaded != target:
        raise RuntimeError('Loaded world %s is not %s' % (loaded, target))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before a checkpointed write')

    map_file = disk_path(target, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps']}
    protected_assets = {a: sha256_of(disk_path(a)) for a in spec['protectedAssets'] if disk_path(a).exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    mode = 'relabel' if relabel_only else ('daylight-port-revert' if revert else 'daylight-port')
    run.receipt_path = receipt_folder / ('native-%s-%s-%s.json' % (mode, target_name, stamp))
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))

    found = run.find_existing()
    sun = run.pick_sun(found)
    sky = found['SkyLight'][0] if found['SkyLight'] else None
    if sun is None or sky is None:
        raise RuntimeError('This map has no sun and sky light to port onto')
    if len(found['DirectionalLight']) != 1 or len(found['SkyLight']) != 1:
        raise RuntimeError('Port needs exactly one DirectionalLight and one SkyLight; found %d and %d'
                           % (len(found['DirectionalLight']), len(found['SkyLight'])))
    wired = {'sun': sun, 'skyLight': sky,
             'skyAtmosphere': found['SkyAtmosphere'][0] if found['SkyAtmosphere'] else None,
             'cloud': found['VolumetricCloud'][0] if found['VolumetricCloud'] else None,
             'fog': found['ExponentialHeightFog'][0] if found['ExponentialHeightFog'] else None,
             'postProcess': run.pick_post_process(found)}

    light = sun.get_component_by_class(ue.DirectionalLightComponent)
    skylight = sky.get_component_by_class(ue.SkyLightComponent)

    def daylight_values():
        rot = sun.get_actor_rotation()
        return {'sunIntensity': float(light.get_editor_property('intensity')),
                'temperature': float(light.get_editor_property('temperature')),
                'useTemperature': bool(light.get_editor_property('use_temperature')),
                'rotation': [rot.pitch, rot.yaw, rot.roll],
                'skyIntensity': float(skylight.get_editor_property('intensity'))}

    tol = spec['verification']['floatRelativeTolerance']
    before_values = daylight_values()
    before_lighting = run.snapshot(wired)          # read EVERY recorded value before any write
    before_label = sun.get_actor_label()

    if revert:
        wanted = revert_record['revert']['daylight']
        wanted_label = revert_record['revert'].get('sunLabel')
    elif relabel_only:
        wanted, wanted_label = before_values, _relabelled_sun(before_label, before_values['temperature'])
    else:
        if not relative_close(before_values, baseline, tol):
            raise RuntimeError('This map is not on the reviewed baseline, so the adopted numbers '
                               'cannot simply be carried across: current %r, reviewed baseline %r'
                               % (before_values, baseline))
        wanted = dict(proposed)
        wanted['rotation'] = before_values['rotation']   # the port carries the adopted VALUES only
        wanted_label = _relabelled_sun(before_label, wanted['temperature'])

    run.receipt = {
        'status': 'started', 'stamp': stamp, 'mode': mode, 'map': target, 'targetName': target_name,
        'portStatement': REVIEWED_DAYLIGHT_PORT['statement'],
        'visualAcceptanceOnThisMap': 'PENDING - no PIE comparison has been run on this map',
        'reviewedDaylightEvidence': evidence,
        'reviewedBaseline': baseline, 'reviewedProposed': proposed, 'preset': preset,
        'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == spec['lastKnownMapSha256'],
        'lastKnownMapSha256Provenance': spec.get('lastKnownMapSha256Provenance'),
        'protectedSha256Before': protected, 'protectedAssetSha256Before': protected_assets,
        'specSha256': sha256_of(SPEC_PATH), 'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'sunActor': {'name': sun.get_name(), 'label': before_label},
        'skyLightActor': {'name': sky.get_name(), 'label': sky.get_actor_label()},
        'daylightBefore': before_values, 'daylightWanted': wanted,
        'sunLabelBefore': before_label, 'sunLabelWanted': wanted_label,
        'lightingBefore': before_lighting,
        # enough to undo this pass without the checkpoint
        'revert': {'daylight': before_values, 'sunLabel': before_label},
        'revertCommand': ('-SkyToDPortRevert="%s" -SkyToDTarget=%s' % (run.receipt_path, target_name)),
        'liveEditorProcessesAtStart': editor_processes(),
        'errors': [], 'omissions': {},
    }
    run.write_receipt()

    saved = False
    try:
        # -- checkpoint before any mutation -------------------------------------
        checkpoint = Path(spec['checkpointRoot']) / ('SkyToDPort-%s-%s' % (target_name, stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        external_copied = []
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / target[6:]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / target[6:])
                external_copied.append(str(external))
        run.receipt['checkpoint'] = str(checkpoint)
        run.receipt['oneFilePerActorFoldersCopied'] = external_copied
        run.write_receipt()

        # -- whole-level baseline, shared snapshot rules -------------------------
        helper = _placement_helper()
        map_package = run.world.get_outermost().get_name()
        level_before = [helper.snapshot_row(ue, a, map_package)
                        for a in run.actors.get_all_level_actors() if a is not None]
        run.receipt['levelBaselineActors'] = len(level_before)
        run.receipt['levelBaselineRelaxations'] = helper.baseline_relaxations(level_before)

        # -- write ---------------------------------------------------------------
        written = {}
        for obj in (sun, sky, light, skylight):
            obj.modify(True)
        if not relative_close(before_values['temperature'], wanted['temperature'], tol) or \
                before_values['useTemperature'] != wanted['useTemperature']:
            light.set_editor_property('use_temperature', wanted['useTemperature'])
            light.set_temperature(wanted['temperature'])
            written['sun.temperature'] = wanted['temperature']
        if not relative_close(before_values['sunIntensity'], wanted['sunIntensity'], tol):
            light.set_intensity(wanted['sunIntensity'])
            written['sun.intensity'] = wanted['sunIntensity']
        if not relative_close(before_values['skyIntensity'], wanted['skyIntensity'], tol):
            skylight.set_intensity(wanted['skyIntensity'])
            written['skyLight.intensity'] = wanted['skyIntensity']
        if wanted_label and wanted_label != sun.get_actor_label():
            sun.set_actor_label(wanted_label)
            written['sun.label'] = wanted_label
        run.receipt['written'] = written
        if not written:
            run.receipt['status'] = 'nothing_to_write_map_unchanged'
            run.receipt['note'] = 'Target already carries these values and a correct label.'
            return run.receipt

        after_write = daylight_values()
        if not relative_close(after_write, wanted, tol):
            raise RuntimeError('Pre-save readback %r != wanted %r' % (after_write, wanted))

        # -- nothing else in the level may have moved ---------------------------
        level_mid = [helper.snapshot_row(ue, a, map_package)
                     for a in run.actors.get_all_level_actors() if a is not None]
        unrelated = [d for d in helper.diff_baselines(level_before, level_mid, strict=True)
                     if d['name'] != sun.get_name()]
        if unrelated:
            raise RuntimeError('Unrelated actors changed during the write: %s' % unrelated[:6])
        run.receipt['unrelatedLevelChangesBeforeSave'] = unrelated

        # -- save ---------------------------------------------------------------
        run.receipt['liveEditorProcessesBeforeSave'] = editor_processes()
        if not run.levels.save_current_level():
            if not ue.EditorLoadingAndSavingUtils.save_dirty_packages(True, True):
                raise RuntimeError('save_current_level and save_dirty_packages both returned False. '
                                   'Live UnrealEditor processes: %s' % run.receipt['liveEditorProcessesBeforeSave'])
            run.receipt['saveFallback'] = 'EditorLoadingAndSavingUtils.save_dirty_packages'
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()

        # -- reopen and read back numerically -----------------------------------
        if not run.levels.load_level(target):
            raise RuntimeError('Reopen failed')
        run.world = run.editor.get_editor_world()
        found2 = run.find_existing()
        sun2 = run.pick_sun(found2)
        sky2 = found2['SkyLight'][0] if found2['SkyLight'] else None
        if sun2 is None or sky2 is None:
            raise RuntimeError('Sun or sky light missing after reopen')
        light, skylight, sun, sky = (sun2.get_component_by_class(ue.DirectionalLightComponent),
                                     sky2.get_component_by_class(ue.SkyLightComponent), sun2, sky2)
        after_values = daylight_values()
        run.receipt['daylightAfter'] = after_values
        run.receipt['sunLabelAfter'] = sun2.get_actor_label()
        if not relative_close(after_values, wanted, tol):
            raise RuntimeError('Reopened daylight %r != wanted %r' % (after_values, wanted))
        if wanted_label and sun2.get_actor_label() != wanted_label:
            raise RuntimeError('Reopened sun label %r != %r' % (sun2.get_actor_label(), wanted_label))

        wired2 = dict(wired, sun=sun2, skyLight=sky2,
                      skyAtmosphere=found2['SkyAtmosphere'][0] if found2['SkyAtmosphere'] else None,
                      cloud=found2['VolumetricCloud'][0] if found2['VolumetricCloud'] else None,
                      fog=found2['ExponentialHeightFog'][0] if found2['ExponentialHeightFog'] else None,
                      postProcess=run.pick_post_process(found2))
        after_lighting = run.snapshot(wired2)
        run.receipt['lightingAfter'] = after_lighting
        delta = _delta(before_lighting, after_lighting, tol)
        intended = {'sun.intensity', 'sun.temperature', 'sun.use_temperature', 'skyLight.intensity'}
        unintended = {k: v for k, v in delta.items() if k not in intended}
        run.receipt['lightingDelta'] = delta
        run.receipt['unintendedLightingDelta'] = unintended
        if unintended:
            raise RuntimeError('Lighting values changed that this port never wrote: %s' % list(unintended)[:8])

        level_after = [helper.snapshot_row(ue, a, map_package)
                       for a in run.actors.get_all_level_actors() if a is not None]
        reopened_unrelated = [d for d in helper.diff_baselines(level_before, level_after, strict=True)
                              if d['name'] != sun2.get_name()]
        run.receipt['unrelatedLevelChangesAfterReopen'] = reopened_unrelated
        if reopened_unrelated:
            raise RuntimeError('Unrelated actors differ after reopen: %s' % reopened_unrelated[:6])

        reviewed = spec.get('reviewedDaylight', {})
        run.receipt['reviewedDaylightAgreementAfter'] = {
            '%s.%s' % (key, prop): {'reviewed': expect,
                                    'now': after_lighting.get(key, {}).get('props', {}).get(prop),
                                    'ok': relative_close(after_lighting.get(key, {}).get('props', {}).get(prop), expect, tol)}
            for section, key in (('DirectionalLight', 'sun'), ('SkyLight', 'skyLight'), ('ExponentialHeightFog', 'fog'))
            for prop, expect in reviewed.get(section, {}).items()}
        run.receipt['status'] = (
            'sun_label_corrected_saved_reopened' if relabel_only else
            'reviewed_daylight_reverted_saved_reopened' if revert else
            'reviewed_daylight_PORTED_from_main50_review_saved_reopened_visual_acceptance_on_this_map_pending')
        return run.receipt
    except Exception as error:
        run.receipt['errors'].append({'stage': mode, 'error': repr(error)})
        changed = sha256_of(map_file) != map_sha_before
        run.receipt['status'] = ('failed_after_save_checkpoint_available'
                                 if saved or run.receipt.get('mapSaved') or changed
                                 else 'failed_before_save_map_unchanged')
        try:
            run.receipt['liveEditorProcessesAtFailure'] = editor_processes()
        except Exception as inventory_error:  # noqa: BLE001
            run.receipt['processInventoryError'] = repr(inventory_error)
        raise
    finally:
        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapBytesChanged'] = run.receipt['mapSha256After'] != map_sha_before
        run.receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(m, 'umap')) == v for m, v in protected.items())
        run.receipt['protectedAssetsUnchanged'] = all(sha256_of(disk_path(a)) == v for a, v in protected_assets.items())
        protection_failed = not (run.receipt['protectedMapsUnchanged'] and run.receipt['protectedAssetsUnchanged'])
        if protection_failed:
            run.receipt['status'] = 'failed_protected_files_changed_checkpoint_available'
            run.receipt['errors'].append({'stage': 'final_protection', 'error': 'Protected map or asset bytes changed'})
        run.write_receipt()
        if protection_failed:
            raise RuntimeError('Protected map or asset bytes changed; see sky receipt')


def _placement_helper():
    """release_place_assets.py, loaded by path: the shared before/after snapshot rules."""
    import importlib.util
    module_spec = importlib.util.spec_from_file_location(
        'release_place_assets_for_sky', ROOT / 'Scripts' / 'release_place_assets.py')
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    for name in ('snapshot_row', 'diff_baselines', 'baseline_relaxations'):
        if not hasattr(module, name):
            raise RuntimeError('release_place_assets.py lacks ' + name)
    return module


def verify(load_target=True, target_name="Main50"):
    """Read-only confirmation that the sky/time-of-day pass is still present and intact on
    the CURRENT map, after other passes have saved over it. Loads the target itself (a
    -run=pythonscript commandlet starts with no map loaded), reads every placed setting,
    every reference and every recorded lighting value, checks the reviewed daylight, writes
    a receipt and saves nothing. Mutates no actor and never calls save."""
    import unreal as ue
    spec = load_spec(target_name)
    target = spec['targetMap']
    offline = offline_check(spec)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())

    run = Placement(ue, spec)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; refusing to read during play')
    if load_target:
        if not run.levels.load_level(target):
            raise RuntimeError('load_level failed for ' + target)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name() if run.world is not None else ''
    if loaded != target:
        raise RuntimeError('Loaded world %s is not %s' % (loaded, target))

    map_file = disk_path(target, 'umap')
    map_sha_before = sha256_of(map_file)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    run.receipt_path = receipt_folder / ('native-verify-' + target_name + '-' + stamp + '.json')
    run.receipt = {'status': 'started', 'stamp': stamp, 'mode': 'verify', 'map': target,
                   'targetName': target_name, 'mapFile': str(map_file),
                   'mapSha256Before': map_sha_before,
                   'mapMatchesLastKnownSha256': map_sha_before == spec['lastKnownMapSha256'],
                   'lastKnownMapSha256Provenance': spec.get('lastKnownMapSha256Provenance'),
                   'specSha256': sha256_of(SPEC_PATH), 'offlineCheck': offline,
                   'engineVersion': ue.SystemLibrary.get_engine_version(),
                   'errors': [], 'problems': []}
    run.write_receipt()

    tol = spec['verification']['floatRelativeTolerance']
    try:
        found = run.find_existing()
        wired = {'sun': run.pick_sun(found),
                 'skyLight': found['SkyLight'][0] if found['SkyLight'] else None,
                 'skyAtmosphere': found['SkyAtmosphere'][0] if found['SkyAtmosphere'] else None,
                 'cloud': found['VolumetricCloud'][0] if found['VolumetricCloud'] else None,
                 'fog': found['ExponentialHeightFog'][0] if found['ExponentialHeightFog'] else None,
                 'postProcess': run.pick_post_process(found)}
        current = run.snapshot(wired)
        run.receipt['wired'] = {k: (v.get_actor_label() if v else None) for k, v in wired.items()}
        run.receipt['lighting'] = current

        for key, entry in (('timeOfDay', spec['actors']['timeOfDay']),
                           ('weather', spec['actors']['weather'])):
            matches = run.find_by_label(entry['label'])
            block = {'label': entry['label'], 'count': len(matches)}
            if len(matches) == 1:
                block['settings'] = run.read_placed(matches[0], entry['settings'])
                block['mismatches'] = sorted(
                    k for k, raw in entry['settings'].items()
                    if not relative_close(block['settings'][k], _plain(run.resolve_value(raw)), tol))
                if block['mismatches']:
                    run.receipt['problems'].append('%s settings differ: %s' % (key, block['mismatches']))
            elif key == 'timeOfDay':
                run.receipt['problems'].append('timeOfDay actor count %d (expected 1)' % len(matches))
            run.receipt['present_' + key] = block

        reviewed = spec.get('reviewedDaylight', {})
        agreement, diverged = {}, []
        for section, snapshot_key in (('DirectionalLight', 'sun'), ('SkyLight', 'skyLight'),
                                      ('ExponentialHeightFog', 'fog')):
            for prop, expect in reviewed.get(section, {}).items():
                now = current.get(snapshot_key, {}).get('props', {}).get(prop)
                ok = relative_close(now, expect, tol)
                agreement['%s.%s' % (snapshot_key, prop)] = {'reviewed': expect, 'now': now, 'ok': ok}
                if not ok:
                    diverged.append('%s.%s' % (snapshot_key, prop))
        run.receipt['reviewedDaylight'] = {'source': reviewed.get('provenance'),
                                           'agreement': agreement, 'diverged': sorted(diverged)}
        run.receipt['status'] = ('sky_tod_verified_present_reviewed_daylight_intact'
                                 if not run.receipt['problems'] and not diverged else
                                 'sky_tod_verified_with_findings')
        return run.receipt
    except Exception as error:
        run.receipt['errors'].append({'stage': 'verify', 'error': repr(error)})
        run.receipt['status'] = 'verify_failed'
        raise
    finally:
        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapBytesChanged'] = run.receipt['mapSha256After'] != map_sha_before
        if run.receipt['mapBytesChanged']:
            run.receipt['errors'].append({'stage': 'verify', 'error': 'read-only pass changed map bytes'})
        run.write_receipt()


def place(load_target=True, bake=None, revert=None, target_name="Main50"):
    """Run the guarded placement. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    spec = load_spec(target_name)
    target = spec['targetMap']
    if target_name == 'Candidate48' and (bake is not None or revert is not None):
        raise RuntimeError('Candidate port is placement-only; preserve its existing lighting, no bake/revert')
    if target_name == 'Candidate48' and sha256_of(disk_path(target, 'umap')) != CANDIDATE_SHA:
        raise RuntimeError('Candidate differs from reviewed24resident checkpoint; refresh evidence before port')
    offline = offline_check(spec)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    if bake is not None and bake not in PRESET_NAMES:
        raise RuntimeError('Unknown -SkyToDBake preset %r; valid: %s' % (bake, PRESET_NAMES))

    run = Placement(ue, spec)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before map load; refusing to discard changes')
    if load_target:
        if not run.levels.load_level(target):
            raise RuntimeError('load_level failed for ' + target)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name() if run.world is not None else ''
    if loaded != target:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, target))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed placement')

    classes = spec['compiledClasses']
    tod_cls = getattr(ue, classes['timeOfDay']['python'], None) or ue.load_class(None, classes['timeOfDay']['path'])
    if tod_cls is None:
        raise RuntimeError('unreal.%s is missing; rebuild MikdashRuntime before running this' % classes['timeOfDay']['python'])
    weather_cls = getattr(ue, classes['weather']['python'], None)
    if weather_cls is None:
        try:
            weather_cls = ue.load_class(None, classes['weather']['path'])
        except Exception:  # noqa: BLE001
            weather_cls = None

    map_file = disk_path(target, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps']}
    protected_assets = {a: sha256_of(disk_path(a)) for a in spec['protectedAssets'] if disk_path(a).exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    prefix = 'native-revert-' if revert else spec['receiptPrefix']
    run.receipt_path = receipt_folder / (prefix + stamp + '.json')
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))
    run.receipt = {
        'status': 'started',
        'stamp': stamp,
        'map': target,
        'targetName': target_name,
        'targetMetadata': {'reviewedInputSha256': spec['lastKnownMapSha256'], 'fixedArchitectureOriginCm': [-6200,0,0] if target_name == 'Candidate48' else None, 'geometryMutation': False},
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == spec['lastKnownMapSha256'],
        'protectedSha256Before': protected,
        'protectedAssetSha256Before': protected_assets,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'offlineCheck': offline,
        'switches': {'bake': bake, 'revert': revert},
        'liveEditorProcessesAtStart': editor_processes(),
        'weatherClassAvailable': weather_cls is not None,
        'errors': [],
        'omissions': {},
    }
    run.write_receipt()

    saved = False
    try:
        if target_name == 'Candidate48':
            descriptors = [a for a in run.actors.get_all_level_actors()
                           if a.get_actor_label() == 'RELEASE_SceneUnits_Selected48_V1']
            if len(descriptors) != 1:
                raise RuntimeError('Expected exactly one reviewed Selected48 descriptor')
            descriptor = descriptors[0]
            pivot = descriptor.get_editor_property('fixed_architecture_origin_cm')
            revision = descriptor.get_editor_property('coordinate_revision')
            if (int(descriptor.get_editor_property('descriptor_schema_version')) != 1
                    or int(revision.value) != 1
                    or str(descriptor.get_editor_property('scene_revision')) != 'Selected48.v1'
                    or [pivot.x,pivot.y,pivot.z] != [-6200,0,0]):
                raise RuntimeError('Candidate descriptor differs from reviewed schema/revision/pivot')
            run.receipt['candidateDescriptorVerified'] = True
        # -- inventory and BEFORE snapshot (nothing has been touched yet) -------
        found = run.find_existing()
        run.check_counts(found)
        wired = {
            'sun': run.pick_sun(found),
            'skyLight': found['SkyLight'][0] if found['SkyLight'] else None,
            'skyAtmosphere': found['SkyAtmosphere'][0] if found['SkyAtmosphere'] else None,
            'cloud': found['VolumetricCloud'][0] if found['VolumetricCloud'] else None,
            'fog': found['ExponentialHeightFog'][0] if found['ExponentialHeightFog'] else None,
            'postProcess': run.pick_post_process(found),
        }
        run.receipt['existingActors'] = {k: [{'name': a.get_name(), 'label': a.get_actor_label()} for a in v] for k, v in found.items()}
        run.receipt['wired'] = {k: (v.get_actor_label() if v else None) for k, v in wired.items()}
        before = run.snapshot(wired)
        run.receipt['before'] = before
        if target_name == 'Candidate48':
            # Preserve THIS map's existing tune, not main's later cooler daylight.
            tune = spec['authoredTuneThatMustSurvive']
            for section, snapshot_key in (('ExponentialHeightFog','fog'),('SkyLight','skyLight')):
                tune[section] = {k: before[snapshot_key]['props'][k] for k in tune[section]}
            run.receipt['candidateTunePreserved'] = tune
        run.write_receipt()

        tod_entry = spec['actors']['timeOfDay']
        weather_entry = spec['actors']['weather']

        if not revert and (run.find_by_label(tod_entry['label']) or run.find_by_label(weather_entry['label'])):
            raise RuntimeError('RELEASE_Sky* actors already present; refusing to duplicate (use -SkyToDRevert first)')
        for actor in run.actors.get_all_level_actors():
            if not revert and (isinstance(actor, tod_cls) or (weather_cls is not None and isinstance(actor, weather_cls))):
                raise RuntimeError('An actor of the time-of-day/weather class already exists: ' + actor.get_actor_label())

        # -- checkpoint ----------------------------------------------------------
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        external_copied = []
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / target[6:]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / target[6:])
                external_copied.append(str(external))
        run.receipt['checkpoint'] = str(checkpoint)
        run.receipt['oneFilePerActorFoldersCopied'] = external_copied
        run.write_receipt()

        if revert:
            return _revert(run, wired, before, Path(revert), map_file, protected, protected_assets, map_sha_before)

        # -- place -------------------------------------------------------------
        refs = {'sun_light': wired['sun'], 'sky_light': wired['skyLight'], 'sky_atmosphere': wired['skyAtmosphere'],
                'volumetric_cloud': wired['cloud'], 'height_fog': wired['fog'], 'post_process_volume': wired['postProcess']}
        expected_ref_labels = {key: actor.get_actor_label() if actor else None for key, actor in refs.items()}
        tod_actor, tod_readback, tod_refs = run.spawn(tod_cls, tod_entry, refs)
        run.receipt['placed'] = {'timeOfDay': {'label': tod_entry['label'], 'settings': tod_readback, 'references': tod_refs}}

        # Astronomy readout for the receipt: the placed actor's own maths for the spec date.
        astro = {}
        try:
            for name in PRESET_NAMES:
                astro[name + 'Hours'] = float(tod_actor.get_preset_hours(_preset_enum(ue, name)))
            astro['timeZoneOffsetHours'] = float(tod_actor.get_time_zone_offset_hours())
        except Exception as error:  # noqa: BLE001
            astro['unavailable'] = repr(error)
        run.receipt['placed']['timeOfDay']['astronomy'] = astro

        if weather_cls is not None:
            weather_actor, weather_readback, weather_refs = run.spawn(weather_cls, weather_entry, {'time_of_day': tod_actor})
            run.receipt['placed']['weather'] = {'label': weather_entry['label'], 'settings': weather_readback, 'references': weather_refs}
        else:
            run.receipt['omissions']['weather'] = {
                'reason': 'unreal.MikdashWeather is not in the loaded MikdashRuntime binary; rebuild and re-run to add it',
                'evidence': {'uhtHasWeather': offline.get('uhtHasWeather'), 'pluginDllModified': offline.get('pluginDllModified')}}
        run.write_receipt()

        # -- optional bake -----------------------------------------------------
        if bake:
            bake_record = {'preset': bake}
            hours = float(tod_actor.get_preset_hours(_preset_enum(ue, bake)))
            bake_record['hours'] = hours
            # Never let a bake put a transient moon light or a dynamic cloud material into
            # the saved map.
            tod_actor.set_editor_property('drive_moon', False)
            tod_actor.set_editor_property('drive_clouds', False)
            tod_actor.set_editor_property('spawn_moon_light_if_missing', False)
            tod_actor.set_editor_property('time_of_day_hours', hours)
            tod_actor.bind_scene_actors()
            tod_actor.apply_now()
            bake_record['describe'] = str(tod_actor.describe_state())
            bake_record['sunAltitudeDeg'] = float(tod_actor.get_sun_altitude_degrees())
            bake_record['sunAzimuthDeg'] = float(tod_actor.get_sun_azimuth_degrees())
            # Restore the flags and the frozen start state exactly as the spec says.
            for key in ('drive_moon', 'drive_clouds', 'spawn_moon_light_if_missing', 'time_of_day_hours'):
                if key in tod_entry['settings']:
                    tod_actor.set_editor_property(key, run.resolve_value(tod_entry['settings'][key]))
                elif key != 'time_of_day_hours':
                    tod_actor.set_editor_property(key, True)
            after_bake = run.snapshot(wired)
            bake_record['after'] = after_bake
            bake_record['delta'] = _delta(before, after_bake, spec['verification']['floatRelativeTolerance'])
            run.receipt['bake'] = bake_record
            run.write_receipt()

        # -- pre-save proof that the default path touched nothing ----------------
        pre_save = run.snapshot(wired)
        untouched_delta = _delta(before, pre_save, spec['verification']['floatRelativeTolerance'])
        run.receipt['existingActorDeltaBeforeSave'] = untouched_delta
        if not bake and untouched_delta:
            raise RuntimeError('Default mode changed existing lighting values before save: %s' % list(untouched_delta)[:8])

        # -- save ----------------------------------------------------------------
        run.receipt['liveEditorProcessesBeforeSave'] = editor_processes()
        if not run.levels.save_current_level():
            pkg = run.world.get_outermost()
            if not ue.EditorLoadingAndSavingUtils.save_packages([pkg], False):
                raise RuntimeError('save_current_level and save_packages both returned False. Live UnrealEditor processes: %s'
                                   % run.receipt['liveEditorProcessesBeforeSave'])
            run.receipt['saveFallback'] = 'EditorLoadingAndSavingUtils.save_packages'
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()

        # -- reopen and read back ---------------------------------------------------
        if not run.levels.load_level(target):
            raise RuntimeError('Reopen failed')
        run.world = run.editor.get_editor_world()
        found2 = run.find_existing()
        wired2 = {
            'sun': run.pick_sun(found2),
            'skyLight': found2['SkyLight'][0] if found2['SkyLight'] else None,
            'skyAtmosphere': found2['SkyAtmosphere'][0] if found2['SkyAtmosphere'] else None,
            'cloud': found2['VolumetricCloud'][0] if found2['VolumetricCloud'] else None,
            'fog': found2['ExponentialHeightFog'][0] if found2['ExponentialHeightFog'] else None,
            'postProcess': run.pick_post_process(found2),
        }
        after = run.snapshot(wired2)
        run.receipt['after'] = after
        run.receipt['existingActorDeltaAfterReopen'] = _delta(before, after, spec['verification']['floatRelativeTolerance'])
        if not bake and run.receipt['existingActorDeltaAfterReopen']:
            raise RuntimeError('Existing lighting differs after reopen in default mode: %s'
                               % list(run.receipt['existingActorDeltaAfterReopen'])[:8])

        # Authored tune assertion.
        tune = spec['authoredTuneThatMustSurvive']
        tol = tune['floatRelativeTolerance']
        tune_ok, tune_report = True, {}
        fog_props = after.get('fog', {}).get('props', {})
        for key, expect in tune['ExponentialHeightFog'].items():
            got = fog_props.get(key)
            ok = relative_close(got, expect, tol)
            tune_report['fog.' + key] = {'expected': expect, 'got': got, 'ok': ok}
            tune_ok &= ok
        sky_props = after.get('skyLight', {}).get('props', {})
        for key, expect in tune['SkyLight'].items():
            got = sky_props.get(key)
            ok = (str(got).endswith(expect) if isinstance(expect, str) else got == expect)
            tune_report['skyLight.' + key] = {'expected': expect, 'got': got, 'ok': ok}
            tune_ok &= ok
        run.receipt['authoredTuneReadback'] = tune_report
        twilight_bake = bake in ('dawn', 'sunrise', 'sunset', 'dusk', 'night')
        if not tune_ok and not twilight_bake:
            raise RuntimeError('Authored fog/skylight tune not preserved: %s' % {k: v for k, v in tune_report.items() if not v['ok']})
        run.receipt['authoredTunePreserved'] = tune_ok

        # -- reviewed daylight ------------------------------------------------------
        # The daylight Shmuel adopted (sun 6500 K / 30,000 lux, sky light 1.3, fog
        # 0.0015 / 0.15 / 8000, volumetric fog off) is honoured but NOT re-written here:
        # this pass reads every existing lighting value before it touches anything, so it
        # stays reversible. The rule is therefore "this pass must not move it". A value that
        # already disagreed before the pass is recorded as a pre-existing divergence, not
        # blamed on this run; a bake is allowed to differ where the preset row deliberately
        # does, and the delta is recorded rather than asserted away.
        reviewed = spec.get('reviewedDaylight', {})
        agreement, broken_here, pre_existing = {}, [], []
        for section, snapshot_key in (('DirectionalLight', 'sun'), ('SkyLight', 'skyLight'),
                                      ('ExponentialHeightFog', 'fog')):
            for key, expect in reviewed.get(section, {}).items():
                was = before.get(snapshot_key, {}).get('props', {}).get(key)
                now = after.get(snapshot_key, {}).get('props', {}).get(key)
                ok_before = relative_close(was, expect, tol)
                ok_after = relative_close(now, expect, tol)
                field = '%s.%s' % (snapshot_key, key)
                agreement[field] = {'reviewed': expect, 'before': was, 'after': now,
                                    'agreedBefore': ok_before, 'agreedAfter': ok_after}
                if ok_before and not ok_after:
                    broken_here.append(field)
                elif not ok_before:
                    pre_existing.append(field)
        bake_may_differ = bake is not None and reviewed.get('bakeMayDifferSections', [])
        run.receipt['reviewedDaylight'] = {
            'source': reviewed.get('provenance'),
            'agreement': agreement,
            'preExistingDivergence': sorted(pre_existing),
            'movedByThisPass': sorted(broken_here),
            'bakeExemptionApplied': bool(bake_may_differ),
            'rule': ('this pass never writes an existing lighting value in default mode; a '
                     'reviewed value that agreed before the pass must still agree after it'),
        }
        if broken_here and not bake:
            raise RuntimeError('This pass moved the reviewed daylight: %s' % broken_here)
        run.write_receipt()

        readback = {}
        matches = run.find_by_label(tod_entry['label'])
        if len(matches) != 1 or not isinstance(matches[0], tod_cls):
            raise RuntimeError('Reopened time-of-day actor count %d' % len(matches))
        readback['timeOfDay'] = run.read_placed(matches[0], tod_entry['settings'])
        for key, raw in tod_entry['settings'].items():
            if not relative_close(readback['timeOfDay'][key], _plain(run.resolve_value(raw)), tol):
                raise RuntimeError('Reopened timeOfDay.%s = %r, expected %r' % (key, readback['timeOfDay'][key], _plain(run.resolve_value(raw))))
        readback['timeOfDayReferences'] = {}
        for key in refs:
            ref = matches[0].get_editor_property(key)
            readback['timeOfDayReferences'][key] = ref.get_actor_label() if ref else None
            if readback['timeOfDayReferences'][key] != expected_ref_labels[key]:
                raise RuntimeError('Reopened reference %s lost' % key)
        if 'weather' in run.receipt['placed']:
            wm = run.find_by_label(weather_entry['label'])
            if len(wm) != 1 or not isinstance(wm[0], weather_cls):
                raise RuntimeError('Reopened weather actor count %d' % len(wm))
            readback['weather'] = run.read_placed(wm[0], weather_entry['settings'])
            for key, raw in weather_entry['settings'].items():
                if not relative_close(readback['weather'][key], _plain(run.resolve_value(raw)), tol):
                    raise RuntimeError('Reopened weather.%s = %r' % (key, readback['weather'][key]))
            link = wm[0].get_editor_property('time_of_day')
            readback['weatherTimeOfDayReference'] = link.get_actor_label() if link else None
            if link is None or link.get_actor_label() != tod_entry['label']:
                raise RuntimeError('Weather actor lost its time-of-day reference on reopen')
        run.receipt['reopenedReadback'] = readback
        run.receipt['status'] = ('sky_tod_placed_baked_%s_saved_reopened_visual_review_pending' % bake) if bake \
            else 'sky_tod_placed_saved_reopened_existing_lighting_unchanged_visual_review_pending'
        return run.receipt
    except Exception as error:
        run.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        changed = sha256_of(map_file) != map_sha_before
        run.receipt['status'] = 'failed_after_save_checkpoint_available' if saved or run.receipt.get('mapSaved') or changed else 'failed_before_save_map_unchanged'
        try:
            run.receipt['liveEditorProcessesAtFailure'] = editor_processes()
        except Exception as inventory_error:
            run.receipt['processInventoryError'] = repr(inventory_error)
        raise
    finally:
        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapBytesChanged'] = run.receipt['mapSha256After'] != map_sha_before
        run.receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(m, 'umap')) == v for m, v in protected.items())
        run.receipt['protectedAssetsUnchanged'] = all(sha256_of(disk_path(a)) == v for a, v in protected_assets.items())
        protection_failed = not (run.receipt['protectedMapsUnchanged'] and run.receipt['protectedAssetsUnchanged'])
        if protection_failed:
            run.receipt['status'] = 'failed_protected_files_changed_checkpoint_available'
            run.receipt['errors'].append({'stage': 'final_protection', 'error': 'Protected map or asset bytes changed'})
        run.write_receipt()
        if protection_failed:
            raise RuntimeError('Protected map or asset bytes changed; see sky receipt')


def _delta(before, after, tolerance):
    """Flat {section.key: {before, after}} of every recorded value that differs."""
    out = {}
    for section, block in before.items():
        other = after.get(section, {})
        for group in ('props', 'settings', 'overrides'):
            if group not in block:
                continue
            for key, value in block[group].items():
                got = other.get(group, {}).get(key)
                if isinstance(value, dict) and ('$struct' in value or 'unavailable' in value):
                    continue
                if not relative_close(got, value, tolerance):
                    out['%s.%s' % (section, key)] = {'before': value, 'after': got}
    return out


SETTERS = {
    # property -> setter on the component (None means use set_editor_property)
    'sun': {'intensity', 'use_temperature', 'temperature', 'light_source_angle', 'volumetric_scattering_intensity'},
    'skyLight': {'intensity'},
    'skyAtmosphere': {'aerial_pespective_view_distance_scale', 'mie_scattering_scale', 'sky_luminance_factor'},
    'fog': {'fog_density', 'fog_height_falloff', 'start_distance', 'fog_max_opacity', 'enable_volumetric_fog',
            'sky_atmosphere_ambient_contribution_color_scale', 'directional_inscattering_luminance'},
}


def _revert(run, wired, before_now, receipt_path, map_file, protected, protected_assets, map_sha_before):
    """Write every 'before' value of an earlier receipt back and destroy the placed actors."""
    ue = run.ue
    earlier = json.loads(receipt_path.read_text(encoding='utf-8'))
    if earlier.get('map') != run.spec['targetMap']:
        raise RuntimeError('Revert receipt belongs to another map')
    source = earlier.get('before') or {}
    tol = run.spec['verification']['floatRelativeTolerance']
    run.receipt['revertSource'] = str(receipt_path)
    written = {}
    comp_cls = {'sun': ue.DirectionalLightComponent, 'skyLight': ue.SkyLightComponent,
                'skyAtmosphere': ue.SkyAtmosphereComponent, 'fog': ue.ExponentialHeightFogComponent}
    for section, keys in SETTERS.items():
        actor = wired.get(section)
        block = source.get(section, {}).get('props', {})
        if actor is None or not block:
            continue
        comp = actor.get_component_by_class(comp_cls[section])
        for key in keys:
            if key not in block or isinstance(block[key], dict):
                continue
            value = block[key]
            if isinstance(value, list) and len(value) == 4:
                value = ue.LinearColor(*value)
            comp.set_editor_property(key, value)
            got = _plain(comp.get_editor_property(key))
            written['%s.%s' % (section, key)] = {'wrote': block[key], 'read': got, 'ok': relative_close(got, block[key], tol)}
        if section == 'sun' and 'actorRotation' in block:
            actor.set_actor_rotation(ue.Rotator(*block['actorRotation']), False)
            rot = actor.get_actor_rotation()
            written['sun.actorRotation'] = {'wrote': block['actorRotation'], 'read': [rot.pitch, rot.yaw, rot.roll]}
    pp = wired.get('postProcess')
    pp_block = source.get('postProcess', {}).get('settings', {})
    if pp is not None and pp_block:
        settings = pp.get_editor_property('settings')
        for key in ('auto_exposure_bias', 'auto_exposure_min_brightness', 'auto_exposure_max_brightness'):
            if key in pp_block and not isinstance(pp_block[key], dict):
                settings.set_editor_property(key, pp_block[key])
                written['postProcess.' + key] = {'wrote': pp_block[key], 'read': _plain(settings.get_editor_property(key))}
        pp.set_editor_property('settings', settings)
    run.receipt['revertWritten'] = written

    destroyed = []
    for label in (run.spec['actors']['timeOfDay']['label'], run.spec['actors']['weather']['label']):
        for actor in run.find_by_label(label):
            if run.actors.destroy_actor(actor):
                destroyed.append(label)
    run.receipt['destroyed'] = destroyed

    run.receipt['liveEditorProcessesBeforeSave'] = editor_processes()
    if not run.levels.save_current_level():
        raise RuntimeError('save_current_level returned False during revert; live editors: %s' % run.receipt['liveEditorProcessesBeforeSave'])
    run.receipt['mapSaved'] = True
    run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
    run.write_receipt()
    if not run.levels.load_level(run.spec['targetMap']):
        raise RuntimeError('Reopen failed after revert')
    run.world = run.editor.get_editor_world()
    found = run.find_existing()
    wired2 = {'sun': run.pick_sun(found), 'skyLight': found['SkyLight'][0], 'skyAtmosphere': found['SkyAtmosphere'][0],
              'cloud': found['VolumetricCloud'][0], 'fog': found['ExponentialHeightFog'][0], 'postProcess': run.pick_post_process(found)}
    after = run.snapshot(wired2)
    run.receipt['after'] = after
    run.receipt['deltaFromRevertSource'] = _delta(source, after, tol)
    run.receipt['status'] = 'sky_tod_reverted_saved_reopened' if not run.receipt['deltaFromRevertSource'] else 'sky_tod_reverted_with_residual_delta'
    return run.receipt


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
    """True only when the engine itself is executing this file as a script."""
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_sky_tod.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    bake, revert = None, None
    verify_only = False
    port_daylight = False
    relabel_only = False
    port_revert = None
    target_name = "Main50"
    for token in command_line.split():
        low = token.lower()
        if low in ('-skytodverify', '-skytodverify=1', '-skytodverify=true'):
            verify_only = True
            continue
        if low in ('-skytodport', '-skytodport=1', '-skytodport=true'):
            port_daylight = True
            continue
        if low in ('-skytodfixsunlabel', '-skytodrelabel'):
            relabel_only = True
            continue
        if low.startswith('-skytodportrevert='):
            port_revert = token.split('=', 1)[1].strip('"')
            continue
        if low.startswith('-skytodtarget=') or low.startswith('-target='):
            target_name = _normalise_target(token.split('=', 1)[1].strip('"'))
        elif low.startswith('-skytodbake='):
            bake = token.split('=', 1)[1].strip('"').lower()
            if bake in ('', 'none'):
                bake = None
        elif low.startswith('-skytodrevert='):
            revert = token.split('=', 1)[1].strip('"')
    try:
        if verify_only:
            receipt = verify(load_target=True, target_name=target_name)
        elif port_daylight or relabel_only or port_revert:
            receipt = port_reviewed_daylight(load_target=True, target_name=target_name,
                                             revert=port_revert, relabel_only=relabel_only)
        else:
            receipt = place(load_target=True, bake=bake, revert=revert, target_name=target_name)
        ue.log('release_sky_tod: %s receipt %s' % (receipt['status'], receipt.get('stamp')))
        ue.log('release_sky_tod: receipt file %s' % receipt.get('stamp'))
    except Exception as error:
        ue.log_error('release_sky_tod failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line.lower() and '-run=pythonscript' not in command_line.lower():
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        args = [arg.split('=', 1)[1] for arg in sys.argv[1:]
                if arg.lower().startswith('-skytodtarget=') or arg.lower().startswith('-target=')]
        print(json.dumps(offline_check(load_spec(_normalise_target(args[0]) if args else 'Main50')), indent=2))
elif _invoked_as_native_script():
    _main()

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
  -SkyToDBake=<dawn|sunrise|morning|midday|afternoon|sunset|dusk|night>
        Also write that one preset into the existing lighting actors for editor preview.
        Default: none. Without it NO existing actor property is written by this pass.
  -SkyToDRevert=<path to a native-place receipt>
        Write every recorded "before" value back, destroy the placed actors, save, reopen.

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
  * The receipt JSON is written at start and again in finally, preserving partial state.

UE 5.8 pitfalls this script is built around:
  * MaterialEditingLibrary instance getters are used read-only here (the pass never edits
    a material asset); the cloud parameters are recorded from the assigned instance.
  * Property setters are verified by reading the value back; return values are ignored.
"""
import hashlib
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_sky_tod.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'

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


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def editor_processes():
    """Zombie check. A 'failed' save is often a leftover editor holding the file."""
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UnrealEditor*.exe', '/NH'],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception as error:  # noqa: BLE001
        return ['tasklist_failed: ' + repr(error)]
    return [line.strip() for line in out.splitlines() if line.strip() and 'UnrealEditor' in line]


def relative_close(a, b, tolerance):
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
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
            return getattr(getattr(ue, enum_name), member)
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


def place(load_target=True, bake=None, revert=None):
    """Run the guarded placement. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    spec = load_spec()
    offline = offline_check(spec)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    if bake is not None and bake not in PRESET_NAMES:
        raise RuntimeError('Unknown -SkyToDBake preset %r; valid: %s' % (bake, PRESET_NAMES))

    run = Placement(ue, spec)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target:
        if not run.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
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

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}
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
        'map': TARGET,
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
        run.write_receipt()

        tod_entry = spec['actors']['timeOfDay']
        weather_entry = spec['actors']['weather']

        if revert:
            return _revert(run, wired, before, Path(revert), map_file, protected, protected_assets, map_sha_before)

        if run.find_by_label(tod_entry['label']) or run.find_by_label(weather_entry['label']):
            raise RuntimeError('RELEASE_Sky* actors already present; refusing to duplicate (use -SkyToDRevert first)')
        for actor in run.actors.get_all_level_actors():
            if isinstance(actor, tod_cls) or (weather_cls is not None and isinstance(actor, weather_cls)):
                raise RuntimeError('An actor of the time-of-day/weather class already exists: ' + actor.get_actor_label())

        # -- checkpoint ----------------------------------------------------------
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
        run.receipt['checkpoint'] = str(checkpoint)
        run.receipt['oneFilePerActorFoldersCopied'] = external_copied
        run.write_receipt()

        # -- place -------------------------------------------------------------
        refs = {'sun_light': wired['sun'], 'sky_light': wired['skyLight'], 'sky_atmosphere': wired['skyAtmosphere'],
                'volumetric_cloud': wired['cloud'], 'height_fog': wired['fog'], 'post_process_volume': wired['postProcess']}
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
        if not run.levels.load_level(TARGET):
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
            if refs[key] is not None and (ref is None or ref.get_actor_label() != refs[key].get_actor_label()):
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
        run.receipt['status'] = 'failed_after_save_checkpoint_available' if saved else 'failed_before_save_map_unchanged'
        run.receipt['liveEditorProcessesAtFailure'] = editor_processes()
        raise
    finally:
        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapBytesChanged'] = run.receipt['mapSha256After'] != map_sha_before
        run.receipt['protectedMapsUnchanged'] = all(sha256_of(disk_path(m, 'umap')) == v for m, v in protected.items())
        run.receipt['protectedAssetsUnchanged'] = all(sha256_of(disk_path(a)) == v for a, v in protected_assets.items())
        run.write_receipt()


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
    if not run.levels.load_level(TARGET):
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
    for token in command_line.split():
        low = token.lower()
        if low.startswith('-skytodbake='):
            bake = token.split('=', 1)[1].strip('"').lower()
            if bake in ('', 'none'):
                bake = None
        elif low.startswith('-skytodrevert='):
            revert = token.split('=', 1)[1].strip('"')
    try:
        receipt = place(load_target=True, bake=bake, revert=revert)
        ue.log('release_sky_tod: %s receipt %s' % (receipt['status'], receipt.get('stamp')))
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
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()

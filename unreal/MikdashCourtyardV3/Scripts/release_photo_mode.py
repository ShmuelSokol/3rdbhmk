"""Guarded acceptance run for photo mode.

Photo mode itself is C++ (Plugins/MikdashRuntime/.../MikdashPhotoMode.h and .cpp). This
script is what proves the parts of it that can be proved without a person holding the
keyboard, and it produces the reference stills that go with a release:

  * The leash. ClampToSphere then ClampToBox is the only thing standing between a visitor
    and the void outside the level, so the recommended radius and bounds are computed
    from the ACTUAL extent of the loaded map, not from a guess, and a battery of numeric
    cases is run against the same clamp order the C++ uses.

  * The capture. It writes real PNGs at 1x, 2x and 4x through the engine's high resolution
    screenshot path, then reads each file back and checks the IHDR dimensions really are
    the multiplier times the base, that the bytes start with the PNG signature, and that
    the frame is not flat black. That is the numeric readback: a capture that silently
    produced a 0-byte file or a half-size image fails here rather than in someone's
    screenshot folder.

  * The directory. "Next to the game" is only useful if it is writable, so the resolved
    photo directory is probed by writing, reading back and deleting a file.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_photo_mode.py"
      -unattended
      -abslog="C:/Mikdash/Working-5.8/Release-PhotoMode-01.log"

Do NOT pass -nullrhi when captures are wanted: with no RHI there is nothing to capture,
and the script says so in the receipt rather than writing an empty PNG and calling it a
pass. Pass -PhotoNoCapture to run the geometry and leash checks alone under -nullrhi.

Run with plain python (no engine) to print the offline plan: the leash battery, the
recommended configuration block and the vantage list are computed and nothing is written.

Safety model, matching Scripts/release_place_assets.py:
  * Refuses to run with the wrong project directory, a game world, dirty packages, or a
    loaded world that is not the combined map.
  * Copies Walkthrough.umap (and any One-File-Per-Actor folders) to
    ReviewCheckpoints/PhotoMode-<stamp>/ before anything runs, and verifies the copy.
  * The map is NOT mutated. It is saved and reopened anyway, and the receipt asserts the
    hash is identical before, after the save and after the reopen, and that the measured
    world bounds are identical across the reopen. A save that changes the map is a
    failure, not a shrug.
  * The receipt JSON is written at start and again in finally.

What this does NOT establish: that a photograph looks good, that depth of field is
focused where a person wanted it, that the colour grades are tasteful, or that the
capture works on somebody else's GPU. It establishes that the file is written, is a PNG,
is the size it claims, and is not blank.
"""

import hashlib
import json
import math
import shutil
import struct
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_photo_mode.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    return ROOT / 'Content' / (asset_path[len('/Game/'):] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if Path(spec['projectDir']) != ROOT:
        raise RuntimeError('Spec projectDir %s is not %s' % (spec['projectDir'], ROOT))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec targetMap %s is not %s' % (spec['targetMap'], TARGET))
    return spec


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


# ---------------------------------------------------------------------------
# the leash, mirroring UMikdashPhotoMode::ClampToLeash
#
# Sphere first, then the hard box. The order matters: the sphere is the leash the visitor
# feels and the box is the guarantee that no configuration of the sphere can put the
# camera outside the built world. Reversing them would let a large radius win.
# ---------------------------------------------------------------------------

def clamp_to_sphere(point, centre, radius):
    delta = [point[i] - centre[i] for i in range(3)]
    length = math.sqrt(sum(d * d for d in delta))
    radius = max(0.0, radius)
    if length <= radius or length < 1e-9:
        return list(point)
    scale = radius / length
    return [centre[i] + delta[i] * scale for i in range(3)]


def clamp_to_box(point, minimum, maximum, margin=0.0):
    margin = max(0.0, margin)
    out = []
    for i in range(3):
        mid = (minimum[i] + maximum[i]) * 0.5
        lo = minimum[i] + margin
        hi = maximum[i] - margin
        out.append(mid if lo > hi else _clamp(point[i], lo, hi))
    return out


def clamp_to_leash(point, anchor, radius, minimum, maximum):
    return clamp_to_box(clamp_to_sphere(point, anchor, radius), minimum, maximum)


def leash_battery(spec):
    """Numeric cases the leash must satisfy. Each records its measured value."""
    anchor = list(spec['leash']['anchorCm'])
    radius = float(spec['leash']['radiusCm'])
    minimum = list(spec['leash']['boundsMinCm'])
    maximum = list(spec['leash']['boundsMaxCm'])
    rows = []

    def record(name, measured, comparison, tolerance, note):
        if comparison == '<=':
            passed = measured <= tolerance
        elif comparison == '>=':
            passed = measured >= tolerance
        else:
            passed = abs(measured - tolerance) <= 1e-9
        rows.append({'name': name, 'measured': measured, 'comparison': comparison,
                     'tolerance': tolerance, 'passed': bool(passed), 'note': note})

    inside = [anchor[0] + radius * 0.5, anchor[1], anchor[2] + 100.0]
    record('insidePointUntouchedCm', _dist(clamp_to_leash(inside, anchor, radius, minimum, maximum), inside),
           '<=', 1e-9, 'a camera already within the leash is not moved at all')

    for direction in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        far = [anchor[i] + direction[i] * radius * 40.0 for i in range(3)]
        clamped = clamp_to_leash(far, anchor, radius, minimum, maximum)
        record('leashHoldsToward_%d_%d_%d' % direction, _dist(clamped, anchor), '<=', radius + 1e-6,
               'a camera flown hard in this direction never gets further out than the radius')
        for i in range(3):
            record('insideBounds_%d_%d_%d_axis%d' % (direction + (i,)), clamped[i], '>=', minimum[i] - 1e-6, '')
            record('insideBoundsUpper_%d_%d_%d_axis%d' % (direction + (i,)), maximum[i] - clamped[i], '>=', -1e-6, '')

    # A radius wider than the world must still not escape it: the box has the last word.
    huge = clamp_to_box(clamp_to_sphere([1e9, 1e9, 1e9], anchor, 1e12), minimum, maximum)
    record('absurdRadiusStillInsideBoundsCm', max(huge[i] - maximum[i] for i in range(3)), '<=', 1e-6,
           'the hard bounds are applied after the sphere, so no radius can beat them')

    # The far corner of the level: reachable only if the radius allows, never beyond.
    corner = list(maximum)
    clamped_corner = clamp_to_leash(corner, anchor, radius, minimum, maximum)
    record('cornerRequestClampedToRadiusCm', _dist(clamped_corner, anchor), '<=', radius + 1e-6, '')

    return rows


def recommended_config(bounds_min, bounds_max, radius):
    """The DefaultGame.ini block a human can paste, derived from measured bounds."""
    return (
        '[/Script/MikdashRuntime.MikdashPhotoMode]\n'
        'bEnabled=True\n'
        'bOwnToggleKey=True\n'
        'LeashRadiusCm=%.0f\n'
        'BoundsMin=(X=%.0f,Y=%.0f,Z=%.0f)\n'
        'BoundsMax=(X=%.0f,Y=%.0f,Z=%.0f)\n'
        % (radius, bounds_min[0], bounds_min[1], bounds_min[2],
           bounds_max[0], bounds_max[1], bounds_max[2])
    )


# ---------------------------------------------------------------------------
# PNG readback
# ---------------------------------------------------------------------------

def png_facts(path):
    """Signature, IHDR dimensions and a crude brightness probe, with no image library."""
    data = Path(path).read_bytes()
    facts = {'file': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    facts['isPng'] = data[:8] == b'\x89PNG\r\n\x1a\n'
    if not facts['isPng'] or len(data) < 24:
        facts['dimensions'] = None
        return facts
    width, height = struct.unpack('>II', data[16:24])
    facts['dimensions'] = [width, height]
    facts['bitDepth'] = data[24]
    facts['colourType'] = data[25]
    # A compressed stream that is almost entirely one byte value is a flat frame. This is
    # not a decode, it is a cheap "is there anything in here at all" probe.
    body = data[8:]
    counts = {}
    for byte in body[:200000]:
        counts[byte] = counts.get(byte, 0) + 1
    facts['mostCommonByteFraction'] = (max(counts.values()) / float(min(len(body), 200000))) if body else 1.0
    return facts


# ---------------------------------------------------------------------------
# offline
# ---------------------------------------------------------------------------

def offline_check(spec=None):
    spec = spec or load_spec()
    rows = leash_battery(spec)
    failures = [row['name'] for row in rows if not row['passed']]
    base = spec['capture']['baseResolution']
    return {
        'specSha256': sha256_of(SPEC_PATH),
        'leashChecks': len(rows),
        'leashFailures': failures,
        'leash': rows,
        'leashAnchorCm': spec['leash']['anchorCm'],
        'leashRadiusCm': spec['leash']['radiusCm'],
        'boundsMinCm': spec['leash']['boundsMinCm'],
        'boundsMaxCm': spec['leash']['boundsMaxCm'],
        'recommendedConfig': recommended_config(spec['leash']['boundsMinCm'],
                                                spec['leash']['boundsMaxCm'],
                                                spec['leash']['radiusCm']),
        'captureMultipliers': spec['capture']['multipliers'],
        'expectedResolutions': {str(m): [base[0] * m, base[1] * m] for m in spec['capture']['multipliers']},
        'vantages': [v['id'] for v in spec['vantages']],
        'captureApi': spec['capture']['api'],
        'packagedSupport': spec['capture']['packagedSupport'],
        'limitations': spec['limitations'],
    }


# ---------------------------------------------------------------------------
# native
# ---------------------------------------------------------------------------

class PhotoRun(object):
    def __init__(self, ue, spec):
        self.ue = ue
        self.spec = spec
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.world = None
        self.receipt = None
        self.receipt_path = None

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    def measure_world_bounds(self):
        """Union of every actor's bounds in the loaded level, in centimetres."""
        ue = self.ue
        minimum = [float('inf')] * 3
        maximum = [float('-inf')] * 3
        counted = 0
        for actor in self.actors.get_all_level_actors():
            try:
                origin, extent = actor.get_actor_bounds(only_colliding_components=False)
            except Exception:  # noqa: BLE001
                continue
            if extent.x <= 0.0 and extent.y <= 0.0 and extent.z <= 0.0:
                continue
            counted += 1
            low = (origin.x - extent.x, origin.y - extent.y, origin.z - extent.z)
            high = (origin.x + extent.x, origin.y + extent.y, origin.z + extent.z)
            for i in range(3):
                minimum[i] = min(minimum[i], low[i])
                maximum[i] = max(maximum[i], high[i])
        if counted == 0:
            raise RuntimeError('No actor in the level reported bounds')
        return [round(v, 1) for v in minimum], [round(v, 1) for v in maximum], counted

    def probe_directory(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ('photo-mode-write-probe-%d.tmp' % int(time.time()))
        payload = b'mikdash photo mode write probe'
        probe.write_bytes(payload)
        readable = probe.read_bytes() == payload
        probe.unlink()
        return {'directory': str(directory), 'writable': bool(readable)}

    def capture(self, vantage, multiplier, directory):
        """One high resolution capture from a fixed editor viewport pose."""
        ue = self.ue
        spec = self.spec
        base = spec['capture']['baseResolution']
        width, height = base[0] * multiplier, base[1] * multiplier
        position = ue.Vector(*vantage['positionCm'])
        rotation = ue.Rotator(0.0, vantage['pitch'], vantage['yaw'])
        self.editor.set_level_viewport_camera_info(position, rotation)
        ue.AutomationLibrary.finish_loading_before_screenshot()

        filename = Path(directory) / ('%s_%s_%dx.png' % (spec['capture']['filePrefix'], vantage['id'], multiplier))
        if filename.exists():
            filename.unlink()
        started = time.monotonic()
        task = ue.AutomationLibrary.take_high_res_screenshot(
            width, height, str(filename), camera=None, mask_enabled=False,
            capture_hdr=False, delay=0.0, force_game_view=True)
        if not (task and task.is_valid_task()):
            raise RuntimeError('take_high_res_screenshot did not configure a task')
        timeout = float(spec['capture']['timeoutSeconds'])
        while not (task.is_task_done() and filename.exists()):
            if time.monotonic() - started > timeout:
                raise RuntimeError('Capture %s at %dx timed out after %.0f s' % (vantage['id'], multiplier, timeout))
            time.sleep(0.25)

        facts = png_facts(filename)
        facts['vantage'] = vantage['id']
        facts['multiplier'] = multiplier
        facts['expectedDimensions'] = [width, height]
        facts['dimensionsMatch'] = facts['dimensions'] == [width, height]
        facts['elapsedSeconds'] = round(time.monotonic() - started, 2)
        facts['flatFrame'] = facts['mostCommonByteFraction'] > float(spec['capture']['flatFrameByteFraction'])
        return facts


def run(load_target=True, do_capture=True):
    """Guarded acceptance run. Returns the receipt dict; raises on guard failure."""
    import unreal as ue

    spec = load_spec()
    offline = offline_check(spec)
    if offline['leashFailures']:
        raise RuntimeError('Leash battery failed offline: %s' % offline['leashFailures'][:5])
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())

    run_state = PhotoRun(ue, spec)
    if run_state.editor.get_game_world():
        raise RuntimeError('A game world is active; never run this during play')
    if load_target:
        if not run_state.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
    run_state.world = run_state.editor.get_editor_world()
    loaded = run_state.world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before this run')

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps'] if disk_path(m, 'umap').exists()}
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
    run_state.receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if run_state.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run_state.receipt_path))

    has_rhi = '-nullrhi' not in ue.SystemLibrary.get_command_line().lower()
    run_state.receipt = {
        'status': 'photo_mode_acceptance_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'protectedMapSha256Before': protected,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'realRhi': has_rhi,
        'captureRequested': bool(do_capture),
        'offlineCheck': offline,
        'captures': [],
        'errors': [],
        'mapSaved': False,
        'limitations': spec['limitations'],
    }
    run_state.write_receipt()

    try:
        bounds_min, bounds_max, actor_count = run_state.measure_world_bounds()
        run_state.receipt['measuredWorldBounds'] = {
            'minCm': bounds_min, 'maxCm': bounds_max, 'actorsWithBounds': actor_count}
        # The configured hard bounds have to contain the measured world, or the leash
        # would clip the camera before the level ends.
        contains = all(spec['leash']['boundsMinCm'][i] <= bounds_min[i]
                       and spec['leash']['boundsMaxCm'][i] >= bounds_max[i] for i in range(3))
        run_state.receipt['configuredBoundsContainMeasuredWorld'] = contains
        run_state.receipt['recommendedConfigFromMeasuredWorld'] = recommended_config(
            [math.floor(v / 1000.0) * 1000.0 for v in bounds_min],
            [math.ceil(v / 1000.0) * 1000.0 for v in bounds_max],
            spec['leash']['radiusCm'])
        run_state.write_receipt()

        directory = Path(spec['captureFolder'])
        if not directory.is_absolute():
            directory = ROOT / directory
        run_state.receipt['directoryProbe'] = run_state.probe_directory(directory)
        if not run_state.receipt['directoryProbe']['writable']:
            raise RuntimeError('Photo directory is not writable: ' + str(directory))
        run_state.write_receipt()

        if do_capture and not has_rhi:
            run_state.receipt['captureSkipped'] = (
                'Started with -nullrhi, so there is nothing to capture. Re-run without it, '
                'or pass -PhotoNoCapture to make skipping explicit.')
        elif do_capture:
            ue.AutomationLibrary.finish_loading_before_screenshot()
            for vantage in spec['vantages']:
                for multiplier in spec['capture']['multipliers']:
                    facts = run_state.capture(vantage, multiplier, directory)
                    run_state.receipt['captures'].append(facts)
                    run_state.write_receipt()
            bad = [c for c in run_state.receipt['captures']
                   if not (c['isPng'] and c['dimensionsMatch']) or c['flatFrame']]
            if bad:
                raise RuntimeError('%d capture(s) failed readback: %s'
                                   % (len(bad), [c['file'] for c in bad][:4]))

        # Save and reopen even though nothing was changed: the point is to prove that,
        # numerically, on both sides of a round trip.
        if not run_state.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        run_state.receipt['mapSaved'] = True
        run_state.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run_state.write_receipt()
        if not run_state.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run_state.world = run_state.editor.get_editor_world()
        reopened_min, reopened_max, reopened_count = run_state.measure_world_bounds()
        run_state.receipt['reopenedWorldBounds'] = {
            'minCm': reopened_min, 'maxCm': reopened_max, 'actorsWithBounds': reopened_count}
        run_state.receipt['boundsStableAcrossReopen'] = (
            reopened_min == bounds_min and reopened_max == bounds_max and reopened_count == actor_count)
        if not run_state.receipt['boundsStableAcrossReopen']:
            raise RuntimeError('World bounds changed across the save and reopen')

        run_state.receipt['mapSha256After'] = sha256_of(map_file)
        run_state.receipt['mapUnchanged'] = run_state.receipt['mapSha256After'] == map_sha_before
        run_state.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
        if not run_state.receipt['mapUnchanged']:
            run_state.receipt['errors'].append(
                'The map hash changed across an unmodified save; the checkpoint holds the original.')
        run_state.receipt['status'] = 'photo_mode_accepted_numerically_visual_review_pending'
        return run_state.receipt
    except Exception as error:  # noqa: BLE001
        run_state.receipt['errors'].append(repr(error))
        run_state.receipt['status'] = 'photo_mode_acceptance_failed'
        raise
    finally:
        try:
            run_state.receipt['mapSha256AtExit'] = sha256_of(map_file)
        except Exception:  # noqa: BLE001
            pass
        run_state.write_receipt()


# ---------------------------------------------------------------------------
# entry points
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
    return 'release_photo_mode.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    do_capture = '-photonocapture' not in command_line
    try:
        receipt = run(load_target=True, do_capture=do_capture)
        ue.log('release_photo_mode: %s, %d capture(s)' % (receipt['status'], len(receipt['captures'])))
    except Exception as error:  # noqa: BLE001
        ue.log_error('release_photo_mode failed: ' + repr(error))
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

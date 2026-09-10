"""The two maps this project places into, and the similarity that carries Main50-authored
coordinates onto the 48 cm candidate.

WHY THIS FILE EXISTS
--------------------
Three release passes -- gate security, surface wear and vegetation -- hardcoded

    TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'

with no way to say otherwise, and none of them contained the Amah48Candidate path anywhere.
Candidate48 is the configured GameDefaultMap and the ONLY map cooked into the download, so
everything those three passes have ever produced exists only on the map that does not ship.
`release_reviewed_daylight.py` had already solved the switch and `release_water.py` had already
solved the geometry; this is those two answers in one place so the next pass does not have to
solve either again.

THE 48 cm TRAP, IN ONE PARAGRAPH
--------------------------------
Candidate48 is NOT Main50 renamed. `release_amah48_candidate.py` rescaled all 2,633 architecture
actors by RATIO = 48/50 = 0.96 about the world origin, and `release_aron_alignment.py` then
translated the temple actors by (-248, 0, 0) so the Aron sits over the rock. The composition is

    p_candidate = 0.96 * p_main50 + (-248, 0, 0)

so anything spawned on Candidate48 at Main50's authored coordinates is 4 per cent oversized and
2.48 m east of where it belongs. The FutureMountV1 TERRAIN and the metric city were NOT rescaled:
they stand at identical coordinates on both maps. So the right transform depends on what the
thing being placed stands on -- architecture (transform it) or ground (leave it alone) -- and
neither answer is ever taken on trust: `prove_placement()` MEASURES the transform off the live
level, against SourceAssets/architecture-manifest.json, before anything is spawned.

NOTHING HERE IMPORTS unreal. Every function is pure, so the whole file is exercisable under
scripts/verify.py on a machine with no engine, and `python Scripts/map_targets.py --tests`
runs its own arithmetic self-test.
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')

MAIN50_MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
CANDIDATE48_MAP = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'

# The authoring frame. Every plan, spec and manifest in this project holds Main50 coordinates,
# because that is the map they were generated against; Candidate48 placement is those numbers
# carried through the similarity below.
AUTHORING_TARGET = 'main50'

TARGETS = {
    'candidate48': {
        'key': 'Candidate48',
        'flag': '-Candidate48',
        'map': CANDIDATE48_MAP,
        'amahCm': 48.0,
        'role': ('the configured GameDefaultMap and the COOK map: the only map in the build the '
                 'user downloads.'),
        'uniformScale': 0.96,
        'translationCm': [-248.0, 0.0, 0.0],
        'derivation': (
            'Scripts/release_amah48_candidate.py rescaled all 2,633 architecture actors by '
            'RATIO = 48/50 = 0.96 about the world origin; Scripts/release_aron_alignment.py then '
            'translated the 2,917 temple actors by deltaCm [-248, 0, 0]. The composition is '
            'p_candidate = 0.96 * p_main50 + (-248, 0, 0). Evidence: '
            'SourceAssets/scale-review/amah48-candidate-20260908T144034771385Z.json and '
            'SourceAssets/scale-review/aron-alignment-release-Candidate48-20260908T220353291775Z.json. '
            'It is measured off the level itself by prove_placement() before anything is spawned.'),
        'groundIsUnscaled': True,
    },
    'main50': {
        'key': 'Main50',
        'flag': '-Main50',
        'map': MAIN50_MAP,
        'amahCm': 50.0,
        'role': 'the legacy 50 cm map every plan and manifest in this project was authored against.',
        'uniformScale': 1.0,
        'translationCm': [0.0, 0.0, 0.0],
        'derivation': 'the authoring frame itself: the identity.',
        'groundIsUnscaled': True,
    },
}


def target_from_command_line(default=AUTHORING_TARGET, argv=None, command_line=None):
    """The target key from -Candidate48 / -Main50 / -Target=Candidate48, DEFAULTING TO MAIN50.

    Exactly the shape release_reviewed_daylight.py settled on, and for its reason: an existing
    invocation that says nothing about a target must keep running against the map it always ran
    against. Retargeting is opt-in, never a side effect of adding the switch.
    """
    tokens = [t.lower() for t in (sys.argv if argv is None else argv)]
    if command_line is None:
        try:
            import unreal as _ue
            command_line = _ue.SystemLibrary.get_command_line()
        except Exception:  # noqa: BLE001 - offline syntax checks have no engine
            command_line = ''
    tokens += [t.lower() for t in (command_line or '').split()]
    for token in tokens:
        token = token.strip('"')
        for key in TARGETS:
            if token in ('-' + key, '--' + key) or token.endswith('=' + key):
                return key
    return default


def target_config(key):
    if key not in TARGETS:
        raise ValueError('Unknown target %r; known targets are %s' % (key, sorted(TARGETS)))
    return TARGETS[key]


def placement_of(key):
    """(uniform scale, translation cm) carrying Main50-authored coordinates onto this target."""
    config = target_config(key)
    return float(config['uniformScale']), [float(v) for v in config['translationCm']]


# --------------------------------------------------------------------------
# Pure geometry
# --------------------------------------------------------------------------

def transform_point(point, scale, translation):
    return [float(point[i]) * scale + translation[i] for i in range(3)]


def transform_box(box, scale, translation):
    """A POSITIVE UNIFORM scale about the origin plus a translation maps an axis-aligned box
    onto an axis-aligned box exactly -- no re-fit, no growth -- which is the whole reason the
    candidate is supported this way rather than by re-exporting geometry at 48 cm."""
    return {'min': transform_point(box['min'], scale, translation),
            'max': transform_point(box['max'], scale, translation)}


def box_error(a, b):
    return max(abs(float(a[key][i]) - float(b[key][i]))
               for key in ('min', 'max') for i in range(3))


def box_contains(box, point, padding_cm=0.0):
    return all(box['min'][i] - padding_cm <= float(point[i]) <= box['max'][i] + padding_cm
               for i in range(3))


ASSET_INDEX_TOKEN = re.compile(r'(SM_\d{4}_.+)$')


def manifest_key_for_asset(asset_name):
    """Reduce a LEVEL mesh asset name to the manifest assetName it was imported from.

    Verbatim from release_water.manifest_key_for_asset and for its reason: the architecture
    importer prefixes every mesh with its import group, so manifest 'SM_0000_architecture_Ulam_
    stair_6' lives in the level as '.../Architecture/architecture_SM_0000_architecture_Ulam_
    stair_6'. An exact-key lookup on the bare assetName matches NOTHING.
    """
    if not asset_name:
        return None
    match = ASSET_INDEX_TOKEN.search(asset_name)
    return match.group(1) if match else asset_name


def architecture_index(root=ROOT, manifest_relative='SourceAssets/architecture-manifest.json'):
    """{manifest key -> entry} for every architecture mesh, plus the manifest itself."""
    manifest = json.loads((Path(root) / manifest_relative).read_text(encoding='utf-8-sig'))
    return {manifest_key_for_asset(e['assetName']): e for e in manifest['meshes']}, manifest


def manifest_entry_for_assets(asset_names, by_key):
    """First manifest entry any of an actor's mesh assets resolves to, or None.

    The object suffix is stripped FIRST. Some callers hand over package paths
    ('/Game/.../architecture_SM_0261_x', release_place_assets._asset_path) and some hand over
    full object paths ('/Game/.../architecture_SM_0261_x.architecture_SM_0261_x',
    release_vegetation._asset_path). Without the strip the second form matches nothing at all,
    because the index token regex is greedy to the end of the string and would swallow the
    repeated name -- the same silent no-match that cost release_water.py a day.
    """
    for asset in asset_names or ():
        name = (asset or '').rsplit('/', 1)[-1].split('.')[0]
        entry = by_key.get(manifest_key_for_asset(name))
        if entry is not None:
            return entry
    return None


def solve_similarity(pairs, minimum_span_cm=50.0):
    """Least-squares (uniform scale, translation) carrying authored points onto live points.

    `pairs` is [(authored_xyz, live_xyz), ...] -- in practice the min and the max corner of every
    architecture actor's AABB, which is 2 points per actor and thousands of points in total.
    Solved PER AXIS and then reconciled, so a map whose axes disagree is caught rather than
    averaged into a plausible-looking single number. Points are only used on an axis where the
    authored spread is wide enough to divide by; a scale is otherwise not observable there.

    This is a MEASUREMENT of the level, independent of anything declared anywhere.
    """
    per_axis = []
    for i in range(3):
        authored = [float(a[i]) for a, _ in pairs]
        live = [float(b[i]) for _, b in pairs]
        if len(authored) < 2:
            per_axis.append(None)
            continue
        mean_a = sum(authored) / len(authored)
        mean_l = sum(live) / len(live)
        variance = sum((a - mean_a) ** 2 for a in authored)
        spread = max(authored) - min(authored)
        if variance <= 0.0 or spread < minimum_span_cm:
            per_axis.append(None)
            continue
        covariance = sum((a - mean_a) * (l - mean_l) for a, l in zip(authored, live))
        scale = covariance / variance
        per_axis.append((scale, mean_l - scale * mean_a))
    observed = [row for row in per_axis if row is not None]
    if not observed:
        raise RuntimeError('No axis of the level carries enough spread to measure a placement')
    scales = [row[0] for row in observed]
    return {
        'perAxis': [None if row is None else [row[0], row[1]] for row in per_axis],
        'uniformScale': sum(scales) / len(scales),
        'scaleSpread': max(scales) - min(scales),
        'translationCm': [0.0 if row is None else row[1] for row in per_axis],
        'points': len(pairs),
    }


def prove_placement(rows, by_key, scale, translation, absolute_tolerance_cm=0.5,
                    span_relative_tolerance=5e-5, minimum_samples=500,
                    minimum_agreeing_fraction=0.99, scale_tolerance=2e-4,
                    translation_tolerance_cm=2.0, report_disagreeing=8):
    """Prove, off the LIVE level, that the target really does sit under (scale, translation).

    `rows` are snapshot rows carrying 'label', 'meshes' (asset paths) and 'bounds' (world AABB
    in cm). Every actor whose mesh resolves to the architecture manifest is compared with its
    manifest bounds carried through the declared placement, IN CENTIMETRES; separately, the
    transform is SOLVED from the same actors and the solution has to agree with what was
    declared. Two independent statements, both required:

      * declared placement predicts the live bounds of essentially every architecture actor;
      * the placement measured from those bounds is the placement that was declared.

    Judgement is on the box error in centimetres, never on a solved per-actor scale: dividing by
    the extent of a 19 cm floor slab turns a sub-millimetre bound difference into a scale error
    of 1e-4. release_water.py refused a run on exactly that mistake on 2026-09-09.
    """
    report = {'declared': {'uniformScale': scale, 'translationCm': list(translation)},
              'sampled': 0, 'agreeing': 0, 'worstBoundsErrorCm': 0.0,
              'disagreeing': [], 'disagreeingCount': 0,
              'method': ('every level actor whose mesh resolves to '
                         'SourceAssets/architecture-manifest.json, compared with its manifest AABB '
                         'carried through the declared placement, per axis, in centimetres; '
                         'allowance %.2f cm + %.1e of the axis span.'
                         % (absolute_tolerance_cm, span_relative_tolerance))}
    pairs = []
    for row in rows:
        entry = manifest_entry_for_assets(row.get('meshes'), by_key)
        if entry is None or not row.get('bounds'):
            continue
        authored = entry['expectedBoundsUnrealCm']
        predicted = transform_box(authored, scale, translation)
        live = row['bounds']
        pairs.append(([authored['min'][i] for i in range(3)], [live['min'][i] for i in range(3)]))
        pairs.append(([authored['max'][i] for i in range(3)], [live['max'][i] for i in range(3)]))
        report['sampled'] += 1
        agrees, worst = True, 0.0
        axes = []
        for i in range(3):
            span = predicted['max'][i] - predicted['min'][i]
            allowance = absolute_tolerance_cm + span_relative_tolerance * abs(span)
            error = max(abs(float(live['min'][i]) - predicted['min'][i]),
                        abs(float(live['max'][i]) - predicted['max'][i]))
            axes.append({'axis': 'XYZ'[i], 'errorCm': round(error, 4),
                         'allowanceCm': round(allowance, 4)})
            worst = max(worst, error)
            agrees = agrees and error <= allowance
        report['worstBoundsErrorCm'] = max(report['worstBoundsErrorCm'], worst)
        if agrees:
            report['agreeing'] += 1
        else:
            report['disagreeingCount'] += 1
            if len(report['disagreeing']) < report_disagreeing:
                report['disagreeing'].append(
                    {'actor': row.get('label'), 'sourceName': entry.get('sourceName'),
                     'boundsErrorCm': round(worst, 4), 'perAxis': axes})
    report['agreeingFraction'] = (report['agreeing'] / report['sampled']) if report['sampled'] else 0.0
    report['worstBoundsErrorCm'] = round(report['worstBoundsErrorCm'], 6)
    if report['sampled'] < minimum_samples:
        raise RuntimeError('Only %d architecture actors resolved to the manifest; the placement '
                           'transform cannot be proved (need %d)'
                           % (report['sampled'], minimum_samples))
    measured = solve_similarity(pairs)
    measured['uniformScale'] = round(measured['uniformScale'], 9)
    measured['scaleSpread'] = round(measured['scaleSpread'], 9)
    measured['translationCm'] = [round(v, 6) for v in measured['translationCm']]
    report['measured'] = measured
    report['scaleErrorFromDeclared'] = round(abs(measured['uniformScale'] - scale), 9)
    report['translationErrorFromDeclaredCm'] = [
        round(abs(measured['translationCm'][i] - translation[i]), 6) for i in range(3)]
    if report['agreeingFraction'] < minimum_agreeing_fraction:
        raise RuntimeError('Only %.4f of %d architecture actors sit under the declared placement '
                           '(scale %s, translation %s); worst bounds error %.3f cm. Measured %s'
                           % (report['agreeingFraction'], report['sampled'], scale, translation,
                              report['worstBoundsErrorCm'], measured))
    if report['scaleErrorFromDeclared'] > scale_tolerance or measured['scaleSpread'] > scale_tolerance:
        raise RuntimeError('The placement MEASURED off the level is scale %.9f (per-axis spread '
                           '%.9f), not the declared %.9f'
                           % (measured['uniformScale'], measured['scaleSpread'], scale))
    if max(report['translationErrorFromDeclaredCm']) > translation_tolerance_cm:
        raise RuntimeError('The placement MEASURED off the level is translation %s cm, not the '
                           'declared %s' % (measured['translationCm'], translation))
    report['status'] = 'placement_proved_against_the_live_level'
    return report


def terrain_fingerprint(rows, prefixes=('SM_JerusalemTerrain_',)):
    """{actor label -> world AABB} for the ground tiles, which are the SAME on both maps.

    SUBSTRING, not startswith: the 256 tiles were imported with a `terrain_` prefix
    normalisation, so the level asset is terrain_SM_JerusalemTerrain_07_07 while the manifest
    calls it SM_JerusalemTerrain_07_07. This is the exclusion rule release_vegetation.py already
    uses, kept identical here on purpose.
    """
    out = {}
    for row in rows:
        names = [n or '' for n in (row.get('meshes') or [])] + [row.get('label') or '']
        if any(token in name for name in names for token in prefixes) and row.get('bounds'):
            out[row['label']] = {'min': [round(float(v), 4) for v in row['bounds']['min']],
                                 'max': [round(float(v), 4) for v in row['bounds']['max']]}
    return out


def compare_fingerprints(a, b):
    """Numeric agreement between two terrain fingerprints; the ground must not have moved."""
    shared = sorted(set(a) & set(b))
    worst, worst_label = 0.0, None
    for label in shared:
        error = box_error(a[label], b[label])
        if error > worst:
            worst, worst_label = error, label
    return {'inFirst': len(a), 'inSecond': len(b), 'matchedLabels': len(shared),
            'onlyInFirst': sorted(set(a) - set(b))[:8], 'onlyInSecond': sorted(set(b) - set(a))[:8],
            'worstBoundsErrorCm': round(worst, 6), 'worstLabel': worst_label}


# --------------------------------------------------------------------------
# Revert: restore a map from the checkpoint a run took before it mutated anything
# --------------------------------------------------------------------------

def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset', root=ROOT):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return Path(root) / 'Content' / (asset_path[6:] + '.' + extension)


def restore_checkpoint(receipt_path, dry_run=False, root=ROOT):
    """Put the map back exactly as the named run found it. OFFLINE -- run with no editor open.

    Every guarded pass in this project copies the .umap (and any One-File-Per-Actor folders) to
    ReviewCheckpoints/<prefix><stamp>/ before it mutates anything, and records both the folder
    and the pre-run SHA-256 in its receipt. This is the other half of that contract: it verifies
    the checkpointed bytes still hash to the receipt's mapSha256Before BEFORE overwriting
    anything, and verifies the restored file hashes to it afterwards. It refuses rather than
    guesses if either check fails.
    """
    receipt_path = Path(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig'))
    target_map = receipt.get('map')
    expected = receipt.get('mapSha256Before')
    checkpoint = Path(receipt['checkpoint'])
    if not target_map or not expected:
        raise RuntimeError('Receipt %s records no map / mapSha256Before to restore to' % receipt_path)
    live = disk_path(target_map, 'umap', root=root)
    source = checkpoint / live.name
    if not source.is_file():
        raise RuntimeError('Checkpointed map missing: ' + str(source))
    source_sha = sha256_of(source)
    if source_sha != expected:
        raise RuntimeError('Checkpoint %s hashes %s, but the receipt says the map was %s before '
                           'the run; refusing to restore bytes nobody recorded'
                           % (source, source_sha, expected))
    report = {'receipt': str(receipt_path), 'map': target_map, 'mapFile': str(live),
              'checkpoint': str(checkpoint), 'checkpointSha256': source_sha,
              'mapSha256Before': sha256_of(live) if live.exists() else None,
              'restoreTargetSha256': expected, 'dryRun': bool(dry_run),
              'externalFoldersRestored': []}
    if dry_run:
        report['status'] = 'revert_dry_run_checkpoint_verified_nothing_written'
        return report
    shutil.copy2(source, live)
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        staged = checkpoint / folder_name / target_map[6:]
        if staged.is_dir():
            destination = Path(root) / 'Content' / folder_name / target_map[6:]
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(staged, destination)
            report['externalFoldersRestored'].append(str(destination))
    report['mapSha256After'] = sha256_of(live)
    if report['mapSha256After'] != expected:
        raise RuntimeError('Restored map hashes %s, expected %s'
                           % (report['mapSha256After'], expected))
    report['status'] = 'reverted_to_checkpoint'
    return report


def revert_from_command_line(argv=None):
    """--revert=<receipt> [--dry-run] parsed off a PLAIN python command line. None if absent."""
    argv = sys.argv if argv is None else argv
    receipt = None
    for index, token in enumerate(argv):
        low = token.lower()
        if low.startswith('--revert='):
            receipt = token.split('=', 1)[1].strip('"')
        elif low == '--revert' and index + 1 < len(argv):
            receipt = argv[index + 1].strip('"')
    if receipt is None:
        return None
    return {'receipt': receipt, 'dryRun': any(t.lower() == '--dry-run' for t in argv)}


# --------------------------------------------------------------------------
# Self-test: the arithmetic, with no engine and no files
# --------------------------------------------------------------------------

def _tests():
    failures = []

    def check(name, condition):
        if not condition:
            failures.append(name)

    check('default target is main50, never candidate', target_from_command_line(argv=['x'], command_line='') == 'main50')
    check('-Candidate48 selects the candidate',
          target_from_command_line(argv=['x', '-Candidate48'], command_line='') == 'candidate48')
    check('-Target=Candidate48 selects the candidate',
          target_from_command_line(argv=['x'], command_line='-run=pythonscript -Target=Candidate48') == 'candidate48')
    check('-Main50 stays on the legacy map',
          target_from_command_line(argv=['x', '-Main50'], command_line='') == 'main50')
    check('an unrelated flag does not retarget',
          target_from_command_line(argv=['x', '-VegetationMaxBatches=40'], command_line='') == 'main50')

    scale, translation = placement_of('candidate48')
    check('candidate placement is 0.96 and -248', scale == 0.96 and translation == [-248.0, 0.0, 0.0])
    check('main50 placement is the identity',
          placement_of('main50') == (1.0, [0.0, 0.0, 0.0]))

    # The Aron: [-6200, 0, 925] authored, [-6200, 0, 888] measured on the candidate after the
    # re-pivot (aron-alignment receipt). 0.96 * -6200 - 248 = -6200 exactly, which is the whole
    # point of the -248: the Aron does not move, everything else closes in around it.
    check('the Aron is the fixed point of the candidate transform',
          abs(transform_point([-6200.0, 0.0, 925.0], scale, translation)[0] + 6200.0) < 1e-9)
    check('925 authored is 888 on the candidate',
          abs(transform_point([-6200.0, 0.0, 925.0], scale, translation)[2] - 888.0) < 1e-9)

    box = {'min': [-1900.0, -775.0, 625.0], 'max': [-1750.0, 775.0, 775.0]}
    moved = transform_box(box, scale, translation)
    check('a box scales about the origin then translates',
          moved['min'] == [-2072.0, -744.0, 600.0] and moved['max'] == [-1928.0, 744.0, 744.0])
    check('a uniform scale preserves box shape exactly',
          abs((moved['max'][1] - moved['min'][1]) - 0.96 * 1550.0) < 1e-9)

    # Solving the transform back out of the transformed boxes must return it exactly.
    authored_boxes = [{'min': [x * 10.0, x * -7.0, x * 3.0],
                       'max': [x * 10.0 + 400.0, x * -7.0 + 250.0, x * 3.0 + 90.0]}
                      for x in range(-60, 61)]
    pairs = []
    for authored in authored_boxes:
        live = transform_box(authored, scale, translation)
        pairs.append((authored['min'], live['min']))
        pairs.append((authored['max'], live['max']))
    solved = solve_similarity(pairs)
    check('the solver recovers 0.96', abs(solved['uniformScale'] - 0.96) < 1e-9)
    check('the solver recovers -248', abs(solved['translationCm'][0] + 248.0) < 1e-6)
    check('the solver recovers a zero Y/Z translation',
          abs(solved['translationCm'][1]) < 1e-6 and abs(solved['translationCm'][2]) < 1e-6)
    check('the solver reports no per-axis disagreement', solved['scaleSpread'] < 1e-9)

    rows = [{'label': 'a%d' % i, 'meshes': ['/Game/X/architecture_SM_%04d_architecture_Thing' % i],
             'bounds': transform_box(b, scale, translation)}
            for i, b in enumerate(authored_boxes)]
    by_key = {'SM_%04d_architecture_Thing' % i: {'assetName': 'SM_%04d_architecture_Thing' % i,
                                                 'sourceName': 'Thing', 'expectedBoundsUnrealCm': b}
              for i, b in enumerate(authored_boxes)}
    proof = prove_placement(rows, by_key, scale, translation, minimum_samples=100)
    check('a level under the declared placement proves', proof['agreeing'] == len(rows))
    check('and its worst bounds error is zero', proof['worstBoundsErrorCm'] < 1e-6)

    # The failure this whole mechanism exists to catch: authored coordinates on the candidate.
    naive = [{'label': r['label'], 'meshes': r['meshes'], 'bounds': authored_boxes[i]}
             for i, r in enumerate(rows)]
    try:
        prove_placement(naive, by_key, scale, translation, minimum_samples=100)
        check('placing at authored coordinates on the candidate is refused', False)
    except RuntimeError:
        pass

    check('an object path resolves to its manifest entry',
          manifest_entry_for_assets(
              ['/Game/MikdashV3/Architecture/architecture_SM_0000_architecture_Thing'
               '.architecture_SM_0000_architecture_Thing'],
              {'SM_0000_architecture_Thing': {'ok': True}}) == {'ok': True})
    check('a package path resolves to the same entry',
          manifest_entry_for_assets(
              ['/Game/MikdashV3/Architecture/architecture_SM_0000_architecture_Thing'],
              {'SM_0000_architecture_Thing': {'ok': True}}) == {'ok': True})
    check('manifest key survives the import prefix',
          manifest_key_for_asset('architecture_SM_0000_architecture_Ulam_stair_6')
          == 'SM_0000_architecture_Ulam_stair_6')
    check('terrain fingerprints compare',
          compare_fingerprints({'t': {'min': [0, 0, 0], 'max': [1, 1, 1]}},
                               {'t': {'min': [0, 0, 0], 'max': [1, 1, 1]}})['worstBoundsErrorCm'] == 0.0)
    return failures


if __name__ == '__main__':
    action = revert_from_command_line()
    if action:
        print(json.dumps(restore_checkpoint(action['receipt'], dry_run=action['dryRun']), indent=2))
    else:
        problems = _tests()
        print(json.dumps({'tests': 'map_targets', 'failures': problems,
                          'status': 'passed' if not problems else 'FAILED'}, indent=2))
        sys.exit(1 if problems else 0)

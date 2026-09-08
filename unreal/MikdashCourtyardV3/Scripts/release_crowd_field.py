"""Guarded native adoption of the instanced crowd: pose meshes, crowd materials, and one
RELEASE_CrowdField actor carrying the authored zones.

Everything numeric comes from Scripts/release_crowd_field.spec.json, which was filled from
SourceAssets/runtime-review/crowd-field/CrowdFigureV1/geometry-manifest.json (frozen OBJ
hashes, canonical bounds, triangle counts) and SourceAssets/runtime-review/crowd-field/
zones.json (polygons, ground planes and densities, each citing the manifest, release spec or
native trace receipt it came from).

What it does, in order:
  1. Offline checks with no engine: frozen OBJ hashes, triangle counts and reflected bounds;
     zones.json hash and internal consistency (simple non-degenerate polygons, no zone wholly
     swallowed by a keep-out, apportionment summing to the crowd count, re-seed segments
     legal, ground planes finite over each zone's own extent).
  2. Guards: right project, no game world, no dirty packages, the FRESH compiled plugin
     (AMikdashCrowdField exists and exposes UpdateBudgetPerFrame), target map untouched by
     any protected-map rule.
  3. Checkpoints the target .umap to <checkpointRoot>/CrowdField-<stamp>/.
  4. Imports the six pose OBJs into /Game/MikdashV3/Runtime/CrowdFieldV1/Meshes through the
     reviewed legacy OBJ adapter path (FbxFactory, the settings release_dove_people_v2.py
     uses), verifies bounds and triangle counts, generates reduction LODs, builds the three
     crowd materials and assigns them by slot name.
  5. Spawns ONE RELEASE_CrowdField actor at identity, writes the zones, keep-outs, meshes and
     every tuning property, builds the editor preview, saves, reopens and reads every written
     value plus the instance count back off the reopened actor.
  6. Writes SourceAssets/runtime-review/crowd-field/native-apply-<stamp>.json at start, on
     failure and in finally.

MATERIALS. Not gold, and not vertex colour. The three materials (robe, skin, wrap) are simple
lit materials whose base colour is a lerp driven by HISM per-instance custom data 1, plus a
phase-driven vertical bob in world position offset driven by custom data 0. Vertex colour was
refused deliberately: this project's own note in create_dove_mesh_v2.py records that FBX-SDK
OBJ reader tolerance for the `v x y z r g b` extension is unverified here, and a silently
dropped colour channel would give a uniformly grey crowd with nothing to show why. Every
setter is read back: this script never trusts a set_editor_property return value, and every
connect call is checked, with the pin name that actually worked recorded in the receipt.

Commandlet invocation (serial; never while another native job is running; fresh -abslog path):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_crowd_field.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-CrowdField-01.log"

Optional engine command-line switches:
  -CrowdImportOnly       import meshes and materials only; no map change.
  -CrowdPlaceOnly        skip the import; the six meshes must already exist (re-verified).
  -CrowdMeshesExist      allow an existing namespace (implies re-verification, not import).
  -CrowdFieldActivate    write ActivateOnBeginPlay = True (default leaves the opt-in False).
  -CrowdCount=<n>        override the CrowdCount property written onto the actor.

Offline (no engine):  python Scripts/release_crowd_field.py --offline-check
"""
import hashlib
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'Scripts' / 'release_crowd_field.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target map differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


# ==========================================================================
# Pure geometry, mirrored from Plugins/MikdashRuntime/Source/MikdashRuntime/Public/
# CrowdFieldMath.h so an illegal zone is caught before the engine is ever started.
# ==========================================================================

def point_in_polygon(points, p):
    if len(points) < 3:
        return False
    inside = False
    j = len(points) - 1
    for i in range(len(points)):
        a, b = points[i], points[j]
        if (a[1] > p[1]) != (b[1] > p[1]):
            denominator = b[1] - a[1]
            if abs(denominator) > 1e-12 and p[0] < a[0] + (b[0] - a[0]) * (p[1] - a[1]) / denominator:
                inside = not inside
        j = i
    return inside


def distance_to_segment(a, b, p):
    abx, aby = b[0] - a[0], b[1] - a[1]
    length_squared = abx * abx + aby * aby
    t = 0.0 if length_squared <= 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * abx + (p[1] - a[1]) * aby) / length_squared))
    dx, dy = p[0] - (a[0] + abx * t), p[1] - (a[1] + aby * t)
    return math.hypot(dx, dy)


def distance_to_edge(points, p):
    return min(distance_to_segment(points[i - 1], points[i], p) for i in range(len(points)))


def in_any_protected(polygons, p, margin):
    for points in polygons:
        if point_in_polygon(points, p) or distance_to_edge(points, p) < margin:
            return True
    return False


def polygon_area(points):
    twice = 0.0
    j = len(points) - 1
    for i in range(len(points)):
        twice += points[j][0] * points[i][1] - points[i][0] * points[j][1]
        j = i
    return abs(twice) * 0.5


def segments_cross(p1, p2, p3, p4):
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    o1, o2, o3, o4 = orient(p1, p2, p3), orient(p1, p2, p4), orient(p3, p4, p1), orient(p3, p4, p2)
    return o1 != o2 and o3 != o4


def polygon_is_simple(points):
    """No two non-adjacent edges may cross. A self-intersecting zone would make the even-odd
    containment test carve holes nobody authored."""
    n = len(points)
    for i in range(n):
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or (i + 1) % n == j:
                continue
            if segments_cross(points[i], points[(i + 1) % n], points[j], points[(j + 1) % n]):
                return False
    return True


def apportion(weights, total):
    """Mirror of MikdashCrowd::ApportionCounts."""
    live = sum(w for w in weights if w > 0)
    if live <= 0 or total <= 0:
        return [0] * len(weights)
    counts = [int(math.floor(total * w / live)) if w > 0 else 0 for w in weights]
    while sum(counts) < total:
        best, best_remainder = -1, -1.0
        for i, w in enumerate(weights):
            if w <= 0:
                continue
            exact = total * w / live
            if counts[i] > math.floor(exact):
                continue
            remainder = exact - math.floor(exact)
            if remainder > best_remainder:
                best_remainder, best = remainder, i
        if best < 0:
            best = next(i for i, w in enumerate(weights) if w > 0)
        counts[best] += 1
    return counts


def parse_obj(path):
    vertices, faces, groups, materials = [], 0, set(), set()
    with open(path, 'r', errors='replace') as handle:
        for line in handle:
            if line.startswith('v '):
                parts = line.split()
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith('f '):
                faces += 1
            elif line.startswith('g '):
                groups.add(line[2:].strip())
            elif line.startswith('usemtl '):
                materials.add(line[7:].strip())
    return vertices, faces, groups, materials


def box_error(a, b):
    return max(abs(a[k][i] - b[k][i]) for k in ('min', 'max') for i in range(3))


def check_zones(spec):
    """Every check that can be made without the engine. Raises on anything that would place a
    figure in the sanctuary, in a wall, or nowhere at all."""
    conf = spec['zones']
    zones_path = ROOT / conf['file']
    if sha(zones_path) != conf['sha256']:
        raise RuntimeError('zones.json changed after the spec was prepared')
    data = json.loads(zones_path.read_text(encoding='utf-8-sig'))
    if data['specVersion'] != conf['specVersionRequired']:
        raise RuntimeError('zones.json specVersion %r' % data['specVersion'])
    if data['targetMap'] != TARGET:
        raise RuntimeError('zones.json targets a different map')

    keep_outs = [p['pointsXYcm'] for p in data['protectedPolygons']]
    if len(keep_outs) != conf['protectedPolygonCount']:
        raise RuntimeError('protected polygon count changed')
    for polygon, record in zip(keep_outs, data['protectedPolygons']):
        if len(polygon) < 3 or not polygon_is_simple(polygon) or polygon_area(polygon) <= 0:
            raise RuntimeError('protected polygon %s is degenerate or self-intersecting' % record['name'])

    margin = float(data['protectedMarginCm'])
    report = {'zones': [], 'protectedPolygons': [p['name'] for p in data['protectedPolygons']], 'protectedMarginCm': margin}
    weights = []
    for zone in data['zones']:
        polygon = zone['polygonXYcm']
        if len(polygon) < 3:
            raise RuntimeError('zone %s has fewer than three points' % zone['name'])
        if not polygon_is_simple(polygon):
            raise RuntimeError('zone %s is self-intersecting' % zone['name'])
        area = polygon_area(polygon)
        if area <= 0:
            raise RuntimeError('zone %s has zero area' % zone['name'])
        if abs(area / 1e4 - zone['areaSqM']) > 0.5:
            raise RuntimeError('zone %s recorded area disagrees with its polygon' % zone['name'])
        weights.append(area / 1e6 * float(zone['densityPer100SqM']))

        # A zone must have usable ground: sample its bounding box and require a healthy share
        # of samples to be inside, clear of every keep-out, and clear of its own edge margin.
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        usable = 0
        grid_samples = 0
        ground = zone['ground']
        ground_min, ground_max = None, None
        for i in range(24):
            for j in range(24):
                x = xs and (min(xs) + (max(xs) - min(xs)) * (i + 0.5) / 24.0)
                y = ys and (min(ys) + (max(ys) - min(ys)) * (j + 0.5) / 24.0)
                grid_samples += 1
                if not point_in_polygon(polygon, (x, y)):
                    continue
                z = ground['z0'] + ground['dzdx'] * x + ground['dzdy'] * y
                ground_min = z if ground_min is None else min(ground_min, z)
                ground_max = z if ground_max is None else max(ground_max, z)
                if distance_to_edge(polygon, (x, y)) < zone['edgeMarginCm']:
                    continue
                if in_any_protected(keep_outs, (x, y), margin):
                    continue
                usable += 1
        if usable == 0:
            raise RuntimeError('zone %s has no point clear of the keep-outs and its own edge margin' % zone['name'])
        if ground_min is None or not (math.isfinite(ground_min) and math.isfinite(ground_max)):
            raise RuntimeError('zone %s ground plane is not finite over its own extent' % zone['name'])
        if ground['mode'] not in ('flat', 'plane'):
            raise RuntimeError('zone %s has an unknown ground mode %r' % (zone['name'], ground['mode']))
        if ground['mode'] == 'flat' and (ground['dzdx'] or ground['dzdy']):
            raise RuntimeError('zone %s is flat but carries a gradient' % zone['name'])

        # The re-seed segment must have somewhere legal on it. AMikdashCrowdField walks the
        # segment from each instance's own place along it and takes the first sample that is
        # inside the zone and clear of every keep-out, so a segment that crosses a gate
        # corridor is still usable along the stretches that are clear -- but a segment with no
        # legal point at all would send every returning figure back to its start, which is a
        # zone that wants re-authoring, not a run to let through.
        a, b = zone['reseedEdgeXYcm']
        samples = 24
        legal = 0
        tight = 0
        for k in range(samples):
            t = k / float(samples)
            q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            if not point_in_polygon(polygon, q) or in_any_protected(keep_outs, q, margin):
                continue
            legal += 1
            if distance_to_edge(polygon, q) < zone['edgeMarginCm']:
                tight += 1
        if legal == 0:
            raise RuntimeError('zone %s re-seed segment has no point inside the zone and clear of the keep-outs' % zone['name'])
        if legal < samples // 2:
            raise RuntimeError('zone %s re-seed segment is legal at only %d of %d samples' % (zone['name'], legal, samples))

        report['zones'].append(dict(name=zone['name'], areaSqM=round(area / 1e4, 1),
                                    usableSampleFraction=round(usable / float(grid_samples), 3),
                                    reseedLegalFraction=round(legal / 24.0, 3),
                                    reseedSamplesInsideEdgeMargin=tight,
                                    groundZRangeCm=[round(ground_min, 1), round(ground_max, 1)],
                                    groundConfidence=ground['confidence'], standingRatio=zone['standingRatio']))

    counts = apportion(weights, int(data['defaultCrowdCount']))
    named = {z['name']: c for z, c in zip(data['zones'], counts)}
    if sum(counts) != int(data['defaultCrowdCount']):
        raise RuntimeError('apportionment does not sum to the crowd count')
    if named != data['expectedCountsAtDefault'] or named != conf['expectedCountsAtDefault']:
        raise RuntimeError('apportionment differs from the recorded expectation: %r' % named)
    thinned = apportion(weights, 2500)
    if sum(thinned) != 2500:
        raise RuntimeError('thinned apportionment does not sum to 2500')
    report['expectedCountsAtDefault'] = named
    report['expectedCountsAt2500'] = {z['name']: c for z, c in zip(data['zones'], thinned)}
    return data, report


def offline_check(spec=None):
    spec = spec or load_spec()
    figures = spec['figures']
    manifest_path = ROOT / figures['manifest']
    if sha(manifest_path) != figures['manifestSha256']:
        raise RuntimeError('geometry-manifest.json changed after the spec was prepared')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if manifest['status'] != figures['manifestStatusRequired']:
        raise RuntimeError('Figure manifest status %r' % manifest['status'])
    if manifest['path'] != figures['vatDecision']:
        raise RuntimeError('Figure manifest no longer records the VAT decision this spec was written against')

    report = {'meshes': [], 'vatDecision': manifest['path'], 'poseHipDegrees': manifest.get('poseHipDegrees')}
    seen_hashes = set()
    for record in figures['meshes']:
        entry = manifest['meshes'][record['name']]
        path = ROOT / figures['sourceFolder'] / record['file']
        if sha(path) != record['sha256'] or entry['sha256'] != record['sha256']:
            raise RuntimeError('Frozen OBJ hash differs for ' + record['name'])
        if record['sha256'] in seen_hashes:
            raise RuntimeError('Two pose meshes are byte-identical: the crowd would carry fewer silhouettes than claimed')
        seen_hashes.add(record['sha256'])
        vertices, faces, groups, materials = parse_obj(path)
        if faces != record['triangles'] or entry['triangles'] != record['triangles']:
            raise RuntimeError('Triangle count differs for ' + record['name'])
        reflected = {'min': [min(v[0] for v in vertices), -max(v[1] for v in vertices), min(v[2] for v in vertices)],
                     'max': [max(v[0] for v in vertices), -min(v[1] for v in vertices), max(v[2] for v in vertices)]}
        if box_error(reflected, record['canonicalBoundsCm']) > 1e-4:
            raise RuntimeError('%s file bounds (Y reflected) differ from the canonical bounds' % record['name'])
        # Feet on the origin plane and a believable adult height: the crowd field places
        # instances at ground level and trusts the mesh origin to be the feet.
        if abs(record['canonicalBoundsCm']['min'][2]) > 8.0:
            raise RuntimeError('%s does not stand on its own origin' % record['name'])
        height = record['canonicalBoundsCm']['max'][2] - record['canonicalBoundsCm']['min'][2]
        if not 150.0 < height < 200.0:
            raise RuntimeError('%s is %.1f cm tall' % (record['name'], height))
        if sorted(materials) != sorted(record['materialSlots']) or sorted(materials) != sorted(figures['materials']):
            raise RuntimeError('%s material groups differ from the spec' % record['name'])
        report['meshes'].append(dict(name=record['name'], triangles=faces, groups=len(groups),
                                     materials=sorted(materials), heightCm=round(height, 2), sha256=record['sha256']))

    zones_data, zone_report = check_zones(spec)
    report['zones'] = zone_report
    report['zoneCount'] = len(zones_data['zones'])
    namespace_dir = ROOT / 'Content' / figures['namespace'][len('/Game/'):]
    report['namespaceFolderExistsOnDisk'] = namespace_dir.exists()
    report['mapFileExists'] = (ROOT / spec['targetMapFile']).is_file()
    lods = figures['lods']
    report['lodTriangleBudget'] = dict(
        lod0=figures['meshes'][0]['triangles'],
        perLod=[int(round(figures['meshes'][0]['triangles'] * p)) for p in lods['percentTriangles']],
        allInstancesAtLod0=figures['meshes'][0]['triangles'] * int(spec['actor']['crowdCount']))
    report['status'] = 'offline_checks_passed'
    return report


# ==========================================================================
# Native (inside the editor)
# ==========================================================================

def _switch(name):
    import unreal as ue
    return bool(ue.SystemLibrary.parse_param(ue.SystemLibrary.get_command_line(), name))


def _switch_value(name):
    import unreal as ue
    # FParse::Value matches the literal prefix; omitting '=' returns '=240'.
    return ue.SystemLibrary.parse_param_value(ue.SystemLibrary.get_command_line(), name + '=')


def _python_property_names(type_object):
    """The real Python names of a UStruct's or UClass's editor properties, taken from the
    generated docstring. Guessing them ('DensityPerHundredSqM' -> ?) is exactly the kind of
    silent mismatch that writes half a zone and reports success."""
    names = set()
    doc = getattr(type_object, '__doc__', '') or ''
    for line in doc.splitlines():
        line = line.strip()
        if line.startswith('- ``'):
            end = line.find('``', 4)
            if end > 4:
                names.add(line[4:end])
    return names


def _resolve_properties(type_object, wanted, label):
    """Map intended CamelCase names to the actual Python names, matching case-insensitively on
    the letters alone so underscore placement cannot break the write."""
    available = _python_property_names(type_object)
    normal = {name.replace('_', '').lower(): name for name in available}
    mapping = {}
    missing = []
    for name in wanted:
        key = name.replace('_', '').lower()
        if key in normal:
            mapping[name] = normal[key]
        else:
            missing.append(name)
    if missing:
        raise RuntimeError('%s is missing %r; it exposes %r' % (label, sorted(missing), sorted(available)))
    return mapping


def _set_and_verify(target, name, value, compare=None):
    """set_editor_property return values are not trusted anywhere in this script; every write
    is read back. compare(readback, value) -> bool for values that are not plainly equal."""
    target.set_editor_property(name, value)
    got = target.get_editor_property(name)
    ok = compare(got, value) if compare else (got == value)
    if not ok:
        raise RuntimeError('Readback mismatch writing %s: wrote %r, read %r' % (name, value, got))
    return got


def _near(a, b, tolerance=1e-3):
    return abs(float(a) - float(b)) <= tolerance


def _connect_expression(ue, source, source_output, target, candidate_inputs):
    """connect_material_expressions with the 5.8 pin-name uncertainty handled explicitly: try
    the plausible names, keep the one that returns True, and record it. The named pitfalls
    (Desaturation and Clamp take '' for their first input, TextureSample takes 'UVs', Noise
    takes 'World Position') are why this is a list and not a constant."""
    ml = ue.MaterialEditingLibrary
    for name in candidate_inputs:
        if ml.connect_material_expressions(source, source_output, target, name):
            return name
    raise RuntimeError('No input pin of %s accepted a connection; tried %r' % (target.get_class().get_name(), candidate_inputs))


def _connect_property(ue, source, source_output, material, material_property, label):
    if not ue.MaterialEditingLibrary.connect_material_property(source, source_output, material_property):
        raise RuntimeError('Material property connection failed for ' + label)


def _build_crowd_material(ue, tools, assets, namespace, name, conf, wpo, receipt_pins):
    """A simple lit material: base colour lerped between two authored colours by per-instance
    custom data 1, plus a phase-driven vertical bob in world position offset from custom
    data 0. No gold, no metal, no texture."""
    ml = ue.MaterialEditingLibrary
    path = namespace + '/Materials/' + name
    if assets.does_asset_exist(path):
        material = ue.load_asset(path)
        if not material:
            raise RuntimeError('Existing material failed to load: ' + path)
        return material, False, {}

    material = tools.create_asset(name, namespace + '/Materials', ue.Material, ue.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Material factory failed for ' + name)

    pins = {}

    def constant3(colour):
        node = ml.create_material_expression(material, ue.MaterialExpressionConstant3Vector)
        node.set_editor_property('constant', ue.LinearColor(colour[0], colour[1], colour[2], 1.0))
        return node

    def constant(value):
        node = ml.create_material_expression(material, ue.MaterialExpressionConstant)
        node.set_editor_property('r', float(value))
        return node

    def custom_data(index):
        node = ml.create_material_expression(material, ue.MaterialExpressionPerInstanceCustomData)
        # data_index selects which of the component's NumCustomDataFloats this reads.
        node.set_editor_property('data_index', int(index))
        if int(node.get_editor_property('data_index')) != int(index):
            raise RuntimeError('PerInstanceCustomData data_index did not take')
        return node

    # ---- base colour: lerp(light, dark, customdata1)
    light = constant3(conf['baseColor'])
    dark = constant3(conf['tintTarget'])
    tint = custom_data(conf['tintedByCustomData'])
    lerp = ml.create_material_expression(material, ue.MaterialExpressionLinearInterpolate)
    pins['lerpA'] = _connect_expression(ue, light, '', lerp, ['A'])
    pins['lerpB'] = _connect_expression(ue, dark, '', lerp, ['B'])
    pins['lerpAlpha'] = _connect_expression(ue, tint, '', lerp, ['Alpha'])
    _connect_property(ue, lerp, '', material, ue.MaterialProperty.MP_BASE_COLOR, name + ' BaseColor')

    for value, prop, label in ((conf['metallic'], ue.MaterialProperty.MP_METALLIC, 'Metallic'),
                               (conf['roughness'], ue.MaterialProperty.MP_ROUGHNESS, 'Roughness')):
        _connect_property(ue, constant(value), '', material, prop, '%s %s' % (name, label))

    # ---- world position offset: Amp * 0.5 * (1 - cos(4*pi*(phase + t*rate)))
    # The engine's Cosine node evaluates cos(2*pi*x/Period), so feeding it 2*(phase + t*rate)
    # with the default period of 1 gives exactly the cos(4*pi*phase) of BobHeightCm.
    phase = custom_data(wpo['phaseCustomDataIndex'])
    time_node = ml.create_material_expression(material, ue.MaterialExpressionTime)
    rate = ml.create_material_expression(material, ue.MaterialExpressionMultiply)
    pins['rateA'] = _connect_expression(ue, time_node, '', rate, ['A'])
    pins['rateB'] = _connect_expression(ue, constant(wpo['cyclesPerSecond']), '', rate, ['B'])
    total = ml.create_material_expression(material, ue.MaterialExpressionAdd)
    pins['totalA'] = _connect_expression(ue, phase, '', total, ['A'])
    pins['totalB'] = _connect_expression(ue, rate, '', total, ['B'])
    doubled = ml.create_material_expression(material, ue.MaterialExpressionMultiply)
    pins['doubledA'] = _connect_expression(ue, total, '', doubled, ['A'])
    pins['doubledB'] = _connect_expression(ue, constant(2.0), '', doubled, ['B'])
    cosine = ml.create_material_expression(material, ue.MaterialExpressionCosine)
    pins['cosine'] = _connect_expression(ue, doubled, '', cosine, ['', 'Input'])
    one_minus = ml.create_material_expression(material, ue.MaterialExpressionOneMinus)
    pins['oneMinus'] = _connect_expression(ue, cosine, '', one_minus, ['', 'Input'])
    scaled = ml.create_material_expression(material, ue.MaterialExpressionMultiply)
    pins['scaledA'] = _connect_expression(ue, one_minus, '', scaled, ['A'])
    pins['scaledB'] = _connect_expression(ue, constant(float(wpo['amplitudeCm']) * 0.5), '', scaled, ['B'])
    up = ml.create_material_expression(material, ue.MaterialExpressionMultiply)
    pins['upA'] = _connect_expression(ue, constant3([0.0, 0.0, 1.0]), '', up, ['A'])
    pins['upB'] = _connect_expression(ue, scaled, '', up, ['B'])
    _connect_property(ue, up, '', material, ue.MaterialProperty.MP_WORLD_POSITION_OFFSET, name + ' WPO')

    # A material used on an instanced component must say so, or it is swapped for the default
    # at draw time and the whole crowd goes grey. set_editor_property is not trusted: read back.
    _set_and_verify(material, 'used_with_instanced_static_meshes', True)

    ml.recompile_material(material)
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Material save failed for ' + name)
    receipt_pins[name] = pins
    return material, True, pins


def _material_statistics(ue, material):
    """A functional readback: a material carrying a WPO chain has vertex-shader instructions a
    flat one does not. Recorded rather than asserted where the API is absent."""
    try:
        stats = ue.MaterialEditingLibrary.get_statistics(material)
        return dict(pixelShaderInstructions=int(stats.get_editor_property('num_pixel_shader_instructions')),
                    vertexShaderInstructions=int(stats.get_editor_property('num_vertex_shader_instructions')),
                    samplers=int(stats.get_editor_property('num_samplers')))
    except Exception as exc:  # noqa: BLE001 - the API surface is what is being probed
        return dict(unavailable=repr(exc))


def _import_mesh(ue, tools, namespace, path, name):
    ui = ue.FbxImportUI()
    for key, value in dict(automated_import_should_detect_type=False, mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
                           import_as_skeletal=False, import_mesh=True, import_animations=False, import_materials=False,
                           import_textures=False, create_physics_asset=False).items():
        ui.set_editor_property(key, value)
    data = ui.get_editor_property('static_mesh_import_data')
    for key, value in dict(combine_meshes=True, transform_vertex_to_absolute=True, bake_pivot_in_vertex=False,
                           convert_scene=False, convert_scene_unit=False, force_front_x_axis=False, import_uniform_scale=1.0,
                           auto_generate_collision=False, build_nanite=False, generate_lightmap_u_vs=False, remove_degenerates=True,
                           normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():
        data.set_editor_property(key, value)
    task = ue.AssetImportTask()
    for key, value in dict(filename=str(path), destination_path=namespace + '/Meshes', destination_name=name, automated=True,
                           async_=False, replace_existing=False, save=False, options=ui, factory=ue.FbxFactory()).items():
        task.set_editor_property(key, value)
    tools.import_asset_tasks([task])
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
        raise RuntimeError('OBJ import did not yield exactly one static mesh for ' + name)
    return objects[0]


def _verify_mesh(ue, mesh, record, tolerance):
    box = mesh.get_bounding_box()
    actual = {'min': [box.min.x, box.min.y, box.min.z], 'max': [box.max.x, box.max.y, box.max.z]}
    error = box_error(actual, record['canonicalBoundsCm'])
    # Nanite is off for these meshes (build_nanite=False), so get_num_triangles(0) is the real
    # LOD0 count and not a Nanite fallback count.
    triangles = mesh.get_num_triangles(0)
    nanite = None
    try:
        nanite = bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
    except Exception:  # noqa: BLE001
        nanite = None
    if nanite:
        raise RuntimeError('%s imported with Nanite enabled; get_num_triangles(0) would be the fallback count' % record['name'])
    if error > tolerance:
        raise RuntimeError('%s bounds error %.4f cm exceeds %.2f' % (record['name'], error, tolerance))
    if triangles != record['triangles']:
        raise RuntimeError('%s imported %d triangles, expected %d' % (record['name'], triangles, record['triangles']))
    return dict(boundsCm=actual, boundsErrorCm=error, triangles=triangles, naniteEnabled=nanite)


def _generate_lods(ue, mesh, lods):
    """Reduction LODs. Without them ten thousand instances are ten thousand LOD0 figures."""
    try:
        subsystem = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)
    except Exception as exc:  # noqa: BLE001
        return dict(generated=False, reason='StaticMeshEditorSubsystem unavailable: %r' % exc, lodCount=mesh.get_num_lods())
    try:
        settings = []
        for percent, screen in zip(lods['percentTriangles'], lods['screenSizes']):
            reduction = ue.StaticMeshReductionSettings()
            reduction.set_editor_property('percent_triangles', float(percent))
            reduction.set_editor_property('screen_size', float(screen))
            settings.append(reduction)
        options = ue.StaticMeshReductionOptions()
        options.set_editor_property('reduction_settings', settings)
        options.set_editor_property('auto_compute_lod_screen_size', False)
        subsystem.set_lods(mesh, options)
    except Exception as exc:  # noqa: BLE001
        return dict(generated=False, reason=repr(exc), lodCount=mesh.get_num_lods())
    count = mesh.get_num_lods()
    triangles = []
    for lod in range(count):
        try:
            triangles.append(mesh.get_num_triangles(lod))
        except Exception:  # noqa: BLE001
            triangles.append(None)
    return dict(generated=count > 1, lodCount=count, trianglesPerLod=triangles,
                requested=len(lods['percentTriangles']))


def _assign_slots(ue, mesh, materials_by_slot):
    statics = list(mesh.get_editor_property('static_materials'))
    assigned = {}
    for index, entry in enumerate(statics):
        imported = str(entry.get_editor_property('imported_material_slot_name'))
        slot = str(entry.get_editor_property('material_slot_name'))
        lowered = (imported + '|' + slot).lower()
        key = imported if imported in materials_by_slot else slot if slot in materials_by_slot else None
        if key is None:
            key = next((k for k in materials_by_slot if k.lower() in lowered), None)
        if key is None:
            # The OBJ importer can rename or merge groups. Fall back on the distinguishing word.
            for word, candidate in (('skin', 'CrowdSkin'), ('wrap', 'CrowdWrap'), ('robe', 'CrowdRobe')):
                if word in lowered and candidate in materials_by_slot:
                    key = candidate
                    break
        if key is None:
            key = 'CrowdRobe' if 'CrowdRobe' in materials_by_slot else sorted(materials_by_slot)[0]
        mesh.set_material(index, materials_by_slot[key])
        assigned.setdefault(key, []).append(index)
    if not assigned:
        raise RuntimeError('No material slot matched on ' + mesh.get_name())
    unmatched = sorted(set(materials_by_slot) - set(assigned))
    if unmatched:
        # Recorded, not fatal: the importer collapsing groups is a known behaviour of this
        # OBJ path and every remaining slot still received a crowd material above.
        assigned['_unmatchedMaterials'] = unmatched
    return assigned


def _vec2(v):
    import unreal as ue
    return ue.Vector2D(float(v[0]), float(v[1]))


def _build_zone_structs(ue, data, zone_props, keepout_props):
    zones = []
    for zone in data['zones']:
        s = ue.MikdashCrowdZone()
        ground = zone['ground']
        flow = zone['flow']
        s.set_editor_property(zone_props['Name'], zone['name'])
        s.set_editor_property(zone_props['PolygonCm'], [_vec2(p) for p in zone['polygonXYcm']])
        s.set_editor_property(zone_props['DensityPerHundredSqM'], float(zone['densityPer100SqM']))
        s.set_editor_property(zone_props['StandingRatio'], float(zone['standingRatio']))
        s.set_editor_property(zone_props['GroundMode'],
                              ue.MikdashCrowdGround.PLANE if ground['mode'] == 'plane' else ue.MikdashCrowdGround.FLAT)
        s.set_editor_property(zone_props['GroundZBase'], float(ground['z0']))
        s.set_editor_property(zone_props['GroundSlopeX'], float(ground['dzdx']))
        s.set_editor_property(zone_props['GroundSlopeY'], float(ground['dzdy']))
        s.set_editor_property(zone_props['FlowDirectionDegrees'], float(flow['directionDegrees']))
        s.set_editor_property(zone_props['GoalCm'], _vec2(flow['goalXYcm']))
        s.set_editor_property(zone_props['GoalWeight'], float(flow['goalWeight']))
        s.set_editor_property(zone_props['SwirlDegrees'], float(flow['swirlDegrees']))
        s.set_editor_property(zone_props['MeanderDegrees'], float(flow['meanderDegrees']))
        s.set_editor_property(zone_props['MeanderHz'], float(flow['meanderHz']))
        s.set_editor_property(zone_props['ReseedEdgeA'], _vec2(zone['reseedEdgeXYcm'][0]))
        s.set_editor_property(zone_props['ReseedEdgeB'], _vec2(zone['reseedEdgeXYcm'][1]))
        s.set_editor_property(zone_props['EdgeMarginCm'], float(zone['edgeMarginCm']))
        zones.append(s)
    keep_outs = []
    for polygon in data['protectedPolygons']:
        s = ue.MikdashCrowdKeepOut()
        s.set_editor_property(keepout_props['Name'], polygon['name'])
        s.set_editor_property(keepout_props['PolygonCm'], [_vec2(p) for p in polygon['pointsXYcm']])
        keep_outs.append(s)
    return zones, keep_outs


def _read_zones_back(zones, zone_props):
    out = []
    for zone in zones:
        out.append(dict(
            name=str(zone.get_editor_property(zone_props['Name'])),
            points=len(list(zone.get_editor_property(zone_props['PolygonCm']))),
            density=float(zone.get_editor_property(zone_props['DensityPerHundredSqM'])),
            standingRatio=float(zone.get_editor_property(zone_props['StandingRatio'])),
            groundZBase=float(zone.get_editor_property(zone_props['GroundZBase'])),
            slopeX=float(zone.get_editor_property(zone_props['GroundSlopeX'])),
            slopeY=float(zone.get_editor_property(zone_props['GroundSlopeY'])),
            direction=float(zone.get_editor_property(zone_props['FlowDirectionDegrees'])),
            goalWeight=float(zone.get_editor_property(zone_props['GoalWeight']))))
    return out


def _path(asset):
    return asset.get_path_name().split('.')[0] if asset else None


def run():
    import unreal as ue

    spec = load_spec()
    figures = spec['figures']
    actor_conf = spec['actor']
    offline = offline_check(spec)
    zones_data = json.loads((ROOT / spec['zones']['file']).read_text(encoding='utf-8-sig'))

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is running; use a dedicated editor process')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Unsaved packages present; run on a clean editor')

    crowd_class = ue.load_class(None, spec['compiledClassesRequired']['crowdField'])
    if not crowd_class:
        raise RuntimeError('Compiled MikdashRuntime with AMikdashCrowdField is not loaded; compile and restart the editor process')
    for attribute in ('MikdashCrowdField', spec['compiledClassesRequired']['crowdZoneStruct'], spec['compiledClassesRequired']['crowdKeepOutStruct'], 'MikdashCrowdGround'):
        if not hasattr(ue, attribute):
            raise RuntimeError('unreal.%s is missing: the loaded MikdashRuntime binary is stale. Compile the plugin and restart the editor process.' % attribute)
    class_props = _resolve_properties(ue.MikdashCrowdField, [
        'CrowdCount', 'RandomSeed', 'PoseMeshes', 'Zones', 'ProtectedPolygons', 'ProtectedMarginCm',
        'UpdateBudgetPerFrame', 'MinWalkSpeedCmPerSecond', 'MaxWalkSpeedCmPerSecond', 'MaxTurnDegreesPerSecond',
        'StrideLengthCm', 'BobAmplitudeCm', 'LeanAmplitudeDegrees', 'FreezeDistanceCm', 'CullDistanceCm',
        'InstanceStartCullDistanceCm', 'InstanceEndCullDistanceCm', 'CastShadows', 'EditorPreviewCount',
        'GarmentPaletteSize', 'FigureScaleMin', 'FigureScaleMax', 'TraceGroundOnSeed',
        'GroundTraceStartOffsetCm', 'GroundTraceDepthCm', 'GroundTraceMaxDeviationCm', 'ActivateOnBeginPlay',
    ], 'MikdashCrowdField')
    zone_props = _resolve_properties(ue.MikdashCrowdZone, [
        'Name', 'PolygonCm', 'DensityPerHundredSqM', 'StandingRatio', 'GroundMode', 'GroundZBase',
        'GroundSlopeX', 'GroundSlopeY', 'FlowDirectionDegrees', 'GoalCm', 'GoalWeight', 'SwirlDegrees',
        'MeanderDegrees', 'MeanderHz', 'ReseedEdgeA', 'ReseedEdgeB', 'EdgeMarginCm',
    ], 'MikdashCrowdZone')
    keepout_props = _resolve_properties(ue.MikdashCrowdKeepOut, ['Name', 'PolygonCm'], 'MikdashCrowdKeepOut')

    import_only = _switch('CrowdImportOnly')
    place_only = _switch('CrowdPlaceOnly')
    meshes_exist = _switch('CrowdMeshesExist') or place_only
    activate = _switch('CrowdFieldActivate')
    count_override = _switch_value('CrowdCount')
    crowd_count = int(actor_conf['crowdCount'])
    if count_override:
        try:
            crowd_count = max(0, min(60000, int(count_override)))
        except ValueError:
            raise RuntimeError('-CrowdCount= was not an integer: %r' % count_override)

    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_dir = ROOT / spec['receiptFolder']
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / (spec['receiptPrefix'] + stamp + '.json')
    map_file = ROOT / spec['targetMapFile']
    namespace = figures['namespace']

    receipt = dict(
        status='started', stamp=stamp, spec=str(SPEC_PATH.relative_to(ROOT)), specSha256=sha(SPEC_PATH),
        offline=offline, mapBeforeSha256=sha(map_file),
        switches=dict(importOnly=import_only, placeOnly=place_only, meshesExist=meshes_exist,
                      activateOnBeginPlay=activate, crowdCount=crowd_count),
        approach='Posed instanced static meshes with a flow field, NOT a vertex animation texture. See Scripts/create_crowd_vat.py for why, with the probe evidence.',
        meshes={}, materials={}, materialPins={}, lods={}, mapSaved=False,
        honesty=['These are instanced background figures: no collision, no navigation, no avoidance, no dialog, no articulated limbs.',
                 'Each instance holds one frozen stride pose; the motion is translation plus a gait bob and lean.',
                 'The 24 MikdashResidentCharacter actors remain the only individuals in the scene.',
                 'No PIE, render, cook, packaged run or frame-time measurement is claimed by this script.'],
        scope='Native asset import and one map actor with save/reopen readback; no runtime or visual acceptance')

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

    write()
    checkpoint = None
    try:
        # ---- meshes and materials
        if assets.does_directory_exist(namespace) and not meshes_exist:
            raise RuntimeError('Namespace %s exists; pass -CrowdMeshesExist to re-verify instead of importing' % namespace)

        materials = {}
        wpo_ok = True
        for slot, conf in sorted(figures['materials'].items()):
            material, created, pins = _build_crowd_material(ue, tools, assets, namespace, conf['asset'], conf,
                                                            figures['worldPositionOffset'], receipt['materialPins'])
            materials[slot] = material
            stats = _material_statistics(ue, material)
            instanced_ok = bool(material.get_editor_property('used_with_instanced_static_meshes'))
            if not instanced_ok:
                raise RuntimeError('%s does not read back used_with_instanced_static_meshes' % conf['asset'])
            receipt['materials'][slot] = dict(path=material.get_path_name(), created=created,
                                              usedWithInstancedStaticMeshes=instanced_ok, statistics=stats,
                                              pins=pins)
            if created and isinstance(stats.get('vertexShaderInstructions'), int) and stats['vertexShaderInstructions'] <= 0:
                wpo_ok = False
            if not created:
                # Re-used an existing material: its graph was authored by an earlier run and is
                # not re-verified here, so the GPU bob cannot be claimed.
                wpo_ok = False
        receipt['worldPositionOffsetVerified'] = wpo_ok

        meshes = {}
        for record in figures['meshes']:
            asset_path = namespace + '/Meshes/' + record['name']
            if meshes_exist:
                mesh = ue.load_asset(asset_path)
                if not mesh:
                    raise RuntimeError('Expected existing mesh missing: ' + asset_path)
                verified = _verify_mesh(ue, mesh, record, figures['boundsToleranceCm'])
                imported = False
            else:
                mesh = _import_mesh(ue, tools, namespace, ROOT / figures['sourceFolder'] / record['file'], record['name'])
                verified = _verify_mesh(ue, mesh, record, figures['boundsToleranceCm'])
                imported = True
            slots = _assign_slots(ue, mesh, materials)
            lod_report = _generate_lods(ue, mesh, figures['lods'])
            receipt['lods'][record['name']] = lod_report
            if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
                raise RuntimeError('Mesh save failed: ' + asset_path)
            meshes[record['name']] = mesh
            receipt['meshes'][record['name']] = dict(path=mesh.get_path_name(), imported=imported, slots=slots, **verified)
        receipt['status'] = 'meshes_ready'
        write()
        if import_only:
            receipt['status'] = 'import_only_complete_map_unchanged'
            return receipt

        # ---- map
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            if not levels.load_level(TARGET):
                raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Unexpected editor world')
        if TARGET in spec['protectedMaps']:
            raise RuntimeError('Refusing to edit a protected map')

        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'BeforeCrowdField.umap')
        if sha(checkpoint / 'BeforeCrowdField.umap') != receipt['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy hash mismatch')
        receipt['checkpoint'] = str(checkpoint)
        write()

        existing = [a for a in actors.get_all_level_actors() if a.get_actor_label() == actor_conf['label']]
        if existing:
            raise RuntimeError('%s already exists; refusing to place a duplicate crowd' % actor_conf['label'])
        before_actor_count = len(actors.get_all_level_actors())

        field = actors.spawn_actor_from_class(crowd_class, ue.Vector(*actor_conf['location']), ue.Rotator(*actor_conf['rotation']), transient=False)
        if not field:
            raise RuntimeError('Crowd field spawn failed')
        field.set_actor_label(actor_conf['label'])
        field.set_folder_path(actor_conf['folder'])
        field.tags = [ue.Name(actor_conf['tag'])]

        zones, keep_outs = _build_zone_structs(ue, zones_data, zone_props, keepout_props)
        pose_meshes = [meshes[record['name']] for record in figures['meshes']]

        _set_and_verify(field, class_props['PoseMeshes'], pose_meshes,
                        compare=lambda got, want: [_path(m) for m in list(got)] == [_path(m) for m in want])
        _set_and_verify(field, class_props['Zones'], zones, compare=lambda got, want: len(list(got)) == len(want))
        _set_and_verify(field, class_props['ProtectedPolygons'], keep_outs, compare=lambda got, want: len(list(got)) == len(want))
        _set_and_verify(field, class_props['CrowdCount'], crowd_count)
        _set_and_verify(field, class_props['RandomSeed'], int(actor_conf['randomSeed']))
        _set_and_verify(field, class_props['ProtectedMarginCm'], float(zones_data['protectedMarginCm']), _near)
        _set_and_verify(field, class_props['UpdateBudgetPerFrame'], int(actor_conf['updateBudgetPerFrame']))
        _set_and_verify(field, class_props['MinWalkSpeedCmPerSecond'], float(actor_conf['minWalkSpeedCmPerSecond']), _near)
        _set_and_verify(field, class_props['MaxWalkSpeedCmPerSecond'], float(actor_conf['maxWalkSpeedCmPerSecond']), _near)
        _set_and_verify(field, class_props['MaxTurnDegreesPerSecond'], float(actor_conf['maxTurnDegreesPerSecond']), _near)
        _set_and_verify(field, class_props['StrideLengthCm'], float(actor_conf['strideLengthCm']), _near)
        # The GPU bob and the CPU bob are the same curve; running both would double it. The CPU
        # bob is kept only when the material could not be verified this run.
        cpu_bob = 0.0 if wpo_ok else float(actor_conf['bobAmplitudeCm'])
        _set_and_verify(field, class_props['BobAmplitudeCm'], cpu_bob, _near)
        _set_and_verify(field, class_props['LeanAmplitudeDegrees'], float(actor_conf['leanAmplitudeDegrees']), _near)
        _set_and_verify(field, class_props['FreezeDistanceCm'], float(actor_conf['freezeDistanceCm']), _near)
        _set_and_verify(field, class_props['CullDistanceCm'], float(actor_conf['cullDistanceCm']), _near)
        _set_and_verify(field, class_props['InstanceStartCullDistanceCm'], int(actor_conf['instanceStartCullDistanceCm']))
        _set_and_verify(field, class_props['InstanceEndCullDistanceCm'], int(actor_conf['instanceEndCullDistanceCm']))
        _set_and_verify(field, class_props['CastShadows'], bool(actor_conf['castShadows']))
        _set_and_verify(field, class_props['EditorPreviewCount'], int(actor_conf['editorPreviewCount']))
        _set_and_verify(field, class_props['GarmentPaletteSize'], int(actor_conf['garmentPaletteSize']))
        _set_and_verify(field, class_props['FigureScaleMin'], float(actor_conf['figureScaleMin']), _near)
        _set_and_verify(field, class_props['FigureScaleMax'], float(actor_conf['figureScaleMax']), _near)
        _set_and_verify(field, class_props['TraceGroundOnSeed'], bool(actor_conf['traceGroundOnSeed']))
        _set_and_verify(field, class_props['GroundTraceStartOffsetCm'], float(actor_conf['groundTraceStartOffsetCm']), _near)
        _set_and_verify(field, class_props['GroundTraceDepthCm'], float(actor_conf['groundTraceDepthCm']), _near)
        _set_and_verify(field, class_props['GroundTraceMaxDeviationCm'], float(actor_conf['groundTraceMaxDeviationCm']), _near)
        _set_and_verify(field, class_props['ActivateOnBeginPlay'], bool(activate))
        receipt['cpuBobAmplitudeCm'] = cpu_bob

        # Build the preview so the map shows a crowd when it is opened, and so there is an
        # instance count to read back. The full CrowdCount is built at BeginPlay.
        field.call_method('BuildEditorPreview')
        preview_instances = int(field.call_method('GetTotalInstanceCount'))
        receipt['preBuild'] = dict(
            previewInstances=preview_instances,
            seeded=int(field.call_method('GetSeededAgentCount')),
            refused=int(field.call_method('GetRefusedSeedCount')),
            groundTraceMisses=int(field.call_method('GetGroundTraceMissCount')),
            framesPerSweep=int(field.call_method('GetFramesPerSweep')),
            summary=str(field.call_method('GetCrowdSummary')))
        if preview_instances != int(actor_conf['editorPreviewCount']):
            raise RuntimeError('Editor preview built %d instances, expected %d' % (preview_instances, actor_conf['editorPreviewCount']))
        if receipt['preBuild']['refused'] > 0:
            # A refusal means a zone could not place a figure clear of the keep-outs. It is
            # surfaced, never averaged away.
            receipt['refusalWarning'] = '%d of %d preview instances could not be seeded clear of the keep-outs' % (
                receipt['preBuild']['refused'], preview_instances)

        field.modify()
        field_name = field.get_name()
        after_actor_count = len(actors.get_all_level_actors())
        if after_actor_count != before_actor_count + 1:
            raise RuntimeError('Actor count moved by %d, expected exactly one new actor' % (after_actor_count - before_actor_count))
        receipt['actor'] = dict(name=field_name, label=actor_conf['label'], folder=actor_conf['folder'])

        if not levels.save_current_level():
            raise RuntimeError('Level save failed')
        receipt.update(status='saved_reopen_pending', mapSaved=True, mapAfterSha256=sha(map_file))
        write()

        # ---- reopen and read back
        if not levels.load_level(TARGET) or editor.get_editor_world().get_outermost().get_name() != TARGET:
            raise RuntimeError('Reopen failed')
        reopened = [a for a in actors.get_all_level_actors() if a.get_actor_label() == actor_conf['label']]
        if len(reopened) != 1:
            raise RuntimeError('Reopened map has %d crowd field actors, expected 1' % len(reopened))
        field = reopened[0]

        readback = dict(
            crowdCount=int(field.get_editor_property(class_props['CrowdCount'])),
            randomSeed=int(field.get_editor_property(class_props['RandomSeed'])),
            poseMeshes=[_path(m) for m in list(field.get_editor_property(class_props['PoseMeshes']))],
            zoneCount=len(list(field.get_editor_property(class_props['Zones']))),
            protectedPolygonCount=len(list(field.get_editor_property(class_props['ProtectedPolygons']))),
            protectedMarginCm=float(field.get_editor_property(class_props['ProtectedMarginCm'])),
            updateBudgetPerFrame=int(field.get_editor_property(class_props['UpdateBudgetPerFrame'])),
            freezeDistanceCm=float(field.get_editor_property(class_props['FreezeDistanceCm'])),
            cullDistanceCm=float(field.get_editor_property(class_props['CullDistanceCm'])),
            instanceStartCullDistanceCm=int(field.get_editor_property(class_props['InstanceStartCullDistanceCm'])),
            instanceEndCullDistanceCm=int(field.get_editor_property(class_props['InstanceEndCullDistanceCm'])),
            editorPreviewCount=int(field.get_editor_property(class_props['EditorPreviewCount'])),
            bobAmplitudeCm=float(field.get_editor_property(class_props['BobAmplitudeCm'])),
            activateOnBeginPlay=bool(field.get_editor_property(class_props['ActivateOnBeginPlay'])),
            zones=_read_zones_back(list(field.get_editor_property(class_props['Zones'])), zone_props))

        expected_meshes = [namespace + '/Meshes/' + record['name'] for record in figures['meshes']]
        problems = []
        if readback['crowdCount'] != crowd_count:
            problems.append('crowdCount %r' % readback['crowdCount'])
        if readback['poseMeshes'] != expected_meshes:
            problems.append('poseMeshes %r' % readback['poseMeshes'])
        if readback['zoneCount'] != len(zones_data['zones']):
            problems.append('zoneCount %r' % readback['zoneCount'])
        if readback['protectedPolygonCount'] != len(zones_data['protectedPolygons']):
            problems.append('protectedPolygonCount %r' % readback['protectedPolygonCount'])
        if readback['activateOnBeginPlay'] != bool(activate):
            problems.append('activateOnBeginPlay %r' % readback['activateOnBeginPlay'])
        if not _near(readback['bobAmplitudeCm'], cpu_bob):
            problems.append('bobAmplitudeCm %r' % readback['bobAmplitudeCm'])
        for got, want in zip(readback['zones'], zones_data['zones']):
            if got['name'] != want['name'] or got['points'] != len(want['polygonXYcm']):
                problems.append('zone %r' % got)
            if not _near(got['density'], want['densityPer100SqM']) or not _near(got['standingRatio'], want['standingRatio']):
                problems.append('zone tuning %r' % got)
            if not _near(got['groundZBase'], want['ground']['z0'], 1e-2):
                problems.append('zone ground %r' % got)
        if problems:
            raise RuntimeError('Readback mismatch after reopen: %r' % problems)

        # Rebuild the preview on the reopened actor: the instance count must reproduce exactly,
        # which is what proves the zones survived the round trip and not merely the numbers.
        field.call_method('BuildEditorPreview')
        rebuilt = int(field.call_method('GetTotalInstanceCount'))
        if rebuilt != int(actor_conf['editorPreviewCount']):
            raise RuntimeError('Reopened actor rebuilt %d instances, expected %d' % (rebuilt, actor_conf['editorPreviewCount']))
        receipt['postReopen'] = dict(
            instanceCount=rebuilt,
            seeded=int(field.call_method('GetSeededAgentCount')),
            refused=int(field.call_method('GetRefusedSeedCount')),
            groundTraceMisses=int(field.call_method('GetGroundTraceMissCount')),
            summary=str(field.call_method('GetCrowdSummary')))
        receipt['readback'] = readback
        receipt['expectedFullCounts'] = zones_data['expectedCountsAtDefault']
        receipt['performanceNote'] = (
            'At the written CrowdCount of %d the crowd is %d LOD0 triangles if every instance were at LOD0; the reduction LODs '
            'and a %d cm instance cull are what make that affordable. The CPU cost is bounded at %d instance updates a frame '
            '(one full sweep every %d frames) and does not grow with CrowdCount. Nothing here has been measured on the target '
            'GPU: pass -CrowdCount=2500 to thin every zone in proportion if the frame time is not acceptable.'
            % (crowd_count, crowd_count * figures['meshes'][0]['triangles'], actor_conf['instanceEndCullDistanceCm'],
               actor_conf['updateBudgetPerFrame'],
               (crowd_count + actor_conf['updateBudgetPerFrame'] - 1) // max(1, actor_conf['updateBudgetPerFrame'])))
        receipt['status'] = 'crowd_field_saved_reopened_runtime_pie_and_visual_review_pending'
    except Exception as exc:
        receipt.update(status='failed_checkpoint_available' if checkpoint else 'failed_before_map_change', failure=repr(exc))
        raise
    finally:
        receipt['mapAfterSha256'] = sha(map_file)
        receipt['mapBytesChanged'] = receipt['mapAfterSha256'] != receipt['mapBeforeSha256']
        write()
        ue.log(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    if '--offline-check' in sys.argv:
        print(json.dumps(offline_check(), indent=2))
    else:
        try:
            import unreal  # noqa: F401
        except ImportError:
            raise SystemExit('Outside the editor use --offline-check; native runs go through UnrealEditor-Cmd -run=pythonscript (see docstring)')
        run()

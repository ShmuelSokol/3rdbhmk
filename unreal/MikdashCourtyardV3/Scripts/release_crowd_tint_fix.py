"""Guarded diagnosis and repair of the uniformly grey instanced crowd (AMikdashCrowdField).

Everything numeric comes from Scripts/release_crowd_tint_fix.spec.json.

Modes (engine command-line switches; exactly one of the first three):
  -CrowdTintDump           READ-ONLY. Load the main map, find RELEASE_CrowdField, dump per pose
                           HISM: NumCustomDataFloats, instance count, static mesh, every material
                           slot (component override + mesh slot names), and a sample plus a
                           histogram of the saved per-instance custom data. Also dumps the three
                           existing crowd materials' graphs. Nothing is saved; the map hash is
                           asserted unchanged at the end.
      -CrowdTintRebuildProbe   with the dump: additionally call BuildEditorPreview in memory and
                           read the freshly written custom data back (still no save).
  -CrowdTintMaterialsOnly  create/verify the three palette materials under the review namespace;
                           no map change.
  -CrowdTintApply          full fix: checkpoint the .umap, create/verify the materials, set the
                           per-slot override materials on the six HISMs, set GarmentPaletteSize,
                           rebuild the editor preview, save, reopen, read everything back.
  -CrowdTintVerify         fresh-process readback of the applied state (no save).

Guards: right project, no game world, no dirty packages, compiled AMikdashCrowdField loaded,
target map not protected, checkpoint hash equals the before hash. Receipts are written at
start, on failure and in finally to SourceAssets/runtime-review/crowd-field/. Setters are never
trusted (UE 5.8 material setters return False on success): every write is read back.

Commandlet invocation (serial; never while another editor/commandlet runs; fresh -abslog):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_crowd_tint_fix.py"
      -unattended -nullrhi -CrowdTintDump -CrowdTintRebuildProbe
      -abslog="C:/Mikdash/Working-5.8/Fable-CrowdTint-Dump-01.log"

Offline (no engine):  python Scripts/release_crowd_tint_fix.py --offline-check
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / 'Scripts' / 'release_crowd_tint_fix.spec.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


# ==========================================================================
# Offline
# ==========================================================================

def expected_tints(size):
    return [k / float(size - 1) for k in range(size)]


def offline_check(spec=None):
    spec = spec or load_spec()
    fix = spec['fix']
    palette = fix['garmentPalette']
    problems = []
    if len(palette) != fix['garmentPaletteSize']:
        problems.append('palette size %d differs from garmentPaletteSize %d' % (len(palette), fix['garmentPaletteSize']))
    if not 1 <= fix['garmentPaletteSize'] <= 32:
        problems.append('garmentPaletteSize outside the C++ clamp 1..32')
    names = [p['name'] for p in palette]
    if len(set(names)) != len(names):
        problems.append('duplicate palette names')
    chroma = {}
    for entry in palette:
        rgb = entry['rgb']
        if len(rgb) != 3 or not all(0.0 <= c <= 1.0 for c in rgb):
            problems.append('%s colour outside 0..1' % entry['name'])
        chroma[entry['name']] = round(max(rgb) - min(rgb), 4)
        if chroma[entry['name']] > fix['maxChroma']:
            problems.append('%s is saturated (chroma %.3f > %.3f)' % (entry['name'], chroma[entry['name']], fix['maxChroma']))
    whites = [p for p in palette if p['name'] == 'linen-bleached']
    white_share = len(whites) / float(len(palette))
    if not 0.10 <= white_share <= 0.20:
        problems.append('white share %.3f outside 10..20 percent' % white_share)
    if not 0 <= fix['sentinelDefaultTintIndex'] < len(palette):
        problems.append('sentinel index outside the palette')
    if not (fix['tintCustomDataIndex'] < spec['expected']['numCustomDataFloats']
            and fix['variationCustomDataIndex'] < spec['expected']['numCustomDataFloats']):
        problems.append('custom data index beyond NumCustomDataFloats')
    order = spec['objSlotOrder']
    if len(order['groups']) != len(order['materials']) != spec['expected']['meshSlotsPerPose']:
        problems.append('OBJ slot order length mismatch')
    # The OBJ order is re-derived from the frozen source, not trusted from the spec alone.
    obj_folder = ROOT / 'SourceAssets/runtime-review/crowd-field/CrowdFigureV1'
    for pose in range(6):
        groups, materials = [], []
        for line in (obj_folder / ('SM_CrowdFigure_P%d.obj' % pose)).read_text(encoding='utf-8').splitlines():
            if line.startswith('g '):
                groups.append(line[2:].strip())
            elif line.startswith('usemtl '):
                materials.append(line[7:].strip())
        if groups != order['groups'] or materials != order['materials']:
            problems.append('SM_CrowdFigure_P%d.obj group/material order differs from the spec' % pose)
    for kind, words in order['groupWords'].items():
        for group, material in zip(order['groups'], order['materials']):
            if any(w in group.lower() for w in words) and material != kind:
                problems.append('group word mapping wrong for %s -> %s' % (group, material))
    if problems:
        raise RuntimeError('Offline check failed: %r' % problems)
    return dict(status='offline_spec_consistent', specSha256=sha(SPEC_PATH), paletteSize=len(palette),
                whiteShare=white_share, chroma=chroma, expectedTints=[round(t, 6) for t in expected_tints(len(palette))],
                sentinelTint=round(fix['sentinelDefaultTintIndex'] / float(len(palette) - 1), 6))


# ==========================================================================
# Native helpers
# ==========================================================================

def _switch(name):
    import unreal as ue
    return bool(ue.SystemLibrary.parse_param(ue.SystemLibrary.get_command_line(), name))


def _python_property_names(type_object):
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
    available = _python_property_names(type_object)
    normal = {name.replace('_', '').lower(): name for name in available}
    mapping, missing = {}, []
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
    target.set_editor_property(name, value)
    got = target.get_editor_property(name)
    ok = compare(got, value) if compare else (got == value)
    if not ok:
        raise RuntimeError('Readback mismatch writing %s: wrote %r, read %r' % (name, value, got))
    return got


def _near(a, b, tolerance=1e-3):
    return abs(float(a) - float(b)) <= tolerance


def _path(asset):
    return asset.get_path_name().split('.')[0] if asset else None


def _linear(color):
    return [float(color.r), float(color.g), float(color.b)]


def _connect_expression(ue, source, source_output, target, candidate_inputs):
    """connect_material_expressions with the 5.8 pin-name uncertainty handled explicitly."""
    ml = ue.MaterialEditingLibrary
    for name in candidate_inputs:
        if ml.connect_material_expressions(source, source_output, target, name):
            return name
    raise RuntimeError('No input pin of %s accepted a connection; tried %r' % (target.get_class().get_name(), candidate_inputs))


def _connect_property(ue, source, material_property, label):
    if not ue.MaterialEditingLibrary.connect_material_property(source, '', material_property):
        raise RuntimeError('Material property connection failed for ' + label)


SINGLE = ['', 'None', 'Input']


def _histogram(values, digits=3):
    counts = {}
    for v in values:
        key = '%.*f' % (digits, v)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: float(kv[0])))


def _component_dump(ue, component, stride_expected, sample_count):
    stride = int(component.get_editor_property('num_custom_data_floats'))
    instances = int(component.get_instance_count())
    custom = list(component.get_editor_property('per_instance_sm_custom_data'))
    mesh = component.get_editor_property('static_mesh')
    slots = []
    if mesh:
        statics = list(mesh.get_editor_property('static_materials'))
        for index, entry in enumerate(statics):
            interface = entry.get_editor_property('material_interface')
            override = component.get_material(index)
            slots.append(dict(index=index,
                              slotName=str(entry.get_editor_property('material_slot_name')),
                              importedSlotName=str(entry.get_editor_property('imported_material_slot_name')),
                              meshMaterial=_path(interface),
                              componentMaterial=_path(override)))
    overrides = [_path(m) for m in list(component.get_editor_property('override_materials'))]
    out = dict(name=component.get_name(), componentClass=component.get_class().get_name(),
               numCustomDataFloats=stride, instanceCount=instances, staticMesh=_path(mesh),
               customDataFloats=len(custom), customDataLengthConsistent=(len(custom) == stride * instances),
               overrideMaterials=overrides, slots=slots)
    if stride == stride_expected and instances > 0 and len(custom) == stride * instances:
        out['sampleFirstInstances'] = [custom[i * stride:(i + 1) * stride] for i in range(min(sample_count, instances))]
        for channel in range(stride):
            out['channel%dHistogram' % channel] = _histogram(custom[channel::stride])
        tints = custom[1::stride]
        out['tintDistinctValues'] = len(set('%.3f' % t for t in tints))
    return out


def _find_field(ue, spec):
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    found = [a for a in actors.get_all_level_actors() if a.get_actor_label() == spec['actorLabel']]
    if len(found) != 1:
        raise RuntimeError('Expected exactly one %s, found %d' % (spec['actorLabel'], len(found)))
    return found[0]


def _pose_components(ue, field, expected):
    components = None
    try:
        props = _resolve_properties(ue.MikdashCrowdField, ['PoseComponents'], 'MikdashCrowdField')
        components = [c for c in list(field.get_editor_property(props['PoseComponents'])) if c]
        basis = 'PoseComponents property'
    except Exception:  # noqa: BLE001 - private UPROPERTY may not be reflected to Python
        components = None
    if not components:
        components = sorted(field.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent), key=lambda c: c.get_name())
        basis = 'get_components_by_class(HierarchicalInstancedStaticMeshComponent) sorted by name'
    if len(components) != expected:
        raise RuntimeError('Expected %d pose components, found %d (%s)' % (expected, len(components), basis))
    return components, basis


def _material_graph_dump(ue, material):
    ml = ue.MaterialEditingLibrary
    out = dict(path=material.get_path_name(),
               usedWithInstancedStaticMeshes=bool(material.get_editor_property('used_with_instanced_static_meshes')))
    try:
        stats = ml.get_statistics(material)
        out['statistics'] = dict(pixelShaderInstructions=int(stats.get_editor_property('num_pixel_shader_instructions')),
                                 vertexShaderInstructions=int(stats.get_editor_property('num_vertex_shader_instructions')),
                                 samplers=int(stats.get_editor_property('num_samplers')))
    except Exception as exc:  # noqa: BLE001
        out['statistics'] = dict(unavailable=repr(exc))
    if hasattr(ml, 'get_material_expressions'):
        expressions = list(ml.get_material_expressions(material))
        classes = {}
        custom_nodes = []
        constants3 = []
        for expression in expressions:
            cls = expression.get_class().get_name()
            classes[cls] = classes.get(cls, 0) + 1
            if isinstance(expression, ue.MaterialExpressionPerInstanceCustomData):
                custom_nodes.append(dict(dataIndex=int(expression.get_editor_property('data_index')),
                                         constDefaultValue=float(expression.get_editor_property('const_default_value'))))
            elif isinstance(expression, ue.MaterialExpressionConstant3Vector):
                constants3.append([round(v, 4) for v in _linear(expression.get_editor_property('constant'))])
        out.update(expressionCount=len(expressions), expressionClasses=classes, perInstanceCustomDataNodes=custom_nodes,
                   constant3Vectors=constants3)
    else:
        out['expressions'] = 'MaterialEditingLibrary.get_material_expressions unavailable'
    try:
        node = ml.get_material_property_input_node(material, ue.MaterialProperty.MP_BASE_COLOR)
        out['baseColorInputClass'] = node.get_class().get_name() if node else None
    except Exception as exc:  # noqa: BLE001
        out['baseColorInputClass'] = 'unavailable: %r' % (exc,)
    return out


# ==========================================================================
# Palette material construction
# ==========================================================================

def _build_material(ue, tools, assets, namespace, name, builder, receipt_pins):
    ml = ue.MaterialEditingLibrary
    path = namespace + '/' + name
    if assets.does_asset_exist(path):
        material = ue.load_asset(path)
        if not material:
            raise RuntimeError('Existing material failed to load: ' + path)
        return material, False
    material = tools.create_asset(name, namespace, ue.Material, ue.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Material factory failed for ' + name)
    pins = {}
    builder(ue, material, pins)
    # A material used on an instanced component must say so, or it is swapped for the default
    # at draw time. set_editor_property is not trusted: read back.
    _set_and_verify(material, 'used_with_instanced_static_meshes', True)
    if hasattr(ml, 'set_material_usage') and hasattr(ue, 'MaterialUsage'):
        try:
            ml.set_material_usage(material, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        except Exception:  # noqa: BLE001 - the property write above is the one that is verified
            pass
    ml.recompile_material(material)
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('Material save failed for ' + name)
    receipt_pins[name] = pins
    return material, True


def _nodes(ue, material):
    ml = ue.MaterialEditingLibrary

    def make(cls, x=0, y=0):
        return ml.create_material_expression(material, cls, x, y)

    def constant(value, x=0, y=0):
        node = make(ue.MaterialExpressionConstant, x, y)
        node.set_editor_property('r', float(value))
        return node

    def constant3(rgb, x=0, y=0):
        node = make(ue.MaterialExpressionConstant3Vector, x, y)
        node.set_editor_property('constant', ue.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
        got = _linear(node.get_editor_property('constant'))
        if any(abs(a - b) > 1e-4 for a, b in zip(got, rgb)):
            raise RuntimeError('Constant3Vector did not take %r (read %r)' % (rgb, got))
        return node

    def custom_data(index, default, x=0, y=0):
        node = make(ue.MaterialExpressionPerInstanceCustomData, x, y)
        node.set_editor_property('data_index', int(index))
        node.set_editor_property('const_default_value', float(default))
        if int(node.get_editor_property('data_index')) != int(index):
            raise RuntimeError('PerInstanceCustomData data_index did not take')
        if not _near(node.get_editor_property('const_default_value'), default, 1e-5):
            raise RuntimeError('PerInstanceCustomData const_default_value did not take')
        return node

    return make, constant, constant3, custom_data


def _brightness_chain(ue, material, pins, custom_data, make, constant, fix, x, y):
    """0.88 + 0.24 * customdata0 -> a per-figure brightness factor."""
    lo, hi = float(fix['brightness']['min']), float(fix['brightness']['max'])
    variation = custom_data(fix['variationCustomDataIndex'], 0.5, x, y)
    scale = make(ue.MaterialExpressionMultiply, x + 200, y)
    pins['brightScaleA'] = _connect_expression(ue, variation, '', scale, ['A'])
    pins['brightScaleB'] = _connect_expression(ue, constant(hi - lo, x, y + 80), '', scale, ['B'])
    offset = make(ue.MaterialExpressionAdd, x + 400, y)
    pins['brightAddA'] = _connect_expression(ue, scale, '', offset, ['A'])
    pins['brightAddB'] = _connect_expression(ue, constant(lo, x + 200, y + 80), '', offset, ['B'])
    return offset


def _finish(ue, material, pins, colour_node, roughness, make, constant, fix):
    if fix['readThroughVertexInterpolator']:
        interp = make(ue.MaterialExpressionVertexInterpolator, 800, 0)
        pins['vertexInterpolator'] = _connect_expression(ue, colour_node, '', interp, SINGLE)
        _connect_property(ue, interp, ue.MaterialProperty.MP_BASE_COLOR, material.get_name() + ' BaseColor')
    else:
        _connect_property(ue, colour_node, ue.MaterialProperty.MP_BASE_COLOR, material.get_name() + ' BaseColor')
    _connect_property(ue, constant(roughness, 800, 300), ue.MaterialProperty.MP_ROUGHNESS, material.get_name() + ' Roughness')
    _connect_property(ue, constant(0.0, 800, 400), ue.MaterialProperty.MP_METALLIC, material.get_name() + ' Metallic')


def garment_builder(fix):
    palette = fix['garmentPalette']
    size = len(palette)
    sentinel = fix['sentinelDefaultTintIndex'] / float(size - 1)

    def build(ue, material, pins):
        make, constant, constant3, custom_data = _nodes(ue, material)
        # u = tint * (N - 1): the palette index the C++ encoded as index / (N - 1).
        tint = custom_data(fix['tintCustomDataIndex'], sentinel, -1600, 0)
        index = make(ue.MaterialExpressionMultiply, -1400, 0)
        pins['indexA'] = _connect_expression(ue, tint, '', index, ['A'])
        pins['indexB'] = _connect_expression(ue, constant(size - 1, -1600, 100), '', index, ['B'])
        # colour = sum_k saturate(1 - |u - k|) * C_k : exactly C_k at u = k, hard steps between.
        total = None
        for k, entry in enumerate(palette):
            y = 200 + k * 160
            diff = make(ue.MaterialExpressionSubtract, -1200, y)
            pins.setdefault('subtractA', _connect_expression(ue, index, '', diff, ['A']))
            pins.setdefault('subtractB', _connect_expression(ue, constant(k, -1400, y), '', diff, ['B']))
            absolute = make(ue.MaterialExpressionAbs, -1000, y)
            pins.setdefault('abs', _connect_expression(ue, diff, '', absolute, SINGLE))
            one_minus = make(ue.MaterialExpressionOneMinus, -800, y)
            pins.setdefault('oneMinus', _connect_expression(ue, absolute, '', one_minus, SINGLE))
            weight = make(ue.MaterialExpressionSaturate, -600, y)
            pins.setdefault('saturate', _connect_expression(ue, one_minus, '', weight, SINGLE))
            weighted = make(ue.MaterialExpressionMultiply, -400, y)
            pins.setdefault('weightA', _connect_expression(ue, weight, '', weighted, ['A']))
            pins.setdefault('weightB', _connect_expression(ue, constant3(entry['rgb'], -600, y + 80), '', weighted, ['B']))
            if total is None:
                total = weighted
            else:
                summed = make(ue.MaterialExpressionAdd, -200, y)
                pins.setdefault('sumA', _connect_expression(ue, total, '', summed, ['A']))
                pins.setdefault('sumB', _connect_expression(ue, weighted, '', summed, ['B']))
                total = summed
        brightness = _brightness_chain(ue, material, pins, custom_data, make, constant, fix, -1600, -300)
        shaded = make(ue.MaterialExpressionMultiply, 200, 0)
        pins['shadedA'] = _connect_expression(ue, total, '', shaded, ['A'])
        pins['shadedB'] = _connect_expression(ue, brightness, '', shaded, ['B'])
        _finish(ue, material, pins, shaded, fix['garmentRoughness'], make, constant, fix)

    return build


def skin_builder(fix):
    tones = fix['skinTones']

    def build(ue, material, pins):
        make, constant, constant3, custom_data = _nodes(ue, material)
        # Complexion from custom data 0 (the gait phase hash, uniform 0..1): light -> mid -> dark.
        variation = custom_data(fix['variationCustomDataIndex'], 0.5, -1400, 0)
        doubled = make(ue.MaterialExpressionMultiply, -1200, 0)
        pins['doubledA'] = _connect_expression(ue, variation, '', doubled, ['A'])
        pins['doubledB'] = _connect_expression(ue, constant(2.0, -1400, 100), '', doubled, ['B'])
        first_alpha = make(ue.MaterialExpressionSaturate, -1000, 0)
        pins['saturate'] = _connect_expression(ue, doubled, '', first_alpha, SINGLE)
        shifted = make(ue.MaterialExpressionSubtract, -1000, 200)
        pins['shiftA'] = _connect_expression(ue, doubled, '', shifted, ['A'])
        pins['shiftB'] = _connect_expression(ue, constant(1.0, -1200, 300), '', shifted, ['B'])
        second_alpha = make(ue.MaterialExpressionSaturate, -800, 200)
        _connect_expression(ue, shifted, '', second_alpha, SINGLE)
        first = make(ue.MaterialExpressionLinearInterpolate, -600, 0)
        pins['lerpA'] = _connect_expression(ue, constant3(tones[0], -800, -100), '', first, ['A'])
        pins['lerpB'] = _connect_expression(ue, constant3(tones[1], -800, 0), '', first, ['B'])
        pins['lerpAlpha'] = _connect_expression(ue, first_alpha, '', first, ['Alpha'])
        second = make(ue.MaterialExpressionLinearInterpolate, -400, 0)
        _connect_expression(ue, first, '', second, ['A'])
        _connect_expression(ue, constant3(tones[2], -600, 300), '', second, ['B'])
        _connect_expression(ue, second_alpha, '', second, ['Alpha'])
        _finish(ue, material, pins, second, fix['skinRoughness'], make, constant, fix)

    return build


def wrap_builder(fix):
    tones = fix['wrapTones']

    def build(ue, material, pins):
        make, constant, constant3, custom_data = _nodes(ue, material)
        variation = custom_data(fix['variationCustomDataIndex'], 0.5, -1000, 0)
        lerp = make(ue.MaterialExpressionLinearInterpolate, -600, 0)
        pins['lerpA'] = _connect_expression(ue, constant3(tones[0], -800, -100), '', lerp, ['A'])
        pins['lerpB'] = _connect_expression(ue, constant3(tones[1], -800, 100), '', lerp, ['B'])
        pins['lerpAlpha'] = _connect_expression(ue, variation, '', lerp, ['Alpha'])
        _finish(ue, material, pins, lerp, fix['wrapRoughness'], make, constant, fix)

    return build


def _verify_palette_material(ue, material, fix, tolerance):
    """Prove the saved graph carries the palette: every authored colour is a Constant3Vector in
    the asset, the tint node reads the right index with the sentinel default, and BaseColor is
    fed through a VertexInterpolator."""
    dump = _material_graph_dump(ue, material)
    problems = []
    wanted = [entry['rgb'] for entry in fix['garmentPalette']]
    have = dump.get('constant3Vectors', [])
    for rgb in wanted:
        if not any(all(abs(a - b) <= tolerance for a, b in zip(rgb, got)) for got in have):
            problems.append('palette colour %r missing from the graph' % (rgb,))
    custom = dump.get('perInstanceCustomDataNodes', [])
    sentinel = fix['sentinelDefaultTintIndex'] / float(len(wanted) - 1)
    if not any(n['dataIndex'] == fix['tintCustomDataIndex'] and _near(n['constDefaultValue'], sentinel, 1e-4) for n in custom):
        problems.append('no PerInstanceCustomData node reading index %d with sentinel %.4f' % (fix['tintCustomDataIndex'], sentinel))
    if not any(n['dataIndex'] == fix['variationCustomDataIndex'] for n in custom):
        problems.append('no PerInstanceCustomData node reading index %d' % fix['variationCustomDataIndex'])
    if fix['readThroughVertexInterpolator'] and dump.get('baseColorInputClass') not in ('MaterialExpressionVertexInterpolator', None):
        problems.append('BaseColor input is %r, not the VertexInterpolator' % dump.get('baseColorInputClass'))
    if not dump['usedWithInstancedStaticMeshes']:
        problems.append('used_with_instanced_static_meshes is not set')
    dump['verified'] = not problems
    dump['problems'] = problems
    return dump


def _verify_simple_material(ue, material, fix, tones, tolerance):
    dump = _material_graph_dump(ue, material)
    problems = []
    have = dump.get('constant3Vectors', [])
    for rgb in tones:
        if not any(all(abs(a - b) <= tolerance for a, b in zip(rgb, got)) for got in have):
            problems.append('tone %r missing from the graph' % (rgb,))
    if not any(n['dataIndex'] == fix['variationCustomDataIndex'] for n in dump.get('perInstanceCustomDataNodes', [])):
        problems.append('no PerInstanceCustomData node reading index %d' % fix['variationCustomDataIndex'])
    if not dump['usedWithInstancedStaticMeshes']:
        problems.append('used_with_instanced_static_meshes is not set')
    dump['verified'] = not problems
    dump['problems'] = problems
    return dump


def _slot_kind(spec, index, slot_name, imported_name):
    """Which crowd material a mesh slot wants: by group word when the importer kept the OBJ
    group names, else by the frozen OBJ order when the slot count matches."""
    order = spec['objSlotOrder']
    lowered = (slot_name + '|' + imported_name).lower()
    for kind, words in order['groupWords'].items():
        if any(w in lowered for w in words):
            return kind, 'group-name'
    if 0 <= index < len(order['materials']):
        return order['materials'][index], 'obj-order'
    return 'CrowdRobe', 'fallback-robe'


# ==========================================================================
# Native entry
# ==========================================================================

def run():
    import unreal as ue

    spec = load_spec()
    fix = spec['fix']
    expected = spec['expected']
    verification = spec['verification']
    offline = offline_check(spec)

    dump_mode = _switch('CrowdTintDump')
    rebuild_probe = _switch('CrowdTintRebuildProbe')
    materials_only = _switch('CrowdTintMaterialsOnly')
    apply_mode = _switch('CrowdTintApply')
    verify_mode = _switch('CrowdTintVerify')
    if sum(1 for m in (dump_mode, materials_only, apply_mode, verify_mode) if m) != 1:
        raise RuntimeError('Pass exactly one of -CrowdTintDump, -CrowdTintMaterialsOnly, -CrowdTintApply, -CrowdTintVerify')
    mode = 'dump' if dump_mode else 'materials_only' if materials_only else 'apply' if apply_mode else 'verify'

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is running; use a dedicated editor process')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Unsaved packages present; run on a clean editor')
    if not ue.load_class(None, spec['crowdClass']):
        raise RuntimeError('Compiled MikdashRuntime with AMikdashCrowdField is not loaded')
    if spec['targetMap'] in spec['protectedMaps']:
        raise RuntimeError('Refusing to touch a protected map')

    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_dir = ROOT / spec['receiptFolder']
    receipt_dir.mkdir(parents=True, exist_ok=True)
    prefix = spec['applyReceiptPrefix'] if mode in ('apply', 'materials_only') else spec['dumpReceiptPrefix']
    receipt_path = receipt_dir / (prefix + mode + '-' + stamp + '.json')
    map_file = ROOT / spec['targetMapFile']
    namespace = fix['materialNamespace']

    receipt = dict(status='started', mode=mode, stamp=stamp, spec=str(SPEC_PATH.relative_to(ROOT)), specSha256=sha(SPEC_PATH),
                   offline=offline, mapBeforeSha256=sha(map_file), mapSaved=False, materialPins={},
                   honesty=['No render, PIE, cook or packaged run is claimed by this script.',
                            'Material readback is graph inspection and property readback; visual acceptance is a real-RHI capture.',
                            'The GPU bob is not carried by the palette materials; the actor keeps its CPU bob.'])

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

    write()
    checkpoint = None
    try:
        # ---- materials (apply / materials_only create; dump / verify only inspect)
        if mode in ('apply', 'materials_only'):
            materials = {}
            builders = {'CrowdRobe': garment_builder(fix), 'CrowdSkin': skin_builder(fix), 'CrowdWrap': wrap_builder(fix)}
            created_flags = {}
            for kind in ('CrowdRobe', 'CrowdSkin', 'CrowdWrap'):
                material, created = _build_material(ue, tools, assets, namespace, fix['assets'][kind], builders[kind], receipt['materialPins'])
                materials[kind] = material
                created_flags[kind] = created
            receipt['materials'] = {}
            tol = verification['colourTolerance']
            receipt['materials']['CrowdRobe'] = _verify_palette_material(ue, materials['CrowdRobe'], fix, tol)
            receipt['materials']['CrowdSkin'] = _verify_simple_material(ue, materials['CrowdSkin'], fix, fix['skinTones'], tol)
            receipt['materials']['CrowdWrap'] = _verify_simple_material(ue, materials['CrowdWrap'], fix, fix['wrapTones'], tol)
            for kind, entry in receipt['materials'].items():
                entry['created'] = created_flags[kind]
                if not entry['verified']:
                    raise RuntimeError('%s did not verify: %r' % (kind, entry['problems']))
            receipt['status'] = 'materials_verified'
            write()
            if mode == 'materials_only':
                receipt['status'] = 'materials_only_complete_map_unchanged'
                return receipt

        # ---- map load (all modes)
        target = spec['targetMap']
        if editor.get_editor_world().get_outermost().get_name() != target:
            if not levels.load_level(target):
                raise RuntimeError('Target map load failed')
        if editor.get_editor_world().get_outermost().get_name() != target:
            raise RuntimeError('Unexpected editor world')

        field = _find_field(ue, spec)
        class_props = _resolve_properties(ue.MikdashCrowdField, ['GarmentPaletteSize', 'CrowdMaterialOverride', 'BobAmplitudeCm', 'EditorPreviewCount', 'CrowdCount'], 'MikdashCrowdField')
        components, basis = _pose_components(ue, field, expected['poseComponents'])
        sample = verification['customDataSample']

        def actor_state():
            return dict(name=field.get_name(), label=field.get_actor_label(),
                        garmentPaletteSize=int(field.get_editor_property(class_props['GarmentPaletteSize'])),
                        crowdMaterialOverride=_path(field.get_editor_property(class_props['CrowdMaterialOverride'])),
                        bobAmplitudeCm=float(field.get_editor_property(class_props['BobAmplitudeCm'])),
                        editorPreviewCount=int(field.get_editor_property(class_props['EditorPreviewCount'])),
                        crowdCount=int(field.get_editor_property(class_props['CrowdCount'])),
                        crowdSummary=str(field.call_method('GetCrowdSummary')),
                        componentBasis=basis,
                        components=[_component_dump(ue, c, expected['numCustomDataFloats'], sample) for c in components])

        receipt['savedState'] = actor_state()
        existing_ns = expected['existingMaterialNamespace']
        receipt['existingMaterials'] = {}
        for name in expected['existingMaterials']:
            material = ue.load_asset(existing_ns + '/' + name)
            receipt['existingMaterials'][name] = _material_graph_dump(ue, material) if material else 'missing'
        write()

        if mode == 'dump':
            if rebuild_probe:
                field.call_method('BuildEditorPreview')
                receipt['rebuildProbe'] = actor_state()
                receipt['rebuildProbeNote'] = 'BuildEditorPreview ran in memory only; nothing was saved.'
            receipt['status'] = 'dump_complete_nothing_saved'
            return receipt

        if mode == 'verify':
            problems = []
            state = receipt['savedState']
            if state['garmentPaletteSize'] != fix['garmentPaletteSize']:
                problems.append('garmentPaletteSize %d' % state['garmentPaletteSize'])
            for comp in state['components']:
                for slot in comp['slots']:
                    kind, _basis = _slot_kind(spec, slot['index'], slot['slotName'], slot['importedSlotName'])
                    want = namespace + '/' + fix['assets'][kind]
                    if slot['componentMaterial'] != want:
                        problems.append('%s slot %d is %r, want %r' % (comp['name'], slot['index'], slot['componentMaterial'], want))
                if comp.get('tintDistinctValues', 0) < min(fix['garmentPaletteSize'], 4):
                    problems.append('%s tint channel has %r distinct values' % (comp['name'], comp.get('tintDistinctValues')))
            receipt['materials'] = {}
            tol = verification['colourTolerance']
            for kind in ('CrowdRobe', 'CrowdSkin', 'CrowdWrap'):
                material = ue.load_asset(namespace + '/' + fix['assets'][kind])
                if not material:
                    problems.append('%s material missing' % kind)
                    continue
                if kind == 'CrowdRobe':
                    receipt['materials'][kind] = _verify_palette_material(ue, material, fix, tol)
                else:
                    receipt['materials'][kind] = _verify_simple_material(ue, material, fix, fix['skinTones'] if kind == 'CrowdSkin' else fix['wrapTones'], tol)
                if not receipt['materials'][kind]['verified']:
                    problems.append('%s: %r' % (kind, receipt['materials'][kind]['problems']))
            receipt['verifyProblems'] = problems
            receipt['status'] = 'verify_passed_nothing_saved' if not problems else 'verify_failed_nothing_saved'
            if problems:
                raise RuntimeError('Verify failed: %r' % problems)
            return receipt

        # ---- apply: checkpoint, then the map change
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / 'BeforeCrowdTintFix.umap')
        if sha(checkpoint / 'BeforeCrowdTintFix.umap') != receipt['mapBeforeSha256']:
            raise RuntimeError('Checkpoint copy hash mismatch')
        receipt['checkpoint'] = str(checkpoint)
        write()

        field.modify()
        applied = []
        for component in components:
            component.modify()
            mesh = component.get_editor_property('static_mesh')
            if not mesh:
                raise RuntimeError('%s has no static mesh' % component.get_name())
            statics = list(mesh.get_editor_property('static_materials'))
            if len(statics) != expected['meshSlotsPerPose']:
                raise RuntimeError('%s has %d slots, expected %d' % (component.get_name(), len(statics), expected['meshSlotsPerPose']))
            for index, entry in enumerate(statics):
                slot_name = str(entry.get_editor_property('material_slot_name'))
                imported = str(entry.get_editor_property('imported_material_slot_name'))
                kind, how = _slot_kind(spec, index, slot_name, imported)
                component.set_material(index, materials[kind])
                got = _path(component.get_material(index))
                want = namespace + '/' + fix['assets'][kind]
                if got != want:
                    raise RuntimeError('%s slot %d read back %r after writing %r' % (component.get_name(), index, got, want))
                applied.append(dict(component=component.get_name(), slot=index, slotName=slot_name, kind=kind, basis=how, material=got))
        receipt['appliedSlots'] = applied
        _set_and_verify(field, class_props['GarmentPaletteSize'], int(fix['garmentPaletteSize']))
        if field.get_editor_property(class_props['CrowdMaterialOverride']):
            raise RuntimeError('CrowdMaterialOverride is set; it would override the per-slot materials')

        # Rebuild the serialised editor preview so the saved custom data carries the new
        # palette size (tint = index / 7), then save.
        field.call_method('BuildEditorPreview')
        receipt['preSaveState'] = actor_state()
        preview = receipt['preSaveState']
        if sum(c['instanceCount'] for c in preview['components']) != preview['editorPreviewCount']:
            raise RuntimeError('Editor preview instance count differs from EditorPreviewCount')
        for comp in preview['components']:
            if comp['numCustomDataFloats'] != expected['numCustomDataFloats'] or not comp['customDataLengthConsistent']:
                raise RuntimeError('%s custom data stride/length wrong before save' % comp['name'])
        field.modify()
        saved = bool(levels.save_current_level())
        after = sha(map_file)
        if not saved and after == receipt['mapBeforeSha256']:
            raise RuntimeError('Level save failed and the .umap is unchanged')
        receipt.update(mapSaved=True, saveReturnedTrue=saved, mapAfterSha256=after, status='saved_reopen_pending')
        write()

        # ---- reopen and read back
        if not levels.load_level(target) or editor.get_editor_world().get_outermost().get_name() != target:
            raise RuntimeError('Reopen failed')
        field = _find_field(ue, spec)
        components, basis = _pose_components(ue, field, expected['poseComponents'])
        receipt['postReopen'] = actor_state()
        problems = []
        state = receipt['postReopen']
        if state['garmentPaletteSize'] != fix['garmentPaletteSize']:
            problems.append('garmentPaletteSize %d' % state['garmentPaletteSize'])
        expected_tints_set = set('%.3f' % t for t in expected_tints(fix['garmentPaletteSize']))
        for comp in state['components']:
            for slot in comp['slots']:
                kind, _basis = _slot_kind(spec, slot['index'], slot['slotName'], slot['importedSlotName'])
                want = namespace + '/' + fix['assets'][kind]
                if slot['componentMaterial'] != want:
                    problems.append('%s slot %d is %r, want %r' % (comp['name'], slot['index'], slot['componentMaterial'], want))
            if comp['numCustomDataFloats'] != expected['numCustomDataFloats']:
                problems.append('%s NumCustomDataFloats %d' % (comp['name'], comp['numCustomDataFloats']))
            seen = set(comp.get('channel1Histogram', {}).keys())
            if not seen or not seen.issubset(expected_tints_set):
                problems.append('%s tint values %r not within %r' % (comp['name'], sorted(seen), sorted(expected_tints_set)))
        receipt['readbackProblems'] = problems
        if problems:
            raise RuntimeError('Readback mismatch after reopen: %r' % problems)
        receipt['status'] = 'crowd_tint_fix_saved_reopened_visual_review_pending'
        receipt['revert'] = ('Copy %s\\BeforeCrowdTintFix.umap back over %s (sha %s). The three review materials can stay; nothing references them once the map is reverted.'
                             % (str(checkpoint), spec['targetMapFile'], receipt['mapBeforeSha256']))
    except Exception as exc:
        receipt.update(status='failed_checkpoint_available' if checkpoint else 'failed_before_map_change', failure=repr(exc))
        raise
    finally:
        receipt['mapAfterSha256'] = sha(map_file)
        receipt['mapBytesChanged'] = receipt['mapAfterSha256'] != receipt['mapBeforeSha256']
        if mode in ('dump', 'verify', 'materials_only') and receipt['mapBytesChanged']:
            receipt['status'] = 'FAILED_read_only_mode_changed_the_map'
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

"""Guarded sanctuary gold / highlight balance for the combined IntegratedReviewV2 map.

Answers the 20260907T214622Z renders (d_heikhal_west_vessels, e_kodesh_aron_keruvim): the Kodesh
partition blows out to white, the gold floor and walls read as flat synthetic yellow, the 250 cm
frieze panels repeat mechanically and the highlights are harsh. Every number comes from
Scripts/release_sanctuary_balance.spec.json; the design notes live in
SourceAssets/sanctuary-detail/BalanceV1/README.md. Astra's lighting (morning sun, EV 0..14
histogram exposure, fill, fog) is refined, never undone.

What it does, in order (all discovery and guards BEFORE any mutation):
  1. frieze    M_KeruvFriezeV2 / _Displaced: gold base colour, roughness lerp 0.50 (ground) -> 0.42
               (raised relief), plus world-space Perlin variation (10 m features, roughness +-0.06,
               tint +-3 percent) so neighbouring panels are not identical.
  2. veneer    the 'Sanctuary finishes' Review_* veneer material (M_Sanctuary_gold): gold colour,
               roughness 0.34 -> 0.46, same variation.
  3. vessels   M_AronStudyV3_Gold, M_HeikhalKeilim_Gold, M_KeruvimStudyGold (only those used by a
               component in the map): gold colour, roughness 0.28 -> 0.42, no variation.
  4. partition the three measured Kodesh partition pieces whose bounds form the X -5600 face
               (SM_0142/0143 shoulders, SM_0144 lintel) leave MI_PBR_GoldHammered for the veneer gold
               (book: gold lining on all Heikhal/Kodesh walls, 41:16-17).
  5. floor     MI_PBR_GoldFloor: RoughnessScale 1.1 -> 1.755 (= 0.5 / measured ARM roughness mean
               0.2849, so the floor's mean roughness becomes 0.5), Tint -> gold, Metallic 0.8 -> 1.
  6. lighting  RELEASE_HeikhalEntranceFill 25,000 cd -> 15,000 cd (threshold 15,000); the
               PostProcessVolume gets bilateral local exposure (highlight contrast 0.8), film white
               clip 0.04 -> 0.02 and shoulder 0.26 -> 0.30. Exposure bounds stay EV 0..14.
  7. save the edited assets and the map, reopen, read everything back numerically, write the receipt
     to SourceAssets/sanctuary-detail/BalanceV1/native-balance-<stamp>.json.

Commandlet invocation (serial; never while another native job or the GUI editor holds the map):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_sanctuary_balance.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Sanctuary-Balance-01.log"

Optional switches (engine command line):
  -BalanceDryRun          guards, discovery and before-value readback only; no checkpoint, no mutation;
                          if a saved apply receipt exists its after-values are compared with the live
                          state (fresh-process verification). Receipt native-balance-dryrun-<stamp>.json.
  -BalanceOnly=<groups>   comma-separated subset of frieze,veneer,vessels,partition,floor,lighting.
  -BalanceRevert[=<receipt.json>]
                          restore the checkpointed material/instance .uasset bytes (verified by SHA-256
                          before the map loads), restore every map property from the receipt's
                          before-values, save, reopen, read back; native-balance-revert-<stamp>.json.

Offline (no engine):  python Scripts/release_sanctuary_balance.py  -> offline_check(): asset files on
                      disk, manifest bounds of the partition pieces, ARM texture hash and roughness-scale
                      arithmetic, lighting receipt values, and the planned before/after table.

Safety model (release_place_assets.py / release_lighting_polish.py pattern):
  * Refuses to run with the wrong project directory, a game world, dirty packages, a loaded world that
    is not the combined map, a missing/unexpected material graph, a material already carrying this
    pass (BaseColor fed by a Multiply), or a saved unreverted apply receipt.
  * Copies Walkthrough.umap (and One-File-Per-Actor folders) AND every material/instance .uasset it
    will edit to ReviewCheckpoints/SanctuaryBalance-<stamp>/ before any mutation; copies verified.
  * UE 5.8 pitfalls honoured: MaterialEditingLibrary setters return False even on success, so every
    set is verified by readback; enum ints are never used (member names only, EnumBase has no int());
    the texture coordinate pin is 'UVs' (not touched here); whole-scene inventory is taken once per
    phase and keyed by component path.
  * Unrelated actors (all of them; nothing moves) are snapshotted and must be numerically unchanged
    before save and after reopen; the whole-scene material inventory may differ only on the three
    partition components. Protected maps/assets are hashed before and after.
  * The receipt is written at start, after each stage and in finally, preserving partial state.
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_sanctuary_balance.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'

sys.path.insert(0, str(ROOT / 'Scripts'))
import release_lighting_polish as lp  # noqa: E402  (helpers only: guards, typed values, checkpoint, save/reopen)

APPLIED_STATUS = 'sanctuary_balance_saved_reopened_visual_acceptance_pending'
REVERTED_STATUS = 'sanctuary_balance_reverted_saved_reopened'
DRY_RUN_STATUS = 'dry_run_no_mutation_map_unchanged'
GROUPS = ('frieze', 'veneer', 'vessels', 'partition', 'floor', 'lighting')
MATERIAL_PROPERTIES = ('MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS')


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so offline_check() runs anywhere
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


def normalise_groups(groups):
    if isinstance(groups, str):
        groups = groups.split(',')
    wanted = [g.strip().lower() for g in groups if g.strip()]
    unknown = [g for g in wanted if g not in GROUPS]
    if unknown:
        raise RuntimeError('Unknown balance groups %s; valid: %s' % (unknown, list(GROUPS)))
    if not wanted:
        raise RuntimeError('No balance groups requested')
    return tuple(g for g in GROUPS if g in wanted)


def veneer_material(spec):
    return spec['veneer']['expectedMaterial']


def latest_lighting_receipt(spec):
    folder = ROOT / spec['lightingReceiptFolder']
    for path in sorted(folder.glob(spec['lightingApplyPrefix'] + '*.json'), reverse=True):
        receipt = json.loads(path.read_text(encoding='utf-8-sig'))
        if receipt.get('mapSaved') and receipt.get('status') == spec['lightingAppliedStatus'] and not receipt.get('revertedBy'):
            return path, receipt
    return None, None


def fill_intensity_from_receipt(receipt):
    if not receipt:
        return None
    for change in receipt.get('changes', []):
        if change.get('target') == 'fill' and change.get('property') == 'intensity' and change.get('applied'):
            after = change.get('afterReopen') or change.get('after') or {}
            return after.get('value')
    return None


def latest_apply_receipt(spec, require=True):
    folder = ROOT / spec['receiptFolder']
    if folder.exists():
        for path in sorted(folder.glob(spec['receiptPrefix'] + '*.json'), reverse=True):
            receipt = json.loads(path.read_text(encoding='utf-8-sig'))
            if receipt.get('mapSaved') and receipt.get('status') == APPLIED_STATUS and not receipt.get('revertedBy'):
                return path, receipt
    if require:
        raise RuntimeError('No saved, unreverted apply receipt found in ' + str(folder))
    return None, None


def planned_table(spec, fill_before=None):
    """Human-readable before/after rows; 'before' values are the receipt/spec expectations, verified live."""
    gold = spec['gold']['linear']
    rows = []
    for material in spec['frieze']['materials']:
        exp = spec['frieze']['expectedBefore']
        rows.append({'group': 'frieze', 'target': material, 'property': 'BaseColor', 'before': exp['baseColor'], 'after': gold})
        rows.append({'group': 'frieze', 'target': material, 'property': 'Roughness lerp A/B (height 0 / 1)', 'before': [exp['roughnessAtHeight0'], exp['roughnessAtHeight1']],
                     'after': [spec['frieze']['roughnessAtHeight0'], spec['frieze']['roughnessAtHeight1']]})
        rows.append({'group': 'frieze', 'target': material, 'property': 'world-space variation', 'before': 'none',
                     'after': 'roughness +-%.2f, tint +-%.0f%% at %.0f m' % (spec['variation']['roughnessAmplitude'], spec['variation']['tintAmplitude'] * 100, spec['variation']['scaleCm'] / 100)})
    exp = spec['veneer']['expectedBefore']
    rows.append({'group': 'veneer', 'target': veneer_material(spec), 'property': 'BaseColor', 'before': exp['baseColor'], 'after': gold})
    rows.append({'group': 'veneer', 'target': veneer_material(spec), 'property': 'Roughness', 'before': exp['roughness'], 'after': spec['veneer']['roughness']})
    rows.append({'group': 'veneer', 'target': veneer_material(spec), 'property': 'world-space variation', 'before': 'none',
                 'after': 'roughness +-%.2f, tint +-%.0f%% at %.0f m' % (spec['variation']['roughnessAmplitude'], spec['variation']['tintAmplitude'] * 100, spec['variation']['scaleCm'] / 100)})
    exp = spec['vessels']['expectedBefore']
    for material in spec['vessels']['materials']:
        rows.append({'group': 'vessels', 'target': material, 'property': 'BaseColor', 'before': exp['baseColor'], 'after': gold})
        rows.append({'group': 'vessels', 'target': material, 'property': 'Roughness', 'before': exp['roughness'], 'after': spec['vessels']['roughness']})
    for mesh in spec['partition']['expectedMeshes']:
        rows.append({'group': 'partition', 'target': mesh.rsplit('/', 1)[1], 'property': 'slot 0 material', 'before': spec['partition']['expectedMaterialBefore'], 'after': veneer_material(spec)})
    floor = spec['floor']
    rows.append({'group': 'floor', 'target': floor['instance'], 'property': 'RoughnessScale (mean roughness)', 'before': [floor['expectedBefore']['RoughnessScale'], round(floor['expectedBefore']['RoughnessScale'] * floor['roughnessSource']['measuredMean01'], 3)],
                 'after': [floor['roughnessScale'], round(floor['roughnessScale'] * floor['roughnessSource']['measuredMean01'], 3)]})
    if floor['alsoTintAndMetallic']:
        rows.append({'group': 'floor', 'target': floor['instance'], 'property': 'Tint', 'before': floor['expectedBefore']['Tint'], 'after': gold + [1.0]})
        rows.append({'group': 'floor', 'target': floor['instance'], 'property': 'Metallic', 'before': floor['expectedBefore']['Metallic'], 'after': floor['metallic']})
    fill = spec['lighting']['fill']
    rows.append({'group': 'lighting', 'target': fill['label'], 'property': 'intensity (cd)', 'before': fill_before, 'after': fill['intensityCd'] if (fill_before is None or fill_before > fill['intensityThresholdCd']) else 'unchanged (<= threshold)'})
    for prop, raw in spec['lighting']['postProcess']['properties'].items():
        if prop.startswith('override_'):
            continue
        rows.append({'group': 'lighting', 'target': 'PostProcessVolume.settings', 'property': prop, 'before': 'live readback', 'after': raw})
    return rows


def offline_check(spec=None):
    """Consistency checks that need no engine. Raises on the first failure."""
    spec = spec or load_spec()
    report = {'assetFilesChecked': 0, 'missingFiles': []}
    assets = list(spec['frieze']['materials']) + [veneer_material(spec)] + list(spec['vessels']['materials']) + [spec['floor']['instance'], spec['floor']['expectedParent'],
                                                                                                                  spec['floor']['expectedArmTexture'], spec['partition']['expectedMaterialBefore']]
    assets += list(spec['partition']['expectedMeshes']) + list(spec.get('protectedAssets', []))
    for asset in assets:
        report['assetFilesChecked'] += 1
        if not disk_path(asset).exists():
            report['missingFiles'].append(asset)
    for asset in spec['protectedMaps']:
        report['assetFilesChecked'] += 1
        if not disk_path(asset, 'umap').exists():
            report['missingFiles'].append(asset)
    if not (ROOT / spec['targetMapFile']).exists():
        report['missingFiles'].append(spec['targetMapFile'])
    if report['missingFiles']:
        raise RuntimeError('Missing files on disk: ' + ', '.join(report['missingFiles']))

    gold = spec['gold']['linear']
    if len(gold) != 3 or not all(0.0 <= c <= 1.0 for c in gold) or not (gold[0] >= gold[1] >= gold[2]):
        raise RuntimeError('Gold colour must be three linear components with r >= g >= b: %r' % (gold,))
    frieze = spec['frieze']
    if not (0.3 <= frieze['roughnessAtHeight1'] < frieze['roughnessAtHeight0'] <= 0.6):
        raise RuntimeError('Frieze roughness lerp must keep the raised relief more polished than the ground, within 0.3..0.6')
    for key in ('veneer', 'vessels'):
        if not 0.3 <= spec[key]['roughness'] <= 0.6:
            raise RuntimeError('%s roughness outside 0.3..0.6' % key)
    variation = spec['variation']
    if not 800.0 <= variation['scaleCm'] <= 1200.0:
        raise RuntimeError('Variation scale must be 8..12 m')
    if not 0.0 < variation['roughnessAmplitude'] <= 0.1 or not 0.0 < variation['tintAmplitude'] <= 0.05:
        raise RuntimeError('Variation amplitudes outside the reviewed range')
    lo, hi = variation['roughnessClamp']
    if not 0.0 <= lo < hi <= 1.0:
        raise RuntimeError('Roughness clamp malformed')

    # Partition pieces: manifest bounds must form the X -5600 face inside the Heikhal envelope.
    manifest = {m['assetName']: m for m in json.loads((ROOT / 'SourceAssets' / 'architecture-manifest.json').read_text(encoding='utf-8-sig'))['meshes']}
    partition = spec['partition']
    faces = []
    for mesh in partition['expectedMeshes']:
        name = mesh.rsplit('/', 1)[1].replace('architecture_', '', 1)
        entry = manifest.get(name)
        if entry is None:
            raise RuntimeError('Partition mesh not in the architecture manifest: ' + name)
        box = entry['expectedBoundsUnrealCm']
        if abs(box['max'][0] - partition['faceX']) > partition['faceToleranceCm'] or abs(box['min'][0] - partition['backX']) > partition['faceToleranceCm']:
            raise RuntimeError('%s does not span X %s..%s: %r' % (name, partition['backX'], partition['faceX'], box))
        if box['min'][1] < -partition['yHalfWidthCm'] - 0.5 or box['max'][1] > partition['yHalfWidthCm'] + 0.5 or box['min'][2] < partition['zRange'][0] - 0.5 or box['max'][2] > partition['zRange'][1] + 0.5:
            raise RuntimeError('%s leaves the Heikhal envelope: %r' % (name, box))
        faces.append({'mesh': name, 'sourceName': entry['sourceName'], 'boundsCm': box})
    report['partitionPieces'] = faces

    # Floor: frozen ARM texture and the roughness-scale arithmetic.
    floor = spec['floor']
    source = floor['roughnessSource']
    arm_file = ROOT / source['file']
    if not arm_file.exists():
        raise RuntimeError('ARM source texture missing: ' + str(arm_file))
    arm_sha = sha256_of(arm_file)
    if arm_sha != source['sha256']:
        raise RuntimeError('ARM source texture hash differs from the measured file; re-measure the roughness mean')
    expected_scale = floor['targetRoughness'] / source['measuredMean01']
    if abs(expected_scale - floor['roughnessScale']) > 0.005:
        raise RuntimeError('roughnessScale %.4f does not equal targetRoughness / measuredMean01 = %.4f' % (floor['roughnessScale'], expected_scale))
    if not 1.0 <= floor['roughnessScale'] <= 3.0:
        raise RuntimeError('roughnessScale outside 1..3')
    report['floor'] = {'armSha256': arm_sha, 'roughnessScale': floor['roughnessScale'],
                       'meanRoughnessAfter': round(floor['roughnessScale'] * source['measuredMean01'], 4),
                       'p10p90After': [round(floor['roughnessScale'] * source['measuredPercentiles01']['p10'], 3), round(floor['roughnessScale'] * source['measuredPercentiles01']['p90'], 3)]}

    # Lighting: the fill value the plan reacts to, and property encodings.
    lighting_path, lighting_receipt = latest_lighting_receipt(spec)
    fill_before = fill_intensity_from_receipt(lighting_receipt)
    report['lightingReceipt'] = {'path': str(lighting_path) if lighting_path else None, 'fillIntensityCd': fill_before,
                                 'fillReductionPlanned': fill_before is not None and fill_before > spec['lighting']['fill']['intensityThresholdCd']}
    pp = spec['lighting']['postProcess']
    for prop, raw in pp['properties'].items():
        if isinstance(raw, dict) and not set(raw) & {'$enum', '$linearColor', '$color', '$asset'}:
            raise RuntimeError('postProcess.%s: unknown value encoding' % prop)
    missing = [p for p in pp['required'] if p not in pp['properties']]
    if missing:
        raise RuntimeError('postProcess required properties missing: %s' % missing)
    if not 0.0 < spec['lighting']['fill']['intensityCd'] <= spec['lighting']['fill']['intensityThresholdCd']:
        raise RuntimeError('Fill target must be positive and not above the threshold')

    report['targetMapSha256'] = sha256_of(ROOT / spec['targetMapFile'])
    report['targetMapMatchesLastKnown'] = report['targetMapSha256'] == spec['lastKnownMapSha256']
    report['plannedTable'] = planned_table(spec, fill_before)
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side
# --------------------------------------------------------------------------

def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _box(origin, extent):
    return {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z], 'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}


def _colour_list(colour):
    return [float(colour.r), float(colour.g), float(colour.b), float(colour.a)]


def _close(a, b, tolerance):
    return all(abs(float(x) - float(y)) <= tolerance for x, y in zip(a, b)) and len(a) == len(b)


def _enum(ue, enum_name, *candidates):
    enum = getattr(ue, enum_name)
    for name in candidates:
        if hasattr(enum, name):
            return getattr(enum, name), name
    raise RuntimeError('%s has none of %s' % (enum_name, candidates))


class Balance:
    """Engine handles, whole-scene inventory, material graph editing and the receipt."""

    def __init__(self, ue, spec):
        self.ue = ue
        self.spec = spec
        self.ml = ue.MaterialEditingLibrary
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.polish = lp.Polish(ue, spec)       # guard_world, set_prop, readback, snapshot_unrelated, save_and_reopen
        self.receipt = None
        self.receipt_path = None
        self.inventory = None

    # -- receipt -----------------------------------------------------------

    def write_receipt(self):
        # lp.Polish helpers (set_prop, save_and_reopen) write into their own receipt handle: keep both bound to ours.
        self.polish.receipt = self.receipt
        self.polish.receipt_path = self.receipt_path
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n', encoding='utf-8')

    def read_cvars(self):
        ue = self.ue
        return {'r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange': ue.SystemLibrary.get_console_variable_int_value('r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange'),
                'r.EyeAdaptation.LensAttenuation': ue.SystemLibrary.get_console_variable_float_value('r.EyeAdaptation.LensAttenuation'),
                'note': 'Exposure bounds are read back raw; with the range flag at 0 the fields are scene luminance (1 = EV 0, 16384 = EV 14).'}

    # -- guards ------------------------------------------------------------

    def guard_before_load(self):
        ue = self.ue
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
        if self.polish.editor.get_game_world():
            raise RuntimeError('A game world is active; never mutate during play')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present before loading the target; refusing to discard unsaved work')

    def load_target(self):
        self.polish.guard_world(True)
        self.world = self.polish.world

    # -- inventory (one pass; keyed by component path) ---------------------

    def take_inventory(self):
        ue = self.ue
        rows = {}
        for actor in self.polish.actors.get_all_level_actors():
            label = actor.get_actor_label()
            folder = str(actor.get_folder_path())
            tags = [str(t) for t in actor.get_editor_property('tags')]
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                mesh = _asset_path(component.get_editor_property('static_mesh'))
                count = component.get_num_materials()
                materials = [_asset_path(component.get_material(i)) for i in range(count)]
                overrides = [_asset_path(m) for m in component.get_editor_property('override_materials')]
                rows[component.get_path_name()] = {'component': component, 'actor': actor, 'actorName': actor.get_name(), 'label': label, 'folder': folder, 'tags': tags,
                                                   'mesh': mesh, 'materials': materials, 'overrides': overrides, 'bounds': None}
        self.inventory = rows
        return rows

    def component_bounds(self, row):
        """World AABB of the component (lazy, cached in the inventory row). Bounds is a read-only UPROPERTY of SceneComponent;
        the actor AABB is the fallback (every measured architecture actor is a single-component StaticMeshActor)."""
        if row['bounds'] is None:
            try:
                bounds = row['component'].get_editor_property('bounds')
                row['bounds'] = _box(bounds.origin, bounds.box_extent)
                row['boundsSource'] = 'component_bounds'
            except Exception:
                origin, extent = row['actor'].get_actor_bounds(False)
                row['bounds'] = _box(origin, extent)
                row['boundsSource'] = 'actor_bounds_fallback'
        return row['bounds']

    def material_signature(self):
        return {path: tuple(row['materials']) for path, row in self.inventory.items()}

    def components_using(self, material_path):
        return [row for row in self.inventory.values() if material_path in row['materials']]

    # -- material graph reading ----------------------------------------------

    def input_node(self, material, prop_name):
        return self.ml.get_material_property_input_node(material, getattr(self.ue.MaterialProperty, prop_name))

    def describe_node(self, node):
        ue = self.ue
        if node is None:
            return {'class': None}
        info = {'class': node.get_class().get_name()}
        if isinstance(node, ue.MaterialExpressionConstant3Vector):
            info['constant'] = _colour_list(node.get_editor_property('constant'))
        elif isinstance(node, ue.MaterialExpressionConstant):
            info['r'] = float(node.get_editor_property('r'))
        elif isinstance(node, ue.MaterialExpressionLinearInterpolate):
            info['constA'] = float(node.get_editor_property('const_a'))
            info['constB'] = float(node.get_editor_property('const_b'))
        elif isinstance(node, ue.MaterialExpressionClamp):
            info['minDefault'] = float(node.get_editor_property('min_default'))
            info['maxDefault'] = float(node.get_editor_property('max_default'))
        return info

    def describe_material(self, material):
        record = {'asset': _asset_path(material), 'class': material.get_class().get_name(), 'inputs': {}}
        for prop_name in MATERIAL_PROPERTIES:
            node = self.input_node(material, prop_name)
            record['inputs'][prop_name] = self.describe_node(node)
        try:
            record['expressionCount'] = int(self.ml.get_num_material_expressions(material))
        except Exception as error:
            record['expressionCount'] = 'unavailable: %r' % (error,)
        return record

    def upstream_constants(self, material, node, depth=0):
        """Classes of the expressions feeding `node` (verification that the original constants survive)."""
        if node is None or depth > 6:
            return []
        try:
            inputs = self.ml.get_inputs_for_material_expression(material, node)
        except Exception:
            return []
        out = []
        for child in inputs:
            if child is None:
                continue
            out.append(self.describe_node(child))
            out += self.upstream_constants(material, child, depth + 1)
        return out

    def load_material(self, path, expect_instance=False):
        ue = self.ue
        obj = ue.load_asset(path)
        wanted = ue.MaterialInstanceConstant if expect_instance else ue.Material
        if not isinstance(obj, wanted):
            raise RuntimeError('%s did not load as %s: %r' % (path, wanted.__name__, obj))
        return obj

    def check_gold_material(self, material, cfg_roughness_node, label, strict=True):
        """Guard: the graph is the plain study graph (Constant3Vector -> BaseColor, Constant -> Metallic, expected node -> Roughness).
        strict=False (fresh-process verification of an applied pass) only reads the nodes."""
        ue = self.ue
        colour = self.input_node(material, 'MP_BASE_COLOR')
        metallic = self.input_node(material, 'MP_METALLIC')
        rough = self.input_node(material, 'MP_ROUGHNESS')
        if not strict:
            return colour, metallic, rough
        if isinstance(colour, ue.MaterialExpressionMultiply):
            raise RuntimeError('%s already carries the balance pass (BaseColor fed by a Multiply); run -BalanceRevert first' % label)
        if not isinstance(colour, ue.MaterialExpressionConstant3Vector):
            raise RuntimeError('%s BaseColor input is %s, not Constant3Vector' % (label, colour.get_class().get_name() if colour else None))
        if metallic is not None and not isinstance(metallic, ue.MaterialExpressionConstant):
            raise RuntimeError('%s Metallic input is %s, not Constant' % (label, metallic.get_class().get_name()))
        if rough is None or rough.get_class().get_name() != cfg_roughness_node:
            raise RuntimeError('%s Roughness input is %s, expected %s' % (label, rough.get_class().get_name() if rough else None, cfg_roughness_node))
        return colour, metallic, rough

    # -- material graph editing ---------------------------------------------

    def adjust_gold_material(self, material, group_cfg, record, with_variation):
        """Set gold colour / metallic / roughness on the plain study graph and optionally add the world-space variation."""
        ue = self.ue
        ml = self.ml
        spec = self.spec
        gold = spec['gold']['linear']
        colour, metallic, rough = self.check_gold_material(material, group_cfg['expectedRoughnessNode'], record['asset'])
        record['before'] = self.describe_material(material)
        record['nodesAdded'] = []
        record['connections'] = []
        record['propertySets'] = []

        def set_and_verify(node, prop, value, compare):
            before = node.get_editor_property(prop)
            node.set_editor_property(prop, value)
            after = node.get_editor_property(prop)
            ok = compare(after, value)
            record['propertySets'].append({'node': node.get_class().get_name(), 'property': prop, 'before': _colour_list(before) if isinstance(before, ue.LinearColor) else float(before),
                                           'after': _colour_list(after) if isinstance(after, ue.LinearColor) else float(after), 'matches': ok})
            if not ok:
                raise RuntimeError('%s.%s readback differs after set' % (node.get_class().get_name(), prop))

        float_eq = lambda a, b: abs(float(a) - float(b)) <= 1e-5
        colour_eq = lambda a, b: _close(_colour_list(a), _colour_list(b), spec['verification']['colourTolerance'])
        set_and_verify(colour, 'constant', ue.LinearColor(gold[0], gold[1], gold[2], 1.0), colour_eq)
        if metallic is not None:
            set_and_verify(metallic, 'r', float(spec['gold']['metallic']), float_eq)
        if isinstance(rough, ue.MaterialExpressionLinearInterpolate):
            set_and_verify(rough, 'const_a', float(group_cfg['roughnessAtHeight0']), float_eq)
            set_and_verify(rough, 'const_b', float(group_cfg['roughnessAtHeight1']), float_eq)
        else:
            set_and_verify(rough, 'r', float(group_cfg['roughness']), float_eq)

        if with_variation:
            self.add_variation(material, colour, rough, record)

        errors = ml.recompile_material(material)
        record['recompileMessages'] = [str(e) for e in errors] if errors else []
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + record['asset'])
        record['after'] = self.describe_material(material)
        record['uassetSha256After'] = sha256_of(disk_path(record['asset']))
        record['upstreamOfBaseColorAfter'] = self.upstream_constants(material, self.input_node(material, 'MP_BASE_COLOR'))
        record['upstreamOfRoughnessAfter'] = self.upstream_constants(material, self.input_node(material, 'MP_ROUGHNESS'))
        self.verify_material_after(record, group_cfg, with_variation)
        record['status'] = 'saved'

    def verify_material_after(self, record, group_cfg, with_variation):
        spec = self.spec
        gold = spec['gold']['linear'] + [1.0]
        inputs = record['after']['inputs']
        tol = spec['verification']['colourTolerance']
        if with_variation:
            if inputs['MP_BASE_COLOR']['class'] != 'MaterialExpressionMultiply' or inputs['MP_ROUGHNESS']['class'] != 'MaterialExpressionClamp':
                raise RuntimeError('%s: variation graph not wired as expected: %r' % (record['asset'], inputs))
            constants = [n for n in record['upstreamOfBaseColorAfter'] if n.get('class') == 'MaterialExpressionConstant3Vector' and n.get('constant') is not None]
            if constants and not any(_close(n['constant'], gold, tol) for n in constants):
                raise RuntimeError('%s: gold constant not found upstream of BaseColor' % record['asset'])
        else:
            if not _close(inputs['MP_BASE_COLOR'].get('constant', []), gold, tol):
                raise RuntimeError('%s: BaseColor constant readback differs' % record['asset'])
            if abs(inputs['MP_ROUGHNESS'].get('r', -1) - group_cfg['roughness']) > 1e-5:
                raise RuntimeError('%s: roughness readback differs' % record['asset'])
        record['verified'] = True

    def add_variation(self, material, colour, rough, record):
        ue = self.ue
        ml = self.ml
        cfg = self.spec['variation']

        def node(cls, x, y, **props):
            expression = ml.create_material_expression(material, cls, x, y)
            if expression is None:
                raise RuntimeError('create_material_expression failed for %s' % cls.__name__)
            applied = {}
            for key, value in props.items():
                try:
                    expression.set_editor_property(key, value)
                    applied[key] = str(value) if not isinstance(value, (int, float, bool)) else value
                except Exception as error:
                    applied[key] = 'unavailable: %r' % (error,)
                    if key in ('const_a', 'const_b', 'min_default', 'max_default', 'output_min', 'output_max'):
                        raise
            record['nodesAdded'].append({'class': cls.__name__, 'position': [x, y], 'properties': applied})
            return expression

        def input_name(expression, wanted):
            names = [str(n) for n in ml.get_material_expression_input_names(expression)]
            for candidate in names:
                if candidate.lower() == wanted.lower():
                    return candidate
            raise RuntimeError('%s has no input %r (inputs %s)' % (expression.get_class().get_name(), wanted, names))

        def wire(source, target, wanted, output=''):
            pin = input_name(target, wanted)
            if not ml.connect_material_expressions(source, output, target, pin):
                raise RuntimeError('Connection %s -> %s.%s failed' % (source.get_class().get_name(), target.get_class().get_name(), pin))
            record['connections'].append('%s -> %s.%s' % (source.get_class().get_name(), target.get_class().get_name(), pin))

        def to_property(source, prop_name):
            if not ml.connect_material_property(source, '', getattr(ue.MaterialProperty, prop_name)):
                raise RuntimeError('connect_material_property %s -> %s failed' % (source.get_class().get_name(), prop_name))
            record['connections'].append('%s -> %s' % (source.get_class().get_name(), prop_name))

        noise_function, function_name = _enum(ue, 'NoiseFunction', *cfg['noise']['functionCandidates'])
        record['noiseFunction'] = function_name
        noise_props = dict(scale=1.0, quality=int(cfg['noise']['quality']), noise_function=noise_function, turbulence=bool(cfg['noise']['turbulence']),
                           levels=int(cfg['noise']['levels']), level_scale=float(cfg['noise']['levelScale']), output_min=float(cfg['noise']['outputMin']),
                           output_max=float(cfg['noise']['outputMax']), tiling=False)
        scale = float(cfg['scaleCm'])

        # Roughness: Clamp(existing + noise * amplitude)
        world = node(ue.MaterialExpressionWorldPosition, -1900, 600)
        divide = node(ue.MaterialExpressionDivide, -1700, 600, const_b=scale)
        wire(world, divide, 'A')
        noise_r = node(ue.MaterialExpressionNoise, -1500, 600, **noise_props)
        wire(divide, noise_r, 'World Position')
        mul_r = node(ue.MaterialExpressionMultiply, -1250, 600, const_b=float(cfg['roughnessAmplitude']))
        wire(noise_r, mul_r, 'A')
        add_r = node(ue.MaterialExpressionAdd, -450, 150)
        wire(rough, add_r, 'A')
        wire(mul_r, add_r, 'B')
        clamp = node(ue.MaterialExpressionClamp, -250, 150, min_default=float(cfg['roughnessClamp'][0]), max_default=float(cfg['roughnessClamp'][1]))
        wire(add_r, clamp, 'None')
        to_property(clamp, 'MP_ROUGHNESS')

        # Tint: Constant3Vector * (1 + noise(offset position) * amplitude)
        offset = cfg['tintPositionOffsetCm']
        offset_node = node(ue.MaterialExpressionConstant3Vector, -1900, 900, constant=ue.LinearColor(float(offset[0]), float(offset[1]), float(offset[2]), 0.0))
        add_pos = node(ue.MaterialExpressionAdd, -1700, 900)
        wire(world, add_pos, 'A')
        wire(offset_node, add_pos, 'B')
        divide_t = node(ue.MaterialExpressionDivide, -1500, 900, const_b=scale)
        wire(add_pos, divide_t, 'A')
        noise_t = node(ue.MaterialExpressionNoise, -1300, 900, **noise_props)
        wire(divide_t, noise_t, 'World Position')
        mul_t = node(ue.MaterialExpressionMultiply, -1050, 900, const_b=float(cfg['tintAmplitude']))
        wire(noise_t, mul_t, 'A')
        add_t = node(ue.MaterialExpressionAdd, -850, 900, const_a=1.0)
        wire(mul_t, add_t, 'B')
        mul_c = node(ue.MaterialExpressionMultiply, -450, -300)
        wire(colour, mul_c, 'A')
        wire(add_t, mul_c, 'B')
        to_property(mul_c, 'MP_BASE_COLOR')
        record['variation'] = {'scaleCm': scale, 'roughnessAmplitude': cfg['roughnessAmplitude'], 'tintAmplitude': cfg['tintAmplitude'], 'tintPositionOffsetCm': offset,
                               'roughnessClamp': cfg['roughnessClamp'], 'noiseFunction': function_name}

    # -- material instance parameters ---------------------------------------

    def set_instance_parameter(self, instance, kind, parameter, value, record):
        """Set one MIC parameter and verify by readback (5.8 setters always return False)."""
        ue = self.ue
        ml = self.ml
        getters = {'scalar': ml.get_material_instance_scalar_parameter_value, 'vector': ml.get_material_instance_vector_parameter_value}
        setters = {'scalar': ml.set_material_instance_scalar_parameter_value, 'vector': ml.set_material_instance_vector_parameter_value}

        def read():
            got = getters[kind](instance, parameter)
            return float(got) if kind == 'scalar' else _colour_list(got)

        def matches(got):
            if kind == 'scalar':
                return abs(got - float(value)) <= 1e-4
            return _close(got, _colour_list(value), 1e-4)

        before = read()
        returned = setters[kind](instance, parameter, value)
        ml.update_material_instance(instance)
        got = read()
        path = 'MaterialEditingLibrary.set_material_instance_%s_parameter_value (return %s ignored)' % (kind, returned)
        if not matches(got):
            prop = {'scalar': 'scalar_parameter_values', 'vector': 'vector_parameter_values'}[kind]
            struct_cls = {'scalar': ue.ScalarParameterValue, 'vector': ue.VectorParameterValue}[kind]
            values = [v for v in instance.get_editor_property(prop) if str(v.get_editor_property('parameter_info').get_editor_property('name')) != parameter]
            entry = struct_cls()
            info = ue.MaterialParameterInfo()
            info.set_editor_property('name', parameter)
            entry.set_editor_property('parameter_info', info)
            entry.set_editor_property('parameter_value', value)
            values.append(entry)
            instance.set_editor_property(prop, values)
            ml.update_material_instance(instance)
            got = read()
            path = 'set_editor_property(%s) struct fallback' % prop
        entry = {'parameter': parameter, 'kind': kind, 'before': before, 'desired': float(value) if kind == 'scalar' else _colour_list(value), 'after': got, 'path': path, 'matches': matches(got)}
        record.setdefault('parameters', []).append(entry)
        if not entry['matches']:
            raise RuntimeError('Parameter %s on %s read back %r after %s' % (parameter, instance.get_name(), got, path))
        return entry

    def read_instance(self, instance, names):
        ml = self.ml
        out = {'parent': _asset_path(instance.get_editor_property('parent'))}
        for name in names['scalars']:
            out[name] = float(ml.get_material_instance_scalar_parameter_value(instance, name))
        for name in names['vectors']:
            out[name] = _colour_list(ml.get_material_instance_vector_parameter_value(instance, name))
        for name in names['textures']:
            out[name] = _asset_path(ml.get_material_instance_texture_parameter_value(instance, name))
        return out

    # -- discovery -----------------------------------------------------------

    def discover(self, groups, strict=True):
        """All guards and handle lookups; nothing is mutated. Returns a plan dict.
        strict=False skips the 'already applied' refusals (dry run verifying a saved pass)."""
        ue = self.ue
        spec = self.spec
        inventory = self.take_inventory()
        plan = {'materials': {}, 'partitionComponents': [], 'floor': None, 'fill': None, 'ppv': None}
        found = {}

        if 'frieze' in groups:
            cfg = spec['frieze']
            users = sum(1 for row in inventory.values() if row['label'].startswith(cfg['actorLabelPrefix']))
            displaced_users = len(self.components_using(cfg['materials'][1]))
            found['frieze'] = {'actorsWithLabelPrefix': users, 'componentsUsingDisplaced': displaced_users}
            if displaced_users < cfg['minimumActorsUsingDisplaced']:
                raise RuntimeError('Frieze displaced material is used by %d components; expected at least %d' % (displaced_users, cfg['minimumActorsUsingDisplaced']))
            for path in cfg['materials']:
                material = self.load_material(path)
                self.check_gold_material(material, cfg['expectedRoughnessNode'], path, strict)
                plan['materials'][path] = {'group': 'frieze', 'object': material, 'variation': cfg['applyVariation'], 'cfg': cfg, 'componentsUsing': len(self.components_using(path))}

        if 'veneer' in groups or 'partition' in groups:
            cfg = spec['veneer']
            veneers = [row for row in inventory.values() if row['folder'].endswith(cfg['folderSuffix']) and row['label'].startswith(cfg['labelPrefix'])]
            materials = sorted({m for row in veneers for m in row['materials'] if m})
            found['veneer'] = {'actors': sorted(row['label'] for row in veneers), 'materials': materials}
            if len(veneers) != cfg['expectedVeneerCount']:
                raise RuntimeError('Expected %d veneer actors in the %s folder, found %d: %s' % (cfg['expectedVeneerCount'], cfg['folderSuffix'], len(veneers), found['veneer']['actors']))
            if materials != [cfg['expectedMaterial']]:
                raise RuntimeError('Veneer actors carry %s, expected exactly %s' % (materials, cfg['expectedMaterial']))
            veneer = self.load_material(cfg['expectedMaterial'])
            if 'veneer' in groups:
                self.check_gold_material(veneer, cfg['expectedRoughnessNode'], cfg['expectedMaterial'], strict)
                plan['materials'][cfg['expectedMaterial']] = {'group': 'veneer', 'object': veneer, 'variation': cfg['applyVariation'], 'cfg': cfg, 'componentsUsing': len(veneers)}
            plan['veneerMaterial'] = veneer

        if 'vessels' in groups:
            cfg = spec['vessels']
            found['vessels'] = {}
            for path in cfg['materials']:
                users = self.components_using(path)
                found['vessels'][path] = {'componentsUsing': len(users), 'actorLabels': sorted({r['label'] for r in users})[:12]}
                if not users and cfg['skipUnused']:
                    found['vessels'][path]['result'] = 'unused_skipped'
                    continue
                material = self.load_material(path)
                self.check_gold_material(material, cfg['expectedRoughnessNode'], path, strict)
                plan['materials'][path] = {'group': 'vessels', 'object': material, 'variation': cfg['applyVariation'], 'cfg': cfg, 'componentsUsing': len(users)}
            gold_like = sorted({m for row in inventory.values() for m in row['materials'] if m and 'gold' in m.lower() and m not in cfg['materials']
                                and m != spec['veneer']['expectedMaterial'] and m not in spec['frieze']['materials'] and m != spec['floor']['instance'] and m != spec['partition']['expectedMaterialBefore']})
            found['vessels']['otherGoldNamedMaterialsInMapNotAdjusted'] = gold_like

        if 'partition' in groups:
            cfg = spec['partition']
            tol = cfg['faceToleranceCm']
            candidates = []
            others = []
            for path, row in inventory.items():
                if not row['mesh']:
                    continue
                if row['mesh'] in cfg['expectedMeshes']:
                    candidates.append((path, row))
                    continue
                if row['mesh'].startswith(cfg['meshPrefix']):
                    continue
                # Anything else standing on the partition face (paroches, doors, future relief) is recorded, never touched.
                box = self.component_bounds(row)
                if abs(box['max'][0] - cfg['faceX']) <= tol and box['min'][0] >= cfg['backX'] - tol and box['min'][1] >= -cfg['yHalfWidthCm'] - tol and box['max'][1] <= cfg['yHalfWidthCm'] + tol:
                    others.append({'label': row['label'], 'mesh': row['mesh'], 'boundsCm': box})
            if len(candidates) != len(cfg['expectedMeshes']):
                raise RuntimeError('Expected %d partition components, found %d: %s' % (len(cfg['expectedMeshes']), len(candidates), [r['label'] for _, r in candidates]))
            for path, row in candidates:
                box = self.component_bounds(row)
                if abs(box['max'][0] - cfg['faceX']) > tol or abs(box['min'][0] - cfg['backX']) > tol or box['min'][2] < cfg['zRange'][0] - tol or box['max'][2] > cfg['zRange'][1] + tol:
                    raise RuntimeError('Partition piece %s bounds %r do not form the X %s face' % (row['label'], box, cfg['faceX']))
                if len(row['materials']) != 1:
                    raise RuntimeError('Partition piece %s has %d material slots, expected 1' % (row['label'], len(row['materials'])))
                if strict and row['materials'][0] == veneer_material(spec):
                    raise RuntimeError('Partition piece %s already carries the veneer gold; run -BalanceRevert first' % row['label'])
                plan['partitionComponents'].append({'componentPath': path, 'row': row, 'bounds': box, 'materialBefore': row['materials'][0], 'overridesBefore': list(row['overrides'])})
            found['partition'] = {'components': [{'label': c['row']['label'], 'actorName': c['row']['actorName'], 'mesh': c['row']['mesh'], 'boundsCm': c['bounds'], 'boundsSource': c['row'].get('boundsSource'),
                                                  'materialBefore': c['materialBefore'], 'expectedBeforeMatches': c['materialBefore'] == cfg['expectedMaterialBefore']} for c in plan['partitionComponents']],
                                  'otherNonArchitectureComponentsAtFace': others}

        if 'floor' in groups:
            cfg = spec['floor']
            instance = self.load_material(cfg['instance'], expect_instance=True)
            names = {'scalars': ['TilingCm', 'NormalStrength', 'RoughnessScale', 'Metallic', 'AlbedoFlatness'], 'vectors': ['Tint'], 'textures': ['Albedo', 'Normal', 'ARM']}
            state = self.read_instance(instance, names)
            users = self.components_using(cfg['instance'])
            found['floor'] = {'before': state, 'componentsUsing': [{'label': r['label'], 'mesh': r['mesh']} for r in users]}
            if state['parent'] != cfg['expectedParent']:
                raise RuntimeError('Floor instance parent %s is not %s' % (state['parent'], cfg['expectedParent']))
            if state['ARM'] != cfg['expectedArmTexture']:
                raise RuntimeError('Floor instance ARM texture %s is not the measured %s; roughnessScale arithmetic would not apply' % (state['ARM'], cfg['expectedArmTexture']))
            if len(users) != cfg['expectedComponentsUsing']:
                raise RuntimeError('Floor instance used by %d components, expected %d' % (len(users), cfg['expectedComponentsUsing']))
            if strict and abs(state['RoughnessScale'] - cfg['roughnessScale']) <= 1e-4:
                raise RuntimeError('Floor instance already carries RoughnessScale %.3f; run -BalanceRevert first' % cfg['roughnessScale'])
            plan['floor'] = {'object': instance, 'names': names, 'before': state}

        if 'lighting' in groups:
            cfg = spec['lighting']
            fills = [a for a in self.polish.actors.get_all_level_actors() if a.get_actor_label() == cfg['fill']['label'] and cfg['fill']['tag'] in [str(t) for t in a.get_editor_property('tags')]]
            ppvs = [a for a in self.polish.actors.get_all_level_actors() if isinstance(a, ue.PostProcessVolume)]
            if len(fills) != 1:
                raise RuntimeError('Expected one tagged %s actor, found %d' % (cfg['fill']['label'], len(fills)))
            if len(ppvs) != 1:
                raise RuntimeError('Expected exactly one PostProcessVolume, found %d' % len(ppvs))
            component = fills[0].get_component_by_class(getattr(ue, cfg['fill']['componentClass']))
            intensity = float(component.get_editor_property('intensity'))
            settings = ppvs[0].get_editor_property('settings')
            recorded = self.polish.record_only('postProcess', settings, cfg['postProcess']['recordOnly'] + [p for p in cfg['postProcess']['properties']])
            found['lighting'] = {'fill': {'actorName': fills[0].get_name(), 'intensityBefore': intensity, 'units': lp.encode_value(ue, component.get_editor_property('intensity_units')),
                                          'reductionPlanned': intensity > cfg['fill']['intensityThresholdCd']},
                                 'postProcess': {'actorName': ppvs[0].get_name(), 'label': ppvs[0].get_actor_label(), 'before': recorded}}
            bounds = cfg['postProcess']['expectedExposureBounds']
            found['lighting']['postProcess']['exposureBoundsMatchInteriorFix'] = {
                key: (recorded.get(key, {}).get('value') is not None and abs(recorded[key]['value'] - bounds[key]) <= 1e-3)
                for key in ('auto_exposure_min_brightness', 'auto_exposure_max_brightness')}
            plan['fill'] = {'actor': fills[0], 'component': component, 'intensityBefore': intensity}
            plan['ppv'] = {'actor': ppvs[0]}
        self.receipt['discovery'] = found
        return plan

    # -- apply -------------------------------------------------------------

    def checkpoint(self, stamp, plan):
        spec = self.spec
        map_file = ROOT / spec['targetMapFile']
        checkpoint, copied = lp._checkpoint(spec, spec['checkpointPrefix'], stamp, map_file, self.receipt['mapSha256Before'])
        assets_dir = checkpoint / 'Assets'
        copies = {}
        paths = list(plan['materials']) + ([spec['floor']['instance']] if plan.get('floor') else [])
        for path in paths:
            source = disk_path(path)
            destination = assets_dir / source.relative_to(ROOT / 'Content')
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            sha = sha256_of(source)
            if sha256_of(destination) != sha:
                raise RuntimeError('Checkpoint copy hash differs for ' + path)
            copies[path] = {'checkpointFile': str(destination), 'uassetSha256Before': sha}
        self.receipt['checkpoint'] = str(checkpoint)
        self.receipt['oneFilePerActorFoldersCopied'] = copied
        self.receipt['assetCheckpoints'] = copies
        return copies

    def apply_materials(self, plan, copies):
        for path, item in plan['materials'].items():
            record = {'asset': path, 'group': item['group'], 'componentsUsing': item['componentsUsing'], 'status': 'started',
                      'uassetSha256Before': copies[path]['uassetSha256Before'], 'checkpointFile': copies[path]['checkpointFile']}
            self.receipt['materials'][path] = record
            self.write_receipt()
            self.adjust_gold_material(item['object'], item['cfg'], record, item['variation'])
            self.write_receipt()

    def apply_partition(self, plan):
        ue = self.ue
        gold = plan['veneerMaterial']
        for item in plan['partitionComponents']:
            component = item['row']['component']
            before_overrides = [m for m in component.get_editor_property('override_materials')]
            component.set_material(0, gold)
            after = _asset_path(component.get_material(0))
            record = {'componentPath': item['componentPath'], 'actorName': item['row']['actorName'], 'label': item['row']['label'], 'mesh': item['row']['mesh'], 'slot': 0,
                      'boundsCm': item['bounds'], 'effectiveBefore': item['materialBefore'], 'overrideArrayBefore': [_asset_path(m) for m in before_overrides],
                      'desired': _asset_path(gold), 'effectiveAfter': after, 'matches': after == _asset_path(gold)}
            self.receipt['partition'].append(record)
            if not record['matches']:
                raise RuntimeError('Partition material did not take on ' + item['row']['label'])

    def apply_floor(self, plan, copies):
        ue = self.ue
        cfg = self.spec['floor']
        instance = plan['floor']['object']
        record = {'asset': cfg['instance'], 'before': plan['floor']['before'], 'uassetSha256Before': copies[cfg['instance']]['uassetSha256Before'], 'checkpointFile': copies[cfg['instance']]['checkpointFile'], 'status': 'started'}
        self.receipt['floor'] = record
        self.set_instance_parameter(instance, 'scalar', 'RoughnessScale', float(cfg['roughnessScale']), record)
        if cfg['alsoTintAndMetallic']:
            gold = self.spec['gold']['linear']
            self.set_instance_parameter(instance, 'vector', 'Tint', ue.LinearColor(gold[0], gold[1], gold[2], 1.0), record)
            self.set_instance_parameter(instance, 'scalar', 'Metallic', float(cfg['metallic']), record)
        if not self.assets.save_loaded_asset(instance, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + cfg['instance'])
        record['after'] = self.read_instance(instance, plan['floor']['names'])
        record['uassetSha256After'] = sha256_of(disk_path(cfg['instance']))
        record['meanRoughnessAfterEstimate'] = round(record['after']['RoughnessScale'] * cfg['roughnessSource']['measuredMean01'], 4)
        record['status'] = 'saved'

    def apply_lighting(self, plan):
        ue = self.ue
        cfg = self.spec['lighting']
        fill = plan['fill']
        if fill['intensityBefore'] > cfg['fill']['intensityThresholdCd']:
            self.polish.set_prop('fill', fill['component'], 'intensity', float(cfg['fill']['intensityCd']), True, actor=fill['actor'], component_class=cfg['fill']['componentClass'])
        else:
            self.receipt['notes'].append('Fill intensity %.1f cd is within the %.0f cd threshold; unchanged' % (fill['intensityBefore'], cfg['fill']['intensityThresholdCd']))
        actor = plan['ppv']['actor']
        block = cfg['postProcess']
        settings = actor.get_editor_property('settings')
        required = set(block['required'])
        records = []
        for prop, raw in block['properties'].items():
            records.append(self.polish.set_prop('postProcess', settings, prop, raw, prop in required, actor=actor, component_class=None, struct='settings'))
        actor.set_editor_property('settings', settings)
        committed = actor.get_editor_property('settings')
        for record in records:
            if record.get('applied'):
                record['afterCommit'] = self.polish.read_prop(committed, record['property'])
                record['matches'] = lp.values_match(record['afterCommit'], record['desired'], self.spec['verification']['floatRelativeTolerance'])
                if not record['matches']:
                    raise RuntimeError('Post-process field %s differs after commit: %r' % (record['property'], record['afterCommit']))
        self.polish.set_label('postProcess', actor, block['labelAfter'])

    # -- fresh-process comparison (dry run) ------------------------------------

    def compare_with_receipt(self, receipt, plan):
        """Compare the live state with a saved apply receipt's after-values (run in a fresh process)."""
        out = {'receipt': str(receipt.get('stamp')), 'materials': {}, 'floor': None, 'partition': [], 'lighting': []}
        for path, record in receipt.get('materials', {}).items():
            item = plan['materials'].get(path)
            if item is None:
                continue
            live = self.describe_material(item['object'])
            out['materials'][path] = {'liveInputs': live['inputs'], 'receiptAfterInputs': record.get('after', {}).get('inputs'), 'matches': live['inputs'] == record.get('after', {}).get('inputs'),
                                      'uassetSha256Matches': sha256_of(disk_path(path)) == record.get('uassetSha256After')}
        if receipt.get('floor') and plan.get('floor'):
            live = plan['floor']['before']
            after = receipt['floor'].get('after', {})
            out['floor'] = {'live': live, 'receiptAfter': after, 'matches': all(abs(live[k] - after[k]) <= 1e-4 for k in ('RoughnessScale', 'Metallic') if k in after) and _close(live.get('Tint', []), after.get('Tint', []), 1e-4)}
        for record in receipt.get('partition', []):
            row = self.inventory.get(record['componentPath'])
            out['partition'].append({'label': record['label'], 'live': row['materials'][0] if row else None, 'receiptAfter': record['effectiveAfter'], 'matches': bool(row) and row['materials'][0] == record['effectiveAfter']})
        for change in receipt.get('lightingChanges', []):
            if change.get('applied') and change.get('property') not in ('actor_label',):
                actor = self.polish.find_actor(change['actorName'], change['actorLabel'])
                if actor is None:
                    out['lighting'].append({'property': change['property'], 'matches': False, 'error': 'actor missing'})
                    continue
                if change.get('struct'):
                    value = self.polish.read_prop(actor.get_editor_property(change['struct']), change['property'])
                else:
                    value = self.polish.read_prop(actor.get_component_by_class(getattr(self.ue, change['componentClass'])), change['property'])
                out['lighting'].append({'property': change['property'], 'live': value, 'receiptAfter': change.get('desired'), 'matches': lp.values_match(value, change.get('desired'), self.spec['verification']['floatRelativeTolerance'])})
        out['allMatch'] = all(m['matches'] for m in out['materials'].values()) and all(p['matches'] for p in out['partition']) and all(l['matches'] for l in out['lighting']) and (out['floor'] is None or out['floor']['matches'])
        return out


def _new_receipt(spec, stamp, switches, map_sha_before, protected, ue):
    return {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(ROOT / spec['targetMapFile']), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == spec['lastKnownMapSha256'], 'protectedSha256Before': protected, 'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'switches': switches, 'discovery': {}, 'materials': {}, 'partition': [], 'floor': None, 'lightingChanges': [],
        'created': [], 'notes': [], 'errors': [], 'mapSaved': False, 'checkpoint': None, 'limitations': list(spec['limitations']),
    }


def run(load_target=True, groups=GROUPS, dry_run=False):
    """Apply (or dry-run) the balance. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    spec = load_spec()
    groups = normalise_groups(groups)
    offline = offline_check(spec)
    balance = Balance(ue, spec)
    balance.guard_before_load()
    previous_path, previous = latest_apply_receipt(spec, require=False)
    if previous and not dry_run:
        raise RuntimeError('A saved, unreverted balance receipt exists (%s); run -BalanceRevert first' % previous_path)
    if load_target:
        balance.load_target()
    else:
        balance.polish.guard_world(False)

    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = lp._protected_hashes(spec)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    balance.receipt_path = lp._fresh_receipt(spec, spec['dryRunReceiptPrefix'] if dry_run else spec['receiptPrefix'], stamp)
    balance.receipt = _new_receipt(spec, stamp, {'groups': list(groups), 'dryRun': dry_run}, map_sha_before, protected, ue)
    balance.receipt['offlineCheck'] = offline
    balance.receipt['cvars'] = balance.read_cvars() if 'lighting' in groups else None
    balance.write_receipt()

    try:
        # A dry run after a saved apply verifies that pass in a fresh process, so the 'already applied' refusals are off.
        plan = balance.discover(groups, strict=not (dry_run and previous))
        balance.receipt['actorCountBefore'] = len(balance.polish.actors.get_all_level_actors())
        for path, item in plan['materials'].items():
            balance.receipt['materials'][path] = {'asset': path, 'group': item['group'], 'componentsUsing': item['componentsUsing'], 'before': balance.describe_material(item['object']), 'status': 'planned'}
        baseline = balance.polish.snapshot_unrelated(set())
        signature_before = balance.material_signature()
        balance.receipt['unrelatedActorBaselineCount'] = len(baseline)
        if dry_run:
            if previous:
                balance.receipt['comparedWithReceipt'] = str(previous_path)
                balance.receipt['comparison'] = balance.compare_with_receipt(previous, plan)
            balance.receipt['status'] = DRY_RUN_STATUS
            return balance.receipt

        copies = balance.checkpoint(stamp, plan)
        balance.receipt['status'] = 'checkpointed_apply_started'
        balance.write_receipt()

        balance.apply_materials(plan, copies)
        if plan['partitionComponents']:
            balance.apply_partition(plan)
            balance.write_receipt()
        if plan.get('floor'):
            balance.apply_floor(plan, copies)
            balance.write_receipt()
        if plan.get('ppv'):
            balance.receipt['changes'] = balance.receipt['lightingChanges']   # lp.Polish.set_prop appends to receipt['changes']
            balance.write_receipt()
            balance.apply_lighting(plan)
            balance.write_receipt()

        current = balance.polish.snapshot_unrelated(set())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed or len(current) != len(baseline):
            raise RuntimeError('Unrelated actors changed before save: %s' % (changed or 'count differs')[:10])
        balance.receipt['unrelatedActorsUnchangedBeforeSave'] = True

        balance.polish.save_and_reopen()
        balance.receipt['mapSaved'] = True
        balance.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        balance.write_receipt()

        reopened = balance.polish.snapshot_unrelated(set())
        changed = [name for name, row in baseline.items() if reopened.get(name) != row]
        if changed:
            raise RuntimeError('Unrelated actors differ after reopen: %s' % changed[:10])
        balance.receipt['unrelatedActorsUnchangedAfterReopen'] = True
        balance.take_inventory()
        signature_after = balance.material_signature()
        expected_changed = {c['componentPath'] for c in balance.receipt['partition']}
        diff = sorted(path for path in set(signature_before) | set(signature_after) if signature_before.get(path) != signature_after.get(path))
        unexpected = [p for p in diff if p not in expected_changed]
        balance.receipt['materialInventoryDiff'] = {'changedComponents': diff, 'unexpected': unexpected}
        if unexpected:
            raise RuntimeError('Material inventory changed on unexpected components: %s' % unexpected[:10])
        for record in balance.receipt['partition']:
            row = balance.inventory.get(record['componentPath'])
            record['afterReopen'] = row['materials'][0] if row else None
            record['afterReopenMatches'] = record['afterReopen'] == record['desired']
            if not record['afterReopenMatches']:
                raise RuntimeError('Partition material differs after reopen for ' + record['label'])
        failures = balance.polish.readback(balance.receipt['lightingChanges'], 'afterReopen', 'desired')
        balance.receipt['reopenReadbackFailures'] = failures
        balance.receipt['actorCountAfter'] = len(balance.polish.actors.get_all_level_actors())
        if failures:
            raise RuntimeError('Reopen readback failed: %s' % failures[:10])
        for path, item in plan['materials'].items():
            balance.receipt['materials'][path]['afterReopenInMemory'] = balance.describe_material(item['object'])
        balance.receipt['status'] = APPLIED_STATUS
        return balance.receipt
    except Exception as error:
        balance.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        balance.receipt['status'] = 'failed_after_save_checkpoint_available' if balance.receipt.get('mapSaved') or sha256_of(map_file) != map_sha_before else 'failed_before_map_save'
        if balance.receipt['status'] == 'failed_before_map_save' and any(m.get('status') == 'saved' for m in balance.receipt['materials'].values()):
            balance.receipt['status'] = 'failed_after_asset_save_map_unchanged_checkpoint_available'
        raise
    finally:
        balance.receipt['mapSha256After'] = sha256_of(map_file)
        balance.receipt['mapBytesChanged'] = balance.receipt['mapSha256After'] != map_sha_before
        balance.receipt['protectedUnchanged'] = lp._protected_hashes(spec) == protected
        balance.receipt['appliedLightingChangeCount'] = sum(1 for c in balance.receipt['lightingChanges'] if c.get('applied'))
        balance.receipt.pop('changes', None)
        if not balance.receipt['protectedUnchanged']:
            balance.receipt['status'] = 'failed_protected_hash_guard'
            balance.receipt['errors'].append({'stage': 'verification', 'error': 'Protected hash changed'})
        balance.write_receipt()
        if not balance.receipt['protectedUnchanged']:
            raise RuntimeError('Protected hash changed')


def revert(receipt_path=None, load_target=True):
    """Restore checkpointed asset bytes, then the map properties, save, reopen, read back."""
    import unreal as ue
    spec = load_spec()
    if receipt_path:
        source_path = Path(receipt_path)
        source = json.loads(source_path.read_text(encoding='utf-8-sig'))
        if not source.get('mapSaved') and not source.get('materials'):
            raise RuntimeError('Receipt never saved anything; nothing to revert: ' + str(source_path))
    else:
        source_path, source = latest_apply_receipt(spec)
    balance = Balance(ue, spec)
    balance.guard_before_load()

    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = lp._protected_hashes(spec)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    balance.receipt_path = lp._fresh_receipt(spec, spec['revertReceiptPrefix'], stamp)
    balance.receipt = _new_receipt(spec, stamp, {'revert': True}, map_sha_before, protected, ue)
    balance.receipt.update({'revertedFrom': str(source_path), 'revertedFromStamp': source.get('stamp'), 'mapMatchesApplySave': map_sha_before == source.get('mapSha256AfterSave'),
                            'assetRestores': [], 'changes': []})
    balance.write_receipt()
    if not balance.receipt['mapMatchesApplySave']:
        balance.receipt['notes'].append('Map changed since the apply receipt saved it; before-values are still restored property by property.')

    try:
        # 1. Asset bytes first, before anything loads them.
        checkpoint, copied = lp._checkpoint(spec, spec['revertCheckpointPrefix'], stamp, map_file, map_sha_before)
        balance.receipt['checkpoint'] = str(checkpoint)
        balance.receipt['oneFilePerActorFoldersCopied'] = copied
        assets_dir = checkpoint / 'Assets'
        records = list(source.get('materials', {}).values()) + ([source['floor']] if source.get('floor') else [])
        for record in records:
            if not record.get('checkpointFile') or record.get('status') not in ('saved',):
                balance.receipt['assetRestores'].append({'asset': record.get('asset'), 'result': 'skipped_not_saved_by_apply'})
                continue
            path = record['asset']
            live = disk_path(path)
            saved_copy = Path(record['checkpointFile'])
            entry = {'asset': path, 'checkpointFile': str(saved_copy), 'liveSha256BeforeRestore': sha256_of(live) if live.exists() else None}
            if not saved_copy.exists():
                raise RuntimeError('Checkpoint file missing for %s: %s' % (path, saved_copy))
            if sha256_of(saved_copy) != record['uassetSha256Before']:
                raise RuntimeError('Checkpoint bytes for %s do not match the receipt before-hash' % path)
            try:
                entry['loadedInMemoryBeforeRestore'] = ue.find_object(None, path + '.' + path.rsplit('/', 1)[1]) is not None
            except Exception as error:
                entry['loadedInMemoryBeforeRestore'] = 'unknown: %r' % (error,)
            current_copy = assets_dir / live.relative_to(ROOT / 'Content')
            current_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, current_copy)
            shutil.copy2(saved_copy, live)
            entry['liveSha256AfterRestore'] = sha256_of(live)
            entry['matchesBeforeHash'] = entry['liveSha256AfterRestore'] == record['uassetSha256Before']
            if not entry['matchesBeforeHash']:
                raise RuntimeError('Restored bytes differ for ' + path)
            balance.receipt['assetRestores'].append(entry)
        balance.write_receipt()

        # 2. Map properties.
        if load_target:
            balance.load_target()
        else:
            balance.polish.guard_world(False)
        balance.write_receipt()
        inventory = balance.take_inventory() if source.get('partition') else {}
        for record in source.get('partition', []):
            row = inventory.get(record['componentPath'])
            if row is None:
                raise RuntimeError('Partition component missing for revert: ' + record['componentPath'])
            component = row['component']
            overrides = []
            for material_path in record['overrideArrayBefore']:
                overrides.append(ue.load_asset(material_path) if material_path else None)
            component.set_editor_property('override_materials', overrides)
            after = _asset_path(component.get_material(record['slot']))
            entry = {'componentPath': record['componentPath'], 'label': record['label'], 'desired': record['effectiveBefore'], 'after': after, 'matches': after == record['effectiveBefore']}
            balance.receipt['partition'].append(entry)
            if not entry['matches']:
                raise RuntimeError('Partition revert readback differs for ' + record['label'])
        structs = {}
        for record in reversed(source.get('lightingChanges', [])):
            if not record.get('applied'):
                continue
            before = record['before']
            entry = {'target': record['target'], 'property': record['property'], 'actorName': record['actorName'], 'actorLabel': record['actorLabel'],
                     'componentClass': record.get('componentClass'), 'struct': record.get('struct'), 'desired': before, 'applied': False}
            actor = balance.polish.find_actor(record['actorName'], record.get('after', {}).get('value') if record['property'] == 'actor_label' else record['actorLabel'])
            if actor is None:
                actor = balance.polish.find_actor(record['actorName'], record['actorLabel'])
            if actor is None:
                raise RuntimeError('Revert: actor %s (%s) not found' % (record['actorName'], record['actorLabel']))
            if record['property'] == 'actor_label':
                entry['before'] = {'type': 'str', 'value': actor.get_actor_label()}
                actor.set_actor_label(before['value'])
                entry['after'] = {'type': 'str', 'value': actor.get_actor_label()}
            elif record.get('struct'):
                key = (actor.get_name(), record['struct'])
                if key not in structs:
                    structs[key] = (actor, actor.get_editor_property(record['struct']))
                struct = structs[key][1]
                entry['before'] = balance.polish.read_prop(struct, record['property'])
                struct.set_editor_property(record['property'], lp.decode_value(ue, before))
                entry['after'] = balance.polish.read_prop(struct, record['property'])
            else:
                component = actor.get_component_by_class(getattr(ue, record['componentClass']))
                entry['before'] = balance.polish.read_prop(component, record['property'])
                component.set_editor_property(record['property'], lp.decode_value(ue, before))
                entry['after'] = balance.polish.read_prop(component, record['property'])
            entry['applied'] = True
            entry['matches'] = lp.values_match(entry['after'], before, spec['verification']['floatRelativeTolerance'])
            balance.receipt['lightingChanges'].append(entry)
            if not entry['matches']:
                raise RuntimeError('Revert readback differs for %s.%s' % (record['target'], record['property']))
        for (name, struct_name), (actor, struct) in structs.items():
            actor.set_editor_property(struct_name, struct)
        balance.write_receipt()

        if source.get('mapSaved'):
            balance.polish.save_and_reopen()
            balance.receipt['mapSaved'] = True
            balance.receipt['mapSha256AfterSave'] = sha256_of(map_file)
            failures = balance.polish.readback(balance.receipt['lightingChanges'], 'afterReopen', 'desired')
            balance.take_inventory()
            for entry in balance.receipt['partition']:
                row = balance.inventory.get(entry['componentPath'])
                entry['afterReopen'] = row['materials'][0] if row else None
                if entry['afterReopen'] != entry['desired']:
                    failures.append('partition %s: %s' % (entry['label'], entry['afterReopen']))
            balance.receipt['reopenReadbackFailures'] = failures
            if failures:
                raise RuntimeError('Revert readback failed: %s' % failures[:10])
        else:
            balance.receipt['notes'].append('Apply receipt never saved the map; only asset bytes were restored.')

        # 3. Materials: in-memory readback (may be stale if the package was loaded before the file restore).
        stale = []
        for record in records:
            if record.get('status') != 'saved':
                continue
            path = record['asset']
            obj = ue.load_asset(path)
            if isinstance(obj, ue.Material):
                live = balance.describe_material(obj)['inputs']
                expected = record.get('before', {}).get('inputs')
                ok = live == expected
            elif isinstance(obj, ue.MaterialInstanceConstant):
                live = balance.read_instance(obj, {'scalars': ['RoughnessScale', 'Metallic'], 'vectors': ['Tint'], 'textures': []})
                expected = {k: record['before'][k] for k in ('RoughnessScale', 'Metallic', 'Tint') if k in record.get('before', {})}
                ok = all(abs(live[k] - expected[k]) <= 1e-4 for k in ('RoughnessScale', 'Metallic') if k in expected) and _close(live['Tint'], expected.get('Tint', live['Tint']), 1e-4)
            else:
                live, expected, ok = None, None, False
            for entry in balance.receipt['assetRestores']:
                if entry.get('asset') == path:
                    entry['inMemoryReadback'] = live
                    entry['inMemoryMatchesBefore'] = ok
            if not ok:
                stale.append(path)
        balance.receipt['inMemoryStaleAfterRestore'] = stale
        if stale:
            balance.receipt['notes'].append('Asset bytes were restored and verified by hash, but the in-memory objects still show the applied graph for %s; confirm with -BalanceDryRun in a fresh process.' % stale)
        balance.receipt['status'] = REVERTED_STATUS if not stale else REVERTED_STATUS + '_in_memory_stale_verify_fresh'
        source['revertedBy'] = str(balance.receipt_path)
        source_path.write_text(json.dumps(source, indent=2, default=str) + '\n', encoding='utf-8')
        return balance.receipt
    except Exception as error:
        balance.receipt['errors'].append({'stage': 'revert', 'error': repr(error)})
        balance.receipt['status'] = 'failed_after_save_checkpoint_available' if balance.receipt.get('mapSaved') or sha256_of(map_file) != map_sha_before else 'failed_before_map_save_asset_restores_recorded'
        raise
    finally:
        balance.receipt['mapSha256After'] = sha256_of(map_file)
        balance.receipt['mapBytesChanged'] = balance.receipt['mapSha256After'] != map_sha_before
        balance.receipt['protectedUnchanged'] = lp._protected_hashes(spec) == protected
        balance.receipt.pop('changes', None)
        if not balance.receipt['protectedUnchanged']:
            balance.receipt['status'] = 'failed_protected_hash_guard'
            balance.receipt['errors'].append({'stage': 'verification', 'error': 'Protected hash changed'})
        balance.write_receipt()
        if not balance.receipt['protectedUnchanged']:
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
    return 'release_sanctuary_balance.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def parse_switches(tokens):
    switches = {'dry_run': False, 'groups': GROUPS, 'revert': False, 'revert_receipt': None}
    for token in tokens:
        low = token.lower()
        if low == '-balancedryrun':
            switches['dry_run'] = True
        elif low.startswith('-balanceonly='):
            switches['groups'] = normalise_groups(token.split('=', 1)[1].strip('"'))
        elif low == '-balancerevert':
            switches['revert'] = True
        elif low.startswith('-balancerevert='):
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
            ue.log('release_sanctuary_balance revert: %s assets %d lighting %d partition %d' % (receipt['status'], len(receipt['assetRestores']), len(receipt['lightingChanges']), len(receipt['partition'])))
        else:
            receipt = run(load_target=True, groups=switches['groups'], dry_run=switches['dry_run'])
            ue.log('release_sanctuary_balance: %s materials %d partition %d lighting %s' % (receipt['status'], len(receipt['materials']), len(receipt['partition']), receipt.get('appliedLightingChangeCount')))
    except Exception as error:
        ue.log_error('release_sanctuary_balance failed: ' + repr(error))
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

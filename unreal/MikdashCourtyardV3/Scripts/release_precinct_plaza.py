"""Guarded native import and placement of PrecinctPlazaV1 - the built flat plaza.

Imports the seven module meshes written by Scripts/create_precinct_plaza.py --export, builds
the one new material the anti-repetition scheme needs, and bakes the plaza onto the
AMikdashEnclosure actor that is ALREADY in the map. The plaza is not a new actor: it is seven
more instanced components on the precinct actor, because the deck and the wall have to be
grounded from the same profile and have to appear and disappear together with the state.

Shmuel's decision of 9 September 2026, verbatim:

    "that whole expanded area around that we had to, like, take out buildings. I'm not sure
     if I like it because either you put it as a platform, like a flat flat platform that's
     built out into those dimensions to just expand the plaza. Or what you have to do is you
     have to restore the buildings that are there now. I would say make it a flat plaza for
     the dimensions of the the area that has call sets, that expanded area."

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_precinct_plaza.py"
      -Candidate48 -PlazaAssets
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-PrecinctPlaza-01.log"

ONE TARGET PER RUN, chosen with its flag; there is no default, because the two maps are not
interchangeable:
  -Candidate48   the configured default and the cook map. Run this one first.
  -Main50        the legacy 50 cm map.

ONE MODE PER RUN:
  -PlazaAssets   import the seven meshes, build the three materials, save the assets. Touches
                 no map and no actor, and refuses if a target map changes by a byte.
  -PlazaApply    bake the plaza onto the existing precinct actor, save, reopen, read back.
  -PlazaVerify   reopen and read the placed actor back against the receipt. Saves nothing.

Run with no engine at all to get the offline check as JSON:
  python Scripts/release_precinct_plaza.py -Candidate48
  python Scripts/release_precinct_plaza.py --write-spec

SAFETY MODEL (identical in shape to Scripts/release_enclosure.py)
----------------------------------------------------------------
Refuse on a live or dirty editor, on the wrong project, on a loaded world that is not the
target. Hash the target map and every protected map before anything, checkpoint the target
map and its one-file-per-actor folders into ReviewCheckpoints, write the receipt at the start
and again in `finally` so a failure preserves evidence rather than losing it, and prove in the
finally block that the protected maps came out byte-identical.

THE PLUGIN MAY NOT BE REBUILT YET. AMikdashEnclosure grew eleven properties and seven
components for the plaza. If the editor running this script was built before that, the class
has no PlazaDeckTileMesh and -PlazaApply CANNOT work. That is not a failure: the meshes and
materials still import and are reviewable, the run records an OMISSION with evidence, and the
map is left byte-identical. Rebuild the editor target and run -PlazaApply again.

WHAT IS SOURCED AND WHAT IS AUTHORED
------------------------------------
Yechezkel 42:15-20 with 40:5 gives the EXTENT - 500 reeds of six amot, 3000 amot a side,
measured from outside - and nothing else. That the enclosed ground is a built flat plaza is
the USER'S decision above. The deck datum's consequences, the paving layout, the drainage,
the retaining and scarp construction, the processional ways and the gate stairs are all
AUTHORED by this project and are a study aid, not a claim about the Temple.
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts/release_precinct_plaza.spec.json'
TARGET_FLAGS = {'-candidate48': 'Candidate48', '-main50': 'Main50'}
TARGET_ORDER = ('Candidate48', 'Main50')
MODE_FLAGS = {'-plazaassets': 'assets', '-plazaapply': 'apply', '-plazaverify': 'verify'}

# The UV mapping of the new master, verbatim, so the graph check compares strings and not
# intentions. P is world position; Cs/Sn are the panel's course direction and U0/V0 its own
# origin, both from per-instance custom data; 500 is the approved tile, unchanged.
UV_CODE = ('float2 d = float2(P.x - U0, P.y - V0);'
           ' return float2(d.x * Cs + d.y * Sn, d.y * Cs - d.x * Sn) / 500.0;')
# Four per cent of lightness, driven by the tonal lattice. Visible as drift across a
# kilometre, invisible on one tile, which is the point.
TINT_CODE = 'return C * saturate(1.0 + T * 0.04);'


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    for name, target in spec['targets'].items():
        if disk_path(target['map'], 'umap') != ROOT / target['mapFile']:
            raise RuntimeError('Target %s map and mapFile disagree' % name)
    return spec


def target_from_command_line(command_line):
    """Exactly one target flag, or nothing. Never a default: the two maps are not
    interchangeable, and a plaza laid at the wrong amah is 1,440 m of wrong."""
    lowered = ' %s ' % command_line.lower()
    chosen = [name for flag, name in TARGET_FLAGS.items()
              if (' %s ' % flag) in lowered or ('%s=' % flag) in lowered]
    if len(chosen) > 1:
        raise RuntimeError('Choose exactly one of %s' % list(TARGET_FLAGS))
    return chosen[0] if chosen else None


def mode_from_command_line(command_line):
    lowered = ' %s ' % command_line.lower()
    chosen = [name for flag, name in MODE_FLAGS.items()
              if (' %s ' % flag) in lowered or ('%s=' % flag) in lowered]
    if len(chosen) > 1:
        raise RuntimeError('Choose exactly one of %s' % list(MODE_FLAGS))
    return chosen[0] if chosen else None


def target_config(spec, target):
    if not target:
        raise RuntimeError('Choose the target map with one of %s (%s first: it is the '
                           'configured default and the cook map)'
                           % (list(TARGET_FLAGS), TARGET_ORDER[0]))
    if target not in spec['targets']:
        raise RuntimeError('Unknown target %r; the spec declares %s' % (target, list(spec['targets'])))
    return spec['targets'][target]


def box_error(a, b):
    return max(abs(a[key][index] - b[key][index]) for key in ('min', 'max') for index in range(3))


# ---------------------------------------------------------------------------
# Offline check - runs with no engine at all
# ---------------------------------------------------------------------------
def offline_check(spec=None, target=None):
    """Everything that can be proved without the editor: that the generator ran, that the
    OBJ files on disk are the ones the manifest describes, that the header the runtime and
    the generator share has not moved under them, and that the plaza receipt agrees with the
    precinct receipt about which square it is paving."""
    spec = spec or load_spec()
    manifest_path = ROOT / spec['geometryManifest']
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    header = ROOT / spec['enclosureMathHeader']
    report = dict(
        status='OFFLINE_CHECK',
        spec=str(SPEC_PATH), specSha256=sha256_of(SPEC_PATH),
        scriptSha256=sha256_of(Path(__file__)),
        geometryManifest=str(manifest_path), geometryManifestSha256=sha256_of(manifest_path),
        generatorSha256=manifest['generatorSha256'],
        enclosureMathSha256Recorded=manifest['enclosureMathSha256'],
        enclosureMathSha256Now=sha256_of(header),
        deckDatum=manifest['deckDatum'],
        antiRepetition=manifest['antiRepetition'],
        meshes=[], warnings=[])
    if report['enclosureMathSha256Recorded'] != report['enclosureMathSha256Now']:
        report['warnings'].append(
            'EnclosureMath.h has changed since create_precinct_plaza.py --export ran. The '
            'runtime and the receipt may now lay different plazas. Re-run --export.')

    folder = ROOT / spec['meshSourceFolder']
    by_name = {row['name']: row for row in manifest['meshes']}
    for entry in spec['meshes']:
        record = by_name.get(entry['name'])
        if record is None:
            raise RuntimeError('plaza-manifest.json has no mesh ' + entry['name'])
        path = folder / record['file']
        actual = sha256_of(path)
        if actual != record['sha256']:
            raise RuntimeError('Frozen OBJ hash changed for %s: %s on disk, %s in the manifest'
                               % (entry['name'], actual, record['sha256']))
        report['meshes'].append(dict(name=entry['name'], file=record['file'], sha256=actual,
                                     triangles=record['triangles'],
                                     canonicalBoundsCm=record['canonicalBoundsCm'],
                                     materialRole=entry['material'],
                                     castShadow=entry['castShadow']))

    names = [target] if target else list(spec['targets'])
    report['targets'] = {}
    for name in names:
        config = target_config(spec, name)
        plaza = json.loads((ROOT / config['plazaReceipt']).read_text(encoding='utf-8-sig'))
        precinct = json.loads((ROOT / config['precinctReceipt']).read_text(encoding='utf-8-sig'))
        if abs(plaza['cmPerAmah'] - config['amahCm']) > 1e-9:
            raise RuntimeError('%s: plaza receipt amah %g, spec %g'
                               % (name, plaza['cmPerAmah'], config['amahCm']))
        if abs(plaza['courtPlatformHalfExtentCm'] - config['courtPlatformHalfExtentCm']) > 1e-6:
            raise RuntimeError('%s: plaza receipt court half-extent disagrees with the spec' % name)
        faces = precinct['square']['outerFacesCm']
        inset = 6.0 * config['amahCm']
        wanted = dict(xMinCm=faces['xWest'] + inset, yMinCm=faces['yNorth'] + inset,
                      xMaxCm=faces['xEast'] - inset, yMaxCm=faces['ySouth'] - inset)
        for key, value in wanted.items():
            if abs(plaza['grid'][key] - value) > 1e-6:
                raise RuntimeError('%s: the paved rectangle does not sit one wall thickness '
                                   'inside the precinct square (%s: %g vs %g)'
                                   % (name, key, plaza['grid'][key], value))
        map_file = ROOT / config['mapFile']
        current = sha256_of(map_file) if map_file.exists() else None
        if config.get('observedMapSha256') and current != config['observedMapSha256']:
            report['warnings'].append(
                '%s: the map has been saved since the spec recorded its hash. That is normal - '
                'every release script in this project saves these maps - and is evidence, not a '
                'gate. The receipt records the hash actually released against.' % name)
        report['targets'][name] = dict(
            map=config['map'], amahCm=config['amahCm'],
            plazaReceipt=config['plazaReceipt'],
            plazaReceiptSha256=sha256_of(ROOT / config['plazaReceipt']),
            deckTopZcm=plaza['deck']['topZcm'],
            deckTopMetresAsl=plaza['deck']['topMetresAsl'],
            grid=plaza['grid'], panels=plaza['panels']['count'],
            plan=plaza['plan'],
            retainingPerSide=plaza['retainingPerSide'],
            gates=plaza['gates'],
            cutFill=plaza.get('cutFill'),
            observedMapSha256=config.get('observedMapSha256'),
            currentMapSha256=current)
    return report


def write_spec():
    """Record each map's current hash WITH its provenance. Evidence, never a gate."""
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    now = datetime.now(timezone.utc).isoformat()
    for name, target in spec['targets'].items():
        path = ROOT / target['mapFile']
        if not path.exists():
            continue
        target['observedMapSha256'] = sha256_of(path)
        target['observedUtc'] = now
        target['observedProvenance'] = (
            'sha256 read off %s by release_precinct_plaza.write_spec() at %s. RECORDED, NEVER '
            'REQUIRED: every release script in this project saves these maps, so the hash is '
            'stale within hours. offline_check() reports the recorded and the current hash and '
            'warns on a difference; the receipt records the hash actually released against.'
            % (target['mapFile'], now))
    SPEC_PATH.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    return dict(wrote=str(SPEC_PATH), sha256=sha256_of(SPEC_PATH))


# ---------------------------------------------------------------------------
# Native
# ---------------------------------------------------------------------------
def _pythonize(name):
    """UE exposes `bBuildPlaza` to Python as `build_plaza` and `PlazaDeckTileMesh` as
    `plaza_deck_tile_mesh`. Both spellings are accepted by set_editor_property in most builds
    and neither is guaranteed, so every access below tries the C++ name first and falls back."""
    if name.startswith('b') and len(name) > 1 and name[1].isupper():
        name = name[1:]
    out = []
    for index, char in enumerate(name):
        if char.isupper() and index > 0:
            out.append('_')
        out.append(char.lower())
    return ''.join(out)


def _get_property(actor, name):
    try:
        return actor.get_editor_property(name)
    except Exception:                                                  # noqa: BLE001
        return actor.get_editor_property(_pythonize(name))


def _set_property(actor, name, value):
    try:
        actor.set_editor_property(name, value)
    except Exception:                                                  # noqa: BLE001
        actor.set_editor_property(_pythonize(name), value)


class OmissionError(RuntimeError):
    """Something the run could not do, recorded with evidence instead of failing the run.
    A missing plugin rebuild is the case this exists for."""

    def __init__(self, message, evidence=None):
        RuntimeError.__init__(self, message)
        self.evidence = evidence or {}


def _asset_path(obj):
    if obj is None:
        return None
    return obj.get_path_name().split('.')[0]


def _static_mesh_box(mesh):
    box = mesh.get_bounding_box()
    return dict(min=[box.min.x, box.min.y, box.min.z], max=[box.max.x, box.max.y, box.max.z])


class Native(object):
    def __init__(self, ue, spec, target_name):
        self.ue = ue
        self.spec = spec
        self.target_name = target_name
        self.target = spec['targets'][target_name]
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.tools = ue.AssetToolsHelpers.get_asset_tools()
        self.ml = ue.MaterialEditingLibrary
        self.receipt = {}
        self.receipt_path = None

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=1, ensure_ascii=False),
                                     encoding='utf-8')

    # -- meshes ------------------------------------------------------------
    def import_mesh(self, entry, record, material):
        ue = self.ue
        settings = self.spec['importSettings']
        path = ROOT / self.spec['meshSourceFolder'] / record['file']
        if sha256_of(path) != record['sha256']:
            raise RuntimeError('Frozen OBJ hash changed: ' + record['file'])
        ui = ue.FbxImportUI()
        for key, value in settings['fbxImportUI'].items():
            if key == 'mesh_type_to_import':
                value = getattr(ue.FBXImportType, value)
            ui.set_editor_property(key, value)
        data = ui.get_editor_property('static_mesh_import_data')
        for key, value in settings['staticMeshImportData'].items():
            if key == 'normal_import_method':
                value = getattr(ue.FBXNormalImportMethod, value)
            data.set_editor_property(key, value)
        task = ue.AssetImportTask()
        for key, value in dict(filename=str(path), destination_path=self.spec['meshFolder'],
                               destination_name=entry['name'], automated=True, async_=False,
                               replace_existing=True, save=False, options=ui,
                               factory=ue.FbxFactory()).items():
            task.set_editor_property(key, value)
        self.tools.import_asset_tasks([task])
        objects = [o for o in list(task.get_objects()) if isinstance(o, ue.StaticMesh)]
        if len(objects) != 1:
            raise RuntimeError('Import of %s produced %s'
                               % (record['file'], [type(o).__name__ for o in list(task.get_objects())]))
        mesh = objects[0]

        box = _static_mesh_box(mesh)
        canonical = record['canonicalBoundsCm']
        error = box_error(box, canonical)
        # If the importer had NOT reflected Y back, the bounds would match this instead. Both
        # numbers go in the receipt so a future reader can tell a passing import from an
        # ambiguous one - a mesh symmetric about Y matches either way and proves nothing.
        plain = {'min': [canonical['min'][0], -canonical['max'][1], canonical['min'][2]],
                 'max': [canonical['max'][0], -canonical['min'][1], canonical['max'][2]]}
        unreflected = box_error(box, plain)
        tolerance = float(self.spec['verification']['boundsToleranceCm'])
        if error > tolerance:
            raise RuntimeError('%s imported bounds differ from canonical by %.4f cm '
                               '(unreflected %.4f): %r; the Y-reflect adapter convention no '
                               'longer holds and every instance would be mirrored'
                               % (entry['name'], error, unreflected, box))
        triangles = mesh.get_num_triangles(0)
        if triangles != record['triangles']:
            raise RuntimeError('%s imported %d triangles, the manifest says %d'
                               % (entry['name'], triangles, record['triangles']))
        slots = len(mesh.get_editor_property('static_materials'))
        for slot in range(slots):
            mesh.set_material(slot, material)
        wrong = [s for s in range(slots) if _asset_path(mesh.get_material(s)) != _asset_path(material)]
        if slots != 1 or wrong:
            raise RuntimeError('%s has %d material slots (want exactly 1) and %s unassigned'
                               % (entry['name'], slots, wrong))
        if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + entry['name'])
        asset = self.spec['meshFolder'] + '/' + entry['name']
        return dict(name=entry['name'], asset=asset, triangles=triangles,
                    importedBoundsCm=box, canonicalBoundsCm=canonical,
                    boundsErrorCm=round(error, 6), unreflectedBoundsErrorCm=round(unreflected, 6),
                    material=_asset_path(material), materialSlots=slots,
                    nanite=bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
                    if hasattr(mesh, 'get_editor_property') else None,
                    uassetSha256=sha256_of(disk_path(asset)))

    # -- materials ---------------------------------------------------------
    def _custom(self, material, code, output_type, input_names):
        ue = self.ue
        node = self.ml.create_material_expression(material, ue.MaterialExpressionCustom)
        node.set_editor_property('Code', code)
        node.set_editor_property('OutputType', output_type)
        pins = []
        for name in input_names:
            pin = ue.CustomInput()
            pin.set_editor_property('InputName', name)
            pins.append(pin)
        node.set_editor_property('Inputs', pins)
        got = [str(pin.get_editor_property('InputName')) for pin in node.get_editor_property('Inputs')]
        if got != list(input_names):
            raise RuntimeError('Custom node inputs read back as %r, wanted %r' % (got, input_names))
        if node.get_editor_property('Code') != code:
            raise RuntimeError('Custom node code did not take')
        return node

    def _per_instance(self, material, index, default=0.0):
        """A per-instance custom data float. 5.8 setters return False even on success, and
        the property name for the slot has moved between versions, so every candidate is
        tried and the value is proved by readback rather than trusted."""
        ue = self.ue
        node = self.ml.create_material_expression(material, ue.MaterialExpressionPerInstanceCustomData)
        for name in ('DataIndex', 'data_index'):
            try:
                node.set_editor_property(name, index)
            except Exception:                                          # noqa: BLE001
                continue
            try:
                if int(node.get_editor_property(name)) == index:
                    break
            except Exception:                                          # noqa: BLE001
                continue
        else:
            raise RuntimeError('Could not set the custom-data slot index on a '
                               'MaterialExpressionPerInstanceCustomData; the property has moved')
        for name in ('const_default_value', 'ConstDefaultValue', 'DefaultValue'):
            try:
                node.set_editor_property(name, default)
                break
            except Exception:                                          # noqa: BLE001
                continue
        return node

    def build_paving_master(self):
        """The one new material. It samples the APPROVED texture at the approved 500 cm with
        the approved roughness and metallic, and adds only a rotation and an origin taken from
        per-instance custom data. The approved M_JerusalemPaving_500cm is never edited: its
        graph is asserted node for node by release_jerusalem_paving.py, and its mapping is a
        frozen unparameterised Custom node with MIRROR addressing, which over 1.44 km is a 5 m
        tile with a 10 m mirror period and axis-aligned symmetry lines - the grid the decision
        was made to get rid of."""
        ue = self.ue
        cfg = self.spec['materials']['deck']
        asset = cfg['asset']
        folder, name = asset.rsplit('/', 1)
        if self.assets.does_asset_exist(asset):
            material = ue.load_asset(asset)
            if not isinstance(material, ue.Material):
                raise RuntimeError('Existing asset at %s is not a Material' % asset)
            return material, dict(asset=asset, reused=True,
                                  readback=self.paving_graph(material),
                                  uassetSha256=sha256_of(disk_path(asset)))
        texture = ue.load_asset(cfg['texture'])
        if texture is None:
            raise RuntimeError('The approved paving texture is missing: ' + cfg['texture'])
        material = self.tools.create_asset(name, folder, ue.Material, ue.MaterialFactoryNew())
        if material is None:
            raise RuntimeError('Material creation failed for ' + asset)
        material.set_editor_property('blend_mode', ue.BlendMode.BLEND_OPAQUE)

        world = self.ml.create_material_expression(material, ue.MaterialExpressionWorldPosition)
        data = [self._per_instance(material, index) for index in range(5)]
        uv = self._custom(material, UV_CODE, ue.CustomMaterialOutputType.CMOT_FLOAT2,
                          ['P', 'Cs', 'Sn', 'U0', 'V0'])
        sample = self.ml.create_material_expression(material, ue.MaterialExpressionTextureSample)
        sample.set_editor_property('Texture', texture)
        tint = self._custom(material, TINT_CODE, ue.CustomMaterialOutputType.CMOT_FLOAT3, ['C', 'T'])
        rough = self.ml.create_material_expression(material, ue.MaterialExpressionConstant)
        rough.set_editor_property('R', float(cfg['roughness']))
        metal = self.ml.create_material_expression(material, ue.MaterialExpressionConstant)
        metal.set_editor_property('R', float(cfg['metallic']))

        wiring = [
            (world, '', uv, 'P'),
            (data[0], '', uv, 'Cs'), (data[1], '', uv, 'Sn'),
            (data[2], '', uv, 'U0'), (data[3], '', uv, 'V0'),
            (uv, '', sample, 'UVs'),
            (sample, '', tint, 'C'), (data[4], '', tint, 'T'),
        ]
        for source, source_pin, dest, dest_pin in wiring:
            # 5.8 returns False even on success; the graph snapshot below is the proof.
            self.ml.connect_material_expressions(source, source_pin, dest, dest_pin)
        for node, prop in ((tint, ue.MaterialProperty.MP_BASE_COLOR),
                           (rough, ue.MaterialProperty.MP_ROUGHNESS),
                           (metal, ue.MaterialProperty.MP_METALLIC)):
            self.ml.connect_material_property(node, '', prop)
        for usage in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            self.ml.set_base_material_usage(material, getattr(ue.MaterialUsage, usage), True)
        errors = [str(e) for e in list(self.ml.recompile_material(material))]
        if errors:
            raise RuntimeError('Material compiler on %s: %r' % (asset, errors))
        readback = self.paving_graph(material)
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + asset)
        return material, dict(asset=asset, reused=False, readback=readback,
                              compileErrors=errors, uassetSha256=sha256_of(disk_path(asset)))

    def paving_graph(self, material):
        """Prove the graph is what the spec says, by reading it back. The two Custom nodes'
        code is compared as a STRING: a rotation that silently became an identity would look
        exactly like a working plaza until someone flew over the repeat."""
        ue = self.ue
        kinds = {}
        rows = {}
        for node in list(self.ml.get_material_expressions(material)):
            kind = node.get_class().get_name()
            kinds[kind] = kinds.get(kind, 0) + 1
            row = dict(kind=kind)
            if isinstance(node, ue.MaterialExpressionCustom):
                row['code'] = node.get_editor_property('Code')
                row['inputNames'] = [str(p.get_editor_property('InputName'))
                                     for p in node.get_editor_property('Inputs')]
            if isinstance(node, ue.MaterialExpressionConstant):
                row['value'] = node.get_editor_property('R')
            if isinstance(node, ue.MaterialExpressionTextureSample):
                texture = node.get_editor_property('Texture')
                row['texture'] = _asset_path(texture)
                row['srgb'] = texture.get_editor_property('srgb')
            if isinstance(node, ue.MaterialExpressionPerInstanceCustomData):
                for name in ('DataIndex', 'data_index'):
                    try:
                        row['dataIndex'] = int(node.get_editor_property(name))
                        break
                    except Exception:                                  # noqa: BLE001
                        continue
            rows[node.get_name()] = row
        codes = sorted(r['code'] for r in rows.values() if 'code' in r)
        if codes != sorted([UV_CODE, TINT_CODE]):
            raise RuntimeError('The plaza paving graph no longer carries the two expected '
                               'Custom nodes; found %r' % codes)
        slots = sorted(r['dataIndex'] for r in rows.values() if 'dataIndex' in r)
        if slots != [0, 1, 2, 3, 4]:
            raise RuntimeError('Per-instance custom data slots read back as %r, wanted 0..4; '
                               'without all five the plaza cannot rotate its panels' % slots)
        texture = [r.get('texture') for r in rows.values() if 'texture' in r]
        if texture != [self.spec['materials']['deck']['texture']]:
            raise RuntimeError('The plaza paving no longer samples the approved texture: %r' % texture)
        usages = {}
        for usage in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            usages[usage] = bool(self.ml.has_material_usage(material, getattr(ue.MaterialUsage, usage)))
            if not usages[usage]:
                raise RuntimeError('%s is not set on the plaza paving master' % usage)
        return dict(nodes=rows, kinds=kinds, usages=usages,
                    blendMode=str(material.get_editor_property('blend_mode')))

    def build_instance(self, role):
        """A MaterialInstanceConstant child of an APPROVED material, so the usage overrides a
        HISM needs are set on the child and the approved asset stays byte-identical."""
        ue = self.ue
        cfg = self.spec['materials'][role]
        asset = cfg['asset']
        folder, name = asset.rsplit('/', 1)
        parent = ue.load_asset(cfg['parent'])
        if parent is None:
            raise RuntimeError('The approved parent material is missing: ' + cfg['parent'])
        parent_sha = sha256_of(disk_path(cfg['parent']))
        if self.assets.does_asset_exist(asset):
            instance = ue.load_asset(asset)
            reused = True
        else:
            instance = self.tools.create_asset(name, folder, ue.MaterialInstanceConstant,
                                               ue.MaterialInstanceConstantFactoryNew())
            reused = False
        if not isinstance(instance, ue.MaterialInstanceConstant):
            raise RuntimeError('MaterialInstanceConstant factory failed for ' + asset)
        if _asset_path(instance.get_editor_property('parent')) != cfg['parent']:
            self.ml.set_material_instance_parent(instance, parent)
            if _asset_path(instance.get_editor_property('parent')) != cfg['parent']:
                instance.set_editor_property('parent', parent)
                self.ml.update_material_instance(instance)
        if _asset_path(instance.get_editor_property('parent')) != cfg['parent']:
            raise RuntimeError('Parent did not take on ' + asset)
        for usage in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES'):
            self.ml.set_material_usage_override(instance, getattr(ue.MaterialUsage, usage), True, True)
        self.ml.update_material_instance(instance)
        if not self.assets.save_loaded_asset(instance, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + asset)
        after = sha256_of(disk_path(cfg['parent']))
        if after != parent_sha:
            raise RuntimeError('The approved parent %s CHANGED while its instance was built' % cfg['parent'])
        return instance, dict(asset=asset, reused=reused, parent=cfg['parent'],
                              parentSha256Unchanged=True,
                              usages={u: bool(self.ml.has_material_usage(instance, getattr(ue.MaterialUsage, u)))
                                      for u in ('MATUSAGE_NANITE', 'MATUSAGE_INSTANCED_STATIC_MESHES')},
                              uassetSha256=sha256_of(disk_path(asset)))

    # -- the actor ---------------------------------------------------------
    def find_precinct_actor(self):
        ue = self.ue
        label = self.spec['enclosureActorLabel']
        world = self.editor.get_editor_world()
        found = [a for a in self.actors.get_all_level_actors()
                 if a is not None and a.get_actor_label() == label]
        if len(found) != 1:
            raise OmissionError(
                'Expected exactly one %s in %s, found %d. The plaza is components on the '
                'precinct actor, not an actor of its own, so there is nothing to place until '
                'Scripts/release_enclosure.py has run on this map.'
                % (label, world.get_outermost().get_name() if world else '?', len(found)),
                {'label': label, 'found': len(found)})
        return found[0]

    def plaza_properties_available(self, actor):
        """The plugin may predate the plaza. Ask the reflected class, do not assume."""
        missing = []
        for prop in ('bBuildPlaza', 'PlazaDeckTileMesh', 'PlazaWayTileMesh', 'PlazaRibMesh',
                     'PlazaKerbMesh', 'PlazaChannelMesh', 'PlazaRetainingBandMesh',
                     'PlazaStepMesh', 'PlazaPavingMaterial', 'PlazaSlabMaterial',
                     'PlazaAshlarMaterial', 'WallThicknessAmot'):
            try:
                _get_property(actor, prop)
            except Exception:                                          # noqa: BLE001
                missing.append(prop)
        return missing

    def apply_to_actor(self, actor, meshes, materials):
        missing = self.plaza_properties_available(actor)
        if missing:
            raise OmissionError(
                'AMikdashEnclosure in this editor has no plaza properties (%s). The '
                'MikdashRuntime plugin has not been rebuilt since Public/MikdashEnclosure.h '
                'and Private/MikdashEnclosure.cpp gained the plaza, so the class in this '
                'process cannot carry it. The meshes and materials above are imported, saved '
                'and reviewable; rebuild the editor target and re-run with -PlazaApply.'
                % ', '.join(missing[:4]),
                {'missingProperties': missing,
                 'importedMeshes': [m['asset'] for m in meshes],
                 'materials': {k: v['asset'] for k, v in materials.items()}})
        by_name = {m['name']: self.ue.load_asset(m['asset']) for m in meshes}
        _set_property(actor, 'bBuildPlaza', True)
        _set_property(actor, 'WallThicknessAmot', 6.0)
        for prop, mesh in (('PlazaDeckTileMesh', 'SM_PlazaV1_DeckTile'),
                           ('PlazaWayTileMesh', 'SM_PlazaV1_WayTile'),
                           ('PlazaRibMesh', 'SM_PlazaV1_Rib'),
                           ('PlazaKerbMesh', 'SM_PlazaV1_Kerb'),
                           ('PlazaChannelMesh', 'SM_PlazaV1_Channel'),
                           ('PlazaRetainingBandMesh', 'SM_PlazaV1_RetainingBand'),
                           ('PlazaStepMesh', 'SM_PlazaV1_Step')):
            _set_property(actor, prop, by_name[mesh])
        _set_property(actor, 'PlazaPavingMaterial', self.ue.load_asset(materials['deck']['asset']))
        _set_property(actor, 'PlazaSlabMaterial', self.ue.load_asset(materials['way']['asset']))
        _set_property(actor, 'PlazaAshlarMaterial', self.ue.load_asset(materials['ashlar']['asset']))
        # Build the ring and the plaza in the editor world WITHOUT hiding a single building,
        # so a commandlet never leaves an editor actor hidden and nothing it does is saved.
        actor.measure_without_hiding()
        return dict(applied=True, meshesSet=len(by_name))

    def read_back(self, actor, expected):
        """The actor's OWN numbers against plaza-<Target>.json. Not a screenshot, not a
        count of what we asked for: what the runtime arithmetic actually produced."""
        verify = self.spec['verification']
        result = dict(plazaStatus=str(actor.get_plaza_status()),
                      deckTopZcm=float(actor.get_plaza_deck_top_z_cm()),
                      triangles=int(actor.get_plaza_triangle_count()))
        if result['plazaStatus'] != 'built':
            raise RuntimeError('The placed actor reports plaza status %r, not "built"'
                               % result['plazaStatus'])
        counts = list(actor.get_plaza_counts())
        keys = ('deckTiles', 'wayTiles', 'ribModules', 'kerbModules', 'channelModules',
                'retainingBands', 'scarpBands', 'stepModules')
        result['counts'] = {key: int(value) for key, value in zip(keys, counts)}
        wanted = {key: int(expected['plan'][key]) for key in keys}
        if result['counts'] != wanted:
            raise RuntimeError('The placed actor built %r; the receipt says %r'
                               % (result['counts'], wanted))
        if abs(result['deckTopZcm'] - float(expected['deck']['topZcm'])) > float(verify['deckZToleranceCm']):
            raise RuntimeError('Deck top Z is %g, the receipt says %g'
                               % (result['deckTopZcm'], expected['deck']['topZcm']))
        extent = actor.get_plaza_extent_cm()
        result['extentCm'] = [float(getattr(extent, axis)) for axis in ('x', 'y', 'z', 'w')]
        for value, key in zip(result['extentCm'], ('xMinCm', 'yMinCm', 'xMaxCm', 'yMaxCm')):
            if abs(value - float(expected['grid'][key])) > float(verify['extentToleranceCm']):
                raise RuntimeError('Paved extent %s is %g, the receipt says %g'
                                   % (key, value, expected['grid'][key]))
        grid = list(actor.get_plaza_grid())
        result['cellsX'], result['cellsY'], result['panels'] = [int(v) for v in grid[:3]]
        if (result['cellsX'], result['cellsY']) != (int(expected['grid']['cellsX']),
                                                    int(expected['grid']['cellsY'])):
            raise RuntimeError('The placed actor laid a %dx%d grid, the receipt says %dx%d'
                               % (result['cellsX'], result['cellsY'],
                                  expected['grid']['cellsX'], expected['grid']['cellsY']))
        if result['panels'] != int(expected['panels']['count']):
            raise RuntimeError('The placed actor made %d super-panels, the receipt says %d. The '
                               'runtime and the generator are laying DIFFERENT plazas.'
                               % (result['panels'], expected['panels']['count']))
        result['facesPerSide'] = []
        tolerance = float(verify['faceHeightToleranceCm'])
        for side, row in enumerate(expected['retainingPerSide']):
            pair = actor.get_plaza_face_heights_cm(side)
            retaining, scarp = float(pair.x), float(pair.y)
            result['facesPerSide'].append(dict(side=row['name'],
                                               retainingCm=round(retaining, 2),
                                               scarpCm=round(scarp, 2)))
            if abs(retaining - float(row['retainingMaxCm'])) > tolerance:
                raise RuntimeError('%s retaining max is %g cm, the receipt says %g'
                                   % (row['name'], retaining, row['retainingMaxCm']))
            if abs(scarp - float(row['scarpMaxCm'])) > tolerance:
                raise RuntimeError('%s scarp max is %g cm, the receipt says %g'
                                   % (row['name'], scarp, row['scarpMaxCm']))
        if result['triangles'] != int(expected['plan']['triangles']['total']):
            raise RuntimeError('The placed actor draws %d plaza triangles, the receipt says %d'
                               % (result['triangles'], expected['plan']['triangles']['total']))
        return result


def run(target_name, mode):
    import unreal as ue
    spec = load_spec()
    config = target_config(spec, target_name)
    offline = offline_check(spec, target_name)

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    native = Native(ue, spec, target_name)
    if native.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
       ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed work')

    target_map = config['map']
    map_file = disk_path(target_map, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in config['protectedMaps']
                 if disk_path(m, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    native.receipt_path = receipt_folder / ('%s%s-%s-%s.json'
                                            % (spec['receiptPrefix'], mode, target_name, stamp))
    if native.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(native.receipt_path))

    checkpoint = None
    external_copied = []
    if mode == 'apply':
        checkpoint = Path(spec['checkpointRoot']) / ('%s%s-%s' % (spec['checkpointPrefix'],
                                                                  target_name, stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / target_map[6:]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / target_map[6:])
                external_copied.append(str(external))

    native.receipt = {
        'status': 'started_' + mode,
        'mode': mode, 'stamp': stamp, 'target': target_name, 'map': target_map,
        'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesSpecObservedSha256': map_sha_before == config.get('observedMapSha256'),
        'checkpoint': str(checkpoint) if checkpoint else None,
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'scriptSha256': sha256_of(Path(__file__)),
        'decision': spec['decision'],
        'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'meshes': [], 'materials': {}, 'actor': None, 'readback': None,
        'omissions': [], 'errors': [], 'mapSaved': False,
        'sourcedVersusAuthored': {
            'sourced': 'The extent only: Yechezkel 42:15-20 with 40:5 - 500 reeds of six amot, '
                       '3000 amot a side, measured from outside.',
            'user': spec['decision'],
            'authored': 'The deck datum\'s consequences, the paving layout and its '
                        'anti-repetition scheme, the drainage, the retaining and scarp '
                        'construction, the processional ways and the gate stairs.'},
        'limitations': spec['limitations'],
    }
    native.write_receipt()

    saved = False
    try:
        if mode in ('apply', 'verify'):
            if not native.levels.load_level(target_map):
                raise RuntimeError('load_level failed for ' + target_map)
            world = native.editor.get_editor_world()
            loaded = world.get_outermost().get_name()
            if loaded != target_map:
                raise RuntimeError('Loaded world %s is not the target map %s' % (loaded, target_map))

        expected = json.loads((ROOT / config['plazaReceipt']).read_text(encoding='utf-8-sig'))

        if mode in ('assets', 'apply'):
            materials = {}
            _paving, materials['deck'] = native.build_paving_master()
            _way, materials['way'] = native.build_instance('way')
            _ashlar, materials['ashlar'] = native.build_instance('ashlar')
            native.receipt['materials'] = materials
            native.write_receipt()

            by_name = {row['name']: row for row in offline['meshes']}
            role_asset = {'deck': materials['deck']['asset'], 'way': materials['way']['asset'],
                          'ashlar': materials['ashlar']['asset']}
            for entry in spec['meshes']:
                material = ue.load_asset(role_asset[entry['material']])
                native.receipt['meshes'].append(
                    native.import_mesh(entry, by_name[entry['name']], material))
                native.write_receipt()
        else:
            materials = {role: dict(asset=spec['materials'][role]['asset'])
                         for role in ('deck', 'way', 'ashlar')}

        if mode == 'apply':
            try:
                actor = native.find_precinct_actor()
                native.receipt['actor'] = native.apply_to_actor(actor, native.receipt['meshes'], materials)
                native.write_receipt()

                if not native.levels.save_current_level():
                    raise RuntimeError('save_current_level returned False')
                saved = True
                native.receipt['mapSaved'] = True
                native.receipt['mapSha256AfterSave'] = sha256_of(map_file)
                native.write_receipt()

                if not native.levels.load_level(target_map):
                    raise RuntimeError('Reopen failed')
                reopened = native.find_precinct_actor()
                reopened.measure_without_hiding()
                native.receipt['readback'] = native.read_back(reopened, expected)
                native.receipt['status'] = 'plaza_saved_reopened_visual_acceptance_pending'
            except OmissionError as omission:
                native.receipt['omissions'].append(dict(stage='actor', message=str(omission),
                                                        evidence=omission.evidence))
                native.receipt['status'] = 'meshes_and_materials_only_actor_omitted_rebuild_required'
        elif mode == 'verify':
            actor = native.find_precinct_actor()
            actor.measure_without_hiding()
            native.receipt['readback'] = native.read_back(actor, expected)
            native.receipt['status'] = 'plaza_verified_map_unchanged'
        else:
            native.receipt['status'] = 'plaza_assets_imported_map_unchanged'
    except Exception as error:
        native.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        native.receipt['status'] = ('FAILED_AFTER_SAVE_CHECKPOINT_AVAILABLE' if saved
                                    else 'FAILED_BEFORE_SAVE_MAP_UNCHANGED')
        raise
    finally:
        native.receipt['mapSha256After'] = sha256_of(map_file)
        native.receipt['mapBytesChanged'] = native.receipt['mapSha256After'] != map_sha_before
        native.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
        if mode in ('assets', 'verify') and native.receipt['mapBytesChanged']:
            native.receipt['errors'].append(
                {'stage': 'finally',
                 'error': 'Mode %s must not change the target map, and it did.' % mode})
        native.write_receipt()
    return native.receipt


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
    return 'release_precinct_plaza.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    target_name = target_from_command_line(command_line)
    mode = mode_from_command_line(command_line)
    if not mode:
        raise RuntimeError('Choose exactly one mode: %s' % list(MODE_FLAGS))
    try:
        receipt = run(target_name, mode)
        ue.log('release_precinct_plaza[%s/%s]: %s; meshes %d; omissions %d'
               % (target_name, mode, receipt['status'], len(receipt['meshes']),
                  len(receipt['omissions'])))
    except Exception as error:
        ue.log_error('release_precinct_plaza failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line.lower() and '-run=pythonscript' not in command_line.lower():
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        import sys
        if '--write-spec' in sys.argv:
            print(json.dumps(write_spec(), indent=2))
        else:
            print(json.dumps(offline_check(target=target_from_command_line(' '.join(sys.argv[1:]))),
                             indent=2))
elif _invoked_as_native_script():
    _main()

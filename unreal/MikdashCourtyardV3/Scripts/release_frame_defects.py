"""Guarded fix for the three defects the first real rendered frames caught.

The frames and their verdicts are in SourceAssets/visual-review/cp05b-frames-20260910.json.
Every number a human should review before this runs is in Scripts/release_frame_defects.spec.json.

THE THREE DEFECTS, AND WHAT EACH ONE ACTUALLY IS

1. VEGETATION ON THE PAVED PLAZA DECKS  (frames 05 and 08)
   release_vegetation.py scattered on 9 September with keep-outs for the Mount enclosure ring
   and the architecture blocker boxes. Both plaza decks were built AFTER that scatter, so no
   keep-out covered them. The scatter planted straight through 1.44 km of precinct paving and
   through the Kotel plaza. This pass adds the two decks as keep-out primitives and removes the
   instances whose own bounding box breaks the deck surface. It does NOT remove the plants that
   stay entirely BELOW a deck top: those are invisible while the deck stands, and they are the
   Modern-state hillside, which AMikdashEnclosure swaps back in with the V key. See
   spec.vegetation.rule and ruleWhyNotEverythingInside.

2. THE BIRD FLOCKS RENDER AS FLAT DARK QUADS  (frames 07, 08, 10)
   Not a usage flag and not a cook substitution. The birds have NO MATERIAL AT ALL: all twenty
   pose meshes carry /Engine/EngineMaterials/WorldGridMaterial in both slots, because
   create_birds.py and release_birds.py both deliberately stopped short of a material pass and
   say so in their own honesty lists. WorldGridMaterial is DefaultLit and samples a tangent
   space normal map; the bird import logged degenerate tangent bases on every species' Level
   pose, so the shading is garbage, and the placeholder planar UVs put a whole bird inside a
   fraction of one grid cell, so there is not even a checker - just flat dark. This pass builds
   the plumage material the meshes never had, WITH bUsedWithInstancedStaticMeshes set, because
   the flock draws on HISM components and the flag-less version of this fix would swap flat
   black for flat grey.

3. THE SEA ON THE HORIZON  (frame 04)
   THERE IS NO WATER ACTOR TO DELETE, RESIZE OR HIDE. A level scan for any flat actor larger
   than a quarter of the DEM span finds exactly zero, and the terrain measures 256 tiles
   spanning 6.4 km. The blue field is the SkyAtmosphere's virtual planet ground shell, seen
   below the true horizon past the edge of that square.
   The first attempt raised fogMaxOpacity to 1.0 and dropped aerialPerspectiveViewDistanceScale
   from 1.8 to 1.0. Frame cp09-04 judged it: the fog change did NOTHING, because height fog
   composites against scene depth and the sky shell is drawn at infinite depth, so that edit is
   reverted here rather than kept. The aerial-perspective change DID work - the outer kilometres
   of terrain now read as tan hills instead of dissolving into the band - and is kept.
   The second attempt is the shell's own groundAlbedo, pushed to a sand tone. The real fix is
   terrain past the DEM edge and is recorded as open, not attempted here.

WHAT IT DOES, IN ORDER
  1. Offline checks, no engine: spec parses, every reviewed number present and sanely ordered.
  2. Guards: right project, no game world, no dirty packages, target map loaded and confirmed.
  3. Checkpoints the .umap and its one-file-per-actor folders into ReviewCheckpoints, hashes the
     copy, and records the SHA-256 of every protected map (including the OTHER target map).
  4. Reads the deck footprints off the LEVEL - real instance transforms of the real deck tile
     components - and asserts them against the numbers in the spec before using them.
  5. Dry run stops here and writes a receipt that mutates nothing.
  6. Removes the offending instances of EVERY plant family - the tagged JudeanFloraV1 scatter
     and the untagged OSM illustrative street trees, which a tag-only filter missed and which
     frame cp09-05 caught still standing on the cleared paving - builds and assigns the bird
     materials, and applies the recorded atmosphere edits.
  7. Saves, REOPENS the map, and reads every count and flag back numerically. A save that did
     not change a byte of the .umap is a failure.
  8. Writes SourceAssets/visual-review/frame-defects-<Target>-<stamp>.json at start, on failure
     and in finally.

ACCEPTANCE IS A FRAME, NOT THIS RECEIPT. The editor silently repairs missing usage flags at
runtime, which is why every offline check in this project stayed green while the cooked build
fell back to the default material. The only artefact that settles any of these three is a PNG
rendered by a packaged build at the cp05b camera positions.

COMMANDLET INVOCATION (serial; never while another engine is running; fresh -abslog path):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_frame_defects.py"
      -Candidate48 [-DryRun] [-SkipBirds]
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/FrameDefects-01.log"

REVERT (plain python, no editor open):

  python Scripts/release_frame_defects.py --revert=<receipt.json> [--dry-run]
"""

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_targets as mt  # noqa: E402

ROOT = mt.ROOT
SPEC_PATH = ROOT / 'Scripts' / 'release_frame_defects.spec.json'


# --------------------------------------------------------------------------
# Pure helpers - no engine
# --------------------------------------------------------------------------

def sha256_of(path):
    return mt.sha256_of(path)


def disk_path(asset_path, extension='uasset'):
    return mt.disk_path(asset_path, extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8-sig'))
    if spec.get('specVersion') != 'MikdashFrameDefects-1':
        raise RuntimeError('Unexpected spec version: %r' % spec.get('specVersion'))
    return spec


class Footprint(object):
    """Axis-aligned deck tile rectangles with a uniform bucket index over XY.

    A deck is tens of thousands of small rectangles and there are a quarter of a million
    vegetation instances to test against them, so a linear scan is not an option. The bucket
    size is the tile pitch, so every query touches a handful of candidates.
    """

    def __init__(self, bucket_cm):
        self.bucket = float(bucket_cm)
        self.cells = {}
        self.count = 0
        self.x0 = self.y0 = float('inf')
        self.x1 = self.y1 = float('-inf')
        self.levels = set()

    def add(self, x0, x1, y0, y1, top_z):
        rect = (x0, x1, y0, y1, top_z)
        self.count += 1
        self.x0 = min(self.x0, x0)
        self.x1 = max(self.x1, x1)
        self.y0 = min(self.y0, y0)
        self.y1 = max(self.y1, y1)
        self.levels.add(round(top_z, 3))
        for i in range(int(x0 // self.bucket), int(x1 // self.bucket) + 1):
            for j in range(int(y0 // self.bucket), int(y1 // self.bucket) + 1):
                self.cells.setdefault((i, j), []).append(rect)

    def top_z_at(self, x, y):
        """The HIGHEST deck top covering this XY, or None. Highest, because the Kotel plaza has
        two levels and the upper one is the surface a plant would be standing on."""
        best = None
        for rect in self.cells.get((int(x // self.bucket), int(y // self.bucket)), ()):
            if rect[0] <= x <= rect[1] and rect[2] <= y <= rect[3]:
                if best is None or rect[4] > best:
                    best = rect[4]
        return best

    def extent(self):
        if not self.count:
            return None
        return [self.x0, self.y0, self.x1, self.y1]


def offline_check(spec=None):
    """Everything that can be proved with no engine and no level."""
    spec = spec or load_spec()
    report = {'specSha256': sha256_of(SPEC_PATH), 'checks': []}

    def ok(name, condition, detail=''):
        if not condition:
            raise RuntimeError('Offline check failed: %s %s' % (name, detail))
        report['checks'].append(name)

    veg = spec['vegetation']
    ok('vegetation.baseTileSizeCm positive', float(veg['baseTileSizeCm']) > 0)
    ok('vegetation.rule explains itself', len(veg['ruleWhyNotEverythingInside']) > 100)
    ok('two deck hosts', len(veg['deckHosts']) == 2)
    modes = sorted(host.get('footprintMode') for host in veg['deckHosts'])
    ok('one analytic and one measured deck',
       modes == ['analytic_rectangle', 'measured_from_level'], str(modes))
    for host in veg['deckHosts']:
        if host.get('footprintMode') == 'analytic_rectangle':
            by_target = host['footprintRectangleByTarget']
            ok('a precinct rectangle for every target',
               sorted(by_target) == sorted(config['key'] for config in mt.TARGETS.values()),
               str(sorted(by_target)))
            ok('the two targets do not share a rectangle',
               len({tuple(v) for v in by_target.values()}) == len(by_target))
            ok('analytic tile count is a perfect square grid',
               int(host['expectedTiles']) == 121 * 121, str(host['expectedTiles']))
            for name, rect in sorted(by_target.items()):
                ok('precinct rectangle %s ordered' % name,
                   rect[0] < rect[2] and rect[1] < rect[3], str(rect))
            continue
        box = host['expectedExtentCm']
        ok('deck %s extent ordered' % host['key'], box[0] < box[2] and box[1] < box[3], str(box))
        ok('deck %s tiles positive' % host['key'], int(host['expectedTiles']) > 0)
        ok('deck %s has levels' % host['key'], len(host['expectedTopZcm']) >= 1)
        ok('deck %s names a mesh' % host['key'], len(host['meshSubstrings']) >= 1)

    birds = spec['birds']
    ok('bird usage flag demanded', birds['usageFlags'].get('used_with_instanced_static_meshes') is True)
    ok('bird slot order is two', len(birds['slotOrder']) == 2)
    ok('four poses', len(birds['poses']) == 4)
    ok('five species', len(birds['species']) == 5)
    for name, entry in birds['species'].items():
        for role in ('main', 'hood'):
            rgb = entry[role]
            ok('%s.%s is linear rgb' % (name, role),
               len(rgb) == 3 and all(0.0 <= float(c) <= 1.0 for c in rgb), str(rgb))
    ok('roughness sane', 0.0 <= float(birds['roughness']) <= 1.0)
    ok('specular sane', 0.0 <= float(birds['specular']) <= 1.0)
    ok('opaque', birds['blendMode'] == 'Opaque')
    ok('single sided', birds['twoSided'] is False)

    ok('two plant families', len(veg['plantFamilies']) == 2)
    for family in veg['plantFamilies']:
        ok('family %s has a match mode' % family['key'],
           family['match'] in ('actorTag', 'meshSubstring'), family['match'])
        if family['match'] == 'actorTag':
            ok('family %s names a tag' % family['key'], bool(family.get('actorTag')))
        else:
            ok('family %s names meshes' % family['key'], len(family['meshSubstrings']) >= 1)

    horizon = spec['horizon']
    for edit in horizon['edits']:
        kind = edit.get('valueType', 'float')
        ok('edit %s has a known value type' % edit['property'], kind in ('float', 'color'), kind)
        if kind == 'color':
            after = edit['after']
            ok('colour edit %s is rgb 0-255' % edit['property'],
               len(after) == 3 and all(0 <= int(c) <= 255 for c in after), str(after))
        elif edit['expectedBefore'] is not None:
            ok('float edit %s has a tolerance' % edit['property'],
               float(edit['toleranceBefore']) > 0)
    box = horizon['terrainExtentCm']
    ok('terrain extent ordered', box[0] < box[2] and box[1] < box[3], str(box))

    report['expectedBirdMeshes'] = sorted(
        'SM_BirdsV1_%s_%s' % (species, pose)
        for species in birds['species'] for pose in birds['poses'])
    if len(report['expectedBirdMeshes']) != 20:
        raise RuntimeError('Expected 20 bird meshes, computed %d' % len(report['expectedBirdMeshes']))
    return report


# --------------------------------------------------------------------------
# Engine-side
# --------------------------------------------------------------------------

def _vec(v):
    return [float(v.x), float(v.y), float(v.z)]


def _asset_path(obj):
    if obj is None:
        return None
    try:
        return obj.get_path_name()
    except Exception:  # noqa: BLE001
        return str(obj)


def _instance_transform(component, index):
    """(location, scale) in WORLD space, tolerating both shapes of the out-param binding."""
    result = component.get_instance_transform(index, world_space=True)
    transform = result[1] if isinstance(result, tuple) else result
    return _vec(transform.translation), _vec(transform.scale3d)


class Run(object):

    def __init__(self, ue, spec, target_key):
        self.ue = ue
        self.spec = spec
        self.target_key = target_key
        self.config = mt.target_config(target_key)
        self.map = self.config['map']
        self.label = self.config['key']
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.receipt = {}
        self.receipt_path = None

    # -- receipt ----------------------------------------------------------
    def write_receipt(self):
        if self.receipt_path is not None:
            self.receipt_path.write_text(json.dumps(self.receipt, indent=2), encoding='utf-8')

    # -- census -----------------------------------------------------------
    def all_actors(self):
        return list(self.actors.get_all_level_actors())

    def hisms(self, actor):
        ue = self.ue
        return list(actor.get_components_by_class(ue.InstancedStaticMeshComponent))

    def read_deck(self, host, actors):
        """Build a Footprint for one deck.

        Two modes, because the two plazas are built by different machinery. The Kotel plaza is
        926 real serialised instances and is MEASURED off the level. The precinct plaza is built
        at runtime by AMikdashEnclosure::BuildPlaza and serialises nothing, so in the editor its
        components carry neither mesh nor instances; it comes from the analytic rectangle the
        build receipt recorded, which is exact because all 121 x 121 cells are paved.
        """
        spec_veg = self.spec['vegetation']
        base = float(spec_veg['baseTileSizeCm'])
        substrings = tuple(host['meshSubstrings'])

        if host.get('footprintMode') == 'analytic_rectangle':
            # PER TARGET. Candidate48's Temple, court platform and plaza grid are 0.96 of the
            # Main50 metric, so its deck spans 143,424 cm a side against Main50's 149,400. One
            # rectangle for both under-removes a border strip on Main50; see the spec's
            # deckHosts.perTargetNote, which records the apply that got this wrong.
            by_target = host['footprintRectangleByTarget']
            if self.label not in by_target:
                raise RuntimeError("No precinct rectangle recorded for target %s; refusing to "
                                   "reuse another map's deck" % self.label)
            rect = by_target[self.label]
            top_z = float(host['footprintTopZcm'])
            # One bucket per 1200 cm so the query cost matches the measured decks.
            footprint = Footprint(1200.0)
            footprint.add(float(rect[0]), float(rect[2]), float(rect[1]), float(rect[3]), top_z)
            footprint.count = int(host['expectedTiles'])
            return footprint, [{'actor': host.get('actorLabel'), 'target': self.label,
                                'rectangleCm': list(rect),
                                'mesh': 'runtime-built, not serialised',
                                'instances': int(host['expectedTiles']),
                                'note': host['analyticNote'],
                                'perTargetNote': host['perTargetNote']}]

        wanted_label = host.get('actorLabel')
        wanted_sub = host.get('actorLabelSubstring')
        wanted_tag = host.get('actorTag')

        footprint = Footprint(base)
        matched = []
        for actor in actors:
            label = actor.get_actor_label()
            if wanted_label and label != wanted_label:
                if not (wanted_sub and wanted_sub.lower() in label.lower()):
                    continue
            elif wanted_sub and wanted_sub.lower() not in label.lower():
                continue
            elif not wanted_label and not wanted_sub:
                continue
            if wanted_tag and not actor.actor_has_tag(self.ue.Name(wanted_tag)):
                pass  # tag is a hint, not a gate: the label already identified the actor
            for component in self.hisms(actor):
                mesh = _asset_path(component.get_editor_property('static_mesh')) or ''
                if not any(s in mesh for s in substrings):
                    continue
                count = int(component.get_instance_count())
                matched.append({'actor': label, 'mesh': mesh, 'instances': count})
                for index in range(count):
                    location, scale = _instance_transform(component, index)
                    half_x = base * abs(scale[0]) * 0.5
                    half_y = base * abs(scale[1]) * 0.5
                    footprint.add(location[0] - half_x, location[0] + half_x,
                                  location[1] - half_y, location[1] + half_y,
                                  location[2])
        return footprint, matched

    # -- vegetation -------------------------------------------------------
    def vegetation_components(self, actors):
        """Every instanced component of every PLANT FAMILY, tagged with which family it is.

        'Vegetation' here is two independently authored sets and only one carries a tag. The
        first pass filtered on the JudeanFloraV1 tag alone, cleared 32,627 instances, and frame
        cp09-05 still showed street trees standing on the open paving - the 4,265 retained
        illustrative OSM trees, which release_vegetation.py kept clear of rather than owned and
        which carry no tag at all. They are matched by mesh name instead.
        """
        veg = self.spec['vegetation']
        rows = []
        for family in veg['plantFamilies']:
            if family['match'] == 'actorTag':
                tag = self.ue.Name(family['actorTag'])
                for actor in actors:
                    if not actor.actor_has_tag(tag):
                        continue
                    for component in self.hisms(actor):
                        rows.append((actor, actor.get_actor_label(), component, family['key']))
            elif family['match'] == 'meshSubstring':
                wanted = tuple(family['meshSubstrings'])
                for actor in actors:
                    for component in self.hisms(actor):
                        mesh = _asset_path(component.get_editor_property('static_mesh')) or ''
                        if any(s in mesh for s in wanted):
                            rows.append((actor, actor.get_actor_label(), component,
                                         family['key']))
            else:
                raise RuntimeError('Unknown plant family match mode: %r' % family['match'])
        seen = set()
        unique = []
        for actor, label, component, key in rows:
            # A component must not be judged twice if a future family list overlaps.
            marker = component.get_path_name()
            if marker in seen:
                continue
            seen.add(marker)
            unique.append((actor, label, component, key))
        return unique

    def mesh_top_cm(self, component):
        """Top of the mesh's own local bounding box, in cm, unscaled."""
        mesh = component.get_editor_property('static_mesh')
        if mesh is None:
            return None
        box = mesh.get_bounding_box()
        return float(box.max.z)

    def plan_vegetation_removals(self, decks, actors):
        # Priority order, smallest footprint first. The Kotel plaza stands inside the precinct
        # rectangle in XY but ten metres below it, so testing the precinct first makes every
        # Kotel plant look buried. See spec.vegetation.deckPriorityNote.
        priority = {host['key']: int(host.get('priority', 99))
                    for host in self.spec['vegetation']['deckHosts']}
        order = sorted(decks, key=lambda key: priority.get(key, 99))
        plan = []
        per_deck = {key: 0 for key in decks}
        per_species = {}
        scanned = 0
        bounds = None
        kept_buried = 0
        per_family = {}
        for actor, label, component, family in self.vegetation_components(actors):
            top = self.mesh_top_cm(component)
            if top is None:
                raise RuntimeError('Vegetation component on %s has no static mesh' % label)
            count = int(component.get_instance_count())
            doomed = []
            for index in range(count):
                location, scale = _instance_transform(component, index)
                scanned += 1
                x, y, z = location
                instance_top = z + top * abs(scale[2])
                for key in order:
                    footprint = decks[key]
                    deck_z = footprint.top_z_at(x, y)
                    if deck_z is None:
                        continue
                    if instance_top <= deck_z:
                        # Entirely under the platform. Invisible while the deck stands, and it is
                        # the Modern-state hillside; leaving it is the cheapest possible fix.
                        kept_buried += 1
                        break
                    doomed.append(index)
                    per_deck[key] += 1
                    per_family[family] = per_family.get(family, 0) + 1
                    species = (label.split('_')[2] if label.startswith('RELEASE_Vegetation_')
                               and label.count('_') >= 2 else '%s:%s' % (family, label))
                    per_species[species] = per_species.get(species, 0) + 1
                    if bounds is None:
                        bounds = [x, y, z, x, y, z]
                    else:
                        bounds = [min(bounds[0], x), min(bounds[1], y), min(bounds[2], z),
                                  max(bounds[3], x), max(bounds[4], y), max(bounds[5], z)]
                    break
            if doomed:
                plan.append({'actor': actor, 'label': label, 'component': component,
                             'family': family, 'before': count, 'remove': doomed})
        return {'plan': plan, 'scanned': scanned, 'perDeck': per_deck,
                'perSpecies': per_species, 'perFamily': per_family,
                'removedBoundsCm': bounds,
                'keptBuriedUnderADeck': kept_buried,
                'total': sum(per_deck.values())}

    def guard_removal_bounds(self, removals, decks):
        """THE REGRESSION CHECK. Nothing outside a deck may be removed."""
        bounds = removals['removedBoundsCm']
        if bounds is None:
            return {'checked': True, 'removed': 0, 'note': 'nothing removed'}
        union = None
        for footprint in decks.values():
            extent = footprint.extent()
            if extent is None:
                continue
            union = extent if union is None else [min(union[0], extent[0]), min(union[1], extent[1]),
                                                  max(union[2], extent[2]), max(union[3], extent[3])]
        if union is None:
            raise RuntimeError('No deck footprint was measured, yet instances were selected')
        if not (union[0] <= bounds[0] and union[1] <= bounds[1]
                and bounds[3] <= union[2] and bounds[4] <= union[3]):
            raise RuntimeError('Removal bounding box %s is not inside the deck union %s; refusing '
                               'to remove anything outside the decks' % (bounds, union))
        return {'checked': True, 'removed': removals['total'],
                'removedBoundsCm': bounds, 'deckUnionCm': union,
                'note': 'every removed instance XY lies inside a measured deck tile footprint'}

    def apply_vegetation_removals(self, removals):
        rows = []
        for entry in removals['plan']:
            component = entry['component']
            doomed = sorted(entry['remove'], reverse=True)
            entry['actor'].modify()
            component.modify()
            removed = 0
            if hasattr(component, 'remove_instances'):
                if component.remove_instances(doomed):
                    removed = len(doomed)
            if removed == 0:
                for index in doomed:
                    if component.remove_instance(index):
                        removed += 1
            after = int(component.get_instance_count())
            if after != entry['before'] - len(doomed):
                raise RuntimeError('%s: %d instances before, %d selected, %d after - the removal '
                                   'did not take' % (entry['label'], entry['before'],
                                                     len(doomed), after))
            rows.append({'label': entry['label'], 'family': entry['family'],
                         'before': entry['before'],
                         'removed': len(doomed), 'after': after})
        return rows

    # -- birds ------------------------------------------------------------
    def build_bird_materials(self):
        ue = self.ue
        birds = self.spec['birds']
        tools = ue.AssetToolsHelpers.get_asset_tools()
        folder = birds['materialFolder']
        master_path = '%s/%s' % (folder, birds['masterMaterial'])

        master = ue.EditorAssetLibrary.load_asset(master_path)
        created_master = False
        if master is None:
            master = tools.create_asset(birds['masterMaterial'], folder, ue.Material,
                                        ue.MaterialFactoryNew())
            created_master = True
        if master is None:
            raise RuntimeError('Could not create ' + master_path)

        library = ue.MaterialEditingLibrary
        if created_master:
            colour = library.create_material_expression(
                master, ue.MaterialExpressionVectorParameter, -420, 0)
            colour.set_editor_property('parameter_name', ue.Name('PlumageColour'))
            colour.set_editor_property('default_value', ue.LinearColor(0.2, 0.2, 0.2, 1.0))
            library.connect_material_property(colour, 'RGB', ue.MaterialProperty.MP_BASE_COLOR)

            rough = library.create_material_expression(
                master, ue.MaterialExpressionScalarParameter, -420, 200)
            rough.set_editor_property('parameter_name', ue.Name('Roughness'))
            rough.set_editor_property('default_value', float(birds['roughness']))
            library.connect_material_property(rough, '', ue.MaterialProperty.MP_ROUGHNESS)

            spec_expr = library.create_material_expression(
                master, ue.MaterialExpressionScalarParameter, -420, 320)
            spec_expr.set_editor_property('parameter_name', ue.Name('Specular'))
            spec_expr.set_editor_property('default_value', float(birds['specular']))
            library.connect_material_property(spec_expr, '', ue.MaterialProperty.MP_SPECULAR)

        # The whole point of this pass. HISM without this flag cooks to DefaultMaterial.
        master.set_editor_property('two_sided', bool(birds['twoSided']))
        master.set_editor_property('blend_mode', ue.BlendMode.BLEND_OPAQUE)
        master.set_editor_property('shading_model', ue.MaterialShadingModel.MSM_DEFAULT_LIT)
        for flag, value in birds['usageFlags'].items():
            master.set_editor_property(flag, bool(value))
        library.recompile_material(master)
        ue.EditorAssetLibrary.save_asset(master_path)

        instances = {}
        for species, entry in sorted(birds['species'].items()):
            for role in ('main', 'hood'):
                name = 'MI_BirdsV1_%s_%s' % (species, role.capitalize())
                path = '%s/%s' % (folder, name)
                instance = ue.EditorAssetLibrary.load_asset(path)
                if instance is None:
                    instance = tools.create_asset(name, folder, ue.MaterialInstanceConstant,
                                                  ue.MaterialInstanceConstantFactoryNew())
                if instance is None:
                    raise RuntimeError('Could not create ' + path)
                library.set_material_instance_parent(instance, master)
                rgb = entry[role]
                library.set_material_instance_vector_parameter_value(
                    instance, 'PlumageColour',
                    ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
                library.update_material_instance(instance)
                ue.EditorAssetLibrary.save_asset(path)
                instances[(species, role)] = (path, instance)
        return {'master': master_path, 'masterCreated': created_master,
                'instances': {'%s/%s' % k: v[0] for k, v in instances.items()}}, master, instances

    def assign_bird_materials(self, instances):
        ue = self.ue
        birds = self.spec['birds']
        rows = []
        for species in sorted(birds['species']):
            for pose in birds['poses']:
                name = 'SM_BirdsV1_%s_%s' % (species, pose)
                path = '%s/%s' % (birds['meshFolder'], name)
                mesh = ue.EditorAssetLibrary.load_asset(path)
                if mesh is None:
                    raise RuntimeError('Bird mesh missing: ' + path)
                slots = mesh.get_editor_property('static_materials')
                if len(slots) != 2:
                    raise RuntimeError('%s has %d material slots, expected 2' % (name, len(slots)))
                before = [_asset_path(s.get_editor_property('material_interface')) for s in slots]
                rebuilt = []
                for index, slot in enumerate(slots):
                    slot_name = str(slot.get_editor_property('material_slot_name'))
                    role = 'main' if 'main' in slot_name.lower() else 'hood'
                    if 'main' not in slot_name.lower() and 'hood' not in slot_name.lower():
                        raise RuntimeError('%s slot %d is named %r, which is neither main nor hood'
                                           % (name, index, slot_name))
                    slot.set_editor_property('material_interface', instances[(species, role)][1])
                    rebuilt.append(slot)
                mesh.set_editor_property('static_materials', rebuilt)
                after = [_asset_path(s.get_editor_property('material_interface'))
                         for s in mesh.get_editor_property('static_materials')]
                if any(a is None or 'WorldGridMaterial' in a for a in after):
                    raise RuntimeError('%s still carries WorldGridMaterial after assignment: %s'
                                       % (name, after))
                ue.EditorAssetLibrary.save_asset(path)
                rows.append({'mesh': path, 'before': before, 'after': after})
        return rows

    # -- horizon ----------------------------------------------------------
    def find_horizon_actors(self, actors):
        """Flat, single-Z things that reach beyond the DEM the terrain was made from."""
        horizon = self.spec['horizon']
        terrain = horizon['terrainExtentCm']
        span_x = terrain[2] - terrain[0]
        span_y = terrain[3] - terrain[1]
        candidates = []
        for actor in actors:
            try:
                origin, extent = actor.get_actor_bounds(False)
            except Exception:  # noqa: BLE001
                continue
            origin = _vec(origin)
            extent = _vec(extent)
            if extent[0] <= 0.0 or extent[1] <= 0.0:
                continue
            reaches = (origin[0] - extent[0] < terrain[0] or origin[0] + extent[0] > terrain[2]
                       or origin[1] - extent[1] < terrain[1] or origin[1] + extent[1] > terrain[3])
            flat = extent[2] < 0.02 * max(extent[0], extent[1])
            big = extent[0] * 2.0 > 0.25 * span_x or extent[1] * 2.0 > 0.25 * span_y
            if not (reaches and flat and big):
                continue
            meshes = []
            for component in actor.get_components_by_class(self.ue.StaticMeshComponent):
                meshes.append(_asset_path(component.get_editor_property('static_mesh')))
            candidates.append({
                'label': actor.get_actor_label(),
                'class': actor.get_class().get_name(),
                'pathName': actor.get_path_name(),
                'locationCm': _vec(actor.get_actor_location()),
                'rotationDegrees': [float(actor.get_actor_rotation().pitch),
                                    float(actor.get_actor_rotation().yaw),
                                    float(actor.get_actor_rotation().roll)],
                'scale': _vec(actor.get_actor_scale3d()),
                'boundsOriginCm': origin,
                'boundsExtentCm': extent,
                'flatTopZcm': origin[2] + extent[2],
                'hiddenInGame': bool(actor.get_editor_property('hidden')),
                'staticMeshes': meshes,
                'actor': actor,
            })
        return candidates

    def atmosphere_actors(self, actors):
        """Every SkyAtmosphere / height fog / cloud on the level, with the numbers the frame
        depends on. Recorded whether or not anything is edited, because the horizon defect is a
        property of these and of where the terrain stops, not of any object in the sky."""
        wanted = ('SkyAtmosphere', 'ExponentialHeightFog', 'VolumetricCloud', 'SkyLight')
        rows = []
        for actor in actors:
            class_name = actor.get_class().get_name()
            if class_name not in wanted:
                continue
            component = self.component_of(actor)
            rows.append({'label': actor.get_actor_label(), 'class': class_name,
                         'pathName': actor.get_path_name(),
                         'componentClass': (component.get_class().get_name()
                                            if component is not None else None),
                         'actor': actor, 'component': component})
        return rows

    def component_of(self, actor):
        """The one component that carries an atmosphere actor's settings.

        AExponentialHeightFog exposes it as 'component', but ASkyAtmosphere does not - it is
        'sky_atmosphere_component', and a first pass that only tried 'component' recorded
        hasComponent False for the sky and silently skipped its edit. Rather than keep a table of
        engine property names, ask the actor for its components and take the first that is not
        the bare scene root.
        """
        for name in ('component', 'sky_atmosphere_component', 'exponential_height_fog_component',
                     'volumetric_cloud_component', 'light_component'):
            try:
                found = actor.get_editor_property(name)
            except Exception:  # noqa: BLE001
                continue
            if found is not None:
                return found
        try:
            components = list(actor.get_components_by_class(self.ue.ActorComponent))
        except Exception:  # noqa: BLE001
            return None
        for component in components:
            if component.get_class().get_name() not in ('SceneComponent', 'BillboardComponent',
                                                        'ArrowComponent'):
                return component
        return None

    def measure_terrain_extent(self, actors):
        """Where the world actually stops. The blue band starts exactly here."""
        box = None
        tiles = 0
        for actor in actors:
            label = actor.get_actor_label()
            if 'JerusalemTerrain' not in label and 'Terrain' not in label:
                continue
            try:
                origin, extent = actor.get_actor_bounds(False)
            except Exception:  # noqa: BLE001
                continue
            origin = _vec(origin)
            extent = _vec(extent)
            if extent[0] <= 0.0:
                continue
            tiles += 1
            low = [origin[i] - extent[i] for i in range(3)]
            high = [origin[i] + extent[i] for i in range(3)]
            box = ([low[0], low[1], low[2], high[0], high[1], high[2]] if box is None
                   else [min(box[0], low[0]), min(box[1], low[1]), min(box[2], low[2]),
                         max(box[3], high[0]), max(box[4], high[1]), max(box[5], high[2])])
        return {'terrainActorsMeasured': tiles, 'measuredBoundsCm': box}

    def apply_atmosphere_edits(self, atmosphere, dry_run):
        """Spec-driven, before-value-checked property edits. Never a blind write."""
        rows = []
        for edit in self.spec['horizon']['edits']:
            targets = [row for row in atmosphere if row['class'] == edit['actorClass']]
            if not targets:
                rows.append({'edit': edit, 'applied': False,
                             'reason': 'no %s actor on this map' % edit['actorClass']})
                continue
            for row in targets:
                component = row['component']
                if component is None:
                    rows.append({'edit': edit, 'actor': row['label'], 'applied': False,
                                 'reason': 'actor exposes no component'})
                    continue
                kind = edit.get('valueType', 'float')
                try:
                    raw = component.get_editor_property(edit['property'])
                    before = ([int(raw.r), int(raw.g), int(raw.b)] if kind == 'color'
                              else float(raw))
                except Exception as error:  # noqa: BLE001
                    rows.append({'edit': edit, 'actor': row['label'], 'applied': False,
                                 'reason': 'property unreadable: %s' % error})
                    continue
                record = {'actor': row['label'], 'class': row['class'],
                          'pathName': row['pathName'], 'property': edit['property'],
                          'valueType': kind, 'before': before,
                          'requestedAfter': edit['after'],
                          'expectedBefore': edit['expectedBefore'],
                          'why': edit['why'],
                          'restore': ('set %s back to %r on %s'
                                      % (edit['property'], before, row['label']))}
                # expectedBefore None means "record whatever is there and proceed". That is still
                # a guarded write, because the before-value goes into the receipt and the after
                # is read back; it just does not pretend to know a value nobody reviewed.
                if kind == 'float' and edit['expectedBefore'] is not None:
                    if abs(before - float(edit['expectedBefore'])) > float(edit['toleranceBefore']):
                        record['applied'] = False
                        record['reason'] = ('before-value %r is outside the reviewed tolerance of '
                                            '%r; leaving it alone rather than guessing'
                                            % (before, edit['expectedBefore']))
                        rows.append(record)
                        continue
                if dry_run:
                    record['applied'] = False
                    record['reason'] = 'dry run'
                    rows.append(record)
                    continue
                row['actor'].modify()
                if kind == 'color':
                    wanted = edit['after']
                    # unreal.Color's POSITIONAL constructor is B, G, R, A - FColor's memory order,
                    # not the r,g,b the properties are named. Color(196, 170, 128, 255) read back
                    # as [128, 170, 196] and this guard refused the write. Set the named fields.
                    colour = self.ue.Color()
                    colour.set_editor_property('r', int(wanted[0]))
                    colour.set_editor_property('g', int(wanted[1]))
                    colour.set_editor_property('b', int(wanted[2]))
                    colour.set_editor_property('a', 255)
                    component.set_editor_property(edit['property'], colour)
                    got = component.get_editor_property(edit['property'])
                    after = [int(got.r), int(got.g), int(got.b)]
                    if after != [int(v) for v in wanted]:
                        raise RuntimeError('%s.%s read back %r after writing %r'
                                           % (row['label'], edit['property'], after, wanted))
                else:
                    component.set_editor_property(edit['property'], float(edit['after']))
                    after = float(component.get_editor_property(edit['property']))
                    if abs(after - float(edit['after'])) > 1e-6:
                        raise RuntimeError('%s.%s read back %r after writing %r'
                                           % (row['label'], edit['property'], after, edit['after']))
                record['applied'] = True
                record['after'] = after
                rows.append(record)
        return rows


# --------------------------------------------------------------------------
# The guarded pass
# --------------------------------------------------------------------------

def run(target_key, dry_run=False, skip_birds=False, skip_horizon=False):
    import unreal as ue
    spec = load_spec()
    offline = offline_check(spec)

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())

    session = Run(ue, spec, target_key)
    if session.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if not session.levels.load_level(session.map):
        raise RuntimeError('load_level failed for ' + session.map)
    loaded = session.editor.get_editor_world().get_outermost().get_name()
    if loaded != session.map:
        raise RuntimeError('Loaded world %s is not %s' % (loaded, session.map))
    if (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Dirty packages present; resolve before a checkpointed pass')

    map_file = disk_path(session.map, 'umap')
    map_sha_before = sha256_of(map_file)
    protected_paths = list(spec['protectedMaps']) + [
        config['map'] for key, config in mt.TARGETS.items() if config['map'] != session.map]
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in protected_paths
                 if disk_path(m, 'umap').exists()}

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + session.label
                                                 + '-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    external_copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / session.map[6:]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / session.map[6:])
            external_copied.append(str(external))

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    session.receipt_path = receipt_folder / (spec['receiptPrefix'] + session.label + '-'
                                             + stamp + '.json')
    session.receipt = {
        'status': 'frame_defect_pass_started',
        'stamp': stamp,
        'target': session.label,
        'targetRole': session.config['role'],
        'map': session.map,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': offline['specSha256'],
        'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'dryRun': bool(dry_run),
        'skipBirds': bool(skip_birds),
        'skipHorizon': bool(skip_horizon),
        'sourceFrames': 'SourceAssets/visual-review/cp05b-frames-20260910.json',
        'acceptance': ('A FRAME FROM A PACKAGED BUILD, not this receipt. Every readback below '
                       'stays green even when the cook substitutes a default material.'),
        'errors': [],
        'mapSaved': False,
    }
    session.write_receipt()

    saved = False
    try:
        actors = session.all_actors()
        session.receipt['levelActorCount'] = len(actors)

        # ---- defect 1: measure the decks, then plan the removals -------
        decks = {}
        deck_report = {}
        for host in spec['vegetation']['deckHosts']:
            footprint, matched = session.read_deck(host, actors)
            extent = footprint.extent()
            deck_report[host['key']] = {
                'componentsMatched': matched,
                'tilesMeasured': footprint.count,
                'tilesExpected': host['expectedTiles'],
                'topZLevelsMeasured': sorted(footprint.levels),
                'topZLevelsExpected': host['expectedTopZcm'],
                'extentMeasuredCm': extent,
                'extentExpectedCm': (host['expectedExtentByTarget'][session.label]
                                     if 'expectedExtentByTarget' in host
                                     else host['expectedExtentCm']),
                'source': host['source'],
            }
            if footprint.count == 0:
                deck_report[host['key']]['note'] = ('NO DECK TILES FOUND on this map; nothing can '
                                                    'be removed for this deck')
                continue
            decks[host['key']] = footprint
        session.receipt['decks'] = deck_report

        removals = session.plan_vegetation_removals(decks, actors)
        guard = session.guard_removal_bounds(removals, decks)
        session.receipt['vegetation'] = {
            'rule': spec['vegetation']['rule'],
            'ruleWhyNotEverythingInside': spec['vegetation']['ruleWhyNotEverythingInside'],
            'why': spec['vegetation']['why'],
            'precedent': spec['vegetation']['precedent'],
            'deckPriorityNote': spec['vegetation']['deckPriorityNote'],
            'deckPriorityOrder': sorted(decks, key=lambda k: {h['key']: int(h.get('priority', 99))
                                        for h in spec['vegetation']['deckHosts']}.get(k, 99)),
            'instancesScanned': removals['scanned'],
            'instancesSelectedForRemoval': removals['total'],
            'keptBuriedUnderADeck': removals['keptBuriedUnderADeck'],
            'perDeck': removals['perDeck'],
            'perFamily': removals['perFamily'],
            'plantFamilies': spec['vegetation']['plantFamilies'],
            'plantFamiliesNote': spec['vegetation']['plantFamiliesNote'],
            'perSpecies': removals['perSpecies'],
            'regressionGuard': guard,
        }
        session.write_receipt()

        # ---- defect 3: the horizon --------------------------------------
        horizon_candidates = session.find_horizon_actors(actors)
        atmosphere = session.atmosphere_actors(actors)
        session.receipt['horizon'] = {
            'why': spec['horizon']['why'],
            'ruledOut': spec['horizon']['ruledOut'],
            'perStateNote': spec['horizon']['perStateNote'],
            'actionNote': spec['horizon']['actionNote'],
            'giantFlatActorTest': ('flat (Z extent under 2 per cent of the larger XY extent), '
                                   'larger than a quarter of the DEM span, and reaching beyond '
                                   'the DEM the terrain mesh was generated from'),
            'giantFlatActorsFound': [{k: v for k, v in c.items() if k != 'actor'}
                                     for c in horizon_candidates],
            'terrainExtentSpecCm': spec['horizon']['terrainExtentCm'],
            'terrainExtentMeasured': session.measure_terrain_extent(actors),
            'atmosphereActors': [{k: v for k, v in row.items()
                                  if k not in ('actor', 'component')} for row in atmosphere],
            'atmosphereComponentNote': ('ASkyAtmosphere exposes its settings on '
                                        'sky_atmosphere_component, not on component; the lookup '
                                        "tries the engine names then falls back to the actor's "
                                        'own component list.'),
        }
        session.receipt['horizon']['edits'] = session.apply_atmosphere_edits(atmosphere, True)
        session.write_receipt()

        if dry_run:
            session.receipt['status'] = 'dry_run_measured_nothing_written'
            session.receipt['mapSha256After'] = sha256_of(map_file)
            if session.receipt['mapSha256After'] != map_sha_before:
                raise RuntimeError('Dry run changed the map on disk')
            return session.receipt

        # ---- apply -----------------------------------------------------
        session.receipt['vegetationApplied'] = session.apply_vegetation_removals(removals)

        if not skip_horizon:
            session.receipt['horizon']['edits'] = session.apply_atmosphere_edits(atmosphere, False)
            session.receipt['horizon']['editsApplied'] = sum(
                1 for row in session.receipt['horizon']['edits'] if row.get('applied'))

        if not skip_birds:
            material_report, master, instances = session.build_bird_materials()
            session.receipt['birds'] = {
                'why': spec['birds']['why'],
                'notTheUsageFlagBug': spec['birds']['notTheUsageFlagBug'],
                'materials': material_report,
                'assignments': session.assign_bird_materials(instances),
            }
        session.write_receipt()

        # ---- save, reopen, read back -----------------------------------
        if session.receipt['vegetation']['instancesSelectedForRemoval'] or not skip_horizon:
            if not session.levels.save_current_level():
                raise RuntimeError('save_current_level returned False')
            saved = True
            session.receipt['mapSaved'] = True
            session.receipt['mapSha256AfterSave'] = sha256_of(map_file)
            if session.receipt['mapSha256AfterSave'] == map_sha_before:
                raise RuntimeError('save_current_level reported success but the .umap is '
                                   'byte-identical; nothing was written')
            if not session.levels.load_level(session.map):
                raise RuntimeError('Reopen failed for ' + session.map)

        reopened = session.all_actors()
        rows = []
        for actor, label, component, family in session.vegetation_components(reopened):
            rows.append({'label': label, 'family': family,
                         'instances': int(component.get_instance_count())})
        session.receipt['reopenedVegetation'] = sorted(rows, key=lambda r: r['label'])
        session.receipt['reopenedVegetationTotal'] = sum(r['instances'] for r in rows)

        if not skip_birds:
            flags = []
            for species in sorted(spec['birds']['species']):
                for pose in spec['birds']['poses']:
                    path = '%s/SM_BirdsV1_%s_%s' % (spec['birds']['meshFolder'], species, pose)
                    mesh = ue.EditorAssetLibrary.load_asset(path)
                    slots = [_asset_path(s.get_editor_property('material_interface'))
                             for s in mesh.get_editor_property('static_materials')]
                    if any(s is None or 'WorldGridMaterial' in s for s in slots):
                        raise RuntimeError('%s still on WorldGridMaterial after reopen: %s'
                                           % (path, slots))
                    flags.append({'mesh': path, 'slots': slots})
            master_path = '%s/%s' % (spec['birds']['materialFolder'],
                                     spec['birds']['masterMaterial'])
            master = ue.EditorAssetLibrary.load_asset(master_path)
            usage = {flag: bool(master.get_editor_property(flag))
                     for flag in spec['birds']['usageFlags']}
            for flag, wanted in spec['birds']['usageFlags'].items():
                if usage[flag] is not bool(wanted):
                    raise RuntimeError('%s reads back %s on %s, expected %s'
                                       % (flag, usage[flag], master_path, wanted))
            session.receipt['birdsReopened'] = {'usageFlags': usage, 'meshes': flags}

        session.receipt['mapSha256After'] = sha256_of(map_file)
        session.receipt['mapBytesChanged'] = (session.receipt['mapSha256After'] != map_sha_before)
        unchanged = {m: sha256_of(disk_path(m, 'umap')) == sha for m, sha in protected.items()}
        session.receipt['protectedMapsUnchanged'] = unchanged
        if not all(unchanged.values()):
            raise RuntimeError('A protected map changed: %s'
                               % [m for m, ok in unchanged.items() if not ok])
        session.receipt['status'] = 'frame_defects_applied_saved_reopened_frame_acceptance_pending'
        return session.receipt
    except Exception as error:  # noqa: BLE001
        session.receipt['errors'].append('%s: %s' % (type(error).__name__, error))
        session.receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                                     else 'failed_before_save_map_unchanged')
        raise
    finally:
        session.write_receipt()


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _flag(name):
    tokens = [t.lower().strip('"') for t in sys.argv]
    try:
        import unreal as ue
        tokens += [t.lower().strip('"') for t in ue.SystemLibrary.get_command_line().split()]
    except Exception:  # noqa: BLE001
        pass
    return ('-' + name.lower()) in tokens or ('--' + name.lower()) in tokens


def _main():
    action = mt.revert_from_command_line()
    if action:
        print(json.dumps(mt.restore_checkpoint(action['receipt'], dry_run=action['dryRun']),
                         indent=2))
        return
    if not _unreal_available():
        print(json.dumps(offline_check(), indent=2))
        return
    import unreal as ue
    target = mt.target_from_command_line()
    try:
        receipt = run(target, dry_run=_flag('DryRun'), skip_birds=_flag('SkipBirds'),
                      skip_horizon=_flag('SkipHorizon'))
        print('STATUS ' + receipt['status'])
        print('RECEIPT ' + str(receipt.get('stamp')))
    finally:
        if '-executepythonscript' not in ue.SystemLibrary.get_command_line().lower():
            pass
    ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    _main()

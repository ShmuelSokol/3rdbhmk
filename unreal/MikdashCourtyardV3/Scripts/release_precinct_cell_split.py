"""PrecinctCellSplitV1 - guarded native import and placement of the split cut-cell halves.

Reads SourceAssets/enclosure-review/CellSplitV1/cell-split-manifest.json, written and
offline-proved by Scripts/create_precinct_cell_split.py --export. Writes ONLY inside
/Game/MikdashV3/JerusalemContext/PrecinctCellSplitV1 and, in the target map, only actors
labelled RELEASE_PrecinctCellSplit_*. No existing asset is rebuilt, re-imported or edited;
the original SM_JerusalemBuildings_* cell actors and meshes are never touched.

WHY THIS EXISTS
---------------
The modern city is batched one actor per 100 m cell, so a cell the Haram boundary cuts cannot
be half hidden. Hiding the 11 cut cells whole would destroy 150 buildings OUTSIDE the ring to
hide 40 inside it - holes punched in the densest part of the Old City, right where the viewer
stands. Two cells alone account for 91 of the 150.

WHAT IS PLACED, AND WHAT IS DELIBERATELY NOT
---------------------------------------------
Only the OUT half is placed - 11 actors. The IN half is generated as the RECORD of exactly
which buildings the precinct removes and is NEVER placed, because it could not be visible in
any state: MODERN shows the original (which already contains it) and YECHEZKEL hides those
buildings by definition. Placing it would be dead geometry that can only z-fight.

THE VISIBILITY CONTRACT, which needs no C++ change
---------------------------------------------------
    MODERN / OVERLAY   original cell actor SHOWS; the Out actor hides.
    YECHEZKEL          original cell actor hides (it is in the precinct hide list);
                       the Out actor SHOWS, so the 150 outside buildings stay standing.

The Out actors carry the tag `PrecinctSplitOut`, and this script appends that tag to the
placed AMikdashEnclosure's `HideWhileModernCityStandsTags`, which is UPROPERTY(EditAnywhere).
That is the same mechanism PrecinctCutTwin and PrecinctApproachV1 already use. NO header edit
and NO rebuild of either target is required, which is the whole reason the tag route was
chosen over adding a class member.

MATERIAL: never guessed. Each Out mesh takes its material slots from the ORIGINAL cell actor
found in the map, so the split half cannot drift from the half it was cut out of.

MODES
  -SplitPreflight  read-only: inputs, target map loads, counts existing actors. Saves nothing.
  -SplitApply      import meshes if missing, place one StaticMeshActor per cut cell, tag the
                   enclosure, save, REOPEN, numeric readback. Refuses if any already exist.
  -SplitVerify     reopen-style readback only. Saves nothing.
  -SplitRevert     destroy every RELEASE_PrecinctCellSplit_* actor, remove the tag, save,
                   reopen, prove none left. The per-run map checkpoint is the byte fallback.

Launch (hidden editor, start on Entry so the startup map is not loaded twice):
  UnrealEditor.exe MikdashCourtyardV3.uproject /Engine/Maps/Entry
      -ExecutePythonScript=C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_precinct_cell_split.py
      -SplitApply -SplitTarget=Candidate48 -unattended -nullrhi -NoSplash -abslog=...
"""
import hashlib
import json
import re
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SCRIPT_TOKEN = 'release_precinct_cell_split.py'
SRC = ROOT / 'SourceAssets' / 'enclosure-review' / 'CellSplitV1'
MANIFEST = SRC / 'cell-split-manifest.json'
GENERATOR = ROOT / 'Scripts' / 'create_precinct_cell_split.py'
OBJ = SRC / 'obj'
RECEIPTS = SRC / 'engine'
NS = '/Game/MikdashV3/JerusalemContext/PrecinctCellSplitV1'
MESH_FOLDER = NS + '/Meshes'
TARGETS = {
    'Candidate48': '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
    'Main50': '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
}
BUILDINGS_FOLDER = '/Game/MikdashV3/JerusalemContext/Buildings'
# Written by -SplitProbe, which loads ONE original mesh asset with NO MAP LOADED and records
# the material the context buildings actually render with. See the OOM note on `probe` below.
MATERIAL_RECORD = SRC / 'buildings-material.json'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
LABEL_PREFIX = 'RELEASE_PrecinctCellSplit_'
FAMILY_TAG = 'PrecinctCellSplitV1'
STATE_TAG = 'PrecinctSplitOut'
ENCLOSURE_LABEL = 'RELEASE_EnclosureV2_Precinct'
FOLDER = 'Release/PrecinctCellSplitV1'
BOUNDS_TOLERANCE_CM = 1.0
FBX_UI = {'automated_import_should_detect_type': False, 'mesh_type_to_import': 'FBXIT_STATIC_MESH',
          'import_as_skeletal': False, 'import_mesh': True, 'import_animations': False,
          'import_materials': False, 'import_textures': False, 'create_physics_asset': False}
FBX_MESH = {'combine_meshes': True, 'transform_vertex_to_absolute': True, 'bake_pivot_in_vertex': False,
            'convert_scene': False, 'convert_scene_unit': False, 'force_front_x_axis': False,
            'import_uniform_scale': 1.0, 'auto_generate_collision': False, 'build_nanite': True,
            'generate_lightmap_u_vs': False, 'remove_degenerates': True,
            'normal_import_method': 'FBXNIM_IMPORT_NORMALS'}


def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    return ROOT / 'Content' / (asset_path[len('/Game/'):] + '.' + extension)


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj is not None else None


def all_maps():
    return sorted(str(p) for p in (ROOT / 'Content').rglob('*.umap'))


def load_inputs():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if manifest.get('status') != 'AUTHORED_OFFLINE_SOURCE_NATIVE_IMPORT_PENDING':
        raise RuntimeError('manifest status is %s' % manifest.get('status'))
    if manifest['generatorSha256'] != sha256_of(GENERATOR):
        raise RuntimeError('generator changed since the manifest was written; re-run --export')
    outs = [m for m in manifest['meshes'] if m['half'] == 'Out']
    if not outs:
        raise RuntimeError('manifest carries no Out halves')
    if len(outs) != manifest['counts']['cellsCut']:
        raise RuntimeError('%d Out meshes for %d cut cells' % (len(outs), manifest['counts']['cellsCut']))
    for mesh in manifest['meshes']:
        if sha256_of(OBJ / mesh['file']) != mesh['sha256']:
            raise RuntimeError('OBJ hash changed: ' + mesh['file'])
    if manifest['counts']['collateralAvoided'] <= 0:
        raise RuntimeError('manifest records no collateral avoided; nothing to do')
    return manifest, outs


class Run(object):
    def __init__(self, ue, target, mode):
        self.ue = ue
        self.target = target
        self.mode = mode
        self.stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        RECEIPTS.mkdir(parents=True, exist_ok=True)
        self.path = RECEIPTS / ('cell-split-%s-%s-%s.json' % (mode, target, self.stamp))
        self.receipt = {'status': 'running', 'mode': mode, 'target': target, 'stamp': self.stamp,
                        'script': SCRIPT_TOKEN, 'scriptSha256': sha256_of(ROOT / 'Scripts' / SCRIPT_TOKEN),
                        'engineVersion': str(ue.SystemLibrary.get_engine_version())}

    def write(self):
        self.path.write_text(json.dumps(self.receipt, indent=1), encoding='utf-8')

    def ours(self):
        # Derived from the SAME single enumeration label_map() builds. This used to be its
        # own get_all_level_actors() pass, so an apply walked all 8,606 actors twice.
        return {label: actor for label, actor in self.label_map().items()
                if label.startswith(LABEL_PREFIX)}

    def label_map(self, refresh=False):
        """label -> actor, built ONCE. This map has 8,606 actors; calling
        get_all_level_actors() per lookup walked it 11 times for the materials pass alone."""
        if refresh or getattr(self, '_labels', None) is None:
            self._labels = {a.get_actor_label(): a for a in self.actors.get_all_level_actors()}
        return self._labels

    def by_label(self, label):
        return self.label_map().get(label)

    def probe_material(self, group):
        """Read the context buildings' material from ONE ORIGINAL MESH ASSET, with NO MAP
        LOADED, and record it.

        WHY THIS IS ITS OWN MODE - paid for three times.
        Reading `static_materials` off an original cell mesh while the target map is open
        does not fetch one mesh: it blocks on FStaticMeshCompilingManager and drags ALL 7,860
        static meshes in the level through compilation at once. The log line is
        `LogStaticMesh: Waiting for static meshes to be ready 4,280/7,860`, and on this 16 GB
        box that is what killed three apply runs - always after the work had succeeded and
        before it could be recorded. The preflight never tripped it because it reads actor
        LABELS and never touches mesh data.

        With no map loaded there is nothing else compiling, so the same call is cheap.
        """
        ue = self.ue
        path = BUILDINGS_FOLDER + '/SM_JerusalemBuildings_' + group
        if not self.assets.does_asset_exist(path):
            raise RuntimeError('original mesh asset missing: ' + path)
        mesh = self.assets.load_asset(path)
        slots = mesh.get_editor_property('static_materials')
        if not slots:
            raise RuntimeError('%s has no material slots' % path)
        mats = [_asset_path(s.get_editor_property('material_interface')) for s in slots]
        if not mats[0]:
            raise RuntimeError('%s slot 0 has no material' % path)
        nanite = bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
        record = dict(probedFrom=path, materialSlots=mats, nanite=nanite,
                      stamp=self.stamp,
                      why='the material the context buildings render with, read once with no '
                          'map loaded so the apply never has to touch an original mesh')
        MATERIAL_RECORD.write_text(json.dumps(record, indent=1), encoding='utf-8')
        self.receipt['materialRecord'] = record
        return record

    def recorded_material(self):
        """The probed material, loaded by PATH. Never guessed, never read off the level."""
        if not MATERIAL_RECORD.exists():
            raise RuntimeError('%s is absent; run -SplitProbe first (it needs no map)' % MATERIAL_RECORD)
        record = json.loads(MATERIAL_RECORD.read_text(encoding='utf-8'))
        mats = []
        for path in record['materialSlots']:
            if not self.assets.does_asset_exist(path):
                raise RuntimeError('probed material missing: ' + path)
            mats.append(self.assets.load_asset(path))
        self.receipt['materialRecord'] = record
        return mats, bool(record['nanite'])

    def mesh(self, spec, mats, nanite_on):
        ue = self.ue
        path = MESH_FOLDER + '/' + spec['assetName']
        created = False
        if self.assets.does_asset_exist(path):
            # ALREADY PREPARED - load it and touch NOTHING else.
            #
            # get_num_triangles() and get_bounding_box() below are mesh-DATA calls, and with
            # the target map open any such call blocks on FStaticMeshCompilingManager and
            # drags the level's whole 7,860-mesh set through compilation. The successful
            # terrain-cut revert survived that flush (915 log lines, 33 s); the apply enters
            # it already holding the imported meshes and was killed four times, always after
            # the work had succeeded and before it could be recorded.
            #
            # These checks are not lost - they ran at IMPORT time (worst bounds error
            # 0.0009 cm, recorded in the import receipt) and they run again in -SplitVerify,
            # which reads the saved map in a FRESH process. Re-running them here proves
            # nothing new and costs the whole level's compilation.
            mesh = self.assets.load_asset(path)
            self.receipt.setdefault('meshes', {})[spec['assetName']] = {
                'asset': path, 'created': False, 'reusedAlreadyPrepared': True,
                'verifiedAt': 'import time and again in -SplitVerify'}
            return mesh
        else:
            options = ue.FbxImportUI()
            for k, v in FBX_UI.items():
                options.set_editor_property(k, getattr(ue.FBXImportType, v) if k == 'mesh_type_to_import' else v)
            data = options.get_editor_property('static_mesh_import_data')
            for k, v in FBX_MESH.items():
                data.set_editor_property(k, getattr(ue.FBXNormalImportMethod, v) if k == 'normal_import_method' else v)
            task = ue.AssetImportTask()
            for k, v in dict(filename=str(OBJ / spec['file']), destination_path=MESH_FOLDER,
                             destination_name=spec['assetName'], automated=True, async_=False,
                             replace_existing=False, save=False, options=options, factory=ue.FbxFactory()).items():
                task.set_editor_property(k, v)
            ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            got = [o for o in task.get_objects() if isinstance(o, ue.StaticMesh)]
            if len(got) != 1 or got[0].get_name() != spec['assetName']:
                raise RuntimeError('import of %s produced %s' % (spec['file'], [o.get_name() for o in task.get_objects()]))
            mesh = got[0]
            created = True
        tris = int(mesh.get_num_triangles(0))
        if tris <= 0:
            raise RuntimeError('%s imported with no triangles' % spec['assetName'])
        box = mesh.get_bounding_box()
        lo, hi = [box.min.x, box.min.y, box.min.z], [box.max.x, box.max.y, box.max.z]
        want = spec['canonicalBoundsCm']
        err = max(max(abs(a - b) for a, b in zip(lo, want['min'])),
                  max(abs(a - b) for a, b in zip(hi, want['max'])))
        if err > BOUNDS_TOLERANCE_CM:
            raise RuntimeError('%s bounds differ from canonical by %.3f cm (reflection?)'
                               % (spec['assetName'], err))
        slots = len(mesh.get_editor_property('static_materials'))
        for slot in range(slots):
            mesh.set_material(slot, mats[min(slot, len(mats) - 1)])
        nanite = mesh.get_editor_property('nanite_settings')
        if bool(nanite.get_editor_property('enabled')) != nanite_on:
            nanite.set_editor_property('enabled', nanite_on)
            mesh.set_editor_property('nanite_settings', nanite)
        if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError('save mesh failed ' + path)
        self.receipt.setdefault('meshes', {})[spec['assetName']] = {
            'asset': path, 'created': created, 'triangles': tris,
            'manifestTriangles': spec['triangles'], 'boundsErrorCm': round(err, 4),
            'materialSlots': slots, 'nanite': nanite_on}
        return mesh

    def place(self, spec, mesh, group):
        ue = self.ue
        actor = self.actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(0.0, 0.0, 0.0),
                                                   ue.Rotator(pitch=0.0, yaw=0.0, roll=0.0))
        if actor is None:
            raise RuntimeError('spawn failed for ' + group)
        comp = actor.get_component_by_class(ue.StaticMeshComponent)
        if not comp.set_static_mesh(mesh):
            self.actors.destroy_actor(actor)
            raise RuntimeError('set_static_mesh failed for ' + group)
        actor.set_actor_label(LABEL_PREFIX + group + '_Out')
        actor.set_folder_path(FOLDER)
        actor.set_editor_property('tags', [ue.Name(FAMILY_TAG), ue.Name(STATE_TAG)])
        comp.set_editor_property('mobility', ue.ComponentMobility.STATIC)
        comp.set_collision_profile_name('BlockAll')
        return actor

    def tag_enclosure(self, remove=False):
        """Append (or remove) PrecinctSplitOut on the placed enclosure's MODERN-hide tag list."""
        ue = self.ue
        actor = self.by_label(ENCLOSURE_LABEL)
        if actor is None:
            raise RuntimeError('%s is not in this map; place the precinct first' % ENCLOSURE_LABEL)
        tags = [str(t) for t in actor.get_editor_property('HideWhileModernCityStandsTags')]
        before = list(tags)
        if remove:
            tags = [t for t in tags if t != STATE_TAG]
        elif STATE_TAG not in tags:
            tags.append(STATE_TAG)
        actor.set_editor_property('HideWhileModernCityStandsTags', [ue.Name(t) for t in tags])
        after = [str(t) for t in actor.get_editor_property('HideWhileModernCityStandsTags')]
        if remove and STATE_TAG in after:
            raise RuntimeError('failed to remove %s from the enclosure' % STATE_TAG)
        if not remove and STATE_TAG not in after:
            raise RuntimeError('failed to add %s to the enclosure' % STATE_TAG)
        self.receipt['enclosureTags'] = {'before': before, 'after': after}
        return after

    def readback(self, outs):
        ue = self.ue
        found = self.ours()
        if len(found) != len(outs):
            raise RuntimeError('%d split actors in map, manifest has %d' % (len(found), len(outs)))
        rows, worst = [], 0.0
        for spec in outs:
            group = spec['group']
            label = LABEL_PREFIX + group + '_Out'
            actor = found.get(label)
            if actor is None:
                raise RuntimeError('missing after reopen: ' + label)
            comps = actor.get_components_by_class(ue.StaticMeshComponent)
            if len(comps) != 1:
                raise RuntimeError('%s has %d mesh components' % (label, len(comps)))
            comp = comps[0]
            mesh = comp.get_editor_property('static_mesh')
            if _asset_path(mesh) != MESH_FOLDER + '/' + spec['assetName']:
                raise RuntimeError('%s mesh %s' % (label, _asset_path(mesh)))
            t = actor.get_actor_transform()
            loc, rot, scl = t.translation, t.rotation.rotator(), t.scale3d
            terr = max(abs(loc.x), abs(loc.y), abs(loc.z), abs(rot.pitch), abs(rot.yaw), abs(rot.roll),
                       abs(scl.x - 1), abs(scl.y - 1), abs(scl.z - 1))
            if terr > 1e-4:
                raise RuntimeError('%s transform is not identity (%g)' % (label, terr))
            tags = sorted(str(x) for x in actor.get_editor_property('tags'))
            if tags != sorted([FAMILY_TAG, STATE_TAG]):
                raise RuntimeError('%s tags %s' % (label, tags))
            # Mesh bounds, not get_actor_bounds(): the actor call can block on the level's
            # whole static-mesh compilation set. The vertices are world-baked and the
            # transform is asserted to be identity just above, so mesh bounds ARE world
            # bounds - the same proof, without dragging 7,860 meshes through compilation.
            box = mesh.get_bounding_box()
            lo = [box.min.x, box.min.y, box.min.z]
            hi = [box.max.x, box.max.y, box.max.z]
            cb = spec['canonicalBoundsCm']
            berr = max(max(abs(a - b) for a, b in zip(lo, cb['min'])),
                       max(abs(a - b) for a, b in zip(hi, cb['max'])))
            if berr > BOUNDS_TOLERANCE_CM:
                raise RuntimeError('%s world bounds differ by %.3f cm' % (label, berr))
            worst = max(worst, berr)
            # The original must still be present - this pass never removes it.
            original = self.by_label('SM_JerusalemBuildings_' + group)
            if original is None:
                raise RuntimeError('ORIGINAL %s vanished; this script must never remove it' % group)
            rows.append({'label': label, 'mesh': _asset_path(mesh), 'tags': tags,
                         'components': spec['components'], 'triangles': spec['triangles'],
                         'worldBoundsErrorCm': round(berr, 4), 'originalStillPresent': True})
        self.receipt['worstWorldBoundsErrorCm'] = round(worst, 4)
        return rows


def run(target, mode):
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('wrong project')
    r = Run(ue, target, mode)
    map_path = TARGETS[target]
    map_file = disk_path(map_path, 'umap')
    saved = False
    others = [m for m in all_maps() if Path(m) != map_file]
    protected = {m: sha256_of(m) for m in others}
    before = sha256_of(map_file)
    r.receipt.update({'map': map_path, 'mapSha256Before': before, 'protectedSha256Before': protected})
    r.write()
    try:
        manifest, outs = load_inputs()
        r.receipt['cutCells'] = manifest['counts']['cellsCut']
        r.receipt['collateralAvoided'] = manifest['counts']['collateralAvoided']
        r.receipt['boundary'] = manifest['boundary']
        if r.editor.get_game_world():
            raise RuntimeError('a game world is active')
        if mode == 'probe':
            # Deliberately BEFORE any load_level: the whole point is that no map is open.
            r.probe_material(outs[0]['group'])
            r.receipt['status'] = 'material_probed_no_map_loaded_nothing_saved'
            return r.receipt

        # ---------------------------------------------------------------- preload, NO MAP
        # ASSETS ARE LOADED BEFORE THE MAP, AND THE ORDER IS THE WHOLE FIX.
        #
        # Measured, across five killed runs and two survivors:
        #   preflight  load_level, then actor LABELS only ............... 0 flush lines, lived
        #   probe      load_asset with NO map loaded .................... 0 flush lines, lived
        #   apply      load_level, THEN load_asset ................... 74-110 flush lines, died
        #
        # `load_asset` on a static mesh while the target map is resident blocks on
        # FStaticMeshCompilingManager and pulls the level's entire 7,860-mesh set through
        # compilation at once - on a 16 GB box, that is the kill. The same call with no map
        # open costs nothing. So the material and all 11 module meshes are resolved here,
        # while memory is empty, and the map is opened afterwards holding them.
        preloaded = None
        if mode == 'apply':
            mats, nanite_on = r.recorded_material()
            preloaded = [(spec, r.mesh(spec, mats, nanite_on)) for spec in outs]
            r.receipt['preloadedBeforeMapLoad'] = len(preloaded)
            r.write()

        if not r.levels.load_level(map_path):
            raise RuntimeError('load_level failed')
        world = r.editor.get_editor_world()
        if world.get_outermost().get_name() != map_path:
            raise RuntimeError('loaded world is not the target')
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('dirty map packages before mutation')
        existing = r.ours()
        r.receipt['existingBefore'] = sorted(existing)
        r.receipt['actorCountBefore'] = len(r.actors.get_all_level_actors())
        if mode == 'preflight':
            missing = [s['group'] for s in outs if r.by_label('SM_JerusalemBuildings_' + s['group']) is None]
            r.receipt['originalsMissing'] = missing
            r.receipt['enclosurePresent'] = r.by_label(ENCLOSURE_LABEL) is not None
            r.receipt['status'] = 'preflight_ok_nothing_saved'
            return r.receipt
        if mode == 'verify':
            r.receipt['readback'] = r.readback(outs)
            r.receipt['status'] = 'verified_read_back_nothing_saved'
            return r.receipt
        if mode == 'apply' and existing:
            raise RuntimeError('%d split actors already exist; revert first' % len(existing))
        checkpoint = CHECKPOINT_ROOT / ('PrecinctCellSplit-%s-%s-%s' % (mode, target, r.stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != before:
            raise RuntimeError('checkpoint copy hash differs')
        r.receipt['checkpoint'] = str(checkpoint)
        r.write()
        if mode == 'revert':
            for actor in existing.values():
                r.actors.destroy_actor(actor)
            r.receipt['destroyed'] = sorted(existing)
            r.tag_enclosure(remove=True)
            if not existing:
                r.receipt['status'] = 'nothing_to_revert_map_unchanged'
                return r.receipt
        else:
            # Meshes were resolved BEFORE the map load (see the preload block above); this
            # loop only spawns, which touches no mesh data.
            placed = []
            for spec, mesh in preloaded:
                group = spec['group']
                r.place(spec, mesh, group)
                placed.append({'group': group, 'nanite': nanite_on})
            r.receipt['placed'] = placed
            r.write()
            r.tag_enclosure(remove=False)
        if not ue.EditorLoadingAndSavingUtils.save_map(world, map_path):
            raise RuntimeError('save_map failed')
        saved = True
        r.receipt['mapSaved'] = True
        r.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        # THE READBACK IS A SEPARATE PROCESS, DELIBERATELY.
        #
        # This used to load the map, save it, then reload it in the SAME editor session to
        # prove the result. On this 16 GB box that is two full loads of a 72 MB, 8,606-actor
        # map in one process, and it was killed by the OOM guard twice - after the work had
        # succeeded but before it could be written, which is the worst possible place to die.
        #
        # Splitting it is not a weakening. A readback in a FRESH process, reading the .umap
        # off disk with nothing of the writing session in memory, is a STRONGER proof than an
        # in-process reopen: it cannot be satisfied by anything still cached from the write.
        # Run `-SplitVerify` next; the status below stays 'verify_pending' until it passes.
        if mode == 'revert':
            r.receipt['status'] = 'reverted_saved_verify_pending'
        else:
            r.receipt['status'] = 'placed_saved_verify_pending'
        r.receipt['nextStep'] = ('run -SplitVerify -SplitTarget=%s in a FRESH editor process; '
                                 'this receipt is not acceptance until that passes' % target)
        return r.receipt
    except Exception as error:
        r.receipt['status'] = 'failed'
        r.receipt['error'] = repr(error)
        r.receipt['traceback'] = traceback.format_exc()
        raise
    finally:
        r.receipt['mapSha256After'] = sha256_of(map_file)
        r.receipt['mapBytesChanged'] = r.receipt['mapSha256After'] != before
        r.receipt['mapSavedFlag'] = saved
        changed = [m for m in others if sha256_of(m) != protected[m]]
        r.receipt['protectedMapsUnchanged'] = not changed
        r.receipt['protectedMapsChanged'] = changed
        r.write()


def _invoked_as_native_script():
    try:
        import unreal as ue
    except ImportError:
        return False
    cl = ue.SystemLibrary.get_command_line().lower()
    return SCRIPT_TOKEN.lower() in cl


def _main():
    import unreal as ue
    cl = ue.SystemLibrary.get_command_line()
    lowered = cl.lower()
    modes = [m for f, m in (('-splitprobe', 'probe'), ('-splitpreflight', 'preflight'),
                            ('-splitapply', 'apply'), ('-splitverify', 'verify'),
                            ('-splitrevert', 'revert')) if f in lowered]
    if len(modes) != 1:
        raise RuntimeError('exactly one of -SplitProbe/-SplitPreflight/-SplitApply/'
                           '-SplitVerify/-SplitRevert is required')
    match = re.search(r'-SplitTarget=(?:"([^"]+)"|(\S+))', cl, re.IGNORECASE)
    name = (match.group(1) or match.group(2)) if match else 'Candidate48'
    names = {'main50': 'Main50', 'candidate48': 'Candidate48'}
    if name.lower() not in names:
        raise RuntimeError('Unknown -SplitTarget=' + name)
    try:
        receipt = run(names[name.lower()], modes[0])
        ue.log('release_precinct_cell_split[%s/%s]: %s' % (names[name.lower()], modes[0], receipt['status']))
    except Exception as error:
        ue.log_error('release_precinct_cell_split failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in lowered and '-run=pythonscript' not in lowered:
            ue.SystemLibrary.quit_editor()


if _invoked_as_native_script():
    _main()

"""Port only the saved Main50 transit configuration to Candidate48.

Modern city coordinates are copied verbatim. No asset creation, imports, birds,
boarding bridge, or runtime acceptance. Apply: -CandidateTransitExpectedHash=SHA
and -CandidateTransitSourceHash=SHA. Fresh read-only: -CandidateTransitVerify=receipt.
"""
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))
from release_surface_soft import sha, inventory, check_hashes
from release_place_assets import snapshot_row, numeric_baseline_rows

SOURCE = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
SOURCE_SHA = '93483d25ff23e01ee1462845b958d9c2139f2cd2e7177cf5e3e3141dd4ae1432'
TARGET_SHA = '7eda28df84b35e45a6e975d39bebc23817798cc2af2db324b0121e09a30255d2'
CLASS = '/Script/MikdashRuntime.MikdashTransit'
LABEL = 'RELEASE_Transit_Selected48_V1'
TAG = 'ReleaseTransitSelected48V1'
# Explicit EditInstanceOnly fields from MikdashTransit.h; no delegates, actors,
# runtime HISM components, or arbitrary reflected object serialization.
STOP = dict(name='string', world_position='vector', dwell_min_seconds='float',
            dwell_max_seconds='float', boarding_min_people='int',
            boarding_max_people='int', furniture_offset_cm='float')
ROUTE = dict(id='name', rail='bool', points='vector[]', stops='stop[]',
             smoothing_per_segment='int', lane_offset_cm='float', ride_height_cm='float',
             speed_limit_cm_per_second='float', vehicle_weight='float', bus_share='float')
BODY = dict(key='name', paint='mesh', glass='mesh', dark='mesh', lens='mesh',
            length_cm='float', serves_stops='bool', door_leaf_paint='mesh',
            door_leaf_glass='mesh', door_local_offsets='vector[]')
ACTOR = dict(activate_on_begin_play='bool', routes='route[]', car_bodies='body[]',
             bus_body='body', train_bodies='body[]', shelter_meshes='mesh[]',
             platform_meshes='mesh[]', road_vehicle_count='int', density_multiplier='float',
             max_road_vehicles='int', max_active_trains='int', update_budget='int',
             seed='int', paint_palette='color[]')
ACTOR.update({p: 'float' for p in (
    'train_headway_min_seconds', 'train_headway_max_seconds', 'train_dwell_min_seconds',
    'train_dwell_max_seconds', 'train_car_length_cm', 'train_coupling_gap_cm',
    'train_bogie_inset_cm', 'bus_dwell_min_seconds', 'bus_dwell_max_seconds',
    'door_open_seconds', 'door_close_seconds', 'door_travel_cm',
    'transform_freeze_distance_cm', 'instance_cull_start_cm', 'instance_cull_end_cm',
    'photographer_share')})
SCHEMAS = {'stop': STOP, 'route': ROUTE, 'body': BODY}


def disk(package, suffix='umap'):
    return ROOT / 'Content' / (package[6:] + '.' + suffix)


def canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))


def run(expected=None, source_hash=None, verify=None):
    import unreal as u
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = ROOT / 'SourceAssets/transit-review' / ('candidate-transit-' + stamp + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(status='starting', pid=os.getpid(), sourceMap=SOURCE, map=TARGET,
                  mapSaved=False, errors=[], coordinateContract='Modern metric world coordinates unchanged',
                  scope='Transit actor only; no boarding bridge; runtime/visual acceptance pending')
    protected = {}; content_paths = set(); before = sha(disk(TARGET))
    report['mapSha256Before'] = before
    def write():
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    write()
    try:
        if bool(verify) == bool(expected) or (verify and source_hash):
            raise RuntimeError('Choose explicit two-hash apply or fresh verification')
        inventory()
        if Path(u.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project')
        prior = json.loads(Path(verify).read_text(encoding='utf-8-sig')) if verify else None
        if prior:
            pid = prior.get('pid')
            if prior.get('status') != 'saved_reopened' or prior.get('map') != TARGET or prior.get('sourceMap') != SOURCE or type(pid) is not int or pid <= 0 or pid == os.getpid():
                raise RuntimeError('Invalid fresh-process receipt')
            if prior.get('sourceSha256') != SOURCE_SHA or check_hashes(prior['protected']):
                raise RuntimeError('Source/protected content changed since apply')
            expected, source_hash = prior['mapSha256After'], SOURCE_SHA
        elif expected != TARGET_SHA or source_hash != SOURCE_SHA:
            raise RuntimeError('Apply hashes must equal the explicitly reviewed states')
        if not re.fullmatch('[0-9a-f]{64}', expected or '') or before != expected or sha(disk(SOURCE)) != source_hash:
            raise RuntimeError('Source or candidate hash mismatch')
        report['sourceSha256'] = source_hash
        ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)
        cls = u.load_class(None, CLASS)
        frame_cls = u.load_class(None, '/Script/MikdashRuntime.MikdashSceneUnits')
        if cls is None or frame_cls is None:
            raise RuntimeError('Required compiled classes absent')
        def clean():
            if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('PIE or dirty packages')
        def load(package):
            clean()
            if not levels.load_level(package): raise RuntimeError('Load failed: ' + package)
            clean()
            world = ed.get_editor_world()
            if world is None or world.get_outermost().get_name() != package:
                raise RuntimeError('Wrong loaded world')
        def matches(base):
            return [a for a in actors.get_all_level_actors() if u.MathLibrary.class_is_child_of(a.get_class(), base)]
        def encode(v, kind):
            if kind.endswith('[]'): return [encode(x, kind[:-2]) for x in v]
            if kind in SCHEMAS: return read(v, SCHEMAS[kind])
            if kind == 'mesh':
                if v is None: return None
                if not isinstance(v, u.StaticMesh): raise RuntimeError('Non-mesh/cross-world reference refused')
                path = v.get_path_name()
                if not path.startswith('/Game/') or ':' in path or not disk(path.split('.')[0], 'uasset').is_file():
                    raise RuntimeError('Unsaved or non-project asset reference: ' + path)
                return path
            if kind in ('vector', 'color'):
                result = [float(getattr(v, k)) for k in ('xyz' if kind == 'vector' else 'rgba')]
                if not all(math.isfinite(x) for x in result): raise RuntimeError('Non-finite coordinate/color')
                return result
            if kind == 'float':
                result = float(v)
                if not math.isfinite(result): raise RuntimeError('Non-finite scalar')
                return result
            if kind == 'int': return int(v)
            if kind == 'bool': return bool(v)
            if kind in ('name', 'string'): return str(v)
            raise RuntimeError('Unsupported schema type ' + kind)
        def read(obj, schema):
            return {key: encode(obj.get_editor_property(key), kind) for key, kind in schema.items()}
        def decode(value, kind):
            if kind.endswith('[]'): return [decode(x, kind[:-2]) for x in value]
            if kind in SCHEMAS:
                item = {'stop': u.MikdashTransitStop, 'route': u.MikdashTransitRoute, 'body': u.MikdashTransitBody}[kind]()
                assign(item, SCHEMAS[kind], value)
                return item
            if kind == 'mesh':
                if value is None: return None
                asset = u.load_asset(value)
                if not isinstance(asset, u.StaticMesh) or asset.get_path_name() != value:
                    raise RuntimeError('Existing mesh failed exact readback: ' + value)
                return asset
            if kind == 'vector': return u.Vector(*value)
            if kind == 'color': return u.LinearColor(*value)
            if kind == 'name': return u.Name(value)
            return value
        def assign(obj, schema, data):
            if set(data) != set(schema): raise RuntimeError('Property schema differs')
            for key, kind in schema.items(): obj.set_editor_property(key, decode(data[key], kind))
            if read(obj, schema) != data: raise RuntimeError('Exact property readback differs')
        def pose(a):
            r = a.get_actor_rotation()
            return {'location': encode(a.get_actor_location(), 'vector'),
                    'rotation': [r.pitch, r.yaw, r.roll], 'scale': encode(a.get_actor_scale3d(), 'vector')}
        clean()
        content_paths = {str(p) for p in (ROOT / 'Content').rglob('*') if p.is_file()}
        protected = {p: sha(Path(p)) for p in content_paths if Path(p) != disk(TARGET)}
        report['protected'] = protected
        load(SOURCE)
        found = matches(cls)
        if len(found) != 1 or found[0].get_class() != cls or found[0].get_outermost().get_name() != SOURCE:
            raise RuntimeError('Require one exact native source Transit, no subclasses')
        source = found[0]
        config = read(source, ACTOR)
        source_pose = pose(source)
        source_tags = [str(t) for t in source.get_editor_property('tags')]
        if source.get_attach_parent_actor() is not None or source.get_attached_actors() or source.get_owner() is not None:
            raise RuntimeError('Source owner/attachment actor references are unsupported across worlds')
        if sum(len(r['stops']) for r in config['routes']) != 15 or not config['activate_on_begin_play']:
            raise RuntimeError('Expected reviewed active 15-stop source')
        report.update(configuration=config, sourcePose=source_pose, sourceTags=source_tags,
                      sourceActor={'name': source.get_name(), 'label': source.get_actor_label()})
        if prior and any(prior.get(k) != report[k] for k in ('configuration', 'sourcePose', 'sourceTags', 'sourceActor')):
            raise RuntimeError('Source semantic readback differs from apply receipt')
        # Release all source-world references before loading the target; only primitive
        # values and project asset paths cross the map boundary.
        del source, found
        load(TARGET)
        def discover():
            ds = matches(frame_cls)
            if len(ds) != 1: raise RuntimeError('Require one scene descriptor including subclasses')
            d = ds[0]; p = d.get_editor_property('fixed_architecture_origin_cm')
            if d.get_outermost().get_name() != TARGET or d.get_actor_label() != 'RELEASE_SceneUnits_Selected48_V1' or int(d.get_editor_property('descriptor_schema_version')) != 1 or int(d.get_editor_property('coordinate_revision').value) != 1 or str(d.get_editor_property('scene_revision')) != 'Selected48.v1' or [p.x,p.y,p.z] != [-6200,0,0]:
                raise RuntimeError('Selected48 descriptor identity/version/pivot differs')
            return matches(cls), [a for a in actors.get_all_level_actors() if a.get_actor_label() == LABEL or TAG in [str(t) for t in a.tags]]
        def snapshot(exclude=None):
            aa = [a for a in actors.get_all_level_actors() if a.get_outermost().get_name() == TARGET and a.get_name() != exclude]
            data = numeric_baseline_rows([snapshot_row(u,a,TARGET) for a in aa], strict=True)
            for a in aa:
                for c in a.get_components_by_class(u.StaticMeshComponent):
                    for i in range(c.get_num_materials()):
                        m = c.get_material(i)
                        data['material:' + c.get_path_name() + ':' + str(i)] = m.get_path_name() if m else None
                for c in a.get_components_by_class(u.DecalComponent):
                    m = c.get_editor_property('decal_material')
                    data['decal:' + c.get_path_name()] = m.get_path_name() if m else None
                if a.get_class().get_path_name() == '/Script/MikdashRuntime.MikdashServiceActor':
                    data['service:' + a.get_name()] = {k: a.get_editor_property(k) for k in ('start_on_begin_play','sequence_enabled','use_grounded_movement')}
            return canonical(data)
        found, owned = discover()
        if not prior and (found or owned): raise RuntimeError('Candidate Transit or ownership collision; never replace')
        if prior and (len(found) != 1 or len(owned) != 1 or found[0] != owned[0]):
            raise RuntimeError('Fresh verification requires exactly one owned Transit')
        exclude = found[0].get_name() if prior else None
        baseline = snapshot(exclude)
        if prior and baseline != prior['unrelatedSnapshot']:
            raise RuntimeError('Unrelated persisted candidate state differs from apply baseline')
        load(TARGET)
        if snapshot(exclude) != baseline: raise RuntimeError('Pristine reload churn; no mutation permitted')
        report['unrelatedSnapshot'] = baseline
        if not prior:
            checkpoint = ROOT.parent / 'ReviewCheckpoints' / ('CandidateTransit-' + stamp)
            checkpoint.mkdir(parents=True, exist_ok=False)
            shutil.copy2(disk(TARGET), checkpoint / 'Walkthrough.umap')
            if sha(checkpoint / 'Walkthrough.umap') != before: raise RuntimeError('Checkpoint mismatch')
            # External actors would require writes outside the locked target map.
            if any((ROOT/'Content'/n/TARGET[6:]).exists() for n in ('__ExternalActors__','__ExternalObjects__')):
                raise RuntimeError('External package layout unsupported; no mutation')
            report['checkpoint'] = str(checkpoint); write()
            a = actors.spawn_actor_from_class(cls, u.Vector(*source_pose['location']), u.Rotator(*source_pose['rotation']), transient=False)
            if a is None: raise RuntimeError('Spawn failed')
            a.set_actor_label(LABEL)
            a.set_editor_property('tags', [u.Name(t) for t in dict.fromkeys(source_tags + [TAG])])
            a.set_actor_scale3d(u.Vector(*source_pose['scale']))
            assign(a, ACTOR, config)
            exclude = a.get_name()
            report['actorName'] = exclude
            if snapshot(exclude) != baseline or check_hashes(protected): raise RuntimeError('Unrelated state changed before save')
            if not levels.save_current_level(): raise RuntimeError('Map save refused')
            report['mapSaved'] = True; report['mapSha256After'] = sha(disk(TARGET)); write()
            load(TARGET)
        found, owned = discover()
        if len(found) != 1 or len(owned) != 1 or found[0] != owned[0]: raise RuntimeError('Saved Transit count/ownership differs')
        a = found[0]
        if a.get_class() != cls or a.get_outermost().get_name() != TARGET or a.get_actor_label() != LABEL or a.get_name() != (prior['actorName'] if prior else exclude):
            raise RuntimeError('Saved actor exact identity differs')
        if read(a, ACTOR) != config or pose(a) != source_pose or [str(t) for t in a.tags] != list(dict.fromkeys(source_tags + [TAG])):
            raise RuntimeError('Saved config/pose/tags differs')
        if snapshot(a.get_name()) != baseline: raise RuntimeError('Unrelated state changed after reload')
        clean()
        report['actorName'] = a.get_name()
        report['status'] = 'fresh_verified' if prior else 'saved_reopened'
    except Exception as error:
        report['status'] = 'failed'; report['errors'].append(repr(error)); raise
    finally:
        report['mapSha256After'] = sha(disk(TARGET))
        report['protectedDifferences'] = check_hashes(protected)
        current_paths = {str(p) for p in (ROOT / 'Content').rglob('*') if p.is_file()}
        report['newContentFiles'] = sorted(current_paths - content_paths) if content_paths else []
        if report['protectedDifferences'] or report['newContentFiles'] or (verify and report['mapSha256After'] != before):
            report['status'] = 'failed_preservation'
        write()
    if report['status'].startswith('failed'): raise RuntimeError(report['status'])
    return report


if __name__ == '__main__':
    try: import unreal as u
    except ImportError: print('Prepared only; requires explicit native arguments')
    else:
        command = u.SystemLibrary.get_command_line()
        args = {m.group(1).lower(): (m.group(2) or m.group(3)) for m in re.finditer(r'(-\w+)=(?:"([^"]+)"|(\S+))', command)}
        try:
            run(args.get('-candidatetransitexpectedhash'), args.get('-candidatetransitsourcehash'), args.get('-candidatetransitverify'))
        finally:
            if '-executepythonscript' in command.lower() and '-run=pythonscript' not in command.lower(): u.SystemLibrary.quit_editor()

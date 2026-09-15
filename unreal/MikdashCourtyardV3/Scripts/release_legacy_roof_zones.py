"""Guarded Candidate48 repair for floating ORIGINAL rooftop tanks/panels.

Run only in a fresh, exclusively owned commandlet. The native actor duplication
API crashes in commandlets; full editor retries exhausted Windows commit memory.
New partitions therefore use the original importer's persistent ISM creation API,
copying render settings and verifying every world transform before and after save.
The default is read-only preflight. Explicit -LegacyRoofApply enables checkpointed
map mutation. -LegacyRoofVerify verifies an already split map without saving.
-LegacyRoofPlan=<absolute JSON> is required. No C++ changes or asset imports.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
ASSETS = ('SM_JerusalemInstance_Rooftop_tanks', 'SM_JerusalemInstance_Rooftop_panels')
MESH_ROOT = '/Game/MikdashV3/JerusalemContext/DecorativeInstancesV1/Meshes/'
PLAN_SHA = '4c259972edda978d3163485e1a9f3780d74cc81673b71b3fc5c9edb1dec1137b'
TAG = 'LegacyRoofZonesV1'
ZONE_TAGS = {'kept':'CityDetailZone_Kept','precinct':'CityDetailZone_Precinct'}
COPY_PROPERTIES = ('mobility','visible','hidden_in_game','cast_shadow',
    'cast_dynamic_shadow','cast_static_shadow','cast_contact_shadow','cast_far_shadow',
    'cast_inset_shadow','affect_dynamic_indirect_lighting','affect_distance_field_lighting',
    'visible_in_ray_tracing','visible_in_reflection_captures','visible_in_real_time_sky_captures',
    'render_in_main_pass','render_in_depth_pass','receives_decals','use_as_occluder',
    'bounds_scale','min_draw_distance','ld_max_draw_distance','never_distance_cull',
    'allow_cull_distance_volume','instance_start_cull_distance','instance_end_cull_distance',
    'evaluate_world_position_offset','world_position_offset_disable_distance',
    'reverse_culling','disallow_nanite','forced_lod_model','override_min_lod','min_lod',
    'lightmap_type','lighting_channels','render_custom_depth','custom_depth_stencil_value',
    'custom_depth_stencil_write_mask','translucency_sort_priority','translucency_sort_distance_offset',
    'can_ever_affect_navigation','generate_overlap_events')


def render_properties(comp):
    values={}
    for prop in COPY_PROPERTIES:
        try:
            values[prop]=comp.get_editor_property(prop)
        except Exception as error:
            # Some names vary between engine versions; absence is recorded, not
            # silently substituted. Only properties present on BOTH ISMs copy.
            if 'Failed to find property' not in str(error):
                raise
    return values


def new_partition(ue, actor_api, original, original_comp, create_component):
    if original.get_class()!=ue.Actor.static_class():
        raise RuntimeError('Only original plain Actor prototypes can be partitioned')
    actor=actor_api.spawn_actor_from_class(ue.Actor,ue.Vector(0,0,0),ue.Rotator(),transient=False)
    if actor is None:
        raise RuntimeError('Persistent actor creation failed')
    comp=create_component(actor)
    comp.set_static_mesh(original_comp.get_editor_property('static_mesh'))
    for i in range(original_comp.get_num_materials()):
        comp.set_material(i,original_comp.get_material(i))
    props=render_properties(original_comp)
    if set(props)!=set(render_properties(comp)):
        raise RuntimeError('Source and new component expose different render properties')
    for prop,value in props.items():
        comp.set_editor_property(prop,value)
    comp.set_collision_profile_name(original_comp.get_collision_profile_name())
    comp.set_collision_enabled(original_comp.get_collision_enabled())
    actor.set_editor_property('tags',list(original.get_editor_property('tags')))
    return actor


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):
            h.update(b)
    return h.hexdigest()


def read_plan(path):
    if sha(path) != PLAN_SHA:
        raise RuntimeError('Plan hash changed; re-review and repin before applying')
    plan=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    validate_plan(plan)
    for source, digest in plan['sources'].items():
        if sha(source) != digest:
            raise RuntimeError('Plan is stale: '+source)
    return plan


def validate_plan(plan):
    if plan['status'] != 'offline_partition_ready_native_apply_pending' or plan['unresolved']:
        raise RuntimeError('Ownership plan has unresolved instances')
    owners=plan['owners']
    if len(owners)!=6007 or sorted(o['sourceIndex'] for o in owners)!=list(range(6007)):
        raise RuntimeError('Expected every source pair exactly once')
    if any(o['zone'] not in ZONE_TAGS for o in owners):
        raise RuntimeError('Unrecognised zone')
    if Counter(o['zone'] for o in owners) != {'kept':4744,'precinct':1263}:
        raise RuntimeError('Reviewed partition counts differ')
    if any(not o['buildingLabel'].startswith('SM_JerusalemBuildings_') for o in owners):
        raise RuntimeError('Unexpected owner family')


def expected_rows(manifest, plan, mesh, zone=None):
    groups=[g for g in manifest['groups'] if g['assetName']==mesh]
    if len(groups)!=1 or len(groups[0]['instances'])!=6007:
        raise RuntimeError('Frozen instance group mismatch')
    indices=sorted(o['sourceIndex'] for o in plan['owners'] if zone is None or o['zone']==zone)
    return [groups[0]['instances'][i] for i in indices]


def snapshot_maps():
    return {str(p):sha(p) for p in (ROOT/'Content').rglob('*.umap')}


def ensure_clean(ue):
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; refusing to load/save over work')


def components_for(ue, actors, mesh):
    matches=[]
    for actor in actors:
        for comp in actor.get_components_by_class(ue.InstancedStaticMeshComponent):
            asset=comp.get_editor_property('static_mesh')
            if asset and asset.get_path_name().split('.')[0] == MESH_ROOT+mesh:
                matches.append((actor,comp))
    return matches


def settings(comp):
    return {'materials':[comp.get_material(i).get_path_name() if comp.get_material(i) else None for i in range(comp.get_num_materials())],
            'collision':str(comp.get_collision_profile_name()),
            'visible':bool(comp.get_editor_property('visible')),
            'hiddenInGame':bool(comp.get_editor_property('hidden_in_game')),
            'castShadow':bool(comp.get_editor_property('cast_shadow')),
            'startCull':int(comp.get_editor_property('instance_start_cull_distance')),
            'endCull':int(comp.get_editor_property('instance_end_cull_distance')),
            'collisionEnabled':str(comp.get_collision_enabled()),
            'renderProperties':{k:(v.export_text() if hasattr(v,'export_text') else str(v))
                                for k,v in render_properties(comp).items()}}


def verify_rows(comp, rows, check_transform):
    if comp.get_instance_count()!=len(rows):
        raise RuntimeError('Native count mismatch')
    worst=0.0
    for i,row in enumerate(rows):
        transform=comp.get_instance_transform(i,True)
        worst=max(worst,check_transform(transform,row))
    return worst


def validate_runtime_policy(enclosure, plan):
    labels=set(str(v) for v in enclosure.get_editor_property('ExplicitHideLabels'))
    wall_tags, modern_tags=state_tags(enclosure)
    if ZONE_TAGS['precinct'] not in wall_tags:
        raise RuntimeError('Current enclosure does not consume the precinct zone tag')
    if ZONE_TAGS['precinct'] in modern_tags or ZONE_TAGS['kept'] in wall_tags|modern_tags or TAG in wall_tags|modern_tags:
        raise RuntimeError('Conflicting runtime zone tags would hide the wrong phase')
    mismatch=[o['sourceIndex'] for o in plan['owners'] if (o['buildingLabel'] in labels)!=(o['zone']=='precinct')]
    if mismatch:
        raise RuntimeError('Saved enclosure and ownership plan disagree: '+str(mismatch[:10]))


def state_tags(enclosure):
    return tuple({str(v) for v in enclosure.get_editor_property(prop)}
                 for prop in ('HideWhileWallStandsTags','HideWhileModernCityStandsTags'))


def validate_original_visibility(actor, comp, enclosure):
    inherited={str(v) for v in actor.get_editor_property('tags')}
    wall_tags, modern_tags=state_tags(enclosure)
    if inherited.intersection(wall_tags|modern_tags):
        raise RuntimeError('Original actor has conflicting state tags')
    if actor.get_editor_property('hidden') or not comp.get_editor_property('visible') or comp.get_editor_property('hidden_in_game'):
        raise RuntimeError('Original is hidden; refusing to change an unreviewed visibility state')


def release(plan_path, apply=False, verify=False):
    import unreal as ue
    if apply and verify:
        raise RuntimeError('Choose apply or verify, not both')
    if Path(ue.Paths.project_dir()).resolve()!=ROOT:
        raise RuntimeError('Wrong Unreal project')
    plan=read_plan(plan_path)
    sys.path.insert(0,str(ROOT/'Scripts'))
    from import_instances_ue58 import _inst_data, _inst_transform_error, _inst_component
    import create_oldcity_facades as F
    _,manifest=_inst_data(F.FROZEN_MANIFEST.parent)
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    actor_api=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('PIE/game world active')
    ensure_clean(ue)
    loaded=editor.get_editor_world()
    if loaded is None or loaded.get_outermost().get_name()!=TARGET:
        if not levels.load_level(TARGET):
            raise RuntimeError('Could not load Candidate48')
    loaded=None
    ensure_clean(ue)
    world=editor.get_editor_world()
    if world.get_outermost().get_name()!=TARGET:
        raise RuntimeError('Wrong loaded map')
    actors=list(actor_api.get_all_level_actors())
    enclosures=[a for a in actors if isinstance(a,ue.MikdashEnclosure)]
    if len(enclosures)!=1:
        raise RuntimeError('Expected one enclosure controller')
    validate_runtime_policy(enclosures[0],plan)
    baseline=snapshot_maps()
    target_file=ROOT/('Content/'+TARGET[6:]+'.umap')
    # This map is a single package today. Refuse rather than incompletely checkpoint OFPA.
    for folder in ('__ExternalActors__','__ExternalObjects__'):
        if (ROOT/'Content'/folder/TARGET[6:]).exists():
            raise RuntimeError('External packages require a separate reviewed checkpoint procedure')
    originals={}
    def inspect_split():
        results=[]
        current=list(actor_api.get_all_level_actors())
        for mesh in ASSETS:
            matches=components_for(ue,current,mesh)
            if len(matches)!=2:
                raise RuntimeError('Expected exactly two zone components for '+mesh)
            seen=set()
            for actor,comp in matches:
                tags={str(t) for t in actor.get_editor_property('tags')}
                zones=[z for z,t in ZONE_TAGS.items() if t in tags]
                if TAG not in tags or len(zones)!=1 or zones[0] in seen:
                    raise RuntimeError('Invalid or duplicate zone tags')
                zone=zones[0]
                wall_tags,modern_tags=state_tags(enclosures[0])
                permitted={ZONE_TAGS['precinct']} if zone=='precinct' else set()
                if tags.intersection(wall_tags|modern_tags)-permitted:
                    raise RuntimeError('Partition inherited a conflicting state tag')
                if not comp.get_editor_property('visible') or comp.get_editor_property('hidden_in_game'):
                    raise RuntimeError('Partition component is invisible')
                if zone=='kept' and actor.get_editor_property('hidden'):
                    raise RuntimeError('Kept actor is hidden')
                seen.add(zone)
                worst=verify_rows(comp,expected_rows(manifest,plan,mesh,zone),_inst_transform_error)
                if mesh in originals and settings(comp)!=originals[mesh]['settings']:
                    raise RuntimeError('Duplicated component settings changed')
                results.append({'mesh':mesh,'zone':zone,'count':comp.get_instance_count(),'worstMatrixProbeErrorCm':worst,'settings':settings(comp)})
        return results
    if verify:
        result={'status':'saved_partition_verified_runtime_capture_pending','groups':inspect_split(),'mapsUnchanged':snapshot_maps()==baseline,'nativeVisualAcceptance':'PENDING'}
        if not result['mapsUnchanged']:
            raise RuntimeError('Verify modified map bytes')
        ue.log(json.dumps(result))
        return result
    for mesh in ASSETS:
        matches=components_for(ue,actors,mesh)
        if len(matches)!=1:
            raise RuntimeError('Not an untouched single original component; use verify if already split')
        actor,comp=matches[0]
        tags={str(t) for t in actor.get_editor_property('tags')}
        if TAG in tags or tags.intersection(ZONE_TAGS.values()):
            raise RuntimeError('Original already has zone ownership')
        if len(actor.get_components_by_class(ue.InstancedStaticMeshComponent))!=1:
            raise RuntimeError('Original actor has other instance components')
        if comp.get_editor_property('num_custom_data_floats')!=0:
            raise RuntimeError('Unexpected custom instance data; refusing data loss')
        validate_original_visibility(actor,comp,enclosures[0])
        rows=expected_rows(manifest,plan,mesh)
        verify_rows(comp,rows,_inst_transform_error)
        originals[mesh]={'actor':actor,'component':comp,'settings':settings(comp),
                         'transforms':[comp.get_instance_transform(i,True) for i in range(len(rows))]}
    if not apply:
        ue.log('Legacy roof preflight passed: 12014 exact transforms; apply not requested; map unsaved.')
        return {'status':'preflight_passed_no_mutation','pairs':6007}
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint=ROOT.parent/'ReviewCheckpoints'/('LegacyRoofZones-'+stamp)
    checkpoint.mkdir(parents=True,exist_ok=False)
    backup=checkpoint/target_file.name
    shutil.copy2(target_file,backup)
    if sha(backup)!=baseline[str(target_file)]:
        raise RuntimeError('Checkpoint hash mismatch')
    receipt={'status':'checkpointed','map':TARGET,'mapSha256Before':baseline[str(target_file)],
             'planSha256':PLAN_SHA,'checkpoint':str(backup),'groups':[],'mapSaved':False,
             'scriptSha256':sha(Path(__file__)),'nativeVisualAcceptance':'PENDING','errors':[]}
    receipt_path=checkpoint/'receipt.json'
    def write():
        receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    write()
    try:
        for mesh,data in originals.items():
            original=data['actor']
            receipt['phase']='create_partition:'+mesh
            write()
            ue.log('Legacy roof: creating persistent partition for '+mesh)
            clone=new_partition(ue,actor_api,original,data['component'],_inst_component)
            clone.set_actor_label('RELEASE_LegacyRoof_Precinct_'+mesh)
            clone.set_folder_path('Release/LegacyRoofZones/Precinct')
            for zone,actor in (('kept',original),('precinct',clone)):
                receipt['phase']='partition:'+mesh+':'+zone
                write()
                comp=components_for(ue,[actor],mesh)[0][1]
                if settings(comp)!=data['settings']:
                    raise RuntimeError('Duplication changed material or render settings')
                tags=list(actor.get_editor_property('tags'))
                actor.set_editor_property('tags',tags+[ue.Name(TAG),ue.Name(ZONE_TAGS[zone])])
                indices=sorted(o['sourceIndex'] for o in plan['owners'] if o['zone']==zone)
                transforms=[data['transforms'][i] for i in indices]
                actor.modify()
                comp.modify()
                comp.clear_instances()
                comp.add_instances(transforms,False,True,False)
                verify_rows(comp,expected_rows(manifest,plan,mesh,zone),_inst_transform_error)
        receipt['groups']=inspect_split()
        receipt['phase']='save'
        write()
        if ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Unexpected dirty content asset; refusing save')
        if not ue.EditorLoadingAndSavingUtils.save_map(world,TARGET):
            raise RuntimeError('Map save failed; checkpoint preserved')
        receipt['mapSaved']=True
        receipt['phase']='reopen'
        write()
        if not levels.load_level(TARGET):
            raise RuntimeError('Map reopen failed')
        actors=list(actor_api.get_all_level_actors())
        enclosures=[a for a in actors if isinstance(a,ue.MikdashEnclosure)]
        if len(enclosures)!=1:
            raise RuntimeError('Enclosure count changed after reopen')
        validate_runtime_policy(enclosures[0],plan)
        receipt['phase']='readback'
        write()
        receipt['groups']=inspect_split()
        after=snapshot_maps()
        if set(after)!=set(baseline) or any(after[p]!=v for p,v in baseline.items() if p!=str(target_file)):
            raise RuntimeError('Protected map changed')
        receipt['protectedMapsUnchanged']=True
        receipt['mapSha256After']=after[str(target_file)]
        receipt['status']='partition_saved_reopened_runtime_capture_pending'
    except Exception as error:
        receipt['errors'].append(repr(error))
        receipt['status']='failed_after_save_checkpoint_available' if receipt['mapSaved'] else 'failed_before_save_discard_unsaved_world'
        raise
    finally:
        write()
    return receipt

def native_entry():
    import unreal as ue
    cmd=ue.SystemLibrary.get_command_line()
    plan=ue.SystemLibrary.parse_param_value(cmd,'LegacyRoofPlan=')
    if not plan:
        raise RuntimeError('-LegacyRoofPlan=<absolute JSON path> is required')
    release(Path(plan),apply=ue.SystemLibrary.parse_param(cmd,'LegacyRoofApply'),
            verify=ue.SystemLibrary.parse_param(cmd,'LegacyRoofVerify'))


def invoked_as_native_script():
    try:
        import unreal as ue
    except ImportError:
        return False
    cmd=ue.SystemLibrary.get_command_line().lower()
    return ('release_legacy_roof_zones.py' in cmd
            and ('-run=pythonscript' in cmd or '-executepythonscript' in cmd))


if __name__=='__main__' or invoked_as_native_script():
    native_entry()

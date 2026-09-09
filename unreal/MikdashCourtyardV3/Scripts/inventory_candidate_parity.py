"""Read-only serial main/candidate runtime parity inventory. Never saves/imports.
Native commandlet only; map hashes and dirty package checks bound every load.
Unavailable selected properties are recorded as findings, never inferred values.
"""
import json
import os
from pathlib import Path
import sys
from collections import Counter
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from release_surface_soft import sha,inventory,check_hashes
MAPS={'Main50':'/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
      'Candidate48':'/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'}
PROPERTIES={
 'MikdashTransit':['activate_on_begin_play','transform_freeze_distance_cm'],
 'MikdashCrowdField':['activate_on_begin_play','crowd_count','enable_visitor_groups'],
 'MikdashTransitBoardingBridge':['activate_on_begin_play','auto_find_actors','refuse_if_coordinator_active','transit','crowd_field','max_figures','max_concurrent_groups'],
 'MikdashTransitCrowdCoordinator':['activate_on_begin_play'],
 'MikdashTourGuide':['content_relative_path','wander_offer_radius_cm'],
 'MikdashSurfaceDetail':['decal_budget','budget_update_interval_seconds','dust_puff_material','ripple_material'],
 'MikdashServiceActor':['sequence_enabled','start_on_begin_play','use_grounded_movement'],
 'MikdashSceneUnits':['scene_revision','descriptor_schema_version','coordinate_revision','fixed_architecture_origin_cm']}


def run():
    import unreal as u
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=ROOT/'SourceAssets/runtime-review'/('candidate-parity-'+stamp+'.json')
    report={'status':'starting','pid':os.getpid(),'errors':[],'maps':{},
            'scope':'Editor persisted actor inventory only; no runtime or visual acceptance'}
    before={}
    def write():
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    write()
    try:
        inventory()
        if Path(u.Paths.project_dir()).resolve()!=ROOT: raise RuntimeError('Wrong project')
        ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
        actor_system=u.get_editor_subsystem(u.EditorActorSubsystem)
        def clean():
            if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
                raise RuntimeError('PIE or dirty packages')
        clean()
        before={str(p):sha(p) for p in (ROOT/'Content').rglob('*.umap')}
        report['mapHashesBefore']=before
        classes={name:u.load_class(None,'/Script/MikdashRuntime.'+name) for name in PROPERTIES}
        report['missingClasses']=[name for name,cls in classes.items() if cls is None]
        def encode(value):
            if value is None or isinstance(value,(bool,int,float,str)): return value
            if isinstance(value,u.Object): return value.get_path_name()
            if isinstance(value,u.Vector): return [value.x,value.y,value.z]
            return str(value)
        for target,map_path in MAPS.items():
            clean()
            if not levels.load_level(map_path): raise RuntimeError('Load failed '+target)
            clean()
            world=ed.get_editor_world()
            if world is None or world.get_outermost().get_name()!=map_path: raise RuntimeError('World differs')
            rows=[];decals=Counter();class_counts=Counter();tour_markers=0
            for actor in actor_system.get_all_level_actors():
                if actor.get_outermost().get_name()!=map_path: continue
                tags=[str(t) for t in actor.get_editor_property('tags')]
                actor_class=actor.get_class();class_path=actor_class.get_path_name()
                matching=[name for name,cls in classes.items() if cls and u.MathLibrary.class_is_child_of(actor_class,cls)]
                if class_path.startswith('/Script/MikdashRuntime.') or matching:
                    row={'name':actor.get_name(),'label':actor.get_actor_label(),'class':class_path,'tags':tags,'properties':{}}
                    class_counts[class_path]+=1
                    for base in matching:
                        for prop in PROPERTIES[base]:
                            try: row['properties'][prop]=encode(actor.get_editor_property(prop))
                            except Exception as error: row['properties'][prop]={'unavailable':str(error)}
                    rows.append(row)
                if actor.get_actor_label().startswith('RELEASE_TOUR_Marker_'): tour_markers+=1
                if 'MikdashSurfaceWearV1' in tags:
                    component=actor.get_component_by_class(u.DecalComponent)
                    if component is None: raise RuntimeError('Tagged wear actor lacks decal component')
                    material=component.get_editor_property('decal_material')
                    decals[material.get_path_name() if material else '<null>']+=1
            report['maps'][target]={'map':map_path,'runtimeActors':sorted(rows,key=lambda r:r['name']),
                'runtimeClassCounts':dict(class_counts),'tourMarkerCount':tour_markers,
                'taggedWearDecalCount':sum(decals.values()),'taggedWearMaterialCounts':dict(decals),
                'softV1DecalCount':sum(n for path,n in decals.items() if path.startswith('/Game/MikdashV3/SurfaceDetailSoftV1/'))}
            clean()
            if check_hashes(before): raise RuntimeError('Map bytes changed during inventory')
            write()
        report['status']='inventory_complete_runtime_unverified'
    except Exception as error:
        report['status']='failed';report['errors'].append(repr(error));raise
    finally:
        report['mapHashDifferences']=check_hashes(before)
        if report['mapHashDifferences']: report['status']='failed_preservation'
        write()
    if report['status'].startswith('failed'): raise RuntimeError(report['status'])
    return report


if __name__=='__main__':
    try: import unreal as u
    except ImportError: print('Prepared native read-only inventory; no execution')
    else:
        command=u.SystemLibrary.get_command_line().lower()
        try: run()
        finally:
            if '-executepythonscript' in command and '-run=pythonscript' not in command: u.SystemLibrary.quit_editor()

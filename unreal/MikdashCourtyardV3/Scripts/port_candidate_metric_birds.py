"""Four metric-city flocks only. Temple PlazaPigeons deliberately deferred.
Apply requires -MetricBirdsSourceHash=SHA -MetricBirdsExpectedHash=SHA;
fresh read-only verification requires -MetricBirdsVerify=<apply receipt>.
No imports, shared asset writes, coordinate scaling, perch discovery or runtime claim.
"""
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from release_surface_soft import sha,inventory,check_hashes
from release_place_assets import snapshot_row,numeric_baseline_rows
from release_birds import _species_enum
SOURCE='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
TARGET='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
SOURCE_SHA='93483d25ff23e01ee1462845b958d9c2139f2cd2e7177cf5e3e3141dd4ae1432'
CLASS='/Script/MikdashRuntime.MikdashBirdFlock'
TAG='ReleaseMetricBirdsSelected48V1'
LABELS={'RELEASE_BirdFlock_KotelPigeons':'RockDove',
        'RELEASE_BirdFlock_WallSwifts':'CommonSwift',
        'RELEASE_BirdFlock_RooftopCrows':'HoodedCrow',
        'RELEASE_BirdFlock_MountKestrel':'CommonKestrel'}
# All authored BirdFlock.h properties; no PoseComponents, delegates or actor refs.
FIELDS=dict(flock_enabled='bool',species='species',bird_count='int',home_point_cm='vector',
    radius_cm='float',ceiling_z_cm='float',floor_z_cm='float',soft_band_cm='float',
    radial_soft_band_cm='float',flock_seed='int',size_scale='float',pose_meshes='mesh[]',
    perch_points_cm='vector[]',perch_actor_tags='name[]',perch_points_per_tagged_actor='int',
    perch_lift_cm='float',near_update_interval_seconds='float',mid_update_interval_seconds='float',
    far_update_interval_seconds='float',near_distance_cm='float',mid_distance_cm='float',
    cull_radius_cm='float',birds_per_update='int',max_birds='int',announce_bird_sounds='bool')


def disk(package): return ROOT/'Content'/(package[6:]+'.umap')
def canon(value): return json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'))


def run(expected=None,source_hash=None,verify=None):
    import unreal as u
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'SourceAssets/birds-review'/('candidate-metric-birds-'+stamp+'.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    report=dict(status='starting',pid=os.getpid(),map=TARGET,sourceMap=SOURCE,mapSaved=False,errors=[],
        scope='Four metric flocks; PlazaPigeons deferred until candidate temple perch geometry reviewed',
        coordinateContract='All saved world coordinates, size and budget properties unchanged',
        runtimeVisualAcceptance='pending',labels=LABELS)
    before=sha(disk(TARGET));protected={};paths=set()
    report['mapSha256Before']=before
    def write(): out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    write()
    try:
        if bool(verify)==bool(expected) or (verify and source_hash): raise RuntimeError('Choose two-hash apply or fresh verify')
        inventory()
        if Path(u.Paths.project_dir()).resolve()!=ROOT: raise RuntimeError('Wrong project')
        prior=json.loads(Path(verify).read_text(encoding='utf-8-sig')) if verify else None
        if prior:
            pid=prior.get('pid')
            if prior.get('status')!='saved_reopened' or prior.get('map')!=TARGET or prior.get('sourceMap')!=SOURCE or prior.get('labels')!=LABELS or type(pid)is not int or pid<=0 or pid==os.getpid(): raise RuntimeError('Invalid fresh-process receipt')
            if prior.get('sourceSha256')!=SOURCE_SHA or check_hashes(prior['protected']): raise RuntimeError('Source/protected content changed')
            expected,source_hash=prior['mapSha256After'],SOURCE_SHA
        if source_hash!=SOURCE_SHA or sha(disk(SOURCE))!=source_hash or not re.fullmatch('[0-9a-f]{64}',expected or '') or before!=expected:
            raise RuntimeError('Explicit source/candidate hash mismatch')
        report['sourceSha256']=source_hash
        spec_path=ROOT/'Scripts/release_birds.spec.json'
        spec=json.loads(spec_path.read_text(encoding='utf-8-sig'))
        selected={r['label']:r['species'] for r in spec['flocks'] if r['label'] in LABELS}
        if selected!=LABELS: raise RuntimeError('Reviewed source species/labels differ')
        report['specSha256']=sha(spec_path)
        if prior and prior['specSha256']!=report['specSha256']: raise RuntimeError('Spec changed since apply')
        cls=u.load_class(None,CLASS);frame_cls=u.load_class(None,'/Script/MikdashRuntime.MikdashSceneUnits')
        if cls is None or frame_cls is None: raise RuntimeError('Required classes absent')
        ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
        actors=u.get_editor_subsystem(u.EditorActorSubsystem)
        def clean():
            if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages(): raise RuntimeError('PIE or dirty packages')
        def load(package):
            clean()
            if not levels.load_level(package): raise RuntimeError('Load failed '+package)
            clean();world=ed.get_editor_world()
            if world is None or world.get_outermost().get_name()!=package: raise RuntimeError('Wrong world')
        def matching(base): return [a for a in actors.get_all_level_actors() if u.MathLibrary.class_is_child_of(a.get_class(),base)]
        species={name:_species_enum(u,name) for name in set(LABELS.values())}
        def encode(v,kind):
            if kind.endswith('[]'): return [encode(x,kind[:-2]) for x in v]
            if kind=='species':
                names=[k for k,e in species.items() if v==e]
                if len(names)!=1: raise RuntimeError('Unsupported bird species')
                return names[0]
            if kind=='mesh':
                if not isinstance(v,u.StaticMesh): raise RuntimeError('Missing/non-mesh/cross-world reference')
                path=v.get_path_name();package=path.split('.')[0]
                if not path.startswith('/Game/') or ':' in path or not (ROOT/'Content'/(package[6:]+'.uasset')).is_file(): raise RuntimeError('Unsaved/non-project mesh')
                return path
            if kind=='vector':
                result=[float(v.x),float(v.y),float(v.z)]
                if not all(math.isfinite(x) for x in result): raise RuntimeError('Nonfinite vector')
                return result
            if kind=='float':
                result=float(v)
                if not math.isfinite(result): raise RuntimeError('Nonfinite scalar')
                return result
            if kind=='int': return int(v)
            if kind=='bool': return bool(v)
            if kind=='name': return str(v)
            raise RuntimeError('Unsupported schema')
        def read(a): return {key:encode(a.get_editor_property(key),kind) for key,kind in FIELDS.items()}
        def decode(v,kind):
            if kind.endswith('[]'): return [decode(x,kind[:-2]) for x in v]
            if kind=='species': return species[v]
            if kind=='vector': return u.Vector(*v)
            if kind=='name': return u.Name(v)
            if kind=='mesh':
                asset=u.load_asset(v)
                if not isinstance(asset,u.StaticMesh) or asset.get_path_name()!=v: raise RuntimeError('Mesh readback differs')
                return asset
            return v
        def pose(a):
            r=a.get_actor_rotation()
            return {'location':encode(a.get_actor_location(),'vector'),'rotation':[r.pitch,r.yaw,r.roll],
                    'scale':encode(a.get_actor_scale3d(),'vector')}
        clean();paths={str(p) for p in (ROOT/'Content').rglob('*') if p.is_file()}
        protected={p:sha(Path(p)) for p in paths if Path(p)!=disk(TARGET)};report['protected']=protected
        load(SOURCE);source={}
        for label,name in LABELS.items():
            found=[a for a in actors.get_all_level_actors() if a.get_actor_label()==label]
            if len(found)!=1 or found[0].get_class()!=cls or found[0].get_outermost().get_name()!=SOURCE: raise RuntimeError('Source label/class/ownership differs '+label)
            a=found[0]
            if a.get_owner() or a.get_attach_parent_actor() or a.get_attached_actors(): raise RuntimeError('Cross-world owner/attachment refused')
            config=read(a)
            if config['species']!=name or len(config['pose_meshes'])!=4 or config['perch_actor_tags'] or not config['flock_enabled']:
                raise RuntimeError('Species/meshes/enabled state differs or dynamic tag-based perches unsupported')
            source[label]={'name':a.get_name(),'pose':pose(a),'tags':[str(t) for t in a.tags],'configuration':config}
        del a,found
        report['sourceActors']=source
        if prior and prior['sourceActors']!=source: raise RuntimeError('Source semantic state differs')
        load(TARGET)
        def discover():
            ds=matching(frame_cls)
            if len(ds)!=1: raise RuntimeError('Require unique scene descriptor class/subclasses')
            d=ds[0];p=d.get_editor_property('fixed_architecture_origin_cm')
            if d.get_outermost().get_name()!=TARGET or d.get_actor_label()!='RELEASE_SceneUnits_Selected48_V1' or int(d.get_editor_property('descriptor_schema_version'))!=1 or int(d.get_editor_property('coordinate_revision').value)!=1 or str(d.get_editor_property('scene_revision'))!='Selected48.v1' or [p.x,p.y,p.z]!=[-6200,0,0]: raise RuntimeError('Selected48 version/pivot differs')
            found=matching(cls)
            owned=[a for a in actors.get_all_level_actors() if a.get_actor_label() in LABELS or TAG in [str(t) for t in a.tags]]
            return found,owned
        def snapshot(exclude=()):
            aa=[a for a in actors.get_all_level_actors() if a.get_outermost().get_name()==TARGET and a.get_name() not in exclude]
            data=numeric_baseline_rows([snapshot_row(u,a,TARGET) for a in aa],strict=True)
            for a in aa:
                for c in a.get_components_by_class(u.StaticMeshComponent):
                    for i in range(c.get_num_materials()):
                        m=c.get_material(i);data['material:'+c.get_path_name()+':'+str(i)]=m.get_path_name() if m else None
                for c in a.get_components_by_class(u.DecalComponent):
                    m=c.get_editor_property('decal_material');data['decal:'+c.get_path_name()]=m.get_path_name() if m else None
                if a.get_class().get_path_name()=='/Script/MikdashRuntime.MikdashServiceActor':
                    data['service:'+a.get_name()]={k:a.get_editor_property(k) for k in ('start_on_begin_play','sequence_enabled','use_grounded_movement')}
            return canon(data)
        found,owned=discover()
        if not prior and (found or owned): raise RuntimeError('Require zero candidate bird actors/ownership collisions')
        if prior and (len(found)!=4 or len(owned)!=4 or {a.get_name() for a in found}!={a.get_name() for a in owned}): raise RuntimeError('Fresh verification requires exactly four owned flocks')
        exclude=[a.get_name() for a in found] if prior else []
        baseline=snapshot(exclude)
        if prior and baseline!=prior['unrelatedSnapshot']: raise RuntimeError('Persisted unrelated state differs')
        load(TARGET)
        if snapshot(exclude)!=baseline: raise RuntimeError('Pristine reload churn; no mutation')
        report['unrelatedSnapshot']=baseline
        if not prior:
            if any((ROOT/'Content'/n/TARGET[6:]).exists() for n in ('__ExternalActors__','__ExternalObjects__')): raise RuntimeError('External package layout unsupported')
            checkpoint=ROOT.parent/'ReviewCheckpoints'/('CandidateMetricBirds-'+stamp)
            checkpoint.mkdir(parents=True,exist_ok=False);shutil.copy2(disk(TARGET),checkpoint/'Walkthrough.umap')
            if sha(checkpoint/'Walkthrough.umap')!=before: raise RuntimeError('Checkpoint mismatch')
            report['checkpoint']=str(checkpoint);write();names={}
            for label,row in source.items():
                p=row['pose'];a=actors.spawn_actor_from_class(cls,u.Vector(*p['location']),u.Rotator(*p['rotation']),transient=False)
                if a is None: raise RuntimeError('Spawn failed '+label)
                a.set_actor_label(label);a.set_actor_scale3d(u.Vector(*p['scale']))
                a.set_editor_property('tags',[u.Name(t) for t in dict.fromkeys(row['tags']+[TAG])])
                for key,kind in FIELDS.items(): a.set_editor_property(key,decode(row['configuration'][key],kind))
                if read(a)!=row['configuration']: raise RuntimeError('Immediate field readback differs')
                names[label]=a.get_name()
            report['actorNames']=names;exclude=list(names.values())
            if snapshot(exclude)!=baseline or check_hashes(protected): raise RuntimeError('Unrelated state changed before save')
            if not levels.save_current_level(): raise RuntimeError('Save refused')
            report['mapSaved']=True;report['mapSha256After']=sha(disk(TARGET));write();load(TARGET)
        found,owned=discover()
        if len(found)!=4 or len(owned)!=4 or {a.get_name() for a in found}!={a.get_name() for a in owned}: raise RuntimeError('Saved exact four flocks differs')
        names=prior['actorNames'] if prior else report['actorNames']
        for a in found:
            label=a.get_actor_label()
            if label not in source or a.get_name()!=names[label] or a.get_class()!=cls or a.get_outermost().get_name()!=TARGET: raise RuntimeError('Saved identity differs')
            row=source[label]
            if read(a)!=row['configuration'] or pose(a)!=row['pose'] or [str(t) for t in a.tags]!=list(dict.fromkeys(row['tags']+[TAG])): raise RuntimeError('Saved configuration/pose/tags differs')
        if snapshot(list(names.values()))!=baseline: raise RuntimeError('Unrelated state differs after reopen')
        clean();report['actorNames']=names;report['status']='fresh_verified' if prior else 'saved_reopened'
    except Exception as error:
        report['status']='failed';report['errors'].append(repr(error));raise
    finally:
        report['mapSha256After']=sha(disk(TARGET));report['protectedDifferences']=check_hashes(protected)
        now={str(p) for p in (ROOT/'Content').rglob('*') if p.is_file()}
        report['newContentFiles']=sorted(now-paths) if paths else []
        if report['protectedDifferences'] or report['newContentFiles'] or (verify and before!=report['mapSha256After']): report['status']='failed_preservation'
        write()
    if report['status'].startswith('failed'): raise RuntimeError(report['status'])
    return report


if __name__=='__main__':
    try: import unreal as u
    except ImportError: print('Prepared guarded native helper; no action')
    else:
        command=u.SystemLibrary.get_command_line()
        args={m.group(1).lower():(m.group(2) or m.group(3)) for m in re.finditer(r'(-\w+)=(?:"([^"]+)"|(\S+))',command)}
        try: run(args.get('-metricbirdsexpectedhash'),args.get('-metricbirdssourcehash'),args.get('-metricbirdsverify'))
        finally:
            if '-executepythonscript' in command.lower() and '-run=pythonscript' not in command.lower(): u.SystemLibrary.quit_editor()

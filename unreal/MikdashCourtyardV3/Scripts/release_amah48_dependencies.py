"""Explicit candidate-only fitted veneers and receipt-matched frieze migration."""
import importlib.util
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'SourceAssets/scale-review'
INVENTORY=REVIEW/'native-scale-inventory-20260908T133142315573Z.json'
VENEER='/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/SM_InteriorVeneerCube'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def module(name):
    spec=importlib.util.spec_from_file_location('dep_'+name,ROOT/'Scripts'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def offline_plan():
    inventory=json.loads(INVENTORY.read_text(encoding='utf-8-sig'))
    frieze_path=ROOT/'SourceAssets/sanctuary-detail/KeruvFriezeV2/native-import-20260907T204023357744Z.json'
    frieze=json.loads(frieze_path.read_text(encoding='utf-8-sig'))
    panels={p['label']:p for p in frieze['placed']}
    walls={w['wall']:w for w in frieze['walls']}
    rows=[];unknown=[]
    for actor in inventory['actors']:
        meshes=[c.get('mesh','').split('.')[0] for c in actor['components']]
        if VENEER in meshes:
            if len(meshes)!=1 or actor['parent']:raise RuntimeError('Ambiguous veneer inventory')
            scales=actor['scale']; thin=[i for i,v in enumerate(scales) if abs(v-.002)<1e-8]
            if len(thin)!=1:raise RuntimeError('Cannot identify physical veneer thickness axis')
            rows.append(dict(name=actor['name'],label=actor['label'],mesh=VENEER,
                originalLocation=actor['locationCm'],originalRotation=actor['rotationDegrees'],originalScale=scales,
                location48=[x*.96 for x in actor['locationCm']],
                scale48=[v if i==thin[0] else v*.96 for i,v in enumerate(scales)],
                physicalThicknessAxis=thin[0],classification='local cube; book-fitted face dimensions; preserve .2cm veneer thickness'))
        elif actor['label'] in panels:
            panel=panels[actor['label']];wall=walls[panel['wall']]
            if meshes!=[panel['mesh']] or any(abs(a-b)>.0001 for a,b in zip(actor['locationCm'],panel['location'])):
                raise RuntimeError('Frieze receipt/live inventory mismatch')
            axis={'x':0,'y':1}[wall['normalAxis']]
            center=(wall['veneerWorldBoundsCm']['min'][axis]+wall['veneerWorldBoundsCm']['max'][axis])/2
            offset=panel['location'][axis]-center
            if abs(abs(offset)-1.6)>.001:raise RuntimeError('Unexpected physical frieze offset')
            location=[x*.96 for x in actor['locationCm']];location[axis]=center*.96+offset
            rows.append(dict(name=actor['name'],label=actor['label'],mesh=panel['mesh'],
                originalLocation=actor['locationCm'],originalRotation=actor['rotationDegrees'],originalScale=actor['scale'],
                location48=location,scale48=[actor['scale'][0]*.96,actor['scale'][1],actor['scale'][2]*.96],
                physicalThicknessAxis=1,classification='local frieze X/Z fitted dimensions; preserve local Y thickness/displacement and 1.5cm standoff plus .1cm veneer half-thickness'))
        elif any('/DoorsParochesV1/' in p for p in meshes):
            unknown.append(dict(name=actor['name'],meshes=meshes,classification='local hinge/panel geometry',
                reason='Opening floor925→888, but door bottom927 includes physical2cm and curtain928 includes3cm. Preserve offsets after floor migration; folded hinge8/16cm offsets need explicit fabrication policy. Curtain artwork HOLD; no adoption here.'))
        elif any('/KeilimTIV1/' in p for p in meshes):
            unknown.append(dict(name=actor['name'],meshes=meshes,classification='local vessel geometry',
                reason='Book-amah dimensions can scale; exact current mesh/version and dimensional units require reconciliation with later vessel replacements. Support floor925→888; physical details/loaves must not be blanket-scaled.'))
        elif any('/KeruvFrieze' in p for p in meshes):
            unknown.append(dict(name=actor['name'],meshes=meshes,classification='local modular fitted relief',
                reason='Placement/spacing depends on resized walls; 1.6cm facade standoff and relief depth are rendering/fabrication offsets needing explicit preservation, not .96 guessing.'))
    if len([r for r in rows if r['mesh']==VENEER])!=7:raise RuntimeError('Expected exactly seven source-fitted veneer panels')
    if len([r for r in rows if r['mesh']!=VENEER])!=len(panels):raise RuntimeError('Incomplete exact frieze coverage')
    return dict(status='PARTIAL_PLAN_VENEERS_AND_FRIEZES',inventorySha256=sha(INVENTORY),friezeReceiptSha256=sha(frieze_path),
                veneerProposals=rows,unconvertedActors=unknown,
                resolvedDoorFabrication=dict(source='create_sanctuary_doors.py geometry; release_import_doors.py hinge/envelope solver',
                    kodesh=dict(openingWidth48=336,openingHeight48=288,nominalQuarter48=84,leafWidth48=83,leafHeight48=284,bottomZ48=890),
                    physicalUnscaled=dict(bottomLift=2,totalHeightClearance=4,widthClearance=1,leafThickness=7,barrelRadius=2,barrelLength=12,barrelOffset=8,jambGap=1),
                    hingeFormula='Second leaf=(nominal48+8*sin(a),8-8*cos(a),0); at180deg=(84,16,0)',
                    blockedReason='Part-level regeneration required: one actor scale cannot retain physical frame margins, barrel radius/length and handles while resizing book-based spans. Then rerun stack envelope and jamb solver; no shared mesh edit.'),
                stairs='Original architecture stairs already migrated by architecture candidate. Do not scale again. Metric Kotel access stairs/context remain fixed; join requires new floor/route review.',
                missing='Inventory is historical, not a current live scene. Native apply demands exact original veneer identity/pose and refuses any change. Unknown/new actor families require a new inventory.',
                promotionAvailable=False)


def run(candidate_receipt=None,apply=False):
    plan=offline_plan()
    if not apply:return plan
    if candidate_receipt is None:raise RuntimeError('Explicit successful architecture candidate receipt required')
    receipt_path=Path(candidate_receipt).resolve()
    if receipt_path.parent!=REVIEW:raise RuntimeError('Receipt must be in scale-review')
    candidate_info=json.loads(receipt_path.read_text(encoding='utf-8-sig'))
    if candidate_info['status']!='PARTIAL_ARCHITECTURE48_SAVED_REOPENED_DEPENDENCIES_UNCONVERTED' or not candidate_info['protectedUnchanged']:
        raise RuntimeError('Architecture candidate did not pass')
    target=candidate_info['candidate']
    if not target.startswith('/Game/MikdashV3/Amah48Candidate_') or not target.endswith('/Maps/Walkthrough'):
        raise RuntimeError('Candidate-only namespace required')
    import unreal as u
    if Path(u.SystemLibrary.get_project_directory()).resolve()!=ROOT:raise RuntimeError('Wrong project')
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    if editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Live/dirty world')
    if editor.get_editor_world().get_path_name().split('.')[0]!=target:raise RuntimeError('Candidate must already be loaded')
    units=module('release_amah48_candidate');protected=units.offline_plan()
    if target==protected['source']:raise RuntimeError('Never modify current main')
    for folder in ('__ExternalActors__','__ExternalObjects__'):
        if (ROOT/'Content'/folder/target[6:]).exists():raise RuntimeError('External package checkpoint unsupported')
    h=module('release_resident_crowd');baseline=h._scene_snapshot(u,actors)
    byname={a.get_name():a for a in actors.get_all_level_actors()};selected=[];asset_hashes={}
    for row in plan['veneerProposals']:
        a=byname.get(row['name'])
        if a is None or a.get_attach_parent_actor() or a.get_attached_actors():raise RuntimeError('Veneer missing/attached')
        cs=a.get_components_by_class(u.StaticMeshComponent)
        if len(cs)!=1 or h._path(cs[0].get_editor_property('static_mesh'))!=row['mesh']:raise RuntimeError('Fitted mesh changed')
        expected=row['originalLocation']+row['originalRotation']+row['originalScale']
        # Native inventory rotation order is pitch,yaw,roll, matching resident pose.
        if any(abs(x-y)>.0001 for x,y in zip(h._pose(a),expected)):raise RuntimeError('Veneer already moved/scaled; refuse replay')
        for asset in [cs[0].get_editor_property('static_mesh')]+[cs[0].get_material(i) for i in range(cs[0].get_num_materials())]:
            package=h._path(asset)
            if package and package.startswith('/Game/'):
                path=ROOT/'Content'/(package[6:]+'.uasset');asset_hashes[str(path)]=sha(path)
        selected.append((a,row))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint=ROOT.parent/'ReviewCheckpoints'/('Amah48Dependencies-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
    mapfile=units.disk(target);before=sha(mapfile);shutil.copy2(mapfile,checkpoint/'Candidate.umap')
    if sha(checkpoint/'Candidate.umap')!=before:raise RuntimeError('Checkpoint mismatch')
    report=dict(plan,candidate=target,candidateShaBefore=before,checkpoint=str(checkpoint),protectedAssets=asset_hashes,status='STARTED')
    output=REVIEW/('amah48-dependencies-'+stamp+'.json')
    def write():output.write_text(json.dumps(report,indent=2),encoding='utf8')
    write()
    try:
        for a,row in selected:
            a.modify(True);a.set_actor_location(u.Vector(*row['location48']),False,True);a.set_actor_scale3d(u.Vector(*row['scale48']))
        expected=h._scene_snapshot(u,actors);names={r['name'] for _,r in selected}
        if {k:v for k,v in baseline.items() if k not in names}!={k:v for k,v in expected.items() if k not in names}:raise RuntimeError('Unrelated actors changed')
        if not levels.save_current_level() or not levels.load_level(target):raise RuntimeError('Candidate save/reopen failed')
        if editor.get_editor_world().get_path_name().split('.')[0]!=target or h._scene_snapshot(u,actors)!=expected:raise RuntimeError('Candidate readback mismatch')
        report['status']='VENEERS_AND_FRIEZES_MIGRATED_OTHER_DEPENDENCIES_PENDING'
    except Exception as error:
        report.update(status='FAILED_CHECKPOINT_AVAILABLE',error=repr(error));raise
    finally:
        report['protectedUnchanged']=units.offline_plan()==protected and all(sha(Path(p))==v for p,v in asset_hashes.items())
        if not report['protectedUnchanged']:report['status']='FAILED_PROTECTED_HASHES'
        write()
        if not report['protectedUnchanged']:raise RuntimeError('Main/source/protected files changed')
    return report


if __name__=='__main__':print(json.dumps(offline_plan(),indent=2))

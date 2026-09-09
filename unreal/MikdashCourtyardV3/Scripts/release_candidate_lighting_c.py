"""Candidate-only map-level C port. Native switches: -CandidateLightingApply
-CandidateLightingExpectedHash=<64hex> or -CandidateLightingVerify=<apply receipt>.
Existing material assets only; no shared writes. Source C visual review is main-only.
"""
import json, os, re, shutil, sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from release_surface_soft import sha,inventory,check_hashes
from release_place_assets import snapshot_row,numeric_baseline_rows
from release_lighting_v3 import Native,load_spec,resolve_variant,close
TARGET='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
SOURCE=ROOT/'SourceAssets/lighting-review/lighting-v3-apply-20260909T014035693311Z.json'
def disk(p):return ROOT/'Content'/(p.split('.')[0][6:]+'.uasset')
def run(expected=None,verify=None):
 import unreal as u
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 out=ROOT/'SourceAssets/lighting-review'/('candidate-c-'+stamp+'.json')
 report={'status':'started','map':TARGET,'pid':os.getpid(),'errors':[],'mapSaved':False,'sourceCReceipt':str(SOURCE),'sourceCReceiptSha256':sha(SOURCE)}
 def write():out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 mapfile=ROOT/'Content'/(TARGET[6:]+'.umap');before=sha(mapfile);protected={};write()
 try:
  if bool(expected)==bool(verify):raise RuntimeError('Choose expected-hash apply or verify receipt')
  inventory()
  if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
  spec=load_spec();variant=resolve_variant(spec,'C_facade_partition_materials');fields=variant['postProcess'];overrides=variant['componentOverrides']
  if len(fields)!=7 or len(overrides)!=4:raise RuntimeError('C spec scope changed')
  original=json.loads(SOURCE.read_text(encoding='utf-8-sig'))
  if original.get('errors') or not original.get('mapSaved'):raise RuntimeError('Source C application unverified')
  if variant!=original['variantResolved']:raise RuntimeError('C variant differs from reviewed source receipt')
  for name,expected_material_hash in original['instanceSha256After'].items():
   if sha(disk(spec['instanceFolder']+name))!=expected_material_hash:raise RuntimeError('Reviewed limestone changed: '+name)
  earlier=json.loads(Path(verify).read_text(encoding='utf-8-sig')) if verify else None
  if earlier:
   if earlier.get('status')!='saved_reopened' or earlier.get('map')!=TARGET or earlier.get('pid')==os.getpid():raise RuntimeError('Invalid fresh verification source')
   expected=earlier['mapSha256After']
   if check_hashes(earlier['protected']):raise RuntimeError('Protected content changed since apply')
  if not re.fullmatch('[0-9a-fA-F]{64}',expected or '') or before!=expected.lower():raise RuntimeError('Explicit candidate hash mismatch')
  ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
  def clean():
   if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Game/dirty packages')
  clean();protected={str(p):sha(p) for p in (ROOT/'Content').rglob('*') if p.is_file() and p!=mapfile};report['protected']=protected
  if not levels.load_level(TARGET):raise RuntimeError('Load failed')
  clean()
  if ed.get_editor_world().get_outermost().get_name()!=TARGET:raise RuntimeError('Wrong world')
  helper=object.__new__(Native);helper.u=u
  def discover():
   aa=list(actors.get_all_level_actors());desc=[a for a in aa if a.get_actor_label()=='RELEASE_SceneUnits_Selected48_V1']
   if len(desc)!=1:raise RuntimeError('Descriptor count')
   d=desc[0];v=d.get_editor_property('fixed_architecture_origin_cm')
   if int(d.get_editor_property('descriptor_schema_version'))!=1 or int(d.get_editor_property('coordinate_revision').value)!=1 or str(d.get_editor_property('scene_revision'))!='Selected48.v1' or [v.x,v.y,v.z]!=[-6200,0,0]:raise RuntimeError('Selected48 pivot/schema mismatch')
   pp=[a for a in aa if isinstance(a,u.PostProcessVolume) and a.get_editor_property('unbound')]
   if len(pp)!=1:raise RuntimeError('Expected one unbound post-process volume')
   found=[]
   for entry in overrides:
    matches=[]
    for a in aa:
     for c in a.get_components_by_class(u.StaticMeshComponent):
      mesh=c.get_editor_property('static_mesh')
      if mesh and mesh.get_path_name().split('.')[0]==entry['meshAsset']:matches.append((a,c))
    if len(matches)!=1:raise RuntimeError('Exact mesh identity not unique: '+entry['meshAsset'])
    a,c=matches[0];target=entry['material']
    if target.startswith('$new:'):target=variant['newInstances'][target[5:]]['package']
    if not verify and not earlier:
     pose=a.get_actor_location();scale=a.get_actor_scale3d()
     if max(abs(pose.x+248),abs(pose.y),abs(pose.z))>1e-3 or max(abs(scale.x-.96),abs(scale.y-.96),abs(scale.z-.96))>1e-6:raise RuntimeError('Candidate target pose differs '+a.get_name())
    mat=u.load_asset(target)
    if mat is None:raise RuntimeError('Reviewed material absent '+target)
    if target.endswith('MI_PBR_GoldMatte_Partition') and sha(disk(target))!='50d935da7fe496da45c08b32d22d3b8e988000d96b121b1c5364cad71c3a1d43':raise RuntimeError('GoldMatte differs from reviewed C asset')
    found.append((a,c,entry,mat))
   return pp[0],found
  pp,found=discover()
  def snapshot():
   aa=list(actors.get_all_level_actors());result=numeric_baseline_rows([snapshot_row(u,a,TARGET) for a in aa],strict=True)
   allowed={(e['meshAsset'],e['slot']) for e in overrides}
   for a in aa:
    if a.get_outermost().get_name()!=TARGET:continue
    for c in a.get_components_by_class(u.StaticMeshComponent):
     mesh=c.get_editor_property('static_mesh');package=mesh.get_path_name().split('.')[0] if mesh else None
     for slot in range(c.get_num_materials()):
      if (package,slot) not in allowed:
       mat=c.get_material(slot);result['material:'+c.get_path_name()+':'+str(slot)]=mat.get_path_name() if mat else None
   return result
  first=snapshot();clean()
  if not levels.load_level(TARGET):raise RuntimeError('Pristine reload failed')
  clean();second=snapshot();excluded={k for k in set(first)|set(second) if first.get(k)!=second.get(k)}
  pp,found=discover()
  if excluded & {a.get_name() for a,c,e,m in found}:raise RuntimeError('Target component actor churn')
  report['pristineChurn']={k:{'before':first.get(k),'after':second.get(k)} for k in sorted(excluded)}
  baseline={k:v for k,v in second.items() if k not in excluded}
  report['ppBefore']=helper.pp_values(pp,fields)
  report['components']=[{'actor':a.get_name(),'component':c.get_name(),'mesh':e['meshAsset'],'slot':e['slot'],'before':c.get_material(e['slot']).get_path_name(),'after':m.get_path_name()} for a,c,e,m in found]
  if not verify:
   for a,c,e,m in found:
    if c.get_material(e['slot']).get_path_name().split('.')[0]!=e['expectedBefore']:raise RuntimeError('Unexpected before material '+a.get_name())
   checkpoint=ROOT.parent/'ReviewCheckpoints'/('CandidateC-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False);shutil.copy2(mapfile,checkpoint/mapfile.name)
   if sha(checkpoint/mapfile.name)!=before:raise RuntimeError('Checkpoint mismatch')
   for name in ('__ExternalActors__','__ExternalObjects__'):
    folder=ROOT/'Content'/name/TARGET[6:]
    if folder.exists():shutil.copytree(folder,checkpoint/name/TARGET[6:])
   report['checkpoint']=str(checkpoint);write()
   for a,c,e,m in found:a.modify(True);c.modify(True);c.set_material(e['slot'],m)
   pp.modify(True);helper.set_pp(pp,fields)
   if check_hashes(protected):raise RuntimeError('Shared content changed')
   if not levels.save_current_level():raise RuntimeError('Map save refused')
   report['mapSaved']=True;report['mapSha256After']=sha(mapfile);write()
   if not levels.load_level(TARGET):raise RuntimeError('Reopen failed')
  pp,found=discover()
  for a,c,e,m in found:
   if c.get_material(e['slot'])!=m:raise RuntimeError('Component readback mismatch')
  read=helper.pp_values(pp,fields)
  if any(not row['override'] or not close(row['value'],fields[k]) for k,row in read.items()):raise RuntimeError('Local exposure readback mismatch')
  after={k:v for k,v in snapshot().items() if k not in excluded}
  if after!=baseline:raise RuntimeError('Unrelated actor state changed')
  report['ppAfter']=read;report['status']='fresh_verified' if verify else 'saved_reopened'
 except Exception as e:report['status']='failed';report['errors'].append(repr(e));raise
 finally:
  report['mapSha256After']=sha(mapfile);report['mapBytesChanged']=report['mapSha256After']!=before
  report['protectedDifferences']=check_hashes(protected)
  if report['protectedDifferences'] or (verify and report['mapBytesChanged']):report['status']='failed_preservation'
  write()
 if report['status'].startswith('failed'):raise RuntimeError(report['status'])
 return report
if __name__=='__main__':
 try:import unreal as u
 except ImportError:print('Offline only: candidate C map-level port, no native acceptance')
 else:
  cmd=u.SystemLibrary.get_command_line();args={t.split('=',1)[0].lower():t.split('=',1)[1].strip('"') for t in cmd.split() if '=' in t}
  try:
   apply='-candidatelightingapply' in cmd.lower()
   run(expected=args.get('-candidatelightingexpectedhash') if apply else None,verify=args.get('-candidatelightingverify'))
  finally:
   if '-executepythonscript' in cmd.lower() and '-run=pythonscript' not in cmd.lower():u.SystemLibrary.quit_editor()

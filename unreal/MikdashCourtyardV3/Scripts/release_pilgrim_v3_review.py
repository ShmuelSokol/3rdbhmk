"""Guarded fresh-batch V3 import. No actors, retargeting or population edits."""
import hashlib
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/'Scripts/release_pilgrim_v3_review.spec.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def helper(name):
    s=importlib.util.spec_from_file_location('review_'+name,ROOT/'Scripts'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def offline_check():
    spec=json.loads(SPEC.read_text())
    for path,value in spec['frozenFiles'].items():
        if sha(ROOT/path)!=value:raise RuntimeError('Frozen input changed: '+path)
    base=helper('release_pilgrim_v3');result=base.offline_check()
    if result['status']!='READY_FOR_NATIVE_IMPORT':raise RuntimeError('Base source checks refuse: '+repr(result['problems']))
    return spec,result
def run(*,import_assets=False,variants=None):
    spec,offline=offline_check()
    if not import_assets:return dict(status='PREPARED_NOT_NATIVE',spec=spec,sourceCheck=offline)
    import unreal as u
    if Path(u.SystemLibrary.get_project_directory()).resolve()!=ROOT:raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():raise RuntimeError('Live/dirty world')
    chosen=variants or list(spec['visualScales'])
    if not chosen or len(chosen)!=len(set(chosen)) or any(v not in spec['visualScales'] for v in chosen):raise RuntimeError('Unknown/duplicate variant')
    # Per-variant freshness supports small batches without trusting a resume marker.
    for v in chosen:
        path=spec['namespace']+'/'+v
        if u.EditorAssetLibrary.does_directory_exist(path) or (ROOT/'Content'/path[6:]).exists():raise RuntimeError('Fresh variant folder required; preserve partial import')
    base=helper('release_pilgrim_v3');base.DEST=spec['namespace']
    units=helper('release_amah48_candidate');protected=units.offline_plan()
    h=helper('release_resident_crowd');actors=u.get_editor_subsystem(u.EditorActorSubsystem);snapshot=h._scene_snapshot(u,actors)
    original_import=base._import
    def checked_import(ue,tools,assets,filename,folder,name=None):
        objects=original_import(ue,tools,assets,filename,folder,name)
        skeletal=[x for x in objects if isinstance(x,ue.SkeletalMesh)]
        if skeletal:
            if len(skeletal)!=1:raise RuntimeError('One skeletal mesh per variant required')
            skeleton=skeletal[0].get_editor_property('skeleton');path=base._path(skeleton)
            if not path or not path.startswith(folder+'/'):raise RuntimeError('Importer reused foreign/V2 skeleton; unsafe retarget refused')
            clips=[x for x in objects if isinstance(x,ue.AnimSequence)]
            if len(clips)!=4:raise RuntimeError('Four GLB-native clips required')
            for clip in clips:
                if base._path(clip.get_editor_property('skeleton'))!=path or clip.get_editor_property('sequence_length')<=0:raise RuntimeError('Clip skeleton/length incompatible')
            entry=next(v for v in json.loads(base.SPEC.read_text())['variants'] if v['id']==folder.rsplit('/',1)[1])
            row,problems=base._skeletal_readback(ue,skeletal[0],clips,entry,base.author().skeleton())
            if problems or row.get('boneNamesMatchAuthoredRig') is not True or row.get('maxRestPositionErrorCm') is None:raise RuntimeError('Native rest-pose proof unavailable/failed: '+repr(row)+' '+repr(problems))
        return objects
    base._import=checked_import
    # Keep existing importer source/receipts immutable; redirect only its progress file.
    base.PROGRESS=ROOT/'SourceAssets/characters-review/PilgrimRigV3/review-native-progress.json'
    result=None
    try:
        result=base.run(apply=True,batch=len(chosen),variants=chosen,fresh=True)
        if result['status']!='IMPORTED_AND_READ_BACK_VISUAL_REVIEW_PENDING':raise RuntimeError('Import readback not clean')
        return dict(status='IMPORTED_NO_PLACEMENT_VISUAL_REVIEW_PENDING',native=result,
                    recommendedVisualComponentScales={v:spec['visualScales'][v] for v in chosen},
                    placement='Not applied; capsule and sole alignment require separate review')
    finally:
        if units.offline_plan()!=protected or h._scene_snapshot(u,actors)!=snapshot:raise RuntimeError('Protected scene/map/assets changed during import')
        offline_check()

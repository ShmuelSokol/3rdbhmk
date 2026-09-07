"""Adopt visually reviewed exposure fields only; preserve checkpoint and readback."""
import unreal as ue, json, hashlib, shutil
from pathlib import Path
root=Path(ue.Paths.project_dir()).resolve()
source='/Game/MikdashV3/Maps/Courtyard'
pilot='/Game/MikdashV3/MaterialReview/InteriorExposureV1/Courtyard_InteriorExposureV1'
mapfile=root/'Content/MikdashV3/Maps/Courtyard.umap'
review=root/'SourceAssets/visual-review/interior-exposure-comparison-37020d7137/comparison.json'
r=json.loads(review.read_text())
assert r['savedMapsUnchanged'] and len(r['captures'])==4
levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
def volume():
 v=[a for a in ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors() if isinstance(a,ue.PostProcessVolume)]
 assert len(v)==1
 return v[0]
fields=['auto_exposure_method','auto_exposure_min_brightness','auto_exposure_max_brightness','histogram_log_min','histogram_log_max','auto_exposure_speed_up','auto_exposure_speed_down','auto_exposure_low_percent','auto_exposure_high_percent']
fields+=['override_'+n for n in list(fields)]
assert levels.load_level(pilot)
p=volume().get_editor_property('settings')
values={n:p.get_editor_property(n) for n in fields}
assert levels.load_level(source)
v=volume(); original=v.get_editor_property('settings').copy()
assert original.get_editor_property('auto_exposure_method')==ue.AutoExposureMethod.AEM_MANUAL
before=hashlib.sha256(mapfile.read_bytes()).hexdigest()
assert before=='f729834e481056e52cb01734cdf652c4a69a7800a75e6719c16ad847703bd409'
checkpoint=root.parent/'Checkpoints/Before-Reviewed-Interior-Exposure/Courtyard.umap'
checkpoint.parent.mkdir(parents=True,exist_ok=True)
assert not checkpoint.exists()
shutil.copy2(mapfile,checkpoint)
s=original.copy()
for n,value in values.items():s.set_editor_property(n,value)
v.set_editor_property('settings',s)
assert levels.save_current_level() and levels.load_level(source)
saved=volume().get_editor_property('settings')
for n,value in values.items():assert saved.get_editor_property(n)==value,n
restored=saved.copy()
for n in fields:restored.set_editor_property(n,original.get_editor_property(n))
assert restored.export_text()==original.export_text(),'Unrelated postprocess fields changed'
report=dict(status='adopted_saved_reopened',beforeSha256=before,afterSha256=hashlib.sha256(mapfile.read_bytes()).hexdigest(),fields={n:str(v) for n,v in values.items()},review=str(review),visualFinding='Interior details readable; exterior retained. Still flat materials. Transition and packaged tests pending.',checkpoint=str(checkpoint))
(root/'SourceAssets/visual-review/interior-exposure-adopted.json').write_text(json.dumps(report,indent=2)+'\n')
ue.log('REVIEWED_INTERIOR_EXPOSURE_ADOPTED')

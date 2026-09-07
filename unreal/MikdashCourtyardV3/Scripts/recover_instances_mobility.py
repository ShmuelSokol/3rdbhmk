import sys, json, unreal
from pathlib import Path
m=sys.modules['mikdash_instances_stage']; s=m._INST_STAGE
assert s['report']['status']=='FAILED_PARTIAL_UNSAVED_REQUIRES_REVIEW'
assert s['report']['error']=='Decoration should remain static'
assert len(s['assets'])==10 and len(s['actors'])==5
out={'before':[], 'after':[]}
for a in s['actors']:
    cs=a.get_components_by_class(unreal.SceneComponent)
    out['before'].append({'actor':a.get_actor_label(),'components':[{'path':c.get_path_name(),'mobility':str(c.get_editor_property('mobility'))} for c in cs]})
    for c in cs: c.set_editor_property('mobility',unreal.ComponentMobility.STATIC)
    out['after'].append({'actor':a.get_actor_label(),'components':[{'path':c.get_path_name(),'mobility':str(c.get_editor_property('mobility'))} for c in cs]})
Path(unreal.Paths.project_dir(),'SourceAssets/context-review/instances-mobility-recovery.json').write_text(json.dumps(out,indent=2))
checks=m._inst_verify(s['data'])
s['report']['recoveredFromError']=s['report'].pop('error')
s['report'].update(status='STAGED_UNSAVED_REQUIRES_EXPLICIT_SAVE',nativeImportExecuted=True,checks=checks)
m._inst_write(s)
unreal.log('DECORATIVE_RECOVERY_FULL_READBACK_PASSED')

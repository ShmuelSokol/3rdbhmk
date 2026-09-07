"""Read-only parse of root's ASCII FBX skeleton metadata; no mesh extraction."""
import hashlib
import json
import math
from pathlib import Path
import re

FOLDER=Path(__file__).resolve().parent
path=FOLDER/'MannequinReference.fbx'
expected='cc3e893fe8863b8022375f8feaaa134a4dc810ddb83025fdd811bc5134a455b1'
assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
text=path.read_text(encoding='utf8')
matches=list(re.finditer(r'^\tModel: (\d+), "Model::([^"]+)", "([^"]+)" \{',text,re.M))
models={}
for i,m in enumerate(matches):
    end=matches[i+1].start() if i+1<len(matches) else text.find('\nConnections:',m.end())
    block=text[m.end():end]
    props={}
    for key,default in [('Lcl Translation',[0,0,0]),('Lcl Rotation',[0,0,0]),('Lcl Scaling',[1,1,1]),('PreRotation',[0,0,0]),('PostRotation',[0,0,0])]:
        p=re.search(r'^\s*P: "'+key+r'",[^\n]+',block,re.M)
        props[key]=[float(x) for x in p.group(0).split(',')[-3:]] if p else default
    models[int(m.group(1))]={'name':m.group(2),'type':m.group(3),'local_fbx_properties':props}
for child,parent in re.findall(r'C: "OO",(\d+),(\d+)',text):
    child=int(child);parent=int(parent)
    if child in models and parent in models:models[child]['parent']=models[parent]['name']
bones=[m for m in models.values() if m['type'] in ('Root','LimbNode')]
names={b['name'] for b in bones}
by_name={b['name']:b for b in bones};world={}
def multiply(a,b):return [[sum(a[r][k]*b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]
def global_transform(name):
    if name in world:return world[name]
    b=by_name[name];p=b['local_fbx_properties']
    assert p['PreRotation']==[0,0,0] and p['PostRotation']==[0,0,0] and p['Lcl Scaling']==[1,1,1]
    x,y,z=[math.radians(v) for v in p['Lcl Rotation']]
    cx,sx,cy,sy,cz,sz=math.cos(x),math.sin(x),math.cos(y),math.sin(y),math.cos(z),math.sin(z)
    rx=[[1,0,0,0],[0,cx,-sx,0],[0,sx,cx,0],[0,0,0,1]]
    ry=[[cy,0,sy,0],[0,1,0,0],[-sy,0,cy,0],[0,0,0,1]]
    rz=[[cz,-sz,0,0],[sz,cz,0,0],[0,0,1,0],[0,0,0,1]]
    m=multiply(multiply(rz,ry),rx)
    for k in range(3):m[k][3]=p['Lcl Translation'][k]
    if b.get('parent') in by_name:m=multiply(global_transform(b['parent']),m)
    world[name]=m;return m
for b in bones:
    m=global_transform(b['name']);b['derived_world_position_cm']=[m[k][3] for k in range(3)]
assert by_name['upperarm_l']['derived_world_position_cm'][0]>0
assert by_name['upperarm_r']['derived_world_position_cm'][0]<0
chains=[]
for name,source,target in [('Spine',['spine_01','spine_05'],['spine_01','chest']),('Head',['neck_01','head'],['neck_01','head'])]+[
    (limb+'_'+side,[a+'_'+side,b+'_'+side],[a+'_'+side,b+'_'+side])
    for side in ('l','r') for limb,a,b in [('Arm','upperarm','hand'),('Leg','thigh','ball')]]:
    assert all(n in names for n in source)
    chains.append({'chain':name,'source_start_end':source,'target_start_end':target})
axes={}
for key in ['UpAxis','UpAxisSign','FrontAxis','FrontAxisSign','CoordAxis','CoordAxisSign','UnitScaleFactor']:
    p=re.search(r'P: "'+key+r'",[^\n]+',text)
    if p:axes[key]=float(p.group(0).split(',')[-1])
result={'status':'actual_ascii_reference_hash_and_skeleton_metadata_checked','source_asset':'/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple',
        'source_sha256':expected,'root_owned_reference_not_worker_publishing_payload':True,'bone_count':len(bones),'fbx_axes_units':axes,'bones':bones,
        'direct_assignment_compatible':False,'reasons':['Source spine_01 through spine_05 versus original target spine_01/spine_02/chest',
        'Source neck_01/neck_02 versus target neck_01 only','Source nonidentity bone-local Euler reference rotations versus identity target reference rotations',
        'Source twist/finger/IK auxiliary bones are not reproduced in target','Same names on some bones do not establish compatible reference poses'],
        'proposed_native_ik_chains':chains,'retarget_root_source':'pelvis','retarget_root_target':'pelvis',
        'target_side_convention_corrected_from_reference':'Anatomical l uses positiveX, r uses negativeX, facing-Y; derived reference upperarm positions verify this.',
        'mandatory_native_checks':['Inspect importer axis conversion and align both characters in a common forward-facing reference pose',
        'Create separate IK rigs and map the measured chains; inspect shoulder and pelvis offsets in retarget pose',
        'Enumerate actual BS_Idle_Walk_Run animation samples natively; export retargeted copies under the V2 review namespace only',
        'Verify feet, robe clearance, shoulders and full loops before using retargeted animations in an actor'],
        'correction':'SK_Mannequin is the Skeleton asset, not the actual SkeletalMesh. Root exported SKM_Manny_Simple using rendered editor after NullRHI failed.'}
(FOLDER/'mannequin-compatibility.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'bones':len(bones),'axes':axes,'direct_assignment_compatible':False,'chains':chains}))

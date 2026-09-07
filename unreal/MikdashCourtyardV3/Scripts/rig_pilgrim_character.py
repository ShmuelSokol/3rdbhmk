"""Original weighted humanoid + idle/walk GLB. Offline only unless root calls import.

V1 remains immutable. This original skeleton is NOT the Epic mannequin skeleton.
Mannequin animation reuse requires native inspection and reviewed IK retargeting.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'SourceAssets/characters-review/PilgrimRigV2'
DEST='/Game/MikdashV3/CharacterReview/PilgrimRigV2'
spec=importlib.util.spec_from_file_location('pilgrim_v1_source',ROOT/'Scripts/create_pilgrim_character.py')
v1=importlib.util.module_from_spec(spec);spec.loader.exec_module(v1)


def clamp(x,a=0,b=1):return max(a,min(b,x))
def mix(a,b,t):return tuple(a[i]*(1-t)+b[i]*t for i in range(len(a)))
def qaxis(axis,angle):return tuple(axis[i]*math.sin(angle/2) for i in range(3))+(math.cos(angle/2),)
def qmul(a,b):
    x,y,z,w=a;X,Y,Z,W=b
    return (w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z)
def qrotate(q,p):
    r=qmul(qmul(q,p+(0,)),(-q[0],-q[1],-q[2],q[3]));return r[:3]
def add(a,b):return tuple(a[i]+b[i] for i in range(3))
def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def gltf_vec(p):return [p[0]/100,p[2]/100,-p[1]/100]
def gltf_quat(q):return [q[0],q[2],-q[1],q[3]]


def geometry():
    parts=v1.assembly()
    # V1's hidden trouser calves continued above the knee; bending the shin made
    # those unnecessary caps protrude through the robe. Keep visible ankle pants
    # only, a standard covered-body omission, and add modest lower robe ease.
    for p in parts:
        if p['name'].startswith('Calf'):
            s=-1 if p['name'].endswith('L') else 1
            p['vertices'],p['faces']=v1.loft([(4,3.2,3.5,s*8,.5),(12,3.4,3.9,s*8,.5),(24,4.1,4.7,s*8,.5)],32)
        if p['name']=='LongPleatedTunic':
            p['vertices']=[(x,y*(1+.24*clamp((88-z)/50)),z) for x,y,z in p['vertices']]
    return parts


def skeleton():
    bones=[]
    def bone(name,parent,pos):bones.append({'name':name,'parent':parent,'position_cm':pos})
    bone('root',None,(0,0,0));bone('pelvis','root',(0,0,98))
    bone('spine_01','pelvis',(0,0,114));bone('spine_02','spine_01',(0,0,132))
    bone('chest','spine_02',(0,0,143));bone('neck_01','chest',(0,0,153));bone('head','neck_01',(0,0,166))
    for s,side in [(-1,'r'),(1,'l')]:
        bone('clavicle_'+side,'chest',(s*10,0,143))
        bone('upperarm_'+side,'clavicle_'+side,(s*20,0,143))
        bone('lowerarm_'+side,'upperarm_'+side,(s*33,-.5,123))
        bone('hand_'+side,'lowerarm_'+side,(s*44,-1,98))
        bone('thigh_'+side,'pelvis',(s*8,0,88))
        bone('calf_'+side,'thigh_'+side,(s*8,0,47))
        bone('foot_'+side,'calf_'+side,(s*8,0,6))
        bone('ball_'+side,'foot_'+side,(s*8,-9,3))
        bone('skirt_'+side,'pelvis',(s*8,0,88))
    bone('mantle_front','chest',(0,-9,143));bone('mantle_back','chest',(0,11,143))
    lookup={b['name']:i for i,b in enumerate(bones)}
    for b in bones:
        b['parent_index']=lookup[b['parent']] if b['parent'] else None
        b['local_translation_cm']=sub(b['position_cm'],bones[b['parent_index']]['position_cm']) if b['parent'] else b['position_cm']
    return bones


def influence(part,p,bones):
    name=part['name'];x,y,z=p;side='r' if x<0 else 'l';weights={}
    def pair(a,b,t):
        t=clamp(t);weights[a]=1-t;weights[b]=t
    if name.startswith(('SculptedHead','Nose','Ear','Eye','Brow','UpperLip','LowerLip','ShortBeard','Headwrap','WrappedBand')):
        weights={'head':1}
    elif name=='Neck':pair('neck_01','head',(z-151)/9)
    elif name.startswith(('Foot','Sandal')):weights={'foot_'+side:1}
    elif name.startswith('Calf'):pair('foot_'+side,'calf_'+side,(z-5)/14)
    elif name.startswith(('Palm','Finger','Thumb')):weights={'hand_'+side:1}
    elif name.startswith('Wrist'):pair('hand_'+side,'lowerarm_'+side,(z-98)/8)
    elif name.startswith(('LongSleeve','SleeveCuff')):
        if z>137:pair('chest','upperarm_'+side,(abs(x)-15)/8)
        elif z>113:pair('lowerarm_'+side,'upperarm_'+side,(z-113)/19)
        else:pair('hand_'+side,'lowerarm_'+side,(z-101)/10)
    elif name.startswith('MantleShoulder'):pair('chest','clavicle_'+side,(abs(x)-7)/16)
    elif name.startswith('Mantle'):
        support='mantle_back' if name=='MantleBack' else 'mantle_front'
        pair('chest',support,(143-z)/35)
    elif name in ('WovenWaistSash','SashTail'):weights={'pelvis':1}
    elif name=='LongPleatedTunic':
        if z>=142:pair('chest','neck_01',(z-146)/7)
        elif z>=126:pair('spine_02','chest',(z-126)/16)
        elif z>=108:pair('spine_01','spine_02',(z-108)/18)
        elif z>=91:pair('pelvis','spine_01',(z-99)/14)
        else:
            t=clamp((91-z)/31);right=clamp((x+6)/12)
            weights={'pelvis':1-t,'skirt_r':t*(1-right),'skirt_l':t*right}
    else:raise ValueError('No explicit weight policy for '+name)
    idx={b['name']:i for i,b in enumerate(bones)}
    entries=sorted([(idx[k],v) for k,v in weights.items() if v>1e-9],key=lambda a:-a[1])
    assert 1<=len(entries)<=4
    total=sum(w for j,w in entries);entries=[(j,w/total) for j,w in entries]
    return entries+[(0,0.)]*(4-len(entries))


def pose(bones,clip,time):
    q={b['name']:(0.,0.,0.,1.) for b in bones};translations={}
    if clip=='Bind':return q,translations
    period=3.2 if clip=='Idle' else 1.2;phase=math.tau*time/period
    breathing=math.sin(phase)*(.007 if clip=='Idle' else .003)
    q['spine_02']=qaxis((1,0,0),breathing)
    q['neck_01']=qaxis((0,0,1),math.sin(phase)*.009)
    q['head']=qaxis((1,0,0),-breathing*.6)
    for s,side in [(-1,'r'),(1,'l')]:
        swing=math.sin(phase+(math.pi if s>0 else 0))*.12 if clip=='Walk' else .02*math.sin(phase)
        q['upperarm_'+side]=qmul(qaxis((0,1,0),s*math.radians(24)),qaxis((1,0,0),swing))
        q['lowerarm_'+side]=qaxis((1,0,0),-.045)
    if clip=='Idle':
        q['mantle_front']=qaxis((1,0,0),breathing*.25);q['mantle_back']=qaxis((1,0,0),-breathing*.25)
        return q,translations
    pelvis_z=95.8-.25*math.cos(phase*2)
    translations['pelvis']=(0,0,pelvis_z)
    for s,side in [(-1,'r'),(1,'l')]:
        a=phase+(math.pi if s>0 else 0)
        # In-place walking: the swing half lifts; source target in centimeters.
        target_y=16*math.cos(a);lift=5*max(0,math.sin(a))**2
        drop=(pelvis_z-10)-(6+lift)
        distance=math.hypot(target_y,drop);assert distance<82
        angle=math.atan2(target_y,drop);knee=math.acos(distance/82)
        thigh=angle-knee
        q['thigh_'+side]=qaxis((1,0,0),thigh)
        q['calf_'+side]=qaxis((1,0,0),2*knee)
        q['foot_'+side]=qaxis((1,0,0),-angle-knee)
        q['skirt_'+side]=qaxis((1,0,0),thigh*.25)
    q['mantle_front']=qaxis((1,0,0),math.sin(phase)*.015)
    q['mantle_back']=qaxis((1,0,0),math.sin(phase+.3)*.012)
    return q,translations


def global_pose(bones,clip,time):
    rotations,translations=pose(bones,clip,time);result=[]
    for b in bones:
        localq=rotations[b['name']];localt=translations.get(b['name'],b['local_translation_cm'])
        if b['parent_index'] is None:result.append((localq,localt))
        else:
            pq,pt=result[b['parent_index']]
            result.append((qmul(pq,localq),add(pt,qrotate(pq,localt))))
    return result


def skinned_parts(parts,bones,clip,time):
    gp=global_pose(bones,clip,time);result=[]
    for part in parts:
        vertices=[]
        for p in part['vertices']:
            out=[0.,0.,0.]
            for j,w in influence(part,p,bones):
                if w:
                    q,t=gp[j];v=add(t,qrotate(q,sub(p,bones[j]['position_cm'])))
                    for k in range(3):out[k]+=v[k]*w
            vertices.append(tuple(out))
        result.append(dict(part,vertices=vertices))
    return result


class GLB:
    def __init__(self):
        self.buffer=bytearray();self.doc={'asset':{'version':'2.0','generator':'Original PilgrimRigV2 Python author'},'buffers':[],
            'bufferViews':[],'accessors':[],'nodes':[],'meshes':[],'skins':[],'materials':[],'animations':[],'scenes':[],'scene':0}
    def accessor(self,rows,typ,component=5126,target=None,bounds=False):
        sizes={'SCALAR':1,'VEC3':3,'VEC4':4,'MAT4':16};n=sizes[typ]
        flat=[x for row in rows for x in row] if n>1 else rows
        while len(self.buffer)%4:self.buffer.append(0)
        offset=len(self.buffer);fmt={5126:'f',5123:'H',5125:'I'}[component]
        self.buffer.extend(struct.pack('<'+fmt*len(flat),*flat))
        view={'buffer':0,'byteOffset':offset,'byteLength':len(self.buffer)-offset}
        if target:view['target']=target
        vi=len(self.doc['bufferViews']);self.doc['bufferViews'].append(view)
        entry={'bufferView':vi,'componentType':component,'count':len(rows),'type':typ}
        if bounds:
            # Exact float32 readback so min/max match packed accessor values.
            values=struct.unpack('<'+fmt*len(flat),self.buffer[offset:])
            entry['min']=[min(values[k::n]) for k in range(n)];entry['max']=[max(values[k::n]) for k in range(n)]
        ai=len(self.doc['accessors']);self.doc['accessors'].append(entry);return ai
    def save(self,path):
        self.doc['buffers']=[{'byteLength':len(self.buffer)}]
        js=json.dumps(self.doc,separators=(',',':')).encode('utf8')
        js+=b' '*((-len(js))%4);binary=bytes(self.buffer)+b'\0'*((-len(self.buffer))%4)
        path.write_bytes(struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(binary))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(binary),b'BIN\0')+binary)


def export_glb(parts,bones):
    asset=GLB();doc=asset.doc
    for i,b in enumerate(bones):
        node={'name':b['name'],'translation':gltf_vec(b['local_translation_cm'])}
        children=[j for j,k in enumerate(bones) if k['parent_index']==i]
        if children:node['children']=children
        doc['nodes'].append(node)
    matrices=[]
    for b in bones:
        x,y,z=gltf_vec(b['position_cm']);matrices.append([1,0,0,0,0,1,0,0,0,0,1,0,-x,-y,-z,1])
    doc['skins']=[{'name':'OriginalPilgrimHumanoid','joints':list(range(len(bones))),'skeleton':0,
                   'inverseBindMatrices':asset.accessor(matrices,'MAT4')}]
    primitives=[]
    for mat,(rgb,rough) in v1.MATERIALS.items():
        mi=len(doc['materials']);doc['materials'].append({'name':mat,'pbrMetallicRoughness':{'baseColorFactor':list(rgb)+[1.],
                    'metallicFactor':0.,'roughnessFactor':rough}})
        positions=[];normals=[];joints=[];weights=[];indices=[]
        for p in parts:
            if p['material']!=mat:continue
            offset=len(positions);positions.extend(gltf_vec(a) for a in p['vertices'])
            normals.extend([n[0],n[2],-n[1]] for n in v1.normals(p))
            for point in p['vertices']:
                inf=influence(p,point,bones);joints.append([j for j,w in inf]);weights.append([w for j,w in inf])
            indices.extend(offset+i for face in p['faces'] for i in face)
        attrs={'POSITION':asset.accessor(positions,'VEC3',target=34962,bounds=True),'NORMAL':asset.accessor(normals,'VEC3',target=34962),
               'JOINTS_0':asset.accessor(joints,'VEC4',5123,target=34962),'WEIGHTS_0':asset.accessor(weights,'VEC4',target=34962)}
        primitives.append({'attributes':attrs,'indices':asset.accessor(indices,'SCALAR',5125,34963),'material':mi,'mode':4})
    doc['meshes']=[{'name':'SK_PilgrimRigV2','primitives':primitives}]
    doc['nodes'].append({'name':'PilgrimRigV2_Mesh','mesh':0,'skin':0})
    doc['scenes']=[{'name':'OriginalWeightedPilgrim','nodes':[0,len(bones)]}]
    for clip,duration in [('Idle',3.2),('Walk',1.2)]:
        count=round(duration*30)+1;times=[i*duration/(count-1) for i in range(count)]
        time_accessor=asset.accessor(times,'SCALAR',bounds=True);anim={'name':'A_Pilgrim_Original_'+clip,'samplers':[],'channels':[]}
        for j,b in enumerate(bones):
            values=[gltf_quat(pose(bones,clip,t)[0][b['name']]) for t in times]
            if all(v==[0.,0.,0.,1.] for v in values):continue
            si=len(anim['samplers']);anim['samplers'].append({'input':time_accessor,'output':asset.accessor(values,'VEC4'),'interpolation':'LINEAR'})
            anim['channels'].append({'sampler':si,'target':{'node':j,'path':'rotation'}})
        if clip=='Walk':
            values=[gltf_vec(pose(bones,clip,t)[1]['pelvis']) for t in times]
            si=len(anim['samplers']);anim['samplers'].append({'input':time_accessor,'output':asset.accessor(values,'VEC3'),'interpolation':'LINEAR'})
            anim['channels'].append({'sampler':si,'target':{'node':1,'path':'translation'}})
        doc['animations'].append(anim)
    doc['extras']={'provenance':'Original geometry/weights/idle/walk; no mannequin or external animation data copied.',
                   'source_coordinates':'V1 centimeters XYZ; glTF meters X,Z,-Y. No legacy OBJ reflection applies.',
                   'limitations':'Original rig; Epic mannequin retargeting, native import and production animation acceptance pending.'}
    asset.save(OUT/'PilgrimRigV2.glb')
    return doc


def deformation_checks(parts,bones):
    checks=[];allweights=[influence(p,v,bones) for p in parts for v in p['vertices']]
    assert max(abs(sum(w for j,w in inf)-1) for inf in allweights)<1e-9
    bind=skinned_parts(parts,bones,'Bind',0)
    error=max(abs(v[k]-w[k]) for p,q in zip(parts,bind) for v,w in zip(p['vertices'],q['vertices']) for k in range(3))
    assert error<1e-9
    for clip,duration in [('Idle',3.2),('Walk',1.2)]:
        first=skinned_parts(parts,bones,clip,0);last=skinned_parts(parts,bones,clip,duration)
        loop=max(abs(v[k]-w[k]) for p,q in zip(first,last) for v,w in zip(p['vertices'],q['vertices']) for k in range(3))
        assert loop<1e-6
        samples=[]
        for t in [0,duration*.125,duration*.25,duration*.375,duration*.5,duration*.75]:
            deformed=skinned_parts(parts,bones,clip,t);bounds=v1.bounds(deformed)
            assert all(math.isfinite(v) for p in deformed for a in p['vertices'] for v in a)
            footpoints=[v for p in deformed if p['name'].startswith('SandalSole') for v in p['vertices']]
            assert min(v[2] for v in footpoints)>-.001
            delta=max(math.sqrt(sum((a[k]-b[k])**2 for k in range(3))) for p,q in zip(parts,deformed) for a,b in zip(p['vertices'],q['vertices']))
            samples.append({'time_s':t,'bounds_cm':bounds,'minimum_sole_z_cm':min(v[2] for v in footpoints),'maximum_vertex_bind_displacement_cm':delta})
        checks.append({'clip':clip,'duration_s':duration,'loop_vertex_error_cm':loop,'samples':samples})
    return {'status':'passed','bind_pose_error_cm':error,'weight_sum_max_error':max(abs(sum(w for j,w in inf)-1) for inf in allweights),
            'weighted_vertices':len(allweights),'joints':len(bones),'clips':checks,
            'limits':['Numerical checks are not cloth self-intersection or cinematic quality acceptance','No native engine execution']}


def export(previews=False):
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'PilgrimRigV2.glb').exists():raise RuntimeError('Frozen GLB exists; preserve before authoring a distinct iteration')
    parts=geometry();bones=skeleton();v1.check(parts)
    doc=export_glb(parts,bones)
    (OUT/'rig-definition.json').write_text(json.dumps({'status':'original_humanoid_not_Mannequin_compatible_without_retarget','bones':bones,
        'influence_policy':'Explicit anatomical/garment policies, normalized up to4 joints; fingers currently rigid to hand.',
        'animations':[{'name':a['name'],'channels':len(a['channels'])} for a in doc['animations']]},indent=2)+'\n')
    checks=deformation_checks(parts,bones)
    (OUT/'deformation-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    if previews:
        for name,clip,t,yaw in [('idle-front','Idle',0,0),('walk-contact','Walk',0,.6),('walk-passing','Walk',.3,.6),('walk-opposite','Walk',.6,.6)]:
            v1.preview(skinned_parts(parts,bones,clip,t),OUT/(name+'.bmp'),yaw)
    return checks


def run_native():
    """Root-only experimental GLB Interchange import, asset-only isolated namespace."""
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
    if ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Stop gameplay first')
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if assets.does_directory_exist(DEST):raise RuntimeError('Preserve existing namespace')
    frozen=json.loads((OUT/'asset-manifest.json').read_text())
    if hashlib.sha256((OUT/'PilgrimRigV2.glb').read_bytes()).hexdigest()!=frozen['glb_sha256']:
        raise RuntimeError('Frozen GLB hash changed')
    task=ue.AssetImportTask()
    for key,value in dict(filename=str(OUT/'PilgrimRigV2.glb'),destination_path=DEST,automated=True,async_=False,
                          replace_existing=False,save=False).items():task.set_editor_property(key,value)
    receipt={'status':'started','map_mutated':False,'skeletal_compatibility':'Original skeleton; mannequin retargeting required','assets':[]}
    try:
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objects=list(task.get_objects())
        if not objects:objects=[ue.load_asset(p) for p in assets.list_assets(DEST,recursive=True,include_folder=False)]
        skeletal=[a for a in objects if isinstance(a,ue.SkeletalMesh)]
        animations=[a for a in objects if isinstance(a,ue.AnimSequence)]
        if len(skeletal)!=1 or len(animations)!=2:raise RuntimeError('Require exactly one skeletal mesh and two animation sequences; inspect partial Interchange assets')
        for asset in objects:
            assert assets.save_loaded_asset(asset,only_if_is_dirty=False)
            receipt['assets'].append({'path':asset.get_path_name(),'class':asset.get_class().get_name()})
        receipt['status']='skeletal_and_two_clips_imported_saved_unplaced_native_visual_validation_pending'
    except Exception as exc:
        receipt.update(status='failed_partial_assets_preserved',error=str(exc));raise
    finally:(OUT/'native-import.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',action='store_true');parser.add_argument('--previews',action='store_true')
    args=parser.parse_args()
    if args.export:print(json.dumps(export(args.previews)))
    else:parser.print_help()

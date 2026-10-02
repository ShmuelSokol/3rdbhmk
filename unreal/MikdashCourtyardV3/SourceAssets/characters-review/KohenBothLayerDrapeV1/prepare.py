"""Fresh-only two-layer input. Original GLB bytes/rig and all vertex attributes retained."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import copy, hashlib, json, struct
from collections import Counter
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'Scripts'))
import study_kohen_cloth_architecture as A
import study_kohen_cloth_parts as P
from measure_pilgrim_walk import read_glb,read_accessor,author

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,obj):
    p=Path(p)
    if p.exists(): raise FileExistsError(p)
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8');t.rename(p)
def source_parts():
    P.K.KNEE_TOP,P.K.KNEE_BOT=65,20
    return P.body_parts()
def key(v,j,w):return struct.pack('<3f',*v),tuple(j),struct.pack('<4f',*w)
def tri(keys):return min(tuple(keys[i:]+keys[:i]) for i in range(3))

def partition(doc,blob,part,index):
    """Split exact triangle ownership, no position/normal/UV/color/weight regeneration."""
    d=copy.deepcopy(doc);b=bytearray(blob)
    linen=next(q for q in d['meshes'][0]['primitives'] if d['materials'][q['material']]['name']=='KG_Linen')
    attrs=linen['attributes'];values={n:read_accessor(d,blob,a) for n,a in attrs.items()}
    keys=[key(v,j,w) for v,j,w in zip(values['POSITION'],values['JOINTS_0'],values['WEIGHTS_0'])]
    sourcekeys=[]
    for v in part['vertices']:
        inf=P.K.influence(part,v,index)
        sourcekeys.append(key(P.M.C.gltf_vec(v),[j for j,w in inf],[w for j,w in inf]))
    required=Counter(tri([sourcekeys[i] for i in f]) for f in part['faces'])
    indices=np.asarray(read_accessor(d,blob,linen['indices'])).reshape(-1,3)
    yes=[];no=[]
    for f in indices:
        k=tri([keys[i] for i in f])
        if required[k]:yes.append(f);required[k]-=1
        else:no.append(f)
    assert not +required and len(yes)==len(part['faces'])
    # Compact both primitives by copying original accessor element bytes exactly.
    def append_accessor(data,template):
        while len(b)%4:b.append(0)
        vi=len(d['bufferViews']);d['bufferViews'].append(dict(buffer=0,byteOffset=len(b),byteLength=len(data)))
        b.extend(data);a=copy.deepcopy(template);a['bufferView']=vi;a.pop('byteOffset',None);a.pop('min',None);a.pop('max',None)
        ai=len(d['accessors']);d['accessors'].append(a);return ai
    result=[]
    for faces in (no,yes):
        ids=sorted(set(int(i) for f in faces for i in f));remap={v:i for i,v in enumerate(ids)}
        q=copy.deepcopy(linen);q['attributes']={}
        for n,ai in attrs.items():
            a=d['accessors'][ai];view=d['bufferViews'][a['bufferView']]
            count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];size={5121:1,5123:2,5125:4,5126:4}[a['componentType']]*count
            start=view.get('byteOffset',0)+a.get('byteOffset',0);stride=view.get('byteStride',size)
            raw=b''.join(blob[start+i*stride:start+i*stride+size] for i in ids)
            template=copy.deepcopy(a);template['count']=len(ids)
            q['attributes'][n]=append_accessor(raw,template)
        arr=np.asarray([[remap[int(i)] for i in f] for f in faces],dtype='<u4')
        q['indices']=append_accessor(arr.tobytes(),dict(componentType=5125,count=arr.size,type='SCALAR'))
        result.append(q)
    mat=copy.deepcopy(d['materials'][linen['material']]);mat['name']='KG_Ketonet';d['materials'].append(mat);result[1]['material']=len(d['materials'])-1
    pi=d['meshes'][0]['primitives'].index(linen);d['meshes'][0]['primitives'][pi:pi+1]=result
    d['buffers'][0]['byteLength']=len(b)
    assert b[:len(blob)]==blob and d['skins']==doc['skins'] and d['nodes']==doc['nodes']
    return d,bytes(b),dict(ketonetTriangles=len(yes),remainingLinenTriangles=len(no),originalBinaryPrefixPreserved=True,allCopiedAttributesExact=True,geometryAndRigUnchanged=True)

def write_glb(path,d,b):
    if path.exists():raise FileExistsError(path)
    j=json.dumps(d,separators=(',',':')).encode();j+=b' '*((-len(j))%4);b+=b'\0'*((-len(b))%4)
    raw=struct.pack('<III',0x46546c67,2,28+len(j)+len(b))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(b),0x004e4942)+b
    temp=path.with_suffix('.glb.tmp');temp.write_bytes(raw);temp.rename(path)

def main():
    bones,index,parts,*_=source_parts();by={p['name']:p for p in parts}
    source=A.SOURCE;assert sha(source)=='b542efdc1a053fd5ae59720a578701355a4a6e5a203691d999755d6ee4f67535'
    d,b=read_glb(source);nd,nb,proof=partition(d,b,by['Ketonet'],index)
    clone=HERE/'SourcePartitionOnly.glb';write_glb(clone,nd,nb)
    model=json.loads((HERE.parent/'KohenClothExecutableV1/prepared-study-input-v2.json').read_bytes())
    maps={};patterns=[]
    for name in ('Meil','Ketonet'):
        pattern,mapping=A.coarse(by[name],True);patterns.append(pattern);maps[name]=mapping
    patterns+=model['patterns'][2:];model['patterns']=patterns
    model['schema']='kohen-both-layer-v1';model['sourceSha256']=sha(clone)
    model['status']='prepared-both-dynamic-native-uncompiled-unrun'
    model['selectedMaterials']=['KG_Meil','KG_Ketonet']
    model.pop('selectedMaterial');model.pop('selectedSourceRenderPositionsCm')
    model['renderSourcePositionsCm']={}
    for q in nd['meshes'][0]['primitives']:
        n=nd['materials'][q['material']]['name']
        if n in model['selectedMaterials']:model['renderSourcePositionsCm'][n]=[author(v) for v in read_accessor(nd,nb,q['attributes']['POSITION'])]
    model['collisionRepresentation']='Meil and Ketonet disconnected dynamic patterns in ONE self-colliding collection; exact kinematic shin/foot surfaces retained. No inner kinematic shelf.'
    model['renderMapping']='Each material section maps ONLY its own physical layer. Noncloth sections remain unbound.'
    model['studyPhysics']['frameSchemaVersion']=3
    model['studyPhysics']['control']='Same TWO dynamic-layer input points/weights, mapping, normal reconstruction and skinning blend; integration disabled. Original rig is a separate preservation reference.'
    model['settings'].update(selfCollisionFriction=.2,bodyCollisionThicknessCm=.5,edgeStiffness=1.,areaStiffness=1.,bendingStiffness=.1)
    atomic(HERE/'prepared-input.json',model);atomic(HERE/'source-correspondence.json',maps)
    proof.update(originalSha256=sha(source),partitionSha256=sha(clone),dynamicLayers=[dict(name=p['name'],vertices=len(p['verticesCm']),fixed=sum(v==0 for v in p['maxDistanceCm'])) for p in patterns[:2]],candidateDeformation=False)
    atomic(HERE/'partition-proof.json',proof)
    print(json.dumps(proof))
if __name__=='__main__':main()

"""Decode delivered GLB buffers and evaluate skin/animation independently of writer."""
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
sys.dont_write_bytecode=True
FOLDER=Path(__file__).resolve().parent
ROOT=FOLDER.parents[2]
spec=importlib.util.spec_from_file_location('rig_author',ROOT/'Scripts/rig_pilgrim_character.py')
author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
data=(FOLDER/'PilgrimRigV2.glb').read_bytes()
magic,version,length=struct.unpack_from('<4sII',data);assert magic==b'glTF' and version==2 and length==len(data)
n,typ=struct.unpack_from('<I4s',data,12);assert typ==b'JSON'
doc=json.loads(data[20:20+n]);size,typ=struct.unpack_from('<I4s',data,20+n);assert typ==b'BIN\0'
binary=data[28+n:28+n+size]


def accessor(i):
    a=doc['accessors'][i];view=doc['bufferViews'][a['bufferView']]
    count={'SCALAR':1,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
    fmt={5126:'f',5123:'H',5125:'I'}[a['componentType']]
    offset=view.get('byteOffset',0)+a.get('byteOffset',0)
    values=struct.unpack_from('<'+fmt*a['count']*count,binary,offset)
    return [tuple(values[j:j+count]) for j in range(0,len(values),count)]


def multiply(a,b):
    return [[sum(a[r][k]*b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def matrix(t,q):
    x,y,z,w=q
    return [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),t[0]],
            [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),t[1]],
            [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),t[2]],[0,0,0,1]]


def evaluate(clip,time):
    nodes=[{'t':n.get('translation',[0,0,0]),'q':n.get('rotation',[0,0,0,1])} for n in doc['nodes']]
    if clip is not None:
        a=doc['animations'][clip]
        for channel in a['channels']:
            s=a['samplers'][channel['sampler']];times=[v[0] for v in accessor(s['input'])];values=accessor(s['output'])
            nearest=min(range(len(times)),key=lambda i:abs(times[i]-time))
            assert abs(times[nearest]-time)<1e-6,'Test exact sampled keys'
            key={'rotation':'q','translation':'t'}[channel['target']['path']]
            nodes[channel['target']['node']][key]=values[nearest]
    parents={c:i for i,n in enumerate(doc['nodes']) for c in n.get('children',[])}
    globals={}
    def global_matrix(i):
        if i not in globals:
            m=matrix(nodes[i]['t'],nodes[i]['q'])
            globals[i]=multiply(global_matrix(parents[i]),m) if i in parents else m
        return globals[i]
    skin=doc['skins'][0];inverse=accessor(skin['inverseBindMatrices']);transforms=[]
    for j,idx in enumerate(skin['joints']):
        inv=[[inverse[j][r+c*4] for c in range(4)] for r in range(4)]
        transforms.append(multiply(global_matrix(idx),inv))
    vertices=[]
    for primitive in doc['meshes'][0]['primitives']:
        attrs=primitive['attributes'];pos=accessor(attrs['POSITION']);joints=accessor(attrs['JOINTS_0']);weights=accessor(attrs['WEIGHTS_0'])
        for p,js,ws in zip(pos,joints,weights):
            assert abs(sum(ws)-1)<1e-6 and min(ws)>=0
            out=[0.,0.,0.]
            for j,w in zip(js,ws):
                m=transforms[j]
                for r in range(3):out[r]+=w*sum(m[r][c]*(p[c] if c<3 else 1) for c in range(4))
            vertices.append((out[0]*100,-out[2]*100,out[1]*100))
    return vertices


parts=author.geometry();bones=author.skeleton();results=[]
for clip,index,times in [('Bind',None,[0]),('Idle',0,[0,.8,3.2]),('Walk',1,[0,.3,.6,.9,1.2])]:
    for t in times:
        actual=evaluate(index,t);expected_parts=author.skinned_parts(parts,bones,clip,t)
        expected=[v for mat in author.v1.MATERIALS for p in expected_parts if p['material']==mat for v in p['vertices']]
        assert len(actual)==len(expected)
        error=max(abs(a[k]-b[k]) for a,b in zip(actual,expected) for k in range(3))
        assert error<.0001,error
        results.append({'clip':clip,'time_s':t,'decoded_glb_skin_max_error_cm':error,'vertices':len(actual)})
report={'status':'passed','checks':['Actual GLB packed weights/indices/inverse bind matrices read','Actual GLB sampled animation channels evaluated through hierarchy',
         'Independent matrix LBS agrees with author quaternion LBS within0.0001cm'],'samples':results,
         'limits':['Exact sampled keys tested; interpolation behavior not native-tested','No cloth self-intersection guarantee']}
(FOLDER/'glb-decode-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))

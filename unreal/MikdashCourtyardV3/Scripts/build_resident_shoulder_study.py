"""Fresh shoulder-root candidate; original meshes and lower garments are untouched."""
import argparse
import copy
import hashlib
import json
import math
import struct
import numpy as np
from pathlib import Path

import create_resident_v4 as R
import create_resident_v4_body as B
import create_pilgrim_v3 as C
from measure_pilgrim_walk import read_glb,read_accessor

ROOT=Path(__file__).resolve().parents[1]


def build(folder, short):
    folder.mkdir(parents=True,exist_ok=False)
    variant=R.variant('V3_Pilgrim_'+short)
    parts=R.finalize(R.assembly(variant),variant)
    bones=C.skeleton()
    index={b['name']:i for i,b in enumerate(bones)}
    source=ROOT/'SourceAssets/characters-review/ResidentV4/meshes'/('SK_RV4_'+short+'.glb')
    regenerated=folder/'baseline.glb'
    R.export_glb(regenerated,parts,bones,index,variant)
    original_doc,original_bin=read_glb(source)
    regenerated_doc,regenerated_bin=read_glb(regenerated)
    assert original_doc==regenerated_doc, 'Current generator layout differs from shipped source'
    required={original_doc['skins'][0]['inverseBindMatrices']}
    normal_accessors=set()
    for primitive in original_doc['meshes'][0]['primitives']:
        required.update(primitive['attributes'].values())
        normal_accessors.add(primitive['attributes']['NORMAL'])
        required.add(primitive['indices'])
    for i in required:
        actual=read_accessor(original_doc,original_bin,i)
        regenerated_values=read_accessor(regenerated_doc,regenerated_bin,i)
        matches=(np.allclose(actual,regenerated_values,rtol=0,atol=1e-12) if i in normal_accessors
                 else actual==regenerated_values)
        assert matches, ('Source accessor mismatch',i)
    candidate=copy.deepcopy(parts)
    tunic=B.Tunic(variant)
    changes=[]
    for part in candidate:
        if part['name'] not in ('SleeveL','SleeveR'): continue
        side=1 if part['name'].endswith('L') else -1
        origin,direction,_,_=C.arm_frame(side)
        along=[C.dot(C.sub(p,origin),direction) for p in part['vertices']]
        root=[i for i,t in enumerate(along) if abs(t)<1e-6]
        assert len(root)>=28, 'Proximal sleeve ring missing'
        # Translate the complete proximal cross-section inward, preserving its
        # shape; search until every root vertex is inside the folded torso.
        def inside(p):
            theta=math.atan2(p[1],p[0])
            surface=tunic.point(theta,p[2],0.)
            return math.hypot(p[0],p[1]) <= math.hypot(surface[0],surface[1])-.75
        shift=0.
        while not all(inside((part['vertices'][i][0]-side*shift,*part['vertices'][i][1:])) for i in root):
            shift+=.25
            assert shift<=16., 'Shoulder root needs excessive correction'
        before=copy.deepcopy(part['vertices'])
        blend=[1.-C.smooth(C.clamp(t/18.)) for t in along]
        for i,p in enumerate(part['vertices']):
            part['vertices'][i]=(p[0]-side*shift*blend[i],p[1],p[2])
        # Blend torso/arm influence over the upper 18 cm; distal weights remain
        # unchanged. Lookup is deterministic at exported vertices.
        weights={}
        for i,p in enumerate(part['vertices']):
            torso,arm=C.torso_skin(p),C.sleeve_skin(before[i])
            weights[tuple(p)]={k:torso.get(k,0.)*blend[i]+arm.get(k,0.)*(1.-blend[i])
                               for k in set(torso)|set(arm)}
        part['skin']=lambda p,w=weights:w[tuple(p)]
        part['normals']=C.normals(part)
        changes.append(dict(part=part['name'],rootVertices=len(root),inwardCm=shift,blendLengthCm=18.))
    assert len(changes)==2
    for a,b in zip(parts,candidate):
        if a['name'] not in ('SleeveL','SleeveR'): assert a==b
    target=folder/('SK_RV4_'+short+'_ShoulderStudy.glb')
    R.export_glb(target,candidate,bones,index,variant)
    # Keep original binary bytes outside explicit sleeve attributes, including
    # signed-zero representations in untouched morph data.
    candidate_doc,candidate_bin=read_glb(target)
    output=bytearray(original_bin)
    allowed=set()
    for primitive in original_doc['meshes'][0]['primitives']:
        material=original_doc['materials'][primitive['material']]['name']
        offset=0
        for part in [p for p in parts if p['material']==material]:
            count=len(part['vertices'])
            if part['name'] in ('SleeveL','SleeveR'):
                for attr,stride in (('POSITION',12),('NORMAL',12),('JOINTS_0',8),('WEIGHTS_0',16)):
                    a=original_doc['accessors'][primitive['attributes'][attr]]
                    view=original_doc['bufferViews'][a['bufferView']]
                    start=view.get('byteOffset',0)+a.get('byteOffset',0)+offset*stride
                    end=start+count*stride
                    output[start:end]=candidate_bin[start:end]
                    allowed.update(range(start,end))
            offset+=count
    changed={i for i,(a,b) in enumerate(zip(original_bin,output)) if a!=b}
    assert changed and changed<=allowed
    encoded=json.dumps(candidate_doc,separators=(',',':')).encode()
    encoded+=b' '*((-len(encoded))%4)
    binary=bytes(output)+b'\0'*((-len(output))%4)
    target.write_bytes(struct.pack('<III',0x46546c67,2,28+len(encoded)+len(binary))+
                       struct.pack('<II',len(encoded),0x4e4f534a)+encoded+
                       struct.pack('<II',len(binary),0x004e4942)+binary)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report=dict(status='source-study-needs-native-and-motion-review',variant=short,
                source=str(source),sourceSha256=sha(source),candidate=target.name,
                candidateSha256=sha(target),changes=changes,
                changedBinaryBytes=len(changed),allowedBinaryBytes=len(allowed),
                preserved='All non-sleeve source parts, topology, UVs and colours; distal sleeve weights/positions.',
                limitation='Root radial test is reference pose only; not animated or whole-sleeve collision acceptance.')
    (folder/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--folder',type=Path,required=True)
    parser.add_argument('--variant',default='Youth')
    args=parser.parse_args()
    build(args.folder,args.variant)

"""Independent GLB edit-boundary and sampled sleeve-root attachment checks."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
import create_resident_v4 as R
import create_pilgrim_v3 as C
import measure_kohen_garment_clearance as M
from measure_pilgrim_walk import read_glb,read_accessor,Rig


def verify(folder):
    review=json.loads((folder/'review.json').read_text())
    source=Path(review['source']);candidate=folder/review['candidate']
    doc,binary=read_glb(source);cd,cb=read_glb(candidate)
    parts=R.finalize(R.assembly(R.variant('V3_Pilgrim_'+review['variant'])),R.variant('V3_Pilgrim_'+review['variant']))
    allowed=set();bounds=set();mapped={};root_masks={}
    for prim in doc['meshes'][0]['primitives']:
        material=doc['materials'][prim['material']]['name'];offset=0
        for part in [p for p in parts if p['material']==material]:
            count=len(part['vertices']);attrs=prim['attributes']
            if part['name'] in ('SleeveL','SleeveR'):
                for attr,stride in (('POSITION',12),('NORMAL',12),('JOINTS_0',8),('WEIGHTS_0',16)):
                    a=doc['accessors'][attrs[attr]];v=doc['bufferViews'][a['bufferView']]
                    start=v.get('byteOffset',0)+a.get('byteOffset',0)+offset*stride
                    allowed.update(range(start,start+count*stride))
                bounds.add(attrs['POSITION'])
                side=1 if part['name'].endswith('L') else -1
                origin,direction,_,_=C.arm_frame(side)
                root_masks[part['name']]=np.array([abs(C.dot(C.sub(p,origin),direction))<1e-6 for p in part['vertices']])
            if part['name'] in ('SleeveL','SleeveR','Tunic'):
                versions=[]
                for d,b in ((doc,binary),(cd,cb)):
                    p,j,w=[np.asarray(read_accessor(d,b,attrs[k])[offset:offset+count]) for k in ('POSITION','JOINTS_0','WEIGHTS_0')]
                    p=np.column_stack((p[:,0],-p[:,2],p[:,1]))*100
                    assert np.isfinite(p).all() and np.isfinite(w).all() and np.allclose(w.sum(axis=1),1.,atol=1e-6)
                    versions.append((p,j.astype(int),w))
                mapped[part['name']]=(versions,np.asarray(part['faces']))
                if part['name'] in root_masks:
                    distal=np.array([C.dot(C.sub(p,origin),direction)>=18.-1e-6 for p in part['vertices']])
                    for a,b in zip(versions[0],versions[1]):
                        assert np.array_equal(a[distal],b[distal]), 'Distal sleeve position/weight changed'
            offset+=count
    expected=copy.deepcopy(doc)
    for i in bounds:
        p=np.asarray(read_accessor(cd,cb,i))
        expected['accessors'][i]['min']=p.min(axis=0).tolist()
        expected['accessors'][i]['max']=p.max(axis=0).tolist()
    assert cd==expected and len(binary)==len(cb)
    changed={i for i,(a,b) in enumerate(zip(binary,cb)) if a!=b}
    assert changed and changed<=allowed
    torso,faces=mapped['Tunic'];rest=torso[0][0]
    faces=faces[rest[faces].mean(axis=1)[:,2]>125.]
    signs=M.tube_signs(rest,faces)
    bones=C.skeleton();rows=[]
    rig_source=source.parents[2]/'PilgrimRigV3/walk-v2/meshes'/('V3_Pilgrim_'+review['variant']+'.glb')
    for clip,rate in (('Walk',240),('Idle',30)):
        rig=Rig(rig_source,'A_Pilgrim_Original_'+clip)
        count=round(rig.duration*rate)
        for i in range(count):
            time=rig.duration*i/count;A,b=M.joint_affines(rig,rig.pose(time),bones)
            t=M.skin(*torso[0],A,b)[faces]
            maxima=[]
            for version in (0,1):
                points=np.concatenate([M.skin(*mapped[n][0][version],A,b)[mask] for n,mask in root_masks.items()])
                maxima.append(float(M.nearest_signed(points,t,signs).max()))
            rows.append(dict(clip=clip,time=time,beforeMaxOutsideCm=maxima[0],afterMaxOutsideCm=maxima[1]))
    return dict(status='sampled-root-check-passed' if all(r['afterMaxOutsideCm']<=0 for r in rows) else 'sampled-root-check-failed',
                scope='Sleeve proximal vertices versus nearest outward upper-tunic surface; walk240Hz/idle30Hz endpoints excluded. Not continuous collision, whole-sleeve clearance or native animation acceptance.',
                changedBinaryBytes=len(changed),exactEditBoundaries=True,
                candidateSha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                worstBeforeCm=max(r['beforeMaxOutsideCm'] for r in rows),worstAfterCm=max(r['afterMaxOutsideCm'] for r in rows),samples=rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',type=Path,required=True);args=parser.parse_args()
    output=args.folder/'motion-root-review.json';assert not output.exists()
    result=verify(args.folder);output.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],result['worstBeforeCm'],result['worstAfterCm'])
    raise SystemExit(0 if result['status']=='sampled-root-check-passed' else 1)

"""One projection-cycle audit of FAILED cached endpoints; no new candidate/solve/sweep.

Reports conflicts immediately after each actual operation and preserves failed NPZs.
"""
import sys
sys.dont_write_bytecode=True
import json
import numpy as np
from prepare import HERE,atomic,source_parts,P,sha
from offline_drape import Cloth,pattern_arrays,contact_body,contact_outer,mapping,deform

def measure(c):
    length=np.linalg.norm(c.x[c.e[:,1]]-c.x[c.e[:,0]],axis=1);ratio=length/c.restEdges;worst=int(ratio.argmax());ij=c.e[worst]
    excess=np.linalg.norm(c.x-c.x[c.anchor],axis=1)-c.tether
    p=c.p;cols=len(p['sourceColumnIndices'])
    return dict(layer=p['name'],maxEdgeStretch=float(ratio.max()),p95EdgeStretch=float(np.percentile(ratio,95)),edgesOver5Percent=int((ratio>1.05).sum()),maxAbsoluteEdgeExtensionCm=float((length-c.restEdges).max()),maxTetherExcessCm=float(max(0,excess.max())),maxTetherRatio=float(np.max(np.divide(np.linalg.norm(c.x-c.x[c.anchor],axis=1),c.tether,out=np.ones(len(c.x)),where=c.tether>0))),maxPinErrorCm=float(np.linalg.norm(c.x[c.pin]-c.control[c.pin],axis=1).max()),worstEdge=dict(indices=ij.tolist(),restLengthCm=float(c.restEdges[worst]),posedLengthCm=float(length[worst]),restXYZ=c.rest[ij].tolist(),posedXYZ=c.x[ij].tolist(),fixed=c.pin[ij].tolist(),sourceGrid=[[p['sourceRingIndices'][int(i)//cols],p['sourceColumnIndices'][int(i)%cols]] for i in ij]))

def gradients(rest,posed,faces):
    r=rest[faces];q=posed[faces];u=r[:,1]-r[:,0];v=r[:,2]-r[:,0];a=np.linalg.norm(u,axis=1);b=np.sum(u*v,axis=1)/a;c=np.sqrt(np.maximum(0,np.sum(v*v,axis=1)-b*b));keep=c>1e-10
    F=np.stack(((q[:,1]-q[:,0])/a[:,None],((q[:,2]-q[:,0])-(b/a)[:,None]*(q[:,1]-q[:,0]))/np.maximum(c[:,None],1e-12)),axis=2)
    sv=np.linalg.svd(F[keep],compute_uv=False)
    return dict(maxPrincipalStretch=float(sv[:,0].max()),p95PrincipalStretch=float(np.percentile(sv[:,0],95)),minPrincipalStretch=float(sv[:,1].min()),maxAreaRatio=float(np.prod(sv,axis=1).max()),degenerateRestFaces=int((~keep).sum()))

def main():
    model=json.loads((HERE/'prepared-input.json').read_bytes());bones,_,parts,*_=source_parts();by={p['name']:p for p in parts};rows=[];grad=[]
    for name,t in [('walk',.295833),('walk',1.166667),('tend',5.)]:
        stem=name+'-'+str(round(t*1e6));path=HERE/'Offline01'/(stem+'.npz');before=sha(path);saved=np.load(path)
        cs=[Cloth(p) for p in model['patterns'][:2]];clip=next(x for x in P.M.CLIPS if x[0]==name);rig=P.M.Rig(clip[1],clip[2]);a,b=P.M.joint_affines(rig,rig.pose(t),bones)
        body=[];faces=[]
        for p in model['patterns'][2:]:
            v,j,w=pattern_arrays(p);faces.extend(np.asarray(p['faces'])+sum(len(x) for x in body));body.append(P.M.skin(v,j,w,a,b))
        body=np.concatenate(body);faces=np.asarray(faces)
        for c,key in zip(cs,('outer','inner')):
            c.set_pose(a,b);c.x=saved[key].copy();v=np.asarray(by[c.p['name']]['vertices']);f=np.asarray(by[c.p['name']]['faces']);dense=deform(mapping(v,c.rest,c.f),c.x)
            grad.append(dict(pose=stem,layer=c.p['name'],**gradients(v,dense,f)))
        stages=[]
        def record(stage):stages.append(dict(stage=stage,layers=[measure(c) for c in cs]))
        record('cached-failed-endpoint')
        for stiffness,label in ((1.,'edge-length-projection'),(.1,'opposite-vertex-bending-projection')):
            for c in cs:
                for e,length,s in c.constraints:
                    if s!=stiffness:continue
                    i,j=e.T;dv=c.x[j]-c.x[i];dist=np.maximum(np.linalg.norm(dv,axis=1),1e-10);den=c.inv[i]+c.inv[j];lam=np.divide((dist-length)*s,den,out=np.zeros_like(dist),where=den>0);delta=dv*(lam/dist)[:,None];c.x[i]+=c.inv[i,None]*delta;c.x[j]-=c.inv[j,None]*delta
            record(label)
        for c in cs:
            dv=c.x-c.x[c.anchor];dist=np.maximum(np.linalg.norm(dv,axis=1),1e-12);c.x-=dv*(np.maximum(0,dist-c.tether)/dist)[:,None]
        record('geodesic-tether-upper-bound-projection')
        for c in cs:
            dv=c.x-c.control;dist=np.maximum(np.linalg.norm(dv,axis=1),1e-12);c.x-=dv*(np.maximum(0,dist-c.radius)/dist)[:,None];c.x[c.pin]=c.control[c.pin]
        record('maxdistance-and-fixed-pins')
        for c in cs:contact_body(c,body,faces)
        record('body-triangle-and-ground-contact')
        for c in cs:c.self_contact()
        record('self-vertex-contact')
        contact_outer(cs[0],cs[1]);record('coupled-interlayer-contact')
        for c in cs:c.x[c.pin]=c.control[c.pin]
        record('final-fixed-pins')
        assert sha(path)==before
        rows.append(dict(pose=stem,oneDiagnosticProjectionCycleOnly=True,stages=stages,failedEndpointPreserved=before))
    atomic(HERE/'Offline01/constraint-conflicts.json',dict(status='REJECTED diagnostic; no parameter change or new candidate',rows=rows,denseGradients=grad,interpretation=['Rest length comes from exact unchanged retained source vertices, not a retargeted or enlarged rest mesh.','Geodesic tethers limit distance to upper anchors; they do NOT guarantee edge lengths or local deformation gradients.','This sequential finite-iteration PBD resolves contact after length projection; contact can reintroduce strain at iteration end.','Read recorded stage deltas before attributing a specific defect to a solver operation. No claim that a single corrective sweep solves the conflict.','5percent counts are diagnostic bins, not a substituted acceptance threshold. Existing clearance failures remain decisive.']))
    for r in rows:
        print(r['pose'])
        for s in r['stages']:print(s['stage'],[(x['layer'],round(x['maxEdgeStretch'],4),round(x['maxTetherExcessCm'],4)) for x in s['layers']])
if __name__=='__main__':main()

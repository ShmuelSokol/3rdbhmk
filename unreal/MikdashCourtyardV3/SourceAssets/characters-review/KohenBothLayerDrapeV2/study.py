"""Bounded deterministic rest-compatible source study; no Unreal or asset write.

One rigid chest support/top ring per layer. Rest edges, areas and geodesic tether
lengths unchanged. All constraint families contribute before residual validation.
Failure retains evidence and stops progression; no random restarts/pose skipping.
"""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial.transform import Rotation,Slerp
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'KohenBothLayerDrapeV1';AUDIT=HERE.parent/'KohenBothLayerContactAuditV1'
sys.path.insert(0,str(OLD))
from prepare import source_parts,P,A,sha,atomic
from offline_drape import pattern_arrays,edges,color_edges,nearest,mapping,deform,normals
from diagnose_constraints import gradients

GAP=.5
TOL=.001 # convergence residual cm; not a relaxed strain allowance
DEADLINE=float('inf')

def exhaustive(points,v,f):
    rows=[]
    for i in range(0,len(points),32):
        if time.monotonic()>DEADLINE:raise TimeoutError('Total budget in exhaustive geometry readback')
        rows.append(nearest(points[i:i+32],v,f,len(f)))
    return tuple(np.concatenate([x[k] for x in rows]) for k in range(4))

class Layer:
    def __init__(self,p):
        self.p=p;self.rest,self.j,self.w=pattern_arrays(p);self.f=np.array(p['faces'],int);self.e=edges(self.f)
        self.pin=np.isclose(self.rest[:,2],self.rest[:,2].max(),atol=1e-10)
        self.x=self.rest.copy();self.control=self.x.copy();self.inv=np.ones(len(self.x));self.inv[self.pin]=0
        self.length=np.linalg.norm(self.rest[self.e[:,1]]-self.rest[self.e[:,0]],axis=1)
        self.groups=[(g,np.linalg.norm(self.rest[g[:,1]]-self.rest[g[:,0]],axis=1)) for g in color_edges(self.e)]
        t=self.rest[self.f];self.area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)*.5
        graph=coo_matrix((np.r_[self.length,self.length],(np.r_[self.e[:,0],self.e[:,1]],np.r_[self.e[:,1],self.e[:,0]])),shape=(len(self.x),)*2).tocsr()
        fixed=np.flatnonzero(self.pin);D=dijkstra(graph,directed=False,indices=fixed);which=D.argmin(axis=0)
        self.anchor=fixed[which];self.tether=D[which,np.arange(len(self.x))];assert np.isfinite(self.tether).all()
        self.history=None;self.history_bary=None
        self.support_R=np.eye(3);self.support_t=np.zeros(3)
    def support(self,a,b,index):
        R=a[index['chest']];t=b[index['chest']]
        assert np.max(np.abs(R.T@R-np.eye(3)))<1e-8 and np.linalg.det(R)>0
        # Rigid predictor transports the prior shape, NOT a rest reset. It keeps
        # every edge/area/tether unchanged before the joint contact solve.
        # This is quasi-static support continuation, not an inertial simulation.
        self.x=(self.x-self.support_t)@self.support_R@R.T+t
        self.support_R=R.copy();self.support_t=t.copy()
        self.control=P.M.skin(self.rest,self.j,self.w,a,b)
        self.control[self.pin]=self.rest[self.pin]@R.T+t
        self.x[self.pin]=self.control[self.pin]
        ids=np.flatnonzero(self.pin);before=self.rest[ids,None]-self.rest[ids]
        after=self.control[ids,None]-self.control[ids]
        return float(np.max(np.abs(np.linalg.norm(before,axis=2)-np.linalg.norm(after,axis=2))))
    def material_project(self):
        for e,L in self.groups:
            i,j=e.T;d=self.x[j]-self.x[i];n=np.maximum(np.linalg.norm(d,axis=1),1e-12);den=self.inv[i]+self.inv[j]
            s=np.divide(n-L,den*n,out=np.zeros_like(n),where=den>0)
            self.x[i]+=self.inv[i,None]*s[:,None]*d;self.x[j]-=self.inv[j,None]*s[:,None]*d
        # Triangle area constraint (Jacobi with per-vertex accumulation averaging).
        t=self.x[self.f];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);twice=np.linalg.norm(cross,axis=1)
        normal=cross/np.maximum(twice[:,None],1e-12)
        g=np.stack((np.cross(t[:,1]-t[:,2],normal),np.cross(t[:,2]-t[:,0],normal),np.cross(t[:,0]-t[:,1],normal)),axis=1)*.5
        inv=self.inv[self.f];den=np.sum(inv*np.sum(g*g,axis=2),axis=1)
        lam=np.divide(twice*.5-self.area,den,out=np.zeros_like(den),where=den>1e-12)
        delta=np.zeros_like(self.x);count=np.zeros(len(self.x))
        for k in range(3):np.add.at(delta,self.f[:,k],-inv[:,k,None]*lam[:,None]*g[:,k]);np.add.at(count,self.f[:,k],1)
        self.x+=delta/np.maximum(count[:,None],1)
        d=self.x-self.x[self.anchor];n=np.maximum(np.linalg.norm(d,axis=1),1e-12)
        self.x-=d*(np.maximum(0,n-self.tether)/n)[:,None]
        self.x[self.pin]=self.control[self.pin]
    def residual(self):
        L=np.linalg.norm(self.x[self.e[:,1]]-self.x[self.e[:,0]],axis=1)
        t=self.x[self.f];ar=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)*.5
        return dict(edgeAbsCm=float(np.max(np.abs(L-self.length))),maxEdgeStretch=float(np.max(L/self.length)),
            areaRelative=float(np.max(np.abs(ar/self.area-1))),
            tetherExcessCm=float(max(0,np.max(np.linalg.norm(self.x-self.x[self.anchor],axis=1)-self.tether))),
            pinErrorCm=float(np.max(np.linalg.norm(self.x[self.pin]-self.control[self.pin],axis=1))),
            **gradients(self.rest,self.x,self.f))

def body_arrays(model,a,b):
    vs=[];fs=[];parts=[]
    for p in model['patterns'][2:]:
        rest,j,w=pattern_arrays(p);v=P.M.skin(rest,j,w,a,b);f=np.array(p['faces'],int)
        fs.extend(f+sum(len(x) for x in vs));vs.append(v);parts.append((p['name'],v,f))
    return np.concatenate(vs),np.array(fs),parts

def inside_body(points,parts):
    inside=np.zeros(len(points),bool)
    for _,v,f in parts:
        candidate=np.all((points>=v.min(0)-.001)&(points<=v.max(0)+.001),axis=1)
        if candidate.any():inside[candidate]|=P.M.inside(points[candidate],v[f])
    return inside

def body_contact(c,v,f,parts):
    ids,bar,q,dist=nearest(c.x,v,f,16)
    t=v[f[ids]];normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
    signed=np.sum((c.x-q)*normal,axis=1);interior=inside_body(c.x,parts)
    if c.history is not None:
        # Retain last accepted exterior feature for local interior trials. No
        # nearest-sole reassignment can authorize crossing to the foot underside.
        bad=interior
        oldtri=v[f[c.history]];oldq=np.einsum('ni,nij->nj',c.history_bary,oldtri)
        oldn=np.cross(oldtri[:,1]-oldtri[:,0],oldtri[:,2]-oldtri[:,0]);oldn/=np.maximum(np.linalg.norm(oldn,axis=1,keepdims=True),1e-12)
        q[bad]=oldq[bad];normal[bad]=oldn[bad]
    signed=np.sum((c.x-q)*normal,axis=1)
    # Exterior closest-feature distance, not infinite plane contact for far points.
    direction=(c.x-q)/np.maximum(np.linalg.norm(c.x-q,axis=1,keepdims=True),1e-12)
    use=interior;direction[use]=normal[use]
    depth=np.where(use,np.maximum(0,GAP-signed),np.maximum(0,GAP-dist))
    c.x[~c.pin]+=depth[~c.pin,None]*direction[~c.pin]
    c.x[~c.pin,2]=np.maximum(c.x[~c.pin,2],GAP)

def layer_contact(outer,inner):
    ids,bary,q,dist=nearest(outer.x,inner.x,inner.f,16);tri=inner.f[ids]
    n=np.einsum('ni,nij->nj',bary,normals(inner.x,inner.f)[tri]);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    signed=np.sum((outer.x-q)*n,axis=1)
    # Tube ordering needed near contact; reject rather than project distant planes.
    depth=np.where(dist<2.,np.maximum(0,GAP-signed),0)
    den=outer.inv+np.sum(inner.inv[tri]*bary*bary,axis=1);lam=np.divide(depth,den,out=np.zeros_like(depth),where=den>0)
    outer.x+=outer.inv[:,None]*lam[:,None]*n
    delta=np.zeros_like(inner.x);count=np.zeros(len(inner.x))
    for k in range(3):
        np.add.at(delta,tri[:,k],-inner.inv[tri[:,k],None]*bary[:,k,None]*lam[:,None]*n)
        np.add.at(count,tri[:,k],depth>0)
    inner.x+=delta/np.maximum(count[:,None],1)

def contacts(layers,v,f,parts,save_history=False):
    result=[]
    for c in layers:
        ids,bary,q,dist=exhaustive(c.x,v,f);inside=inside_body(c.x,parts)
        result.append(dict(layer=c.p['name'],insideBody=int(inside.sum()),minimumBodyDistanceCm=float(dist.min()),
            bodyGapDeficitCm=float(max(0,GAP-dist.min())),groundDeficitCm=float(max(0,GAP-c.x[:,2].min())),
            fixedInsideBody=int(inside[c.pin].sum())))
        if save_history and not inside.any():c.history=ids;c.history_bary=bary
    o,i=layers;_,_,q,dist=exhaustive(o.x,i.x,i.f)
    result.append(dict(pair='Meil-Ketonet',minimumUnsignedVertexTriangleDistanceCm=float(dist.min()),
                       gapDeficitCm=float(max(0,GAP-dist.min()))))
    return result

def ornament_transport(by,outer,anchor_map,index):
    K=P.K;made=K.Parts();meil=K.meil(made);K.bells_and_pomegranates(made,meil)
    parts={p['name']:p for p in made.parts};rest=np.asarray(by['Meil']['vertices'])
    dense=deform(mapping(rest,outer.rest,outer.f),outer.x);rows=[];output={}
    def frame(v,j):
        x=v[(j+1)%176]-v[(j-1)%176];x/=np.linalg.norm(x)
        z=v[j+176]-v[j];z-=x*np.dot(x,z);z/=np.linalg.norm(z)
        return np.column_stack((x,np.cross(z,x),z))
    for name in ('MeilBells','MeilPomegranates'):
        p=parts[name];old=np.asarray(p['vertices']);new=old.copy();covered=set()
        entries=[r for r in anchor_map['rows'] if r['part']==name];assert len(entries)==72
        for entry in entries:
            ids=np.asarray(entry['vertices']);j=entry['sourceHemIndex'];assert not covered.intersection(ids.tolist());covered.update(ids.tolist())
            assert np.array_equal(np.asarray(meil[1][j]),np.asarray(entry['sourceAnchorCm']))
            for point in old[ids]:assert np.array_equal(np.asarray(p['anchor_map'][tuple(point)]),entry['sourceAnchorCm'])
            R=frame(dense,j)@frame(rest,j).T;assert np.linalg.det(R)>0
            new[ids]=(old[ids]-rest[j])@R.T+dense[j]
            offset=np.abs(np.linalg.norm(new[ids]-dense[j],axis=1)-np.linalg.norm(old[ids]-rest[j],axis=1))
            rows.append(dict(part=name,ornament=entry['ornament'],sourceHemIndex=j,vertices=len(ids),
                rigidError=float(np.max(np.abs(R.T@R-np.eye(3)))),attachmentErrorCm=float(offset.max())))
        assert len(covered)==len(old);output[name]=(new,np.asarray(p['faces'],int))
    return output,rows

def main():
    global DEADLINE
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--seconds',type=float,default=180);ap.add_argument('--iterations',type=int,default=160)
    args=ap.parse_args();assert 0<args.seconds<=300 and 1<=args.iterations<=200
    out=HERE/args.out;assert out.parent==HERE;out.mkdir(exist_ok=False)
    started=time.monotonic();DEADLINE=started+args.seconds
    protected={str(p):sha(p) for folder in (OLD,AUDIT,HERE.parent/'KohenJointConstraintV1') for p in folder.rglob('*') if p.is_file()}
    bones,index,parts,*_=source_parts();by={p['name']:p for p in parts};protected[str(A.SOURCE)]=sha(A.SOURCE)
    model=json.loads((OLD/'prepared-input.json').read_text());anchor_map=json.loads((AUDIT/'attachment-anchor-map.json').read_text())
    layers=[Layer(p) for p in model['patterns'][:2]];N=len(bones);a=np.tile(np.eye(3),(N,1,1));b=np.zeros((N,3))
    body,f,bodyparts=body_arrays(model,a,b);report=dict(scope='Source-only residual study; not Chaos/native/cinematic acceptance',
        support='Top boundary ring only, single original chest rigid transform. No rest dimensional change; graph geodesic tethers rebuilt to this support. Free original bone weights retained; no lower animation drive or original zero-radius multi-bone upper clamps.',
        acceptance=False,stages=[],requested=[['walk',.295833],['walk',1.166667],['tend',5.]],native=False)
    try:
        init=contacts(layers,body,f,bodyparts,True);report['initialization']=init
        if any(x.get('insideBody',0) or x.get('minimumBodyDistanceCm',1)<=1e-8 or x.get('minimumUnsignedVertexTriangleDistanceCm',1)<=1e-8 for x in init):
            report['stop']='Rest initialization penetrates or touches; no time integration or below-foot projection permitted'
        else:
            # Target01 first. A bounded continuous affines path from exact source
            # rest to the early pose is a diagnostic preparation path, NOT walk.
            clip=P.M.CLIPS[0];rig=P.M.Rig(clip[1],clip[2]);ta,tb=P.M.joint_affines(rig,rig.pose(.295833),bones)
            curves=[Slerp([0,1],Rotation.from_matrix(np.stack((np.eye(3),R)))) for R in ta]
            for step in range(1,25):
                alpha=step/24;a=np.array([s(alpha).as_matrix() for s in curves]);b=tb*alpha
                body,f,bodyparts=body_arrays(model,a,b)
                support=[c.support(a,b,index) for c in layers]
                if max(support)>1e-8:raise AssertionError('Rigid support distance contradiction')
                for iteration in range(args.iterations):
                    if time.monotonic()-started>args.seconds:raise TimeoutError('Total source-study deadline')
                    for c in layers:c.material_project();body_contact(c,body,f,bodyparts)
                    layer_contact(*layers)
                    for c in layers:c.x[c.pin]=c.control[c.pin]
                    residual=[c.residual() for c in layers]
                    if all(r['edgeAbsCm']<=TOL and r['areaRelative']<=1e-4 and r['tetherExcessCm']<=TOL for r in residual):break
                contact=contacts(layers,body,f,bodyparts,True)
                passed=all(r['edgeAbsCm']<=TOL and r['areaRelative']<=1e-4 and r['tetherExcessCm']<=TOL for r in residual) and all(
                    x.get('insideBody',0)==0 and x.get('bodyGapDeficitCm',0)<=TOL and x.get('gapDeficitCm',0)<=TOL for x in contact)
                report['stages'].append(dict(restToPoseFraction=alpha,iterations=iteration+1,supportPairErrorCm=support,residual=residual,contact=contact,passed=passed))
                print('stage',step,'passed',passed,'edge',[round(r['maxEdgeStretch'],6) for r in residual],flush=True)
                if not passed:
                    report['stop']='Joint residual convergence failed at bounded stage; not global infeasibility, no next pose/unchecked contact overwrite accepted';break
            else:report['stop']='First preparation path passed point/residual gates; full triangle CCD/self/dense gates still mandatory; no later pose accepted'
        ornaments,rows=ornament_transport(by,layers[0],anchor_map,index)
        report['ornamentTransport']=dict(count=len(rows),bells=72,pomegranates=72,maxAttachmentErrorCm=max(x['attachmentErrorCm'] for x in rows),maxRigidError=max(x['rigidError'] for x in rows),sourceMapSha256=sha(AUDIT/'attachment-anchor-map.json'))
        report['ornamentContacts']=[]
        for name,(v,ff) in ornaments.items():
            _,_,_,dist=exhaustive(v,body,f);inside=inside_body(v,bodyparts)
            report['ornamentContacts'].append(dict(part=name,insideBodyVertices=int(inside.sum()),minimumBodyDistanceCm=float(dist.min()),
                status='Point check only; ornament triangle/layer contacts must additionally pass before any acceptance'))
        np.savez(out/'failed-or-diagnostic-state.npz',outer=layers[0].x,inner=layers[1].x,
            outerMatchedControl=layers[0].control,innerMatchedControl=layers[1].control,
            **{k:v[0] for k,v in ornaments.items()})
        atomic(out/'ornament-anchor-readback.json',rows)
    except Exception as e:report['stop']=type(e).__name__+': '+str(e);report['acceptance']=False
    finally:
        report['elapsedSeconds']=time.monotonic()-started
        report['protectedUnchanged']=all(sha(Path(p))==h for p,h in protected.items());assert report['protectedUnchanged']
        report['protectedFiles']=len(protected)
        report['unproved']=['Full dense conjunction/self triangle collision and CCD','Full walk/tend motion, not interpolated rest preparation path','Ornament/layer triangle and inter-ornament clearance/hanging plausibility','Native rendered appearance and cloth simulation']
        atomic(out/'receipt.json',report);atomic(out/'protected-hashes.json',protected)
        print(json.dumps(dict(receipt=str(out/'receipt.json'),stop=report.get('stop'),seconds=report['elapsedSeconds'])))
if __name__=='__main__':main()

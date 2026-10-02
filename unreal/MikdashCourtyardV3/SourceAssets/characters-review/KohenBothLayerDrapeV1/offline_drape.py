"""Bounded NumPy PBD reference, NOT UE Chaos or collision acceptance.

One authored configuration, both layers present. Three fixed posed equilibrations;
no claim of walk/tend time integration. Exact source checker evaluates final meshes.
"""
import sys
sys.dont_write_bytecode=True
import argparse,json,math,time
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from prepare import HERE,ROOT,atomic,sha,source_parts,read_glb,read_accessor,author,P
from study_kohen_hem_diagnose import metrics
from render_face_v5 import render

def edges(f):return np.unique(np.sort(np.concatenate((f[:,[0,1]],f[:,[1,2]],f[:,[2,0]])),axis=1),axis=0)
def normals(v,f):
    n=np.zeros_like(v);fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    for k in range(3):np.add.at(n,f[:,k],fn)
    return n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
def basis(t):
    x=t[:,1]-t[:,0];x/=np.maximum(np.linalg.norm(x,axis=1,keepdims=True),1e-12)
    z=np.cross(x,t[:,2]-t[:,0]);z/=np.maximum(np.linalg.norm(z,axis=1,keepdims=True),1e-12)
    y=np.cross(z,x);return np.stack((x,y,z),axis=2)
def nearest(points,v,f,k=8):
    """Exact closest point on k nearest CENTROIDS. Search is approximate, not certificate."""
    t=v[f];_,ids=cKDTree(t.mean(axis=1)).query(points,k=min(k,len(f)))
    if ids.ndim==1:ids=ids[:,None]
    tri=t[ids];a=tri[:,:,0];ab=tri[:,:,1]-a;ac=tri[:,:,2]-a;ap=points[:,None]-a
    aa=np.sum(ab*ab,axis=2);bb=np.sum(ab*ac,axis=2);cc=np.sum(ac*ac,axis=2);dd=np.sum(ap*ab,axis=2);ee=np.sum(ap*ac,axis=2)
    den=np.maximum(aa*cc-bb*bb,1e-20);u=(dd*cc-ee*bb)/den;w=(ee*aa-dd*bb)/den
    bary=np.stack((1-u-w,u,w),axis=2);q=a+u[:,:,None]*ab+w[:,:,None]*ac
    dst=np.sum((points[:,None]-q)**2,axis=2);dst[np.any(bary<0,axis=2)]=np.inf
    for i,j in ((0,1),(1,2),(2,0)):
        start=tri[:,:,i];dv=tri[:,:,j]-start;s=np.clip(np.sum((points[:,None]-start)*dv,axis=2)/np.maximum(np.sum(dv*dv,axis=2),1e-20),0,1)
        pt=start+s[:,:,None]*dv;distance=np.sum((points[:,None]-pt)**2,axis=2);take=distance<dst
        by=np.zeros_like(bary);by[:,:,i]=1-s;by[:,:,j]=s;bary[take]=by[take];q[take]=pt[take];dst[take]=distance[take]
    best=dst.argmin(axis=1);row=np.arange(len(points));fid=ids[row,best]
    return fid,bary[row,best],q[row,best],np.sqrt(dst[row,best])
def mapping(points,rest,faces):
    ids,weights,q,_=nearest(points,rest,faces,16);b=basis(rest[faces[ids]])
    residual=np.einsum('nji,nj->ni',b,points-q)
    return faces[ids],weights,residual
def deform(mp,v):
    ids,w,res=mp;t=v[ids];return np.einsum('ni,nij->nj',w,t)+np.einsum('nij,nj->ni',basis(t),res)
def color_edges(e):
    groups=[];used=[]
    for a,b in e:
        for i,s in enumerate(used):
            if int(a) not in s and int(b) not in s:break
        else:i=len(groups);groups.append([]);used.append(set())
        groups[i].append((a,b));used[i].update((int(a),int(b)))
    return [np.asarray(g,dtype=int) for g in groups]
def pattern_arrays(p):
    v=np.asarray(p['verticesCm'],float);j=np.zeros((len(v),4),int);w=np.zeros((len(v),4))
    for i,inf in enumerate(p['boneInfluences']):
        assert len(inf)<=4
        for k,(a,b) in enumerate(inf):j[i,k]=a;w[i,k]=b
    return v,j,w

class Cloth:
    def __init__(self,p):
        self.p=p;self.rest,self.j,self.w=pattern_arrays(p);self.f=np.asarray(p['faces'],int);self.e=edges(self.f)
        self.pin=np.asarray(p['maxDistanceCm'])==0;self.radius=np.asarray(p['maxDistanceCm'])
        area=np.linalg.norm(np.cross(self.rest[self.f[:,1]]-self.rest[self.f[:,0]],self.rest[self.f[:,2]]-self.rest[self.f[:,0]]),axis=1)*.5
        mass=np.zeros(len(self.rest))
        for k in range(3):np.add.at(mass,self.f[:,k],area*.35/30000.)
        self.mass=np.maximum(mass,.0001);self.inv=1/self.mass;self.inv[self.pin]=0
        adjacent={}
        for face in self.f:
            for a,b,c in ((face[0],face[1],face[2]),(face[1],face[2],face[0]),(face[2],face[0],face[1])):adjacent.setdefault(tuple(sorted((a,b))),[]).append(c)
        bend=np.asarray([v for v in adjacent.values() if len(v)==2],int)
        self.constraints=[]
        for es,stiffness in ((self.e,1.),(bend,.1)):
            for group in color_edges(es):self.constraints.append((group,np.linalg.norm(self.rest[group[:,0]]-self.rest[group[:,1]],axis=1),stiffness))
        lengths=np.linalg.norm(self.rest[self.e[:,0]]-self.rest[self.e[:,1]],axis=1)
        graph=coo_matrix((np.r_[lengths,lengths],(np.r_[self.e[:,0],self.e[:,1]],np.r_[self.e[:,1],self.e[:,0]])),shape=(len(self.rest),)*2).tocsr()
        fixed=np.flatnonzero(self.pin);dist=dijkstra(graph,directed=False,indices=fixed);which=dist.argmin(axis=0);self.anchor=fixed[which];self.tether=dist[which,np.arange(len(self.rest))]
        assert np.isfinite(self.tether).all() and np.all(self.pin[self.anchor])
        self.adjacent=set(tuple(x) for x in self.e);self.restEdges=lengths
    def set_pose(self,a,b):
        self.control=P.M.skin(self.rest,self.j,self.w,a,b);self.x=self.control.copy();self.vel=np.zeros_like(self.x)
    def project(self):
        for e,length,stiffness in self.constraints:
            i,j=e.T;dv=self.x[j]-self.x[i];n=np.maximum(np.linalg.norm(dv,axis=1),1e-10);den=self.inv[i]+self.inv[j]
            lam=np.divide((n-length)*stiffness,den,out=np.zeros_like(n),where=den>0);delta=dv*(lam/n)[:,None]
            self.x[i]+=self.inv[i,None]*delta;self.x[j]-=self.inv[j,None]*delta
        dv=self.x-self.x[self.anchor];dist=np.maximum(np.linalg.norm(dv,axis=1),1e-12)
        self.x-=dv*(np.maximum(0,dist-self.tether)/dist)[:,None]
        dv=self.x-self.control;dist=np.maximum(np.linalg.norm(dv,axis=1),1e-12)
        self.x-=dv*(np.maximum(0,dist-self.radius)/dist)[:,None]
        self.x[self.pin]=self.control[self.pin]
    def self_contact(self):
        pairs=cKDTree(self.x).query_pairs(.5,output_type='ndarray')
        if not len(pairs):return 0
        pairs=np.asarray([p for p in pairs if tuple(p) not in self.adjacent and np.linalg.norm(self.rest[p[0]]-self.rest[p[1]])>1.],int).reshape(-1,2)
        if not len(pairs):return 0
        i,j=pairs.T;dv=self.x[j]-self.x[i];dist=np.maximum(np.linalg.norm(dv,axis=1),1e-9);den=self.inv[i]+self.inv[j]
        lam=np.divide(.5-dist,den,out=np.zeros_like(dist),where=den>0);delta=dv*(lam/dist)[:,None]
        np.add.at(self.x,i,-self.inv[i,None]*delta);np.add.at(self.x,j,self.inv[j,None]*delta)
        return len(pairs)

def contact_outer(outer,inner):
    ids,bary,q,dist=nearest(outer.x,inner.x,inner.f);tri=inner.f[ids]
    n=np.einsum('ni,nij->nj',bary,normals(inner.x,inner.f)[tri]);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    # Authored outward winding verified against radial vectors in tests.
    signed=np.sum((outer.x-q)*n,axis=1);depth=np.maximum(0,.5-signed)
    den=outer.inv+np.sum(inner.inv[tri]*bary*bary,axis=1)
    lam=np.divide(depth,den,out=np.zeros_like(depth),where=den>0)
    outer.x+=outer.inv[:,None]*lam[:,None]*n
    delta=-inner.inv[tri,None]*bary[:,:,None]*lam[:,None,None]*n[:,None]
    for k in range(3):np.add.at(inner.x,tri[:,k],delta[:,k])
    return int(np.count_nonzero(depth>0))
def contact_body(c,body,faces):
    ids,w,q,dist=nearest(c.x,body,faces);t=body[faces[ids]];n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    signed=np.sum((c.x-q)*n,axis=1)
    # Only nearby exact source body triangles; broadphase search is not exhaustive.
    depth=np.where((dist<12)&(~c.pin),np.maximum(0,.5-signed),0)
    c.x+=depth[:,None]*n
    # Author ground plane is z=0; no lowered floor or clipped vertices.
    c.x[~c.pin,2]=np.maximum(c.x[~c.pin,2],.5)
    return int(np.count_nonzero(depth))

def solve(layers,body,faces,steps=180):
    start=time.monotonic();contacts=0
    for step in range(steps):
        if time.monotonic()-start>120:raise TimeoutError('120s per posed solve')
        previous=[c.x.copy() for c in layers]
        for c in layers:c.vel[:,2]-=980.665/120;c.x+=c.vel/120
        for it in range(10):
            for c in layers:c.project()
            if it%2==1:
                for c in layers:contacts+=contact_body(c,body,faces)+c.self_contact()
                contacts+=contact_outer(layers[0],layers[1])
                for c in layers:c.x[c.pin]=c.control[c.pin]
        for c,prev in zip(layers,previous):c.vel=(c.x-prev)*120*.94
        if step%60==59:print('settle',step+1,'seconds',round(time.monotonic()-start,2),flush=True)
    return dict(steps=steps,dtSeconds=1/120,iterations=10,seconds=time.monotonic()-start,contactsProjected=contacts)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();out=HERE/args.out
    out.mkdir(exist_ok=False)
    model=json.loads((HERE/'prepared-input.json').read_bytes());bones,index,parts,influence,*_=source_parts();by={p['name']:p for p in parts}
    doc,blob=read_glb(HERE/'SourcePartitionOnly.glb');base=[]
    for primitive in doc['meshes'][0]['primitives']:
        a=primitive['attributes'];v=np.array([author(x) for x in read_accessor(doc,blob,a['POSITION'])]);ids=read_accessor(doc,blob,primitive['indices'])
        base.append(dict(material=doc['materials'][primitive['material']]['name'],rest=v,j=np.asarray(read_accessor(doc,blob,a['JOINTS_0']),int),w=np.asarray(read_accessor(doc,blob,a['WEIGHTS_0'])),colours=read_accessor(doc,blob,a['COLOR_0']),faces=np.asarray(ids,int).reshape(-1,3)))
    render_maps={};probe_maps={};layers=[Cloth(p) for p in model['patterns'][:2]]
    for c,material in zip(layers,('KG_Meil','KG_Ketonet')):
        render_maps[material]=mapping(next(p['rest'] for p in base if p['material']==material),c.rest,c.f)
        probe_maps[c.p['name']]=mapping(np.asarray(by[c.p['name']]['vertices']),c.rest,c.f)
    rows=[]
    for clipname,t in [('walk',.295833),('walk',1.166667),('tend',5.)]:
        clip=next(c for c in P.M.CLIPS if c[0]==clipname);rig=P.M.Rig(clip[1],clip[2]);a,b=P.M.joint_affines(rig,rig.pose(t),bones)
        for c in layers:c.set_pose(a,b)
        body=[];bf=[]
        for p in model['patterns'][2:]:
            v,j,w=pattern_arrays(p);bf.extend(np.asarray(p['faces'])+sum(len(x) for x in body));body.append(P.M.skin(v,j,w,a,b))
        body=np.concatenate(body);bf=np.asarray(bf,int)
        timing=solve(layers,body,bf)
        name=clipname+'-'+str(round(t*1e6));np.savez(out/(name+'.npz'),outer=layers[0].x,inner=layers[1].x,outerControl=layers[0].control,innerControl=layers[1].control)
        for mode in ('original','matched','offline-pbd'):
            meshes=[]
            for p in base:
                v=P.M.skin(p['rest'],p['j'],p['w'],a,b)
                if mode!='original' and p['material'] in render_maps:
                    c=layers[0 if p['material']=='KG_Meil' else 1];v=deform(render_maps[p['material']],c.x if mode=='offline-pbd' else c.control)
                meshes.append(dict(material='KG_Linen' if p['material']=='KG_Ketonet' else p['material'],vertices=v.tolist(),normals=normals(v,p['faces']).tolist(),faces=p['faces'].tolist(),colours=p['colours']))
            for view,yaw in [('front',0),('side',math.pi/2)]:
                output=out/(name+'-'+mode+'-'+view+'.png');render(meshes,output,dist_m=2.1,yaw=yaw,target=(0,0,90),width=420,height=630,ss=1)
                print('render',output.name,flush=True)
        for c in layers:
            dense=deform(probe_maps[c.p['name']],c.x);rest=c.rest
            stretch=np.linalg.norm(c.x[c.e[:,1]]-c.x[c.e[:,0]],axis=1)/c.restEdges
            v,j,w=P.M.skin_arrays(by[c.p['name']],influence,index);original=P.M.skin(v,j,w,a,b)
            rows.append(dict(clip=clipname,time=t,layer=c.p['name'],originalHem=metrics(original[:176]),offlineHem=metrics(dense[:176]),maxEdgeStretch=float(stretch.max()),minEdgeRatio=float(stretch.min()),maxPinErrorCm=float(np.linalg.norm(c.x[c.pin]-c.control[c.pin],axis=1).max()),maxRestReconstructionCm=float(np.linalg.norm(deform(probe_maps[c.p['name']],rest)-v,axis=1).max()),timing=timing))
        atomic(out/(name+'-metrics.json'),rows[-2:])
    atomic(out/'results.json',dict(scope='NumPy fixed-pose PBD diagnostic, NOT UE Chaos, NOT continuous motion, NOT clearance acceptance',rows=rows,configuration=dict(gravityCmS2=-980.665,densityKgM2=.35,minMassKg=.0001,edgeStiffness=1,bendOppositeVertexStiffness=.1,selfVertexRadiusCm=.5,layerTriangleGapCm=.5,bodyTriangleGapCm=.5,bodySearchTriangles=8),limitations=['Approximate centroid-neighbour triangle collision broadphase; not continuous collision detection.','Same-layer vertex repulsion is not triangle self-intersection proof.','Native Chaos uses bending elements and triangle self collision; this reference uses distance bending and vertex self contacts. No solver parity claimed.','Ephod, collar, bells and remaining ornaments retain original rig; not hidden or deleted.','Existing source conjunction checker and gradient/strain assessment remain acceptance gates. Full986 samples NOT RUN.'],sourceSha256=sha(HERE/'SourcePartitionOnly.glb'),candidateExported=False))
if __name__=='__main__':main()

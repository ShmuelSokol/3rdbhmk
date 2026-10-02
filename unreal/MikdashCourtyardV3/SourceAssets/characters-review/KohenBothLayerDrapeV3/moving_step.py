"""One local cloth patch / actual moving FootL face implicit contact step.

Not a whole-garment simulator. Actual walk71/240 ->72/240, physical gravity,
lumped area mass, elastic rest-edge and dihedral energy, symmetric finite-triangle
sample contacts. No redundant exact edge+area equalities. All parameters assumed.
Local patch is freshly initialized at source feature; not claimed settled/history.
"""
import sys
sys.dont_write_bytecode=True
import time,json,argparse
import numpy as np
from scipy.optimize import minimize
import inputs as I
from mapped_contact import mapped_vertex,point_triangle_distance_gap,hinge_angle
from test_witness import fd

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--frame',type=int,default=71);ap.add_argument('--out',required=True);args=ap.parse_args()
    assert 0<=args.frame<=71 and args.out.isidentifier()
    assert not (I.HERE/(args.out+'.json')).exists() and not (I.HERE/(args.out+'.npz')).exists()
    model,bones,index,by,c,rest,faces,mp,rig=I.load()
    t0=args.frame/240;t1=(args.frame+1)/240;h=t1-t0;gap=.5
    a0,b0=I.pose(rig,bones,t0);a1,b1=I.pose(rig,bones,t1)
    bv0,bf,_=I.s.body_arrays(model,a0,b0);bv1,_,_=I.s.body_arrays(model,a1,b1)
    foot0=bv0[bf[2039]];foot1=bv1[bf[2039]]
    denseids=faces[3938];coarseSeed=np.unique(mp[0][denseids])
    # Small patch: mapped triangles plus their edge-neighbours, no global solver.
    selected=c.f[np.sum(np.isin(c.f,coarseSeed),axis=1)>=2]
    ids=np.unique(selected);remap={int(v):i for i,v in enumerate(ids)}
    pf=np.array([[remap[int(v)] for v in f] for f in selected]);ref=c.rest[ids]
    maps=[(np.array([remap[int(v)] for v in mp[0][d]]),mp[1][d],mp[2][d]) for d in denseids]
    edges=I.s.edges(pf);L=np.linalg.norm(ref[edges[:,1]]-ref[edges[:,0]],axis=1)
    area=np.linalg.norm(np.cross(ref[pf[:,1]]-ref[pf[:,0]],ref[pf[:,2]]-ref[pf[:,0]]),axis=1)*.5
    mass=np.zeros(len(ids))
    for k in range(3):np.add.at(mass,pf[:,k],area*.35/30000.)
    assert np.all(mass>0)
    adjacent={}
    for f in pf:
        for i,j,k in ((f[0],f[1],f[2]),(f[1],f[2],f[0]),(f[2],f[0],f[1])):
            adjacent.setdefault(tuple(sorted((i,j))),[]).append(k)
    hinges=np.array([[i,j,*op] for (i,j),op in adjacent.items() if len(op)==2],int)
    restAngles=np.array([hinge_angle(ref[q])[0] for q in hinges])
    def dense(x):return np.array([mapped_vertex(x[m[0]],m[1],m[2])[0] for m in maps])
    def contact(x,foot):
        d=dense(x);values=[];grads=[]
        # Dense-face centroid against body triangle, body centroid against dense
        # face: both finite triangles, includes rotating offsets on every corner.
        val,g,_=point_triangle_distance_gap(d.mean(0),foot,gap)
        grad=np.zeros_like(x)
        for m in maps:
            _,J=mapped_vertex(x[m[0]],m[1],m[2]);np.add.at(grad,m[0],((g[:3]/3)@J).reshape(3,3))
        values.append(val);grads.append(grad.ravel())
        val,g,_=point_triangle_distance_gap(foot.mean(0),d,gap);grad=np.zeros_like(x)
        for m,gg in zip(maps,g[3:].reshape(3,3)):
            _,J=mapped_vertex(x[m[0]],m[1],m[2]);np.add.at(grad,m[0],(gg@J).reshape(3,3))
        values.append(val);grads.append(grad.ravel())
        return np.array(values),np.array(grads)
    x0=ref@a0[index['chest']].T+b0[index['chest']]
    n=np.cross(foot0[1]-foot0[0],foot0[2]-foot0[0]);n/=np.linalg.norm(n)
    # Exact shape-preserving LOCAL initialization at the measured feature. Does
    # not solve/globalize the full garment or invent a settled prior velocity.
    x0+=foot0.mean(0)-dense(x0).mean(0)
    base=x0.copy();lo=0.;hi=2.
    if np.min(contact(base+n*hi,foot0)[0])<0:raise RuntimeError('Local exterior initialization not bracketed')
    for _ in range(50):
        mid=(lo+hi)/2
        if np.min(contact(base+n*mid,foot0)[0])<0:lo=mid
        else:hi=mid
    x0=base+n*(hi+1e-7);v0=np.zeros_like(x0);gravity=np.array([0.,0.,-980.665]);y=x0+h*v0+h*h*gravity
    kEdge=20.;kBend=.05 # kg/s^2; kg*cm^2/s^2 per rad^2. Assumptions, not fitted.
    start=time.monotonic();deadline=start+20
    def energy(z):
        if time.monotonic()>deadline:raise TimeoutError('20-second local step budget')
        x=z.reshape(-1,3);delta=x-y;E=.5*np.sum(mass[:,None]*delta*delta)/(h*h);g=mass[:,None]*delta/(h*h)
        i,j=edges.T;dv=x[j]-x[i];ell=np.linalg.norm(dv,axis=1);r=ell-L
        E+=.5*kEdge*np.sum(r*r);d=kEdge*r[:,None]*dv/ell[:,None]
        np.add.at(g,i,-d);np.add.at(g,j,d)
        for q,theta0 in zip(hinges,restAngles):
            theta,J=hinge_angle(x[q]);r=np.arctan2(np.sin(theta-theta0),np.cos(theta-theta0))
            E+=.5*kBend*r*r;np.add.at(g,q,(kBend*r*J).reshape(4,3))
        return E,g.ravel()
    # Independently validate actual-step energy/contact derivatives before solve.
    _,eg=energy(x0.ravel());en=fd(lambda z:energy(z.ravel())[0],x0).ravel()
    cv,cg=contact(x0,foot1);cn=fd(lambda z:contact(z,foot1)[0],x0)
    derivativeErrors=dict(energy=float(np.max(np.abs(eg-en))),contact=float(np.max(np.abs(cg-cn))))
    assert max(derivativeErrors.values())<1e-6
    result=minimize(energy,y.ravel(),jac=True,method='SLSQP',constraints=[dict(type='ineq',
        fun=lambda z:contact(z.reshape(-1,3),foot1)[0],jac=lambda z:contact(z.reshape(-1,3),foot1)[1])],
        options=dict(maxiter=60,ftol=1e-12))
    x=result.x.reshape(-1,3);values,J=contact(x,foot1);E,grad=energy(result.x)
    # Complementarity/stationarity readback for the local constrained problem.
    active=np.flatnonzero(values<1e-6)
    from scipy.optimize import nnls
    lam=np.zeros(len(values))
    if len(active):lam[active]=nnls(J[active].T,grad)[0]
    stationarity=float(np.max(np.abs(grad-J.T@lam)))
    ratios=np.linalg.norm(x[edges[:,1]]-x[edges[:,0]],axis=1)/L
    # Sampled side checks, explicitly NOT a CCD certificate.
    side=[]
    for alpha in (0.,.25,.5,.75,1.):
        foot=(1-alpha)*foot0+alpha*foot1;point=dense((1-alpha)*x0+alpha*x).mean(0)
        normal=np.cross(foot[1]-foot[0],foot[2]-foot[0]);normal/=np.linalg.norm(normal)
        side.append(float(normal@(point-foot.mean(0))))
    receipt=dict(status='LOCAL_STEP_ONLY_NATIVE_AND_GARMENT_HOLD',optimizerSuccess=bool(result.success),message=str(result.message),
        t0Seconds=t0,t1Seconds=t1,stepSeconds=h,sourceRateHz=240,restFractionUsed=False,
        patch=dict(coarseVertices=ids.tolist(),triangles=len(pf),hinges=len(hinges),denseKetonetTriangle=3938,FootLTriangle=231),
        assumptions=dict(densityKgM2=.35,edgeStiffnessKgPerS2=kEdge,bendingEnergyKgCm2PerS2PerRad2=kBend,
            initialVelocity='zero; local test assumption, NOT settled full-clip history',gravityCmS2=gravity.tolist(),
            initialization='rigidly translated rest patch at actual t0 FootL feature; only two local finite-triangle sample constraints certified'),
        restEdgeInitialMaxErrorCm=float(np.max(np.abs(np.linalg.norm(x0[edges[:,1]]-x0[edges[:,0]],axis=1)-L))),
        footMaxVertexMotionCm=float(np.linalg.norm(foot1-foot0,axis=1).max()),freeGravityDisplacementCm=(h*h*gravity).tolist(),
        contactGapMinusMarginBefore=contact(x0,foot0)[0].tolist(),gravityPredictorGaps=contact(y,foot1)[0].tolist(),
        contactGapMinusMarginAfter=values.tolist(),activeContacts=len(active),multipliers=lam.tolist(),
        stationarityMaxKgCmPerS2=stationarity,complementarityMax=float(np.max(np.abs(lam*values))),
        derivativeErrors=derivativeErrors,maxEdgeStretch=float(ratios.max()),minEdgeRatio=float(ratios.min()),
        denseGradients=I.s.gradients(dense(x0),dense(x),np.array([[0,1,2]])),
        maxMovementCm=float(np.linalg.norm(x-x0,axis=1).max()),sampledExteriorSignsCm=side,
        iterations=int(result.nit),elapsedSeconds=time.monotonic()-start,V2FilesPreserved=I.preserved(),native=False,
        garmentAcceptance=False,limits=['Local sample contacts only, no full triangle CCD/self/layer/ornament proof',
            'Actual body timestamps, but initialized free patch is not a continued drape trajectory',
            'Elastic/bending assumptions are not calibrated Chaos parameters or a new strain acceptance threshold'])
    np.savez(I.HERE/(args.out+'.npz'),coarseIds=ids,initial=x0,final=x,velocity=(x-x0)/h,foot0=foot0,foot1=foot1)
    I.write(args.out+'.json',receipt);print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()

"""Finite-difference validation at the measured V2 FootL/dense Ketonet witness."""
import sys
sys.dont_write_bytecode=True
import numpy as np
import inputs as I
from mapped_contact import mapped_vertex,vertex_face,edge_edge_feature,pullback

def fd(fn,x,h=1e-5):
    y=np.asarray(fn(x));out=np.zeros((y.size,x.size))
    for k in range(x.size):
        plus=x.copy();minus=x.copy();plus.flat[k]+=h;minus.flat[k]-=h
        out[:,k]=(np.asarray(fn(plus)).ravel()-np.asarray(fn(minus)).ravel())/(2*h)
    return out

def main():
    model,bones,index,by,c,rest,faces,mp,rig=I.load()
    old=np.load(I.V2/'Probe03/failed-or-diagnostic-state.npz');x=old['inner']
    ta,tb=I.pose(rig,bones,.295833);fraction=.875
    a=np.array([I.s.Slerp([0,1],I.s.Rotation.from_matrix(np.stack((np.eye(3),R))))(fraction).as_matrix() for R in ta]);b=tb*fraction
    bv,bf,_=I.s.body_arrays(model,a,b);body=bv[bf[2039]]
    ids=faces[3938];maps=[(mp[0][j],mp[1][j],mp[2][j]) for j in ids]
    dense=np.array([mapped_vertex(x[m[0]],m[1],m[2])[0] for m in maps]);rows=[]
    for j,m in zip(ids,maps):
        q,J=mapped_vertex(x[m[0]],m[1],m[2]);numeric=fd(lambda v:mapped_vertex(v,m[1],m[2])[0],x[m[0]])
        baryOnly=np.concatenate([np.eye(3)*w for w in m[1]],axis=1)
        rows.append(dict(test='mapped-position',denseVertex=int(j),maxDerivativeError=float(np.max(np.abs(J-numeric))),
            omittedOffsetDerivativeError=float(np.max(np.abs(baryOnly-numeric))),offsetCm=m[2].tolist()))
    # Both contact directions: dense cloth vertex/body face and prescribed body
    # vertex/dense cloth face. The latter differentiates the cloth normal.
    for direction in ('cloth-vertex/body-face','body-vertex/cloth-face'):
        geom=np.vstack((dense[0],body)) if direction.startswith('cloth') else np.vstack((body[0],dense))
        sign=1 if direction.startswith('cloth') else -1
        value,g=vertex_face(geom[0],geom[1:],sign)
        numeric=fd(lambda v:vertex_face(v[0],v[1:],sign)[0],geom).ravel()
        mappings=[maps[0],None,None,None] if sign==1 else [None,*maps]
        analytic=pullback(g,mappings,x)
        active=np.unique(np.concatenate([m[0] for m in mappings if m is not None]))
        def composed(local):
            xx=x.copy();xx[active]=local
            dd=np.array([mapped_vertex(xx[m[0]],m[1],m[2])[0] for m in maps])
            return vertex_face(dd[0],body,1)[0] if sign==1 else vertex_face(body[0],dd,-1)[0]
        numericPull=fd(composed,x[active]).ravel()
        rows.append(dict(test=direction,maxDerivativeError=float(np.max(np.abs(g-numeric))),
            maxPullbackError=float(np.max(np.abs(analytic[active].ravel()-numericPull))),signedGapCm=float(value)))
    normal=np.cross(body[1]-body[0],body[2]-body[0]);geo=np.vstack((dense[:2],body[:2]))
    value,g=edge_edge_feature(geo[:2],geo[2:],.4,.6,normal)
    numeric=fd(lambda v:edge_edge_feature(v[:2],v[2:],.4,.6,normal)[0],geo).ravel()
    analytic=pullback(g,[maps[0],maps[1],None,None],x);active=np.unique(np.r_[maps[0][0],maps[1][0]])
    def edge_composed(local):
        xx=x.copy();xx[active]=local
        dd=np.array([mapped_vertex(xx[m[0]],m[1],m[2])[0] for m in maps[:2]])
        return edge_edge_feature(dd,body[:2],.4,.6,normal)[0]
    numericPull=fd(edge_composed,x[active]).ravel()
    rows.append(dict(test='symmetric-edge-edge-frozen-history-feature',maxDerivativeError=float(np.max(np.abs(g-numeric))),
        maxPullbackError=float(np.max(np.abs(analytic[active].ravel()-numericPull)))))
    # Translation covariance catches a wrong offset derivative sign/column order.
    for m in maps:
        _,J=mapped_vertex(x[m[0]],m[1],m[2]);assert np.max(np.abs(J[:,:3]+J[:,3:6]+J[:,6:]-np.eye(3)))<1e-10
    # Degenerate geometry must refuse, not divide by a numerical floor and claim proof.
    try:mapped_vertex(np.zeros((3,3)),np.ones(3)/3,np.zeros(3))
    except ValueError:pass
    else:raise AssertionError('Degenerate mapping accepted')
    passed=all(r['maxDerivativeError']<1e-7 and r.get('maxPullbackError',0)<1e-7 for r in rows)
    I.write('jacobian-tests01.json',dict(passed=passed,rows=rows,finiteDifferenceStepCm=1e-5,tolerance=1e-7,
        witness=dict(denseKetonetTriangle=3938,bodyGlobalTriangle=2039,bodyPart='FootL',bodyLocalTriangle=231,
            source='V2 failed .875 rest-to-pose endpoint; NOT a physical time sample'),
        covariancePassed=True,degenerateRefused=True,V2FilesPreserved=I.preserved(),native=False,
        limits=['Local fixed-feature Jacobians, not contact detection/CCD','No cloth acceptance or elastic parameter calibration']))
    print('Jacobian tests passed:',passed,'worst:',max(max(r['maxDerivativeError'],r.get('maxPullbackError',0)) for r in rows))
    assert passed

if __name__=='__main__':main()

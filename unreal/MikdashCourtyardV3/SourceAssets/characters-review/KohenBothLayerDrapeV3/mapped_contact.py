"""Analytic dense mapping/contact derivatives, independent implementation.

No engine code. Rest mapping is the frozen V1 barycentric+rotating-offset map.
Contact feature discovery/CCD is NOT implemented by these differential operators.
"""
import numpy as np

def unit_jac(v):
    length=np.linalg.norm(v)
    if length<1e-10:raise ValueError('Degenerate mapping/contact frame')
    u=v/length
    return u,(np.eye(3)-np.outer(u,u))/length

def mapped_vertex(tri,weights,offset):
    """Return q and dq/d(triangle coordinates), shape3x9, including frame rotation."""
    dv=np.eye(9).reshape(3,3,9);e=tri[1]-tri[0];f=tri[2]-tri[0]
    x,Px=unit_jac(e);dx=Px@(dv[1]-dv[0])
    cross=np.cross(x,f);z,Pz=unit_jac(cross)
    dc=np.cross(dx.T,f).T+np.cross(x,(dv[2]-dv[0]).T).T;dz=Pz@dc
    y=np.cross(z,x);dy=np.cross(dz.T,x).T+np.cross(z,dx.T).T
    q=weights@tri+offset[0]*x+offset[1]*y+offset[2]*z
    J=np.einsum('i,ijk->jk',weights,dv)+offset[0]*dx+offset[1]*dy+offset[2]*dz
    return q,J

def vertex_face(point,tri,sign=1.,gap=.5):
    """Signed oriented feature gap and full derivative [point,a,b,c] (12).

    sign+1: cloth vertex outside outward body face. sign-1: body vertex inside
    outward cloth face. The latter differentiates the MOVING cloth normal too.
    Caller must establish feature domain, orientation and exterior history.
    This is not permission to apply infinite planes to unrelated points.
    """
    dv=np.eye(12).reshape(4,3,12);e=tri[1]-tri[0];f=tri[2]-tri[0]
    n,P=unit_jac(np.cross(e,f))
    de=dv[2]-dv[1];df=dv[3]-dv[1]
    dn=P@(np.cross(de.T,f).T+np.cross(e,df.T).T)
    r=point-tri[0]
    return sign*np.dot(n,r)-gap,sign*(n@(dv[0]-dv[1])+r@dn)

def edge_edge_feature(a,b,u,v,normal,gap=.5):
    """History-oriented material-point edge row and derivative [a0,a1,b0,b1].

    u/v and exterior normal are an explicitly FROZEN feature during a local
    solve. Includes both edges; not derivative of a reselected closest feature.
    Caller supplies history/CCD; no zero-distance nearest-normal invention.
    """
    if not (0<=u<=1 and 0<=v<=1):raise ValueError('Edge feature outside segment')
    n,_=unit_jac(normal);coeff=np.array([1-u,u,-(1-v),-v])
    points=np.concatenate((a,b));return float(n@(coeff@points)-gap),(coeff[:,None]*n).ravel()

def pullback(feature_gradient,mappings,coarse):
    """Assemble scalar derivative to shared coarse vertices, adding duplicates.

    mappings sequence entries are (triangleVertexIds, baryWeights, localOffset)
    for each feature point; None means externally prescribed (body) geometry.
    """
    output=np.zeros_like(coarse)
    for grad,mp in zip(np.asarray(feature_gradient).reshape(-1,3),mappings):
        if mp is None:continue
        ids,w,r=mp;_,J=mapped_vertex(coarse[ids],w,r)
        np.add.at(output,ids,(grad@J).reshape(3,3))
    return output

def point_triangle_distance_gap(point,tri,gap=.5):
    """Closest-feature distance derivative (envelope theorem), away from zero.

    Unsigned distance; caller must separately preserve the exterior side/history.
    Unlike a supporting plane, this operates on a finite triangle, including edges.
    """
    a,b,c=tri;e=b-a;f=c-a;rhs=point-a
    gram=np.array([[e@e,e@f],[e@f,f@f]])
    if np.linalg.det(gram)<1e-18:raise ValueError('Degenerate contact triangle')
    uv=np.linalg.solve(gram,np.array([rhs@e,rhs@f]));w=np.array([1-uv.sum(),*uv])
    choices=[]
    if np.all(w>=0):choices.append(w)
    for i,j in ((0,1),(1,2),(2,0)):
        d=tri[j]-tri[i];t=np.clip((point-tri[i])@d/(d@d),0,1);weight=np.zeros(3);weight[i]=1-t;weight[j]=t;choices.append(weight)
    w=min(choices,key=lambda z:np.sum((point-z@tri)**2));r=point-w@tri;dist=np.linalg.norm(r)
    if dist<1e-10:raise ValueError('Zero distance needs history/CCD; no invented normal')
    n=r/dist;return dist-gap,np.r_[n,(-w[:,None]*n).ravel()],w

def hinge_angle(q):
    """Signed dihedral plus analytic derivative for edge0-1/opposites2-3."""
    dv=np.eye(12).reshape(4,3,12);e=q[1]-q[0];de=dv[1]-dv[0]
    x,Px=unit_jac(e);dx=Px@de
    u=q[2]-q[0];du=dv[2]-dv[0];v=q[3]-q[0];ddv=dv[3]-dv[0]
    n,Pn=unit_jac(np.cross(e,u));dn=Pn@(np.cross(de.T,u).T+np.cross(e,du.T).T)
    m,Pm=unit_jac(np.cross(v,e));dm=Pm@(np.cross(ddv.T,e).T+np.cross(v,de.T).T)
    co=n@m;sn=x@np.cross(n,m)
    dc=m@dn+n@dm;ds=np.cross(n,m)@dx+x@(np.cross(dn.T,m).T+np.cross(n,dm.T).T)
    return np.arctan2(sn,co),(co*ds-sn*dc)/(co*co+sn*sn)

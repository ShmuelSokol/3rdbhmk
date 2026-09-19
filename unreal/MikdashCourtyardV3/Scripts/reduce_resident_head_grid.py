"""Index-only head-grid candidate; retained accepted-source attributes are copied by exporter."""
import hashlib
import numpy as np
import create_resident_v4 as R
import create_resident_v4_face as F

def reduce_head(part,variant,stride=2):
    assert stride==2 and part['name']=='Head'
    grid=F.head_grid(variant);rows,cols=grid['rows'],grid['cols']
    assert cols%stride==0
    original=F.head_mesh(grid)
    assert part['vertices']==original[0] and part['faces']==original[1]
    rr=sorted(set(range(0,rows,stride))|{rows-1})
    cc=list(range(0,cols,stride))
    mapping=[r*cols+c for r in rr for c in cc]+[rows*cols,rows*cols+1]
    faces=R.grid_faces(len(rr),len(cc),True)
    bot,top=len(rr)*len(cc),len(rr)*len(cc)+1
    for c in range(len(cc)):
        faces.extend(((bot,(c+1)%len(cc),c),(top,(len(rr)-1)*len(cc)+c,(len(rr)-1)*len(cc)+(c+1)%len(cc))))
    faces=np.asarray([[mapping[i] for i in f] for f in faces],dtype=np.int32)
    points=np.asarray(part['vertices']);tri=points[faces]
    if np.einsum('ij,ij->',tri[:,0],np.cross(tri[:,1],tri[:,2]))<0:faces=faces[:,[0,2,1]]
    tri=points[faces]
    assert np.min(np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1))>1e-10
    edges={}
    for a,b,c in faces.tolist():
        for x,y in ((a,b),(b,c),(c,a)):
            key=tuple(sorted((x,y)));edges.setdefault(key,[]).append((x,y))
    assert all(len(v)==2 and v[0]==v[1][::-1] for v in edges.values()),'Non-manifold or inconsistent head winding'
    assert len(mapping)-len(edges)+len(faces)==2,'Head sphere topology changed'
    result=dict(part);result['faces']=[tuple(f) for f in faces.tolist()]
    return result,dict(sourceTriangles=len(part['faces']),candidateTriangles=len(faces),sourceVertices=len(points),retainedVertices=len(mapping),rows=rr,columns=cc,closedManifold=True,eulerCharacteristic=2,sourceIndicesSha256=hashlib.sha256(faces.astype('<i4').tobytes()).hexdigest())

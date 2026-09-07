"""Independent stdlib validation of generated OBJ attributes and portal envelope."""
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    meshes=json.loads((ROOT/'opening-v2.mesh.json').read_text())['meshes']
    spec=json.loads((ROOT/'opening-v2-spec.json').read_text())
    seg=spec['walkingSegments']; errors=[]
    def require(ok,why):
        if not ok: errors.append(why)
    dz=[b['topZcm']-a['topZcm'] for a,b in zip(seg,seg[1:])]
    require(sum(t>1e-8 for t in dz)==82,'Riser count')
    require(all(abs(t-1432.5/82)<1e-8 or abs(t)<1e-8 for t in dz),'Unequal risers')
    require(all(abs(a['xEndCm']-b['xStartCm'])<1e-8 for a,b in zip(seg,seg[1:])),'Landing discontinuity')
    counts={}
    y=spec['crossingXYcm'][1]
    for mesh in meshes:
        vs,uvs,ns,fs=[],[],[],[]
        for line in (ROOT/(mesh['name']+'.obj')).read_text().splitlines():
            t=line.split()
            if not t: continue
            if t[0]=='v': vs.append(tuple(map(float,t[1:])))
            elif t[0]=='vt': uvs.append(tuple(map(float,t[1:])))
            elif t[0]=='vn': ns.append(tuple(map(float,t[1:])))
            elif t[0]=='f': fs.append([tuple(int(v)-1 for v in p.split('/')) for p in t[1:]])
        require(len(fs)==mesh['triangleCount'],'OBJ/JSON count mismatch')
        require(all(math.isfinite(v) for p in vs+uvs+ns for v in p),'Nonfinite attribute')
        require(all(abs(sum(v*v for v in n)-1)<1e-7 for n in ns),'Normal unit length')
        for face in fs:
            a,b,c=[vs[f[0]] for f in face]
            u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
            n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            require(sum(t*t for t in n)>1e-18,'Degenerate triangle')
            require(sum(n[i]*ns[face[0][2]][i] for i in range(3))>0,'Winding/normal mismatch')
            a,b,c=[uvs[f[1]] for f in face]
            require(abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-10,'Degenerate UV')
        require(all(max(abs(vs[i][j]-[p[0]/100,-p[1]/100,p[2]/100][j]) for j in range(3))<1e-8 for i,p in enumerate(mesh['verticesUEcm'])),'Coordinate conversion drift')
        if 'Portal' in mesh['name']:
            # Each source cuboid has12triangles/36vertices; independently check
            # no portal solid intersects the entire claimed300x320cm clear box.
            vv=mesh['verticesUEcm']
            for start in range(0,len(vv),36):
                group=vv[start:start+36]
                lo=[min(p[i] for p in group) for i in range(3)]
                hi=[max(p[i] for p in group) for i in range(3)]
                require(not (lo[1]<y+150-1e-8 and hi[1]>y-150+1e-8 and lo[2]<320-1e-8 and hi[2]>0+1e-8),'Portal clear envelope blocked')
        counts[mesh['name']]=len(fs)
    report={'status':'PASS' if not errors else 'FAIL','errors':errors,'triangles':counts,
            'checks':['82 equal risers/continuous landing endpoints','OBJ/JSON coordinate parity','UV/nondegenerate faces/explicit consistent normals','Full300x320cm portal opening envelope'],
            'nativeExecuted':False}
    (ROOT/'independent-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if errors: raise SystemExit(1)


if __name__=='__main__':main()

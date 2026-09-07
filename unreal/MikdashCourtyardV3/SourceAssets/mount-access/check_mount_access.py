"""Independent output validation; stdlib only. Does not run Unreal or regenerate."""
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def check():
    spec=json.loads((ROOT/'mount-access-spec.json').read_text())
    meshes=json.loads((ROOT/'mount-access.mesh.json').read_text())['meshes']
    segments=spec['stairs']['segments']
    errors=[]
    def require(condition,message):
        if not condition: errors.append(message)
    risers=[]
    for left,right in zip(segments,segments[1:]):
        require(abs(left['xEndCm']-right['xStartCm'])<1e-8,'Gap in walking sequence')
        dz=right['topZcm']-left['topZcm']
        if dz>1e-8: risers.append(dz)
        require(dz>=-1e-8,'Downstep in uphill staircase')
    require(len(risers)==82,'Incorrect riser count')
    require(all(abs(z-1432.5/82)<1e-8 for z in risers),'Unequal riser')
    require(segments[0]['topZcm']==-1432.5 and segments[-1]['topZcm']==0,'Wrong endpoint level')
    require(all(s['xEndCm']-s['xStartCm']==35 for s in segments if s['kind']=='tread'),'Wrong tread run')
    require(len([s for s in segments if s['kind']=='rest_landing'])==6,'Missing rest landing')
    require(all(s['clearWidthCm']==300 for s in segments),'Clear width changed')
    counts={}
    for mesh in meshes:
        path=ROOT/(mesh['name']+'.obj')
        vs,uvs,normals,faces=[],[],[],[]
        for line in path.read_text().splitlines():
            fields=line.split()
            if not fields: continue
            if fields[0]=='v': vs.append(tuple(map(float,fields[1:])))
            elif fields[0]=='vt': uvs.append(tuple(map(float,fields[1:])))
            elif fields[0]=='vn': normals.append(tuple(map(float,fields[1:])))
            elif fields[0]=='f': faces.append([tuple(int(t)-1 for t in field.split('/')) for field in fields[1:]])
        require(len(faces)==mesh['triangleCount'],'OBJ/JSON triangle mismatch')
        require(all(math.isfinite(t) for p in vs+uvs+normals for t in p),'Nonfinite mesh attribute')
        require(all(abs(sum(t*t for t in n)-1)<1e-7 for n in normals),'Nonunit normals')
        for face in faces:
            a,b,c=[vs[f[0]] for f in face]
            u=[b[i]-a[i] for i in range(3)]; v=[c[i]-a[i] for i in range(3)]
            n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            require(sum(t*t for t in n)>1e-18,'Degenerate face')
            require(sum(n[i]*normals[face[0][2]][i] for i in range(3))>0,'Normal/winding mismatch')
            a,b,c=[uvs[f[1]] for f in face]
            require(abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-10,'Degenerate UV')
        require(all(max(abs(vs[i][axis]-[p[0]/100,-p[1]/100,p[2]/100][axis]) for axis in range(3))<1e-8 for i,p in enumerate(mesh['verticesUEcm'])),'OBJ coordinate conversion drift')
        counts[mesh['name']]=len(faces)
    report={'status':'PASS' if not errors else 'FAIL','errors':errors,'triangles':counts,
            'verified':['82 equal risers and continuous segment endpoints','6 rest landings and300cm clear width',
                        'OBJ/JSON coordinate agreement','finite nondegenerate triangles, explicit consistent normals and UVs'],
            'limitations':'No scene obstacles, native import, collision, visual or package testing.'}
    (ROOT/'independent-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if errors: raise SystemExit(1)


if __name__=='__main__': check()

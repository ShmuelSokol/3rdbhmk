"""Read-only source geometry diagnostic; no native/render acceptance.

Instrument the unchanged tree generator to identify emitted tube boundaries.
Sample parent end caps with deterministic area-uniform barycentric samples;
classify coverage by all other closed bark shells using solid-angle winding.
The reported fractions are samples, not a continuous coverage proof.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[3])
parser.add_argument('--output', type=Path, required=True, help='Fresh directory; never overwrite evidence')
args=parser.parse_args()
ROOT=args.project_root.resolve()
OUT=args.output.resolve()
if OUT.exists():
    raise SystemExit('Output must be a fresh directory')
expected={
    'Scripts/create_street_trees.py':'93721e75f7fede024362e0851759291c070dd6320f6524d608584f0537432e01',
    'Scripts/create_vegetation.py':'d5d9586eb0df74756e560080c491ecb7fbf2833f79cb3c4329ccce1f5c0cd4b4',
    'SourceAssets/vegetation-review/StreetTreesV1/obj/SM_StreetTreesV1_Olive_S0_L0_Bark.obj':
        '0a8162fd8c286a336c5070d4a5d3b5a713ffde878faf713eacd5db972f505633',
}
for name,digest in expected.items():
    if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
        raise SystemExit('Pinned source mismatch: '+name)
OUT.mkdir(parents=True)
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('trees', ROOT/'Scripts/create_street_trees.py')
trees = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trees)
original = trees.tapered_tube
tubes = []

def capture(part, spine, radii, sides, **kwargs):
    begin_v, begin_f = len(part.vertices), len(part.faces)
    original(part, spine, radii, sides, **kwargs)
    tubes.append(dict(spine=np.array(spine), sides=sides,
                      vertices=np.array(part.vertices[begin_v:]),
                      faces=np.array(part.faces[begin_f:])-begin_v))

def winding(points, triangles):
    result = np.zeros(len(points))
    for offset in range(0, len(points), 64):
        p = points[offset:offset+64, None, :]
        a,b,c = (triangles[None,:,i,:]-p for i in range(3))
        la,lb,lc = (np.linalg.norm(x, axis=2) for x in (a,b,c))
        numerator = np.einsum('pfi,pfi->pf', a, np.cross(b,c))
        denominator = (la*lb*lc + np.einsum('pfi,pfi->pf', a,b)*lc
                       + np.einsum('pfi,pfi->pf', b,c)*la
                       + np.einsum('pfi,pfi->pf', c,a)*lb)
        result[offset:offset+64] = np.sum(2*np.arctan2(numerator, denominator),axis=1)/(4*np.pi)
    return np.abs(result) > 0.5

def samples(triangles, count=4096):
    area = np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],
                                  triangles[:,2]-triangles[:,0]),axis=1)/2
    rng = np.random.default_rng(20261002)
    ids = rng.choice(len(triangles), count, p=area/area.sum())
    uv = rng.random((count,2))
    s = np.sqrt(uv[:,0])
    w = np.column_stack((1-s, s*(1-uv[:,1]), s*uv[:,1]))
    return np.einsum('pi,pij->pj',w,triangles[ids]), float(area.sum())

def main():
    # Check the classifier independently on an outward tetrahedron, including
    # reversed winding. These are numerical tests, not a robust geometry proof.
    v=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,0,1]])
    f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
    points=np.array([[.1,.1,.1],[2,2,2],[-.1,.1,.1]])
    assert winding(points,v[f]).tolist()==[True,False,False]
    assert winding(points,v[f[:,::-1]]).tolist()==[True,False,False]
    trees.tapered_tube=capture
    species=trees.SPECIES_BY_KEY['Olive']
    bark,leaf=trees.build_street_tree(species,0,trees.species_seed(species,0))
    trees.tapered_tube=original
    assert sum(len(t['faces']) for t in tubes)==len(bark[0].faces)
    obj=ROOT/'SourceAssets/vegetation-review/StreetTreesV1/obj/SM_StreetTreesV1_Olive_S0_L0_Bark.obj'
    stored_v=[];stored_f=[]
    for line in obj.read_text(encoding='utf-8').splitlines():
        if line.startswith('v '):
            x,y,z=map(float,line.split()[1:4]);stored_v.append((x,-y,z))
        elif line.startswith('f '):
            f=[int(x.split('/')[0])-1 for x in line.split()[1:]]
            assert len(f)==3
            stored_f.append(tuple(reversed(f)))
    generated=np.array(bark[0].vertices)
    stored=np.array(stored_v)
    assert stored.shape==generated.shape
    quantization_error=float(np.abs(stored-generated).max())
    assert quantization_error<=0.0000051
    # OBJ winding may be globally oriented before export; compare exact
    # triangle membership with orientation handled independently by winding.
    assert sorted(tuple(sorted(f)) for f in stored_f)==sorted(tuple(sorted(f)) for f in bark[0].faces)
    forks=[]
    for idx,tube in enumerate(tubes):
        children=[i for i,t in enumerate(tubes) if i!=idx and
                  np.linalg.norm(t['spine'][0]-tube['spine'][-1])<1e-9]
        if not children:
            continue
        sides=tube['sides']
        start=(len(tube['spine'])-1)*sides*2
        cap=tube['vertices'][tube['faces'][start:start+sides-2]]
        pts,area=samples(cap)
        # Offset toward the parent's tip along its final tangent avoids coplanar
        # boundary ambiguity. Report two epsilon scales to expose sensitivity.
        axis=tube['spine'][-1]-tube['spine'][-2]
        axis/=np.linalg.norm(axis)
        rows=[]
        for epsilon in (0.001,0.01):
            query=pts+epsilon*axis
            covered=np.zeros(len(query),dtype=bool)
            for j,other in enumerate(tubes):
                if j==idx:
                    continue
                vv=other['vertices']
                candidates=np.all((query>=vv.min(0)) & (query<=vv.max(0)),axis=1)&~covered
                if candidates.any():
                    covered[candidates]|=winding(query[candidates],vv[other['faces']])
            rows.append(dict(offsetCm=epsilon,uncoveredSamples=int((~covered).sum()),
                             sampleCount=len(query),uncoveredFraction=float((~covered).mean())))
        forks.append(dict(parentTube=idx,children=children,capAreaCm2=area,coverage=rows))
    inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT/'Scripts/create_street_trees.py',ROOT/'Scripts/create_vegetation.py')}
    result=dict(scope='source numerical diagnostic only; sampled cap coverage, not rendered visibility or continuous proof',
                inputs=inputs,species='Olive',variant=0,lod=0,
                tubeCount=len(tubes),barkTriangles=len(bark[0].faces),forks=forks,
                exportedObj=dict(sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),
                                 vertices=len(stored),triangles=len(stored_f),
                                 maxCoordinateDifferenceCm=quantization_error,
                                 triangleMembershipMatches=True),
                controls='tetrahedron inside/outside and reversed winding pass',
                productionWrites=False)
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(tubes=len(tubes),forks=len(forks),rootFork=forks[0])))

if __name__=='__main__':
    main()

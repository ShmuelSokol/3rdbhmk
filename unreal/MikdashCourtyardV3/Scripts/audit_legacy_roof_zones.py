"""Read-only ownership audit for the original imported roof tanks and panels.

Writes a proposed visibility partition outside the Unreal project. No asset or map writes.
Uses the frozen triangle connectivity, not a whole-actor bounding-box hide heuristic.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import mmap
from pathlib import Path
import sys
import numpy as np

TANK = 'SM_JerusalemInstance_Rooftop_tanks'
PANEL = 'SM_JerusalemInstance_Rooftop_panels'
TOL_AMOT = 0.002  # 0.1 cm; covers the frozen float32 export.


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def read_positions(path, frozen):
    if sha(path) != frozen['sourceMeshSha256']:
        raise RuntimeError('Original triangle source hash mismatch')
    with path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        start = mm.find(b'"category":"Mapped building extrusions"')
        if start < 0:
            raise RuntimeError('Building source category absent')
        marker = b'"positions":['
        begin = mm.find(marker, start)
        if begin < 0:
            raise RuntimeError('Building positions absent')
        begin += len(marker)
        end = mm.find(b']', begin)
        p = np.fromstring(mm[begin:end].decode('ascii'), sep=',').reshape(-1, 3)
    if len(p) != frozen['sourceVertices'] or not np.isfinite(p).all():
        raise RuntimeError('Frozen vertex census differs')
    return p


def component_membership(p, frozen):
    """Replay the frozen export's exact connectivity and check every component box/count."""
    unique, inverse = np.unique(p, axis=0, return_inverse=True)
    if len(unique) != frozen['analysisUniquePositions']:
        raise RuntimeError('Unique vertex census differs')
    parent = list(range(len(unique)))
    sizes = [1] * len(unique)
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    def union(a, b):
        a, b = find(int(a)), find(int(b))
        if a == b:
            return
        if sizes[a] < sizes[b]:
            a, b = b, a
        parent[b] = a
        sizes[a] += sizes[b]
    for a, b, c in inverse.reshape(-1, 3):
        union(a, b)
        union(b, c)
    roots = np.array([find(i) for i in range(len(unique))])
    tri_roots = roots[inverse.reshape(-1, 3)[:, 0]]
    grouped = defaultdict(list)
    for i, root in enumerate(tri_roots):
        grouped[int(root)].append(i)
    if len(grouped) != frozen['connectedComponentCount']:
        raise RuntimeError('Connected component census differs')
    by_root = {c['sourceRootVertexId']: c for c in frozen['components']}
    if set(grouped) != set(by_root):
        raise RuntimeError('Component root identity differs from frozen export')
    tris = p.reshape(-1, 3, 3)
    for root, tids in grouped.items():
        c = by_root[root]
        points = tris[tids].reshape(-1, 3)
        if len(tids) != c['triangles'] or not np.array_equal(points.min(0), c['sourceBoundsAmos']['min']) or not np.array_equal(points.max(0), c['sourceBoundsAmos']['max']):
            raise RuntimeError('Component geometry differs: %s' % root)
    return tris, tri_roots, by_root


def point_on_triangle(x, z, tri, tolerance=TOL_AMOT):
    a, b, c = tri[:, (0, 2)]
    v0, v1, v2 = b-a, c-a, np.array([x, z])-a
    det = v0[0]*v1[1] - v0[1]*v1[0]
    if abs(det) < 1e-10:
        return False
    u = (v2[0]*v1[1] - v2[1]*v1[0])/det
    v = (v0[0]*v2[1] - v0[1]*v2[0])/det
    # Convert the positional tolerance to a barycentric edge allowance.
    eps = tolerance * max(np.linalg.norm(v0), np.linalg.norm(v1), np.linalg.norm(c-b)) / abs(det)
    return u >= -eps and v >= -eps and u+v <= 1+eps


def choose_owner(groups):
    """Do not guess when surfaces from different actors share a position."""
    unique = set(groups)
    return next(iter(unique)) if len(unique) == 1 else None


def audit(project, output):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(project/'Scripts'))
    import create_oldcity_facades as F
    import create_enclosure as E
    import create_city_detail as C
    frozen_path = F.FROZEN_MANIFEST
    frozen = json.loads(frozen_path.read_text(encoding='utf-8-sig'))
    if frozen['fbxSha256'] != F.FROZEN_FBX_SHA:
        raise RuntimeError('Unreviewed frozen building manifest')
    instance_path = frozen_path.parent/'instances-manifest.json'
    if sha(instance_path) != '5b80379b80b891dc20809a025bb69a15c5219123d23f6a25e0bc1de81199ec33':
        raise RuntimeError('Unreviewed original instance manifest')
    instances = json.loads(instance_path.read_text(encoding='utf-8-sig'))
    groups = {g['assetName']:g for g in instances['groups']}
    tanks, panels = groups[TANK]['instances'], groups[PANEL]['instances']
    if len(tanks) != 6007 or len(panels) != 6007:
        raise RuntimeError('Original roof pair census differs')
    source_path = frozen_path.parent.parent.parent/'architecture-review/jerusalem-meshes.json'
    p = read_positions(source_path, frozen)
    tris, roots, by_root = component_membership(p, frozen)
    # Only horizontal faces; their actual triangle footprint proves support.
    horizontal = np.ptp(tris[:, :, 1], axis=1) <= TOL_AMOT
    roof_tids = np.flatnonzero(horizontal)
    spatial = defaultdict(list)
    for tid in roof_tids:
        tri = tris[tid]
        for ix in range(math.floor(tri[:,0].min()/200), math.floor(tri[:,0].max()/200)+1):
            for iz in range(math.floor(tri[:,2].min()/200), math.floor(tri[:,2].max()/200)+1):
                spatial[ix,iz].append(tid)
    comps = list(frozen['components'])
    lows = np.array([c['sourceBoundsAmos']['min'] for c in comps])
    highs = np.array([c['sourceBoundsAmos']['max'] for c in comps])
    centres = (lows + highs) / 2
    owners, unresolved = [], []
    for index, (tank, panel) in enumerate(zip(tanks, panels)):
        if tank['sourceInstanceIndex'] != index or panel['sourceInstanceIndex'] != index:
            raise RuntimeError('Pair ordering changed')
        t = np.array(tank['translationUnrealCm'])
        q = np.array(panel['translationUnrealCm'])
        if max(abs(q-t-np.array([100,50,-15]))) > .05:
            raise RuntimeError('Tank/panel pair transform mismatch at %s' % index)
        x, z = t[0]/50-F.TX, t[1]/50-F.TZ
        y = (t[2]-45)/50
        # Frozen source places a tank at the footprint bounds centre, 0.9 amah above roof.
        exact = np.flatnonzero((abs(centres[:,0]-x)<=TOL_AMOT) & (abs(centres[:,2]-z)<=TOL_AMOT) & (abs(highs[:,1]-y)<=TOL_AMOT))
        exact_groups = {comps[i]['assignedGroup'] for i in exact}
        surface_groups = set()
        for tid in spatial.get((math.floor(x/200),math.floor(z/200)),[]):
            if abs(tris[tid,0,1]-y)<=TOL_AMOT and point_on_triangle(x,z,tris[tid]):
                surface_groups.add(by_root[int(roots[tid])]['assignedGroup'])
        all_groups = exact_groups | surface_groups
        owner = choose_owner(all_groups)
        if owner is None:
            unresolved.append({'sourceIndex':index,'translationCm':t.tolist(),'groups':sorted(all_groups)})
        else:
            owners.append({'sourceIndex':index,'buildingLabel':'SM_JerusalemBuildings_'+owner,
                           'basis':'roof_triangle' if owner in surface_groups else 'exact_frozen_component_bounds_centre',
                           'tankTranslationCm':t.tolist(),'panelTranslationCm':q.tolist()})
    hidden = C.load_precinct_hidden_cells()
    f=hidden['squareOuterFacesCm']
    current = E.hide_set(dict(west=f['xWest'],east=f['xEast'],north=f['yNorth'],south=f['ySouth']),hidden['policy'])
    labels=set(current['labels'])
    for entry in owners:
        entry['zone']='precinct' if entry['buildingLabel'] in labels else 'kept'
    report={'status':'offline_partition_ready_native_apply_pending' if not unresolved else 'refused_unresolved_owners',
            'generatedUtc':datetime.now(timezone.utc).isoformat(),
            'scriptSha256':sha(Path(__file__)),
            'sources':{str(p):sha(p) for p in (frozen_path,instance_path,source_path,C.PRECINCT_JSON,project/'Scripts/create_enclosure.py')},
            'triangleConnectivityVerified':True,'componentCount':len(by_root),'pairs':len(tanks),
            'resolvedPairs':len(owners),'zones':dict(Counter(e['zone'] for e in owners)),
            'ownershipBasis':dict(Counter(e['basis'] for e in owners)),
            'unresolved':unresolved,'owners':owners,
            'nativeStateVerified':False,'visualRepairVerified':False,
            'nextAction':'Split only the two original ISM components by these source pairs; precinct instances use CityDetailZone_Precinct. Preserve all transforms/materials; verify map readback and MODERN restore, then package and capture A1.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('owners','sources')},indent=2))
    return not unresolved

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    raise SystemExit(0 if audit(args.project.resolve(),args.output.resolve()) else 1)

"""Deterministic, offline-only curtains for four diagnosed solid infill blocks.

Writes only OldCityFoundationV1/foundation-study.json. --check writes nothing.
No Unreal, imports, asset/map writes, original generator edits, or collision claim.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/context-review/OldCityFoundationV1'
MANIFEST = ROOT / 'SourceAssets/context-review/OldCityFacadesV1/facades-manifest.json'
TERRAIN = ROOT / 'SourceAssets/FutureMountV1/terrain-generated/SM_JerusalemTerrain_07_08_FutureMountCut.mesh.json'
RAW = Path('C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/architecture-review/jerusalem-meshes.json')
DECK = ROOT / 'SourceAssets/context-review/KotelPlazaV1/kotel-plaza-plan.json'
PRECINCT = ROOT / 'SourceAssets/enclosure-review/precinct-Candidate48.json'
MODULES = ROOT / 'SourceAssets/enclosure-review/plaza-manifest.json'
ACCESS = [ROOT / 'SourceAssets/mount-access/mount-access.mesh.json',
          ROOT / 'SourceAssets/mount-access/OpeningV2/opening-v2.mesh.json']
IDS = (1200, 1210, 1181, 1183)
PINS = {
    MANIFEST: '9f5c133d378f36e4c23216713dadfc2c963a8613e6bd1d02166ed3fa067e5456',
    TERRAIN: 'abc6152db1d10b80476870ac843bfde232b30ccac90733994e3ecf743579095a',
    RAW: 'cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb',
    DECK: 'f3483bff589169159bc99200761d90230e4726ec248226c948f0ead6dedca69c',
    PRECINCT: '201e5b2d4b223690f7398f3d767e7877b1c89f1017f7e845d67e18e4296ed33e',
    MODULES: '98f2578043a6f1cdecf39e1a2771406c684e76e292448f51939742dfddc9f74a',
    ACCESS[0]: '3bf90defcdbb3f6a9447ff9f0fc0d1139d9b457324487ce9361099a53abe13e7',
    ACCESS[1]: '61c4d2f7fef2afc6a03d365c5e78ea54f9674ca377a1e79ee9c601f55afe982b',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def area(poly):
    return sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(poly, poly[1:]+poly[:1]))/2


def cross(a, b, c):
    u = [b[i]-a[i] for i in range(3)]
    v = [c[i]-a[i] for i in range(3)]
    return [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]


def norm(v):
    return math.sqrt(sum(x*x for x in v))


def lerp(a, b, t):
    return [x+(y-x)*t for x, y in zip(a, b)]


def bary(tri, p):
    a, b, c = tri
    det = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(det) < 1e-8:
        raise ValueError('Degenerate projected terrain triangle')
    u = ((b[1]-c[1])*(p[0]-c[0])+(c[0]-b[0])*(p[1]-c[1]))/det
    v = ((c[1]-a[1])*(p[0]-c[0])+(a[0]-c[0])*(p[1]-c[1]))/det
    return [u, v, 1-u-v]


def segment_interval(tri, a, b):
    lo, hi = 0., 1.
    for u, v in zip(bary(tri, a), bary(tri, b)):
        d = v-u
        if abs(d) < 1e-12:
            if u < -1e-10:
                return None
        elif d > 0:
            lo = max(lo, -u/d)
        else:
            hi = min(hi, -u/d)
    return (lo, hi) if hi-lo > 1e-10 else None


def height(tri, p):
    return sum(w*v[2] for w, v in zip(bary(tri, p), tri))


def clip_convex(subject, boundary):
    """Actual polygon intersection, never an AABB occupancy approximation."""
    out = [list(p[:2]) for p in subject]
    boundary = [list(p[:2]) for p in boundary]
    if area(boundary) < 0:
        boundary.reverse()
    for a, b in zip(boundary, boundary[1:]+boundary[:1]):
        def side(p):
            return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        prev, out = out, []
        for p, q in zip(prev, prev[1:]+prev[:1]):
            u, v = side(p), side(q)
            if u >= 0:
                out.append(p)
            if (u >= 0) != (v >= 0):
                out.append(lerp(p, q, u/(u-v)))
        if not out:
            break
    return out


def bounds(poly):
    return [min(p[0] for p in poly), min(p[1] for p in poly),
            max(p[0] for p in poly), max(p[1] for p in poly)]


def boxes_touch(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def load_obj(path):
    verts, tris = [], []
    for line in path.read_text().splitlines():
        parts = line.split()
        if parts and parts[0] == 'v':
            verts.append([float(parts[1]), -float(parts[2]), float(parts[3])])
        elif parts and parts[0] == 'f':
            assert len(parts) == 4
            ids = [int(p.split('/')[0])-1 for p in [parts[1], parts[3], parts[2]]]
            tris.append([verts[i] for i in ids])
    return tris


def load_owners(manifest, hashes):
    owners = {}
    for batch in manifest['batches']:
        entry = batch.get('infill')
        if not entry or not any(r['infillId'] in IDS for r in entry['perBuilding']):
            continue
        path = MANIFEST.parent/'obj'/entry['file']
        assert sha(path) == entry['sha256'], 'Changed source OBJ'
        hashes[str(path)] = sha(path)
        tris = load_obj(path)
        offset = 0
        for row in entry['perBuilding']:
            count = row['triangles']
            if row['infillId'] in IDS:
                assert row['plan'] == 'block' and row['wings'] == 1
                prism = tris[offset:offset+12]
                polygon = [prism[i][0][:2] for i in (0, 2, 4, 6)]
                assert area(polygon) > 0
                edges, volume = {}, 0.
                for tri in prism:
                    volume += sum(tri[0][i]*cross([0, 0, 0], tri[1], tri[2])[i] for i in range(3))/6
                    for a, b in zip(tri, tri[1:]+tri[:1]):
                        key = tuple(sorted([tuple(a), tuple(b)]))
                        edges[key] = edges.get(key, 0)+1
                assert volume > 0 and all(v == 2 for v in edges.values())
                base = row['baseZcm']
                assert all(abs(p[2]-base) < .001 for tri in prism[10:] for p in tri)
                owner = dict(infillId=row['infillId'], obj=entry['file'],
                             firstPrismTriangle0=offset, footprintCm=polygon, baseZcm=base,
                             sourceMesh='/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Meshes/'+entry['file'][:-4],
                             expectedActorLabel='RELEASE_'+entry['file'][3:-4],
                             expectedWorldTransform=dict(location=[0, 0, 0], rotation=[0, 0, 0], scale=[1, 1, 1]))
                asset = ROOT/'Content'/(owner['sourceMesh'][6:]+'.uasset')
                owner['sourceAssetSha256'] = sha(asset)
                expected_asset = {'Grid_N003_P001': '9bc21a5c917fe3bf4fbf055f67f8bfe9b364a18c09992dfb6e561d920439be76',
                                  'Grid_N003_P002': 'c3c11ce93146552eef87ab1c0d2c59d71f118f87cb404da579f34d4ca6fa9164'}
                assert owner['sourceAssetSha256'] == expected_asset[batch['name']], 'Owner asset drift'
                hashes[str(asset)] = sha(asset)
                owners[row['infillId']] = owner
            offset += count
        assert offset == len(tris) == entry['triangles']
    assert set(owners) == set(IDS)
    return [owners[i] for i in IDS]


def build(owners, terrain):
    out = dict(vertices=[], triangles=[], normals=[], uv0=[], pieces=[])
    missing = 0.
    for owner in owners:
        ring, top = owner['footprintCm'], owner['baseZcm']
        for ei, (a, b) in enumerate(zip(ring, ring[1:]+ring[:1])):
            length = math.dist(a, b)
            normal = [(b[1]-a[1])/length, -(b[0]-a[0])/length, 0.]
            hits = [(r[0], r[1], ti) for ti, tri in enumerate(terrain)
                    if (r := segment_interval(tri, a, b))]
            knots = sorted({0., 1.} | {v for lo, hi, ti in hits for v in (lo, hi)})
            for lo, hi in zip(knots, knots[1:]):
                if (hi-lo)*length < 1e-6:
                    continue
                mid = (lo+hi)/2
                tids = [ti for l, h, ti in hits if l-1e-10 <= mid <= h+1e-10]
                if not tids:
                    missing += (hi-lo)*length
                    continue
                zs = [[height(terrain[ti], lerp(a, b, t)) for ti in tids] for t in (lo, hi)]
                assert all(max(z)-min(z) < .01 for z in zs), 'Discontinuous source heights'
                z0, z1 = [z[0] for z in zs]
                if min(z0, z1) >= top-1e-7:
                    continue
                if max(z0, z1) > top:
                    t = (top-z0)/(z1-z0)
                    root = lo+(hi-lo)*t
                    if z0 > top:
                        lo, z0 = root, top
                    else:
                        hi, z1 = root, top
                p, q = lerp(a, b, lo), lerp(a, b, hi)
                quad = [p+[z0], q+[z1], q+[top], p+[top]]
                first = len(out['triangles'])
                for order in ((0, 1, 2), (0, 2, 3)):
                    tri = [quad[k] for k in order]
                    n = cross(*tri)
                    if norm(n) < 1e-7:
                        continue
                    if sum(n[i]*normal[i] for i in range(3)) < 0:
                        tri.reverse()
                    ids = []
                    for v in tri:
                        ids.append(len(out['vertices']))
                        out['vertices'].append(v)
                        out['normals'].append(normal)
                        out['uv0'].append([math.dist(v[:2], a)/100, (v[2]-top)/100])
                    out['triangles'].append(ids)
                out['pieces'].append(dict(infillId=owner['infillId'], edgeIndex=ei,
                    sourceTriangles=tids, sourceEdgeParameters=[lo, hi], xyEndpointsCm=[p, q],
                    bottomZcm=[z0, z1], topZcm=top, outwardNormal=normal,
                    triangleStart=first, triangleCount=len(out['triangles'])-first))
    if missing > 1e-6:
        raise ValueError('Uncovered terrain boundary: %.6f cm' % missing)
    out['uncoveredTerrainBoundaryCm'] = missing
    return out


def validate_geometry(mesh, owners, terrain):
    owners = {o['infillId']: o for o in owners}
    for piece in mesh['pieces']:
        owner = owners[piece['infillId']]
        ring = owner['footprintCm']
        a, b = ring[piece['edgeIndex']], ring[(piece['edgeIndex']+1) % len(ring)]
        delta = [b[i]-a[i] for i in range(2)]
        length = math.dist(a, b)
        for face in mesh['triangles'][piece['triangleStart']:piece['triangleStart']+piece['triangleCount']]:
            tri = [mesh['vertices'][i] for i in face]
            assert sum(x*y for x, y in zip(cross(*tri), piece['outwardNormal'])) > 1e-7
            for p in tri:
                t = sum((p[i]-a[i])*delta[i] for i in range(2))/(length*length)
                assert -1e-9 <= t <= 1+1e-9 and math.dist(p[:2], lerp(a, b, t)) < 1e-6
                z = height(terrain[piece['sourceTriangles'][0]], p)
                assert z-1e-6 <= p[2] <= owner['baseZcm']+1e-6
    return True


def overlaps(owners, label, candidates):
    """Conservative projected area test; any positive area requires review.

    It does not claim AABBs are solids or distinguish clear vertical separation.
    """
    result, tested = [], 0
    for identity, tri in candidates:
        if abs(area(tri)) < 1e-7:
            continue
        box = bounds(tri)
        for owner in owners:
            if not boxes_touch(box, bounds(owner['footprintCm'])):
                continue
            tested += 1
            value = abs(area(clip_convex(tri, owner['footprintCm'])))
            if value > .01:
                result.append(dict(infillId=owner['infillId'], source=identity,
                                   projectedOverlapAreaCm2=value))
    return dict(category=label, projectedTrianglePairsTested=tested, overlaps=result,
                criterion='positive XY intersection area >0.01cm2; conservative, not 3D collision')


def audits(owners, manifest, hashes):
    raw = read(RAW)['meshes']
    results = []
    def raw_triangles(mi):
        mesh = raw[mi]
        p, ix = mesh['positions'], mesh['indices']
        for i in range(0, len(ix), 3):
            yield str(mi)+':'+str(i//3), [[(p[j*3]+17.509700315687695)*50,
                (p[j*3+2]-.5513496449385334)*50, p[j*3+1]*50] for j in ix[i:i+3]]
    for mi, label in [(1, 'original_building_triangles'), (2, 'asphalt_road_triangles'),
                      (3, 'stone_path_triangles'), (4, 'city_wall_triangles')]:
        results.append(overlaps(owners, label, raw_triangles(mi)))
    del raw
    for path in ACCESS:
        data = read(path)
        assert data['units'] == 'Unreal centimetres east/south/up'
        candidates = ((m['name']+':'+str(i), [m['verticesUEcm'][j] for j in face])
                      for m in data['meshes'] for i, face in enumerate(m['triangles']))
        results.append(overlaps(owners, str(path.relative_to(ROOT)), candidates))
    plan = read(DECK)
    for category in ['deck', 'step']:
        candidates = []
        for i, row in enumerate(plan[category]):
            cx, cy, cz = row['loc']
            hx, hy = ([625*row['scale'][0], 625*row['scale'][1]] if category == 'deck'
                      else [1250*row['scale'][0], 50*row['scale'][1]])
            theta = math.radians(row['rot'][2])
            poly = [[cx+x*math.cos(theta)-y*math.sin(theta), cy+x*math.sin(theta)+y*math.cos(theta)]
                    for x, y in [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]]
            if category == 'deck':
                # V3 cut rectangles use its 0.01cm snap, not only unsnapped paving.
                box = bounds(poly)
                x0, y0, x1, y1 = [round(round(v/.01)*.01, 6) for v in box]
                poly = [[x0,y0], [x1,y0], [x1,y1], [x0,y1]]
            candidates.extend([(str(i)+':0', poly[:3]), (str(i)+':1', [poly[0],poly[2],poly[3]])])
        results.append(overlaps(owners, 'kotel_'+category, candidates))
    # All potentially nearby generated batches, exact triangles. Exclude only the four
    # diagnosed owners' own bodies and ornament; their 4cm lower trim is intentionally adjacent.
    candidates = []
    for batch in manifest['batches']:
        for role in ('facades', 'infill'):
            e = batch.get(role)
            if not e:
                continue
            lo, hi = e['canonicalBoundsCm']['min'], e['canonicalBoundsCm']['max']
            if not any(boxes_touch([lo[0],lo[1],hi[0],hi[1]], bounds(o['footprintCm'])) for o in owners):
                continue
            path = MANIFEST.parent/'obj'/e['file']
            assert sha(path) == e['sha256']
            hashes[str(path)] = sha(path)
            tris, offset = load_obj(path), 0
            for record in e['perBuilding']:
                if record.get('infillId') not in IDS:
                    candidates.extend((e['file']+':'+str(i), tris[i])
                                      for i in range(offset, offset+record['triangles']))
                offset += record['triangles']
            assert offset == len(tris)
    results.append(overlaps(owners, 'other_oldcity_facades_and_infill', candidates))
    return results


def self_test():
    square = dict(infillId=1, footprintCm=[[.25,.25],[1.75,.25],[1.75,1.75],[.25,1.75]], baseZcm=10.)
    flat = [[[0,0,0],[2,0,0],[2,2,0]], [[0,0,0],[2,2,0],[0,2,0]]]
    mesh = build([square], flat)
    measured = sum(norm(cross(*[mesh['vertices'][i] for i in f]))/2 for f in mesh['triangles'])
    assert abs(measured-60) < 1e-8, 'shared diagonal must not duplicate faces'
    validate_geometry(mesh, [square], flat)
    diagonal = dict(square, footprintCm=[[.25,.25],[1.25,1.25],[.75,1.75],[0,1]])
    shared = build([diagonal], flat)
    shared_area = sum(norm(cross(*[shared['vertices'][i] for i in f]))/2 for f in shared['triangles'])
    perimeter = sum(math.dist(a,b) for a,b in zip(diagonal['footprintCm'], diagonal['footprintCm'][1:]+diagonal['footprintCm'][:1]))
    assert abs(shared_area-perimeter*10) < 1e-8, 'Coincident terrain diagonal must emit one curtain'
    assert not build([dict(square, baseZcm=-1)], flat)['triangles'], 'no excavation faces'
    slope = [[[0,0,0],[2,0,20],[2,2,20]], [[0,0,0],[2,2,20],[0,2,0]]]
    cut = build([square], slope)
    validate_geometry(cut, [square], slope)
    assert all(v[0] <= 1+1e-8 for v in cut['vertices']), 'split at terrain/base crossing'
    assert abs(area(clip_convex([[0,0],[2,0],[2,2],[0,2]], [[1,1],[3,1],[3,3],[1,3]]))-1) < 1e-8
    assert not clip_convex([[0,0],[1,0],[1,1],[0,1]], [[2,0],[3,0],[3,1],[2,1]])
    try:
        build([dict(square, footprintCm=[[5,5],[6,5],[6,6],[5,6]])], flat)
    except ValueError:
        pass
    else:
        raise AssertionError('Missing terrain must refuse')
    for axis in range(3):
        mesh['vertices'][0][axis] += .1*mesh['normals'][0][axis]
    try:
        validate_geometry(mesh, [square], flat)
    except AssertionError:
        pass
    else:
        raise AssertionError('Off-boundary mutation must refuse')
    return '8 synthetic invariants passed (area, coincident diagonal, split, excavation, polygon overlap, disjoint, missing terrain, mutation)'


def generate():
    tests = self_test()
    hashes = {str(p): sha(p) for p in PINS}
    assert all(hashes[str(p)] == h for p, h in PINS.items()), 'Pinned source changed'
    manifest, source = read(MANIFEST), read(TERRAIN)
    assert source['units'] == 'centimeters' and source['axes'] == 'east,south,up' and source['anchorAlreadyApplied'] is True
    modules = {m['name']: m['canonicalBoundsCm'] for m in read(MODULES)['meshes']}
    assert modules['SM_PlazaV1_DeckTile'] == {'min': [-625.,-625.,-50.], 'max': [625.,625.,0.]}
    assert modules['SM_PlazaV1_Step'] == {'min': [-1250.,-50.,-25.], 'max': [1250.,50.,0.]}
    assert len(source['triangles']) == 566 and len(read(DECK)['deck']) == 959
    terrain = [[source['vertices'][i] for i in f] for f in source['triangles']]
    owners = load_owners(manifest, hashes)
    mesh = build(owners, terrain)
    validate_geometry(mesh, owners, terrain)
    checks = audits(owners, manifest, hashes)
    blocked = [c['category'] for c in checks if c['overlaps']]
    # Preserve a diagnosable study even if a new overlap refuses progression to integration.
    hidden = read(PRECINCT)['modernCity']['hideSet']['labels']
    for owner in owners:
        owner['inCandidate48PrecinctHideSet'] = owner['expectedActorLabel'] in hidden
        assert owner['inCandidate48PrecinctHideSet'], 'Reviewed visibility owner changed'
        owner['visibilityPolicy'] = 'Follow actual owning actor/component visibility and state; MODERN visible, YECHEZKEL hidden, OVERLAY visible for these precinct owners. Never toggle owner.'
    mesh.update(schemaVersion=1, status='offline_study_overlap_review_required' if blocked else 'offline_study_checks_passed_native_pending',
        units='world centimeters east/south/up', owners=owners, overlapAudits=checks,
        overlapReviewRequired=blocked, selfTests=tests, sourceSha256=hashes,
        generatorSha256=sha(Path(__file__)), collision='None: visual-only open curtain, not a watertight physics solid',
        winding='Canonical mathematical CCW agrees with outward normals. UE native import must reverse(a,c,b) only; preserve canonical data.',
        scope='Only boundary faces beneath four existing one-wing solid blocks. No roofs, floor caps, volumes, outward offsets, streets or Kotel cut edits.',
        unknowns=['No native rendered or collision acceptance.', 'Projected-overlap audits are conservative and ignore vertical clearance.',
                  'GatewayV3 has no offline mesh triangles; gateway interior V4 is an unimplemented draft, not audited geometry.',
                  'Later runtime decorations and complete navigable routes are not an exhaustive collision census.'])
    assert all(sha(Path(p)) == h for p, h in hashes.items()), 'Input changed during calculation'
    return mesh


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        print(self_test())
    else:
        result = generate()
        path = OUT/'foundation-study.json'
        payload = json.dumps(result, sort_keys=True, separators=(',', ':'))+'\n'
        if args.check:
            assert path.read_bytes() == payload.encode('utf-8'), 'Study drift; review inputs before regeneration'
        else:
            OUT.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload.encode('utf-8'))
        print(result['status'], len(result['triangles']), 'triangles;', len(result['pieces']), 'pieces;',
              'overlap review:', result['overlapReviewRequired'])

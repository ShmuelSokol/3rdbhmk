"""Author editable, offline-only Kotel access studies; never imports Unreal.

Python 3.12 + shapely 2.1.2 (existing FutureMountV1/.tools is read only).
Run: python Scripts/create_mount_access.py. Source geometry is cm east/south/up;
OBJ is metres east/north/up. Do not apply the OSM alignment a second time.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/mount-access'
sys.path.insert(0, str(ROOT / 'SourceAssets/FutureMountV1/.tools'))
import shapely
from shapely.geometry import Polygon, box, LineString
from shapely.geometry.polygon import orient

SOURCE = Path('C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/architecture-review/jerusalem-meshes.json')
EXPECTED = 'cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sampler():
    assert digest(SOURCE) == EXPECTED
    mesh = json.loads(SOURCE.read_text(encoding='utf-8'))['meshes'][0]
    assert mesh['name'] == 'Terrain 0'
    pos = mesh['positions']
    grid = {(pos[i], pos[i+2]): pos[i+1] for i in range(0, len(pos), 3)}

    def sample(x, y):
        x, y = x/50-17.509700315687695, y/50+.5513496449385334
        gx, gy = math.floor(x/50)*50, math.floor(y/50)*50
        a, b = (x-gx)/50, (y-gy)/50
        h00, h10, h01, h11 = [grid[p] for p in [(gx, gy), (gx+50, gy), (gx, gy+50), (gx+50, gy+50)]]
        return 50*(h00+(h10-h00)*a+(h01-h00)*b if a+b <= 1 else h11+(h01-h11)*(1-a)+(h10-h11)*(1-b))
    return sample


class Mesh:
    def __init__(self, name, category):
        self.name, self.category = name, category
        self.vertices, self.faces = [], []

    def triangle(self, a, b, c):
        n = len(self.vertices)
        self.vertices.extend([list(a), list(b), list(c)])
        self.faces.append([n, n+1, n+2])

    def quad(self, a, b, c, d):
        self.triangle(a, b, c)
        self.triangle(a, c, d)

    def cuboid(self, x0, y0, z0, x1, y1, z1):
        assert x1 > x0 and y1 > y0 and z1 > z0
        p = [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
             (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
        for a,b,c,d in [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            self.quad(p[a],p[b],p[c],p[d])

    def save(self):
        # Per-face normals + planar UVs have nonzero area, including risers/sides.
        lines = ['# Original illustrative access study; OBJ metres east/north/up',
                 'mtllib mount-access.mtl', 'o '+self.name, 'usemtl Limestone']
        vv = [(x/100,-y/100,z/100) for x,y,z in self.vertices]
        lines += ['v %.9f %.9f %.9f' % p for p in vv]
        normals, uvs = [], []
        for a,b,c in self.faces:
            a,b,c = a,c,b  # Reflection reverses handedness.
            p,q,r = vv[a],vv[b],vv[c]
            u,v = [q[i]-p[i] for i in range(3)], [r[i]-p[i] for i in range(3)]
            n = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            length = math.sqrt(sum(t*t for t in n))
            assert length > 1e-10
            normals.append([t/length for t in n])
            axes = [i for i in range(3) if i != max(range(3), key=lambda i: abs(n[i]))]
            uvs.extend([[vv[j][axes[0]],vv[j][axes[1]]] for j in [a,b,c]])
        lines += ['vt %.9f %.9f' % tuple(p) for p in uvs]
        lines += ['vn %.9f %.9f %.9f' % tuple(n) for n in normals]
        for i,(a,b,c) in enumerate(self.faces):
            lines.append('f '+' '.join(f'{j+1}/{3*i+k+1}/{i+1}' for k,j in enumerate([a,c,b])))
        (OUT/(self.name+'.obj')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
        return {'name':self.name,'category':self.category,'verticesUEcm':self.vertices,
                'triangles':self.faces,'actorLocationUEcm':[0,0,0], 'actorRotationDegrees':[0,0,0],
                'actorScale':[1,1,1], 'triangleCount':len(self.faces),
                'boundsUEcm':[[min(v[i] for v in self.vertices) for i in range(3)],
                              [max(v[i] for v in self.vertices) for i in range(3)]]}


def triangles(poly):
    result = [orient(t, sign=1) for t in shapely.constrained_delaunay_triangles(poly).geoms]
    assert abs(sum(t.area for t in result)-poly.area) < .01
    assert shapely.union_all(result).symmetric_difference(poly).area < .01
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert shapely.__version__ == '2.1.2'
    design_path = ROOT/'SourceAssets/visual-review/mount-platform-design.json'
    design = json.loads(design_path.read_text(encoding='utf-8'))
    wall, plaza = [Polygon(p['nativeXYcm']) for p in design['protected']]
    guard = shapely.union_all([wall.buffer(200),plaza.buffer(200)])
    terrain = sampler()
    # Additive infill intentionally overlaps protected plaza but NEVER the wall guard.
    fill = plaza.difference(wall.buffer(201))
    infill = Mesh('KotelPlaza_Infill_REVIEW_ONLY','intentional_additive_plaza_overlap')
    ox, oy = 17.509700315687695*50, -.5513496449385334*50
    minx,miny,maxx,maxy = fill.bounds
    pieces=[]
    # Split on the exact retained DEM diagonals before triangulation. A single
    # flat polygon would bury terrain or float above it by several metres.
    for ix in range(math.floor((minx-ox)/2500),math.ceil((maxx-ox)/2500)):
        for iy in range(math.floor((miny-oy)/2500),math.ceil((maxy-oy)/2500)):
            x,y=ox+ix*2500,oy+iy*2500
            for cell in [Polygon([(x,y),(x+2500,y),(x,y+2500)]),
                         Polygon([(x+2500,y),(x+2500,y+2500),(x,y+2500)])]:
                part=fill.intersection(cell)
                if part.area < 1e-5: continue
                for tri in triangles(part):
                    points=list(tri.exterior.coords)[:3]
                    infill.triangle(*[(a,b,terrain(a,b)+3) for a,b in points])
                    infill.triangle(*[(a,b,terrain(a,b)-12) for a,b in reversed(points)])
                    pieces.append(tri)
    # Boundary sides are split at each cell crossing via the already clipped pieces.
    # Internal sides omitted; outer skin is an editable terrain-following slab.
    for piece in pieces:
        coords=list(piece.exterior.coords)
        for a,b in zip(coords,coords[1:]):
            if fill.boundary.distance(LineString([a,b]).interpolate(.5,normalized=True)) < 1e-5:
                infill.quad((a[0],a[1],terrain(*a)-12),(b[0],b[1],terrain(*b)-12),
                            (b[0],b[1],terrain(*b)+3),(a[0],a[1],terrain(*a)+3))
    assert shapely.union_all(pieces).symmetric_difference(fill).area < .01

    y=19972.432518
    x=-18400.0
    z=-1432.5
    start=x
    rise=1432.5/82
    slabs=Mesh('KotelApproach_StairAndLandings','buffer_clear_stairs')
    rails=Mesh('KotelApproach_Parapets','buffer_clear_stairs')
    segments=[]
    def section(run, top, kind, step=None):
        nonlocal x
        slabs.cuboid(x,y-150,-2100,x+run,y+150,top)
        # Continuous solid stone side guards provide a physical fall barrier.
        for ya,yb in [(y-180,y-150),(y+150,y+180)]:
            rails.cuboid(x,ya,-2100,x+run,yb,top+110)
        segments.append({'kind':kind,'step':step,'xStartCm':x,'xEndCm':x+run,
                         'topZcm':top,'clearWidthCm':300})
        x+=run
    section(300,z,'lower_landing')
    for step in range(1,83):
        section(35,z+step*rise,'tread',step)
        if step%12==0 and step<82:
            section(250,z+step*rise,'rest_landing')
    section(500,0,'upper_landing')
    footprint=box(start,y-180,x,y+180)
    assert footprint.intersection(guard).area < .01, 'Stairs overlap protected guard'
    enclosure=Polygon(design['boundary']['nativeXYcm'])
    platform_end=box(x-200,y-150,x,y+150)
    assert enclosure.buffer(-110).covers(platform_end), 'Top landing misses platform'
    # Separate short terrain-following apron bridges the intentional plaza buffer
    # gap. It is NOT included in zero-overlap stair certification.
    apron=Mesh('KotelApproach_LowerApron_REVIEW_ONLY','intentional_additive_plaza_buffer_overlap')
    ax=-19200.0
    for i in range(8):
        a=ax+i*100; b=a+100
        for lo,hi in [(y-150,y+150)]:
            def h(xx,yy):
                t=(xx-ax)/(start-ax)
                return terrain(ax,yy)+3+(z-terrain(ax,yy)-3)*t
            apron.quad((a,lo,h(a,lo)),(b,lo,h(b,lo)),(b,hi,h(b,hi)),(a,hi,h(a,hi)))
    apron_foot=box(ax,y-150,start,y+150)
    assert apron_foot.intersection(wall.buffer(200)).area < .01
    data=[m.save() for m in [infill,slabs,rails,apron]]
    (OUT/'mount-access.mtl').write_text('newmtl Limestone\nKd 0.66 0.60 0.49\nKs 0.03 0.03 0.03\nNs 5\n',encoding='utf-8')
    (OUT/'mount-access.mesh.json').write_text(json.dumps({'units':'Unreal centimetres east/south/up','meshes':data},indent=2)+'\n',encoding='utf-8')
    checks={
        'status':'PASS_OFFLINE_GEOMETRY_ONLY',
        'stairProtectedBufferOverlapCm2':footprint.intersection(guard).area,
        'stairDistanceToProtectedPolygonsCm':min(footprint.distance(wall),footprint.distance(plaza)),
        'infillIntentionalPlazaOverlapCm2':fill.intersection(plaza).area,
        'infillWallBufferOverlapCm2':fill.intersection(wall.buffer(200)).area,
        'apronIntentionalPlazaGuardOverlapCm2':apron_foot.intersection(plaza.buffer(200)).area,
        'apronWallBufferOverlapCm2':apron_foot.intersection(wall.buffer(200)).area,
        'triangulatedInfillGapCm2':shapely.union_all(pieces).symmetric_difference(fill).area,
        'riseCm':rise,'riserCount':82,'finalTopZcm':segments[-1]['topZcm'],
        'treadRunCm':35,'minRestLandingRunCm':250,'clearWidthCm':300,
        'minimumOwnAssemblyHeadroomCm':None,
        'headroomMeaning':'Open sky; no overhead geometry in this authored assembly. Scene-wide capsule/headroom not tested.',
        'upperLandingContainedInInsetEnclosure':True,
        'nativeExecuted':False,
        'wallCrossingXYcm':list(enclosure.boundary.intersection(LineString([(start,y),(x,y)])).coords),
        'originalsEdited':False,
    }
    spec={
        'scenario':'Original illustrative future access proposal, not existing surveyed bridge, prediction, halachic access rule or building-code certification.',
        'status':'AUTHORED_OFFLINE_NOT_NATIVE_ACCEPTED',
        'coordinateContract':'JSON UE centimetres east/south/up with world placement baked. Actor identity transform. OBJ metres east/north/up; adapter must convert once and verify bounds/winding/UVs.',
        'sources':[{'path':str(p),'sha256':digest(p)} for p in [design_path, ROOT/'SourceAssets/visual-review/mount-platform-scenario-audit.json',ROOT/'SourceAssets/visual-review/western-wall-detail-brief.json',SOURCE]],
        'protectedInterpretation':'Infill and lower apron are separately held additive proposals overlapping the protected plaza or its buffer. They do not qualify for zero-overlap acceptance; original terrain, ribbon and wall are untouched. Root must explicitly scope additive plaza adoption and verify before/after collision.',
        'platformTopZcm':0,'existingOuterCourtZcm':300,'existingGatewayStairs':'Preserve existing 12 x 25cm stairs at x9200..8600; no measured Temple mesh edited or new stairs duplicated there.',
        'stairs':{'centerYCm':y,'xStartCm':start,'xEndCm':x,'bottomZcm':z,'topZcm':0,'segments':segments,'riseCm':rise,'runCm':35,'parapetHeightCm':110,'parapetThicknessCm':30,'clearWidthCm':300},
        'plaza':{'surface':'Piecewise planar source-terrain-following, +3cm visual surface, 15cm slab. Existing slope retained; not a level surveyed plaza. Wall footprint plus201cm excluded.','infillAreaM2':fill.area/10000,'apron':'800cm linear blend from source terrain+3cm to lower landing,300cm wide; no step-free certification.'},
        'materials':'Original warm limestone placeholder MTL; native believable paving/joints and variation still needed. No downloaded textures or paid assets.',
        'requiredNativeGates':['Exact enclosure wall crossing listed in checks; existing wall may block bridge. Inspect and split ONLY verified non-Kotel scenario wall segment; do not hide shared wall batch.', 'Top landing needs checked collision seam to new platform; stairs solid down to -2100cm and may intersect retained outside terrain/structures. Terrain and unrelated buildings were not clipped by this script.', 'Check source buildings/roads at full footprint; offline buffer checks do not establish scene obstacle clearance.', 'Measure apron slope and every capsule contact; existing ground/plaza ribbons may protrude above +3cm infill, so never adopt merely from triangle counts.', 'Additive infill stays201cm away from Wall; preserved ground occupies that gap. Native prayer-face walk must verify this deliberate seam.', 'Continuous walking lower apron,82steps,6rest landings,platform,originalTemple gateway and return. Check rails/landings,headroom,fall barriers and topwall opening.', 'Native save/reopen, whole approach/Kotel captures and fresh cook/package required. No native importer or map write is part of this delivery.'],
        'checks':checks,
    }
    (OUT/'mount-access-spec.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
    (OUT/'mount-access-checks.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(checks,indent=2))


if __name__ == '__main__':
    main()

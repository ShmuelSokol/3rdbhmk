"""Fresh native proof of wall surface/attribute preservation outside gate cuts."""
import json
import math
import sys
import traceback
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parent))
from release_haram_wall_passages import OUT,MAP,limits,local,sha,disk
from release_fix_kotel_occlusion import Native
from repair_candidate_kotel_skirt import rows_with_attributes,area,inside_polygon,sub,dot,cross

def bary(p,tri):
    a,b,c=tri;v0=sub(b,a);v1=sub(c,a);v2=sub(p,a)
    den=dot(v0,v0)*dot(v1,v1)-dot(v0,v1)**2
    if abs(den)<1e-12:return None
    v=(dot(v1,v1)*dot(v2,v0)-dot(v0,v1)*dot(v2,v1))/den
    w=(dot(v0,v0)*dot(v2,v1)-dot(v0,v1)*dot(v2,v0))/den
    weights=[1-v-w,v,w]
    projection=[sum(weights[i]*tri[i][j] for i in range(3)) for j in range(3)]
    # A fixed barycentric epsilon is a different physical tolerance on every
    # triangle. Thin platform fan triangles need the stated 0.02 cm edge bound.
    twice_area=math.sqrt(dot(cross(v0,v1),cross(v0,v1)))
    tolerances=[.02*math.dist(tri[(i+1)%3],tri[(i+2)%3])/twice_area for i in range(3)]
    return weights if all(value>=-tol for value,tol in zip(weights,tolerances)) and math.dist(p,projection)<.02 else None

def area2(poly):
    return sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(poly,poly[1:]+poly[:1]))/2 if len(poly)>2 else 0.

def overlap2(poly,clip):
    if area2(clip)<0:clip=list(reversed(clip))
    for a,b in zip(clip,clip[1:]+clip[:1]):
        def side(p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
        result=[]
        for p,q in zip(poly,poly[1:]+poly[:1]):
            dp,dq=side(p),side(q)
            if dp>=0:result.append(p)
            if (dp>=0)!=(dq>=0):
                f=dp/(dp-dq);result.append([p[i]+f*(q[i]-p[i]) for i in range(2)])
        poly=result
        if not poly:return 0.
    return abs(area2(poly))

def subtract_box(poly,gate):
    # Sequential half-space partitions give disjoint exterior fragments. Doing
    # this for each cutter measures their UNION, including overlapping runouts.
    exterior=[];remaining=poly;b=limits(gate)
    for axis in range(3):
        for side in (0,1):
            sign=1 if side==0 else -1;bound=b[2*axis+side]
            def clip(keep):
                result=[]
                for p,q in zip(remaining,remaining[1:]+remaining[:1]):
                    dp=(local(p,gate)[axis]-bound)*sign*keep;dq=(local(q,gate)[axis]-bound)*sign*keep
                    if dp>=0:result.append(p)
                    if (dp>=0)!=(dq>=0):
                        f=dp/(dp-dq);result.append([p[i]+f*(q[i]-p[i]) for i in range(3)])
                return result
            outside=clip(-1);within=clip(1)
            if area(outside)>1e-8:exterior.append(outside)
            remaining=within
            if area(remaining)<1e-8:return exterior
    return exterior

def retained_area(points,gates):
    pieces=[points]
    for gate in gates:pieces=[piece for poly in pieces for piece in subtract_box(poly,gate)]
    return sum(area(poly) for poly in pieces)

def clipped_area(points,gate,shrink=0):
    b=limits(gate)
    bounds=[[b[2*i]+shrink for i in range(3)],[b[2*i+1]-shrink for i in range(3)]]
    return area(inside_polygon([local(p,gate) for p in points],bounds))

def is_cap(points,gates):
    for g in gates:
        ps=[local(p,g) for p in points];b=limits(g)
        if all(b[2*i]-.02<=p[i]<=b[2*i+1]+.02 for p in ps for i in range(3)):
            if any(all(abs(p[i]-b[2*i+side])<.02 for p in ps) for i in range(3) for side in (0,1)):return True
    return False

def verify(original,current,gates):
    wanted={r['tid']:retained_area(r['positions'],gates) for r in original}
    got={r['tid']:0. for r in original}
    bounds=[(r,[min(p[i] for p in r['positions'])-.02 for i in range(3)],
              [max(p[i] for p in r['positions'])+.02 for i in range(3)]) for r in original]
    caps=0
    fragments={r['tid']:[] for r in original}
    for row in current:
        points=row['positions'];size=area(points)
        assert size>1e-8,'Degenerate wall result'
        assert all(clipped_area(points,g,.02)<.01 for g in gates),'Triangle crosses passage interior'
        if is_cap(points,gates):
            assert row['materialId']==0,'Unexpected cap material'
            caps+=1;continue
        candidates=[]
        face=cross(sub(points[1],points[0]),sub(points[2],points[0]))
        for old,lo,hi in bounds:
            if any(not lo[i]<=p[i]<=hi[i] for p in points for i in range(3)):continue
            ws=[bary(p,old['positions']) for p in points]
            if any(w is None for w in ws):continue
            sf=cross(sub(old['positions'][1],old['positions'][0]),sub(old['positions'][2],old['positions'][0]))
            if dot(face,sf)<=0 or row['materialId']!=old['materialId'] or set(row['attrs'])!=set(old['attrs']):continue
            okay=True
            for name,values in old['attrs'].items():
                for i,w in enumerate(ws):
                    value=[sum(w[j]*values[j][k] for j in range(3)) for k in range(len(values[0]))]
                    if name=='normal':
                        length=math.sqrt(dot(value,value))
                        if length:value=[v/length for v in value]
                    if math.dist(value,row['attrs'][name][i])>.002:okay=False
            if okay:candidates.append(old)
        assert candidates,('Source attributes/winding/position mismatch',row['tid'],points)
        old=min(candidates,key=lambda r:got[r['tid']]/max(wanted[r['tid']],1e-9))
        got[old['tid']]+=size
        fragments[old['tid']].append(points)
    maximum=0.
    for old in original:
        # Containment + disjoint fragments + area establishes coverage; area
        # alone could hide an equal-sized overlap and missing patch.
        normal=cross(sub(old['positions'][1],old['positions'][0]),sub(old['positions'][2],old['positions'][0]))
        drop=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=drop]
        scale=math.sqrt(dot(normal,normal))/max(abs(normal[drop]),1e-20)
        pieces=[[[p[i] for i in axes] for p in tri] for tri in fragments[old['tid']]]
        for i,piece in enumerate(pieces):
            for other in pieces[i+1:]:assert overlap2(piece,other)*scale<.01,('Overlapping output fragments',old['tid'])
        perimeter=sum(math.dist(a,b) for a,b in zip(old['positions'],old['positions'][1:]+old['positions'][:1]))
        error=abs(got[old['tid']]-wanted[old['tid']]);maximum=max(maximum,error)
        assert error<max(1.,perimeter*.01),('Exterior area lost/added',old['tid'],wanted[old['tid']],got[old['tid']],error)
    return dict(originalTriangles=len(original),resultTriangles=len(current),authoredCapTriangles=caps,
                maximumPerTriangleAreaErrorCm2=maximum,areaTolerance='max(1 cm2, original perimeter * 0.01 cm)',
                positionToleranceCm=.02,attributeTolerance=.002,
                attributes='All existing UV sets, normalized normals, vertex colors, material IDs and winding preserved on surviving source surfaces')

def main():
    import unreal as ue
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt=OUT/('wall-surfaces-'+stamp+'.json')
    report=dict(status='started',scriptSha256=sha(Path(__file__)),walls=[])
    map_before=sha(disk(MAP,'.umap'));protected={}
    try:
        native=Native();gates=json.loads((OUT/'plan.json').read_text())['gates']
        for spec in json.loads((OUT/'wall-cuts.json').read_text())['walls']:
            for key,hash_key in [('mesh','sha256'),('twin','twinSha256')]:
                assert sha(disk(spec[key]))==spec[hash_key]
                protected[spec[key]]=spec[hash_key]
            original=rows_with_attributes(native,native.source_dynamic_mesh(ue.load_asset(spec['mesh'])))
            current=rows_with_attributes(native,native.source_dynamic_mesh(ue.load_asset(spec['twin'])))
            result=verify(original,current,[g for g in gates if g['osmId'] in spec['gateIds']])
            report['walls'].append(dict(label=spec['label'],**result));receipt.write_text(json.dumps(report,indent=2)+'\n')
        report['status']='passed'
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();ue.log_error(report['error'])
    finally:
        report['mapUnchanged']=map_before==sha(disk(MAP,'.umap'))
        report['assetsUnchanged']=all(sha(disk(p))==h for p,h in protected.items())
        if not report['mapUnchanged'] or not report['assetsUnchanged']:report['status']='failed-hash-guard'
        receipt.write_text(json.dumps(report,indent=2)+'\n');ue.SystemLibrary.quit_editor()

if __name__=='__main__':main()

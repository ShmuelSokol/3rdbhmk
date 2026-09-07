"""Independent exported-OBJ readback and orthographic geometry preview, stdlib only."""
import ast
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
manifest=json.loads((HERE/'geometry-manifest.json').read_text())
ast.parse((ROOT/'Scripts/create_sanctuary_doors.py').read_text())
checks=[]
for r in manifest['meshes']:
    p=HERE/r['file']; assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
    verts=[]; uvs=[]; normals=[]; faces=[]
    for line in p.read_text().splitlines():
        cols=line.split()
        if cols[0]=='v': verts.append(tuple(map(float,cols[1:])))
        elif cols[0]=='vt': uvs.append(tuple(map(float,cols[1:])))
        elif cols[0]=='vn': normals.append(tuple(map(float,cols[1:])))
        elif cols[0]=='f': faces.append([tuple(int(v)-1 for v in c.split('/')) for c in cols[1:]])
    assert len(faces)==r['triangles']
    for face in faces:
        assert len(face)==3
        for v,t,n in face:
            assert 0<=v<len(verts) and 0<=t<len(uvs) and 0<=n<len(normals)
            assert abs(sum(x*x for x in normals[n])-1)<1e-7
        a,b,c=[verts[f[0]] for f in face]
        ab=[b[i]-a[i] for i in range(3)]; ac=[c[i]-a[i] for i in range(3)]
        cr=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
        area=math.sqrt(sum(x*x for x in cr)); assert area>1e-8
        assert sum(cr[i]*normals[face[0][2]][i] for i in range(3))/area>.999999
        a,b,c=[uvs[f[1]] for f in face]
        assert abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))>1e-10
    canonical=[(x,-y,z) for x,y,z in verts]
    bounds={k:[fn(v[i] for v in canonical) for i in range(3)] for k,fn in [('min',min),('max',max)]}
    error=max(abs(bounds[k][i]-r['bounds_cm'][k][i]) for k in bounds for i in range(3))
    assert error<1e-7
    checks.append(dict(mesh=r['name'],triangles=len(faces),bounds_error_cm=error,normals_and_uvs='PASS'))

editable=json.loads((HERE/'editable-meshes.json').read_text())
def render(prefix,width,height,pixelscale,offset,filename):
    rgb=bytearray([23,27,31]*(width*height)); zbuffer=[-1e9]*(width*height)
    for name,parts in editable.items():
        if not name.startswith(prefix): continue
        base=(128,77,38)
        if 'Palm' in name or 'Hardware' in name or 'Fixings' in name: base=(220,170,79)
        if 'Cloth' in name: base=(65,48,123)
        if 'Hem' in name: base=(159,46,68)
        for part in parts:
            v=part['vertices_cm']
            for ids in part['triangles']:
                a,b,c=[v[i] for i in ids]
                ab=[b[i]-a[i] for i in range(3)]; ac=[c[i]-a[i] for i in range(3)]
                n=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
                ln=math.sqrt(sum(x*x for x in n))
                light=.4+.6*max(0,(-.4*n[0]+.75*n[1]+.5*n[2])/ln)
                color=bytes(min(255,int(x*light)) for x in base)
                pts=[(offset+p[0]*pixelscale,height-25-p[2]*pixelscale,p[1]) for p in (a,b,c)]
                x0,y0,d0=pts[0]; x1,y1,d1=pts[1]; x2,y2,d2=pts[2]
                det=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
                if abs(det)<1e-9: continue
                for y in range(max(0,int(min(q[1] for q in pts))),min(height,int(max(q[1] for q in pts))+1)):
                    for x in range(max(0,int(min(q[0] for q in pts))),min(width,int(max(q[0] for q in pts))+1)):
                        w0=((y1-y2)*(x+.5-x2)+(x2-x1)*(y+.5-y2))/det
                        w1=((y2-y0)*(x+.5-x2)+(x0-x2)*(y+.5-y2))/det
                        w2=1-w0-w1
                        if min(w0,w1,w2)<0: continue
                        depth=w0*d0+w1*d1+w2*d2; index=y*width+x
                        if depth>zbuffer[index]: zbuffer[index]=depth; rgb[index*3:index*3+3]=color
    def chunk(kind,data):
        return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    scan=b''.join(b'\x00'+rgb[y*width*3:(y+1)*width*3] for y in range(height))
    (HERE/filename).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b''))

render('SM_Paroches',620,540,1.5,310,'paroches-preview.png')
render('SM_Kodesh',260,720,2.2,30,'kodesh-leaf-preview.png')
render('SM_Heichal',180,1100,.42,55,'heichal-leaf-preview.png')

# Reconcile source fit independently from editable bounds, without engine assumptions.
assert manifest['openings']['Heichal']['width_cm']==500
assert manifest['openings']['Heichal']['height_cm']==2500
assert manifest['openings']['Kodesh']['width_cm']==350
assert manifest['openings']['Kodesh']['height_cm']==300
for room in ('Heichal','Kodesh'):
    r=next(r for r in manifest['meshes'] if r['name']=='SM_'+room+'FoldingLeafV1')
    nominal=manifest['openings'][room]['width_cm']/4
    assert abs(r['bounds_cm']['min'][0]-.5)<1e-7
    assert abs(r['bounds_cm']['max'][0]-(nominal-.5))<1e-7
    assert abs(r['bounds_cm']['max'][2]-(manifest['openings'][room]['height_cm']-4))<1e-7
receipt=dict(status='PASS_OFFLINE_ONLY',checks=checks,source_fit='PASS_nominal_four_leaves_with1cm_edge_gaps_and2cm_vertical_clearances',
    previews=['paroches-preview.png','kodesh-leaf-preview.png','heichal-leaf-preview.png'],
    limitations='Original software geometry previews, illustrative colors only. Not native shading, folding sweep, character clearance, cloth simulation or final textile/cherub design acceptance.')
(HERE/'offline-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))

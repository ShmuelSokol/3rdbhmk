"""Independent exported-OBJ readback and orthographic geometry preview, stdlib only."""
import ast
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

HERE=Path(__file__).resolve().parent/'PalmReliefV1'
ROOT=HERE.parents[2]
manifest=json.loads((HERE/'geometry-manifest.json').read_text())
ast.parse((ROOT/'Scripts/create_sanctuary_reliefs.py').read_text())
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

# Render authored source geometry, no native engine or external imagery involved.
W,H=440,860
rgb=bytearray([23,27,31]*(W*H))
zbuffer=[-1e9]*(W*H)
editable=json.loads((HERE/'editable-meshes.json').read_text())
for name,parts in editable.items():
    base=(113,66,34) if 'Backing' in name else (205,153,74)
    for part in parts:
        v=part['vertices_cm']
        for ids in part['triangles']:
            a,b,c=[v[i] for i in ids]
            ab=[b[i]-a[i] for i in range(3)]; ac=[c[i]-a[i] for i in range(3)]
            n=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
            ln=math.sqrt(sum(x*x for x in n))
            light=.45+.55*max(0,(-.4*n[0]+.75*n[1]+.5*n[2])/ln)
            color=bytes(min(255,int(x*light)) for x in base)
            pts=[(W/2+p[0]*2.95,H-45-p[2]*2.95,p[1]) for p in (a,b,c)]
            x0,y0,d0=pts[0]; x1,y1,d1=pts[1]; x2,y2,d2=pts[2]
            det=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
            if abs(det)<1e-9: continue
            for y in range(max(0,int(min(q[1] for q in pts))),min(H,int(max(q[1] for q in pts))+1)):
                for x in range(max(0,int(min(q[0] for q in pts))),min(W,int(max(q[0] for q in pts))+1)):
                    w0=((y1-y2)*(x+.5-x2)+(x2-x1)*(y+.5-y2))/det
                    w1=((y2-y0)*(x+.5-x2)+(x0-x2)*(y+.5-y2))/det
                    w2=1-w0-w1
                    if min(w0,w1,w2)<0: continue
                    depth=w0*d0+w1*d1+w2*d2; index=y*W+x
                    if depth>zbuffer[index]:
                        zbuffer[index]=depth; rgb[index*3:index*3+3]=color
def chunk(kind,data):
    return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
scan=b''.join(b'\x00'+rgb[y*W*3:(y+1)*W*3] for y in range(H))
(HERE/'orthographic-preview.png').write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',W,H,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b''))
receipt=dict(status='PASS_OFFLINE_ONLY',checks=checks,preview='orthographic-preview.png',
    preview_limit='Software orthographic source preview with illustrative wood/gold colors, not a native render or material acceptance')
(HERE/'offline-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))

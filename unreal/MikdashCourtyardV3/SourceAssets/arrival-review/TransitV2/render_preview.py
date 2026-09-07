"""Original stdlib depth-buffer offline previews; not Unreal rendering evidence."""
import json
import math
from pathlib import Path
import struct
import zlib

FOLDER=Path(__file__).resolve().parent
palette=json.loads((FOLDER/'offline-checks.json').read_text())['palette']


def render(label,cutaway=False):
    data=json.loads((FOLDER/(label.lower()+'-editable.mesh.json')).read_text());parts=data['parts']
    if cutaway:
        prefixes=('RoofCrown','RoofHVAC','HVACLouvre','InteriorCeiling','UpperFascia','CanopyRoof','CanopyFascia')
        parts=[p for p in parts if not p['name'].startswith(prefixes)]
    w,h=1400,840;scale=.98 if label=='Bus' else .14
    def uncentered(v):
        x,y,z=v
        return (scale*(.82*x-.7*y),scale*(.18*x+.34*y-.95*z),.665*x+.779*y+.4048*z)
    pts=[uncentered(v) for p in parts for v in p['vertices']]
    cx=w/2-(min(v[0] for v in pts)+max(v[0] for v in pts))/2
    cy=h/2-(min(v[1] for v in pts)+max(v[1] for v in pts))/2
    pixels=bytearray(bytes((196,203,208))*w*h);depth=[-1e30]*(w*h);faces=[]
    for p in parts:
        for f in p['triangles']:
            raw=[p['vertices'][i] for i in f];a,b,c=raw
            ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)]
            n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
            nl=math.sqrt(sum(v*v for v in n));light=.4+.6*max(0,sum(n[i]*[.3,.5,.81][i] for i in range(3))/nl)
            col=bytes(max(0,min(255,round(255*(v*light)**(1/2.2)))) for v in palette[p['material']][0])
            pts=[uncentered(v) for v in raw];pts=[(v[0]+cx,v[1]+cy,v[2]) for v in pts]
            transparent=p['material']=='Glass';faces.append((transparent,sum(v[2] for v in pts)/3,pts,col))
    # Draw opaque surfaces first, then approximate sorted transparent panes.
    for transparent,_,pts,col in sorted(faces,key=lambda f:(f[0],f[1])):
        for y in range(max(0,math.ceil(min(v[1] for v in pts))),min(h,math.ceil(max(v[1] for v in pts)))):
            yy=y+.5;cuts=[]
            for a,b in zip(pts,pts[1:]+pts[:1]):
                if min(a[1],b[1])<=yy<max(a[1],b[1]):
                    t=(yy-a[1])/(b[1]-a[1]);cuts.append((a[0]+t*(b[0]-a[0]),a[2]+t*(b[2]-a[2])))
            if len(cuts)!=2:continue
            cuts.sort();(x0,d0),(x1,d1)=cuts
            if x1-x0<1e-9:continue
            for x in range(max(0,math.ceil(x0)),min(w,math.ceil(x1))):
                z=d0+(x+.5-x0)*(d1-d0)/(x1-x0);idx=y*w+x
                if z>depth[idx]:
                    if transparent:
                        for k in range(3):pixels[idx*3+k]=round(.18*col[k]+.82*pixels[idx*3+k])
                    else:depth[idx]=z;pixels[idx*3:idx*3+3]=col
    def chunk(k,d):return struct.pack('!I',len(d))+k+d+struct.pack('!I',zlib.crc32(k+d)&0xffffffff)
    raw=b''.join(b'\0'+pixels[y*w*3:(y+1)*w*3] for y in range(h))
    suffix='cutaway' if cutaway else 'exterior'
    (FOLDER/(label.lower()+'-'+suffix+'-offline.png')).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b''))


if __name__=='__main__':
    for label in ('Bus','Station'):
        for cutaway in (False,True):render(label,cutaway)

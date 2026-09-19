"""Compare native skeletal pose exports to lossless PNG16 VAT data offline."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import zlib
import numpy as np

def png16(path):
    data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
    w,h,bits,kind,compression,filtering,interlace=struct.unpack('>IIBBBBB',data[16:29])
    assert (bits,kind,compression,filtering,interlace)==(16,6,0,0,0)
    offset=8;parts=[]
    while offset<len(data):
        size=struct.unpack('>I',data[offset:offset+4])[0];chunk=data[offset+4:offset+8+size]
        assert zlib.crc32(chunk)&0xffffffff==struct.unpack('>I',data[offset+8+size:offset+12+size])[0]
        if chunk[:4]==b'IDAT':parts.append(chunk[4:])
        offset+=size+12
    assert offset==len(data)
    raw=zlib.decompress(b''.join(parts));stride=w*8;assert len(raw)==h*(stride+1)
    image=np.empty((h,stride),dtype=np.uint8)
    for y in range(h):
        kind=raw[y*(stride+1)];scan=np.frombuffer(raw,dtype=np.uint8,count=stride,offset=y*(stride+1)+1).copy()
        previous=image[y-1] if y else np.zeros(stride,dtype=np.uint8)
        if kind==1:scan=np.cumsum(scan.reshape(w,8),axis=0,dtype=np.uint32).astype(np.uint8).reshape(stride)
        elif kind==2:scan=(scan.astype(np.uint16)+previous).astype(np.uint8)
        elif kind in (3,4):
            values=scan.tolist();up=previous.tolist()
            for x in range(stride):
                a=values[x-8] if x>=8 else 0;b=up[x];c=up[x-8] if x>=8 else 0
                if kind==3:prediction=(a+b)//2
                else:
                    p=a+b-c;pa=abs(p-a);pb=abs(p-b);pc=abs(p-c)
                    prediction=a if pa<=pb and pa<=pc else (b if pb<=pc else c)
                values[x]=(values[x]+prediction)&255
            scan=np.array(values,dtype=np.uint8)
        else:assert kind==0
        image[y]=scan
    return image.reshape(h,w,8).view('>u2').reshape(h,w,4).astype(np.float64)/65535.

def write_png16(path,array):
    height,width,channels=array.shape;assert channels==4
    pixels=np.rint(array*65535).astype('>u2')
    def chunk(name,payload):return struct.pack('>I',len(payload))+name+payload+struct.pack('>I',zlib.crc32(name+payload)&0xffffffff)
    raw=b''.join(b'\0'+pixels[y].tobytes() for y in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,16,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
    assert np.array_equal(png16(path),pixels.astype(np.float64)/65535.)

def run(path,write_correction=False):
    path=Path(path);folder=path.parent;receipt=json.loads(path.read_text())
    assert receipt['status']=='exported-posed-normals' and receipt['protectedUnchanged']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,digest in receipt['files'].items():assert sha(folder/name)==digest
    assert sha(folder/receipt['normalTexture'])==receipt['normalTextureSha256']
    normals=png16(folder/receipt['normalTexture'])
    corrected=normals.copy() if write_correction else None
    modified=np.zeros(normals.shape[:2],dtype=bool) if write_correction else None
    positions=png16(folder/next(n for n in receipt['files'] if n.endswith('-position.png')))
    layout=receipt['walkBake'];assert normals.shape==positions.shape==(layout['height'],layout['width'],4)
    def summary(a):return dict(count=len(a),mean=float(np.mean(a)),median=float(np.median(a)),p95=float(np.percentile(a,95)),maximum=float(np.max(a)))
    report=dict(scope='Source-model CPU skeletal normals versus decoded stored VAT normals, not a GPU rendering or continuous-clearance claim.',poseReceipt=path.name,poseReceiptSha256=sha(path),frames=[])
    for pose in receipt['poses']:
        with gzip.open(folder/pose['file'],'rt',encoding='utf-8') as stream:rows=json.load(stream)['rows']
        assert len(rows)==pose['uniqueRows']
        materials=np.array([r[0] for r in rows]);reference=np.array([r[1] for r in rows]);uv=np.array([r[2] for r in rows]);expected_p=np.array([r[3] for r in rows]);expected_n=np.array([r[4] for r in rows])
        pixel=uv*np.array([layout['width'],layout['height']]);xy=np.floor(pixel).astype(int)
        assert np.max(np.abs(pixel-xy-.5))<.002
        xy[:,1]+=pose['frame']*layout['rowsPerFrame'];assert np.all(xy>=0) and np.all(xy<np.array([layout['width'],layout['height']]))
        decoded_p=positions[xy[:,1],xy[:,0],:3]*np.array(layout['sizeBBox'])+np.array(layout['minBBox'])+reference
        decoded_n=normals[xy[:,1],xy[:,0],:3]*2.-1.
        assert np.min(np.linalg.norm(decoded_n,axis=1))>.9
        decoded_n/=np.linalg.norm(decoded_n,axis=1)[:,None];expected_n/=np.linalg.norm(expected_n,axis=1)[:,None]
        if write_correction:
            assert len(set(map(tuple,xy)))==len(rows)
            corrected[xy[:,1],xy[:,0],:3]=(expected_n+1.)*.5
            modified[xy[:,1],xy[:,0]]=True
        position_error=np.linalg.norm(decoded_p-expected_p,axis=1)
        angles=np.degrees(np.arccos(np.clip(np.sum(decoded_n*expected_n,axis=1),-1,1)))
        groups={str(m):dict(positionErrorCm=summary(position_error[materials==m]),normalAngleDegrees=summary(angles[materials==m])) for m in sorted(set(materials))}
        lower=np.isin(materials,[3,4]) & (reference[:,2]<95.)
        groups['lowerCloth']=dict(positionErrorCm=summary(position_error[lower]),normalAngleDegrees=summary(angles[lower]))
        worst=np.argsort(angles)[-20:][::-1]
        report['frames'].append(dict(frame=pose['frame'],positionErrorCm=summary(position_error),normalAngleDegrees=summary(angles),overFiveDegrees=int(np.sum(angles>5)),groups=groups,worst=[dict(material=int(materials[i]),reference=reference[i].tolist(),vatUV=uv[i].tolist(),expectedNormal=expected_n[i].tolist(),bakedNormal=decoded_n[i].tolist(),angle=float(angles[i]),positionErrorCm=float(position_error[i])) for i in worst]))
    report['status']='compared-posed-normals'
    output=path.with_name(path.stem.replace('posed-normals-','posed-correction-' if write_correction else 'posed-comparison-')+'.json');assert not output.exists()
    if write_correction:
        texture=output.with_name(output.stem+'-normal.png');assert not texture.exists()
        write_png16(texture,corrected)
        recovered=png16(texture)
        assert np.array_equal(recovered[~modified],normals[~modified]) and np.array_equal(recovered[:,:,3],normals[:,:,3])
        report['correction']=dict(file=texture.name,sha256=sha(texture),frames=receipt['frames'],assignedTexels=int(np.sum(modified)),unselectedTexelsAndAlphaUnchanged=True,scope='ONLY four exact frozen phases are corrected. Other phases retain old normals. Diagnostic texture; never adopt into runtime.')
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(output)
    for frame in report['frames']:print(frame['frame'],frame['positionErrorCm'],frame['normalAngleDegrees'],frame['groups']['lowerCloth'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('pose_receipt');parser.add_argument('--write-correction',action='store_true');args=parser.parse_args();run(args.pose_receipt,args.write_correction)

import struct, zlib
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

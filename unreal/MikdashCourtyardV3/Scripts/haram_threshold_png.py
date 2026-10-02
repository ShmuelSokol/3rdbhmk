"""Strict study PNG validation and sanitization; no Unreal dependencies."""
import hashlib
from pathlib import Path
import struct
import zlib


def require(ok, message):
    if not ok:
        raise ValueError(message)


def decode_bytes(data):
    require(len(data) <= 16*1024*1024 and data[:8] == b'\x89PNG\r\n\x1a\n', 'Invalid PNG header/size')
    offset, payload, tags = 8, bytearray(), []
    while True:
        require(offset+12 <= len(data), 'Missing/truncated PNG chunk')
        size = int.from_bytes(data[offset:offset+4], 'big')
        tag = data[offset+4:offset+8]
        end = offset+12+size
        require(end <= len(data), 'Truncated PNG chunk body')
        body = data[offset+8:end-4]
        require(zlib.crc32(tag+body) & 0xffffffff == int.from_bytes(data[end-4:end], 'big'), 'PNG CRC mismatch')
        # Exporter output needs only IHDR/IDAT/IEND. Reject unexpected ancillary data.
        require(tag in (b'IHDR', b'IDAT', b'IEND'), 'Unexpected PNG chunk')
        if not tags:
            require(tag == b'IHDR' and size == 13, 'Missing IHDR')
            require(struct.unpack('>IIBBBBB', body) == (960,720,8,6,0,0,0), 'Unexpected PNG format')
        elif tag == b'IHDR':
            raise ValueError('Duplicate IHDR')
        if tag == b'IDAT':
            payload.extend(body)
        tags.append(tag)
        offset = end
        if tag == b'IEND':
            require(size == 0 and b'IDAT' in tags, 'Invalid IEND/image data')
            break
    stride, height = 960*4, 720
    expected = (stride+1)*height
    inflater = zlib.decompressobj()
    raw = inflater.decompress(payload, expected+1)
    require(len(raw) == expected and inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail,
            'Invalid or oversized PNG zlib stream')
    previous, rgba = bytearray(stride), bytearray()
    for y in range(height):
        kind = raw[y*(stride+1)]
        row = bytearray(raw[y*(stride+1)+1:(y+1)*(stride+1)])
        require(0 <= kind <= 4, 'Invalid PNG filter')
        if kind:
            for x in range(stride):
                a = row[x-4] if x >= 4 else 0
                b = previous[x]
                c = previous[x-4] if x >= 4 else 0
                if kind == 1: value = a
                elif kind == 2: value = b
                elif kind == 3: value = (a+b)//2
                else:
                    p = a+b-c
                    pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
                    value = a if pa <= pb and pa <= pc else b if pb <= pc else c
                row[x] = (row[x]+value) & 255
        rgba.extend(row)
        previous = row
    info = dict(fileSha256=hashlib.sha256(data).hexdigest(),
        pngThroughIendSha256=hashlib.sha256(data[:offset]).hexdigest(),
        rgbaSha256=hashlib.sha256(rgba).hexdigest(), trailingBytes=len(data)-offset,
        visibleRgbPixels=sum(max(rgba[i:i+3]) > 8 for i in range(0,len(rgba),4)), crcValid=True)
    return rgba, info, offset


def decode(path):
    rgba, info, _ = decode_bytes(Path(path).read_bytes())
    return rgba, info


def sanitize_new_export(raw_path, destination):
    """Only fresh staging exports; final files are exclusive-created, never replaced."""
    raw_path, destination = Path(raw_path), Path(destination)
    require(raw_path.name.endswith('.local-export.png') and raw_path.parent == destination.parent,
            'Only a sibling local staging export may be sanitized')
    require(not destination.exists(), 'Existing capture must not be overwritten')
    data = raw_path.read_bytes()
    _, info, end = decode_bytes(data)
    with destination.open('xb') as stream:
        stream.write(data[:end])
    require(destination.stat().st_size == end and hashlib.sha256(destination.read_bytes()).hexdigest() == info['pngThroughIendSha256'],
            'Sanitized capture write mismatch')
    raw_path.unlink()
    return dict(sha256=info['pngThroughIendSha256'], rgbaSha256=info['rgbaSha256'],
                removedTrailingBytes=info['trailingBytes'], pngCrcAndDecodeChecked=True,
                trailingBytes=0, visibleRgbPixels=info['visibleRgbPixels'])

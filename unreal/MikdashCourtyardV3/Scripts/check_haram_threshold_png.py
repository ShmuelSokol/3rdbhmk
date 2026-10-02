"""Offline sanitizer regression checks; writes only temporary study-cache files."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib
sys.dont_write_bytecode = True
from haram_threshold_png import decode_bytes, sanitize_new_export


def chunk(tag, body):
    return struct.pack('>I',len(body))+tag+body+struct.pack('>I',zlib.crc32(tag+body)&0xffffffff)


def main():
    root=Path(__file__).resolve().parents[1]
    out=root/'SourceAssets/context-review/HaramThresholdSidesV1'
    header=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',960,720,8,6,0,0,0))
    raw=(b'\0'+bytes([25,50,75,255])*960)*720
    png=header+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
    rgba, info, end=decode_bytes(png+b'PRIVATE-ALLOCATION-BYTES')
    assert end==len(png) and len(rgba)==960*720*4 and info['trailingBytes']==24
    invalid=[png[:-1], png[:40], png[:-12], png[:20]+bytes([png[20]^1])+png[21:],
             header+chunk(b'IDAT',zlib.compress(b'\x05'+raw[1:]))+chunk(b'IEND',b''),
             header+chunk(b'IDAT',zlib.compress(raw+b'X'))+chunk(b'IEND',b'')]
    for data in invalid:
        try: decode_bytes(data)
        except (ValueError,zlib.error): pass
        else: raise AssertionError('Invalid PNG accepted')
    cache=out/'verification-cache'
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as tmp:
        staging=Path(tmp)/'sample.local-export.png';final=Path(tmp)/'sample.png'
        staging.write_bytes(png+b'PRIVATE-ALLOCATION-BYTES')
        proof=sanitize_new_export(staging,final)
        assert final.read_bytes()==png and not staging.exists() and proof['trailingBytes']==0
        staging.write_bytes(png)
        try: sanitize_new_export(staging,final)
        except ValueError: pass
        else: raise AssertionError('Existing PNG overwritten')
        assert staging.exists() and final.read_bytes()==png
    checked=[]
    audit=json.loads((out/'pixel-audit07.json').read_text(encoding='utf-8-sig'))
    for path in sorted((out/'review07-clean-png').glob('*.png')):
        # Coordinator contact sheets are separate dimensions, not engine captures.
        if path.name not in [name.split('/',1)[1] for name in audit['images']]: continue
        _, info, end=decode_bytes(path.read_bytes())
        assert info['trailingBytes']==0 and info['rgbaSha256']==audit['images']['verify/'+path.name]['rgbaSha256']
        checked.append(path.name)
    assert len(checked)==9
    print('PASS: CRC/decode/truncation/filter/size rejection; exact trim; no overwrite; 9 clean07 payloads match preserved pixel audit')


if __name__=='__main__': main()

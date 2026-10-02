"""Private inherited-pipe v2 envelope. Syntax is not transport authentication.

Outer frame remains BE32 length <=4092. Body: MKS2, BE32 v1 body length,
unchanged v1 JSON bytes, BE16 root length, canonical ASCII root, then lowercase
fixed hex: volume(8), file ID(16), PID(8), FILETIME(16), event handle(16),
slot count(2), generation(32). No floating point conversion of kernel identities.
"""
import json
import re
import struct
from runtime_candidate05.bootstrap_record import inspect_private_record
from runtime_settings03.launcher_contract03 import launch_inputs
from session_core import SessionError

WIDTHS=(('volume',8),('file_id',16),('pid',8),('created',16),('event',16),('slots',2))

def hex_uint(value,width):
    if type(value) is not int or not 0<=value<1<<(width*4):raise ValueError('Integer range')
    return format(value,f'0{width}x')

def parse_hex(value,width):
    if type(value) is not str or re.fullmatch('[0-9a-f]{'+str(width)+'}',value) is None:
        raise ValueError('Noncanonical fixed hex')
    return int(value,16)

def encode(v1,owner,now,descriptor):
    inspect_private_record(v1,owner,now)
    if set(descriptor)!={'root','generation'}|{n for n,_ in WIDTHS}:raise ValueError('Descriptor shape')
    root=descriptor['root']
    if launch_inputs(root,owner.settings_slot,owner.save_prefix,descriptor['slots'])['root']!=root:
        raise ValueError('Noncanonical root')
    raw=root.encode('ascii')
    tail=''.join(hex_uint(descriptor[n],w) for n,w in WIDTHS)+descriptor['generation']
    body=b'MKS2'+struct.pack('!I',len(v1)-4)+v1[4:]+struct.pack('!H',len(raw))+raw+tail.encode('ascii')
    frame=struct.pack('!I',len(body))+body
    decode(frame,owner,now)
    return frame

def decode(frame,owner,now):
    try:
        if type(frame) is not bytes or not 4<len(frame)<=4096 or struct.unpack('!I',frame[:4])[0]!=len(frame)-4:
            raise ValueError()
        if frame[4:8]!=b'MKS2':raise ValueError()
        n=struct.unpack('!I',frame[8:12])[0]
        if not 2<=n<=4092 or 14+n>len(frame):raise ValueError()
        v1=struct.pack('!I',n)+frame[12:12+n]
        original=inspect_private_record(v1,owner,now)
        size=struct.unpack('!H',frame[12+n:14+n])[0]
        if not 4<=size<=240 or len(frame)!=14+n+size+98:raise ValueError()
        root=frame[14+n:14+n+size].decode('ascii')
        tail=frame[14+n+size:].decode('ascii');d={'root':root};p=0
        for name,width in WIDTHS:d[name]=parse_hex(tail[p:p+width],width);p+=width
        d['generation']=tail[p:];parse_hex(d['generation'],32)
        if d['generation']=='0'*32 or any(d[k]==0 for k in ('pid','created','event')):raise ValueError()
        if launch_inputs(root,owner.settings_slot,owner.save_prefix,d['slots'])['root']!=root:raise ValueError()
        return original,d,v1
    except Exception:raise SessionError('Private settings v2 refused') from None

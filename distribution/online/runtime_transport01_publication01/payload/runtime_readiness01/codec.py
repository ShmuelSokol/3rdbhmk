"""MKR1 private stopped-admission envelope; unchanged MKS2 bytes nested inside.

BE32 body length, MKR1, event16 lowerhex, generation32 lowerhex, MKS2 body.
No JSON additions, public name, port, credential, or deadline extension.
"""
import struct
from runtime_settings05.codec import decode as decode_v2,hex_uint,parse_hex
from session_core import SessionError

def decode(frame,owner,now):
    try:
        if type(frame) is not bytes or not 56<len(frame)<=4096 or struct.unpack('!I',frame[:4])[0]!=len(frame)-4:raise ValueError()
        if frame[4:8]!=b'MKR1':raise ValueError()
        event=parse_hex(frame[8:24].decode('ascii'),16)
        generation=frame[24:56].decode('ascii');parse_hex(generation,32)
        nested=struct.pack('!I',len(frame)-56)+frame[56:]
        original,d,v1=decode_v2(nested,owner,now)
        if not event or event==d['event'] or generation!=d['generation']:raise ValueError()
        return nested,d,event
    except Exception:raise SessionError('Private stopped admission refused') from None

def encode(v2,owner,now,event,generation):
    try:
        body=b'MKR1'+hex_uint(event,16).encode()+generation.encode('ascii')+v2[4:]
        frame=struct.pack('!I',len(body))+body
        decode(frame,owner,now)
        return frame
    except Exception:raise SessionError('Private stopped admission refused') from None

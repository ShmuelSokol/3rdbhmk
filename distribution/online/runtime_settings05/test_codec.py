import copy,json,struct,unittest
from session_core import Ownership,SessionError
from runtime_candidate05.bootstrap_record import make_private_record,inspect_private_record
from runtime_settings05.codec import encode,decode,hex_uint,parse_hex

class CodecTests(unittest.TestCase):
    def setUp(self):
        self.o=Ownership('s','p','v','save','settings',100)
        self.v=make_private_record(self.o,19001,b'F'*32,clock=lambda:10,qpc=lambda:10)
        self.d=dict(root='C:/owned',volume=0xffffffff,file_id=2**64-1,pid=4,created=2**53+1,
                    event=8,slots=2,generation='1'*32)
    def test_roundtrip_and_v1_bytes(self):
        f=encode(self.v,self.o,10,self.d)
        _,d,v=decode(f,self.o,10)
        self.assertEqual(d,self.d);self.assertEqual(v,self.v)
        inspect_private_record(v,self.o,10)
    def test_integer_edges(self):
        for v in (0,2**53-1,2**53,2**53+1,134000000000000001,2**64-1):
            self.assertEqual(parse_hex(hex_uint(v,16),16),v)
        for v in (-1,2**64,True,1.0):
            with self.assertRaises(ValueError):hex_uint(v,16)
        for v in ('1','+000000000000001','FFFFFFFFFFFFFFFF','10000000000000000','0x00000000000000'):
            with self.assertRaises(ValueError):parse_hex(v,16)
    def test_rejections(self):
        frame=encode(self.v,self.o,10,self.d)
        for n in range(len(frame)):
            with self.assertRaises(SessionError):decode(frame[:n],self.o,10)
        for f in (frame+b'0',frame[:7]+b'3'+frame[8:],frame[:-1]+b'G'):
            with self.assertRaises(SessionError):decode(f,self.o,10)
        for field,val in (('event',0),('pid',0),('created',0),('generation','0'*32),('slots',65),('root','C:/../bad')):
            d=dict(self.d);d[field]=val
            with self.assertRaises((ValueError,SessionError)):encode(self.v,self.o,10,d)
    def test_owner_and_expiry(self):
        f=encode(self.v,self.o,10,self.d)
        with self.assertRaises(SessionError):decode(f,Ownership('s','stale','v','save','settings',100),10)
        with self.assertRaises(SessionError):decode(f,self.o,100)
    def test_unknown_duplicate_v1_rejected(self):
        for extra in ('"unknown":0,','"version":1,'):
            b=('{'+extra+self.v[5:].decode()).encode()
            with self.assertRaises(SessionError):encode(struct.pack('!I',len(b))+b,self.o,10,self.d)

if __name__=='__main__':unittest.main()

"""UE-shaped receive doubles; no sockets/native. C++ counterparts are staged.

Model includes original accept deadline and fragmented framing, not HMAC parsing
(the existing authenticated parser retains that responsibility).
"""
from pathlib import Path
import struct
import unittest


class Peer:
    def __init__(self, results): self.results=list(results); self.calls=0
    def recv(self, want):
        self.calls+=1
        success,data=self.results.pop(0) if self.results else (True,b'')
        if len(data)>want:
            self.results.insert(0,(success,data[want:])); data=data[:want]
        return success,data


class Pump:
    def __init__(self): self.end=.5; self.data=bytearray(); self.expected=4; self.closed=False; self.dispatches=0
    def tick(self, peer, now):
        if self.closed:return
        if now>=self.end:self.closed=True; return
        for _ in range(4):
            want=min(1024,self.expected-len(self.data))
            success,data=peer.recv(want)
            if not success:self.closed=True; return  # stale error never consulted
            if not data:return  # exact FSocketBSD would-block contract
            self.data.extend(data)
            if len(self.data)==4 and self.expected==4:
                n=struct.unpack('!I',self.data)[0]
                if not 2<=n<=4096:self.closed=True; return
                self.expected=n+36
            if len(self.data)==self.expected and self.expected>4:
                self.dispatches+=1; return


class StreamReadTests(unittest.TestCase):
    def test_accepted_before_first_byte_waits(self):
        p=Pump(); peer=Peer([(True,b'')]); p.tick(peer,.1)
        self.assertFalse(p.closed); self.assertEqual(peer.calls,1)
    def test_eof_false_zero_drops_even_with_stale_wouldblock(self):
        p=Pump(); peer=Peer([(True,b''),(False,b'')]); peer.last_error='SE_EWOULDBLOCK'
        p.tick(peer,.1); p.tick(peer,.2)
        self.assertTrue(p.closed); self.assertEqual(p.dispatches,0)
    def test_fragmented_prefix_body_tag_dispatch_once(self):
        frame=struct.pack('!I',2)+b'{}'+bytes(32)
        p=Pump(); peer=Peer([(True,frame[:2]),(True,b''),(True,frame[2:5]),
                            (True,b''),(True,frame[5:13]),(True,b''),(True,frame[13:])])
        for now in (.01,.1,.2,.3):p.tick(peer,now)
        self.assertEqual(p.data,frame); self.assertEqual(p.dispatches,1); self.assertFalse(p.closed)
    def test_repeated_wait_does_not_renew_deadline(self):
        p=Pump(); peer=Peer([])
        for now in (.1,.2,.499,.5):p.tick(peer,now)
        self.assertTrue(p.closed); self.assertEqual(peer.calls,3); self.assertEqual(p.end,.5)
    def test_prefix_eof_never_dispatches(self):
        p=Pump(); p.tick(Peer([(True,b'\0\0'),(False,b'')]),.1)
        self.assertTrue(p.closed); self.assertEqual(p.dispatches,0)
    def test_oversized_prefix_refused(self):
        p=Pump(); p.tick(Peer([(True,struct.pack('!I',4097))]),.1)
        self.assertTrue(p.closed)
    def test_fragment_work_is_capped_per_tick(self):
        p=Pump(); peer=Peer([(True,bytes([b])) for b in struct.pack('!I',100)+bytes(132)])
        p.tick(peer,.1); self.assertEqual(peer.calls,4); self.assertEqual(p.dispatches,0)
    def test_production_receive_uses_tested_native_seam(self):
        root=Path(__file__).resolve().parents[2]
        cpp=(root/'native/receiver04/Receiver.cpp').read_text()
        receive=cpp[cpp.index('if(!Input.Complete())'):cpp.index('if(Input.Complete()&&Output.IsEmpty())')]
        self.assertIn('ReadStream(*Peer,Buffer,Want,Read)',receive)
        self.assertNotIn('GetLastErrorCode',receive)
        self.assertIn('if(Result==StreamRead::Wait)break',receive)


if __name__=='__main__':unittest.main()

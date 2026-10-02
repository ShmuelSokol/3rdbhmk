import hashlib
import hmac
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
from dataclasses import asdict, replace
from session_core import Ownership, SessionError
from adapters.receiver03_bootstrap import make_record, PrivateBootstrapPipe
from adapters.loopback_channel import encode_frame, decode_frame

ROOT=Path(__file__).resolve().parent.parent


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.owner=Ownership('s','p','stream','save','settings',110)
        self.key=bytes(32) # public test vector only

    def record(self,owner=None,**kwargs):
        return make_record(owner or self.owner,34567,self.key,clock=lambda:100,qpc=lambda:100,**kwargs)

    def test_conservative_clock_order_and_startup_consumes_lease(self):
        order=[]
        samples=iter([100,100.02])
        def qpc():order.append('qpc');return next(samples)
        def clock():order.append('core');return 100.01
        data=make_record(self.owner,34567,self.key,clock=clock,qpc=qpc)
        self.assertEqual(order,['qpc','core','qpc'])
        self.assertEqual(struct.unpack('!I',data[:4])[0],len(data)-4)
        value=json.loads(data[4:]);self.assertAlmostEqual(value['qpc_deadline'],109.988)
        self.assertLessEqual(value['qpc_deadline'],self.owner.expires_at)
        self.assertEqual(value['clock_domain'],'windows-qpc-v1')
        self.assertEqual(value['owner'],asdict(self.owner))
        self.assertEqual(value['port'],34567)

    def test_offset_drift_backwards_and_late_sample_refused(self):
        for before,core,after in [(100,1100,100.01),(100,100.02,100.01),(100,100.001,99),(100,100.1,100.2)]:
            samples=iter([before,after])
            with self.assertRaises(SessionError):
                make_record(self.owner,34567,self.key,clock=lambda:core,qpc=lambda:next(samples))

    def test_late_startup_cannot_renew_serialized_deadline(self):
        first=self.record();value=json.loads(first[4:]);deadline=value['qpc_deadline']
        self.assertAlmostEqual(deadline,109.998)
        # Receiver uses this absolute QPC deadline, NOT now+remaining on dequeue.
        self.assertTrue(111>=deadline)
        source=(ROOT/'native/receiver03/Bootstrap.cpp').read_text()
        self.assertIn('Config.Deadline<=Fresh',source)
        self.assertNotIn('Fresh+Config.Deadline',source)

    def test_expired_huge_and_malformed_inputs_refused_without_io(self):
        for expiry in (100,99,10**400,float('nan'),float('inf'),True):
            with self.assertRaises(SessionError):self.record(replace(self.owner,expires_at=expiry))
        for session in ([],{},'x'*129,'bad/name','s\"injection'):
            with self.assertRaises(SessionError):self.record(replace(self.owner,session_id=session))
        for n in (10**400,float('nan'),-1,True):
            with self.assertRaises(SessionError):make_record(self.owner,34567,self.key,clock=lambda:n,qpc=lambda:1000)

    def test_private_pipe_one_bounded_preload_and_idempotent_close(self):
        frame=self.record()
        with patch('adapters.receiver03_bootstrap.os.pipe',return_value=(10,11)),\
             patch('adapters.receiver03_bootstrap.os.set_inheritable') as inherit,\
             patch('adapters.receiver03_bootstrap.os.write',return_value=len(frame)) as write,\
             patch('adapters.receiver03_bootstrap.os.close') as close:
            pipe=PrivateBootstrapPipe(frame)
            self.assertEqual(pipe.read_fd,10);write.assert_called_once_with(11,frame)
            self.assertEqual([c.args for c in inherit.call_args_list],[(10,False),(11,False)])
            pipe.close();pipe.close()
            self.assertEqual([c.args for c in close.call_args_list],[(11,),(10,)])

    def test_partial_preload_closes_both_handles_without_retry_or_raw_error(self):
        with patch('adapters.receiver03_bootstrap.os.pipe',return_value=(10,11)),\
             patch('adapters.receiver03_bootstrap.os.set_inheritable'),\
             patch('adapters.receiver03_bootstrap.os.write',return_value=1) as write,\
             patch('adapters.receiver03_bootstrap.os.close') as close:
            with self.assertRaisesRegex(SessionError,'^Bootstrap transfer failed$'):PrivateBootstrapPipe(self.record())
            self.assertEqual(write.call_count,1)
            self.assertEqual(set(c.args[0] for c in close.call_args_list),{10,11})

    def test_native_embedded_vector_matches_frozen_real_encoder(self):
        vectors=json.loads((ROOT/'native/receiver03/public-test-vectors.json').read_text())
        frame=encode_frame(vectors['request'],bytes(32),b'mikdash-request-v1\0')
        self.assertEqual(frame.hex(),vectors['requestFrameHex'])
        body=json.dumps(vectors['request'],sort_keys=True,separators=(',',':')).encode('ascii')
        expected=hmac.new(bytes(32),b'mikdash-request-v1\0'+body,hashlib.sha256).digest()
        self.assertEqual(frame[-32:],expected)
        ack=encode_frame(vectors['ack'],bytes(32),b'mikdash-response-v1\0')
        self.assertEqual(ack.hex(),vectors['ackFrameHex'])
        self.assertEqual(decode_frame(ack[4:-32],ack[-32:],bytes(32),b'mikdash-response-v1\0'),vectors['ack'])


class SourceBoundaryTests(unittest.TestCase):
    def test_frozen_source02_every_hash_unchanged(self):
        receipt=json.loads((ROOT/'adapters/receipt-real-stream-source-02.json').read_text())
        for p,h in receipt['fileSha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h,p)

    def test_native_auth_before_parse_and_exact_ownership_before_delivery(self):
        code=(ROOT/'native/receiver03/Wire.cpp').read_text().split('bool DecodeRequest(')[1]
        self.assertLess(code.index('if(Difference)return false'),code.index('!Json('))
        self.assertIn('Fields.Last().Contains(Name)',(ROOT/'native/receiver03/Wire.cpp').read_text())
        service=(ROOT/'native/receiver03/Receiver.cpp').read_text()
        self.assertLess(service.index('P.owner==Identity'),service.index('Bridge.Handle(P)'))
        self.assertLess(service.index('Bridge.Handle(P)'),service.index('EncodeAck(A,Key,Response)'))

    def test_listener_and_cleanup_are_bounded_in_source_not_executed(self):
        code=(ROOT/'native/receiver03/Receiver.cpp').read_text()
        for s in ['TEXT("127.0.0.1")','Listen(1)','Accepted>MaximumAcceptedPerSecond','Pass<4','Input.Expired(Authority.Now())','SetNonBlocking(true)']:
            self.assertIn(s,code)
        self.assertIn('Deadline=Now+0.5',(ROOT/'native/receiver03/FrameBuffer.h').read_text())
        self.assertNotIn('AsyncTask(',code);self.assertNotIn('while(',code)
        shutdown=code.split('bool Receiver::Shutdown()')[1]
        self.assertLess(shutdown.index('Listener->Close()'),shutdown.index('Authority.Shutdown()'))
        self.assertIn('if(!Sink.Release())return false',code)
        self.assertIn('if(!Peer->Close())return false',code)
        self.assertIn('return Closed&&PeerGone&&Released',code)

if __name__=='__main__':unittest.main()

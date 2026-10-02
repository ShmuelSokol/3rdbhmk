from dataclasses import asdict
import unittest
from session_core import SessionError
from adapters.process04.test_host import OWNER, Clock
from adapters.process04.consumption_channel import ConsumptionChannel


class Transport:
    def __init__(self, clock): self.clock=clock; self.patch={}; self.generation=0; self.delay=.01
    def exchange(self, owner, packet, timeout):
        stamp=self.clock()
        self.clock.sleep(self.delay)
        if packet['operation'] in ('bind','release','close'): self.generation+=1
        result=dict(version=2,owner=asdict(owner),sequence=packet['sequence'],operation=packet['operation'],
                    connection_id=packet['connection_id'],status='consumed',outcome='applied',
                    authorized_at=stamp,generation=self.generation)
        result.update(self.patch)
        return result


class SemanticChannelTests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock(); self.t=Transport(self.clock)
        self.c=ConsumptionChannel(OWNER,19001,b'0'*32,clock=self.clock,transport=self.t)
        self.packet=dict(version=1,owner=asdict(OWNER),sequence=1,operation='open',connection_id='',event=None)
    def exchange(self): return self.c.exchange(OWNER,self.packet,1)
    def test_new_consumed_ack_adapts_exact_old_shape(self):
        self.assertEqual(self.exchange(),dict(version=1,owner=asdict(OWNER),sequence=1,
                         operation='open',connection_id='',status='applied'))
    def test_old_enqueue_ack_refused(self):
        self.t.patch=dict(version=1,status='applied')
        with self.assertRaises(SessionError): self.exchange()
    def test_explicit_no_op_consumed_not_claimed_physical_effect(self):
        self.t.patch=dict(outcome='no_op'); self.assertEqual(self.exchange()['status'],'applied')
    def test_rejected_unknown_not_acknowledged(self):
        for status in ('rejected','unknown','queued'):
            self.t.patch=dict(outcome=status)
            with self.assertRaises(SessionError): self.exchange()
    def test_timestamp_hostile_huge_future_before_send(self):
        for stamp in (10**400,float('nan'),[],True,-1,99,0):
            self.t.patch=dict(authorized_at=stamp)
            with self.assertRaises(SessionError): self.exchange()
    def test_late_ack_before_tick_refused(self):
        self.t.delay=.5
        with self.assertRaises(SessionError): self.exchange()
    def test_cross_owner_and_connection_refused(self):
        for patch in (dict(owner={}),dict(connection_id='foreign'),dict(sequence=True),dict(generation=[])):
            self.t.patch=patch
            with self.assertRaises(SessionError): self.exchange()
    def test_generation_lifecycle(self):
        self.exchange()
        for seq,op,conn in ((2,'bind','a'),(3,'input','a'),(4,'release','a'),(5,'bind','b'),(6,'close','b')):
            self.packet.update(sequence=seq,operation=op,connection_id=conn)
            self.exchange()
        self.assertEqual(self.c.generation,4)
    def test_failure_does_not_advance_generation_or_retry(self):
        self.packet.update(operation='bind',connection_id='c')
        self.t.delay=.6
        with self.assertRaises(SessionError): self.exchange()
        self.assertEqual(self.c.generation,0)
        self.assertEqual(self.t.generation,1)
    def test_extra_field_refused(self):
        self.t.patch={'secret':'not-public'}
        with self.assertRaisesRegex(SessionError,'^Semantic acknowledgment unavailable$'): self.exchange()


if __name__=='__main__': unittest.main()

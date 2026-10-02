import unittest
from dataclasses import asdict, replace
from session_core import SessionCore, Limits, InputEvent, Ownership, SessionError
from adapters.bridge import BridgeStreams
from adapters.core_host import CoreAuthority


class Channel:
    def __init__(self):
        self.sent=[]
        self.change=lambda ack:ack
    def exchange(self, owner, packet, timeout):
        self.sent.append(packet)
        return self.change(dict(version=1,owner=asdict(owner),sequence=packet['sequence'],
            operation=packet['operation'],connection_id=packet['connection_id'],status='applied'))


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.now=100
        self.channel=Channel()
        self.stream=BridgeStreams(self.channel,clock=lambda:self.now)
        self.owner=Ownership('s','process','stream','save','settings',110)
        self.stream.open(self.owner)
        self.stream.bind(self.owner,'connection')

    def test_exact_ack_after_apply(self):
        self.stream.send_input(self.owner,'connection',InputEvent('move',1,0))
        p=self.channel.sent[-1]
        self.assertEqual(p['event'],dict(action='move',x=1,y=0))
        self.assertEqual(p['sequence'],3)

    def test_reject_stale_cross_owner_and_connection(self):
        for owner,conn in [(replace(self.owner,process_key='other'),'connection'),(self.owner,'other')]:
            with self.assertRaises(SessionError):self.stream.send_input(owner,conn,InputEvent('pause'))
        self.assertEqual(len(self.channel.sent),2)

    def test_no_success_for_enqueued_rejected_wrong_identity_or_sequence_ack(self):
        for change in [lambda a:None,lambda a:dict(a,status='queued'),lambda a:dict(a,sequence=0),
                       lambda a:dict(a,owner={}),lambda a:dict(a,connection_id='other'),
                       lambda a:dict(a,version=True),lambda a:dict(a,sequence=True)]:
            self.channel.change=change
            with self.assertRaises(SessionError):self.stream.send_input(self.owner,'connection',InputEvent('mute'))

    def test_timeout_and_expiry_during_native_callback(self):
        def advance(ack):self.now+=2;return ack
        self.channel.change=advance
        with self.assertRaises(SessionError):self.stream.send_input(self.owner,'connection',InputEvent('move'))
        self.now=109.9
        def expire(ack):self.now=110;return ack
        self.channel.change=expire
        with self.assertRaises(SessionError):self.stream.send_input(self.owner,'connection',InputEvent('move'))

    def test_expired_cleanup_allowed_duplicate_close_idempotent(self):
        self.now=111
        with self.assertRaises(SessionError):self.stream.send_input(self.owner,'connection',InputEvent('move'))
        self.stream.release_inputs(self.owner,'connection')
        self.stream.close(self.owner)
        n=len(self.channel.sent);self.stream.close(self.owner)
        self.assertEqual(len(self.channel.sent),n)

    def test_release_failure_retains_binding_and_close_failure_capacity(self):
        self.channel.change=lambda a:dict(a,status='rejected')
        with self.assertRaises(SessionError):self.stream.release_inputs(self.owner,'connection')
        self.assertEqual(self.stream.records['stream']['connection'],'connection')
        with self.assertRaises(SessionError):self.stream.close(self.owner)
        with self.assertRaises(SessionError):self.stream.open(replace(self.owner,stream_id='second'))
        self.channel.change=lambda a:a
        self.stream.close(self.owner)
        self.assertFalse(self.stream.records)

    def test_unsupported_reset_dove_console_and_huge_number_not_sent(self):
        for e in [InputEvent('reset'),InputEvent('dove'),InputEvent('console'),InputEvent('move',10**400)]:
            with self.assertRaises(SessionError):self.stream.send_input(self.owner,'connection',e)
        self.assertEqual(len(self.channel.sent),2)

    def test_adapter_exception_is_fixed_message(self):
        def bad(a):raise RuntimeError('secret-not-for-receipt')
        self.channel.change=bad
        with self.assertRaises(SessionError) as e:self.stream.send_input(self.owner,'connection',InputEvent('pause'))
        self.assertEqual(str(e.exception),'Native acknowledgment failed')


class Processes:
    def start(self,owner):pass
    def stop(self,owner):pass


class CoreIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.channel=Channel();self.stream=BridgeStreams(self.channel,clock=lambda:100)
        self.core=SessionCore(Processes(),self.stream,Limits(capacity=1),clock=lambda:100)
        self.host=CoreAuthority(self.core,self.stream)
        self.ticket=self.core.request()
        self.binding=self.host.attach(self.ticket)

    def test_real_core_submit_release_and_disconnect(self):
        self.host.submit(self.binding,dict(action='move',x=1,y=0))
        self.host.release(self.binding)
        self.assertEqual(self.channel.sent[-1]['event'],dict(action='move',x=0,y=0))
        self.host.disconnect(self.binding);self.host.disconnect(self.binding)
        with self.assertRaises(SessionError):self.host.validate(self.binding)
        self.assertEqual(self.channel.sent[-1]['operation'],'release')

    def test_failure_revokes_and_quarantines_until_native_cleanup_ack(self):
        self.channel.change=lambda a:dict(a,status='rejected')
        with self.assertRaises(SessionError):self.host.submit(self.binding,dict(action='move',x=1,y=0))
        self.assertEqual(self.core.cleanup_pending(),1)
        with self.assertRaises(SessionError):self.host.disconnect(self.binding)
        self.channel.change=lambda a:a
        self.host.disconnect(self.binding)
        self.assertEqual(self.core.cleanup_pending(),0)

if __name__=='__main__':unittest.main()

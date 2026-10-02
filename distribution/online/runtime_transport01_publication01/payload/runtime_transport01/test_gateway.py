"""Actual Gateway/Core/FlightAuthority; OS and native exchange adapters only.

No sockets/UE. Shifted clocks exercise gateway domain handling; frozen private
bootstrap separately refuses unproved mappings (not claimed as supported native).
"""
import json,threading,unittest
from pathlib import Path
from types import SimpleNamespace
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from session_core import SessionCore,SessionError,Limits
from runtime_flight01.host import FlightAuthority,FlightStreams
from runtime_transport01.gateway import Gateway,Unavailable,strict_json
from adapters.receiver03_bootstrap import make_record

class Process:
    def __init__(self,offset=0):
        self.host_time=100000+offset;self.native_time=100000.;self.ports=(19001,)
        self.records={};self.commands=[];self.handoff=False;self.revoke=lambda owner:None
        self.fail=None;self.fail_stop=False;self.delay=0;self.auth_delay=0;self.toggle=True
    def now(self):return self.host_time
    def qpc(self):return self.native_time
    def advance(self,n):self.host_time+=n;self.native_time+=n
    def start(self,owner):
        def identity():self.advance(self.auth_delay)
        child=SimpleNamespace(ready_binding=(owner,(10,20),'a'*32),native_deadline=self.native_time+60,
            _admit=lambda:None,_identity=identity,alive=lambda:True)
        self.records[owner.process_key]=SimpleNamespace(child=child)
    def record(self,owner):return self.records[owner.process_key]
    def stop(self,owner):
        self.revoke(owner)
        if self.fail_stop:raise SessionError('synthetic adapter failure')
        self.records.pop(owner.process_key,None)
    def exchange(self,owner,p,timeout):
        self.commands.append(p)
        if p['operation']==self.fail:raise SessionError('synthetic private failure')
        if p['operation']=='stream':self.advance(self.delay)
        if p['operation']=='input' and p['event']['action']=='dove':self.handoff=self.toggle
        return dict(version=1,owner=p['owner'],sequence=p['sequence'],operation=p['operation'],connection_id=p['connection_id'],status='applied')
    def take_handoff(self,owner):v=self.handoff;self.handoff=False;return v

class Host:
    def __init__(self,offset=0,capacity=1):
        self.lock=threading.RLock();self.processes=Process(offset)
        self.processes.ports=tuple(range(19001,19001+capacity))
        streams=FlightStreams(self.processes)
        self.core=SessionCore(self.processes,streams,Limits(capacity=capacity),clock=self.processes.now)
        self.authority=FlightAuthority(self.core,streams,self.processes);self.authority.lock=self.lock
    def request(self):return self.core.request()
    def tick(self):self.core.tick()
    def shutdown(self):self.core.shutdown()

class Peer:
    def __init__(self):self.messages=[];self.closed=False;self.fail_close=False;self.onclose=lambda:None
    def send(self,m):self.messages.append(m)
    def close(self):
        if self.fail_close:raise RuntimeError('synthetic private detail')
        if self.closed:return
        self.closed=True;self.onclose()

class GatewayTests(unittest.TestCase):
    def start(self,offset=0,subscribe=True):
        self.host=Host(offset);self.p=self.host.processes;self.g=Gateway(self.host,19443)
        self.p.revoke=self.g.process_revoked
        self.rid,self.sid,self.cookie=self.g.request();self.r=self.g.routes[self.rid]
        self.ticket=self.p.commands[-1]['event']['ticket'];self.peers={}
        self.g.authenticate_streamer(self.sid,self.ticket)
        for role in ('streamer','control','player'):
            self.peers[role]=Peer();self.g.attach(self.r,role,self.peers[role])
        self.g.receive(self.r,'streamer',json.dumps(dict(type='endpointId',id=self.sid)))
        if subscribe:self.g.receive(self.r,'player',json.dumps(dict(type='subscribe',streamerId=self.sid)))
    def send(self,action='move',sequence=1,generation=0):
        return self.g.receive(self.r,'control',json.dumps(dict(type='input',sequence=sequence,generation=generation,event=dict(action=action,x=0,y=0))))
    def test_owned_signalling_routes_and_actual_submit(self):
        self.start();self.send()
        self.assertEqual(self.p.commands[-1]['operation'],'input')
        self.g.receive(self.r,'streamer',json.dumps(dict(type='offer',playerId=self.rid,sdp='synthetic SDP')))
        self.assertEqual(self.peers['player'].messages[-1],dict(type='offer',sdp='synthetic SDP'))
        self.assertEqual(self.peers['control'].messages[-1],dict(type='ack',sequence=1,generation=0,handoff=False))
    def test_flight_release_rebind_then_fresh_movement(self):
        self.start();old=self.r.binding;expiry=old.owner.expires_at
        self.send('dove');self.send('move',2,1)
        self.assertEqual([p['operation'] for p in self.p.commands][-4:],['input','release','bind','input'])
        self.assertEqual(self.r.binding.owner.expires_at,expiry)
        self.assertIsNot(old,self.r.binding)
        self.assertFalse(self.host.authority.pending_handoffs)
    def test_noop_without_transition_preserves_generation(self):
        self.start();self.p.toggle=False;old=self.r.binding;self.send('dove')
        self.assertIs(self.r.binding,old);self.assertEqual(self.r.generation,0)
    def test_boundary_254_accepts_255_then_exhaustion_before_submit(self):
        self.start();self.r.generation=254;self.send('dove',1,254)
        self.assertEqual(self.r.generation,255)
        n=sum(c['operation']=='input' for c in self.p.commands)
        with self.assertRaises(Unavailable):self.send('dove',2,255)
        self.assertEqual(sum(c['operation']=='input' for c in self.p.commands),n)
        self.assertFalse(self.host.authority.streams.records)
    def test_counter_256_is_never_dispatched(self):
        self.start();self.r.generation=256
        with self.assertRaises(Unavailable):self.send('dove',1,256)
        self.assertFalse(any(c['operation']=='input' for c in self.p.commands))
    def test_bad_post_submit_result_cleans_authentic_fresh_binding(self):
        self.start();real=self.host.authority.submit
        def bad(b,e):real(b,e);return dict(binding=[],streamId=self.sid)
        self.host.authority.submit=bad
        with self.assertRaises(Unavailable):self.send('dove')
        self.assertFalse(self.host.authority.pending_handoffs);self.assertFalse(self.host.authority.streams.records)
    def test_failed_cleanup_retains_capacity_and_pending_pair(self):
        self.start();real=self.host.authority.submit
        def bad(b,e):real(b,e);return dict(binding=[],streamId=self.sid)
        self.host.authority.submit=bad;self.p.fail_stop=True
        with self.assertRaises(Unavailable):self.send('dove')
        self.assertTrue(self.host.authority.pending_handoffs);self.assertTrue(self.host.authority.streams.records)
        self.p.fail_stop=False;self.g.revoke(self.r)
        self.assertFalse(self.host.authority.streams.records)
    def test_delayed_subscription_no_early_control_dispatch(self):
        self.start(subscribe=False)
        # Browser prevents early input; malicious premature input fails closed.
        self.assertFalse(any(c['operation']=='input' for c in self.p.commands))
        self.g.receive(self.r,'player',json.dumps(dict(type='subscribe',streamerId=self.sid)));self.send()
    def test_unallocated_and_fallback_subscription_refused(self):
        self.start(subscribe=False)
        with self.assertRaises(Unavailable):self.g.receive(self.r,'player','{"type":"subscribe","streamerId":"default"}')
        self.assertTrue(self.peers['control'].closed)
    def test_wrong_and_duplicate_native_ticket(self):
        self.start()
        for stream,ticket in [(self.sid,'x'*64),('foreign',self.ticket),(self.sid,self.ticket)]:
            with self.assertRaises(Unavailable):self.g.authenticate_streamer(stream,ticket)
    def test_cookie_refuses_hostile_types_and_unicode(self):
        self.start()
        for rid,cookie in [([],self.cookie),(self.rid,[]),(self.rid,'\u263a'*64)]:
            with self.assertRaises(Unavailable):self.g.authenticate_browser(rid,cookie)
    def test_synchronous_close_reentry(self):
        self.start()
        for peer in self.peers.values():peer.onclose=lambda:self.g.revoke(self.r)
        self.g.revoke(self.r);self.g.revoke(self.r)
        self.assertFalse(self.g.routes);self.assertFalse(self.host.authority.streams.records)
    def test_release_failure_never_sends_ack(self):
        self.start();self.p.fail='input'
        with self.assertRaises(Unavailable):self.g.receive(self.r,'control','{"type":"release","sequence":1,"generation":0}')
        self.assertFalse(self.peers['control'].messages)
    def test_old_generation_and_duplicate_ack_input_refused(self):
        self.start();self.send('dove')
        with self.assertRaises(Unavailable):self.send('move',2,0)
        self.assertEqual(sum(c['operation']=='input' for c in self.p.commands),1)
    def test_large_positive_and_negative_clock_offsets(self):
        for offset in (-90000,90000):
            self.start(offset)
            event=next(c['event'] for c in self.p.commands if c['operation']=='stream')
            self.assertAlmostEqual(event['until'],100004.998)
            self.assertAlmostEqual(self.r.attach_end,100004.998+offset)
            self.assertLessEqual(event['until'],self.r.native_expiry)
            self.g.shutdown()
    def test_frozen_bootstrap_refuses_shifted_mapping(self):
        self.start()
        for offset in (-90000,90000):
            with self.assertRaises(SessionError):make_record(self.r.binding.owner,19001,b'x'*32,clock=lambda:100000+offset,qpc=lambda:100000)
    def test_qpc_expiry_after_delayed_stream_exchange(self):
        h=Host();g=Gateway(h,19443);real=h.processes.exchange
        def delayed(o,p,t):
            result=real(o,p,t)
            if p['operation']=='stream':h.processes.native_time+=6
            return result
        h.processes.exchange=delayed
        with self.assertRaises(Unavailable):g.request()
        self.assertFalse(g.routes)
    def test_auth_callbacks_must_recheck_both_domains(self):
        for native in (False,True):
            h=Host(90000);g=Gateway(h,19443);rid,sid,c=g.request();r=g.routes[rid]
            ticket=h.processes.commands[-1]['event']['ticket']
            child=h.processes.record(r.binding.owner).child
            def delayed():
                if native:h.processes.native_time+=6
                else:h.processes.host_time+=6
            child._identity=delayed
            with self.assertRaises(Unavailable):g.authenticate_streamer(sid,ticket)
            self.assertFalse(r.ticket_used)
    def test_nonfinite_huge_and_regressing_qpc_refused(self):
        for value in (float('nan'),float('inf'),10**400,-1,99999):
            self.start();self.p.native_time=value
            with self.assertRaises(Unavailable):self.g.authenticate_browser(self.rid,self.cookie)
    def test_session_expiry_before_input_no_dispatch(self):
        self.start();self.p.advance(self.r.binding.owner.expires_at-self.p.now())
        with self.assertRaises(Unavailable):self.send()
        self.assertFalse(any(c['operation']=='input' for c in self.p.commands))
    def test_duplicate_json_keys_refused(self):
        with self.assertRaises(Unavailable):strict_json('{"type":"input","type":"release"}')
    def test_two_independent_allocations_cross_cookie_and_ticket_refusal(self):
        h=Host(capacity=2);g=Gateway(h,19443);h.processes.revoke=g.process_revoked
        a,sa,ca=g.request();ta=h.processes.commands[-1]['event']['ticket']
        b,sb,cb=g.request();tb=h.processes.commands[-1]['event']['ticket']
        self.assertNotEqual(g.routes[a].binding.owner,g.routes[b].binding.owner)
        for rid,cookie in [(a,cb),(b,ca)]:
            with self.assertRaises(Unavailable):g.authenticate_browser(rid,cookie)
        for stream,ticket in [(sa,tb),(sb,ta)]:
            with self.assertRaises(Unavailable):g.authenticate_streamer(stream,ticket)
        g.revoke(g.routes[a]);self.assertTrue(g.authenticate_browser(b,cb));self.assertEqual(len(h.processes.records),1)
        g.shutdown()
    def test_no_browser_attachment_expires_even_after_native_ready(self):
        self.start(subscribe=False);self.p.advance(5);self.g.tick();self.assertFalse(self.g.routes)
    def test_delayed_host_lock_never_dispatches_stale_input(self):
        self.start();values=iter((10.,10.3));self.g.io_clock=lambda:next(values)
        with self.assertRaises(Unavailable):self.send()
        self.assertFalse(any(c['operation']=='input' for c in self.p.commands));self.assertFalse(self.g.routes)
    def test_process_revoke_callback_does_not_reenter_core(self):
        self.start()
        for peer in self.peers.values():peer.onclose=lambda:self.g.revoke(self.r)
        self.host.core.cancel(self.r.binding.connection.session_id,self.r.binding.connection.credential)
        self.g.tick();self.assertFalse(self.g.routes)

if __name__=='__main__':unittest.main(verbosity=2)

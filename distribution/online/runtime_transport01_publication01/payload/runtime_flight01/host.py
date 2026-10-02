"""Consumed flight ACK -> native release -> fresh Core binding, same lease.

No listener/process starts on import. Handoff is accepted only through the actual
generation-bound HMAC transport followed by the frozen consumption validator.
"""
from adapters.process04.host import OwnedStreams
from adapters.core_host import CoreAuthority, Binding, serialized
from runtime_activation01.owned_host import GenerationTransport, ActiveProcesses
from session_core import InputEvent, SessionError

class _V4:
    def __init__(self, raw):self.raw=raw;self.handoff=False
    def exchange(self,owner,packet,timeout):
        self.handoff=False
        r=self.raw.exchange(owner,packet,timeout)
        if (type(r) is not dict or type(r.get('version')) is not int or r['version']!=4 or
                type(r.get('handoff')) is not bool):raise SessionError('Flight acknowledgment unavailable')
        flag=r['handoff']
        if flag and (packet.get('operation')!='input' or
                     packet.get('event',{}).get('action')!='dove'):
            raise SessionError('Flight acknowledgment unavailable')
        self.handoff=flag
        projected=dict(r);del projected['handoff'];projected['version']=3
        return projected

class FlightTransport(GenerationTransport):
    def __init__(self,raw,child):
        self.v4=_V4(raw)
        super().__init__(self.v4,child)

class FlightProcesses(ActiveProcesses):
    def exchange(self,owner,packet,timeout):
        r=self.record(owner)
        if not isinstance(r.channel.transport,FlightTransport):
            # Refuse replacing a previously started v3 transport midway through a lease.
            if isinstance(r.channel.transport,GenerationTransport):
                raise SessionError('Flight transport version mismatch')
            r.channel.transport=FlightTransport(r.channel.transport,r.child)
        if getattr(r,'flight_handoff',False):
            raise SessionError('Flight handoff not consumed')
        ack=super().exchange(owner,packet,timeout) # includes actual ConsumptionChannel checks
        r.flight_handoff=r.channel.transport.v4.handoff
        return ack
    def take_handoff(self,owner):
        r=self.record(owner)
        flag=getattr(r,'flight_handoff',False);r.flight_handoff=False
        return flag

class FlightStreams(OwnedStreams):
    def send_input(self,owner,connection_id,event):
        if type(event) is not InputEvent or event.action!='dove':
            return super().send_input(owner,connection_id,event)
        with self.lock:
            event.validate();r=self._record(owner)
            if r['closing'] or not r['connection'] or connection_id!=r['connection']:
                raise SessionError('Flight input refused')
            self._exchange(r,'input',connection_id,dict(action='dove',x=0,y=0))

class FlightAuthority(CoreAuthority):
    def __init__(self,core,streams,processes):
        super().__init__(core,streams);self.processes=processes;self.pending_handoffs={}
    @serialized
    def submit(self,binding,event):
        if any(binding is fresh for fresh in self.pending_handoffs.values()):
            raise SessionError('Flight binding not accepted')
        super().submit(binding,event) # returns only after real consumed outcome
        if not self.processes.take_handoff(binding.owner):return None
        if event['action']!='dove':raise SessionError('Unexpected flight handoff')
        current=binding.connection
        self.bindings.remove(binding) # old browser binding revoked before native release
        try:
            self.core.disconnect(current) # existing core releases native input
            fresh=self.attach(current) # rotates credential + connection, never session expiry
            current=fresh.connection
            self.pending_handoffs[binding]=fresh # retain BEFORE post-attachment checks
            if fresh.owner!=binding.owner or not self.validate(fresh):
                raise SessionError('Flight ownership changed')
            return dict(binding=fresh,streamId=fresh.owner.stream_id)
        except Exception:
            try:
                if binding in self.pending_handoffs:self.abortHandoff(binding)
                else:self.core.cancel(current.session_id,current.credential)
            except SessionError:pass
            raise SessionError('Flight handoff unavailable') from None
    @serialized
    def commitHandoff(self,old,fresh):
        if type(old) is not Binding or type(fresh) is not Binding or self.pending_handoffs.get(old) is not fresh:
            raise SessionError('Flight acceptance unavailable')
        self.validate(fresh)
        del self.pending_handoffs[old]
    @serialized
    def abortHandoff(self,old):
        if type(old) is not Binding:raise SessionError('Flight cleanup unavailable')
        fresh=self.pending_handoffs.get(old)
        if fresh is None:return
        if fresh.owner.stream_id not in self.streams.records:
            self.bindings.discard(fresh);del self.pending_handoffs[old];return
        # Lookup is solely the retained server-issued pair, never result/browser fields.
        try:self.core.cancel(fresh.connection.session_id,fresh.connection.credential)
        except SessionError:pass # cancellation revokes credential before incomplete cleanup
        self.core.tick()
        if fresh.owner.stream_id in self.streams.records:
            raise SessionError('Flight cleanup pending')
        self.bindings.discard(fresh);del self.pending_handoffs[old]

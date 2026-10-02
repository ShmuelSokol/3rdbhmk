"""Real readiness01 child + authenticated IPC, with explicit process generation.

Imports/constructors launch nothing. Core.request -> authenticated open (no browser)
-> CoreAuthority.attach/bind -> submit -> actual receiver consumption ACK.
"""
from session_core import SessionError
from adapters.process04.host import OwnedProcesses
from runtime_readiness01.owned_host import StoppedProcesses

class GenerationTransport:
    def __init__(self,transport,child):
        self.transport=transport;self.child=child
        self.binding=child.ready_binding
        if not self.binding or not child.observed:raise SessionError('Private admission not observed')
    def exchange(self,owner,packet,timeout):
        try:
            c=self.child
            if c.ready_binding!=self.binding or owner!=self.binding[0]:raise ValueError()
            c._admit();c._identity()
            wire=dict(packet,process_generation=self.binding[2])
            result=self.transport.exchange(owner,wire,timeout)
            c._admit();c._identity()
            if not c.alive():raise ValueError()
            c._identity() # alive revalidates an external premise; fence afterwards
            if (c.ready_binding!=self.binding or
                type(result) is not dict or result.get('version')!=3 or type(result.get('version')) is not int or
                result.get('process_generation')!=self.binding[2]):raise ValueError()
            # Retain the frozen v2 consumption/time/outcome validator. Only the
            # authenticated v3 generation field is projected; no success invented.
            result=dict(result);del result['process_generation'];result['version']=2
            return result
        except Exception:raise SessionError('Generation-bound acknowledgment unavailable') from None

class ActiveProcesses(StoppedProcesses):
    def exchange(self,owner,packet,timeout):
        r=self.record(owner)
        if not isinstance(r.channel.transport,GenerationTransport):
            r.channel.transport=GenerationTransport(r.channel.transport,r.child)
        return OwnedProcesses.exchange(self,owner,packet,timeout)

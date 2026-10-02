"""Validate receiver04 semantic ACKs before adapting to frozen BridgeStreams.

This is a reviewed API extension in a NEW adapter; old native ACKs are refused.
Imports/constructor open nothing. The underlying frozen channel authenticates.
"""
from dataclasses import asdict
from session_core import SessionError
from adapters.loopback_channel import LoopbackChannel
from adapters.receiver03_bootstrap import windows_qpc


class ConsumptionChannel:
    def __init__(self, owner, port, key, clock=windows_qpc, transport=None):
        self.owner, self.clock = owner, clock
        self.transport = transport or LoopbackChannel(owner, port, key, clock=clock)
        self.generation = 0

    def exchange(self, owner, packet, timeout):
        try:
            start = self.clock()
            if type(start) not in (int,float) or not 0 <= start <= 2**40:
                raise ValueError()
            response = self.transport.exchange(owner, packet, timeout)
            now = self.clock()
            if type(response) is not dict or set(response) != {
                    'version','owner','sequence','operation','connection_id','status',
                    'outcome','authorized_at','generation'}:
                raise ValueError()
            stamp = response['authorized_at']; generation = response['generation']
            expected = self.generation + (1 if packet['operation'] in ('bind','release','close') else 0)
            if (owner != self.owner or type(now) not in (int,float) or not start <= now < start+timeout or
                    type(stamp) not in (int,float) or not start <= stamp <= now or
                    type(generation) is not int or generation != expected or
                    type(response['version']) is not int or response['version'] != 2 or
                    type(response['sequence']) is not int or response['sequence'] != packet['sequence'] or
                    response['owner'] != asdict(owner) or response['operation'] != packet['operation'] or
                    response['connection_id'] != packet['connection_id'] or response['status'] != 'consumed' or
                    response['outcome'] not in ('applied','no_op')):
                raise ValueError()
            # Original client send time is a conservative lower bound on accept.
            # End-to-end budget <=0.5s is stricter than native accept+0.5s.
            if now >= start+0.5 or (packet['operation'] not in ('release','close') and now >= owner.expires_at):
                raise ValueError()
            self.generation = generation
            # No fabricated success: only the above authenticated consumed result
            # is reduced to the frozen bridge's exact ACK shape. NoOp means the
            # action was consumed with an explicit, supported no-effect outcome.
            return dict(version=1, owner=response['owner'], sequence=response['sequence'],
                        operation=response['operation'], connection_id=response['connection_id'], status='applied')
        except Exception:
            raise SessionError('Semantic acknowledgment unavailable') from None

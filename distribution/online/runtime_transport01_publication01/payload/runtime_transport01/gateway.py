"""Concrete in-process dispatch to the actual owned Python host.

No RPC placeholder: control messages call FlightAuthority under its real shared
lock. This module does not open sockets. server.py supplies bounded TLS peers.
"""
import hashlib,json,secrets,time,threading
from dataclasses import dataclass,field
from session_core import SessionError
from adapters.core_host import Binding

class Unavailable(Exception):
    def __init__(self):super().__init__('Session unavailable')
def strict_json(raw):
    if type(raw) is not str:raise Unavailable()
    try:
        if len(raw.encode('utf-8'))>65536:raise Unavailable()
    except UnicodeError:raise Unavailable() from None
    def pairs(values):
        out={}
        for k,v in values:
            if k in out:raise Unavailable()
            out[k]=v
        return out
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(Unavailable()))
    except Exception:raise Unavailable() from None
def digest(value):return hashlib.sha256(value.encode('ascii')).digest()
def same(value,expected):
    return type(value) is str and len(value)==64 and value.isascii() and secrets.compare_digest(digest(value),expected)
def integer(v):return type(v) is int and 0<=v<=9007199254740991
def semantic(e):
    if type(e) is not dict or set(e)!={'action','x','y'} or e['action'] not in ('move','look','interact','pause','mute','dove'):raise Unavailable()
    if any(type(e[k]) not in (int,float) or not -1<=e[k]<=1 for k in ('x','y')):raise Unavailable()
    if e['action'] not in ('move','look') and (e['x'] or e['y']):raise Unavailable()
    return e
def rtc(m):
    if m.get('type') in ('offer','answer') and type(m.get('sdp')) is str and 0<len(m['sdp'])<=60000:
        return dict(type=m['type'],sdp=m['sdp'])
    if m.get('type')=='iceCandidate':
        c=m.get('candidate')
        if type(c) is dict and type(c.get('candidate')) is str and len(c['candidate'])<=4096 and (
           c.get('sdpMid') is None or type(c['sdpMid']) is str and len(c['sdpMid'])<=128) and (
           c.get('sdpMLineIndex') is None or integer(c['sdpMLineIndex']) and c['sdpMLineIndex']<=65535):
            return dict(type='iceCandidate',candidate={k:c.get(k) for k in ('candidate','sdpMid','sdpMLineIndex')})
    raise Unavailable()
@dataclass(eq=False,repr=False)
class Route:
    id:str
    binding:object
    cookie:bytes
    ticket:bytes
    attach_end:float
    initial_binding:object
    process_generation:str
    native_expiry:float
    native_attach_end:float
    ready:bool=False
    subscribed:bool=False
    closing:bool=False
    cleaning:bool=False
    ticket_used:bool=False
    sequence:int=0
    generation:int=0
    pending_old:object=None
    peers:dict=field(default_factory=dict)
    window:float=0
    count:int=0
    cancelled:object=field(default_factory=threading.Event)

class Gateway:
    def __init__(self,host,port,*,io_clock=time.monotonic):
        if type(port) is not int or not 1024<=port<=65535:raise Unavailable()
        self.host=host;self.authority=host.authority;self.port=port;self.routes={};self.closed=False
        self.lock=host.lock
        self.last_host=-1;self.last_native=-1
        self.io_clock=io_clock
    def _clock(self,native=False):
        try:
            n=self.host.processes.qpc() if native else self.host.processes.now()
            last=self.last_native if native else self.last_host
            if type(n) not in (int,float) or not 0<=n<=2**40 or n<last:raise Unavailable()
            if native:self.last_native=n
            else:self.last_host=n
            return n
        except Exception:raise Unavailable() from None
    def _attach_live(self,r):
        if self._clock()>=r.attach_end or self._clock(True)>=r.native_attach_end:raise Unavailable()
    def _live(self,r):
        if self.closed or r.closing or r.cancelled.is_set() or self.routes.get(r.id) is not r:raise Unavailable()
        self.authority.validate(r.binding)
        if r.closing or self._clock()>=r.binding.owner.expires_at or self._clock(True)>=r.native_expiry:raise Unavailable()
    def request(self):
        with self.lock:
            if self.closed or len(self.routes)>=self.host.core.limits.capacity:raise Unavailable()
            ticket=self.host.request();binding=None;r=None
            try:
                binding=self.authority.attach(ticket);owner=binding.owner
                process=self.host.processes.record(owner)
                # Exact deadline retained from the original serialized private body.
                native0=self._clock(True);host0=self._clock();native1=self._clock(True)
                expiry=process.child.native_deadline
                if type(expiry) not in (int,float) or not native1<expiry<=2**40 or native1-native0>.05:raise Unavailable()
                # Compare durations only; absolute clock domains never mix.
                # Earlier QPC sample plus a margin conservatively accounts for
                # time spent sampling; neither immutable expiry is extended.
                duration=min(5,binding.owner.expires_at-host0,expiry-native1)-.002
                if duration<=0:raise Unavailable()
                end=host0+duration;native_end=native0+duration
                cookie=secrets.token_hex(32);native_ticket=secrets.token_hex(32)
                r=Route(secrets.token_hex(16),binding,digest(cookie),digest(native_ticket),end,binding,process.child.ready_binding[2],expiry,native_end)
                self.routes[r.id]=r # allocation is visible BEFORE owned StartStreaming
                streams=self.authority.streams
                streams._exchange(streams._record(owner),'stream',binding.connection.connection_id,
                    dict(port=self.port,ticket=native_ticket,until=native_end))
                self._live(r);self._attach_live(r)
                return r.id,owner.stream_id,cookie
            except Exception:
                if r is not None:self.revoke(r)
                else:
                    c=binding.connection if binding is not None else ticket
                    try:self.host.core.cancel(c.session_id,c.credential)
                    except SessionError:pass
                raise Unavailable() from None
    def authenticate_browser(self,route_id,cookie):
        with self.lock:
            if type(route_id) is not str or len(route_id)!=32:raise Unavailable()
            r=self.routes.get(route_id)
            if r is None or not same(cookie,r.cookie):raise Unavailable()
            self._live(r);return r
    def authenticate_streamer(self,stream_id,ticket):
        with self.lock:
            matches=[r for r in self.routes.values() if r.binding.owner.stream_id==stream_id]
            if len(matches)!=1:raise Unavailable()
            r=matches[0];self._live(r)
            p=self.host.processes.record(r.binding.owner)
            self._attach_live(r)
            if r.ticket_used or r.binding is not r.initial_binding or (
                p.child.ready_binding[2]!=r.process_generation) or not same(ticket,r.ticket):raise Unavailable()
            p.child._admit();p.child._identity()
            if not p.child.alive():raise Unavailable()
            p.child._identity();self._live(r)
            self._attach_live(r)
            r.ticket_used=True;return r
    def attach(self,r,role,peer):
        with self.lock:
            self._live(r)
            if role not in ('streamer','player','control') or role in r.peers:raise Unavailable()
            r.peers[role]=peer
            try:
                if role!='control':peer.send(dict(type='config',protocolVersion='1.3.0',peerConnectionOptions={'iceServers':[]}))
                if role=='streamer':peer.send(dict(type='identify'))
            except Exception:self.revoke(r);raise Unavailable() from None
    def _send(self,r,role,message):
        self._live(r)
        if role not in r.peers:raise Unavailable()
        r.peers[role].send(message)
    def receive(self,r,role,raw):
        # Bound admission to the shared host lock. A frame waiting behind another
        # session's startup must not become freshly authorized seconds later.
        before=self.io_clock()
        if type(before) not in (int,float) or not 0<=before<=2**40:raise Unavailable()
        if not self.lock.acquire(timeout=.25):
            r.cancelled.set();raise Unavailable()
        try:
            after=self.io_clock()
            if type(after) not in (int,float) or not before<=after<before+.25:
                r.cancelled.set();self.revoke(r);raise Unavailable()
            return self._receive_locked(r,role,raw)
        finally:self.lock.release()
    def _receive_locked(self,r,role,raw):
        with self.lock:
            try:
                self._live(r);m=strict_json(raw)
                if type(m) is not dict or type(m.get('type')) is not str:raise Unavailable()
                now=self._clock()
                if now-r.window>=1:r.window=now;r.count=0
                r.count+=1
                if r.count>240:raise Unavailable()
                if role!='control' and m['type']=='ping':
                    if type(m.get('time')) not in (int,float) or not 0<=m['time']<=2**53:raise Unavailable()
                    return self._send(r,role,dict(type='pong',time=m['time']))
                if role=='streamer':
                    if m['type']=='endpointId' and not r.ready and m.get('id')==r.binding.owner.stream_id:
                        r.ready=True;self._send(r,role,dict(type='endpointIdConfirm',committedId=m['id']))
                        # Pinned frontend MaxReconnectAttempts=0 means an empty
                        # list is not polled. Notify only this allocated player.
                        if 'player' in r.peers:self._send(r,'player',dict(type='streamerList',ids=[r.binding.owner.stream_id]))
                        return
                    if not r.ready or not r.subscribed or m.get('playerId')!=r.id:raise Unavailable()
                    if m['type']=='disconnectPlayer':self.revoke(r);return
                    return self._send(r,'player',rtc(m))
                if role=='player':
                    if m['type']=='listStreamers':return self._send(r,role,dict(type='streamerList',ids=[r.binding.owner.stream_id] if r.ready else []))
                    if m['type']=='subscribe':
                        if m.get('streamerId')!=r.binding.owner.stream_id or not r.ready or r.subscribed or 'control' not in r.peers:raise Unavailable()
                        r.subscribed=True;return self._send(r,'streamer',dict(type='playerConnected',playerId=r.id,dataChannel=True,sfu=False))
                    if m['type']=='unsubscribe':self.revoke(r);return
                    if not r.ready or not r.subscribed:raise Unavailable()
                    return self._send(r,'streamer',dict(rtc(m),playerId=r.id))
                if role!='control' or not integer(m.get('sequence')) or m['sequence']!=r.sequence+1 or type(m.get('generation')) is not int or m['generation']!=r.generation:raise Unavailable()
                handoff=False
                if m['type']=='release':self.authority.release(r.binding)
                elif m['type']=='input':
                    if not r.subscribed:raise Unavailable()
                    event=semantic(m.get('event'))
                    if event['action']=='dove':
                        if r.generation>=255:raise Unavailable()
                        r.pending_old=r.binding
                    result=self.authority.submit(r.binding,event)
                    if result is not None:
                        if event['action']!='dove' or type(result) is not dict or set(result)!={'binding','streamId'} or result['streamId']!=r.binding.owner.stream_id:raise Unavailable()
                        fresh=result['binding']
                        if type(fresh) is not Binding or fresh.owner!=r.binding.owner or self.authority.pending_handoffs.get(r.pending_old) is not fresh:raise Unavailable()
                        r.binding=result['binding'];self._live(r)
                        self.authority.commitHandoff(r.pending_old,r.binding);r.pending_old=None
                        r.generation+=1;handoff=True
                    else:r.pending_old=None
                else:raise Unavailable()
                r.sequence=m['sequence'];self._send(r,'control',dict(type='ack',sequence=r.sequence,generation=r.generation,handoff=handoff))
            except Exception:self.revoke(r);raise Unavailable() from None
    def process_revoked(self,owner):
        """Exact process04 callback: close peers, NEVER recursively stop the Job.

        Routes stay charged until the outer Core cleanup proves disposal. Before
        a route exists (failed startup), there are no peers to revoke.
        """
        with self.lock:
            failed=False
            for r in tuple(self.routes.values()):
                if r.binding.owner!=owner:continue
                r.closing=True;r.subscribed=False
                previous=r.cleaning;r.cleaning=True
                try:
                    for role,peer in list(r.peers.items()):
                        try:peer.close();r.peers.pop(role,None)
                        except Exception:failed=True
                finally:r.cleaning=previous
            if failed:raise Unavailable()
    def revoke(self,r):
        with self.lock:
            if self.routes.get(r.id) is not r or r.cleaning:return
            r.closing=True;r.subscribed=False;r.cleaning=True
            try:
                if r.pending_old is not None:
                    try:self.authority.abortHandoff(r.pending_old);r.pending_old=None
                    except Exception:pass
                for role,peer in list(r.peers.items()):
                    # Close callback may reenter; cleaning is set before any call.
                    try:peer.close();del r.peers[role]
                    except Exception:pass
                c=r.binding.connection
                try:self.host.core.cancel(c.session_id,c.credential)
                except SessionError:pass
                self.host.core.tick()
                if r.pending_old is None and not r.peers and r.binding.owner.stream_id not in self.authority.streams.records:
                    self.authority.bindings.discard(r.binding);del self.routes[r.id]
            finally:r.cleaning=False
    def tick(self):
        with self.lock:
            self.host.tick()
            for r in list(self.routes.values()):
                try:
                    self._live(r)
                    if not r.subscribed:self._attach_live(r)
                except Exception:self.revoke(r)
    def shutdown(self):
        with self.lock:
            self.closed=True
            for r in list(self.routes.values()):self.revoke(r)
            self.host.shutdown()

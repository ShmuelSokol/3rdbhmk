"""Explicit loopback TLS HTTP/WebSocket transport for the actual owned host.

Import/construction never binds. serve() is an explicit future execution gate.
There is no default certificate, trust bypass, mock media, or default allocation.
All diagnostics are fixed strings; request headers/bodies are never logged.
"""
import base64
import hashlib
import json
import re
import socket
import ssl
import struct
import threading
import time

from runtime_transport01.gateway import Gateway,Unavailable,strict_json

GUID=b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

def request_head(raw):
    try:
        if type(raw) is not bytes or len(raw)>16384 or not raw.endswith(b'\r\n\r\n'):raise ValueError()
        lines=raw[:-4].decode('ascii').split('\r\n')
        method,path,version=lines[0].split(' ')
        if method not in ('GET','POST') or version!='HTTP/1.1' or not re.fullmatch(r'/[A-Za-z0-9_./-]*',path):raise ValueError()
        headers={}
        for line in lines[1:]:
            k,v=line.split(':',1);k=k.lower();v=v.strip(' ')
            if not re.fullmatch('[a-z0-9-]+',k) or k in headers or any(ord(c)<32 or ord(c)>126 for c in v):raise ValueError()
            headers[k]=v
        if 'transfer-encoding' in headers or len(headers)>40:raise ValueError()
        return method,path,headers
    except Exception:raise Unavailable() from None

def upgrade(headers):
    try:
        if headers.get('upgrade','').lower()!='websocket' or 'upgrade' not in [s.strip() for s in headers.get('connection','').lower().split(',')]:raise ValueError()
        if headers.get('sec-websocket-version')!='13' or 'sec-websocket-protocol' in headers:raise ValueError()
        key=headers['sec-websocket-key']
        if len(base64.b64decode(key,validate=True))!=16:raise ValueError()
        if headers.get('content-length','0')!='0':raise ValueError()
        return base64.b64encode(hashlib.sha1(key.encode('ascii')+GUID).digest()).decode('ascii')
    except Exception:raise Unavailable() from None

def cookie_value(headers):
    found=[]
    for part in headers.get('cookie','').split(';'):
        k,sep,v=part.strip().partition('=')
        if k=='walk':found.append(v)
    if len(found)!=1:return None
    return found[0]

def server_frame(payload,opcode=1):
    if type(payload) is not bytes or len(payload)>65536:raise Unavailable()
    n=len(payload)
    return bytes([0x80|opcode])+(bytes([n]) if n<126 else b'\x7e'+struct.pack('!H',n) if n<65536 else b'\x7f'+struct.pack('!Q',n))+payload

def read_frame(read):
    """read(n) must enforce one shared partial-frame deadline, not per chunk."""
    h=read(2);op=h[0]&15
    if h[0]&0xf0!=0x80 or not h[1]&0x80 or op not in (1,8,9,10):raise Unavailable()
    n=h[1]&127
    if n==126:
        n=struct.unpack('!H',read(2))[0]
        if n<126:raise Unavailable()
    elif n==127:
        n=struct.unpack('!Q',read(8))[0]
        if n<65536:raise Unavailable()
    if n>65536 or op>=8 and n>125:raise Unavailable()
    mask=read(4);data=read(n)
    payload=bytes(c^mask[i%4] for i,c in enumerate(data))
    if op==1:
        try:payload.decode('utf-8',errors='strict')
        except UnicodeError:raise Unavailable() from None
    return op,payload

class Peer:
    def __init__(self,sock,clock=time.monotonic):
        self.sock=sock;self.clock=clock;self.closed=False;self.disposed=False;self.close_failed=False
        self.send_lock=threading.Lock()
    def raw(self,data):
        if not self.send_lock.acquire(timeout=.25):raise Unavailable()
        try:
            end=self.clock()+.25;offset=0
            while offset<len(data):
                if self.closed or self.clock()>=end:raise Unavailable()
                try:n=self.sock.send(data[offset:])
                except (socket.timeout,ssl.SSLWantWriteError,ssl.SSLWantReadError):continue
                if n<=0:raise Unavailable()
                offset+=n
            if self.clock()>=end:raise Unavailable()
        finally:self.send_lock.release()
    def send(self,message):
        self.raw(server_frame(json.dumps(message,separators=(',',':'),allow_nan=False).encode('utf-8')))
    def close(self):
        self.closed=True
        if self.close_failed:raise Unavailable()
        if self.disposed:return
        # Close alone is ownership disposal. A failure retains this Peer for
        # cleanup retries/capacity; shutdown failure is not proof of disposal.
        try:self.sock.close();self.disposed=True
        except Exception:
            self.close_failed=True # Python may invalidate fd even on OS error; no retry proof
            raise Unavailable() from None

class Server:
    def __init__(self,host,port,tls,assets):
        if not isinstance(tls,ssl.SSLContext) or tls.protocol!=ssl.PROTOCOL_TLS_SERVER:raise Unavailable()
        if tls.minimum_version<ssl.TLSVersion.TLSv1_2:raise Unavailable()
        # Trusted immutable assets, prepared by the pinned offline build. Never
        # resolve a browser path into the filesystem or serve source/config.
        if set(assets)!={'/','/app.js','/style.css'}:raise Unavailable()
        for mime,data in assets.values():
            if mime not in ('text/html; charset=utf-8','text/javascript; charset=utf-8','text/css; charset=utf-8') or type(data) is not bytes or len(data)>8*1024**2:raise Unavailable()
        self.gateway=Gateway(host,port);self.tls=tls;self.port=port;self.assets=dict(assets)
        self.origin='https://127.0.0.1:'+str(port);self.host='127.0.0.1:'+str(port)
        self.stop_event=threading.Event();self.listener=None;self.started=False
        self.workers={};self.worker_lock=threading.Lock();self.limit=host.core.limits.capacity*3+4
        self.quarantined=False
    def _read(self,sock,n,end):
        data=bytearray()
        while len(data)<n:
            if self.stop_event.is_set() or time.monotonic()>=end:raise Unavailable()
            try:b=sock.recv(n-len(data))
            except (socket.timeout,ssl.SSLWantReadError,ssl.SSLWantWriteError):continue
            if not b:raise Unavailable()
            data.extend(b)
        if time.monotonic()>=end:raise Unavailable()
        return bytes(data)
    def _head(self,sock):
        data=bytearray();end=time.monotonic()+2
        while not data.endswith(b'\r\n\r\n'):
            if len(data)>=16384:raise Unavailable()
            data.extend(self._read(sock,1,end))
        return request_head(bytes(data))
    def _reply(self,peer,status,mime,payload,extra=''):
        headers=('HTTP/1.1 '+status+'\r\nContent-Type: '+mime+'\r\nContent-Length: '+str(len(payload))+
            '\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\n'+
            "Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self' wss://127.0.0.1:"+str(self.port)+"; media-src 'self' blob:; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'\r\n"+extra+'\r\n').encode('ascii')
        peer.raw(headers+payload)
    def _http(self,peer):
        method,path,h=self._head(peer.sock)
        if h.get('host')!=self.host:raise Unavailable()
        if method=='GET' and path in self.assets:
            if h.get('content-length','0')!='0' or 'upgrade' in h:raise Unavailable()
            mime,data=self.assets[path];self._reply(peer,'200 OK',mime,data);return
        if method=='POST' and path=='/session':
            if h.get('origin')!=self.origin or h.get('content-type')!='application/json' or h.get('content-length')!='2':raise Unavailable()
            if self._read(peer.sock,2,time.monotonic()+.5)!=b'{}':raise Unavailable()
            rid,stream,credential=self.gateway.request();r=self.gateway.routes[rid]
            try:
                payload=json.dumps(dict(route='/s/'+rid,streamId=stream),separators=(',',':')).encode()
                self._reply(peer,'201 Created','application/json',payload,
                    'Set-Cookie: walk='+credential+'; Path=/s/'+rid+'/; Secure; HttpOnly; SameSite=Strict\r\n')
            except Exception:self.gateway.revoke(r);raise
            return
        if method!='GET':raise Unavailable()
        accept,r,role=self.admit_upgrade(path,h)
        try:
            # Authenticate before upgrade; no queued unauthenticated peer is
            # handed to the gateway. A failed one-shot upgrade revokes its route.
            peer.raw(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+accept+'\r\n\r\n').encode('ascii'))
            self.gateway.attach(r,role,peer)
            while not self.stop_event.is_set() and not peer.closed:
                try:first=peer.sock.recv(1)
                except (socket.timeout,ssl.SSLWantReadError,ssl.SSLWantWriteError):continue
                if not first:break
                end=time.monotonic()+.5;prefix=bytearray(first)
                def read(n):
                    take=bytes(prefix[:n]);del prefix[:n]
                    return take+self._read(peer.sock,n-len(take),end)
                op,payload=read_frame(read)
                if op==8:break
                if op==9:peer.raw(server_frame(payload,10))
                elif op==1:self.gateway.receive(r,role,payload.decode('utf-8'))
        finally:self.gateway.revoke(r)
    def admit_upgrade(self,path,h):
        """Shared real HTTP upgrade authority; caller must dispose on failure."""
        if h.get('host')!=self.host:raise Unavailable()
        accept=upgrade(h)
        native=re.fullmatch('/stream/([A-Za-z0-9_-]{1,128})',path)
        browser=re.fullmatch('/s/([a-f0-9]{32})/(player|control)',path)
        if native:
            if 'origin' in h or not h.get('authorization','').startswith('Bearer '):raise Unavailable()
            r=self.gateway.authenticate_streamer(native[1],h['authorization'][7:]);role='streamer'
        elif browser:
            if h.get('origin')!=self.origin or 'authorization' in h:raise Unavailable()
            r=self.gateway.authenticate_browser(browser[1],cookie_value(h));role=browser[2]
        else:raise Unavailable()
        return accept,r,role
    def _worker(self,sock):
        peer=None
        try:
            sock.settimeout(2)
            sock=self.tls.wrap_socket(sock,server_side=True)
            sock.settimeout(.05);peer=Peer(sock)
            with self.worker_lock:self.workers[threading.current_thread()]=sock
            self._http(peer)
        except Exception:
            pass # never print request, exception, credentials, SDP or peer diagnostics
        finally:
            try:
                if peer:peer.close()
                else:sock.close()
            except Exception:
                self.quarantined=True
                return # close may invalidate a handle; retain uncertainty, no retry proof
            with self.worker_lock:self.workers.pop(threading.current_thread(),None)
    def serve(self):
        """Explicit future launch only, after host.prepare and deployment review."""
        if self.started:raise Unavailable()
        self.started=True
        try:
            self.listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            if hasattr(socket,'SO_EXCLUSIVEADDRUSE'):self.listener.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
            self.listener.bind(('127.0.0.1',self.port));self.listener.listen(self.limit);self.listener.settimeout(.05)
            while not self.stop_event.is_set():
                self.gateway.tick() # even with no peers; no lease renewal
                try:sock,address=self.listener.accept()
                except socket.timeout:continue
                with self.worker_lock:
                    if address[0]!='127.0.0.1' or len(self.workers)>=self.limit:sock.close();continue
                    worker=threading.Thread(target=self._worker,args=(sock,),daemon=True)
                    self.workers[worker]=sock
                    try:worker.start()
                    except Exception:sock.close();del self.workers[worker];raise
        finally:self.close()
    def close(self):
        self.stop_event.set();error=self.quarantined
        # Stop accepting first; authority then revokes all routes and exact Jobs.
        if self.listener:
            try:self.listener.close();self.listener=None
            except Exception:error=True
        try:self.gateway.shutdown()
        except Exception:error=True
        end=time.monotonic()+2.5
        with self.worker_lock:workers=list(self.workers.items())
        for thread,sock in workers:
            try:sock.close()
            except Exception:error=True
        for thread,sock in workers:
            if thread is not threading.current_thread():thread.join(max(0,end-time.monotonic()))
            if thread.is_alive():error=True
        if error:raise Unavailable() # caller retains host/server; never declare capacity free

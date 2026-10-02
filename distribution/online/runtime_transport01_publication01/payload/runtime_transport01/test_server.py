"""Production HTTP/WebSocket parser/dispatch on byte adapters; no sockets opened."""
import base64,json,socket,ssl,struct,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runtime_transport01.server import Server,Peer,read_frame,server_frame,request_head,upgrade
from runtime_transport01.gateway import Unavailable
from test_gateway import Host

class BytesSocket:
    def __init__(self,data=b''):self.data=data;self.sent=bytearray();self.closed=False
    def recv(self,n):b=self.data[:n];self.data=self.data[n:];return b
    def send(self,b):self.sent.extend(b);return len(b)
    def close(self):self.closed=True

def client_frame(payload=b'{}',op=1):
    mask=b'abcd';n=len(payload)
    head=bytes([128|op,128|n]) if n<126 else bytes([128|op,254])+struct.pack('!H',n)
    return head+mask+bytes(c^mask[i%4] for i,c in enumerate(payload))

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.host=Host();tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.minimum_version=ssl.TLSVersion.TLSv1_2
        self.server=Server(self.host,19443,tls,{'/':('text/html; charset=utf-8',b'page'),'/app.js':('text/javascript; charset=utf-8',b'js'),'/style.css':('text/css; charset=utf-8',b'css')})
        self.host.processes.revoke=self.server.gateway.process_revoked
    def http(self,head,tail=b''):
        s=BytesSocket(head.encode('ascii')+tail);p=Peer(s);self.server._http(p);return s
    def upgrade_head(self,path,extra=''):
        return 'GET '+path+' HTTP/1.1\r\nHost: 127.0.0.1:19443\r\nUpgrade: websocket\r\nConnection: keep-alive, Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: '+base64.b64encode(b'0123456789abcdef').decode()+'\r\n'+extra+'\r\n'
    def test_construct_no_socket(self):
        with patch('socket.socket',side_effect=AssertionError('No acquisition')):
            self.setUp()
    def test_post_dispatch_actual_host_sets_path_scoped_cookie(self):
        s=self.http('POST /session HTTP/1.1\r\nHost: 127.0.0.1:19443\r\nOrigin: https://127.0.0.1:19443\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n',b'{}')
        head,body=bytes(s.sent).split(b'\r\n\r\n',1);m=json.loads(body)
        self.assertIn(('Path='+m['route']+'/; Secure; HttpOnly; SameSite=Strict').encode(),head)
        self.assertEqual(set(m),{'route','streamId'})
        self.assertEqual([p['operation'] for p in self.host.processes.commands],['open','bind','stream'])
    def test_native_upgrade_authenticated_then_disconnect_cleans_owner(self):
        rid,sid,_=self.server.gateway.request();ticket=self.host.processes.commands[-1]['event']['ticket']
        frame=client_frame(json.dumps(dict(type='endpointId',id=sid)).encode())
        s=self.http(self.upgrade_head('/stream/'+sid,'Authorization: Bearer '+ticket+'\r\n'),frame)
        self.assertTrue(s.sent.startswith(b'HTTP/1.1 101'))
        self.assertFalse(self.server.gateway.routes);self.assertFalse(self.host.processes.records)
    def test_wrong_native_auth_never_upgrades(self):
        rid,sid,_=self.server.gateway.request();s=BytesSocket(self.upgrade_head('/stream/'+sid,'Authorization: Bearer '+'0'*64+'\r\n').encode())
        with self.assertRaises(Unavailable):self.server._http(Peer(s))
        self.assertFalse(s.sent)
    def test_browser_auth_and_origin_before_upgrade(self):
        rid,sid,c=self.server.gateway.request()
        for extra in ['Cookie: walk='+c+'\r\n','Origin: https://foreign.invalid\r\nCookie: walk='+c+'\r\n','Origin: https://127.0.0.1:19443\r\nCookie: walk=wrong\r\n']:
            s=BytesSocket(self.upgrade_head('/s/'+rid+'/control',extra).encode())
            with self.assertRaises(Unavailable):self.server._http(Peer(s))
            self.assertFalse(s.sent)
    def test_duplicate_cookie_rejected(self):
        rid,sid,c=self.server.gateway.request()
        with self.assertRaises(Unavailable):self.http(self.upgrade_head('/s/'+rid+'/control','Origin: https://127.0.0.1:19443\r\nCookie: walk='+c+'; walk='+c+'\r\n'))
    def test_http_duplicate_length_transfer_encoding_and_traversal(self):
        for raw in [b'GET / HTTP/1.1\r\nHost: a\r\nHost: b\r\n\r\n',b'POST /session HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n']:
            with self.assertRaises(Unavailable):request_head(raw)
        with self.assertRaises(Unavailable):self.http('GET /../config HTTP/1.1\r\nHost: 127.0.0.1:19443\r\n\r\n')
    def test_valid_masked_text_and_server_frame(self):
        data=BytesSocket(client_frame(b'hello'));self.assertEqual(read_frame(data.recv),(1,b'hello'))
        self.assertEqual(server_frame(b'hello'),b'\x81\x05hello')
    def test_no_fragment_binary_unmasked_or_oversized(self):
        for b in [b'\x01\x80',b'\x82\x80',b'\x81\x00',b'\x81\xff'+struct.pack('!Q',65537),b'\x89\xfe'+struct.pack('!H',126)]:
            with self.assertRaises(Unavailable):read_frame(BytesSocket(b).recv)
    def test_partial_frame_shares_absolute_deadline(self):
        class Slow(BytesSocket):
            def recv(s,n):clock[0]+=.3;return super(Slow,s).recv(min(1,n))
        clock=[100.]
        with patch('runtime_transport01.server.time.monotonic',side_effect=lambda:clock[0]):
            with self.assertRaises(Unavailable):self.server._read(Slow(b'abc'),3,100.5)
    def test_close_failure_quarantines_even_if_retry_would_succeed(self):
        class Bad(BytesSocket):
            def close(s):
                if not s.closed:s.closed=True;raise OSError('private detail')
        peer=Peer(Bad())
        for _ in range(2):
            with self.assertRaisesRegex(Unavailable,'^Session unavailable$'):peer.close()
        self.assertFalse(peer.disposed)
    def test_wrong_public_host_rejected(self):
        with self.assertRaises(Unavailable):self.http('GET / HTTP/1.1\r\nHost: public.example\r\n\r\n')

if __name__=='__main__':unittest.main(verbosity=2)

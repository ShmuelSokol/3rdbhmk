"""Bounded offline test child: production HTTP/Gateway/Core, native byte adapter.

Never a deployment server or mock video. No listener, process host or UE starts.
Stdio test responses stay inside the owned test process; do not save raw traffic.
"""
import base64,json,ssl,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_gateway import Host,Peer as MessagePeer
from test_server import BytesSocket
from runtime_transport01.server import Server,Peer,request_head

host=Host();tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.minimum_version=ssl.TLSVersion.TLSv1_2
server=Server(host,19443,tls,{'/':('text/html; charset=utf-8',b''),'/app.js':('text/javascript; charset=utf-8',b''),'/style.css':('text/css; charset=utf-8',b'')})
host.processes.revoke=server.gateway.process_revoked
peers={};connections={}
def drain():
    out={}
    for k,p in peers.items():out[k]={'messages':p.messages[:],'closed':p.closed};p.messages.clear()
    return out

def dispatch(m):
    op=m['op'];extra={}
    if op=='post':
        sock=BytesSocket(b'POST /session HTTP/1.1\r\nHost: 127.0.0.1:19443\r\nOrigin: https://127.0.0.1:19443\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}')
        server._http(Peer(sock));head,body=bytes(sock.sent).split(b'\r\n\r\n',1)
        extra={'body':json.loads(body),'cookie':next(line[12:].split(';',1)[0] for line in head.decode().split('\r\n') if line.startswith('Set-Cookie: '))}
    elif op=='upgrade':
        raw=('GET '+m['path']+' HTTP/1.1\r\nHost: 127.0.0.1:19443\r\nOrigin: https://127.0.0.1:19443\r\nCookie: '+m['cookie']+'\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: MDEyMzQ1Njc4OWFiY2RlZg==\r\n\r\n').encode()
        method,path,h=request_head(raw);accept,r,role=server.admit_upgrade(path,h)
        peer=MessagePeer();peers[m['path']]=peer;connections[m['path']]=(r,role)
        server.gateway.attach(r,role,peer)
    elif op=='message':
        r,role=connections[m['path']];server.gateway.receive(r,role,m['text'])
    elif op=='native':
        r=next(iter(server.gateway.routes.values()));packet=next(p for p in host.processes.commands if p['operation']=='stream')
        ticket=packet['event']['ticket'];sid=r.binding.owner.stream_id
        h={'host':server.host,'upgrade':'websocket','connection':'Upgrade','sec-websocket-version':'13','sec-websocket-key':'MDEyMzQ1Njc4OWFiY2RlZg==','authorization':'Bearer '+ticket}
        accept,r,role=server.admit_upgrade('/stream/'+sid,h)
        p=MessagePeer();server.gateway.attach(r,role,p)
        server.gateway.receive(r,role,json.dumps({'type':'endpointId','id':sid}))
    elif op=='close':
        if m['path'] in connections:server.gateway.revoke(connections[m['path']][0])
    elif op=='snapshot':
        extra={'subscribed':any(r.subscribed for r in server.gateway.routes.values()),
            'routes':len(server.gateway.routes),'processes':len(host.processes.records),
            'inputs':sum(p['operation']=='input' for p in host.processes.commands),
            'operations':[p['operation'] for p in host.processes.commands]}
    elif op=='shutdown':server.gateway.shutdown()
    else:raise ValueError()
    return dict(ok=True,peers=drain(),**extra)

try:
    for _ in range(300):
        raw=sys.stdin.buffer.readline(70000)
        if not raw:break
        if len(raw)>68000 or not raw.endswith(b'\n'):break
        try:response=dispatch(json.loads(raw))
        except Exception:response={'ok':False,'peers':drain()}
        print(json.dumps(response,separators=(',',':')),flush=True)
finally:server.gateway.shutdown()

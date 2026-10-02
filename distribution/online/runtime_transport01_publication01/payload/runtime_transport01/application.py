"""Actual host + transport construction, deliberately no implicit prepare/serve.

Deployment supplies real immutable executable recipe, exclusive settings premise,
and a server SSLContext with a certificate trusted by BOTH browser and native UE.
There is no always-valid lease/premise, generated certificate, or TLS bypass.
"""
import hashlib
import json
from pathlib import Path
from session_core import Limits
from runtime_transport01.gateway import Unavailable
from runtime_transport01.server import Server

def load_assets(directory,manifest_sha256):
    root=Path(directory).resolve()
    for p in (root,*root.parents):
        if p.is_symlink() or getattr(p.stat(),'st_file_attributes',0)&0x400:raise Unavailable()
    raw=(root/'assets.json').read_bytes()
    if len(raw)>4096 or hashlib.sha256(raw).hexdigest()!=manifest_sha256:raise Unavailable()
    m=json.loads(raw)
    if m.get('commit')!='6b8cfb460bda09703e85178f1f77aa6faec9e890' or set(m['files'])!={'app.js','index.html','style.css'}:raise Unavailable()
    out={}
    for n,url,mime in [('app.js','/app.js','text/javascript; charset=utf-8'),('index.html','/','text/html; charset=utf-8'),('style.css','/style.css','text/css; charset=utf-8')]:
        p=root/n
        if p.is_symlink() or getattr(p.stat(),'st_file_attributes',0)&0x400 or p.stat().st_size>8*1024**2:raise Unavailable()
        b=p.read_bytes()
        if hashlib.sha256(b).hexdigest()!=m['files'][n]:raise Unavailable()
        out[url]=(mime,b)
    return out

def compose_application(recipe,ipc_ports,spec,premise,tls,media_port,assets,limits=Limits()):
    # Imported only from the guarded composed derivative, never an unrelated live
    # settings host. Constructor creates no child, handle, listener or media.
    from runtime_transport01.managed_host import AllocatedHost
    holder={}
    def revoke(owner):
        if 'server' not in holder:raise Unavailable()
        holder['server'].gateway.process_revoked(owner)
    host=AllocatedHost(recipe,ipc_ports,revoke,spec,premise,limits)
    server=Server(host,media_port,tls,assets);holder['server']=server
    return server # explicit future host.prepare(); server.serve(); finally server.close()

"""Compose frozen flight01 with real owned media hook; source only."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parent
P='P/Source/Receiver04Compile/Private/'
BASE='6a7562cd53c78bd451850a507efdf38ffabf32c988cb61ee3241881c97695b1f'
def sha(b):return hashlib.sha256(b).hexdigest()
def once(s,a,b):
    if s.count(a)!=1:raise ValueError('Exact source anchor mismatch')
    return s.replace(a,b,1)
def build(base,media_recipe):
    raw=(base/'allowlist.json').read_bytes()
    if sha(raw)!=BASE:raise ValueError('Frozen flight closure changed')
    out={}
    for e in json.loads(raw)['entries']:
        b=(base/e['path']).read_bytes()
        if sha(b)!=e['sha256']:raise ValueError('Source changed')
        out[e['path']]=b
    pins=json.loads((ROOT/'recipe-pins.json').read_text())
    upstream=(ROOT.parent/'upstream-lock.json').read_bytes()
    if sha(upstream)!=pins['upstream-lock.json']:raise ValueError('Official upstream pin changed')
    out['upstream-lock.json']=upstream
    if sha(media_recipe.read_bytes())!=pins['media_overlay.py']:raise ValueError('Media insertion recipe changed')
    spec=importlib.util.spec_from_file_location('owned_media_overlay',media_recipe)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.apply(out,ROOT,once)
    def edit(n,f):out[P+n]=f(out[P+n].decode()).encode()
    def wire(s):
        return once(s,'Shape(**E,{TEXT("port")})&&Number(**E,TEXT("port"),Out.x,1024,65535)&&Out.x==FMath::FloorToDouble(Out.x);', '''Shape(**E,{TEXT("port"),TEXT("ticket"),TEXT("until")})&&
            Number(**E,TEXT("port"),Out.x,1024,65535)&&Out.x==FMath::FloorToDouble(Out.x)&&
            Text(**E,TEXT("ticket"),Out.action)&&Out.action.size()==64&&
            Number(**E,TEXT("until"),Out.y,0,1099511627776.0);''')
    edit('Native/receiver03/Wire.cpp',wire)
    edit('Native/receiver04/Bootstrap.h',lambda s:once(s,'    bool AuthenticatedLifecycle(const Packet& P);',
        '    bool AuthenticatedLifecycle(const Packet& P);\n    bool AttachOwnedMedia(const Packet& P);'))
    def boot(s):
        s=once(s,'#include "Bootstrap.h"','#include "Bootstrap.h"\n#include "MikdashOwnedRtc.h"')
        start=s.index('    if(P.operation=="stream") {');end=s.index('    if(P.operation!="bind")return false;',start)
        s=s[:start]+'    if(P.operation=="stream")return AttachOwnedMedia(P);\n'+s[end:]
        s=once(s,'bool Bootstrap::Shutdown() {',(ROOT/'NativeMedia.cpp.inc').read_text()+'\nbool Bootstrap::Shutdown() {')
        return once(s,'    if(Busy)return false;\n    const bool Closed=',
            '    if(Busy)return false;\n    UE::PixelStreaming2::MikdashRevokeOwnedRtc(Streamer);\n    const bool Closed=')
    edit('Native/receiver04/Bootstrap.cpp',boot)
    module='P/Source/Receiver04Compile/Receiver04Compile.Build.cs'
    out[module]=once(out[module].decode(),'"PixelStreaming2Core", "PixelStreaming2Input"',
        '"PixelStreaming2Core", "PixelStreaming2Input", "PixelStreaming2RTC"').encode()
    managed=out['runtime_flight01/managed_host.py'].decode()
    managed=once(managed,'from runtime_flight01.host import FlightAuthority,FlightStreams,FlightProcesses',
        'from runtime_flight01.host import FlightAuthority,FlightStreams\nfrom runtime_transport01.owned_host import TransportProcesses')
    managed=once(managed,'self.processes=FlightProcesses(', 'self.processes=TransportProcesses(')
    begin=managed.index('def verify_sources():');end=managed.index('class AllocatedHost:',begin)
    managed=managed[:begin]+'def verify_sources():\n    from runtime_transport01.integrity import verify_host_sources\n    verify_host_sources()\n\n'+managed[end:]
    out['runtime_transport01/managed_host.py']=managed.encode()
    for name in ('owned_host.py','gateway.py','server.py','application.py','integrity.py','entry.mjs','index.html','style.css','build.mjs'):
        out['runtime_transport01/'+name]=(ROOT/name).read_bytes()
    main=once(out['browser/main.mjs'].decode(),
        '// Admission/reconnect HTTP endpoints are deliberately not fabricated by this slice.',
        '// transport01 entry performs private-cookie HTTP admission before mounting.')
    main=once(main,'  let stopped=false, timer;', '  let stopped=false, timer, controls=null, port=null;')
    main=once(main,'stopped=true; clearInterval(timer); abort.abort(); controls.disconnect(); stream.disconnect();',
        'stopped=true; clearInterval(timer); abort.abort();\n    try { if(controls)controls.disconnect(); else port?.close(); } finally { stream.disconnect(); }')
    main=once(main,'  const resetPointers=[];', '  const resetPointers=[];\n  try {')
    main=once(main,'  const port=new ControlPort(', '  port=new ControlPort(')
    main=once(main,'  const controls=new Controls(port);', '  controls=new Controls(port);')
    main=once(main,'  return {disconnect:stop};',
        "  return {disconnect:stop};\n  } catch { stop(); throw Error('Stream mount unavailable'); }")
    out['browser/main.mjs']=main.encode()
    return out
def stage(base,media_recipe,dest):
    if dest.exists():raise ValueError('Fresh destination required')
    for q in (base,*base.parents,dest,*dest.parents):
        if q.exists() and (q.is_symlink() or getattr(q.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Reparse refused')
    out=build(base,media_recipe);dest.mkdir(parents=True);entries=[]
    for n,b in sorted(out.items()):
        p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        entries.append(dict(path=n,bytes=len(b),sha256=sha(b)))
    raw=(json.dumps(dict(schema=1,entries=entries),indent=2)+'\n').encode();(dest/'allowlist.json').write_bytes(raw)
    return dict(files=len(entries)+1,manifestSha256=sha(raw),ueCompiled=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True,type=Path);p.add_argument('--media-recipe',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    print(json.dumps(stage(a.base,a.media_recipe,a.output)))

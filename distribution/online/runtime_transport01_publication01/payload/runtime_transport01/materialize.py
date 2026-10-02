"""Fresh private licensed plugin staging only; no engine/build/process execution.

Run on a portable exact export. Adds the pinned installed plugin source locally,
never to publication. No junctions or plugin binaries are copied.
"""
import argparse,hashlib,importlib.util,json
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def clean(p):
    p=Path(p).absolute()
    for q in (p,*p.parents):
        if q.exists() and (q.is_symlink() or getattr(q.lstat(),'st_file_attributes',0)&0x400):raise ValueError('Reparse refused')
    return p.resolve()
def materialize(source,dest,engine,expected):
    source,dest,engine=map(clean,(source,dest,engine))
    if dest.exists() or source in dest.parents:raise ValueError('Fresh separate destination required')
    raw=(source/'allowlist.json').read_bytes()
    if sha(raw)!=expected:raise ValueError('Export changed')
    entries=json.loads(raw)['entries'];out={}
    for e in entries:
        n=e['path']
        if '..' in Path(n).parts or Path(n).is_absolute():raise ValueError('Bad path')
        b=clean(source/n).read_bytes()
        if sha(b)!=e['sha256'] or len(b)!=e['bytes']:raise ValueError('Export changed')
        out[n]=b
    if {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}!=set(out)|{'allowlist.json'}:raise ValueError('Unexpected export file')
    spec=importlib.util.spec_from_file_location('private_plugin_recipe',source/'runtime_transport01/plugin_recipe.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    plugin=engine/'Engine/Plugins/Media/PixelStreaming2'
    clone=module.local_clone(plugin)
    for n,b in clone.items():out['P/Plugins/PixelStreaming2/'+n]=b
    context=json.loads(out['source-context.json'])
    pins=json.loads((source/'runtime_transport01/plugin-source-pins.json').read_text())
    for n,h in pins.items():context['engineFiles'].append({'path':'Engine/Plugins/Media/PixelStreaming2/'+n,'sha256':h})
    context['transportRequiredObjects']=['MikdashOwnedRtc.cpp.obj','EpicRtcStreamer.cpp.obj','PixelStreaming2RTCModule.cpp.obj']
    context['transportScope']='Exact local-plugin source/UHT/object/API proof required; no runtime evidence'
    out['source-context.json']=(json.dumps(context,indent=2)+'\n').encode()
    dest.mkdir()
    for n,b in out.items():
        p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    raw=(json.dumps({'schema':1,'entries':[{'path':n,'bytes':len(b),'sha256':sha(b)} for n,b in sorted(out.items())]},indent=2)+'\n').encode()
    (dest/'allowlist.json').write_bytes(raw)
    return {'files':len(out)+1,'localPluginSourceFiles':len(clone),'manifestSha256':sha(raw),'privateEngineCode':True,'binariesCopied':0,'engineExecuted':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--engine',required=True,type=Path);p.add_argument('--manifest',required=True)
    a=p.parse_args();print(json.dumps(materialize(a.source,a.output,a.engine,a.manifest)))

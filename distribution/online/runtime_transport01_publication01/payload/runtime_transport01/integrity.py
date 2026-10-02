"""Exact portable runtime source pins; generated constant, never a bool provider.

This replaces ONLY historical author-path preparation checks in the additive
TransportProcesses/managed-host derivative. All settings admission/lease/cleanup
implementations remain unchanged. Deployment files must remain immutable.
"""
import hashlib,json,re
from pathlib import Path
from session_core import SessionError
EXPECTED = '29d54c5f9a595e3a0e363bf04ed3d4c05351edbfc8027a005ee26cc5797701ca' # substituted only by the exact portable closure preparer

def verify_host_sources():
    try:
        root=Path(__file__).resolve().parent.parent
        raw=(root/'runtime_transport01/host-pins.json').read_bytes()
        if EXPECTED is None or len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=EXPECTED:raise ValueError()
        pins=json.loads(raw)
        for name,h in pins.items():
            if not re.fullmatch(r'[A-Za-z0-9_./-]+',name) or '..' in Path(name).parts or Path(name).is_absolute():raise ValueError()
            p=root/name
            for q in (p,*p.parents):
                if q.is_symlink() or getattr(q.stat(),'st_file_attributes',0)&0x400:raise ValueError()
            if hashlib.sha256(p.read_bytes()).hexdigest()!=h:raise ValueError()
    except Exception:raise SessionError('Portable host source verification failed') from None

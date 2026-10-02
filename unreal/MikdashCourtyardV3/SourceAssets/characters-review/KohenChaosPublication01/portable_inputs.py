"""Explicit replay-only I/O adapter; no replacement physics or native authority.

Original reviewed V3 numerical modules are imported unchanged. This adapter
binds portable source/fixture/output roots and verifies the publication closure.
It NEVER reports that excluded private V2 preservation files were verified.
"""
import sys,json,hashlib
from pathlib import Path
import numpy as np
HERE=None;V2=None;s=None;ROOT=None;CHECKS=None

def configure(project,fixture,output,checks):
    global HERE,V2,s,ROOT,CHECKS
    ROOT=Path(project);HERE=Path(output);V2=Path(fixture);CHECKS=checks
    sys.path.insert(0,str(ROOT/'SourceAssets/characters-review/KohenBothLayerDrapeV2'))
    import study
    s=study

def preserved():
    for path,h in CHECKS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=h:raise ValueError('Portable input changed')
    # Compatibility return consumed only by historical receipt metadata. Zero
    # explicitly means NO V2 private-history count; write() labels it accordingly.
    return 0

def load():
    preserved();model=json.loads((s.OLD/'prepared-input.json').read_text())
    bones,index,parts,influence,*_=s.source_parts();by={p['name']:p for p in parts}
    c=s.Layer(model['patterns'][1]);rest=np.asarray(by['Ketonet']['vertices']);faces=np.asarray(by['Ketonet']['faces'])
    mp=s.mapping(rest,c.rest,c.f);rig=s.P.M.Rig(s.P.M.CLIPS[0][1],s.P.M.CLIPS[0][2])
    return model,bones,index,by,c,rest,faces,mp,rig

def pose(rig,bones,t):return s.P.M.joint_affines(rig,rig.pose(t),bones)

def write(name,value):
    path=HERE/name
    if path.parent!=HERE or path.exists():raise ValueError('Fresh direct-child output required')
    value=dict(value)
    value.pop('V2FilesPreserved',None)
    value.update(publicationInputsVerified=len(CHECKS),privateAuthorHistoryReplayed=False,
                 replayIOAdapter=True,native=False,garmentAcceptance=False)
    s.atomic(path,value)

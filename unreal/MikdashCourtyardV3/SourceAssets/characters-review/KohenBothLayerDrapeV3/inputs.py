import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;V2=HERE.parent/'KohenBothLayerDrapeV2'
sys.path.insert(0,str(V2))
import study as s

V2_FREEZE='66e05261876d6091b9217aba314f9fddb968854a4e0ea3050239b7990cfdf273'
def preserved():
    assert s.sha(V2/'freeze.json')==V2_FREEZE
    pins=json.loads((V2/'freeze.json').read_text())['files']
    assert all(s.sha(V2/p)==h for p,h in pins.items())
    return len(pins)

def load():
    preserved();model=json.loads((s.OLD/'prepared-input.json').read_text())
    bones,index,parts,influence,*_=s.source_parts();by={p['name']:p for p in parts}
    p=model['patterns'][1];c=s.Layer(p);rest=np.asarray(by['Ketonet']['vertices']);faces=np.asarray(by['Ketonet']['faces'])
    mp=s.mapping(rest,c.rest,c.f);rig=s.P.M.Rig(s.P.M.CLIPS[0][1],s.P.M.CLIPS[0][2])
    return model,bones,index,by,c,rest,faces,mp,rig

def pose(rig,bones,t):return s.P.M.joint_affines(rig,rig.pose(t),bones)

def write(name,value):
    path=HERE/name;assert path.parent==HERE;s.atomic(path,value)

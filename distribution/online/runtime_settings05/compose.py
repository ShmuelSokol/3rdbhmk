"""Return reviewed additive overlay for McClintock's ONE composed project.

No launch or build. Frozen candidate05 source is verified before exact-anchor
transformation. Existing v1 validator stays byte-semantically unchanged; only
this new project's stopped private reader accepts v2. No receiver04 pipe/read.
"""
from pathlib import Path
import hashlib,json
BASE=Path(__file__).resolve().parent
ROOT=BASE.parent
PREFIX='P/Source/Receiver04Compile/Private/'

def once(s,a,b):
    if s.count(a)!=1:raise ValueError('Composition anchor mismatch')
    return s.replace(a,b,1)

def overlay():
    pins=json.loads((BASE/'prerequisites.json').read_text())
    for n,h in pins.items():
        if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise ValueError('Prerequisite changed: '+n)
    s=(ROOT/'runtime_candidate05/PrivateBootstrap.cpp').read_text()
    s=once(s,'#include "PrivateBootstrap.h"','#include "PrivateBootstrap.h"\n#include "../runtime_settings05/NativeLease.h"')
    s=once(s,'ValidatePrivateRecord(Body,Last,*Provisioning)','Settings05::AdmitPrivateV2(Body,Last,*Provisioning)')
    s=once(s,'if(!Valid||!Fresh(ReadEnd)||!Fresh(Provisioning->Deadline))',
        'if(!Valid||!Settings05::LeaseLive()||!Fresh(ReadEnd)||!Fresh(Provisioning->Deadline))')
    s=once(s,'if(Stopping||!Admitted||!Fresh(ReadEnd)||!Fresh(Provisioning->Deadline))',
        'if(Stopping||!Admitted||!Settings05::LeaseLive()||!Fresh(ReadEnd)||!Fresh(Provisioning->Deadline))')
    s=once(s,'if(Phase==State::StoppedProvisioned&&(!Provisioning||',
        'if(Phase==State::StoppedProvisioned&&(!Settings05::LeaseLive()||!Provisioning||')
    s=once(s,'const bool InputClosed=CloseInput();','const bool LeaseClosed=Settings05::RevokeLease();\n    const bool InputClosed=CloseInput();')
    s=once(s,'Phase=InputClosed&&HostClosed?', 'Phase=LeaseClosed&&InputClosed&&HostClosed?')
    # Case-correct paths in the composed project (existing composer uses Native).
    s=s.replace('../native/','../Native/')
    out={PREFIX+'runtime_candidate05/PrivateBootstrap.cpp':s.encode()}
    for name in ('PrivateEnvelope.h','WinLease.h','NativeLease.h','NativeLease.cpp'):
        out[PREFIX+'runtime_settings05/'+name]=(BASE/name).read_bytes()
    # Concrete ingestion call for the existing optional seam; no ownership bit.
    out[PREFIX+'integration01/SettingsV2Api.cpp']=b'''#include "../runtime_settings05/NativeLease.h"
#include "MikdashPlayerController.h"
TFunction<bool()> ReceiverIntegrationSettingsV2Api(const MikdashOnline::Owner& Owner,AMikdashPlayerController* Controller){
    return MikdashOnline::Settings05::MakeOwnedSettingsCallback(Owner,Controller);
}
'''
    return out

if __name__=='__main__':
    print(json.dumps({n:hashlib.sha256(b).hexdigest() for n,b in overlay().items()},indent=2))

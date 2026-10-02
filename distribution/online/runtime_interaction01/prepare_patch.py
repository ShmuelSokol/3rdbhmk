"""Deterministic review-only export. Never edits any source input or live project."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json

ROOT=Path(__file__).resolve().parent

def sha(data):return hashlib.sha256(data).hexdigest()

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Exact patch anchor mismatch')
    return text.replace(old,new,1)

def build():
    spec=json.loads((ROOT/'source-pins.json').read_text());original={}
    for path,digest in spec['dependencySha256'].items():
        if sha((ROOT/path).read_bytes())!=digest:raise ValueError('Dependency pin drift')
    for entry in spec['sources']:
        data=(ROOT/entry['source']).read_bytes()
        if sha(data)!=entry['sha256']:raise ValueError('Pinned baseline drift; no output written')
        snapshot=(ROOT/entry['snapshot']).read_bytes()
        if snapshot!=data:raise ValueError('Snapshot mismatch')
        original[entry['role']]=data
    header=original['project-header'].decode('utf-8').replace('\r\n','\n')
    header=once(header,'#include "ResidentDialogState.h"','#include "ResidentDialogState.h"\n#include "ResidentTalkAction.h"')
    declaration='    UFUNCTION(BlueprintCallable, Category="Residents") void TalkToNearbyResident();'
    header=once(header,declaration,declaration+'\n    // Native-only result API. No default authorization callback.\n    MikdashDialog::TalkOutcome TryTalkToNearbyResident(const TFunction<bool()>& LastBranch);')
    header=once(header,'    MikdashDialog::Conversation Conversation;','    bool bTalkAttemptActive = false;\n    MikdashDialog::Conversation Conversation;')
    cpp=original['project-cpp'].decode('utf-8').replace('\r\n','\n')
    start=cpp.index('void AMikdashPlayerController::TalkToNearbyResident()\n')
    end=cpp.index('void AMikdashPlayerController::CloseResidentDialog()',start)
    cpp=cpp[:start]+(ROOT/'try_talk_replacement.txt').read_text().rstrip()+'\n\n'+cpp[end:]
    cpp=once(cpp,'#include "MikdashPlayerController.h"','#include "MikdashPlayerController.h"\n#include "Templates/UnrealTemplate.h"')
    remote=original['remote-cpp'].decode('utf-8').replace('\r\n','\n')
    remote=once(remote,'#include "OnlineController.h"','#include "OnlineController.h"\n#include "../../runtime_interaction01/RemoteResidentInteraction.h"')
    old='''            if(Action=="interact"&&ConsumeInteract){
                // Callback must perform its own last-branch check if it scans or
                // blocks before changing dialog state, and return an explicit outcome.
                return ConsumeInteract(Fence);
            }'''
    new='''            if(Action=="interact"){
                // Explicit project consumption API; never infer Applied from void.
                return MikdashOnline::Interaction01::ConsumeResidentInteraction(*this,Remote.ToSharedRef(),Fence);
            }'''
    remote=once(remote,old,new)
    outputs={
        'project/Public/MikdashPlayerController.h':header.encode(),
        'project/Private/MikdashPlayerController.cpp':cpp.encode(),
        'project/Public/ResidentTalkAction.h':(ROOT/'ResidentTalkAction.h').read_bytes(),
        'online/native/receiver04/OnlineController.cpp':remote.encode(),
        'online/runtime_interaction01/RemoteResidentInteraction.h':(ROOT/'RemoteResidentInteraction.h').read_bytes()}
    patch=''
    for role,name in [('project-header','project/Public/MikdashPlayerController.h'),('project-cpp','project/Private/MikdashPlayerController.cpp'),('remote-cpp','online/native/receiver04/OnlineController.cpp')]:
        before=original[role].decode().replace('\r\n','\n')
        patch+=''.join(difflib.unified_diff(before.splitlines(True),outputs[name].decode().splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    for name in ('project/Public/ResidentTalkAction.h','online/runtime_interaction01/RemoteResidentInteraction.h'):
        patch+=''.join(difflib.unified_diff([],outputs[name].decode().splitlines(True),fromfile='/dev/null',tofile='b/'+name))
    outputs['interaction.patch']=patch.encode()
    return outputs

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--export',type=Path)
    args=parser.parse_args();outputs=build()
    if args.export:
        target=args.export.resolve()
        if target.parent!=ROOT or target.exists():raise ValueError('New direct child of this candidate only')
        target.mkdir()
        for name,data in outputs.items():
            p=target/name;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(data)
    print(json.dumps({'status':'guarded-review-patch','outputs':{n:sha(d) for n,d in outputs.items()},'productionModified':False}))

if __name__=='__main__':main()

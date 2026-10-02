#pragma once
#include "CoreMinimal.h"

namespace MikdashOnline::Receiver04 {
// Executed by Bootstrap and directly testable with native call doubles. A failed
// close retains the handle identity but permanently forbids retry/use; only owned
// process exit can resolve this quarantine without guessing handle validity.
template<class Close> bool CloseBootstrapInput(void*& Input,bool& Poisoned,Close CloseHandle){
    if(Poisoned)return false;
    if(!Input)return true;
    if(!CloseHandle(Input)){Poisoned=true;return false;}
    Input=nullptr;return true;
}
template<class ControllerRef,class PawnRef,class InputRef,class StreamRef,class Clock>
bool BootstrapTargetsValid(const ControllerRef& Controller,const PawnRef& Pawn,const InputRef& Input,
                          const StreamRef& Streamer,double Deadline,Clock Now){
    if(!Controller.IsValid()||!Pawn.IsValid()||!Input.IsValid()||!Streamer.IsValid())return false;
    if(Controller->GetPawn()!=Pawn.Get()||Pawn->GetController()!=Controller.Get()||
       Controller->PlayerInput!=Input.Get()||!Controller->GetWorld()||!Controller->IsLocalController()||
       Streamer->IsStreaming())return false;
    const double Fresh=Now();return Fresh>=0&&Fresh<Deadline;
}
}

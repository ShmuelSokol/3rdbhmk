#include "Authority.h"
#include "../../integration01/PossessionTransitions.h"

namespace MikdashOnline::Receiver04 {
bool Authority::BeginPossession() {
    check(IsInGameThread());Maintain();
    bool OtherAwaiting=Awaiting;
    if(Flight.Consuming()) {
        if(!Awaiting||Waiting.action!="dove"||!Flight.Begin(NativeContext.controller,
            NativeContext.pawn,NativeContext.generation,Now())) {Abort();return false;}
        OtherAwaiting=false; // only the exact consumed flight receipt may cross possession
    }
    if(!Integration01::BeginPossession({Closed,OtherAwaiting,Possessing,NeedsRelease,
        NativeContext,PawnSerial,Connection,Mailbox})) { Abort();return false; }
    return true;
}
bool Authority::FinishPossession() {
    check(IsInGameThread());Maintain();
    if(!Integration01::FinishPossession({Closed,Awaiting,Possessing,NeedsRelease,
        NativeContext,PawnSerial,Connection,Mailbox})) { Abort();return false; }
    return true;
}
}

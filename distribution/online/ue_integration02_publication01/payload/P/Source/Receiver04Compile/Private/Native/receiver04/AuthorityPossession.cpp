#include "Authority.h"
#include "../../integration01/PossessionTransitions.h"

namespace MikdashOnline::Receiver04 {
bool Authority::BeginPossession() {
    check(IsInGameThread());Maintain();
    if(!Integration01::BeginPossession({Closed,Awaiting,Possessing,NeedsRelease,
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

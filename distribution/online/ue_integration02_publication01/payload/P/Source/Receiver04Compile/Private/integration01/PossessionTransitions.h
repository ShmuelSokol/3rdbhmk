#pragma once
#include "../native/receiver04/SemanticMailbox.h"

namespace MikdashOnline::Integration01 {
using Receiver04::Context;
using Receiver04::SemanticMailbox;
// References to the REAL Authority state, not a parallel simulation. The UE
// caller runs Maintain first and Abort on failure. No clock/lease extension here.
struct PossessionState {
    bool& Closed;
    bool& Awaiting;
    bool& Possessing;
    bool& NeedsRelease;
    Context& NativeContext;
    uint64_t& PawnSerial;
    std::string& Connection;
    SemanticMailbox& Mailbox;
};
inline bool BeginPossession(PossessionState S) {
    if(S.Closed || S.Awaiting || S.Possessing || S.NativeContext.generation>=9007199254740990ULL)
        return false;
    S.Mailbox.Clear();
    S.NativeContext.pawn=0;
    ++S.NativeContext.generation;
    S.Connection.clear();S.NeedsRelease=true;S.Possessing=true;
    return true;
}
inline bool FinishPossession(PossessionState S) {
    if(S.Closed || !S.Possessing || S.PawnSerial>=9007199254740990ULL) return false;
    S.NativeContext.pawn=++S.PawnSerial;
    S.Possessing=false;
    return true;
}
}

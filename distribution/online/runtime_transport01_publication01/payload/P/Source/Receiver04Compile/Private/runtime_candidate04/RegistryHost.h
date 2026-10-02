#pragma once
#include "CoreMinimal.h"
#include "../native/SessionBridge.h"

namespace MikdashOnline::Adoption01 { class FParsedAdmission; }
namespace MikdashOnline::RuntimeCandidate04 {
// Sole process-local host API. No streamer pointer, URL, receiver Start, or
// attachment capability is exposed. Admission is trusted in-process only.
class FRegistryHost final {
public:
    enum class State { WaitingForModule, AwaitingAllocation, StoppedReady, Closed, Quarantined };
    static bool Startup();
    static bool AdmitStopped(const Owner& Identity,double NativeQpcDeadline);
    static bool AdoptParsed(TSharedRef<const Adoption01::FParsedAdmission> Parsed);
    static bool Shutdown();
    static State GetState();
};
}

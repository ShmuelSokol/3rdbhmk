#pragma once
#include "CoreMinimal.h"
#include "../native/SessionBridge.h"

namespace MikdashOnline::RuntimeCandidate04 {
// Sole process-local host API. No streamer pointer, URL, receiver Start, or
// attachment capability is exposed. Admission is trusted in-process only.
class FRegistryHost final {
public:
    enum class State { WaitingForModule, AwaitingAllocation, StoppedReady, Closed, Quarantined };
    static bool Startup();
    static bool AdmitStopped(const Owner& Identity,double NativeQpcDeadline);
    static bool Shutdown();
    static State GetState();
};
}

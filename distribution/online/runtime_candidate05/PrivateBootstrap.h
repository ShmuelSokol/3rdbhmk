#pragma once
#include "CoreMinimal.h"
#include "../native/receiver03/Wire.h"

namespace MikdashOnline::RuntimeCandidate05 {
// Validation, NOT authentication of arbitrary bytes. Transport trust is the
// reviewed parent's private inherited stdin capability, never a JSON claim.
bool ValidatePrivateRecord(const TArray<uint8>& Body,double Now,Receiver03::Bootstrap& Out);

class FPrivateBootstrap final {
public:
    enum class State { Empty, Reading, StoppedProvisioned, Closed, Quarantined };
    bool Startup();
    void Tick();
    bool Shutdown();
    State GetState() const { return Phase; }
private:
    State Phase=State::Empty;
    bool Used=false,Busy=false,Stopping=false,InputPoisoned=false,HostStarted=false;
    void* Input=nullptr;
    double ReadEnd=0,Last=-1;
    int32 Expected=4;
    TArray<uint8> Bytes;
    TUniquePtr<Receiver03::Bootstrap> Provisioning;
    bool Fresh(double Deadline);
    bool CloseInput();
    void PollRead();
    void AcceptClosedRecord();
};
}

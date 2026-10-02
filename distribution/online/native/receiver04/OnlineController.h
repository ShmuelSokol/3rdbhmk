#pragma once
#include "CoreMinimal.h"
#include "MikdashPlayerController.h"
#include "Authority.h"
#include "OnlineController.generated.h"

UCLASS()
class AReceiver04Controller : public AMikdashPlayerController {
    GENERATED_BODY()
    TSharedPtr<MikdashOnline::Receiver04::Authority> Remote;
    TWeakObjectPtr<APawn> OwnedPawn;
    // Required trusted check: M persists settings. No default bypass/isolation claim.
    TFunction<bool()> SettingsOwned;
    // Project void TalkToNearbyResident cannot report exact consumed/no-op. New
    // project outcome API is required; absent callback means explicit rejection.
    TFunction<MikdashOnline::Receiver04::Outcome(const MikdashOnline::Receiver04::SemanticMailbox::Fence&)> ConsumeInteract;
    double LookDegrees=0;
    bool ValidRemote();
public:
    bool ConfigureRemote(TSharedPtr<MikdashOnline::Receiver04::Authority> Service,
        TFunction<bool()> SettingsOwnership,TFunction<MikdashOnline::Receiver04::Outcome(const MikdashOnline::Receiver04::SemanticMailbox::Fence&)> Interact,
        double DegreesPerNormalizedUnit);
    virtual void PostProcessInput(float DeltaTime,bool bGamePaused) override;
    virtual void UpdateRotation(float DeltaTime) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
};

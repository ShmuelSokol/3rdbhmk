#pragma once
#include "CoreMinimal.h"
#include "MikdashPlayerController.h"
#include "Authority.h"
#include "OnlineController.generated.h"

namespace MikdashOnline::Receiver04 { class Bootstrap; }
UCLASS()
class AReceiver04Controller : public AMikdashPlayerController {
    GENERATED_BODY()
    friend class MikdashOnline::Receiver04::Authority;
    friend class MikdashOnline::Receiver04::Bootstrap;
    TFunction<bool(const TSharedPtr<MikdashOnline::Receiver04::Authority>&)> OnOwnedPossessionBegin;
    TFunction<bool(const TSharedPtr<MikdashOnline::Receiver04::Authority>&)> OnOwnedPossessionCommit;
    TSharedPtr<MikdashOnline::Receiver04::Authority> Remote;
    TWeakObjectPtr<APawn> OwnedPawn;
    // Required trusted check: M persists settings. No default bypass/isolation claim.
    TFunction<bool()> SettingsOwned;
    // Project void TalkToNearbyResident cannot report exact consumed/no-op. New
    // project outcome API is required; absent callback means explicit rejection.
    TFunction<MikdashOnline::Receiver04::Outcome(const MikdashOnline::Receiver04::SemanticMailbox::Fence&)> ConsumeInteract;
    double LookDegrees=0;
    bool ValidRemote();
    bool FlightTransition=false;
    TWeakObjectPtr<APawn> FlightWalker,FlightDove;
    bool SupportedInitialWalker() const;
    void DetachRemoteMovement();
protected:
    virtual UClass* DoveClassForFlight() const override;
    virtual bool AcceptDoveSpawn(AMikdashDovePawn* P) override;
    virtual bool BeginDoveTransition() override;
    virtual void EndDoveTransition() override;
public:
    bool RemotePossessionCurrent() const;
    uint64_t RemotePossessionGeneration() const { return Remote.IsValid()?Remote->BoundContext().generation:0; }
    virtual void OnPossess(APawn* P) override;
    virtual void OnUnPossess() override;
    bool ConfigureRemote(TSharedPtr<MikdashOnline::Receiver04::Authority> Service,
        TFunction<bool()> SettingsOwnership,TFunction<MikdashOnline::Receiver04::Outcome(const MikdashOnline::Receiver04::SemanticMailbox::Fence&)> Interact,
        double DegreesPerNormalizedUnit);
    virtual void PostProcessInput(float DeltaTime,bool bGamePaused) override;
    virtual void UpdateRotation(float DeltaTime) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
};

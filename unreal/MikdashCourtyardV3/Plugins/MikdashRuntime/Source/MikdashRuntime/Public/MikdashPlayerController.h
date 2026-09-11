#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "FootstepCadence.h"
#include "PreparationJourney.h"
#include "ResidentDialogState.h"
#include "ResidentSimulation.h"
#include "MikdashPlayerController.generated.h"

class SWidget;
class USoundBase;
class AMikdashDovePawn;
class AMikdashResidentCharacter;
class ACharacter;

/** Uses the existing measured-walkthrough Character and its collision. */
UCLASS(Config=Game)
class MIKDASHRUNTIME_API AMikdashPlayerController : public APlayerController
{
    GENERATED_BODY()
public:
    AMikdashPlayerController();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void SetupInputComponent() override;
    virtual void PlayerTick(float DeltaTime) override;

    UFUNCTION(BlueprintCallable, Category="Walkthrough")
    void ToggleWalkthroughMenu();

    UFUNCTION(BlueprintCallable, Category="Walkthrough")
    void ResumeWalkthrough();

    UFUNCTION(BlueprintCallable, Category="Walkthrough")
    void ToggleSound();

    UFUNCTION(BlueprintPure, Category="Walkthrough")
    bool IsWalkthroughMenuOpen() const { return bMenuOpen; }

    UFUNCTION(BlueprintPure, Category="Walkthrough")
    bool IsSoundMuted() const { return bSoundMuted; }

    UFUNCTION(BlueprintCallable, Category="Walkthrough") void ToggleDoveFlight();

    /** V: cycle the precinct view on every AMikdashEnclosure in the world —
     *  Yechezkel (default) → Modern → Overlay. Shmuel's decision of 8 September 2026
     *  makes Yechezkel the opening state; this key is how a visitor compares it with today. */
    UFUNCTION(BlueprintCallable, Category="Walkthrough") void CyclePrecinctView();
    UFUNCTION(BlueprintCallable, Category="Walkthrough") void RequestDoveFlightFromMenu();
    UFUNCTION(BlueprintPure, Category="Walkthrough") bool IsDoveFlightActive() const { return bDoveFlight; }
    UFUNCTION(BlueprintPure, Category="Walkthrough") FString GetDoveFlightStatus() const { return DoveFlightStatus; }
    // Called only by the authoritative front end; never opens another menu.
    void SynchronizeFrontEndMenu(bool bVisible);
    void QuitWalkthrough();
    void ShowPreparationLesson();
    void BackToWalkthroughMenu();

    // --- Talking to a resident. The panel never pauses the game and never captures the
    // mouse: it is a hit-test-invisible overlay under the pause menu, driven from the same
    // key bindings the walkthrough already uses.
    UFUNCTION(BlueprintCallable, Category="Residents") void TalkToNearbyResident();
    UFUNCTION(BlueprintCallable, Category="Residents") void CloseResidentDialog();
    UFUNCTION(BlueprintPure, Category="Residents") bool IsResidentDialogOpen() const { return Conversation.IsTalking(); }
    UFUNCTION(BlueprintPure, Category="Residents") bool IsTalkPromptVisible() const;
    UFUNCTION(BlueprintPure, Category="Residents") FString GetTalkPromptText() const;
    /** "Name — role", empty when no panel is open. */
    UFUNCTION(BlueprintPure, Category="Residents") FString GetResidentDialogHeading() const;
    UFUNCTION(BlueprintPure, Category="Residents") FString GetResidentDialogMission() const;
    UFUNCTION(BlueprintPure, Category="Residents") FString GetResidentDialogLine() const;
    UFUNCTION(BlueprintPure, Category="Residents") FString GetResidentDialogFooter() const;
    /** The in-flight control reminder, shown only while the dove is being flown. */
    UFUNCTION(BlueprintPure, Category="Walkthrough") FString GetDoveControlHint() const;
    /** Escape: close an open dialog panel first, otherwise reach the pause menu. */
    void HandleEscapeKey();

private:
    UPROPERTY() TObjectPtr<AMikdashDovePawn> DovePawn;
    UPROPERTY() TObjectPtr<ACharacter> ParkedWalker;
    FVector ParkedWalkLocation = FVector::ZeroVector;
    FRotator ParkedControlRotation = FRotator::ZeroRotator;
    FString DoveFlightStatus = TEXT("Ground walking");
    bool bDoveFlight = false;
    bool bPendingMenuDove = false;
    double MenuDoveDeadline = 0.0;
    uint8 ParkedMovementMode = 1;
    uint8 ParkedCustomMovementMode = 0;
    void OpenMenu();
    void ApplySoundVolume();
    void Turn(float Value);
    void LookUp(float Value);
    void ApplicationActivationChanged(bool bActive);
    void UpdateFootsteps(float DeltaTime);
    UPROPERTY()
    TArray<TObjectPtr<USoundBase>> StoneSteps;
    UPROPERTY()
    TArray<TObjectPtr<USoundBase>> SoftSteps;
    TWeakObjectPtr<APawn> FootstepPawn;
    FVector LastFootstepPosition = FVector::ZeroVector;
    FMikdashFootstepCadence FootstepCadence;
    int32 FootstepSide = 0;
    int32 LastStepVariation[2] = {-1, -1};
    MikdashPreparation::Journey PreparationJourney;
    MikdashResidents::Simulation ResidentSimulation;
    double ResidentClockSeconds = 0.0;

    MikdashDialog::Conversation Conversation;
    TWeakObjectPtr<AMikdashResidentCharacter> TalkTarget;
    TArray<TWeakObjectPtr<AMikdashResidentCharacter>> KnownResidents;
    double NextResidentScanSeconds = 0.0;
    void UpdateResidentDialog();
    void ReleaseTalkTarget();
    void RefreshKnownResidents();

    TSharedPtr<SWidget> OverlayWidget;
    TSharedPtr<SWidget> MenuWidget;
    FDelegateHandle ActivationHandle;
    bool bMenuOpen = false;
    bool bHasStarted = false;

    UPROPERTY(Config)
    bool bSoundMuted = false;

    /** Scripted walk for packaged-build acceptance (development builds only):
     *  -MikdashWalkProbe=label=S2;state=YECHEZKEL;start=X:Y:Z:Yaw:Pitch;wp=X:Y/X:Y;delay=4;timeout=90
     *  After `delay` game seconds it undoes a capture script's Ghost, sets the precinct state,
     *  teleports the walking character once, steers it through the waypoints with ordinary
     *  movement input (no further teleports, no cheats), and logs MIKDASH_WALKPROBE lines:
     *  position, movement mode, and the component and actor it stands on. Inert without the switch. */
    struct FWalkProbe
    {
        bool bActive = false, bStarted = false, bDone = false;
        FString Label, State;
        FVector Start = FVector::ZeroVector;
        float Yaw = 0.f, Pitch = 0.f;
        TArray<FVector2D> Waypoints;
        int32 Next = 0;
        double Delay = 4.0, Timeout = 90.0, StartedAt = 0.0, LastLog = -1.0, FinishedWaypointsAt = -1.0;
        double MinFeetZ = 1e300, MaxFeetZ = -1e300, FallStartZ = 0.0, LongestFallCm = 0.0, SlowSeconds = 0.0;
        bool bWasFalling = false;
        int32 Samples = 0, FallingSamples = 0, StuckEvents = 0;
    };
    FWalkProbe WalkProbe;
    void ParseWalkProbe(const FString& Spec);
    void TickWalkProbe(float DeltaTime);
};

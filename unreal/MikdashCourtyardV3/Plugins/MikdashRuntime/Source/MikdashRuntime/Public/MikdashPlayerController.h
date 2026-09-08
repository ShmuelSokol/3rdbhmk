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
    UFUNCTION(BlueprintCallable, Category="Walkthrough") void RequestDoveFlightFromMenu();
    UFUNCTION(BlueprintPure, Category="Walkthrough") bool IsDoveFlightActive() const { return bDoveFlight; }
    UFUNCTION(BlueprintPure, Category="Walkthrough") FString GetDoveFlightStatus() const { return DoveFlightStatus; }
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
};

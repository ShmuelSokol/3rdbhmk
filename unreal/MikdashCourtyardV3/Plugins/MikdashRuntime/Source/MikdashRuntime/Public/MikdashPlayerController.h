#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "FootstepCadence.h"
#include "PreparationJourney.h"
#include "ResidentSimulation.h"
#include "MikdashPlayerController.generated.h"

class SWidget;
class USoundBase;
class AMikdashDovePawn;
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
    TSharedPtr<SWidget> MenuWidget;
    FDelegateHandle ActivationHandle;
    bool bMenuOpen = false;
    bool bHasStarted = false;

    UPROPERTY(Config)
    bool bSoundMuted = false;
};

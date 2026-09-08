#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/FloatingPawnMovement.h"
#include "DoveFlightMath.h"
#include "MikdashDovePawn.generated.h"

class UCameraComponent;
class USphereComponent;
class USceneComponent;
class UStaticMeshComponent;
class UStaticMesh;
class AMikdashDoveAppearance;

/** Floating movement with near-obstacle steering: a forward sphere sweep (60 cm, 300 cm ahead)
 * slows the bird and slides its input along surfaces, and a floor/ceiling trace keeps it at
 * least 120 cm above traced floors and 60 cm below ceilings. Pure math lives in DoveFlightMath.h.
 */
UCLASS()
class MIKDASHRUNTIME_API UMikdashDoveMovement : public UFloatingPawnMovement
{
    GENERATED_BODY()
public:
    UMikdashDoveMovement();
    // Shapes the pending input against a forward sweep before the base class applies it.
    virtual void ApplyControlInputToVelocity(float DeltaTime) override;
    virtual float GetMaxSpeed() const override { return MaxSpeed * ObstacleSpeedScale; }
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    bool IsSlidingAlongSurface() const { return bSliding; }
    float LastFloorDistanceCm() const { return LastFloorDistance; }
private:
    float ObstacleSpeedScale = 1.f;
    float LastFloorDistance = -1.f;
    bool bSliding = false;
};

/** Original stylized white dove for aerial architectural exploration. Wings are separate
 * components driven by a sine beat (35 degrees; 4 Hz cruise, 6 Hz climbing, level glide when
 * diving). The camera follows with a 0.15 s lag, 200 cm look-ahead and a 10 degree bank.
 * Meshes come from a map-placed AMikdashDoveAppearance when present; otherwise the earlier
 * procedural basic-shape silhouette is kept so flight never depends on an import.
 */
UCLASS()
class MIKDASHRUNTIME_API AMikdashDovePawn : public APawn
{
    GENERATED_BODY()
public:
    AMikdashDovePawn();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UFUNCTION(BlueprintCallable, Category="Dove") void SetFlightBoost(bool bBoost);
    UFUNCTION(BlueprintPure, Category="Dove") float GetFlightSpeed() const;
    UFUNCTION(BlueprintPure, Category="Dove") bool IsUsingImportedMeshes() const { return bImportedMeshes; }
    UFUNCTION(BlueprintPure, Category="Dove") bool IsGliding() const { return Wings.Gliding(); }
    UFUNCTION(BlueprintPure, Category="Dove") float GetWingAngleDegrees() const { return static_cast<float>(Wings.Angle()); }
    UFUNCTION(BlueprintPure, Category="Dove") float GetCameraRollDegrees() const { return static_cast<float>(Camera.RollDegrees); }
    // Applies the three meshes; returns false (procedural silhouette kept) when any is missing.
    bool ApplyAppearance(const AMikdashDoveAppearance* Appearance);
    bool ApplyMeshes(UStaticMesh* InBody, UStaticMesh* InLeftWing, UStaticMesh* InRightWing,
        const FVector& LeftShoulderCm, const FVector& RightShoulderCm);
private:
    UPROPERTY() TObjectPtr<USphereComponent> FlightCollision;
    UPROPERTY() TObjectPtr<UMikdashDoveMovement> FlightMovement;
    UPROPERTY() TObjectPtr<USceneComponent> Body;
    UPROPERTY() TObjectPtr<USceneComponent> LeftWing;
    UPROPERTY() TObjectPtr<USceneComponent> RightWing;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> BodyMesh;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> LeftWingMesh;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> RightWingMesh;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> ProceduralParts;
    UPROPERTY() TObjectPtr<UCameraComponent> FollowCamera;
    MikdashDove::WingBeat Wings;
    MikdashDove::CameraState Camera;
    double PreviousYaw = 0.0;
    double SmoothedYawRate = 0.0;
    bool bImportedMeshes = false;
    void UpdateWings(float DeltaSeconds);
    void UpdateBodyPose(float DeltaSeconds);
    void UpdateCamera(float DeltaSeconds);
};

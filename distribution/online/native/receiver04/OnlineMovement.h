#pragma once
#include "CoreMinimal.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "MikdashDovePawn.h"
#include "Authority.h"
#include "OnlineMovement.generated.h"

// Staged UHT source only: no project/module/default-subobject registration yet.
UCLASS()
class UReceiver04WalkerMovement : public UCharacterMovementComponent {
    GENERATED_BODY()
    TSharedPtr<MikdashOnline::Receiver04::Authority> Remote;
    TWeakObjectPtr<APlayerController> OwnedController;
    TWeakObjectPtr<APawn> OwnedPawn;
    bool ValidRemote() const;
public:
    bool ConfigureRemote(TSharedPtr<MikdashOnline::Receiver04::Authority> Service,APlayerController* Controller);
    virtual void ControlledCharacterMove(const FVector& Local,float DeltaSeconds) override;
    virtual void BuildAsyncInput() override;
};

UCLASS()
class UReceiver04DoveMovement : public UMikdashDoveMovement {
    GENERATED_BODY()
    TSharedPtr<MikdashOnline::Receiver04::Authority> Remote;
    TWeakObjectPtr<APlayerController> OwnedController;
    TWeakObjectPtr<APawn> OwnedPawn;
    struct Shaped { FVector Direction; float Scale=1; bool Sliding=false; };
    float EvaluatedScale=1;
    bool EvaluatedSliding=false;
    bool ValidRemote() const;
    Shaped Shape(const FVector& Input) const;
    void Commit(const Shaped& Input,float DeltaSeconds);
public:
    bool ConfigureRemote(TSharedPtr<MikdashOnline::Receiver04::Authority> Service,APlayerController* Controller);
    virtual void ApplyControlInputToVelocity(float DeltaSeconds) override;
    virtual float GetMaxSpeed() const override{return Remote.IsValid()?MaxSpeed*EvaluatedScale:Super::GetMaxSpeed();}
    // The original nonvirtual IsSlidingAlongSurface cannot expose this subclass's
    // state. Future project integration must route diagnostics to this accessor.
    bool IsOnlineSlidingAlongSurface()const{return EvaluatedSliding;}
};

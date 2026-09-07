#include "MikdashDovePawn.h"
#include "Camera/CameraComponent.h"
#include "Components/SphereComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/FloatingPawnMovement.h"
#include "GameFramework/SpringArmComponent.h"
#include "UObject/ConstructorHelpers.h"

AMikdashDovePawn::AMikdashDovePawn()
{
    PrimaryActorTick.bCanEverTick = true;
    AutoPossessAI = EAutoPossessAI::Disabled;
    FlightCollision = CreateDefaultSubobject<USphereComponent>(TEXT("FlightCollision"));
    FlightCollision->InitSphereRadius(24.f);
    FlightCollision->SetCollisionProfileName(TEXT("Pawn"));
    FlightCollision->SetCanEverAffectNavigation(false);
    SetRootComponent(FlightCollision);
    FlightMovement = CreateDefaultSubobject<UFloatingPawnMovement>(TEXT("FlightMovement"));
    FlightMovement->UpdatedComponent = FlightCollision;
    FlightMovement->MaxSpeed = 1800.f;
    FlightMovement->Acceleration = 4500.f;
    FlightMovement->Deceleration = 6500.f;
    FlightMovement->TurningBoost = 5.f;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cone(TEXT("/Engine/BasicShapes/Cone.Cone"));
    auto Shape = [this](const FName Name, USceneComponent* Parent, UStaticMesh* Mesh,
                       FVector Position, FVector Scale, FRotator Rotation = FRotator::ZeroRotator)
    {
        UStaticMeshComponent* Part = CreateDefaultSubobject<UStaticMeshComponent>(Name);
        Part->SetupAttachment(Parent); Part->SetStaticMesh(Mesh);
        Part->SetRelativeLocation(Position); Part->SetRelativeScale3D(Scale); Part->SetRelativeRotation(Rotation);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Part->SetCanEverAffectNavigation(false);
    };
    // Engine basic-shape white material; original ellipsoid/feather silhouette.
    Shape(TEXT("Body"), FlightCollision, Sphere.Object, FVector::ZeroVector, FVector(.61,.25,.28));
    Shape(TEXT("Breast"), FlightCollision, Sphere.Object, FVector(15,0,4), FVector(.29,.25,.32));
    Shape(TEXT("Head"), FlightCollision, Sphere.Object, FVector(30,0,14), FVector(.19,.17,.19));
    Shape(TEXT("Beak"), FlightCollision, Cone.Object, FVector(42,0,14), FVector(.07,.07,.17), FRotator(90,0,0));
    for (int32 Index=0; Index<5; ++Index)
        Shape(FName(*FString::Printf(TEXT("TailFeather%d"),Index)), FlightCollision, Sphere.Object,
              FVector(-36, (Index-2)*5.f,0), FVector(.39,.067,.025), FRotator(0,(Index-2)*9.f,0));
    LeftWing=CreateDefaultSubobject<USceneComponent>(TEXT("LeftWing"));LeftWing->SetupAttachment(FlightCollision);LeftWing->SetRelativeLocation(FVector(0,-9,5));
    RightWing=CreateDefaultSubobject<USceneComponent>(TEXT("RightWing"));RightWing->SetupAttachment(FlightCollision);RightWing->SetRelativeLocation(FVector(0,9,5));
    for (int32 Side : {-1,1})
    {
        USceneComponent* Wing = Side<0 ? LeftWing.Get() : RightWing.Get();
        Shape(FName(*FString::Printf(TEXT("WingShoulder%d"),Side)), Wing, Sphere.Object,
              FVector(-3,Side*19.f,0), FVector(.35,.55,.045), FRotator(0,Side*-12.f,0));
        for (int32 Index=0; Index<7; ++Index)
            Shape(FName(*FString::Printf(TEXT("FlightFeather%d_%d"),Side,Index)),Wing,Sphere.Object,
                  FVector(-15+Index*3.f,Side*(36+Index*3.f),0),
                  FVector(.075,.42-Index*.025,.024),FRotator(0,Side*(20+Index*7.f),0));
    }
    USpringArmComponent* Boom=CreateDefaultSubobject<USpringArmComponent>(TEXT("DoveCameraBoom"));
    Boom->SetupAttachment(FlightCollision);Boom->TargetArmLength=230.f;Boom->SocketOffset=FVector(0,0,45);
    Boom->bUsePawnControlRotation=true;Boom->bDoCollisionTest=true;Boom->bEnableCameraLag=true;Boom->CameraLagSpeed=8.f;
    UCameraComponent* Camera=CreateDefaultSubobject<UCameraComponent>(TEXT("DoveCamera"));
    Camera->SetupAttachment(Boom,USpringArmComponent::SocketName);Camera->FieldOfView=85.f;
}
void AMikdashDovePawn::SetFlightBoost(bool bBoost) { FlightMovement->MaxSpeed=bBoost ? 6000.f : 1800.f; }
float AMikdashDovePawn::GetFlightSpeed() const { return FlightMovement->MaxSpeed; }
void AMikdashDovePawn::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    WingTime+=FMath::Max(0.f,DeltaSeconds);
    const float Flap=FMath::Sin(WingTime*9.f)*21.f;
    LeftWing->SetRelativeRotation(FRotator(0,0,-Flap));
    RightWing->SetRelativeRotation(FRotator(0,0,Flap));
    if (GetVelocity().SizeSquared2D()>100.f)
        SetActorRotation(FRotator(0,GetVelocity().Rotation().Yaw,0));
}
